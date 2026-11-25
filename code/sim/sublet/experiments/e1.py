"""E1: revocation exposure and the benchmark gap (design/sim_spec_ms3.md §4; deliverable D23).

E1(b) runs the PD variants and Sublet on E1's trace instance (configs/bench_e1.json on the slow grid with the
menu of M1, {s5_tau5_H60, s5_tau60_H0, protected}) at rho* in {1.5, 2, 4, 8, 16}, set by a transfer fee per LLM
(C10, C12: calib.beta_for_rho, recomputed per config seed), under the lender schedules 'adaptive' (main text),
'trace' and 'eager' (supplement), and bounds every run from below by Q39's rule (ms3_common.lb_record: the LP of
the run's realized schedule and the MILP of OPT(sigma, omega), or of OPT_eager under 'eager'). Under 'trace' the
bracket of OPT_eager / OPT(sigma, omega) (M4, M5) gives Fig. 5(a)'s trace points. The single-site tightness
family of C3-L1(c) at large T (§4.4) and the re-solve of c3_benchmark.json `b` (check E1-4) are two small jobs.
E1(a) has no runs (the figure script computes it, §4.2).

Jobs (§4.3, §4.4, §4.6; job ids by ms3_common.job_id; numbers as num_key, "1.5", "16", "0.2"):
  pool  e1:tight                                    tight_family.json (§4.4, E1-3, E1-4)
  pool  e1:core_b                                   core_b.json: the 60 solve_core calls on c3_benchmark.json
                                                    `b` (10 instances x 5 rates + OPT_eager; E1-4)
  pool  e1:cell:sched=S:rho=R:mu=U:c=C              one cell: every tag and policy seed, their LPs (one per
                                                    distinct realized schedule of the cell), the run files with
                                                    the realized schedule and the A8 certificates
  milp  e1:milp:bench=eager:rho=R:mu=U:c=C          OPT_eager (once per (rho*, mu, alignment))
  milp  e1:milp:sched=trace:rho=R:mu=1:c=C:bench=omega   OPT(sigma, omega) of the trace schedule (once per cell)
  milp  e1:milp:sched=adaptive:rho=R:mu=U:c=C:tag=T:p=P  OPT(sigma, omega) of one adaptive run
(The spec's ids `e1:milp:<cell>:omega` and `e1:milp:eager:...` have a part without '=' that §2.4's id format and
ms3_common.parse_job_id reject; 'bench=omega' and 'bench=eager' take their place.) A MILP job rebuilds the
instance from the cell's resolved config (runs/<cell>/cell.json) and the stored schedule and checks the instance
hash and the schedule hash (q44_study.instance_hash, schedule_hash) before solving; the eager MILP builds the
instance from (rho*, mu, c) and checks its hash against every cell record of the same (rho*, mu, c). Every MILP
runs with time_limit_s = ms3_common.milp_limit_s() (300 s, M3) and mip_rel_gap 1e-4 on the slow grid.

Grid (§4.3; M7, M8): main 'adaptive' x rho* x mu/beta~ = 1 x alignments c in {1, 2, 3, 4} (config seed c,
lender seed c) x the tags A2-r1, A2-th, A3-ref, Sublet (and A3-rot, supplement) x policy seeds {0, 1, 2};
supplement: the same under 'trace' and 'eager' (without A3-rot), and mu/beta~ in {0.2, 0.5, 2} at rho* = 4 under
'adaptive'. Tags (registry id, parameters; style key of design/sim_spec_ms3.md §8):
  A2-r1   A2 {"rbar": 1}                                            a2_r1 (its P / LB is a2_frac)
  A2-th   A2 {"rbar": "theory"}                                     a2_theory
  A3-ref  A3 {"x3": false, "x2": "reference", "reaction": "cold"}   a3
  Sublet  A8 {"inner": "BL5"}                                       sublet
  A3-rot  A3 {"x3": true, "x2": "reference", "reaction": "cold"}    a3_rot (supplement only)

Reduced job list (smoke runs and tests): MS3_E1_REDUCED=1 (run_e1.sh --reduced sets it) keeps the whole grid of
schedules, rho*, mu and tags but uses alignment c = 1 only, policy seed 0 only and the first 24 slow slots (2 h)
of each instance (instance.restrict_horizon(inst, 0, 24) after the build; the fee is computed on the full
instance). Default (unset or 0): the full list above.

Outputs under out/e1/ (§4.3, §2.6): runs/ (not versioned: runs/<sched>/rho=R/mu=U/c=C/cell.json and
<tag>_p<p>.json with the realized schedule), lb/ (versioned: lb/<cell>/lp_<schedule hash 16>.json, lb/<cell>/
milp_omega[_<tag>_p<p>].json, lb/opt_eager/rho=R/mu=U/c=C/milp_eager.json), tight_family.json, core_b.json,
summary.json, tables.md, manifest.json, jobs/, logs/, run_e1.log.

summary.json (every key path and its meaning; <rho> in {"1.5", "2", "4", "8", "16"}, <mu> in {"0.2", "0.5", "1",
"2"}, <c> in {"1", "2", "3", "4"}; every path of the design grid is present, a value the runs did not produce is
null with a '<key>_note'):
  meta                     exp, git_revision, written, reduced (bool; reduced_note), grid {schedules, rho_star,
                           mu_main, mu_sweep, rho_mu_sweep, alignments, alignments_design, policy_seeds,
                           policy_seeds_design, tags, horizon_slots, cells_found}, config, menu (the overrides of
                           M1), milp {limit_s, mip_rel_gap, grid}, tags {tag: {policy_id, params, style_key}},
                           fees.<rho>.<c> {beta_jl_usd {LLM: USD}, instance_rho {LLM: rho}, instance_rho_at {LLM:
                           [site, contract]}, base_rho {LLM: rho} (calibrated rho without fee)}, ignored_outputs
                           (outputs present whose job record is not 'ok', with job and status: not used, §2.4)
  ratios.<sched>.<rho>.<mu>.<tag>
                           n_runs, n_ratio (runs with a ratio_LB), ratio_LB and ratio_inc (metrics.aggregate over
                           the runs: n, median, p95, max, median_ci95), the flat copies median, median_ci95, p95,
                           max (of ratio_LB) and inc_median (median of ratio_inc) that Figs. 5(b) and sf_e1_sched
                           draw, share_exact (MILP gap <= 1e-4), max_gap, n_above_max2rho (ratio_LB >
                           max(2, rho*), E1-8), max2rho, alg_mean; for A2-r1 also P_over_LB (aggregate of A2's
                           fractional cost P over LB) and its copy a2_frac (the style key of Fig. 5(b))
  brackets.trace.<rho>.<c> OPT_eager / OPT(sigma, omega) under 'trace' at mu = 1 (M4, M5): point, lo, hi, exact,
                           gap_eager, gap_omega, rho_instance (max over the LLMs of calib.instance_rho), rho_star,
                           max2rho, eager / omega {LB, LB_source, incumbent, gap, milp_status, lp_status}
  certificates             runs, available, held, by_case {"W(a)" no abort, "W(b)" abort followed by FB at every
                           slot (Theorem W's proven cases), "W(c)" other aborts: {runs, held}}, failures (held false
                           in a proven case: bug), w_c_runs (reported), unavailable
  milp                     counts.<kind> {status: n} (kinds omega_adaptive, omega_trace, eager; statuses 0, 1, ...,
                           'wall_limit', 'oom_at_3G', 'error', 'missing', 'stale'), max_gap, wall_limit_kills (job
                           ids), n_jobs, stale (MILP job ids) and stale_lp_files: records whose instance or schedule
                           hash differs from the run's (left by an earlier run of the job), not used for any LB
  tight_family             rows at T = 3000 (T, rho, ratio) for Fig. 5(a) (also in tight_family.json)
  checks.E1-1 ... E1-8     status 'pass' | 'fail' | 'informative' | 'missing' | 'elsewhere' with the inputs of
                           each check of §4.6 (E1-1 is computed by the Fig. 2 script into figs/fig2.json; E1-7
                           reads e10/repro.json, E10-1)
tight_family.json: rows {T, rho, beta, OPT_none, OPT_eager, status_none, status_eager, gap_none, gap_eager, ratio,
  OPT_none_closed_form, OPT_eager_closed_form, ratio_closed_form, max2rho, size_none, size_eager, solve_none_s,
  solve_eager_s, peak_rss_mb}, reference_T60 (c3/out/c3_benchmark.json `a`), meta.
core_b.json: rows {seed, rho, rate, OPT_omega, OPT_eager, eager_over_omega, the reference values (*_ref), abs_diff,
  max2rho, within_bound, statuses, gaps}, max_eager_over_omega, max_abs_diff, meta.

Run from code/sim under the 3 GB cap through run_e1.sh (ms3_lib.sh); estimates (--estimate) use the time constants
of §11.1: engine 0.75 s and LP 2.26 s per run, MILP limit + 60 s, 0.49 s per core solve.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import copy
import math
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

from . import ms3_common as mc
from .ms3_common import Job, job_id, num_key, put

EXP = "e1"
CONFIG = "bench_e1.json"
# M1: E1's default menu without s5_tau5_H2 (unusable on the slow grid, M51 of the MS2 spec), on the slow grid
MENU = {"time.fast_slot_min": 5,
        "contracts": [{"id": "s5_tau5_H60", "tau_min": 5, "H_min": 60},
                      {"id": "s5_tau60_H0", "tau_min": 60, "H_min": 0},
                      {"id": "protected", "tau_min": None, "H_min": 0, "prepaid_min": 5}],
        "lender_defaults.menu": ["s5_tau5_H60", "s5_tau60_H0"]}
RHOS = (1.5, 2.0, 4.0, 8.0, 16.0)
MU_MAIN = 1.0
MUS_SWEEP = (0.2, 0.5, 2.0)
RHO_MU = 4.0                       # M7: the default point of the mu sweep
SCHEDS = ("adaptive", "trace", "eager")
ALIGNMENTS = (1, 2, 3, 4)          # M8: config seeds = lender seeds
POLICY_SEEDS = (0, 1, 2)
TAGS = {"A2-r1": ("A2", {"rbar": 1}),
        "A2-th": ("A2", {"rbar": "theory"}),
        "A3-ref": ("A3", {"x3": False, "x2": "reference", "reaction": "cold"}),
        "Sublet": ("A8", {"inner": "BL5"}),
        "A3-rot": ("A3", {"x3": True, "x2": "reference", "reaction": "cold"})}
MAIN_TAGS = ("A2-r1", "A2-th", "A3-ref", "Sublet")
ROT_TAG = "A3-rot"
STYLE_KEYS = {"A2-r1": "a2_r1", "A2-th": "a2_theory", "A3-ref": "a3", "Sublet": "sublet", "A3-rot": "a3_rot"}
MILP_GAP = 1e-4
BENCH_GRID = "slow"
TIGHT_T = (60, 600, 1500, 3000)
TIGHT_RHOS = (1.5, 2.0, 4.0, 8.0, 16.0)
TIGHT_D = 3                        # check_c3_benchmark.single_site: tau 2 + H 1
CORE_B_SEEDS = tuple(range(10))
TOL = 1e-9
P1_TOL = 1e-6                      # E1-6: design §5.2.4 flags every P1 ratio below 1 - 1e-6
REDUCED_ENV = "MS3_E1_REDUCED"
REDUCED_HORIZON_SLOTS = 24         # 2 h of 5-min slots
# time constants of §11.1 (seconds; MS3-spec measurements under load)
EST_ENGINE_S = 0.75
EST_LP_S = 2.26
EST_CORE_SOLVE_S = 0.49


# ---------------------------------------------------------------- grid and jobs
def design() -> dict:
    """The job grid: the full grid of §4.3, or the reduced one with MS3_E1_REDUCED=1 (module docstring)."""
    reduced = os.environ.get(REDUCED_ENV, "0") == "1"
    return {"reduced": reduced, "alignments": (1,) if reduced else ALIGNMENTS,
            "policy_seeds": (0,) if reduced else POLICY_SEEDS,
            "horizon_slots": REDUCED_HORIZON_SLOTS if reduced else None}


def cell_tags(sched: str, mu: float) -> tuple:
    return MAIN_TAGS + ((ROT_TAG,) if sched == "adaptive" and float(mu) == MU_MAIN else ())


def grid_cells(alignments=ALIGNMENTS) -> list[tuple]:
    """(sched, rho*, mu, c) of every cell, the headline first (§4.3)."""
    out = [(s, r, MU_MAIN, c) for s in SCHEDS for r in RHOS for c in alignments]
    out += [("adaptive", RHO_MU, mu, c) for mu in MUS_SWEEP for c in alignments]
    return out


def eager_points(alignments=ALIGNMENTS) -> list[tuple]:
    """(rho*, mu, c) of the OPT_eager MILPs: once per (rho*, mu, alignment) of the grid."""
    return [(r, MU_MAIN, c) for r in RHOS for c in alignments] + [(RHO_MU, mu, c) for mu in MUS_SWEEP
                                                                  for c in alignments]


def cell_id(sched, rho, mu, c) -> str:
    return job_id(EXP, "cell", sched=sched, rho=rho, mu=mu, c=int(c))


def milp_omega_id(sched, rho, mu, c, tag=None, p=None) -> str:
    if sched == "adaptive":
        return job_id(EXP, "milp", sched=sched, rho=rho, mu=mu, c=int(c), tag=tag, p=int(p))
    return job_id(EXP, "milp", sched=sched, rho=rho, mu=mu, c=int(c), bench="omega")


def milp_eager_id(rho, mu, c) -> str:
    return job_id(EXP, "milp", bench="eager", rho=rho, mu=mu, c=int(c))


def jobs() -> list[Job]:
    d = design()
    al, seeds = d["alignments"], d["policy_seeds"]
    milp_s = mc.wall_timeout_s()
    common = {"horizon_slots": d["horizon_slots"], "policy_seeds": list(seeds)}
    out = [Job(job_id(EXP, "tight"), "pool", {"T": list(TIGHT_T), "rho": list(TIGHT_RHOS)},
               est_s=2 * len(TIGHT_T) * len(TIGHT_RHOS) * EST_CORE_SOLVE_S),
           Job(job_id(EXP, "core_b"), "pool", {"seeds": list(CORE_B_SEEDS)},
               est_s=len(CORE_B_SEEDS) * 6 * EST_CORE_SOLVE_S)]
    cells = grid_cells(al)
    for (s, r, mu, c) in cells:
        tags = cell_tags(s, mu)
        n = len(tags) * len(seeds)
        n_lp = n if s == "adaptive" else 1
        out.append(Job(cell_id(s, r, mu, c), "pool",
                       {"sched": s, "rho": r, "mu": mu, "c": int(c), "tags": list(tags), **common},
                       est_s=n * EST_ENGINE_S + n_lp * EST_LP_S))
    for (r, mu, c) in eager_points(al):
        out.append(Job(milp_eager_id(r, mu, c), "milp", {"bench": "eager", "rho": r, "mu": mu, "c": int(c),
                                                         **common}, est_s=milp_s))
    for (s, r, mu, c) in cells:
        if s == "trace":
            out.append(Job(milp_omega_id(s, r, mu, c), "milp", {"bench": "omega", "sched": s, "rho": r, "mu": mu,
                                                                "c": int(c), **common}, est_s=milp_s))
    for (s, r, mu, c) in cells:
        if s != "adaptive":
            continue
        for tag in cell_tags(s, mu):
            for p in seeds:
                out.append(Job(milp_omega_id(s, r, mu, c, tag, p), "milp",
                               {"bench": "omega", "sched": s, "rho": r, "mu": mu, "c": int(c), "tag": tag,
                                "p": int(p), **common}, est_s=milp_s))
    return out


# ---------------------------------------------------------------- paths
def cell_rel(sched, rho, mu, c) -> Path:
    return Path(sched) / f"rho={num_key(rho)}" / f"mu={num_key(mu)}" / f"c={int(c)}"


def cell_file(out: Path, sched, rho, mu, c) -> Path:
    return Path(out) / "runs" / cell_rel(sched, rho, mu, c) / "cell.json"


def run_file(out: Path, sched, rho, mu, c, tag, p) -> Path:
    return Path(out) / "runs" / cell_rel(sched, rho, mu, c) / f"{tag}_p{int(p)}.json"


def lp_file(out: Path, sched, rho, mu, c, sh: str) -> Path:
    return Path(out) / "lb" / cell_rel(sched, rho, mu, c) / f"lp_{sh[:16]}.json"


def milp_omega_file(out: Path, sched, rho, mu, c, tag=None, p=None) -> Path:
    name = f"milp_omega_{tag}_p{int(p)}.json" if sched == "adaptive" else "milp_omega.json"
    return Path(out) / "lb" / cell_rel(sched, rho, mu, c) / name


def milp_eager_file(out: Path, rho, mu, c) -> Path:
    return Path(out) / "lb" / "opt_eager" / f"rho={num_key(rho)}" / f"mu={num_key(mu)}" / f"c={int(c)}" / \
        "milp_eager.json"


# ---------------------------------------------------------------- instances (§4.3, M1, M2, C10, C12)
def overrides(mu: float, fees: Optional[dict] = None) -> dict:
    """The instance overrides of a cell: M1's menu on the slow grid, mu/beta~ (M2: mu includes the fee, C10) and
    the per-LLM fee map (costs.beta_jl_usd) once known."""
    ov = copy.deepcopy(MENU)
    ov["stranding.mu_over_beta_tilde"] = float(mu)
    if fees is not None:
        ov["costs.beta_jl_usd"] = {k: float(v) for k, v in fees.items()}
    return ov


def run_spec(tag: str, sched: str, ov: dict, c: int, seeds=(0,)) -> dict:
    """The validated run spec of one tag on one cell (drivers.run.load_run_spec): bench_e1 with the overrides,
    the cell's lender schedule (I1, 'sell', violations absorbed from the config), invariant checks on."""
    from ..drivers import run as drun
    pid, params = TAGS[tag] if tag in TAGS else (tag, {})
    return drun.load_run_spec({"schema_version": 1, "name": tag.replace("-", "_") if tag in TAGS else tag,
                               "instance": CONFIG, "overrides": copy.deepcopy(ov),
                               "lender_model": {"schedule": sched}, "engine": {"check_invariants": True},
                               "policy": {"id": pid, "params": copy.deepcopy(params)},
                               "seeds": {"config": [int(c)], "lender": "config", "policy": [int(p) for p in seeds]}})


def fees_for(rho: float, mu: float, c: int) -> tuple[dict, dict]:
    """(fee map {LLM id: USD}, calibrated rho without fee): calib.beta_for_rho on the instance of config seed c
    built without fee (the fee depends on the seed through the load-scenario draw, §4.3)."""
    from .. import calib
    from ..drivers import run as drun
    inst0, _, _ = drun.build(run_spec("BL0a", "trace", overrides(mu), c), int(c))
    return calib.beta_for_rho(inst0, float(rho)), _rho_json(calib.instance_rho(inst0))


def _rho_json(r: dict) -> dict:
    return {k: (None if v is None else {"rho": float(v[0]), "site": v[1], "contract": v[2]}) for k, v in r.items()}


def cell_instance(ov: dict, sched: str, c: int, horizon_slots: Optional[int]):
    """(inst, model, ecfg, instance_rho on the full instance) of a cell from its resolved overrides; with
    horizon_slots the instance is restrict_horizon(inst, 0, horizon_slots) (reduced runs)."""
    from .. import calib
    from ..drivers import run as drun
    from ..instance import restrict_horizon
    inst, model, ecfg = drun.build(run_spec("BL0a", sched, ov, c), int(c))
    rho_inst = _rho_json(calib.instance_rho(inst))
    if horizon_slots:
        inst = restrict_horizon(inst, 0, int(horizon_slots))
    if not ecfg.check_invariants:
        raise RuntimeError("E1 runs need check_invariants=True (§2.2)")
    return inst, model, ecfg, rho_inst


def rho_check(rho_inst: dict, target: float) -> dict:
    """E1-2 on one instance: instance_rho after beta_for_rho equals rho* for every LLM to 1e-9."""
    diffs = {k: (None if v is None else abs(v["rho"] - float(target))) for k, v in rho_inst.items()}
    ok = all(d is not None and d <= TOL * max(1.0, float(target)) for d in diffs.values())
    return {"target": float(target), "abs_diff": diffs, "pass": bool(ok)}


# ---------------------------------------------------------------- small records
def _solve_record(sr, **extra) -> dict:
    size = sr.size or {}
    return {**extra, "method": sr.method, "benchmark": sr.benchmark, "grid": sr.grid, "status": sr.status,
            "status_msg": sr.status_msg, "objective": sr.objective, "dual_bound": sr.dual_bound, "gap": sr.gap,
            "size": {k: size.get(k) for k in ("n_vars", "n_int", "n_rows", "nnz") if k in size},
            "build_s": sr.build_s, "solve_s": sr.solve_s, "peak_rss_mb": sr.peak_rss_mb,
            "git_revision": mc.git_revision()}


def _slim(rep: dict) -> dict:
    """The scalar entries of a policy report (the run file keeps these; A8's certificate is stored apart)."""
    return {k: v for k, v in (rep or {}).items() if isinstance(v, (bool, int, float, str)) or v is None}


CERT_KEYS = ("available", "held", "aborted", "t_a", "fb_after_t_a", "proven_case", "core_bound_ok", "e_mode_ok",
             "e_mode_reserve_ok", "wind_down_ok", "m_ok", "reserve", "ALG_T", "core_bound_rhs", "core_bound_slack",
             "test", "missing")


def cert_case(c: Optional[dict]) -> str:
    """Theorem W's case of a certificate: 'W(a)' (no abort), 'W(b)' (abort, S follows FB from t_a on: proven),
    'W(c)' (another abort), 'unavailable'."""
    if not c or not c.get("available"):
        return "unavailable"
    if not c.get("aborted"):
        return "W(a)"
    return "W(b)" if c.get("proven_case") else "W(c)"


def _rel(p, base) -> str:
    try:
        return str(Path(p).resolve().relative_to(Path(base).resolve()))
    except ValueError:
        return str(p)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _jsonish(x):
    """metrics._jsonable (non-finite floats as strings) for the free-form parts of run files."""
    from ..metrics import _jsonable
    return _jsonable(x)


# ---------------------------------------------------------------- job: one cell
def run_cell(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """Every tag and policy seed of one cell (§4.3): engine runs, the A8 certificates, one LP per distinct
    realized schedule, the run files and the cell record."""
    from ..drivers import run as drun
    from ..engine import simulate
    from ..algos import registry
    from ..opt.milp import solve_lp
    from . import q44_study as q44
    p = job.params
    sched, rho, mu, c = p["sched"], float(p["rho"]), float(p["mu"]), int(p["c"])
    hz = p.get("horizon_slots")
    t_start = time.perf_counter()
    fees, base_rho = fees_for(rho, mu, c)
    ov = overrides(mu, fees)
    inst, model, ecfg, rho_inst = cell_instance(ov, sched, c, hz)
    ih = mc.instance_hash(inst)
    errors: list = []
    rows, lps, first = [], {}, {}
    for tag in p["tags"]:
        pid, params = TAGS[tag]
        spec = run_spec(tag, sched, ov, c, p["policy_seeds"])
        for ps in p["policy_seeds"]:
            def one(tag=tag, pid=pid, params=params, spec=spec, ps=ps):
                t0 = time.perf_counter()
                pol = drun.make_policy(spec, inst)
                _, imeta = drun.driver_inputs(pid, params, inst)
                res = simulate(inst, pol, model, ecfg, lender_seed=c, policy_seed=int(ps))
                wall = time.perf_counter() - t0
                rep = res.metrics.get("policy") or {}
                rp = {**params, **(pol.params() or {})}
                sh = mc.schedule_hash(res.schedule)
                cert = q44.certificate(res, inst, rep, core_exact=False) if pid == "A8" else None
                alg = float(res.components["total"])
                rv = drun.ratio_validity(BENCH_GRID, inst, model)
                p1 = bool(q44.plan_class_p1(res, inst))
                if sh not in lps:
                    t1 = time.perf_counter()
                    lp = solve_lp(inst, res.schedule, grid=BENCH_GRID, allow_large=True, return_plan=False)
                    rec = _solve_record(lp, job=job.id, kind="lp", sched=sched, rho_star=rho, mu=mu, c=c,
                                        instance_hash=ih, schedule_hash=sh, wall_s=time.perf_counter() - t1)
                    path = lp_file(out, sched, rho, mu, c, sh)
                    outputs.dump(rec, path)
                    lps[sh] = {"file": _rel(path, out), "status": lp.status, "objective": lp.objective}
                info = registry.info_class(pid, rp, model.information)
                run = {"meta": {"exp": EXP, "job": job.id, "tag": tag, "policy_id": pid, "params": rp,
                                "style_key": STYLE_KEYS[tag], "info_class": info, "driver_inputs": imeta,
                                "seeds": dict(res.seeds), "sched": sched, "rho_star": rho, "mu": mu, "c": c,
                                "horizon_slots": hz, "instance_hash": ih, "schedule_hash": sh,
                                "git_revision": mc.git_revision(), "versions": mc.versions()},
                       "ALG": alg, "components": dict(res.components), "grouped": q44.grouped(res.components),
                       "invariant_failures": list(res.invariant_failures)[:20],
                       "n_invariant_failures": len(res.invariant_failures),
                       "gpu_only_lease_slots": int(res.metrics.get("gpu_only_lease_slots", 0)),
                       "plan_class_p1": p1, "ratio_validity": rv, "intensity": q44.intensity(res, inst),
                       "leases": q44.lease_stats(res, inst), "report": _slim(rep),
                       "P": rep.get("P") if pid == "A2" else None, "certificate": cert,
                       "schedule": {"mode": res.schedule.mode, "realized": bool(res.schedule.realized),
                                    "R": [np.asarray(r, dtype=np.int64).tolist() for r in res.schedule.R]},
                       "engine_wall_s": res.runtime.get("wall_s"), "wall_s": wall}
                path = run_file(out, sched, rho, mu, c, tag, ps)
                outputs.dump(_jsonish(run), path, compact=True)
                row = {"tag": tag, "policy_id": pid, "p": int(ps), "file": _rel(path, out), "ALG": alg,
                       "P": run["P"], "schedule_hash": sh, "lp_file": lps[sh]["file"], "ratio_validity": rv,
                       "plan_class_p1": p1, "n_invariant_failures": len(res.invariant_failures),
                       "gpu_only_lease_slots": run["gpu_only_lease_slots"],
                       "n_announcements": int(sum(len(r) for r in res.schedule.R)), "wall_s": wall,
                       "certificate": None if cert is None else {k: cert.get(k) for k in CERT_KEYS},
                       "certificate_case": None if cert is None else cert_case(cert)}
                rows.append(row)
                first.setdefault("schedule", res.schedule)
                print(f"[e1] {job.id} {tag} p{ps}: ALG {alg:.4f}, {row['n_announcements']} announcements, "
                      f"{wall:.2f} s", flush=True)
            mc.try_run(errors, f"{tag}_p{ps}", one)
    core_exact = None
    if sched == "trace" and "schedule" in first:
        # E1-4: whether the trace instance has an exact core export (expected false: lambda > 0, mu > 0); an
        # instance that to_core cannot export at all has none (recorded, not an error of the job)
        def export():
            from ..instance import InstanceError, to_core
            try:
                ex = to_core(inst, first["schedule"], not_offered="big_m")
            except InstanceError as err:
                return {"exact": False, "exportable": False, "why": f"{type(err).__name__}: {err}"}
            return {"exact": bool(ex.exact), "exportable": True, "notes": list(ex.notes)[:10]}
        core_exact = mc.try_run(errors, "to_core", export)
    rec = {"job": job.id, "exp": EXP, "sched": sched, "rho_star": rho, "mu": mu, "c": c,
           "rho_key": num_key(rho), "mu_key": num_key(mu), "config": CONFIG, "overrides": ov, "fees": fees,
           "base_rho": base_rho, "instance_rho": rho_inst, "rho_check": rho_check(rho_inst, rho),
           "horizon_slots": hz, "instance_hash": ih, "lender_model": {"schedule": model.schedule,
                                                                     "information": model.information,
                                                                     "on_unavailable": model.on_unavailable,
                                                                     "violations": model.violations},
           "tags": list(p["tags"]), "policy_seeds": list(p["policy_seeds"]), "runs": rows, "lps": lps,
           "schedule_hashes": sorted({r["schedule_hash"] for r in rows}), "core_export": core_exact,
           "errors": [{k: v for k, v in e.items() if k != "traceback"} for e in errors],
           "git_revision": mc.git_revision(), "versions": mc.versions(), "wall_s": time.perf_counter() - t_start}
    outputs.dump(rec, cell_file(out, sched, rho, mu, c))
    return {"runs": len(rows), "errors": errors, "lps": len(lps), "instance_hash": ih}


# ---------------------------------------------------------------- job: MILPs
def _schedule_of(run: dict):
    from ..types import Schedule
    s = run["schedule"]
    return Schedule(s["mode"], tuple(np.asarray(r, dtype=np.int64) for r in s["R"]), bool(s.get("realized", True)))


def run_milp(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One MILP (§4.3): OPT_eager of (rho*, mu, c), or OPT(sigma, omega) of a trace cell or of one adaptive run,
    on the rebuilt instance after the hash checks."""
    from ..opt.milp import solve_eager, solve_opt
    p = job.params
    rho, mu, c, hz = float(p["rho"]), float(p["mu"]), int(p["c"]), p.get("horizon_slots")
    limit = mc.milp_limit_s()
    t0 = time.perf_counter()
    if p["bench"] == "eager":
        fees, _ = fees_for(rho, mu, c)
        ov = overrides(mu, fees)
        inst, _, _, _ = cell_instance(ov, "eager", c, hz)
        ih = mc.instance_hash(inst)
        checked = []
        for s in SCHEDS:
            cr = mc.read_json(cell_file(out, s, rho, mu, c))
            if cr is not None:
                if cr["instance_hash"] != ih:
                    raise RuntimeError(f"instance hash {ih[:12]} differs from the cell record {s} "
                                       f"({cr['instance_hash'][:12]})")
                checked.append(s)
        sr = solve_eager(inst, grid=BENCH_GRID, time_limit_s=limit, mip_rel_gap=MILP_GAP, allow_large=True,
                         return_plan=False)
        sh, path, extra = None, milp_eager_file(out, rho, mu, c), {"cells_checked": checked}
    else:
        sched = p["sched"]
        cr = mc.read_json(cell_file(out, sched, rho, mu, c))
        if cr is None:
            raise FileNotFoundError(f"no cell record {cell_file(out, sched, rho, mu, c)} (run the cell job first)")
        inst, _, _, _ = cell_instance(cr["overrides"], sched, c, cr.get("horizon_slots"))
        ih = mc.instance_hash(inst)
        if ih != cr["instance_hash"]:
            raise RuntimeError(f"rebuilt instance hash {ih[:12]} differs from the cell's {cr['instance_hash'][:12]}")
        if sched == "adaptive":
            row = next((r for r in cr["runs"] if r["tag"] == p["tag"] and r["p"] == int(p["p"])), None)
            if row is None:
                raise FileNotFoundError(f"cell {cr['job']} has no run {p['tag']} p{p['p']}")
        else:
            if len(cr["schedule_hashes"]) != 1:
                raise RuntimeError(f"trace cell {cr['job']} has {len(cr['schedule_hashes'])} realized schedules")
            row = cr["runs"][0]
        run = mc.read_json(Path(out) / row["file"])
        if run is None:
            raise FileNotFoundError(f"run file {row['file']} missing")
        sched_obj = _schedule_of(run)
        sh = mc.schedule_hash(sched_obj)
        if sh != row["schedule_hash"]:
            raise RuntimeError(f"stored schedule hash {sh[:12]} differs from the record's {row['schedule_hash'][:12]}")
        sr = solve_opt(inst, sched_obj, grid=BENCH_GRID, time_limit_s=limit, mip_rel_gap=MILP_GAP,
                       allow_large=True, return_plan=False)
        path = milp_omega_file(out, sched, rho, mu, c, p.get("tag"), p.get("p"))
        extra = {"tag": p.get("tag"), "p": p.get("p"), "run_file": row["file"], "ALG": row["ALG"]}
    rec = _solve_record(sr, job=job.id, kind="milp", bench=p["bench"], sched=p.get("sched"), rho_star=rho, mu=mu,
                        c=c, instance_hash=ih, schedule_hash=sh, time_limit_s=limit, mip_rel_gap=MILP_GAP,
                        wall_s=time.perf_counter() - t0, **extra)
    outputs.dump(rec, path)
    print(f"[e1] {job.id}: status {sr.status} ({sr.status_msg}), objective {sr.objective}, dual bound "
          f"{sr.dual_bound}, gap {sr.gap}, {rec['size']}, {rec['wall_s']:.1f} s", flush=True)
    return {"runs": 0, "status": sr.status, "objective": sr.objective, "dual_bound": sr.dual_bound, "gap": sr.gap,
            "n_vars": rec["size"].get("n_vars"), "nnz": rec["size"].get("nnz")}


# ---------------------------------------------------------------- jobs: tight family and core_b (§4.4, E1-4)
def tight_rows(Ts=TIGHT_T, rhos=TIGHT_RHOS) -> list[dict]:
    """C3-L1(c)'s single-site family (check_c3_benchmark.single_site: tau 2, H 1, a 1, D 3, beta = (rho - 1) D,
    q 1e3, one always-active client) by opt.milp.solve_core with omega empty (OPT, no reclaims) and omega_all
    (OPT_eager), with the closed forms OPT = beta + a T and OPT_eager = ceil(T / D) (beta + a D)."""
    from ..opt.milp import solve_core
    from ..paths import import_ref
    cb = import_ref("check_c3_benchmark")
    rows = []
    for T in Ts:
        for rho in rhos:
            beta = (float(rho) - 1.0) * TIGHT_D
            I = cb.single_site(beta, T=int(T))
            a = float(I.a[0, 0])
            t0 = time.perf_counter()
            om = solve_core(I, [np.zeros(0, dtype=np.int64)])
            t1 = time.perf_counter()
            eg = solve_core(I, [np.arange(int(T), dtype=np.int64)])
            t2 = time.perf_counter()
            none_cf = beta + a * T
            eager_cf = math.ceil(T / TIGHT_D) * (beta + a * TIGHT_D)
            rows.append({"T": int(T), "rho": float(rho), "beta": beta, "a": a, "D": TIGHT_D, "q": float(I.q),
                         "OPT_none": om.objective, "OPT_eager": eg.objective, "status_none": om.status,
                         "status_eager": eg.status, "gap_none": om.gap, "gap_eager": eg.gap,
                         "ratio": eg.objective / om.objective, "OPT_none_closed_form": none_cf,
                         "OPT_eager_closed_form": eager_cf, "ratio_closed_form": eager_cf / none_cf,
                         "max2rho": max(2.0, float(rho)),
                         "size_none": {k: (om.size or {}).get(k) for k in ("n_vars", "nnz")},
                         "size_eager": {k: (eg.size or {}).get(k) for k in ("n_vars", "nnz")},
                         "solve_none_s": t1 - t0, "solve_eager_s": t2 - t1, "peak_rss_mb": eg.peak_rss_mb})
    return rows


def tight_check(rows: list[dict], ref_a: list[dict]) -> dict:
    """E1-3: at T = 60 the rows equal c3_benchmark.json `a` (OPT_eager, OPT_none, OPTeager_over_OPTnone) and at
    every T the MILP values equal the closed forms, to 1e-9 with status 0 and gap <= 1e-9; plus E1-4's bound
    OPT_eager / OPT <= max(2, rho) on these exact instances."""
    ref = {float(r["rho"]): r for r in ref_a}
    d_ref, d_cf, bad = 0.0, 0.0, []
    for r in rows:
        if r["T"] == 60 and r["rho"] in ref:
            x = ref[r["rho"]]
            for k, kr in (("OPT_eager", "OPT_eager"), ("OPT_none", "OPT_none"), ("ratio", "OPTeager_over_OPTnone")):
                d_ref = max(d_ref, abs(float(r[k]) - float(x[kr])))
        for k, kc in (("OPT_none", "OPT_none_closed_form"), ("OPT_eager", "OPT_eager_closed_form")):
            d_cf = max(d_cf, abs(float(r[k]) - float(r[kc])) / max(1.0, abs(float(r[kc]))))
        if r["status_none"] != 0 or r["status_eager"] != 0 or (r["gap_none"] or 0) > TOL or (r["gap_eager"] or 0) > TOL:
            bad.append({"T": r["T"], "rho": r["rho"], "status": [r["status_none"], r["status_eager"]],
                        "gap": [r["gap_none"], r["gap_eager"]]})
    n60 = sum(1 for r in rows if r["T"] == 60 and r["rho"] in ref)
    above = [{"T": r["T"], "rho": r["rho"], "ratio": r["ratio"]} for r in rows if r["ratio"] > r["max2rho"] + TOL]
    ok = n60 == len(ref) and d_ref <= TOL and d_cf <= TOL and not bad
    return {"pass": bool(ok), "n_rows": len(rows), "n_T60_compared": n60, "max_abs_diff_T60_vs_reference": d_ref,
            "max_rel_diff_closed_form": d_cf, "not_optimal_or_gap": bad, "above_max2rho": above}


def run_tight(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    from ..paths import C3
    rows = tight_rows()
    ref = mc.read_json(C3 / "out" / "c3_benchmark.json") or {}
    chk = tight_check(rows, ref.get("a") or [])
    outputs.dump({"meta": {"exp": EXP, "job": job.id, "instance": "check_c3_benchmark.single_site(beta, T) "
                           "(tau 2, H 1, a 1, D 3, beta = (rho - 1) D, q 1e3)",
                           "solver": "opt.milp.solve_core (mip_rel_gap 1e-9)", "git_revision": mc.git_revision(),
                           "versions": mc.versions(), "written": _now()},
                  "rows": rows, "reference_T60": ref.get("a"), "check_E1_3": chk},
                 Path(out) / "tight_family.json")
    return {"runs": 0, "rows": len(rows), "E1_3_pass": chk["pass"]}


def core_b_rows(seeds=CORE_B_SEEDS) -> list[dict]:
    """The random core instances of c3_benchmark.json `b` (repro_c3_benchmark.instance and .omega, the rates of
    check_c3_benchmark.run_b) re-solved by solve_core: OPT(sigma, omega) per rate and OPT_eager per instance."""
    from ..opt.milp import solve_core
    from ..paths import C3
    from .repro_c3_benchmark import RATES, instance, omega
    ref = (mc.read_json(C3 / "out" / "c3_benchmark.json") or {}).get("b") or []
    refs = {int(b["seed"]): b for b in ref}
    rows = []
    for s in seeds:
        I = instance(int(s))
        t0 = time.perf_counter()
        eg = solve_core(I, [np.arange(int(I.T), dtype=np.int64)] * int(I.a.shape[0]))
        te = time.perf_counter() - t0
        rb = refs.get(int(s)) or {}
        for i, rate in enumerate(RATES):
            om = omega(I, int(s), rate)
            t1 = time.perf_counter()
            sr = solve_core(I, om)
            rr = (rb.get("per_rate") or [{}] * len(RATES))[i] if rb.get("per_rate") else {}
            e_o = eg.objective / sr.objective if sr.objective else None
            rho = rb.get("rho")
            row = {"seed": int(s), "rho": rho, "rate": float(rate), "OPT_omega": sr.objective,
                   "OPT_eager": eg.objective, "eager_over_omega": e_o,
                   "OPT_omega_ref": rr.get("OPT_omega"), "OPT_eager_ref": rb.get("OPT_eager"),
                   "eager_over_omega_ref": rr.get("eager_over_omega"),
                   "status_omega": sr.status, "status_eager": eg.status, "gap_omega": sr.gap, "gap_eager": eg.gap,
                   "status_ref": rr.get("status"), "solve_omega_s": time.perf_counter() - t1, "solve_eager_s": te}
            row["abs_diff"] = (abs(e_o - float(rr["eager_over_omega"])) if e_o is not None
                               and rr.get("eager_over_omega") is not None else None)
            row["max2rho"] = None if rho is None else max(2.0, float(rho))
            row["within_bound"] = None if (rho is None or e_o is None) else bool(e_o <= max(2.0, float(rho)) + TOL)
            rows.append(row)
    return rows


def run_core_b(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    rows = core_b_rows()
    diffs = [r["abs_diff"] for r in rows if r["abs_diff"] is not None]
    vals = [r["eager_over_omega"] for r in rows if r["eager_over_omega"] is not None]
    res = {"meta": {"exp": EXP, "job": job.id, "instances": "repro_c3_benchmark.instance(seed), seeds 0-9; omega "
                    "repro_c3_benchmark.omega(I, seed, rate)", "solver": "opt.milp.solve_core (mip_rel_gap 1e-9)",
                    "reference": "code/theory_checks/c3/out/c3_benchmark.json b[*].per_rate[*]",
                    "git_revision": mc.git_revision(), "versions": mc.versions(), "written": _now()},
           "rows": rows, "n_solves": len(CORE_B_SEEDS) * 6, "max_eager_over_omega": max(vals) if vals else None,
           "max_abs_diff": max(diffs) if diffs else None, "n_compared": len(diffs),
           "reproduced": bool(diffs and len(diffs) == len(rows) and max(diffs) <= TOL),
           "all_within_bound": bool(rows and all(r["within_bound"] for r in rows))}
    outputs.dump(res, Path(out) / "core_b.json")
    return {"runs": 0, "rows": len(rows), "reproduced": res["reproduced"], "max": res["max_eager_over_omega"]}


# ---------------------------------------------------------------- dispatch
def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    _, part, _ = mc.parse_job_id(job.id)
    if part == "cell":
        return run_cell(job, outputs, out)
    if part == "milp":
        return run_milp(job, outputs, out)
    if part == "tight":
        return run_tight(job, outputs, out)
    if part == "core_b":
        return run_core_b(job, outputs, out)
    raise ValueError(f"unknown E1 job {job.id!r}")


def manifest_extra(out: Path) -> dict:
    """The instance hash of every (rho*, mu, c) instance of the grid (§2.6), with its fee map."""
    d = design()
    hashes, fees = {}, {}
    pts = sorted({(r, mu, c) for (_, r, mu, c) in grid_cells(d["alignments"])})
    for (r, mu, c) in pts:
        f, _ = fees_for(r, mu, c)
        inst, _, _, _ = cell_instance(overrides(mu, f), "trace", c, d["horizon_slots"])
        key = f"rho={num_key(r)}:mu={num_key(mu)}:c={int(c)}"
        hashes[key] = mc.instance_hash(inst)
        fees[key] = f
    return {"instance_hashes": hashes, "fees": fees, "design": {k: (list(v) if isinstance(v, tuple) else v)
                                                                for k, v in d.items()}}


# ---------------------------------------------------------------- summary
def _ok_output(out: Path, jid: str, path, ignored: Optional[list] = None) -> Optional[dict]:
    """The JSON output `path` of job `jid`, or None unless the job's record says 'ok' (§2.4: only 'ok' counts as
    done). An output that exists while its record is not 'ok' (left by an earlier run of a job that later failed or
    was killed) is not used and is listed in `ignored`."""
    rec = mc.read_record(out, jid)
    if rec is None or rec.get("status") != "ok":
        if ignored is not None and Path(path).is_file():
            ignored.append({"job": jid, "status": None if rec is None else rec.get("status"),
                            "output": _rel(path, out)})
        return None
    return mc.read_json(path)


def _milp_input(out: Path, jid: str, path, ignored: Optional[list] = None) -> dict:
    """A MILP's record for Q39's rule: its lb file if the job's record says 'ok', else a stand-in with the job's
    status ('wall_limit', 'oom_at_3G', 'error', 'failed', 'running'), or {'status': 'missing'}."""
    got = _ok_output(out, jid, path, ignored)
    if got is not None:
        return got
    rec = mc.read_record(out, jid)
    return {"status": rec.get("status") if rec is not None and rec.get("status") != "ok" else "missing"}


def _agg(values: list, note: str) -> dict:
    a = mc.median_summary(values) if values else mc.median_summary([])
    if not values:
        for k in ("median", "p95", "max"):
            put(a, k, None, note)
    return a


def _empty_ratio_entry(rho: float, note: str, tag: str) -> dict:
    e = {"n_runs": 0, "n_ratio": 0, "max2rho": max(2.0, float(rho))}
    e["ratio_LB"] = _agg([], note)
    e["ratio_inc"] = _agg([], note)
    for k in ("median", "p95", "max", "inc_median", "share_exact", "max_gap", "alg_mean"):
        put(e, k, None, note)
    e["median_ci95"] = [None, None]
    e["median_ci95_note"] = note
    e["n_above_max2rho"] = 0
    if tag == "A2-r1":
        e["P_over_LB"] = _agg([], note)
        e["a2_frac"] = e["P_over_LB"]
    return e


def ratio_entry(rows: list[dict], rho: float, tag: str) -> dict:
    """The aggregates of one (sched, rho*, mu, tag) over its runs (§4.3, Metrics)."""
    if not rows:
        return _empty_ratio_entry(rho, "no runs of this tag in the cell's outputs", tag)
    rl = [r["lb"]["ratio_LB"] for r in rows if r["lb"].get("ratio_LB") is not None]
    ri = [r["lb"]["ratio_inc"] for r in rows if r["lb"].get("ratio_inc") is not None]
    gaps = [r["lb"]["gap"] for r in rows if r["lb"].get("gap") is not None]
    m2 = max(2.0, float(rho))
    e = {"n_runs": len(rows), "n_ratio": len(rl), "max2rho": m2,
         "ratio_LB": _agg(rl, "no run with a lower bound"), "ratio_inc": _agg(ri, "no run with an incumbent")}
    e["median"], e["median_ci95"] = e["ratio_LB"]["median"], e["ratio_LB"]["median_ci95"]
    e["p95"], e["max"] = e["ratio_LB"]["p95"], e["ratio_LB"]["max"]
    if e["median"] is None:
        put(e, "median", None, "no run with a lower bound")
    put(e, "inc_median", e["ratio_inc"]["median"], "no run with an incumbent")
    put(e, "share_exact", sum(bool(r["lb"].get("exact")) for r in rows) / len(rows))
    put(e, "max_gap", max(gaps) if gaps else None, "no MILP gap (MILP missing or killed)")
    put(e, "alg_mean", float(np.mean([r["ALG"] for r in rows])))
    e["n_above_max2rho"] = sum(1 for v in rl if v > m2)
    if tag == "A2-r1":
        pv = [r["P"] / r["lb"]["LB"] for r in rows if r.get("P") is not None and r["lb"].get("LB")]
        e["P_over_LB"] = _agg(pv, "no A2 run with P and a lower bound")
        e["a2_frac"] = e["P_over_LB"]
    return e


def _checked(rec: dict, ih: str, sh: Optional[str], what: str) -> dict:
    """A benchmark record whose instance hash (or schedule hash, where sh is given) differs from the run's, e.g. one
    left by an earlier run of its job before the cell was rerun, is not used: {'status': 'stale', ...}, so that
    Q39's LB falls back to the other record. Stand-ins without hashes (missing, killed) pass unchanged."""
    bad = []
    if rec.get("instance_hash") is not None and rec["instance_hash"] != ih:
        bad.append("instance hash")
    if sh is not None and rec.get("schedule_hash") is not None and rec["schedule_hash"] != sh:
        bad.append("schedule hash")
    if not bad:
        return rec
    return {"status": "stale", "stale_note": f"{what} record {rec.get('job')!r}: {' and '.join(bad)} differ from the "
                                             "run's (an output of an earlier run of the job; rerun it)"}


def _lb_inputs(out: Path, cr: dict, row: dict, ignored: Optional[list] = None) -> tuple[dict, dict, str]:
    """(LP record, MILP record or stand-in, MILP job id) of one run, each checked against the run's instance and
    schedule hashes (_checked)."""
    s, rho, mu, c = cr["sched"], cr["rho_star"], cr["mu"], cr["c"]
    lp = mc.read_json(Path(out) / row["lp_file"]) or {"status": "missing"}
    lp = _checked(lp, cr["instance_hash"], row["schedule_hash"], "LP")
    if s == "eager":
        jid, path = milp_eager_id(rho, mu, c), milp_eager_file(out, rho, mu, c)
    elif s == "trace":
        jid, path = milp_omega_id(s, rho, mu, c), milp_omega_file(out, s, rho, mu, c)
    else:
        jid, path = milp_omega_id(s, rho, mu, c, row["tag"], row["p"]), \
            milp_omega_file(out, s, rho, mu, c, row["tag"], row["p"])
    milp = _milp_input(out, jid, path, ignored)
    # OPT_eager does not depend on the run's schedule: only its instance hash is compared
    milp = _checked(milp, cr["instance_hash"], None if s == "eager" else row["schedule_hash"], "MILP")
    return lp, milp, jid


def _bench_brief(b: dict) -> dict:
    return {k: b.get(k) for k in ("LB", "LB_source", "incumbent", "gap", "exact", "milp_status", "lp_status")}


def summary(out: Path) -> dict:
    out = Path(out)
    d = design()
    al, seeds = d["alignments"], d["policy_seeds"]
    ignored: list = []      # outputs whose job record is not 'ok' (not used)
    cells = {}
    for (s, r, mu, c) in grid_cells(ALIGNMENTS):
        cr = _ok_output(out, cell_id(s, r, mu, c), cell_file(out, s, r, mu, c), ignored)
        if cr is not None:
            cells[(s, r, mu, c)] = cr
    runs_by = {}            # (s, r, mu, tag) -> rows with 'lb'
    e16, cert_rows = [], []
    milps: dict = {}        # MILP job id -> (kind, record or stand-in)
    for key, cr in cells.items():
        s, r, mu, c = key
        for row in cr["runs"]:
            lp, milp, jid = _lb_inputs(out, cr, row, ignored)
            milps.setdefault(jid, ("eager" if s == "eager" else f"omega_{s}", milp))
            lb = mc.lb_record(row["ALG"], lp, milp, reason=row["ratio_validity"])
            row = {**row, "lb": lb, "milp_job": jid, "cell": cr["job"]}
            runs_by.setdefault((s, r, mu, row["tag"]), []).append(row)
            e16.append(row)
            if row.get("certificate") is not None:
                cert_rows.append(row)
    for (r, mu, c) in eager_points(al):            # the eager MILPs of the mu sweep have no eager cell
        jid = milp_eager_id(r, mu, c)
        if jid not in milps:
            milps[jid] = ("eager", _milp_input(out, jid, milp_eager_file(out, r, mu, c), ignored))
    milp_counts: dict = {"omega_adaptive": {}, "omega_trace": {}, "eager": {}}
    gaps, kills, stale = [], [], []
    for jid, (kind, milp) in milps.items():
        st = milp.get("status")
        milp_counts[kind][str(st)] = milp_counts[kind].get(str(st), 0) + 1
        if milp.get("gap") is not None and st in (0, 1):
            gaps.append(milp["gap"])
        if st == "wall_limit":
            kills.append(jid)
        if st == "stale":
            stale.append(jid)
    stale_lp = sorted({r["lp_file"] for r in e16 if r["lb"].get("lp_status") == "stale"})
    seen = milps
    # ratios on the whole design grid
    ratios: dict = {}
    for (s, r, mu, c) in grid_cells((1,)):
        for tag in cell_tags(s, mu):
            rows = runs_by.get((s, r, mu, tag), [])
            ratios.setdefault(s, {}).setdefault(num_key(r), {}).setdefault(num_key(mu), {})[tag] = \
                ratio_entry(rows, r, tag)
    # brackets under 'trace' at mu = 1 (Fig. 5(a), M4, M5)
    brackets: dict = {"trace": {}}
    for r in RHOS:
        for c in ALIGNMENTS:
            ent = {"rho_star": float(r), "max2rho": max(2.0, float(r))}
            tr, eg = cells.get(("trace", r, MU_MAIN, c)), cells.get(("eager", r, MU_MAIN, c))
            if tr is None or not tr["runs"]:
                for k in ("point", "lo", "hi", "rho_instance"):
                    put(ent, k, None, "no 'trace' cell at this (rho*, c) in the outputs")
                ent["exact"] = False
            else:
                lp_t, milp_t, _ = _lb_inputs(out, tr, tr["runs"][0])
                om = mc.bench_values(lp_t, milp_t)
                if eg and eg["runs"]:
                    lp_e, milp_e, _ = _lb_inputs(out, eg, eg["runs"][0])
                else:
                    lp_e = {"status": "missing"}
                    milp_e = _milp_input(out, milp_eager_id(r, MU_MAIN, c), milp_eager_file(out, r, MU_MAIN, c))
                    milp_e = _checked(milp_e, tr["instance_hash"], None, "MILP")
                ev = mc.bench_values(lp_e, milp_e)
                ent.update(mc.bracket(ev, om))
                ent["eager"], ent["omega"] = _bench_brief(ev), _bench_brief(om)
                rv = [v["rho"] for v in (tr["instance_rho"] or {}).values() if v]
                put(ent, "rho_instance", max(rv) if rv else None, "instance_rho unavailable")
            brackets["trace"].setdefault(num_key(r), {})[num_key(c)] = ent
    # fees and instance rho per (rho*, c)
    fees: dict = {}
    for (s, r, mu, c), cr in sorted(cells.items(), key=lambda kv: (kv[0][1], kv[0][3], kv[0][0], kv[0][2])):
        e = fees.setdefault(num_key(r), {}).setdefault(num_key(c), None)
        val = {"beta_jl_usd": cr["fees"],
               "instance_rho": {k: (v or {}).get("rho") for k, v in cr["instance_rho"].items()},
               "instance_rho_at": {k: (None if v is None else [v["site"], v["contract"]])
                                   for k, v in cr["instance_rho"].items()},
               "base_rho": {k: (v or {}).get("rho") for k, v in cr["base_rho"].items()}}
        if e is None:
            fees[num_key(r)][num_key(c)] = val
    for r in RHOS:
        for c in ALIGNMENTS:
            if fees.get(num_key(r), {}).get(num_key(c)) is None:
                fees.setdefault(num_key(r), {})[num_key(c)] = None
                fees[num_key(r)][f"{num_key(c)}_note"] = "no cell at this (rho*, c) in the outputs"
    # certificates (E1-5)
    by_case = {k: {"runs": 0, "held": 0} for k in ("W(a)", "W(b)", "W(c)", "unavailable")}
    fails, wc = [], []
    for row in cert_rows:
        cs = row["certificate_case"]
        by_case[cs]["runs"] += 1
        held = bool((row["certificate"] or {}).get("held"))
        by_case[cs]["held"] += int(held)
        brief = {"file": row["file"], "case": cs, **{k: (row["certificate"] or {}).get(k) for k in
                                                     ("held", "t_a", "core_bound_ok", "e_mode_ok", "wind_down_ok",
                                                      "e_mode_reserve_ok", "core_bound_slack")}}
        if cs in ("W(a)", "W(b)") and not held:
            fails.append(brief)
        if cs == "W(c)":
            wc.append(brief)
    certs = {"runs": len(cert_rows), "available": sum(v["runs"] for k, v in by_case.items() if k != "unavailable"),
             "held": sum(v["held"] for v in by_case.values()), "by_case": by_case, "failures": fails,
             "w_c_runs": wc, "unavailable": by_case["unavailable"]["runs"]}
    tight = _ok_output(out, job_id(EXP, "tight"), out / "tight_family.json", ignored)
    core_b = _ok_output(out, job_id(EXP, "core_b"), out / "core_b.json", ignored)
    checks = build_checks(out, cells, e16, certs, tight, core_b, brackets, ratios)
    meta = {"exp": EXP, "git_revision": mc.git_revision(), "written": _now(), "reduced": d["reduced"],
            "grid": {"schedules": list(SCHEDS), "rho_star": list(RHOS), "mu_main": MU_MAIN,
                     "mu_sweep": list(MUS_SWEEP), "rho_mu_sweep": RHO_MU, "alignments": list(al),
                     "alignments_design": list(ALIGNMENTS), "policy_seeds": list(seeds),
                     "policy_seeds_design": list(POLICY_SEEDS), "tags": list(TAGS),
                     "horizon_slots": d["horizon_slots"], "cells_found": len(cells)},
            "config": CONFIG, "menu": MENU, "milp": {"limit_s": mc.milp_limit_s(), "mip_rel_gap": MILP_GAP,
                                                     "grid": BENCH_GRID},
            "tags": {t: {"policy_id": v[0], "params": v[1], "style_key": STYLE_KEYS[t]} for t, v in TAGS.items()},
            "fees": fees,
            "ignored_outputs": list({x["job"]: x for x in ignored}.values())}
    if d["reduced"]:
        meta["reduced_note"] = (f"reduced job list ({REDUCED_ENV}=1): alignment 1, policy seed 0, the first "
                                f"{REDUCED_HORIZON_SLOTS} slow slots of each instance; not a result")
    summ = {"meta": meta, "ratios": ratios, "brackets": brackets, "certificates": certs,
            "milp": {"counts": milp_counts, "max_gap": max(gaps) if gaps else None, "wall_limit_kills": kills,
                     "n_jobs": len(seen), "stale": stale, "stale_lp_files": stale_lp},
            "tight_family": {"rows_T3000": [{k: r[k] for k in ("T", "rho", "ratio")}
                                            for r in (tight or {}).get("rows", []) if r["T"] == 3000]},
            "checks": checks}
    if summ["milp"]["max_gap"] is None:
        summ["milp"]["max_gap_note"] = "no MILP with a gap"
    if tight is None:
        summ["tight_family"]["rows_T3000_note"] = "tight_family.json missing (job e1:tight)"
    mc.dump_json(summ, out / "summary.json")
    mc.write_text(tables(summ, tight, core_b), out / "tables.md")
    return summ


def build_checks(out: Path, cells: dict, rows: list, certs: dict, tight, core_b, brackets, ratios) -> dict:
    ch = {}
    ch["E1-1"] = {"status": "elsewhere", "claim": "Fig. 2(b)'s rho equals a11's rows.*.rho",
                  "where": "code/sim/out/figs/fig2.json (figs/fig2_e1a.py, design/sim_spec_ms3.md §4.2, §8.2)"}
    rc = [{"cell": cr["job"], **cr["rho_check"], "fees": cr["fees"]} for cr in cells.values()]
    ch["E1-2"] = {"status": ("pass" if rc and all(x["pass"] for x in rc) else "fail") if rc else "missing",
                  "claim": "instance_rho after beta_for_rho equals rho* for both LLMs, every config seed (1e-9)",
                  "n_cells": len(rc), "max_abs_diff": max((v for x in rc for v in x["abs_diff"].values()
                                                           if v is not None), default=None),
                  "failures": [x for x in rc if not x["pass"]][:20]}
    if tight is None:
        ch["E1-3"] = {"status": "missing", "why": "tight_family.json missing (job e1:tight)"}
    else:
        t3 = tight["check_E1_3"]
        ch["E1-3"] = {"status": "pass" if t3["pass"] else "fail", "claim": "C3-L1(c) tight family: T = 60 equals "
                      "c3_benchmark.json a; MILP values equal the closed forms (1e-9, status 0, gap 0)", **t3}
    e14 = {"status": "missing",            # set below; first, as in every other check entry
           "claim": "C3-L2 (PROVEN): OPT_eager / OPT(sigma, omega) <= max(2, rho) on exact core exports"}
    ok = True
    if tight is not None:
        e14["tight_family_above_max2rho"] = tight["check_E1_3"]["above_max2rho"]
        ok &= not tight["check_E1_3"]["above_max2rho"]
    else:
        e14["tight_family_note"] = "tight_family.json missing"
    if core_b is not None:
        e14.update(core_b_reproduced=core_b["reproduced"], core_b_max_abs_diff=core_b["max_abs_diff"],
                   core_b_max_eager_over_omega=core_b["max_eager_over_omega"],
                   core_b_all_within_bound=core_b["all_within_bound"], core_b_n=len(core_b["rows"]))
        ok &= bool(core_b["all_within_bound"]) and bool(core_b["reproduced"])
    else:
        e14["core_b_note"] = "core_b.json missing (job e1:core_b)"
    tr = [(cr["job"], cr.get("core_export")) for k, cr in cells.items() if k[0] == "trace"]
    e14["trace_exports"] = {"n": len(tr), "n_exact": sum(1 for _, x in tr if x and x.get("exact")),
                            "n_not_exportable": sum(1 for _, x in tr if x and x.get("exportable") is False),
                            "why_not_exportable": sorted({x["why"] for _, x in tr if x and x.get("why")})[:3],
                            "exact_cells": [j for j, x in tr if x and x.get("exact")]}
    diag = []
    for rk, by_c in brackets["trace"].items():
        for ck, b in by_c.items():
            if b.get("point") is not None:
                diag.append({"rho": rk, "c": ck, "point": b["point"], "lo": b["lo"], "hi": b["hi"],
                             "exact": b["exact"], "lo_above_max2rho": b["lo"] is not None
                             and b["lo"] > b["max2rho"] + TOL})
    e14["trace_brackets_diagnostic"] = {"n": len(diag), "n_lo_above_max2rho": sum(x["lo_above_max2rho"] for x in diag)}
    e14["status"] = ("pass" if ok else "fail") if (tight is not None and core_b is not None) else "missing"
    ch["E1-4"] = e14
    ch["E1-5"] = {"status": ("pass" if not certs["failures"] and certs["unavailable"] == 0 else "fail")
                  if certs["runs"] else "missing",
                  "claim": "Theorem W: every Sublet certificate held in the proven cases; W(c) runs reported",
                  "runs": certs["runs"], "by_case": certs["by_case"], "n_failures": len(certs["failures"]),
                  "n_w_c": len(certs["w_c_runs"])}
    bad_inv = [r["file"] for r in rows if r["n_invariant_failures"]]
    bad_gpu = [r["file"] for r in rows if r["gpu_only_lease_slots"]]
    bad_rv = [r["file"] for r in rows if r["ratio_validity"] is not None]
    p1 = [r for r in rows if r["plan_class_p1"] and r["lb"].get("ratio_LB") is not None]
    bad_p1 = [{"file": r["file"], "ratio_LB": r["lb"]["ratio_LB"]} for r in p1 if r["lb"]["ratio_LB"] < 1 - P1_TOL]
    ch["E1-6"] = {"status": ("pass" if not (bad_inv or bad_gpu or bad_rv or bad_p1) else "fail") if rows else "missing",
                  "claim": "every run: no invariant failure, no GPU-only lease slot, ratio_validity None; P1 runs "
                           "ratio_LB >= 1 - 1e-6 (Proposition M4)",
                  "n_runs": len(rows), "invariant_failures": bad_inv[:20], "gpu_only_lease_slots": bad_gpu[:20],
                  "ratio_validity_not_none": bad_rv[:20], "n_p1": len(p1), "p1_below": bad_p1[:20],
                  "min_ratio_LB_p1": min((r["lb"]["ratio_LB"] for r in p1), default=None)}
    rep = _ok_output(Path(out).parent / "e10", "e10:repro", Path(out).parent / "e10" / "repro.json")
    if rep is None:
        ch["E1-7"] = {"status": "missing", "where": "e10/repro.json (E10-1, job e10:repro)",
                      "claim": "A3 reference mode with rbar = 1 and theory reproduces c4_lower.json a (pd_r1, "
                               "pd_r1_min, pd_rth, pd_rth_min)"}
    else:
        cols = ("pd_r1", "pd_r1_min", "pd_rth", "pd_rth_min")
        md = max((abs(x["diff"].get(k) or 0.0) for x in rep.get("rows", []) for k in cols if x.get("diff")),
                 default=None)
        ch["E1-7"] = {"status": "pass" if rep.get("pass_pd") else "fail", "where": "e10/repro.json (E10-1)",
                      "claim": "A3 reference mode with rbar = 1 and theory reproduces c4_lower.json a",
                      "max_abs_diff_pd_columns": md, "n_points": len(rep.get("rows", []))}
    above = []
    for s, by_r in ratios.items():
        for rk, by_mu in by_r.items():
            for mk, by_t in by_mu.items():
                for tag, e in by_t.items():
                    if e["n_above_max2rho"]:
                        above.append({"sched": s, "rho": rk, "mu": mk, "tag": tag, "n": e["n_above_max2rho"],
                                      "of": e["n_ratio"]})
    ch["E1-8"] = {"status": "informative", "claim": "ratios ALG/LB above max(2, rho*) on trace instances are not "
                  "bugs (plan §7)", "n_runs_above": sum(x["n"] for x in above), "by_point": above}
    return ch


def tables(s: dict, tight, core_b) -> str:
    L = ["# E1: revocation exposure and the benchmark gap (design/sim_spec_ms3.md §4)", ""]
    if s["meta"].get("reduced"):
        L += [f"*{s['meta']['reduced_note']}*", ""]
    for sched, by_r in s["ratios"].items():
        L.append(f"## ALG / LB under `{sched}` (median [95% CI], median of ALG / incumbent, share exact)")
        L.append("")
        rows = []
        for rk, by_mu in by_r.items():
            for mk, by_t in by_mu.items():
                for tag, e in by_t.items():
                    ci = e.get("median_ci95") or [None, None]
                    rows.append([rk, mk, tag, e["n_runs"], e.get("median"), ci[0], ci[1], e.get("inc_median"),
                                 e.get("share_exact"), e.get("max_gap"), e["n_above_max2rho"]])
                    if tag == "A2-r1":
                        f = e["P_over_LB"]
                        rows.append([rk, mk, "A2 frac (P/LB)", f["n"], f["median"], f["median_ci95"][0],
                                     f["median_ci95"][1], None, None, None, None])
        L.append(mc.md_table(["rho*", "mu", "tag", "runs", "median", "ci lo", "ci hi", "inc median", "exact",
                              "max gap", "> max(2, rho)"], rows))
    L.append("## OPT_eager / OPT(sigma, omega) under `trace` (brackets, M4)")
    L.append("")
    rows = [[rk, ck, b.get("rho_instance"), b.get("point"), b.get("lo"), b.get("hi"), b.get("exact")]
            for rk, by_c in s["brackets"]["trace"].items() for ck, b in by_c.items()]
    L.append(mc.md_table(["rho*", "c", "rho (instance)", "point", "lo", "hi", "exact"], rows))
    if tight is not None:
        L.append("## Tight family (C3-L1(c), solve_core)")
        L.append("")
        L.append(mc.md_table(["T", "rho", "OPT", "OPT_eager", "ratio", "closed form", "max(2, rho)"],
                             [[r["T"], r["rho"], r["OPT_none"], r["OPT_eager"], r["ratio"], r["ratio_closed_form"],
                               r["max2rho"]] for r in tight["rows"]], digits=6))
    if core_b is not None:
        L.append(f"core_b: {len(core_b['rows'])} rows, max OPT_eager/OPT(sigma, omega) "
                 f"{core_b['max_eager_over_omega']}, max |diff| to c3_benchmark.json {core_b['max_abs_diff']}, "
                 f"reproduced {core_b['reproduced']}")
        L.append("")
    c = s["certificates"]
    L.append("## Certificates (Sublet, Theorem W)")
    L.append("")
    L.append(mc.md_table(["case", "runs", "held"], [[k, v["runs"], v["held"]] for k, v in c["by_case"].items()]))
    L.append("## MILPs")
    L.append("")
    L.append(mc.md_table(["kind", "status", "jobs"], [[k, st, n] for k, v in s["milp"]["counts"].items()
                                                      for st, n in sorted(v.items())]))
    L.append(f"max gap {s['milp']['max_gap']}; wall-limit kills {len(s['milp']['wall_limit_kills'])}")
    L.append("")
    L.append("## Checks (§4.6)")
    L.append("")
    L.append(mc.md_table(["check", "status"], [[k, v["status"]] for k, v in s["checks"].items()]))
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                     description=__doc__))
