"""T9 with the audit's fix: only the nearest predicted column F_hat(e) joins each request's
candidate set (d <= mK + 2).  Same instances and predictions as check_c5_la.py part (a).
Checks P <= 2/(1-lam) c(P_hat(sigma)) and dual feasibility with ln(1 + d/lam), d = mK + 2.
Output: out/c5_la_nearest.txt, out/c5_la_nearest.json
"""
import os, sys, json, math
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
import multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import random_instance, opt_eager, opt_eager_cols, lp_aligned
from pd import FracPD, pred_cost
from check_c5_la import NOISE, LAMS, predicted, OUT


def job(seed):
    rng = np.random.default_rng(11000 + seed)
    I = random_instance(rng, T=36, m=4, J=2, n=8)
    OPT = opt_eager(I)['fun']
    LPal = lp_aligned(I)['fun']
    rows = []
    for kind, par in NOISE:
        Ip = predicted(I, kind, par, np.random.default_rng(12000 + seed))
        P = opt_eager_cols(Ip, opt_eager(Ip))
        cP = pred_cost(I, P)
        for lam in LAMS:
            pdl = FracPD(I, lam=lam, pred_cols=P, nearest_pred=True).run()
            Pl = pdl.primal()
            rows.append(dict(kind=kind, par=par, lam=lam, d=pdl.d, P_over_OPT=Pl / OPT,
                             cons_chk=(Pl / (2 / (1 - lam) * cP)) if lam < 1 else None,
                             dualfeas=pdl.check_dual_feasible(),
                             rob_chk=Pl / (2 * math.log(1 + pdl.d / lam) * LPal)))
    return dict(seed=seed, rows=rows)


if __name__ == '__main__':
    with mp.get_context('spawn').Pool(5) as p:
        R = p.map(job, range(10))
    json.dump(R, open(os.path.join(OUT, 'c5_la_nearest.json'), 'w'), indent=1)
    rows = [x for r in R for x in r['rows']]
    L = ['T9 with nearest predicted column only (d = mK + 2); 10 instances x 9 predictions x 5 lambdas',
         f"max d: {max(x['d'] for x in rows)}",
         f"max consistency check P/(2c(P)/(1-lam)): {max(x['cons_chk'] for x in rows if x['cons_chk'] is not None):.3f} (must be <= 1)",
         f"max dual load / (c ln(1+d/lam)): {max(x['dualfeas'] for x in rows):.3f} (must be <= 1)",
         f"max P / (2 ln(1+d/lam) LP_al): {max(x['rob_chk'] for x in rows):.3f} (must be <= 1)"]
    for lam in LAMS:
        ex = [x['P_over_OPT'] for x in rows if x['lam'] == lam and x['kind'] == 'exact']
        L.append(f"lam={lam}: mean P/OPT_eager with exact prediction {np.mean(ex):.3f}")
    txt = '\n'.join(L)
    print(txt)
    open(os.path.join(OUT, 'c5_la_nearest.txt'), 'w').write(txt + '\n')
