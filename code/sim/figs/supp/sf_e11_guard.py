"""sf_e11_guard: the guard in E11 (design/sim_spec_ms3.md §8.7; design/figure_plan.md §4, part S-F), and the scope
table e11_scope.tex (paper/supplement/tables/; SUBLET_FIGS_TABLES_DIR, else SUBLET_FIGS_PDF_DIR when set,
figs.common.tables_dir).

(a) The share of a guarded policy's runs that abort (a one-way guard trips at most once, so this is E11's trips per
    run) per lender mode, from code/sim/out/e11/summary.json
    D3.trips.<I>.<mode>.<tag>.trips_per_run: a horizontal bar per guarded policy at the share over every run of that
    mode on the instances that ran it (each instance weighted by its runs), ended by the policy's marker (so that the
    bars read in greyscale), with a dot per instance on the bar; one row per mode, named on the y axis (C62: at 7 pt
    the seven names still need 179 pt side by side, against a panel's 132 pt); the x axis starts just left of 0, so
    that dots at 0 clear the y axis; C62: light vertical grid lines at every GRID_STEP behind the bars.
(b) The price of the guard under the trace lender, the median paired ratio of each guarded policy's cost to its inner
    policy's on the same cell, with its 95% bootstrap interval (D3.price_of_guard_L-tr.<I>.<G>/<inner>), per instance
    (C62: light separators between the instances, as sf_e11_inst draws them, and y ticks 0.2 apart).
(c) The ECDF of the certificate ratio ALG(T) / core_bound_rhs over every A8 run file under code/sim/out/e11/runs/
    (meta.policy A8; full model and exact core exports), one per guarded policy of Fig. 3, with the policy's marker at
    about every ECDF_MARK_STEP_PT of its drawn length (C62, ecdf_marks; at about every 5% of its runs before, where
    the markers stacked into columns on the steep rises), staggered between the policies, where its ratio is below
    ECDF_MARK_BELOW (C47); the other A8 tags (PS-GR, PS-G1) are in the extract. A ratio of at most 1 (up to the
    tolerance) is the certificate's core bound holding: Theorem W(a)(b) (PROVEN for the engine as implemented under
    C1-C3, audited) on full-model runs in its proven case, G2 (PROVEN, audited) on core exports.
The scope runs of D6 (slow grid, s5_tau5_H5, alpha 0.2 and 0.3, headroom on the slow grid) go to e11_scope.tex.

C47 (print check of the gate, U46): (a)'s x label says what it plots, "Share of runs that abort" (was "Trips per
run"), and its lender names are the table's and the other figures' ("i.i.d. 0.05", "correlated"; were "iid 0.05",
"corr."). (c) puts no marker where the ratio is ECDF_MARK_BELOW or more: 28-44% of each policy's runs end within 1%
of the bound, and their markers stood in one column on the vertical at 1, hiding the lines; labels.caption gives
those shares (labels.at_bound). labels.caption is a caption draft for the supplement. The table writes the variant
s5_tau5_H5 as "5-min notice" and defines it in its caption, names Fig. 3 by \ref and no experiment ID, and defines
the headroom as LB over all-fallback.

MS6 C46 (design/ms6_spec.md M2-M4): the guarded policies are their configurations' keys (BL5-G bl5_g1, "Lagged
RetroRenting + one-way guard"; PS-G a7_g1; BL1-G bl1_g1; BL5 bl5_lag); the data tags are E11's. The table sets each
guarded configuration's column beside its inner policy's under the inner policy's name (_head). Their legend is a
row over the panels (registry labels, one row, in GUARDED's order, as (a) draws the bars from the top and (b) the
points from the left): in (c)'s upper left corner the longer names ran off the page, so the figure is 2.5 in high
(2.2 in before), the largest supplementary height, and its panels are a little taller. (c) puts a marker on each
ECDF at about every 5% of its runs (20 markers; 10% before; C62 places them by drawn length, ecdf_marks): bl1_g1's
orange and bl5_g1's sky blue print as one grey, and their curves run together between the shares 0.33 and 0.55 (print
check of the gate). The markers at the bars' ends in (a) stay: they tell the bars apart in greyscale.

C62 (the type scale of the caption; figures high-end, informative, readable): the margins of style; (a) light vertical
grid lines at 0.25, 0.5, 0.75 and 1 behind the bars; (b) light separators between the instances and y ticks 0.2 apart
(MaxNLocator's default set eight labels 0.1 apart at 7 pt); (c) markers by drawn length (ecdf_marks), none within
ECDF_MARK_FLOOR_PT of the x axis. The height stays 2.5 in (the top of the supplementary range): the 21 bars of (a)
need it. The extract and the scope table are unchanged.
C62 fix round (the supplement's critic): (c)'s x label sets T in math italic, "$\\mathrm{ALG}(T)$ / certificate
bound" (C_X_LABEL; "ALG(T)" set T upright, against the caption's $\\ALG(T)$), on the row's x-label baseline as the PDF
prints it (common.align_baselines); (b), which has no x ticks, sets the instance names one tick length further
down, so that the row's tick labels and x labels share one baseline ((b)'s sat 3 pt above the others). The extract's
labels.c_x changes with it (a label entry; its data entries and the scope table are unchanged).

Run files are read, so the extract code/sim/out/figs/sf_e11_guard.json carries every plotted value and label and is
the figure's source; ``--from-extract`` redraws from it alone (and rewrites the table from the extract's ``scope``).
Run from code/sim: ``python -m figs.supp.sf_e11_guard [--from-extract [JSON]]`` (figs.common.cli).

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): e11_scope.tex's caption leaves the definitions
of r_best and r_0 to the supplement's text before the table (s_f1.tex), so that the float fits its page without the
\\arraystretch override.
"""
from __future__ import annotations

import json
import sys

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

from figs import style
from figs.common import align_baselines, cli, finite, tex_num, write_table
from figs.inputs import Inputs

NAME = "sf_e11_guard"
WIDTH, HEIGHT = "W2", 2.5       # C46: with a legend row (style.LEGEND_ROW) over the panels, 2.2 in before
SUMMARY = "code/sim/out/e11/summary.json"
RUNS = "code/sim/out/e11/runs"
RUN_PATTERN = RUNS + "/**/*.json"
TABLE = "e11_scope.tex"
INSTANCES = ("I1", "I2", "I3", "I4")
MODES = ("L-tr", "L-eg", "L-ss", "L-iid-0.0124", "L-iid-0.05", "L-iid-0.2", "L-co")
GUARDED = {"BL5-G": ("bl5_g1", "BL5"), "PS-G": ("a7_g1", "PS"), "BL1-G": ("bl1_g1", "BL1")}     # C46 (M2-M4)
OTHER_A8 = ("PS-GR", "PS-G1")
KEYS = tuple(k for k, _ in GUARDED.values())
SCOPE_TAGS = ("BL5-G", "BL5", "PS-G", "PS", "BL1-G", "BL1", "BL2", "A6")
SCOPE_TAG_KEY = {"BL5-G": "bl5_g1", "BL5": "bl5_lag", "PS-G": "a7_g1", "PS": "a7", "BL1-G": "bl1_g1",
                 "BL1": "bl1", "BL2": "bl2", "A6": "a6"}                                        # C46 (M2-M4)
BAR_GROUP = 0.78                      # height of a mode's group of bars (category units)
BAR_FILL = 0.6                        # share of its slot a bar fills, so that the marker at its end shows its shape
DOT_PT = 1.6                          # (a): the dot of each instance on a bar
SPINE_CLEAR_PT = 1.5                  # (a): the x axis starts this far left of 0, so that a dot at 0 clears the spine
ECDF_MARK_BELOW = 0.99                # (c): C47, markers only where the ratio is below this (the rise at 1 unmarked)
ECDF_MARK_STEP_PT = 16.0              # (c): C62, a marker about every this many pt along each ECDF (C47: at every 5%
#                                       of the runs, 10% before; bl1_g1's orange and bl5_g1's sky blue print as one
#                                       grey, and between the shares 0.33 and 0.55 their curves run together, told apart
#                                       by their markers alone; direct labels of the registry names fit nowhere in the
#                                       panel; print check of the gate)
GRID_STEP = 0.25                      # (a): C62, light vertical grid lines at this step behind the bars (as the paper's
#                                       Fig. 4(a))
B_Y_BINS = 5                          # (b): C62, at most this many y steps (0.2 apart; eight labels 0.1 apart before)
ECDF_MARK_FLOOR_PT = 3.0              # (c): C62, no marker this close to the x axis (one at a ratio's first point sat
#                                       on the spine)
C_X_LABEL = r"$\mathrm{ALG}(T)$ / certificate bound"   # (c): C62 fix round, T in math italic as the caption's $\ALG(T)$

style.register_supplementary(NAME, WIDTH, HEIGHT)


def mode_label(mode: str) -> str:
    """Short tick label of a lender mode, on one line: trace, eager, safe-site, i.i.d. at p, correlated (C47: the
    table's and the other figures' names, "i.i.d. 0.05" and "correlated"; "iid 0.05" and "corr." before)."""
    if mode.startswith("L-iid-"):
        return "i.i.d. " + mode[len("L-iid-"):]
    return {"L-tr": "trace", "L-eg": "eager", "L-ss": "safe-site", "L-co": "correlated",
            "L-ad": "adaptive"}.get(mode, mode)


# ---------------------------------------------------------------------------------------------------------------
def _certificates(inp: Inputs) -> dict:
    """Certificate ratios ALG_T / core_bound_rhs of every A8 run file, by tag and model (full or core)."""
    names = inp.glob(RUN_PATTERN)
    out: dict = {}
    n_files = 0
    for name in names:
        base = name.rsplit("/", 1)[-1]
        if base.startswith("cell_") or base.endswith("_sum.json"):
            continue
        style.check_source(name)
        with open(inp.root / name, encoding="utf-8") as f:
            run = json.load(f)
        n_files += 1
        if (run.get("meta") or {}).get("policy") != "A8":
            continue
        q = run["q44"]
        c = q["certificate"]
        if not c.get("available") or c.get("core_bound_rhs") is None:
            raise style.StyleError(f"{name}: no certificate core bound")
        model = "core" if q.get("grid") == "core" else "full"
        d = out.setdefault(q["tag"], {"ratio": [], "model": [], "held": 0, "runs": 0})
        d["ratio"].append(float(c["ALG_T"]) / float(c["core_bound_rhs"]))
        d["model"].append(model)
        d["held"] += bool(c.get("held"))
        d["runs"] += 1
    if not out:
        raise style.StyleError(f"no A8 run file under {RUNS}")
    res = {}
    for tag, d in out.items():
        r = np.asarray(d["ratio"])
        order = np.argsort(r, kind="stable")
        res[tag] = {"sorted": r[order].tolist(), "model": [d["model"][i] for i in order], "n": int(r.size),
                    "n_full": d["model"].count("full"), "n_core": d["model"].count("core"), "max": float(r.max()),
                    "min": float(r.min()), "held": d["held"]}
    return {"by_tag": res, "files_read": n_files}


SCOPE_METRICS = (("L-tr", "r_best"), ("L-eg", "r0"), ("L-iid-0.05", "r0"))     # every (mode, metric) D6 compares


def _scope(S: dict) -> dict:
    D6 = S["D6"]
    rows = []
    for variant, src in (("slow grid", "slow_grid"), ("s5_tau5_H5", "H5"), ("alpha", "alpha")):
        for inst, modes in D6[src].items():
            for mode, metric in SCOPE_METRICS:
                if mode not in modes:
                    continue
                vals = {t: {"value": modes[mode][t][metric], "default": modes[mode][t][metric + "_default"]}
                        for t in SCOPE_TAGS}
                rows.append({"variant": variant, "instance": inst, "mode": mode, "metric": metric, "values": vals})
    head, no_lb = [], []
    for inst, modes in D6["headroom"].items():
        for mode, v in modes.items():
            if "tuning" in mode or not isinstance(v, dict) or v.get("h") is None:
                continue
            if v["h"].get("median") is None:          # no cell of the mode has an LB (cells_with_lb 0)
                no_lb.append({"instance": inst, "mode": mode, "cells": v.get("cells"),
                              "cells_with_lb": v.get("cells_with_lb")})
                continue
            head.append({"instance": inst, "mode": mode, "cells": v.get("cells"), "h": v["h"]["median"],
                         "h_ci": v["h"]["median_ci95"],
                         "r_LB": {t: (v["r_LB"].get(t) or {}).get("median") for t in SCOPE_TAGS}})
    return {"rows": rows, "headroom": head, "headroom_without_lb": no_lb,
            "headroom_without_lb_note": "D6.headroom modes whose held-out cells have no LB on the slow grid; not in "
                                        "the table",
            "tags": list(SCOPE_TAGS), "tag_labels": [style.POLICIES[SCOPE_TAG_KEY[t]].label for t in SCOPE_TAGS],
            "thresholds": S["D4"]["thresholds"]}


def collect(inp: Inputs) -> dict:
    S = inp.json(SUMMARY)
    trips = S["D3"]["trips"]
    a = {}
    for tag, (key, _) in GUARDED.items():
        share, per_inst = [], []
        for m in MODES:
            runs = trips_ = 0.0
            pi = {}
            for I in INSTANCES:
                v = (trips.get(I) or {}).get(m, {}).get(tag)
                if v is None:
                    continue
                pi[I] = v["trips_per_run"]
                runs += v["runs"]
                trips_ += v["trips_per_run"] * v["runs"]
            share.append(trips_ / runs if runs else None)
            per_inst.append(pi)
        a[key] = {"tag": tag, "modes": list(MODES), "share": share, "per_instance": per_inst}
    pog = S["D3"]["price_of_guard_L-tr"]
    b = {}
    for tag, (key, inner) in GUARDED.items():
        r = [pog[I][f"{tag}/{inner}"] for I in INSTANCES]
        b[key] = {"tag": tag, "inner": inner, "instance": list(INSTANCES), "median": [v["median"] for v in r],
                  "ci_lo": [v["median_ci95"][0] for v in r], "ci_hi": [v["median_ci95"][1] for v in r],
                  "n": [v["n"] for v in r]}
    cert = _certificates(inp)
    c = {GUARDED[t][0]: cert["by_tag"][t] for t in GUARDED}
    c_other = {t: cert["by_tag"][t] for t in OTHER_A8 if t in cert["by_tag"]}
    tot = {"runs": sum(v["n"] for v in cert["by_tag"].values()),
           "full": sum(v["n_full"] for v in cert["by_tag"].values()),
           "core": sum(v["n_core"] for v in cert["by_tag"].values()),
           "held": sum(v["held"] for v in cert["by_tag"].values()),
           "max_ratio": max(v["max"] for v in cert["by_tag"].values()),
           "summary_full_model": S["certificate_full_model"]["total"],
           "summary_core": S["D5"]["certificate"]["total"],
           "files_read": cert["files_read"]}
    # the run files counted here are the summary's: certificate_full_model (full model) and D5.certificate (core)
    tot["matches_summary"] = bool(tot["full"] == tot["summary_full_model"]["runs"]
                                  and tot["core"] == tot["summary_core"]["runs"])
    if not tot["matches_summary"]:
        raise style.StyleError(f"A8 run files: {tot['full']} full-model and {tot['core']} core, against the summary's "
                               f"{tot['summary_full_model']['runs']} and {tot['summary_core']['runs']}")
    out = {"git_revision": S["meta"]["git_revision"], "modes": list(MODES),
           "mode_labels": [mode_label(m) for m in MODES], "instances": list(INSTANCES), "a": a, "b": b, "c": c,
           "c_other": c_other, "certificates": tot, "scope": _scope(S), "labels": {
               "a_x": "Share of runs that abort", "a_y": "Lender", "b_x": "Instance",
               "b_y": "Cost with / without guard",
               "c_x": C_X_LABEL, "c_y": "Share of runs",
               "status": {"W_ab": "PROVEN for the engine as implemented under C1-C3, audited",
                          "G2": "PROVEN, audited", "W_c": "CONJECTURE"},
           }}
    # C47: the share of each drawn policy's runs within 1% of the bound (unmarked in (c)), and the caption draft
    out["labels"]["at_bound"] = {k: float(np.mean(np.asarray(v["sorted"]) >= ECDF_MARK_BELOW)) for k, v in c.items()}
    out["labels"]["caption"] = caption(out)
    return out


CAPTION = ("The one-way guard (Algorithm~1 without projection) around three inner policies, at Algorithm~1's "
           "defaults, on the one-day instances I1--I4 and the exact core families of Fig.~\\ref{{fig:guard}}'s study. "
           "(a) The share of runs that abort under each lender: a bar over the instances that ran the lender (each "
           "weighted by its runs), ended by the policy's marker, and a dot per instance. (b) Under the trace lender, "
           "the median over the cells of the guarded configuration's cost over its inner policy's on the same cell, "
           "with its 95\\% bootstrap interval. (c) Empirical distribution of $\\mathrm{{ALG}}(T)$ over the run's "
           "certificate bound over the {n:,} runs of each configuration ({n_full:,} full-model runs, with the bound of "
           "Theorem~\\ref{{thm:fullmodel}}, proven where all-fallback follows an abort and conjectured otherwise; "
           "{n_core:,} core exports, with the bound of Theorem~\\ref{{thm:envelope}}). The bound held in all {held:,} "
           "runs of the one-way guard (largest ratio {max_ratio:.4f}). Markers stop at a ratio of {mark_below}: "
           "{at_bound} of the runs lie within 1\\% of the bound.")


def caption(d: dict) -> str:
    """labels.caption (C47): the caption draft, with the run counts of the certificates and the shares at the bound."""
    keys = list(d["c"])
    n, n_full, n_core = ({d["c"][k][f] for k in keys} for f in ("n", "n_full", "n_core"))
    if len(n) != 1 or len(n_full) != 1 or len(n_core) != 1:
        raise style.StyleError(f"{NAME}: the configurations of (c) have different run counts")
    shares = [f"{100 * d['labels']['at_bound'][k]:.0f}\\% ({style.POLICIES[k].label})" for k in keys]
    t = d["certificates"]
    return CAPTION.format(n=n.pop(), n_full=n_full.pop(), n_core=n_core.pop(), held=t["held"],
                          max_ratio=t["max_ratio"], mark_below=ECDF_MARK_BELOW,
                          at_bound=", ".join(shares[:-1]) + " and " + shares[-1])


# ---------------------------------------------------------------------------------------------------------------
def draw_a(ax, data: dict, lab: dict) -> None:
    keys = list(data["a"])
    n = len(keys)
    w = BAR_GROUP / n
    for j, key in enumerate(keys):
        s = data["a"][key]
        p = style.policy(key)
        y = np.arange(len(s["modes"])) - BAR_GROUP / 2 + (j + 0.5) * w
        v = finite(s["share"])
        ax.barh(y, v, height=w * BAR_FILL, color=p.color, edgecolor="none", zorder=2.0, label="_nolegend_")
        style.scatter_policy(ax, key, v, y)
        for i, pi in enumerate(s["per_instance"]):
            vals = list(pi.values())
            ax.plot(vals, [y[i]] * len(vals), linestyle="none", marker="o", markersize=DOT_PT,
                    markerfacecolor="black", markeredgecolor="none", zorder=3.0)
    ax.set_yticks(range(len(data["modes"])))
    ax.set_yticklabels(data["mode_labels"])
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(len(data["modes"]) - 0.45, -0.55)          # the first mode at the top
    pad = (0.5 * DOT_PT + SPINE_CLEAR_PT) / (style.axes_rect_in(ax)[2] * style.BP_PER_IN)    # axes fraction
    ax.set_xlim(-pad * 1.06 / (1.0 - pad), 1.06)
    ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    for v in np.arange(GRID_STEP, 1.0 + 1e-9, GRID_STEP):          # C62: behind the bars, the dots and the markers
        ax.axvline(v, color=style.GRID_GREY, linewidth=style.GRID_PT, zorder=0.5)
    ax.xaxis.set_major_formatter(style.PLAIN)
    ax.set_xlabel(lab["a_x"])
    ax.set_ylabel(lab["a_y"])


def draw_b(ax, data: dict, lab: dict) -> None:
    style.reference_line(ax, y=1.0)
    keys = list(data["b"])
    offs = np.linspace(-0.22, 0.22, len(keys))
    for off, key in zip(offs, keys):
        s = data["b"][key]
        x = np.arange(len(s["instance"])) + off
        y = finite(s["median"])
        lo = finite(s["ci_lo"])
        hi = finite(s["ci_hi"])
        style.errorbars(ax, key, x, y, lo, hi)
        style.scatter_policy(ax, key, x, y)
    ax.set_xticks(range(len(data["instances"])))
    ax.set_xticklabels(data["instances"])
    # no ticks; C62 fix round: the names as far below the axis as (a)'s and (c)'s tick labels, so that the row's tick
    # labels and x labels share one baseline ((b)'s sat one tick length, 3 pt, high)
    rc = style.mpl.rcParams
    ax.tick_params(axis="x", length=0, pad=rc["xtick.major.pad"] + rc["xtick.major.size"])
    ax.set_xlim(-0.5, len(data["instances"]) - 0.5)
    for i in range(1, len(data["instances"])):          # C62: the instances' groups apart, as in sf_e11_inst (a), (b)
        ax.axvline(i - 0.5, color=style.GRID_GREY, linewidth=style.GRID_PT, zorder=0.5)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=B_Y_BINS, steps=[1, 2, 5, 10]))
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.set_xlabel(lab["b_x"])
    ax.set_ylabel(lab["b_y"])


def ecdf_marks(ax, x, y, j: int, n: int) -> list[int]:
    """C62: indices of the points of a steps-post ECDF (x, y) (the drawn arrays) at about every ECDF_MARK_STEP_PT of its
    drawn length on the panel's final scales, the targets staggered by (j + 0.5) / n of a step between the n curves;
    none where the ratio is ECDF_MARK_BELOW or more (C47) or within ECDF_MARK_FLOOR_PT of the x axis. Placed by length,
    not by share of runs (C47's every 5%), the markers no longer stack into columns where an ECDF rises steeply, and
    still mark every stretch of the curve."""
    k_pt = style.BP_PER_IN / ax.figure.dpi
    P = ax.transData.transform(np.column_stack([x, y])) * k_pt
    floor = ax.transData.transform((x[0], 0.0))[1] * k_pt + ECDF_MARK_FLOOR_PT
    s = np.r_[0.0, np.cumsum(np.abs(np.diff(P[:, 0])) + np.abs(np.diff(P[:, 1])))]   # along the steps (pt)
    targets = np.arange((j + 0.5) / n * ECDF_MARK_STEP_PT, s[-1], ECDF_MARK_STEP_PT)
    out = []
    for i in sorted({int(np.argmin(np.abs(s - t))) for t in targets}):
        # where a target falls in a long step, the nearest point can lie next to the following target's: at least
        # half a step apart along the curve
        if x[i] < ECDF_MARK_BELOW and P[i, 1] >= floor and (not out or s[i] - s[out[-1]] >= 0.5 * ECDF_MARK_STEP_PT):
            out.append(i)
    return out


def draw_c(ax, data: dict, lab: dict) -> None:
    style.reference_line(ax, x=1.0)
    keys = list(data["c"])
    curves = {}
    for key in keys:
        r = np.asarray(data["c"][key]["sorted"], dtype=float)
        curves[key] = (np.r_[r[0], r], np.r_[0.0, np.arange(1, r.size + 1) / r.size])
    lo = min([1.0] + [float(x[0]) for x, _ in curves.values()])
    ax.set_xlim(lo - 0.04 * (1.0 - lo + 1e-9), 1.0 + 0.06 * (1.0 - lo + 1e-9))
    ax.set_ylim(0.0, 1.02)
    for j, key in enumerate(keys):
        # the policy's marker along its ECDF (ecdf_marks; the scales set first), staggered between the policies so
        # that markers of curves that run together do not sit on each other
        x, y = curves[key]
        style.plot_policy(ax, key, x, y, drawstyle="steps-post", markevery=ecdf_marks(ax, x, y, j, len(keys)),
                          label="_nolegend_")
    ax.xaxis.set_major_formatter(style.PLAIN)
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.set_xlabel(lab["c_x"])
    ax.set_ylabel(lab["c_y"])


def draw(data: dict):
    lab = data["labels"]
    fig = style.new_figure(NAME)
    left = style.ytick_reserve(fig, data["mode_labels"], ylabel=True)      # (a) names the lender modes on its y axis
    axes = style.panel_row(fig, (1, 1, 1), legend=True, left=[left, None, None])
    draw_a(axes[0], data, lab)
    draw_b(axes[1], data, lab)
    draw_c(axes[2], data, lab)
    align_baselines([ax.xaxis.label for ax in axes])   # C62 fix round: (c)'s mathtext label on the row's
    style.panel_letters(axes)
    # C46: the guarded policies, over the panels; C47: in the order (a) draws them from the top and (b) from the left
    # (GUARDED's), not the registry's (print check of the gate: the legend listed PD heuristic first)
    style.legend_row(fig, [], extra=[(Line2D([], [], **style.policy_kwargs(k)), style.policy(k).label)
                                     for k in data["c"]])
    return fig


# ---------------------------------------------------------------------------------------------------------------
def _two_lines(label: str) -> str:
    """A header label broken at the space nearest its middle (never inside a word), for \\shortstack; a guarded
    configuration's name before its " + " (C46: "Greedy\\+ one-way guard", as the figures break it)."""
    if " + " in label:
        return label.replace(" + ", r"\\+ ", 1)
    w = label.split(" ")
    if len(w) == 1:
        return label
    cut = min(range(1, len(w)), key=lambda i: abs(len(" ".join(w[:i])) - len(" ".join(w[i:]))))
    return " ".join(w[:cut]) + r"\\" + " ".join(w[cut:])


def _head(tags, labels) -> tuple[str, str, str]:
    """The table's two header rows over the policy columns, and their \\cmidrules (C46, design/ms6_spec.md M5: a
    guarded configuration's column, tag "<inner>-G", stands beside its inner policy's under the inner policy's name,
    as the paired legend of Fig. 3 groups them; the configuration names on their own made the table 89 pt wider than
    the page): (row 1, row 2, rules). A pair spans two columns, "+ one-way guard" and "inner policy"; any other
    policy is named in row 2."""
    top, bottom, rules = [], [], []
    i, col = 0, 4                                      # columns 1-3: variant, instance, lender and metric
    while i < len(tags):
        if i + 1 < len(tags) and tags[i] == tags[i + 1] + "-G":
            top.append(r"\multicolumn{2}{c}{\shortstack{" + _two_lines(labels[i + 1]) + "}}")
            bottom += [r"\shortstack{+ one-way\\guard}", r"\shortstack{inner\\policy}"]
            rules.append(rf"\cmidrule(lr){{{col}-{col + 1}}}")
            i, col = i + 2, col + 2
        else:
            top.append("")
            bottom.append(r"\shortstack{" + _two_lines(labels[i]) + "}")
            i, col = i + 1, col + 1
    return " & ".join(top), " & ".join(bottom), "".join(rules)


def scope_table(scope: dict) -> str:
    """paper/supplement/tables/e11_scope.tex: the D6 scope runs of E11 (a table* float, booktabs). Each variant row
    carries the default (1-min grid, alpha 0.40, default menu, same configuration seeds) on the line below it."""
    tags, labels = scope["tags"], scope["tag_labels"]
    top, head, rules = _head(tags, labels)
    var = {"slow grid": "Slow grid", "s5_tau5_H5": "5-min notice", "alpha": r"$\alpha$"}      # C47: no contract tag
    lender = {"L-tr": "trace", "L-eg": "eager", "L-iid-0.05": r"i.i.d.\ 0.05", "L-ad": "adaptive"}
    met = {"r_best": r"$r_{\mathrm{best}}$", "r0": r"$r_0$"}
    # C47 (print check of the gate): no experiment ID, Fig. 3 by \ref, the 5-min-notice variant defined, and the
    # headroom defined as LB over all-fallback (one quantity, with its interval on the line below)
    # C50 (D5 review; D4's script items): the definitions of r_best and r_0 are in the supplement's text before the
    # table (s_f1.tex), so that the float fits its page without the \arraystretch override that s_f1.tex had
    lines = [r"\begin{table*}[t]", r"\caption{Scope runs of the guard study of Fig.~\ref{fig:guard}. Each cell is "
             r"the variant's median over the held-out cells, with the default (1-min grid, $\alpha=0.40$, default "
             r"menu, same configuration seeds) below it. Slow grid: 5-min routing; 5-min notice: the default menu's "
             r"contract with $(\tau,H)=(5,2)$~min replaced by a $(5,5)$-min one. Paired columns: the inner policy inside Algorithm~1 without projection (the one-way guard) "
             r"and alone. Bottom, on the slow grid: the headroom $h$, LB over all-fallback (median; 95\% interval "
             r"below), and the cost over LB, with LB the LP of the cohort MILP on the run's realized schedule (under "
             r"the eager lender, of its site-merged relaxation), so these ratios bound those to "
             r"$\mathrm{OPT}(\sigma,\omega)$ from above.}",
             r"\label{tab:e11-scope}", r"\centering\footnotesize", r"\setlength{\tabcolsep}{3.4pt}",
             r"\begin{tabular}{@{}lll" + "r" * len(tags) + "@{}}", r"\toprule",
             r" & & & " + top + r" \\" + rules, r"Variant & Instance & Lender, metric & " + head + r" \\",
             r"\midrule"]
    prev = None
    for r in scope["rows"]:
        v = var[r["variant"]] if r["variant"] != prev else ""
        if r["variant"] != prev and prev is not None:
            lines.append(r"\addlinespace")
        prev = r["variant"]
        inst = r["instance"].replace("-a", r", $\alpha=") + ("$" if "-a" in r["instance"] else "")
        lines.append(f"{v} & {inst} & {lender.get(r['mode'], r['mode'])}, {met[r['metric']]} & "
                     + " & ".join(tex_num(r["values"][t]["value"]) for t in tags) + r" \\")
        lines.append(r" & & \quad default & " + " & ".join(f"({tex_num(r['values'][t]['default'])})" for t in tags)
                     + r" \\")
    lines += [r"\midrule", r"Headroom & Instance & Lender, $h$ & \multicolumn{" + str(len(tags)) +
              r"}{c}{Cost / LB (slow grid)} \\", r"\midrule"]
    for h in scope["headroom"]:
        mode = lender.get(h["mode"], h["mode"])
        lines.append(f" & {h['instance']} & {mode}, {tex_num(h['h'])} & "
                     + " & ".join(tex_num(h["r_LB"].get(t)) for t in tags) + r" \\")
        lines.append(r" & & \quad " + f"[{tex_num(h['h_ci'][0])}, {tex_num(h['h_ci'][1])}]" + " &" * len(tags) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    return "\n".join(lines)


def write_scope_table(data: dict, rep: dict) -> None:
    """e11_scope.tex in figs.common.tables_dir() (SUBLET_FIGS_TABLES_DIR, else SUBLET_FIGS_PDF_DIR, else
    paper/supplement/tables/), from the extract's `scope`; and the report line of the certificates."""
    p = write_table(TABLE, scope_table(data["scope"]))
    t = data["certificates"]
    print(f"[{NAME}] {t['runs']} A8 runs ({t['full']} full model, {t['core']} core), {t['held']} held, max ratio "
          f"{t['max_ratio']:.6f}; wrote {p}")


def main(argv=None) -> dict:
    return cli(NAME, collect, draw, argv, supplementary=True, after=write_scope_table, extra_sources=[RUN_PATTERN],
               doc=__doc__)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
