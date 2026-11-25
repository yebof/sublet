# Independent audit check of prop:s-tradeoff-bound (a)-(c) and prop:s-tradeoff-funded (c)-(d) on the family J (Supplement S-D.10; MS7 D8(d)-(e), design/ms7/plan.md). Exits 0; prints the violation counts.
import math, itertools
import numpy as np
from scipy.optimize import linprog

INF = None
def phi(L, u, P, q):
    if u is not None and u < L: return q*u + P
    return q*L

def rhs(L, P, q, r, rp, Af, weak=False):
    opt = q*L if weak else min(q*L, P)
    return r*q*L + rp*opt + Af

def lp_opt(P, q, T, r, rp, Af, weak=False):
    U = list(range(T)) + [None]
    c = np.array([phi(T, u, P, q) for u in U])
    A = np.array([[phi(L, u, P, q) for u in U] for L in range(1, T+1)])
    b = np.array([rhs(L, P, q, r, rp, Af, weak) for L in range(1, T+1)])
    res = linprog(c, A_ub=A, b_ub=b, A_eq=np.ones((1, len(U))), b_eq=[1.0], bounds=[(0, None)]*len(U), method='highs')
    return res.fun if res.status == 0 else math.inf

def det_opt(P, q, T, r, rp, Af, weak=False):
    best = math.inf
    for u in list(range(T)) + [None]:
        if all(phi(L, u, P, q) <= rhs(L, P, q, r, rp, Af, weak) + 1e-9 for L in range(1, T+1)):
            best = min(best, phi(T, u, P, q))
    return best

def bound_a(P, q, r, rp, Af):
    rh = r + rp
    return P + max(0.0, P - Af - rh*q)/(rh - 1)

def bound_b(P, q, r, rp, Af):
    rh = r + rp
    return rh*math.log(rh/(rh-1))*(P-q) - rh*q - Af/(rh-1)

def sstar_cost(P, q, T, r, rp, Af):
    rh = r + rp
    s = math.ceil(max(0.0, P - Af - rh*q)/((rh-1)*q) - 1e-12)
    ok = all((phi(L, s, P, q) if s < T else q*L) <= rhs(L, P, q, r, rp, Af) + 1e-9 for L in range(1, T+1))
    return s, ok, phi(T, s, P, q)

nviol = 0; ncase = 0
for (r, rp) in [(0, 1.5), (0, 2), (0, 3), (1, 1), (0.5, 0.7), (2, 0.5), (1, 2), (11.657, 1), (3, 3), (0.2, 1.0)]:
    rh = r + rp
    if rh <= 1: continue
    for q in [1.0]:
        for Pq in [1.5, 2, 3.7, 10, 25.3, 60]:
            P = Pq*q
            T = max(2, math.ceil(rh*P/((rh-1)*q) + 1e-9))
            for extra in [0, 3]:
                TT = T + extra
                for Af in [0, 0.3*P, P, 2*P]:
                    ncase += 1
                    d = det_opt(P, q, TT, r, rp, Af)
                    dw = det_opt(P, q, TT, r, rp, Af, weak=True)
                    l = lp_opt(P, q, TT, r, rp, Af)
                    lw = lp_opt(P, q, TT, r, rp, Af, weak=True)
                    ba = bound_a(P, q, r, rp, Af); bb = bound_b(P, q, r, rp, Af)
                    if not (dw >= ba - 1e-7): nviol += 1; print('A viol', r, rp, P, TT, Af, dw, ba)
                    if not (lw >= bb - 1e-7): nviol += 1; print('B viol', r, rp, P, TT, Af, lw, bb)
                    if r >= 1 and rp >= 1:
                        s, ok, cst = sstar_cost(P, q, TT, r, rp, Af)
                        if not ok or cst > ba + q + 1e-9: nviol += 1; print('C viol', r, rp, P, TT, Af, s, ok, cst, ba+q)
                        if not (d <= cst + 1e-9): nviol += 1; print('C opt viol', d, cst)
print('cases', ncase, 'violations', nviol)

# Asymptotics of (b) at rh=2 and rh=7+4sqrt2
for rh in [2.0, 7+4*math.sqrt(2)]:
    for Pq in [50, 200]:
        P = Pq; q = 1.0; T = math.ceil(rh*P/(rh-1)) + 1
        print('rh', round(rh, 3), 'P/q', Pq, 'LP/P', lp_opt(P, q, T, rh-1, 1, 0)/P, 'bound(b)/P', bound_b(P, q, rh-1, 1, 0)/P,
              'limit', rh*math.log(rh/(rh-1)), 'det/P', det_opt(P, q, T, rh-1, 1, 0)/P, 'bound(a)/P', bound_a(P, q, rh-1, 1, 0)/P)

# ------------------------------------------------------------------ guard on J, core semantics, S = FB
def lbprime_core(ns, t, btilde, rG, q):
    # one group; ns[u] requests at slot u
    s1 = q*sum(ns[:t+1]); s2 = btilde + sum(min(rG, q*n) for n in ns[:t+1])
    return min(s1, s2) if t >= 0 else 0.0

def guard_J_FB(P, q, T, L, gamma, Af, btilde, a, g=1, Bkind='lb'):
    # E_ins: buy one lease at slot 0. S = FB. T0g. B = LB' (or 0), B_f = B + Af.
    ns = [1 if u < L else 0 for u in range(T)]
    rG = g*a
    ALG = 0.0; held = False; aborted = False; ta = None
    CS = 0.0
    for t in range(T):
        CS += q*ns[t]
        B = lbprime_core(ns, t, btilde, rG, q) if Bkind == 'lb' else 0.0
        Bf = B + Af
        if not aborted:
            buys = (t == 0)
            hold_after = held or buys
            ahat = ALG + (P if buys else 0.0) + 0.0 + ns[t]*(0.0 if hold_after else q)
            if ahat <= gamma*CS + Bf + 1e-12:
                if buys: ALG += P; held = True
                ALG += ns[t]*(0.0 if held else q)
                continue
            aborted = True; ta = t
        # FB after abort: release nothing held? lease from E only if executed earlier (held); keep coverage within window
        ALG += ns[t]*(0.0 if held else q)
    return ALG, ta

nv2 = 0
for Pq in [1.2, 2, 2.5, 5, 13]:
    P = Pq; q = 1.0; T = math.ceil(2*P) + 2
    for gamma in [0.5, 1.0, 2.0]:
        for Af in [0, 0.5, P - 0.01, P]:
            for (btilde, a) in [(P/2, P/(2*T)), (0.0, P/T), (P - 1e-3, 1e-3/T)]:
                CS0 = q; B0 = lbprime_core([1], 0, btilde, a, q)
                abort_pred = P > gamma*CS0 + B0 + Af + 1e-12
                for L in range(1, T+1):
                    alg, ta = guard_J_FB(P, q, T, L, gamma, Af, btilde, a)
                    if abort_pred:
                        if not (ta == 0 and abs(alg - q*L) < 1e-9): nv2 += 1; print('funded d viol abort', P, gamma, Af, L, alg, ta)
                    else:
                        if not (ta is None and abs(alg - P) < 1e-9): nv2 += 1; print('funded d viol pass', P, gamma, Af, L, alg, ta)
                    # trade-off (d)(i): ALG <= max(1,gamma) q L + OPT + Af  (funded version)
                    opt = min(q*L, P)
                    if alg > max(1, gamma)*q*L + opt + Af + 1e-9: nv2 += 1; print('tradeoff d(i) viol', P, gamma, Af, L, alg)
                if Af == 0 and gamma <= 1:
                    alg, _ = guard_J_FB(P, q, T, T, gamma, Af, btilde, a)
                    if alg < 2*(P - q) - 1e-9: nv2 += 1; print('tradeoff d(i) lower viol', P, gamma, alg)
print('guard checks violations', nv2)

# ------------------------------------------------------------------ funded (c): one request at slot 1, lease price C <= Af
nv3 = 0
for Af in [1.0, 3.7, 10.0]:
    for C in [Af, Af/1.9, Af/2.01, 0.3]:
        if C > Af: continue
        k = math.floor(Af/C)
        ahat0 = k*C
        if ahat0 > 0*1 + 0 + Af + 1e-12: nv3 += 1; print('funded c viol pass')
        if k*C < Af/2 - 1e-12: nv3 += 1; print('funded c viol half', Af, C, k)
print('funded c violations', nv3)
