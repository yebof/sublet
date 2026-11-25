"""Write the input tree tests/fixtures_figs_ms7/g4b/inputs/ of the tests of the MS7 baseline and stress figures
(figs/supp/sf_bl_ms7.py and sf_stress_ms7.py; design/ms7/w_spec.md §4, unit W-G4 B; README in inputs/) from a root of
reduced (smoke) e7r outputs. **Every file is a reduced-mode (smoke) output, trimmed, not a result.**

Run from code/sim (any Python; it reads JSON files and writes JSON files):

    python tests/fixtures_figs_ms7/g4b/trim_inputs.py ROOT [--check]

ROOT holds ROOT/out/e7r/{analysis.json, tune/selection.json, tune/summary.json, confirm/summary.json}: a reduced run of
run_e7r.sh (parts tune, confirm and eval) with e7r_analysis.py run against the MS5b fixture tree's confirmation
summaries (refresh_inputs.sh makes it). The tree keeps:

  inputs/code/sim/out/e7r/analysis.json        weeks, tags (every tag, every field), margins (r0_tr, W0 and W0plus;
                                               not r0_by_mode), as_built_vs_c2 (the pairs' names), tuned, best_of,
                                               confirm, checks (identity_summary, a9p_invariance,
                                               adaptive_equivalence, provenance) and meta
  inputs/code/sim/out/e7r/tune/selection.json  unchanged
  inputs/code/sim/out/e7r/tune/summary.json    meta (the keys the scripts read) and table
  inputs/code/sim/out/e7r/confirm/summary.json meta (the keys the scripts read) and table
Every value kept is copied unchanged; only keys are left out. --check writes nothing and exits 1 if a copy differs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # code/sim/tests/fixtures_figs_ms7/g4b
OUT = HERE / "inputs" / "code" / "sim" / "out" / "e7r"
META_KEYS = ("exp", "part", "spec", "git_revision", "written", "reduced", "weeks", "modes", "tags", "selection",
             "aliases", "reduced_note")
CHECKS = ("identity_summary", "a9p_invariance", "adaptive_equivalence", "provenance")


def trim_analysis(a: dict) -> dict:
    return {"weeks": a["weeks"], "tags": a["tags"],
            "margins": {t: {k: v for k, v in m.items() if k in ("r0_tr", "W0", "W0plus")}
                        for t, m in a["margins"].items()},
            "as_built_vs_c2": [{"as_built": p["as_built"], "c2": p["c2"]} for p in a["as_built_vs_c2"]],
            "tuned": a["tuned"], "best_of": a["best_of"], "confirm": a["confirm"],
            "checks": {k: a["checks"][k] for k in CHECKS}, "meta": a["meta"]}


def trim_summary(s: dict) -> dict:
    return {"meta": {k: s["meta"][k] for k in META_KEYS if k in s["meta"]}, "table": s["table"]}


def text_of(obj) -> str:
    return json.dumps(obj, indent=1, allow_nan=False) + "\n"


def targets(root: Path) -> dict[Path, str]:
    e = root / "out" / "e7r"
    rd = lambda p: json.loads((e / p).read_text())                         # noqa: E731
    return {OUT / "analysis.json": text_of(trim_analysis(rd("analysis.json"))),
            OUT / "tune" / "selection.json": (e / "tune" / "selection.json").read_text(),
            OUT / "tune" / "summary.json": text_of(trim_summary(rd("tune/summary.json"))),
            OUT / "confirm" / "summary.json": text_of(trim_summary(rd("confirm/summary.json")))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root", type=Path, help="a root of reduced e7r outputs (ROOT/out/e7r/)")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if a copy differs")
    a = ap.parse_args(argv)
    t = targets(a.root)
    stale = [p for p, txt in t.items() if not p.is_file() or p.read_text() != txt]
    if a.check:
        for p in stale:
            print(f"stale: {p.relative_to(HERE)}")
        return 1 if stale else 0
    for p, txt in t.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt)
    print(f"[trim_inputs g4b] wrote {len(t)} files under {OUT.relative_to(HERE)} ({len(stale)} changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
