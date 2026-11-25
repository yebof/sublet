"""sf_e2_pool: E2 per spot pool, per MaaS quartile of alpha_k, and the whole-trace ratio (design/sim_spec_ms3.md §8.7,
M50; plan §4, part S-F).

(a) Per-episode median ALG / OPT of A1 against H (min, symlog) per spot pool (e2/summary.json
    episodes.<pool>.<H>.1.a1.median; the pools of a11_calibration.json inputs.spot_L7_lenders), in A1's color, the
    pools told apart by their markers (POOL_MARKERS: A1's filled hexagon, an open hexagon, an open square drawn on
    top) and named in a legend in a corner free of data; a pool without any value (H800, whose cells have no layer
    site, design/sim_spec_ms3.md §13 item 35) is left out of the legend. Its own y scale (as built it shared (b)'s,
    1 to 3.3, so its pools, 1.000-1.075, filled the bottom 6% and series-2 covered A100): a log axis where
    nice_log_ticks gives three ticks over the range, else linear (median_axis).
(b) The same per MaaS quartile (episodes.maas_q<i>.<H>.1.a1.median; the 20 clusters ordered by their median alpha_k
    over the H grid, 5 per quartile, e2/summary.json meta.maas_quartiles), with four markers (QUARTILE_MARKERS),
    labeled Q1-Q4 at their ends, coinciding ends under one label ("Q1, Q2"); its own y axis.
(c) Whole-trace ratio sum ALG / sum DP of A1 (layers with a band), the median over (lender, series) with its
    median_ci95 (totals.<group>.<H>.1.<sched>.a1.whole_trace_ratio; under `trace` its by_alignment.1 values, so
    that both schedules use alignment 1, M19; the four-alignment values are in the extract): MaaS solid, spot
    dashed, `trace` filled markers, `eager` open markers.
Trace episodes and whole traces leave C2's core: the ratios are diagnostics.

C62 (2026-11-24; the look of Fig. 7): (a)'s and (b)'s y labels on one line; in (c) the lender lines named
directly (lender_names) and the schedules keyed by their markers in its free upper left corner, so that its y range
is the data's (a two-column key of ALG*, the line styles and the schedules filled its top 40%); the light y grid in
(c) too; the notice H in math; H ticks thinned at half an em of the 7-pt labels. The data and their extract entries
are unchanged.

C62 fix round (the critic of the supplement build): each panel titled beside its letter at the caption size, as Figs.
S9 and S10 on the same page ("Spot pools", "MaaS clusters by price quartile", "Whole traces"; labels.titles), with
(c)'s top raised just enough that its top tick label clears the title (top_tick_room), and the axes' tops
sf_e2_mu_ep.title_drop_in below the letters' line as in Figs. S9 and S10 on the same page; (a)'s legend names the pool
"Series 2", as the paper's Fig. 2 and its caption do (as built "series-2"). The plotted values are unchanged.

Run from code/sim: python -m figs.supp.sf_e2_pool [--from-extract [JSON]].
"""
from __future__ import annotations

import math
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, FuncFormatter, MaxNLocator, NullLocator

from figs import style
from figs.common import TOP_TICK_GAP_PT, cli, finite, maybe, need, num_items, place_label, points_pt, text_width_in
from figs.fig2_e1a import POOL_SHORT
from figs.fig7_e2_e6 import (A11, E2, GROUPS, H_TICK_GAP_PT, LENDER, MAIN_LABELS, _dense, h_axis, nice_log_ticks,
                             panel_titles, totals_block)
from figs.inputs import Inputs
from figs.supp.sf_e2_mu_ep import raise_texts, title_drop_in        # C62 fix round

NAME = "sf_e2_pool"
KEY = "a1"
SCHEDS = ("trace", "eager")
style.register_supplementary(NAME, "W2", 2.2)
# (a) and (b) each with its own y scale (they shared one, §8.7, until the print check); the y label on two lines at 9
# pt, where one line was longer than the axes are high and ran into the panel letters; on one line since C62 (7.97
# pt). The notice H in math as in Fig. 7 (MAIN_LABELS)
# C62 fix round: each panel titled beside its letter at the caption size, as Figs. S9 and S10 on the same page (as
# built the only untitled figure of the ALG* family, Figs. S7-S11)
TITLES = {"a": "Spot pools", "b": "MaaS clusters by price quartile", "c": "Whole traces"}
LABELS = {"H": MAIN_LABELS["H"], "a_y": "Median per-episode ALG / OPT", "c_y": "Whole-trace ΣALG / ΣDP",
          "trace": "Trace schedule", "eager": "Eager schedule", "titles": TITLES,
          "note": "A1 (ALG*), mu/beta~ = 1; (a), (b) trace schedule, four alignments pooled (M19); (c) alignment 1"}


def pool_label(pool: str) -> str:
    """Short pool name, as the paper's Fig. 2 and its caption name the pools (fig2_e1a.POOL_SHORT: 'a1:A100-SXM4-80GB'
    -> 'A100', 'a1:GPU-series-2' -> 'Series 2'; as built 'series-2'); other names lose their '-SXM' suffix."""
    return POOL_SHORT.get(pool, pool.split(":", 1)[-1].split("-SXM")[0])


def a1_median_series(e2: Mapping, group: str) -> dict:
    """A1's per-episode median at mu = 1 per H (episodes.<group>.<H>.1.a1) with its median_ci95 (extract only) and
    the note of a missing or null value (§8.7)."""
    s = {"H_min": [], "median": [], "ci_lo": [], "ci_hi": [], "note": []}
    eps = need(e2, "episodes", group, what=E2)
    for H, hk, _ in num_items(eps):
        ent, note = maybe(eps, hk, 1, KEY)
        ent = ent if isinstance(ent, Mapping) else {}
        if note is None and ent.get("median") is None:
            note = ent.get("note") or ent.get("median_note") or "null"
        lo, hi = (ent.get("median_ci95") or [None, None])[:2]
        for f, v in zip(s, (H, ent.get("median"), lo, hi, note)):
            s[f].append(v)
    return s


def build(inp: Inputs) -> dict:
    e2, a11 = inp.json(E2), inp.json(A11)
    pools = [str(p) for p in need(a11, "inputs", "spot_L7_lenders", what=A11)]
    quart = need(e2, "meta", "maas_quartiles", what=E2)
    a = {p: {**a1_median_series(e2, p), "label": pool_label(p)} for p in pools}
    b = {q: {**a1_median_series(e2, q), "label": f"Q{i + 1}", "members": list(quart[q])}
         for i, q in enumerate(sorted(quart))}
    c = {g: {"trace": totals_block(e2, 1, sched="trace", field="whole_trace_ratio", groups=(g,), alignment=1,
                                   minimizer=False)[g],
             "eager": totals_block(e2, 1, sched="eager", field="whole_trace_ratio", groups=(g,),
                                   minimizer=False)[g]} for g in GROUPS}
    c4 = {g: totals_block(e2, 1, sched="trace", field="whole_trace_ratio", groups=(g,), minimizer=False)[g]
          for g in GROUPS}
    return {"a": a, "b": b, "c": c, "c_trace_four_alignments": c4, "labels": LABELS, "sources": list(inp.sources)}


def symlog_label_column(ax, x_hi: float, texts: Sequence[str], *, pad_pt: float = 6.0) -> None:
    """Extend a symlog H axis (linear below 1, linscale 1) to the right so that a column right of x_hi holds the
    widest of `texts`, and end the x spine at x_hi."""
    w = style.axes_rect_in(ax)[2]
    f = min((max(text_width_in(ax.figure, t) for t in texts) + pad_pt / 72.0) / w, 0.5)
    lo = ax.get_xlim()[0]
    units = (1.0 + math.log10(x_hi)) if x_hi > 1 else x_hi
    u_new = units / (1.0 - f)
    ax.set_xlim(lo, 10.0 ** (u_new - 1.0) if u_new > 1 else u_new)
    ax.spines["bottom"].set_bounds(lo, x_hi)


END_LABEL_H = style.TICK_PT * 1.15         # height of an end label (TICK_PT), points


def stack_end_labels(ax, series: Sequence[Mapping], *, dx_pt: float = 3.0, gap_pt: float = 0.5) -> list:
    """Rows [y_end, y_label, x, y, label, x_end, width] (y in points) of the end labels at the current scales:
    each just right of its line's last finite point; labels that would overlap moved apart vertically (the least
    amount, the block recentered on the line ends)."""
    to_pt = 72.0 / ax.figure.dpi
    rows = []
    for s in series:
        x, y = finite(s["H_min"]), finite(s["median"])
        ok = np.isfinite(x) & np.isfinite(y)
        if not ok.any():
            continue
        i = int(np.flatnonzero(ok)[-1])
        xp, yp = (v * to_pt for v in ax.transData.transform((x[i], y[i])))
        w = text_width_in(ax.figure, s["label"]) * 72.0
        rows.append([yp, yp, x[i], y[i], s["label"], xp, w])
    rows.sort(key=lambda r: r[0])
    for j in range(1, len(rows)):          # only labels whose x extents overlap push each other
        for k in range(j):
            a, b = rows[k], rows[j]
            if a[5] + dx_pt < b[5] + dx_pt + b[6] and b[5] + dx_pt < a[5] + dx_pt + a[6]:
                b[1] = max(b[1], a[1] + END_LABEL_H + gap_pt)
    if rows:
        shift = float(np.mean([r[1] - r[0] for r in rows]))
        for r in rows:
            r[1] -= shift
    return rows


def end_labels(ax, series: Sequence[Mapping], *, dx_pt: float = 3.0, gap_pt: float = 0.5) -> None:
    """Each line labeled just right of its last finite point in A1's color (stack_end_labels). Where the block
    reaches above the axes, the top of the (log) y range is raised until it fits, so that every label stays beside
    its line's end (as built at 9 pt: Q1 and Q2 end at one point near the top of (b), and moving the block down
    inside the axes set Q4's label 12 pt below its line); a block that still crosses an edge is moved inside."""
    to_pt = 72.0 / ax.figure.dpi
    h = END_LABEL_H
    for _ in range(6):
        rows = stack_end_labels(ax, series, dx_pt=dx_pt, gap_pt=gap_pt)
        bb = ax.get_window_extent()
        top, bottom = bb.y1 * to_pt, bb.y0 * to_pt
        over = max((r[1] for r in rows), default=-math.inf) + h / 2 - top
        if over <= 0.25 or ax.get_yscale() != "log":
            break
        y0, y1 = ax.get_ylim()
        ax.set_ylim(y0, y1 * (y1 / y0) ** (over / (top - bottom)))
    if rows:
        over = max(r[1] for r in rows) + h / 2 - top
        under = bottom - (min(r[1] for r in rows) - h / 2)
        move = -over if over > 0 else (under if under > 0 else 0.0)
        for r in rows:
            r[1] += move
    for y0, y1, x, y, lab, _, _ in rows:
        style.direct_label(ax, KEY, x, y, lab, dx=dx_pt, dy=y1 - y0)


# (a)'s pool markers in order (later pools on top): A1's own (filled hexagon), an open hexagon, an open square, a
# filled square; (b)'s quartile markers: triangles up and down, filled and open, so that two coinciding points show
# both shapes (a filled up and down triangle stack to a star)
POOL_MARKERS = ({}, {"markerfacecolor": "white"}, {"marker": "s", "markerfacecolor": "white"}, {"marker": "s"})
QUARTILE_MARKERS = ({"marker": "^"}, {"marker": "v"}, {"marker": "^", "markerfacecolor": "white"},
                    {"marker": "v", "markerfacecolor": "white"})
END_MERGE_PT = style.MARKER_PT       # (b): ends closer than a marker (the markers overlap) share one label


def median_axis(lo: float, hi: float) -> tuple[str, tuple[float, float], list[float], Any]:
    """(scale, limits, ticks, formatter) of a median panel's y axis over the values [lo, hi]: log as before
    (limits lo / 1.02, hi x 1.04; nice_log_ticks) where that gives at least three ticks, else linear (limits padded
    by 6% of the range as (c), at most five ticks of MaxNLocator, written with the fewest decimals that give every
    tick exactly)."""
    lim = (lo / 1.02, hi * 1.04)
    ticks = nice_log_ticks(*lim)
    if len(ticks) >= 3:
        return "log", lim, ticks, style.PLAIN
    pad = 0.06 * (hi - lo)
    lim = (lo - pad, hi + pad)
    ticks = [float(t) for t in MaxNLocator(5, steps=[1, 2, 2.5, 5, 10]).tick_values(*lim) if lim[0] <= t <= lim[1]]
    # the fewest decimals that write every tick exactly (a step of 2.5 x 10^k needs one more than its order)
    dec = next(d for d in range(7) if all(abs(round(t, d) - t) <= 1e-9 * max(1.0, abs(t)) for t in ticks))
    return "linear", lim, ticks, FuncFormatter(lambda v, _pos=None: f"{v:.{dec}f}")


def merged_ends(ax, series: Sequence[Mapping]) -> list[dict]:
    """The series for end_labels with the ends at one H that lie within END_MERGE_PT of each other (in points, at
    the current scales) under one label, the labels joined in series order ("Q1, Q2"); a merged entry keeps its
    first member's line. Needs the final y scale."""
    to_pt = 72.0 / ax.figure.dpi
    ends = []
    for k, s in enumerate(series):
        x, y = finite(s["H_min"]), finite(s["median"])
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.any():
            i = int(np.flatnonzero(ok)[-1])
            ends.append((x[i], ax.transData.transform((x[i], y[i]))[1] * to_pt, k))
    groups: list[list] = []
    for x, y, k in sorted(ends):
        g = groups[-1] if groups else None
        if g is not None and g[-1][0] == x and y - g[-1][1] < END_MERGE_PT:
            g.append((x, y, k))
        else:
            groups.append([(x, y, k)])
    out = []
    for g in groups:
        ks = sorted(k for _, _, k in g)
        out.append({**series[ks[0]], "label": ", ".join(series[k]["label"] for k in ks)})
    return out


def free_corner_legend(ax, handles: Sequence[tuple], *, corners=("upper left", "upper right", "lower right",
                                                                  "lower left")):
    """A corner legend in the first of `corners` where its box covers no data point of the axes (the markers'
    radius included); the first corner if none is free. Needs the final scales."""
    rend = ax.figure.canvas.get_renderer()
    pts = [ax.transData.transform(np.column_stack([ln.get_xdata(), ln.get_ydata()]).astype(float))
           for ln in ax.lines if getattr(ln, "_sublet_policy", None)]
    pts = np.vstack(pts) if pts else np.empty((0, 2))
    pts = pts[np.isfinite(pts).all(axis=1)]
    r = (style.MARKER_PT / 2.0 + 1.0) * ax.figure.dpi / 72.0
    for loc in corners:
        leg = style.corner_legend(ax, [], extra=handles, loc=loc)
        bb = leg.get_window_extent(rend)
        if not ((pts[:, 0] >= bb.x0 - r) & (pts[:, 0] <= bb.x1 + r) & (pts[:, 1] >= bb.y0 - r)
                & (pts[:, 1] <= bb.y1 + r)).any():
            return leg
        leg.remove()
    return style.corner_legend(ax, [], extra=handles, loc=corners[0])


def draw_median_panel(ax, block: Mapping, ylabel: str, *, legend: bool = False) -> None:
    """One line per series in A1's style with its own y axis (median_axis); with `legend`, the series are told apart
    by POOL_MARKERS and named in a legend in a free corner (panel (a)), otherwise by QUARTILE_MARKERS and labeled at
    their last H (panel (b), coinciding ends merged, merged_ends)."""
    xs, handles = [], []
    drawn = [s for s in block.values() if any(v is not None for v in s["median"])]
    marks = POOL_MARKERS if legend else QUARTILE_MARKERS
    if len(drawn) > len(marks):
        raise ValueError(f"{len(drawn)} series with values, {len(marks)} marker variants")
    for i, s in enumerate(drawn):
        line = style.plot_policy(ax, KEY, s["H_min"], [np.nan if v is None else v for v in s["median"]], **marks[i])
        handles.append((line, s["label"]))
    for s in block.values():
        xs += [float(v) for v in s["H_min"]]
    h_axis(ax, xs, gap_pt=H_TICK_GAP_PT)               # C62: half an em of the 7-pt labels
    vals = [v for s in drawn for v in s["median"] if v is not None]
    scale, lim, ticks, fmt = median_axis(min(vals + [1.0]), max(vals))
    if scale == "log":
        style.log_axis(ax, "y", ticks=ticks)
    else:
        ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.yaxis.set_major_formatter(fmt)
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_ylim(*lim)
    if not legend:
        ends = merged_ends(ax, drawn)
        at_end = [s["label"] for s in ends
                  if max((h for h, v in zip(s["H_min"], s["median"]) if v is not None), default=None) == max(xs)]
        if at_end:                         # a label column only for the lines that end at the last H
            symlog_label_column(ax, max(xs), at_end)
        end_labels(ax, ends)
    elif handles:
        free_corner_legend(ax, handles)
    style.ygrid(ax)
    ax.set_ylabel(ylabel)


def y_reserve(fig, block: Mapping, ylabel: str) -> float:
    """Left reserve (inches) of a median panel: its tick labels (median_axis) and the y label's lines (ytick_reserve
    counts one)."""
    vals = [v for s in block.values() for v in s["median"] if v is not None]
    _, _, ticks, fmt = median_axis(min(vals + [1.0]), max(vals))
    return (style.ytick_reserve(fig, [fmt(t) for t in ticks], ylabel=True)
            + ylabel.count("\n") * style.LABEL_PT * 1.2 / style.BP_PER_IN)


def lender_names(ax, series: Mapping) -> list:
    """(c) (C62): each lender group named once on the free space next to its two lines (trace and eager schedule;
    common.place_label, nearer to them than to the other group's), in ALG*'s label color with a white halo, as
    Fig. 7(b) names its lender lines; a group whose lines run on where the other group's end (MaaS beyond 5 min) is
    named there, away from the other's lines (in the first render "MaaS" sat at the peak of its eager line at 2 min,
    above the spot lines' peak). StyleError where a name fits nowhere. Needs the final scales."""
    lines, near = {}, {}
    ends = {g: max((h for s in SCHEDS for h, v in zip(series[g][s]["H_min"], series[g][s]["median"])
                    if v is not None), default=-math.inf) for g in GROUPS}
    for g in GROUPS:
        P = [points_pt(ax, series[g][s]["H_min"], series[g][s]["median"]) for s in SCHEDS]
        lines[g] = np.vstack([_dense(q) if len(q) > 1 else q for q in P if len(q)] or [np.empty((0, 2))])
        beyond = max(ends[o] for o in GROUPS if o != g)
        x_cut = ax.transData.transform((beyond, 1.0))[0] * 72.0 / ax.figure.dpi if np.isfinite(beyond) else -np.inf
        own = lines[g][lines[g][:, 0] > x_cut]
        near[g] = own if len(own) else lines[g]
    out = []
    for g in GROUPS:
        others = np.vstack([lines[o] for o in GROUPS if o != g])
        t = place_label(ax, style.ENV_LABELS["lender"][g], near[g], others=others,
                        color=style.policy(KEY).label_color)
        if t is None:
            raise style.StyleError(f"{NAME} (c): the {g} lines' name fits nowhere in the panel")
        out.append(t)
    return out


def top_tick_room(ax) -> None:
    """C62 fix round: fix the major y ticks of a linear axis and raise its top so that its highest tick label ends
    TOP_TICK_GAP_PT below the axes top, clear of the panel title on its letter's baseline (sf_e8's rule; with the
    titles, (c)'s "Whole traces" touched its top tick label "2.2", 0.02 below the data's padded top). Every tick is
    kept; the bottom stays."""
    y0, y1 = ax.get_ylim()
    ticks = [float(t) for t in ax.yaxis.get_majorticklocs() if y0 <= t <= y1]
    if not ticks:
        return
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    t = max(ticks)
    r = ax.figure.canvas.get_renderer()
    to_pt = style.BP_PER_IN / ax.figure.dpi
    up = [tk.label1.get_window_extent(r).y1 - ax.transData.transform((0.0, t))[1]
          for tk in ax.yaxis._update_ticks() if abs(tk.get_loc() - t) <= 1e-9 * max(1.0, abs(t))
          and tk.label1.get_visible()]
    room = (max(up) * to_pt if up else 0.5 * style.TICK_PT) + TOP_TICK_GAP_PT
    h_pt = style.axes_rect_in(ax)[3] * style.BP_PER_IN
    if (y1 - t) / (y1 - y0) * h_pt < room:
        ax.set_ylim(y0, (t * h_pt - room * y0) / (h_pt - room))


def draw(data: Mapping) -> Any:
    """C62: (a)'s and (b)'s y labels on one line; H ticks thinned at half an em of the 7-pt labels (H_TICK_GAP_PT);
    (c) its lender lines named directly (lender_names, as Fig. 7(b)) and the schedules keyed by their markers in its
    free upper left corner, its y range the data's (as built, a two-column key of ALG*, the lender line styles and
    the schedules filled the top 40% of (c), which legend_headroom raised the y range for). C62 fix round: the panel
    titles (TITLES) on the letters' baseline at the caption size (fig7_e2_e6.panel_titles), (c)'s top raised so that
    its top tick label clears its title (top_tick_room)."""
    lab = data["labels"]
    fig = style.new_figure(NAME)
    drop = title_drop_in()                         # C62 fix round: as the other titled figures of the family
    ax_a, ax_b, ax_c = style.panel_row(fig, (1, 1, 1), left=(y_reserve(fig, data["a"], lab["a_y"]),
                                                             y_reserve(fig, data["b"], lab["a_y"]), None),
                                       top=style.MARGIN_TOP + drop)
    draw_median_panel(ax_a, data["a"], lab["a_y"], legend=True)
    draw_median_panel(ax_b, data["b"], lab["a_y"])
    xs, vals = [], []
    for g in GROUPS:
        for sched in SCHEDS:
            s = data["c"][g][sched]
            x, y, lo, hi = (finite(s[f]) for f in ("H_min", "median", "ci_lo", "ci_hi"))
            kw = {} if sched == "trace" else dict(markerfacecolor="white")
            style.plot_policy(ax_c, KEY, x, y, env=LENDER[g], **kw)
            ok = np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi)
            if ok.any():
                style.errorbars(ax_c, KEY, x[ok], y[ok], lo[ok], hi[ok])
            xs += list(x)
            vals += [v for v in np.concatenate([y, lo, hi]) if np.isfinite(v)]
    h_axis(ax_c, xs, gap_pt=H_TICK_GAP_PT)
    lo, hi = min(vals + [1.0]), max(vals)
    pad = 0.06 * (hi - lo)
    ax_c.set_ylim(lo - pad, hi + pad)
    top_tick_room(ax_c)                             # C62 fix round: its top tick label clear of the title
    ax_c.set_ylabel(lab["c_y"])
    style.ygrid(ax_c)
    for ax in (ax_a, ax_b, ax_c):
        ax.set_xlabel(lab["H"])
    p = style.policy(KEY)
    sched_handles = [(Line2D([], [], color=p.color, marker=p.marker, markersize=p.markersize, linestyle="none",
                             markeredgewidth=style.MARKER_EDGE_PT, markerfacecolor=face), lab[s])
                     for s, face in (("trace", p.color), ("eager", "white"))]
    free_corner_legend(ax_c, sched_handles, corners=("upper left", "upper right", "lower right", "lower left"))
    lender_names(ax_c, data["c"])
    titles = lab.get("titles", TITLES)              # extracts before the C62 fix round have none
    letters, texts = panel_titles([ax_a, ax_b, ax_c], [titles[p] for p in "abc"])        # C62 fix round
    raise_texts(letters + texts, drop)
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
