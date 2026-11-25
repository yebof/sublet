"""C4 checks (Theorem 4, Propositions 5-8 of design/theory/c3_c4_c5_general.md).

(a) cat-and-mouse adaptive lender, m sites, one always-active client, one contract:
    measured ALG/OPT(sigma,omega) for 'stay', 'round-robin' and the rounded PD with
    renewal, vs the finite-T bound LB_T and the asymptotic rho*m/(m+rho-1).
(b) revocable-only: offline best revocable-only cost / OPT on the announce-every-slot
    instance vs a1*rho1/a2 (and finite-T formula); random instances.
(c) notice-oblivious (lease k usable only on [s, s+tau_k)) vs OPT_eager; vs L/tau.
(d) siloed per-borrower planning vs shared: constructed (ratio b) and random.
(e) parking-permit embedding: OPT_eager (MILP) == independent parking-permit DP.
Output: out/c4_lower.json, out/c4_lower.txt
"""
import os, sys, json, math
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
import multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import (Instance, random_instance, opt_eager, opt_omega, solve_fl,
                  any_start_columns)
from pd import FracPD, round_pd, real_cost_renew, service_cost_given_open

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')


def cm_instance(m, rho, T=48, tau=2, H=1, a=1.0):
    L = tau + H
    beta = (rho - 1) * a * L
    return Instance(T=T, tau=np.array([tau]), H=np.array([H]), a=np.full((m, 1), a),
                    beta=np.full((1, m), beta), g=np.array([1]), q=beta + a * L + 1,
                    cl_llm=np.array([0]), delta=np.zeros((1, m)),
                    active=np.ones((1, T), dtype=bool))


def cm_job(args):
    m, rho = args
    I = cm_instance(m, rho)
    T, L, tau = I.T, int(I.L[0]), int(I.tau[0])
    beta, a = float(I.beta[0, 0]), float(I.a[0, 0])
    nA = math.ceil(T / L)
    LB_T = (nA * beta + a * T) / ((nA / m + 1) * beta + a * (T + L))
    asym = rho * m / (m + rho - 1)
    res = dict(m=m, rho=rho, LB_T=LB_T, asym=asym)
    for name in ['stay', 'rr']:
        om = [[] for _ in range(m)]
        for i in range(nA):
            site = 0 if name == 'stay' else i % m
            om[site].append(i * L + tau)
        om = [np.array(sorted(o), dtype=int) for o in om]
        alg = nA * I.C(0, 0, 0)
        oo = opt_omega(I, om)
        res[name] = alg / oo['fun']
    pd = FracPD(I).run()
    vals = {}
    for tag, rr in [('pd_r1', 1), ('pd_rth', None)]:
        ratios = []
        for s in range(4):
            x = round_pd(pd, np.random.default_rng(s), r=rr)
            lease, om = real_cost_renew(I, x['opened'], None, adversary=True)
            serv = float(service_cost_given_open(I, x['opened']).sum())
            oo = opt_omega(I, om)
            ratios.append((lease + serv) / oo['fun'])
        vals[tag] = float(np.mean(ratios))
        vals[tag + '_min'] = float(np.min(ratios))
    res.update(vals)
    return res


def single(T, contracts, beta, a_list):
    tau = np.array([c[0] for c in contracts]); H = np.array([c[1] for c in contracts])
    return Instance(T=T, tau=tau, H=H, a=np.array([a_list]), beta=np.array([[beta]]),
                    g=np.array([1]), q=1e4, cl_llm=np.array([0]), delta=np.array([[0.0]]),
                    active=np.ones((1, T), dtype=bool))


def part_b():
    rows = []
    T = 48
    for beta in [2, 6, 14, 30]:
        I = single(T, [(1, 1), (T, 0)], beta, [1.0, 1.3])
        full = opt_eager(I)['fun']
        rev = opt_eager(I.subset(contracts=[0]))['fun']
        rho1 = 1 + beta / 2.0
        pd = FracPD(I).run()
        alg = np.mean([round_pd(pd, np.random.default_rng(s), r=1)['cost_pr'] for s in range(10)])
        rows.append(dict(beta=beta, rho1=rho1, ratio=rev / full, formula_asym=1.0 * rho1 / 1.3,
                         formula_T=(T / 2) * (beta + 2) / (beta + 1.3 * T), pd_r1_ratio=alg / full,
                         frac_ratio=pd.primal() / full))
    return rows


def b_random(seed):
    rng = np.random.default_rng(9000 + seed)
    I = random_instance(rng, T=36, m=4, J=2, n=8)
    full = opt_eager(I)['fun']
    rev = opt_eager(I.subset(contracts=[0, 1]))['fun']
    spot = opt_eager(I.subset(contracts=[0]))['fun']
    return dict(seed=seed, rev_over_full=rev / full, spot_over_full=spot / full)


def notice_oblivious_opt(I):
    cols = [(l, j, k, s, s, min(s + int(I.tau[k]), I.T), C) for (l, j, k, s, st, en, C)
            in any_start_columns(I)]
    return solve_fl(I, cols, True)['fun']


def part_c():
    rows = []
    for H in [0, 1, 2, 4, 8]:
        I = single(48, [(2, H)], 20.0, [1.0])
        rows.append(dict(H=H, tau=2, ratio=notice_oblivious_opt(I) / opt_eager(I)['fun'],
                         L_over_tau=(2 + H) / 2))
    return rows


def c_random(seed):
    rng = np.random.default_rng(9100 + seed)
    I = random_instance(rng, T=36, m=4, J=2, n=8, contracts=[(1, 2, 1.0), (4, 4, 1.25), (12, 6, 1.6)])
    return dict(seed=seed, ratio=notice_oblivious_opt(I) / opt_eager(I)['fun'])


def part_d_constructed():
    rows = []
    for b in [1, 2, 4, 8, 16]:
        T = 24
        I = Instance(T=T, tau=np.array([T]), H=np.array([0]), a=np.array([[1.0]]),
                     beta=np.array([[10.0]]), g=np.array([1]), q=1e3,
                     cl_llm=np.zeros(b, dtype=int), delta=np.zeros((b, 1)),
                     active=np.ones((b, T), dtype=bool), owner=np.arange(b))
        shared = opt_eager(I)['fun']
        silo = sum(opt_eager(I.subset(clients=[c]))['fun'] for c in range(b))
        rows.append(dict(b=b, ratio=silo / shared))
    return rows


def d_random(args):
    seed, b = args
    rng = np.random.default_rng(9200 + seed)
    I = random_instance(rng, T=36, m=4, J=1, n=16, n_borrowers=b)
    shared = opt_eager(I)['fun']
    silo = 0.0
    for o in range(b):
        cl = np.nonzero(I.owner == o)[0]
        if len(cl):
            silo += opt_eager(I.subset(clients=cl))['fun']
    return dict(seed=seed, b=b, ratio=silo / shared)


def pp_dp(T, active, Ls, Cs, q):
    dp = np.zeros(T + 1)
    for t in range(1, T + 1):
        if not active[t - 1]:
            dp[t] = dp[t - 1]
            continue
        best = dp[t - 1] + q
        for L, C in zip(Ls, Cs):
            best = min(best, dp[max(0, t - L)] + C)
        dp[t] = best
    return dp[T]


def part_e():
    rows = []
    for seed in range(20):
        rng = np.random.default_rng(9300 + seed)
        T = 40
        contracts = [(1, 0), (3, 1), (10, 6)]
        a = [1.0, 0.8, 0.6]
        I = single(T, contracts, float(rng.uniform(1, 6)), a)
        I.q = float(rng.uniform(2, 8))
        I.active = (rng.random((1, T)) < rng.uniform(0.2, 0.8))
        Ls = list(I.L); Cs = [I.C(0, 0, k) for k in range(3)]
        rows.append(dict(seed=seed, milp=opt_eager(I)['fun'], dp=pp_dp(T, I.active[0], Ls, Cs, I.q)))
    return rows


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    ctx = mp.get_context('spawn')
    with ctx.Pool(5) as p:
        A = p.map(cm_job, [(m, rho) for m in [2, 3, 4, 6] for rho in [2, 4, 8, 16]])
        Br = p.map(b_random, range(10))
        Cr = p.map(c_random, range(10))
        Dr = p.map(d_random, [(s, b) for b in [2, 4, 8] for s in range(6)])
    B = part_b(); C = part_c(); D = part_d_constructed(); E = part_e()
    json.dump(dict(a=A, b=B, b_random=Br, c=C, c_random=Cr, d=D, d_random=Dr, e=E),
              open(os.path.join(OUT, 'c4_lower.json'), 'w'), indent=1)
    L = ['(a) cat-and-mouse (adaptive per-site lender), T=48, tau=2, H=1, a=1',
         '  m  rho   LB_T   rho*m/(m+rho-1)   stay   round-robin   PD(r=1) mean/min   PD(r=th) mean/min   all>=LB_T']
    for r in A:
        ok = min(r['stay'], r['rr'], r['pd_r1_min'], r['pd_rth_min']) >= r['LB_T'] - 1e-9
        L.append(f"  {r['m']}  {r['rho']:4.0f}  {r['LB_T']:.3f}   {r['asym']:.3f}           {r['stay']:.3f}  "
                 f"{r['rr']:.3f}         {r['pd_r1']:.3f}/{r['pd_r1_min']:.3f}      {r['pd_rth']:.3f}/{r['pd_rth_min']:.3f}       {ok}")
    L.append('(b) revocable-only vs full menu, announce every slot; revocable (1,1,a=1), protected (48,0,a=1.3)')
    L.append('  beta  rho1  revonly/OPT  finite-T formula  a1*rho1/a2  PD(r=1)/OPT  frac/OPT')
    for r in B:
        L.append(f"  {r['beta']:4.0f}  {r['rho1']:4.1f}  {r['ratio']:.3f}        {r['formula_T']:.3f}            "
                 f"{r['formula_asym']:.3f}       {r['pd_r1_ratio']:.3f}        {r['frac_ratio']:.3f}")
    rv = np.array([x['rev_over_full'] for x in Br]); sv = np.array([x['spot_over_full'] for x in Br])
    L.append(f"  random (T=36,m=4,J=2): without long contract OPT ratio mean {rv.mean():.3f} max {rv.max():.3f}; "
             f"spot-only mean {sv.mean():.3f} max {sv.max():.3f}")
    L.append('(c) notice-oblivious (uses lease only for tau) vs OPT_eager; single site, tau=2, beta=20, a=1, T=48')
    for r in C:
        L.append(f"  H={r['H']}  ratio {r['ratio']:.3f}  L/tau {r['L_over_tau']:.2f}")
    cr = np.array([x['ratio'] for x in Cr])
    L.append(f"  random (contracts (1,2),(4,4),(12,6)): mean {cr.mean():.3f} max {cr.max():.3f}")
    L.append('(d) siloed per-borrower OPT / shared OPT')
    L.append('  constructed: ' + ', '.join(f"b={r['b']}: {r['ratio']:.3f}" for r in D))
    for b in [2, 4, 8]:
        v = np.array([x['ratio'] for x in Dr if x['b'] == b])
        L.append(f"  random n=16 clients, b={b} borrowers: mean {v.mean():.3f} min {v.min():.3f} max {v.max():.3f}")
    err = max(abs(r['milp'] - r['dp']) for r in E)
    L.append(f"(e) parking-permit embedding: max |OPT_eager(MILP) - PP DP| over 20 instances = {err:.2e}")
    txt = '\n'.join(L)
    print(txt)
    open(os.path.join(OUT, 'c4_lower.txt'), 'w').write(txt + '\n')
