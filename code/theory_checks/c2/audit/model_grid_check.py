"""Audit (C2, model/solver lens): grid error of the exact solver.
(1) The 26 scan rows with exact - LB > 0.035 (out/scan_summary.txt).  The write-up says all are of
    three structural kinds (F3 at mu = 4 beta with long notice; alpha = 0, lam > 0, mu = 4; the P10
    price band).  Five rows at alpha = 0 with H <= 1 fit none of them; we re-solve them at dt = 0.05
    and 0.025 and compare with the closed forms (report.md RRL formulas, as in det_game.rrl_closed)
    and with the family bound.  At alpha = 0 the F1 ratio (s + beta)/s has slope 1 at s0 = 1, so a
    dt = 0.1 grid gives errors up to dt/2 = 0.05, above the 0.035 tolerance used by analyze_scan.py.
(2) Table PoR cells (dt = 0.05 in the write-up) at dt = 0.025 (s0 = 1.4286 lies off both grids).
(3) Reproduction of a stratified sample of the 1120 scan rows with the current det_game (the csv
    was patched selectively by scan_fix.py).
Output: audit/out/model_grid_check.txt"""
import os, sys, csv, re
os.environ['OMP_NUM_THREADS'] = '1'
HERE = os.path.dirname(os.path.abspath(__file__)); C2 = os.path.dirname(HERE)
sys.path.insert(0, C2)
import numpy as np
from multiprocessing import Pool
from model import Params
from det_game import solve_det, rrl_closed
from families import lb_total


def job(j):
    tag, kw, dt, T, Rmax, full = j
    P = Params(**kw)
    r = solve_det(P, dt=dt, T=T, Rmax=Rmax, full_plans=full)
    return tag, kw, dt, r['CR'], r['plan']


if __name__ == '__main__':
    lines = []
    log = lambda s: (print(s, flush=True), lines.append(s))
    J = []
    rows1 = [dict(alpha=0.0, ap=0.5, mu=2.0, lam=0.5, H=0.5), dict(alpha=0.0, ap=0.5, mu=2.0, lam=1.0, H=0.5),
             dict(alpha=0.0, ap=1.0, mu=2.0, H=0.5, allow_p=False),
             dict(alpha=0.0, ap=1.0, mu=4.0, H=1.0, allow_p=False), dict(alpha=0.0, ap=1.0, mu=4.0, H=0.0, allow_p=False)]
    for kw in rows1:
        for dt in [0.1, 0.05, 0.025]:
            J.append(('(1)', kw, dt, 14.0, 7.0, False))
    por = [dict(alpha=0.3, ap=0.7, mu=0.5, lam=0.0, H=0.0), dict(alpha=0.3, ap=0.7, mu=1.0, lam=0.0, H=0.5),
           dict(alpha=0.3, ap=0.7, mu=2.0, lam=0.5, H=0.0), dict(alpha=0.3, ap=0.7, mu=2.0, lam=0.5, H=1.0)]
    for kw in por:
        J.append(('(2)', kw, 0.025, 13.0, 7.0, False))
    # (3) scan sample
    rows = list(csv.DictReader(open(os.path.join(C2, 'out', 'scan_compare.csv'))))
    rng = np.random.default_rng(5)
    idx_bigH = [i for i, r in enumerate(rows) if float(r['H']) >= 2]
    idx_rest = [i for i in range(len(rows)) if float(rows[i]['H']) < 2]
    pick = sorted(set(list(rng.choice(idx_bigH, 10, replace=False)) + list(rng.choice(idx_rest, 10, replace=False))))
    for i in pick:
        r = rows[i]
        kw = dict(alpha=float(r['alpha']), ap=float(r['ap']), mu=float(r['mu']), lam=float(r['lam']),
                  H=float(r['H']), tau=float(r['tau']), allow_p=(r.get('allow_p', '') != 'False'))
        J.append((f"(3) row {i} csv={float(r['CR'])!r}", kw, 0.1, 14.0, 7.0, True))
    with Pool(4) as p:
        res = p.map(job, J, chunksize=1)
    log("(1) scan rows with exact-LB > 0.035 that fit none of the three kinds named in the write-up (kind D of analyze_scan.py, all 5 rows)")
    for tag, kw, dt, cr, plan in [x for x in res if x[0] == '(1)']:
        P = Params(**kw)
        lb = lb_total(P)[0]
        cf = rrl_closed(kw['mu'], kw['H'], kw['alpha']) if (not kw.get('allow_p', True) and (kw['H'] == 0 or kw['mu'] <= 2)) else float('nan')
        log(f"   {kw} dt={dt}: exact {cr:.4f}  family LB {lb:.4f}  RRL closed form {cf:.4f}  exact-LB {cr - lb:+.4f}")
    log("(2) Table PoR cells at dt=0.025 (write-up: bound / exact dt=0.05)")
    for tag, kw, dt, cr, plan in [x for x in res if x[0] == '(2)']:
        lb = lb_total(Params(**kw))[0]
        log(f"   {kw}: exact(dt=0.025) {cr:.4f}  family bound {lb:.4f}  diff {cr - lb:+.4f}  plan {plan}")
    log("(3) re-solve of sampled scan rows (dt=0.1, T=14, Rmax=7, full plans) vs out/scan_compare.csv")
    nm = 0
    for tag, kw, dt, cr, plan in [x for x in res if x[0].startswith('(3)')]:
        old = float(tag.split('csv=')[1])
        nm += abs(old - cr) > 1e-6
        log(f"   {'MISMATCH' if abs(old - cr) > 1e-6 else 'ok'} {tag.split(' csv=')[0]} csv={old:.6f} rerun={cr:.6f} {kw}")
    log(f"   mismatches: {nm}")
    open(os.path.join(HERE, 'out', 'model_grid_check.txt'), 'w').write('\n'.join(lines) + '\n')
