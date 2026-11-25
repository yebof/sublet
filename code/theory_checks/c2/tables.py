"""Tables for the write-up.
  por   : CR*(H) and price of revocability PoR(H) = CR*(H)/(2-alpha) at calibrated parameters
          (exact deterministic game dt=0.05 and family lower bound)          -> out/table_por.txt
  rand  : optimal randomized CR (sequence-form LP, dt=0.1) next to deterministic -> out/table_rand.txt
  conv  : grid convergence of the exact solver (dt = 0.1, 0.05, 0.025)          -> out/table_conv.txt
Usage: python tables.py por|rand|conv
"""
import os, sys, itertools
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
from multiprocessing import Pool
from model import Params
from det_game import solve_det
from families import lb_total


def job_por(kw):
    P = Params(**kw)
    r = solve_det(P, dt=0.05, T=13.0, Rmax=7.0, full_plans=False)
    lb, lbr, s = lb_total(P)
    return kw, r['CR'], str(r['plan']), lb


def job_rand(kw):
    from rand_lp import solve_rand
    P = Params(**kw)
    rr = solve_rand(P, dt=0.1, T=8.0, Rmax=5.0, Ts=4.0, Vmax=4.0)
    rd = solve_det(P, dt=0.1, T=8.0, Rmax=5.0, Ts=4.0, full_plans=False)
    pmass = sum(rr['plan'].get('p', {}).values())
    return kw, rr['CR'], rd['CR'], pmass, rr['plan']['none']


def job_conv(args):
    kw, dt = args
    P = Params(**kw)
    r = solve_det(P, dt=dt, T=10.0, Rmax=6.0, full_plans=False)
    return kw, dt, r['CR']


if __name__ == '__main__':
    which = sys.argv[1]
    if which == 'por':
        jobs = [dict(alpha=0.3, ap=0.7, mu=mu, lam=lam, H=H)
                for mu, lam, H in itertools.product([0.5, 1.0, 2.0], [0.0, 0.5, 1.0],
                                                    [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0])]
        with Pool(6) as pool:
            res = pool.map(job_por, jobs)
        with open('out/table_por.txt', 'w') as f:
            f.write("alpha=0.3 ap=0.7 beta=1 tau=0; CR = exact det (dt=0.05), LB = family lower bound, PoR = CR/(2-alpha)\n")
            f.write("mu lam H | CR LB PoR | plan\n")
            for kw, cr, plan, lb in res:
                f.write(f"{kw['mu']} {kw['lam']} {kw['H']} | {cr:.4f} {lb:.4f} {cr/(2-kw['alpha']):.4f} | {plan}\n")
    elif which == 'rand':
        jobs = []
        for mu, H in itertools.product([0.5, 1.0, 2.0], [0.0, 0.5, 1.0]):
            jobs.append(dict(alpha=0.0, ap=1.0, mu=mu, H=H, allow_p=False))
        for mu, lam, H in itertools.product([0.5, 1.0, 2.0], [0.0, 0.5], [0.0, 0.5, 1.0]):
            jobs.append(dict(alpha=0.3, ap=0.7, mu=mu, lam=lam, H=H))
        for ap in [0.4, 0.5]:
            jobs.append(dict(alpha=0.3, ap=ap, mu=2.0, lam=0.5, H=0.0))
        with Pool(6) as pool:
            res = pool.map(job_rand, jobs)
        with open('out/table_rand.txt', 'w') as f:
            f.write("randomized LP (dt=0.1, T=8, Rmax=5) vs deterministic (same grid); p_mass = prob. of insuring before notice\n")
            f.write("params | CR_rand CR_det | p_mass none_mass\n")
            for kw, crr, crd, pm, nm in res:
                f.write(f"{kw} | {crr:.4f} {crd:.4f} | {pm:.3f} {nm:.3f}\n")
    elif which == 'randh':
        jobs = [dict(alpha=0.0, ap=1.0, mu=mu, H=H, allow_p=False) for mu in [0.5, 1.0]
                for H in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2]]
        jobs += [dict(alpha=0.3, ap=0.7, mu=1.0, lam=0.0, H=H) for H in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2]]
        with Pool(6) as pool:
            res = pool.map(job_rand, jobs)
        with open('out/table_randh.txt', 'w') as f:
            f.write("randomized LP vs notice H (dt=0.1, T=8, Rmax=5)\n")
            f.write("params | CR_rand CR_det\n")
            for kw, crr, crd, pm, nm in res:
                f.write(f"{kw} | {crr:.4f} {crd:.4f}\n")
    elif which == 'conv':
        pts = [dict(alpha=0.0, mu=1.0, H=0.0, allow_p=False), dict(alpha=0.3, mu=1.0, H=0.0, allow_p=False),
               dict(alpha=0.0, mu=4.0, H=2.0, allow_p=False), dict(alpha=0.3, ap=0.7, mu=2.0, lam=0.5, H=0.25),
               dict(alpha=0.3, ap=0.7, mu=1.0, lam=0.5, H=0.25), dict(alpha=0.0, ap=0.5, mu=4.0, lam=0.5, H=0.0)]
        jobs = [(kw, dt) for kw in pts for dt in [0.1, 0.05, 0.025]]
        with Pool(6) as pool:
            res = pool.map(job_conv, jobs)
        with open('out/table_conv.txt', 'w') as f:
            f.write("exact deterministic CR vs grid step dt (T=10, Rmax=6)\n")
            for kw, dt, cr in res:
                f.write(f"{kw} dt={dt}: {cr:.4f}\n")
    print(open(f'out/table_{which}.txt').read())
