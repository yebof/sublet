"""Scan of ALG* with the C2-SW thresholds at the default calibration (design/sim_spec_ms2.md §16.4 item 8).

For mu / beta~ from 1.10 to 2.00 in steps of 0.01 the script sets H to the C2-SW threshold H*_SW,
builds A1's rule (`AlgStarRule.from_thresholds` of `c2_thresholds(..., bw)`) and evaluates its worst
ratio on the (R, x) grid of `c2/alg_check.py::worst_star` (lines 134-148), with the algorithm's
pre-warm also charged bw (`harness.c2_plan_cost(..., bw)`) and OPT from
`c2/audit/model_switch_cost.opt_cost_bw`. It writes the worst excess over 2 - alpha per mu to
code/sim/out/ms2_checks/c2sw_rule_scan.json. Informative: no assertion; the result informs
Q17. The default calibration is alpha and alpha_p of `a5b_exposure_thresholds.json` `inputs`,
lambda = 1/(alpha + phi) and bw = `prewarm_switch_cost_over_beta_tilde` (0.597), as
`c2/audit/model_switch_cost_default.py` reads them.

`grid_worst` is the grid evaluator shared by the C2 checks of tests/test_c2_harness.py (§16.4 items 7
and 11) and repro_c2_below_hstar.py (item 9).

Run from code/sim under the 3 GB cap (run_ms2_checks.sh):
  python -m sublet.experiments.repro_c2sw_scan [--out DIR] [--workers 4] [--quick]
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

from ..paths import ANALYSIS_OUT, import_c2
from .repro_common import checks_dir, pool_map

OUT = checks_dir()
INF = math.inf

# x grid of alg_check.worst_star (line 137)
XS_BASE = np.concatenate([np.linspace(1e-4, 30, 6001), np.geomspace(31, 1e6, 80)])


def default_calibration() -> dict:
    """alpha, alpha_p, phi, lambda = 1/(alpha + phi) and bw (0.597) of the default calibration, read from
    a5b_exposure_thresholds.json as model_switch_cost_default.py does (its lines 45-48)."""
    a5b = json.loads((ANALYSIS_OUT / "a5b_exposure_thresholds.json").read_text())
    al, ap, phi = a5b["inputs"]["alpha"], a5b["inputs"]["alpha_p"], a5b["inputs"]["phi"]
    return {"alpha": al, "alpha_p": ap, "phi": phi, "lam": 1 / (al + phi),
            "bw": a5b["prewarm_switch_cost_over_beta_tilde"]}


def grid_worst(P, plan_of, opt_of, s, *, bw=None, Rmax=14.0, dR=0.02):
    """Worst ratio of a C2 plan over the grid of alg_check.worst_star (lines 139-147): R over
    arange(H, max(Rmax, H + 6), dR), x over XS_BASE plus R - lam + 1e-7, R +- 1e-7 and s + 1e-7, then
    R = inf on XS_BASE. plan_of(R) gives the plan for window end R (R = inf included), opt_of(xs, R)
    the OPT costs; the plan is priced by harness.c2_plan_cost(plan, R, xs, P, bw=bw).
    Returns (worst ratio, R of the worst finite window rounded to 3 decimals, or 'inf')."""
    from ..harness.c2_harness import c2_plan_cost
    w, arg = 0.0, None
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        for R in np.arange(P.H, max(Rmax, P.H + 6), dR):
            xs = np.unique(np.concatenate([XS_BASE, [R - P.lam + 1e-7, R + 1e-7, R - 1e-7, s + 1e-7]]))
            xs = xs[xs > 0]
            r = float((np.asarray(c2_plan_cost(plan_of(R), R, xs, P, bw=bw), dtype=float) / opt_of(xs, R)).max())
            if r > w:
                w, arg = r, round(float(R), 3)
        r = float((np.asarray(c2_plan_cost(plan_of(INF), INF, XS_BASE, P, bw=bw), dtype=float)
                   / opt_of(XS_BASE, INF)).max())
    if r > w:
        w, arg = r, "inf"
    return w, arg


def scan_point(mu: float, cal: dict) -> dict:
    """One mu of the scan: H = H*_SW, worst ratio of ALG* with the C2-SW thresholds against opt_cost_bw."""
    from ..algos.c2rule import AlgStarRule, c2_thresholds
    c2 = import_c2()
    al, ap, lam, bw = cal["alpha"], cal["alpha_p"], cal["lam"], cal["bw"]
    th = c2_thresholds(al, ap, mu, lam, 1.0, bw)
    H = th.Hstar
    P = c2.model.Params(mu=mu, alpha=al, ap=ap, H=H, lam=lam)
    rule = AlgStarRule.from_thresholds(th, lam)
    t0 = time.perf_counter()
    w, arg = grid_worst(P, lambda R: rule.plan(R, H), lambda xs, R: c2.model_switch_cost.opt_cost_bw(xs, R, P, bw),
                        th.s0, bw=bw)
    return {"mu_over_beta_tilde": mu, "H_star_SW": H, "reaction": th.react, "regime": th.regime,
            "R_rho": th.Rrho, "R_wait": th.Rw, "worst_ratio": w, "two_minus_alpha": 2 - al,
            "excess_over_2_minus_alpha": w - (2 - al), "argmax_R": arg, "seconds": time.perf_counter() - t0}


def mu_grid() -> list[float]:
    """mu / beta~ = 1.10, 1.11, ..., 2.00 (91 points)."""
    return [round(i * 0.01, 2) for i in range(110, 201)]


def _job(args):
    return scan_point(*args)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT, help="output folder (default code/sim/out/ms2_checks or SUBLET_MS2_CHECKS_DIR)")
    ap.add_argument("--workers", type=int, default=4, help="worker processes (at most 4)")
    ap.add_argument("--quick", action="store_true", help="three mu values only (a smoke check)")
    a = ap.parse_args(argv)
    cal = default_calibration()
    mus = mu_grid()
    if a.quick:
        mus = [mus[0], mus[len(mus) // 2], mus[-1]]
    t0 = time.perf_counter()
    jobs = [(mu, cal) for mu in mus]
    rows = pool_map(_job, jobs, a.workers)
    above = [r["mu_over_beta_tilde"] for r in rows if r["excess_over_2_minus_alpha"] > 1e-9]
    out = {"meta": {"script": "code/sim/sublet/experiments/repro_c2sw_scan.py",
                    "spec": "design/sim_spec_ms2.md §16.4 item 8 (informative, no assertion)",
                    "calibration": cal, "source": "code/analysis/out/a5b_exposure_thresholds.json `inputs`",
                    "rule": "AlgStarRule.from_thresholds(c2_thresholds(alpha, alpha_p, mu, lam, 1, bw)) at H = H*_SW",
                    "algorithm_cost": "harness.c2_plan_cost(..., bw): ALG*'s pre-warm also costs bw",
                    "opt": "c2/audit/model_switch_cost.opt_cost_bw",
                    "grid": "alg_check.worst_star: R in arange(H, max(14, H + 6), 0.02); x in linspace(1e-4, 30, 6001) "
                            "+ geomspace(31, 1e6, 80) + R - lam + 1e-7, R +- 1e-7, s0 + 1e-7; then R = inf",
                    "n_points": len(rows), "quick": bool(a.quick), "seconds": time.perf_counter() - t0},
           "mu_with_excess_above_1e-9": above, "rows": rows}
    a.out.mkdir(parents=True, exist_ok=True)
    path = a.out / "c2sw_rule_scan.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"[repro_c2sw_scan] {len(rows)} points, {len(above)} with excess > 1e-9; wrote {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
