"""Summarize out/scan_compare.csv: decomposition checks and exact-vs-family-LB gaps.
Output: out/scan_summary.txt, out/scan_with_lb.csv"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
import csv
import numpy as np
from multiprocessing import Pool
from model import Params
from families import lb_total

GRID_TOL = 0.035   # exact solver on dt=0.1 grid: thresholds off by <= dt/2 (see table_conv)


def to_params(r):
    return Params(alpha=float(r['alpha']), ap=float(r['ap']), mu=float(r['mu']), lam=float(r['lam']),
                  H=float(r['H']), tau=float(r['tau']), allow_p=(r.get('allow_p', '') != 'False'))


def lb(r):
    return lb_total(to_params(r))


if __name__ == '__main__':
    import sys
    R = list(csv.DictReader(open('out/scan_compare.csv')))
    if '--reuse' in sys.argv:      # reuse LB values computed in a previous run
        prev = list(csv.DictReader(open('out/scan_with_lb.csv')))
        L = [(float(p['LB']), float(p['LBreact']), None) for p in prev]
    else:
        with Pool(int(os.environ.get('NPROC', '6'))) as pool:
            L = pool.map(lb, R, chunksize=8)
    out = []
    def log(s):
        print(s); out.append(s)
    log(f"rows: {len(R)}")
    menu = [i for i, r in enumerate(R) if r.get('allow_p', '') != 'False']
    d = [float(R[i]['CRins_cls']) - float(R[i]['CRins_formula']) for i in menu if float(R[i]['alpha']) > 0]
    log(f"insurance class (best plan committing to p before notice) minus max(2-a, ap/a): min {min(d):+.4f} max {max(d):+.4f}")
    nup = sum(1 for r in R if r['plan'].startswith("('r'") and not r['plan'].endswith('inf)'))
    log(f"rows where a planned pre-notice upgrade r->p is the unique optimum: {nup}")
    gaps = []
    for r, (lbt, lbr, s) in zip(R, L):
        r['LB'] = lbt; r['LBreact'] = lbr
        gaps.append(float(r['CR']) - lbt)
    gaps = np.array(gaps)
    log(f"exact - LB: min {gaps.min():+.4f}, median {np.median(gaps):+.4f}, max {gaps.max():+.4f}")
    log(f"rows with exact - LB < -{GRID_TOL} (LB violated beyond grid error): {(gaps < -GRID_TOL).sum()}")
    big = [(g, r) for g, r in zip(gaps, R) if g > GRID_TOL]
    log(f"rows with exact - LB > {GRID_TOL} (families not tight): {len(big)}")
    def kind(r):
        al, ap, mu, lam, H = (float(r[k]) for k in ('alpha', 'ap', 'mu', 'lam', 'H'))
        menu = r.get('allow_p', '') != 'False'
        if al == 0 and lam > 0 and mu == 4 and menu:
            return 'B: alpha=0, lam>0, mu=4'
        if mu == 4 and H >= 2:
            return 'A: mu=4, long notice (known window)'
        if al == 0.2 and ap == 0.4:
            return 'C: middle price band'
        return 'D: other (alpha=0, H<=1; grid error, audit/out/model_grid_check.txt)'
    for g, r in sorted(big, key=lambda t: -t[0]):
        log(f"  gap {g:+.4f}: alpha={r['alpha']} ap={r['ap']} mu={r['mu']} lam={r['lam']} H={r['H']} tau={r['tau']} "
            f"allow_p={r.get('allow_p','')} CR={float(r['CR']):.4f} LB={r['LB']:.4f} plan={r['plan']}  [{kind(r)}]")
    for k in sorted(set(kind(r) for _, r in big)):
        log(f"  kind {k}: {sum(1 for _, r in big if kind(r) == k)} rows")
    t0 = np.array([float(r['tau']) == 0 for r in R])
    log(f"tau = 0 rows only: {int(t0.sum())}; exact - LB: min {gaps[t0].min():+.4f}, median {np.median(gaps[t0]):+.4f}; "
        f"rows with exact - LB > {GRID_TOL}: {int((gaps[t0] > GRID_TOL).sum())}; "
        f"of these not of kind D: {sum(1 for g, r in big if float(r['tau']) == 0 and not kind(r).startswith('D'))}")
    # tau vs notice
    log("guaranteed period vs notice: CR(H=0,tau=1) vs CR(H=1,tau=0) and CR(H=0,tau=0)")
    idx = {(r['alpha'], r['ap'], r['mu'], r['lam'], float(r['H']), float(r['tau'])): r for r in R if r.get('allow_p', '') != 'False'}
    npair = neq = 0
    for (al, ap, mu, lam, H, tau), r in sorted(idx.items()):
        if H == 0 and tau == 1.0:
            npair += 1
            neq += abs(float(r['CR']) - float(idx[(al, ap, mu, lam, 1.0, 0.0)]['CR'])) < 1e-6
            r1 = idx.get((al, ap, mu, lam, 1.0, 0.0)); r0 = idx.get((al, ap, mu, lam, 0.0, 0.0))
            log(f"  a={al} ap={ap} mu={mu} lam={lam}: tau=1,H=0 -> {float(r['CR']):.4f};  tau=0,H=1 -> {float(r1['CR']):.4f};  tau=0,H=0 -> {float(r0['CR']):.4f}")
    log(f"  combinations: {npair}; equal (|diff|<1e-6) CR(H=0,tau=1) and CR(H=1,tau=0): {neq}")
    open('out/scan_summary.txt', 'w').write('\n'.join(out) + '\n')
    keys = list(R[0].keys())
    with open('out/scan_with_lb.csv', 'w') as f:
        f.write(','.join(keys) + '\n')
        for r in R:
            f.write(','.join(str(r[k]) for k in keys) + '\n')
