"""Audit (C2, proof correctness): two scope questions.

(1) Is alpha <= 1/2 needed for Theorem 4?  The proof of Thm 4 (unlike Cor 5) never uses it.
    Re-run the independent sufficiency check (alg_star_exact.worst_ratio) and the rigorous necessity
    bound (necessity_lb.lb_all) for alpha in {0.6, 0.75, 0.9} with the rest of (C).
(2) tau > 0: the model (Section 1, item 2) lets anyone buy a revocable lease at any s < R and keeps it
    until max(R, s + tau).  A second purchase shortly before R therefore extends revocable coverage
    past R ("re-buy").  model.opt_cost (used by det_game, families, scan) allows only one revocable
    purchase.  Compare model.opt_cost with an explicit re-buy schedule (second lease committed at
    d2 = R - max(lam, 0.05) < R, serving from d2 + lam <= R; both leases paid while held), and show that the re-buy is also a
    feasible reaction for the algorithm in the F2 instance of Theorem 3 (tau > H), which the proof's
    option list (cold / warm) omits.
Output: audit/out/alpha_and_tau_scope.txt"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
from alg_star_exact import thresholds, worst_ratio
from necessity_lb import lb_all
from model import Params, opt_cost

lines = []
def log(t):
    print(t, flush=True); lines.append(t)

log('(1) Theorem 4 outside alpha <= 1/2 (all other parts of (C) kept).')
log('    sufficiency: worst ratio of ALG* at H* minus (2-a);  necessity: rigorous LB at H*-0.05 minus (2-a)')
for a in [0.6, 0.75]:
    lo = max(1 / (2 - a), a * (2 - a))
    s0 = 1 / (1 - a)
    for ap in [lo + 1e-3, (lo + 1) / 2]:
        for mu in [0.3, 1.0, 1.5, 2.0, 4.0]:
            for lam in [0.0, 0.5 * s0]:
                P = dict(b=1.0, a=a, ap=ap, mu=mu, lam=lam, rrl=False)
                th = thresholds(a, ap, mu, lam)
                if not np.isfinite(th['Hs']):
                    continue
                w, arg = worst_ratio(P, th['Hs'], th, dR=0.02, Rspan=max(14.0, 2 * th['Hs']))
                Hb = th['Hs'] - 0.05
                nb = lb_all(P, Hb, ds=5e-4, du=max(1e-3, Hb / 4000), dR=max(0.01, Hb / 1500))[0] - (2 - a) if Hb >= 0 else np.nan
                flag = '' if (w - (2 - a) <= 1e-7 and (np.isnan(nb) or nb > 0)) else '   <-- FAILS'
                log(f'  a={a} ap={ap:.4f} mu={mu} lam={lam:.3f}: H*={th["Hs"]:.4f} ({th["rho"]}) '
                    f'suff {w-(2-a):+.2e}  nec(H*-0.05) {nb:+.5f}{flag}')

log('')
log('(2) tau > 0: OPT re-buy omitted by model.opt_cost.')
# (the pre-audit-record version used x = 4 = R + tau with a commit at R - lam = R for lam = 0, which is not a
#  purchase before R; the second lease must be committed at d2 < R, so x <= d2 + tau < 4: use x = 3.9, d2 = 2.95)
for kw, R, x in [(dict(alpha=0.0, ap=0.8, mu=2.0, lam=0.0, tau=1.0), 3.0, 3.9),
                 (dict(alpha=0.0, ap=0.8, mu=2.0, lam=0.5, tau=1.0), 3.0, 3.5),
                 (dict(alpha=0.3, ap=0.7, mu=2.0, lam=0.5, tau=1.0), 3.0, 3.5),
                 (dict(alpha=0.3, ap=0.8, mu=2.0, lam=0.0, tau=1.0), 3.0, 3.9)]:
    P = Params(**kw)
    b, a, lam, tau = P.beta, P.alpha, P.lam, P.tau
    G = np.round(np.arange(0, R + 1e-9, 0.01), 10)
    oc = float(opt_cost(np.array([x]), R, P, G)[0])
    # re-buy schedule: lease 1 at 0 (ends max(R, tau) = R), lease 2 committed at d2 = R - max(lam, 0.05) < R
    # (ends d2 + tau), serves from d2 + lam <= R, demand ends at x <= d2 + tau.  Both leases paid while held.
    d2 = R - max(lam, 0.05)
    E2 = d2 + tau
    assert d2 < R and x <= E2 + 1e-12
    rb = b + a * R + b + a * (x - d2)
    log(f'  {kw} R={R} x={x}: model.opt_cost={oc:.4f}  re-buy schedule={rb:.4f}  (OPT over-estimated by {oc-rb:+.4f}, '
        f'{100*(oc-rb)/rb:.1f}%)')

log('')
log('    Algorithm side, F2 instance with tau > H (notice at E - H, E = s + tau): feasible reactions at the notice')
log('    are cold, warm (commit E - lam) and re-buy (second lease committed at E - 0.05 < R = E, serving from')
log('    E, ending E - 0.05 + tau).  Costs at demand end x = E + t, t <= tau - 0.05 (tau = 1, H = 0.5, s = 2, lam = 0):')
P = Params(alpha=0.0, ap=0.8, mu=2.0, lam=0.0, tau=1.0, H=0.5)
b, a, ap, mu, lam, tau = P.beta, P.alpha, P.ap, P.mu, P.lam, P.tau
s = 2.0; E = s + tau
for t in [0.25, 0.5, 0.9]:
    cold = s + b + a * tau + mu + t
    warm = s + b + a * tau + b + ap * t
    rebuy = s + b + a * (E - s) + b + a * t
    log(f'    t={t}: cold={cold:.3f} warm={warm:.3f} re-buy={rebuy:.3f}')
log('    The re-buy is cheaper than both proof options whenever (ap - a) t > 0, i.e. the option list of Lemma 2 /')
log('    Theorem 3 is incomplete for tau > 0, and model.opt_cost / det_game omit it for OPT and the algorithm.')
open(os.path.join(HERE, 'out', 'alpha_and_tau_scope.txt'), 'w').write('\n'.join(lines) + '\n')
