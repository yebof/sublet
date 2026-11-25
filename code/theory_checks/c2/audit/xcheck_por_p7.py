"""Audit (C2): lower-bound parts of P7 / P8 (Table PoR, P7 table).  Rigorous family bound of
necessity_lb.lb_all (F1, F2 and the known-window family F3, interval bounds over the algorithm,
min with CR_ins), compared with the 'family bound' column of Table PoR and the P7 formula values.
Output: audit/out/xcheck_por_p7.txt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from necessity_lb import lb_all
L = []
L.append("Table PoR (a=0.3, ap=0.7, beta=1): rigorous LB incl. F3 at H = 0, .25, .5, .75, 1, 1.5, 2, 3")
doc = {(0.5, 0.5): [1.8241, 1.7386, 1.7, 1.7, 1.7, 1.7, 1.7, 1.7], (1, 0.5): [1.9207, 1.8479, 1.7702, 1.7, 1.7, 1.7, 1.7, 1.7],
       (2, 0.0): [1.9207, 1.8479, 1.7702, 1.7, 1.7, 1.7, 1.7, 1.7], (2, 0.5): [2.0674, 2.0104, 1.9501, 1.8865, 1.8198, 1.7, 1.7, 1.7]}
for (mu, lam), dv in doc.items():
    v = [lb_all(dict(b=1.0, a=0.3, ap=0.7, mu=mu, lam=lam, rrl=False), H)[0] for H in [0, 0.25, 0.5, 0.75, 1, 1.5, 2, 3]]
    L.append(f"mu={mu} lam={lam}: rigorous " + ' '.join(f'{x:.4f}' for x in v) + " | doc " + ' '.join(f'{x:.4f}' for x in dv)
             + f" | max(doc - rigorous) = {max(d - x for d, x in zip(dv, v)):+.4f}")
L.append("P7 (a=0, ap=0.5, H=0): RRL | menu lam=0 | menu lam=0.5   (doc formula: 2.2247/2.4142/2.7321/3.2361 RRL; menu lam=0.5: 2.2247/2.4142/2.7321/3.5000)")
for mu in [0.5, 1, 2, 4]:
    v = [lb_all(dict(b=1.0, a=0.0, ap=0.5, mu=mu, lam=lam, rrl=rrl), 0.0)[0] for lam, rrl in [(0.5, True), (0.0, False), (0.5, False)]]
    L.append(f"mu={mu}: " + ' | '.join(f'{x:.4f}' for x in v))
open(os.path.join(HERE, 'out', 'xcheck_por_p7.txt'), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))
