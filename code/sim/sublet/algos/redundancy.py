"""Redundancy rule: exposure and N+1 headroom (design/sim_spec_ms2.md §12; design §3.2.6, M36, M37).

Applied by A6 each slow slot (heuristic, no guarantee). Logical slots of the execution layer
(§7.1) with the same LLM j and the same X3 pool P (§7.3, computed at their last purchase) form a
group. A lease of a slot in the group is exposed if it is alive, revocable, past its guaranteed
period (t >= start_slot + tau_k) and its notice is shorter than the fastest feasible replacement
load, 60 H_k < lambda_min(P) = min_{l in P} lam_s[j, l] (M36). The group needs a spare if
  'always2': n_exp >= 1;   'rule' (default): alpha < n_exp nu lambda_min / 86400,
with alpha = g_j a / q_j at the cheapest price among the exposed leases and nu the calibration
constant `spare_threshold.nu_per_day_used` of a5b_exposure_thresholds.json (M37). The spare (at
most one per group) is one replica at the pool site with the lowest column cost per guaranteed
hour C_ljk / (L_k Δs / 60) outside the correlation group that holds most of the exposed replicas,
preferring a contract that is not exposed itself; it serves through routing like any replica and
is not a logical slot. It is released at the first slot at or after its billed term once the
condition fails, and re-bought after a death while the condition holds.

Wider set (MS4 addition C26, design/sim_spec_ms4.md §2.3, M40): when no pool site qualifies (every
pool site in the majority group, without a finite C or failing can_buy), the same choice is made
over the sites outside the pool with a finite delta_{cl} for at least one stranded client c of the
exposed replicas' slots (`stranded_clients`, the set S of x3_pool), with the same group rule, C and
can_buy: a second cover for those clients in another correlation group. report()['buys'] counts
every spare purchase, 'buys_wide' those from the wider set, 'no_site' the cases where neither set
has a site. Where the pool search succeeds, or no spare is needed, nothing changes.

The rule stages its actions in the policy's LeaseBook under keys ('spare', group key).
"""
from __future__ import annotations

import json
from typing import Callable, Iterable, Optional, Sequence

import numpy as np

from ..paths import ANALYSIS_OUT
from ..types import INF, Buy, PublicView, SlowObs
from .common import EPS_DEMAND, PolicyError, column_cost, pd_window_slots, treated_as_protected

MODES = ("off", "rule", "always2")
A5B_FILE = "a5b_exposure_thresholds.json"
SPARE_TAG = "spare"
_NU_CACHE: list = []


def default_nu_per_day() -> float:
    """nu = a5b_exposure_thresholds.json `spare_threshold.nu_per_day_used` (reclaims per day; the
    median over the MaaS clusters at lease size P50, M37)."""
    if not _NU_CACHE:
        with open(ANALYSIS_OUT / A5B_FILE) as f:
            _NU_CACHE.append(float(json.load(f)["spare_threshold"]["nu_per_day_used"]))
    return _NU_CACHE[0]


# ---------------------------------------------------------------- pure parts
def x3_pool(view: PublicView, key: tuple, D: np.ndarray, *, zeta: float, site_perm: np.ndarray,
            ptr: int, L: Sequence[int]) -> tuple[int, ...]:
    """X3 pool of a logical slot with key (l0, j, k, iota) (§7.3, M15), sites in pi order: stranded
    clients S = clients of LLM j with delta_{c l0} < INF and D_c > EPS_DEMAND (all such clients if
    none is on); feasible sites offer k (k not flagged by treated_as_protected) and have
    delta_{cl} < INF for every c in S; the pool keeps those with C_ljk <= zeta min C (column cost of
    §5.2 with window L_k); (ptr,) if it is empty."""
    l0, j, k = int(key[0]), int(key[1]), int(key[2])
    delta = np.asarray(view.client_delta_usd_per_h, dtype=np.float64)
    cl = np.asarray(view.client_llm, dtype=np.int64)
    cands = [c for c in range(len(cl)) if cl[c] == j and np.isfinite(delta[c, l0])]
    S = [c for c in cands if D[c] > EPS_DEMAND] or cands
    feas: list[int] = []
    if not treated_as_protected(view, k):
        for l in site_perm:
            l = int(l)
            if k in view.sites[l].menu and np.isfinite(view.price[l, k]) \
                    and all(np.isfinite(delta[c, l]) for c in S):
                feas.append(l)
    if feas:
        cost = {l: column_cost(view, l, j, k, int(L[k])) for l in feas}
        cmin = min(cost.values())
        pool = [l for l in feas if cost[l] <= zeta * cmin]
        if pool:
            return tuple(pool)
    return (int(ptr),)


def stranded_clients(view: PublicView, key: tuple, D: np.ndarray) -> list[int]:
    """The stranded clients S of a logical slot with key (l0, j, k, iota), as x3_pool takes them (§7.3, M15):
    the clients of LLM j with delta_{c l0} < INF and D_c > EPS_DEMAND, all such clients if none is on (C26)."""
    l0, j = int(key[0]), int(key[1])
    delta = np.asarray(view.client_delta_usd_per_h, dtype=np.float64)
    cl = np.asarray(view.client_llm, dtype=np.int64)
    cands = [c for c in range(len(cl)) if cl[c] == j and np.isfinite(delta[c, l0])]
    return [c for c in cands if D[c] > EPS_DEMAND] or cands


def wide_sites(view: PublicView, clients: Iterable[int], site_perm: np.ndarray,
               exclude: Iterable[int] = ()) -> tuple[int, ...]:
    """C26's wider set: the sites, in pi order, with delta_{cl} < INF for at least one of `clients`, without the
    sites of `exclude` (the pool, already searched). choose_spare keeps those with a finite C for LLM j."""
    delta = np.asarray(view.client_delta_usd_per_h, dtype=np.float64)
    cs = sorted({int(c) for c in clients})
    skip = {int(l) for l in exclude}
    if not cs:
        return ()
    ok = np.isfinite(delta[cs]).any(axis=0)
    return tuple(int(l) for l in site_perm if ok[int(l)] and int(l) not in skip)


def lam_min_s(view: PublicView, j: int, pool: Iterable[int]) -> float:
    """lambda_min(P) = min_{l in P} lam_s[j, l] in seconds, the fastest feasible replacement load."""
    return float(min(float(view.lam_s[j, l]) for l in pool))


def is_exposed(view: PublicView, lease, t: int, lam_min: float) -> bool:
    """Exposure of an alive lease at slot t (M36): revocable (not flagged by treated_as_protected),
    past its guaranteed period (t >= start_slot + tau_k) and 60 H_k < lambda_min (seconds)."""
    k = int(lease.contract)
    if treated_as_protected(view, k):
        return False
    c = view.contracts[k]
    return t >= int(lease.start_slot) + int(c.tau_slots) and 60.0 * c.H_min < lam_min


def spare_needed(mode: str, n_exp: int, alpha: float, nu_per_day: float, lam_min: float) -> bool:
    """'always2': n_exp >= 1; 'rule': alpha < n_exp nu lambda_min / 86400 (design §3.2.6); 'off': never."""
    if mode == "off" or n_exp < 1:
        return False
    if mode == "always2":
        return True
    if mode == "rule":
        return alpha < n_exp * nu_per_day * lam_min / 86400.0
    raise PolicyError(f"redundancy: unknown mode {mode!r}; known {list(MODES)}")


def choose_spare(view: PublicView, j: int, pool: Sequence[int], major_group: Optional[str], lam_min: float,
                 L: Sequence[int], C: np.ndarray, site_perm: np.ndarray,
                 can_buy: Optional[Callable[[int, int], bool]] = None) -> Optional[tuple[int, int]]:
    """(site, contract) of a spare (§12) or None: among the pool sites whose correlation group differs
    from `major_group` (and that pass `can_buy(site, g_j)` if given), the site with the lowest
    column cost per guaranteed hour C[l, j, k] / (L_k Δs / 60) over its allowed contracts (finite C),
    ties by pi; at that site the cheapest such contract that is not exposed itself (flagged by
    treated_as_protected, or 60 H_k >= lambda_min), else the cheapest one, ties by contract index."""
    slow = view.grid.slow_min
    pos = {int(l): i for i, l in enumerate(site_perm)}
    g = view.llms[j].g

    def per_hour(l: int, k: int) -> float:
        return float(C[l, j, k]) / (int(L[k]) * slow / 60.0)

    best, best_site = INF, None
    for l in sorted((int(x) for x in pool), key=lambda x: pos.get(x, len(pos))):
        if major_group is not None and view.sites[l].group == major_group:
            continue
        ks = [k for k in view.sites[l].menu if np.isfinite(C[l, j, k])]
        if not ks:
            continue
        if can_buy is not None and not can_buy(l, g):
            continue
        v = min(per_hour(l, k) for k in ks)
        if v < best:
            best, best_site = v, l
    if best_site is None:
        return None
    ks = sorted(k for k in view.sites[best_site].menu if np.isfinite(C[best_site, j, k]))
    safe = [k for k in ks if treated_as_protected(view, k) or 60.0 * view.contracts[k].H_min >= lam_min]
    pick = min(safe or ks, key=lambda k: (per_hour(best_site, k), k))
    return best_site, int(pick)


# ---------------------------------------------------------------- the rule
class RedundancyRule:
    """N+1 headroom per group of logical slots (§12). `step(obs, book, slots)` runs after the
    execution layer's step; `on_results` takes the (key, ActionResult) pairs of its own keys from
    LeaseBook.begin. `slots` are the execution layer's logical slots (objects with `key`
    (l0, j, k, iota), `lease` (lease id, None, or a negative placeholder while a purchase is in
    flight), `ptr` and, optionally, `pool`, the X3 pool at the last purchase)."""

    def __init__(self, view: PublicView, *, mode: str = "rule", nu_per_day: Optional[float] = None,
                 zeta: float = 2.0, site_perm: Optional[np.ndarray] = None, L: Optional[Sequence[int]] = None,
                 C: Optional[np.ndarray] = None):
        if mode not in MODES:
            raise PolicyError(f"redundancy: unknown mode {mode!r}; known {list(MODES)}")
        self.view, self.mode, self.zeta = view, mode, float(zeta)
        self.nu = float(default_nu_per_day() if nu_per_day is None else nu_per_day)
        if not self.nu >= 0:
            raise PolicyError(f"redundancy: nu_per_day must be >= 0, got {nu_per_day!r}")
        m, J, K = len(view.sites), len(view.llms), len(view.contracts)
        self.pi = np.arange(m, dtype=np.int64) if site_perm is None else np.asarray(site_perm, dtype=np.int64)
        self.L = (np.array([pd_window_slots(view, k, None) for k in range(K)], dtype=np.int64)
                  if L is None else np.asarray(L, dtype=np.int64))
        if C is None:
            C = np.full((m, J, K), INF)
            for l in range(m):
                for k in view.sites[l].menu:
                    for j in range(J):
                        C[l, j, k] = column_cost(view, l, j, k, int(self.L[k]))
        self.C = np.asarray(C, dtype=np.float64)
        self.q = np.array([x.q_usd_per_h for x in view.llms], dtype=np.float64)
        T = view.grid.T_slow
        self._pool: dict = {}          # slot key -> (lease id, pool)
        self._D_prev: Optional[np.ndarray] = None
        self._t_prev: Optional[int] = None
        self.spare: dict = {}          # group key -> {'lease', 'pending', 'site', 'contract', 'llm'}
        self.groups_with_spare = np.zeros(T, dtype=np.int64)
        self.n_exp = np.zeros(T, dtype=np.int64)
        self.n_groups = np.zeros(T, dtype=np.int64)
        self.stats = {"buys": 0, "releases": 0, "refused": 0, "deaths": 0, "no_site": 0, "buys_wide": 0}

    # -------------------------------------------------------- results
    def owns(self, key) -> bool:
        return isinstance(key, tuple) and len(key) == 2 and key[0] == SPARE_TAG

    def on_results(self, pairs) -> None:
        """Results of last slot's spare purchases: (('spare', gkey), ActionResult)."""
        for key, r in pairs:
            if not self.owns(key):
                continue
            st = self.spare.get(key[1])
            if st is None:
                continue
            st["pending"] = False
            if r.ok:
                st["lease"] = int(r.lease_id)
            else:
                self.stats["refused"] += 1

    # -------------------------------------------------------- per slot
    def _slot_pool(self, s, D_buy: np.ndarray) -> Optional[tuple[int, ...]]:
        """The slot's X3 pool at its last purchase: the execution layer's LogicalSlot.pool when it
        records one (non-empty), else x3_pool recomputed when the slot's lease changes."""
        lid = getattr(s, "lease", None)
        if lid is None:
            return None
        pool = getattr(s, "pool", None)
        if pool:
            return tuple(int(l) for l in pool)
        key = tuple(s.key)
        hit = self._pool.get(key)
        if hit is not None and hit[0] == lid:
            return hit[1]
        pool = x3_pool(self.view, key, D_buy, zeta=self.zeta, site_perm=self.pi,
                       ptr=int(getattr(s, "ptr", key[0])), L=self.L)
        self._pool[key] = (lid, pool)
        return pool

    def step(self, obs: SlowObs, book, slots: Iterable, D: Optional[np.ndarray] = None) -> None:
        """Groups, exposure and the spare decisions of slot obs.t; stages Buys and Releases in `book`.
        D is the slot's demand maxima (n,); a pool is computed with the demand of the slot of its
        lease's purchase when that is the previous slot, else with D. In mode 'off' the groups and
        exposures are counted for the report and nothing is bought."""
        view, t = self.view, obs.t
        if D is None:
            D = np.asarray(obs.demand, dtype=np.float64).max(axis=1) if obs.demand.size else np.zeros(0)
        D_buy = self._D_prev if (self._D_prev is not None and self._t_prev == t - 1) else D
        groups: dict = {}
        src: dict = {}                  # lease id -> (slot key, demand used): the stranded clients of C26
        for s in slots:
            lid = getattr(s, "lease", None)
            if lid is None or lid not in obs.leases:
                continue
            lv = obs.leases[lid]
            D_use = D_buy if lv.start_slot == t - 1 else D
            src[lv.id] = (tuple(s.key), D_use)
            pool = self._slot_pool(s, D_use)
            j = int(s.key[1])
            gk = (j, tuple(sorted(pool)))
            groups.setdefault(gk, {"pool": pool, "leases": []})["leases"].append(lv)
        # deaths of spares
        for gk, st in list(self.spare.items()):
            if st["lease"] is not None and st["lease"] not in obs.leases:
                self.stats["deaths"] += 1
                st["lease"] = None
            if st["lease"] is None and not st["pending"]:
                del self.spare[gk]
        n_exp_t = 0
        need: dict = {}
        for gk, grp in groups.items():
            j, pool = gk[0], grp["pool"]
            lam = lam_min_s(view, j, pool)
            exp = [lv for lv in grp["leases"] if is_exposed(view, lv, t, lam)]
            n_exp_t += len(exp)
            alpha = (view.llms[j].g * min(float(view.price[lv.site, lv.contract]) for lv in exp) / self.q[j]
                     if exp else INF)
            if self.mode != "off" and spare_needed(self.mode, len(exp), alpha, self.nu, lam):
                need[gk] = (pool, lam, exp)
        # releases where the condition fails
        for gk, st in self.spare.items():
            if gk in need or st["lease"] is None:
                continue
            lv = obs.leases.get(st["lease"])
            if lv is not None and t * view.grid.slow_min >= lv.prepaid_end_min:
                book.release(st["lease"])
                self.stats["releases"] += 1
                st["lease"] = None
        self.spare = {gk: st for gk, st in self.spare.items() if st["lease"] is not None or st["pending"]}
        # purchases where the condition holds and no spare is alive or pending
        pos = {int(l): i for i, l in enumerate(self.pi)}
        for gk, (pool, lam, exp) in need.items():
            if gk in self.spare:
                continue
            j = gk[0]
            count: dict = {}            # correlation group -> exposed replicas (ties: first in pi order)
            first: dict = {}
            for lv in exp:
                grp = view.sites[lv.site].group
                count[grp] = count.get(grp, 0) + 1
                first[grp] = min(first.get(grp, len(pos)), pos.get(int(lv.site), len(pos)))
            major = max(count, key=lambda x: (count[x], -first[x])) if count else None
            pick = choose_spare(view, j, pool, major, lam, self.L, self.C, self.pi,
                                can_buy=lambda l, g: book.can_buy(obs, view, l, g))
            wide = False
            if pick is None:            # C26: the wider set of the exposed slots' stranded clients
                S = {c for lv in exp for c in stranded_clients(view, *src[lv.id])}
                pick = choose_spare(view, j, wide_sites(view, S, self.pi, exclude=pool), major, lam, self.L,
                                    self.C, self.pi, can_buy=lambda l, g: book.can_buy(obs, view, l, g))
                wide = pick is not None
            if pick is None:
                self.stats["no_site"] += 1
                continue
            l, k = pick
            book.buy((SPARE_TAG, gk), Buy(l, k, j, 1, tag=SPARE_TAG, admission=1.0))
            self.spare[gk] = {"lease": None, "pending": True, "site": l, "contract": k, "llm": j}
            self.stats["buys"] += 1
            if wide:
                self.stats["buys_wide"] += 1
        if 0 <= t < len(self.n_exp):
            self.n_exp[t] = n_exp_t
            self.n_groups[t] = len(groups)
            self.groups_with_spare[t] = len(self.spare)
        self._D_prev, self._t_prev = np.asarray(D, dtype=np.float64).copy(), t

    def report(self) -> dict:
        return {"mode": self.mode, "nu_per_day": self.nu, "zeta": self.zeta, **self.stats,
                "n_exp_total": int(self.n_exp.sum()), "n_exp_max": int(self.n_exp.max(initial=0)),
                "spare_slot_groups": int(self.groups_with_spare.sum()),
                "groups_with_spare": self.groups_with_spare.tolist(), "n_exp": self.n_exp.tolist(),
                "n_groups": self.n_groups.tolist()}


__all__ = ["MODES", "SPARE_TAG", "default_nu_per_day", "x3_pool", "stranded_clients", "wide_sites", "lam_min_s",
           "is_exposed", "spare_needed", "choose_spare", "RedundancyRule"]
