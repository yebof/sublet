"""Cohort MILP for OPT(sigma, omega), OPT_eager, the LP lower bound and slow_lb
(design/sim_spec.md §8).

The bench model (§8.1) is the engine's model on a bench grid (rule T10), restricted to the
plan class P1: every lease carries one replica of one LLM, loaded at purchase and never
reloaded, and is released only at decision slots (bench slots that start a slow slot).

Variables per usable triple u = (site l, LLM j, contract k):
  n_u(s)       leases bought at start s (integer);
  e_kap(t)     leases of cohort kap held past s + A_u, the extension pool (integer, rent);
and per client c, site l and bench slot t:
  z_cl(t)      routed fraction of the demand (continuous);
  y_cl(t), w_c(t)  persisting load moved away from l / to fallback (stranding, §5.6).

Hold pools. §8.2 models releases inside the rent-free hold region G_u(s) = [s + Lambda_u,
min(s + A_u, E_u(s))) with per-start hold variables eta_u(s, t), created where such a release can
matter (finite capacity, or on the fast grid a hold region that ends between decision slots;
§8.2's omission rule). For a triple where that rule creates any eta, this module uses an exact
aggregate instead (the reformulation R2 of the MS1 review): per cohort kap one pool
  p_kap(t), t in [P0_kap, E_kap), P0_kap = min_{s in kap} (s + Lambda_u)   (integer),
holding the cohort's warm leases, with inflow n_u(s) at s + Lambda_u and releases at decision
slots only (rows (C0p), the analogue of (C1)); the pool replaces both eta and e of the triple.
Within a cohort all leases die together and are equally warm, and a later start has a later
end of its rent-free region, so releasing the earliest start first (FIFO) is optimal; the held
set is then the latest arrivals, and the rent-bearing count is (p_kap(t) - F_kap(t))^+ with
F_kap(t) = sum of n_u(s) over the members with s + Lambda_u <= t < s + A_u. A continuous
  rho_kap(t) >= p_kap(t) - F_kap(t), rho >= 0   (rows (C0r)), cost r_u,
carries the rent at the rent-bearing slots t in [A0_kap, E_kap) (A0_kap = min_s (s + A_u); in
slow_lb only up to the cohort's last fully rent-bearing slot) where some member is in its hold
region; at the other rent-bearing slots the pool itself pays r_u. The FIFO split of an integral
or fractional pool solution is a solution of §8.2's model with the same cost, and aggregating a
solution of §8.2's model gives a pool solution of no larger cost, so the MILP and the LP optimum
are those of §8.2 (with Propositions M4 and M5 unchanged); plan extraction releases FIFO from
each pool.

Core mode (`solve_core`, §8.3) builds the same lease structure from a core.Instance-like
object, with unit requests and an explicit fallback variable per request.

Creation sets: y_cl(t) exists for (c, l, t) with z, t >= 1, hat d_c(t) > 0 and mu_kv > 0, and
w_c(t) for t >= 1 with hat d_c(t) > 0, mu_fb > 0 and some routing arc of c (elsewhere the
right-hand side of (C5)-(C6) is <= 0 and the variable would be 0). estimate_size counts the
same sets. The rows (C0p), (C0r), (C1)-(C6) form one constraint matrix with per-row bounds
(lb = ub = 0 for the equality rows of (C0p) and (C1) at non-decision slots), which HiGHS
receives as is.

The discretization here is independent of opt/dp.py (§2.2); deaths and cohorts come from
sublet.reclaim. Reference theory code is not imported.
"""
from __future__ import annotations

import gc
import os
import resource
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Optional

import numpy as np
import scipy.sparse as sp
from scipy.optimize import Bounds, LinearConstraint, milp

from .. import reclaim
from ..types import (BenchGrid, Contract, Instance, PlannedLease, Schedule, SolveResult,
                     TimeGrid)

# Ledger component names of §5.6 (ledger.COMPONENTS); repeated here so that opt/ does not
# depend on the engine package.
COMPONENTS = ("lease_prepaid", "lease_rent", "loading", "routing", "fallback",
              "stranding_kv", "stranding_fl", "stranding_fb", "stranding_pi")
GRIDS = ("slow", "fast", "slow_lb")


class SizeError(ValueError):
    """The model has more variables than `max_vars` or an estimated peak above `mem_budget_mb` (§8.9)."""


# Memory estimates (§8.7, §10 S36): peak MB = intercept + b * nnz, with b = 1.1 times the largest
# (peak_rss_mb - intercept) / nnz over the measured cases of code/sim/out/mem_bench/*.json with
# status ok (the run of 2026-10-16 at HEAD 61d98b8 with the MS1 fixes uncommitted, env.git dirty),
# rounded up at two significant digits; the factor 1.1 keeps reruns whose peaks move by a few MB
# inside the rule.
# LP, intercept 130: e1_lp_1d_slow 4.354e-4, e1_lp_2d_slow 4.666e-4, e1_lp_1d_fast 3.861e-4,
# e7s_lp_1d_slow 4.605e-4, e7s_lp_2d_slow 4.429e-4, e7r_lp_1d_slow 4.851e-4 (the maximum: 1883.2 MB
# at 3,613,941 nonzeros) -> 1.1 * 4.851e-4 = 5.34e-4 -> 5.4e-4. MILP and OPT_eager, intercept 400:
# e1_milp_1d_slow 1.827e-3, e1_milp_2d_slow 1.676e-3, e1_milp_1d_fast 1.255e-3, e1_eager_1d_fast
# 5.697e-4, e1_eager_1d_slow 2.454e-3 (the maximum: 1343.7 MB at 384,521 nonzeros)
# -> 1.1 * 2.454e-3 = 2.70e-3 -> 2.7e-3.
EST_LP_MB0, EST_LP_MB_PER_NNZ = 130.0, 5.4e-4
EST_MILP_MB0, EST_MILP_MB_PER_NNZ = 400.0, 2.7e-3
MEM_BUDGET_MB = 2500.0       # default gate of solve_opt (§8.9): under the 3G cap with room for the caller


# ============================================================================ index sets
@dataclass(eq=False)
class _Triple:
    """Lease structure of one usable triple u = (l, j, k) on the bench grid."""
    l: int
    j: int
    k: int
    g: int
    lam: int            # loading length Lambda_u in bench slots
    A: int              # forced length max(billed term, Lambda_u) in bench slots
    rent: float         # rent of one lease per bench slot (pool slots)
    prepaid: float      # minimum billed term charged at purchase (g a P_k / 60)
    beta: float         # loading charge per lease
    load_rent: float    # rent of loading slots beyond the billed term, charged at purchase
    s: np.ndarray       # slow start slots of S_u, increasing
    sb: np.ndarray      # bench index of each start
    E: np.ndarray       # bench death of each start (its cohort's death)
    coh: np.ndarray     # cohort index of each start
    coh_E: np.ndarray   # death of each cohort
    coh_X0: np.ndarray  # first slot of the extension region X_kap (empty if >= coh_E)
    coh_full: np.ndarray  # pool slots t < coh_full carry `rent`, later ones 0 (slow_lb)
    eta: np.ndarray     # per start: §8.2's omission rule would create hold variables
    coh_lo: np.ndarray  # first start index of each cohort (members are consecutive starts)
    coh_hi: np.ndarray  # one past the last start index of each cohort
    # variable layout (set by the builder)
    n0: int = 0
    coh_e0: Optional[np.ndarray] = None   # extension pool e of each cohort (unpooled triples)
    coh_p0: Optional[np.ndarray] = None   # hold pool p of each cohort (pooled triples)

    @property
    def pooled(self) -> bool:
        """Releases inside the hold region are modelled (§8.2), by the hold pools of this
        module: per cohort one pool p over [P0, E) in place of eta and e."""
        return bool(self.eta.any())

    @property
    def coh_P0(self) -> np.ndarray:
        """First slot of each cohort's hold pool: its first member's s + Lambda_u."""
        return self.sb[self.coh_lo] + self.lam if len(self.coh_lo) else np.zeros(0, np.int64)

    @property
    def G_start(self) -> np.ndarray:
        return self.sb + self.lam

    @property
    def G_end(self) -> np.ndarray:
        return np.minimum(self.sb + self.A, self.E)

    @property
    def charge(self) -> float:
        return self.beta + self.prepaid + self.load_rent


@dataclass(eq=False)
class _Bench:
    """Index sets of one bench model (§8.2, §8.3, §8.6)."""
    mode: str           # 'full' (C3 with capacity 1), 'kinf' (kappa_infinite), 'core'
    grid: str           # 'slow' | 'fast' | 'slow_lb' | 'core'
    Tb: int             # bench slots
    phib: int           # bench slots per slow slot (decision slots: t % phib == 0)
    hours: float        # bench slot length in hours (1 in core mode: costs are per slot)
    cap: np.ndarray     # (m,) site capacity in GPUs, inf = unlimited
    triples: list
    d: np.ndarray       # (n, Tb) bench demand (core: activity as 0/1)
    jc: np.ndarray      # (n,) LLM of each client
    q: np.ndarray       # (n,) fallback cost per load-hour (core: per request)
    delta: np.ndarray   # (n, m) routing cost
    allowed: np.ndarray  # (n, m) bool: routing arcs (c, l)
    mu_kv: np.ndarray   # (n,) per client; 0 where no y variables
    mu_fb: np.ndarray   # (n,)
    n_ub: float         # upper bound of n (1 in core mode)


def _ceil_div(a, b):
    return -(-a // b)


def _deaths(R: np.ndarray, n_starts: int, c: Contract, tg: TimeGrid, bench: str) -> np.ndarray:
    """Bench death E_b (rule T10) of a lease bought at every slow slot 0..n_starts-1, from
    reclaim.cohorts (the one implementation of the reclaim rule)."""
    E = np.empty(n_starts, dtype=np.int64)
    starts = np.arange(n_starts, dtype=np.int64)
    for Eb, part in reclaim.cohorts(np.asarray(R, dtype=np.int64), starts, c, tg, bench):
        E[part] = Eb
    return E


def _group(E_key: np.ndarray):
    """Cohorts of consecutive starts with equal death key: (cohort index per start, index of
    the first start of each cohort). E_key is non-decreasing in the start (§3.3)."""
    if len(E_key) == 0:
        return np.zeros(0, np.int64), np.zeros(0, np.int64)
    new = np.ones(len(E_key), dtype=bool)
    new[1:] = E_key[1:] != E_key[:-1]
    coh = np.cumsum(new) - 1
    first = np.flatnonzero(new)
    return coh.astype(np.int64), first


def _bench_instance(inst: Instance, sched: Schedule, grid: str, refuse_unavailable: bool,
                    refuse_sched: Optional[Schedule]) -> _Bench:
    """Index sets of the full mode (§8.2) or of slow_lb (§8.6) for an Instance."""
    if grid not in GRIDS:
        raise ValueError(f"unknown bench grid {grid!r}; expected one of {GRIDS}")
    if not sched.realized:
        raise ValueError("schedule is not realized (adaptive before the run): no valid omega")
    if len(sched.R) != inst.m:
        raise ValueError(f"schedule has {len(sched.R)} sites, instance {inst.m}")
    tg = inst.grid
    Ts, phi = tg.T_slow, tg.phi
    lb_mode = grid == "slow_lb"
    db = tg.bench_min(grid)                 # bench slot length in minutes
    Tb = tg.T_bench(grid)
    phib = tg.slow_min // db
    m, J = inst.m, inst.J
    g_j = np.array([x.g for x in inst.llms], dtype=np.int64)
    q_j = np.array([x.q_usd_per_h for x in inst.llms], dtype=float)
    cl = inst.clients
    jc = np.asarray(cl.llm, dtype=np.int64)
    delta = np.asarray(cl.delta_usd_per_h, dtype=float)
    q_c = q_j[jc]
    lam_ms = inst.lam_ms()
    cap = np.array([s.capacity_gpus for s in inst.sites], dtype=float)
    finite_cap = np.isfinite(cap)

    # usable (l, j): some client of j with delta < q_j (§8.2)
    good = delta < q_c[:, None]                       # INF < q is False
    lj_used = np.zeros((m, J), dtype=bool)
    for c in range(cl.n):
        lj_used[good[c], jc[c]] = True
    has_menu = np.array([len(s.menu) > 0 for s in inst.sites])
    allowed = good & (lj_used.T[jc] & has_menu[None, :])

    refuse_R = None
    if refuse_unavailable:
        src = refuse_sched if refuse_sched is not None else sched
        if len(src.R) != m:
            raise ValueError("refusal schedule has a different number of sites")
        refuse_R = [np.asarray(r, dtype=np.int64) for r in src.R]

    s_all = np.arange(Ts, dtype=np.int64)
    triples = []
    for l, site in enumerate(inst.sites):
        js = np.flatnonzero(lj_used[l])
        if len(js) == 0:
            continue
        open_start = np.ones(Ts, dtype=bool)
        if refuse_R is not None and len(refuse_R[l]):
            open_start[refuse_R[l][(refuse_R[l] >= 0) & (refuse_R[l] < Ts)]] = False
        for k in site.menu:
            a = float(inst.price[l, k])
            if not np.isfinite(a):
                raise ValueError(f"contract {k} is on the menu of site {l} but has no price")
            c = inst.contracts[k]
            P = int(c.prepaid_min)
            if lb_mode:
                E_f = _deaths(sched.R[l], Ts, c, tg, "fast")
            else:
                E_all = _deaths(sched.R[l], Ts, c, tg, grid)
            for j in js:
                g = int(g_j[j])
                if lb_mode:
                    lam_f = int(_ceil_div(int(lam_ms[j, l]), 60000 * tg.fast_min))
                    P_f = int(_ceil_div(P, tg.fast_min))
                    lam = lam_f // phi
                    A = max(lam, int(_ceil_div(P_f, phi)))
                    ok = (E_f > s_all * phi + lam_f) & open_start
                    s = s_all[ok]
                    key = E_f[ok]
                    coh, first = _group(key)
                    coh_Ef = key[first]
                    coh_E = np.minimum(Ts, _ceil_div(coh_Ef, phi))
                    coh_full = coh_Ef // phi
                    r_f = g * a * tg.fast_min / 60.0
                    rent = r_f * phi
                    load_rent = r_f * max(0, min(lam_f, A * phi) - P_f)
                    sb = s
                else:
                    lam = int(_ceil_div(int(lam_ms[j, l]), 60000 * db))
                    Pb = int(_ceil_div(P, db))
                    A = max(Pb, lam)
                    sb_all = s_all * phib
                    ok = (E_all > sb_all + lam) & open_start
                    s = s_all[ok]
                    sb = sb_all[ok]
                    key = E_all[ok]
                    coh, first = _group(key)
                    coh_E = key[first]
                    coh_full = coh_E
                    rent = g * a * db / 60.0
                    load_rent = rent * max(0, lam - Pb)
                E = coh_E[coh] if len(s) else np.zeros(0, np.int64)
                coh_X0 = sb[first] + A
                G_len = np.minimum(sb + A, E) - (sb + lam)
                if finite_cap[l]:
                    eta = G_len > 0
                else:
                    eta = (G_len > 0) & ((sb + A) % phib != 0) & (sb + A < E)
                triples.append(_Triple(
                    l=l, j=int(j), k=int(k), g=g, lam=lam, A=A, rent=rent,
                    prepaid=g * a * P / 60.0, beta=float(inst.beta_usd[j, l]),
                    load_rent=load_rent, s=s, sb=sb.astype(np.int64), E=E.astype(np.int64),
                    coh=coh, coh_E=coh_E.astype(np.int64), coh_X0=coh_X0.astype(np.int64),
                    coh_full=coh_full.astype(np.int64), eta=eta,
                    coh_lo=first.astype(np.int64),
                    coh_hi=np.append(first[1:], len(s)).astype(np.int64)))

    # bench demand: mean over the fast slots of a bench slot; minimum for slow_lb
    r = db // tg.fast_min
    dem = np.asarray(cl.demand, dtype=float).reshape(cl.n, Tb, r)
    d = dem.min(axis=2) if lb_mode else dem.mean(axis=2)
    st = inst.stranding
    if lb_mode:
        mu_kv = np.zeros(cl.n)
        mu_fb = np.zeros(cl.n)
    else:
        mu_kv = np.asarray(st.mu_kv_usd, dtype=float)[jc]
        mu_fb = np.asarray(st.mu_fb_usd, dtype=float)[jc]
    mode = "kinf" if inst.kappa_infinite else "full"
    return _Bench(mode=mode, grid=grid, Tb=Tb, phib=phib, hours=db / 60.0, cap=cap,
                  triples=triples, d=d, jc=jc, q=q_c, delta=delta, allowed=allowed,
                  mu_kv=mu_kv, mu_fb=mu_fb, n_ub=np.inf)


def _bench_core(I, omega) -> _Bench:
    """Index sets of the core mode (§8.3): decision at every slot, no loading, forced window
    L_k = tau_k + H_k charged in full, deaths of core.effective_end capped at T, n <= 1."""
    T = int(I.T)
    tau = np.asarray(I.tau, dtype=np.int64)
    H = np.asarray(I.H, dtype=np.int64)
    a = np.asarray(I.a, dtype=float)
    beta = np.asarray(I.beta, dtype=float)
    g_j = np.asarray(I.g, dtype=np.int64)
    jc = np.asarray(I.cl_llm, dtype=np.int64)
    delta = np.asarray(I.delta, dtype=float)
    active = np.asarray(I.active, dtype=bool)
    m, K = a.shape
    n = len(jc)
    if len(omega) != m:
        raise ValueError(f"omega has {len(omega)} sites, core instance {m}")
    allowed = np.isfinite(delta)
    lj_used = np.zeros((m, len(g_j)), dtype=bool)          # core.Instance.lj_pairs
    for c in range(n):
        lj_used[allowed[c], jc[c]] = True
    tg = TimeGrid(1, 1, T, 0)
    s_all = np.arange(T, dtype=np.int64)
    triples = []
    for l in range(m):
        R = np.sort(np.asarray(omega[l], dtype=np.int64))
        for k in range(K):
            L = int(tau[k] + H[k])
            c = Contract(id=f"k{k}", tau_slots=int(tau[k]), H_min=int(H[k]), prepaid_min=L,
                         klass="core")
            E_all = _deaths(R, T, c, tg, "slow")
            for j in np.flatnonzero(lj_used[l]):
                g = int(g_j[j])
                ok = E_all > s_all
                s = s_all[ok]
                key = E_all[ok]
                coh, first = _group(key)
                coh_E = key[first]
                E = coh_E[coh] if len(s) else np.zeros(0, np.int64)
                triples.append(_Triple(
                    l=l, j=int(j), k=k, g=g, lam=0, A=L, rent=g * float(a[l, k]),
                    prepaid=g * float(a[l, k]) * L, beta=float(beta[j, l]), load_rent=0.0,
                    s=s, sb=s.copy(), E=E, coh=coh, coh_E=coh_E, coh_X0=s[first] + L,
                    coh_full=coh_E.copy(), eta=np.zeros(len(s), dtype=bool),
                    coh_lo=first.astype(np.int64),
                    coh_hi=np.append(first[1:], len(s)).astype(np.int64)))
    q = np.full(n, float(I.q))
    return _Bench(mode="core", grid="core", Tb=T, phib=1, hours=1.0, cap=np.full(m, np.inf),
                  triples=triples, d=active.astype(float), jc=jc, q=q, delta=delta,
                  allowed=allowed, mu_kv=np.zeros(n), mu_fb=np.zeros(n), n_ub=1.0)


# ============================================================================ helpers
def _intervals(a: np.ndarray, b: np.ndarray):
    """Enumerate the slots of the intervals [a_i, b_i): (owner index i, slot t) arrays."""
    a = np.asarray(a, dtype=np.int64)
    L = np.maximum(np.asarray(b, dtype=np.int64) - a, 0)
    own = np.repeat(np.arange(len(a), dtype=np.int64), L)
    first = np.repeat(np.cumsum(L) - L, L)
    t = np.arange(int(L.sum()), dtype=np.int64) - first + np.repeat(a, L)
    return own, t


def _cover(Tb: int, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Number of the intervals [a_i, b_i) that contain each slot 0..Tb-1."""
    a = np.asarray(a, dtype=np.int64)
    b = np.asarray(b, dtype=np.int64)
    keep = b > a
    diff = np.zeros(Tb + 1, dtype=np.int64)
    np.add.at(diff, a[keep], 1)
    np.add.at(diff, b[keep], -1)
    return np.cumsum(diff[:-1])


@dataclass(eq=False)
class _Routing:
    """Routing variables: one z per (pair p = (c, l), slot t with d_c(t) > 0)."""
    pc: np.ndarray       # (P,) client of each pair, pairs sorted by (c, l)
    pl: np.ndarray       # (P,) site of each pair
    act: list            # per client: slots with positive demand
    pos: np.ndarray      # (n, Tb) position of t in act[c], -1 if inactive
    zbase: np.ndarray    # (P,) offset of the pair's z block within the z variables
    pairs_of: list       # per client: pair indices
    N_z: int


def _routing(B: _Bench) -> _Routing:
    n = len(B.jc)
    pc, pl = np.nonzero(B.allowed)
    pc = pc.astype(np.int64)
    pl = pl.astype(np.int64)
    pos_mask = B.d > 0
    act = [np.flatnonzero(pos_mask[c]) for c in range(n)]
    pos = np.where(pos_mask, np.cumsum(pos_mask, axis=1) - 1, -1).astype(np.int64)
    nact = np.array([len(x) for x in act], dtype=np.int64)
    L = nact[pc] if len(pc) else np.zeros(0, np.int64)
    zbase = np.cumsum(L) - L
    pairs_of = [[] for _ in range(n)]
    for p, c in enumerate(pc):
        pairs_of[c].append(p)
    return _Routing(pc=pc, pl=pl, act=act, pos=pos, zbase=zbase.astype(np.int64),
                    pairs_of=pairs_of, N_z=int(L.sum()))


def _strand_slots(B: _Bench, R: _Routing, c: int) -> np.ndarray:
    """Slots t >= 1 with hat d_c(t) = min(d_c(t-1), d_c(t)) > 0."""
    t = R.act[c]
    t = t[t >= 1]
    return t[B.d[c, t - 1] > 0]


def _rss_mb() -> float:
    with open("/proc/self/statm") as f:
        pages = int(f.read().split()[1])
    return pages * os.sysconf("SC_PAGE_SIZE") / 2 ** 20


def _peak_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


@dataclass(eq=False)
class _PoolSets:
    """Index sets of the hold pools of a pooled triple (module docstring). Pool slots are
    numbered cohort by cohort, slot by slot: cohort kap owns [base[kap], base[kap] + E - P0)."""
    kp: np.ndarray        # (N_hp,) cohort of each pool slot
    tp: np.ndarray        # (N_hp,) bench slot of each pool slot
    first: np.ndarray     # (N_hp,) True at the first slot P0 of its cohort
    in_idx: np.ndarray    # (N,) pool slot at which start i arrives (t = s + Lambda_u)
    direct: np.ndarray    # rent-bearing pool slots without a member in its hold region
    rho: np.ndarray       # rent-bearing pool slots with such members: one rho each
    rho_lo: np.ndarray    # members [rho_lo, rho_hi) in their hold region at each rho slot
    rho_hi: np.ndarray


def _pool_sets(u: _Triple) -> _PoolSets:
    P0 = u.coh_P0
    kp, tp = _intervals(P0, u.coh_E)                 # E_kap > P0_kap for every cohort
    L = u.coh_E - P0
    base = np.cumsum(L) - L
    arrive = u.sb + u.lam                            # increasing in the start
    in_idx = base[u.coh] + (arrive - P0[u.coh])
    if u.rent > 0:
        A0 = u.sb[u.coh_lo] + u.A
        R1 = np.minimum(u.coh_E, u.coh_full)
        rent = np.flatnonzero((tp >= A0[kp]) & (tp < R1[kp]))
    else:
        rent = np.zeros(0, np.int64)
    t, k = tp[rent], kp[rent]
    lo_k, hi_k = u.coh_lo[k], u.coh_hi[k]
    hi = np.clip(np.searchsorted(arrive, t, side="right"), lo_k, hi_k)
    lo = np.clip(np.searchsorted(u.sb + u.A, t, side="right"), lo_k, hi_k)
    free = hi > lo
    return _PoolSets(kp=kp, tp=tp, first=tp == P0[kp], in_idx=in_idx.astype(np.int64),
                     direct=rent[~free], rho=rent[free], rho_lo=lo[free].astype(np.int64),
                     rho_hi=hi[free].astype(np.int64))


# ============================================================================ counting
def _count(B: _Bench) -> dict:
    """Exact sizes of the model of B (§8.7), from the index sets, without building it."""
    Tb = B.Tb
    R = _routing(B)
    n = len(B.jc)
    N_n = N_e = n_coh_X = n_inflow = 0
    N_hp = n_coh_hp = n_in_hp = N_rho = nnz_r = 0
    warm = defaultdict(lambda: np.zeros(Tb, dtype=np.int64))    # (j, l) -> warm terms per t
    alive = defaultdict(lambda: np.zeros(Tb, dtype=np.int64))   # l -> alive terms per t
    n_coh = 0
    for u in B.triples:
        N_n += len(u.s)
        n_coh += len(u.coh_E)
        if u.pooled:
            ps = _pool_sets(u)
            N_hp += len(ps.tp)
            n_coh_hp += len(u.coh_E)
            n_in_hp += len(u.s)
            N_rho += len(ps.rho)
            nnz_r += 2 * len(ps.rho) + int((ps.rho_hi - ps.rho_lo).sum())
            w = _cover(Tb, u.coh_P0, u.coh_E)
        else:
            XL = np.maximum(u.coh_E - u.coh_X0, 0)
            N_e += int(XL.sum())
            n_coh_X += int((XL > 0).sum())
            n_inflow += int((u.sb + u.A < u.E).sum())
            w = _cover(Tb, u.G_start, u.G_end) + _cover(Tb, u.coh_X0, u.coh_E)
        warm[(u.j, u.l)] += w
        if np.isfinite(B.cap[u.l]):
            alive[u.l] += w + _cover(Tb, u.sb, u.sb + u.lam)
    nact = np.array([len(x) for x in R.act], dtype=np.int64)
    N_z = R.N_z
    has_pair = np.array([len(p) > 0 for p in R.pairs_of], dtype=bool)
    # (C2) or the core coverage rows
    if B.mode == "core":
        N_f = int(nact.sum())
        R2, nnz2 = N_f, N_z + N_f
    else:
        N_f = 0
        R2, nnz2 = int(nact[has_pair].sum()), N_z
    # (C3) or the per-z linking rows
    R3 = nnz3 = 0
    if B.mode == "full":
        for (j, l), w in _jl_groups(B, R).items():
            tmask = np.zeros(Tb, dtype=bool)
            for p in w:
                tmask[R.act[R.pc[p]]] = True
            R3 += int(tmask.sum())
            nnz3 += int(warm[(j, l)][tmask].sum()) if (j, l) in warm else 0
        nnz3 += N_z
    else:
        for p in range(len(R.pc)):
            c, l = int(R.pc[p]), int(R.pl[p])
            R3 += len(R.act[c])
            key = (int(B.jc[c]), l)
            if key in warm:
                nnz3 += int(warm[key][R.act[c]].sum())
        nnz3 += N_z
    # (C4)
    R4 = nnz4 = 0
    for l, a in alive.items():
        R4 += int((a > 0).sum())
        nnz4 += int(a.sum())
    # (C5), (C6)
    N_y = N_w = nnz6 = 0
    for c in range(n):
        if not has_pair[c]:
            continue
        ts = None
        if B.mu_kv[c] > 0:
            ts = _strand_slots(B, R, c)
            N_y += len(ts) * len(R.pairs_of[c])
        if B.mu_fb[c] > 0:
            ts = _strand_slots(B, R, c) if ts is None else ts
            N_w += len(ts)
            nnz6 += len(ts) * (1 + 2 * len(R.pairs_of[c]))
    nnz_p = 2 * N_hp - n_coh_hp + n_in_hp
    nnz1 = 2 * N_e - n_coh_X + n_inflow
    n_vars = N_n + N_e + N_hp + N_rho + N_z + N_y + N_w + N_f
    n_rows = N_hp + N_rho + N_e + R2 + R3 + R4 + N_y + N_w
    nnz = nnz_p + nnz_r + nnz1 + nnz2 + nnz3 + nnz4 + 3 * N_y + nnz6
    parts = dict(N_n=N_n, N_hp=N_hp, N_rho=N_rho, N_e=N_e, N_z=N_z, N_y=N_y, N_w=N_w, N_f=N_f,
                 rows_C0p=N_hp, rows_C0r=N_rho, rows_C1=N_e, rows_C2=R2, rows_C3=R3, rows_C4=R4,
                 rows_C5=N_y, rows_C6=N_w,
                 nnz_C0p=nnz_p, nnz_C0r=nnz_r, nnz_C1=nnz1, nnz_C2=nnz2, nnz_C3=nnz3,
                 nnz_C4=nnz4, nnz_C5=3 * N_y, nnz_C6=nnz6,
                 n_triples=len(B.triples), n_pooled_triples=sum(u.pooled for u in B.triples),
                 n_cohorts=n_coh, n_pairs=int(len(R.pc)), T_b=Tb)
    lp_mb = EST_LP_MB0 + EST_LP_MB_PER_NNZ * nnz
    milp_mb = EST_MILP_MB0 + EST_MILP_MB_PER_NNZ * nnz
    parts["est_mb_lp"] = lp_mb
    parts["est_mb_milp"] = milp_mb
    return dict(n_vars=n_vars, n_int=N_n + N_e + N_hp, n_rows=n_rows, nnz=nnz,
                est_mb=milp_mb, parts=parts)


def _jl_groups(B: _Bench, R: _Routing) -> dict:
    """(j, l) -> list of routing pairs (c, l) with j_c = j, in pair order."""
    out = defaultdict(list)
    for p in range(len(R.pc)):
        out[(int(B.jc[R.pc[p]]), int(R.pl[p]))].append(p)
    return out


# ============================================================================ building
@dataclass(eq=False)
class _Model:
    c: np.ndarray
    const: float
    integrality: np.ndarray
    lb: np.ndarray
    ub: np.ndarray
    A: Optional[sp.csr_matrix]
    rlb: np.ndarray
    rub: np.ndarray
    blocks: dict        # block name -> (first var, count)
    comp: dict          # component -> (var indices, coefficients)
    size: dict


class _Rows:
    """Accumulates COO entries and row bounds as numpy blocks."""

    def __init__(self):
        self.r, self.c, self.v, self.lo, self.hi = [], [], [], [], []
        self.n = 0

    def new(self, k: int, lo, hi) -> np.ndarray:
        rows = np.arange(self.n, self.n + k, dtype=np.int64)
        self.lo.append(np.broadcast_to(np.asarray(lo, dtype=float), (k,)).copy())
        self.hi.append(np.broadcast_to(np.asarray(hi, dtype=float), (k,)).copy())
        self.n += k
        return rows

    def add(self, rows, cols, vals) -> None:
        rows = np.asarray(rows, dtype=np.int64)
        self.r.append(rows)
        self.c.append(np.asarray(cols, dtype=np.int64))
        self.v.append(np.broadcast_to(np.asarray(vals, dtype=float), rows.shape).copy())


def _build(B: _Bench, integral: bool) -> _Model:
    """Variables, objective, bounds and the constraint matrix (C0)-(C6) of B."""
    Tb, phib = B.Tb, B.phib
    R = _routing(B)
    n = len(B.jc)
    rows = _Rows()

    # ---- variable layout: n | e | hold pools p | rho | z | y | w | f
    off = 0
    for u in B.triples:
        u.n0 = off
        off += len(u.s)
    N_n = off
    e0 = off
    for u in B.triples:
        if u.pooled:
            u.coh_e0 = np.full(len(u.coh_E), -1, dtype=np.int64)
            continue
        L = np.maximum(u.coh_E - u.coh_X0, 0)
        u.coh_e0 = np.where(L > 0, off + np.cumsum(L) - L, -1).astype(np.int64)
        off += int(L.sum())
    N_e = off - e0
    hp0 = off
    pools = {}
    for u in B.triples:
        if u.pooled:
            ps = pools[id(u)] = _pool_sets(u)
            u.coh_p0 = off
            off += len(ps.tp)
    N_hp = off - hp0
    rho0 = off
    rho_first = {}
    for u in B.triples:
        if u.pooled:
            rho_first[id(u)] = off
            off += len(pools[id(u)].rho)
    N_rho = off - rho0
    z0 = off
    N_z = R.N_z
    off += N_z
    y_slots, w_slots = {}, {}
    for c in range(n):
        if not R.pairs_of[c]:
            continue
        if B.mu_kv[c] > 0:
            y_slots[c] = _strand_slots(B, R, c)
        if B.mu_fb[c] > 0:
            w_slots[c] = _strand_slots(B, R, c)
    y0 = off
    N_y = sum(len(t) * len(R.pairs_of[c]) for c, t in y_slots.items())
    off += N_y
    w0 = off
    N_w = sum(len(t) for t in w_slots.values())
    off += N_w
    f0 = off
    N_f = int(sum(len(a) for a in R.act)) if B.mode == "core" else 0
    off += N_f
    nv = off

    cost = np.zeros(nv)
    lb = np.zeros(nv)
    ub = np.full(nv, np.inf)
    integ = np.zeros(nv, dtype=np.uint8)
    if integral:
        integ[:rho0] = 1                    # n, e and the hold pools; rho is continuous
    ub[:N_n] = B.n_ub
    ub[z0:z0 + N_z] = 1.0
    ub[f0:f0 + N_f] = 1.0

    warm = defaultdict(lambda: ([], []))    # (j, l) -> (vars, slots) of warm terms
    alive = defaultdict(lambda: ([], [], []))   # l -> (vars, slots, GPUs) at finite sites
    n_idx, n_pre, n_beta, n_lr = [], [], [], []
    e_idx, e_rent = [], []                  # rent-bearing variables: e, pool slots, rho
    for u in B.triples:
        N = len(u.s)
        if N == 0:
            continue
        nvars = u.n0 + np.arange(N, dtype=np.int64)
        cost[nvars] = u.charge
        n_idx.append(nvars)
        n_pre.append(np.full(N, u.prepaid))
        n_beta.append(np.full(N, u.beta))
        n_lr.append(np.full(N, u.load_rent))
        # loading region F: alive, not warm
        own, tF = _intervals(u.sb, u.sb + u.lam)
        vF = u.n0 + own
        if u.pooled:
            ps = pools[id(u)]
            vP = u.coh_p0 + np.arange(len(ps.tp), dtype=np.int64)
            # (C0p) hold-pool dynamics: releases at decision slots, inflow n at s + Lambda
            r0 = rows.new(len(vP), np.where(ps.tp % phib == 0, -np.inf, 0.0), 0.0)
            rows.add(r0, vP, 1.0)
            rows.add(r0[~ps.first], vP[~ps.first] - 1, -1.0)
            rows.add(r0[ps.in_idx], nvars, -1.0)
            # rent: on the pool where no member is in its hold region, else on rho (C0r)
            vD = vP[ps.direct]
            cost[vD] = u.rent
            rv = rho_first[id(u)] + np.arange(len(ps.rho), dtype=np.int64)
            cost[rv] = u.rent
            if len(rv):
                rr = rows.new(len(rv), -np.inf, 0.0)
                rows.add(rr, rv, -1.0)
                rows.add(rr, vP[ps.rho], 1.0)
                own, mem = _intervals(ps.rho_lo, ps.rho_hi)
                rows.add(rr[own], u.n0 + mem, -1.0)
            e_idx += [vD, rv]
            e_rent += [np.full(len(vD), u.rent), np.full(len(rv), u.rent)]
            wv, wt = vP, ps.tp
        else:
            # hold region: n itself is held (alive and warm)
            own, tG = _intervals(u.G_start, u.G_end)
            vG = u.n0 + own
            # extension pools and (C1)
            cidx = np.flatnonzero(u.coh_E > u.coh_X0)
            own, tX = _intervals(u.coh_X0[cidx], u.coh_E[cidx])
            ki = cidx[own]
            vX = u.coh_e0[ki] + (tX - u.coh_X0[ki])
            if len(vX):
                rent = np.where(tX < u.coh_full[ki], u.rent, 0.0)
                cost[vX] = rent
                e_idx.append(vX)
                e_rent.append(rent)
                r1 = rows.new(len(vX), np.where(tX % phib == 0, -np.inf, 0.0), 0.0)
                rows.add(r1, vX, 1.0)
                notfirst = tX > u.coh_X0[ki]
                rows.add(r1[notfirst], vX[notfirst] - 1, -1.0)
                # inflow: leases of start s enter the pool at s + A if alive then
                ins = np.flatnonzero(u.sb + u.A < u.E)
                t_in = u.sb[ins] + u.A
                kk = u.coh[ins]
                row_in = r1[0] + (u.coh_e0[kk] + (t_in - u.coh_X0[kk]) - vX[0])
                rows.add(row_in, u.n0 + ins, -1.0)
            wv = np.concatenate([vG, vX])
            wt = np.concatenate([tG, tX])
        warm[(u.j, u.l)][0].append(wv)
        warm[(u.j, u.l)][1].append(wt)
        if np.isfinite(B.cap[u.l]):
            alive[u.l][0].append(np.concatenate([vF, wv]))
            alive[u.l][1].append(np.concatenate([tF, wt]))
            alive[u.l][2].append(np.full(len(vF) + len(wv), float(u.g)))

    def zvars(p: int) -> np.ndarray:
        return z0 + R.zbase[p] + np.arange(len(R.act[R.pc[p]]), dtype=np.int64)

    # ---- routing costs
    z_route, z_fb = np.zeros(N_z), np.zeros(N_z)
    for p in range(len(R.pc)):
        c, l = int(R.pc[p]), int(R.pl[p])
        zv = zvars(p)
        dt = B.d[c, R.act[c]]
        if B.mode == "core":
            z_route[zv - z0] = B.delta[c, l]
        else:
            z_route[zv - z0] = B.delta[c, l] * dt * B.hours
            z_fb[zv - z0] = -B.q[c] * dt * B.hours
    cost[z0:z0 + N_z] = z_route + z_fb
    if B.mode == "core":
        const = 0.0
        cost[f0:f0 + N_f] = B.q[0] if n else 0.0
    else:
        const = float((B.q * B.d.sum(axis=1)).sum() * B.hours)

    # ---- (C2) or the core coverage rows
    fpos = 0
    for c in range(n):
        na = len(R.act[c])
        if na == 0:
            continue
        if B.mode == "core":
            r2 = rows.new(na, -np.inf, -1.0)
            for p in R.pairs_of[c]:
                rows.add(r2, zvars(p), -1.0)
            rows.add(r2, f0 + fpos + np.arange(na), -1.0)
            fpos += na
        elif R.pairs_of[c]:
            r2 = rows.new(na, -np.inf, 1.0)
            for p in R.pairs_of[c]:
                rows.add(r2, zvars(p), 1.0)

    # ---- (C3), or per-z linking rows (kappa_infinite and core)
    for (j, l), plist in _jl_groups(B, R).items():
        if (j, l) in warm:
            wv = np.concatenate(warm[(j, l)][0])
            wt = np.concatenate(warm[(j, l)][1])
        else:
            wv = wt = np.zeros(0, np.int64)
        if B.mode == "full":
            tmask = np.zeros(Tb, dtype=bool)
            for p in plist:
                tmask[R.act[R.pc[p]]] = True
            rowmap = np.full(Tb, -1, dtype=np.int64)
            rowmap[tmask] = rows.new(int(tmask.sum()), -np.inf, 0.0)
            for p in plist:
                c = R.pc[p]
                rows.add(rowmap[R.act[c]], zvars(p), B.d[c, R.act[c]])
            keep = rowmap[wt] >= 0
            rows.add(rowmap[wt[keep]], wv[keep], -1.0)
        else:
            order = np.argsort(wt, kind="stable")
            wv, wt = wv[order], wt[order]
            cnt = np.bincount(wt, minlength=Tb)
            first = np.cumsum(cnt) - cnt
            for p in plist:
                zt = R.act[R.pc[p]]
                r3 = rows.new(len(zt), -np.inf, 0.0)
                rows.add(r3, zvars(p), 1.0)
                k = cnt[zt]
                pos = np.repeat(first[zt], k) + (np.arange(int(k.sum())) - np.repeat(np.cumsum(k) - k, k))
                rows.add(np.repeat(r3, k), wv[pos], -1.0)

    # ---- (C4) site capacity
    for l, (av, at, ag) in alive.items():
        av, at, ag = np.concatenate(av), np.concatenate(at), np.concatenate(ag)
        if len(av) == 0:
            continue
        cnt = np.bincount(at, minlength=Tb)
        rowmap = np.full(Tb, -1, dtype=np.int64)
        rowmap[cnt > 0] = rows.new(int((cnt > 0).sum()), -np.inf, float(B.cap[l]))
        rows.add(rowmap[at], av, ag)

    # ---- (C5) moved load, any destination; (C6) moved load to fallback
    ypos = 0
    for c, ts in y_slots.items():
        dh = np.minimum(B.d[c, ts - 1], B.d[c, ts])
        for p in R.pairs_of[c]:
            yv = y0 + ypos + np.arange(len(ts))
            ypos += len(ts)
            cost[yv] = B.mu_kv[c]
            r5 = rows.new(len(ts), -np.inf, 0.0)
            base = z0 + R.zbase[p]
            rows.add(r5, yv, -1.0)
            rows.add(r5, base + R.pos[c, ts - 1], dh)
            rows.add(r5, base + R.pos[c, ts], -B.d[c, ts])
    wpos = 0
    for c, ts in w_slots.items():
        dh = np.minimum(B.d[c, ts - 1], B.d[c, ts])
        wv = w0 + wpos + np.arange(len(ts))
        wpos += len(ts)
        cost[wv] = B.mu_fb[c]
        r6 = rows.new(len(ts), -np.inf, 0.0)
        rows.add(r6, wv, -1.0)
        for p in R.pairs_of[c]:
            base = z0 + R.zbase[p]
            rows.add(r6, base + R.pos[c, ts - 1], dh)
            rows.add(r6, base + R.pos[c, ts], -B.d[c, ts])

    # ---- assemble CSR with int32 indices
    nr = rows.n
    if nr:
        rr = np.concatenate(rows.r).astype(np.int32)
        cc = np.concatenate(rows.c).astype(np.int32)
        vv = np.concatenate(rows.v)
        rows.r = rows.c = rows.v = None
        A = sp.csr_matrix((vv, (rr, cc)), shape=(nr, nv))
        del rr, cc, vv
        A.sum_duplicates()
        A.indices = A.indices.astype(np.int32, copy=False)
        A.indptr = A.indptr.astype(np.int32, copy=False)
        rlb, rub = np.concatenate(rows.lo), np.concatenate(rows.hi)
    else:
        A = None
        rlb = rub = np.zeros(0)
    rows = None
    cat = (lambda xs: np.concatenate(xs) if xs else np.zeros(0))
    comp = {
        "n": cat(n_idx).astype(np.int64),
        "lease_prepaid": cat(n_pre), "loading": cat(n_beta), "lease_rent_n": cat(n_lr),
        "e": cat(e_idx).astype(np.int64), "lease_rent_e": cat(e_rent),
        "z_route": z_route, "z_fb": z_fb,
    }
    blocks = dict(n=(0, N_n), e=(e0, N_e), hp=(hp0, N_hp), rho=(rho0, N_rho), z=(z0, N_z),
                  y=(y0, N_y), w=(w0, N_w), f=(f0, N_f))
    # n_int counts the integer-typed variables (n, e, hold pools) also when the LP relaxes them,
    # so that the counts equal estimate_size's; 'relaxed' tells the two apart.
    size = dict(n_vars=nv, n_int=rho0, n_rows=nr, nnz=int(A.nnz) if A is not None else 0,
                n_eq_rows=int((rlb == rub).sum()), relaxed=not integral)
    return _Model(c=cost, const=const, integrality=integ, lb=lb, ub=ub, A=A, rlb=rlb,
                  rub=rub, blocks=blocks, comp=comp, size=size)


# ============================================================================ solution
def _components(B: _Bench, M: _Model, x: np.ndarray) -> dict:
    """Ledger split (§5.6) of the objective at x."""
    cp = M.comp
    xn = x[cp["n"]] if len(cp["n"]) else np.zeros(0)
    z0, Nz = M.blocks["z"]
    xz = x[z0:z0 + Nz]
    out = dict.fromkeys(COMPONENTS, 0.0)
    out["lease_prepaid"] = float(cp["lease_prepaid"] @ xn)
    out["loading"] = float(cp["loading"] @ xn)
    out["lease_rent"] = float(cp["lease_rent_n"] @ xn) + (
        float(cp["lease_rent_e"] @ x[cp["e"]]) if len(cp["e"]) else 0.0)
    out["routing"] = float(cp["z_route"] @ xz)
    if B.mode == "core":
        f0, Nf = M.blocks["f"]
        out["fallback"] = float(M.c[f0:f0 + Nf] @ x[f0:f0 + Nf])
    else:
        out["fallback"] = M.const + float(cp["z_fb"] @ xz)
    y0, Ny = M.blocks["y"]
    w0, Nw = M.blocks["w"]
    out["stranding_kv"] = float(M.c[y0:y0 + Ny] @ x[y0:y0 + Ny])
    out["stranding_fb"] = float(M.c[w0:w0 + Nw] @ x[w0:w0 + Nw])
    out["lease"] = out["lease_prepaid"] + out["lease_rent"]
    out["stranding"] = (out["stranding_kv"] + out["stranding_fl"] + out["stranding_fb"]
                        + out["stranding_pi"])
    out["total"] = sum(out[k] for k in COMPONENTS)
    return out


def _plan(B: _Bench, x: np.ndarray) -> list:
    """Leases of an integral solution (§8.10): one PlannedLease (n = 1) per lease. Extension
    pools release last in, first out (any order is equivalent there); hold pools release first
    in, first out, the order that their rent rows (C0r) price (module docstring)."""
    plan = []
    phib = B.phib

    def emit(u, i, t_rel):
        """Lease of start i of u released at bench slot t_rel (None: dies or horizon)."""
        if t_rel is None:
            plan.append(PlannedLease(site=u.l, contract=u.k, llm=u.j, start_slot=int(u.s[i])))
            return
        if t_rel == u.sb[i]:
            return                          # released in its purchase slot: never alive
        if t_rel % phib:
            raise RuntimeError(f"release at bench slot {t_rel}, not a decision slot")
        plan.append(PlannedLease(site=u.l, contract=u.k, llm=u.j, start_slot=int(u.s[i]),
                                 release_slot=int(t_rel // phib)))

    for u in B.triples:
        N = len(u.s)
        if N == 0:
            continue
        nval = np.rint(x[u.n0:u.n0 + N]).astype(np.int64)
        if u.pooled:
            P0, E = u.coh_P0, u.coh_E
            base = u.coh_p0 + np.cumsum(E - P0) - (E - P0)
            for kap in range(len(E)):
                lo, hi = int(u.coh_lo[kap]), int(u.coh_hi[kap])
                L = int(E[kap] - P0[kap])
                pv = np.rint(x[base[kap]:base[kap] + L]).astype(np.int64)
                if not pv.any() and not nval[lo:hi].any():
                    continue
                arr = u.sb[lo:hi] + u.lam - P0[kap]          # arrival offsets, increasing
                inflow = np.zeros(L, dtype=np.int64)
                inflow[arr] = nval[lo:hi]
                exits = np.concatenate([[0], pv[:-1]]) + inflow - pv
                if (exits < 0).any():
                    raise RuntimeError("hold pool grows without inflow")
                queue, nxt = deque(), 0
                for o in np.flatnonzero((inflow > 0) | (exits > 0)):
                    while nxt < len(arr) and arr[nxt] <= o:
                        queue.extend([lo + nxt] * int(nval[lo + nxt]))
                        nxt += 1
                    for _ in range(int(exits[o])):
                        emit(u, queue.popleft(), int(P0[kap] + o))   # first in, first out
                for i in queue:
                    emit(u, i, None)
            continue
        pools = defaultdict(list)           # cohort -> [(entry slot, start index, count)]
        for i in np.flatnonzero(nval > 0):
            held = int(nval[i])
            t_in = int(u.sb[i] + u.A)
            if t_in < u.E[i]:
                if held > 0:
                    pools[int(u.coh[i])].append((t_in, int(i), held))
            else:
                for _ in range(held):
                    emit(u, i, None)
        for kap, events in pools.items():
            X0, XE = int(u.coh_X0[kap]), int(u.coh_E[kap])
            e = np.rint(x[u.coh_e0[kap]:u.coh_e0[kap] + XE - X0]).astype(np.int64)
            inflow = np.zeros(XE - X0, dtype=np.int64)
            for t_in, i, h in events:
                inflow[t_in - X0] += h
            prev = np.concatenate([[0], e[:-1]])
            exits = prev + inflow - e
            if (exits < 0).any():
                raise RuntimeError("extension pool grows without inflow")
            events.sort()
            stack, p = [], 0
            for o in np.flatnonzero((inflow > 0) | (exits > 0)):
                t = X0 + int(o)
                while p < len(events) and events[p][0] <= t:
                    stack.extend([events[p][1]] * events[p][2])
                    p += 1
                for _ in range(int(exits[o])):
                    emit(u, stack.pop(), t)      # last in, first out
            for i in stack:
                emit(u, i, None)
    plan.sort(key=lambda pl: (pl.start_slot, pl.site, pl.contract, pl.llm,
                              -1 if pl.release_slot is None else pl.release_slot))
    return plan


def _solve(B: _Bench, *, integral: bool, time_limit_s: float, mip_rel_gap: float,
           return_plan: bool, method: str, benchmark: str, t_start: float,
           est: Optional[dict] = None) -> SolveResult:
    M = _build(B, integral)
    gc.collect()
    build_s = time.perf_counter() - t_start
    size = dict(M.size)
    size["rss_after_build_mb"] = _rss_mb()
    size["parts"] = (est or _count(B))["parts"]
    nv = len(M.c)
    t1 = time.perf_counter()
    x = None
    if nv == 0:
        status, msg, obj, bound = 0, "empty model", M.const, M.const
        x = np.zeros(0)
    else:
        cons = [LinearConstraint(M.A, M.rlb, M.rub)] if M.A is not None else None
        res = milp(M.c, integrality=M.integrality, bounds=Bounds(M.lb, M.ub),
                   constraints=cons,
                   options={"time_limit": float(time_limit_s), "mip_rel_gap": float(mip_rel_gap),
                            "presolve": True, "disp": False})
        status = int(res.status) if res.status in (0, 1, 2, 3) else 4
        msg = str(res.message)
        x = res.x
        fun = float(res.fun) if x is not None else None
        is_mip = integral and bool(M.integrality.any())
        if x is None and status == 1 and is_mip:
            # No incumbent at the limit: report the all-fallback plan (every lease and
            # routing variable 0; in core mode every request on fallback), which is feasible.
            x = np.zeros(nv)
            f0, Nf = M.blocks["f"]
            x[f0:f0 + Nf] = 1.0
            fun = float(M.c @ x)
            msg += "; no incumbent from HiGHS, objective is the all-fallback plan"
        obj = fun + M.const if fun is not None else None
        if is_mip:
            db = getattr(res, "mip_dual_bound", None)
            if db is not None and np.isfinite(db):
                bound = float(db) + M.const
                if bound < 0.0:
                    # every cost component is non-negative, so OPT >= 0 is the better bound
                    bound = 0.0
                    msg += "; HiGHS dual bound below 0, dual_bound 0"
            elif status == 0:
                bound = obj
            elif obj is not None:
                bound = 0.0         # every cost component is non-negative, so OPT >= 0
                msg += "; no dual bound from HiGHS, dual_bound 0"
            else:
                bound = None
        else:
            bound = obj if status == 0 else None    # an LP stopped early is no bound
    solve_s = time.perf_counter() - t1
    gap = None
    if obj is not None and bound is not None:
        gap = (obj - bound) / max(1.0, abs(obj))
    comps = _components(B, M, x) if x is not None else {}
    plan = None
    if return_plan and integral and x is not None:
        plan = _plan(B, x)
    return SolveResult(method=method, benchmark=benchmark, grid=B.grid, status=status,
                       status_msg=msg, objective=obj, dual_bound=bound, gap=gap, plan=plan,
                       components=comps, size=size, build_s=build_s, solve_s=solve_s,
                       peak_rss_mb=_peak_rss_mb())


# ============================================================================ interface
def estimate_size(inst: Instance, sched: Schedule, *, grid: BenchGrid = "slow") -> dict:
    """Exact counts of the model that solve_opt builds (§8.7), without building it:
    {'n_vars', 'n_int', 'n_rows', 'nnz', 'est_mb', 'parts'}. n_int and est_mb are those of the
    MILP (est_mb = 400 + 2.7e-3 nnz MB, §10 S36); parts holds the counts per variable block
    and constraint family, 'est_mb_milp' (= est_mb) and 'est_mb_lp' = 130 + 5.4e-4 nnz MB."""
    return _count(_bench_instance(inst, sched, grid, False, None))


def _gate(est: dict, integral: bool, max_vars: int, mem_budget_mb: float) -> None:
    """§8.9, §10 S36: SizeError if n_vars > max_vars or the estimated peak (MILP rule, or the LP
    rule for integral=False) exceeds mem_budget_mb."""
    mb = est["est_mb"] if integral else est["parts"]["est_mb_lp"]
    what = "MILP" if integral else "LP"
    if est["n_vars"] > max_vars:
        raise SizeError(f"model has {est['n_vars']} variables > max_vars = {max_vars} "
                        f"(estimated {mb:.0f} MB, {what} rule); pass allow_large=True to solve")
    if mb > mem_budget_mb:
        raise SizeError(f"estimated peak {mb:.0f} MB ({what} rule, {est['nnz']} nonzeros) > mem_budget_mb = "
                        f"{mem_budget_mb:.0f}; pass allow_large=True to solve (alone, §8.9)")


def solve_opt(inst: Instance, sched: Schedule, *, grid: BenchGrid = "slow", integral: bool = True,
              refuse_unavailable: bool = False, refuse_sched: Optional[Schedule] = None,
              time_limit_s: float = 300.0, mip_rel_gap: float = 1e-4, max_vars: int = 200_000,
              mem_budget_mb: float = MEM_BUDGET_MB, allow_large: bool = False,
              return_plan: bool = True) -> SolveResult:
    """OPT_P1(sigma, omega) on the bench grid (§8.2; grid 'slow_lb': §8.6) for the realized
    schedule `sched`. integral=False gives the LP bound (§8.5). With refuse_unavailable no
    lease starts at site l in a slow slot of refuse_sched.R[l] (sched.R[l] if refuse_sched is
    None). Raises SizeError, unless allow_large, if the model has more than max_vars variables
    or its estimated peak exceeds mem_budget_mb (the MILP rule of estimate_size, or for the LP
    the LP rule parts['est_mb_lp']; §8.9, §10 S36).

    Status (§8.8): 0 optimal; 1 time or iteration limit; 2-4 as HiGHS reports. At a limit a MILP
    reports its incumbent (the all-fallback plan if HiGHS returned none) and HiGHS's dual bound
    clipped at 0 (0 if HiGHS has none: every cost is non-negative, so OPT >= 0), the substitutes
    noted in status_msg; an LP stopped
    early reports HiGHS's last point, if any, as objective and dual_bound None.
    size['n_int'] counts the integer-typed variables (n, e, hold pools) also for the LP, whose
    size['relaxed'] is True."""
    t0 = time.perf_counter()
    B = _bench_instance(inst, sched, grid, refuse_unavailable,
                        refuse_sched if refuse_unavailable else None)
    est = _count(B)
    if not allow_large:
        _gate(est, integral, max_vars, mem_budget_mb)
    return _solve(B, integral=integral, time_limit_s=time_limit_s, mip_rel_gap=mip_rel_gap,
                  return_plan=return_plan, method="milp" if integral else "lp",
                  benchmark="omega", t_start=t0, est=est)


def solve_eager(inst: Instance, *, refuse_sched: Optional[Schedule] = None, **kw) -> SolveResult:
    """OPT_eager (§8.4): solve_opt under Schedule.eager(inst); refuse_sched is the schedule of a
    'refuse' run, whose refusal sets then remove starts."""
    res = solve_opt(inst, Schedule.eager(inst), refuse_unavailable=refuse_sched is not None,
                    refuse_sched=refuse_sched, **kw)
    res.benchmark = "eager"
    return res


def solve_lp(inst: Instance, sched: Schedule, **kw) -> SolveResult:
    """LP lower bound (§8.5): solve_opt(..., integral=False)."""
    return solve_opt(inst, sched, integral=False, **kw)


def solve_core(core_inst, omega: list, *, integral: bool = True,
               time_limit_s: float = 120.0, mip_rel_gap: float = 1e-9) -> SolveResult:
    """Core mode (§8.3) on a core.Instance-like object (fields T, tau, H, a, beta, g, q, cl_llm,
    delta, active); omega per core site. Equals core.opt_omega (Proposition M1) and, under
    omega_all, core.opt_eager (Corollary M2). The plan uses core indices and core slots."""
    t0 = time.perf_counter()
    B = _bench_core(core_inst, omega)
    T = int(core_inst.T)
    eager = all(len(np.intersect1d(np.asarray(o), np.arange(T))) == T for o in omega)
    return _solve(B, integral=integral, time_limit_s=time_limit_s, mip_rel_gap=mip_rel_gap,
                  return_plan=True, method="core_milp" if integral else "core_lp",
                  benchmark="eager" if eager else "omega", t_start=t0)
