"""Write the two trimmed input copies of the MS5b fixture tree that the confirmation parts do not make
(design/sublet_v2.md §11, W13; README in inputs/): E11's summary for sf_e7_grid_dev and MS4's E7 main summary for
sf_e7_links.

Run from code/sim (any Python; it reads two JSON files and writes two):

    python tests/fixtures_figs_ms5b/trim_inputs.py [--check]

  inputs/code/sim/out/e11/summary.json      from the repository's versioned code/sim/out/e11/summary.json (E11, a
                                            result at its commit, meta.git_revision): meta's provenance keys, D2 per
                                            instance (stress modes, the W0 rows and the per-mode medians and cell
                                            counts) for E11's tags BL1-G, BL5-G and BL5, D4's thresholds, and D4's
                                            criteria T and S of those tags (E11's own verdicts, which e7v2_q44.tex
                                            shows in its T column)
  inputs/code/sim/out/e7/main/summary.json  from the MS4 fixture tree's reduced copy
                                            tests/fixtures_figs_ms4/inputs/code/sim/out/e7/main/summary.json (reduced
                                            mode, not a result): meta's provenance, grid, tag and links keys, runs.1
                                            and links of Sublet, BL5 and BL1, each with its saving_pct only

Every value kept is copied unchanged; only keys are left out. --check writes nothing and exits 1 if a copy differs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # code/sim/tests/fixtures_figs_ms5b
SIM = HERE.parents[1]                                # code/sim
OUT = HERE / "inputs" / "code" / "sim" / "out"
E11_SRC = SIM / "out" / "e11" / "summary.json"
E7_SRC = SIM / "tests" / "fixtures_figs_ms4" / "inputs" / "code" / "sim" / "out" / "e7" / "main" / "summary.json"
E11_TAGS = ("BL1-G", "BL5-G", "BL5")
E7_TAGS = ("Sublet", "BL5", "BL1")


def trim_e11(s: dict) -> dict:
    meta = {k: s["meta"][k] for k in ("script", "note", "written", "git_revision", "tags", "definitions")}
    d2 = {}
    for inst, blk in s["D2"].items():
        d2[inst] = {"stress_modes": blk["stress_modes"],
                    "W0": {t: blk["W0"][t] for t in E11_TAGS},
                    "modes": {m: {"cells": v["cells"], "r0": {t: v["r0"][t] for t in E11_TAGS}}
                              for m, v in blk["modes"].items()}}
    crit = {t: {k: s["D4"]["criteria"][t][k] for k in ("T", "S")} for t in E11_TAGS}
    return {"meta": meta, "D2": d2, "D4": {"thresholds": s["D4"]["thresholds"], "criteria": crit}}


def trim_e7(s: dict) -> dict:
    keep = ("exp", "part", "spec", "git_revision", "written", "reduced", "reduced_note", "grids", "tags", "B0_rule",
            "links")
    meta = {k: s["meta"][k] for k in keep if k in s["meta"]}
    runs = {"1": {t: {"saving_pct": s["runs"]["1"][t]["saving_pct"]} for t in E7_TAGS}}
    links = {n: {t: {"saving_pct": v[t]["saving_pct"]} for t in E7_TAGS} for n, v in s["links"].items()}
    return {"meta": meta, "runs": runs, "links": links}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if a copy is stale")
    args = ap.parse_args(argv)
    jobs = ((E11_SRC, OUT / "e11" / "summary.json", trim_e11), (E7_SRC, OUT / "e7" / "main" / "summary.json", trim_e7))
    stale = []
    for src, dst, fn in jobs:
        text = json.dumps(fn(json.loads(src.read_text())), indent=1, allow_nan=False) + "\n"
        if not dst.is_file() or dst.read_text() != text:
            stale.append(str(dst.relative_to(HERE)))
            if not args.check:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(text)
    print(f"[trim_inputs] {'stale' if args.check else 'written'}: {stale or 'none'}")
    return 1 if (args.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
