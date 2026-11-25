"""Write the input tree tests/fixtures_figs_ms8/x7/inputs/ of the tests of the X7 supplementary script sf_e8q
(tests/test_figs_ms8_x7.py; design/ms8/plan.md W; README in inputs/) from a smoke root of the X7 driver. **Every file
is a reduced-mode (smoke) output, a trimmed copy of one, or the frozen analysis run on those; not a result.**

Run from code/sim, inside a 3G scope (it imports the frozen analysis):

    python tests/fixtures_figs_ms8/x7/trim_inputs.py ROOT [--check]

ROOT is an MS3_ROOT whose out/e8q/ holds the reduced outputs of run_e8q.sh --reduced (refresh_inputs.sh makes one, or
reuses an earlier one). The summary is copied into inputs/code/sim/out/e8q/summary.json with every key that neither the
frozen analysis (sublet/experiments/e8q_analysis.py) nor sf_e8q reads left out (TRIM below; every value kept is copied
unchanged), hist.json unchanged (the analysis's Q-2 input; sf_e8q does not read it); then the frozen analysis runs on
that tree (e8q_analysis.run_analysis(root=<a temporary copy>)) with E8 v2's reduced summary of the MS7 fixture tree
(tests/fixtures_figs_ms7/g4c/inputs/code/sim/out/e8v2/a/summary.json, the same reduced grid) as Q-0's reference, so
that analysis.json records the sha256 of the trimmed summary that sf_e8q reads beside it (the script checks it). The
analysis's markdown file is left out. --check writes nothing and exits 1 if a file of the tree would change (the
analysis's git revision included).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent              # code/sim/tests/fixtures_figs_ms8/x7
SIM = HERE.parents[2]                                # code/sim
TREE = HERE / "inputs"
OUT = TREE / "code" / "sim" / "out"
E8V2_REF = SIM / "tests" / "fixtures_figs_ms7" / "g4c" / "inputs" / "code" / "sim" / "out" / "e8v2" / "a" / \
    "summary.json"
if str(SIM) not in sys.path:
    sys.path.insert(0, str(SIM))

META_DROP = ("versions", "jobs_not_ok", "ignored_outputs", "service", "sources")
# per tag cell: the keys the analysis (q0-q3) and sf_e8q read
TAG_KEEP = ("C_fluid", "fluid", "lease_usd", "headroom", "classes", "status", "e8v2", "e8_2_pass", "e8_3_pass")
BY_W_KEEP = ("C_fluid", "C_replay", "error", "gap_usd", "replay", "fallback_by_demand", "by_class",
             "conservation_pass")


def _checks(c: dict) -> dict:
    return {k: {x: v.get(x) for x in ("status", "claim", "n") if x in v} for k, v in c.items()}


def trim_cell(x):
    if x is None:
        return None
    out = {k: x[k] for k in TAG_KEEP if k in x}
    out["by_W"] = {w: {k: y[k] for k in BY_W_KEEP if k in y} for w, y in (x.get("by_W") or {}).items()}
    return out


def trim(s: dict) -> dict:
    """The summary `s` with the keys that no reader uses left out (values unchanged)."""
    cells = {t: {w: {c: {tg: trim_cell(x) for tg, x in d.items()} for c, d in b.items()} for w, b in a.items()}
             for t, a in s["cells"].items()}
    return {"meta": {k: v for k, v in s["meta"].items() if k not in META_DROP}, "cells": cells,
            "missing": s.get("missing", []), "checks": _checks(s.get("checks") or {})}


def text_of(obj) -> str:
    return json.dumps(obj, indent=1, allow_nan=False) + "\n"


def targets(root: Path) -> dict[Path, str]:
    """{file of the tree: its text}: the trimmed summary and hist.json, then the analysis run on them (in a temporary
    copy, with E8 v2's reduced summary as Q-0's reference)."""
    src = root / "out" / "e8q"
    out = {OUT / "e8q" / "summary.json": text_of(trim(json.loads((src / "summary.json").read_text()))),
           OUT / "e8q" / "hist.json": (src / "hist.json").read_text()}
    from sublet.experiments import e8q_analysis as A
    with tempfile.TemporaryDirectory(prefix="x7_trim_") as tmp:
        t = Path(tmp)
        for p, txt in out.items():
            q = t / "out" / p.relative_to(OUT)
            q.parent.mkdir(parents=True, exist_ok=True)
            q.write_text(txt)
        (t / "out" / "e8v2" / "a").mkdir(parents=True)
        shutil.copy(E8V2_REF, t / "out" / "e8v2" / "a" / "summary.json")
        if A.run_analysis(root=t) is None:
            raise SystemExit("[trim_inputs x7] the analysis found an input missing")
        out[OUT / "e8q" / "analysis.json"] = (t / "out" / "e8q" / "analysis.json").read_text()
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root", type=Path, help="an MS3_ROOT with the reduced X7 outputs under out/e8q/")
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
    print(f"[trim_inputs x7] wrote {len(t)} files under {OUT.relative_to(SIM)} ({len(stale)} changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
