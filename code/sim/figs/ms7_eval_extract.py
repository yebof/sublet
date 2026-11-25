"""MS7 Sections VI-C and VII extract: the economics, the guard's records, the insurance family's aborts and alpha_N of
the week instances, under one key per number.

Design: design/ms7/w_spec.md (unit W-X; §2.7 VI-C and §2.8 VII-B, VII-C; §3 Values), in the style of
figs/ms6_eval_extract.py (design/ms6_spec.md §3.3: one versioned file and key per printed number). Every input is a
versioned file; the script reads no run file (code/sim/out/sublet_v2/*/runs/ is not versioned), records the sha256 of
every input it reads under meta.inputs, exits 2 when an input is missing and 1 when a check fails, and writes
code/sim/out/ms7/eval_extract.json. Run (from the repository root, under the project's 3G cap; about 50 s, 40 s of it
the planner check of part 5; peak about 250 MB):
  systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \\
      ~/venv/bin/python code/sim/figs/ms7_eval_extract.py
Options: --root DIR (the tree the JSON inputs are read from; default the repository; the week instances are always
built from the repository's files, sublet.paths), --out PATH, --no-planner-check (tests; the output then records
planner_check null).

Statistic: every "median" is statistics.median over the 16 confirmation weeks of per-week values (the mean of the two
middle values), the median of Table III v2 (ms5b_common.bootstrap_median_ci's point estimate; checked on Sublet's
overflow cell). "Paired per week": a difference or ratio is formed within each week first, then the median is taken.

1. econ: the economics of the 16 confirmation weeks (part main, trace lender L-tr, policy seed 0). Sources:
   code/sim/out/figs/table3_v2.json (per-week overflow and total USD of its rows, data.rows.<tag>.cells.usd), the
   primary baselines from code/sim/out/sublet_v2/analysis.json (H2.set, H1's set; checked against table3_v2's
   caption_source.h1_set), and, for the one primary baseline without a row in Table III v2 (BL5, RetroRenting-style,
   lagged), its overflow r0 x bl0a_usd from code/sim/out/sublet_v2/main/summary.json, the definition table3_v2.py
   uses (checked equal to the table's overflow for every row tag). Total accounting = overflow + the instance's own
   capacity (ms4_common.accountings, total_usd = overflow_usd + own_capacity_usd(inst)); own capacity is
   total - overflow of the table's rows, checked equal over all 14 rows and to fig4v2.json's own_capacity_usd. So a
   USD difference between two policies is the same in both accountings.
   - econ.weeks, econ.primary_set (tags), econ.primary_labels (Table III v2 / registry labels where the table has them)
   - econ.own_capacity_usd.{median,min,max,by_week}: borrowers' own capacity, USD per week (the same for every policy)
   - econ.bl0a_total_usd.{median,by_week}, econ.sublet_total_usd.{median,by_week}: All-fallback's and Sublet's total
     cost, USD per week
   - econ.saving_vs_fallback.usd.{median,min,max,by_week}: BL0a total - Sublet total (= overflow difference), USD per
     week
   - econ.saving_vs_fallback.pct_total.{median,min,max,by_week}: 100 (1 - Sublet total / BL0a total), percent
   - econ.saving_vs_fallback.pct_overflow_median: 100 (1 - r0) median (Table III v2's Saving cell; consistency)
   - econ.margin_vs_cheapest_primary.usd.{median,min,max,by_week}: per week, the smallest total of the primary
     baselines minus Sublet's total (H1's margin in USD: analysis.json H1.margins[w].delta x bl0a_usd, checked)
   - econ.margin_vs_cheapest_primary.pct_total.{median,min,max,by_week}: that margin over the cheapest primary
     baseline's total, percent
   - econ.margin_vs_cheapest_primary.cheapest_by_week, .cheapest_counts, .weeks_positive, .n_weeks
   - econ.margin_vs_lowest_median_primary.{tag,label,usd.median,usd.min,usd.max}: for reference, the paired margin
     to the one primary baseline with the lowest median total
2. guard: the guarded runs of every confirmation part (code/sim/out/sublet_v2/<part>/summary.json, guarded[], joined
   with runs[] for the run kind), counted by whether the safe expert S followed all-fallback (FB) at every slot
   (s_fb_all, ms5b_common.guard_extras: every entry of S's followed run-length list is FB).
   - guard.week.{runs,s_fb_all,aborted,by_part,by_tag}: the guarded week runs (kind 'week') of all parts (main,
     seeds, second on weeks 301-316; grid on alignments 1-4, development-exposed); check: s_fb_all in every one
   - guard.week_confirmation_weeks.{runs,s_fb_all}: those of parts main, seeds and second (weeks 301-316)
   - guard.week_main.{runs,s_fb_all}: part main only (16 weeks x 7 lender modes x 4 guarded tags)
   - guard.sublet_week.{runs,s_fb_all,aborted,by_part}: tag Sublet's week runs
   - guard.not_family.{runs,s_fb_all}: every guarded run but the families of part fam (week, e5, gap, q44, e3cell)
   - guard.all.{runs,s_fb_all,aborted}: every guarded run (checked against analysis.json H3.n_runs)
   - guard.projected_aborts_s_fb_all: runs with projection on that abort while S follows FB at every slot (Theorem
     11(b): none; check)
   - guard.rows: one row per (part, kind, tag) with runs, s_fb_all, aborted
3. allowance: B(T), the allowance at the last slot (guarded[].B_T: the last entry of the safe expert's B curve;
   online_lb.Wk_T = B_peak(T), the cap; online_lb.LB_T = LB'(T); B = min{B_peak, LB'}), over tag Sublet's week runs.
   - allowance.sublet_week.{runs,B_T,Wk_T,LB_T} with {min,max} each, B_T.min_floor and B_T.max_ceil (the range
     rounded outward to whole USD, for "at most" and a printed range), B_T_eq_Wk_T (runs whose B(T) is the cap),
     B_T_over_bl0a_max, excess_max (largest ALG - bl0a_usd - B_T over these runs, overflow accounting; check <= 0:
     with S on FB at every slot and no abort, the guard's envelope ALG(T) <= C_S(T) + B(T) with C_S(T) the
     all-fallback bill, the run's form of Theorem 11(a)'s bound, since B(T) = min{B_peak(T), LB'(T)} and
     LB'(T) <= OPT_min by Lemma 7(c)),
     by_part.<part>.{runs,B_T_min,B_T_max}
   - allowance.sublet_week_main: the same over part main's 112 runs
4. fam_f3: the insurance family of part fam (code/sim/out/sublet_v2/fam/summary.json; runs whose 'fam' field is F3,
   sources F3 and CF3, as sf_e7_decomp's e7v2_h3 groups them), per guarded tag: runs, aborts, abort_slots (distinct
   t_a, ascending), abort_slot_min, abort_slot_max, aborts_at_slot0, aborts_s_fb_all, abort_cases (the certificate's
   case of each aborting run: W(b) with S on FB after the abort, W(c) the conjectured case), by_src; for Sublet also
   inner_insured_runs (runs whose inner policy, critical-ratio renting, insured at least once: a9.insured >= 1).
   Check: every abort of Sublet on F3 is at slot 0.
5. alpha_N: m, K and the request bound N of the 16 week instances of part main, and
   alpha_N = 4 ceil(2 ln N) ln(m K + 2) + 1 (paper/sections/revocation.tex, Theorem 1(d); design/theory/
   c3_c4_c5_general.md §1: a request is a pair (client, slot) with the client active, N >= 2 an upper bound on their
   number known in advance). In the simulator a request is a unit-slot (pd_core: q_req and delta_req per unit-slot),
   m = the instance's sites, K = its contracts (pd_core.problem_from_view, d = m K + 1), and N is the bound the
   driver passes to Sublet's primal-dual as Theorem 1(d)'s a-priori N: drivers/run.py driver_inputs, N_bound =
   max(N_u T_slow, 3), N_u the client units (instance.units), T_slow the routing slots. N_u sizes each client by its
   peak demand over the week, so N_bound is a hindsight-reference statistic that the runs use as the a-priori bound
   (design/sim_spec_ms2.md M6; the runs record the information class 'online-I1 + a-priori N', checked on Sublet's
   guarded records of part main). Each instance is rebuilt from its versioned inputs
   (BUILD_INPUTS: the a1, a2, a4b, a11 and a12 outputs and configs/bench_e7f.json; no raw trace; about 1 s and
   150 MB per week), and its instance_hash is checked against part main's versioned job record of Sublet on that
   week. BUILD_INPUTS are recorded with their sha256 under meta.inputs; an audit hook on 'open' checks that the
   builder opens no other data file (the check fails on a file outside BUILD_INPUTS, a raw trace included).
   - alpha_N.{m,K,d}: sites, contracts, d = m K + 1 (the same in every week; check)
   - alpha_N.N_info_class: the information class that Sublet's week runs of part main report (the same in all)
   - alpha_N.N.{min,max}, alpha_N.rbar.{min,max} (ceil(2 ln N), rounding.rbar_theory), alpha_N.value.{min,max}
   - alpha_N.requests.{min,max}: |sigma|, the active unit-slots of the week; alpha_N.value_at_requests.{min,max}:
     the formula at N = |sigma|, the smallest valid a-priori bound (a lower reference)
   - alpha_N.by_week.<w>: m, K, n_clients, n_units, T_slow, requests, N, rbar, value, value_at_requests,
     instance_hash, rho, rho_by_llm
   - alpha_N.rho.{min,max} (C13(b)): per week the rho of Theorem 1(b), the largest
     rho_ljk = 1 + beta~_jlk / (g_j a_lk D_k / 60) over the usable revocable triples (calib.instance_rho per LLM,
     the maximum over the LLMs); by_week.<w>.rho_by_llm: per LLM [rho, site id, contract id] of its largest triple
   - alpha_N.planner_check: the first week's Sublet policy (A8P around A9, ms5b_common's tag Sublet) reset on the
     instance, and its safe expert's primal-dual planner's rbar, N_bound and d against by_week (null with
     --no-planner-check)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import sys
from pathlib import Path
from typing import Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[3]
SIM = REPO / "code" / "sim"
OUT = REPO / "code/sim/out/ms7/eval_extract.json"
CONF = "code/sim/out/sublet_v2"
PARTS = ("main", "seeds", "second", "e3", "fam", "grid")
WEEK_PARTS_CONF = ("main", "seeds", "second")          # weeks 301-316; grid runs on alignments 1-4
TABLE3 = "code/sim/out/figs/table3_v2.json"
FIG4V2 = "code/sim/out/figs/fig4v2.json"
ANALYSIS = f"{CONF}/analysis.json"
SUMMARY = {p: f"{CONF}/{p}/summary.json" for p in PARTS}
# the files the week instance builder reads (checked up front and recorded; it must open no other data file)
BUILD_INPUTS = ("code/analysis/out/a11_calibration.json", "code/analysis/out/a12_minute_io.npz",
                "code/analysis/out/a12_sim_inputs.json", "code/analysis/out/a1_slack_series.npz",
                "code/analysis/out/a2_slack_series.npz", "code/analysis/out/a4b_wildchat_weekly.json",
                "code/sim/configs/bench_e7f.json")
TRACE, SEED, REFERENCE, SUBLET = "L-tr", 0, "BL0a", "Sublet"
WEEK_MIN = 10080
REL_TOL = 1e-9
N_INFO_CLASS = "online-I1 + a-priori N"      # drivers/run.py N_bound, design/sim_spec_ms2.md M6


class MissingInput(Exception):
    pass


class CheckFailed(Exception):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def close(a: float, b: float, tol: float = REL_TOL) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def need(d, *keys, what: str):
    cur = d
    for k in keys:
        if not isinstance(cur, Mapping) or k not in cur:
            raise MissingInput(f"{what}: no key {'.'.join(map(str, keys))}")
        cur = cur[k]
    return cur


def summ(values: Mapping[str, float]) -> dict:
    v = [float(x) for x in values.values()]
    return {"median": statistics.median(v), "min": min(v), "max": max(v), "by_week": dict(values)}


class Reader:
    """The versioned inputs under `root`, each read once, with its sha256 recorded (relative path -> sha256)."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.sha: dict = {}
        self._json: dict = {}

    def path(self, rel: str) -> Path:
        p = self.root / rel
        if not p.is_file():
            raise MissingInput(f"missing input {rel} (under {self.root})")
        return p

    def json(self, rel: str):
        if rel not in self._json:
            p = self.path(rel)
            self.sha[rel] = sha256(p)
            self._json[rel] = json.loads(p.read_text(encoding="utf-8"))
        return self._json[rel]

    def record(self, rel: str, path: Optional[Path] = None) -> None:
        self.sha[rel] = sha256(self.path(rel) if path is None else path)


# ---------------------------------------------------------------- 1. economics
def _week_rows(summary: Mapping, what: str) -> dict:
    """{(tag, cell): row} of the week runs under L-tr at policy seed 0; every one must be 'ok'."""
    out = {}
    for r in need(summary, "runs", what=what):
        if r.get("kind") != "week" or r.get("mode") != TRACE or int(r.get("seed", -1)) != SEED:
            continue
        if r.get("status") != "ok":
            raise CheckFailed(f"{what}: run {r.get('job')} under {TRACE} is not ok ({r.get('status')})")
        key = (r["tag"], str(r["cell"]))
        if key in out:
            raise CheckFailed(f"{what}: two week rows for {key}")
        out[key] = r
    return out


def economics(rd: Reader) -> dict:
    t3 = need(rd.json(TABLE3), "data", what=TABLE3)
    rows = need(t3, "rows", what=TABLE3)
    ana = rd.json(ANALYSIS)
    main = rd.json(SUMMARY["main"])
    fig4 = need(rd.json(FIG4V2), "data", "a", what=FIG4V2)
    primary = list(need(ana, "H2", "set", what=ANALYSIS))
    if sorted(primary) != sorted(need(t3, "caption_source", "h1_set", what=TABLE3)):
        raise CheckFailed(f"{ANALYSIS} H2.set {primary} differs from {TABLE3} caption_source.h1_set")
    weeks = [str(w) for w in need(ana, "H1", "weeks", what=ANALYSIS)]
    wk = _week_rows(main, SUMMARY["main"])

    def cell(tag: str, acc: str) -> dict:
        c = need(rows, tag, "cells", "usd", acc, "by_cell", what=f"{TABLE3} row {tag}")
        if sorted(c, key=int) != sorted(weeks, key=int):
            raise CheckFailed(f"{TABLE3} row {tag}: weeks {sorted(c)} differ from H1's {weeks}")
        return {w: float(c[w]) for w in weeks}

    def ovf_summary(tag: str) -> dict:
        out = {}
        for w in weeks:
            r = wk.get((tag, w))
            if r is None or r.get("r0") is None:
                raise MissingInput(f"{SUMMARY['main']}: no {tag} week run with r0 under {TRACE} in week {w}")
            out[w] = float(r["r0"]) * float(r["bl0a_usd"])
        return out

    # own capacity: total - overflow, the same in every row and equal to Fig. 4 v2's
    own = None
    for tag in rows:
        o, t = cell(tag, "overflow"), cell(tag, "total")
        d = {w: t[w] - o[w] for w in weeks}
        if own is None:
            own = d
        elif any(not close(d[w], own[w]) for w in weeks):
            raise CheckFailed(f"{TABLE3}: own capacity (total - overflow) of row {tag} differs from the first row's")
        if tag != REFERENCE:
            s = ovf_summary(tag)
            bad = [w for w in weeks if not close(s[w], o[w], 1e-12)]
            if bad:
                raise CheckFailed(f"{TABLE3} row {tag}: overflow differs from r0 x bl0a_usd of main in weeks {bad}")
    f4 = need(fig4, "own_capacity_usd", "by_week", what=FIG4V2)
    if any(not close(own[w], float(f4[w])) for w in weeks):
        raise CheckFailed(f"{TABLE3} own capacity differs from {FIG4V2} own_capacity_usd")
    if not close(statistics.median(cell(SUBLET, "overflow").values()),
                 float(need(rows, SUBLET, "cells", "usd", "overflow", "median", what=TABLE3))):
        raise CheckFailed(f"{TABLE3}: Sublet's overflow median is not statistics.median of its by_cell")

    total = {}
    for tag in set(primary) | {SUBLET, REFERENCE}:
        if tag in rows:
            total[tag] = cell(tag, "total")
        else:
            s = ovf_summary(tag)
            total[tag] = {w: s[w] + own[w] for w in weeks}
    sub, ref = total[SUBLET], total[REFERENCE]
    sav_usd = {w: ref[w] - sub[w] for w in weeks}
    sav_pct = {w: 100.0 * (1.0 - sub[w] / ref[w]) for w in weeks}

    h1 = need(ana, "H1", "margins", what=ANALYSIS)
    cheapest, margin, margin_pct = {}, {}, {}
    for w in weeks:
        best = min(primary, key=lambda t: total[t][w])
        cheapest[w], margin[w] = best, total[best][w] - sub[w]
        margin_pct[w] = 100.0 * margin[w] / total[best][w]
        hw = need(h1, w, what=f"{ANALYSIS} H1.margins")
        if hw.get("best") != best:
            raise CheckFailed(f"week {w}: cheapest primary baseline {best}, H1's {hw.get('best')}")
        bl0a = float(wk[(SUBLET, w)]["bl0a_usd"])
        if not close(margin[w], float(hw["delta"]) * bl0a, 1e-8):
            raise CheckFailed(f"week {w}: margin {margin[w]} USD differs from H1's delta x bl0a_usd")
    med = {t: statistics.median(total[t].values()) for t in primary}
    low = min(primary, key=lambda t: med[t])
    low_m = {w: total[low][w] - sub[w] for w in weeks}

    def label(t: str) -> Optional[str]:
        return (rows.get(t) or {}).get("label") or need(t3, "caption_source", "labels", what=TABLE3).get(t)

    counts = {t: sum(1 for w in weeks if cheapest[w] == t) for t in primary}
    return {
        "weeks": weeks, "n_weeks": len(weeks), "mode": TRACE, "policy_seed": SEED,
        "accounting": "total = overflow + own capacity of the instance (ms4_common.accountings); overflow = r0 x "
                      "bl0a_usd; a USD difference between policies is the same in both",
        "primary_set": primary, "primary_labels": {t: label(t) for t in primary},
        "own_capacity_usd": summ(own),
        "bl0a_total_usd": {"median": statistics.median(ref.values()), "by_week": ref},
        "sublet_total_usd": {"median": statistics.median(sub.values()), "by_week": sub},
        "saving_vs_fallback": {
            "usd": summ(sav_usd), "pct_total": summ(sav_pct),
            "pct_overflow_median": float(need(rows, SUBLET, "cells", "saving_pct", "value", what=TABLE3))},
        "margin_vs_cheapest_primary": {
            "definition": "per week, min over the primary baselines of their total minus Sublet's total",
            "usd": summ(margin), "pct_total": summ(margin_pct), "cheapest_by_week": cheapest,
            "cheapest_counts": {t: n for t, n in counts.items() if n}, "weeks_positive":
                sum(1 for w in weeks if margin[w] > 0), "n_weeks": len(weeks)},
        "margin_vs_lowest_median_primary": {
            "tag": low, "label": label(low), "median_total_usd": med[low],
            "usd": {k: v for k, v in summ(low_m).items() if k != "by_week"}},
    }


# ---------------------------------------------------------------- 2./3. guarded records and B(T)
def _guarded(rd: Reader) -> list:
    """[(part, kind, record, run row)] of every guarded record of every part."""
    out = []
    for p in PARTS:
        s = rd.json(SUMMARY[p])
        runs = {}
        for r in need(s, "runs", what=SUMMARY[p]):
            runs[(r["job"], r["tag"], r.get("mode"), int(r.get("seed", 0)), str(r["cell"]))] = r
        for x in need(s, "guarded", what=SUMMARY[p]):
            r = runs.get((x["job"], x["tag"], x.get("mode"), int(x.get("seed", 0)), str(x["cell"])))
            if r is None:
                raise CheckFailed(f"{SUMMARY[p]}: guarded record {x['job']} {x['tag']} has no run row")
            if r.get("status") != "ok":
                raise CheckFailed(f"{SUMMARY[p]}: run {r['job']} {r['tag']} {r.get('mode')} is not ok")
            out.append((p, r["kind"], x, r))
    return out


def _count(xs: Sequence) -> dict:
    return {"runs": len(xs), "s_fb_all": sum(1 for _p, _k, x, _r in xs if x.get("s_fb_all") is True),
            "aborted": sum(1 for _p, _k, x, _r in xs if x.get("aborted"))}


def guard(rd: Reader, g: list) -> dict:
    week = [e for e in g if e[1] == "week"]
    by_part = {p: _count([e for e in week if e[0] == p]) for p in PARTS if any(e[0] == p for e in week)}
    tags = sorted({e[2]["tag"] for e in week})
    rows = {}
    for p, k, x, _r in g:
        c = rows.setdefault((p, k, x["tag"]), {"part": p, "kind": k, "tag": x["tag"], "runs": 0, "s_fb_all": 0,
                                               "aborted": 0})
        c["runs"] += 1
        c["s_fb_all"] += x.get("s_fb_all") is True
        c["aborted"] += bool(x.get("aborted"))
    proj_ab = [f"{p}:{x['job']}:{x['tag']}:{x.get('mode')}:{x.get('seed')}" for p, _k, x, _r in g
               if x.get("project") is True and x.get("aborted") and x.get("s_fb_all") is True]
    sub = [e for e in week if e[2]["tag"] == SUBLET]
    out = {
        "definition": "s_fb_all: the safe expert S followed all-fallback (FB) at every slot (ms5b_common.guard_extras)",
        "week": {**_count(week), "parts": list(by_part), "by_part": by_part,
                 "by_tag": {t: _count([e for e in week if e[2]["tag"] == t]) for t in tags}},
        "week_confirmation_weeks": {**_count([e for e in week if e[0] in WEEK_PARTS_CONF]),
                                    "parts": list(WEEK_PARTS_CONF)},
        "week_main": _count([e for e in week if e[0] == "main"]),
        "sublet_week": {**_count(sub), "by_part": {p: _count([e for e in sub if e[0] == p])
                                                   for p in PARTS if any(e[0] == p for e in sub)}},
        "not_family": _count([e for e in g if e[0] != "fam"]),
        "all": _count(g),
        "projected_aborts_s_fb_all": len(proj_ab),
        "rows": [rows[k] for k in sorted(rows, key=lambda k: (PARTS.index(k[0]), k[1], k[2]))],
    }
    n_h3 = int(need(rd.json(ANALYSIS), "H3", "n_runs", what=ANALYSIS))
    if out["all"]["runs"] != n_h3:
        raise CheckFailed(f"{out['all']['runs']} guarded runs, {ANALYSIS} H3.n_runs = {n_h3}")
    if out["week"]["s_fb_all"] != out["week"]["runs"]:
        bad = [f"{p}:{x['job']}:{x.get('mode')}" for p, _k, x, _r in week if x.get("s_fb_all") is not True]
        raise CheckFailed(f"guarded week runs with S not on FB at every slot: {bad[:5]}")
    if proj_ab:
        raise CheckFailed(f"runs with projection that abort while S follows FB: {proj_ab[:5]}")
    return out


def _allowance(xs: Sequence) -> dict:
    if not xs:
        raise MissingInput("no Sublet week run with a guarded record")
    bt = [float(x["B_T"]) for _p, _k, x, _r in xs]
    wk = [float(need(x, "online_lb", "Wk_T", what=f"guarded record {x['job']}")) for _p, _k, x, _r in xs]
    lb = [float(need(x, "online_lb", "LB_T", what=f"guarded record {x['job']}")) for _p, _k, x, _r in xs]
    ex = [float(r["ALG"]) - float(r["bl0a_usd"]) - float(x["B_T"]) for _p, _k, x, r in xs]
    return {"runs": len(xs), "B_T": {"min": min(bt), "max": max(bt), "min_floor": math.floor(min(bt)),
                                     "max_ceil": math.ceil(max(bt))},
            "Wk_T": {"min": min(wk), "max": max(wk)}, "LB_T": {"min": min(lb), "max": max(lb)},
            "B_T_eq_Wk_T": sum(1 for a, b in zip(bt, wk) if a == b),
            "B_T_over_bl0a_max": max(float(x["B_T"]) / float(r["bl0a_usd"]) for _p, _k, x, r in xs),
            "excess_max": max(ex)}


def allowance(g: list) -> dict:
    sub = [e for e in g if e[1] == "week" and e[2]["tag"] == SUBLET]
    out = {"definition": "B_T: B(T), the last entry of the safe expert's B curve; Wk_T: B_peak(T), the cap; LB_T: "
                         "LB'(T); B = min{B_peak, LB'}; excess: ALG - bl0a_usd - B_T, overflow accounting, USD",
           "sublet_week": {**_allowance(sub), "by_part": {}},
           "sublet_week_main": _allowance([e for e in sub if e[0] == "main"])}
    for p in PARTS:
        xs = [e for e in sub if e[0] == p]
        if xs:
            a = _allowance(xs)
            out["sublet_week"]["by_part"][p] = {"runs": a["runs"], "B_T_min": a["B_T"]["min"],
                                                "B_T_max": a["B_T"]["max"]}
    if out["sublet_week"]["excess_max"] > 1e-6 * max(1.0, out["sublet_week"]["B_T"]["max"]):
        raise CheckFailed(f"a Sublet week run costs more than bl0a_usd + B(T): {out['sublet_week']['excess_max']}")
    return out


# ---------------------------------------------------------------- 4. the insurance family F3
def fam_f3(rd: Reader, g: list) -> dict:
    f3 = [e for e in g if e[0] == "fam" and e[3].get("fam") == "F3"]
    if not f3:
        raise MissingInput(f"{SUMMARY['fam']}: no guarded run of family F3")

    def one(xs: Sequence) -> dict:
        ab = [x for _p, _k, x, _r in xs if x.get("aborted")]
        slots = sorted({int(x["t_a"]) for x in ab})
        return {"runs": len(xs), "aborts": len(ab), "abort_slots": slots,
                "abort_slot_min": slots[0] if slots else None, "abort_slot_max": slots[-1] if slots else None,
                "aborts_at_slot0": sum(1 for x in ab if int(x["t_a"]) == 0),
                "aborts_s_fb_all": sum(1 for x in ab if x.get("s_fb_all") is True),
                "abort_cases": {c: sum(1 for x in ab if x.get("case") == c) for c in sorted({str(x.get("case"))
                                                                                            for x in ab})}}

    by_tag = {}
    for t in sorted({e[2]["tag"] for e in f3}):
        xs = [e for e in f3 if e[2]["tag"] == t]
        by_tag[t] = {**one(xs), "by_src": {s: one([e for e in xs if e[3].get("src") == s])
                                           for s in sorted({e[3].get("src") for e in xs})}}
    sub = [e for e in f3 if e[2]["tag"] == SUBLET]
    if SUBLET not in by_tag:
        raise MissingInput(f"{SUMMARY['fam']}: no Sublet run on F3")
    by_tag[SUBLET]["inner_insured_runs"] = sum(1 for e in sub if int((e[3].get("a9") or {}).get("insured") or 0) >= 1)
    s = by_tag[SUBLET]
    if s["aborts"] and s["abort_slots"] != [0]:
        raise CheckFailed(f"Sublet's F3 aborts at slots {s['abort_slots']}, not only at slot 0")
    return {"definition": "runs of part fam whose 'fam' field is F3 (sources F3 and CF3); t_a: the abort slot",
            "modes": sorted({e[2].get("mode") for e in f3}), "by_tag": by_tag}


# ---------------------------------------------------------------- 5. alpha_N of the week instances
def alpha_n_value(N: int, m: int, K: int) -> float:
    return 4.0 * math.ceil(2.0 * math.log(N)) * math.log(m * K + 2) + 1.0


class _Opens:
    """Files opened while active (sys.addaudithook; a hook cannot be removed, so it is installed once)."""
    active = False
    paths: set = set()
    installed = False

    @classmethod
    def install(cls) -> None:
        if not cls.installed:
            def hook(event, args):
                if cls.active and event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
                    cls.paths.add(os.fsdecode(args[0]))
            sys.addaudithook(hook)
            cls.installed = True


def _opened_inputs(root: Path) -> list:
    """The data files the builder opened under `root` or /mnt/data (no source file), as paths relative to root (raw
    trace files absolute)."""
    out = set()
    for p in _Opens.paths:
        q = Path(p)
        if not q.is_absolute():
            q = Path.cwd() / q
        try:
            q = q.resolve()
        except OSError:
            continue
        if not q.is_file() or q.suffix in (".py", ".pyc", ".pth", ".so"):
            continue
        if q.is_relative_to(root.resolve()):
            out.add(str(q.relative_to(root.resolve())))
        elif str(q).startswith("/mnt/data/"):
            out.add(str(q))
    return sorted(out)


def week_instances(rd: Reader, weeks: Sequence[str], planner_check: bool = True) -> dict:
    for rel in BUILD_INPUTS:          # the builder reads them from the repository (sublet.paths), whatever --root
        if not (REPO / rel).is_file():
            raise MissingInput(f"missing input {rel} of the week instances (under {REPO})")
    if str(SIM) not in sys.path:
        sys.path.insert(0, str(SIM))
    from sublet import paths as spaths
    from sublet.algos.rounding import rbar_theory
    from sublet.drivers import run as drun
    from sublet.experiments import ms3_common as mc
    from sublet.experiments import ms5b_common as m5
    from sublet.calib import instance_rho
    from sublet.instance import units
    if spaths.REPO.resolve() != REPO.resolve():      # the open check below only sees files under REPO
        raise CheckFailed(f"package sublet is imported from {spaths.REPO}, not from {REPO}")
    _Opens.install()
    _Opens.paths.clear()
    by_week, insts = {}, {}
    for w in weeks:
        c = int(w)
        job = f"{CONF}/main/jobs/e7h__main__k__week__tag__{SUBLET}__c__{w}.json"
        rec = rd.json(job)
        want = need(rec, "result", "instance_hash", what=job)
        if int(need(rec, "params", "horizon_min", what=job)) != WEEK_MIN:
            raise CheckFailed(f"{job}: horizon {rec['params']['horizon_min']} min, not one week")
        _Opens.active = True
        try:
            spec0 = m5.week_spec("BL0a", {}, mode=TRACE, c=c, horizon_min=WEEK_MIN, seeds=[SEED], name="ms7_extract")
            inst, _model, _ecfg = drun.build(spec0, c)
        finally:
            _Opens.active = False
        h = mc.instance_hash(inst)
        if h != want:
            raise CheckFailed(f"week {w}: rebuilt instance_hash {h} differs from {job}'s {want}")
        params = m5.tag_params(SUBLET, inst)
        pid = m5.tag(SUBLET).id
        vals, _meta = drun.driver_inputs(pid, dict(params), inst)
        U = units(inst)
        N, m, K = int(vals["N_bound"]), int(inst.m), int(inst.K)
        if N != max(len(U.client) * int(inst.grid.T_slow), 3):
            raise CheckFailed(f"week {w}: driver N_bound {N} is not max(N_u T_slow, 3)")
        req = int(U.active.sum())
        rbar = int(rbar_theory(N))
        if rbar != math.ceil(2.0 * math.log(N)):
            raise CheckFailed(f"week {w}: rbar_theory({N}) = {rbar}, not ceil(2 ln N)")
        by_week[w] = {"m": m, "K": K, "n_clients": int(inst.n), "n_units": int(len(U.client)),
                      "T_slow": int(inst.grid.T_slow), "requests": req, "N": N, "rbar": rbar,
                      "value": alpha_n_value(N, m, K), "value_at_requests": alpha_n_value(max(req, 2), m, K),
                      "instance_hash": h}
        rl = instance_rho(inst)
        if any(v is None for v in rl.values()):
            raise CheckFailed(f"week {w}: an LLM without a usable revocable triple: {rl}")
        by_week[w]["rho"] = max(v[0] for v in rl.values())
        by_week[w]["rho_by_llm"] = {j: list(v) for j, v in sorted(rl.items())}
        insts[w] = (inst, pid, params, c)
    ms, Ks = {b["m"] for b in by_week.values()}, {b["K"] for b in by_week.values()}
    if len(ms) != 1 or len(Ks) != 1:
        raise CheckFailed(f"the week instances have m in {sorted(ms)} and K in {sorted(Ks)}")
    m, K = ms.pop(), Ks.pop()
    ic = {x.get("info_class_reported") for x in need(rd.json(SUMMARY["main"]), "guarded", what=SUMMARY["main"])
          if x.get("tag") == SUBLET}
    if ic != {N_INFO_CLASS}:
        raise CheckFailed(f"{SUMMARY['main']}: Sublet's guarded records report the classes {sorted(map(str, ic))}, "
                          f"not only {N_INFO_CLASS!r}")

    check = None
    if planner_check:
        from sublet.config import rng_streams
        from sublet.instance import public_view
        w0 = weeks[0]
        inst, pid, params, c = insts[w0]
        spec = m5.week_spec(pid, params, mode=TRACE, c=c, horizon_min=WEEK_MIN, seeds=[SEED], name="ms7_extract")
        pol = drun.make_policy(spec, inst)
        pol.reset(public_view(inst, drun._lender_model(spec, inst).information), rng_streams(SEED)["policy"])
        pl = pol.sx.planner
        check = {"week": w0, "policy": type(pol).__name__, "rbar": int(pl.rbar), "N_bound": int(pl.N_bound),
                 "d": int(pl.prob.d), "m": int(pl.prob.m), "K": int(pl.prob.K)}
        check["matches"] = (check["rbar"] == by_week[w0]["rbar"] and check["N_bound"] == by_week[w0]["N"]
                            and check["d"] == m * K + 1 and check["m"] == m and check["K"] == K)
        if not check["matches"]:
            raise CheckFailed(f"Sublet's planner on week {w0}: {check} differs from the instance's values")

    def rng(k: str) -> dict:
        v = [b[k] for b in by_week.values()]
        return {"min": min(v), "max": max(v)}

    # the loaders cache what they read (lru_cache), so a process that built an instance before opens less: the check
    # is that the builder opened nothing outside BUILD_INPUTS (no raw trace either); BUILD_INPUTS are recorded
    extra = [rel for rel in _opened_inputs(REPO) if rel not in BUILD_INPUTS]
    if extra:
        raise CheckFailed(f"the instance builder opened {extra}, which BUILD_INPUTS does not list")
    for rel in BUILD_INPUTS:
        rd.record(rel, REPO / rel)
    return {"formula": "4 ceil(2 ln N) ln(m K + 2) + 1 (Theorem 1(d))",
            "N_definition": "the request bound that Sublet's primal-dual uses as the a-priori N: drivers/run.py "
                            "driver_inputs, N_bound = max(N_u T_slow, 3), N_u client units (sized by each client's "
                            "peak demand over the week: a hindsight-reference statistic, design/sim_spec_ms2.md M6), "
                            "T_slow routing slots; a request is a unit-slot",
            "N_info_class": N_INFO_CLASS,
            "weeks": list(weeks), "m": m, "K": K, "d": m * K + 1,
            "N": rng("N"), "rbar": rng("rbar"), "value": rng("value"), "requests": rng("requests"),
            "value_at_requests": rng("value_at_requests"),
            "rho_definition": "Theorem 1(b)'s rho: the largest rho_ljk = 1 + beta~_jlk / (g_j a_lk D_k / 60) over the "
                              "usable revocable triples (sublet.calib.instance_rho, the maximum over the LLMs)",
            "rho": rng("rho"), "by_week": by_week, "planner_check": check}


# ---------------------------------------------------------------- main
def build(root: Path = REPO, planner_check: bool = True) -> dict:
    rd = Reader(root)
    econ = economics(rd)
    g = _guarded(rd)
    out = {"econ": econ, "guard": guard(rd, g), "allowance": allowance(g), "fam_f3": fam_f3(rd, g)}
    out["alpha_N"] = week_instances(rd, econ["weeks"], planner_check=planner_check)
    out = {"meta": {"script": "code/sim/figs/ms7_eval_extract.py",
                    "spec": "design/ms7/w_spec.md (unit W-X; §2.7, §2.8, §3 Values)",
                    "statistic": "statistics.median over the weeks of per-week (paired) values",
                    "inputs": dict(sorted(rd.sha.items()))}, **out}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--root", type=Path, default=REPO, help="tree the inputs are read from (default: the repository)")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--no-planner-check", action="store_true")
    a = ap.parse_args(argv)
    try:
        out = build(a.root, planner_check=not a.no_planner_check)
    except MissingInput as err:
        print(f"ms7_eval_extract: {err}", file=sys.stderr)
        return 2
    except CheckFailed as err:
        print(f"ms7_eval_extract: check failed: {err}", file=sys.stderr)
        return 1
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    e, gd, al, an = out["econ"], out["guard"], out["allowance"], out["alpha_N"]
    print(json.dumps({"econ.total_saving_pct": e["saving_vs_fallback"]["pct_total"]["median"],
                      "econ.usd_saving": e["saving_vs_fallback"]["usd"]["median"],
                      "econ.usd_margin": e["margin_vs_cheapest_primary"]["usd"]["median"],
                      "guard.week": [gd["week"]["s_fb_all"], gd["week"]["runs"]],
                      "allowance.B_T": [al["sublet_week"]["B_T"]["min"], al["sublet_week"]["B_T"]["max"]],
                      "fam_f3.Sublet": [out["fam_f3"]["by_tag"][SUBLET]["aborts"],
                                        out["fam_f3"]["by_tag"][SUBLET]["abort_slots"]],
                      "alpha_N": [an["m"], an["K"], an["N"], an["value"]]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
