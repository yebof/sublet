"""Fig. 4 (v2, the paper's Fig. 4): E7 on the confirmation weeks; design/sublet_v2.md §11, W1, W6, W9, W10.

Claims: none of its own. The figure shows the pre-registered E7 endpoints of the confirmation as measured
(design/sublet_v2_prereg.md; H1, H2 and H2b of design/sublet_v2.md §6): every number is read from
code/sim/out/sublet_v2/ (main/summary.json, analysis.json and, for what only they hold, main/runs/), the statistics are
descriptive (§4.5, Dependence: the weeks are rotations of one availability and demand series), and every week's result
is shown in (b) (prereg l.241). Sublet is A8P around A9 at the allowance min{W_k, LB'} (registry key sublet_v2, W7).

(a) Cost breakdown (part main, L-tr, policy seed 0, every week of the summary): week cost over all-fallback (BL0a) in
    overflow accounting (r0) as horizontal bars, top to bottom Sublet, Greedy, back-off (BL1-BO), Greedy renting (BL1),
    RetroRenting-style (BL5-cur), RetroRenting, tau >= 1 h (BL5-tau60), Per-borrower ski rental (BL2), SpotHedge-style
    N_Extra = 0 (BL3-0) and CoCaR-style (BL4), named on the y ticks (W1: H1's set without the lagged BL5, whose row is
    in the supplement, and BL5-tau60, which decides H2b). Each bar is the median of r0 over the weeks (table.<tag>.L-tr.
    <week>.0 of the summary), outlined in the policy's color, with the 95% week-bootstrap interval of the median as a
    whisker (W9: ms5b_common.bootstrap_median_ci, seed 20261031, 10,000 resamples, imported read-only), drawn in the
    policy's label color (Policy.label_color, at least 4.5:1 against white: in greyscale the series colors of the light
    policies lost their contrast over the light lease segment; print check of U37) in a white casing (WHISKER_CASING_PT:
    in greyscale the label colors also lost their contrast over the dark fallback segment, in which six of the eight
    lower ends lie on the confirmation; second print check of U37). The bar is split
    in a grey ramp into the ledger components lease (lease_prepaid + lease_rent), loading, routing, fallback and
    stranding (the run files' `grouped`, over the run's bl0a_usd) by the components' medians over the weeks, scaled to
    the bar (W1; the medians of the shares need not sum to the median of r0): segment_c = median(r0) * m_c /
    sum_c' m_c'. A component that is 0 in every bar (loading: bench_e7f's load fee is 0) has no segment and no key
    entry and is named in the extract (a.zero_components). BL0a is the vertical line at 1 across the bars in its
    registry style, above them in a white casing (fig4_e7_e3's Z_BL0A and BL0A_CASING_PT). BL0b ("Provision for
    peak") has a row below the bars, named on the y ticks: off the axis, its median ratio (the run files'
    bl0b_overflow_usd / bl0a_usd, median over the weeks) starts the label column, right at the end of the x spine, and
    an arrow runs from it to the column's right end (print check of U37: the ratio and a short arrow at the column's
    right end sat 1.55 in from the row's name, not joined to the axis). The x spine ends at x_hi (1, or the
    largest bar or whisker beyond it); right of it a label column (common.label_column's idiom) holds BL0a's label
    "All-fallback" level with the first bar, beside the top of its line, and the key of the components, one entry per
    bar row (a patch at the bars' height and the name), centered in the rows between that label and BL0b's row, so
    that at least one empty row parts it from each (key_rows; print check of U37: stacked right under the label, the
    label read as the key's title). Where x_hi > 1, BL0a's line lies inside the bars' range; its label is then set
    above the line's top end, centered on x = 1 in the panel letters' band, and the key is centered in the rows
    above BL0b's. As built: MS4's key band above the bars (draw_a of
    fig4_e7_e3) does not fit here: with the two-row legend the axes are 1.37 in high, and the band with the eight bars
    and BL0b's row leaves a row pitch of 9.55 pt, at which the mathtext names of BL5-tau60 and BL3-0 (11.5 pt high)
    overlap their neighbors (finalize); the column leaves 10.96 pt. The column ends COL_END_PT left of the axes edge
    (BL0b's arrow with it), so that its texts stay about 7 pt clear of (b)'s y label (review of U37: 2.6 pt without).
(b) Every week's result (W1, prereg l.241), from analysis.json: per week, H1's margin Delta_w = min over H1's set of r0
    minus Sublet's r0 (H1.margins.<week>.delta; the registered paired statistic), Sublet's W0 margin under H1's set (the
    least W0 of H2.weeks[i].others minus H2.weeks[i].Sublet; H1's set is H2's `set`) and its W0 margin under BL5-tau60
    (H2b.weeks[i].others.BL5-tau60 minus Sublet), against the week (config seed), with a reference line at 0. The three
    series are no policies: they are drawn in black with markers of their own (MARGIN_STYLES, none a (marker, fill) of
    (c)'s policies; the two W0 margins open, the cost margin filled), keyed in the legend row. Within a week they are
    dodged in x (DODGE, stored in the extract as b.dodge_weeks): the W0 margin under BL5-tau60 B_DODGE weeks left of the
    week, the cost margin as far right, the W0 margin under H1's set on it (print check of U37: undodged, the filled
    cost hexagon and the then filled BL5-tau60 diamond merged in 6 of 16 weeks); no two markers overlap by more than
    MAX_MARKER_OVERLAP of the smaller one (marker_overlaps, on the drawn marker outlines; StyleError). A week in which
    any margin is negative is marked by a shaded column (style.shade_region) and labeled with its number, centered on
    its column (or shifted by the least amount that is clear, its center within the column), at the highest spot below
    the column's lowest marker that is clear of everything drawn (common's occupancy grid and clearance; the weeks
    placed from the highest spot down, so that neighboring labels stack; on the confirmation: BL5-tau60's weeks 302, 307
    and 309; print check of U37: placed on the nearest free space, '307' and '309' sat 7.3 pt beside their columns); the
    y range leaves WEEK_LABEL_ROOM_PT below the lowest point, grown in steps of ROOM_STEP_PT until every label fits.
    The weeks are labeled on the x axis at a regular stride from the first to the last (week_tick_labels). Each W0 of
    analysis.json is checked against main/summary.json W0.0, each H1 margin's `best` against H1's set, and the drawn
    margins against the analysis's counts (H1's wins, H2's weeks below the set; H2b's weeks below the set against its
    rows) (StyleError where they differ). A week without a margin (the missing-run rule of §4.5: a loss for Sublet)
    leaves that point out and is marked and labeled as a negative week is (its label below the lowest point drawn), and
    the caption names it, so that no failure is hidden (prereg §4.5). H2b's failing weeks (its rows without below_all)
    are stored; where they are not BL5-tau60's negative weeks, the caption gives them beside BL5-tau60's.
(c) Decomposition (W1, D10): the median of r0 under L-tr against the median of W0 over the weeks, each with its 95%
    week-bootstrap interval as a bar, for Sublet, Greedy renting (BL1), Greedy + notice layer (BL1N), Greedy + guard
    (BL1-GP), RetroRenting-style (BL5-cur) and RetroRenting + notice layer (BL5N), in their registry styles (the
    interval bars in the policy's label color, so that in greyscale BL1-GP's interval at W0 = 1.009 stays apart from
    the reference line), keyed in the legend row; a reference line at W0 = 1 (the level of all-fallback, named in the
    caption). A9 alone is not drawn: its medians are compared with Sublet's in the extract (c.a9), and the caption says
    that it coincides with Sublet where both medians are within A9_TOL (H6), else gives A9's medians.
Legend: two rows (style.legend_row(rows=2); the figure plan's fallback for Fig. 4, +0.021 page): (c)'s six
policies, markers only, then the three margin series of (b); matplotlib fills it column by column, so the policies take
the first three columns and the margins the last two.

Layout (W1: "width ratios set by the measured fit and stored in the extract"; layout(), from build(), on the figure's
geometry; draw() places the panels from the stored widths, so a redraw is exact): (a)'s left reserve is the widest bar
name at the tick size (style.ytick_reserve); the axes of (b) and (c) and (a)'s bars' range [0, x_hi] have one width,
and (a)'s axes add the label column (COL_GAP_PT and the widest of BL0a's label, the components' key and BL0b's ratio
with its arrow, measured at the tick size); the extract stores the left reserves, the axes widths, x_hi and (a)'s right
x limit. C62 (2026-11-24: 7-pt text, 7.97-pt axis labels and letters): the layout stored as built was measured
at 9 pt; the extract's layout is now layout() on its data at C62's sizes (the narrower names and label column and
style's C62 reserves widen (b) and (c) by 0.21 in each), every data entry unchanged. The run files are not versioned,
so it was recomputed from the versioned extract's data, which is what build() stores on the same inputs.

As built (choices that §11 leaves open): x labels "Trace cost / all-fallback" in (a) and (c) (the same quantity, r0
under L-tr); (b)'s y label "Sublet's margin" (in units of BL0a, as the caption says); (c)'s y label "Worst case $W_0$";
the margins' legend labels MARGIN_LABELS ("best": the per-week least of H1's set); a missing value (a week without a
run, the missing-run rule) leaves its point out, is marked and labeled in (b) and named in the caption and the
extract's notes; the bars' order is W1's list; the caption says "overflow accounting" (the scope of BL0a's USD and of
(a)) and names the policies by their registry labels, as the figure does (print check of U37: tags such as BL0a,
BL5-tau60 and A9 appear nowhere in the figure), and says what (a)'s segments, BL0b's ratio, (c)'s grey line and W0 are;
the extract's status block holds no theory label (the figure states no theory result). The margins' black (no OPT,
LB or attaining instance is drawn in Fig. 4) follows §5's grey ramp for non-policy categories.

The run files are not versioned (C40), so the extract code/sim/out/figs/fig4v2.json lists every main/runs/ file read
with its sha256 (runs_files; W10) and carries every plotted number; it is the figure's source. The caption draft (at
most 4 lines of about 140 characters, W1) is in the extract (labels.caption), every number read from the inputs; the
extract's `scope` names the part, weeks, policy seed, mode and tags it covers (for the claims report, W11). Run from
code/sim: python -m figs.fig4_v2 [--from-extract [JSON]] (figs.common.cli).
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib import patheffects
from matplotlib.lines import Line2D
from matplotlib.markers import MarkerStyle
from matplotlib.ticker import FixedLocator, MaxNLocator

from figs import style
from figs.common import (GRID_RES_PT, LINE_STEP_PT, TICK_GAP_PT, MissingKey, _label_only, _occupancy,
                         align_baselines, align_printed_rows, cli, finite, need, text_width_in)
from figs.fig4_e7_e3 import ARROW_IN, ARROW_TEXT_PT, BL0A_CASING_PT, BL0A_CLEAR_PT, Z_BL0A
# C62: BAR_H (0.62 rows) and BAR_EDGE_PT (0.8 pt) as built, kept by fig4_e7_e3 since sf_e6b's restyle (sf_e6b's bars are
# 0.56 rows high since C62); fig4_v3 reads BAR_EDGE_PT from here
from figs.fig4_e7_e3 import BAR_EDGE_PT, BAR_H
from figs.inputs import Inputs
from sublet.experiments.ms3_common import job_file_name
from sublet.experiments.ms5b_common import BOOT_B, BOOT_SEED, TRACE_MODE, bootstrap_median_ci, stress_modes

NAME = "fig4v2"
MAIN = "code/sim/out/sublet_v2/main/summary.json"
ANALYSIS = "code/sim/out/sublet_v2/analysis.json"
RUNS = "code/sim/out/sublet_v2/main/runs"
KEYS = style.FIGURE_POLICIES[NAME]
SEED = 0                                       # policy seed 0 (§4.4(a), W1)
LEVEL = 0.95
BARS = ("sublet_v2", "bl1_bo", "bl1", "bl5_cur", "bl5_tau60", "bl2", "bl3_0", "bl4")    # (a), top to bottom (W1)
C_KEYS = ("bl1", "bl5_cur", "bl1n", "bl5n", "bl1_gp", "sublet_v2")                    # (c), drawing order: Sublet last
# registry key -> tag of the confirmation (ms5b_common.TAGS; the notes of style._REGISTRY_MS5B)
TAGS = {"sublet_v2": "Sublet", "bl1_bo": "BL1-BO", "bl1": "BL1", "bl5_cur": "BL5-cur", "bl5_tau60": "BL5-tau60",
        "bl2": "BL2", "bl3_0": "BL3-0", "bl4": "BL4", "bl1n": "BL1N", "bl5n": "BL5N", "bl1_gp": "BL1-GP"}
A9_TAG = "A9"
TAU60 = "BL5-tau60"
A9_TOL = 0.001                 # A9 "coincides with Sublet at these medians" where both medians differ by at most this
COMPONENT_ORDER = ("lease", "loading", "routing", "fallback", "stranding")
COMPONENT_LABEL = {"lease": "Lease", "loading": "Loading", "routing": "Routing", "fallback": "Fallback",
                   "stranding": "Stranding"}
MARGINS = ("trace", "w0_set", "w0_tau60")      # (b)'s series
MARGIN_LABELS = {"trace": "Cost vs. best", "w0_set": "$W_0$ vs. best", "w0_tau60": r"$W_0$ vs. $\tau\geq1$ h"}
MARGIN_STYLES = {   # black: the margins are no policies; (marker, fill) apart from (c)'s policies and each other; the
    "trace": dict(marker="h", markerfacecolor="#000000"),     # cost margin filled, the two W0 margins open (a white
    "w0_set": dict(marker="h", markerfacecolor="white"),      # face, so that a contact with the filled hexagon does
    "w0_tau60": dict(marker="d", markerfacecolor="white"),    # not merge; print check of U37)
}
MARGIN_COLOR = "#000000"
B_DODGE = 0.25                 # (b): the W0 margin under BL5-tau60 this many weeks left of its week, the cost margin as
#                                far right (a week is 5.4 pt wide, the markers 3.6 pt; measured on the confirmation, as
#                                built: at 0.25 the largest overlap is 0.10 of a marker, at 0.28-0.32 0.18-0.29, since
#                                a week's cost margin and the next week's BL5-tau60 margin are often level; with
#                                BL5-tau60's diamonds on the left, week 309's label fits under its own diamond, clear
#                                of week 307's, so (b) needs no extra room for the labels)
DODGE = {"trace": B_DODGE, "w0_set": 0.0, "w0_tau60": -B_DODGE}
MAX_MARKER_OVERLAP = 1.0 / 3.0  # (b): no two markers overlap by more than this share of the smaller marker's area
LABELS = {"a_x": "Trace cost / all-fallback", "b_x": "Week", "b_y": "Sublet's margin",
          "c_x": "Trace cost / all-fallback", "c_y": "Worst case $W_0$", "no_data": "no runs"}
WHISKER_CASING_PT = 0.8         # (a): white casing of the whiskers (their width plus this, 0.4 pt on each side), so
#                                 that they read over every grey of the bars (as BL0a's line, fig4_e7_e3)
COL_GAP_PT = 4.0                # (a): the label column starts this far right of x_hi (clear of BL0a's casing)
COL_END_PT = 4.0                # (a): the label column (and BL0b's arrow) ends this far left of (a)'s axes edge, so
#                                 that its texts stay about 7 pt clear of (b)'s y label
KEY_HANDLE_PT = style.TICK_PT  # (a): the key's patch, one font size wide (fig4_e7_e3.KEY_HANDLE) at the bars' height
KEY_TEXT_GAP_PT = 3.6           # (a): patch to name (legend.handletextpad, 0.4 font sizes)
CAPTION_LINE_CHARS = 140        # W1: the caption has at most 4 lines of about this many characters
CAPTION_LINES = 4
B_PAD = 0.08                    # (b), (c): the y range this share beyond the data
C_PAD = 0.07                    # (c): the x range this share beyond the data and intervals
WEEK_LABEL_ROOM_PT = 14.0       # (b): room below the lowest point for a week's label (set for a 9-pt line with its
#                                 clearances; kept at C62, since fig4_v3 reads it)
WEEK_LABEL_GAP_PT = 1.5         # (b): a week's label at least this far below its column's lowest marker
ROOM_STEP_PT = 2.0              # (b): the room below the lowest point grows in these steps until the labels fit
BL0A_LABEL_RISE_PT = 1.0        # (a), x_hi > 1: BL0a's label box (its descent included) this far above the axes top
CAPTION_LOWER = ("a9", "bl0a", "bl0b")      # the caption's names in lower case (inside a sentence)
# The figure draws no theory line and states no theory result, so it carries no status label of C3 (a label is
# copied verbatim where a figure uses it, never paraphrased; W5); only the statistics' status (§4.5).
STATUS = {"statistics": "descriptive (design/sublet_v2.md §4.5, Dependence)"}


# ---------------------------------------------------------------------------------------------------------------
# Inputs
def _boot(values: Sequence[float | None]) -> dict:
    """The registered statistic (W9): median and 95% week-bootstrap interval of the values present."""
    v = [float(x) for x in values if x is not None]
    b = bootstrap_median_ci(v, B=BOOT_B, seed=BOOT_SEED, level=LEVEL)
    return {"median": b["median"], "ci": list(b["ci"]), "n": b["n"]}


def _week_values(block: Any, weeks: Sequence[str]) -> tuple[list, list]:
    """(values by week, weeks without a value) of block.<week>.<SEED> or block.<week> (a number)."""
    vals, missing = [], []
    for w in weeks:
        v = block.get(w) if isinstance(block, Mapping) else None
        if isinstance(v, Mapping):
            v = v.get(str(SEED))
        if v is None:
            missing.append(w)
        vals.append(None if v is None else float(v))
    return vals, missing


def _tags_present(summary: Mapping, tags: Sequence[str]) -> None:
    have = need(summary, "meta", "tags", what=MAIN)
    missing = [t for t in tags if t not in have]
    if missing:
        raise MissingKey(f"{MAIN}: no tag {missing} in meta.tags (have {sorted(have)})")


def _run_rows(summary: Mapping) -> dict:
    """{(tag, mode, week, seed): row} of the summary's run rows of kind 'week'."""
    out = {}
    for r in need(summary, "runs", what=MAIN):
        if r.get("kind") == "week":
            out[(r["tag"], r["mode"], str(r["cell"]), int(r["seed"]))] = r
    return out


def _run_file(inp: Inputs, row: Mapping, files: dict) -> tuple[str, dict]:
    """(repository-relative name, parsed record) of the run file of a summary row (RUNS/<job_file_name(job)>, the
    drivers' rule), read once; its sha256 recorded in `files` (W10)."""
    name = f"{RUNS}/{job_file_name(row['job'])}"
    if name not in files:
        raw = inp.path(name).read_bytes()
        files[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "record": json.loads(raw)}
    return name, files[name]["record"]


def _run_of(rec: Mapping, name: str, mode: str, seed: int) -> dict:
    hits = [r for r in rec.get("runs") or [] if r.get("mode") == mode and int(r.get("policy_seed", -1)) == seed]
    if len(hits) != 1:
        raise MissingKey(f"{name}: {len(hits)} runs with mode {mode!r} and policy seed {seed} (expected 1)")
    return hits[0]


def bar_entry(inp: Inputs, summary: Mapping, rows: Mapping, key: str, weeks: Sequence[str], files: dict) -> dict:
    """(a)'s bar of one key: the median of r0 over the weeks (summary) with its interval, the per-week grouped
    components over the run's BL0a and the total accounting (run files, each checked against the summary's r0), and
    each week's references (BL0a, BL0b, own capacity; in `_refs`, which build() pops)."""
    tag = TAGS[key]
    r0, missing = _week_values(need(summary, "table", tag, TRACE_MODE, what=MAIN), weeks)
    comps: dict[str, list] = {}
    total, refs = [], {}
    for w, v in zip(weeks, r0):
        if v is None:
            continue
        row = rows.get((tag, TRACE_MODE, w, SEED))
        if row is None:
            raise MissingKey(f"{MAIN}: no run row for {tag} {TRACE_MODE} week {w} seed {SEED}")
        name, rec = _run_file(inp, row, files)
        run = _run_of(rec, name, TRACE_MODE, SEED)
        acc = need(run, "accountings", what=name)
        if abs(float(acc["overflow_over_bl0a"]) - v) > 1e-9 * max(1.0, abs(v)):
            raise style.StyleError(f"{name}: overflow_over_bl0a {acc['overflow_over_bl0a']} differs from the summary's "
                                   f"r0 {v}")
        bl0a = float(need(run, "bl0a_usd", what=name))
        for c, usd in need(run, "grouped", what=name).items():
            if c != "total" and not c.endswith("_note") and usd is not None:
                comps.setdefault(c, []).append(float(usd) / bl0a)
        total.append(float(acc["total_over_bl0a"]))
        refs[w] = {k: float(x) for k, x in need(rec, "instances", "base", "references", what=name).items()
                   if isinstance(x, (int, float)) and not isinstance(x, bool)}
    st = _boot(r0)
    return {"tag": tag, "label": style.POLICIES[key].label, "r0": r0, "missing": missing,
            "median": st["median"], "ci_lo": st["ci"][0], "ci_hi": st["ci"][1], "n": st["n"],
            "components_over_bl0a": comps,
            "components_median_over_bl0a": {c: statistics.median(v) for c, v in comps.items() if v},
            "total_over_bl0a_median": statistics.median(total) if total else None, "_refs": refs}


def margin_series(ana: Mapping, summary: Mapping, weeks: Sequence[str]) -> dict:
    """(b): per week Delta_w (H1), the W0 margin under H1's set (H2) and under BL5-tau60 (H2b), from analysis.json;
    each W0 checked against the summary's W0.<SEED>, each margin's `best` against H1's set."""
    h1, h2, h2b = (need(ana, h, what=ANALYSIS) for h in ("H1", "H2", "H2b"))
    if [str(w) for w in need(h1, "weeks", what=ANALYSIS)] != list(weeks):
        raise style.StyleError(f"{ANALYSIS}: H1's weeks {h1['weeks']} are not the summary's {list(weeks)}")
    h1_set = list(need(h2, "set", what=ANALYSIS))
    if TAU60 not in need(h2b, "set", what=ANALYSIS):
        raise MissingKey(f"{ANALYSIS}: H2b's set {h2b['set']} has no {TAU60}")
    w0 = need(summary, "W0", str(SEED), what=MAIN)
    by2 = {str(r["week"]): r for r in need(h2, "weeks", what=ANALYSIS)}
    by2b = {str(r["week"]): r for r in need(h2b, "weeks", what=ANALYSIS)}

    def checked(tag, w, v):
        s = (w0.get(tag) or {}).get(w)
        if (v is None) != (s is None) or (v is not None and abs(float(v) - float(s)) > 1e-12):
            raise style.StyleError(f"{ANALYSIS}: the W0 of {tag} in week {w} is {v}, the summary's {s}")
        return None if v is None else float(v)

    out: dict = {k: [] for k in ("trace", "w0_set", "w0_tau60", "best_trace", "best_w0")}
    notes = []
    for w in weeks:
        m = (h1.get("margins") or {}).get(w) or {}
        d = m.get("delta")
        if m.get("best") is not None and m["best"] not in h1_set:
            raise style.StyleError(f"{ANALYSIS}: H1's best in week {w}, {m['best']}, is not in H1's set {h1_set}")
        out["trace"].append(None if d is None else float(d))
        out["best_trace"].append(m.get("best"))
        if d is None:
            notes.append(f"week {w}: H1's margin missing (runs {m.get('missing')})")
        r2, r2b = by2.get(w), by2b.get(w)
        sub = checked("Sublet", w, r2["Sublet"]) if r2 else None
        if r2b is not None:
            checked("Sublet", w, r2b["Sublet"])
        oth = {t: checked(t, w, v) for t, v in ((r2 or {}).get("others") or {}).items()}
        if sub is None or not oth or any(v is None for v in oth.values()):
            out["w0_set"].append(None)
            out["best_w0"].append(None)
            notes.append(f"week {w}: a W0 of H1's set or Sublet's missing")
        else:
            best = min(oth, key=lambda t: oth[t])
            out["w0_set"].append(oth[best] - sub)
            out["best_w0"].append(best)
        t60 = checked(TAU60, w, ((r2b or {}).get("others") or {}).get(TAU60)) if r2b else None
        out["w0_tau60"].append(None if (t60 is None or sub is None) else t60 - sub)
        if t60 is None or sub is None:
            notes.append(f"week {w}: {TAU60}'s or Sublet's W0 missing")
    neg, lost = [], []
    for i, w in enumerate(weeks):
        vals = {k: out[k][i] for k in MARGINS if out[k][i] is not None and out[k][i] < 0}
        if vals:
            low = min(vals, key=lambda k: vals[k])
            neg.append({"week": w, "x": int(w), "series": sorted(vals), "lowest": low, "y": vals[low]})
        gone = [k for k in MARGINS if out[k][i] is None]
        if gone:                     # the missing-run rule (§4.5): a loss for Sublet, marked like a negative week
            lost.append({"week": w, "x": int(w), "series": gone})
    below = [w for w, v in zip(weeks, out["w0_tau60"]) if v is not None and v < 0]
    # the drawn margins give the analysis's counts (H1's wins, H2's and H2b's weeks below the set)
    counts = {"H1.wins": (h1.get("wins"), sum(1 for v in out["trace"] if v is not None and v > 0)),
              "H2.weeks_below_set": (h2.get("weeks_below_set"),
                                     sum(1 for v in out["w0_set"] if v is not None and v > 0))}
    for name, (have, drawn) in counts.items():
        if have is not None and int(have) != drawn:
            raise style.StyleError(f"{ANALYSIS}: {name} is {have}, the margins drawn give {drawn}")
    h2b_fail = [str(r["week"]) for r in need(h2b, "weeks", what=ANALYSIS) if not r.get("below_all")]
    if h2b.get("weeks_below_set") is not None and int(h2b["weeks_below_set"]) != len(weeks) - len(h2b_fail):
        raise style.StyleError(f"{ANALYSIS}: H2b.weeks_below_set {h2b['weeks_below_set']} is not the {len(weeks)} "
                               f"weeks less the {len(h2b_fail)} weeks without below_all")
    return {"weeks": list(weeks), "x": [int(w) for w in weeks], **out, "dodge_weeks": dict(DODGE),
            "negative": neg, "missing_weeks": lost,
            "notes": notes, "h1_set": h1_set, "h2b_set": list(h2b["set"]), "tau60_below_sublet_weeks": below,
            "h2b_failing_weeks": h2b_fail,
            "sources": {"trace": "analysis.json H1.margins.<week>.delta",
                        "w0_set": "analysis.json min(H2.weeks[i].others) - H2.weeks[i].Sublet",
                        "w0_tau60": "analysis.json H2b.weeks[i].others.BL5-tau60 - H2b.weeks[i].Sublet"}}


def point_entry(summary: Mapping, tag: str, weeks: Sequence[str]) -> dict:
    """(c)'s point: medians of r0 (L-tr) and of W0 over the weeks with their 95% week-bootstrap intervals."""
    r0, m_r0 = _week_values(need(summary, "table", tag, TRACE_MODE, what=MAIN), weeks)
    w0, m_w0 = _week_values(need(summary, "W0", str(SEED), tag, what=MAIN), weeks)
    return {"tag": tag, "r0": _boot(r0), "W0": _boot(w0), "missing_r0": m_r0, "missing_W0": m_w0}


def plain_label(key: str) -> str:
    """A registry label as plain caption text ('RetroRenting, $\\tau\\geq1$ h' -> 'RetroRenting, τ≥1 h'), in lower
    case for the keys of CAPTION_LOWER."""
    s = style.POLICIES[key].label
    for tex, txt in ((r"\tau", "τ"), (r"\geq", "≥"), (r"\mathrm", ""), ("$", ""), ("{", ""), ("}", "")):
        s = s.replace(tex, txt)
    return s[0].lower() + s[1:] if key in CAPTION_LOWER else s


def caption(d: Mapping) -> str:
    """The caption draft of W1 (at most CAPTION_LINES lines of about CAPTION_LINE_CHARS characters), every number read
    from the inputs: BL0a's weekly USD (median over the weeks), what the bars, (a)'s segments, BL0b's ratio, (c)'s grey
    line and W0 are, H1's registered margin and interval, H2's count, H2b's count and weeks, the dependence of the
    weeks, A9 against Sublet, the lagged BL5's row in the supplement; the policies by their registry labels, as the
    figure names them (plain_label)."""
    n = d["n_weeks"]
    h1 = d["h1"]
    t60 = d["tau60_below_sublet_weeks"]
    usd = "–" if d["bl0a_usd_median"] is None else f"{d['bl0a_usd_median']:,.0f}"
    a9 = (f"{plain_label('a9')} alone coincides with Sublet" if d["a9_coincides"] else
          f"{plain_label('a9')} alone: {d['a9']['r0']:.3f}, {d['a9']['W0']:.3f}")
    fail = d.get("h2b_failing_weeks", t60)      # H2b's weeks not below its whole set; BL5-tau60's alone on the data
    h2b = ("" if fail == t60 else f"; H2b's set not above Sublet in {len(fail)}/{n}" +
           (f": {', '.join(fail)}" if fail else ""))
    lost = d.get("missing_weeks") or []
    lost = f" No run in week {', '.join(lost)}: a loss (§4.5)." if lost else ""
    peak = "" if d.get("bl0b_ratio") is None else f"; {plain_label('bl0b')}: {d['bl0b_ratio']}"
    fb = plain_label("bl0a")
    return (f"Fig. 4. E7, {n} confirmation week{'s' if n != 1 else ''} (trace lender, overflow accounting); {fb}: "
            f"{usd} USD/week (median). Medians, 95% intervals. (a) Segments: component medians, scaled{peak}. "
            f"(b) Per week, least of H1's set minus Sublet: trace cost (H1: median {h1['median']:.3f} "
            f"[{h1['ci'][0]:.3f}, {h1['ci'][1]:.3f}]), W0 (>0 in {d['h2_below_set']}/{n}, H2); "
            f"{plain_label('bl5_tau60')} minus Sublet: W0 (<0 in {len(t60)}/{n}{h2b}; "
            f"H2b {'holds' if d['h2b_pass'] else 'fails'}). (c) Grey: {fb}; {a9}.{lost} Weeks: rotations of one "
            f"series; statistics descriptive; {plain_label('bl5_lag')} (H1's set): supplement.")


def build(inp: Inputs) -> dict:
    main = inp.json(MAIN)
    ana = inp.json(ANALYSIS)
    meta = need(main, "meta", what=MAIN)
    _tags_present(main, [TAGS[k] for k in dict.fromkeys(BARS + C_KEYS)] + [A9_TAG, TAU60])
    weeks = sorted(need(main, "table", TAGS["sublet_v2"], TRACE_MODE, what=MAIN), key=int)
    rows = _run_rows(main)
    files: dict = {}

    # (a)
    a: dict = {"order": list(BARS), "accounting": "overflow", "mode": TRACE_MODE, "policy_seed": SEED,
               "weeks": list(weeks)}
    refs: dict = {}
    for key in BARS:
        e = bar_entry(inp, main, rows, key, weeks, files)
        for w, r in e.pop("_refs").items():
            if w in refs and refs[w] != r:
                raise style.StyleError(f"week {w}: the run files of {key} carry other references than {refs[w]}")
            refs[w] = r
        a[key] = e
    present = {c for k in BARS for c in a[k]["components_median_over_bl0a"]}
    drawn = [c for c in COMPONENT_ORDER if any((a[k]["components_median_over_bl0a"].get(c) or 0.0) > 0 for k in BARS)]
    drawn += sorted(c for c in present if c not in COMPONENT_ORDER and
                    any((a[k]["components_median_over_bl0a"].get(c) or 0.0) > 0 for k in BARS))
    a["zero_components"] = sorted(c for c in present if c not in drawn)
    a["components"] = {"order": drawn, "labels": {c: COMPONENT_LABEL.get(c, c) for c in drawn},
                       "note": "lease is lease_prepaid + lease_rent (the run files' grouped components over the run's "
                               "bl0a_usd); each bar's median r0 split by the components' medians over the weeks, "
                               "scaled to the bar (W1)"}
    for key in BARS:
        e = a[key]
        med = e["components_median_over_bl0a"]
        s = sum(med.get(c) or 0.0 for c in drawn)
        e["segments"] = ({c: e["median"] * (med.get(c) or 0.0) / s for c in drawn}
                         if e["median"] is not None and s > 0 else {})

    def ref(field):
        return {w: refs[w][field] for w in weeks if w in refs and refs[w].get(field) is not None}

    bl0a, own = ref("bl0a_usd"), ref("own_capacity_usd")
    b_ovf, b_tot, a_tot = ref("bl0b_overflow_usd"), ref("bl0b_total_usd"), ref("bl0a_total_usd")
    r_ovf = {w: b_ovf[w] / bl0a[w] for w in weeks if w in b_ovf and bl0a.get(w)}
    r_tot = {w: b_tot[w] / a_tot[w] for w in weeks if w in b_tot and a_tot.get(w)}
    usd = {}
    for w in weeks:                                      # BL0a's USD from the summary rows, as the run files'
        r = rows.get((TAGS["sublet_v2"], TRACE_MODE, w, SEED))
        if r is not None and r.get("bl0a_usd") is not None:
            usd[w] = float(r["bl0a_usd"])
            if w in bl0a and abs(bl0a[w] - usd[w]) > 1e-9 * usd[w]:
                raise style.StyleError(f"week {w}: the summary's bl0a_usd {usd[w]} differs from the run files' "
                                       f"{bl0a[w]}")
    a["bl0a"] = {"x": 1.0, "usd_by_week": usd, "usd_median": statistics.median(usd.values()) if usd else None,
                 "label": style.POLICIES["bl0a"].label}
    a["bl0b"] = {"overflow_over_bl0a": statistics.median(r_ovf.values()) if r_ovf else None,
                 "total_over_bl0a": statistics.median(r_tot.values()) if r_tot else None,
                 "overflow_over_bl0a_by_week": r_ovf, "total_over_bl0a_by_week": r_tot, "off_scale": True,
                 "label": style.POLICIES["bl0b"].label,
                 "rule": "median over the weeks of the run files' references bl0b_overflow_usd / bl0a_usd (total "
                         "accounting: bl0b_total_usd / bl0a_total_usd)"}
    a["own_capacity_usd"] = {"by_week": own, "median": statistics.median(own.values()) if own else None}

    # (b)
    b = margin_series(ana, main, weeks)

    # (c)
    c: dict = {"order": list(C_KEYS), "mode": TRACE_MODE, "policy_seed": SEED}
    for key in C_KEYS:
        c[key] = {**point_entry(main, TAGS[key], weeks), "label": style.POLICIES[key].label}
    a9 = point_entry(main, A9_TAG, weeks)
    sub = c["sublet_v2"]
    diff = {f: (None if a9[f]["median"] is None or sub[f]["median"] is None else
                abs(a9[f]["median"] - sub[f]["median"])) for f in ("r0", "W0")}
    coincide = all(v is not None and v <= A9_TOL for v in diff.values())
    c["a9"] = {**a9, "abs_diff_to_sublet": diff, "tol": A9_TOL, "coincides": coincide}

    h1, h2, h2b, h6 = (need(ana, h, what=ANALYSIS) for h in ("H1", "H2", "H2b", "H6"))
    h1m = need(h1, "median_margin", what=ANALYSIS)
    cap = caption({"n_weeks": len(weeks), "bl0a_usd_median": a["bl0a"]["usd_median"],
                   "h1": {"median": float(h1m["median"]), "ci": [float(v) for v in h1m["ci"]]},
                   "h2_below_set": int(h2["weeks_below_set"]),
                   "tau60_below_sublet_weeks": b["tau60_below_sublet_weeks"], "h2b_pass": bool(h2b.get("pass")),
                   "h2b_failing_weeks": b["h2b_failing_weeks"],
                   "missing_weeks": [m["week"] for m in b["missing_weeks"]],
                   "a9_coincides": coincide, "a9": {"r0": a9["r0"]["median"], "W0": a9["W0"]["median"]},
                   "n_stress": len(stress_modes()),
                   "bl0b_ratio": None if a["bl0b"]["overflow_over_bl0a"] is None else
                   f"{a['bl0b']['overflow_over_bl0a']:.1f}"})
    labels = {**LABELS, "bars": {k: style.POLICIES[k].label for k in BARS}, "bl0a": style.POLICIES["bl0a"].label,
              "bl0b": style.POLICIES["bl0b"].label,
              "bl0b_ratio": None if a["bl0b"]["overflow_over_bl0a"] is None else
              f"{a['bl0b']['overflow_over_bl0a']:.1f}",
              "components": a["components"]["labels"], "margins": dict(MARGIN_LABELS),
              "accounting": "overflow accounting: cost / BL0a without the borrowers' own capacity (M2)",
              "own_capacity": "–" if a["own_capacity_usd"]["median"] is None else
              f"{a['own_capacity_usd']['median']:,.0f} USD per week",
              "caption": cap, "caption_chars": len(cap), "caption_lines_est": math.ceil(len(cap) / CAPTION_LINE_CHARS),
              "status": STATUS}
    if labels["caption_lines_est"] > CAPTION_LINES:
        raise style.StyleError(f"{NAME}: the caption draft has {len(cap)} characters, more than {CAPTION_LINES} lines "
                               f"of about {CAPTION_LINE_CHARS} (W1)")
    hyp = {"H1": {"wins": h1.get("wins"), "n_weeks": h1.get("n_weeks"), "median_margin": h1m["median"],
                  "ci": h1m["ci"], "B": h1m.get("B"), "seed": h1m.get("seed"), "pass": h1.get("pass")},
           "H2": {"weeks_below_1": h2.get("weeks_below_1"), "weeks_below_set": h2.get("weeks_below_set"),
                  "n_weeks": h2.get("n_weeks"), "median_W0": h2.get("median_W0"), "set": h2.get("set"),
                  "pass": h2.get("pass")},
           "H2b": {"weeks_below_set": h2b.get("weeks_below_set"), "n_weeks": h2b.get("n_weeks"),
                   "set": h2b.get("set"), "tau60_below_sublet_weeks": b["tau60_below_sublet_weeks"],
                   "failing_weeks": b["h2b_failing_weeks"], "pass": h2b.get("pass")},
           "H6": {"median_price": h6.get("median_price"), "n": h6.get("n"), "pass": h6.get("pass")}}
    scope = {"part": "main", "weeks": list(weeks), "seeds": [SEED], "modes": [TRACE_MODE],
             "W0_modes": "the five stress modes of W0 (main/summary.json W0.0; ms4_common.stress_modes)",
             "tags": {"a": [TAGS[k] for k in BARS], "b": ["Sublet"] + b["h1_set"] + [TAU60],
                      "c": [TAGS[k] for k in C_KEYS], "a9": [A9_TAG]}}
    data = {"a": a, "b": b, "c": c, "hypotheses": hyp, "labels": labels, "scope": scope,
            "stats": {"function": "sublet.experiments.ms5b_common.bootstrap_median_ci", "B": BOOT_B,
                      "seed": BOOT_SEED, "level": LEVEL, "over": "the weeks, policy seed 0"},
            "runs_files": [{"path": p, "sha256": v["sha256"]} for p, v in files.items()],
            "meta": {"git_revision": meta.get("git_revision"),
                     "analysis_git_revision": (ana.get("meta") or {}).get("git_revision"),
                     "analysis_sha256": (ana.get("meta") or {}).get("sha256"),
                     "reduced": bool(meta.get("reduced", False)), "weeks": list(weeks), "sources": []}}
    data["layout"] = layout(data)
    data["meta"]["sources"] = list(inp.sources)
    return data


# ---------------------------------------------------------------------------------------------------------------
# Layout
def x_hi(a: Mapping) -> float:
    """The right end of (a)'s x spine: 1 (BL0a), or the largest bar or whisker beyond it."""
    return max([1.0] + [v for k in a["order"] for v in (a[k]["median"], a[k]["ci_hi"]) if v is not None])


def column_in(fig, a: Mapping, lab: Mapping) -> dict:
    """Widths (in, at the tick size: 7 pt since C62, 9 pt as built) of what (a)'s label column holds: BL0a's label, the
    key of the components (a patch KEY_HANDLE_PT wide, KEY_TEXT_GAP_PT, the name) and BL0b's ratio with its arrow;
    `width` the widest."""
    comps = a["components"]["order"]
    key = max([(KEY_HANDLE_PT + KEY_TEXT_GAP_PT) / style.BP_PER_IN + text_width_in(fig, lab["components"][c])
               for c in comps], default=0.0)
    bl0a = text_width_in(fig, lab["bl0a"])
    bl0b = (0.0 if lab.get("bl0b_ratio") is None else
            text_width_in(fig, lab["bl0b_ratio"]) + ARROW_TEXT_PT / style.BP_PER_IN + ARROW_IN)
    return {"key": key, "bl0a_label": bl0a, "bl0b": bl0b, "width": max(key, bl0a, bl0b)}


def layout(data: Mapping) -> dict:
    """The panels' left reserves and axes widths (inches) and (a)'s x range (module docstring): (a)'s reserve the
    widest bar name (style.ytick_reserve); (b)'s and (c)'s axes and (a)'s bars' range [0, x_hi] one width, (a)'s axes
    that width plus the label column (COL_GAP_PT and the widest of BL0a's label, the components' key and BL0b's ratio
    with its arrow, measured at the tick size); a_x_max, (a)'s right x limit, puts x_hi where the column's gap
    starts."""
    a, lab = data["a"], data["labels"]
    fig = style.new_figure(NAME)
    names = [lab["bars"][k] for k in a["order"]] + [lab["bl0b"]]
    left_a = style.ytick_reserve(fig, names)
    W = float(fig.get_size_inches()[0])
    avail = W - left_a - 2 * style.LEFT_LABEL - style.MARGIN_RIGHT
    col = column_in(fig, a, lab)
    col_in = (COL_GAP_PT + COL_END_PT) / style.BP_PER_IN + col["width"]
    w = (avail - col_in) / 3.0
    if w <= 0:
        raise style.StyleError(f"{NAME}: no room for the panels beside (a)'s names and label column")
    hi = x_hi(a)
    return {"left_in": [round(left_a, 4), style.LEFT_LABEL, style.LEFT_LABEL],
            "axes_in": [round(w + col_in, 4), round(w, 4), round(w, 4)],
            "a_x_hi": hi, "a_x_max": hi * (w + col_in) / w, "a_column_in": round(col_in, 4),
            "measured": {"bar_names_in": round(left_a, 4), **{f"{k}_in": round(v, 4) for k, v in col.items()}},
            "rule": "(a): reserve = widest bar name (ytick_reserve); axes = the bars' [0, x_hi] at (b)'s width + the "
                    f"label column ({COL_GAP_PT:g} pt + the widest of BL0a's label, the components' key and BL0b's "
                    f"ratio with its arrow, at {style.TICK_PT:g} pt, + {COL_END_PT:g} pt); (b) = (c)"}


# ---------------------------------------------------------------------------------------------------------------
# (a)
def key_rows(n_bars: int, n_comps: int, label_above: bool) -> list[int]:
    """The rows of (a)'s components key in the label column: centered (the extra row below) in the rows between
    BL0a's label (row 0; none where the label is above the axes) and BL0b's row (n_bars), so that at least one empty
    row parts the key from each; StyleError where the bars leave no such room."""
    first, last = (0 if label_above else 1), n_bars - 1
    free = last - first + 1
    if n_comps and free - n_comps < 2:
        raise style.StyleError(f"{NAME} (a): {n_comps} components, BL0a's label and BL0b's row need more rows than "
                               f"the {n_bars} bars")
    start = first + math.ceil((free - n_comps) / 2)
    return list(range(start, start + n_comps))


def draw_a(ax, a: Mapping, lab: Mapping, lay: Mapping) -> None:
    """(a): the bars named on the y ticks (as fig4_e7_e3.draw_a), BL0a's line at 1 and BL0b's row; the label column
    right of x_hi: BL0a's label level with the first bar (above the line's top end where x_hi > 1), the key of the
    components in the rows of key_rows, one entry per row, and on BL0b's row its ratio at the column's start with an
    arrow to the column's end."""
    order = list(a["order"])
    comps = list(a["components"]["order"])
    shades = dict(zip(comps, style.ramp(len(comps), "greys")[::-1])) if comps else {}
    n_rows = len(order) + 1                              # the bars and BL0b's row
    hi, X = float(lay["a_x_hi"]), float(lay["a_x_max"])
    label_above = hi > 1.0 + 1e-12                       # BL0a's line inside the bars' range: its label above its top
    rows = key_rows(len(order), len(comps), label_above)
    for i, key in enumerate(order):
        e, pol = a[key], style.policy(key)
        total = e["median"]
        if total is None:                                # no runs: an empty row, its note in the extract
            ax.text(0.01, i, lab.get("no_data", "no runs"), transform=ax.get_yaxis_transform(), ha="left",
                    va="center", fontsize=style.TICK_PT, color=style.THEORY_LABEL_GREY)
            continue
        x0 = 0.0
        for comp in comps:
            wd = e["segments"].get(comp, 0.0)
            if wd > 0:
                ax.barh(i, wd, left=x0, height=BAR_H, color=shades[comp], linewidth=0, zorder=1.5)
            x0 += wd
        if not e["segments"]:                            # components null: unstacked, in the darkest grey
            ax.barh(i, total, height=BAR_H, color=style.ramp(1, "greys")[0], linewidth=0, zorder=1.5)
        outline = ax.barh(i, total, height=BAR_H, fill=False, edgecolor=pol.text_color, linewidth=BAR_EDGE_PT,
                          zorder=1.6)
        for p in outline.patches:
            p._sublet_policy = key                       # the bar's policy, for the registry checks
        if e["ci_lo"] is not None and e["ci_hi"] is not None:            # in the label color (module docstring)
            eb = style.errorbars(ax, key, [total], [i], [e["ci_lo"]], [e["ci_hi"]], orientation="x", zorder=1.7,
                                 ecolor=pol.label_color)
            for lc in eb.lines[2]:                       # the bars, in a white casing (WHISKER_CASING_PT)
                lc.set_path_effects([patheffects.Stroke(linewidth=style.UNCERTAINTY_PT + WHISKER_CASING_PT,
                                                        foreground="white"), patheffects.Normal()])
    ax.set_xlim(0.0, X)
    ax.set_ylim(n_rows - 0.5, -0.5)
    ticks = [float(v) for v in MaxNLocator(nbins=4, steps=[1, 2, 2.5, 5, 10]).tick_values(0.0, hi)
             if -1e-12 <= v <= hi + 1e-12]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_major_formatter(style.PLAIN)
    ax.spines["bottom"].set_bounds(0.0, hi)
    ax.set_xlabel(lab["a_x"])
    ax.xaxis.label.set_x(0.5 * hi / X)                   # centered under the spine (common.label_column)
    ax.set_yticks(range(n_rows), [lab["bars"][k] for k in order] + [lab["bl0b"]])
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    # C62: the names with mathtext ("RetroRenting, $\tau\geq1$ h", "SpotHedge-style, $N_{\mathrm{Extra}}=0$") on the
    # rows' pitch as printed (0.46 pt off it, and off the key's names on their rows, as built), after the last
    # tick_params, as fig4_v3 sets its names (common.align_baselines)
    align_baselines([tk.label1 for tk in ax.yaxis.get_major_ticks()])

    fig = ax.figure
    r = fig.canvas.get_renderer()
    per_pt = X / (style.axes_rect_in(ax)[2] * style.BP_PER_IN)       # data units per pt along x
    x_col = hi + COL_GAP_PT * per_pt                     # the label column's left edge
    if label_above:                                      # above the line's top end, in the panel letters' band
        t = ax.annotate(lab["bl0a"], xy=(1.0, 1.0), xycoords=("data", "axes fraction"),
                        xytext=(0.0, BL0A_LABEL_RISE_PT), textcoords="offset points", ha="center", va="bottom",
                        fontsize=style.TICK_PT, color=style.policy("bl0a").label_color, zorder=style.Z_THEORY_LABEL)
    else:                                                # beside the line's top end, level with the first bar; C62:
        #                                                  on its name's baseline (the y tick labels' center_baseline)
        t = ax.text(x_col, 0, lab["bl0a"], ha="left", va="center_baseline", fontsize=style.TICK_PT,
                    color=style.policy("bl0a").label_color, zorder=style.Z_THEORY_LABEL)
    t._sublet_role = "direct_label"
    for j, comp in zip(rows, comps):                     # the key: a patch at the bars' height and the name, a row each
        ax.barh(j, KEY_HANDLE_PT * per_pt, left=x_col, height=BAR_H, color=shades[comp], linewidth=0, zorder=1.5)
        k = ax.text(x_col + (KEY_HANDLE_PT + KEY_TEXT_GAP_PT) * per_pt, j, a["components"]["labels"][comp],
                    ha="left", va="center_baseline", fontsize=style.TICK_PT)      # C62: on its row's name's baseline
        k._sublet_role = "key"

    # BL0b: its own row; off the axis, its ratio at the start of the label column (right at the end of the x spine)
    # and an arrow from it to the column's right end
    row = len(order)
    ratio = None
    if a["bl0b"].get("overflow_over_bl0a") is None:
        ax.text(0.01, row, lab.get("no_data", "no runs"), transform=ax.get_yaxis_transform(), ha="left",
                va="center", fontsize=style.TICK_PT, color=style.THEORY_LABEL_GREY)
    else:
        head = X - COL_END_PT * per_pt                   # the column's right end
        pol = style.policy("bl0b")
        ratio = style.direct_label(ax, "bl0b", x_col, row, lab["bl0b_ratio"], dx=0.0, ha="left",
                                   va="center_baseline")                 # C62: on "Provision for peak"'s baseline
        ratio._sublet_role = "direct_label"
        tail_px = ratio.get_window_extent(r).x1 + ARROW_TEXT_PT * fig.dpi / 72.0
        tail = float(ax.transData.inverted().transform((tail_px, 0.0))[0])
        if (head - tail) / per_pt < ARROW_IN * style.BP_PER_IN - 0.5:
            raise style.StyleError(f"{NAME} (a): BL0b's arrow is shorter than {ARROW_IN} in")
        arr = style.arrow(ax, (tail, row), (head, row), color=pol.color, linewidth=style.REFERENCE_POLICY_PT,
                          shrinkA=0.0, shrinkB=0.0)
        arr._sublet_role = "off_scale_arrow"
        arr._sublet_policy = "bl0b"

    # BL0a: a line at 1 across the bars, above them in a white casing; it ends half a row below the last bar, or
    # BL0A_CLEAR_PT above BL0b's ratio where the ratio lies under it (fig4_e7_e3.draw_a)
    to_pt = 72.0 / fig.dpi
    y_end = len(order) - 0.5
    if ratio is not None:
        bb = ratio.get_window_extent(r)
        x1_px = ax.transData.transform((1.0, row))[0]
        if bb.x0 - BL0A_CLEAR_PT / to_pt < x1_px < bb.x1 + BL0A_CLEAR_PT / to_pt:
            y_clear = ax.transData.inverted().transform((x1_px, bb.y1 + BL0A_CLEAR_PT / to_pt))[1]
            if y_clear < len(order) - 1 + 0.5 * BAR_H:
                raise style.StyleError(f"{NAME} (a): BL0b's ratio {lab['bl0b_ratio']!r} leaves no room under the "
                                       "last bar for BL0a's line")
            y_end = min(y_end, float(y_clear))
    kw = style.policy_kwargs("bl0a", markers=False)
    kw["zorder"] = Z_BL0A
    (line,) = ax.plot([1.0, 1.0], [y_end, -0.5], **kw)
    line.set_path_effects([patheffects.Stroke(linewidth=kw["linewidth"] + BL0A_CASING_PT, foreground="white"),
                           patheffects.Normal()])
    line._sublet_policy = "bl0a"


# ---------------------------------------------------------------------------------------------------------------
# (b)
def margin_kwargs(k: str) -> dict:
    """Line2D keyword arguments of a margin series of (b): black markers, no line (MARGIN_STYLES)."""
    kw = dict(color=MARGIN_COLOR, linestyle="none", markersize=style.MARKER_PT, markeredgewidth=style.MARKER_EDGE_PT,
              markeredgecolor=MARGIN_COLOR, zorder=style.Z_DATA)
    kw.update(MARGIN_STYLES[k])
    return kw


def margin_handles(lab: Mapping) -> list:
    return [(Line2D([], [], **margin_kwargs(k)), lab["margins"][k]) for k in MARGINS]


def week_tick_labels(ax, xs: Sequence[float]) -> list[float]:
    """Label the weeks at a regular stride from the first to the last: the smallest divisor k of (n - 1) at which
    labels k weeks apart clear each other by common.TICK_GAP_PT (k = n - 1, the two ends, at the most); the other
    weeks keep unlabeled ticks at minor length (common._label_only). Returns the labeled weeks."""
    xs = sorted(float(v) for v in xs)
    ax.xaxis.set_major_locator(FixedLocator(xs))
    n = len(xs)
    if n <= 2:
        return xs
    fig = ax.figure
    px = [ax.transData.transform((v, 0.0))[0] / fig.dpi for v in xs]
    half = [0.5 * text_width_in(fig, style.PLAIN(v)) for v in xs]
    gap = TICK_GAP_PT / style.BP_PER_IN
    idx = [0, n - 1]
    for k in (d for d in range(1, n) if (n - 1) % d == 0):
        cand = list(range(0, n, k))
        if all(px[j] - half[j] - (px[i] + half[i]) >= gap for i, j in zip(cand, cand[1:])):
            idx = cand
            break
    keep = [xs[i] for i in idx]
    if len(keep) < n:
        _label_only(ax, keep)
    return keep


def marker_outline_pt(marker: str, size_pt: float, edge_pt: float) -> np.ndarray:
    """A marker's outline (n x 2, pt, about its center, counterclockwise) at markersize size_pt with its edge: the
    marker's convex path scaled to size_pt + edge_pt (the edge's outer side, up to the miter at its corners)."""
    ms = MarkerStyle(marker)
    v = np.unique(np.round(ms.get_path().transformed(ms.get_transform()).vertices, 9), axis=0)
    v = v[np.argsort(np.arctan2(v[:, 1] - v[:, 1].mean(), v[:, 0] - v[:, 0].mean()))]
    return v * (size_pt + edge_pt)


def _area(p: np.ndarray) -> float:
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _clip(subject: np.ndarray, clipper: np.ndarray) -> np.ndarray | None:
    """The intersection of two convex polygons (Sutherland-Hodgman; the clipper counterclockwise), None if empty."""
    def side(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])

    out = [np.asarray(p, dtype=float) for p in subject]
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        pts, out = out, []
        for j, e in enumerate(pts):
            s = pts[j - 1]
            fe, fs = side(e, a, b), side(s, a, b)
            if fe >= 0:
                if fs < 0:
                    out.append(s + (e - s) * (fs / (fs - fe)))
                out.append(e)
            elif fs >= 0:
                out.append(s + (e - s) * (fs / (fs - fe)))
        if len(out) < 3:
            return None
    return np.array(out)


def marker_overlaps(ax) -> list[dict]:
    """Every pair of (b)'s margin markers whose outlines (marker_outline_pt) overlap, with the overlap's share of the
    smaller marker's area, largest first."""
    to_pt = 72.0 / ax.figure.dpi
    marks = []
    for ln in ax.lines:
        role = getattr(ln, "_sublet_role", "")
        if not role.startswith("margin:"):
            continue
        poly = marker_outline_pt(ln.get_marker(), ln.get_markersize(), ln.get_markeredgewidth())
        xy = ln.get_transform().transform(np.asarray(ln.get_xydata(), dtype=float)) * to_pt
        for (px, py), (dx, _) in zip(xy, ln.get_xydata()):
            marks.append((role[7:], float(dx), poly + [px, py]))
    out = []
    for i in range(len(marks)):
        for j in range(i + 1, len(marks)):
            (ki, xi, pi), (kj, xj, pj) = marks[i], marks[j]
            if np.abs(pi.mean(axis=0) - pj.mean(axis=0)).max() > np.ptp(pi, axis=0).max() + np.ptp(pj, axis=0).max():
                continue
            q = _clip(pi, pj)
            if q is not None:
                share = _area(q) / min(_area(pi), _area(pj))
                if share > 1e-9:
                    out.append({"a": [ki, round(xi, 6)], "b": [kj, round(xj, 6)], "share": share})
    return sorted(out, key=lambda o: -o["share"])


def _column_low_pt(ax, b: Mapping, n: Mapping, dodge: Mapping) -> float:
    """The lowest point (pt) of the markers drawn in a flagged week's column (each marker's bottom, its edge included);
    for a week with no marker, the bottom of a marker at the lowest point drawn (n['y'])."""
    to_pt = 72.0 / ax.figure.dpi
    i = list(b["x"]).index(n["x"])
    lows = []
    for k in MARGINS:
        v = b[k][i]
        if v is not None and math.isfinite(float(v)):
            kw = margin_kwargs(k)
            half = 0.5 * np.ptp(marker_outline_pt(kw["marker"], kw["markersize"], kw["markeredgewidth"])[:, 1])
            lows.append(ax.transData.transform((n["x"] + dodge[k], float(v)))[1] * to_pt - half)
    if not lows:
        y_pt = ax.transData.transform((n["x"], n["y"]))[1] * to_pt
        lows.append(y_pt - 0.5 * (style.MARKER_PT + style.MARKER_EDGE_PT))
    return min(lows)


def _column_label(ax, n: Mapping, top_pt: float):
    """The label of a flagged week on its column: its top at the highest spot at or below top_pt where its box is clear
    of everything drawn (common's occupancy grid, which keeps KEY_PAD_PT from it), centered on the week, or, where that
    is not clear, shifted by the least amount that is, its center staying within the column (the week +- 0.5); None
    if no such spot is clear."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    to_pt = 72.0 / fig.dpi
    t = ax.text(n["x"], 0.0, n["week"], ha="center", va="top", fontsize=style.TICK_PT, zorder=style.Z_THEORY_LABEL)
    bb = t.get_window_extent(r)
    w, h = bb.width * to_pt, bb.height * to_pt
    xc, y_anchor = ax.transData.transform((n["x"], 0.0)) * to_pt
    rise = bb.y1 * to_pt - y_anchor                     # from the anchor to the box's top
    half_col = 0.5 * abs(ax.transData.transform((1.0, 0.0))[0] - ax.transData.transform((0.0, 0.0))[0]) * to_pt
    taken, gx0, gy0 = _occupancy(ax, skip=(t,))
    res = GRID_RES_PT
    steps = int(math.floor(half_col / res))
    shifts = [0.0] + [s * k * res for k in range(1, steps + 1) for s in (1.0, -1.0)]
    top = top_pt
    while top - h >= gy0:
        j0, j1 = int(math.floor((top - h - gy0) / res)), int(math.ceil((top - gy0) / res))
        for dx in shifts:
            i0 = int(math.floor((xc + dx - 0.5 * w - gx0) / res))
            i1 = int(math.ceil((xc + dx + 0.5 * w - gx0) / res))
            if i0 < 0 or i1 > taken.shape[1] or j1 > taken.shape[0] or taken[j0:j1, i0:i1].any():
                continue
            x, y = ax.transData.inverted().transform(((xc + dx) / to_pt, (top - rise) / to_pt))
            t.set_position((float(x), float(y)))
            t.set_path_effects([patheffects.withStroke(linewidth=style.LABEL_HALO_PT, foreground="white")])
            t._sublet_role = "week_label"
            return t
        top -= res
    t.remove()
    return None


def draw_b(ax, b: Mapping, lab: Mapping) -> None:
    x = finite(b["x"])
    dodge = {**DODGE, **(b.get("dodge_weeks") or {})}
    vals = [0.0]
    for k in MARGINS:
        y = finite(b[k])
        ok = np.isfinite(y)
        if ok.any():
            (ln,) = ax.plot(x[ok] + dodge[k], y[ok], label="_nolegend_", **margin_kwargs(k))
            ln._sublet_role = f"margin:{k}"
        vals += list(y[ok])
    style.reference_line(ax, y=0.0)
    lo, hi = min(vals), max(vals)
    pad = B_PAD * (hi - lo) if hi > lo else 0.05
    x0, x1 = (float(np.nanmin(x)), float(np.nanmax(x))) if x.size else (0.0, 1.0)
    ax.set_xlim(x0 - 0.7, x1 + 0.7)
    ax.xaxis.set_major_formatter(style.PLAIN)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, steps=[1, 2, 5, 10]))
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.set_xlabel(lab["b_x"])
    ax.set_ylabel(lab["b_y"])
    week_tick_labels(ax, list(x))
    lost = list(b.get("missing_weeks") or [])
    neg_weeks = {n["week"] for n in b["negative"]}
    flagged = list(b["negative"]) + [{**m, "y": lo} for m in lost if m["week"] not in neg_weeks]
    h_pt = style.axes_rect_in(ax)[3] * style.BP_PER_IN
    labels = None
    extras = np.arange(0.0, len(flagged) * LINE_STEP_PT + 0.5 * ROOM_STEP_PT, ROOM_STEP_PT)
    for extra in extras:                               # room below the lowest point for the weeks' labels
        span = hi - lo + 2 * pad
        if flagged:
            span /= 1.0 - (WEEK_LABEL_ROOM_PT + extra) / h_pt
        ax.set_ylim(hi + pad - span, hi + pad)
        # each label centered on its column, at the highest free spot below the column's lowest marker, the columns
        # with the highest such spot first (so that a neighbor's label stacks below)
        tops = {n["week"]: _column_low_pt(ax, b, n, dodge) - WEEK_LABEL_GAP_PT for n in flagged}
        labels = []
        for n in sorted(flagged, key=lambda n: (-tops[n["week"]], n["x"])):
            t = _column_label(ax, n, tops[n["week"]])
            if t is None:
                break
            labels.append(t)
        if len(labels) == len(flagged):
            break
        for t in labels:
            t.remove()
        labels = None
    if labels is None:
        raise style.StyleError(f"{NAME} (b): the weeks' labels do not fit below their columns")
    y0, y1 = ax.get_ylim()
    for n in flagged:                                     # marked: a shaded column; labeled: the week's number
        style.shade_region(ax, (n["x"] - 0.5, n["x"] + 0.5), (y0, y1))
    worst = marker_overlaps(ax)
    if worst and worst[0]["share"] > MAX_MARKER_OVERLAP:
        raise style.StyleError(f"{NAME} (b): markers overlap by more than {MAX_MARKER_OVERLAP:.2f} of a marker: "
                               f"{worst[:3]}")


# ---------------------------------------------------------------------------------------------------------------
# (c)
def draw_c(ax, c: Mapping, lab: Mapping) -> None:
    xs, ys = [], [1.0]
    for key in c["order"]:
        e = c[key]
        mx, my = e["r0"]["median"], e["W0"]["median"]
        if mx is None or my is None:
            continue
        (xl, xh), (yl, yh) = e["r0"]["ci"], e["W0"]["ci"]
        ecolor = style.policy(key).label_color          # module docstring: apart from the grey line in greyscale
        if xl is not None and xh is not None:
            style.errorbars(ax, key, [mx], [my], [xl], [xh], orientation="x", ecolor=ecolor)
            xs += [xl, xh]
        if yl is not None and yh is not None:
            style.errorbars(ax, key, [mx], [my], [yl], [yh], ecolor=ecolor)
            ys += [yl, yh]
        style.scatter_policy(ax, key, [mx], [my])
        xs.append(mx)
        ys.append(my)
    style.reference_line(ax, y=1.0)
    for vals, setter, pad in ((xs, ax.set_xlim, C_PAD), (ys, ax.set_ylim, B_PAD)):
        lo, hi = min(vals), max(vals)
        p = pad * (hi - lo) if hi > lo else 0.05
        setter(lo - p, hi + p)
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_locator(MaxNLocator(nbins=4, steps=[1, 2, 2.5, 5, 10]))
        axis.set_major_formatter(style.PLAIN)
    ax.set_xlabel(lab["c_x"])
    ax.set_ylabel(lab["c_y"])


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    lay = data["layout"]
    fig = style.new_figure(NAME)
    ax_a, ax_b, ax_c = style.panel_row(fig, lay["axes_in"], legend=2, left=lay["left_in"])
    leg = style.legend_row(fig, list(data["c"]["order"]), extra=margin_handles(lab), lines=False, rows=2)
    align_printed_rows(fig, leg.get_texts())          # C62: "$W_0$ vs. $\tau\geq1$ h" sat 0.9 pt above its row
    draw_a(ax_a, data["a"], lab, lay)
    draw_b(ax_b, data["b"], lab)
    draw_c(ax_c, data["c"], lab)
    style.panel_letters([ax_a, ax_b, ax_c])
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
