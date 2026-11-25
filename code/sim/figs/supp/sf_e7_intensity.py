"""sf_e7_intensity: E7's stress-intensity curves on the confirmation weeks, with the table e7v2_crossings.tex
(design/sublet_v2.md §11, W4, W9, W10; §4.5 "Stress-intensity curve"; prereg §5, "reported in full").

Figure (W2 x 2.5 in, C41). The cost over all-fallback (r0) of the twelve tags of part `second` (SUPP_POLICIES_MS5B
[NAME]) against the reclaim probability p of the i.i.d. lender (iid_step with D_slots 1: an announcement at each
revocable site in each slow slot with probability p; p = 0 is L-hon), on the weeks where every one of the twelve has
the full grid (analysis.json reported.intensity_curves: main's and second's runs merged per tag and week by the
registered analysis, §8.4 B8; on the confirmation weeks 301-304 of part `second`, the grid {0, 0.05, 0.1, 0.2, 0.34,
0.5, 0.8, 1}; read from the data, never typed). Each point is the median over those weeks with its 95% week-bootstrap
interval (ms5b_common.bootstrap_median_ci, seed 20261031, 10,000 resamples; W9; C59: over 4 weeks the interval is the
range of the weeks' values, and the caption draft calls it so), policy seed 0. A legend row of the
twelve labels needed about 10 in in two rows at 9 pt (7.3 in at 7 pt, C62) against the 7.1 in of W2 (§11 review,
finding 13), so the figure has one
panel per family with its own legend (W4: "one panel per week or per group"): (a) greedy renting and its variants
(BL1, BL1-BO, BL1N, BL1-GP), (b) RetroRenting-style and its variants (BL5-cur, BL5-tau60, BL5N, Sublet-MS4), (c) the
other policies (A9, BL3-0, BL4); Sublet is drawn in every panel as the reference and labeled directly at its curve's
point nearest p = REF_LABEL_P (below it where it is the lowest series there within REF_TIE, else above; C62: as built
at the curve's last point), so that the legends hold
only each panel's own policies (the registry's legend order, style.legend_order). The panels share the y axis; the
grey reference line marks all-fallback (cost 1).

As built (choices that §11 leaves open):
* The legend sits in each panel's upper left corner, one entry per line, a label wider than LEGEND_WRAP_IN split
  once at a word break (ms5b_e7_lib.wrap; Sublet-MS4's label, 3.1 in on one line, in two). The panels' widths are
  set so that each legend fits its panel (its widest entry plus LEGEND_EXTRA_IN), the rest of the row shared
  equally. The y axis then reaches high enough that no median, interval or marker lies under a legend (the data
  under a legend's width, plus the marker radius and LEGEND_PAD_PT; the spines and ticks end at the data's top).
* x on a square-root scale (print check 2026-11-03: on a linear axis the grid points 0, 0.05 and 0.1 lie 6 pt apart
  and the five dodged series of a panel ran into each other): the points are drawn at sqrt(p), from -X_PAD to
  sqrt(1) + X_PAD, with labeled ticks at X_TICKS and minor ticks at the grid's other points; one x label centered
  under the row (ms4_lib.center_xlabel); y ticks the first step of Y_STEPS that gives Y_MIN_TICKS to Y_MAX_TICKS
  ticks over the data.
* The series of a panel are dodged by DODGE_PT points per series and layered as in ms4_lib.draw_series_layered:
  every line, then every interval bar, then every marker.
* labels.caption is a caption draft with every count, week and grid point read from the inputs; it names the part,
  states that the statistics are descriptive (§4.5, "Dependence"), gives the scale and the dodge, and names the
  medians that overlap (overlaps: equal to three decimals at a p, or within NEAR_TOL at the grid's last NEAR_RUN
  or more points; A9 against Sublet has its own sentence).

Table (after hook, figs.common.write_table: SUBLET_FIGS_TABLES_DIR, else SUBLET_FIGS_PDF_DIR when set, else
paper/supplement/tables/), from the extract's `tables`, so --from-extract rewrites it:
  e7v2_crossings.tex  every tag of analysis.json reported.intensity_curves (the 22 tags of part main, §3's order;
                      the lagged-demand tags ran under L-tr only and have no curve) and every week: the first p at
                      which r0 > 1, "none" where r0 <= 1 at every p up to the grid's largest (as Table III v2),
                      ">p_max" where r0 <= 1 at every p measured that week and its curve ends below that (p_max the
                      largest; on a three-point grid {0, 0.05, 0.2} that reads "not reached at p <= 0.2", W4), "--"
                      where the week has no curve, and a dagger where a point before the crossing has no run. Its
                      scope (tags, weeks, grids) is in the extract's tables block for the claims report (W11, R
                      rows).

Inputs (W10): code/sim/out/sublet_v2/analysis.json and the summaries of parts main and second (the weeks of part
second, each part's git revision, meta.reduced); no run file. Run from code/sim:
python -m figs.supp.sf_e7_intensity [--from-extract [JSON]].
"""
from __future__ import annotations

import itertools
import math
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.ticker import FixedFormatter, FixedLocator

from figs import style
from figs.common import MissingKey, cli, need, text_width_in, write_table
from figs.inputs import Inputs
from figs.supp import ms5b_e7_lib as L
from figs.supp.ms4_lib import center_xlabel, line_casing

NAME = "sf_e7_intensity"
KEYS = style.SUPP_POLICIES_MS5B[NAME]          # the twelve tags of part second (C41)
TABLES = ("e7v2_crossings.tex",)
style.register_supplementary(NAME, "W2", 2.5)
REF = "sublet_v2"                              # drawn in every panel
GROUPS = (("a", "Greedy variants", ("bl1", "bl1_bo", "bl1n", "bl1_gp")),
          ("b", "RetroRenting variants", ("bl5_cur", "bl5_tau60", "bl5n", "sublet_ms4")),
          ("c", "Other policies", ("a9", "bl3_0", "bl4")))
if sorted({REF, *(k for _, _, ks in GROUPS for k in ks)}) != sorted(KEYS):
    raise style.StyleError(f"{NAME}: the panels' keys must be SUPP_POLICIES_MS5B[{NAME!r}]")
DODGE_PT = 1.4                  # x offset between neighboring series of a panel (not in §11)
X_PAD = 0.045                   # the x axis beyond sqrt(p) = 0 and 1 (room for the dodged markers)
X_TICKS = (0.0, 0.05, 0.2, 0.5, 1.0)  # labeled p ticks on the square-root axis; the grid's other points get minor ticks
NEAR_TOL = 0.03                 # medians this close overlap at the panels' scale (about 2.5 pt)
NEAR_RUN = 3                    # ... noted in the caption where a pair stays this close at the grid's last NEAR_RUN p
Y_STEPS = (0.05, 0.1, 0.2, 0.25, 0.5, 1.0)
Y_MIN_TICKS, Y_MAX_TICKS = 3, 6
Y_PAD = 0.04                    # the y range beyond the data, as a share of its span
LEGEND_WRAP_IN = 1.6            # a legend label wider than this is split once at a word break (ms5b_e7_lib.wrap)
LEGEND_EXTRA_IN = 0.45          # a legend's width beyond its widest label (handle, pads); for the panel widths
LEGEND_PAD_PT = 2.0             # the least gap between a legend and the data below it
Z_BARS = style.Z_SUBLET + 0.05
Z_MARKS = style.Z_SUBLET + 0.1
Z_STEP = 0.1
LABELS = {"x": "i.i.d. lender: reclaim probability $p$ per site and slot (square-root scale)",
          "y": "Cost / all-fallback",
          "caption": ("Stress-intensity curves of the {n_tags} policies of part second on weeks {weeks} ({n_weeks} "
                      "week{s}, policy seed 0): cost over all-fallback against the reclaim probability $p$ of the "
                      "i.i.d. lender per site and slot, on the grid $p\\in\\{{{grid}\\}}$ ($p=0$ is the honoring "
                      "lender L-hon; part main's runs and part second's merged). Medians over the {n_weeks} weeks "
                      "with their ranges; the weeks are rotations of one series. Sublet is drawn and labeled "  # C59
                      "in every panel; the "
                      "grey line marks all-fallback. The $p$ axis has a square-root scale (minor ticks: the grid's "
                      "other points), and the series of a panel are offset horizontally by {dodge} pt each, so that "
                      "equal medians stay apart. {near}{overlap}Each policy's first $p$ with a cost above 1, on every "
                      "week, is in Table~\\ref{{tab:e7v2-crossings}}."),
          "equal": "At $p={p}$, {names} share the median {v}. ",
          "tail": "At $p\\ge{p}$, {names} differ by at most {d}. ",
          "near": "Critical-ratio renting's medians lie within {d} of Sublet's at every $p$. ",
          "near_equal": "Critical-ratio renting's medians equal Sublet's at every $p$. "}
CROSS_LABEL = "tab:e7v2-crossings"


def _full(curve: Mapping, grid: Sequence[float]) -> bool:
    pts = {float(p): v for p, v in curve.get("points") or []}
    return all(pts.get(p) is not None for p in grid)


def _fmt_p(p) -> str:
    return format(float(p), "g")


def crossing_rows(curves: Mapping) -> dict:
    """The rows of e7v2_crossings.tex: every tag of `curves` (§3's order, then any other), every week of any curve;
    per cell the first p with r0 > 1 (None: not reached), the largest p measured and the number of points, and
    whether a point before the crossing has no run (the curve's first_p_note)."""
    tags = [t for t in L.E7_TAGS if t in curves] + sorted(t for t in curves if t not in L.E7_TAGS)
    weeks = sorted({w for by_w in curves.values() for w in by_w}, key=int)
    rows = []
    for t in tags:
        if t not in L.KEY_OF_TAG:
            raise MissingKey(f"{L.ANALYSIS}: tag {t!r} has no registry key (ms5b_e7_lib.KEY_OF_TAG)")
        cells = {}
        for w in weeks:
            c = curves[t].get(w)
            if c is None:
                cells[w] = None
                continue
            have = [float(p) for p, v in c.get("points") or [] if v is not None]
            cells[w] = {"first": c.get("first_p_above_1"), "p_max": max(have) if have else None,
                        "n_points": len(have), "gap": bool(c.get("first_p_note"))}
        rows.append({"tag": t, "key": L.KEY_OF_TAG[t], "label": L.label(t), "cells": cells})
    grids = sorted({(c["n_points"], c["p_max"]) for r in rows for c in r["cells"].values() if c})
    top = max((c["p_max"] for r in rows for c in r["cells"].values() if c and c["p_max"] is not None), default=None)
    return {"weeks": weeks, "rows": rows, "grid_top": top,
            "scope": {"tags": tags, "weeks": weeks, "parts": ["main", "second"],
                      "grids": [{"n_points": n, "p_max": p} for n, p in grids]}}


def build(inp: Inputs) -> dict:
    main, second, an = inp.json(L.MAIN), inp.json(L.SECOND), inp.json(L.ANALYSIS)
    curves = need(an, "reported", "intensity_curves", what=L.ANALYSIS)
    grid = sorted({float(p) for by_w in curves.values() for c in by_w.values() for p, _ in c.get("points") or []})
    full = {}
    for key in KEYS:
        tag = L.TAG_OF_KEY[key]
        if not curves.get(tag):
            raise MissingKey(f"{L.ANALYSIS}: reported.intensity_curves has no curve of {tag!r}")
        full[key] = [w for w in sorted(curves[tag], key=int) if _full(curves[tag][w], grid)]
    weeks = sorted(set.intersection(*(set(v) for v in full.values())), key=int)
    if not weeks:
        raise MissingKey(f"{L.ANALYSIS}: no week has the full grid {grid} for every tag of {list(KEYS)}")
    series = {}
    for key in KEYS:
        tag = L.TAG_OF_KEY[key]
        pts = {w: {float(p): v for p, v in curves[tag][w]["points"]} for w in weeks}
        s = {"tag": tag, "p": grid, "median": [], "lo": [], "hi": [], "n": [],
             "per_week": {w: [pts[w][p] for p in grid] for w in weeks}}
        for p in grid:
            st = L.med_ci(pts[w][p] for w in weeks)
            for f in ("median", "lo", "hi", "n"):
                s[f].append(st[f])
        series[key] = s
    near = max(abs(a - b) for a, b in zip(series["a9"]["median"], series[REF]["median"]))
    out = {"keys": list(KEYS), "groups": [{"letter": g, "title": t, "keys": list(ks)} for g, t, ks in GROUPS],
           "grid": grid, "weeks": weeks, "series": series,
           "a9_sublet_max_gap": near, "overlaps": overlaps(series, grid), "bootstrap": dict(L.BOOT),
           "tables": {"e7v2_crossings": crossing_rows(curves)},
           "labels": dict(LABELS),
           "meta": {**L.meta_of({"main": main, "second": second, "analysis": an}), "runs_files": []}}
    out["labels"]["caption"] = caption(out)
    out["meta"]["sources"] = list(inp.sources)
    return out


bound_text = L.bound_text


def overlaps(series: Mapping, grid: Sequence[float]) -> dict:
    """The medians that overlap within a panel (Sublet in each), beyond A9 and Sublet (the caption's own sentence):
    equal: [{panel, p, value, keys}] groups of two or more series with the same median to three decimals at a p;
    tail: [{panel, p, keys, max_diff}] pairs whose medians differ by at most NEAR_TOL at each of the grid's last
    NEAR_RUN or more points (p the first of them)."""
    eq, tail = [], []
    for letter, _, ks in GROUPS:
        keys = style.legend_order([REF, *ks])
        for i, p in enumerate(grid):
            by: dict = {}
            for k in keys:
                v = series[k]["median"][i]
                if v is not None:
                    by.setdefault(round(float(v), 3), []).append(k)
            for v, g in by.items():
                if len(g) > 1 and set(g) != {REF, "a9"}:
                    eq.append({"panel": letter, "p": p, "value": v, "keys": g})
        for a, b in itertools.combinations(keys, 2):
            if {a, b} == {REF, "a9"}:
                continue
            ma, mb = series[a]["median"], series[b]["median"]
            n = 0
            for i in range(len(grid) - 1, -1, -1):
                if ma[i] is None or mb[i] is None or abs(ma[i] - mb[i]) > NEAR_TOL:
                    break
                n += 1
            if n >= NEAR_RUN:
                tail.append({"panel": letter, "p": grid[len(grid) - n], "keys": [a, b],
                             "max_diff": max(abs(ma[i] - mb[i]) for i in range(len(grid) - n, len(grid)))})
    return {"equal": eq, "tail": tail}


def caption(d: Mapping) -> str:
    near = d["a9_sublet_max_gap"]
    nt = ((LABELS["near_equal"] if near == 0.0 else LABELS["near"].format(d=bound_text(near))) if near < 0.01
          else "")
    ov = d.get("overlaps") or {}
    lab = lambda ks: L.join_labels([L.tex(style.POLICIES[k].label) for k in ks])     # noqa: E731
    overlap = "".join(LABELS["equal"].format(p=_fmt_p(e["p"]), names=lab(e["keys"]), v=format(e["value"], ".3f"))
                      for e in ov.get("equal") or [])
    overlap += "".join(LABELS["tail"].format(p=_fmt_p(e["p"]), names=lab(e["keys"]), d=bound_text(e["max_diff"]))
                       for e in ov.get("tail") or [])
    nw = len(d["weeks"])
    return LABELS["caption"].format(n_tags=len(d["keys"]), weeks=L.week_span(d["weeks"]), n_weeks=nw,
                                    s="s" if nw != 1 else "", grid=", ".join(_fmt_p(p) for p in d["grid"]),
                                    B=f"{d['bootstrap']['B']:,}", seed=d["bootstrap"]["seed"], near=nt,
                                    dodge=format(DODGE_PT, "g"), overlap=overlap)


# ---------------------------------------------------------------------------------------------------------------
def legend_pairs(fig, keys: Sequence[str]) -> list[tuple]:
    """(handle, label) of `keys` in the registry's legend order, each label wrapped at LEGEND_WRAP_IN."""
    return [(h, L.wrap(fig, lab, LEGEND_WRAP_IN)) for h, lab in style.policy_handles(keys)]


def panel_widths(fig, pairs: Sequence[Sequence[tuple]]) -> list[float]:
    """Axes widths (in) of the panels: each its legend's widest label plus LEGEND_EXTRA_IN, the rest of the row (W2
    less the y-label reserve of (a), the shared reserves of the others and the right margin) shared equally."""
    need_in = [max(text_width_in(fig, lab) for _, lab in ps) + LEGEND_EXTRA_IN for ps in pairs]
    avail = style.W2 - style.LEFT_LABEL - style.LEFT_SHARED * (len(pairs) - 1) - style.MARGIN_RIGHT
    extra = avail - sum(need_in)
    if extra < 0:
        raise style.StyleError(f"{NAME}: the legends need {sum(need_in):.2f} in, the row has {avail:.2f} in")
    return [w + extra / len(pairs) for w in need_in]


def y_ticks(lo: float, hi: float) -> list[float]:
    """Ticks of the first step of Y_STEPS with Y_MIN_TICKS to Y_MAX_TICKS ticks in [lo, hi]."""
    for st in Y_STEPS:
        t = [round(k * st, 10) for k in range(math.ceil(lo / st - 1e-9), math.floor(hi / st + 1e-9) + 1)]
        if Y_MIN_TICKS <= len(t) <= Y_MAX_TICKS:
            return t
    return [round(lo, 3), round(hi, 3)]


def draw_panel(ax, keys: Sequence[str], series: Mapping) -> list[tuple]:
    """The panel's series, layered (lines, bars, markers) and dodged; returns (x, y_top) of every drawn point and
    interval end, for the legend's headroom."""
    n = len(keys)
    w_pt = style.axes_rect_in(ax)[2] * style.BP_PER_IN
    x0, x1 = ax.get_xlim()
    per_pt = (x1 - x0) / w_pt
    drawn = []
    for i, k in enumerate(keys):
        s = series[k]
        x = np.sqrt(np.asarray(s["p"], dtype=float)) + (i - (n - 1) / 2.0) * DODGE_PT * per_pt
        y = np.array([np.nan if v is None else v for v in s["median"]], dtype=float)
        lo = np.array([np.nan if v is None else v for v in s["lo"]], dtype=float)
        hi = np.array([np.nan if v is None else v for v in s["hi"]], dtype=float)
        drawn.append((k, x, y, lo, hi))
        line_casing(ax, k, x, y)
        style.plot_policy(ax, k, x, y, markevery=[])
    for k, x, y, lo, hi in drawn:
        ok = np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi) & (hi > lo)
        if ok.any():
            style.errorbars(ax, k, x[ok], y[ok], lo[ok], hi[ok], zorder=Z_BARS)
    pts = []
    for k, x, y, lo, hi in drawn:
        kw = style.policy_kwargs(k, lines=False, label=False)
        kw["zorder"] = Z_MARKS + Z_STEP * (kw["zorder"] - style.Z_DATA)
        (mk,) = ax.plot(x, y, **kw)
        mk._sublet_role = "markers"
        mk._sublet_markers_of = k
        pts += [(float(a), float(np.nanmax([b, c]))) for a, b, c in zip(x, y, hi) if np.isfinite(b)]
    return pts


REF_LABEL_DY_PT = 4.5           # Sublet's direct label this far below (or above) its curve's point
REF_TIE = 0.01                  # Sublet counts as the lowest series where it is within this of the lowest (A9 in (c))
REF_LABEL_P = 0.5               # C62: Sublet's label sits at the grid point nearest this p (as built, at the curve's
#                                 last point, right-aligned, where its text touched the segment from p = 0.8)


def ref_label(ax, keys: Sequence[str], series: Mapping):
    """Sublet's direct label at the point of its curve nearest REF_LABEL_P, centered on it: below the point where
    Sublet's median there is the lowest of the panel's series (within REF_TIE), else above it (C62; as built, at the
    last point, right-aligned)."""
    s = series[REF]
    have = [j for j, v in enumerate(s["median"]) if v is not None]
    i = min(have, key=lambda j: (abs(s["p"][j] - REF_LABEL_P), -j))
    y = s["median"][i]
    others = [series[k]["median"][i] for k in keys if k != REF and series[k]["median"][i] is not None]
    below = all(y <= v + REF_TIE for v in others)
    t = style.direct_label(ax, REF, math.sqrt(s["p"][i]), y, dx=0.0,
                           dy=-REF_LABEL_DY_PT if below else REF_LABEL_DY_PT, ha="center",
                           va="top" if below else "bottom")
    t._sublet_role = "direct_label"
    return t


def headroom(axes, legends, points, y0: float, top: float) -> float:
    """The y axis top at which every legend's lower edge clears the data under its width by the marker radius and
    LEGEND_PAD_PT (each legend's depth below its axes top is fixed in inches)."""
    fig = axes[0].figure
    r = fig.canvas.get_renderer()
    rad = 0.5 * (style.SUBLET_MARKER_PT + style.MARKER_EDGE_PT)
    need_top = top
    for ax, leg, pts in zip(axes, legends, points):
        bb, ab = leg.get_window_extent(r), ax.get_window_extent(r)
        if bb.x1 > ab.x1 + 0.5:
            raise style.StyleError(f"{NAME}: a legend is wider than its panel")
        frac = (bb.y0 - ab.y0) / ab.height - (rad + LEGEND_PAD_PT) * fig.dpi / 72.0 / ab.height
        x_right = ax.transData.inverted().transform((bb.x1, ab.y0))[0]
        under = [y for x, y in pts if x <= x_right + 0.02]
        if under and frac > 0:
            need_top = max(need_top, y0 + (max(under) - y0) / frac)
    return need_top


def draw(data: Mapping) -> Any:
    fig = style.new_figure(NAME)
    lab = data["labels"]
    groups = data["groups"]
    pairs = [legend_pairs(fig, g["keys"]) for g in groups]
    widths = panel_widths(fig, pairs)
    axes = style.panel_row(fig, widths, sharey=[False] + [True] * (len(groups) - 1))
    series = data["series"]
    vals = [v for s in series.values() for f in ("median", "lo", "hi") for v in s[f] if v is not None]
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, 1e-6)
    y0, top = lo - Y_PAD * span, hi + Y_PAD * span
    points, legends = [], []
    for ax, g, ps in zip(axes, groups, pairs):
        ax.set_xlim(-X_PAD, math.sqrt(max(data["grid"])) + X_PAD)
        keys = style.legend_order([REF] + list(g["keys"]))
        points.append(draw_panel(ax, keys, series))
        ref_label(ax, keys, series)
        if y0 < 1.0 < top:
            style.reference_line(ax, y=1.0)
        ticks = [p for p in X_TICKS if p <= max(data["grid"]) + 1e-12]
        ax.xaxis.set_major_locator(FixedLocator([math.sqrt(p) for p in ticks]))
        ax.xaxis.set_major_formatter(FixedFormatter([style.PLAIN(p) for p in ticks]))
        ax.xaxis.set_minor_locator(FixedLocator([math.sqrt(p) for p in data["grid"]
                                                 if all(abs(p - q) > 1e-12 for q in ticks)]))
        h, t = zip(*ps)
        legends.append(ax.legend(list(h), list(t), loc="upper left", frameon=False, borderaxespad=0.3))
    axes[0].set_ylim(y0, top)
    ticks = y_ticks(y0, top)
    axes[0].set_ylim(y0, headroom(axes, legends, points, y0, top))
    for ax in axes:
        ax.yaxis.set_major_locator(FixedLocator(ticks))
        ax.yaxis.set_major_formatter(style.PLAIN)
        ax.spines["left"].set_bounds(y0, max(top, ticks[-1]))
    axes[0].set_ylabel(lab["y"])
    center_xlabel(axes, lab["x"])
    letters = style.panel_letters(axes)
    for ax, letter, g in zip(axes, letters, groups):
        L.caption_title(ax, letter, g["title"])
    return fig


# ---------------------------------------------------------------------------------------------------------------
def cell_text(c: Mapping | None, grid_top: float | None = None) -> str:
    """A crossing cell: the first p with r0 > 1; 'none' where r0 <= 1 at every p up to the largest p of any curve
    (grid_top); '>q' where the week's curve ends at q below it; '--' without a curve; a dagger where a point before
    the crossing has no run."""
    if c is None:
        return "--"
    if c["first"] is not None:
        s = _fmt_p(c["first"])
    elif c["p_max"] is not None:
        s = "none" if grid_top is not None and c["p_max"] >= grid_top - 1e-12 else f"$>${_fmt_p(c['p_max'])}"
    else:
        return "--"
    return s + ("$^\\dagger$" if c["gap"] else "")


def grid_text(t: Mapping) -> str:
    """Which grid each tag had on which weeks, from the cells: per grid (points, largest p), the tags and weeks
    that had it, written as 'the N tags ... on weeks a--b' where those cells form a product, else as a cell count."""
    out = []
    for g in sorted(t["scope"]["grids"], key=lambda g: -g["n_points"]):
        cells = [(r["tag"], w) for r in t["rows"] for w, c in r["cells"].items()
                 if c and (c["n_points"], c["p_max"]) == (g["n_points"], g["p_max"])]
        tags = sorted({a for a, _ in cells}, key=[r["tag"] for r in t["rows"]].index)
        weeks = sorted({w for _, w in cells}, key=int)
        what = f"{g['n_points']} points up to $p={_fmt_p(g['p_max'])}$"
        if len(cells) == len(tags) * len(weeks):
            who = "every policy" if len(tags) == len(t["rows"]) else f"{len(tags)} policies"
            out.append(f"{what} for {who} on week{'s' if len(weeks) != 1 else ''} {L.week_span(weeks)}")
        else:
            out.append(f"{what} on the other {len(cells)} policy-weeks" if out
                       else f"{what} on {len(cells)} policy-weeks")
    return "; ".join(out)


def crossings_tex(t: Mapping, d: Mapping) -> str:
    weeks = t["weeks"]
    top = t.get("grid_top")
    cap = (r"First crossing of all-fallback on every confirmation week (policy seed 0): the least reclaim probability "
           r"$p$ of the i.i.d. lender at which the cost exceeds all-fallback ($r_0>1$), parts main and second merged "
           r"as in the registered analysis. "
           + (r"A cell `none' means $r_0\le1$ at every $p$ of the grid up to $p=" + _fmt_p(top) + r"$; " if top is
              not None else "")
           + r"a cell $>q$ means $r_0\le1$ at every $p$ measured that week, $q$ the largest ($>$0.2 on a three-point "
           r"grid: not reached at $p\le0.2$); a dash, no run. Grids: "
           + grid_text(t) + r". The lagged-demand policies ran under the trace lender only and have no curve."
           + (r" $^\dagger$A point before the crossing has no run." if any(
               (c or {}).get("gap") for r in t["rows"] for c in r["cells"].values()) else ""))
    blocks = L.chunks(weeks, 16)
    out = []
    for j, ws in enumerate(blocks):
        rows = [[L.rag(L.tex(r["label"]))] + [cell_text(r["cells"][w], t.get("grid_top")) for w in ws]
                for r in t["rows"]]
        out.append(L.longtable("@{}p{2.0in}" + "c" * len(ws) + "@{}", cap if j == 0 else
                               f"Table~\\ref{{{CROSS_LABEL}}}, continued: weeks {L.week_span(ws)}.",
                               CROSS_LABEL, ["Policy"] + [str(w) for w in ws], rows, tabcolsep="2.4pt",
                               cont=j == 0))
    return "\n".join(out)


def write_tables(data: Mapping, report: Mapping) -> None:
    """e7v2_crossings.tex from the extract's `tables` (figs.common.write_table)."""
    t = data["tables"]["e7v2_crossings"]
    path = write_table(TABLES[0], L.table_head(NAME, [L.ANALYSIS]) + crossings_tex(t, data))
    print(f"[{NAME}] wrote {path}")


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
