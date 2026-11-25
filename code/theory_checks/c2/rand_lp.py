"""Randomized C2 game: optimal randomized competitive ratio against an oblivious adversary,
solved as a sequence-form LP over discretized behavioral strategies.

Behavioral strategy: a distribution over pre-notice plans {none, protected at s, revocable at s}
(planned pre-notice upgrades r->p are omitted; see the write-up), and, for every possible notice
(window end R) and information state at the notice (nothing held / revocable held since s), a
distribution over post-notice options (same option sets as det_game.py).  Perfect recall lets the
post-notice distributions of all plans that reach the same state with the same sunk cost be merged.
Constraint per environment (R, x): E[ALG]/OPT <= c.  Minimize c.
Discretization: decisions on grid G (step dt), adversary R in G U (G+eps), x in X.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from model import Params, opt_cost, make_grids, INF
np.seterr(invalid='ignore', over='ignore')


def _post_opts_N(Xa, a, R, P, G, Vmax):
    b, al, ap, mu, lam, tau = P.beta, P.alpha, P.ap, P.mu, P.lam, P.tau
    opts = [Xa.copy()]
    if P.allow_p:
        for u in G[(G >= a - 1e-12) & (G <= a + Vmax)]:
            opts.append(np.where(Xa <= u, Xa, u + b + ap * (Xa - u)))
    for u in G[(G >= a - 1e-12) & (G < R - 1e-12)]:
        E = max(R, u + tau)
        pre = np.where(Xa <= u, Xa, u + b + al * (np.minimum(Xa, E) - u))
        atE = u + b + al * (E - u)
        opts += _reactions(Xa, E, u, pre, atE, P, G, Vmax)
    return opts


def _reactions(Xa, E, tmin, pre, atE, P, G, Vmax):
    b, ap, mu, lam = P.beta, P.ap, P.mu, P.lam
    out = [np.where(Xa > E, atE + mu + (Xa - E), pre)]
    if P.allow_p:
        for v in G[(G >= E - 1e-12) & (G <= E + Vmax)]:
            out.append(np.where(Xa > E, atE + mu + np.where(Xa <= v, Xa - E, v - E + b + ap * (Xa - v)), pre))
        if E - lam >= tmin - 1e-12:
            d = E - lam
            out.append(np.where(Xa > E, atE + b + ap * (Xa - E), np.where(Xa > d, pre + b, pre)))
    return out


def solve_rand(P, dt=0.2, T=8.0, Rmax=5.0, Ts=4.0, Vmax=4.0, verbose=False):
    G, X, RG = make_grids(P, dt, T, Rmax)
    b, al, ap = P.beta, P.alpha, P.ap
    Ts = min(Ts, Rmax - P.H - 1.0)
    S = G[G <= Ts + 1e-9]
    ns = len(S)
    # variable layout
    nv = 1
    i_none = nv; nv += 1
    i_p = None
    if P.allow_p:
        i_p = nv; nv += ns
    i_r = nv; nv += ns
    rows, cols, vals = [], [], []
    eq_r, eq_c, eq_v, eq_b = [], [], [], []
    nrow = 0; neq = 0
    # equality: plan probabilities sum to 1
    for j in range(i_none, i_r + ns):
        eq_r.append(neq); eq_c.append(j); eq_v.append(1.0)
    eq_b.append(1.0); neq += 1
    # R = inf rows
    Oinf = opt_cost(X, INF, P)
    for k, x in enumerate(X):
        cs = [(i_none, x)]
        for i, s in enumerate(S):
            if P.allow_p:
                cs.append((i_p + i, x if x <= s else s + b + ap * (x - s)))
            cs.append((i_r + i, x if x <= s else s + b + al * (x - s)))
        for j, c in cs:
            rows.append(nrow); cols.append(j); vals.append(c / Oinf[k])
        rows.append(nrow); cols.append(0); vals.append(-1.0); nrow += 1
    # finite R
    for R in RG:
        a = max(0.0, R - P.H)
        Xa = np.unique(np.concatenate([X[X > a + 1e-12], [a + 2e-7, R + 2e-7, R - P.lam + 2e-7]]))
        Xa = Xa[Xa > a + 1e-12]
        O = opt_cost(Xa, R, P, G)
        nx = len(Xa)
        block = []   # list of (var index, cost vector)
        # state N
        optsN = _post_opts_N(Xa, a, R, P, G, Vmax)
        idxN = list(range(nv, nv + len(optsN))); nv += len(optsN)
        block += list(zip(idxN, optsN))
        for j in idxN:
            eq_r.append(neq); eq_c.append(j); eq_v.append(1.0)
        eq_r.append(neq); eq_c.append(i_none); eq_v.append(-1.0)
        for i, s in enumerate(S):
            if s >= a - 1e-12:
                if P.allow_p:
                    eq_r.append(neq); eq_c.append(i_p + i); eq_v.append(-1.0)
                eq_r.append(neq); eq_c.append(i_r + i); eq_v.append(-1.0)
        eq_b.append(0.0); neq += 1
        # protected held, revocable held
        for i, s in enumerate(S):
            if s >= a - 1e-12:
                break
            if P.allow_p:
                block.append((i_p + i, s + b + ap * (Xa - s)))
            E = max(R, s + P.tau)
            C = s + b + al * (a - s)
            pre = C + al * (np.minimum(Xa, E) - a)
            atE = C + al * (E - a)
            optsR = _reactions(Xa, E, a, pre, atE, P, G, Vmax)
            idx = list(range(nv, nv + len(optsR))); nv += len(optsR)
            block += list(zip(idx, optsR))
            for j in idx:
                eq_r.append(neq); eq_c.append(j); eq_v.append(1.0)
            eq_r.append(neq); eq_c.append(i_r + i); eq_v.append(-1.0)
            eq_b.append(0.0); neq += 1
        js = np.array([j for j, _ in block])
        C = np.array([c for _, c in block]) / O[None, :]       # (nvars_block, nx)
        for k in range(nx):
            rows.extend([nrow] * len(js)); cols.extend(js.tolist()); vals.extend(C[:, k].tolist())
            rows.append(nrow); cols.append(0); vals.append(-1.0); nrow += 1
    A = coo_matrix((vals, (rows, cols)), shape=(nrow, nv)).tocsr()
    Aeq = coo_matrix((eq_v, (eq_r, eq_c)), shape=(neq, nv)).tocsr()
    cvec = np.zeros(nv); cvec[0] = 1.0
    if verbose:
        print(f"LP: {nv} vars, {nrow} ineq, {neq} eq, nnz {A.nnz}", flush=True)
    res = linprog(cvec, A_ub=A, b_ub=np.zeros(nrow), A_eq=Aeq, b_eq=np.array(eq_b),
                  bounds=[(0, None)] * nv, method='highs')
    assert res.status == 0, res.message
    xsol = res.x
    plan = dict(none=xsol[i_none], r={float(S[i]): xsol[i_r + i] for i in range(ns) if xsol[i_r + i] > 1e-6})
    if P.allow_p:
        plan['p'] = {float(S[i]): xsol[i_p + i] for i in range(ns) if xsol[i_p + i] > 1e-6}
    return dict(CR=float(res.fun), plan=plan)


if __name__ == '__main__':
    import sys
    # self-test: RRL randomized, H=0, alpha=0 (report.md 5C: mu/B=0.5/1/2 -> 1.735/1.865/2.085 continuous)
    for mu in [0.5, 1, 2]:
        r = solve_rand(Params(mu=mu, allow_p=False), dt=0.05, T=8, Rmax=5, Ts=4, verbose=True)
        print(f"RRL rand mu={mu}: LP={r['CR']:.4f}", flush=True)
