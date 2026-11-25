"""sf_e1_sched: E1(b) under the `trace` and `eager` schedules and at the mu default points (design/sim_spec_ms3.md
§8.7; plan §4, part S-F).

(a) ALG / LB against rho* under `trace` (e1/summary.json ratios.trace.<rho>.1.<tag>): the median of ratio_LB
    (Q39's LB) with its median_ci95 bars and a black tick at the median of ratio_inc where it differs from the
    median by more than 1% (common.inc_ticks), A2 fractional from A2-r1's P/LB; grey dashed max(2, rho), C3-Cor3's
    factor, its label hanging below the line's end (first line level with it).
(b) The same under `eager` (ratios.eager.<rho>.1.<tag>).
(c) ALG / LB against mu / beta~ in {0.2, 0.5, 1, 2} at rho* = 4 under `adaptive` (ratios.adaptive.4.<mu>.<tag>,
    the default point of M7).
The three panels share the y scale. Trace instances leave the ORML core, so the ratios are diagnostics (E1-8).
The guarded series (E1's tag Sublet) is the one-way guard around the lagged BL5 at Algorithm 1's defaults, drawn as
bl5_g1, "Lagged RetroRenting + one-way guard" (MS6 C46: design/ms6_spec.md M2, M4), as in Fig. 5(b); the bound's
label is Fig. 5(b)'s max(2, rho), in math as the axes' rho (C47), and the note names its result.
Where A2 (r-bar = 1) and A3 agree within AGREE_MAX_PCT at every point of a panel, a key next to them says so, with
the panel's tolerance rounded up to a whole percent (common.agree_entry, agree_key; `agree` in the extract).
MS7 C62 (the type scale of style.py): the panel titles at the caption size (style.LABEL_PT), each on its letter's
baseline as printed, (c)'s rho in math, italic as on the axes (common.align_baselines); the legend's mathtext labels
(A2's r-bar) on the row's plain baseline as printed; the shared log y axis without minor ticks between its labeled
1, 2, 5, 10, 20 (as Fig. 7); the bound's label placed on its own height (right_theory_lines(..., measured=True)).
No plotted number changes.
C62 fix round (the supplement's critic): a key starts at least fig5_e1_e10.SPINE_CLEAR_PT (4 pt) right of its y spine
(key_off_spine): where the shared rule (common.agree_key) puts it closer, as (c)'s one-line key, 1.5 pt from the
spine, it is set on two lines ("... ≈ A3" over "(within p%)"), centered over the panel on the free band nearest to
its pair (in (c) just above the pair, below A2 with the theory r-bar), else at least 4 pt from the spine on the free
space nearest to the pair (fig5_e1_e10.off_spine).

Run from code/sim: python -m figs.supp.sf_e1_sched [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import NullLocator

from figs import style
from figs.common import (AGREE_MAX_PCT, E1, GRID_RES_PT, INC_TICK_RULE, KEY_PAD_PT, agree_entry, agree_key,
                         align_baselines, cli, data_range, draw_e1_ratio_panel, e1_series, free_spot, max2rho,
                         panel_title, place_key, points_pt, ratio_log10_axis, rho_star_axis, rho_star_range,
                         right_theory_lines)
from figs.fig5_e1_e10 import FIG5_B_KEYS, SPINE_CLEAR_PT, move_to, off_spine, spine_gap_pt
from figs.inputs import Inputs

NAME = "sf_e1_sched"
KEYS = FIG5_B_KEYS                  # bl5_g1, a2_frac, a2_r1, a2_theory, a3 (style.SUPP_POLICIES[NAME])
RHO_MU = 4                          # M7: the default point of the mu sweep
PANEL_RATIOS = (1.8, 1.8, 1.0)      # axes widths of (a), (b), (c) (not in §8.7, which has (1, 1, 1))
PAIR = ("a2_r1", "a3")              # the pair whose agreement a key reports
style.register_supplementary(NAME, "W2", 2.2)
# C47 (print check of the gate): the bound's drawn label as Fig. 5(b)'s, max(2, rho) (as built "max(2, ρ),\nC3-Cor3
# factor"; the result it comes from is named in the note, the caption's source), in math since U46, as the x axes' rho
# and Fig. 5(b)'s label. C62: the panel title's rho in math too, italic as on the axes, the title moved onto its
# letter's baseline as printed (common.align_baselines; C47 kept it upright since mathtext lifted the title's
# baseline 0.5 pt above the letter's), as the supplement's other panel titles (sf_e1_rotation, sf_e10b, sf_e10_rho).
LABELS = {"rho": r"$\rho$", "mu": r"$\mu/\tilde\beta$", "y": "ALG / LB", "bound": r"$\max(2,\rho)$",
          "a": "Trace schedule", "b": "Eager schedule", "c": f"Adaptive lender, $\\rho={RHO_MU}$",
          "tick": f"black tick: median of ALG / MILP incumbent, {INC_TICK_RULE}",
          "note": "trace instances leave the ORML core: ratios are diagnostics (E1-8); C3-Cor3 PROVEN"}


def build(inp: Inputs) -> dict:
    e1 = inp.json(E1)
    out: dict = {}
    for panel, sched in (("a", "trace"), ("b", "eager")):
        out[panel] = e1_series(e1, sched, 1, KEYS)
        out[panel]["x_range"] = rho_star_range(out[panel][KEYS[0]]["x"], len(KEYS))
        out[panel]["bound"] = max2rho(out[panel]["x_range"])
    out["c"] = e1_series(e1, "adaptive", None, KEYS, rho=RHO_MU)
    out["bound"] = out["a"]["bound"]
    for p in "abc":
        out[p]["agree"] = agree_entry(*PAIR, *(out[p][k]["median"] for k in PAIR), AGREE_MAX_PCT)
    out["labels"] = {**LABELS, "agree": {p: out[p]["agree"]["key"] for p in "abc" if out[p]["agree"]}}
    out["sources"] = list(inp.sources)
    return out


def key_off_spine(ax, entry: Mapping | None, series: Mapping, *, y: str = "median"):
    """C62 fix round: the coincidence key of common.agree_key, kept at least SPINE_CLEAR_PT right of the y spine of
    `ax`. Where agree_key places it closer (free_spot keeps 1.5 pt from the axes edges; (c)'s one-line key filled the
    narrow panel), it is set on two lines, its tolerance under the names, and centered over the axes on the free band
    of the axes' full width nearest to the pair's points (a box of that width on free_spot's grid); where no such band
    is free, it is moved at least SPINE_CLEAR_PT from the spine on the free space nearest to the pair (off_spine)."""
    leg = agree_key(ax, entry, series, y=y)
    if leg is None or spine_gap_pt(ax, leg) >= SPINE_CLEAR_PT:
        return leg
    near = np.concatenate([points_pt(ax, series[k]["x"], series[k][y]) for k in entry["pair"]])
    hs = tuple(Line2D([], [], **style.policy_kwargs(k, lines=False)) for k in entry["pair"])
    leg.remove()
    # agree_key's two-line form, placed by the same rule; its one-line form again where the two lines fit nowhere
    leg = place_key(ax, [(hs, entry["key"].replace(" (within", "\n(within"))], near, handlelength=1.3) or \
        agree_key(ax, entry, series, y=y)
    r = ax.figure.canvas.get_renderer()
    to_pt = 72.0 / ax.figure.dpi
    bb, ab = leg.get_window_extent(r), ax.get_window_extent(r)
    band = ab.width * to_pt - 2.0 * (KEY_PAD_PT + GRID_RES_PT)      # the axes' width less free_spot's edge clearance
    spot = free_spot(ax, band, bb.height * to_pt, near, skip=(leg,)) if band >= bb.width * to_pt else None
    if spot is not None:
        move_to(ax, leg, spot[0] + 0.5 * (band - bb.width * to_pt), spot[1])
    else:
        off_spine(ax, leg, near)
    return leg


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    # one y scale across the panels (§8.7), so (b) and (c) share (a)'s y axis and its label; the width this saves,
    # and the width (c) can spare with its four mu values, go to (a) and (b), whose label column of max(2, rho)
    # narrows the data (so that the rho* labels 1.5 and 2 both fit)
    axes = style.panel_row(fig, PANEL_RATIOS, legend=True, sharey=(False, True, True))
    vals = [data[p][k][f] for p in "abc" for k in KEYS for f in ("median", "ci_lo", "ci_hi")]
    lo, hi = data_range(*vals, data["a"]["bound"]["max2rho"], data["b"]["bound"]["max2rho"])
    ratio_log10_axis(axes[0], lo, hi)
    axes[0].yaxis.set_minor_locator(NullLocator())      # C62: no comb of minor ticks between 1, 2, 5, 10, 20 (Fig. 7)
    for ax, p in zip(axes[:2], "ab"):
        d = data[p]
        draw_e1_ratio_panel(ax, d, KEYS)
        ax.set_xlabel(lab["rho"])                  # before the label column, which centers it under the data
        rho_star_axis(ax, d[KEYS[0]]["x"], d["x_range"], [lab["bound"]])
        right_theory_lines(ax, [dict(x=d["bound"]["rho"], y=d["bound"]["max2rho"], kind="upper",
                                     label=lab["bound"], first_line=True)], measured=True)     # C62: its own height
    ax = axes[2]
    d = data["c"]
    draw_e1_ratio_panel(ax, d, KEYS)
    mus = sorted({float(x) for x in d[KEYS[0]]["x"]})
    style.log_axis(ax, "x", ticks=mus)
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlim(min(mus) / 1.35, max(mus) * 1.35)
    ax.set_xlabel(lab["mu"])
    axes[0].set_ylabel(lab["y"])
    for ax in axes:
        style.ygrid(ax)
    for ax, letter, p in zip(axes, style.panel_letters(axes), "abc"):
        # the schedule or the default point of each panel; C62: at the caption size, on its letter's baseline
        align_baselines([letter, panel_title(ax, letter, lab[p], fontsize=style.LABEL_PT)])
        key_off_spine(ax, data[p].get("agree"), data[p])     # C62 fix round: at least 4 pt right of the spine
    leg = style.legend_row(fig, list(KEYS))
    align_baselines(leg.get_texts())        # C62: the r-bar labels (mathtext) on their plain neighbors' baseline
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
