"""Audit (C2): the 'two-family closed form' of Section 5 is labelled PROVEN (as a lower bound) with
m_A = mu (cold) or m_A = beta (pre-warm, lam = 0).  Unconditionally, F2(s) >= (s+b+aH+m)/(s+H) holds with
m = mu only if the algorithm cannot pre-warm (H < lam or no protected option); if it can (H >= lam),
only m = min(mu, beta) is unconditional.  This script compares, for H >= lam > 0 and mu > beta (inside
(C) and H < H*), the closed form with m_A = mu against the rigorous family bound of necessity_lb.lb_all
(a valid lower bound on CR*), and against the closed form with m_A = min(mu, beta).
Output: audit/out/closed_form_mA.txt"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from alg_star_exact import thresholds
from necessity_lb import lb_all

def quad(a, H, m, b=1.0):
    A = 1 - a; B = H * (1 - a * a) - a * (b + m); C = b * (H * (1 - a) - b - m)
    s = (-B + np.sqrt(B * B - 4 * A * C)) / (2 * A)
    return max(2 - a, (s + b) / (b + a * s)), s

lines = []
def log(t):
    print(t, flush=True); lines.append(t)
log('Reactive class only (insure-up-front excluded, as in the closed form).')
log('a ap mu lam H | H* | quad(m=mu) | quad(m=min(mu,b)) | rigorous react LB | quad(m=mu) - LB')
mx = -np.inf; arg = None
for a in [0.1, 0.3, 0.5]:
    lo = max(1 / (2 - a), a * (2 - a))
    for ap in [lo + 0.01, 0.9]:
        for mu in [1.5, 2.0, 3.0, 4.0]:
            for lam in [0.1, 0.5]:
                th = thresholds(a, ap, mu, lam)
                Hs = th['Hs'] if np.isfinite(th['Hs']) else 8.0
                for H in np.unique(np.round(np.linspace(lam, min(Hs, 8.0) - 1e-6, 4), 4)):
                    P = dict(b=1.0, a=a, ap=ap, mu=mu, lam=lam, rrl=False)
                    q1, _ = quad(a, H, mu); q2, _ = quad(a, H, min(mu, 1.0))
                    L, info = lb_all(P, H, ds=5e-4, du=max(1e-3, H / 3000), dR=max(0.01, H / 1500), include_insure=False)
                    d = q1 - L
                    if d > mx:
                        mx, arg = d, (a, ap, mu, lam, H)
                    flag = '   <-- closed form (m=mu) above a rigorous LB' if d > 1e-3 else ''
                    log(f'{a} {ap:.3f} {mu} {lam} {H:.3f} | {Hs:.3f} | {q1:.4f} | {q2:.4f} | {L:.4f} ({info["binding"]}) | {d:+.4f}{flag}')
log(f'max (quad(m=mu) - rigorous LB) = {mx:+.4f} at (a, ap, mu, lam, H) = {arg}')
open(os.path.join(HERE, 'out', 'closed_form_mA.txt'), 'w').write('\n'.join(lines) + '\n')
