"""Write the input tree tests/fixtures_figs_ms7/g4a/inputs/ of the tests of figs/supp/sf_lag_v2.py and sf_oos.py
(tests/test_figs_ms7_a.py; design/ms7/w_spec.md §4, unit W-G4, writer A; README in inputs/) from the smoke roots that
refresh_inputs.sh makes. **Every file is a reduced-mode (smoke) output or a trimmed copy of one, not a result.**

Run from code/sim (any Python; it reads JSON files and writes JSON files):

    python tests/fixtures_figs_ms7/g4a/trim_inputs.py SCRATCH [--check]

SCRATCH holds refresh_inputs.sh's roots: SCRATCH/e7c/out/ (the registered X1 analysis e7c/analysis.json on a reduced run
of run_e7c.sh, with that run's e7c/lag/summary.json and the confirmation summary it ran against,
sublet_v2/main/summary.json: the MS5b fixture's, development week 101) and SCRATCH/e7o/out/e7o/analysis.json (the
registered X2 analysis on a reduced run of run_e7o.sh, both folds, one cell, bridged to the same MS5b fixture summary).

  inputs/code/sim/out/e7c/analysis.json         SCRATCH's, unchanged
  inputs/code/sim/out/e7c/lag/summary.json      SCRATCH's, trimmed to meta (exp, part, git_revision, reduced, design),
                                                the table and the runs of Sublet-lag and BL1-GP-lag (the keys that
                                                e7c_analysis.py reads: tag, mode, cell, seed, status, r0, guard)
  inputs/code/sim/out/sublet_v2/main/summary.json  SCRATCH's, trimmed to meta and the table rows of the revealed
                                                counterparts and the lagged RetroRenting-style (BL5)
  inputs/code/sim/out/e7o/analysis.json         SCRATCH's, without each fold's sublet_vs_h1_summary (the scripts
                                                recompute it), written without indentation
Every value kept is copied unchanged; only keys and rows are left out. --check writes nothing and exits 1 if a file of
the tree differs (listing it).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # code/sim/tests/fixtures_figs_ms7/g4a
OUT = HERE / "inputs" / "code" / "sim" / "out"
MAIN_TAGS = ("Sublet", "A9", "BL1", "BL1-BO", "BL2", "BL3-0", "BL4", "BL5", "BL5-cur", "BL5-tau60", "BL5N", "BL1N",
             "BL1-GP")
GUARDED = ("Sublet-lag", "BL1-GP-lag")
RUN_KEYS = ("tag", "mode", "cell", "seed", "status", "r0", "guard")


def text_of(obj, indent: int | None = 1) -> str:
    return json.dumps(obj, indent=indent, allow_nan=False) + "\n"


def trim_lag(s: dict) -> dict:
    meta = {k: s["meta"][k] for k in ("exp", "part", "git_revision", "written", "reduced", "design")
            if k in s["meta"]}
    runs = [{k: r[k] for k in RUN_KEYS if k in r} for r in s["runs"] if r.get("tag") in GUARDED]
    return {"meta": meta, "table": s["table"], "runs": runs}


def trim_main(s: dict) -> dict:
    meta = {k: s["meta"][k] for k in ("exp", "part", "git_revision", "written", "reduced") if k in s["meta"]}
    return {"meta": meta, "table": {t: s["table"][t] for t in MAIN_TAGS if t in s["table"]}}


def trim_e7o(a: dict) -> dict:
    out = dict(a)
    out["folds"] = {f: {k: v for k, v in x.items() if k != "sublet_vs_h1_summary"} for f, x in a["folds"].items()}
    return out


def targets(scratch: Path) -> dict[Path, str]:
    e7c, e7o = scratch / "e7c" / "out", scratch / "e7o" / "out"
    return {OUT / "e7c" / "analysis.json": (e7c / "e7c" / "analysis.json").read_text(),
            OUT / "e7c" / "lag" / "summary.json": text_of(trim_lag(json.loads((e7c / "e7c" / "lag" / "summary.json")
                                                                              .read_text()))),
            OUT / "sublet_v2" / "main" / "summary.json": text_of(trim_main(json.loads(
                (e7c / "sublet_v2" / "main" / "summary.json").read_text()))),
            OUT / "e7o" / "analysis.json": text_of(trim_e7o(json.loads((e7o / "e7o" / "analysis.json").read_text())),
                                                   indent=None)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scratch", type=Path)
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if a file differs")
    a = ap.parse_args(argv)
    t = targets(a.scratch)
    if a.check:
        bad = [str(p) for p, txt in t.items() if not p.is_file() or p.read_text() != txt]
        print("\n".join(bad) or "inputs/ is current")
        return 1 if bad else 0
    for p, txt in t.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt)
        print(f"wrote {p.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
