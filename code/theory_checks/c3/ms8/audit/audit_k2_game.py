"""Independent audit check (unit R3) of the two-contract composition game of
design/theory/core_additive.md §5 (Lemmas K.1-K.5 and the value table). Written without reading the
builder's check_k2_composition.py beyond its docstring; nothing is imported from it.

Game G(rho, rho2, X): one client active on [0, l), stop l chosen by an oblivious adversary.
Contract 1: window 1, cost rho (exposure rho). Contract 2: window X, cost X, rent 1/rho2 (exposure rho2).
Every lease of the algorithm dies at age D_k (Theorem 2(a)'s rule), so a deterministic algorithm is a
sequence of purchases at its coverage points; ALG(l) = cost of the purchases at coverage points < l.

What this script computes, per grid point rho in {2,4,8,16}, X/rho^2 in {1,4,16}, rho2 in {2, rho}:
  K1  OPT(l) closed form of Lemma K.1(b) against an independent DP over held leases (no announcements),
      in exact rational arithmetic, for small X; and the per-site-coupling claim of K.1(a) (every lease
      of the algorithm dies at age D_k under the rule, also with overlapping leases at one site), by
      simulation of random purchase sequences.
  DET the deterministic value in EXACT rational arithmetic: the DP over coverage points (minimal cost per
      coverage point dominates) is infeasible at r = V - 1e-12 for stops l <= 4X (a lower bound on the
      infinite game), and the switch schedule t = X - rho (or the best switch time if that one fails)
      has sup_l ALG/OPT <= V over ALL l (exact evaluation for l <= t + 2X; for l = t + jX + s, j >= 1,
      the ratio is a Mobius function of j, so its sup is max(value at j = 1, rho2)).
      V = rho + 1 - rho^2/X.
  RND the randomized value as a bracket, by my own LP (realization-plan flow on coverage points with
      cumulative cost variables, scipy HiGHS):
        lb = max(rho2, Yao certificate): the duals q_l of the unrestricted LP with l <= L_lb, evaluated
             against the exact best response over all deterministic schedules (shortest-path DP);
        ub = max(rho2, value of the LP restricted to contract 2 from coverage U on, with l <= U + X),
             which is the exact sup over all l of that strategy by the periodic tail (Lemma K.4);
             the strategy is also re-evaluated directly up to U + 4X as a check of the tail.
Compares with the note's table (design/theory/core_additive.md §5). Exit 1 on any violation.
Output: out/audit_k2_game.json, out/audit_k2_game.txt. Usage: audit_k2_game.py [--reduced]
"""
import os
import sys
import json
import time
import math
import argparse
import random
from fractions import Fraction as Fr

import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

# the note's table (§5), for comparison: (rho, rho2, X) -> (det, rnd_lb, rnd_ub)
NOTE = {
    (2, 2, 4): (2.0, 2.0, 2.0), (2, 2, 16): (2.75, 2.0163, 2.0164), (2, 2, 64): (2.9375, 2.1696, 2.1696),
    (4, 2, 16): (4.0, 2.3366, 2.3366), (4, 4, 16): (4.0, 4.0, 4.0), (4, 2, 64): (4.75, 3.4134, 3.4134),
    (4, 4, 64): (4.75, 4.0, 4.0), (4, 2, 256): (4.9375, 3.8630, 3.8630), (4, 4, 256): (4.9375, 4.0, 4.0),
    (8, 2, 64): (8.0, 4.2684, 4.2684), (8, 8, 64): (8.0, 8.0, 8.0), (8, 2, 256): (8.75, 6.5657, 6.5657),
    (8, 8, 256): (8.75, 8.0, 8.0), (8, 2, 1024): (8.9375, 7.5866, 7.5866), (8, 8, 1024): (8.9375, 8.0, 8.0),
    (16, 2, 256): (16.0, 8.2581, 8.2581), (16, 16, 256): (16.0, 16.0, 16.0),
    (16, 2, 1024): (16.75, 12.9620, 12.9620), (16, 16, 1024): (16.75, 16.0, 16.0),
    (16, 2, 4096): (16.9375, 15.1141, 15.1144), (16, 16, 4096): (16.9375, 16.0, 16.0),
}


# ------------------------------------------------------------------ OPT
def opt_exact(rho, rho2, X, l):
    rho, rho2, X, l = Fr(rho), Fr(rho2), Fr(X), Fr(l)
    return min(rho - 1 + l, X * (1 - 1 / rho2) + max(l, X) / rho2)


def opt_float(rho, rho2, X, ls):
    ls = np.asarray(ls, dtype=float)
    return np.minimum(rho - 1 + ls, X * (1 - 1 / rho2) + np.maximum(ls, X) / rho2)


def opt_bruteforce(rho, rho2, X, L, q=None):
    """Exact DP: cheapest cover of [0, l) by leases held as long as wanted (no announcements; the
    optimum sits at a silent site), each lease paying loading + rent * max(D_k, held), plus fallback
    slots at q >= rho. Leases may be held past l (prepaid window). Returns [OPT(1..L)]."""
    q = Fr(rho) if q is None else Fr(q)
    load = [Fr(rho) - 1, Fr(X) * (1 - Fr(1, rho2))]
    rent = [Fr(1), Fr(1, rho2)]
    D = [1, X]
    best = [Fr(0)] + [None] * L        # best[v]: min cost to cover [0, v) exactly with pieces
    for v in range(1, L + 1):
        cands = [best[v - 1] + q]
        for u in range(v):
            for k in range(2):
                cands.append(best[u] + load[k] + rent[k] * max(v - u, D[k]))
        best[v] = min(cands)
    # OPT(l) = min over v >= l of covering [0, v)? No: covering [0, l) exactly suffices, since a lease
    # held for fewer than D_k slots still pays D_k (max), which the formula charges.
    return best[1:]


def check_K1_sim(rng, n_runs=400):
    """K.1(a): under 'announce at the site when a lease of the algorithm there reaches age tau_k'
    with per-site coupling, every lease of the algorithm dies exactly at age D_k (never earlier, as
    S-B.1's first fact says, never later). Random overlapping purchases at 2 sites, 2 contracts."""
    viol = 0
    for _ in range(n_runs):
        X = rng.randint(2, 6)
        tau = [1, rng.randint(1, X)]          # contract 2: tau_2 in [1, X], H_2 = X - tau_2
        H = [0, X - tau[1]]
        T = 40
        buys = sorted((rng.randrange(T - 8), rng.randrange(2), rng.randrange(2)) for _ in range(rng.randint(1, 10)))
        # simulate slot by slot: announcements R_l are added when a lease reaches age tau_k
        R = {0: set(), 1: set()}
        leases = [dict(s=s, site=site, k=k, death=None) for (s, site, k) in buys]
        for t in range(T + 2 * X + 2):
            for L in leases:
                if L['s'] + tau[L['k']] == t:
                    R[L['site']].add(t)
            for L in leases:
                if L['death'] is None:
                    elig = [r for r in R[L['site']] if r >= L['s'] + tau[L['k']] and r <= t]
                    if elig:
                        L['death'] = min(elig) + H[L['k']]
        for L in leases:
            D = tau[L['k']] + H[L['k']]
            if L['death'] != L['s'] + D:
                viol += 1
    return viol


# ------------------------------------------------------------------ deterministic, exact
def det_feasible_exact(rho, rho2, X, L, r):
    """Is there a schedule with ALG(l) <= r OPT(l) for all l <= L? Exact Fractions."""
    best = [None] * (L + 1)
    best[0] = 0
    for u in range(L):
        bu = best[u]
        if bu is None:
            continue
        lim = r * opt_exact(rho, rho2, X, u + 1)
        for c, w in ((rho, 1), (X, X)):
            if bu + c <= lim:
                v = min(u + w, L)
                if best[v] is None or bu + c < best[v]:
                    best[v] = bu + c
    return best[L] is not None


def switch_sup_exact(rho, rho2, X, t):
    """sup over all l of ALG/OPT for 'contract 1 at coverage 0..t-1, then contract 2 forever'."""
    best = Fr(0)
    argl = None
    for l in range(1, t + 2 * X + 1):
        if l <= t:
            alg = rho * l
        else:
            j = (l - t - 1) // X          # contract-2 purchases at t, t+X, ..., t+jX are < l
            alg = rho * t + (j + 1) * X
        r = Fr(alg) / opt_exact(rho, rho2, X, l)
        if r > best:
            best, argl = r, l
    return max(best, Fr(rho2)), argl


def det_value(rho, rho2, X):
    V = Fr(rho) + 1 - Fr(rho * rho, X)
    L = 4 * X
    lb_ok = not det_feasible_exact(rho, rho2, X, L, V - Fr(1, 10 ** 12))
    t0 = X - rho
    sup0, _ = switch_sup_exact(rho, rho2, X, t0)
    best_t, best_sup = t0, sup0
    if sup0 > V:
        for t in range(0, 2 * X + 1):
            s, _ = switch_sup_exact(rho, rho2, X, t)
            if s < best_sup:
                best_t, best_sup = t, s
    return dict(V=float(V), V_exact=str(V), lb_infeasible_below_V=lb_ok, switch_t=best_t,
                switch_sup=float(best_sup), switch_sup_exact=str(best_sup), ub_le_V=best_sup <= V,
                det_equals_V=lb_ok and best_sup <= V)


# ------------------------------------------------------------------ randomized, LP
def build_lp(rho, rho2, X, L, U=None):
    """Variables: u_v, w_v (v < L): probability of buying contract 1 / 2 at coverage point v;
    A_l (l = 1..L): E[ALG(l)]; r. Flow: u_v + w_v = [v=0] + u_{v-1} + w_{v-X}. If U is given,
    u_v = 0 for v >= U (contract 2 only from coverage U on)."""
    nu, nw, nA = L, L, L
    iu = lambda v: v
    iw = lambda v: L + v
    iA = lambda l: 2 * L + l - 1
    ir = 3 * L
    nvar = 3 * L + 1
    rows, cols, vals, beq = [], [], [], []
    rr = 0
    for v in range(L):
        rows += [rr, rr]; cols += [iu(v), iw(v)]; vals += [1.0, 1.0]
        if v >= 1:
            rows.append(rr); cols.append(iu(v - 1)); vals.append(-1.0)
        if v >= X:
            rows.append(rr); cols.append(iw(v - X)); vals.append(-1.0)
        beq.append(1.0 if v == 0 else 0.0)
        rr += 1
    for l in range(1, L + 1):
        rows += [rr, rr, rr]; cols += [iA(l), iu(l - 1), iw(l - 1)]; vals += [1.0, -float(rho), -float(X)]
        if l >= 2:
            rows.append(rr); cols.append(iA(l - 1)); vals.append(-1.0)
        beq.append(0.0)
        rr += 1
    Aeq = sp.csr_matrix((vals, (rows, cols)), shape=(rr, nvar))
    OPT = opt_float(rho, rho2, X, np.arange(1, L + 1))
    rows, cols, vals = [], [], []
    for l in range(1, L + 1):
        rows += [l - 1, l - 1]; cols += [iA(l), ir]; vals += [1.0, -float(OPT[l - 1])]
    Aub = sp.csr_matrix((vals, (rows, cols)), shape=(L, nvar))
    bub = np.zeros(L)
    c = np.zeros(nvar); c[ir] = 1.0
    bounds = [(0, None)] * nvar
    if U is not None:
        for v in range(U, L):
            bounds[iu(v)] = (0, 0)
    return c, Aub, bub, Aeq, np.array(beq), bounds, OPT, (iu, iw, ir)


def solve_lp(rho, rho2, X, L, U=None):
    c, Aub, bub, Aeq, beq, bounds, OPT, idx = build_lp(rho, rho2, X, L, U)
    res = linprog(c, A_ub=Aub, b_ub=bub, A_eq=Aeq, b_eq=beq, bounds=bounds, method='highs',
                  options=dict(primal_feasibility_tolerance=1e-10, dual_feasibility_tolerance=1e-10))
    if res.status != 0:
        raise RuntimeError(res.message)
    return res, OPT, idx


def yao_bound(rho, X, q, OPT, L):
    """min over deterministic schedules of sum_l q_l ALG(l), divided by sum_l q_l OPT(l)."""
    Q = np.concatenate([np.cumsum(q[::-1])[::-1], [0.0]])     # Q[v] = sum_{l > v} q_l (l = v+1..L)
    dist = np.full(L + 1, np.inf)
    dist[0] = 0.0
    for v in range(L):
        d = dist[v]
        if not np.isfinite(d):
            continue
        w = Q[v]                                     # weight of a purchase at coverage v
        if d + rho * w < dist[v + 1]:
            dist[v + 1] = d + rho * w
        t = min(v + X, L)
        if d + X * w < dist[t]:
            dist[t] = d + X * w
    return dist[L] / float(np.dot(q, OPT))


def eval_strategy(rho, rho2, X, u, w, U, Lev):
    """E[ALG(l)] / OPT(l) for l <= Lev of the flow (u, w) defined on v < len(u), extended with
    contract 2 only from coverage U on (the restricted LP's strategy). Returns the max ratio."""
    L = len(u)
    y = np.zeros(Lev + X + 1)
    uu = np.zeros(Lev + 1); ww = np.zeros(Lev + 1)
    y[0] = 1.0
    for v in range(Lev):
        if v < L:
            uu[v], ww[v] = u[v], w[v]
        else:
            uu[v], ww[v] = 0.0, y[v]
        if v + 1 <= Lev:
            y[v + 1] += uu[v]
        if v + X <= Lev + X:
            y[v + X] += ww[v]
    EA = np.cumsum(rho * uu[:Lev] + X * ww[:Lev])        # EA[l-1] = E[ALG(l)]
    r = EA / opt_float(rho, rho2, X, np.arange(1, Lev + 1))
    return float(r.max())


def rnd_bracket(rho, rho2, X, L_lb, U):
    t0 = time.time()
    out = {}
    # upper end: restricted LP, exact by the periodic tail
    res, OPT, (iu, iw, ir) = solve_lp(rho, rho2, X, U + X, U=U)
    x = res.x
    Lr = U + X
    u = x[:Lr]; w = x[Lr:2 * Lr]
    out['ub_lp'] = float(res.fun)
    out['ub'] = max(float(res.fun), float(rho2))
    out['ub_direct_U+4X'] = max(eval_strategy(rho, rho2, X, u, w, U, U + 4 * X), float(rho2))
    if out['ub'] <= rho2 + 1e-9:
        out['lb'] = float(rho2); out['yao'] = None; out['lb_lp'] = None
    else:
        res2, OPT2, _ = solve_lp(rho, rho2, X, L_lb)
        q = -np.asarray(res2.ineqlin.marginals)
        q = np.maximum(q, 0.0)
        yao = yao_bound(rho, X, q, OPT2, L_lb)
        out['lb_lp'] = float(res2.fun)
        out['yao'] = float(yao)
        out['lb'] = max(float(yao), float(rho2))
    out['secs'] = round(time.time() - t0, 1)
    return out


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reduced', action='store_true')
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random(20261124)
    viol = []
    rec = dict(K1={}, grid=[])

    # K1: closed form vs brute force (exact), and the death-at-D_k simulation
    k1_bad = 0
    k1_n = 0
    for rho in (2, 3, 4):
        for rho2 in (Fr(3, 2), 2, rho):
            for X in (2, 3, 5, 8, 12):
                L = 3 * X + 3
                bf = opt_bruteforce(rho, rho2, X, L)
                for l in range(1, L + 1):
                    k1_n += 1
                    if bf[l - 1] != opt_exact(rho, rho2, X, l):
                        k1_bad += 1
                        viol.append(('K1_closed_form', rho, str(rho2), X, l))
    sim_bad = check_K1_sim(rng, 100 if args.reduced else 1000)
    if sim_bad:
        viol.append(('K1_death_age', sim_bad))
    rec['K1'] = dict(closed_form_points=k1_n, closed_form_mismatch=k1_bad, death_sim_violations=sim_bad)

    grid = []
    for rho in (2, 4, 8, 16):
        for f in (1, 4, 16):
            X = f * rho * rho
            for rho2 in sorted({2, rho}):
                grid.append((rho, rho2, X))
    if args.reduced:
        grid = [g for g in grid if g[2] <= 64][:4]

    lines = []
    for (rho, rho2, X) in grid:
        t0 = time.time()
        det = det_value(rho, rho2, X)
        if not det['lb_infeasible_below_V']:
            viol.append(('K2_lower', rho, rho2, X))
        if X >= 2 * rho * rho and 1 + 1 / rho <= rho2 <= rho and not det['ub_le_V']:
            viol.append(('K5_upper', rho, rho2, X))
        # randomized bracket; restriction point U and the lower LP's stops L_lb by X
        if X <= 256:
            L_lb, U = 16 * X, 12 * X
        elif X <= 1024:
            L_lb, U = 8 * X, 6 * X
        else:
            L_lb, U = 5 * X, 4 * X
        rnd = rnd_bracket(rho, rho2, X, L_lb, U)
        if rnd['lb'] > rnd['ub'] * (1 + 1e-7):
            viol.append(('rnd_bracket_inverted', rho, rho2, X, rnd))
        if rnd['ub'] > det['switch_sup'] * (1 + 1e-9):
            viol.append(('rnd_above_det', rho, rho2, X))
        if abs(rnd['ub_direct_U+4X'] - rnd['ub']) > 1e-6 * rnd['ub']:
            viol.append(('tail_mismatch', rho, rho2, X, rnd['ub'], rnd['ub_direct_U+4X']))
        note = NOTE.get((rho, rho2, X))
        cmp = None
        if note:
            nd, nl, nu = note
            # the note rounds to 4 decimals; brackets must overlap within the rounding
            overlap = (rnd['lb'] <= nu + 6e-5) and (nl - 6e-5 <= rnd['ub'])
            det_match = abs(det['V'] - nd) < 1e-4 and det['det_equals_V']
            cmp = dict(det_match=det_match, rnd_overlap=overlap)
            if not det_match:
                viol.append(('note_det_mismatch', rho, rho2, X))
            if not overlap:
                viol.append(('note_rnd_mismatch', rho, rho2, X, rnd['lb'], rnd['ub'], note))
        row = dict(rho=rho, rho2=rho2, X=X, det=det, rnd=rnd, note=note, cmp=cmp,
                   secs=round(time.time() - t0, 1))
        rec['grid'].append(row)
        lines.append(f"{rho:4d} {rho2:4d} {X:5d}  det={det['switch_sup']:.6f} (V={det['V']:.6f}, exact "
                     f"lb ok={det['lb_infeasible_below_V']}, switch t={det['switch_t']})  rnd=[{rnd['lb']:.6f}, "
                     f"{rnd['ub']:.6f}] direct={rnd['ub_direct_U+4X']:.6f}  note={note}  {row['secs']}s")
        print(lines[-1], flush=True)

    rec['violations'] = [list(map(str, v)) for v in viol]
    with open(os.path.join(OUT, 'audit_k2_game' + ('_reduced' if args.reduced else '') + '.json'), 'w') as fh:
        json.dump(rec, fh, indent=1, default=str)
    with open(os.path.join(OUT, 'audit_k2_game' + ('_reduced' if args.reduced else '') + '.txt'), 'w') as fh:
        fh.write('Audit R3: two-contract composition game, independent values (core_additive.md §5)\n')
        fh.write(f"K.1 closed form vs exact DP: {k1_n} points, {k1_bad} mismatches; death-at-D_k simulation "
                 f"violations {sim_bad}\n")
        fh.write('rho rho2 X  deterministic (exact) | randomized bracket [lb, ub] | ub re-evaluated to U+4X | note\n')
        fh.write('\n'.join(lines) + '\n')
        fh.write(f'violations {len(viol)}\n')
        for v in viol:
            fh.write(f'  {v}\n')
    print(f'violations {len(viol)}')
    sys.exit(1 if viol else 0)


if __name__ == '__main__':
    main()
