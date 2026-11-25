"""The two-contract composition game of design/theory/core_additive.md §5: exact values.

Game G(rho, rho2, X). One client is active on [0, l) with the stop l chosen by the adversary
(oblivious demand, revealed slot by slot). Contract 1 has window 1 (tau=1, H=0), rent 1 and
loading cost rho-1, so C_1 = rho and exposure rho; contract 2 has window X, up-front cost X and
exposure rho2 (rent 1/rho2, loading cost X(1-1/rho2)). Fallback costs q >= rho, so it is never
better than a contract-1 lease. The lender is Theorem 2(a)'s adaptive rule (announce at a site
whenever a lease of the algorithm there reaches age tau), with more sites than the horizon, so
every lease of the algorithm dies at age D_k and the optimum holds one lease at a silent site:
    OPT(l) = min(rho - 1 + l, X(1 - 1/rho2) + max(l, X)/rho2)        (Lemma K.1)
A deterministic algorithm is a fixed schedule of purchases (contract 1 covers one slot, contract 2
covers X slots), executed while the client stays; ALG(l) is the cost of the purchases made before
coverage reaches l.

Computed, for rho in {2,4,8,16}, X/rho^2 in {1,4,16}, rho2 in {2, rho}:
  det      exact min over all schedules of max_{l<=L} ALG(l)/OPT(l) (DP + bisection), L = 4X, with an
           upper bound for every l (the schedule extended by contract 2 forever, the tail of Lemma K.4);
  det_sw   the same over switch-time schedules (contract 1 for t slots, then contract 2 forever);
  det_lb   the analytic lower bound min(rho rho2, min_t (rho t + X)/min(rho + t, X)) of Lemma K.2,
           which equals rho + 1 - rho^2/X for integer rho and X >= rho^2;
  rnd      the randomized value over all algorithms: the exact value of the game with l <= L by a
           sequence-form LP (behavioral strategies on the coverage points), cross-checked by its Yao
           certificate (dual weights on l against the exact best response, a DP over all schedules);
           lb = max(that value, rho2) (Lemma K.3), ub = the better of the switch-time mixture and the
           LP's strategy restricted to contract 2 from coverage 5X on, each evaluated at every l
           (Lemma K.4 for the tail); when the switch mixture attains rho2 the value is rho2 and the
           sequence-form LPs are skipped;
  rnd_sw   the LP value over switch-time distributions (t on a grid for L > 2048).
Checks (exit 1 on a violation): OPT's closed form against a DP for X <= 256; det >= det_lb; the
upper bounds >= the lower bounds; det = det_sw; rnd_lb <= rnd_ub <= det, bracket within 0.2%;
the LP value = its Yao certificate.
Output: out/k2_composition.json, out/k2_composition.txt. Usage: check_k2_composition.py [--reduced]
"""
import os
import sys
import json
import math
import time
import argparse
import numpy as np
from scipy.optimize import linprog

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
E_RATIO = math.e / (math.e - 1)


def opt_closed(rho, rho2, X, ls):
    ls = np.asarray(ls, dtype=float)
    return np.minimum(rho - 1 + ls, X * (1 - 1 / rho2) + np.maximum(ls, X) / rho2)


def opt_dp(rho, rho2, X, L):
    """min cost to cover [0, l) with leases held as long as wanted (no announcements), both
    contracts, for l = 1..L: opt[v] = min_{u < v, k} opt[u] + btilde_k + a_k max(v - u, D_k)."""
    b = [rho - 1.0, X * (1 - 1 / rho2)]
    a = [1.0, 1.0 / rho2]
    D = [1, X]
    INF = float('inf')
    opt = [0.0] + [INF] * L
    for v in range(1, L + 1):
        best = INF
        for u in range(v):
            for k in range(2):
                best = min(best, opt[u] + b[k] + a[k] * max(v - u, D[k]))
        opt[v] = best
    return np.array(opt[1:])


def alg_of_schedule(purch, rho, X, ls):
    """purch: list of (u_prev, kind) in order; ALG(l) = cost of purchases with u_prev < l."""
    ups = np.array([u for u, _ in purch], dtype=float)
    cs = np.array([rho if k == 1 else X for _, k in purch], dtype=float)
    cum = np.cumsum(cs)
    idx = np.searchsorted(ups, np.asarray(ls, dtype=float), side='left')   # number of u_prev < l
    return np.where(idx > 0, cum[np.maximum(idx - 1, 0)], 0.0)


def switch_schedule(t, X, L):
    purch = [(u, 1) for u in range(t)]
    u = t
    while u < L:
        purch.append((u, 2)); u += X
    return purch, u


def tail_sup(rho2):
    """Lemma K.4 (periodic tail). If every path buys only contract 2 at coverage points >= U, then
    for L0 >= max(U, X), l = L0 + jX + s (j >= 0, 1 <= s <= X):
        E[ALG(l)] = E[ALG(L0)] + jX + X F(s),   F(s) = P(the path's first point >= L0 is < L0 + s),
    and OPT(l) = X(1-1/rho2) + l/rho2. For fixed s the ratio is a Mobius function of j, so its sup
    over j >= 0 is at j = 0 or the limit X/(X/rho2) = rho2. Hence sup over l > L0 of the ratio is
    max(rho2, the sup over l in (L0, L0 + X]), and the evaluation up to L0 + X plus rho2 is exact."""
    return float(rho2)


def eval_mixture(scheds, probs, rho, rho2, X, L_eval):
    """max over l in [1, L_eval] of E[ALG(l)]/OPT(l) (schedules extended by contract 2 forever)
    and the exact tail beyond (Lemma K.4, needs L_eval >= every switch point + 2X); returns (sup, argmax)."""
    ls = np.arange(1, L_eval + 1)
    EA = np.zeros(len(ls))
    for (purch, uend), p in zip(scheds, probs):
        if p <= 0:
            continue
        last1 = max([u for u, k in purch if k == 1], default=-1)
        assert L_eval - X >= max(last1 + 1, X)
        ext = list(purch)
        u = uend
        while u < L_eval:
            ext.append((u, 2)); u += X
        EA += p * alg_of_schedule(ext, rho, X, ls)
    r = EA / opt_closed(rho, rho2, X, ls)
    i = int(np.argmax(r))
    return max(float(r[i]), tail_sup(rho2)), int(ls[i])


# ---------------------------------------------------------------- deterministic
def det_feasible(rho, X, OPT, L, c):
    """OPT[l-1] = OPT(l). Forward DP over coverage points with minimal cumulative cost."""
    INF = float('inf')
    best = np.full(L + 1, INF)
    pred = [None] * (L + 1)
    best[0] = 0.0
    for u in range(L):
        bu = best[u]
        if bu == INF:
            continue
        lim = c * OPT[u]          # constraint at l = u + 1
        if bu + rho <= lim + 1e-12 and bu + rho < best[u + 1]:
            best[u + 1] = bu + rho; pred[u + 1] = (u, 1)
        v = min(u + X, L)
        if bu + X <= lim + 1e-12 and bu + X < best[v]:
            best[v] = bu + X; pred[v] = (u, 2)
    if best[L] == INF:
        return None
    purch, v = [], L
    while v > 0:
        u, k = pred[v]
        purch.append((u, k)); v = u
    purch.reverse()
    uend = purch[-1][0] + (1 if purch[-1][1] == 1 else X)
    return purch, uend


def det_value(rho, rho2, X, L):
    OPT = opt_closed(rho, rho2, X, np.arange(1, L + 1))
    lo, hi = 1.0, rho * rho2 + 1.0
    assert det_feasible(rho, X, OPT, L, hi) is not None
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if det_feasible(rho, X, OPT, L, mid) is None:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-10:
            break
    sch = det_feasible(rho, X, OPT, L, hi)
    ub, arg = eval_mixture([sch], [1.0], rho, rho2, X, 4 * L)
    return lo, hi, ub, sch


def det_switch(rho, rho2, X, L):
    ls = np.arange(1, L + 1)
    OPT = opt_closed(rho, rho2, X, ls)
    best, bt = float('inf'), None
    for t in range(L + 1):
        A = rho * np.minimum(t, ls) + np.where(ls > t, X * np.ceil(np.maximum(ls - t, 0) / X), 0.0)
        r = float(np.max(A / OPT))
        if r < best:
            best, bt = r, t
    return best, bt


def det_lb(rho, rho2, X, L):
    ts = np.arange(0, L)
    first = np.min((rho * ts + X) / np.minimum(rho + ts, X))
    never = rho * L / float(opt_closed(rho, rho2, X, [L])[0])
    return float(min(first, never)), float(min(first, rho * rho2))


# ---------------------------------------------------------------- randomized
def best_response(w_ls, w, rho, X, L):
    """min over all schedules of sum_l w_l ALG(l), weights w on the points w_ls (<= L)."""
    W = np.zeros(L + 2)
    np.add.at(W, np.asarray(w_ls, dtype=int), w)
    W = np.cumsum(W[::-1])[::-1]     # W[x] = sum_{l >= x} w_l
    V = np.zeros(L + 1)
    ch = np.zeros(L, dtype=int)
    for u in range(L - 1, -1, -1):
        c1 = rho * W[u + 1] + V[u + 1]
        c2 = X * W[u + 1] + V[min(u + X, L)]
        if c2 <= c1:
            V[u], ch[u] = c2, 2
        else:
            V[u], ch[u] = c1, 1
    purch, u = [], 0
    while u < L:
        purch.append((u, int(ch[u])))
        u = u + 1 if ch[u] == 1 else u + X
    return float(V[0]), (purch, u)


def solve_mix_lp(cols, OPTv):
    n = len(cols)
    A = np.hstack([np.array(cols).T, -OPTv[:, None]])
    c = np.zeros(n + 1); c[-1] = 1.0
    res = linprog(c, A_ub=A, b_ub=np.zeros(len(OPTv)), A_eq=np.hstack([np.ones(n), [0.0]])[None, :],
                  b_eq=[1.0], bounds=[(0, None)] * (n + 1), method='highs')
    assert res.status == 0, res.message
    w = np.maximum(-np.asarray(res.ineqlin.marginals), 0.0)
    # strong duality: the dual objective mu (the value of the convexity row) equals the LP value
    return float(res.fun), res.x[:n], w, float(res.fun)


def grids(rho, X, L, full):
    if full:
        return np.arange(0, L + 1), np.arange(1, L + 1)
    step = max(1, X // 256)
    tg = set(range(0, L + 1, step))
    t0 = X - int(round(rho))
    tg |= set(range(max(0, t0 - 4 * step), min(L, t0 + 4 * step) + 1))
    tg = np.array(sorted(tg))
    lg = set(int(x) for x in tg + 1 if x + 1 <= L) | set(int(x) for x in tg if x >= 1)
    lg |= set(np.unique(np.geomspace(1, L, 400).astype(int)).tolist()) | {L}
    return tg, np.array(sorted(lg))


def seqform_lp(rho, rho2, X, L, force_from=None):
    """Exact randomized value of the game with stops l in [1, L], over all algorithms. The
    algorithm learns only that the client is still active, so a mixed strategy is a behavioral
    strategy on the coverage points u = 0..L-1 (perfect recall), and its realization plan is
    y_k(u) = P(coverage reaches u and the algorithm buys contract k there). Variables y1, y2 (2L),
    S(l) = E[ALG(l)] for l = 1..L, and c:
        y1(u) + y2(u) - y1(u-1) - y2(u-X) = [u = 0],   S(l) - S(l-1) - rho y1(l-1) - X y2(l-1) = 0,
        S(l) - c OPT(l) <= 0.
    With force_from, the algorithm buys only contract 2 from coverage force_from on (a restriction,
    so its value is an upper bound on the value of the game with l <= L).
    Returns (value, y1, y2, dual weights on l)."""
    import scipy.sparse as sp
    nY = 2 * L
    iS = nY            # S(1..L) at iS + l - 1
    ic = nY + L
    nV = ic + 1
    rows, cols, vals, beq = [], [], [], []
    r = 0
    for u in range(L):
        rows += [r, r]; cols += [u, L + u]; vals += [1.0, 1.0]
        if u >= 1:
            rows.append(r); cols.append(u - 1); vals.append(-1.0)
        if u >= X:
            rows.append(r); cols.append(L + u - X); vals.append(-1.0)
        beq.append(1.0 if u == 0 else 0.0); r += 1
    for l in range(1, L + 1):
        rows.append(r); cols.append(iS + l - 1); vals.append(1.0)
        if l >= 2:
            rows.append(r); cols.append(iS + l - 2); vals.append(-1.0)
        rows += [r, r]; cols += [l - 1, L + l - 1]; vals += [-float(rho), -float(X)]
        beq.append(0.0); r += 1
    Aeq = sp.csr_matrix((vals, (rows, cols)), shape=(r, nV))
    OPTv = opt_closed(rho, rho2, X, np.arange(1, L + 1))
    ri = np.arange(L)
    Aub = sp.csr_matrix((np.concatenate([np.ones(L), -OPTv]),
                         (np.concatenate([ri, ri]), np.concatenate([iS + ri, np.full(L, ic)]))), shape=(L, nV))
    cvec = np.zeros(nV); cvec[ic] = 1.0
    bnds = [(0, None)] * nV
    if force_from is not None:
        for u in range(force_from, L):
            bnds[u] = (0, 0)
    res = linprog(cvec, A_ub=Aub, b_ub=np.zeros(L), A_eq=Aeq, b_eq=np.array(beq),
                  bounds=bnds, method='highs')
    assert res.status == 0, res.message
    w = np.maximum(-np.asarray(res.ineqlin.marginals), 0.0)
    return float(res.fun), res.x[:L], res.x[L:2 * L], w


def extend_behavioral(y1, y2, rho, rho2, X, L, L_eval):
    """E[ALG(l)] for l = 1..L_eval of the behavioral strategy of (y1, y2) on [0, L), extended by
    contract 2 forever from every coverage point >= L, and the exact tail beyond L_eval (Lemma K.4;
    the strategy must buy only contract 2 from a coverage point U <= L_eval - X on)."""
    n = L_eval + X + 1
    reach = np.zeros(n)
    reach[0] = 1.0
    buy1 = np.zeros(n)
    buy2 = np.zeros(n)
    for u in range(L_eval):
        if reach[u] <= 0:
            continue
        if u < L:
            tot = y1[u] + y2[u]
            p1 = y1[u] / tot if tot > 1e-15 else 0.0
        else:
            p1 = 0.0
        buy1[u] = reach[u] * p1
        buy2[u] = reach[u] * (1 - p1)
        reach[u + 1] += buy1[u]
        reach[u + X] += buy2[u]
    inc = rho * buy1[:L_eval] + X * buy2[:L_eval]
    EA = np.cumsum(inc)                 # EA[l-1] = sum_{u < l} = E[ALG(l)]
    ls = np.arange(1, L_eval + 1)
    ratio = EA / opt_closed(rho, rho2, X, ls)
    win = np.arange(L_eval, L_eval + X)
    mass = reach[win].sum()
    return float(np.max(ratio)), tail_sup(rho2), mass


def switch_lp(rho, rho2, X, L, full):
    """LP over distributions of the switch time t (t on a grid when not full)."""
    tg, lg = grids(rho, X, L, full)
    OPTv = opt_closed(rho, rho2, X, lg)
    scheds = [switch_schedule(int(t), X, L) for t in tg]
    cols = [alg_of_schedule(p, rho, X, lg) for p, _ in scheds]
    val, x, w, _ = solve_mix_lp(cols, OPTv)
    ub, _ = eval_mixture(scheds, x, rho, rho2, X, 4 * L)
    return val, ub, len(tg), len(lg)


def randomized(rho, rho2, X, L, full):
    """lb: rho2 (Lemma K.3) and the value of the game with l <= Lr = 10X over all algorithms
    (sequence-form LP, cross-checked by its Yao certificate); ub: the better of two explicit
    strategies evaluated at every l (Lemma K.4 for the tail): the switch-time mixture of switch_lp,
    and the sequence-form LP's strategy restricted to contract 2 from coverage 5X on. If the switch
    mixture already attains rho2, the value is rho2 and the sequence-form LPs are skipped."""
    sw_val, sw_ub, ntg, nlg = switch_lp(rho, rho2, X, L, full)
    out = dict(rnd_sw_lp=sw_val, rnd_sw_ub=sw_ub, grid_t=ntg, grid_l=nlg, full_grid=full)
    if sw_ub <= rho2 * (1 + 1e-9):
        out.update(rnd_L=None, rnd_forced=None, rnd_yao=None, rnd_lb=float(rho2), rnd_ub=sw_ub,
                   rnd_sup_eval=None, rnd_tail=float(rho2), reach_mass=1.0, seqform='skipped (switch mixture attains rho2)')
        return out
    Lr = 10 * X
    val, y1, y2, w = seqform_lp(rho, rho2, X, Lr)
    ls = np.arange(1, Lr + 1)
    OPTv = opt_closed(rho, rho2, X, ls)
    br, _ = best_response(ls, w, rho, X, Lr)
    yao = br / float(np.dot(w, OPTv))
    valF, y1F, y2F, _ = seqform_lp(rho, rho2, X, Lr, force_from=5 * X)
    # Lemma K.4 applies with U = 5X <= 4 Lr - X
    sup_eval, tail, mass = extend_behavioral(y1F, y2F, rho, rho2, X, Lr, 4 * Lr)
    ub = min(max(sup_eval, tail), sw_ub)
    # the certified lower end: the Yao value (dual weights against the exact best response) and Lemma K.3;
    # the LP's primal value agrees with the Yao value up to the solver's tolerance
    lb = max(yao, float(rho2))
    out.update(rnd_L=val, rnd_forced=valF, rnd_yao=yao, rnd_lb=lb, rnd_ub=ub, rnd_sup_eval=sup_eval,
               rnd_tail=tail, reach_mass=mass, seqform='solved')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reduced', action='store_true')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    viol = []
    # Lemma K.1: OPT's closed form against the DP
    for rho in (2, 3, 4):
        for rho2 in (2, rho, 1.5):
            for X in (4, 9, 16, 32):
                L = 3 * X
                d = opt_dp(rho, rho2, X, L)
                cf = opt_closed(rho, rho2, X, np.arange(1, L + 1))
                if np.max(np.abs(d - cf)) > 1e-9:
                    viol.append(('opt_closed', rho, rho2, X))
    rhos = (2, 4) if a.reduced else (2, 4, 8, 16)
    fs = (1, 4) if a.reduced else (1, 4, 16)
    rows = []
    for rho in rhos:
        for f in fs:
            X = f * rho * rho
            for rho2 in sorted(set((2, rho))):
                t0 = time.time()
                L = 4 * X
                dlo, dhi, dub, sch = det_value(rho, rho2, X, L)
                dsw, tsw = det_switch(rho, rho2, X, L)
                # the better of the DP's schedule and the best switch-time schedule, each at every l
                sw_all, _ = eval_mixture([switch_schedule(tsw, X, L)], [1.0], rho, rho2, X, 4 * L)
                dub = min(dub, sw_all)
                lbL, lbinf = det_lb(rho, rho2, X, L)
                R = randomized(rho, rho2, X, L, full=(L <= 2048))
                row = dict(rho=rho, rho2=rho2, X=X, X_over_rho2=f, L=L, det_lo=dlo, det_hi=dhi, det_ub=dub,
                           det_switch=dsw, det_switch_t=tsw, det_lb_L=lbL, det_lb_inf=lbinf,
                           formula=rho + 1 - rho * rho / X, sum=rho + 1, prod_det=2 * rho,
                           prod_rnd=rho * E_RATIO, secs=0.0, **R)
                row['secs'] = time.time() - t0
                if dlo < lbL - 1e-7:
                    viol.append(('det_below_lb', row))
                if dub < dhi - 1e-9 or dub > dhi + 1e-6:
                    viol.append(('det_ub', row))
                if abs(dsw - dhi) > 1e-6:
                    viol.append(('det_ne_switch', row))
                if not (R['rnd_lb'] <= R['rnd_ub'] + 1e-7 and R['rnd_ub'] <= dub + 1e-7):
                    viol.append(('rnd_order', row))
                if R['rnd_ub'] - R['rnd_lb'] > 2e-3 * R['rnd_lb']:
                    viol.append(('rnd_bracket_wide', row))
                if R['rnd_L'] is not None and abs(R['rnd_yao'] - R['rnd_L']) > 1e-4 * R['rnd_L']:
                    viol.append(('rnd_yao_ne_lp', row))
                if abs(R['reach_mass'] - 1.0) > 1e-9:
                    viol.append(('reach_mass', row))
                if R['rnd_sw_ub'] < R['rnd_lb'] - 1e-7:
                    viol.append(('switch_mixture_below_value', row))
                if abs(dhi - row['formula']) > 1e-6 and f >= 1:
                    row['formula_note'] = 'det differs from rho+1-rho^2/X'
                rows.append(row)
                print(f"rho={rho:2d} rho2={rho2:2d} X={X:5d} det={dhi:.4f} (sw {dsw:.4f}, lb {lbL:.4f}, "
                      f"formula {row['formula']:.4f}) rnd=[{R['rnd_lb']:.4f},{R['rnd_ub']:.4f}] (L-game {R['rnd_L'] if R['rnd_L'] is None else round(R['rnd_L'], 4)}) "
                      f"rnd_sw={R['rnd_sw_lp']:.4f} {row['secs']:.1f}s", flush=True)
    L_ = ['Two-contract composition game G(rho, rho2, X) under Theorem 2(a)\'s lender (more sites than slots)',
          f'checks: OPT closed form vs DP (rho<=4, X<=32), det >= lb, det = switch-time det, '
          f'rnd_lb <= rnd_ub <= det with rnd_ub/rnd_lb - 1 <= 0.002, the LP value = its Yao certificate (rel. 1e-4); violations {len(viol)}',
          ' rnd = bracket on the randomized value of the infinite game: [max(value with l <= 10X, rho2), '
          'ratio of an explicit strategy at every l]',
          ' rho rho2     X  det value  rho+1-rho^2/X  det(switch)  rnd [lb, ub]        rnd(switch mix)'
          '  rho+1  2rho  rho e/(e-1)  switch grid']
    for r in rows:
        L_.append(f" {r['rho']:3d} {r['rho2']:4d} {r['X']:5d}  {r['det_hi']:9.4f}  {r['formula']:13.4f}  "
                  f"{r['det_switch']:11.4f}  [{r['rnd_lb']:.4f}, {r['rnd_ub']:.4f}]  {r['rnd_sw_ub']:14.4f}"
                  f"  {r['sum']:5d} {r['prod_det']:5d}  {r['prod_rnd']:11.3f}  "
                  f"{'full' if r['full_grid'] else 'grid'}")
    for v in viol:
        L_.append(f' VIOLATION {v[0]} {v[1:]}')
    txt = '\n'.join(L_)
    tag = '_reduced' if a.reduced else ''
    json.dump(dict(rows=rows, violations=[str(v) for v in viol]),
              open(os.path.join(a.out, f'k2_composition{tag}.json'), 'w'), indent=1)
    open(os.path.join(a.out, f'k2_composition{tag}.txt'), 'w').write(txt + '\n')
    print(txt)
    sys.exit(1 if viol else 0)


if __name__ == '__main__':
    main()
