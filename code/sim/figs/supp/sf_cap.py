"""sf_cap: Sublet against the naive spend caps of the MS8 budget-cap runs (X6) on the confirmation weeks and at five
sensitivity points, with the tables cap_runs.tex, cap_modes.tex, cap_sens.tex and cap_checks.tex and the data file
cap_runs.csv
(design/ms8/plan.md D2, D4, W; design/ms8/registration.md §2 and §3, X6).

Claims: none of its own. Every number is read from the registered analysis of the budget-cap runs (e7b_analysis.py, its
sha256 in design/ms8/registration.md): medians and min-max over weeks, counts of runs and weeks, no interval and no
p-value (D4; registration §3). The margins follow the confirmation's convention: a policy's value minus the
reference's in the same week, positive when the reference costs less (a win of the reference), a week in which the
cap or the reference has no run counted as the reference's loss ('+m').

Figure (W2 x 2.5 in, style.py's MS8 unit F6 block). One question: what does a spend cap that leaves out a term of
Algorithm 1's test cost, and does it keep the line FB + B that Sublet keeps? Sublet and the seven caps
(SUPP_POLICIES_MS8[NAME]; the references A9, BL1 and BL1-GP are in the tables), a two-row legend over four panels:
  (a) part week, Sublet and the caps but the latched and the slot-count cap B(t) (A_DROP: in (b)-(d) and the tables;
      review of unit F6, finding 6), per lender mode (the thirteen of part week in the supplement's order: the trace
      and the honoring lender, the five stress lenders of the confirmation, the six new ones): the median over the
      weeks of r0 (its min-max per lender in tab:cap-modes), and per week the worst cases W0 (the largest r0 over the
      five stress lenders) and W0+ (over the eleven): the median with its min-max as a bar; the series dodged within
      each column; the grey line marks the all-fallback cost (r0 = 1); the value axis clear of the markers
      (marker_pad);
  (b) both parts, every run of each policy: its run-time excess max_t ALG(t) - FB(t) - B(t) over FB(T) (the analysis's
      runtime_rel: from E7b's per-slot series, or, for a frozen guarded run of Sublet, its envelope, an upper bound on
      the run-time excess when the safe expert followed all-fallback), one column per policy, the runs spread
      sideways by a fixed rule (strip_offsets); the region above 0, where a run is above the bound at some slot, shaded;
      under each column, rotated, the runs above the bound at some slot (out of the runs with a value, in the axis
      label when every column has the same number, else under each column), the markers part transparent
      (STRIP_ALPHA), and over each
      column, in a strip of GLYPH_ROOM_PT above the shaded region, the policy's legend glyph at full size; the y axis
      linear within +-LINTHRESH_B and logarithmic beyond (ticks at 1, 2 and 5 per decade), from the data's least value; The bound is Sublet's FB + B for every column, also for a
      cap whose own limit X is another (cap 0, cap 5%), as the analysis defines it;
  (c), (d) part sens, one row per point (fee4, fee8, fee16, slow1, scen_cold_wan_1gbps, in that order), Sublet and the
      caps at X = B(t): (c) the median r0 under the trace lender over the point's weeks with an L-tr run, (d) the
      median W0 over the weeks with a value of W0 (the stress lenders run there on fewer weeks; sens_weeks), each with
      its min-max; the series dodged within each row; the grey line at 1; the value axis from a tick at or below the
      smallest value where that costs little room (nice_axis), clear of the markers. Without any run at the points,
      (c) says "No runs" and (d) is empty.
Panel titles at the caption size on their letters' baseline (C62); the mode names as the supplement's tables print
them (ms7_e7r_lib.mode_text). labels.caption is a caption draft with every count read from the analysis; its statement
on Sublet follows readings.R1.sublet_violations (the analysis's scope: above at the end, above at some slot by the
series, or an envelope violation), whatever its count.

Tables (after hook, figs.common.write_table: SUBLET_FIGS_TABLES_DIR, else SUBLET_FIGS_PDF_DIR when set, else
paper/supplement/tables/), from the extract's `tables`, so --from-extract rewrites them; each entry carries a `scope`:
  cap_runs.tex    three longtables: (1) part week, per policy (Sublet, the seven caps, A9, BL1 and BL1-GP) the median
                  and min-max over the weeks of r0 under L-tr, W0 and W0+ (the analysis's per_tag and W), its runs
                  above the bound out of its runs (summed over the modes of per_tag), and its largest final and
                  run-time excess over FB(T), the run-time one with (n/N) where only n of its N runs have a value
                  (an unguarded frozen run has none); (2) part week, per cap and reference (Sublet; BL1-GP also for
                  the greedy caps) the paired margins on r0 under L-tr, W0 and W0+ (W/T/L, +m; median and min-max; a
                  cap without any run: every week missing), with the median share of the inner policy's saving that
                  the cap keeps (inner.all.kept_share) and the cells of reading R3 in part week where the cap costs
                  less than Sublet; (3) per part and point and cap, the binds (median and min-max of bind_slots over
                  the runs), the latched runs, the kept share per mode class (trace, stress, other, all) and the runs
                  whose inner policy saved nothing;
  cap_modes.tex   two longtables on part week, per lender (the columns of the supplement's e7r_modes): every tag's
                  r0 (median over min-max), and every cap's paired margin per lender against each reference (the
                  analysis's r0:<mode>; W/T/L over the median);
  cap_sens.tex    part sens, per point (with its weeks under L-tr and its weeks of W0) and policy: the median and
                  min-max of r0 under L-tr and of W0, the runs above the bound, the largest final and run-time excess,
                  and a cap's margins against Sublet on r0 under L-tr and W0, for a greedy cap on a second line
                  against BL1-GP; every cap has a row, with every week missing when it has no run;
  cap_checks.tex  the analysis's checks: per part the runs, the per-run checks of E7b's own runs (counts true, false
                  and missing) and whether they hold; the identity of E7b's reruns with the frozen runs; Sublet's
                  certificate rows per part; and the readings R1, R2 and R3 as the analysis states them, R1 per cap at
                  X = B(t) (runs in scope, runs above, largest final and run-time excess) and R2 per stress lender;
  cap_runs.csv    every run record of the analysis (part, point, lender, week, policy, tag, source, policy seed, r0,
                  ALG, FB, B, final and run-time excess in USD and over FB, above, run-time above, the cap's binds,
                  first bind and latch slot, and whether the cell is one of reading R3's); the extract's
                  tables.cap_runs_csv holds the values, the columns, the row count and the sha256, and the after hook
                  refuses to write a file of another sha256.
Every table is a longtable (ms5b_e7_lib.longtable: one-column mode, "Table <n>, continued").

Inputs (RUN_INPUTS; figs.inputs, so SUBLET_FIGS_IN_ROOT redirects them): code/sim/out/e7b/analysis.json, the MS8 run
output copied in after the runs (figs/rebuild.py's MS8 block X6 keeps the entry pending until then). A missing input
stops the script with exit code 2 and the file named; input from a reduced (smoke) run is never written into paper/ or
code/sim/out/figs/ (ms7_e7r_lib.guard_reduced; the analysis records meta.reduced per part, and the extract's
meta.reduced is true when either part is reduced). Run from code/sim: python -m figs.supp.sf_cap [--from-extract
[JSON]].
"""
from __future__ import annotations

import json
import math
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, NullLocator

from figs import style
from figs.common import MissingKey, align_baselines, align_legend_rows, align_right_math, cli, need, write_table
from figs.inputs import Inputs
from figs.supp import ms5b_e7_lib as L
from figs.supp import ms7_e7r_lib as E
from figs.supp import ms7_x3_lib as X

NAME = "sf_cap"
KEYS = style.SUPP_POLICIES_MS8[NAME]
E7B = "code/sim/out/e7b"
ANALYSIS = f"{E7B}/analysis.json"
RUN_INPUTS = (ANALYSIS,)
INPUTS = RUN_INPUTS
TABLES = ("cap_runs.tex", "cap_modes.tex", "cap_sens.tex", "cap_checks.tex", "cap_runs.csv")
RUNS_CSV = TABLES[-1]
style.register_supplementary(NAME, "W2", 2.5)

SUBLET = "Sublet"
TRACE = "L-tr"
KEY_OF_TAG: dict[str, str] = {**L.KEY_OF_TAG, **style.MS8_KEY_OF_TAG}
TAG_OF_KEY: dict[str, str] = {k: t for t, k in KEY_OF_TAG.items()}
FIG_TAGS = tuple(TAG_OF_KEY[k] for k in KEYS)                # Sublet and the seven caps, in legend order
REFERENCE_TAGS = ("A9", "BL1", "BL1-GP")                     # in the tables only
A_DROP = ("CR-cap-B-latch", "CR-cap-B-slot")                 # not in (a): the variants of cap B(t), in (b)-(d), tables
TABLE_LABELS = ("tab:cap-runs", "tab:cap-margins", "tab:cap-binds", "tab:cap-modes", "tab:cap-mode-margins",
                "tab:cap-sens", "tab:cap-checks")
SENS_ORDER = ("fee4", "fee8", "fee16", "slow1", "scen_cold_wan_1gbps")
POINT_TEXT = {"fee4": r"Transfer fee, $\rho=4$", "fee8": r"Transfer fee, $\rho=8$",
              "fee16": r"Transfer fee, $\rho=16$", "slow1": "Slow-loop slot, 1 min",
              "scen_cold_wan_1gbps": "Cold loads, WAN 1 Gb/s"}
POINT_TEX = {"fee4": r"transfer fee, $\rho=4$", "fee8": r"transfer fee, $\rho=8$",
             "fee16": r"transfer fee, $\rho=16$", "slow1": "slow-loop slot of 1 min",
             "scen_cold_wan_1gbps": "cold loads over a WAN of 1 Gb/s"}
METRICS = ("r0_tr", "W0", "W0plus")
SUMMARY_COLS = ("W0", "W0plus")                              # the worst-case columns of (a), after the modes

# drawing (as built)
GROUP_GAP = 0.55                # extra space between groups of columns in (a) (column units)
DODGE_SHARE = 0.84              # the dodged series of a column or row span this share of its pitch
STRIP_HALF = 0.34               # (b): the runs of a column spread over +-STRIP_HALF (column units)
STRIP_MARKER_PT = 2.2           # (b): marker size of a run (the registry's 3.5 pt would merge the strip into a bar)
STRIP_EDGE_PT = 0.4
STRIP_ALPHA = 0.55              # (b): the runs' opacity, so that dense stretches of a column stay graded
LINTHRESH_B = 0.01              # (b): symmetric log, linear within +-LINTHRESH_B
LINSCALE_B = 0.6
ROW_PAD = 0.55                  # (c), (d): the y axis beyond the first and the last row (row units)
Y_PAD = 0.05                    # (b): the value axis beyond the data, as a share of its (symlog) span
ROT_PAD_PT = 3.0                # rotated tick labels: room below them
MARKER_PAD_PT = 1.5             # (c), (d): room between a marker's edge and the axis end (pt)
GLYPH_ROOM_PT = 7.0             # (b): the strip at the top of the axes that holds each column's legend glyph (pt)
AXES_RATIOS = (3.0, 1.05, 0.78, 0.78)
LABELS = {"ya": r"Cost over all-fallback, $r_0$", "yb": r"Excess over $C_{\mathrm{FB}}(T)$",
          "xc": r"$r_0$, trace lender", "xd": r"$W_0$",
          "titles": {"a": "Confirmation weeks, by lender", "b": "Run-time excess",
                     "c": "Sensitivity points", "d": ""},
          "w0": r"$W_0$", "w0plus": r"$W_0^{+}$", "above": "{k}", "above_mixed": "{k}/{n}",
          "xb": "Runs above at some slot,\nof {n} each", "xb_mixed": "Runs above at some slot"}


class MissingInput(SystemExit):
    """A required input file is missing (exit code 2, the file named)."""


def read(inp: Inputs, name: str) -> Any:
    p = inp.path(name)
    if not p.is_file():
        raise MissingInput(f"[{NAME}] required input {name} is missing under {inp.root} (an MS8 run output, "
                           "design/ms8/registration.md; copied in after the runs)")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def key(tag: str) -> str:
    if tag not in KEY_OF_TAG:
        raise MissingKey(f"{ANALYSIS}: tag {tag!r} has no registry key (style.MS8_KEY_OF_TAG, ms5b_e7_lib.KEY_OF_TAG)")
    return KEY_OF_TAG[tag]


def label(tag: str) -> str:
    return style.POLICIES[key(tag)].label


def point_order(points) -> list[str]:
    ps = list(points)
    return [p for p in SENS_ORDER if p in ps] + sorted(p for p in ps if p not in SENS_ORDER)


def _stats(st: Mapping | None) -> dict | None:
    return None if st is None else {k: st.get(k) for k in ("n", "median", "min", "max")}


def _max(vals) -> float | None:
    v = [float(x) for x in vals if x is not None]
    return max(v) if v else None


# ---------------------------------------------------------------------------------------------------------------
# build
def tag_rows(an: Mapping, part: str, point: str, tags: Sequence[str]) -> list[dict]:
    """Per tag of a part and point: r0 under L-tr, W0, W0+ (part week), runs, runs above the bound, runs with a
    run-time excess above the tolerance at some slot (from the runs), the largest final and run-time excess."""
    pt = ((an.get("per_tag") or {}).get(part) or {}).get(point) or {}
    wt = ((an.get("W") or {}).get(part) or {}).get(point) or {}
    runs = [r for r in an["runs"] if r["part"] == part and r["point"] == point]
    out = []
    for t in tags:
        by_m = pt.get(t) or {}
        rs = [r for r in runs if r["tag"] == t]
        w = wt.get(t) or {}
        out.append({"tag": t, "key": key(t), "label": label(t),
                    "r0_tr": _stats((by_m.get(TRACE) or {}).get("r0")),
                    "W0": _stats(w.get("W0_stats")), "W0plus": _stats(w.get("W0plus_stats")),
                    "runs": sum(int(x.get("runs") or 0) for x in by_m.values()),
                    "above": sum(int(x.get("above") or 0) for x in by_m.values()),
                    "runtime_above": sum(1 for r in rs if r.get("runtime_above")),
                    "runtime_n": sum(1 for r in rs if r.get("runtime_rel") is not None),
                    "envelope_runs": sum(1 for r in rs if r.get("runtime_label") == "envelope"),
                    "final_rel_max": _max(x.get("final_rel_max") for x in by_m.values()),
                    "runtime_rel_max": _max(x.get("runtime_rel_max") for x in by_m.values()),
                    "modes": sorted(by_m, key=E.mode_rank)})
    return out


def panel_a(an: Mapping, modes: Sequence[str]) -> dict:
    """(a): Sublet and the caps but the two variants of cap B(t) (A_DROP), per mode and W0, W0+."""
    pt = need(an, "per_tag", "week", "default", what=ANALYSIS)
    wt = need(an, "W", "week", "default", what=ANALYSIS)
    series = {}
    for t in FIG_TAGS:
        if t in A_DROP:
            continue
        by_m = pt.get(t) or {}
        w = wt.get(t) or {}
        series[key(t)] = {"modes": {m: _stats((by_m.get(m) or {}).get("r0")) for m in modes},
                          "W0": _stats(w.get("W0_stats")), "W0plus": _stats(w.get("W0plus_stats"))}
    return {"keys": list(series), "modes": list(modes), "mode_text": [E.mode_text(m) for m in modes],
            "series": series}


def panel_b(an: Mapping) -> dict:
    """Per key the run-time excess over FB(T) of every run (both parts, the analysis's order), its label and part."""
    out = {}
    for t in FIG_TAGS:
        rs = [r for r in an["runs"] if r["tag"] == t]
        vals = [r.get("runtime_rel") for r in rs]
        out[key(t)] = {"values": vals, "labels": [r.get("runtime_label") for r in rs],
                       "parts": [r["part"] for r in rs], "n": sum(1 for v in vals if v is not None),
                       "above": sum(1 for r in rs if r.get("runtime_above")),
                       "runs": len(rs)}
    return out


def panel_cd(an: Mapping, points: Sequence[str], b_caps: Sequence[str]) -> dict:
    pt = (an.get("per_tag") or {}).get("sens") or {}
    wt = (an.get("W") or {}).get("sens") or {}
    tags = (SUBLET,) + tuple(t for t in FIG_TAGS if t in b_caps)
    rows = []
    for p in points:
        s = {}
        for t in tags:
            by_m = (pt.get(p) or {}).get(t) or {}
            s[key(t)] = {"r0_tr": _stats((by_m.get(TRACE) or {}).get("r0")),
                         "W0": _stats(((wt.get(p) or {}).get(t) or {}).get("W0_stats"))}
        rows.append({"point": p, "text": POINT_TEXT.get(p, p), "series": s})
    return {"keys": [key(t) for t in tags], "rows": rows}


def sens_weeks(an: Mapping, points: Sequence[str]) -> dict:
    """{'r0_tr': {point: the weeks with a run under L-tr}, 'W0': {point: the weeks with a value of W0 for some tag}}:
    the stress lenders run at the points on fewer weeks than the trace lender (registration §2)."""
    wt = (an.get("W") or {}).get("sens") or {}
    tr = {p: sorted({str(r["week"]) for r in an["runs"] if r["part"] == "sens" and r["point"] == p
                     and r["mode"] == TRACE and r.get("r0") is not None}, key=int) for p in points}
    w0 = {p: sorted({str(w) for row in (wt.get(p) or {}).values() for w, v in (row.get("W0") or {}).items()
                     if v is not None}, key=int) for p in points}
    return {"r0_tr": tr, "W0": w0}


def union_weeks(by_point: Mapping[str, Sequence[str]]) -> list[str]:
    return sorted({w for ws in by_point.values() for w in ws}, key=int)


def runs_table(an: Mapping, tags: Sequence[str]) -> dict:
    rows = tag_rows(an, "week", "default", tags)
    for r in rows:
        r["group"] = "sublet" if r["tag"] == SUBLET else ("cap" if r["tag"] in an["meta"]["cap_tags"] else "reference")
    weeks = [str(w) for w in need(an, "meta", "cells", "week", "default", what=ANALYSIS)]
    return {"rows": rows, "weeks": weeks,
            "scope": {"part": "week", "tags": [r["tag"] for r in rows], "weeks": weeks,
                      "metrics": ["r0_tr", "W0", "W0plus", "above", "final_rel_max", "runtime_rel_max"]}}


def r3_counts(an: Mapping) -> dict:
    """{(part, point): {tag: cells}} of reading R3's cells."""
    out: dict = {}
    for c in need(an, "readings", "R3", "cells", what=ANALYSIS):
        k = f"{c['part']}:{c['point']}"
        out.setdefault(k, {}).setdefault(c["tag"], 0)
        out[k][c["tag"]] += 1
    return out


def no_run_margin(n_weeks: int) -> dict:
    """The margin block of a cap without any run in a part or point, which the analysis leaves out: every week missing
    (a loss for the reference, the analysis's convention), no value."""
    return {"n": 0, "median": None, "min": None, "max": None, "wins": 0, "ties": 0, "losses": 0, "missing": n_weeks,
            "losses_with_missing": n_weeks}


def margins_table(an: Mapping) -> dict:
    mg = need(an, "margins", "week", "default", what=ANALYSIS)
    inner = ((an.get("inner") or {}).get("week") or {}).get("default") or {}
    r3 = r3_counts(an).get("week:default", {})
    n_w = len(need(an, "meta", "cells", "week", "default", what=ANALYSIS))
    rows = []
    for cap in an["meta"]["cap_tags"]:
        for ref in an["meta"]["references"][cap]:
            m = ((mg.get(cap) or {}).get(ref)) or {}
            kept = (inner.get(cap) or {}).get("all") or {}
            rows.append({"tag": cap, "label": label(cap), "reference": ref, "reference_label": label(ref),
                         **{k: (E.stats_of(m.get(k)) if m else no_run_margin(n_w)) for k in METRICS},
                         "no_runs": not m,
                         "kept_share": _stats(kept.get("kept_share")),
                         "inner": kept.get("inner"), "r3_cells": r3.get(cap, 0) if ref == SUBLET else None})
    return {"rows": rows, "scope": {"part": "week", "caps": list(an["meta"]["cap_tags"]), "metrics": list(METRICS)}}


KEPT_CLASSES = ("trace", "stress", "other", "all")


def binds_table(an: Mapping, points: Sequence[str]) -> dict:
    """Per part (part week, then each point of part sens) and cap: the runs, the slots at which the cap bound per run
    (median and min-max over the runs, from the run records), the runs whose cap latched (per_tag's latched_runs summed
    over the modes), the share of the inner policy's saving that the cap keeps per mode class (inner: L-tr, the five
    stress lenders, the others, all; median and min-max) and the runs whose inner policy saved nothing (all)."""
    blocks = []
    for part, point in [("week", "default")] + [("sens", p) for p in points]:
        pt = ((an.get("per_tag") or {}).get(part) or {}).get(point) or {}
        inner = ((an.get("inner") or {}).get(part) or {}).get(point) or {}
        rows = []
        for cap in an["meta"]["cap_tags"]:
            by_m = pt.get(cap) or {}
            binds = [((r.get("cap") or {}).get("bind_slots")) for r in an["runs"]
                     if r["part"] == part and r["point"] == point and r["tag"] == cap]
            b = [float(x) for x in binds if x is not None]
            inn = inner.get(cap) or {}
            rows.append({"tag": cap, "label": label(cap), "runs": sum(int(x.get("runs") or 0) for x in by_m.values()),
                         "bind_slots": ({"n": len(b), "median": float(np.median(b)), "min": min(b), "max": max(b)}
                                        if b else None),
                         "latched_runs": sum(int(x.get("latched_runs") or 0) for x in by_m.values()),
                         "kept_share": {c: _stats((inn.get(c) or {}).get("kept_share")) for c in KEPT_CLASSES},
                         "inner": (inn.get("all") or {}).get("inner"),
                         "n_inner_saving_nonpositive": (inn.get("all") or {}).get("n_inner_saving_nonpositive")})
        blocks.append({"part": part, "point": point,
                       "text": "Confirmation weeks" if part == "week" else _cap1(POINT_TEX.get(point, point)),
                       "rows": rows})
    return {"blocks": blocks, "scope": {"parts": [(b["part"], b["point"]) for b in blocks],
                                        "caps": list(an["meta"]["cap_tags"]), "classes": list(KEPT_CLASSES)}}


def mode_columns(modes) -> list[dict]:
    """The lender columns of cap_modes in the order of the supplement's e7r_modes (sf_stress_ms7.mode_columns): L-tr,
    L-hon, the other stress lenders of the confirmation that are not i.i.d., the i.i.d. lenders by p, the regional
    lenders by spreading probability, the peak-aligned lender, then any other mode."""
    modes = set(modes)
    iid = sorted((m for m in modes if m.startswith("L-iid-")), key=lambda m: float(m[len("L-iid-"):]))
    reg = sorted((m for m in modes if m.startswith("L-co-reg-")), key=lambda m: float(m[len("L-co-reg-"):]))
    first = [m for m in (E.TRACE, E.HON, "L-eg", "L-ss", "L-co") if m in modes]
    last = [m for m in ("L-pk",) if m in modes]
    rest = sorted(modes - set(first) - set(iid) - set(reg) - set(last), key=E.mode_rank)
    out = [{"mode": m, "group": None, "head": E.mode_text(m)} for m in first]
    out += [{"mode": m, "group": "iid", "head": m[len("L-iid-"):]} for m in iid]
    out += [{"mode": m, "group": "regional", "head": m[len("L-co-reg-"):]} for m in reg]
    out += [{"mode": m, "group": None, "head": "peak"} for m in last]
    out += [{"mode": m, "group": None, "head": E.mode_text(m)} for m in rest]
    return out


def modes_table(an: Mapping, tags: Sequence[str]) -> dict:
    """Part week per lender: every tag's r0 (median and min-max over the weeks) and every cap's paired margin against
    each reference (the analysis's margins r0:<mode>)."""
    pt = need(an, "per_tag", "week", "default", what=ANALYSIS)
    mg = (an.get("margins") or {}).get("week", {}).get("default") or {}
    n_w = len(need(an, "meta", "cells", "week", "default", what=ANALYSIS))
    have = {m for t in tags for m in (pt.get(t) or {})}
    cols = mode_columns(have)
    rows = [{"tag": t, "label": label(t),
             "group": "sublet" if t == SUBLET else ("cap" if t in an["meta"]["cap_tags"] else "reference"),
             "r0": {c["mode"]: _stats(((pt.get(t) or {}).get(c["mode"]) or {}).get("r0")) for c in cols}}
            for t in tags]
    mrows = []
    for cap in an["meta"]["cap_tags"]:
        for ref in an["meta"]["references"][cap]:
            m = (mg.get(cap) or {}).get(ref) or {}
            mrows.append({"tag": cap, "label": label(cap), "reference": ref, "reference_label": label(ref),
                          "r0": {c["mode"]: (E.stats_of(m.get(f"r0:{c['mode']}")) if m else no_run_margin(n_w))
                                 for c in cols}})
    return {"rows": rows, "margins": mrows, "columns": cols,
            "scope": {"part": "week", "tags": list(tags), "modes": [c["mode"] for c in cols]}}


def sens_table(an: Mapping, points: Sequence[str], tags: Sequence[str], weeks: Mapping) -> dict:
    mg = (an.get("margins") or {}).get("sens") or {}
    cells = need(an, "meta", "cells", what=ANALYSIS).get("sens") or {}
    caps = an["meta"]["cap_tags"]
    r3 = r3_counts(an)
    blocks = []
    for p in points:
        n_tr, n_w0 = len(weeks["r0_tr"].get(p) or []), len(weeks["W0"].get(p) or [])
        rows = tag_rows(an, "sens", p, tags)
        for r in rows:
            if r["tag"] in caps:
                by_ref = ((mg.get(p) or {}).get(r["tag"])) or {}
                r["vs"] = {ref: ({k: E.stats_of((by_ref.get(ref) or {}).get(k)) for k in ("r0_tr", "W0")}
                                 if by_ref.get(ref) else {"r0_tr": no_run_margin(n_tr), "W0": no_run_margin(n_w0)})
                           for ref in an["meta"]["references"][r["tag"]]}
                r["r3_cells"] = r3.get(f"sens:{p}", {}).get(r["tag"], 0)
            else:
                r["vs"], r["r3_cells"] = None, None
        rows = [r for r in rows if r["tag"] in caps or r["runs"] or r["r0_tr"] or r["W0"]]
        blocks.append({"point": p, "text": POINT_TEX.get(p, p), "weeks": [str(w) for w in cells.get(p) or []],
                       "weeks_r0_tr": list(weeks["r0_tr"].get(p) or []), "weeks_W0": list(weeks["W0"].get(p) or []),
                       "rows": rows})
    return {"blocks": blocks, "scope": {"part": "sens", "points": list(points), "tags": list(tags)}}


def checks_table(an: Mapping) -> dict:
    rd = need(an, "readings", what=ANALYSIS)
    idn = need(an, "identity", what=ANALYSIS)
    r1 = rd["R1"]
    return {"checks": need(an, "checks", what=ANALYSIS), "sublet": need(an, "sublet", what=ANALYSIS),
            "identity": {k: idn.get(k) for k in ("holds", "n_pairs", "n_equal", "max_abs_diff")}
            | {"n_reruns_without_frozen": len(idn.get("reruns_without_frozen") or [])},
            "R1": {"holds": r1.get("holds"), "n_runs": r1.get("n_runs"), "sublet_runs": r1.get("sublet_runs"),
                   "sublet_violations": len(r1.get("sublet_violations") or []),
                   "by_tag": {t: dict(v) for t, v in (r1.get("by_tag") or {}).items()}},
            "R2": {k: rd["R2"].get(k) for k in ("holds", "cap_median", "sublet_median", "n_cells", "n_sublet_missing")}
            | {"per_mode": dict(rd["R2"].get("per_mode") or {})},
            "R3": {"n_cells": rd["R3"].get("n_cells"), "by_tag": {t: dict(v) for t, v in
                                                                   (rd["R3"].get("by_tag") or {}).items()}},
            "scope": {"parts": sorted(need(an, "checks", what=ANALYSIS)), "readings": ["R1", "R2", "R3"]}}


RUNS_COLUMNS = ("part", "point", "lender", "week", "policy", "tag", "source", "policy_seed", "r0", "alg_usd", "fb_usd",
                "b_usd", "final_excess_usd", "final_excess_rel", "above", "runtime_source", "runtime_excess_usd",
                "runtime_excess_rel", "runtime_above", "cap_bind_slots", "cap_first_bind", "cap_latch_slot",
                "r3_cell")


def runs_csv_entry(an: Mapping) -> dict:
    r3 = {(c["part"], c["point"], c["mode"], str(c["week"]), c["tag"]) for c in an["readings"]["R3"]["cells"]}
    rows = []
    for r in an["runs"]:
        cap = r.get("cap") or {}
        k = (r["part"], r["point"], r["mode"], str(r["week"]), r["tag"])
        rows.append([r["part"], r["point"], E.mode_plain(r["mode"]), str(r["week"]), L.plain_label(label(r["tag"])),
                     r["tag"], r.get("source"), 0, r.get("r0"), r.get("ALG"), r.get("FB"), r.get("B"),
                     r.get("final_usd"), r.get("final_rel"), r.get("above"), r.get("runtime_label"),
                     r.get("runtime_usd"), r.get("runtime_rel"), r.get("runtime_above"),
                     cap.get("bind_slots") if cap else None, cap.get("first_bind") if cap else None,
                     cap.get("latch_t") if cap else None, k in r3])
    e = X.csv_entry(RUNS_CSV, RUNS_COLUMNS, rows)
    e["scope"] = {"runs": len(rows), "parts": sorted({r[0] for r in rows}), "tags": sorted({r[5] for r in rows})}
    return e


def meta_of(an: Mapping) -> dict:
    m = an.get("meta") or {}
    red = m.get("reduced")
    by = dict(red) if isinstance(red, Mapping) else {"analysis": bool(red)}
    rg = m.get("registration") or {}
    return {"reduced_by_part": {k: bool(v) for k, v in by.items()}, "reduced": any(bool(v) for v in by.values()),
            "analysis_sha256": m.get("analysis_sha256"), "registration_matches": rg.get("matches"),
            "git_revision": m.get("git_revision"), "git_revisions": dict(m.get("git_revisions") or {}),
            "inputs_sha256": dict(m.get("inputs_sha256") or {})}


def build(inp: Inputs) -> dict:
    an = read(inp, ANALYSIS)
    m = need(an, "meta", what=ANALYSIS)
    for k in ("cap_tags", "b_caps", "references", "stress_modes", "w0plus_modes", "cells"):
        need(m, k, what=f"{ANALYSIS} meta")
    if not isinstance(an.get("runs"), list):
        raise MissingKey(f"{ANALYSIS}: no runs")
    if tuple(m["cap_tags"]) != tuple(t for t in FIG_TAGS if t != SUBLET):
        raise style.StyleError(f"{ANALYSIS}: the cap tags {m['cap_tags']} are not the figure's {FIG_TAGS[1:]}")
    for t in {r["tag"] for r in an["runs"]}:
        key(t)                                               # every tag of the analysis has a registry key
    weeks = [str(w) for w in need(m, "cells", "week", "default", what=f"{ANALYSIS} meta")]
    week_tags = need(an, "per_tag", "week", "default", what=ANALYSIS)
    modes = sorted({md for t in FIG_TAGS for md in (week_tags.get(t) or {})}, key=E.mode_rank)
    points = point_order((m["cells"].get("sens") or {}).keys())
    sw = sens_weeks(an, points)
    table_tags = tuple(FIG_TAGS) + REFERENCE_TAGS
    out = {"keys": list(KEYS), "tags": list(FIG_TAGS), "weeks": weeks,
           "sens_weeks": {p: [str(w) for w in m["cells"]["sens"][p]] for p in points},
           "sens_weeks_r0_tr": sw["r0_tr"], "sens_weeks_W0": sw["W0"],
           "modes": {"week": modes, "stress": list(m["stress_modes"]), "w0plus": list(m["w0plus_modes"])},
           "b_caps": list(m["b_caps"]),
           "a": panel_a(an, modes), "b": panel_b(an), "cd": panel_cd(an, points, m["b_caps"]),
           "tables": {"cap_runs": runs_table(an, table_tags), "cap_margins": margins_table(an),
                      "cap_binds": binds_table(an, points), "cap_modes": modes_table(an, table_tags),
                      "cap_sens": sens_table(an, points, table_tags, sw), "cap_checks": checks_table(an),
                      "cap_runs_csv": runs_csv_entry(an)},
           "labels": dict(LABELS), "meta": meta_of(an)}
    out["labels"]["caption"] = caption(out)
    out["meta"]["sources"] = list(inp.sources)
    return out


def _s(n: int) -> str:
    return "" if n == 1 else "s"


def weeks_text(ws: Sequence[str]) -> str:
    """'week 101', 'weeks 301--304' or 'no week'."""
    return "no week" if not ws else f"week{_s(len(ws))} " + L.week_span(ws)


def caption(d: Mapping) -> str:
    n = len(d["weeks"])
    caps_b = [label(t) for t in d["b_caps"]]
    r1 = d["tables"]["cap_checks"]["R1"]
    nr, nv, ns = int(r1["n_runs"] or 0), int(r1["sublet_violations"] or 0), int(r1["sublet_runs"] or 0)
    tr_w, w0_w = union_weeks(d.get("sens_weeks_r0_tr") or {}), union_weeks(d.get("sens_weeks_W0") or {})
    if nv:
        sub = (f"{E.count(nv)} of Sublet's {ns:,} runs {'is' if nv == 1 else 'are'} above the bound at the end, or "
               r"at some slot by its series or envelope")
    else:
        sub = f"none of Sublet's {ns:,} runs is above the bound, at the end or at some slot"
    if d["cd"]["rows"]:
        cd = (r"(c), (d)~At the sensitivity points, Sublet and the caps at $X=B(t)$ (" + E.join(L.tex(x) for x in caps_b)
              + r"): the median $r_0$ under the trace lender over " + weeks_text(tr_w)
              + r" and the median $W_0$ over " + weeks_text(w0_w) + r", each with its min--max. ")
    else:
        cd = r"(c), (d)~No run at the sensitivity points. "
    return (r"Sublet against the naive spend caps (policy seed 0): (a)~on weeks " + L.week_span(d["weeks"])
            + f" ({n} week{_s(n)}), the median over the weeks of $r_0$ under each of the "
            + E.count(len(d["modes"]["week"])) + r" lenders, and of the worst cases $W_0$ (over the "
            + E.count(len(d["modes"]["stress"])) + r" stress lenders) and $W_0^{+}$ (over these and the new ones), "
            r"with bars from the min to the max over the weeks of $W_0$ and $W_0^{+}$; the grey line is the "
            r"all-fallback cost; the latched and the slot-count cap $B(t)$ of critical-ratio renting are in "
            r"(b)--(d) and the tables only. "
            r"(b)~The run-time excess $\max_t \mathrm{ALG}(t)-C_{\mathrm{FB}}(t)-B(t)$ over $C_{\mathrm{FB}}(T)$ of "
            r"every run of the confirmation weeks and of the sensitivity points, one column per policy under its "
            r"marker, against Sublet's bound $C_{\mathrm{FB}}+B$ with $B$ Sublet's allowance, the same for every "
            r"column whatever the cap's own limit $X$; shaded: above the bound; under each column the runs above it at "
            r"some slot, out of the runs with a value; a run above the bound at some slot may end below it. For Sublet's runs read from the earlier studies the value is its "
            r"envelope, an upper bound. "
            + f"{E.count(nr).capitalize()} run{_s(nr)} of a cap at $X=B(t)$ under one of the "
            + E.count(len(d["modes"]["w0plus"])) + r" lenders of $W_0^{+}$ or at $\rho=16$ "
            + ("ends" if nr == 1 else "end") + r" above the bound, having been above it at some slot; " + sub + ". "
            + cd + r"Every policy's values: Tables~" + E.join(r"\ref{" + x + "}" for x in TABLE_LABELS)
            + "; every run: " + L.tex(RUNS_CSV) + ".")


# ---------------------------------------------------------------------------------------------------------------
# drawing
def column_positions(modes: Sequence[str], stress: Sequence[str]) -> tuple[list[float], list[str], list[str]]:
    """x of each column of (a): the modes in groups (trace and honoring; the stress lenders; the others), then W0 and
    W0+, with GROUP_GAP between groups; returns (xs, names, group of each)."""
    def grp(m):
        return "base" if m in (E.TRACE, E.HON) else ("stress" if m in stress else "new")
    cols = [(m, grp(m)) for m in modes] + [(c, "worst") for c in SUMMARY_COLS]
    xs, x, prev = [], 0.0, None
    for _c, g in cols:
        if prev is not None and g != prev:
            x += GROUP_GAP
        xs.append(x)
        x += 1.0
        prev = g
    return xs, [c for c, _ in cols], [g for _, g in cols]


def dodge(n: int) -> list[float]:
    """Offsets of n series within one column or row (column units)."""
    if n <= 1:
        return [0.0] * n
    step = DODGE_SHARE / n
    return [step * (i - (n - 1) / 2) for i in range(n)]


TICK_STEPS = (0.01, 0.02, 0.025, 0.05, 0.1, 0.2, 0.25, 0.5, 1.0, 2.0, 2.5, 5.0, 10.0)


def nice_ticks(lo: float, hi: float, n_min: int = 3, n_max: int = 6) -> list[float]:
    for st in TICK_STEPS:
        t = [round(k * st, 10) for k in range(math.ceil(lo / st - 1e-9), math.floor(hi / st + 1e-9) + 1)]
        if n_min <= len(t) <= n_max:
            return t
    return [round(lo, 3), round(hi, 3)]


EXTEND_MAX = 0.35              # nice_axis: the axis may start below the data by at most this share of its span


def nice_axis(lo: float, hi: float, n_min: int = 2, n_max: int = 4) -> tuple[float, list[float]]:
    """(the axis start, the ticks) for data in [lo, hi]: for the steps of TICK_STEPS in turn, the ticks from the
    multiple at or below lo up to hi when that multiple lies within EXTEND_MAX of the span below lo (the axis then
    starts at a tick below every value), else the ticks within [lo, hi]; the first that numbers n_min to n_max."""
    span = max(hi - lo, 1e-9)
    for st in TICK_STEPS:
        k0, k1 = math.floor(lo / st + 1e-9), math.floor(hi / st + 1e-9)
        if lo - k0 * st <= EXTEND_MAX * span + 1e-12:
            t = [round(k * st, 10) for k in range(k0, k1 + 1)]
            if n_min <= len(t) <= n_max:
                return min(lo, t[0]), t
        t = [round(k * st, 10) for k in range(math.ceil(lo / st - 1e-9), k1 + 1)]
        if n_min <= len(t) <= n_max:
            return lo, t
    return lo, [round(lo, 3), round(hi, 3)]


def marker_pad(span: float, length_in: float) -> float:
    """The data distance that keeps a marker (style.MARKER_PT) MARKER_PAD_PT clear of an axis end, on an axis of
    `length_in` inches whose data span is `span` before the padding."""
    fr = (style.MARKER_PT / 2.0 + MARKER_PAD_PT) / (max(length_in, 1e-3) * style.BP_PER_IN)
    return fr * span / max(1e-6, 1.0 - 2.0 * fr)


def _whisker(ax, k: str, x: float, y: float, st: Mapping, orientation: str = "y") -> None:
    if st.get("min") is not None and st.get("max") is not None and st["max"] > st["min"]:
        if orientation == "y":
            style.errorbars(ax, k, [x], [y], [st["min"]], [st["max"]])
        else:
            style.errorbars(ax, k, [y], [x], [st["min"]], [st["max"]], orientation="x")


def draw_a(ax, d: Mapping) -> None:
    """(a): medians per lender (no bars: the min-max per lender is in tab:cap-modes), median and min-max bar in the
    columns W0 and W0+."""
    a = d["a"]
    xs, cols, groups = column_positions(a["modes"], d["modes"]["stress"])
    keys = a.get("keys") or list(a["series"])
    off = dodge(len(keys))
    vals = []
    for i, k in enumerate(keys):
        s = a["series"][k]
        for x, c in zip(xs, cols):
            st = s["modes"].get(c) if c not in SUMMARY_COLS else s[c]
            if not st or st.get("median") is None:
                continue
            xx = x + off[i]
            if c in SUMMARY_COLS:
                _whisker(ax, k, xx, st["median"], st)
                vals += [st.get("min"), st.get("max")]
            mk = style.scatter_policy(ax, k, [xx], [st["median"]])
            mk._sublet_role = "median"
            vals.append(st["median"])
    v = [float(x) for x in vals if x is not None] + [1.0]
    lo, hi = min(v), max(v)
    pad = marker_pad(max(hi - lo, 1e-6), _axes_in(ax)[1])
    lo, hi = lo - pad, hi + pad
    ax.set_ylim(lo, hi)
    ax.yaxis.set_major_locator(FixedLocator(nice_ticks(lo, hi)))
    ax.yaxis.set_major_formatter(style.PLAIN)
    style.reference_line(ax, y=1.0)
    for i in range(1, len(xs)):
        if groups[i] != groups[i - 1]:
            sep = ax.axvline(0.5 * (xs[i] + xs[i - 1] + 1.0) - 0.5, color=style.GRID_GREY, linewidth=0.4, zorder=0.6,
                             label="_nolegend_")
            sep._sublet_role = "separator"
    ax.set_xlim(xs[0] - 0.5, xs[-1] + 0.5)
    names = list(a["mode_text"]) + [d["labels"]["w0"], d["labels"]["w0plus"]]
    ax.set_xticks(xs)
    ax.set_xticklabels(names, rotation=90, ha="center", va="top")
    ax.tick_params(axis="x", length=0)
    ax.set_ylabel(d["labels"]["ya"])


def strip_offsets(vals: Sequence[float]) -> list[float]:
    """Sideways offsets of a column's runs, by a fixed rule: the runs in the order of their values, each offset by the
    golden-ratio sequence of its rank, so that equal values spread over the column and redraws are identical."""
    order = sorted(range(len(vals)), key=lambda i: (vals[i], i))
    out = [0.0] * len(vals)
    g = (math.sqrt(5.0) - 1.0) / 2.0
    for r, i in enumerate(order):
        out[i] = (((r * g) % 1.0) - 0.5) * 2.0 * STRIP_HALF
    return out


SYMLOG_MANTISSAS = (1.0, 2.0, 5.0)   # (b): ticks at 1, 2 and 5 times the powers of ten from LINTHRESH_B on


def _symlog_ticks(lo: float, hi: float) -> list[float]:
    """0 and, on each side the axis reaches, the ticks m * LINTHRESH_B * 10^k (m in SYMLOG_MANTISSAS) within it."""
    t = [0.0]
    dec = LINTHRESH_B
    while dec <= max(abs(lo), abs(hi)) * 1.0001 and dec < 1e6:
        for m in SYMLOG_MANTISSAS:
            v = round(m * dec, 12)
            if v <= hi * 1.0001:
                t.append(v)
            if -v >= lo * 1.0001:
                t.insert(0, -v)
        dec *= 10.0
    return t


def b_tick_labels(d: Mapping) -> tuple[list[str], str]:
    """(b): the tick label under each column and the axis label: the count of runs above the bound at some slot, with
    the runs with a value in the axis label when every column has the same number, else k/n under each column."""
    keys = d["keys"]
    lab = d["labels"]
    ns = {d["b"][k]["n"] for k in keys}
    if len(ns) == 1:
        return ([lab["above"].format(k=d["b"][k]["above"], n=d["b"][k]["n"]) for k in keys],
                lab["xb"].format(n=f"{next(iter(ns)):,}"))
    return ([lab["above_mixed"].format(k=d["b"][k]["above"], n=d["b"][k]["n"]) for k in keys], lab["xb_mixed"])


def _axes_in(ax) -> tuple[float, float]:
    """(width, height) of an axes in inches (after the layout)."""
    w, h = ax.figure.get_size_inches()
    pos = ax.get_position()
    return pos.width * w, pos.height * h


def draw_b(ax, d: Mapping) -> None:
    """(b): every run per column; a strip of GLYPH_ROOM_PT at the top holds each column's legend glyph, the shaded
    region above the bound ends below it."""
    keys = d["keys"]
    vals_all = []
    for i, k in enumerate(keys):
        s = d["b"][k]
        v = [x for x in s["values"] if x is not None]
        if not v:
            continue
        off = strip_offsets(v)
        p = style.policy(k)
        ln = ax.plot([i + o for o in off], v, linestyle="none", marker=p.marker, markersize=STRIP_MARKER_PT,
                     markeredgewidth=STRIP_EDGE_PT, markeredgecolor=p.edgecolor or p.color,
                     markerfacecolor=p.color if p.fill == "filled" else "white", color=p.color, zorder=p.zorder,
                     alpha=STRIP_ALPHA, label="_nolegend_")[0]
        ln._sublet_policy = k
        ln._sublet_role = "runs"
        vals_all += v
    lo = min(vals_all + [0.0])                               # the axis from the data, not from the threshold
    hi = max(vals_all + [LINTHRESH_B])
    ax.set_yscale("symlog", linthresh=LINTHRESH_B, linscale=LINSCALE_B)
    tr = ax.yaxis.get_transform()
    tlo, thi = tr.transform([lo, hi])
    span = thi - tlo
    tlo2, thi_data = tlo - Y_PAD * span, thi + Y_PAD * span
    f = min(0.3, GLYPH_ROOM_PT / (_axes_in(ax)[1] * style.BP_PER_IN))   # the strip's share of the axes height
    thi2 = (thi_data - f * tlo2) / (1.0 - f)
    lo2, hi_data, hi2 = tr.inverted().transform([tlo2, thi_data, thi2])
    ax.set_ylim(lo2, hi2)
    ax.yaxis.set_major_locator(FixedLocator([t for t in _symlog_ticks(lo2, hi_data) if t <= hi_data]))
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_xlim(-0.6, len(keys) - 0.4)
    sh = ax.axhspan(0.0, hi_data, color=style.SHADE_GREY, zorder=0.4, linewidth=0, label="_nolegend_")
    sh._sublet_role = "above_region"
    style.reference_line(ax, y=0.0)
    glyph_tr = ax.get_xaxis_transform()                      # x in data, y in axes
    for i, k in enumerate(keys):
        g = style.scatter_policy(ax, k, [i], [1.0 - f / 2.0], transform=glyph_tr, clip_on=False)
        g._sublet_role = "column_glyph"
    ax.set_xticks(range(len(keys)))
    ticks, xlabel = b_tick_labels(d)
    ax.set_xticklabels(ticks, rotation=90, ha="center", va="top")
    ax.tick_params(axis="x", length=0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(d["labels"]["yb"])


def draw_cd(axes, d: Mapping) -> list[float]:
    cd = d["cd"]
    rows = cd["rows"]
    keys = cd["keys"]
    n = len(rows)
    if not n:                                                 # no run at the sensitivity points
        for ax, xl in zip(axes, (d["labels"]["xc"], d["labels"]["xd"])):
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_xlabel(xl)
        t = axes[0].text(0.5, 0.5, "No runs", transform=axes[0].transAxes, ha="center", va="center",
                         fontsize=style.TICK_PT)
        t._sublet_role = "no_runs"
        return []
    ys = [float(n - 1 - i) for i in range(n)]                     # the first point on top
    off = dodge(len(keys))
    for ax, metric, xl in zip(axes, ("r0_tr", "W0"), (d["labels"]["xc"], d["labels"]["xd"])):
        vals = []
        for r, y in zip(rows, ys):
            for j, k in enumerate(keys):
                st = (r["series"].get(k) or {}).get(metric) or {}
                if st.get("median") is None:
                    continue
                yy = y - off[j]                                      # Sublet (first) on top of its row
                _whisker(ax, k, yy, st["median"], st, orientation="x")
                mk = style.scatter_policy(ax, k, [st["median"]], [yy])
                mk._sublet_role = "median"
                vals += [st["median"], st.get("min"), st.get("max")]
        v = [float(x) for x in vals if x is not None] + [1.0]
        lo, ticks = nice_axis(min(v), max(v), 2, 4)
        hi = max(v)
        pad = marker_pad(max(hi - lo, 1e-6), _axes_in(ax)[0])
        ax.set_xlim(lo - pad, hi + pad)
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        ax.xaxis.set_major_formatter(style.PLAIN)
        style.reference_line(ax, x=1.0)
        ax.set_xlabel(xl)
        for i in range(1, n):
            sep = ax.axhline(0.5 * (ys[i] + ys[i - 1]), color=style.GRID_GREY, linewidth=0.4, zorder=0.6,
                             label="_nolegend_")
            sep._sublet_role = "separator"
    axes[0].set_ylim(-ROW_PAD, n - 1 + ROW_PAD)
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels([r["text"] for r in rows])
    for ax in axes:
        ax.tick_params(axis="y", length=0)
    align_baselines([tk.label1 for tk in axes[0].yaxis.get_major_ticks()])
    align_right_math([tk.label1 for tk in axes[0].yaxis.get_major_ticks()])
    return ys


def rotated_reserve(fig, texts: Sequence[str]) -> float:
    """The bottom margin (in) that rotated tick labels need: the widest label, the tick pad and ROT_PAD_PT."""
    from figs.common import text_width_in
    w = max((text_width_in(fig, t) for t in texts), default=0.0)
    return w + (style.mpl.rcParams["xtick.major.pad"] + ROT_PAD_PT) / style.BP_PER_IN


def legend_pairs(keys: Sequence[str]) -> list[tuple]:
    """The legend's entries, in its two rows read left to right: Sublet and the caps in legend order (legend_row fills
    the columns first, so the list is put in column order)."""
    pairs = style.policy_handles(keys, lines=False)
    n = len(pairs)
    ncol = -(-n // 2)
    rows = [pairs[:ncol], pairs[ncol:]]
    out = []
    for c in range(ncol):
        for r in rows:
            if c < len(r):
                out.append(r[c])
    return out


def draw(data: Mapping) -> Any:
    fig = style.new_figure(NAME)
    lab = data["labels"]
    rot = [*data["a"]["mode_text"], lab["w0"], lab["w0plus"]] + b_tick_labels(data)[0]
    bottom = max(style.MARGIN_BOTTOM, rotated_reserve(fig, rot))
    names = [r["text"] for r in data["cd"]["rows"]] or list(POINT_TEXT.values())   # the same room without a run
    left_c = style.ytick_reserve(fig, names) + 0.04
    axes = style.panel_row(fig, AXES_RATIOS, legend=2, sharey=[False, False, False, True],
                           left=[None, None, left_c, None], bottom=bottom)
    draw_a(axes[0], data)
    draw_b(axes[1], data)
    draw_cd(axes[2:], data)
    leg = style.legend_row(fig, [], extra=legend_pairs(data["keys"]), rows=2, lines=False)
    letters = style.panel_letters(axes)
    for letter, p in zip(letters, "abcd"):
        if lab["titles"].get(p):
            E.title(letter, lab["titles"][p])
    align_legend_rows(leg, 2)
    fig._sublet_axes = axes
    return fig


# ---------------------------------------------------------------------------------------------------------------
# LaTeX
NAME_IN = 2.05                  # the policy column of the tables (in)


SHORT_INNER = {"Critical-ratio renting": "CR", "Greedy renting": "GR"}   # the mode tables' short cap names
SHORT_NOTE = r"CR: critical-ratio renting; GR: greedy renting."


def name_cell(lab: str, short: bool = False) -> str:
    """A policy's name in a table's name column, ragged right: a cap's name ('<inner policy>, <cap>') breaks only
    after the comma, the cap kept on one line (an \\mbox), so that a wrapped '0' or '$B(t)$' never reads as a cell of
    the row's second line; with `short`, the inner policy of a cap as CR or GR (SHORT_NOTE in the caption)."""
    inner, sep, cap = str(lab).rpartition(", ")
    if not sep or "cap" not in cap:
        return L.rag(L.tex(lab))
    if short:
        inner = SHORT_INNER.get(inner, inner)
    return L.rag(L.tex(inner) + r", \mbox{" + L.tex(cap) + "}")


def _frac(k, n) -> str:
    return "--" if not n else f"{k}/{n}"


def _excess(v) -> str:
    return E.num(v, 4)


def _runtime(r: Mapping) -> str:
    """The largest run-time excess of a row, a dagger when some of its runs give the envelope, and (n/N) when only n of
    its N runs have a value."""
    if r.get("runtime_rel_max") is None:
        return "--"
    s = _excess(r["runtime_rel_max"]) + (r"$^{\dagger}$" if r.get("envelope_runs") else "")
    n, big_n = int(r.get("runtime_n") or 0), int(r.get("runs") or 0)
    return s + (f" ({n}/{big_n})" if n < big_n else "")


WTL_TEXT = (r"weeks won by the reference (the reference costs less), tied and lost (W/T/L), with $+m$ for the $m$ "
            r"weeks in which the cap or the reference has no run, counted as the reference's losses")
RUNTIME_NOTE = (r"with a value, with ($n$/$N$) where only $n$ of the $N$ runs have one. $^{\dagger}$For the runs read "
                r"from the earlier studies, the run-time value of a guarded run is the guard's envelope, an upper "
                r"bound on the run-time excess when the safe expert followed all-fallback; their unguarded runs have "
                r"none.")


def runs_tex(t: Mapping, d: Mapping) -> str:
    groups, rows, prev = [], [], None
    for r in t["rows"]:
        if r["group"] != prev:
            groups.append(len(rows))
            prev = r["group"]
        rows.append([name_cell(r["label"]), E.med_range(r["r0_tr"]), E.med_range(r["W0"]),
                     E.med_range(r["W0plus"]), _frac(r["above"], r["runs"]), _excess(r["final_rel_max"]),
                     _runtime(r)])
    n_w = len(t["weeks"])
    cap = (r"The naive spend caps on weeks " + L.week_span(t["weeks"]) + f" ({n_w} week" + ("s" if n_w != 1 else "")
           + r", policy seed 0) beside Sublet and the references: the median and, in parentheses, min--max over the "
           r"weeks of $r_0$ under the trace lender L-tr, of $W_0$ (the largest $r_0$ over the "
           + E.count(len(d["modes"]["stress"])) + r" stress lenders) and of $W_0^{+}$ (over the "
           + E.count(len(d["modes"]["w0plus"])) + r" lenders of the stress and new modes); the runs above the bound "
           r"$C_{\mathrm{FB}}(T)+B(T)$ out of the runs over all " + E.count(len(d["modes"]["week"]))
           + r" lenders; and the largest final excess $(\mathrm{ALG}(T)-C_{\mathrm{FB}}(T)-B(T))/C_{\mathrm{FB}}(T)$ "
           r"and run-time excess $\max_t(\mathrm{ALG}(t)-C_{\mathrm{FB}}(t)-B(t))/C_{\mathrm{FB}}(T)$ over the runs "
           + RUNTIME_NOTE + r" Rules separate Sublet, the caps and the references. Every run is in the data file "
           + L.tex(RUNS_CSV) + ".")
    return L.longtable("@{}p{" + f"{NAME_IN}in" + "}cccccc@{}", cap, "tab:cap-runs",
                       ["Policy", r"$r_0$, L-tr", "$W_0$", r"$W_0^{+}$", "Above", "Final", "Run-time"], rows,
                       groups=groups, tabcolsep="2.2pt")


def margins_tex(t: Mapping, d: Mapping) -> str:
    rows, groups, prev = [], [], None
    for r in sorted(t["rows"], key=lambda x: (x["reference"] != SUBLET, x["reference"])):
        if r["reference"] != prev:
            groups.append(len(rows))
            prev = r["reference"]
            rows.append([r"\multicolumn{9}{@{}l}{\emph{Against " + L.tex(r["reference_label"]) + "}}"])
        out = [name_cell(r["label"])]
        for m in METRICS:
            out += [E.wtl(r[m]), E.med_range(r[m])]
        ks = r.get("kept_share") or {}
        out += [E.num(ks.get("median"), 2), "--" if r.get("r3_cells") is None else str(r["r3_cells"])]
        rows.append(out)
    refs = list(dict.fromkeys(r["reference"] for r in t["rows"]))
    cap = (r"The caps' paired margins on weeks " + L.week_span(d["weeks"]) + r": a cap's value minus the reference's "
           r"in the same week (positive: the reference costs less), against "
           + E.join(L.tex(label(x)) for x in refs) + r" (the greedy caps also against the same guard around greedy "
           r"renting), on $r_0$ under L-tr, $W_0$ and $W_0^{+}$: " + WTL_TEXT + r"; median and min--max over the "
           r"weeks with a value. Kept: the median over all runs of the share of the inner policy's saving "
           r"$(1-r_0)/(1-r_0^{\mathrm{inner}})$ that the cap keeps (by lender class in Table~\ref{tab:cap-binds}). "
           r"Cheaper: the runs, over all lenders, in which the cap's $r_0$ is below Sublet's.")
    head_top = (r" & \multicolumn{2}{c}{$r_0$, L-tr} & \multicolumn{2}{c}{$W_0$} & \multicolumn{2}{c}{$W_0^{+}$} "
                r"& & \\" "\n" r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}")
    return L.longtable("@{}p{1.55in}cccccccc@{}", cap, "tab:cap-margins",
                       ["Cap", "W/T/L", "Median (min--max)", "W/T/L", "Median (min--max)", "W/T/L",
                        "Median (min--max)", "Kept", "Cheaper"], rows, groups=groups, tabcolsep="1.8pt",
                       head_top=head_top)


def binds_tex(t: Mapping, d: Mapping) -> str:
    rows, groups = [], []
    ncol = 9
    for b in t["blocks"]:
        groups.append(len(rows))
        rows.append([r"\multicolumn{" + str(ncol) + r"}{@{}l}{\emph{" + b["text"] + "}}"])
        for r in b["rows"]:
            ks = r["kept_share"]
            rows.append([name_cell(r["label"]), str(r["runs"]), _two(r["bind_slots"], 0),
                         str(r["latched_runs"])] + [_two(ks.get(c), 2) for c in KEPT_CLASSES]
                        + ["--" if r["n_inner_saving_nonpositive"] is None else str(r["n_inner_saving_nonpositive"])])
    cap = (r"The caps' binds and the saving they keep (policy seed 0), on the confirmation weeks and at each "
           r"sensitivity point: the runs; the slots at which the cap bound, median and, below it, min--max over "
           r"the runs; the "
           r"runs in which the latched cap latched; and the share of the inner policy's saving "
           r"$(1-r_0)/(1-r_0^{\mathrm{inner}})$ that the cap keeps (critical-ratio renting for the critical-ratio "
           r"caps, greedy renting for the greedy caps), median and, below it, min--max over the runs under the "
           r"trace lender "
           r"L-tr, the " + E.count(len(d["modes"]["stress"])) + r" stress lenders, the other lenders and all "
           r"lenders, over the runs in which the inner policy saved something; No saving: the runs in which it saved "
           r"nothing ($r_0^{\mathrm{inner}}\ge1$).")
    head_top = (r" & & & & \multicolumn{4}{c}{Kept} & \\" "\n" r"\cmidrule(lr){5-8}")
    return L.longtable("@{}p{1.55in}cccccccc@{}", cap, "tab:cap-binds",
                       ["Cap", "Runs", "Binds", "Latched", "L-tr", "Stress", "Other", "All", "No saving"], rows,
                       groups=groups, tabcolsep="2.2pt", keep=0, head_top=head_top)


def _two(st: Mapping | None, d: int) -> str:
    """A cell of tab:cap-binds: the median over its min--max, both with d decimals; '--' without a value."""
    if not st or st.get("median") is None:
        return "--"
    lo, hi = E.num(st.get("min"), d), E.num(st.get("max"), d)
    return two_lines(E.num(st["median"], d), "" if lo == hi else f"{lo}--{hi}")


def two_lines(top: str, bottom: str) -> str:
    return r"\begin{tabular}[t]{@{}c@{}}" + top + r"\\" + bottom + r"\end{tabular}"


def _mode_cell(st: Mapping | None) -> str:
    """A cell of tab:cap-modes: the median (three decimals) over its min--max (two decimals); '--' without a run."""
    if not st or st.get("median") is None:
        return "--"
    return two_lines(E.num(st["median"]), "" if st.get("min") is None
                     else f"{E.num(st['min'], 2)}--{E.num(st['max'], 2)}")


def _margin_cell(mg: Mapping | None) -> str:
    """A cell of tab:cap-mode-margins: W/T/L (+m) over the median margin (three decimals)."""
    if not mg:
        return "--"
    return two_lines(E.wtl(mg), E.num(mg.get("median")))


def _mode_head(cols: Sequence[Mapping]) -> tuple[list[str], str]:
    n = len(cols)
    spans, i = [], 0
    while i < n:                                   # the spanning heads of the i.i.d. and regional columns
        g = cols[i]["group"]
        j = i
        while j + 1 < n and g is not None and cols[j + 1]["group"] == g:
            j += 1
        spans.append((i, j, g))
        i = j + 1
    head_top = " & " + " & ".join(
        ("" if g is None else r"\multicolumn{" + str(b - a + 1) + r"}{c}{" + {"iid": r"i.i.d., $p=$",
                                                                             "regional": "regional"}[g] + "}")
        for a, b, g in spans) + r" \\"
    rules = "".join(r"\cmidrule(lr){" + f"{a + 2}-{b + 2}" + "}" for a, b, g in spans if g is not None)
    if rules:
        head_top += "\n" + rules
    return [c["head"] for c in cols], head_top


MODES_NAME_IN = 1.05            # the name column of cap_modes (in; a long name on several lines)


def modes_tex(t: Mapping, d: Mapping) -> str:
    cols = t["columns"]
    n = len(cols)
    heads, head_top = _mode_head(cols)
    rows, groups, prev = [], [], None
    for r in t["rows"]:
        if r["group"] != prev:
            groups.append(len(rows))
            prev = r["group"]
        rows.append([name_cell(r["label"], short=True)] + [_mode_cell(r["r0"].get(c["mode"])) for c in cols])
    n_w = len(d["weeks"])
    lenders = (r"the trace lender L-tr, the honoring lender L-hon, the stress lenders of the confirmation, the i.i.d.\ "
               r"lenders by their reclaim probability $p$ per site and slot, the regional correlated lender by its "
               r"spreading probability, and the peak-aligned trace lender (peak)")
    cap = (r"Every policy of the spend-cap runs under every lender on weeks " + L.week_span(d["weeks"]) + f" ({n_w} "
           + ("weeks" if n_w != 1 else "week") + r", policy seed 0): the median of $r_0$ over the weeks and, on the "
           r"line below, its min--max (--: no run), under " + lenders + r". Rules separate Sublet, the caps and the "
           r"references; " + SHORT_NOTE + r" Every run is in the data file " + L.tex(RUNS_CSV) + ".")
    t1 = L.longtable("@{}p{" + f"{MODES_NAME_IN}in" + "}" + "c" * n + "@{}", cap, "tab:cap-modes",
                     ["Policy"] + heads, rows, groups=groups, size=r"\scriptsize", tabcolsep="1.7pt",
                     head_top=head_top, keep=0)
    rows, groups, prev = [], [], None
    for r in sorted(t["margins"], key=lambda x: (x["reference"] != SUBLET, x["reference"])):
        if r["reference"] != prev:
            groups.append(len(rows))
            prev = r["reference"]
            rows.append([r"\multicolumn{" + str(n + 1) + r"}{@{}l}{\emph{Against " + L.tex(r["reference_label"])
                         + "}}"])
        rows.append([name_cell(r["label"], short=True)] + [_margin_cell(r["r0"].get(c["mode"])) for c in cols])
    cap2 = (r"The caps' paired margins on $r_0$ per lender on weeks " + L.week_span(d["weeks"]) + r" (the lenders "
            r"of Table~\ref{tab:cap-modes}): a cap's $r_0$ minus the reference's in the same week (positive: the "
            r"reference costs less); on the first line " + WTL_TEXT + r", on the second the median over the weeks "
            r"with a value; " + SHORT_NOTE)
    t2 = L.longtable("@{}p{" + f"{MODES_NAME_IN}in" + "}" + "c" * n + "@{}", cap2, "tab:cap-mode-margins",
                     ["Cap"] + heads, rows, groups=groups, size=r"\scriptsize", tabcolsep="1.7pt",
                     head_top=head_top, keep=0)
    return t1 + "\n" + t2


SENS_NAME_IN = 1.6             # the policy column of cap_sens (in; the run-time column may carry (n/N))


def sens_tex(t: Mapping, d: Mapping) -> str:
    rows, groups = [], []
    ncol = 9
    for b in t["blocks"]:
        groups.append(len(rows))
        rows.append([r"\multicolumn{" + str(ncol) + r"}{@{}l}{\emph{" + _cap1(b["text"])
                     + r"}, $r_0$: " + weeks_text(b["weeks_r0_tr"]) + r", $W_0$: "
                     + weeks_text(b["weeks_W0"]) + "}"])
        for r in b["rows"]:
            vs = r.get("vs") or {}
            refs = list(vs)
            first = vs.get(refs[0]) if refs else None
            rows.append([name_cell(r["label"]), E.med_range(r["r0_tr"]), E.med_range(r["W0"]),
                         _frac(r["above"], r["runs"]), _excess(r["final_rel_max"]), _runtime(r)]
                        + _vs_cells(first))
            for ref in refs[1:]:
                rows.append([L.rag(r"\quad against " + L.tex(label(ref))), "", "", "", "", ""] + _vs_cells(vs[ref]))
    cap = (r"The caps at the sensitivity points (policy seed 0): per point and policy, the median and min--max of "
           r"$r_0$ under L-tr over the point's trace weeks and of $W_0$ over its weeks with stress runs (both named "
           r"per point), the runs above the bound out of the runs, the largest final and run-time excess over "
           r"$C_{\mathrm{FB}}(T)$ (as in Table~\ref{tab:cap-runs}), and a cap's margin against Sublet (for a greedy "
           r"cap, on the line below, against the same guard around greedy renting): " + WTL_TEXT + r" on $r_0$ "
           r"under L-tr (with the median margin) and on $W_0$.")
    return L.longtable("@{}p{" + f"{SENS_NAME_IN}in" + "}cccccccc@{}", cap, "tab:cap-sens",
                       ["Policy", r"$r_0$, L-tr", "$W_0$", "Above", "Final", "Run-time", r"$\Delta r_0$ W/T/L",
                        r"$\Delta r_0$", r"$\Delta W_0$ W/T/L"], rows, groups=groups, tabcolsep="1.8pt", keep=0)


def _vs_cells(m: Mapping | None) -> list[str]:
    if not m:
        return ["", "", ""]
    return [E.wtl(m.get("r0_tr")), E.num((m.get("r0_tr") or {}).get("median")), E.wtl(m.get("W0"))]


CHECK_TEXT = {"fb_equal_bl0a": r"$C_{\mathrm{FB}}(T)$ equals the all-fallback run's bill",
              "cap_fb_equal_bound": r"a cap's $C_{\mathrm{FB}}(T)$ equals the bound's",
              "cap_X_equal_B": r"$X(T)=B(T)$ for the caps at $X=B(t)$",
              "cap_B_series_equal_bound": r"a cap's series $B(t)$ equals the bound's"}


PARTS_IN = 4.1                  # the part columns of cap_checks together (in)


def _cap1(s: str) -> str:
    """`s` with its first letter in upper case (str.capitalize lowers the rest: 'Gb/s', 'WAN')."""
    return s[:1].upper() + s[1:]


def _tfm(c: Mapping) -> str:
    return f"{c['true']}/{c['false']}/{c['missing']}"


def _yes(v) -> str:
    return "--" if v is None else ("yes" if v else "no")


def checks_tex(t: Mapping, d: Mapping) -> str:
    parts = [p for p in ("week", "sens") if p in t["checks"]]
    rows, groups = [], [0]
    ch = t["checks"]
    rows.append(["Runs of this study"] + [f"{ch[p]['runs']:,}" for p in parts])
    rows.append(["Runs of a cap"] + [f"{ch[p]['cap_runs']:,}" for p in parts])
    for k, txt in CHECK_TEXT.items():
        rows.append([L.rag(txt + " (true/false/missing)")] + [_tfm(ch[p][k]) for p in parts])
    rows.append(["The checks hold"] + [_yes(ch[p]["holds"]) for p in parts])
    groups.append(len(rows))
    sub = t["sublet"]
    for k, txt, f in (("runs", "Sublet's runs", lambda v: f"{v:,}"),
                      ("held", "certificates held", lambda v: f"{v:,}"),
                      ("envelope_violations", "envelope violations", str),
                      ("above", "runs above the bound", str),
                      ("final_usd_max", r"largest final excess (USD)", lambda v: E.num(v, 2)),
                      ("envelope_usd_max", r"largest envelope (USD)", lambda v: E.num(v, 2))):
        rows.append([L.rag(txt)] + [("--" if (sub.get(p) or {}).get(k) is None else f(sub[p][k])) for p in parts])
    groups.append(len(rows))
    idn = t["identity"]
    span = r"\multicolumn{" + str(len(parts)) + r"}{p{" + f"{PARTS_IN - 0.05:.2f}in" + r"}}{\raggedright "
    rows.append([L.rag("Reruns equal to the frozen runs"),
                 span + f"{idn['n_equal']} of {idn['n_pairs']} (largest difference "
                 + ("--" if idn.get("max_abs_diff") is None else L.bound_text(float(idn["max_abs_diff"])))
                 + f"); without a frozen run: {idn['n_reruns_without_frozen']}; holds: {_yes(idn['holds'])}" + "}"])
    groups.append(len(rows))
    r1, r2, r3 = t["R1"], t["R2"], t["R3"]
    rows.append([L.rag(r"R1: a cap at $X=B(t)$ above the bound, Sublet never"),
                 span + f"holds: {_yes(r1['holds'])}; {r1['n_runs']} runs; Sublet {r1['sublet_violations']} of "
                 + f"{r1['sublet_runs']:,}" + "}"])
    for tg, v in r1["by_tag"].items():
        rows.append([L.rag(r"\quad " + L.tex(label(tg))),
                     span + f"{v.get('above_with_runtime', 0)} of {v.get('runs_in_scope', 0)} runs in scope; largest "
                     + "final " + _excess(v.get("final_rel_max")) + ", run-time " + _excess(v.get("runtime_rel_max"))
                     + "}"])
    rows.append([L.rag(r"R2: " + L.tex(label("CR-cap-0")) + r" median $r_0\ge0.95$ under stress, Sublet's $\le0.79$"),
                 span + f"holds: {_yes(r2['holds'])}; " + E.num(r2.get("cap_median")) + " against "
                 + E.num(r2.get("sublet_median")) + f" over {r2.get('n_cells') or 0} cells" + "}"])
    for m in sorted(r2.get("per_mode") or {}, key=E.mode_rank):
        v = r2["per_mode"][m]
        rows.append([L.rag(r"\quad under " + E.mode_text(m)),
                     span + E.num(v.get("cap")) + " against " + E.num(v.get("sublet")) + "}"])
    by = "; ".join(f"{L.tex(label(tg))}: {v.get('cells', 0)}" for tg, v in sorted(r3["by_tag"].items()))
    rows.append([L.rag(r"R3: runs where a cap costs less than Sublet"),
                 span + f"{r3['n_cells'] or 0}" + (f" ({by})" if by else "") + "}"])
    cap = (r"The checks of the spend-cap runs: per part, the runs of this study and the per-run checks of its runs "
           r"(true/false/missing), Sublet's certificate rows (its runs of both sources), the identity of this study's "
           r"reruns of Sublet and critical-ratio renting with the frozen runs (equal as floats), and the readings R1 "
           r"to R3, each reported whatever its outcome: R1 per cap at $X=B(t)$, its runs in scope (on the "
           r"confirmation weeks under the " + E.count(len(d["modes"]["w0plus"])) + r" lenders of $W_0^{+}$, at the "
           r"sensitivity point $\rho=16$ under every lender) that end above the bound and are above it at some slot, "
           r"and the largest final and run-time excess over $C_{\mathrm{FB}}(T)$ among them; R2 per stress lender, "
           r"the median $r_0$ of the cap against Sublet's.")
    col = f"p{{{PARTS_IN / max(1, len(parts)) - 0.05:.2f}in}}"
    return L.longtable("@{}p{2.9in}" + col * len(parts) + "@{}", cap, "tab:cap-checks",
                       ["Check"] + [f"Part {p}" for p in parts], rows, groups=groups, tabcolsep="3.0pt")


def write_tables(data: Mapping, report: Mapping) -> None:
    E.guard_reduced(data, NAME)
    t = data["tables"]
    head = L.table_head
    paths = [write_table(TABLES[0], head(NAME, [ANALYSIS]) + runs_tex(t["cap_runs"], data) + "\n"
                         + margins_tex(t["cap_margins"], data) + "\n" + binds_tex(t["cap_binds"], data)),
             write_table(TABLES[1], head(NAME, [ANALYSIS]) + modes_tex(t["cap_modes"], data)),
             write_table(TABLES[2], head(NAME, [ANALYSIS]) + sens_tex(t["cap_sens"], data)),
             write_table(TABLES[3], head(NAME, [ANALYSIS]) + checks_tex(t["cap_checks"], data)),
             X.write_csv(t["cap_runs_csv"], NAME)]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    def build_checked(inp: Inputs) -> dict:
        d = build(inp)
        E.guard_reduced(d, NAME)
        return d

    def draw_checked(d: Mapping) -> Any:
        E.guard_reduced(d, NAME)
        return draw(d)

    try:
        return cli(NAME, build_checked, draw_checked, argv, supplementary=True, after=write_tables, doc=__doc__)
    except MissingInput as err:
        print(err.code, file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main(sys.argv[1:])
