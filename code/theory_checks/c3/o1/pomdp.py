"""Exact best response (Bayes-optimal deterministic algorithm) to a finite, uniformly
weighted set of schedules Omega, under own-lease feedback (I1) or full feedback (I2).

The algorithm may hold any number of leases (up to `cap` live leases), buy several per slot,
release leases past their prepaid window, and fall back.  Information:
  I1: at slot t it observes, for each lease it holds whose commitment has ended, whether that
      lease is announced at t;
  I2: it observes every site's announcement bit at t.
By Yao's principle, min over deterministic algorithms of E_omega[ALG] is a valid comparison
for every randomized algorithm.  Used to check Theorem O1-A numerically.
"""
import itertools
import numpy as np


def best_response(F, omegas, info='I1', cap=None):
    T, m, tau, H, D = F.T, F.m, F.tau, F.H, F.D
    beta, a, q = F.beta, F.a, F.q
    cap = cap or 10 ** 9
    R = [[set(map(int, om[l])) for l in range(m)] for om in omegas]
    memo = {}
    subsets = [s for r in range(m + 1) for s in itertools.combinations(range(m), r)]

    def V(t, leases, Om):
        if t >= T:
            return 0.0
        key = (t, leases, Om)
        if key in memo:
            return memo[key]
        # observation at t
        parts = {}
        for w in Om:
            if info == 'I1':
                obs = tuple(1 if (r < 0 and t >= s + tau and t in R[w][l]) else 0
                            for (l, s, r) in leases)
            else:
                obs = tuple(1 if t in R[w][l] else 0 for l in range(m))
            parts.setdefault(obs, []).append(w)
        tot = 0.0
        for obs, ws in parts.items():
            live = []
            for i, (l, s, r) in enumerate(leases):
                if r < 0 and t >= s + tau and t in R[ws[0]][l]:
                    r = t
                if r >= 0 and r + H <= t:
                    continue
                live.append((l, s, r))
            fixed = [x for x in live if t - x[1] < D]        # prepaid: always keep
            aged = [x for x in live if t - x[1] >= D]
            best = np.inf
            for kr in range(len(aged) + 1):
                for keep in itertools.combinations(aged, kr):
                    for buy in subsets:
                        n_live = len(fixed) + kr + len(buy)
                        if n_live > cap:
                            continue
                        c = len(buy) * (beta + a * D) + a * kr
                        if n_live == 0:
                            c += q
                        nl = tuple(sorted(fixed + list(keep) + [(l, t, -1) for l in buy]))
                        v = c + V(t + 1, nl, tuple(ws))
                        if v < best:
                            best = v
            tot += len(ws) * best
        memo[key] = tot / len(Om)
        return memo[key]

    val = V(0, tuple(), tuple(range(len(omegas))))
    return val, len(memo)
