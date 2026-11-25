"""Independent audit check (unit R3) of Proposition A of design/theory/core_additive.md.

Written from the note's statements and the model of the paper (paper/sections/model.tex §III,
Supplement S-B.1), without importing the builder's check_additive.py, c3/core.py or c3/pd.py.

What it checks, on small instances of the multi-site core that the builder's families do not cover
(unequal phase lengths, S < D_min, the last phase shorter than S, several LLMs with g_j in {1, 2},
contracts not offered at some sites, zero-cost triples, finite and infinite routing costs, demand
that is phase-persistent, phase-predictable only, or arbitrary):

  A0  internal consistency of my MILPs: OPT(sigma, omega_all) by the interval MILP equals the eager
      MILP; OPT(sigma, never) <= OPT(sigma, omega) for random omega (so the never-announcing lender
      minimizes OPT_sw: it is the hardest lender for an omega-free bound); Theorem 1(b)'s conversion
      OPT_eager <= max(2, rho) OPT(sigma, never).
  A1  Lemma A.1(c): OPT_eager(sigma^r_i) with leases restricted to start at or after p_i + S equals
      the unrestricted OPT_eager(sigma^r_i).
  A2  Lemma A.2 and A.3 lease by lease on an optimal plan pi of (sigma, never) (counts n1, nR, n_R
      and the coefficient bounds), and inequality (1) (both halves).
  A3  Proposition A(a), the omega-free bound, for alpha in {1, 2, 8, 40}:
        alpha OPT_eager(sigma^1) + sum_i OPT_eager(sigma^r_i) <= c_A(alpha) OPT(sigma, never)
      and the plan-wise form with pi's leases; since OPT(sigma, never) = OPT_min(sigma) <= OPT_sw for
      every omega (A0), this is the bound against every lender, adaptive included.
  A4  the closed forms of Proposition A(b)-(d) against c_A computed from the triples.
  A5  an adversarial local search over instances maximizing the ratio of A3's two sides.
  A6  Proposition B(b)'s optimum bound OPT(sigma, never) <= SC* ((rho-1) a D + a P0) on set-cover
      instances (SC* by brute force).
  CTRL a negative control that breaks a hypothesis (S > D_min): the bound must fail there,
      which shows the check has power (reported, not counted as violations).
Exit 1 on a violation. Output: out/audit_additive.json and .txt. Usage: audit_additive.py [--reduced]
[--workers W]
"""
import os
import sys
import json
import math
import time
import random
import argparse
import itertools
from multiprocessing import Pool

os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
import scipy.sparse as sp
from scipy.optimize import milp, LinearConstraint, Bounds

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
INF = math.inf
TOL = 1e-6
ALPHAS = (1.0, 2.0, 8.0, 40.0)


# ------------------------------------------------------------------ instance
class Inst:
    """Multi-site core instance. a[l][k]: price per GPU-slot (inf: not offered); bt[j][l][k]: loading
    cost btilde; g[j]: GPUs per replica; tau, H: contracts; cl[c] = LLM, dl[c][l] = routing cost;
    act[c] = sorted active slots; q fallback. Phases: starts (p_0 = 0 < ... ), S."""

    def __init__(self, T, tau, H, a, bt, g, cl, dl, act, q, starts, S):
        self.T, self.tau, self.H = T, list(tau), list(H)
        self.D = [t + h for t, h in zip(tau, H)]
        self.K = len(tau)
        self.a, self.bt, self.g = a, bt, g
        self.m, self.J = len(a), len(g)
        self.cl, self.dl, self.act, self.q = cl, dl, act, q
        self.starts, self.S = list(starts), S

    def to_json(self):
        return dict(T=self.T, tau=self.tau, H=self.H, a=self.a, bt=self.bt, g=self.g, cl=self.cl, dl=self.dl,
                    act=self.act, q=self.q, starts=self.starts, S=self.S)

    @staticmethod
    def from_json(d):
        return Inst(**d)

    def requests(self):
        return [(c, t) for c in range(len(self.cl)) for t in self.act[c]]

    def usable(self):
        out = []
        for l in range(self.m):
            for j in range(self.J):
                if not any(self.cl[c] == j and self.dl[c][l] < INF for c in range(len(self.cl))):
                    continue
                for k in range(self.K):
                    if self.a[l][k] < INF:
                        out.append((l, j, k))
        return out

    def rent(self, l, j, k):
        return self.g[j] * self.a[l][k]

    def C(self, l, j, k):
        return self.bt[j][l][k] + self.rent(l, j, k) * self.D[k]

    def rho_t(self, l, j, k):
        r = self.rent(l, j, k)
        if r == 0:
            return 1.0 if self.bt[j][l][k] == 0 else INF
        return 1.0 + self.bt[j][l][k] / (r * self.D[k])

    def rho(self):
        return max(self.rho_t(*t) for t in self.usable())

    # phases
    def phase_bounds(self):
        ends = self.starts[1:] + [self.T]
        return list(zip(self.starts, ends))

    def P(self):
        pb = self.phase_bounds()
        L = [e - p for p, e in pb[:-1]]
        return float(min(L)) if L else INF

    def intervals(self):
        out = []
        for i, (p, e) in enumerate(self.phase_bounds()):
            out.append(('S', i, p, min(p + self.S, e)))
            if p + self.S < e:
                out.append(('R', i, p + self.S, e))
        return out


# ------------------------------------------------------------------ MILP
def death(I, l, k, s, omega):
    """slot at which a lease (l, k) bought at s dies under omega = {l: set of slots} (None: never)."""
    if omega is None:
        return INF
    for r in sorted(omega.get(l, ())):
        if r >= s + I.tau[k]:
            return r + I.H[k]
    return INF


def solve(I, reqs, mode, omega=None, min_start=0):
    """mode 'eager': columns (l,j,k,s) living exactly D_k (covering [s, min(s+D_k, T)), cost C).
    mode 'held': columns (l,j,k,s,e) for every end e from min(s+D_k, T) up to the death under omega
    (None = never announces), cost btilde + rent max(D_k, e - s). Returns (value, plan) with plan =
    dict(leases=[(l,j,k,s,e,cost)], serv={req index: routing+fallback cost}, route={idx: [l...]})."""
    T = I.T
    need = {}
    for ri, (c, t) in enumerate(reqs):
        for l in range(I.m):
            if I.dl[c][l] < INF:
                need.setdefault((l, I.cl[c]), []).append(ri)
    cols = []
    for (l, j) in need:
        for k in range(I.K):
            if I.a[l][k] == INF:
                continue
            for s in range(min_start, T):
                lo = min(s + I.D[k], T)
                if mode == 'eager':
                    ends = [lo]
                else:
                    hi = min(death(I, l, k, s, omega), T)
                    ends = list(range(lo, max(lo, hi) + 1))
                for e in ends:
                    cost = I.bt[j][l][k] + I.rent(l, j, k) * max(I.D[k], e - s)
                    cols.append((l, j, k, s, e, cost))
    # variables: x (cols), z (req, l), f (req)
    zidx = []
    for ri, (c, t) in enumerate(reqs):
        for l in range(I.m):
            if I.dl[c][l] < INF:
                zidx.append((ri, l))
    nx, nz, nf = len(cols), len(zidx), len(reqs)
    n = nx + nz + nf
    cost = np.zeros(n)
    for i, col in enumerate(cols):
        cost[i] = col[5]
    for i, (ri, l) in enumerate(zidx):
        cost[nx + i] = I.dl[reqs[ri][0]][l]
    cost[nx + nz:] = I.q
    rows, cc, vv, lo_, hi_ = [], [], [], [], []
    r = 0
    # sum_l z + f >= 1
    zof = {}
    for i, (ri, l) in enumerate(zidx):
        zof.setdefault(ri, []).append(i)
    for ri in range(nf):
        for i in zof.get(ri, []):
            rows.append(r); cc.append(nx + i); vv.append(1.0)
        rows.append(r); cc.append(nx + nz + ri); vv.append(1.0)
        lo_.append(1.0); hi_.append(INF); r += 1
    # z_{ri,l} <= sum of covering cols at (l, j_c)
    cov = {}
    for ci, (l, j, k, s, e, _) in enumerate(cols):
        for t in range(s, e):
            cov.setdefault((l, j, t), []).append(ci)
    for i, (ri, l) in enumerate(zidx):
        c, t = reqs[ri]
        rows.append(r); cc.append(nx + i); vv.append(1.0)
        for ci in cov.get((l, I.cl[c], t), []):
            rows.append(r); cc.append(ci); vv.append(-1.0)
        lo_.append(-INF); hi_.append(0.0); r += 1
    if r == 0:
        return 0.0, dict(leases=[], serv={}, route={})
    A = sp.csr_matrix((vv, (rows, cc)), shape=(r, n))
    integ = np.zeros(n); integ[:nx] = 1
    res = milp(cost, constraints=LinearConstraint(A, lo_, hi_), integrality=integ,
               bounds=Bounds(np.zeros(n), np.ones(n)),
               options=dict(mip_rel_gap=1e-9, time_limit=600))
    if res.status != 0:
        raise RuntimeError(f'milp status {res.status}: {res.message}')
    x = res.x
    leases = [cols[i] for i in range(nx) if x[i] > 0.5]
    serv, route = {}, {}
    for ri in range(nf):
        serv[ri] = I.q * x[nx + nz + ri]
    for i, (ri, l) in enumerate(zidx):
        if x[nx + i] > 1e-9:
            serv[ri] += I.dl[reqs[ri][0]][l] * x[nx + i]
            route.setdefault(ri, []).append(l)
    return float(res.fun), dict(leases=leases, serv=serv, route=route)


# ------------------------------------------------------------------ coefficients (as in the note)
def g1(rho, D, S, P):
    if P == INF:
        return 1.0
    simple = 1.0 + (S + rho * D) / P
    den = P + (rho - 1) * D - S
    refined = max(1.0, 2 * rho * D / den, rho * D / P) if den > 0 else INF
    return min(simple, refined)


def gr(rho, D, S, P):
    v = max(1.0 + S / D, rho)
    if D >= S + 2:
        v += (D - 1 - S) * (2.0 / D + (rho / P if P < INF else 0.0))
    return v


def cA(I, alpha):
    S, P = I.S, I.P()
    vals = [alpha * g1(I.rho_t(*t), I.D[t[2]], S, P) + gr(I.rho_t(*t), I.D[t[2]], S, P) for t in I.usable()]
    return max(vals) if vals else alpha


# ------------------------------------------------------------------ evaluation of one instance
def split_requests(I):
    reqs = I.requests()
    seg, rest = [], {}
    kind = {}
    for (kd, i, x0, x1) in I.intervals():
        for t in range(x0, x1):
            kind[t] = (kd, i)
    for (c, t) in reqs:
        kd, i = kind[t]
        if kd == 'S':
            seg.append((c, t))
        else:
            rest.setdefault(i, []).append((c, t))
    return reqs, seg, rest


def evaluate(I, full=True, rng=None):
    """Returns dict of measured quantities and a list of violations."""
    V = []
    reqs, seg, rest = split_requests(I)
    S, P = I.S, I.P()
    opt_min, plan = solve(I, reqs, 'held', None)
    E1, _ = solve(I, seg, 'eager')
    E2 = {}
    for i, rq in rest.items():
        E2[i], _ = solve(I, rq, 'eager')
        if full:
            e2r, _ = solve(I, rq, 'eager', min_start=I.starts[i] + S)
            if e2r > E2[i] * (1 + TOL) + TOL:
                V.append(('A1_restricted_rest_plan_costs_more', i, E2[i], e2r))
    sumE2 = sum(E2.values())
    plen = [e - p for p, e in I.phase_bounds()[:-1]]
    out = dict(opt_min=opt_min, E1=E1, E2=sumE2, rho=I.rho(), P=P, S=S, Dmin=min(I.D), Dmax=max(I.D), m=I.m,
               nphase=len(I.starts), unequal=len(set(plen)) > 1, last_short=(I.T - I.starts[-1]) < S)
    # A0
    if full:
        eag, _ = solve(I, reqs, 'eager')
        all_omega = {l: set(range(I.T)) for l in range(I.m)}
        held_all, _ = solve(I, reqs, 'held', all_omega)
        if abs(held_all - eag) > TOL * max(1, eag):
            V.append(('A0_eager_mismatch', eag, held_all))
        if eag > max(2.0, I.rho()) * opt_min * (1 + TOL) + TOL:
            V.append(('A0_thm1b', eag, opt_min))
        if rng is not None:
            for _ in range(2):
                p = rng.choice((0.05, 0.3, 0.7))
                om = {l: {t for t in range(I.T) if rng.random() < p} for l in range(I.m)}
                o, _ = solve(I, reqs, 'held', om)
                if o < opt_min * (1 - TOL) - TOL:
                    V.append(('A0_never_not_min', opt_min, o))
        out['opt_eager'] = eag
    # A2: lemma checks on pi
    ivs = I.intervals()
    seg_ri = set(i for i, r in enumerate(reqs) if r in set(seg))
    serv1 = sum(v for ri, v in plan['serv'].items() if ri in seg_ri)
    servR = sum(v for ri, v in plan['serv'].items() if ri not in seg_ri)
    sumn1C = sumnRC = 0.0
    sum_g1c = sum_grc = 0.0
    cpi = {a: a for a in ALPHAS}
    nt = dict(A2=0.0, A3=0.0)     # tightness over leases with a coefficient above its trivial value
    for (l, j, k, s, e, cL) in plan['leases']:
        D = I.D[k]
        CL = I.C(l, j, k)
        rhoL = I.rho_t(l, j, k)
        length = max(e - s, D)
        n1 = nR = nRst = 0
        for (kd, i, x0, x1) in ivs:
            lo, hi = max(s, x0), min(e, x1)
            if lo >= hi:
                continue
            if kd == 'S':
                n1 += 1
            else:
                nRst += 1
                nR += math.ceil((hi - lo) / D)
        if P < INF:
            if n1 > math.ceil((length + S) / P - 1e-12):
                V.append(('A2_lemmaA2i', n1, length, S, P))
            if not nRst < 2 + (length - S) / P + 1e-12:
                V.append(('A2_lemmaA3i', nRst, length, S, P))
        else:
            if n1 > 1 or nRst > 1:
                V.append(('A2_single_phase_counts', n1, nRst))
        if nR > (length + S) / D + nRst * max(0, D - 1 - S) / D + 1e-9:
            V.append(('A2_lemmaA3ii', nR, length, S, D, nRst))
        G1, GR = g1(rhoL, D, S, P), gr(rhoL, D, S, P)
        if n1 * CL > G1 * cL * (1 + TOL) + 1e-9:
            V.append(('A2_lemmaA2ii', n1, CL, cL, G1))
        if nR * CL > GR * cL * (1 + TOL) + 1e-9:
            V.append(('A2_lemmaA3iii', nR, CL, cL, GR))
        if G1 > 1 + 1e-9 and cL > 0:
            nt['A2'] = max(nt['A2'], n1 * CL / (G1 * cL))
        if GR > max(1.0 + S / D, 1.0) + 1e-9 and cL > 0 and nR > 0:
            nt['A3'] = max(nt['A3'], nR * CL / (GR * cL))
        sumn1C += n1 * CL
        sumnRC += nR * CL
        sum_g1c += G1 * cL
        sum_grc += GR * cL
        for a in ALPHAS:
            cpi[a] = max(cpi[a], a * G1 + GR)
    if E1 > sumn1C + serv1 + TOL * max(1, E1):
        V.append(('A2_ineq1_seg', E1, sumn1C, serv1))
    if sumE2 > sumnRC + servR + TOL * max(1, sumE2):
        V.append(('A2_ineq1_rest', sumE2, sumnRC, servR))
    # A3, A4
    ratios = {}
    for a in ALPHAS:
        B = a * E1 + sumE2
        c = cA(I, a)
        ratios[a] = B / (c * opt_min) if opt_min > 0 else (0.0 if B <= TOL else INF)
        if B > c * opt_min * (1 + TOL) + TOL:
            V.append(('A3_propA', a, B, c, opt_min))
        if B > cpi[a] * opt_min * (1 + TOL) + TOL:
            V.append(('A3_planwise', a, B, cpi[a], opt_min))
        rho, Dmax = I.rho(), max(I.D)
        small = all(D <= S + 1 for D in I.D)
        if P >= rho * Dmax:
            bnd = 3 * a + max(2, rho) + (0 if small else 3)
            if c > bnd + 1e-9:
                V.append(('A4_b', a, c, bnd))
            if rho >= 2:
                bnd2 = rho / (rho - 1) * a + rho + (0 if small else 3)
                if c > bnd2 + 1e-9:
                    V.append(('A4_b_rho2', a, c, bnd2))
        if P >= (rho + 1) * Dmax + S:
            bnd = a + max(2, rho) + (0 if small else 3)
            if c > bnd + 1e-9:
                V.append(('A4_c', a, c, bnd))
    out['ratio'] = ratios
    out['nontrivial'] = nt
    out['nleases'] = len(plan['leases'])
    out['tight_ineq1_seg'] = E1 / (sum_g1c + serv1) if sum_g1c + serv1 > 0 else 0.0
    out['tight_ineq1_rest'] = sumE2 / (sum_grc + servR) if sum_grc + servR > 0 else 0.0
    return out, V


# ------------------------------------------------------------------ generators
def gen_instance(rng, demand=None):
    T = rng.randint(6, 16)
    K = rng.choice((1, 2, 2))
    D1 = rng.choice((1, 2, 3))
    Ds = [D1] if K == 1 else [D1, rng.randint(D1, 8)]
    tau = [rng.randint(1, D) for D in Ds]
    H = [D - t for D, t in zip(Ds, tau)]
    m = rng.choice((1, 2, 3))
    J = rng.choice((1, 1, 2))
    g = [rng.choice((1, 2)) for _ in range(J)]
    a = [[rng.choice((0.5, 1.0, 2.0, 1.0, INF if k > 0 else 1.0)) for k in range(K)] for _ in range(m)]
    if rng.random() < 0.1:
        a[0][0] = 0.0
    bt = []
    shared = rng.random() < 0.4
    for j in range(J):
        row = []
        for l in range(m):
            base = rng.choice((0.0, 1.0, 3.0, 8.0, 20.0))
            cells = []
            for k in range(K):
                if a[l][k] == 0.0:
                    cells.append(0.0)
                elif shared:
                    cells.append(base)
                else:
                    rho = rng.choice((1.0, 1.5, 2.0, 3.0, 5.0, 8.0))
                    cells.append((rho - 1) * g[j] * (a[l][k] if a[l][k] < INF else 1.0) * Ds[k])
            row.append(cells)
        bt.append(row)
    Dmin = min(Ds)
    S = rng.randint(1, Dmin)
    # phases, unequal lengths, non-last phases >= S
    starts = [0]
    while True:
        Lp = rng.randint(S, max(S, 3 * max(Ds) + 2))
        if starts[-1] + Lp >= T or rng.random() < 0.25:
            break
        starts.append(starts[-1] + Lp)
    n = rng.randint(1, 4)
    cl = [rng.randrange(J) for _ in range(n)]
    dl = []
    for c in range(n):
        row = [rng.choice((0.0, 0.0, 0.3, 1.0, INF)) for _ in range(m)]
        if all(x == INF for x in row):
            row[rng.randrange(m)] = 0.0
        dl.append(row)
    q = rng.choice((2.0, 5.0, 15.0, 100.0))
    I = Inst(T, tau, H, a, bt, g, cl, dl, [[] for _ in range(n)], q, starts, S)
    mode = demand or rng.choice(('persistent', 'persistent', 'predictable', 'arbitrary', 'always'))
    fill_demand(I, rng, mode)
    return I, mode


def fill_demand(I, rng, mode):
    n = len(I.cl)
    act = [set() for _ in range(n)]
    pb = I.phase_bounds()
    for c in range(n):
        if mode == 'always':
            act[c] = set(range(I.T))
        elif mode == 'arbitrary':
            p = rng.choice((0.2, 0.5, 0.8))
            act[c] = {t for t in range(I.T) if rng.random() < p}
        else:
            for (p0, p1) in pb:
                if rng.random() < 0.7:
                    tc = rng.randint(p0, min(p0 + I.S, p1) - 1)
                    if mode == 'persistent':
                        act[c] |= set(range(tc, p1))
                    else:   # predictable: some pattern in the rest, fixed function of the segment
                        act[c] |= {tc}
                        act[c] |= {t for t in range(p0 + I.S, p1) if (t - tc) % rng.choice((1, 2, 3)) == 0}
    I.act = [sorted(s) for s in act]
    if not any(I.act):
        I.act[0] = [0]


def mutate(I, rng):
    J = Inst.from_json(json.loads(json.dumps(I.to_json(), default=lambda o: o)))
    J.act = [list(x) for x in I.act]
    r = rng.random()
    if r < 0.4:
        c = rng.randrange(len(J.cl)); t = rng.randrange(J.T)
        s = set(J.act[c])
        s ^= {t}
        J.act[c] = sorted(s)
        if not any(J.act):
            J.act[c] = [t]
    elif r < 0.55:
        # stretch or shrink a client's interval inside a phase
        c = rng.randrange(len(J.cl))
        p0, p1 = rng.choice(J.phase_bounds())
        tc = rng.randint(p0, p1 - 1)
        s = set(J.act[c]) - set(range(p0, p1))
        s |= set(range(tc, p1)) if rng.random() < 0.7 else set(range(p0, tc + 1))
        J.act[c] = sorted(s)
    elif r < 0.75:
        j = rng.randrange(J.J); l = rng.randrange(J.m); k = rng.randrange(J.K)
        if J.a[l][k] not in (0.0, INF):
            J.bt[j][l][k] = max(0.0, J.bt[j][l][k] * rng.choice((0.5, 0.8, 1.25, 2.0)) + rng.choice((0.0, 0.5)))
    elif r < 0.85:
        c = rng.randrange(len(J.cl)); l = rng.randrange(J.m)
        J.dl[c][l] = rng.choice((0.0, 0.3, 1.0, INF))
        if all(x == INF for x in J.dl[c]):
            J.dl[c][l] = 0.0
    elif r < 0.95:
        # move a phase boundary (keeping non-last phases >= S)
        if len(J.starts) > 1:
            i = rng.randrange(1, len(J.starts))
            cand = J.starts[i] + rng.choice((-1, 1))
            st = J.starts[:i] + [cand] + J.starts[i + 1:]
            ok = all(st[x + 1] - st[x] >= J.S for x in range(len(st) - 1)) and st[-1] < J.T and st[0] == 0
            if ok:
                J.starts = st
    else:
        J.q = max(0.5, J.q * rng.choice((0.5, 2.0)))
    return J


# ------------------------------------------------------------------ jobs
def job_random(seed):
    rng = random.Random(seed)
    I, mode = gen_instance(rng)
    t0 = time.time()
    try:
        out, V = evaluate(I, full=True, rng=rng)
    except Exception as ex:   # noqa: BLE001
        return dict(seed=seed, error=repr(ex), inst=I.to_json())
    return dict(seed=seed, mode=mode, out=out, V=V, inst=I.to_json() if V else None, secs=time.time() - t0)


def job_search(args):
    seed, steps, alpha = args
    rng = random.Random(seed)
    I, mode = gen_instance(rng, demand=rng.choice(('persistent', 'always', 'arbitrary')))
    try:
        out, V = evaluate(I, full=False)
    except Exception as ex:   # noqa: BLE001
        return dict(seed=seed, error=repr(ex))
    best, bestI, allV = out['ratio'][alpha], I, list(V)
    for _ in range(steps):
        J = mutate(bestI, rng)
        try:
            o, V2 = evaluate(J, full=False)
        except Exception:      # noqa: BLE001
            continue
        if V2:
            allV += V2
            return dict(seed=seed, alpha=alpha, best=o['ratio'][alpha], V=allV, inst=J.to_json())
        if o['ratio'][alpha] > best:
            best, bestI = o['ratio'][alpha], J
    return dict(seed=seed, alpha=alpha, best=best, V=allV, inst=bestI.to_json())


def controls():
    """Instances that break a hypothesis: the inequality of A3 must fail on them."""
    res = []
    # S > D_min: one contract D = 1, segment of 3 slots, one always-active client, rho = 6
    rho = 6.0
    I = Inst(3, [1], [0], [[1.0]], [[[(rho - 1) * 1.0]]], [1], [0], [[0.0]], [[0, 1, 2]], 100.0, [0], 3)
    reqs, seg, rest = split_requests(I)
    opt, _ = solve(I, reqs, 'held')
    E1, _ = solve(I, seg, 'eager')
    a = 40.0
    c = a * 1.0 + gr(rho, 1, 3, INF)
    res.append(dict(name='S>Dmin', B=a * E1, cA_opt=c * opt, fails=a * E1 > c * opt))
    return res


def setcover_A6(rng, n_inst):
    """Proposition B(b): OPT(sigma, never) <= SC* ((rho-1) a D + a P0) on random set-cover instances."""
    V, rec = [], []
    for _ in range(n_inst):
        M = rng.randint(2, 4)
        ne = rng.randint(1, 4)
        D = rng.randint(ne, ne + 2)
        P0 = rng.choice((D, D + 2, 2 * D + 1))
        rho = rng.choice((1.5, 2.0, 4.0))
        aa = 1.0
        sets = [set(e for e in range(ne) if rng.random() < 0.5) for _ in range(M)]
        for e in range(ne):
            if not any(e in s for s in sets):
                sets[rng.randrange(M)].add(e)
        order = list(range(ne)); rng.shuffle(order)
        dl = [[0.0 if e in sets[l] else INF for l in range(M)] for e in order]
        act = [list(range(t, P0)) for t in range(ne)]
        tau = rng.randint(1, D)
        I = Inst(P0, [tau], [D - tau], [[aa] for _ in range(M)], [[[(rho - 1) * aa * D] for _ in range(M)]], [1],
                 [0] * ne, dl, act, rho * aa * D, [0], D)
        opt, _ = solve(I, I.requests(), 'held')
        sc = min(len(cmb) for r in range(1, M + 1) for cmb in itertools.combinations(range(M), r)
                 if set().union(*[sets[i] for i in cmb]) >= set(range(ne)))
        bnd = sc * ((rho - 1) * aa * D + aa * P0)
        rec.append(dict(M=M, ne=ne, D=D, P0=P0, rho=rho, opt=opt, bound=bnd))
        if opt > bnd * (1 + TOL):
            V.append(('A6_setcover_opt', opt, bnd))
    return V, rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reduced', action='store_true')
    ap.add_argument('--workers', type=int, default=3)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    n_rand = 40 if args.reduced else 3000
    n_search, steps = (4, 6) if args.reduced else (120, 80)
    allV, errors = [], []
    with Pool(args.workers) as pool:
        rand = pool.map(job_random, range(1000, 1000 + n_rand), chunksize=4)
        sargs = [(5000 + i, steps, ALPHAS[0] if i % 2 == 0 else ALPHAS[-1]) for i in range(n_search)]
        srch = pool.map(job_search, sargs, chunksize=1)
    stats = dict(modes={}, max_ratio={a: 0.0 for a in ALPHAS}, max_ineq1_seg=0.0, max_ineq1_rest=0.0,
                 closed_b=0, closed_c=0, S_lt_Dmin=0, unequal_phases=0, single_phase=0, rho_ge_m=0)
    for r in rand:
        if 'error' in r:
            errors.append(r); continue
        allV += [(r['seed'],) + tuple(v) for v in r['V']]
        o = r['out']
        stats['modes'][r['mode']] = stats['modes'].get(r['mode'], 0) + 1
        for a in ALPHAS:
            stats['max_ratio'][a] = max(stats['max_ratio'][a], o['ratio'][a])
        stats['max_ineq1_seg'] = max(stats['max_ineq1_seg'], o['tight_ineq1_seg'])
        stats['max_ineq1_rest'] = max(stats['max_ineq1_rest'], o['tight_ineq1_rest'])
        stats['nt_A2'] = max(stats.get('nt_A2', 0.0), o['nontrivial']['A2'])
        stats['nt_A3'] = max(stats.get('nt_A3', 0.0), o['nontrivial']['A3'])
        if o['nleases'] > 0 and o['P'] < INF:
            stats['ineq1_seg_nontriv'] = max(stats.get('ineq1_seg_nontriv', 0.0), o['tight_ineq1_seg'])
            stats['ineq1_rest_nontriv'] = max(stats.get('ineq1_rest_nontriv', 0.0), o['tight_ineq1_rest'])
            for a in ALPHAS:
                k = f'ratio_multi_{a:g}'
                stats[k] = max(stats.get(k, 0.0), o['ratio'][a])
        stats['closed_b'] += int(o['P'] >= o['rho'] * o['Dmax'])
        stats['closed_c'] += int(o['P'] >= (o['rho'] + 1) * o['Dmax'] + o['S'])
        stats['S_lt_Dmin'] += int(o['S'] < o['Dmin'])
        stats['single_phase'] += int(o['P'] == INF)
        stats['unequal_phases'] += int(o['unequal'])
        stats['rho_ge_m'] += int(o['rho'] >= o['m'])
    search = []
    for r in srch:
        if 'error' in r:
            errors.append(r); continue
        allV += [('search', r['seed']) + tuple(v) for v in r['V']]
        search.append(dict(seed=r['seed'], alpha=r['alpha'], best=r['best']))
    rngc = random.Random(77)
    v6, rec6 = setcover_A6(rngc, 10 if args.reduced else 120)
    allV += v6
    ctrl = controls()
    best_search = {a: max([s['best'] for s in search if s['alpha'] == a], default=0.0) for a in (ALPHAS[0], ALPHAS[-1])}
    rec = dict(n_random=n_rand, n_search=n_search, steps=steps, stats=stats, search=search, best_search=best_search,
               setcover=rec6, controls=ctrl, violations=[list(map(str, v)) for v in allV],
               errors=[str(e) for e in errors], secs=round(time.time() - t0, 1))
    suf = '_reduced' if args.reduced else ''
    with open(os.path.join(OUT, f'audit_additive{suf}.json'), 'w') as fh:
        json.dump(rec, fh, indent=1, default=str)
    lines = [
        'Audit R3: independent check of Proposition A (design/theory/core_additive.md)',
        f'random instances {n_rand} (modes {stats["modes"]}), with S < D_min {stats["S_lt_Dmin"]}, '
        f'one phase {stats["single_phase"]}, unequal phase lengths {stats["unequal_phases"]}, rho >= m {stats["rho_ge_m"]}, closed form (b) applies {stats["closed_b"]}, (c) {stats["closed_c"]}',
        'largest ratio (alpha OPT_eager(sigma^1) + sum_i OPT_eager(sigma^r_i)) / (c_A(alpha) OPT(sigma, never)): ' +
        ', '.join(f'alpha={a:g}: {stats["max_ratio"][a]:.4f}' for a in ALPHAS),
        f'inequality (1) tightness: segments {stats["max_ineq1_seg"]:.4f}, rests {stats["max_ineq1_rest"]:.4f} '
        '(left side over sum gamma c_L + serv; attained trivially, e.g. by plans without leases); on instances '
        f'with several phases and a plan with leases: {stats.get("ineq1_seg_nontriv", 0):.4f}, '
        f'{stats.get("ineq1_rest_nontriv", 0):.4f}',
        f'lemma tightness over leases whose coefficient exceeds its trivial value: A.2 {stats.get("nt_A2", 0):.4f}, '
        f'A.3 {stats.get("nt_A3", 0):.4f}',
        'ratio on instances with several phases and leases: ' +
        ', '.join(f'alpha={a:g}: {stats.get(f"ratio_multi_{a:g}", 0):.4f}' for a in ALPHAS),
        f'adversarial search ({n_search} starts x {steps} steps): best ratio alpha=1: {best_search[ALPHAS[0]]:.4f}, '
        f'alpha={ALPHAS[-1]:g}: {best_search[ALPHAS[-1]]:.4f}',
        f'Proposition B(b) optimum bound on {len(rec6)} set-cover instances: max OPT/bound '
        f'{max(r["opt"] / r["bound"] for r in rec6):.4f}',
        'negative controls: ' + '; '.join(f'{c["name"]}: B={c["B"]:.2f} vs c_A OPT={c["cA_opt"]:.2f} fails={c["fails"]}'
                                          for c in ctrl),
        f'errors {len(errors)}',
        f'violations {len(allV)}',
    ] + [f'  {v}' for v in allV[:50]] + [f'time {rec["secs"]} s']
    with open(os.path.join(OUT, f'audit_additive{suf}.txt'), 'w') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    sys.exit(1 if (allV or errors) else 0)


if __name__ == '__main__':
    main()
