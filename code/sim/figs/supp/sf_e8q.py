"""sf_e8q: the request-level replay with a queue, Sublet and its baselines replayed request by request while a copy may
wait up to W seconds for a free replica before it falls back, with the tables e8q_costs.tex, e8q_latency.tex and
e8q_decomp.tex and the data files e8q_cells.csv and e8q_latency.csv (design/ms8/plan.md D1, W; design/ms8/
registration.md §2-§3, X7).

Question: is the fluid routing model closer to a replay in which requests may queue briefly, does the queue change
which policies cost less than Sublet, and what does it do to the time to first token?

Inputs (RUN_INPUTS, the MS8 run outputs; a missing one stops the script with exit code 2 and the file named; figs/
rebuild.py keeps the entry pending until they are copied in): the registered analysis code/sim/out/e8q/analysis.json
(sublet/experiments/e8q_analysis.py, frozen by its sha256 in design/ms8/registration.md: every cost, error E, ratio r,
margin, count, latency share, percentile and Q-3 median is read from it) and the summary it read,
code/sim/out/e8q/summary.json (the grid, and per cell the parts of Q-3's split, the lease spend and the headroom for
the data file; checked against the sha256 that the analysis recorded). The script recomputes the medians it plots
from the analysis's per-cell values and checks them against the analysis's own (overall E_abs_median, r_median, the
Q-3 medians; StyleError on a difference: a stale input). A non-reduced analysis must be the registered one on full
runs (meta.registered_full_inputs). Descriptive statistics; no p-value (registration §3).

Notation (the analysis's): per cell (tier, smoothing window, alignment), tag and waiting limit W in {0, 1, 2.5, 10} s
(W* = 2.5 s): C_replay(W), C_fluid, E(W) = (C_replay - C_fluid) / C_replay, the replayed all-fallback bill B(W) (BL0a's
zero placement replayed with the same queue) and r(W) = C_replay(W) / B(W); Delta(W) = min(r of greedy back-off,
r of RetroRenting-style) - r(Sublet), a win when positive.

Figure (W2 x HEIGHT_IN in; the set KEYS = style.SUPP_POLICIES_MS8['sf_e8q'], figs/style.py's MS8 unit F7 block).
Legend row above the panels: Sublet, critical-ratio renting, RetroRenting-style, Greedy back-off and All-fallback (the
replayed bill, panels (a) and (c); its legend sample is its line with the dot that marks its values).
(a) The fluid model's signed error E (%) against W, per policy: the median over the cells (marker, joined across W)
    with the interquartile range over the cells (bar; statistics.quantiles, method 'inclusive'), dodged at each W, a
    grey line at 0; All-fallback is the bill's own E (no policy: what the queue alone does to the fluid model's
    all-fallback cost). Below 0 the replay costs less than the fluid model: waiting moves work into idle capacity, so
    E falls with W by construction (e8q_analysis's Q-1). The medians are checked against overall.E_median and
    bill_E_median, the counts of cells with E < 0 against n_E_negative and bill_n_E_negative; the registered rule's
    |E| (overall.E_abs_median, rule) is in the caption and e8q_costs.tex.
(b) Each policy's replayed cost over Sublet's in the same cell against W (log scale; the median over the cells with
    the min-max range), the grey line at 1 marking Sublet; above each W the cells in which Sublet costs less than both
    RetroRenting-style and Greedy back-off, of all the cells (the analysis's wins; registration §3: a missing run counts
    as a loss).
(c) The share of request copies served by fallback (%) per minute class (reclaim, load, overflow, base:
    queue.window_classes of each policy's fluid run) and policy (and the bill), pooled over the tiers S, M, L (the
    analysis's Q-2 per tier, weighted by its copies: the share of all the copies of the cells in that class's
    minutes): the policy's marker at W*, a small open dot at W = 0, joined by a thin line; a class without copies is
    left out. W is an ordinal axis in (a) and (b), the policies dodged sideways at each W.
Panel titles at the caption size (LABEL_PT) on the letters' baseline (C62).

Tables (after hook, figs.common.write_table, from the extract's `tables`, so --from-extract rewrites them byte for byte;
longtables of ms5b_e7_lib, one-column mode):
  e8q_costs.tex   per W and tier (and over all cells): the cells; each policy's replayed cost over the replayed bill
                  (%), its E and |E| (%), the bill's own E, Sublet's margin Delta (percentage points of the bill;
                  median), its wins of all the cells (a missing run counts as a loss) and the cells in which the fluid
                  and replayed orders of the four policies agree;
  e8q_latency.tex per tier and policy (and the bill): every minute at W = 0 and each minute class and every minute
                  at W*: the minute slots and copies (millions, three significant figures), the fallback share, the
                  share served after waiting and the interrupted share (%), and at each D_fb in {0.5, 1, 2} s the
                  TTFT P50, P99 and P99.9 (s; a percentile in the histogram's last bin printed as a bound at that
                  bin's edge, read from the analysis's note) and the attainment of the tier's TTFT SLO (%);
  e8q_decomp.tex  Q-3 per W and policy, medians over the cells: the gap C_replay - C_fluid split into the fallback in
                  minutes without fluid demand, the extra fallback in minutes with demand, stranding and routing (USD),
                  the gap (USD and % of the bill), E, the lease spend and the headroom shares;
  e8q_cells.csv   every cell, policy and W: costs, E, r, the gap and its four parts, lease spend, headroom, Delta, win,
                  same order and ranks (the bill's rows: its costs and E);
  e8q_latency.csv every tier, policy (and the bill), W and minute class (and all): Q-2's counts, shares and, per
                  D_fb, the percentiles and SLO attainment (the whole of Q-2, every W).
Every policy is named by its registry label; no tag, file or design name is printed.

labels.caption is a caption draft for the integrator (the supplement), labels.values the counts and values it reads
from the inputs (candidate \\val entries); headline is the analysis's headline block, unchanged.

Run from code/sim: python -m figs.supp.sf_e8q [--from-extract [JSON]].
"""
from __future__ import annotations

import math
import statistics
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.ticker import FixedLocator, MaxNLocator, NullLocator

from figs import style
from figs.common import MissingKey, need, panel_title, write_table
from figs.inputs import Inputs
from figs.supp import ms7_x3_lib as X
from figs.supp.ms4_lib import log_ticks

NAME = "sf_e8q"
ANALYSIS = "code/sim/out/e8q/analysis.json"
SUMMARY = "code/sim/out/e8q/summary.json"
RUN_INPUTS = (ANALYSIS, SUMMARY)
INPUTS = RUN_INPUTS
REGISTRATION = "design/ms8/registration.md"
TAGS = ("Sublet", "A9", "BL5-cur", "BL1-BO")          # in the legend order of KEYS
PAIR = ("BL1-BO", "BL5-cur")                          # e8q_analysis.PAIR
BILL = "BL0a"
KEY_OF = {"Sublet": "sublet_v2", "A9": "a9", "BL5-cur": "bl5_cur", "BL1-BO": "bl1_bo", BILL: "bl0a"}
KEYS = style.SUPP_POLICIES_MS8[NAME]                  # figs/style.py, MS8 unit F7 block
OTHERS = tuple(t for t in TAGS if t != "Sublet")
WAITS = ("0", "1", "2.5", "10")                       # e8q_analysis.WAITS
W0, W_STAR = "0", "2.5"
D_FB = ("0.5", "1", "2")                              # e8q_analysis.D_FB, as mc.num_key writes them
D_FB_PRIMARY = "1"                                    # the analysis's headline latency (latency_at_d_fb_1)
CLASSES = ("reclaim", "load", "overflow", "base")     # e8q_analysis.CLASSES
QUANT = ("p50", "p99", "p999")
PARTS = ("fallback_zero_demand", "fallback_overflow", "stranding", "routing")      # e8q_analysis.PARTS
Q3_KEYS = PARTS + ("gap_usd", "E", "gap_over_bill", "lease_usd", "headroom_all", "headroom_overflow",
                   "zero_demand_share_of_gap")
TIERS = ("S", "M", "L")
TABLES = ("e8q_costs.tex", "e8q_latency.tex", "e8q_decomp.tex", "e8q_cells.csv", "e8q_latency.csv")
CELLS_CSV, LATENCY_CSV = TABLES[3], TABLES[4]
HEIGHT_IN = 2.5
style.register_supplementary(NAME, "W2", HEIGHT_IN)     # as figs/style.py's MS8 unit F7 block registers it
AXES_RATIOS = (1.0, 1.0, 1.35)
DODGE = {"a": 0.13, "b": 0.16, "c": 0.17}             # series i of n at its category + (i - (n - 1) / 2) * DODGE
LOG_PAD = 1.12                                        # (b): the log range extends this factor beyond the data
LIN_PAD = 0.08                                        # (a), (c): the linear range extends this share beyond the data
COUNT_ROOM = 0.16                                     # (b): the share of the axes height above the data for the counts
COUNT_PT = 2.0                                        # (b): the counts this far below the axes top
REL_TOL = 1e-9
TOP_ROOM_PT = 0.5 * style.TICK_PT + 2.0      # (a), (c): half a tick label's height and the gap of common._top_tick_room
BILL_DOT_PT = 2.0                            # the bill's dots (a line policy without a marker), as in the legend
W0_DOT_PT = 2.4                              # (c): the open dot at W = 0, its size and edge width
W0_DOT_EDGE_PT = 0.7
LETTER = {"Sublet": "S", "A9": "C", "BL5-cur": "R", "BL1-BO": "G", BILL: "B"}
CLASS_TICKS = {"reclaim": "Reclaim", "load": "Load", "overflow": "Overflow", "base": "Base", "all": "All"}
CLASS_TEX = {"reclaim": "reclaim", "load": "load", "overflow": "overflow", "base": "base", "all": "all"}
LABELS = {"x_wait": "Waiting limit (s)", "y_a": "Fluid cost error E (%)", "y_b": "Replayed cost / Sublet's",
          "x_class": "Minute class", "y_c": "Copies served by fallback (%)",
          "titles": {"a": "Fluid model's error", "b": "Replayed cost", "c": "Fallback by minute class"},
          "caption": (
              "The request-level replay with a queue: {sublet} and its baselines replayed request by request on "
              "the request-level instance's {n} cells (tiers {tiers}, smoothing windows {windows} min, alignments "
              "{alignments}, $\\mu=\\tilde{{\\beta}}$), a copy that finds no free replica waiting up to $W$ before it "
              "falls back; costs in overflow accounting (as in the earlier replay study). (a) The fluid model's cost "
              "error $E=(C_{{\\mathrm{{replay}}}}-C_{{\\mathrm{{fluid}}}})/C_{{\\mathrm{{replay}}}}$, the median "
              "over the cells with the interquartile range; {fb}: the all-fallback cost's own error, with no policy. "
              "Below 0 the replay costs less than the fluid model: a copy that waits is served by idle capacity that "
              "the fluid model books as fallback, so $E$ falls with $W$ ({fbneg} of the {n} cells below 0 for {fb} at "
              "$W={wstar}$~s). (b) Each policy's replayed cost over {sublet}'s in the same cell, the median over the "
              "cells with the range; the numbers count the cells in which {sublet} costs less than both {rr} and "
              "{bo}, of all {n} cells. In (a) and (b) $W$ is on an ordinal axis and the policies are offset "
              "sideways. (c) The share of the request copies served by fallback per minute "
              "class (the minutes in which a lease of the policy is reclaimed, a replica loads, the fluid model sends "
              "demand beyond the borrower's own capacity to the platform, or none of these), pooled over the tiers: "
              "the marker at $W={wstar}$~s, the small open dot at $W=0$. At $W=0$ the replay is the earlier replay study's ({q0}). {sublet}'s median $|E|$ is {e0} at "
              "$W=0$ and {es} at $W={wstar}$~s; it costs less than both baselines in {w0} and {ws} of the {n} "
              "cells.{miss}")}


# ---------------------------------------------------------------------------------------------------------------
# inputs and provenance (ms7_x3_lib's, with the MS8 registration)
def load(inp: Inputs, name: str) -> Any:
    """The JSON input `name` through `inp`; ms7_x3_lib.MissingInput (exit code 2) naming the file when it is absent."""
    import json
    p = inp.path(name)
    if not p.is_file():
        raise X.MissingInput(f"[{NAME}] required input {name} is missing under {inp.root} (an MS8 run output, "
                             f"{REGISTRATION}; copied in after the runs)")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def check_registered(prov: Mapping) -> None:
    """A non-reduced analysis must be the registered one on full inputs (design/ms8/registration.md §1, §6):
    StyleError otherwise, naming the record."""
    if prov.get("reduced"):
        return
    if prov.get("registered_full_inputs") is not True or (prov.get("registration") or {}).get("matches") is not True:
        raise style.StyleError(
            f"[{NAME}] the analysis {prov.get('exp')} is not a registered analysis of full runs (registration matches "
            f"{(prov.get('registration') or {}).get('matches')}, registered_full_inputs "
            f"{prov.get('registered_full_inputs')}; {REGISTRATION} §1): rerun it on the copied outputs")


# ---------------------------------------------------------------------------------------------------------------
# small rules
def _f(v) -> float | None:
    return None if v is None else float(v)


def agg(xs) -> dict:
    """median (statistics.median's rule, ms7_x3_lib.median), min, max and n of the values that are not None."""
    v = [float(x) for x in xs if x is not None]
    return {"median": X.median(v), "min": min(v) if v else None, "max": max(v) if v else None, "n": len(v)}


def _close(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= REL_TOL * max(1.0, abs(float(b)))


def _check(what: str, mine, theirs) -> None:
    if not _close(mine, theirs):
        raise style.StyleError(f"[{NAME}] {what}: {mine} recomputed from the analysis's cells, {theirs} in its summary "
                               f"block (a stale or edited analysis)")


def _bw(x: Mapping | None, W: str) -> Mapping:
    return ((x or {}).get("by_W") or {}).get(W) or {}


def cell_list(q1: Mapping, W: str) -> list[tuple[str, str, str, Mapping]]:
    """(tier, window, alignment, the analysis's cell record at W) in the analysis's order."""
    return [(t, w, c, e) for t, a in ((q1.get("cells") or {}).get(W) or {}).items() for w, b in a.items()
            for c, e in b.items()]


def decompose(x: Mapping | None, W: str) -> dict | None:
    """The four parts of a tag's gap at W from its summary cell (e8q_analysis.decompose's rule) and the residual;
    None when a value is missing."""
    y = _bw(x, W)
    fl = (x or {}).get("fluid") or {}
    rep = y.get("replay") or {}
    fbd = y.get("fallback_by_demand") or {}
    try:
        p = {"fallback_zero_demand": float(fbd["zero"]["usd"]),
             "fallback_overflow": float(fbd["positive"]["usd"]) - float(fl["fallback"]),
             "stranding": float(rep["stranding"]) - float(fl["stranding"]),
             "routing": float(rep["routing"]) - float(fl["routing"])}
        gap = float(y["gap_usd"])
    except (KeyError, TypeError):
        return None
    p["gap_usd"] = gap
    p["residual_usd"] = gap - sum(p[k] for k in PARTS)
    return p


# ---------------------------------------------------------------------------------------------------------------
# data
def quartiles(xs) -> dict:
    """The lower and upper quartiles of the values that are not None (statistics.quantiles, n=4, method 'inclusive';
    a single value is its own quartiles)."""
    v = [float(x) for x in xs if x is not None]
    if not v:
        return {"q25": None, "q75": None}
    if len(v) == 1:
        return {"q25": v[0], "q75": v[0]}
    q = statistics.quantiles(v, n=4, method="inclusive")
    return {"q25": q[0], "q75": q[2]}


def panel_a(q1: Mapping) -> dict:
    """Per tag (and the bill) per W: the signed E over the cells (median, quartiles, min, max, n and the cells with
    E < 0), in percent; the medians checked against overall.E_median and bill_E_median, the counts against
    n_E_negative and bill_n_E_negative."""
    out = {}
    for tg in TAGS + (BILL,):
        rows = []
        for W in WAITS:
            cl = cell_list(q1, W)
            o = (q1.get("overall") or {}).get(W) or {}
            if tg == BILL:
                v = [_f(e.get("bill_E")) for *_k, e in cl]
                ref_m, ref_n = o.get("bill_E_median"), o.get("bill_n_E_negative")
            else:
                v = [_f(((e.get("tags") or {}).get(tg) or {}).get("E")) for *_k, e in cl]
                ref_m, ref_n = (o.get("E_median") or {}).get(tg), (o.get("n_E_negative") or {}).get(tg)
            a = {**agg(v), **quartiles(v)}
            neg = sum(1 for x in v if x is not None and x < 0)
            _check(f"median E of {tg} at W {W}", a["median"], ref_m)
            if neg != ref_n:
                raise style.StyleError(f"[{NAME}] cells with E < 0 of {tg} at W {W}: {neg} recomputed from the "
                                       f"analysis's cells, {ref_n} in its summary block (a stale or edited analysis)")
            rows.append({"W": W, "n": a["n"], "n_negative": neg,
                         **{k: None if a[k] is None else 100.0 * a[k] for k in ("median", "q25", "q75", "min", "max")}})
        out[tg] = rows
    return {"series": out, "unit": "percent", "bars": "interquartile range"}


def panel_b(q1: Mapping) -> dict:
    """Per tag other than Sublet per W: C_replay(tag) / C_replay(Sublet) over the cells; the wins per W, of all the
    cells (registration §3: a missing run counts as a loss)."""
    out = {}
    for tg in OTHERS:
        rows = []
        for W in WAITS:
            v = []
            for *_k, e in cell_list(q1, W):
                a, s = (((e.get("tags") or {}).get(t) or {}).get("C_replay") for t in (tg, "Sublet"))
                v.append(None if a is None or s is None or not float(s) > 0 else float(a) / float(s))
            rows.append({"W": W, **agg(v)})
        out[tg] = rows
    ov = q1.get("overall") or {}
    wins = []
    for W in WAITS:
        o = ov.get(W) or {}
        n = len(cell_list(q1, W))
        if o.get("n_cells") != n:
            raise style.StyleError(f"[{NAME}] cells at W {W}: {n} in the analysis's cells, {o.get('n_cells')} in its "
                                   f"overall block (a stale or edited analysis)")
        wins.append({"W": W, "wins": o.get("wins"), "n_with_delta": o.get("n_with_delta"), "n_cells": n})
    return {"series": out, "wins": wins}


def panel_c(q2: Mapping) -> dict:
    """Per tag (and the bill) per minute class, at W = 0 and W*: the fallback share per tier (Q-2) and pooled over
    the tiers, weighted by their copies (sum of share x copies over the sum of copies), in percent; a tier without
    copies is left out, a class without copies in every tier has no value."""
    by = q2.get("by_tier") or {}
    tiers = [t for t in TIERS if t in by] + [t for t in by if t not in TIERS]
    out = {}
    for tg in TAGS + (BILL,):
        rows = []
        for cn in CLASSES:
            row = {"class": cn}
            for W in (W0, W_STAR):
                per, num, den = {}, 0.0, 0
                for t in tiers:
                    r = (((by.get(t) or {}).get(tg) or {}).get(W) or {}).get(cn) or {}
                    n, sh = r.get("copies") or 0, r.get("fallback_share")
                    if not n or sh is None:
                        continue
                    per[t] = 100.0 * float(sh)
                    num += float(sh) * int(n)
                    den += int(n)
                row[W] = {"pooled": 100.0 * num / den if den else None, "copies": den, "tiers": per}
            rows.append(row)
        out[tg] = rows
    return {"series": out, "tiers": tiers, "waits": [W0, W_STAR], "unit": "percent"}


def _cap_edge(note: str) -> float:
    """The last bin's lower edge from the analysis's note 'in the last bin (>= 20 s)'; StyleError on another note."""
    import re
    m = re.search(r">=\s*([0-9.]+)\s*s", note or "")
    if not m:
        raise style.StyleError(f"[{NAME}] a percentile in the last bin without its edge in the note {note!r}")
    return float(m.group(1))


def _rank_of(r, t):
    return None if r is None or t not in r else r.index(t) + 1


def cost_rows(q1: Mapping) -> list[dict]:
    """e8q_costs: per W, per tier and over all cells (tier 'all'): n, per tag median r, E, |E|, the bill's median E,
    Delta (median, min, max), wins, same order; the 'all' rows checked against the analysis's overall block."""
    out = []
    for W in WAITS:
        cl = cell_list(q1, W)
        groups = [(t, [e for tt, _w, _c, e in cl if tt == t]) for t in TIERS if any(tt == t for tt, *_ in cl)]
        groups += [(t, [e for tt, _w, _c, e in cl if tt == t]) for t in dict.fromkeys(tt for tt, *_ in cl)
                   if t not in TIERS]
        groups.append(("all", [e for *_k, e in cl]))
        for t, es in groups:
            row = {"W": W, "tier": t, "n": len(es),
                   "r": {tg: X.median(((e.get("tags") or {}).get(tg) or {}).get("r") for e in es) for tg in TAGS},
                   "E": {tg: X.median(((e.get("tags") or {}).get(tg) or {}).get("E") for e in es) for tg in TAGS},
                   "E_abs": {tg: X.median(None if ((e.get("tags") or {}).get(tg) or {}).get("E") is None
                                          else abs(float(e["tags"][tg]["E"])) for e in es) for tg in TAGS},
                   "bill_E": X.median(e.get("bill_E") for e in es),
                   "delta": agg(e.get("delta") for e in es),
                   "wins": sum(1 for e in es if e.get("win")),
                   "n_with_delta": sum(1 for e in es if e.get("delta") is not None),
                   "same_order": sum(1 for e in es if e.get("same_order"))}
            if t == "all":
                o = (q1.get("overall") or {}).get(W) or {}
                for tg in TAGS:
                    _check(f"median E of {tg} at W {W}", row["E"][tg], (o.get("E_median") or {}).get(tg))
                    _check(f"median r of {tg} at W {W}", row["r"][tg], (o.get("r_median") or {}).get(tg))
                    _check(f"median |E| of {tg} at W {W}", row["E_abs"][tg], (o.get("E_abs_median") or {}).get(tg))
                rule = q1.get("rule") or {}
                for k, w in (("sublet_E_abs_median_w0", W0), ("sublet_E_abs_median_w_star", W_STAR)):
                    if W == w:
                        _check(f"the rule's {k}", row["E_abs"]["Sublet"], rule.get(k))
                _check(f"the bill's median E at W {W}", row["bill_E"], o.get("bill_E_median"))
                _check(f"median Delta at W {W}", row["delta"]["median"], (o.get("delta") or {}).get("median"))
                if row["wins"] != o.get("wins") or row["same_order"] != o.get("same_order"):
                    raise style.StyleError(f"[{NAME}] wins or same order at W {W} differ from the analysis's overall "
                                           f"block (a stale or edited analysis)")
            out.append(row)
    return out


def latency_rows(q2: Mapping, waits: Sequence[str], classes: Sequence[str]) -> list[dict]:
    """Q-2's rows (tier, tag or the bill, W, class): counts, shares and per D_fb the percentiles and attainment."""
    out = []
    by = q2.get("by_tier") or {}
    for t in [x for x in TIERS if x in by] + [x for x in by if x not in TIERS]:
        for tg in TAGS + (BILL,):
            for W in waits:
                rows = ((by.get(t) or {}).get(tg) or {}).get(W) or {}
                for cn in classes:
                    r = rows.get(cn)
                    if r is None:
                        continue
                    ttft = {}
                    for d in D_FB:
                        tt = (r.get("ttft") or {}).get(d) or {}
                        ttft[d] = {**{q: tt.get(q) for q in QUANT}, "slo_attainment": tt.get("slo_attainment"),
                                   "slo_s": tt.get("slo_s"),
                                   "capped": [q for q in QUANT if tt.get(q) is None and tt.get(f"{q}_note")],
                                   "cap_s": {q: _cap_edge(tt[f"{q}_note"]) for q in QUANT
                                             if tt.get(q) is None and tt.get(f"{q}_note")}}
                    out.append({"tier": t, "tag": tg, "W": W, "class": cn,
                                **{k: r.get(k) for k in ("copies", "slots", "fallback_share", "fallback_token_share",
                                                         "reneged_share", "waited_share", "mean_wait_of_waited_s",
                                                         "interrupted_share")}, "ttft": ttft})
    return out


def decomp_rows(q3: Mapping) -> list[dict]:
    ov = q3.get("overall") or {}
    return [{"W": W, "tag": tg, **{k: ((ov.get(W) or {}).get(tg) or {}).get(k) for k in Q3_KEYS + ("n",)}}
            for W in WAITS for tg in TAGS if tg in (ov.get(W) or {})]


def cells_csv(q1: Mapping, summ: Mapping, q3: Mapping) -> dict:
    """Every cell, tag (and the bill) and W; the four parts of the gap from the summary, their medians over the cells
    checked against the analysis's Q-3 medians."""
    cols = ("tier", "window_min", "alignment", "wait_s", "policy", "tag", "c_fluid_usd", "c_replay_usd",
            "bill_replay_usd", "cost_over_bill", "error", "gap_usd", *(f"{p}_usd" for p in PARTS), "residual_usd",
            "lease_usd", "headroom_all", "headroom_positive_demand", "delta_over_bill", "sublet_below_both",
            "same_order_of_4", "rank_fluid_of_4", "rank_replay_of_4")
    rows, parts = [], {}
    sc = summ.get("cells") or {}
    for W in WAITS:
        for t, w, c, e in cell_list(q1, W):
            sx = ((sc.get(t) or {}).get(w) or {}).get(c) or {}
            for tg in TAGS:
                y = (e.get("tags") or {}).get(tg) or {}
                x = sx.get(tg) or {}
                p = decompose(x, W)
                if p is not None:
                    parts.setdefault(W, {}).setdefault(tg, []).append(p)
                hr = x.get("headroom") or {}
                rows.append((t, int(w), int(c), float(W), X.plain(style.POLICIES[KEY_OF[tg]].label), tg,
                             y.get("C_fluid"), y.get("C_replay"), e.get("bill"), y.get("r"), y.get("E"),
                             y.get("gap_usd"), *((p or {}).get(k) for k in PARTS), (p or {}).get("residual_usd"),
                             x.get("lease_usd"), hr.get("share_all"), hr.get("share_overflow"), e.get("delta"),
                             e.get("win"), e.get("same_order"), _rank_of(e.get("rank_fluid"), tg),
                             _rank_of(e.get("rank_replay"), tg)))
            bx = sx.get(BILL) or {}
            rows.append((t, int(w), int(c), float(W), "All-fallback bill", BILL, bx.get("C_fluid"), e.get("bill"),
                         e.get("bill"), None if e.get("bill") is None else 1.0, e.get("bill_E"),
                         _bw(bx, W).get("gap_usd"), *([None] * (len(PARTS) + 1)), None, None, None, None, None,
                         None, None, None))
    ov = q3.get("overall") or {}
    for W, a in parts.items():
        for tg, ps in a.items():
            for k in PARTS + ("gap_usd",):
                _check(f"Q-3 median {k} of {tg} at W {W}", X.median(p[k] for p in ps),
                       ((ov.get(W) or {}).get(tg) or {}).get(k))
    return X.csv_entry(CELLS_CSV, cols, rows)


def latency_csv(rows: Sequence[Mapping]) -> dict:
    cols = ("tier", "policy", "tag", "wait_s", "window_class", "slots", "copies", "fallback_share",
            "fallback_token_share", "reneged_share", "waited_share", "mean_wait_of_waited_s", "interrupted_share",
            *(f"{q}_s_dfb_{d}" for d in D_FB for q in QUANT), *(f"slo_attainment_dfb_{d}" for d in D_FB), "slo_s",
            "percentiles_in_last_bin")
    out = []
    for r in rows:
        lab = "All-fallback bill" if r["tag"] == BILL else X.plain(style.POLICIES[KEY_OF[r["tag"]]].label)
        capped = ";".join(f"{q}@{d}" for d in D_FB for q in r["ttft"][d]["capped"])
        out.append((r["tier"], lab, r["tag"], float(r["W"]), r["class"], r["slots"], r["copies"], r["fallback_share"],
                    r["fallback_token_share"], r["reneged_share"], r["waited_share"], r["mean_wait_of_waited_s"],
                    r["interrupted_share"], *(r["ttft"][d][q] for d in D_FB for q in QUANT),
                    *(r["ttft"][d]["slo_attainment"] for d in D_FB), r["ttft"][D_FB[0]]["slo_s"], capped or None))
    return X.csv_entry(LATENCY_CSV, cols, out)


def build(inp: Inputs) -> dict:
    ana = load(inp, ANALYSIS)
    summ = load(inp, SUMMARY)
    prov = X.provenance(ana, ANALYSIS)
    check_registered(prov)
    shas = X.check_input_shas(prov, inp, {"out/e8q/summary.json": SUMMARY}, NAME)
    shas[ANALYSIS] = X.sha256_of(inp, ANALYSIS)
    meta = need(summ, "meta", what=SUMMARY)
    grid = need(meta, "grid", what=f"{SUMMARY} meta")
    q1, q2, q3 = (need(ana, k, what=ANALYSIS) for k in ("q1", "q2", "q3"))
    if not (q1.get("cells") or {}).get(W0):
        raise MissingKey(f"{ANALYSIS}: no cells")
    lat_all = latency_rows(q2, WAITS, CLASSES + ("all",))
    data = {"panels": {"a": panel_a(q1), "b": panel_b(q1), "c": panel_c(q2)},
            "grid": {k: grid.get(k) for k in ("tiers", "windows", "alignments", "mu", "waits", "w_star", "horizon_min",
                                              "market_tightness")},
            "q0": {k: (ana.get("q0") or {}).get(k) for k in ("status", "n", "n_equal", "n_expected", "n_missing",
                                                              "max_rel_diff", "tolerance")},
            "rule": dict(q1.get("rule") or {}),
            "slo_s": dict(q2.get("slo_s") or {}),
            "tables": {"costs": cost_rows(q1),
                       "latency": [r for r in lat_all if r["W"] == W_STAR or (r["W"] == W0 and r["class"] == "all")],
                       "decomp": decomp_rows(q3),
                       "max_abs_residual_usd": q3.get("max_abs_residual_usd"),
                       "e8q_cells": cells_csv(q1, summ, q3), "e8q_latency": latency_csv(lat_all)},
            "missing": missing_runs(summ),
            "headline": ana.get("headline"),
            "meta": {"reduced": bool(prov["reduced"] or meta.get("reduced")),
                     "git_revision": {"analysis": prov["git_revision"], "summary": meta.get("git_revision")},
                     "analysis": prov, "inputs_sha256": shas},
            "labels": {k: v for k, v in LABELS.items() if k != "caption"}}
    data["layout"] = layout(data)
    data["labels"]["values"] = values(data)
    data["labels"]["caption"] = caption(data)
    return data


def missing_runs(summ: Mapping) -> dict:
    """The summary's missing runs (e8q.summary: one entry per job and tag, with the reason): their count, the count
    per tag (TAGS and the bill, in that order) and the entries."""
    ms = [dict(x) for x in (summ.get("missing") or [])]
    by = {t: sum(1 for x in ms if x.get("tag") == t) for t in TAGS + (BILL,)}
    return {"n": len(ms), "by_tag": {t: k for t, k in by.items() if k}, "runs": ms}


def values(d: Mapping) -> dict:
    rule = d.get("rule") or {}
    pa, pb, pc = d["panels"]["a"]["series"], d["panels"]["b"], d["panels"]["c"]["series"]
    ov = {r["W"]: r for r in d["tables"]["costs"] if r["tier"] == "all"}
    miss = d.get("missing") or {}
    return {"n_cells": len(cell_rows_at(d, W0)), "q0_status": d["q0"].get("status"),
            "rule_holds": rule.get("holds"), "abs_E_falls": rule.get("abs_E_falls"), "wins_hold": rule.get("wins_hold"),
            "sublet_abs_E_median_pct": {W: None if ov[W]["E_abs"]["Sublet"] is None else 100.0 * ov[W]["E_abs"]["Sublet"]
                                        for W in WAITS},
            "sublet_E_median_pct": {r["W"]: r["median"] for r in pa["Sublet"]},
            "bill_E_median_pct": {r["W"]: r["median"] for r in pa[BILL]},
            "n_E_negative": {tg: {r["W"]: r["n_negative"] for r in pa[tg]} for tg in TAGS + (BILL,)},
            "wins": {w["W"]: w["wins"] for w in pb["wins"]},
            "n_with_delta": {w["W"]: w["n_with_delta"] for w in pb["wins"]},
            "same_order": {W: ov[W]["same_order"] for W in WAITS},
            "delta_median_pp": {W: None if ov[W]["delta"]["median"] is None else 100.0 * ov[W]["delta"]["median"]
                                for W in WAITS},
            "fallback_share_pct": {tg: {r["class"]: {W: r[W]["pooled"] for W in (W0, W_STAR)} for r in pc[tg]}
                                   for tg in TAGS + (BILL,)},
            "n_missing": miss.get("n", 0), "missing_by_tag": dict(miss.get("by_tag") or {}),
            "tiers": list(d["grid"].get("tiers") or []), "windows": list(d["grid"].get("windows") or []),
            "alignments": list(d["grid"].get("alignments") or []), "w_star": W_STAR, "d_fb": D_FB_PRIMARY,
            "slo_s": d.get("slo_s"), "max_abs_residual_usd": d["tables"].get("max_abs_residual_usd")}


def cell_rows_at(d: Mapping, W: str) -> list:
    return [r for r in d["tables"]["e8q_cells"]["rows"] if r[3] == float(W) and r[5] == "Sublet"]


def caption(d: Mapping) -> str:
    v = d["labels"]["values"]
    lab = {t: style.POLICIES[KEY_OF[t]].label for t in TAGS + (BILL,)}

    def lst(xs):
        xs = [str(x) for x in xs]
        return "--" if not xs else xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]
    al = v["alignments"]
    al_t = f"{al[0]}--{al[-1]}" if len(al) > 1 and al == list(range(al[0], al[-1] + 1)) else lst(al)
    q0 = {"pass": "identical costs in every cell", "fail": "costs differ in some cell",
          "missing": "some cells missing", "no reference": "not compared: another grid"}.get(v["q0_status"],
                                                                                            str(v["q0_status"]))

    def pct(x):
        return "--" if x is None else f"{x:.1f}\\%"
    nm = v["n_missing"]
    miss = "" if not nm else (" Missing runs: " + str(nm) + " (" + ", ".join(
        f"{lab[t]} {k}" for t, k in v["missing_by_tag"].items()) + "); a cell without the run of " + lab["Sublet"]
        + ", " + lab["BL5-cur"] + ", " + lab["BL1-BO"] + " or " + lab[BILL] + " counts as a loss in (b).")
    return LABELS["caption"].format(
        sublet=lab["Sublet"], bo=lab["BL1-BO"], rr=lab["BL5-cur"], fb=lab[BILL], n=v["n_cells"],
        tiers=", ".join(str(x) for x in v["tiers"]) or "--", windows=lst(v["windows"]), alignments=al_t,
        wstar=W_STAR, q0=q0, e0=pct(v["sublet_abs_E_median_pct"].get(W0)),
        es=pct(v["sublet_abs_E_median_pct"].get(W_STAR)), w0=v["wins"].get(W0), ws=v["wins"].get(W_STAR),
        fbneg=v["n_E_negative"][BILL].get(W_STAR), miss=miss)


# ---------------------------------------------------------------------------------------------------------------
# layout and drawing
def _vals(series: Mapping, keys=("median", "min", "max")) -> list[float]:
    return [float(r[k]) for rows in series.values() for r in rows for k in keys if r.get(k) is not None]


def _lin_range(vals: Sequence[float], *, floor0: bool) -> list[float]:
    """A linear range over `vals` (and 0) extended by LIN_PAD of its span on each side, from 0 when floor0 and no value
    is below 0."""
    lo, hi = min(list(vals) + [0.0]), max(list(vals) + [0.0])
    span = (hi - lo) or 1.0
    return [0.0 if floor0 and lo >= 0 else lo - LIN_PAD * span, hi + LIN_PAD * span]


def _b_ticks(lo: float, hi: float) -> list[float]:
    """(b)'s log ticks (ms4_lib.log_ticks), with 0.9 added when the range reaches below it and no tick lies below 1."""
    t = log_ticks(lo, hi)
    if lo <= 0.9 <= hi and (not t or min(t) >= 1.0):
        t = [0.9] + list(t)
    return t


def layout(data: Mapping) -> dict:
    pa, pb, pc = (data["panels"][p] for p in "abc")
    va = _vals(pa["series"], ("median", "q25", "q75"))
    vb = _vals(pb["series"]) + [1.0]
    vc = [float(r[W]["pooled"]) for rows in pc["series"].values() for r in rows for W in (W0, W_STAR)
          if r[W]["pooled"] is not None]
    lo_b, hi_b = min(vb) / LOG_PAD, max(vb) * LOG_PAD
    # (b): room above the data for the counts: the data take the lower 1 - COUNT_ROOM of the log range
    top_b = math.exp(math.log(lo_b) + (math.log(hi_b) - math.log(lo_b)) / (1.0 - COUNT_ROOM))
    return {"a": {"y": _lin_range(va, floor0=False)},
            "b": {"y": [lo_b, top_b], "data_top": hi_b, "ticks": _b_ticks(lo_b, hi_b)},
            "c": {"y": _lin_range(vc, floor0=True),
                  "classes": [cn for cn in CLASSES if any(r[W]["pooled"] is not None
                                                          for rows in pc["series"].values() for r in rows
                                                          if r["class"] == cn for W in (W0, W_STAR))]}}


def _dodge(n: int, i: int, step: float) -> float:
    return (i - (n - 1) / 2.0) * step


def _bill_dots(ax, xs, ys) -> None:
    """The bill (a line policy without a marker): its values marked by small dots in its color."""
    c = style.POLICIES["bl0a"].color
    style.scatter_policy(ax, "bl0a", xs, ys, marker="o", markersize=BILL_DOT_PT, markerfacecolor=c,
                         markeredgecolor=c, label="_nolegend_")


def _series_plot(ax, tag: str, xs: Sequence[float], rows: Sequence[Mapping], *, lines: bool,
                 bars=("min", "max")) -> None:
    k = KEY_OF[tag]
    ok = [j for j, r in enumerate(rows) if r.get("median") is not None]
    if not ok:
        return
    y = [np.nan if r.get("median") is None else float(r["median"]) for r in rows]
    if k == "bl0a":
        style.plot_policy(ax, k, xs, y)
        _bill_dots(ax, [xs[j] for j in ok], [y[j] for j in ok])
    else:
        style.plot_policy(ax, k, xs, y, lines=lines)
    lo, hi = bars
    have = [j for j in ok if rows[j].get(lo) is not None and rows[j].get(hi) is not None]
    if have:
        style.errorbars(ax, k, [xs[j] for j in have], [float(rows[j]["median"]) for j in have],
                        [float(rows[j][lo]) for j in have], [float(rows[j][hi]) for j in have])


def _linear_y(ax, lo: float, hi: float) -> None:
    """MaxNLocator ticks in plain format, the top tick label clear of the panel title (common._top_tick_room's rule
    on a linear axis: the highest tick in range at least TOP_ROOM_PT below the axes top)."""
    loc = MaxNLocator(nbins=5, steps=[1, 2, 2.5, 5, 10])
    ax.yaxis.set_major_locator(loc)
    ax.yaxis.set_major_formatter(style.PLAIN)
    t = max(v for v in loc.tick_values(lo, hi) if v <= hi + 1e-9 * max(1.0, abs(hi)))
    h_pt = style.axes_rect_in(ax)[3] * style.BP_PER_IN
    if t > lo and (hi - t) / (hi - lo) * h_pt < TOP_ROOM_PT:
        hi = lo + (t - lo) * h_pt / (h_pt - TOP_ROOM_PT)
    ax.set_ylim(lo, hi)


def draw_a(ax, pan: Mapping, lay: Mapping) -> None:
    style.reference_line(ax, y=0.0)
    tags = TAGS + (BILL,)
    for i, tg in enumerate(tags):
        xs = [j + _dodge(len(tags), i, DODGE["a"]) for j in range(len(WAITS))]
        _series_plot(ax, tg, xs, pan["series"][tg], lines=True, bars=("q25", "q75"))
    ax.set_xticks(range(len(WAITS)), WAITS)
    ax.set_xlim(-0.5, len(WAITS) - 0.5)
    _linear_y(ax, *lay["y"])


def draw_b(ax, pan: Mapping, lay: Mapping) -> None:
    style.reference_line(ax, y=1.0)
    for i, tg in enumerate(OTHERS):
        xs = [j + _dodge(len(OTHERS), i, DODGE["b"]) for j in range(len(WAITS))]
        _series_plot(ax, tg, xs, pan["series"][tg], lines=True)
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(FixedLocator(lay["ticks"]))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.set_ylim(*lay["y"])
    ticks = list(lay["ticks"])
    if 0.9 in ticks and 1.0 in ticks:                  # _b_ticks' 0.9 only where its label clears the label of 1
        h_pt = style.axes_rect_in(ax)[3] * style.BP_PER_IN
        lo, hi = (math.log(v) for v in lay["y"])
        if (math.log(1.0) - math.log(0.9)) / (hi - lo) * h_pt < 1.4 * style.TICK_PT:
            ticks.remove(0.9)
            ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.set_xticks(range(len(WAITS)), WAITS)
    ax.set_xlim(-0.5, len(WAITS) - 0.5)
    for j, w in enumerate(pan["wins"]):
        if w.get("wins") is None:
            continue
        t = ax.annotate(f"{w['wins']}/{w['n_cells']}", xy=(j, 1.0), xycoords=("data", "axes fraction"),
                        xytext=(0.0, -COUNT_PT), textcoords="offset points", ha="center", va="top",
                        fontsize=style.TICK_PT, color=style.POLICIES["sublet_v2"].label_color)
        t._sublet_role = "win_count"


def draw_c(ax, pan: Mapping, lay: Mapping) -> None:
    classes = lay["classes"]
    tags = TAGS + (BILL,)
    for i, tg in enumerate(tags):
        k = KEY_OF[tg]
        by = {r["class"]: r for r in pan["series"][tg]}
        pts = [(j + _dodge(len(tags), i, DODGE["c"]), (by.get(cn) or {}).get(W0, {}).get("pooled"),
                (by.get(cn) or {}).get(W_STAR, {}).get("pooled")) for j, cn in enumerate(classes)]
        col = style.POLICIES[k].text_color
        for x, y0, ys in pts:                # the thin line from the open dot at W = 0 to the marker at W*
            if y0 is not None and ys is not None:
                ax.plot([x, x], [y0, ys], color=col, linewidth=style.UNCERTAINTY_PT, solid_capstyle="butt",
                        zorder=style.POLICIES[k].zorder - 0.01, label="_nolegend_")
        d0 = [(x, y0) for x, y0, _ in pts if y0 is not None]
        if d0:
            ax.plot([x for x, _ in d0], [y for _, y in d0], linestyle="none", marker="o", markersize=W0_DOT_PT,
                    markeredgewidth=W0_DOT_EDGE_PT, markeredgecolor=col, markerfacecolor="white", color=col,
                    zorder=style.POLICIES[k].zorder - 0.005, label="_nolegend_")
        ds = [(x, y) for x, _, y in pts if y is not None]
        if ds:
            if k == "bl0a":
                _bill_dots(ax, [x for x, _ in ds], [y for _, y in ds])
            else:
                style.scatter_policy(ax, k, [x for x, _ in ds], [y for _, y in ds])
    ax.set_xticks(range(len(classes)), [CLASS_TICKS[c] for c in classes])
    ax.set_xlim(-0.5, len(classes) - 0.5)
    _linear_y(ax, *lay["y"])


def _legend_rows(keys: Sequence[str]) -> int:
    """One legend row where the entries fit it (TICK_PT), else two (a pyplot-free Figure, dropped on return)."""
    fig = style.new_figure(NAME)
    style.panel_row(fig, AXES_RATIOS, legend=1)
    try:
        _legend(fig, keys, 1)
        return 1
    except style.StyleError:
        return 2


def _legend(fig, keys: Sequence[str], rows: int):
    """The legend row: the policies' entries, then the bill's line with the dot that marks its values in (a), (c)."""
    from matplotlib.lines import Line2D
    kw = style.policy_kwargs("bl0a", lines=True, markers=False)
    c = style.POLICIES["bl0a"].color
    kw.update(marker="o", markersize=BILL_DOT_PT, markerfacecolor=c, markeredgecolor=c)
    bill = (Line2D([], [], **kw), kw["label"])
    return style.legend_row(fig, [k for k in keys if k != "bl0a"], extra=[bill] if "bl0a" in keys else [],
                            rows=rows)


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    lay = data["layout"]
    rows = _legend_rows(KEYS)
    fig = style.new_figure(NAME)
    axes = style.panel_row(fig, AXES_RATIOS, legend=rows)
    _legend(fig, KEYS, rows)
    draw_a(axes[0], data["panels"]["a"], lay["a"])
    draw_b(axes[1], data["panels"]["b"], lay["b"])
    draw_c(axes[2], data["panels"]["c"], lay["c"])
    for ax, xl, yl in zip(axes, (lab["x_wait"], lab["x_wait"], lab["x_class"]), (lab["y_a"], lab["y_b"], lab["y_c"])):
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
    letters = style.panel_letters(axes)
    for ax, letter, p in zip(axes, letters, ("a", "b", "c")):     # C62: at the caption size, on the letters' baseline
        panel_title(ax, letter, lab["titles"][p], fontsize=style.LABEL_PT)
    fig._sublet_axes = dict(zip(("a", "b", "c"), axes))
    return fig


# ---------------------------------------------------------------------------------------------------------------
# tables
def _p(v, d: int = 1) -> str:
    """A share or ratio in percent (`d` decimals)."""
    return X.num(None if v is None else 100.0 * float(v), f".{d}f")


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}{'' if n == 1 else 's'}"


def _key_text() -> str:
    lab = {t: X.tex(style.POLICIES[KEY_OF[t]].label) for t in TAGS}
    return (r"Sublet (S); " + lab["A9"].lower() + r" (C); " + lab["BL5-cur"] + r" (R); " + lab["BL1-BO"] + r" (G)")


def costs_tex(t: Sequence[Mapping], d: Mapping) -> str:
    rows = []
    for r in t:
        rows.append([X.num(float(r["W"]), "g"), "All" if r["tier"] == "all" else X.tex(r["tier"]), str(r["n"])]
                    + [_p(r["r"][x]) for x in TAGS] + [_p(r["E"][x]) for x in TAGS] + [_p(r["bill_E"])]
                    + [_p(r["E_abs"][x]) for x in TAGS]
                    + [_p(r["delta"]["median"]), f"{r['wins']}/{r['n']}", f"{r['same_order']}/{r['n']}"])
    groups = [i for i in range(1, len(t)) if t[i]["W"] != t[i - 1]["W"]]
    g = d["grid"]
    nw, na = len(g.get("windows") or []), len(g.get("alignments") or [])
    cap = (r"The request-level replay with a queue per waiting limit $W$ and tier (each tier over its "
           + _count(nw, "smoothing window") + r" and " + _count(na, "alignment")
           + r"; All: every cell): Cells, the cells; each policy's replayed cost over the replayed "
           r"all-fallback cost at the same $W$ (\%), the median over the cells, of " + _key_text() + r"; the relative "
           r"cost error of the fluid model $E=(C_{\mathrm{replay}}-C_{\mathrm{fluid}})/C_{\mathrm{replay}}$ (\%), the "
           r"median, and that of the all-fallback cost itself (B, no policy); the median of $|E|$; Margin, the "
           r"replayed cost of the cheaper of " + X.tex(style.POLICIES["bl5_cur"].label) + " and "
           + X.tex(style.POLICIES["bl1_bo"].label) + r" minus Sublet's, in percentage points of the all-fallback "
           r"cost, the median (positive where Sublet costs less); Below, the cells in which Sublet costs less than "
           r"both, of all the cells (a cell without one of the three runs or the all-fallback run counts as not "
           r"below); Same, the cells in which the fluid and replayed orders of the four policies agree. Costs in "
           r"overflow accounting (as in the earlier replay study). Every cell is in the data file "
           + CELLS_CSV.replace("_", r"\_") + ".")
    head_top = (r" & & & \multicolumn{4}{c}{Cost / all-fallback (\%)} & \multicolumn{5}{c}{$E$ (\%)} & "
                r"\multicolumn{4}{c}{$|E|$ (\%)} & & & \\" "\n"
                r"\cmidrule(lr){4-7}\cmidrule(lr){8-12}\cmidrule(lr){13-16}")
    header = [r"\shortstack{$W$\\(s)}", "Tier", "Cells", "S", "C", "R", "G", "S", "C", "R", "G", "B", "S", "C", "R",
              "G", r"\shortstack{Margin\\(pp)}", "Below", "Same"]
    return X.longtable("@{}llr" + "r" * 13 + "rrr@{}", cap, "tab:s-e8q-costs", header, rows, groups=groups,
                       tabcolsep="3.0pt", head_top=head_top)


def _ttft(v, cap: float | None) -> str:
    """A percentile (s), or the bound at the last bin's edge `cap` for one in that bin."""
    if v is None:
        return (r"$\geq$" + X.num(cap, "g")) if cap is not None else "--"
    return X.num(float(v), ".2f")


def _sig3(x) -> str:
    """A non-negative count in millions to three significant figures in fixed notation (a thousands separator from
    100 up), so that a small class never prints as 0.0."""
    if x is None:
        return "--"
    x = float(x)
    if x == 0:
        return "0"
    d = max(0, 2 - math.floor(math.log10(x)))
    return f"{x:,.{d}f}"


def latency_tex(t: Sequence[Mapping], d: Mapping) -> str:
    rows, keys = [], []
    for r in t:
        if not r.get("copies"):
            continue
        cells = [X.tex(r["tier"]), LETTER[r["tag"]], X.num(float(r["W"]), "g"), CLASS_TEX[r["class"]],
                 f"{int(r['slots']):,}", _sig3(None if r["copies"] is None else float(r["copies"]) / 1e6),
                 _p(r["fallback_share"]), _p(r["waited_share"]), _p(r["interrupted_share"])]
        for dfb in D_FB:
            tt = r["ttft"][dfb]
            cells += [_ttft(tt[q], (tt.get("cap_s") or {}).get(q)) for q in QUANT] + [_p(tt["slo_attainment"])]
        rows.append(cells)
        keys.append((r["tier"], r["tag"]))
    groups = [i for i in range(1, len(keys)) if keys[i] != keys[i - 1]]
    slo = d.get("slo_s") or {}
    slo_t = ", ".join(f"{X.tex(k)} {X.num(float(v), 'g')}~s" for k, v in slo.items())
    capt = (r"Latency of the request-level replay per tier (pooled over its smoothing windows and alignments) and "
            r"policy, at $W=" + W_STAR + r"$~s per minute class (the minutes in which a lease of the policy is "
            r"reclaimed, a replica loads, the fluid model sends demand beyond the borrower's own capacity to the "
            r"platform, or none of these; all: every minute) "
            r"and, for comparison, at $W=0$ over every minute: " + _key_text() + r"; the all-fallback cost (B: own "
            r"capacity, then fallback, with the same queue). Slots, the minutes; Copies, the request copies "
            r"(millions); Fallback, the share of copies served by fallback (at once, after waiting $W$, or at the end "
            r"of the horizon); Waited, the share served by a replica after waiting; Interrupted, the share stranded "
            r"by a reclaim; the time to first token (s) at the percentiles 50, 99 and 99.9 and the attainment of the "
            r"tier's TTFT objective (" + slo_t + r"; \%) for each fallback latency $D_{\mathrm{fb}}$. A percentile "
            r"in the last bin of the histogram is printed as a bound at that bin's edge. Classes without copies are "
            r"left out; every $W$ and class is in the data file " + LATENCY_CSV.replace("_", r"\_") + ".")
    head_top = (r" & & & & & & & & & " + " & ".join(r"\multicolumn{4}{c}{$D_{\mathrm{fb}}=" + X.num(float(x), "g")
                                                     + r"$~s}" for x in D_FB) + r" \\" "\n"
                + "".join(r"\cmidrule(lr){" + f"{10 + 4 * i}-{13 + 4 * i}" + "}" for i in range(len(D_FB))))
    header = ["Tier", "", r"\shortstack{$W$\\(s)}", "Class", "Slots", "Copies", r"\shortstack{Fall-\\back}",
              "Waited", r"\shortstack{Inter-\\rupted}"] + ["P50", "P99", "P99.9", "SLO"] * len(D_FB)
    return X.longtable("@{}llrl" + "r" * 17 + "@{}", capt, "tab:s-e8q-latency", header, rows, groups=groups,
                       tabcolsep="2.3pt", head_top=head_top)


def _sci(x) -> str:
    """A small residual in math, one significant digit: $2\\times10^{-11}$ (0 as $0$; -- when missing)."""
    if x is None:
        return "--"
    x = float(x)
    if x == 0.0:
        return "$0$"
    m, e = f"{x:.0e}".split("e")
    return "$" + m + r"\times10^{" + str(int(e)) + "}$"


def decomp_tex(t: Sequence[Mapping], d: Mapping) -> str:
    rows = []
    for r in t:
        rows.append([X.num(float(r["W"]), "g"), X.tex(style.POLICIES[KEY_OF[r["tag"]]].label)]
                    + [X.num(r[k], ".2f") for k in PARTS] + [X.num(r["gap_usd"], ".2f"), _p(r["gap_over_bill"]),
                                                            _p(r["E"]), X.num(r["lease_usd"], ".2f"),
                                                            _p(r["headroom_all"]), _p(r["headroom_overflow"]),
                                                            _p(r["zero_demand_share_of_gap"])])
    groups = [i for i in range(1, len(t)) if t[i]["W"] != t[i - 1]["W"]]
    res = d["tables"].get("max_abs_residual_usd")
    cap = (r"Why the fluid model's error depends on the policy: per waiting limit $W$ and policy, the medians over "
           r"the cells of the gap between the replayed and the fluid cost (USD) split into the replayed fallback in "
           r"minutes in which the fluid demand is zero (Zero), the replayed fallback in minutes with demand minus the "
           r"fluid fallback (Overflow), the replayed minus the fluid stranding and routing; the gap (USD and \% of the "
           r"replayed all-fallback cost), $E$ (\%), the lease spend (lease and loading, USD), the share of all minutes "
           r"and of the minutes with demand in which the warm capacity exceeds the demand (Headroom, \%), and the "
           r"zero-demand fallback's share of a positive gap (\%). Per cell the four parts add up to the gap (largest "
           r"residual " + _sci(res) + r" USD); the medians need not. Every cell is in the data file "
           + CELLS_CSV.replace("_", r"\_") + ".")
    head_top = (r" & & \multicolumn{4}{c}{Gap parts (USD)} & \multicolumn{2}{c}{Gap} & & & "
                r"\multicolumn{2}{c}{Headroom (\%)} & \\" "\n"
                r"\cmidrule(lr){3-6}\cmidrule(lr){7-8}\cmidrule(lr){11-12}")
    header = [r"\shortstack{$W$\\(s)}", "Policy", "Zero", "Overflow", r"\shortstack{Strand-\\ing}", "Routing", "USD",
              r"\shortstack{/ all-\\fallback (\%)}", r"$E$ (\%)", r"\shortstack{Lease\\(USD)}", "All", r"$d>0$",
              r"\shortstack{Zero /\\gap (\%)}"]
    return X.longtable("@{}ll" + "r" * 11 + "@{}", cap, "tab:s-e8q-decomp", header, rows, groups=groups,
                       tabcolsep="3.0pt", head_top=head_top)


def write_tables(data: Mapping, report: Mapping) -> None:
    t = data["tables"]
    paths = [write_table(TABLES[0], X.table_head(NAME, [ANALYSIS]) + costs_tex(t["costs"], data)),
             write_table(TABLES[1], X.table_head(NAME, [ANALYSIS]) + latency_tex(t["latency"], data)),
             write_table(TABLES[2], X.table_head(NAME, [ANALYSIS]) + decomp_tex(t["decomp"], data)),
             X.write_csv(t["e8q_cells"], NAME), X.write_csv(t["e8q_latency"], NAME)]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    return X.run(NAME, build, draw, argv, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
