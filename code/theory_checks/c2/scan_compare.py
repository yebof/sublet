"""Broad scan: exact deterministic game (det_game.solve_det, dt=0.1) vs the family lower bound
(families.lb_total) and vs the class decomposition CR* = min(CR_ins, CR_react).
Output: out/scan_compare.csv"""
import os, sys, itertools
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
from multiprocessing import Pool
from model import Params
from det_game import solve_det
from families import cr_ins

DT, T, RMAX = 0.1, 14.0, 7.0

def run(kw):
    P = Params(**kw)
    r = solve_det(P, dt=DT, T=T, Rmax=RMAX, return_detail=True)
    return dict(kw, CR=r['CR'], plan=str(r['plan']).replace(',', ';'), CRins_cls=r['CR_ins_class'],
                CRreact_cls=r['CR_react_class'], CRins_formula=cr_ins(P))

if __name__ == '__main__':
    jobs = []
    combos = [(0.0, 0.5), (0.2, 0.4), (0.2, 0.6), (0.2, 0.8), (0.3, 0.4), (0.3, 0.6), (0.3, 0.8), (0.5, 0.6), (0.5, 0.8)]
    for (al, ap), mu, lam, H, tau in itertools.product(combos, [0.5, 1, 2, 4], [0, 0.5, 1], [0, 0.5, 1, 2, 3], [0, 1]):
        jobs.append(dict(alpha=al, ap=ap, mu=float(mu), lam=lam, H=float(H), tau=float(tau)))
    for al, mu, H in itertools.product([0.0, 0.3], [0.5, 1, 2, 4], [0, 0.5, 1, 2, 3]):
        jobs.append(dict(alpha=al, ap=1.0, mu=float(mu), lam=0.0, H=float(H), tau=0.0, allow_p=False))
    with Pool(6) as pool:
        res = pool.map(run, jobs, chunksize=4)
    keys = list(res[0].keys())
    keys = keys + [k for k in res[-1].keys() if k not in keys]
    with open('out/scan_compare.csv', 'w') as f:
        f.write(','.join(keys) + '\n')
        for r in res:
            f.write(','.join(str(r.get(k, '')) for k in keys) + '\n')
    print('done', len(res))
