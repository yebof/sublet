"""A9, notice-aware critical-ratio renting (design/sublet_v2.md §2.2, §2.3; registry id A9, online-I1).

A subclass of BL1 (baselines.greedy.GreedyLease: its SiteTable, LeaseBook, rule BR and Baseline._try_release).
It issues only Buy and Release, buys one replica per lease with admission 1 and never uses on_fast
(wants_fast false). Every threshold is a function of the PublicView; nothing is fitted. The only constants are
BL1's conventions (EPS_DEMAND, the tolerance 1e-9 of the ceiling, rule BR), the tolerance THETA_TOL of the
threshold test and the one-slot floor of the commitment rule. A9 reads the PublicView, the revealed slot (MS1
spec S14) and its own observations under I1 (notices and ends of its own leases, the results of its actions);
under I2 it ignores site_announced. Per client c (LLM j) at slow slot t:

A9.3 Contracts (reset). contracts.c2_contract_table: Rev(l), P3(l, j), the base contract kbar(l, j), the billed
     terms b_k, the usable sites with their scores sigma_cl = g_j a_{l kbar} + delta_cl < q_j, the cheapest
     flagged contract k_p(l) and C2-T2's insurance flags; cached per instance fingerprint in this process
     (contract_table, TABLE_STATS), never on disk (tests/test_policy_isolation.py). Commitment rule: a purchase
     for layer k (0-based index in the kept count) that has lain within c's kept count for A >= 1 consecutive
     slots, the current one included, may use k' in Rev(l) only if b_k' - min_{Rev(l)} b <= Δs max(1, A); among
     these it buys argmin (a_lk', b_k', k') over P3(l, j), else argmin (-H_k', a_lk', k'). An insured client
     buys only k_p at its usable flagged sites in (sigma^p, l) order.
A9.1 Target. theta_c = g_j a_{l_c kbar} / (q_j - delta_{c l_c}) with l_c the usable site of least sigma (ties by
     site id; an insured client: l_p and k_p), the break-even utilization of BL5's per-slot gain on the revealed
     slot. Layer k has utilization x_k = mean_f clip(d_c(f) - (k - 1), 0, 1) and N_c = |{k <= ceil(max_f d_c(f) -
     1e-9): x_k >= theta_c - THETA_TOL}|, 0 if max_f d_c(f) <= EPS_DEMAND; with kappa_infinite N_c = [mean_f
     d_c(f) >= theta_c - THETA_TOL] (the EPS_DEMAND test first, as in the prototypes).
A9.2 Rent-or-strand release. h_c counted leases (A9.4). If h_c <= N_c the accumulators of c are cleared and c
     keeps N_c; else for k = N_c + 1, ..., h_c: w_ck += (theta_c - x_k)^+ (q_j - delta_{c l_c}) Δs / 60 and layer k
     is kept while w_ck < kappa'_j clip(d_c(f*) - (k - 1), 0, 1), f* the last fast slot of slot t - 1 (0 at
     t = 0); the first failing layer ends the scan, and accumulators above the kept count or at most N_c are
     cleared. kappa'_j = mu^kv_j + mu^fl_j [mu^fl_j > 0, T^dr_j > 0] + mu^fb_j + pi_j W_f (guard.T0gBound.kap).
     A9 releases h_c minus the kept count of c's counted leases, highest rent rate first, then latest start, then
     highest lease id, under rule BR (GreedyLease.act's order). With kappa_infinite x_k = mean_f d_c(f) and the
     load is clip(d_c(f*), 0, 1).
A9.4 Make-before-break. For an own notice (L, r, E): u_L = timing.latest_prewarm_slot(r, E, lam^max_c, grid), or
     r if None, lam^max_c the largest load time (ms) of LLM j over c's usable sites, flagged ones included. L
     counts toward h_c at t iff t < u_L; from u_L on it is neither counted nor released by A9 and serves until
     its death, so the deficit buys the replacement at u_L. Before u_L it may be released as surplus by A9.2.
A9.5 Ski-rental site marking. An own notice at l, or an end of an own lease at l with cause 'reclaim' or
     'violation' without an earlier notice, marks l: excess_l = 0, budget_l = max_j ell_lj, last_hit_l = t, with
     ell_lj = beta~_{j l kbar} + [60 H_kbar < lam_jl / 1000] mu^fb_j. A non-insured client buys at the usable site,
     not refused in this slot and passing LeaseBook.can_buy, of least key sigma_cl + (beta~_{j l kbar} +
     [marked_l] ell_lj) / T_lj, T_lj = b_kbar / 60 hours; ties by the least last_hit (never hit first), then the
     site id. If every usable site of c is marked, those marks are cleared first (a phase end). Expiry: at every
     slot each counted lease of c at site l' adds (sigma_cl' - sigma_cl) Δs / 60 to excess_l of every marked l
     usable for c with sigma_cl < sigma_cl'; a site whose excess reaches its budget is unmarked.

Flags (PARAMS = GreedyLease's plus the keys below; the defaults are A9; §2.2 'Flags', §2.3):
  target         'ratio' (A9.1) | 'ceil' (BL1's ceiling, GreedyLease.target's rule with demand_stat)
  release        'ski' (A9.2) | 'now' (BL1's: keep N_c)
  contract_rule  'c2' (A9.3) | 'kstar': every purchase of a non-insured client uses the baselines' k*(l), and
                 k* replaces kbar in sigma, theta, ell and T; no commitment rule; the insurance flags are those of
                 the table (A9.3's test, unchanged)
  commit         True: the commitment rule; False: kbar(l, j)
  mbb            True (A9.4); False: a noticed lease counts until its death
  site_rule      'ski' (A9.5) | 'static' (BL1's order by (sigma, pi), no marking) | 'noticed' (NBR's: the static
                 order without the sites of own alive leases under notice; if no such site passes the checks, the
                 static order with them, as dev:skeptic/nbr.py)
  insure         True: C2-T2 insurance; False: no client is insured
  demand_lag     0; 1 acts on slot t - 1's demand (zeros at t = 0) in A9.1 and A9.2 (P5's boundary run)
  theta          'be' (A9.1) | 'cr': RCRb's theta = (g a + delta) / q with waste (theta - x)^+ q (P0 only)
  tie            'lru' (A9.5) | 'rank': ties between sites of equal key by the public layer rank in the site id
                 ('<lender>/S<i>'), then pi, in every site rule (the RCR prototype; P0 only)
At the defaults no rule reads pi or the policy's random streams, so a run does not depend on the policy seed.
A non-default value of a key that GreedyLease.PARAMS may add and A9 does not implement raises PolicyError.

Status: A9.1, A9.2, A9.4 as part of A9 and the commitment rule are HEURISTIC; P3 is a design rule; C2-T2's use
per client is HEURISTIC ('lb_react' is a grid value); A9.5 is HEURISTIC outside the T4/O1 family, and that A9
equals RR-renew there (O1-B, PROVEN for RR-renew, C3 §8) is CONJECTURE until tests/test_a9.py passes. No
competitive ratio is claimed for A9 on the full model.

Policy isolation (design/sim_spec_ms2.md §2.2): numpy, the standard library, sublet.types, sublet.timing,
sublet.algos.common and contracts, sublet.baselines.greedy; no file is read.
"""
from __future__ import annotations

import copy
import hashlib
import re
import time
from typing import Iterable, Optional

import numpy as np

from ..baselines.greedy import GreedyLease
from ..timing import latest_prewarm_slot
from ..types import INF, Buy, LeaseView, PublicView, SlowObs
from .common import EPS_DEMAND, PolicyError, lam_ms
from .contracts import c2_contract_table

THETA_TOL = 1e-12          # tolerance of the threshold test x_k >= theta_c
CEIL_TOL = 1e-9            # BL1's tolerance of the ceiling
_RANK = re.compile(r"/S(\d+)$")

# ---------------------------------------------------------------- contract table cache (A9.3)
_TABLES: dict = {}
TABLE_STATS = {"calls": 0, "hits": 0, "build_s": 0.0}     # contract_table calls, cache hits, build time


def view_fingerprint(view: PublicView) -> str:
    """sha256 over every PublicView field that c2_contract_table reads (prices, menus, contracts, LLMs, load
    times and charges, routing, stranding, grid); `information` is left out, so I1 and I2 share a table."""
    h = hashlib.sha256()
    st = view.stranding
    for a in (view.price, view.lam_s, view.beta_usd, view.beta_tilde_usd, view.client_llm,
              view.client_delta_usd_per_h, st.mu_kv_usd, st.mu_fl_usd, st.mu_fb_usd, st.pi_usd_per_min):
        x = np.ascontiguousarray(np.asarray(a, dtype=np.float64))
        h.update(repr(x.shape).encode())
        h.update(x.tobytes())
    h.update(repr((view.grid, view.contracts, view.llms,
                   [(s.id, s.kind, s.region, tuple(int(k) for k in s.menu)) for s in view.sites],
                   float(st.W_f_min), view.units_per_replica, float(view.q_gpu_usd_per_h), bool(view.kappa_infinite),
                   view.billing)).encode())
    return h.hexdigest()


def contract_table(view: PublicView, insure: bool = True) -> dict:
    """contracts.c2_contract_table(view, insure), cached per (view_fingerprint, insure) in this process (the masks
    and the insurance test are slow; a disk cache is ruled out by the isolation rules). The arrays of a cached
    table are read-only; callers copy what they change."""
    key = (view_fingerprint(view), bool(insure))
    TABLE_STATS["calls"] += 1
    tab = _TABLES.get(key)
    if tab is not None:
        TABLE_STATS["hits"] += 1
        return tab
    t0 = time.perf_counter()
    tab = c2_contract_table(view, insure=bool(insure))
    for v in tab.values():
        if isinstance(v, np.ndarray):
            v.setflags(write=False)
    TABLE_STATS["build_s"] += time.perf_counter() - t0
    _TABLES[key] = tab
    return tab


def public_rank(site_id: str) -> int:
    """The public layer rank i of a layer site id '<lender>/S<i>'; 0 for other sites."""
    mm = _RANK.search(site_id)
    return int(mm.group(1)) if mm else 0


# ---------------------------------------------------------------- policy A9
class NoticeCriticalRatio(GreedyLease):
    """A9 (online-I1): critical-ratio renting with the C2/O1 revocation layer (module docstring)."""
    name = "A9"
    OWN_PARAMS = {"demand_lag": 0, "target": "ratio", "release": "ski", "contract_rule": "c2", "commit": True,
                  "mbb": True, "site_rule": "ski", "insure": True, "theta": "be", "tie": "lru"}
    PARAMS = {**GreedyLease.PARAMS, **OWN_PARAMS}
    GREEDY_USED = ("defer_release", "demand_stat", "site_order")     # GreedyLease keys that A9 reads

    def _validate(self) -> None:
        super()._validate()
        p = self._params
        self._choice("target", ("ratio", "ceil"))
        self._choice("release", ("ski", "now"))
        self._choice("contract_rule", ("c2", "kstar"))
        self._choice("site_rule", ("ski", "static", "noticed"))
        self._choice("theta", ("be", "cr"))
        self._choice("tie", ("lru", "rank"))
        for name in ("commit", "mbb", "insure"):
            if not isinstance(p[name], (bool, np.bool_)):
                raise PolicyError(f"{type(self).__name__}: {name} must be true or false, got {p[name]!r}")
        lag = p["demand_lag"]
        if isinstance(lag, bool) or lag not in (0, 1):
            raise PolicyError(f"{type(self).__name__}: demand_lag must be 0 or 1, got {lag!r}")
        for k, v in GreedyLease.PARAMS.items():
            if k not in self.GREEDY_USED and k not in self.OWN_PARAMS and p[k] != v:
                raise PolicyError(f"{type(self).__name__}: option {k!r} of GreedyLease is not implemented by A9; "
                                  f"only its default {v!r} is allowed")

    # -------------------------------------------------------- reset
    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        p = self._params
        st = self.sites
        m, J, n = len(view.sites), len(view.llms), self.n
        price = np.asarray(view.price, dtype=np.float64)
        slow = view.grid.slow_min
        self.Ds_h = slow / 60.0
        self.phi = view.grid.phi
        tab = contract_table(view, bool(p["insure"]))
        self.table = tab
        self.insured = np.array(tab["insured"], dtype=bool) if p["insure"] else np.zeros(n, dtype=bool)
        self.b_min = np.array(tab["b_min"], dtype=np.float64)
        self.kp = np.array(tab["kp"], dtype=np.int64)
        self.sigma_p = np.array(tab["sigma_p"], dtype=np.float64)
        if p["contract_rule"] == "c2":
            self.kb = np.array(tab["kbar"], dtype=np.int64)
            self.sigma = np.array(tab["sigma"], dtype=np.float64)
        else:
            self.kb = np.repeat(np.asarray(st.kstar, dtype=np.int64)[:, None], J, axis=1)
            self.sigma = np.where(st.usable, st.score, INF)
        self.usable = np.isfinite(self.sigma)
        self.rev = [[int(k) for k in np.flatnonzero(tab["rev"][l])] for l in range(m)]
        self.p3 = tab["p3"]
        g, q, cl, delta = st.g, st.q, st.cl_llm, st.delta
        # A9.1: theta_c at l_c (insured: l_p, k_p) and the waste rate per unit of (theta - x)^+ (USD per hour)
        self.l_c = np.full(n, -1, dtype=np.int64)
        self.theta = np.full(n, INF)
        self.waste_rate = np.zeros(n)
        for c in range(n):
            j = int(cl[c])
            if self.insured[c]:
                l = int(tab["lp"][c])
                k = int(self.kp[l]) if l >= 0 else -1
            else:
                l = int(np.argmin(self.sigma[c])) if self.usable[c].any() else -1
                k = int(self.kb[l, j]) if l >= 0 else -1
            if l < 0 or k < 0:
                continue
            self.l_c[c] = l
            a, dl = float(price[l, k]), float(delta[c, l])
            if p["theta"] == "be":
                self.theta[c] = g[j] * a / (q[j] - dl)
                self.waste_rate[c] = q[j] - dl
            else:
                self.theta[c] = (g[j] * a + dl) / q[j]
                self.waste_rate[c] = q[j]
        # A9.2: kappa'_j per client (guard.T0gBound.kap)
        s = view.stranding
        Tdr = np.array([x.T_dr_s for x in view.llms], dtype=np.float64)
        mu_fl = np.asarray(s.mu_fl_usd, dtype=np.float64)
        kap = (np.asarray(s.mu_kv_usd, dtype=np.float64) + np.where((mu_fl > 0) & (Tdr > 0), mu_fl, 0.0)
               + np.asarray(s.mu_fb_usd, dtype=np.float64)
               + np.asarray(s.pi_usd_per_min, dtype=np.float64) * float(s.W_f_min))
        self.kap = kap[cl] if n else np.zeros(0)
        # A9.4: lam^max_c over the usable sites, flagged ones included (ms)
        self.lam = lam_ms(view)
        flag_ok = np.isfinite(self.sigma_p)
        self.lam_c = np.array([int(max((int(self.lam[int(cl[c]), l]) for l in
                                        np.flatnonzero(self.usable[c] | flag_ok[c])), default=0))
                               for c in range(n)], dtype=np.int64)
        # A9.5: per (site, LLM) beta~, ell and the billed term T (hours) of the base contract; site budgets
        bt = np.asarray(view.beta_tilde_usd, dtype=np.float64)
        mu_fb = np.asarray(s.mu_fb_usd, dtype=np.float64)
        self.bt0 = np.zeros((m, J))
        self.ell = np.zeros((m, J))
        self.T_h = np.ones((m, J))
        for l in range(m):
            for j in range(J):
                k = int(self.kb[l, j])
                if k < 0:
                    continue
                self.bt0[l, j] = bt[j, l, k]
                self.ell[l, j] = bt[j, l, k] + (mu_fb[j] if 60000 * int(view.contracts[k].H_min) < self.lam[j, l]
                                                else 0.0)
                self.T_h[l, j] = self.b_min[k] / 60.0
        self.site_budget = self.ell.max(axis=1) if J else np.zeros(m)
        self.prank = np.array([public_rank(x.id) for x in view.sites], dtype=np.int64)
        self.pirank = np.asarray(st.rank, dtype=np.int64)
        # candidate sites: A9.5 (usable, by id), the static order (BL1's), the insured order (sigma^p, l)
        self.cands = [[int(l) for l in np.flatnonzero(self.usable[c])] for c in range(n)]
        rank = p["tie"] == "rank"
        self.order_static = [sorted(self.cands[c], key=lambda l, c=c: (self.sigma[c, l],) + (
            (int(self.prank[l]), int(self.pirank[l])) if rank else (int(self.pirank[l]),))) for c in range(n)]
        self.order_p = [sorted((int(l) for l in np.flatnonzero(flag_ok[c])), key=lambda l, c=c: (self.sigma_p[c, l], l))
                        for c in range(n)]
        # state
        self.marked = np.zeros(m, dtype=bool)
        self.excess = np.zeros(m)
        self.budget = np.zeros(m)
        self.last_hit = np.full(m, -1, dtype=np.int64)
        self.acc: list[dict] = [dict() for _ in range(n)]
        self.age = [np.zeros(0, dtype=np.int64) for _ in range(n)]
        self.u: dict[int, int] = {}                  # own noticed lease id -> u_L
        self.noticed: dict[int, Optional[int]] = {}  # noticed lease id -> its site (alive leases, and this slot's ends)
        self.client_of: dict[int, int] = {}
        self.site_of: dict[int, int] = {}
        self.d_prev = np.zeros((n, self.phi))        # demand of slot t - 1 (zeros before slot 0)
        self._counted: list[list[int]] = [[] for _ in range(n)]
        self.stats = {"marks": 0, "phase_ends": 0, "mark_expiries": 0, "notices": 0, "commit_fallbacks": 0,
                      "commit_no_p3": 0, "guard_released": 0, "contracts": {}}

    # -------------------------------------------------------- A9.1, A9.2
    def _demand(self, obs: SlowObs) -> np.ndarray:
        """(n, phi) the demand A9 acts on: the revealed slot t, or slot t - 1 with demand_lag 1."""
        if self._params["demand_lag"]:
            return self.d_prev
        return np.asarray(obs.demand, dtype=np.float64)

    def base_target(self, d: np.ndarray) -> np.ndarray:
        """(n,) N_c of A9.1 on the demand d (n, phi); target 'ceil': BL1's ceiling (GreedyLease.target's rule)."""
        if self._params["target"] == "ceil":
            D = d.max(axis=1) if self._params["demand_stat"] == "max" else d.mean(axis=1)
            if self.kinf:
                return (D > EPS_DEMAND).astype(np.int64)
            return np.maximum(np.ceil(D - CEIL_TOL), 0).astype(np.int64)
        N = np.zeros(self.n, dtype=np.int64)
        for c in range(self.n):
            dc, th = d[c], float(self.theta[c])
            if dc.size == 0 or dc.max() <= EPS_DEMAND or not np.isfinite(th):
                continue
            if self.kinf:
                N[c] = int(float(dc.mean()) >= th - THETA_TOL)
                continue
            top = int(np.ceil(dc.max() - CEIL_TOL))
            x = np.clip(dc[None, :] - np.arange(top)[:, None], 0.0, 1.0).mean(axis=1)
            N[c] = int(np.sum(x >= th - THETA_TOL))
        return N

    def target(self, obs: SlowObs, h: Optional[Iterable[int]] = None) -> np.ndarray:
        """(n,) the kept count of each client: A9.1's N_c, then A9.2's scan of the surplus layers (release 'ski').
        h: counted leases per client (default: the counts that act recorded for this slot; zeros after reset).
        Updates the accumulators, so act calls it once per slot."""
        d = self._demand(obs)
        Nb = self.base_target(d)
        if self._params["release"] == "now":
            return Nb
        hh = [len(x) for x in self._counted] if h is None else [int(v) for v in h]
        f_last = self.d_prev[:, -1] if self.phi else np.zeros(self.n)
        out = Nb.copy()
        for c in range(self.n):
            hc, Nc = hh[c], int(Nb[c])
            acc = self.acc[c]
            if hc <= Nc:
                acc.clear()
                continue
            keep = Nc
            th = float(self.theta[c])
            if np.isfinite(th):
                dc = d[c]
                for k in range(Nc + 1, hc + 1):
                    if self.kinf:
                        x = float(dc.mean()) if dc.size else 0.0
                        load = min(1.0, max(0.0, float(f_last[c])))
                    else:
                        x = float(np.clip(dc - (k - 1), 0.0, 1.0).mean()) if dc.size else 0.0
                        load = min(1.0, max(0.0, float(f_last[c]) - (k - 1)))
                    w = acc.get(k, 0.0) + max(0.0, th - x) * self.waste_rate[c] * self.Ds_h
                    if w < self.kap[c] * load:
                        acc[k] = w
                        keep = k
                    else:
                        break
            for k in list(acc):
                if k > keep or k <= Nc:
                    acc.pop(k)
            out[c] = keep
        return out

    # -------------------------------------------------------- A9.3
    def commit_allowed(self, l: int, A: int) -> list[int]:
        """The contracts of Rev(l) that the commitment rule allows for a layer of age A: b_k - min_{Rev(l)} b <=
        Δs max(1, A), in index order."""
        rev = self.rev[int(l)]
        if not rev:
            return []
        bmin = min(self.b_min[k] for k in rev)
        return [k for k in rev if self.b_min[k] - bmin <= self.slow_min * max(1, int(A))]

    def commit_contract(self, l: int, j: int, A: int) -> tuple[int, bool]:
        """(contract, from_p3) of the commitment rule at site l for LLM j and a layer of age A: argmin (a, b, k)
        over the allowed contracts in P3(l, j), else argmin (-H, a, k) over the allowed ones (from_p3 False)."""
        ok = self.commit_allowed(l, A)
        pr = self.view.price
        p3 = [k for k in ok if self.p3[l, j, k]]
        if p3:
            return int(min(p3, key=lambda k: (float(pr[l, k]), self.b_min[k], k))), True
        return int(min(ok, key=lambda k: (-int(self.view.contracts[k].H_min), float(pr[l, k]), k))), False

    def _buy(self, key, site: int, llm: int, tag: str, layer: int = 0) -> None:
        """Stage one single-replica Buy for client `key` at `site` (A9.3's contract); `layer` is the 0-based
        index of the layer in the client's kept count (its age drives the commitment rule)."""
        c, l, j = int(key), int(site), int(llm)
        p = self._params
        if self.insured[c]:
            k = int(self.kp[l])
        elif p["contract_rule"] == "kstar":
            k = int(self.sites.kstar[l])
        else:
            k = int(self.kb[l, j])
            if p["commit"]:
                A = int(self.age[c][layer]) if layer < self.age[c].size else 0
                k2, from_p3 = self.commit_contract(l, j, A)
                if k2 != k:
                    self.stats["commit_fallbacks"] += 1
                if not from_p3:
                    self.stats["commit_no_p3"] += 1
                k = k2
        self.book.buy(c, Buy(l, k, j, 1, tag=tag))
        self.counts["buys"] += 1
        cid = self.view.contracts[k].id
        self.stats["contracts"][cid] = self.stats["contracts"].get(cid, 0) + 1

    # -------------------------------------------------------- A9.5
    def _mark(self, l: int, t: int) -> None:
        self.marked[l] = True
        self.excess[l] = 0.0
        self.budget[l] = self.site_budget[l]
        self.last_hit[l] = int(t)
        self.stats["marks"] += 1

    def site_key(self, c: int, l: int) -> tuple:
        """A9.5's order of site l for client c: (sigma + (beta~ + [marked] ell) / T, tie) with tie (last_hit, l)
        ('lru') or (public rank, pi rank) ('rank')."""
        j = int(self.sites.cl_llm[c])
        v = self.sigma[c, l] + (self.bt0[l, j] + (self.ell[l, j] if self.marked[l] else 0.0)) / self.T_h[l, j]
        if self._params["tie"] == "lru":
            return (v, int(self.last_hit[l]), int(l))
        return (v, int(self.prank[l]), int(self.pirank[l]))

    def _expire(self, obs: SlowObs) -> None:
        """Mark expiry of A9.5 on this slot's counted leases."""
        ml = np.flatnonzero(self.marked)
        if not ml.size:
            return
        for c in range(self.n):
            sc, ok = self.sigma[c], self.usable[c]
            for lid in self._counted[c]:
                s1 = sc[int(obs.leases[lid].site)]
                if not np.isfinite(s1):
                    continue
                for l in ml:
                    if ok[l] and sc[l] < s1:
                        self.excess[l] += (s1 - sc[l]) * self.Ds_h
        done = ml[self.excess[ml] >= self.budget[ml]]
        if done.size:
            self.marked[done] = False
            self.stats["mark_expiries"] += int(done.size)

    def _site(self, c: int, obs: SlowObs, excl: set) -> Optional[int]:
        """The site of client c's next purchase, or None (module docstring, A9.3 and A9.5)."""
        gp = int(self.sites.g[self.sites.cl_llm[c]])

        def fits(l: int) -> bool:
            return l not in self.unavail and self.book.can_buy(obs, self.view, l, gp)

        if self.insured[c]:
            return next((l for l in self.order_p[c] if fits(l)), None)
        rule = self._params["site_rule"]
        if rule == "ski":
            cand = self.cands[c]
            if not cand:
                return None
            if all(self.marked[l] for l in cand):
                self.marked[cand] = False
                self.stats["phase_ends"] += 1
            return next((l for l in sorted(cand, key=lambda l: self.site_key(c, l)) if fits(l)), None)
        order = self.order_static[c]
        if rule == "noticed" and excl:
            l = next((l for l in order if l not in excl and fits(l)), None)
            if l is not None:
                return l
        return next((l for l in order if fits(l)), None)

    # -------------------------------------------------------- one slot
    def _observe(self, obs: SlowObs) -> None:
        """Notices (u_L, marks) and ends (marks) of own leases."""
        t, ski = obs.t, self._params["site_rule"] == "ski"
        for nt in obs.notices:
            lid = int(nt.lease_id)
            L: Optional[LeaseView] = obs.leases.get(lid)
            site = int(L.site) if L is not None else self.site_of.get(lid)
            self.noticed[lid] = site
            c = self.client_of.get(lid)
            if c is not None:
                self.stats["notices"] += 1
                v = latest_prewarm_slot(int(nt.r_slot), int(nt.death_min), int(self.lam_c[c]), self.view.grid)
                self.u[lid] = int(nt.r_slot) if v is None else int(v)
            if ski and site is not None:
                self._mark(site, t)
        for lid, _end, cause in obs.ended:
            lid = int(lid)
            if ski and cause in ("reclaim", "violation") and lid not in self.noticed and lid in self.site_of:
                self._mark(self.site_of[lid], t)
        self.noticed = {k: v for k, v in self.noticed.items() if k in obs.leases}
        self.u = {k: v for k, v in self.u.items() if k in obs.leases}

    def act(self, obs: SlowObs) -> list:
        t, p = obs.t, self._params
        for c, r in self._begin(obs):
            if r.ok:
                lid = int(r.lease_id)
                self.held[c].append(lid)
                self.client_of[lid] = int(c)
                self.site_of[lid] = int(r.action.site)
        self._observe(obs)
        # a lease that ended with cause 'release' without A9 releasing it was released by a guard around A9 (A8P's
        # K0 or a projected list, §2.4 step 1): neither a death nor a mark
        by_guard = {int(lid) for lid, _end, cause in obs.ended if cause == "release"} - self._released
        for c in range(self.n):
            alive = []
            for lid in self.held[c]:
                if lid in obs.leases:
                    alive.append(lid)
                else:
                    if lid in by_guard:
                        self._released.add(lid)
                        self.stats["guard_released"] += 1
                    self._gone(lid, obs)
            self.held[c] = alive
            self._counted[c] = [lid for lid in alive if not (p["mbb"] and lid in self.u and t >= self.u[lid])]
        if p["site_rule"] == "ski":
            self._expire(obs)
        N = self.target(obs)
        for c in range(self.n):                      # ages of the layers within the kept count (commitment rule)
            old, K = self.age[c], int(N[c])
            nw = np.zeros(K, dtype=np.int64)
            kk = min(old.size, K)
            nw[:kk] = old[:kk]
            self.age[c] = nw + 1
        # releases: the surplus of the counted leases, highest rent rate first, then latest start (rule BR)
        for c in range(self.n):
            cnt = self._counted[c]
            order = sorted(cnt, key=lambda lid: (-self.sites.rent_rate(obs.leases[lid]),
                                                 -obs.leases[lid].start_min, -lid))
            surplus = set(order[:max(0, len(cnt) - int(N[c]))])
            for lid in order:
                if lid not in surplus:
                    self._not_deferred(lid)
                elif self._try_release(obs, obs.leases[lid]):
                    self.held[c].remove(lid)
                    cnt.remove(lid)
        # purchases: the deficit, one lease per replica
        excl = ({s for s in self.noticed.values() if s is not None} if p["site_rule"] == "noticed" else set())
        for c in range(self.n):
            j = int(self.sites.cl_llm[c])
            h0 = len(self._counted[c])
            for i in range(int(N[c]) - h0):
                l = self._site(c, obs, excl)
                if l is None:
                    break
                self._buy(c, l, j, f"a9:{c}", layer=h0 + i)
        self.d_prev = np.array(obs.demand, dtype=np.float64)
        return self.book.assemble(obs, self.view)

    def report(self) -> dict:
        out = super().report()
        if not hasattr(self, "stats"):
            return out
        out["a9"] = {**copy.deepcopy(self.stats), "insured": int(self.insured.sum()),
                     "insured_flags": [bool(x) for x in self.insured], "marked_at_end": int(self.marked.sum()),
                     "theta": [float(x) if np.isfinite(x) else None for x in self.theta],
                     "site_c": [int(x) for x in self.l_c],
                     "c2": copy.deepcopy(self.table["c2"])}
        return out


__all__ = ["NoticeCriticalRatio", "contract_table", "view_fingerprint", "public_rank", "TABLE_STATS", "THETA_TOL"]
