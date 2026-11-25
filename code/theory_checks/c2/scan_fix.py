"""Recompute scan rows whose optimal threshold was within H+1 of Rmax (truncation artifact fixed in
det_game.solve_det: thresholds are now capped at Rmax - H - 1).  Patches out/scan_compare.csv."""
import csv, re
from model import Params
from det_game import solve_det
from scan_compare import DT, T, RMAX
rows = list(csv.DictReader(open('out/scan_compare.csv')))
keys = list(rows[0].keys())
for r in rows:
    m = re.match(r"\('(\w)'; ([0-9.]+)", r['plan'])
    if m and float(m.group(2)) > RMAX - float(r['H']) - 1 - 1e-9:
        P = Params(alpha=float(r['alpha']), ap=float(r['ap']), mu=float(r['mu']), lam=float(r['lam']),
                   H=float(r['H']), tau=float(r['tau']), allow_p=(r.get('allow_p', '') != 'False'))
        res = solve_det(P, dt=DT, T=T, Rmax=RMAX, return_detail=True)
        print('fixed', {k: r[k] for k in ['alpha', 'ap', 'mu', 'lam', 'H']}, r['CR'], '->', res['CR'], res['plan'])
        r['CR'] = res['CR']; r['plan'] = str(res['plan']).replace(',', ';')
        r['CRins_cls'] = res['CR_ins_class']; r['CRreact_cls'] = res['CR_react_class']
with open('out/scan_compare.csv', 'w') as f:
    f.write(','.join(keys) + '\n')
    for r in rows:
        f.write(','.join(str(r[k]) for k in keys) + '\n')
