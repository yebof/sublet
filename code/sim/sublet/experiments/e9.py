"""E9: scalability (design/sim_spec_ms5.md §5; deliverable D41, unit U28; open choices M16-M24). The supplementary
figure sf_e9 and the table e9_steps.tex (§7.2).

Claims: none (design §5.5, E9: a supplementary figure of the wall time per simulated hour against sites x LLMs for the
slow loop, the fast loop and the LP bound, with a reference line at real time). The checks E9-1 ... E9-5 (§5.9) are
that every run and every LP finishes inside the 3 GB cap with no invariant failure, that the engine's loop times add up
(C27), that every A8 run keeps its certificate (Theorem W(a)(b), PROVEN for the engine as implemented under C1-C3 and
audited; W(c) CONJECTURE, counted), and, informative, the times against real time and against the slot lengths.

Instances (§5.3, M16). A point <base>_V<V>_<llms> (point_overrides, the point builder of
code/sim/out/ms5spec/e9_sizing.py) is configs/bench_e7f.json (base e7f: E7's full menu, 20 revocable contracts and the
protected one) or configs/bench_e7r.json (base e7r: the E5 and E6 base, 3 revocable contracts and the protected one)
with the overrides time.horizon_min (1440, one day), stranding.mu_over_beta_tilde 1 (the configs' value, set
explicitly as E7 does), lender_defaults.n_layers V (each trace lender then offers min(V, v_top) layer sites) and one
LLM set: SML (the configs' S, M and L with s_S 0.25; no override), ML (llms [M, L], borrowers.s_S 0) or S (llms [S],
borrowers.s_S 1). Every run keeps the configs' 1-min fast grid on 5-min slow slots, the trace lender with I1, 'sell'
and violations absorbed, unmerged layers, and engine.check_invariants true (§0 item 5; the configs set it false).
The builder solves Gamma again at every point, so the demand grows with the supply at the configs' tightness 0.5.
Alignments c in {1, 2, 3, 4} are config seeds with lender seed = config seed; policy seed 0 (§5.5, M20).
  run points (16)  e7f SML at V in {1, 2, 4, 8, 16, 32, 64}; e7f S and ML at V 8 (the LLM axis); e7r SML at the
                   same seven V (the base of the LP bound)
  LP points (7)    e7r SML at the seven V (M17, M18)

Policies (§5.4, M22; tag: registry id, parameters, style key of figs/style.py, SUPP_POLICIES_MS5['sf_e9']):
  Sublet  A8 ms4_common.sublet_params(inst, 'BL5') on the point's own instance (M4: gamma 1, kappa None,
          B0 = B0_SHARE x e6.bl0a_all(inst))                                                         sublet
  A6      A6 {} (its defaults)                                                                       a6
The LP bound is E7's gap LP (§3.8 of design/sim_spec_ms4.md): the one-day merged relaxation on the slow grid,
opt.milp.solve_lp(merged_relaxation(inst, sched), grid 'slow', allow_large, HiGHS time limit 1500 s, no plan), with
sched the lender's static schedule of lender seed c (Lender.static_schedule, the realized schedule under 'trace' with
'sell' and 'absorb', so no BL0a run is made), solved only when the LP rule's estimate (opt.milp.estimate_size,
parts.est_mb_lp = 130 + 5.4e-4 nnz MB) is under LP_GATE_MB (2800 MB, M18); style key lb. Since the slow grid's LP
bounds a 1-min-routing run's optimum in neither direction (design §5.2.4), E9 reports its time, never a ratio.

Timing (§5.6, M21). Every number is read from the engine's RunResult.runtime (C27's keys; E9 never copies
engine.simulate): the slow loop per simulated hour slow_step_s_sum / hours, the fast loop fast_step_s_sum / hours, the
invariant checks check_s (inside the fast steps), the setup per run apart (the build, the driver inputs, the policy's
construction and reset_s, once per run), the P50, P99 and maximum of the slow and fast steps, policy_s, routing_s and
the routing LP's calls; the job's ru_maxrss and its scope's memory.peak; the load average at the job's start. Real time
is 3600 s per simulated hour, the slow slot 300 s and the fast slot 60 s.

Jobs (§5.7, §2.4; ids by ms3_common.job_id; every job 'alone', holding every slot of the host-wide semaphore, §0
item 3, M24), in run order (the runs in the order of the points, then the LPs):
  e9:run:pt=<point>:pol=<tag>:c=<c>   one simulated day of one policy at one point and alignment (16 x 2 x 4 = 128)
  e9:lp:pt=<point>:c=<c>              the one-day merged LP bound at one LP point and alignment (7 x 4 = 28)
Limits (§5.7): a run's limit is measurement 4's case limit (code/sim/out/ms5spec/run_all.sh, E9_RUNS: 900 s by
default, Sublet 1800 s at e7f_V16_SML, 3600 s at e7f_V32_SML and 7200 s at e7f_V64_SML and e7r_V64_SML, A6 1800 s at
e7f_V32_SML and e7r_V64_SML and 3600 s at e7f_V64_SML), 900 s at the four added e7r points (V 2, 4, 16, 32; their
estimates are at most 165 s); an LP's limit is 1800 s (HiGHS's own limit 1500 s). run_e9.sh runs each job under
`timeout --foreground -k 30 (LIMIT + 60)`, as ms3_lib.sh runs a MILP job, and classifies a nonzero exit with
ms3_common.classify_exit and LIMIT (exit 124: wall_limit; 137 at LIMIT + 60 s or later: wall_limit; other 137:
oom_at_3G), so that MS3 spec §0 item 2's rule applies unchanged. `python -m sublet.experiments.e9 --limits` prints
'<limit s> <job id>' per job for run_e9.sh.

Command line (ms3_common.main, §2.4), run from code/sim:
  python -m sublet.experiments.e9 --list | --job ID | --summary | --estimate | --manifest  [--out DIR]
  python -m sublet.experiments.e9 --limits
--estimate uses measurement 4's case walls (run_all.log; EST_RUN_S, EST_LP_S), and for the four added e7r points
e7f's growth over V applied to the nearest measured e7r point (V 8 for V <= 16, V 64 for V 32; estimate, §5.8),
scaled by the horizon.

Reduced runs (smoke tests): MS3_E9_REDUCED=1 (run_e9.sh --reduced sets it) keeps every point and job kind with
alignment 1, policy seed 0 and a 2-hour horizon (REDUCED_HORIZON_MIN); its summary carries meta.reduced true and is
never a result.

Outputs under code/sim/out/e9/ (§5.7, §2.6): runs/<job file>.json (not versioned; per job the point's overrides, the
instance's sizes, hash and references and the job's results: a run's run entry (experiments/e7.run_entry: both
accountings, components, metrics, invariants, the A8 record and certificate) with its timing, an LP's estimate, size,
status and times), jobs/, logs/, manifest.json, summary.json, tables.md and run_e9.log. Numeric keys as
ms3_common.num_key ('1', '64'); a missing value is null with a '*_note' key, and an entry without runs keeps every field
of its non-null form (§2.6).

summary.json
  meta                      exp, spec, git_revision, written, reduced (reduced_note), host, versions, horizon_min,
                            grid {run_points, lp_points, bases {base: config}, V, llm_sets {set: {llms, s_S}},
                            alignments, alignments_design, policy_seed}, policies {tag: {policy_id, params, style_key,
                            a8}}, lp {style_key, grid, merged, time_limit_s, gate_mb, rule}, limits {run {point: {tag:
                            s}}, lp_s, timeout_grace_s, kill_after_s, rule}, real_time_s_per_h, slow_slot_s,
                            fast_slot_s, B0_rule, info_class_reported_a8, jobs_ok, jobs_missing, jobs_by_status,
                            ignored_outputs, hosts and loadavg_start (the jobs' hosts and load averages at their start)
  points.<point>            base, config, menu ('full' for e7f, 'reduced' for e7r), V, llm_set, llms, s_S, lp_point;
                            n_sites, n_sites_by_kind, n_sites_merged (the LP's merged sites, median over its
                            alignments; null with a note at a run-only point), n_llms, n_contracts,
                            n_revocable_contracts, sites_x_llms (the instance's sizes at the lowest alignment run;
                            sites, LLMs and contracts do not depend on the alignment), n_clients and n_units
                            ({median, min, max} over the alignments), bl0a_usd {c}, by_alignment.<c> {instance_hash,
                            bl0a_usd, own_capacity_usd, n_clients, n_units, demand_load_h}; policies.<tag> {n_runs,
                            alignments, by_alignment.<c> (RUN_METRICS, and for Sublet t_a, aborted, certificate_case,
                            certificate_held), median, min, max (each RUN_METRICS over the alignments), abort_share,
                            t_a, certificates (ms4_common.count_certificates; Sublet only, null with a note for A6)}
  lp.<point>                n_runs, alignments, by_alignment.<c> (LP_METRICS, status, status_msg, highs_model_status,
                            highs_model_status_text, skipped, skip_reason, instance_hash, schedule_hash,
                            instance_hash_equal_runs), median, min, max (each LP_METRICS over the alignments)
  checks.E9-1 ... E9-5      {status ('pass', 'fail', 'missing', 'informative'), claim, the check's inputs}

Status labels (copied from design/sim_spec_ms5.md §5.1, never upgraded): E9 is a system measurement with no claim;
Theorem W(a)(b) PROVEN for the engine as implemented under C1-C3 and audited (checked per run by the certificate); W(c)
CONJECTURE.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import copy
import hashlib
import math
import platform
import re
import resource
import sys
import time
from pathlib import Path
from typing import Mapping, Optional

import numpy as np

from .. import paths
from . import ms3_common as mc
from . import ms4_common as m4
from .ms3_common import Job, job_id, num_key, put

EXP = "e9"
SPEC = "design/sim_spec_ms5.md §5"
BASES = {"e7f": m4.E7_CONFIG, "e7r": m4.E7R_CONFIG}          # bench_e7f.json, bench_e7r.json (§5.3)
MENU = {"e7f": "full", "e7r": "reduced"}                     # E7's full menu, the E5/E6 base's reduced menu
VS = (1, 2, 4, 8, 16, 32, 64)                                # lender_defaults.n_layers (§5.3)
# LLM set -> (llm ids, borrowers.s_S; None keeps the configs' llms list and s_S 0.25), e9_sizing.py LLM_SETS
LLM_SETS = {"SML": (("S", "M", "L"), None), "ML": (("M", "L"), 0.0), "S": (("S",), 1.0)}
CONFIG_S_S = 0.25                                            # both configs' borrowers.s_S
DAY_MIN = 1440                                               # one simulated day (M23)
E7F_SML = tuple(f"e7f_V{v}_SML" for v in VS)
LLM_AXIS = ("e7f_V8_S", "e7f_V8_ML")
E7R_SML = tuple(f"e7r_V{v}_SML" for v in VS)
RUN_POINTS = E7F_SML + LLM_AXIS + E7R_SML                    # 16 run points (M16), in run order
LP_POINTS = E7R_SML                                          # 7 LP points (M17)
LARGEST = {"e7f": "e7f_V64_SML", "e7r": "e7r_V64_SML"}       # the largest run point of each menu (E9-5)
# tag: registry id, inner (A8), fixed parameters, style key (§5.4, M22; style.SUPP_POLICIES_MS5['sf_e9'])
TAGS = {"Sublet": {"id": "A8", "inner": "BL5", "params": None, "style": "sublet"},
        "A6": {"id": "A6", "inner": None, "params": {}, "style": "a6"}}
A8_TAGS = ("Sublet",)
LP_STYLE = "lb"
ALIGNMENTS = (1, 2, 3, 4)
POLICY_SEED = 0                                              # M20
REDUCED_ENV = "MS3_E9_REDUCED"
REDUCED_HORIZON_MIN = 120                                    # a 2-hour horizon (24 slow slots)
# limits (§5.7): measurement 4's case limits (out/ms5spec/run_all.sh E9_RUNS, s), RUN_LIMIT_DEFAULT_S elsewhere
RUN_LIMIT_S = {"e7f_V16_SML": {"Sublet": 1800}, "e7f_V32_SML": {"Sublet": 3600, "A6": 1800},
               "e7f_V64_SML": {"Sublet": 7200, "A6": 3600}, "e7r_V64_SML": {"Sublet": 7200, "A6": 1800}}
RUN_LIMIT_DEFAULT_S = 900
LP_LIMIT_S = 1800                                            # the LP job's limit
LP_TIME_LIMIT_S = 1500.0                                     # HiGHS's own time limit (E7's gap LP, e7.GAP_LP_LIMIT_S)
LP_GATE_MB = 2800.0                                          # M18: the LP rule's estimate must be under it
LP_GRID = "slow"
TIMEOUT_GRACE_S = mc.WALL_GRACE_S                            # run_e9.sh: timeout at LIMIT + 60 s, as ms3_lib.sh's MILPs
KILL_AFTER_S = mc.KILL_AFTER_S
CAP_MB = 3072.0                                              # MemoryMax=3G (MiB)
SCOPE_NOTE = "not in a capped scope (no memory.max): memory.peak would be an enclosing cgroup's"
REAL_TIME_S_PER_H = 3600.0
SLOW_SLOT_S = 300.0
FAST_SLOT_S = 60.0
COUNT_KEYS = ("routing_lp_calls", "n_slow_steps", "n_fast_steps")     # timing_fields keeps them integers
STEP_TOL_S = 1e-6                                            # E9-2: the step sums may exceed wall_s by at most this
HIGHS_OPTIMAL = 7                                            # HiGHS's model status kOptimal
_HIGHS_STATUS = re.compile(r"HiGHS Status (\d+):\s*([^)]*)\)")
FAIL_STATUSES = ("error", "failed", "oom_at_3G", "wall_limit")
# time constants (s per one-day run or LP; case walls of measurement 4, out/ms5spec/run_all.log): (Sublet, A6)
EST_RUN_S = {"e7f_V1_SML": (5.7, 4.1), "e7f_V2_SML": (9.7, 5.6), "e7f_V4_SML": (18.5, 8.9),
             "e7f_V8_SML": (41.5, 17.4), "e7f_V16_SML": (109.9, 41.8), "e7f_V32_SML": (353.1, 127.2),
             "e7f_V64_SML": (1357.6, 432.7), "e7f_V8_S": (59.8, 13.2), "e7f_V8_ML": (36.8, 13.8),
             "e7r_V1_SML": (4.1, 3.5), "e7r_V8_SML": (19.4, 13.1), "e7r_V64_SML": (500.4, 112.5)}
EST_LP_S = {1: 13.8, 2: 30.6, 4: 75.0, 8: 180.9, 16: 261.4, 32: 394.4, 64: 388.1}     # e7r SML, case walls
EST_JOB_S = 5.0                                              # process start and imports, per job
# the numeric fields of a run (by_alignment.<c>) and their median, min and max over the alignments (§5.6, §5.7)
RUN_METRICS = ("slow_loop_s_per_h", "fast_loop_s_per_h", "loops_s_per_h", "check_s_per_h", "setup_s", "build_s",
               "driver_inputs_s", "make_policy_s", "reset_s", "slow_step_p50_s", "slow_step_p99_s", "slow_step_max_s",
               "fast_step_p50_s", "fast_step_p99_s", "fast_step_max_s", "check_s", "finish_s", "policy_s",
               "routing_s", "routing_lp_s", "routing_lp_calls", "engine_wall_s", "engine_s_per_h", "job_s",
               "job_s_per_h", "n_slow_steps", "n_fast_steps", "peak_rss_mb", "scope_memory_peak_mb",
               "cost_over_bl0a", "total_over_bl0a", "overflow_usd", "n_leases", "n_alive_leases_max",
               "n_invariant_failures")
# the numeric fields of an LP (by_alignment.<c>) and their median, min and max over the alignments
LP_METRICS = ("n_vars", "n_rows", "nnz", "n_sites", "n_sites_merged", "est_mb_lp", "instance_build_s", "schedule_s",
              "merge_s", "estimate_s", "build_s", "solve_s", "lp_s", "s_per_h", "objective", "objective_over_bl0a",
              "bl0a_usd", "solver_peak_rss_mb", "peak_rss_mb", "scope_memory_peak_mb", "est_over_measured")
CHECK_IDS = ("E9-1", "E9-2", "E9-3", "E9-4", "E9-5")
INFORMATIVE = ("E9-5",)
# summary checks.<id>.claim: the content of §5.9 with the status labels of §5.1 (copied, never upgraded)
CHECK_CLAIMS = {
    "E9-1": "every run job finished with status ok inside the 3 GB cap, with no invariant failure",
    "E9-2": "per run, C27's counts equal the grid (n_slow_steps = T_slow, n_fast_steps = T_fast: 288 and 1,440 for "
            "one day) and slow_step_s_sum + fast_step_s_sum + reset_s + finish_s does not exceed wall_s by more than "
            "1e-6 s",
    "E9-3": "every A8 run has its certificate, and it holds in every run of Theorem W's proven cases (W(a), W(b); "
            "PROVEN for the engine as implemented under C1-C3, audited); W(c) runs (CONJECTURE) are counted and "
            "listed with their t_a",
    "E9-4": "every LP job was solved to optimality (linprog status 0, HiGHS's model status 7, 'Optimal') inside the "
            "3 GB cap",
    "E9-5": "per point and policy, the loops per simulated hour against real time, the slow-step P99 and maximum "
            "against the 300-s slot, the fast-step P99 against the 60-s slot, the setup, the peak memory and the "
            "LP's time; the ratio to real time of the largest point of each menu named (informative)"}


# ---------------------------------------------------------------- settings
def design() -> dict:
    """The job grid: the full grid of §5.3-§5.5, or the reduced one with MS3_E9_REDUCED=1 (module docstring)."""
    red = os.environ.get(REDUCED_ENV, "0") == "1"
    return {"reduced": red, "alignments": (1,) if red else ALIGNMENTS, "policy_seed": POLICY_SEED,
            "horizon_min": REDUCED_HORIZON_MIN if red else DAY_MIN}


# ---------------------------------------------------------------- points (§5.3; out/ms5spec/e9_sizing.py)
def point_name(base: str, V: int, llms: str) -> str:
    return f"{base}_V{int(V)}_{llms}"


def parse_point(name: str) -> tuple:
    """(base, V, LLM set) of a point name <base>_V<V>_<llms>; ValueError for any other name."""
    parts = str(name).split("_")
    if len(parts) != 3 or not parts[1].startswith("V") or not parts[1][1:].isdigit():
        raise ValueError(f"bad E9 point {name!r}: expected <base>_V<V>_<llms>")
    base, V, llms = parts[0], int(parts[1][1:]), parts[2]
    if base not in BASES or V < 1 or llms not in LLM_SETS:
        raise ValueError(f"bad E9 point {name!r}: base in {list(BASES)}, V >= 1, LLM set in {list(LLM_SETS)}")
    return base, V, llms


def llm_entry(tier: str) -> dict:
    """An llms[] entry as the configs write theirs."""
    return {"id": tier, "catalog": "maas_a10", "entry": tier, "kappa_mult": 1.0}


def point_overrides(point: str, horizon_min: int = DAY_MIN) -> dict:
    """The overrides of a point (§5.3), as out/ms5spec/e9_sizing.py's point_overrides builds them: time.horizon_min,
    stranding.mu_over_beta_tilde 1, lender_defaults.n_layers V, and for the sets ML and S the llms list and
    borrowers.s_S (SML keeps the configs' own)."""
    _, V, llms = parse_point(point)
    ov = {"time.horizon_min": int(horizon_min), "stranding.mu_over_beta_tilde": 1.0,
          "lender_defaults.n_layers": int(V)}
    ids, s_S = LLM_SETS[llms]
    if s_S is not None:
        ov["llms"] = [llm_entry(t) for t in ids]
        ov["borrowers.s_S"] = float(s_S)
    return ov


def point_spec(point: str, policy_id: str, params=None, *, c: int = 1, horizon_min: int = DAY_MIN,
               name: str = "e9") -> dict:
    """The validated run spec of one run at a point (drivers.run.load_run_spec): the point's config with
    point_overrides, the config's trace lender (I1, 'sell', 'absorb'), engine.check_invariants true (§0 item 5),
    config seed = lender seed c, policy seed 0."""
    from ..drivers.run import load_run_spec
    base = parse_point(point)[0]
    return load_run_spec({"schema_version": 1, "name": name, "instance": BASES[base],
                          "overrides": point_overrides(point, horizon_min), "lender_model": {},
                          "engine": dict(m4.ENGINE),
                          "policy": {"id": policy_id, "params": copy.deepcopy(dict(params or {}))},
                          "seeds": {"config": [int(c)], "lender": "config", "policy": [POLICY_SEED]},
                          "bench": None, "out": "code/sim/out/e9"})


def build_point(point: str, c: int, horizon_min: int) -> tuple:
    """(inst, model, ecfg, build_s) of a point at alignment c (BL0a's spec: the instance does not depend on the
    policy)."""
    from ..drivers.run import build
    t0 = time.perf_counter()
    inst, model, ecfg = build(point_spec(point, "BL0a", {}, c=c, horizon_min=horizon_min), int(c))
    return inst, model, ecfg, time.perf_counter() - t0


def instance_sizes(inst) -> dict:
    """Sites (by kind), contracts, clients, LLMs (and those with clients), units, sites x LLMs, the grid, the trace
    lenders' v_top = v0 + offered layers (the most layer sites V can reach), the demand in load-hours, BL0a and the
    Gamma note (out/ms5spec/e9_sizing.py's instance_sizes)."""
    from .e6 import bl0a_all
    from ..instance import units
    kinds: dict = {}
    for s in inst.sites:
        kinds[s.kind] = kinds.get(s.kind, 0) + 1
    trace = [lt for lt in inst.lenders if lt.kind not in ("protected", "synthetic")]
    with_sites = [lt for lt in trace if len(lt.site_index) > 0]
    v_top = {lt.lender: int(lt.v0 + lt.n_layers) for lt in with_sites}
    g = inst.grid
    return {"n_sites": int(inst.m), "n_sites_by_kind": kinds, "n_contracts": int(inst.K),
            "n_revocable_contracts": int(sum(not k.protected for k in inst.contracts)),
            "contracts": [k.id for k in inst.contracts],
            "n_llms": int(inst.J), "llms": [x.id for x in inst.llms],
            "llms_with_clients": sorted({inst.llms[int(j)].id for j in inst.clients.llm}),
            "n_clients": int(inst.n), "n_units": int(len(units(inst).client)),
            "units_per_replica": int(inst.units_per_replica), "sites_x_llms": int(inst.m * inst.J),
            "grid": {"slow_min": int(g.slow_min), "fast_min": int(g.fast_min), "T_slow": int(g.T_slow),
                     "T_fast": int(g.T_fast), "horizon_min": int(g.horizon_min), "start_mow": int(g.start_mow)},
            "n_trace_lenders": len(trace), "n_trace_lenders_with_sites": len(with_sites), "v_top": v_top,
            "demand_load_h": float(np.asarray(inst.clients.demand, dtype=np.float64).sum()) * g.fast_min / 60.0,
            "bl0a_usd": float(bl0a_all(inst)), "gamma_note": [n for n in inst.notes if "Gamma" in n]}


# ---------------------------------------------------------------- process facts
def _rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def cgroup_memory() -> dict:
    """memory.max and memory.peak of this process's cgroup (the job's systemd-run scope), in MB where readable."""
    out = {"path": None, "memory_max": None, "memory_peak_mb": None}
    try:
        for line in Path("/proc/self/cgroup").read_text().splitlines():
            parts = line.strip().split(":", 2)
            if len(parts) == 3 and parts[0] == "0":
                out["path"] = parts[2]
        if out["path"]:
            base = Path("/sys/fs/cgroup") / out["path"].lstrip("/")
            mx, pk = base / "memory.max", base / "memory.peak"
            if mx.exists():
                out["memory_max"] = mx.read_text().strip()
            if pk.exists():
                out["memory_peak_mb"] = int(pk.read_text().strip()) / 2.0 ** 20
    except (OSError, ValueError) as err:
        out["error"] = str(err)
    return out


def _loadavg() -> Optional[list]:
    try:
        return [float(x) for x in os.getloadavg()]
    except OSError:
        return None


def _job_meta(job: Job) -> dict:
    return {"exp": EXP, "job": job.id, "spec": SPEC, "git_revision": mc.git_revision(), "versions": mc.versions(),
            "written": mc._now(), "reduced": design()["reduced"], "host": platform.node(),
            "omp_num_threads": os.environ.get("OMP_NUM_THREADS")}


# ---------------------------------------------------------------- jobs (§5.7)
def run_id(point: str, tag: str, c: int) -> str:
    return job_id(EXP, "run", pt=point, pol=tag, c=int(c))


def lp_id(point: str, c: int) -> str:
    return job_id(EXP, "lp", pt=point, c=int(c))


def run_path(out, jid: str) -> Path:
    return Path(out) / "runs" / mc.job_file_name(jid)


def run_limit_s(point: str, tag: str) -> int:
    """A run job's limit (§5.7): measurement 4's case limit, RUN_LIMIT_DEFAULT_S (900 s) elsewhere."""
    return int(RUN_LIMIT_S.get(point, {}).get(tag, RUN_LIMIT_DEFAULT_S))


def est_run_s(point: str, tag: str) -> float:
    """A one-day run's time (§5.8): measurement 4's case wall where measured; at the four added e7r points (estimate)
    e7f's ratio t(V) / t(anchor) applied to e7r's run at the anchor, V 8 for V <= 16 and V 64 above."""
    i = list(TAGS).index(tag)
    if point in EST_RUN_S:
        return EST_RUN_S[point][i]
    base, V, llms = parse_point(point)
    anchor = 8 if V <= 16 else 64
    ref = EST_RUN_S[point_name("e7r", anchor, llms)][i]
    return ref * EST_RUN_S[point_name("e7f", V, llms)][i] / EST_RUN_S[point_name("e7f", anchor, llms)][i]


def jobs() -> list:
    """The E9 jobs in run order (§5.7): the runs in the order of the points (per point Sublet, then A6, each over the
    alignments), then the LPs; every job 'alone'."""
    d = design()
    hz, scale = d["horizon_min"], d["horizon_min"] / float(DAY_MIN)
    out = []
    for point in RUN_POINTS:
        base, V, llms = parse_point(point)
        for tag in TAGS:
            for c in d["alignments"]:
                out.append(Job(run_id(point, tag, c), "alone",
                               {"kind": "run", "point": point, "base": base, "V": V, "llm_set": llms, "tag": tag,
                                "c": int(c), "policy_seed": POLICY_SEED, "horizon_min": hz,
                                "limit_s": run_limit_s(point, tag)},
                               EST_JOB_S + scale * est_run_s(point, tag)))
    for point in LP_POINTS:
        base, V, llms = parse_point(point)
        for c in d["alignments"]:
            out.append(Job(lp_id(point, c), "alone",
                           {"kind": "lp", "point": point, "base": base, "V": V, "llm_set": llms, "c": int(c),
                            "horizon_min": hz, "limit_s": LP_LIMIT_S, "time_limit_s": LP_TIME_LIMIT_S,
                            "gate_mb": LP_GATE_MB},
                           EST_JOB_S + scale * EST_LP_S[V]))
    return out


def tag_params(tag: str, inst) -> dict:
    """The policy parameters of `tag` on the run's own instance (§5.4, M4): Sublet ms4_common.sublet_params(inst,
    'BL5'), A6 its defaults {}. A driver never types B0 (§2.2)."""
    t = TAGS[tag]
    if t["id"] == "A8":
        return m4.sublet_params(inst, t["inner"])
    return copy.deepcopy(t["params"])


# ---------------------------------------------------------------- timing (§5.6, M21; C27's keys)
def _num(v) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def timing_fields(rt: Mapping, hours: float, setup: Mapping) -> dict:
    """E9's timing of one run (§5.6, M21) from C27's keys of `rt` (RunResult.runtime) over `hours` simulated hours,
    with the setup parts `setup` (build_s, driver_inputs_s, make_policy_s; the policy's reset is rt['reset_s']): the
    slow and fast loop per simulated hour (slow_step_s_sum / hours, fast_step_s_sum / hours) and their sum, the
    invariant checks per simulated hour, the setup per run apart (setup_s = build + driver inputs + the policy's
    construction + reset_s), the steps' P50, P99 and maximum, check_s, finish_s, policy_s, routing_s, the routing LP's
    time and calls, the engine's wall (with the reset) and per simulated hour, and the step counts. A key that the
    runtime lacks gives null with a note (§2.6)."""
    h = float(hours)
    if not h > 0:
        raise ValueError(f"timing_fields: hours must be positive, got {hours!r}")
    out: dict = {}

    def per_h(key, src):
        v = _num(rt.get(src))
        put(out, key, None if v is None else v / h, f"runtime has no {src}")
    per_h("slow_loop_s_per_h", "slow_step_s_sum")
    per_h("fast_loop_s_per_h", "fast_step_s_sum")
    s, f = out.get("slow_loop_s_per_h"), out.get("fast_loop_s_per_h")
    put(out, "loops_s_per_h", None if s is None or f is None else s + f, "a loop sum is missing")
    per_h("check_s_per_h", "check_s")
    parts = {k: _num(setup.get(k)) for k in ("build_s", "driver_inputs_s", "make_policy_s")}
    parts["reset_s"] = _num(rt.get("reset_s"))
    for k, v in parts.items():
        put(out, k, v, f"no {k}")
    put(out, "setup_s", None if any(v is None for v in parts.values()) else sum(parts.values()),
        "a setup part is missing")
    for key, src in (("slow_step_p50_s", "slow_step_s_p50"), ("slow_step_p99_s", "slow_step_s_p99"),
                     ("slow_step_max_s", "slow_step_s_max"), ("fast_step_p50_s", "fast_step_s_p50"),
                     ("fast_step_p99_s", "fast_step_s_p99"), ("fast_step_max_s", "fast_step_s_max"),
                     ("check_s", "check_s"), ("finish_s", "finish_s"), ("policy_s", "policy_s"),
                     ("routing_s", "routing_s"), ("routing_lp_s", "routing_lp_s"),
                     ("routing_lp_calls", "routing_lp_calls"), ("engine_wall_s", "wall_s"),
                     ("n_slow_steps", "n_slow_steps"), ("n_fast_steps", "n_fast_steps")):
        v = _num(rt.get(src))
        put(out, key, int(v) if v is not None and key in COUNT_KEYS else v, f"runtime has no {src}")
    per_h("engine_s_per_h", "wall_s")
    return out


def step_check(rt: Mapping, T_slow: int, T_fast: int, tol: float = STEP_TOL_S) -> dict:
    """E9-2's rule on one run (§5.9): n_slow_steps = T_slow, n_fast_steps = T_fast, and slow_step_s_sum +
    fast_step_s_sum + reset_s + finish_s - wall_s <= tol (C27 ends finish_s where wall_s is read, so the sum never
    exceeds the wall but for rounding). Returns {ok, problems, excess_s, tolerance_s, n_slow_steps, n_fast_steps,
    T_slow, T_fast}."""
    probs = []
    ns, nf = rt.get("n_slow_steps"), rt.get("n_fast_steps")
    if ns != int(T_slow):
        probs.append(f"n_slow_steps {ns!r} != T_slow {int(T_slow)}")
    if nf != int(T_fast):
        probs.append(f"n_fast_steps {nf!r} != T_fast {int(T_fast)}")
    keys = ("slow_step_s_sum", "fast_step_s_sum", "reset_s", "finish_s", "wall_s")
    vals = {k: _num(rt.get(k)) for k in keys}
    excess = None
    miss = [k for k, v in vals.items() if v is None]
    if miss:
        probs.append(f"runtime has no finite {', '.join(miss)}")
    else:
        excess = (vals["slow_step_s_sum"] + vals["fast_step_s_sum"] + vals["reset_s"] + vals["finish_s"]
                  - vals["wall_s"])
        if excess > float(tol):
            probs.append(f"the step sums with reset_s and finish_s exceed wall_s by {excess:.3g} s > {tol:g} s")
    return {"ok": not probs, "problems": probs, "excess_s": excess, "tolerance_s": float(tol), "n_slow_steps": ns,
            "n_fast_steps": nf, "T_slow": int(T_slow), "T_fast": int(T_fast)}


def agg_alignments(by_c: Mapping, keys) -> dict:
    """The median, minimum and maximum over the alignments (§5.5, M20) of each numeric key of the entries
    by_c.<c> (None left out): {'n', 'alignments', 'median': {key: v}, 'min': {...}, 'max': {...}}; a key without a value
    at any alignment is null with its note in each of the three (§2.6)."""
    out = {"n": len(by_c), "alignments": sorted(int(c) for c in by_c), "median": {}, "min": {}, "max": {}}
    for k in keys:
        v = [x for x in (_num((e or {}).get(k)) for e in by_c.values()) if x is not None]
        note = "no alignment with a value" if by_c else "no run"
        put(out["median"], k, float(np.median(v)) if v else None, note)
        put(out["min"], k, float(min(v)) if v else None, note)
        put(out["max"], k, float(max(v)) if v else None, note)
    return out


def lp_gate(est_mb_lp, gate_mb: float = LP_GATE_MB) -> bool:
    """M18: an LP is solved iff the LP rule's estimate (opt.milp.estimate_size parts.est_mb_lp) is under the gate."""
    v = _num(est_mb_lp)
    return v is not None and v < float(gate_mb)


def highs_status(msg) -> tuple:
    """(HiGHS's model status, its text) parsed from a solver message '... (HiGHS Status 7: Optimal)'; (None, None)
    if the message names none."""
    m = _HIGHS_STATUS.search(str(msg or ""))
    return (int(m.group(1)), m.group(2).strip()) if m else (None, None)


# ---------------------------------------------------------------- jobs: one-day runs
def run_point(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One run job (§5.7): one simulated day of `tag` at the point and alignment, alone on the host: the build, the
    driver inputs, the policy (drivers.run.make_policy) and engine.simulate, each timed; the run entry of
    experiments/e7.run_entry and E9's timing from C27's runtime keys (timing_fields, step_check)."""
    from ..algos import registry
    from ..drivers.run import driver_inputs, make_policy
    from ..engine import simulate
    from ..lender import resolve_params
    from .e7 import run_entry
    p = job.params
    point, tag, c, hz = p["point"], p["tag"], int(p["c"]), int(p["horizon_min"])
    load, cg0 = _loadavg(), cgroup_memory()
    t_job = time.perf_counter()
    inst, model, ecfg, build_s = build_point(point, c, hz)
    if not ecfg.check_invariants:
        raise RuntimeError("E9 runs need check_invariants=True (§0 item 5)")
    refs, ih = m4.references(inst), mc.instance_hash(inst)
    sizes = instance_sizes(inst)
    pid = TAGS[tag]["id"]
    params = tag_params(tag, inst)
    spec = point_spec(point, pid, params, c=c, horizon_min=hz, name=f"e9_{tag}_{point}")
    t0 = time.perf_counter()
    inputs, imeta = driver_inputs(pid, params, inst)
    driver_inputs_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    pol = make_policy(spec, inst, inputs=inputs)
    make_policy_s = time.perf_counter() - t0
    print(f"[e9] {job.id}: {inst.m} sites x {inst.J} LLMs, {sizes['n_units']} units, T_slow {inst.grid.T_slow}; "
          f"running {pid} {params}", flush=True)
    t0 = time.perf_counter()
    res = simulate(inst, pol, model, ecfg, lender_seed=c, policy_seed=POLICY_SEED)
    sim_s = time.perf_counter() - t0
    peak, cg1 = _rss_mb(), cgroup_memory()
    hours = inst.grid.horizon_min / 60.0
    rt = dict(res.runtime)
    timing = timing_fields(rt, hours, {"build_s": build_s, "driver_inputs_s": driver_inputs_s,
                                       "make_policy_s": make_policy_s})
    # the run with its setup: the build, the driver inputs, the policy's construction and engine.simulate
    job_s = build_s + driver_inputs_s + make_policy_s + sim_s
    timing.update(simulate_s=sim_s, job_s=job_s, job_s_per_h=job_s / hours, hours=hours)
    steps = step_check(rt, inst.grid.T_slow, inst.grid.T_fast)
    entry = run_entry(res, inst, model, refs, refs.get("own_capacity_usd"), tag=tag, spec=spec, pol=pol,
                      ps=POLICY_SEED, c=c, wall_s=driver_inputs_s + make_policy_s + sim_s, imeta=imeta)
    entry["runtime"] = rt
    memory = {"peak_rss_mb": peak, "scope_start": cg0, "scope_after_run": cg1, "scope_capped": _capped(cg1),
              "cap_mb": CAP_MB, "fits_cap": _fits_cap(peak, cg1)}
    put(memory, "scope_memory_peak_mb", cg1.get("memory_peak_mb") if _capped(cg1) else None, SCOPE_NOTE)
    a8 = entry.get("a8") or {}
    rec = {"meta": {**_job_meta(job), "loadavg_start": load}, "kind": "run", "point": point, "base": p["base"],
           "config": BASES[p["base"]], "V": int(p["V"]), "llm_set": p["llm_set"], "tag": tag, "policy_id": pid,
           "params": params, "style_key": TAGS[tag]["style"], "c": c, "policy_seed": POLICY_SEED, "horizon_min": hz,
           "limit_s": p.get("limit_s"), "overrides": spec["overrides"], "instance_hash": ih, "instance": sizes,
           "references": refs, "lender_model": _lender_dict(inst, model),
           "lender_params_resolved": resolve_params(inst, model), "info_class": registry.info_class(
               pid, params, model.information), "timing": timing, "steps_check": steps, "memory": memory,
           "job_wall_s": time.perf_counter() - t_job, "runs": [entry], "errors": []}
    outputs.dump(_plain(rec), run_path(out, job.id), compact=True)
    print(f"[e9] {job.id}: {entry['ALG']:.4f} USD ({entry['accountings'].get('overflow_over_bl0a')} x BL0a); slow "
          f"loop {timing['slow_loop_s_per_h']} s/h, fast loop {timing['fast_loop_s_per_h']} s/h, setup "
          f"{timing['setup_s']} s, job {job_s:.1f} s, ru_maxrss {peak:.0f} MB, t_a {a8.get('t_a')}", flush=True)
    return {"runs": 1, "errors": [], "point": point, "tag": tag, "c": c, "instance_hash": ih,
            "slow_loop_s_per_h": timing["slow_loop_s_per_h"], "fast_loop_s_per_h": timing["fast_loop_s_per_h"],
            "setup_s": timing["setup_s"], "cost_over_bl0a": entry["accountings"].get("overflow_over_bl0a"),
            "t_a": a8.get("t_a"), "steps_ok": steps["ok"]}


def _plain(x):
    """metrics._jsonable (non-finite floats as strings) for the free-form parts of run files."""
    from ..metrics import _jsonable
    return _jsonable(x)


def _lender_dict(inst, model) -> dict:
    """The run's lender model and the builder's merge flag (§0 item 5: unmerged layers)."""
    lm = (getattr(inst, "config", None) or {}).get("lender_model") or {}
    return {"schedule": model.schedule, "information": model.information, "on_unavailable": model.on_unavailable,
            "violations": model.violations, "params": dict(model.params or {}),
            "merge_identical_layers": lm.get("merge_identical_layers")}


def _capped(cg: Mapping) -> bool:
    """Whether the cgroup has a memory limit (the job's 3G scope; 'max' or unreadable: not capped)."""
    mx = str(cg.get("memory_max") or "")
    return mx.isdigit()


def _fits_cap(peak_rss_mb: float, cg: Mapping) -> bool:
    """The job stayed under the 3 GB cap: its ru_maxrss and, in a capped scope, the scope's memory.peak below CAP_MB.
    Outside a capped scope (a test run without systemd-run) memory.peak is that of an enclosing cgroup and does not
    count."""
    if not float(peak_rss_mb) < CAP_MB:
        return False
    sp = cg.get("memory_peak_mb")
    return not (_capped(cg) and sp is not None and not float(sp) < CAP_MB)


# ---------------------------------------------------------------- jobs: the LP bound
def run_lp(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One LP job (§5.3, §5.7, M17, M18; alone on the host): the point's instance at alignment c, the lender's static
    schedule of lender seed c, the merged relaxation, the LP rule's estimate and, under the gate, opt.milp.solve_lp on
    the merged model (grid 'slow', allow_large, HiGHS limit 1500 s, no plan)."""
    from ..config import rng_streams
    from ..lender import Lender
    from ..opt.milp import estimate_size, solve_lp
    from ..opt.relax import merged_relaxation
    p = job.params
    point, c, hz = p["point"], int(p["c"]), int(p["horizon_min"])
    gate, limit = float(p.get("gate_mb", LP_GATE_MB)), float(p.get("time_limit_s", LP_TIME_LIMIT_S))
    load, cg0 = _loadavg(), cgroup_memory()
    t_job = time.perf_counter()
    inst, model, _, build_s = build_point(point, c, hz)
    sizes, ih = instance_sizes(inst), mc.instance_hash(inst)
    t0 = time.perf_counter()
    sched = Lender(inst, model, rng_streams(c)["lender"]).static_schedule()
    if sched is None:
        raise RuntimeError(f"{job.id}: the lender has no static schedule (adaptive)")
    schedule_s = time.perf_counter() - t0
    sh = mc.schedule_hash(sched)
    t0 = time.perf_counter()
    inst_m, sched_m, _ = merged_relaxation(inst, sched)
    merge_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    est = estimate_size(inst_m, sched_m, grid=LP_GRID)
    estimate_s = time.perf_counter() - t0
    est_mb = float(est["parts"]["est_mb_lp"])
    fits = lp_gate(est_mb, gate)
    hours = inst.grid.horizon_min / 60.0
    bl0a = sizes["bl0a_usd"]
    m: dict = {"n_sites": int(inst.m), "n_sites_merged": int(inst_m.m), "est_mb_lp": est_mb,
               "instance_build_s": build_s, "schedule_s": schedule_s, "merge_s": merge_s, "estimate_s": estimate_s,
               "bl0a_usd": bl0a}
    estimate = {"n_vars": est.get("n_vars"), "n_rows": est.get("n_rows"), "nnz": est.get("nnz"),
                "est_mb_lp": est_mb, "est_mb_milp": est.get("est_mb"),
                "rule": "est_mb_lp = 130 + 5.4e-4 nnz MB (the LP rule of opt/milp.py estimate_size)"}
    print(f"[e9] {job.id}: {inst.m} -> {inst_m.m} merged sites, {est.get('n_vars')} vars, {est.get('nnz')} nnz, LP "
          f"rule {est_mb:.0f} MB (gate {gate:.0f} MB)", flush=True)
    del inst, sched
    lp: dict = {"label": "one-day merged relaxation LP bound on the slow grid (E7's gap LP); its time is reported, "
                         "never a ratio (design §5.2.4)", "grid": LP_GRID, "merged": True, "time_limit_s": limit,
                "gate_mb": gate, "fits_gate": fits}
    if not fits:
        lp.update(skipped=True, skip_reason=f"the LP rule's estimate {est_mb:.0f} MB is not under the gate "
                                            f"{gate:.0f} MB (M18)", status=None, status_msg=None)
        for k in ("highs_model_status", "highs_model_status_text"):
            lp[k] = None
        for k in ("n_vars", "n_rows", "nnz", "build_s", "solve_s", "lp_s", "s_per_h", "objective",
                  "objective_over_bl0a", "solver_peak_rss_mb", "est_over_measured"):
            put(m, k, None, lp["skip_reason"])
        print(f"[e9] {job.id}: skipped ({lp['skip_reason']})", flush=True)
    else:
        sr = solve_lp(inst_m, sched_m, grid=LP_GRID, allow_large=True, time_limit_s=limit, return_plan=False)
        hs, ht = highs_status(sr.status_msg)
        size = sr.size or {}
        lp.update(skipped=False, method=sr.method, benchmark=sr.benchmark, status=sr.status,
                  status_msg=sr.status_msg, highs_model_status=hs, highs_model_status_text=ht,
                  dual_bound=sr.dual_bound, gap=sr.gap,
                  size={k: size.get(k) for k in ("n_vars", "n_int", "n_rows", "n_eq_rows", "nnz", "relaxed")})
        for k in ("n_vars", "n_rows", "nnz"):
            m[k] = size.get(k)
        m.update(build_s=sr.build_s, solve_s=sr.solve_s, lp_s=sr.build_s + sr.solve_s,
                 s_per_h=(sr.build_s + sr.solve_s) / hours, solver_peak_rss_mb=sr.peak_rss_mb)
        put(m, "objective", sr.objective, f"no objective ({sr.status_msg})")
        put(m, "objective_over_bl0a", None if sr.objective is None or not bl0a > 0 else sr.objective / bl0a,
            "no objective or BL0a not positive")
        print(f"[e9] {job.id}: {sr.status_msg}, objective {sr.objective}, build {sr.build_s:.1f} s, solve "
              f"{sr.solve_s:.1f} s", flush=True)
    peak, cg1 = _rss_mb(), cgroup_memory()
    m["peak_rss_mb"] = peak
    put(m, "scope_memory_peak_mb", cg1.get("memory_peak_mb") if _capped(cg1) else None, SCOPE_NOTE)
    if fits:
        put(m, "est_over_measured", est_mb / peak if peak > 0 else None, "no peak")
    memory = {"peak_rss_mb": peak, "scope_start": cg0, "scope_after_solve": cg1, "scope_capped": _capped(cg1),
              "cap_mb": CAP_MB, "fits_cap": _fits_cap(peak, cg1)}
    put(memory, "scope_memory_peak_mb", cg1.get("memory_peak_mb") if _capped(cg1) else None, SCOPE_NOTE)
    rec = {"meta": {**_job_meta(job), "loadavg_start": load}, "kind": "lp", "point": point, "base": p["base"],
           "config": BASES[p["base"]], "V": int(p["V"]), "llm_set": p["llm_set"], "c": c, "horizon_min": hz,
           "limit_s": p.get("limit_s"), "overrides": point_overrides(point, hz), "instance_hash": ih,
           "schedule_hash": sh, "schedule_source": "Lender.static_schedule (lender seed c): the realized schedule "
                                                    "under 'trace' with 'sell' and 'absorb'",
           "instance": sizes, "estimate": estimate, "lp": lp, "metrics": m, "memory": memory,
           "job_s": time.perf_counter() - t_job, "errors": []}
    outputs.dump(_plain(rec), run_path(out, job.id), compact=True)
    return {"runs": 1, "errors": [], "point": point, "c": c, "instance_hash": ih, "schedule_hash": sh,
            "skipped": not fits, "status": lp.get("status"), "highs_model_status": lp.get("highs_model_status"),
            "objective": m.get("objective"), "solve_s": m.get("solve_s"), "est_mb_lp": est_mb}


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    k = job.params["kind"]
    if k == "run":
        return run_point(job, outputs, out)
    if k == "lp":
        return run_lp(job, outputs, out)
    raise ValueError(f"unknown E9 job {job.id!r}")


def _sha256(p: Path) -> Optional[str]:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def manifest_extra(out) -> dict:
    """The instance hash of every point and alignment of the grid (§2.6; the LP points are run points) and the sha256
    of the input files."""
    d = design()
    hashes = {}
    for point in RUN_POINTS:
        for c in d["alignments"]:
            hashes[f"{point}:c={int(c)}"] = mc.instance_hash(build_point(point, int(c), d["horizon_min"])[0])
    files = [paths.CONFIGS / f for f in BASES.values()]
    files += [paths.ANALYSIS_OUT / f for f in ("a11_calibration.json", "a12_sim_inputs.json", "a12_minute_io.npz")]
    return {"instance_hashes": hashes, "design": {k: (list(v) if isinstance(v, tuple) else v) for k, v in d.items()},
            "reduced": d["reduced"], "B0_rule": m4.B0_RULE,
            "inputs_sha256": {_rel_repo(f): _sha256(f) for f in files}}


def _rel_repo(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(paths.REPO))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------- summary
def _outputs(out: Path, js: list) -> tuple:
    """({job id: run file} of the jobs whose record says 'ok', {job id: record}, ignored outputs, ok ids without a
    run file): a run file present while its job's record is not 'ok' (left by an earlier run) is not used and is
    listed (§2.6)."""
    recs = mc.read_records(out)
    data, ignored, no_file = {}, [], []
    for j in js:
        rec = recs.get(j.id) or {}
        path = run_path(out, j.id)
        if rec.get("status") != "ok":
            if path.is_file():
                ignored.append({"job": j.id, "status": rec.get("status"), "output": str(path.relative_to(out))})
            continue
        f = mc.read_json(path)
        if f is None:
            no_file.append(j.id)
        else:
            data[j.id] = f
    return data, recs, ignored, no_file


def run_fields(f: Mapping) -> dict:
    """by_alignment.<c> of one run file (RUN_METRICS, and for an A8 run t_a, aborted, certificate_case and
    certificate_held)."""
    e = (f.get("runs") or [{}])[0]
    acc = e.get("accountings") or {}
    tm = f.get("timing") or {}
    mem = f.get("memory") or {}
    rt = e.get("runtime") or {}
    x = {k: tm.get(k) for k in RUN_METRICS if k in tm}
    for k in ("job_s", "job_s_per_h"):
        x[k] = tm.get(k)
    x.update(peak_rss_mb=mem.get("peak_rss_mb"), scope_memory_peak_mb=mem.get("scope_memory_peak_mb"),
             cost_over_bl0a=acc.get("overflow_over_bl0a"), total_over_bl0a=acc.get("total_over_bl0a"),
             overflow_usd=acc.get("overflow_usd"), n_leases=e.get("n_leases"),
             n_alive_leases_max=rt.get("n_alive_leases_max"), n_invariant_failures=e.get("n_invariant_failures"))
    for k in RUN_METRICS:
        if x.get(k) is None:
            put(x, k, None, x.get(f"{k}_note") or tm.get(f"{k}_note") or mem.get(f"{k}_note")
                or f"no {k} in the run file")
    if f.get("tag") in A8_TAGS:
        a8 = e.get("a8") or {}
        x.update(t_a=a8.get("t_a"), aborted=bool(a8.get("aborted")), certificate_case=a8.get("certificate_case"),
                 certificate_held=(a8.get("certificate") or {}).get("held"), B0_rule=a8.get("B0_rule"),
                 B0_usd=a8.get("B0_usd"))
    x["steps_ok"] = (f.get("steps_check") or {}).get("ok")
    x["instance_hash"] = f.get("instance_hash")
    x["loadavg_start"] = (f.get("meta") or {}).get("loadavg_start")
    return x


def policy_entry(files: list, tag: str, note: str = "no run of this point and policy in the outputs") -> dict:
    """points.<point>.policies.<tag> (module docstring) over the run files of one point and policy."""
    by = {num_key(int(f["c"])): run_fields(f) for f in sorted(files, key=lambda f: int(f["c"]))}
    e = {"n_runs": len(by), "alignments": sorted(int(c) for c in by), "by_alignment": by}
    if not by:
        e["note"] = note
    a = agg_alignments(by, RUN_METRICS)
    e.update(median=a["median"], min=a["min"], max=a["max"])
    if tag in A8_TAGS:
        a8 = [(f.get("runs") or [{}])[0].get("a8") or {} for f in files]
        tas = sorted(int(x["t_a"]) for x in a8 if x.get("aborted") and x.get("t_a") is not None)
        put(e, "abort_share", sum(bool(x.get("aborted")) for x in a8) / len(a8) if a8 else None, note)
        e["t_a"] = tas
        e["certificates"] = m4.count_certificates([x for x in a8 if x])
    else:
        why = "unguarded policy (not an A8 tag): no abort, no certificate"
        for k in ("abort_share", "t_a", "certificates"):
            put(e, k, None, why)
    return e


def lp_fields(f: Mapping) -> dict:
    """lp.<point>.by_alignment.<c> of one LP run file."""
    m, lp = dict(f.get("metrics") or {}), f.get("lp") or {}
    x = {k: m.get(k) for k in LP_METRICS}
    for k in LP_METRICS:
        if x[k] is None:
            put(x, k, None, m.get(f"{k}_note") or f"no {k} in the LP file")
    x.update(status=lp.get("status"), status_msg=lp.get("status_msg"), highs_model_status=lp.get("highs_model_status"),
             highs_model_status_text=lp.get("highs_model_status_text"), skipped=bool(lp.get("skipped")),
             skip_reason=lp.get("skip_reason"), instance_hash=f.get("instance_hash"),
             schedule_hash=f.get("schedule_hash"), loadavg_start=(f.get("meta") or {}).get("loadavg_start"))
    return x


def lp_entry(files: list, note: str = "no LP of this point in the outputs") -> dict:
    by = {num_key(int(f["c"])): lp_fields(f) for f in sorted(files, key=lambda f: int(f["c"]))}
    e = {"n_runs": len(by), "alignments": sorted(int(c) for c in by), "by_alignment": by}
    if not by:
        e["note"] = note
    a = agg_alignments(by, LP_METRICS)
    e.update(median=a["median"], min=a["min"], max=a["max"])
    return e


def point_entry(point: str, run_files: list, lp_files: list) -> dict:
    """points.<point> (module docstring)."""
    base, V, llms = parse_point(point)
    ids, s_S = LLM_SETS[llms]
    e = {"base": base, "config": BASES[base], "menu": MENU[base], "V": V, "llm_set": llms, "llms": list(ids),
         "s_S": CONFIG_S_S if s_S is None else s_S, "lp_point": point in LP_POINTS}
    first = min(run_files + lp_files, key=lambda f: int(f["c"]), default=None)
    ins = (first or {}).get("instance") or {}
    note = "no output of this point"
    for k in ("n_sites", "n_sites_by_kind", "n_llms", "n_contracts", "n_revocable_contracts", "sites_x_llms"):
        put(e, k, ins.get(k), note)
    merged = [float(f["metrics"]["n_sites_merged"]) for f in lp_files
              if (f.get("metrics") or {}).get("n_sites_merged") is not None]
    put(e, "n_sites_merged", float(np.median(merged)) if merged else None,
        "no LP at this point" if point not in LP_POINTS else "no LP output of this point")
    by: dict = {}
    found: dict = {}
    for f in sorted(run_files + lp_files, key=lambda f: int(f["c"])):
        k = num_key(int(f["c"]))
        found.setdefault(k, set()).add(str(f.get("instance_hash")))
        if k in by:
            continue
        i = f.get("instance") or {}
        refs = f.get("references") or {}
        by[k] = {"instance_hash": f.get("instance_hash"), "bl0a_usd": i.get("bl0a_usd"),
                 "own_capacity_usd": refs.get("own_capacity_usd"), "n_clients": i.get("n_clients"),
                 "n_units": i.get("n_units"), "demand_load_h": i.get("demand_load_h")}
    for k, hs in found.items():               # every job of one point and alignment builds the same instance
        by[k]["one_instance"] = len(hs) == 1
        if len(hs) > 1:
            by[k]["instance_hashes_found"] = sorted(hs)
    e["by_alignment"] = by
    e["bl0a_usd"] = {k: v["bl0a_usd"] for k, v in by.items()}
    for k in ("n_clients", "n_units"):
        a = agg_alignments(by, (k,))
        e[k] = {"median": a["median"][k], "min": a["min"][k], "max": a["max"][k]}
        if a["median"][k] is None:
            e[k]["note"] = note
    e["policies"] = {t: policy_entry([f for f in run_files if f.get("tag") == t], t) for t in TAGS}
    return e


def _status(ok: bool, n: int) -> str:
    return ("pass" if ok else "fail") if n else "missing"


def check_jobs(kind: str, js: list, recs: Mapping, files: Mapping, no_file: list) -> dict:
    """The job part of E9-1 (kind 'run') and E9-4 (kind 'lp'): every job of the design grid has an 'ok' record and its
    run file; a record in a failure status (error, failed, oom_at_3G, wall_limit) fails, a job without an 'ok' output
    leaves the check missing."""
    want = [j for j in js if j.params["kind"] == kind]
    by_status: dict = {}
    failed, missing = [], []
    for j in want:
        st = (recs.get(j.id) or {}).get("status")
        by_status[str(st)] = by_status.get(str(st), 0) + 1
        if st in FAIL_STATUSES or (st is not None and st not in mc.STATUSES):
            r = recs.get(j.id) or {}
            failed.append({"job": j.id, "status": st, "rule": r.get("rule"), "error": r.get("error"),
                           "exit_code": r.get("exit_code")})
        elif j.id not in files:
            missing.append({"job": j.id, "status": st, "note": "ok record without its run file"
                            if j.id in no_file else "no 'ok' record"})
    return {"n_jobs": len(want), "jobs_by_status": dict(sorted(by_status.items())), "failed": failed[:50],
            "n_failed": len(failed), "missing": missing[:50], "n_missing": len(missing)}


def check_e9_1(js: list, recs: Mapping, files: Mapping, no_file: list) -> dict:
    """E9-1 (§5.9)."""
    jb = check_jobs("run", js, recs, files, no_file)
    runs = [f for f in files.values() if f.get("kind") == "run"]
    inv = [{"job": f["meta"]["job"], "n": (f.get("runs") or [{}])[0].get("n_invariant_failures"),
            "first": ((f.get("runs") or [{}])[0].get("invariant_failures_first") or [])[:2]} for f in runs
           if (f.get("runs") or [{}])[0].get("n_invariant_failures")]
    cap = [{"job": f["meta"]["job"], "peak_rss_mb": (f.get("memory") or {}).get("peak_rss_mb"),
            "scope_memory_peak_mb": (f.get("memory") or {}).get("scope_memory_peak_mb")} for f in runs
           if not (f.get("memory") or {}).get("fits_cap", False)]
    fail = bool(jb["n_failed"] or inv or cap)
    st = "fail" if fail else ("missing" if (jb["n_missing"] or not runs) else "pass")
    return {"status": st, "claim": CHECK_CLAIMS["E9-1"], **jb, "n_runs": len(runs), "invariant_failures": inv[:50],
            "n_runs_with_invariant_failures": len(inv), "over_cap": cap[:50], "n_over_cap": len(cap), "cap_mb": CAP_MB}


def check_e9_2(runs: list) -> dict:
    """E9-2 (§5.9) over the run files' step checks, recomputed from the stored runtime."""
    bad, worst = [], None
    for f in runs:
        rt = (f.get("runs") or [{}])[0].get("runtime") or {}
        g = (f.get("instance") or {}).get("grid") or {}
        ch = step_check(rt, g.get("T_slow", -1), g.get("T_fast", -1))
        if ch["excess_s"] is not None:
            worst = ch["excess_s"] if worst is None else max(worst, ch["excess_s"])
        if not ch["ok"]:
            bad.append({"job": f["meta"]["job"], "problems": ch["problems"]})
    grids = sorted({(int(((f.get("instance") or {}).get("grid") or {}).get("T_slow", -1)),
                     int(((f.get("instance") or {}).get("grid") or {}).get("T_fast", -1))) for f in runs})
    e = {"status": _status(not bad, len(runs)), "claim": CHECK_CLAIMS["E9-2"], "n_runs": len(runs),
         "failures": bad[:50], "n_failures": len(bad), "tolerance_s": STEP_TOL_S, "grids": [list(x) for x in grids]}
    put(e, "max_excess_s", worst, "no run")
    return e


def check_e9_3(runs: list) -> dict:
    """E9-3 (§5.9) over the A8 runs: a certificate is available in every run, and it is held in every run of
    Theorem W's proven cases; W(c) runs are counted and listed."""
    a8 = [(f, (f.get("runs") or [{}])[0].get("a8")) for f in runs if f.get("tag") in A8_TAGS]
    lab = [(f["meta"]["job"], r or {}) for f, r in a8]
    cnt = m4.count_certificates([r for _, r in lab])
    unavailable = [j for j, r in lab if not (r.get("certificate") or {}).get("available")]
    failures = [{"job": j, "case": r.get("certificate_case"), "t_a": r.get("t_a")} for j, r in lab
                if r.get("certificate_case") in m4.PROVEN_CASES
                and (r.get("certificate") or {}).get("held") is not True]
    wc = [{"job": j, "t_a": r.get("t_a"), "held": (r.get("certificate") or {}).get("held")} for j, r in lab
          if r.get("certificate_case") == "W(c)"]
    ok = not unavailable and not failures
    return {"status": _status(ok, len(lab)), "claim": CHECK_CLAIMS["E9-3"], "n_runs": len(lab), "certificates": cnt,
            "unavailable": unavailable[:50], "n_unavailable": len(unavailable), "failures": failures[:50],
            "n_failures": len(failures), "w_c_runs": wc[:50], "n_w_c": len(wc)}


def check_e9_4(js: list, recs: Mapping, files: Mapping, no_file: list) -> dict:
    """E9-4 (§5.9): every LP job of the grid solved to optimality (status 0 and HiGHS's model status 7) inside the
    cap; an LP skipped by the gate is not solved and fails."""
    jb = check_jobs("lp", js, recs, files, no_file)
    lps = [f for f in files.values() if f.get("kind") == "lp"]
    bad = []
    for f in lps:
        lp, mem = f.get("lp") or {}, f.get("memory") or {}
        why = []
        if lp.get("skipped"):
            why.append(lp.get("skip_reason") or "skipped")
        else:
            if lp.get("status") != 0:
                why.append(f"status {lp.get('status')!r} ({lp.get('status_msg')})")
            if lp.get("highs_model_status") != HIGHS_OPTIMAL:
                why.append(f"HiGHS model status {lp.get('highs_model_status')!r} "
                           f"({lp.get('highs_model_status_text')!r}) != {HIGHS_OPTIMAL} (Optimal)")
        if not mem.get("fits_cap", False):
            why.append(f"peak {mem.get('peak_rss_mb')} MB, scope {mem.get('scope_memory_peak_mb')} MB not under "
                       f"{CAP_MB:g} MB")
        if why:
            bad.append({"job": f["meta"]["job"], "problems": why})
    fail = bool(jb["n_failed"] or bad)
    st = "fail" if fail else ("missing" if (jb["n_missing"] or not lps) else "pass")
    return {"status": st, "claim": CHECK_CLAIMS["E9-4"], **jb, "n_lps": len(lps), "not_optimal": bad[:50],
            "n_not_optimal": len(bad), "gate_mb": LP_GATE_MB, "time_limit_s": LP_TIME_LIMIT_S}


def _ratio(a, b) -> Optional[float]:
    a, b = _num(a), _num(b)
    return None if a is None or b is None or not b > 0 else a / b


def check_e9_5(points: Mapping, lp: Mapping) -> dict:
    """E9-5 (§5.9, informative): per point and policy the medians against real time and the slot lengths, the setup,
    the peak memory; per LP point the LP's time per simulated hour against real time; the largest point of each
    menu with its ratios to real time."""
    per: dict = {}
    flags = {"slow_step_max_over_slot": [], "fast_step_p99_over_slot": [], "loops_over_real_time": []}
    for p, e in points.items():
        for t, pe in e["policies"].items():
            md = pe["median"]
            row = {"loops_s_per_h": md.get("loops_s_per_h"), "job_s_per_h": md.get("job_s_per_h"),
                   "slow_step_p99_s": md.get("slow_step_p99_s"), "slow_step_max_s": md.get("slow_step_max_s"),
                   "fast_step_p99_s": md.get("fast_step_p99_s"), "setup_s": md.get("setup_s"),
                   "peak_rss_mb": md.get("peak_rss_mb")}
            row["real_time_over_loops"] = _ratio(REAL_TIME_S_PER_H, md.get("loops_s_per_h"))
            row["real_time_over_job"] = _ratio(REAL_TIME_S_PER_H, md.get("job_s_per_h"))
            row["slow_step_p99_over_slot"] = _ratio(md.get("slow_step_p99_s"), SLOW_SLOT_S)
            row["slow_step_max_over_slot"] = _ratio(pe["max"].get("slow_step_max_s"), SLOW_SLOT_S)
            row["fast_step_p99_over_slot"] = _ratio(md.get("fast_step_p99_s"), FAST_SLOT_S)
            per.setdefault(p, {})[t] = row
            if (row["slow_step_max_over_slot"] or 0.0) > 1.0:
                flags["slow_step_max_over_slot"].append(f"{p}:{t}")
            if (row["fast_step_p99_over_slot"] or 0.0) > 1.0:
                flags["fast_step_p99_over_slot"].append(f"{p}:{t}")
            if (_num(pe["max"].get("loops_s_per_h")) or 0.0) > REAL_TIME_S_PER_H:
                flags["loops_over_real_time"].append(f"{p}:{t}")
    lp_rows = {p: {"s_per_h": e["median"].get("s_per_h"), "s_per_h_min": e["min"].get("s_per_h"),
                   "s_per_h_max": e["max"].get("s_per_h"),
                   "real_time_over_lp": _ratio(REAL_TIME_S_PER_H, e["median"].get("s_per_h")),
                   "peak_rss_mb": e["median"].get("peak_rss_mb"),
                   "objective_over_bl0a": e["median"].get("objective_over_bl0a"),
                   "instance_hash_equal_runs": {c: x.get("instance_hash_equal_runs")
                                                for c, x in e["by_alignment"].items()}} for p, e in lp.items()}
    largest = {}
    for base, p in LARGEST.items():
        e = points.get(p) or {}
        largest[MENU[base]] = {"point": p, "sites_x_llms": e.get("sites_x_llms"),
                               "policies": {t: {k: (per.get(p, {}).get(t) or {}).get(k) for k in
                                                ("loops_s_per_h", "job_s_per_h", "real_time_over_loops",
                                                 "real_time_over_job", "slow_step_max_over_slot")} for t in TAGS}}
    return {"status": "informative", "claim": CHECK_CLAIMS["E9-5"], "real_time_s_per_h": REAL_TIME_S_PER_H,
            "slow_slot_s": SLOW_SLOT_S, "fast_slot_s": FAST_SLOT_S, "per_point": per, "lp": lp_rows,
            "largest_point_by_menu": largest, "flags": flags}


def _meta(d: dict, js: list, files: dict, recs: dict, ignored: list) -> dict:
    ok = [j.id for j in js if j.id in files]
    st: dict = {}
    for j in js:
        s = str((recs.get(j.id) or {}).get("status"))
        st[s] = st.get(s, 0) + 1
    limits = {p: {t: run_limit_s(p, t) for t in TAGS} for p in RUN_POINTS}
    meta = {"exp": EXP, "spec": SPEC, "git_revision": mc.git_revision(), "versions": mc.versions(),
            "written": mc._now(), "reduced": d["reduced"], "host": platform.node(), "horizon_min": d["horizon_min"],
            "grid": {"run_points": list(RUN_POINTS), "lp_points": list(LP_POINTS), "bases": dict(BASES),
                     "menus": dict(MENU), "V": list(VS),
                     "llm_sets": {k: {"llms": list(v[0]), "s_S": CONFIG_S_S if v[1] is None else v[1]}
                                  for k, v in LLM_SETS.items()},
                     "alignments": list(d["alignments"]), "alignments_design": list(ALIGNMENTS),
                     "policy_seed": POLICY_SEED},
            "policies": {t: {"policy_id": v["id"], "params": f"ms4_common.sublet_params(inst, {v['inner']!r})"
                             if v["id"] == "A8" else v["params"], "style_key": v["style"], "a8": v["id"] == "A8"}
                         for t, v in TAGS.items()},
            "lp": {"style_key": LP_STYLE, "grid": LP_GRID, "merged": True, "time_limit_s": LP_TIME_LIMIT_S,
                   "gate_mb": LP_GATE_MB, "rule": "solved iff opt.milp.estimate_size parts.est_mb_lp < gate_mb (M18)",
                   "call": "opt.milp.solve_lp(merged_relaxation(inst, Lender.static_schedule()), grid 'slow', "
                           "allow_large, return_plan False)"},
            "limits": {"run": limits, "lp_s": LP_LIMIT_S, "timeout_grace_s": TIMEOUT_GRACE_S,
                       "kill_after_s": KILL_AFTER_S,
                       "rule": "run_e9.sh: timeout --foreground -k 30 (LIMIT + 60) per job; a nonzero exit classified "
                               "by ms3_common.classify_exit with LIMIT"},
            "real_time_s_per_h": REAL_TIME_S_PER_H, "slow_slot_s": SLOW_SLOT_S, "fast_slot_s": FAST_SLOT_S,
            "B0_rule": m4.B0_RULE, "info_class_reported_a8": m4.INFO_CLASS_REPORTED,
            "jobs_ok": len(ok), "jobs_missing": [j.id for j in js if j.id not in files],
            "jobs_by_status": dict(sorted(st.items())), "ignored_outputs": ignored,
            "hosts": sorted({(f.get("meta") or {}).get("host") for f in files.values()
                             if (f.get("meta") or {}).get("host")}),
            "loadavg_start": {jid: (f.get("meta") or {}).get("loadavg_start") for jid, f in files.items()}}
    if d["reduced"]:
        meta["reduced_note"] = (f"reduced job list ({REDUCED_ENV}=1): alignment 1, policy seed 0, a "
                                f"{REDUCED_HORIZON_MIN}-min horizon; not a result")
    return meta


def summary(out) -> dict:
    """summary.json and tables.md (module docstring) from the outputs of the jobs whose record is 'ok'."""
    out = Path(out)
    d = design()
    js = jobs()
    files, recs, ignored, no_file = _outputs(out, js)
    runs = [f for f in files.values() if f.get("kind") == "run"]
    lps = [f for f in files.values() if f.get("kind") == "lp"]
    points = {p: point_entry(p, [f for f in runs if f.get("point") == p], [f for f in lps if f.get("point") == p])
              for p in RUN_POINTS}
    lp = {p: lp_entry([f for f in lps if f.get("point") == p]) for p in LP_POINTS}
    for p, e in lp.items():                       # the LP on the runs' instance (§5.3): informative cross-check
        by_run = (points.get(p) or {}).get("policies") or {}
        for c, x in e["by_alignment"].items():
            hs = {((by_run.get(t) or {}).get("by_alignment") or {}).get(c, {}).get("instance_hash") for t in TAGS}
            hs.discard(None)
            put(x, "instance_hash_equal_runs", None if not hs else hs == {x.get("instance_hash")},
                "no run at this point and alignment")
    checks = {"E9-1": check_e9_1(js, recs, files, no_file), "E9-2": check_e9_2(runs), "E9-3": check_e9_3(runs),
              "E9-4": check_e9_4(js, recs, files, no_file), "E9-5": check_e9_5(points, lp)}
    summ = {"meta": _meta(d, js, files, recs, ignored), "points": points, "lp": lp, "checks": checks}
    mc.dump_json(summ, out / "summary.json")
    _write_tables(out / "tables.md", summ)
    return summ


def _fmt(x, digits: int = 4) -> str:
    if x is None:
        return "–"
    return f"{x:.{digits}g}" if isinstance(x, float) else str(x)


def _range(e: Mapping, k: str) -> str:
    return f"{_fmt(e['median'].get(k))} [{_fmt(e['min'].get(k))}, {_fmt(e['max'].get(k))}]"


def _write_tables(path: Path, s: dict) -> None:
    lines = ["# E9: scalability (design/sim_spec_ms5.md §5)", ""]
    if s["meta"].get("reduced"):
        lines += ["## Reduced run", "", s["meta"]["reduced_note"], ""]
    cols = ["point", "policy", "sites x LLMs", "units", "runs", "slow loop s/h", "fast loop s/h", "setup s",
            "slow P99 s", "slow max s", "fast P99 s", "peak MB", "cost / BL0a"]
    for base in BASES:
        rows = []
        for p, e in s["points"].items():
            if e["base"] != base:
                continue
            u = e["n_units"].get("median")
            u = int(u) if isinstance(u, float) and u.is_integer() else u
            for t, pe in e["policies"].items():
                rows.append([p, t, e.get("sites_x_llms"), u, pe["n_runs"],
                             _range(pe, "slow_loop_s_per_h"), _range(pe, "fast_loop_s_per_h"),
                             pe["median"].get("setup_s"), pe["median"].get("slow_step_p99_s"),
                             pe["max"].get("slow_step_max_s"), pe["median"].get("fast_step_p99_s"),
                             pe["median"].get("peak_rss_mb"), pe["median"].get("cost_over_bl0a")])
        lines += [f"## Runs on the {MENU[base]} menu ({BASES[base]}): median [min, max] over the alignments", "",
                  mc.md_table(cols, rows), ""]
    rows = [[p, e["n_runs"], e["median"].get("n_vars"), e["median"].get("nnz"), e["median"].get("n_sites_merged"),
             e["median"].get("est_mb_lp"), _range(e, "solve_s"), _range(e, "s_per_h"), e["median"].get("peak_rss_mb"),
             e["median"].get("objective_over_bl0a"),
             ", ".join(f"{c}: {x.get('highs_model_status_text') or ('skipped' if x.get('skipped') else '–')}"
                       for c, x in e["by_alignment"].items())]
            for p, e in s["lp"].items()]
    lines += ["## One-day merged LP bounds on the slow grid (e7r SML): median [min, max] over the alignments", "",
              mc.md_table(["point", "LPs", "vars", "nnz", "merged sites", "LP rule MB", "solve s", "s/h", "peak MB",
                           "objective / BL0a", "HiGHS status"], rows), ""]
    lines += ["## Checks (§5.9)", "", mc.md_table(["check", "status"], [[k, v.get("status")]
                                                                         for k, v in s["checks"].items()]), ""]
    mc.write_text("\n".join(lines) + "\n", path)


# ---------------------------------------------------------------- command line
def limits_text() -> str:
    """'<limit s> <job id>' per job, in run order (run_e9.sh reads it, §5.7)."""
    return "".join(f"{int(j.params['limit_s'])} {j.id}\n" for j in jobs())


def main(argv=None) -> int:
    """ms3_common.main's command line, plus --limits (the job limits for run_e9.sh)."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--limits" in args:
        ap = argparse.ArgumentParser(prog=f"python -m sublet.experiments.{EXP} --limits",
                                     description="print '<limit s> <job id>' per job (§5.7)")
        ap.add_argument("--limits", action="store_true", required=True)
        ap.parse_args(args)
        sys.stdout.write(limits_text())
        return 0
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=args, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
