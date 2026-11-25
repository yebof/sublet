"""Audit: Propositions 5-7 need a lower bound on q (and P5 needs tau_2 = T), which the
statements omit. Small-q instances where the stated bounds fail."""
import os, sys
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from core import Instance, opt_eager, any_start_columns, solve_fl

def single(T, contracts, beta, a_list, q):
    tau = np.array([c[0] for c in contracts]); H = np.array([c[1] for c in contracts])
    return Instance(T=T, tau=tau, H=H, a=np.array([a_list]), beta=np.array([[beta]]),
                    g=np.array([1]), q=q, cl_llm=np.array([0]), delta=np.array([[0.0]]),
                    active=np.ones((1, T), dtype=bool))
T = 48
# P5: revocable (1,1,a1=1), protected (T,0,a2=1.3), beta=14 -> rho1=8, claim ~ (T/2)(16)/(14+1.3T)
for q in [1e4, 1.0]:
    I = single(T, [(1, 1), (T, 0)], 14.0, [1.0, 1.3], q)
    full = opt_eager(I)['fun']; rev = opt_eager(I.subset(contracts=[0]))['fun']
    print(f"P5 q={q}: revocable-only/OPT = {rev/full:.3f}; claimed lower bound (T/D1)(b+a1D1)/(b+a2T) = {(T/2)*16/(14+1.3*T):.3f}")
# P5 with tau2 = 2T (prepaid window longer than horizon): OPT <= beta + a2 T fails
I = single(T, [(1, 1), (2 * T, 0)], 14.0, [1.0, 1.3], 1e4)
print(f"P5 tau2=2T: OPT_eager = {opt_eager(I)['fun']:.1f} vs claimed OPT <= beta+a2T = {14+1.3*T:.1f}")
# P6: notice-oblivious, tau=2, H=2, beta=20, a=1 -> C=24
for q in [1e4, 1.0]:
    I = single(T, [(2, 2)], 20.0, [1.0], q)
    cols = [(l, j, k, s, s, min(s + int(I.tau[k]), I.T), C) for (l, j, k, s, st, en, C) in any_start_columns(I)]
    no = solve_fl(I, cols, True)['fun']
    print(f"P6 q={q}: notice-oblivious/OPT_eager = {no/opt_eager(I)['fun']:.3f}; claimed -> D/tau = 2")
# P7: b borrowers, protected contract, small q
b = 4
for q in [1e3, 0.2]:
    I = Instance(T=24, tau=np.array([24]), H=np.array([0]), a=np.array([[1.0]]), beta=np.array([[10.0]]),
                 g=np.array([1]), q=q, cl_llm=np.zeros(b, dtype=int), delta=np.zeros((b, 1)),
                 active=np.ones((b, 24), dtype=bool), owner=np.arange(b))
    sh = opt_eager(I)['fun']; si = sum(opt_eager(I.subset(clients=[c]))['fun'] for c in range(b))
    print(f"P7 q={q}: siloed/shared = {si/sh:.3f}; claimed = b = {b}")
