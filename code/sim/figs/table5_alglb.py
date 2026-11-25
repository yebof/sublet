"""Table V (MS7, label tab:alglb): ALG/LB on the gap days, with the policy-seed spread (design/ms7/w_spec.md §2.8,
"Floats", and §4, unit W-G2; change C58). Writes the float paper/floats/table5_alglb.tex and its extract
code/sim/out/figs/table5_alglb.json. ALG/LB was a column of Table III v2; in the MS7 manuscript it is a table of its own,
with the spread over the gap days and the policy seeds (n with min and max, the
seed spread next to ALG/LB).

Claims: none of its own; descriptive (design/ms7/plan.md D4). Inputs, through figs.inputs (SUBLET_FIGS_IN_ROOT
redirects them):
  code/sim/out/sublet_v2/second/summary.json     the gap days of the confirmation's part second: per (tag, gap cell)
                                                 the ratio of the run's cost to the lower bound (gap_ratio, the
                                                 summary's), the gap rows (bl0a_usd, ratio_validity) and the bounds
                                                 (gap_lp)
  code/sim/out/sublet_v2/second/lb/gap_lp_c<c>.json   each gap day's bound file: its method ('lp': the LP bound of the
                                                 merged relaxation; a MILP's file carries its relative gap), grid and
                                                 horizon
  code/sim/out/s1v2/analysis.json                X3's sensitivity analysis (ms7_sens_analysis.py, registered):
                                                 seed_spread.by_tag.<tag>.max_abs_diff, the largest |r0 at policy seed
                                                 k - r0 at seed 0| over the confirmation's parts main and seeds (weeks,
                                                 lender modes and seeds in the block); its meta.confirmation_inputs must
                                                 name the sha256 of this tree's main and seeds summaries (StyleError: an
                                                 analysis of other confirmation files)
  code/sim/out/sublet_v2/{main,seeds}/summary.json   read for that sha256 check only
RUN_INPUTS = (s1v2/analysis.json,), the MS7 run output; figs/rebuild.py lists the float as pending while it is missing.
A missing input stops the script with exit code 2 and the file named.

Rows (ROWS; style.TABLE_POLICIES_MS7["table5_alglb"], by registry label; nine, as built): Sublet, the guard around
greedy renting, the primary baselines that ran on the gap days (greedy renting with and without back-off,
RetroRenting-style, SpotHedge-style, CoCaR-style; per-borrower ski rental, the lagged RetroRenting-style row, MPC and
protected-only renting did not run there), RetroRenting with tau >= 1 h, and All-fallback (its bill over the bound, the
same in every row of a day). As built: w_spec §2.8 says about 11 rows; with Greedy + notice layer and RetroRenting +
notice layer (Table IV's transplants; their ALG/LB is in the supplement's gap table) and a note the float measured
0.1374 page (floats_heights.py --ms7), above the 0.120-page budget of §1.1, which the pages study's mock of nine rows
without a note set (0.1202); this table measures 0.1202 too. Columns:
  gap       the median over the gap days of ALG/LB, two decimals (statistics.median; Table III v2's ALG/LB cell)
  range     the smallest and largest ALG/LB over the gap days, two decimals ("1.21--1.39")
  bound_gap only if a bound file is a MILP's (method other than 'lp'): the largest relative gap of the bounds of the
            days; with LP bounds alone (the confirmation's) the column is left out and the title says that LB is the LP
            bound (as built: w_spec §2.8 lists a MILP-gap column, but no MILP ran on the gap days)
  seeds     the seed spread of the row's tag from X3's analysis, three decimals, "--" for a tag that ran one policy seed
Every gap day of the summary must have a ratio for a row's tag (MissingKey otherwise); a row whose gap rows carry a
ratio_validity note has it in the extract's notes.

Caption: one title, no note (the budget above): the gap days and their horizon (from the gap cells and the bound files),
the bound (the files' method) and the seed spread's dash; the grid, the menu and the seed spread's scope (weeks, lender
modes, seeds, read from the analysis) are in caption_source for Section VII's sentence. The float goes to --out DIR,
else SUBLET_FIGS_PDF_DIR when set, else paper/floats/; input from a reduced run (any summary's meta.reduced or the
analysis's) is never written into paper/floats/ or code/sim/out/figs/ (SUBLET_FIGS_OUT_DIR must be set).
--from-extract rewrites the float from the extract alone, byte for byte. Run from code/sim:
python -m figs.table5_alglb [--out DIR] [--from-extract [JSON]].
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from figs import style
from figs import table3_v2 as t3
from figs.common import MissingKey, need
from figs.inputs import Inputs

NAME = "table5_alglb"
LABEL = "tab:alglb"
CONF = "code/sim/out/sublet_v2"
SECOND = f"{CONF}/second/summary.json"
MAIN = f"{CONF}/main/summary.json"
SEEDS = f"{CONF}/seeds/summary.json"
S1V2 = "code/sim/out/s1v2/analysis.json"
RUN_INPUTS = (S1V2,)              # the MS7 run output this table needs (figs/rebuild.py's MS7_PENDING)
FLOATS_DIR = style.REPO / "paper" / "floats"
DASH = t3.DASH
TRACE = "L-tr"
ROWS = (("Sublet", "sublet_v2"), ("BL1-GP", "bl1_gp"), ("BL1", "bl1"), ("BL1-BO", "bl1_bo"), ("BL5-cur", "bl5_cur"),
        ("BL5-tau60", "bl5_tau60"), ("BL3-0", "bl3_0"), ("BL4", "bl4"), ("BL0a", "bl0a"))
REFERENCE = "BL0a"
WD_TOL = 1e-9
if tuple(k for _, k in ROWS) != style.TABLE_POLICIES_MS7[NAME]:
    raise style.StyleError(f"{NAME}: ROWS must be style.TABLE_POLICIES_MS7[{NAME!r}] (C58)")
TABLE_ENV_FMT = (r"\setlength{\tabcolsep}{3pt}" "\n"
                 r"\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}l{cols}@{}}")
TABLE_END = r"\end{tabular*}"


class MissingInput(SystemExit):
    """A required input file is missing (exit code 2, the file named)."""


def _json(inp: Inputs, name: str) -> Any:
    p = inp.path(name)
    if not p.is_file():
        what = "an MS7 run output (design/ms7/registration.md; copied in after the runs)" if name in RUN_INPUTS else \
            "a versioned result file"
        raise MissingInput(f"[{NAME}] required input {name} is missing under {inp.root} ({what})")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _sha(inp: Inputs, name: str) -> str:
    p = inp.path(name)
    if not p.is_file():
        raise MissingInput(f"[{NAME}] required input {name} is missing under {inp.root} (a versioned result file)")
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _num(cell: str) -> float:
    return t3._num(cell)


def build(inp: Inputs) -> dict:
    second = _json(inp, SECOND)
    s1 = _json(inp, S1V2)
    gap_rows = {}
    for r in need(second, "runs", what=SECOND):
        if r.get("kind") == "gap":
            gap_rows.setdefault((r["tag"], str(r["cell"])), []).append(r)
    cells = sorted({c for _, c in gap_rows}, key=_num)
    if not cells:
        raise MissingKey(f"{SECOND}: no gap run")
    gap_lp = need(second, "gap_lp", what=SECOND)
    ratio = need(second, "gap_ratio", what=SECOND)
    seeds = sorted({int(r["seed"]) for rs in gap_rows.values() for r in rs})
    if len(seeds) != 1:
        raise MissingKey(f"{SECOND}: the gap runs have policy seeds {seeds}, not one")
    seed = seeds[0]
    files = {c: _json(inp, f"{CONF}/second/lb/gap_lp_{c.split(':')[-1]}.json") for c in cells}
    methods = {c: str(need(f, "method", what=f"gap bound file of {c}")) for c, f in files.items()}
    grids = {need(f, "grid", what="gap bound file") for f in files.values()}
    hz = {int(need(f, "horizon_min", what="gap bound file")) for f in files.values()}
    if len(grids) != 1 or len(hz) != 1:
        raise MissingKey(f"{SECOND}: the gap bound files have grids {sorted(grids)} and horizons {sorted(hz)}")
    for c, f in files.items():
        if abs(float(need(f, "dual_bound", what=f"gap bound file of {c}")) - float(gap_lp[c])) > \
                WD_TOL * max(1.0, abs(float(gap_lp[c]))):
            raise style.StyleError(f"{SECOND}: gap_lp of {c} is {gap_lp[c]}, its bound file's dual bound "
                                   f"{f['dual_bound']}")
    milp = sorted(c for c, m in methods.items() if m != "lp")
    bound_gap = {c: (float(files[c].get("gap")) if files[c].get("gap") is not None else None) for c in cells}
    # the seed spread (X3) and its inputs
    ss = need(s1, "seed_spread", what=S1V2)
    by_tag = need(ss, "by_tag", what=f"{S1V2} seed_spread")
    want = (s1.get("meta") or {}).get("confirmation_inputs") or {}
    have = {"out/sublet_v2/main/summary.json": _sha(inp, MAIN), "out/sublet_v2/seeds/summary.json": _sha(inp, SEEDS)}
    for k, v in have.items():
        if want.get(k) != v:
            raise style.StyleError(f"{S1V2}: its seed spread read {k} with sha256 {want.get(k)}, this tree's has {v} "
                                   "(an analysis of other confirmation summaries)")
    n_weeks, n_seeds = len(ss.get("weeks") or []), len(ss.get("seeds") or [])
    pairs = {int(v.get("n_pairs") or 0) for v in by_tag.values()}
    n_modes = (pairs.pop() // (n_weeks * n_seeds)) if len(pairs) == 1 and n_weeks and n_seeds else None
    rows, notes = {}, {}
    for tag, key in ROWS:
        if tag == REFERENCE:
            vals = {}
            for c in cells:
                b = {float(r["bl0a_usd"]) for t, cc in gap_rows for r in gap_rows[(t, cc)] if cc == c}
                if not b or max(b) - min(b) > WD_TOL * max(b):
                    raise MissingKey(f"{SECOND}: the gap rows of {c} have bl0a_usd {sorted(b)}")
                vals[c] = max(b) / float(gap_lp[c])
            validity = []
        else:
            vals = {c: ratio.get(f"{tag}:{c}:{seed}") for c in cells}
            missing = [c for c, v in vals.items() if v is None]
            if missing:
                raise MissingKey(f"{SECOND}: no gap_ratio of {tag} on {missing}")
            vals = {c: float(v) for c, v in vals.items()}
            validity = sorted({str(r.get("ratio_validity")) for c in cells for r in gap_rows.get((tag, c), [])}
                              - {"None"})
        med, lo, hi = statistics.median(vals.values()), min(vals.values()), max(vals.values())
        sp = (by_tag.get(tag) or {}).get("max_abs_diff")
        row = {"label": style.policy(key).label, "style_key": key, "by_cell": vals, "median": med, "min": lo, "max": hi,
               "seed_spread": None if sp is None else float(sp),
               "seed_spread_at": (by_tag.get(tag) or {}).get("at"),
               "seed_pairs": (by_tag.get(tag) or {}).get("n_pairs"),
               "bound_gap_max": (max(v for v in bound_gap.values() if v is not None)
                                 if milp and any(v is not None for v in bound_gap.values()) else None),
               "texts": {"gap": t3.tex_value(med, 2), "range": f"{t3.tex_value(lo, 2)}--{t3.tex_value(hi, 2)}",
                         "seeds": DASH if sp is None else t3.tex_value(float(sp), 3)}}
        if milp:
            row["texts"]["bound_gap"] = DASH if row["bound_gap_max"] is None else t3.tex_value(row["bound_gap_max"], 3)
        if validity:
            notes[f"{tag}.gap"] = "; ".join(validity)
        if sp is None:
            notes[f"{tag}.seeds"] = "one policy seed (the seed spread covers the tags of part seeds only)"
        rows[tag] = row
    unknown = sorted(t for t in by_tag if t not in rows)
    columns = ["gap", "range"] + (["bound_gap"] if milp else []) + ["seeds"]
    cap = {"gap_cells": cells, "horizon_min": hz.pop(), "grid": grids.pop(), "menu": "reduced", "seed": seed,
           "methods": methods, "milp_cells": milp,
           "spread": {"weeks": list(ss.get("weeks") or []), "seeds": list(ss.get("seeds") or []),
                      "reference_seed": ss.get("reference_seed"), "n_modes": n_modes, "tags": sorted(by_tag)}}
    title, note = caption_parts(cap)
    reduced = {"second": bool((second.get("meta") or {}).get("reduced")),
               "s1v2": bool((s1.get("meta") or {}).get("reduced"))}
    return {"order": [t for t, _ in ROWS], "rows": rows, "columns": columns, "caption": title, "note": note,
            "labels": {"caption": f"{title} {note}".strip()}, "caption_source": cap, "notes": notes,
            "seed_spread_tags_without_row": unknown,
            "tables": {f"{NAME}.tex": {"scope": {"tags": [t for t, _ in ROWS], "keys": [k for _, k in ROWS],
                                                 "gap_cells": cells, "seeds": [seed],
                                                 "seed_spread": cap["spread"]}}},
            "statistic": "statistics.median, min and max over the gap days (no interval: design/ms7/plan.md D4)",
            "meta": {"reduced": any(reduced.values()), "reduced_by_input": reduced,
                     "git_revisions": {"second": (second.get("meta") or {}).get("git_revision"),
                                       "s1v2": (s1.get("meta") or {}).get("git_revision")},
                     "s1v2_registration_matches": ((s1.get("meta") or {}).get("registration") or {}).get("matches"),
                     "inputs_sha256": {n: hashlib.sha256(inp.path(n).read_bytes()).hexdigest()
                                       for n in [SECOND, S1V2, MAIN, SEEDS]},
                     "sources": [SECOND, S1V2]},
            "sources": list(inp.sources)}


# ---------------------------------------------------------------------------------------------------------------
NUMBER_WORDS = t3.NUMBER_WORDS


def caption_parts(cap: Mapping) -> tuple[str, str]:
    """(title, note): the title names the gap days (from the gap cells and the bound files' horizon), the bound (the
    files' method) and the seed spread with its dash (as built: the table has no note, so that it keeps the page budget
    of w_spec §1.1, 0.120 page, measured as the pages study's mock: floats_heights.py --ms7; the grid and menu of the gap
    days, which Section VII-A and the supplement give, and the seed spread's scope are in caption_source)."""
    bound = ("LB: the LP bound" if not cap["milp_cells"] else
             "LB: the larger of the LP bound and the MILP dual bound")
    title = (f"ALG/LB on the first {t3.horizon_text(cap['horizon_min'])} of {t3._cells_text(cap['gap_cells'])} "
             f"({bound}) and the largest change of $r_0$ from policy seed {cap['spread']['reference_seed']} "
             f"({DASH}: one seed).")
    return title, ""


HEADER = {"policy": "Policy", "gap": "Median", "range": "Range", "bound_gap": "Bound gap", "seeds": "Seed spread"}
# review of W-G2: the ALG/LB column is the median over the gap days (the title names ALG/LB); the seed spread is the
# largest |r0(seed k) - r0(seed 0)| of the S1 v2 analysis, which the title says


def float_tex(data: Mapping) -> str:
    meta = data["meta"]
    revs = meta.get("git_revisions") or {}
    cols = data["columns"]
    lines = [
        "% Table V (MS7, design/ms7/w_spec.md §2.8, unit W-G2; change C58). Written by code/sim/figs/table5_alglb.py from",
        "% code/sim/out/sublet_v2/second/ (the gap days) and code/sim/out/s1v2/analysis.json (the seed spread); do not",
        "% edit. Revisions: " + ", ".join(f"{k} {v}" for k, v in revs.items()) + ". Rows by registry label",
        "% (style.TABLE_POLICIES_MS7['table5_alglb']); per-day values in code/sim/out/figs/table5_alglb.json. Needs booktabs."]
    if meta.get("reduced"):
        lines.append("% REDUCED INPUT (meta.reduced true): a smoke run, not a result.")
    spec = "c" * len(cols)
    lines += [r"\begin{table}[t]", r"\caption{" + data["caption"] + "}", r"\label{" + LABEL + "}",
              r"\centering\footnotesize", TABLE_ENV_FMT.replace("{cols}", spec), r"\toprule"]
    lines.append(" & ".join([HEADER["policy"]] + [HEADER[c] for c in cols]) + r" \\")
    lines.append(r"\midrule")
    for tag in data["order"]:
        r = data["rows"][tag]
        lines.append(" & ".join([r["label"]] + [r["texts"][c] for c in cols]) + r" \\")
    lines += [r"\bottomrule", TABLE_END]
    if data.get("note"):
        lines[-1] += r"\par\vspace{2pt}"
        lines.append(r"\parbox{\columnwidth}{\footnotesize\raggedright " + data["note"] + "}")
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n"


def float_dir(out: str | os.PathLike | None) -> Path:
    if out:
        return Path(out)
    env = os.environ.get(style.ENV_PDF_DIR)
    return Path(env) if env else FLOATS_DIR


def write_float(data: Mapping, out_dir: Path) -> Path:
    if data["meta"].get("reduced") and Path(out_dir).resolve() == FLOATS_DIR.resolve():
        raise SystemExit(f"[{NAME}] the inputs are from a reduced run (meta.reduced); the float is not written into "
                         f"{FLOATS_DIR} (give --out DIR)")
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / f".{NAME}.tex.partial"
    tmp.write_text(float_tex(data), encoding="utf-8")
    os.replace(tmp, out_dir / f"{NAME}.tex")
    return out_dir / f"{NAME}.tex"


def _guard_extract(data: Mapping) -> None:
    """Input from a reduced run is never written into code/sim/out/figs/ either (review of W-G2: a reduced extract there
    would end the rebuild entry's pending state, figs/rebuild.py); main() checks it before writing anything."""
    _, out = style.output_dirs()
    if data["meta"].get("reduced") and Path(out).resolve() == Path(style.DEFAULT_OUT_DIR).resolve():
        raise SystemExit(f"[{NAME}] the inputs are from a reduced run (meta.reduced); the extract is not written into "
                         f"{style.DEFAULT_OUT_DIR} (set {style.ENV_OUT_DIR})")


def write_extract(data: Mapping, sources: Sequence[str]) -> Path:
    _, out = style.output_dirs()
    _guard_extract(data)
    out.mkdir(parents=True, exist_ok=True)
    payload = {"table": NAME, "sources": [style.check_source(s) for s in sources],
               "data": {k: v for k, v in data.items() if k != "sources"}}
    tmp = out / f".{NAME}.json.partial"
    tmp.write_text(json.dumps(payload, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, out / f"{NAME}.json")
    return out / f"{NAME}.json"


def main(argv: Sequence[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(prog=f"python -m figs.{NAME}", description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=None, metavar="DIR",
                    help=f"folder of the float (default: SUBLET_FIGS_PDF_DIR if set, else {FLOATS_DIR})")
    ap.add_argument("--from-extract", nargs="?", const="", default=None, metavar="JSON",
                    help=f"rewrite the float from the extract alone (default code/sim/out/figs/{NAME}.json under the "
                         "input root)")
    args = ap.parse_args(argv)
    try:
        if args.from_extract is None:
            inp = Inputs()
            data = json.loads(json.dumps(build(inp), allow_nan=False))
            sources = list(data.pop("sources"))
        else:
            if args.from_extract:
                payload = json.loads(Path(args.from_extract).read_text(encoding="utf-8"))
            else:
                payload = _json(Inputs(), f"code/sim/out/figs/{NAME}.json")
            if payload.get("table") != NAME:
                raise style.StyleError(f"{args.from_extract or NAME} is the extract of {payload.get('table')!r}, "
                                       f"not {NAME!r}")
            data, sources = dict(payload["data"]), list(payload.get("sources") or [])
            data["caption"], data["note"] = caption_parts(data["caption_source"])
            data["labels"] = {**data.get("labels", {}), "caption": f"{data['caption']} {data['note']}".strip()}
    except MissingInput as err:
        print(err.code, file=sys.stderr)
        raise SystemExit(2) from None
    _guard_extract(data)
    tex = write_float(data, float_dir(args.out))
    ext = write_extract(data, sources)
    print(f"[{NAME}] wrote {tex} and {ext} ({len(data['order'])} rows, {len(data['notes'])} cell notes)")
    return {"tex": str(tex), "json": str(ext), "data": data, "sources": sources}


if __name__ == "__main__":
    main(sys.argv[1:])
