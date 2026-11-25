"""E10: the value of public reclaim information (design/sim_spec_ms3.md §5; deliverable D24).

E10(a) runs the T4/O1 family (fam.Fam(m, rho, 2, 1, T), D = 3, a = 1, beta = (rho - 1) a D, q = beta + a D + 1, one
always-active client) through the engine (instance.from_core) under the adaptive lender (Fig. 5(c); T = 16 m D,
M10), the oblivious 'safe_site' lender at k* (O1-A; Phi = max(2, floor(600 / (k* D))), T = Phi k* D, M12) and the
oblivious 'iid_step' lender at p* (O1-C; T = 3000, U = T / D) (Fig. 6), with the exact OPT(sigma, omega) of
fam.opt_dp per realized schedule (drivers.bench.bench_for(..., "fam")), and aggregates E[ALG] / E[OPT] by
ms3_common.ratio_of_means (M13). E10-1 reproduces c3/out/c4_lower.json `a` by the R2 path of the MS2 spec
(repro_c4_lower.part_a_row). E10(b) (supplement, evidence on C-O1b, CONJECTURE) runs A3 (I1) and A4 (I2) on
general core instances whose clients follow the E2 demand layers of one day (general_core, §5.4, M15, M49) under
'safe_site' and under the trace schedule of configs/ms3_e10b_trace.json, against Q39's lower bound from
opt.milp.solve_core.

Jobs (§5.5; job ids by ms3_common.job_id, numbers as num_key):
  pool  e10:repro                         E10-1 (16 points of c4_lower.json `a` at T = 48) and E10-9's
                                          recomputation of o1_lb.json `A` (o1_lb.lb_A, lb_C through C11) -> repro.json
  pool  e10:a:sched=S:rho=R:m=M           every tag and seed of one point of E10(a) -> runs/a/S/rho=R/m=M.json
  pool  e10:rerun:sched=S:rho=R:m=M       seeds 30-129 of the tags that E10-5 or E10-6 flags at that point (listed
                                          only when the point's e10:a output flags one; run_e10.sh lists the jobs
                                          again after the pool phase) -> runs/rerun/S/rho=R/m=M.json
  pool  e10:b:rho=R:m=M                   E10(b): both schedules, seeds 0-9, A3 and A4 -> runs/b/rho=R/m=M.json
  milp  e10:b_milp:sched=S:rho=R:m=M:key=K   solve_core of one (instance, omega) of E10(b): K the seed under
                                          'safe_site', the series under 'trace' -> runs/b/milp/S/rho=R/m=M/K.json
(The spec's `e10:b:milp:...` has a part without '=' that §2.4's id format and ms3_common.parse_job_id reject;
'b_milp' takes its place.)

E10(a) grid: sched in {adaptive, safe_site, iid_step}, rho in {4, 16, 64} (16 main), m in {2, 4, 8, 16, 32, 64}.
Tags (registry id, parameters, information; style key of §8):
  RR      RR_RENEW {}                                                I1  rr_renew
  A2-th   A2 {"rbar": "theory"}                                      I1  a2_theory
  A3-ref  A3 {"x3": false, "x2": "reference", "reaction": "cold"}    I1  a3
  A3-rot  A3 {"x3": true, "x2": "reference", "reaction": "cold"}     I1  a3_rot (supplement)
  MARK    MARKING {}                                                 I2  marking
adaptive: RR (deterministic, one run: lender seed 0, policy seed 0), A2-th, A3-ref, A3-rot (policy seeds 0-29,
lender seed 0); safe_site: RR, A2-th, MARK; iid_step: MARK, RR, A2-th (30 runs each, lender seed = policy seed
s = 0-29, M11). k* and p* come from code/theory_checks/c3/o1/out/o1_lb.json `A` (fields k, p) where it lists the
point, else from o1_lb.lb_A / lb_C (m = 32, through paths.import_ref, C11); at m = 2, where O1-A does not apply, k = 2.
E10(b): m in {2, 4, 8, 16}, rho in {4, 16}, seeds s = 0-9 (series = the (s mod 5)-th of E2_SERIES, so s and s + 5
share the instance), schedules 'safe_site' (D_slots 3, k = max(2, m), Phi = floor(T / (k D)), lender seed s) and
'trace' (omega_i = the announcement set of the one site of lender a2:c<i>), tags A3 {} (I1, style a3) and A4 {}
(I2, style a4), policy seed s. Client k (k = 0..7) of general_core follows demand layer k + 1 and serves LLM k mod 2.

Reduced job list (smoke runs and tests): MS3_E10_REDUCED=1 (run_e10.sh --reduced sets it) runs E10(a) at m in
{2, 4, 8} with 5 seeds (RR under 'adaptive' still once) and E10(b) at m in {2, 4}, seeds {0, 1}; e10:repro is
unchanged. Default (unset or 0): the full lists above.

Outputs under out/e10/ (§5.5): runs/ (not versioned), repro.json, summary.json, tables.md, manifest.json, jobs/,
logs/, run_e10.log.

summary.json (every key path and its meaning; <rho> "4", "16", "64" in part a, "4", "16" in part b; <m> "2" ...;
every path of the design grid is present, a value the runs did not produce is null with a '<key>_note'):
  meta                        exp, git_revision, written, reduced (and reduced_note), grid {a {schedules, rho,
                              rho_main, m, m_run, n_seeds, n_seeds_design, tags, rerun_seeds}, b {schedules, rho, m,
                              m_run, seeds, seeds_design, series, T, slot_min, trace_config}}, family {tau, H, D, a,
                              c_T, T_iid, phi_slots}, tags {tag: {policy_id, params, information, style_key}},
                              points_found {a, reruns, b_runs}, ignored_outputs (outputs present whose job record
                              is not 'ok', with job and status: not used, §2.4)
  a.<sched>.<rho>.<m>.<tag>   ratio (E[ALG] / E[OPT], ratio of means), ci95 [lo, hi] (bootstrap over runs, B 2000,
                              seed 0), min and max of the per-run ALG / OPT, runs, T, alg and opt (means), seeds
                              (lender/policy pairing), and the lender parameters k_star, Phi (safe_site), p_star, U
                              (iid_step); sched in {adaptive, safe_site, iid_step}
  bounds.<rho>.<m>            k_star, p_star, Phi, T_safe_site, LB_A (at k*; null at m = 2), LB_C_max, LB_T (C3-T4 at
                              T = 16 m D), T_adaptive, T_iid_step, limit (rho m / (m + rho - 1)), O1B_adaptive
                              (min{rho (1 + D / T), 2 m + a D / OPT_RR} at RR-renew's adaptive run, M38) with
                              OPT_RR_adaptive (that run's OPT), O1B_safe_site (the same at T = Phi k* D and OPT =
                              OPT_safe_site = Phi beta + a T), two_h_m_plus_1, UB_I1 (min(rho, 2 m)), UB_I2
                              (min(rho, 2 h_m + 1)), source {k_star, p_star, LB_A, LB_C_max}: 'o1_lb.json A' or
                              'o1_lb.lb_A (C11)' / 'o1_lb.lb_C (C11)' or the m = 2 rule
  value_public.<sched>.<rho>.<m>   sched in {safe_site, iid_step} (M52): best_private (tag among RR, A2-th with
                              the smallest mean cost), best_public (MARK), mean_private, mean_public, ratio (mean
                              private / mean public), ci95 (paired bootstrap over the seeds, B 2000, seed 0, the best
                              tags fixed on the full sample), n_pairs, B, seed, means (mean cost per tag run there)
  b.<sched>.<rho>.<m>.<tag>   sched in {safe_site, trace}, tag in {A3, A4}: ratio (E[ALG] / E[LB], Q39's LB, an upper
                              bound on E[ALG] / E[OPT]) with ci95, inc (E[ALG] / E[incumbent]) with inc_ci95,
                              ratio_LB and ratio_inc (metrics.aggregate of the per-run ratios), share_exact,
                              max_gap, runs, runs_with_LB, empty_instances (runs with no demand), T, alg, lb, incumbent
                              (means), min and max of the per-run ratio_LB
  checks.E10-1 ... E10-10     status 'pass' | 'fail' | 'pending' | 'informative' | 'missing' with the inputs of
                              each check of §5.5 (E10-10 also lists stale_milp_records: E10(b) MILP records whose
                              instance or schedule hash differs from the runs', left by an earlier run of the job and
                              not used for any LB)
repro.json: rows {m, rho, values {rr, stay, pd_r1, pd_r1_min, pd_rth, pd_rth_min, LB_T}, ref, diff, R checks},
  pass, pass_pd (the A3 columns, E1-7), max_abs_diff; o1_lb {rows {rho, m, LB_A, k, LB_C, p, ref, diff}, pass}.

Run from code/sim under the 3 GB cap through run_e10.sh (ms3_lib.sh). --estimate uses the time constants of
§5.2, §5.3 and §11.1: adaptive 15 s per run at m = 64, T = 3072, scaled by T m; safe_site 0.137 + 0.049 s per run
(A2 at m = 64); iid_step 5 (0.157 + 0.212) s per run (five times RR-renew's T = 600 values at m = 64); e10:repro
120 s ("minutes"); a MILP limit + 60 s; E10(b) pool jobs have no constant in §11.1 (no estimate).
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import copy
import functools
import math
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

from . import ms3_common as mc
from .ms3_common import Job, job_id, num_key, put

EXP = "e10"
TAU, H_SLOTS, D, A = 2, 1, 3, 1.0          # fam.Fam(m, rho, 2, 1, T): D = tau + H, rent a = 1
C_T = 16                                    # M10: T = c m D under the adaptive lender
T_IID = 3000                                # M12
PHI_SLOTS = 600                             # M12: Phi = max(2, floor(600 / (k* D)))
MS = (2, 4, 8, 16, 32, 64)
RHOS = (4.0, 16.0, 64.0)
RHO_MAIN = 16.0
SCHEDS_A = ("adaptive", "safe_site", "iid_step")
OBLIVIOUS = ("safe_site", "iid_step")
N_SEEDS = 30                                # M11
RERUN_SEEDS = tuple(range(30, 130))         # M14
TAGS = {"RR": ("RR_RENEW", {}, "I1"),
        "A2-th": ("A2", {"rbar": "theory"}, "I1"),
        "A3-ref": ("A3", {"x3": False, "x2": "reference", "reaction": "cold"}, "I1"),
        "A3-rot": ("A3", {"x3": True, "x2": "reference", "reaction": "cold"}, "I1"),
        "MARK": ("MARKING", {}, "I2")}
SCHED_TAGS = {"adaptive": ("RR", "A2-th", "A3-ref", "A3-rot"), "safe_site": ("RR", "A2-th", "MARK"),
              "iid_step": ("MARK", "RR", "A2-th")}
DETERMINISTIC = ("RR",)                     # one run under the (deterministic) adaptive lender
PRIVATE, PUBLIC = ("RR", "A2-th"), ("MARK",)
STYLE_KEYS = {"RR": "rr_renew", "A2-th": "a2_theory", "A3-ref": "a3", "A3-rot": "a3_rot", "MARK": "marking",
              "A3": "a3", "A4": "a4"}
# E10(b) (§5.4, M15, M49)
MS_B = (2, 4, 8, 16)
RHOS_B = (4.0, 16.0)
SCHEDS_B = ("safe_site", "trace")
SEEDS_B = tuple(range(10))
TAGS_B = {"A3": ("A3", {}, "I1"), "A4": ("A4", {}, "I2")}
E2_SERIES = ("azure2024_code", "azure2024_conv", "burstgpt_1", "burstgpt_2", "burstgpt_3")   # §6.3, in order
T_B, SLOT_B, N_LAYERS = 288, 5, 8
G_B = (1, 2)
B_LENDER, B_H, B_MU, B_C = "a2:c05", 60, 1.0, 1     # the base instance of §6.3 whose day 0 gives the demand
TRACE_CONFIG = "ms3_e10b_trace.json"
TRACE_LENDERS = tuple(f"a2:c{i:02d}" for i in range(16))
MILP_GAP = 1e-4
GATE_VARS, GATE_MB = 200_000, 2500.0        # S36: a larger model must run alone
# E10-1 (repro_c4_lower part (a))
REPRO_MS, REPRO_RHOS = (2, 3, 4, 6), (2.0, 4.0, 8.0, 16.0)
REPRO_COLS = ("rr", "stay", "pd_r1", "pd_r1_min", "pd_rth", "pd_rth_min", "LB_T")
TOL = 1e-9
B_BOOT, BOOT_SEED = 2000, 0
REDUCED_ENV = "MS3_E10_REDUCED"
# time constants (§5.2, §5.3, §11.1)
EST_ADAPTIVE_S = 15.0           # per run at m = 64, T = 3072 (estimate of §5.2)
EST_SAFE_S = 0.137 + 0.049      # per run: A2's engine + opt_dp at m = 64, the slower tag (§5.3)
EST_IID_S = 5 * (0.157 + 0.212)  # per run at T = 3000: five times RR-renew's T = 600 values at m = 64 (§5.3)
EST_REPRO_S = 120.0             # §11.1: "minutes"


# ---------------------------------------------------------------- grid
def design() -> dict:
    reduced = os.environ.get(REDUCED_ENV, "0") == "1"
    return {"reduced": reduced, "ms": (2, 4, 8) if reduced else MS, "n_seeds": 5 if reduced else N_SEEDS,
            "ms_b": (2, 4) if reduced else MS_B, "seeds_b": (0, 1) if reduced else SEEDS_B}


def default_out() -> Path:
    """out/e10, or MS3_OUT (exported by ms3_lib.sh's ms3_init) when set."""
    v = os.environ.get("MS3_OUT")
    return Path(v).resolve() if v else mc.out_dir(EXP)


def a_rel(sched, rho, m) -> Path:
    return Path(sched) / f"rho={num_key(rho)}" / f"m={int(m)}.json"


def a_file(out: Path, sched, rho, m) -> Path:
    return Path(out) / "runs" / "a" / a_rel(sched, rho, m)


def rerun_file(out: Path, sched, rho, m) -> Path:
    return Path(out) / "runs" / "rerun" / a_rel(sched, rho, m)


def b_file(out: Path, rho, m) -> Path:
    return Path(out) / "runs" / "b" / f"rho={num_key(rho)}" / f"m={int(m)}.json"


def b_milp_file(out: Path, sched, rho, m, key) -> Path:
    return Path(out) / "runs" / "b" / "milp" / sched / f"rho={num_key(rho)}" / f"m={int(m)}" / f"{key}.json"


def b_keys(sched: str, seeds) -> list:
    """The MILP keys of E10(b): the seeds under 'safe_site', the distinct series under 'trace'."""
    if sched == "safe_site":
        return [int(s) for s in seeds]
    return list(dict.fromkeys(E2_SERIES[int(s) % len(E2_SERIES)] for s in seeds))


# ---------------------------------------------------------------- bounds (O1-A, O1-C, C3-T4, O1-B, O1-D)
@functools.lru_cache(maxsize=None)
def o1_rows() -> dict:
    """{(rho, m string): row} of c3/o1/out/o1_lb.json `A`."""
    from ..paths import C3
    d = mc.read_json(C3 / "o1" / "out" / "o1_lb.json") or {}
    return {(float(r["rho"]), str(r["m"])): r for r in d.get("A", [])}


@functools.lru_cache(maxsize=None)
def _o1_lb():
    from ..paths import import_ref
    return import_ref("o1_lb")


@functools.lru_cache(maxsize=None)
def lb_A(rho: float, m) -> tuple:
    """o1_lb.lb_A(rho, m) -> (LB_A max over k, k*), through C11."""
    return _o1_lb().lb_A(float(rho) if float(rho) != int(rho) else int(rho), m)


@functools.lru_cache(maxsize=None)
def lb_C(rho: float, m) -> tuple:
    """o1_lb.lb_C(rho, m) -> (max_p LB_C, p*), through C11."""
    return _o1_lb().lb_C(float(rho) if float(rho) != int(rho) else int(rho), m)


def k_star(rho: float, m: int) -> dict:
    """k* of O1-A (§5.3): o1_lb.json `A` field k where the file lists (rho, m), else o1_lb.lb_A (C11); k = 2 at
    m = 2, where O1-A does not apply."""
    if int(m) == 2:
        return {"k": 2, "LB_A": None, "source": "m = 2: O1-A needs m >= 3, k = 2 (§5.3)",
                "LB_A_note": "O1-A does not apply at m = 2"}
    row = o1_rows().get((float(rho), str(int(m))))
    if row is not None and row.get("k") is not None:
        return {"k": int(row["k"]), "LB_A": float(row["LB_A"]), "source": "o1_lb.json A"}
    la, k = lb_A(float(rho), int(m))
    return {"k": int(k), "LB_A": float(la), "source": "o1_lb.lb_A (C11)"}


def p_star(rho: float, m: int) -> dict:
    """p* of O1-C (§5.3): o1_lb.json `A` field p where listed, else o1_lb.lb_C (C11)."""
    row = o1_rows().get((float(rho), str(int(m))))
    if row is not None and row.get("p") is not None:
        return {"p": float(row["p"]), "LB_C_max": float(row["LB_C"]), "source": "o1_lb.json A"}
    lc, p = lb_C(float(rho), int(m))
    return {"p": float(p), "LB_C_max": float(lc), "source": "o1_lb.lb_C (C11)"}


def lb_T(rho: float, m: int, T: int, a: float = A, Dk: int = D) -> float:
    """C3-T4's bound LB_T = (A0 beta + a T) / ((A0 / m + 1) beta + a (T + D)), A0 = ceil(T / D),
    beta = (rho - 1) a D."""
    beta = (float(rho) - 1.0) * a * Dk
    A0 = math.ceil(T / Dk)
    return (A0 * beta + a * T) / ((A0 / m + 1.0) * beta + a * (T + Dk))


def o1b_bound(rho: float, m: int, T: int, opt: float, a: float = A, Dk: int = D) -> float:
    """O1-B: RR-renew has ALG <= min{rho (1 + D / T) OPT, 2 m OPT + a D}."""
    return min(float(rho) * (1.0 + Dk / T) * opt, 2.0 * m * opt + a * Dk)


def o1b_ok(alg: float, rho: float, m: int, T: int, opt: float) -> bool:
    """Check E10-3 on one RR-renew run (relative tolerance 1e-9)."""
    return bool(alg <= o1b_bound(rho, m, T, opt) * (1.0 + TOL))


def harmonic(m: int) -> float:
    return sum(1.0 / i for i in range(1, int(m) + 1))


def two_h_m_plus_1(m: int) -> float:
    return 2.0 * harmonic(m) + 1.0


def point(sched: str, rho: float, m: int) -> dict:
    """The family and lender parameters of one E10(a) point (§5.2, §5.3; M10, M12)."""
    rho, m = float(rho), int(m)
    beta = (rho - 1.0) * A * D
    out = {"sched": sched, "rho": rho, "m": m, "tau": TAU, "H": H_SLOTS, "D": D, "a": A, "beta": beta}
    if sched == "adaptive":
        out.update(T=C_T * m * D, lender_params={}, LB_T=lb_T(rho, m, C_T * m * D))
    elif sched == "safe_site":
        ks = k_star(rho, m)
        Phi = max(2, PHI_SLOTS // (ks["k"] * D))
        T = Phi * ks["k"] * D
        out.update(T=T, k_star=ks["k"], Phi=Phi, LB_A=ks["LB_A"], k_source=ks["source"],
                   lender_params={"D_slots": D, "k": ks["k"], "Phi": Phi}, OPT_closed_form=Phi * beta + A * T)
    elif sched == "iid_step":
        ps = p_star(rho, m)
        out.update(T=T_IID, p_star=ps["p"], U=T_IID // D, LB_C_max=ps["LB_C_max"], p_source=ps["source"],
                   lender_params={"D_slots": D, "p": ps["p"], "U": T_IID // D})
    else:
        raise ValueError(f"unknown E10(a) schedule {sched!r}")
    out["two_h_m_plus_1"] = two_h_m_plus_1(m)
    return out


def seed_pairs(sched: str, tag: str, seeds) -> list[tuple]:
    """(lender seed, policy seed) of the runs (M11): under 'adaptive' RR once (0, 0) and the others (0, s); under
    the oblivious lenders (s, s)."""
    if sched == "adaptive":
        return [(0, 0)] if tag in DETERMINISTIC else [(0, int(s)) for s in seeds]
    return [(int(s), int(s)) for s in seeds]


# ---------------------------------------------------------------- jobs
def a_id(sched, rho, m) -> str:
    return job_id(EXP, "a", sched=sched, rho=rho, m=int(m))


def rerun_id(sched, rho, m) -> str:
    return job_id(EXP, "rerun", sched=sched, rho=rho, m=int(m))


def b_id(rho, m) -> str:
    return job_id(EXP, "b", rho=rho, m=int(m))


def b_milp_id(sched, rho, m, key) -> str:
    return job_id(EXP, "b_milp", sched=sched, rho=rho, m=int(m), key=key)


def est_run_s(sched: str, m: int, T: int) -> float:
    if sched == "adaptive":
        return EST_ADAPTIVE_S * (T * m) / (3072 * 64)
    if sched == "safe_site":
        return EST_SAFE_S
    return EST_IID_S


def a_points(ms=MS) -> list[tuple]:
    return [(s, r, m) for s in SCHEDS_A for r in RHOS for m in ms]


def jobs() -> list[Job]:
    d = design()
    out = [Job(job_id(EXP, "repro"), "pool", {"m": list(REPRO_MS), "rho": list(REPRO_RHOS)}, est_s=EST_REPRO_S)]
    od = default_out()
    reruns = []
    for (s, r, m) in a_points(d["ms"]):
        T = C_T * m * D if s == "adaptive" else (T_IID if s == "iid_step" else PHI_SLOTS)
        n = sum(len(seed_pairs(s, t, range(d["n_seeds"]))) for t in SCHED_TAGS[s])
        out.append(Job(a_id(s, r, m), "pool", {"sched": s, "rho": r, "m": int(m), "n_seeds": d["n_seeds"]},
                       est_s=n * est_run_s(s, m, T)))
        res = _ok_output(od, a_id(s, r, m), a_file(od, s, r, m))     # only an 'ok' e10:a output flags a point
        flagged = sorted((res or {}).get("flagged") or {})
        if flagged:
            reruns.append(Job(rerun_id(s, r, m), "pool", {"sched": s, "rho": r, "m": int(m), "tags": flagged,
                                                          "seeds": [RERUN_SEEDS[0], RERUN_SEEDS[-1]]},
                              est_s=len(flagged) * len(RERUN_SEEDS) * est_run_s(s, m, T)))
    out += reruns
    for r in RHOS_B:
        for m in d["ms_b"]:
            out.append(Job(b_id(r, m), "pool", {"rho": r, "m": int(m), "seeds": list(d["seeds_b"])}, est_s=None))
    milp_s = mc.wall_timeout_s()
    for sched in SCHEDS_B:
        for r in RHOS_B:
            for m in d["ms_b"]:
                for key in b_keys(sched, d["seeds_b"]):
                    out.append(Job(b_milp_id(sched, r, m, key), "milp", {"sched": sched, "rho": r, "m": int(m),
                                                                         "key": key}, est_s=milp_s))
    return out


# ---------------------------------------------------------------- E10(a): runs
def fam_instance(F):
    from ..instance import from_core
    inst, _ = from_core(F.core_instance(), [np.zeros(0, dtype=np.int64)] * int(F.m))
    return inst


def fam_run(F, sched: str, lender_params: dict, tag: str, lender_seed: int, policy_seed: int, tags=None):
    """One engine run of `tag` on the family instance of F under the lender `sched` (invariant checks on)."""
    from ..drivers import run as drun
    from ..engine import EngineConfig, simulate
    from ..types import LenderModel
    pid, params, info = (tags or TAGS)[tag]
    inst = fam_instance(F)
    vals, _ = drun.driver_inputs(pid, dict(params), inst)
    pol = drun.make_policy({"policy": {"id": pid, "params": copy.deepcopy(params)}}, inst, inputs=vals)
    model = LenderModel(schedule=sched, information=info, params=dict(lender_params))
    res = simulate(inst, pol, model, EngineConfig(check_invariants=True), lender_seed=int(lender_seed),
                   policy_seed=int(policy_seed))
    return res, inst


def run_point(pt: dict, tags, seeds, errors: list, label: str) -> list[dict]:
    """The runs of `tags` at one E10(a) point, with the exact OPT (fam.opt_dp; per schedule under the oblivious
    lenders, per run under 'adaptive') and the per-run checks E10-2 (adaptive), E10-3 (RR-renew), E10-4
    (safe_site)."""
    from ..drivers.bench import bench_for
    from ..paths import import_ref
    fam = import_ref("fam")
    sched, rho, m, T = pt["sched"], pt["rho"], pt["m"], pt["T"]
    F = fam.Fam(m, rho, TAU, H_SLOTS, T)
    opts: dict = {}           # lender seed -> (schedule hash, OPT) under the oblivious lenders
    rows = []
    for tag in tags:
        for (l, p) in seed_pairs(sched, tag, seeds):
            def one(tag=tag, l=l, p=p):
                t0 = time.perf_counter()
                res, inst = fam_run(F, sched, pt["lender_params"], tag, l, p)
                t1 = time.perf_counter()
                sh = mc.schedule_hash(res.schedule)
                if sched in OBLIVIOUS and l in opts:
                    if opts[l][0] != sh:
                        raise RuntimeError(f"lender seed {l}: the oblivious schedule differs between tags")
                    opt = opts[l][1]
                else:
                    opt = float(bench_for(res, inst, "fam", fam=F).objective)
                    if sched in OBLIVIOUS:
                        opts[l] = (sh, opt)
                alg = float(res.components["total"])
                row = {"tag": tag, "lender_seed": int(l), "policy_seed": int(p), "ALG": alg, "OPT": opt,
                       "ratio": alg / opt if opt > 0 else None, "schedule_hash": sh,
                       "n_announcements": int(sum(len(r) for r in res.schedule.R)), "leases": len(res.leases),
                       "n_invariant_failures": len(res.invariant_failures),
                       "engine_s": t1 - t0, "opt_s": time.perf_counter() - t1}
                if sched == "adaptive":
                    row["E10_2_ok"] = bool(row["ratio"] is not None and row["ratio"] >= pt["LB_T"] - TOL)
                if tag == "RR":
                    row["O1B_bound"] = o1b_bound(rho, m, T, opt)
                    row["E10_3_ok"] = o1b_ok(alg, rho, m, T, opt)
                if sched == "safe_site":
                    cf = pt["OPT_closed_form"]
                    row["E10_4_diff"] = abs(opt - cf) / max(1.0, abs(cf))
                    row["E10_4_ok"] = bool(row["E10_4_diff"] <= TOL)
                rows.append(row)
            mc.try_run(errors, f"{label} {tag} l{l} p{p}", one)
    return rows


def tag_aggregate(rows: list[dict], pt: dict) -> dict:
    """E[ALG] / E[OPT] over the runs of one tag (M13) with its bootstrap interval, the per-run min and max."""
    alg = [r["ALG"] for r in rows]
    opt = [r["OPT"] for r in rows]
    rm = mc.ratio_of_means(alg, opt, B=B_BOOT, seed=BOOT_SEED)
    per = [r["ratio"] for r in rows if r["ratio"] is not None]
    e = {"ratio": rm["ratio"], "ci95": rm["ci95"], "runs": len(rows), "T": pt["T"],
         "alg": rm["mean_alg"], "opt": rm["mean_opt"],
         "min": min(per) if per else None, "max": max(per) if per else None}
    for k in ("k_star", "Phi", "p_star", "U"):
        if k in pt:
            e[k] = pt[k]
    if rm.get("ratio_note"):
        e["ratio_note"] = rm["ratio_note"]
    if not per:
        e["min_note"] = e["max_note"] = "no run with OPT > 0"
    return e


def flags(pt: dict, aggs: dict) -> dict:
    """E10-5 and E10-6 at one point (M14): O1-A under 'safe_site' at m >= 3 for the private tags (upper end of the
    95% interval below LB_A(k*) - 1e-9), O1-D for marking under the oblivious lenders (lower end above 2 h_m + 1)."""
    out = {}
    for tag, e in aggs.items():
        lo, hi = (e.get("ci95") or [None, None])
        if pt["sched"] == "safe_site" and pt["m"] >= 3 and tag in PRIVATE and pt.get("LB_A") is not None \
                and hi is not None and hi < pt["LB_A"] - TOL:
            out[tag] = {"check": "E10-5", "ci95_hi": hi, "LB_A": pt["LB_A"]}
        if tag == "MARK" and pt["sched"] in OBLIVIOUS and lo is not None and lo > pt["two_h_m_plus_1"]:
            out[tag] = {"check": "E10-6", "ci95_lo": lo, "two_h_m_plus_1": pt["two_h_m_plus_1"]}
    return out


def run_a(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    p = job.params
    pt = point(p["sched"], p["rho"], p["m"])
    errors: list = []
    t0 = time.perf_counter()
    tags = SCHED_TAGS[pt["sched"]]
    rows = run_point(pt, tags, range(int(p["n_seeds"])), errors, job.id)
    aggs = {t: tag_aggregate([r for r in rows if r["tag"] == t], pt) for t in tags}
    fl = flags(pt, aggs)
    res = {"meta": {"exp": EXP, "job": job.id, "point": pt, "instance": f"fam.Fam({pt['m']}, {pt['rho']:g}, {TAU}, "
                    f"{H_SLOTS}, {pt['T']}).core_instance() via instance.from_core",
                    "n_seeds": int(p["n_seeds"]), "git_revision": mc.git_revision(), "versions": mc.versions(),
                    "written": _now(), "wall_s": time.perf_counter() - t0},
           "runs": rows, "tags": aggs, "flagged": fl,
           "errors": [{k: v for k, v in e.items() if k != "traceback"} for e in errors]}
    outputs.dump(res, a_file(out, pt["sched"], pt["rho"], pt["m"]))
    for t, e in aggs.items():
        print(f"[e10] {job.id} {t}: E[ALG]/E[OPT] {e['ratio']} {e['ci95']} over {e['runs']} runs", flush=True)
    return {"runs": len(rows), "errors": errors, "flagged": sorted(fl)}


def run_rerun(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """Seeds 30-129 of the flagged tags at one point (E10-5, E10-6; M14)."""
    p = job.params
    pt = point(p["sched"], p["rho"], p["m"])
    prev = mc.read_json(a_file(out, pt["sched"], pt["rho"], pt["m"]))
    if prev is None:
        raise FileNotFoundError("the point's e10:a output is missing")
    errors: list = []
    tags = sorted(prev.get("flagged") or {})
    rows = run_point(pt, tags, RERUN_SEEDS, errors, job.id)
    comb = {t: tag_aggregate([r for r in prev["runs"] + rows if r["tag"] == t], pt) for t in tags}
    res = {"meta": {"exp": EXP, "job": job.id, "point": pt, "seeds": [RERUN_SEEDS[0], RERUN_SEEDS[-1]],
                    "git_revision": mc.git_revision(), "written": _now()},
           "runs": rows, "flagged_before": prev.get("flagged"), "combined": comb,
           "still_flagged": flags(pt, comb),
           "errors": [{k: v for k, v in e.items() if k != "traceback"} for e in errors]}
    outputs.dump(res, rerun_file(out, pt["sched"], pt["rho"], pt["m"]))
    return {"runs": len(rows), "errors": errors, "still_flagged": sorted(res["still_flagged"])}


# ---------------------------------------------------------------- E10-1 and E10-9 (job e10:repro)
def repro_rows(points) -> list[dict]:
    """E10-1: repro_c4_lower.part_a_row (the R2 path of the MS2 spec §17.3) at each (m, rho) against
    c3/out/c4_lower.json `a` (rr, stay, pd_r1, pd_r1_min, pd_rth, pd_rth_min, LB_T)."""
    from ..paths import C3
    from .repro_c4_lower import part_a_row
    ref = {(int(r["m"]), float(r["rho"])): r for r in (mc.read_json(C3 / "out" / "c4_lower.json") or {}).get("a", [])}
    rows = []
    for (m, rho) in points:
        t0 = time.perf_counter()
        r = part_a_row((int(m), int(rho) if float(rho) == int(rho) else float(rho)))
        x = ref.get((int(m), float(rho)))
        vals = {k: r[k] for k in REPRO_COLS}
        diff = {k: (abs(float(vals[k]) - float(x[k])) if x is not None and x.get(k) is not None else None)
                for k in REPRO_COLS}
        rows.append({"m": int(m), "rho": float(rho), "values": vals, "ref": None if x is None else
                     {k: x.get(k) for k in REPRO_COLS}, "diff": diff,
                     "R_equals_real_cost_renew": {k: r.get(f"{k}_R_equals_real_cost_renew")
                                                  for k in ("pd_r1", "pd_rth")},
                     "pass": bool(x is not None and all(v is not None and v <= TOL for v in diff.values())),
                     "seconds": time.perf_counter() - t0})
    return rows


def o1_recompute() -> dict:
    """E10-9: o1_lb.lb_A and lb_C through import_ref (C11) at every (rho, m) that o1_lb.json `A` lists, against
    the file (k, p and the bounds; o1_lb.part_A's rule at m = 2: LB_A 1, k null)."""
    rows, ok = [], True
    for (rho, ms), x in sorted(o1_rows().items(), key=lambda kv: (kv[0][0], float(kv[0][1]))):
        m = math.inf if ms == "inf" else int(ms)
        r = int(rho) if float(rho) == int(rho) else float(rho)
        la, k = (1.0, None) if m == 2 else lb_A(r, m)
        lc, p = lb_C(r, m)
        diff = {"LB_A": abs(la - float(x["LB_A"])), "LB_C": abs(lc - float(x["LB_C"])),
                "p": abs(float(p) - float(x["p"])) if p is not None and x.get("p") is not None else None}
        same_k = (k is None and x.get("k") is None) or (k is not None and x.get("k") is not None
                                                        and int(k) == int(x["k"]))
        good = same_k and diff["LB_A"] <= 1e-12 and diff["LB_C"] <= 1e-12 and (diff["p"] or 0.0) <= 1e-12
        ok &= good
        rows.append({"rho": float(rho), "m": ms, "LB_A": la, "k": k, "LB_C": lc, "p": p,
                     "ref": {kk: x.get(kk) for kk in ("LB_A", "k", "LB_C", "p")}, "diff": diff, "same_k": same_k,
                     "pass": bool(good)})
    return {"rows": rows, "n": len(rows), "pass": bool(ok and rows)}


def run_repro(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    t0 = time.perf_counter()
    rows = repro_rows([(m, r) for m in REPRO_MS for r in REPRO_RHOS])
    pd_cols = ("pd_r1", "pd_r1_min", "pd_rth", "pd_rth_min")
    mx = max((v for r in rows for v in r["diff"].values() if v is not None), default=None)
    o1 = o1_recompute()
    res = {"meta": {"exp": EXP, "job": job.id, "path": "repro_c4_lower.part_a_row (MS2 spec §17.3, R2)",
                    "reference": "code/theory_checks/c3/out/c4_lower.json a",
                    "o1_reference": "code/theory_checks/c3/o1/out/o1_lb.json A",
                    "git_revision": mc.git_revision(), "versions": mc.versions(), "written": _now(),
                    "wall_s": time.perf_counter() - t0},
           "rows": rows, "n": len(rows), "max_abs_diff": mx,
           "pass": bool(len(rows) == len(REPRO_MS) * len(REPRO_RHOS) and all(r["pass"] for r in rows)),
           "pass_pd": bool(rows and all(r["ref"] is not None and all((r["diff"][k] or 0.0) <= TOL for k in pd_cols)
                                        for r in rows)),
           "o1_lb": o1}
    outputs.dump(res, Path(out) / "repro.json")
    return {"runs": 0, "pass": res["pass"], "o1_lb_pass": o1["pass"], "max_abs_diff": mx}


# ---------------------------------------------------------------- E10(b): instances (§5.4, M15, M49)
def base_config(series: str) -> dict:
    """The §6.3 base instance of (lender a2:c05, series, H = 60, mu/beta~ = 1, alignment 1): configs/
    ms2_single_site.json with one week, the 1-min grid, seed 1, the contracts s5_tau5_H60 and protected, the lender
    with 8 layers of 8 GPUs and the series borrower."""
    from ..paths import SIM
    cfg = mc.read_json(SIM / "configs" / "ms2_single_site.json")
    cfg = copy.deepcopy(cfg)
    k = f"s5_tau5_H{B_H}"
    cfg["name"] = "e10b_base"
    cfg["seed"] = B_C
    cfg["time"]["horizon_min"] = 10080
    cfg["time"]["fast_slot_min"] = 1
    cfg["contracts"] = [{"id": k, "tau_min": 5, "H_min": B_H},
                        {"id": "protected", "tau_min": None, "H_min": 0, "prepaid_min": 5}]
    cfg["lenders"][0] = {"id": B_LENDER, "kind": "trace", "region": "europe", "group": B_LENDER,
                         "n_layers": N_LAYERS, "layer_gpus": 8, "lease_size_quantile": 25, "offset": "random",
                         "load_scenario": "a5_2GBps", "menu": [k]}
    cfg["borrowers"] = {"model": "series", "list": [{"id": "b0", "series": series, "tier": "M", "region": "europe",
                                                      "slo_class": "strict"}],
                        "own_capacity_quantile": 75, "smoothing_min": 15, "market_tightness": 0.5}
    cfg["stranding"]["mu_over_beta_tilde"] = B_MU
    return cfg


@functools.lru_cache(maxsize=None)
def e10b_layers(series: str) -> tuple:
    """(active (8, 288) bool, meta): the 8 one-replica demand layers of §6.3 (x' = 8 x / P99.5(x) over the week,
    layer k on iff x' >= k) on day 0 (fast slots 0-1439), aggregated to 5-min slots (on if on in any minute)."""
    from ..instance import build_instance
    if series not in E2_SERIES:
        raise ValueError(f"unknown E2 series {series!r}")
    inst = build_instance(base_config(series))
    g = inst.grid
    if g.fast_min != 1:
        raise RuntimeError("the E10(b) base instance must be on the 1-min grid")
    x = np.asarray(inst.clients.demand[0], dtype=np.float64)
    p995 = float(np.percentile(x, 99.5))
    xs = N_LAYERS * x / p995 if p995 > 0 else np.zeros_like(x)
    lay = np.array([xs >= k for k in range(1, N_LAYERS + 1)], dtype=bool)[:, :T_B * SLOT_B]
    act = lay.reshape(N_LAYERS, T_B, SLOT_B).any(axis=2)
    act.setflags(write=False)
    meta = {"series": series, "p995_loads": p995, "start_mow": int(g.start_mow), "on_share_5min":
            act.mean(axis=1).tolist(), "empty": not bool(act.any())}
    return act, meta


def general_core(m: int, rho: float, b: str):
    """E10(b)'s core instance (§5.4): T = 288 slots, m sites, J = 2 LLMs with g = (1, 2), one contract (tau 2,
    H 1), a = 1, beta_j = (rho - 1) g_j a D, q = max_j beta_j + max_j g_j a D + 1, delta = 0, n = 8 clients, client
    k with demand layer k + 1 of series b (e10b_layers) and LLM k mod 2."""
    from ..paths import import_ref
    core = import_ref("core")
    act, _ = e10b_layers(b)
    g = np.array(G_B, dtype=np.int64)
    beta = np.repeat(((float(rho) - 1.0) * g * A * D)[:, None], int(m), axis=1).astype(np.float64)
    q = float(beta.max() + g.max() * A * D + 1.0)
    return core.Instance(T=T_B, tau=np.array([TAU]), H=np.array([H_SLOTS]), a=np.full((int(m), 1), A),
                         beta=beta, g=g, q=q, cl_llm=np.arange(N_LAYERS, dtype=np.int64) % len(G_B),
                         delta=np.zeros((N_LAYERS, int(m))), active=np.array(act, dtype=bool))


@functools.lru_cache(maxsize=None)
def trace_omegas() -> tuple:
    """(omega per lender a2:c00 ... a2:c15, meta): the announcement set of each lender's one site in
    configs/ms3_e10b_trace.json under the 'trace' schedule (lender.build_R; equal to every 'trace' run's realized
    schedule). A lender without exactly one site is an error."""
    from ..instance import build_instance
    from ..lender import build_R
    from ..paths import SIM
    from ..types import LenderModel
    inst = build_instance(str(SIM / "configs" / TRACE_CONFIG))
    if inst.grid.T_slow != T_B or inst.grid.slow_min != SLOT_B:
        raise RuntimeError(f"{TRACE_CONFIG}: expected {T_B} slots of {SLOT_B} min")
    R = build_R(inst, LenderModel(schedule="trace"), np.random.default_rng(0))
    om, sites = [], []
    for lid in TRACE_LENDERS:
        idx = [i for i, s in enumerate(inst.sites) if s.lender == lid]
        if len(idx) != 1:
            raise ValueError(f"{TRACE_CONFIG}: lender {lid} has {len(idx)} sites (one expected)")
        om.append(np.asarray(R[idx[0]], dtype=np.int64))
        sites.append(inst.sites[idx[0]].id)
    meta = {"config": f"configs/{TRACE_CONFIG}", "sites": sites, "announcements": [int(len(r)) for r in om]}
    return tuple(om), meta


def trace_omega(m: int) -> list:
    om, _ = trace_omegas()
    if int(m) > len(om):
        raise ValueError(f"E10(b) 'trace' has {len(om)} lenders, m = {m}")
    return [r.copy() for r in om[:int(m)]]


def safe_site_params(m: int) -> dict:
    k = max(2, int(m))
    return {"D_slots": D, "k": k, "Phi": T_B // (k * D)}


def b_instance(sched: str, m: int, rho: float, s: int):
    """(core instance, omega passed to from_core, engine instance, series) of E10(b) seed s under `sched`."""
    from ..instance import from_core
    b = E2_SERIES[int(s) % len(E2_SERIES)]
    I = general_core(m, rho, b)
    om = trace_omega(m) if sched == "trace" else [np.zeros(0, dtype=np.int64)] * int(m)
    inst, _ = from_core(I, om, slot_min=SLOT_B)
    return I, om, inst, b


def run_b(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    from ..drivers import run as drun
    from ..engine import EngineConfig, simulate
    from ..types import LenderModel
    p = job.params
    rho, m = float(p["rho"]), int(p["m"])
    errors: list = []
    rows = []
    t0 = time.perf_counter()
    for sched in SCHEDS_B:
        for s in p["seeds"]:
            def one_seed(sched=sched, s=int(s)):
                I, om, inst, b = b_instance(sched, m, rho, s)
                ih = mc.instance_hash(inst)
                lp = safe_site_params(m) if sched == "safe_site" else {}
                for tag, (pid, params, info) in TAGS_B.items():
                    t1 = time.perf_counter()
                    vals, _ = drun.driver_inputs(pid, dict(params), inst)
                    pol = drun.make_policy({"policy": {"id": pid, "params": dict(params)}}, inst, inputs=vals)
                    res = simulate(inst, pol, LenderModel(schedule=sched, information=info, params=dict(lp)),
                                   EngineConfig(check_invariants=True), lender_seed=s, policy_seed=s)
                    rows.append({"sched": sched, "seed": s, "series": b, "tag": tag, "policy_id": pid,
                                 "information": info, "lender_params": lp, "ALG": float(res.components["total"]),
                                 "instance_hash": ih, "schedule_hash": mc.schedule_hash(res.schedule),
                                 "R": [np.asarray(r, dtype=np.int64).tolist() for r in res.schedule.R],
                                 "n_announcements": int(sum(len(r) for r in res.schedule.R)),
                                 "n_invariant_failures": len(res.invariant_failures),
                                 "empty_instance": not bool(np.asarray(I.active).any()),
                                 "milp_key": s if sched == "safe_site" else b, "wall_s": time.perf_counter() - t1})
            mc.try_run(errors, f"{job.id} {sched} s{s}", one_seed)
    res = {"meta": {"exp": EXP, "job": job.id, "rho": rho, "m": m, "seeds": list(p["seeds"]), "T": T_B,
                    "slot_min": SLOT_B, "layers": {b: e10b_layers(b)[1] for b in
                                                   dict.fromkeys(E2_SERIES[int(s) % 5] for s in p["seeds"])},
                    "trace": trace_omegas()[1], "git_revision": mc.git_revision(), "versions": mc.versions(),
                    "written": _now(), "wall_s": time.perf_counter() - t0},
           "runs": rows, "errors": [{k: v for k, v in e.items() if k != "traceback"} for e in errors]}
    outputs.dump(res, b_file(out, rho, m), compact=True)
    return {"runs": len(rows), "errors": errors}


def run_b_milp(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """solve_core of one (instance, omega) of E10(b) with Q39's rule (§5.4), after the hash checks."""
    from ..opt.milp import _bench_core, _count, solve_core
    p = job.params
    sched, rho, m, key = p["sched"], float(p["rho"]), int(p["m"]), p["key"]
    runs = (mc.read_json(b_file(out, rho, m)) or {}).get("runs")
    if runs is None:
        raise FileNotFoundError(f"no E10(b) run file {b_file(out, rho, m)} (run {b_id(rho, m)} first)")
    mine = [r for r in runs if r["sched"] == sched and str(r["milp_key"]) == str(key)]
    if not mine:
        raise FileNotFoundError(f"no E10(b) run with sched {sched} and key {key}")
    s = int(mine[0]["seed"])
    I, om, inst, b = b_instance(sched, m, rho, s)
    ih = mc.instance_hash(inst)
    if any(r["instance_hash"] != ih for r in mine):
        raise RuntimeError(f"rebuilt instance hash {ih[:12]} differs from the runs'")
    shs = {r["schedule_hash"] for r in mine}
    if len(shs) != 1:
        raise RuntimeError(f"{len(shs)} realized schedules for one (instance, omega): the lender is not oblivious")
    omega = [np.asarray(r, dtype=np.int64) for r in mine[0]["R"]]
    if sched == "trace" and any(not np.array_equal(a_, b_) for a_, b_ in zip(omega, trace_omega(m))):
        raise RuntimeError("the realized 'trace' schedule differs from the static trace omega")
    est = _count(_bench_core(I, omega))
    gate = {"n_vars": est["n_vars"], "nnz": est["nnz"], "est_mb": est["est_mb"]}
    if est["n_vars"] > GATE_VARS or est["est_mb"] > GATE_MB:
        raise RuntimeError(f"model above the S36 gate ({gate}): run it as an 'alone' job")
    t0 = time.perf_counter()
    limit = mc.milp_limit_s()
    sr = solve_core(I, omega, time_limit_s=limit, mip_rel_gap=MILP_GAP)
    size = sr.size or {}
    rec = {"job": job.id, "sched": sched, "rho": rho, "m": m, "key": key, "series": b, "seeds": sorted(
           {int(r["seed"]) for r in mine}), "instance_hash": ih, "schedule_hash": next(iter(shs)),
           "method": sr.method, "benchmark": sr.benchmark, "grid": sr.grid, "status": sr.status,
           "status_msg": sr.status_msg, "objective": sr.objective, "dual_bound": sr.dual_bound, "gap": sr.gap,
           "size": {k: size.get(k) for k in ("n_vars", "n_int", "n_rows", "nnz") if k in size}, "estimate": gate,
           "time_limit_s": limit, "mip_rel_gap": MILP_GAP, "build_s": sr.build_s, "solve_s": sr.solve_s,
           "peak_rss_mb": sr.peak_rss_mb, "wall_s": time.perf_counter() - t0, "git_revision": mc.git_revision()}
    outputs.dump(rec, b_milp_file(out, sched, rho, m, key))
    return {"runs": 0, "status": sr.status, "objective": sr.objective, "dual_bound": sr.dual_bound,
            "gap": sr.gap, "n_vars": rec["size"].get("n_vars")}


# ---------------------------------------------------------------- dispatch, manifest
def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    _, part, _ = mc.parse_job_id(job.id)
    fn = {"a": run_a, "rerun": run_rerun, "repro": run_repro, "b": run_b, "b_milp": run_b_milp}.get(part)
    if fn is None:
        raise ValueError(f"unknown E10 job {job.id!r}")
    return fn(job, outputs, out)


def manifest_extra(out: Path) -> dict:
    """The instance hashes of the E10(a) family instances and of the E10(b) instances (§2.6)."""
    from ..paths import import_ref
    fam = import_ref("fam")
    d = design()
    ha, hb = {}, {}
    for (s, r, m) in a_points(d["ms"]):
        pt = point(s, r, m)
        ha[f"{s}:rho={num_key(r)}:m={m}"] = mc.instance_hash(fam_instance(fam.Fam(m, r, TAU, H_SLOTS, pt["T"])))
    for sched in SCHEDS_B:
        for r in RHOS_B:
            for m in d["ms_b"]:
                for s in d["seeds_b"]:
                    hb[f"{sched}:rho={num_key(r)}:m={m}:s={s}"] = mc.instance_hash(b_instance(sched, m, r, s)[2])
    return {"instance_hashes": {"a": ha, "b": hb}, "design": {k: (list(v) if isinstance(v, tuple) else v)
                                                             for k, v in d.items()}}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------- value of public information (M52)
def _vp_notes(out: dict, note: str) -> dict:
    """A value_public entry without a ratio: every null field with its '*_note' (§2.6)."""
    for k in ("best_private", "best_public", "mean_private", "mean_public", "ratio"):
        if out.get(k) is None:
            put(out, k, None, note)
    out["ci95_note"] = note
    return out


def value_public(alg_by_tag: dict, private=PRIVATE, public=PUBLIC, B: int = B_BOOT, seed: int = BOOT_SEED) -> dict:
    """The value of public reclaim information under one oblivious lender (design §5.5, M52): the best private
    (I1) policy's mean cost over the best public (I2) policy's mean cost, best = the smallest mean cost among the
    class's tags run there, with a 95% bootstrap interval that resamples the paired seeds (B resamples drawn with
    default_rng(seed); the best tags are fixed on the full sample). alg_by_tag: {tag: {seed: ALG}}; only the seeds
    common to the two chosen tags are used."""
    means = {t: float(np.mean(list(v.values()))) for t, v in alg_by_tag.items() if v}
    pv = {t: means[t] for t in private if t in means}
    pb = {t: means[t] for t in public if t in means}
    out = {"best_private": None, "best_public": None, "mean_private": None, "mean_public": None, "ratio": None,
           "ci95": [None, None], "n_pairs": 0, "B": int(B), "seed": int(seed), "means": means}
    if not pv or not pb:
        return _vp_notes(out, "no run of a private or of a public tag")
    tp, tb = min(pv, key=pv.get), min(pb, key=pb.get)
    common = sorted(set(alg_by_tag[tp]) & set(alg_by_tag[tb]))
    a = np.array([alg_by_tag[tp][s] for s in common], dtype=np.float64)
    b = np.array([alg_by_tag[tb][s] for s in common], dtype=np.float64)
    out.update(best_private=tp, best_public=tb, n_pairs=len(common))
    if not common or b.sum() <= 0:
        return _vp_notes(out, "no common seeds or zero public cost")
    out.update(mean_private=float(a.mean()), mean_public=float(b.mean()), ratio=float(a.sum() / b.sum()))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(common), size=(int(B), len(common)))
    den = b[idx].sum(axis=1)
    r = np.where(den > 0, a[idx].sum(axis=1) / np.where(den > 0, den, 1.0), np.nan)
    r = r[np.isfinite(r)]
    if len(r):
        lo, hi = np.percentile(r, [2.5, 97.5])
        out["ci95"] = [float(lo), float(hi)]
    return out


# ---------------------------------------------------------------- summary
def _null_entry(note: str, extra: Optional[dict] = None) -> dict:
    e = {"runs": 0}
    for k in ("ratio", "min", "max", "alg", "opt"):
        put(e, k, None, note)
    e["ci95"] = [None, None]
    e["ci95_note"] = note
    e.update(extra or {})
    return e


def bounds_entry(rho: float, m: int, rr_adaptive: Optional[dict]) -> dict:
    """bounds.<rho>.<m> (§5.5): the theory lines of Figs. 5(c) and 6 and their sources."""
    ks, ps = k_star(rho, m), p_star(rho, m)
    beta = (float(rho) - 1.0) * A * D
    Phi = max(2, PHI_SLOTS // (ks["k"] * D))
    T_ss = Phi * ks["k"] * D
    T_ad = C_T * m * D
    opt_ss = Phi * beta + A * T_ss
    e = {"k_star": ks["k"], "p_star": ps["p"], "Phi": Phi, "T_safe_site": T_ss, "T_adaptive": T_ad,
         "T_iid_step": T_IID, "LB_C_max": ps["LB_C_max"], "LB_T": lb_T(rho, m, T_ad),
         "limit": float(rho) * m / (m + float(rho) - 1.0),
         "O1B_safe_site": min(float(rho) * (1.0 + D / T_ss), 2.0 * m + A * D / opt_ss),
         "OPT_safe_site": opt_ss, "two_h_m_plus_1": two_h_m_plus_1(m), "UB_I1": min(float(rho), 2.0 * m),
         "UB_I2": min(float(rho), two_h_m_plus_1(m)),
         "source": {"k_star": ks["source"], "p_star": ps["source"], "LB_A": ks["source"], "LB_C_max": ps["source"]}}
    put(e, "LB_A", ks["LB_A"], ks.get("LB_A_note"))
    if rr_adaptive and rr_adaptive.get("opt"):
        e["O1B_adaptive"] = min(float(rho) * (1.0 + D / T_ad), 2.0 * m + A * D / float(rr_adaptive["opt"]))
        e["OPT_RR_adaptive"] = float(rr_adaptive["opt"])
    else:
        put(e, "O1B_adaptive", None, "no RR-renew run under 'adaptive' at this point in the outputs")
    return e


def _agg_note(values: list, note: str) -> dict:
    """metrics.aggregate of `values`; with no values its null fields carry '*_note' (§2.6)."""
    a = mc.median_summary(values)
    if not values:
        for k in ("median", "p95", "max"):
            put(a, k, None, note)
        a["median_ci95_note"] = note
    return a


def b_entry(rows: list[dict], note: str) -> dict:
    """b.<sched>.<rho>.<m>.<tag>: Q39's ratios over the seeds of one E10(b) point (§5.5)."""
    if not rows:
        e = {**_null_entry(note), "inc_ci95": [None, None], "inc_ci95_note": note,
             "ratio_LB": _agg_note([], note), "ratio_inc": _agg_note([], note), "runs_with_LB": 0,
             "empty_instances": 0, "T": T_B}
        del e["opt"], e["opt_note"]                    # part b has lb and incumbent in place of opt (below)
        for k in ("inc", "share_exact", "max_gap", "lb", "incumbent"):
            put(e, k, None, note)
        return e
    withlb = [r for r in rows if r["lb"].get("LB") is not None]
    withinc = [r for r in rows if r["lb"].get("incumbent") is not None]
    rm = mc.ratio_of_means([r["ALG"] for r in withlb], [r["lb"]["LB"] for r in withlb], B=B_BOOT, seed=BOOT_SEED)
    ri = mc.ratio_of_means([r["ALG"] for r in withinc], [r["lb"]["incumbent"] for r in withinc], B=B_BOOT,
                           seed=BOOT_SEED)
    rl = [r["lb"]["ratio_LB"] for r in rows if r["lb"].get("ratio_LB") is not None]
    rc = [r["lb"]["ratio_inc"] for r in rows if r["lb"].get("ratio_inc") is not None]
    gaps = [r["lb"]["gap"] for r in rows if r["lb"].get("gap") is not None]
    e = {"ratio": rm["ratio"], "ci95": rm["ci95"], "inc": ri["ratio"], "inc_ci95": ri["ci95"],
         "ratio_LB": _agg_note(rl, "no run with a positive lower bound"),
         "ratio_inc": _agg_note(rc, "no run with a positive incumbent"),
         "share_exact": sum(bool(r["lb"].get("exact")) for r in rows) / len(rows),
         "max_gap": max(gaps) if gaps else None, "runs": len(rows), "runs_with_LB": len(withlb),
         "empty_instances": sum(bool(r["empty_instance"]) for r in rows), "T": T_B,
         "alg": float(np.mean([r["ALG"] for r in rows])), "lb": rm["mean_opt"], "incumbent": ri["mean_opt"],
         "min": min(rl) if rl else None, "max": max(rl) if rl else None}
    for k in ("ratio", "inc", "max_gap", "lb", "incumbent", "min", "max"):
        if e[k] is None:
            put(e, k, None, rm.get("ratio_note") or "no run with a lower bound or incumbent")
    return e


def _ok_output(out: Path, jid: str, path, ignored: Optional[list] = None) -> Optional[dict]:
    """The JSON output `path` of job `jid`, or None unless the job's record says 'ok' (§2.4: only 'ok' counts as
    done). An output that exists while its record is not 'ok' (left by an earlier run of a job that later failed or
    was killed) is not used and is listed in `ignored`."""
    rec = mc.read_record(out, jid)
    if rec is None or rec.get("status") != "ok":
        if ignored is not None and Path(path).is_file():
            ignored.append({"job": jid, "status": None if rec is None else rec.get("status"), "output": str(path)})
        return None
    return mc.read_json(path)


def summary(out: Path) -> dict:
    out = Path(out)
    d = design()
    ignored: list = []      # outputs whose job record is not 'ok' (not used)
    a_res = {}
    for (s, r, m) in a_points(MS):
        x = _ok_output(out, a_id(s, r, m), a_file(out, s, r, m), ignored)
        if x is not None:
            a_res[(s, r, m)] = x
    reruns = {}
    for k in a_res:
        v = _ok_output(out, rerun_id(*k), rerun_file(out, *k), ignored)
        if v is not None:
            reruns[k] = v
    # part a
    a: dict = {}
    for (s, r, m) in a_points(MS):
        x = a_res.get((s, r, m))
        pt = point(s, r, m)
        known = {k: pt[k] for k in ("T", "k_star", "Phi", "p_star", "U") if k in pt}
        for tag in SCHED_TAGS[s]:
            if x is None or tag not in x["tags"]:
                ent = _null_entry("no e10:a output at this point" if x is None else "tag not run", known)
            else:
                ent = dict(x["tags"][tag])
                ent["seeds"] = "lender 0, policy 0" if (s == "adaptive" and tag in DETERMINISTIC) else \
                    ("lender 0, policy 0-" + str(x["meta"]["n_seeds"] - 1) if s == "adaptive" else
                     "lender = policy = 0-" + str(x["meta"]["n_seeds"] - 1))
            a.setdefault(s, {}).setdefault(num_key(r), {}).setdefault(str(m), {})[tag] = ent
    # bounds
    bounds: dict = {}
    for r in RHOS:
        for m in MS:
            x = a_res.get(("adaptive", r, m))
            rr = (x or {}).get("tags", {}).get("RR")
            bounds.setdefault(num_key(r), {})[str(m)] = bounds_entry(r, m, rr)
    # value of public information
    vp: dict = {}
    for s in OBLIVIOUS:
        for r in RHOS:
            for m in MS:
                x = a_res.get((s, r, m))
                if x is None:
                    ent = _vp_notes(value_public({}), "no e10:a output at this point")
                else:
                    by = {}
                    for row in x["runs"]:
                        by.setdefault(row["tag"], {})[row["lender_seed"]] = row["ALG"]
                    ent = value_public(by)
                vp.setdefault(s, {}).setdefault(num_key(r), {})[str(m)] = ent
    # part b
    b_runs = []
    for r in RHOS_B:
        for m in MS_B:
            x = _ok_output(out, b_id(r, m), b_file(out, r, m), ignored)
            for row in (x or {}).get("runs", []):
                jid = b_milp_id(row["sched"], r, m, row["milp_key"])
                milp = _ok_output(out, jid, b_milp_file(out, row["sched"], r, m, row["milp_key"]), ignored)
                if milp is None:
                    rec = mc.read_record(out, jid)
                    milp = {"status": (rec or {}).get("status", "missing") if (rec or {}).get("status") != "ok"
                            else "missing"}
                elif milp.get("instance_hash") != row["instance_hash"] or \
                        milp.get("schedule_hash") != row["schedule_hash"]:
                    # a record of another instance or omega (left by an earlier run of the MILP job) is not used
                    milp = {"status": "stale", "stale_note": f"{jid}: instance or schedule hash differs from the run's"}
                row = {**row, "rho": r, "m": m, "milp_job": jid,
                       "lb": mc.lb_record(row["ALG"], None, milp)}
                b_runs.append(row)
    bsum: dict = {}
    for s in SCHEDS_B:
        for r in RHOS_B:
            for m in MS_B:
                for tag in TAGS_B:
                    rows = [x for x in b_runs if x["sched"] == s and x["rho"] == r and x["m"] == m and x["tag"] == tag]
                    bsum.setdefault(s, {}).setdefault(num_key(r), {}).setdefault(str(m), {})[tag] = \
                        b_entry(rows, "no e10:b output at this point")
    repro = _ok_output(out, job_id(EXP, "repro"), out / "repro.json", ignored)
    checks = build_checks(a_res, reruns, a, bounds, bsum, b_runs, repro)
    meta = {"exp": EXP, "git_revision": mc.git_revision(), "written": _now(), "reduced": d["reduced"],
            "grid": {"a": {"schedules": list(SCHEDS_A), "rho": list(RHOS), "rho_main": RHO_MAIN, "m": list(MS),
                           "m_run": list(d["ms"]), "n_seeds": d["n_seeds"], "n_seeds_design": N_SEEDS,
                           "tags": {s: list(t) for s, t in SCHED_TAGS.items()}, "rerun_seeds": [30, 129]},
                     "b": {"schedules": list(SCHEDS_B), "rho": list(RHOS_B), "m": list(MS_B), "m_run": list(d["ms_b"]),
                           "seeds": list(d["seeds_b"]), "seeds_design": list(SEEDS_B), "series": list(E2_SERIES),
                           "T": T_B, "slot_min": SLOT_B, "trace_config": f"configs/{TRACE_CONFIG}"}},
            "family": {"tau": TAU, "H": H_SLOTS, "D": D, "a": A, "c_T": C_T, "T_iid": T_IID, "phi_slots": PHI_SLOTS},
            "tags": {t: {"policy_id": v[0], "params": v[1], "information": v[2], "style_key": STYLE_KEYS[t]}
                     for t, v in {**TAGS, **TAGS_B}.items()},
            "points_found": {"a": len(a_res), "reruns": len(reruns), "b_runs": len(b_runs)},
            "ignored_outputs": list({x["job"]: x for x in ignored}.values())}
    if d["reduced"]:
        meta["reduced_note"] = (f"reduced job list ({REDUCED_ENV}=1): E10(a) at m in {list(d['ms'])} with "
                                f"{d['n_seeds']} seeds, E10(b) at m in {list(d['ms_b'])}, seeds "
                                f"{list(d['seeds_b'])}; not a result")
    summ = {"meta": meta, "a": a, "bounds": bounds, "value_public": vp, "b": bsum, "checks": checks}
    mc.dump_json(summ, out / "summary.json")
    mc.write_text(tables(summ), out / "tables.md")
    return summ


def build_checks(a_res: dict, reruns: dict, a: dict, bounds: dict, bsum: dict, b_runs: list, repro) -> dict:
    ch = {}
    rows = [(k, r) for k, x in a_res.items() for r in x["runs"]]
    if repro is None:
        ch["E10-1"] = {"status": "missing", "why": "repro.json missing (job e10:repro)"}
    else:
        ch["E10-1"] = {"status": "pass" if repro["pass"] else "fail", "claim": "R2 reproduction of c4_lower.json a "
                       "(rr, stay, pd_r1, pd_r1_min, pd_rth, pd_rth_min, LB_T) to 1e-9", "n_points": repro["n"],
                       "max_abs_diff": repro["max_abs_diff"],
                       "failures": [{"m": r["m"], "rho": r["rho"], "diff": r["diff"]} for r in repro["rows"]
                                    if not r["pass"]]}
    ad = [(k, r) for k, r in rows if k[0] == "adaptive"]
    bad2 = [{"point": list(k), "tag": r["tag"], "seed": r["policy_seed"], "ratio": r["ratio"]} for k, r in ad
            if not r.get("E10_2_ok")]
    ch["E10-2"] = {"status": ("pass" if not bad2 else "fail") if ad else "missing",
                   "claim": "C3-T4 (PROVEN): every adaptive run has ALG/OPT >= LB_T - 1e-9", "n_runs": len(ad),
                   "failures": bad2[:20],
                   "min_ratio_over_LB_T": min((r["ratio"] / point(*k)["LB_T"] for k, r in ad if r["ratio"]),
                                              default=None)}
    rr = [(k, r) for k, r in rows if r["tag"] == "RR"]
    rr += [(k, r) for k, x in reruns.items() for r in x["runs"] if r["tag"] == "RR"]
    bad3 = [{"point": list(k), "seed": r["lender_seed"], "ALG": r["ALG"], "bound": r["O1B_bound"]} for k, r in rr
            if not r.get("E10_3_ok")]
    ch["E10-3"] = {"status": ("pass" if not bad3 else "fail") if rr else "missing",
                   "claim": "O1-B (PROVEN): RR-renew ALG <= min{rho (1 + D/T) OPT, 2 m OPT + a D} (1 + 1e-9)",
                   "n_runs": len(rr), "failures": bad3[:20],
                   "max_alg_over_bound": max((r["ALG"] / r["O1B_bound"] for _, r in rr if r["O1B_bound"]),
                                             default=None)}
    ss = [(k, r) for k, r in rows if k[0] == "safe_site"]
    ss += [(k, r) for k, x in reruns.items() if k[0] == "safe_site" for r in x["runs"]]     # their schedules too
    ch["E10-4"] = {"status": ("pass" if all(r.get("E10_4_ok") for _, r in ss) else "fail") if ss else "missing",
                   "claim": "under safe_site OPT = Phi beta + a T on every schedule (1e-9)", "n_runs": len(ss),
                   "max_rel_diff": max((r["E10_4_diff"] for _, r in ss), default=None)}
    for cid, check, claim in (("E10-5", "E10-5", "O1-A (PROVEN, m >= 3): upper end of the 95% interval of "
                               "E[ALG]/OPT under safe_site at k* >= LB_A(k*) - 1e-9 (private tags)"),
                              ("E10-6", "E10-6", "O1-D (PROVEN): lower end of the 95% interval of marking's ratio "
                               "<= 2 h_m + 1")):
        fl = [(k, t, f) for k, x in a_res.items() for t, f in (x.get("flagged") or {}).items() if f["check"] == check]
        still, pend = [], []
        for k, t, f in fl:
            rr_ = reruns.get(k)
            if rr_ is None:
                pend.append({"point": list(k), "tag": t, **f})
            elif t in (rr_.get("still_flagged") or {}):
                still.append({"point": list(k), "tag": t, **rr_["still_flagged"][t]})
        if cid == "E10-5":
            n_pts = sum(1 for k in a_res if k[0] == "safe_site" and k[2] >= 3)
        else:
            n_pts = sum(1 for k in a_res if k[0] in OBLIVIOUS)
        ch[cid] = {"status": ("fail" if still else ("pending" if pend else "pass")) if a_res else "missing",
                   "claim": claim, "n_points": n_pts, "flagged": [{"point": list(k), "tag": t, **f} for k, t, f in fl],
                   "still_flagged_after_rerun": still, "rerun_pending": pend}
    e7 = []
    for rk, by_m in a.get("iid_step", {}).items():
        for mk, by_t in by_m.items():
            e = by_t.get("MARK")
            if e and e.get("ratio") is not None:
                e7.append({"sched": "iid_step", "rho": rk, "m": mk, "p_star": e.get("p_star"), "T": e.get("T"),
                           "ratio": e["ratio"], "ci95": e["ci95"], "LB_C_max": bounds[rk][mk]["LB_C_max"],
                           "ratio_minus_LB_C": e["ratio"] - bounds[rk][mk]["LB_C_max"]})
    ch["E10-7"] = {"status": "informative", "claim": "O1-C (PROVEN with tau >= 1; a T -> infinity limit that bounds "
                   "no finite run): marking's ratio under iid_step at p* against max_p LB_C", "points": e7}
    e8 = []
    for rk, by_m in a.get("adaptive", {}).items():
        for mk, by_t in by_m.items():
            e = by_t.get("RR")
            if e and e.get("ratio") is not None:
                lim = bounds[rk][mk]["limit"]
                e8.append({"rho": rk, "m": mk, "ratio": e["ratio"], "limit": lim, "ratio_over_limit": e["ratio"] / lim})
    ch["E10-8"] = {"status": "informative", "claim": "C-O1a (VERIFIED NUMERICALLY / CONJECTURE): RR-renew's "
                   "adaptive ratio against rho m / (m + rho - 1)", "points": e8}
    if repro is None or "o1_lb" not in repro:
        ch["E10-9"] = {"status": "missing", "why": "repro.json (o1_lb) missing (job e10:repro)"}
    else:
        rec = {(float(x["rho"]), str(x["m"])): x for x in repro["o1_lb"]["rows"]}
        mism = []
        for rk, by_m in bounds.items():
            for mk, e in by_m.items():
                x = rec.get((float(rk), mk))
                if x is None:
                    continue
                if e["source"]["k_star"] == "o1_lb.json A" and int(e["k_star"]) != int(x["k"]):
                    mism.append({"rho": rk, "m": mk, "what": "k_star"})
                if e.get("LB_A") is not None and abs(e["LB_A"] - x["LB_A"]) > 1e-12:
                    mism.append({"rho": rk, "m": mk, "what": "LB_A"})
                if abs(e["LB_C_max"] - x["LB_C"]) > 1e-12 or abs(e["p_star"] - float(x["p"])) > 1e-12:
                    mism.append({"rho": rk, "m": mk, "what": "LB_C_max or p_star"})
        ok = repro["o1_lb"]["pass"] and not mism
        ch["E10-9"] = {"status": "pass" if ok else "fail", "claim": "o1_lb.lb_A, lb_C through import_ref reproduce "
                       "o1_lb.json A at every listed (rho, m); bounds equal them there",
                       "n_listed": repro["o1_lb"]["n"], "recompute_pass": repro["o1_lb"]["pass"],
                       "bounds_mismatch": mism}
    e10 = []
    for s, by_r in bsum.items():
        for rk, by_m in by_r.items():
            for tag in TAGS_B:
                ser = [(int(mk), by_m[mk][tag].get("ratio")) for mk in by_m]
                e10.append({"sched": s, "rho": rk, "tag": tag,
                            "m": [x for x, _ in ser], "ratio": [y for _, y in ser],
                            "min_rho_m": [min(float(rk), x) for x, _ in ser],
                            "min_rho_1_log2m": [min(float(rk), 1.0 + math.log2(x)) for x, _ in ser]})
    ch["E10-10"] = {"status": "informative", "claim": "C-O1b (CONJECTURE): E10(b) ratios against min(rho, m) in m",
                    "series": e10, "n_runs": len(b_runs),
                    "n_empty_instances": sum(bool(r["empty_instance"]) for r in b_runs),
                    "stale_milp_records": sorted({r["milp_job"] for r in b_runs
                                                  if r["lb"].get("milp_status") == "stale"})}
    return ch


def tables(s: dict) -> str:
    L = ["# E10: the value of public reclaim information (design/sim_spec_ms3.md §5)", ""]
    if s["meta"].get("reduced"):
        L += [f"*{s['meta']['reduced_note']}*", ""]
    for sched, by_r in s["a"].items():
        L.append(f"## E10(a), `{sched}`: E[ALG] / E[OPT] [95% CI]")
        L.append("")
        rows = []
        for rk, by_m in by_r.items():
            for mk, by_t in by_m.items():
                for tag, e in by_t.items():
                    ci = e.get("ci95") or [None, None]
                    rows.append([rk, mk, tag, e.get("runs"), e.get("T"), e.get("ratio"), ci[0], ci[1], e.get("min"),
                                 e.get("max")])
        L.append(mc.md_table(["rho", "m", "tag", "runs", "T", "ratio", "ci lo", "ci hi", "min", "max"], rows))
    L.append("## Bounds")
    L.append("")
    rows = [[rk, mk, e["k_star"], e["p_star"], e["Phi"], e.get("LB_A"), e["LB_C_max"], e["LB_T"], e["limit"],
             e.get("O1B_adaptive"), e["O1B_safe_site"], e["two_h_m_plus_1"]] for rk, by_m in s["bounds"].items()
            for mk, e in by_m.items()]
    L.append(mc.md_table(["rho", "m", "k*", "p*", "Phi", "LB_A", "LB_C max", "LB_T", "limit", "O1-B adaptive",
                          "O1-B safe_site", "2 h_m + 1"], rows))
    L.append("## Value of public information (best private / best public mean cost, M52)")
    L.append("")
    rows = [[sk, rk, mk, e["best_private"], e["best_public"], e["ratio"], e["ci95"][0], e["ci95"][1], e["n_pairs"]]
            for sk, by_r in s["value_public"].items() for rk, by_m in by_r.items() for mk, e in by_m.items()]
    L.append(mc.md_table(["lender", "rho", "m", "best private", "best public", "ratio", "ci lo", "ci hi", "pairs"],
                         rows))
    L.append("## E10(b): E[ALG] / E[LB] (Q39) and E[ALG] / E[incumbent]")
    L.append("")
    rows = [[sk, rk, mk, tag, e["runs"], e.get("ratio"), (e.get("ci95") or [None, None])[0],
             (e.get("ci95") or [None, None])[1], e.get("inc"), e.get("share_exact"), e.get("empty_instances")]
            for sk, by_r in s["b"].items() for rk, by_m in by_r.items() for mk, by_t in by_m.items()
            for tag, e in by_t.items()]
    L.append(mc.md_table(["lender", "rho", "m", "tag", "runs", "ratio", "ci lo", "ci hi", "inc", "exact", "empty"],
                         rows))
    L.append("## Checks (§5.5)")
    L.append("")
    L.append(mc.md_table(["check", "status"], [[k, v["status"]] for k, v in s["checks"].items()]))
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                     description=__doc__))
