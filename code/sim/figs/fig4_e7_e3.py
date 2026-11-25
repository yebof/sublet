"""Fig. 4: end-to-end savings and the value of sharing (E7, E3); design/sim_spec_ms4.md §8.1, plan §1.

Claims (plan §1): (a) and (b) none, a system result (every A8 run reports its certificate, Theorem W; the A8 runs use
Sublet's MS4 allowance, B0 = 10% of the run's own BL0a, sim_spec_ms4 §3.3, M36). (c) siloed OPT <= b * shared OPT by
the copy argument (design §5.5, E3), attained on C3-P7's instance (PROVEN, elementary).

(a) Cost breakdown (E7 main grid, code/sim/out/e7/main/summary.json runs.1.<tag>): week cost / BL0a in overflow
    accounting (M2) as horizontal bars, top to bottom Sublet, RetroRenting-style (BL5), Greedy renting (BL1),
    CoCaR-style (BL4), PD heuristic (A7), PD heuristic + guard (A7 + guard), Two-timescale PD (A6), named on the y
    ticks; each bar the median of overflow_over_bl0a over the alignments x seeds, split into the ledger components in a
    grey ramp in proportion to their mean ratios to BL0a (components_over_bl0a; sf_e6b's component_groups, so that
    `lease`, the sum of lease_prepaid and lease_rent, is counted once), outlined in the policy's color (BL4 in its black
    edge color), with the 95% bootstrap interval of the median as a whisker. A component that is 0 in every bar
    (loading) has no segment and no key entry and is named in the extract (a.zero_components). The key of the components
    sits in an empty band above the bars (sf_e6b's rows_below), starting at the left edge of the policy names, on one
    row where the label of BL0a then fits over its line beside it, else on two. BL0a is a vertical line at 1 across the
    bars in its registry style, drawn above them in a white casing (Z_BL0A, BL0A_CASING_PT: behind them, or on the
    darker greys, it did not read where a bar crosses 1), labeled directly "All-fallback" in the band above the line's
    top (the label spans x = 1), level with the key's last row and ending LETTER_GAP_PT left of the slot of (b), where
    the letter "(b)" sits just above that row. BL0b lies far right of the bars (meta: bl0b_overflow_usd / bl0a_usd, the
    median over the alignments): it has a row of its own below the bars, named "Provision for peak" on the y ticks like
    the bars, with a short arrow in its registry color at the right end of the x axis and its ratio, rounded to one
    decimal, left of the arrow (in place of plan §1's reference line; M2). BL0a's line ends half a row below the last
    bar, or, where BL0b's ratio lies under it (within BL0A_CLEAR_PT of x = 1), BL0A_CLEAR_PT above the ratio's top, so
    that it does not point into the number (StyleError where that end would cut the last bar). Own capacity is not
    drawn; the caption gives its USD (meta.own_capacity_usd, the median over the alignments).
(b) Pooling (E7 grid (c), links.<n>.<tag>; n = 5 is the main grid, runs.1): the saving over BL0a in percent, overflow
    accounting (saving_pct), median with its 95% bootstrap interval, against the number of cross-region routing links n,
    for Sublet, BL5 and BL1 (dodged in x by DODGE_LINKS, Sublet drawn last); a reference line at 0, the level of BL0a.
    The y label is "Saving (%)": §8.1's "Saving over all-fallback (%)" is 1.52 in long at 9 pt, longer than the 1.41-in
    axes it would run along; the caption says "over all-fallback". Where Sublet and BL5 agree within
    common.AGREE_MAX_PCT at every n, a key on the free space says so (common.agree_entry, agree_key; Sublet executes BL5
    unchanged while its guard does not abort), kept off the levels of the y tick labels within TICK_CLEAR_PT (one font
    size) of the spine (agree_key_clear: a key line level with a tick label next to the spine read as its continuation,
    "10 = RetroRenting-style"); where no form of agree_key then fits (at 9 pt, two lines of the key do not fit between
    two tick labels, and "= RetroRenting-style" does not fit one font size right of the spine), its text is broken
    after the "=", "Sublet =" over "RetroRenting-style", as a label without the markers.
(c) Sharing (E3, code/sim/out/e3/summary.json ratios.<b>.<u>.<mu>.<tag>, opt.<b>.<u>.<mu>) at u = 8 and
    mu / beta~ = 1: cost / shared OPT (ratio_LB, Q39's LB) against b on log2 axes for Sublet and A6, shared (solid,
    filled markers) and siloed (dashed, open markers; env sharing), and BL2, each with its 95% interval, dodged in x
    by DODGE_OCT_C into the slots C_SLOTS, left to right A6, Sublet, A6 siloed, Sublet siloed, BL2, then OPT. The
    slots are apart from the drawing order (C_KEYS, Sublet last); on E3's data, this is the one order of the 120
    that (i) keeps the dodge's shear from reversing two lines that run within 5% of each other over neighboring b
    at b >= 2 (on a rising pair the left-dodged line reads higher at a given x: with BL2 left of A6 siloed, BL2's
    line read about 6% above A6 siloed's from b = 4 on, though BL2's medians are 0.6-4.8% lower; here BL2 sits right
    of A6 siloed; inside the b = 1 cluster, where all five lie within 3%, BL2's thin line runs just above Sublet's
    thick one up to their crossing near b = 1.8), (ii) leaves the label of b room (with A6 siloed in either of the two left slots, its interval at
    b = 32, up to 3.3, takes it) and (iii) puts the fewest pairs of markers within 3 pt of each other at b >= 2 (no
    order puts none): one, BL2 and Sublet siloed at b = 4 (2.4 pt apart; the only neighbors that run within 5%, at
    b = 4 and 8; at b = 1 all five lie within 3%). The lines are drawn first, in C_KEYS's order (Sublet's above the
    others), then every interval bar (Z_C_BARS) and above them every marker (Z_C_MARKS: OPT's stars, then C_KEYS's
    order), so that no line runs over a marker (with each series drawn whole in turn, Sublet's line hid most of
    BL2's triangle at b = 2 and A6's line crossed A6 siloed's open hexagon there); siloed OPT / shared OPT as black
    brackets in the `opt` style (point_median with [lo_min, hi_max]; an open star where the bracket is open: a
    shared MILP without a result, the LB from the LP alone, §4.6); grey dashed y = b, the copy bound on siloed OPT
    (attained on C3-P7's instance), labeled "b, bound on\\nsiloed OPT", or where that does not fit
    "b, bound\\non OPT" (the legend's name of the stars), so that the label says what it bounds (the policies'
    points at b = 1 lie above the line: it bounds the stars, not the policies), its label on the free space nearest
    to the drawn part of the line and nearer to it than to any data point (common.free_spot), its lines
    left-aligned, joined to the line by a thin grey leader where it lies more than LEADER_MIN_PT from it, since a
    label column right of the data (sim_spec_ms3 §8, common.right_theory_lines) would take 0.6 of the 1.21-in panel.
    The y axis spans the data and brackets with the level 1, at least up to C_TOP_MIN, not the bound's b = 32: the
    line leaves through the top (with the bound in the range, the measured ratios filled the axis's bottom quarter).
Legend: one row of the keys that (b) and (c) share (M3), OPT's entry the star alone as drawn in (c); the siloed line
style, the stars (siloed OPT) and the grey line (b, the bound on siloed OPT) are named in the caption.

The caption draft (at most 3 lines, plan §5) is in the extract (labels.caption, with its length), every number read
from the summaries. Run from code/sim: python -m figs.fig4_e7_e3 [--from-extract [JSON]] (figs.common.cli).

C62 (2026-11-24: no text larger than the caption; style's 7-pt text and 7.97-pt axis labels and letters): the
sizes and measurements above that say "at 9 pt" are those of the build; the layout is measured at draw time, so the
figure follows the smaller text without a change of its rules. Two texts now print on the baseline of the row they
share: BL0b's ratio is set by its row's center baseline, as the y tick labels are (centered on the row, it printed
0.7 pt above "Provision for peak"), and the "All-fallback" label is moved onto the printed baseline of the key's
last row (common.printed_baselines_pt; centered on the row, it printed 0.3 pt above it).
"""
from __future__ import annotations

import math
import statistics
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib import patheffects
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.transforms import IdentityTransform

from figs import style
from figs.common import (AGREE_MAX_PCT, KEY_PAD_PT, LEADER_PT, MissingKey, agree_entry, agree_key, ci_of, cli,
                         data_range, finite, free_spot, maybe, need, num_items, place_label, points_pt,
                         printed_baselines_pt, ratio_log2_axis, text_width_in, thin_tick_labels)
from figs.inputs import Inputs
from figs.supp.sf_e6b import component_groups

# C62: the bars' height, their outline and the key band of (a) as built, from sf_e6b until C62, which restyled sf_e6b
# (its bars 0.56 rows high, its keys on the letters' line, rows_below removed); this figure and fig4_v2 (which imports
# BAR_H and BAR_EDGE_PT from here) keep them
BAR_H = 0.62                    # (a): bar height in rows (sf_e6b.BAR_H until C62)
BAR_EDGE_PT = 0.8               # (a): a bar's outline in its policy's color (sf_e6b.BAR_EDGE_PT)


def rows_below(axes, n_rows: int, h_key: float) -> None:
    """One categorical y range for the panels of `axes`, extended upward by an empty band of h_key inches for the key
    (sf_e6b.rows_below until C62)."""
    h_ax = style.axes_rect_in(axes[0])[3]
    extra = n_rows * h_key / (h_ax - h_key)
    for ax in axes:
        ax.set_ylim(n_rows - 0.5, -0.5 - extra)


NAME = "fig4"
E7 = "code/sim/out/e7/main/summary.json"
E3 = "code/sim/out/e3/summary.json"

MU = 1                                                             # mu / beta~ of (a), (b) and (c) (§8.1)
BARS = ("sublet", "bl5", "bl1", "bl4", "a7", "a7_guard", "a6")     # (a), top to bottom (design E7, Q43)
B_KEYS = ("bl5", "bl1", "sublet")                                  # (b), in drawing order: Sublet last
C_KEYS = ("bl2", "a6_siloed", "a6", "sublet_siloed", "sublet")     # (c), in drawing order: Sublet last
# (c)'s dodge slots, left to right, then OPT's, apart from the drawing order (module docstring): BL2 right of A6 siloed,
# so that the dodge's shear keeps their true order (BL2 lower) from b = 4 on; A6 siloed in neither of the two left
# slots (there its interval at b = 32 takes the room of the label of b); of E3's close pairs (within 5% at some
# b >= 2: BL2 and A6 siloed at b = 8 to 32, BL2 and Sublet at b = 2, A6 and A6 siloed at b = 2 and 4, BL2 and A6 at
# b = 4, BL2 and Sublet siloed at b = 4 and 8, A6 and Sublet siloed at b = 4, Sublet and Sublet siloed at b = 4) only
# BL2 and Sublet siloed are neighbors (at b = 1 all five lie within 3%)
C_SLOTS = ("a6", "sublet", "a6_siloed", "sublet_siloed", "bl2")
assert sorted(C_SLOTS) == sorted(C_KEYS)
C_ENV = {"sublet": "shared", "a6": "shared", "sublet_siloed": "siloed", "a6_siloed": "siloed"}
LEGEND = ("sublet", "a6", "bl5", "bl1", "bl2")                     # the keys that (b) and (c) share (M3), then OPT
COMPONENT_ORDER = ("lease", "loading", "routing", "fallback", "stranding")
# short names, so that the key of the components fits one row; lease is rent and billed term (lease_rent +
# lease_prepaid, sf_e6b.component_groups)
COMPONENT_LABEL = {"lease": "Lease", "loading": "Loading", "routing": "Routing", "fallback": "Fallback",
                   "stranding": "Stranding"}
LABELS = {"a_x": "Week cost / all-fallback", "b_x": "Cross-region links", "b_y": "Saving (%)",
          "c_x": "Borrowers b", "c_y": "Cost / shared OPT", "theory": "b, bound on\nsiloed OPT",
          "theory_forms": ["b, bound on\nsiloed OPT", "b, bound\non OPT"], "no_data": "no runs"}
STATUS = {"copy bound siloed OPT <= b * shared OPT, attained on C3-P7's instance": "PROVEN, elementary",
          "Theorem W(a)(b) for every A8 run (certificate per run)": "PROVEN for the engine as implemented under C1-C3, "
                                                                     "audited; W(c) CONJECTURE"}
X_PAD = 0.05                    # (a): the x axis ends this share beyond the largest bar or whisker (not in §8.1)
KEY_HANDLE = 1.0                # (a): the key's patches, in font sizes (sf_e6b's legend_top uses 1.2: one row here)
KEY_COLUMNS = 0.8               # (a): the gap between the key's entries, in font sizes (sf_e6b: 0.9)
KEY_TOP_PT = 1.8                # (a): the key's top this far below the axes top, clear of the letter "(a)"
KEY_LEFT_IN = 0.03              # (a): the key starts this far right of the panel's slot, where the longest name does
LABEL_GAP_PT = 3.0              # (a): least gap between the key and the "All-fallback" label
LETTER_GAP_PT = 3.0             # (a): least gap between the "All-fallback" label and the slot of (b) (its letter)
BL0A_CLEAR_PT = 3.0             # (a): least gap between BL0a's line and BL0b's ratio where the ratio lies under it
ARROW_IN = 0.2                  # (a): length of BL0b's arrow at the right end of the x axis
Z_BL0A = 1.65                   # (a): BL0a's line above the bars (1.5) and outlines (1.6), under the whiskers (1.7)
BL0A_CASING_PT = 1.2            # (a): white casing of BL0a's line (its width plus this), so that it reads on every grey
ARROW_TEXT_PT = 2.0             # (a): gap between BL0b's ratio and its arrow
C_MARGIN_OCT = 0.15             # (c): x margin beyond the outermost dodged markers, in octaves
C_TOP_MIN = 4.0                 # (c): the y axis reaches at least this ratio (room for the label of b above the data)
LEADER_MIN_PT = 4.0             # (c): a theory label farther than this from its line gets a leader (common.LEADER_PT)
DODGE_LINKS = 0.22              # (b): x dodge between neighboring series, in links (not in §8.1)
TICK_CLEAR_PT = style.TICK_PT   # (b): a key line level with a y tick label starts at least this far right of the spine
DODGE_OCT_C = 0.12              # (c): x dodge between neighboring series, in octaves (common.DODGE_OCT, 0.055, moves
#                                 six series by less than a marker in the 1.21-in panel; not in §8.1)
Z_C_BARS = style.Z_SUBLET + 0.1  # (c): every interval bar above every line (the highest, Sublet's, at Z_SUBLET)
Z_C_MARKS = Z_C_BARS + 0.05     # (c): every marker above every bar: OPT's stars here, the policies' above them in
Z_C_STEP = 0.01                 #      C_KEYS's order (Sublet's last), Z_C_STEP apart, under the theory label
assert Z_C_MARKS + Z_C_STEP * len(C_KEYS) < style.Z_THEORY_LABEL


# ---------------------------------------------------------------------------------------------------------------
# Inputs
def tag_map(summary: Mapping, what: str) -> dict:
    """{style key: tag} from meta.tags.<tag>.style_key (§3.5, §4.5)."""
    tags = need(summary, "meta", "tags", what=what)
    return {v["style_key"]: t for t, v in tags.items() if isinstance(v, Mapping) and v.get("style_key")}


def _need_tags(tags: Mapping, keys: Sequence[str], what: str) -> None:
    missing = [k for k in keys if k not in tags]
    if missing:
        raise MissingKey(f"{what}: no tag with style key {missing} in meta.tags")


def by_alignment(meta: Mapping, field: str, what: str) -> dict:
    """{alignment: value} of meta.<field> (E7 writes the references per alignment, §3.10), nulls left out."""
    d = need(meta, field, what=f"{what} meta")
    if not isinstance(d, Mapping):
        raise MissingKey(f"{what}: meta.{field} is {type(d).__name__}, not a map by alignment")
    return {k: float(v) for k, v in d.items() if not k.endswith("_note") and v is not None}


def bar_entry(e7: Mapping, tag: str) -> dict:
    """(a)'s bar of one tag: the median of overflow_over_bl0a with its interval and count, the grouped components'
    mean ratios to BL0a and the median of total_over_bl0a; a tag without runs gives null values with the note."""
    ent = need(e7, "runs", MU, tag, what=E7)
    agg = ent.get("overflow_over_bl0a") if isinstance(ent.get("overflow_over_bl0a"), Mapping) else {}
    lo, hi = ci_of(agg)
    raw = ent.get("components_over_bl0a")
    comps = component_groups(raw) if isinstance(raw, Mapping) and raw else {}
    tot = ent.get("total_over_bl0a") if isinstance(ent.get("total_over_bl0a"), Mapping) else {}
    out = {"tag": tag, "median": agg.get("median"), "ci_lo": lo, "ci_hi": hi, "n": agg.get("n"),
           "components_mean_over_bl0a": comps, "total_over_bl0a_median": tot.get("median")}
    if agg.get("median") is None:
        out["note"] = agg.get("median_note") or ent.get("note") or "null"
    return out


def series_entry(block: Mapping | None, field: str) -> tuple:
    """(median, ci_lo, ci_hi, n, note) of the aggregate block[field]; nulls with their note."""
    if not isinstance(block, Mapping):
        return None, None, None, None, "missing"
    agg = block.get(field)
    if not isinstance(agg, Mapping):
        return None, None, None, None, block.get(f"{field}_note") or "missing"
    lo, hi = ci_of(agg)
    note = None if agg.get("median") is not None else (agg.get("median_note") or "null")
    return agg.get("median"), lo, hi, agg.get("n"), note


def caption(own_usd: float | None, n_align: int, n_seeds: int, u) -> str:
    """The caption draft of §8.1 with the numbers of the summaries (plan §5: at most 3 lines of about 140
    characters): own capacity in whole USD with a thousands separator (417 characters with a six-digit value at 4
    alignments x 3 seeds, §8.1); the grey line named as the bound on siloed OPT, the stars (the copy bound); the
    claims report drafts it with this function."""
    own = "–" if own_usd is None else f"{own_usd:,.0f}"                # whole USD with a thousands separator
    al = f"{n_align} alignment{'s' if n_align != 1 else ''}"
    se = f"{n_seeds} seed{'s' if n_seeds != 1 else ''}"
    return (f"Fig. 4. (a) Week cost over all-fallback by component, overflow accounting (not drawn: the borrowers' own "
            f"capacity, {own} USD per week, the same for every policy); medians with 95% intervals over {al} × {se}. "
            f"(b) Saving over all-fallback against cross-region links. (c) Cost over shared OPT against b "
            f"(u = {u:g}); dashed, open markers: siloed. Grey: b, the bound on siloed OPT (stars; tight by C3-P7, "
            f"PROVEN).")


def build(inp: Inputs) -> dict:
    e7 = inp.json(E7)
    e3 = inp.json(E3)
    meta7 = need(e7, "meta", what=E7)
    meta3 = need(e3, "meta", what=E3)

    # (a)
    tags7 = tag_map(e7, E7)
    _need_tags(tags7, BARS + B_KEYS, E7)
    a: dict = {"order": list(BARS), "accounting": "overflow"}
    for key in BARS:
        a[key] = {**bar_entry(e7, tags7[key]), "label": style.POLICIES[key].label}
    present = {c for k in BARS for c in a[k]["components_mean_over_bl0a"]}
    drawn = [c for c in COMPONENT_ORDER if any((a[k]["components_mean_over_bl0a"].get(c) or 0.0) > 0 for k in BARS)]
    drawn += sorted(c for c in present if c not in COMPONENT_ORDER and
                    any((a[k]["components_mean_over_bl0a"].get(c) or 0.0) > 0 for k in BARS))
    a["zero_components"] = sorted(c for c in present if c not in drawn)
    a["components"] = {"order": drawn, "labels": {c: COMPONENT_LABEL.get(c, c) for c in drawn},
                       "note": "lease is rent and billed term (lease_rent + lease_prepaid; sf_e6b.component_groups); "
                               "each bar's median split in proportion to the components' mean ratios to BL0a"}
    for key in BARS:
        e = a[key]
        comps = e["components_mean_over_bl0a"]
        csum = sum(comps.get(c) or 0.0 for c in drawn)
        e["segments"] = ({c: e["median"] * (comps.get(c) or 0.0) / csum for c in drawn}
                         if e["median"] is not None and csum > 0 else {})
    bl0a = by_alignment(meta7, "bl0a_usd", E7)
    own = by_alignment(meta7, "own_capacity_usd", E7)
    b_ovf = by_alignment(meta7, "bl0b_overflow_usd", E7)
    b_tot = by_alignment(meta7, "bl0b_total_usd", E7)
    try:
        a_tot = by_alignment(meta7, "bl0a_total_usd", E7)
    except MissingKey:                                   # total accounting = overflow + own capacity (§2.6)
        a_tot = {c: bl0a[c] + own[c] for c in bl0a if c in own}
    r_ovf = {c: b_ovf[c] / bl0a[c] for c in sorted(b_ovf) if bl0a.get(c)}
    r_tot = {c: b_tot[c] / a_tot[c] for c in sorted(b_tot) if a_tot.get(c)}
    a["bl0a"] = {"x": 1.0, "usd_by_alignment": bl0a}
    a["bl0b"] = {"overflow_over_bl0a": statistics.median(r_ovf.values()) if r_ovf else None,
                 "total_over_bl0a": statistics.median(r_tot.values()) if r_tot else None,
                 "overflow_over_bl0a_by_alignment": r_ovf, "total_over_bl0a_by_alignment": r_tot,
                 "off_scale": True, "label": style.POLICIES["bl0b"].label,
                 "rule": "median over the alignments of meta.bl0b_overflow_usd / meta.bl0a_usd (and the total "
                         "accounting's bl0b_total_usd / bl0a_total_usd)"}
    a["own_capacity_usd"] = {"by_alignment": own, "median": statistics.median(own.values()) if own else None}

    # (b)
    links_meta = need(meta7, "links", what=f"{E7} meta")
    ns = [x for x, _, _ in num_items(links_meta)]
    blinks = e7.get("links") if isinstance(e7.get("links"), Mapping) else {}
    b: dict = {}
    for key in B_KEYS:
        tag = tags7[key]
        s = {"tag": tag, "links": [], "median": [], "ci_lo": [], "ci_hi": [], "n": [], "note": [], "source": []}
        for n in ns:
            nk = format(float(n), "g")
            if nk in blinks:
                block, src = maybe(blinks, nk, tag)[0], f"links.{nk}.{tag}"
            else:                                        # S7, all five links: the main grid (§3.10)
                block, src = maybe(e7, "runs", MU, tag)[0], f"runs.{format(float(MU), 'g')}.{tag}"
            med, lo, hi, cnt, note = series_entry(block, "saving_pct")
            for f, v in zip(("links", "median", "ci_lo", "ci_hi", "n", "note", "source"),
                            (n, med, lo, hi, cnt, note, src)):
                s[f].append(v)
        b[key] = s
    b["agree"] = agree_entry("sublet", "bl5", b["sublet"]["median"], b["bl5"]["median"], AGREE_MAX_PCT)
    b["cross_region_links"] = {format(float(n), "g"): links_meta.get(format(float(n), "g")) for n in ns}

    # (c)
    grid = need(meta3, "grid", what=f"{E3} meta")
    bs = [float(v) for v in need(grid, "b", what=f"{E3} meta.grid")]
    dp = grid.get("default_point") or []
    u = float(dp[1]) if len(dp) > 1 else float(need(grid, "u", what=f"{E3} meta.grid")[0])
    mu3 = float(grid.get("mu_main", MU))
    tags3 = tag_map(e3, E3)
    _need_tags(tags3, C_KEYS, E3)
    c: dict = {"u": u, "mu": mu3}
    for key in C_KEYS:
        tag = tags3[key]
        s = {"tag": tag, "b": [], "median": [], "ci_lo": [], "ci_hi": [], "n": [], "open": [], "note": [], "u": u}
        for bv in bs:
            ent, note = maybe(e3, "ratios", bv, u, mu3, tag)
            ent = ent if isinstance(ent, Mapping) else {}
            lo, hi = ci_of(ent)
            if note is None and ent.get("median") is None:
                note = ent.get("median_note") or ent.get("open_note") or "null"
            for f, v in zip(("b", "median", "ci_lo", "ci_hi", "n", "open", "note"),
                            (bv, ent.get("median"), lo, hi, ent.get("n"), bool(ent.get("open", False)), note)):
                s[f].append(v)
        c[key] = s
    o = {"b": [], "point": [], "lo": [], "hi": [], "exact": [], "open": [], "note": []}
    for bv in bs:
        ent, note = maybe(e3, "opt", bv, u, mu3)
        ent = ent if isinstance(ent, Mapping) else {}
        if note is None and ent.get("point_median") is None:
            note = ent.get("point_median_note") or ent.get("open_note") or "null"
        for f, v in zip(o, (bv, ent.get("point_median"), ent.get("lo_min"), ent.get("hi_max"),
                            bool(ent.get("exact", False)), bool(ent.get("open", True)), note)):
            o[f].append(v)
    c["opt"] = o
    c["theory"] = {"b": bs, "upper_b": bs, "u": u, "kind": "upper"}

    grids7 = need(meta7, "grids", what=f"{E7} meta")
    n_al = len(grids7.get("alignments") or [])
    n_se = len(grids7.get("policy_seeds") or [])
    cap = caption(a["own_capacity_usd"]["median"], n_al, n_se, u)
    labels = {**LABELS,
              "bars": {k: style.POLICIES[k].label for k in BARS}, "bl0a": style.POLICIES["bl0a"].label,
              "bl0b": style.POLICIES["bl0b"].label,
              "bl0b_ratio": None if a["bl0b"]["overflow_over_bl0a"] is None else
              f"{a['bl0b']['overflow_over_bl0a']:.1f}",
              "components": a["components"]["labels"],
              "agree": b["agree"]["key"] if b["agree"] else None,
              "accounting": "overflow accounting: cost / BL0a without the borrowers' own capacity (M2)",
              "own_capacity": "–" if a["own_capacity_usd"]["median"] is None else
              f"{a['own_capacity_usd']['median']:,.0f} USD per week",
              "caption": cap, "caption_chars": len(cap),
              "c_open": "open star: siloed/shared OPT bracket open (a shared MILP without a result: LB from the LP "
                        "alone, sim_spec_ms4 §4.6)",
              "status": STATUS}
    meta = {"e7_main": {"git_revision": meta7.get("git_revision"), "B0_rule": meta7.get("B0_rule"),
                        "reduced": bool(meta7.get("reduced", False)),
                        "alignments": grids7.get("alignments"), "policy_seeds": grids7.get("policy_seeds")},
            "e3": {"git_revision": meta3.get("git_revision"), "B0_rule": meta3.get("B0_rule"),
                   "reduced": bool(meta3.get("reduced", False)), "normalize": meta3.get("normalize")}}
    return {"a": a, "b": b, "c": c, "labels": labels, "meta": meta, "sources": list(inp.sources)}


# ---------------------------------------------------------------------------------------------------------------
# (a)
def x_max(a: Mapping) -> float:
    """The right end of (a)'s x axis: X_PAD beyond the largest bar or whisker, at least that beyond 1 (BL0a)."""
    vals = [1.0] + [v for k in a["order"] for v in (a[k]["median"], a[k]["ci_hi"]) if v is not None]
    return max(vals) * (1.0 + X_PAD)


def _key(ax, comps: Sequence[str], shades: Mapping, labels: Mapping, ncol: int):
    """The key of the components at the top of (a), from KEY_LEFT_IN right of the panel's slot (the left edge of the
    longest policy name), KEY_TOP_PT below the axes top."""
    x0, _, w, _ = style.axes_rect_in(ax)
    slot = getattr(ax, "_sublet_slot_left_in", x0 - style.LEFT_LABEL)
    pad = KEY_TOP_PT / style.TICK_PT                          # borderaxespad is in font sizes
    leg = ax.legend([Patch(facecolor=shades[c], edgecolor="none") for c in comps],
                    [labels.get(c, c) for c in comps], loc="upper left",
                    bbox_to_anchor=((slot + KEY_LEFT_IN - x0) / w, 1.0), ncol=ncol, frameon=False,
                    handlelength=KEY_HANDLE, handleheight=0.8, columnspacing=KEY_COLUMNS, borderaxespad=pad,
                    borderpad=0.0)
    leg._sublet_role = "key"
    return leg


def draw_a(ax, a: Mapping, lab: Mapping, next_slot_in: float | None = None) -> None:
    """(a); next_slot_in: the left edge (in) of the next panel's slot, where its letter starts (the axes' right edge
    if None)."""
    order = list(a["order"])
    comps = list(a["components"]["order"])
    shades = dict(zip(comps, style.ramp(len(comps), "greys")[::-1])) if comps else {}
    n_rows = len(order) + 1                              # the bars and BL0b's row
    X = x_max(a)
    for i, key in enumerate(order):
        e, pol = a[key], style.policy(key)
        total = e["median"]
        if total is None:                                # no runs: an empty row, its note in the extract
            ax.text(0.01, i, lab.get("no_data", "no runs"), transform=ax.get_yaxis_transform(), ha="left",
                    va="center", fontsize=style.TICK_PT, color=style.THEORY_LABEL_GREY)
            continue
        x0 = 0.0
        for comp in comps:
            wd = e["segments"].get(comp, 0.0)
            if wd > 0:
                ax.barh(i, wd, left=x0, height=BAR_H, color=shades[comp], linewidth=0, zorder=1.5)
            x0 += wd
        if not e["segments"]:                            # components null: unstacked, in the darkest grey
            ax.barh(i, total, height=BAR_H, color=style.ramp(1, "greys")[0], linewidth=0, zorder=1.5)
        ax.barh(i, total, height=BAR_H, fill=False, edgecolor=pol.text_color, linewidth=BAR_EDGE_PT, zorder=1.6)
        if e["ci_lo"] is not None and e["ci_hi"] is not None:
            style.errorbars(ax, key, [total], [i], [e["ci_lo"]], [e["ci_hi"]], orientation="x", zorder=1.7)
    ax.set_xlim(0.0, X)
    ax.xaxis.set_major_formatter(style.PLAIN)
    ax.set_xlabel(lab["a_x"])
    ax.set_yticks(range(n_rows), [lab["bars"][k] for k in order] + [lab["bl0b"]])
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)

    # the key in a band above the bars, on one row where the "All-fallback" label then fits beside it over its line
    # (the label spans x = 1) and LETTER_GAP_PT left of the next panel's slot (its letter "(b)" sits there, just above
    # the label's row), else on two rows with the label beside the second
    fig = ax.figure
    r = fig.canvas.get_renderer()
    to_pt = 72.0 / fig.dpi
    ax_x0, _, ax_w, _ = style.axes_rect_in(ax)
    w_pt = ax_w * 72.0
    right_pt = w_pt if next_slot_in is None else min(w_pt, (next_slot_in - ax_x0) * 72.0)
    text_w = text_width_in(fig, lab["bl0a"]) * 72.0
    p_pt = w_pt / X                                      # x = 1 from the axes' left edge (the x axis starts at 0)
    leg, left, nrow = None, None, 1
    for ncol in ([len(comps), max(1, math.ceil(len(comps) / 2))] if comps else [1]):
        leg = _key(ax, comps, shades, a["components"]["labels"], ncol) if comps else None
        key_right = (leg.get_window_extent(r).x1 - ax.get_window_extent(r).x0) * to_pt if leg else 0.0
        lo, hi = key_right + LABEL_GAP_PT, right_pt - LETTER_GAP_PT - text_w
        left = min(max(p_pt - 0.5 * text_w, lo), hi)
        nrow = math.ceil(len(comps) / ncol) if comps else 1
        if lo <= hi and left <= p_pt <= left + text_w:
            break
        if leg is not None:
            leg.remove()
    else:
        raise style.StyleError(f"{NAME} (a): the label {lab['bl0a']!r} does not fit over its line beside the "
                               "components' key")
    h_key = (leg.get_window_extent(r).height / fig.dpi if leg else 0.12) + KEY_TOP_PT / 72.0 + 0.03
    rows_below([ax], n_rows, h_key)
    ax.set_xlim(0.0, X)                                  # rows_below sets the y range only

    # BL0b: its own row, a short arrow at the right end of the x axis and its ratio left of it
    bl0b = a["bl0b"]
    row = len(order)
    ratio = None
    if bl0b.get("overflow_over_bl0a") is None:
        ax.text(0.01, row, lab.get("no_data", "no runs"), transform=ax.get_yaxis_transform(), ha="left",
                va="center", fontsize=style.TICK_PT, color=style.THEORY_LABEL_GREY)
    else:
        tail = X * (1.0 - ARROW_IN * 72.0 / w_pt)
        pol = style.policy("bl0b")
        arr = style.arrow(ax, (tail, row), (X, row), color=pol.color, linewidth=style.REFERENCE_POLICY_PT,
                          shrinkA=0.0, shrinkB=0.0)
        arr._sublet_role = "off_scale_arrow"
        ratio = style.direct_label(ax, "bl0b", tail, row, lab["bl0b_ratio"], dx=-ARROW_TEXT_PT, ha="right",
                                   va="center_baseline")         # C62: on "Provision for peak"'s baseline (the y
        ratio._sublet_role = "direct_label"                       # tick labels' alignment; 0.7 pt above it as built)

    # BL0a: a line at 1 across the bars, above them in a white casing (behind them, or in #4D4D4D on the darker grey
    # segments, it would not read where a bar crosses 1), labeled in the band above its top, level with the key's last
    # row; it ends half a row below the last bar, or BL0A_CLEAR_PT above BL0b's ratio where the ratio lies under it
    # (else the line points into the number)
    y_end = len(order) - 0.5
    if ratio is not None:
        bb = ratio.get_window_extent(r)
        x1_px = ax.transData.transform((1.0, row))[0]
        if bb.x0 - BL0A_CLEAR_PT / to_pt < x1_px < bb.x1 + BL0A_CLEAR_PT / to_pt:
            y_clear = ax.transData.inverted().transform((x1_px, bb.y1 + BL0A_CLEAR_PT / to_pt))[1]
            if y_clear < len(order) - 1 + 0.5 * BAR_H:
                raise style.StyleError(f"{NAME} (a): BL0b's ratio {lab['bl0b_ratio']!r} leaves no room under the "
                                       "last bar for BL0a's line")
            y_end = min(y_end, float(y_clear))
    kw = style.policy_kwargs("bl0a", markers=False)
    kw["zorder"] = Z_BL0A
    (line,) = ax.plot([1.0, 1.0], [y_end, -0.5], **kw)
    line.set_path_effects([patheffects.Stroke(linewidth=kw["linewidth"] + BL0A_CASING_PT, foreground="white"),
                           patheffects.Normal()])
    line._sublet_policy = "bl0a"
    if leg is not None:
        bb = leg.get_window_extent(r)
        y_c = bb.y0 + 0.5 * bb.height / nrow
    else:
        y_c = ax.get_window_extent(r).y1 - (KEY_TOP_PT + 0.5 * style.TICK_PT) / to_pt
    xy = ax.transAxes.inverted().transform((ax.get_window_extent(r).x0 + left / to_pt, y_c))
    t = ax.text(xy[0], xy[1], lab["bl0a"], transform=ax.transAxes, ha="left", va="center", fontsize=style.TICK_PT,
                color=style.policy("bl0a").label_color, zorder=style.Z_THEORY_LABEL)
    t._sublet_role = "direct_label"
    if leg is not None:
        # C62: moved onto the printed baseline of the key's last row (as built, centered on the row, it printed 0.3 pt
        # above it), measured in a PDF draw (common.printed_baselines_pt)
        from matplotlib.transforms import ScaledTranslation
        base = printed_baselines_pt(fig, [*leg.get_texts(), t])
        shift = min(base[:-1]) - base[-1]
        t.set_transform(t.get_transform() + ScaledTranslation(0.0, shift / style.BP_PER_IN, fig.dpi_scale_trans))
        t._sublet_baseline_shift_pt = round(shift, 4)


# ---------------------------------------------------------------------------------------------------------------
# (b)
def draw_b(ax, b: Mapping, lab: Mapping) -> None:
    vals = [0.0]
    n = len(B_KEYS)
    links = finite(b[B_KEYS[0]]["links"])
    for i, key in enumerate(B_KEYS):
        s = b[key]
        x = finite(s["links"]) + DODGE_LINKS * (i - (n - 1) / 2)
        y, lo, hi = finite(s["median"]), finite(s["ci_lo"]), finite(s["ci_hi"])
        style.plot_policy(ax, key, x, y)
        ok = np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi)
        if ok.any():
            style.errorbars(ax, key, x[ok], y[ok], lo[ok], hi[ok])
        vals += [v for v in np.concatenate([y, lo, hi]) if np.isfinite(v)]
    style.reference_line(ax, y=0.0)
    ax.set_xticks(list(links))
    ax.xaxis.set_major_formatter(style.PLAIN)
    ax.set_xlim(float(np.nanmin(links)) - 0.5, float(np.nanmax(links)) + 0.5)
    lo, hi = min(vals), max(vals)
    pad = 0.08 * (hi - lo) if hi > lo else 1.0
    ax.set_ylim(lo - pad, hi + pad)
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.set_xlabel(lab["b_x"])
    ax.set_ylabel(lab["b_y"])
    agree_key_clear(ax, b.get("agree"), {k: b[k] for k in B_KEYS}, x="links", y="median")


def _tick_label_blockers(ax, clear_pt: float) -> LineCollection:
    """Invisible segments (display coordinates, no width) that free_spot reads as drawn: one at clear_pt less
    KEY_PAD_PT right of the y spine across the height of each y tick label, so that a key or label level with a tick
    label starts at least clear_pt right of the spine (a key line there reads as continuing the tick label, as in
    "10 = RetroRenting-style"). The caller removes them."""
    r = ax.figure.canvas.get_renderer()
    px = ax.figure.dpi / 72.0
    x = ax.get_window_extent(r).x0 + (clear_pt - KEY_PAD_PT) * px
    segs = []
    for t in ax.get_yticklabels():
        if t.get_visible() and t.get_text().strip():
            bb = t.get_window_extent(r)
            segs.append([(x, bb.y0), (x, bb.y1)])
    lc = LineCollection(segs, colors="none", linewidths=0.0, transform=IdentityTransform())
    ax.add_collection(lc, autolim=False)
    return lc


def agree_key_clear(ax, entry: Mapping | None, series: Mapping, *, x: str, y: str):
    """common.agree_key with its key kept off the levels of the y tick labels near the spine (_tick_label_blockers,
    TICK_CLEAR_PT); where none of agree_key's forms then fits, its text broken after the "=" or "≈" (the second line
    one policy name, the narrowest form of the key's widest line), as a label without the markers (it names both
    policies) on the free space next to the two series (common.place_label). Nothing where entry is None; StyleError
    where it fits nowhere."""
    if not entry:
        return None
    blockers = _tick_label_blockers(ax, TICK_CLEAR_PT)
    try:
        try:
            return agree_key(ax, entry, series, x=x, y=y)
        except style.StyleError:
            pass
        near = np.concatenate([points_pt(ax, series[k][x], series[k][y]) for k in entry["pair"]])
        text = entry["key"].replace(" = ", " =\n").replace(" ≈ ", " ≈\n").replace(" (within", "\n(within")
        t = place_label(ax, text, near)
        if t is None:
            raise style.StyleError(f"{NAME} (b): the key {entry['key']!r} fits nowhere on the free space clear of "
                                   "the y tick labels")
        t._sublet_role = "key"
        return t
    finally:
        blockers.remove()


# ---------------------------------------------------------------------------------------------------------------
# (c)
def _dodge(i: int, n: int) -> float:
    return 2.0 ** (DODGE_OCT_C * (i - (n - 1) / 2))


def place_theory_label(ax, txt, x, y, forms: Sequence[str]) -> None:
    """Move the theory line's label (an annotation from theory_line) to the free space nearest to the line and
    nearer to it than to any data point (common.free_spot), trying the text forms in order; StyleError where none
    fits."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    to_pt = 72.0 / fig.dpi
    xs = np.geomspace(min(x), max(x), 200)
    xs = xs[xs <= ax.get_ylim()[1]]                      # the drawn part: y = b leaves through the axis top
    near = points_pt(ax, xs, xs)
    txt.set_annotation_clip(False)                       # measured while its anchor (b = 32) lies above the axis top
    others = [points_pt(ax, ln.get_xdata(), ln.get_ydata()) for ln in ax.lines if hasattr(ln, "_sublet_policy")]
    others = np.concatenate(others) if others else None
    for text in forms:
        txt.set_text(text)
        bb = txt.get_window_extent(r)
        spot = free_spot(ax, bb.width * to_pt, bb.height * to_pt, near, others=others, skip=(txt,))
        if spot is None:
            continue
        right_bottom = ax.transData.inverted().transform(((spot[0] + bb.width * to_pt) / to_pt, spot[1] / to_pt))
        txt.xy = tuple(float(v) for v in right_bottom)
        txt.xyann = (0.0, 0.0)
        txt.set_horizontalalignment("right")
        txt.set_verticalalignment("bottom")
        txt.set_multialignment("left")                   # "b," at the box's left, next to the line
        # a label set apart from its line (where the free space next to it is taken) is joined to the line's nearest
        # point by a thin grey leader, as common.right_theory_lines joins a moved label (IEEE: connect the label)
        x0, y0 = spot
        x1, y1 = x0 + bb.width * to_pt, y0 + bb.height * to_pt
        q = np.column_stack([np.clip(near[:, 0], x0, x1), np.clip(near[:, 1], y0, y1)])
        d = np.hypot(*(near - q).T)
        k = int(np.argmin(d))
        if d[k] > LEADER_MIN_PT:
            end = ax.transData.inverted().transform(near[k] / to_pt)
            start = ax.transData.inverted().transform(q[k] / to_pt)
            ld = ax.annotate("", xy=tuple(end), xytext=tuple(start), arrowprops=dict(
                arrowstyle="-", color=style.THEORY_GREY, linewidth=LEADER_PT, shrinkA=1.0, shrinkB=1.5),
                zorder=style.Z_THEORY)
            ld._sublet_role = "theory_leader"
        return
    raise style.StyleError(f"{NAME} (c): the label of the line b fits nowhere on the free space ({list(forms)})")


def draw_c(ax, c: Mapping, lab: Mapping) -> None:
    n = len(C_KEYS) + 1                                  # the policies and the OPT brackets
    bs = finite(c["theory"]["b"])
    vals = [1.0]                                         # the data and the level 1, not the bound (it leaves the top)
    pts = {}
    for key in C_KEYS:                                   # pass 1, the lines in C_KEYS's order, dodged into C_SLOTS
        s = c[key]
        x = finite(s["b"]) * _dodge(C_SLOTS.index(key), n)
        y, lo, hi = finite(s["median"]), finite(s["ci_lo"]), finite(s["ci_hi"])
        env = ("sharing", C_ENV[key]) if key in C_ENV else None
        style.plot_policy(ax, key, x, y, env=env, markers=False)
        pts[key] = (x, y, lo, hi)
        vals += [v for v in np.concatenate([y, lo, hi]) if np.isfinite(v)]
    o = c["opt"]
    x = finite(o["b"]) * _dodge(n - 1, n)
    y, lo, hi = finite(o["point"]), finite(o["lo"]), finite(o["hi"])
    ok = np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi)
    if ok.any():
        style.errorbars(ax, "opt", x[ok], y[ok], lo[ok], hi[ok], zorder=Z_C_BARS)
    shut = np.isfinite(y) & ~np.asarray(o["open"], dtype=bool)
    if shut.any():
        style.scatter_policy(ax, "opt", x[shut], y[shut], zorder=Z_C_MARKS)
    opened = np.isfinite(y) & np.asarray(o["open"], dtype=bool)
    if opened.any():                                     # LB from the LP alone (§4.6): an open star
        style.scatter_policy(ax, "opt", x[opened], y[opened], markerfacecolor="white", label="_nolegend_",
                             zorder=Z_C_MARKS)
    vals += [v for v in np.concatenate([y, lo, hi]) if np.isfinite(v)]
    for i, key in enumerate(C_KEYS, start=1):            # pass 2, above every line: the bars, then the markers
        x, y, lo, hi = pts[key]
        ok = np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi)
        if ok.any():
            style.errorbars(ax, key, x[ok], y[ok], lo[ok], hi[ok], zorder=Z_C_BARS)
        style.scatter_policy(ax, key, x, y, zorder=Z_C_MARKS + Z_C_STEP * i)   # Sublet's last (C_KEYS)
    _, txt = style.theory_line(ax, bs, bs, "upper", lab["theory"])
    style.log2_axis(ax, "x", ticks=list(bs))
    reach = DODGE_OCT_C * (n - 1) / 2 + C_MARGIN_OCT    # the outermost dodged markers and a margin
    ax.set_xlim(float(np.nanmin(bs)) / 2 ** reach, float(np.nanmax(bs)) * 2 ** reach)
    thin_tick_labels(ax)
    lo_v, hi_v = data_range(vals)
    # the y range from the data and the brackets, at least up to C_TOP_MIN: the line y = b, drawn to b = 32, leaves
    # through the top (§4.2: at b = 8 the runs cost about twice shared OPT, and siloed OPT about shared OPT)
    ratio_log2_axis(ax, min(lo_v, 1.0), max(hi_v, C_TOP_MIN))
    style.ygrid(ax)
    ax.set_xlabel(lab["c_x"])
    ax.set_ylabel(lab["c_y"])
    place_theory_label(ax, txt, bs, bs, lab.get("theory_forms") or [lab["theory"]])


# ---------------------------------------------------------------------------------------------------------------
def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    names = [lab["bars"][k] for k in data["a"]["order"]] + [lab["bl0b"]]
    res_a = style.ytick_reserve(fig, names)
    ax_a, ax_b, ax_c = style.panel_row(fig, (2, 1, 1), legend=True, left=(res_a, None, None))
    # OPT's entry as drawn in (c): the star alone (the brackets are unjoined); the caption names it siloed OPT
    opt_kw = style.policy_kwargs("opt", lines=False)
    style.legend_row(fig, list(LEGEND), extra=[(Line2D([], [], **opt_kw), opt_kw["label"])])
    draw_a(ax_a, data["a"], lab, next_slot_in=getattr(ax_b, "_sublet_slot_left_in", None))
    draw_b(ax_b, data["b"], lab)
    draw_c(ax_c, data["c"], lab)
    style.panel_letters([ax_a, ax_b, ax_c])
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
