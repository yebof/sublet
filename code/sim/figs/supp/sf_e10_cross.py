"""sf_e10_cross: each information class under the other oblivious lender (design/sim_spec_ms3.md §8.7, §5.4; plan
§4, part S-F).

E[ALG] / E[OPT] against m on the T4 family at rho = 16 with the bootstrap interval of the ratio of means (30 paired
seeds, M11, M13): (a) under `safe_site` at k* and (b) under `iid_step` at p*, for RR-renew, A2 (theory r-bar) and
marking (e10/summary.json a.<sched>.16.<m>.{RR, A2-th, MARK}). Line style by the policy's information class
(private I1 solid, public I2 dashed). Where RR-renew and marking agree within AGREE_MAX_PCT at every m of a panel,
a key next to them says so with the tolerance rounded up to a whole percent (common.agree_entry, agree_key; `agree`
in the extract). The legend rows sit at the top, the panel letters and titles (the lender, its
parameter starred as in the paper) directly above the data. The value of public information under each lender
(value_public.<sched>.16.<m>, M52: best private mean cost over best public mean cost, paired bootstrap) is in the
extract for the caption table, not on the axes.
MS7 C62 (the type scale of style.py): the panel titles at the caption size (style.LABEL_PT), each on its letter's
baseline as printed (their k* and p* are mathtext: common.align_baselines); each policy's legend sample in its
series' line style (Marking dashed, as Fig. 6; as built solid), its dashes centered, the mathtext label on the row's
plain baseline as printed. No plotted number changes.

Run from code/sim: python -m figs.supp.sf_e10_cross [--from-extract [JSON]].
"""
from __future__ import annotations

import math
import sys
from typing import Any, Mapping, Sequence

from figs import style
from figs.common import (AGREE_MAX_PCT, E10, RHO_MAIN, agree_entry, agree_key, align_baselines, cli, data_range,
                         draw_e10_series, e10_series, legend_headroom, legend_rows, m_axis, need, num_items,
                         panel_title, ratio_log2_axis)
from figs.fig6_e10 import ENVS, policy_env_handles
from figs.fig7_e2_e6 import centered_dashes
from figs.inputs import Inputs

NAME = "sf_e10_cross"
KEYS = ("rr_renew", "a2_theory", "marking")
SCHEDS = (("a", "safe_site"), ("b", "iid_step"))
PAIR = ("rr_renew", "marking")                 # the pair whose agreement a key reports
TITLE_GAP_PT = 2.0                             # between the legend rows and the panel titles below them
TOP_PT = 1.5                                   # between the page top and the first legend row
style.register_supplementary(NAME, "W1", 2.2)


def build(inp: Inputs) -> dict:
    e10 = inp.json(E10)
    out = {}
    for p, sched in SCHEDS:
        out[p] = e10_series(e10, sched, RHO_MAIN, KEYS, extra=("k_star",) if sched == "safe_site" else ("p_star",))
        out[p]["sched"] = sched
    vp = {}
    for _, sched in SCHEDS:
        block = need(e10, "value_public", sched, RHO_MAIN, what=E10)
        vp[sched] = [{"m": m, **v} if isinstance(v, Mapping) else
                     {"m": m, "ratio": None, "note": block.get(mk + "_note") or "null"}
                     for m, mk, v in num_items(block)]
    out["value_public"] = vp
    agree = {}
    for p, _ in SCHEDS:
        out[p]["agree"] = agree_entry(*PAIR, *(out[p][k]["ratio"] for k in PAIR), AGREE_MAX_PCT)
        if out[p]["agree"]:
            agree[p] = out[p]["agree"]["key"]
    out["labels"] = {"x": "Sites m", "y": "E[ALG] / E[OPT]", "a": r"Safe-site lender at $k^\star$",
                     "b": r"i.i.d.-step lender at $p^\star$", "rho": f"rho = {RHO_MAIN}", "agree": agree}
    out["sources"] = list(inp.sources)
    return out


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    axes = style.panel_row(fig, (1, 1), sharey=(False, True))
    lo, hi = data_range(*(data[p][k][f] for p, _ in SCHEDS for k in KEYS for f in ("ratio", "ci_lo", "ci_hi")))
    for ax, (p, sched) in zip(axes, SCHEDS):
        draw_e10_series(ax, data[p], KEYS, envs=ENVS)
        m_axis(ax, data[p][KEYS[0]]["m"])
    ratio_log2_axis(axes[0], min(lo, 1.0), hi)
    axes[0].set_ylabel(lab["y"])
    top = axes[0].get_ylim()[1]
    # the legend rows (the policies, then the line styles) span the shared headroom of both panels from the page top
    # (less TOP_PT); the letters and titles go directly above the data, below the rows
    letters = style.panel_letters(axes)
    # C62: the titles at the caption size, each on its letter's baseline as printed (its k* or p* is mathtext, which
    # the PDF sets up to 1 pt high: common.align_baselines)
    titles = [panel_title(ax, letter, lab[p], fontsize=style.LABEL_PT) for ax, letter, (p, _) in
              zip(axes, letters, SCHEDS)]
    for letter, title in zip(letters, titles):
        align_baselines([letter, title])
    heads = letters + titles
    r = fig.canvas.get_renderer()
    ax_top = axes[0].get_window_extent(r).y1
    up_pt = (max(t.get_window_extent(r).y1 for t in heads) - ax_top) * 72.0 / fig.dpi
    page_pt = (fig.bbox.y1 - ax_top) * 72.0 / fig.dpi
    # C62: as Fig. 6, each policy's sample in its series' line style (marking dashed; as built every sample solid,
    # against the second row's key), the dashes centered on the samples, the mathtext label on its row's baseline
    legs = legend_rows(axes[0], [centered_dashes(policy_env_handles(KEYS)),
                                 centered_dashes(style.env_handles("information", color="black"))],
                       top_pt=TOP_PT - page_pt)
    for lg in legs:
        align_baselines(lg.get_texts())
    legend_headroom(axes[0], legs, data_top=top, pad_in=(up_pt + TITLE_GAP_PT) / style.BP_PER_IN)  # title room
    drop = (ax_top - axes[0].transData.transform((1.0, top))[1]) / fig.dpi / fig.get_size_inches()[1]
    for t in heads:
        t.set_y(t.get_position()[1] - drop)
    y0, y1 = (math.log(v) for v in axes[0].get_ylim())
    axes[0].yaxis.label.set_y(0.5 * (math.log(top) - y0) / (y1 - y0))      # centered on the data, below (a)
    for ax, p in zip(axes, (p for p, _ in SCHEDS)):
        style.ygrid(ax)
        ax.spines["left"].set_bounds(axes[0].get_ylim()[0], top)
        agree_key(ax, data[p].get("agree"), data[p], x="m", y="ratio")
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
