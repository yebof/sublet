"""R8: regenerate c3/o1/out/o1_ub.txt (a, b) and o1_ub.json through the engine (design/sim_spec_ms2.md
§17.3, R8; checks 3g and 3h of §1.3).

Jobs as o1_ub.main: m in {2, 3, 5, 8}, rho in {2, 8, 32}, (tau, H) in {(1, 0), (2, 1), (1, 3)}, T = 96,
seeds 0 and 1; the schedules of o1_ub.schedules(F, default_rng(seed)), every set truncated to [0, 96)
(648 rows). Per row: OPT and X from fam.opt_dp; RR_RENEW on from_core(F.core_instance(), omega)
under the `trace` lender (total cost and number of purchases; for 'adaptiveRR' also under the
`adaptive` lender on the empty schedule, whose realized R must equal o1_ub.adaptive_rr(F)); the
bound and rr_ok of o1_ub.job. Marking rows (576, every schedule but 'adaptiveRR'): MARKING under I2
with the policy generators default_rng(1000 + s), s = 0..399 (230,400 engine runs); mark, mark_se,
mark_N from the engine runs, mark_N_exact = fam.marking_expected_leases, Phi from fam.marking_phases,
mark_ok and opt_phase_ok as o1_ub.job. Writes code/sim/out/ms2_checks/o1_ub_repro.json and
o1_ub_repro.txt (the reference's format strings; the bound column of the text uses D = 3 for every
row, o1_ub.py:112, as written).

Run from code/sim under the 3 GB cap (run_ms2_checks.sh), a pool of 4 workers:
  python -m sublet.experiments.repro_o1_ub [--out DIR] [--workers 4] [--seeds 400] [--quick]
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

from ..paths import import_ref
from .repro_common import checks_dir, empty_omega, make, pool_map, run

OUT = checks_dir()
T_FAM = 96


def jobs_list() -> list:
    return [(m, rho, tau, H, T_FAM, seed) for m in [2, 3, 5, 8] for rho in [2, 8, 32]
            for (tau, H) in [(1, 0), (2, 1), (1, 3)] for seed in range(2)]


def harm(m: int) -> float:
    return sum(1.0 / i for i in range(1, m + 1))


def case(m, rho, tau, H, T, seed):
    """(Fam, [(name, omega)]) of o1_ub.schedules(F, default_rng(seed)), sets truncated to [0, T)."""
    fam = import_ref("fam")
    o1 = import_ref("o1_ub")
    F = fam.Fam(m, rho, tau, H, T)
    sch = o1.schedules(F, np.random.default_rng(seed))
    return F, [(name, [np.asarray(o, dtype=np.int64)[np.asarray(o, dtype=np.int64) < T] for o in om])
               for name, om in sch]


def job(args) -> list:
    m, rho, tau, H, T, seed, n_mark = args
    from ..instance import from_core
    fam = import_ref("fam")
    o1 = import_ref("o1_ub")
    F, sch = case(m, rho, tau, H, T, seed)
    rows = []
    for name, om in sch:
        opt, X = fam.opt_dp(F, om)
        inst, _ = from_core(F.core_instance(), om)
        r = run(inst, make("RR_RENEW", {}, inst), schedule="trace")
        ca, na = r.components["total"], len(r.leases)
        bound = min(rho * (1 + F.D / T), 2 * m + F.a * F.D / opt)
        row = dict(m=m, rho=rho, tau=tau, H=H, T=T, sched=name, opt=opt, X=X, rr=ca / opt, NA=na, rr_bound=bound,
                   rr_ok=bool(ca / opt <= bound + 1e-9 and na <= m * (X + 1) and na <= math.ceil(T / F.D)))
        if name == "adaptiveRR":
            inst0, _ = from_core(F.core_instance(), empty_omega(m))
            ra = run(inst0, make("RR_RENEW", {}, inst0), schedule="adaptive")
            want = [np.asarray(o, dtype=np.int64) for o in o1.adaptive_rr(F)]
            want = [o[o < T] for o in want]
            got = [np.asarray(o, dtype=np.int64) for o in ra.schedule.R]
            row["rr_adaptive_lender"] = ra.components["total"] / opt
            row["NA_adaptive_lender"] = len(ra.leases)
            row["adaptive_R_equals_adaptive_rr"] = bool(all(np.array_equal(a, b) for a, b in zip(got, want)))
        else:
            ph = fam.marking_phases(F, om)
            Phi = sum(1 for (p, pe) in ph if pe is not None and pe + F.H <= T - 1)
            started = len(ph)
            c, n = np.zeros(n_mark), np.zeros(n_mark)
            for s in range(n_mark):
                rm = run(inst, make("MARKING", {}, inst), schedule="trace", information="I2",
                         rng=np.random.default_rng(1000 + s))
                c[s], n[s] = rm.components["total"], len(rm.leases)
            Hm = harm(m)
            exN = fam.marking_expected_leases(F, om)
            row.update(mark_N_exact=exN, mark=float(c.mean()) / opt, mark_se=float(c.std() / math.sqrt(len(c))) / opt,
                       mark_N=float(n.mean()), mark_N_bound=Hm * started, Phi=Phi,
                       opt_phase_ok=bool(opt >= Phi * F.beta + F.a * T - 1e-9),
                       mark_ok=bool(exN <= Hm * started + 1e-9 and abs(n.mean() - exN) <= 4 * n.std() / math.sqrt(len(n)) + 1e-9
                                    and c.mean() / opt <= 2 * Hm + 1))
        rows.append(row)
    return rows


def text(res: list) -> str:
    """o1_ub.txt with o1_ub.py's format strings (lines 104-127)."""
    L = ['(a) RR-renew: pathwise bound checks', f"runs: {len(res)}; all ok: {all(r['rr_ok'] for r in res)}"]
    L.append('max RR ratio per (m, rho) over schedules / tau,H / seeds, with min(rho(1+D/T), 2m) and the adaptive T4 value rho m/(m+rho-1)')
    L.append('m rho  maxRR   bound(min rho(1+D/T),2m)  RR@adaptive  T4_asym  argmax_sched')
    for m in [2, 3, 5, 8]:
        for rho in [2, 8, 32]:
            sub = [r for r in res if r['m'] == m and r['rho'] == rho]
            if not sub:
                continue
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
    return '\n'.join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT, help="output folder (default code/sim/out/ms2_checks or SUBLET_MS2_CHECKS_DIR)")
    ap.add_argument("--workers", type=int, default=4, help="worker processes (at most 4)")
    ap.add_argument("--seeds", type=int, default=400, help="marking seeds per schedule (reference: 400)")
    ap.add_argument("--quick", action="store_true", help="two jobs (m = 2 and 8 at rho = 32) and 3 marking seeds")
    a = ap.parse_args(argv)
    jobs = jobs_list()
    n_mark = a.seeds
    if a.quick:
        jobs = [j for j in jobs if j[1] == 32 and j[2:4] == (2, 1) and j[5] == 0 and j[0] in (2, 8)]
        n_mark = 3
    t0 = time.perf_counter()
    res = [r for rows in pool_map(job, [j + (n_mark,) for j in jobs], a.workers) for r in rows]
    a.out.mkdir(parents=True, exist_ok=True)
    meta = {"script": "code/sim/sublet/experiments/repro_o1_ub.py", "spec": "design/sim_spec_ms2.md §17.3 R8",
            "marking_seeds": n_mark, "quick": bool(a.quick), "seconds": time.perf_counter() - t0}
    (a.out / "o1_ub_repro.json").write_text(json.dumps({"meta": meta, "rows": res}, indent=1) + "\n")
    txt = text(res)
    (a.out / "o1_ub_repro.txt").write_text(txt + "\n")
    print(txt, flush=True)
    print(f"[repro_o1_ub] {len(res)} rows in {time.perf_counter() - t0:.1f} s; wrote {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
