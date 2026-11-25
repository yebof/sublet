"""R6: regenerate c3/out/c3_benchmark.txt (b, c) and c3_benchmark.json `b[*].per_rate[*]` through the
engine (design/sim_spec_ms2.md §17.3, R6).

For the instances of check_c3_benchmark.run_b (seeds 0-9: core.random_instance(default_rng(5000 +
seed), T=36, m=4, J=2, n=8, slo=0.7 for odd seeds)) and the rates 0, 0.02, 0.1, 0.3, 1.0
(core.random_omega(default_rng(7000 + seed), I, rate), every slot at rate 1.0), A3 in reference
mode (x3=False, x2='reference', reaction='cold', §7.5) runs on from_core(I, omega) under the
`trace` lender with the policy generators default_rng(s), s = 0..9, for rbar = ceil(2 ln N) and
rbar = 1. Real cost = engine lease cost + pd.service_cost_given_open(I, opened).sum() (the
reference's real_cost_renew + service); accounted cost = A3's cost_pr. ALG_renew, ALG_acc and the
r = 1 values are the means over the rounding seeds; renew_le_2acc as the reference. OPT_omega,
OPT_omega_lb, status, eager_over_omega, bound, rho, OPT_eager and part (a) come from the reference
MILPs and are copied from c3_benchmark.json. Writes code/sim/out/ms2_checks/c3_benchmark_repro.json
and c3_benchmark_repro.txt (the reference's format strings).

Run from code/sim under the 3 GB cap (run_ms2_checks.sh):
  python -m sublet.experiments.repro_c3_benchmark [--out DIR] [--workers 4] [--seeds 10] [--quick]
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from ..paths import C3, import_ref
from .repro_common import checks_dir, lease_cost, make, opened_map, pool_map, run

OUT = checks_dir()
REF_JSON = C3 / "out" / "c3_benchmark.json"
RATES = [0.0, 0.02, 0.1, 0.3, 1.0]
A3_REF = {"x3": False, "x2": "reference", "reaction": "cold", "record": True}
COPIED = ("OPT_omega", "OPT_omega_lb", "status", "eager_over_omega", "bound")


def instance(seed: int):
    core = import_ref("core")
    return core.random_instance(np.random.default_rng(5000 + seed), T=36, m=4, J=2, n=8,
                                slo=0.7 if seed % 2 else None)


def omega(I, seed: int, rate: float) -> list:
    core = import_ref("core")
    if rate < 1:
        return core.random_omega(np.random.default_rng(7000 + seed), I, rate)
    return [np.arange(I.T)] * I.m


def job(args) -> dict:
    seed, rate_i, seeds, ref = args
    from ..instance import from_core
    pd = import_ref("pd")
    I = instance(seed)
    rate = RATES[rate_i]
    inst, _ = from_core(I, omega(I, seed, rate))
    out = {}
    for tag, rbar in (("", "theory"), ("_r1", 1)):
        real, acc = [], []
        for s in range(seeds):
            pol = make("A3", dict(A3_REF, rbar=rbar), inst,
                       inputs={"N_bound": max(I.n * I.T, 3)} if rbar == "theory" else None)
            r = run(inst, pol, schedule="trace", rng=np.random.default_rng(s))
            serv = float(pd.service_cost_given_open(I, opened_map(pol)).sum())
            real.append(lease_cost(r) + serv)
            acc.append(float(pol.report()["cost_pr"]))
        out["real" + tag], out["acc" + tag] = real, acc
    row = dict(rate=rate, ALG_renew=float(np.mean(out["real"])), ALG_acc=float(np.mean(out["acc"])),
               ALG_renew_r1=float(np.mean(out["real_r1"])), ALG_acc_r1=float(np.mean(out["acc_r1"])),
               renew_le_2acc=bool(all(rv <= 2 * av + 1e-6 for rv, av in
                                      zip(out["real"] + out["real_r1"], out["acc"] + out["acc_r1"]))))
    row.update({k: ref["per_rate"][rate_i][k] for k in COPIED})
    row["per_seed"] = out
    return {"seed": seed, "rate_i": rate_i, "row": row}


def text(A: list, B: list) -> str:
    """c3_benchmark.txt with check_c3_benchmark.py's format strings (lines 81-101)."""
    L = ['(a) single site, always-active client, tau=2,H=1,a=1, T=60, no reclaims',
         ' rho   LP_trunc  OPT_eager  OPT_none  LP/OPT_none  OPTeager/OPT_none  max(2,rho)']
    for r in A:
        L.append(f" {r['rho']:4.1f}  {r['LP_trunc']:8.2f}  {r['OPT_eager']:8.2f}  {r['OPT_none']:8.2f}  "
                 f"{r['LP_over_OPTnone']:8.3f}     {r['OPTeager_over_OPTnone']:8.3f}          {r['bound']:.1f}")
    L.append('(b,c) random instances T=36 m=4 J=2 n=8; 10 instances x 10 rounding seeds')
    L.append(' rate  OPTeager/OPTomega(max)  max(2,rho)(min)  status  ALGrenew/OPTomega(mean,max)  '
             'ALGacc/OPTomega(mean)  r=1: renew/OPTomega(mean,max)  renew<=2acc')
    for rate in RATES:
        P = [x for b in B for x in b['per_rate'] if x['rate'] == rate]
        if not P:
            continue
        e = np.array([p['eager_over_omega'] for p in P])
        bd = np.array([p['bound'] for p in P])
        rr = np.array([p['ALG_renew'] / p['OPT_omega_lb'] for p in P])
        ra = np.array([p['ALG_acc'] / p['OPT_omega_lb'] for p in P])
        r1 = np.array([p['ALG_renew_r1'] / p['OPT_omega_lb'] for p in P])
        L.append(f" {rate:4.2f}  {e.max():.3f} (all<=bound: {bool((e <= bd + 1e-9).all())})        {bd.min():.2f}"
                 f"        {set(p['status'] for p in P)}     {rr.mean():.2f},{rr.max():.2f}                  "
                 f"{ra.mean():.2f}                {r1.mean():.2f},{r1.max():.2f}                    "
                 f"{all(p['renew_le_2acc'] for p in P)}")
    eq = [abs(x['OPT_omega'] - b['OPT_eager']) < 1e-6 for b in B for x in b['per_rate'] if x['rate'] == 1.0]
    L.append(f" check: rate=1.0 (announce every slot) reproduces OPT_eager exactly: {all(eq)}")
    return '\n'.join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT, help="output folder (default code/sim/out/ms2_checks or SUBLET_MS2_CHECKS_DIR)")
    ap.add_argument("--workers", type=int, default=4, help="worker processes (at most 4)")
    ap.add_argument("--seeds", type=int, default=10, help="rounding seeds (reference: 10)")
    ap.add_argument("--quick", action="store_true", help="instance 0, rates 0 and 1.0, 2 rounding seeds")
    a = ap.parse_args(argv)
    ref = json.loads(REF_JSON.read_text())
    seeds = 2 if a.quick else a.seeds
    inst_seeds = [0] if a.quick else list(range(10))
    rate_idx = [0, len(RATES) - 1] if a.quick else list(range(len(RATES)))
    t0 = time.perf_counter()
    jobs = [(s, i, seeds, ref["b"][s]) for s in inst_seeds for i in rate_idx]
    res = pool_map(job, jobs, a.workers)
    B = []
    for s in inst_seeds:
        rows = sorted((x for x in res if x["seed"] == s), key=lambda x: x["rate_i"])
        B.append(dict(seed=s, rho=ref["b"][s]["rho"], OPT_eager=ref["b"][s]["OPT_eager"],
                      per_rate=[x["row"] for x in rows]))
    out = dict(a=ref["a"], b=B, meta={"script": "code/sim/sublet/experiments/repro_c3_benchmark.py",
                                      "spec": "design/sim_spec_ms2.md §17.3 R6",
                                      "a": "copied from code/theory_checks/c3/out/c3_benchmark.json",
                                      "copied_per_rate": list(COPIED), "rounding_seeds": seeds,
                                      "quick": bool(a.quick), "seconds": time.perf_counter() - t0})
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "c3_benchmark_repro.json").write_text(json.dumps(out, indent=1) + "\n")
    txt = text(ref["a"], B)
    (a.out / "c3_benchmark_repro.txt").write_text(txt + "\n")
    print(txt, flush=True)
    print(f"[repro_c3_benchmark] done in {time.perf_counter() - t0:.1f} s; wrote {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
