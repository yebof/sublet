"""C3 checks: LP chain and the primal-dual guarantees (Theorems 1-2 of
design/theory/c3_c4_c5_general.md).

For each instance:
  OPT_eager (MILP, any start), LP_trunc, LP_aligned;
  FracPD: P, dual sum, dual-feasibility ratio (must be <= 1), P/LP_aligned vs 2 ln(d+1);
  rounding (r = ceil(2 ln N), 40 seeds): mean analysed-rule cost vs r*P + OPT_eager and
  vs (4 r ln(mK+2) + 1) OPT_eager; practical rule; heuristic r = 1.
Families: 'rand' (metric, all sites feasible), 'slo' (SLO-restricted), 'setcover'
(delta in {0, inf}, one long contract: online set cover embedding), 'spiky' (short
activity bursts).
Output: out/c3_upper.json, out/c3_upper.txt
"""
import os, sys, json, math
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
import multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import random_instance, opt_eager, lp_trunc, lp_aligned, Instance
from pd import FracPD, round_pd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
SEEDS = 40


def setcover_instance(rng, T=24, m=6, n=10):
    tau = np.array([T]); H = np.array([0])
    a = np.full((m, 1), 0.05)
    beta = rng.uniform(2, 6, size=(1, m))
    feas = rng.random((n, m)) < 0.35
    for c in range(n):
        if not feas[c].any():
            feas[c, rng.integers(m)] = True
    delta = np.where(feas, 0.0, np.inf)
    active = np.zeros((n, T), dtype=bool)
    for c in range(n):  # each client appears for a single slot (set-cover element)
        active[c, rng.integers(T)] = True
    return Instance(T=T, tau=tau, H=H, a=a, beta=beta, g=np.array([1]), q=20.0,
                    cl_llm=np.zeros(n, dtype=int), delta=delta, active=active)


def make(fam, seed):
    rng = np.random.default_rng(1000 + seed)
    if fam == 'rand':
        return random_instance(rng, T=36, m=4, J=2, n=8)
    if fam == 'slo':
        return random_instance(rng, T=36, m=5, J=2, n=10, slo=0.45)
    if fam == 'setcover':
        return setcover_instance(rng)
    if fam == 'spiky':
        return random_instance(rng, T=36, m=4, J=1, n=10, on_mean=2, off_mean=8)
    if fam == 'big':
        return random_instance(rng, T=48, m=6, J=2, n=12, slo=0.6)
    raise ValueError(fam)


def run(args):
    fam, seed = args
    I = make(fam, seed)
    oe = opt_eager(I)
    lt = lp_trunc(I)
    la = lp_aligned(I)
    pd = FracPD(I).run()
    P = pd.primal()
    d = pd.d
    rr = [round_pd(pd, np.random.default_rng(s)) for s in range(SEEDS)]
    r = rr[0]['r']
    r1 = [round_pd(pd, np.random.default_rng(s), r=1) for s in range(SEEDS)]
    an = float(np.mean([x['cost_an'] for x in rr]))
    pr = float(np.mean([x['cost_pr'] for x in rr]))
    h1 = float(np.mean([x['cost_pr'] for x in r1]))
    OPT = oe['fun']
    OPTlb = oe['lb']
    rec = dict(fam=fam, seed=seed, m=I.m, K=I.K, J=I.J, n_el=len(I.elements()), d=d, r=r,
               rho=I.rho(), OPT_eager=OPT, OPT_lb=OPTlb, mip_status=oe['status'],
               LP_trunc=lt['fun'], LP_aligned=la['fun'], P=P, dual=pd.dual,
               dualfeas=pd.check_dual_feasible(), iter_hits=pd.max_iter_hit,
               P_over_LPal=P / la['fun'], bound_frac=2 * math.log(d + 1),
               P_over_2dual=P / (2 * pd.dual),
               ALG_an=an, ALG_pr=pr, ALG_r1=h1,
               chk_an_vs_rP=an / (r * P + OPT),
               bound_int=4 * r * math.log(I.m * I.K + 2) + 1,
               ratio_an=an / OPTlb, ratio_pr=pr / OPTlb, ratio_r1=h1 / OPTlb,
               lp_valid=lt['fun'] <= OPT + 1e-6, align2=la['fun'] <= 2 * lt['fun'] + 1e-6)
    return rec


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    jobs = [(f, s) for f in ['rand', 'slo', 'setcover', 'spiky', 'big'] for s in range(12)]
    with mp.get_context('spawn').Pool(5) as p:
        recs = p.map(run, jobs)
    json.dump(recs, open(os.path.join(OUT, 'c3_upper.json'), 'w'), indent=1)
    lines = []
    hdr = ('fam       #  P/LPal(max) bound  dualfeas(max) P/2Y(max) LPt<=OPT LPal<=2LPt '
           'an/(rP+OPT)(max) ALGan/OPT(mean,max) bound_int  ALGpr/OPT(mean)  r=1/OPT(mean,max)')
    lines.append(hdr)
    for f in ['rand', 'slo', 'setcover', 'spiky', 'big']:
        R = [x for x in recs if x['fam'] == f]
        g = lambda k: np.array([x[k] for x in R])
        lines.append(f"{f:9s} {len(R):2d}  {g('P_over_LPal').max():.3f}     {g('bound_frac').max():.2f}   "
                     f"{g('dualfeas').max():.3f}         {g('P_over_2dual').max():.3f}     "
                     f"{all(g('lp_valid'))}     {all(g('align2'))}       {g('chk_an_vs_rP').max():.3f}"
                     f"            {g('ratio_an').mean():.2f},{g('ratio_an').max():.2f}        "
                     f"{g('bound_int').max():.1f}     {g('ratio_pr').mean():.2f}            "
                     f"{g('ratio_r1').mean():.2f},{g('ratio_r1').max():.2f}")
        lines.append(f"          frac P/OPT_eager mean {np.mean(g('P')/g('OPT_lb')):.3f} max {np.max(g('P')/g('OPT_lb')):.3f}; "
                     f"LPal/LPt max {np.max(g('LP_aligned')/g('LP_trunc')):.3f}; OPT/LPt max {np.max(g('OPT_eager')/g('LP_trunc')):.3f}; "
                     f"rho range [{g('rho').min():.2f},{g('rho').max():.2f}]; mip_status {set(g('mip_status'))}; iter_hits {g('iter_hits').sum()}")
    txt = '\n'.join(lines)
    print(txt)
    open(os.path.join(OUT, 'c3_upper.txt'), 'w').write(txt + '\n')
