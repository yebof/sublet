"""Audit (C2): is alpha <= 1/2 needed in Theorem 4?  Exact game (det_game, dt=0.1) around the
Theorem 4 formula H* for alpha in {0.6, 0.75} with all other parts of (C) satisfied
((2-a)ap >= 1, ap > a(2-a), lam <= s0, tau = 0).  Output: audit/out/t4_alpha_gt_half.txt"""
import os, sys
os.environ.setdefault('OMP_NUM_THREADS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from multiprocessing import Pool
from model import Params
from det_game import solve_det
import importlib.util
spec = importlib.util.spec_from_file_location('fc', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'formula_check.py'))

def thm4(al, ap, mu, lam, b=1.0):
    big = lambda n, d: (np.inf if n > 0 else -np.inf) if d == 0 else n / d
    c = 2 - al; s0 = b / (1 - al); kap = c * ap - al; Rw = c * b / (1 - al) ** 2
    Hm = lambda R: R - s0 if R <= Rw + 1e-12 else R
    Rc = max(s0 + mu / (2 * (1 - al)), big(mu - 2 * (1 - al) * b, al * (1 - al)), (mu + al * b) / kap)
    Rh = max(s0 + b / (2 * (1 - al)), (1 + al) * b / kap)
    if lam > 0:
        Rh = max(Rh, lam + big((1 + al) * b, al * (1 - al)))
    return min(Hm(Rc), max(lam, Hm(Rh))), Hm(Rc), max(lam, Hm(Rh))

CASES = [dict(alpha=0.6, ap=0.9, mu=1.0, lam=0.5), dict(alpha=0.6, ap=0.9, mu=3.0, lam=0.5),
         dict(alpha=0.6, ap=0.9, mu=2.0, lam=0.0), dict(alpha=0.6, ap=0.9, mu=2.4, lam=1.0),
         dict(alpha=0.75, ap=0.95, mu=1.0, lam=0.0), dict(alpha=0.75, ap=0.95, mu=3.0, lam=0.9)]

def job(arg):
    kw, H = arg
    Rmax = H + 8.0
    r = solve_det(Params(H=H, **kw), dt=0.1, T=Rmax + 9.0, Rmax=Rmax, full_plans=False)
    return kw, H, r['CR']

if __name__ == '__main__':
    jobs = []; pred = {}
    for kw in CASES:
        hs, hc, hw = thm4(kw['alpha'], kw['ap'], kw['mu'], kw['lam'])
        pred[str(kw)] = (hs, hc, hw)
        g = np.ceil(hs / 0.1 - 1e-9) * 0.1
        for H in [g - 0.2, g - 0.1, g, g + 0.1]:
            jobs.append((kw, round(max(H, 0), 10)))
    with Pool(4) as p:
        res = p.map(job, jobs)
    lines = ["params | H* (Thm 4 formula; H_cold, H_warm) | H | exact CR | CR-(2-a)"]
    for kw, H, cr in res:
        hs, hc, hw = pred[str(kw)]
        lines.append(f"{kw} | {hs:.4f} ({hc:.4f}, {hw:.4f}) | {H:.2f} | {cr:.5f} | {cr-(2-kw['alpha']):+.5f}")
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 't4_alpha_gt_half.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
