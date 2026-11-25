"""sf_e9: E9, the wall time per simulated hour against sites x LLMs, and the table e9_steps.tex
(design/sim_spec_ms5.md §5, §7.2; M16-M26; plan §4, part S-F).

Three panels side by side (style.panel_row(..., legend=True, sharey=(False, True, False))), every axis log-log with x
"Sites x LLMs" over one common range (x_range: from the largest 1-2-5 value at or below 0.75 times the smallest point
to the smallest at or above 1.2 times the largest; 50-5,000 on E9's grid, where §7.2's 20-5,000 would leave the left
quarter of each panel empty), and a one-row legend of Sublet and the two-timescale
PD (A6) above them (style.legend_row); every other series carries a direct label on the free space next to it
(common.place_label), the reference lines a label at their right end below the line:
(a) The full menu, E7's (e9/summary.json points of base e7f with the LLM set SML, ordered by sites x LLMs): per
    policy the slow loop per simulated hour (points.<pt>.policies.<tag>.median.slow_loop_s_per_h) in the registry style,
    labeled "slow loop" next to the right end of Sublet's line; the fast loop (fast_loop_s_per_h) in the policy's color
    and line width with its markers small (FAST_MARKER_SCALE; C47), labeled "fast loop" once; the range over the
    alignments (min to max) as 0.6-pt bars without caps (style.errorbars; the caption says they are ranges); real time
    (meta.real_time_s_per_h) as plan §5's reference line labeled "real time" (M19); y "Wall time per simulated hour (s)"
    in two lines (one line, at 9 pt as at C62's LABEL_PT, is longer than the axes are high), decades from y_range over
    every value of (a) and (b) and real time (0.01-10,000 s on E9's grid), shared with (b).
(b) Reduced menu (base e7r, SML): the same series, and the LP bound's build and solve time per simulated hour
    (e9/summary.json lp.<pt>.{median,min,max}.s_per_h) in the registry's computed lower bound (lb: black, dashed),
    labeled "LP solve time" (on a wall-time axis "LP bound" alone reads as a bound on time); its range over the
    alignments as a band (style.band: black at alpha 0.18, plan §5's other uncertainty style) under every policy
    layer, since bars at the policies' x lie under their markers and bars (print check, 2026-10-30).
(c) Slow steps on the full menu: per point the slow-step P99 (slow_step_p99_s) of Sublet and A6 with their ranges, and
    the slow slot (meta.slow_slot_s) as a reference line labeled "5-min slot"; y "Slow-step P99 (s)", decades over
    the values and the slot (0.01-1,000 s on E9's grid). The longest step is in the table.
Panel titles on the baseline of the letters (common.panel_title; C62: at the caption size, LABEL_PT). The LLM-axis
points (e7f V8 S and ML) are in the table only (M26). A value that is null in the summary (a run that did not finish) leaves a gap with its note.

The caption draft (build, from the extract) gives the line encoding of the loops (lines with markers: slow; with small
markers: fast), the points' V, why (a) has no LP bound (MS5-spec measurement 4's LP estimate at (a)'s points against the
job's memory cap, read when present), the host's load at the jobs' starts, the crossing of the two fast loops and
their largest difference from there on (computed from the extract; Sublet's line covers the other where they meet),
and the LPs that measurement 9 completed.

The after hook writes e9_steps.tex (a longtable; figs.common.write_table) from the extract's `table`: one row per run
point and policy with menu, V, LLMs, sites, units, sites x LLMs, the slow and fast loop per simulated hour, the setup,
the slow-step P50 (ms), P99 and maximum, the fast-step P99 (ms), the peak memory (ru_maxrss) and the cost over BL0a
(medians over the alignments), ordered by menu, then V (the LLM-axis rows after the SML row at their V); then one row
per LP point with variables, nonzeros (medians), the merged sites (their range over the alignments), the solve time,
the time per simulated hour, the peak and the objective over BL0a. Each column of times has fixed decimals (the
column's smallest value with TABLE_SIG significant digits), so that its decimal points line up; medians of counts
are rounded half up.

MS6 C47 (design/ms6_spec.md M2, M4): "Sublet" above is the summary's tag of the one-way guard around the lagged BL5
at MS4's allowance, drawn as the registry key sublet_ms4 (GUARD; 1.0-pt line, as A6's, still drawn last), whose label
the legend row and the table print; the caption's note on the fast loops says that the line drawn last covers the
other (as built "Sublet's thicker line", false at 1.0 pt). The fast loops carry their policies' markers, small
(FAST_MARKER_SCALE; as built they had none): sublet_ms4's sky blue and A6's pink
print as one grey, and the two thin lines cross near 1,000 sites x LLMs (print check of the gate); the caption names
the encoding (slow: lines with markers; fast: lines with small markers). In e9_steps.tex a label is split before
" + " and its
parenthesis (ms4_lib.label_lines), the further lines indented on rows of their own, and TABCOLSEP is 3.0 pt.

Run from code/sim: python -m figs.supp.sf_e9 [--from-extract [JSON]].

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): each longtable's head on its later pages opens
with "Table <n>, continued", and the LP longtable, which has no caption, steps the table counter back before it
starts (s_f1.tex did it after the \\input).
"""
from __future__ import annotations

import hashlib
import math
import sys
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.ticker import NullLocator

from figs import style
from figs.common import (LINE_STEP_PT, MissingKey, _top_tick_room, align_baselines, cli, finite, maybe, need,
                         panel_title, place_label, points_pt, thin_tick_labels, write_table)
from figs.inputs import Inputs
from figs.supp.ms4_lib import DRAWN_KEY, drop_idle_halos, label_lines, log_ticks, tag_of, tex_label
from figs.table3_e7 import HORIZON_WORDS

NAME = "sf_e9"
E9 = "code/sim/out/e9/summary.json"
# MS5-spec measurement 9 (design/sim_spec_ms5.md §5.9 as amended): E9's LPs that M18's gate skipped, solved by the same
# job function with the gate at 3,000 MB; read when present, for the summary it names (sha256), and only for LPs on
# E9's own instance and schedule
GATED = "code/sim/out/ms5spec/e9_lp_gated.json"
# MS5-spec measurement 4's grid (design/sim_spec_ms5.md §5.2, §5.3): the LP rule's memory estimate at every point of
# E9's grid; read when present, for the caption's clause on why (a) has no LP bound (checked against the job's cap)
GRID = "code/sim/out/ms5spec/e9_sizing_grid.json"
TABLE = "e9_steps.tex"
TABLES = (TABLE,)                             # the tables the after hook writes (as sf_s1.TABLES)
KEYS = style.SUPP_POLICIES_MS5[NAME]          # sublet_ms4, a6, lb
# C47 (design/ms6_spec.md M2, M4): E9 ran the one-way guard around the lagged BL5 at MS4's allowance (tag Sublet,
# recorded style key sublet; ms4_lib.DRAWN_KEY), drawn as its configuration key sublet_ms4, still last (on top)
GUARD = "sublet_ms4"
RUN_KEYS = ("a6", GUARD)                      # drawn in this order (the guard last, as Sublet was; plan §5)
LP_KEY = "lb"
# the LP's range band under every policy layer (the bars sit 0.01 below their policy's zorder; not in §7.2)
Z_BAND = min(style.POLICIES[k].zorder for k in (*RUN_KEYS, LP_KEY)) - 0.05
BAND_PROBE_N = 25                             # band_obstacle: vertical segments per stretch, under 1 pt apart at W2
PANELS = (("a", "e7f", "SML"), ("b", "e7r", "SML"), ("c", "e7f", "SML"))
LOOP_FIELDS = ("slow_loop_s_per_h", "fast_loop_s_per_h", "slow_step_p99_s")
TABLE_RUN_FIELDS = ("slow_loop_s_per_h", "fast_loop_s_per_h", "setup_s", "slow_step_p50_s", "slow_step_p99_s",
                    "slow_step_max_s", "fast_step_p99_s", "peak_rss_mb", "cost_over_bl0a")
TABLE_LP_FIELDS = ("n_vars", "nnz", "n_sites_merged", "solve_s", "s_per_h", "peak_rss_mb", "objective_over_bl0a")
X_LADDER = (1.0, 2.0, 5.0)                    # x_range's end values (not in §7.2)
X_LO_FACTOR, X_HI_FACTOR = 0.75, 1.2          # ... at most 0.75 times the smallest point, at least 1.2 times the
#                                               largest (not in §7.2; 0.5 left an empty quarter of each panel)
Y_PAD = 1.2                                   # y_range: the decades around the values / and x this factor
DIRECT = ("slow", "fast", "lp")              # the direct labels (LABELS keys), placed in this order
FAST_MARKER_SCALE = 0.7                       # C47: a fast loop's markers at 0.7 of the registry size (2.45 pt), at
#                                               every point (print check of the gate)
TABCOLSEP = "3.0pt"                           # e9_steps.tex at footnotesize: as the MS4 supplementary tables
#                                               (e7_total_accounting.tex); fills a one-column text width without an
#                                               overfull box (print check, 2026-10-30; 2.0 pt ran the columns together).
#                                               C47: 3.0 pt, from 3.4 pt, since the policy column's widest line,
#                                               sublet_ms4's indented "($B_0=10\\%$ BL0a)", made it 9 pt too wide
TABLE_SIG = 2                                 # a column of times: decimals for its smallest value at 2 significant
#                                               digits (not in §7.2)
TABLE_MENU = {"e7f": "full", "e7r": "reduced"}  # the figure's menu names (panel titles) in the table's Menu column
REF_LABEL_PT = 1.5                            # a reference line's label this far below it (not in §7.2)
style.register_supplementary(NAME, "W2", 2.2)
LABELS = {"x": "Sites × LLMs", "a_y": "Wall time per\nsimulated hour (s)", "c_y": "Slow-step P99 (s)",
          # C47: the full menu by its name (as the E7 tables' scope), not by the experiment's ID (print check)
          "titles": {"a": "Full menu", "b": "Reduced menu", "c": "Slow steps, full menu"},
          "slow": "slow loop", "fast": "fast loop", "lp": "LP solve time", "real_time": "real time",
          "slot": "{slot_min:g}-min slot",
          "moved": {"slow": "lines with markers: the slow loops", "fast": "lines with small markers: the fast loops",
                    "lp": "black dashed: the LP bound"},
          # C62: "at 9 pt" dropped (the labels are at TICK_PT)
          "moved_rule": "a direct label that fits nowhere next to its line moves to the caption (M25)",
          "caption": ("Wall time per simulated hour against sites × LLMs ({horizon} per run; medians over {n_al} "
                      "alignment{al_s} at policy seed {seed}, with the range over the alignments as bars and, for "
                      "the LP, as a grey band; invariant checks on{load}). The points are, from left to right, "
                      "$V$ = {vs} layers per trace lender. (a) The full menu of E7 ({rev_f} revocable contracts) and "
                      "(b) the "
                      "reduced menu ({rev_r}): the slow loop (lines with markers) and the fast loop (lines with small "
                      "markers) of each policy; the setup per run (build, inputs, construction and reset) is left "
                      "out and given in Table~\\ref{{tab:e9-steps}}. (b) also gives the time to build and solve the "
                      "LP bound over the day, divided by its simulated hours (black dashed; the merged relaxation on "
                      "the slow grid).{no_lp} (c) The slow-step P99 "
                      "on the full menu. Grey: real time ({real:,.0f} s per simulated hour) and the {slot_min:g}-min "
                      "slow slot."),
          "load": "; the host's 1-min load average at a job's start: median {med:.2f}, at most {max:.2f}",
          "no_lp": (" (a) has no LP bound: on the full menu the LP's estimated memory, at least {est_gb:.1f} GB, "
                    "exceeds the {cap_gb:g} GB cap of a job."),
          "crossing": ("The two fast loops cross between $V$ = {v0} and {v1}{where} and differ by at most {pct:.0f}% "
                       "from $V$ = {v0} on; where they meet, the line of {top}, drawn last, covers the other.")}
# C47: as built "{top}'s thicker line": Sublet's 1.5-pt line; sublet_ms4's is 1.0 pt, as A6's


def ladder_floor(v: float) -> float:
    e = math.floor(math.log10(v))
    return max(m * 10.0 ** k for k in (e - 1, e) for m in X_LADDER if m * 10.0 ** k <= v * (1 + 1e-12))


def ladder_ceil(v: float) -> float:
    e = math.floor(math.log10(v))
    return min(m * 10.0 ** k for k in (e, e + 1) for m in X_LADDER if m * 10.0 ** k >= v * (1 - 1e-12))


def x_range(xs: Sequence[float]) -> list[float]:
    """The common x range: the largest 1-2-5 value at or below X_LO_FACTOR times the smallest point and the smallest
    at or above X_HI_FACTOR times the largest (50 and 5,000 for E9's 84-3,885)."""
    v = [float(x) for x in xs if x is not None and x > 0]
    return [ladder_floor(min(v) * X_LO_FACTOR), ladder_ceil(max(v) * X_HI_FACTOR)]


def y_range(values: Sequence[float]) -> list[float]:
    """Whole decades around the positive values, Y_PAD beyond them (0.01-10,000 s for (a) and (b) on E9's grid)."""
    v = [float(x) for x in values if x is not None and x > 0]
    return [10.0 ** math.floor(math.log10(min(v) / Y_PAD)), 10.0 ** math.ceil(math.log10(max(v) * Y_PAD))]


def run_series(e9: Mapping, pts: Sequence[str], tag: str, field: str) -> dict:
    """{x, median, min, max, note} of one policy's field over the points (a null value kept with its note)."""
    s = {"point": list(pts), "x": [], "median": [], "min": [], "max": [], "note": []}
    for pt in pts:
        p = need(e9, "points", pt, what=E9)
        s["x"].append(need(p, "sites_x_llms", what=f"{E9} points.{pt}"))
        pol, note = maybe(p, "policies", tag)
        for st in ("median", "min", "max"):
            v, n = (None, note) if note is not None else maybe(pol, st, field)
            s[st].append(v)
            if st == "median":
                s["note"].append(n)
    return s


def gated_lps(inp: Inputs, e9: Mapping) -> dict:
    """{point: {alignment: {field: value}}} of the LPs that E9's gate skipped and measurement 9 solved (GATED), or {}
    without that file. The file must name the summary read (its sha256) and record that no file on the LP's code path
    changed since E9's revision (code.lp_code_equal_to_e9), and each LP must be on E9's instance and schedule, solved
    to optimality; anything else raises, so that a stale file is never drawn."""
    if not (inp.root / GATED).is_file():
        return {}
    g = inp.json(GATED)
    sha = hashlib.sha256(inp.path(E9).read_bytes()).hexdigest()
    if need(g, "meta", "e9_summary_sha256", what=GATED) != sha:
        raise style.StyleError(f"{NAME}: {GATED} was made for another {E9} (sha256 differs)")
    if (g.get("code") or {}).get("lp_code_equal_to_e9") is not True:
        raise style.StyleError(f"{NAME}: {GATED} does not record that its LP code is E9's (code.lp_code_equal_to_e9)")
    out: dict = {}
    for jid, j in need(g, "jobs", what=GATED).items():
        ok = (j.get("same_instance_as_e9") is True and j.get("same_schedule_as_e9") is True and j.get("status") == 0
              and j.get("highs_model_status") == 7)
        if not ok:
            raise style.StyleError(f"{NAME}: {GATED} {jid} is not an optimal LP on E9's instance and schedule")
        pt, c = need(j, "point", what=f"{GATED} {jid}"), str(need(j, "c", what=f"{GATED} {jid}"))
        ent, _ = maybe(e9, "lp", pt, "by_alignment", c)
        if ent is None or ent.get("s_per_h") is not None:
            raise style.StyleError(f"{NAME}: {GATED} {jid}: {E9} has no gated LP at {pt}, alignment {c}")
        out.setdefault(pt, {})[c] = {f: j.get(f) for f in TABLE_LP_FIELDS}
    return out


def lp_entry(e9: Mapping, pt: str, gated: Mapping) -> tuple:
    """(entry, note) of E9's LP point: e9/summary.json lp.<pt>, with the median, minimum and maximum over the
    alignments recomputed (np.median of the values present, as e9.agg_alignments) where measurement 9 solved one of
    its gated alignments; the entry then lists those alignments under 'completed'."""
    ent, note = maybe(e9, "lp", pt)
    if note is not None or pt not in gated:
        return ent, note
    by_c = {c: dict(v or {}) for c, v in (ent.get("by_alignment") or {}).items()}
    for c, vals in gated[pt].items():
        by_c[c].update(vals)
    out = {**ent, "by_alignment": by_c, "completed": sorted(int(c) for c in gated[pt])}
    for st in ("median", "min", "max"):
        out[st] = dict(ent.get(st) or {})
    for f in TABLE_LP_FIELDS:
        v = [float(e[f]) for e in by_c.values() if isinstance(e.get(f), (int, float))]
        if v:
            out["median"][f], out["min"][f], out["max"][f] = float(np.median(v)), min(v), max(v)
    return out, None


def lp_series(e9: Mapping, pts: Sequence[str], gated: Mapping) -> dict:
    s = {"point": list(pts), "x": [], "median": [], "min": [], "max": [], "note": []}
    for pt in pts:
        s["x"].append(need(e9, "points", pt, "sites_x_llms", what=E9))
        ent, note = lp_entry(e9, pt, gated)
        vals = {st: (maybe(ent, st, "s_per_h")[0] if note is None else None) for st in ("median", "min", "max")}
        for st in ("median", "min", "max"):
            s[st].append(vals[st])
        s["note"].append(None if vals["median"] is not None else
                         (note or (ent or {}).get("note") or (ent or {}).get("skip_reason") or "null"))
    return s


def no_lp_estimate(inp: Inputs, e9: Mapping, pts: Sequence[str]) -> dict | None:
    """Why (a) has no LP bound: the LP rule's memory estimate (merged, lp_estimate.merged.est_mb_lp) at (a)'s points
    in measurement 4's grid (GRID) against the job's memory cap (E9-1's cap_mb); None without the grid or the cap, or
    if E9 solved an LP at one of the points. Raises if a point is missing from the grid or has another size there, or
    if an estimate is under the cap, so that the caption never states a wrong reason."""
    if not (inp.root / GRID).is_file():
        return None
    cap, note = maybe(e9, "checks", "E9-1", "cap_mb")
    lp_pts = set(need(e9, "meta", "grid", "lp_points", what=E9))
    if note is not None or cap is None or lp_pts & set(pts):
        return None
    g = inp.json(GRID)
    est = []
    for pt in pts:
        gp = need(g, "points", pt, what=GRID)
        if need(gp, "instance", "sites_x_llms", what=f"{GRID} points.{pt}") != e9["points"][pt]["sites_x_llms"]:
            raise style.StyleError(f"{NAME}: {GRID} {pt} is not E9's point (sites x LLMs differ)")
        est.append(float(need(gp, "lp_estimate", "merged", "est_mb_lp", what=f"{GRID} points.{pt}")))
    if min(est) <= float(cap):
        raise style.StyleError(f"{NAME}: {GRID}: an LP estimate of (a) is under the {cap} MB cap; the caption's "
                               "reason for (a)'s missing LP bound would be wrong")
    return {"points": list(pts), "est_mb_lp": est, "cap_mb": float(cap)}


def load_at_start(meta: Mapping) -> dict | None:
    """The 1-min load average of the host at the jobs' starts (meta.loadavg_start, the first of the three values):
    the number of jobs, the median and the maximum; None where the summary has none."""
    la = [v[0] for v in (meta.get("loadavg_start") or {}).values() if v and v[0] is not None]
    return {"n_jobs": len(la), "median": float(np.median(la)), "max": float(max(la))} if la else None


def panel_points(e9: Mapping, base: str, llm_set: str) -> list[str]:
    """The run points of `base` with the LLM set `llm_set` (meta.grid.run_points), ordered by sites x LLMs."""
    pts = [pt for pt in need(e9, "meta", "grid", "run_points", what=E9)
           if need(e9, "points", pt, "base", what=E9) == base and need(e9, "points", pt, "llm_set", what=E9) == llm_set]
    if not pts:
        raise MissingKey(f"{E9}: no run point of base {base!r} with the LLM set {llm_set!r}")
    return sorted(pts, key=lambda pt: e9["points"][pt]["sites_x_llms"])


def table_rows(e9: Mapping, tags: Mapping[str, str], gated: Mapping) -> dict:
    runs, lps = [], []
    for pt in need(e9, "meta", "grid", "run_points", what=E9):
        p = need(e9, "points", pt, what=E9)
        head = {"point": pt, "base": p.get("base"), "menu": p.get("menu"), "V": p.get("V"),
                "llms": list(p.get("llms") or []), "n_sites": p.get("n_sites"),
                "n_units": (p.get("n_units") or {}).get("median"), "sites_x_llms": p.get("sites_x_llms")}
        for key in style.legend_order(RUN_KEYS):
            med, note = maybe(p, "policies", tags[key], "median")
            runs.append({**head, "key": key, "label": style.POLICIES[key].label,
                         **{f: (med or {}).get(f) for f in TABLE_RUN_FIELDS}, "note": note})
    for pt in need(e9, "meta", "grid", "lp_points", what=E9):
        p = need(e9, "points", pt, what=E9)
        ent, note = lp_entry(e9, pt, gated)
        med = None if note is not None else ent.get("median")
        span = {f"n_sites_merged_{st}": (None if note is not None else (ent.get(st) or {}).get("n_sites_merged"))
                for st in ("min", "max")}
        lps.append({"point": pt, "base": p.get("base"), "menu": p.get("menu"), "V": p.get("V"),
                    "llms": list(p.get("llms") or []), "sites_x_llms": p.get("sites_x_llms"),
                    **{f: (med or {}).get(f) for f in TABLE_LP_FIELDS}, **span, "note": note})
    return {"runs": runs, "lp": lps}


def build(inp: Inputs) -> dict:
    e9 = inp.json(E9)
    meta = need(e9, "meta", what=E9)
    tags = tag_of(need(meta, "policies", what=f"{E9} meta"), RUN_KEYS, f"{E9} meta.policies",
                  drawn=DRAWN_KEY)                  # C47: the recorded style key sublet as sublet_ms4
    gated = gated_lps(inp, e9)
    out: dict = {"tags": tags}
    for p, base, sset in PANELS:
        pts = panel_points(e9, base, sset)
        fields = ("slow_step_p99_s",) if p == "c" else ("slow_loop_s_per_h", "fast_loop_s_per_h")
        out[p] = {"base": base, "llm_set": sset, "points": pts, "V": [e9["points"][pt].get("V") for pt in pts],
                  "series": {key: {f: run_series(e9, pts, tags[key], f) for f in fields} for key in RUN_KEYS}}
        if p == "b":
            lp_pts = [pt for pt in pts if pt in need(meta, "grid", "lp_points", what=f"{E9} meta.grid")]
            out[p]["lp"] = lp_series(e9, lp_pts, gated)
    xs = [x for p, _, _ in PANELS for s in out[p]["series"][RUN_KEYS[0]].values() for x in s["x"]]
    real = float(need(meta, "real_time_s_per_h", what=f"{E9} meta"))
    slot = float(need(meta, "slow_slot_s", what=f"{E9} meta"))

    def vals(*blocks):
        return [v for b in blocks for st in ("median", "min", "max") for v in b[st]]
    ab = [s for p in ("a", "b") for k in RUN_KEYS for s in out[p]["series"][k].values()] + [out["b"]["lp"]]
    cc = [out["c"]["series"][k]["slow_step_p99_s"] for k in RUN_KEYS]
    grid = need(meta, "grid", what=f"{E9} meta")
    rev = {}
    for base in ("e7f", "e7r"):
        pts = [pt for pt in grid["run_points"] if e9["points"][pt]["base"] == base]
        rev[base] = sorted({e9["points"][pt].get("n_revocable_contracts") for pt in pts} - {None})
    horizon = float(need(meta, "horizon_min", what=f"{E9} meta"))
    out.update({"axes": {"x": x_range(xs), "y_ab": y_range(vals(*ab) + [real]), "y_c": y_range(vals(*cc) + [slot])},
                "real_time_s_per_h": real, "slow_slot_s": slot, "fast_slot_s": meta.get("fast_slot_s"),
                "table": table_rows(e9, tags, gated),
                "lp_completed": {pt: {"V": e9["points"][pt].get("V"), "alignments": sorted(int(c) for c in v)}
                                 for pt, v in sorted(gated.items())},
                "grid": {"alignments": list(need(grid, "alignments", what=f"{E9} meta.grid")),
                         "policy_seed": grid.get("policy_seed"), "horizon_min": horizon,
                         "revocable_contracts": rev, "llm_axis_points": [pt for pt in grid["run_points"]
                                                                          if e9["points"][pt]["llm_set"] != "SML"],
                         "lp_gate_mb": (meta.get("lp") or {}).get("gate_mb")},
                "no_lp_a": no_lp_estimate(inp, e9, out["a"]["points"]),
                "load": load_at_start(meta),
                "meta": {"git_revision": meta.get("git_revision"), "reduced": bool(meta.get("reduced")),
                         "host": meta.get("host")},
                "sources": list(inp.sources)})
    out["labels"] = {**LABELS, "slot": LABELS["slot"].format(slot_min=slot / 60.0)}
    moved = layout(out)
    out["layout"] = {"moved": moved, "rule": LABELS["moved_rule"]}
    out["labels"]["caption"] = caption(out)
    return out


def layout(data: Mapping) -> list[str]:
    """The direct labels that fit nowhere in their panels (draw's probe, without a layout): they move to the caption
    (M25), and draw() then leaves them out; the result is stored in the extract, so a redraw is exact."""
    fig = draw({**data, "layout": None})
    return list(fig._sublet_moved)


def horizon_text(minutes: float) -> str:
    return HORIZON_WORDS.get(int(minutes), f"{minutes:g} min") if float(minutes).is_integer() else f"{minutes:g} min"


def and_list(items: Sequence) -> str:
    """'1', '1 and 2', '1, 2 and 3'."""
    s = [str(i) for i in items]
    return s[0] if len(s) == 1 else ", ".join(s[:-1]) + " and " + s[-1]


def completed_text(done: Mapping, gate_mb: float | None = None) -> str:
    """The sentence on the LPs that E9's memory gate skipped and measurement 9 solved (caption and table), from the
    extract, in the reader's terms (V and the alignment; the gate on the LP's estimated memory, not its measured
    peak, which stayed under the gate)."""
    vs = sorted({v["V"] for v in done.values()})
    cs = sorted({c for v in done.values() for c in v["alignments"]})
    one = len(cs) == 1
    gate = f" of {gate_mb:,.0f} MB" if gate_mb else ""
    return (f"At $V$ = {and_list(vs)} the LP{'' if one else 's'} of alignment{'' if one else 's'} {and_list(cs)} "
            f"{'was' if one else 'were'} not solved in E9's run, since {'its' if one else 'their'} estimated memory "
            f"exceeded the LP runs' gate{gate}; {'it was' if one else 'they were'} solved separately on the same "
            f"instance and {'is' if one else 'are'} included in the median and range.")


def fast_crossings(d: Mapping) -> list[dict]:
    """Per panel (a), (b): where the two fast loops first cross (the V of the points before and after the first
    change of sign of Sublet's minus A6's median) and their largest difference from the point before on, in percent
    of the smaller (the caption's note on the coinciding lines); panels without a crossing are left out."""
    out = []
    for p in ("a", "b"):
        ser, vs = d[p]["series"], d[p].get("V")
        if vs is None:
            continue
        s, a = (finite(ser[k]["fast_loop_s_per_h"]["median"]) for k in (GUARD, "a6"))
        idx = np.flatnonzero(np.isfinite(s) & np.isfinite(a) & (s > 0) & (a > 0))
        sg = np.sign(s[idx] - a[idx])
        cut = [i for i in range(len(idx) - 1) if sg[i] == 0 or sg[i] * sg[i + 1] < 0]
        if not cut:
            continue
        i = cut[0]
        rest = idx[i:]
        pct = 100.0 * float(np.max(np.maximum(s[rest], a[rest]) / np.minimum(s[rest], a[rest]) - 1.0))
        out.append({"panel": p, "v0": vs[idx[i]], "v1": vs[idx[i + 1]], "pct": pct})
    return out


def crossing_text(d: Mapping) -> str:
    """The caption's note on the two fast loops (fast_crossings): one sentence where both panels cross between the
    same points, else one per panel."""
    cr = fast_crossings(d)
    top = style.POLICIES[RUN_KEYS[-1]].label          # the series drawn last
    if not cr:
        return ""
    if len({(c["v0"], c["v1"]) for c in cr}) == 1:
        return LABELS["crossing"].format(v0=cr[0]["v0"], v1=cr[0]["v1"], where="", top=top,
                                         pct=max(c["pct"] for c in cr))
    return " ".join(LABELS["crossing"].format(v0=c["v0"], v1=c["v1"], where=f" in ({c['panel']})", top=top,
                                              pct=c["pct"]) for c in cr)


def caption(d: Mapping) -> str:
    """The caption draft (§7.2), every number read from the extract."""
    g = d["grid"]
    rev = {b: "/".join(str(v) for v in vs) or "–" for b, vs in g["revocable_contracts"].items()}
    n = len(g["alignments"])
    vs = sorted({v for p in ("a", "b") for v in (d[p].get("V") or []) if v is not None})
    ld = d.get("load")
    load = LABELS["load"].format(med=ld["median"], max=ld["max"]) if ld else ""
    na = d.get("no_lp_a")
    no_lp = (LABELS["no_lp"].format(est_gb=min(na["est_mb_lp"]) / 1024.0, cap_gb=na["cap_mb"] / 1024.0)
             if na else "")
    text = LABELS["caption"].format(horizon=horizon_text(g["horizon_min"]), n_al=n, al_s="s" if n != 1 else "",
                                    seed=g["policy_seed"], rev_f=rev.get("e7f", "–"), rev_r=rev.get("e7r", "–"),
                                    real=d["real_time_s_per_h"], slot_min=d["slow_slot_s"] / 60.0, load=load,
                                    vs=and_list(vs) if vs else "–", no_lp=no_lp)
    cross = crossing_text(d)
    if cross:
        text += " " + cross
    done = d.get("lp_completed") or {}
    if done:
        text += " " + completed_text(done, g.get("lp_gate_mb"))
    # the slow and fast labels' encoding is always in the caption (above); a moved LP label adds its line
    if "lp" in (d.get("layout") or {}).get("moved", []):
        text += " " + LABELS["moved"]["lp"][:1].upper() + LABELS["moved"]["lp"][1:] + "."
    return text


# ---------------------------------------------------------------------------------------------------------------
def decades(y: Sequence[float]) -> list[float]:
    """The powers of ten from y[0] to y[1] (whole decades, y_range)."""
    return [10.0 ** e for e in range(round(math.log10(y[0])), round(math.log10(y[1])) + 1)]


def log_axes(ax, x: Sequence[float], y: Sequence[float]) -> None:
    """Log-log axes over the x and y ranges: x ticks from ms4_lib.log_ticks (thinned where tick labels would crowd),
    y ticks at the decades; plain labels, no minor ticks."""
    style.log_axis(ax, "x", ticks=log_ticks(*x))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlim(*x)
    style.log_axis(ax, "y", ticks=decades(y))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_ylim(*y)
    _top_tick_room(ax)               # the top decade's label clears the panel letter and title above the axes
    thin_tick_labels(ax)


def draw_range(ax, key: str, s: Mapping) -> None:
    x, y, lo, hi = finite(s["x"]), finite(s["median"]), finite(s["min"]), finite(s["max"])
    ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi) & (hi > lo)
    if ok.any():
        style.errorbars(ax, key, x[ok], y[ok], lo[ok], hi[ok])


def draw_band(ax, key: str, s: Mapping):
    """The range of a series as a band (style.band: its color at alpha 0.18) from min to max, under every policy
    layer (Z_BAND, below the policies' bars), with a gap where a value is missing; None if none."""
    x, lo, hi = finite(s["x"]), finite(s["min"]), finite(s["max"])
    ok = np.isfinite(x) & np.isfinite(lo) & np.isfinite(hi)
    if not ok.any():
        return None
    band = style.band(ax, key, x, lo, hi, where=ok, zorder=Z_BAND)
    band._sublet_role = "range_band"
    return band


def band_obstacle(ax, s: Mapping):
    """A LineCollection of vertical segments that fills the band of `s` (draw_band), BAND_PROBE_N per stretch between
    two points (straight in display space, as the band's edges), added for the label placement only: the occupancy
    of common.place_label counts lines and line collections but not filled areas, so a label's white halo would
    otherwise cut into the band. The caller removes it once the labels are placed; None if there is no band."""
    from matplotlib.collections import LineCollection
    x, lo, hi = finite(s["x"]), finite(s["min"]), finite(s["max"])
    ok = np.isfinite(x) & np.isfinite(lo) & np.isfinite(hi)
    if not ok.any():
        return None
    with np.errstate(all="ignore"):
        p_lo = ax.transData.transform(np.column_stack([x, lo]))
        p_hi = ax.transData.transform(np.column_stack([x, hi]))
    segs = [np.array([p_lo[i], p_hi[i]]) for i in np.flatnonzero(ok)]
    for i in range(len(x) - 1):
        if ok[i] and ok[i + 1]:
            f = np.linspace(0.0, 1.0, BAND_PROBE_N)[1:-1, None]
            a, b = p_lo[i] + f * (p_lo[i + 1] - p_lo[i]), p_hi[i] + f * (p_hi[i + 1] - p_hi[i])
            segs += [np.array([u, v]) for u, v in zip(a, b)]
    inv = ax.transData.inverted()
    lc = LineCollection([inv.transform(sg) for sg in segs], linewidths=style.UNCERTAINTY_PT, alpha=0.0)
    ax.add_collection(lc, autolim=False)
    lc._sublet_role = "band_probe"
    return lc


def draw_loops(ax, series: Mapping) -> dict:
    """Each policy's slow loop (registry style) and fast loop (its color and width, its markers small:
    FAST_MARKER_SCALE; C47) with their ranges; returns the drawn lines by (key, field)."""
    lines = {}
    for key in RUN_KEYS:
        for field, small in (("fast_loop_s_per_h", True), ("slow_loop_s_per_h", False)):
            s = series[key].get(field)
            if s is None:
                continue
            draw_range(ax, key, s)
            kw = dict(markersize=style.policy(key).markersize * FAST_MARKER_SCALE) if small else {}
            ln = style.plot_policy(ax, key, finite(s["x"]), finite(s["median"]), **kw)
            ln._sublet_loop = field
            lines[(key, field)] = ln
    return lines


def ref_label(ax, y: float, text: str) -> None:
    """A reference line's label next to its right end, on the free space nearest that end (common.place_label: clear
    of the data, so that a series ending near the line does not run into it; the white halo dropped where nothing is
    under the label, ms4_lib.drop_idle_halos), else right-aligned just below the line's right end."""
    x1 = ax.get_xlim()[1]
    end = np.array([ax.transData.transform((x1, y))]) * (style.BP_PER_IN / ax.figure.dpi)
    t = place_label(ax, text, end, color=style.THEORY_LABEL_GREY)
    if t is None:
        t = ax.annotate(text, xy=(x1, y), xytext=(-1.0, -REF_LABEL_PT), textcoords="offset points", ha="right",
                        va="top", fontsize=style.TICK_PT, color=style.THEORY_LABEL_GREY, zorder=style.Z_THEORY_LABEL)
    else:
        drop_idle_halos(ax, [t])
    t._sublet_role = "reference_label"


def ends_pt(ax, s: Mapping, n: int = 2) -> np.ndarray:
    """The last n finite points of a series in display pt (where a label at the line's right end goes)."""
    p = points_pt(ax, s["x"], s["median"])
    return p[-n:] if len(p) else p


def label_near(ax, text: str, near: np.ndarray, others: list):
    """A direct label (black, TICK_PT) on the free space nearest `near` and nearer to it than to `others`
    (common.place_label); None (nothing drawn) where it fits nowhere."""
    other = np.concatenate(others) if others else None
    t = place_label(ax, text, near, others=other, color="black")
    if t is not None:
        t._sublet_role = "direct_label"
    return t


def direct_labels(ax_a, ax_b, data: Mapping, lab: Mapping, moved: Sequence[str] | None) -> list[str]:
    """The direct labels of DIRECT: "slow loop" next to the right end of Sublet's slow line in (a), "fast loop" once
    next to the right ends of both fast lines in (a), each nearer to its own line(s) than to the other kind's points,
    and "LP solve time" next to the LP line's right end in (b), nearer to it than to the loops' points and clear of
    the LP's band (band_obstacle); where a label fits nowhere next to the right end, it goes next to any point of its
    line(s). With `moved` None
    (build's probe, layout()), a label that fits nowhere is left out and named in the result; otherwise the labels
    of `moved` are left out (they move to the caption, M25) and any other that does not fit raises StyleError."""
    sa, sb, lp = data["a"]["series"], data["b"]["series"], data["b"]["lp"]
    fast = [ends_pt(ax_a, sa[k]["fast_loop_s_per_h"]) for k in RUN_KEYS]
    slow = [points_pt(ax_a, sa[k]["slow_loop_s_per_h"]["x"], sa[k]["slow_loop_s_per_h"]["median"]) for k in RUN_KEYS]
    others_b = [points_pt(ax_b, sb[k][f]["x"], sb[k][f]["median"]) for k in RUN_KEYS for f in sb[k]]
    fast_all = [points_pt(ax_a, sa[k]["fast_loop_s_per_h"]["x"], sa[k]["fast_loop_s_per_h"]["median"])
                for k in RUN_KEYS]
    sub = sa[GUARD]["slow_loop_s_per_h"]
    # per label (panel, its points to be near, first its right end and then its whole line, the other points)
    todo = {"slow": (ax_a, (ends_pt(ax_a, sub), points_pt(ax_a, sub["x"], sub["median"])), fast_all),
            "fast": (ax_a, (np.concatenate(fast), np.concatenate(fast_all)), slow),
            "lp": (ax_b, (ends_pt(ax_b, lp), points_pt(ax_b, lp["x"], lp["median"])), others_b)}
    out = []
    for name in DIRECT:
        if moved is not None and name in moved:
            continue
        ax, nears, others = todo[name]
        if not any(len(near) and label_near(ax, lab[name], near, others) is not None for near in nears):
            if moved is not None:
                raise style.StyleError(f"{NAME}: the direct label {lab[name]!r} fits nowhere in its panel, but the "
                                       "extract's layout does not move it (rebuild the extract from the summary)")
            out.append(name)
    return out


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    ax_ = data["axes"]
    t_ab = [style.PLAIN(v) for v in decades(ax_["y_ab"])]
    t_c = [style.PLAIN(v) for v in decades(ax_["y_c"])]
    res_a = style.ytick_reserve(fig, t_ab, ylabel=True) + (lab["a_y"].count("\n")) * LINE_STEP_PT / style.BP_PER_IN
    res_c = style.ytick_reserve(fig, t_c, ylabel=True)
    axes = style.panel_row(fig, (1, 1, 1), legend=True, sharey=(False, True, False), left=(res_a, None, res_c))
    ax_a, ax_b, ax_c = axes
    log_axes(ax_a, ax_["x"], ax_["y_ab"])
    log_axes(ax_c, ax_["x"], ax_["y_c"])
    style.log_axis(ax_b, "x", ticks=log_ticks(*ax_["x"]))
    ax_b.xaxis.set_minor_locator(NullLocator())
    ax_b.set_xlim(*ax_["x"])
    thin_tick_labels(ax_b)
    for ax in axes:
        ax.set_xlabel(lab["x"])
    ax_a.set_ylabel(lab["a_y"])
    ax_c.set_ylabel(lab["c_y"])
    real, slot = data["real_time_s_per_h"], data["slow_slot_s"]
    lines = {}
    for ax, p in ((ax_a, "a"), (ax_b, "b")):
        style.reference_line(ax, y=real)
        lines[p] = draw_loops(ax, data[p]["series"])
    lp = data["b"]["lp"]
    draw_band(ax_b, LP_KEY, lp)
    style.plot_policy(ax_b, LP_KEY, finite(lp["x"]), finite(lp["median"]))
    style.reference_line(ax_c, y=slot)
    for key in RUN_KEYS:
        s = data["c"]["series"][key]["slow_step_p99_s"]
        draw_range(ax_c, key, s)
        style.plot_policy(ax_c, key, finite(s["x"]), finite(s["median"]))
    ref_label(ax_a, real, lab["real_time"])
    ref_label(ax_c, slot, lab["slot"])
    lay = data.get("layout")
    probe = band_obstacle(ax_b, lp)               # the LP band counts as drawn for the labels' placement only
    moved = direct_labels(ax_a, ax_b, data, lab, None if lay is None else lay["moved"])
    if probe is not None:
        probe.remove()
    fig._sublet_moved = moved
    letters = style.panel_letters(axes)
    for ax, letter, (p, _, _) in zip(axes, letters, PANELS):     # C62: at the caption size, on the letters' baseline
        panel_title(ax, letter, lab["titles"][p], fontsize=style.LABEL_PT)
    leg = style.legend_row(fig, RUN_KEYS)
    # C62: the guard's mathtext label printed 0.9 pt above its neighbor's baseline (the PDF rounds mathtext metrics)
    align_baselines(leg.get_texts())
    return fig


# ---------------------------------------------------------------------------------------------------------------
def _num(v):
    return None if v is None or not math.isfinite(float(v)) else float(v)


def _decimals(values, n: int = TABLE_SIG) -> int:
    """The decimals of a column: its smallest nonzero magnitude with n significant digits (0 for no value)."""
    v = [abs(x) for x in map(_num, values) if x]
    return max(n - 1 - math.floor(math.log10(min(v))), 0) if v else 0


def _fixed(v, d: int) -> str:
    """`v` with d decimals and a thousands separator; '--' where missing."""
    v = _num(v)
    if v is None:
        return "--"
    s = f"{v:,.{d}f}"
    return s.replace("-", "$-$") if s.startswith("-") else s


def _int(v) -> str:
    """A count (or the median of counts, which may end in .5) rounded half up, with a thousands separator."""
    v = _num(v)
    return "--" if v is None else f"{int(Decimal(repr(v)).quantize(Decimal(1), rounding=ROUND_HALF_UP)):,}"


def _span(lo, hi) -> str:
    """A count's range over the alignments ('80--110'; one value where they are equal)."""
    return _int(lo) if _num(lo) == _num(hi) or _num(hi) is None else f"{_int(lo)}--{_int(hi)}"


def _menu(r: Mapping) -> str:
    return TABLE_MENU.get(r.get("base"), r.get("menu") or "")


def run_order(runs: Sequence[Mapping]) -> list[Mapping]:
    """The run rows by menu (in their order of appearance), then V, then the point's order, so that the LLM-axis
    points follow the SML row at their V (the policies of a point keep their order)."""
    base = {b: i for i, b in enumerate(dict.fromkeys(r["base"] for r in runs))}
    pos = {pt: i for i, pt in enumerate(dict.fromkeys(r["point"] for r in runs))}
    return sorted(runs, key=lambda r: (base[r["base"]], math.inf if r["V"] is None else r["V"], pos[r["point"]]))


def llm_axis_text(t: Mapping, g: Mapping) -> str:
    """The table caption's sentence on the LLM-axis rows (meta.grid's points with another LLM set), from the extract."""
    axis = [r for r in t["runs"] if r["point"] in set(g.get("llm_axis_points") or [])]
    rows = list({r["point"]: r for r in axis}.values())
    if not rows:
        return ""
    sets = and_list([r"\{" + ", ".join(r["llms"]) + r"\}" for r in rows])
    vs = and_list(sorted({r["V"] for r in rows}))
    return (f" The rows with the LLM set{'s' if len(rows) > 1 else ''} {sets} at $V$ = {vs} (the LLM axis) are in "
            "this table only.")


def steps_tex(t: Mapping, g: Mapping, done: Mapping | None = None) -> str:
    """e9_steps.tex: the longtable of the runs (one row per run point and policy, with the caption), then the LP
    points in a longtable of their own (its own head), both at footnotesize. C50 (design/ms6_spec.md §7.2, the D5
    review; §7.1 D4's script items): each head opens with "Table <n>, continued" on the later pages, and the LP
    longtable, which has no caption, steps the table counter back before it starts."""
    n = len(g["alignments"])
    # two header lines without \multicolumn (in a longtable's head it widens the caption row, sf_s1.points_tex)
    runs_hdr = (r"Menu & $V$ & LLMs & Sites & Units & Sites & Policy & Slow & Fast & Setup & Slow & Slow & Slow & "
                r"Fast & Peak & Cost / \\" "\n"
                r" & & & & & $\times$LLMs & & (s/h) & (s/h) & (s) & P50 (ms) & P99 (s) & max (s) & P99 (ms) & (MB) & "
                r"all-fallback \\" "\n")
    head = (r"{\footnotesize\setlength{\tabcolsep}{" + TABCOLSEP + r"}" "\n"
            r"\begin{longtable}{@{}lrlrrrlrrrrrrrrr@{}}" "\n"
            r"\caption{E9 per point: " + horizon_text(g["horizon_min"]) + r" per run, medians over " + f"{n} "
            r"alignment" + ("s" if n != 1 else "") + f" at policy seed {g['policy_seed']}" + r". Menu: E7's full "
            r"or the reduced menu; $V$: the layers per trace lender; sites and units: the point's sites and client "
            r"units. "
            r"Slow and fast: the slow and the fast loop per simulated hour; setup: the instance build, the driver "
            r"inputs, the policy's construction and its reset, once per run; P50, P99 and max of the step times; "
            r"peak: the run's maximum resident set; cost over all-fallback in overflow accounting."
            + llm_axis_text(t, g) + r" LP bound: the merged relaxation of the same instance on the slow grid, with "
            r"its variables and nonzeros, its merged sites (their range over the alignments), its solve time, its "
            r"build and solve time per simulated hour, its peak and its objective over all-fallback."
            + ((" " + completed_text(done, g.get("lp_gate_mb"))) if done else "") + r" A dash marks a value that is "
            r"missing.}\label{tab:e9-steps}\\" "\n"
            r"\toprule" "\n" + runs_hdr + r"\midrule\endfirsthead" "\n"
            r"\multicolumn{16}{@{}l}{Table~\thetable, continued}\\[2pt]" "\n"                         # C50
            r"\toprule" "\n" + runs_hdr + r"\midrule\endhead" "\n"
            r"\bottomrule\endlastfoot" "\n")
    runs = run_order(t["runs"])
    p50_ms = [None if r["slow_step_p50_s"] is None else 1000.0 * r["slow_step_p50_s"] for r in runs]
    p99_ms = [None if r["fast_step_p99_s"] is None else 1000.0 * r["fast_step_p99_s"] for r in runs]
    cols = {f: [r[f] for r in runs] for f in ("slow_loop_s_per_h", "fast_loop_s_per_h", "setup_s",
                                               "slow_step_p99_s", "slow_step_max_s")}
    cols.update(p50_ms=p50_ms, p99_ms=p99_ms)
    dec = {f: _decimals(v) for f, v in cols.items()}
    lines, last = [head], None
    for i, r in enumerate(runs):
        first = r["point"] != last
        if first and last is not None:
            lines.append(r"\addlinespace[2pt]" "\n")
        cells = ([_menu(r), str(r["V"]), ", ".join(r["llms"]), _int(r["n_sites"]), _int(r["n_units"]),
                  _int(r["sites_x_llms"])] if first else [""] * 6)
        # C47: the policy's label split into lines (ms4_lib.label_lines, before " + " and its parenthesis; sublet_ms4's
        # in one line made the table wider than the text), the lines after the first indented on rows of their own
        # C59 (RC19(3)): and after " of the" of the allowance in words, which on one line widened the table by 51 pt
        name, *more = [tex_label(t) for t in label_lines(r["label"], plus=True, of=True)]
        cells += [name] + [_fixed(cols[f][i], dec[f]) for f in ("slow_loop_s_per_h", "fast_loop_s_per_h",
                                                                "setup_s", "p50_ms", "slow_step_p99_s",
                                                                "slow_step_max_s", "p99_ms")]
        cells += [_int(r["peak_rss_mb"]), "--" if r["cost_over_bl0a"] is None else f"{r['cost_over_bl0a']:.3f}"]
        # C47 (print check of the gate): every row of a point's block but its last ends in \\*, so that a page breaks
        # only between points, never inside a policy's name (as relabeled, "+ one-way guard" and its parenthesis could
        # open the next page under the repeated head) or between a point's policies (the rows after its first carry no
        # menu, V and LLMs)
        last_of_point = i + 1 == len(runs) or runs[i + 1]["point"] != r["point"]
        ends = [r" \\*" "\n"] * len(more) + [r" \\" "\n" if last_of_point else r" \\*" "\n"]
        lines.append(" & ".join(cells) + ends[0])
        n = len(cells)
        lines += [" & ".join([""] * 6 + [r"\quad " + m] + [""] * (n - 7)) + e for m, e in zip(more, ends[1:])]
        last = r["point"]
    lines.append(r"\end{longtable}" "\n")
    # the LP block in a longtable of its own, with its own head (on a page break the runs' head would stand over it)
    lp_hdr = (r"Menu & $V$ & LLMs & Sites & Merged & Variables & Nonzeros & Solve & Time & Peak & LP / \\" "\n"
              r" & & & $\times$LLMs & sites & & & (s) & (s/h) & (MB) & all-fallback \\" "\n")
    # C50 (D5 review; D4's script items): uncaptioned, it steps the table counter back first (longtable steps it at
    # every longtable), so that the next table keeps its number (s_f1.tex no longer does it after the \input)
    lines.append(r"\addtocounter{table}{-1}" "\n"                                                       # C50
                 r"\begin{longtable}{@{}lrlrrrrrrrr@{}}" "\n" r"\multicolumn{11}{@{}l}{\textit{LP bound}} \\" "\n"
                 r"\toprule" "\n" + lp_hdr + r"\midrule\endfirsthead" "\n"
                 r"\multicolumn{11}{@{}l}{Table~\thetable, continued}\\[2pt]" "\n"                       # C50
                 r"\toprule" "\n" + lp_hdr +
                 r"\midrule\endhead" "\n" r"\bottomrule\endlastfoot" "\n")
    dec_lp = {f: _decimals([r[f] for r in t["lp"]]) for f in ("solve_s", "s_per_h")}
    for r in t["lp"]:
        cells = [_menu(r), str(r["V"]), ", ".join(r["llms"]), _int(r["sites_x_llms"]),
                 _span(r.get("n_sites_merged_min", r["n_sites_merged"]),
                       r.get("n_sites_merged_max", r["n_sites_merged"])),
                 _int(r["n_vars"]), _int(r["nnz"]), _fixed(r["solve_s"], dec_lp["solve_s"]),
                 _fixed(r["s_per_h"], dec_lp["s_per_h"]), _int(r["peak_rss_mb"]),
                 "--" if r["objective_over_bl0a"] is None else f"{r['objective_over_bl0a']:.3f}"]
        lines.append(" & ".join(cells) + r" \\" "\n")
    lines.append(r"\end{longtable}}" "\n")
    return "".join(lines)


def write_steps_table(data: Mapping, report: Mapping) -> None:
    p = write_table(TABLE, f"% Written by code/sim/figs/supp/sf_e9.py from {E9}; do not edit.\n"
                    + steps_tex(data["table"], data["grid"], data.get("lp_completed")))
    print(f"[{NAME}] wrote {p} ({len(data['table']['runs'])} run rows, {len(data['table']['lp'])} LP rows)")


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, after=write_steps_table, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
