"""Fig. 6: the value of public reclaim information (E10(a) under oblivious lenders); design/sim_spec_ms3.md §8.5.

E[ALG] / E[OPT] against m at rho = 16 on the T4 family, each information class under the oblivious lender of its
own lower bound: RR-renew and A2 (theory r-bar) under `safe_site` at k* (private information, solid; e10/summary.json
a.safe_site.16.<m>.{RR, A2-th}) and marking under `iid_step` at p* (public information, dashed;
a.iid_step.16.<m>.MARK), with 95% bootstrap bars (ratio of means, M13). Theory lines, all from e10/summary.json
bounds.16.<m> (the E10 driver computes them; the script imports no reference code): LB_A(k*) (O1-A, dotted, m >= 3),
max_p LB_C (O1-C's limit for T -> infinity, solid), O1-B for RR-renew at T = Phi k* D (dashed) and 2 h_m + 1 (O1-D,
dashed); all PROVEN (Table I). Marking's dashed line runs on a white underlay above the theory lines (it lies on
O1-C's limit), so that its dash gaps show white rather than the grey line; the line-style samples of the legend are
black, unlike the grey theory lines; the y axis starts low enough for the markers at a ratio of about 1 to clear the
x spine (common.clear_floor). Where marking's ratio lies within AGREE_MAX_PCT of O1-C's limit at every m
(marking_near_limit; the agreement in `limit_marking` of the extract), the limit's label says so
(LIMIT_NEAR_MARKING; labels.LB_C_max).

The drawn labels name no design ID (MS6 C46: design/ms6_spec.md M6): "LB_A (private)" (O1-A), "LB_C limit (public),
T -> infinity" (O1-C's limit), "RR-renew bound" (O1-B) and "marking bound" (O1-D), MAIN_LABELS; the caption (LaTeX, in
the manuscript) gives the paper's result numbers, and the status labels of the extract keep the design names (data).
LABELS keeps the labels with the design names, which the supplementary sf_e10_rho takes for its narrow panels (the
supplement keeps the design names, M9).

C52 (design/ms7/plan.md §4, unit T1: the manuscript scan): each policy's legend sample is drawn in its series' line
style (policy_env_handles: marking dashed), so that the first legend row agrees with the second, which says that
dashed is public information (as built, style.policy_handles drew every sample solid).

MS7 C62 (the type scale of style.py: text at 7 pt, axis labels at the caption size): the label column is stacked on
the labels' own heights (right_theory_lines(..., measured=True); at 7 pt the three-line limit label, whose mathtext
lines are taller than common.LINE_STEP_PT allows, overlapped "LB_A (private)") and placed so that no label is level
with another line's end (clear_ends: "RR-renew bound" and "marking bound" level with their lines, LB_A's label below
them with a leader to its end, which RR-renew's covers); the legend's dashed samples have their dashes centered,
whole at both ends (fig7_e2_e6.centered_dashes), and its mathtext label sits on the row's plain baseline as printed
(common.align_baselines); the y label is centered on the spine, below the legend's headroom. No plotted number
changes.

Run from code/sim: python -m figs.fig6_e10 [--from-extract [JSON]].
"""
from __future__ import annotations

import math
import sys
from typing import Any, Mapping, Sequence

from matplotlib.lines import Line2D

from figs import style
from figs.common import (AGREE_MAX_PCT, E10, RHO_MAIN, agreement, align_baselines, clear_floor, cli, data_range,
                         draw_e10_series, e10_bound, e10_series, legend_headroom, legend_rows, m_axis, ratio_log2_axis,
                         right_theory_lines)
from figs.fig7_e2_e6 import centered_dashes
from figs.inputs import Inputs

NAME = "fig6"
RHO = RHO_MAIN                             # §8.5: rho = 16 in the main text
KEYS = ("rr_renew", "a2_theory", "marking")
PRIVATE, PUBLIC = ("information", "private"), ("information", "public")
ENVS = {"rr_renew": PRIVATE, "a2_theory": PRIVATE, "marking": PUBLIC}
SCHED = {"rr_renew": "safe_site", "a2_theory": "safe_site", "marking": "iid_step"}
EXTRA = {"safe_site": ("k_star",), "iid_step": ("p_star",)}
UNDERLAY_PT = 0.6                          # white underlay of marking's line, each side: 2.2 pt in all
STATUS = {"O1-A": "PROVEN (m >= 3, design §1.8.3)", "O1-B": "PROVEN", "O1-C": "PROVEN (tau >= 1); a limit",
          "O1-D": "PROVEN"}
LABELS = {"x": "Sites m", "y": "E[ALG] / E[OPT]", "LB_A": r"LB$_A$, O1-A", "LB_C_max": "O1-C\nlimit, T→∞",
          "O1B": "O1-B", "O1D": "O1-D"}             # with the design names: sf_e10_rho's (the supplement's)
# C46 (design/ms6_spec.md M6): Fig. 6's drawn labels, descriptive, without design IDs; C47 (print check of the gate,
# U46): the limit's arrow is \longrightarrow, STIX's full-height arrow (Liberation Sans' U+2192, which \to sets, prints
# at about 40% of the cap height, low between T and the infinity sign), as in Figs. 3 and 5
MAIN_LABELS = {**LABELS, "LB_A": r"LB$_A$ (private)", "LB_C_max": "LB$_C$ limit\n(public), $T\\longrightarrow\\infty$",
               "O1B": "RR-renew bound", "O1D": "marking bound"}
LIMIT_NEAR_MARKING = MAIN_LABELS["LB_C_max"] + "\n≈ Marking"   # LB_C_max's label where marking_near_limit holds


def build_block(e10: Mapping, rho) -> dict:
    """Fig. 6's series and theory lines at `rho` (also sf_e10_rho (c), (d))."""
    out = {}
    for key in KEYS:
        sched = SCHED[key]
        out[key] = e10_series(e10, sched, rho, [key], extra=EXTRA[sched])[key]
        out[key]["sched"] = sched
    out["LB_A"] = e10_bound(e10, rho, "LB_A", m_min=3)
    out["LB_C_max"] = e10_bound(e10, rho, "LB_C_max")
    out["O1B"] = e10_bound(e10, rho, "O1B_safe_site")
    out["O1D"] = e10_bound(e10, rho, "two_h_m_plus_1")
    out["rho"] = rho
    return out


def marking_near_limit(blocks: Sequence[Mapping]) -> dict | None:
    """How closely marking's ratio follows O1-C's limit (max_p LB_C) in the blocks of build_block, over every m of
    either, both given at the same m (common.agreement; the largest max_rel_diff over the blocks, and within_pct): a
    dict where marking lies within AGREE_MAX_PCT of the limit at every m of every block, so that the limit's line
    lies under marking's on the drawn scale (Fig. 6; sf_e10_rho (c), (d)); None otherwise."""
    worst = None
    for blk in blocks:
        lim = dict(zip(blk["LB_C_max"]["m"], blk["LB_C_max"]["value"]))
        mk = dict(zip(blk["marking"]["m"], blk["marking"]["ratio"]))
        ms = sorted(set(lim) | set(mk))
        ag = agreement([mk.get(m) for m in ms], [lim.get(m) for m in ms])
        if ag is None or ag["within_pct"] > AGREE_MAX_PCT:
            return None
        worst = ag if worst is None or ag["max_rel_diff"] > worst["max_rel_diff"] else worst
    return worst


def build(inp: Inputs) -> dict:
    e10 = inp.json(E10)
    data = build_block(e10, RHO)
    data["limit_marking"] = marking_near_limit([data])
    data["labels"] = {**MAIN_LABELS, "series": {"rr_renew": "RR-renew, safe_site at k*, private (I1)",
                                           "a2_theory": "A2 (theory r-bar, no renewal), safe_site at k*, private (I1)",
                                           "marking": "marking, iid_step at p*, public (I2)"},
                      "runs": "30 runs per point, lender seed = policy seed; ratio of means with a run bootstrap "
                              "(M11, M13); iid_step at T = 3000 (M12)",
                      "rho": f"rho = {RHO}", "status": STATUS,
                      "LB_C_max": LIMIT_NEAR_MARKING if data["limit_marking"] else MAIN_LABELS["LB_C_max"]}
    data["sources"] = list(inp.sources)
    return data


def theory_specs(block: Mapping, labels: Mapping) -> list[dict]:
    return [dict(x=block["O1B"]["m"], y=block["O1B"]["value"], kind="upper", label=labels["O1B"]),
            dict(x=block["O1D"]["m"], y=block["O1D"]["value"], kind="upper", label=labels["O1D"]),
            dict(x=block["LB_A"]["m"], y=block["LB_A"]["value"], kind="lower", label=labels["LB_A"]),
            dict(x=block["LB_C_max"]["m"], y=block["LB_C_max"]["value"], kind="limit", label=labels["LB_C_max"])]


def policy_env_handles(keys: Sequence[str], envs: Mapping[str, tuple[str, str]] = ENVS) -> list:
    """C52 (design/ms7/plan.md §4, T1 scan): the legend entries of the policies, each drawn as its series is (the
    line style of its information class, `envs`, with its marker), in style.legend_order. C62: `envs` for a figure
    with policies beyond Fig. 6's (sf_e10_rho's A3, private information)."""
    out = []
    for k in style.legend_order(keys):
        kw = style.policy_kwargs(k, env=envs[k])
        out.append((Line2D([], [], **kw), kw["label"]))
    return out


def draw_panel(ax, block: Mapping, labels: Mapping, *, ylabel: bool = True, legend: bool = False,
               label_top_pad_pt: float = 0.0) -> None:
    """Series of the two information classes and the four theory lines, labeled in a column right of m_max. With
    `legend`, the corner legend (plan §5) in two rows, the policies and then the line styles, on headroom above the
    data (no corner is empty: O1-B and O1-D cross the upper left), its line-style samples in black (the theory lines
    are grey); the headroom is set before the theory labels are placed, so that their spacing holds on the final
    scale. Marking's dashed line lies on O1-C's limit, so it runs on a white underlay (style.halo) drawn above the
    theory lines and below the other data: its dash gaps show white, not grey. The y axis then starts low enough for
    the markers of the lowest ratio to clear the x spine (clear_floor)."""
    draw_e10_series(ax, block, KEYS, envs=ENVS)
    for ln in [ln for ln in ax.lines if getattr(ln, "_sublet_policy", None) == "marking"]:
        style.halo(ln, UNDERLAY_PT).set_zorder(style.Z_THEORY + 0.1)
    specs = theory_specs(block, labels)
    ms = sorted({m for k in KEYS for m in block[k]["m"]} | set(block["O1B"]["m"]))
    m_axis(ax, ms, [sp["label"] for sp in specs])
    lo, hi = data_range(*(block[k][f] for k in KEYS for f in ("ratio", "ci_lo", "ci_hi")),
                        *(sp["y"] for sp in specs))
    ratio_log2_axis(ax, min(lo, 1.0), hi)
    if legend:
        # C52 (design/ms7/plan.md §4, T1 scan): each policy's sample in its series' own line style (marking dashed,
        # public; as built, every sample solid, which contradicted the second row's key)
        # C62: the dashed samples (marking's, public information's) with their dashes centered on the sample, whole
        # at both ends (fig7_e2_e6.centered_dashes), and the mathtext label on its row's plain baseline
        legs = legend_rows(ax, [centered_dashes(policy_env_handles(KEYS)),
                                centered_dashes(style.env_handles("information", color="black"))])        # C52
        for lg in legs:
            align_baselines(lg.get_texts())
        legend_headroom(ax, legs, data_top=ax.get_ylim()[1])
    clear_floor(ax, data_range(*(block[k]["ratio"] for k in KEYS))[0])
    # C62: the labels' own heights (common.text_height_pt; their mathtext lines are taller than LINE_STEP_PT allows),
    # placed so that none is level with another line's end (at 7 pt "RR-renew bound" and "marking bound" stay level
    # with their lines, and LB_A's label, whose end RR-renew's covers, moves below them with a leader)
    right_theory_lines(ax, specs, measured=True, clear_ends=True, top_pad_pt=label_top_pad_pt)   # sf_e10_rho: titles
    style.ygrid(ax)
    if ylabel:
        ax.set_ylabel(labels["y"])
        if legend:      # C62: centered on the spine (the data), not on the axes with the legend's headroom
            y0, y1 = (math.log(v) for v in ax.get_ylim())
            lo_s, hi_s = (math.log(v) for v in ax.spines["left"].get_bounds())
            ax.yaxis.label.set_y(0.5 * (lo_s + hi_s - 2.0 * y0) / (y1 - y0))


def draw(data: Mapping) -> Any:
    fig = style.new_figure(NAME)
    (ax,) = style.panel_row(fig, (1,))
    draw_panel(ax, data, data["labels"], legend=True)
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
