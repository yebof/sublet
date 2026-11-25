"""G4 stress, switch at slot 0: on the instances and synthetic eager experts of part (C) of
a5_guard_independent.py (same seeds), count the T11 combinations started with a forced first expert
('X' or 'Y', gamma' in {1.05, 1.3, 1+1/sqrt2, 2.5}) that switch at slot 0.
Audit of C3 §9: design/theory/audit_guard.md. Uses a5_guard_independent.py and core.py of
code/theory_checks/c3. Output: out/a7_g4_switch0.txt (also printed)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import numpy as np
from a5_guard_independent import Ix, ex_synth, combine, G2C
from core import random_instance
n0 = tot = 0
for rep in range(150):
    rng = np.random.default_rng(424242 + rep)
    I = random_instance(rng, T=30, m=3, J=2, n=6, q=float(rng.choice([2.0, 6.0])), contracts=[(0, 1, 1.0), (2, 1, 1.2), (4, 3, 1.5)])
    ix = Ix(I, 's')
    A = ex_synth(ix, rng, 'SA', 0, phase_len=int(rng.integers(2, 6)), growth=float(rng.uniform(1.2, 1.8)))
    Bx = ex_synth(ix, rng, 'SB', 1, phase_len=int(rng.integers(2, 6)), growth=float(rng.uniform(1.2, 1.8)))
    for gp in (1.05, 1.3, G2C, 2.5):
        for first in ('X', 'Y'):
            S = combine(ix, A, Bx, gp, first)
            tot += 1
            n0 += int(any(pid[0] == 'copy' for pid, _ in S.buys[0]) or (S.switches and S.inc[0] != (A if first == 'X' else Bx).inc[0]))
line = f'combinations with a forced first expert: {tot}; with a switch at slot 0: {n0}'
print(line)
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
with open(os.path.join(HERE, 'out', 'a7_g4_switch0.txt'), 'w') as f:
    f.write(line + '\n')
