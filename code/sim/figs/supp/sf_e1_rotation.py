"""sf_e1_rotation: A3 with rotation against its reference mode (design/sim_spec_ms3.md §8.7, M6; plan §4, part S-F).

A3-ref is A3 {"x3": false, "x2": "reference", "reaction": "cold"}, A3-rot the same with X3 rotation (§4.3), so the
comparison answers how much of the adaptive gap A3's rotation recovers.
(a) ALG / LB against rho* on E1(b)'s instances under the adaptive lender (e1/summary.json
    ratios.adaptive.<rho>.1.{A3-ref, A3-rot}): median of ratio_LB with its median_ci95, a black tick at the median
    of ratio_inc where it differs from the median by more than 1% (common.inc_ticks); y ticks at the powers of two,
    as in (b).
(b) E[ALG] / E[OPT] against m on the single-LLM family (T4) at rho = 16 under the adaptive lender (e10/summary.json
    a.adaptive.16.<m>.{A3-ref, A3-rot}) with the bootstrap interval of the ratio of means.
Each panel has its condition as a title (labels a, b), as sf_e1_sched.
The MS2 rows of code/sim/out/ms2_checks/a3_rotation_c4a.json (T = 48, reaction c2sw) go into the extract
(`ms2_reference`) for the caption, not onto the axes.
MS7 C62 (the type scale of style.py): the panel titles at the caption size (style.LABEL_PT), each on its letter's
baseline as printed, (b)'s rho in math, italic as on the axes (common.align_baselines). No plotted number changes.

Run from code/sim: python -m figs.supp.sf_e1_rotation [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

from figs import style
from figs.common import (E1, E10, INC_TICK_RULE, RHO_MAIN, align_baselines, cli, data_range, draw_e1_ratio_panel,
                         draw_e10_series, e1_series, e10_series, m_axis, need, panel_title, ratio_log2_axis,
                         rho_star_axis, rho_star_range)
from figs.inputs import Inputs

NAME = "sf_e1_rotation"
KEYS = ("a3", "a3_rot")
MS2_REF = "code/sim/out/ms2_checks/a3_rotation_c4a.json"
style.register_supplementary(NAME, "W1", 2.0)
LABELS = {"a_x": r"$\rho$", "a_y": "ALG / LB", "b_x": "Sites m", "b_y": "E[ALG] / E[OPT]",
          # C59 (RC19(3)): the instances by their name (as built "E1(b), adaptive" and "T4 family, adaptive")
          # C62: the rho of (b)'s title in math, italic as on the axes, on its letter's baseline as printed
          # (align_baselines; as built upright, "ρ = 16")
          "a": "Trace instances, adaptive", "b": f"One LLM, adaptive, $\\rho={RHO_MAIN}$",
          "tick": f"black tick: median of ALG / MILP incumbent, {INC_TICK_RULE}"}


def build(inp: Inputs) -> dict:
    e1, e10, ms2 = inp.json(E1), inp.json(E10), inp.json(MS2_REF)
    a = e1_series(e1, "adaptive", 1, KEYS)
    a["x_range"] = rho_star_range(a[KEYS[0]]["x"], len(KEYS))
    b = e10_series(e10, "adaptive", RHO_MAIN, KEYS)
    ref = [{"m": r["m"], "rho": r["rho"], "LB_T": r.get("LB_T"),
            "pd_r1": need(r, "ref", "pd_r1", what=MS2_REF), "pd_rth": need(r, "ref", "pd_rth", what=MS2_REF),
            "a3_x3_r1_mean": need(r, "a3_x3_r1", "mean", what=MS2_REF),
            "a3_x3_rth_mean": need(r, "a3_x3_rth", "mean", what=MS2_REF)}
           for r in need(ms2, "rows", what=MS2_REF)]
    return {"a": a, "b": b, "ms2_reference": {"description": ms2.get("description"), "rows": ref},
            "labels": LABELS, "sources": list(inp.sources)}


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    ax_a, ax_b = style.panel_row(fig, (1, 1))
    a, b = data["a"], data["b"]
    draw_e1_ratio_panel(ax_a, a, KEYS)
    rho_star_axis(ax_a, a[KEYS[0]]["x"], a["x_range"])
    lo, hi = data_range(*(a[k][f] for k in KEYS for f in ("median", "ci_lo", "ci_hi")))
    ratio_log2_axis(ax_a, min(lo, 1.0), hi)
    ax_a.set_xlabel(lab["a_x"])
    ax_a.set_ylabel(lab["a_y"])
    draw_e10_series(ax_b, b, KEYS)
    m_axis(ax_b, b[KEYS[0]]["m"])
    lo, hi = data_range(*(b[k][f] for k in KEYS for f in ("ratio", "ci_lo", "ci_hi")))
    ratio_log2_axis(ax_b, min(lo, 1.0), hi)
    ax_b.set_ylabel(lab["b_y"])
    for ax in (ax_a, ax_b):
        style.ygrid(ax)
    for ax, letter, p in zip((ax_a, ax_b), style.panel_letters([ax_a, ax_b]), "ab"):
        # the condition of each panel; C62: at the caption size, on its letter's baseline
        align_baselines([letter, panel_title(ax, letter, lab[p], fontsize=style.LABEL_PT)])
    # the empty lower right corner of (a), below the data (as built at 9 pt a legend at the upper left reached the
    # interval bar at rho* = 8)
    style.corner_legend(ax_a, list(KEYS), loc="lower right")
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
