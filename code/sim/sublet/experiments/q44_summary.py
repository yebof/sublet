"""Summary of the Q44 study (design/q44_practical_sublet.md §5.5, §5.6): D1-D6, checks V1-V7, the
certificate of §3.10 on every guarded run, tables and the study figures.

  python -m sublet.experiments.q44_summary [--out DIR] [--no-fig]

Reads what q44_study.py wrote under code/sim/out/q44_study/ (or SUBLET_Q44_DIR, or --out): the run files
(their 'q44' objects), the cell records, the LB files and the job records. Writes summary.json,
tables.md and fig/ (three views, labeled as study figures, not paper figures). With runs of
T0g runs that have a T0 partner, summary.json also has 'T0g' (t0g_pairs: each T0g run paired with the T0 run of
the same base tag, cell, mode and seeds: the historical block T2_t0g against Q1, Q2 and Q6 as run at commit
d2a538d, or, since T0g became A8's default on 2026-10-17, a default tag against its T0 variant, q44_study.T0_PARTNERS;
D3 under T0g for T2_t0g) and tables.md a section for it.

Definitions (§5.5): per cell and mode the policy seeds are averaged; r0 = cost / BL0a and r_best = cost /
min(BL1, BL2, BL5) of the same cell-mode; r_LB = cost / LB and the headroom h = LB / BL0a on the slow grid
only (violations absorbed, LB = the largest valid bound of the schedule: the LP, or BL8's MILP dual bound);
W0 = the maximum over the stress modes run on the instance of the median r0. Medians carry 95% percentile-
bootstrap intervals over cells (metrics.aggregate, 2000 resamples, seed 0); comparisons between two policies
are medians of paired ratios on the same cell. Decisions use the held-out cells of the main blocks Q1 and
Q2 on the 1-min grid; tuning cells are reported apart. A cell identical to an earlier one of the same block,
grid and mode (equal instance hash and BL0a's realized schedule hash) is dropped before medians, and the
drop is reported (§5.2). Criteria T (D1 <= 1 + x on at least three of I1-I4) and S (W0 <= 1 + y on every
instance) use the proposed x = 10%, y = 5%; 'framing_indicated' applies the rule of §5.6 mechanically, as an
input, not a decision.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

import numpy as np

from ..paths import C3, SIM_OUT
from .q44_study import BASE_TAGS, GUARD_DEFAULTS, GUARD_DEFAULTS_T0, MODES, NOTE, POLICIES, T0G_PAIRS, out_root

MAIN_BLOCKS = ("Q1", "Q2")
FAMILIES = ("I1", "I2", "I3", "I4")
X_T, Y_S = 0.10, 0.05                 # proposed thresholds of criteria T and S (§5.6)
D1_TAGS = ("PS-G", "PS", "A6", "BL1", "BL2", "BL5", "BL1-G", "BL5-G")
RENTING = ("BL1", "BL2", "BL5")
GUARDED_BASELINES = ("BL1-G", "BL5-G")
GUARD_PAIRS = (("PS-G", "PS"), ("PS-G1", "PS"), ("PS-GR", "PS"), ("BL1-G", "BL1"), ("BL5-G", "BL5"))
CONTROL_PAIRS = (("BL1-G", "PS-G"), ("BL5-G", "PS-G"))
FAMILY_FIG_TAGS = ("PS", "PS-G", "BL1", "BL5", "BL1-G", "BL5-G", "A2-th", "RR_RENEW")
LINE_TAGS = ("PS-G", "PS", "A6", "BL1", "BL2", "BL5", "BL1-G", "BL5-G")
PD_COST_DIAG = SIM_OUT / "ms2_checks" / "pd_cost_diag.json"
C4_LOWER = C3 / "out" / "c4_lower.json"
REL = 1e-9
# reference categorical palette (dataviz skill, references/palette.md, light mode), in fixed order
PALETTE = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")


def _agg(values) -> dict:
    from ..metrics import aggregate
    v = [float(x) for x in values if x is not None and np.isfinite(x)]
    return aggregate(v, seed=0, B=2000)


def _med(values) -> Optional[float]:
    v = [float(x) for x in values if x is not None and np.isfinite(x)]
    return float(np.median(v)) if v else None


# ---------------------------------------------------------------- loading
_SKIP = re.compile(r"(^cell_.*|.*_error\.json$|.*_b\d+\.json$|.*\.tmp$)")


def load_runs(out: Path) -> tuple[list[dict], list[dict]]:
    """(runs, errors): one row per run file with a 'q44' object (BL2: the _sum file), and the error records."""
    rows, errors = [], []
    base = out / "runs"
    if not base.is_dir():
        return rows, errors
    for p in sorted(base.rglob("*.json")):
        if p.name.endswith("_error.json"):
            try:
                errors.append({**json.loads(p.read_text()), "file": str(p.relative_to(out))})
            except (OSError, json.JSONDecodeError):
                errors.append({"file": str(p.relative_to(out)), "error": "unreadable"})
            continue
        if _SKIP.match(p.name):
            continue
        try:
            js = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            errors.append({"file": str(p.relative_to(out)), "error": "unreadable run file"})
            continue
        q = js.get("q44")
        if not q:
            continue
        meta = js.get("meta") or {}
        comp = js.get("components") or {}
        seeds = q.get("seeds") or meta.get("seeds") or {}
        cert = q.get("certificate")
        if isinstance(cert, dict):
            cert = {k: v for k, v in cert.items() if k not in ("ALG_per_slot", "followed", "mode")}
        inv = js.get("invariant_failures")
        rows.append({"file": str(p.relative_to(out)), "block": q["block"], "tier": q.get("tier"),
                     "instance": q["instance"], "family": q.get("family"), "cell": q.get("cell"),
                     "tuning": bool(q.get("tuning")), "grid": q["grid"], "mode": q["mode"], "tag": q["tag"],
                     "policy_id": q.get("policy_id"), "c": seeds.get("config"), "l": seeds.get("lender"),
                     "p": seeds.get("policy"), "total": float(comp.get("total", q["components"]["total"])),
                     "components": q.get("components"), "intensity": q.get("intensity") or {},
                     "p1": q.get("plan_class_p1"), "invariant_failures": len(inv) if isinstance(inv, list)
                     else int(q.get("invariant_failures") or 0),
                     "gpu_only": int(q.get("gpu_only_lease_slots") or 0), "certificate": cert,
                     "instance_hash": q.get("instance_hash"), "schedule_hash": q.get("schedule_hash"),
                     "wall_s": q.get("wall_s"), "engine_wall_s": q.get("engine_wall_s"), "opt": q.get("opt"),
                     "ratio_opt": q.get("ratio_opt"), "rho": q.get("rho"), "m": q.get("m"), "rho1": q.get("rho1"),
                     "values": q.get("values"), "params": meta.get("params"), "leases": q.get("leases"),
                     "px": q.get("px"), "fallback_share": q.get("fallback_share"),
                     "violations": (q.get("mode_def") or {}).get("lender_model", {}).get("violations", "absorb")})
    return rows, errors


def load_cells(out: Path) -> list[dict]:
    out_l = []
    for p in sorted((out / "runs").rglob("cell_c*.json")) if (out / "runs").is_dir() else []:
        try:
            js = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        parts = p.relative_to(out / "runs").parts      # block, instance, grid, mode, file
        js.update(block=parts[0], instance=parts[1], grid=parts[2], mode=parts[3],
                  cell=int(re.match(r"cell_c(\d+)\.json", parts[4]).group(1)))
        out_l.append(js)
    return out_l


def load_lbs(out: Path) -> tuple[dict, dict]:
    """(per-schedule LBs keyed (instance, run grid, mode, cell, lender seed) -> list of records, per-run LBs
    keyed (instance, run grid, mode, cell, lender seed, tag, policy seed) -> record)."""
    sched, per_run = defaultdict(list), {}
    for p in sorted((out / "lb").rglob("*.json")) if (out / "lb").is_dir() else []:
        try:
            js = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        key = (js.get("instance"), js.get("run_grid"), js.get("mode"), js.get("cell"), js.get("lender_seed"))
        if js.get("per_run"):
            per_run[key + (js.get("tag"), js.get("policy_seed"))] = js
        else:
            sched[key].append({**js, "file": str(p.relative_to(out))})
    return sched, per_run


def _lb_value(recs) -> Optional[float]:
    vals = [r["lb"] for r in recs if r.get("lb") is not None and r.get("valid_for_runs", True)
            and (r.get("exact") or r.get("status") in (0, 1, None))]
    return max(vals) if vals else None


# ---------------------------------------------------------------- cell means and duplicates
def cell_key(r: dict) -> tuple:
    return (r["block"], r["family"], r["instance"], r["cell"], r["grid"], r["mode"])


def cell_means(rows: list[dict]) -> dict:
    """{cell key: {tag: mean total over the cell-mode's runs}} (policy seeds, and paired lender seeds)."""
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        acc[cell_key(r)][r["tag"]].append(r["total"])
    return {k: {t: float(np.mean(v)) for t, v in d.items()} for k, d in acc.items()}


def duplicates(cells: list[dict], blocks_order: dict) -> dict:
    """{cell key: the key of the earlier identical cell}: equal instance hash and BL0a's schedule hash within
    one block, family, grid and mode (§5.2, duplicate cells)."""
    groups = defaultdict(list)
    for c in cells:
        groups[(c["block"], c["grid"], c["mode"])].append(c)
    out = {}
    for (b, g, md), cs in groups.items():
        order = blocks_order.get(b, {})
        cs = sorted(cs, key=lambda c: (order.get(c["instance"], 999), c["cell"]))
        seen = {}
        for c in cs:
            ident = (c.get("instance_hash"), c.get("schedule_hash"))
            fam = c.get("family") or c["instance"].split("-")[0]
            key = (b, fam, c["instance"], c["cell"], g, md)
            if None in ident:
                continue
            if (fam,) + ident in seen:
                out[key] = seen[(fam,) + ident]
            else:
                seen[(fam,) + ident] = key
    return out


def _family_of_instance(cells: list[dict], rows: list[dict]) -> dict:
    fam = {}
    for r in rows:
        fam[(r["block"], r["instance"])] = r["family"]
    for c in cells:
        c["family"] = fam.get((c["block"], c["instance"]), c["instance"].split("-")[0])
    return fam


def _block_order(out: Path) -> dict:
    """{block: {instance: index}} from manifest.json's block files (else empty: alphabetical order)."""
    m = out / "manifest.json"
    res = {}
    if m.is_file():
        try:
            for b in json.loads(m.read_text()).get("blocks", []):
                bj = json.loads(Path(b["file"]).read_text())
                res[b["block"]] = {i["id"]: n for n, i in enumerate(bj.get("instances") or [])}
        except (OSError, json.JSONDecodeError, KeyError):
            pass
    return res


# ---------------------------------------------------------------- metrics per cell
def _r_best(cm: dict, tag: str, ref: Optional[dict] = None) -> Optional[float]:
    base = [(cm.get(b) if cm.get(b) is not None else (ref or {}).get(b)) for b in RENTING]
    if tag not in cm or any(v is None for v in base) or min(base) <= 0:
        return None
    return cm[tag] / min(base)


def _r0(cm: dict, tag: str, ref: Optional[dict] = None) -> Optional[float]:
    b0 = cm.get("BL0a", (ref or {}).get("BL0a"))
    if tag not in cm or b0 is None or b0 <= 0:
        return None
    return cm[tag] / b0


class Study:
    """The loaded study and its derived per-cell tables."""

    def __init__(self, out: Path):
        self.out = out
        self.rows, self.errors = load_runs(out)
        self.cells = load_cells(out)
        _family_of_instance(self.cells, self.rows)
        self.lb_sched, self.lb_run = load_lbs(out)
        self.cm = cell_means(self.rows)
        self.dups = duplicates(self.cells, _block_order(out))
        self.tags = sorted({r["tag"] for r in self.rows}, key=lambda t: list(POLICIES).index(t) if t in POLICIES else 99)
        self.tuning = {cell_key(r): r["tuning"] for r in self.rows}

    def keys(self, blocks, family=None, grid=None, mode=None, held_out=True, instances=None):
        out = []
        tuning = self.tuning
        for k in self.cm:
            b, fam, inst, c, g, md = k
            if b not in blocks or (family and fam != family) or (grid and g != grid) or (mode and md != mode):
                continue
            if instances is not None and inst not in instances:
                continue
            if k in self.dups:
                continue
            if held_out and tuning.get(k):
                continue
            out.append(k)
        return sorted(out, key=lambda k: (k[2], k[3]))

    def ref_cm(self, k, ref_block: Optional[str]) -> Optional[dict]:
        if not ref_block:
            return None
        return self.cm.get((ref_block,) + k[1:])


# ---------------------------------------------------------------- D1-D6
def d1(st: Study) -> dict:
    """D1: per instance, the median over held-out cells of r_best under L-tr (main blocks, 1-min grid)."""
    out = {}
    for fam in FAMILIES:
        ks = st.keys(MAIN_BLOCKS, fam, "1min", "L-tr")
        row = {}
        for tag in st.tags:
            row[tag] = {**_agg([_r_best(st.cm[k], tag) for k in ks]), "d1_tag": tag in D1_TAGS}
        out[fam] = {"cells": [list(k[2:4]) for k in ks], "r_best": row}
    return out


def stress_modes(st: Study, fam: str) -> list[str]:
    run = {k[5] for k in st.keys(MAIN_BLOCKS, fam, "1min", held_out=False)}
    return [m for m in MODES if MODES[m]["stress"] and m in run]


def d2(st: Study) -> dict:
    """D2: per instance and mode, the median r0 over held-out cells; W0 per policy and instance = the maximum
    over the stress modes of the median r0 (§5.5)."""
    out = {}
    for fam in FAMILIES:
        modes = sorted({k[5] for k in st.keys(MAIN_BLOCKS, fam, "1min", held_out=False)}, key=list(MODES).index)
        per_mode = {}
        for md in modes:
            ks = st.keys(MAIN_BLOCKS, fam, "1min", md)
            per_mode[md] = {"cells": len(ks), "r0": {t: _agg([_r0(st.cm[k], t) for k in ks]) for t in st.tags}}
        sm = stress_modes(st, fam)
        W0 = {}
        for t in st.tags:
            meds = [(per_mode[md]["r0"][t]["median"], md) for md in sm if per_mode.get(md)
                    and per_mode[md]["r0"][t]["median"] is not None]
            W0[t] = {"W0": max(meds)[0] if meds else None, "argmax_mode": max(meds)[1] if meds else None}
        out[fam] = {"modes": per_mode, "stress_modes": sm, "W0": W0}
    return out


def _paired(st: Study, ks, a: str, b: str) -> dict:
    return _agg([st.cm[k][a] / st.cm[k][b] for k in ks if a in st.cm[k] and b in st.cm[k] and st.cm[k][b] > 0])


def d3(st: Study) -> dict:
    """D3: price of the guard (paired ratios guarded / unguarded under L-tr) and trips per run in every mode."""
    price = {}
    for fam in FAMILIES:
        ks = st.keys(MAIN_BLOCKS, fam, "1min", "L-tr")
        price[fam] = {f"{a}/{b}": _paired(st, ks, a, b) for a, b in GUARD_PAIRS}
    trips = defaultdict(dict)
    for r in st.rows:
        if r["policy_id"] != "A8" or r["block"] not in MAIN_BLOCKS or not r["certificate"]:
            continue
        d = trips[(r["family"], r["mode"])].setdefault(r["tag"], {"runs": 0, "aborted": 0, "t_a": []})
        d["runs"] += 1
        if r["certificate"].get("aborted"):
            d["aborted"] += 1
            d["t_a"].append(r["certificate"].get("t_a"))
    tr = {}
    for (fam, md), dd in sorted(trips.items()):
        tr.setdefault(fam, {})[md] = {t: {"runs": v["runs"], "trips_per_run": v["aborted"] / v["runs"] if v["runs"] else None,
                                          "median_t_a": _med(v["t_a"]), "min_t_a": min(v["t_a"]) if v["t_a"] else None}
                                      for t, v in dd.items()}
    return {"price_of_guard_L-tr": price, "trips": tr}


T0G_BLOCK = "T2_t0g"
T0G_REF_BLOCKS = ("Q1", "Q2", "Q6")          # the Tier 1 blocks whose A8 rows T2_t0g reruns under T0g
T0G_UNGUARDED = {"PS-G-T0g": "PS", "BL1-G-T0g": "BL1", "BL5-G-T0g": "BL5"}


def _run_key(r: dict) -> tuple:
    return (r["family"], r["instance"], r["cell"], r["grid"], r["mode"], r["l"], r["p"])


def _test_of(r: dict) -> Optional[str]:
    return (r.get("certificate") or {}).get("test")


def t0g_pairs(st: Study) -> Optional[dict]:
    """Test T0g against T0; None without a T0g run that has a T0 partner and without runs of block T2_t0g.
    Pairs: an A8 run whose certificate records test T0g and an A8 run with test T0 of the same base tag
    (q44_study.BASE_TAGS: PS-G, BL1-G, BL5-G, with their T0g and T0 variants) and the same instance, cell, grid,
    mode, lender and policy seed. This finds the historical pairs (block T2_t0g against the Tier 1 rows of Q1,
    Q2 and Q6 run at commit d2a538d, when T0 was the default and T0g had no reserve) and, for runs made since
    T0g became the default (2026-10-17), the default tags against their T0 variants (q44_study.T0_PARTNERS).
    Per family (I1-I4, F1-F3), mode and T0g tag: runs paired and unpaired (T2_t0g runs without a partner),
    the runs among them whose T0g has the wind-down reserve, trips per run under T0 and under T0g (D3's
    definition), the runs in which T0g aborted earlier than T0, at the same slot, later, not at all while T0
    aborted, and aborted while T0 did not; median t_a under each test; the median and maximum paired cost ratio
    T0g / T0. For block T2_t0g against T0 partners of the main blocks: D3 for T0g, the price of the guard under
    L-tr per instance family (median over the held-out cells of the main blocks of the paired cell-mean ratio
    guarded / unguarded, the unguarded inner from the main blocks) for the T0g tags and, on the same cells, for
    their T0 partners, and the cost ratio T0g / T0 of the cell means per family and mode (held-out cells of the
    main blocks; every cell of Q6). The certificate of the paired T0g runs (cert_summary; under T0g m = 0 is
    required, in the full model as well)."""
    a8 = [r for r in st.rows if r["policy_id"] == "A8" and r["tag"] in BASE_TAGS]
    idx: dict = {}
    for r in a8:
        if _test_of(r) == "T0":
            idx.setdefault((BASE_TAGS[r["tag"]],) + _run_key(r), r)
    rows = [r for r in a8 if _test_of(r) == "T0g" and ((BASE_TAGS[r["tag"]],) + _run_key(r) in idx
                                                      or r["block"] == T0G_BLOCK)]
    if not any((BASE_TAGS[r["tag"]],) + _run_key(r) in idx for r in rows) and not any(
            r["block"] == T0G_BLOCK for r in rows):
        return None
    acc = defaultdict(lambda: {"pairs": 0, "unpaired": 0, "reserve": 0, "trips_T0": 0, "trips_T0g": 0, "earlier": 0,
                               "same": 0, "later": 0, "T0g_none_T0_abort": 0, "T0g_abort_T0_none": 0, "ratio": [],
                               "t_a_T0": [], "t_a_T0g": [], "earlier_runs": []})
    paired_rows = []
    for r in rows:
        d = acc[(r["family"], r["mode"], r["tag"])]
        o = idx.get((BASE_TAGS[r["tag"]],) + _run_key(r))
        c1 = r.get("certificate") or {}
        c0 = (o or {}).get("certificate") or {}
        if o is None or not c1.get("available") or not c0.get("available"):
            d["unpaired"] += 1
            continue
        d["pairs"] += 1
        d["reserve"] += int(bool(c1.get("reserve")))
        paired_rows.append(r)
        ta0, ta1 = c0.get("t_a"), c1.get("t_a")
        d["trips_T0"] += int(ta0 is not None)
        d["trips_T0g"] += int(ta1 is not None)
        if ta0 is not None:
            d["t_a_T0"].append(ta0)
        if ta1 is not None:
            d["t_a_T0g"].append(ta1)
        if ta0 is not None and ta1 is not None:
            key = "earlier" if ta1 < ta0 else "same" if ta1 == ta0 else "later"
            d[key] += 1
            if key == "earlier" and len(d["earlier_runs"]) < 20:
                d["earlier_runs"].append({"file": r["file"], "t_a_T0": ta0, "t_a_T0g": ta1})
        elif ta0 is not None:
            d["T0g_none_T0_abort"] += 1
        elif ta1 is not None:
            d["T0g_abort_T0_none"] += 1
            if len(d["earlier_runs"]) < 20:
                d["earlier_runs"].append({"file": r["file"], "t_a_T0": None, "t_a_T0g": ta1})
        if o["total"] > 0:
            d["ratio"].append(r["total"] / o["total"])
    per = {}
    for (fam, md, tag), d in sorted(acc.items()):
        n = d["pairs"]
        v = [x for x in d["ratio"] if np.isfinite(x)]
        per.setdefault(fam, {}).setdefault(md, {})[tag] = {
            "pairs": n, "unpaired": d["unpaired"], "reserve": d["reserve"],
            "trips_per_run_T0": d["trips_T0"] / n if n else None, "trips_per_run_T0g": d["trips_T0g"] / n if n else None,
            "earlier": d["earlier"], "same": d["same"], "later": d["later"],
            "T0g_none_T0_abort": d["T0g_none_T0_abort"], "T0g_abort_T0_none": d["T0g_abort_T0_none"],
            "median_t_a_T0": _med(d["t_a_T0"]), "median_t_a_T0g": _med(d["t_a_T0g"]),
            "cost_ratio_median": _med(v), "cost_ratio_max": float(max(v)) if v else None,
            "earlier_runs": d["earlier_runs"]}
    # D3 under T0g and the cell-mean cost ratios: block T2_t0g against its partners of the main blocks, where these
    # are T0 runs (the Tier 1 runs before 2026-10-17)
    partner_t0 = all(_test_of(r) == "T0" for r in st.rows
                     if r["block"] in T0G_REF_BLOCKS and r["tag"] in set(T0G_PAIRS.values()) and r.get("certificate"))
    price = {}
    for fam in (FAMILIES if partner_t0 and any(r["block"] == T0G_BLOCK for r in rows) else ()):
        ks = st.keys(MAIN_BLOCKS, fam, "1min", "L-tr")
        price[fam] = {}
        for tg, unguarded in T0G_UNGUARDED.items():
            pairs = [(st.cm.get((T0G_BLOCK,) + k[1:], {}).get(tg), st.cm[k].get(T0G_PAIRS[tg]), st.cm[k].get(unguarded))
                     for k in ks]
            pairs = [(a, b, u) for a, b, u in pairs if a is not None and b is not None and u is not None and u > 0]
            price[fam][f"{tg}/{unguarded}"] = _agg([a / u for a, b, u in pairs])
            price[fam][f"{T0G_PAIRS[tg]}/{unguarded} (same cells)"] = _agg([b / u for a, b, u in pairs])
    cost = {}
    for k in (sorted(st.cm) if partner_t0 else ()):
        if k[0] not in T0G_REF_BLOCKS or k in st.dups:
            continue
        if k[0] in MAIN_BLOCKS and st.tuning.get(k):
            continue
        k2 = (T0G_BLOCK,) + k[1:]
        if k2 not in st.cm:
            continue
        for tg in T0G_PAIRS:
            a, b = st.cm[k2].get(tg), st.cm[k].get(T0G_PAIRS[tg])
            if a is not None and b is not None and b > 0:
                cost.setdefault(k[1], {}).setdefault(k[5], {}).setdefault(tg, []).append(a / b)
    cost = {f: {md: {tg: _agg(v) for tg, v in tt.items()} for md, tt in mm.items()} for f, mm in cost.items()}
    seen = {id(r) for r in paired_rows}
    t0g_rows = paired_rows + [r for r in rows if r["block"] == T0G_BLOCK and id(r) not in seen]
    return {"pairs": per, "price_of_guard_L-tr": price, "cost_ratio_T0g_over_T0": cost,
            "historical_T2_t0g": bool(partner_t0 and any(r["block"] == T0G_BLOCK for r in rows)),
            "certificate_full_model": cert_summary([r for r in t0g_rows if r["grid"] != "core"], core=False),
            "certificate_core": cert_summary([r for r in t0g_rows if r["grid"] == "core"], core=True)}


def criteria(D1: dict, D2: dict, tags) -> dict:
    out = {}
    for t in tags:
        d1v = {f: D1[f]["r_best"].get(t, {}).get("median") for f in FAMILIES if f in D1}
        w0 = {f: D2[f]["W0"].get(t, {}).get("W0") for f in FAMILIES if f in D2}
        n_t = sum(1 for v in d1v.values() if v is not None and v <= 1 + X_T)
        T = n_t >= 3
        S = len([f for f in FAMILIES if w0.get(f) is not None]) == len(FAMILIES) and \
            all(w0[f] <= 1 + Y_S for f in FAMILIES)
        out[t] = {"T": bool(T), "S": bool(S), "D1": d1v, "W0": w0, "instances_meeting_T": n_t,
                  "complete": all(v is not None for v in d1v.values()) and all(w0.get(f) is not None for f in FAMILIES)}
    return out


def framing(crit: dict) -> dict:
    """The framing that §5.6's rule indicates (A, B1, B2, C, D); an input, not a decision."""
    g = crit.get("PS-G")
    if g is None:
        return {"framing": None, "reason": "PS-G not run"}
    if not g["complete"]:
        miss = [f for f in FAMILIES if g["D1"].get(f) is None or g["W0"].get(f) is None]
        return {"framing": None, "reason": f"incomplete: PS-G has no D1 or W0 on {miss}"}
    both = sorted(t for t, c in crit.items() if c["T"] and c["S"] and t != "PS-G")
    if not g["T"]:
        gb = [t for t in GUARDED_BASELINES if t in both]
        return {"framing": "C", "reason": "PS-G misses criterion T", "guarded_baselines_meeting_T_and_S": gb,
                "note": "framing B1 applies with that baseline as the inner policy" if gb else None,
                "others_meeting_T_and_S": both}
    if not g["S"]:
        return {"framing": "D", "reason": "PS-G meets T but misses S", "others_meeting_T_and_S": both}
    ub = [t for t in RENTING if t in both]
    gb = [t for t in GUARDED_BASELINES if t in both]
    if ub:
        return {"framing": "B2", "reason": f"PS-G meets T and S, and the unguarded renting baseline(s) {ub} too",
                "others_meeting_T_and_S": both}
    if gb:
        return {"framing": "B1", "reason": f"PS-G meets T and S, the guarded baseline(s) {gb} too, and no "
                                           "unguarded renting baseline does", "others_meeting_T_and_S": both}
    return {"framing": "A", "reason": "PS-G meets T and S and no renting baseline, guarded or not, does",
            "others_meeting_T_and_S": both}


def d4(st: Study, D1: dict, D2: dict) -> dict:
    """D4: BL1-G and BL5-G against PS-G (paired ratios) in every Q1 and Q2 cell-mode, and criteria T and S
    for every policy."""
    per = {}
    for fam in FAMILIES:
        modes = sorted({k[5] for k in st.keys(MAIN_BLOCKS, fam, "1min", held_out=False)}, key=list(MODES).index)
        per[fam] = {}
        for md in modes:
            ks = st.keys(MAIN_BLOCKS, fam, "1min", md)
            per[fam][md] = {f"{a}/{b}": {**_paired(st, ks, a, b),
                                         "per_cell": {f"{k[2]}:c{k[3]}": (st.cm[k][a] / st.cm[k][b]
                                                                          if a in st.cm[k] and b in st.cm[k] else None)
                                                      for k in ks}}
                            for a, b in CONTROL_PAIRS}
    crit = criteria(D1, D2, st.tags)
    return {"paired": per, "criteria": crit, "framing_indicated": framing(crit),
            "thresholds": {"x_T": X_T, "y_S": Y_S, "T": "D1 <= 1 + x on at least three of I1-I4",
                           "S": "W0 <= 1 + y on every instance"}}


def _bounds(m: int, rho: float) -> dict:
    Hm = sum(1.0 / i for i in range(1, m + 1))
    return {"rho_m_over_m_plus_rho_minus_1": rho * m / (m + rho - 1), "min_rho_2m": min(rho, 2 * m),
            "2H_m_plus_1": 2 * Hm + 1}


def d5(st: Study) -> dict:
    """D5: family ratios to the exact OPT (mean and maximum over the runs) against rho, with the bounds of
    C3-T4, O1-B and O1-D (F1, F2) and C3-P5's revocable-only values (F3); the certificate on every guarded
    family run (V6)."""
    acc = defaultdict(list)
    meta = {}
    for r in st.rows:
        if r["grid"] != "core":
            continue
        k = (r["family"], r["instance"], r["mode"], r["tag"])
        acc[k].append(r["ratio_opt"])
        meta[(r["family"], r["instance"], r["mode"])] = (r.get("m"), r.get("rho"), r.get("values") or {}, r.get("rho1"))
    out = defaultdict(lambda: defaultdict(dict))
    for (fam, inst, md, tag), v in sorted(acc.items()):
        m, rho, vals, rho1 = meta[(fam, inst, md)]
        e = out[fam][f"{inst}:{md}"]
        if not e:
            e.update(instance=inst, mode=md, m=m, rho=rho, values=vals)
            if m is not None and rho is not None:
                e["bounds"] = _bounds(int(m), float(rho))
            if rho1 is not None:
                T, beta = int(vals.get("T")), float(vals.get("beta"))
                e["bounds"] = {"revocable_only_asymptote_a1rho1_over_a2": rho1 / 1.3,
                               "revocable_only_finite_T": (T / 2) * (beta + 2) / (beta + 1.3 * T)}
                e["rho1"] = rho1
            e["ratio"] = {}
        vv = [x for x in v if x is not None]
        e["ratio"][tag] = {"mean": float(np.mean(vv)) if vv else None, "max": float(np.max(vv)) if vv else None,
                           "min": float(np.min(vv)) if vv else None, "runs": len(v)}
    cert = cert_summary([r for r in st.rows if r["grid"] == "core"], core=True)
    return {"families": {f: dict(d) for f, d in out.items()}, "certificate": cert}


def cert_summary(rows: list[dict], core: bool) -> dict:
    """Per guarded tag and mode: runs, certificates available and held, aborts, max core-bound violation and
    S-mode excess, drops and refusals of S's purchases after t_a, switches of S after t_a; for T0g runs with the
    wind-down reserve (q44_study.certificate): their number, the runs in Theorem W's proven case, the failures of
    the E-mode check with the reserve and of wind-down cost <= budget, and the largest wind-down cost and budget."""
    acc = defaultdict(lambda: {"runs": 0, "available": 0, "held": 0, "aborted": 0, "core_bound_fail": 0,
                               "e_mode_fail": 0, "m_fail": 0, "s_mode_excess_max": None, "drops_after_t_a": 0,
                               "refusals_after_t_a": 0, "switches_after_t_a": 0, "reserve": 0, "proven_case": 0,
                               "e_mode_reserve_fail": 0, "wind_down_fail": 0, "wind_down_cost_max": None,
                               "budget_t_a_max": None, "failures": []})
    for r in rows:
        c = r.get("certificate")
        if r["policy_id"] != "A8":
            continue
        d = acc[(r["tag"], r["mode"])]
        d["runs"] += 1
        if not c or not c.get("available"):
            d["failures"].append({"file": r["file"], "why": "certificate unavailable", "missing": (c or {}).get("missing")})
            continue
        d["available"] += 1
        d["held"] += int(bool(c.get("held")))
        d["aborted"] += int(bool(c.get("aborted")))
        d["core_bound_fail"] += int(not c.get("core_bound_ok"))
        d["e_mode_fail"] += int(not c.get("e_mode_ok"))
        d["m_fail"] += int(not c.get("m_ok"))
        se = c.get("s_mode_excess")
        if se is not None:
            d["s_mode_excess_max"] = se if d["s_mode_excess_max"] is None else max(d["s_mode_excess_max"], se)
        for k in ("drops_after_t_a", "refusals_after_t_a", "switches_after_t_a"):
            d[k] += int(c.get(k) or 0)
        if c.get("reserve"):
            d["reserve"] += 1
            d["proven_case"] += int(bool(c.get("proven_case")))
            d["e_mode_reserve_fail"] += int(not c.get("e_mode_reserve_ok"))
            d["wind_down_fail"] += int(bool(c.get("proven_case")) and not c.get("wind_down_ok"))
            for k, kk in (("wind_down_cost", "wind_down_cost_max"), ("budget_t_a", "budget_t_a_max")):
                v = c.get(k)
                if v is not None:
                    d[kk] = v if d[kk] is None else max(d[kk], v)
        if not c.get("held") and len(d["failures"]) < 20:
            d["failures"].append({"file": r["file"], **{k: c.get(k) for k in (
                "core_bound_ok", "core_bound_slack", "e_mode_ok", "e_mode_max_excess", "m_ok", "s_mode_excess",
                "recomputed_ok", "m_zero_ok", "s_mode_ok", "cor_G3_ok", "lemma_G5_ok", "e_mode_reserve_ok",
                "proven_case", "budget_t_a", "wind_down_cost", "wind_down_ok")}})
    out = {f"{t}|{m}": v for (t, m), v in sorted(acc.items())}
    tot = {k: sum(v[k] for v in acc.values()) for k in ("runs", "available", "held")}
    return {"by_tag_mode": out, "total": tot, "all_held": tot["runs"] > 0 and tot["held"] == tot["runs"],
            "scope": "exact core exports (V6)" if core else
            "full model (T0g with the reserve: Theorem W of guard.py in its proven case; otherwise measured, §3.10)"}


def _sign_table(st: Study, blocks, grid, fam, modes, instances=None, cells=None) -> dict:
    """Median r_best under L-tr and median r0 per mode, per tag, over held-out cells (restricted to `cells`
    {(instance, c)} when given)."""
    res = {}
    for md in modes:
        ks = [k for k in st.keys(blocks, fam, grid, md, instances=instances)
              if cells is None or (k[2], k[3]) in cells or (k[2].split("-")[0], k[3]) in cells]
        if not ks:
            continue
        res[md] = {"cells": len(ks)}
        for t in st.tags:
            v = {"r0": _med([_r0(st.cm[k], t) for k in ks])}
            if md == "L-tr":
                v["r_best"] = _med([_r_best(st.cm[k], t) for k in ks])
            res[md][t] = v
    return res


def _same_side(a: Optional[float], b: Optional[float], thr: float) -> Optional[bool]:
    if a is None or b is None:
        return None
    return (a <= thr) == (b <= thr)


def _compare(var: dict, dflt: dict) -> dict:
    out = {}
    for md, row in var.items():
        if md not in dflt:
            continue
        out[md] = {}
        for t, v in row.items():
            if t == "cells" or t not in dflt[md]:
                continue
            d = dflt[md][t]
            e = {"r0": v["r0"], "r0_default": d["r0"], "r0_same_side_of_1+y": _same_side(v["r0"], d["r0"], 1 + Y_S)}
            if "r_best" in v:
                e.update({"r_best": v["r_best"], "r_best_default": d.get("r_best"),
                          "r_best_same_side_of_1+x": _same_side(v["r_best"], d.get("r_best"), 1 + X_T)})
            out[md][t] = e
    return out


def d6(st: Study) -> dict:
    """D6: whether D1-D2 keep their side of the thresholds on the slow grid (Q5), with s5_tau5_H5 (Q4) and at
    alpha = 0.2, 0.3 (Q3), each against the default 1-min cells with the same config seeds; headroom h = LB /
    BL0a and r_LB per instance and mode (Q5)."""
    out = {"slow_grid": {}, "H5": {}, "alpha": {}, "headroom": {}}
    for fam in FAMILIES:
        slow = _sign_table(st, ("Q5",), "slow", fam, ("L-tr", "L-eg"))
        cells = {(k[2].split("-")[0] if False else k[2], k[3]) for md in ("L-tr", "L-eg")
                 for k in st.keys(("Q5",), fam, "slow", md)}
        dflt = _sign_table(st, MAIN_BLOCKS, "1min", fam, ("L-tr", "L-eg"), cells=cells)
        if slow:
            out["slow_grid"][fam] = _compare(slow, dflt)
    var = _sign_table(st, ("Q4",), "1min", "I2", ("L-tr", "L-eg", "L-iid-0.05"))
    if var:
        cells = {("I2", k[3]) for k in st.keys(("Q4",), "I2", "1min")}
        out["H5"]["I2"] = _compare(var, _sign_table(st, MAIN_BLOCKS, "1min", "I2", ("L-tr", "L-eg", "L-iid-0.05"),
                                                    instances={"I2"}, cells=cells))
    for fam in ("I2", "I3"):
        for a in ("0.2", "0.3"):
            vid = f"{fam}-a{a}"
            var = _sign_table(st, ("Q3",), "1min", fam, ("L-tr", "L-eg", "L-iid-0.05"), instances={vid})
            if var:
                cells = {(fam, k[3]) for k in st.keys(("Q3",), fam, "1min", instances={vid})}
                out["alpha"][vid] = _compare(var, _sign_table(st, MAIN_BLOCKS, "1min", fam,
                                                              ("L-tr", "L-eg", "L-iid-0.05"), instances={fam},
                                                              cells=cells))
    out["headroom"] = headroom(st)
    return out


def _lb_of(st: Study, k, r=None) -> Optional[float]:
    b, fam, inst, c, g, md = k
    if r is not None and MODES.get(md, {}).get("oblivious") is False:
        rec = st.lb_run.get((inst, g, md, c, r["l"], r["tag"], r["p"]))
        return None if rec is None else rec.get("lb")
    recs = [x for (i2, g2, m2, c2, l2), v in st.lb_sched.items() for x in v
            if i2 == inst and g2 == g and m2 == md and c2 == c]
    return _lb_value(recs)


def headroom(st: Study) -> dict:
    """h = LB / BL0a and r_LB = cost / LB (median over held-out cells; tuning cells apart) on the slow grid."""
    out = {}
    slow_blocks = sorted({r["block"] for r in st.rows if r["grid"] == "slow"})
    for fam in FAMILIES:
        for md in ("L-tr", "L-eg", "L-ad", "L-rf"):
            for held in (True, False):
                ks = [k for k in st.keys(slow_blocks, fam, "slow", md, held_out=held)]
                if not held:
                    ks = [k for k in ks if k not in st.keys(slow_blocks, fam, "slow", md, held_out=True)]
                if not ks:
                    continue
                hs, rl = [], defaultdict(list)
                for k in ks:
                    lb = _lb_of(st, k)
                    if lb is None or lb <= 0:
                        continue
                    if "BL0a" in st.cm[k]:
                        hs.append(lb / st.cm[k]["BL0a"])
                    for t, v in st.cm[k].items():
                        rl[t].append(v / lb)
                out.setdefault(fam, {})[md + ("" if held else " (tuning)")] = {
                    "cells": len(ks), "cells_with_lb": len(hs), "h": _agg(hs),
                    "r_LB": {t: _agg(v) for t, v in rl.items()}}
    return out


# ---------------------------------------------------------------- checks V1-V7
def v1(st: Study) -> dict:
    """V1: with every knob off A6, A3 and A2 (and BL0a, BL1) reproduce pd_cost_diag.json on ms s3, policy seed 0."""
    if not PD_COST_DIAG.is_file():
        return {"status": "unavailable", "why": f"{PD_COST_DIAG} missing"}
    ref = json.loads(PD_COST_DIAG.read_text())
    b0 = float(ref["baselines"]["BL0a"])
    want = {"BL0a": b0, "BL1": float(ref["baselines"]["BL1"])}
    a2 = sorted((r for r in ref["rows"] if r["policy"] == "A2"), key=lambda r: r["total_over_BL0a"])
    if a2:
        want["A2"] = a2[0]["total_over_BL0a"] * b0
    for pol in ("A3", "A6"):
        rr = [r for r in ref["rows"] if r["policy"] == pol]
        if rr:
            want[pol] = rr[0]["total_over_BL0a"] * b0
    got = {}
    for r in st.rows:
        if r["family"] == "I1" and r["instance"] == "I1" and r["cell"] == 3 and r["grid"] == "1min" and \
                r["mode"] == "L-tr" and r["p"] == 0 and r["tag"] in want and r["block"] in ("Q0", "Q1"):
            got.setdefault(r["tag"], r["total"])
    res = {t: {"reference": w, "run": got.get(t), "ok": None if got.get(t) is None else
               abs(got[t] - w) <= 1e-6 * max(1.0, w)} for t, w in want.items()}
    ok = [v["ok"] for v in res.values()]
    return {"status": "pass" if ok and all(o is True for o in ok) else ("incomplete" if None in ok else "fail"),
            "values": res, "reference_file": "code/sim/out/ms2_checks/pd_cost_diag.json"}


def v2(st: Study) -> dict:
    """V2: BL0a's cost is identical across modes (per block, instance, cell, grid, policy seed)."""
    acc = defaultdict(list)
    for r in st.rows:
        if r["tag"] == "BL0a":
            acc[(r["block"], r["instance"], r["cell"], r["grid"], r["p"])].append((r["mode"], r["total"]))
    bad = []
    for k, v in acc.items():
        vals = [x for _, x in v]
        if max(vals) - min(vals) > REL * max(1.0, max(vals)):
            bad.append({"cell": list(k), "totals": dict(v)})
    return {"status": "pass" if not bad else "fail", "groups": len(acc), "violations": bad[:50]}


def v3(st: Study) -> dict:
    """V3: every policy's cost under L-ad equals its cost under L-eg (same instance, cell, grid, tag, seed)."""
    eg = {(r["instance"], r["cell"], r["grid"], r["tag"], r["p"]): r["total"] for r in st.rows if r["mode"] == "L-eg"}
    pairs, bad = 0, []
    for r in st.rows:
        if r["mode"] != "L-ad":
            continue
        k = (r["instance"], r["cell"], r["grid"], r["tag"], r["p"])
        if k in eg:
            pairs += 1
            if abs(eg[k] - r["total"]) > 1e-6 * max(1.0, eg[k]):
                bad.append({"run": r["file"], "L-ad": r["total"], "L-eg": eg[k]})
    if pairs == 0:
        return {"status": "not run", "why": "no L-ad run with an L-eg counterpart (Tier 2 block T2_ad)"}
    return {"status": "pass" if not bad else "fail", "pairs": pairs, "violations": bad[:50]}


def v4(st: Study) -> dict:
    """V4: every slow-grid run with violations absorbed costs at least its LB (Proposition M4); runs outside
    the plan class P1 below their LB are listed apart (they can cost less than the P1 optimum)."""
    checked, bad, non_p1 = 0, [], []
    for r in st.rows:
        if r["grid"] != "slow" or r["violations"] != "absorb":
            continue
        k = cell_key(r)
        lb = _lb_of(st, k, r)
        if lb is None:
            continue
        checked += 1
        if r["total"] < lb * (1 - 1e-6) - 1e-9:
            (bad if r["p1"] else non_p1).append({"run": r["file"], "total": r["total"], "lb": lb})
    if checked == 0:
        return {"status": "not run", "why": "no slow-grid run with an LB"}
    return {"status": "pass" if not bad else "fail", "checked": checked, "violations": bad[:50],
            "non_P1_below_lb": non_p1[:50]}


def v5(st: Study) -> dict:
    """V5: BL1 reproduces the 'stay' column of c4_lower.json (a) on the cat-and-mouse family F1."""
    if not C4_LOWER.is_file():
        return {"status": "unavailable"}
    ref = {(int(a["m"]), float(a["rho"])): float(a["stay"]) for a in json.loads(C4_LOWER.read_text())["a"]}
    checked, bad = 0, []
    for r in st.rows:
        if r["family"] != "F1" or r["tag"] != "BL1" or r["ratio_opt"] is None:
            continue
        key = (int(r["m"]), float(r["rho"]))
        if key not in ref:
            continue
        checked += 1
        if abs(r["ratio_opt"] - ref[key]) > 1e-9 * max(1.0, ref[key]):
            bad.append({"run": r["file"], "ratio": r["ratio_opt"], "stay": ref[key]})
    if checked == 0:
        return {"status": "not run"}
    return {"status": "pass" if not bad else "fail", "checked": checked, "violations": bad[:50],
            "reference_file": "code/theory_checks/c3/out/c4_lower.json"}


def v6(st: Study) -> dict:
    cs = cert_summary([r for r in st.rows if r["grid"] == "core"], core=True)
    if cs["total"]["runs"] == 0:
        return {"status": "not run"}
    return {"status": "pass" if cs["all_held"] else "fail", **cs["total"],
            "failures": {k: v["failures"] for k, v in cs["by_tag_mode"].items() if v["failures"]}}


def v7(st: Study) -> dict:
    bad = [{"run": r["file"], "invariant_failures": r["invariant_failures"], "gpu_only_lease_slots": r["gpu_only"]}
           for r in st.rows if r["invariant_failures"] or r["gpu_only"]]
    return {"status": "pass" if not bad and st.rows else ("not run" if not st.rows else "fail"),
            "runs": len(st.rows), "violations": bad[:50]}


def params_check(st: Study) -> dict:
    """The resolved parameters of the PS-G runs against the note's A8 defaults (§5.4): those since the decision
    of 2026-10-17 (GUARD_DEFAULTS: test T0g, wind_down auto, reserve true) or those of the earlier runs
    (GUARD_DEFAULTS_T0: test T0, commits 9cf16de to d2a538d). 'pass' if every run matches one of them and all match
    the same one ('mixed' if both occur); a run that matches neither (e.g. T0g with reserve false) fails, with its
    mismatches against GUARD_DEFAULTS."""
    def same(got, v):
        return abs(float(got) - float(v)) <= 1e-12 if isinstance(v, float) and got is not None else got == v

    bad, n, kinds = [], 0, Counter()
    for r in st.rows:
        if r["tag"] != "PS-G" or not isinstance(r.get("params"), dict):
            continue
        n += 1
        for name, D in (("current", GUARD_DEFAULTS), ("T0", GUARD_DEFAULTS_T0)):
            if all(same(r["params"].get(k), v) for k, v in D.items()):
                kinds[name] += 1
                break
        else:
            for k, v in GUARD_DEFAULTS.items():
                if not same(r["params"].get(k), v):
                    bad.append({"run": r["file"], "param": k, "got": r["params"].get(k), "want": v})
    status = ("not run" if not n else "fail" if bad else "mixed" if len(kinds) > 1 else "pass")
    return {"status": status, "runs": n, "defaults": dict(kinds), "mismatches": bad[:20]}


# ---------------------------------------------------------------- tier 2 and budget
def _ref_blocks(b: str) -> tuple[Optional[str], dict]:
    """(the block's ref_block, {instance id: ref_block} for the instances that name their own) of block b."""
    p = Path(__file__).resolve().parent / "q44_blocks" / f"{b}.json"
    if not p.is_file():
        return None, {}
    bj = json.loads(p.read_text())
    return bj.get("ref_block"), {i["id"]: i["ref_block"] for i in bj.get("instances") or [] if i.get("ref_block")}


def tier2(st: Study) -> dict:
    """Per Tier 2 block: median r0 per instance, mode and tag over held-out cells, and r_best where the
    block or its reference block (ref_block; an instance's own ref_block overrides the block's) has the renting
    baselines."""
    out = {}
    blocks = sorted({r["block"] for r in st.rows if (r.get("tier") or 1) == 2})
    refs, inst_refs = {}, {}
    for b in blocks:
        refs[b], inst_refs[b] = _ref_blocks(b)
    for b in blocks:
        res = {}
        for k in sorted(st.cm):
            if k[0] != b or k in st.dups:
                continue
            res.setdefault(f"{k[2]}|{k[5]}", []).append(k)
        tab = {}
        for name, ks in res.items():
            tab[name] = {"cells": len(ks)}
            for t in st.tags:
                ref = [st.ref_cm(k, inst_refs[b].get(k[2], refs[b])) for k in ks]
                r0 = _med([_r0(st.cm[k], t, rf) for k, rf in zip(ks, ref)])
                rb = _med([_r_best(st.cm[k], t, rf) for k, rf in zip(ks, ref)])
                if r0 is not None or rb is not None:
                    tab[name][t] = {"r0": r0, "r_best": rb}
        out[b] = {"ref_block": refs[b], "table": tab}
        if inst_refs[b]:
            out[b]["ref_block_by_instance"] = dict(inst_refs[b])
    return out


def budget(out: Path) -> dict:
    """Wall time and peak RSS per block from the job records (single-worker sum)."""
    acc = defaultdict(lambda: {"jobs": 0, "wall_s": 0.0, "peak_rss_mb": 0.0, "status": defaultdict(int)})
    for p in sorted((out / "jobs").glob("*.json")) if (out / "jobs").is_dir() else []:
        try:
            j = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        b = str(j.get("job", "")).split(":", 1)[0]
        d = acc[b]
        d["jobs"] += 1
        d["wall_s"] += float(j.get("wall_s") or 0.0)
        d["peak_rss_mb"] = max(d["peak_rss_mb"], float(j.get("peak_rss_mb") or 0.0))
        d["status"][j.get("status")] += 1
    return {b: {**v, "status": dict(v["status"])} for b, v in sorted(acc.items())}


def intensity_table(st: Study) -> dict:
    """Median realized announcements per site-day and mean lease life per instance and mode (BL0a's runs
    give the schedule; lease lives of PS-G and BL1)."""
    acc = defaultdict(lambda: defaultdict(list))
    for r in st.rows:
        if r["block"] not in MAIN_BLOCKS:
            continue
        k = (r["family"], r["mode"])
        if r["tag"] == "BL0a":
            acc[k]["announcements_per_site_day"].append(r["intensity"].get("announcements_per_site_day"))
        if r["tag"] in ("PS-G", "BL1", "PS"):
            acc[k][f"mean_lease_life_min_{r['tag']}"].append(r["intensity"].get("mean_lease_life_min"))
    return {f"{f}|{m}": {k: _med(v) for k, v in d.items()} for (f, m), d in sorted(acc.items())}


# ---------------------------------------------------------------- tables and figures
def _f(x, nd=3) -> str:
    if x is None:
        return "-"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    return f"{x:.{nd}f}"


def _ci(a: dict) -> str:
    if not a or a.get("median") is None:
        return "-"
    lo, hi = a.get("median_ci95") or [None, None]
    return f"{a['median']:.3f} [{_f(lo)}, {_f(hi)}] (n={a.get('n')})"


def tables_md(S: dict) -> str:
    L = ["# Q44 study: tables", "",
         f"Generated by `code/sim/sublet/experiments/q44_summary.py` from `{S['meta']['out']}` "
         f"({S['meta']['written']}, git {S['meta']['git_revision']}). Design: `{NOTE}` §5. "
         "Medians over held-out cells of the main blocks (Q1, Q2; 1-min grid) with 95% bootstrap intervals; "
         "tuning cells are excluded from decisions. Study tables, not paper tables.", ""]
    L += ["## Checks", "", "| Check | Status | Detail |", "|---|---|---|"]
    for k, v in S["checks"].items():
        det = {kk: vv for kk, vv in v.items() if kk not in ("status", "violations", "values", "failures",
                                                              "non_P1_below_lb", "mismatches")}
        L.append(f"| {k} | {v.get('status')} | {json.dumps(det)[:200]} |")
    L += ["", "## D1: r_best under L-tr (median over held-out cells)", "",
          "| Policy | " + " | ".join(FAMILIES) + " |", "|---|" + "---|" * len(FAMILIES)]
    for t in S["meta"]["tags"]:
        cells = [_ci(S["D1"].get(f, {}).get("r_best", {}).get(t)) for f in FAMILIES]
        if any(c != "-" for c in cells):
            L.append(f"| {t}{' *' if t in D1_TAGS else ''} | " + " | ".join(cells) + " |")
    L += ["", "\\* the policies of D1 (§5.6).", "", "## D2: median r0 per stress mode and W0", ""]
    for f in FAMILIES:
        d = S["D2"].get(f)
        if not d or not d["modes"]:
            continue
        modes = list(d["modes"])
        L += [f"### {f} (stress modes for W0: {', '.join(d['stress_modes'])})", "",
              "| Policy | " + " | ".join(modes) + " | W0 |", "|---|" + "---|" * (len(modes) + 1)]
        for t in S["meta"]["tags"]:
            vals = [_f(d["modes"][m]["r0"].get(t, {}).get("median")) for m in modes]
            if any(v != "-" for v in vals):
                L.append(f"| {t} | " + " | ".join(vals) + f" | {_f(d['W0'].get(t, {}).get('W0'))} |")
        L.append("")
    L += ["## D3: price of the guard under L-tr (median paired ratio) and trips per run", "",
          "| Pair | " + " | ".join(FAMILIES) + " |", "|---|" + "---|" * len(FAMILIES)]
    for a, b in GUARD_PAIRS:
        L.append(f"| {a}/{b} | " + " | ".join(_ci(S["D3"]["price_of_guard_L-tr"].get(f, {}).get(f"{a}/{b}"))
                                               for f in FAMILIES) + " |")
    L += ["", "| Instance | Mode | " + " | ".join(t for t in S["meta"]["tags"] if POLICIES.get(t, {}).get("id") == "A8")
          + " |", "|---|---|" + "---|" * sum(1 for t in S["meta"]["tags"] if POLICIES.get(t, {}).get("id") == "A8")]
    for f, mm in S["D3"]["trips"].items():
        for md, tt in mm.items():
            L.append(f"| {f} | {md} | " + " | ".join(
                (f"{_f(tt[t]['trips_per_run'], 2)} (t_a {_f(tt[t]['median_t_a'], 0)})" if t in tt else "-")
                for t in S["meta"]["tags"] if POLICIES.get(t, {}).get("id") == "A8") + " |")
    L += ["", "## D4: controls and criteria", "", "| Policy | T | S | D1 per instance | W0 per instance |",
          "|---|---|---|---|---|"]
    for t, c in S["D4"]["criteria"].items():
        L.append(f"| {t} | {_f(c['T'])} | {_f(c['S'])} | " + ", ".join(f"{f} {_f(v)}" for f, v in c["D1"].items())
                 + " | " + ", ".join(f"{f} {_f(v)}" for f, v in c["W0"].items()) + " |")
    fr = S["D4"]["framing_indicated"]
    L += ["", f"Framing indicated by the rule of §5.6: **{fr.get('framing')}** - {fr.get('reason')}.", "",
          "| Instance | Mode | " + " | ".join(f"{a}/{b}" for a, b in CONTROL_PAIRS) + " |",
          "|---|---|" + "---|" * len(CONTROL_PAIRS)]
    for f, mm in S["D4"]["paired"].items():
        for md, pp in mm.items():
            L.append(f"| {f} | {md} | " + " | ".join(_ci(pp[f"{a}/{b}"]) for a, b in CONTROL_PAIRS) + " |")
    L += ["", "## D5: families, ratio to exact OPT (mean over runs; max)", ""]
    for fam, insts in S["D5"]["families"].items():
        tags = sorted({t for e in insts.values() for t in e["ratio"]},
                      key=lambda t: list(POLICIES).index(t) if t in POLICIES else 99)
        L += [f"### {fam}", "", "| Instance | Mode | bounds | " + " | ".join(tags) + " |",
              "|---|---|---|" + "---|" * len(tags)]
        for e in insts.values():
            bd = ", ".join(f"{k} {_f(v)}" for k, v in (e.get("bounds") or {}).items())
            L.append(f"| {e['instance']} | {e['mode']} | {bd} | " + " | ".join(
                (f"{_f(e['ratio'][t]['mean'])} ({_f(e['ratio'][t]['max'])})" if t in e["ratio"] else "-") for t in tags)
                + " |")
        L.append("")
    c5 = S["D5"]["certificate"]
    L += [f"Certificate on the family runs: {c5['total']['held']} of {c5['total']['runs']} held.", "",
          "## D6: sensitivity", ""]
    for name, part in (("slow grid (Q5) vs 1-min", S["D6"]["slow_grid"]), ("s5_tau5_H5 (Q4)", S["D6"]["H5"]),
                       ("alpha (Q3)", S["D6"]["alpha"])):
        for inst, mm in part.items():
            L += [f"### {name}: {inst}", "", "| Mode | Policy | r_best (default) | same side of 1+x | r0 (default) | "
                  "same side of 1+y |", "|---|---|---|---|---|---|"]
            for md, tt in mm.items():
                for t, e in tt.items():
                    L.append(f"| {md} | {t} | {_f(e.get('r_best'))} ({_f(e.get('r_best_default'))}) | "
                             f"{_f(e.get('r_best_same_side_of_1+x'))} | {_f(e['r0'])} ({_f(e['r0_default'])}) | "
                             f"{_f(e['r0_same_side_of_1+y'])} |")
            L.append("")
    L += ["### headroom h = LB / BL0a and r_LB (slow grid)", "", "| Instance | Mode | h | r_LB PS-G | r_LB PS | r_LB BL1 | "
          "r_LB BL5 |", "|---|---|---|---|---|---|---|"]
    for f, mm in S["D6"]["headroom"].items():
        for md, e in mm.items():
            L.append(f"| {f} | {md} | {_ci(e['h'])} | " + " | ".join(_f((e['r_LB'].get(t) or {}).get('median'))
                                                                    for t in ("PS-G", "PS", "BL1", "BL5")) + " |")
    cf = S["certificate_full_model"]
    L += ["", "## Certificate on full-model runs (§3.10; T0g with the reserve: guard.py Theorem W in its proven case)",
          "", f"{cf['total']['held']} of {cf['total']['runs']} guarded runs held.", "",
          "| Tag | Mode | runs | held | aborted | core bound fails | max S-mode excess | drops after t_a | "
          "refusals after t_a | switches after t_a | reserve runs | proven case | wind-down > budget |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, v in cf["by_tag_mode"].items():
        t, md = k.split("|")
        L.append(f"| {t} | {md} | {v['runs']} | {v['held']} | {v['aborted']} | {v['core_bound_fail']} | "
                 f"{_f(v['s_mode_excess_max'])} | {v['drops_after_t_a']} | {v['refusals_after_t_a']} | "
                 f"{v['switches_after_t_a']} | {v.get('reserve', 0)} | {v.get('proven_case', 0)} | "
                 f"{v.get('wind_down_fail', 0)} |")
    if S.get("T0g"):
        L += _t0g_md(S["T0g"])
    if S["duplicates"]:
        L += ["", "## Dropped duplicate cells", ""] + [f"- {d['cell']} = {d['duplicate_of']}" for d in S["duplicates"]]
    if S["errors"]:
        L += ["", "## Errors", ""] + [f"- {e.get('file')}: {e.get('error')}" for e in S["errors"][:50]]
    L += ["", "## Budget (single-worker job time per block)", "", "| Block | jobs | wall time (h) | peak RSS (MB) | status |",
          "|---|---|---|---|---|"]
    for b, v in S["budget"].items():
        L.append(f"| {b} | {v['jobs']} | {v['wall_s'] / 3600:.2f} | {v['peak_rss_mb']:.0f} | {json.dumps(v['status'])} |")
    return "\n".join(L) + "\n"


def _t0g_md(T: dict) -> list:
    """The tables.md section of t0g_pairs (test T0g against T0): the historical block T2_t0g against Q1, Q2 and Q6,
    and default tags against their T0 variants; the column 'reserve' counts the T0g runs with the wind-down
    reserve (runs since 2026-10-17)."""
    hist = (f" (historical: block {T0G_BLOCK} against Q1, Q2, Q6 as run at commit d2a538d, T0g without the "
            "reserve)") if T.get("historical_T2_t0g") else ""
    L = ["", f"## T0g against T0 (paired runs: same base tag, cell, mode and seeds){hist}", "",
         "| Instance | Mode | Tag | pairs | reserve | trips/run T0 | trips/run T0g | T0g earlier | same | later | "
         "T0g none | T0g only | median t_a T0 | median t_a T0g | cost T0g/T0 median (max) |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for f, mm in T["pairs"].items():
        for md, tt in mm.items():
            for tg, e in tt.items():
                L.append(f"| {f} | {md} | {tg} | {e['pairs']} | {e.get('reserve', 0)} | "
                         f"{_f(e['trips_per_run_T0'], 2)} | "
                         f"{_f(e['trips_per_run_T0g'], 2)} | {e['earlier']} | {e['same']} | {e['later']} | "
                         f"{e['T0g_none_T0_abort']} | {e['T0g_abort_T0_none']} | {_f(e['median_t_a_T0'], 0)} | "
                         f"{_f(e['median_t_a_T0g'], 0)} | {_f(e['cost_ratio_median'])} ({_f(e['cost_ratio_max'])}) |")
    keys = [k for k in next(iter(T["price_of_guard_L-tr"].values()), {})]
    if keys:
        L += ["", "D3 under T0g: price of the guard under L-tr (median paired ratio over held-out cells of the main "
              "blocks)", "", "| Pair | " + " | ".join(FAMILIES) + " |", "|---|" + "---|" * len(FAMILIES)]
    for k in keys:
        L.append(f"| {k} | " + " | ".join(_ci(T["price_of_guard_L-tr"].get(f, {}).get(k)) for f in FAMILIES) + " |")
    for name in ("certificate_full_model", "certificate_core"):
        c = T[name]
        L += ["", f"Certificate of the T0g runs ({c['scope']}): {c['total']['held']} of {c['total']['runs']} held."]
    return L


def _plain_log(ax) -> None:
    """Log axes with plain tick labels (1, 2, 5, 10, ...)."""
    import matplotlib.ticker as mt
    for axis, setter in ((ax.xaxis, ax.set_xscale), (ax.yaxis, ax.set_yscale)):
        setter("log")
        axis.set_major_locator(mt.LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
        axis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:g}"))
        axis.set_minor_formatter(mt.NullFormatter())


def figures(S: dict, st: Study, fig_dir: Path) -> list[str]:
    """The three study views (§5.5): robustness-consistency scatter per instance; r0 against announcements per
    site-day; family ratios against rho with the bounds. Single-column width (3.5 in), 8-pt text."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker
    plt.rcParams.update({"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "legend.fontsize": 7,
                         "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.5})
    fig_dir.mkdir(parents=True, exist_ok=True)
    made = []
    label = "Q44 study figure (not a paper figure)"
    # 1. robustness-consistency scatter per instance
    fams = [f for f in FAMILIES if f in S["D1"] and f in S["D2"]]
    if fams:
        fig, axs = plt.subplots(2, 2, figsize=(7.0, 5.2), squeeze=False)
        for ax, f in zip(axs.flat, fams + [None] * (4 - len(fams))):
            if f is None:
                ax.axis("off")
                continue
            for i, t in enumerate(LINE_TAGS):
                x = S["D1"][f]["r_best"].get(t, {}).get("median")
                y = S["D2"][f]["W0"].get(t, {}).get("W0")
                if x is None or y is None:
                    continue
                ax.plot([x], [y], "o", ms=5, color=PALETTE[i % len(PALETTE)], mec="white", mew=1.0)
                ax.annotate(t, (x, y), xytext=(3, 3), textcoords="offset points", fontsize=7, color="#52514e")
            ax.axvline(1 + X_T, color="#999", lw=0.8, ls="--")
            ax.axhline(1 + Y_S, color="#999", lw=0.8, ls="--")
            ax.set_title(f)
            ax.set_xlabel("median r_best under L-tr (held-out cells)")
            ax.set_ylabel("W0 (max over stress modes of median r0)")
        fig.suptitle(label, fontsize=7, color="#777")
        fig.tight_layout()
        p = fig_dir / "robustness_consistency.pdf"
        fig.savefig(p)
        plt.close(fig)
        made.append(str(p))
    # 2. r0 against realized announcements per site-day
    if fams:
        fig, axs = plt.subplots(2, 2, figsize=(7.0, 5.2), squeeze=False)
        for ax, f in zip(axs.flat, fams + [None] * (4 - len(fams))):
            if f is None:
                ax.axis("off")
                continue
            modes = [m for m in S["D2"][f]["modes"] if S["intensity"].get(f"{f}|{m}", {}).get("announcements_per_site_day")]
            xs = {m: S["intensity"][f"{f}|{m}"]["announcements_per_site_day"] for m in modes}
            modes = sorted(modes, key=lambda m: xs[m])
            for i, t in enumerate(LINE_TAGS):
                pts = [(max(xs[m], 0.1), S["D2"][f]["modes"][m]["r0"].get(t, {}).get("median")) for m in modes]
                pts = [(x, y) for x, y in pts if y is not None]
                if not pts:
                    continue
                ax.plot(*zip(*pts), "-o", lw=1.2, ms=3, color=PALETTE[i % len(PALETTE)], label=t)
            ax.axhline(1.0, color="#999", lw=0.8, ls="--")
            ax.set_xscale("log")
            ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
            ax.set_title(f)
            ax.set_xlabel("realized announcements per site-day")
            ax.set_ylabel("median r0 (cost / BL0a)")
        h, lab = axs.flat[0].get_legend_handles_labels()
        if h:
            fig.legend(h, lab, loc="lower center", ncol=4, frameon=False)
        fig.suptitle(label, fontsize=7, color="#777")
        fig.tight_layout(rect=(0, 0.08, 1, 0.97))
        p = fig_dir / "r0_vs_intensity.pdf"
        fig.savefig(p)
        plt.close(fig)
        made.append(str(p))
    # 3. family ratios against rho, at m = 4 (F1, F2 per mode) and against rho1 (F3 per T)
    fam = S["D5"]["families"]
    panels = []
    for fname in ("F1", "F2"):
        for key, e in (fam.get(fname) or {}).items():
            if e.get("m") == 4:
                panels.append((fname, e["mode"]))
    panels = sorted(set(panels))
    f3T = sorted({int(e["values"]["T"]) for e in (fam.get("F3") or {}).values()})
    n = len(panels) + len(f3T)
    if n:
        cols = min(3, n)
        rows = int(math.ceil(n / cols))
        fig, axs = plt.subplots(rows, cols, figsize=(7.0, 2.3 * rows + 0.4), squeeze=False)
        flat = list(axs.flat)
        for ax, (fname, md) in zip(flat, panels):
            es = sorted((e for e in fam[fname].values() if e.get("m") == 4 and e["mode"] == md), key=lambda e: e["rho"])
            rhos = [e["rho"] for e in es]
            for i, t in enumerate(FAMILY_FIG_TAGS):
                ys = [e["ratio"].get(t, {}).get("mean") for e in es]
                if any(y is not None for y in ys):
                    ax.plot(rhos, ys, "-o", lw=1.2, ms=3, color=PALETTE[i % len(PALETTE)], label=t)
            for bk, ls in (("rho_m_over_m_plus_rho_minus_1", ":"), ("min_rho_2m", "--"), ("2H_m_plus_1", "-.")):
                ax.plot(rhos, [e["bounds"][bk] for e in es], ls, color="#aaa", lw=0.9)
            _plain_log(ax)
            ax.set_title(f"{fname} {md}, m = 4")
            ax.set_xlabel("rho")
            ax.set_ylabel("ALG / OPT")
        for ax, T in zip(flat[len(panels):], f3T):
            es = sorted((e for e in fam["F3"].values() if int(e["values"]["T"]) == T), key=lambda e: e["rho1"])
            x = [e["rho1"] for e in es]
            for i, t in enumerate(FAMILY_FIG_TAGS):
                ys = [e["ratio"].get(t, {}).get("mean") for e in es]
                if any(y is not None for y in ys):
                    ax.plot(x, ys, "-o", lw=1.2, ms=3, color=PALETTE[i % len(PALETTE)], label=t)
            ax.plot(x, [e["bounds"]["revocable_only_finite_T"] for e in es], "--", color="#aaa", lw=0.9)
            _plain_log(ax)
            ax.set_title(f"F3 F-eg, T = {T}")
            ax.set_xlabel("rho_1")
            ax.set_ylabel("ALG / OPT")
        for ax in flat[n:]:
            ax.axis("off")
        h, lab = flat[0].get_legend_handles_labels()
        if h:
            fig.legend(h, lab, loc="lower center", ncol=4, frameon=False)
        fig.suptitle(label + "\ngrey: rho m/(m+rho-1) dotted, min(rho, 2m) dashed, 2H_m+1 dash-dot (F1, F2); "
                     "revocable-only value dashed (F3)", fontsize=7, color="#777")
        fig.tight_layout(rect=(0, 0.1, 1, 0.93))
        p = fig_dir / "family_ratios.pdf"
        fig.savefig(p)
        plt.close(fig)
        made.append(str(p))
    return made


# ---------------------------------------------------------------- main
def summarize(out: Path, fig: bool = True) -> dict:
    from .q44_study import _dump, _git_revision, _versions
    st = Study(out)
    D1 = d1(st)
    D2 = d2(st)
    S = {"meta": {"script": "code/sim/sublet/experiments/q44_summary.py", "note": NOTE, "out": str(out),
                  "written": time.strftime("%Y-%m-%dT%H:%M:%S"), "git_revision": _git_revision(),
                  "versions": _versions(), "runs": len(st.rows), "tags": st.tags,
                  "blocks": sorted({r["block"] for r in st.rows}),
                  "definitions": {"r0": "cost / BL0a (same cell-mode, policy seeds averaged)",
                                  "r_best": "cost / min(BL1, BL2, BL5)", "W0": "max over stress modes of median r0",
                                  "h": "LB / BL0a (slow grid)", "r_LB": "cost / LB (slow grid, violations absorbed)",
                                  "decision_cells": "held-out cells of Q1 and Q2 on the 1-min grid"}},
         "checks": {"V1": v1(st), "V2": v2(st), "V3": v3(st), "V4": v4(st), "V5": v5(st), "V6": v6(st), "V7": v7(st),
                    "PS-G_params": params_check(st)},
         "D1": D1, "D2": D2, "D3": d3(st), "D4": d4(st, D1, D2), "D5": d5(st), "D6": d6(st),
         "certificate_full_model": cert_summary([r for r in st.rows if r["grid"] != "core"], core=False),
         "intensity": intensity_table(st), "tier2": tier2(st),
         "duplicates": [{"cell": list(k), "duplicate_of": list(v)} for k, v in sorted(st.dups.items())],
         "errors": [{k: e.get(k) for k in ("file", "job", "tag", "error")} for e in st.errors],
         "budget": budget(out)}
    T0g = t0g_pairs(st)                  # only with paired T0g and T0 runs, or runs of block T2_t0g
    if T0g is not None:
        S["T0g"] = T0g
    S["figures"] = figures(S, st, out / "fig") if fig and st.rows else []
    _dump(S, out / "summary.json")
    (out / "tables.md").write_text(tables_md(S))
    return S


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=None, help="study folder (default SUBLET_Q44_DIR or "
                                                           "code/sim/out/q44_study)")
    ap.add_argument("--no-fig", action="store_true", help="skip the figures")
    a = ap.parse_args(argv)
    out = out_root(a.out)
    S = summarize(out, fig=not a.no_fig)
    print(json.dumps({"runs": S["meta"]["runs"], "checks": {k: v.get("status") for k, v in S["checks"].items()},
                      "framing_indicated": S["D4"]["framing_indicated"].get("framing"),
                      "figures": S["figures"]}, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
