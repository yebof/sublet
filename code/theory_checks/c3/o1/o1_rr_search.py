"""Adversarial local search over oblivious schedules for RR-renew (Theorem O1-B tightness).
Question: is the worst RR-renew/OPT ratio the cat-and-mouse value of Theorem 4?  Each run starts
from a random Bernoulli schedule (or the cat-and-mouse schedule) and flips announcement bits
while the ratio does not decrease (2000 proposals).  Output: out/o1_rr_search.txt/json
"""
import os, sys, json
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
import multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fam import Fam, opt_dp, run_renew, rr_choose
from o1_ub import adaptive_rr

OUT = os.path.join(HERE, 'out')


def ratio(F, B):
    om = [np.nonzero(B[l])[0].astype(int) for l in range(F.m)]
    return run_renew(F, om, rr_choose(F.m))[0] / opt_dp(F, om)[0]


def job(args):
    m, rho, tau, H, T, seed = args
    F = Fam(m, rho, tau, H, T)
    rng = np.random.default_rng(seed)
    adv = adaptive_rr(F)
    Badv = np.zeros((m, T), dtype=bool)
    for l in range(m):
        Badv[l, adv[l][adv[l] < T]] = True
    r_adv = ratio(F, Badv)
    best = r_adv
    for start in range(6):
        B = Badv.copy() if start == 0 else (rng.random((m, T)) < rng.choice([0.05, 0.2, 0.5]))
        cur = ratio(F, B)
        for _ in range(2000):
            l, t = int(rng.integers(m)), int(rng.integers(T))
            B[l, t] ^= True
            v = ratio(F, B)
            if v >= cur:
                cur = v
            else:
                B[l, t] ^= True
        best = max(best, cur)
    return dict(m=m, rho=rho, tau=tau, H=H, T=T, seed=seed, adaptive=r_adv, search_max=best,
                T4_asym=rho * m / (m + rho - 1))


def main():
    jobs = [(m, rho, tau, H, 24, s) for m in [2, 3, 4] for rho in [4, 16] for (tau, H) in [(1, 0), (2, 1)] for s in range(2)]
    with mp.Pool(5) as pool:
        res = pool.map(job, jobs)
    with open(os.path.join(OUT, 'o1_rr_search.json'), 'w') as f:
        json.dump(res, f, indent=1)
    L = ['RR-renew, adversarial local search over oblivious schedules (T=24)',
         'm rho tau H seed  RR@cat-and-mouse  search max  T4 asym rho m/(m+rho-1)']
    for r in res:
        L.append(f"{r['m']} {r['rho']:<3} {r['tau']}   {r['H']} {r['seed']}     {r['adaptive']:.4f}            "
                 f"{r['search_max']:.4f}      {r['T4_asym']:.4f}")
    txt = '\n'.join(L)
    print(txt)
    open(os.path.join(OUT, 'o1_rr_search.txt'), 'w').write(txt + '\n')


if __name__ == '__main__':
    main()
