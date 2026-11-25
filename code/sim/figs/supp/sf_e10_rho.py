"""sf_e10_rho: Figs. 5(c) and 6 at rho = 4 and 64 (design/sim_spec_ms3.md §8.7, §5.4; plan §4, part S-F).

(a), (b): Fig. 5(c) at rho = 4 and 64: E[ALG] / E[OPT] against m on the T4 family under the adaptive lender
(e10/summary.json a.adaptive.<rho>.<m>.{RR, A2-th, A3-ref}) with LB_T at T = 16 m D (C3-T4, PROVEN, dotted), its
T -> infinity limit rho m / (m + rho - 1) (solid) and O1-B at RR-renew's run (PROVEN, dashed), from bounds.<rho>.<m>.
The limit's label says that it equals RR-renew where RR-renew's ratio equals it at every m of both panels; LB_T's
label is one line, so that the three labels fit under O1-B's end in (a) with none level with another line's end
(Fig. 5(c)'s placement, right_theory_lines(..., clear_ends=True)).
(c), (d): Fig. 6 at rho = 4 and 64: RR-renew and A2 under `safe_site` at k* (private information, solid),
marking under `iid_step` at p* (public information, dashed, on Fig. 6's white underlay), with LB_A (O1-A), max_p
LB_C (O1-C's limit), O1-B and 2 h_m + 1 (O1-D), all from bounds.<rho>.<m>. O1-C's limit label says that marking
lies on it where marking's ratio is within AGREE_MAX_PCT of the limit at every m of both panels (Fig. 6's rule,
marking_near_limit; the agreement in `limit_marking` of the extract). Every policy of (a), (b) has private
information (I1); the line-style samples of the legend are black, as in Fig. 6. Unlabeled m ticks are drawn at
minor length (common.same_tick_labels).
MS7 C62 (the type scale of style.py): the panel titles at the caption size (style.LABEL_PT), in sentence case with the
lenders named and rho in math ("Adaptive lender, $\\rho=4$"; as built "adaptive, ρ = 4"), each on its letter's
baseline as printed (common.align_baselines); the row 2.3 in high (2.5 in before); each policy's legend
sample in its series' line style (Marking dashed, as Fig. 6; as built solid), its dashes centered, the mathtext label
on the row's plain baseline as printed; (b)-(d) reserve GUTTER_IN beyond their tick labels, so that a label column's
text stays apart from the next panel's tick labels; the label columns stacked on the labels' own heights (Fig. 5(c)'s
and Fig. 6's drawers, right_theory_lines(..., measured=True)). No plotted number changes.
C62 fix round (the supplement's critic): the four panels plot one quantity against the same m, so they get one data
width (as built 0.82, 0.82, 0.91, 0.99 in, since the label columns differ, (a)-(c) widened for their leaders): the
row is drawn once and again (sf_e10b.equal_data_ratios), each axes as wide as the common data width plus its own
label column; (b)-(d) reserve their own widest tick label plus GUTTER_IN (tick_reserves; as built all reserved the
row's widest, so the gutter before (c), whose labels end at 32, was wider), so that the gutters between a label
column's text and the next panel's tick labels are equal.

Run from code/sim: python -m figs.supp.sf_e10_rho [--from-extract [JSON]].
"""
from __future__ import annotations

import math
import sys
from typing import Any, Mapping, Sequence

from figs import style
from figs.common import E10, RHO_MAIN, align_baselines, cli, finite, need, num_items, panel_title, same_tick_labels
from figs.fig5_e1_e10 import build_e10_adaptive, draw_e10_adaptive_panel, limit_is_rr
from figs.fig6_e10 import ENVS as FIG6_ENVS
from figs.fig6_e10 import LABELS as FIG6_LABELS
from figs.fig6_e10 import PRIVATE, build_block, draw_panel, marking_near_limit, policy_env_handles
from figs.fig7_e2_e6 import centered_dashes
from figs.inputs import Inputs
from figs.supp.sf_e10b import equal_data_ratios

NAME = "sf_e10_rho"
KEYS = ("rr_renew", "a2_theory", "a3", "marking")
ENVS = {**FIG6_ENVS, "a3": PRIVATE}    # C62: the information class of each policy's legend sample (A3 private)
GUTTER_IN = 0.08                       # C62: (b)-(d)'s reserve beyond their tick labels (ytick_reserve's gap)
TITLE_CLEAR_PT = 2.0                   # C62: the label columns end this far below the axes top, clear of the titles
#                                        (caption size; a title's descent reaches about 0.6 pt below the axes top)
# 2.3 in (C62; 2.5 in, the largest supplementary height, while the label columns stacked up to five lines at 9 pt): at
# 7 pt the columns fit a lower row, whose four panels then come out about as high as they are wide
style.register_supplementary(NAME, "W2", 2.3)
# one- to three-line labels for the narrow panels; the limit's label of (a), (b) is LIMIT_IS_RR where RR-renew's ratio
# equals the limit at every m, O1-C's of (c), (d) LIMIT_NEAR_MARKING where marking lies within AGREE_MAX_PCT of it at
# every m (build)
NARROW = {"c_O1B": "O1-B", "c_limit": "T→∞\nlimit", "c_LB_T": "LB$_T$", "c_y": "E[ALG] / E[OPT]",
          **{**FIG6_LABELS, "LB_A": "LB$_A$,\nO1-A", "LB_C_max": "O1-C\nlimit,\nT→∞"}}
LIMIT_IS_RR = "limit =\nRR-renew"
LIMIT_NEAR_MARKING = "O1-C\nlimit ≈\nMarking"


def side_rhos(e10: Mapping) -> list[float]:
    """The rho values of bounds other than the main text's rho = 16."""
    return [x for x, _, _ in num_items(need(e10, "bounds", what=E10)) if x != RHO_MAIN]


def build(inp: Inputs) -> dict:
    e10 = inp.json(E10)
    rhos = side_rhos(e10)
    adaptive = [build_e10_adaptive(e10, r) for r in rhos]
    oblivious = [build_block(e10, r) for r in rhos]
    near = marking_near_limit(oblivious)
    labels = {**NARROW, "c_limit": LIMIT_IS_RR if limit_is_rr(adaptive) else NARROW["c_limit"],
              "LB_C_max": LIMIT_NEAR_MARKING if near else NARROW["LB_C_max"],
              # C62: sentence case and the lenders named, as the supplement's other panel titles (sf_e1_sched,
              # sf_e10b, sf_e10_cross), rho in math, italic as on the axes (as built "adaptive, ρ = 4" and
              # "oblivious, ρ = 4"); each title on its letter's baseline as printed (draw: align_baselines)
              "panel_a": "Adaptive lender, $\\rho={:g}$", "panel_o": "Oblivious lenders, $\\rho={:g}$",
              "status": {"C3-T4": "PROVEN", "O1-A": "PROVEN (m >= 3)", "O1-B": "PROVEN",
                         "O1-C": "PROVEN (tau >= 1), a limit", "O1-D": "PROVEN"}}
    return {"rhos": rhos, "a_b": adaptive, "c_d": oblivious, "limit_marking": near, "labels": labels,
            "sources": list(inp.sources)}


def top_tick_label(blocks: Sequence[Mapping]) -> str:
    """The highest y tick label of the panels drawn from `blocks`: the power of two at or above their largest
    plotted value (ratio_log2_axis's ticks)."""
    vals = [finite(v.get(f, [])) for blk in blocks for v in blk.values() if isinstance(v, Mapping)
            for f in ("ratio", "ci_lo", "ci_hi", "value")]
    hi = max(float(a[a > 0].max()) for a in vals if (a > 0).any())
    return style.PLAIN(2.0 ** math.ceil(math.log2(hi) - 1e-9))


def tick_reserves(axes: Sequence) -> list[float | None]:
    """C62 fix round: the left reserves of a drawn row for style.panel_row: None for (a), which has the y label and
    style.LEFT_LABEL, and for (b)-(d) each its own visible y tick labels plus GUTTER_IN (style.ytick_reserve)."""
    fig = axes[0].figure
    fig.canvas.draw()
    out: list[float | None] = [None]
    for ax in axes[1:]:
        lo, hi = sorted(ax.get_ylim())
        shown = [t.get_text() for t in ax.get_yticklabels()
                 if t.get_visible() and t.get_text() and lo <= t.get_position()[1] <= hi]
        out.append(style.ytick_reserve(fig, shown, gap=GUTTER_IN))
    return out


def draw(data: Mapping) -> Any:
    # C62 fix round: drawn twice, the second time with (b)-(d)'s own tick reserves and the axes widths that give the
    # four panels one data width (sf_e10b.equal_data_ratios), the row's width kept
    fig = draw_row(data, (1, 1, 1, 1), None)
    left = tick_reserves(fig.axes)
    total = float(fig.get_size_inches()[0]) - style.LEFT_LABEL - sum(left[1:]) - style.MARGIN_RIGHT
    return draw_row(data, equal_data_ratios(fig.axes, total), left)


def draw_row(data: Mapping, ratios: Sequence[float], left: Sequence[float | None] | None) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    # the four panels plot one quantity, so its y label is on (a) only and (b)-(d) reserve their tick labels alone:
    # the width goes to the data, which the label columns narrow
    blocks = list(data["a_b"]) + list(data["c_d"])
    # C62: the reserve holds the tick labels and GUTTER_IN more, so that a label column's text (its right end 3 pt
    # inside its axes) stays apart from the next panel's tick labels (0.03 in apart at 7 pt with the default gap); the
    # first drawing reserves the row's widest top tick label, the second each panel's own (tick_reserves)
    if left is None:
        reserve = style.ytick_reserve(fig, [top_tick_label(blocks)], gap=GUTTER_IN)
        left = (None, reserve, reserve, reserve)
    axes = style.panel_row(fig, ratios, legend=True, left=left)
    for i, (ax, c) in enumerate(zip(axes[:2], data["a_b"])):
        draw_e10_adaptive_panel(ax, c, lab, env=("information", "private"), ylabel=i == 0,
                                label_top_pad_pt=TITLE_CLEAR_PT)
    for ax, blk in zip(axes[2:], data["c_d"]):
        draw_panel(ax, blk, lab, ylabel=False, label_top_pad_pt=TITLE_CLEAR_PT)
    same_tick_labels(axes)          # the m labels that the narrowest data area holds, in all four panels
    letters = style.panel_letters(axes)
    titles = [lab["panel_a"].format(r) for r in data["rhos"]] + [lab["panel_o"].format(r) for r in data["rhos"]]
    for ax, letter, t in zip(axes, letters, titles):
        align_baselines([letter, panel_title(ax, letter, t, fontsize=style.LABEL_PT)])     # C62: caption size
    # as Fig. 6: each policy's sample in its series' line style (marking dashed, public information; C62, as built
    # every sample solid), the dashes centered on the samples, the mathtext label on its neighbors' baseline
    leg = style.legend_row(fig, [], extra=centered_dashes(policy_env_handles(KEYS, ENVS))
                           + centered_dashes(style.env_handles("information", color="black")))
    align_baselines(leg.get_texts())
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
