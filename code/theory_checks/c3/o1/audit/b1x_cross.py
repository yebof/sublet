"""Audit b1x: cross-check of the independent solver in b1 against o1/pomdp.py on the H = 0
settings reported in o1/out/o1_lb.txt (C).  Output: out/b1x_cross.txt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
from b1_bayes_info import safe_site_all, bayes
from fam import Fam, safe_site_schedule
from pomdp import best_response


def main():
    L = ['b1x: independent solver (b1) vs o1/pomdp.py, I1 narrow and I2',
         'm rho tau H k Phi  b1_I1    pomdp_I1  b1_I2    pomdp_I2']
    for (m, rho, tau, H, k, Phi) in [(3, 8, 1, 0, 3, 2), (3, 32, 1, 0, 3, 3), (4, 8, 1, 0, 3, 2), (3, 8, 2, 1, 2, 2)]:
        F = Fam(m, rho, tau, H, T=k * (tau + H) * Phi)
        oms, seqs = safe_site_all(m, k, F.D, Phi)
        a1, _ = bayes(m, tau, H, F.T, F.beta, F.a, F.q, oms, 'I1n')
        a2, _ = bayes(m, tau, H, F.T, F.beta, F.a, F.q, oms, 'I2')
        po = [safe_site_schedule(F, k, Phi, None, S=S)[0] for S in seqs]
        p1, _ = best_response(F, po, 'I1')
        p2, _ = best_response(F, po, 'I2')
        L.append(f'{m} {rho:<3} {tau}   {H} {k} {Phi}    {a1:8.3f} {p1:8.3f}  {a2:8.3f} {p2:8.3f}')
    txt = '\n'.join(L)
    print(txt)
    open(os.path.join(HERE, 'out', 'b1x_cross.txt'), 'w').write(txt + '\n')


if __name__ == '__main__':
    main()
