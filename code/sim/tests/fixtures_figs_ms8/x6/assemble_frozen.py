"""Assemble the folder of frozen stand-in summaries that e7b_analysis.py reads (--frozen) for the reduced input tree of
the budget-cap figure (figs/supp/sf_cap.py; README in inputs/). **Every file is a reduced-mode (smoke) output, not a
result.** e7b's reduced runs cover the development week 101 with a two-hour horizon; the analysis takes the other runs
of Sublet, A9, BL1 and BL1-GP from the frozen summaries, so the stand-ins must be reduced runs of that week:

    python tests/fixtures_figs_ms8/x6/assemble_frozen.py DST --main MAIN --eval EVAL --sweep SWEEP [SWEEP ...]
                                                         --w0 W0 [W0 ...]

  MAIN   a confirmation part main summary of week 101 (default: the MS5b fixture tree's,
         tests/fixtures_figs_ms5b/inputs/code/sim/out/sublet_v2/main/summary.json)
  EVAL   a reduced e7r part eval summary (run_e7r.sh --reduced, E7R_PART=eval) with Sublet, A9, BL1 and BL1-GP
  SWEEP  reduced S1 v2 part sweep summaries (run_s1v2.sh --reduced, S1V2_PART=sweep), merged: the first run of each
         (tag, point, lender, week, seed) is kept
  W0     reduced S1 v2 part w0 summaries, merged likewise
DST receives sublet_v2/main/summary.json, e7r/eval/summary.json, s1v2/sweep/summary.json and s1v2/w0/summary.json
(meta of the first file of each, with a note naming the merge; the runs unchanged). The tree of 2026-11-24 was made
from the MS5b fixture tree's main, unit B2's reduced eval at 56b847be and the reduced sweep and w0 summaries of the two
smoke roots of unit B4 and its review at 56b847be (points fee8, fee16, slow1, scen_cold_wan_1gbps; fee4 has no S1 v2
run there, so the analysis has no Sublet or A9 run at fee4).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # code/sim/tests/fixtures_figs_ms8/x6
SIM = HERE.parents[2]
MS5B_MAIN = SIM / "tests" / "fixtures_figs_ms5b" / "inputs" / "code" / "sim" / "out" / "sublet_v2" / "main" / \
    "summary.json"


def _rd(p) -> dict:
    return json.loads(Path(p).read_text())


def merged(paths) -> dict:
    """The runs of the summaries `paths`, the first of each (tag, point, mode, week, seed) kept."""
    first = _rd(paths[0])
    seen, runs = set(), []
    for p in paths:
        for r in _rd(p).get("runs") or []:
            k = (r.get("tag"), r.get("point"), r.get("mode"), str(r.get("c")), str(r.get("seed")))
            if k not in seen:
                seen.add(k)
                runs.append(r)
    meta = dict(first.get("meta") or {})
    if len(paths) > 1:
        meta["standin_note"] = f"runs merged from {len(paths)} reduced summaries (assemble_frozen.py); not a result"
    return {"meta": meta, "runs": runs}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dst", type=Path)
    ap.add_argument("--main", type=Path, default=MS5B_MAIN)
    ap.add_argument("--eval", type=Path, required=True)
    ap.add_argument("--sweep", type=Path, nargs="+", required=True)
    ap.add_argument("--w0", type=Path, nargs="+", required=True)
    a = ap.parse_args(argv)
    out = {"sublet_v2/main": merged([a.main]), "e7r/eval": merged([a.eval]), "s1v2/sweep": merged(a.sweep),
           "s1v2/w0": merged(a.w0)}
    for rel, s in out.items():
        if not (s["meta"] or {}).get("reduced"):
            print(f"[assemble_frozen] {rel}: not a reduced summary (meta.reduced); refused", file=sys.stderr)
            return 2
        p = a.dst / rel / "summary.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(s, indent=1, allow_nan=False) + "\n")
        print(f"[assemble_frozen] {p}: {len(s['runs'])} runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
