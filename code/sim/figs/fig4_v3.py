"""Fig. 3 v3 (figure name fig4v3; the paper's Fig. 3 since cut K1): end-to-end cost on the confirmation weeks with the
causal runs and the decomposition (design/ms7/w_spec.md §2.8, "Fig. 4 v3", and §4, unit W-G2; change C58).

Claims: none of its own. Every number is read from versioned result files: the confirmation (code/sim/out/sublet_v2/:
main/summary.json, analysis.json), Fig. 4 v2's extract code/sim/out/figs/fig4v2.json (the source of (a): its bars were
built from the unversioned run files of part main, which fig4v2.json lists with their sha256), and two analyses of the
MS7 runs registered in design/ms7/registration.md: X1's code/sim/out/e7c/analysis.json (the lagged margin) and X4's
code/sim/out/e7r/analysis.json (protected-only critical-ratio renting). The statistics are descriptive: per-week values
and medians over the weeks (the weeks are rotations of one series; design/ms7/plan.md D4); no p-value.

(a) Fig. 4 v2's (a) (fig4v2.json's bars, segments, BL0a's line at 1 and BL0b's row with its ratio; drawn by draw_a
    here on fig4_v2's helpers): per policy of fig4_v2.BARS, the median over the weeks of the trace cost r0 (overflow
    cost over the all-fallback bill under the trace lender, policy seed 0) as a bar split into the ledger components;
    the bars named on the y ticks by their registry labels and the components keyed in the label column. Changed from
    fig4_v2: the segments' fills are COMPONENT_FILLS, lease light grey, routing white with
    a dense dark hatch, fallback mid grey, stranding near black, in the key too (C19: fig4_v2's four greys were hard to
    tell apart); the whisker is the range over the weeks, min to max of the policy's per-week r0 of main/summary.json
    (bar.range: min, max, n; C10), not fig4v2's week-bootstrap interval (its ci_lo and ci_hi are dropped from the
    extract). Added: each bar's name is followed by its policy's registry marker, between the name and the bar
    (A_MARKERS), so that (a)'s names key the same policies in (c) (review of W-G2: a marker at the bar's end hid the
    whisker). Each bar's median is checked against the median of main/summary.json's r0 of its tag (StyleError where it
    differs: a stale fig4v2.json). A hatched segment narrower than HAIRLINE_PT shows no hatch, only a white hairline
    (routing, at most 0.0153 of the bill on the confirmation, about 0.7 pt): the caption draft says so, with the
    component's largest segment (layout's a_thin; review of W-G2). BL0b's row, beyond the axis, has a light bar to the
    spine's end with a break mark (offscale_bar), then its ratio and arrow (fig4_v2's off-scale convention).
(b) Per week, four margins, each positive when Sublet costs less (the confirmation's convention, ms5b_common.
    paired_margins), in two sub-panels on one week axis, each with its own y range (B_SUBPANELS; as built: on one axis
    the cost margins, about 0.05, sat in a narrow band under the W0 margins, about 0.3, and with four series per week
    in 1.1 in neighbouring markers overlapped by up to 0.41 of a marker on the prototype). Top, "Cost": "trace", the
    least r0 over the primary baselines (H1's set) minus Sublet's (analysis.json H1.margins, the revealed slot;
    fig4_v2.margin_series with its checks), and "trace_lag", the same with every policy on the previous slot's demand
    (e7c analysis margins.h1.r0: the least lagged primary baseline minus Sublet-lag; the guard's test reads the
    realized slot; its count of positive weeks checked against the analysis's n_wins). Bottom, "W0": "w0_set", the least
    W0 of H1's set minus Sublet's (H2), and "w0_tau60", RetroRenting, tau >= 1 h's W0 minus Sublet's. Black markers of
    MARGIN_STYLES (one series of each sub-panel open, none the (marker, fill) of a key that (a) or (c) draws), the two
    series of a sub-panel B_DODGE weeks left and right of the week; no two markers of a sub-panel overlap by more than
    fig4_v2.MAX_MARKER_OVERLAP (StyleError); each sub-panel's y range keeps its markers MARKER_CLEAR_PT inside its
    frame (_sub_ylim). A week with a negative margin is shaded in each sub-panel that holds one
    of its negative margins (b['shaded'], per sub-panel: the W0 sub-panel's shading marks the weeks with a negative W0
    margin, the cost sub-panel's those with a negative cost margin, so that a lagged loss does not shade a W0 column;
    review of W-G2) and labeled once, below its column in the first sub-panel with a negative margin (fig4_v2's
    placement); a week without a margin (a missing run: a loss for Sublet) is shaded in the sub-panel of the missing
    series, labeled too, and named in the extract's notes. The two y labels are aligned (align_ylabels_x) on one
    baseline (align_baselines).
(c) The median r0 (x) against the median W0 (y) over the weeks of: Sublet; critical-ratio planning and the ablations
    of critical-ratio renting (k*, no make-before-break, no commitment rule, no site marking), named in a column left
    of the data with thin leaders (their registry labels without the prefix "Critical-ratio renting, ", which the
    caption carries, as sf_e7_decomp names them; NAMED; names whose points lie within COINCIDE_PT share one name, one
    leader and one marker, the first's, as no commitment rule and no site marking on the confirmation); Sublet, named
    beside its point (label_sublet); protected-only critical-ratio renting (e7r's A9-P), keyed in (c)'s key; the
    baselines of (a), keyed by the markers after (a)'s names; and the notice layer added to greedy and
    RetroRenting-style renting, as arrows in a tint of the base's color from the baseline to its transplant, whose point
    a small copy of the base's marker marks (ARROWS, transplant_arrow). A grey line at W0 = 1 (the all-fallback
    level). The y axis is on the right, so that the names sit next to the points at the low-cost end.
Keys (C19: each panel its own; no shared legend row): (b) and (c) each start with a key whose first row is level with
the panel's letter, right of it: (b)'s the two margins of its upper sub-panel, (c)'s protected-only renting; (b)'s lower
sub-panel has the key of its two margins above it, at the same x, set on its bottom. As the PDF prints them, the ink
(glyphs and markers) of (b)'s lower key, and of the deeper of the other two keys, ends KEY_AXES_GAP_PT above the axes
it keys ((b)'s upper sub-panel and (c) start at one height), and the ink of (b)'s lower key lies
B_TICK_ROOM_PT below the upper sub-panel's frame (its tick marks take 3 pt of that), so that it sits nearer to its own
sub-panel than to the upper one (8 pt against 3 pt of ink; tests/test_figs_ms7_fig4.py measures it in the PDF). No key
covers an axes (check_keys, StyleError); a sub-panel's top y tick label that would reach its key is left out
(clear_top_tick_label). (a)'s key is its label column.

Layout (layout(), stored in the extract; draw() places the panels from it, so a redraw is exact): (a)'s left reserve is
the widest bar name at TICK_PT (style.ytick_reserve) plus the key markers' column (the widest marker of BARS and
A_KEY_GAP_PT on each side; a_key), and its label column fig4_v2.column_in's; (b) has the standard left reserve; (c)
has the names column on its left (a gutter of NAME_LEFT_GAP_PT after (b)'s axes, where (c)'s slot starts, the widest
name line at TICK_PT and the leader run) and its y axis in a right reserve of style.LEFT_LABEL; the rest of the width
goes to the three axes in AXES_RATIOS, (b) at least as wide as its keys need right of its letter. Heights (the legend
row's 0.48 in given back to the panels): (a) runs from the bottom margin to the letters' line, style.MARGIN_TOP
below the top (lower by the room of BL0a's label where that sits above the axes); (b)'s upper sub-panel and (c) start
below their keys, (b)'s lower sub-panel below its key; the keys' corners, widths and heights, and the empty room of
each key's box below and above its ink, are measured at TICK_PT as the PDF sets them (key_size_in, in_pdf; as built at
9 pt, the canvas's Agg at 100 dpi set (b)'s lower key, then two mathtext rows, 3.7 pt higher) and stored (layout's
keys).

C62 (2026-11-24: no text larger than the caption; the figures high-end, informative and readable). The text
follows style's C62 scale (axis labels and letters at CAPTION_PT, the rest at TICK_PT), and the room the smaller text
frees goes to the data: each of (b)'s keys is one row (make_key; MARGIN_LABELS name the series after the sub-panels' y
labels "Cost margin" and "$W_0$ margin": "vs. best", "lagged", "vs. $\\tau\\geq1$ h"), so that its sub-panels gain
0.12 in of height each; (a)'s bars about 1 in wide (AXES_RATIOS) with x ticks at 0, 0.5 and 1 and light grid lines at
A_GRID_STEP behind the bars, A_BAR_H rows high; (c)'s names wrap at NAME_MAX_IN, the names of one shared name each on
lines of their own (group_lines). Added: Sublet's name beside its point in (c) (label_sublet), the arrows of (c)
under the markers, BL0b's arrow fig4_v2.ARROW_IN long (it ran to the label column's end, 6 pt from (b)'s y label),
and (b)'s week labels without a white halo (placed clear of everything drawn, the halo cut a notch in the column's
shade). After the review of C62's first render: (b) narrower (AXES_RATIOS) and a gutter of NAME_LEFT_GAP_PT before
(c)'s names and letter; in (c) one marker for coinciding points, a small copy of the base's marker at each transplant's
point and the arrows thinner in a tint; in (a) BL0b's off-scale bar, minor ticks under the grid lines and the
components' names and BL0b's ratio on the bar names' alignment; the texts with mathtext on their plain neighbors'
baselines as printed (align_baselines: the keys' labels, (a)'s names, (b)'s y labels). No plotted number changes.

Run files: none (C40: fig4v2.json carries (a)'s run-file data with their sha256). The extract code/sim/out/figs/
fig4v3.json carries every plotted number, the caption draft (labels.caption, at most CAPTION_LINES lines of about
CAPTION_LINE_CHARS characters, every number read from the inputs) and the scope (weeks, modes, tags of each panel).
Inputs are read through figs.inputs (SUBLET_FIGS_IN_ROOT redirects them to a fixture tree); a missing input stops the
build with exit code 2 and the file named (RUN_INPUTS: the MS7 run outputs, which exist only once the runs are copied
in; figs/rebuild.py lists the figure as pending until then). Data from a reduced (smoke) run is never written into
paper/figures/ or code/sim/out/figs/ (it stops unless SUBLET_FIGS_PDF_DIR and SUBLET_FIGS_OUT_DIR are both set). Run
from code/sim: python -m figs.fig4_v3 [--from-extract [JSON]] (figs.common.cli).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import sys
from typing import Any, Mapping, Sequence

import matplotlib as mpl
import numpy as np
from matplotlib import patheffects
from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
from matplotlib.ticker import FixedLocator, MaxNLocator
from matplotlib.transforms import offset_copy

from figs import fig4_v2 as v2
from figs import style
from figs.common import (GRID_RES_PT, LEADER_PT, LINE_STEP_PT, MissingKey, _occupancy, align_baselines,
                         align_ylabels_x, cli, finite, free_spot, in_pdf, letter_box, need, stack_labels, text_ink,
                         text_width_in, thin_tick_labels)
from figs.inputs import Inputs
from sublet.experiments.ms5b_common import TRACE_MODE, stress_modes

NAME = "fig4v3"
CONF = "code/sim/out/sublet_v2"
MAIN = f"{CONF}/main/summary.json"
ANALYSIS = f"{CONF}/analysis.json"
FIG4V2 = "code/sim/out/figs/fig4v2.json"
E7C = "code/sim/out/e7c/analysis.json"
E7R = "code/sim/out/e7r/analysis.json"
RUN_INPUTS = (E7C, E7R)          # the MS7 run outputs this figure needs (figs/rebuild.py's MS7_PENDING)
INPUTS = (MAIN, ANALYSIS, FIG4V2) + RUN_INPUTS
KEYS = style.FIGURE_POLICIES[NAME]
SEED = 0
BARS = v2.BARS
# (c): registry key -> tag of the confirmation (ms5b_common.TAGS) or of e7r (ms7_baselines.MS7_TAGS)
C_MAIN = {"sublet_v2": "Sublet", "cr": "CR", "a9_kstar": "A9-kstar", "a9_nombb": "A9-noMBB",
          "a9_nocommit": "A9-noCommit", "a9_static": "A9-static", "bl1": "BL1", "bl1_bo": "BL1-BO", "bl5_cur": "BL5-cur",
          "bl5_tau60": "BL5-tau60", "bl2": "BL2", "bl3_0": "BL3-0", "bl4": "BL4", "bl1n": "BL1N", "bl5n": "BL5N"}
C_E7R = {"a9p": "A9-P"}
ARROWS = (("bl1", "bl1n"), ("bl5_cur", "bl5n"))          # (c): base -> base + notice layer (no marker at the head)
NAMED = ("cr", "a9_kstar", "a9_nombb", "a9_nocommit", "a9_static")      # (c): named in the column left of the data
LEGEND_KEYS = ("a9p",)                                    # (c): keyed in (c)'s key
C_ORDER = ("bl4", "bl3_0", "bl2", "bl5_tau60", "bl1", "bl1_bo", "bl5_cur", "a9p", "cr", "a9_kstar", "a9_static",
           "a9_nocommit", "a9_nombb", "sublet_v2")                         # (c): drawing order, Sublet last
NAME_PREFIX = style.POLICIES["a9"].label + ", "          # dropped from the ablations' names (the caption carries it)
MARGINS = ("trace", "trace_lag", "w0_set", "w0_tau60")
# C62: each sub-panel's key is one row beside its letter or above its sub-panel, its entries named after the sub-panel's
# y label ("Cost margin", "$W_0$ margin"): the margin against the least primary baseline ("vs. best"), the same with
# every policy on the previous slot's demand ("lagged"), and against RetroRenting, tau >= 1 h (as built at 9 pt, two
# rows each, "Cost vs. best", "Cost vs. best, lagged", "$W_0$ vs. best", "$W_0$ vs. $\tau\geq1$ h", took 0.25 in of
# (b)'s height from its sub-panels)
MARGIN_LABELS = {"trace": "vs. best", "trace_lag": "lagged", "w0_set": "vs. best", "w0_tau60": r"vs. $\tau\geq1$ h"}
MARGIN_STYLES = {   # black: no policy. Cost: filled and open diamonds; W0: a filled hexagon and an open circle; none is
    "trace": dict(marker="D", markerfacecolor="#000000", markersize=3.2),   # the (marker, fill) of a key that (a) or
    "trace_lag": dict(marker="D", markerfacecolor="white", markersize=3.2),  # (c) draws (greyscale), and within each
    "w0_set": dict(marker="h", markerfacecolor="#000000"),                   # sub-panel one series is open, so that two
    "w0_tau60": dict(marker="o", markerfacecolor="white", markersize=3.2),   # touching markers do not merge
}
MARGIN_COLOR = "#000000"
# (b) in two sub-panels on one week axis, each with its own y range: the cost margins on top, the W0 margins below
# (as built: on one axis the cost margins, about 0.05, sat in a band near 0 under W0's, about 0.3, and with four series
# per week in 1.1 in the markers of neighbouring series overlapped by up to 0.41 of a marker on the prototype)
B_SUBPANELS = (("cost", ("trace", "trace_lag")), ("w0", ("w0_set", "w0_tau60")))
B_DODGE = 0.25                    # (b): within a sub-panel the first series this many weeks left of the week, the second
#                                   as far right (fig4_v2's B_DODGE)
MAX_MARKER_OVERLAP = v2.MAX_MARKER_OVERLAP
# (a): the components' fills, distinct in greyscale (C19: the four greys of fig4_v2's ramp
# were hard to tell apart and routing, a sliver, read as lease); lightest to darkest along a bar, routing (and loading,
# zero on the confirmation) white with a dense dark hatch, so that each pair of neighboring segments differs in
# lightness or texture. The key in (a)'s label column draws the same fills.
COMPONENT_FILLS = {"lease": {"facecolor": "#D9D9D9", "hatch": None},
                   "loading": {"facecolor": "#FFFFFF", "hatch": "xxxx"},
                   "routing": {"facecolor": "#FFFFFF", "hatch": "//////"},
                   "fallback": {"facecolor": "#808080", "hatch": None},
                   "stranding": {"facecolor": "#1A1A1A", "hatch": None}}
HATCH_COLOR = "#1A1A1A"           # (a): the hatch lines (style's hatch.linewidth, 0.4 pt)
A_MARKERS = True                  # (a): each bar's name keyed by its policy's marker (the key of (c)'s baselines)
A_KEY_GAP_PT = 2.0                # (a): the key marker this far from the bar's left end and from its name
A_X_NBINS = 3                     # (a): x ticks 0, 0.5, 1 (C62: the bars about 1 in wide; 0 and 1 alone at 9 pt)
A_GRID_STEP = 0.25                # (a): light vertical grid lines at this step behind the bars (C62; BL0a's line at 1)
OFFSCALE_FILL = "#EFEFEF"         # (a): BL0b's bar beyond the axis (offscale_bar), lighter than every component's fill
OFFSCALE_BREAK_AT = 0.8           # (a): its break mark this share of the way to the spine's end
BREAK_GAP_PT = 1.6                # (a): the break's white gap, across
BREAK_SLANT_PT = 2.4              # (a): its edges' run across over their height
BREAK_OVER_PT = 1.2               # (a): its edges beyond the bar's top and bottom
BREAK_PT = 0.6                    # (a): its edges' width
A_BAR_H = 0.56                    # (a): a bar's height in rows (fig4_v2's BAR_H 0.62 at 9 pt; C62: lighter beside 7-pt
#                                   names, 8.2 pt in a row of 14.6 pt)
AXES_RATIOS = (1.0, 1.2, 1.08)    # (a)'s bars, (b), (c): shares of the width left after the reserves (C62: about 1.0,
#                                   1.2 and 1.1 in; (0.85, 1.25, 1.0), as built at 9 pt, gave 0.66, 1.14 and 0.77 in;
#                                   1.3 for (b), C62's first render, left no gutter before (c)'s names: 16 weeks need
#                                   less)
NAME_MAX_IN = 0.67                # (c): a name wraps at word (or hyphen) breaks to at most this width (TICK_PT; 0.86 at
#                                   9 pt): two lines at most, "no make-" / "before-break" broken at its hyphen
NAME_GAP_PT = 2.0                 # (c): the names' right end this far left of the leader's start
LEADER_RUN_PT = 7.0               # (c): leader from the names' column to the data area's left edge, at least
NAME_LEFT_GAP_PT = 12.0           # (c): the gutter from (b)'s data area to (c)'s slot, where (c)'s letter and its
#                                   widest name start (C62 review: at 6 pt from (b)'s axes, 4 pt from its "316", the
#                                   shared name read as a label of (b)'s last week; (a)'s label column ends about 12 pt
#                                   left of (b)'s slot, so the two gutters match)
COINCIDE_PT = 2.0                 # (c): names whose points lie within this distance share one name and one leader
NAME_JOIN = "; "                  # (c): between the names of one shared name (a list of policies, not one policy)
LEADER_END_PT = 1.2               # (c): a leader ends this far from its marker's edge
C_PAD = 0.07                      # (c): the x range this share beyond the data
SUBLET_GAP_PT = 1.5               # (c): Sublet's name this far off its marker's edge (label_sublet; C62)
SUBLET_DY_PT = 0.5                # (c): ... centered on its point across its side, or moved in these steps
SUBLET_DY_MAX_PT = 6.0            # (c): ... by at most this across its side (and away by at most SUBLET_DX_MAX_PT),
SUBLET_DX_MAX_PT = 4.0            #     the nearest place clear of everything drawn (common's occupancy grid) first
SUBLET_SIDES = ("right", "left", "above", "below")      # (c): the sides of Sublet's point tried for its name, in order
SUBLET_OWN_PT = 2.0               # (c): its name's facing edge this much nearer to Sublet's point than to any other
C_Y_PAD = 0.08                    # (c): the y range this share beyond the data
GHOST_PT = 2.4                    # (c): the small copy of the base's marker at a transplant's point (transplant_arrow)
GHOST_EDGE_PT = 0.5               # (c): its edge
GHOST_GAP_PT = 0.4                # (c): an arrow's head ends this far from its edge
ARROW_PT = 0.5                    # (c): the arrows' shafts (C62 review: lighter, so that the markers they pass read)
ARROW_TINT = 0.6                  # (c): ... in the base's color mixed with white, this share of the color
ARROW_STYLE = "-|>,head_length=0.36,head_width=0.18"   # (c): the arrows' heads, 0.8 of style.arrow's (final
#                                   render: the two heads, BL1N's and BL5N's, 2 to 4 pt apart, overlapped)
C_EDGE_PT = 1.5                   # (c): and wider where needed, so that every marker's edge lies at least this far
#                                   inside the frame (final render: protected-only renting at r0 = W0 = 0.9995, the
#                                   largest r0, touched the y axis on the right with the share alone)
B_PAD = v2.B_PAD
WEEK_LABEL_ROOM_PT = v2.WEEK_LABEL_ROOM_PT
WEEK_LABEL_GAP_PT = v2.WEEK_LABEL_GAP_PT
ROOM_STEP_PT = v2.ROOM_STEP_PT
# Keys (C19: each panel its own key, no shared legend row). (b) and (c) each start with a key whose first row is level
# with the panel's letter, right of it (KEY_X_GAP_PT): (b)'s the two margins of its upper sub-panel, (c)'s
# protected-only renting (its label wrapped to C_KEY_MAX_IN); (b)'s lower sub-panel has the key of its two margins above
# it, at the same x, set on its bottom. A key's ink ends KEY_AXES_GAP_PT above the axes it keys ((b)'s upper sub-panel
# and (c) start at one height, below the deeper of their keys). The keys are measured as the PDF sets them (in_pdf;
# review of W-G2: Agg at the canvas's 100 dpi rounds a mathtext line up to whole pixels with a pad, and set (b)'s lower
# key, two mathtext rows, 24.4 pt high where the PDF sets it 20.7 pt high, which left it midway between the two
# sub-panels on the page), and by their ink (key_ink: the labels' glyphs and the markers, not the layout boxes, below
# whose mathtext glyphs about 1 pt is empty). (a)'s axes start at the letters' line (lower by the room of BL0a's label
# where it sits above the axes). (b) is widened beyond its AXES_RATIOS share where its upper key needs it (the share of
# (a) and (c) shrinks in their ratio).
KEY_HANDLE_LENGTH = 1.0           # keys: the handle's length in font sizes (a marker, no line)
KEY_X_GAP_PT = 3.0                # keys: a panel's key starts this far right of its letter
KEY_END_GAP_PT = 6.0              # (b): its keys end at least this far left of its axes' right end (and so of (c)'s
#                                   slot and letter, NAME_LEFT_GAP_PT further right)
KEY_AXES_GAP_PT = 3.0             # keys: from a key's ink to the top of the axes it keys (a top y tick label that
#                                   would come within KEY_TICK_CLEAR_PT of the key is left out: clear_top_tick_label)
KEY_TICK_CLEAR_PT = 1.0
B_TICK_ROOM_PT = 11.0             # (b): from the upper sub-panel's bottom to the lower key's ink (the x ticks, 3 pt,
#                                   then 8 pt, against the key's KEY_AXES_GAP_PT to its own sub-panel)
MARKER_CLEAR_PT = 0.5             # (b): a marker's edge at least this far inside its sub-panel's top (and bottom where
#                                   the sub-panel has no week label below the data; review of W-G2: the top marker of
#                                   the W0 sub-panel was clipped)
HAIRLINE_PT = 2.0                 # (a): a hatched segment narrower than this (the hatch's line spacing) shows as a
#                                   white hairline, which the caption draft names with its largest value (review of
#                                   W-G2)
C_KEY_MAX_IN = 1.25               # (c): the key's label wraps at word breaks to at most this width (TICK_PT: one line,
#                                   0.95 in)
BL0A_ROOM_PT = 0.5                # (a): BL0a's label above the axes ends at least this far below the page's top edge
LETTER_RISE_PT = 1.2              # the panel letters' baseline this far above the letters' line (style.panel_letters')
CAPTION_LINE_CHARS = 140
CAPTION_LINES = 5
LABELS = {"a_x": "Trace cost / all-fallback", "b_x": "Week", "b_y": {"cost": "Cost margin", "w0": "$W_0$ margin"},
          "c_x": "Trace cost / all-fallback", "c_y": "Worst case $W_0$", "no_data": "no runs"}
STATUS = {"statistics": "descriptive (design/ms7/plan.md D4; design/sublet_v2.md §4.5, Dependence)"}


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


def _sha(inp: Inputs, name: str) -> str:
    return hashlib.sha256(inp.path(name).read_bytes()).hexdigest()


def _week_values(block: Any, weeks: Sequence[str], what: str) -> list[float]:
    """The values block.<week>[.<SEED>] of every week; MissingKey naming the weeks without one."""
    vals, missing = [], []
    for w in weeks:
        v = block.get(w) if isinstance(block, Mapping) else None
        if isinstance(v, Mapping):
            v = v.get(str(SEED))
        if v is None:
            missing.append(w)
        else:
            vals.append(float(v))
    if missing:
        raise MissingKey(f"{what}: no value in weeks {missing}")
    return vals


def _stats(vals: Sequence[float]) -> dict:
    return {"median": float(statistics.median(vals)), "min": float(min(vals)), "max": float(max(vals)), "n": len(vals)}


def panel_a(inp: Inputs, main: Mapping) -> tuple[dict, list]:
    """(a): fig4v2.json's (a) (data.a and its labels), with each bar's median checked against main's r0; each bar's
    whisker is the range of main's per-week r0 (bar.range: min, max, n; C10), which replaces fig4v2's week-bootstrap
    interval (its ci_lo and ci_hi are dropped)."""
    payload = _json(inp, FIG4V2)
    if payload.get("figure") != "fig4v2":
        raise style.StyleError(f"{FIG4V2} is the extract of {payload.get('figure')!r}, not 'fig4v2'")
    d = need(payload, "data", what=FIG4V2)
    a = json.loads(json.dumps(need(d, "a", what=FIG4V2)))
    if tuple(a.get("order") or ()) != BARS:
        raise style.StyleError(f"{FIG4V2}: (a)'s bars {a.get('order')} are not fig4_v2.BARS {list(BARS)}")
    weeks = [str(w) for w in need(a, "weeks", what=FIG4V2)]
    for key in BARS:
        tag = v2.TAGS[key]
        r0 = _week_values(need(main, "table", tag, TRACE_MODE, what=MAIN), weeks, f"{MAIN} table.{tag}.{TRACE_MODE}")
        med, have = statistics.median(r0), a[key].get("median")
        if have is None or abs(float(have) - med) > 1e-12 * max(1.0, abs(med)):
            raise style.StyleError(f"{FIG4V2}: (a)'s median of {tag} is {have}, the median of {MAIN}'s r0 is {med} "
                                   "(a stale fig4v2.json: rerun figs/fig4_v2.py)")
        for k in ("ci_lo", "ci_hi"):
            a[key].pop(k, None)
        st = _stats(r0)
        a[key]["range"] = {"min": st["min"], "max": st["max"], "n": st["n"]}
    a["whiskers"] = (f"range over the weeks: min to max of the per-week r0 ({MAIN} table.<tag>.{TRACE_MODE}.<week>."
                     f"{SEED}), n weeks; fig4v2's week-bootstrap intervals are not drawn (C10)")
    for c in a["components"]["order"]:
        if c not in COMPONENT_FILLS:
            raise style.StyleError(f"{FIG4V2}: (a)'s component {c!r} has no fill in COMPONENT_FILLS")
    lab = need(d, "labels", what=FIG4V2)
    stale = {k: v for k, v in (lab.get("bars") or {}).items() if v != style.POLICIES[k].label}
    if stale or set(lab.get("bars") or {}) != set(BARS):
        raise style.StyleError(f"{FIG4V2}: (a)'s bar names {stale or lab.get('bars')} are not the registry labels "
                               "(a stale fig4v2.json)")
    keep = ("bars", "bl0a", "bl0b", "bl0b_ratio", "components", "own_capacity")
    a_lab = {k: lab.get(k) for k in keep}
    a["source"] = {"extract": FIG4V2, "sha256": _sha(inp, FIG4V2),
                   "fig4v2_meta": {k: (d.get("meta") or {}).get(k) for k in ("git_revision", "analysis_git_revision",
                                                                            "analysis_sha256", "reduced")},
                   "runs_files": len(d.get("runs_files") or [])}
    return {"a": a, "a_labels": a_lab}, weeks


def panel_b(inp: Inputs, ana: Mapping, main: Mapping, weeks: Sequence[str]) -> dict:
    """(b): the confirmation's three margins (fig4_v2.margin_series, its checks included) and X1's lagged margin."""
    b3 = v2.margin_series(ana, main, weeks)
    e7c = _json(inp, E7C)
    lw = [str(w) for w in need(e7c, "meta", "weeks", what=E7C)]
    if lw != list(weeks):
        raise style.StyleError(f"{E7C}: the causal runs' weeks {lw} are not the confirmation's {list(weeks)}")
    g = need(e7c, "margins", "h1", "r0", what=E7C)
    rows = need(g, "weeks", what=f"{E7C} margins.h1.r0")
    lag, best_lag = [], []
    for w in weeks:
        r = rows.get(w) or {}
        d = r.get("delta")
        lag.append(None if d is None else float(d))
        best_lag.append(r.get("best"))
    drawn_wins = sum(1 for v in lag if v is not None and v > 0)
    if int(g.get("n_wins", -1)) != drawn_wins:
        raise style.StyleError(f"{E7C}: margins.h1.r0.n_wins is {g.get('n_wins')}, the lagged margins drawn give "
                               f"{drawn_wins}")
    b = {"weeks": list(weeks), "x": [int(w) for w in weeks], "trace": b3["trace"], "trace_lag": lag,
         "w0_set": b3["w0_set"], "w0_tau60": b3["w0_tau60"], "best_trace": b3["best_trace"], "best_trace_lag": best_lag,
         "best_w0": b3["best_w0"], "h1_set": b3["h1_set"], "h1_lag_set": list(need(g, "set", what=E7C)),
         "notes": list(b3["notes"]) + [f"week {w}: the lagged margin is missing (runs {(rows.get(w) or {}).get('missing')})"
                                       for w, v in zip(weeks, lag) if v is None],
         "lag_summary": {k: g.get(k) for k in ("n_weeks", "n_wins", "n_ties", "n_losses", "n_lost_missing", "median",
                                               "min", "max")},
         "sources": {**b3["sources"], "trace_lag": "e7c analysis.json margins.h1.r0.weeks.<week>.delta"}}
    neg, lost = [], []
    for i, w in enumerate(weeks):
        vals = {k: b[k][i] for k in MARGINS if b[k][i] is not None and b[k][i] < 0}
        if vals:
            low = min(vals, key=lambda k: vals[k])
            neg.append({"week": w, "x": int(w), "series": sorted(vals), "lowest": low, "y": vals[low]})
        gone = [k for k in MARGINS if b[k][i] is None]
        if gone:
            lost.append({"week": w, "x": int(w), "series": gone})
    b["negative"], b["missing_weeks"] = neg, lost
    sub_of = {k: name for name, ks in B_SUBPANELS for k in ks}
    for n in neg:                     # a negative week is labeled in the first sub-panel with a negative margin
        n["subpanel"] = next(name for name, ks in B_SUBPANELS if any(k in n["series"] for k in ks))
    for m in lost:
        m["subpanel"] = sub_of[m["series"][0]]
    b["subpanels"] = [[name, list(ks)] for name, ks in B_SUBPANELS]
    # the weeks each sub-panel shades: a negative or a missing margin of one of its own series (module docstring)
    b["shaded"] = {name: sorted({n["week"] for n in neg + lost if set(n["series"]) & set(ks)}, key=int)
                   for name, ks in B_SUBPANELS}
    b["dodge_weeks"] = {k: (-B_DODGE if i == 0 else B_DODGE) for _, ks in B_SUBPANELS for i, k in enumerate(ks)}
    return b, e7c


def panel_c(inp: Inputs, main: Mapping, weeks: Sequence[str]) -> tuple[dict, dict]:
    """(c): the medians of r0 (L-tr) and W0 over the weeks; the confirmation's tags from main/summary.json, A9-P from
    the e7r analysis's per-week values."""
    W0 = need(main, "W0", str(SEED), what=MAIN)
    c: dict = {"order": list(C_ORDER), "arrows": [list(a) for a in ARROWS], "named": list(NAMED),
               "legend": list(LEGEND_KEYS), "mode": TRACE_MODE, "policy_seed": SEED}
    for key, tag in C_MAIN.items():
        r0 = _week_values(need(main, "table", tag, TRACE_MODE, what=MAIN), weeks, f"{MAIN} table.{tag}.{TRACE_MODE}")
        w0 = _week_values(need(W0, tag, what=f"{MAIN} W0.{SEED}"), weeks, f"{MAIN} W0.{SEED}.{tag}")
        c[key] = {"tag": tag, "source": "main", "r0": {**_stats(r0), "weeks": dict(zip(weeks, r0))},
                  "W0": {**_stats(w0), "weeks": dict(zip(weeks, w0))}, "label": style.POLICIES[key].label}
    e7r = _json(inp, E7R)
    rw = [str(w) for w in need(e7r, "weeks", what=E7R)]
    if rw != list(weeks):
        raise style.StyleError(f"{E7R}: the baseline runs' weeks {rw} are not the confirmation's {list(weeks)}")
    modes = list((e7r.get("meta") or {}).get("stress_modes") or [])
    if modes and modes != list(stress_modes()):
        raise style.StyleError(f"{E7R}: W0's stress modes {modes} are not the confirmation's {list(stress_modes())}")
    for key, tag in C_E7R.items():
        pw = need(e7r, "tags", tag, "per_week", what=E7R)
        r0 = _week_values({w: (pw.get(w) or {}).get("r0_tr") for w in weeks}, weeks, f"{E7R} tags.{tag}.r0_tr")
        w0 = _week_values({w: (pw.get(w) or {}).get("W0") for w in weeks}, weeks, f"{E7R} tags.{tag}.W0")
        c[key] = {"tag": tag, "source": "e7r", "r0": {**_stats(r0), "weeks": dict(zip(weeks, r0))},
                  "W0": {**_stats(w0), "weeks": dict(zip(weeks, w0))}, "label": style.POLICIES[key].label}
    c["names"] = {k: name_text(k) for k in NAMED}
    return c, e7r


def name_text(key: str) -> str:
    """(c)'s name of a key of NAMED: its registry label without NAME_PREFIX (one line; wrapped at layout)."""
    lab = style.POLICIES[key].label
    return lab[len(NAME_PREFIX):] if lab.startswith(NAME_PREFIX) else lab


def caption(d: Mapping) -> str:
    """The caption draft (at most CAPTION_LINES lines of about CAPTION_LINE_CHARS characters; every number from the
    inputs). The policies by their registry labels, the margins by their legend labels; a hatched component that shows
    as a white hairline (layout's a_thin) named with its largest segment, rounded up (review of W-G2)."""
    n, lag = d["n_weeks"], d["lag"]
    usd = "–" if d["bl0a_usd"] is None else f"{d['bl0a_usd']:,.0f}"
    thin = "".join(f"; {t['label'].lower()}: white hairline (at most {math.ceil(t['max'] * 1e4) / 1e4:.4f})"
                   for t in d.get("thin") or [])
    rng = (f"{lag['min']:.3f} to {lag['max']:.3f}" if lag.get("min") is not None else "no week")
    lost = d.get("missing_weeks") or []
    lost = f" No run in week {', '.join(lost)}: a loss." if lost else ""
    nr = d["range_n"]
    return (f"Fig. 3. End-to-end cost on {n} confirmation week{'s' if n != 1 else ''} (trace lender, overflow "
            f"accounting; all-fallback: {usd} USD/week, median). (a) Medians; whiskers: range over the {nr} "
            f"week{'s' if nr != 1 else ''}; segments: component medians, scaled{thin}; markers: as in (c); "
            f"provision for peak: {d['bl0b_ratio']}. (b) Per week, the least primary baseline minus Sublet "
            f"(positive: Sublet costs less): trace cost, also with demand one slot late ({lag['n_wins']} of {n} weeks "
            f"positive; {rng}), and W0; RetroRenting, τ≥1 h, minus Sublet: W0; shaded: negative margin. (c) Medians; "
            f"named in blue: Sublet, critical-ratio planning and "
            f"critical-ratio renting with one part changed; arrows: notice layer added; grey: all-fallback.{lost}")


def build(inp: Inputs) -> dict:
    main = _json(inp, MAIN)
    ana = _json(inp, ANALYSIS)
    meta = need(main, "meta", what=MAIN)
    pa, weeks = panel_a(inp, main)
    mweeks = sorted(need(main, "table", "Sublet", TRACE_MODE, what=MAIN), key=int)
    if mweeks != weeks:
        raise style.StyleError(f"{FIG4V2}: (a)'s weeks {weeks} are not {MAIN}'s {mweeks}")
    b, e7c = panel_b(inp, ana, main, weeks)
    c, e7r = panel_c(inp, main, weeks)
    a = pa["a"]
    lab = {**LABELS, **pa["a_labels"], "margins": dict(MARGIN_LABELS),
           "c_names": dict(c["names"]), "c_legend": {k: style.POLICIES[k].label for k in LEGEND_KEYS},
           "status": STATUS}
    lag = b["lag_summary"]
    ns = {a[k]["range"]["n"] for k in BARS}
    if len(ns) != 1:
        raise style.StyleError(f"{NAME} (a): the whiskers' ranges cover different numbers of weeks {sorted(ns)}")
    e7c_meta, e7r_meta = e7c.get("meta") or {}, e7r.get("meta") or {}
    reduced = {"main": bool(meta.get("reduced", False)), "fig4v2": bool(a["source"]["fig4v2_meta"].get("reduced")),
               "e7c": bool(e7c_meta.get("reduced")), "e7r": bool(e7r_meta.get("reduced"))}
    scope = {"part": "main", "weeks": list(weeks), "seeds": [SEED], "modes": [TRACE_MODE],
             "W0_modes": list(stress_modes()),
             "tags": {"a": [v2.TAGS[k] for k in BARS], "b": ["Sublet", "Sublet-lag"] + b["h1_set"] + b["h1_lag_set"]
                      + [v2.TAU60], "c": [c[k]["tag"] for k in C_ORDER] + [c[t]["tag"] for _, t in ARROWS]}}
    data = {"a": a, "b": b, "c": c, "labels": lab, "scope": scope,
            "checks": {"e7c": {"registration_matches": ((e7c_meta.get("registration") or {}).get("matches")),
                               "weeks_are_confirmation_weeks": e7c_meta.get("weeks_are_confirmation_weeks"),
                               "identity_holds": (e7c.get("identity") or {}).get("holds"),
                               "gate_pass": (e7c.get("gate") or {}).get("pass")},
                       "e7r": {"identity_all_identical": ((e7r.get("checks") or {}).get("identity_summary") or {})
                               .get("all_identical"),
                               "registration_sha256": e7r_meta.get("script_sha256")}},
            "meta": {"git_revision": meta.get("git_revision"),
                     "analysis_git_revision": (ana.get("meta") or {}).get("git_revision"),
                     "e7c_git_revision": e7c_meta.get("git_revision"), "e7r_git_revision": e7r_meta.get("git_revision"),
                     "reduced": any(reduced.values()), "reduced_by_input": reduced, "weeks": list(weeks),
                     "inputs_sha256": {n: _sha(inp, n) for n in INPUTS}, "sources": []}}
    data["layout"] = layout(data)
    cap = caption({"n_weeks": len(weeks), "range_n": ns.pop(), "bl0a_usd": (a.get("bl0a") or {}).get("usd_median"),
                   "bl0b_ratio": lab.get("bl0b_ratio"), "lag": lag, "thin": data["layout"]["a_thin"],
                   "missing_weeks": [m["week"] for m in b["missing_weeks"]]})
    lab.update(caption=cap, caption_chars=len(cap), caption_lines_est=math.ceil(len(cap) / CAPTION_LINE_CHARS))
    if lab["caption_lines_est"] > CAPTION_LINES:
        raise style.StyleError(f"{NAME}: the caption draft has {len(cap)} characters, more than {CAPTION_LINES} lines "
                               f"of about {CAPTION_LINE_CHARS}")
    data["meta"]["sources"] = list(inp.sources)
    return data


# ---------------------------------------------------------------------------------------------------------------
# Layout
def wrap(fig, text: str, max_in: float) -> list[str]:
    """`text` in lines of at most max_in inches at TICK_PT, broken at spaces (or after a hyphen where a word alone is
    wider); a word wider than max_in stays on its own line."""
    words: list[str] = []
    for w in text.split(" "):
        if text_width_in(fig, w) <= max_in or "-" not in w:
            words.append(w)
            continue
        parts = w.split("-")
        words += [p + "-" for p in parts[:-1]] + [parts[-1]]
    lines: list[str] = []
    for w in words:
        if lines:
            glue = "" if lines[-1].endswith("-") else " "
            cand = lines[-1] + glue + w
            if text_width_in(fig, cand) <= max_in:
                lines[-1] = cand
                continue
        lines.append(w)
    return lines


def x_hi(a: Mapping) -> float:
    """The right end of (a)'s x spine: 1 (BL0a), or the largest bar or whisker end beyond it (the whiskers are the
    ranges over the weeks, bar.range)."""
    return max([1.0] + [v for k in a["order"] for v in (a[k]["median"], (a[k].get("range") or {}).get("max"))
                        if v is not None])


def key_entries(lab: Mapping, name: str, lines: Sequence[str] | None = None) -> list[tuple]:
    """(handle, label) pairs of a key: 'cost' or 'w0', (b)'s two margins of that sub-panel (B_SUBPANELS), or 'c',
    protected-only renting with its label in `lines` (the label wrapped; the registry label where None)."""
    if name == "c":
        (h, label), = style.policy_handles(LEGEND_KEYS, lines=False)
        return [(h, "\n".join(lines) if lines else label)]
    keys = dict(B_SUBPANELS)[name]
    return [(Line2D([], [], **margin_kwargs(k)), lab["margins"][k]) for k in keys]


def make_key(fig, pairs: Sequence[tuple], loc: str, x_in: float, y_in: float):
    """A frameless key of `pairs` in one row (C62; one column as built at 9 pt), its corner `loc` ('upper left' or
    'lower left') at (x_in, y_in) (inches from the figure's bottom left corner; placed through fig.transFigure), drawn
    above every axes, its labels on one baseline as printed (align_baselines)."""
    W, H = (float(v) for v in fig.get_size_inches())
    handles, labels = zip(*pairs)
    leg = fig.legend(list(handles), list(labels), loc=loc, bbox_to_anchor=(x_in / W, y_in / H),
                     bbox_transform=fig.transFigure, ncol=len(pairs), frameon=False, borderpad=0.0,
                     borderaxespad=0.0, handlelength=KEY_HANDLE_LENGTH, handler_map=dict(style.PAIR_HANDLER_MAP))
    align_baselines(leg.get_texts())        # a mathtext label on its plain neighbors' baseline (C62 review)
    return leg


def key_ink(leg, r) -> tuple[float, float]:
    """(bottom, top) of a key's ink as the PDF draws it (`r` the renderer of in_pdf's draw; pt): its labels' glyphs
    (text_ink) and its handles' markers (their window extents)."""
    spans = [text_ink(t, r) for t in leg.get_texts()]
    for h in leg.legend_handles:
        if isinstance(h, Line2D) and h.get_marker() not in (None, "None", "", " "):
            bb = h.get_window_extent(r)
            spans.append((bb.y0, bb.y1))
    return min(s[0] for s in spans), max(s[1] for s in spans)


def key_size_in(fig, pairs: Sequence[tuple]) -> dict:
    """A key of `pairs` (make_key) measured at TICK_PT, in inches: its width w (the larger of the canvas's and the
    PDF's), its height h as the PDF sets it, and the empty room of its box below and above its ink (ink_below,
    ink_above; key_ink), as the PDF sets them (in_pdf)."""
    leg = make_key(fig, pairs, "upper left", 0.5, 0.5 * float(fig.get_size_inches()[1]))

    def measure(r):
        bb = leg.get_window_extent(r)
        return bb, key_ink(leg, r)

    try:
        w = leg.get_window_extent(fig.canvas.get_renderer()).width / fig.dpi
        bb, (lo, hi) = in_pdf(fig, measure)
    finally:
        leg.remove()
    pt = 1.0 / style.BP_PER_IN
    return {"w": max(w, bb.width * pt), "h": bb.height * pt, "ink_below": (lo - bb.y0) * pt,
            "ink_above": (bb.y1 - hi) * pt}


def bl0a_room_pt(fig, lab: Mapping) -> float:
    """(a): how far the axes top lies below the letters' line so that BL0a's label, set above the axes
    (fig4_v2.BL0A_LABEL_RISE_PT) where x_hi > 1, ends BL0A_ROOM_PT below the page's top edge (0 where it fits)."""
    t = fig.text(0.0, 0.0, lab["bl0a"], fontsize=style.TICK_PT, va="bottom")
    h_pt = t.get_window_extent(fig.canvas.get_renderer()).height * 72.0 / fig.dpi
    t.remove()
    return max(0.0, v2.BL0A_LABEL_RISE_PT + h_pt + BL0A_ROOM_PT - style.MARGIN_TOP * style.BP_PER_IN)


def layout(data: Mapping) -> dict:
    """The panels' left reserves and axes widths (inches), (a)'s x range and (c)'s names (module docstring), and the
    heights: (a) from the bottom margin to the letters' line (less BL0a's label room), (b)'s two sub-panels and (c)
    below their keys (keys: each key's corner, width and height and the empty room of its box below and above its ink,
    measured at TICK_PT as the PDF sets them; key_size_in), and (a)'s thin segments (a_thin: the hatched components
    whose widest segment is narrower than HAIRLINE_PT, which the caption draft names)."""
    a, lab = data["a"], data["labels"]
    fig = style.new_figure(NAME)
    names = [lab["bars"][k] for k in a["order"]] + [lab["bl0b"]]
    names_in = style.ytick_reserve(fig, names)
    key = a_key(a)
    left_a = names_in + (key["pad_pt"] - float(mpl.rcParams["ytick.major.pad"])) / style.BP_PER_IN
    col = v2.column_in(fig, a, lab)
    col_in = (v2.COL_GAP_PT + v2.COL_END_PT) / style.BP_PER_IN + col["width"]
    c_lines = {k: wrap(fig, data["c"]["names"][k], NAME_MAX_IN) for k in NAMED}
    name_w = max(text_width_in(fig, ln) for ls in c_lines.values() for ln in ls)
    left_c = name_w + (NAME_GAP_PT + LEADER_RUN_PT + NAME_LEFT_GAP_PT) / style.BP_PER_IN
    W, H = (float(v) for v in fig.get_size_inches())
    right = style.LEFT_LABEL
    avail = W - left_a - col_in - style.LEFT_LABEL - left_c - right
    if avail <= 0:
        raise style.StyleError(f"{NAME}: no room for the panels beside the names and label columns")
    pt = 1.0 / style.BP_PER_IN
    c_key_lines = wrap(fig, lab["c_legend"][LEGEND_KEYS[0]], C_KEY_MAX_IN)
    size = {n: key_size_in(fig, key_entries(lab, n, c_key_lines if n == "c" else None)) for n in ("cost", "w0", "c")}
    (lw_b, rise), (lw_c, _) = letter_box(fig, "b"), letter_box(fig, "c")
    # widths: AXES_RATIOS, with (b) widened where its upper key (right of its letter) needs it
    w_a, w_b, w_c = (avail * r / sum(AXES_RATIOS) for r in AXES_RATIOS)
    need_b = lw_b + (KEY_X_GAP_PT + KEY_END_GAP_PT) * pt + max(size["cost"]["w"], size["w0"]["w"]) - style.LEFT_LABEL
    if need_b > w_b:
        rest = avail - need_b
        w_a, w_b, w_c = (rest * AXES_RATIOS[0] / (AXES_RATIOS[0] + AXES_RATIOS[2]), need_b,
                         rest * AXES_RATIOS[2] / (AXES_RATIOS[0] + AXES_RATIOS[2]))
    hi = x_hi(a)
    # heights (inches from the bottom): the letters' line, (a)'s top, the keys, (b)'s sub-panels and (c); each key's
    # ink KEY_AXES_GAP_PT above the axes it keys, (b)'s lower key set on its bottom, its ink B_TICK_ROOM_PT below the
    # upper sub-panel
    line = H - style.MARGIN_TOP
    key_top = line + (LETTER_RISE_PT + rise) * pt              # a key's first row level with its panel's letter
    a_top = line - (bl0a_room_pt(fig, lab) * pt if hi > 1.0 + 1e-12 else 0.0)
    x_b = left_a + w_a + col_in + style.LEFT_LABEL
    # (c)'s slot (its letter and key) starts after the gutter, at its widest name's left end
    slot_b, slot_c = x_b - style.LEFT_LABEL, x_b + w_b + NAME_LEFT_GAP_PT * pt
    x_c = x_b + w_b + left_c
    top_bc = key_top - max(size[n]["h"] - size[n]["ink_below"] for n in ("cost", "c")) - KEY_AXES_GAP_PT * pt
    w0 = size["w0"]
    mid = KEY_AXES_GAP_PT * pt + (w0["h"] - w0["ink_below"] - w0["ink_above"]) + B_TICK_ROOM_PT * pt
    hs = 0.5 * (top_bc - style.MARGIN_BOTTOM - mid)
    if hs <= 0:
        raise style.StyleError(f"{NAME}: no height left for (b)'s sub-panels below their keys")
    x_kb = slot_b + lw_b + KEY_X_GAP_PT * pt
    keys = {"cost": {"loc": "upper left", "x_in": x_kb, "y_in": key_top},
            "w0": {"loc": "lower left", "x_in": x_kb,
                   "y_in": style.MARGIN_BOTTOM + hs + KEY_AXES_GAP_PT * pt - w0["ink_below"]},
            "c": {"loc": "upper left", "x_in": slot_c + lw_c + KEY_X_GAP_PT * pt, "y_in": key_top,
                  "lines": list(c_key_lines)}}
    if keys["c"]["x_in"] + size["c"]["w"] > W - style.MARGIN_RIGHT:
        raise style.StyleError(f"{NAME} (c): the key ({size['c']['w']:.3f} in) is wider than (c)'s slot right of its "
                               "letter")
    for n, k in keys.items():
        k.update(entries=list(LEGEND_KEYS if n == "c" else dict(B_SUBPANELS)[n]), w_in=size[n]["w"],
                 h_in=size[n]["h"], ink_below_in=size[n]["ink_below"], ink_above_in=size[n]["ink_above"])
        for f in ("x_in", "y_in", "w_in", "h_in", "ink_below_in", "ink_above_in"):
            k[f] = round(k[f], 4)
    # (a): the hatched components whose widest segment is narrower than HAIRLINE_PT (x: w_a over [0, hi])
    thin = []
    for comp in a["components"]["order"]:
        segs = [float((a[k].get("segments") or {}).get(comp) or 0.0) for k in a["order"]
                if a[k].get("median") is not None]
        widest = max(segs, default=0.0)
        if COMPONENT_FILLS[comp]["hatch"] and 0.0 < widest * w_a * style.BP_PER_IN / hi < HAIRLINE_PT:
            thin.append({"component": comp, "label": a["components"]["labels"][comp], "max": widest,
                         "max_pt": round(widest * w_a * style.BP_PER_IN / hi, 4)})
    r4 = lambda v: [round(x, 4) for x in v]                             # noqa: E731
    return {"left_in": [round(left_a, 4), style.LEFT_LABEL, round(left_c, 4)],
            "axes_in": [round(w_a + col_in, 4), round(w_b, 4), round(w_c, 4)], "right_in": right,
            "a_x_hi": hi, "a_x_max": hi * (w_a + col_in) / w_a, "a_column_in": round(col_in, 4), "a_key": key,
            "a_thin": thin, "c_name_lines": c_lines, "c_names_in": round(name_w, 4), "c_slot_in": round(slot_c, 4),
            "letters_in": round(line, 4), "a_top_in": round(a_top, 4),
            "b_rects_in": [r4((x_b, style.MARGIN_BOTTOM + hs + mid, w_b, hs)), r4((x_b, style.MARGIN_BOTTOM, w_b, hs))],
            "c_rect_in": r4((x_c, style.MARGIN_BOTTOM, w_c, top_bc - style.MARGIN_BOTTOM)), "keys": keys,
            "measured": {"bar_names_in": round(names_in, 4), **{f"{k}_in": round(v, 4) for k, v in col.items()},
                         "b_need_in": round(need_b, 4)},
            "rule": f"(a): reserve = widest bar name + the key markers' column; axes = bars + fig4_v2's label column; "
                    f"(b) the standard reserve; (c): reserve = widest name line (names wrapped at {NAME_MAX_IN} in) + "
                    f"{NAME_GAP_PT:g} + {LEADER_RUN_PT:g} + {NAME_LEFT_GAP_PT:g} pt (the gutter after (b), where "
                    f"(c)'s slot starts), y axis in a right reserve of {right} in; the axes share the rest in the "
                    f"ratios {list(AXES_RATIOS)}, (b) at least its keys' width right of its letter ({KEY_X_GAP_PT:g} "
                    f"pt after the letter, {KEY_END_GAP_PT:g} pt before (b)'s axes end). Heights: the letters' "
                    f"line {style.MARGIN_TOP} in below the top; (a)'s top on it "
                    f"(lower by BL0a's label room where x_hi > 1); the keys of (b) and (c) start level with their "
                    f"letters; (b)'s upper sub-panel and (c) {KEY_AXES_GAP_PT:g} pt below the deeper key's ink; (b)'s "
                    f"lower key's ink {B_TICK_ROOM_PT:g} pt below the upper sub-panel, its sub-panel "
                    f"{KEY_AXES_GAP_PT:g} pt below it; the two sub-panels of one height; the keys measured as the PDF "
                    f"sets them, by their ink"}


# ---------------------------------------------------------------------------------------------------------------
# (a)
def a_key(a: Mapping) -> dict:
    """(a)'s key markers (A_MARKERS): the widest marker of the bars with a median (pt, its edge included), the y tick
    labels' pad that leaves A_KEY_GAP_PT on each side of it, and the markers' centers left of the bars' start."""
    keys = [k for k in a["order"] if a[k].get("median") is not None] if A_MARKERS else []
    w = max((float(np.ptp(v2.marker_outline_pt(style.policy(k).marker, style.policy(k).markersize,
                                               style.MARKER_EDGE_PT)[:, 0])) for k in keys), default=0.0)
    if not keys:
        return {"keys": [], "width_pt": 0.0, "pad_pt": float(mpl.rcParams["ytick.major.pad"]), "center_pt": 0.0}
    return {"keys": keys, "width_pt": round(w, 4), "pad_pt": round(2 * A_KEY_GAP_PT + w, 4),
            "center_pt": round(A_KEY_GAP_PT + 0.5 * w, 4)}


def fill_kwargs(comp: str) -> dict:
    """barh keyword arguments of a component's fill (COMPONENT_FILLS; the hatch drawn in HATCH_COLOR, no edge)."""
    f = COMPONENT_FILLS[comp]
    return dict(color=f["facecolor"], edgecolor=HATCH_COLOR, linewidth=0, hatch=f["hatch"])


def draw_a(ax, a: Mapping, lab: Mapping, lay: Mapping) -> None:
    """(a): fig4_v2.draw_a's bars, BL0a's line and label, the components' key and BL0b's row (its helpers key_rows and
    the label column of column_in), with the fills of COMPONENT_FILLS (bars and key) and each bar's whisker the
    range over the weeks (bar.range) in the policy's label color in a white casing; (a)'s x ticks A_X_NBINS; then each
    bar's policy marker between its name and the bar (A_MARKERS, layout's a_key)."""
    order = list(a["order"])
    comps = list(a["components"]["order"])
    n_rows = len(order) + 1                              # the bars and BL0b's row
    hi, X = float(lay["a_x_hi"]), float(lay["a_x_max"])
    label_above = hi > 1.0 + 1e-12                       # BL0a's line inside the bars' range: its label above its top
    rows = v2.key_rows(len(order), len(comps), label_above)
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
                seg = ax.barh(i, wd, left=x0, height=A_BAR_H, zorder=1.5, **fill_kwargs(comp))
                for p in seg.patches:
                    p._sublet_role, p._sublet_component = "segment", comp
            x0 += wd
        if not e["segments"]:                            # components null: unstacked, in the darkest fill
            ax.barh(i, total, height=A_BAR_H, zorder=1.5, **fill_kwargs(comps[-1] if comps else "stranding"))
        outline = ax.barh(i, total, height=A_BAR_H, fill=False, edgecolor=pol.text_color, linewidth=v2.BAR_EDGE_PT,
                          zorder=1.6)
        for p in outline.patches:
            p._sublet_policy = key                       # the bar's policy, for the registry checks
        rng = e.get("range") or {}
        if rng.get("min") is not None and rng.get("max") is not None:
            eb = style.errorbars(ax, key, [total], [i], [rng["min"]], [rng["max"]], orientation="x", zorder=1.7,
                                 ecolor=pol.label_color)
            for lc in eb.lines[2]:                       # in a white casing (fig4_v2.WHISKER_CASING_PT)
                lc.set_path_effects([patheffects.Stroke(linewidth=style.UNCERTAINTY_PT + v2.WHISKER_CASING_PT,
                                                        foreground="white"), patheffects.Normal()])
                lc._sublet_role, lc._sublet_whisker = "whisker", key
    ax.set_xlim(0.0, X)
    ax.set_ylim(n_rows - 0.5, -0.5)
    ticks = [float(v) for v in MaxNLocator(nbins=A_X_NBINS, steps=[1, 2, 5, 10]).tick_values(0.0, hi)
             if -1e-12 <= v <= hi + 1e-12]               # (a)'s bars are narrower than fig4v2's: fewer x ticks
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_major_formatter(style.PLAIN)
    ax.spines["bottom"].set_bounds(0.0, hi)
    grid = [g for g in np.arange(A_GRID_STEP, hi, A_GRID_STEP) if abs(g - 1.0) > 1e-9]
    if grid:                                             # behind the bars, over the bars' rows only (C62)
        gl = ax.vlines(grid, -0.5, len(order) - 0.5, colors=style.GRID_GREY, linewidths=style.GRID_PT, zorder=0.5)
        gl._sublet_role = "grid"
        # a minor tick under each grid line that has no major tick, so that the grid explains itself (C62 review)
        ax.xaxis.set_minor_locator(FixedLocator([g for g in grid if min(abs(g - t) for t in ticks) > 1e-9]))
    ax.set_xlabel(lab["a_x"])
    ax.xaxis.label.set_x(0.5 * hi / X)                   # centered under the spine (common.label_column)
    ax.set_yticks(range(n_rows), [lab["bars"][k] for k in order] + [lab["bl0b"]])
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)

    fig = ax.figure
    r = fig.canvas.get_renderer()
    per_pt = X / (style.axes_rect_in(ax)[2] * style.BP_PER_IN)       # data units per pt along x
    x_col = hi + v2.COL_GAP_PT * per_pt                  # the label column's left edge
    if label_above:                                      # above the line's top end, in the panel letters' band
        t = ax.annotate(lab["bl0a"], xy=(1.0, 1.0), xycoords=("data", "axes fraction"),
                        xytext=(0.0, v2.BL0A_LABEL_RISE_PT), textcoords="offset points", ha="center", va="bottom",
                        fontsize=style.TICK_PT, color=style.policy("bl0a").label_color, zorder=style.Z_THEORY_LABEL)
    else:                                                # beside the line's top end, level with the first bar
        t = ax.text(x_col, 0, lab["bl0a"], ha="left", va="center", fontsize=style.TICK_PT,
                    color=style.policy("bl0a").label_color, zorder=style.Z_THEORY_LABEL)
    t._sublet_role = "direct_label"
    for j, comp in zip(rows, comps):                     # the key: a patch at the bars' height and the name, a row each
        kp = ax.barh(j, v2.KEY_HANDLE_PT * per_pt, left=x_col, height=A_BAR_H, zorder=1.5, **fill_kwargs(comp))
        for p in kp.patches:
            p._sublet_role, p._sublet_component = "key_patch", comp
        k = ax.text(x_col + (v2.KEY_HANDLE_PT + v2.KEY_TEXT_GAP_PT) * per_pt, j, a["components"]["labels"][comp],
                    ha="left", va="center_baseline", fontsize=style.TICK_PT)     # as the names (C62 review)
        k._sublet_role = "key"

    # BL0b: its own row; off the axis: a light bar to the spine's end with a break mark (offscale_bar; C62 review: the
    # empty row left its ratio 1.2 in from its name), its ratio at the start of the label column, on the names'
    # baseline, and an arrow
    row = len(order)
    ratio = None
    if a["bl0b"].get("overflow_over_bl0a") is None:
        ax.text(0.01, row, lab.get("no_data", "no runs"), transform=ax.get_yaxis_transform(), ha="left",
                va="center", fontsize=style.TICK_PT, color=style.THEORY_LABEL_GREY)
    else:
        end = X - v2.COL_END_PT * per_pt                 # the column's right end
        pol = style.policy("bl0b")
        offscale_bar(ax, row, hi, per_pt, pol.text_color)
        ratio = style.direct_label(ax, "bl0b", x_col, row, lab["bl0b_ratio"], dx=0.0, ha="left",
                                   va="center_baseline")
        ratio._sublet_role = "direct_label"
        tail_px = ratio.get_window_extent(r).x1 + v2.ARROW_TEXT_PT * fig.dpi / 72.0
        tail = float(ax.transData.inverted().transform((tail_px, 0.0))[0])
        # C62: ARROW_IN long, not to the column's end (as built at 9 pt), whose key is wider than the ratio and its
        # arrow: the longer arrow ended 6 pt from (b)'s y label and read as pointing at it
        head = min(end, tail + v2.ARROW_IN * style.BP_PER_IN * per_pt)
        if (head - tail) / per_pt < v2.ARROW_IN * style.BP_PER_IN - 0.5:
            raise style.StyleError(f"{NAME} (a): BL0b's arrow is shorter than {v2.ARROW_IN} in")
        arr = style.arrow(ax, (tail, row), (head, row), color=pol.color, linewidth=style.REFERENCE_POLICY_PT,
                          shrinkA=0.0, shrinkB=0.0)
        arr._sublet_role = "off_scale_arrow"
        arr._sublet_policy = "bl0b"

    # BL0a: a line at 1 across the bars, above them in a white casing; it ends half a row below the last bar, or
    # BL0A_CLEAR_PT above BL0b's ratio where the ratio lies under it (fig4_v2.draw_a)
    to_pt = 72.0 / fig.dpi
    y_end = len(order) - 0.5
    if ratio is not None:
        bb = ratio.get_window_extent(r)
        x1_px = ax.transData.transform((1.0, row))[0]
        if bb.x0 - v2.BL0A_CLEAR_PT / to_pt < x1_px < bb.x1 + v2.BL0A_CLEAR_PT / to_pt:
            y_clear = ax.transData.inverted().transform((x1_px, bb.y1 + v2.BL0A_CLEAR_PT / to_pt))[1]
            if y_clear < len(order) - 1 + 0.5 * A_BAR_H:
                raise style.StyleError(f"{NAME} (a): BL0b's ratio {lab['bl0b_ratio']!r} leaves no room under the "
                                       "last bar for BL0a's line")
            y_end = min(y_end, float(y_clear))
    kw = style.policy_kwargs("bl0a", markers=False)
    kw["zorder"] = v2.Z_BL0A
    (line,) = ax.plot([1.0, 1.0], [y_end, -0.5], **kw)
    line.set_path_effects([patheffects.Stroke(linewidth=kw["linewidth"] + v2.BL0A_CASING_PT, foreground="white"),
                           patheffects.Normal()])
    line._sublet_policy = "bl0a"

    key = lay["a_key"]
    if key["keys"]:
        ax.tick_params(axis="y", pad=key["pad_pt"])
        tr = offset_copy(ax.get_yaxis_transform(), fig=ax.figure, x=-key["center_pt"], units="points")
        for i, k in enumerate(a["order"]):
            if k in key["keys"]:
                ln = style.scatter_policy(ax, k, [0.0], [i], transform=tr, clip_on=False)
                ln._sublet_role = "name_key"
    # the names with mathtext on the rows' pitch as printed (C62 review: 0.45 pt off), after the last tick_params
    align_baselines([tk.label1 for tk in ax.yaxis.get_major_ticks()])


def offscale_bar(ax, row: float, hi: float, per_pt: float, color: str) -> None:
    """(a): BL0b's row, beyond the axis (C62 review): a bar of A_BAR_H in OFFSCALE_FILL from 0 to the spine's end hi,
    edged in `color` (BL0b's) on its top, bottom and left and open at its right end, cut OFFSCALE_BREAK_AT of the way
    by a white slanted gap with drawn edges (a break mark, BREAK_* pt), so that the row reads as one bar running off
    the scale to its ratio."""
    rows_per_pt = (ax.get_ylim()[0] - ax.get_ylim()[1]) / (style.axes_rect_in(ax)[3] * style.BP_PER_IN)
    y0, y1 = row - 0.5 * A_BAR_H, row + 0.5 * A_BAR_H        # y0 the bar's top on the page (the y axis runs down)
    bar = ax.barh(row, hi, height=A_BAR_H, color=OFFSCALE_FILL, linewidth=0, zorder=1.5)
    for p in bar.patches:
        p._sublet_role, p._sublet_policy = "offscale_bar", "bl0b"
    (edge,) = ax.plot([hi, 0.0, 0.0, hi], [y0, y0, y1, y1], color=color, linewidth=v2.BAR_EDGE_PT,
                      solid_joinstyle="miter", solid_capstyle="butt", zorder=1.6)
    edge._sublet_role = "offscale_bar"
    xb = OFFSCALE_BREAK_AT * hi
    g, sl = BREAK_GAP_PT * per_pt, BREAK_SLANT_PT * per_pt
    top, bot = y0 - BREAK_OVER_PT * rows_per_pt, y1 + BREAK_OVER_PT * rows_per_pt
    left = [(xb - 0.5 * g - 0.5 * sl, bot), (xb - 0.5 * g + 0.5 * sl, top)]
    right = [(xb + 0.5 * g - 0.5 * sl, bot), (xb + 0.5 * g + 0.5 * sl, top)]
    gap = Polygon(left + right[::-1], closed=True, facecolor="white", edgecolor="none", zorder=1.65)
    ax.add_patch(gap)
    gap._sublet_role = "offscale_break"
    for side in (left, right):
        (ln,) = ax.plot(*zip(*side), color=color, linewidth=BREAK_PT, solid_capstyle="butt", zorder=1.7)
        ln._sublet_role = "offscale_break"


# ---------------------------------------------------------------------------------------------------------------
# (b)
def margin_kwargs(k: str) -> dict:
    """Line2D keyword arguments of a margin series of (b): black markers, no line (MARGIN_STYLES)."""
    kw = dict(color=MARGIN_COLOR, linestyle="none", markersize=style.MARKER_PT, markeredgewidth=style.MARKER_EDGE_PT,
              markeredgecolor=MARGIN_COLOR, zorder=style.Z_DATA)
    kw.update(MARGIN_STYLES[k])
    return kw


def place_axes(ax, rect: Sequence[float]) -> None:
    """Move `ax` to `rect` (x, y, width, height in inches from the figure's bottom left corner; the layout's) and
    record it (finalize's geometry check), before anything is drawn in it."""
    W, H = (float(v) for v in ax.figure.get_size_inches())
    x, y, w, h = (float(v) for v in rect)
    ax.set_position((x / W, y / H, w / W, h / H))
    ax._sublet_rect_in = (x, y, w, h)


def split_b(fig, ax, rects: Sequence[Sequence[float]]) -> list:
    """(b)'s slot as two axes on one week axis (B_SUBPANELS, top first) at the layout's rectangles (b_rects_in: each
    below its key); each records its rectangle (finalize's geometry check) and the slot's left edge (panel_letters)."""
    slot = ax._sublet_slot_left_in
    fig.delaxes(ax)
    W, H = (float(v) for v in fig.get_size_inches())
    out = []
    for x, y0, w, hs in ((float(v) for v in r) for r in rects):
        sub = fig.add_axes((x / W, y0 / H, w / W, hs / H), sharex=out[0] if out else None)
        sub._sublet_rect_in = (x, y0, w, hs)
        sub._sublet_slot_left_in = slot
        out.append(sub)
    for sub in out[:-1]:
        sub.tick_params(axis="x", labelbottom=False)
    return out


def _marker_half_pt(keys: Sequence[str]) -> float:
    """The largest half-height (pt, the edge's outer side included) of the markers of `keys` (MARGIN_STYLES)."""
    out = 0.0
    for k in keys:
        kw = margin_kwargs(k)
        out = max(out, 0.5 * float(np.ptp(v2.marker_outline_pt(kw["marker"], kw["markersize"],
                                                                kw["markeredgewidth"])[:, 1])))
    return out


def _sub_ylim(ax, b: Mapping, keys: Sequence[str], extra_pt: float, flagged: bool) -> float:
    """The sub-panel's y range: its series and 0, padded by B_PAD, with WEEK_LABEL_ROOM_PT + extra_pt below where it
    holds a week label, and the highest marker's edge (and, without a week label, the lowest's) at least
    MARKER_CLEAR_PT inside the range (review of W-G2: B_PAD alone, with the label room stretching the range below,
    left the top marker of the W0 sub-panel 1.1 pt below the top, clipped); returns the lowest value.

    With the span s, the label room's share f of it, a marker's need c (its half-height and MARKER_CLEAR_PT over the
    axes' height) and e_t, e_b the distances of the highest and lowest values from hi and lo: s is the least solution
    of s = (hi - lo + max(pad, c s - e_t) + max(pad, c s - e_b)) / (1 - f), the largest of the fixed points of its
    four linear pieces (the right side is convex in s with slopes below 1)."""
    ser = [float(v) for k in keys for v in b[k] if v is not None]
    vals = [0.0] + ser
    lo, hi = min(vals), max(vals)
    pad = B_PAD * (hi - lo) if hi > lo else 0.05
    h_pt = style.axes_rect_in(ax)[3] * style.BP_PER_IN
    f = (WEEK_LABEL_ROOM_PT + extra_pt) / h_pt if flagged else 0.0
    c = (_marker_half_pt(keys) + MARKER_CLEAR_PT) / h_pt if ser else 0.0
    c_t, c_b = c, (0.0 if flagged else c)          # above a week label's room the lowest marker is clear anyway
    e_t, e_b = (hi - max(ser), min(ser) - lo) if ser else (0.0, 0.0)
    d = hi - lo
    if 1.0 - f - c_t - c_b <= 0.0:
        raise style.StyleError(f"{NAME} (b): the sub-panel ({h_pt:.1f} pt) has no height left for its data")
    span = max((d + 2 * pad) / (1.0 - f), (d + pad - e_t) / (1.0 - f - c_t), (d + pad - e_b) / (1.0 - f - c_b),
               (d - e_t - e_b) / (1.0 - f - c_t - c_b))
    top = max(pad, c_t * span - e_t)
    ax.set_ylim(hi + top - span, hi + top)
    return lo


def _column_low_pt(ax, b: Mapping, keys: Sequence[str], n: Mapping, dodge: Mapping) -> float:
    """The lowest point (pt) of the markers of `keys` in a flagged week's column (fig4_v2's rule)."""
    to_pt = 72.0 / ax.figure.dpi
    i = list(b["x"]).index(n["x"])
    lows = []
    for k in keys:
        v = b[k][i]
        if v is not None and math.isfinite(float(v)):
            kw = margin_kwargs(k)
            half = 0.5 * np.ptp(v2.marker_outline_pt(kw["marker"], kw["markersize"], kw["markeredgewidth"])[:, 1])
            lows.append(ax.transData.transform((n["x"] + dodge[k], float(v)))[1] * to_pt - half)
    if not lows:
        y_pt = ax.transData.transform((n["x"], n["y"]))[1] * to_pt
        lows.append(y_pt - 0.5 * (style.MARKER_PT + style.MARKER_EDGE_PT))
    return min(lows)


def draw_b_sub(ax, b: Mapping, name: str, keys: Sequence[str], lab: Mapping, dodge: Mapping) -> list:
    """One sub-panel of (b): its two series, the line at 0, its flagged weeks' labels (fig4_v2's placement: the
    highest free spot below the column's lowest marker, the room below the data grown until they fit). Returns the
    flagged weeks it labels."""
    x = finite(b["x"])
    for k in keys:
        y = finite(b[k])
        ok = np.isfinite(y)
        if ok.any():
            (ln,) = ax.plot(x[ok] + dodge[k], y[ok], label="_nolegend_", **margin_kwargs(k))
            ln._sublet_role = f"margin:{k}"
    style.reference_line(ax, y=0.0)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=3, steps=[1, 2, 5, 10]))     # short tick labels (no 0.25)
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.set_ylabel(lab["b_y"][name])
    neg_weeks = {n["week"] for n in b["negative"]}
    lo = _sub_ylim(ax, b, keys, 0.0, False)
    flagged = [n for n in b["negative"] if n["subpanel"] == name] + \
        [{**m, "y": lo} for m in b["missing_weeks"] if m["subpanel"] == name and m["week"] not in neg_weeks]
    if not flagged:
        return []
    labels = None
    for extra in np.arange(0.0, len(flagged) * LINE_STEP_PT + 0.5 * ROOM_STEP_PT, ROOM_STEP_PT):
        _sub_ylim(ax, b, keys, extra, True)
        tops = {n["week"]: _column_low_pt(ax, b, keys, n, dodge) - WEEK_LABEL_GAP_PT for n in flagged}
        labels = []
        for n in sorted(flagged, key=lambda n: (-tops[n["week"]], n["x"])):
            t = v2._column_label(ax, n, tops[n["week"]])
            if t is None:
                break
            t.set_path_effects([])        # clear of everything drawn: no white halo cutting the column's shade (C62)
            labels.append(t)
        if len(labels) == len(flagged):
            break
        for t in labels:
            t.remove()
        labels = None
    if labels is None:
        raise style.StyleError(f"{NAME} (b, {name}): the weeks' labels do not fit below their columns")
    return flagged


def clear_top_tick_label(ax, key_box) -> bool:
    """Leave the top major y tick of `ax` unlabeled, at minor length, where its label would come within
    KEY_TICK_CLEAR_PT of `key_box` (a key's window extent above the axes; both across and up); returns whether it
    did."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    y0, y1 = sorted(ax.get_ylim())
    locs = [float(t) for t in ax.yaxis.get_majorticklocs() if y0 <= t <= y1]
    if not locs:
        return False
    top = max(locs)
    clear = KEY_TICK_CLEAR_PT * fig.dpi / 72.0
    for tk in ax.yaxis._update_ticks():
        if abs(tk.get_loc() - top) > 1e-12 * max(1.0, abs(top)) or not tk.label1.get_visible():
            continue
        bb = tk.label1.get_window_extent(r)
        if bb.y1 + clear > key_box.y0 and bb.x1 + clear > key_box.x0 and bb.x0 - clear < key_box.x1:
            ax.yaxis.set_major_locator(FixedLocator([t for t in locs if t != top]))
            ax.yaxis.set_minor_locator(FixedLocator([top]))
            return True
    return False


def draw_b(axes: Sequence, b: Mapping, lab: Mapping) -> None:
    """(b): the sub-panels of B_SUBPANELS on one week axis; each sub-panel shades its own flagged weeks (b['shaded']: a
    negative or a missing margin of one of its series); no two markers of a sub-panel overlapping by more than
    MAX_MARKER_OVERLAP (StyleError)."""
    x = finite(b["x"])
    x0, x1 = (float(np.nanmin(x)), float(np.nanmax(x))) if x.size else (0.0, 1.0)
    dodge = dict(need(b, "dodge_weeks", what=f"{NAME} extract b"))
    shaded = need(b, "shaded", what=f"{NAME} extract b")
    for ax, (name, keys) in zip(axes, b["subpanels"]):
        ax.set_xlim(x0 - 0.7, x1 + 0.7)
        draw_b_sub(ax, b, name, keys, lab, dodge)
    bottom = axes[-1]
    bottom.xaxis.set_major_formatter(style.PLAIN)
    bottom.set_xlabel(lab["b_x"])
    v2.week_tick_labels(bottom, list(x))
    for ax, (name, _) in zip(axes, b["subpanels"]):
        y0, y1 = ax.get_ylim()
        for w in shaded[name]:
            r = style.shade_region(ax, (int(w) - 0.5, int(w) + 0.5), (y0, y1))
            r._sublet_role, r._sublet_week = "shade", str(w)
        worst = v2.marker_overlaps(ax)
        if worst and worst[0]["share"] > MAX_MARKER_OVERLAP:
            raise style.StyleError(f"{NAME} (b): markers overlap by more than {MAX_MARKER_OVERLAP:.2f} of a marker: "
                                   f"{worst[:3]}")


# ---------------------------------------------------------------------------------------------------------------
# (c)
def _c_limits(ax, c: Mapping) -> None:
    """The data ranges with C_PAD and C_Y_PAD beyond them, widened where a marker's edge would lie less than C_EDGE_PT
    inside the frame (the axes' size in pt from its position, set before (c) is drawn)."""
    keys = [k for k in C_ORDER] + [t for _, t in ARROWS]
    xs = [c[k]["r0"]["median"] for k in keys]
    ys = [c[k]["W0"]["median"] for k in keys]
    _, _, w_pt, h_pt = (v * style.BP_PER_IN for v in style.axes_rect_in(ax))
    reach = max(_marker_radius_pt(k) for k in C_ORDER) + C_EDGE_PT       # an arrow head has no marker (ARROWS)
    for vals, extra, setter, pad, span in ((xs, [], ax.set_xlim, C_PAD, w_pt),
                                           (ys, [1.0], ax.set_ylim, C_Y_PAD, h_pt)):
        lo, hi = min(vals + extra), max(vals + extra)
        p = pad * (hi - lo) if hi > lo else 0.05
        a, b = lo - p, hi + p
        for _ in range(4):                    # (b - a) grows, so the reach in data units does too: a few rounds
            per_pt = (b - a) / span
            a, b = min(a, min(vals) - reach * per_pt), max(b, max(vals) + reach * per_pt)
        setter(a, b)


def _marker_radius_pt(key: str) -> float:
    p = style.policy(key)
    return 0.5 * (p.markersize + style.MARKER_EDGE_PT)


def draw_c(ax, c: Mapping, lab: Mapping, lay: Mapping) -> None:
    """(c) (module docstring): reference line, arrows, points, names with leaders; the y axis on the right."""
    _c_limits(ax, c)
    style.reference_line(ax, y=1.0)
    fig = ax.figure
    to_pt = 72.0 / fig.dpi
    # names whose points coincide (within COINCIDE_PT) share one name, one leader and one marker, the first's (C62
    # review: two markers on one point overprinted into one unreadable glyph)
    pts = {k: ax.transData.transform((c[k]["r0"]["median"], c[k]["W0"]["median"])) * to_pt for k in NAMED}
    groups = name_groups(pts)
    hidden = {k for g in groups for k in g[1:]}
    for base, head in ARROWS:              # the notice layer added: base -> transplant (transplant_arrow)
        transplant_arrow(ax, c, base, head)
    for key in C_ORDER:
        if key in hidden:
            continue
        e = c[key]
        ln = style.scatter_policy(ax, key, [e["r0"]["median"]], [e["W0"]["median"]])
        g = next((g for g in groups if g[0] == key), None)
        if g is not None and len(g) > 1:
            ln._sublet_policies, ln._sublet_role = list(g), "shared_marker"
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_locator(MaxNLocator(nbins=4, steps=[1, 2, 2.5, 5, 10]))
        axis.set_major_formatter(style.PLAIN)
    thin_tick_labels(ax)                       # (c) is narrow: x tick labels at least common.TICK_GAP_PT apart
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.spines["right"].set_visible(True)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel(lab["c_x"])
    ax.set_ylabel(lab["c_y"])
    # the names: a column left of the data area, stacked as close to their points' heights as they fit; names whose
    # points coincide (within COINCIDE_PT) share one name, wrapped to the column's width, and one leader
    x0_ax, y0_ax, w_ax, h_ax = (v * style.BP_PER_IN for v in style.axes_rect_in(ax))
    lines = {g[0]: (lay["c_name_lines"][g[0]] if len(g) == 1 else group_lines(fig, [c["names"][k] for k in g],
                                                                               float(lay["c_names_in"]) + 1e-6))
             for g in groups}
    at = {g[0]: pts[g[0]] for g in groups}                        # the drawn marker's point
    heights = [len(lines[g[0]]) * LINE_STEP_PT for g in groups]
    centers = stack_labels([at[g[0]][1] for g in groups], heights, gap=1.0, bottom=y0_ax, top=y0_ax + h_ax)
    x_text = x0_ax - LEADER_RUN_PT - NAME_GAP_PT                 # the names' right end (pt)
    color = style.policy("sublet_v2").label_color
    for g, yc in zip(groups, centers):
        tx, ty = ax.transData.inverted().transform((x_text / to_pt, yc / to_pt))
        t = ax.text(tx, ty, "\n".join(lines[g[0]]), ha="right", va="center", fontsize=style.TICK_PT, color=color,
                    linespacing=1.2, clip_on=False)
        t._sublet_role = "direct_label"
        t._sublet_policy, t._sublet_policies = g[0], list(g)
        px, py = at[g[0]]
        half = 0.5 * (len(lines[g[0]]) - 1) * LINE_STEP_PT        # the leader leaves at the line nearest its point
        start = np.array([x_text + NAME_GAP_PT, min(max(py, yc - half), yc + half)])
        d = np.array([px, py]) - start
        dist = float(np.hypot(*d))
        rad = max(_marker_radius_pt(k) for k in g)
        end = start + d * max(0.0, (dist - rad - LEADER_END_PT) / dist) if dist > 0 else start
        (ln,) = ax.plot(*ax.transData.inverted().transform(np.array([start, end]) / to_pt).T, color=color,
                        linewidth=LEADER_PT, clip_on=False, zorder=style.Z_REFERENCE, label="_nolegend_")
        ln._sublet_role = "leader"
    label_sublet(ax, c)


def transplant_arrow(ax, c: Mapping, base: str, head: str) -> None:
    """(c): the notice layer added to `base`, an arrow from its marker to the transplant's point `head`, which a small
    copy of the base's marker marks (GHOST_PT, the base's registry marker, fill and color; C62 review: a bare head
    pointed past its point at the next policy's marker and read as naming it). The transplants' own registry markers
    are not drawn (as before): the open diamond of Greedy + notice layer is (b)'s lagged margin's. Shaft and head
    ARROW_PT wide in a tint of the base's color (ARROW_TINT), under the markers, so that the markers they pass, edged in
    the full color, read on top (C62 review: in the base's label color the shaft merged with the edges of Greedy,
    back-off's and RetroRenting-style's markers)."""
    p = style.policy(base)
    p0 = (c[base]["r0"]["median"], c[base]["W0"]["median"])
    p1 = (c[head]["r0"]["median"], c[head]["W0"]["median"])
    ghost = ax.plot([p1[0]], [p1[1]], linestyle="none", marker=p.marker, markersize=GHOST_PT,
                    markeredgewidth=GHOST_EDGE_PT, markeredgecolor=p.edgecolor or p.color,
                    markerfacecolor="white" if p.fill == "open" else p.color, zorder=style.Z_DATA - 0.05,
                    label="_nolegend_")[0]
    ghost._sublet_role, ghost._sublet_policy, ghost._sublet_base = "transplant_end", head, base
    tint = tuple(1.0 - ARROW_TINT * (1.0 - v) for v in to_rgb(p.color))      # the base's color toward white
    arr = style.arrow(ax, p0, p1, color=tint, linewidth=ARROW_PT, shrinkA=_marker_radius_pt(base) + 0.4,
                      shrinkB=0.5 * (GHOST_PT + GHOST_EDGE_PT) + GHOST_GAP_PT, arrowstyle=ARROW_STYLE)
    arr.set_zorder(style.Z_DATA - 0.1)      # under the markers (C62: it ran over Greedy, back-off's marker)
    arr._sublet_role = "transplant_arrow"
    arr._sublet_policy = head


def side_anchor(side: str, x0: float, y0: float, w: float, h: float) -> np.ndarray:
    """The middle of the edge of the box (x0, y0, w, h) that faces the point it names from `side` (pt)."""
    return np.array({"right": (x0, y0 + 0.5 * h), "left": (x0 + w, y0 + 0.5 * h), "above": (x0 + 0.5 * w, y0),
                     "below": (x0 + 0.5 * w, y0 + h)}[side])


def label_sublet(ax, c: Mapping):
    """(c): Sublet's name beside its point (C62), in its label color with a white halo. Its box lies SUBLET_GAP_PT off
    the marker's edge on the first side of SUBLET_SIDES (right, left, above, below) that has a place for it, centered on
    the point across that side, or moved by the least distance (SUBLET_DY_PT steps, up to SUBLET_DY_MAX_PT across and
    SUBLET_DX_MAX_PT away from the point): a place that comes no closer than common.KEY_PAD_PT to anything drawn in (c)
    (common's occupancy grid: markers, arrows, leaders, the reference line) and whose edge facing the point
    (side_anchor) is at least SUBLET_OWN_PT nearer to Sublet's point than to any other point or arrow head of (c), so
    that it names Sublet only (on the confirmation: right of the point, level with it). Where no side has such a place
    (the reduced fixture, where CoCaR-style's marker touches Sublet's), the free place nearest to the point and
    SUBLET_OWN_PT nearer to it than to any other (common.free_spot), or, where there is none, the free place nearest to
    the point, joined to the marker by a leader; StyleError where no place is free (the caption draft names Sublet in
    (c))."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    to_pt = 72.0 / fig.dpi
    pt_of = lambda k: ax.transData.transform((c[k]["r0"]["median"], c[k]["W0"]["median"])) * to_pt  # noqa: E731
    px, py = pt_of("sublet_v2")
    others = np.array([pt_of(k) for k in C_ORDER if k != "sublet_v2"] + [pt_of(t) for _, t in ARROWS])
    t = ax.text(0.0, 0.0, style.POLICIES["sublet_v2"].label, ha="left", va="bottom", fontsize=style.TICK_PT,
                color=style.policy("sublet_v2").label_color, zorder=style.Z_THEORY_LABEL)
    bb = t.get_window_extent(r)
    w, h = bb.width * to_pt, bb.height * to_pt
    taken, gx0, gy0 = _occupancy(ax, skip=(t,))
    res = GRID_RES_PT
    off = _marker_radius_pt("sublet_v2") + SUBLET_GAP_PT
    n_dy, n_dx = int(round(SUBLET_DY_MAX_PT / SUBLET_DY_PT)), int(round(SUBLET_DX_MAX_PT / SUBLET_DY_PT))
    steps = sorted(((k * SUBLET_DY_PT, sg * j * SUBLET_DY_PT) for k in range(n_dx + 1) for j in range(n_dy + 1)
                    for sg in ((1.0, -1.0) if j else (1.0,))), key=lambda v: (math.hypot(*v), -v[1]))
    corner = {"right": lambda a, b: (px + off + a, py - 0.5 * h + b), "left": lambda a, b: (px - off - a - w,
                                                                                             py - 0.5 * h + b),
              "above": lambda a, b: (px - 0.5 * w + b, py + off + a), "below": lambda a, b: (px - 0.5 * w + b,
                                                                                            py - off - a - h)}
    for side in SUBLET_SIDES:
        for a, b in steps:                  # away from the point, across its side: the nearest place first
            x0, y0 = corner[side](a, b)
            i0, i1 = int(math.floor((x0 - gx0) / res)), int(math.ceil((x0 + w - gx0) / res))
            j0, j1 = int(math.floor((y0 - gy0) / res)), int(math.ceil((y0 + h - gy0) / res))
            if i0 < 0 or j0 < 0 or i1 > taken.shape[1] or j1 > taken.shape[0] or taken[j0:j1, i0:i1].any():
                continue
            ref = side_anchor(side, x0, y0, w, h)
            if len(others) and math.hypot(px - ref[0], py - ref[1]) + SUBLET_OWN_PT > \
                    float(np.hypot(*(others - ref).T).min()):
                continue
            t.set_position(tuple(ax.transData.inverted().transform((x0 / to_pt, y0 / to_pt))))
            t.set_path_effects([patheffects.withStroke(linewidth=style.LABEL_HALO_PT, foreground="white")])
            t._sublet_role, t._sublet_policy, t._sublet_side = "point_label", "sublet_v2", side
            return t
    # no place beside the point: the free place nearest to it, SUBLET_OWN_PT nearer to it than to any other point where
    # there is one (common.free_spot), joined to the marker by a leader, which names it where another marker touches it
    spot = free_spot(ax, w, h, np.array([[px, py]]), others=others, margin_pt=SUBLET_OWN_PT, skip=(t,)) or \
        free_spot(ax, w, h, np.array([[px, py]]), skip=(t,))
    if spot is None:
        raise style.StyleError(f"{NAME} (c): no free place for Sublet's name")
    x0, y0 = spot
    t.set_position(tuple(ax.transData.inverted().transform((x0 / to_pt, y0 / to_pt))))
    t.set_path_effects([patheffects.withStroke(linewidth=style.LABEL_HALO_PT, foreground="white")])
    t._sublet_role, t._sublet_policy, t._sublet_side = "point_label", "sublet_v2", "leader"
    start = np.array([min(max(px, x0), x0 + w), min(max(py, y0), y0 + h)])       # the box's point nearest the marker
    d = np.array([px, py]) - start
    dist = float(np.hypot(*d))
    end = start + d * max(0.0, (dist - _marker_radius_pt("sublet_v2") - LEADER_END_PT) / dist) if dist > 0 else start
    (ln,) = ax.plot(*ax.transData.inverted().transform(np.array([start, end]) / to_pt).T,
                    color=style.policy("sublet_v2").label_color, linewidth=LEADER_PT, zorder=style.Z_REFERENCE,
                    label="_nolegend_")
    ln._sublet_role = "point_leader"
    t._sublet_leader = ln
    return t


def group_lines(fig, names: Sequence[str], max_in: float) -> list[str]:
    """The lines of one shared name (names joined by NAME_JOIN): each name wrapped on lines of its own (C62; as built
    at 9 pt the joined text was wrapped as one, which set the end of one name and the start of the next on one line,
    "rule; no site")."""
    sep = NAME_JOIN.rstrip()
    return [ln for i, n in enumerate(names) for ln in wrap(fig, n + (sep if i < len(names) - 1 else ""), max_in)]


def name_groups(pts: Mapping[str, Any]) -> list[tuple]:
    """NAMED in groups of keys whose points (pt) lie within COINCIDE_PT of the group's first point, in NAMED's order
    of each group's first key; a key joins the first group it is close to."""
    groups: list[list] = []
    for k in NAMED:
        for g in groups:
            if float(np.hypot(*(np.asarray(pts[k]) - np.asarray(pts[g[0]])))) <= COINCIDE_PT:
                g.append(k)
                break
        else:
            groups.append([k])
    return [tuple(g) for g in groups]


# ---------------------------------------------------------------------------------------------------------------
def draw_keys(fig, lab: Mapping, lay: Mapping) -> dict:
    """The keys of (b)'s sub-panels and of (c) at the layout's corners (layout's keys; no shared legend row, C19)."""
    out = {}
    for name, k in lay["keys"].items():
        leg = make_key(fig, key_entries(lab, name, k.get("lines")), k["loc"], k["x_in"], k["y_in"])
        leg._sublet_role = f"key:{name}"
        out[name] = leg
    return out


def check_keys(fig, keys: Mapping, panels: Mapping) -> None:
    """Each key clear of every axes (it covers no data) and of the other keys, within the page, and within its
    panel's slot across: (b)'s keys between (b)'s slot's left edge and (c)'s slot, (c)'s key within (c)'s slot
    (StyleError)."""
    r = fig.canvas.get_renderer()
    W = float(fig.get_size_inches()[0]) * fig.dpi
    boxes = {n: leg.get_window_extent(r) for n, leg in keys.items()}
    axes = [("a", panels["a"])] + [("b", ax) for ax in panels["b"]] + [("c", panels["c"])]
    slot = {p: [ax for n, ax in axes if n == p][0]._sublet_slot_left_in * fig.dpi for p in ("b", "c")}
    tol = 0.5 * fig.dpi / 72.0
    problems = []
    for n, bb in boxes.items():
        for p, ax in axes:
            ab = ax.get_window_extent(r)
            if min(bb.x1, ab.x1) - max(bb.x0, ab.x0) > tol and min(bb.y1, ab.y1) - max(bb.y0, ab.y0) > tol:
                problems.append(f"key {n} covers panel ({p})")
        for m, ob in boxes.items():
            if m < n and min(bb.x1, ob.x1) - max(bb.x0, ob.x0) > tol and \
                    min(bb.y1, ob.y1) - max(bb.y0, ob.y0) > tol:
                problems.append(f"keys {m} and {n} overlap")
        lo, hi = (slot["c"], W - style.MARGIN_RIGHT * fig.dpi) if n == "c" else (slot["b"], slot["c"])
        if bb.x0 < lo - tol or bb.x1 > hi + tol:
            problems.append(f"key {n} leaves its panel's slot ({bb.x0 / fig.dpi:.3f}-{bb.x1 / fig.dpi:.3f} in)")
        if bb.y1 > fig.get_size_inches()[1] * fig.dpi + tol:
            problems.append(f"key {n} reaches above the page")
    if problems:
        raise style.StyleError(f"{NAME}: " + "; ".join(problems))


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    lay = data["layout"]
    fig = style.new_figure(NAME)
    H = float(fig.get_size_inches()[1])
    ax_a, ax_b, ax_c = style.panel_row(fig, lay["axes_in"], left=lay["left_in"], right=lay["right_in"],
                                       top=H - float(lay["a_top_in"]))
    b_axes = split_b(fig, ax_b, lay["b_rects_in"])
    place_axes(ax_c, lay["c_rect_in"])
    ax_c._sublet_slot_left_in = float(lay["c_slot_in"])        # after the gutter (layout): (c)'s letter, key and names
    keys = draw_keys(fig, lab, lay)
    draw_a(ax_a, data["a"], lab, lay)
    draw_b(b_axes, data["b"], lab)
    draw_c(ax_c, data["c"], lab, lay)
    r = fig.canvas.get_renderer()
    for ax, name in zip(b_axes, (n for n, _ in data["b"]["subpanels"])):    # each sub-panel's key above it
        clear_top_tick_label(ax, keys[name].get_window_extent(r))
    align_ylabels_x(b_axes)                     # (b)'s two y labels at one x, then on one baseline (C62 review)
    align_baselines([ax.yaxis.label for ax in b_axes])
    for t in style.panel_letters([ax_a, b_axes[0], ax_c]):       # on one line, above (a) and the keys
        t.set_y((float(lay["letters_in"]) + LETTER_RISE_PT / style.BP_PER_IN) / H)
    fig._sublet_panels = {"a": ax_a, "b": list(b_axes), "c": ax_c}     # the panels by letter (tests)
    fig._sublet_keys = keys
    check_keys(fig, keys, fig._sublet_panels)
    return fig


def _guard_reduced(data: Mapping) -> None:
    """Data from a reduced (smoke) run is never written into paper/figures/ or code/sim/out/figs/ (review of W-G2:
    a reduced extract there would end the rebuild entry's pending state)."""
    if (data.get("meta") or {}).get("reduced") and not (os.environ.get(style.ENV_PDF_DIR)
                                                         and os.environ.get(style.ENV_OUT_DIR)):
        raise SystemExit(f"[{NAME}] the inputs are from a reduced run (meta.reduced): set {style.ENV_PDF_DIR} (and "
                         f"{style.ENV_OUT_DIR}) to scratch folders; nothing is written into paper/figures/ or "
                         f"code/sim/out/figs/")


def main(argv: Sequence[str] | None = None) -> dict:
    def build_checked(inp: Inputs) -> dict:
        data = build(inp)
        _guard_reduced(data)
        return data

    def draw_checked(data: Mapping) -> Any:
        _guard_reduced(data)
        return draw(data)

    try:
        return cli(NAME, build_checked, draw_checked, argv, doc=__doc__)
    except MissingInput as err:
        print(err.code, file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main(sys.argv[1:])
