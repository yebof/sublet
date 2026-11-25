"""sf_e3_util: E3's replicas shared or siloed, by the number of borrowers b (design/sim_spec_ms4.md §8.2, §4.8;
plan §4, part S-F).

At u = 8 (E3's only u, M41) and mu / beta~ = 1, against b in {1, 2, 4, 8, 16, 32} (log2), for the one-way guard
around the lagged BL5 at MS4's allowance B0 = 0.1 BL0a (the summary's tag Sublet; MS6 C47, design/ms6_spec.md M2, M4:
drawn as the registry key sublet_ms4, "Lagged RetroRenting + one-way guard ($B_0=10\\%$ BL0a)") and A6, shared (solid)
and siloed (dashed: env=("sharing", "siloed"); A6's siloed form in its registry triple a6_siloed, open hexagons, and
sublet_ms4's in the key's own filled markers, the series id "sublet_ms4:siloed", as sf_e3_v2 draws a siloed form
without a key), BL2 (per-borrower by construction) and the lagged BL5 (bl5_lag; the supplement's BL5, design §5.5 E3),
each the median over the alignments x policy seeds of meta.grid with its 95% bootstrap interval. The summary records
the style keys of its build (sublet, sublet_siloed, bl5), which ms4_lib.tag_of maps to the drawn series (RECORDED):
(a) replica utilization (served over capacity load-minutes; a siloed run's summed over its sub-runs),
    e3/summary.json util.<b>.8.1.<tag>.replica_utilization, on a linear axis from 0 to 1;
(b) replica loads per day, util.<b>.8.1.<tag>.loads_per_day, log;
(c) cost over the shared OPT's lower bound, ratios.<b>.8.1.<tag> (ratio_LB: Q39's LB, so an upper bound on the
    ratio to shared OPT; siloed runs take the shared denominator), log2 (common.ratio_log2_axis's range), labeled at
    the coarsest ladder of mantissas per octave of RATIO_LADDERS (1; 1, 1.5; 1, 1.25, 1.5) that puts at least
    RATIO_MIN_TICKS ticks on the axis (ratio_axis: 1, 1.5, 2, 3 on E3; the powers of two alone labeled only 1 and 2
    over data from 1.37 to 2.91), with the level 1 as a reference line.
The series are dodged in x by DODGE_OCT_E3 (0.12 octave between neighbors, as Fig. 4(c): common.DODGE_OCT's 0.055 octave
moved six series by about a third of a marker, so that near-equal series hid each other), in the slot order DRAW_ORDER,
BL5, A6, Sublet, A6 siloed, Sublet siloed, BL2: none of the pairs that run close (Sublet and BL5 at every b, Sublet and
its siloed form at b <= 4, A6 and its siloed form at b <= 4, A6 siloed and BL2 at b >= 8, BL2 and Sublet at b = 2 in
(c)) take neighboring slots. The x axis reaches X_MARGIN_OCT beyond the outermost dodged markers at b = 1 and b = 32.
Each panel is drawn in two passes (draw_panel): first every series' line, then every interval bar (Z_BARS) and every
series' markers (Z_MARKS, in the registry's z-order, Sublet's last) above all lines, so that no line runs over another
series' marker (as built, in one pass, BL2's triangle at b = 2 in (c) and b = 1 in (b) lay under Sublet's thicker line,
and at b = 1 in (c) under the siloed Sublet's dashed line). The series' Line2D (`_sublet_policy`) keeps its full
registry style, its markers suppressed (markevery=[]); the markers are a markers-only Line2D of their own
(`_sublet_role` "markers").
The note's encoding clause names the series it covers, from the drivers' modes in e3/summary.json meta.tags
(sharing_modes): the siloed forms of shared policies (policy_id SILOED, their shared form the tag whose policy_id is
params.inner), drawn dashed (env=("sharing", "siloed"); as built "dashed lines with open circles and hexagons: the
siloed forms of Sublet and Two-timescale PD"; C47: on E3 "dashed lines: the siloed forms of Lagged RetroRenting +
one-way guard ($B_0=10\\%$ BL0a) (its own markers) and Two-timescale PD (open hexagons)"), and the policies run per
borrower by construction (mode siloed, not a SILOED wrapper; on E3 Per-borrower ski rental, drawn solid in its registry
style),
since RetroRenting-style's registry marker is an open square and Per-borrower ski rental's line is solid, so that
"dashed, open markers: siloed" (as built) misnamed both. A StyleError where the modes disagree with the drawn
encoding (SILOED).
Coincidences, computed from the data: where Sublet and BL5 agree within common.AGREE_MAX_PCT in every median and
interval end of the three panels (common.agree_entry; on E3 they are equal), a key ("Sublet = RetroRenting-style",
common.agree_key) on the free space of the first panel of (a), (b), (c) where it fits, and labels.note says so; where
A6 siloed and BL2 agree within AGREE_MAX_PCT in (c) over a tail of b, grown from the largest b down while they do and
holding at least TAIL_MIN b (near_tail), labels.note states it with the percent (on E3: within 4% for b >= 8); where
each siloed form equals its shared form at b = 1 in every median and interval end of the three panels (one borrower;
single_borrower), labels.note says so (on E3 they are equal, and the six series at b = 1 lie within 3% in (c), so
their markers overlap there).
The legend names the four policies (Fig. 4's form, §8.1), not the six series; the line-style samples of
env_handles("sharing") name the siloed form, and labels.note's encoding clause the series drawn dashed. C47: with
sublet_ms4's label the four policies and the two line styles do not fit one row, so the legend has two rows; the
agreement key of sublet_ms4 and the lagged BL5, whose full text no panel holds, is then their two markers with "equal
at every b" (AGREE_SHORT; identity_key), and labels.note names both. C62 (7-pt text): the two rows of LEGEND_LAYOUT,
each its entries side by side and centered over the panels (ms4_lib.legend_rows_above; as built two column-aligned rows
of three, whose first column, as wide as the guard's label, left a wide gap in the second row): the guard beside the
lagged rule it equals, then Two-timescale PD, Per-borrower ski rental and the two line styles, with the dashes of the
siloed sample centered on it (ms4_lib.centered_dash_pairs) and the guard's mathtext label on its neighbor's baseline
(common.align_baselines); (b)'s y label in one line; b italic in the x labels ("Borrowers per LLM, $b$", the
design's name of b, as sf_e3_v2; fix round) and the key, as in the caption; (a)
with the y grid of (b) and (c). Elsewhere in this docstring "Sublet" and "BL5" are the summary's tags of sublet_ms4 and
bl5_lag (MS4's names), never the paper's Sublet.
Print check of the gate (U46): the short key's two markers sit on one solid line (AGREE_HANDLE, no gap between the
samples), since the filled marker alone is also the siloed guard's, on a dashed line; at b = 1, where single_borrower
finds each siloed form equal to its shared form, only the shared forms have markers and bars, the siloed lines start
at their shared forms' markers, and the four markers left take evenly spread places over the six slots' span
(draw_panel, b1_offsets; as relabeled, six markers within 3% in (c), 2.7 pt apart, covered a third of each other),
which labels.note states; and labels.note names (c)'s denominator in words (as relabeled "ratio_LB", "Q39's").
A point without runs (the reduced grid's b in {2, 4, 16, 32}) is null with its note (a gap in the line); a ratio point
whose shared MILP has no result is against the LP alone (`open`, listed in the extract).

Run from code/sim: python -m figs.supp.sf_e3_util [--from-extract [JSON]].
"""
from __future__ import annotations

import math
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator

from figs import style
from figs.common import (AGREE_MAX_PCT, _top_tick_room, agree_entry, agree_key, agreement, align_baselines, cli, finite,
                         need, LINE_STEP_PT, place_key, points_pt, ratio_log2_axis)
from figs.inputs import Inputs
from figs.supp.ms4_lib import (DRAWN_KEY, LOG_PAD, SILOED_FORM, agg_point, centered_dash_pairs, dodge, finite_values,
                               grid_counts, legend_reserve_top, legend_rows_above, levels_of, line_casing,
                               log_axis_over, log_ticks, runs_text, series_key, series_over, tag_of)

NAME = "sf_e3_util"
E3 = "code/sim/out/e3/summary.json"
KEYS = style.SUPP_POLICIES_MS4[NAME]          # sublet_ms4, a6, a6_siloed, bl2, bl5_lag
# C47 (design/ms6_spec.md M2, M4): the drawn series, registry keys and the siloed form of sublet_ms4 (no registry key
# of its own, C46: the key in the sharing line style, as sf_e3_v2 draws it), by the summary's recorded style keys
SUBLET_SILOED = "sublet_ms4" + SILOED_FORM
SERIES = ("sublet_ms4", SUBLET_SILOED, "a6", "a6_siloed", "bl2", "bl5_lag")
RECORDED = {**DRAWN_KEY, "sublet_siloed": SUBLET_SILOED}   # recorded style key -> drawn series
SILOED = (SUBLET_SILOED, "a6_siloed")          # drawn with env=("sharing", "siloed")
SHARED = ("sublet_ms4", "a6")                  # drawn with env=("sharing", "shared")
LEGEND_KEYS = ("sublet_ms4", "a6", "bl5_lag", "bl2")   # + env_handles("sharing")
# C62: the legend's two rows, each its entries side by side and centered over the panels (ms4_lib.legend_rows_above):
# the guard beside the lagged rule it equals at every b (4.8 in), then Two-timescale PD, Per-borrower ski rental and
# the two line styles (3.4 in); as built at 9 pt, two column-aligned rows of three (legend_row(..., rows=2, ncol=3)),
# whose first column, as wide as the guard's label, left a 2.3-in gap after "Two-timescale PD"
LEGEND_LAYOUT = (("sublet_ms4", "bl5_lag"), ("a6", "bl2", "shared", "siloed"))
LEGEND_HANDLE = 2.0                            # C62: the samples' length (em), three whole dashes when centered
#                                                (ms4_lib.centered_dash_pairs), the markers on their lines' middles
# dodge order, left to right: no two of the pairs that run close (module docstring) in neighboring slots
DRAW_ORDER = ("bl5_lag", "a6", "sublet_ms4", "a6_siloed", SUBLET_SILOED, "bl2")
style.register_supplementary(NAME, "W2", 2.2)
UTIL_PAD = 0.05                                # (a): axis margin beyond [0, 1] (not in §8.2)
DODGE_OCT_E3 = 0.12                            # x dodge between neighboring series, in octaves (Fig. 4(c)'s
#                                                DODGE_OCT_C; common.DODGE_OCT, 0.055, is a third of a marker; not in
#                                                §8.2)
X_MARGIN_OCT = 0.15                            # x margin beyond the outermost dodged markers, in octaves (Fig. 4(c))
RATIO_LADDERS = ((1.0,), (1.0, 1.5), (1.0, 1.25, 1.5))   # labeled mantissas per octave of a log2 ratio axis
RATIO_MIN_TICKS = 3                            # ... the coarsest ladder with at least this many ticks on the axis
IDENTITY = ("sublet_ms4", "bl5_lag")           # the pair of the key (agree_entry over all three panels)
AGREE_SHORT = {"same": "equal at every $b$", "near": "within {pct}% at every $b$"}   # identity_key's short form,
#                                                beside the pair's markers, where no form of the full key fits a panel
#                                                (C47; C62: b italic, as in the x labels)
AGREE_HANDLE = 2.8                             # C47: the short key's handle (em), the pair's two samples with their
#                                                lines side by side (1.3 as relabeled, bare markers)
AGREE_PAD_PT = 4.0                             # C47 (U46 re-review): the short key's padding (pt), so that its line,
#                                                which starts at the key's left edge, stays clear of the y spine
NEAR_C = ("a6_siloed", "bl2")                  # the pair of the note on (c) (near_tail)
TAIL_MIN = 2                                   # near_tail: at least this many b with points of both
Z_BARS = style.Z_SUBLET + 0.05                 # draw_panel's second pass: interval bars above every line
Z_MARKS = style.Z_SUBLET + 0.1                 # ... and markers above the bars, Z_MARK_STEP per unit of registry
Z_MARK_STEP = 0.1                              #     z-order above Z_DATA (Sublet's last; all below the key and labels)
B1 = 1.0                                       # C47: the b of one borrower, where single_borrower's pairs are equal
WRAPPER_ID = "SILOED"                          # meta.tags.<tag>.policy_id of a siloed form (params.inner: the shared)
MARKER_NAMES = {"o": "circles", "h": "hexagons", "s": "squares", "^": "triangles", "v": "triangles",
                "D": "diamonds", "p": "pentagons", "*": "stars", "P": "pluses", "<": "triangles"}
# C62: (b)'s y label in one line (1.08 in at 7.97 pt, inside the 1.28-in axes; C47 put it on two lines, since at 9 pt
# it was 1.37 in long against 1.17-in axes and reached the panel letter); b italic, as in the caption (the three x
# labels are one mathtext string, so they share one baseline). C62 fix round: "Borrowers per LLM, $b$", the design's
# name of b (Sublet_design.md's notation table: "$b$ borrowers per LLM (C3-P7)"; E3's b borrowers of one LLM in one
# region), as its MS5b sister sf_e3_v2 labels it (as first restyled "Borrowers $b$")
LABELS = {"x": "Borrowers per LLM, $b$", "a_y": "Replica utilization", "b_y": "Replica loads per day",
          "c_y": "Cost / shared OPT",
          # C47 (print check of the gate): (c) without the build's names (ratio_LB, Q39)
          "note": "u = {u:g}, mu/beta~ = {mu:g}; medians over {runs} with 95% bootstrap intervals; (c) cost over a "
                  "lower bound on the shared OPT, so an upper bound on cost / shared OPT, siloed runs over the "
                  "shared denominator"}


def e3_point(e3: Mapping, what: str = E3) -> tuple[float, float, list[tuple[float, str]]]:
    """(u, mu_main, b levels) of E3's grid: meta.grid.u (one value since M41), mu_main and the b keys of `ratios`."""
    us = need(e3, "meta", "grid", "u", what=what)
    if len(us) != 1:
        raise style.StyleError(f"{what}: meta.grid.u is {us}; E3 runs at one u (M41)")
    mu = float(need(e3, "meta", "grid", "mu_main", what=what))
    return float(us[0]), mu, levels_of(need(e3, "ratios", what=what), f"{what} ratios")


def at_u_mu(block: Mapping, levels, u: float, mu: float) -> dict:
    """{b key: block[b][u][mu]} (a level without the (u, mu) entry is left out, so its points are null)."""
    uk, mk = format(u, "g"), format(mu, "g")
    return {bk: block[bk][uk][mk] for _, bk in levels
            if isinstance(block.get(bk), Mapping) and isinstance(block[bk].get(uk), Mapping)
            and mk in block[bk][uk]}


def identity_entry(panels: Mapping, a: str = IDENTITY[0], b: str = IDENTITY[1]) -> dict | None:
    """common.agree_entry of `a` and `b` over every median and interval end of the panels (a), (b) and (c): "A = B"
    where they are equal at every point, "A ≈ B (within p%)" within AGREE_MAX_PCT, else None."""
    vals = {k: [v for p in ("a", "b", "c") for f in ("median", "ci_lo", "ci_hi") for v in panels[p][k][f]]
            for k in (a, b)}
    return agree_entry(a, b, vals[a], vals[b], AGREE_MAX_PCT)


def near_tail(block: Mapping, a: str, b: str, max_pct: int = AGREE_MAX_PCT) -> dict | None:
    """How far down from the largest b the medians of `a` and `b` in `block` agree within max_pct percent at every b
    (common.agreement), grown one b at a time while they do: {pair, b_min, b_count, every_b, max_rel_diff,
    within_pct} where the tail holds at least TAIL_MIN b with points of both, else None. A b where only one of the
    two has a point ends the tail; a b where neither has one is skipped (a gap of the reduced grid)."""
    bs, ya, yb = finite(block[a]["b"]), finite(block[a]["median"]), finite(block[b]["median"])
    both = [i for i in range(len(bs)) if np.isfinite(ya[i]) and np.isfinite(yb[i])]
    idx: list[int] = []
    best = None
    for i in sorted(range(len(bs)), key=lambda j: -bs[j]):
        fa, fb = bool(np.isfinite(ya[i])), bool(np.isfinite(yb[i]))
        if not (fa or fb):
            continue
        if fa != fb:
            break
        ag = agreement(ya[idx + [i]], yb[idx + [i]])
        if ag is None or ag["within_pct"] > max_pct:
            break
        idx.append(i)
        best = ag
    if len(idx) < TAIL_MIN or best is None:
        return None
    return {"pair": [a, b], "b_min": float(min(bs[idx])), "b_count": len(idx), "every_b": len(idx) == len(both),
            **best}


def identity_text(entry: Mapping | None) -> str | None:
    """The note's sentence on the key's pair (None without a key)."""
    if not entry:
        return None
    la, lb = (style.POLICIES[k].label for k in entry["pair"])
    if entry["within_pct"] == 0:
        return f"{la} and {lb} have equal medians and intervals at every b in (a)-(c)"
    return f"{la} and {lb} agree within {entry['within_pct']}% in every median and interval at every b in (a)-(c)"


def near_text(entry: Mapping | None) -> str | None:
    """The note's sentence on the near-equal pair of (c) (None where near_tail found no tail)."""
    if not entry:
        return None
    a, b = entry["pair"]
    la, lb = series_text(a), series_text(b)
    where = "at every b" if entry["every_b"] else f"for b >= {entry['b_min']:g}"
    how = "are equal" if entry["within_pct"] == 0 else f"agree within {entry['within_pct']}%"
    return f"in (c), {la} and {lb} {how} {where}"


def series_text(series: str) -> str:
    """A drawn series by its legend name for the note: a siloed form (SILOED) as "the siloed <its shared form's
    label>" (C47: the siloed form of sublet_ms4 has no registry key; a6_siloed's registry label reads the same), else
    the registry label."""
    if series in SILOED:
        return f"the siloed {style.POLICIES[series_key(series) if series != 'a6_siloed' else 'a6'].label}"
    return style.POLICIES[series].label


def and_join(words: Sequence[str]) -> str:
    """'A', 'A and B', 'A, B and C'."""
    words = list(words)
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def sharing_modes(meta_tags: Mapping, tags: Mapping[str, str], keys: Sequence[str], what: str = E3) -> dict:
    """The sharing of the figure's keys from the drivers' meta.tags (mode, policy_id, params.inner): {siloed:
    [[siloed key, shared key]], per_borrower: [keys]}, in the order of `keys`. A siloed form is a tag with mode
    "siloed" and policy_id WRAPPER_ID; its shared form is the one tag among `keys` with mode "shared" whose policy_id
    is its params.inner. A key with mode "siloed" and another policy_id is per borrower by construction. StyleError
    where these disagree with the drawn encoding: the siloed forms are exactly SILOED among `keys` (drawn dashed with
    their registry markers), each of the registry family of its shared form. `keys` are drawn series ids (C47: a key, or
    SUBLET_SILOED)."""
    ent = {k: meta_tags[tags[k]] for k in keys}
    siloed, per = [], []
    for k in keys:
        e = ent[k]
        if e.get("mode") != "siloed":
            continue
        if e.get("policy_id") != WRAPPER_ID:
            per.append(k)
            continue
        inner = (e.get("params") or {}).get("inner")
        cand = [j for j in keys if ent[j].get("mode") == "shared" and ent[j].get("policy_id") == inner]
        if len(cand) != 1:
            raise style.StyleError(f"{what}: meta.tags.{tags[k]} (inner {inner!r}) has {len(cand)} shared forms "
                                   f"among {list(keys)}, not one")
        if style.POLICIES[series_key(k)].family != style.POLICIES[series_key(cand[0])].family:
            raise style.StyleError(f"{what}: the siloed form {k!r} and its shared form {cand[0]!r} are of different "
                                   "registry families")
        siloed.append([k, cand[0]])
    drawn = [k for k in keys if k in SILOED]
    if [s for s, _ in siloed] != drawn:
        raise style.StyleError(f"{what}: meta.tags give the siloed forms {[s for s, _ in siloed]}, the figure draws "
                               f"{drawn} dashed (SILOED)")
    return {"siloed": siloed, "per_borrower": per}


def encoding_text(modes: Mapping) -> str:
    """The note's clause on the line styles, naming the series it covers (sharing_modes): on E3 "dashed lines: the
    siloed forms of Lagged RetroRenting + one-way guard ($B_0=10\\%$ BL0a) (its own markers) and Two-timescale PD
    (open hexagons); Per-borrower ski rental is per-borrower by construction" (the markers' names and fills from the
    registry; C47: the siloed form of sublet_ms4 keeps the key's filled markers, so "dashed lines with open circles
    and hexagons", as built, would misname it)."""
    parts = []
    if modes["siloed"]:
        forms = []
        for s, h in modes["siloed"]:
            p, shared = style.POLICIES[series_key(s)], style.POLICIES[series_key(h)]
            if p.key == shared.key:
                forms.append(f"{shared.label} (its own markers)")
            else:
                forms.append(f"{shared.label} ({p.fill} {MARKER_NAMES.get(p.marker or '', 'markers')})")
        n = len(forms)
        parts.append(f"dashed lines: the siloed form{'s' if n > 1 else ''} of {and_join(forms)}")
    if modes["per_borrower"]:
        per = modes["per_borrower"]
        parts.append(f"{and_join([style.POLICIES[k].label for k in per])} {'is' if len(per) == 1 else 'are'} "
                     "per-borrower by construction")
    return "; ".join(parts)


def single_borrower(panels: Mapping, modes: Mapping) -> dict | None:
    """Where b = 1 is a level: the pairs of modes['siloed'] (siloed form, shared form) whose medians and interval ends
    at b = 1 are equal in all three panels (common.agreement, within_pct 0; a value one of the two lacks is not
    equality), as {b: 1, pairs, every_pair}; None where no pair is."""
    same = []
    for s, h in modes["siloed"]:
        vals = {}
        for k in (s, h):
            v = []
            for p in ("a", "b", "c"):
                bs = [float(b) for b in panels[p][k]["b"]]
                if 1.0 not in bs:
                    return None
                i = bs.index(1.0)
                v += [panels[p][k][f][i] for f in ("median", "ci_lo", "ci_hi")]
            vals[k] = v
        ag = agreement(vals[s], vals[h])
        if ag is not None and ag["within_pct"] == 0:
            same.append([s, h])
    if not same:
        return None
    return {"b": 1.0, "pairs": same, "every_pair": len(same) == len(modes["siloed"])}


def single_text(entry: Mapping | None) -> str | None:
    """The note's sentence on single_borrower (None without an entry)."""
    if not entry:
        return None
    if entry["every_pair"] and len(entry["pairs"]) > 1:
        return "at b = 1 each siloed form equals its shared form (one borrower), so only the shared forms are drawn there"
    names = and_join([style.POLICIES[series_key(h)].label for _, h in entry["pairs"]])
    if len(entry["pairs"]) == 1:
        return (f"at b = 1 the siloed form of {names} equals its shared form (one borrower), so only the shared form "
                "is drawn there")
    return (f"at b = 1 the siloed forms of {names} equal their shared forms (one borrower), so only the shared forms "
            "are drawn there")


def build(inp: Inputs) -> dict:
    e3 = inp.json(E3)
    u, mu, levels = e3_point(e3)
    meta_tags = need(e3, "meta", "tags", what=E3)
    tags = tag_of(meta_tags, SERIES, E3, drawn=RECORDED)            # C47: the recorded keys to the drawn series
    modes = sharing_modes(meta_tags, tags, SERIES)
    util = at_u_mu(need(e3, "util", what=E3), levels, u, mu)
    ratios = at_u_mu(need(e3, "ratios", what=E3), levels, u, mu)
    out = {"a": {}, "b": {}, "c": {}}
    for key in SERIES:
        out["a"][key] = series_over(util, levels, tags[key], lambda e: agg_point(e, "replica_utilization"), "b")
        out["b"][key] = series_over(util, levels, tags[key], lambda e: agg_point(e, "loads_per_day"), "b")
        c = series_over(ratios, levels, tags[key], agg_point, "b")
        c["open"] = [bool((ratios.get(bk, {}).get(tags[key]) or {}).get("open")) for _, bk in levels]
        out["c"][key] = c
    agree = identity_entry(out)
    near = near_tail(out["c"], *NEAR_C)
    single = single_borrower(out, modes)
    note = LABELS["note"].format(u=u, mu=mu, runs=runs_text(*grid_counts(need(e3, "meta", "grid", what=E3),
                                                                         f"{E3} meta.grid")))
    note = "; ".join([note] + [s for s in (encoding_text(modes), single_text(single), identity_text(agree),
                                           near_text(near)) if s])
    out.update({"u": u, "mu": mu, "b_levels": [x for x, _ in levels], "tags": tags, "sharing": modes,
                "single_b1": single, "agree": agree, "near_c": near,
                "labels": {**LABELS, "legend": [style.POLICIES[k].label for k in LEGEND_KEYS],
                           "agree": agree["key"] if agree else None, "note": note},
                "meta": {"git_revision": need(e3, "meta", "git_revision", what=E3),
                         "reduced": bool(e3["meta"].get("reduced")), "B0_rule": e3["meta"].get("B0_rule")},
                "sources": list(inp.sources)})
    return out


def env_of(series: str):
    """The sharing line style of a drawn series (SILOED dashed, SHARED solid; None for the others)."""
    return ("sharing", "siloed") if series in SILOED else (("sharing", "shared") if series in SHARED else None)


def draw_panel(ax, block: Mapping, keys: Sequence[str], merged_b1: Sequence[Sequence[str]] = ()) -> int:
    """The series of `keys` in DRAW_ORDER's slots, DODGE_OCT_E3 apart, in two passes: first every series' line (its
    Line2D in the full registry style, env_of's line style, its markers suppressed with markevery=[]; Sublet's line
    above the others by its registry z-order), then every 95% interval bar (Z_BARS) and every series' markers
    (a markers-only Line2D, `_sublet_role` "markers", at Z_MARKS plus Z_MARK_STEP per unit of registry z-order above
    Z_DATA, so Sublet's last), above all lines: no line runs over another series' marker, and a marker's face covers
    a bar that passes under it. Returns the number of slots.
    C47 (print check of the gate): at b = B1 each siloed form of `merged_b1` ([siloed, shared] pairs: single_borrower's,
    equal there in every median and interval end) has no marker and no bar; its line starts at its shared form's
    marker, and the series still drawn at b = B1 take evenly spread places over the span of all n slots (b1_offsets).
    As relabeled, the six series at b = 1 lay within 3% in (c), 0.12 octave (2.7 pt) apart, and a marker covered a
    third of its neighbour's."""
    order = [k for k in DRAW_ORDER if k in keys]
    n = len(order)
    merged = {a: b for a, b in merged_b1 if a in order and b in order}
    off = b1_offsets(order, merged)
    pts = []
    for i, ser in enumerate(order):
        s, key = block[ser], series_key(ser)
        x, y = dodge(s["b"], i, n, DODGE_OCT_E3), finite(s["median"])
        lo, hi, my = finite(s["ci_lo"]), finite(s["ci_hi"]), y.copy()
        for j, b in enumerate(s["b"]):
            if b is not None and float(b) == B1 and (ser in off or ser in merged):
                x[j] = float(b) * 2.0 ** off[merged.get(ser, ser)]
                if ser in merged:                    # drawn by its shared form's marker and bar
                    my[j] = lo[j] = hi[j] = np.nan
        line_casing(ax, key, x, y)
        ln = style.plot_policy(ax, key, x, y, env=env_of(ser), markevery=[])
        ln._sublet_series = ser
        pts.append((ser, x, my, lo, hi))
    for ser, x, y, lo, hi in pts:
        ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi) & (hi > lo)
        if ok.any():
            style.errorbars(ax, series_key(ser), x[ok], y[ok], lo[ok], hi[ok], zorder=Z_BARS)
    for ser, x, y, _, _ in pts:
        kw = style.policy_kwargs(series_key(ser), lines=False, label=False)
        kw["zorder"] = Z_MARKS + Z_MARK_STEP * (kw["zorder"] - style.Z_DATA)
        (mk,) = ax.plot(x, y, **kw)
        mk._sublet_role = "markers"
        mk._sublet_markers_of = series_key(ser)
        mk._sublet_series = ser
    return n


def b1_offsets(order: Sequence[str], merged: Mapping[str, str]) -> dict:
    """C47: {series: dodge offset at b = B1 in octaves} for the series of `order` (DRAW_ORDER's slots) that keep their
    marker there (not a key of `merged`, {siloed form: shared form}), spread evenly, in slot order, over the span
    of all len(order) slots; {} where nothing is merged (every series keeps its slot)."""
    shown = [k for k in order if k not in merged]
    n = len(order)
    if not merged or len(shown) < 1:
        return {}
    if len(shown) == 1:
        return {shown[0]: 0.0}
    step = (n - 1) / (len(shown) - 1)
    return {k: DODGE_OCT_E3 * (j * step - (n - 1) / 2.0) for j, k in enumerate(shown)}


def b_axis(ax, bs: Sequence[float], n: int) -> None:
    """log2 x axis at the b levels, reaching X_MARGIN_OCT beyond the outermost of n dodged slots."""
    style.log2_axis(ax, "x", ticks=bs)
    reach = DODGE_OCT_E3 * (n - 1) / 2.0 + X_MARGIN_OCT
    ax.set_xlim(min(bs) / 2 ** reach, max(bs) * 2 ** reach)
    style.end_label_inside(ax)


def ratio_axis(ax, lo: float, hi: float, *, min_ticks: int = RATIO_MIN_TICKS) -> list[float]:
    """common.ratio_log2_axis over [lo, hi] (its log2 scale and limits), its labeled ticks the coarsest ladder of
    RATIO_LADDERS (mantissas per octave) that puts at least `min_ticks` ticks inside the limits (the finest where
    none does); the top then clears the highest tick label (common._top_tick_room). Returns the ticks."""
    ratio_log2_axis(ax, lo, hi)
    y0, y1 = ax.get_ylim()
    e0, e1 = math.floor(math.log2(y0)) - 1, math.ceil(math.log2(y1)) + 1
    ticks: list[float] = []
    for lad in RATIO_LADDERS:
        ticks = sorted({m * 2.0 ** e for e in range(e0, e1 + 1) for m in lad if y0 <= m * 2.0 ** e <= y1})
        if len(ticks) >= min_ticks:
            break
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    _top_tick_room(ax)
    return ticks


def positive_range(block: Mapping, keys: Sequence[str], default: tuple[float, float]) -> tuple[float, float]:
    v = finite_values(*(block[k][f] for k in keys for f in ("median", "ci_lo", "ci_hi")))
    v = v[v > 0]
    return (float(v.min()), float(v.max())) if v.size else default


def identity_key(axes: Sequence, data: Mapping) -> str | None:
    """The key of data['agree'] (common.agree_key) on the free space of the first of the panels (a), (b), (c) where
    it fits, next to the pair's points; where no form of it fits any panel (C47: sublet_ms4's label alone is wider
    than a panel), the pair's markers side by side with the short text AGREE_SHORT ("equal at every b"; the note
    names both policies) on the free space of the first panel where that fits (common.place_key); the panel's
    letter, or None (no key, or no free space in any panel: the note still states the identity)."""
    entry = data.get("agree")
    if not entry:
        return None
    for ax, p in zip(axes, ("a", "b", "c")):
        try:
            if agree_key(ax, entry, {k: data[p][k] for k in entry["pair"]}, x="b", y="median") is not None:
                return p
        except style.StyleError:
            continue
    text = (AGREE_SHORT["same"] if entry["within_pct"] == 0 else
            AGREE_SHORT["near"].format(pct=entry["within_pct"]))
    # C47 (print check of the gate): the samples on one solid line, each with its line in the series' style (env_of:
    # the shared form solid) and no gap between them (pad 0), since the filled marker alone also fits the siloed
    # form's dashed line (as relabeled, bare markers), and two solid samples with a gap read as one dashed line
    hs = tuple(Line2D([], [], **style.policy_kwargs(series_key(k), env=env_of(k), lines=True)) for k in entry["pair"])
    for ax, p in zip(axes, ("a", "b", "c")):
        near = np.concatenate([points_pt(ax, data[p][k]["b"], data[p][k]["median"]) for k in entry["pair"]])
        leg = place_key(ax, [(hs, text)], near, handlelength=AGREE_HANDLE, borderpad=AGREE_PAD_PT / style.TICK_PT,
                        handler_map={tuple: HandlerTuple(ndivide=None, pad=0.0)})
        if leg is not None:
            leg._sublet_agree = "short"
            return p
    return None


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    keys = [k for k in SERIES if k in data["a"]]
    # (b)'s left reserve fits its tick labels (loads per day reach five digits at b = 32 when siloed)
    lo_b, hi_b = positive_range(data["b"], keys, (1.0, 10.0))
    ticks_b = log_ticks(lo_b / LOG_PAD, hi_b * LOG_PAD)
    res_b = max(style.LEFT_LABEL, style.ytick_reserve(fig, [style.PLAIN(t) for t in ticks_b], ylabel=True)
                + lab["b_y"].count("\n") * LINE_STEP_PT / style.BP_PER_IN)        # C47: a y label of n lines
    axes = style.panel_row(fig, (1, 1, 1), top=legend_reserve_top(2), left=(None, res_b, None))   # two legend rows
    bs = data["b_levels"]
    merged_b1 = [tuple(pr) for pr in (data.get("single_b1") or {}).get("pairs", [])]    # C47: drawn once at b = 1
    for ax, p in zip(axes, ("a", "b", "c")):
        n = draw_panel(ax, data[p], keys, merged_b1)
        b_axis(ax, bs, n)
        ax.set_xlabel(lab["x"])
        ax.set_ylabel(lab[f"{p}_y"])
    ax_a, ax_b, ax_c = axes
    # a share from 0 to 1: the y spine spans [0, 1], the axis a little more, so that markers at 0 or 1 clear the
    # x spine and the panel letter
    ax_a.set_ylim(-UTIL_PAD, 1.0 + UTIL_PAD)
    ax_a.spines["left"].set_bounds(0.0, 1.0)
    ax_a.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax_a.yaxis.set_major_formatter(style.PLAIN)
    style.ygrid(ax_a)                              # C62: the y grid of (b) and (c) in (a) too
    log_axis_over(ax_b, "y", lo_b, hi_b, ticks=ticks_b)
    style.ygrid(ax_b)
    lo, hi = positive_range(data["c"], keys, (1.0, 2.0))
    ratio_axis(ax_c, min(lo, 1.0), max(hi, 1.0))
    style.reference_line(ax_c, y=1.0)
    style.ygrid(ax_c)
    style.panel_letters(axes)
    legend(fig)
    identity_key(axes, data)
    return fig


def legend(fig) -> list:
    """C62: the legend's rows of LEGEND_LAYOUT (registry keys, then the sharing line styles of env_handles), each its
    entries side by side, centered over the panels in the top reserve of two legend rows (ms4_lib.legend_rows_above),
    the samples LEGEND_HANDLE em long with the siloed form's dashes centered (centered_dash_pairs) and the guard's
    mathtext label on its plain neighbor's baseline as printed (common.align_baselines). Returns the legends."""
    env = dict(zip(("shared", "siloed"), style.env_handles("sharing")))
    rows = [centered_dash_pairs([env[k] if k in env else style.policy_handles([k])[0] for k in row], LEGEND_HANDLE)
            for row in LEGEND_LAYOUT]
    legs = legend_rows_above(fig, rows, n_rows=2, handlelength=LEGEND_HANDLE)
    for leg in legs:
        align_baselines(leg.get_texts())
    return legs


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
