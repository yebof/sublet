"""Table IV (MS7, label tab:e7): end-to-end cost per policy on the confirmation weeks with the causal and contract
columns (design/ms7/w_spec.md §2.8, "Floats", and §4, unit W-G2; change C58). Writes the float paper/floats/
table3_v3.tex and its extract code/sim/out/figs/table3_v3.json. It replaces Table III v2 (figs/table3_v2.py, frozen) in
the manuscript.

Claims: none of its own; descriptive medians over the weeks of per-week values (design/ms7/plan.md D4: no interval, no
p-value; the per-week values are in the extract). Inputs, through figs.inputs (SUBLET_FIGS_IN_ROOT redirects them):
  code/sim/out/figs/table3_v2.json     Table III v2's extract (versioned): the per-week cells of the confirmation's
                                       rows (part main, trace lender, policy seed 0), which it built from the
                                       unversioned run files (listed there with their sha256), and its caption source
                                       (weeks, lender, menu, mu/beta-tilde)
  code/sim/out/sublet_v2/main/summary.json
                                       the confirmation's part main (versioned): table.<tag>.L-tr.<week>.0, the per-week
                                       r0 of the confirmation's rows (RC16(4); each checked against Table III v2's
                                       saving cell of its week, 100 (1 - r0))
  code/sim/out/e7c/analysis.json       X1, the causal runs (e7c_analysis.py, registered): per_policy.<lagged>.r0.weeks,
                                       the lagged trace cost of each policy (lag_minus_revealed.<lagged>.revealed names
                                       the row it belongs to)
  code/sim/out/e7r/analysis.json       X4, the baseline runs (e7r_analysis.py, registered): tags.<tag>.per_week.<week>
                                       {r0_tr, W0, RC}, of the rows MPC (tag MPC-T, the setting of rule T) and A9-P,
                                       and of the contract transplants (as_built_vs_c2: as built -> '-c2')
  code/sim/out/e7r/eval/summary.json   X4's part eval: the L-tr runs of the e7r rows (ALG, bl0a_usd), so that their
                                       overflow USD is the run's own and its bl0a_usd is checked equal to the table's
RUN_INPUTS are the three MS7 run outputs; figs/rebuild.py lists the float as pending while one is missing. A missing
input stops the script with exit code 2 and the file named.

Rows (ROWS; at most 16; w_spec: the confirmation's rows of Table III v2 without Sublet, one-way and Two-timescale PD,
plus MPC and protected-only critical-ratio renting), each by its registry label (style.TABLE_POLICIES_MS7["table3_v3"]).
Columns (COLUMNS), each the median over the weeks (statistics.median) of the per-week values:
  usd       USD per week in thousands, one decimal: overflow (total accounting in parentheses). Confirmation rows: Table III
            v2's per-week cells (checked: their medians equal Table III v2's printed medians). e7r rows: the eval run's
            ALG under L-tr (overflow), plus the week's own capacity, Table III v2's BL0a total minus overflow (the same
            for every policy, so a difference between two rows is the same in both accountings)
  r0        the trace cost r0 (overflow cost over the all-fallback bill under the trace lender), three decimals, with
            the min-max over the weeks below the median (RC16(4), C9;
            RANGE_COLS). Confirmation rows: main/summary.json's per-week r0; e7r rows: r0_tr; All-fallback 1 in every
            week (the reference, no range line). It replaces the column "Saving (%)" of w_spec §2.8, 100 (1 - r0): the
            median commutes with that map, so the column carries the same medians, sits next to the lagged r0 in the
            same unit, and leaves the width that the ranges need (the extract keeps saving_pct, not printed)
  lag_r0    the trace cost with every policy reading the previous slot's demand (X1), three decimals; "--" where the
            row has no lagged run (MPC, protected-only, All-fallback)
  RC        r0 under the trace lender minus r0 under the honoring lender, three decimals; "--" for All-fallback
  W0        the largest r0 over the five stress lenders, three decimals (All-fallback 1 by definition, Table III v2's),
            with the min-max over the weeks below the median (RANGE_COLS; none for All-fallback)
  W0_kbar   W0 of the row's rule with Algorithm 2's base contract kbar (X4's contract transplants, as_built_vs_c2),
            three decimals; "--" where no transplant ran (the rows that buy kbar already, the guarded and the tau >= 1 h
            rows, the e7r rows, All-fallback)
Every week of the confirmation must have a value where a cell has one (MissingKey otherwise, no partial median); the
weeks of the three analyses must be Table III v2's (StyleError).

Caption: the title from Table III v2's caption source (no experiment ID, as C52); a note of three lines (w_spec: medians
of per-week values, so r0 need not equal the ratio of the USD medians; the min-max below; "--" not run), with the
readings of the two new columns; on RetroRenting-style's row the lagged cell is RetroRenting-style, lagged, a primary
baseline without a row of its own, which the note says by its registry label (LAG_NAMED, checked against the e7c
analysis; C9; measured: the note's third line ends it).
Layout (RC16(4), as built): Table III v2's tabular* with its ragged name column and hanging indent (TABLE_ENV), the
name column NAME_COL_W (0.243 columnwidth: every name in at most two lines since C61 shortened protected-only
renting's label, the second line beside the ranges) and \\tabcolsep TABCOLSEP (1.6 pt), so that the two range
columns fit; each cell of RANGE_COLS is the median over the range in \\scriptsize, RANGE_GAP_PT closer than a line
(RANGE_MACRO, defined in the float); the USD header, wider than its numbers, extends left over the name column's empty
header (HEADER). The float compiles with the paper's class without an overfull box (tests/test_tables_ms7.py);
floats_heights.py --ms7 measures it (0.2577 page with the ranges on the confirmation, 0.2491 since C61, 0.2577 since
the MS7 print check's title, against Table III v2's 0.2767 and 0.1975 without them).

The extract {"table", "sources", "data"} holds every cell with its per-week values (and, for RANGE_COLS, min, max and
range_text), the caption source and the checks;
--from-extract rewrites the float from it alone (caption and note recomputed from caption_source), byte for byte. The
float goes to --out DIR, else SUBLET_FIGS_PDF_DIR when set, else paper/floats/; input from a reduced (smoke) run is
never written into paper/floats/ or code/sim/out/figs/ (SUBLET_FIGS_OUT_DIR must be set). Run from code/sim:
python -m figs.table3_v3 [--out DIR] [--from-extract [JSON]].
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
from figs.supp.ms5b_e7_lib import KEY_OF_TAG

NAME = "table3_v3"
LABEL = "tab:e7"
T3V2 = "code/sim/out/figs/table3_v2.json"
MAIN = "code/sim/out/sublet_v2/main/summary.json"      # RC16(4): the confirmation rows' per-week r0
E7C = "code/sim/out/e7c/analysis.json"
E7R = "code/sim/out/e7r/analysis.json"
E7R_EVAL = "code/sim/out/e7r/eval/summary.json"
RUN_INPUTS = (E7C, E7R, E7R_EVAL)        # the MS7 run outputs this table needs (figs/rebuild.py's MS7_PENDING)
INPUTS = (T3V2, MAIN) + RUN_INPUTS
FLOATS_DIR = style.REPO / "paper" / "floats"
DASH = t3.DASH
TRACE, HON = "L-tr", "L-hon"
# (tag, registry key, source): 'conf' a row of Table III v2, 'e7r' a tag of X4's analysis
ROWS = (("Sublet", "sublet_v2", "conf"), ("BL1-GP", "bl1_gp", "conf"), ("BL1N", "bl1n", "conf"),
        ("BL5N", "bl5n", "conf"), ("BL1", "bl1", "conf"), ("BL1-BO", "bl1_bo", "conf"), ("BL5-cur", "bl5_cur", "conf"),
        ("BL5-tau60", "bl5_tau60", "conf"), ("BL2", "bl2", "conf"), ("BL3-0", "bl3_0", "conf"), ("BL4", "bl4", "conf"),
        ("MPC-T", "mpc", "e7r"), ("A9-P", "a9p", "e7r"), ("BL0a", "bl0a", "conf"))
REFERENCE = "BL0a"
# rows whose "r_0, lagged" cell is a policy of its own, named in the note by its registry label (C9:
# RetroRenting-style, lagged, a primary baseline, has no row): row tag -> lagged tag,
# checked against the e7c analysis (lag_minus_revealed.<lagged>.revealed is the row, the lagged tag in its h1_set, the
# primary baselines) and named by ms5b_e7_lib.KEY_OF_TAG's key
LAG_NAMED = {"BL5-cur": "BL5"}
COLUMNS = (("usd", 1), ("r0", 3), ("lag_r0", 3), ("RC", 3), ("W0", 3), ("W0_kbar", 3))
RANGE_COLS = ("r0", "W0")        # RC16(4), C9: the median with the min-max over the weeks below it
SEED = "0"                       # main/summary.json's policy seed (Table III v2's caption source names it)


def _overhang(text: str) -> str:
    """A right-aligned header wider than its column's numbers, extending left over the name column's empty header."""
    return r"\multicolumn{1}{r}{\makebox[0pt][r]{" + text + "}}"


HEADER = (("", "Policy"), (_overhang("USD/week (k)"), _overhang("overflow (total)")), ("", "$r_0$"),
          ("$r_0$,", "lagged"), ("", "RC"), ("", "$W_0$"), ("$W_0$,", r"$\bar k$"))
NAME_COL_W = r"0.243\columnwidth"   # the names in at most two lines (protected-only renting's in three before C61)
TABCOLSEP = "1.6pt"                 # with NAME_COL_W, the widest cells fit the column (no overfull box)
RANGE_GAP_PT = 2.5                  # a range line this much closer to its median than a line of the table
RANGE_MACRO = r"\TableIVcell"       # defined in the float (\providecommand, local to the table environment)
TABLE_ENV = (r"\setlength{\tabcolsep}{" + TABCOLSEP + "}\n"
             r"\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}"
             r">{\raggedright\arraybackslash\hangindent=0.6em\hangafter=1}p{" + NAME_COL_W + r"}rccccc@{}}")
TABLE_END = t3.TABLE_END
REL_TOL = 1e-9                   # a recomputed median against a stored one; bl0a_usd of an e7r run against the table's
if tuple(k for _, k, _ in ROWS) != style.TABLE_POLICIES_MS7[NAME]:
    raise style.StyleError(f"{NAME}: ROWS must be style.TABLE_POLICIES_MS7[{NAME!r}] (C58)")


class MissingInput(SystemExit):
    """A required input file is missing (exit code 2, the file named)."""


# ---------------------------------------------------------------------------------------------------------------
# Inputs
def _json(inp: Inputs, name: str) -> Any:
    p = inp.path(name)
    if not p.is_file():
        what = "an MS7 run output (design/ms7/registration.md; copied in after the runs)" if name in RUN_INPUTS else \
            "a versioned result file"
        raise MissingInput(f"[{NAME}] required input {name} is missing under {inp.root} ({what})")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _close(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= REL_TOL * max(1.0, abs(float(b)))


def _median(by_week: Mapping[str, float], weeks: Sequence[str], what: str) -> float:
    missing = [w for w in weeks if by_week.get(w) is None]
    if missing:
        raise MissingKey(f"{what}: no value in weeks {missing} (no partial median)")
    return float(statistics.median(float(by_week[w]) for w in weeks))


def _cell(by_week: Mapping[str, float], weeks: Sequence[str], d: int, what: str, note: str | None = None) -> dict:
    by = {w: float(by_week[w]) for w in weeks if by_week.get(w) is not None}
    m = _median(by, weeks, what)
    return {"text": t3.tex_value(m, d), "value": m, "by_week": by, "note": note}


def _ranged(cell: dict, weeks: Sequence[str], d: int, show: bool = True) -> dict:
    """RC16(4): a cell of RANGE_COLS with the min and max of its per-week values; range_text is printed below the
    median (None for the reference, whose value is 1 in every week by definition)."""
    vals = [cell["by_week"][w] for w in weeks]
    cell["min"], cell["max"] = min(vals), max(vals)
    cell["range_text"] = f"{t3.tex_value(cell['min'], d)}--{t3.tex_value(cell['max'], d)}" if show else None
    return cell


def _dash(note: str) -> dict:
    return {"text": DASH, "value": None, "by_week": {}, "note": note}


def _usd_cell(ovf: Mapping[str, float], tot: Mapping[str, float], weeks: Sequence[str], what: str) -> dict:
    o, t = _median(ovf, weeks, f"{what} overflow"), _median(tot, weeks, f"{what} total")
    return {"text": f"{t3.tex_value(o * 1e-3, 1)} ({t3.tex_value(t * 1e-3, 1)})", "overflow": o, "total": t,
            "overflow_by_week": {w: float(ovf[w]) for w in weeks}, "total_by_week": {w: float(tot[w]) for w in weeks},
            "note": None}


def _conf_r0(main: Mapping, t2: Mapping, tag: str, weeks: Sequence[str]) -> dict:
    """RC16(4): a confirmation row's per-week r0 under the trace lender (main/summary.json, policy seed SEED; the
    reference's 1 in every week), each checked against Table III v2's saving cell of its week, 100 (1 - r0)."""
    sav = need(t2, "rows", tag, "cells", "saving_pct", "by_cell", what=T3V2)
    if tag == REFERENCE:
        r0 = {w: 1.0 for w in weeks}
    else:
        block = need(main, "table", tag, TRACE, what=MAIN)
        r0 = {}
        for w in weeks:
            v = block.get(w)
            v = v.get(SEED) if isinstance(v, Mapping) else v
            if v is None:
                raise MissingKey(f"{MAIN}: no r0 of {tag} under {TRACE} in week {w} (seed {SEED})")
            r0[w] = float(v)
    for w in weeks:
        s = sav.get(w)
        if s is None or abs(100.0 * (1.0 - r0[w]) - float(s)) > 1e-9 * max(1.0, abs(float(s))):
            raise style.StyleError(f"{MAIN}: r0 of {tag} in week {w} is {r0[w]}, Table III v2's saving {s} "
                                   "(another confirmation)")
    return r0


def _conf_cells(t2: Mapping, tag: str, weeks: Sequence[str]) -> dict:
    """A confirmation row's usd, saving_pct, RC and W0 from Table III v2's per-week cells, each median checked against
    the one Table III v2 prints."""
    row = need(t2, "rows", tag, "cells", what=T3V2)
    out = {}
    u = need(row, "usd", what=f"{T3V2} {tag}.usd")
    ovf, tot = need(u, "overflow", "by_cell", what=T3V2), need(u, "total", "by_cell", what=T3V2)
    out["usd"] = _usd_cell(ovf, tot, weeks, f"{T3V2} {tag}.usd")
    for k, d in (("overflow", "overflow"), ("total", "total")):
        if not _close(out["usd"][k], need(u, d, "median", what=T3V2)):
            raise style.StyleError(f"{T3V2}: {tag}'s {k} median {u[d]['median']} is not the median of its weeks")
    for col, d in (("saving_pct", 1), ("RC", 3), ("W0", 3)):
        c = need(row, col, what=f"{T3V2} {tag}.{col}")
        if c.get("value") is None:
            out[col] = _dash(c.get("note") or "no value in Table III v2")
            continue
        out[col] = _cell(need(c, "by_cell", what=T3V2), weeks, d, f"{T3V2} {tag}.{col}", c.get("note"))
        if not _close(out[col]["value"], c["value"]):
            raise style.StyleError(f"{T3V2}: {tag}'s {col} median {c['value']} is not the median of its weeks")
    return out


def _lag_map(e7c: Mapping) -> dict:
    """{revealed tag: lagged tag} from the analysis's lag_minus_revealed (its 'revealed' names the row)."""
    out = {}
    for lagged, row in need(e7c, "lag_minus_revealed", what=E7C).items():
        rev = need(row, "revealed", what=f"{E7C} lag_minus_revealed.{lagged}")
        if rev in out:
            raise style.StyleError(f"{E7C}: two lagged policies ({out[rev]}, {lagged}) of the row {rev}")
        out[rev] = lagged
    return out


def _e7r_week(e7r: Mapping, tag: str, weeks: Sequence[str], field: str) -> dict:
    pw = need(e7r, "tags", tag, "per_week", what=E7R)
    out = {}
    for w in weeks:
        v = (pw.get(w) or {}).get(field)
        if isinstance(v, Mapping):
            v = v.get(TRACE)
        if v is not None:
            out[w] = float(v)
    return out


def build(inp: Inputs) -> dict:
    payload = _json(inp, T3V2)
    if payload.get("table") != "table3_v2":
        raise style.StyleError(f"{T3V2} is the extract of {payload.get('table')!r}, not 'table3_v2'")
    t2 = need(payload, "data", what=T3V2)
    cs = need(t2, "caption_source", what=T3V2)
    weeks = [str(w) for w in need(cs, "weeks", what=T3V2)]
    main = _json(inp, MAIN)
    e7c, e7r, ev = _json(inp, E7C), _json(inp, E7R), _json(inp, E7R_EVAL)
    for what, ws in ((E7C, (e7c.get("meta") or {}).get("weeks")), (E7R, e7r.get("weeks"))):
        if [str(w) for w in (ws or [])] != weeks:
            raise style.StyleError(f"{what}: the weeks {ws} are not Table III v2's {weeks}")
    lag_of = _lag_map(e7c)
    primary = set(need(e7c, "h1_set", what=E7C))
    lag_named = []
    for row, lagged in LAG_NAMED.items():
        if lag_of.get(row) != lagged:
            raise style.StyleError(f"{E7C}: the lagged policy of the row {row} is {lag_of.get(row)}, not {lagged} "
                                   "(lag_minus_revealed)")
        if lagged not in primary:
            raise style.StyleError(f"{E7C}: {lagged} is not in h1_set {sorted(primary)} (the primary baselines)")
        lag_named.append({"row": row, "row_label": style.policy(dict((t, k) for t, k, _ in ROWS)[row]).label,
                          "lagged": lagged, "label": style.policy(KEY_OF_TAG[lagged]).label, "primary": True})
    c2_of = {need(p, "as_built", what=E7R): need(p, "c2", what=E7R) for p in need(e7r, "as_built_vs_c2", what=E7R)}
    per_lag = need(e7c, "per_policy", what=E7C)
    bl0a = {w: float(v) for w, v in need(t2, "rows", REFERENCE, "cells", "usd", "overflow", "by_cell",
                                         what=T3V2).items()}
    bl0a_tot = {w: float(v) for w, v in need(t2, "rows", REFERENCE, "cells", "usd", "total", "by_cell",
                                             what=T3V2).items()}
    own = {w: bl0a_tot[w] - bl0a[w] for w in weeks}
    for tag, _, src in ROWS:     # own capacity is the same for every policy (the e7r rows' totals rest on it)
        u = need(t2, "rows", tag, "cells", "usd", what=T3V2) if src == "conf" else None
        for w in (weeks if u else ()):
            o, t = u["overflow"]["by_cell"].get(w), u["total"]["by_cell"].get(w)
            if o is not None and t is not None and abs(float(t) - float(o) - own[w]) > 1e-6 * max(1.0, own[w]):
                raise style.StyleError(f"{T3V2}: {tag}'s own capacity in week {w} is {float(t) - float(o)}, BL0a's "
                                       f"{own[w]} (the e7r rows' total accounting needs one value per week)")
    eval_rows = {(r["tag"], r["mode"], str(r["cell"]), int(r["seed"])): r for r in need(ev, "runs", what=E7R_EVAL)
                 if r.get("kind") == "week"}
    rows: dict = {}
    for tag, key, src in ROWS:
        what = f"{tag} ({style.policy(key).label})"
        if src == "conf":
            cells = _conf_cells(t2, tag, weeks)
            r0 = _conf_r0(main, t2, tag, weeks)
            cells["r0"] = _cell(r0, weeks, 3, f"{MAIN} table.{tag}.{TRACE}",
                                "1 in every week (the reference)" if tag == REFERENCE else None)
        else:
            r0 = _e7r_week(e7r, tag, weeks, "r0_tr")
            ovf = {}
            for w in weeks:
                run = eval_rows.get((tag, TRACE, w, 0))
                if run is None or run.get("ALG") is None or run.get("status") != "ok":
                    raise MissingKey(f"{E7R_EVAL}: no ok {tag} run under {TRACE} in week {w}")
                if not _close(run["bl0a_usd"], bl0a[w]):
                    raise style.StyleError(f"{E7R_EVAL}: bl0a_usd of {tag} in week {w} is {run['bl0a_usd']}, "
                                           f"Table III v2's {bl0a[w]} (another week instance)")
                if w in r0 and not _close(float(run["ALG"]) / float(run["bl0a_usd"]), r0[w]):
                    raise style.StyleError(f"{E7R}: r0_tr of {tag} in week {w} is not its eval run's ALG/bl0a_usd")
                ovf[w] = float(run["ALG"])
            cells = {"usd": _usd_cell(ovf, {w: ovf[w] + own[w] for w in weeks}, weeks, f"{E7R_EVAL} {tag}")}
            cells["saving_pct"] = _cell({w: 100.0 * (1.0 - v) for w, v in r0.items()}, weeks, 1, f"{E7R} {tag}.r0_tr")
            cells["r0"] = _cell(r0, weeks, 3, f"{E7R} {tag}.r0_tr")
            cells["RC"] = _cell(_e7r_week(e7r, tag, weeks, "RC"), weeks, 3, f"{E7R} {tag}.RC.{TRACE}")
            cells["W0"] = _cell(_e7r_week(e7r, tag, weeks, "W0"), weeks, 3, f"{E7R} {tag}.W0")
        for col in RANGE_COLS:                    # RC16(4): min-max over the weeks (not for the reference)
            _ranged(cells[col], weeks, 3, show=tag != REFERENCE)
        lagged = lag_of.get(tag)
        if lagged is None:
            cells["lag_r0"] = _dash("no lagged run (X1 ran the confirmation's policies)" if tag != REFERENCE else
                                    "an analytic reference")
        else:
            cells["lag_r0"] = _cell(need(per_lag, lagged, "r0", "weeks", what=E7C), weeks, 3,
                                    f"{E7C} per_policy.{lagged}.r0", f"lagged tag {lagged}")
        c2 = c2_of.get(tag)
        if c2 is None:
            cells["W0_kbar"] = _dash("no contract transplant (X4 transplanted the as-built baselines that buy k*)")
        else:
            cells["W0_kbar"] = _cell(_e7r_week(e7r, c2, weeks, "W0"), weeks, 3, f"{E7R} {c2}.W0", f"transplant {c2}")
        rows[tag] = {"label": style.policy(key).label, "style_key": key, "source": src, "lagged": lagged, "c2": c2,
                     "cells": cells}
    missing_rows = sorted(t for t in lag_of if t not in rows and t not in ("A9",))
    cap = {"weeks": weeks, "n_weeks": len(weeks), "lender": cs.get("lender"), "menu": cs.get("menu"),
           "mu_over_beta_tilde": cs.get("mu_over_beta_tilde"), "seed": cs.get("seed"),
           "e7r_rows": {t: rows[t]["label"] for t, _, s in ROWS if s == "e7r"},
           "mpc_setting": (need(e7r, "tags", "MPC-T", what=E7R).get("role")),
           "lag_rows": {t: r["lagged"] for t, r in rows.items() if r["lagged"]},
           "lag_named": lag_named,
           "c2_rows": {t: r["c2"] for t, r in rows.items() if r["c2"]}}
    title, note = caption_parts(cap)
    reduced = {"table3_v2": bool((t2.get("meta") or {}).get("reduced")),
               "main": bool((main.get("meta") or {}).get("reduced")),
               "e7c": bool((e7c.get("meta") or {}).get("reduced")), "e7r": bool((e7r.get("meta") or {}).get("reduced")),
               "e7r_eval": bool((ev.get("meta") or {}).get("reduced"))}
    notes = {f"{t}.{c}": cell["note"] for t, r in rows.items() for c, cell in r["cells"].items()
             if cell["text"] == DASH or cell.get("note")}
    return {"order": [t for t, _, _ in ROWS], "rows": rows, "columns": [c for c, _ in COLUMNS],
            "header": [list(h) for h in HEADER], "caption": title, "note": note,
            "labels": {"caption": f"{title} {note}"}, "caption_source": cap, "notes": notes,
            "lagged_policies_without_row": missing_rows,
            "own_capacity_usd": own,
            "checks": {"e7c": {"registration_matches": ((e7c.get("meta") or {}).get("registration") or {})
                               .get("matches"),
                               "weeks_are_confirmation_weeks": (e7c.get("meta") or {}).get(
                                   "weeks_are_confirmation_weeks"),
                               "gate_pass": (e7c.get("gate") or {}).get("pass")},
                       "e7r": {"identity_all_identical": ((e7r.get("checks") or {}).get("identity_summary") or {})
                               .get("all_identical"), "script_sha256": (e7r.get("meta") or {}).get("script_sha256")}},
            "tables": {f"{NAME}.tex": {"scope": {"tags": [t for t, _, _ in ROWS], "keys": [k for _, k, _ in ROWS],
                                                 "weeks": weeks, "modes": [TRACE, HON, "the five stress modes"],
                                                 "seeds": [cs.get("seed")]}}},
            "statistic": "statistics.median over the weeks of the per-week values (no interval: design/ms7/plan.md D4); "
                         "for r0 and W0 also their min and max over the weeks (RC16(4), C9)",
            "meta": {"reduced": any(reduced.values()), "reduced_by_input": reduced,
                     "git_revisions": {"table3_v2": (t2.get("meta") or {}).get("git_revision"),
                                       "main": (main.get("meta") or {}).get("git_revision"),
                                       "e7c": (e7c.get("meta") or {}).get("git_revision"),
                                       "e7r": (e7r.get("meta") or {}).get("git_revision"),
                                       "e7r_eval": (ev.get("meta") or {}).get("git_revision")},
                     "inputs_sha256": {n: hashlib.sha256(inp.path(n).read_bytes()).hexdigest() for n in INPUTS},
                     "sources": list(INPUTS)},
            "sources": list(inp.sources)}


# ---------------------------------------------------------------------------------------------------------------
# Caption and float
def caption_parts(cap: Mapping) -> tuple[str, str]:
    """(title, note): the title as Table III v2's (C52: no policy seed, no experiment ID), which since the MS7 print
    check (2026-11-11) names the lender of every column ("trace lender except W0, the worst stress lender": W0 is the
    largest r0 over the stress lenders, Section VII-A); the note of three lines (two before C9, which named the lagged
    cell that is a primary baseline of its own, cap's lag_named, by its registry label; measured:
    tests/test_tables_ms7.py). RC16(4): its first sentence says that the cells are medians of per-week
    values (so r0 need not equal the ratio of the USD medians) with the min-max below; the longer "Medians over weeks,
    min-max below; r0 need not match the USD medians." set the note in four lines (0.0085 page more)."""
    n, w = cap["n_weeks"], t3.weeks_text(cap["weeks"])
    title = ("End-to-end cost per policy, "
             + (f"medians of {n} confirmation weeks" if n > 1 else "the confirmation week")
             + f" ({w.split(' ', 1)[1]}; {cap['lender']} lender except $W_0$, the worst stress lender; "
               f"{cap['menu']} menu, $\\mu/\\tilde\\beta={float(cap['mu_over_beta_tilde']):g}$).")
    named = "".join(f" ({r['row_label']}'s row: {r['label']}" + (", a primary baseline" if r.get("primary") else "")
                    + ")" for r in cap.get("lag_named") or [])
    note = (r"Medians of per-week values, min--max below. $r_0$, lagged: demand one slot late"
            + named + r". $W_0$, $\bar k$: with Algorithm~2's base contract. " + DASH + ": not run.")  # 3 lines
    return title, note


def cell_tex(cell: Mapping) -> str:
    """A cell as the float prints it: its text, or (RC16(4)) RANGE_MACRO's median over the range."""
    rt = cell.get("range_text")
    return cell["text"] if not rt else f"{RANGE_MACRO}{{{cell['text']}}}{{{rt}}}"


def float_tex(data: Mapping) -> str:
    meta = data["meta"]
    revs = meta.get("git_revisions") or {}
    lines = [
        "% Table IV (MS7, design/ms7/w_spec.md §2.8, unit W-G2; change C58). Written by code/sim/figs/table3_v3.py from",
        "% code/sim/out/figs/table3_v2.json and sublet_v2/main/summary.json (the confirmation's rows),",
        "% code/sim/out/e7c/analysis.json (lagged r0) and",
        "% code/sim/out/e7r/ (MPC, protected-only renting, the contract transplants); do not edit. Revisions: "
        + ", ".join(f"{k} {v}" for k, v in revs.items()) + ".",
        "% Rows: style.TABLE_POLICIES_MS7['table3_v3'] by registry label; medians over the weeks of per-week values,",
        "% r0 and W0 with their min-max over the weeks below (RC16(4));",
        "% the per-week values in the extract code/sim/out/figs/table3_v3.json. Cites nothing. Needs booktabs and array."]
    if meta.get("reduced"):
        lines.append("% REDUCED INPUT (meta.reduced true): a smoke run, not a result.")
    lines += [r"\begin{table}[t]", r"\providecommand{" + RANGE_MACRO + r"}[2]{\begin{tabular}[t]{@{}c@{}}#1\\["
              + f"-{RANGE_GAP_PT:g}pt" + r"]{\scriptsize #2}\end{tabular}}%",
              r"\caption{" + data["caption"] + "}", r"\label{" + LABEL + "}", r"\centering\footnotesize", TABLE_ENV,
              r"\toprule"]
    head = data["header"]
    lines.append(" & ".join(h[0] for h in head) + r" \\")
    lines.append(" & ".join(h[1] for h in head) + r" \\")
    lines.append(r"\midrule")
    for tag in data["order"]:
        r = data["rows"][tag]
        lines.append(" & ".join([r["label"]] + [cell_tex(r["cells"][c]) for c in data["columns"]]) + r" \\")
    lines += [r"\bottomrule", TABLE_END + r"\par\vspace{2pt}",
              r"\parbox{\columnwidth}{\footnotesize\raggedright " + data["note"] + "}", r"\end{table}"]
    return "\n".join(lines) + "\n"


def float_dir(out: str | os.PathLike | None) -> Path:
    """--out, else SUBLET_FIGS_PDF_DIR when set (scratch builds and tests), else paper/floats/."""
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
    """code/sim/out/figs/table3_v3.json (SUBLET_FIGS_OUT_DIR)."""
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
            data["labels"] = {**data.get("labels", {}), "caption": f"{data['caption']} {data['note']}"}
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
