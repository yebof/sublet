"""E3: shared replicas (design/sim_spec_ms4.md §4; deliverable D32, unit U21; open choices M4-M9, M28, M36, M41).

E3 measures how much of the sharing factor b of C3-P7 survives on trace demand: b co-located borrowers of one LLM
(tier M) are planned on one shared (merged) instance or per borrower (siloed, Q41(a)) on E1's lenders, and every
run is bounded from below by the shared OPT(sigma, omega) (Q39's rule, ms3_common.lb_record), with the bracket of
siloed OPT / shared OPT (ms3_common.bracket over ms4_common.sum_bench of the per-borrower MILPs, §2.5, §4.6).

Status labels (copied from design/sim_spec_ms4.md §4.1, never upgraded): C3-P7 PROVEN (elementary; numerically
checked, c3/out/c4_lower.txt (d)): per-borrower planning has ratio at least b even offline, attained exactly on the
constructed always-on instance; the siloed optimum is at most b times the shared one (the copy argument of design
§5.5 E3), so a bracket whose lower end exceeds b is a bug (E3-1). The informal min(b, kappa) of the remark after
C3-P7 needs a per-replica client cap, which the simulator does not model (M41, below), so E3 does not test it. Trace
instances leave the core, so the policies' ratios are diagnostics. Sublet's allowance (M36, §3.3): every A8 run and
every Sublet-siloed sub-run takes ms4_common.sublet_params of its own (sub-)instance (gamma 1, kappa None, B0 =
ms4_common.B0_SHARE x BL0a); Theorem W(a)(b) (PROVEN for the engine as implemented under C1-C3, audited) gives
ALG(T) <= C_S(T) + B0 without an abort and with an abort after which S follows FB; G3(b)'s ratio does not apply (G3(d),
G6); W(c) is CONJECTURE and is counted (E3-5).

Instance (§4.3, M5, M6; the overrides of code/sim/out/ms4spec/e3_sizing.py): configs/bench_e1.json (E1's 4 trace
lenders x 2 layer sites + protected) with E1's slow-grid menu (e1.MENU: s5_tau5_H60, s5_tau60_H0, protected,
time.fast_slot_min 5), one day, regions.list ["europe"] with no adjacency (co-located borrowers), llms [M],
units.per_replica u, stranding.mu_over_beta_tilde mu, the trace lender (I1, 'sell', violations absorbed), invariant
checks on, Q40(a)'s random site order and unmerged layers; borrowers model 'series' with the first b of the fixed
order of the 64 M-tier week slices (m_slices: azure2024_conv and azure2024_code, then the six BurstGPT ChatGPT splits
round-robin by whole week), own capacity P75, smoothing 15 min, market tightness 0.5, normalize 'mean' (C24, M7:
every borrower's overflow scaled to mean 1 before Gamma), merge true (shared: one merged client) or false (siloed: one
client per borrower; a borrower without overflow on the day is dropped by the builder and kept in the list, E3-6).
Config seed = lender seed = alignment c; policy seed p. Under 'trace' with 'absorb' every run of an alignment has the
lender's static schedule (Lender.static_schedule), the realized schedule of the benchmark.

Tags (§4.5; registry id, parameters; style key):
  Sublet          A8 ms4_common.sublet_params(inst) (inner BL5)                           sublet
  A6              A6 {}                                                                   a6
  BL5             BL5 {}                                                                  bl5
  Sublet-siloed   SILOED {inner A8}, each sub-run ms4_common.sublet_params(sub)          sublet_siloed
  A6-siloed       SILOED {inner A6}                                                       a6_siloed
  BL2             BL2 {} (runner 'siloed')                                                bl2
The siloed tags run through ms4_common.siloed_run on the merge-false instance (drivers.siloed.run_siloed with the
sub-instances restrict_clients(inst, idx_b), the same seeds in every sub-run, the costs summed), so that each
Sublet-siloed sub-run has its own B0 and certificate (M28).

Jobs (§4.4, §4.7; ids by ms3_common.job_id, numbers as num_key: "1", "0.2", "16"):
  pool  e3:cell:b=B:u=U:mu=M:c=C              the 18 runs of one cell (6 tags x 3 policy seeds), the shared LP and
                                              every sub-instance's LP, the certificates, the cell record
                                              runs/cells/<job>.json with the realized schedule's hash
  milp  e3:milp:b=B:u=U:mu=M:c=C:part=shared  the shared OPT(sigma, omega) of the cell
  milp  e3:milp:b=B:u=U:mu=M:c=C:part=b<ii>   borrower b<ii>'s OPT on its sub-instance (a no-op with OPT 0 if the
                                              borrower has no client on the day; at b = 1 the job of b00 copies the
                                              shared record when the two instance hashes agree, E3-2, and fails
                                              unless the shared job is 'ok', so that a resume runs it again)
  pool  e3:gate                               the gate of §1.2 item 6 and §4.4 on the cell (b, u, mu, c) =
                                              (8, 8, 1, 1): gate.json
A MILP job rebuilds the instance from the cell's resolved overrides, checks q44_study.instance_hash and
schedule_hash against the cell record before solving, records opt.milp.estimate_size, and solves with
time_limit_s = ms3_common.milp_limit_s() (300 s, M9) and mip_rel_gap 1e-4 on the slow grid; a MILP above the S36 gate
(opt.milp.solve_opt's default max_vars and MEM_BUDGET_MB) is not solved and records status 'size_gate' (the LP is the
LB). run_e3.sh --gate runs the cell job, the 9 MILP jobs and e3:gate of the gate cell in three filtered passes; the
full run_e3.sh (MS3_RESUME=1, refused unless gate.json records the grid's config hash and the current MILP limit,
--check-gate) runs the cell jobs, every MILP job except the part=b00 jobs at b = 1, then those, then the summary. The
summary takes the b00 part at b = 1 from the shared record (the same model, E3-2) and lists a b00 record that is not
a current copy of it under milp.stale_copies.

units.per_replica u is read by the policies that plan in client units of 1/u replica load (instance.units: A2, A5,
A6, the reclaim handler, algos.common, and the driver's a-priori N of A8), not by the engine, the lender or opt.milp:
it is the policies' unit discretization of demand, not a cap on the clients one replica serves. The benchmarks, BL5
and BL2 are the same at every u (only the instance hash differs), the U21 smoke and review runs found Sublet's and
Sublet-siloed's the same too (not in out/), and only A6 and A6-siloed change, so E3 runs at u = 8 only (M41, §4.1,
§4.3); u stays a level of every job id and summary key.

Grid (§4.7, M8, M41): b in {1, 2, 4, 8, 16, 32} at u = 8 x alignments c in {1, 2, 3, 4} x policy seeds {0, 1, 2} at
mu / beta~ = 1, and the default point b = 8, u = 8 at mu / beta~ in {0.2, 0.5, 2}: 36 cells, 36 shared and 348
per-borrower MILP jobs (at most 384 MILPs), 324 shared and 324 siloed runs (at most 3,132 sub-runs).

Reduced job list (smoke runs and tests): MS3_E3_REDUCED=1 (run_e3.sh --reduced sets it) uses b in {1, 8}, u = 8, the
mu point 2 only, alignment 1, policy seed 0 and the 2-h window of slow slots [156, 180) (13:00-15:00, where the first
day's demand starts; instance.restrict_horizon after the build, as e3_sizing.py --smoke), with MS3_MILP_LIMIT 30 s
unless set: 3 cells, 20 MILP jobs and the gate; never a result (meta.reduced true). Default (unset or 0): the full
lists above.

Outputs under out/e3/ (§4.8, §2.6): runs/cells/<job>.json (not versioned), lb/<job>.json (versioned: one record per
MILP job with the fields of e1._solve_record, the time limit, the instance and schedule hashes and the size estimate)
and lb/e3__lp__b__B__u__U__mu__M__c__C__part__P.json (one per LP, the same fields; written by the cell job), gate.json,
summary.json, tables.md, manifest.json, jobs/, logs/, run_e3.log.

summary.json (<b> in {"1", "2", "4", "8", "16", "32"}, <u> in {"8"}, <mu> in {"1"} for every (b, u) and {"0.2",
"0.5", "1", "2"} at (8, 8), <c> in {"1", ..., "4"}, <tag> the six tags; every path of the design grid is present, a
value the runs did not produce is null with a '<key>_note'):
  meta                     exp, git_revision, written, reduced (reduced_note), grid {b, u, mu_main, mu_sweep,
                           default_point, alignments, alignments_design, policy_seeds, policy_seeds_design,
                           horizon, cells_found}, config, overrides_template (the shared overrides at b = 1, u = 8),
                           slices (the 64 [series, week_index]), normalize, B0_rule, B0_share, milp {limit_s,
                           mip_rel_gap, grid}, tags {tag: {policy_id, params, mode, style_key, info_class_reported}},
                           references.<b>.<u>.<mu>.<c> (ms4_common.references of the shared instance: BL0a, own
                           capacity, BL0b in both accountings, the committed price), ignored_outputs
  ratios.<b>.<u>.<mu>.<tag>
                           n_runs, n_ratio, n (= n_ratio), ratio_LB and ratio_inc (metrics.aggregate over the runs of
                           the 4 alignments x 3 seeds: n, median, p95, max, median_ci95), the flat copies median,
                           median_ci95, p95, max (of ratio_LB) and inc_median (median of ratio_inc) that Fig. 4(c),
                           sf_e3_util and sf_e3_mu draw, share_exact (shared MILP gap <= 1e-4), max_gap,
                           alg_mean, lp_only (runs whose shared MILP has no result, so LB = LP) and open (lp_only > 0,
                           or no run in the outputs, with open_note)
  opt.<b>.<u>.<mu>         by_alignment.<c> (bracket of siloed OPT / shared OPT: point, lo, hi, exact, gap_siloed,
                           gap_shared, open, missing (no cell), shared and siloed {LB, LB_source, incumbent, gap,
                           exact, ...}, n_borrowers, n_empty), point_median (median of the points), lo_min, hi_max,
                           exact (every bracket of the cells found exact), open (a bracket of the cells found without
                           a point, or whose shared MILP has no result: drawn against the LP alone; or no cell in the
                           outputs, with open_note), n_alignments (brackets with a point), n_cells, lb_source {shared:
                           {source: n}, siloed: {source: n}}
  util.<b>.<u>.<mu>.<tag>  n, replica_utilization and loads_per_day (metrics.aggregate; a siloed run's served and
                           capacity load-minutes and loads summed over its sub-runs)
  cost_over_bl0a.<b>.<u>.<mu>.<tag>
                           n, the medians over the runs of overflow_usd, total_usd, overflow_over_bl0a,
                           total_over_bl0a, own_share_of_total, overflow_over_bl0b, total_over_bl0b
                           (ms4_common.accountings; BL0a and BL0b of the shared instance) and median_ci95
                           {overflow_over_bl0a, total_over_bl0a}
  borrowers.<b>.<u>        at mu = 1: day (0: the series borrowers read the first day of their week slices),
                           by_alignment.<c> {kept, dropped, shares (each borrower's share of the day's overflow in
                           replica-load-hours), C0_loads, peak_loads, normalize_factor}, n_kept and n_dropped per
                           alignment (null with '<c>_note' where the alignment has no mu = 1 cell)
  certificates             shared, siloed_sub_runs and all (ms4_common.count_certificates: n, held, by_case
                           {W(a), W(b), W(c), unavailable: {runs, held}}, failures), failures (briefs of the runs of
                           Theorem W's proven cases whose certificate is not held), w_c_runs (briefs), aborts.<b>.<u>.
                           <mu> {shared {runs, aborted}, sub_runs {runs, aborted}}
  milp                     counts {shared, siloed: {status: n}} (statuses 0, 1, 'wall_limit', 'oom_at_3G', 'error',
                           'failed', 'running', 'missing', 'stale', 'size_gate', 'empty', and 'copied' for the b00 parts
                           at b = 1), max_gap, wall_limit_kills, oom_kills, size_gate and stale (copies left out),
                           copied (the b00 parts at b = 1, taken from the shared record), stale_copies (b00 jobs at
                           b = 1 whose own record is not an 'ok' copy of the shared record used: rerun them), stale
                           (records whose instance or schedule hash differs from the cell's: not used), stale_lp_cells,
                           limit_mismatch (LP and MILP records whose time_limit_s is not limit_s), n_jobs, limit_s
  checks.E3-1 ... E3-7     status 'pass' | 'fail' | 'missing' | 'informative' with the inputs of each check of §4.9;
                           E3-3 recomputes the sums from the stored rows (components and ALG against the sub-runs')
                           next to the cell job's per-slot difference (run_siloed's per-slot sums against its
                           components); E3-7 fails when gate.json's MILP limit is not limit_s
gate.json (§4.4): meta (cell, reduced, horizon, B0_rule, milp_limit_s, git_revision, versions, written), config_hash
  (the grid's, grid_config_hash), cell_config_hashes, instance_hashes {shared, siloed, sub}, schedule_hash, hash_check,
  sizes, gamma_notes, borrowers (own capacity, peak, share of the day's overflow per borrower, the borrowers
  dropped), lp and milp per part (sizes, statuses, gaps, times, time_limit_s; the MILP job's status), bracket (siloed /
  shared OPT), allowance {gamma, B0_rule, shared and sub_runs.<b<ii>> (ms4_common.allowance_need of an A8 run with
  ms4_common.need_params: need_usd, need_over_bl0a, need_slot, bl0a_usd, B0_usd (M36's B0), margin_usd, t_a_at_B0,
  total_usd, n_invariant_failures, wall_s), n_sub_runs, n_sub_abort_at_B0}, runs (the cell's runs per tag: totals, cost
  over BL0a, certificate cases, aborts).

Command line (ms3_common.main, §2.4), run from code/sim:
  python -m sublet.experiments.e3 --list | --job ID | --summary | --estimate | --manifest  [--out DIR]
  python -m sublet.experiments.e3 --check-gate [--out DIR]   exit 0 iff gate.json exists, the job record of e3:gate
                                                             is 'ok', gate.json records grid_config_hash() and its
                                                             MILP records ran under milp_limit_s()
--estimate uses the constants of §4.7 and §11.1: 1.2 s per shared run (measurement 4's u = 8), 2 s per sub-run, 0.4 s
per LP, MILP limit + 60 s.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import copy
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

from . import ms3_common as mc
from . import ms4_common as m4
from .ms3_common import Job, job_id, num_key, put

EXP = "e3"
CONFIG = "bench_e1.json"
DAY_MIN = 1440
MIN_PER_WEEK = 10080
BS = (1, 2, 4, 8, 16, 32)
US = (8,)                          # M41: units.per_replica is the policies' discretization, no replica cap
MU_MAIN = 1.0
MUS_SWEEP = (0.2, 0.5, 2.0)
DEFAULT_POINT = (8, 8)             # M8: (b, u) of the mu points
GATE_CELL = (8, 8, 1.0, 1)         # §1.2 item 6, §4.4: (b, u, mu, c) of the gate
ALIGNMENTS = (1, 2, 3, 4)          # config seeds = lender seeds
POLICY_SEEDS = (0, 1, 2)
NORMALIZE = "mean"                 # C24, M7
AZURE_M = ("azure2024_conv", "azure2024_code")
BURST_SPLITS = ("burstgpt_1__ChatGPT__conv", "burstgpt_1__ChatGPT__api", "burstgpt_2__ChatGPT__conv",
                "burstgpt_2__ChatGPT__api", "burstgpt_3__ChatGPT__conv", "burstgpt_3__ChatGPT__api")
N_SLICES = 64
LLM_M = {"id": "M", "catalog": "maas_a10", "entry": "M", "kappa_mult": 1.0}
LENDER_MODEL = {"schedule": "trace", "violations": "absorb", "on_unavailable": "sell", "information": "I1"}
# §4.5: tag -> (registry id, parameters, mode, style key); the A8 parameters come from ms4_common.sublet_params of
# the run's own (sub-)instance (M36), never typed here
TAGS = {"Sublet": ("A8", None, "shared", "sublet"),
        "A6": ("A6", {}, "shared", "a6"),
        "BL5": ("BL5", {}, "shared", "bl5"),
        "Sublet-siloed": ("SILOED", {"inner": "A8", "inner_params": {"inner": "BL5"}}, "siloed", "sublet_siloed"),
        "A6-siloed": ("SILOED", {"inner": "A6"}, "siloed", "a6_siloed"),
        "BL2": ("BL2", {}, "siloed", "bl2")}
SHARED_TAGS = ("Sublet", "A6", "BL5")
SILOED_TAGS = ("Sublet-siloed", "A6-siloed", "BL2")
A8_TAGS = ("Sublet", "Sublet-siloed")
PART_RE = re.compile(r"shared|b[0-9]{2}")        # the part of a MILP job: the shared instance or borrower b<ii>
PAIRS_B1 = (("Sublet-siloed", "Sublet"), ("A6-siloed", "A6"))      # E3-2
MILP_GAP = 1e-4
BENCH_GRID = "slow"
TOL = 1e-9
P1_TOL = 1e-6                      # E3-4: Proposition M4
REDUCED_ENV = "MS3_E3_REDUCED"
REDUCED = {"bs": (1, 8), "us": (8,), "mus_sweep": (2.0,), "alignments": (1,), "policy_seeds": (0,),
           "horizon": (156, 24)}   # 2 h of 5-min slots from 13:00 (e3_sizing.py --smoke)
# time constants of §4.7 and §11.1 (seconds; MS4-spec measurement 4 and the bounded check run of measurement 8)
EST_SHARED_RUN_S = 1.2
EST_SUB_RUN_S = 2.0
EST_LP_S = 0.4


# ---------------------------------------------------------------- grid and jobs
def full_design() -> dict:
    """The full grid of §4.7."""
    return {"reduced": False, "bs": BS, "us": US, "mus_sweep": MUS_SWEEP, "alignments": ALIGNMENTS,
            "policy_seeds": POLICY_SEEDS, "horizon": None}


def design() -> dict:
    """The job grid: the full grid of §4.7, or the reduced one with MS3_E3_REDUCED=1 (module docstring)."""
    if os.environ.get(REDUCED_ENV, "0") == "1":
        return {"reduced": True, **REDUCED}
    return full_design()


def grid_cells(d: Optional[dict] = None) -> list[tuple]:
    """(b, u, mu, c) of every cell of the design `d` (default design()): the mu = 1 grid, then the mu points at the
    default point (M8)."""
    d = d or design()
    out = [(b, u, MU_MAIN, c) for b in d["bs"] for u in d["us"] for c in d["alignments"]]
    out += [(DEFAULT_POINT[0], DEFAULT_POINT[1], mu, c) for mu in d["mus_sweep"] for c in d["alignments"]]
    return out


def design_points() -> list[tuple]:
    """(b, u, mu) of the full design grid (the key paths of the summary)."""
    return [(b, u, MU_MAIN) for b in BS for u in US] + [(DEFAULT_POINT[0], DEFAULT_POINT[1], mu) for mu in MUS_SWEEP]


def borrower_ids(b: int) -> list[str]:
    return [f"b{i:02d}" for i in range(int(b))]


def cell_id(b, u, mu, c) -> str:
    return job_id(EXP, "cell", b=int(b), u=int(u), mu=mu, c=int(c))


def _with_part(jid: str, part: str) -> str:
    """jid + ':part=<part>' (job_id's own second argument is named part, so the key is appended here; §4.7 writes
    the MILP ids with the key 'part')."""
    if not PART_RE.fullmatch(str(part)):
        raise ValueError(f"E3 part {part!r} is neither 'shared' nor a borrower id b<ii>")
    out = f"{jid}:part={part}"
    mc.parse_job_id(out)
    return out


def milp_id(b, u, mu, c, part: str) -> str:
    return _with_part(job_id(EXP, "milp", b=int(b), u=int(u), mu=mu, c=int(c)), part)


def lp_id(b, u, mu, c, part: str) -> str:
    """The name of an LP record (not a job: the cell job solves its LPs)."""
    return _with_part(job_id(EXP, "lp", b=int(b), u=int(u), mu=mu, c=int(c)), part)


GATE_ID = job_id(EXP, "gate")


def jobs() -> list[Job]:
    d = design()
    seeds, hz = d["policy_seeds"], d["horizon"]
    milp_s = mc.wall_timeout_s()
    common = {"policy_seeds": list(seeds), "horizon": None if hz is None else list(hz)}
    cells = grid_cells(d)
    out = []
    for (b, u, mu, c) in cells:
        n_run = len(seeds) * (len(SHARED_TAGS) * EST_SHARED_RUN_S + len(SILOED_TAGS) * b * EST_SUB_RUN_S)
        out.append(Job(cell_id(b, u, mu, c), "pool", {"b": b, "u": u, "mu": mu, "c": c, **common},
                       est_s=n_run + (1 + b) * EST_LP_S))
    for (b, u, mu, c) in cells:
        for part in ["shared"] + borrower_ids(b):
            out.append(Job(milp_id(b, u, mu, c, part), "milp", {"b": b, "u": u, "mu": mu, "c": c, "part": part,
                                                                "horizon": common["horizon"]}, est_s=milp_s))
    gb, gu, gmu, gc = GATE_CELL
    out.append(Job(GATE_ID, "pool", {"b": gb, "u": gu, "mu": gmu, "c": gc, "horizon": common["horizon"]},
                   est_s=EST_SHARED_RUN_S + gb * EST_SUB_RUN_S))
    return out


# ---------------------------------------------------------------- paths
def cell_file(out: Path, b, u, mu, c) -> Path:
    return Path(out) / "runs" / "cells" / mc.job_file_name(cell_id(b, u, mu, c))


def lp_file(out: Path, b, u, mu, c, part: str) -> Path:
    return Path(out) / "lb" / mc.job_file_name(lp_id(b, u, mu, c, part))


def milp_file(out: Path, b, u, mu, c, part: str) -> Path:
    return Path(out) / "lb" / mc.job_file_name(milp_id(b, u, mu, c, part))


def gate_file(out: Path) -> Path:
    return Path(out) / "gate.json"


# ---------------------------------------------------------------- borrowers and instances (§4.3, §4.4, M5, M7)
def m_slices() -> list[tuple[str, int]]:
    """The fixed order of the 64 M-tier week slices (§4.4; e3_sizing.py m_slices): Azure 2024 conv and code (one
    week each), then the six BurstGPT ChatGPT conv/api splits round-robin by week index, whole weeks only
    (floor(minutes / 10080) per split: 8, 8 and 15 weeks for files 1, 2 and 3)."""
    from ..traces.borrowers import series_length
    out = [(s, 0) for s in AZURE_M]
    weeks = {s: series_length(s) // MIN_PER_WEEK for s in BURST_SPLITS}
    for w in range(max(weeks.values())):
        for s in BURST_SPLITS:
            if w < weeks[s]:
                out.append((s, w))
    return out


def borrower_list(b: int) -> list[dict]:
    """The `borrowers.list` entries of the first b slices: {id b<ii>, series, week_index, tier M, region europe}."""
    sl = m_slices()
    if not 1 <= int(b) <= len(sl):
        raise ValueError(f"b = {b} is not in [1, {len(sl)}] (the M-tier week slices)")
    return [{"id": bid, "series": s, "week_index": int(w), "tier": "M", "region": "europe"}
            for bid, (s, w) in zip(borrower_ids(b), sl[:b])]


def overrides(b: int, u: int, merge: bool, mu: float = MU_MAIN) -> dict:
    """The instance overrides of one cell (§4.3; e3_sizing.py `overrides` plus mu and normalize 'mean')."""
    from .e1 import MENU
    ov = copy.deepcopy(MENU)
    ov.update({"time.horizon_min": DAY_MIN, "regions.list": ["europe"], "regions.adjacency": [],
               "llms": [dict(LLM_M)], "units.per_replica": int(u), "stranding.mu_over_beta_tilde": float(mu),
               "borrowers": {"model": "series", "list": borrower_list(b), "own_capacity_quantile": 75,
                             "smoothing_min": 15, "market_tightness": 0.5, "merge": bool(merge),
                             "normalize": NORMALIZE}})
    return ov


def run_spec(pid: str, params: Optional[dict], ov: dict, c: int, seeds=(0,), name: str = "e3") -> dict:
    """The validated run spec (drivers.run.load_run_spec): bench_e1 with the cell's overrides, the trace lender (I1,
    'sell', 'absorb'), invariant checks on, the policy and the seeds."""
    from ..drivers.run import load_run_spec
    return load_run_spec({"schema_version": 1, "name": name.replace("-", "_"), "instance": CONFIG,
                          "overrides": copy.deepcopy(ov), "lender_model": dict(LENDER_MODEL),
                          "engine": {"check_invariants": True},
                          "policy": {"id": pid, "params": copy.deepcopy(dict(params or {}))},
                          "seeds": {"config": [int(c)], "lender": "config", "policy": [int(p) for p in seeds]},
                          "bench": None, "out": "code/sim/out/e3/runs"})


def build_instance(b: int, u: int, mu: float, c: int, merge: bool, horizon=None):
    """(inst, model, ecfg, ov) of the shared (merge true) or siloed (merge false) instance of a cell; with `horizon`
    [t0, T] the instance is restrict_horizon(inst, t0, T) (reduced runs)."""
    from ..drivers import run as drun
    from ..instance import restrict_horizon
    ov = overrides(b, u, merge, mu)
    inst, model, ecfg = drun.build(run_spec("BL0a", {}, ov, c), int(c))
    if horizon:
        inst = restrict_horizon(inst, int(horizon[0]), int(horizon[1]))
    if not ecfg.check_invariants:
        raise RuntimeError("E3 runs need check_invariants=True (§0 item 5)")
    return inst, model, ecfg, ov


def trace_schedule(inst, model, c: int):
    """The realized schedule of every run on `inst` under 'trace' with 'absorb': the lender's static schedule."""
    from ..config import rng_streams
    from ..lender import Lender
    return Lender(inst, model, rng_streams(int(c))["lender"]).static_schedule()


def sub_instances(inst) -> dict:
    """{borrower id: restrict_clients(inst, idx)} of the siloed instance, in the order of drivers.siloed."""
    from ..drivers.siloed import borrower_partition
    from ..instance import restrict_clients
    return {bid: restrict_clients(inst, idx) for bid, idx in borrower_partition(inst)}


def cell_config_hashes(b: int, u: int, mu: float, c: int) -> dict:
    """config.config_hash of the resolved instance configs (load_config at config seed c) of a cell's shared and
    siloed instances."""
    from .. import config as C
    from ..drivers.run import instance_config
    out = {}
    for key, merge in (("shared", True), ("siloed", False)):
        cfg = instance_config(run_spec("BL0a", {}, overrides(b, u, merge, mu), c))
        cfg["seed"] = int(c)
        out[key] = C.config_hash(C.load_config(cfg))
    return out


def grid_config_hash(d: Optional[dict] = None) -> str:
    """The config hash of the grid's instances (§4.4, E3-7): sha256 over the canonical JSON of the config file's name,
    normalize, the reduced horizon and, per cell of the design `d` (default design()), its id and the config hashes
    of its shared and siloed resolved instance configs (cell_config_hashes, which cover the file's content)."""
    d = d or design()
    rows = []
    for (b, u, mu, c) in grid_cells(d):
        h = cell_config_hashes(b, u, mu, c)
        rows.append([cell_id(b, u, mu, c), h["shared"], h["siloed"]])
    payload = {"config": CONFIG, "normalize": NORMALIZE, "horizon": None if d["horizon"] is None
               else list(d["horizon"]), "cells": rows}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def borrower_block(shared, siloed, b: int) -> dict:
    """The borrowers of a cell (§4.4, §4.8; E3-6): per listed borrower its slice, whether it has a client on the day
    (kept) or was dropped (no overflow), own capacity C0_loads and peak_loads in replica loads after Gamma and the
    normalization (shared instance's borrower_stats), normalize_factor, the demand of its client in replica-load-hours
    and its share of the day's overflow (siloed instance)."""
    lst = borrower_list(b)
    stats = shared.borrower_stats or {}
    fast_h = siloed.grid.fast_min / 60.0
    load_h = {siloed.clients.borrowers[k][0]: float(np.asarray(siloed.clients.demand[k], dtype=np.float64).sum())
              * fast_h for k in range(siloed.n)}
    tot = float(sum(load_h.values()))
    rows = []
    for x in lst:
        st = stats.get(x["id"]) or {}
        kept = x["id"] in load_h
        row = {"id": x["id"], "series": x["series"], "week_index": x["week_index"], "kept": kept,
               "C0_loads": st.get("C0_loads"), "peak_loads": st.get("peak_loads"),
               "normalize_factor": st.get("normalize_factor"), "overflow_load_h": load_h.get(x["id"], 0.0)}
        put(row, "share", load_h.get(x["id"], 0.0) / tot if tot > 0 else None, "no overflow on the horizon")
        rows.append(row)
    kept = [r["id"] for r in rows if r["kept"]]
    return {"list": rows, "kept": kept, "dropped": [r["id"] for r in rows if not r["kept"]], "n_kept": len(kept),
            "n_dropped": len(rows) - len(kept), "total_overflow_load_h": tot,
            "dropped_notes": [n for n in siloed.notes if "no overflow" in n]}


def inst_sizes(inst) -> dict:
    rev = [s for s in inst.sites if s.kind != "protected"]
    return {"sites": inst.m, "revocable_sites": len(rev), "protected_sites": inst.m - len(rev),
            "contracts": [k.id for k in inst.contracts], "lenders": len(inst.lenders),
            "lenders_with_sites": len({s.lender for s in rev}), "clients": inst.n, "T_slow": inst.grid.T_slow,
            "slow_min": inst.grid.slow_min, "fast_min": inst.grid.fast_min,
            "units_per_replica": inst.units_per_replica}


# ---------------------------------------------------------------- small records
def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _rel(p, base) -> str:
    try:
        return str(Path(p).resolve().relative_to(Path(base).resolve()))
    except ValueError:
        return str(p)


def _jsonish(x):
    """metrics._jsonable (non-finite floats as strings) for the free-form parts of the run records."""
    from ..metrics import _jsonable
    return _jsonable(x)


def _est_brief(est: dict) -> dict:
    return {"n_vars": int(est["n_vars"]), "n_int": int(est["n_int"]), "n_rows": int(est["n_rows"]),
            "nnz": int(est["nnz"]), "est_mb_milp": float(est["est_mb"]), "est_mb_lp": float(est["parts"]["est_mb_lp"])}


def _gate_record(err, est: dict, method: str, **extra) -> dict:
    """A record in the fields of e1._solve_record for a model that opt.milp's S36 gate refuses (status
    'size_gate'): not solved; for a MILP the LP stays the LB (§4.6)."""
    return {**extra, "method": method, "benchmark": "omega", "grid": BENCH_GRID, "status": "size_gate",
            "status_msg": f"not solved: {type(err).__name__}: {err}", "objective": None, "dual_bound": None,
            "gap": None, "size": {k: est.get(k) for k in ("n_vars", "n_int", "n_rows", "nnz")}, "build_s": None,
            "solve_s": None, "peak_rss_mb": None, "git_revision": mc.git_revision()}


def solve_bench(inst, sched, method: str, limit: float, **extra) -> dict:
    """The LP ('lp') or the MILP ('milp') of OPT(sigma, omega) on the slow grid with opt.milp's S36 gate (default
    max_vars and MEM_BUDGET_MB; a refused model gives status 'size_gate'), as a record with the fields of
    e1._solve_record, the size estimate (estimate_size, recorded before the solve), the time limit and `extra`."""
    from ..opt.milp import SizeError, estimate_size, solve_lp, solve_opt
    from .e1 import _solve_record
    t0 = time.perf_counter()
    est = estimate_size(inst, sched, grid=BENCH_GRID)
    fn = solve_lp if method == "lp" else solve_opt
    kw = {} if method == "lp" else {"mip_rel_gap": MILP_GAP}
    try:
        sr = fn(inst, sched, grid=BENCH_GRID, time_limit_s=float(limit), return_plan=False, **kw)
    except SizeError as err:
        rec = _gate_record(err, est, method, **extra)
    else:
        rec = _solve_record(sr, **extra)
    rec.update(time_limit_s=float(limit), mip_rel_gap=MILP_GAP if method == "milp" else None,
               estimate=_est_brief(est), wall_s=time.perf_counter() - t0)
    return rec


def run_row(res, inst, model, refs: Optional[dict] = None) -> dict:
    """The per-run fields of a cell record (§4.8): cost and components, both accountings (with refs), replica
    utilization and loads per day with their sums, the checks of E3-4 and the realized schedule's hash."""
    from ..drivers.run import ratio_validity
    from ..metrics import run_metrics
    from . import q44_study as q44
    rm = run_metrics(res, inst)
    m = res.metrics
    alg = float(res.components["total"])
    row = {"ALG": alg, "components": {k: float(v) for k, v in res.components.items()},
           "grouped": q44.grouped(res.components),
           "replica_utilization": rm["replica_utilization"], "loads_per_day": rm["loads_per_day"],
           "served_load_min": float(m["served_load_min"]), "capacity_load_min": float(m["capacity_load_min"]),
           "loads": float(m["loads"]), "fallback_share": rm["fallback_share"],
           "n_invariant_failures": len(res.invariant_failures),
           "invariant_failures": list(res.invariant_failures)[:10],
           "gpu_only_lease_slots": int(m.get("gpu_only_lease_slots", 0)),
           "ratio_validity": ratio_validity(BENCH_GRID, inst, model),
           "plan_class_p1": bool(q44.plan_class_p1(res, inst)), "schedule_hash": mc.schedule_hash(res.schedule),
           "n_leases": len(res.leases), "engine_wall_s": res.runtime.get("wall_s")}
    if refs is not None:
        row["accountings"] = m4.accountings(alg, inst, refs)
    return row


def _sum_diff(total: dict, parts: list[dict]) -> float:
    """max over the components of |total - the sum of the parts| (E3-3)."""
    keys = set(total) | {k for p in parts for k in p}
    return max((abs(float(total.get(k, 0.0)) - sum(float(p.get(k, 0.0)) for p in parts)) for k in keys),
               default=0.0)


def _per_slot_diff(components: dict, per_slot: dict) -> float:
    """max over the components of |the sum over the slow slots of run_siloed's summed per-slot series - its summed
    component| (E3-3's per-slot side: run_siloed's two accumulators; a key in only one of them counts in full)."""
    keys = set(components) | set(per_slot)
    return max((abs(float(np.sum(per_slot.get(k, 0.0))) - float(components.get(k, 0.0))) for k in keys),
               default=0.0)


# ---------------------------------------------------------------- job: one cell
def run_cell(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """The 18 runs of one cell (§4.7), the shared and the sub-instances' LPs, the certificates and the cell
    record runs/cells/<job>.json."""
    from .. import config as C
    from ..algos import registry
    from ..drivers import run as drun
    from ..engine import simulate
    from . import q44_study as q44
    from .e6 import bl0a_all
    p = job.params
    b, u, mu, c = int(p["b"]), int(p["u"]), float(p["mu"]), int(p["c"])
    hz, seeds = p.get("horizon"), list(p["policy_seeds"])
    t_start = time.perf_counter()
    limit = mc.milp_limit_s()
    sh_inst, model, ecfg, ov_sh = build_instance(b, u, mu, c, True, hz)
    si_inst, _, _, ov_si = build_instance(b, u, mu, c, False, hz)
    subs = sub_instances(si_inst)
    refs = m4.references(sh_inst)
    sched = trace_schedule(sh_inst, model, c)
    sh = mc.schedule_hash(sched)
    sub_sched = {bid: trace_schedule(s, model, c) for bid, s in subs.items()}
    sub_sh = {bid: mc.schedule_hash(s) for bid, s in sub_sched.items()}
    ih = {"shared": mc.instance_hash(sh_inst), "siloed": mc.instance_hash(si_inst),
          "sub": {bid: mc.instance_hash(s) for bid, s in subs.items()}}
    errors: list = []
    lps = {}
    for part, inst_x, sch in [("shared", sh_inst, sched)] + [(bid, subs[bid], sub_sched[bid]) for bid in subs]:
        def one_lp(part=part, inst_x=inst_x, sch=sch):
            rec = solve_bench(inst_x, sch, "lp", limit, job=job.id, kind="lp", part=part,
                              borrower=None if part == "shared" else part, b=b, u=u, mu=mu, c=c,
                              instance_hash=ih["shared"] if part == "shared" else ih["sub"][part],
                              schedule_hash=sh if part == "shared" else sub_sh[part])
            path = lp_file(out, b, u, mu, c, part)
            outputs.dump(rec, path)
            lps[part] = {"file": _rel(path, out), "status": rec["status"], "objective": rec["objective"],
                         "n_vars": rec["size"].get("n_vars"), "solve_s": rec["solve_s"]}
        mc.try_run(errors, f"lp_{part}", one_lp)
    rows = []
    for tag in SHARED_TAGS + SILOED_TAGS:
        pid, params0, mode, skey = TAGS[tag]
        for ps in seeds:
            def one(tag=tag, pid=pid, params0=params0, mode=mode, skey=skey, ps=ps):
                t0 = time.perf_counter()
                if mode == "shared":
                    params = m4.sublet_params(sh_inst) if pid == "A8" else dict(params0)
                    spec = run_spec(pid, params, ov_sh, c, seeds, tag)
                    pol = drun.make_policy(spec, sh_inst)
                    res = simulate(sh_inst, pol, model, ecfg, lender_seed=c, policy_seed=int(ps))
                    rp = {**params, **(pol.params() or {})}
                    row = {"tag": tag, "policy_id": pid, "params": rp, "mode": mode, "style_key": skey, "p": int(ps),
                           "info_class": registry.info_class(pid, rp, model.information),
                           **run_row(res, sh_inst, model, refs)}
                    if pid == "A8":
                        row.update(m4.a8_record(res, sh_inst, params, model.information))
                else:
                    spec = run_spec(pid, params0, ov_si, c, seeds, tag)
                    pof = m4.sublet_params if tag == "Sublet-siloed" else None
                    d = m4.siloed_run(si_inst, spec, model, ecfg, c, int(ps), params_of=pof)
                    sub_rows = []
                    for srow, res_b, sub in zip(d["sub_runs"], d["results"], d["instances"]):
                        sub_rows.append({**srow, **run_row(res_b, sub, model), "bl0a_usd": float(bl0a_all(sub))})
                    served = sum(r["served_load_min"] for r in sub_rows)
                    cap = sum(r["capacity_load_min"] for r in sub_rows)
                    days = si_inst.grid.horizon_min / DAY_MIN
                    total = float(d["total"])
                    rvs = [r["ratio_validity"] for r in sub_rows if r["ratio_validity"] is not None]
                    info = registry.info_class(pid, params0, model.information)
                    row = {"tag": tag, "policy_id": pid, "inner_id": d["inner_id"], "params": dict(params0),
                           "inner_params_of": "ms4_common.sublet_params(sub)" if pof else None, "mode": mode,
                           "style_key": skey, "p": int(ps), "info_class": info,
                           "ALG": total, "components": {k: float(v) for k, v in d["components"].items()},
                           "grouped": q44.grouped(d["components"]),
                           "accountings": m4.accountings(total, sh_inst, refs),
                           "replica_utilization": served / cap if cap > 0 else None,
                           "loads_per_day": sum(r["loads"] for r in sub_rows) / days,
                           "served_load_min": served, "capacity_load_min": cap,
                           "loads": sum(r["loads"] for r in sub_rows),
                           "n_invariant_failures": len(d["invariant_failures"]),
                           "invariant_failures": list(d["invariant_failures"])[:10],
                           "gpu_only_lease_slots": sum(r["gpu_only_lease_slots"] for r in sub_rows),
                           "ratio_validity": rvs[0] if rvs else None,
                           "plan_class_p1": bool(sub_rows) and all(r["plan_class_p1"] for r in sub_rows),
                           "schedule_hashes": sorted({r["schedule_hash"] for r in sub_rows}),
                           "n_sub_runs": len(sub_rows),
                           "components_sum_abs_diff": _sum_diff(d["components"],
                                                                [r["components"] for r in sub_rows]),
                           "per_slot_abs_diff": _per_slot_diff(d["components"], d["per_slot"]),
                           "certificates": d["certificates"], "sub_runs": sub_rows}
                    if tag == "Sublet-siloed":
                        row["info_class_reported"] = m4.info_class_reported(info, m4.B0_RULE)
                        row["B0_rule"] = sorted({r["B0_rule"] for r in sub_rows})
                        row["n_aborted_sub_runs"] = sum(1 for r in sub_rows if r.get("aborted"))
                row["wall_s"] = time.perf_counter() - t0
                rows.append(row)
                print(f"[e3] {job.id} {tag} p{ps}: ALG {row['ALG']:.4f}"
                      + (f", {row['n_sub_runs']} sub-runs" if mode == "siloed" else "")
                      + (f", certificate {row['certificate_case']}" if "certificate_case" in row else "")
                      + f", {row['wall_s']:.2f} s", flush=True)
            mc.try_run(errors, f"{tag}_p{ps}", one)
    mismatch = [{"tag": r["tag"], "p": r["p"], "borrower": s.get("borrower")} for r in rows
                for s in ([r] if r["mode"] == "shared" else r["sub_runs"])
                if s["schedule_hash"] != (sh if r["mode"] == "shared" else sub_sh[s["borrower"]])]
    rec = {"job": job.id, "exp": EXP, "b": b, "u": u, "mu": mu, "c": c, "mu_key": num_key(mu), "config": CONFIG,
           "overrides": {"shared": ov_sh, "siloed": ov_si}, "horizon": hz, "borrower_list": borrower_ids(b),
           "instances": ih, "config_hashes": {"shared": C.config_hash(sh_inst.config),
                                              "siloed": C.config_hash(si_inst.config)},
           "schedule_hash": sh, "sub_schedule_hashes": sub_sh,
           "schedule_mismatch": mismatch, "n_announcements": int(sum(len(r) for r in sched.R)),
           "lender_model": {"schedule": model.schedule, "information": model.information,
                            "on_unavailable": model.on_unavailable, "violations": model.violations},
           "sizes": inst_sizes(sh_inst), "gamma_notes": {"shared": [n for n in sh_inst.notes if "Gamma" in n],
                                                         "siloed": [n for n in si_inst.notes if "Gamma" in n]},
           "borrowers": borrower_block(sh_inst, si_inst, b),
           "bl0a": {"shared": float(bl0a_all(sh_inst)), "siloed": float(bl0a_all(si_inst)),
                    "sub": {bid: float(bl0a_all(s)) for bid, s in subs.items()}},
           "references": refs, "lps": lps, "policy_seeds": seeds, "tags": list(SHARED_TAGS + SILOED_TAGS),
           "runs": rows, "errors": [{k: v for k, v in e.items() if k != "traceback"} for e in errors],
           "git_revision": mc.git_revision(), "versions": mc.versions(), "wall_s": time.perf_counter() - t_start}
    outputs.dump(_jsonish(rec), cell_file(out, b, u, mu, c), compact=True)
    return {"runs": len(rows), "errors": errors, "lps": len(lps), "instance_hash": ih["shared"],
            "n_sub_instances": len(subs), "schedule_mismatch": len(mismatch)}


# ---------------------------------------------------------------- job: MILPs
def _ok_output(out: Path, jid: str, path, ignored: Optional[list] = None) -> Optional[dict]:
    """The JSON output `path` of job `jid`, or None unless the job's record says 'ok' (§2.4); an output present
    while its record is not 'ok' is listed in `ignored`."""
    rec = mc.read_record(out, jid)
    if rec is None or rec.get("status") != "ok":
        if ignored is not None and Path(path).is_file():
            ignored.append({"job": jid, "status": None if rec is None else rec.get("status"),
                            "output": _rel(path, out)})
        return None
    return mc.read_json(path)


def _cell_record(out: Path, b, u, mu, c) -> dict:
    cr = _ok_output(out, cell_id(b, u, mu, c), cell_file(out, b, u, mu, c))
    if cr is None:
        raise FileNotFoundError(f"no 'ok' cell record {cell_file(out, b, u, mu, c)} (run {cell_id(b, u, mu, c)} first)")
    return cr


def run_milp(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One MILP (§4.6, §4.7) on the instance rebuilt from the cell's resolved overrides, after the instance and
    schedule hash checks against the cell record: the shared OPT(sigma, omega), or borrower b<ii>'s on its
    sub-instance (a no-op with OPT 0 if the borrower has no client on the day; at b = 1 the job of b00 copies the
    shared record when the sub-instance's hash is the shared one's, E3-2, and fails unless the shared job is 'ok')."""
    from ..instance import restrict_clients
    p = job.params
    b, u, mu, c, part = int(p["b"]), int(p["u"]), float(p["mu"]), int(p["c"]), p["part"]
    hz = p.get("horizon")
    limit = mc.milp_limit_s()
    t0 = time.perf_counter()
    cr = _cell_record(out, b, u, mu, c)
    if cr.get("horizon") != hz:
        raise RuntimeError(f"cell {cr['job']} has horizon {cr.get('horizon')}, the job {hz}")
    common = {"job": job.id, "kind": "milp", "part": part, "borrower": None if part == "shared" else part, "b": b,
              "u": u, "mu": mu, "c": c, "cell_job": cr["job"]}
    path = milp_file(out, b, u, mu, c, part)
    if part == "shared":
        inst, model, _, _ = build_instance(b, u, mu, c, True, hz)
        want_ih, want_sh = cr["instances"]["shared"], cr["schedule_hash"]
    else:
        si, model, _, _ = build_instance(b, u, mu, c, False, hz)
        from ..drivers.siloed import borrower_partition
        idx = dict(borrower_partition(si)).get(part)
        if idx is None:
            if part not in cr["borrowers"]["dropped"]:
                raise RuntimeError(f"borrower {part} has no client in the rebuilt instance but the cell record "
                                   f"lists it as kept")
            rec = {**common, "method": "milp", "benchmark": "omega", "grid": BENCH_GRID, "status": "empty",
                   "status_msg": "the borrower has no client on the day (no overflow): OPT 0, no MILP",
                   "empty": True, "objective": 0.0, "dual_bound": 0.0, "gap": 0.0, "size": {}, "build_s": 0.0,
                   "solve_s": 0.0, "peak_rss_mb": None, "instance_hash": None, "schedule_hash": None,
                   "time_limit_s": float(limit), "mip_rel_gap": MILP_GAP, "git_revision": mc.git_revision(),
                   "wall_s": time.perf_counter() - t0}
            outputs.dump(rec, path)
            print(f"[e3] {job.id}: borrower without a client on the day, OPT 0", flush=True)
            return {"runs": 0, "status": "empty", "objective": 0.0}
        inst = restrict_clients(si, idx)
        want_ih, want_sh = cr["instances"]["sub"][part], cr["sub_schedule_hashes"][part]
    ih = mc.instance_hash(inst)
    if ih != want_ih:
        raise RuntimeError(f"rebuilt instance hash {ih[:12]} differs from the cell record's {want_ih[:12]}")
    sched = trace_schedule(inst, model, c)
    sh = mc.schedule_hash(sched)
    if sh != want_sh:
        raise RuntimeError(f"rebuilt schedule hash {sh[:12]} differs from the cell record's {want_sh[:12]}")
    common.update(instance_hash=ih, schedule_hash=sh)
    if b == 1 and part == "b00" and cr["instances"]["sub"].get("b00") == cr["instances"]["shared"]:
        # E3-2: the same model as the shared MILP; only an 'ok' shared record is copied, so that this job is 'ok'
        # only with a finished copy and a resume (MS3_RESUME=1) runs it again after the shared job
        sid = milp_id(b, u, mu, c, "shared")
        src_rec = mc.read_record(out, sid)
        st = None if src_rec is None else src_rec.get("status")
        if st != "ok":
            raise RuntimeError(f"b = 1: job {sid} is {st!r}, not 'ok': nothing to copy; {job.id} runs again after it "
                               "(run_e3.sh's second MILP pass; the summary takes this part from the shared record)")
        src = mc.read_json(milp_file(out, b, u, mu, c, "shared"))
        if src is None:
            raise FileNotFoundError(f"job {sid} is 'ok' but its record {milp_file(out, b, u, mu, c, 'shared')} "
                                    "is missing")
        if src.get("instance_hash") != ih or src.get("schedule_hash") != sh:
            raise RuntimeError(f"the shared record of {sid} has other hashes than this sub-instance")
        rec = {**src, **common, "copied_from": sid, "copied": True, "git_revision": mc.git_revision(),
               "wall_s": time.perf_counter() - t0}
        outputs.dump(rec, path)
        print(f"[e3] {job.id}: copied {sid} (status {rec['status']}, objective {rec.get('objective')})", flush=True)
        return {"runs": 0, "status": rec["status"], "objective": rec.get("objective"), "copied_from": sid}
    rec = solve_bench(inst, sched, "milp", limit, **common)
    rec["wall_s"] = time.perf_counter() - t0
    outputs.dump(rec, path)
    print(f"[e3] {job.id}: status {rec['status']} ({rec['status_msg']}), objective {rec['objective']}, dual bound "
          f"{rec['dual_bound']}, gap {rec['gap']}, {rec['size']}, {rec['wall_s']:.1f} s", flush=True)
    return {"runs": 0, "status": rec["status"], "objective": rec["objective"], "dual_bound": rec["dual_bound"],
            "gap": rec["gap"], "n_vars": rec["size"].get("n_vars")}


# ---------------------------------------------------------------- benchmark records of a cell (summary, gate)
def _milp_input(out: Path, jid: str, path, ignored: Optional[list] = None) -> dict:
    """A MILP's record for Q39's rule: its lb file if the job's record says 'ok', else a stand-in with the job's
    status ('wall_limit', 'oom_at_3G', 'error', 'failed', 'running'), or {'status': 'missing'}."""
    got = _ok_output(out, jid, path, ignored)
    if got is not None:
        return got
    rec = mc.read_record(out, jid)
    return {"status": rec.get("status") if rec is not None and rec.get("status") != "ok" else "missing"}


def _checked(rec: dict, ih: str, sh: str, what: str) -> dict:
    """A record whose instance or schedule hash differs from the cell's (left by an earlier run of its job) is not
    used: {'status': 'stale', ...}. Stand-ins without hashes pass unchanged."""
    bad = [name for key, want, name in (("instance_hash", ih, "instance hash"),
                                        ("schedule_hash", sh, "schedule hash"))
           if rec.get(key) is not None and rec[key] != want]
    if not bad:
        return rec
    return {"status": "stale", "stale_note": f"{what} record {rec.get('job')!r}: {' and '.join(bad)} differ from the "
                                             "cell's (an output of an earlier run of the job; rerun it)"}


COPY_KEYS = ("status", "objective", "dual_bound", "gap")    # a b00 copy at b = 1 is current iff these are the source's


def _b00_part(own: dict, src: dict, jid: str, sid: str) -> dict:
    """The b00 part at b = 1 when its sub-instance is the shared instance (E3-2): the shared record `src` (or its
    stand-in) as used for the shared part, marked as a copy; `own`, the b00 job's record or stand-in, is current
    iff it is an 'ok' copy of `src` (the job writes a record only then) with the same COPY_KEYS, else the entry
    carries a stale_copy note (rerun the b00 job; the values used are the shared record's either way)."""
    current = (own.get("copied") is True and own.get("copied_from") == sid
               and all(own.get(k) == src.get(k) for k in COPY_KEYS))
    rec = {**src, "job": jid, "copied_from": sid, "copied": True, "copy_current": current}
    if not current:
        rec["stale_copy"] = (f"the record of {jid} (status {own.get('status')!r}) is not a current copy of {sid}'s "
                             f"(status {src.get('status')!r}): rerun {jid}; the shared record is used (E3-2)")
    return rec


def cell_benchmarks(out: Path, cr: dict, ignored: Optional[list] = None) -> dict:
    """The benchmark records of one cell: per part (shared and each listed borrower) the LP record, the MILP
    record or stand-in (both checked against the cell's hashes) and bench_values; at b = 1, when the b00
    sub-instance is the shared instance, the b00 part is the shared part (_b00_part); the siloed sum
    (ms4_common.sum_bench: a dropped borrower adds 0) and the bracket of siloed / shared OPT (ms3_common.bracket)."""
    b, u, mu, c = cr["b"], cr["u"], cr["mu"], cr["c"]
    copy_b00 = int(b) == 1 and cr["instances"]["sub"].get("b00") == cr["instances"]["shared"]
    parts, bv, sums = {}, {}, []
    for part in ["shared"] + list(cr["borrower_list"]):
        jid = milp_id(b, u, mu, c, part)
        if part != "shared" and part in cr["borrowers"]["dropped"]:
            milp = _milp_input(out, jid, milp_file(out, b, u, mu, c, part), ignored)
            parts[part] = {"lp": None, "milp": milp, "job": jid, "empty": True}
            sums.append({"empty": True})
            continue
        ih = cr["instances"]["shared"] if part == "shared" else cr["instances"]["sub"].get(part)
        sh = cr["schedule_hash"] if part == "shared" else cr["sub_schedule_hashes"].get(part)
        lpi = (cr.get("lps") or {}).get(part)
        lp = (mc.read_json(Path(out) / lpi["file"]) if lpi else None) or {"status": "missing"}
        lp = _checked(lp, ih, sh, "LP")
        milp = _checked(_milp_input(out, jid, milp_file(out, b, u, mu, c, part), ignored), ih, sh, "MILP")
        if copy_b00 and part == "b00":
            milp = _b00_part(milp, parts["shared"]["milp"], jid, milp_id(b, u, mu, c, "shared"))
        v = mc.bench_values(lp, milp)
        parts[part] = {"lp": lp, "milp": milp, "job": jid, "empty": False}
        bv[part] = v
        if part != "shared":
            sums.append(v)
    shared = bv["shared"]
    siloed = m4.sum_bench(sums)
    try:
        br = mc.bracket(siloed, shared)
        br["gap_siloed"], br["gap_shared"] = br.pop("gap_eager"), br.pop("gap_omega")
    except ValueError as err:
        br = {"point": None, "lo": None, "hi": None, "exact": False, "gap_siloed": siloed.get("gap"),
              "gap_shared": shared.get("gap"), "error": str(err)}
        for k in ("point", "lo", "hi"):
            br[f"{k}_note"] = f"bracket refused: {err}"
    br["missing"] = False
    br["open"] = bool(br.get("point") is None or shared.get("milp_status") not in (0, 1))
    br["shared"] = _bench_brief(shared)
    br["siloed"] = {k: siloed.get(k) for k in ("LB", "incumbent", "gap", "exact", "n_parts", "n_empty",
                                                "LB_sources", "parts_without_incumbent", "parts_without_LB")}
    br["n_borrowers"], br["n_empty"] = len(cr["borrower_list"]), siloed["n_empty"]
    return {"parts": parts, "bench": bv, "shared": shared, "siloed": siloed, "bracket": br}


def _bench_brief(v: dict) -> dict:
    return {k: v.get(k) for k in ("LB", "LB_source", "incumbent", "gap", "exact", "milp_status", "lp_status")}


# ---------------------------------------------------------------- job: the gate (§1.2 item 6, §4.4)
def _brief_milp(rec: Optional[dict], job_rec: Optional[dict]) -> dict:
    r = rec or {}
    return {"job_status": None if job_rec is None else job_rec.get("status"),
            **{k: r.get(k) for k in ("status", "status_msg", "objective", "dual_bound", "gap", "size", "build_s",
                                     "solve_s", "wall_s", "peak_rss_mb", "time_limit_s", "estimate", "copied_from",
                                     "empty")}}


def run_gate(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """The E3 gate (§1.2 item 6, §4.4) on the gate cell: rebuilds its shared and siloed instances (hashes checked
    against the cell record), runs one A8 around BL5 with an allowance that never binds (ms4_common.need_params) on
    the shared instance and on every sub-instance, and writes gate.json with the config hash of the grid, the
    borrowers, the MILP sizes, statuses, gaps and times, the bracket of siloed / shared OPT and the allowance need of
    each run next to its M36 B0 (ms4_common.allowance_need: margin and t_a_at_B0)."""
    from ..drivers import run as drun
    from ..engine import simulate
    from .e6 import bl0a_all
    p = job.params
    b, u, mu, c, hz = int(p["b"]), int(p["u"]), float(p["mu"]), int(p["c"]), p.get("horizon")
    t_start = time.perf_counter()
    cr = _cell_record(out, b, u, mu, c)
    sh_inst, model, ecfg, ov_sh = build_instance(b, u, mu, c, True, hz)
    si_inst, _, _, ov_si = build_instance(b, u, mu, c, False, hz)
    subs = sub_instances(si_inst)
    ih = {"shared": mc.instance_hash(sh_inst), "siloed": mc.instance_hash(si_inst),
          "sub": {bid: mc.instance_hash(s) for bid, s in subs.items()}}
    sh = mc.schedule_hash(trace_schedule(sh_inst, model, c))
    check = {"instance": ih == cr["instances"], "schedule": sh == cr["schedule_hash"]}
    if not all(check.values()):
        raise RuntimeError(f"the rebuilt gate cell differs from the cell record {cr['job']}: {check}")
    errors: list = []

    def need(inst, ov, what):
        t0 = time.perf_counter()
        spec = run_spec("A8", m4.need_params("BL5"), ov, c, (0,), f"e3_gate_{what}")
        res = simulate(inst, drun.make_policy(spec, inst), model, ecfg, lender_seed=c, policy_seed=0)
        b0 = m4.sublet_params(inst)["B0"]
        bl0a = float(bl0a_all(inst))
        nd = m4.allowance_need(res, b0=b0)
        return {**nd, "bl0a_usd": bl0a, "B0_rule": m4.B0_RULE,
                "need_over_bl0a": nd["need_usd"] / bl0a if bl0a > 0 else None,
                "total_usd": float(res.components["total"]),
                "n_invariant_failures": len(res.invariant_failures), "wall_s": time.perf_counter() - t0}
    shared_need = mc.try_run(errors, "need_shared", need, sh_inst, ov_sh, "shared")
    sub_need = {}
    for bid, s in subs.items():
        sub_need[bid] = mc.try_run(errors, f"need_{bid}", need, s, ov_si, bid)
    bench = cell_benchmarks(out, cr)
    milp = {}
    for part, x in bench["parts"].items():
        milp[part] = _brief_milp(x["milp"], mc.read_record(out, x["job"]))
    lp = {part: (cr.get("lps") or {}).get(part) for part in ["shared"] + list(subs)}
    runs: dict = {}
    for r in cr["runs"]:
        e = runs.setdefault(r["tag"], {"p": [], "totals": [], "overflow_over_bl0a": [], "certificate_cases": {},
                                       "aborted": 0, "sub_aborted": 0, "n_sub_runs": 0})
        e["p"].append(r["p"])
        e["totals"].append(r["ALG"])
        e["overflow_over_bl0a"].append((r.get("accountings") or {}).get("overflow_over_bl0a"))
        if r.get("certificate_case"):
            e["certificate_cases"][r["certificate_case"]] = e["certificate_cases"].get(r["certificate_case"], 0) + 1
            e["aborted"] += bool(r.get("aborted"))
        for s in r.get("sub_runs") or []:
            e["n_sub_runs"] += 1
            if s.get("certificate_case"):
                e["certificate_cases"][s["certificate_case"]] = e["certificate_cases"].get(s["certificate_case"],
                                                                                           0) + 1
                e["sub_aborted"] += bool(s.get("aborted"))
    n_abort = sum(1 for v in sub_need.values() if v is not None and v.get("t_a_at_B0") is not None)
    gate = {"meta": {"exp": EXP, "job": job.id, "cell": {"b": b, "u": u, "mu": mu, "c": c}, "cell_job": cr["job"],
                     "reduced": design()["reduced"], "horizon": hz, "config": CONFIG, "normalize": NORMALIZE,
                     "B0_rule": m4.B0_RULE, "B0_share": m4.B0_SHARE, "milp_limit_s": mc.milp_limit_s(),
                     "git_revision": mc.git_revision(), "versions": mc.versions(), "written": _now(),
                     "note": "the E3 gate of design/sim_spec_ms4.md §1.2 item 6 and §4.4 (M7): the normalized "
                             "construction measured on the built config before the E3 grid runs"},
            "config_hash": grid_config_hash(), "cell_config_hashes": cell_config_hashes(b, u, mu, c),
            "instance_hashes": ih, "schedule_hash": sh, "hash_check": check, "sizes": cr["sizes"],
            "gamma_notes": cr["gamma_notes"], "borrowers": cr["borrowers"], "bl0a": cr["bl0a"],
            "references": cr["references"], "lp": lp, "milp": milp, "bracket": bench["bracket"],
            "allowance": {"gamma": m4.GAMMA, "B0_rule": m4.B0_RULE, "shared": shared_need, "sub_runs": sub_need,
                          "n_sub_runs": len(sub_need), "n_sub_abort_at_B0": n_abort,
                          "shared_abort_at_B0": None if shared_need is None
                          else shared_need.get("t_a_at_B0") is not None},
            "runs": runs, "errors": [{k: v for k, v in e.items() if k != "traceback"} for e in errors],
            "wall_s": time.perf_counter() - t_start}
    outputs.dump(gate, gate_file(out))
    return {"runs": 1 + len(sub_need), "errors": errors, "config_hash": gate["config_hash"],
            "bracket": {k: bench["bracket"].get(k) for k in ("point", "lo", "hi")},
            "shared_need_usd": None if shared_need is None else shared_need["need_usd"],
            "n_sub_abort_at_B0": n_abort}


def gate_limits(g: dict) -> set:
    """The MILP time limits a gate record ran under: meta.milp_limit_s and every solved or copied MILP record's
    time_limit_s (the gate's MILP jobs are jobs of the grid, which the full run resumes)."""
    out = {(g.get("meta") or {}).get("milp_limit_s")}
    for x in (g.get("milp") or {}).values():
        if isinstance(x, dict) and x.get("time_limit_s") is not None and not x.get("empty"):
            out.add(x["time_limit_s"])
    return {int(v) if isinstance(v, float) and v.is_integer() else v for v in out}


def check_gate(out=None) -> tuple[bool, str]:
    """Whether the full grid may start (§4.4): gate.json exists, the job record of e3:gate says 'ok', gate.json
    records the config hash of the grid's instances (grid_config_hash of design()) and its MILPs ran under the
    current MILP limit (ms3_common.milp_limit_s)."""
    o = mc.out_dir(EXP, out)
    g = mc.read_json(gate_file(o))
    if not isinstance(g, dict):
        return False, f"no {gate_file(o)}: run run_e3.sh --gate first (design/sim_spec_ms4.md §4.4)"
    rec = mc.read_record(o, GATE_ID)
    if rec is None or rec.get("status") != "ok":
        return False, f"the job record of {GATE_ID} is {None if rec is None else rec.get('status')!r}, not 'ok'"
    want = grid_config_hash()
    if g.get("config_hash") != want:
        return False, f"gate.json records the config hash {g.get('config_hash')!r}, the grid's is {want!r}"
    lim = gate_limits(g)
    if lim != {mc.milp_limit_s()}:
        return False, (f"the gate ran under the MILP limit(s) {sorted(lim, key=str)} s, the grid's is "
                       f"{mc.milp_limit_s()} s (MS3_MILP_LIMIT): run run_e3.sh --gate again")
    return True, (f"gate.json records the grid's config hash {want[:16]} and MILP limit {mc.milp_limit_s()} s (git "
                  f"revision {g['meta'].get('git_revision')})")


# ---------------------------------------------------------------- dispatch
def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    _, part, _ = mc.parse_job_id(job.id)
    if part == "cell":
        return run_cell(job, outputs, out)
    if part == "milp":
        return run_milp(job, outputs, out)
    if part == "gate":
        return run_gate(job, outputs, out)
    raise ValueError(f"unknown E3 job {job.id!r}")


def manifest_extra(out: Path) -> dict:
    """The instance hashes of every cell's shared and siloed instance and of its sub-instances (§2.6), the config
    hashes, the grid's config hash and the slice order."""
    d = design()
    hashes, cfgs = {}, {}
    for (b, u, mu, c) in grid_cells(d):
        key = f"b={b}:u={u}:mu={num_key(mu)}:c={c}"
        sh, _, _, _ = build_instance(b, u, mu, c, True, d["horizon"])
        si, _, _, _ = build_instance(b, u, mu, c, False, d["horizon"])
        hashes[key] = {"shared": mc.instance_hash(sh), "siloed": mc.instance_hash(si),
                       "sub": {bid: mc.instance_hash(s) for bid, s in sub_instances(si).items()}}
        cfgs[key] = cell_config_hashes(b, u, mu, c)
    return {"instance_hashes": hashes, "config_hashes": cfgs, "grid_config_hash": grid_config_hash(d),
            "slices": [list(x) for x in m_slices()],
            "design": {k: (list(v) if isinstance(v, tuple) else v) for k, v in d.items()}}


# ---------------------------------------------------------------- summary
def _agg(values: list, note: str) -> dict:
    a = mc.median_summary(values)
    if not values:
        for k in ("median", "p95", "max"):
            put(a, k, None, note)
        a["median_ci95_note"] = note
    return a


def _median(values: list) -> Optional[float]:
    v = [x for x in values if x is not None]
    return float(np.median(v)) if v else None


def ratio_entry(rows: list[dict]) -> dict:
    """The aggregates of one (b, u, mu, tag) over its runs (§4.8): ratio_LB and ratio_inc against the shared OPT."""
    note = "no run of this tag in the outputs" if not rows else "no run with a lower bound"
    rl = [r["lb"]["ratio_LB"] for r in rows if r["lb"].get("ratio_LB") is not None]
    ri = [r["lb"]["ratio_inc"] for r in rows if r["lb"].get("ratio_inc") is not None]
    gaps = [r["lb"]["gap"] for r in rows if r["lb"].get("gap") is not None]
    e = {"n_runs": len(rows), "n_ratio": len(rl), "n": len(rl), "ratio_LB": _agg(rl, note),
         "ratio_inc": _agg(ri, "no run with an incumbent" if rows else note)}
    e["median"], e["median_ci95"] = e["ratio_LB"]["median"], e["ratio_LB"]["median_ci95"]
    e["p95"], e["max"] = e["ratio_LB"]["p95"], e["ratio_LB"]["max"]
    if e["median"] is None:
        put(e, "median", None, note)
        e["median_ci95_note"] = note
    put(e, "inc_median", e["ratio_inc"]["median"], "no run with an incumbent" if rows else note)
    put(e, "share_exact", sum(bool(r["lb"].get("exact")) for r in rows) / len(rows) if rows else None, note)
    put(e, "max_gap", max(gaps) if gaps else None, "no MILP gap (MILP missing or killed)" if rows else note)
    put(e, "alg_mean", float(np.mean([r["ALG"] for r in rows])) if rows else None, note)
    e["lp_only"] = sum(1 for r in rows if r["lb"].get("milp_status") not in (0, 1))
    e["open"] = not rows or bool(e["lp_only"])
    if not rows:
        e["open_note"] = note
    return e


def util_entry(rows: list[dict]) -> dict:
    note = "no run of this tag in the outputs"
    return {"n": len(rows),
            "replica_utilization": _agg([r["replica_utilization"] for r in rows
                                         if r.get("replica_utilization") is not None], note),
            "loads_per_day": _agg([r["loads_per_day"] for r in rows if r.get("loads_per_day") is not None], note)}


ACC_FIELDS = ("overflow_usd", "total_usd", "overflow_over_bl0a", "total_over_bl0a", "own_share_of_total",
              "overflow_over_bl0b", "total_over_bl0b")


def cost_entry(rows: list[dict]) -> dict:
    """Cost over BL0a in both accountings (§2.6, ms4_common.accountings): medians over the runs, with the 95% bootstrap
    interval of the two ratios to BL0a."""
    note = "no run of this tag in the outputs"
    e = {"n": len(rows)}
    for k in ACC_FIELDS:
        put(e, k, _median([(r.get("accountings") or {}).get(k) for r in rows]), note)
    e["median_ci95"] = {}
    for k in ("overflow_over_bl0a", "total_over_bl0a"):
        v = [(r.get("accountings") or {}).get(k) for r in rows]
        e["median_ci95"][k] = _agg([x for x in v if x is not None], note)["median_ci95"]
    return e


def opt_entry(by_c: dict) -> dict:
    """opt.<b>.<u>.<mu> (§4.8): the brackets per alignment, the median of their points, the smallest lo and the
    largest hi; open where a bracket has no point or its shared MILP no result."""
    present = [x for x in by_c.values() if isinstance(x, dict) and not x.get("missing")]
    have = [x for x in present if x.get("point") is not None]
    e = {"by_alignment": by_c, "n_alignments": len(have), "n_cells": len(present)}
    note = "no bracket with a value"
    put(e, "point_median", _median([x["point"] for x in have]), note)
    put(e, "lo_min", min((x["lo"] for x in present if x.get("lo") is not None), default=None), note)
    put(e, "hi_max", max((x["hi"] for x in present if x.get("hi") is not None), default=None), note)
    e["exact"] = bool(present) and all(bool(x.get("exact")) for x in present)
    e["open"] = not present or any(bool(x.get("open")) for x in present)
    if not present:
        e["open_note"] = "no cell of this point in the outputs"
    src: dict = {"shared": {}, "siloed": {}}
    for x in present:
        s = (x.get("shared") or {}).get("LB_source")
        if s is not None:
            src["shared"][s] = src["shared"].get(s, 0) + 1
        for k, n in ((x.get("siloed") or {}).get("LB_sources") or {}).items():
            src["siloed"][k] = src["siloed"].get(k, 0) + n
    e["lb_source"] = src
    return e


def _null_bracket(note: str) -> dict:
    e = {"missing": True, "exact": False, "open": True, "shared": None, "siloed": None, "n_borrowers": None,
         "n_empty": None}
    for k in ("point", "lo", "hi", "gap_siloed", "gap_shared"):
        put(e, k, None, note)
    return e


def _cert_brief(r: dict, sub: Optional[dict] = None) -> dict:
    x = sub or r
    cert = x.get("certificate") or {}
    return {"cell": r.get("cell"), "tag": r["tag"], "p": r["p"], "borrower": None if sub is None else sub["borrower"],
            "case": x.get("certificate_case"), "t_a": x.get("t_a"), "B0_usd": x.get("B0_usd"),
            **{k: cert.get(k) for k in ("held", "core_bound_ok", "e_mode_ok", "e_mode_reserve_ok", "wind_down_ok")}}


def summary(out: Path) -> dict:
    out = Path(out)
    d = design()
    seeds = d["policy_seeds"]
    ignored: list = []
    cells = {}
    for key in grid_cells(full_design()):
        cr = _ok_output(out, cell_id(*key), cell_file(out, *key), ignored)
        if cr is not None:
            cells[key] = cr
    rows_by: dict = {}          # (b, u, mu, tag) -> run rows with 'lb'
    all_rows, brackets, milps, refs, borrowers, mism = [], {}, {}, {}, {}, []
    limit = mc.milp_limit_s()
    for key, cr in cells.items():
        b, u, mu, c = key
        bench = cell_benchmarks(out, cr, ignored)
        brackets[key] = bench["bracket"]
        for part, x in bench["parts"].items():
            st = x["milp"].get("status")
            milps[x["job"]] = {"kind": "shared" if part == "shared" else "siloed",
                               "status": "empty" if x["empty"] and st == "empty" else st,
                               "gap": x["milp"].get("gap"), "copied": bool(x["milp"].get("copied")),
                               "stale_copy": x["milp"].get("stale_copy")}
            for kind, r in (("lp", x["lp"]), ("milp", x["milp"])):
                tl = None if r is None or r.get("copied") or r.get("empty") else r.get("time_limit_s")
                if tl is not None and float(tl) != float(limit):
                    mism.append({"job": x["job"] if kind == "milp" else lp_id(b, u, mu, c, part), "kind": kind,
                                 "time_limit_s": float(tl)})
        lp_sh, milp_sh = bench["parts"]["shared"]["lp"], bench["parts"]["shared"]["milp"]
        for row in cr["runs"]:
            lb = mc.lb_record(row["ALG"], lp_sh, milp_sh, reason=row["ratio_validity"])
            r = {**row, "lb": lb, "cell": cr["job"], "c": c}
            rows_by.setdefault((b, u, mu, row["tag"]), []).append(r)
            all_rows.append(r)
        refs.setdefault(num_key(b), {}).setdefault(num_key(u), {}).setdefault(num_key(mu), {})[num_key(c)] = \
            cr["references"]
        if mu == MU_MAIN:
            bb = cr["borrowers"]
            borrowers.setdefault((b, u), {})[c] = {
                "kept": bb["kept"], "dropped": bb["dropped"], "shares": {x["id"]: x["share"] for x in bb["list"]},
                "C0_loads": {x["id"]: x["C0_loads"] for x in bb["list"]},
                "peak_loads": {x["id"]: x["peak_loads"] for x in bb["list"]},
                "normalize_factor": {x["id"]: x["normalize_factor"] for x in bb["list"]},
                "overflow_load_h": {x["id"]: x["overflow_load_h"] for x in bb["list"]}}
    ratios, opt, util, cost = {}, {}, {}, {}
    for (b, u, mu) in design_points():
        kb, ku, km = num_key(b), num_key(u), num_key(mu)
        for tag in TAGS:
            rows = rows_by.get((b, u, mu, tag), [])
            ratios.setdefault(kb, {}).setdefault(ku, {}).setdefault(km, {})[tag] = ratio_entry(rows)
            util.setdefault(kb, {}).setdefault(ku, {}).setdefault(km, {})[tag] = util_entry(rows)
            cost.setdefault(kb, {}).setdefault(ku, {}).setdefault(km, {})[tag] = cost_entry(rows)
        by_c = {}
        for c in ALIGNMENTS:
            by_c[num_key(c)] = brackets.get((b, u, mu, c)) or _null_bracket("no cell at this alignment in the outputs")
        opt.setdefault(kb, {}).setdefault(ku, {})[km] = opt_entry(by_c)
    bor: dict = {}
    for b in BS:
        for u in US:
            by = borrowers.get((b, u), {})
            ent = {"day": 0, "by_alignment": {}, "n_kept": {}, "n_dropped": {}}
            for c in ALIGNMENTS:
                ck = num_key(c)
                if c in by:
                    ent["by_alignment"][ck] = by[c]
                    ent["n_kept"][ck] = len(by[c]["kept"])
                    ent["n_dropped"][ck] = len(by[c]["dropped"])
                else:
                    note = "no mu = 1 cell at this alignment in the outputs"
                    for key in ("by_alignment", "n_kept", "n_dropped"):
                        put(ent[key], ck, None, note)
            bor.setdefault(num_key(b), {})[num_key(u)] = ent
    certs = certificates_block(all_rows)
    mcounts: dict = {"shared": {}, "siloed": {}}
    gaps, kills, ooms, gate_sz, copied, stale = [], [], [], [], [], []
    stale_copies = []
    for jid, x in milps.items():
        st = x["status"]
        if x["copied"]:             # the b00 parts at b = 1 (E3-2): the shared record's, counted there
            mcounts[x["kind"]]["copied"] = mcounts[x["kind"]].get("copied", 0) + 1
            copied.append(jid)
            if x["stale_copy"]:
                stale_copies.append({"job": jid, "note": x["stale_copy"]})
            continue
        mcounts[x["kind"]][str(st)] = mcounts[x["kind"]].get(str(st), 0) + 1
        if x["gap"] is not None and st in (0, 1):
            gaps.append(x["gap"])
        if st == "wall_limit":
            kills.append(jid)
        if st == "oom_at_3G":
            ooms.append(jid)
        if st == "size_gate":
            gate_sz.append(jid)
        if st == "stale":
            stale.append(jid)
    stale_lp = sorted({r["cell"] for r in all_rows if r["lb"].get("lp_status") == "stale"})
    milp = {"counts": mcounts, "max_gap": max(gaps) if gaps else None, "wall_limit_kills": kills, "oom_kills": ooms,
            "size_gate": gate_sz, "copied": copied, "stale_copies": stale_copies, "stale": stale,
            "stale_lp_cells": stale_lp, "limit_mismatch": mism, "n_jobs": len(milps), "limit_s": limit,
            "mip_rel_gap": MILP_GAP, "grid": BENCH_GRID}
    if milp["max_gap"] is None:
        milp["max_gap_note"] = "no MILP with a gap"
    gate = _ok_output(out, GATE_ID, gate_file(out), ignored)
    checks = build_checks(cells, all_rows, brackets, opt, bor, certs, gate)
    meta = {"exp": EXP, "git_revision": mc.git_revision(), "written": _now(), "reduced": d["reduced"],
            "grid": {"b": list(BS), "u": list(US), "mu_main": MU_MAIN, "mu_sweep": list(MUS_SWEEP),
                     "default_point": list(DEFAULT_POINT), "alignments": list(d["alignments"]),
                     "alignments_design": list(ALIGNMENTS), "policy_seeds": list(seeds),
                     "policy_seeds_design": list(POLICY_SEEDS), "b_run": list(d["bs"]), "u_run": list(d["us"]),
                     "mu_sweep_run": list(d["mus_sweep"]),
                     "horizon": None if d["horizon"] is None else list(d["horizon"]), "cells_found": len(cells)},
            "config": CONFIG, "lender_model": LENDER_MODEL, "normalize": NORMALIZE, "B0_rule": m4.B0_RULE,
            "B0_share": m4.B0_SHARE, "milp": {"limit_s": limit, "mip_rel_gap": MILP_GAP, "grid": BENCH_GRID},
            "tags": {t: {"policy_id": v[0], "params": v[1] if v[1] is not None else "ms4_common.sublet_params(inst)",
                         "mode": v[2], "style_key": v[3],
                         "info_class_reported": m4.INFO_CLASS_REPORTED if t in A8_TAGS else None}
                     for t, v in TAGS.items()},
            "references": refs, "ignored_outputs": list({x["job"]: x for x in ignored}.values())}
    try:
        meta["slices"] = [list(x) for x in m_slices()]
        meta["overrides_template"] = overrides(1, 8, True)
    except (OSError, KeyError, ValueError) as err:     # the a12 outputs missing: the summary still builds
        put(meta, "slices", None, f"{type(err).__name__}: {err}")
    if d["reduced"]:
        meta["reduced_note"] = (f"reduced job list ({REDUCED_ENV}=1): b {list(d['bs'])}, u {list(d['us'])}, mu "
                                f"points {list(d['mus_sweep'])}, alignment 1, policy seed 0, slow slots "
                                f"[{d['horizon'][0]}, {d['horizon'][0] + d['horizon'][1]}); not a result")
    summ = {"meta": meta, "ratios": ratios, "opt": opt, "util": util, "cost_over_bl0a": cost, "borrowers": bor,
            "certificates": certs, "milp": milp, "checks": checks}
    mc.dump_json(summ, out / "summary.json")
    mc.write_text(tables(summ), out / "tables.md")
    return summ


def certificates_block(rows: list[dict]) -> dict:
    """The certificate counts (§2.6, §4.8, E3-5): Sublet runs and Sublet-siloed sub-runs (count_certificates), the
    failures in Theorem W's proven cases, the W(c) runs and the aborts per (b, u, mu)."""
    shared = [r for r in rows if r["tag"] == "Sublet"]
    subs = [(r, s) for r in rows if r["tag"] == "Sublet-siloed" for s in r.get("sub_runs") or []]
    fails, wc = [], []
    for r, s in [(r, None) for r in shared] + subs:
        x = s or r
        case = x.get("certificate_case")
        held = (x.get("certificate") or {}).get("held") is True
        if case in m4.PROVEN_CASES and not held:
            fails.append(_cert_brief(r, s))
        if case == "W(c)":
            wc.append(_cert_brief(r, s))
    ab: dict = {}
    for r in shared:
        b, u, mu = _cell_key(r)
        e = ab.setdefault(b, {}).setdefault(u, {}).setdefault(mu, {"shared": {"runs": 0, "aborted": 0},
                                                                  "sub_runs": {"runs": 0, "aborted": 0}})
        e["shared"]["runs"] += 1
        e["shared"]["aborted"] += bool(r.get("aborted"))
    for r, s in subs:
        b, u, mu = _cell_key(r)
        e = ab.setdefault(b, {}).setdefault(u, {}).setdefault(mu, {"shared": {"runs": 0, "aborted": 0},
                                                                  "sub_runs": {"runs": 0, "aborted": 0}})
        e["sub_runs"]["runs"] += 1
        e["sub_runs"]["aborted"] += bool(s.get("aborted"))
    return {"shared": m4.count_certificates(shared), "siloed_sub_runs": m4.count_certificates([s for _, s in subs]),
            "all": m4.count_certificates(shared + [s for _, s in subs]), "failures": fails,
            "w_c_runs": wc, "aborts": ab}


def _cell_key(r: dict) -> tuple:
    """(b, u, mu) keys of a run row from its cell id."""
    _, _, kv = mc.parse_job_id(r["cell"])
    return kv["b"], kv["u"], kv["mu"]


def build_checks(cells: dict, rows: list, brackets: dict, opt: dict, bor: dict, certs: dict, gate) -> dict:
    ch = {}
    # E3-1: lo <= b (1 + 1e-9)
    e31 = [{"cell": cell_id(*k), "b": k[0], "lo": br.get("lo"), "point": br.get("point"), "hi": br.get("hi")}
           for k, br in brackets.items() if br.get("lo") is not None]
    bad = [x for x in e31 if x["lo"] > x["b"] * (1 + TOL)]
    refused = [cell_id(*k) for k, br in brackets.items() if br.get("error")]
    ch["E3-1"] = {"status": ("fail" if bad or refused else "pass") if e31 or refused else "missing",
                  "claim": "every bracket of siloed / shared OPT has lo <= b (1 + 1e-9): the siloed optimum is at most "
                           "b times the shared one (the copy argument of design §5.5 E3; C3-P7, PROVEN, elementary, "
                           "gives the factor's attainment, not this bound)",
                  "n_brackets": len(e31), "n_above_b": len(bad), "above_b": bad[:20], "refused": refused[:20],
                  "max_lo_over_b": max((x["lo"] / x["b"] for x in e31), default=None)}
    # E3-2: at b = 1 the siloed sub-instance is the shared instance and the siloed totals equal the shared ones
    b1 = {k: cr for k, cr in cells.items() if k[0] == 1}
    hash_bad, tot = [], []
    for k, cr in b1.items():
        if cr["instances"]["sub"].get("b00") != cr["instances"]["shared"]:
            hash_bad.append(cr["job"])
        by = {(r["tag"], r["p"]): r["ALG"] for r in cr["runs"]}
        for si, shd in PAIRS_B1:
            for p in cr["policy_seeds"]:
                if (si, p) in by and (shd, p) in by:
                    tot.append({"cell": cr["job"], "pair": [si, shd], "p": p,
                                "abs_diff": abs(by[(si, p)] - by[(shd, p)])})
                else:
                    tot.append({"cell": cr["job"], "pair": [si, shd], "p": p, "abs_diff": None})
    tot_bad = [x for x in tot if x["abs_diff"] is None or x["abs_diff"] > TOL]
    ch["E3-2"] = {"status": ("fail" if hash_bad or tot_bad else "pass") if b1 else "missing",
                  "claim": "at b = 1 the siloed sub-instance has the shared instance's q44_study.instance_hash and "
                           "each siloed run's total equals its shared counterpart's (Sublet-siloed and Sublet, "
                           "A6-siloed and A6) to 1e-9 USD",
                  "n_cells": len(b1), "hash_differs": hash_bad, "n_pairs": len(tot), "failures": tot_bad[:20],
                  "max_abs_diff": max((x["abs_diff"] for x in tot if x["abs_diff"] is not None), default=None)}
    # E3-3: every siloed run's components are the sum of its sub-runs', recomputed from the stored rows, and
    # run_siloed's per-slot sums equal its components (the cell job's per_slot_abs_diff)
    sil = [r for r in rows if r["mode"] == "siloed"]
    d3 = []
    for r in sil:
        subs = r.get("sub_runs") or []
        d3.append({"cell": r["cell"], "tag": r["tag"], "p": r["p"],
                   "components": _sum_diff(r["components"], [s["components"] for s in subs]),
                   "alg": abs(float(r["ALG"]) - sum(float(s["ALG"]) for s in subs)),
                   "per_slot": r.get("per_slot_abs_diff")})
    bad3 = [x for x in d3 if x["per_slot"] is None or max(x["components"], x["alg"], x["per_slot"]) > TOL]

    def mx(key):
        return max((x[key] for x in d3 if x[key] is not None), default=None)
    ch["E3-3"] = {"status": ("fail" if bad3 else "pass") if sil else "missing",
                  "claim": "every siloed run's components and total equal the sums of its sub-runs' (recomputed from "
                           "the stored rows), and run_siloed's per-slot series sum to its components (1e-9 USD)",
                  "n_runs": len(sil), "failures": bad3[:20], "max_abs_diff": mx("components"),
                  "max_abs_diff_alg": mx("alg"), "max_abs_diff_per_slot": mx("per_slot"),
                  "n_per_slot_missing": sum(1 for x in d3 if x["per_slot"] is None)}
    # E3-4: invariants, GPU-only lease slots, ratio validity, the realized schedule, P1 ratios >= 1 - 1e-6
    units = [(r, s) for r in rows for s in ([r] if r["mode"] == "shared" else r.get("sub_runs") or [])]

    def where(r, s):
        return {"cell": r["cell"], "tag": r["tag"], "p": r["p"], "borrower": None if s is r else s.get("borrower")}
    bad_inv = [where(r, s) for r, s in units if s["n_invariant_failures"]]
    bad_gpu = [where(r, s) for r, s in units if s["gpu_only_lease_slots"]]
    bad_rv = [where(r, s) for r, s in units if s["ratio_validity"] is not None]
    mism = [{"cell": cr["job"], **x} for cr in cells.values() for x in cr.get("schedule_mismatch") or []]
    p1 = [r for r in rows if r["mode"] == "shared" and r["plan_class_p1"] and r["lb"].get("ratio_LB") is not None]
    bad_p1 = [{"cell": r["cell"], "tag": r["tag"], "p": r["p"], "ratio_LB": r["lb"]["ratio_LB"]} for r in p1
              if r["lb"]["ratio_LB"] < 1 - P1_TOL]
    ch["E3-4"] = {"status": ("fail" if bad_inv or bad_gpu or bad_rv or mism or bad_p1 else "pass") if units
                  else "missing",
                  "claim": "every run and sub-run: invariant_failures empty, gpu_only_lease_slots 0, ratio_validity "
                           "None and the cell's realized schedule; every shared run of plan class P1 has ratio_LB >= "
                           "1 - 1e-6 (Proposition M4)",
                  "n_runs": len(rows), "n_runs_and_sub_runs": len(units), "invariant_failures": bad_inv[:20],
                  "gpu_only_lease_slots": bad_gpu[:20], "ratio_validity_not_none": bad_rv[:20],
                  "schedule_mismatch": mism[:20], "n_p1": len(p1), "p1_below": bad_p1[:20],
                  "min_ratio_LB_p1": min((r["lb"]["ratio_LB"] for r in p1), default=None)}
    # E3-5: certificates held in Theorem W's proven cases; W(c) counted
    a = certs["all"]
    ch["E3-5"] = {"status": ("pass" if not certs["failures"] and a["by_case"]["unavailable"]["runs"] == 0 else "fail")
                  if a["n"] else "missing",
                  "claim": "Theorem W (PROVEN for the engine as implemented under C1-C3, audited): every Sublet run "
                           "and Sublet-siloed sub-run has its certificate held in the proven cases W(a), W(b); W(c) "
                           "runs (CONJECTURE) counted and reported",
                  "n": a["n"], "held": a["held"], "by_case": a["by_case"], "n_failures": len(certs["failures"]),
                  "failures": certs["failures"][:20], "n_w_c": len(certs["w_c_runs"]),
                  "shared": certs["shared"]["by_case"], "siloed_sub_runs": certs["siloed_sub_runs"]["by_case"]}
    # E3-6: the share of the factor that survives and the borrowers without overflow (informative)
    share = {}
    for kb, by_u in opt.items():
        for ku, by_mu in by_u.items():
            e = by_mu.get(num_key(MU_MAIN))
            if e is None:
                continue
            bb = float(kb)
            share.setdefault(kb, {})[ku] = {k: (None if e.get(src) is None else e[src] / bb)
                                            for k, src in (("point", "point_median"), ("lo", "lo_min"),
                                                           ("hi", "hi_max"))}
    zero = {kb: {ku: {"day": v["day"], "n_dropped": v["n_dropped"]} for ku, v in by_u.items()}
            for kb, by_u in bor.items()}
    ch["E3-6"] = {"status": "informative",
                  "claim": "the share of the factor that survives, (siloed / shared OPT) / b per (b, u) at mu = 1, and "
                           "the count of borrowers without overflow per (b, day) (plan §7)",
                  "factor_share": share, "borrowers_without_overflow": zero}
    # E3-7: the gate record
    if gate is None:
        ch["E3-7"] = {"status": "missing", "claim": "the gate record (§4.4) with the grid's config hash",
                      "file": "gate.json", "why": "gate.json missing or the job record of e3:gate is not 'ok'"}
    else:
        try:
            want = grid_config_hash()
        except (OSError, KeyError, ValueError) as err:
            want = None
            why = f"{type(err).__name__}: {err}"
        al = gate.get("allowance") or {}
        eq = want is not None and gate.get("config_hash") == want
        lim = gate_limits(gate)
        lim_eq = lim == {mc.milp_limit_s()}
        ch["E3-7"] = {"status": "informative" if eq and lim_eq else "fail",
                      "claim": "the gate record (§4.4): its config hash equals the grid's, its MILPs ran under the "
                               "grid's MILP limit, and its bracket, borrower shares and allowance needs (shared and "
                               "per sub-run) are those reported",
                      "file": "gate.json", "config_hash": gate.get("config_hash"), "grid_config_hash": want,
                      "config_hash_equal": eq, "gate_milp_limits_s": sorted(lim, key=str),
                      "milp_limit_s": mc.milp_limit_s(), "milp_limit_equal": lim_eq,
                      "git_revision": (gate.get("meta") or {}).get("git_revision"),
                      "bracket": {k: (gate.get("bracket") or {}).get(k) for k in ("point", "lo", "hi", "exact")},
                      "borrower_shares": {x["id"]: x.get("share")
                                          for x in (gate.get("borrowers") or {}).get("list", [])},
                      "allowance": {"shared": {k: (al.get("shared") or {}).get(k)
                                               for k in ("need_usd", "need_over_bl0a", "B0_usd", "margin_usd",
                                                         "t_a_at_B0")},
                                    "sub_runs": {bid: None if v is None else
                                                 {k: v.get(k) for k in ("need_usd", "need_over_bl0a", "B0_usd",
                                                                        "margin_usd", "t_a_at_B0")}
                                                 for bid, v in (al.get("sub_runs") or {}).items()},
                                    "n_sub_abort_at_B0": al.get("n_sub_abort_at_B0")}}
        if want is None:
            ch["E3-7"]["grid_config_hash_note"] = why
    return ch


def tables(s: dict) -> str:
    L = ["# E3: shared replicas (design/sim_spec_ms4.md §4)", ""]
    if s["meta"].get("reduced"):
        L += [f"*{s['meta']['reduced_note']}*", ""]
    L.append("## ALG / shared LB per (b, u, mu) (median [95% CI], median of ALG / incumbent, share exact)")
    L.append("")
    rows = []
    for kb, by_u in s["ratios"].items():
        for ku, by_mu in by_u.items():
            for km, by_t in by_mu.items():
                for tag, e in by_t.items():
                    if e["n_runs"] == 0:
                        continue
                    ci = e.get("median_ci95") or [None, None]
                    rows.append([kb, ku, km, tag, e["n_runs"], e.get("median"), ci[0], ci[1], e.get("inc_median"),
                                 e.get("share_exact"), e.get("max_gap"), e["lp_only"]])
    L.append(mc.md_table(["b", "u", "mu", "tag", "runs", "median", "ci lo", "ci hi", "inc median", "exact", "max gap",
                          "LP only"], rows))
    L.append("## Siloed OPT / shared OPT (brackets, MS3 spec M4)")
    L.append("")
    rows = [[kb, ku, km, e["n_alignments"], e.get("point_median"), e.get("lo_min"), e.get("hi_max"), e["exact"],
             e["open"]] for kb, by_u in s["opt"].items() for ku, by_mu in by_u.items() for km, e in by_mu.items()
            if e["n_alignments"]]
    L.append(mc.md_table(["b", "u", "mu", "alignments", "point median", "lo min", "hi max", "exact", "open"], rows))
    L.append("## Cost over BL0a (overflow accounting; total accounting) and replica utilization, medians")
    L.append("")
    rows = []
    for kb, by_u in s["cost_over_bl0a"].items():
        for ku, by_mu in by_u.items():
            for km, by_t in by_mu.items():
                for tag, e in by_t.items():
                    if e["n"]:
                        ut = s["util"][kb][ku][km][tag]
                        rows.append([kb, ku, km, tag, e["n"], e.get("overflow_over_bl0a"), e.get("total_over_bl0a"),
                                     ut["replica_utilization"]["median"], ut["loads_per_day"]["median"]])
    L.append(mc.md_table(["b", "u", "mu", "tag", "runs", "cost / BL0a", "total / (BL0a + own)", "utilization",
                          "loads per day"], rows))
    L.append("## Borrowers without overflow on the day (per alignment)")
    L.append("")
    rows = [[kb, ku, ck, n] for kb, by_u in s["borrowers"].items() for ku, e in by_u.items()
            for ck, n in e["n_dropped"].items() if n is not None and not ck.endswith("_note")]
    L.append(mc.md_table(["b", "u", "c", "dropped"], rows))
    c = s["certificates"]
    L.append("## Certificates (Sublet runs and Sublet-siloed sub-runs, Theorem W)")
    L.append("")
    L.append(mc.md_table(["case", "shared runs", "held", "sub-runs", "held"],
                         [[k, c["shared"]["by_case"][k]["runs"], c["shared"]["by_case"][k]["held"],
                           c["siloed_sub_runs"]["by_case"][k]["runs"], c["siloed_sub_runs"]["by_case"][k]["held"]]
                          for k in m4.CASES]))
    L.append("## MILPs")
    L.append("")
    L.append(mc.md_table(["kind", "status", "jobs"], [[k, st, n] for k, v in s["milp"]["counts"].items()
                                                      for st, n in sorted(v.items())]))
    L.append(f"max gap {s['milp']['max_gap']}; wall-limit kills {len(s['milp']['wall_limit_kills'])}; size gate "
             f"{len(s['milp']['size_gate'])}; copied at b = 1 {len(s['milp']['copied'])}")
    L.append("")
    L.append("## Checks (§4.9)")
    L.append("")
    L.append(mc.md_table(["check", "status"], [[k, v["status"]] for k, v in s["checks"].items()]))
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- command line
def main(argv=None) -> int:
    """ms3_common.main's command line, plus --check-gate [--out DIR] (§4.4: run_e3.sh refuses the full run unless
    it exits 0)."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check-gate" in args:
        ap = argparse.ArgumentParser(prog=f"python -m sublet.experiments.{EXP} --check-gate",
                                     description="exit 0 iff gate.json records the grid's config hash (§4.4)")
        ap.add_argument("--check-gate", action="store_true", required=True)
        ap.add_argument("--out", type=Path, default=None, help=f"output folder (default <root>/out/{EXP})")
        a = ap.parse_args(args)
        try:
            ok, msg = check_gate(a.out)
        except (OSError, KeyError, ValueError) as err:
            ok, msg = False, f"the check could not run: {type(err).__name__}: {err}"
        print(f"[{EXP}] gate {'ok' if ok else 'NOT OK'}: {msg}", flush=True)
        return 0 if ok else 1
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=args, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
