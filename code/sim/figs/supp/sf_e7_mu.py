"""sf_e7_mu: E7's week cost against the stranding price mu / beta~ (design/sim_spec_ms4.md §8.2, §3.7(b), M2, M26;
plan §4, part S-F).

Week cost over BL0a in overflow accounting (M2) against mu / beta~ in {0.2, 0.5, 1, 2} (log): the median over the
alignments x policy seeds of the main grid with its 95% bootstrap interval (e7/main/summary.json
runs.<mu>.<tag>.overflow_over_bl0a, §3.10), dodged in x: (a) Sublet, A7 + guard, A7 and A6; (b) Sublet, BL5, BL1, BL2
and BL4 (plan §5: at most six lines per panel; Sublet in both). The dodge runs left to right in PANELS' order, Sublet
last (drawn on top); in (a) A6 sits between A7 + guard and Sublet (as built, A6, A7, A7 + guard, Sublet: at
mu / beta~ = 2 Sublet's interval, up to 0.83, ran one dodge step from A7 + guard's diamond at 0.81 and touched it),
in (b) BL1 between BL4 and BL2 (as built, BL4, BL2, BL1: BL2's long interval at mu / beta~ = 2, up to 0.93, rose
beside BL4's marker at 0.92 one dodge step away and read as BL4's). The panels share y; the level 1 (all-fallback)
is a reference line. Each panel is drawn in two passes (ms4_lib.draw_series_layered; print check of 2026-10-27): every
line first, then every interval bar and marker above all lines, Sublet's markers last, so that no line runs over
another series' marker (as built, Sublet's thick line, drawn last with its markers, cut A7 + guard's and A7's diamonds
at mu / beta~ = 0.5). The eight keys need two legend rows (one row is 10.1 in at 9 pt, about 7.9 in at C62's 7 pt,
against 7.08 in; legend_row(..., rows=2)). BL4's yellow line has a black casing (ms4_lib.line_casing), in the plot and
in its legend sample: without it, it printed lighter in greyscale than the reference line at 1 beside which it runs.
labels.note, the caption source, names the policies by their legend names (style.POLICIES; the cased ones from the
registry's edge colors) and states the pairs of PAIRS whose series are identical (medians and both interval
ends equal to 1e-12 relative, common.agreement), at every mu / beta~ or at the levels where they are (on the E7
outputs: BL5 with Sublet in (b), A7 with A7 + guard in (a), at every level; the one line hides the other); the pairs
and their levels are in the extract's `coincide`.

MS6 C47 (design/ms6_spec.md M2, M3, M4): Sublet, BL5 and A7 + guard above are the summary's tags, drawn as the
configuration keys sublet_ms4 ("Lagged RetroRenting + one-way guard ($B_0=10\\%$ BL0a)"), bl5_lag and a7_ms4 ("PD
heuristic + one-way guard ($B_0=10\\%$ BL0a)"; C46: both guards ran at MS4's allowance, which their labels and
labels.note, from the summary's B0_rule, state). With these labels the two aligned legend rows are 8.38 in wide, so
the eight entries, in the registry's order, stand side by side in rows of their own, filled as far as the width
allows, with 1.4-em handles (ms4_lib.split_rows, legend_rows_above): three rows, the two guards' long labels in the
first.

Run from code/sim: python -m figs.supp.sf_e7_mu [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

from matplotlib.lines import Line2D

from figs import style
from figs.common import agreement, cli, need, ratio_log10_axis
from figs.inputs import Inputs
from figs.supp.ms4_lib import (CASING_PT, DRAWN_KEY, agg_point, b0_share_text, draw_series_layered, finite_values,
                               grid_counts, legend_rows_above, level_axis, levels_of, runs_text, series_over,
                               split_rows, tag_of)

NAME = "sf_e7_mu"
MAIN = "code/sim/out/e7/main/summary.json"
KEYS = style.SUPP_POLICIES_MS4[NAME]          # sublet_ms4, a7_ms4, a7, a6, bl5_lag, bl1, bl2, bl4
# C47 (design/ms6_spec.md M2, M3, M4): the configuration keys of MS4's allowance in place of the frozen sublet, bl5 and
# a7_guard; the guard around the lagged BL5 still last, drawn on top
PANELS = (("a", ("a7", "a7_ms4", "a6", "sublet_ms4")), ("b", ("bl4", "bl1", "bl2", "bl5_lag", "sublet_ms4")))
PAIRS = (("bl5_lag", "sublet_ms4"), ("a7", "a7_ms4"))   # series that may coincide: labels.note states where they do
GUARDS = ("sublet_ms4", "a7_ms4")              # the one-way guards, at MS4's allowance (labels.note, C47)
LEGEND_ROWS = 3                               # C47: legend_rows_above's rows (one column-aligned legend_row of two
#                                               rows is 8.38 in wide with sublet_ms4's label; C46: with a7_ms4's,
#                                               the two guards fill one row of their own)
style.register_supplementary(NAME, "W2", 2.5)          # C46: 2.5 in (was 2.2), for the third legend row
LABELS = {"x": r"Stranding price $\mu/\tilde{\beta}$", "y": "Cost / all-fallback",
          # C47 (print check of the gate): no build or milestone names ("(M2)", "(MS4's allowance)")
          "note": "overflow accounting; medians over {runs} with 95% bootstrap intervals; level 1: {bl0a}"
                  "{guards}{casing}{coincide}",
          "guards": "; {names} run at B0 = {pct} of each run's all-fallback cost",
          "casing": "; {names}'s line in a black casing",
          "coincide_first": "{a} coincides with {b} in ({p})", "coincide_more": ", and {a} with {b} in ({p})",
          "coincide_all": "; {pairs}, at every mu/beta~ (identical medians and 95% intervals)",
          "coincide_some": "; {pairs} at mu/beta~ = {levels} (identical medians and 95% intervals)"}


def cased_key(key: str) -> bool:
    """A yellow key (edge color other than its color), whose line ms4_lib.line_casing draws in a black casing."""
    p = style.policy(key)
    return p.edgecolor is not None and p.edgecolor.upper() != p.color.upper()


def coincide(data: Mapping, levels: Sequence[float]) -> list[dict]:
    """The pairs of PAIRS drawn in one panel whose medians and interval ends are equal (common.agreement within 1e-12
    relative) at a level: [{pair, panel, levels}] for the levels where they are, in PAIRS' order; a pair equal
    nowhere is left out."""
    out = []
    for ka, kb in PAIRS:
        for p, _ in PANELS:
            if ka not in data[p] or kb not in data[p]:
                continue
            sa, sb = data[p][ka], data[p][kb]
            at = []
            for i, x in enumerate(levels):
                ags = [agreement([sa[f][i]], [sb[f][i]]) for f in ("median", "ci_lo", "ci_hi")]
                if all(ag is not None and ag["within_pct"] == 0 for ag in ags):
                    at.append(x)
            if at:
                out.append({"pair": [ka, kb], "panel": p, "levels": at})
            break
    return out


def coincide_text(pairs: Sequence[Mapping], levels: Sequence[float]) -> str:
    """labels.note's statement of the coinciding pairs (registry labels): those equal at every level in one clause
    ('at every mu/beta~'), each other pair in a clause with its levels; '' where no pair coincides."""
    def clause(cs):
        return "".join(LABELS["coincide_more" if j else "coincide_first"].format(
            a=style.POLICIES[c["pair"][0]].label, b=style.POLICIES[c["pair"][1]].label, p=c["panel"])
            for j, c in enumerate(cs))

    every = [c for c in pairs if len(c["levels"]) == len(levels)]
    out = LABELS["coincide_all"].format(pairs=clause(every)) if every else ""
    for c in pairs:
        if c not in every:
            out += LABELS["coincide_some"].format(pairs=clause([c]), levels=", ".join(f"{x:g}" for x in c["levels"]))
    return out


def build(inp: Inputs) -> dict:
    main = inp.json(MAIN)
    tags = tag_of(need(main, "meta", "tags", what=MAIN), KEYS, MAIN, drawn=DRAWN_KEY)       # C47: recorded keys
    runs = need(main, "runs", what=MAIN)
    levels = levels_of(runs, f"{MAIN} runs")
    out = {}
    for p, keys in PANELS:
        out[p] = {k: series_over(runs, levels, tags[k], lambda e: agg_point(e, "overflow_over_bl0a"), "mu")
                  for k in keys}
    runs_txt = runs_text(*grid_counts(need(main, "meta", "grids", what=MAIN), f"{MAIN} meta.grids"))
    mus = [x for x, _ in levels]
    same = coincide(out, mus)
    cased = [style.POLICIES[k].label for k in style.legend_order(KEYS) if cased_key(k)]
    pct = b0_share_text(main["meta"].get("B0_rule"))
    guards = LABELS["guards"].format(names=" and ".join(style.POLICIES[k].label for k in GUARDS), pct=pct) \
        if pct else ""
    note = LABELS["note"].format(runs=runs_txt, coincide=coincide_text(same, mus), guards=guards,
                                 bl0a=style.POLICIES["bl0a"].label.lower(),
                                 casing=LABELS["casing"].format(names=" and ".join(cased)) if cased else "")
    out.update({"mu_levels": mus, "tags": tags, "coincide": same,
                "labels": {**LABELS, "note": note},
                "meta": {"git_revision": need(main, "meta", "git_revision", what=MAIN),
                         "reduced": bool(main["meta"].get("reduced")), "accounting": "overflow",
                         "B0_rule": main["meta"].get("B0_rule")},
                "sources": list(inp.sources)})
    return out


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    axes = style.panel_row(fig, (1, 1), legend=LEGEND_ROWS, sharey=(False, True))
    v = finite_values(*(data[p][k][f] for p, keys in PANELS for k in keys if k in data[p]
                        for f in ("median", "ci_lo", "ci_hi")))
    v = v[v > 0]
    lo, hi = (float(v.min()), float(v.max())) if v.size else (0.9, 1.1)
    ratio_log10_axis(axes[0], lo, max(hi, 1.0))
    for ax, (p, keys) in zip(axes, PANELS):
        keys = [k for k in keys if k in data[p]]
        draw_series_layered(ax, [(key, data[p][key], i, None) for i, key in enumerate(keys)], "mu", n=len(keys))
        level_axis(ax, data["mu_levels"])
        style.reference_line(ax, y=1.0)
        style.ygrid(ax)
        ax.set_xlabel(lab["x"])
    axes[0].set_ylabel(lab["y"])
    style.panel_letters(axes)
    pairs = []                                         # a yellow key's sample in its black casing, as drawn
    for (h, t), k in zip(style.policy_handles(KEYS), style.legend_order(KEYS)):
        p = style.policy(k)
        if cased_key(k):
            h = (Line2D([], [], color=p.edgecolor, linewidth=p.linewidth + CASING_PT, solid_capstyle="butt"), h)
        pairs.append((h, t))
    # C47: the entries in the registry's legend order, side by side in rows of their own, with the shorter handles of
    # ms4_lib.legend_rows_above (style.legend_row's two aligned rows are 8.38 in wide); C46: the guards in the first
    # row, the other policies halved over the next two (filled greedily, the last row held CoCaR-style alone)
    order = style.legend_order(KEYS)
    guards = [e for e, k in zip(pairs, order) if style.policy(k).group == "guarded"]
    rest = [e for e, k in zip(pairs, order) if style.policy(k).group != "guarded"]
    half = (len(rest) + 1) // 2
    rows = [r for part in (guards, rest[:half], rest[half:]) if part for r in split_rows(fig, part, max_rows=1)]
    legend_rows_above(fig, rows, n_rows=LEGEND_ROWS)
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
