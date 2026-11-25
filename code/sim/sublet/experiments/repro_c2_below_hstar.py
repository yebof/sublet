"""ALG* below H*: worst ratio at the notices of Table PoR (design/sim_spec_ms2.md §16.4 item 9).

C2-T4 analyses ALG* only for H >= H*_mu, while E2 runs A1 at every notice of its grid. For every
cell of `c2/out/por_default.json` `table_por_switch_beta` (switch cost beta~, the default prices of
a5b `inputs`, tau = 0) the script evaluates A1's rule (`AlgStarRule.from_thresholds` of
`c2_thresholds(alpha, alpha_p, mu, lam)`, C2-T4) with the evaluator of the C2 harness
(`harness.c2_plan_cost` against `c2/model.py::opt_cost`, on the grid of `alg_check.worst_star`) and
writes its worst ratio next to the table's exact CR*(H) to code/sim/out/ms2_checks/a1_below_hstar.json.
Informative, no assertion.

Run from code/sim under the 3 GB cap (run_ms2_checks.sh):
  python -m sublet.experiments.repro_c2_below_hstar [--out DIR] [--workers 4] [--quick]
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import json
import sys
import time
from pathlib import Path

from ..paths import C2, import_c2
from .repro_common import checks_dir, pool_map
from .repro_c2sw_scan import grid_worst

OUT = checks_dir()
POR = C2 / "out" / "por_default.json"


def cell(args) -> dict:
    """One Table PoR cell: ALG*'s worst ratio at notice H (beta~ units) next to the exact CR*(H)."""
    row, al, ap = args
    from ..algos.c2rule import AlgStarRule, c2_thresholds
    c2 = import_c2()
    mu, lam, H = float(row["mu"]), float(row["lam"]), float(row["H"])
    th = c2_thresholds(al, ap, mu, lam)
    P = c2.model.Params(mu=mu, alpha=al, ap=ap, H=H, lam=lam)
    rule = AlgStarRule.from_thresholds(th, lam)
    w, arg = grid_worst(P, lambda R: rule.plan(R, H), lambda xs, R: c2.model.opt_cost(xs, R, P), th.s0)
    cr = float(row["CR"])
    return {"mu_over_beta_tilde": mu, "lam": lam, "H": H, "H_s": row.get("Hs"), "H_star": th.Hstar,
            "below_H_star": bool(H < th.Hstar - 1e-12), "reaction": th.react, "regime": th.regime,
            "alg_star_worst": w, "argmax_R": arg, "CR_star_exact": cr, "alg_star_over_CR_star": w / cr,
            "two_minus_alpha": 2 - al, "excess_over_2_minus_alpha": w - (2 - al),
            "table_plan": [row.get("plan_type"), row.get("plan_s")]}


def main(argv=None) -> int:
    ap_ = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap_.add_argument("--out", type=Path, default=OUT, help="output folder (default code/sim/out/ms2_checks or SUBLET_MS2_CHECKS_DIR)")
    ap_.add_argument("--workers", type=int, default=4, help="worker processes (at most 4)")
    ap_.add_argument("--quick", action="store_true", help="four cells only (a smoke check)")
    a = ap_.parse_args(argv)
    por = json.loads(POR.read_text())
    al, ap = por["inputs"]["alpha"], por["inputs"]["alpha_p"]
    rows = por["table_por_switch_beta"]
    if a.quick:
        rows = rows[:: max(1, len(rows) // 4)][:4]
    t0 = time.perf_counter()
    jobs = [(r, al, ap) for r in rows]
    out_rows = pool_map(cell, jobs, a.workers)
    out = {"meta": {"script": "code/sim/sublet/experiments/repro_c2_below_hstar.py",
                    "spec": "design/sim_spec_ms2.md §16.4 item 9 (informative, no assertion)",
                    "source": "code/theory_checks/c2/out/por_default.json table_por_switch_beta",
                    "alpha": al, "alpha_p": ap, "switch": "beta~ (C2-T4 thresholds)",
                    "evaluator": "harness.c2_plan_cost vs model.opt_cost on the grid of alg_check.worst_star",
                    "n_cells": len(out_rows), "n_below_H_star": sum(r["below_H_star"] for r in out_rows),
                    "quick": bool(a.quick), "seconds": time.perf_counter() - t0},
           "rows": out_rows}
    a.out.mkdir(parents=True, exist_ok=True)
    path = a.out / "a1_below_hstar.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"[repro_c2_below_hstar] {len(out_rows)} cells; wrote {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
