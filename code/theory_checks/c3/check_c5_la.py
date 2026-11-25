"""C5 checks (Theorems 9-10 of design/theory/c3_c4_c5_general.md).

Predictions: predicted activity mask (exact / random flips / time shift / complement /
empty / flood = all clients always active);
P_hat = OPT_eager columns of the predicted instance.
(a) lambda-interpolated fractional PD: P_lam <= 2/(1-lam) * c(P_hat(sigma)) and
    dual feasibility with ln(1 + d/lam) (both must hold); P_lam / OPT_eager.
(b) integral: follow-prediction (FP), rounded robust PD (R), doubling combiner with
    gamma=2 (bound 6) and gamma=1+1/sqrt2 (bound 3+2*sqrt2); pathwise check and ratios.
Output: out/c5_la.json, out/c5_la.txt
"""
import os, sys, json, math
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
import multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import random_instance, opt_eager, opt_eager_cols, lp_aligned
from pd import FracPD, round_pd, pred_cost, follow_prediction, combine

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
NOISE = [('exact', 0), ('flip', 0.05), ('flip', 0.15), ('flip', 0.3), ('shift', 2), ('shift', 6),
         ('complement', 0), ('empty', 0), ('flood', 0)]
LAMS = [0.1, 0.3, 0.5, 0.8, 1.0]
G2 = 1 + 1 / math.sqrt(2)


def predicted(I, kind, par, rng):
    Ip = I.subset()
    A = I.active.copy()
    if kind == 'flip':
        A = A ^ (rng.random(A.shape) < par)
    elif kind == 'shift':
        A = np.zeros_like(A); A[:, par:] = I.active[:, :-par]
    elif kind == 'complement':
        A = ~A
    elif kind == 'empty':
        A = np.zeros_like(A)
    elif kind == 'flood':
        A = np.ones_like(A)
    Ip.active = A
    return Ip


def job(seed):
    rng = np.random.default_rng(11000 + seed)
    I = random_instance(rng, T=36, m=4, J=2, n=8)
    OPT = opt_eager(I)['fun']
    LPal = lp_aligned(I)['fun']
    pdR = FracPD(I).run()
    Rs = [round_pd(pdR, np.random.default_rng(s), r=1) for s in range(8)]
    Rth = [round_pd(pdR, np.random.default_rng(s)) for s in range(8)]
    out = dict(seed=seed, OPT=OPT, LPal=LPal, rows=[])
    for kind, par in NOISE:
        Ip = predicted(I, kind, par, np.random.default_rng(12000 + seed))
        P = opt_eager_cols(Ip, opt_eager(Ip))
        cP = pred_cost(I, P)
        eta = int((I.active ^ Ip.active).sum())
        row = dict(kind=kind, par=par, cPhat=cP, cPhat_over_OPT=cP / OPT, eta=eta,
                   eta_chk=bool(cP <= OPT + I.q * eta + 1e-6), lam=[])
        for lam in LAMS:
            pdl = FracPD(I, lam=lam, pred_cols=P).run()
            Pl = pdl.primal()
            row['lam'].append(dict(lam=lam, P=Pl, P_over_OPT=Pl / OPT,
                                   cons_chk=(Pl / (2 / (1 - lam) * cP)) if lam < 1 else None,
                                   dualfeas=pdl.check_dual_feasible(),
                                   rob_chk=Pl / (2 * math.log(1 + pdl.d / lam) * LPal)))
        fp = follow_prediction(I, P)
        FP = float(fp.sum())
        for tag, RR in [('r1', Rs), ('rth', Rth)]:
            c2, cg, mins, sw = [], [], [], []
            for x in RR:
                Rt = float(x['curve'].sum())
                a2, s2 = combine(I, P, fp, x['opened'], x['curve'], gamma=2.0)
                ag, _ = combine(I, P, fp, x['opened'], x['curve'], gamma=G2)
                c2.append(a2); cg.append(ag); mins.append(min(FP, Rt)); sw.append(s2)
            c2, cg, mins = map(np.array, (c2, cg, mins))
            row[tag] = dict(R=float(np.mean([x['curve'].sum() for x in RR])) / OPT, FP=FP / OPT,
                            comb2=float(c2.mean()) / OPT, combg=float(cg.mean()) / OPT,
                            chk2=float((c2 / mins).max()), chkg=float((cg / mins).max()),
                            switches=float(np.mean(sw)))
        out['rows'].append(row)
    return out


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    with mp.get_context('spawn').Pool(5) as p:
        R = p.map(job, range(10))
    json.dump(R, open(os.path.join(OUT, 'c5_la.json'), 'w'), indent=1)
    L = ['10 random instances T=36 m=4 J=2 n=8; P_hat = OPT_eager on predicted demand',
         '(a) fractional lambda-PD: mean P/OPT_eager per lambda; max consistency check P/(2c(P)/(1-lam)) and '
         'max dual-feasibility ratio (both must be <= 1)']
    for i, (kind, par) in enumerate(NOISE):
        rows = [r['rows'][i] for r in R]
        cpo = np.array([x['cPhat_over_OPT'] for x in rows])
        s = f"  {kind:10s}{par:<5} c(P)/OPT mean {cpo.mean():6.3f} | "
        for j, lam in enumerate(LAMS):
            po = np.mean([x['lam'][j]['P_over_OPT'] for x in rows])
            s += f"lam={lam}: {po:.3f} "
        cc = max(x['lam'][j]['cons_chk'] for x in rows for j in range(len(LAMS)) if x['lam'][j]['cons_chk'] is not None)
        dfe = max(x['lam'][j]['dualfeas'] for x in rows for j in range(len(LAMS)))
        rc = max(x['lam'][j]['rob_chk'] for x in rows for j in range(len(LAMS)))
        s += f"| cons_chk {cc:.3f} dualfeas {dfe:.3f} rob_chk {rc:.3f} | c(P)<=OPT+q*eta: {all(x['eta_chk'] for x in rows)}"
        L.append(s)
    L.append('(b) integral (mean ratio to OPT_eager): FP, R, combiner gamma=2 (pathwise bound 6), '
             'gamma=1+1/sqrt2 (bound 5.83); max comb/min(FP,R) pathwise')
    for tag in ['r1', 'rth']:
        L.append(f"  robust R = rounded PD with {'r=1 (heuristic)' if tag == 'r1' else 'r=ceil(2 ln N) (theory)'}")
        for i, (kind, par) in enumerate(NOISE):
            rows = [r['rows'][i][tag] for r in R]
            g = lambda k: np.array([x[k] for x in rows])
            L.append(f"   {kind:10s}{par:<5} FP {g('FP').mean():6.3f}  R {g('R').mean():6.3f}  comb2 {g('comb2').mean():6.3f}  "
                     f"combg {g('combg').mean():6.3f}  max comb2/min {g('chk2').max():.3f}  max combg/min {g('chkg').max():.3f}  "
                     f"switches {g('switches').mean():.2f}")
    txt = '\n'.join(L)
    print(txt)
    open(os.path.join(OUT, 'c5_la.txt'), 'w').write(txt + '\n')
