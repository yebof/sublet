"""The analysis of E8q (X7, design/ms8/plan.md D1; design/ms8/scout_x7_queue.md §4): E8 v2's request-level replay
with a FIFO queue and a waiting limit W. Its sha256 is recorded in design/ms8/registration.md before the runs, and
e8q.py refuses a full run unless this file still has it (e8q.gate); so every rule below is fixed, deterministic and
complete. The runs are exploratory; no p-value is computed (the alignments are rotations of one request stream).

  python -m sublet.experiments.e8q_analysis [--root DIR] [--out DIR]

Inputs (<root> as ms3_common.ms3_root): out/e8q/summary.json and out/e8q/hist.json (e8q.summary), and E8 v2's
out/e8v2/a/summary.json (the reference of Q-0). Exit 2 when one of them is missing or unreadable. Outputs:
<out>/analysis.json and analysis.md (default <root>/out/e8q/; meta: the inputs' sha256 and the git revision, no time
stamp).

Notation. Cells are E8 v2's (tier, window, alignment), 36 at full scale; TAGS = (Sublet, A9, BL1-BO, BL5-cur), PAIR =
(BL1-BO, BL5-cur), BILL = BL0a's zero placement; W in WAITS = (0, 1, 2.5, 10) s, W* = 2.5 s. For a tag at W:
C_replay(W) (the fluid run's lease and loading plus the replayed routing, fallback and stranding), C_fluid, E(W) =
(C_replay - C_fluid) / C_replay and the gap C_replay - C_fluid (USD); the bill's C_replay(W) is B(W); r(W) = C_replay(W)
/ B(W), the replayed cost over the replayed all-fallback bill at the same W.

Q-0 (identity). At W = 0 the replay is loop.replay: C_fluid and C_replay of every (cell, tag) equal E8 v2's stored
values to REL_TOL = 1e-9 relative. 'fail' if a present pair differs, else 'missing' while a pair is missing here or in
E8 v2's summary, else 'pass' (all n_cells x 4 present and equal); 'no reference' when E8 v2's summary is of another
grid (a reduced run).

Q-1 (cost and margins). Per W and cell: each tag's C_replay, E, gap and r; Delta(W) = min over PAIR of r - r(Sublet)
(in USD also: min over PAIR of C_replay - C_replay(Sublet); the bill cancels in the sign); win iff Delta > 0; same
order iff the four tags ordered by C_fluid and by C_replay(W) agree (ties by name). Per (tier, window): the median,
minimum and maximum over the alignments of each tag's E and of Delta, and the wins. Over all cells, per W: each tag's
median E, median |E| and count of cells with E < 0, the bill's own median E and its count of cells with E < 0 (a
reference that does not depend on a policy), the wins and the same-order count. Holding rule (registered, design/ms8/plan.md D1 as decided before registration): Q-1 holds iff Sublet's median
|E| over the cells at W* is below its median |E| at W = 0 and the wins at W* are at least the wins at W = 0 (E8 v2
had 23 of 36); reported either way. The signed E is reported beside the rule, not in it: waiting costs nothing, so the
queue moves work into idle own capacity and leased slots that the fluid model books as fallback, the replay gets
cheaper than the fluid model and the signed E falls by construction and can turn negative (the bill's E(W) shows by
how much without any policy); |E| asks whether the fluid model is closer to the queued replay.

Q-2 (latency, descriptive). Per tier (pooled over windows and alignments), tag (and BILL), W and window class
(reclaim, load, overflow, base, and 'all'): the copies, the fallback share of copies and of their weighted tokens
(immediate, reneged and end of horizon), the share served after waiting, the interrupted (stranded) share (by the
class of the stranding slot), and for each D_fb in D_FB = (0.5, 1, 2) s the TTFT percentiles P50, P99 and P99.9 and
the SLO attainment at the tier's TTFT SLO (DistServe's chatbot SLOs by LLM size, Table 1 of
literature/papers/zhong2024distserve: S 0.25 s, M 2.5 s, L 4.0 s). The TTFT distribution is the histogram of served
copies (wait + inp / P_j) plus the fallback copies' prefill histogram shifted by D_fb, and by D_fb + W for the copies
that waited (queue.py's TTFT model); a percentile is the upper edge of the first 10 ms bin at which the cumulative
share reaches it (None, with a note, in the last bin, >= 20 s); attainment counts the bins that end at or below the
SLO.

Q-3 (why E depends on the policy). Per cell, tag and W the gap splits exactly into four parts: the replayed fallback in
fast slots with zero fluid demand (the fluid fallback there is 0), the replayed fallback in slots with positive demand
minus the fluid fallback, the replayed minus the fluid stranding, and the replayed minus the fluid routing (USD; the
residual is reported). Per (tier, window) and over all cells, per tag and W: the medians of the parts, of the gap, of
E, of the gap over the bill (a common denominator), of the lease spend (lease plus loading) and of the headroom (the
share of all slots and of the positive-demand slots in which the warm capacity exceeds the demand).

Each analysis ends with the block 'headline': the values the text reports.

Provenance (meta): this file's sha256 beside the one design/ms8/registration.md records on its line
'e8q_analysis_sha256: <64 hex>' (read from the repository's working tree) and whether they match; per input its sha256,
git revision, whether it is reduced, and the gate it records; 'registered_full_inputs' is true only when the sha256
matches and the E8q summary is a full run that recorded an enforced gate that passed. A mismatch is printed to
stderr.
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

import numpy as np

from .. import paths
from . import ms3_common as mc

SPEC = "design/ms8/plan.md D1; design/ms8/scout_x7_queue.md §4 (X7)"
REGISTRATION = "design/ms8/registration.md"
REG_SHA_RE = re.compile(r"^e8q_analysis_sha256:\s*([0-9a-f]{64})\s*$", re.MULTILINE)
TAGS = ("Sublet", "A9", "BL1-BO", "BL5-cur")
PAIR = ("BL1-BO", "BL5-cur")
BILL = "BL0a"
WAITS = ("0", "1", "2.5", "10")
W0, W_STAR = "0", "2.5"
D_FB = (0.5, 1.0, 2.0)
SLO_S = {"S": 0.25, "M": 2.5, "L": 4.0}
QUANTILES = {"p50": 0.5, "p99": 0.99, "p999": 0.999}
CLASSES = ("reclaim", "load", "overflow", "base")
KINDS = ("served", "fallback", "fallback_waited")
REL_TOL = 1e-9
E8V2_WINS_W0 = 23                  # E8 v2's analysis (out/e8v2/analysis.json headline.cells.sublet_beats_pair_replay)
INPUTS = {"summary": "e8q/summary.json", "hist": "e8q/hist.json", "e8v2": "e8v2/a/summary.json"}


# ---------------------------------------------------------------- small rules
def median(xs) -> Optional[float]:
    v = [float(x) for x in xs if x is not None]
    return float(statistics.median(v)) if v else None


def agg(xs) -> dict:
    v = [float(x) for x in xs if x is not None]
    return {"median": float(statistics.median(v)) if v else None, "min": min(v) if v else None,
            "max": max(v) if v else None, "n": len(v)}


def rel_diff(a, b) -> Optional[float]:
    if a is None or b is None:
        return None
    return abs(float(a) - float(b)) / max(abs(float(b)), 1e-300)


def rank(costs: Mapping[str, Optional[float]]) -> Optional[list]:
    """The tags ordered by cost (ties by name); None while a cost is missing."""
    if not costs or any(v is None for v in costs.values()):
        return None
    return [t for t, _ in sorted(costs.items(), key=lambda kv: (float(kv[1]), kv[0]))]


def _div(a, b) -> Optional[float]:
    if a is None or b is None or not float(b) > 0:
        return None
    return float(a) / float(b)


def _cells(s: Mapping):
    """(tier, window, alignment, {tag: cell}) over the summary's cells, in its order."""
    for t, a in (s.get("cells") or {}).items():
        for w, b in a.items():
            for c, x in b.items():
                yield t, w, c, x


def _bw(x: Optional[Mapping], W: str) -> Mapping:
    return ((x or {}).get("by_W") or {}).get(W) or {}


# ---------------------------------------------------------------- Q-0
def q0(s: Mapping, ref: Optional[Mapping]) -> dict:
    g, gr = (s.get("meta") or {}).get("grid") or {}, ((ref or {}).get("meta") or {}).get("grid") or {}
    same = ref is not None and g.get("horizon_min") == gr.get("horizon_min") and \
        g.get("market_tightness") == gr.get("market_tightness")
    rows, fails, miss = [], [], []
    n_cells = 0
    for t, w, c, x in _cells(s):
        n_cells += 1
        if not same:
            continue
        for tg in TAGS:
            y = x.get(tg) or {}
            r = (((((ref or {}).get("cells") or {}).get(t) or {}).get(w) or {}).get(c) or {}).get(tg) or {}
            got = (y.get("C_fluid"), _bw(y, W0).get("C_replay"))
            if any(v is None for v in got) or r.get("C_fluid") is None or r.get("C_replay") is None:
                miss.append(f"{t}:{w}:{c}:{tg}")
                continue
            d = {"C_fluid": rel_diff(got[0], r["C_fluid"]), "C_replay": rel_diff(got[1], r["C_replay"])}
            ok = all(v <= REL_TOL for v in d.values())
            rows.append({"cell": f"{t}:{w}:{c}", "tag": tg, "rel_diff": d, "equal": ok})
            if not ok:
                fails.append(f"{t}:{w}:{c}:{tg}")
    n_exp = n_cells * len(TAGS)
    if not same:
        status = "no reference"
    elif fails:
        status = "fail"
    elif miss or not n_cells:
        status = "missing"
    else:
        status = "pass"
    mx = {k: max((r["rel_diff"][k] for r in rows), default=None) for k in ("C_fluid", "C_replay")}
    return {"status": status, "same_grid": same, "n": len(rows), "n_expected": n_exp,
            "n_equal": sum(1 for r in rows if r["equal"]), "failures": fails[:100], "n_missing": len(miss),
            "missing": miss[:100], "max_rel_diff": mx, "tolerance": REL_TOL}


# ---------------------------------------------------------------- Q-1
def _cell_w(x: Mapping, W: str) -> dict:
    """One cell at W: each tag's C_replay, E, gap and r, the bill, Delta (r and USD), win and same order."""
    bill = _bw(x.get(BILL), W).get("C_replay")
    bill_e = _bw(x.get(BILL), W).get("error")
    per = {}
    for tg in TAGS:
        y = _bw(x.get(tg), W)
        per[tg] = {"C_fluid": (x.get(tg) or {}).get("C_fluid"), "C_replay": y.get("C_replay"), "E": y.get("error"),
                   "gap_usd": y.get("gap_usd"), "r": _div(y.get("C_replay"), bill)}
    rs = per["Sublet"]["r"]
    rp = [per[t]["r"] for t in PAIR]
    delta = None if rs is None or any(v is None for v in rp) else min(rp) - rs
    cs = per["Sublet"]["C_replay"]
    cp = [per[t]["C_replay"] for t in PAIR]
    d_usd = None if cs is None or any(v is None for v in cp) else min(cp) - cs
    best = None if any(v is None for v in cp) else min(PAIR, key=lambda t: (per[t]["C_replay"], t))
    rf, rr = rank({t: per[t]["C_fluid"] for t in TAGS}), rank({t: per[t]["C_replay"] for t in TAGS})
    return {"bill": bill, "bill_E": bill_e, "tags": per, "delta": delta, "delta_usd": d_usd, "best_of_pair": best,
            "win": None if delta is None else delta > 0, "rank_fluid": rf, "rank_replay": rr,
            "same_order": None if rf is None or rr is None else rf == rr,
            "sublet_rank_replay": None if rr is None else rr.index("Sublet") + 1}


def q1(s: Mapping) -> dict:
    cells: dict = {}
    by_tw: dict = {}
    overall: dict = {}
    for W in WAITS:
        allc = []
        for t, w, c, x in _cells(s):
            e = _cell_w(x, W)
            cells.setdefault(W, {}).setdefault(t, {}).setdefault(w, {})[c] = e
            allc.append(e)
            b = by_tw.setdefault(W, {}).setdefault(t, {}).setdefault(w, {"_": []})
            b["_"].append(e)
        for t, a in (by_tw.get(W) or {}).items():
            for w, b in list(a.items()):
                es = b.pop("_")
                a[w] = {"n": len(es), "E": {tg: agg(e["tags"][tg]["E"] for e in es) for tg in TAGS},
                        "delta": agg(e["delta"] for e in es), "delta_usd": agg(e["delta_usd"] for e in es),
                        "wins": sum(1 for e in es if e["win"]), "same_order": sum(1 for e in es if e["same_order"])}
        overall[W] = {"n_cells": len(allc), "n_with_delta": sum(1 for e in allc if e["delta"] is not None),
                      "E_median": {tg: median(e["tags"][tg]["E"] for e in allc) for tg in TAGS},
                      "E_abs_median": {tg: median(None if e["tags"][tg]["E"] is None else abs(e["tags"][tg]["E"])
                                                  for e in allc) for tg in TAGS},
                      "n_E_negative": {tg: sum(1 for e in allc if e["tags"][tg]["E"] is not None
                                               and e["tags"][tg]["E"] < 0) for tg in TAGS},
                      "bill_E_median": median(e["bill_E"] for e in allc),
                      "bill_n_E_negative": sum(1 for e in allc if e["bill_E"] is not None and e["bill_E"] < 0),
                      "gap_median_usd": {tg: median(e["tags"][tg]["gap_usd"] for e in allc) for tg in TAGS},
                      "r_median": {tg: median(e["tags"][tg]["r"] for e in allc) for tg in TAGS},
                      "delta": agg(e["delta"] for e in allc), "wins": sum(1 for e in allc if e["win"]),
                      "same_order": sum(1 for e in allc if e["same_order"]),
                      "sublet_first_replay": sum(1 for e in allc if e["sublet_rank_replay"] == 1),
                      "bill_median_usd": median(e["bill"] for e in allc)}
    e0, es = (overall.get(W0) or {}).get("E_median", {}).get("Sublet"), \
        (overall.get(W_STAR) or {}).get("E_median", {}).get("Sublet")
    w0, ws = (overall.get(W0) or {}).get("wins"), (overall.get(W_STAR) or {}).get("wins")
    a = None if e0 is None or es is None else es < e0
    ea0, eas = (overall.get(W0) or {}).get("E_abs_median", {}).get("Sublet"), \
        (overall.get(W_STAR) or {}).get("E_abs_median", {}).get("Sublet")
    b = None if w0 is None or ws is None or not (overall.get(W_STAR) or {}).get("n_with_delta") else ws >= w0
    rule = {"w_star": W_STAR, "sublet_E_median_w0": e0, "sublet_E_median_w_star": es, "E_falls": a,
            "wins_w0": w0, "wins_w_star": ws, "wins_hold": b, "e8v2_wins_w0": E8V2_WINS_W0,
            "holds": None if ea0 is None or eas is None or b is None else bool(eas < ea0 and b),
            "sublet_E_abs_median_w0": ea0, "sublet_E_abs_median_w_star": eas,
            "abs_E_falls": None if ea0 is None or eas is None else eas < ea0,
            "bill_E_median_w0": (overall.get(W0) or {}).get("bill_E_median"),
            "bill_E_median_w_star": (overall.get(W_STAR) or {}).get("bill_E_median")}
    return {"cells": cells, "by_tier_window": by_tw, "overall": overall, "rule": rule}


# ---------------------------------------------------------------- Q-2
def _dense(sp: Optional[Mapping], n: int) -> np.ndarray:
    h = np.zeros(n, dtype=np.int64)
    if sp:
        c = np.asarray(sp["counts"], dtype=np.int64)
        h[int(sp["lo"]):int(sp["lo"]) + len(c)] = c
    return h


def _shift(h: np.ndarray, k: int) -> np.ndarray:
    """h moved k bins up, everything beyond the last bin into the last bin."""
    if k <= 0:
        return h.copy()
    out = np.zeros_like(h)
    n = len(h)
    if k < n:
        out[k:] = h[:n - k]
        out[-1] += int(h[n - k:].sum())
    else:
        out[-1] = int(h.sum())
    return out


def ttft_stats(served: np.ndarray, fb: np.ndarray, fbw: np.ndarray, W: float, d_fb: float, slo: Optional[float],
               bin_s: float) -> dict:
    """The TTFT distribution (module docstring) at one D_fb: its percentiles and the SLO attainment."""
    n = len(served)
    k_fb = int(round(d_fb / bin_s))
    k_w = int(round((d_fb + W) / bin_s))
    h = served + _shift(fb, k_fb) + _shift(fbw, k_w)
    N = int(h.sum())
    out: dict = {"n": N}
    if not N:
        out.update({k: None for k in QUANTILES}, slo_attainment=None)
        return out
    cum = np.cumsum(h)
    for k, q in QUANTILES.items():
        b = int(np.searchsorted(cum, q * N, side="left"))
        if b >= n - 1:
            out[k] = None
            out[f"{k}_note"] = f"in the last bin (>= {(n - 1) * bin_s:g} s)"
        else:
            out[k] = (b + 1) * bin_s
    if slo is not None:
        out["slo_s"] = slo
        out["slo_attainment"] = float(h[:int(round(slo / bin_s))].sum()) / N
    return out


def q2(s: Mapping, hist: Mapping) -> dict:
    hm = (hist.get("meta") or {}).get("hist") or {}
    bin_s, nb = float(hm.get("bin_s", 0.01)), int(hm.get("n_bins", 2001))
    cnt: dict = {}
    for t, w, c, x in _cells(s):
        for tg in TAGS + (BILL,):
            for W in WAITS:
                bc = _bw(x.get(tg), W).get("by_class") or {}
                for cn in CLASSES:
                    z = bc.get(cn) or {}
                    d = cnt.setdefault(t, {}).setdefault(tg, {}).setdefault(W, {}).setdefault(cn, {})
                    for k in ("copies", "tokens", "fallback_immediate", "fallback_reneged", "fallback_end",
                              "tokens_fallback_immediate", "tokens_fallback_reneged", "tokens_fallback_end",
                              "served_after_wait", "stranded", "slots", "wait_sum_s"):
                        d[k] = d.get(k, 0) + (z.get(k) or 0)
    out: dict = {}
    for t, a in cnt.items():
        slo = SLO_S.get(t)
        for tg, b in a.items():
            for W, cls in b.items():
                hs = (((hist.get("tiers") or {}).get(t) or {}).get(tg) or {}).get(W) or {}
                tot_h = {k: np.zeros(nb, np.int64) for k in KINDS}
                tot_c: dict = {}
                rows = {}
                for cn in CLASSES + ("all",):
                    if cn == "all":
                        z, hh = tot_c, tot_h
                    else:
                        z = cls[cn]
                        hh = {k: _dense((hs.get(cn) or {}).get(k), nb) for k in KINDS}
                        for k in KINDS:
                            tot_h[k] = tot_h[k] + hh[k]
                        for k, v in z.items():
                            tot_c[k] = tot_c.get(k, 0) + v
                    n = z.get("copies", 0)
                    nfb = z.get("fallback_immediate", 0) + z.get("fallback_reneged", 0) + z.get("fallback_end", 0)
                    tfb = z.get("tokens_fallback_immediate", 0) + z.get("tokens_fallback_reneged", 0) + \
                        z.get("tokens_fallback_end", 0)
                    rows[cn] = {"copies": n, "slots": z.get("slots", 0),
                                "fallback_share": _div(nfb, n), "fallback_token_share": _div(tfb, z.get("tokens")),
                                "reneged_share": _div(z.get("fallback_reneged", 0), n),
                                "waited_share": _div(z.get("served_after_wait", 0), n),
                                "mean_wait_of_waited_s": _div(z.get("wait_sum_s", 0), z.get("served_after_wait", 0)),
                                "interrupted_share": _div(z.get("stranded", 0), n),
                                "ttft": {mc.num_key(dfb): ttft_stats(hh["served"], hh["fallback"],
                                                                     hh["fallback_waited"], float(W), dfb, slo, bin_s)
                                         for dfb in D_FB}}
                out.setdefault(t, {}).setdefault(tg, {})[W] = rows
    return {"slo_s": SLO_S, "d_fb_s": list(D_FB), "bin_s": bin_s, "by_tier": out}


# ---------------------------------------------------------------- Q-3
PARTS = ("fallback_zero_demand", "fallback_overflow", "stranding", "routing")


def decompose(x: Mapping, W: str) -> Optional[dict]:
    """The four parts of a tag's gap at W (module docstring) and the residual; None when a value is missing."""
    y = _bw(x, W)
    fl = x.get("fluid") or {}
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


def q3(s: Mapping) -> dict:
    by_tw: dict = {}
    allr: dict = {}
    max_res = 0.0
    for t, w, c, x in _cells(s):
        for W in WAITS:
            bill = _bw(x.get(BILL), W).get("C_replay")
            for tg in TAGS:
                y = x.get(tg) or {}
                p = decompose(y, W)
                if p is None:
                    continue
                max_res = max(max_res, abs(p["residual_usd"]))
                hr = y.get("headroom") or {}
                row = {**p, "E": _bw(y, W).get("error"), "gap_over_bill": _div(p["gap_usd"], bill),
                       "lease_usd": y.get("lease_usd"), "headroom_all": hr.get("share_all"),
                       "headroom_overflow": hr.get("share_overflow"),
                       "zero_demand_share_of_gap": _div(p["fallback_zero_demand"], p["gap_usd"])
                       if p["gap_usd"] > 0 else None}
                by_tw.setdefault(W, {}).setdefault(t, {}).setdefault(w, {}).setdefault(tg, []).append(row)
                allr.setdefault(W, {}).setdefault(tg, []).append(row)
    keys = PARTS + ("gap_usd", "E", "gap_over_bill", "lease_usd", "headroom_all", "headroom_overflow",
                    "zero_demand_share_of_gap")

    def med(rows):
        return {k: median(r[k] for r in rows) for k in keys} | {"n": len(rows)}
    return {"parts": list(PARTS), "max_abs_residual_usd": max_res,
            "by_tier_window": {W: {t: {w: {tg: med(r) for tg, r in b.items()} for w, b in a.items()}
                                   for t, a in x.items()} for W, x in by_tw.items()},
            "overall": {W: {tg: med(r) for tg, r in x.items()} for W, x in allr.items()}}


# ---------------------------------------------------------------- headline and the whole analysis
def headline(r1: Mapping, r2: Mapping, r3: Mapping) -> dict:
    o = r1["overall"]
    h: dict = {"rule": r1["rule"],
               "E_median": {W: o[W]["E_median"] for W in WAITS if W in o},
               "E_abs_median": {W: o[W]["E_abs_median"] for W in WAITS if W in o},
               "n_E_negative": {W: o[W]["n_E_negative"] for W in WAITS if W in o},
               "bill_E_median": {W: o[W]["bill_E_median"] for W in WAITS if W in o},
               "bill_n_E_negative": {W: o[W]["bill_n_E_negative"] for W in WAITS if W in o},
               "wins": {W: o[W]["wins"] for W in WAITS if W in o},
               "n_cells": {W: o[W]["n_cells"] for W in WAITS if W in o},
               "same_order": {W: o[W]["same_order"] for W in WAITS if W in o},
               "delta_median": {W: o[W]["delta"]["median"] for W in WAITS if W in o}}
    lat: dict = {}
    for t, a in (r2.get("by_tier") or {}).items():
        for tg in TAGS:
            for W in (W0, W_STAR):
                rows = (a.get(tg) or {}).get(W) or {}
                if not rows:
                    continue
                lat.setdefault(t, {}).setdefault(tg, {})[W] = {
                    cn: {"fallback_share": (rows.get(cn) or {}).get("fallback_share"),
                         "p99_s": (((rows.get(cn) or {}).get("ttft") or {}).get("1") or {}).get("p99"),
                         "slo_attainment": (((rows.get(cn) or {}).get("ttft") or {}).get("1") or {}).get(
                             "slo_attainment")}
                    for cn in CLASSES + ("all",)}
    h["latency_at_d_fb_1"] = lat
    h["q3_overall"] = {W: {tg: {k: (x or {}).get(k) for k in ("gap_usd", "E", "gap_over_bill", "lease_usd",
                                                              "headroom_all", "zero_demand_share_of_gap")}
                           for tg, x in (r3["overall"].get(W) or {}).items()} for W in (W0, W_STAR)}
    return h


def analyse(s: Mapping, hist: Mapping, ref: Optional[Mapping]) -> dict:
    r0 = q0(s, ref)
    r1 = q1(s)
    r2 = q2(s, hist)
    r3 = q3(s)
    return {"q0": r0, "q1": r1, "q2": r2, "q3": r3, "headline": headline(r1, r2, r3)}


def registration(sha: str, repo=None) -> dict:
    """This file's sha256 against the one design/ms8/registration.md records (read from the working tree of `repo`,
    default this repository): {path, exists, registered_sha256, analysis_sha256, matches}."""
    f = Path(repo if repo is not None else paths.REPO) / REGISTRATION
    text = f.read_text(encoding="utf-8", errors="replace") if f.is_file() else None
    m = REG_SHA_RE.search(text) if text else None
    want = m.group(1) if m else None
    return {"path": REGISTRATION, "exists": f.is_file(), "registered_sha256": want, "analysis_sha256": sha,
            "matches": want is not None and want == sha}


def input_record(name: str, f: Path, d: Optional[Mapping]) -> dict:
    m = (d or {}).get("meta") or {}
    g = m.get("gate") or {}
    return {"name": name, "file": f"out/{INPUTS[name]}", "exists": f.is_file(),
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None,
            "git_revision": m.get("git_revision"), "reduced": bool(m.get("reduced")), "gate_kind": g.get("kind"),
            "gate_ok": g.get("ok"), "gate_enforced": g.get("enforced")}


def run_analysis(root=None, repo=None, out=None) -> Optional[dict]:
    """The analysis from <root>/out/ (module docstring), written to <out>/analysis.json and analysis.md; None (and
    nothing written) when an input is missing."""
    r = mc.ms3_root(root) / "out"
    files = {k: r / v for k, v in INPUTS.items()}
    data = {k: mc.read_json(f) for k, f in files.items()}
    missing = [k for k, d in data.items() if not isinstance(d, dict)]
    if missing:
        for k in missing:
            print(f"[e8q_analysis] missing or unreadable input: {files[k]}", file=sys.stderr)
        return None
    sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    reg = registration(sha, repo)
    ins = {k: input_record(k, files[k], data[k]) for k in INPUTS}
    s = ins["summary"]
    full = bool(reg["matches"]) and s["exists"] and not s["reduced"] and s["gate_ok"] is True \
        and s["gate_enforced"] is True
    a = analyse(data["summary"], data["hist"], data["e8v2"])
    a = {"meta": {"exp": "e8q", "spec": SPEC, "git_revision": mc.git_revision(), "analysis_sha256": sha,
                  "registration": reg, "inputs": {x["file"]: x["sha256"] for x in ins.values()},
                  "input_records": list(ins.values()), "reduced": s["reduced"], "registered_full_inputs": full,
                  "label": "exploratory: E8 v2's replay with a queue (design/ms8/plan.md D1, D4); no p-values"},
         **a}
    if not reg["matches"]:
        print(f"[e8q_analysis] WARNING: this file's sha256 {sha[:12]} is not the one {REGISTRATION} records "
              f"({str(reg['registered_sha256'])[:12]}); the output says so (meta.registration)", file=sys.stderr)
    if not full:
        print(f"[e8q_analysis] not a registered full analysis (registration matches {reg['matches']}; summary "
              f"reduced {s['reduced']}, gate ok {s['gate_ok']}, enforced {s['gate_enforced']})", file=sys.stderr)
    od = Path(out) if out is not None else r / "e8q"
    mc.dump_json(a, od / "analysis.json")
    mc.write_text(report(a), od / "analysis.md")
    return a


def report(a: Mapping) -> str:
    m = a["meta"]
    rg = m["registration"]
    L = ["# E8q: analysis (" + SPEC + ")", "", "Exploratory (design/ms8/plan.md D4); no p-values.", "",
         f"Analysis sha256 {m['analysis_sha256'][:12]}; {rg['path']} records {str(rg['registered_sha256'])[:12]}; "
         f"matches {rg['matches']}; registered full inputs {m['registered_full_inputs']}; reduced {m['reduced']}.", ""]
    q = a["q0"]
    L += ["## Q-0 (identity at W = 0 with E8 v2)", "",
          f"status {q['status']}: {q['n_equal']} of {q['n']} equal (expected {q['n_expected']}); max relative "
          f"differences {q['max_rel_diff']}", ""]
    o = a["q1"]["overall"]
    rows = [[W, x["n_cells"], *(x["E_median"][t] for t in TAGS), x["delta"]["median"], x["wins"], x["same_order"]]
            for W, x in o.items()]
    L += ["## Q-1 (over all cells; Delta = min over BL1-BO, BL5-cur of r - r(Sublet), r over the replayed bill)", "",
          mc.md_table(["W s", "cells", *(f"E {t}" for t in TAGS), "Delta median", "wins", "same order"], rows), "",
          f"Rule: {json.dumps(a['q1']['rule'], sort_keys=True)}", ""]
    rows = [[W, *(x["E_abs_median"][t] for t in TAGS), *(x["n_E_negative"][t] for t in TAGS), x["bill_E_median"],
             x["bill_n_E_negative"]] for W, x in o.items()]
    L += ["Median |E| and cells with E < 0 per tag, and the bill's own E (no policy):", "",
          mc.md_table(["W s", *(f"|E| {t}" for t in TAGS), *(f"E<0 {t}" for t in TAGS), "bill E median",
                       "bill E<0"], rows), ""]
    rows = []
    for t, x in a["q2"]["by_tier"].items():
        for tg, y in x.items():
            for W, z in y.items():
                for cn in CLASSES + ("all",):
                    v = z[cn]
                    if not v["copies"]:
                        continue
                    tt = v["ttft"]["1"]
                    rows.append([t, tg, W, cn, v["copies"], v["fallback_share"], v["interrupted_share"], tt["p50"],
                                 tt["p99"], tt["p999"], tt.get("slo_attainment")])
    L += ["## Q-2 (per tier; TTFT at D_fb = 1 s; classes without copies left out)", "",
          mc.md_table(["tier", "tag", "W s", "class", "copies", "fallback share", "interrupted", "P50 s", "P99 s",
                       "P99.9 s", "SLO att."], rows), ""]
    rows = [[W, tg, *(x[k] for k in PARTS), x["gap_usd"], x["E"], x["gap_over_bill"], x["lease_usd"],
             x["headroom_all"]] for W, y in a["q3"]["overall"].items() for tg, x in y.items()]
    L += ["## Q-3 (medians over all cells, USD)", "",
          mc.md_table(["W s", "tag", *PARTS, "gap", "E", "gap / bill", "lease", "headroom"], rows), "",
          f"Largest |residual| {a['q3']['max_abs_residual_usd']:.3g} USD", ""]
    L += ["## Headline", "", "```json", json.dumps(a["headline"], indent=1, sort_keys=True), "```", ""]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.e8q_analysis", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="folder whose out/ holds e8q/ and e8v2/a/ (default MS3_ROOT or this "
                                                 "repository's code/sim)")
    ap.add_argument("--out", type=Path, default=None, help="output folder (default <root>/out/e8q)")
    a = ap.parse_args(argv)
    res = run_analysis(a.root, out=a.out)
    if res is None:
        return 2
    r = res["q1"]["rule"]
    print(f"[e8q_analysis] Q-0 {res['q0']['status']} ({res['q0']['n_equal']} of {res['q0']['n']}); Q-1 holds "
          f"{r['holds']} (Sublet's median E {r['sublet_E_median_w0']} -> {r['sublet_E_median_w_star']}, wins "
          f"{r['wins_w0']} -> {r['wins_w_star']})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
