"""sf_e8_v2: the request-level replay of Sublet and its baselines, fluid against replayed cost, and the tables
e8v2_tiers.tex and e8v2_mooncake.tex with the data file e8v2_cells.csv (design/ms7/w_spec.md §4, unit W-G4, writer C;
design/ms7/registration.md §2-§3, X3, E8 v2 part (a); change C58).

Question: does replaying the fluid runs request by request change which policies cost less than Sublet?

Inputs (RUN_INPUTS, the MS7 run outputs; a missing one stops the build with exit code 2 and the file named; figs/
rebuild.py keeps the entry pending until they are copied in): the registered analysis code/sim/out/e8v2/analysis.json
(sublet/experiments/ms7_sens_analysis.py, frozen by its sha256: every cost, error E, ranking and count is read from it;
the figure's ratios are those costs divided by Sublet's) and the summary it read, code/sim/out/e8v2/a/summary.json (the
grid: tiers, windows, alignments, mu, the Mooncake point; checked against the sha256 that the analysis recorded). A6,
the two-timescale PD, is E8's stored run (the analysis's reused A6; E8v2-0 checks its identity). A non-reduced analysis
must be the registered one on full runs. Descriptive statistics; no p-value.

Figure (W2 x HEIGHT_IN in; 2.2 in as built at 9 pt, 2.5 in since C62 for nearly square panels). Three panels side by
side, log-log, each policy's cost over Sublet's in the same cell, in the
fluid model (x: C_fluid / C_fluid of Sublet) and in the replay (y: C_replay / C_replay of Sublet), overflow accounting
in USD; one marker per cell in the registry style, Sublet at (1, 1) as the reference; grey lines at x = 1 and y = 1, and
the diagonal y = x (the same ratio in both); the two quadrants where the replay reverses a policy's order with Sublet (x
< 1 < y, y < 1 < x) shaded: (a) the Azure 2024 conversation week of the request-level instance at mu = beta~, one point
per tier (S, M, L), smoothing window and alignment; (b) and (c) the Mooncake conversation hour (tier M, one alignment)
without and with prefix hits, one point per window. Each panel's range covers its points (log ticks of ms4_lib, the same
range on both axes, the top raised where the highest y tick label needs room below the panel title). Points with a
missing cost are counted in the extract and left out. Legend: Sublet and the policies drawn in some panel, above the
panels (one row where it fits, else two). C62: the shaded quadrants are named once, "Order reversed" (sentence case, as
every label), in (a)'s lower right corner where no point lies under the text (else its upper left one; shade_label);
the panel titles at the caption size (LABEL_PT) on the letters' baseline.

Tables (after hook, figs.common.write_table, from the extract's `tables`, so --from-extract rewrites them byte for byte;
longtables of ms5b_e7_lib):
  e8v2_tiers.tex    per tier and window over the alignments: the alignments with both rankings of the four policies,
                    those with the same fluid and replayed order, with Sublet first in each, and with Sublet below both
                    Greedy, back-off and RetroRenting-style in each (the analysis's by_tier_window counts); and the
                    relative cost error E = (C_replay - C_fluid) / C_replay, the median over the alignments per policy,
                    with Sublet's min-max;
  e8v2_mooncake.tex per window and prefix setting of the Mooncake hour: each policy's fluid and replayed cost (USD),
                    whether the four policies' orders agree, and Sublet's rank in each;
  e8v2_cells.csv    every cell: costs, E, each policy's rank among the four and among the five, fluid and replayed.
Every policy is named by its registry label; no tag, file or design name is printed.

labels.caption is a caption draft for the integrator (the supplement part s_f3.tex), labels.values the counts and
values it reads from the inputs (candidate \\val entries); headline is the analysis's headline block, unchanged.

Run from code/sim: python -m figs.supp.sf_e8_v2 [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

from matplotlib.ticker import FixedLocator, NullLocator

from figs import style
from figs.common import MissingKey, _top_tick_room, need, panel_title, thin_tick_labels, write_table
from figs.inputs import Inputs
from figs.supp import ms7_x3_lib as X
from figs.supp.ms4_lib import log_ticks

NAME = "sf_e8_v2"
ANALYSIS = "code/sim/out/e8v2/analysis.json"
SUMMARY = "code/sim/out/e8v2/a/summary.json"
RUN_INPUTS = (ANALYSIS, SUMMARY)
INPUTS = RUN_INPUTS
KEYS = style.SUPP_POLICIES_MS7[NAME]
REF = "Sublet"
TAGS4 = ("Sublet", "A9", "BL1-BO", "BL5-cur")          # ms7_sens_analysis.TAGS4
TAGS = ("Sublet", "A9", "A6", "BL5-cur", "BL1-BO")      # in the order of KEYS
OTHERS = tuple(t for t in TAGS if t != REF)
PREFIX = ("off", "on")
TABLES = ("e8v2_tiers.tex", "e8v2_mooncake.tex", "e8v2_cells.csv")
CELLS_CSV = TABLES[-1]
# C62: 2.5 in (2.2 as built at 9 pt): each panel's axes nearly square (1.79 by 1.93 in), the same range on both axes,
# so that the diagonal y = x runs at about 45 degrees and the points spread over the height the smaller text frees
HEIGHT_IN = 2.5
style.register_supplementary(NAME, "W2", HEIGHT_IN)
PAD = 1.25                         # each panel's log range extends this factor beyond its points and 1
SHADE = style.SHADE_GREY
DIAG = dict(color=style.REFERENCE_GREY, linewidth=style.REFERENCE_PT, linestyle=(0, (3.0, 1.6)),
            zorder=style.Z_REFERENCE)
SHADE_LABEL_PT = 3.0               # C62: the shaded quadrants' name this far inside (a)'s lower right corner
LABELS = {"x": "Fluid cost / Sublet's", "y": "Replayed cost / Sublet's",
          "shade": "Order reversed",           # C62: the shaded quadrants named once, in (a) (sentence case)
          "titles": {"a": "Request-level week", "b": "Mooncake, no prefix hits", "c": "Mooncake, prefix hits"},
          "caption": (
              "Fidelity of the fluid routing model for {sublet} and its baselines: each policy's cost over {sublet}'s "
              "in the same cell (overflow accounting), in the fluid model (x) and replayed request by request (y), "
              "logarithmic scales. (a) The request-level instance's Azure 2024 conversation week at "
              "$\\mu=\\tilde{{\\beta}}$, one point per tier ({tiers}), smoothing window ({windows} min) and "
              "alignment ({alignments}); (b) the Mooncake conversation hour (tier {mc_tier}), one point per window, "
              "without and (c) with prefix hits. In the shaded quadrants the replay reverses a policy's order with "
              "{sublet}; on the dashed diagonal the ratio is unchanged. The fluid and replayed orders of {sublet}, "
              "{cr}, {rr} and {bo} agree in {same} of {n} cells of (a); {sublet} costs less than both {bo} and {rr} "
              "in {beats_f} of the {n} cells in the fluid model and in {beats_r} replayed.")}


# ---------------------------------------------------------------------------------------------------------------
# data
def _ratio(a, b):
    if a is None or b is None or not float(b) > 0 or not float(a) > 0:
        return None
    return float(a) / float(b)


def scatter(cells: Sequence[tuple[dict, Mapping]]) -> dict:
    """{tag: [{cell..., x, y, fluid, replay}]} of the policies other than Sublet over `cells` ((id, the analysis's
    rank block)); the cells without a ratio are counted in 'missing'."""
    out, missing = {t: [] for t in OTHERS}, {t: 0 for t in OTHERS}
    for cid, e in cells:
        fl, rp = e.get("fluid") or {}, e.get("replay") or {}
        for t in OTHERS:
            x, y = _ratio(fl.get(t), fl.get(REF)), _ratio(rp.get(t), rp.get(REF))
            if x is None or y is None:
                missing[t] += 1
                continue
            out[t].append({**cid, "x": x, "y": y, "fluid": fl.get(t), "replay": rp.get(t),
                           "flipped": bool((x - 1.0) * (y - 1.0) < 0.0)})
    return {"points": out, "missing": missing,
            "n_cells": len(cells), "ref_cells": sum(1 for _c, e in cells if _ratio((e.get("fluid") or {}).get(REF), 1.0)
                                                    and _ratio((e.get("replay") or {}).get(REF), 1.0))}


def build_panels(ana: Mapping) -> dict:
    inst = [({"tier": tier, "window": w, "alignment": c}, e) for tier, a in (ana.get("cells") or {}).items()
            for w, b in a.items() for c, e in b.items()]
    mc = {pf: [({"window": w, "prefix": pf}, (ana.get("mooncake") or {})[w][pf]) for w in (ana.get("mooncake") or {})
               if pf in (ana.get("mooncake") or {})[w]] for pf in PREFIX}
    return {"a": scatter(inst), "b": scatter(mc["off"]), "c": scatter(mc["on"])}


def tier_rows(ana: Mapping) -> list[dict]:
    out = []
    for tier, a in (ana.get("by_tier_window") or {}).items():
        for w, x in a.items():
            es = [((ana["cells"][tier][w][c] or {}).get("E") or {}).get(REF) for c in ana["cells"][tier][w]]
            lo, hi = X.extent(es)
            out.append({"tier": tier, "window": w, **{k: x.get(k) for k in (
                "n_alignments", "n", "same_order", "sublet_first_fluid", "sublet_first_replay",
                "sublet_beats_pair_fluid", "sublet_beats_pair_replay")},
                "E_median": {t: (x.get("E_median") or {}).get(t) for t in TAGS}, "E_sublet_lo": lo, "E_sublet_hi": hi})
    return out


def mooncake_rows(ana: Mapping) -> list[dict]:
    out = []
    for w, a in (ana.get("mooncake") or {}).items():
        for pf in PREFIX:
            e = a.get(pf)
            if e is None:
                continue
            out.append({"window": w, "prefix": pf, "fluid": {t: (e.get("fluid") or {}).get(t) for t in TAGS},
                        "replay": {t: (e.get("replay") or {}).get(t) for t in TAGS}, "same_order": e.get("same_order"),
                        "same_order_with_a6": e.get("same_order_with_a6"),
                        "sublet_rank_fluid": e.get("sublet_rank_fluid"),
                        "sublet_rank_replay": e.get("sublet_rank_replay"), "E": dict(e.get("E") or {})})
    return out


def _rank_of(r, t):
    return None if r is None or t not in r else r.index(t) + 1


def cells_csv(ana: Mapping, mc_point: Mapping) -> dict:
    cols = ("part", "tier", "window_min", "alignment", "prefix_hits", "policy", "tag", "c_fluid_usd", "c_replay_usd",
            "error", "rank_fluid_of_4", "rank_replay_of_4", "rank_fluid_of_5", "rank_replay_of_5", "same_order_of_4",
            "source")
    rows = []

    def add(part, tier, w, c, pf, e):
        for t in TAGS:
            src = "the earlier replay study's stored runs" if t == "A6" else "this study"
            rows.append((part, tier, int(w), c, pf, X.plain(X.label_of(t)), t, (e.get("fluid") or {}).get(t),
                         (e.get("replay") or {}).get(t), (e.get("E") or {}).get(t),
                         _rank_of(e.get("rank_fluid"), t), _rank_of(e.get("rank_replay"), t),
                         _rank_of(e.get("rank_fluid_with_a6"), t), _rank_of(e.get("rank_replay_with_a6"), t),
                         e.get("same_order"), src))
    for tier, a in (ana.get("cells") or {}).items():
        for w, b in a.items():
            for c, e in b.items():
                add("instance", tier, w, int(c), None, e)
    for w, a in (ana.get("mooncake") or {}).items():
        for pf, e in a.items():
            add("mooncake", mc_point.get("tier"), w, mc_point.get("c"), pf, e)     # review: the hour's alignment too
    return X.csv_entry(CELLS_CSV, cols, rows)


def build(inp: Inputs) -> dict:
    ana = X.load(inp, ANALYSIS, script=NAME, run_inputs=RUN_INPUTS)
    summ = X.load(inp, SUMMARY, script=NAME, run_inputs=RUN_INPUTS)
    prov = X.provenance(ana, ANALYSIS)
    X.check_registered(prov, NAME)
    shas = X.check_input_shas(prov, inp, {"out/e8v2/a/summary.json": SUMMARY}, NAME)
    shas[ANALYSIS] = X.sha256_of(inp, ANALYSIS)
    meta = need(summ, "meta", what=SUMMARY)
    grid = need(meta, "grid", what=f"{SUMMARY} meta")
    if not ana.get("cells"):
        raise MissingKey(f"{ANALYSIS}: no cells")
    data = {"panels": build_panels(ana), "grid": {k: grid.get(k) for k in ("tiers", "windows", "alignments", "mu",
                                                                            "mooncake_point", "horizon_min",
                                                                            "market_tightness")},
            "tables": {"tiers": tier_rows(ana), "mooncake": mooncake_rows(ana),
                       "e8v2_cells": cells_csv(ana, grid.get("mooncake_point") or {})},
            "headline": ana.get("headline"),
            "meta": {"reduced": bool(prov["reduced"] or meta.get("reduced")),
                     "git_revision": {"analysis": prov["git_revision"], "summary": meta.get("git_revision")},
                     "analysis": prov, "inputs_sha256": shas},
            "labels": {k: v for k, v in LABELS.items() if k != "caption"}}
    data["layout"] = layout(data)
    data["labels"]["values"] = values(data)
    data["labels"]["caption"] = caption(data)
    return data


def values(d: Mapping) -> dict:
    h = d.get("headline") or {}
    c = h.get("cells") or {}
    flips = {p: {t: sum(1 for q in d["panels"][p]["points"][t] if q["flipped"]) for t in OTHERS} for p in d["panels"]}
    return {"n_cells": c.get("n_alignments"), "n_ranked": c.get("n"), "same_order": c.get("same_order"),
            "sublet_first_fluid": c.get("sublet_first_fluid"), "sublet_first_replay": c.get("sublet_first_replay"),
            "sublet_beats_pair_fluid": c.get("sublet_beats_pair_fluid"),
            "sublet_beats_pair_replay": c.get("sublet_beats_pair_replay"), "flipped_points": flips,
            "tiers": list(d["grid"].get("tiers") or []), "windows": list(d["grid"].get("windows") or []),
            "alignments": list(d["grid"].get("alignments") or []),
            "mooncake_tier": (d["grid"].get("mooncake_point") or {}).get("tier"),
            "E_median_range": h.get("E_median_range"), "cells_reordered": h.get("cells_reordered"),
            "mooncake_counts": h.get("mooncake")}


def caption(d: Mapping) -> str:
    v = d["labels"]["values"]
    lab = {t: style.POLICIES[X.key_of(t)].label for t in TAGS}

    def lst(xs):
        xs = [str(x) for x in xs]
        return "--" if not xs else xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]
    al = v["alignments"]
    al_t = f"{al[0]}--{al[-1]}" if len(al) > 1 and al == list(range(al[0], al[-1] + 1)) else lst(al)
    return LABELS["caption"].format(sublet=lab["Sublet"], cr=lab["A9"].lower(), rr=lab["BL5-cur"], bo=lab["BL1-BO"],
                                    tiers=", ".join(str(x) for x in v["tiers"]) or "--", windows=lst(v["windows"]),
                                    alignments=al_t, mc_tier=v["mooncake_tier"],
                                    same=v["same_order"], n=v["n_ranked"], beats_f=v["sublet_beats_pair_fluid"],
                                    beats_r=v["sublet_beats_pair_replay"])


# ---------------------------------------------------------------------------------------------------------------
# layout and drawing
def legend_keys(data: Mapping) -> list[str]:
    """The keys of the legend: Sublet (the reference at (1, 1)) and every policy drawn in some panel, in KEYS' order."""
    drawn = {X.key_of(REF)} | {X.key_of(t) for pan in data["panels"].values() for t, pts in pan["points"].items()
                               if pts}
    return [k for k in KEYS if k in drawn]


def _legend_rows(keys: Sequence[str]) -> int:
    """One legend row where the keys fit it (TICK_PT), else two."""
    fig = style.new_figure(NAME)
    style.panel_row(fig, (1, 1, 1), legend=1)
    try:
        style.legend_row(fig, keys, lines=False)
        return 1
    except style.StyleError:
        return 2


def layout(data: Mapping) -> dict:
    keys = legend_keys(data)
    out = {"legend_keys": keys, "legend_rows": _legend_rows(keys)}
    for p, pan in data["panels"].items():
        v = [1.0] + [q[k] for pts in pan["points"].values() for q in pts for k in ("x", "y")]
        lo, hi = min(v) / PAD, max(v) * PAD
        out[p] = {"range": [lo, hi], "ticks": log_ticks(lo, hi)}
    return out


def draw_panel(ax, pan: Mapping, lay: Mapping) -> None:
    lo, hi = lay["range"]
    ax.set_xscale("log")
    ax.set_yscale("log")
    far_lo, far_hi = lo / 100.0, hi * 100.0                           # beyond the limits: clipped by the axes
    for xy in (((far_lo, 1.0), (1.0, far_hi)), ((1.0, far_lo), (far_hi, 1.0))):     # x < 1 < y and y < 1 < x
        (x0, y0), (x1, y1) = xy
        style.shade_region(ax, (x0, x1), (y0, y1), color=SHADE)
    style.reference_line(ax, x=1.0)
    style.reference_line(ax, y=1.0)
    d, = ax.plot([far_lo, far_hi], [far_lo, far_hi], **DIAG)
    d._sublet_role = "diagonal"
    for t in reversed(OTHERS):                       # the first of the legend drawn last (on top)
        pts = pan["points"][t]
        if pts:
            style.scatter_policy(ax, X.key_of(t), [q["x"] for q in pts], [q["y"] for q in pts])
    style.scatter_policy(ax, X.key_of(REF), [1.0], [1.0])
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_locator(FixedLocator(lay["ticks"]))
        axis.set_minor_locator(NullLocator())
        axis.set_major_formatter(style.PLAIN)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    _top_tick_room(ax)                                # the top y tick label clear of the panel title
    thin_tick_labels(ax)


def shade_label(ax, pan: Mapping, text: str):
    """C62: the shaded quadrants named in the lower right one, in its corner (THEORY_LABEL_GREY, TICK_PT), where no
    point lies under the text; else in the upper left one's corner, on two lines; None (nothing drawn) where both
    corners hold a point."""
    r = ax.figure.canvas.get_renderer()
    pts = [ax.transData.transform((q["x"], q["y"])) for qs in pan["points"].values() for q in qs]
    pts.append(ax.transData.transform((1.0, 1.0)))
    pad = SHADE_LABEL_PT * ax.figure.dpi / style.BP_PER_IN
    for xy, off, ha, va, s in (((1.0, 0.0), (-SHADE_LABEL_PT, SHADE_LABEL_PT), "right", "bottom", text),
                               ((0.0, 1.0), (SHADE_LABEL_PT, -SHADE_LABEL_PT), "left", "top", text.replace(" ", "\n"))):
        t = ax.annotate(s, xy=xy, xycoords="axes fraction", xytext=off, textcoords="offset points", ha=ha, va=va,
                        fontsize=style.TICK_PT, color=style.THEORY_LABEL_GREY, zorder=style.Z_THEORY_LABEL)
        bb = t.get_window_extent(r).expanded(1.0, 1.0)
        if not any(bb.x0 - pad <= x <= bb.x1 + pad and bb.y0 - pad <= y <= bb.y1 + pad for x, y in pts):
            t._sublet_role = "shade_label"
            return t
        t.remove()
    return None


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    lay = data["layout"]
    fig = style.new_figure(NAME)
    axes = style.panel_row(fig, (1, 1, 1), legend=lay["legend_rows"])
    style.legend_row(fig, lay["legend_keys"], lines=False, rows=lay["legend_rows"])
    for ax, p in zip(axes, ("a", "b", "c")):
        draw_panel(ax, data["panels"][p], lay[p])
        ax.set_xlabel(lab["x"])
        ax.set_ylabel(lab["y"])
    if lab.get("shade"):
        shade_label(axes[0], data["panels"]["a"], lab["shade"])
    letters = style.panel_letters(axes)
    for ax, letter, p in zip(axes, letters, ("a", "b", "c")):     # C62: at the caption size, on the letters' baseline
        panel_title(ax, letter, lab["titles"][p], fontsize=style.LABEL_PT)
    fig._sublet_axes = dict(zip(("a", "b", "c"), axes))
    return fig


# ---------------------------------------------------------------------------------------------------------------
# tables
def _e(v) -> str:
    return X.num(v, ".3f")


def tiers_tex(t: Sequence[Mapping], d: Mapping) -> str:
    rows = []
    for r in t:
        n = r["n_alignments"]
        rows.append([X.tex(r["tier"]), str(r["window"]), f"{r['n']}/{n}", str(r["same_order"]),
                     str(r["sublet_first_fluid"]), str(r["sublet_first_replay"]), str(r["sublet_beats_pair_fluid"]),
                     str(r["sublet_beats_pair_replay"]), _e(r["E_median"]["Sublet"]),
                     X.span(r["E_sublet_lo"], r["E_sublet_hi"], ".3f")]
                    + [_e(r["E_median"][x]) for x in TAGS[1:]])
    groups = [i for i in range(1, len(t)) if t[i]["tier"] != t[i - 1]["tier"]]
    lab = {x: X.tex(style.POLICIES[X.key_of(x)].label) for x in TAGS}
    al = d["grid"].get("alignments") or []
    cap = (r"The request-level replay per tier and smoothing window over " + str(len(al)) + r" alignments: "
           # C59 (RC18(5)): the Ranked column's count in words
           r"Ranked, the alignments in which all four of Sublet, " + lab["A9"].lower() + ", " + lab["BL5-cur"]
           + r" and " + lab["BL1-BO"] + r" have a cost, of " + str(len(al)) + r"; Same, those in which their order by "
           r"fluid cost is their order by replayed cost; First, those in which Sublet costs least of the four, in the "
           r"fluid model (F) and replayed "
           r"(R); Below, those in which Sublet costs less than both " + lab["BL1-BO"] + r" and " + lab["BL5-cur"]
           + r"; and the relative cost error $E=(C_{\mathrm{replay}}-C_{\mathrm{fluid}})/C_{\mathrm{replay}}$ in "
           r"overflow accounting, the median over the alignments and, for Sublet, its range. "
           + lab["A6"] + r": the earlier replay study's runs. Every cell is in the data file "
           + CELLS_CSV.replace("_", r"\_") + ".")
    head_top = (r" & & & & \multicolumn{2}{c}{First} & \multicolumn{2}{c}{Below} & \multicolumn{6}{c}{$E$} \\" "\n"
                r"\cmidrule(lr){5-6}\cmidrule(lr){7-8}\cmidrule(lr){9-14}")
    header = ["Tier", r"\shortstack{Window\\(min)}", "Ranked", "Same", "F", "R", "F", "R",
              r"\shortstack{Sublet\\median}", r"\shortstack{Sublet\\range}", r"\shortstack{Critical-ratio\\renting}",
              r"\shortstack{Two-\\timescale PD}", r"\shortstack{RetroRenting-\\style}",
              r"\shortstack{Greedy,\\back-off}"]
    return X.longtable("@{}llrrrrrrrrrrrr@{}", cap, "tab:s-e8v2-tiers", header, rows, groups=groups,
                       tabcolsep="3.0pt", head_top=head_top)


def _yn(v) -> str:
    return "--" if v is None else ("yes" if v else "no")


def mooncake_tex(t: Sequence[Mapping], d: Mapping) -> str:
    rows = [[str(r["window"]), {"off": "without", "on": "with"}[r["prefix"]]]
            + [X.num(r["fluid"][x], ".2f") for x in TAGS] + [X.num(r["replay"][x], ".2f") for x in TAGS]
            + [_yn(r["same_order"]), "--" if r["sublet_rank_fluid"] is None else str(r["sublet_rank_fluid"]),
               "--" if r["sublet_rank_replay"] is None else str(r["sublet_rank_replay"])] for r in t]
    groups = [i for i in range(1, len(t)) if t[i]["window"] != t[i - 1]["window"]]
    lab = {x: X.tex(style.POLICIES[X.key_of(x)].label) for x in TAGS}
    tier = (d["grid"].get("mooncake_point") or {}).get("tier")
    cap = (r"The Mooncake conversation hour (tier " + X.tex(tier) + r", one alignment), replayed through each "
           r"policy's placements without and with prefix hits: the cost in overflow accounting (USD) in the fluid "
           r"model and replayed, of Sublet (S), " + lab["A9"].lower() + r" (C), " + lab["A6"] + r" (P), "
           + lab["BL5-cur"] + r" (R) and " + lab["BL1-BO"] + r" (G); Same: whether the four policies other than "
           + lab["A6"] + r" have the same order by both costs; Sublet's rank among the four, fluid (F) and replayed "
           r"(R). The fluid run does not depend on the prefix setting.")
    head_top = (r" & & \multicolumn{5}{c}{Fluid cost (USD)} & \multicolumn{5}{c}{Replayed cost (USD)} & & "
                r"\multicolumn{2}{c}{Rank} \\" "\n" r"\cmidrule(lr){3-7}\cmidrule(lr){8-12}\cmidrule(lr){14-15}")
    header = [r"\shortstack{Window\\(min)}", r"\shortstack{Prefix\\hits}"] + ["S", "C", "P", "R", "G"] * 2 + \
        ["Same", "F", "R"]
    return X.longtable("@{}ll" + "r" * 10 + "lrr@{}", cap, "tab:s-e8v2-mooncake", header, rows, groups=groups,
                       tabcolsep="3.0pt", head_top=head_top)


def write_tables(data: Mapping, report: Mapping) -> None:
    t = data["tables"]
    paths = [write_table(TABLES[0], X.table_head(NAME, [ANALYSIS]) + tiers_tex(t["tiers"], data)),
             write_table(TABLES[1], X.table_head(NAME, [ANALYSIS]) + mooncake_tex(t["mooncake"], data)),
             X.write_csv(t["e8v2_cells"], NAME)]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    return X.run(NAME, build, draw, argv, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
