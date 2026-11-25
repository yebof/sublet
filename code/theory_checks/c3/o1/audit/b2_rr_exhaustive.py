"""Audit b2 (O1-B): RR-renew against EVERY schedule on small instances (exhaustive), which covers
every adaptive lender because RR-renew is deterministic.

Checks, per schedule omega (all subsets of announcement slots [tau, T) at every site):
  (i)   ALG <= rho (1 + D/T) OPT(omega)
  (ii)  ALG <= 2 m OPT(omega) + a D
  (iii) N_A <= m (X_min + 1), where X_min = min over ALL feasible plans of (#purchases + #fallback
        slots)  -- stronger than the proof's X for an optimal plan
  (iv)  N_A <= ceil(T / D)
Also reports the worst RR/OPT and the T4 value rho m/(m+rho-1).
Lease semantics re-implemented here (not imported from fam.py).
Output: out/b2_rr_exhaustive.txt
"""
import os, itertools, math
import multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
INF = 10 ** 9


def death(R, l, s, tau, H):
    # R is a list of per-site 'next announcement' arrays nxt[l][t] = first r >= t in R_l (INF if none)
    t = s + tau
    if t >= len(R[l]):
        return INF
    r = R[l][t]
    return r + H if r < INF else INF


def nxt_arrays(Rb, T):
    out = []
    for row in Rb:
        nx = [INF] * (T + 1)
        for t in range(T - 1, -1, -1):
            nx[t] = t if row[t] else nx[t + 1]
        out.append(nx[:T])
    return out


def opt_and_xmin(m, T, tau, H, beta, a, q, R):
    D = tau + H
    f = [0.0] * (T + 1)      # min cost to cover [t, T) with purchases at >= t
    x = [0] * (T + 1)        # min #purchases+fallback to cover [t, T)
    for t in range(T - 1, -1, -1):
        bf, bx = q + f[t + 1], 1 + x[t + 1]
        for l in range(m):
            d = min(death(R, l, t, tau, H), T)
            for e in range(t + 1, d + 1):
                bf = min(bf, beta + a * max(D, e - t) + f[e])
                bx = min(bx, 1 + x[e])
        f[t], x[t] = bf, bx
    return f[0], x[0]


def rr(m, T, tau, H, beta, a, R):
    D = tau + H
    t, site, cost, n = 0, -1, 0.0, 0
    while t < T:
        site = (site + 1) % m
        d = death(R, site, t, tau, H)
        cost += beta + a * max(D, min(d, T) - t)
        n += 1
        t = d
    return cost, n


def job(args):
    m, T, tau, H, rho = args
    D = tau + H
    a = 1.0
    beta = (rho - 1) * a * D
    q = beta + a + 0.5          # smallest fallback allowed by the family (q >= beta + a)
    slots = list(range(tau, T))
    nb = len(slots)
    worst, worst_R, viol = 0.0, None, []
    cnt = 0
    for bits in range(1 << (m * nb)):
        R = [[False] * T for _ in range(m)]
        for l in range(m):
            for i, t in enumerate(slots):
                if (bits >> (l * nb + i)) & 1:
                    R[l][t] = True
        NX = nxt_arrays(R, T)
        opt, xmin = opt_and_xmin(m, T, tau, H, beta, a, q, NX)
        c, n = rr(m, T, tau, H, beta, a, NX)
        cnt += 1
        r = c / opt
        if r > worst:
            worst, worst_R = r, [[t for t in range(T) if R[l][t]] for l in range(m)]
        if not (c <= rho * (1 + D / T) * opt + 1e-9):
            viol.append(('rho', r))
        if not (c <= 2 * m * opt + a * D + 1e-9):
            viol.append(('2m', r))
        if not (n <= m * (xmin + 1)):
            viol.append(('NA', n, xmin))
        if not (n <= math.ceil(T / D)):
            viol.append(('ceil', n))
    return dict(m=m, T=T, tau=tau, H=H, rho=rho, n=cnt, worst=worst, worst_R=worst_R,
                viol=len(viol), ex=viol[:3], T4=rho * m / (m + rho - 1))


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    for rho in [1.5, 4, 32]:
        jobs += [(2, 8, 1, 0, rho), (2, 8, 1, 1, rho), (2, 9, 2, 1, rho), (2, 8, 0, 1, rho),
                 (3, 6, 1, 0, rho), (3, 7, 1, 1, rho), (3, 6, 0, 2, rho)]
    with mp.Pool(int(os.environ.get('NPROC', 4))) as pool:
        res = pool.map(job, jobs)
    L = ['b2: RR-renew vs exact OPT over ALL schedules (covers adaptive lenders)',
         'm T tau H rho   #omega   violations  worst RR/OPT  T4 asym  worst schedule']
    for r in res:
        L.append(f"{r['m']} {r['T']} {r['tau']}   {r['H']} {r['rho']:<5} {r['n']:<8} {r['viol']:<11} {r['worst']:.4f}        "
                 f"{r['T4']:.4f}   {r['worst_R']}")
    L.append(f"total schedules: {sum(r['n'] for r in res)}; total violations: {sum(r['viol'] for r in res)}")
    txt = '\n'.join(L)
    print(txt)
    open(os.path.join(OUT, 'b2_rr_exhaustive.txt'), 'w').write(txt + '\n')


if __name__ == '__main__':
    main()
