"""Benchmark checks (Lemma 1 / Lemma 3 of design/theory/c3_c4_c5_general.md).

(a) Counterexample: LP_trunc is NOT a lower bound on OPT(sigma, omega) when the lender
    is benign (no reclaims): one site, one always-active client, one contract.
(b) Conversion lemma: OPT_eager <= max(2, rho) * OPT(sigma, omega) for every omega
    (random per-site schedules at several rates; rate 1.0 = announce every slot, which
    must reproduce OPT_eager exactly).
(c) Empirical ratios of the rounded PD (renewal heuristic, real cost under omega) to
    OPT(sigma, omega).
Output: out/c3_benchmark.json, out/c3_benchmark.txt
"""
import os, sys, json
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
import multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import Instance, random_instance, opt_eager, lp_trunc, opt_omega, random_omega
from pd import FracPD, round_pd, real_cost_renew, service_cost_given_open

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
RATES = [0.0, 0.02, 0.1, 0.3, 1.0]


def single_site(beta, T=60, tau=2, H=1, a=1.0):
    return Instance(T=T, tau=np.array([tau]), H=np.array([H]), a=np.array([[a]]),
                    beta=np.array([[beta]]), g=np.array([1]), q=1e3,
                    cl_llm=np.array([0]), delta=np.array([[0.0]]),
                    active=np.ones((1, T), dtype=bool))


def part_a():
    rows = []
    for rho in [1.5, 2, 4, 8, 16]:
        L = 3
        beta = (rho - 1) * L
        I = single_site(beta)
        lt = lp_trunc(I)['fun']
        oe = opt_eager(I)['fun']
        on = opt_omega(I, [np.array([], dtype=int)])['fun']
        rows.append(dict(rho=rho, LP_trunc=lt, OPT_eager=oe, OPT_none=on,
                         LP_over_OPTnone=lt / on, OPTeager_over_OPTnone=oe / on,
                         bound=max(2, rho)))
    return rows


def run_b(seed):
    rng = np.random.default_rng(5000 + seed)
    I = random_instance(rng, T=36, m=4, J=2, n=8, slo=0.7 if seed % 2 else None)
    oe = opt_eager(I)
    pd = FracPD(I).run()
    rnd = [round_pd(pd, np.random.default_rng(s)) for s in range(10)]
    rnd1 = [round_pd(pd, np.random.default_rng(s), r=1) for s in range(10)]
    for x in rnd + rnd1:
        x['serv'] = float(service_cost_given_open(I, x['opened']).sum())
        opencost = sum(I.C(F[1], F[2], F[3]) for F in x['opened'])
        assert opencost + x['serv'] <= x['cost_pr'] + 1e-6  # end-of-slot routing <= sequential
    out = dict(seed=seed, rho=I.rho(), OPT_eager=oe['fun'], per_rate=[])
    for rate in RATES:
        om = random_omega(np.random.default_rng(7000 + seed), I, rate) if rate < 1 else \
            [np.arange(I.T)] * I.m
        oo = opt_omega(I, om, time_limit=120)
        real = [real_cost_renew(I, x['opened'], om)[0] + x['serv'] for x in rnd]
        real1 = [real_cost_renew(I, x['opened'], om)[0] + x['serv'] for x in rnd1]
        acc = [x['cost_pr'] for x in rnd]
        acc1 = [x['cost_pr'] for x in rnd1]
        out['per_rate'].append(dict(
            rate=rate, OPT_omega=oo['fun'], OPT_omega_lb=oo['lb'], status=oo['status'],
            eager_over_omega=oe['fun'] / oo['lb'], bound=max(2, I.rho()),
            ALG_renew=float(np.mean(real)), ALG_acc=float(np.mean(acc)),
            ALG_renew_r1=float(np.mean(real1)), ALG_acc_r1=float(np.mean(acc1)),
            renew_le_2acc=bool(all(rv <= 2 * av + 1e-6 for rv, av in zip(real + real1, acc + acc1)))))
    return out


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    with mp.get_context('spawn').Pool(5) as p:
        B = p.map(run_b, range(10))
    A = part_a()
    json.dump(dict(a=A, b=B), open(os.path.join(OUT, 'c3_benchmark.json'), 'w'), indent=1)
    L = ['(a) single site, always-active client, tau=2,H=1,a=1, T=60, no reclaims',
         ' rho   LP_trunc  OPT_eager  OPT_none  LP/OPT_none  OPTeager/OPT_none  max(2,rho)']
    for r in A:
        L.append(f" {r['rho']:4.1f}  {r['LP_trunc']:8.2f}  {r['OPT_eager']:8.2f}  {r['OPT_none']:8.2f}  "
                 f"{r['LP_over_OPTnone']:8.3f}     {r['OPTeager_over_OPTnone']:8.3f}          {r['bound']:.1f}")
    L.append('(b,c) random instances T=36 m=4 J=2 n=8; 10 instances x 10 rounding seeds')
    L.append(' rate  OPTeager/OPTomega(max)  max(2,rho)(min)  status  ALGrenew/OPTomega(mean,max)  '
             'ALGacc/OPTomega(mean)  r=1: renew/OPTomega(mean,max)  renew<=2acc')
    for i, rate in enumerate(RATES):
        P = [b['per_rate'][i] for b in B]
        e = np.array([p['eager_over_omega'] for p in P])
        bd = np.array([p['bound'] for p in P])
        rr = np.array([p['ALG_renew'] / p['OPT_omega_lb'] for p in P])
        ra = np.array([p['ALG_acc'] / p['OPT_omega_lb'] for p in P])
        r1 = np.array([p['ALG_renew_r1'] / p['OPT_omega_lb'] for p in P])
        L.append(f" {rate:4.2f}  {e.max():.3f} (all<=bound: {bool((e <= bd + 1e-9).all())})        {bd.min():.2f}"
                 f"        {set(p['status'] for p in P)}     {rr.mean():.2f},{rr.max():.2f}                  "
                 f"{ra.mean():.2f}                {r1.mean():.2f},{r1.max():.2f}                    "
                 f"{all(p['renew_le_2acc'] for p in P)}")
    eq = [abs(b['per_rate'][-1]['OPT_omega'] - b['OPT_eager']) < 1e-6 for b in B]
    L.append(f" check: rate=1.0 (announce every slot) reproduces OPT_eager exactly: {all(eq)}")
    txt = '\n'.join(L)
    print(txt)
    open(os.path.join(OUT, 'c3_benchmark.txt'), 'w').write(txt + '\n')
