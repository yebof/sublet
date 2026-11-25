"""Audit (C2): Theorem 3 takes inf over finite purchase times s only.  A reactive algorithm that
never buys before a notice has ratio exactly 1/alpha (R = inf, x -> inf).  Check that the true
inf_s max(F1, F2) is <= 1/alpha (so the omission is harmless), and show that families.lb_react
(s restricted to [1e-3, 8], the pre-audit window, lb_react(..., tail=False)) can over-estimate the
inf when the minimiser is at s -> inf; the post-audit default (tail=True: geometric grid to 1e4 plus
the never-buy limit 1/alpha) is printed next to it.
Output: audit/out/never_buy.txt"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from model import Params
from families import lb_react, F1, F2_parts, cr_ins
lines = []
for kw in [dict(alpha=0.5, ap=0.8, mu=10.0, lam=1.0, H=0.0), dict(alpha=0.5, ap=0.8, mu=4.0, lam=1.0, H=0.0),
           dict(alpha=0.5, mu=10.0, H=0.0, allow_p=False)]:
    P = Params(**kw)
    vals = []
    for s in [8, 20, 50, 200, 1000]:
        f2 = min(F2_parts(s, P))
        vals.append(f"s={s}: max(F1,F2)={max(F1(s, P), f2):.4f}")
    l, sarg = lb_react(P, tail=False)
    l2, sarg2 = lb_react(P)
    lines.append(f"{kw}: 1/alpha={1/P.alpha:.4f} CR_ins={cr_ins(P):.4f} families.lb_react(s<=8, pre-audit)={l:.4f} at s={sarg:.2f}; "
                 f"families.lb_react(default, post-audit)={l2:.4f} at s={sarg2:.2f}; " + '; '.join(vals))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'never_buy.txt')
open(out, 'w').write('\n'.join(lines) + '\n'); print('\n'.join(lines))

# Direct simulation of the never-buy reactive algorithm NB: fallback until the notice; after the
# reclaim at R (H = 0) buy protected at max(R, theta(R)) with theta(R) = s0 if R < alpha*s0 else R.
from model import opt_cost, INF
P = Params(alpha=0.5, ap=0.8, mu=10.0, lam=1.0, H=0.0)
b, a, ap = P.beta, P.alpha, P.ap
s0 = b / (1 - a)
xs = np.concatenate([np.linspace(1e-4, 60, 60001), np.geomspace(61, 1e7, 200)])
w = (xs / opt_cost(xs, INF, P)).max()
for R in np.linspace(0.0, 50, 5001):
    v = s0 if R < a * s0 else R
    A = np.where(xs <= v, xs, v + b + ap * (xs - v))
    w = max(w, (A / opt_cost(xs, R, P)).max())
line = f"never-buy reactive algorithm, {P}: worst ratio over R in [0,50] U {{inf}} = {w:.4f} (1/alpha = {1/a:.4f})"
print(line)
open(out, 'a').write(line + '\n')
