"""Audit (C2, model/solver lens): exact deterministic game (det_game.solve_det) on finer grids
(dt = 0.05, some at 0.025) just below and at the Theorem 4 threshold H*, and at the corners of the
Section 9 'calibrated range' where the Section 9 restatement H* = mu/(2(q-a)) drops the proviso of
Corollary 5.3.  Thresholds from alg_check.thresholds (the Theorem 4 formula incl. kappa terms).
Planned pre-notice upgrades are omitted (full_plans=False): they belong to the insurance class,
whose ratio is >= ap/alpha > 2 - alpha in every case below.
Output: audit/out/model_hstar_fine.txt"""
import os, sys
os.environ['OMP_NUM_THREADS'] = '1'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multiprocessing import Pool
from model import Params
from det_game import solve_det
from alg_check import thresholds

CASES = [  # (label, params, H list, dt)
    ('a=1/3 ap=.8 mu=1.5 lam=.5', dict(alpha=1/3, ap=0.8, mu=1.5, lam=0.5), [1.10, 1.15], 0.05),
    ('a=.5 ap=.8 mu=1 lam=.5', dict(alpha=0.5, ap=0.8, mu=1.0, lam=0.5), [0.95, 1.00], 0.05),
    ('a=1/3 ap=.8 mu=.5 lam=0', dict(alpha=1/3, ap=0.8, mu=0.5, lam=0.0), [0.35, 0.40], 0.05),
    ('a=1/3 ap=.8 mu=1.5 lam=0 (pre-warm)', dict(alpha=1/3, ap=0.8, mu=1.5, lam=0.0), [0.70, 0.75], 0.05),
    ('a=.2 ap=.56 mu=2 lam=1 (kappa term)', dict(alpha=0.2, ap=0.56, mu=2.0, lam=1.0), [1.45, 1.50], 0.05),
    ('a=.2 ap=.6 mu=1.5 lam=.5', dict(alpha=0.2, ap=0.6, mu=1.5, lam=0.5), [0.90, 0.95], 0.05),
    ('RRL a=0 mu=.5', dict(alpha=0.0, ap=1.0, mu=0.5, allow_p=False), [0.20, 0.25], 0.05),
    ('RRL a=1/3 mu=3', dict(alpha=1/3, ap=1.0, mu=3.0, allow_p=False), [2.20, 2.25], 0.05),
    ('a=1/3 ap=.8 mu=3 lam=.5 (known window)', dict(alpha=1/3, ap=0.8, mu=3.0, lam=0.5), [6.45, 6.50], 0.05),
    # Section 9 corners: mu = 2 beta, alpha in [0.2, 0.5], ap = max(1/(2 - alpha), > alpha(2-alpha)): lowest protected price allowed in Sec. 9
    # (at alpha = 0.5 the bound ap > alpha(2-alpha) = 0.75 dominates 1/(2-alpha), and Cor. 5.3's proviso holds there)
    ('Sec9 corner a=1/3 ap=.6 mu=2 lam=.5', dict(alpha=1/3, ap=0.6, mu=2.0, lam=0.5), [1.50, 1.95, 2.00], 0.05),
    ('Sec9 corner a=.2 ap=1/1.8 mu=2 lam=.5', dict(alpha=0.2, ap=1/1.8, mu=2.0, lam=0.5), [1.25, 1.45, 1.50], 0.05),
    # finer grid at the boundary
    ('a=1/3 ap=.8 mu=1.5 lam=.5 [dt=.025]', dict(alpha=1/3, ap=0.8, mu=1.5, lam=0.5), [1.100, 1.125], 0.025),
    ('a=1/3 ap=.8 mu=.5 lam=0 [dt=.025]', dict(alpha=1/3, ap=0.8, mu=0.5, lam=0.0), [0.350, 0.375], 0.025),
]


def run(job):
    label, kw, H, dt = job
    P = Params(H=H, **kw)
    Rmax = H + 6.0
    r = solve_det(P, dt=dt, T=Rmax + 7.0, Rmax=Rmax, full_plans=False)
    th = thresholds(P) if kw.get('allow_p', True) else None
    return label, H, dt, r['CR'], 2 - kw['alpha'], r['plan'], th


if __name__ == '__main__':
    jobs = [(l, kw, H, dt) for l, kw, Hs, dt in CASES for H in Hs]
    lines = ["label | H | dt | exact CR | 2-alpha | excess | best plan | Theorem 4 H* (H_cold, H_warm) | mu/(2(1-alpha))"]
    with Pool(4) as p:
        res = p.map(run, jobs, chunksize=1)
    for label, H, dt, cr, c, plan, th in res:
        kw = dict(CASES[[x[0] for x in CASES].index(label)][1])
        rule = kw['mu'] / (2 * (1 - kw['alpha']))
        hs = f"{th['Hstar']:.4f} ({th['Hc']:.4f}, {th['Hh']:.4f})" if th else "Cor. 6"
        lines.append(f"{label} | H={H:.3f} | dt={dt} | {cr:.5f} | {c:.5f} | {cr - c:+.5f} {'(=2-a)' if cr <= c + 1e-4 else '(>2-a)'} | {plan} | {hs} | {rule:.4f}")
    print('\n'.join(lines))
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'model_hstar_fine.txt'), 'w').write('\n'.join(lines) + '\n')
