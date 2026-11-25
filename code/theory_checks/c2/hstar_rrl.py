"""RRL special case (no protected option): exact H* vs Corollary formula
   H*_RRL = H(s0 + mu/(2(1-a))),  H(R) = R - s0 if R <= R_wait = (2-a)beta/(1-a)^2 else R.
At alpha = 0: mu/2 (mu <= 2 beta) and beta + mu/2 (mu > 2 beta), the report.md section 5B claim.
Output: out/hstar_rrl.txt"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
import itertools
import numpy as np
from multiprocessing import Pool
from model import Params
from hstar import h_ex


def formula(P):
    a, b, mu = P.alpha, P.beta, P.mu
    s0 = b / (1 - a); Rw = (2 - a) * b / (1 - a) ** 2
    R = s0 + mu / (2 * (1 - a))
    return R - s0 if R <= Rw + 1e-12 else R


def run(kw):
    P = Params(allow_p=False, **kw)
    return kw, h_ex(P), formula(P)


if __name__ == '__main__':
    jobs = [dict(alpha=al, mu=mu) for al, mu in itertools.product([0.0, 1 / 3, 0.5], [0.5, 1.0, 2.0, 3.0, 4.0, 6.0])]
    with Pool(6) as pool:
        res = pool.map(run, jobs)
    with open('out/hstar_rrl.txt', 'w') as f:
        f.write("RRL: alpha mu | H*_exact (dt=0.1, first grid H with CR <= 2-a+1e-4) | formula\n")
        for kw, he, fo in res:
            f.write(f"{kw['alpha']:.3f} {kw['mu']} | {he:.2f} | {fo:.3f}\n")
    print(open('out/hstar_rrl.txt').read())
