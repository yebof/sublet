"""Audit (C2): exact deterministic game (det_game.solve_det, dt as given) around the Theorem 4 /
Corollary 6 threshold H* in regimes NOT covered by out/hstar.txt (which has ap = 0.8 only):
  - kappa term of R_cold binding (ap at the lower end of condition (C)),
  - L3 term (mu - 2(1-a)beta)/(a(1-a)) binding, both regimes,
  - lam = s0 (boundary of (C)), alpha = 0 with protection,
  - RRL (Corollary 6) at alpha > 1/2 (claimed for every alpha in [0,1)).
Output: audit/out/t4_exact.txt"""
import os, sys
os.environ.setdefault('OMP_NUM_THREADS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from multiprocessing import Pool
from model import Params
from det_game import solve_det
from formula_check import thm4, Hmap

def rrl_h(al, mu, b=1.0):
    s0 = b / (1 - al); Rw = (2 - al) * b / (1 - al) ** 2
    return Hmap(s0 + mu / (2 * (1 - al)), s0, Rw)

CASES = [
    ('kappa-binding cold', dict(alpha=1/3, ap=0.6, mu=2.0, lam=0.5)),
    ('kappa-binding cold', dict(alpha=1/3, ap=0.6, mu=1.8, lam=0.5)),
    ('L3-binding cold, regime 1', dict(alpha=0.5, ap=0.8, mu=2.2, lam=0.5)),
    ('L3-binding cold, known window', dict(alpha=1/3, ap=0.8, mu=2.4, lam=0.5)),
    ('lam = s0', dict(alpha=1/3, ap=0.8, mu=1.5, lam=1.5)),
    ('alpha=0 menu, lam>0', dict(alpha=0.0, ap=0.6, mu=1.6, lam=0.5)),
    ('alpha=0 menu, lam=0, mu>2beta', dict(alpha=0.0, ap=0.6, mu=2.6, lam=0.0)),
    ('RRL alpha=0.6', dict(alpha=0.6, mu=1.0, allow_p=False)),
    ('RRL alpha=0.6', dict(alpha=0.6, mu=4.0, allow_p=False)),
    ('RRL alpha=0.6', dict(alpha=0.6, mu=6.0, allow_p=False)),
    ('RRL alpha=0.75', dict(alpha=0.75, mu=1.0, allow_p=False)),
]

def job(arg):
    name, kw, H, dt = arg
    P = Params(H=H, **kw)
    Rmax = H + 6.0
    r = solve_det(P, dt=dt, T=Rmax + 7.0, Rmax=Rmax, full_plans=False)
    return name, kw, H, dt, r['CR'], r['plan']

if __name__ == '__main__':
    jobs = []
    pred = {}
    for name, kw in CASES:
        if kw.get('allow_p', True):
            Hs = thm4(kw['alpha'], kw['ap'], kw['mu'], kw['lam'])[0]
        else:
            Hs = rrl_h(kw['alpha'], kw['mu'])
        pred[(name, str(kw))] = Hs
        dt = 0.1
        g = np.ceil(Hs / dt - 1e-9) * dt if np.isfinite(Hs) else 6.0
        for H in sorted(set([max(0.0, round(g - 2 * dt, 10)), max(0.0, round(g - dt, 10)), round(g, 10), round(g + dt, 10)])):
            jobs.append((name, kw, H, dt))
    with Pool(4) as pool:
        res = pool.map(job, jobs)
    lines = ["case | params | H*(formula) | H | exact CR (dt=0.1) | 2-alpha | CR-(2-alpha)"]
    for name, kw, H, dt, cr, plan in res:
        c = 2 - kw['alpha']
        lines.append(f"{name} | {kw} | {pred[(name, str(kw))]:.4f} | {H:.2f} | {cr:.5f} | {c:.5f} | {cr - c:+.5f} | plan={plan}")
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 't4_exact.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
