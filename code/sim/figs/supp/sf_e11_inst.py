"""sf_e11_inst: E11 per instance (design/sim_spec_ms3.md §8.7; design/figure_plan.md §4, part S-F).

From code/sim/out/e11/summary.json (the Q44 Tier 1 rerun, E11):
(a) the median cost over the cheapest of BL1, BL2 and BL5 under the trace lender (D1.<I>.r_best) with its 95%
    bootstrap interval, per instance I1-I4, the policies of Fig. 3 dodged;
(b) the largest median cost over all-fallback across the stress lenders (D2.<I>.W0) with the interval of the median
    at the stress mode that attains it (D2.<I>.modes.<argmax_mode>.r0.<tag>.median_ci95);
(c) The median cost over all-fallback of the lagged RetroRenting-style rule with the one-way guard (E11's tag BL5-G,
    bl5_g1; D2.<I>.modes.<mode>.r0.BL5-G) against the realized announcements per site-day (intensity, tuning cells
    included, M37) on I1-I3, one line per instance (I4 is Fig. 3(b)), all in its style (color and filled marker) and
    told apart by line style (I1 solid, I2 dashed, I3 dotted), each named at its left end (the lines meet near 1 at
    the right); every tag of every instance is in the extract (``c_all``) and in E11's tables.md.
Measurements; scope: one-day instances, alpha = 0.40, 1-min routing, medians over held-out cells. The legend is
Fig. 3's (figs.fig3_e11.legend_entries): the three (inner, guarded) pairs, Two-timescale PD, per-borrower ski rental
and the note style.GUARD_PAIR_NOTE, "paired, filled: + one-way guard (Algorithm 1 without projection)" (C47: the
pair's filled marker, since two unpaired entries have filled markers too), in two rows (C46, design/ms6_spec.md M5). The
policies of (a) and (b) are dodged in the legend's order, each guarded configuration just right of its inner policy,
so that Greedy + one-way guard and per-borrower ski rental, which share a filled down triangle in greyscale, are told
apart by their places: the first follows Greedy renting's open up triangle, the second ends the group.

MS6 C46 (design/ms6_spec.md M2, M4, M5): the guarded series are their configurations' keys (BL5-G bl5_g1, PS-G a7_g1,
BL1-G bl1_g1, BL5 bl5_lag); the data tags are E11's.

C47 (print check of the gate, U46):
- (a), (b): the uniform slots of the dodge (DODGE ±0.40, about 3.6 pt apart) are narrower than the markers (a filled
  thin diamond beside an open diamond needs about 4.7 pt), so an inner policy and its guarded configuration at one
  height (equal on I1 and I4, where the guard did not change the run) touched or overprinted. Each instance's markers
  now start at the uniform slots and are moved apart, in the legend's order, only where a marker or interval bar
  would come closer than CLEAR_PT to another policy's (on the marker outlines at the panel's final scale, _positions);
  neighbours keep at least MIN_STEP_PT between them. The group stays inside ±DODGE (StyleError if it cannot).
- (c): each instance's interval bars took its line's dash pattern (I2 dashed, I3 dotted), since the three lines share
  one color and marker and two bars of different instances can stand 1 pt apart (I2 and I3 at about 14
  announcements per site-day). Replaced in C62's fix round (below).
- labels.caption: a caption draft (the supplement's), with the dodge order, (b)'s worst stress lender, (c)'s policy,
  the pairs that are equal and where I4 is; labels.equal lists those pairs per panel.

C62 (the type scale of the caption; figures high-end, informative, readable): the margins of style; Fig. 3's legend
keeps its two rows (fig3_e11: one row needs 8.6 in at 7 pt); (c)'s log x axis has no minor ticks (labeled at 3, 10,
30, ...) and its y ticks are 0.1 apart (C_Y_BINS; eight labels 0.05 apart at MaxNLocator's default). The extract is
unchanged.
C62 fix round (the supplement's critic): (c)'s interval bars are solid, UNCERTAINTY_PT wide, in the series color, the
dashes and dots only on the connecting lines (I2's dashed and I3's dotted bars read as reference or grid lines: I3's
near 14 and 45 announcements per site-day run from 0.74 to 0.98 with no marker on most of their length). Where two
lines' solid bars that show beyond their markers overlap in height and stand closer than BAR_SEP_PT (I2 and I3 near
14, 1.0 pt apart), they are drawn BAR_SEP_PT apart about their mean x, each at most BAR_SHIFT_MAX_PT (0.4 pt there)
from its point (_bar_x); markers and lines stay at the points' x. (a) and (b), which have no x ticks, set the instance
names one tick length further down, so that the row's tick labels and x labels share one baseline as printed ((a)'s and
(b)'s sat 3 pt above (c)'s). Only labels.caption changes in the extract (no interval "in its line's style").

Run from code/sim: ``python -m figs.supp.sf_e11_inst [--from-extract [JSON]]`` (figs.common.cli).
"""
from __future__ import annotations

import sys

import numpy as np
from matplotlib.markers import MarkerStyle
from matplotlib.path import Path
from matplotlib.ticker import MaxNLocator, NullLocator

from figs import fig3_e11 as f3
from figs import style
from figs.common import AGREE_SAME, ci_of, cli, finite, text_width_in
from figs.inputs import Inputs

NAME = "sf_e11_inst"
WIDTH, HEIGHT = "W2", 2.5
SUMMARY = "code/sim/out/e11/summary.json"
INSTANCES = ("I1", "I2", "I3", "I4")
C_INSTANCES = ("I1", "I2", "I3")
TAG_KEY = {"BL5-G": "bl5_g1", "PS-G": "a7_g1", "BL1-G": "bl1_g1", "PS": "a7", "A6": "a6", "BL5": "bl5_lag",
           "BL1": "bl1", "BL2": "bl2"}                  # C46 (M2-M4): the configuration keys of Algorithm 1's defaults
GUARDED = ("bl5_g1", "a7_g1", "bl1_g1")
C_KEY = "bl5_g1"             # (c): the policy of the instance lines
KEYS = tuple(TAG_KEY.values())
# (a), (b): dodged in the legend's order (fig3_e11.legend_entries), each guarded configuration right of its inner policy
DODGE_ORDER = tuple(k for pair in f3.PAIRS for k in pair) + f3.UNPAIRED
DODGE = 0.40                 # half-width of the dodge around each instance (category units)
CLEAR_PT = 0.5               # C47: least gap between two policies' markers and interval bars in (a), (b) (_positions)
MIN_STEP_PT = 2.0            # C47: least horizontal step between neighbours of an instance's group, so the order shows
OUTLINE_STEP_PT = 0.2        # C47: sampling step along the outlines of markers and bars (_boundary)
C_STYLES = ("-", "--", ":")  # (c), per line in C_INSTANCES order: the line style (all in C_KEY's style)
LABEL_GAP_PT = 4.0           # (c): gap between an instance's name and its line's first point
LABEL_PAD_PT = 2.0           # (c): room left of the widest name, inside the axes
C_Y_BINS = 4                 # (c): C62, at most this many y steps (0.1 apart; MaxNLocator's default put eight labels
#                              0.05 apart on the 1.6-in axis)
BAR_SEP_PT = 1.8             # (c): C62 fix round, least distance between the centers of two lines' bars that overlap in
#                              height (two UNCERTAINTY_PT bars with twice their width of white between them; _bar_x)
BAR_SHIFT_MAX_PT = 1.0       # (c): C62 fix round, the farthest a bar is drawn from its point's x (_bar_x)

style.register_supplementary(NAME, WIDTH, HEIGHT)


def collect(inp: Inputs) -> dict:
    S = inp.json(SUMMARY)
    a, b = {}, {}
    for tag, key in TAG_KEY.items():
        ra, rb = {"tag": tag, "instance": [], "median": [], "ci_lo": [], "ci_hi": [], "n": []}, \
                 {"tag": tag, "instance": [], "W0": [], "argmax_mode": [], "ci_lo": [], "ci_hi": [], "n": []}
        for I in INSTANCES:
            v = S["D1"][I]["r_best"][tag]
            m, (lo, hi) = v.get("median"), ci_of(v)
            ra["instance"].append(I)
            ra["median"].append(m)
            ra["ci_lo"].append(lo)
            ra["ci_hi"].append(hi)
            ra["n"].append(S["D1"][I]["r_best"][tag]["n"])
            w = S["D2"][I]["W0"][tag]
            mode = w["argmax_mode"]
            r = S["D2"][I]["modes"][mode]["r0"][tag]
            if r["median"] != w["W0"]:
                raise style.StyleError(f"D2.{I}.W0.{tag} = {w['W0']} is not the median at its argmax mode {mode}")
            rb["instance"].append(I)
            rb["W0"].append(w["W0"])
            rb["argmax_mode"].append(mode)
            rb["ci_lo"].append(r["median_ci95"][0])
            rb["ci_hi"].append(r["median_ci95"][1])
            rb["n"].append(r["n"])
        a[key], b[key] = ra, rb
    c, c_all = {}, {}
    for I in INSTANCES:
        modes = list(S["D2"][I]["modes"])
        x = {m: S["intensity"][f"{I}|{m}"]["announcements_per_site_day"] for m in modes}
        order = sorted(modes, key=lambda m: x[m])
        c_all[I] = {"modes": order, "x": [x[m] for m in order], "tags": {}}
        for tag in S["D2"][I]["modes"][order[0]]["r0"]:
            rs = [S["D2"][I]["modes"][m]["r0"][tag] for m in order]
            c_all[I]["tags"][tag] = {"median": [r["median"] for r in rs],
                                     "ci_lo": [r["median_ci95"][0] for r in rs],
                                     "ci_hi": [r["median_ci95"][1] for r in rs]}
        if I in C_INSTANCES:
            t = c_all[I]["tags"]["BL5-G"]
            c[I] = {"modes": order, "x": c_all[I]["x"], "median": t["median"], "ci_lo": t["ci_lo"],
                    "ci_hi": t["ci_hi"]}
    out = {"git_revision": S["meta"]["git_revision"], "instances": list(INSTANCES), "a": a, "b": b, "c": c,
           "c_all": c_all, "labels": {
               "a_x": "Instance", "a_y": "Trace cost / best renting",
               "b_x": "Instance", "b_y": "Stress cost / all-fallback",
               "c_x": "Announcements per site-day", "c_y": "Cost / all-fallback",
               "c_policy": style.POLICIES[C_KEY].label,        # (c)'s lines: the legend's filled marker, the caption
               "guarded": {k: style.POLICIES[k].label for k in GUARDED},
               "legend": [lab for _, lab in f3.legend_entries()],
               "c_lines": {I: I for I in C_INSTANCES},
               "status": "measurements; one-day instances I1-I4, alpha = 0.40, 1-min routing, medians over held-out "
                         "cells",
           }}
    # C47: the (inner, guarded) pairs that are equal (median and interval) per panel and instance, and the caption
    out["labels"]["equal"] = {p: _equal_pairs(out[p], f) for p, f in (("a", "median"), ("b", "W0"))}
    out["labels"]["caption"] = caption(out)
    return out


def _same(u, v) -> bool:
    return u is not None and v is not None and abs(u - v) <= 1e-12 * max(1.0, abs(v))


def _equal_pairs(ser: dict, field: str) -> dict:
    """{"inner|guarded": [instances]} of the pairs of f3.PAIRS whose median and interval are equal at an instance (the
    guarded run was the inner policy's, up to its statistics)."""
    out = {}
    for inner, guarded in f3.PAIRS:
        s, g = ser[inner], ser[guarded]
        at = [I for i, I in enumerate(s["instance"])
              if all(_same(s[k][i], g[k][i]) for k in (field, "ci_lo", "ci_hi"))]
        if at:
            out[f"{inner}|{guarded}"] = at
    return out


CAPTION = ("The policies of Fig.~\\ref{{fig:guard}} per one-day instance I1--I4 ($\\alpha=0.40$, 1-min routing; "
           "medians over the held-out cells with 95\\% bootstrap intervals). (a) Cost under the trace lender over the "
           "cheapest of greedy renting, per-borrower ski rental and the lagged RetroRenting-style rule. (b) The worst "
           "stress cost: the largest median cost over all-fallback across the stress lenders, with its interval at the "
           "lender that attains it. In (a) and (b) the markers of an instance run from left to right in the legend's "
           "column order, each guarded configuration right of its inner policy, so Greedy + one-way guard comes before "
           "Two-timescale PD and per-borrower ski rental ends the group; markers that would touch are moved apart. "
           "{equal}(c) {policy}: cost over all-fallback against the realized reclaim announcements per site-day (over "
           "all cells of the lender), one point per lender and one line per instance (I1 solid, I2 dashed, I3 dotted); "
           "I4 is Fig.~\\ref{{fig:guard}}(b).")


def caption(d: dict) -> str:
    """labels.caption (C47): the caption draft, with the equal pairs of labels.equal named by their inner policies."""
    parts = []
    for p in ("a", "b"):
        eq = d["labels"]["equal"].get(p) or {}
        if eq:
            names = [f"{style.POLICIES[k.split('|')[0]].label} ({', '.join(at)})" for k, at in eq.items()]
            parts.append(("for " + ", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1
                          else "for " + names[0]) + f" in ({p})")
    equal = ("An inner policy equals its guarded configuration " + " and ".join(parts) + ". ") if parts else ""
    return CAPTION.format(equal=equal, policy=d["labels"]["c_policy"])


# ---------------------------------------------------------------------------------------------------------------
def _outline_pt(key: str) -> np.ndarray:
    """A policy's drawn marker outline (n x 2, pt, about its center, counterclockwise): its convex path at markersize,
    each edge moved out by half the edge's width and the corners mitered (the stroke's outer side)."""
    p = style.policy(key)
    ms = MarkerStyle(p.marker)
    path = ms.get_path().transformed(ms.get_transform())
    v = path.vertices if path.codes is None else path.vertices[path.codes != Path.CLOSEPOLY]
    v = np.unique(np.round(v, 9), axis=0)
    v = v[np.argsort(np.arctan2(v[:, 1] - v[:, 1].mean(), v[:, 0] - v[:, 0].mean()))] * p.markersize
    e = np.roll(v, -1, axis=0) - v                                   # edge i from vertex i to vertex i + 1
    n = np.column_stack([e[:, 1], -e[:, 0]]) / np.hypot(e[:, 0], e[:, 1])[:, None]     # outward normals (ccw)
    n_in = np.roll(n, 1, axis=0)                                     # the normal of the edge that ends at vertex i
    half = 0.5 * style.MARKER_EDGE_PT
    return v + half * (n + n_in) / (1.0 + np.sum(n * n_in, axis=1))[:, None]


def _boundary(poly: np.ndarray) -> np.ndarray:
    """Points along a closed polygon's edges, at most OUTLINE_STEP_PT apart."""
    pts = []
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / OUTLINE_STEP_PT)))
        pts.append(a + (np.arange(n) / n)[:, None] * (b - a))
    return np.vstack(pts)


def _need_pt(P: np.ndarray, Q: np.ndarray) -> float:
    """The least shift (pt) of the shape Q to the right of the shape P (both outline points, pt, at their x = 0) such
    that every point of Q lies at least CLEAR_PT right of every point of P at about its height (0 if none is)."""
    dy = Q[None, :, 1] - P[:, None, 1]
    close = np.abs(dy) < CLEAR_PT
    if not close.any():
        return 0.0
    dx = P[:, None, 0] - Q[None, :, 0] + np.sqrt(np.maximum(CLEAR_PT ** 2 - dy ** 2, 0.0))
    return max(0.0, float(dx[close].max()))


def _positions(ax, order: list, vals: dict, n_inst: int) -> dict:
    """C47: the x of every policy of `order` at each instance (data units). An instance's markers start at the uniform
    slots of ±DODGE; where a marker or interval bar (an UNCERTAINTY_PT-wide rectangle) of one policy would come closer
    than CLEAR_PT to another's (on the y scale already set), the later policies move right, neighbours keep at least
    MIN_STEP_PT apart, and if the group then passes +DODGE it is pushed back from the right. The order is kept;
    StyleError if the group cannot fit inside ±DODGE."""
    to_pt = style.BP_PER_IN / ax.figure.dpi
    tr = ax.transData.transform
    unit = (tr((1.0, 0.0))[0] - tr((0.0, 0.0))[0]) * to_pt          # pt per category
    half = DODGE * unit
    slots = dict(zip(order, np.linspace(-half, half, len(order))))
    w = 0.5 * style.UNCERTAINTY_PT
    out = {k: np.full(n_inst, np.nan) for k in order}
    for i in range(n_inst):
        ks, shapes = [], []
        for k in order:
            y, lo, hi = (float(v[i]) for v in vals[k])
            if not np.isfinite(y):
                continue
            y_pt = tr((0.0, y))[1] * to_pt
            parts = [_boundary(_outline_pt(k)) + [0.0, y_pt]]
            if np.isfinite(lo) and np.isfinite(hi):
                lo_pt, hi_pt = tr((0.0, lo))[1] * to_pt, tr((0.0, hi))[1] * to_pt
                if hi_pt - lo_pt > OUTLINE_STEP_PT:
                    parts.append(_boundary(np.array([[-w, lo_pt], [w, lo_pt], [w, hi_pt], [-w, hi_pt]])))
            ks.append(k)
            shapes.append(np.vstack(parts))
        m = len(ks)
        need = np.zeros((m, m))
        for a in range(m):
            for b in range(a + 1, m):
                need[a, b] = max(_need_pt(shapes[a], shapes[b]), MIN_STEP_PT if b == a + 1 else 0.0)
        x = [slots[k] for k in ks]
        for b in range(m):                                  # from the uniform slots, moved right where needed
            x[b] = max([x[b]] + [x[a] + need[a, b] for a in range(b)])
        if m and x[-1] > half + 1e-9:                       # pushed back from the right end
            x[-1] = half
            for a in range(m - 2, -1, -1):
                x[a] = min([x[a]] + [x[b] - need[a, b] for b in range(a + 1, m)])
            if x[0] < -half - 1e-6:
                raise style.StyleError(f"{NAME}: the markers of instance {i + 1} need {x[-1] - x[0]:.1f} pt, more "
                                       f"than the dodge's {2 * half:.1f} pt")
        for k, xv in zip(ks, x):
            out[k][i] = i + xv / unit
    return out


def _dodged(ax, ser: dict, ykey: str, instances: list) -> None:
    order = [k for k in DODGE_ORDER if k in ser]
    vals = {k: (finite(ser[k][ykey]), finite(ser[k]["ci_lo"]), finite(ser[k]["ci_hi"])) for k in order}
    ax.set_xlim(-0.6, len(instances) - 0.4)
    # the y scale first: drawn at the uniform slots, autoscaled and fixed (C47), then drawn at _positions
    offs = np.linspace(-DODGE, DODGE, len(order))
    probe = []
    for off, key in zip(offs, order):
        xs = np.arange(len(instances)) + off
        probe += [style.errorbars(ax, key, xs, *vals[key]), style.scatter_policy(ax, key, xs, vals[key][0])]
    ax.autoscale_view()
    ax.set_ylim(ax.get_ylim())
    for art in probe:
        art.remove()
    pos = _positions(ax, order, vals, len(instances))
    for key in order:
        style.errorbars(ax, key, pos[key], *vals[key])
        style.scatter_policy(ax, key, pos[key], vals[key][0])
    ax.set_xticks(range(len(instances)))
    ax.set_xticklabels(instances)
    # no ticks; C62 fix round: the names as far below the axis as (c)'s tick labels, so that the row's tick labels and
    # x labels share one baseline ((a)'s and (b)'s sat one tick length, 3 pt, high)
    rc = style.mpl.rcParams
    ax.tick_params(axis="x", length=0, pad=rc["xtick.major.pad"] + rc["xtick.major.size"])
    for i in range(1, len(instances)):
        ax.axvline(i - 0.5, color=style.GRID_GREY, linewidth=style.GRID_PT, zorder=0.5)
    ax.yaxis.set_major_formatter(style.PLAIN)


def _bar_x(ax, C: dict) -> dict:
    """(c), C62 fix round: the x (data) at which each point's interval bar is drawn, on the panel's final scales. A bar
    stands at its point's x, except where bars of two lines that show beyond their markers (by more than CLEAR_PT)
    overlap in height and stand closer than BAR_SEP_PT (I2 and I3 at about 14 announcements per site-day, 1.0 pt
    apart, whose solid bars would merge into one): each such group of bars is spread to BAR_SEP_PT apart about its mean
    x, in the order of the points' x (C's order on ties). The markers and lines stay at the points' x. StyleError if a
    bar would move more than BAR_SHIFT_MAX_PT from its point."""
    k = style.BP_PER_IN / ax.figure.dpi
    reach = float(np.abs(_outline_pt(C_KEY)[:, 1]).max())          # the marker's reach above and below its point (pt)
    pts = []                                                        # (instance, index, x pt, lo pt, hi pt, y px)
    for I, s in C.items():
        for i, (x, y, lo, hi) in enumerate(zip(s["x"], s["median"], s["ci_lo"], s["ci_hi"])):
            (xp, yp), (_, lp), (_, hp) = ax.transData.transform([(x, y), (x, lo), (x, hi)]) * k
            if max(hp - yp, yp - lp) > reach + CLEAR_PT:
                pts.append((I, i, float(xp), float(lp), float(hp), float(yp / k)))
    group = list(range(len(pts)))

    def root(a: int) -> int:
        while group[a] != a:
            a = group[a]
        return a
    for a in range(len(pts)):
        for b in range(a + 1, len(pts)):
            A, B = pts[a], pts[b]
            if A[0] != B[0] and abs(A[2] - B[2]) < BAR_SEP_PT and min(A[4], B[4]) > max(A[3], B[3]) - CLEAR_PT:
                group[root(b)] = root(a)
    out = {I: [float(v) for v in s["x"]] for I, s in C.items()}
    order = list(C)
    groups: dict = {}
    for a in range(len(pts)):
        groups.setdefault(root(a), []).append(a)
    for g in groups.values():
        if len(g) < 2:
            continue
        g.sort(key=lambda a: (pts[a][2], order.index(pts[a][0])))
        xs = [pts[a][2] for a in g]
        new = [xs[0]]
        for xv in xs[1:]:
            new.append(max(xv, new[-1] + BAR_SEP_PT))
        new = [v + float(np.mean(xs) - np.mean(new)) for v in new]
        for a, v in zip(g, new):
            I, i, xp, _, _, y_px = pts[a]
            if abs(v - xp) > BAR_SHIFT_MAX_PT + 1e-9:
                raise style.StyleError(f"{NAME} (c): the bar of {I} at {C[I]['x'][i]} would stand {abs(v - xp):.2f} pt "
                                       f"from its point (at most {BAR_SHIFT_MAX_PT} pt)")
            out[I][i] = float(ax.transData.inverted().transform((v / k, y_px))[0])
    return out


def _instance_lines(ax, C: dict, names: dict) -> None:
    """(c): one line of C_KEY per instance, in its style (color, filled marker), told apart by line style (C_STYLES),
    each named at its left end, where the lines are furthest apart (they meet near 1 at the right): left of its first
    point, or just above or below that point where a label there would cross another line or interval bar. The x
    axis starts far enough left for the names. C62 fix round: every interval bar solid, UNCERTAINTY_PT wide, in the
    series color (dashed and dotted bars read as reference lines), at _bar_x, drawn once the scales are final."""
    sub = style.policy(C_KEY)
    drawn = {}
    for (I, s), ls in zip(C.items(), C_STYLES):
        drawn[I] = style.plot_policy(ax, C_KEY, s["x"], s["median"], linestyle=ls)
    style.log_axis(ax, "x", ticks=[3, 10, 30, 100, 300])
    ax.xaxis.set_minor_locator(NullLocator())       # C62: labeled at 3, 10, 30, ...; no comb of minor ticks
    lo = min(v for s in C.values() for v in s["ci_lo"])
    hi = max(v for s in C.values() for v in s["ci_hi"])
    ax.set_ylim(lo - 0.12 * (hi - lo), hi + 0.04 * (hi - lo))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=C_Y_BINS, steps=[1, 2, 5, 10]))   # C62: 0.1, not 0.05, apart
    # x limits: the right one as before, the left one so that each name fits left of its line's first point
    x_hi = max(v for s in C.values() for v in s["x"]) * 1.4
    w_pt = style.axes_rect_in(ax)[2] * style.BP_PER_IN
    L, H = np.log10(min(v for s in C.values() for v in s["x"]) / 1.4), np.log10(x_hi)
    for I, s in C.items():
        r = LABEL_GAP_PT + text_width_in(ax.figure, names[I]) * style.BP_PER_IN + LABEL_PAD_PT
        L = min(L, (np.log10(s["x"][0]) * w_pt - r * H) / (w_pt - r))      # (log x0 - L) w / (H - L) >= r
    ax.set_xlim(10 ** L, x_hi)
    bx = _bar_x(ax, C)                  # C62 fix round: solid bars in the series color, apart where they would merge
    for I, s in C.items():
        style.errorbars(ax, C_KEY, bx[I], s["median"], s["ci_lo"], s["ci_hi"])
    rend = ax.figure.canvas.get_renderer()
    k = ax.figure.dpi / style.BP_PER_IN
    for I, s in C.items():
        others = [Path(ax.transData.transform(np.column_stack([t["x"], t["median"]]))) for J, t in C.items() if J != I]
        others += [Path(ax.transData.transform([[x, a], [x, b]])) for J, t in C.items() if J != I
                   for x, a, b in zip(bx[J], t["ci_lo"], t["ci_hi"])]
        for va, dy in (("center", 0.0), ("bottom", 0.5 * sub.markersize), ("top", -0.5 * sub.markersize)):
            t = style.direct_label(ax, C_KEY, s["x"][0], s["median"][0], names[I], dx=-LABEL_GAP_PT, dy=dy,
                                   ha="right", va=va)
            bb = t.get_window_extent(rend).padded(0.5 * k)
            if not any(o.intersects_bbox(bb, filled=False) for o in others):
                break
            t.remove()
        else:                                           # every line must be named: the lines differ only by style
            raise style.StyleError(f"sf_e11_inst (c): no clear place for the name {names[I]!r} at its line's start")


def draw(data: dict):
    lab = data["labels"]
    fig = style.new_figure(NAME)
    axes = style.panel_row(fig, (1, 1, 1), legend=2)
    a, b, c = axes
    style.reference_line(a, y=1.0)
    _dodged(a, data["a"], "median", data["instances"])
    a.set_xlabel(lab["a_x"])
    a.set_ylabel(lab["a_y"])
    style.reference_line(b, y=1.0)
    _dodged(b, data["b"], "W0", data["instances"])
    b.set_xlabel(lab["b_x"])
    b.set_ylabel(lab["b_y"])
    style.reference_line(c, y=1.0)
    _instance_lines(c, data["c"], lab["c_lines"])
    c.yaxis.set_major_formatter(style.PLAIN)
    c.set_xlabel(lab["c_x"])
    c.set_ylabel(lab["c_y"])
    style.panel_letters(axes)
    style.legend_row(fig, [], extra=f3.legend_entries(), rows=2)                 # Fig. 3's (C46, M5)
    return fig


def main(argv=None) -> dict:
    return cli(NAME, collect, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
