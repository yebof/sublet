"""R7: regenerate c3/out/c5_la.txt (a, b), c5_la.json, c5_la_nearest.txt and c5_la_nearest.json
(design/sim_spec_ms2.md §17.3, R7).

Instances and predictions as check_c5_la.py: core.random_instance(default_rng(11000 + seed), T=36, m=4,
J=2, n=8), seeds 0-9; the nine predictions of check_c5_la.NOISE, each predicted instance drawn by
check_c5_la.predicted with a fresh default_rng(12000 + seed) (check_c5_la.py:54), and P_hat =
drivers.predict.plan_core of it (core.opt_eager_cols of core.opt_eager, the reference's MILP).
OPT and LP_aligned are copied from c5_la.json.
(a) psi-PD in core mode: VecPD(problem_from_core(I), psi, pred_cols=P_hat, nearest_pred=False) for
    psi in {0.1, 0.3, 0.5, 0.8, 1.0} (`FracPD(I, lam=psi, pred_cols=P)`), with P, the
    dual-feasibility ratio and d; `_nearest`: the same with nearest_pred=True.
(b) A5 through the engine on from_core(I) with execute='none' (accounting only): its report's C_FP
    (= c(P_hat(sigma)), checked against the JSON's cPhat), C_R (R = VecPD + Rounder with the policy
    generator default_rng(s), s = 0..7, at R_rbar = 1 and the theory rbar), and the combiner's total
    and switches at gamma = 2 and 1 + 1/sqrt 2.
Writes code/sim/out/ms2_checks/c5_la_repro.json, c5_la_repro.txt, c5_la_nearest_repro.json and
c5_la_nearest_repro.txt (the reference's format strings).

Run from code/sim under the 3 GB cap (run_ms2_checks.sh):
  python -m sublet.experiments.repro_c5_la [--out DIR] [--workers 4] [--seeds 10] [--quick]
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

from ..paths import C3, import_ref
from .repro_c3_upper import run_core
from .repro_common import checks_dir, empty_omega, get, make, pool_map, run

OUT = checks_dir()
REF_JSON = C3 / "out" / "c5_la.json"
LAMS = [0.1, 0.3, 0.5, 0.8, 1.0]
G2 = 1 + 1 / math.sqrt(2)
R_SEEDS = 8


def predictions(I, seed: int, la) -> list:
    """(kind, par, predicted instance, P_hat) for the nine predictions of check_c5_la.NOISE."""
    from ..drivers.predict import plan_core
    out = []
    for kind, par in la.NOISE:
        Ip = la.predicted(I, kind, par, np.random.default_rng(12000 + seed))
        out.append((kind, par, Ip, [tuple(int(v) for v in F) for F in plan_core(Ip)]))
    return out


def a5_run(inst, P, gamma, rbar, s, N):
    pol = make("A5", {"gamma": gamma, "R_rbar": rbar, "execute": "none"}, inst,
               inputs={"pred_cols": P, **({"N_bound": N} if rbar == "theory" else {})})
    run(inst, pol, schedule="trace", rng=np.random.default_rng(s))
    rep = pol.report()
    return (float(get(rep, "C_FP")), float(get(rep, "C_R")), float(get(rep, "total")), int(get(rep, "switches")))


def job(args) -> dict:
    seed, ref, quick = args
    from ..instance import from_core
    core = import_ref("core")
    la = import_ref("check_c5_la")
    t0 = time.perf_counter()
    I = core.random_instance(np.random.default_rng(11000 + seed), T=36, m=4, J=2, n=8)
    OPT, LPal = ref["OPT"], ref["LPal"]
    inst, _ = from_core(I, empty_omega(I.m))
    N = max(I.n * I.T, 3)
    out = dict(seed=seed, OPT=OPT, LPal=LPal, rows=[])
    near = []
    preds = predictions(I, seed, la)
    if quick:
        preds = preds[:2]
    for kind, par, Ip, P in preds:
        row = dict(kind=kind, par=par, n_pred_cols=len(P), lam=[])
        for lam in LAMS:
            pdl, _, _ = run_core(I, psi=lam, pred_cols=P, nearest_pred=False)
            Pl = pdl.primal()
            row["lam"].append(dict(lam=lam, P=Pl, P_over_OPT=Pl / OPT, d=int(pdl.d), dualfeas=pdl.dual_feasibility()))
            pdn, _, _ = run_core(I, psi=lam, pred_cols=P, nearest_pred=True)
            Pn = pdn.primal()
            near.append(dict(kind=kind, par=par, lam=lam, d=int(pdn.d), P_over_OPT=Pn / OPT, P=Pn,
                             dualfeas=pdn.dual_feasibility(), rob_chk=Pn / (2 * math.log(1 + pdn.d / lam) * LPal)))
        cP = None
        for tag, rbar in (("r1", 1), ("rth", "theory")):
            c2, cg, mins, sw, Rs, FPs = [], [], [], [], [], []
            for s in range(2 if quick else R_SEEDS):
                fp2, R2, a2, s2 = a5_run(inst, P, 2.0, rbar, s, N)
                fpg, Rg, ag, _ = a5_run(inst, P, G2, rbar, s, N)
                assert abs(R2 - Rg) <= 1e-9 * max(1.0, abs(R2)) and abs(fp2 - fpg) <= 1e-9 * max(1.0, abs(fp2))
                c2.append(a2); cg.append(ag); mins.append(min(fp2, R2)); sw.append(s2); Rs.append(R2); FPs.append(fp2)
            FP = FPs[0]
            cP = FP if cP is None else cP
            c2, cg, mins = map(np.array, (c2, cg, mins))
            row[tag] = dict(R=float(np.mean(Rs)) / OPT, FP=FP / OPT, comb2=float(c2.mean()) / OPT,
                            combg=float(cg.mean()) / OPT, chk2=float((c2 / mins).max()), chkg=float((cg / mins).max()),
                            switches=float(np.mean(sw)))
        eta = int((I.active ^ Ip.active).sum())
        row.update(cPhat=cP, cPhat_over_OPT=cP / OPT, eta=eta, eta_chk=bool(cP <= OPT + I.q * eta + 1e-6))
        for x in row["lam"]:
            lam = x["lam"]
            x["cons_chk"] = (x["P"] / (2 / (1 - lam) * cP)) if lam < 1 else None
            x["rob_chk"] = x["P"] / (2 * math.log(1 + x["d"] / lam) * LPal)
        for x in near:
            if x["kind"] == kind and x["par"] == par:
                lam = x["lam"]
                x["cons_chk"] = (x["P"] / (2 / (1 - lam) * cP)) if lam < 1 else None
        out["rows"].append(row)
    out["_near"] = near
    out["_seconds"] = time.perf_counter() - t0
    return out


def text(R: list, noise) -> str:
    """c5_la.txt with check_c5_la.py's format strings (lines 90-114)."""
    L = ['10 random instances T=36 m=4 J=2 n=8; P_hat = OPT_eager on predicted demand',
         '(a) fractional lambda-PD: mean P/OPT_eager per lambda; max consistency check P/(2c(P)/(1-lam)) and '
         'max dual-feasibility ratio (both must be <= 1)']
    n_rows = min(len(r['rows']) for r in R)
    for i, (kind, par) in enumerate(noise[:n_rows]):
        rows = [r['rows'][i] for r in R]
        cpo = np.array([x['cPhat_over_OPT'] for x in rows])
        s = f"  {kind:10s}{par:<5} c(P)/OPT mean {cpo.mean():6.3f} | "
        for j, lam in enumerate(LAMS):
            po = np.mean([x['lam'][j]['P_over_OPT'] for x in rows])
            s += f"lam={lam}: {po:.3f} "
        cc = max(x['lam'][j]['cons_chk'] for x in rows for j in range(len(LAMS)) if x['lam'][j]['cons_chk'] is not None)
        dfe = max(x['lam'][j]['dualfeas'] for x in rows for j in range(len(LAMS)))
        rc = max(x['lam'][j]['rob_chk'] for x in rows for j in range(len(LAMS)))
        s += f"| cons_chk {cc:.3f} dualfeas {dfe:.3f} rob_chk {rc:.3f} | c(P)<=OPT+q*eta: {all(x['eta_chk'] for x in rows)}"
        L.append(s)
    L.append('(b) integral (mean ratio to OPT_eager): FP, R, combiner gamma=2 (pathwise bound 6), '
             'gamma=1+1/sqrt2 (bound 5.83); max comb/min(FP,R) pathwise')
    for tag in ['r1', 'rth']:
        L.append(f"  robust R = rounded PD with {'r=1 (heuristic)' if tag == 'r1' else 'r=ceil(2 ln N) (theory)'}")
        for i, (kind, par) in enumerate(noise[:n_rows]):
            rows = [r['rows'][i][tag] for r in R]
            g = lambda k: np.array([x[k] for x in rows])
            L.append(f"   {kind:10s}{par:<5} FP {g('FP').mean():6.3f}  R {g('R').mean():6.3f}  comb2 {g('comb2').mean():6.3f}  "
                     f"combg {g('combg').mean():6.3f}  max comb2/min {g('chk2').max():.3f}  max combg/min {g('chkg').max():.3f}  "
                     f"switches {g('switches').mean():.2f}")
    return '\n'.join(L)


def text_nearest(R: list) -> str:
    """c5_la_nearest.txt with check_c5_la_nearest.py's format strings (lines 39-48)."""
    rows = [x for r in R for x in r['rows']]
    L = ['T9 with nearest predicted column only (d = mK + 2); 10 instances x 9 predictions x 5 lambdas',
         f"max d: {max(x['d'] for x in rows)}",
         f"max consistency check P/(2c(P)/(1-lam)): {max(x['cons_chk'] for x in rows if x['cons_chk'] is not None):.3f} (must be <= 1)",
         f"max dual load / (c ln(1+d/lam)): {max(x['dualfeas'] for x in rows):.3f} (must be <= 1)",
         f"max P / (2 ln(1+d/lam) LP_al): {max(x['rob_chk'] for x in rows):.3f} (must be <= 1)"]
    for lam in LAMS:
        ex = [x['P_over_OPT'] for x in rows if x['lam'] == lam and x['kind'] == 'exact']
        L.append(f"lam={lam}: mean P/OPT_eager with exact prediction {np.mean(ex):.3f}")
    return '\n'.join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT, help="output folder (default code/sim/out/ms2_checks or SUBLET_MS2_CHECKS_DIR)")
    ap.add_argument("--workers", type=int, default=4, help="worker processes (at most 4)")
    ap.add_argument("--seeds", type=int, default=10, help="instances (reference: 10)")
    ap.add_argument("--quick", action="store_true", help="instance 0, two predictions, two R seeds")
    a = ap.parse_args(argv)
    ref = json.loads(REF_JSON.read_text())
    la = import_ref("check_c5_la")
    seeds = [0] if a.quick else list(range(a.seeds))
    t0 = time.perf_counter()
    R = pool_map(job, [(s, ref[s], a.quick) for s in seeds], a.workers)
    near = [dict(seed=r["seed"], rows=r.pop("_near")) for r in R]
    secs = [r.pop("_seconds") for r in R]
    meta = {"script": "code/sim/sublet/experiments/repro_c5_la.py", "spec": "design/sim_spec_ms2.md §17.3 R7",
            "copied": "OPT and LPal from code/theory_checks/c3/out/c5_la.json", "quick": bool(a.quick),
            "seconds": time.perf_counter() - t0, "seconds_per_instance": secs}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "c5_la_repro.json").write_text(json.dumps({"meta": meta, "runs": R}, indent=1) + "\n")
    (a.out / "c5_la_repro.txt").write_text(text(R, la.NOISE) + "\n")
    (a.out / "c5_la_nearest_repro.json").write_text(json.dumps({"meta": meta, "runs": near}, indent=1) + "\n")
    (a.out / "c5_la_nearest_repro.txt").write_text(text_nearest(near) + "\n")
    print(text(R, la.NOISE), flush=True)
    print(text_nearest(near), flush=True)
    print(f"[repro_c5_la] done in {time.perf_counter() - t0:.1f} s; wrote {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
