"""MS7 unit B4's analysis: the quantities of Sublet's own sensitivity and fidelity studies from the summaries of
s1v2, e5v2, e8v2 and e9v2 (design/ms7/plan.md X3, D6; design/ms7/feasibility/sens.md §2 A-D; change C56). Its sha256
is recorded in design/ms7/registration.md before the runs, and the four drivers refuse a full run unless the file
still has it (s1v2.gate); so every rule below is fixed, deterministic and complete. The runs are exploratory (after
the MS5b freeze); nothing here is a confirmation result, and no p-value is computed (the weeks are rotations of one
series, plan D4).

  python -m sublet.experiments.ms7_sens_analysis [--exp s1v2 e5v2 e8v2 e9v2] [--root DIR]

Inputs (<root> as ms3_common.ms3_root): out/s1v2/sweep/summary.json and out/s1v2/w0/summary.json, out/e5v2/
summary.json, out/e8v2/a/summary.json, out/e9v2/summary.json (a missing input leaves its experiment's analysis with a
note). Outputs: out/<exp>/analysis.json and analysis.md for each experiment asked (meta: the inputs' sha256 and the git
revision; no time stamp).

Rules (r0 is a run's overflow cost over BL0a, policy seed 0; weeks are the summaries' weeks; PAIR = (BL1-BO,
BL5-cur), the per-week best of H1's set in every confirmation week):
  saving       100 (1 - r0) percent, per week and its median over the weeks
  Delta_w      min over a comparison set of r0(w, tag) - r0(w, Sublet) (ms5b_common.paired_margins), i.e. Sublet's
               saving minus the best saving of the set; None (a loss) when a run of the week is missing
  weeks_hold   the number of weeks with Delta_w > 0 (H1's ordering on that set; a loss does not hold), of n_weeks
  S1 v2        per point (the sweep's points and the reused points buf999, q28_rf, q28_vr): each tag's savings, Delta
               and weeks_hold against PAIR, Sublet - A9 (r0, the price of the guard) by week and its median; per row
               the lowest and highest median saving of Sublet over its points and the default, and the points at which
               the ordering fails in a week (flips). Part w0: per point (the load-scenario and fee points, and the
               default from part main) and week, each tag's W0 (the largest r0 over the five stress modes) and whether
               Sublet's W0 is below 1 and below the W0 of every tag of W0_SET (H2's ordering on these tags). The seed
               spread that justifies policy seed 0 (feasibility §1.2, read from the confirmation: out/sublet_v2/main
               and seeds, weeks 301-304, every mode): per tag of part seeds, the largest |r0 at seed k - r0 at seed
               0| with its cell, and the pairs counted and missing.
  E5 v2        per (level, menu) at mu 1 and per mu at (trace, short): each tag's savings, Delta and weeks_hold
               against PAIR and against every baseline present (E5_BASELINES), and BL3-2 - BL3-0 (r0; the spares'
               effect) by week.
  E8 v2        per (tier, window, alignment): C_fluid, C_replay and E per tag (A6 from E8's stored runs), the fluid and
               the replayed ranking of the four tags (by cost, ties by name; None while a cost is missing) and of the
               four with A6, whether they agree, Sublet's rank among the four in each, and its margin against PAIR in
               each (min over PAIR of C minus Sublet's C, USD, and over that baseline's C); per (tier, window) the
               counts over the alignments (n: those with both four-tag rankings); per Mooncake hour (window, prefix)
               the same on the hour's costs.
  E9 v2        per point and alignment: the act time per slow slot (policy_act_s_mean) and the slow step per slot
               (slow_loop_s_per_h x hours / n_slow_steps) of Sublet and A9 and their differences, the guard's
               per-slot overhead (Sublet - A9) and Sublet's over A9's; the medians over the alignments; and, where the
               split run equals its uninstrumented run, the split's per-slot guard parts.
Each analysis ends with its block 'headline', the values the text reports (the reading of the earlier claims rows
S1-4, E8-4, E9-1 and E9-5 on Sublet v2; s1_headline, analyse_w0, e5_headline, e8_headline and e9_headline state them),
so that the values registry can point at analysis.json.

Provenance (meta): this file's sha256 beside the one design/ms7/registration.md records on its line
'ms7_sens_analysis_sha256: <64 hex>' (read from the repository's working tree; s1v2.REG_SHA_RE's line) and whether
they match, and per input summary its sha256, git revision, whether it is reduced and the gate it records (ok,
enforced); 'registered_full_inputs' is true only when the sha256 matches and every input exists, is a full run and
recorded an enforced gate that passed. A mismatch is also printed to stderr, so that an analysis changed after the runs,
or one run on summaries that did not pass the gate, is visible in its own output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Mapping, Optional, Sequence

from .. import paths
from . import ms3_common as mc
from . import ms5b_common as m5

SPEC = "design/ms7/feasibility/sens.md §2 A-D (C56)"
REGISTRATION = "design/ms7/registration.md"        # s1v2.REGISTRATION
REG_SHA_RE = re.compile(r"^ms7_sens_analysis_sha256:\s*([0-9a-f]{64})\s*$", re.MULTILINE)    # s1v2.REG_SHA_RE
EXPS = ("s1v2", "e5v2", "e8v2", "e9v2")
INPUTS = {"s1v2": ("s1v2/sweep/summary.json", "s1v2/w0/summary.json"), "e5v2": ("e5v2/summary.json",),
          "e8v2": ("e8v2/a/summary.json",), "e9v2": ("e9v2/summary.json",)}
OUT_DIR = {"s1v2": "s1v2", "e5v2": "e5v2", "e8v2": "e8v2", "e9v2": "e9v2"}
CONF_DIR = paths.SIM_OUT / m5.CONF_DIR             # the confirmation's versioned outputs (s1v2.CONF_DIR)
CONF_INPUTS = ("main/summary.json", "seeds/summary.json")      # the seed spread's inputs (S1 v2)
TAGS4 = ("Sublet", "A9", "BL1-BO", "BL5-cur")
PAIR = ("BL1-BO", "BL5-cur")
W0_SET = ("BL1-BO", "BL5-cur", "BL4")
E5_BASELINES = ("BL1-BO", "BL5-cur", "BL3-0", "BL3-2")
E8_TAGS = TAGS4 + ("A6",)
REUSED_POINTS = ("buf999", "q28_rf", "q28_vr")
Q28_POINTS = ("q28_rf", "q28_vr")                  # Q28's stress variants: not register points (S1's rule)
DEFAULT = "default"
SPAN_PP = 10.0                                     # S1's S1-4: the rows whose span exceeds 10 percentage points
REAL_TIME_S_PER_H = 3600.0                         # e9.REAL_TIME_S_PER_H
LARGEST = {"full": "e7f_V64_SML", "reduced": "e7r_V64_SML"}     # e9.LARGEST: the largest run point of each menu


# ---------------------------------------------------------------- small rules
def saving(r0: Optional[float]) -> Optional[float]:
    return None if r0 is None else 100.0 * (1.0 - float(r0))


def median(xs) -> Optional[float]:
    v = [float(x) for x in xs if x is not None]
    return float(statistics.median(v)) if v else None


def margins(sub: Mapping, others: Mapping[str, Mapping], weeks: Sequence[str]) -> dict:
    """Delta_w over the comparison set `others` (ms5b_common.paired_margins), weeks_hold, the loss weeks and the
    median, minimum and maximum of Delta over the weeks without a loss."""
    pm = m5.paired_margins(sub, others, list(weeks))
    d = [x["delta"] for x in pm.values() if x["delta"] is not None]
    return {"by_week": pm, "n_weeks": len(weeks), "weeks_hold": sum(1 for x in pm.values()
                                                                     if x["delta"] is not None and x["delta"] > 0),
            "loss_weeks": [w for w, x in pm.items() if x["delta"] is None], "delta_median": median(d),
            "delta_min": min(d) if d else None, "delta_max": max(d) if d else None}


def tag_block(by_week: Mapping[str, Optional[float]]) -> dict:
    """{r0 by week, saving by week, median r0, median saving, n}."""
    return {"r0": dict(by_week), "saving_pct": {w: saving(v) for w, v in by_week.items()},
            "median_r0": median(by_week.values()), "median_saving_pct": median(saving(v) for v in by_week.values()),
            "n": sum(1 for v in by_week.values() if v is not None)}


def diff_by_week(a: Mapping, b: Mapping) -> dict:
    """{week: a - b} (None where either is missing) and its median."""
    d = {w: (None if a.get(w) is None or b.get(w) is None else float(a[w]) - float(b[w])) for w in a}
    return {"by_week": d, "median": median(d.values())}


def rank(costs: Mapping[str, Optional[float]]) -> Optional[list]:
    """The tags ordered by cost (ties by name); None while a cost is missing."""
    if not costs or any(v is None for v in costs.values()):
        return None
    return [t for t, _ in sorted(costs.items(), key=lambda kv: (float(kv[1]), kv[0]))]


def _r0(table: Mapping, tag: str, mode: str, point: str, week: str, seed: str = "0") -> Optional[float]:
    v = ((((table.get(tag) or {}).get(mode) or {}).get(point) or {}).get(week) or {}).get(seed)
    return None if v is None else float(v)


# ---------------------------------------------------------------- S1 v2
def seed_spread(main: Optional[Mapping], seeds: Optional[Mapping]) -> dict:
    """Policy seed 0 (part main) against the seeds of part seeds on the same weeks and modes: per tag of part seeds,
    the largest |r0(seed k) - r0(seed 0)| with its cell 'mode:week:seed' (the first on ties, in the files' order), the
    pairs counted and those with a run missing (feasibility §1.2; A9 is seed-free by construction)."""
    if main is None or seeds is None:
        return {"note": "the confirmation's main or seeds summary is missing"}
    mt, st = main.get("table") or {}, seeds.get("table") or {}
    by: dict = {}
    weeks, ks = set(), set()
    for t, modes in st.items():
        best, at, n, miss = None, None, 0, 0
        for mode, cells in (modes or {}).items():
            for w, xs in (cells or {}).items():
                r00 = ((((mt.get(t) or {}).get(mode) or {}).get(w)) or {}).get("0")
                weeks.add(w)
                for k, v in (xs or {}).items():
                    ks.add(k)
                    if v is None or r00 is None:
                        miss += 1
                        continue
                    n += 1
                    d = abs(float(v) - float(r00))
                    if best is None or d > best:
                        best, at = d, f"{mode}:{w}:{k}"
        by[t] = {"max_abs_diff": best, "at": at, "n_pairs": n, "n_missing": miss}
    return {"by_tag": by, "weeks": sorted(weeks), "seeds": sorted(ks), "reference_seed": "0",
            "sources": ["out/sublet_v2/main/summary.json", "out/sublet_v2/seeds/summary.json"]}


def analyse_s1v2(sweep: Optional[Mapping], w0: Optional[Mapping], conf: Optional[Sequence] = None) -> dict:
    """S1 v2's rules (module docstring); `conf` = (the confirmation's main summary, its seeds summary) for the seed
    spread (None: not computed)."""
    out: dict = {"points": {}, "rows": {}, "flips": [], "w0": None}
    if conf is not None:
        out["seed_spread"] = seed_spread(*conf)
    if sweep is None:
        out["note"] = "no s1v2/sweep/summary.json"
        return out
    weeks = [mc.num_key(c) for c in sweep["meta"]["grids"]["weeks"]]
    table = sweep.get("table") or {}
    pts = {}
    for name in list(sweep.get("points") or {}):
        pts[name] = {t: {w: _r0(table, t, "L-tr", name, w) for w in weeks} for t in TAGS4}
    for name, v in (sweep.get("reused") or {}).items():
        pts[name] = {t: {w: (v.get("by_tag") or {}).get(t, {}).get(w) for w in weeks} for t in TAGS4}
    for name, by in pts.items():
        e = {"by_tag": {t: tag_block(by[t]) for t in TAGS4},
             "vs_pair": margins(by["Sublet"], {t: by[t] for t in PAIR}, weeks),
             "a9_vs_pair": margins(by["A9"], {t: by[t] for t in PAIR}, weeks),
             "sublet_minus_a9_r0": diff_by_week(by["Sublet"], by["A9"])}
        meta_p = (sweep.get("points") or {}).get(name) or (sweep.get("reused") or {}).get(name) or {}
        e.update(row=meta_p.get("row"), value=meta_p.get("value"), label=meta_p.get("label"),
                 source="second" if name in (sweep.get("reused") or {}) else "s1v2")
        out["points"][name] = e
        vp = e["vs_pair"]
        if vp["weeks_hold"] < vp["n_weeks"]:
            out["flips"].append({"point": name, "row": e["row"], "weeks_hold": vp["weeks_hold"],
                                 "n_weeks": vp["n_weeks"], "loss_weeks": vp["loss_weeks"],
                                 "delta_median": vp["delta_median"]})
    dsav = (out["points"].get(DEFAULT) or {}).get("by_tag", {}).get("Sublet", {}).get("median_saving_pct")
    for row in sweep["meta"].get("rows_order") or []:
        names = [n for n, e in out["points"].items() if e.get("row") == row]
        if not names:
            continue
        cand = [(DEFAULT, dsav)] + [(n, out["points"][n]["by_tag"]["Sublet"]["median_saving_pct"]) for n in names]
        cv = [(n, v) for n, v in cand if v is not None]
        r = {"points": names, "default_saving_pct": dsav,
             "min_weeks_hold": min(out["points"][n]["vs_pair"]["weeks_hold"] for n in names),
             "points_with_flips": [n for n in names if out["points"][n]["vs_pair"]["weeks_hold"]
                                   < out["points"][n]["vs_pair"]["n_weeks"]]}
        if cv:
            lo = min(cv, key=lambda x: x[1])
            hi = max(cv, key=lambda x: x[1])
            r.update(lo=lo[1], lo_point=lo[0], hi=hi[1], hi_point=hi[0], span=hi[1] - lo[1])
        out["rows"][row] = r
    out["n_points"] = len(out["points"])
    out["n_points_all_weeks_hold"] = sum(1 for e in out["points"].values()
                                         if e["vs_pair"]["weeks_hold"] == e["vs_pair"]["n_weeks"])
    out["weeks"] = weeks
    out["headline"] = s1_headline(out)
    if w0 is not None:
        out["w0"] = analyse_w0(w0)
    else:
        out["w0_note"] = "no s1v2/w0/summary.json"
    return out


def _extreme(pairs: Sequence, fn) -> tuple:
    """(value, name) of the minimum or maximum (fn) over (name, value) pairs with a value; (None, None) without."""
    v = [(n, x) for n, x in pairs if x is not None]
    if not v:
        return None, None
    n, x = fn(v, key=lambda t: (t[1], t[0]))
    return x, n


def s1_headline(a: Mapping) -> dict:
    """The S1 v2 values the text reports (S1-4's reading on Sublet v2): over the register points (the sweep's points
    and buf999; Q28's variants apart) the number of points with Sublet's median saving, its lowest and highest
    median saving with their points, the default's, the rows whose span exceeds SPAN_PP, the points at which H1's
    ordering against PAIR holds in every week and the (point, week) pairs in which it holds; the same lowest and
    highest median savings of A9, BL1-BO and BL5-cur; the median over the register points of Sublet - A9 (r0); and
    Q28's variants by tag (median saving, weeks_hold)."""
    pts = {n: e for n, e in a["points"].items() if n not in Q28_POINTS}
    out: dict = {"register_points": sorted(pts), "n_points": sum(
        1 for e in pts.values() if e["by_tag"]["Sublet"]["median_saving_pct"] is not None)}
    for t in TAGS4:
        pairs = [(n, e["by_tag"][t]["median_saving_pct"]) for n, e in pts.items()]
        lo, lo_p = _extreme(pairs, min)
        hi, hi_p = _extreme(pairs, max)
        out[t] = {"lo": lo, "lo_point": lo_p, "hi": hi, "hi_point": hi_p,
                  "default": ((pts.get(DEFAULT) or {}).get("by_tag") or {}).get(t, {}).get("median_saving_pct")}
    spans = {r: x.get("span") for r, x in a["rows"].items() if r not in Q28_POINTS}
    out["max_span"], out["max_span_row"] = _extreme(list(spans.items()), max)
    out["rows_span_above"] = sorted(r for r, s in spans.items() if s is not None and s > SPAN_PP)
    out["span_threshold_pp"] = SPAN_PP
    out["points_all_weeks_hold"] = sum(1 for e in pts.values() if e["vs_pair"]["weeks_hold"] == e["vs_pair"]["n_weeks"])
    out["point_weeks_hold"] = sum(e["vs_pair"]["weeks_hold"] for e in pts.values())
    out["point_weeks"] = sum(e["vs_pair"]["n_weeks"] for e in pts.values())
    out["points_with_flips"] = sorted(n for n, e in pts.items() if e["vs_pair"]["weeks_hold"] < e["vs_pair"]["n_weeks"])
    out["sublet_minus_a9_r0_median"] = median(e["sublet_minus_a9_r0"]["median"] for e in pts.values())
    out["q28"] = {n: {"by_tag": {t: a["points"][n]["by_tag"][t]["median_saving_pct"] for t in TAGS4},
                      "weeks_hold": a["points"][n]["vs_pair"]["weeks_hold"],
                      "n_weeks": a["points"][n]["vs_pair"]["n_weeks"]} for n in Q28_POINTS if n in a["points"]}
    out["seed_spread_max"] = {t: x.get("max_abs_diff") for t, x in
                              ((a.get("seed_spread") or {}).get("by_tag") or {}).items()}
    return out


def analyse_w0(w0: Mapping) -> dict:
    weeks = [mc.num_key(c) for c in w0["meta"]["grids"]["weeks"]]
    W = w0.get("W0") or {}
    tags = list(TAGS4) + ["BL4"]
    pts = {}
    names = list((W.get("Sublet") or {}).keys())
    for name in names:
        pts[name] = {t: {w: ((W.get(t) or {}).get(name) or {}).get(w, {}).get("W0") for w in weeks} for t in tags}
    pts[DEFAULT] = {t: {w: (w0.get("reused_default_W0") or {}).get(t, {}).get(w) for w in weeks} for t in tags}
    out = {}
    for name, by in pts.items():
        hold = {}
        for w in weeks:
            s = by["Sublet"].get(w)
            o = [by[t].get(w) for t in W0_SET]
            hold[w] = None if s is None or any(x is None for x in o) else bool(s < 1.0 and all(s < x for x in o))
        out[name] = {"W0": by, "holds": hold, "weeks_hold": sum(1 for v in hold.values() if v),
                     "n_weeks": len(weeks), "sublet_W0_median": median(by["Sublet"].values()),
                     "source": "main" if name == DEFAULT else "s1v2"}
    sw = [(f"{n}:{w}", v) for n, e in out.items() for w, v in e["W0"]["Sublet"].items()]
    hi, hi_at = _extreme(sw, max)
    head = {"n_points": len(out),
            "points_all_weeks_hold": sum(1 for e in out.values() if e["weeks_hold"] == e["n_weeks"]),
            "points_with_failures": sorted(n for n, e in out.items() if e["weeks_hold"] < e["n_weeks"]),
            "point_weeks_hold": sum(e["weeks_hold"] for e in out.values()),
            "point_weeks": sum(e["n_weeks"] for e in out.values()), "sublet_W0_max": hi, "sublet_W0_max_at": hi_at,
            "sublet_W0_below_1": sum(1 for _n, v in sw if v is not None and v < 1.0),
            "n_sublet_W0": sum(1 for _n, v in sw if v is not None)}
    return {"points": out, "weeks": weeks, "set": list(W0_SET), "headline": head,
            "rule": "Sublet's W0 < 1 and below the W0 of every tag of the set, per week (a missing W0 fails)"}


# ---------------------------------------------------------------- E5 v2
def analyse_e5v2(s: Optional[Mapping]) -> dict:
    if s is None:
        return {"note": "no e5v2/summary.json"}
    weeks = [mc.num_key(c) for c in s["meta"]["grid"]["weeks"]]
    out: dict = {"cells": {}, "weeks": weeks}
    for lv, a in (s.get("cells") or {}).items():
        for menu, b in a.items():
            for mk, x in b.items():
                by = {t: {w: (x.get(t) or {}).get("by_c", {}).get(w) for w in weeks} for t in x}
                if "Sublet" not in by:
                    continue
                base = [t for t in E5_BASELINES if t in by]
                e = {"by_tag": {t: {**tag_block(v), "source": (x.get(t) or {}).get("source")} for t, v in by.items()},
                     "vs_pair": margins(by["Sublet"], {t: by[t] for t in PAIR if t in by}, weeks),
                     "vs_baselines": margins(by["Sublet"], {t: by[t] for t in base}, weeks), "baselines": base}
                if "A9" in by:
                    e["sublet_minus_a9_r0"] = diff_by_week(by["Sublet"], by["A9"])
                if "BL3-2" in by and "BL3-0" in by:
                    e["bl3_spares_r0"] = diff_by_week(by["BL3-2"], by["BL3-0"])
                out["cells"].setdefault(lv, {}).setdefault(menu, {})[mk] = e
    flips = [{"level": lv, "menu": mn, "mu": mk, "weeks_hold_pair": e["vs_pair"]["weeks_hold"],
              "weeks_hold_baselines": e["vs_baselines"]["weeks_hold"], "n_weeks": e["vs_pair"]["n_weeks"]}
             for lv, a in out["cells"].items() for mn, b in a.items() for mk, e in b.items()
             if e["vs_baselines"]["weeks_hold"] < e["vs_baselines"]["n_weeks"]]
    out["flips"] = flips
    out["headline"] = e5_headline(out["cells"])
    return out


def e5_headline(cells: Mapping) -> dict:
    """The E5 v2 values the text reports: over the cells (level:menu:mu) the number in which Sublet's ordering holds
    in every week against PAIR and against every baseline present, the (cell, week) pairs in which it holds, the cells
    of each kind of failure; at mu 1 Sublet's lowest and highest median saving with their cells; per (level, menu) at
    mu 1 the median of BL3-2 - BL3-0 (r0: the spares' effect, negative when the spares save) and Sublet's median
    saving against the best baseline's."""
    mu1 = mc.num_key(1.0)
    flat = {f"{lv}:{mn}:{mk}": (lv, mn, mk, e) for lv, a in cells.items() for mn, b in a.items()
            for mk, e in b.items()}
    out: dict = {"n_cells": len(flat)}
    for k in ("vs_pair", "vs_baselines"):
        out[k] = {"cells_all_weeks_hold": sum(1 for *_, e in flat.values()
                                              if e[k]["weeks_hold"] == e[k]["n_weeks"]),
                  "cells_with_failures": sorted(c for c, (*_, e) in flat.items()
                                                if e[k]["weeks_hold"] < e[k]["n_weeks"]),
                  "cell_weeks_hold": sum(e[k]["weeks_hold"] for *_, e in flat.values()),
                  "cell_weeks": sum(e[k]["n_weeks"] for *_, e in flat.values())}
    at1 = [(c, e["by_tag"]["Sublet"]["median_saving_pct"]) for c, (_lv, _mn, mk, e) in flat.items() if mk == mu1]
    out["sublet_saving_lo"], out["sublet_saving_lo_cell"] = _extreme(at1, min)
    out["sublet_saving_hi"], out["sublet_saving_hi_cell"] = _extreme(at1, max)
    out["bl3_spares_r0_median"] = {f"{lv}:{mn}": e["bl3_spares_r0"]["median"] for lv, mn, mk, e in flat.values()
                                   if mk == mu1 and e.get("bl3_spares_r0")}
    out["sublet_vs_best_baseline_median_delta"] = {c: e["vs_baselines"]["delta_median"] for c, (*_, e) in flat.items()}
    return out


# ---------------------------------------------------------------- E8 v2
def _pair_margin(costs: Mapping[str, Optional[float]]) -> dict:
    """min over PAIR of C minus Sublet's C (USD) and over that baseline's C; None while a cost is missing."""
    s = costs.get("Sublet")
    o = [costs.get(t) for t in PAIR]
    if s is None or any(x is None for x in o):
        return {"usd": None, "relative": None, "best": None}
    best = min(PAIR, key=lambda t: (float(costs[t]), t))
    m = float(costs[best]) - float(s)
    return {"usd": m, "relative": m / float(costs[best]) if costs[best] else None, "best": best}


def _rank_block(fl: Mapping, rp: Mapping) -> dict:
    """The rankings of the four tags (Sublet's rank among them) and of the four with A6, fluid and replayed."""
    rf, rr = rank({t: fl.get(t) for t in TAGS4}), rank({t: rp.get(t) for t in TAGS4})
    rf6, rr6 = rank({t: fl.get(t) for t in E8_TAGS}), rank({t: rp.get(t) for t in E8_TAGS})
    return {"fluid": fl, "replay": rp, "rank_fluid": rf, "rank_replay": rr,
            "same_order": None if rf is None or rr is None else rf == rr,
            "rank_fluid_with_a6": rf6, "rank_replay_with_a6": rr6,
            "same_order_with_a6": None if rf6 is None or rr6 is None else rf6 == rr6,
            "sublet_rank_fluid": None if rf is None else rf.index("Sublet") + 1,
            "sublet_rank_replay": None if rr is None else rr.index("Sublet") + 1,
            "margin_fluid": _pair_margin(fl), "margin_replay": _pair_margin(rp)}


def analyse_e8v2(s: Optional[Mapping]) -> dict:
    if s is None:
        return {"note": "no e8v2/a/summary.json"}
    out: dict = {"cells": {}, "by_tier_window": {}, "mooncake": {}}
    a6 = s.get("reused_a6") or {}
    for tier, a in (s.get("cells") or {}).items():
        for w, b in a.items():
            agg = {"n_alignments": 0, "n": 0, "same_order": 0, "sublet_first_fluid": 0, "sublet_first_replay": 0,
                   "sublet_beats_pair_fluid": 0, "sublet_beats_pair_replay": 0,
                   "E": {t: [] for t in E8_TAGS}}
            for c, x in b.items():
                ref = ((a6.get(tier) or {}).get(w) or {}).get(c) or {}
                fl = {t: (x.get(t) or {}).get("C_fluid") for t in TAGS4}
                rp = {t: (x.get(t) or {}).get("C_replay") for t in TAGS4}
                fl["A6"], rp["A6"] = ref.get("C_fluid"), ref.get("C_replay")
                e = _rank_block(fl, rp)
                e["E"] = {t: (x.get(t) or {}).get("error") for t in TAGS4}
                e["E"]["A6"] = ref.get("error")
                out["cells"].setdefault(tier, {}).setdefault(w, {})[c] = e
                agg["n_alignments"] += 1
                agg["n"] += int(e["rank_fluid"] is not None and e["rank_replay"] is not None)
                agg["same_order"] += int(e["same_order"] is True)
                agg["sublet_first_fluid"] += int(e["sublet_rank_fluid"] == 1)
                agg["sublet_first_replay"] += int(e["sublet_rank_replay"] == 1)
                agg["sublet_beats_pair_fluid"] += int((e["margin_fluid"]["usd"] or 0.0) > 0)
                agg["sublet_beats_pair_replay"] += int((e["margin_replay"]["usd"] or 0.0) > 0)
                for t in E8_TAGS:
                    agg["E"][t].append(e["E"].get(t))
            agg["E_median"] = {t: median(v) for t, v in agg.pop("E").items()}
            out["by_tier_window"].setdefault(tier, {})[w] = agg
    a6m = s.get("reused_a6_mooncake") or {}
    for w, a in (s.get("mooncake") or {}).items():
        for pf, x in a.items():
            ref = (a6m.get(w) or {}).get(pf) or {}
            fl = {t: (x.get(t) or {}).get("C_fluid") for t in TAGS4}
            rp = {t: (x.get(t) or {}).get("C_replay") for t in TAGS4}
            fl["A6"], rp["A6"] = ref.get("C_fluid"), ref.get("C_replay")
            e = _rank_block(fl, rp)
            e["E"] = {t: (x.get(t) or {}).get("error") for t in TAGS4}
            e["E"]["A6"] = ref.get("error")
            out["mooncake"].setdefault(w, {})[pf] = e
    out["headline"] = e8_headline(out)
    return out


def e8_headline(a: Mapping) -> dict:
    """The E8 v2 values the text reports (E8-4's reading per policy): per tag the lowest and highest median E over the
    (tier, window) cells with their cells (E: (C_replay - C_fluid) / C_replay, the median over the alignments); over
    the (tier, window, alignment) cells the number with both four-tag rankings, with the same fluid and replayed
    order, with Sublet first, and with Sublet below both of PAIR, fluid and replayed; per prefix of the Mooncake hour
    the windows with the same order and with Sublet first when replayed."""
    out: dict = {"E_median_range": {}}
    for t in E8_TAGS:
        pairs = [(f"{tier}:{w}", x["E_median"].get(t)) for tier, y in a["by_tier_window"].items() for w, x in y.items()]
        lo, lo_c = _extreme(pairs, min)
        hi, hi_c = _extreme(pairs, max)
        out["E_median_range"][t] = {"lo": lo, "lo_cell": lo_c, "hi": hi, "hi_cell": hi_c,
                                    "n_cells": sum(1 for _c, v in pairs if v is not None)}
    keys = ("n_alignments", "n", "same_order", "sublet_first_fluid", "sublet_first_replay", "sublet_beats_pair_fluid",
            "sublet_beats_pair_replay")
    out["cells"] = {k: sum(x[k] for y in a["by_tier_window"].values() for x in y.values()) for k in keys}
    out["cells_reordered"] = sorted(f"{tier}:{w}:{c}" for tier, y in a["cells"].items() for w, z in y.items()
                                    for c, e in z.items() if e["same_order"] is False)
    out["mooncake"] = {}
    for w, y in a["mooncake"].items():
        for pf, e in y.items():
            m = out["mooncake"].setdefault(pf, {"n": 0, "same_order": 0, "sublet_first_replay": 0, "E_sublet": {}})
            m["n"] += int(e["rank_fluid"] is not None and e["rank_replay"] is not None)
            m["same_order"] += int(e["same_order"] is True)
            m["sublet_first_replay"] += int(e["sublet_rank_replay"] == 1)
            m["E_sublet"][w] = e["E"].get("Sublet")
    return out


# ---------------------------------------------------------------- E9 v2
def _per_slot_step(x: Mapping) -> Optional[float]:
    v, h, n = x.get("slow_loop_s_per_h"), x.get("hours"), x.get("n_slow_steps")
    if v is None or h is None or not n:
        return None
    return float(v) * float(h) / float(n)


def analyse_e9v2(s: Optional[Mapping]) -> dict:
    if s is None:
        return {"note": "no e9v2/summary.json"}
    out: dict = {"points": {}}
    for p, e in (s.get("points") or {}).items():
        pol = e.get("policies") or {}
        sb = (pol.get("Sublet") or {}).get("by_alignment") or {}
        ab = (pol.get("A9") or {}).get("by_alignment") or {}
        by = {}
        for c in sorted(set(sb) | set(ab), key=int):
            x, y = sb.get(c) or {}, ab.get(c) or {}
            act_s, act_a = x.get("policy_act_s_mean"), y.get("policy_act_s_mean")
            st_s, st_a = _per_slot_step(x), _per_slot_step(y)
            by[c] = {"act_s_per_slot": {"Sublet": act_s, "A9": act_a},
                     "act_overhead_s_per_slot": None if act_s is None or act_a is None else act_s - act_a,
                     "act_ratio": None if not act_s or not act_a else act_s / act_a,
                     "slow_step_s_per_slot": {"Sublet": st_s, "A9": st_a},
                     "slow_step_overhead_s_per_slot": None if st_s is None or st_a is None else st_s - st_a,
                     "slow_loop_s_per_h": {"Sublet": x.get("slow_loop_s_per_h"), "A9": y.get("slow_loop_s_per_h")},
                     "projected_slots": x.get("projected_slots")}
        sp = e.get("split") or {}
        out["points"][p] = {
            "sites_x_llms": e.get("sites_x_llms"), "by_alignment": by,
            "act_overhead_s_per_slot_median": median(v["act_overhead_s_per_slot"] for v in by.values()),
            "slow_step_overhead_s_per_slot_median": median(v["slow_step_overhead_s_per_slot"] for v in by.values()),
            "act_ratio_median": median(v["act_ratio"] for v in by.values()),
            "split": {"c": sp.get("c"), "identical": sp.get("identical"),
                      "per_slot_mean_s": ((sp.get("split") or {}).get("per_slot_mean_s"))} if sp else None}
    out["headline"] = e9_headline(s, out)
    return out


def _real_time(loops_s_per_h) -> Optional[float]:
    return None if loops_s_per_h is None or not float(loops_s_per_h) > 0 else REAL_TIME_S_PER_H / float(loops_s_per_h)


def e9_headline(s: Mapping, a: Mapping) -> dict:
    """The E9 v2 values the text reports (E9-5's and E9-1's reading on Sublet v2): at the largest run point of each
    menu its sites x LLMs and, per tag, real time over the median seconds per simulated hour of the slow and fast loops
    (3,600 / loops_s_per_h, e9.check_e9_5's rule) and the median peak memory; there and over every point the guard's
    per-slot overhead (the medians of Sublet - A9 in act time per slow slot), its largest value with its point and the
    largest act ratio; the memory cap with the runs over it (E9v2-1) and the largest peak memory of any run."""
    pts = s.get("points") or {}
    out: dict = {"largest_point_by_menu": {}}
    for menu, p in LARGEST.items():
        e = pts.get(p) or {}
        pol = e.get("policies") or {}
        out["largest_point_by_menu"][menu] = {
            "point": p, "sites_x_llms": e.get("sites_x_llms"),
            "policies": {t: {"loops_s_per_h": ((pol.get(t) or {}).get("median") or {}).get("loops_s_per_h"),
                             "real_time_over_loops": _real_time(((pol.get(t) or {}).get("median") or {})
                                                                .get("loops_s_per_h")),
                             "peak_rss_mb": ((pol.get(t) or {}).get("median") or {}).get("peak_rss_mb")}
                         for t in ("Sublet", "A9")},
            "act_overhead_s_per_slot_median": (a["points"].get(p) or {}).get("act_overhead_s_per_slot_median"),
            "act_ratio_median": (a["points"].get(p) or {}).get("act_ratio_median")}
    ov = [(p, e["act_overhead_s_per_slot_median"]) for p, e in a["points"].items()]
    out["act_overhead_s_per_slot_max"], out["act_overhead_s_per_slot_max_point"] = _extreme(ov, max)
    rt = [(p, e["act_ratio_median"]) for p, e in a["points"].items()]
    out["act_ratio_max"], out["act_ratio_max_point"] = _extreme(rt, max)
    peaks = [(f"{p}:{t}", ((pe.get("max") or {}).get("peak_rss_mb"))) for p, e in pts.items()
             for t, pe in (e.get("policies") or {}).items()]
    out["peak_rss_mb_max"], out["peak_rss_mb_max_at"] = _extreme(peaks, max)
    c1 = (s.get("checks") or {}).get("E9v2-1") or {}
    out.update(cap_mb=c1.get("cap_mb"), n_over_cap=c1.get("n_over_cap"), n_runs=c1.get("n_runs"),
               e9v2_1_status=c1.get("status"))
    return out


ANALYSES = {"s1v2": lambda d, c: analyse_s1v2(d[0], d[1], c), "e5v2": lambda d, c: analyse_e5v2(d[0]),
            "e8v2": lambda d, c: analyse_e8v2(d[0]), "e9v2": lambda d, c: analyse_e9v2(d[0])}


# ---------------------------------------------------------------- outputs
def _md(exp: str, a: Mapping) -> str:
    L = [f"# {exp}: analysis ({SPEC})", "", "Exploratory, after the MS5b freeze (design/ms7/plan.md D6).", ""]
    m = a.get("meta") or {}
    rg = m.get("registration") or {}
    if m:
        L += [f"Analysis sha256 {str(m.get('analysis_sha256'))[:12]}; {rg.get('path')} records "
              f"{str(rg.get('registered_sha256'))[:12]}; matches {rg.get('matches')}; registered full inputs "
              f"{m.get('registered_full_inputs')}.", ""]
    if a.get("note"):
        return "\n".join(L + [a["note"], ""]) + "\n"
    if exp == "s1v2":
        rows = [[n, e.get("row"), e["by_tag"]["Sublet"]["median_saving_pct"], e["by_tag"]["A9"]["median_saving_pct"],
                 e["by_tag"]["BL1-BO"]["median_saving_pct"], e["by_tag"]["BL5-cur"]["median_saving_pct"],
                 e["vs_pair"]["delta_median"], f"{e['vs_pair']['weeks_hold']}/{e['vs_pair']['n_weeks']}"]
                for n, e in a["points"].items()]
        L += ["## Points (median saving %, Delta = Sublet - best of BL1-BO and BL5-cur in r0 terms)", "",
              mc.md_table(["point", "row", "Sublet", "A9", "BL1-BO", "BL5-cur", "Delta median", "weeks hold"], rows),
              ""]
        if a.get("w0"):
            rows = [[n, e["sublet_W0_median"], f"{e['weeks_hold']}/{e['n_weeks']}", e["source"]]
                    for n, e in a["w0"]["points"].items()]
            L += ["## W0 (Sublet's median W0; weeks with Sublet's W0 < 1 and below BL1-BO, BL5-cur and BL4)", "",
                  mc.md_table(["point", "Sublet W0", "weeks hold", "source"], rows), ""]
        ss = (a.get("seed_spread") or {}).get("by_tag") or {}
        if ss:
            rows = [[t, x["max_abs_diff"], x["at"], x["n_pairs"], x["n_missing"]] for t, x in ss.items()]
            L += ["## Seed spread (largest |r0 at seed k - r0 at seed 0|; the confirmation's parts main and seeds)", "",
                  mc.md_table(["tag", "max |diff|", "at", "pairs", "missing"], rows), ""]
    elif exp == "e5v2":
        rows = [[lv, mn, mk, e["by_tag"]["Sublet"]["median_saving_pct"], e["vs_pair"]["delta_median"],
                 f"{e['vs_pair']['weeks_hold']}/{e['vs_pair']['n_weeks']}", e["vs_baselines"]["delta_median"],
                 f"{e['vs_baselines']['weeks_hold']}/{e['vs_baselines']['n_weeks']}"]
                for lv, x in a["cells"].items() for mn, y in x.items() for mk, e in y.items()]
        L += ["## Cells (Sublet's median saving %; Delta against the pair and against every baseline)", "",
              mc.md_table(["level", "menu", "mu", "Sublet", "Delta pair", "hold", "Delta all", "hold"], rows), ""]
    elif exp == "e8v2":
        rows = [[t, w, x["n"], x["same_order"], x["sublet_first_fluid"], x["sublet_first_replay"],
                 x["E_median"].get("Sublet")] for t, y in a["by_tier_window"].items() for w, x in y.items()]
        L += ["## Rankings over the alignments (counts) and Sublet's median E", "",
              mc.md_table(["tier", "window", "n", "same order", "Sublet first (fluid)", "Sublet first (replay)",
                           "E Sublet"], rows), ""]
        rows = [[w, pf, e["same_order"], e["sublet_rank_fluid"], e["sublet_rank_replay"], e["E"].get("Sublet")]
                for w, y in a["mooncake"].items() for pf, e in y.items()]
        L += ["## Mooncake hour", "", mc.md_table(["window", "prefix", "same order", "Sublet rank (fluid)",
                                                   "Sublet rank (replay)", "E Sublet"], rows), ""]
    elif exp == "e9v2":
        rows = [[p, e["sites_x_llms"], e["act_overhead_s_per_slot_median"], e["act_ratio_median"],
                 e["slow_step_overhead_s_per_slot_median"],
                 ((e.get("split") or {}).get("per_slot_mean_s") or {}).get("guard")] for p, e in a["points"].items()]
        L += ["## The guard's per-slot overhead (Sublet - A9; medians over the alignments; split if identical)", "",
              mc.md_table(["point", "sites x LLMs", "act s/slot", "act ratio", "slow step s/slot", "split guard s"],
                          rows), ""]
    for name, h in (("headline", a.get("headline")), ("W0 headline", (a.get("w0") or {}).get("headline"))):
        if h:
            L += [f"## {name[0].upper() + name[1:]}", "", "```json", json.dumps(h, indent=1, sort_keys=True), "```", ""]
    return "\n".join(L) + "\n"


def registration(sha: str, repo=None) -> dict:
    """This file's sha256 against the one design/ms7/registration.md records (read from the working tree of `repo`,
    default this repository): {path, exists, registered_sha256, analysis_sha256, matches}."""
    f = Path(repo if repo is not None else paths.REPO) / REGISTRATION
    text = f.read_text(encoding="utf-8", errors="replace") if f.is_file() else None
    m = REG_SHA_RE.search(text) if text else None
    want = m.group(1) if m else None
    return {"path": REGISTRATION, "exists": f.is_file(), "registered_sha256": want, "analysis_sha256": sha,
            "matches": want is not None and want == sha}


def input_record(rel: str, f: Path, d: Optional[Mapping]) -> dict:
    """One input summary's provenance: sha256, git revision, reduced, and the gate it records (ok, enforced)."""
    m = (d or {}).get("meta") or {}
    g = m.get("gate") or {}
    return {"file": f"out/{rel}", "exists": f.is_file(),
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None,
            "git_revision": m.get("git_revision"), "reduced": bool(m.get("reduced")), "gate_kind": g.get("kind"),
            "gate_ok": g.get("ok"), "gate_enforced": g.get("enforced")}


def run_analysis(exps: Sequence[str] = EXPS, root=None, repo=None, conf_dir=None) -> dict:
    """Each experiment's analysis from its summaries under <root>/out/ (S1 v2's seed spread also from the
    confirmation's summaries under `conf_dir`, default CONF_DIR), written to out/<exp>/analysis.json and analysis.md,
    with the provenance of the module docstring; returns {exp: analysis}."""
    r = mc.ms3_root(root) / "out"
    sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    reg = registration(sha, repo)
    cd = Path(conf_dir) if conf_dir is not None else CONF_DIR
    res = {}
    for exp in exps:
        files = [r / f for f in INPUTS[exp]]
        data = [mc.read_json(f) for f in files]
        ins = [input_record(x, f, d) for x, f, d in zip(INPUTS[exp], files, data)]
        full = bool(reg["matches"]) and all(x["exists"] and not x["reduced"] and x["gate_ok"] is True
                                            and x["gate_enforced"] is True for x in ins)
        conf, conf_in = None, {}
        if exp == "s1v2":
            cf = [cd / x for x in CONF_INPUTS]
            conf = [mc.read_json(f) for f in cf]
            conf_in = {f"out/{m5.CONF_DIR}/{x}": (hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None)
                       for x, f in zip(CONF_INPUTS, cf)}
        a = ANALYSES[exp](data, conf)
        a = {"meta": {"exp": exp, "spec": SPEC, "change": "C56", "git_revision": mc.git_revision(),
                      "analysis_sha256": sha, "registration": reg,
                      "inputs": {x["file"]: x["sha256"] for x in ins}, "input_records": ins,
                      "confirmation_inputs": conf_in,
                      "reduced": any(x["reduced"] for x in ins), "registered_full_inputs": full,
                      "label": "exploratory: post-freeze runs on the confirmation weeks (design/ms7/plan.md D6)"},
             **a}
        if not full:
            print(f"[ms7_sens] {exp}: not a registered full analysis (registration matches {reg['matches']}; inputs "
                  + ", ".join(f"{x['file']} exists {x['exists']} reduced {x['reduced']} gate ok {x['gate_ok']} "
                              f"enforced {x['gate_enforced']}" for x in ins) + ")", file=sys.stderr)
        od = r / OUT_DIR[exp]
        od.mkdir(parents=True, exist_ok=True)
        mc.dump_json(a, od / "analysis.json")
        mc.write_text(_md(exp, a), od / "analysis.md")
        res[exp] = a
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.ms7_sens_analysis", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exp", nargs="+", choices=EXPS, default=list(EXPS))
    ap.add_argument("--root", default=None)
    a = ap.parse_args(argv)
    res = run_analysis(a.exp, a.root)
    for exp, x in res.items():
        print(f"[ms7_sens] {exp}: {'; '.join(k for k in x if k != 'meta')}" + (f" ({x['note']})" if x.get("note")
                                                                               else ""), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
