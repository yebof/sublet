"""Audit: (1) (P) with ALL A-constraints has the same optimum as LP_al (tiny instances);
(2) number of raise iterations per request of ORML-PD (termination of the while loop),
including tie-heavy instances (equal tiny delta at many sites)."""
import os, sys, itertools, math
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
from scipy.optimize import linprog
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pd as PD
from core import random_instance, lp_aligned

def solve_P(I):
    # variables: x_F (aligned cols), y_eF, f_e
    el = I.elements()
    cols = {}
    def colid(F):
        if F not in cols: cols[F] = len(cols)
        return cols[F]
    Fe = []
    for (c, t) in el:
        j = int(I.cl_llm[c]); L = []
        for l in range(I.m):
            if np.isfinite(I.delta[c, l]):
                for k in range(I.K):
                    Lk = int(I.L[k]); L.append(((l, j, k, (t // Lk) * Lk), float(I.delta[c, l])))
        Fe.append(L)
        for F, _ in L: colid(F)
    nX = len(cols); yid = []; off = nX
    for L in Fe:
        yid.append(list(range(off, off + len(L)))); off += len(L)
    fid = list(range(off, off + len(el))); nV = off + len(el)
    cost = np.zeros(nV)
    for F, i in cols.items(): cost[i] = I.C(F[0], F[1], F[2])
    for ei, L in enumerate(Fe):
        for (F, dl), yi in zip(L, yid[ei]): cost[yi] = dl
        cost[fid[ei]] = I.q
    rows = []
    for ei, L in enumerate(Fe):
        n = len(L)
        for mask in range(1 << n):
            r = np.zeros(nV)
            for b in range(n):
                if mask >> b & 1: r[cols[L[b][0]]] = -1
                else: r[yid[ei][b]] = -1
            r[fid[ei]] = -1
            rows.append(r)
    res = linprog(cost, A_ub=np.array(rows), b_ub=-np.ones(len(rows)), bounds=(0, None), method='highs')
    return res.fun

print("(1) (P) vs LP_al")
worst = 0
for seed in range(12):
    rng = np.random.default_rng(500 + seed)
    I = random_instance(rng, T=8, m=2, J=1, n=2, K=2)
    p = solve_P(I); a = lp_aligned(I)['fun']
    worst = max(worst, abs(p - a) / max(a, 1e-9))
    print(f"  seed {seed}: (P)={p:.6f} LP_al={a:.6f}")
print(f"  max rel diff {worst:.2e}")

print("(2) raise iterations per request")
calls = [0]
orig = PD._solve_Y
def wrapped(*a, **k):
    calls[0] += 1
    return orig(*a, **k)
PD._solve_Y = wrapped
for tag, slo, tie in [('rand', None, False), ('slo', 0.4, False), ('ties', None, True)]:
    mx = 0; tot = 0; nreq = 0; hits = 0
    for seed in range(6):
        rng = np.random.default_rng(700 + seed)
        I = random_instance(rng, T=24, m=6 if tie else 4, J=1, n=6, K=3, slo=slo)
        if tie:
            I.delta[:] = 0.05
            I.beta[:] = 5.0; I.a[:] = 1.0
        pdr = PD.FracPD(I)
        for (c, t) in I.elements():
            calls[0] = 0
            pdr.process(c, t)
            mx = max(mx, calls[0]); tot += calls[0]; nreq += 1
        hits += pdr.max_iter_hit
    print(f"  {tag}: requests {nreq}, mean iters {tot/nreq:.2f}, max iters {mx}, cap(2000) hits {hits}")
