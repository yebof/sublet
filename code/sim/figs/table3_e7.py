"""Table III: E7 per policy (design/sim_spec_ms4.md §9; design/figure_plan.md §2), the float paper/floats/table3_e7.tex.

Reads code/sim/out/e7/table3.json (written by E7's main summary job from the four part summaries, sim_spec_ms4 §3.10)
through figs.inputs, so that SUBLET_FIGS_IN_ROOT redirects it, and writes a complete IEEEtran `table` float with
booktabs and \\footnotesize (as the mock pages use them): the rows of `order` in that order (Sublet, BL5, BL1, BL2,
BL4, A7, A7 + guard, A6, BL0b, BL0a), each named by its style.POLICIES label (the label table3.json records must be
the same), and the columns of §9, each cell the median of table3.json rows.<tag>.<column>:
  1. USD per week in thousands with one decimal, overflow accounting with the total accounting in parentheses (M2);
  2. saving over BL0a in percent, overflow accounting, one decimal below 100% in magnitude, none above (BL0b's saving
     is about -3,700%, so that its cell stays narrow);
  3. the gap column, ALG / merged LP bound on the 1-day slow-grid reruns with the e7r menu (an upper bound on the
     ratio to OPT(sigma, omega), Propositions M4 and M6; M39), two decimals, headed "ALG/LB"; its label "slow grid,
     e7r menu" is in the caption's scope sentence, since in the header it would widen the column past
     \\columnwidth;
  4. the fallback share after reclaims, two decimals;
  5. W0, the worst cost over BL0a under the five stress modes, two decimals;
  6. the share of the 12 trace week runs with an abort (M24), two decimals.
Columns 3-6 are centered (their cells have one width), so that they keep apart under their two-line headers. The
names stay on one line each; at \\footnotesize with 3.5 pt between the columns a table of real-scale cells (USD in
hundreds of thousands, BL0b's saving in thousands of percent) is \\columnwidth wide. A null cell prints "--" (an en
dash) and its note goes to the extract. Medians only: the intervals and counts are in
the supplementary table3_intervals.tex (sf_e7_mix) and e7/main/tables.md (M25). The caption gives the scope, Sublet's
MS4 allowance (B0 = 10% of the all-fallback bill, gamma = 1; M36) and the certificate count over every A8 run of E7
(N of N certificates held, with the W(a), W(b) and W(c) counts), every number from table3.json's `caption` block (a
null count, or a part summary of E7 left out of the count, raises MissingKey rather than print a partial count); the
column definitions beyond the header are left to the Section VII text (M27). The float cites nothing.

The extract code/sim/out/figs/table3_e7.json (SUBLET_FIGS_OUT_DIR) holds every cell as printed, its value and note,
the caption and the sources; --from-extract rewrites the float from it alone. The float goes to paper/floats/ unless
--out DIR is given (tests); a table3.json of a reduced run (meta.reduced) is never written into paper/floats/.

Run from code/sim: python -m figs.table3_e7 [--out DIR] [--from-extract [JSON]].
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Mapping, Sequence

from figs import style
from figs.common import MissingKey, need
from figs.inputs import Inputs

NAME = "table3_e7"
T3 = "code/sim/out/e7/table3.json"
FLOATS_DIR = style.REPO / "paper" / "floats"
DASH = "--"                     # a null cell: an en dash in LaTeX
# (table3.json column, decimals, scale) of the six columns of §9, in order; usd prints "overflow (total)"
COLUMNS = (("usd", 1, 1e-3), ("saving_pct", 1, 1.0), ("gap", 2, 1.0), ("fallback_share_after_reclaims", 2, 1.0),
           ("W0", 2, 1.0), ("abort_share", 2, 1.0))
# the header, two lines per column (§9; the definitions beyond it are in the Section VII text, M27); the gap column's
# label "slow grid, e7r menu" is in the caption's scope sentence, where it costs no column width
HEADER = (("", "Policy"), ("USD/week (k)", "overflow (total)"), ("Saving", r"(\%)"), ("ALG/", "LB"),
          ("Fallback", "after recl."), ("", "$W_0$"), ("Abort", "share"))
# the names on one line each (l), USD and saving right-aligned, the two-decimal columns centered, 3.5 pt between
# columns: at \footnotesize the widest name and the widest cells of a real-scale table fit \columnwidth
# (tests/test_floats_ms4.py compiles the float without an overfull box)
TABLE_ENV = r"\setlength{\tabcolsep}{1.75pt}" "\n" r"\begin{tabular}{@{}lrrcccc@{}}"
SAVING_DECIMALS_BELOW = 100.0   # saving (%) with one decimal below 100 in magnitude, without decimals above
HORIZON_WORDS = {10080: "one week", 1440: "one day"}


def tex_value(v: float | None, d: int) -> str:
    """A number with d decimals, a negative sign as a math minus; DASH for a missing value."""
    if v is None:
        return DASH
    s = f"{float(v):.{d}f}"
    if float(s) == 0.0:
        s = s.lstrip("-")                                # no "-0.0"
    return "$-$" + s[1:] if s.startswith("-") else s


def _cell(rows: Mapping, tag: str, col: str) -> Mapping:
    ent = need(rows, tag, col, what=f"{T3} rows")
    if not isinstance(ent, Mapping):
        raise MissingKey(f"{T3}: rows.{tag}.{col} is {type(ent).__name__}, not a cell")
    return ent


def row_cells(rows: Mapping, tag: str) -> dict:
    """{column: {text, value(s), note}} of one row, as printed."""
    out = {}
    for col, d, scale in COLUMNS:
        if col == "usd":
            ovf, tot = (need(rows, tag, "usd", k, what=f"{T3} rows") for k in ("overflow", "total"))
            vo, vt = ovf.get("median"), tot.get("median")
            if vo is None:
                text = DASH
            else:
                text = tex_value(vo * scale, d) + ("" if vt is None else f" ({tex_value(vt * scale, d)})")
            note = "; ".join(f"{k}: {e.get('note')}" for k, e in (("overflow", ovf), ("total", tot))
                             if e.get("note"))
            out[col] = {"text": text, "overflow": vo, "total": vt, "note": note or None}
        else:
            e = _cell(rows, tag, col)
            v = e.get("median")
            if col == "saving_pct" and v is not None and abs(v) >= SAVING_DECIMALS_BELOW:
                d = 0                                    # BL0b's saving is about -3,700% (38 times BL0a)
            out[col] = {"text": tex_value(None if v is None else v * scale, d), "value": v, "n": e.get("n"),
                        "note": e.get("note")}
    return out


def share_text(rule: str) -> str:
    """'0.1*BL0a' -> '10\\%' (the allowance's share of BL0a in percent)."""
    m = re.fullmatch(r"\s*([0-9.]+)\s*\*\s*BL0a\s*", str(rule))
    if m is None:
        raise MissingKey(f"{T3}: caption.B0_rule {rule!r} is not of the form '<share>*BL0a'")
    return f"{100.0 * float(m.group(1)):g}" + r"\%"


def caption_text(cap: Mapping, sources: Mapping | None = None) -> str:
    """Scope, allowance and certificate count (§9; M27), every number from table3.json's caption block: the counts
    n, held and each case's runs are required (a null raises MissingKey, never a printed 0), and so is every part of E7
    (caption.certificates.parts_counted, and meta.sources.<part>.used where `sources` is given): a count over some
    parts only is not the count over every A8 run of E7 that the caption states."""
    scope = need(cap, "scope", what=f"{T3} caption")
    h = float(need(scope, "horizon_min", what=f"{T3} caption.scope"))
    horizon = HORIZON_WORDS.get(int(h), f"{h:g} min") if h.is_integer() else f"{h:g} min"
    menu = str(need(scope, "menu", what=f"{T3} caption.scope")).split(" (")[0]
    lender = need(scope, "lender", what=f"{T3} caption.scope")
    mu = float(need(scope, "mu_over_beta_tilde", what=f"{T3} caption.scope"))
    na, ns = len(scope.get("alignments") or []), len(scope.get("policy_seeds") or [])
    gamma = float(need(cap, "gamma", what=f"{T3} caption"))
    cert = need(cap, "certificates", what=f"{T3} caption")
    counted = need(cert, "parts_counted", what=f"{T3} caption.certificates")
    unused = sorted(k for k, v in (sources or {}).items() if isinstance(v, Mapping) and v.get("used") is False)
    missing = sorted(k for k, v in counted.items() if not k.endswith("_note") and v is not True)
    if missing or unused:
        raise MissingKey(f"{T3}: the certificate count leaves out E7 part(s) {sorted(set(missing) | set(unused))} "
                         "(caption.certificates.parts_counted, meta.sources.<part>.used): rebuild table3.json from "
                         "all four part summaries")
    n_runs, held = (int(need(cert, k, what=f"{T3} caption.certificates")) for k in ("n", "held"))
    cases = ", ".join(f"{c} {int(need(cert, 'by_case', c, 'runs', what=f'{T3} caption.certificates'))}"
                      for c in ("W(a)", "W(b)", "W(c)"))
    return (f"{horizon[:1].upper()}{horizon[1:]}, {menu} menu, {lender} lender, $\\mu/\\tilde\\beta={mu:g}$, medians of "
            f"{na} alignment{'s' if na != 1 else ''} $\\times$ {ns} seed{'s' if ns != 1 else ''} (ALG/LB: "
            f"reruns on the slow grid, e7r menu). Guarded rows: $\\gamma={gamma:g}$, $B_0$ = "
            f"{share_text(need(cap, 'B0_rule', what=f'{T3} caption'))} of all-fallback; "
            f"{held} of {n_runs} certificates held ({cases}).")


def build(inp: Inputs) -> dict:
    t3 = inp.json(T3)
    order = list(need(t3, "order", what=T3))
    rows = need(t3, "rows", what=T3)
    out_rows = {}
    for tag in order:
        key = need(rows, tag, "style_key", what=f"{T3} rows")
        label = style.policy(key).label
        recorded = rows[tag].get("label")
        if recorded is not None and recorded != label:
            raise MissingKey(f"{T3}: rows.{tag}.label {recorded!r} is not the style.POLICIES label {label!r}")
        out_rows[tag] = {"label": label, "style_key": key, "cells": row_cells(rows, tag)}
    cap = need(t3, "caption", what=T3)
    meta = t3.get("meta") if isinstance(t3.get("meta"), Mapping) else {}
    notes = {f"{tag}.{col}": c["note"] for tag, r in out_rows.items() for col, c in r["cells"].items()
             if c["text"] == DASH or c.get("note")}
    return {"order": order, "rows": out_rows, "columns": [c for c, _, _ in COLUMNS], "header": [list(h) for h in HEADER],
            "caption": caption_text(cap, meta.get("sources") if isinstance(meta.get("sources"), Mapping) else None),
            "caption_source": cap, "notes": notes,
            "column_definitions": t3.get("columns"),
            "meta": {"git_revision": meta.get("git_revision"), "reduced": bool(meta.get("reduced", False)),
                     "sources": meta.get("sources")},
            "sources": list(inp.sources)}


def float_tex(data: Mapping) -> str:
    """The float paper/floats/table3_e7.tex."""
    rev = data["meta"].get("git_revision")
    lines = [
        "% Table III: E7 per policy (design/sim_spec_ms4.md §9; design/figure_plan.md §2). Written by "
        "code/sim/figs/table3_e7.py",
        f"% from code/sim/out/e7/table3.json (git revision {rev}); do not edit. Rows and names: style.POLICIES "
        "labels; columns:",
        "% USD per week in thousands, overflow (total) accounting; saving over BL0a (%, overflow); ALG / merged LP "
        "bound,",
        "% slow grid, e7r menu (an upper bound on the gap, M39); fallback share after reclaims; W0; share of runs with "
        "an abort.",
        "% Medians; intervals and counts in paper/supplement/tables/table3_intervals.tex. Cites nothing. Needs "
        "booktabs and array."]
    if data["meta"].get("reduced"):
        lines.append("% REDUCED INPUT (meta.reduced true): a smoke run, not a result.")
    lines += [r"\begin{table}[t]", r"\caption{" + data["caption"] + "}", r"\label{tab:e7}",
              r"\centering\footnotesize", TABLE_ENV, r"\toprule"]
    head = data["header"]
    lines.append(" & ".join(h[0] for h in head) + r" \\")
    lines.append(" & ".join(h[1] for h in head) + r" \\")
    lines.append(r"\midrule")
    for tag in data["order"]:
        r = data["rows"][tag]
        lines.append(" & ".join([r["label"]] + [r["cells"][c]["text"] for c in data["columns"]]) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines) + "\n"


def write_float(data: Mapping, out_dir: Path) -> Path:
    if data["meta"].get("reduced") and Path(out_dir).resolve() == FLOATS_DIR.resolve():
        raise SystemExit(f"{NAME}: {T3} is from a reduced run (meta.reduced); it is not written into {FLOATS_DIR} "
                         "(give --out DIR)")
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / f".{NAME}.tex.partial"
    tmp.write_text(float_tex(data), encoding="utf-8")
    os.replace(tmp, out_dir / f"{NAME}.tex")
    return out_dir / f"{NAME}.tex"


def write_extract(data: Mapping, sources: Sequence[str]) -> Path:
    """code/sim/out/figs/table3_e7.json (SUBLET_FIGS_OUT_DIR): every printed cell with its value and note."""
    _, out = style.output_dirs()
    out.mkdir(parents=True, exist_ok=True)
    payload = {"table": NAME, "sources": [style.check_source(s) for s in sources],
               "data": {k: v for k, v in data.items() if k != "sources"}}
    tmp = out / f".{NAME}.json.partial"
    tmp.write_text(json.dumps(payload, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, out / f"{NAME}.json")
    return out / f"{NAME}.json"


def main(argv: Sequence[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(prog=f"python -m figs.{NAME}", description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=None, metavar="DIR", help=f"folder of the float (default {FLOATS_DIR})")
    ap.add_argument("--from-extract", nargs="?", const="", default=None, metavar="JSON",
                    help=f"rewrite the float from the extract alone (default code/sim/out/figs/{NAME}.json under the "
                         "input root)")
    args = ap.parse_args(argv)
    if args.from_extract is None:
        inp = Inputs()
        data = json.loads(json.dumps(build(inp), allow_nan=False))
        sources = list(inp.sources)
    else:
        if args.from_extract:
            payload = json.loads(Path(args.from_extract).read_text(encoding="utf-8"))
        else:
            payload = Inputs().json(f"code/sim/out/figs/{NAME}.json")
        if payload.get("table") != NAME:
            raise style.StyleError(f"{args.from_extract or NAME} is the extract of {payload.get('table')!r}, "
                                   f"not {NAME!r}")
        data, sources = dict(payload["data"]), list(payload.get("sources") or [])
    data["sources"] = sources
    tex = write_float(data, Path(args.out) if args.out else FLOATS_DIR)
    ext = write_extract(data, sources)
    print(f"[{NAME}] wrote {tex} and {ext} ({len(data['order'])} rows, {len(data['notes'])} cell notes)")
    return {"tex": str(tex), "json": str(ext), "data": data}


if __name__ == "__main__":
    main(sys.argv[1:])
