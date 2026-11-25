"""sf_e5_v2: redundancy under correlated reclaims with Sublet and SpotHedge-style with spares, and the tables
e5v2_costs.tex and e5v2_margins.tex with the data file e5v2_runs.csv (design/ms7/w_spec.md §4, unit W-G4, writer C;
design/ms7/registration.md §2-§3, X3; change C58).

Question: as the lenders' reclaims become correlated, and on a menu of short or long notice, does Sublet keep its cost
below that of its strongest baselines and of SpotHedge-style with spare replicas?

Inputs (RUN_INPUTS, the MS7 run outputs; a missing one stops the build with exit code 2 and the file named; figs/
rebuild.py keeps the entry pending until they are copied in): the registered analysis code/sim/out/e5v2/analysis.json
(sublet/experiments/ms7_sens_analysis.py, frozen by its sha256: every cost, saving and margin is read from it, nothing
recomputed but the minimum and maximum of a policy's r0 over the config seeds) and the summary it read, code/sim/out/
e5v2/summary.json (the correlation levels, the menus' notice periods and the grid; checked against the sha256 that the
analysis recorded). A non-reduced analysis must be the registered one on full runs. Descriptive statistics (medians and
min-max over the config seeds, plan D4); no p-value.

Figure (W2 x 2.5 in, the size of sf_e5). Three panels side by side, y the cost over the all-fallback cost in overflow
accounting (r0; log axis, each panel its own range), per policy its median over the config seeds (the analysis's
cells.<level>.<menu>.<mu>.by_tag.<tag>.median_r0) as a marker on a thin line in the registry style, with its min-max
over the config seeds as a 0.6-pt bar (style.errorbars), the policies dodged in x (DODGE_CAT category widths, DODGE_OCT
octaves in (c)) so that their bars do not sit on each other, and the level 1 (all-fallback) as a grey line: (a) the
short-notice menu and (b) the long-notice menu at mu = beta~, against the correlation level (categories: the trace
lender; correlated reclaims within the lenders' own groups at p_sh = 0.25, 0.5 and 1; one group of all lenders at p_sh
= 1); (c) the trace lender with the short-notice menu against mu / beta~ (log axis; the four policies of the stranding
runs, the six at mu = beta~). Legend: the six policies in two rows above the panels (one row at 7 pt is 7.3 in wide).
A cell without a run of a policy leaves a gap (none in a full run). C62: the grey line at 1 named "All-fallback" (BL0a's
label, as in sf_lag_v2 and the paper's Fig. 3) at its left end in (a); (c)'s x label names its axis, "Stranding price
(mu / beta~)", as (a)'s does (the quantity's name in sf_e3_mu, sf_e7_mu and the supplement's text); the two x labels
on one baseline (common.align_baselines) and each legend row's mathtext labels on its plain ones'
(common.align_legend_rows), since mathtext's PDF metrics set them up to 2 pt off; the panel titles at the
caption size (LABEL_PT) on the letters' baseline.

Tables (after hook, figs.common.write_table, from the extract's `tables`, so --from-extract rewrites them byte for byte;
longtables of ms5b_e7_lib):
  e5v2_costs.tex    per cell (level, menu, mu) Sublet's median saving over the all-fallback cost and its min-max over
                    the config seeds, and the median saving of every other policy; a dagger marks the medians of runs
                    reused from the confirmation (the analysis's by_tag.<tag>.source 'second');
  e5v2_margins.tex  per cell the margin of the cheaper of Greedy, back-off and RetroRenting-style per config seed minus
                    Sublet in r0 (percentage points of the all-fallback cost) and the same over every baseline of the
                    cell (with SpotHedge-style at N_Extra = 0 and 2 where they ran), each with its median, min-max and
                    the config seeds in which it is positive; the spares' effect, SpotHedge-style at N_Extra = 2 minus
                    at 0 in r0 (median and min-max; negative when the spares save); and Sublet minus critical-ratio
                    renting in r0 (median);
  e5v2_runs.csv     every per-run value: level, menu, mu, policy, tag, config seed, r0, saving and source.
Every policy is named by its registry label; no tag, file or design name is printed.

labels.caption is a caption draft for the integrator (the supplement part s_f3.tex), labels.values the counts and
values it reads from the inputs (candidate \\val entries); headline is the analysis's headline block, unchanged.

Run from code/sim: python -m figs.supp.sf_e5_v2 [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.ticker import FixedLocator, NullLocator
from matplotlib.transforms import blended_transform_factory

from figs import style
from figs.common import MissingKey, align_baselines, align_legend_rows, need, panel_title, thin_tick_labels, write_table
from figs.inputs import Inputs
from figs.supp import ms7_x3_lib as X
from figs.supp.ms4_lib import center_xlabel, log_axis_over

NAME = "sf_e5_v2"
ANALYSIS = "code/sim/out/e5v2/analysis.json"
SUMMARY = "code/sim/out/e5v2/summary.json"
RUN_INPUTS = (ANALYSIS, SUMMARY)
INPUTS = RUN_INPUTS
KEYS = style.SUPP_POLICIES_MS7[NAME]
TAGS = ("Sublet", "A9", "BL5-cur", "BL1-BO", "BL3-0", "BL3-2")      # in the order of KEYS
BASELINES = ("BL1-BO", "BL5-cur", "BL3-0", "BL3-2")                 # ms7_sens_analysis.E5_BASELINES
LEVELS = ("trace", "sh0.25", "sh0.5", "sh1", "all1")
MENUS = ("short", "long")
MU1 = "1"
STRAND = ("trace", "short")                                          # the stranding runs' cell
TABLES = ("e5v2_costs.tex", "e5v2_margins.tex", "e5v2_runs.csv")
RUNS_CSV = TABLES[-1]
style.register_supplementary(NAME, "W2", 2.5)
DODGE_CAT = 0.13                   # (a), (b): series i of n at its level + (i - (n - 1) / 2) * DODGE_CAT
DODGE_OCT = 0.07                   # (c): ... times 2 ** ((i - (n - 1) / 2) * DODGE_OCT) on the log mu axis
AXES_RATIOS = (1.25, 1.25, 1.0)
REF_LABEL_DX_PT, REF_LABEL_DY_PT = 2.0, 1.0     # the reference line's label: from the axes' left end, above the line
LEVEL_TICKS = {"trace": "Trace", "sh0.25": "0.25", "sh0.5": "0.5", "sh1": "1", "all1": "All"}
LEVEL_TEX = {"trace": "Trace lender", "sh0.25": r"$p_{\mathrm{sh}}=0.25$", "sh0.5": r"$p_{\mathrm{sh}}=0.5$",
             "sh1": r"$p_{\mathrm{sh}}=1$", "all1": "One group"}
MENU_WORDS = {"short": "short", "long": "long"}
LABELS = {"y": "Cost / all-fallback", "x_level": r"Reclaim correlation ($p_{\mathrm{sh}}$)",
          # C62: (c)'s axis named, as (a)'s and (b)'s (as built the ratio alone)
          "x_mu": r"Stranding price ($\mu/\tilde{\beta}$)",     # the quantity's name in sf_e3_mu, sf_e7_mu, the text
          "ref": "All-fallback",                  # C62: the grey line at 1, named once in (a) (BL0a's label)
          "titles": {"a": "Short-notice menu", "b": "Long-notice menu", "c": "Trace lender, short menu"},
          "caption": (
              "Redundancy under correlated reclaims on {seeds}: cost over the all-fallback cost (overflow "
              "accounting), the median over the config seeds with min--max bars. (a) The short-notice menu (notice "
              "{short} min) and (b) the long-notice menu (notice {long} min) at $\\mu=\\tilde{{\\beta}}$, against the "
              "correlation of reclaims: the trace lender (Trace); a reclaim at a lender is repeated at each other "
              "lender of its group, independently with probability $p_{{\\mathrm{{sh}}}}$ (0.25 to 1); one group of "
              "all lenders at $p_{{\\mathrm{{sh}}}}=1$ (All). (c) The trace lender with the short-notice menu against "
              "$\\mu/\\tilde{{\\beta}}$ (SpotHedge-style at $\\mu=\\tilde{{\\beta}}$ only). SpotHedge-style keeps "
              "$N_{{\\mathrm{{Extra}}}}$ spare replicas per pool. "
              "{sublet} costs less than both {bo} and {rr} in every config seed in {n_pair} of {n_cells} cells, and "
              "less than each baseline of the cell in {n_all}.")}


# ---------------------------------------------------------------------------------------------------------------
# data
def _cell(ana: Mapping, lv: str, menu: str, mk: str) -> Mapping | None:
    return ((ana.get("cells") or {}).get(lv) or {}).get(menu, {}).get(mk)


def series(ana: Mapping, keys_of: Sequence[tuple[str, str, str]], xs: Sequence[float]) -> dict:
    """{tag: {x, median, lo, hi}} over the cells `keys_of` ((level, menu, mu) per x): the analysis's median r0 and the
    min-max of its r0 over the config seeds; None where a cell has no run of the tag."""
    out = {}
    for t in TAGS:
        med, lo, hi = [], [], []
        for lv, mn, mk in keys_of:
            b = ((_cell(ana, lv, mn, mk) or {}).get("by_tag") or {}).get(t) or {}
            a, z = X.extent((b.get("r0") or {}).values())
            med.append(b.get("median_r0"))
            lo.append(a)
            hi.append(z)
        if any(v is not None for v in med):
            out[t] = {"x": list(xs), "median": med, "lo": lo, "hi": hi}
    return out


def cell_rows(ana: Mapping) -> list[dict]:
    """The tables' cells in the order of the panels: (a) and (b) by level, then (c)'s other mu."""
    order = [(lv, mn, MU1) for mn in MENUS for lv in LEVELS]
    order += sorted(((STRAND[0], STRAND[1], mk) for mk in ((ana.get("cells") or {}).get(STRAND[0]) or {})
                     .get(STRAND[1], {}) if mk != MU1), key=lambda c: float(c[2]))
    order += [(lv, mn, mk) for lv, a in (ana.get("cells") or {}).items() for mn, b in a.items() for mk in b
              if (lv, mn, mk) not in order]                  # any other cell of the analysis, in its order
    out = []
    for lv, mn, mk in order:
        e = _cell(ana, lv, mn, mk)
        if e is None:
            continue
        bt = e.get("by_tag") or {}
        sub = bt.get("Sublet") or {}
        lo, hi = X.extent((sub.get("saving_pct") or {}).values())

        def mrg(m):
            m = m or {}
            return {k: m.get(k) for k in ("delta_median", "delta_min", "delta_max", "weeks_hold", "n_weeks")} | {
                "loss_weeks": list(m.get("loss_weeks") or [])}
        sp = e.get("bl3_spares_r0") or {}
        spv = [v for v in (sp.get("by_week") or {}).values()]
        out.append({"level": lv, "menu": mn, "mu": mk,
                    "saving": {t: (bt.get(t) or {}).get("median_saving_pct") for t in TAGS},
                    "source": {t: (bt.get(t) or {}).get("source") for t in TAGS if t in bt},
                    "sublet_lo": lo, "sublet_hi": hi, "pair": mrg(e.get("vs_pair")),
                    "all": mrg(e.get("vs_baselines")), "baselines": list(e.get("baselines") or []),
                    "spares": {"median": sp.get("median"), "lo": X.extent(spv)[0], "hi": X.extent(spv)[1]} if sp else
                    None, "guard_r0": (e.get("sublet_minus_a9_r0") or {}).get("median")})
    return out


def runs_csv(ana: Mapping, levels_meta: Mapping) -> dict:
    cols = ("level", "p_sh", "groups", "menu", "mu_over_beta", "policy", "tag", "config_seed", "r0", "saving_pct",
            "source")
    rows = []
    for lv, a in (ana.get("cells") or {}).items():
        par = ((levels_meta.get(lv) or {}).get("params") or {})
        for mn, b in a.items():
            for mk, e in b.items():
                for t, x in (e.get("by_tag") or {}).items():
                    src = "confirmation, part second" if x.get("source") == "second" else "this study"
                    for c, v in (x.get("r0") or {}).items():
                        rows.append((lv, par.get("p_sh"), par.get("groups") or ("own" if par else None), mn,
                                     float(mk), X.plain(X.label_of(t)), t, c, v, (x.get("saving_pct") or {}).get(c),
                                     src))
    return X.csv_entry(RUNS_CSV, cols, rows)


def build(inp: Inputs) -> dict:
    ana = X.load(inp, ANALYSIS, script=NAME, run_inputs=RUN_INPUTS)
    summ = X.load(inp, SUMMARY, script=NAME, run_inputs=RUN_INPUTS)
    prov = X.provenance(ana, ANALYSIS)
    X.check_registered(prov, NAME)
    shas = X.check_input_shas(prov, inp, {"out/e5v2/summary.json": SUMMARY}, NAME)
    shas[ANALYSIS] = X.sha256_of(inp, ANALYSIS)
    meta = need(summ, "meta", what=SUMMARY)
    weeks = [str(w) for w in need(ana, "weeks", what=ANALYSIS)]
    lv_in = [lv for lv in LEVELS if lv in (ana.get("cells") or {})]
    if not lv_in:
        raise MissingKey(f"{ANALYSIS}: no cell of the levels {list(LEVELS)}")
    pos = {lv: float(i) for i, lv in enumerate(LEVELS)}
    panels = {}
    for p, mn in (("a", "short"), ("b", "long")):
        cells = [(lv, mn, MU1) for lv in LEVELS]
        panels[p] = {"levels": list(LEVELS), "x": [pos[lv] for lv in LEVELS],
                     "series": series(ana, cells, [pos[lv] for lv in LEVELS])}
    mus = sorted(((ana.get("cells") or {}).get(STRAND[0]) or {}).get(STRAND[1], {}), key=float)
    panels["c"] = {"mu": mus, "x": [float(m) for m in mus],
                   "series": series(ana, [(STRAND[0], STRAND[1], m) for m in mus], [float(m) for m in mus])}
    menus = meta.get("menus") or {}

    def notice(mn):
        hs = sorted({int(c["H_min"]) for c in (menus.get(mn) or {}).get("contracts") or []
                     if c.get("tau_min") is not None and c.get("H_min") is not None})
        return hs
    data = {"panels": panels, "weeks": weeks,
            "tables": {"cells": cell_rows(ana), "e5v2_runs": runs_csv(ana, meta.get("levels") or {})},
            "notice_min": {mn: notice(mn) for mn in MENUS}, "levels_meta": meta.get("levels"),
            "reused": meta.get("reused"), "headline": ana.get("headline"), "flips": ana.get("flips"),
            "meta": {"reduced": bool(prov["reduced"] or meta.get("reduced")),
                     "git_revision": {"analysis": prov["git_revision"], "summary": meta.get("git_revision")},
                     "analysis": prov, "inputs_sha256": shas, "horizon_min": (meta.get("grid") or {}).get(
                         "horizon_min")},
            "labels": {k: v for k, v in LABELS.items() if k != "caption"}}
    data["layout"] = layout(data)
    data["labels"]["values"] = values(data)
    data["labels"]["caption"] = caption(data)
    return data


def values(d: Mapping) -> dict:
    h = d.get("headline") or {}
    return {"seeds": X.week_list(d["weeks"]), "n_seeds": len(d["weeks"]), "n_cells": h.get("n_cells"),
            "n_pair_all_seeds": (h.get("vs_pair") or {}).get("cells_all_weeks_hold"),
            "n_baselines_all_seeds": (h.get("vs_baselines") or {}).get("cells_all_weeks_hold"),
            "sublet_saving_lo": h.get("sublet_saving_lo"), "sublet_saving_lo_cell": h.get("sublet_saving_lo_cell"),
            "sublet_saving_hi": h.get("sublet_saving_hi"), "sublet_saving_hi_cell": h.get("sublet_saving_hi_cell"),
            "notice_short_min": d["notice_min"]["short"], "notice_long_min": d["notice_min"]["long"],
            "spares_r0_median": h.get("bl3_spares_r0_median"),
            "cells_with_failures_pair": (h.get("vs_pair") or {}).get("cells_with_failures"),
            "cells_with_failures_baselines": (h.get("vs_baselines") or {}).get("cells_with_failures")}


def caption(d: Mapping) -> str:
    v = d["labels"]["values"]

    def mins(xs):
        xs = [str(x) for x in xs]
        return "--" if not xs else xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " or " + xs[-1]
    return LABELS["caption"].format(seeds=X.weeks_text(d["weeks"], "config seed"), short=mins(v["notice_short_min"]),
                                    long=mins(v["notice_long_min"]), sublet=style.POLICIES["sublet_v2"].label,
                                    bo=style.POLICIES["bl1_bo"].label, rr=style.POLICIES["bl5_cur"].label,
                                    n_pair=v["n_pair_all_seeds"], n_cells=v["n_cells"],
                                    n_all=v["n_baselines_all_seeds"])


# ---------------------------------------------------------------------------------------------------------------
# layout and drawing
def _vals(s: Mapping) -> list[float]:
    return [float(v) for k in ("median", "lo", "hi") for v in s[k] if v is not None and v > 0]


def layout(data: Mapping) -> dict:
    """Each panel's y range (the data's, log ticks of ms4_lib) and x positions of the dodged series."""
    out = {}
    for p, pan in data["panels"].items():
        vals = [v for s in pan["series"].values() for v in _vals(s)] + [1.0]
        out[p] = {"y": [min(vals), max(vals)]}
    return out


def _dodged(p: str, xs: Sequence[float], i: int, n: int) -> np.ndarray:
    x = np.asarray(xs, dtype=float)
    k = i - (n - 1) / 2.0
    return x * 2.0 ** (DODGE_OCT * k) if p == "c" else x + DODGE_CAT * k


def draw_panel(ax, p: str, pan: Mapping, lay: Mapping) -> None:
    keys = [t for t in TAGS if t in pan["series"]]
    n = len(TAGS)
    style.reference_line(ax, y=1.0)
    for t in keys:
        i = TAGS.index(t)
        k = X.key_of(t)
        s = pan["series"][t]
        ok = [j for j, v in enumerate(s["median"]) if v is not None]
        x = _dodged(p, s["x"], i, n)
        y = [np.nan if v is None else float(v) for v in s["median"]]      # a missing cell breaks the line
        style.plot_policy(ax, k, x, y)
        bars = [j for j in ok if s["lo"][j] is not None and s["hi"][j] is not None]
        if bars:
            style.errorbars(ax, k, _dodged(p, [s["x"][j] for j in bars], i, n), [s["median"][j] for j in bars],
                            [s["lo"][j] for j in bars], [s["hi"][j] for j in bars])
    lo, hi = lay["y"]
    log_axis_over(ax, "y", lo, hi)
    if p == "c":
        ax.set_xscale("log")
        xs = pan["x"]
        ax.xaxis.set_major_locator(FixedLocator(xs))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.xaxis.set_major_formatter(style.PLAIN)
        ax.set_xlim(min(xs) / 1.35, max(xs) * 1.35)
    else:
        ax.set_xticks(pan["x"], [LEVEL_TICKS[lv] for lv in pan["levels"]])
        ax.set_xlim(pan["x"][0] - 0.5, pan["x"][-1] + 0.5)
    thin_tick_labels(ax)


def ref_label(ax, text: str) -> Any:
    """The grey line at 1 named at its left end, just above it (THEORY_LABEL_GREY, TICK_PT; C62): (a)'s Trace column
    has no series near 1."""
    tr = blended_transform_factory(ax.transAxes, ax.transData)
    t = ax.annotate(text, xy=(0.0, 1.0), xycoords=tr, xytext=(REF_LABEL_DX_PT, REF_LABEL_DY_PT),
                    textcoords="offset points", ha="left", va="bottom", fontsize=style.TICK_PT,
                    color=style.THEORY_LABEL_GREY, zorder=style.Z_THEORY_LABEL)
    t._sublet_role = "reference_label"
    return t


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    axes = style.panel_row(fig, AXES_RATIOS, legend=2)
    leg = style.legend_row(fig, KEYS, rows=2)
    for ax, p in zip(axes, ("a", "b", "c")):
        draw_panel(ax, p, data["panels"][p], data["layout"][p])
        ax.set_ylabel(lab["y"])
    if lab.get("ref"):
        ref_label(axes[0], lab["ref"])
    center_xlabel(axes[:2], lab["x_level"])
    axes[2].set_xlabel(lab["x_mu"])
    letters = style.panel_letters(axes)
    for ax, letter, p in zip(axes, letters, ("a", "b", "c")):     # C62: at the caption size, on the letters' baseline
        panel_title(ax, letter, lab["titles"][p], fontsize=style.LABEL_PT)
    # C62: the two x labels on one baseline, and each legend row's mathtext labels on its plain ones' (mathtext's PDF
    # metrics set (c)'s label 2.0 pt and the SpotHedge-style labels 0.9 and 0.6 pt off)
    align_baselines([axes[0].xaxis.label, axes[2].xaxis.label])
    align_legend_rows(leg, 2)
    fig._sublet_axes = dict(zip(("a", "b", "c"), axes))
    return fig


# ---------------------------------------------------------------------------------------------------------------
# tables
def _group_key(r: Mapping) -> tuple:
    """A table's row group: (a)'s and (b)'s cells by menu at mu = beta~, then (c)'s other mu together (review: one
    group per mu split three single rows)."""
    return (r["menu"], r["mu"] == MU1)


def _groups(t: Sequence[Mapping]) -> list[int]:
    return [i for i in range(1, len(t)) if _group_key(t[i]) != _group_key(t[i - 1])]


def _cell_text(r: Mapping) -> list[str]:
    return [LEVEL_TEX.get(r["level"], X.tex(r["level"])), MENU_WORDS.get(r["menu"], r["menu"]), X.num(float(r["mu"]),
                                                                                                    "g")]


def _mark(r: Mapping, t: str) -> str:
    v = X.pct(r["saving"].get(t))
    return v + (r"$^\dagger$" if r["source"].get(t) == "second" and v != "--" else "")


def costs_tex(t: Sequence[Mapping], d: Mapping) -> str:
    rows = [_cell_text(r) + [_mark(r, "Sublet"), X.span(r["sublet_lo"], r["sublet_hi"])]
            + [_mark(r, x) for x in TAGS[1:]] for r in t]
    groups = _groups(t)
    lab = {x: X.tex(style.POLICIES[X.key_of(x)].label) for x in TAGS}
    cap = (r"Redundancy under correlated reclaims per cell on " + X.weeks_text(d["weeks"], "config seed") + r": the "
           r"saving over the all-fallback cost in overflow accounting, the median over the config seeds and, for "
           r"Sublet, its range. Lender: the trace lender, correlated reclaims within the lenders' groups at "
           r"$p_{\mathrm{sh}}$, or one group of all lenders at $p_{\mathrm{sh}}=1$; the stranding runs at "
           r"$\mu\neq\tilde{\beta}$ are the four policies' with the trace lender and the short-notice menu. "
           r"$^\dagger$: the confirmation's runs, reused. Every run is in the data file "
           + RUNS_CSV.replace("_", r"\_") + ".")
    head_top = (r" & & & \multicolumn{" + str(len(TAGS) + 1) + r"}{c}{Saving (\%)} \\" "\n"
                r"\cmidrule(lr){4-" + str(len(TAGS) + 4) + "}")
    header = ["Lender", "Menu", r"$\mu/\tilde{\beta}$", r"\shortstack{Sublet\\median}", r"\shortstack{Sublet\\range}",
              r"\shortstack{Critical-ratio\\renting}", r"\shortstack{RetroRenting-\\style}",
              r"\shortstack{Greedy,\\back-off}", r"\shortstack{SpotHedge-style,\\$N_{\mathrm{Extra}}=0$}",
              r"\shortstack{SpotHedge-style,\\$N_{\mathrm{Extra}}=2$ per pool}"]
    del lab
    return X.longtable("@{}lll" + "r" * (len(TAGS) + 1) + "@{}", cap, "tab:s-e5v2-costs", header, rows, groups=groups,
                       tabcolsep="3.0pt", head_top=head_top)


def _weeks(m: Mapping) -> str:
    return "--" if m.get("n_weeks") is None else X.count_text(m.get("weeks_hold") or 0, m["n_weeks"])


def margins_tex(t: Sequence[Mapping], d: Mapping) -> str:
    rows = []
    for r in t:
        sp = r["spares"] or {}
        rows.append(_cell_text(r) + [X.pp(r["pair"]["delta_median"]),
                                     X.span(r["pair"]["delta_min"], r["pair"]["delta_max"], scale=100.0),
                                     _weeks(r["pair"]), X.pp(r["all"]["delta_median"]),
                                     X.span(r["all"]["delta_min"], r["all"]["delta_max"], scale=100.0),
                                     _weeks(r["all"]), X.pp(sp.get("median")),
                                     X.span(sp.get("lo"), sp.get("hi"), scale=100.0), X.pp(r["guard_r0"])])
    groups = _groups(t)
    lab = {x: X.tex(style.POLICIES[X.key_of(x)].label) for x in TAGS}
    cap = (r"Margins of Sublet per cell on " + X.weeks_text(d["weeks"], "config seed") + r", in percentage points of "
           r"the all-fallback cost (overflow accounting): the cost of " + lab["BL1-BO"] + r" or " + lab["BL5-cur"]
           + r", whichever is lower in the config seed, minus Sublet's, and the same over every baseline of the cell "
           r"(with SpotHedge-style at $N_{\mathrm{Extra}}=0$ and $2$ where they ran), each with its median, range "
           r"and the config seeds in which it is positive (a missing run counts as not); the spares' effect, "
           r"SpotHedge-style at $N_{\mathrm{Extra}}=2$ per pool minus at $N_{\mathrm{Extra}}=0$ (negative when the "
           r"spares save); and the price of the guard, Sublet minus " + lab["A9"].lower() + r" (median).")
    head_top = (r" & & & \multicolumn{3}{c}{Margin, two baselines} & \multicolumn{3}{c}{Margin, every baseline} & "
                r"\multicolumn{2}{c}{Spares} & \\" "\n" r"\cmidrule(lr){4-6}\cmidrule(lr){7-9}\cmidrule(lr){10-11}")
    header = ["Lender", "Menu", r"$\mu/\tilde{\beta}$", "Median", "Range", "Seeds", "Median", "Range", "Seeds",
              "Median", "Range", "Guard"]
    return X.longtable("@{}lll" + "r" * 9 + "@{}", cap, "tab:s-e5v2-margins", header, rows, groups=groups,
                       tabcolsep="3.0pt", head_top=head_top)


def write_tables(data: Mapping, report: Mapping) -> None:
    t = data["tables"]
    paths = [write_table(TABLES[0], X.table_head(NAME, [ANALYSIS]) + costs_tex(t["cells"], data)),
             write_table(TABLES[1], X.table_head(NAME, [ANALYSIS]) + margins_tex(t["cells"], data)),
             X.write_csv(t["e5v2_runs"], NAME)]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    return X.run(NAME, build, draw, argv, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
