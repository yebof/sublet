"""sf_e2_mu_cost: E2's total cost including the price of notice at mu / beta~ in {0.2, 0.5, 2}
(design/sim_spec_ms3.md §8.7; plan §4, part S-F).

(a)-(c): Fig. 7(b) at mu = 0.2, 0.5 and 2: A1's total cost over BL0a against H, the MaaS and spot medians over the
(lender, series) totals of alignment 1 (M19; e2/summary.json totals.<group>.<H>.<mu>.trace.a1.cost_over_bl0a) with
their bootstrap intervals, a marker at each minimizing H (best_H.<group>.<mu>.trace.a1), and the level 1
(all-fallback) as a reference line. MaaS solid, spot dashed. The three panels share the y scale. The key gives ALG*
as a plain line and the marker as its own entry ("Minimum over H"), since the lines carry no markers.

C62 (2026-11-24; the look of Fig. 7(b)): the three panels share one y axis, labeled once, with
SHARED_GUTTER_IN between them, and the light y grid; the lender lines named directly (lender_labels) instead of in
the key; the key one row above the panels (key_row, its mathtext label on the plain label's baseline) instead of
four rows in (a)'s corner; the notice H in math; H ticks thinned at half an em of the 7-pt labels; the panel titles
on their letters' baseline. The data and their extract entries are unchanged. C62 fix round: the axes' tops
sf_e2_mu_ep.title_drop_in below the letters' line (about 1.8 pt more), so that the titles' mu ends TITLE_CLEAR_PT
above the tops of (b)'s and (c)'s y spines (0.8 pt as built).

Run from code/sim: python -m figs.supp.sf_e2_mu_cost [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

from matplotlib.lines import Line2D

from figs import style
from figs.common import cli, finite
from figs.fig7_e2_e6 import (E2, GROUPS, H_TICK_GAP_PT, LABELS, MAIN_LABELS, POR, SHARED_GUTTER_IN,
                             draw_totals_panel, key_row, lender_labels, panel_titles, totals_block)
from figs.inputs import Inputs
from figs.supp.sf_e2_mu_ep import raise_texts, side_mus, title_drop_in      # C62 fix round: the title drop

NAME = "sf_e2_mu_cost"
style.register_supplementary(NAME, "W2", 2.2)


def build(inp: Inputs) -> dict:
    e2, por = inp.json(E2), inp.json(POR)
    panels = []
    for mu in side_mus(por):
        b = totals_block(e2, mu)
        panels.append({"mu": mu, "a1": {g: b[g] for g in GROUPS}, "minimizer": b["minimizer"]})
    # C62: the notice H in math, as in Fig. 7 (MAIN_LABELS) and sf_e2_mu_ep
    labels = {**LABELS, "H": MAIN_LABELS["H"], "panel": r"$\mu/\tilde{{\beta}}$ = {:g}",
              "minimum": "Minimum over $H$",
              "note": "medians over the (lender, series) totals of alignment 1 (M19); level 1 = all-fallback (BL0a)"}
    return {"panels": panels, "labels": labels, "sources": list(inp.sources)}


def y_range(panels: Sequence[Mapping]) -> tuple[float, float]:
    """One y range for the three panels: draw_totals_panel's (the medians, their intervals and the level 1, padded
    by 6% of the range) over all of them."""
    vals = [1.0] + [float(v) for p in panels for g in GROUPS for f in ("median", "ci_lo", "ci_hi")
                    for v in finite(p["a1"][g][f]) if v == v]
    lo, hi = min(vals), max(vals)
    pad = 0.06 * (hi - lo)
    return lo - pad, hi + pad


def draw(data: Mapping) -> Any:
    """C62 (the look of Fig. 7(b) and sf_e2_mu_ep): the three panels share one y axis (their y scale was shared
    already), so that its tick labels and label are drawn once; the light y grid; the lender lines labeled directly
    (lender_labels, as Fig. 7(b)); a one-row key above the panels with ALG*'s line and the minimizer's marker, as
    drawn (until C62, a four-entry key in (a)'s upper left corner, the lender line styles among them); H ticks
    thinned at half an em of the 7-pt labels (H_TICK_GAP_PT); the panel titles on their letters' baseline."""
    lab = data["labels"]
    fig = style.new_figure(NAME)
    drop = title_drop_in()                         # C62 fix round: the titles' mu clear of (b)'s and (c)'s y spines
    axes = style.panel_row(fig, (1, 1, 1), sharey=(False, True, True), top=style.MARGIN_TOP + style.LEGEND_ROW + drop,
                           left=(None, SHARED_GUTTER_IN, SHARED_GUTTER_IN))       # legend=True's top, less drop
    blocks =[{**p["a1"], "minimizer": p["minimizer"]} for p in data["panels"]]
    for i, (ax, b) in enumerate(zip(axes, blocks)):
        draw_totals_panel(ax, b, lab, h_gap_pt=H_TICK_GAP_PT)
        if i:
            ax.set_ylabel("")
            ax.tick_params(axis="y", labelleft=False)
    axes[0].set_ylim(*y_range(data["panels"]))
    for ax, b in zip(axes, blocks):               # after the final scales
        style.ygrid(ax)
        lender_labels(ax, b)
    letters, titles = panel_titles(axes, [lab["panel"].format(p["mu"]) for p in data["panels"]])     # each mu
    raise_texts(letters + titles, drop)
    # ALG* as drawn, a line without markers, and the minimizer's marker as its own entry (as built, ALG*'s entry
    # showed the marker on the line, which the panels draw only at the minimizing H)
    mark = Line2D([], [], **{**style.policy_kwargs("a1", lines=False), "label": lab["minimum"]})
    W, H = fig.get_size_inches()
    r0, r2 = style.axes_rect_in(axes[0]), style.axes_rect_in(axes[-1])
    key_row(fig, style.policy_handles(["a1"], markers=False) + [(mark, lab["minimum"])],
            x_center_in=0.5 * (r0[0] + r2[0] + r2[2]), y_center_in=H - 0.5 * style.LEGEND_ROW)   # as legend_row
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
