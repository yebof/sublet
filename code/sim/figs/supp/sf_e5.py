"""sf_e5: E5, redundancy under correlated reclaims (design/sim_spec_ms4.md §8.2, §5; M18, M19; plan §4, part S-F).

Small multiples, one panel per correlation level (§5.3): (a) the trace lender, (b)-(d) the correlated lender with
p_sh = 0.25, 0.5, 1 over the lenders' own groups, (e) one group for all lenders (p_sh = 1, Q44's L-co). In each,
per policy (A6 with redundancy 'off', 'rule' (its default) and 'always2'; BL3 with N_Extra = 0, 1, 2 (its default);
Sublet), at mu / beta~ = 1: x = week cost over BL0a in overflow accounting (M2), y = the fallback share of an LLM's
demand within 60 min after a reclaim-caused capacity drop, both the median over 4 alignments x 3 policy seeds
(e5/summary.json cells.<level>.<menu>.1.<tag>: cost_over_bl0a, fallback_share_after_reclaims), with their 95%
bootstrap intervals as thin bars; one registry triple per policy (M18, C18), the filled marker for the short-notice
menu and the open one (white face) for the long-notice menu (the caption names this encoding: with the two menu
entries the two legend rows did not fit, test C18; C47 below). Both axes are log (cost over BL0a reaches 10-21 for BL3 under
one group); each panel has its own x range (the levels differ by an order of magnitude in BL3's cost), the panels
share y. A share of 0 or null (no run with a reclaim-caused drop) cannot be drawn on the log axis: it is drawn on the
x spine and counted in the extract (`zero_or_null`, M19). The level 1 of cost (all-fallback) is a reference line.
Where the three A6 modes give the same point (within COINCIDE_REL), A6's default ('rule') alone is drawn there: three
markers on one point would show a mix of their outlines, and a key beside it read as data (both as built); the
extract's `a6_coincide` lists these cells, with pareto.<level>.<menu>.a6_modes_identical (whether their runs were
identical), for the caption. The legend lists the keys drawn in some panel only; where A6's other two modes are drawn
nowhere since they coincide with the default in every cell, A6's entry reads "Two-timescale PD, all modes". The y label
is "Fallback share" ("after reclaims" goes to the caption: the full label is longer than the axes).

Every interval bar lies below every marker of its panel (BAR_Z), so that a marker's face covers any other policy's bar
that runs under it (print check: in (e) BL3's bars crossed each other's markers). Markers stack as drawn: the long menu
below the short, Sublet on top (DRAW_ORDER, LONG_DZ). A point within UNDER_REL of a point drawn over it in both
coordinates lies under it (hidden_points; a share of 0 or null on the spine is not checked); the extract lists these
(`under`), labels.note states each with both points' values, and the figure names it with a 7-pt label in the hidden
policy's label color, "<name> (hidden by <name of the point over it>)" (as first built "(under ...)", which read as
"below"; print check), joined by a thin grey leader (hidden_labels: a straight leader 15-75 degrees from the
horizontal, else an arc, clear of every other mark; the label LABEL_CLEAR_PT from the other markers and not level with
one), where such a spot exists. On the real data this is A6's short-menu point under Sublet's in (e) (print check:
Sublet's circle hid it). The label keeps a white halo only where its box overlaps a line, grid, bar, arrow or marker
(ms4_lib.drop_idle_halos): a haloed label is written to the PDF as outlines, not text.

Two overlaps show only in the drawn geometry; build() draws the figure once from its data to find them (overlaps):
a marker with at least PARTLY_SHARE of its disk under a marker drawn over it (`partly_under`; on the real data A6's
long-menu point under Sublet's short-menu disk in (e)), and two parallel interval bars whose ranges overlap and whose
gap is below BAR_GAP_PT, which print as one line (`bars_merged`, with the overlap of the two intervals; on the real
data BL3's short-menu cost bars at N_Extra = 1 and 2 in (e)); a hidden point's own bars are left out. labels.note
states each, and that 'SpotHedge-style' without N_Extra is BL3 at its default N_Extra, read from its tag's params,
else from the number its tag (BL3-2) ends in; where the three A6 modes give one point in every cell, it says so and
names A6's legend entry (else labels.coincide, the rule, with the cells). The note names every policy by its legend
name (style.POLICIES label as plain text, note_name), never by its tag.

MS6 C47 (design/ms6_spec.md M2, M4): "Sublet" above is the summary's tag of the one-way guard around the lagged BL5
at MS4's allowance, drawn as the registry key sublet_ms4 ("Lagged RetroRenting + one-way guard ($B_0=10\\%$ BL0a)",
a filled sky-blue left triangle at 3.5 pt and the common z-order, no longer Sublet's 4-pt circle on top; it is still
drawn last). With its label the two legend rows hold at most five entries in style.legend_row's aligned columns (on
E5 the drawn ones: A6's modes merged); where more are drawn, the entries in order stand side by side in two rows of
their own (ms4_lib.split_rows, legend_rows_above). The label of a hidden point names the point over it where that
fits, else reads "(hidden)" (LABELS["hidden_short"]; the leader ends at the stack, labels.note names both points), and
the leader is drawn below the marker over the hidden point (leader_z). In greyscale sublet_ms4's and BL3's filled
left triangles differ by BL3's black edge and lighter fill (both keys' triples are fixed:
tests/test_ms6_additions_figs.py GREY_SHARED); sublet_ms4 is not labeled directly (a direct label of 3.1 in fits no
panel). The menus' encoding (filled: short-notice menu, open: long-notice menu) stayed in the caption as relabeled:
the two column-aligned rows hold no entry for it, and a third legend row (at the registered 2.5 in, the largest
supplementary height) leaves (e) no room for the label of its hidden point. Print check of the gate (U46): the
policies now fill the two rows column by column as before, side by side and centered (ms4_lib.legend_rows_above), and
the second row ends with the menus' black samples, a filled and an open circle (menu_handles; on E5 the rows are
6.4 in and 6.3 in wide, against 7.08 in), so that the encoding is in the legend; labels.note names the menus in
words from meta.menus (menu_text) and no longer uses the build's names (M2, zero_or_null).

C62 (7-pt text): the legend's two rows hold one line each, the guard's label unwrapped beside Two-timescale PD, then
SpotHedge-style in N_Extra's order (BL3_KEYS) and the menus' samples, each row side by side and centered, the samples
LEGEND_HANDLE em long, every label on its row's baseline as printed (common.align_baselines); the C47 and C59 rows
remain the fallback where these do not fit (A6's modes apart). One x label centered under the five panels
(ms4_lib.center_xlabel; as built one per panel). The panel titles name each condition in words with its p_sh,
"Groups, p_sh = ..." for the lenders' own groups and "One group, p_sh = 1", so that (d) and (e) read apart (as built
"p_sh = 1" and "One group"), at the caption size (style.LABEL_PT, as C62 sets panel titles), the titles with p_sh on
the letters' baseline as printed.

Run from code/sim: python -m figs.supp.sf_e5 [--from-extract [JSON]].
"""
from __future__ import annotations

import json
import math
import re
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import NullLocator

from figs import style
from figs.common import (GRID_RES_PT, KEY_PAD_PT, LEADER_PT, _box_sum, _halo_texts, _occupancy, _top_tick_room,
                         align_baselines, cli, json_number, maybe, need, panel_title, points_pt, thin_tick_labels)
from figs.inputs import Inputs
from figs.supp.ms4_lib import (DRAWN_KEY, agg_point, center_xlabel, drop_idle_halos, finite_values, grid_counts,
                               legend_rows_above, log_axis_over, log_ticks, runs_text, split_rows, tag_of, wrap_wide)

NAME = "sf_e5"
E5 = "code/sim/out/e5/summary.json"
KEYS = style.SUPP_POLICIES_MS4[NAME]          # sublet_ms4, a6_red_off, a6, a6_always2, bl3_n0, bl3_n1, bl3
A6_KEYS = ("a6_red_off", "a6", "a6_always2")
LEVELS = ("trace", "sh0.25", "sh0.5", "sh1", "all1")      # §5.3, panels (a)-(e)
MENUS = ("short", "long")
MU = 1
COINCIDE_REL = 0.005          # A6 modes within 0.5% in both coordinates draw as one point (not in §8.2)
SPINE_FLOOR = 0.70            # the y axis starts this factor below the least positive share (room for the spine)
X_PAD = 1.18
OPEN_EDGE_PT = 0.9            # the long menu's open markers: a heavier edge than the 0.6-pt registry edge, so that in
#                               greyscale BL3's open markers (white) differ from its filled ones (yellow prints as
#                               light grey; not in §8.2)
DRAW_ORDER = ("bl3_n0", "bl3_n1", "bl3", "a6_always2", "a6_red_off", "a6", "sublet_ms4")   # the guard last
LONG_DZ = 0.2                 # the long menu's markers this far below the short menu's (z-order)
BAR_Z = style.Z_DATA - LONG_DZ - 0.1    # every interval bar below every marker of its panel, so that no bar crosses
#                               another policy's marker (as built, a bar was drawn just below its own marker only, and
#                               in (e) BL3's bars ran through each other's markers; print check)
UNDER_REL = 0.05              # a point within 5% in both coordinates of a point drawn over it lies under that point (on
#                               the real E5 panels, 58-105 pt per decade in x and 34.5 in y, 5% is at most 2.2 pt, less
#                               than a marker's radius with its edge; not in §8.2)
LEADER_Z = style.Z_DATA + 0.3   # a hidden point's leader: over the other markers, under Sublet's (Z_SUBLET); C47: and
#                               always under the marker drawn over the hidden point (leader_z)
LEADER_ANGLES = (15.0, 75.0)  # a straight leader runs within these degrees from the horizontal (not in §8.2)
LEADER_RADS = (0.0, 0.2, -0.2, 0.35, -0.35)    # leader shapes tried in turn: straight, then arcs (arc3 rad)
LEADER_MAX_PT = 40.0          # a leader spans at most this (not in §8.2)
LABEL_CLEAR_PT = 8.0          # the label stays this far from every other marker's center (not in §8.2; at 6 pt the
#                               label's corner came 4 pt from Sublet's long-menu circle in (e), and a reader could take
#                               the label for that circle's, print check) ...
LEVEL_CLEAR_PT = 12.0         # ... and this far from one level with it, beside a text line (as first built, a label
#                               6 pt from Sublet's long-menu circle in (e), level with it, read as its legend entry)
PARTLY_SHARE = 0.1            # a marker with at least this share of its disk (radius: half its size and edge) under a
#                               marker drawn over it lies partly under that marker (print check: in (e) Sublet's
#                               short-menu disk covered part of Two-timescale PD's long-menu hexagon; not in §8.2)
MENU_MARKER = "o"              # C47: the menus' legend samples (menu_handles), black circles: no E5 series is a circle
BAR_GAP_PT = 0.5              # two parallel interval bars of one panel whose ranges overlap and whose gap is below this
#                               (centers closer than UNCERTAINTY_PT + BAR_GAP_PT) print as one line (print check: in
#                               (e) two short-menu cost bars 0.63 pt apart; not in §8.2)
# C59 (RC19(3)): the guard's label in words takes two lines in the legend's first row (ms4_lib.wrap_wide); the two rows
# then fit the reserve of two rows (0.48 in) with LEGEND_GAP_EM between them (as built LEGEND_ROW_GAP_EM, 0.3 em), so
# that the panels keep their height and (e) the label of its hidden point (a reserve of three rows leaves no room)
LEGEND_RESERVE = 2
LEGEND_GAP_EM = 0.1
style.register_supplementary(NAME, "W2", 2.5)
BL3_KEYS = ("bl3_n0", "bl3_n1", "bl3")       # C62: the legend's second row, SpotHedge-style in N_Extra's order
LEGEND_HANDLE = 1.0                            # C62: marker samples one em long (ms4_lib's 1.4 em leaves a wide gap)
LEGEND_ROW_GAP_EM = 0.3                        # C62: the gap between the two one-line rows (C59's LEGEND_GAP_EM, 0.1 em,
#                                                is kept for the fallback rows, which hold the guard's label wrapped)
# C62: the panels' conditions in words, (b)-(d) the lenders' own groups and (e) one group of all lenders, each with its
# p_sh, so that (d) and (e), both at p_sh = 1, read apart without the caption (as built "$p_{sh}$ = 1" and "One group")
LABELS = {"x": "Cost / all-fallback", "y": "Fallback share",
          "a6_all_modes": "Two-timescale PD, all modes",
          "panel": {"trace": "Trace lender", "sh0.25": r"Groups, $p_{\mathrm{sh}}$ = 0.25",
                    "sh0.5": r"Groups, $p_{\mathrm{sh}}$ = 0.5", "sh1": r"Groups, $p_{\mathrm{sh}}$ = 1",
                    "all1": r"One group, $p_{\mathrm{sh}}$ = 1"},
          "coincide": "where {name}'s three modes ({modes}) give one point (within {pct:g}% in both coordinates), "
                      "only its default is drawn there (a6_coincide)",
          "coincide_all": "{name}'s three modes ({modes}) give one point in every cell (within {pct:g}% in both "
                          "coordinates), so only its default is drawn and its legend entry reads '{all_modes}'",
          "under": "in ({letter}), the {menu}-menu point of {name} ({x}, {y}) is hidden by the {over_menu}-menu point "
                   "of {over} ({ox}, {oy}) (cost, share)",
          "partly": "in ({letter}), the {menu}-menu point of {name} ({x}, {y}) lies partly under the {over_menu}-menu "
                    "point of {over} ({ox}, {oy}) (cost, share)",
          "bars": "in ({letter}), the 95% {what} intervals of {points} overlap between {lo} and {hi}, where their bars, "
                  "{d} pt apart, print as one line",
          "hidden": "(hidden by {over})",
          "hidden_short": "(hidden)",      # C47: where no form with the name of the point over it fits its panel
          "bl3_default": "'{name}' without N_Extra is its default, N_Extra = {n}",
          # C47 (print check of the gate): the menus' samples in the legend (menu_handles), and in labels.note the
          # menus in words from the summary's meta.menus (menu_text; as relabeled, their contract ids), without the
          # build's names (M2, zero_or_null, "key")
          "menu": {"short": "Short-notice menu", "long": "Long-notice menu"},
          "menu_contracts": " (leases with {tau} and {notice} min notice{protected})",
          "note": "mu/beta~ = 1; y: the fallback share within 60 min after a reclaim-caused capacity drop; medians "
                  "over {runs} with 95% bootstrap intervals; filled: short-notice menu{short}, open: long-notice "
                  "menu{long}; cost in overflow accounting; a share of 0, or without a value (no reclaim-caused "
                  "drop), on the x spine; a policy drawn in no panel is left out of the legend"}


def _or(items: Sequence[str]) -> str:
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " or " + items[-1]


def menu_text(menu: Any) -> str:
    """C47: labels.note's parenthesis on one menu, from e5/summary.json meta.menus.<menu>.contracts: its revocable
    contracts' guaranteed periods and notices in words ("leases with a 5-min guaranteed period and 0, 1 or 2 min
    notice, plus protected capacity"); '' where the summary does not list them."""
    con = menu.get("contracts") if isinstance(menu, Mapping) else None
    if not isinstance(con, list):
        return ""
    rev = [c for c in con if isinstance(c, Mapping) and c.get("tau_min") is not None and c.get("H_min") is not None]
    if not rev:
        return ""
    taus = sorted({float(c["tau_min"]) for c in rev})
    tau = (f"a {taus[0]:g}-min guaranteed period" if len(taus) == 1 else
           f"guaranteed periods of {_or([f'{t:g}' for t in taus])} min")
    prot = any(isinstance(c, Mapping) and c.get("tau_min") is None for c in con)
    return LABELS["menu_contracts"].format(tau=tau, notice=_or([f"{h:g}" for h in sorted({float(c["H_min"])
                                                                                           for c in rev})]),
                                           protected=", plus protected capacity" if prot else "")


def cell_point(cells: Mapping, level: str, menu: str, tag: str) -> dict:
    ent, note = maybe(cells, level, menu, MU, tag)
    if note is not None or not isinstance(ent, Mapping):
        empty = {"median": None, "ci_lo": None, "ci_hi": None, "n": 0, "note": note or "missing"}
        return {"cost": dict(empty), "fallback": dict(empty), "n_null": None}
    fb = ent.get("fallback_share_after_reclaims")
    return {"cost": agg_point(ent, "cost_over_bl0a"), "fallback": agg_point(ent, "fallback_share_after_reclaims"),
            "n_null": fb.get("n_null") if isinstance(fb, Mapping) else None}


def coincide(points: Sequence[Mapping]) -> bool:
    """Whether the A6 modes' points agree within COINCIDE_REL in cost and in fallback share (a null share counts as
    equal only to a null share)."""
    c = [p["cost"]["median"] for p in points]
    f = [p["fallback"]["median"] for p in points]
    if any(v is None for v in c):
        return False
    if any(v is None for v in f) and not all(v is None for v in f):
        return False

    def close(v):
        v = [x for x in v if x is not None]
        return not v or max(v) <= min(v) * (1.0 + COINCIDE_REL) and min(v) >= 0
    return close(c) and close(f)


def build(inp: Inputs) -> dict:
    e5 = inp.json(E5)
    tags = tag_of(need(e5, "meta", "tags", what=E5), KEYS, E5, drawn=DRAWN_KEY)      # C47: recorded sublet
    cells = need(e5, "cells", what=E5)
    out = {"levels": [lv for lv in LEVELS], "menus": list(MENUS), "tags": tags}
    zero_or_null = []
    a6_coincide = {}
    for lv in LEVELS:
        out[lv] = {}
        for menu in MENUS:
            block = {k: cell_point(cells, lv, menu, tags[k]) for k in KEYS}
            out[lv][menu] = block
            for k, p in block.items():
                m = p["fallback"]["median"]
                if p["cost"]["median"] is not None and (m is None or m <= 0):
                    zero_or_null.append({"level": lv, "menu": menu, "key": k, "share": m,
                                         "note": p["fallback"]["note"]})
            same, _ = maybe(e5, "pareto", lv, menu, "a6_modes_identical", "all_identical")
            a6_coincide.setdefault(lv, {})[menu] = {"drawn_as_one": coincide([block[k] for k in A6_KEYS]),
                                                    "runs_identical": same}
    out["zero_or_null"] = zero_or_null
    out["a6_coincide"] = a6_coincide
    out["under"] = under = [u for lv in LEVELS for u in hidden_points(out[lv], a6_coincide[lv], lv)]
    # the overlaps that only the drawn geometry shows: the figure drawn once from these data, as cli draws it
    out["partly_under"], out["bars_merged"] = overlaps(json.loads(json.dumps({**out, "labels": dict(LABELS)},
                                                                             default=json_number)))
    menus = {m: menu_text(maybe(e5, "meta", "menus", m)[0]) for m in MENUS}
    note = [LABELS["note"].format(runs=runs_text(*grid_counts(need(e5, "meta", "grid", what=E5), f"{E5} meta.grid")),
                                  **menus)]
    coinc, coinc_note = coincide_texts(out)
    note += [coinc_note] if coinc_note else []
    note += [under_text(u) for u in under]
    note += [under_text(u, "partly") for u in out["partly_under"]]
    note += [bars_text(b) for b in out["bars_merged"]]
    n_extra = default_n_extra(need(e5, "meta", "tags", what=E5), tags["bl3"])
    if n_extra is not None:
        note.append(LABELS["bl3_default"].format(name=note_name("bl3"), n=n_extra))
    out["labels"] = {**LABELS, "coincide": coinc, "note": "; ".join(note)}
    out["meta"] = {"git_revision": need(e5, "meta", "git_revision", what=E5), "reduced": bool(e5["meta"].get("reduced")),
                   "B0_rule": e5["meta"].get("B0_rule")}
    out["sources"] = list(inp.sources)
    return out


def drawn_points(block: Mapping, flags: Mapping) -> list[dict]:
    """The points of one panel as draw_panel draws them, bottom to top: (z-order, drawing order) of each marker (the
    long menu LONG_DZ below the short, Sublet last), a share of 0 or null (on the x spine) and A6's merged modes left
    out. Each {menu, key, x, y}."""
    pts = []
    for menu in MENUS:
        for key in DRAW_ORDER:
            if flags[menu]["drawn_as_one"] and key in A6_KEYS and key != "a6":
                continue
            p = block[menu][key]
            x, y = p["cost"]["median"], p["fallback"]["median"]
            if x is None or y is None or x <= 0 or y <= 0:
                continue
            z = style.policy(key).zorder - (LONG_DZ if menu == "long" else 0.0)
            pts.append({"menu": menu, "key": key, "x": x, "y": y, "_rank": (z, len(pts))})
    pts.sort(key=lambda q: q["_rank"])
    return [{k: v for k, v in q.items() if k != "_rank"} for q in pts]


def hidden_points(block: Mapping, flags: Mapping, level: str) -> list[dict]:
    """The points of a panel that lie under a point drawn over them: within UNDER_REL of it in both coordinates
    (the topmost such point is named). Each {level, menu, key, x, y, over: {menu, key, x, y}}."""
    pts = drawn_points(block, flags)
    tol = math.log1p(UNDER_REL)
    out = []
    for i, p in enumerate(pts):
        over = [q for q in pts[i + 1:]
                if abs(math.log(p["x"] / q["x"])) <= tol and abs(math.log(p["y"] / q["y"])) <= tol]
        if over:
            out.append({"level": level, **p, "over": over[-1]})
    return out


def _disk_share(p, r1: float, q, r2: float) -> float:
    """The share of the disk (p, r1) that the disk (q, r2) covers (pt)."""
    d = float(np.hypot(*(np.asarray(p, dtype=float) - np.asarray(q, dtype=float))))
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r1 - r2):
        return min(1.0, (r2 / r1) ** 2)
    a = r1 * r1 * math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1)) + \
        r2 * r2 * math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2)) - \
        0.5 * math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))
    return a / (math.pi * r1 * r1)


def _bar_drawn(iv: Mapping, orient: str) -> bool:
    """Whether draw_panel draws the interval bar of iv ({ci_lo, ci_hi}): both ends, hi > lo, lo > 0 on the y axis."""
    lo, hi = iv["ci_lo"], iv["ci_hi"]
    return lo is not None and hi is not None and hi > lo and (orient == "x" or lo > 0)


def overlaps(data: Mapping) -> tuple[list, list]:
    """(partly_under, bars_merged) of the figure drawn from `data`: per panel, (1) each marker (a share of 0 or null on
    the spine and a point that hidden_points lists left out) with at least PARTLY_SHARE of its disk under a marker
    drawn over it, {level, menu, key, x, y, share, over: {menu, key, x, y}}; (2) each pair of parallel interval bars
    (a hidden point's left out) whose ranges overlap and whose centers are closer than UNCERTAINTY_PT + BAR_GAP_PT,
    which print as one line, {level, orient ('x': cost, 'y': share), a: {menu, key}, b: {menu, key}, lo, hi, d_pt}
    (lo, hi: the overlap of their intervals). Positions from the drawn markers (draw_panel tags them)."""
    fig = draw(data)
    to_pt = style.BP_PER_IN / fig.dpi
    hidden = {(u["level"], u["menu"], u["key"]) for u in data.get("under", [])}
    partly, bars = [], []
    for ax in fig.axes:
        lv = getattr(ax, "_sublet_level", None)
        if lv is None:
            continue
        lines = sorted(((ln.get_zorder(), i, ln) for i, ln in enumerate(ax.lines) if hasattr(ln, "_sublet_menu")),
                       key=lambda q: q[:2])
        pts = []
        for _, _, ln in lines:
            xy = np.asarray(ln.get_xydata(), dtype=float)[0]
            pts.append({"menu": ln._sublet_menu, "key": ln._sublet_policy, "spine": ln._sublet_spine,
                        "P": ax.transData.transform(xy) * to_pt,
                        "r": 0.5 * (ln.get_markersize() + ln.get_markeredgewidth())})
        for i, a in enumerate(pts):
            if a["spine"] or (lv, a["menu"], a["key"]) in hidden:
                continue
            pa = data[lv][a["menu"]][a["key"]]
            for b in pts[i + 1:]:
                share = 0.0 if b["spine"] else _disk_share(a["P"], a["r"], b["P"], b["r"])
                if share >= PARTLY_SHARE:
                    pb = data[lv][b["menu"]][b["key"]]
                    partly.append({"level": lv, "menu": a["menu"], "key": a["key"], "x": pa["cost"]["median"],
                                   "y": pa["fallback"]["median"], "share": round(share, 3),
                                   "over": {"menu": b["menu"], "key": b["key"], "x": pb["cost"]["median"],
                                            "y": pb["fallback"]["median"]}})
        for i, a in enumerate(pts):
            for b in pts[i + 1:]:
                if (lv, a["menu"], a["key"]) in hidden or (lv, b["menu"], b["key"]) in hidden:
                    continue
                for orient, field, axis in (("x", "cost", 1), ("y", "fallback", 0)):
                    if orient == "y" and (a["spine"] or b["spine"]):
                        continue
                    ia, ib = data[lv][a["menu"]][a["key"]][field], data[lv][b["menu"]][b["key"]][field]
                    if not (_bar_drawn(ia, orient) and _bar_drawn(ib, orient)):
                        continue
                    lo, hi = max(ia["ci_lo"], ib["ci_lo"]), min(ia["ci_hi"], ib["ci_hi"])
                    d = abs(float(a["P"][axis] - b["P"][axis]))
                    if hi > lo and d < style.UNCERTAINTY_PT + BAR_GAP_PT:
                        bars.append({"level": lv, "orient": orient, "a": {"menu": a["menu"], "key": a["key"]},
                                     "b": {"menu": b["menu"], "key": b["key"]}, "lo": lo, "hi": hi,
                                     "d_pt": round(d, 2)})
    return partly, bars


def _sig3(v: float) -> str:
    return f"{v:#.3g}".rstrip(".")


def note_name(key: str, quote: bool | None = None) -> str:
    """The policy's legend name (style.POLICIES label) as plain text: mathtext such as $N_{\\mathrm{Extra}}=1$ as
    "N_Extra = 1"; in quotes where `quote`, by default where it holds a comma, so that it reads as one name in a
    clause."""
    def plain(m):
        s = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", m.group(1)).replace("\\%", "%")       # C47: sublet_ms4's 10\\%
        s = re.sub(r"_\{([^}]*)\}", r"_\1", s)
        return re.sub(r"\s*=\s*", " = ", s)
    name = re.sub(r"\$([^$]*)\$", plain, style.POLICIES[key].label)
    return f"'{name}'" if (("," in name) if quote is None else quote) else name


def _letter(level: str) -> str:
    return "abcdefghij"[LEVELS.index(level)]


def under_text(u: Mapping, form: str = "under") -> str:
    """The note clause of a point under another: hidden (`under`, hidden_points) or partly under (`partly`,
    overlaps)."""
    o = u["over"]
    return LABELS[form].format(letter=_letter(u["level"]), name=note_name(u["key"]), menu=u["menu"],
                               x=_sig3(u["x"]), y=_sig3(u["y"]), over=note_name(o["key"]), over_menu=o["menu"],
                               ox=_sig3(o["x"]), oy=_sig3(o["y"]))


def bars_text(b: Mapping) -> str:
    """The note clause of two interval bars that print as one line (overlaps)."""
    a, c = b["a"], b["b"]
    q = any("," in note_name(k, quote=False) for k in (a["key"], c["key"]))     # both quoted, or neither
    na, nc = note_name(a["key"], q), note_name(c["key"], q)
    points = (f"the {a['menu']}-menu points of {na} and {nc}" if a["menu"] == c["menu"] else
              f"the {a['menu']}-menu point of {na} and the {c['menu']}-menu point of {nc}")
    return LABELS["bars"].format(letter=_letter(b["level"]), what="cost" if b["orient"] == "x" else "fallback-share",
                                 points=points, lo=_sig3(b["lo"]), hi=_sig3(b["hi"]), d=f"{b['d_pt']:.2g}")


def coincide_texts(data: Mapping) -> tuple[str, str]:
    """(labels.coincide, the note's clause) on Two-timescale PD's merged modes (a6_coincide): where they give one
    point in every cell with a point, the clause says so and names the legend entry (as legend() writes it); else it
    lists the cells drawn as one point (none: no clause)."""
    base = style.POLICIES["a6"].label
    modes = ", ".join(lab[len(base) + 2:] if lab.startswith(base + ", ") else "default"
                      for lab in (style.POLICIES[k].label for k in ("a6", "a6_red_off", "a6_always2")))
    kw = dict(name=base, modes=modes, pct=round(COINCIDE_REL * 100, 6))
    rule = LABELS["coincide"].format(**kw)
    cells = [(lv, menu) for lv in data["levels"] for menu in MENUS if data[lv][menu]["a6"]["cost"]["median"] is not None]
    one = [(lv, menu) for lv, menu in cells if data["a6_coincide"][lv][menu]["drawn_as_one"]]
    if cells and len(one) == len(cells):
        return rule, LABELS["coincide_all"].format(**kw, all_modes=LABELS["a6_all_modes"])
    if not one:
        return rule, ""
    return rule, rule + ": " + ", ".join(f"({_letter(lv)}) {menu} menu" for lv, menu in one)


def default_n_extra(meta_tags: Mapping, tag: str) -> int | None:
    """N_Extra of BL3's default run: its tag's params.n_extra, else the number that ends the tag (the driver's tags
    BL3-0, BL3-1, BL3-2 name it), where the other BL3 tags' params agree with that naming; None otherwise."""
    ent = meta_tags.get(tag) if isinstance(meta_tags, Mapping) else None
    params = ent.get("params") if isinstance(ent, Mapping) else None
    if isinstance(params, Mapping) and params.get("n_extra") is not None:
        return int(params["n_extra"])
    m = re.fullmatch(r"BL3-(\d+)", tag)
    named = {t: v.get("params", {}).get("n_extra") for t, v in meta_tags.items()
             if isinstance(v, Mapping) and isinstance(v.get("params"), Mapping) and re.fullmatch(r"BL3-\d+", t)}
    if m is None or any(n is not None and int(t.split("-")[1]) != int(n) for t, n in named.items()):
        return None
    return int(m.group(1))


def y_range(data: Mapping) -> tuple[float, float]:
    """(lo, hi) of the positive median shares and their intervals (a zero or null share is on the x spine and its
    interval not drawn), at least a decade wide and at most 1."""
    pts = [data[lv][m][k]["fallback"] for lv in LEVELS for m in MENUS for k in KEYS]
    v = finite_values(*([p[f] for p in pts if (p["median"] or 0) > 0] for f in ("median", "ci_lo", "ci_hi")))
    v = v[v > 0]
    if not v.size:
        return 0.01, 1.0
    return float(v.min()), float(min(max(v.max(), v.min() * 10.0), 1.0))


def draw_panel(ax, block: Mapping, y_floor: float, flags: Mapping) -> set:
    """Both menus' points with their interval bars; a share of 0 or null on the x spine (clip_on False). Where the
    three A6 modes coincide (flags.<menu>.drawn_as_one), A6's default ('rule', key a6) alone is drawn: three markers
    on one point would show a mix of their outlines (as built, the square of 'off' around the hexagon). Returns the
    keys drawn."""
    drawn = set()
    for menu in MENUS:
        face = {} if menu == "short" else {"markerfacecolor": "white", "markeredgewidth": OPEN_EDGE_PT}
        for key in DRAW_ORDER:
            if flags[menu]["drawn_as_one"] and key in A6_KEYS and key != "a6":
                continue
            p = block[menu][key]
            x, y = p["cost"]["median"], p["fallback"]["median"]
            if x is None:
                continue
            on_spine = y is None or y <= 0
            yy = y_floor if on_spine else y
            pol = style.policy(key)
            for (lo, hi), orient in (((p["cost"]["ci_lo"], p["cost"]["ci_hi"]), "x"),
                                     ((p["fallback"]["ci_lo"], p["fallback"]["ci_hi"]), "y")):
                if on_spine and orient == "y":
                    continue
                if lo is not None and hi is not None and hi > lo and (orient == "x" or lo > 0):
                    style.errorbars(ax, key, [x], [yy], [lo], [hi], orientation=orient,
                                    zorder=BAR_Z - (0.05 if menu == "long" else 0.0))
            ln = style.scatter_policy(ax, key, [x], [yy], clip_on=not on_spine, label="_nolegend_",
                                      zorder=pol.zorder - (LONG_DZ if menu == "long" else 0.0), **face)
            ln._sublet_menu, ln._sublet_spine = menu, on_spine         # for overlaps()
            drawn.add(key)
    return drawn


def x_axis(ax, block: Mapping) -> None:
    v = finite_values(*([block[m][k]["cost"][f] for k in KEYS] for m in MENUS for f in ("median", "ci_lo", "ci_hi")))
    v = v[v > 0]
    lo, hi = (float(min(v.min(), 1.0)), float(max(v.max(), 1.0))) if v.size else (0.9, 1.1)
    log_axis_over(ax, "x", lo, hi, pad=X_PAD, ticks=log_ticks(lo / X_PAD, hi * X_PAD))
    style.end_label_inside(ax)
    thin_tick_labels(ax)


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    lo, hi = y_range(data)
    y_floor = lo * SPINE_FLOOR
    ticks = log_ticks(y_floor, hi * 1.15)
    # (a)'s left reserve fits its tick labels (a share axis reaching 0.003 has five-character labels)
    res = max(style.LEFT_LABEL, style.ytick_reserve(fig, [style.PLAIN(t) for t in ticks], ylabel=True))
    axes = style.panel_row(fig, (1, 1, 1, 1, 1), legend=LEGEND_RESERVE, sharey=(False, True, True, True, True),  # C59
                           left=(res, None, None, None, None))
    style.log_axis(axes[0], "y", ticks=ticks)
    axes[0].yaxis.set_minor_locator(NullLocator())
    axes[0].set_ylim(y_floor, hi * 1.15)
    _top_tick_room(axes[0])                   # the top tick label clear of the panel title
    drawn: set = set()
    for ax, lv in zip(axes, data["levels"]):
        ax._sublet_level = lv
        drawn |= draw_panel(ax, data[lv], y_floor, data["a6_coincide"][lv])
        x_axis(ax, data[lv])
        style.reference_line(ax, x=1.0)
    center_xlabel(axes, lab["x"])          # C62: one x label under the five panels (as built, one per panel)
    axes[0].set_ylabel(lab["y"])
    letters = style.panel_letters(axes)
    # C62 (fix round): the titles at the caption size (style.LABEL_PT; at TICK_PT as first restyled), those with p_sh
    # on the letters' baseline as printed (the letters and "Trace lender" are the plain references)
    titles = [panel_title(ax, letter, lab["panel"][lv], fontsize=style.LABEL_PT)
              for ax, letter, lv in zip(axes, letters, data["levels"])]
    align_baselines(letters + titles)
    legend(fig, data, drawn, lab)
    for ax, lv in zip(axes, data["levels"]):
        drop_idle_halos(ax, hidden_labels(ax, [u for u in data.get("under", []) if u["level"] == lv]))
    return fig


def hidden_labels(ax, under: Sequence[Mapping]) -> list:
    """A label (style.TICK_PT) naming each point that lies under another (hidden_points) and the point over it ("Two-timescale
    PD (hidden by Sublet)", labels.hidden; as first built the label gave the name alone, and a leader that can reach
    the stack only from below ended on Sublet's disk), in the hidden policy's label color (darkened to 4.5:1 against
    white), with a white halo (draw() drops it where it overlaps nothing), joined to the hidden marker's edge by a
    LEADER_PT grey leader drawn under Sublet's marker.
    The label goes on the free space of the panel (common._occupancy: KEY_PAD_PT clear of every line, bar, marker and
    text) where its leader is shortest among those whose leader (1) is straight and runs 15-75 degrees from the
    horizontal (LEADER_ANGLES: a straight leader near the vertical or horizontal reads as an interval bar; as first
    built a vertical one did), else is an arc (LEADER_RADS, which no bar resembles), (2) arrives from the side away
    from the point drawn over the hidden one, (3) spans at most LEADER_MAX_PT and crosses nothing beyond that point's
    marker, and whose label box stays LABEL_CLEAR_PT from every other marker and LEVEL_CLEAR_PT from one level with
    it (as first built, a label nearest the point sat beside Sublet's long-menu circle, level with it, and read as its
    label); the name in one line, else in two. Nothing where no box qualifies (the note states the point either way).
    Returns the labels drawn."""
    out = []
    fig = ax.figure
    r = fig.canvas.get_renderer()
    to_pt = style.BP_PER_IN / fig.dpi
    marks = [(ln, points_pt(ax, *np.asarray(ln.get_xydata(), dtype=float).T)) for ln in ax.lines
             if hasattr(ln, "_sublet_policy") and ln.get_marker() not in (None, "None", "none", "")]
    for u in under:
        pol, opol = style.policy(u["key"]), style.policy(u["over"]["key"])
        P = points_pt(ax, [u["x"]], [u["y"]])[0]
        O = points_pt(ax, [u["over"]["x"]], [u["over"]["y"]])[0]
        others = [q for _, qs in marks for q in qs if min(np.hypot(*(q - P)), np.hypot(*(q - O))) > 1e-3]
        rad = 0.5 * (pol.markersize + style.MARKER_EDGE_PT)
        r0 = max(np.hypot(*(P - O)) + 0.5 * (opol.markersize + style.MARKER_EDGE_PT), rad) + KEY_PAD_PT + GRID_RES_PT
        taken, gx0, gy0 = _occupancy(ax)
        under_lab = LABELS["hidden"].format(over=opol.label)
        short = LABELS.get("hidden_short", "(hidden)")
        texts = [f"{pol.label}\n{under_lab}"] + \
            ([f"{chr(10).join(pol.label.rsplit(' ', 1))}\n{under_lab}"] if " " in pol.label else [])
        # C47: then without the name of the point over it (sublet_ms4's label makes the forms above 3.5 in wide); the
        # leader ends at the stack, whose top marker is that point, and labels.note names it
        texts += [f"{pol.label}\n{short}"] + \
            ([f"{chr(10).join(pol.label.rsplit(' ', 1))}\n{short}"] if " " in pol.label else [])
        for text in texts:
            t = ax.text(0.0, 0.0, text, fontsize=style.TICK_PT, ha="left", va="bottom", transform=ax.transAxes,
                        color=pol.label_color, zorder=style.Z_THEORY_LABEL)
            bb = t.get_window_extent(r)
            spot = leader_spot(taken, gx0, gy0, bb.width * to_pt, bb.height * to_pt, P, O, others, rad, r0)
            if spot is None:
                t.remove()
                continue
            (bx, by), (cx, cy), f = spot
            t.set_position(tuple(ax.transAxes.inverted().transform(np.array([bx, by]) / to_pt)))
            _halo_texts([t])
            t._sublet_role = "direct_label:hidden"
            ld = ax.annotate("", xy=(u["x"], u["y"]), xytext=(cx - P[0], cy - P[1]), textcoords="offset points",
                             arrowprops=dict(arrowstyle="-", color=style.THEORY_GREY, linewidth=LEADER_PT,
                                             shrinkA=0.5, shrinkB=rad, connectionstyle=f"arc3,rad={f:g}"),
                             zorder=leader_z(u))
            ld._sublet_role = "hidden_leader"
            out.append(t)
            break
    return out


def leader_z(u: Mapping) -> float:
    """The z-order of the leader of a hidden point (hidden_points' entry u): LEADER_Z, over the other markers, but
    below the marker drawn over the hidden point (C47: sublet_ms4 is drawn at the common z-order, not at Sublet's
    Z_SUBLET above it, so a leader at LEADER_Z would cross that marker)."""
    o = u["over"]
    return min(LEADER_Z, style.policy(o["key"]).zorder - (LONG_DZ if o["menu"] == "long" else 0.0) - 0.05)


def leader_spot(taken, gx0: float, gy0: float, w: float, h: float, P, O, others, rad: float, r0: float):
    """((x0, y0) of a free w x h box, (x, y) of its point nearest P, the arc3 rad of its leader) in pt, the box of
    hidden_labels' rules whose leader from P is shortest, a straight one first, else one curved by LEADER_RADS (taken:
    common._occupancy's grid, cells GRID_RES_PT from (gx0, gy0)); None if no box qualifies."""
    res = GRID_RES_PT
    wi, hj = int(math.ceil(w / res)), int(math.ceil(h / res))
    if hj > taken.shape[0] or wi > taken.shape[1]:
        return None
    jj, ii = np.nonzero(_box_sum(taken, hj, wi) == 0)
    if not jj.size:
        return None
    x0, y0 = gx0 + ii * res, gy0 + jj * res
    cx, cy = np.clip(P[0], x0, x0 + w), np.clip(P[1], y0, y0 + h)
    vx, vy = cx - P[0], cy - P[1]
    L = np.hypot(vx, vy)
    ang = np.degrees(np.arctan2(np.abs(vy), np.abs(vx)))
    away = P - O
    ok = (L <= LEADER_MAX_PT) & (L >= rad + 1.0) & (vx * away[0] + vy * away[1] >= 0.0)
    for q in others:
        dx = np.maximum(np.maximum(x0 - q[0], 0.0), q[0] - (x0 + w))
        dy = np.maximum(np.maximum(y0 - q[1], 0.0), q[1] - (y0 + h))
        ok &= (np.hypot(dx, dy) >= LABEL_CLEAR_PT) & ((dy > rad) | (dx >= LEVEL_CLEAR_PT))
    straight = (ang >= LEADER_ANGLES[0]) & (ang <= LEADER_ANGLES[1])
    for f in LEADER_RADS:
        cand = np.nonzero(ok & straight)[0] if f == 0.0 else np.nonzero(ok)[0]
        for k in cand[np.argsort(L[cand], kind="stable")]:
            S = np.array([cx[k], cy[k]])
            if leader_clear(taken, gx0, gy0, S, P, O, f, r0):
                return (float(x0[k]), float(y0[k])), (float(cx[k]), float(cy[k])), f
    return None


def leader_clear(taken, gx0: float, gy0: float, S, P, O, f: float, r0: float) -> bool:
    """Whether a leader from S to P, matplotlib's arc3 with rad f (a quadratic Bezier whose control point is the
    chord's midpoint plus f times the chord turned clockwise), crosses no taken cell farther than r0 from P, stays in
    the grid, and arrives at P from the side away from O."""
    res = GRID_RES_PT
    d = P - S
    C = 0.5 * (S + P) + f * np.array([d[1], -d[0]])
    if np.dot(C - P, P - O) < 0.0 and np.hypot(*(P - O)) > 1e-6:
        return False
    n = max(int(2.0 * np.hypot(*d) / (0.5 * res)), 2)
    t = np.linspace(0.0, 1.0, n)[:, None]
    pts = (1 - t) ** 2 * S + 2 * (1 - t) * t * C + t ** 2 * P
    pts = pts[np.hypot(pts[:, 0] - P[0], pts[:, 1] - P[1]) >= r0]
    ij = np.floor((pts - [gx0, gy0]) / res).astype(int)
    inside = (ij[:, 0] >= 0) & (ij[:, 0] < taken.shape[1]) & (ij[:, 1] >= 0) & (ij[:, 1] < taken.shape[0])
    return bool(inside.all() and not taken[ij[:, 1], ij[:, 0]].any())


def menu_handles(lab: Mapping) -> list[tuple[Line2D, str]]:
    """C47 (print check of the gate): the legend's samples of the menus' encoding, black circles (MENU_MARKER, a
    marker no E5 series has) at the registry's marker size: filled for the short-notice menu, open (white face,
    OPEN_EDGE_PT edge, as draw_panel draws the long menu) for the long-notice menu; generic black samples, as
    style.env_handles' line styles, so that neither reads as a policy."""
    kw = dict(linestyle="none", marker=MENU_MARKER, markersize=style.MARKER_PT, color="black", markeredgecolor="black")
    names = lab.get("menu") or LABELS["menu"]
    return [(Line2D([], [], markerfacecolor="black", markeredgewidth=style.MARKER_EDGE_PT, **kw), names["short"]),
            (Line2D([], [], markerfacecolor="white", markeredgewidth=OPEN_EDGE_PT, **kw), names["long"])]


def legend(fig, data: Mapping, drawn: set, lab: Mapping):
    """The two legend rows of the keys drawn in some panel, in the registry's order (a key drawn nowhere, an A6
    mode whose point coincides with A6's default in every cell, is left out); where neither of A6's other modes is
    drawn anywhere while A6 is, and every cell with A6 merges the three modes, A6's entry reads 'all modes'.
    C47 (print check of the gate): the policies fill the two rows column by column, as style.legend_row's aligned
    columns placed them (on E5: the guard, SpotHedge-style at N_Extra = 0 and at its default; Two-timescale PD and
    SpotHedge-style at N_Extra = 1), and the menus' samples (menu_handles) follow in the second row, each row side by
    side and centered (ms4_lib.legend_rows_above); where these rows do not fit, the policies alone in
    style.legend_row's two aligned rows, else side by side in two rows of their own (ms4_lib.split_rows), and
    labels.note alone states the menus' encoding. C62: first the rows of the module docstring's C62 paragraph (the
    guard and Two-timescale PD; SpotHedge-style and the menus), the C47 and C59 rows only where those do not fit.
    Returns the legends, top row first."""
    keys = style.legend_order([k for k in KEYS if k in drawn])
    pairs = style.policy_handles(keys, lines=False)
    merged = all(f["drawn_as_one"] for lv in data["levels"] for menu, f in data["a6_coincide"][lv].items()
                 if data[lv][menu]["a6"]["cost"]["median"] is not None)
    if "a6" in drawn and merged and not drawn & (set(A6_KEYS) - {"a6"}):
        pairs = [(h, lab.get("a6_all_modes", t) if t == style.POLICIES["a6"].label else t) for h, t in pairs]
    # C62 (7-pt text): the rows by family, each side by side and centered, every label on its row's baseline as
    # printed: first the guard and Two-timescale PD (its modes where they are apart), then SpotHedge-style in N_Extra's
    # order and the menus' samples; the guard's label on one line where the rows fit so, else in words on two lines
    # (C59, wrap_wide). As built at 9 pt, the guard's label wrapped and the entries dealt alternately to the two rows,
    # which at 7 pt fit with A6's modes apart and then listed them out of order
    for wrap, gap in ((False, LEGEND_ROW_GAP_EM), (True, LEGEND_GAP_EM)):
        ps = wrap_wide(fig, pairs) if wrap else pairs
        rows = [r for r in ([p for k, p in zip(keys, ps) if k not in BL3_KEYS],
                            [p for k, p in zip(keys, ps) if k in BL3_KEYS] + menu_handles(lab)) if r]
        try:
            legs = legend_rows_above(fig, rows, n_rows=LEGEND_RESERVE, handlelength=LEGEND_HANDLE, gap_em=gap)
        except style.StyleError:
            continue
        for leg in legs:
            align_baselines(leg.get_texts())
        return legs
    pairs = wrap_wide(fig, pairs)          # C59: the guard's label in words on two lines (as built one line)
    try:
        return [style.legend_row(fig, [], extra=pairs, rows=2, lines=False)]
    except style.StyleError:
        # C47: with sublet_ms4's label the two column-aligned rows hold at most five entries (on E5 the drawn ones);
        # where more are drawn (A6's modes apart), the entries in order, side by side in two rows of their own
        return legend_rows_above(fig, split_rows(fig, pairs, max_rows=2), n_rows=LEGEND_RESERVE,
                                 gap_em=LEGEND_GAP_EM)                                                     # C59


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
