"""Audit (C2): Theorem 3, tau > H.  The text says the F2 adversary sends the notice at s^+ (so R = s + H)
while the formula divides by OPT(E+t, E) with E = s + max(H, tau).  With R = s + H < E, the true OPT is
OPT_tau(x, s+H) >= OPT_tau(x, E) (OPT is nonincreasing in R), so the literal instance gives a smaller ratio
than the formula.  The formula is recovered by the instance R = E with the notice at E - H >= s (a reactive
algorithm holds its lease unchanged until the notice).  Uses model.opt_cost with its own tau handling.
Output: audit/out/tau_f2_instance.txt"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from model import Params, opt_cost
lines = []
for kw, s in [(dict(alpha=0.3, ap=0.7, mu=1.0, lam=0.0, tau=1.0, H=0.0), 2.0),
              (dict(alpha=0.0, ap=0.6, mu=2.0, lam=0.5, tau=1.0, H=0.25), 1.0)]:
    P = Params(**kw)
    D = max(P.H, P.tau); E = s + D; Rlit = s + P.H
    x = np.array([E + 1e-9, E + 0.5])
    o_lit = opt_cost(x, Rlit, P, np.linspace(0, Rlit, 2001))
    o_E = opt_cost(x, E, P, np.linspace(0, E, 2001))
    A = s + P.beta + P.alpha * D + P.mu + np.array([0.0, 0.5])      # cold, stays on fallback
    lines.append(f"{kw}, s={s}: E={E}, literal R=s+H={Rlit}")
    for i, xx in enumerate(x):
        lines.append(f"   x={xx:.3f}: OPT(x, s+H)={o_lit[i]:.4f}  OPT(x, E)={o_E[i]:.4f}  cold ratio literal={A[i]/o_lit[i]:.4f}  formula={A[i]/o_E[i]:.4f}")
open(os.path.join(HERE, 'out', 'tau_f2_instance.txt'), 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
