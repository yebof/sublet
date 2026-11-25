"""E7o: the out-of-sample folds of MS7's X2 (design/ms7/plan.md §3 X2; design/ms7/feasibility/oos.md §3 and §4 items
6 and 8; change C55).

The confirmation (e7h, design/sublet_v2.md §4.4) fits every lender quantity (the P99 notice buffer, B, the lease size
v_top, the menu pruning and the IR prices) on the same series the lender replays, and its demand on the evaluated
horizon itself (own capacity C0 = the P75 of that horizon's smoothed demand, Gamma from that horizon's peak overflow).
E7o holds the calibration out and pairs every held-out run with an in-sample twin on the same windows and the same
demand, so that OOS minus IS isolates the lender calibration (oos.md §3; only calibration is held out: development
and the pilot saw every MaaS day, oos.md risk 2).

Parts (E7O_PART; one part per run of run_e7o.sh) are the folds of the MaaS week (FOLDS; the 20 clusters replay on the
trace's own clock, every cluster at the same offset, no rotation, no wrap; the spot pools as below in both folds):
  fwd   (primary) the MaaS lenders calibrated on slots [0, 1152) (days 1-4), evaluated on [1152, 2016) (days 5-7)
  rev   (robustness) calibrated on [864, 2016) (days 4-7), evaluated on [0, 864) (days 1-3); the owed series' lead-in
        before slot 0 wraps to the end of day 7 (lender.owed_series; at most D_max = 300 min)
Arms (ARMS), the same windows, clock and demand in both:
  oos   every trace lender with calib_slots: MaaS the fold's calibration days, spot weeks 1-12 (SPOT_CALIB)
  is    no calib_slots: the whole series, the confirmation's builder (the in-sample twin)
Cells (cell(k), k = 0..15, the same in both folds): config seed 301 + k (the confirmation week's draws: start minute,
lender regions, load scenarios; the lender offsets and the demand sources are then replaced in the resolved config,
so no draw changes), the spot pools at one 72-h block of weeks 13-25 (start 24192 + 1729 k, disjoint), the WildChat
held-out week 37 + round(35 k / 15) of a4c_wildchat_weeks.json (its own separable profile, level normalized; pooled
over 4 weeks for south_southeast_asia and south_america, a4c's pool_regions), xi from the held-out BurstGPT weeks
(XI_HELD: the later half of the full weeks of burstgpt_1, _2 and _3, 15 weeks; region i of cell k takes
XI_HELD[(5 k + i + k // 3) % 15], so a cell's five regions use five different weeks and each region meets every week
once over cells 0-14), and the borrower model 'a4c_fit' (p_o and r_oj counted before the first held-out week). The
demand of both arms is fitted out of sample: C0 on the fit period (borrowers.demand_fit: one fit week of p_o 'a4c_fit'
x xi of the region's fit week fit_week(series, week), the week of the same BurstGPT series as many weeks into its
earlier half (XI_FIT) as the evaluated week is into the later half, so that a region's C0 is fitted on the past of
its own demand source; 15 of XI_FIT's 16 weeks) and Gamma = market tightness x the oos arm's supply / the fit period's
peak overflow, pinned (borrowers.gamma) to that value in both arms (pinned_gamma), so the two arms are paired on
demand (oos.md §1.8, risk 4). Horizon HORIZON_MIN = 4320 (72 h), policy seed 0, lender seed =
config seed, the 15 tags of TAGS (oos.md §3 names Sublet, A9, the seven H1 baselines, the four H2b baselines, CR and
A9-kstar: 15 tags, though it counts 14; its cost sum of 5,847 s per week is that of these 15) under the 8 modes of
MODES (L-tr, L-vr, the five stress modes of W0 and L-hon; L-vr is a headline mode, since L-tr absorbs violations,
oos.md risk 3).

Jobs: one per (cell, arm, tag) ('e7o:<part>:k=cell:arm=<arm>:tag=<tag>:cell=<k>'), every mode in one process (A9's
contract table once per job, as e7h). Every run entry is ms5b_common.week_entry's (e7h's) plus fold, arm, cell and the
lender-source block 'sources' (source_fields: buffer violations, the attributable ones, reclaims and violation cuts,
leases and GPU-hours per lender source maas, spot, protected); every run file records the cell, the pinned Gamma and
the instance's calibration per lender (instance_facts). Outputs <root>/out/e7o/<part>/ (jobs/, logs/, runs/ (not
versioned), retry/, manifest.json, summary.json, tables.md, run_e7o.log; ms3_common.COPY_PARTS['e7o']); the frozen
analysis e7o_analysis.py writes <root>/out/e7o/analysis.json and analysis.md from both parts' summaries.

The gate (D6 of design/ms7/plan.md): a job of the full design runs only if design/ms7/registration.md exists at HEAD
and records 'e7o_analysis_sha256: <64 hex>' equal to the sha256 of e7o_analysis.py at HEAD and on disk, and the
working tree is clean (check_registration, as ms5b_common.check_confirmation and e7c's gate); every run file, summary
and manifest records it (kind 'ms7_registration'), never the confirmation's; reduced runs record the gate without
enforcing it.

Command line (ms3_common.main), run from code/sim:
  python -m sublet.experiments.e7o --list | --job ID | --summary | --estimate | --manifest  [--out DIR]
  python -m sublet.experiments.e7o --check-start          the gate of the part(s) of E7O_PART; exit 1 if refused
  python -m sublet.experiments.e7o --retry-list --out DIR  the missing-run rule's rerun (sublet_v2.md §4.5, as e7h)
Without --out the part's folder is the default (one part in E7O_PART). Reduced runs (MS3_E7O_REDUCED=1, run_e7o.sh
--reduced): cell 0 only, at development config seed 101 and a 2-hour horizon (never a seed of the design); summaries
carry meta.reduced; never a result.

Status labels: as e7h's (Theorem W, Remark R, Lemma G5', Corollary G3', Proposition P PROVEN, audited for A8P; A9's
rules HEURISTIC; no competitive ratio is claimed for A9 on the full model).
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import copy
import hashlib
import re
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

from .. import paths
from . import e7
from . import e7h
from . import ms3_common as mc
from . import ms4_common as m4
from . import ms5b_common as m5
from .ms3_common import Job, job_id

EXP = "e7o"
SPEC = "design/ms7/plan.md §3 X2; design/ms7/feasibility/oos.md §3, §4 items 6, 8 (C55)"
PARTS = mc.COPY_PARTS[EXP]                       # ("fwd", "rev")
ARMS = ("oos", "is")
TAGS = ("Sublet", "A9") + m5.H1_SET + m5.H2B_SET + ("CR", "A9-kstar")     # 15 tags (module docstring)
MODES = (m5.TRACE_MODE, "L-vr") + m5.stress_modes() + (m5.HON_MODE,)       # 8 modes
HORIZON_MIN = 4320                               # 72 h: one held-out MaaS block
N_CELLS = 16
CONF_SEEDS = m5.CONF_WEEKS                       # cell k: config seed 301 + k (the confirmation week's draws)
REDUCED_ENV = "MS3_E7O_REDUCED"
REDUCED_HORIZON_MIN = 120
REDUCED_SEED = 101                               # a development seed (never a cell of the design)
WEEK_MIN = m5.WEEK_MIN
SLACK_SLOTS_PER_WEEK = 2016
MAAS_SLOTS = 2016
FOLDS = {"fwd": {"maas_offset": 1152, "maas_calib": (0, 1152), "calib_days": "1-4", "eval_days": "5-7"},
         "rev": {"maas_offset": 0, "maas_calib": (864, 2016), "calib_days": "4-7", "eval_days": "1-3"}}
SPOT_CALIB = (0, 12 * SLACK_SLOTS_PER_WEEK)      # weeks 1-12
SPOT_BLOCK_SLOTS = 864                           # 72 h
SPOT_BLOCK_STRIDE = 1729                         # (50993 - 24192 - 864) // 15: 16 disjoint blocks over weeks 13-25
WILDCHAT_N_WEEKS, WILDCHAT_N_FIT = 73, 37        # a4c_wildchat_weeks.json (checked by tests/test_oos_calibration.py)
BURST_FULL_WEEKS = (("burstgpt_1", 8), ("burstgpt_2", 8), ("burstgpt_3", 15))   # full weeks of the a12 series
XI_HELD = tuple((s, w) for s, n in BURST_FULL_WEEKS for w in range(n - n // 2, n))     # the later halves: 15 weeks
XI_FIT = tuple((s, w) for s, n in BURST_FULL_WEEKS for w in range(n - n // 2))         # the earlier halves: 16 weeks
HELD_START = {s: n - n // 2 for s, n in BURST_FULL_WEEKS}                                 # first week of the later half
REGIONS = ("north_america", "europe", "east_asia", "south_southeast_asia", "south_america")   # bench_e7f's order
WILDCHAT_MODEL = "a4c_fit"
HZ_FACTOR = 0.5                                  # oos.md §5: a 72-h run takes about half a week run's time
EST_BUILD_S = 3.0                                # the pin build and the arm's build (measured 1.0-1.2 s each)
# mean wall_s of the confirmation's week jobs per tag (7 modes, one week; out/sublet_v2/main/jobs/*.json, oos.md §5)
EST_CONF_JOB_S = {"Sublet": 1756.0, "A9": 253.0, "BL1": 231.0, "BL1-BO": 78.0, "BL2": 219.0, "BL3-0": 203.0,
                  "BL4": 211.0, "BL5": 91.0, "BL5-cur": 105.0, "BL5-tau60": 116.0, "BL1-GP": 1678.0, "BL1N": 310.0,
                  "BL5N": 160.0, "CR": 190.0, "A9-kstar": 238.0}
REGISTRATION = "design/ms7/registration.md"
ANALYSIS = Path(__file__).resolve().parent / "e7o_analysis.py"
ANALYSIS_REL = "code/sim/sublet/experiments/e7o_analysis.py"
REG_SHA_RE = re.compile(r"^e7o_analysis_sha256:\s*([0-9a-f]{64})\s*$", re.MULTILINE)
SOURCES = ("maas", "spot", "protected")


# ---------------------------------------------------------------- settings, parts, cells
def design() -> dict:
    red = os.environ.get(REDUCED_ENV, "0") == "1"
    return {"reduced": red, "horizon_min": REDUCED_HORIZON_MIN if red else HORIZON_MIN,
            "cells": [0] if red else list(range(N_CELLS)), "arms": list(ARMS), "tags": list(TAGS),
            "modes": list(MODES), "policy_seeds": [0], "folds": {k: {**v, "maas_calib": list(v["maas_calib"])}
                                                                  for k, v in FOLDS.items()},
            "spot_calib": list(SPOT_CALIB), "spot_block_slots": SPOT_BLOCK_SLOTS,
            "spot_block_stride": SPOT_BLOCK_STRIDE, "wildchat_model": WILDCHAT_MODEL}


def parts() -> list:
    v = os.environ.get("E7O_PART", "")
    ps = [p for p in v.replace(",", " ").split() if p]
    bad = [p for p in ps if p not in PARTS]
    if bad:
        raise ValueError(f"E7O_PART must name parts of {list(PARTS)}, got {v!r}")
    return ps or list(PARTS)


def part_dir(part: str, root=None) -> Path:
    """<root>/out/e7o/<part> (root as ms3_common.ms3_root)."""
    return mc.ms3_root(root) / "out" / EXP / part


def run_path(out, jid: str) -> Path:
    return Path(out) / "runs" / mc.job_file_name(jid)


def fit_week(series: str, week: int) -> tuple:
    """The fit week of an evaluated (held-out) BurstGPT week: the same series, as many weeks into the earlier half as
    `week` is into the later half (XI_FIT; module docstring). ValueError for a week outside XI_HELD."""
    if (series, int(week)) not in XI_HELD:
        raise ValueError(f"fit_week: ({series!r}, {week!r}) is not a held-out BurstGPT week")
    return series, int(week) - HELD_START[series]


def cell(k: int, reduced: Optional[bool] = None) -> dict:
    """The design of cell k (module docstring): config seed, WildChat week (index into a4c_wildchat_weeks.json),
    the spot block's offset, and per region the evaluated and the fit xi source (series, BurstGPT week)."""
    k = int(k)
    if not 0 <= k < N_CELLS:
        raise ValueError(f"cell {k} is not in 0..{N_CELLS - 1}")
    red = design()["reduced"] if reduced is None else bool(reduced)
    n_held = WILDCHAT_N_WEEKS - WILDCHAT_N_FIT
    h = int(round(k * (n_held - 1) / (N_CELLS - 1)))
    s = k // 3
    ev = {o: XI_HELD[(5 * k + i + s) % len(XI_HELD)] for i, o in enumerate(REGIONS)}
    return {"k": k, "c": REDUCED_SEED if red else CONF_SEEDS[k], "wildchat_week": WILDCHAT_N_FIT + h,
            "wildchat_held_out_position": h, "spot_offset": SPOT_CALIB[1] + k * SPOT_BLOCK_STRIDE,
            "xi_eval": {o: list(v) for o, v in ev.items()}, "xi_fit": {o: list(fit_week(*v)) for o, v in ev.items()}}


def cell_config(part: str, arm: str, k: int, *, gamma: Optional[float] = None) -> dict:
    """The resolved instance config of (fold, arm, cell): bench_e7f.json with ms4_common.e7_spec's overrides (the
    horizon of design(), mu 1) resolved at the cell's config seed (load_config: the confirmation week's draws), then
    every MaaS lender at the fold's offset and every spot pool at the cell's block, calib_slots for the oos arm, and
    the borrowers of the module docstring (wildchat_model 'a4c_fit', p_o_week, xi_sources, demand_fit and, given, the
    pinned gamma). The xi offsets start each BurstGPT week smoothing_min - 1 minutes in, so the smoothing lead-in
    reads the week's first minutes; the fit period is the whole fit week, lead-in included, aligned to WildChat's
    Monday 00:00 (start minute smoothing_min - 1, horizon 10080 - (smoothing_min - 1) minutes: its minutes with the
    lead-in are the minutes 0-10079 of the week and of p_o). The result is a valid config that resolves to itself
    (config.py), the run specs' inline instance."""
    from ..config import load_config
    from ..drivers import run as drun
    from ..traces import lenders as tl
    if part not in FOLDS or arm not in ARMS:
        raise ValueError(f"cell_config: fold {part!r} or arm {arm!r} unknown ({list(FOLDS)}, {list(ARMS)})")
    d, ce = design(), cell(k)
    raw = drun.instance_config(m4.e7_spec("BL0a", {}, mu=m5.MU, horizon_min=d["horizon_min"]))
    raw["seed"] = int(ce["c"])
    r = load_config(raw)
    fold = FOLDS[part]
    for e in r["lenders"]:
        if e["kind"] != "trace":
            continue
        if tl.lender_kind(e["series"]) == "maas":
            e["offset"] = int(fold["maas_offset"])
            if arm == "oos":
                e["calib_slots"] = list(fold["maas_calib"])
        else:
            e["offset"] = int(ce["spot_offset"])
            if arm == "oos":
                e["calib_slots"] = list(SPOT_CALIB)
    b = r["borrowers"]
    if b["model"] != "regional" or tuple(r["regions"]["list"]) != REGIONS:
        raise ValueError("cell_config: bench_e7f.json no longer has the regional model on the five a4b regions")
    lead = int(b["smoothing_min"]) - 1
    b["wildchat_model"] = WILDCHAT_MODEL
    b["p_o_week"] = int(ce["wildchat_week"])
    b["xi_sources"] = {o: {"series": s, "offset_min": int(w) * WEEK_MIN + lead} for o, (s, w) in ce["xi_eval"].items()}
    b["demand_fit"] = {"xi_sources": {o: {"series": s, "offset_min": int(w) * WEEK_MIN + lead}
                                      for o, (s, w) in ce["xi_fit"].items()},
                       "horizon_min": WEEK_MIN - lead, "start_minute_of_week": lead}
    if gamma is not None:
        b["gamma"] = float(gamma)
    r["name"] = f"e7o_{part}_{arm}_k{int(k)}"
    return r


def cell_spec(policy_id: str, params, cfg: dict, *, mode: str, c: int, seeds=(0,), name: str = "e7o") -> dict:
    """The validated run spec of one run (drivers.run.load_run_spec): the inline instance `cfg` (cell_config), the
    mode's lender model (ms5b_common.mode_lender_model), engine.check_invariants true (ms4_common.ENGINE), the policy
    and the seeds (config [c], lender 'config', policy `seeds`)."""
    from ..drivers.run import load_run_spec
    return load_run_spec({"schema_version": 1, "name": name, "instance": copy.deepcopy(cfg), "overrides": {},
                          "lender_model": m5.mode_lender_model(mode), "engine": dict(m4.ENGINE),
                          "policy": {"id": policy_id, "params": copy.deepcopy(dict(params or {}))},
                          "seeds": {"config": [int(c)], "lender": "config", "policy": [int(p) for p in seeds]},
                          "bench": None, "out": f"code/sim/out/{EXP}"})


_PIN: dict = {}


def pinned_gamma(part: str, k: int) -> dict:
    """Gamma of (fold, cell) (module docstring): the oos arm's instance built without borrowers.gamma, whose Gamma
    is market tightness x its supply / the fit period's peak overflow (borrowers.demand_fit); both arms then take it
    as borrowers.gamma. {'gamma', 'instance_hash' (of that build), 'supply_gpus', 'note'}; cached per process."""
    from ..instance import build_instance
    key = (part, int(k), design()["reduced"])
    if key not in _PIN:
        inst = build_instance(cell_config(part, "oos", k))
        gs = {float(v["gamma"]) for v in inst.borrower_stats.values()}
        if len(gs) != 1:
            raise RuntimeError(f"pinned_gamma({part}, {k}): borrower_stats hold {sorted(gs)}")
        _PIN[key] = {"gamma": gs.pop(), "arm": "oos", "instance_hash": mc.instance_hash(inst),
                     "supply_gpus": float(sum(s.capacity_gpus for s in inst.sites if s.kind == "layer")),
                     "note": [n for n in inst.notes if "Gamma" in n]}
    return copy.deepcopy(_PIN[key])


# ---------------------------------------------------------------- jobs
def _est(t: str, n_runs: int, hz: int) -> float:
    """A job's estimate: the confirmation's measured job time of the tag per mode (EST_CONF_JOB_S / 7) x n_runs x
    HZ_FACTOR at the 72-h horizon (about 30 CPU-h per fold, oos.md §5), e7h's estimate for a reduced horizon."""
    if hz >= HORIZON_MIN and t in EST_CONF_JOB_S:
        return EST_BUILD_S + EST_CONF_JOB_S[t] / 7.0 * n_runs * HZ_FACTOR * hz / HORIZON_MIN
    return EST_BUILD_S + e7h._est_week(t, n_runs, hz)


def cell_job_id(part: str, arm: str, tag: str, k: int) -> str:
    return job_id(EXP, part, k="cell", arm=arm, tag=tag, cell=int(k))


def jobs(ps=None) -> list:
    """The jobs of the parts `ps` (default: E7O_PART): per fold, cell, arm and tag one job covering every mode."""
    ps = parts() if ps is None else list(ps)
    d = design()
    out = []
    for part in ps:
        for k in d["cells"]:
            for arm in ARMS:
                for t in TAGS:
                    out.append(Job(cell_job_id(part, arm, t, k), "pool",
                                   {"part": part, "kind": "cell", "arm": arm, "tag": t, "cell": int(k),
                                    "c": int(cell(k)["c"]), "modes": list(MODES), "policy_seeds": [0],
                                    "horizon_min": int(d["horizon_min"])},
                                   _est(t, len(MODES), d["horizon_min"])))
    return out


def jobs_all() -> list:
    return jobs(list(PARTS))


# ---------------------------------------------------------------- the gate (D6)
_GATE: dict = {}


def registration_record() -> dict:
    """The gate's facts: HEAD, whether design/ms7/registration.md exists at HEAD and the analysis sha256 it records
    (its line 'e7o_analysis_sha256: <64 hex>'), the sha256 of e7o_analysis.py at HEAD and on disk, the dirty paths
    (ms5b_common.dirty_paths: untracked files under code/sim/out/ do not count)."""
    reg = m5.file_at("HEAD", REGISTRATION)
    m = REG_SHA_RE.search(reg.decode("utf-8", "replace")) if reg is not None else None
    disk = hashlib.sha256(ANALYSIS.read_bytes()).hexdigest() if ANALYSIS.is_file() else None
    return {"head": m5.head_commit(), "registration": REGISTRATION, "registration_at_head": reg is not None,
            "registration_sha256": m5._sha(reg), "analysis_sha256_registered": m.group(1) if m else None,
            "analysis_sha256_head": m5._sha(m5.file_at("HEAD", ANALYSIS_REL)), "analysis_sha256_disk": disk,
            "dirty_paths": m5.dirty_paths()}


def check_registration(rec: Optional[dict] = None) -> tuple:
    """(ok, reason, record): a job of the full design runs only if the registration exists at HEAD, records the
    analysis sha256, which equals the analysis script's at HEAD and on disk, and the tree is clean."""
    rec = dict(rec if rec is not None else registration_record())
    why = []
    if not rec.get("registration_at_head"):
        why.append(f"{REGISTRATION} does not exist at HEAD")
    want = rec.get("analysis_sha256_registered")
    if rec.get("registration_at_head") and want is None:
        why.append(f"{REGISTRATION} records no line 'e7o_analysis_sha256: <64 hex>'")
    for k in ("analysis_sha256_disk", "analysis_sha256_head"):
        if want is not None and rec.get(k) != want:
            why.append(f"{k} {str(rec.get(k))[:12]} differs from the registered {want[:12]}")
    if rec.get("dirty_paths") is None:
        why.append("git cannot tell whether the working tree is clean")
    elif rec["dirty_paths"]:
        why.append(f"the working tree is dirty ({len(rec['dirty_paths'])} paths, e.g. {rec['dirty_paths'][:3]})")
    if why:
        return False, "e7o does not start (design/ms7/plan.md D6): " + "; ".join(why), rec
    return True, "registration at HEAD, clean tree, analysis sha256 as registered", rec


def gate() -> dict:
    """The gate, checked once per process; enforced (RuntimeError when refused) except in reduced runs."""
    if "g" not in _GATE:
        ok, why, rec = check_registration()
        red = design()["reduced"]
        _GATE["g"] = {"kind": "ms7_registration", "ok": ok, "reason": why, "enforced": not red,
                      "registration": rec}
        if red:
            _GATE["g"]["note"] = "reduced run on a development seed: the gate is recorded, not enforced"
    g = _GATE["g"]
    if g["enforced"] and not g["ok"]:
        raise RuntimeError(g["reason"])
    return g


def _meta_run(job: Job) -> dict:
    return {"exp": EXP, "job": job.id, "part": job.params["part"], "spec": SPEC, "git_revision": mc.git_revision(),
            "versions": mc.versions(), "written": mc._now(), "reduced": design()["reduced"], "gate": gate()}


# ---------------------------------------------------------------- run entries
def source_fields(res, inst) -> dict:
    """Per lender source (maas, spot, protected) of one engine run: buffer violation slots (the engine's entries,
    lender.violations), those with a positive attributable deficit, the deficits in GPU-slots, the leases, their
    GPU-hours and their end causes, and reclaims (end cause 'reclaim') and violation cuts ('violation', L-vr)."""
    def empty() -> dict:
        return {"violation_slots": 0, "violation_slots_attributable": 0, "deficit_gpu_slots": 0.0,
                "deficit_attributable_gpu_slots": 0.0, "leases": 0, "lease_gpu_h": 0.0, "ends": {}}
    kind = {lt.lender: lt.kind for lt in inst.lenders}
    site_kind = [kind.get(s.lender, s.kind) for s in inst.sites]
    out = {k: empty() for k in SOURCES}
    for v in res.violations:
        x = out.setdefault(kind.get(v["lender"], "other"), empty())
        att = float(v.get("deficit_attributable", v["deficit"]))
        x["violation_slots"] += 1
        x["violation_slots_attributable"] += int(att > 0)
        x["deficit_gpu_slots"] += float(v["deficit"])
        x["deficit_attributable_gpu_slots"] += att
    for L in res.leases:
        x = out.setdefault(site_kind[L.site], empty())
        x["leases"] += 1
        x["lease_gpu_h"] += L.gpus * (L.end_min - L.start_min) / 60.0
        x["ends"][L.end_cause] = x["ends"].get(L.end_cause, 0) + 1
    for x in out.values():
        x["reclaims"] = int(x["ends"].get("reclaim", 0))
        x["violation_cuts"] = int(x["ends"].get("violation", 0))
        x["ends"] = dict(sorted(x["ends"].items()))
    return out


def sum_sources(blocks: list) -> dict:
    """The sum of several source_fields blocks (the sub-runs of a siloed run)."""
    out: dict = {}
    for b in blocks:
        for k, x in b.items():
            y = out.setdefault(k, {"ends": {}})
            for f, v in x.items():
                if f == "ends":
                    for c, n in v.items():
                        y["ends"][c] = y["ends"].get(c, 0) + int(n)
                else:
                    y[f] = y.get(f, 0) + v
    return out


def instance_facts(inst) -> dict:
    """The calibration of a built instance per trace lender (kind, series, offset, calib_slots, B, b = B / mean slack
    of the calibration window, D_max, v0, offered layers, capacity, offered revocable contracts and their prices),
    the supply by source, Gamma and C0's source (borrower_stats, C55), and the start minute of the week."""
    cs_of = {e["id"]: e.get("calib_slots") for e in inst.config.get("lenders", [])}
    rows, supply = {}, {k: 0.0 for k in SOURCES}
    for lt in inst.lenders:
        sites = [inst.sites[l] for l in lt.site_index]
        cap = float(sum(s.capacity_gpus for s in sites if np.isfinite(s.capacity_gpus)))
        if lt.kind in supply:
            supply[lt.kind] += float(sum(s.capacity_gpus for s in sites if s.kind == "layer"))
        if lt.S_full is None:
            continue
        cs = cs_of.get(lt.lender)
        S = np.asarray(lt.S_full, dtype=np.float64)
        S_cal = S if cs is None else S[int(cs[0]):int(cs[1])]
        rev = sorted({k for s in sites for k in s.menu if not inst.contracts[k].protected})
        pr = [float(inst.price[l, k]) for l in lt.site_index for k in rev if np.isfinite(inst.price[l, k])]
        rows[lt.lender] = {"kind": lt.kind, "series": lt.series, "offset_5min": int(lt.offset_5min),
                           "calib_slots": None if cs is None else [int(x) for x in cs], "B_gpus": float(lt.B_gpus),
                           "b": float(lt.B_gpus / S_cal.mean()) if S_cal.mean() > 0 else None,
                           "D_max_min": int(lt.D_max_lender_min), "v0": int(lt.v0), "n_layers": int(lt.n_layers),
                           "capacity_gpus": cap, "n_revocable_contracts": len(rev),
                           "price_min_usd_per_gpu_h": min(pr) if pr else None,
                           "price_max_usd_per_gpu_h": max(pr) if pr else None}
    st = list((inst.borrower_stats or {}).values())
    return {"lenders": rows, "supply_gpus": supply, "gamma": st[0].get("gamma") if st else None,
            "C0_from": st[0].get("C0_from") if st else None, "start_mow": int(inst.grid.start_mow),
            "gamma_note": [n for n in inst.notes if "Gamma" in n]}


def one_run(spec: dict, name: str, inst, model, ecfg, refs: dict, own, c: int, ps: int, mode: str) -> dict:
    """One run of tag `name` (e7h.one_run's steps; BL2 through ms4_common.siloed_run) as ms5b_common.week_entry's
    (or siloed_week_entry's) entry, plus its lender-source block 'sources' (source_fields; summed over the sub-runs
    of a siloed run)."""
    from ..algos import registry
    from ..drivers.run import driver_inputs, make_policy
    from ..engine import simulate
    pid, params = spec["policy"]["id"], dict(spec["policy"]["params"] or {})
    t0 = time.perf_counter()
    if registry.entry(pid).runner == "siloed":
        d = m4.siloed_run(inst, spec, model, ecfg, c, ps)
        e = m5.siloed_week_entry(d, inst, model, refs, own, tag_name=name, spec=spec, ps=ps, c=c, mode=mode,
                                 wall_s=time.perf_counter() - t0)
        e["sources"] = sum_sources([source_fields(r, s) for r, s in zip(d["results"], d["instances"])])
        return e
    _, imeta = driver_inputs(pid, params, inst)
    pol = make_policy(spec, inst)
    res = simulate(inst, pol, model, ecfg, lender_seed=int(c), policy_seed=int(ps))
    e = m5.week_entry(res, inst, model, refs, own, tag_name=name, spec=spec, pol=pol, ps=ps, c=c, mode=mode,
                      wall_s=time.perf_counter() - t0, imeta=imeta)
    e["sources"] = source_fields(res, inst)
    return e


def run_cell(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One job: tag p['tag'] on (fold, arm, cell) under every mode of p['modes'], the instance built once with the
    pinned Gamma."""
    from ..drivers import run as drun
    from ..lender import resolve_params
    p = job.params
    part, arm, k, name = p["part"], p["arm"], int(p["cell"]), p["tag"]
    c, seeds = int(p["c"]), [int(s) for s in p["policy_seeds"]]
    meta = _meta_run(job)
    t0 = time.perf_counter()
    pin = pinned_gamma(part, k)
    cfg = cell_config(part, arm, k, gamma=pin["gamma"])
    inst, _, ecfg = drun.build(cell_spec("BL0a", {}, cfg, mode=m5.TRACE_MODE, c=c, seeds=seeds, name="e7o_build"), c)
    if not ecfg.check_invariants:
        raise RuntimeError("E7o runs need check_invariants=True")
    refs, own = m4.references(inst), e7._own(inst)
    params = m5.tag_params(name, inst)
    errors, rows, models = [], [], {}
    for mode in p["modes"]:
        spec = cell_spec(m5.tag(name).id, params, cfg, mode=mode, c=c, seeds=seeds, name=f"e7o_{part}_{arm}_{name}")
        model = drun._lender_model(spec, inst)
        models[mode] = {**e7._lender_dict(model), "resolved": resolve_params(inst, model)}
        for ps in seeds:
            e = mc.try_run(errors, f"{name} {arm} k{k} {mode} p{ps}", one_run, spec, name, inst, model, ecfg, refs,
                           own, c, ps, mode)
            if e is not None:
                e.update(fold=part, arm=arm, cell=k)
                rows.append(e)
                src = e.get("sources") or {}
                print(f"[e7o] {part} {arm} k{k} {name} {mode} p{ps}: ALG {e['ALG']:.4f} USD, r0 {e.get('r0')}, "
                      f"status {e.get('status')}, reclaims maas {(src.get('maas') or {}).get('reclaims')} spot "
                      f"{(src.get('spot') or {}).get('reclaims')}, violation slots maas "
                      f"{(src.get('maas') or {}).get('violation_slots')}, {e.get('wall_s', 0.0):.1f} s", flush=True)
    rec = {"meta": meta, "part": part, "kind": "cell", "arm": arm, "cell": cell(k), "tag": name,
           "tags": m5.tag_table([name]), "params": params, "c": c, "modes": list(p["modes"]), "policy_seeds": seeds,
           "horizon_min": int(p["horizon_min"]), "pinned_gamma": pin, "instance_hash": mc.instance_hash(inst),
           "instance": {"sizes": e7.instance_sizes(inst), "references": refs, "own_capacity_usd": own,
                        "facts": instance_facts(inst)},
           "lender_models": models, "wall_s": time.perf_counter() - t0, "runs": rows, "errors": e7h._errs(errors)}
    outputs.dump(e7._jsonish(rec), run_path(out, job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": rec["instance_hash"], "gamma": pin["gamma"],
            "r0": [[r["mode"], r["policy_seed"], r.get("r0")] for r in rows]}


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    gate()
    if job.params.get("kind") != "cell":
        raise ValueError(f"e7o: unknown job kind {job.params.get('kind')!r}")
    return run_cell(job, outputs, out)


# ---------------------------------------------------------------- summaries
def cell_key(k: int) -> str:
    return f"k{int(k)}"


def expected_runs(job: Job) -> list:
    p = job.params
    return [(p["arm"], p["tag"], m, int(p["cell"]), int(s)) for m in p["modes"] for s in p["policy_seeds"]]


def _src_brief(src: Optional[dict]) -> Optional[dict]:
    if not src:
        return None
    return {k: {f: x.get(f) for f in ("violation_slots", "violation_slots_attributable", "reclaims", "violation_cuts",
                                      "leases", "lease_gpu_h")} for k, x in src.items()}


def brief(e: dict, job: Job) -> dict:
    """One run's row in a summary: fold, arm, cell, tag, mode, seed, r0, ALG, BL0a, the status of the missing-run
    rule, fallback and stranding totals, the leases, the lender sources, the guard facts and A9's counts."""
    p = job.params
    row = {"job": job.id, "fold": p["part"], "arm": p["arm"], "cell": int(p["cell"]), "c": int(p["c"]),
           "tag": e["tag"], "mode": e.get("mode"), "seed": int(e.get("policy_seed", 0)),
           "status": e.get("status") or m5.run_status(e), "r0": e.get("r0"), "ALG": e.get("ALG"),
           "bl0a_usd": e.get("bl0a_usd"), "fallback_usd": e.get("fallback_usd"),
           "stranding_usd": e.get("stranding_usd"), "fallback_share": e.get("fallback_share"),
           "n_leases": e.get("n_leases"), "n_invariant_failures": e.get("n_invariant_failures"),
           "sources": _src_brief(e.get("sources"))}
    g = e7h.guard_brief(e.get("a8"))
    if g is not None:
        row["guard"] = g
    a9 = e7h._a9_brief(e.get("a9"))
    if a9 is not None:
        row["a9"] = a9
    return row


def part_outputs(out_p: Path, js: list) -> tuple:
    """({job id: run file} of the jobs whose record says 'ok', {job id: status} of the others, ignored outputs)."""
    recs = mc.read_records(out_p)
    files, not_ok, ignored = {}, {}, []
    for j in js:
        rec = recs.get(j.id) or {}
        path = run_path(out_p, j.id)
        if rec.get("status") != "ok":
            not_ok[j.id] = rec.get("status") or "no record"
            if path.is_file():
                ignored.append({"job": j.id, "status": rec.get("status"), "output": f"runs/{path.name}"})
            continue
        d = mc.read_json(path)
        if d is None:
            not_ok[j.id] = "ok record without a readable output"
            continue
        files[j.id] = d
    return files, not_ok, ignored


def collect(out_p: Path, js: list) -> dict:
    """The rows of a part (brief), the missing runs of the expected grid with their reason, the table {arm: {tag:
    {mode: {cell: r0 or null}}}} (null: missing or failed, the missing-run rule), the guarded runs, the instances
    {arm: {cell: facts, with n_instance_hashes, 1 when every tag ran on the same instance}} and the pinned Gammas
    per cell (one value when every job of the cell pinned the same)."""
    files, not_ok, ignored = part_outputs(out_p, js)
    by_id = {j.id: j for j in js}
    rows, guarded, have, insts, pins = [], [], {}, {}, {}
    hashes: dict = {}
    for jid, f in files.items():
        j = by_id[jid]
        p = j.params
        insts.setdefault(p["arm"], {}).setdefault(cell_key(p["cell"]), {
            "instance_hash": f.get("instance_hash"), "references": (f.get("instance") or {}).get("references"),
            "facts": (f.get("instance") or {}).get("facts"), "cell": f.get("cell")})
        hashes.setdefault((p["arm"], cell_key(p["cell"])), set()).add(f.get("instance_hash"))
        g = (f.get("pinned_gamma") or {}).get("gamma")
        pins.setdefault(cell_key(p["cell"]), set()).add(None if g is None else float(g))
        for e in f.get("runs") or []:
            r = brief(e, j)
            rows.append(r)
            have[(r["arm"], r["tag"], r["mode"], r["cell"], r["seed"])] = r
            if r.get("guard"):
                guarded.append({k: r[k] for k in ("job", "arm", "cell", "tag", "mode", "seed")} | r["guard"])
    for (arm, ck), hs in hashes.items():       # every tag of an (arm, cell) runs on the same instance
        insts[arm][ck]["n_instance_hashes"] = len(hs)
    pins = {ck: sorted(v, key=lambda x: (x is None, x)) for ck, v in pins.items()}    # one Gamma per cell
    missing, table = [], {}
    for j in js:
        errs = [e.get("error") for e in (files.get(j.id) or {}).get("errors") or []]
        for key in expected_runs(j):
            arm, t, m, k, s = key
            r = have.get(key)
            ok = r is not None and r["status"] == "ok"
            table.setdefault(arm, {}).setdefault(t, {}).setdefault(m, {})[cell_key(k)] = r["r0"] if ok else None
            if not ok:
                why = r["status"] if r is not None else (not_ok.get(j.id) or (errs[0] if errs else None)
                                                         or "run missing")
                missing.append({"job": j.id, "arm": arm, "tag": t, "mode": m, "cell": k, "seed": s, "why": why})
    return {"files": files, "not_ok": not_ok, "ignored": ignored, "rows": rows, "table": table, "missing": missing,
            "guarded": guarded, "instances": insts, "pinned_gamma": pins}


def w0_table(table: dict) -> dict:
    """{arm: {tag: {cell: W0 or null}}}: the largest r0 over the five stress modes (null while one is missing)."""
    out = {}
    for arm, by_t in table.items():
        for t, by_m in by_t.items():
            cells = sorted({c for v in by_m.values() for c in v}, key=lambda x: int(x[1:]))
            for c in cells:
                w, _m, _miss = m5.w0_of({m: (by_m.get(m) or {}).get(c) for m in m5.stress_modes()})
                out.setdefault(arm, {}).setdefault(t, {})[c] = w
    return out


def _meta(part: str, js: list, col: dict) -> dict:
    d = design()
    ok, why, rec = check_registration()
    m = {"exp": EXP, "part": part, "spec": SPEC, "git_revision": mc.git_revision(), "versions": mc.versions(),
         "written": mc._now(), "reduced": d["reduced"], "design": d, "fold": FOLDS[part],
         "cells": [cell(k) for k in d["cells"]], "tags": m5.tag_table(TAGS), "jobs": len(js),
         "jobs_ok": len(col["files"]), "jobs_not_ok": col["not_ok"], "ignored_outputs": col["ignored"],
         "n_runs": len(col["rows"]), "n_missing": len(col["missing"]),
         "gate": {"kind": "ms7_registration", "ok": ok, "reason": why, "registration": rec}}
    if d["reduced"]:
        m["reduced_note"] = (f"reduced job list ({REDUCED_ENV}=1): cell 0 at development seed {REDUCED_SEED}; "
                             "not a result")
    return m


def summary_part(part: str, out_p: Path) -> dict:
    out_p = Path(out_p)
    js = [j for j in jobs_all() if j.params["part"] == part]
    col = collect(out_p, js)
    rc = {arm: m5.rc_rows([{**r, "config_seed": r["cell"], "policy_seed": r["seed"]} for r in col["rows"]
                           if r["arm"] == arm]) for arm in ARMS}
    s = {"meta": _meta(part, js, col), "runs": col["rows"], "table": col["table"], "W0": w0_table(col["table"]),
         "RC": rc, "instances": col["instances"], "pinned_gamma": col["pinned_gamma"], "missing": col["missing"],
         "guarded": col["guarded"], "guard_summary": e7h.guard_summary(col["guarded"])}
    mc.dump_json(e7._jsonish(s), out_p / "summary.json")
    mc.write_text(tables(s), out_p / "tables.md")
    return s


def tables(s: dict) -> str:
    """tables.md: r0 per tag, mode and cell for each arm, the missing runs and the guard counts."""
    m = s["meta"]
    lines = [f"# E7o part {m['part']} ({SPEC})", ""]
    if m.get("reduced"):
        lines += [f"Reduced run: {m.get('reduced_note')}", ""]
    for arm in ARMS:
        by_t = s["table"].get(arm) or {}
        cells = sorted({c for by_m in by_t.values() for v in by_m.values() for c in v}, key=lambda x: int(x[1:]))
        rows = [[t, md] + [(by_t[t].get(md) or {}).get(c) for c in cells] for t in TAGS if t in by_t for md in MODES]
        lines += [f"## r0 (cost over BL0a), arm {arm}", "", mc.md_table(["tag", "mode"] + cells, rows), ""]
    lines += ["## Missing runs (the missing-run rule)", "",
              mc.md_table(["job", "arm", "tag", "mode", "cell", "why"],
                          [[x["job"], x["arm"], x["tag"], x["mode"], x["cell"], x["why"]] for x in s["missing"]]), ""]
    g = s["guard_summary"]
    lines += ["## Guarded runs", "", mc.md_table(["runs", "held", "envelope violations", "aborts", "projected slots"],
                                                 [[g["n_runs"], g["held"], g["n_envelope_violations"], g["aborts"],
                                                   g["projected_slots"]]]), ""]
    return "\n".join(lines) + "\n"


def summary(out) -> dict:
    """The summary of the part whose folder `out` is (its name), else of the one part of E7O_PART."""
    out = Path(out)
    part = out.name if out.name in PARTS else None
    if part is None:
        ps = parts()
        if len(ps) != 1:
            raise ValueError(f"--summary needs one part (E7O_PART) or a part's folder, got {out}")
        part = ps[0]
    return summary_part(part, out)


def manifest_extra(out) -> dict:
    """The design, the instance hashes the run files record and the sha256 of the driver, the shared layers and the
    analysis script."""
    out = Path(out)
    part = out.name if out.name in PARTS else (parts()[0] if len(parts()) == 1 else None)
    js = [j for j in jobs_all() if part is None or j.params["part"] == part]
    hashes = {}
    for j in js:
        f = mc.read_json(run_path(out, j.id))
        if isinstance(f, dict):
            hashes[j.id] = f.get("instance_hash")
    files = [Path(__file__), Path(m5.__file__), Path(e7h.__file__), ANALYSIS]
    ok, why, rec = check_registration()
    return {"part": part, "design": design(), "instance_hashes_from_outputs": hashes,
            "sources_sha256": {str(f.relative_to(paths.REPO)): (hashlib.sha256(f.read_bytes()).hexdigest()
                                                                 if f.is_file() else None) for f in files},
            "gate": {"kind": "ms7_registration", "ok": ok, "reason": why, "registration": rec}}


def retry_list(out) -> list:
    """The pool jobs of the part to run once more (the missing-run rule, design/sublet_v2.md §4.5, as
    e7h.retry_list): a record not 'ok', or 'ok' with a run that raised or failed an invariant; each one's record is
    moved to retry/ and its output to runs/retry/ first, and a job with a record in retry/ is not listed again."""
    out = Path(out)
    part = out.name if out.name in PARTS else parts()[0]
    lines = []
    for j in [j for j in jobs_all() if j.params["part"] == part]:
        name = mc.job_file_name(j.id)
        old = out / "retry" / name
        if old.is_file():
            continue
        rec = mc.read_record(out, j.id)
        if rec is None:
            continue
        path = run_path(out, j.id)
        bad = rec.get("status") != "ok" or int(rec.get("n_errors") or 0) > 0
        if not bad:
            f = mc.read_json(path) or {}
            bad = any(m5.run_status(e) == "invariant_failure" for e in f.get("runs") or [])
        if not bad:
            continue
        old.parent.mkdir(parents=True, exist_ok=True)
        mc.dump_json({"job": j.id, "first_record": rec, "moved": mc._now(), "rule": "design/sublet_v2.md §4.5"}, old)
        if mc.record_path(out, j.id).is_file():
            mc.record_path(out, j.id).unlink()
        if path.is_file():
            keep = out / "runs" / "retry" / name
            keep.parent.mkdir(parents=True, exist_ok=True)
            path.rename(keep)
        lines.append(f"{j.kind} {j.id}")
    return lines


# ---------------------------------------------------------------- command line
def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check-start" in args:
        try:
            g = gate()
            print(f"[e7o] gate {g['kind']} {'ok' if g['ok'] else 'REFUSED (not enforced)'}: {g['reason']}")
            return 0
        except RuntimeError as err:
            print(f"[e7o] REFUSED: {err}", file=sys.stderr)
            return 1
    if "--retry-list" in args:
        ap = argparse.ArgumentParser(prog="python -m sublet.experiments.e7o --retry-list")
        ap.add_argument("--retry-list", action="store_true", required=True)
        ap.add_argument("--out", type=Path, required=True)
        a = ap.parse_args(args)
        for ln in retry_list(a.out):
            print(ln)
        return 0
    if "--out" not in args and any(x in args for x in ("--job", "--summary", "--manifest")):
        ps = parts()
        if len(ps) == 1:
            args += ["--out", str(part_dir(ps[0]))]
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=args, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
