"""sf_e3_mu: E3 at the default point b = 8, u = 8 against the stranding price mu / beta~ (design/sim_spec_ms4.md
§8.2, §4.7, M8; plan §4, part S-F).

Cost over the shared OPT's lower bound (e3/summary.json ratios.8.8.<mu>.<tag>: ratio_LB, Q39's LB, an upper bound on
the ratio to shared OPT; siloed runs over the shared denominator) against mu / beta~ in {0.2, 0.5, 1, 2} (log), the
median over the alignments x policy seeds with its 95% bootstrap interval, dodged in x in DRAW_ORDER's slots (the OPT
bracket in a slot of its own) and drawn in two passes (ms4_lib.draw_series_layered: every line first, then every bar
and marker above all lines, so that no line runs over another series' marker; print check of 2026-10-27): Sublet
and A6 shared (solid, filled) and siloed (dashed, open; env=("sharing", "siloed")), BL2 (per-borrower by
construction). Black: the siloed OPT over the shared OPT (opt.8.8.<mu>: the median of the alignments' bracket points,
with the smallest lo and the largest hi as its bar, MS3 spec M4's bracket rule as §2.5 and §4.6 extend it), in the `opt`
style, open where the bracket is against the LP alone (`open`); the copy argument bounds it by b (design §5.5 E3, check
E3-1). labels.note states the open stars only where some drawn bracket is open (open_text, with its mu / beta~
levels; on E3 none is, and the clause as built, always present, described nothing in the figure and gave "open" a
second meaning beside the siloed forms' open markers), and its encoding clause names the series it covers, from the
modes of e3/summary.json meta.tags (sf_e3_util.sharing_modes and encoding_text: on E3 "dashed lines with open circles
and hexagons: the siloed forms of Sublet and Two-timescale PD; Per-borrower ski rental is per-borrower by
construction"). The y axis is log2 over common.ratio_log2_axis's range, labeled at the coarsest ladder of mantissas per
octave of sf_e3_util.RATIO_LADDERS that puts at least Y_MIN_TICKS ticks on the axis (sf_e3_util.ratio_axis: 1, 1.25,
1.5, 2 on E3; the powers of two alone labeled only 1 and 2, with every value between them), fixed before the legend's
headroom, so that no tick is labeled in the headroom; the level 1 is a reference line. Corner legend (the policies, the
bracket as "Siloed OPT", and env_handles("sharing")) on headroom above the data (common.legend_headroom). labels.note
says that intervals and brackets narrower than the markers are hidden (LABELS["hidden"]).

MS6 C47 (design/ms6_spec.md M2, M4): "Sublet" above is the summary's tag of the one-way guard around the lagged BL5
at MS4's allowance, drawn as the registry key sublet_ms4 ("Lagged RetroRenting + one-way guard ($B_0=10\\%$ BL0a)"),
its siloed form as the series id "sublet_ms4:siloed" in the key's own filled markers with the dashed sharing line
(sf_e3_util.SUBLET_SILOED; the summary's recorded keys mapped by sf_e3_util.RECORDED). That label alone (3.1 in at
7 pt) is wider than the panel, so the legend left the corner: its entries (the three policies, "Siloed OPT" and the
two line styles) stand in at most LEGEND_ROWS rows above the panel, each filled in order as far as the width allows
(ms4_lib.split_rows, legend_rows_above), in the reserve of LEGEND_RESERVE column-aligned rows
(panel_row(..., top=legend_reserve_top(LEGEND_RESERVE))), and the y axis has no legend headroom. C59 (RC19(3)): the
guard's label in words takes two lines, and the figure is 2.4 in high (2.2 in before). C62 (7-pt text): the guard's
two-line label and Two-timescale PD fill the first row, the other four entries the second, in the reserve of two rows
(three at 9 pt), so the axes are 1.48 in high (1.13 in at 9 pt), which spreads the three lines that run within 9% of
each other near 2; the legend samples are LEGEND_HANDLE em long, with the siloed sample's dashes centered on it.

Run from code/sim: python -m figs.supp.sf_e3_mu [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.lines import Line2D

from figs import style
from figs.common import align_baselines, cli, finite, maybe, need
from figs.inputs import Inputs
from figs.supp.ms4_lib import (agg_point, centered_dash_pairs, dodge, draw_series_layered, finite_values, grid_counts,
                               legend_reserve_top, legend_rows_above, level_axis, levels_of, runs_text, series_key,
                               series_over, split_rows, tag_of)
from figs.supp.sf_e3_util import (E3, RECORDED, SUBLET_SILOED, and_join, encoding_text, env_of, ratio_axis,
                                  sharing_modes)

NAME = "sf_e3_mu"
KEYS = style.SUPP_POLICIES_MS4[NAME]          # sublet_ms4, a6, a6_siloed, bl2, opt
# C47 (design/ms6_spec.md M2, M4): the drawn series, sublet_ms4's siloed form the key in the sharing line style
# (sf_e3_util.SUBLET_SILOED)
SERIES = ("sublet_ms4", SUBLET_SILOED, "a6", "a6_siloed", "bl2")
# the dodge slots, left to right (print check of 2026-10-27): no neighbours within 15% of each other on E3 (as built,
# bl2, a6_siloed, a6, sublet_siloed, sublet: BL2 and A6 siloed, 3.7-3.8% apart, in neighbouring slots, the hexagon
# covering the triangle's corner at every mu / beta~)
DRAW_ORDER = ("a6_siloed", "a6", "bl2", "sublet_ms4", SUBLET_SILOED)
LEGEND_KEYS = ("sublet_ms4", "a6", "bl2")
LEGEND_ROWS = 2                                # C47: the legend rows above the panel (legend_rows_above), at most ...
LEGEND_RESERVE = 2                             # ... in the reserve of this many column-aligned rows. C62 (7-pt text):
#                                                the guard's label in words on two lines (split_rows, wrap_wide) beside
#                                                Two-timescale PD, then the other four entries in one row: three lines,
#                                                0.38 in on E3, in the 0.42-in reserve of two rows (C59 at 9 pt: three
#                                                rows in a reserve of three, 0.63 in, which left 0.25 in of white above
#                                                the axes at 7 pt); the axes gain those 0.21 in (1.48 in high)
style.register_supplementary(NAME, "W1", 2.4)                 # C59: was 2.2 in (style.py registers the same)
LEGEND_HANDLE = 12.2 / style.TICK_PT          # C62: the samples' length (em), three whole 3.0-pt dashes and their two
#                                                1.6-pt gaps (12.2 pt; ms4_lib.centered_dash_pairs), as built 1.4 em
#                                                (ms4_lib.LEGEND_HANDLE_SHORT), which cut the siloed sample's last dash
Y_MIN_TICKS = 4                                # y: the coarsest ladder with this many labeled ticks (not in §8.2)
LABELS = {"x": r"Stranding price $\mu/\tilde{\beta}$", "y": "Cost / shared OPT", "opt": "Siloed OPT",
          # C47 (print check of the gate): the y values in words (as relabeled "ratio_LB", "Q39's")
          "note": "b = {b:g}, u = {u:g}; medians over {runs} with 95% bootstrap intervals; y: cost over a lower "
                  "bound on the shared OPT, so an upper bound on cost / shared OPT; Siloed OPT: siloed OPT / shared "
                  "OPT, the median of the alignments' bracket points with [smallest lo, largest hi]",
          "hidden": "intervals and brackets narrower than the markers are hidden"}


def default_point(e3: Mapping) -> tuple[float, float]:
    b, u = need(e3, "meta", "grid", "default_point", what=E3)
    return float(b), float(u)


def open_text(opt: Mapping) -> str | None:
    """The note's clause on the open stars: the mu / beta~ levels whose bracket is drawn (a point) and is against the
    LP alone (`open`); None where none is."""
    mus = [mu for mu, pt, op in zip(opt["mu"], opt["point"], opt["open"]) if op and pt is not None]
    if not mus:
        return None
    star = "an open star: a bracket" if len(mus) == 1 else "open stars: brackets"
    return f"{star} against the LP alone (mu/beta~ = {and_join([format(m, 'g') for m in mus])})"


def build(inp: Inputs) -> dict:
    e3 = inp.json(E3)
    b, u = default_point(e3)
    bk, uk = format(b, "g"), format(u, "g")
    meta_tags = need(e3, "meta", "tags", what=E3)
    tags = tag_of(meta_tags, SERIES, E3, drawn=RECORDED)          # C47: the recorded keys to the drawn series
    modes = sharing_modes(meta_tags, tags, SERIES)
    block = need(e3, "ratios", bk, uk, what=E3)
    levels = levels_of(block, f"{E3} ratios.{bk}.{uk}")
    out = {key: series_over(block, levels, tags[key], agg_point, "mu") for key in SERIES}
    opt = {"mu": [], "point": [], "lo": [], "hi": [], "exact": [], "open": [], "n_alignments": [], "note": []}
    for mu, mk in levels:
        o, note = maybe(e3, "opt", bk, uk, mk)
        o = o if isinstance(o, Mapping) else {}
        pt = o.get("point_median")
        for f, v in zip(opt, (mu, pt, o.get("lo_min"), o.get("hi_max"), bool(o.get("exact")), bool(o.get("open")),
                              o.get("n_alignments"),
                              note or (None if pt is not None else o.get("point_median_note") or "null"))):
            opt[f].append(v)
    runs = runs_text(*grid_counts(need(e3, "meta", "grid", what=E3), f"{E3} meta.grid"))
    note = "; ".join([LABELS["note"].format(b=b, u=u, runs=runs)]
                     + [t for t in (open_text(opt), encoding_text(modes), LABELS["hidden"]) if t])
    out.update({"opt": opt, "b": b, "u": u, "mu_levels": [x for x, _ in levels], "tags": tags, "sharing": modes,
                "labels": {**LABELS, "note": note},
                "meta": {"git_revision": need(e3, "meta", "git_revision", what=E3),
                         "reduced": bool(e3["meta"].get("reduced"))},
                "sources": list(inp.sources)})
    return out


def draw_opt(ax, opt: Mapping, i: int, n: int) -> None:
    """The siloed/shared OPT bracket: the point in the `opt` style (white face where `open`) with its [lo, hi] bar,
    dodged as series i of n (its own slot, as Fig. 4(c)'s brackets: undodged it sat on A6's marker and bar)."""
    y, lo, hi = (finite(opt[f]) for f in ("point", "lo", "hi"))
    x = dodge(opt["mu"], i, n)
    ok = np.isfinite(x) & np.isfinite(lo) & np.isfinite(hi) & np.isfinite(y)
    if ok.any():
        style.errorbars(ax, "opt", x[ok], y[ok], lo[ok], hi[ok])
    is_open = np.array(opt["open"], dtype=bool)
    for sel, face in ((~is_open, None), (is_open, "white")):
        if (sel & np.isfinite(y)).any():
            kw = {} if face is None else {"markerfacecolor": face}
            style.scatter_policy(ax, "opt", x[sel], y[sel], label="_nolegend_", **kw)


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    (ax,) = style.panel_row(fig, (1,), top=legend_reserve_top(LEGEND_RESERVE))       # C47: the legend above
    order = [k for k in DRAW_ORDER if k in data]
    n = len(order) + 1                                  # the policies and the OPT brackets, each in its own x slot
    draw_series_layered(ax, [(series_key(s), data[s], i, env_of(s)) for i, s in enumerate(order)], "mu", n=n)
    draw_opt(ax, data["opt"], n - 1, n)
    level_axis(ax, data["mu_levels"])
    v = finite_values(*(data[k][f] for k in order for f in ("median", "ci_lo", "ci_hi")),
                      *(data["opt"][f] for f in ("point", "lo", "hi")))
    v = v[v > 0]
    lo, hi = (float(min(v.min(), 1.0)), float(max(v.max(), 1.0))) if v.size else (1.0, 2.0)
    ratio_axis(ax, lo, hi, min_ticks=Y_MIN_TICKS)
    style.reference_line(ax, y=1.0)
    style.ygrid(ax)
    ax.set_xlabel(lab["x"])
    ax.set_ylabel(lab["y"])
    opt_handle = Line2D([], [], **{**style.policy_kwargs("opt", lines=False), "label": lab["opt"]})
    # C47: sublet_ms4's label (3.1 in at 7 pt) is wider than the panel, so the legend leaves the corner (as built, on
    # headroom above the data) for rows above the panel, each filled in order as far as the figure's width allows;
    # C62: the dashes of the siloed sample centered on it, mathtext labels on their neighbors' baseline
    pairs = centered_dash_pairs(style.policy_handles(LEGEND_KEYS) + [(opt_handle, lab["opt"])]
                                + style.env_handles("sharing"), LEGEND_HANDLE)
    rows = split_rows(fig, pairs, max_rows=LEGEND_ROWS, handlelength=LEGEND_HANDLE)
    for leg in legend_rows_above(fig, rows, n_rows=LEGEND_RESERVE, handlelength=LEGEND_HANDLE):
        align_baselines(leg.get_texts())
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
