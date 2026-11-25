"""C2-SW formula breakpoints at the default calibration (design/Sublet_design.md §2.2 reading 2, §2.8 item 8,
§3.4, Q11, Q17; c2_single_site.md §6 "Switch cost").

Evaluates the C2-SW substitution formula (CONJECTURE), the same function `c2sw` that
model_switch_cost_default.py checks against the exact game at 58 points, on a fine mu grid, and reports
where (i) the simple form mu/(2(1-alpha)) stops holding (theory: mu = 2 bw), (ii) the cold threshold enters
the known-window regime, and (iii) the minimizing reaction switches from cold to pre-warm.  It also checks
the claim of c2_single_site.md §6 that at mu = 2 beta any bw < beta pushes the cold threshold into the
known-window regime: that needs the L3 term (mu + a b - (2 - a) bw)/(a (1 - a)) above R_wait.

Formula only: the exact game was run at mu/beta~ in {0.2, 0.5, 1, 2} (model_switch_cost_default.txt).
No exact-game evaluation here; runs in about a second.
Output: audit/out/switch_cost_crossover.txt."""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from model_switch_cost_default import c2sw, AL, AP, BW_DEF, LAM_DEF

STEP = 0.001
MU_MAX = 4.0


def breakpoints(lam, bw, a=AL, ap=AP):
    """mu values (grid STEP, in beta) where the formula's (simple form?, reaction, regime) label changes"""
    out, prev = [], None
    for i in range(1, int(round(MU_MAX / STEP)) + 1):
        mu = i * STEP
        f = c2sw(mu, lam, bw, a=a, ap=ap)
        simple = abs(f['H'] - mu / (2 * (1 - a))) < 1e-9
        key = ('simple form' if simple else 'above simple form', f['react'], f['regime'])
        if key != prev:
            out.append((mu, key, f['H']))
            prev = key
    return out


def l3_vs_rwait(mu, bw, a, b=1.0):
    l3 = (mu + a * b - (2 - a) * bw) / (a * (1 - a))
    rw = (2 - a) * b / (1 - a) ** 2
    return l3, rw


lines = []
P = lines.append
P(f"C2-SW formula breakpoints (formula CONJECTURE; units beta = beta~ = 1, q = 1): alpha={AL:.6f} alpha_p={AP:.6f}")
P(f"default calibration: lambda = {LAM_DEF:.4f}, bw = {BW_DEF:.4f}; mu grid step {STEP}; each row: first mu with that label")
P("label = (simple form mu/(2(1-alpha)) or above it, minimizing reaction, regime of that reaction's threshold)")
cases = [(LAM_DEF, BW_DEF, 'default calibration'),
         (0.5, BW_DEF, 'default switch, lambda = 0.5'),
         (0.25, BW_DEF, 'default switch, lambda = 0.25'),
         (1e-9, BW_DEF, 'default switch, lambda -> 0'),
         (0.5, 0.7182, 'fee-consistent pair'),
         (0.25, 0.8591, 'fee-consistent pair')]
for lam, bw, lab in cases:
    P(f"\nlambda={lam:.4f} bw={bw:.4f} ({lab}); 2 bw = {2 * bw:.4f}")
    for mu, key, H in breakpoints(lam, bw):
        P(f"  mu >= {mu:.3f}: {key[0]}, {key[1]}, {key[2]} (H* = {H:.4f})")

P("\nlambda dependence at mu = 2, bw = 0.8 (formula; exact brackets in model_switch_cost_default.txt):")
for lam in (0.25, 0.5, LAM_DEF):
    f = c2sw(2.0, lam, 0.8)
    P(f"  lambda={lam:.4f}: H* = {f['H']:.4f} ({f['react']}, {f['regime']}); cold {f['Hc']:.4f}, pre-warm {f['Hh']:.4f}")

P("\nc2_single_site.md §6 check at mu = 2 beta: cold threshold in the known-window regime iff L3 > R_wait"
  " (the kappa term is below R_wait in every case below)")
for a, ap, lab in ((1 / 3, 0.8, 'alpha = 1/3, alpha_p = 0.8'), (AL, AP, 'default prices')):
    chi = (2 - a) * ap - a
    P(f"  {lab}: R_wait = {(2 - a) / (1 - a) ** 2:.4f}, kappa term (mu + a)/chi = {(2 + a) / chi:.4f}")
    for bw in (0.6, 0.8, 0.8591, 0.9, 0.95, 1.0):
        l3, rw = l3_vs_rwait(2.0, bw, a)
        P(f"    bw={bw:.4f}: L3 = {l3:.4f} -> {'known window' if l3 > rw + 1e-12 else 'sit-out'}"
          f" (cold threshold above s0 + mu/(2(1-a)) = {1 / (1 - a) + 1 / (1 - a):.4f}: {l3 > 2 / (1 - a) + 1e-12})")
    # bw at which L3 = R_wait
    bw_star = (2 + a - a * (1 - a) * (2 - a) / (1 - a) ** 2) / (2 - a)
    P(f"    L3 = R_wait at bw = {bw_star:.4f}")

out = os.path.join(HERE, 'out', 'switch_cost_crossover.txt')
with open(out, 'w') as fh:
    fh.write('\n'.join(lines) + '\n')
print('\n'.join(lines))
