"""Audit (C2, model/solver lens): does the randomized ratio keep falling beyond the deterministic H*
on a finer grid?  (Bears on the Section 9 design rule 'buy H*, not longer', which is a statement
about the deterministic worst-case ratio.)  rand_lp.solve_rand at dt = 0.05 (write-up: dt = 0.1,
out/table_randh.txt).  Deterministic H*: RRL alpha=0, mu=1: 0.5 (Cor. 6); menu alpha=0.3, ap=0.7,
mu=1, lam=0: 0.714 (Cor. 5.2).  LPs are solved one at a time (memory).
Output: audit/out/model_rand_fine.txt"""
import os, sys, time
os.environ['OMP_NUM_THREADS'] = '1'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model import Params
from rand_lp import solve_rand

# (label, params, H, horizon (T, Rmax, Ts, Vmax)).  The menu case (alpha=0.3, ap=0.7, mu=1, lam=0) was dropped:
# its LP-building step exceeded the 3 GB memory cap at dt = 0.05 even with horizon (6, 4, 3, 2); only RRL is
# checked at the finer grid (the menu values at dt = 0.1 are in out/table_randh.txt).
JOBS = [('RRL a=0 mu=1 (det H*=0.5)', dict(alpha=0.0, ap=1.0, mu=1.0, allow_p=False), H, (8.0, 5.0, 4.0, 4.0)) for H in [0.5, 0.6, 0.75, 1.0]]
JOBS += [('RRL a=0 mu=0.5 (det H*=0.25)', dict(alpha=0.0, ap=1.0, mu=0.5, allow_p=False), H, (8.0, 5.0, 4.0, 4.0)) for H in [0.25, 0.3, 0.4, 0.6]]

if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'model_rand_fine.txt')
    lines = ["randomized LP (rand_lp.solve_rand, dt=0.05; horizon (T, Rmax, Ts, Vmax) per row)"]
    open(out, 'w').write(lines[0] + '\n')
    for label, kw, H, (T, Rmax, Ts, Vmax) in JOBS:
        t = time.time()
        r = solve_rand(Params(H=H, **kw), dt=0.05, T=T, Rmax=Rmax, Ts=Ts, Vmax=Vmax)
        line = f"{label}: H={H} horizon={(T, Rmax, Ts, Vmax)} CR_rand={r['CR']:.4f}  [{time.time() - t:.0f}s]"
        print(line, flush=True)
        with open(out, 'a') as f:
            f.write(line + '\n')
