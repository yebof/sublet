"""Write the input tree tests/fixtures_figs_ms7/g4c/inputs/ of the tests of the X3 supplementary scripts sf_s1_v2,
sf_e5_v2, sf_e8_v2 and sf_e9_v2 (tests/test_figs_ms7_c.py; design/ms7/w_spec.md §4, unit W-G4, writer C; README in
inputs/) from a smoke root of the X3 drivers. **Every file is a reduced-mode (smoke) output, a trimmed copy of one, or
the frozen analysis run on those; not a result.**

Run from code/sim, inside a 3G scope (it imports the frozen analysis):

    python tests/fixtures_figs_ms7/g4c/trim_inputs.py ROOT [--check]

ROOT is an MS3_ROOT whose out/ holds reduced outputs of run_s1v2.sh (parts sweep and w0), run_e5v2.sh, run_e8v2.sh
(part a) and run_e9v2.sh (refresh_inputs.sh makes one, or reuses an earlier one). The summaries are copied into
inputs/code/sim/out/<exp>/ with every key that neither the frozen analysis (sublet/experiments/ms7_sens_analysis.py)
nor the four scripts read left out (TRIM below; every value kept is copied unchanged), and the frozen analysis then runs
on that tree (ms7_sens_analysis.run_analysis(['s1v2', 'e5v2', 'e8v2', 'e9v2'], root=<the tree's code/sim>,
conf_dir=<the MS5b fixture's sublet_v2>)), so that each analysis.json records the sha256 of the trimmed summaries that
the scripts read beside it (the scripts check it) and the seed spread is the MS5b fixture's (one development week). The
analyses' markdown files are left out. --check writes nothing and exits 1 if a file of the tree would change (the
analyses' git revision and registration record included).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent              # code/sim/tests/fixtures_figs_ms7/g4c
SIM = HERE.parents[2]                                # code/sim
TREE = HERE / "inputs"
OUT = TREE / "code" / "sim" / "out"
MS5B_CONF = SIM / "tests" / "fixtures_figs_ms5b" / "inputs" / "code" / "sim" / "out" / "sublet_v2"
if str(SIM) not in sys.path:
    sys.path.insert(0, str(SIM))

SUMMARIES = {"s1v2/sweep/summary.json": "sweep", "s1v2/w0/summary.json": "w0", "e5v2/summary.json": "e5v2",
             "e8v2/a/summary.json": "e8v2", "e9v2/summary.json": "e9v2"}
META_DROP = ("instances", "sources", "jobs_not_ok", "loadavg_start", "versions", "limits", "first_job",
             "ignored_outputs")
POINT_KEEP = ("row", "value", "label", "mu", "gamma_row")
E9_RUN_KEEP = ("policy_act_s_mean", "policy_act_s_p99", "slow_loop_s_per_h", "fast_loop_s_per_h", "loops_s_per_h",
               "slow_step_p99_s", "peak_rss_mb", "hours", "n_slow_steps", "projected_slots", "r0")
E9_AGG_KEEP = ("loops_s_per_h", "slow_loop_s_per_h", "fast_loop_s_per_h", "peak_rss_mb", "policy_act_s_mean")


def _meta(m: dict) -> dict:
    return {k: v for k, v in m.items() if k not in META_DROP}


def _checks(c: dict, keep_full: tuple = ()) -> dict:
    """Each check's status and claim (and the whole check for keep_full)."""
    return {k: (v if k in keep_full else {x: v.get(x) for x in ("status", "claim") if x in v}) for k, v in c.items()}


def trim(kind: str, s: dict) -> dict:
    """The summary `s` of `kind` with the keys that no reader uses left out (values unchanged)."""
    if kind == "sweep":
        return {"meta": _meta(s["meta"]), "table": s["table"],
                "points": {n: {k: p.get(k) for k in POINT_KEEP} for n, p in s["points"].items()},
                "reused": s["reused"], "not_run": s["not_run"], "checks": _checks(s.get("checks") or {})}
    if kind == "w0":
        return {"meta": _meta(s["meta"]), "table": s["table"], "W0": s["W0"],
                "reused_default_W0": s["reused_default_W0"], "checks": _checks(s.get("checks") or {})}
    if kind == "e5v2":
        return {"meta": _meta(s["meta"]), "cells": s["cells"], "checks": _checks(s.get("checks") or {})}
    if kind == "e8v2":
        return {k: (_meta(v) if k == "meta" else _checks(v) if k == "checks" else v) for k, v in s.items()
                if k not in ("missing",)}
    if kind == "e9v2":
        pts = {}
        for p, e in s["points"].items():
            pol = {}
            for t, x in (e.get("policies") or {}).items():
                pol[t] = {"n_runs": x.get("n_runs"), "alignments": x.get("alignments"),
                          "by_alignment": {c: {k: r.get(k) for k in E9_RUN_KEEP}
                                           for c, r in (x.get("by_alignment") or {}).items()},
                          "median": {k: (x.get("median") or {}).get(k) for k in E9_AGG_KEEP},
                          "max": {k: (x.get("max") or {}).get(k) for k in ("peak_rss_mb",)}}
            pts[p] = {**{k: e.get(k) for k in ("n_sites", "n_llms", "n_contracts", "sites_x_llms", "n_units")},
                      "policies": pol, "split": e.get("split")}
        return {"meta": _meta(s["meta"]), "points": pts, "lp": s.get("lp"),
                "checks": _checks(s.get("checks") or {}, keep_full=("E9v2-1",))}
    raise KeyError(kind)


def text_of(obj) -> str:
    return json.dumps(obj, indent=1, allow_nan=False) + "\n"


def targets(root: Path) -> dict[Path, str]:
    """{file of the tree: its text}: the trimmed summaries, then the analyses run on them (in a temporary copy)."""
    out = {OUT / rel: text_of(trim(kind, json.loads((root / "out" / rel).read_text())))
           for rel, kind in SUMMARIES.items()}
    from sublet.experiments import ms7_sens_analysis as M
    with tempfile.TemporaryDirectory(prefix="g4c_trim_") as tmp:
        t = Path(tmp)
        for p, txt in out.items():
            q = t / "out" / p.relative_to(OUT)
            q.parent.mkdir(parents=True, exist_ok=True)
            q.write_text(txt)
        M.run_analysis(list(M.EXPS), root=t, conf_dir=MS5B_CONF)
        for exp in M.EXPS:
            out[OUT / exp / "analysis.json"] = (t / "out" / exp / "analysis.json").read_text()
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root", type=Path, help="an MS3_ROOT with the reduced X3 outputs under out/")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if a file would change")
    a = ap.parse_args(argv)
    t = targets(a.root.resolve())
    stale = [p for p, txt in t.items() if not p.is_file() or p.read_text() != txt]
    if a.check:
        for p in stale:
            print(f"stale: {p.relative_to(HERE)}")
        return 1 if stale else 0
    for p, txt in t.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt)
    print(f"[trim_inputs g4c] wrote {len(t)} files under {OUT.relative_to(SIM)} ({len(stale)} changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
