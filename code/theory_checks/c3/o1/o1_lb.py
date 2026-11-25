"""O1 lower bounds (design/theory/o1_oblivious_lender.md, Theorems O1-A and O1-C).

(A) formulas: LB_A (own-lease feedback, safe-site phases), LB_C (any feedback, i.i.d. step
    hits), adaptive T4, and the upper bounds of O1-B / O1-D, on a (rho, m) grid.
(B) safe-site distribution: OPT(sigma, omega) <= Phi*beta + a*T on every schedule (exact DP,
    MILP cross-check on a subset), and expected costs of natural strategies.
(C) exact Bayes-optimal algorithm (POMDP, own-lease feedback) on tiny instances vs. the
    bound E[ALG] >= Phi*beta*g(k,m) + a*T; same with full feedback to show the gap.
(D) i.i.d. step-hit distribution: E[ALG] >= beta*p*U + a*T for strategies; Monte-Carlo E[OPT].
Output: out/o1_lb.txt, out/o1_lb.json
"""
import os, sys, json, math, itertools, time
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
import multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
from fam import (Fam, opt_dp, safe_site_schedule, iid_step_schedule, run_renew, rr_choose,
                 stay_choose, rand_choose, run_eager, run_marking)
from pomdp import best_response

OUT = os.path.join(HERE, 'out')


def g_fn(k, m):
    if m == math.inf:
        return float(k - 1)
    return sum(max(0.0, 1.0 - (j - 1) / (m - 1)) for j in range(1, k))


def lb_A(rho, m, kmax=4000):
    best, kb = 1.0, None
    for k in range(2, kmax):
        v = ((rho - 1) * g_fn(k, m) + k) / (rho - 1 + k)
        if v > best:
            best, kb = v, k
    return best, kb


def mu_max_geom(m, p):
    """E[max of m iid Geometric(p) on {1,2,...}]."""
    if m == math.inf:
        return math.inf
    s, gq = 0.0, 0
    while True:
        term = 1.0 - (1.0 - (1.0 - p) ** gq) ** m
        s += term
        gq += 1
        if term < 1e-13 and gq > 5:
            return s


def lb_C(rho, m):
    best, pb = 1.0, None
    for p in np.concatenate([np.linspace(0.01, 0.99, 99), 1 - np.logspace(-6, -2, 30)]):
        mu = mu_max_geom(m, p)
        v = ((rho - 1) * p + 1) / ((rho - 1) / mu + 1) if mu < math.inf else (rho - 1) * p + 1
        if v > best:
            best, pb = v, float(p)
    return best, pb


def harm(m):
    return sum(1.0 / i for i in range(1, m + 1))


def part_A():
    rows = []
    for rho in [2, 4, 8, 16, 32, 64, 256]:
        for m in [2, 3, 4, 8, 16, 64, 1024, math.inf]:
            la, kb = lb_A(rho, m) if m != 2 else (1.0, None)   # LB_A needs m >= 3
            lc, pb = lb_C(rho, m)
            ad = rho * m / (m + rho - 1) if m != math.inf else rho
            rows.append(dict(rho=rho, m=str(m), LB_A=la, k=kb, LB_C=lc, p=pb, adaptive_T4=ad,
                             UB_I1=min(rho, 2 * m) if m != math.inf else rho,
                             UB_I2=min(rho, 2 * harm(m) + 1) if m != math.inf else rho))
    return rows


def all_S(m, Phi):
    out = []

    def rec(S):
        if len(S) == Phi:
            out.append(list(S)); return
        for l in range(m):
            if l != S[-1]:
                rec(S + [l])
    for s0 in range(m):
        rec([s0])
    return out


def job_B(args):
    m, rho, tau, H, k, Phi, milp = args
    F = Fam(m, rho, tau, H, T=k * (tau + H) * Phi)
    Ss = all_S(m, Phi)
    rng = np.random.default_rng(1)
    if len(Ss) > 300:
        Ss = [Ss[i] for i in rng.choice(len(Ss), 300, replace=False)]
    bound_opt = Phi * F.beta + F.a * F.T
    opts, costs = [], {n: [] for n in ['rr_renew', 'stay_renew', 'rand_renew', 'eager']}
    milp_diff = 0.0
    for i, S in enumerate(Ss):
        om, _ = safe_site_schedule(F, k, Phi, None, S=S)
        o, _ = opt_dp(F, om)
        opts.append(o)
        if milp and i < 3:
            from core import opt_omega
            milp_diff = max(milp_diff, abs(opt_omega(F.core_instance(), om)['fun'] - o))
        costs['rr_renew'].append(run_renew(F, om, rr_choose(m))[0])
        costs['stay_renew'].append(run_renew(F, om, stay_choose)[0])
        costs['rand_renew'].append(np.mean([run_renew(F, om, rand_choose(m), np.random.default_rng(s))[0]
                                            for s in range(20)]))
        costs['eager'].append(run_eager(F)[0])
    g = g_fn(k, m)
    lb_alg = Phi * F.beta * g + F.a * F.T
    res = dict(m=m, rho=rho, tau=tau, H=H, k=k, Phi=Phi, T=F.T, n_omega=len(Ss),
               max_opt=float(max(opts)), bound_opt=bound_opt, opt_ok=bool(max(opts) <= bound_opt + 1e-9),
               milp_diff=milp_diff, lb_alg=lb_alg, formula=((rho - 1) * g + k) / (rho - 1 + k),
               adaptive_T4=rho * m / (m + rho - 1))
    for n, c in costs.items():
        res[n] = float(np.mean(c)) / bound_opt
        res[n + '_ok'] = bool(np.mean(c) >= lb_alg - 1e-9)
    return res


def part_B():
    jobs = []
    for m in [3, 4, 6, 8]:
        for rho in [4, 16, 64]:
            for (tau, H) in [(1, 0), (2, 1), (1, 2)]:
                jobs.append((m, rho, tau, H, m, 6, (m <= 4 and rho == 16)))
    with mp.Pool(5) as pool:
        return pool.map(job_B, jobs)


def job_C(args):
    m, rho, tau, H, k, Phi, cap = args
    F = Fam(m, rho, tau, H, T=k * (tau + H) * Phi)
    oms = [safe_site_schedule(F, k, Phi, None, S=S)[0] for S in all_S(m, Phi)]
    t0 = time.time()
    v1, n1 = best_response(F, oms, 'I1', cap=cap)
    v2, n2 = best_response(F, oms, 'I2', cap=cap)
    eo = float(np.mean([opt_dp(F, om)[0] for om in oms]))
    g = g_fn(k, m)
    lb_alg = Phi * F.beta * g + F.a * F.T
    return dict(m=m, rho=rho, tau=tau, H=H, k=k, Phi=Phi, T=F.T, cap=cap, n_omega=len(oms),
                best_I1=v1, best_I2=v2, lb_alg=lb_alg, ok=bool(v1 >= lb_alg - 1e-9),
                E_opt=eo, ratio_I1=v1 / eo, ratio_I2=v2 / eo,
                formula=((rho - 1) * g + k) / (rho - 1 + k), states=n1 + n2, sec=time.time() - t0)


def part_C():
    jobs = [(3, 8, 1, 0, 2, 2, None), (3, 8, 1, 0, 3, 2, None), (3, 8, 1, 0, 3, 3, None),
            (3, 32, 1, 0, 3, 3, None), (4, 8, 1, 0, 3, 2, None), (4, 32, 1, 0, 4, 2, None),
            (3, 8, 1, 1, 2, 2, None), (3, 8, 2, 1, 2, 2, None), (4, 32, 1, 0, 3, 3, None),
            (5, 32, 1, 0, 5, 2, 3)]
    with mp.Pool(5) as pool:
        return pool.map(job_C, jobs)


def job_D(args):
    m, rho, tau, H, p, U, n = args
    F = Fam(m, rho, tau, H, T=U * (tau + H))
    rng = np.random.default_rng(7)
    opts, rr, st, mk = [], [], [], []
    for _ in range(n):
        om = iid_step_schedule(F, p, U, rng)
        opts.append(opt_dp(F, om)[0])
        rr.append(run_renew(F, om, rr_choose(m))[0])
        st.append(run_renew(F, om, stay_choose)[0])
        mk.append(run_marking(F, om, rng)[0])
    lb_alg = F.beta * p * U + F.a * F.T
    eo = float(np.mean(opts))
    mu = mu_max_geom(m, p)
    return dict(m=m, rho=rho, tau=tau, H=H, p=p, U=U, n=n, E_opt=eo, E_opt_se=float(np.std(opts) / math.sqrt(n)),
                lb_alg=lb_alg, finite_ratio=lb_alg / eo,
                asym_formula=((rho - 1) * p + 1) / ((rho - 1) / mu + 1),
                rr=float(np.mean(rr)) / eo, stay=float(np.mean(st)) / eo, marking=float(np.mean(mk)) / eo,
                strategies_ok=bool(all(np.mean(x) >= lb_alg - 3 * np.std(x) / math.sqrt(n) for x in (rr, st, mk))))


def part_D():
    jobs = []
    for m in [4, 16, 64]:
        for rho in [8, 32]:
            for (tau, H) in [(1, 0), (2, 1)]:
                jobs.append((m, rho, tau, H, 0.5, 120, 200))
    jobs += [(256, 32, 1, 0, 0.5, 120, 100), (16, 64, 1, 0, 0.1, 200, 100)]
    with mp.Pool(5) as pool:
        return pool.map(job_D, jobs)


def main():
    os.makedirs(OUT, exist_ok=True)
    res = dict(A=part_A(), B=part_B(), C=part_C(), D=part_D())
    with open(os.path.join(OUT, 'o1_lb.json'), 'w') as f:
        json.dump(res, f, indent=1)
    L = []
    L.append('(A) asymptotic ratio bounds on the T4 family (T -> infinity)')
    L.append('rho   m      LB_A(I1)  k*    LB_C(any)  p*     adaptive_T4  UB_I1=min(rho,2m)  UB_I2=min(rho,2H_m+1)')
    for r in res['A']:
        L.append(f"{r['rho']:<5} {r['m']:<6} {r['LB_A']:8.3f}  {str(r['k']):<5} {r['LB_C']:8.3f}  "
                 f"{(r['p'] or 0):.4f}  {r['adaptive_T4']:8.3f}     {r['UB_I1']:8.3f}           {r['UB_I2']:8.3f}")
    L.append('\n(B) safe-site distribution (k = m, Phi = 6): OPT bound and strategies (E[ALG] / (Phi beta + aT))')
    L.append('m rho tau H  T   #om  maxOPT/bound  milp_diff  formula  T4adapt  rr_renew stay_renew rand_renew eager  all>=LB')
    for r in res['B']:
        ok = r['opt_ok'] and all(r[n + '_ok'] for n in ['rr_renew', 'stay_renew', 'rand_renew', 'eager'])
        L.append(f"{r['m']} {r['rho']:<3} {r['tau']}   {r['H']}  {r['T']:<3} {r['n_omega']:<4} "
                 f"{r['max_opt']/r['bound_opt']:.4f}        {r['milp_diff']:.1e}    {r['formula']:.3f}    "
                 f"{r['adaptive_T4']:.3f}    {r['rr_renew']:.3f}    {r['stay_renew']:.3f}      {r['rand_renew']:.3f}     "
                 f"{r['eager']:.3f}  {ok}")
    L.append('\n(C) exact Bayes-optimal algorithm vs the safe-site distribution (all schedules enumerated)')
    L.append('m rho tau H k Phi T  cap  E[ALG*]_I1  bound Phi*beta*g+aT  ok   E[OPT]   ratio_I1  ratio_I2  formula')
    for r in res['C']:
        L.append(f"{r['m']} {r['rho']:<3} {r['tau']}   {r['H']} {r['k']} {r['Phi']}   {r['T']:<2} {str(r['cap']):<4} "
                 f"{r['best_I1']:9.3f}   {r['lb_alg']:9.3f}           {r['ok']}  {r['E_opt']:7.3f}  "
                 f"{r['ratio_I1']:.3f}     {r['ratio_I2']:.3f}     {r['formula']:.3f}")
    L.append('\n(D) i.i.d. step hits: E[ALG] >= beta p U + aT; ratios to Monte-Carlo E[OPT]')
    L.append('m   rho tau H  p     U    E[OPT] (se)        lb/E[OPT]  asym_formula  rr     stay   marking  ok(mean>=lb-3se)')
    for r in res['D']:
        L.append(f"{r['m']:<3} {r['rho']:<3} {r['tau']}   {r['H']}  {r['p']:.2f}  {r['U']:<4} {r['E_opt']:9.2f} ({r['E_opt_se']:.2f})  "
                 f"{r['finite_ratio']:.3f}      {r['asym_formula']:.3f}         {r['rr']:.3f}  {r['stay']:.3f}  {r['marking']:.3f}    {r['strategies_ok']}")
    txt = '\n'.join(L)
    print(txt)
    with open(os.path.join(OUT, 'o1_lb.txt'), 'w') as f:
        f.write(txt + '\n')


if __name__ == '__main__':
    main()
