"""Notice threshold H* = min{H : CR*(H) = 2 - alpha} (reactive class, protected not cheap).
H*_LB: bisection on the family lower bound (families.lb_react), continuous H.
H*_ex: bisection on the exact deterministic game (det_game, dt=0.1, H on the grid).
Closed form: Theorem 4 of c2_single_site.md, H* = min{H(R_cold), max(lam, H(R_warm))}, computed by
alg_check.thresholds (the pre-audit version printed an older 'Conjecture 6' formula without the
kappa terms; on this grid (ap = 0.8) the kappa terms never bind, so the values agree).
Output: out/hstar.txt
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
import itertools
import numpy as np
from multiprocessing import Pool
from model import Params
from families import lb_react
from det_game import solve_det
from alg_check import thresholds

TOL = 2e-3


def h_lb(P):
    c = 2 - P.alpha
    lo, hi = 0.0, 12.0
    if lb_react(P.with_(H=hi))[0] > c + TOL:
        return np.inf
    for _ in range(22):
        mid = (lo + hi) / 2
        if lb_react(P.with_(H=mid))[0] > c + TOL:
            lo = mid
        else:
            hi = mid
    return hi


def h_ex(P, dt=0.1):
    """smallest grid H with exact CR <= 2 - alpha + grid tolerance (the s0 grid error)"""
    c = 2 - P.alpha
    s0 = P.beta / (1 - P.alpha)
    cgrid = c + 1e-4                               # alpha chosen so that s0 lies on the grid
    def ok(H):
        Rmax = H + 6.0
        r = solve_det(P.with_(H=H), dt=dt, T=Rmax + 7.0, Rmax=Rmax, full_plans=False)
        return r['CR'] <= cgrid
    Hs = np.round(np.arange(0, 9.0 + 1e-9, dt), 10)
    lo, hi = 0, len(Hs) - 1
    if not ok(Hs[hi]):
        return np.inf
    if ok(Hs[0]):
        return 0.0
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if ok(Hs[mid]):
            hi = mid
        else:
            lo = mid
    return Hs[hi]


def closed(P):
    """Theorem 4 of c2_single_site.md (thresholds from alg_check.thresholds, including the kappa
    terms of R_cold and R_warm): returns (H*, H(R_cold), max(lam, H(R_warm)))."""
    th = thresholds(P)
    return th['Hstar'], th['Hc'], th['Hh']


def run(kw):
    P = Params(**kw)
    return kw, h_lb(P), h_ex(P), closed(P)


if __name__ == '__main__':
    jobs = []
    for al, ap, mu, lam in itertools.product([1 / 3, 0.5], [0.8], [0.5, 1.0, 1.5, 2.0, 3.0], [0.0, 0.5, 1.0]):
        jobs.append(dict(alpha=al, ap=ap, mu=mu, lam=lam))
    with Pool(4) as pool:
        res = pool.map(run, jobs)
    with open('out/hstar.txt', 'w') as f:
        hdr = "alpha ap mu lam | H*_F2 (necessary cond. from families F1,F2 only) H*_exact(dt=0.1, first grid H with CR<=2-a+1e-4) | Theorem 4: H* (H(R_cold), max(lam, H(R_warm)))"
        print(hdr); f.write(hdr + '\n')
        for kw, hl, he, (hc, hcold, hwarm) in res:
            line = f"{kw['alpha']:.3f} {kw['ap']} {kw['mu']} {kw['lam']} | {hl:.3f} {he:.2f} | {hc:.3f} ({hcold:.3f}, {hwarm:.3f})"
            print(line); f.write(line + '\n')
