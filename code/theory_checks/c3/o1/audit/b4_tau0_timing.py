"""Audit b4 (O1-C, timing convention).  O1-C's ALG side says: on the i.i.d. step distribution,
every algorithm with ANY feedback has E[N+F] >= pU, because "the steps after the purchase are
independent of everything observed at purchase time".  With tau >= 1 this is right.  With
tau = 0 (allowed by the model, D = tau + H >= 1) and the within-slot order used by the
project's scripts (observe the announcements of slot t, then decide at t), a full-feedback
algorithm buys at a step slot after seeing which sites were hit there, so its lease skips one
draw.  Policy 'dodge': hold one lease; at its death buy at a uniformly random site NOT announced
at the current slot (any site if all were hit).  Lease semantics as in fam.py: a lease bought at
s is announced at the first r in R_l with r >= s + tau (r = s allowed when tau = 0).
Compare E[N]/U with p, and E[ALG]/E[OPT] with LB_C(p).  Output: out/b4_tau0_timing.txt
"""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from fam import Fam, opt_dp, iid_step_schedule

OUT = os.path.join(HERE, 'out')


def mu_max_geom(m, p):
    s, g = 0.0, 0
    while True:
        term = 1.0 - (1.0 - (1.0 - p) ** g) ** m
        s += term
        g += 1
        if term < 1e-13 and g > 5:
            return s


def dodge(F, om, rng, see_current):
    """see_current: observe slot t's announcements before deciding at t (scripts' order)."""
    T = F.T
    sets = [set(map(int, o)) for o in om]
    t, cost, n = 0, 0.0, 0
    while t < T:
        cand = [l for l in range(F.m) if not (see_current and t in sets[l])] or list(range(F.m))
        l = int(cand[rng.integers(len(cand))])
        d = F.death(om, l, t)
        cost += F.lease_cost(t, min(d, T))
        n += 1
        t = d
    return cost, n


def main():
    os.makedirs(OUT, exist_ok=True)
    L = ['b4: O1-C ALG-side bound E[N+F] >= pU under tau = 0 vs tau = 1 (policy "dodge", full feedback)',
         'm  rho tau H  p    U    E[N]/U (see t first)  E[N]/U (decide first)  p     E[ALG]/E[OPT] (see first)  LB_C(p) asym  finite (beta p U + aT)/E[OPT]']
    rng = np.random.default_rng(3)
    for (m, rho, tau, H, p) in [(8, 32, 0, 1, 0.5), (8, 32, 0, 2, 0.5), (16, 32, 0, 1, 0.5), (8, 32, 1, 0, 0.5), (8, 32, 1, 1, 0.5)]:
        U = 150
        F = Fam(m, rho, tau, H, T=U * (tau + H))
        ns, nd, ca, co = [], [], [], []
        for _ in range(150):
            om = iid_step_schedule(F, p, U, rng)
            c1, n1 = dodge(F, om, rng, True)
            c2, n2 = dodge(F, om, rng, False)
            ns.append(n1); nd.append(n2); ca.append(c1); co.append(opt_dp(F, om)[0])
        mu = mu_max_geom(m, p)
        lbc = ((rho - 1) * p + 1) / ((rho - 1) / mu + 1)
        fin = (F.beta * p * U + F.a * F.T) / np.mean(co)
        L.append(f"{m:<2} {rho:<3} {tau}   {H}  {p:.1f}  {U}  {np.mean(ns)/U:.3f}                 {np.mean(nd)/U:.3f}                   {p:.2f}  "
                 f"{np.mean(ca)/np.mean(co):.3f}                      {lbc:.3f}         {fin:.3f}")
    L.append('Reading: with tau = 0 and observe-then-decide, E[N]/U ~ p/(1+p) < p, and the ratio falls below the finite-U and asymptotic')
    L.append('value of LB_C(p) claimed for "any feedback". With tau >= 1 seeing slot t does not help (E[N]/U ~ p).')
    txt = '\n'.join(L)
    print(txt)
    open(os.path.join(OUT, 'b4_tau0_timing.txt'), 'w').write(txt + '\n')


if __name__ == '__main__':
    main()
