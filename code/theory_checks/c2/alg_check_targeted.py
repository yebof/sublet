"""Targeted instances for Theorem 4's algorithm ALG* (alg_check.py): warm reaction with lam > 0,
and binding threshold above R_wait (known-window regime).  Output: out/alg_check_targeted.txt"""
import numpy as np
from model import Params
from alg_check import thresholds, worst_star

rng = np.random.default_rng(11)
lines = ["ALG* at H = H* and H* + 0.3; instances where warm (lam>0) or R_rho > R_wait"]
cnt = 0; mx = -1; kinds = {}
while cnt < 60:
    al = rng.uniform(0.25, 0.5)
    ap = rng.uniform(max(1 / (2 - al), al * (2 - al)) + 1e-3, 1.0)
    mu = rng.uniform(2.0, 8.0)
    lam = rng.uniform(0.01, 1 / (1 - al))
    P0 = Params(mu=mu, alpha=al, ap=ap, lam=lam)
    th = thresholds(P0)
    warm = th['Hh'] < th['Hc']
    Rx = th['Rh'] if warm else th['Rc']
    kind = ('warm' if warm else 'cold', 'Rx>Rwait' if Rx > th['Rw'] else 'Rx<=Rwait')
    if th['Hstar'] > 12 or kind == ('cold', 'Rx<=Rwait'):
        continue
    kinds[kind] = kinds.get(kind, 0) + 1
    for H in [th['Hstar'], th['Hstar'] + 0.3]:
        w, arg, _ = worst_star(P0.with_(H=H), Rmax=H + 8, dR=0.02)
        mx = max(mx, w - (2 - al)); cnt += 1
        lines.append(f"{kind} alpha={al:.3f} ap={ap:.3f} mu={mu:.3f} lam={lam:.3f} H*={th['Hstar']:.3f} H={H:.3f}: worst={w:.5f} excess={w-(2-al):+.2e} at R={arg}")
lines.append(f"branch counts (instances): {kinds}")
lines.append(f"SUMMARY: {cnt} runs, max excess over 2-alpha = {mx:+.3e}")
print('\n'.join(lines[-3:]))
open('out/alg_check_targeted.txt', 'w').write('\n'.join(lines) + '\n')
