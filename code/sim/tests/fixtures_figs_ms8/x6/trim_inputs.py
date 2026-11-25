"""Write the input tree tests/fixtures_figs_ms8/x6/inputs/ of the tests of the budget-cap figure (figs/supp/sf_cap.py;
design/ms8/plan.md D2, W; README in inputs/) from a root of reduced (smoke) e7b outputs. **Every file is a
reduced-mode (smoke) output, trimmed, not a result.**

Run from code/sim (any Python; it reads a JSON file and writes a JSON file):

    python tests/fixtures_figs_ms8/x6/trim_inputs.py ROOT [--check]

ROOT holds ROOT/out/e7b/analysis.json: a reduced run of run_e7b.sh (parts week and sens) with e7b_analysis.py run
against the frozen stand-ins that refresh_inputs.sh assembles (it makes the root). The tree keeps

  inputs/code/sim/out/e7b/analysis.json    every key of the analysis but identity.rows (the per-pair rows of the
                                           identity check; its counts stay), with every value kept unchanged.

--check writes nothing and exits 1 if the copy differs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # code/sim/tests/fixtures_figs_ms8/x6
OUT = HERE / "inputs" / "code" / "sim" / "out" / "e7b"


def trim_analysis(a: dict) -> dict:
    out = dict(a)
    out["identity"] = {k: v for k, v in a["identity"].items() if k != "rows"}
    return out


def text_of(obj) -> str:
    return json.dumps(obj, indent=1, allow_nan=False) + "\n"


def targets(root: Path) -> dict[Path, str]:
    a = json.loads((root / "out" / "e7b" / "analysis.json").read_text())
    return {OUT / "analysis.json": text_of(trim_analysis(a))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root", type=Path, help="a root of reduced e7b outputs (ROOT/out/e7b/analysis.json)")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if the copy differs")
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
    print(f"[trim_inputs x6] wrote {len(t)} file(s) under {OUT.relative_to(HERE)} ({len(stale)} changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
