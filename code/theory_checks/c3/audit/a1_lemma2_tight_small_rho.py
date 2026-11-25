"""Audit: Lemma 2 tightness of the factor 2 when rho < 2 (the draft only cites rho >= 2).
Instance: one site, one contract (tau=D, H=0), client active on [0, D+1) only, q huge.
OPT(sigma, no reclaims) = beta + a(D+1); OPT_eager = 2(beta + aD). Ratio -> 2 as D grows."""
import os, sys
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from core import Instance, opt_eager, opt_omega

for rho in [1.2, 1.5, 1.9]:
    for D in [4, 10, 25]:
        T = D + 3
        beta = (rho - 1) * 1.0 * D
        act = np.zeros((1, T), dtype=bool); act[0, :D + 1] = True
        I = Instance(T=T, tau=np.array([D]), H=np.array([0]), a=np.array([[1.0]]),
                     beta=np.array([[beta]]), g=np.array([1]), q=1e4, cl_llm=np.array([0]),
                     delta=np.array([[0.0]]), active=act)
        e = opt_eager(I)['fun']
        o = opt_omega(I, [np.array([], dtype=int)])['fun']
        print(f"rho={rho} D={D}: OPT_eager={e:.2f} OPT(no reclaim)={o:.2f} ratio={e/o:.3f} "
              f"formula 2(rho)/(rho+1/D)={2*rho/(rho+1/D):.3f}")
