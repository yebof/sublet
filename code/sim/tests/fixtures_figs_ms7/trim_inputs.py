"""Write the input tree tests/fixtures_figs_ms7/inputs/ of the MS7 figure and table tests (Fig. 3 v3, figs/fig4_v3.py;
Tables IV and V, figs/table3_v3.py and figs/table5_alglb.py; design/ms7/w_spec.md §4, unit W-G2; README in inputs/)
from the smoke roots that refresh_inputs.sh makes, and from the MS5b fixture tree. **Every file is a reduced-mode
(smoke) output or a copy of one, not a result.**

Run from code/sim (any Python; it reads JSON files and writes JSON files):

    python tests/fixtures_figs_ms7/trim_inputs.py SCRATCH [--check]

SCRATCH holds refresh_inputs.sh's roots: SCRATCH/e7c/out/e7c/analysis.json (X1's analysis on a reduced run of
run_e7c.sh), SCRATCH/e7r/out/e7r/{analysis.json, eval/summary.json} (X4's analysis on a reduced run of run_e7r.sh) and
SCRATCH/s1v2/out/s1v2/analysis.json (X3's analysis of S1 v2 on a reduced run of run_s1v2.sh); each analysis was run
against the MS5b fixture tree's confirmation summaries (week 101), so that the tree is one development week throughout.

  inputs/code/sim/out/sublet_v2/             copies of tests/fixtures_figs_ms5b/inputs/code/sim/out/sublet_v2/ main,
                                             second (with lb/) and seeds summary.json and analysis.json (reduced runs
                                             of e7h.py's confirmation parts on week 101; that tree's README)
  inputs/code/sim/out/figs/fig4v2.json       copies of the MS5b fixture extracts tests/fixtures_figs_ms5b/fig4v2.json
  inputs/code/sim/out/figs/table3_v2.json    and table3_v2.json (what figs/fig4_v2.py and figs/table3_v2.py write on
                                             that tree), in place of the versioned extracts that Fig. 3 v3 and Table IV
                                             read
  inputs/code/sim/out/e7c/analysis.json      SCRATCH's, unchanged
  inputs/code/sim/out/e7r/analysis.json      SCRATCH's, trimmed to what the scripts read: weeks, meta, tags A9-P,
                                             MPC-T and the '-c2' transplants (their per_week and role), as_built_vs_c2
                                             and checks.identity_summary
  inputs/code/sim/out/e7r/eval/summary.json  SCRATCH's, trimmed to meta and the week runs of A9-P and MPC-T
  inputs/code/sim/out/s1v2/analysis.json     SCRATCH's, trimmed to meta and seed_spread
Every value kept is copied unchanged; only keys and rows are left out. --check writes nothing and exits 1 if a copy
differs (listing it).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # code/sim/tests/fixtures_figs_ms7
SIM = HERE.parents[1]                                # code/sim
OUT = HERE / "inputs" / "code" / "sim" / "out"
MS5B = SIM / "tests" / "fixtures_figs_ms5b"
CONF_FILES = ("main/summary.json", "second/summary.json", "seeds/summary.json", "analysis.json")
E7R_ROWS = ("A9-P", "MPC-T")


def trim_e7r(a: dict) -> dict:
    pairs = [{"as_built": p["as_built"], "c2": p["c2"]} for p in a["as_built_vs_c2"]]
    keep = set(E7R_ROWS) | {p["c2"] for p in pairs}
    tags = {t: {k: v for k, v in a["tags"][t].items() if k in ("policy_id", "family", "kind", "role", "per_week")}
            for t in a["tags"] if t in keep}
    return {"weeks": a["weeks"], "tags": tags, "as_built_vs_c2": pairs,
            "checks": {"identity_summary": a["checks"]["identity_summary"]}, "meta": a["meta"]}


def trim_eval(s: dict) -> dict:
    meta = {k: s["meta"][k] for k in ("exp", "part", "spec", "git_revision", "written", "reduced", "weeks",
                                      "reduced_note") if k in s["meta"]}
    return {"meta": meta, "runs": [r for r in s["runs"] if r.get("tag") in E7R_ROWS and r.get("kind") == "week"]}


def trim_s1v2(a: dict) -> dict:
    return {"meta": a["meta"], "seed_spread": a["seed_spread"]}


def text_of(obj) -> str:
    return json.dumps(obj, indent=1, allow_nan=False) + "\n"


def targets(scratch: Path) -> dict[Path, str]:
    """{file of the tree: its text}."""
    out: dict[Path, str] = {}
    for f in CONF_FILES:
        out[OUT / "sublet_v2" / f] = (MS5B / "inputs" / "code" / "sim" / "out" / "sublet_v2" / f).read_text()
    for lb in sorted((MS5B / "inputs" / "code" / "sim" / "out" / "sublet_v2" / "second" / "lb").glob("*.json")):
        out[OUT / "sublet_v2" / "second" / "lb" / lb.name] = lb.read_text()
    for name in ("fig4v2", "table3_v2"):
        out[OUT / "figs" / f"{name}.json"] = (MS5B / f"{name}.json").read_text()
    out[OUT / "e7c" / "analysis.json"] = (scratch / "e7c" / "out" / "e7c" / "analysis.json").read_text()
    e7r = scratch / "e7r" / "out" / "e7r"
    out[OUT / "e7r" / "analysis.json"] = text_of(trim_e7r(json.loads((e7r / "analysis.json").read_text())))
    out[OUT / "e7r" / "eval" / "summary.json"] = text_of(trim_eval(json.loads((e7r / "eval" / "summary.json")
                                                                             .read_text())))
    out[OUT / "s1v2" / "analysis.json"] = text_of(trim_s1v2(json.loads(
        (scratch / "s1v2" / "out" / "s1v2" / "analysis.json").read_text())))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scratch", type=Path, help="refresh_inputs.sh's folder of smoke roots")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if a copy differs")
    a = ap.parse_args(argv)
    t = targets(a.scratch)
    stale = [p for p, txt in t.items() if not p.is_file() or p.read_text() != txt]
    if a.check:
        for p in stale:
            print(f"stale: {p.relative_to(HERE)}")
        return 1 if stale else 0
    for p, txt in t.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt)
    print(f"[trim_inputs ms7] wrote {len(t)} files under {OUT.relative_to(SIM)} ({len(stale)} changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
