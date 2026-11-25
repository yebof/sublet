"""MS7 extract: the counts and references that the revised manuscript prints, under one key per number.


Three parts, each a reference computed after the registered analyses from the runs they read; none changes a
registered analysis or its outputs (design/ms7/registration.md §3), and the supplement labels each as computed after
the analysis.

1. guard_fb: whether the safe expert S = Comb(FB, PD) followed all-fallback (FB) at every slot, and whether the guard
   aborted, in the guarded runs of the further runs and of the confirmation's families. Sources (versioned):
   code/sim/out/e7c/<part>/summary.json, code/sim/out/e7o/<part>/summary.json and, after the X4/X5 runs,
   code/sim/out/e7r/eval/summary.json (guarded[]: s_fb_all, aborted, the fields of ms5b_common.guard_extras),
   code/sim/out/sublet_v2/fam/summary.json (guarded[], by the family source of the
   job id, src=F1, CF1, F2, CF2, F3, CF3); code/sim/out/e8v2/a/summary.json (cells.<tier>.<win>.<c>.Sublet.guard). And
   the sensitivity runs of S1 v2 (code/sim/out/s1v2/<part>/runs/*.json, not versioned; sha256 recorded): Sublet's
   record a8 (safe_followed, aborted, projection slots) per point and week.
   - guard_fb.further.{runs,s_fb_all,aborted,by_part}: every guarded run of e7c lag, e7o fwd and rev and e7r eval
     (by_part keys e7c/lag, e7o/fwd, e7o/rev and e7r_eval; both guarded tags, Sublet and Greedy + guard; e7r eval's
     under L-tr and the six new stress lenders); guard_fb.further.lag_oos.{runs,s_fb_all,aborted}: the lagged-demand
     and held-out-calibration parts alone (the population Supplement S-F.2's run populations name);
     guard_fb.further.by_part.e7r_eval.projection.<tag>.by_mode.<mode>.{runs,runs_projected,projected_slots,aborted}
     and .other_modes.{runs,runs_projected,projected_slots}_{min,max} over the six new stress lenders (Section VII-B's
     projected slots under the further stress lenders); check: S on FB in every one and no projected run aborts while
     S is on FB
   - guard_fb.fam_sublet.by_src.<src> and .by_family.<F1|F2|F3> (a source CFk joins family Fk)
     .{runs,s_fb_all,switch_runs,start_pd_runs,aborted}: Sublet on the core families; start_pd_runs: S off FB
     without a switch, so S started on the primal-dual
   - guard_fb.e8v2_sublet.{runs,s_fb_all,aborted}; guard_fb.s1v2_sublet.{runs,s_fb_all,aborted} with by_point
     (runs, s_fb_all, aborted, projected_slots_max) over the sweep and w0 parts
2. replay: the request-level replay of E8 v2 (code/sim/out/e8v2/a/runs/pairs/*.json, not versioned; sha256 recorded),
   36 cells (tier S, M, L x smoothing window 5, 15, 60 min x alignment 1-4). The registered analysis states each
   replayed cost over the fluid all-fallback bill (e8v2.py: r0_replay over the fluid BL0a). The replay serves the
   per-second stream of request copies from the borrower's own capacity first, in the same order for every policy, so
   the copies the own capacity serves are the same for every policy of a cell (checked: tokens.own and tokens.stream
   equal over the cell's runs), and the replayed all-fallback bill is the fallback price of every other copy:
   bill_replay = u (tokens.stream - tokens.own), with u the fallback price per weighted token,
   costs.fallback / (tokens.fallback + tokens.stranded_remainder) (replay.loop.token_costs; checked equal over the
   cell's runs). Per cell and tag: C_fluid, C_replay (checked against code/sim/out/e8v2/analysis.json cells),
   r0_fluid = C_fluid / bl0a_fluid, r0_replay = C_replay / bill_replay, and overflow_growth = bill_replay / bl0a_fluid.
   - replay.by_tag.<tag>.{r0_fluid,r0_replay}.{median,min,max}: over the 36 cells
   - replay.by_tag.<tag>.saving_pct.{fluid,replay}.median: 100 (1 - median r0)
   - replay.overflow_growth.{median,min,max}
   - replay.by_tier_window.<tier>.<win>.<tag>.{r0_fluid,r0_replay} (medians over the 4 alignments)
   - replay.sublet_below_both.{fluid,replay}: cells in which Sublet costs less than both Greedy, back-off and
     RetroRenting-style (checked against the analysis's headline counts)
3. sens: the sensitivity points of S1 v2 (code/sim/out/s1v2/analysis.json, versioned).
   - sens.points.<point>.{margin_median,weeks_hold,n_weeks,sublet_saving_pct,a9_saving_pct,guard_price_median} and,
     where part w0 ran the point, {w0_sublet_median,w0_a9_median}: margin = the better of Greedy, back-off and
     RetroRenting-style minus Sublet (vs_pair), guard price = Sublet minus critical-ratio renting (sublet_minus_a9_r0),
     W0 medians over the w0 part's weeks
   - sens.guard_price.{min,min_point,max,max_point}: the least and largest median guard price over the points
   - sens.lose_all_weeks: the points at which Sublet loses every week; sens.lose_some_weeks: those with 0 < weeks_hold
     < n_weeks
   - sens.near_bill.<point>.<week>.{r0,aborted,s_fb_all,projected}: Sublet's sweep runs within 1% of the all-fallback
     bill or above it, with the guard's record (from part 1's run files)
4. e5: the redundancy cells of E5 v2 by menu (code/sim/out/e5v2/analysis.json headline, versioned): e5.<menu>.{cells,
   hold}, hold = the cells in which Sublet costs less than every baseline in every seed (not in cells_with_failures).
5. bounds (items RC5, RC6 and RC17; references computed after the registered
   analyses, like parts 1-4): Theorem 11's bound with S on FB at every slot, ALG(T) <= bill + B(T), checked run by run
   from the guard's record a8 (B_T = B(T) = min{B_peak(T), LB'(T)}; the bill = bl0a_usd, which equals the safe expert's
   C_S(T), checked). excess = ALG - bl0a_usd - B_T, USD (<= 0 when the bound holds); W0 = the largest r0 over the five
   stress modes (ms5b_common.w0_of, as e7o_analysis.py defines it).
   - bounds.oos.<fold>.<arm>: Sublet's cells of X2 (code/sim/out/e7o/<fold>/runs/*tag__Sublet*.json, not versioned;
     sha256 recorded), each cell {bill_usd, W0, W0_mode (checked against code/sim/out/e7o/analysis.json per_cell),
     B_T_usd and B_T_over_bill {min, max} over the cell's runs, B_T_eq_Wk_T, runs, s_fb_all, aborted,
     max_excess_usd}; per fold and arm {runs, s_fb_all, aborted, max_excess_usd, w0_above_1 (the cells with W0 > 1),
     B_T_over_bill_w0_above_1 {min, max}}
   - bounds.oos.by_arm.<arm>: the same over both folds (w0_above_1 as "<fold>:<cell>")
   - bounds.sens.by_point.<part>:<point>: Sublet's S1 v2 runs {runs, max_excess_usd, B_T_over_bill {min, max}}
   - bounds.sens.near_bill.<point>.<week>: sens.near_bill's runs with {r0, B_T_over_bill, bound_r0 = 1 + B_T/bill,
     excess_usd}
   - bounds.sens.w0.<point>.<week>: part w0's weeks {W0, W0_mode, W0_a9, bound_r0 (1 + B_T/bill of the W0 run),
     gap = bound_r0 - W0}; bounds.sens.w0_a9_above_1 {weeks, gap_max, max_excess_usd}: the point-weeks at which
     critical-ratio renting's W0 exceeds the bill
   - bounds.gp_week.<week>: Greedy + guard on the confirmation weeks (code/sim/out/sublet_v2/main/summary.json,
     versioned: runs[].r0 and guarded[].B_T) {W0, W0_mode, bill_usd, B_T_usd, bound_r0, gap}; bounds.gp_week_summary
     {W0_max, W0_max_week, gap_max, B_T_over_bill_max}

Run (from the repository root, under the project's 3G cap; about 2 min):
  systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \\
      ~/venv/bin/python code/sim/figs/ms7_review_extract.py [--runs-root CHECKOUT]
Options: --root DIR (default the repository), --runs-root DIR (the checkout that holds the unversioned run files,
default --root; a git worktree has none), --out PATH (default code/sim/out/ms7/review_extract.json under --root).
Exits 2 when an input is missing and 1 when a check fails.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = "code/sim/out/ms7/review_extract.json"
REL_TOL = 1e-9
# guard_fb.further.by_part key -> the part's folder under code/sim/out/ (e7r_eval added after the X4/X5 runs: the
# guarded runs of e7r part eval, Sublet and Greedy + guard under L-tr and the six new stress lenders)
FURTHER = {"e7c/lag": "e7c/lag", "e7o/fwd": "e7o/fwd", "e7o/rev": "e7o/rev", "e7r_eval": "e7r/eval"}
FURTHER_LAG_OOS = ("e7c/lag", "e7o/fwd", "e7o/rev")     # the lagged-demand and held-out-calibration parts
REPLAY_TAGS = ("Sublet", "A9", "BL1-BO", "BL5-cur")
BASELINES = ("BL1-BO", "BL5-cur")
NEAR_BILL = 0.99


class Missing(Exception):
    pass


class CheckFailed(Exception):
    pass


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def close(a: float, b: float, tol: float = REL_TOL) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def summ(xs) -> dict:
    xs = list(xs)
    return {"median": statistics.median(xs), "min": min(xs), "max": max(xs), "n": len(xs)}


class Reader:
    """Versioned inputs from root, the unversioned run files (runs=True) from runs_root; keys repository-relative."""

    def __init__(self, root: Path, runs_root: Path | None = None):
        self.root = Path(root)
        self.runs_root = Path(runs_root) if runs_root else self.root
        self.sha: dict = {}

    def json(self, rel: str, runs: bool = False):
        p = (self.runs_root if runs else self.root) / rel
        if not p.exists():
            raise Missing(rel)
        self.sha[rel] = sha256(p)
        return json.loads(p.read_text(encoding="utf-8"))

    def glob(self, pattern: str, runs: bool = False) -> list:
        base = self.runs_root if runs else self.root
        return sorted(str(Path(f).relative_to(base)) for f in glob.glob(str(base / pattern)))


def _count(rows) -> dict:
    rows = list(rows)
    return {"runs": len(rows), "s_fb_all": sum(1 for r in rows if r.get("s_fb_all") is True),
            "aborted": sum(1 for r in rows if r.get("aborted") is True)}


def _projection(g) -> dict:
    """Projection in the guarded runs of one part, per tag and lender mode: {runs, runs_projected (runs with at
    least one projected slot), projected_slots, aborted}; per tag, `other_modes`: the same over the modes other than
    L-tr as min-max over those modes (e7r eval: the six new stress lenders)."""
    out = {}
    for t in sorted({r["tag"] for r in g}):
        rows = [r for r in g if r["tag"] == t]
        by_mode = {}
        for m in sorted({r["mode"] for r in rows}):
            rs = [r for r in rows if r["mode"] == m]
            by_mode[m] = {"runs": len(rs), "runs_projected": sum(1 for r in rs if (r.get("projected_slots") or 0) > 0),
                          "projected_slots": sum(int(r.get("projected_slots") or 0) for r in rs),
                          "aborted": sum(1 for r in rs if r.get("aborted") is True)}
        other = [v for m, v in by_mode.items() if m != "L-tr"]
        out[t] = {"by_mode": by_mode, "other_modes": {
            "modes": sorted(m for m in by_mode if m != "L-tr"),
            **{f"{k}_{f.__name__}": f(v[k] for v in other)
               for k in ("runs", "runs_projected", "projected_slots") for f in (min, max)},
            "aborted": sum(v["aborted"] for v in other)} if other else None}
    return out


def guard_fb(rd: Reader) -> dict:
    out = {"further": {"by_part": {}}}
    allg, lag_oos = [], []
    for key, part in FURTHER.items():
        g = rd.json(f"code/sim/out/{part}/summary.json").get("guarded") or []
        if not g:
            raise CheckFailed(f"{part}: no guarded runs")
        out["further"]["by_part"][key] = {"by_tag": {t: _count(r for r in g if r["tag"] == t)
                                                     for t in sorted({r["tag"] for r in g})}, **_count(g)}
        allg += g
        if key in FURTHER_LAG_OOS:
            lag_oos += g
        else:
            out["further"]["by_part"][key]["projection"] = _projection(g)
    out["further"].update(_count(allg))
    out["further"]["lag_oos"] = _count(lag_oos)
    if out["further"]["s_fb_all"] != out["further"]["runs"]:
        raise CheckFailed("further runs: S left FB in some guarded run")
    bad = [r for r in allg if r.get("project") and r.get("aborted") and r.get("s_fb_all")]
    if bad:
        raise CheckFailed("a projected run aborted with S on FB (Theorem 11(b))")
    fam = [r for r in rd.json("code/sim/out/sublet_v2/fam/summary.json")["guarded"] if r["tag"] == "Sublet"]
    by_src: dict = {}
    for r in fam:
        m = re.search(r"src=([A-Z0-9]+)", r["job"])
        by_src.setdefault(m.group(1) if m else "?", []).append(r)
    def fam_row(rs):
        return {**_count(rs), "switch_runs": sum(1 for r in rs if (r.get("switches") or 0) > 0),
                "start_pd_runs": sum(1 for r in rs if not r.get("s_fb_all") and not (r.get("switches") or 0))}
    by_family = {}
    for s, rs in by_src.items():
        by_family.setdefault(s[1:] if s.startswith("C") else s, []).extend(rs)
    out["fam_sublet"] = {"by_src": {s: fam_row(rs) for s, rs in sorted(by_src.items())},
                         "by_family": {f: fam_row(rs) for f, rs in sorted(by_family.items())}, **_count(fam)}
    e8 = rd.json("code/sim/out/e8v2/a/summary.json")["cells"]
    gs = [e8[t][w][c]["Sublet"]["guard"] for t in e8 for w in e8[t] for c in e8[t][w]
          if isinstance(e8[t][w][c].get("Sublet"), dict) and e8[t][w][c]["Sublet"].get("guard")]
    out["e8v2_sublet"] = _count(gs)
    return out


NEAR_KEYS = ("r0", "mode", "aborted", "s_fb_all", "projected")     # the fields of sens.near_bill's records


def _bound_fields(x: dict, a8: dict) -> dict:
    """Part 5's fields of one guarded run: ALG, the bill, B(T), the cap B_peak(T) and the safe expert's C_S(T)."""
    cert = a8.get("certificate") if isinstance(a8.get("certificate"), dict) else {}
    ol = a8.get("online_lb") if isinstance(a8.get("online_lb"), dict) else {}
    return {"ALG": x.get("ALG"), "bill": x.get("bl0a_usd"), "B_T": a8.get("B_T"), "Wk_T": ol.get("Wk_T"),
            "C_S_T": cert.get("C_S_T")}


def s1v2_runs(rd: Reader, a9: dict | None = None) -> dict:
    """{(part, point, week): Sublet's run records} from the S1 v2 run files (sha256 recorded); when a9 is a dict, it
    receives critical-ratio renting's {(part, point, week): {mode: r0}}."""
    out = {}
    for part in ("sweep", "w0"):
        files = rd.glob(f"code/sim/out/s1v2/{part}/runs/*.json", runs=True)
        if not files:
            raise Missing(f"code/sim/out/s1v2/{part}/runs/*.json")
        for rel in files:
            d = rd.json(rel, runs=True)
            for x in d.get("runs") or []:
                if a9 is not None and x.get("tag") == "A9":
                    a9.setdefault((part, str(d["point"]), str(d["c"])), {})[x.get("mode")] = x.get("r0")
                if x.get("tag") != "Sublet":
                    continue
                a8 = x.get("a8") or {}
                proj = a8.get("projection") if isinstance(a8.get("projection"), dict) else {}
                followed = a8.get("safe_followed") or []
                out.setdefault((part, str(d["point"]), str(d["c"])), []).append({
                    "r0": x.get("r0"), "mode": x.get("mode"), "aborted": bool(a8.get("aborted")),
                    "s_fb_all": bool(followed) and all(f[0] == "FB" for f in followed),
                    "projected": int(proj.get("slots") or 0), **_bound_fields(x, a8)})
    return out


def sens(rd: Reader, runs: dict) -> dict:
    allr = [x for xs in runs.values() for x in xs]
    by_point: dict = {}
    for (part, pt, wk), xs in runs.items():
        b = by_point.setdefault(f"{part}:{pt}", {"runs": 0, "s_fb_all": 0, "aborted": 0, "projected_slots_max": 0})
        for x in xs:
            b["runs"] += 1
            b["s_fb_all"] += int(x["s_fb_all"])
            b["aborted"] += int(x["aborted"])
            b["projected_slots_max"] = max(b["projected_slots_max"], x["projected"])
    near = {}
    for (part, pt, wk), xs in runs.items():
        for x in xs:
            if part == "sweep" and x["mode"] in (None, "L-tr") and (x["r0"] or 0) >= NEAR_BILL:
                near.setdefault(pt, {})[wk] = {k: x[k] for k in NEAR_KEYS}
    an = rd.json("code/sim/out/s1v2/analysis.json")
    w0p = an["w0"]["points"]
    pts = {}
    for pt, p in an["points"].items():
        bt = p["by_tag"]
        row = {"label": p.get("label"), "row": p.get("row"), "margin_median": p["vs_pair"]["delta_median"],
               "weeks_hold": p["vs_pair"]["weeks_hold"], "n_weeks": p["vs_pair"]["n_weeks"],
               "sublet_saving_pct": bt["Sublet"]["median_saving_pct"], "a9_saving_pct": bt["A9"]["median_saving_pct"],
               "guard_price_median": p["sublet_minus_a9_r0"]["median"]}
        if pt in w0p:
            row["w0_sublet_median"] = statistics.median(w0p[pt]["W0"]["Sublet"].values())
            row["w0_a9_median"] = statistics.median(w0p[pt]["W0"]["A9"].values())
        pts[pt] = row
    gp = sorted((r["guard_price_median"], pt) for pt, r in pts.items())
    return {"s1v2_sublet": {**_count(allr), "by_point": by_point}, "points": pts,
            "guard_price": {"min": gp[0][0], "min_point": gp[0][1], "max": gp[-1][0], "max_point": gp[-1][1]},
            "lose_all_weeks": sorted(pt for pt, r in pts.items() if r["weeks_hold"] == 0),
            "lose_some_weeks": sorted(pt for pt, r in pts.items() if 0 < r["weeks_hold"] < r["n_weeks"]),
            "near_bill_threshold": NEAR_BILL, "near_bill": near}


def replay(rd: Reader) -> dict:
    an = rd.json("code/sim/out/e8v2/analysis.json")
    files = rd.glob("code/sim/out/e8v2/a/runs/pairs/*.json", runs=True)
    if len(files) != 36:
        raise Missing(f"code/sim/out/e8v2/a/runs/pairs/*.json: {len(files)} of 36 files")
    cells = {}
    for rel in files:
        d = rd.json(rel, runs=True)
        tier, win, c = str(d["tier"]), str(d["win"]), str(d["c"])
        bl0a = float(d["references"]["bl0a_usd"])
        streams = {t: (r["replay"]["tokens"]["stream"], r["replay"]["tokens"]["own"]) for t, r in d["runs"].items()}
        s0 = next(iter(streams.values()))
        if not all(close(a, s0[0]) and close(b, s0[1]) for a, b in streams.values()):
            raise CheckFailed(f"{rel}: tokens.stream or tokens.own differ between the cell's runs")
        units = []
        for t, r in d["runs"].items():
            tk, co = r["replay"]["tokens"], r["replay"]["costs"]
            fb = tk["fallback"] + tk["stranded_remainder"]
            if fb > 0:
                units.append(co["fallback"] / fb)
        if not units or not all(close(u, units[0], 1e-6) for u in units):
            raise CheckFailed(f"{rel}: the fallback price per token differs between the cell's runs")
        bill = units[0] * (s0[0] - s0[1])
        row = {"bl0a_fluid_usd": bl0a, "bill_replay_usd": bill, "overflow_growth": bill / bl0a, "by_tag": {}}
        for t in REPLAY_TAGS:
            r = d["runs"][t]
            ref = an["cells"][tier][win][c]
            if not (close(r["C_fluid"], ref["fluid"][t]) and close(r["C_replay"], ref["replay"][t])):
                raise CheckFailed(f"{rel}: {t}'s costs differ from code/sim/out/e8v2/analysis.json")
            row["by_tag"][t] = {"C_fluid": r["C_fluid"], "C_replay": r["C_replay"], "r0_fluid": r["C_fluid"] / bl0a,
                                "r0_replay": r["C_replay"] / bill}
        cells.setdefault(tier, {}).setdefault(win, {})[c] = row
    flat = [cells[t][w][c] for t in cells for w in cells[t] for c in cells[t][w]]
    by_tag = {}
    for t in REPLAY_TAGS:
        f = summ(x["by_tag"][t]["r0_fluid"] for x in flat)
        r = summ(x["by_tag"][t]["r0_replay"] for x in flat)
        by_tag[t] = {"r0_fluid": f, "r0_replay": r,
                     "saving_pct": {"fluid": 100.0 * (1.0 - f["median"]), "replay": 100.0 * (1.0 - r["median"])}}
    below = {"fluid": sum(1 for x in flat if all(x["by_tag"]["Sublet"]["C_fluid"] < x["by_tag"][b]["C_fluid"]
                                                 for b in BASELINES)),
             "replay": sum(1 for x in flat if all(x["by_tag"]["Sublet"]["C_replay"] < x["by_tag"][b]["C_replay"]
                                                  for b in BASELINES))}
    head = an["headline"]["cells"]
    if (below["fluid"], below["replay"]) != (head["sublet_beats_pair_fluid"], head["sublet_beats_pair_replay"]):
        raise CheckFailed("Sublet's counts below both baselines differ from the analysis's headline")
    btw = {t: {w: {g: {k: statistics.median(cells[t][w][c]["by_tag"][g][k] for c in cells[t][w])
                       for k in ("r0_fluid", "r0_replay")} for g in REPLAY_TAGS} for w in cells[t]} for t in cells}
    return {"definition": "r0_replay = C_replay / (u (tokens.stream - tokens.own)), the replayed all-fallback bill; "
                          "r0_fluid = C_fluid / the fluid all-fallback bill (bl0a_usd)",
            "n_cells": len(flat), "by_tag": by_tag, "overflow_growth": summ(x["overflow_growth"] for x in flat),
            "sublet_below_both": below, "by_tier_window": btw, "cells": cells}


# ---------------------------------------------------------------------------------------------------------------
# Part 5: Theorem 11's bound, ALG(T) <= bill + B(T) with S on FB at every slot, run by run
STRESS = ("L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co")    # ms5b_common.stress_modes(), checked against e7o
OOS_FOLDS = ("fwd", "rev")                                       # e7o_analysis.FOLDS
OOS_ARMS = ("oos", "is")                                         # e7o_analysis.ARMS
BOUND_DEF = ("excess = ALG - bl0a_usd - B_T (USD; <= 0 when Theorem 11's bound with S on FB holds), B_T = B(T) = "
             "min{B_peak(T), LB'(T)} from the run's a8 record, bl0a_usd checked equal to the safe expert's C_S(T); "
             "W0 = the largest r0 over the five stress modes (ms5b_common.w0_of); bound_r0 = 1 + B_T / bl0a_usd")


def _excess(f: dict) -> float:
    return f["ALG"] - f["bill"] - f["B_T"]


def _w0(r0: dict) -> tuple:
    """(W0, its mode) over the five stress modes, ties to the earlier mode (ms5b_common.w0_of)."""
    miss = [m for m in STRESS if r0.get(m) is None]
    if miss:
        raise CheckFailed(f"W0: stress modes without r0: {miss}")
    m = max(STRESS, key=lambda k: (r0[k], -STRESS.index(k)))
    return float(r0[m]), m


def _check_bound(where: str, f: dict) -> None:
    """The bill is the safe expert's C_S(T) and, with S on FB, ALG <= bill + B(T) up to the certificate tolerance."""
    if f["C_S_T"] is not None and not close(f["C_S_T"], f["bill"], 1e-9):
        raise CheckFailed(f"{where}: C_S(T) differs from the all-fallback bill")
    if f["s_fb_all"] and _excess(f) > 1e-6 * max(1.0, f["bill"]):
        raise CheckFailed(f"{where}: ALG exceeds the bill plus B(T) with S on FB (Theorem 11)")


def _range(xs) -> dict:
    xs = list(xs)
    return {"min": min(xs), "max": max(xs)} if xs else None


def oos_bounds(rd: Reader) -> dict:
    an = rd.json("code/sim/out/e7o/analysis.json")
    if tuple(an["stress_modes"]) != STRESS:
        raise CheckFailed("e7o: the stress modes differ from ms5b_common's five")
    out: dict = {}
    by_arm: dict = {arm: {"w0_above_1": [], "B_T_over_bill_w0_above_1": [], "runs": 0, "s_fb_all": 0, "aborted": 0,
                          "max_excess_usd": None} for arm in OOS_ARMS}
    for fold in OOS_FOLDS:
        fa = an["folds"][fold]
        for arm in OOS_ARMS:
            cells = {}
            for k in fa["cells"]:
                rel = f"code/sim/out/e7o/{fold}/runs/e7o__{fold}__k__cell__arm__{arm}__tag__Sublet__cell__{k}.json"
                d = rd.json(rel, runs=True)
                recs = []
                for x in d.get("runs") or []:
                    if x.get("tag") != "Sublet":
                        continue
                    if x.get("status", "ok") != "ok":
                        raise CheckFailed(f"{rel}: a run is not ok")
                    a8 = x.get("a8") or {}
                    f = {"mode": x.get("mode"), "r0": x.get("r0"), "s_fb_all": a8.get("s_fb_all") is True,
                         "aborted": a8.get("aborted") is True, **_bound_fields(x, a8)}
                    _check_bound(f"{rel} {f['mode']}", f)
                    recs.append(f)
                if sorted(f["mode"] for f in recs) != sorted(an["modes"]):
                    raise CheckFailed(f"{rel}: the runs' modes differ from the analysis's")
                w0, w0m = _w0({f["mode"]: f["r0"] for f in recs})
                ref = fa["per_cell"][arm]["Sublet"][str(k)]
                if not close(w0, ref["W0"]) or w0m != ref["W0_mode"]:
                    raise CheckFailed(f"{rel}: W0 differs from code/sim/out/e7o/analysis.json per_cell")
                bill = recs[0]["bill"]
                if not all(close(f["bill"], bill) for f in recs):
                    raise CheckFailed(f"{rel}: the bill differs between the cell's runs")
                cells[str(k)] = {"bill_usd": bill, "W0": w0, "W0_mode": w0m,
                                 "B_T_usd": _range(f["B_T"] for f in recs),
                                 "B_T_over_bill": _range(f["B_T"] / f["bill"] for f in recs),
                                 "B_T_eq_Wk_T": all(f["Wk_T"] is not None and close(f["B_T"], f["Wk_T"]) for f in recs),
                                 "runs": len(recs), "s_fb_all": sum(f["s_fb_all"] for f in recs),
                                 "aborted": sum(f["aborted"] for f in recs),
                                 "max_excess_usd": max(_excess(f) for f in recs)}
            above = [c for c, v in cells.items() if v["W0"] > 1.0]
            row = {"cells": cells, "runs": sum(v["runs"] for v in cells.values()),
                   "s_fb_all": sum(v["s_fb_all"] for v in cells.values()),
                   "aborted": sum(v["aborted"] for v in cells.values()),
                   "max_excess_usd": max(v["max_excess_usd"] for v in cells.values()),
                   "w0_above_1": above,
                   "B_T_over_bill_w0_above_1": _range(x for c in above for x in cells[c]["B_T_over_bill"].values())}
            out.setdefault(fold, {})[arm] = row
            b = by_arm[arm]
            b["w0_above_1"] += [f"{fold}:{c}" for c in above]
            b["B_T_over_bill_w0_above_1"] += [x for c in above for x in cells[c]["B_T_over_bill"].values()]
            for key in ("runs", "s_fb_all", "aborted"):
                b[key] += row[key]
            b["max_excess_usd"] = row["max_excess_usd"] if b["max_excess_usd"] is None else max(b["max_excess_usd"],
                                                                                                  row["max_excess_usd"])
    for b in by_arm.values():
        b["B_T_over_bill_w0_above_1"] = _range(b["B_T_over_bill_w0_above_1"])
    out["by_arm"] = by_arm
    return out


def sens_bounds(rd: Reader, runs: dict, a9: dict) -> dict:
    by_point: dict = {}
    near: dict = {}
    w0: dict = {}
    w0p = rd.json("code/sim/out/s1v2/analysis.json")["w0"]["points"]
    for (part, pt, wk), xs in sorted(runs.items()):
        for x in xs:
            _check_bound(f"s1v2 {part} {pt} {wk} {x['mode']}", x)
        b = by_point.setdefault(f"{part}:{pt}", {"runs": 0, "max_excess_usd": None, "B_T_over_bill": []})
        b["runs"] += len(xs)
        e = max(_excess(x) for x in xs)
        b["max_excess_usd"] = e if b["max_excess_usd"] is None else max(b["max_excess_usd"], e)
        b["B_T_over_bill"] += [x["B_T"] / x["bill"] for x in xs]
        for x in xs:
            if part == "sweep" and x["mode"] in (None, "L-tr") and (x["r0"] or 0) >= NEAR_BILL:
                near.setdefault(pt, {})[wk] = {"r0": x["r0"], "B_T_over_bill": x["B_T"] / x["bill"],
                                               "bound_r0": 1.0 + x["B_T"] / x["bill"], "excess_usd": _excess(x)}
        if part == "w0":
            by_mode = {x["mode"]: x for x in xs}
            v, m = _w0({k: x["r0"] for k, x in by_mode.items()})
            if not close(v, w0p[pt]["W0"]["Sublet"][wk]):
                raise CheckFailed(f"s1v2 w0 {pt} {wk}: Sublet's W0 differs from code/sim/out/s1v2/analysis.json")
            va, _ = _w0(a9[(part, pt, wk)])
            if not close(va, w0p[pt]["W0"]["A9"][wk]):
                raise CheckFailed(f"s1v2 w0 {pt} {wk}: A9's W0 differs from code/sim/out/s1v2/analysis.json")
            x = by_mode[m]
            bound = 1.0 + x["B_T"] / x["bill"]
            w0.setdefault(pt, {})[wk] = {"W0": v, "W0_mode": m, "W0_a9": va, "bound_r0": bound, "gap": bound - v,
                                         "max_excess_usd": max(_excess(y) for y in xs)}
    for b in by_point.values():
        b["B_T_over_bill"] = _range(b["B_T_over_bill"])
    hi = [r for p in w0.values() for r in p.values() if r["W0_a9"] > 1.0]
    return {"by_point": by_point, "near_bill": near, "w0": w0,
            "w0_a9_above_1": {"weeks": len(hi), "gap_max": max((r["gap"] for r in hi), default=None),
                              "max_excess_usd": max((r["max_excess_usd"] for r in hi), default=None)},
            "max_excess_usd": max(b["max_excess_usd"] for b in by_point.values())}


def gp_week(rd: Reader) -> dict:
    """Greedy + guard on the confirmation weeks: per week its W0 and the bound 1 + B(T)/bill of the W0 run."""
    d = rd.json("code/sim/out/sublet_v2/main/summary.json")
    runs = {(r["cell"], r["mode"]): r for r in d["runs"] if r["tag"] == "BL1-GP" and r.get("seed", 0) == 0}
    guard = {(g["cell"], g["mode"]): g for g in d["guarded"] if g["tag"] == "BL1-GP" and g.get("seed", 0) == 0}
    weeks = sorted({c for c, _ in runs}, key=int)
    out = {}
    for wk in weeks:
        v, m = _w0({mm: r["r0"] for (c, mm), r in runs.items() if c == wk})
        if not close(v, d["W0"]["0"]["BL1-GP"][wk]):
            raise CheckFailed(f"sublet_v2 main {wk}: Greedy + guard's W0 differs from the summary's W0")
        r, g = runs[(wk, m)], guard[(wk, m)]
        if not g.get("s_fb_all") or g.get("aborted"):
            raise CheckFailed(f"sublet_v2 main {wk}: Greedy + guard's W0 run left FB or aborted")
        bound = 1.0 + g["B_T"] / r["bl0a_usd"]
        if r["ALG"] - r["bl0a_usd"] - g["B_T"] > 1e-6 * max(1.0, r["bl0a_usd"]):
            raise CheckFailed(f"sublet_v2 main {wk}: Greedy + guard exceeds the bill plus B(T)")
        out[wk] = {"W0": v, "W0_mode": m, "bill_usd": r["bl0a_usd"], "B_T_usd": g["B_T"], "bound_r0": bound,
                   "gap": bound - v}
    top = max(weeks, key=lambda w: out[w]["W0"])
    return {"weeks": out, "summary": {"W0_max": out[top]["W0"], "W0_max_week": top,
                                      "gap_max": max(r["gap"] for r in out.values()),
                                      "B_T_over_bill_max": max(r["bound_r0"] - 1.0 for r in out.values())}}


def build(root: Path = REPO, runs_root: Path | None = None) -> dict:
    rd = Reader(root, runs_root)
    out = {"guard_fb": guard_fb(rd), "replay": replay(rd)}
    a9: dict = {}
    runs = s1v2_runs(rd, a9)
    s = sens(rd, runs)
    out["guard_fb"]["s1v2_sublet"] = s.pop("s1v2_sublet")
    out["sens"] = s
    e5 = rd.json("code/sim/out/e5v2/analysis.json")["headline"]
    keys = list(e5["sublet_vs_best_baseline_median_delta"])
    fail = set(e5["vs_baselines"]["cells_with_failures"])
    out["e5"] = {menu: {"cells": sum(1 for k in keys if k.split(":")[1] == menu),
                        "hold": sum(1 for k in keys if k.split(":")[1] == menu and k not in fail)}
                 for menu in ("short", "long")}
    if sum(v["cells"] for v in out["e5"].values()) != e5["n_cells"]:
        raise CheckFailed("e5v2: the cells by menu do not add up to n_cells")
    gp = gp_week(rd)
    out["bounds"] = {"label": "references computed after the registered analyses (design/ms7/registration.md §3), "
                              "not registered results", "definition": BOUND_DEF,
                     "oos": oos_bounds(rd), "sens": sens_bounds(rd, runs, a9), "gp_week": gp["weeks"],
                     "gp_week_summary": gp["summary"]}
    try:
        rev = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        rev = None
    out["meta"] = {"script": "code/sim/figs/ms7_review_extract.py", "git_revision": rev,
                   "written": datetime.datetime.now().isoformat(timespec="seconds"),
                   "label": "references computed after the registered analyses (design/ms7/registration.md §3), "
                            "not registered results", "inputs": dict(sorted(rd.sha.items()))}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=REPO)
    ap.add_argument("--runs-root", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    try:
        out = build(a.root, a.runs_root)
    except Missing as e:
        print(f"ms7_review_extract: missing input {e}", file=sys.stderr)
        return 2
    except CheckFailed as e:
        print(f"ms7_review_extract: check failed: {e}", file=sys.stderr)
        return 1
    dst = a.out or (a.root / OUT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    print(f"ms7_review_extract: wrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
