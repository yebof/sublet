"""Numerical check of Proposition A (design/theory/core_additive.md): the additive price on
phase-predictable (in particular phase-persistent) demand on the multi-site core.

For each instance (phases [p_i, p_{i+1}) of length >= P except the last, segments
S_i = [p_i, p_i + S) with S = D_min, rests R_i = [p_i + S, p_{i+1})), the script
  * runs LR: A2 (c3/pd.py FracPD + the analysed threshold rounding of S-B) on the segment
    requests sigma^1, and at each rest start buys an offline eager-optimal plan for sigma^r_i
    (MILP with columns starting at or after the rest start);
  * for every lender (eager, never-announce, Bernoulli 0.05 / 0.2 / 0.6 per site-slot, and
    Theorem 2(a)'s adaptive rule run against LR's realized leases) solves OPT(sigma, omega)
    with its plan pi, builds the split plans of the proof from pi, and checks every
    inequality of the proof:
      C1  n1_L <= ceil((len_L + S)/P)                       (segments met by a lease)
      C2  n1_L * C_L <= g1_L * c_L for the refined and the simple g1 (Lemma A.2)
      C3  nR_L <= (len_L + S)/D + n_R (D-1-S)^+ / D, n_R < 2 + (len_L - S)/P
      C4  nR_L * C_L <= gR_L * c_L                          (Lemma A.3)
      C5  the split plans cover every routed request of pi (same site, same routing cost)
      C6  OPT_eager(sigma^1) <= split^1 cost <= sum g1 c_L + serv_pi(sigma^1)
      C7  sum_i OPT_eager(sigma^r_i) <= split^r cost <= sum gR c_L + serv_pi(sigma^r)
      C8  B := alpha_N OPT_eager(sigma^1) + sum_i OPT_eager(sigma^r_i) <= c_pi cost(pi)
          <= c_A OPT_sw (lower bound of the MILP) and the closed forms of Proposition A(b)-(c);
          the same chain with alpha = 1 in place of alpha_N (B1 <= c1 OPT_sw, reported for tightness)
      C9  the fractional cost of A2 <= 4 ln(mK+2) OPT_eager(sigma^1)       (Theorem 1(d))
      C10 the mean of A2's rounded cost over the seeds <= alpha_N OPT_eager(sigma^1)
          (an expectation; reported, counted as a violation only if exceeded)
      C11 LR's leases live through their windows under omega; mean LR <= c_A OPT_sw
      C12 the eager MILPs agree with c3/core.py's opt_eager, the plan MILP with opt_omega
          (on the instances listed in XCHECK), and rest plans need no lease before the rest.
It exits 1 on any violation. Output: out/additive.json, out/additive.txt.
Usage: check_additive.py [--reduced] [--workers W] [--n-rand N]
"""
import os
import sys
import json
import math
import time
import argparse
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
import scipy.sparse as sp
from scipy.optimize import milp, LinearConstraint, Bounds

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from core import Instance, opt_eager, opt_omega, any_start_columns, effective_end  # noqa: E402
from pd import FracPD, round_pd  # noqa: E402

OUT = os.path.join(HERE, 'out')
RTOL = 1e-6
GAP = 1e-9
N_SEEDS = 12          # rounding seeds of A2 per instance
N_SEEDS_ADAPT = 3     # seeds whose realized adaptive schedule is solved
XCHECK = 25           # instances cross-checked against core.py's MILPs


# ---------------------------------------------------------------- phases
class Phases:
    def __init__(self, T, P, S):
        self.T, self.P, self.S = T, P, S
        self.starts = list(range(0, T, P)) if P < T else [0]
        self.ends = self.starts[1:] + [T]

    def intervals(self):
        """[(kind, i, a, b)]: segments ('S') and nonempty rests ('R'), in time order."""
        out = []
        for i, (p, e) in enumerate(zip(self.starts, self.ends)):
            out.append(('S', i, p, min(p + self.S, e)))
            if p + self.S < e:
                out.append(('R', i, p + self.S, e))
        return out

    def P_min(self):
        """minimum length of the phases other than the last (inf with one phase)."""
        L = [e - p for p, e in zip(self.starts[:-1], self.ends[:-1])]
        return float(min(L)) if L else math.inf


def alpha_N(N, m, K):
    return 4 * math.ceil(2 * math.log(N)) * math.log(m * K + 2) + 1


# ---------------------------------------------------------------- coefficients
def g1_refined(rho, D, S, P):
    if not math.isfinite(P):
        return 1.0
    den = P + (rho - 1) * D - S
    if den <= 0:
        # rho = 1 and P = S (audit F8): the second bound of Lemma A.2(ii) is read as +infinity.
        assert den == 0
        return math.inf
    return max(1.0, 2 * rho * D / den, rho * D / P)


def g1_simple(rho, D, S, P):
    if not math.isfinite(P):
        return 1.0
    return 1.0 + (S + rho * D) / P


def g1(rho, D, S, P):
    """gamma^1 of Lemma A.2: the smaller of the refined and the simple bound."""
    return min(g1_refined(rho, D, S, P), g1_simple(rho, D, S, P))


def gR(rho, D, S, P):
    g = max(1.0 + S / D, rho)
    if D >= S + 2:
        g += (D - 1 - S) * (2.0 / D + (rho / P if math.isfinite(P) else 0.0))
    return g


def triples(I):
    out = []
    for (l, j) in I.lj_pairs():
        for k in range(I.K):
            out.append((l, j, k, I.C(l, j, k) / (I.rent(l, j, k) * I.L[k]), int(I.L[k])))
    return out


def class_constants(I, ph, aN):
    S, P = ph.S, ph.P_min()
    tr = triples(I)
    # No usable triple (audit F9): every plan falls back everywhere, c_A(alpha) := alpha.
    G1 = max((g1(r, D, S, P) for (_, _, _, r, D) in tr), default=1.0)
    GR = max((gR(r, D, S, P) for (_, _, _, r, D) in tr), default=0.0)
    cA = max((aN * g1(r, D, S, P) + gR(r, D, S, P) for (_, _, _, r, D) in tr), default=aN)
    c1 = max((g1(r, D, S, P) + gR(r, D, S, P) for (_, _, _, r, D) in tr), default=1.0)
    return dict(G1=G1, GR=GR, cA=cA, cA_sep=aN * G1 + GR, c1=c1)


def closed_forms(I, ph, aN):
    """Proposition A(b)-(c): the closed forms that apply to this instance (None if not)."""
    rho = I.rho()
    Dmax, S, P = int(I.L.max()), ph.S, ph.P_min()
    eq = all(int(D) <= S + 1 for D in I.L)
    out = {}
    if P >= rho * Dmax:
        out['b_all'] = 3 * aN + max(2, rho) + (0 if eq else 3)
        if rho >= 2:
            out['b_rho2'] = rho / (rho - 1) * aN + rho + (0 if eq else 3)
    if P >= (rho + 1) * Dmax + S:
        out['c'] = aN + max(2, rho) + (0 if eq else 3)
    return out


# ---------------------------------------------------------------- MILPs
def eager_milp(I, min_start=0, time_limit=300.0):
    """OPT_eager of I with any-start columns starting at slot >= min_start. Returns
    (fun, lb, leases [(l,j,k,s)])."""
    cols = [c for c in any_start_columns(I) if c[3] >= min_start]
    el = I.elements()
    nE, nX = len(el), len(cols)
    if nE == 0:
        return 0.0, 0.0, []
    by_lj = {}
    for i, (l, j, k, s, st, en, cst) in enumerate(cols):
        by_lj.setdefault((l, j), []).append((i, st, en))
    zidx = [(ei, l) for ei, (c, t) in enumerate(el) for l in range(I.m)
            if np.isfinite(I.delta[c, l]) and (l, int(I.cl_llm[c])) in by_lj]
    nZ = len(zidx)
    nV = nX + nZ + nE
    cost = np.zeros(nV)
    cost[:nX] = [col[6] for col in cols]
    for zi, (ei, l) in enumerate(zidx):
        cost[nX + zi] = I.delta[el[ei][0], l]
    cost[nX + nZ:] = I.q
    rows, cidx, vals, ub = [], [], [], []
    z_of_e = {}
    for zi, (ei, l) in enumerate(zidx):
        z_of_e.setdefault(ei, []).append(zi)
    r = 0
    for ei in range(nE):
        for zi in z_of_e.get(ei, []):
            rows.append(r); cidx.append(nX + zi); vals.append(-1.0)
        rows.append(r); cidx.append(nX + nZ + ei); vals.append(-1.0)
        ub.append(-1.0); r += 1
    for zi, (ei, l) in enumerate(zidx):
        c, t = el[ei]
        rows.append(r); cidx.append(nX + zi); vals.append(1.0)
        for (i, st, en) in by_lj[(l, int(I.cl_llm[c]))]:
            if st <= t < en:
                rows.append(r); cidx.append(i); vals.append(-1.0)
        ub.append(0.0); r += 1
    A = sp.csr_matrix((vals, (rows, cidx)), shape=(r, nV))
    integ = np.zeros(nV)
    integ[:nX] = 1
    res = milp(cost, constraints=LinearConstraint(A, -np.inf, np.array(ub)), integrality=integ,
               bounds=Bounds(np.zeros(nV), np.ones(nV)),
               options=dict(time_limit=time_limit, disp=False, mip_rel_gap=GAP))
    assert res.x is not None, 'eager MILP failed'
    lb = getattr(res, 'mip_dual_bound', None)
    lb = float(lb) if lb is not None and np.isfinite(lb) else float(res.fun)
    leases = [(c[0], c[1], c[2], c[3]) for c, v in zip(cols, res.x[:nX]) if v > 0.5]
    return float(res.fun), lb, leases


def omega_plan(I, omega, time_limit=300.0):
    """OPT(sigma, omega) with its plan (formulation of core.opt_omega). Returns dict(fun, lb,
    leases [dict(l,j,k,s,ext,cost)], serv {request index: cost}, z {request index: [l]})."""
    el = I.elements()
    T = I.T
    ocols, hvars = [], []
    for (l, j) in I.lj_pairs():
        for k in range(I.K):
            for s in range(T):
                oi = len(ocols)
                ocols.append((l, j, k, s))
                E = min(effective_end(I, omega, l, k, s), T)
                for t in range(s + I.L[k], E):
                    hvars.append((oi, t))
    nO, nH, nE = len(ocols), len(hvars), len(el)
    ljset = set(I.lj_pairs())
    zidx = [(ei, l) for ei, (c, t) in enumerate(el) for l in range(I.m)
            if np.isfinite(I.delta[c, l]) and (l, int(I.cl_llm[c])) in ljset]
    nZ = len(zidx)
    nV = nO + nH + nZ + nE
    cost = np.zeros(nV)
    for oi, (l, j, k, s) in enumerate(ocols):
        cost[oi] = I.C(l, j, k)
    for hi, (oi, t) in enumerate(hvars):
        l, j, k, s = ocols[oi]
        cost[nO + hi] = I.rent(l, j, k)
    for zi, (ei, l) in enumerate(zidx):
        cost[nO + nH + zi] = I.delta[el[ei][0], l]
    cost[nO + nH + nZ:] = I.q
    rows, cidx, vals, ub = [], [], [], []
    r = 0
    z_of_e = {}
    for zi, (ei, l) in enumerate(zidx):
        z_of_e.setdefault(ei, []).append(zi)
    for ei in range(nE):
        for zi in z_of_e.get(ei, []):
            rows.append(r); cidx.append(nO + nH + zi); vals.append(-1.0)
        rows.append(r); cidx.append(nO + nH + nZ + ei); vals.append(-1.0)
        ub.append(-1.0); r += 1
    prev = {}
    for hi, (oi, t) in enumerate(hvars):
        rows.append(r); cidx.append(nO + hi); vals.append(1.0)
        rows.append(r); cidx.append(nO + prev[oi] if oi in prev else oi); vals.append(-1.0)
        prev[oi] = hi
        ub.append(0.0); r += 1
    cover = {}
    for oi, (l, j, k, s) in enumerate(ocols):
        for t in range(s, min(s + I.L[k], T)):
            cover.setdefault((l, j, t), []).append(oi)
    for hi, (oi, t) in enumerate(hvars):
        l, j, k, s = ocols[oi]
        cover.setdefault((l, j, t), []).append(nO + hi)
    for zi, (ei, l) in enumerate(zidx):
        c, t = el[ei]
        rows.append(r); cidx.append(nO + nH + zi); vals.append(1.0)
        for v in cover.get((l, int(I.cl_llm[c]), t), []):
            rows.append(r); cidx.append(v); vals.append(-1.0)
        ub.append(0.0); r += 1
    A = sp.csr_matrix((vals, (rows, cidx)), shape=(r, nV))
    integ = np.zeros(nV)
    integ[:nO + nH] = 1
    res = milp(cost, constraints=LinearConstraint(A, -np.inf, np.array(ub)), integrality=integ,
               bounds=Bounds(np.zeros(nV), np.ones(nV)),
               options=dict(time_limit=time_limit, disp=False, mip_rel_gap=GAP))
    assert res.x is not None, 'omega MILP failed'
    x = res.x
    lb = getattr(res, 'mip_dual_bound', None)
    lb = float(lb) if lb is not None and np.isfinite(lb) else float(res.fun)
    ext = {}
    for hi, (oi, t) in enumerate(hvars):
        if x[nO + hi] > 0.5:
            ext[oi] = ext.get(oi, 0) + 1
    leases = []
    for oi, (l, j, k, s) in enumerate(ocols):
        if x[oi] > 0.5:
            e = ext.get(oi, 0)
            leases.append(dict(l=l, j=j, k=k, s=s, ext=e, cost=I.C(l, j, k) + I.rent(l, j, k) * e))
    serv = {ei: I.q * x[nO + nH + nZ + ei] for ei in range(nE)}
    zon = {ei: [] for ei in range(nE)}
    for zi, (ei, l) in enumerate(zidx):
        v = x[nO + nH + zi]
        serv[ei] += I.delta[el[ei][0], l] * v
        if v > 1e-6:          # routed shares above the solver's feasibility tolerance
            zon[ei].append(l)
    return dict(fun=float(res.fun), lb=lb, leases=leases, serv=serv, z=zon, status=int(res.status))


# ---------------------------------------------------------------- A2 rounding with its leases
def round_analysed(pd, rng, N):
    """The analysed rule of S-B (identical draws and cost to pd.round_pd's cost_an), with the
    leases it buys: threshold openings and the fix-up leases, as (l, j, k, purchase slot)."""
    I = pd.I
    r = int(math.ceil(2 * math.log(N)))
    theta = {}

    def th(F):
        if F not in theta:
            theta[F] = 1.0 - rng.random() ** (1.0 / r)
        return theta[F]
    opened, leases, cost = {}, [], 0.0
    for (c, t, cand, xs, ys, f, dl) in pd.records:
        for F in cand:
            if F not in opened and xs[F] > th(F):
                opened[F] = t
                cost += I.C(F[1], F[2], F[3])
                leases.append((F[1], F[2], F[3], t))
        if f >= 0.5:
            cost += I.q
        else:
            usable = [F for F in cand if min(xs[F], ys[F]) > th(F)]
            if usable:
                cost += min(dl[F] for F in usable)
            else:
                best, bF = I.q, None
                for F in cand:
                    v = I.C(F[1], F[2], F[3]) + dl[F]
                    if v < best:
                        best, bF = v, F
                cost += best
                if bF is not None:
                    leases.append((bF[1], bF[2], bF[3], t))
    return cost, leases


# ---------------------------------------------------------------- instances
def restrict(I, mask):
    J = I.subset()
    J.active = I.active & mask
    return J


def make_instance(T, tau, H, a, beta, g, q, cl_llm, delta, active):
    return Instance(T=T, tau=np.array(tau), H=np.array(H), a=np.array(a, dtype=float),
                    beta=np.array(beta, dtype=float), g=np.array(g), q=float(q),
                    cl_llm=np.array(cl_llm), delta=np.array(delta, dtype=float),
                    active=np.array(active, dtype=bool))


def persistent_active(rng, n, ph, p_in=0.6, distinct=False):
    act = np.zeros((n, ph.T), dtype=bool)
    for p, e in zip(ph.starts, ph.ends):
        segl = min(ph.S, e - p)
        slots = list(rng.permutation(segl)) if distinct else None
        for c in range(n):
            if rng.random() < p_in:
                off = slots[c % segl] if distinct else int(rng.integers(0, segl))
                act[c, p + off:e] = True
    return act


CONTRACT_POOL = {
    1: [[(2, 1)], [(3, 0)], [(2, 2)], [(1, 2)]],
    2: [[(1, 1), (4, 2)], [(2, 1), (4, 2)], [(2, 1), (3, 1)], [(1, 2), (3, 3)], [(2, 0), (2, 1)]],
}


def gen_random(rng, pmode, P_override=None):
    T = int(rng.choice([36, 48]))
    m = int(rng.integers(2, 5))
    J = int(rng.integers(1, 3))
    n = int(rng.integers(3, 7))
    K = int(rng.integers(1, 3))
    cons = CONTRACT_POOL[K][int(rng.integers(len(CONTRACT_POOL[K])))]
    tau = [c[0] for c in cons]
    H = [c[1] for c in cons]
    mult = np.array([1.0, 1.3][:K]) * rng.uniform(0.9, 1.1, size=K)
    a = np.outer(rng.uniform(0.7, 1.3, size=m), mult)
    g = rng.choice([1, 2], size=J)
    D = np.array(tau) + np.array(H)
    rho_t = rng.uniform(1.2, 4.0)
    beta = (rho_t - 1) * g[:, None] * a[:, 0][None, :] * D[0] * rng.uniform(0.6, 1.0, size=(J, m))
    sites = rng.uniform(0, 1, size=(m, 2))
    cl = rng.uniform(0, 1, size=(n, 2))
    dist = np.linalg.norm(cl[:, None, :] - sites[None, :, :], axis=2)
    delta = 0.5 * dist
    if rng.random() < 0.5:
        delta = np.where(dist <= 0.6, delta, np.inf)
        for c in range(n):
            if not np.isfinite(delta[c]).any():
                l = int(np.argmin(dist[c])); delta[c, l] = 0.5 * dist[c, l]
    q = float(rng.choice([3.0, 6.0, 50.0]))
    cl_llm = rng.integers(0, J, size=n)
    I0 = make_instance(T, tau, H, a, beta, g, q, cl_llm, delta, np.zeros((n, T), dtype=bool))
    S = int(D.min())
    rho = I0.rho()
    if P_override is not None:
        P = P_override(S, int(D.max()), rho)
    else:
        f = {'rhoD': rho * D.max(), '2rhoD': 2 * rho * D.max(), 'D': D.max(),
             'rho2D': (rho + 1) * D.max() + S}[pmode]
        P = max(S, int(math.ceil(f - 1e-9)))
    ph = Phases(T, P, S)
    I0.active = persistent_active(rng, n, ph)
    return I0, ph


def gen_thm2(rng, m, rho, tau, Hn, T, Pmode):
    D = tau + Hn
    beta = (rho - 1) * D
    I = make_instance(T, [tau], [Hn], np.ones((m, 1)), np.full((1, m), beta), [1], beta + D,
                      [0], np.zeros((1, m)), np.zeros((1, T), dtype=bool))
    P = {'single': T, 'rhoD': int(math.ceil(rho * D)), 'rho2D': int(math.ceil((rho + 2) * D)), 'D': D}[Pmode]
    ph = Phases(T, P, D)
    I.active = np.ones((1, T), dtype=bool)
    return I, ph


def gen_setcover(rng, T, m, n, rho, Pmode):
    tau, Hn = 4, 2
    D = tau + Hn
    beta = (rho - 1) * D
    while True:
        memb = rng.random((n, m)) < 0.45
        if memb.any(axis=1).all():
            break
    delta = np.where(memb, 0.0, np.inf)
    C = beta + D
    I = make_instance(T, [tau], [Hn], np.ones((m, 1)), np.full((1, m), beta), [1], C,
                      np.zeros(n, dtype=int), delta, np.zeros((n, T), dtype=bool))
    P = {'single': T, 'rhoD': int(math.ceil(rho * D)), 'D': D}[Pmode]
    ph = Phases(T, P, D)
    I.active = persistent_active(rng, n, ph, p_in=0.8, distinct=True)
    return I, ph


def gen_longwin(rng, Pmode):
    T = 48
    m = int(rng.integers(2, 4))
    n = int(rng.integers(2, 5))
    D2 = int(rng.choice([8, 12]))
    tau, H = [1, D2 - 3], [1, 3]
    a = np.outer(rng.uniform(0.8, 1.2, size=m), [1.0, float(rng.uniform(0.7, 1.2))])
    rho_t = rng.uniform(1.5, 3.5)
    beta = (rho_t - 1) * 2 * a[:, 0][None, :]
    delta = rng.uniform(0, 0.3, size=(n, m))
    I = make_instance(T, tau, H, a, beta, [1], 20.0, np.zeros(n, dtype=int), delta,
                      np.zeros((n, T), dtype=bool))
    S = 2
    rho = I.rho()
    P = {'S': S, 'Dmax': D2, 'rhoD': int(math.ceil(rho * D2))}[Pmode]
    ph = Phases(T, max(P, S), S)
    I.active = persistent_active(rng, n, ph, p_in=0.7)
    return I, ph


def build_cases(reduced, n_rand):
    cases = []
    rng = np.random.default_rng(81000)
    pm = ['rhoD', '2rhoD', 'D', 'rho2D']
    nr = 8 if reduced else n_rand
    for i in range(nr):
        cases.append(('rand', dict(seed=81000 + i, pmode=pm[i % 4])))
    for i in range(3 if reduced else 24):
        cases.append(('contig', dict(seed=82000 + i)))
    thm = [(m, rho, tau, Hn, T, Pm) for m in (2, 3, 4) for rho in (2.0, 3.0, 5.0)
           for (tau, Hn) in ((2, 1),) for T in (36,) for Pm in ('single', 'rhoD', 'rho2D', 'D')]
    thm += [(m, rho, 2, 1, 72, Pm) for m in (2, 4) for rho in (3.0, 6.0) for Pm in ('single', 'rho2D')]
    if reduced:
        thm = thm[:4]
    for c in thm:
        cases.append(('thm2', dict(m=c[0], rho=c[1], tau=c[2], H=c[3], T=c[4], Pmode=c[5])))
    for i in range(3 if reduced else 30):
        cases.append(('setcover', dict(seed=83000 + i, Pmode=['single', 'rhoD', 'D'][i % 3],
                                       rho=[2.0, 3.0, 4.0][(i // 3) % 3])))
    for i in range(3 if reduced else 24):
        cases.append(('longwin', dict(seed=84000 + i, Pmode=['S', 'Dmax', 'rhoD'][i % 3])))
    return cases


def instantiate(kind, prm):
    if kind == 'rand':
        return gen_random(np.random.default_rng(prm['seed']), prm['pmode'])
    if kind == 'contig':
        return gen_random(np.random.default_rng(prm['seed']), None, P_override=lambda S, Dm, r: S)
    if kind == 'thm2':
        return gen_thm2(None, prm['m'], prm['rho'], prm['tau'], prm['H'], prm['T'], prm['Pmode'])
    if kind == 'setcover':
        rng = np.random.default_rng(prm['seed'])
        T = 36 if prm['Pmode'] != 'single' else int(math.ceil(prm['rho'] * 6))
        return gen_setcover(rng, T, int(rng.integers(2, 5)), int(rng.integers(3, 6)), prm['rho'], prm['Pmode'])
    if kind == 'longwin':
        return gen_longwin(np.random.default_rng(prm['seed']), prm['Pmode'])
    raise ValueError(kind)


# ---------------------------------------------------------------- one case
def lender_schedules(I, seed):
    rng = np.random.default_rng(seed)
    out = [('eager', [np.arange(I.T)] * I.m), ('none', [np.array([], dtype=int)] * I.m)]
    for p in (0.05, 0.2, 0.6):
        out.append((f'bern{p}', [np.sort(np.nonzero(rng.random(I.T) < p)[0]) for _ in range(I.m)]))
    return out


def adaptive_schedule(I, leases):
    """Theorem 2(a)'s rule against LR: announce at a site whenever a lease of LR there reaches
    age tau_k (LR's leases do not depend on omega, so the realized schedule is this one)."""
    ann = [set() for _ in range(I.m)]
    for (l, j, k, s) in leases:
        r = s + int(I.tau[k])
        if r < I.T:
            ann[l].add(r)
    return [np.array(sorted(a), dtype=int) for a in ann]


def split_checks(I, ph, plan, el, aN, V):
    """Checks C1-C7 and part of C8 for one plan pi. Returns a dict of measured quantities."""
    S, P = ph.S, ph.P_min()
    ivs = ph.intervals()
    split1, splitR = [], {}
    sum_g1c, sum_gRc, sum_c_pi = 0.0, 0.0, 0.0
    cpi = c1pi = 0.0
    tight = dict(C2=0.0, C4=0.0)
    for L in plan['leases']:
        l, j, k, s, e_ = L['l'], L['j'], L['k'], L['s'], L['ext']
        D = int(I.L[k])
        Ck = I.C(l, j, k)
        a = I.rent(l, j, k)
        rhoL = Ck / (a * D)
        cL = L['cost']
        end = min(s + D + e_, I.T)
        length = end - s
        lenb = max(length, D)          # held length counted for the bounds (prepaid window)
        n1, nR, nRest = 0, 0, 0
        for (kind, i, x0, x1) in ivs:
            lo, hi = max(s, x0), min(end, x1)
            if lo >= hi:
                continue
            if kind == 'S':
                n1 += 1
                if hi - lo > D:
                    V.append(('piece_longer_than_D', dict(L=L)))
                split1.append((l, j, k, lo))
            else:
                nRest += 1
                cnt = int(math.ceil((hi - lo) / D))
                nR += cnt
                for r_ in range(cnt):
                    splitR.setdefault(i, []).append((l, j, k, lo + r_ * D))
        # C1
        if math.isfinite(P) and n1 > math.ceil((lenb + S) / P - 1e-12):
            V.append(('C1', dict(n1=n1, len=lenb, S=S, P=P)))
        if not math.isfinite(P) and n1 > 1:
            V.append(('C1_single', dict(n1=n1)))
        g1r, g1s = g1_refined(rhoL, D, S, P), g1_simple(rhoL, D, S, P)
        g1 = min(g1r, g1s)
        for nm, gg in (('C2_refined', g1r), ('C2_simple', g1s)):
            if n1 * Ck > gg * cL * (1 + RTOL):
                V.append((nm, dict(n1=n1, Ck=Ck, cL=cL, g1=gg)))
        tight['C2'] = max(tight['C2'], n1 * Ck / (g1 * cL))
        # C3
        bnd3 = (lenb + S) / D + nRest * max(0, D - 1 - S) / D
        if nR > bnd3 + 1e-9:
            V.append(('C3', dict(nR=nR, bnd=bnd3)))
        if math.isfinite(P) and not nRest < 2 + (lenb - S) / P + 1e-12:
            V.append(('C3_nRest', dict(nRest=nRest, len=lenb, P=P)))
        if not math.isfinite(P) and nRest > 1:
            V.append(('C3_nRest_single', dict(nRest=nRest)))
        gr = gR(rhoL, D, S, P)
        if nR * Ck > gr * cL * (1 + RTOL):
            V.append(('C4', dict(nR=nR, Ck=Ck, cL=cL, gR=gr)))
        tight['C4'] = max(tight['C4'], nR * Ck / (gr * cL))
        sum_g1c += g1 * cL
        sum_gRc += gr * cL
        sum_c_pi += cL
        cpi = max(cpi, aN * g1 + gr)
        c1pi = max(c1pi, g1 + gr)
    # C5 coverage of the split plans
    cov1 = set()
    for (l, j, k, s0) in split1:
        for t in range(s0, min(s0 + int(I.L[k]), I.T)):
            cov1.add((l, j, t))
    covR = {}
    for i, Ls in splitR.items():
        cs = covR.setdefault(i, set())
        for (l, j, k, s0) in Ls:
            if s0 < ph.starts[i] + S:
                V.append(('C5_rest_lease_before_rest', dict(i=i, s0=s0)))
            for t in range(s0, min(s0 + int(I.L[k]), I.T)):
                cs.add((l, j, t))
    serv1 = servR = 0.0
    seg_mask = np.zeros(I.T, dtype=bool)
    phase_of = np.zeros(I.T, dtype=int)
    for (kind, i, x0, x1) in ivs:
        if kind == 'S':
            seg_mask[x0:x1] = True
        phase_of[x0:x1] = i
    for ei, (c, t) in enumerate(el):
        j = int(I.cl_llm[c])
        if seg_mask[t]:
            serv1 += plan['serv'][ei]
            for l in plan['z'][ei]:
                if (l, j, t) not in cov1:
                    V.append(('C5_seg', dict(c=c, t=t, l=l)))
        else:
            servR += plan['serv'][ei]
            for l in plan['z'][ei]:
                if (l, j, t) not in covR.get(int(phase_of[t]), set()):
                    V.append(('C5_rest', dict(c=c, t=t, l=l)))
    split1_cost = sum(I.C(l, j, k) for (l, j, k, _) in split1) + serv1
    splitR_cost = sum(I.C(l, j, k) for Ls in splitR.values() for (l, j, k, _) in Ls) + servR
    return dict(split1_cost=split1_cost, splitR_cost=splitR_cost, serv1=serv1, servR=servR,
                sum_g1c=sum_g1c, sum_gRc=sum_gRc, c_pi=cpi, c1_pi=c1pi, tight=tight)


def run_case(arg):
    idx, kind, prm = arg
    t0 = time.time()
    V = []
    I, ph = instantiate(kind, prm)
    el = I.elements()
    N = max(2, len(el))
    aN = alpha_N(N, I.m, I.K)
    S = ph.S
    seg_mask = np.zeros(I.T, dtype=bool)
    for (kd, i, x0, x1) in ph.intervals():
        if kd == 'S':
            seg_mask[x0:x1] = True
    # class membership: every client active in a phase arrives in its segment and stays to its end
    for c in range(I.n):
        for p, e in zip(ph.starts, ph.ends):
            act = I.active[c, p:e]
            if act.any():
                first = int(np.argmax(act))
                if first >= S or not act[first:].all():
                    V.append(('class', dict(c=c, p=p)))
    I1 = restrict(I, seg_mask[None, :])
    oe1, oe1_lb, _ = eager_milp(I1)
    # A2 on sigma^1
    pdr = FracPD(I1).run()
    frac = pdr.primal()
    if frac > 4 * math.log(I.m * I.K + 2) * oe1 * (1 + RTOL) + 1e-9:
        V.append(('C9', dict(frac=frac, oe1=oe1)))
    a2 = []
    for sd in range(N_SEEDS):
        cst, leases = round_analysed(pdr, np.random.default_rng(9000 + sd), N)
        ref = round_pd(pdr, np.random.default_rng(9000 + sd), N=N)['cost_an']
        if abs(cst - ref) > 1e-7 * max(1, ref):
            V.append(('rounding_mismatch', dict(c=cst, ref=ref)))
        a2.append((cst, leases))
    a2mean = float(np.mean([c for c, _ in a2]))
    if a2mean > aN * oe1 * (1 + RTOL) + 1e-9:
        V.append(('C10', dict(a2mean=a2mean, bound=aN * oe1)))
    # rest plans
    rest_cost, rest_leases = 0.0, []
    for (kd, i, x0, x1) in ph.intervals():
        if kd != 'R':
            continue
        mask = np.zeros(I.T, dtype=bool)
        mask[x0:x1] = True
        Ii = restrict(I, mask[None, :])
        if not Ii.active.any():
            continue
        f_r, _, ls = eager_milp(Ii, min_start=x0)
        f_u, _, _ = eager_milp(Ii, min_start=0)
        if f_r > f_u * (1 + 1e-7) + 1e-7:
            V.append(('C12_rest_start', dict(i=i, restricted=f_r, unrestricted=f_u)))
        rest_cost += f_r
        rest_leases += ls
    B = aN * oe1 + rest_cost
    B1 = oe1 + rest_cost
    cc = class_constants(I, ph, aN)
    cf = closed_forms(I, ph, aN)
    for key, val in cf.items():
        if cc['cA'] > val * (1 + 1e-12):
            V.append(('closed_form_' + key, dict(cA=cc['cA'], val=val)))
    if cc['cA'] > cc['cA_sep'] + 1e-12:
        V.append(('cA_sep', cc))
    # A2 on the whole sigma (Theorem 1(d)'s algorithm), informative
    pd_all = FracPD(I).run()
    a2all = float(np.mean([round_analysed(pd_all, np.random.default_rng(9500 + sd), N)[0]
                           for sd in range(N_SEEDS)]))
    # cross-checks against core.py
    if idx < XCHECK:
        ref = opt_eager(I1)['fun']
        if abs(ref - oe1) > 1e-6 * max(1, ref):
            V.append(('C12_eager_xcheck', dict(ref=ref, mine=oe1)))
    lenders = lender_schedules(I, 86000 + idx)
    for sd in range(N_SEEDS_ADAPT):
        lenders.append((f'adaptive_s{sd}', adaptive_schedule(I, a2[sd][1] + rest_leases)))
    rows = []
    for name, om in lenders:
        plan = omega_plan(I, om)
        if idx < XCHECK and name in ('none', 'bern0.2', 'adaptive_s0'):
            ref = opt_omega(I, om)['fun']
            if abs(ref - plan['fun']) > 1e-4 * max(1, ref):
                V.append(('C12_omega_xcheck', dict(ref=ref, mine=plan['fun'], lender=name)))
        sc = split_checks(I, ph, plan, el, aN, V)
        # C6, C7
        if oe1 > sc['split1_cost'] * (1 + RTOL) + 1e-7:
            V.append(('C6a', dict(oe1=oe1, split=sc['split1_cost'], lender=name)))
        if sc['split1_cost'] > (sc['sum_g1c'] + sc['serv1']) * (1 + RTOL) + 1e-7:
            V.append(('C6b', dict(lender=name)))
        if rest_cost > sc['splitR_cost'] * (1 + RTOL) + 1e-7:
            V.append(('C7a', dict(rest=rest_cost, split=sc['splitR_cost'], lender=name)))
        if sc['splitR_cost'] > (sc['sum_gRc'] + sc['servR']) * (1 + RTOL) + 1e-7:
            V.append(('C7b', dict(lender=name)))
        # C8
        mid = aN * (sc['sum_g1c'] + sc['serv1']) + sc['sum_gRc'] + sc['servR']
        if B > mid * (1 + RTOL) + 1e-7:
            V.append(('C8a', dict(B=B, mid=mid, lender=name)))
        # Step 4: the coefficient is max(alpha_N, max over pi's leases), alpha_N when pi has no lease
        if mid > max(aN, sc['c_pi']) * plan['fun'] * (1 + RTOL) + 1e-7:
            V.append(('C8b', dict(lender=name)))
        if B > cc['cA'] * plan['lb'] * (1 + RTOL) + 1e-7:
            V.append(('C8c', dict(B=B, cA=cc['cA'], opt_lb=plan['lb'], lender=name)))
        # the same chain with alpha = 1 in place of alpha_N (Proposition A(a) for any alpha >= 1)
        mid1 = sc['sum_g1c'] + sc['serv1'] + sc['sum_gRc'] + sc['servR']
        if B1 > mid1 * (1 + RTOL) + 1e-7 or mid1 > max(1.0, sc['c1_pi']) * plan['fun'] * (1 + RTOL) + 1e-7:
            V.append(('C8d', dict(B1=B1, mid1=mid1, lender=name)))
        if B1 > cc['c1'] * plan['lb'] * (1 + RTOL) + 1e-7:
            V.append(('C8e', dict(B1=B1, c1=cc['c1'], opt_lb=plan['lb'], lender=name)))
        # C11: LR's leases live through their windows; realized LR vs c_A OPT_sw
        seeds = [int(name.split('_s')[1])] if name.startswith('adaptive') else list(range(N_SEEDS))
        for (l, j, k, s) in rest_leases + [x for sd in seeds for x in a2[sd][1]]:
            if effective_end(I, om, l, k, s) < s + int(I.L[k]):
                V.append(('C11_life', dict(lender=name)))
        lr = float(np.mean([a2[sd][0] for sd in seeds])) + rest_cost
        if lr > cc['cA'] * plan['lb'] * (1 + RTOL) + 1e-7:
            V.append(('C11_ratio', dict(lr=lr, lender=name)))
        rows.append(dict(lender=name, opt=plan['fun'], opt_lb=plan['lb'], LR=lr,
                         LR_over_opt=lr / plan['lb'] if plan['lb'] > 0 else None,
                         B_over_opt=B / plan['lb'] if plan['lb'] > 0 else None,
                         B1_over_c1opt=B1 / (cc['c1'] * plan['lb']) if plan['lb'] > 0 else None,
                         A2all_over_opt=a2all / plan['lb'] if plan['lb'] > 0 else None,
                         tight_C2=sc['tight']['C2'], tight_C4=sc['tight']['C4'],
                         tight_C6=(oe1 / (sc['sum_g1c'] + sc['serv1'])) if sc['sum_g1c'] + sc['serv1'] > 0 else 0.0,
                         tight_C7=(rest_cost / (sc['sum_gRc'] + sc['servR'])) if sc['sum_gRc'] + sc['servR'] > 0 else 0.0,
                         c_pi=sc['c_pi'], n_leases=len(plan['leases'])))
    return dict(idx=idx, kind=kind, prm=prm, T=I.T, m=I.m, J=I.J, n=I.n, K=I.K, D=[int(x) for x in I.L],
                S=S, P=ph.P_min(), phases=len(ph.starts), rho=I.rho(), N=N, alpha_N=aN,
                OPT_eager_seg=oe1, frac=frac, A2_mean=a2mean, rest=rest_cost, B=B, B1=B1, A2all=a2all,
                consts=cc, closed=cf, rows=rows, violations=V, secs=time.time() - t0)


def summarize(res):
    L = []
    nv = sum(len(r['violations']) for r in res)
    L.append(f'Proposition A check: {len(res)} instances, {sum(len(r["rows"]) for r in res)} '
             f'(instance, lender) pairs, violations {nv}')
    kinds = sorted(set(r['kind'] for r in res))
    L.append(' kind      inst  rho range     P/(rho Dmax) range   max LR/OPT  max B/OPT  max cA   '
             'max A2(sigma)/OPT  tight C2   C4    C6    C7   viol')
    for kd in kinds:
        R = [r for r in res if r['kind'] == kd]
        rows = [w for r in R for w in r['rows'] if w['LR_over_opt'] is not None]
        pr = [r['P'] / (r['rho'] * max(r['D'])) for r in R if math.isfinite(r['P'])]
        L.append(f" {kd:9s} {len(R):4d}  {min(r['rho'] for r in R):4.2f}-{max(r['rho'] for r in R):4.2f}   "
                 f"{(min(pr) if pr else float('nan')):5.2f}-{(max(pr) if pr else float('nan')):5.2f}"
                 f"{' (+single)' if any(not math.isfinite(r['P']) for r in R) else '          '} "
                 f"  {max(w['LR_over_opt'] for w in rows):7.3f}  {max(w['B_over_opt'] for w in rows):8.3f}"
                 f"  {max(r['consts']['cA'] for r in R):7.2f}  {max(w['A2all_over_opt'] for w in rows):10.3f}"
                 f"        {max(w['tight_C2'] for w in rows):5.3f} {max(w['tight_C4'] for w in rows):5.3f}"
                 f" {max(w['tight_C6'] for w in rows):5.3f} {max(w['tight_C7'] for w in rows):5.3f}"
                 f"  {sum(len(r['violations']) for r in R)}")
    L.append(' tightness of the chain with alpha = 1: max B1/(c1 OPT_sw) per kind, B1 = OPT_eager(sigma^1) + '
             'sum_i OPT_eager(sigma^r_i), c1 = max (g1 + gR)')
    for kd in kinds:
        ws = [w for r in res if r['kind'] == kd for w in r['rows'] if w['B1_over_c1opt'] is not None]
        L.append(f"  {kd:9s} max B1/(c1 OPT) {max(w['B1_over_c1opt'] for w in ws):6.4f}   max c1 "
                 f"{max(r['consts']['c1'] for r in res if r['kind'] == kd):6.3f}")
    L.append(' per lender: max LR/OPT_sw, max B/(c_A OPT_sw)')
    lnames = []
    for r in res:
        for w in r['rows']:
            nm = w['lender'].split('_s')[0]
            if nm not in lnames:
                lnames.append(nm)
    for nm in lnames:
        ws = [(r, w) for r in res for w in r['rows'] if w['lender'].split('_s')[0] == nm and w['LR_over_opt']]
        L.append(f"  {nm:9s} pairs {len(ws):4d}  max LR/OPT {max(w['LR_over_opt'] for _, w in ws):7.3f}"
                 f"  max B/(cA OPT) {max(w['B_over_opt'] / r['consts']['cA'] for r, w in ws):6.4f}")
    th = [r for r in res if r['kind'] == 'thm2']
    if th:
        L.append(' Theorem 2 family (one client, always active): LR/OPT_sw under the adaptive rule vs '
                 'rho m/(m+rho-1), and cA')
        for r in th:
            ad = [w for w in r['rows'] if w['lender'].startswith('adaptive')]
            lim = r['rho'] * r['m'] / (r['m'] + r['rho'] - 1)
            L.append(f"  m={r['m']} rho={r['rho']:.0f} P={r['P']:>4} LR/OPT(adaptive) "
                     f"{max(w['LR_over_opt'] for w in ad):6.3f}  limit {lim:5.3f}  A2(sigma)/OPT "
                     f"{max(w['A2all_over_opt'] for w in ad):6.3f}  cA {r['consts']['cA']:6.2f}")
    L.append(f" total time {sum(r['secs'] for r in res):.0f} s")
    if nv:
        L.append(' VIOLATIONS:')
        for r in res:
            for v in r['violations'][:5]:
                L.append(f"  idx {r['idx']} {r['kind']} {v[0]} {v[1]}")
    return '\n'.join(L), nv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reduced', action='store_true')
    ap.add_argument('--workers', type=int, default=int(os.environ.get('ADD_WORKERS', '3')))
    ap.add_argument('--n-rand', type=int, default=600)
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cases = [(i, k, p) for i, (k, p) in enumerate(build_cases(a.reduced, a.n_rand))]
    if a.workers > 1:
        import multiprocessing as mp
        with mp.get_context('spawn').Pool(a.workers) as pool:
            res = list(pool.imap_unordered(run_case, cases))
    else:
        res = [run_case(c) for c in cases]
    res.sort(key=lambda r: r['idx'])
    txt, nv = summarize(res)
    tag = '_reduced' if a.reduced else ''

    def clean(o):
        if isinstance(o, float) and not math.isfinite(o):
            return str(o)
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        return o
    json.dump(clean(res), open(os.path.join(a.out, f'additive{tag}.json'), 'w'), indent=1)
    open(os.path.join(a.out, f'additive{tag}.txt'), 'w').write(txt + '\n')
    print(txt)
    sys.exit(1 if nv else 0)


if __name__ == '__main__':
    main()
