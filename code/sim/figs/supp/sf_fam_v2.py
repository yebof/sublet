"""sf_fam_v2: the families of block Q6 and the confirmation's fresh family instances, part fam (design/sublet_v2.md
§11, W4, W7; §4.4(d), §6 H4; plan §4, part S-F).

Input (versioned): code/sim/out/sublet_v2/fam/summary.json (runs: one record per family run with fam, src, inst, mode,
seed, total, n_purchases, opt and ratio_opt = ALG/OPT against the exact OPT; fam.pairs: H4's pairs of A9 and RR_RENEW)
and code/sim/out/sublet_v2/analysis.json (H4: the counted pairs, the identity, Sublet's projecting runs, F3's mean
ALG/OPT per policy). Families, instances, lenders and seeds are read from the runs, never typed. No runs/ file is read
(meta.runs_files is empty). H4's counting rule is ms5b_analysis._counted (imported read-only): the fresh instances
(src CF1, CF2) and the Q6 instances under F-ss and F-iid; the Q6 instances under F-ad and F-eg repeat P3's runs for a
policy with no random draw (§4.4(d)) and are reported in full in fam_v2_q6.tex.

Layout (W2 x 2.2 in, C41), ALG/OPT on log axes, each instance's value the mean over its policy seeds (as E11's
D5), two panels:
(a) F1 and F2 (H4's families) by family and lender (x: F1 under the adaptive lender F-ad, F2 under the safe-site,
    i.i.d. and eager lenders, in q44_study.FAMILY_MODES's order, Q6 and fresh instances pooled), per policy the median
    over the instances with the range from the smallest to the largest instance (bars), dodged in x;
(b) F3 (C3-P5's insurance family) under the eager lender F-eg by beta (the instances' b<beta>_T<T>; one category
    per beta, in increasing order: the levels of Q6 and of the fresh instances interleave, 2, 4, 6, 14, 24, 30 on the
    confirmation, so that dodged markers on a log axis would cross into the neighboring level), per policy the median
    over the instances at that beta (T = 48 and 192 for Q6, 96 for the fresh ones) with their range, dodged in x.
Both panels draw markers only, so the legend shows markers without line segments, with a handle length of
LEGEND_HANDLE em (rcParams for the legend_row call; 2.0 left a gap of about 13 pt between a marker and its name at
9 pt, about 10 pt at 7 pt). The
series sit left to right in the legend's order (style.legend_order, read down the legend's columns), so that a
series' position backs up its marker in greyscale, where the orange and light-blue triangles print at one grey (print
check of 2026-11-03).
The policies: Sublet, Critical-ratio renting (A9) and its ablation without insurance (A9-noIns), Greedy + guard (BL1-GP,
A8P at Sublet's allowance), and E11's one-way guards Greedy + one-way guard (BL1-G) and Lagged RetroRenting + one-way
guard (BL5-G), at most six series per panel. RR_RENEW and MARKING are in the tables only: their orange is BL1's with
another family (check_policies, C41). Equal series (the same value at every instance of a panel; on the confirmation
Sublet, A9 and A9-noIns on F1 and F2, and BL1-GP and BL1-G on every family) are drawn dodged side by side and listed in
the extract's `equal` and the caption. The legend is two rows (one row needs 7.2 in at 7 pt, more than W2 less its
right margin).
C62 (the type scale of the caption; design/figure_plan.md §5): the panel titles at the caption size
(ms5b_e7_lib.caption_title); (a)'s categories on one line ("F1, adaptive"; the extract keeps the two-line group
labels, which draw() joins) under an x label of their own, on the baseline of (b)'s (as built, (a)'s second tick label
line sat beside (b)'s x label, on another baseline and at another size); the log y axis without minor ticks (a comb
of eight minor ticks between 1 and 10 and one above 10 at 9 pt).

Tables (TABLES; written by the after hook from the extract's `tables`, each with its `scope`; booktabs and array):
  fam_v2_pairs.tex  H4's pairs of A9 and RR-renew by family, instance set (Q6 or fresh) and lender: the pairs, those
                    with equal total cost and purchase count, whether H4 counts them, and Sublet's runs with a
                    projected slot; the totals against analysis.json's H4 (StyleError where they differ)
  fam_v2_f3.tex     F3: per instance and policy the mean ALG/OPT over the seeds, the guarded rows' aborts, and each
                    policy's mean over all runs (analysis.json H4.f3_ratio_opt, checked); the figure's caption gives
                    the guarded policies' F3 aborts too
  fam_v2_q6.tex     the Q6 instances under F-ad and F-eg: per instance the mean ALG/OPT of every policy that ran there,
                    RR-renew and Marking included; the caption decodes the instance ids and explains a dash (a policy
                    that did not run on an instance) where the table has one

The caption draft (labels.caption) reads every count from the inputs. Run from code/sim:
python -m figs.supp.sf_fam_v2 [--from-extract [JSON]] (figs.common.cli).

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): the captions print the paper's words for the
project names: "the pilot's runs" for P3's and "the single-LLM family" for the T4/O1 family.
"""
from __future__ import annotations

import re
import statistics
import sys
from typing import Any, Mapping, Sequence

import matplotlib
import numpy as np
from matplotlib.ticker import NullLocator

from figs import style
from figs.common import MissingKey, align_baselines, cli, finite, need, write_table
from figs.inputs import Inputs
from figs.supp.ms5b_e7_lib import caption_title
from figs.supp.sf_e3_v2 import tex_f, tex_label
from figs.supp.sf_e7_mix import _tex_text
from sublet.experiments.ms5b_analysis import COUNTED_Q6_MODES, _counted

NAME = "sf_fam_v2"
FAM = "code/sim/out/sublet_v2/fam/summary.json"
ANALYSIS = "code/sim/out/sublet_v2/analysis.json"
KEYS = style.SUPP_POLICIES_MS5B[NAME]          # sublet_v2, bl1_gp, bl1_g1, bl5_g1, a9, a9_noins
TAG_KEY = {"Sublet": "sublet_v2", "A9": "a9", "A9-noIns": "a9_noins", "BL1-GP": "bl1_gp", "BL1-G": "bl1_g1",
           "BL5-G": "bl5_g1"}
TABLE_TAGS = tuple(TAG_KEY) + ("RR_RENEW", "MARKING")      # the tables' columns (RR-renew and Marking: tables only)
TABLE_LABEL = {"RR_RENEW": "rr_renew", "MARKING": "marking"}   # their registry labels (style.POLICIES)
LENDERS = ("F-ad", "F-ss", "F-iid", "F-eg")      # q44_study.FAMILY_MODES's order
LENDER_NAME = {"F-ad": "adaptive", "F-ss": "safe-site", "F-iid": "i.i.d.", "F-eg": "eager"}
SLOTS = tuple(style.legend_order(TAG_KEY.values()))     # dodge slots, left to right: the legend's order
DRAW = tuple(reversed(SLOTS))                           # drawing order: Sublet last
LEGEND_HANDLE = 0.8             # the legend's handle length (em) for markers without line segments (not in §8)
DODGE_GROUP = 0.13              # x offset between neighboring slots, in categories (not in §8)
WIDTHS = (1.0, 1.2)             # panel width ratio: (a) has one category per family and lender, (b) one per beta
BETA_RE = re.compile(r"_b(\d+)_T(\d+)$")
TABLES = ("fam_v2_pairs.tex", "fam_v2_f3.tex", "fam_v2_q6.tex")
SAME_TOL = 1e-12                # relative: two series equal at every instance (labels, `equal`)
style.register_supplementary(NAME, "W2", 2.2)
# C59 (RC19(3)): panel (b) names the family in words (as built "F3 (C3-P5)"), and the tables print the instance set
# of the guard study's family instances (the summary's src F...; as built "Q6") as SET_TEXT gives it
SET_TEXT = {"Q6": "guard study", "fresh": "fresh"}
# C62: (a)'s x label, beside (b)'s (as built, (a) had none and its categories took two lines)
LABELS = {"a_y": "ALG / OPT", "a_x": "Family, lender", "b_x": r"$\beta$ (F3, eager lender)",
          "titles": {"a": "F1 and F2, by lender", "b": "F3, insurance family"},
          "group": "{fam}\n{lender}",
          "order": "the series sit left to right in the legend's order, read down its columns"}


# ---------------------------------------------------------------------------------------------------------------
# inputs
def instance_means(runs: Sequence[Mapping]) -> dict:
    """{(fam, src, inst, mode, tag): {mean, n, seeds}} of ratio_opt over the policy seeds."""
    acc: dict = {}
    for r in runs:
        if r.get("kind") != "fam" or r.get("status") != "ok" or r.get("ratio_opt") is None:
            continue
        acc.setdefault((r["fam"], r["src"], r["inst"], r["mode"], r["tag"]), []).append((r["seed"], r["ratio_opt"]))
    return {k: {"mean": statistics.fmean(v for _, v in vs), "n": len(vs), "seeds": sorted(s for s, _ in vs)}
            for k, vs in acc.items()}


def agg(values: Sequence[float]) -> dict:
    """{median, lo, hi, n}: the median and range of instance values."""
    if not values:
        return {"median": None, "lo": None, "hi": None, "n": 0}
    return {"median": float(np.median(values)), "lo": float(min(values)), "hi": float(max(values)), "n": len(values)}


def panel_a(means: Mapping) -> dict:
    groups = [(f, m) for f in ("F1", "F2") for m in LENDERS
              if any(k[0] == f and k[3] == m for k in means)]
    out = {"groups": [{"fam": f, "mode": m, "label": LABELS["group"].format(fam=f, lender=LENDER_NAME.get(m, m))}
                      for f, m in groups], "series": {}}
    for tag, key in TAG_KEY.items():
        s = {"median": [], "lo": [], "hi": [], "n": [], "instances": []}
        for f, m in groups:
            vals = {k[2]: v["mean"] for k, v in means.items() if k[0] == f and k[3] == m and k[4] == tag}
            a = agg(list(vals.values()))
            for fld in ("median", "lo", "hi", "n"):
                s[fld].append(a[fld])
            s["instances"].append(vals)
        out["series"][key] = s
    return out


def beta_of(inst: str) -> tuple[int, int]:
    m = BETA_RE.search(inst)
    if m is None:
        raise MissingKey(f"{FAM}: F3 instance {inst!r} has no _b<beta>_T<T> suffix")
    return int(m.group(1)), int(m.group(2))


def panel_b(means: Mapping) -> dict:
    f3 = {k: v for k, v in means.items() if k[0] == "F3"}
    betas = sorted({beta_of(k[2])[0] for k in f3})
    out = {"beta": betas, "modes": sorted({k[3] for k in f3}), "series": {}}
    for tag, key in TAG_KEY.items():
        s = {"beta": list(betas), "median": [], "lo": [], "hi": [], "n": [], "instances": []}
        for b in betas:
            vals = {k[2]: v["mean"] for k, v in f3.items() if k[4] == tag and beta_of(k[2])[0] == b}
            a = agg(list(vals.values()))
            for fld in ("median", "lo", "hi", "n"):
                s[fld].append(a[fld])
            s["instances"].append(vals)
        out["series"][key] = s
    return out


def equal_pairs(series: Mapping) -> list[list[str]]:
    """Pairs of drawn keys whose instance values are equal (SAME_TOL relative) at every instance of the panel."""
    out = []
    keys = list(SLOTS)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            ia, ib = series[a]["instances"], series[b]["instances"]
            pts = [(va.get(n), vb.get(n)) for va, vb in zip(ia, ib) for n in set(va) | set(vb)]
            if pts and all(x is not None and y is not None and abs(x - y) <= SAME_TOL * max(abs(x), abs(y), 1.0)
                           for x, y in pts):
                out.append([a, b])
    return out


def pairs_table(fam: Mapping, an: Mapping) -> dict:
    """H4's pairs grouped by family, instance set and lender (fam.pairs), checked against analysis.json's H4."""
    rows: dict = {}
    for p in need(fam, "fam", "pairs", what=FAM):
        src = "Q6" if str(p["src"]).startswith("F") else "fresh"
        counted = _counted({"fam": p["fam"], "src": p["src"], "mode": p["mode"]})
        r = rows.setdefault((p["fam"], src, p["mode"]), {"fam": p["fam"], "set": src, "mode": p["mode"],
                                                         "counted": counted, "pairs": 0, "equal": 0,
                                                         "sublet_projected_runs": 0, "instances": set(),
                                                         "seeds": set()})
        r["pairs"] += 1
        r["equal"] += bool(p.get("equal"))
        r["sublet_projected_runs"] += int(p.get("sublet_projected_runs") or 0)
        r["instances"].add(p["inst"])
        r["seeds"].add(p["seed"])
    out = []
    for key in sorted(rows, key=lambda k: (k[0], k[1] != "Q6", LENDERS.index(k[2]) if k[2] in LENDERS else 9)):
        r = rows[key]
        out.append({**r, "instances": len(r["instances"]), "seeds": sorted(r["seeds"])})
    h4 = need(an, "H4", what=ANALYSIS)
    n_counted = sum(r["pairs"] for r in out if r["counted"])
    if n_counted != h4.get("n_counted_pairs"):
        raise style.StyleError(f"{FAM}: {n_counted} counted pairs, analysis.json H4 has {h4.get('n_counted_pairs')}")
    return {"rows": out, "counted_pairs": n_counted, "equal_counted": sum(r["equal"] for r in out if r["counted"]),
            "identity_holds": h4.get("identity_holds"), "sublet_projected_runs": h4.get("sublet_projected_runs"),
            "pass": h4.get("pass"), "wording": h4.get("wording"), "counted_q6_modes": list(COUNTED_Q6_MODES)}


def f3_table(runs: Sequence[Mapping], means: Mapping, an: Mapping) -> dict:
    f3 = {k: v for k, v in means.items() if k[0] == "F3"}
    insts = sorted({(k[2], k[1], k[3]) for k in f3}, key=lambda t: (beta_of(t[0]), t[0]))
    tags = [t for t in TABLE_TAGS if any(k[4] == t for k in f3)]
    aborts: dict = {}
    for r in runs:
        if r.get("fam") == "F3" and (r.get("guard") or {}).get("aborted"):
            aborts[(r["inst"], r["tag"])] = aborts.get((r["inst"], r["tag"]), 0) + 1
    rows = []
    for inst, src, mode in insts:
        beta, T = beta_of(inst)
        cells = {}
        for t in tags:
            v = f3.get(("F3", src, inst, mode, t))
            cells[t] = None if v is None else {"mean": v["mean"], "n": v["n"],
                                               "aborts": aborts.get((inst, t), 0) if t in GUARDED else None}
        rows.append({"inst": inst, "set": "Q6" if src.startswith("F") else "fresh", "mode": mode, "beta": beta,
                     "T": T, "cells": cells})
    want = need(an, "H4", "f3_ratio_opt", what=ANALYSIS)
    overall = {}
    for t in tags:
        vals = [r["ratio_opt"] for r in runs if r.get("fam") == "F3" and r.get("tag") == t and r.get("status") == "ok"
                and r.get("ratio_opt") is not None]
        overall[t] = {"mean": statistics.fmean(vals) if vals else None, "n": len(vals),
                      "aborts": sum(aborts.get((i, t), 0) for i, _, _ in insts) if t in GUARDED else None}
        w = want.get(t) or {}
        if vals and (w.get("n") != len(vals) or abs(float(w.get("mean")) - overall[t]["mean"]) > 1e-9):
            raise style.StyleError(f"{FAM}: F3 mean ALG/OPT of {t} differs from analysis.json H4.f3_ratio_opt")
    return {"tags": tags, "rows": rows, "overall": overall}


GUARDED = ("Sublet", "BL1-GP", "BL1-G", "BL5-G")


Q6_MODES = ("F-ad", "F-eg")      # §6: the Q6 family runs under F-ad and F-eg, reported in full (fam_v2_q6.tex)


def q6_table(means: Mapping) -> dict:
    keys = {k for k in means if str(k[1]).startswith("F") and k[3] in Q6_MODES}
    insts = sorted({(k[0], k[2], k[3]) for k in keys},
                   key=lambda t: (t[0], LENDERS.index(t[2]), [int(x) for x in re.findall(r"\d+", t[1])]))
    tags = [t for t in TABLE_TAGS if any(k[4] == t for k in keys)]
    rows = [{"fam": f, "inst": i, "mode": m,
             "cells": {t: (None if (v := means.get((f, f, i, m, t))) is None else {"mean": v["mean"], "n": v["n"]})
                       for t in tags}} for f, i, m in insts]
    return {"tags": tags, "rows": rows}


def equal_classes(pairs: Sequence[Sequence[str]]) -> list[list[str]]:
    """The classes of keys joined by equal pairs (each class in SLOTS's order, the classes by their first key)."""
    cls: list[set] = []
    for a, b in pairs:
        hit = [c for c in cls if a in c or b in c]
        merged = set().union({a, b}, *hit)
        cls = [c for c in cls if c not in hit] + [merged]
    return sorted(([k for k in SLOTS if k in c] for c in cls), key=lambda c: SLOTS.index(c[0]))


def caption(d: Mapping) -> str:
    pt = d["tables"]["fam_v2_pairs"]
    eq = d["equal"]
    names = {k: style.POLICIES[k].label for k in SLOTS}
    same = []
    for p, pairs in (("(a)", eq["a"]), ("(b)", eq["b"])):
        if pairs:
            same.append(f"{p} " + "; ".join(" = ".join(names[k] for k in c) for c in equal_classes(pairs)))
    seeds = d["grid"]["seeds"]
    f3 = d["tables"]["fam_v2_f3"]["overall"]
    ab = [(t, o) for t, o in f3.items() if o.get("aborts") is not None and o.get("n")]
    lab = {t: style.POLICIES[TAG_KEY[t]].label for t, _ in ab}
    aborts = ""
    if ab:
        first, rest = ab[0], ab[1:]
        aborts = (f" On F3 {lab[first[0]]} aborts in {first[1]['aborts']} of its {first[1]['n']} runs"
                  + ("; " + "; ".join(f"{lab[t]} in {o['aborts']} of {o['n']}" for t, o in rest) if rest else "")
                  + " (Table fam_v2_f3).")
    return (f"The guard study's family instances and the confirmation's fresh instances (policy seeds "
            f"{min(seeds)}-{max(seeds)}): "
            f"ALG/OPT against the exact OPT, each instance's mean over its seeds, the median over the instances with "
            f"their range; (a) F1 and F2 by lender, (b) F3 against beta under the eager lender; {LABELS['order']}. "
            f"Critical-ratio renting equals RR-renew on {pt['equal_counted']} of the {pt['counted_pairs']} counted "
            f"pairs (H4), and Sublet projects in {pt['sublet_projected_runs']} of them; RR-renew and Marking are in "
            f"the tables."
            + (" Equal at every instance: " + "; ".join(same) + "." if same else "") + aborts)


def build(inp: Inputs) -> dict:
    fam, an = inp.json(FAM), inp.json(ANALYSIS)
    meta = need(fam, "meta", what=FAM)
    runs = [r for r in need(fam, "runs", what=FAM) if r.get("kind") == "fam"]
    if not runs:
        raise MissingKey(f"{FAM}: no family run")
    means = instance_means(runs)
    a, b = panel_a(means), panel_b(means)
    d = {"a": a, "b": b, "equal": {"a": equal_pairs(a["series"]), "b": equal_pairs(b["series"])},
         "grid": {"seeds": sorted({r["seed"] for r in runs}), "families": sorted({r["fam"] for r in runs}),
                  "modes": [m for m in LENDERS if any(r["mode"] == m for r in runs)],
                  "instances": len({(r["fam"], r["inst"]) for r in runs}), "runs": len(runs)},
         "tag_key": dict(TAG_KEY), "labels": dict(LABELS),
         "meta": {"git_revision": {"fam": meta.get("git_revision"),
                                   "analysis": (an.get("meta") or {}).get("git_revision")},
                  "reduced": bool(meta.get("reduced")), "sources": list(inp.sources), "runs_files": []}}
    pt, f3, q6 = pairs_table(fam, an), f3_table(runs, means, an), q6_table(means)
    pt["scope"] = {"families": sorted({r["fam"] for r in pt["rows"]}), "sets": sorted({r["set"] for r in pt["rows"]}),
                   "modes": [m for m in LENDERS if any(r["mode"] == m for r in pt["rows"])],
                   "seeds": sorted({s for r in pt["rows"] for s in r["seeds"]})}
    f3["scope"] = {"tags": list(f3["tags"]), "instances": [r["inst"] for r in f3["rows"]],
                   "modes": sorted({r["mode"] for r in f3["rows"]}),
                   "seeds": sorted({r["seed"] for r in runs if r["fam"] == "F3"})}
    q6_seeds = sorted({r["seed"] for r in runs if str(r["src"]).startswith("F") and r["mode"] in Q6_MODES})
    q6["scope"] = {"tags": list(q6["tags"]), "instances": [r["inst"] for r in q6["rows"]], "modes": list(Q6_MODES),
                   "seeds": q6_seeds}
    d["tables"] = {"fam_v2_pairs": {"file": TABLES[0], **pt}, "fam_v2_f3": {"file": TABLES[1], **f3},
                   "fam_v2_q6": {"file": TABLES[2], **q6}}
    d["labels"]["caption"] = caption(d)
    return d


# ---------------------------------------------------------------------------------------------------------------
# figure
def log_range(vals: Sequence[float]) -> tuple[float, float]:
    v = [x for x in vals if x is not None and x > 0]
    lo, hi = (min(v), max(v)) if v else (1.0, 2.0)
    return min(lo, 1.0) / 1.12, hi * 1.15


def log_ticks(lo: float, hi: float) -> list[float]:
    """Ticks 1, 2, 5, 10, 20 ... within [lo, hi] (at least 1)."""
    t = [m * 10.0 ** e for e in range(0, 4) for m in (1, 2, 5) if lo <= m * 10.0 ** e <= hi]
    return t or [1.0]


def draw_groups(ax, series: Mapping, labels: Sequence[str]) -> list[float]:
    """Markers at the categories 0..n-1 dodged into SLOTS (drawn in DRAW's order, Sublet last), with the instances'
    range as bars where it is not a point; returns the values drawn."""
    xs0 = np.arange(len(labels), dtype=float)
    n = len(SLOTS)
    vals = []
    for key in DRAW:
        s = series[key]
        x = xs0 + DODGE_GROUP * (SLOTS.index(key) - (n - 1) / 2)
        y, lo, hi = finite(s["median"]), finite(s["lo"]), finite(s["hi"])
        ok = np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi) & (hi > lo)
        if ok.any():
            style.errorbars(ax, key, x[ok], y[ok], lo[ok], hi[ok])
        style.scatter_policy(ax, key, x, y)
        vals += [v for v in np.concatenate([y, lo, hi]) if np.isfinite(v)]
    ax.set_xticks(list(xs0), list(labels))
    ax.set_xlim(-0.5, len(labels) - 0.5)
    ax.tick_params(axis="x", length=0)
    return vals


def draw_a(ax, a: Mapping) -> list[float]:
    """(a)'s categories, each on one line (C62: "F1, adaptive" for the group label "F1\\nadaptive")."""
    return draw_groups(ax, a["series"], [", ".join(g["label"].split("\n")) for g in a["groups"]])


def draw_b(ax, b: Mapping) -> list[float]:
    return draw_groups(ax, b["series"], [f"{float(v):g}" for v in b["beta"]])


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    ax_a, ax_b = style.panel_row(fig, WIDTHS, legend=2, sharey=(False, True))
    vals = draw_a(ax_a, data["a"]) + draw_b(ax_b, data["b"])
    lo, hi = log_range(vals)
    style.log_axis(ax_a, "y", ticks=log_ticks(lo, hi))
    ax_a.yaxis.set_minor_locator(NullLocator())       # C62: no comb of minor ticks on the short decades
    ax_a.set_ylim(lo, hi)
    for ax in (ax_a, ax_b):
        style.reference_line(ax, y=1.0)
        style.ygrid(ax)
    ax_a.set_ylabel(lab["a_y"])
    ax_a.set_xlabel(lab.get("a_x") or LABELS["a_x"])
    ax_b.set_xlabel(lab["b_x"])
    align_baselines([ax_a.xaxis.label, ax_b.xaxis.label])   # C62: (b)'s mathtext label on (a)'s baseline
    letters = style.panel_letters([ax_a, ax_b])
    for ax, letter, p in zip((ax_a, ax_b), letters, ("a", "b")):
        caption_title(ax, letter, lab["titles"][p])
    with matplotlib.rc_context({"legend.handlelength": LEGEND_HANDLE}):
        style.legend_row(fig, KEYS, rows=2, lines=False)
    return fig


# ---------------------------------------------------------------------------------------------------------------
# tables
def _label(tag: str) -> str:
    return tex_label(style.POLICIES[TAG_KEY.get(tag) or TABLE_LABEL[tag]].label)


def _hdr(tag: str) -> str:
    return r"\multicolumn{1}{>{\raggedleft\arraybackslash}p{" + HDR_W + "}}{" + _label(tag) + "}"


HDR_W = "1.55cm"                # the tables' policy columns (the header wraps; needs the array package)


def pairs_tex(t: Mapping) -> str:
    lines = [r"\begin{table}[t]",
             r"\caption{H4's pairs of critical-ratio renting and RR-renew on the families F1 and F2, by family, "
             r"instance set (the guard study's family instances or the confirmation's fresh instances) and lender: "
             r"the pairs (instance and policy "
             r"seed), those with equal total cost and purchase count, whether H4 counts them (fresh instances, and the "
             r"guard study's family instances under the "
             + " and ".join(LENDER_NAME.get(m, _tex_text(m)) for m in t["counted_q6_modes"])
             + r" lenders; under the fixed adaptive and eager lenders the runs on the guard study's family instances "
             r"of a policy without random draws repeat the pilot's runs), and Sublet's runs with a projected "
             r"slot. "                                                     # C50: the paper's words for P3 (D5 review)
             + f"{t['equal_counted']} of the {t['counted_pairs']} counted pairs are equal and Sublet projects in "
             + f"{t['sublet_projected_runs']} of them; H4 {'holds' if t['pass'] else 'fails'}." + "}",
             # C59: 3.0 pt (as built 3.4 pt), so that the set "guard study" (as built "Q6") keeps a column's width
             r"\label{tab:fam-v2-pairs}", r"\centering\footnotesize", r"\setlength{\tabcolsep}{3.0pt}",
             r"\begin{tabular}{@{}lllrrrcr@{}}", r"\toprule",
             r"Family & Set & Lender & Inst. & Pairs & Equal & Counted & Sublet proj. \\", r"\midrule"]
    for r in t["rows"]:
        lines.append(f"{r['fam']} & {SET_TEXT.get(r['set'], r['set'])} & "                             # C59
                     f"{LENDER_NAME.get(r['mode'], _tex_text(r['mode']))} & "
                     f"{r['instances']} & {r['pairs']} & {r['equal']} & {'yes' if r['counted'] else 'no'} & "
                     f"{r['sublet_projected_runs']} \\\\")
    lines += [r"\midrule",
              f"Counted &  &  &  & {t['counted_pairs']} & {t['equal_counted']} &  & {t['sublet_projected_runs']} \\\\",
              r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def f3_tex(t: Mapping) -> str:
    tags = t["tags"]
    cols = "@{}ll" + "r" * len(tags) + "@{}"
    lines = [r"\begin{table*}[t]",
             r"\caption{F3 (the insurance family of Proposition~\ref{prop:insurance}) under the eager lender: per instance ($\beta$, horizon $T$) the "
             r"mean ALG/OPT over the policy seeds against the exact OPT, with the guarded policies' aborting runs in "
             r"parentheses, and each policy's mean over all its F3 runs (the pre-registered analysis, H4); set: the "
             r"guard study's family instances or the confirmation's fresh instances. No "                  # C59
             r"criterion (H4: reported against the guarded baselines and the inner policy alone).}",
             r"\label{tab:fam-v2-f3}", r"\centering\footnotesize", r"\setlength{\tabcolsep}{3.4pt}",
             r"\begin{tabular}{" + cols + "}", r"\toprule",
             r"Instance & Set & " + " & ".join(_hdr(tg) for tg in tags) + r" \\", r"\midrule"]

    def cell(c):
        if c is None:
            return "--"
        a = "" if c.get("aborts") is None else f" ({c['aborts']})"
        return tex_f(c["mean"]) + a

    for r in t["rows"]:
        lines.append(f"$\\beta={r['beta']}$, $T={r['T']}$ & {SET_TEXT.get(r['set'], r['set'])} & "  # C59
                     + " & ".join(cell(r["cells"][tg])
                                                                                    for tg in tags) + r" \\")
    lines += [r"\midrule", r"Mean over the runs &  & " + " & ".join(cell(t["overall"][tg]) for tg in tags) + r" \\",
              r"Runs &  & " + " & ".join(str(t["overall"][tg]["n"]) for tg in tags) + r" \\",
              r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    return "\n".join(lines)


ONE_CONTRACT = ("RR_RENEW", "MARKING")      # family.py: one client, one LLM, one revocable contract (T4/O1)


def q6_dashes(t: Mapping) -> str:
    """The caption's sentence on the table's dashes: which policies did not run on which families (from the rows),
    with the reason where they are RR-renew and Marking on F3, whose instance has two contracts
    (check_c4_lower.single(T, [(1, 1), (T, 0)], ...): a revocable and a protected one); '' without a dash."""
    miss: dict = {}
    for r in t["rows"]:
        for tg in t["tags"]:
            if r["cells"][tg] is None:
                miss.setdefault(tg, set()).add(r["fam"])
    if not miss:
        return ""
    names = [style.POLICIES[TABLE_LABEL.get(tg) or TAG_KEY[tg]].label for tg in miss]
    fams = sorted(set().union(*miss.values()))
    why = (", since they take the one revocable contract of the single-LLM family and F3's instances offer a "  # C50
           "revocable and a protected contract" if set(miss) <= set(ONE_CONTRACT) and fams == ["F3"] else "")
    return " A dash marks a policy that did not run: " + " and ".join(names) + " on " + " and ".join(fams) + why + "."


ID_RE = {"m": re.compile(r"_m(\d+)_r(\d+(?:\.\d+)?)$"), "b": BETA_RE}


def q6_ids(t: Mapping) -> str:
    """The caption's key to the instance ids, by an example of each kind among the rows (F1/F2: m and rho; F3: beta
    and T)."""
    parts = []
    for kind, (a, b) in (("m", (r"$m=", r"$, $\rho=")), ("b", (r"$\beta=", r"$, horizon $T="))):
        ex = next((r["inst"] for r in t["rows"] if ID_RE[kind].search(r["inst"])), None)
        if ex is not None:
            g = ID_RE[kind].search(ex)
            # \textnormal: the caption's small capitals would print the id's lowercase letters unlike the table body
            parts.append(r"\textnormal{" + _tex_text(ex) + "}: " + a + g.group(1) + b + g.group(2) + "$")
    return (" An instance id gives its parameters, e.g. " + "; ".join(parts) + ".") if parts else ""


def q6_tex(t: Mapping) -> str:
    tags = t["tags"]
    cols = "@{}ll" + "r" * len(tags) + "@{}"
    lines = [r"\begin{table*}[t]",
             r"\caption{The guard study's family instances under the fixed lenders (adaptive for F1, eager for F2 "
             r"and F3; "
             r"lender seed 0): per instance the mean ALG/OPT over the policy seeds of every policy that ran there. "
             r"A policy without random draws (critical-ratio renting, its ablation without insurance and RR-renew) "
             r"gives one run per instance, and its runs repeat the pilot's runs (not new evidence); reported in full "
             r"with no "                                                   # C50: the paper's words for P3 (D5 review)
             r"criterion." + q6_ids(t) + _tex_text(q6_dashes(t)) + "}",
             r"\label{tab:fam-v2-q6}", r"\centering\footnotesize", r"\setlength{\tabcolsep}{3.4pt}",
             r"\begin{tabular}{" + cols + "}", r"\toprule",
             r"Instance & Lender & " + " & ".join(_hdr(tg) for tg in tags) + r" \\", r"\midrule"]
    prev = None
    for r in t["rows"]:
        if prev is not None and r["fam"] != prev:
            lines.append(r"\addlinespace[2pt]")
        prev = r["fam"]
        lines.append(f"{_tex_text(r['inst'])} & {LENDER_NAME.get(r['mode'], _tex_text(r['mode']))} & "
                     + " & ".join("--" if r["cells"][tg] is None else tex_f(r["cells"][tg]["mean"]) for tg in tags)
                     + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    return "\n".join(lines)


def write_tables(data: Mapping, report: Mapping) -> None:
    t = data["tables"]
    head = f"% Written by code/sim/figs/supp/{NAME}.py from {FAM} and {ANALYSIS}; do not edit.\n"
    paths = [write_table(TABLES[0], head + pairs_tex(t["fam_v2_pairs"])),
             write_table(TABLES[1], head + f3_tex(t["fam_v2_f3"])),
             write_table(TABLES[2], head + q6_tex(t["fam_v2_q6"]))]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
