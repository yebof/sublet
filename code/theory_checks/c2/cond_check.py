"""Theorem 4 side condition (2-a)ap >= 1: exact CR around H = mu/(2(1-a)) when it fails.
alpha=0.2 (s0=1.25 on the dt=0.05 grid), ap=0.45 (in (a(2-a), 1/(2-a)) = (0.36, 0.556)).
Output: out/cond_check.txt"""
import numpy as np
from model import Params
from det_game import solve_det
lines = []
for mu in [0.5, 1.0]:
    Hc = mu / (2 * 0.8)
    for H in [0.0, 0.25, 0.5, 0.6, 0.65, 0.75, 1.0, 1.5]:
        r = solve_det(Params(alpha=0.2, ap=0.45, mu=mu, lam=0.5, H=H), dt=0.05, T=12, Rmax=7, full_plans=False)
        lines.append(f"alpha=0.2 ap=0.45 mu={mu} lam=0.5 H={H} (mu/(2(1-a))={Hc:.4f}): CR={r['CR']:.4f} (2-a=1.8) plan={r['plan']}")
        print(lines[-1], flush=True)
open('out/cond_check.txt', 'w').write('\n'.join(lines) + '\n')
