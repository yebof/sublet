"""sf_e9_v2: Sublet's time per slot against instance size, the guard's overhead over critical-ratio renting and its
split, and the tables e9v2_overhead.tex and e9v2_split.tex with the data file e9v2_runs.csv (design/ms7/w_spec.md §4,
unit W-G4, writer C; design/ms7/registration.md §2-§3, X3, E9 v2; change C58).

Question: what does the guard add to the time Sublet takes per slow-loop slot as the instance grows, and which of its
parts takes that time?

Inputs (RUN_INPUTS, the MS7 run outputs; a missing one stops the build with exit code 2 and the file named; figs/
rebuild.py keeps the entry pending until they are copied in): the registered analysis code/sim/out/e9v2/analysis.json
(sublet/experiments/ms7_sens_analysis.py, frozen by its sha256: the act times per slow slot of Sublet and critical-ratio
renting per point and alignment, the overhead and ratio with their medians, and the split of the guard's time where
the instrumented run equals the uninstrumented one) and the summary it read, code/sim/out/e9v2/summary.json (each
point's sites, LLMs and contracts, the loops per simulated hour, peak memory and the slot length; checked against the
sha256 that the analysis recorded). A non-reduced analysis must be the registered one on full runs. Each job ran alone
on the host (design/ms7/registration.md §4). Descriptive statistics (medians and min-max over the alignments); no
p-value.

Figure (W2 x 2.2 in, the size of sf_e9). Three panels side by side, log-log, x "Sites x LLMs" over one common range:
(a) the full menu and (b) the reduced menu (the points with the three-LLM set, ordered by sites x LLMs): per policy
the median over the alignments of its act time per slow-loop slot (the analysis's by_alignment.<c>.act_s_per_slot)
as a line with markers in the registry style, the min-max over the alignments as 0.6-pt bars; (b) shares (a)'s y axis.
(c) The guard's time per slot on the full menu (the analysis's split.per_slot_mean_s of the points whose split is
identical to the uninstrumented run; one alignment): the guard in total (Sublet's act time minus that of its inner
policy, in the run) and its parts (the safe expert's step, the online lower bound, the guard's test, the projection,
the rest) as black and grey lines with markers of their own (PARTS), the total drawn last so that it stays on top of
the safe expert's open markers just below it, each named at its right end (labels stacked so that they do not
overlap, LABEL_GAP_PT clear of the end marker; in the parts' grey darkened to 4.5:1 against white). The points with
other LLM sets (e7f V8 S and ML) are in the tables only, as in sf_e9. Keys (C62; layout.keys): Sublet and
critical-ratio renting named next to their lines in (a) (series_labels, on the free space nearest each line and nearer
to it than to the other), so that the panels take the legend row's height; where a name fits nowhere there (a probe
draw in build), a legend row above (a) and (b), as built. The parts' names in sentence case and the panel titles at the
caption size (LABEL_PT) on the letters' baseline (C62).

Tables (after hook, figs.common.write_table, from the extract's `tables`, so --from-extract rewrites them byte for byte;
longtables of ms5b_e7_lib):
  e9v2_overhead.tex  per point: menu, V, LLMs, sites x LLMs, the act time per slot (ms, three significant digits,
                     _ms3) of Sublet and critical-ratio renting (median and min-max over the alignments), the overhead
                     Sublet minus critical-ratio renting (median, min-max) and their ratio (median), the loops per
                     simulated hour (s) and the peak memory (MB) of each (medians);
  e9v2_split.tex     per point with a split run: its alignment, whether it equals the uninstrumented run, and the mean
                     time per slot (ms) of Sublet's act, the inner policy, the guard and its parts;
  e9v2_runs.csv      every run: point, policy, alignment, act time per slot, slow step per slot, loops per simulated
                     hour, peak memory, projected slots; and the split's parts on its run's line.
Every policy is named by its registry label; no tag, file or design name is printed.

labels.caption is a caption draft for the integrator (the supplement part s_f3.tex), labels.values the counts and
values it reads from the inputs (candidate \\val entries); headline is the analysis's headline block, unchanged.

Run from code/sim: python -m figs.supp.sf_e9_v2 [--from-extract [JSON]].
"""
from __future__ import annotations

import math
import re
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.ticker import FixedLocator, NullLocator

from figs import style
from figs.common import (MissingKey, _top_tick_room, need, panel_title, place_label, points_pt, stack_labels,
                         text_width_in, thin_tick_labels, write_table)
from figs.inputs import Inputs
from figs.supp import ms7_x3_lib as X
from figs.supp.ms4_lib import LOG_PAD, log_axis_over, log_ticks

NAME = "sf_e9_v2"
ANALYSIS = "code/sim/out/e9v2/analysis.json"
SUMMARY = "code/sim/out/e9v2/summary.json"
RUN_INPUTS = (ANALYSIS, SUMMARY)
INPUTS = RUN_INPUTS
KEYS = style.SUPP_POLICIES_MS7[NAME]
TAGS = ("Sublet", "A9")
MENUS = {"e7f": "full", "e7r": "reduced"}
LLM_SET = "SML"                    # the panels' LLM set; the others are in the tables only (sf_e9's M26)
POINT_RE = re.compile(r"^(e7[fr])_V(\d+)_([A-Z]+)$")
TABLES = ("e9v2_overhead.tex", "e9v2_split.tex", "e9v2_runs.csv")
RUNS_CSV = TABLES[-1]
style.register_supplementary(NAME, "W2", 2.2)
# (c): the guard's parts, drawn in this order, each as (label, color, marker, fill); C62: the labels in sentence case,
# as (a)'s policy names beside them and the split table's columns (as built lower case)
PARTS = {"guard": ("Guard, total", "#000000", "o", "filled"),
         "safe": ("Safe expert", "#4D4D4D", "s", "open"),
         "test": ("Test", "#4D4D4D", "^", "filled"),
         "projection": ("Projection", "#7F7F7F", "D", "open"),
         "lb": ("Lower bound", "#7F7F7F", "v", "filled"),
         "other": ("Rest", "#7F7F7F", "x", "line")}
SPLIT_KEYS = ("act", "inner_act", "guard", "safe", "lb", "test", "projection", "other")
X_LADDER = (1.0, 2.0, 5.0)
X_LO_FACTOR, X_HI_FACTOR = 0.75, 1.2          # sf_e9's x range rule
# (c)'s y margin, a factor beyond its lowest and highest part: LOG_PAD's 0.05 decade (about 1 pt on (c)'s nearly six
# decades) cut the markers at both ends in half (MS7 print check, 2026-11-11); 0.3 decade clears half a marker
C_PAD = 2.0
MS = 1000.0                                   # the figure's times in ms (the extract keeps seconds)
LABEL_GAP_PT = 4.5                            # (c): a part's name this far right of its line's end (review: clear
                                              # of the end marker, MARKER_PT / 2 and its edge, by about 2.5 pt)
AXES_RATIOS = (1.0, 1.0, 1.0)
LINE_SAMPLE_PT = 2.0                          # C62: a series line sampled this densely for its direct label's place
LABELS = {"x": "Sites × LLMs", "y": "Time per slot (ms)", "c_y": "Time per slot (ms)",
          "titles": {"a": "Full menu", "b": "Reduced menu", "c": "Guard's parts, full menu"},
          "caption": (
              "Time per slow-loop slot of {sublet} and {cr} (its inner policy) against sites $\\times$ LLMs, each job "
              "alone on the host: (a) the full and (b) the reduced menu, the median over {n_al} of a day "
              "with min--max bars; (c) the guard's time per slot on the full menu in one alignment, in total and by "
              "part: the safe expert's step, the online lower bound, the guard's test, the projection and the rest. A "
              "slow-loop slot is {slot_s:g} s. The guard's overhead, {sublet}'s time minus {cr}'s, is at most "
              "{ov_max_ms:.3g} ms per slot (median over the alignments, at {ov_max_point_text}).")}


# ---------------------------------------------------------------------------------------------------------------
# data
def point_info(name: str, summ_pt: Mapping) -> dict:
    m = POINT_RE.match(name)
    base, v, llms = (m.group(1), int(m.group(2)), m.group(3)) if m else (None, None, None)
    return {"point": name, "menu": MENUS.get(base), "V": v, "llms": llms,
            **{k: summ_pt.get(k) for k in ("n_sites", "n_llms", "n_contracts", "sites_x_llms", "n_units")}}


def _act(a_pt: Mapping, tag: str) -> list:
    return [((v.get("act_s_per_slot") or {}).get(tag)) for v in (a_pt.get("by_alignment") or {}).values()]


def series(ana: Mapping, summ: Mapping, base: str) -> dict:
    """Per tag the points of `base` with the LLM set LLM_SET in the order of sites x LLMs: x, the median and min-max
    of its act time per slot over the alignments."""
    pts = [(p, e) for p, e in (ana.get("points") or {}).items() if (POINT_RE.match(p) or [None, None])[1] == base
           and p.endswith("_" + LLM_SET) and e.get("sites_x_llms")]
    pts.sort(key=lambda pe: float(pe[1]["sites_x_llms"]))
    out = {"points": [p for p, _ in pts], "x": [float(e["sites_x_llms"]) for _, e in pts], "series": {}}
    for t in TAGS:
        vals = [_act(e, t) for _, e in pts]
        out["series"][t] = {"median": [X.median(v) for v in vals], "lo": [X.extent(v)[0] for v in vals],
                            "hi": [X.extent(v)[1] for v in vals]}
    return out


def split_series(ana: Mapping) -> dict:
    """(c): the full menu's LLM_SET points with an identical split, x and the parts' mean time per slot."""
    pts = [(p, e) for p, e in (ana.get("points") or {}).items() if (POINT_RE.match(p) or [None, None])[1] == "e7f"
           and p.endswith("_" + LLM_SET) and e.get("sites_x_llms")]
    pts.sort(key=lambda pe: float(pe[1]["sites_x_llms"]))
    out = {"points": [], "x": [], "parts": {k: [] for k in PARTS}}
    for p, e in pts:
        sp = e.get("split") or {}
        ps = sp.get("per_slot_mean_s") if sp.get("identical") is True else None
        if not ps:
            continue
        out["points"].append(p)
        out["x"].append(float(e["sites_x_llms"]))
        for k in PARTS:
            out["parts"][k].append(ps.get(k))
    return out


def slot_seconds(summ: Mapping) -> float | None:
    """The slow-loop slot (s) of the runs: hours x 3600 / n_slow_steps, the median over the runs that report both."""
    v = []
    for e in (summ.get("points") or {}).values():
        for pol in (e.get("policies") or {}).values():
            for r in (pol.get("by_alignment") or {}).values():
                if r.get("hours") and r.get("n_slow_steps"):
                    v.append(float(r["hours"]) * 3600.0 / float(r["n_slow_steps"]))
    return X.median(v)


def overhead_rows(ana: Mapping, summ: Mapping) -> list[dict]:
    out = []
    for p, e in (ana.get("points") or {}).items():
        se = (summ.get("points") or {}).get(p) or {}
        info = point_info(p, se)
        by = e.get("by_alignment") or {}
        ov = [v.get("act_overhead_s_per_slot") for v in by.values()]
        pol = se.get("policies") or {}
        out.append({**info, "n_alignments": len(by),
                    "act": {t: {"median": X.median(_act(e, t)), "lo": X.extent(_act(e, t))[0],
                                "hi": X.extent(_act(e, t))[1]} for t in TAGS},
                    "overhead": {"median": e.get("act_overhead_s_per_slot_median"), "lo": X.extent(ov)[0],
                                 "hi": X.extent(ov)[1]}, "ratio_median": e.get("act_ratio_median"),
                    "loops_s_per_h": {t: ((pol.get(t) or {}).get("median") or {}).get("loops_s_per_h") for t in TAGS},
                    "peak_rss_mb": {t: ((pol.get(t) or {}).get("median") or {}).get("peak_rss_mb") for t in TAGS}})
    out.sort(key=lambda r: (list(MENUS.values()).index(r["menu"]) if r["menu"] in MENUS.values() else 9,
                            r["V"] or 0, r["llms"] != LLM_SET, r["llms"] or ""))
    return out


def split_rows(ana: Mapping, summ: Mapping) -> list[dict]:
    out = []
    for r in overhead_rows(ana, summ):
        sp = (ana["points"][r["point"]].get("split")) or {}
        if not sp:
            continue
        out.append({**{k: r[k] for k in ("point", "menu", "V", "llms", "sites_x_llms")}, "alignment": sp.get("c"),
                    "identical": sp.get("identical"),
                    "per_slot_mean_s": {k: (sp.get("per_slot_mean_s") or {}).get(k) for k in SPLIT_KEYS}})
    return out


def runs_csv(ana: Mapping, summ: Mapping) -> dict:
    cols = ("point", "menu", "V", "llm_set", "sites_x_llms", "policy", "tag", "alignment", "act_s_per_slot",
            "slow_step_s_per_slot", "slow_loop_s_per_h", "fast_loop_s_per_h", "loops_s_per_h", "peak_rss_mb",
            "projected_slots", "split_identical") + tuple(f"split_{k}_s_per_slot" for k in SPLIT_KEYS)
    rows = []
    for p, e in (ana.get("points") or {}).items():
        se = (summ.get("points") or {}).get(p) or {}
        info = point_info(p, se)
        sp = e.get("split") or {}
        for c, v in (e.get("by_alignment") or {}).items():
            for t in TAGS:
                run = (((se.get("policies") or {}).get(t) or {}).get("by_alignment") or {}).get(c) or {}
                on_split = t == "Sublet" and sp and str(sp.get("c")) == str(c)
                parts = [((sp.get("per_slot_mean_s") or {}).get(k) if on_split else None) for k in SPLIT_KEYS]
                rows.append((p, info["menu"], info["V"], info["llms"], info["sites_x_llms"], X.plain(X.label_of(t)), t,
                             int(c), (v.get("act_s_per_slot") or {}).get(t),
                             (v.get("slow_step_s_per_slot") or {}).get(t),
                             (v.get("slow_loop_s_per_h") or {}).get(t), run.get("fast_loop_s_per_h"),
                             run.get("loops_s_per_h"), run.get("peak_rss_mb"),
                             v.get("projected_slots") if t == "Sublet" else None,
                             sp.get("identical") if on_split else None, *parts))
    return X.csv_entry(RUNS_CSV, cols, rows)


def build(inp: Inputs) -> dict:
    ana = X.load(inp, ANALYSIS, script=NAME, run_inputs=RUN_INPUTS)
    summ = X.load(inp, SUMMARY, script=NAME, run_inputs=RUN_INPUTS)
    prov = X.provenance(ana, ANALYSIS)
    X.check_registered(prov, NAME)
    shas = X.check_input_shas(prov, inp, {"out/e9v2/summary.json": SUMMARY}, NAME)
    shas[ANALYSIS] = X.sha256_of(inp, ANALYSIS)
    meta = need(summ, "meta", what=SUMMARY)
    if not ana.get("points"):
        raise MissingKey(f"{ANALYSIS}: no points")
    data = {"panels": {"a": series(ana, summ, "e7f"), "b": series(ana, summ, "e7r"), "c": split_series(ana)},
            "slot_s": slot_seconds(summ), "alignments": list((meta.get("grid") or {}).get("alignments") or []),
            "tables": {"overhead": overhead_rows(ana, summ), "split": split_rows(ana, summ),
                       "e9v2_runs": runs_csv(ana, summ)},
            "headline": ana.get("headline"),
            "meta": {"reduced": bool(prov["reduced"] or meta.get("reduced")),
                     "git_revision": {"analysis": prov["git_revision"], "summary": meta.get("git_revision")},
                     "analysis": prov, "inputs_sha256": shas, "horizon_min": (meta.get("grid") or {}).get(
                         "horizon_min")},
            "labels": {k: v for k, v in LABELS.items() if k != "caption"}}
    data["labels"]["parts"] = {k: v[0] for k, v in PARTS.items()}
    data["labels"]["series"] = {t: X.label_of(t) for t in TAGS}          # C62: (a)'s direct labels
    data["layout"] = layout(data)
    data["layout"]["keys"] = keys_mode(data)
    data["labels"]["values"] = values(data)
    data["labels"]["caption"] = caption(data)
    return data


def values(d: Mapping) -> dict:
    """The counts and values that the caption and the integrator's text read from the inputs: the analysis's headline
    (the largest overhead per slot is its act_overhead_s_per_slot_max, at its point), the slot length and Sublet's
    largest time per slot over every run with its share of the slot."""
    h = d.get("headline") or {}
    pmax = h.get("act_overhead_s_per_slot_max_point")
    r = next((r for r in d["tables"]["overhead"] if r["point"] == pmax), None)
    acts = [x["act"]["Sublet"]["hi"] for x in d["tables"]["overhead"] if x["act"]["Sublet"]["hi"] is not None]
    return {"n_alignments": len(d["alignments"]), "slot_s": d["slot_s"],
            "overhead_max_s": h.get("act_overhead_s_per_slot_max"), "overhead_max_point": pmax,
            "overhead_max_point_text": None if r is None else (f"the {r['menu']} menu at $V={r['V']}$ with LLM tiers "
                                                               f"{llm_text(r['llms'])}"),
            "sublet_act_max_s": max(acts) if acts else None,
            "sublet_act_max_share_of_slot": (max(acts) / d["slot_s"]) if acts and d["slot_s"] else None,
            "act_ratio_max": h.get("act_ratio_max"), "act_ratio_max_point": h.get("act_ratio_max_point"),
            "peak_rss_mb_max": h.get("peak_rss_mb_max"), "cap_mb": h.get("cap_mb"), "n_over_cap": h.get("n_over_cap"),
            "n_runs": h.get("n_runs"),
            "n_split_identical": sum(1 for x in d["tables"]["split"] if x["identical"] is True),
            "n_split": len(d["tables"]["split"]), "largest_point_by_menu": h.get("largest_point_by_menu")}


def caption(d: Mapping) -> str:
    v = d["labels"]["values"]
    n_al = f"{v['n_alignments']} alignment{'' if v['n_alignments'] == 1 else 's'}"
    return LABELS["caption"].format(sublet=style.POLICIES["sublet_v2"].label, cr=style.POLICIES["a9"].label.lower(),
                                    n_al=n_al, slot_s=v["slot_s"] or 0.0,
                                    ov_max_ms=1000.0 * (v["overhead_max_s"] or 0.0),
                                    ov_max_point_text=v["overhead_max_point_text"] or "--")


# ---------------------------------------------------------------------------------------------------------------
# layout and drawing
def _ladder_floor(v: float) -> float:
    e = math.floor(math.log10(v))
    return max(m * 10.0 ** e for m in X_LADDER if m * 10.0 ** e <= v) if any(
        m * 10.0 ** e <= v for m in X_LADDER) else 10.0 ** (e - 1) * X_LADDER[-1]


def _ladder_ceil(v: float) -> float:
    e = math.floor(math.log10(v))
    for m in X_LADDER + (10.0,):
        if m * 10.0 ** e >= v:
            return m * 10.0 ** e
    return 10.0 ** (e + 1)


def layout(data: Mapping) -> dict:
    """The common x range (sf_e9's rule) and the data's y extents in ms, of (a) and (b) together and of (c); the axes
    extend these by ms4_lib's LOG_PAD (log_axis_over), and (c)'s part names are stacked at draw time on that axis."""
    xs = [x for p in ("a", "b", "c") for x in data["panels"][p]["x"]]
    if not xs:
        raise MissingKey(f"{ANALYSIS}: no point of the LLM set {LLM_SET} with sites x LLMs")
    x_range = [_ladder_floor(X_LO_FACTOR * min(xs)), _ladder_ceil(X_HI_FACTOR * max(xs))]
    ab = [v for p in ("a", "b") for s in data["panels"][p]["series"].values() for k in ("median", "lo", "hi")
          for v in s[k] if v is not None and v > 0]
    cc = [v for vs in data["panels"]["c"]["parts"].values() for v in vs if v is not None and v > 0]
    if not ab:
        raise MissingKey(f"{ANALYSIS}: no act time per slot of the LLM set {LLM_SET}")
    return {"x_range": x_range, "y_ab": [MS * min(ab), MS * max(ab)],
            "y_c": [MS * min(cc), MS * max(cc)] if cc else None,
            "c_parts": [k for k in PARTS if any(v is not None and v > 0 for v in data["panels"]["c"]["parts"][k])]}


X_TICK_LADDER = (1.0, 3.0)                    # x ticks 1, 3 per decade (sf_e9's 100, 300, 1,000, 3,000)


def x_ticks(a: float, b: float) -> list[float]:
    e0, e1 = math.floor(math.log10(a)), math.ceil(math.log10(b))
    return [m * 10.0 ** e for e in range(e0, e1 + 1) for m in X_TICK_LADDER if a <= m * 10.0 ** e <= b]


def _x_axis(ax, lay: Mapping) -> None:
    a, b = lay["x_range"]
    ax.set_xscale("log")
    ax.set_xlim(a, b)
    ax.xaxis.set_major_locator(FixedLocator(x_ticks(a, b)))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(style.PLAIN)


def y_ticks(rng, pad: float = LOG_PAD) -> list[float]:
    return log_ticks(rng[0] / pad, rng[1] * pad)


def draw_policy_panel(ax, pan: Mapping, lay: Mapping, *, y_axis: bool) -> None:
    for t in reversed(TAGS):                       # Sublet last (on top)
        s = pan["series"][t]
        k = X.key_of(t)
        y = [np.nan if v is None else MS * float(v) for v in s["median"]]
        if any(v is not None for v in s["median"]):
            style.plot_policy(ax, k, pan["x"], y)
        ok = [i for i, v in enumerate(s["median"]) if v is not None and s["lo"][i] is not None]
        if ok:
            style.errorbars(ax, k, [pan["x"][i] for i in ok], [MS * s["median"][i] for i in ok],
                            [MS * s["lo"][i] for i in ok], [MS * s["hi"][i] for i in ok])
    _x_axis(ax, lay)
    if y_axis:
        log_axis_over(ax, "y", *lay["y_ab"])
        # C62: the top decade's label TOP_TICK_GAP_PT below the axes top, clear of the panel title above it (sf_e9's
        # rule; the 10,000 of (a) came within 1.9 pt)
        _top_tick_room(ax)
    thin_tick_labels(ax)


def draw_parts(ax, c: Mapping, lay: Mapping, lab: Mapping) -> None:
    """(c): the guard's parts as lines with markers, each named right of its last point; the names stacked in points
    (common.stack_labels) so that no two overlap and all stay within the axes' height."""
    ends = []
    # review: drawn in reverse so that the total is on top: it lies just above the safe expert's step, whose open
    # (white-faced) markers hid it when drawn after it
    for k in reversed(lay["c_parts"]):
        _name, color, marker, fill = PARTS[k]
        vs = c["parts"][k]
        y = [np.nan if v is None or v <= 0 else MS * float(v) for v in vs]
        face = "white" if fill == "open" else color
        ln, = ax.plot(c["x"], y, color=color, linewidth=style.LINE_PT, marker=marker, markersize=style.MARKER_PT,
                      markeredgewidth=style.MARKER_EDGE_PT, markeredgecolor=color, markerfacecolor=face,
                      zorder=style.Z_DATA)
        ln._sublet_part = k
        last = max(i for i, v in enumerate(y) if not math.isnan(v))
        ends.append((k, c["x"][last], y[last]))
    ends.reverse()                                   # the labels in PARTS' order, as before
    _x_axis(ax, lay)
    if lay["y_c"]:
        log_axis_over(ax, "y", *lay["y_c"], pad=C_PAD)
    thin_tick_labels(ax)
    if not ends:
        return
    tr = ax.transData
    dpi = ax.figure.dpi
    y0 = ax.transAxes.transform((0.0, 0.0))[1]
    h_pt = (ax.transAxes.transform((0.0, 1.0))[1] - y0) / dpi * style.BP_PER_IN
    tgt = [(tr.transform((x, v))[1] - y0) / dpi * style.BP_PER_IN for _k, x, v in ends]
    height = 1.15 * style.TICK_PT
    pos = stack_labels(tgt, [height] * len(ends), gap=0.3, bottom=0.5 * height, top=h_pt - 0.5 * height)
    for (k, x, v), p, t0 in zip(ends, pos, tgt):
        t = ax.annotate(lab["parts"][k], xy=(x, v), xytext=(LABEL_GAP_PT, p - t0), textcoords="offset points",
                        ha="left", va="center", fontsize=style.TICK_PT, annotation_clip=False,
                        color=style.readable_on_white(PARTS[k][1]))      # C62: the light grey at 4.5:1 as text
        t._sublet_role = "part_label"
        t._sublet_part = k


def _line_pt(ax, x, y_ms) -> np.ndarray:
    """Points every LINE_SAMPLE_PT or less along a series' drawn segments (display pt, n x 2; not across a gap)."""
    p = points_pt(ax, x, y_ms)
    out = [p]
    for a, b in zip(p[:-1], p[1:]):
        n = max(int(np.hypot(*(b - a)) / LINE_SAMPLE_PT), 1) + 1
        out.append(np.linspace(a, b, n))
    return np.concatenate(out) if len(p) else p


def series_labels(ax, pan: Mapping, lab: Mapping) -> list:
    """C62: Sublet and critical-ratio renting named next to their lines in (a), in place of the legend row: each label
    (TICK_PT, its policy's label color) on the free space nearest to its own line and nearer to it than to the other
    line (common.place_label), without a halo (on white). Returns the labels drawn (None where one fits nowhere)."""
    lines = {t: _line_pt(ax, pan["x"], [np.nan if v is None else MS * float(v) for v in pan["series"][t]["median"]])
             for t in TAGS}
    out = []
    for t in TAGS:
        other = np.concatenate([lines[u] for u in TAGS if u != t])
        k = X.key_of(t)
        txt = place_label(ax, lab["series"][t], lines[t], others=other, color=style.policy(k).label_color)
        if txt is not None:
            txt.set_path_effects([])
            txt._sublet_role = "series_label"
            txt._sublet_policy = k
        out.append(txt)
    return out


def keys_mode(data: Mapping) -> str:
    """'direct' where both series labels fit in (a) (a probe draw), else 'row' (the legend row above the panels)."""
    fig = draw({**data, "layout": {**data["layout"], "keys": "direct"}}, probe=True)
    return "direct" if all(t is not None for t in fig._sublet_series_labels) else "row"


def draw(data: Mapping, probe: bool = False) -> Any:
    lab = data["labels"]
    lay = data["layout"]
    mode = lay.get("keys", "row")
    fig = style.new_figure(NAME)
    axes = panel_axes(fig, data, legend=mode == "row")
    if mode == "row":
        style.legend_row(fig, KEYS)
    draw_policy_panel(axes[0], data["panels"]["a"], lay, y_axis=True)
    draw_policy_panel(axes[1], data["panels"]["b"], lay, y_axis=False)
    draw_parts(axes[2], data["panels"]["c"], lay, lab)
    fig._sublet_series_labels = []
    if mode == "direct":
        fig._sublet_series_labels = series_labels(axes[0], data["panels"]["a"], lab)
        if not probe and any(t is None for t in fig._sublet_series_labels):
            raise style.StyleError(f"[{NAME}] a series label fits nowhere in (a), but the extract's layout puts the "
                                   "keys there (rebuild the extract from the inputs)")
    axes[0].set_ylabel(lab["y"])
    axes[2].set_ylabel(lab["c_y"])
    for ax in axes:
        ax.set_xlabel(lab["x"])
    letters = style.panel_letters(axes)
    for ax, letter, p in zip(axes, letters, ("a", "b", "c")):     # C62: at the caption size, on the letters' baseline
        panel_title(ax, letter, lab["titles"][p], fontsize=style.LABEL_PT)
    fig._sublet_axes = dict(zip(("a", "b", "c"), axes))
    return fig


def panel_axes(fig, data: Mapping, legend: bool = True) -> list:
    """(a), (b) sharing y, (c) with its own; the left reserves from the widest y tick label (TICK_PT) and the y label
    (style.ytick_reserve), and a right reserve for (c)'s part names (the widest at TICK_PT and LABEL_GAP_PT); the
    legend row's reserve above them where the keys go there."""
    lay = data["layout"]
    names = [data["labels"]["parts"][k] for k in lay["c_parts"]]
    right = max([text_width_in(fig, n) for n in names], default=0.0) + LABEL_GAP_PT / style.BP_PER_IN + 0.04
    pads = {"y_ab": LOG_PAD, "y_c": C_PAD}
    left = [style.ytick_reserve(fig, [style.PLAIN(t) for t in (y_ticks(lay[k], pads[k]) if lay.get(k) else [1.0])],
                                ylabel=True) for k in ("y_ab", "y_c")]
    return style.panel_row(fig, AXES_RATIOS, legend=bool(legend), sharey=(False, True, False),
                           left=(left[0], None, left[1]), right=max(right, style.MARGIN_RIGHT))


# ---------------------------------------------------------------------------------------------------------------
# tables
def _ms(v, fmt: str = ".2f") -> str:
    return X.num(None if v is None else 1000.0 * float(v), fmt)


def _thin(text: str) -> str:
    """Thousands separated by a thin space (TeX \\,), not a comma, in both tables (MS7 print check, 2026-11-11): a
    comma would read as the separator of a range '[a, b]'."""
    return text.replace(",", r"\,")


def _ms3(v) -> str:
    """A time in ms to three significant digits without an exponent, with _thin's thousands separator (9\\,079, 94.3,
    0.77; e9v2_overhead.tex, so that the table fits the text width; '--' for None)."""
    if v is None:
        return "--"
    m = 1000.0 * float(v)
    return _thin(X.num(m, ",.0f" if abs(m) >= 99.95 else ".1f" if abs(m) >= 9.995 else ".2f"))


def _ms3_span(lo, hi) -> str:
    """The range '[a, b]' of _ms3, the value alone where the two ends print the same, '--' when either is missing."""
    if lo is None or hi is None:
        return "--"
    a, b = _ms3(lo), _ms3(hi)
    return a if a == b else f"[{a}, {b}]"


def llm_text(llms: str | None) -> str:
    """The LLM tiers of a point's set ('SML' as 'S, M, L')."""
    return "--" if not llms else ", ".join(llms)


def _point_cells(r: Mapping) -> list[str]:
    return [r["menu"] or "--", "--" if r["V"] is None else str(r["V"]), llm_text(r["llms"]),
            "--" if r["sites_x_llms"] is None else _thin(f"{int(r['sites_x_llms']):,}")]


def overhead_tex(t: Sequence[Mapping], d: Mapping) -> str:
    rows = []
    for r in t:
        a, o = r["act"], r["overhead"]
        rows.append(_point_cells(r) + [_ms3(a["Sublet"]["median"]), _ms3_span(a["Sublet"]["lo"], a["Sublet"]["hi"]),
                                       _ms3(a["A9"]["median"]), _ms3_span(a["A9"]["lo"], a["A9"]["hi"]),
                                       _ms3(o["median"]), _ms3_span(o["lo"], o["hi"]), X.num(r["ratio_median"], ".1f"),
                                       X.num(r["loops_s_per_h"]["Sublet"], ".2f"),
                                       X.num(r["loops_s_per_h"]["A9"], ".2f"),
                                       X.num(r["peak_rss_mb"]["Sublet"], ".0f"), X.num(r["peak_rss_mb"]["A9"], ".0f")])
    groups = [i for i in range(1, len(t)) if t[i]["menu"] != t[i - 1]["menu"]]
    cr = X.tex(style.POLICIES["a9"].label).lower()
    cap = (r"The scaling study per point, each job alone on the host, over " + str(len(d["alignments"]))
           + r" alignments of a day: the act time per slow-loop slot (ms) of Sublet and of " + cr + r", its inner "
           r"policy, with the median and range over the alignments; the guard's overhead, Sublet's time minus " + cr
           + r"'s in the same alignment (median, range), and their ratio (median); the wall time of the slow and fast "
           r"loops per simulated hour (s) and the peak memory (MB) of each, medians. A slow-loop slot is "
           + X.num(d["slot_s"], "g") + r"~s. Every run is in the data file " + RUNS_CSV.replace("_", r"\_")
           + ".")
    head_top = (r" & & & & \multicolumn{2}{c}{Sublet (ms)} & \multicolumn{2}{c}{Critical-ratio (ms)} & "
                r"\multicolumn{3}{c}{Overhead} & \multicolumn{2}{c}{Loops (s/h)} & \multicolumn{2}{c}{Memory (MB)} \\"
                "\n" r"\cmidrule(lr){5-6}\cmidrule(lr){7-8}\cmidrule(lr){9-11}\cmidrule(lr){12-13}\cmidrule(lr){14-15}")
    header = ["Menu", "$V$", "LLMs", r"\shortstack{Sites\\$\times$ LLMs}", "Median", "Range", "Median", "Range",
              "ms", "Range", "Ratio", "Sublet", r"\shortstack{Critical-\\ratio}", "Sublet",
              r"\shortstack{Critical-\\ratio}"]
    return X.longtable("@{}lrlr" + "r" * 11 + "@{}", cap, "tab:s-e9v2-overhead", header, rows, groups=groups,
                       tabcolsep="2.6pt", head_top=head_top)


def split_tex(t: Sequence[Mapping], d: Mapping) -> str:
    rows = []
    for r in t:
        ps = r["per_slot_mean_s"]
        rows.append(_point_cells(r) + [str(r["alignment"]), {True: "yes", False: "no"}.get(r["identical"], "--")]
                    + [_thin(_ms(ps[k], ",.3f")) for k in SPLIT_KEYS])
    groups = [i for i in range(1, len(t)) if t[i]["menu"] != t[i - 1]["menu"]]
    cap = (r"The guard's time per slow-loop slot by part (mean, ms), from one instrumented run of Sublet per point "
           r"(alignment), used where the run equals the uninstrumented one bit for bit (Equal): Sublet's act time, "
           r"its inner policy's, the guard's (the difference), and the guard's parts: the safe expert's step, the "
           r"online lower bound, the guard's test (the update of its bound and the slot's first evaluation), the "
           r"projection (the candidates and the later evaluations) and the rest.")
    header = ["Menu", "$V$", "LLMs", r"\shortstack{Sites\\$\times$ LLMs}", "Alignment", "Equal", "Act", "Inner",
              "Guard", r"\shortstack{Safe\\expert}", r"\shortstack{Lower\\bound}", "Test", "Projection", "Rest"]
    return X.longtable("@{}lrlrrl" + "r" * 8 + "@{}", cap, "tab:s-e9v2-split", header, rows, groups=groups,
                       tabcolsep="3.0pt")


def write_tables(data: Mapping, report: Mapping) -> None:
    t = data["tables"]
    paths = [write_table(TABLES[0], X.table_head(NAME, [ANALYSIS, SUMMARY]) + overhead_tex(t["overhead"], data)),
             write_table(TABLES[1], X.table_head(NAME, [ANALYSIS]) + split_tex(t["split"], data)),
             X.write_csv(t["e9v2_runs"], NAME)]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    return X.run(NAME, build, draw, argv, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
