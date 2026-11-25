"""O1 upper bounds on the T4 family (design/theory/o1_oblivious_lender.md, Thms O1-B, O1-D).

(a) RR-renew (deterministic, own-lease feedback).  Pathwise checks against exact OPT (DP):
    N_A <= m (X + 1), X = purchases + fallback slots of an optimal plan;  N_A <= ceil(T/D);
    ALG/OPT <= min(rho (1 + D/T), 2m + aD/OPT).  Schedules: Bernoulli, safe-site, i.i.d. step,
    single-site-per-step, and the adaptive cat-and-mouse lender of Theorem 4.
(b) Marking (randomized, full feedback).  Per schedule, 400 runs: E[N_A] <= H_m (#phases
    started) and E[ALG] <= (2 H_m + 1) OPT; deterministic check OPT >= Phi beta + a T with Phi the
    number of complete phases.
Output: out/o1_ub.txt, out/o1_ub.json
"""
import os, sys, json, math
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
import multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
from fam import (Fam, opt_dp, safe_site_schedule, iid_step_schedule, bernoulli_schedule,
                 run_renew, rr_choose, run_marking, marking_phases, marking_expected_leases)

OUT = os.path.join(HERE, 'out')


def harm(m):
    return sum(1.0 / i for i in range(1, m + 1))


def one_site_per_step(F, U, rng):
    om = [[] for _ in range(F.m)]
    for u in range(1, U):
        om[int(rng.integers(F.m))].append(u * F.D)
    return [np.array(o, dtype=int) for o in om]


def adaptive_rr(F):
    """cat-and-mouse: announce at a site exactly when RR's lease there reaches age tau."""
    om = [[] for _ in range(F.m)]
    t, site = 0, -1
    while t < F.T:
        site = (site + 1) % F.m
        om[site].append(t + F.tau)
        t = t + F.D
    return [np.array(sorted(o), dtype=int) for o in om]


def schedules(F, rng):
    out = []
    for rate in [0.005, 0.02, 0.05, 0.2, 0.5]:
        out.append(('bern%.3f' % rate, bernoulli_schedule(F, rate, rng)))
    U = F.T // F.D
    k = max(2, F.m)
    Phi = max(1, F.T // (k * F.D))
    if Phi >= 1 and F.m >= 2:
        om, _ = safe_site_schedule(F, k, Phi, rng)
        om = [o[o < F.T] for o in om]
        out.append(('safe', om))
    out.append(('iid0.5', iid_step_schedule(F, 0.5, U, rng)))
    out.append(('onesite', one_site_per_step(F, U, rng)))
    out.append(('adaptiveRR', adaptive_rr(F)))
    return out


def job(args):
    m, rho, tau, H, T, seed = args
    F = Fam(m, rho, tau, H, T)
    rng = np.random.default_rng(seed)
    rows = []
    for name, om in schedules(F, rng):
        opt, X = opt_dp(F, om)
        ca, na = run_renew(F, om, rr_choose(m))
        bound = min(rho * (1 + F.D / T), 2 * m + F.a * F.D / opt)
        r = dict(m=m, rho=rho, tau=tau, H=H, T=T, sched=name, opt=opt, X=X, rr=ca / opt, NA=na,
                 rr_bound=bound, rr_ok=bool(ca / opt <= bound + 1e-9 and na <= m * (X + 1)
                                            and na <= math.ceil(T / F.D)))
        if name != 'adaptiveRR':
            ph = marking_phases(F, om)
            Phi = sum(1 for (p, pe) in ph if pe is not None and pe + F.H <= T - 1)
            started = len(ph)
            mc = [run_marking(F, om, np.random.default_rng(1000 + s)) for s in range(400)]
            c = np.array([x[0] for x in mc]); n = np.array([x[1] for x in mc])
            Hm = harm(m)
            exN = marking_expected_leases(F, om)
            r.update(mark_N_exact=exN, mark=float(c.mean()) / opt, mark_se=float(c.std() / math.sqrt(len(c))) / opt,
                     mark_N=float(n.mean()), mark_N_bound=Hm * started, Phi=Phi,
                     opt_phase_ok=bool(opt >= Phi * F.beta + F.a * T - 1e-9),
                     mark_ok=bool(exN <= Hm * started + 1e-9 and abs(n.mean() - exN) <= 4 * n.std() / math.sqrt(len(n)) + 1e-9
                                  and c.mean() / opt <= 2 * Hm + 1))
        rows.append(r)
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    for m in [2, 3, 5, 8]:
        for rho in [2, 8, 32]:
            for (tau, H) in [(1, 0), (2, 1), (1, 3)]:
                for seed in range(2):
                    jobs.append((m, rho, tau, H, 96, seed))
    with mp.Pool(5) as pool:
        res = [r for rows in pool.map(job, jobs) for r in rows]
    with open(os.path.join(OUT, 'o1_ub.json'), 'w') as f:
        json.dump(res, f, indent=1)
    L = ['(a) RR-renew: pathwise bound checks', f"runs: {len(res)}; all ok: {all(r['rr_ok'] for r in res)}"]
    L.append('max RR ratio per (m, rho) over schedules / tau,H / seeds, with min(rho(1+D/T), 2m) and the adaptive T4 value rho m/(m+rho-1)')
    L.append('m rho  maxRR   bound(min rho(1+D/T),2m)  RR@adaptive  T4_asym  argmax_sched')
    for m in [2, 3, 5, 8]:
        for rho in [2, 8, 32]:
            sub = [r for r in res if r['m'] == m and r['rho'] == rho]
            b = max(sub, key=lambda r: r['rr'])
            ad = max(r['rr'] for r in sub if r['sched'] == 'adaptiveRR')
            L.append(f"{m} {rho:<4} {b['rr']:.3f}   {min(rho * (1 + 3 / 96), 2 * m):.3f}                      {ad:.3f}        "
                     f"{rho * m / (m + rho - 1):.3f}    {b['sched']}")
    mk = [r for r in res if 'mark' in r]
    L.append('\n(b) full-information marking: exact E[N_A]; E[ALG] over 400 runs per schedule (MC count agrees with exact within 4 se)')
    L.append(f"runs: {len(mk)}; all ok (E[N_A] <= H_m * phases, E[ALG] <= (2H_m+1) OPT): {all(r['mark_ok'] for r in mk)}; "
             f"OPT >= Phi beta + aT on all: {all(r['opt_phase_ok'] for r in mk)}")
    L.append('m rho  sched        max E[ALG]/OPT   2H_m+1   max exact E[N_A]/(H_m phases)   RR on same')
    for m in [2, 3, 5, 8]:
        for rho in [8, 32]:
            for sc in ['bern0.050', 'bern0.200', 'safe', 'iid0.5', 'onesite']:
                sub = [r for r in mk if r['m'] == m and r['rho'] == rho and r['sched'] == sc]
                if not sub:
                    continue
                b = max(sub, key=lambda r: r['mark'])
                L.append(f"{m} {rho:<4} {sc:<11}  {b['mark']:.3f}            {2 * harm(m) + 1:.3f}    "
                         f"{max(r['mark_N_exact'] / r['mark_N_bound'] for r in sub):.3f}                           {max(r['rr'] for r in sub):.3f}")
    txt = '\n'.join(L)
    print(txt)
    with open(os.path.join(OUT, 'o1_ub.txt'), 'w') as f:
        f.write(txt + '\n')


if __name__ == '__main__':
    main()
