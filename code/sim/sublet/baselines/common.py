"""Shared rules of the baselines BL1-BL5 (design/sim_spec_ms2.md §15.1).

- Contract per site: k*(l) = argmin over the contracts of l's menu that common.treated_as_protected
  does not flag of the key (a_lk, P_k, -H_k, k) (cheapest per GPU-hour, then the shortest billed term,
  then the longest notice, then the index).
- Usable arc (c, l): delta_cl < INF and delta_cl + g_j a_{l k*(l)} < q_j (a replica at full load beats
  fallback); site score sigma_cl = g_j a_{l k*(l)} + delta_cl; a site choice takes the minimum score
  among usable sites that pass the capacity pre-check, ties by the site order pi (§2.3, M7).
- Rule BR (defer_release, M41): a release decided while t Δs < prepaid_end_min waits for the first slot
  at or after prepaid_end_min (releasing earlier saves nothing under rule T7); each baseline re-applies
  its own release rule every slot, so a release is cancelled if the lease is needed again.
- A refusal or pre-check drop marks the site unavailable to the baseline for the slot in which it is
  reported. Notices are ignored unless a baseline says otherwise.
- Demand statistics per client and slot: D_c(t) (maximum over the slot's fast slots, revealed at the
  slot's start) and dbar_c(t) (mean), kept in a ring buffer.

MS5b options (design/sublet_v2.md §3, §8.1; C38). A baseline takes one by declaring its key in PARAMS; every
default is the MS1-MS5 behaviour, so every run at the defaults is unchanged, and params() leaves the keys a
class lists in QUIET_KEYS out while they hold their defaults, so that its records are unchanged too.
- tau_min (None; minutes): k*(l) is taken over the contracts with tau_k Δs >= tau_min (SiteTable); a site with
  none is not usable (BL5-tau60).
- backoff_cap (None; slots): generic site back-off. After an own lease ends with cause 'reclaim' or
  'violation' at site l, reported in slot t: b_l <- 1 if b_l = 0 or t > until_l + 2 b_l, else
  min(2 b_l, backoff_cap); until_l <- t + b_l; the site choice excludes l while t <= until_l (BL1-BO; the
  baseline's purchases use _excluded).
- contract_rule ('kstar' | 'c2'): with 'c2' a purchase for LLM j at site l uses A9.3's base contract
  kbar(l, j) (contracts.c2_contract_table, read by c2_base_contracts) and the usable arcs and scores are those of
  kbar (SiteTable.use_contracts; BL5N).
retrorenting.py adds mbb and greedy.py demand_lag.

MS7 (design/ms7/plan.md X1, C53; design/ms7/feasibility/causal.md, build list): demand_lag (0; slots) moves from
greedy.py into Baseline.demand_of, unchanged: a subclass that declares the key in PARAMS (BL1, BL2, BL3) and reads
demand_of(obs) instead of obs.demand acts at slot t on the demand of slot t - L as revealed then (zeros for t < L),
so with L = 1 on the full fast-slot vector of slot t - 1, with no lookahead; at L = 0 demand_of returns obs.demand
itself, so every run at the defaults is unchanged. BL5 keeps no demand_lag (its default build is already lagged).

MS7 options (design/ms7/plan.md X4, C54; design/ms7/feasibility/baselines.md §2 item 1, §3 B2): contract_rule 'c2'
is also declared by BL2 (ski.py), BL3 (spothedge.py) and BL4 (cocar.py), each hiding the key at its default
(QUIET_KEYS), which read kbar through c2_base_contracts_cached (A9's per-process table cache; BL5 keeps
c2_base_contracts); SiteTable.s0_min reads the contract of use_contracts (unchanged before it). spothedge.py adds
extra_scope and extra_when_idle, and mpc.py the receding-horizon LP (MPC).

Baselines see only the PublicView and the observations (§2.2); this module imports numpy, the
standard library and the allowed sublet modules.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Iterable, Optional

import numpy as np

from ..algos.common import (LeaseBook, PolicyError, policy_streams, resolve_params, site_order,
                            treated_as_protected)
from ..policies.base import Policy
from ..types import INF, ActionResult, Buy, LeaseView, PublicView, SlowObs

SITE_ORDERS = ("auto", "index", "random")
CONTRACT_RULES = ("kstar", "c2")             # MS5b option contract_rule (design/sublet_v2.md §3, BL5N)
BACKOFF_CAUSES = ("reclaim", "violation")    # end causes that start or extend a site back-off (BL1-BO)


# ---------------------------------------------------------------- contracts and sites
def _contract_key(view: PublicView, l: int, k: int) -> tuple:
    c = view.contracts[k]
    return (float(view.price[l, k]), int(c.prepaid_min), -int(c.H_min), int(k))


def _offered(view: PublicView, l: int, flagged: bool) -> list[int]:
    return [int(k) for k in view.sites[l].menu
            if np.isfinite(view.price[l, k]) and treated_as_protected(view, k) == flagged]


def k_star(view: PublicView, tau_min: Optional[float] = None) -> np.ndarray:
    """(m,) int64: k*(l), the contract of §15.1 among the offered contracts that
    treated_as_protected does not flag; -1 where the site offers none. With tau_min (minutes; MS5b,
    design/sublet_v2.md §3, BL5-tau60) only the contracts with tau_k Δs >= tau_min count."""
    out = np.full(len(view.sites), -1, dtype=np.int64)
    slow = view.grid.slow_min
    for l in range(len(view.sites)):
        ks = _offered(view, l, False)
        if tau_min is not None:
            ks = [k for k in ks if view.contracts[k].tau_slots * slow >= tau_min]
        if ks:
            out[l] = min(ks, key=lambda k: _contract_key(view, l, k))
    return out


def c2_base_contracts(view: PublicView) -> np.ndarray:
    """(m, J) int64: A9.3's base contract kbar(l, j) = argmin over P3(l, j) of (a_lk, P_k, -H_k, k), -1 where
    the site offers no revocable contract (design/sublet_v2.md §2.2 A9.3; contract_rule 'c2', §3 BL5N): the
    'kbar' of contracts.c2_contract_table(view, insure=False), imported on first use (no insurance test)."""
    from ..algos import contracts
    table = getattr(contracts, "c2_contract_table", None)
    if table is None:
        raise PolicyError("contract_rule 'c2' needs contracts.c2_contract_table (design/sublet_v2.md §8.1, C37), "
                          "which this build does not have")
    tab = table(view, insure=False)
    kbar = tab.get("kbar") if isinstance(tab, Mapping) else getattr(tab, "kbar", None)
    if kbar is None:
        raise PolicyError("contracts.c2_contract_table returned no 'kbar'")
    kbar = np.asarray(kbar, dtype=np.int64)
    if kbar.shape != (len(view.sites), len(view.llms)):
        raise PolicyError(f"contracts.c2_contract_table: kbar has shape {kbar.shape}, expected "
                          f"{(len(view.sites), len(view.llms))}")
    return kbar.copy()


def c2_base_contracts_cached(view: PublicView) -> np.ndarray:
    """c2_base_contracts(view) through A9's per-process cache of contracts.c2_contract_table (algos.a9.contract_table,
    keyed by the view's fingerprint; imported on first use): the same array, computed once per view and process (MS7
    C54: BL2-c2 builds one table per borrower and lender mode). BL5's contract_rule keeps c2_base_contracts."""
    from ..algos.a9 import contract_table
    kbar = np.asarray(contract_table(view, insure=False)["kbar"], dtype=np.int64)
    if kbar.shape != (len(view.sites), len(view.llms)):
        raise PolicyError(f"contract_table: kbar has shape {kbar.shape}, expected {(len(view.sites), len(view.llms))}")
    return kbar.copy()


def cheapest_flagged(view: PublicView) -> np.ndarray:
    """(m,) int64: the cheapest offered contract of each site that treated_as_protected flags (same
    key as k*); -1 where the site offers none (BL4's K_l, §15.6)."""
    out = np.full(len(view.sites), -1, dtype=np.int64)
    for l in range(len(view.sites)):
        ks = _offered(view, l, True)
        if ks:
            out[l] = min(ks, key=lambda k: _contract_key(view, l, k))
    return out


class SiteTable:
    """k*(l), usable arcs, site scores and the site choice of §15.1 for one view and site order pi. With
    tau_min (MS5b) k* is restricted to tau_k Δs >= tau_min; use_contracts replaces k*(l) by a contract per site
    and LLM (contract_rule 'c2'), which `contract` and `price_of` return (k*(l) and a_{l k*} until then)."""

    def __init__(self, view: PublicView, pi: np.ndarray, tau_min: Optional[float] = None):
        self.view = view
        m = len(view.sites)
        self.tau_min = tau_min
        self.kstar = k_star(view, tau_min)
        self.kc: Optional[np.ndarray] = None              # (m, J) contract per site and LLM after use_contracts
        self.a_c: Optional[np.ndarray] = None             # (m, J) its price, INF if none
        self.g = np.array([x.g for x in view.llms], dtype=np.float64)
        self.q = np.array([x.q_usd_per_h for x in view.llms], dtype=np.float64)
        self.cl_llm = np.asarray(view.client_llm, dtype=np.int64)
        self.delta = np.asarray(view.client_delta_usd_per_h, dtype=np.float64)
        has = self.kstar >= 0
        a = np.full(m, INF)
        a[has] = np.asarray(view.price, dtype=np.float64)[np.flatnonzero(has), self.kstar[has]]
        self.a_star = a                                   # (m,) price of k*(l), INF if none
        rent = self.g[self.cl_llm][:, None] * np.where(has, a, 0.0)[None, :]
        qc = self.q[self.cl_llm][:, None]
        with np.errstate(invalid="ignore"):
            self.usable = np.isfinite(self.delta) & has[None, :] & (self.delta + rent < qc)
        self.score = np.where(self.usable, rent + np.where(np.isfinite(self.delta), self.delta, 0.0), INF)
        self.pi = np.asarray(pi, dtype=np.int64)
        self.rank = np.empty(m, dtype=np.int64)
        self.rank[self.pi] = np.arange(m, dtype=np.int64)
        # usable sites of each client in (score, pi) order
        self.order = [sorted((int(l) for l in np.flatnonzero(self.usable[c])),
                             key=lambda l, c=c: (self.score[c, l], self.rank[l]))
                      for c in range(len(self.cl_llm))]

    def use_contracts(self, kc: np.ndarray) -> None:
        """Buy contract kc[l, j] for LLM j at site l (-1: none, site not usable for j) and rebuild the usable
        arcs, scores and site orders of §15.1 with it: (c, l) is usable iff delta_cl < inf, kc[l, j_c] >= 0 and
        delta_cl + g_j a_{l kc} < q_j, with score g_j a_{l kc} + delta_cl (MS5b contract_rule 'c2', BL5N)."""
        m, J = len(self.view.sites), len(self.g)
        kc = np.asarray(kc, dtype=np.int64)
        if kc.shape != (m, J):
            raise ValueError(f"SiteTable.use_contracts: kc has shape {kc.shape}, expected {(m, J)}")
        has = kc >= 0
        a = np.full((m, J), INF)
        li, ji = np.nonzero(has)
        a[li, ji] = np.asarray(self.view.price, dtype=np.float64)[li, kc[li, ji]]
        self.kc, self.a_c = kc.copy(), a
        has_c, a_c = has[:, self.cl_llm].T, a[:, self.cl_llm].T          # (n, m) at each client's LLM
        rent = self.g[self.cl_llm][:, None] * np.where(has_c, a_c, 0.0)
        qc = self.q[self.cl_llm][:, None]
        with np.errstate(invalid="ignore"):
            self.usable = np.isfinite(self.delta) & has_c & (self.delta + rent < qc)
        self.score = np.where(self.usable, rent + np.where(np.isfinite(self.delta), self.delta, 0.0), INF)
        self.order = [sorted((int(l) for l in np.flatnonzero(self.usable[c])),
                             key=lambda l, c=c: (self.score[c, l], self.rank[l]))
                      for c in range(len(self.cl_llm))]

    def contract(self, l: int, j: int) -> int:
        """The contract a purchase for LLM j at site l uses: k*(l), or kc[l, j] after use_contracts."""
        return int(self.kstar[l]) if self.kc is None else int(self.kc[l, j])

    def price_of(self, l: int, j: int) -> float:
        """Price per GPU-hour of that contract: a_{l k*(l)}, or a_{l kc[l, j]} after use_contracts."""
        return self.a_star[l] if self.a_c is None else self.a_c[l, j]

    def best_static(self, c: int) -> Optional[int]:
        """The usable site of client c with the lowest score (ties by pi), ignoring capacity."""
        return self.order[c][0] if self.order[c] else None

    def best_site(self, c: int, obs: SlowObs, book: LeaseBook, exclude: Iterable[int] = ()) -> Optional[int]:
        """The usable site of client c with the lowest score (ties by pi) that is not in `exclude` and
        passes the capacity pre-check for one replica of c's LLM given the actions staged in `book`."""
        ex = set(exclude)
        gp = int(self.g[self.cl_llm[c]])
        for l in self.order[c]:
            if l not in ex and book.can_buy(obs, self.view, l, gp):
                return l
        return None

    def s0_min(self, j: int, l: int) -> float:
        """C2's s0 in minutes at site l with k*(l): 60 beta~_{j l k*} / (q_j - g_j a_{l k*}) (§15.4); after
        use_contracts the same with kc[l, j] and its price (MS7 C54, BL2's contract_rule 'c2'). Until then contract
        and price_of are k*(l) and a_{l k*}, so the value is unchanged."""
        k = self.contract(l, j)
        return 60.0 * float(self.view.beta_tilde_usd[j, l, k]) / (self.q[j] - self.g[j] * self.price_of(l, j))

    def rent_rate(self, lease: LeaseView) -> float:
        """USD per hour of a lease past its billed term: gpus x price."""
        return float(lease.gpus) * float(self.view.price[lease.site, lease.contract])


# ---------------------------------------------------------------- demand history
class DemandHistory:
    """Ring buffer of the slot maxima D_c(t) and slot means dbar_c(t) of the last `size` slow slots."""

    def __init__(self, n: int, size: int):
        self.size = max(1, int(size))
        self.D = np.zeros((n, self.size))
        self.mean = np.zeros((n, self.size))
        self.t_last = -1

    def push(self, obs: SlowObs) -> tuple[np.ndarray, np.ndarray]:
        """Record slot obs.t; returns (D, dbar) of the slot."""
        d = np.asarray(obs.demand, dtype=np.float64)
        if d.shape[1]:
            D, mean = d.max(axis=1), d.mean(axis=1)
        else:
            D = mean = np.zeros(d.shape[0])
        i = obs.t % self.size
        self.D[:, i], self.mean[:, i] = D, mean
        self.t_last = obs.t
        return D, mean

    def mean_at(self, t: int) -> np.ndarray:
        """(n,) dbar_c(t) of a recorded slot t in (t_last - size, t_last]."""
        if not (self.t_last - self.size < t <= self.t_last) or t < 0:
            raise IndexError(f"slot {t} is not in the buffer (last {self.t_last}, size {self.size})")
        return self.mean[:, t % self.size].copy()


# ---------------------------------------------------------------- base class
class Baseline(Policy):
    """Common state of BL1-BL5: parameters (PARAMS, PolicyError for unknown keys), the policy's random
    streams and site order pi, the SiteTable, a LeaseBook, the sites marked unavailable for the slot,
    and counters for report(). MS5b: the options tau_min and backoff_cap of the module docstring, for a
    subclass that declares them."""
    name = "baseline"
    PARAMS: dict = {}
    INPUTS: tuple = ()          # driver inputs the constructor accepts (§4.2)
    # MS5b option keys of PARAMS that params() leaves out while they hold their defaults (design/sublet_v2.md
    # §8.2, C38: the records of runs at the defaults stay those of MS1-MS5). Read from the class's own body
    # only, so a subclass lists every key it declares in params() unless it sets its own QUIET_KEYS.
    QUIET_KEYS: tuple = ()

    def __init__(self, **kw):
        self._params, self._inputs = resolve_params(self.PARAMS, kw, who=type(self).__name__, inputs=self.INPUTS)
        if "defer_release" in self._params and not isinstance(self._params["defer_release"], bool):
            raise PolicyError(f"{type(self).__name__}: defer_release must be true or false")
        if self._params.get("site_order", "auto") not in SITE_ORDERS:
            raise PolicyError(f"{type(self).__name__}: site_order must be one of {SITE_ORDERS}")
        self._validate_options()
        self._validate()

    def _validate_options(self) -> None:
        """Checks of the MS5b options a subclass declares (PolicyError)."""
        p, who = self._params, type(self).__name__

        def is_int(v) -> bool:
            return isinstance(v, (int, np.integer)) and not isinstance(v, bool)

        if p.get("backoff_cap") is not None and not (is_int(p["backoff_cap"]) and p["backoff_cap"] >= 1):
            raise PolicyError(f"{who}: backoff_cap must be None or an integer >= 1, got {p['backoff_cap']!r}")
        u = p.get("tau_min")
        if u is not None and (isinstance(u, bool) or not isinstance(u, (int, float, np.integer, np.floating))
                              or not np.isfinite(u) or u < 0):
            raise PolicyError(f"{who}: tau_min must be None or a number of minutes >= 0, got {u!r}")
        if "contract_rule" in p:
            self._choice("contract_rule", CONTRACT_RULES)
        if "mbb" in p and not isinstance(p["mbb"], bool):
            raise PolicyError(f"{who}: mbb must be true or false")
        if "demand_lag" in p and not (is_int(p["demand_lag"]) and p["demand_lag"] >= 0):
            raise PolicyError(f"{who}: demand_lag must be an integer >= 0, got {p['demand_lag']!r}")

    def _validate(self) -> None:
        """Checks of the subclass's parameter values (PolicyError)."""

    def _choice(self, name: str, options: tuple) -> None:
        if self._params[name] not in options:
            raise PolicyError(f"{type(self).__name__}: {name} must be one of {list(options)}, "
                              f"got {self._params[name]!r}")

    def params(self) -> dict:
        quiet = type(self).__dict__.get("QUIET_KEYS", ())
        return {k: copy.deepcopy(v) for k, v in self._params.items()
                if not (k in quiet and type(v) is type(self.PARAMS[k]) and v == self.PARAMS[k])}

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        self.streams = policy_streams(rng)
        self.pi = site_order(view, self.streams["order"], self._params.get("site_order", "auto"))
        self.sites = SiteTable(view, self.pi, tau_min=self._params.get("tau_min"))
        self.book = LeaseBook()
        self.unavail: set[int] = set()
        self.slow_min = view.grid.slow_min
        self.T_slow = view.grid.T_slow
        self.n = len(view.client_llm)
        self._released: set[int] = set()
        self._deferred: set[int] = set()
        self.counts = {"buys": 0, "bought": 0, "refused": 0, "releases": 0, "deferred_leases": 0,
                       "notices": 0, "deaths": 0, "ended": {}}
        self._lagged: dict[int, np.ndarray] = {}        # slot -> its demand (demand_lag >= 1; demand_of, C53)
        self._backoff_cap = self._params.get("backoff_cap")
        if self._backoff_cap is not None:
            self._lease_site: dict[int, int] = {}       # own leases bought (results seen) -> site
            self._bo_b: dict[int, int] = {}             # site -> b_l (slots)
            self._bo_until: dict[int, int] = {}         # site -> until_l (last slot of the back-off)
            self._bo_hits: dict[int, int] = {}          # site -> number of back-off events

    # -------------------------------------------------------- per slot helpers
    def demand_of(self, obs: SlowObs) -> np.ndarray:
        """(n, phi) the demand the policy acts on at slot obs.t: obs.demand itself, or with demand_lag L >= 1 the
        demand of slot t - L as observed then (zeros for t < L); idempotent within a slot. GreedyLease's rule of MS5b
        (C38), moved here unchanged for BL2 and BL3 (C53); a class without the key in PARAMS gets obs.demand."""
        lag = int(self._params.get("demand_lag", 0))
        if not lag:
            return obs.demand
        self._lagged[obs.t] = np.array(obs.demand, dtype=np.float64)
        for s in [s for s in self._lagged if s < obs.t - lag]:
            del self._lagged[s]
        past = self._lagged.get(obs.t - lag)
        return np.zeros_like(self._lagged[obs.t]) if past is None else past

    def _begin(self, obs: SlowObs) -> list[tuple[object, ActionResult]]:
        """LeaseBook.begin; marks the sites of refused or dropped Buys unavailable for this slot and
        updates the counters (and, with backoff_cap, the site back-off from obs.ended). Returns begin's
        (key, result) list."""
        res = self.book.begin(obs)
        self.unavail = set()
        for _key, r in res:
            if r.ok:
                self.counts["bought"] += 1
            else:
                self.counts["refused"] += 1
                self.unavail.add(int(r.action.site))
        self.counts["notices"] += len(obs.notices)
        for _lid, _end, cause in obs.ended:
            self.counts["ended"][cause] = self.counts["ended"].get(cause, 0) + 1
        if self._backoff_cap is not None:
            self._back_off(obs, res)
        return res

    def _back_off(self, obs: SlowObs, res: list[tuple[object, ActionResult]]) -> None:
        """The site back-off of backoff_cap (module docstring): every own lease that obs.ended reports with
        cause 'reclaim' or 'violation' at site l in slot t = obs.t starts or extends l's back-off."""
        t = obs.t
        for _key, r in res:
            if r.ok:
                self._lease_site[int(r.lease_id)] = int(r.action.site)
        for lid, _end, cause in obs.ended:
            l = self._lease_site.pop(int(lid), None)
            if l is None or cause not in BACKOFF_CAUSES:
                continue
            b = self._bo_b.get(l, 0)
            b = 1 if (b == 0 or t > self._bo_until[l] + 2 * b) else min(2 * b, self._backoff_cap)
            self._bo_b[l], self._bo_until[l] = b, t + b
            self._bo_hits[l] = self._bo_hits.get(l, 0) + 1

    def _excluded(self, t: int) -> set[int]:
        """Sites a purchase at slot t must avoid: those marked unavailable for the slot and, with backoff_cap,
        those backed off (t <= until_l). Without backoff_cap this is self.unavail itself."""
        if self._backoff_cap is None:
            return self.unavail
        return self.unavail | {l for l, u in self._bo_until.items() if t <= u}

    def _gone(self, lid: int, obs: SlowObs) -> bool:
        """Lease `lid` is absent from obs.leases; True if it died (was not released by this policy)."""
        died = lid not in self._released
        self._released.discard(lid)
        self._deferred.discard(lid)
        if died:
            self.counts["deaths"] += 1
        return died

    def _buy(self, key, site: int, llm: int, tag: str) -> None:
        self.book.buy(key, Buy(int(site), self.sites.contract(site, llm), int(llm), 1, tag=tag))
        self.counts["buys"] += 1

    def _release_due(self, obs: SlowObs, lease: LeaseView) -> bool:
        """Rule BR: a release may execute now (defer_release off, or t Δs >= prepaid_end_min)."""
        return (not self._params.get("defer_release", True)) or obs.minute >= lease.prepaid_end_min

    def _try_release(self, obs: SlowObs, lease: LeaseView) -> bool:
        """Release `lease` now if rule BR allows it (True), else count it as deferred (False)."""
        if self._release_due(obs, lease):
            self.book.release(lease.id)
            self._released.add(lease.id)
            self._deferred.discard(lease.id)
            self.counts["releases"] += 1
            return True
        if lease.id not in self._deferred:
            self._deferred.add(lease.id)
            self.counts["deferred_leases"] += 1
        return False

    def _not_deferred(self, lid: int) -> None:
        """A deferred release that the baseline's rule no longer selects is cancelled."""
        self._deferred.discard(lid)

    def report(self) -> dict:
        if not hasattr(self, "sites"):          # before reset
            return {"params": self.params()}
        out = {"params": self.params(), "counts": copy.deepcopy(self.counts),
               "k_star": [int(k) for k in self.sites.kstar], "site_order": [int(l) for l in self.pi],
               "book": dict(self.book.stats)}
        if self.sites.kc is not None:
            out["contracts"] = [[int(k) for k in row] for row in self.sites.kc]
        if self._backoff_cap is not None:
            out["backoff"] = {"cap": int(self._backoff_cap), "events": int(sum(self._bo_hits.values())),
                              "by_site": {str(l): {"events": int(self._bo_hits[l]), "b": int(self._bo_b[l]),
                                                   "until": int(self._bo_until[l])} for l in sorted(self._bo_b)}}
        return out


__all__ = ["SITE_ORDERS", "CONTRACT_RULES", "BACKOFF_CAUSES", "k_star", "c2_base_contracts", "c2_base_contracts_cached",
           "cheapest_flagged",
           "SiteTable", "DemandHistory", "Baseline"]
