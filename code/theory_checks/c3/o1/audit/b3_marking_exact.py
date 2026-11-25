"""Audit b3 (O1-D): randomized marking under full feedback, EXACT expectation (all random
branches enumerated with their probabilities) against EVERY oblivious schedule on small
instances.  Semantics re-implemented from the text of o1_oblivious_lender.md Sec. 5
(not imported from fam.py).

Checks per schedule: coverage (every held lease alive until it is released), E[ALG] <= (2H_m+1) OPT,
E[N_A] <= H_m (Phi+1), and OPT >= Phi beta + aT.
Output: out/b3_marking_exact.txt
"""
import os, math
import multiprocessing as mp
from fractions import Fraction
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
INF = 10 ** 9


def first_ann(R, l, s, tau):
    # R holds per-site 'next announcement' arrays: R[l][t] = first r >= t in R_l (INF if none)
    t = s + tau
    return R[l][t] if t < len(R[l]) else INF


def nxt_arrays(Rb, T):
    out = []
    for row in Rb:
        nx = [INF] * (T + 1)
        for t in range(T - 1, -1, -1):
            nx[t] = t if row[t] else nx[t + 1]
        out.append(nx[:T])
    return out


def opt(m, T, tau, H, beta, a, q, R):
    D = tau + H
    f = [0.0] * (T + 1)
    for t in range(T - 1, -1, -1):
        b = q + f[t + 1]
        for l in range(m):
            r = first_ann(R, l, t, tau)
            d = min(r + H if r < INF else INF, T)
            for e in range(t + 1, d + 1):
                b = min(b, beta + a * max(D, e - t) + f[e])
        f[t] = b
    return f[0]


def phases(m, T, tau, H, R):
    ph, p = [], 0
    while p < T:
        marks = [first_ann(R, l, p, tau) for l in range(m)]
        pe = max(marks)
        ph.append((p, marks, pe))
        if pe >= T:
            break
        p = pe + H
    return ph


def marking_exact(m, T, tau, H, beta, a, R):
    """returns (E[cost], E[#leases], coverage_ok)."""
    D = tau + H
    ph = phases(m, T, tau, H, R)
    ok = [True]

    def lease_cost(l, s, rel):
        d = first_ann(R, l, s, tau)
        d = d + H if d < INF else INF
        if d < min(rel, T):
            ok[0] = False
        return beta + a * max(D, min(rel, T) - s)

    # distribution over (current site, purchase time) carried across phases: we only need the
    # expected cost; process phase by phase with a dict state -> prob, accumulating expected cost.
    Ecost, En = 0.0, 0.0
    state = {None: 1.0}   # (site, s) of the lease held when the phase starts
    for j, (p, marks, pe) in enumerate(ph):
        end = min(pe, T) if pe < INF else T
        nxt = (pe + H) if pe < T else T
        # close previous leases at p
        for st, pr in state.items():
            if st is not None:
                Ecost += pr * lease_cost(st[0], st[1], p)
        # new lease at uniform site
        dist = {}
        for l in range(m):
            dist[(l, p)] = dist.get((l, p), 0.0) + 1.0 / m
        En += 1.0
        Ecost += 0.0
        events = sorted(set(v for v in marks if v <= end and v < T))
        for t in events:
            newly = set(l for l in range(m) if marks[l] == t)
            unmarked = [l for l in range(m) if marks[l] > t]
            nd = {}
            for (l, s), pr in dist.items():
                if l in newly and unmarked:
                    Ecost += pr * lease_cost(l, s, t)
                    En += pr
                    for y in unmarked:
                        nd[(y, t)] = nd.get((y, t), 0.0) + pr / len(unmarked)
                else:
                    nd[(l, s)] = nd.get((l, s), 0.0) + pr
            dist = nd
        state = dist
        if nxt >= T:
            break
    for st, pr in state.items():
        Ecost += pr * lease_cost(st[0], st[1], T)
    return Ecost, En, ok[0], ph


def harm(m):
    return sum(1.0 / i for i in range(1, m + 1))


def job(args):
    m, T, tau, H, rho = args
    D = tau + H
    a = 1.0
    beta = (rho - 1) * a * D
    q = beta + a + 0.5
    slots = list(range(tau, T))
    nb = len(slots)
    Hm = harm(m)
    worst, worstR, nviol, cnt, worstN = 0.0, None, 0, 0, 0.0
    for bits in range(1 << (m * nb)):
        R = [[False] * T for _ in range(m)]
        for l in range(m):
            for i, t in enumerate(slots):
                if (bits >> (l * nb + i)) & 1:
                    R[l][t] = True
        NX = nxt_arrays(R, T)
        o = opt(m, T, tau, H, beta, a, q, NX)
        c, n, ok, ph = marking_exact(m, T, tau, H, beta, a, NX)
        Phi = sum(1 for (p, marks, pe) in ph if pe < T and pe + H <= T - 1)
        cnt += 1
        v = c / o
        if v > worst:
            worst, worstR = v, [[t for t in range(T) if R[l][t]] for l in range(m)]
        worstN = max(worstN, n / (Hm * (Phi + 1)))
        if not ok or v > 2 * Hm + 1 + 1e-9 or n > Hm * (Phi + 1) + 1e-9 or o < Phi * beta + a * T - 1e-9:
            nviol += 1
    return dict(m=m, T=T, tau=tau, H=H, rho=rho, n=cnt, viol=nviol, worst=worst, bound=2 * Hm + 1,
                worstN=worstN, worstR=worstR)


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    for rho in [4, 32]:
        jobs += [(2, 8, 1, 0, rho), (2, 8, 1, 1, rho), (2, 8, 0, 1, rho), (2, 9, 2, 1, rho),
                 (3, 6, 1, 0, rho), (3, 7, 1, 1, rho), (3, 6, 0, 2, rho)]
    with mp.Pool(int(os.environ.get('NPROC', 4))) as pool:
        res = pool.map(job, jobs)
    L = ['b3: exact E[ALG] of randomized marking (I2) over ALL schedules',
         'm T tau H rho  #omega  violations  worst E[ALG]/OPT  2H_m+1  max E[N_A]/(H_m(Phi+1))  worst schedule']
    for r in res:
        L.append(f"{r['m']} {r['T']} {r['tau']}   {r['H']} {r['rho']:<4} {r['n']:<7} {r['viol']:<11} {r['worst']:.4f}            "
                 f"{r['bound']:.3f}   {r['worstN']:.3f}                    {r['worstR']}")
    L.append(f"total schedules: {sum(r['n'] for r in res)}; total violations: {sum(r['viol'] for r in res)}")
    txt = '\n'.join(L)
    print(txt)
    open(os.path.join(OUT, 'b3_marking_exact.txt'), 'w').write(txt + '\n')


if __name__ == '__main__':
    main()
