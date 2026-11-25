"""Fig. 1 v3, the paper's Fig. 1 since MS7: the lease, the platform's control plane and one slot of Algorithm 1
(design/ms7/w_spec.md §2.2, items 57-76, and §4, unit W-G1; change C58), restyled for C62's type scale (7-pt text,
7.97-pt bold letters; 2026-11-24). A schematic at two-column width (W2, the registered height of
style.FIGURES["fig1v3"]); it reads no file and draws no data. It replaces fig1v2 (figs/fig1_v2.py) in the manuscript;
fig1v2 and the frozen fig1 stay registered and rebuild from their extracts.

Layout. Two rows. The top row holds (a) at the width A_WIDTH and (b) in the rest of the row; the bottom row holds (c)
across the full width. The three panels are drawn in inches on axes that are switched off (x from the axes' left edge,
y from their bottom edge), so that the 7-pt text rows are spaced in inches; each panel's first text row sits on the
baseline of its bold panel letter (style.panel_letters), and (a) and (c) start at one left edge. The rows (rows())
have minimum gaps that hold 7-pt text; the registered height's slack over their sum goes to three gaps, (b)'s arrows,
the space between the two rows and (c)'s "passes" arrows (STRETCH), and (a)'s rows spread so that (a)'s last text ends
on the bottom edge of (b)'s data plane: the top row ends on one line at any height from MIN_HEIGHT_IN up. Below (c),
BOTTOM_PAD keeps about 6 pt between the ink and the page's bottom, as Figs. 2-4 leave under their x labels, so that the
four captions sit at one distance from their figures' ink.

(a) The lease of contract k, in fig1_v2's labels (contract k's subscripts) with the cold reaction labeled "cold" (the
    model's word, Section III: "falls back and re-buys later (cold)"): purchase s, s + tau_k, the announcement r, the
    end of the guaranteed window s + D_k and the end r + H_k of the lease (the lease drawn as a dark bar on the time
    axis), the brackets tau_k, H_k and T^dr, the shaded guaranteed window D_k = tau_k + H_k labeled at its top, and
    the two reactions on two rows in Sublet's color, each of load time lambda: a replacement pre-warmed by
    r + H_k - lambda (dashed), which is warm at r + H_k, and one re-bought cold after r + H_k (solid). A dotted grey
    guide drops from the mark r + H_k through both rows, so that the pre-warm ends and the cold re-buy starts on it.
    (As built at 9 pt, (a) was fig1_guard.draw_timeline, fig1_v2's panel, with both reactions on one row, apart at
    r + H_k; C62 draws it here, at 7-pt spacing.)
(b) The platform's control plane. Top: the platform, shaded from below its components up to the letter row, with a
    light 0.4-pt outline, and labeled on the letter's baseline (as (a)'s guaranteed window), with its components:
    critical-ratio renting (the inner policy) and Algorithm 1 (the guard) in Sublet's color, the list going from the
    first to the second, and the safe expert (dark grey), whose cost C_S(t) goes to Algorithm 1; the labels "list" and
    C_S(t) print on one baseline. Bottom: the data plane, the borrowers, whose requests go to fallback capacity (left)
    or to the replicas at the lender sites (right). Between them two pairs of arrows that end on, and start from, the
    platform's outline (not a component; the right pair lies under the safe expert): up, the inputs (the borrowers'
    demand; the lenders' menus and notices), dark grey; down, the platform's decisions in Sublet's color (routing per
    interval, to the borrowers' requests; contracts, replicas and reactions, to the lender sites). The labels of a pair
    sit left of its arrows, the input's one line above the decision's, the two lines' ink centered in the span.
(c) One slot of Algorithm 1 at gamma = 1 (Sublet's default and Theorem 11's), as Algorithm 1 states its candidate ladder
    and test. Its first row, on the letter's baseline as printed, states the test, "list Y passes if a_hat_Y + R_Y <=
    C_S(t) + B(t)", with gamma written out (fig1_guard.threshold_label's rule: Liberation Sans sets the glyph gamma like
    an italic y; figure plan §1, Fig. 1(b)), its text aligned with the first box's. Below it the ladder in its order,
    the inner list A_E(t) and the trimmed lists P1 (fewer purchases: the first n' of them), P0 (no purchase) and K0
    (release every lease), each joined to the next by a grey arrow ("fails", under the first); from each a blue arrow
    ("passes", beside the first) to the bar "execute the first list that passes; next slot" (Sublet's color, light
    fill), which ends EXEC_GAP left of the abort box so that every blue arrow lands on its straight top edge; from the
    last a grey elbow to "abort: follow the safe expert" (grey fill). The ladder's arrows and the elbow's horizontal run
    are of one length.

Every drawn text is in the extract code/sim/out/figs/fig1v3.json (labels), with gamma and labels.caption, a caption
draft of at most CAPTION_LINES lines of about CAPTION_LINE_CHARS characters (design/figure_plan.md §5, "Captions": at
about 140 characters per line of a double-column caption, 5 lines hold about 700). No design ID is drawn, and not the
name Sublet (the caption names it); the policy names are the paper's ("critical-ratio renting", "safe expert",
"Algorithm 1"), and P1, P0 and K0 are Algorithm 1's names of its trimmed lists. Run from code/sim:
``python -m figs.fig1_v3 [--from-extract [JSON]]`` (figs.common.cli); the build reads no file, so its sources are empty.
"""
from __future__ import annotations

import math
import sys
from typing import Mapping

from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.textpath import TextPath

from figs import style
from figs.common import cli, text_width_in
from figs.fig1_guard import _pdf_math_raise_in
from figs.fig1_v2 import LABELS_A as V2_LABELS_A, printed_chars

NAME = "fig1v3"
KEY = "sublet_v2"                # the registry key whose color the figure draws (FIGURE_POLICIES["fig1v3"])
GAMMA = 1.0                      # (c)'s test is drawn at Sublet's gamma (Algorithm 1's default; Theorem 11)

# Horizontal layout (inches; not in §5). (a) and (c) start LEFT from the page's left edge, right of their letters (a
# bold 7.97-pt "(a)" is 0.135 in wide); (b)'s letter sits in its left reserve B_LEFT. A_WIDTH is (a)'s axes width: its
# time axis ends at the axes' right edge, 0.05 in after its last text ("cold") and B_LEFT left of (b)'s shading.
LEFT = 0.16
A_WIDTH = 2.80
B_LEFT = 0.22
TOP = 0.135                      # page top to the top row's axes; the letters' baseline is 1.2 pt above it, and the
#                                  shadings' tops (SHADE_UP above it) 1 pt below the page's top
LETTER_RISE = 1.2 / style.BP_PER_IN   # style.panel_letters: a letter's baseline above its axes' top

# Boxes and strokes
BOX_H = 0.16                     # a box of one 7-pt text line: its capital (0.067 in) 0.047 in from each edge
PAD_X = 0.07                     # a box's text to its left and right edges
ROUND_IN = 0.025                 # rounded corners of the boxes and of the platform's shading
EDGE_PT = 0.6                    # box edges (style.AXES_PT)
ARROW_PT = 0.6                   # arrows and (a)'s time axis
ARROW = "-|>,head_length=0.45,head_width=0.22"   # style.arrow's head, at its scale (the 7-pt rc font size)
ARROW_SCALE = style.TICK_PT
INK = "#4D4D4D"                  # boxes and arrows of what is not Sublet's (the registry's reference grey)
SUBLET_FILL = "#E5F0F7"          # (c)'s execute bar: Sublet's blue at about 10% on white
PLATFORM_EDGE = "#A6A6A6"        # (b): the platform's light outline, on which the inputs end and the decisions start
PLATFORM_EDGE_PT = 0.4
INSET = 0.06                     # a shading's label and (b)'s components from the shading's left (and right) edge
PAIR_DX = 0.11                   # (b): an input arrow to its decision arrow
LABEL_DX = 0.05                  # (b): an arrow pair to its labels; (c): an arrow to its label
PAIR_LEAD = 1.2 * style.TICK_PT / style.BP_PER_IN   # (b): a pair's two labels, one line apart (1.2 x 7 pt)
ARROW_LABEL_UP = 0.03            # (b): the arrow row's labels ("list", C_S(t)): their layout bottom above the arrow
EXEC_GAP = 0.12                  # (c): the execute bar's right end to the abort box

# Vertical layout (inches). Minimum gaps for 7-pt text; rows() adds the registered height's slack over their sum to
# the gaps in STRETCH, in those shares. The top row's depths are measured down from its letters' baseline.
SHADE_UP = 0.105                 # the shadings' tops above the letters' baseline (0.03 in above the ascenders)
COMP_DROP = 0.06                 # (b): the letters' baseline to the components' top
SHADE_PAD = 0.055                # (b): the components' bottom to the platform shading's bottom
SPAN_MIN = 0.29                  # (b): the shading's bottom to the data plane's top (a pair's two labels, PAIR_LEAD
#                                  apart, with 0.04 in above and below their ink, and the arrows)
ROW_GAP_MIN = 0.19               # the data plane's bottom to (c)'s letter baseline (0.11 in above the letter)
LADDER_DROP = 0.08               # (c): the letter baseline to the ladder's top
PASS_MIN = 0.15                  # (c): the ladder's bottom to the execute bar's top (the label "passes", 0.04 in
#                                  clear of each)
BOTTOM_PAD = 0.09                # (c): the execute bar's bottom to the page's bottom: about 6 pt from the ink to the
#                                  edge, as Figs. 2-4 leave under their x labels, so that the captions sit alike
STRETCH = {"span": 0.45, "gap": 0.30, "pass": 0.25}
# (a), down from the letters' baseline: the time axis, then the first reaction row, then the second; the second
# row's lambda sits on the top row's bottom line (rows()["top_depth"]). Minimum gaps; the slack shares A_STRETCH.
A_AXIS_MIN = 0.25                # the window label's baseline to the time axis (the tau_k and H_k brackets between)
A_ROW1_MIN = 0.235               # the time axis to the pre-warm row (the marks' labels between)
A_PITCH_MIN = 0.13               # the pre-warm row to the cold row (the pre-warm's lambda between)
A_STRETCH = (0.4, 0.3, 0.3)
LAM_RISE = 0.10                  # (a): a reaction row above the baseline of its lambda
MARK_DROP = 0.125                # (a): the time axis to the baseline of the marks' labels
MARK_TICK = 0.035                # (a): a mark's half height; a reaction's end tick's half height
BRACKET_UP = 0.08                # (a): the time axis to the tau_k and H_k brackets
BRACKET_STEP = 0.09              # (a): the H_k bracket to the T^dr bracket above it
# (a)'s timeline in inches from the axes' left edge: s, tau_k, r, H_k, T^dr; the pre-warm starts LAM_CLEAR right of
# the mark of s + D_k, so lambda = (r + H_k) - (s + D_k) - LAM_CLEAR (it reads as started after the window's end)
T_S, T_TAU, T_R, T_H, T_DR = 0.08, 0.42, 0.90, 1.33, 0.25
LAM_CLEAR = 0.10
MIN_HEIGHT_IN = 1.70             # rows() refuses a smaller height (the minimum gaps need 1.673 in)
CAPTION_LINES = 5                # figure plan §5, "Captions": at most 5 lines for a double-column figure
CAPTION_LINE_CHARS = 140         # about this many characters per line of an 8-pt double-column caption (figure plan)

LABELS_A = {**V2_LABELS_A, "cold": "cold"}
LABELS_B = {"platform": "platform", "crr": "critical-ratio renting", "list": "list", "guard": "Algorithm 1",
            "cost": "$C_S(t)$", "safe": "safe expert", "fallback": "fallback capacity", "borrowers": "borrowers",
            "sites": "lender sites", "demand": "demand", "route": "routing per interval", "menus": "menus, notices",
            "decide": "contracts, replicas, reactions"}
LABELS_C = {"lists": [r"$A_E(t)$: inner list", "P1: fewer purchases", "P0: no purchase", "K0: release every lease"],
            "fails": "fails", "passes": "passes", "execute": "execute the first list that passes; next slot",
            "abort": "abort: follow the safe expert"}


def test_label(gamma: float) -> str:
    """(c)'s test with gamma written out: "C_S(t)+B(t)" at gamma = 1, else e.g. "1.5 C_S(t)+B(t)"; never the glyph
    gamma (fig1_guard.threshold_label's rule)."""
    rhs = "C_S(t)+B(t)" if gamma == 1.0 else f"{gamma:g}" + r"\,C_S(t)+B(t)"
    return r"list $Y$ passes if $\hat a_Y+R_Y\leq " + rhs + "$"


def caption(gamma: float) -> str:
    """The caption draft: (a) the contract's terms as the timeline draws them; (b) the control plane, naming Sublet; (c)
    the slot of Algorithm 1 with gamma and the two terms of its threshold."""
    return (r"(a)~Contract $k$: purchase $s$, announcement $r\ge s+\tau_k$, end $r+H_k$, guaranteed window "
            r"$D_k=\tau_k+H_k$, drain time $T^{\mathrm{dr}}$, and load time $\lambda$ of a replacement started by "
            r"$r+H_k-\lambda$ (pre-warm) or after $r+H_k$ (cold). (b)~The platform's control plane: Sublet, "
            r"critical-ratio renting inside Algorithm~1, reads demand, menus and notices and decides contracts, "
            r"replica placement, routing per interval and reactions to notices. "
            r"(c)~One slot of Algorithm~1 ($\gamma=" + f"{gamma:g}" + r"$; $C_S$: the safe expert's cost, $B$: the "
            r"allowance): the inner list or the first trimmed list that passes the test is executed, else Algorithm~1 "
            r"aborts to the safe expert.")


def collect(_inp=None) -> dict:
    """The extract: every drawn label, gamma and the caption draft (no input file)."""
    cap = caption(GAMMA)
    n = printed_chars(cap)
    out = {
        "gamma": GAMMA,
        "labels": {"a": dict(LABELS_A), "b": dict(LABELS_B), "c": {"test": test_label(GAMMA), **LABELS_C},
                   "caption": cap, "caption_printed_chars": n,
                   "caption_lines_est": math.ceil(n / CAPTION_LINE_CHARS)},
        "note": "a schematic: no data; every drawn text is in labels",
    }
    if out["labels"]["caption_lines_est"] > CAPTION_LINES:
        raise style.StyleError(f"{NAME}: the caption draft has about {n} printed characters, more than "
                               f"{CAPTION_LINES} lines of about {CAPTION_LINE_CHARS}")
    return out


# ---------------------------------------------------------------------------------------------------------------
def rows(height: float) -> dict:
    """The vertical layout at the figure height `height` (in): the top row's letters' baseline below the page's top
    (top_bl), the depth of the top row below it (top_depth: (b)'s data plane's bottom edge, on which (a)'s last row
    of text sits), (b)'s arrow span, the gap from the top row to (c)'s letter baseline, (c)'s "passes" gap and (c)'s
    letter baseline above the page's bottom (c_bl). The minimum gaps need need_in; StyleError below MIN_HEIGHT_IN."""
    top_bl = TOP - LETTER_RISE
    c_fixed = LADDER_DROP + 2 * BOX_H + BOTTOM_PAD
    need = top_bl + COMP_DROP + BOX_H + SHADE_PAD + SPAN_MIN + BOX_H + ROW_GAP_MIN + PASS_MIN + c_fixed
    if height < MIN_HEIGHT_IN - 1e-9 or height < need:
        raise style.StyleError(f"{NAME}: {height} in is below the height the rows need ({need:.3f} in, at least "
                               f"MIN_HEIGHT_IN = {MIN_HEIGHT_IN} in)")
    slack = height - need
    span = SPAN_MIN + STRETCH["span"] * slack
    gap = ROW_GAP_MIN + STRETCH["gap"] * slack
    pas = PASS_MIN + STRETCH["pass"] * slack
    top_depth = COMP_DROP + BOX_H + SHADE_PAD + span + BOX_H
    return {"top_bl": top_bl, "top_depth": top_depth, "span": span, "gap": gap, "pass": pas,
            "c_bl": c_fixed + pas, "need_in": need, "slack": slack}


def _canvas(ax) -> tuple[float, float]:
    """Axes switched off whose data units are inches from their bottom left corner; returns (width, height)."""
    _, _, w, h = style.axes_rect_in(ax)
    ax.set_xlim(0.0, w)
    ax.set_ylim(0.0, h)
    ax.axis("off")
    ax.set_xticks([])                    # axis("off") hides the tick labels but keeps them as texts
    ax.set_yticks([])
    return w, h


def _baseline(ax, letter) -> float:
    """The baseline of the panel letter `letter` in the axes' inches."""
    return letter.get_position()[1] * ax.figure.get_size_inches()[1] - style.axes_rect_in(ax)[1]


def _width(ax, text: str) -> float:
    """The width (in) of a box that holds `text` at 7 pt."""
    return text_width_in(ax.figure, text) + 2 * PAD_X


def _ink_in(text: str) -> tuple[float, float]:
    """The ink of the plain 7-pt text `text` (in) below and above its baseline (bottom <= 0 <= top), as its glyph
    outlines give it (TextPath; not the renderer's metrics, which round to whole pixels at the figure's 100 dpi)."""
    ext = TextPath((0.0, 0.0), text, size=style.TICK_PT, prop=FontProperties(family=style.FONT_FAMILY)).get_extents()
    return min(ext.y0, 0.0) / style.BP_PER_IN, max(ext.y1, 0.0) / style.BP_PER_IN


def _cap_in() -> float:
    """The cap height (in) of 7-pt text (the height of "H": 4.82 pt)."""
    return _ink_in("H")[1]


def _descent_in(ax) -> float:
    """The descent (in) of a plain 7-pt text line's layout (matplotlib's "lp"): where va="bottom" puts a plain label's
    baseline above the given y."""
    r = ax.figure.canvas.get_renderer()
    return r.get_text_width_height_descent("lp", FontProperties(size=style.TICK_PT), ismath=False)[2] / ax.figure.dpi


def _line(ax, xs, ys, color: str, lw: float, **kw):
    """A line in the axes' inches, never clipped (the axes are only a canvas)."""
    (ln,) = ax.plot(xs, ys, color=color, linewidth=lw, solid_capstyle="butt", clip_on=False, **kw)
    return ln


def _box(ax, x0: float, y0: float, w: float, text: str, *, edge: str = INK, face: str = "white", role: str = ""):
    """A rounded box of one text line, its text centered on it: on the baseline that centers a capital letter, so that
    the texts of one row share their baseline whether or not they hold mathtext, lowered by the amount the PDF backend
    raises a mathtext's glyphs (fig1_guard._pdf_math_raise_in)."""
    p = FancyBboxPatch((x0, y0), w, BOX_H, boxstyle=f"round,pad=0,rounding_size={ROUND_IN}", linewidth=EDGE_PT,
                       edgecolor=edge, facecolor=face, zorder=2, clip_on=False)
    ax.add_patch(p)
    y = y0 + (BOX_H - _cap_in()) / 2
    t = ax.text(x0 + w / 2, y, text, ha="center", va="baseline", fontsize=style.TICK_PT, color="black", zorder=4)
    t.set_y(y - _pdf_math_raise_in(text, t.get_fontproperties()))
    p._sublet_role = t._sublet_role = role
    return p, t


def _arrow(ax, p0, p1, color: str = INK, role: str = ""):
    """An arrow from p0 to p1 with style.arrow's head."""
    a = ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle=ARROW, color=color, linewidth=ARROW_PT,
                                                          shrinkA=0, shrinkB=0, mutation_scale=ARROW_SCALE),
                    zorder=3, annotation_clip=False)
    a._sublet_role = role
    return a


def _label(ax, x: float, y: float, text: str, *, color: str = "black", **kw):
    return ax.text(x, y, text, fontsize=style.TICK_PT, color=color, zorder=4, **kw)


def _mathtext(ax, x: float, y: float, text: str, **kw):
    """A label on the baseline y, lowered by the amount the PDF backend raises a mathtext's glyphs, so that labels of
    one row print on one baseline whether or not they hold mathtext."""
    t = _label(ax, x, y, text, va="baseline", **kw)
    t.set_y(y - _pdf_math_raise_in(text, t.get_fontproperties()))
    return t


def _bracket(ax, x0: float, x1: float, y: float, text: str):
    """A square bracket over [x0, x1] at height y, ends pointing down, its label centered above it."""
    _line(ax, [x0, x0, x1, x1], [y - 0.03, y, y, y - 0.03], "black", 0.6, zorder=3)
    t = _label(ax, 0.5 * (x0 + x1), y + 0.012, text, ha="center", va="bottom")
    t._sublet_role = "bracket"
    return t


def draw_lease(ax, lab: Mapping, letter, rw: Mapping) -> None:
    """Fig. 1(a): the lease of contract k on a time axis, its terms, and the two reactions to its notice."""
    w, _ = _canvas(ax)
    y_lbl = _baseline(ax, letter)
    c = style.policy(KEY).color
    extra = rw["top_depth"] - (A_AXIS_MIN + A_ROW1_MIN + A_PITCH_MIN + LAM_RISE)
    y_ax = y_lbl - A_AXIS_MIN - A_STRETCH[0] * extra
    y_r1 = y_ax - A_ROW1_MIN - A_STRETCH[1] * extra
    y_r2 = y_r1 - A_PITCH_MIN - A_STRETCH[2] * extra
    s, s_tau, r, r_h = T_S, T_S + T_TAU, T_R, T_R + T_H
    s_d = s_tau + T_H
    lam = r_h - s_d - LAM_CLEAR
    # the guaranteed window [s, s + D_k): shaded from the axis up to the letter row, labeled inside at the top
    win = Rectangle((s, y_ax), s_d - s, y_lbl + SHADE_UP - y_ax, facecolor=style.SHADE_GREY, edgecolor="none",
                    zorder=0.5, clip_on=False)
    win._sublet_role = "window"
    ax.add_patch(win)
    _mathtext(ax, s + INSET, y_lbl, lab["window"], ha="left")._sublet_role = "window"
    # the time axis, and the lease from purchase to its end on it
    _arrow(ax, (0.0, y_ax), (w, y_ax), color="black", role="time")
    _line(ax, [s, r_h], [y_ax, y_ax], INK, 3.0, zorder=2.2)._sublet_role = "lease"
    # the marks, the window's end s + D_k among them, their labels on one baseline
    for x, k in ((s, "s"), (s_tau, "s_tau"), (r, "r"), (s_d, "s_D"), (r_h, "r_H")):
        _line(ax, [x, x], [y_ax - MARK_TICK, y_ax + MARK_TICK], "black", 0.6, zorder=3)
        _mathtext(ax, x, y_ax - MARK_DROP, lab[k], ha="center")._sublet_role = "mark"
    # brackets above the axis: tau_k and H_k; the drain time at H_k's end, one step above
    _bracket(ax, s, s_tau, y_ax + BRACKET_UP, lab["tau"])
    _bracket(ax, r, r_h, y_ax + BRACKET_UP, lab["H"])
    _bracket(ax, r_h - T_DR, r_h, y_ax + BRACKET_UP + BRACKET_STEP, lab["T_dr"])
    # the reactions, one row each: a pre-warm that is warm at r + H_k, a cold re-buy that starts after it; a dotted
    # guide from below the mark's label through both rows
    y_guide = y_ax - MARK_DROP - 0.06
    _line(ax, [r_h, r_h], [y_guide, y_r2 - MARK_TICK], style.THEORY_GREY, 0.6, linestyle=":", zorder=1.5)
    for (x0, x1), y, ls, side, key in (((r_h - lam, r_h), y_r1, "--", "left", "prewarm"),
                                        ((r_h, r_h + lam), y_r2, "-", "right", "cold")):
        _line(ax, [x0, x1], [y, y], c, style.SUBLET_LINE_PT, linestyle=ls, zorder=3)._sublet_role = key
        for x in (x0, x1):
            _line(ax, [x, x], [y - MARK_TICK, y + MARK_TICK], c, 0.6, zorder=3)
        if side == "left":
            _label(ax, x0 - 0.04, y, lab[key], color=c, ha="right", va="center")._sublet_role = key
        else:
            _label(ax, x1 + 0.04, y, lab[key], color=c, ha="left", va="center")._sublet_role = key
        _mathtext(ax, 0.5 * (x0 + x1), y - LAM_RISE, lab["lam"], ha="center", color=c)._sublet_role = "lam"


def draw_control_plane(ax, lab: Mapping, letter, rw: Mapping) -> None:
    """Fig. 1(b): the platform with its components above the data plane, joined by the inputs and the decisions."""
    w, _ = _canvas(ax)
    y_lbl = _baseline(ax, letter)
    blue, blue_text = style.policy(KEY).color, style.policy(KEY).label_color
    # the platform: shaded from below its components up to the letter row, with a light outline (the inputs end on it
    # and the decisions start from it, not from the component above them), labeled on the letter's baseline
    yb = y_lbl - COMP_DROP - BOX_H
    f0 = yb - SHADE_PAD
    shade = FancyBboxPatch((0.0, f0), w, y_lbl + SHADE_UP - f0, boxstyle=f"round,pad=0,rounding_size={ROUND_IN}",
                           linewidth=PLATFORM_EDGE_PT, edgecolor=PLATFORM_EDGE, facecolor=style.SHADE_GREY, zorder=1,
                           clip_on=False)
    shade._sublet_role = "platform"
    ax.add_patch(shade)
    _label(ax, INSET, y_lbl, lab["platform"], ha="left", va="baseline")
    wc, wg, ws = (_width(ax, lab[k]) for k in ("crr", "guard", "safe"))
    gap = (w - 2 * INSET - wc - wg - ws) / 2
    xc = INSET
    xg = xc + wc + gap
    xs = xg + wg + gap
    ym = yb + BOX_H / 2
    _box(ax, xc, yb, wc, lab["crr"], edge=blue, role="inner")
    _box(ax, xg, yb, wg, lab["guard"], edge=blue, role="guard")
    _box(ax, xs, yb, ws, lab["safe"], role="safe")
    # the arrow row's two labels on one baseline: a plain label's layout bottom ARROW_LABEL_UP above the arrows (the
    # subscript and parentheses of C_S(t) then descend into that space instead of lifting its baseline)
    y_al = ym + ARROW_LABEL_UP + _descent_in(ax)
    _arrow(ax, (xc + wc, ym), (xg, ym), color=blue, role="list")
    _mathtext(ax, 0.5 * (xc + wc + xg), y_al, lab["list"], color=blue_text, ha="center")._sublet_role = "arrow_label"
    _arrow(ax, (xs, ym), (xg + wg, ym), role="cost")
    _mathtext(ax, 0.5 * (xg + wg + xs), y_al, lab["cost"], ha="center")._sublet_role = "arrow_label"
    # the data plane: fallback capacity <- borrowers -> lender sites; the borrowers at a fifth of the free stretch,
    # since the lender sites' labels, left of their arrows above that stretch, are the wider
    y_d = y_lbl - rw["top_depth"]
    wf, wbo, wl = (_width(ax, lab[k]) for k in ("fallback", "borrowers", "sites"))
    xf, xl = 0.0, w - wl
    xbo = xf + wf + 0.2 * (xl - xf - wf - wbo)
    yc = y_d + BOX_H / 2
    _box(ax, xf, y_d, wf, lab["fallback"], role="fallback")
    _box(ax, xbo, y_d, wbo, lab["borrowers"], role="borrowers")
    _box(ax, xl, y_d, wl, lab["sites"], role="sites")
    _arrow(ax, (xbo, yc), (xf + wf, yc), role="requests")
    _arrow(ax, (xbo + wbo, yc), (xl, yc), role="requests")
    # inputs up (grey) from the data plane to the platform's outline and decisions down (blue) from it, in pairs;
    # labels left of a pair, the input's one line (PAIR_LEAD) above the decision's, the two lines' ink centered in the
    # span (as much space above the inputs' ascenders as below the decisions' descenders)
    top, bot = f0, y_d + BOX_H
    ink_top = max(_ink_in(lab[k])[1] for k in ("demand", "menus"))
    ink_bottom = min(_ink_in(lab[k])[0] for k in ("route", "decide"))
    y_dn = bot + 0.5 * (rw["span"] - PAIR_LEAD - ink_top + ink_bottom) - ink_bottom
    y_up = y_dn + PAIR_LEAD
    for x_up, up, down in ((xbo + 0.16, lab["demand"], lab["route"]), (xl + wl - 0.22, lab["menus"], lab["decide"])):
        _arrow(ax, (x_up, bot), (x_up, top), role="input")
        _arrow(ax, (x_up + PAIR_DX, top), (x_up + PAIR_DX, bot), color=blue, role="decision")
        _label(ax, x_up - LABEL_DX, y_up, up, ha="right", va="baseline")._sublet_role = "input_label"
        _label(ax, x_up - LABEL_DX, y_dn, down, color=blue_text, ha="right", va="baseline")._sublet_role = \
            "decision_label"


def draw_slot(ax, lab: Mapping, letter, rw: Mapping) -> None:
    """Fig. 1(c): the test, the ladder of lists and the two outcomes of a slot."""
    w, _ = _canvas(ax)
    y_lbl = _baseline(ax, letter)
    blue, blue_text = style.policy(KEY).color, style.policy(KEY).label_color
    _mathtext(ax, INSET, y_lbl, lab["test"], ha="left")._sublet_role = "test"     # on the letter's baseline, as printed
    # the ladder's row, then the outcomes' row: the execute bar under the ladder, the abort box at the right
    y2 = y_lbl - LADDER_DROP - BOX_H
    y3 = y2 - rw["pass"] - BOX_H
    wa = _width(ax, lab["abort"])
    xa = w - wa
    elbow = xa + wa / 2                           # the abort arrow comes down at the abort box's middle
    bw = max(_width(ax, s) for s in lab["lists"])     # the ladder's boxes of one width, the widest list's
    gap = (elbow - len(lab["lists"]) * bw) / len(lab["lists"])   # its arrows and the elbow's run, of one length
    x, boxes = 0.0, []
    ym = y2 + BOX_H / 2
    for i, s in enumerate(lab["lists"]):
        _box(ax, x, y2, bw, s, edge=blue, role="candidate")
        boxes.append((x, bw))
        if i < len(lab["lists"]) - 1:
            _arrow(ax, (x + bw, ym), (x + bw + gap, ym), color=style.THEORY_GREY, role="fails")
            if i == 0:
                _label(ax, x + bw + gap / 2, ym - 0.025, lab["fails"], color=style.THEORY_LABEL_GREY, ha="center",
                       va="top")
        x += bw + gap
    x_last = boxes[-1][0] + boxes[-1][1]
    _box(ax, 0.0, y3, xa - EXEC_GAP, lab["execute"], edge=blue, face=SUBLET_FILL, role="execute")
    for i, (bx, _) in enumerate(boxes):
        _arrow(ax, (bx + bw / 2, y2), (bx + bw / 2, y3 + BOX_H), color=blue, role="passes")
        if i == 0:                                # its ink centered in the gap ("passes" has no ascender)
            lo, hi = _ink_in(lab["passes"])
            _label(ax, bx + bw / 2 + LABEL_DX, 0.5 * (y2 + y3 + BOX_H) - 0.5 * (lo + hi), lab["passes"],
                   color=blue_text, ha="left", va="baseline")
    _box(ax, xa, y3, wa, lab["abort"], face=style.SHADE_GREY, role="abort")
    _line(ax, [x_last, elbow], [ym, ym], style.THEORY_GREY, ARROW_PT, zorder=3)
    _arrow(ax, (elbow, ym), (elbow, y3 + BOX_H), color=style.THEORY_GREY, role="fails")


def draw(data: Mapping):
    lab = data["labels"]
    fig = style.new_figure(NAME)
    height = float(fig.get_size_inches()[1])
    rw = rows(height)
    avail = style.figure_spec(NAME).width_in - LEFT - B_LEFT - style.MARGIN_RIGHT
    top_bottom = height - rw["top_bl"] - rw["top_depth"]          # the top row's axes end on its bottom line
    a, b = style.panel_row(fig, (A_WIDTH, avail - A_WIDTH), left=[LEFT, B_LEFT], bottom=top_bottom, top=TOP)
    (c,) = style.panel_row(fig, (1,), left=[LEFT], bottom=0.0, top=height - rw["c_bl"] + LETTER_RISE)
    letters = style.panel_letters([a, b, c])
    draw_lease(a, lab["a"], letters[0], rw)
    draw_control_plane(b, lab["b"], letters[1], rw)
    draw_slot(c, lab["c"], letters[2], rw)
    return fig


def report(data: dict, rep: dict) -> None:
    print(f"[{NAME}] caption about {data['labels']['caption_lines_est']} lines "
          f"({data['labels']['caption_printed_chars']} characters); preview {rep['png']}")


def main(argv=None) -> dict:
    return cli(NAME, collect, draw, argv, after=report, doc=__doc__)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
