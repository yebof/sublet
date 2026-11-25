"""MS6 Section VII extract: what projection did in the confirmation's week runs, under one key per number.

Design: design/ms6_spec.md §3.3 (value registry: one versioned file and key per printed number) and review D5, finding
R10 (paper/sections/evaluation.tex, VII-C). The confirmation's part main (code/sim/out/sublet_v2/main/summary.json,
written by experiments/e7h.py in the clean clone of the freeze commit and copied in) lists every week run with its
guard record, but stores no per-tag count of projected runs and no range of the guard's price per run; this step
computes them from that versioned file, reads no run file, and writes code/sim/out/ms6/eval_extract.json.
Cheap (one 2.5 MB JSON, under a second).

Keys of the output (all over the week runs of part main, kind 'week'):
- projection.sublet_runs: Sublet's week runs (16 weeks x 7 lender modes).
- projection.runs_projected: Sublet's runs with at least one projected slot (guard.projected_slots > 0).
- projection.slots_total, slots_min, slots_max: projected slots over those runs, in all and per run.
- projection.same_as_oneway_aborts: True when the projected runs are exactly the (week, mode) pairs in which the
  one-way guard (tag Sublet-1way, the same inner policy without projection) aborts; the script exits nonzero otherwise.
- price.n, price.min, price.max, price.n_nonzero: the guard's price per run, r0(Sublet) - r0(A9) (critical-ratio
  renting alone), over the trace and stress runs (every mode but the honoring lender L-hon), the runs of the
  registered H6 (code/sim/out/sublet_v2/analysis.json H6.n; the script checks the count).

Run (from the repository root):
  ~/venv/bin/python code/sim/figs/ms6_eval_extract.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "code/sim/out/sublet_v2/main/summary.json"
ANALYSIS = REPO / "code/sim/out/sublet_v2/analysis.json"
OUT = REPO / "code/sim/out/ms6/eval_extract.json"
HONOR_MODE = "L-hon"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    summary = json.loads(SRC.read_text(encoding="utf-8"))
    analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    week = [r for r in summary["runs"] if r["kind"] == "week"]
    sublet = [r for r in week if r["tag"] == "Sublet"]
    oneway = [r for r in week if r["tag"] == "Sublet-1way"]
    alone = {(r["cell"], r["mode"]): r["r0"] for r in week if r["tag"] == "A9"}
    bad = [r["job"] for r in sublet + oneway if r["status"] != "ok"]
    if bad:
        print(f"ms6_eval_extract: runs not ok: {bad[:5]}", file=sys.stderr)
        return 1

    projected = [r for r in sublet if r["guard"]["projected_slots"] > 0]
    slots = [r["guard"]["projected_slots"] for r in projected]
    aborted = {(r["cell"], r["mode"]) for r in oneway if r["guard"]["aborted"]}
    same = aborted == {(r["cell"], r["mode"]) for r in projected}

    price = [r["r0"] - alone[(r["cell"], r["mode"])] for r in sublet if r["mode"] != HONOR_MODE]
    if len(price) != analysis["H6"]["n"]:
        print(f"ms6_eval_extract: {len(price)} price runs, H6.n = {analysis['H6']['n']}", file=sys.stderr)
        return 1

    out = {
        "meta": {
            "script": "code/sim/figs/ms6_eval_extract.py",
            "sources": {
                "code/sim/out/sublet_v2/main/summary.json": sha256(SRC),
                "code/sim/out/sublet_v2/analysis.json": sha256(ANALYSIS),
            },
            "note": "review D5 finding R10; over the week runs of the confirmation's part main",
        },
        "projection": {
            "sublet_runs": len(sublet),
            "runs_projected": len(projected),
            "slots_total": sum(slots),
            "slots_min": min(slots) if slots else 0,
            "slots_max": max(slots) if slots else 0,
            "oneway_aborts": len(aborted),
            "same_as_oneway_aborts": same,
        },
        "price": {
            "definition": "r0(Sublet) - r0(A9) per (week, mode), modes other than L-hon",
            "n": len(price),
            "min": min(price),
            "max": max(price),
            "n_nonzero": sum(1 for p in price if p != 0.0),
        },
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out["projection"]), json.dumps(out["price"]))
    if not same:
        print("ms6_eval_extract: projected runs differ from the one-way guard's aborts", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
