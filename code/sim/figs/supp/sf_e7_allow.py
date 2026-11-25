"""sf_e7_allow: E7(f), the allowance B0 of the one-way guard around the lagged BL5 (design/sim_spec_ms4.md §8.2,
§3.7(f), M36; plan §4, part S-F).

MS6 C47 (design/ms6_spec.md M2, M4): the swept policy, the summary's tag Sublet (MS4's name), is drawn as the registry
key bl5_g1, "Lagged RetroRenting + one-way guard" (Algorithm 1 without projection at its defaults, whose B0 the axis
sweeps), and the unguarded BL5 as bl5_lag; below, "Sublet" is that tag. The legend holds the two policies in two rows
of one column (panel_row(..., legend=2), legend_row(..., rows=2, ncol=1): with bl5_g1's label the three entries of
the row as built take 5.57 in against W1's 3.43 in), and Algorithm 1's default is named by a direct label next to
its open marker (default_label); (b)'s y label is in two lines, the axes now being shorter than it. Print check of the
gate (U46): that point is the one-way guard at Algorithm 1's original allowance (B0 auto, kappa 10; design/ms6_spec.md
M12), not Sublet's default min{W_k, LB'} of Algorithm 1 v2, so its label reads "Original allowance" (as relabeled,
"Algorithm 1 default") and labels.note names it so; it is labeled in each panel where it fits (as relabeled, in the
first only, and (b)'s open marker stood unlabeled).

C62 (2026-11-24: 7-pt text, 7.97-pt axis labels and letters): the two policies fit one legend row again (3.27
in at 7 pt against W1's 3.43 in; C47's two rows of one column were for the 9-pt labels), and (b)'s y label is one line
("Worst cost / all-fallback", 1.15 in at 7.97 pt, along axes now 1.49 in high), as (a)'s is; the panels take the
freed legend row and the second label line's reserve (LEGEND_ROWS, LABELS["b_y"]).

Sublet (A8 around BL5 with gamma = 1 and the constant allowance, kappa null) on the E7 week at alignment 1, against
its allowance B0 as a share of the instance's BL0a (log x, the sweep's shares 0.5-20%, e7/allow/summary.json cells
.<share>, §3.10):
(a) the week cost over BL0a under the trace lender (overflow accounting; cells.<share>.L-tr.cost_over_bl0a, the
    median over policy seeds 0-2 with its 95% bootstrap interval);
(b) W0, the worst cost over BL0a under the five stress modes (W0.<share>.value; note §5.5), y label "Worst cost /
    all-fallback" (W0 is named in the caption).
A share is drawn only where its cell's B0_usd is the share times meta.bl0a_usd (B0_TOL relative; the driver's rule,
M36, which check E7-6 tests): a cell whose B0 differs has its points set to null with a note and a warning.
In both, Algorithm 1's default (B0 'auto', one fresh replica per client, with kappa = 10) as an open marker at its
share meta.b0_auto_usd / meta.bl0a_usd (cells.auto.L-tr and W0.auto), the unguarded BL5 as a horizontal line in its
registry style with its marker (an open square) at both ends, BL5_END_PT inside the axes (bl5.L-tr in (a), bl5.W0 in
(b); as built, a marker-less line that in greyscale differed from the reference line only in shade and width), and
the level 1 (all-fallback) as a reference line. The x axis ends X_PAD below the smallest share drawn (the default's)
and X_PAD_RIGHT above the largest, so that BL5's right-end square clears Sublet's marker at the largest share (in (b)
1% below BL5's line).

Axes. x: ticks at the swept shares (as built, decades only, so that four of the six shares had no tick), labels
thinned (common.thin_tick_labels; the unlabeled ticks at minor length); labels.note states the grid and the default's
share. y (y_ticks): of the ladders of Y_LADDERS, then steps of Y_STEP times the top value's decade, the coarsest
evenly stepped one (constant difference or constant ratio) that has a tick at or below the lowest plotted value, at
most FLOOR_MAX below it, and Y_MIN_TICKS to Y_MAX_TICKS ticks from there to the highest value; else the coarsest such
ladder (as built, (a)'s only labels were 0.8 and 1, above its data at 0.683, and then 0.6, 0.7, 0.8, 1, which skipped
0.9: now 0.6, 0.7, 0.8, 0.9, 1; (b): 1, 1.1, 1.2). The y limits come from the data (fit_y): the lowest value's
markers and the lowest tick's label clear the x spine, and the highest value's markers and the highest tick's label
end just below the axes top, with no more room (as built, the top was the highest value times 1.15, and the spine ran
on to it: an empty third of (b)'s).
The legend is one row above both panels (style.legend_row with panel_row(..., legend=True), handles LEGEND_HANDLE
long so that the three entries fit W1), as in sf_e7_mu, and the panel letters sit on the axes tops below it (as
built, two rows in the panels' headroom ran under "(b)", which sat 3 pt above "RetroRenting-style" and read as its
heading; the spines are now 1.41 in tall, against 1.32 in as built). labels.note names the policies by their legend
names and reads its counts and parameters from the summary (the stress modes of W0's `expected`, gamma and kappa of
the cells); it states the identities the data show: where Sublet's median cost in (a) equals unguarded BL5's (to
SAME_TOL relative), at every B0 or at the shares listed (extract: `same_as_bl5`), and where (a)'s 95% intervals lie
within Sublet's markers as drawn (both ends at most the marker's outer radius from the median; build() draws the
figure to measure it, intervals_within_markers), at every share or at the shares listed (extract:
`ci_within_markers`; on the E7 outputs at every share, the intervals reaching at most 1.3 pt below the median). The
caption gives the kappa cap 10 sum_j C^min_j (meta.kappa10_cap_usd, in the extract).

C52 (design/ms7/plan.md §4, unit T1, glossary G5): Algorithm 1's original allowance min{B0, kappa B_on} is "the
per-LLM allowance" in the paper (Section VI), so the open marker's direct label reads "Per-LLM allowance" and
labels.note names it so (as built, "Original allowance" and "Algorithm 1's original allowance").

Run from code/sim: python -m figs.supp.sf_e7_allow [--from-extract [JSON]].
"""
from __future__ import annotations

import math
import sys
import warnings
from typing import Any, Mapping, Sequence

import matplotlib as mpl
import numpy as np
from matplotlib.ticker import NullLocator

from figs import style
from figs.common import (KEY_PAD_PT, LEADER_PT, LINE_STEP_PT, cli, finite, maybe, need, place_label, points_pt,
                         thin_tick_labels)
from figs.inputs import Inputs
from figs.supp.ms4_lib import agg_point, log_axis_over, runs_text

NAME = "sf_e7_allow"
ALLOW = "code/sim/out/e7/allow/summary.json"
KEYS = style.SUPP_POLICIES_MS4[NAME]          # bl5_g1, bl5_lag
# C47 (design/ms6_spec.md M2, M4): the swept policy (the summary's tag Sublet, the one-way guard around the lagged BL5)
# is drawn as bl5_g1, the configuration key of Algorithm 1's defaults, since the axis sweeps B0 with Algorithm 1's
# default (its original allowance, the open marker) as one of its points; the unguarded lagged BL5 (the summary's bl5)
# as bl5_lag
GUARD, BL5 = KEYS
MODE = "L-tr"
AUTO = "auto"
X_PAD = 1.4                                   # the x axis below the smallest share drawn (a factor)
X_PAD_RIGHT = 2.0                             # ... and above the largest (room for BL5's right-end square)
B0_TOL = 1e-9                                 # relative: a cell's B0_usd against share x BL0a (ms4_common.SHARE_TOL
#                                               is 1e-12 on the runs' own values; not in §8.2)
SAME_TOL = 1e-12                              # relative: Sublet's median equal to BL5's (labels.note)
LEGEND_HANDLE = 1.4                           # the legend row's handle length (em; rcParams 2.0): one row fits W1
LEGEND_ROWS = 1                               # C62: the two policies side by side (3.27 in at 7 pt). C47 (9 pt): 2,
#                                               one above the other (bl5_g1's label, 2.16 in at 9 pt, and the default's
#                                               entry took 5.57 in in one row against 3.43 in); the per-LLM allowance
#                                               (C52) is labeled directly (default_label)
DEFAULT_LINES = ("{d}", "{d0}\n{d1}")         # default_label's forms: one line, then broken at its last space
BL5_END_PT = 3.5                              # BL5's end markers this far inside the axes' left and right edges
Y_LADDERS = ((1.0, 2.0, 5.0), (1.0, 1.5, 2.0, 3.0, 5.0, 7.0),
             (1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0))
Y_STEP = 0.1                                  # the last resort: steps of 0.1 times the top value's decade
Y_MIN_TICKS = 3
Y_MAX_TICKS = 6
FLOOR_MAX = 1.25                              # the lowest tick at most this factor below the lowest value
LABEL_SPINE_PT = 0.5                          # a tick label ends this far inside the spine's ends
style.register_supplementary(NAME, "W1", 2.2)
# C62: (b)'s y label in one line (1.15 in at 7.97 pt along 1.49-in axes). C47 (9 pt): in two lines, since with the two
# legend rows the axes were 1.17 in high and the label in one line (1.45 in at 9 pt) reached the panel letter; draw()
# reserves the height of any further line on (b)'s left
LABELS = {"x": r"$B_0$ / all-fallback (%)", "a_y": "Cost / all-fallback", "b_y": "Worst cost / all-fallback",
          "default": "Per-LLM allowance",                    # C52 (T1 glossary G5; as built "Original allowance")
          "note": "{guard} (Algorithm 1 without projection around the lagged RetroRenting-style rule, gamma {gamma}, "
                  "kappa {kappa}) on the E7 "
                  "week at alignment {alignment}, B0 swept over {grid}% of {bl0a} (the x ticks); (a) trace lender, "
                  "medians over {seeds} with 95% bootstrap intervals{within}; (b) W0, the worst cost over {bl0a} "
                  "under the {n_modes} stress modes; open marker (both panels): the per-LLM allowance "
                  "min{{B0, kappa B_on}} (B0 auto, kappa {kappa_auto}; {default_pct}% of {bl0a}); line with its open "
                  "markers at its ends: "
                  "{lagged}, unguarded"
                  "{same}; overflow accounting",
          "within_all": ", which lie within the markers",
          "within_some": ", which lie within the markers at B0 = {shares}%",
          "same_all": "; in (a) the cost of {guard} equals that of {lagged} at every B0 (both {value})",
          "same_some": "; in (a) the cost of {guard} equals that of {lagged} at B0 = {shares}% (both {value})"}


def names() -> dict:
    """The policies of labels.note by their legend names (style.POLICIES; C47: bl5_g1's as "guard" and bl5_lag's as
    "lagged", the template names "sublet" and "bl5" as built); all-fallback in lower case, as in the y labels."""
    q = lambda k: f"'{style.POLICIES[k].label}'" if "," in style.POLICIES[k].label else style.POLICIES[k].label
    return {"guard": q(GUARD), "lagged": q(BL5),                 # a name with a comma in quotes (sf_e5.note_name)
            "bl0a": style.POLICIES["bl0a"].label.lower()}


def _and(items: Sequence[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def same_as_bl5(shares: Sequence[float], medians: Sequence, bl5) -> list[float]:
    """The shares (percent) at which Sublet's median in (a) equals unguarded BL5's (SAME_TOL relative)."""
    if bl5 is None:
        return []
    b = float(bl5)
    return [s for s, m in zip(shares, medians)
            if m is not None and abs(float(m) - b) <= SAME_TOL * max(abs(b), abs(float(m)))]


def same_text(same: Sequence[float], shares: Sequence[float], bl5) -> str:
    if not same:
        return ""
    value = f"{float(bl5):.3f}"
    drawn = [s for s in shares if s is not None]
    if len(same) == len(drawn):
        return LABELS["same_all"].format(value=value, **names())
    return LABELS["same_some"].format(shares=_and([f"{s:g}" for s in same]), value=value, **names())


def within_text(within: Sequence[float], with_ci: Sequence[float]) -> str:
    """labels.note's clause on (a)'s intervals inside the markers: every share with an interval, the shares listed,
    or '' where none."""
    if not within:
        return ""
    if len(within) == len(with_ci):
        return LABELS["within_all"]
    return LABELS["within_some"].format(shares=_and([f"{s:g}" for s in within]))


def _param(v) -> str:
    """A parameter for labels.note: a null kappa is the constant allowance (no kappa cap), never Python's None."""
    return "none" if v is None else f"{float(v):g}"


def one_value(vals: Sequence, what: str):
    """The single value of a parameter over the cells (gamma, kappa), for labels.note; StyleError where the cells
    differ (the note would state one value)."""
    vs = {None if v is None else float(v) for v in vals}
    if len(vs) != 1:
        raise style.StyleError(f"{NAME}: the cells differ in {what} ({sorted(vs, key=str)}); labels.note states one")
    return vs.pop()


def build(inp: Inputs) -> dict:
    al = inp.json(ALLOW)
    cells = need(al, "cells", what=ALLOW)
    bl0a = float(need(al, "meta", "bl0a_usd", what=ALLOW))
    auto_usd = float(need(al, "meta", "b0_auto_usd", what=ALLOW))
    shares = sorted((float(k), k) for k in cells if k != AUTO and not k.endswith("_note"))
    a = {"share_pct": [], "median": [], "ci_lo": [], "ci_hi": [], "n": [], "note": [], "B0_usd": []}
    b = {"share_pct": [], "value": [], "mode": [], "note": []}
    for s, k in shares:
        ent, note = maybe(cells, k, MODE)
        p = agg_point(ent, "cost_over_bl0a") if note is None else {"median": None, "ci_lo": None, "ci_hi": None,
                                                                    "n": 0, "note": note}
        b0 = ent.get("B0_usd") if isinstance(ent, Mapping) else None
        w, wn = maybe(al, "W0", k, "value")
        if b0 is not None and abs(float(b0) - s * bl0a) > B0_TOL * abs(float(b0)):
            bad = (f"cells.{k}.{MODE}.B0_usd {b0!r} is not {k} x meta.bl0a_usd {bl0a!r} (relative tolerance "
                   f"{B0_TOL:g}): not drawn at the share")
            warnings.warn(f"{NAME}: {bad}")
            p = {"median": None, "ci_lo": None, "ci_hi": None, "n": p["n"], "note": bad}
            w, wn = None, bad
        for f in ("median", "ci_lo", "ci_hi", "n", "note"):
            a[f].append(p[f])
        a["share_pct"].append(100.0 * s)
        a["B0_usd"].append(b0)
        b["share_pct"].append(100.0 * s)
        b["value"].append(w)
        b["mode"].append(maybe(al, "W0", k, "mode")[0])
        b["note"].append(wn)
    ent, note = maybe(cells, AUTO, MODE)
    pd = agg_point(ent, "cost_over_bl0a") if note is None else {"median": None, "ci_lo": None, "ci_hi": None,
                                                                "n": 0, "note": note}
    w_auto, w_note = maybe(al, "W0", AUTO, "value")
    default = {"share_pct": 100.0 * auto_usd / bl0a, "B0_usd": auto_usd, "a": pd, "b": {"value": w_auto,
                                                                                       "note": w_note}}
    bl5 = {"L-tr": maybe(al, "bl5", "L-tr")[0], "L-tr_note": maybe(al, "bl5", "L-tr")[1],
           "W0": maybe(al, "bl5", "W0")[0], "W0_note": maybe(al, "bl5", "W0")[1]}
    drawn = [s for s, m in zip(a["share_pct"], a["median"]) if m is not None]
    same = same_as_bl5(a["share_pct"], a["median"], bl5["L-tr"])
    swept = [cells[k][MODE] for _, k in shares if isinstance(maybe(cells, k, MODE)[0], Mapping)]
    modes = sorted({m for _, k in shares for m in (maybe(al, "W0", k, "expected")[0] or [])})
    fmt = {"alignment": need(al, "meta", "alignment", what=ALLOW), "grid": _and([f"{s:g}" for s in a["share_pct"]]),
           "default_pct": f"{default['share_pct']:.2g}", "same": same_text(same, drawn, bl5["L-tr"]),
           "seeds": runs_text(1, len(need(al, "meta", "grids", "policy_seeds", what=ALLOW))).split(" x ", 1)[1],
           "gamma": _param(one_value([e.get("gamma") for e in swept], "gamma")),
           "kappa": _param(one_value([e.get("kappa") for e in swept], "kappa")),
           "kappa_auto": _param(maybe(cells, AUTO, MODE, "kappa")[0]), "n_modes": len(modes), **names()}
    data = {"a": a, "b": b, "default": default, "bl5": bl5, "mode": MODE, "same_as_bl5": same,
            "meta": {"bl0a_usd": bl0a, "b0_auto_usd": auto_usd,
                     "kappa10_cap_usd": maybe(al, "meta", "kappa10_cap_usd")[0],
                     "git_revision": need(al, "meta", "git_revision", what=ALLOW),
                     "reduced": bool(al["meta"].get("reduced"))},
            "labels": {**LABELS, "note": None},
            "sources": list(inp.sources)}
    with_ci, within = intervals_within_markers(data)
    data["ci_within_markers"] = within
    data["labels"]["note"] = LABELS["note"].format(within=within_text(within, with_ci), **fmt)
    return data


def intervals_within_markers(data: Mapping) -> tuple[list[float], list[float]]:
    """(the shares of (a) with a drawn 95% interval, those whose interval lies within the guard's marker): the figure
    drawn from `data` (draw; its y axis follows from the values alone), both interval ends at most the marker's outer
    radius (half its size plus half its edge) from the median."""
    fig = draw(data)
    ax = fig.axes[0]
    (ln,) = [x for x in ax.lines if getattr(x, "_sublet_policy", "") == GUARD and x.get_linestyle() != "None"]
    rad = 0.5 * (ln.get_markersize() + ln.get_markeredgewidth())
    to_pt = style.BP_PER_IN / fig.dpi
    a = data["a"]
    with_ci, within = [], []
    for s, m, lo, hi in zip(a["share_pct"], a["median"], a["ci_lo"], a["ci_hi"]):
        if s is None or m is None or lo is None or hi is None or not hi > lo:
            continue
        y = [ax.transData.transform((s, v))[1] for v in (lo, m, hi)]
        with_ci.append(s)
        if max(y[2] - y[1], y[1] - y[0]) * to_pt <= rad:
            within.append(s)
    return with_ci, within


# ---------------------------------------------------------------------------------------------------------------
def x_axis(ax, xs: Sequence[float], shares: Sequence[float]) -> None:
    """Log x over [min(xs) / X_PAD, max(xs) * X_PAD_RIGHT] with ticks at the swept shares, labels thinned."""
    lo, hi = min(xs), max(xs)
    log_axis_over(ax, "x", lo, hi, pad=X_PAD, ticks=sorted(shares))
    ax.set_xlim(lo / X_PAD, hi * X_PAD_RIGHT)
    style.end_label_inside(ax)
    thin_tick_labels(ax)


def evenly_stepped(ticks: Sequence[float]) -> bool:
    """Ticks with a constant difference (0.6, 0.7, 0.8, 0.9, 1) or a constant ratio (0.1, 1, 10)."""
    t = np.asarray(ticks, dtype=float)
    if t.size < 3:
        return True
    d, r = np.diff(t), t[1:] / t[:-1]
    return bool(np.allclose(d, d[0], rtol=1e-6) or np.allclose(r, r[0], rtol=1e-6))


def y_ticks(lo: float, hi: float) -> list[float]:
    """The y ticks: the coarsest evenly stepped one (evenly_stepped) of the ladders of Y_LADDERS (mantissas per
    decade), then multiples of Y_STEP times the decade of `hi`, whose largest tick at or below `lo` is at most
    FLOOR_MAX below it and that has Y_MIN_TICKS to Y_MAX_TICKS ticks from that one up to `hi`; else the coarsest such
    ladder, evenly stepped or not; else the coarsest with that many ticks, its lowest further below `lo`; else the
    coarsest with at least Y_MIN_TICKS and its lowest within FLOOR_MAX; else the last one's ticks."""
    e0, e1 = math.floor(math.log10(lo)) - 1, math.ceil(math.log10(hi)) + 1
    step = Y_STEP * 10.0 ** math.floor(math.log10(hi))
    cands = [[m * 10.0 ** e for e in range(e0, e1 + 1) for m in lad] for lad in Y_LADDERS]
    cands.append([k * step for k in range(1, int(round(10.0 ** (e1 + 1) / step)) + 1)])
    ticks: list[float] = []
    found = []                                  # (ticks, lowest within FLOOR_MAX)
    for c in cands:
        c = sorted({round(v, 12) for v in c})
        below = [v for v in c if v <= lo * (1 + 1e-9)]
        if not below:
            continue
        ticks = [v for v in c if below[-1] <= v <= hi * (1 + 1e-9)]
        found.append((ticks, lo / below[-1] <= FLOOR_MAX))
    for rule in (lambda t, near: near and Y_MIN_TICKS <= len(t) <= Y_MAX_TICKS and evenly_stepped(t),
                 lambda t, near: near and Y_MIN_TICKS <= len(t) <= Y_MAX_TICKS,
                 lambda t, near: Y_MIN_TICKS <= len(t) <= Y_MAX_TICKS,
                 lambda t, near: near and len(t) >= Y_MIN_TICKS):
        for t, near in found:
            if rule(t, near):
                return t
    return found[-1][0] if found else ticks


def _label_extents(ax) -> tuple[float, float]:
    """(up, down): how far (pt) the y tick labels of `ax` reach above and below their ticks (the largest)."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    to_pt = style.BP_PER_IN / fig.dpi
    up, down = [0.5 * style.TICK_PT], [0.5 * style.TICK_PT]
    y0, y1 = ax.get_ylim()
    for tk in ax.yaxis._update_ticks():
        t = tk.get_loc()
        if not (y0 <= t <= y1) or not tk.label1.get_visible() or not tk.label1.get_text():
            continue
        bb = tk.label1.get_window_extent(r)
        yt = ax.transData.transform((0.0, t))[1]
        up.append((bb.y1 - yt) * to_pt)
        down.append((yt - bb.y0) * to_pt)
    return max(up), max(down)


def fit_y(ax, lo: float, hi: float) -> list[float]:
    """The y axis of a panel from its plotted values [lo, hi]: ticks y_ticks(lo, hi), no minor ticks; the limits
    such that the markers at `lo` clear the x spine as common.clear_floor has them, the lowest tick's label ends
    LABEL_SPINE_PT above the x spine, and the markers at `hi` (KEY_PAD_PT) and the highest tick's label
    (LABEL_SPINE_PT) end below the axes top, with no more room above. Returns the ticks."""
    ticks = y_ticks(lo, hi)
    style.log_axis(ax, "y", ticks=ticks)
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_ylim(min(ticks[0], lo) / 1.05, max(ticks[-1], hi) * 1.05)        # provisional, to measure the labels
    up, down = _label_extents(ax)
    h_pt = style.axes_rect_in(ax)[3] * style.BP_PER_IN
    rad = max([0.5 * (ln.get_markersize() + ln.get_markeredgewidth()) for ln in ax.lines
               if hasattr(ln, "_sublet_policy") and ln.get_marker() not in (None, "None", "none", "")], default=0.0)
    bottom = [(math.log(lo), rad + 0.5 * style.AXES_PT + KEY_PAD_PT), (math.log(ticks[0]), down + LABEL_SPINE_PT)]
    top = [(math.log(hi), rad + KEY_PAD_PT), (math.log(ticks[-1]), up + LABEL_SPINE_PT)]
    u, w = min(v for v, _ in bottom), max(v for v, _ in top)
    if w - u < 1e-9:                           # one value: a range to scale the margins on
        u, w = u - 0.05, w + 0.05
    for _ in range(100):                       # fixed point: the margins in pt on the log range they make
        span = w - u
        u, w = min(v - m / h_pt * span for v, m in bottom), max(v + m / h_pt * span for v, m in top)
    ax.set_ylim(math.exp(u), math.exp(w))
    return ticks


def draw_panel(ax, xs, y, lo, hi, default_x, default_y, bl5_y, ylabel: str) -> list[float]:
    """Sublet's series with its intervals, the default as an open marker, BL5 as a line with its marker at both ends
    (BL5_END_PT inside the axes; call after the x limits are final) and the reference line at 1; returns the values
    plotted (for the y axis)."""
    style.reference_line(ax, y=1.0)
    if bl5_y is not None:
        fig = ax.figure
        bb = ax.get_window_extent(fig.canvas.get_renderer())
        d = BL5_END_PT * fig.dpi / style.BP_PER_IN
        inv = ax.transData.inverted()
        x_ends = [float(inv.transform((bb.x0 + d, bb.y0))[0]), float(inv.transform((bb.x1 - d, bb.y0))[0])]
        style.plot_policy(ax, BL5, x_ends, [bl5_y, bl5_y], label="_nolegend_")
    x, y = finite(xs), finite(y)
    style.plot_policy(ax, GUARD, x, y, label="_nolegend_")
    lo, hi = finite(lo), finite(hi)
    ok = np.isfinite(lo) & np.isfinite(hi) & np.isfinite(y) & (hi > lo)
    if ok.any():
        style.errorbars(ax, GUARD, x[ok], y[ok], lo[ok], hi[ok])
    if default_y is not None:
        dm = style.scatter_policy(ax, GUARD, [default_x], [default_y], markerfacecolor="white", label="_nolegend_")
        dm._sublet_role = "default"
    ax.set_ylabel(ylabel)
    return [v for v in list(y) + list(lo) + list(hi) + [default_y, bl5_y, 1.0] if v is not None and np.isfinite(v)]


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    res_b = style.LEFT_LABEL + lab["b_y"].count("\n") * LINE_STEP_PT / style.BP_PER_IN      # C47: a y label's lines
    ax_a, ax_b = style.panel_row(fig, (1, 1), legend=LEGEND_ROWS, left=(None, res_b))      # C62: one legend row
    d = data["default"]
    shares = [v for v in data["a"]["share_pct"] if v is not None]
    xs = shares + ([d["share_pct"]] if d["share_pct"] is not None else [])
    for ax in (ax_a, ax_b):
        x_axis(ax, xs, shares)
    va = draw_panel(ax_a, data["a"]["share_pct"], data["a"]["median"], data["a"]["ci_lo"], data["a"]["ci_hi"],
                    d["share_pct"], d["a"]["median"], data["bl5"]["L-tr"], lab["a_y"])
    none = [None] * len(data["b"]["value"])          # W0 is one number per share (the worst 3-seed mean)
    vb = draw_panel(ax_b, data["b"]["share_pct"], data["b"]["value"], none, none, d["share_pct"], d["b"]["value"],
                    data["bl5"]["W0"], lab["b_y"])
    for ax, vals in ((ax_a, va), (ax_b, vb)):
        fit_y(ax, min(vals), max(vals))
        style.ygrid(ax)
        ax.set_xlabel(lab["x"])
    style.panel_letters([ax_a, ax_b])
    # C62: the two policies in one row (C47, at 9 pt: two rows of one column, since bl5_g1's label and the default's
    # entry did not fit one row of W1), and Algorithm 1's original allowance labeled next to its open marker in each
    # panel
    with mpl.rc_context({"legend.handlelength": LEGEND_HANDLE}):
        style.legend_row(fig, KEYS, rows=LEGEND_ROWS, ncol=1 if LEGEND_ROWS > 1 else None)
    default_label((ax_a, ax_b), lab["default"])
    return fig


def default_label(axes, text: str) -> list:
    """C47: Algorithm 1's original allowance named by a label (TICK_PT) in the guard's label color on the free space
    next to its open marker (common.place_label), in every panel of `axes` where it fits (print check of the gate: as first
    relabeled, only the first panel where it fitted, and the same open marker stood unlabeled in (b)), in one line or
    broken at its last space (DEFAULT_LINES): first nearer to it than to the other points, then, where no such spot
    exists (a default share among the swept ones, as on the reduced fixtures), on the free space nearest to it, joined
    to the marker's edge by a thin grey leader (common.LEADER_PT); a panel where it fits nowhere has no label
    (labels.note names the open marker). As built, the default was a third entry of the legend row. C62: in that
    second try the form whose box lies nearer to the marker is drawn (box_gap_pt; the one-line form first on a tie), so
    that the leader stays short (at 7 pt the one-line form, tried first as built, fitted 0.4 in above (b)'s marker
    where the two-line form fits beside it). Returns the labels drawn."""
    color = style.policy(GUARD).label_color
    d0, _, d1 = text.rpartition(" ")
    forms = [form.format(d=text, d0=d0, d1=d1) for form in DEFAULT_LINES]
    out = []
    for ax in axes:
        marks = [ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "default"]
        if not marks:
            continue
        near = points_pt(ax, marks[0].get_xdata(), marks[0].get_ydata())
        others = np.concatenate([points_pt(ax, ln.get_xdata(), ln.get_ydata()) for ln in ax.lines
                                 if hasattr(ln, "_sublet_policy") and ln not in marks] or [np.zeros((0, 2))])
        placed = None
        for s in forms:                                  # first try: nearer to the marker than to the other points
            placed = place_label(ax, s, near, others=others, color=color)
            if placed is not None:
                break
        if placed is None:                               # second try: the free space nearest to it, with a leader
            gaps = []
            for j, s in enumerate(forms):
                t = place_label(ax, s, near, color=color)
                if t is not None:
                    gaps.append((box_gap_pt(t, near[0]), j))
                    t.remove()
            if gaps:
                placed = place_label(ax, forms[min(gaps)[1]], near, color=color)
                default_leader(ax, placed, near[0])
        if placed is not None:
            placed._sublet_role = "direct_label:default"
            out.append(placed)
    return out


def box_gap_pt(t, p) -> float:
    """The distance (pt) from the point p (display pt) to the box of the text t (0 inside it)."""
    fig = t.get_figure(root=True)
    to_pt = style.BP_PER_IN / fig.dpi
    bb = t.get_window_extent(fig.canvas.get_renderer())
    dx = max(bb.x0 * to_pt - p[0], 0.0, p[0] - bb.x1 * to_pt)
    dy = max(bb.y0 * to_pt - p[1], 0.0, p[1] - bb.y1 * to_pt)
    return float(math.hypot(dx, dy))


def default_leader(ax, t, p) -> None:
    """A LEADER_PT grey leader from the box of the label t to the default's marker at p (display pt), ending at the
    marker's edge (default_label's second try, where the label is not next to the marker)."""
    fig = ax.figure
    to_pt = style.BP_PER_IN / fig.dpi
    bb = t.get_window_extent(fig.canvas.get_renderer())
    x0, y0, x1, y1 = bb.x0 * to_pt, bb.y0 * to_pt, bb.x1 * to_pt, bb.y1 * to_pt
    q = np.array([min(max(p[0], x0), x1), min(max(p[1], y0), y1)])
    pol = style.policy(GUARD)
    xy = ax.transData.inverted().transform(p / to_pt)
    ld = ax.annotate("", xy=tuple(xy), xytext=tuple(q - p), textcoords="offset points",
                     arrowprops=dict(arrowstyle="-", color=style.THEORY_GREY, linewidth=LEADER_PT, shrinkA=0.5,
                                     shrinkB=0.5 * (pol.markersize + style.MARKER_EDGE_PT)),
                     zorder=style.Z_DATA - 0.05)
    ld._sublet_role = "default_leader"


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
