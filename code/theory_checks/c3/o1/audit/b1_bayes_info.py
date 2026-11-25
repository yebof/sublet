"""Audit b1 (O1-A): independent exact Bayes-optimal algorithm on the safe-site distribution,
under three readings of the observation model:

  I1n  own-lease feedback, narrow: a lease reports only its own announcement time r
       (the slot at which it is first announced after its commitment); nothing afterwards.
  I1b  own-lease feedback, literal reading of o1_oblivious_lender.md Sec. 1: at every slot t the
       algorithm observes t in R_l for every lease it holds at l whose commitment has ended,
       *including leases already in their notice period [r, r+H)*.
  I2   full feedback: every site's bit t in R_l.

Written independently of o1/pomdp.py (shared only: the lease semantics of fam.py).
Within a slot the order is: observe announcements at t, then decide (buy / keep / fallback).
With tau >= 1 this order is immaterial for leases bought at t.

Checks: Theorem O1-A says min_det E[ALG] >= Phi*beta*g(k,m) + a*T for the safe-site
distribution.  The bound is proved for I1n; question: does it survive I1b when H >= 2?
No cap on the number of live leases unless stated (a cap only *raises* the min, so a capped
value below the bound is still a valid counterexample, while a capped value above it is not a
valid verification).
The 'ok' column compares with the O1-A bound, which is an I1 statement; for I2 it is expected to be
False (with full feedback the safe site is visible at each phase start and the optimum is Phi*beta+aT).
Output: out/b1_bayes_info.txt
"""
import os, sys, itertools, math, time
import numpy as np
import multiprocessing as mp
sys.setrecursionlimit(100000)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')


def g_fn(k, m):
    return sum(max(0.0, 1.0 - (j - 1) / (m - 1)) for j in range(1, k))


def safe_site_all(m, k, D, Phi):
    """all safe-site sequences (uniform), as boolean arrays R[l][t]."""
    P, T = k * D, k * D * Phi
    seqs = []

    def rec(S):
        if len(S) == Phi:
            seqs.append(list(S)); return
        for l in range(m):
            if not S or l != S[-1]:
                rec(S + [l])
    rec([])
    oms = []
    for S in seqs:
        R = np.ones((m, T), dtype=bool)
        for i, si in enumerate(S):
            R[si, i * P:(i + 1) * P] = False
        oms.append(R)
    return oms, seqs


def bayes(m, tau, H, T, beta, a, q, oms, info, cap=None):
    D = tau + H
    cap = cap if cap is not None else 10 ** 9
    W = len(oms)
    memo = {}
    site_subsets = [c for r in range(m + 1) for c in itertools.combinations(range(m), r)]

    def canon(leases):
        # announced leases: under I1n / I2 the site no longer matters (no more observations,
        # and the announcement already happened); keep (death, prepaid_end).
        out = []
        for (l, s, r) in leases:
            if r >= 0 and info != 'I1b':
                out.append((-1, s, r))
            else:
                out.append((l, s, r))
        return tuple(sorted(out))

    def V(t, leases, bel):
        if t >= T:
            return 0.0
        key = (t, leases, bel)
        if key in memo:
            return memo[key]
        parts = {}
        for w in bel:
            R = oms[w]
            if info == 'I1n':
                obs = tuple(bool(R[l, t]) if (r < 0 and t >= s + tau) else None for (l, s, r) in leases)
            elif info == 'I1b':
                obs = tuple(bool(R[l, t]) if (l >= 0 and t >= s + tau and (r < 0 or r + H > t)) else None for (l, s, r) in leases)
            else:
                obs = tuple(bool(R[l, t]) for l in range(m))
            parts.setdefault(obs, []).append(w)
        tot = 0.0
        for obs, ws in parts.items():
            R0 = oms[ws[0]]
            live = []
            for (l, s, r) in leases:
                if r < 0 and t >= s + tau and R0[l, t]:
                    r = t
                if r >= 0 and r + H <= t:
                    continue
                live.append((l, s, r))
            fixed = [x for x in live if t - x[1] < D]
            aged = [x for x in live if t - x[1] >= D]
            best = math.inf
            for kr in range(len(aged) + 1):
                for keep in itertools.combinations(aged, kr):
                    for buy in site_subsets:
                        n_live = len(fixed) + kr + len(buy)
                        if n_live > cap:
                            continue
                        c = len(buy) * (beta + a * D) + a * kr + (q if n_live == 0 else 0.0)
                        if c >= best:
                            continue
                        nl = canon(fixed + list(keep) + [(l, t, -1) for l in buy])
                        v = c + V(t + 1, nl, tuple(ws))
                        if v < best:
                            best = v
            tot += len(ws) * best
        memo[key] = tot / len(bel)
        return memo[key]

    v = V(0, tuple(), tuple(range(W)))
    return v, len(memo)


def job(args):
    m, rho, tau, H, k, Phi, info, cap = args
    D = tau + H
    a = 1.0
    beta = (rho - 1) * a * D
    q = beta + a * D + 1.0
    oms, _ = safe_site_all(m, k, D, Phi)
    T = k * D * Phi
    t0 = time.time()
    v, ns = bayes(m, tau, H, T, beta, a, q, oms, info, cap)
    lb = Phi * beta * g_fn(k, m) + a * T
    optb = Phi * beta + a * T
    return dict(m=m, rho=rho, tau=tau, H=H, k=k, Phi=Phi, T=T, info=info, cap=cap, val=v, lb=lb,
                ok=v >= lb - 1e-9, ratio=v / optb, formula=((rho - 1) * g_fn(k, m) + k) / (rho - 1 + k),
                states=ns, sec=time.time() - t0)


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    # non-trivial g needs k >= 3; notice-period leakage needs H >= 2
    for info in ['I1n', 'I1b', 'I2']:
        jobs += [(3, 32, 1, 2, 3, 2, info, None),
                 (3, 32, 1, 3, 3, 2, info, None),
                 (4, 32, 1, 2, 3, 2, info, None),
                 (3, 32, 2, 2, 3, 2, info, None)]
    res = []
    with mp.Pool(int(os.environ.get('NPROC', 4))) as pool:
        for r in pool.imap_unordered(job, jobs):
            print('done', r['m'], r['tau'], r['H'], r['info'], round(r['val'], 3), round(r['lb'], 3), round(r['sec']), flush=True)
            res.append(r)
    res.sort(key=lambda r: (r['m'], r['tau'], r['H'], ['I1n', 'I1b', 'I2'].index(r['info'])))
    L = ['b1: exact Bayes-optimal E[ALG] on the safe-site distribution vs O1-A bound Phi*beta*g + aT',
         'm rho tau H k Phi T   info cap   E[ALG*]    bound      ok     E[ALG*]/(Phi beta+aT)  formula  states  sec']
    for r in res:
        L.append(f"{r['m']} {r['rho']:<3} {r['tau']}   {r['H']} {r['k']} {r['Phi']}   {r['T']:<3} {r['info']:<4} {str(r['cap']):<5} "
                 f"{r['val']:9.3f}  {r['lb']:9.3f}  {str(r['ok']):<5}  {r['ratio']:.4f}                 {r['formula']:.4f}   {r['states']:<7} {r['sec']:.0f}")
    txt = '\n'.join(L)
    print(txt)
    open(os.path.join(OUT, 'b1_bayes_info.txt'), 'w').write(txt + '\n')


if __name__ == '__main__':
    main()
