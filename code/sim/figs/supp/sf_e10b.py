"""sf_e10b: E10(b), A3 (private information, I1) against A4 (public information, I2) on general core instances
(design/sim_spec_ms3.md §8.7, §5.4, M15, M49; plan §4, part S-F). Evidence on C-O1b, a CONJECTURE.

(a) `safe_site`, rho = 4; (b) `safe_site`, rho = 16; (c) `trace`, rho = 4; (d) `trace`, rho = 16 (titled with the
reader-facing names of the lenders, labels.sched: "Safe-site lender, ρ = 4", ..., as in sf_e10_cross): E[ALG] / E[LB]
against m (Q39's LB = max(LP, MILP dual bound), so an upper bound on E[ALG] / E[OPT]) with its 95% interval and a
black tick at the ratio to the MILP incumbents where it differs from `ratio` by more than 1% (e10/summary.json
b.<sched>.<rho>.<m>.{A3, A4}: `ratio`, `ci95` and `inc`, E[ALG] / E[incumbent]; common.inc_ticks). Dash-dot:
min(rho, m) and min(rho, 1 + log2 m), C-O1b's orders up to polylog factors, not bounds (unproven). Each order line
has its own label in the panels where the two end apart (no label level with the other's end); where they end on
one point (rho = 4, both reach rho), one label names both. Where A3 and A4 agree within AGREE_MAX_PCT at every m, a
key next to them says so (A3 = A4 where they are equal; common.agree_entry, agree_key; `agree` in the extract).
MS7 C62 (the type scale of style.py): the panel titles at the caption size (style.LABEL_PT), each on its letter's
baseline as printed, their rho in math (common.align_baselines); the order labels in math, min(rho, m) and
min(rho, 1 + log_2 m), as plotted and as the caption states them (as built upright, with "log m"), stacked on their
own heights (right_theory_lines(..., measured=True)); the shared y axis rises (label_room) where the label of the
order ending at rho = 16 would reach the titles. No plotted number changes.
C62 fix round (the supplement's critic): the four panels share the y scale and the m range, so they get one data
width (equal_data_ratios, as built 1.20, 0.95, 1.20, 0.95 in, which made the order lines' slopes look different):
the row is drawn once, each axes' label column measured (its width less its data width: (b) and (d) reserve more,
for their two order labels), and drawn again with each axes as wide as the common data width plus its own column,
so that the gutters between a label column's text and the next panel are equal too. A key keeps 1 em (7 pt) beside
an order label level with it (fig5_e1_e10.off_spine(..., text_pt=TEXT_GAP_PT); with (d)'s wider data area the
shared rule put its key 4 pt before "min(rho, m)", which read as one line) and 4 pt from the spine.

Run from code/sim: python -m figs.supp.sf_e10b [--from-extract [JSON]].
"""
from __future__ import annotations

import math
import sys
from typing import Any, Mapping, Sequence

import numpy as np

from figs import style
from figs.common import (AGREE_MAX_PCT, E10, INC_TICK_RULE, agree_entry, agree_key, align_baselines, cli, data_range,
                         finite, inc_ticks, m_axis, maybe, need, num_items, panel_title, points_pt, ratio_log2_axis,
                         right_theory_lines, text_height_pt)
from figs.fig5_e1_e10 import TEXT_GAP_PT, off_spine
from figs.inputs import Inputs

NAME = "sf_e10b"
TAGS = {"a3": "A3", "a4": "A4"}
PANELS = (("a", "safe_site", 4), ("b", "safe_site", 16), ("c", "trace", 4), ("d", "trace", 16))
style.register_supplementary(NAME, "W2", 2.2)
TITLE_CLEAR_PT = 2.0                # C62: an order label ends at least this far below the axes top (label_room)
# C62: the orders and the titles' rho in math, italic as on the axes and in the caption, and the order's logarithm to
# base 2 as plotted and as the caption states it (as built "min(ρ, m)", "min(ρ, 1 + log m)" and "ρ = 4", upright);
# each title on its letter's baseline as printed (align_baselines)
LABELS = {"x": "Sites m", "y": "E[ALG] / E[LB]", "order_m": "$\\min(\\rho,m)$,\nC-O1b order",
          "order_log": "$\\min(\\rho,$\n$1+\\log_2m)$,\nC-O1b order", "orders": "C-O1b\norders",
          "panel": "{}, $\\rho={:g}$",
          "sched": {"safe_site": "Safe-site lender", "trace": "Trace lender"},
          "tick": f"black tick: E[ALG] / E[MILP incumbent] (inc), {INC_TICK_RULE}", "status": {"C-O1b": "CONJECTURE"}}


def build(inp: Inputs) -> dict:
    e10 = inp.json(E10)
    out = {}
    for p, sched, rho in PANELS:
        block = need(e10, "b", sched, rho, what=E10)
        d = {"sched": sched, "rho": float(rho)}
        for key, tag in TAGS.items():
            s = {"m": [], "ratio": [], "ci_lo": [], "ci_hi": [], "inc": [], "note": []}
            for m, mk, _ in num_items(block):
                ent, note = maybe(block, mk, tag)       # null or missing: kept with its note (§2.6, §8.7)
                ent = ent if isinstance(ent, Mapping) else {}
                if note is None and ent.get("ratio") is None:
                    note = ent.get("ratio_note") or "null"
                lo, hi = (ent.get("ci95") or [None, None])[:2]
                for f, v in zip(s, (m, ent.get("ratio"), lo, hi, ent.get("inc"), note)):
                    s[f].append(v)
            d[key] = s
        ms = sorted({m for k in TAGS for m in d[k]["m"]})
        d["orders"] = {"m": ms, "min_rho_m": [min(rho, m) for m in ms],
                       "min_rho_1_log2m": [min(rho, 1 + math.log2(m)) for m in ms]}
        d["agree"] = agree_entry("a3", "a4", d["a3"]["ratio"], d["a4"]["ratio"], AGREE_MAX_PCT)
        out[p] = d
    out["labels"] = {**LABELS, "agree": {p: out[p]["agree"]["key"] for p, _, _ in PANELS if out[p]["agree"]}}
    out["sources"] = list(inp.sources)
    return out


def label_room(ax, end: float, label_h_pt: float) -> None:
    """C62: raise the top of the shared log y axis, where needed, so that an order label centered on a line ending at
    `end` (the largest order, rho = 16) ends TITLE_CLEAR_PT below the axes top, clear of the panel titles above it
    (caption size since C62; as built at 7 pt the label column reached the axes top under smaller titles)."""
    y0, y1 = ax.get_ylim()
    need = 0.5 * label_h_pt + TITLE_CLEAR_PT
    h = style.axes_rect_in(ax)[3] * style.BP_PER_IN
    a = math.log(end / y0)
    if (math.log(y1 / y0) - a) / math.log(y1 / y0) * h < need:
        ax.set_ylim(y0, y0 * math.exp(a / (1.0 - need / h)))


def data_width_in(ax) -> float:
    """C62 fix round: the width (inches) of the data area of `ax`: the x spine's bounds where a label column sets them
    (common.label_column), else the axes' width."""
    b = ax.spines["bottom"].get_bounds()
    if b is None:
        return style.axes_rect_in(ax)[2]
    y = ax.get_ylim()[0]
    x0, x1 = (ax.transData.transform((v, y))[0] for v in b)
    return (x1 - x0) / ax.figure.dpi


def equal_data_ratios(axes: Sequence, total: float | None = None) -> list[float]:
    """C62 fix round: style.panel_row ratios (inches) that give the panels of a drawn row one data width: each axes as
    wide as that width plus its own label column (its width less its data width as drawn; common.label_column and
    right_theory_lines set the column in points, so it does not change with the axes' width), the axes' widths summing
    to `total` (default: their sum as drawn)."""
    w = [style.axes_rect_in(ax)[2] for ax in axes]
    col = [wi - data_width_in(ax) for wi, ax in zip(w, axes)]
    d = ((sum(w) if total is None else float(total)) - sum(col)) / len(axes)
    if d <= 0:
        raise style.StyleError(f"no room for one data width: label columns {col} in, total {total}")
    return [d + c for c in col]


def draw(data: Mapping) -> Any:
    # C62 fix round: drawn twice, the second time with the axes widths that give the four panels one data width
    fig = draw_row(data, (1, 1, 1, 1))
    return draw_row(data, equal_data_ratios(fig.axes))


def draw_row(data: Mapping, ratios: Sequence[float]) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    # one y scale for the four panels (the orders reach rho = 16), so (b)-(d) share (a)'s y axis and its label: the
    # 0.36 in per panel this saves goes to the data, which the label column of the two order lines narrows
    axes = style.panel_row(fig, ratios, legend=True, sharey=(False, True, True, True))
    lo, hi = data_range(*(data[p][k][f] for p, _, _ in PANELS for k in TAGS for f in ("ratio", "ci_lo", "ci_hi")),
                        *(data[p]["orders"][f] for p, _, _ in PANELS for f in ("min_rho_m", "min_rho_1_log2m")))
    ratio_log2_axis(axes[0], min(lo, 1.0), hi)          # the shared y axis, set once
    label_room(axes[0], hi, max(text_height_pt(fig, lab[k]) for k in ("order_m", "order_log", "orders")))
    for ax, (p, sched, rho) in zip(axes, PANELS):
        d = data[p]
        for key in TAGS:
            s = d[key]
            x, y, l, h = (finite(s[f]) for f in ("m", "ratio", "ci_lo", "ci_hi"))
            style.plot_policy(ax, key, x, y)
            ok = np.isfinite(y) & np.isfinite(l) & np.isfinite(h)
            if ok.any():
                style.errorbars(ax, key, x[ok], y[ok], l[ok], h[ok])
            inc_ticks(ax, x, y, s["inc"])
        o = d["orders"]
        apart = abs(o["min_rho_m"][-1] - o["min_rho_1_log2m"][-1]) > 1e-9 * abs(o["min_rho_m"][-1])
        if apart:               # each line its own label, none level with the other line's end
            specs = [dict(x=o["m"], y=o["min_rho_m"], kind="unproven", label=lab["order_m"]),
                     dict(x=o["m"], y=o["min_rho_1_log2m"], kind="unproven", label=lab["order_log"])]
        else:                   # one end, one label naming both lines; the second line is drawn unlabeled
            specs = [dict(x=o["m"], y=o["min_rho_m"], kind="unproven", label=lab["orders"])]
            style.theory_line(ax, o["m"], o["min_rho_1_log2m"], "unproven", lab["orders"])[1].remove()
        m_axis(ax, o["m"], [sp["label"] for sp in specs])
        right_theory_lines(ax, specs, clear_ends=True, measured=True)     # C62: the labels' own heights
        style.ygrid(ax)
    axes[0].set_ylabel(lab["y"])
    for ax, letter, (p, sched, _) in zip(axes, style.panel_letters(axes), PANELS):
        # C62: the title at the caption size, on its letter's baseline as printed
        title = panel_title(ax, letter, lab["panel"].format(lab["sched"][sched], data[p]["rho"]),
                            fontsize=style.LABEL_PT)
        align_baselines([letter, title])
        key = agree_key(ax, data[p].get("agree"), data[p], x="m", y="ratio")
        if key is not None:     # C62 fix round: clear of the spine, and 1 em beside an order label level with it
            off_spine(ax, key, np.concatenate([points_pt(ax, data[p][k]["m"], data[p][k]["ratio"]) for k in TAGS]),
                      text_pt=TEXT_GAP_PT)
    style.legend_row(fig, list(TAGS))
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
