"""E7: end-to-end savings (design/sim_spec_ms4.md §3; deliverable D31, unit U20; open choices M1, M2, M20-M26,
M34, M36, M38, M39). Fig. 4(a)(b), Table III and the supplementary panels sf_e7_mix, sf_e7_mu and sf_e7_allow.

Instance (§3.4, M35): configs/bench_e7f.json through ms4_common.e7_spec (one week, 1-min routing on 5-min slow slots,
the full a11 menu, all 24 lenders, regional borrowers, the trace lender with I1, 'sell', violations absorbed,
engine.check_invariants true), mu / beta~ set explicitly; alignments c in {1, 2, 3, 4} are config seeds with lender
seed = config seed; policy seeds 0, 1, 2 (§3.6). The gap reruns (§3.7(e)) run on ms4_common.gap_instance(c): one day
of bench_e7r on the slow grid with s5_tau5_H5 in place of s5_tau5_H2 (Q44's block Q4), carrying the E7 week's
first-day demand of the same alignment (M22).

Policies (§3.5; tag: registry id, parameters, style key):
  Sublet  A8 ms4_common.sublet_params(inst, 'BL5')   sublet     (gamma 1, kappa None, B0 = B0_SHARE x BL0a, M36)
  A7G     A8 ms4_common.sublet_params(inst, 'A7')    a7_guard
  A7      A7 {}    a7          A6   A6 {}   a6          BL5  BL5 {}  bl5
  BL1     BL1 {}   bl1         BL2  BL2 {} (siloed runner, ms4_common.siloed_run)   bl2
  BL4     BL4 {}   bl4
  BL0a    analytic, e6.bl0a_all(inst); an engine run only in the gap jobs e7:gap_lp (M23)   bl0a
  BL0b    analytic, drivers/provision.bl0b_usd in both accountings                          bl0b
Every A8 run takes its parameters from ms4_common.sublet_params on the run's own instance (the allowance sweep: its
shares, and ms4_common.theory_params for Algorithm 1's defaults), never a typed B0, and records ms4_common.a8_record
(B0_rule, B0_usd, bl0a_usd, gamma, kappa, info_class_reported, the certificate of q44_study.certificate with its case
by e1.cert_case, t_a, aborted). Every cost entry carries both accountings (ms4_common.accountings, Q32, M2).

Grids (§3.7) and jobs (§3.10; ids by ms3_common.job_id, lender modes as in q44_study.MODES):
  part main    e7:main:pol=P:mu=U:c=C         pool   (a) and (b): 8 tags x mu in {1, 0.2, 0.5, 2} x 4 alignments,
                                                     3 policy seeds per job (128 jobs)
               e7:links:n=N:pol=P:c=C         pool   (c): Sublet, BL5, BL1 x n in {0, 2, 3} cross-region routing
                                                     links (ms4_common.routing_overrides, M1 (b)) x 4 (36 jobs); n = 5
                                                     is the main grid's mu = 1
  part stress  e7:stress:mode=M:pol=P         pool   (d): 8 tags x the five stress modes of W0 at alignment 1 (40 jobs)
  part allow   e7:allow:b0=X:mode=M           pool   (f): Sublet x B0 in {auto (kappa 10), 0.005, 0.01, 0.02, 0.05, 0.1,
                                                     0.2 of BL0a (kappa None)} x {L-tr and the stress modes} at
                                                     alignment 1 (42 jobs)
  part gap     e7:gap_run:pol=P:c=C           pool   (e): 8 tags x 4 alignments on the gap instance (32 jobs)
               e7:gap_lp:c=C                  alone  BL0a's engine run on the gap instance and the merged LP of §3.8,
                                                     drivers.bench.bench_for(res, inst, 'lp', grid='slow', merged=True,
                                                     allow_large=True, time_limit_s=1500, return_plan=False) (4 jobs)
E7_PART (environment): 'main', 'stress', 'gap', 'allow' or unset (all) selects the jobs that --list prints and the
parts --summary builds. run_e7.sh runs each part with E7_PART=<part> and --out out/e7/<part>, so each part has its own
jobs/, logs/, runs/, manifest.json, summary.json, tables.md and run_e7.log (ms3_common.COPY_PARTS['e7'], C20); a part's
files are written to <out> if its name is the part's, else to <out>/<part>. Pass 1 runs the jobs of the parts gap,
stress, main, allow; pass 2 the summaries of gap, stress, allow and main: allow's summary reads main's and stress's
run files (check E7-7) and stress's summary (BL5's W0), and main's summary, written last, reads the other three and
writes code/sim/out/e7/table3.json and the combined checks block (below).

Command line (ms3_common.main, §2.4), run from code/sim:
  python -m sublet.experiments.e7 --list | --job ID | --summary | --estimate | --manifest  [--out DIR]
--estimate uses the time constants of §3.7 and §11.1 (seconds per run: one week of Sublet 140.2, A7 + guard 190, A7
61.6, A6 49.4, BL4 28.6, BL2 25.2, BL1 11.7, BL5 10.9; one gap-rerun day of Sublet 18.7, A7 + guard 31, A7 16, A6
12.8, the others 20, BL0a 0.1; a merged LP 207.1 s), scaled by the horizon, plus EST_JOB_S per job.

Reduced runs (smoke tests): MS3_E7_REDUCED=1 (run_e7.sh --reduced sets it) keeps every job kind and the whole grid of
tags, mu, routing graphs, stress modes and allowances, with alignment 1 only, policy seed 0 only and a 2-hour horizon
(REDUCED_HORIZON_MIN, from the build: e7_spec(horizon_min) for the week runs, gap_instance(c, horizon_min) for the gap
reruns and their tiny merged LP). Its summaries carry meta.reduced true; never a result.

Outputs under code/sim/out/e7/ (§3.10, §2.6): <part>/runs/<job file>.json (not versioned; one file per job with its
runs: the instance's references, sizes and hash, and per policy seed the run entry: ALG (the ledger total),
accountings, components, the metrics of §3.9, the A8 record, BL2's sub-runs), gap/lb/lp_c<C>.json (versioned: the
fields of e1._solve_record with grid 'slow', the time limit, the instance and schedule hashes, BL0a's analytic and
engine cost), <part>/summary.json, <part>/tables.md, <part>/manifest.json, <part>/jobs/, <part>/logs/,
<part>/run_e7.log, table3.json. Numeric keys as ms3_common.num_key ('1', '0.2', '0.005'); a missing value is null
with a '*_note' key and an entry without runs keeps every field of its non-null form (§2.6).

main/summary.json
  meta                   exp, part, spec, git_revision, written, reduced (reduced_note), grids {mu, links,
                         alignments, policy_seeds and their design values, horizon_min}, tags {tag: policy_id,
                         params, style_key, a8, info_class_reported}, B0_rule, per alignment bl0a_usd,
                         own_capacity_usd, bl0a_total_usd, bl0b_overflow_usd, bl0b_total_usd and
                         committed_price_usd_per_gpu_h (ms4_common.references of the mu = 1 instance), instances
                         (sizes and instance hash per 'mu=U:c=C' and 'links=N:c=C'), links (the cross-region links of
                         each n; '5': S7, the main grid, runs.1), jobs_ok, jobs_missing, ignored_outputs
  runs.<mu>.<tag>        n_runs, alignments, policy_seeds; overflow_usd, total_usd, overflow_over_bl0a, total_over_bl0a,
                         own_share_of_total, overflow_over_bl0b, total_over_bl0b, saving_pct (100 (1 - overflow /
                         BL0a)), saving_pct_total (the same in total accounting), fallback_share,
                         stranding_events_per_day, loads_per_day, replica_utilization, n_leases: each
                         metrics.aggregate over the runs (n, median, p95, max, median_ci95) with mean;
                         components_over_bl0a.<component> (the mean of each ledger
                         component over BL0a: lease_prepaid, lease_rent, lease, loading, routing, fallback, stranding,
                         total); fallback_share_after_reclaims (the aggregate over the runs where it is defined, mean,
                         n_null); gpu_hour_share.<class> (GPU-hours summed over the runs over their sum); abort_share,
                         t_a (the abort slots, sorted), t_a_first, t_a_median and certificates {n, held, by_case {case:
                         {runs, held}}, failures} for the A8 tags (null with a note for the others);
                         info_class_reported; n_runs_with_invariant_failures, n_runs_with_gpu_only_lease_slots
  links.<n>.<tag>        the same fields at mu = 1 for n in {0, 2, 3} and the tags Sublet, BL5, BL1 (n = 5: runs.1)
  certificates           ms4_common.count_certificates over every A8 run of the part, w_c_runs
  checks_local           the checks of the part (E7-1, E7-2, E7-4, E7-5 (BL0b recorded), E7-6, E7-9, E7-11, E7-12)
  checks                 every check id of §3.11 (E7-1 ... E7-12) once: {status, claim, parts {<part>: the part's
                         entry}}, combined over the part summaries (a fail of a part fails it; a part without its
                         entry leaves it missing); the claims report reads E7's rows here. A part summary is used
                         only if its e7:summary record is 'ok' or absent (part_summary; else it counts as missing and
                         is listed in meta.ignored_outputs); allow's summary reads stress's the same way
stress/summary.json
  meta                   as main's for alignment 1, modes {mode: lender_model, lender_params_resolved}
  modes.<mode>.<tag>     n_runs, seeds, r0 {seed: overflow cost / BL0a}, r0_mean, total_over_bl0a {seed} and its mean,
                         overflow_usd {seed}, total_usd {seed}, accountings {seed: both accountings}, intensity (mean
                         announcements per revocable site-day; intensity_by_seed), fallback_share_after_reclaims,
                         gpu_hour_share.<class>, and for the A8 tags aborted {seed}, t_a {seed}, abort_share,
                         t_a_median, certificate_case {seed}, certificates (null with a note for the others)
  W0.<tag>               ms4_common.w0 over the five stress modes (one cell, alignment 1): value, mode, seed_range,
                         per_mode, modes_missing (value null with value_partial while a mode is missing), criterion_S
                         (value <= 1.05, note §5.6)
  certificates, checks   checks: E7-1, E7-2, E7-4, E7-6, E7-8, E7-11
gap/summary.json
  meta                   per alignment the gap instance's references, sizes, hash, demand sha256 and
                         bl0a_own_demand; the LP settings
  lp.<c>                 the record of gap/lb/lp_c<C>.json (LP_FIELDS: job, status, status_msg, objective, dual_bound,
                         gap, grid, method, benchmark, size, build_s, solve_s, peak_rss_mb, time_limit_s, instance_hash,
                         schedule_hash, merged_sites, sites, label, horizon_min, wall_s; file), every field null with
                         its note without an 'ok' job
  runs.<tag>             n_runs, n_ratio, ratio_LB (aggregate over the 12 runs, over 4 for BL0a, of ms3_common.lb_record
                         against the alignment's LP paired by instance and schedule hash), alg_usd (= overflow_usd) and
                         the seven fields of both accountings (ACC_FIELDS) as aggregates, p1_flags (P1 runs with
                         ratio_LB < 1 - 1e-6; BL2 exempt), ratio_validity (the reasons of every run: all null),
                         abort_share and t_a for the A8 tags, certificates
  bl0a_by_alignment.<c>  analytic_usd, engine_usd, rel_diff, bl0a_own_demand_usd, demand_sha256; for an alignment of
                         the grid without an 'ok' e7:gap_lp output every field null with its note
  certificates, checks   checks: E7-1, E7-2, E7-3, E7-4, E7-5 (missing while an alignment of the grid has no BL0a
                         engine run), E7-6, E7-10 (ratio_LB_median per tag and ratio_LB_median_range, measured; no
                         range is typed), E7-11
allow/summary.json
  meta                   bl0a_usd (alignment 1), b0_auto_usd (A8's report field B0 at the theory point),
                         kappa10_cap_usd (10 sum_j C^min_j, guard.c_min of the instance's public view), c_min_sum_usd,
                         allowances, modes
  cells.<b0>.<mode>      b0 'auto' or the share; B0_rule, B0_usd, kappa (kappa_note when null: the constant
                         allowance), n_runs, cost_over_bl0a (overflow_over_bl0a: aggregate over the seeds with mean and
                         by_seed), total_over_bl0a, own_share_of_total, overflow_over_bl0b, total_over_bl0b (the same),
                         overflow_usd {seed}, total_usd {seed}, accountings {seed: both accountings}, t_a {seed}, case
                         {seed}, held {seed}, aborted {seed}, abort_share, certificates
  W0.<b0>                ms4_common.w0 of Sublet at that allowance over the five stress modes: value, mode, seed_range
  bl5                    L-tr (BL5's median cost over BL0a at alignment 1 and mu = 1, from part main's runs), W0
                         (BL5's W0 from part stress's summary), L-tr_aggregate, W0_detail, sources
  certificates, checks   checks: E7-1, E7-2, E7-4, E7-6, E7-7, E7-11
table3.json              rows.<tag> in Table III's order (Sublet, BL5, BL1, BL2, BL4, A7, A7G, A6, BL0b, BL0a): label
                         (style.POLICIES), style_key and the columns usd {overflow, total}, saving_pct, gap,
                         fallback_share_after_reclaims, W0, abort_share, each {median, interval, n, note} (§9);
                         caption {certificates over every A8 run of E7 (by case and held, summed over the part
                         summaries), B0_rule, info_class_reported, own_capacity_usd {by_alignment, median}, scope};
                         meta {git_revision, written, reduced, sources {<part>: file, exists, sha256, used (used_note),
                         git_revision, reduced}}

Status labels (copied from design/sim_spec_ms4.md §3.1, never upgraded): E7 is a system result with no claim; Theorem
W(a)(b) PROVEN for the engine as implemented under C1-C3 and audited (the additive envelope with B = B0 under M36);
W(c) CONJECTURE, checked per run by the certificate; Propositions M4 and M6 PROVEN (the gap column is an upper bound
on the ratio to OPT(sigma, omega) against a merged bound).
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import copy
import hashlib
import math
import sys
import time
import types
from pathlib import Path
from typing import Optional

import numpy as np

from .. import paths
from . import ms3_common as mc
from . import ms4_common as m4
from .ms3_common import Job, job_id, num_key, put

EXP = "e7"
SPEC = "design/sim_spec_ms4.md §3"
PARTS = mc.COPY_PARTS[EXP]                         # ("main", "stress", "gap", "allow"), C20
PASS_JOBS = ("gap", "stress", "main", "allow")     # run_e7.sh pass 1 (§3.10)
PASS_SUMMARIES = ("gap", "stress", "allow", "main")    # pass 2: main's summary last (table3.json)
# tag: registry id, fixed parameters (A8: the inner id, parameters from ms4_common), style key, q44_study tag (§3.5)
TAGS = {"Sublet": {"id": "A8", "inner": "BL5", "params": None, "style": "sublet", "q44": "BL5-G"},
        "A7G": {"id": "A8", "inner": "A7", "params": None, "style": "a7_guard", "q44": "PS-G"},
        "A7": {"id": "A7", "inner": None, "params": {}, "style": "a7", "q44": "PS"},
        "A6": {"id": "A6", "inner": None, "params": {}, "style": "a6", "q44": "A6"},
        "BL5": {"id": "BL5", "inner": None, "params": {}, "style": "bl5", "q44": "BL5"},
        "BL1": {"id": "BL1", "inner": None, "params": {}, "style": "bl1", "q44": "BL1"},
        "BL2": {"id": "BL2", "inner": None, "params": {}, "style": "bl2", "q44": "BL2"},
        "BL4": {"id": "BL4", "inner": None, "params": {}, "style": "bl4", "q44": None}}
A8_TAGS = ("Sublet", "A7G")
REF_STYLE = {"BL0a": "bl0a", "BL0b": "bl0b"}
TABLE3_ROWS = ("Sublet", "BL5", "BL1", "BL2", "BL4", "A7", "A7G", "A6", "BL0b", "BL0a")     # §9
MU_MAIN = 1.0
MUS = (1.0, 0.2, 0.5, 2.0)                         # the headline first, then the mu points of M26
LINKS = (0, 2, 3)                                  # M1 (b): n = 5 is the main grid
LINK_TAGS = ("Sublet", "BL5", "BL1")
ALIGNMENTS = (1, 2, 3, 4)
POLICY_SEEDS = (0, 1, 2)
STRESS_C = 1                                       # the stress block and the sweep at alignment 1 (decision 5)
ALLOW_B0 = ("auto", 0.005, 0.01, 0.02, 0.05, 0.1, 0.2)      # §3.7(f): the theory default and the shares of BL0a
GAP_LP_LIMIT_S = 1500.0                            # §3.8: HiGHS's time limit of the merged LP
GAP_GRID = "slow"
COMPONENT_KEYS = ("lease_prepaid", "lease_rent", "lease", "loading", "routing", "fallback", "stranding", "total")
ACC_FIELDS = ("overflow_usd", "total_usd", "overflow_over_bl0a", "total_over_bl0a", "own_share_of_total",
              "overflow_over_bl0b", "total_over_bl0b")
METRIC_FIELDS = ("fallback_share", "stranding_events_per_day", "loads_per_day", "replica_utilization")
REL_TOL = 1e-9                                     # E7-4, E7-5, E7-7
P1_TOL = 1e-6                                      # E7-3 (design §5.2.4)
CRITERION_S = 1.05                                 # Q44's criterion S: W0 <= 1.05 (note §5.6)
KAPPA_NONE_NOTE = "kappa None: the constant allowance B(t) = B0 (guard.Ratchet.allowance; M36)"
REDUCED_ENV = "MS3_E7_REDUCED"
REDUCED_HORIZON_MIN = 120                          # a 2-hour horizon (24 slow slots)
# time constants (§3.7, §11.1; seconds per run of one week or one gap-rerun day, measured or estimated there)
EST_WEEK_S = {"Sublet": 140.2, "A7G": 190.0, "A7": 61.6, "A6": 49.4, "BL4": 28.6, "BL2": 25.2, "BL1": 11.7,
              "BL5": 10.9}
EST_GAP_S = {"Sublet": 18.7, "A7G": 31.0, "A7": 16.0, "A6": 12.8, "BL4": 20.0, "BL2": 20.0, "BL1": 20.0,
             "BL5": 20.0, "BL0a": 0.1}
EST_LP_S = 207.1
EST_JOB_S = 5.0                                    # process start, imports and the build, per job
CHECK_IDS = tuple(f"E7-{i}" for i in range(1, 13))
INFORMATIVE = ("E7-8", "E7-9", "E7-10", "E7-11", "E7-12")
# the checks each part's summary computes over its own runs; main's summary combines them (module docstring)
PART_CHECKS = {"main": ("E7-1", "E7-2", "E7-4", "E7-5", "E7-6", "E7-9", "E7-11", "E7-12"),
               "stress": ("E7-1", "E7-2", "E7-4", "E7-6", "E7-8", "E7-11"),
               "gap": ("E7-1", "E7-2", "E7-3", "E7-4", "E7-5", "E7-6", "E7-10", "E7-11"),
               "allow": ("E7-1", "E7-2", "E7-4", "E7-6", "E7-7", "E7-11")}
# summary checks.<id>.claim: the content of §3.11 with the status labels of §3.1 (copied, never upgraded)
CHECK_CLAIMS = {
    "E7-1": "every A8 run of E7 (all six grids) has a certificate with available true; in every run of Theorem W's "
            "proven cases (W(a), W(b); PROVEN for the engine as implemented under C1-C3, audited) held is true; W(c) "
            "runs (CONJECTURE) are counted and listed with their t_a",
    "E7-2": "every run, BL2's sub-runs included: invariant_failures empty and gpu_only_lease_slots 0",
    "E7-3": "every gap rerun: ratio_validity('slow', ...) None; its alignment's LP record has status 0 (optimal) and "
            "the instance and schedule hashes of the run; all runs of one alignment have one schedule hash; every "
            "engine run in plan class P1 has ratio_LB >= 1 - 1e-6 (Proposition M4(b) with Proposition M6, PROVEN); "
            "BL2's summed runs are exempt from the P1 test",
    "E7-4": "accounting identity: total - overflow = own_capacity_usd(inst) for every run, and BL0a's total-"
            "accounting cost = BL0a + own capacity (1e-9 relative)",
    "E7-5": "BL0a: e6.bl0a_all(inst) equals BL0a's engine run on every gap-rerun instance (1e-9 relative); BL0b is "
            "recorded in both accountings per alignment",
    "E7-6": f"the allowance rule (M36): every A8 run outside the allowance sweep records B0_rule {m4.B0_RULE!r}, B0 = "
            f"{m4.B0_SHARE:g} x e6.bl0a_all of its own instance (1e-12 relative), resolved gamma 1 and kappa null; the "
            f"sweep's runs record their own rule ({m4.THEORY_RULE!r} with kappa 10, or the share of BL0a with kappa "
            "null)",
    "E7-7": f"the allowance sweep's runs at B0 = {100 * m4.B0_SHARE:g}% of BL0a reproduce the main grid's Sublet runs "
            "at alignment 1 under L-tr and the stress block's Sublet runs, seed by seed (totals equal to 1e-9 USD)",
    "E7-8": "W0 per policy (stress block) against Q44's criterion S (W0 <= 1.05, note §5.6) (informative)",
    "E7-9": "saving over BL0a against the cross-region links n (Fig. 4(b)), with one BL0a at every n (informative)",
    "E7-10": "Sublet's slow-grid ratio to the merged LP bound against BL5's (decision B1; the slow-grid item of the "
             "must-not-claim list) (informative)",
    "E7-11": "abort shares and first-abort slots of the A8 rows in every grid; under the sweep's theory default, the "
             "share of runs that abort at slot 1 or earlier (informative)",
    "E7-12": "policies whose median cost exceeds BL0a (A6, M38; reported as measured) (informative)"}


# ---------------------------------------------------------------- settings
def design() -> dict:
    """The job grid: the full grid of §3.7, or the reduced one with MS3_E7_REDUCED=1 (module docstring)."""
    red = os.environ.get(REDUCED_ENV, "0") == "1"
    return {"reduced": red, "alignments": (1,) if red else ALIGNMENTS, "policy_seeds": (0,) if red else POLICY_SEEDS,
            "horizon_min": REDUCED_HORIZON_MIN if red else m4.WEEK_MIN,
            "gap_horizon_min": REDUCED_HORIZON_MIN if red else m4.DAY_MIN}


def parts() -> list:
    v = os.environ.get("E7_PART", "")
    ps = [p for p in v.replace(",", " ").split() if p]
    bad = [p for p in ps if p not in PARTS]
    if bad:
        raise ValueError(f"E7_PART must name parts of {list(PARTS)}, got {v!r}")
    return ps or list(PARTS)


def part_dir(out, part: str) -> Path:
    o = Path(out)
    return o if o.name == part else o / part


def e7_root(out) -> Path:
    """out/e7 (the folder of the parts and of table3.json) from a part's folder or from out/e7 itself."""
    o = Path(out)
    return o.parent if o.name in PARTS else o


def stress_modes() -> tuple:
    """The five stress modes of W0 (ms4_common.stress_modes: q44_study.MODES with stress true)."""
    return m4.stress_modes()


def allow_modes() -> tuple:
    """The lender modes of the allowance sweep: the trace lender and the stress modes (§3.7(f))."""
    return ("L-tr",) + stress_modes()


def b0_key(b0) -> str:
    return "auto" if b0 == "auto" else num_key(b0)


def is_a8(tag: str) -> bool:
    return TAGS[tag]["id"] == "A8"


# ---------------------------------------------------------------- job ids and paths
def main_id(tag: str, mu, c: int) -> str:
    return job_id(EXP, "main", pol=tag, mu=float(mu), c=int(c))


def links_id(n: int, tag: str, c: int) -> str:
    return job_id(EXP, "links", n=int(n), pol=tag, c=int(c))


def stress_id(mode: str, tag: str) -> str:
    return job_id(EXP, "stress", mode=mode, pol=tag)


def allow_id(b0, mode: str) -> str:
    return job_id(EXP, "allow", b0=b0_key(b0), mode=mode)


def gap_run_id(tag: str, c: int) -> str:
    return job_id(EXP, "gap_run", pol=tag, c=int(c))


def gap_lp_id(c: int) -> str:
    return job_id(EXP, "gap_lp", c=int(c))


def run_path(out, part: str, jid: str) -> Path:
    return part_dir(out, part) / "runs" / mc.job_file_name(jid)


def lp_path(out, c: int) -> Path:
    return part_dir(out, "gap") / "lb" / f"lp_c{int(c)}.json"


# ---------------------------------------------------------------- jobs
def _est(tag: str, n_seeds: int, hz: int, table: dict, full: int) -> float:
    return EST_JOB_S + n_seeds * table[tag] * float(hz) / float(full)


def jobs(ps=None) -> list:
    """The E7 jobs of the parts `ps` (default: E7_PART) in run order (§3.10): main (mu = 1 first, then the mu points,
    then the routing graphs), stress, allow, gap (the LP jobs first; ms3_lib.sh runs the 'alone' kind after the pool
    jobs)."""
    ps = parts() if ps is None else list(ps)
    d = design()
    al, seeds, hz, ghz = d["alignments"], list(d["policy_seeds"]), d["horizon_min"], d["gap_horizon_min"]
    common = {"policy_seeds": seeds, "horizon_min": hz}
    out = []
    if "main" in ps:
        for mu in MUS:
            for c in al:
                for tag in TAGS:
                    out.append(Job(main_id(tag, mu, c), "pool",
                                   {"part": "main", "kind": "main", "tag": tag, "mu": float(mu), "c": int(c),
                                    "mode": "L-tr", **common}, _est(tag, len(seeds), hz, EST_WEEK_S, m4.WEEK_MIN)))
        for n in LINKS:
            for c in al:
                for tag in LINK_TAGS:
                    out.append(Job(links_id(n, tag, c), "pool",
                                   {"part": "main", "kind": "links", "tag": tag, "n": int(n), "mu": MU_MAIN,
                                    "c": int(c), "mode": "L-tr", **common},
                                   _est(tag, len(seeds), hz, EST_WEEK_S, m4.WEEK_MIN)))
    if "stress" in ps:
        for mode in stress_modes():
            for tag in TAGS:
                out.append(Job(stress_id(mode, tag), "pool",
                               {"part": "stress", "kind": "stress", "tag": tag, "mode": mode, "mu": MU_MAIN,
                                "c": STRESS_C, **common}, _est(tag, len(seeds), hz, EST_WEEK_S, m4.WEEK_MIN)))
    if "allow" in ps:
        for b0 in ALLOW_B0:
            for mode in allow_modes():
                out.append(Job(allow_id(b0, mode), "pool",
                               {"part": "allow", "kind": "allow", "tag": "Sublet", "b0": b0, "mode": mode,
                                "mu": MU_MAIN, "c": STRESS_C, **common},
                               _est("Sublet", len(seeds), hz, EST_WEEK_S, m4.WEEK_MIN)))
    if "gap" in ps:
        for c in al:
            out.append(Job(gap_lp_id(c), "alone", {"part": "gap", "kind": "gap_lp", "c": int(c),
                                                   "horizon_min": ghz, "time_limit_s": GAP_LP_LIMIT_S},
                           EST_JOB_S + EST_LP_S * float(ghz) / m4.DAY_MIN + EST_GAP_S["BL0a"]))
        for c in al:
            for tag in TAGS:
                out.append(Job(gap_run_id(tag, c), "pool",
                               {"part": "gap", "kind": "gap_run", "tag": tag, "c": int(c), "policy_seeds": seeds,
                                "horizon_min": ghz}, _est(tag, len(seeds), ghz, EST_GAP_S, m4.DAY_MIN)))
    return out


def jobs_all() -> list:
    """Every job of the four parts (the summaries look up the records of their own part)."""
    return jobs(list(PARTS))


# ---------------------------------------------------------------- run specs and parameters
def tag_params(tag: str, inst, b0=None) -> dict:
    """The policy parameters of `tag` on the run's own instance `inst`: for the A8 tags M36's allowance
    (ms4_common.sublet_params(inst, inner)), in the allowance sweep (b0 given) ms4_common.theory_params for 'auto' and
    sublet_params with the share b0 otherwise; the fixed parameters of §3.5 for the other tags. A driver never types
    B0 (§2.2)."""
    t = TAGS[tag]
    if t["id"] != "A8":
        if b0 is not None:
            raise ValueError(f"tag {tag}: the allowance sweep runs A8 tags only")
        return copy.deepcopy(t["params"])
    if b0 is None:
        return m4.sublet_params(inst, t["inner"])
    if b0 == "auto":
        return m4.theory_params(t["inner"])
    return m4.sublet_params(inst, t["inner"], share=float(b0))


def week_spec(policy_id: str, params=None, *, mu: float = MU_MAIN, mode: str = "L-tr", n: Optional[int] = None,
              horizon_min: int = m4.WEEK_MIN, c: int = 1, seeds=(0,), name: str = "e7") -> dict:
    """The validated run spec of one week run (§3.4; ms4_common.e7_spec): mu, the lender mode's lender model
    (ms4_common.mode_lender_model) and the routing graph of n cross-region links (ms4_common.routing_overrides; None:
    the main grid's S7)."""
    ov = {} if n is None else m4.routing_overrides(int(n))
    return m4.e7_spec(policy_id, params, mu=float(mu), horizon_min=int(horizon_min),
                      lender_model=m4.mode_lender_model(mode), overrides=ov, name=name,
                      seeds={"config": [int(c)], "lender": "config", "policy": [int(p) for p in seeds]})


def gap_spec(policy_id: str, params=None, *, horizon_min: int = m4.DAY_MIN, c: int = 1, seeds=(0,),
             name: str = "e7_gap") -> dict:
    """The validated run spec of one gap rerun (§3.7(e); ms4_common.e7r_h5_spec); its instance is
    ms4_common.gap_instance(c)."""
    return m4.e7r_h5_spec(policy_id, params, horizon_min=int(horizon_min), name=name,
                          seeds={"config": [int(c)], "lender": "config", "policy": [int(p) for p in seeds]})


# ---------------------------------------------------------------- run entries (§3.9)
def _jsonish(x):
    """metrics._jsonable (non-finite floats as strings) for the free-form parts of run files."""
    from ..metrics import _jsonable
    return _jsonable(x)


def instance_sizes(inst) -> dict:
    kinds: dict = {}
    for s in inst.sites:
        kinds[s.kind] = kinds.get(s.kind, 0) + 1
    g = inst.grid
    return {"n_sites": int(inst.m), "n_sites_by_kind": kinds, "n_contracts": int(inst.K),
            "contracts": [k.id for k in inst.contracts], "n_clients": int(inst.n), "n_llms": int(inst.J),
            "T_slow": int(g.T_slow), "T_fast": int(g.T_fast), "slow_min": int(g.slow_min), "fast_min": int(g.fast_min),
            "horizon_min": int(g.horizon_min), "start_mow": int(g.start_mow)}


def cross_region_arcs(inst) -> list:
    """The region pairs {client region, site region} with a routing arc between two different regions (a finite
    delta), sorted (measurement 9's cross_region_arcs)."""
    d = np.asarray(inst.clients.delta_usd_per_h, dtype=np.float64)
    arcs = {tuple(sorted((inst.clients.region[c], inst.sites[k].region))) for c, k in zip(*np.nonzero(np.isfinite(d)))
            if inst.clients.region[c] != inst.sites[k].region}
    return [list(a) for a in sorted(arcs)]


def _metric_fields(m: dict) -> dict:
    bv = m.get("buffer_violations") or {}
    return {"fallback_share": m.get("fallback_share"),
            "fallback_share_after_reclaims": m.get("fallback_share_after_reclaims"),
            "stranding_events_per_day": m.get("stranding_events_per_day"), "loads_per_day": m.get("loads_per_day"),
            "replica_utilization": m.get("replica_utilization"),
            "gpu_hours_by_class": {k: float(v) for k, v in (m.get("gpu_hours_by_class") or {}).items()},
            "gpu_only_lease_slots": int(m.get("gpu_only_lease_slots", 0)),
            "buffer_violations": {"count": bv.get("count"), "share": bv.get("share")}}


def _a8_fields(res, inst, params: dict, information: str) -> dict:
    """ms4_common.a8_record (allowance record, info_class_reported, the certificate without its per-slot list, its
    case, t_a, aborted) and the safe expert's accounted costs (safe_C_S, safe_C_R, safe_C_FB) and followed experts."""
    rec = m4.a8_record(res, inst, params, information)
    rep = res.metrics.get("policy") or {}
    safe = rep.get("safe") or {}
    fol = safe.get("followed") or []
    rec.update(safe_C_S=safe.get("C_S"), safe_C_R=safe.get("C_R"), safe_C_FB=safe.get("C_FB"),
               safe_followed=list(fol[:20]), safe_followed_n=len(fol), safe_switches=safe.get("switches"),
               inner_id=rep.get("inner_id"), test=rep.get("test"), wind_down=rep.get("wind_down"))
    return rec


def run_entry(res, inst, model, refs: dict, own: Optional[float], *, tag: str, spec: dict, pol, ps: int, c: int,
              wall_s: float, imeta: Optional[dict] = None) -> dict:
    """One engine run's entry of a run file (§3.9): ALG (the ledger total, overflow accounting), both accountings
    (ms4_common.accountings), the components, the metrics, invariants, plan class P1, the realized intensity, lease
    statistics, the schedule hash, the times and, for A8, the A8 record."""
    from ..algos import registry
    from ..metrics import run_metrics
    from . import q44_study as q44
    pid, params = spec["policy"]["id"], dict(spec["policy"]["params"] or {})
    rp = {**params, **(pol.params() or {})} if callable(getattr(pol, "params", None)) else dict(params)
    m = run_metrics(res, inst)
    alg = float(res.components["total"])
    info = registry.info_class(pid, rp, model.information)
    style = TAGS[tag]["style"] if tag in TAGS else REF_STYLE.get(tag)
    e = {"tag": tag, "policy_id": pid, "params": params, "resolved_params": rp, "style_key": style,
         "policy_seed": int(ps), "config_seed": int(c), "lender_seed": int(c),
         "info_class": info, "info_class_reported": info, "driver_inputs": imeta or {},
         "bl0a_usd": refs["bl0a_usd"], "own_capacity_usd": own, "ALG": alg,
         "accountings": m4.accountings(alg, inst, refs),
         "components": {k: float(v) for k, v in res.components.items()}, "grouped": q44.grouped(res.components),
         **_metric_fields(m),
         "n_invariant_failures": len(res.invariant_failures),
         "invariant_failures_first": list(res.invariant_failures[:5]),
         "plan_class_p1": bool(q44.plan_class_p1(res, inst)), "intensity": q44.intensity(res, inst),
         "leases": q44.lease_stats(res, inst), "n_leases": len(res.leases),
         "schedule_hash": q44.schedule_hash(res.schedule), "wall_s": float(wall_s),
         "engine_wall_s": res.runtime.get("wall_s"), "peak_rss_mb": res.runtime.get("peak_rss_mb"), "a8": None}
    if pid == "A8":
        e["a8"] = _a8_fields(res, inst, params, model.information)
        e["info_class_reported"] = e["a8"]["info_class_reported"]
    return e


def siloed_entry(d: dict, inst, model, refs: dict, own: Optional[float], *, tag: str, spec: dict, ps: int, c: int,
                 wall_s: float) -> dict:
    """The entry of a siloed run (BL2; ms4_common.siloed_run): the summed costs and the engine sums of
    metrics.run_metrics summed over the sub-runs (shares as sums over sums), the sub-runs' invariants and GPU-only
    lease slots (E7-2), plan class P1 of every sub-run, the realized intensity of the schedule with every sub-run's
    leases, and one row per sub-run."""
    from ..algos import registry
    from . import q44_study as q44
    subs, sub_insts = d["results"], d["instances"]
    days = inst.grid.horizon_min / 1440.0
    tot = {k: np.sum([np.asarray(r.metrics[k], dtype=float) for r in subs], axis=0)
           for k in ("demand_after_reclaims_load_min_by_llm", "fallback_after_reclaims_load_min_by_llm",
                     "demand_load_min_by_llm", "fallback_load_min_by_llm")}

    def share(a, b):
        return float(np.sum(a) / np.sum(b)) if np.sum(b) > 0 else None
    served = sum(float(r.metrics["served_load_min"]) for r in subs)
    cap = sum(float(r.metrics["capacity_load_min"]) for r in subs)
    gh: dict = {}
    for r in subs:
        for k, v in (r.metrics.get("gpu_hours_by_class") or {}).items():
            gh[k] = gh.get(k, 0.0) + float(v)
    ls: dict = {"leases": 0, "by_end_cause": {}, "rebuys": 0, "replicas": 0}
    for r, s in zip(subs, sub_insts):
        x = q44.lease_stats(r, s)
        ls["leases"] += x["leases"]
        ls["rebuys"] += x["rebuys"]
        ls["replicas"] += x["replicas"]
        for k, v in x["by_end_cause"].items():
            ls["by_end_cause"][k] = ls["by_end_cause"].get(k, 0) + v
    merged = types.SimpleNamespace(schedule=subs[0].schedule, leases=[L for r in subs for L in r.leases]) \
        if subs else None
    sh = sorted({q44.schedule_hash(r.schedule) for r in subs})
    pid, params = spec["policy"]["id"], dict(spec["policy"]["params"] or {})
    alg = float(d["components"].get("total", 0.0))
    info = registry.info_class(pid, params, model.information)
    rows = [{k: x[k] for k in ("borrower", "clients", "total", "n_invariant_failures", "gpu_only_lease_slots",
                               "plan_class_p1")} for x in d["sub_runs"]]
    for row, r in zip(rows, subs):
        row["schedule_hash"] = q44.schedule_hash(r.schedule)
        row["wall_s"] = r.runtime.get("wall_s")
    return {"tag": tag, "policy_id": pid, "params": params, "resolved_params": params, "style_key": TAGS[tag]["style"],
            "runner": "siloed", "policy_seed": int(ps), "config_seed": int(c), "lender_seed": int(c),
            "info_class": info, "info_class_reported": info, "driver_inputs": {},
            "bl0a_usd": refs["bl0a_usd"], "own_capacity_usd": own, "ALG": alg,
            "accountings": m4.accountings(alg, inst, refs),
            "components": {k: float(v) for k, v in d["components"].items()}, "grouped": q44.grouped(d["components"]),
            "fallback_share": share(tot["fallback_load_min_by_llm"], tot["demand_load_min_by_llm"]),
            "fallback_share_after_reclaims": share(tot["fallback_after_reclaims_load_min_by_llm"],
                                                   tot["demand_after_reclaims_load_min_by_llm"]),
            "stranding_events_per_day": sum(float(r.metrics["stranding_events"]) for r in subs) / days,
            "loads_per_day": sum(int(r.metrics["loads"]) for r in subs) / days,
            "replica_utilization": served / cap if cap > 0 else None, "gpu_hours_by_class": gh,
            "gpu_only_lease_slots": int(sum(x["gpu_only_lease_slots"] for x in d["sub_runs"])),
            "buffer_violations": {"count": int(sum(int(r.metrics.get("violation_lender_slots", 0)) for r in subs)),
                                  "share": None},
            "n_invariant_failures": len(d["invariant_failures"]),
            "invariant_failures_first": list(d["invariant_failures"][:5]),
            "plan_class_p1": bool(all(x["plan_class_p1"] for x in d["sub_runs"])),
            "intensity": q44.intensity(merged, inst) if merged is not None else None, "leases": ls,
            "n_leases": ls["leases"], "schedule_hash": sh[0] if len(sh) == 1 else None, "schedule_hashes": sh,
            "n_sub_runs": len(subs), "sub_runs": rows, "wall_s": float(wall_s),
            "engine_wall_s": float(sum(float(r.runtime.get("wall_s") or 0.0) for r in subs)),
            "peak_rss_mb": max((float(r.runtime.get("peak_rss_mb") or 0.0) for r in subs), default=None), "a8": None}


def one_run(spec: dict, tag: str, inst, model, ecfg, refs: dict, own, c: int, ps: int) -> dict:
    """One run of `tag` (the spec's policy) on `inst`: the simulate runner (the policy built by drivers.run.make_policy
    from the instance) or BL2's siloed runner (ms4_common.siloed_run, each sub-policy from its own sub-instance)."""
    from ..algos import registry
    from ..drivers.run import driver_inputs, make_policy
    from ..engine import simulate
    pid, params = spec["policy"]["id"], dict(spec["policy"]["params"] or {})
    t0 = time.perf_counter()
    if registry.entry(pid).runner == "siloed":
        d = m4.siloed_run(inst, spec, model, ecfg, c, ps)
        return siloed_entry(d, inst, model, refs, own, tag=tag, spec=spec, ps=ps, c=c, wall_s=time.perf_counter() - t0)
    _, imeta = driver_inputs(pid, params, inst)
    pol = make_policy(spec, inst)
    res = simulate(inst, pol, model, ecfg, lender_seed=int(c), policy_seed=int(ps))
    return run_entry(res, inst, model, refs, own, tag=tag, spec=spec, pol=pol, ps=ps, c=c,
                     wall_s=time.perf_counter() - t0, imeta=imeta)


def _own(inst) -> Optional[float]:
    """provision.own_capacity_usd(inst), computed apart from the references (check E7-4); None without
    borrower_stats."""
    from ..drivers import provision
    try:
        return float(provision.own_capacity_usd(inst))
    except ValueError:
        return None


def _lender_dict(model) -> dict:
    return {"schedule": model.schedule, "information": model.information, "on_unavailable": model.on_unavailable,
            "violations": model.violations, "params": dict(model.params or {})}


def _seeds_loop(errors: list, spec: dict, tag: str, inst, model, ecfg, refs, own, c: int, seeds, extra=None) -> list:
    rows = []
    for ps in seeds:
        e = mc.try_run(errors, f"{tag} p{ps}", one_run, spec, tag, inst, model, ecfg, refs, own, c, int(ps))
        if e is None:
            continue
        e.update(extra or {})
        rows.append(e)
        a8 = e.get("a8") or {}
        print(f"[e7] {tag} p{ps}: ALG {e['ALG']:.4f} USD ({e['accountings'].get('overflow_over_bl0a')} x BL0a), "
              f"t_a {a8.get('t_a')}, {e['wall_s']:.1f} s", flush=True)
    return rows


# ---------------------------------------------------------------- jobs: week runs (grids (a)-(d), (f))
def run_week(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One week job (§3.10): main, links, stress or allow; the 3 policy seeds of one tag on one instance, built once
    (the instance does not depend on the policy's parameters, §3.3)."""
    from ..algos.guard import c_min
    from ..drivers.run import build
    from ..instance import public_view
    from ..lender import resolve_params
    p = job.params
    tag, mu, mode, c, hz = p["tag"], float(p["mu"]), p["mode"], int(p["c"]), int(p["horizon_min"])
    n, b0, seeds = p.get("n"), p.get("b0"), p["policy_seeds"]
    t0 = time.perf_counter()
    spec0 = week_spec("BL0a", {}, mu=mu, mode=mode, n=n, horizon_min=hz, c=c, seeds=seeds)
    inst, model, ecfg = build(spec0, c)
    build_s = time.perf_counter() - t0
    if not ecfg.check_invariants:
        raise RuntimeError("E7 runs need check_invariants=True (§0 item 5)")
    refs, own, ih = m4.references(inst), _own(inst), mc.instance_hash(inst)
    params = tag_params(tag, inst, b0)
    spec = week_spec(TAGS[tag]["id"], params, mu=mu, mode=mode, n=n, horizon_min=hz, c=c, seeds=seeds,
                     name=f"e7_{p['kind']}_{tag}")
    errors: list = []
    rows = _seeds_loop(errors, spec, tag, inst, model, ecfg, refs, own, c, seeds)
    view = public_view(inst, model.information)
    cm = [float(x) for x in c_min(view)]
    rec = {"meta": {"exp": EXP, "job": job.id, "spec": SPEC, "git_revision": mc.git_revision(),
                    "versions": mc.versions(), "written": mc._now(), "reduced": design()["reduced"]},
           "part": p["part"], "kind": p["kind"], "tag": tag, "policy_id": TAGS[tag]["id"], "params": params,
           "style_key": TAGS[tag]["style"], "mu": mu, "mode": mode, "n": n, "c": c, "b0": b0,
           "b0_key": None if b0 is None else b0_key(b0), "horizon_min": hz, "policy_seeds": list(seeds),
           "instance_hash": ih, "instance": instance_sizes(inst), "references": refs, "own_capacity_usd": own,
           "lender_model": _lender_dict(model), "lender_params_resolved": resolve_params(inst, model),
           "overrides": spec["overrides"],
           "cross_region_links": None if n is None else [list(e) for e in (m4.ROUTING_LINKS[int(n)] or [])],
           "cross_region_arcs": cross_region_arcs(inst),
           "c_min_usd": [x if math.isfinite(x) else None for x in cm],
           "c_min_sum_usd": float(sum(x for x in cm if math.isfinite(x))),
           "build_s": build_s, "runs": rows,
           "errors": [{k: v for k, v in e.items() if k != "traceback"} for e in errors]}
    outputs.dump(_jsonish(rec), run_path(out, p["part"], job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": ih, "bl0a_usd": refs["bl0a_usd"],
            "totals": [r["ALG"] for r in rows], "t_a": [(r.get("a8") or {}).get("t_a") for r in rows],
            "wall_s_runs": [r["wall_s"] for r in rows]}


# ---------------------------------------------------------------- jobs: gap reruns and their LPs (grid (e), §3.8)
def run_gap(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One gap-rerun job: the 3 policy seeds of one tag on ms4_common.gap_instance(c), with
    drivers.run.ratio_validity('slow', inst, model) per run (E7-3)."""
    from ..drivers.run import ratio_validity
    p = job.params
    tag, c, hz, seeds = p["tag"], int(p["c"]), int(p["horizon_min"]), p["policy_seeds"]
    t0 = time.perf_counter()
    inst, model, ecfg, info = m4.gap_instance(c, horizon_min=hz)
    build_s = time.perf_counter() - t0
    if not ecfg.check_invariants:
        raise RuntimeError("E7 runs need check_invariants=True (§0 item 5)")
    refs, own, ih = m4.references(inst), _own(inst), mc.instance_hash(inst)
    rv = ratio_validity(GAP_GRID, inst, model)
    params = tag_params(tag, inst)
    spec = gap_spec(TAGS[tag]["id"], params, horizon_min=hz, c=c, seeds=seeds, name=f"e7_gap_{tag}")
    errors: list = []
    rows = _seeds_loop(errors, spec, tag, inst, model, ecfg, refs, own, c, seeds,
                       extra={"ratio_validity": rv, "instance_hash": ih})
    rec = {"meta": {"exp": EXP, "job": job.id, "spec": SPEC, "git_revision": mc.git_revision(),
                    "versions": mc.versions(), "written": mc._now(), "reduced": design()["reduced"]},
           "part": "gap", "kind": "gap_run", "tag": tag, "policy_id": TAGS[tag]["id"], "params": params,
           "style_key": TAGS[tag]["style"], "c": c, "horizon_min": hz, "policy_seeds": list(seeds),
           "instance_hash": ih, "instance": instance_sizes(inst), "instance_info": info, "references": refs,
           "own_capacity_usd": own, "lender_model": _lender_dict(model), "overrides": spec["overrides"],
           "ratio_validity": rv, "build_s": build_s, "runs": rows,
           "errors": [{k: v for k, v in e.items() if k != "traceback"} for e in errors]}
    outputs.dump(_jsonish(rec), run_path(out, "gap", job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": ih, "totals": [r["ALG"] for r in rows],
            "schedule_hashes": sorted({r["schedule_hash"] for r in rows if r.get("schedule_hash")})}


def run_gap_lp(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One merged LP (§3.8; an 'alone' job): the gap instance (ms4_common.gap_instance, the builder that e7:gap_run
    uses, so the instance hashes agree), BL0a's engine run (lender seed c, policy seed 0), which gives the LP its
    schedule and the BL0a row its gap (M23), and drivers.bench.bench_for(res, inst, 'lp', grid='slow', merged=True,
    allow_large=True, time_limit_s=1500, return_plan=False). Writes gap/lb/lp_c<C>.json (versioned) and BL0a's run."""
    from ..drivers.bench import bench_for
    from ..drivers.run import make_policy, ratio_validity
    from ..engine import simulate
    from .e1 import _solve_record
    from .e6 import bl0a_all
    p = job.params
    c, hz, limit = int(p["c"]), int(p["horizon_min"]), float(p.get("time_limit_s", GAP_LP_LIMIT_S))
    t0 = time.perf_counter()
    inst, model, ecfg, info = m4.gap_instance(c, horizon_min=hz)
    build_s = time.perf_counter() - t0
    if not ecfg.check_invariants:
        raise RuntimeError("E7 runs need check_invariants=True (§0 item 5)")
    refs, own, ih = m4.references(inst), _own(inst), mc.instance_hash(inst)
    rv = ratio_validity(GAP_GRID, inst, model)
    spec = gap_spec("BL0a", {}, horizon_min=hz, c=c, seeds=(0,), name="e7_gap_BL0a")
    t1 = time.perf_counter()
    pol = make_policy(spec, inst)
    res = simulate(inst, pol, model, ecfg, lender_seed=c, policy_seed=0)
    row = run_entry(res, inst, model, refs, own, tag="BL0a", spec=spec, pol=pol, ps=0, c=c,
                    wall_s=time.perf_counter() - t1)
    row.update(ratio_validity=rv, instance_hash=ih, bl0a_analytic_usd=float(bl0a_all(inst)))
    sh = row["schedule_hash"]
    print(f"[e7] {job.id}: BL0a engine {row['ALG']:.4f} USD, analytic {row['bl0a_analytic_usd']:.4f} USD; solving the "
          f"merged LP (time limit {limit:g} s)", flush=True)
    t2 = time.perf_counter()
    sr = bench_for(res, inst, "lp", grid=GAP_GRID, merged=True, allow_large=True, time_limit_s=limit,
                   return_plan=False)
    size = sr.size or {}
    lp = _solve_record(sr, job=job.id, kind="lp", c=c, instance_hash=ih, schedule_hash=sh, time_limit_s=limit,
                       merged=True, merged_sites=size.get("merged_sites"), sites=size.get("sites"),
                       label="merged relaxation LP bound (Proposition M6, PROVEN); ALG / LB bounds ALG / OPT(sigma, "
                             "omega) from above (Proposition M4, PROVEN)",
                       horizon_min=hz, demand=info.get("demand"), demand_sha256=info.get("demand_sha256"),
                       bl0a_analytic_usd=row["bl0a_analytic_usd"], bl0a_engine_usd=row["ALG"],
                       ratio_validity=rv, build_instance_s=build_s, wall_s=time.perf_counter() - t2)
    outputs.dump(lp, lp_path(out, c))
    rec = {"meta": {"exp": EXP, "job": job.id, "spec": SPEC, "git_revision": mc.git_revision(),
                    "versions": mc.versions(), "written": mc._now(), "reduced": design()["reduced"]},
           "part": "gap", "kind": "gap_lp", "tag": "BL0a", "policy_id": "BL0a", "params": {}, "style_key": "bl0a",
           "c": c, "horizon_min": hz, "policy_seeds": [0], "instance_hash": ih, "instance": instance_sizes(inst),
           "instance_info": info, "references": refs, "own_capacity_usd": own, "lender_model": _lender_dict(model),
           "overrides": spec["overrides"], "ratio_validity": rv, "build_s": build_s, "lp_file": f"lb/lp_c{c}.json",
           "runs": [row], "errors": []}
    outputs.dump(_jsonish(rec), run_path(out, "gap", job.id), compact=True)
    print(f"[e7] {job.id}: {sr.status_msg}, objective {sr.objective}, {lp['size']}, solve {sr.solve_s:.1f} s",
          flush=True)
    return {"runs": 1, "errors": [], "status": sr.status, "objective": sr.objective, "instance_hash": ih,
            "schedule_hash": sh, "n_vars": lp["size"].get("n_vars"), "nnz": lp["size"].get("nnz"),
            "solve_s": sr.solve_s, "bl0a_engine_usd": row["ALG"], "bl0a_analytic_usd": row["bl0a_analytic_usd"]}


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    k = job.params["kind"]
    if k in ("main", "links", "stress", "allow"):
        return run_week(job, outputs, out)
    if k == "gap_run":
        return run_gap(job, outputs, out)
    if k == "gap_lp":
        return run_gap_lp(job, outputs, out)
    raise ValueError(f"unknown E7 job {job.id!r}")


def manifest_extra(out) -> dict:
    """The instance hash of every instance of the parts' grids (§2.6): the week instance per (mu, c) and per (routing
    graph n, c), the alignment-1 instance of the stress block and the sweep (the lender mode does not change the
    instance), the gap instance per alignment; the sha256 of the input files."""
    from ..drivers.run import build
    d = design()
    ps = parts()
    hashes: dict = {}

    def week(mu, c, n=None):
        key = f"week:{'mu=' + num_key(mu) if n is None else 'links=' + str(int(n))}:c={int(c)}"
        if key not in hashes:
            inst = build(week_spec("BL0a", {}, mu=mu, n=n, horizon_min=d["horizon_min"], c=c), int(c))[0]
            hashes[key] = mc.instance_hash(inst)
    if "main" in ps:
        for mu in MUS:
            for c in d["alignments"]:
                week(mu, c)
        for n in LINKS:
            for c in d["alignments"]:
                week(MU_MAIN, c, n)
    if "stress" in ps or "allow" in ps:
        week(MU_MAIN, STRESS_C)
    if "gap" in ps:
        for c in d["alignments"]:
            hashes[f"gap:c={int(c)}"] = mc.instance_hash(m4.gap_instance(int(c), horizon_min=d["gap_horizon_min"])[0])
    files = (paths.CONFIGS / m4.E7_CONFIG, paths.CONFIGS / m4.E7R_CONFIG,
             Path(__file__).parent / "q44_blocks" / "Q4.json")
    return {"instance_hashes": hashes, "design": {k: (list(v) if isinstance(v, tuple) else v) for k, v in d.items()},
            "parts": ps, "reduced": d["reduced"], "B0_rule": m4.B0_RULE,
            "inputs_sha256": {str(f.relative_to(paths.REPO)): _sha256(f) for f in files}}


# ---------------------------------------------------------------- summaries: shared pieces
def _agg(values, note: str) -> dict:
    """metrics.aggregate (n, median, p95, max, median_ci95: the 95% percentile bootstrap of the median, B = 2000, seed
    0) and the mean, over the values that are not None; the null form with notes when none is left (§2.6)."""
    v = [float(x) for x in values if x is not None and not isinstance(x, (str, bool))]
    a = mc.median_summary(v)
    if v:
        a["mean"] = float(np.mean(v))
    else:
        for k in ("median", "p95", "max", "mean"):
            put(a, k, None, note)
        a["median_ci95"] = [None, None]
        a["median_ci95_note"] = note
    return a


def _mean(values) -> Optional[float]:
    v = [float(x) for x in values if x is not None]
    return float(np.mean(v)) if v else None


def _part_outputs(out_p: Path, js: list, part: str) -> tuple:
    """({job id: run file} of the part's jobs whose record says 'ok', the ok ids, ignored outputs): a run file present
    while its job's record is not 'ok' (left by an earlier run) is not used and is listed (§2.6)."""
    recs = mc.read_records(out_p)
    data, ok, ignored = {}, set(), []
    for j in js:
        rec = recs.get(j.id) or {}
        path = run_path(out_p, part, j.id)
        if rec.get("status") != "ok":
            if path.is_file():
                ignored.append({"job": j.id, "status": rec.get("status"), "output": str(path.relative_to(out_p))})
            continue
        d = mc.read_json(path)
        if d is not None:
            data[j.id] = d
            ok.add(j.id)
    return data, ok, ignored


def part_summary(root: Path, part: str) -> tuple:
    """(<part>/summary.json or None, the reason it is not used or None, its ignored-output entry or None): a part
    summary whose e7:summary record exists and is not 'ok' (a failed or running summary job, so the file may be an
    earlier run's) is not used (§2.6); a file without a record (a summary called directly, as test_e7 does) is."""
    folder = Path(root) / part
    f = folder / "summary.json"
    rec = mc.read_record(folder, job_id(EXP, "summary"))
    if rec is not None and rec.get("status") != "ok":
        why = f"{part}/summary.json not used: its {job_id(EXP, 'summary')} record has status {rec.get('status')!r}"
        ign = {"job": job_id(EXP, "summary"), "part": part, "status": rec.get("status"),
               "output": f"{part}/summary.json"} if f.is_file() else None
        return None, why, ign
    s = mc.read_json(f)
    return s, (None if s is not None else f"{part}/summary.json is missing or unreadable"), None


def _rows(files, **match) -> list:
    """The run entries of the files whose fields equal `match`, each with the job id and alignment."""
    out = []
    for jid, f in files.items():
        if all(f.get(k) == v for k, v in match.items()):
            out.extend({**r, "job": jid, "c": f.get("c"), "b0": f.get("b0"), "mode": f.get("mode")} for r in f["runs"])
    return out


def _gpu_share(rows) -> Optional[dict]:
    cls: dict = {}
    for r in rows:
        for k, v in (r.get("gpu_hours_by_class") or {}).items():
            cls[k] = cls.get(k, 0.0) + float(v)
    tot = sum(cls.values())
    return {k: v / tot for k, v in sorted(cls.items())} if tot > 0 else None


def _abort_fields(e: dict, rows: list, tag: str, note: str) -> None:
    """abort_share, t_a (the abort slots, sorted), t_a_first, t_a_median and the certificate counts of an A8 tag
    (M24); null with a note for an unguarded tag."""
    if not is_a8(tag):
        why = "unguarded policy (not an A8 tag): no abort, no certificate"
        for k in ("abort_share", "t_a", "t_a_first", "t_a_median", "certificates"):
            put(e, k, None, why)
        return
    a8 = [r["a8"] for r in rows if r.get("a8")]
    tas = sorted(int(x["t_a"]) for x in a8 if x.get("aborted") and x.get("t_a") is not None)
    put(e, "abort_share", sum(bool(x.get("aborted")) for x in a8) / len(a8) if a8 else None, note)
    e["t_a"] = tas
    put(e, "t_a_first", tas[0] if tas else None, "no abort" if a8 else note)
    put(e, "t_a_median", float(np.median(tas)) if tas else None, "no abort" if a8 else note)
    e["certificates"] = m4.count_certificates(a8)


def cost_entry(rows: list, tag: str, note: str = "no run of this cell in the outputs") -> dict:
    """runs.<mu>.<tag> and links.<n>.<tag> of main/summary.json (§3.9, §3.10; module docstring); with no rows every
    field null with its note (§2.6)."""
    acc = [r.get("accountings") or {} for r in rows]
    e = {"n_runs": len(rows), "alignments": sorted({int(r["config_seed"]) for r in rows}),
         "policy_seeds": sorted({int(r["policy_seed"]) for r in rows})}
    if not rows:
        e["note"] = note
    for k in ACC_FIELDS:
        e[k] = _agg([a.get(k) for a in acc], note if not rows else f"{k} unavailable")
    e["saving_pct"] = _agg([100.0 * (1.0 - a["overflow_over_bl0a"]) for a in acc
                            if a.get("overflow_over_bl0a") is not None], note)
    e["saving_pct_total"] = _agg([100.0 * (1.0 - a["total_over_bl0a"]) for a in acc
                                  if a.get("total_over_bl0a") is not None], note)
    if rows:
        e["components_over_bl0a"] = {k: _mean(r["components"].get(k, 0.0) / r["bl0a_usd"] for r in rows
                                              if r.get("bl0a_usd")) for k in COMPONENT_KEYS}
    else:
        put(e, "components_over_bl0a", None, note)
    fs = [r.get("fallback_share_after_reclaims") for r in rows]
    e["fallback_share_after_reclaims"] = {**_agg([x for x in fs if x is not None],
                                                 "no run with a reclaim-caused capacity drop" if rows else note),
                                          "n_null": sum(x is None for x in fs)}
    for k in METRIC_FIELDS:
        e[k] = _agg([r.get(k) for r in rows], note if not rows else f"{k} undefined in every run")
    e["n_leases"] = _agg([r.get("n_leases") for r in rows], note)
    put(e, "gpu_hour_share", _gpu_share(rows), "no leased GPU-hour" if rows else note)
    _abort_fields(e, rows, tag, note)
    e["info_class_reported"] = sorted({r.get("info_class_reported") for r in rows if r.get("info_class_reported")})
    e["n_runs_with_invariant_failures"] = sum(1 for r in rows if r.get("n_invariant_failures"))
    e["n_runs_with_gpu_only_lease_slots"] = sum(1 for r in rows if r.get("gpu_only_lease_slots"))
    return e


def _label(r: dict) -> dict:
    return {"job": r.get("job"), "seed": r.get("policy_seed"), "c": r.get("c")}


# ---------------------------------------------------------------- checks of the parts (§3.11)
def _status(ok: bool, n: int) -> str:
    return ("pass" if ok else "fail") if n else "missing"


def check_certificates(rows: list) -> dict:
    """E7-1 over the A8 runs of a part."""
    a8 = [r for r in rows if r.get("a8")]
    cnt = m4.count_certificates([r["a8"] for r in a8])
    unavailable = [_label(r) for r in a8 if not (r["a8"].get("certificate") or {}).get("available")]
    failures = [{**_label(r), "case": r["a8"]["certificate_case"], "t_a": r["a8"].get("t_a")} for r in a8
                if r["a8"]["certificate_case"] in m4.PROVEN_CASES and (r["a8"].get("certificate") or {}).get("held")
                is not True]
    wc = [{**_label(r), "t_a": r["a8"].get("t_a")} for r in a8 if r["a8"]["certificate_case"] == "W(c)"]
    ok = not unavailable and not failures
    return {"status": _status(ok, len(a8)), "claim": CHECK_CLAIMS["E7-1"], "n_runs": len(a8), "certificates": cnt,
            "unavailable": unavailable[:50], "n_unavailable": len(unavailable), "failures": failures[:50],
            "n_failures": len(failures), "w_c_runs": wc[:200], "n_w_c": len(wc)}


def check_clean(rows: list) -> dict:
    """E7-2: no invariant failure and no GPU-only lease slot in any run (BL2's sub-runs included)."""
    inv, gpu = [], []
    for r in rows:
        subs = r.get("sub_runs") or []
        if r.get("n_invariant_failures") or any(s.get("n_invariant_failures") for s in subs):
            inv.append({**_label(r), "first": (r.get("invariant_failures_first") or [])[:2]})
        if r.get("gpu_only_lease_slots") or any(s.get("gpu_only_lease_slots") for s in subs):
            gpu.append(_label(r))
    return {"status": _status(not inv and not gpu, len(rows)), "claim": CHECK_CLAIMS["E7-2"], "n_runs": len(rows),
            "n_sub_runs": sum(len(r.get("sub_runs") or []) for r in rows), "invariant_failures": inv[:50],
            "n_invariant_failures": len(inv), "gpu_only_lease_slots": gpu[:50], "n_gpu_only": len(gpu)}


def check_accounting(rows: list, refs_by: Optional[dict] = None) -> dict:
    """E7-4: total - overflow = own capacity (provision.own_capacity_usd, computed apart) for every run and, with
    refs_by ({alignment: references}), BL0a in total accounting = BL0a + own capacity (1e-9 relative)."""
    bad, worst = [], 0.0
    for r in rows:
        a, own = r.get("accountings") or {}, r.get("own_capacity_usd")
        if own is None or a.get("total_usd") is None:
            bad.append({**_label(r), "why": "own capacity or total accounting missing"})
            continue
        d = abs((a["total_usd"] - a["overflow_usd"]) - own) / max(1.0, abs(own))
        worst = max(worst, d)
        if d > REL_TOL or a["overflow_usd"] != r["ALG"]:
            bad.append({**_label(r), "rel_diff": d})
    ref_bad, n_ref = [], 0
    for c, ref in (refs_by or {}).items():
        n_ref += 1
        if ref.get("bl0a_total_usd") is None or ref.get("own_capacity_usd") is None:
            ref_bad.append({"c": c, "why": "own capacity missing"})
            continue
        d = abs(ref["bl0a_total_usd"] - (ref["bl0a_usd"] + ref["own_capacity_usd"])) / max(1.0, ref["bl0a_total_usd"])
        worst = max(worst, d)
        if d > REL_TOL:
            ref_bad.append({"c": c, "rel_diff": d})
    return {"status": _status(not bad and not ref_bad, len(rows)), "claim": CHECK_CLAIMS["E7-4"],
            "n_runs": len(rows), "n_alignments_checked": n_ref, "max_rel_diff": worst, "tolerance": REL_TOL,
            "failures": bad[:50], "n_failures": len(bad), "reference_failures": ref_bad}


def _rule_problems(a: dict, b0) -> list:
    """The deviations of one A8 record from its allowance rule (E7-6): M36's for b0 None, else the sweep's."""
    bad = []
    bl0a, B0 = a.get("bl0a_usd"), a.get("B0_usd")
    if b0 == "auto":
        if a.get("B0_rule") != m4.THEORY_RULE:
            bad.append(f"B0_rule {a.get('B0_rule')!r} != {m4.THEORY_RULE!r}")
        if a.get("kappa") != 10.0:
            bad.append(f"kappa {a.get('kappa')!r} != 10")
    else:
        share = m4.B0_SHARE if b0 is None else float(b0)
        want = m4.B0_RULE if b0 is None else f"{num_key(share)}*BL0a"
        if a.get("B0_rule") != want:
            bad.append(f"B0_rule {a.get('B0_rule')!r} != {want!r}")
        if a.get("kappa") is not None:
            bad.append(f"kappa {a.get('kappa')!r} is not null")
        if bl0a is None or B0 is None or abs(B0 - share * bl0a) > m4.SHARE_TOL * abs(share * bl0a):
            bad.append(f"B0 {B0!r} != {share} x BL0a {bl0a!r}")
        if a.get("info_class_reported") != m4.INFO_CLASS_REPORTED:
            bad.append(f"info_class_reported {a.get('info_class_reported')!r}")
    if a.get("gamma") != 1.0:
        bad.append(f"gamma {a.get('gamma')!r} != 1")
    rep = a.get("B0_report_usd")
    if rep is None or B0 is None or abs(rep - B0) > m4.SHARE_TOL * max(abs(B0), 1e-300):
        bad.append(f"A8's resolved B0 {rep!r} != the passed {B0!r}")
    cert = a.get("certificate") or {}
    if cert.get("available") and (cert.get("gamma") != 1.0 or cert.get("kappa") != a.get("kappa")):
        bad.append(f"A8's report gamma {cert.get('gamma')!r}, kappa {cert.get('kappa')!r}")
    return bad


def check_allowance(rows: list, sweep: bool = False) -> dict:
    """E7-6 over the A8 runs of a part: M36's rule outside the sweep, the sweep's own rule in it; the run's BL0a is
    e6.bl0a_all of its own instance (the run file's references)."""
    a8 = [r for r in rows if r.get("a8")]
    bad = []
    for r in a8:
        b0 = r.get("b0") if sweep else None
        probs = _rule_problems(r["a8"], b0)
        if r["a8"].get("bl0a_usd") != r.get("bl0a_usd"):
            probs.append(f"bl0a_usd {r['a8'].get('bl0a_usd')!r} != the instance's BL0a {r.get('bl0a_usd')!r}")
        if probs:
            bad.append({**_label(r), "b0": b0, "problems": probs})
    rules = sorted({r["a8"].get("B0_rule") for r in a8 if r["a8"].get("B0_rule")})
    return {"status": _status(not bad, len(a8)), "claim": CHECK_CLAIMS["E7-6"], "n_runs": len(a8), "sweep": sweep,
            "rules_found": rules, "failures": bad[:50], "n_failures": len(bad), "tolerance": m4.SHARE_TOL}


def abort_table(groups: dict) -> dict:
    """E7-11's inputs: per group key the A8 runs' abort share, the first and the median abort slot, the cases."""
    out = {}
    for key, rows in groups.items():
        a8 = [r["a8"] for r in rows if r.get("a8")]
        if not a8:
            continue
        tas = sorted(int(x["t_a"]) for x in a8 if x.get("aborted") and x.get("t_a") is not None)
        e = {"n_runs": len(a8), "abort_share": sum(bool(x.get("aborted")) for x in a8) / len(a8)}
        put(e, "t_a_first", tas[0] if tas else None, "no abort")
        put(e, "t_a_median", float(np.median(tas)) if tas else None, "no abort")
        e["by_case"] = {c: sum(x.get("certificate_case") == c for x in a8) for c in m4.CASES}
        out[key] = e
    return out


def _certs_block(rows: list) -> dict:
    a8 = [r for r in rows if r.get("a8")]
    cnt = m4.count_certificates([r["a8"] for r in a8])
    cnt["w_c_runs"] = [{**_label(r), "t_a": r["a8"].get("t_a")} for r in a8 if r["a8"]["certificate_case"] == "W(c)"]
    return cnt


def _meta(part: str, d: dict, js: list, ok: set, ignored: list, **extra) -> dict:
    meta = {"exp": EXP, "part": part, "spec": SPEC, "git_revision": mc.git_revision(), "versions": mc.versions(),
            "written": mc._now(), "reduced": d["reduced"],
            "grids": {"alignments": list(d["alignments"]), "alignments_design": list(ALIGNMENTS),
                      "policy_seeds": list(d["policy_seeds"]), "policy_seeds_design": list(POLICY_SEEDS),
                      "horizon_min": d["horizon_min"], "gap_horizon_min": d["gap_horizon_min"]},
            "tags": {t: {"policy_id": v["id"], "params": ("ms4_common.sublet_params(inst, %r)" % v["inner"])
                         if v["id"] == "A8" else v["params"], "style_key": v["style"], "a8": v["id"] == "A8",
                         "q44_tag": v["q44"]} for t, v in TAGS.items()},
            "B0_rule": m4.B0_RULE, "info_class_reported_a8": m4.INFO_CLASS_REPORTED,
            "jobs_ok": len(ok), "jobs_missing": [j.id for j in js if j.id not in ok], "ignored_outputs": ignored}
    if d["reduced"]:
        meta["reduced_note"] = (f"reduced job list ({REDUCED_ENV}=1): alignment 1, policy seed 0, a "
                                f"{REDUCED_HORIZON_MIN}-min horizon; not a result")
    meta.update(extra)
    return meta


def _refs_by_alignment(files: dict, **match) -> dict:
    """{alignment key: references} from the first run file of each alignment that matches."""
    out: dict = {}
    for f in files.values():
        if all(f.get(k) == v for k, v in match.items()):
            out.setdefault(num_key(f["c"]), f["references"])
    return dict(sorted(out.items()))


def _write_tables(path: Path, title: str, blocks: list) -> None:
    lines = [f"# {title}", ""]
    for head, table in blocks:
        lines += [f"## {head}", "", table, ""]
    mc.write_text("\n".join(lines) + "\n", path)


def _checks_table(checks: dict) -> str:
    return mc.md_table(["check", "status"], [[k, v.get("status")] for k, v in checks.items()])


def _ci(a: dict) -> list:
    return (a or {}).get("median_ci95") or [None, None]


# ---------------------------------------------------------------- summary: part main
def summary_main(out_m: Path) -> dict:
    out_m = Path(out_m)
    d = design()
    js = [j for j in jobs_all() if j.params["part"] == "main"]
    files, ok, ignored = _part_outputs(out_m, js, "main")
    # the other part summaries (pass 2 writes them before main's), each only with an 'ok' e7:summary record
    root = e7_root(out_m)
    others, others_why = {}, {}
    for p in PARTS:
        if p != "main":
            others[p], others_why[p], ign = part_summary(root, p)
            if ign:
                ignored.append(ign)
    mains = {k: f for k, f in files.items() if f.get("kind") == "main"}
    links = {k: f for k, f in files.items() if f.get("kind") == "links"}
    runs: dict = {}
    for mu in MUS:
        for tag in TAGS:
            runs.setdefault(num_key(mu), {})[tag] = cost_entry(_rows(mains, mu=float(mu), tag=tag), tag)
    lk: dict = {}
    for n in LINKS:
        for tag in LINK_TAGS:
            lk.setdefault(num_key(n), {})[tag] = cost_entry(_rows(links, n=int(n), tag=tag), tag)
    refs = _refs_by_alignment(mains, mu=MU_MAIN)
    all_rows = _rows(mains) + _rows(links)
    # BL0a at every mu and routing graph of an alignment (one denominator per alignment, §3.7(c), E7-9)
    bl0a_sets = {}
    for f in list(mains.values()) + list(links.values()):
        bl0a_sets.setdefault(num_key(f["c"]), set()).add(f["references"]["bl0a_usd"])
    bl0a_rel = {c: (max(v) / min(v) - 1.0) if min(v) > 0 else None for c, v in bl0a_sets.items()}
    instances = {}
    for f in mains.values():
        instances.setdefault(f"mu={num_key(f['mu'])}:c={int(f['c'])}", {**f["instance"], "instance_hash":
                                                                         f["instance_hash"]})
    for f in links.values():
        instances.setdefault(f"links={int(f['n'])}:c={int(f['c'])}", {**f["instance"], "instance_hash":
                                                                       f["instance_hash"],
                                                                       "cross_region_arcs": f["cross_region_arcs"]})
    arcs_ok = {}
    for f in links.values():
        want = sorted(tuple(sorted(e)) for e in (f.get("cross_region_links") or []))
        arcs_ok[f"links={int(f['n'])}:c={int(f['c'])}"] = sorted(tuple(e) for e in f["cross_region_arcs"]) == want
    links_meta = {num_key(n): [list(e) for e in m4.ROUTING_LINKS[n]] for n in LINKS}
    links_meta["5"] = "S7, config.DEFAULT_ADJACENCY: the main grid (runs.1)"
    per_c = {k: {c: r.get(k) for c, r in refs.items()} for k in
             ("bl0a_usd", "own_capacity_usd", "bl0a_total_usd", "bl0b_overflow_usd", "bl0b_total_usd",
              "committed_price_usd_per_gpu_h")}
    meta = _meta("main", d, js, ok, ignored, grids_main={"mu": list(MUS), "mu_main": MU_MAIN, "links": list(LINKS),
                                                         "link_tags": list(LINK_TAGS)},
                 references=refs, links=links_meta, instances=instances, **per_c)
    # checks of the part
    ch = {"E7-1": check_certificates(all_rows), "E7-2": check_clean(all_rows),
          "E7-4": check_accounting(all_rows, refs), "E7-6": check_allowance(all_rows)}
    b0b_bad = [c for c, r in refs.items() if r.get("bl0b_overflow_usd") is None or r.get("bl0b_total_usd") is None]
    ch["E7-5"] = {"status": _status(not b0b_bad, len(refs)), "claim": CHECK_CLAIMS["E7-5"],
                  "bl0b_overflow_usd": per_c["bl0b_overflow_usd"], "bl0b_total_usd": per_c["bl0b_total_usd"],
                  "alignments_without_bl0b": b0b_bad, "note": "part main: BL0b recorded in both accountings per "
                                                              "alignment; the BL0a identity is part gap's"}
    sav = {}
    for tag in LINK_TAGS:
        sav[tag] = {num_key(n): lk[num_key(n)][tag]["saving_pct"].get("median") for n in LINKS}
        sav[tag]["5"] = runs[num_key(MU_MAIN)][tag]["saving_pct"].get("median")
    ch["E7-9"] = {"status": "informative", "claim": CHECK_CLAIMS["E7-9"], "saving_pct_median": sav,
                  "bl0a_max_rel_diff_over_mu_and_n": bl0a_rel,
                  "one_bl0a_per_alignment": all(v is not None and v <= REL_TOL for v in bl0a_rel.values()),
                  "cross_region_arcs_equal_links": arcs_ok}
    groups = {f"mu={k}:{t}": _rows(mains, mu=float(mu), tag=t) for mu in MUS for k in [num_key(mu)] for t in A8_TAGS}
    groups.update({f"links={n}:Sublet": _rows(links, n=int(n), tag="Sublet") for n in LINKS})
    ch["E7-11"] = {"status": "informative", "claim": CHECK_CLAIMS["E7-11"], "by_grid": abort_table(groups)}
    above = {k: sorted(t for t, e in by.items() if (e["overflow_over_bl0a"].get("median") or 0.0) > 1.0)
             for k, by in runs.items()}
    ch["E7-12"] = {"status": "informative", "claim": CHECK_CLAIMS["E7-12"], "above_bl0a_by_mu": above,
                   "above_bl0a_headline": above.get(num_key(MU_MAIN), []),
                   "median_overflow_over_bl0a_headline": {t: e["overflow_over_bl0a"].get("median")
                                                          for t, e in runs[num_key(MU_MAIN)].items()}}
    local = {k: {**ch[k], "part": "main"} for k in PART_CHECKS["main"]}
    summ = {"meta": meta, "runs": runs, "links": lk, "certificates": _certs_block(all_rows), "checks_local": local}
    summ["checks"] = combine_checks(local, others, others_why)
    mc.dump_json(summ, out_m / "summary.json")
    t3 = table3(root, summ, others, others_why)
    _write_tables(out_m / "tables.md", "E7: end-to-end savings, main grid (design/sim_spec_ms4.md §3)",
                  tables_main(summ, t3))
    return summ


def combine_checks(local_main: dict, others: dict, why: Optional[dict] = None) -> dict:
    """main/summary.json checks: every check id of §3.11 once, from the part summaries that compute it (PART_CHECKS):
    'informative' for E7-8 ... E7-12; else 'fail' if a part fails, 'pass' if every part passes, 'pending' if one is
    pending, else 'missing' (a part summary or its entry absent, or the summary not used: `why`, part_summary)."""
    out = {}
    why = why or {}
    for cid in CHECK_IDS:
        ents = {}
        for p in PARTS:
            if cid not in PART_CHECKS[p]:
                continue
            if p == "main":
                e = local_main.get(cid)
            else:
                s = others.get(p)
                e = (s.get("checks") or {}).get(cid) if isinstance(s, dict) else None
            ents[p] = e if isinstance(e, dict) else {
                "status": "missing", "note": why.get(p) or f"{p}/summary.json is missing or has no entry {cid}"}
        sts = [e.get("status") for e in ents.values()]
        if cid in INFORMATIVE:
            st = "informative"
        elif "fail" in sts:
            st = "fail"
        elif sts and all(s == "pass" for s in sts):
            st = "pass"
        elif "pending" in sts:
            st = "pending"
        else:
            st = "missing"
        out[cid] = {"status": st, "claim": CHECK_CLAIMS[cid], "parts": ents,
                    "part_status": {p: e.get("status") for p, e in ents.items()}}
    return out


def tables_main(s: dict, t3: dict) -> list:
    blocks = []
    if s["meta"].get("reduced"):
        blocks.append(("Reduced run", s["meta"]["reduced_note"]))
    for mk, by in s["runs"].items():
        rows = []
        for tag, e in by.items():
            o, t = e["overflow_over_bl0a"], e["total_over_bl0a"]
            ci = _ci(o)
            rows.append([tag, e["n_runs"], o.get("median"), ci[0], ci[1], t.get("median"),
                         e["saving_pct"].get("median"), e["fallback_share_after_reclaims"].get("median"),
                         e.get("abort_share")])
        blocks.append((f"Week cost over BL0a at mu / beta~ = {mk} (median [95% CI] over the runs)",
                       mc.md_table(["tag", "runs", "overflow / BL0a", "ci lo", "ci hi", "total / BL0a", "saving %",
                                    "fallback after reclaims", "abort share"], rows)))
    rows = [[n, tag, e["n_runs"], e["saving_pct"].get("median"), _ci(e["saving_pct"])[0], _ci(e["saving_pct"])[1]]
            for n, by in s["links"].items() for tag, e in by.items()]
    blocks.append(("Saving over BL0a (%) against cross-region links n (n = 5: mu = 1 above)",
                   mc.md_table(["n", "tag", "runs", "median", "ci lo", "ci hi"], rows)))
    cols = ("usd_overflow", "usd_total", "saving_pct", "gap", "fallback_share_after_reclaims", "W0", "abort_share")
    rows = []
    for tag in TABLE3_ROWS:
        r = t3["rows"][tag]
        cells = [r["usd"]["overflow"], r["usd"]["total"]] + [r[k] for k in cols[2:]]
        rows.append([r["label"]] + [f"{_fmt(x['median'])} [{_fmt(x['interval'][0])}, {_fmt(x['interval'][1])}] "
                                    f"n={x['n']}" for x in cells])
    blocks.append(("Table III cells: median [95% interval] n (table3.json)",
                   mc.md_table(["policy"] + list(cols), rows)))
    cap = t3["caption"]["certificates"]
    blocks.append(("Certificates over every A8 run of E7 (Table III caption)",
                   mc.md_table(["case", "runs", "held"], [[k, v["runs"], v["held"]]
                                                          for k, v in cap["by_case"].items()])))
    blocks.append(("Checks (§3.11, combined over the parts)", _checks_table(s["checks"])))
    return blocks


def _fmt(x) -> str:
    return "–" if x is None else (f"{x:.4g}" if isinstance(x, float) else str(x))


# ---------------------------------------------------------------- summary: part stress
def stress_entry(rows: list, tag: str, note: str = "no run of this cell in the outputs") -> dict:
    """modes.<mode>.<tag> of stress/summary.json (§3.10; module docstring)."""
    by = {str(int(r["policy_seed"])): r for r in sorted(rows, key=lambda r: int(r["policy_seed"]))}
    acc = {s: r.get("accountings") or {} for s, r in by.items()}
    e = {"n_runs": len(rows), "seeds": [int(s) for s in by]}
    if not rows:
        e["note"] = note
    e["r0"] = {s: a.get("overflow_over_bl0a") for s, a in acc.items()}
    put(e, "r0_mean", _mean(e["r0"].values()), note)
    e["total_over_bl0a"] = {s: a.get("total_over_bl0a") for s, a in acc.items()}
    put(e, "total_over_bl0a_mean", _mean(e["total_over_bl0a"].values()), note)
    e["overflow_usd"] = {s: a.get("overflow_usd") for s, a in acc.items()}
    e["total_usd"] = {s: a.get("total_usd") for s, a in acc.items()}
    e["accountings"] = acc
    ints = {s: (r.get("intensity") or {}).get("announcements_per_site_day") for s, r in by.items()}
    put(e, "intensity", _mean(ints.values()), note)
    e["intensity_by_seed"] = ints
    fs = [r.get("fallback_share_after_reclaims") for r in rows]
    e["fallback_share_after_reclaims"] = {**_agg([x for x in fs if x is not None],
                                                 "no run with a reclaim-caused capacity drop" if rows else note),
                                          "n_null": sum(x is None for x in fs)}
    put(e, "gpu_hour_share", _gpu_share(rows), "no leased GPU-hour" if rows else note)
    if is_a8(tag):
        e["aborted"] = {s: bool(r["a8"].get("aborted")) for s, r in by.items()}
        e["t_a"] = {s: r["a8"].get("t_a") for s, r in by.items()}
        e["certificate_case"] = {s: r["a8"].get("certificate_case") for s, r in by.items()}
        put(e, "abort_share", _mean([float(v) for v in e["aborted"].values()]), note)
        tas = [int(v) for v in e["t_a"].values() if v is not None]
        put(e, "t_a_median", float(np.median(tas)) if tas else None, "no abort" if rows else note)
        e["certificates"] = m4.count_certificates([r["a8"] for r in rows])
    else:
        why = "unguarded policy (not an A8 tag): no abort, no certificate"
        for k in ("aborted", "t_a", "certificate_case", "abort_share", "t_a_median", "certificates"):
            put(e, k, None, why)
    return e


def w0_of(r0_by_mode: dict) -> dict:
    """W0 of one policy (ms4_common.w0, one cell 'c1' at alignment 1) with criterion S (W0 <= 1.05)."""
    w = m4.w0({m: {"c1": v} for m, v in r0_by_mode.items()})
    w["criterion_S"] = None if w.get("value") is None else bool(w["value"] <= CRITERION_S)
    w["criterion_S_threshold"] = CRITERION_S
    return w


def summary_stress(out_s: Path) -> dict:
    out_s = Path(out_s)
    d = design()
    js = [j for j in jobs_all() if j.params["part"] == "stress"]
    files, ok, ignored = _part_outputs(out_s, js, "stress")
    modes, w0 = {}, {}
    for mode in stress_modes():
        for tag in TAGS:
            modes.setdefault(mode, {})[tag] = stress_entry(_rows(files, mode=mode, tag=tag), tag)
    for tag in TAGS:
        r0 = {m: {s: v for s, v in modes[m][tag]["r0"].items() if v is not None} for m in stress_modes()
              if modes[m][tag]["n_runs"]}
        w0[tag] = w0_of(r0)
    all_rows = _rows(files)
    refs = _refs_by_alignment(files)
    mode_meta = {}
    for f in files.values():
        mode_meta.setdefault(f["mode"], {"lender_model": f["lender_model"],
                                         "lender_params_resolved": f["lender_params_resolved"]})
    meta = _meta("stress", d, js, ok, ignored, alignment=STRESS_C, mu=MU_MAIN, modes=mode_meta,
                 modes_expected=list(stress_modes()), references=refs.get(num_key(STRESS_C)),
                 criterion_S=CRITERION_S)
    ch = {"E7-1": check_certificates(all_rows), "E7-2": check_clean(all_rows),
          "E7-4": check_accounting(all_rows, refs), "E7-6": check_allowance(all_rows)}
    ch["E7-8"] = {"status": "informative", "claim": CHECK_CLAIMS["E7-8"],
                  "W0": {t: {"value": w.get("value"), "mode": w.get("mode"), "criterion_S": w.get("criterion_S"),
                             "modes_missing": w.get("modes_missing")} for t, w in w0.items()},
                  "meets_criterion_S": sorted(t for t, w in w0.items() if w.get("criterion_S") is True),
                  "misses_criterion_S": sorted(t for t, w in w0.items() if w.get("criterion_S") is False)}
    ch["E7-11"] = {"status": "informative", "claim": CHECK_CLAIMS["E7-11"],
                   "by_grid": abort_table({f"mode={m}:{t}": _rows(files, mode=m, tag=t) for m in stress_modes()
                                           for t in A8_TAGS})}
    checks = {k: {**ch[k], "part": "stress"} for k in PART_CHECKS["stress"]}
    summ = {"meta": meta, "modes": modes, "W0": w0, "certificates": _certs_block(all_rows), "checks": checks}
    mc.dump_json(summ, out_s / "summary.json")
    rows = [[m, t, e["n_runs"], e.get("r0_mean"), e.get("intensity"), e.get("abort_share")]
            for m, by in modes.items() for t, e in by.items()]
    blocks = [("Reduced run", meta["reduced_note"])] if d["reduced"] else []
    blocks += [("r0 = week cost / BL0a (overflow accounting) per stress mode, alignment 1 (mean over the seeds)",
                mc.md_table(["mode", "tag", "runs", "r0 mean", "announcements / site-day", "abort share"], rows)),
               ("W0 (note §5.5): the largest 3-seed mean of r0 over the five stress modes",
                mc.md_table(["tag", "W0", "mode", "criterion S (<= 1.05)"],
                            [[t, w.get("value"), w.get("mode"), w.get("criterion_S")] for t, w in w0.items()])),
               ("Checks (§3.11)", _checks_table(checks))]
    _write_tables(out_s / "tables.md", "E7: stress block (design/sim_spec_ms4.md §3.7(d))", blocks)
    return summ


# ---------------------------------------------------------------- summary: part gap
LP_FIELDS = ("job", "status", "status_msg", "objective", "dual_bound", "gap", "grid", "method", "benchmark", "size",
             "build_s", "solve_s", "peak_rss_mb", "time_limit_s", "instance_hash", "schedule_hash", "merged_sites",
             "sites", "label", "horizon_min", "wall_s")      # gap/summary.json lp.<c>, from gap/lb/lp_c<C>.json
BL0A_FIELDS = ("analytic_usd", "engine_usd", "rel_diff", "bl0a_own_demand_usd", "demand_sha256")


def _lp_null(note: str) -> dict:
    """lp.<c> without an 'ok' e7:gap_lp output: every field of the non-null form null with the note (§2.6)."""
    d = {"note": note}
    for k in LP_FIELDS + ("file",):
        if k == "size":
            d[k] = {}                   # n_vars, nnz, ... absent: the tables print "–"
        else:
            put(d, k, None, note)
    return d


def _bl0a_null(note: str) -> dict:
    """bl0a_by_alignment.<c> without an 'ok' e7:gap_lp output (§2.6)."""
    d = {"note": note}
    for k in BL0A_FIELDS:
        put(d, k, None, note)
    return d


def _lp_input(lp: Optional[dict], row: dict) -> dict:
    """The LP record for Q39's rule of one gap run: the record if its instance and schedule hashes are the run's, else
    a stand-in {'status': 'stale' | 'missing'} (no lower bound)."""
    if lp is None or lp.get("status") is None:
        return {"status": "missing"}
    bad = [w for w, a, b in (("instance hash", lp.get("instance_hash"), row.get("instance_hash")),
                             ("schedule hash", lp.get("schedule_hash"), row.get("schedule_hash"))) if a != b]
    if bad:
        return {"status": "stale", "stale_note": f"LP record {lp.get('job')!r}: {' and '.join(bad)} differ from the "
                                                 "run's"}
    return lp


def gap_entry(rows: list, tag: str, note: str = "no run of this tag in the outputs") -> dict:
    """runs.<tag> of gap/summary.json (§3.10; module docstring); rows carry their 'lb' (ms3_common.lb_record)."""
    rl = [r["lb"].get("ratio_LB") for r in rows if r["lb"].get("ratio_LB") is not None]
    acc = [r.get("accountings") or {} for r in rows]
    e = {"n_runs": len(rows), "n_ratio": len(rl), "alignments": sorted({int(r["config_seed"]) for r in rows})}
    if not rows:
        e["note"] = note
    e["ratio_LB"] = _agg(rl, "no run with a lower bound" if rows else note)
    e["alg_usd"] = _agg([r["ALG"] for r in rows], note)          # = overflow_usd (the engine's total)
    for k in ACC_FIELDS:
        e[k] = _agg([a.get(k) for a in acc], note if not rows else f"{k} unavailable")
    e["p1_flags"] = [{**_label(r), "ratio_LB": r["lb"]["ratio_LB"]} for r in rows
                     if tag != "BL2" and r.get("plan_class_p1") and r["lb"].get("ratio_LB") is not None
                     and r["lb"]["ratio_LB"] < 1.0 - P1_TOL]
    e["n_plan_class_p1"] = sum(1 for r in rows if r.get("plan_class_p1"))
    e["ratio_validity"] = [r.get("ratio_validity") for r in rows]
    if tag in TAGS:
        _abort_fields(e, rows, tag, note)
    return e


def summary_gap(out_g: Path) -> dict:
    out_g = Path(out_g)
    d = design()
    js = [j for j in jobs_all() if j.params["part"] == "gap"]
    files, ok, ignored = _part_outputs(out_g, js, "gap")
    lps, lp_meta, lp_why = {}, {}, {}
    for c in ALIGNMENTS:
        jid = gap_lp_id(c)
        rec = mc.read_record(out_g, jid)
        path = lp_path(out_g, c)
        if rec is None or rec.get("status") != "ok":
            if rec is not None or path.is_file():
                lp_why[c] = f"job {jid} has record status {None if rec is None else rec.get('status')!r}"
                lp_meta[num_key(c)] = _lp_null(lp_why[c])
                if path.is_file():
                    ignored.append({"job": jid, "status": None if rec is None else rec.get("status"),
                                    "output": str(path.relative_to(out_g))})
            elif c in d["alignments"]:
                lp_why[c] = f"job {jid} has no record"
                lp_meta[num_key(c)] = _lp_null(lp_why[c])
            continue
        lp = mc.read_json(path)
        if lp is None:
            lp_why[c] = f"{path.name} is missing or unreadable"
            lp_meta[num_key(c)] = _lp_null(lp_why[c])
            continue
        lps[c] = lp
        lp_meta[num_key(c)] = {k: lp.get(k) for k in LP_FIELDS}
        lp_meta[num_key(c)]["file"] = f"lb/lp_c{int(c)}.json"
    # every run with its alignment's LP (paired by instance and schedule hash) and Q39's record
    by_tag: dict = {}
    all_rows = []
    for f in files.values():
        for r in f["runs"]:
            r = {**r, "job": f["meta"]["job"], "c": f["c"]}
            lp = lps.get(int(f["c"]))
            r["lb"] = mc.lb_record(r["ALG"], _lp_input(lp, r), None, reason=r.get("ratio_validity"))
            by_tag.setdefault(r["tag"], []).append(r)
            all_rows.append(r)
    runs = {t: gap_entry(by_tag.get(t, []), t) for t in list(TAGS) + ["BL0a"]}
    bl0a, refs, inst_meta = {}, {}, {}
    for f in files.values():
        refs.setdefault(num_key(f["c"]), f["references"])
        inst_meta.setdefault(num_key(f["c"]), {**f["instance"], "instance_hash": f["instance_hash"],
                                               "demand_sha256": f["instance_info"].get("demand_sha256"),
                                               "bl0a_own_demand_usd": f["instance_info"].get("bl0a_own_demand")})
        if f["kind"] == "gap_lp":
            r = f["runs"][0]
            a, b = r["bl0a_analytic_usd"], r["ALG"]
            bl0a[num_key(f["c"])] = {"analytic_usd": a, "engine_usd": b, "rel_diff": abs(a - b) / max(1.0, abs(a)),
                                     "bl0a_own_demand_usd": f["instance_info"].get("bl0a_own_demand"),
                                     "demand_sha256": f["instance_info"].get("demand_sha256")}
    # an alignment of the grid without an 'ok' e7:gap_lp output keeps its entry, null with the reason (§2.6)
    bl0a_missing = [int(c) for c in d["alignments"] if num_key(c) not in bl0a]
    bl0a_all_c = dict(bl0a)
    for c in bl0a_missing:
        bl0a_all_c[num_key(c)] = _bl0a_null(lp_why.get(c) or f"no 'ok' output of {gap_lp_id(c)}")
    bl0a_all_c = dict(sorted(bl0a_all_c.items(), key=lambda kv: int(kv[0])))
    meta = _meta("gap", d, js, ok, ignored, references=dict(sorted(refs.items())),
                 instances=dict(sorted(inst_meta.items())),
                 lp_settings={"kind": "lp", "grid": GAP_GRID, "merged": True, "allow_large": True,
                              "time_limit_s": GAP_LP_LIMIT_S, "return_plan": False,
                              "call": "drivers.bench.bench_for on BL0a's run (§3.8)"},
                 instance="ms4_common.gap_instance(c): bench_e7r with e7r_h5_overrides(), the E7 week's day-1 "
                          "demand (M22)")
    ch = {"E7-1": check_certificates(all_rows), "E7-2": check_clean(all_rows),
          "E7-4": check_accounting(all_rows, dict(sorted(refs.items()))), "E7-6": check_allowance(all_rows)}
    ch["E7-3"] = check_gap(all_rows, lps, d["alignments"])
    bad5 = [{"c": c, **v} for c, v in bl0a.items() if v["rel_diff"] > REL_TOL]
    inst_bl0a = [{"job": f["meta"]["job"], "c": f["c"]} for f in files.values()
                 if num_key(f["c"]) in bl0a and abs(f["references"]["bl0a_usd"] - bl0a[num_key(f["c"])]["analytic_usd"])
                 > REL_TOL * max(1.0, abs(bl0a[num_key(f["c"])]["analytic_usd"]))]
    st5 = "fail" if (bad5 or inst_bl0a) else ("missing" if (not bl0a or bl0a_missing) else "pass")
    ch["E7-5"] = {"status": st5, "claim": CHECK_CLAIMS["E7-5"],
                  "bl0a_by_alignment": bl0a_all_c, "alignments_missing": bl0a_missing, "failures": bad5,
                  "runs_with_another_bl0a": inst_bl0a,
                  "tolerance": REL_TOL, "note": "part gap: BL0a's analytic cost against its engine run on every gap "
                                                "instance; BL0b in both accountings is part main's"}
    s_med, b_med = runs["Sublet"]["ratio_LB"].get("median"), runs["BL5"]["ratio_LB"].get("median")
    meds = {t: e["ratio_LB"].get("median") for t, e in runs.items()}
    known = [v for v in meds.values() if v is not None]
    e10 = {"status": "informative", "claim": CHECK_CLAIMS["E7-10"], "sublet_ratio_LB_median": s_med,
           "bl5_ratio_LB_median": b_med}
    put(e10, "sublet_over_bl5", None if s_med is None or not b_med else s_med / b_med,
        "no ratio_LB median for Sublet or BL5")
    e10["ratio_LB_median"] = meds
    put(e10, "ratio_LB_median_range", [min(known), max(known)] if known else None, "no run with a lower bound")
    e10["label"] = "upper bound on ALG / OPT(sigma, omega) against a merged LP bound (Propositions M4, M6; M39)"
    ch["E7-10"] = e10
    ch["E7-11"] = {"status": "informative", "claim": CHECK_CLAIMS["E7-11"],
                   "by_grid": abort_table({f"gap:{t}": by_tag.get(t, []) for t in A8_TAGS})}
    checks = {k: {**ch[k], "part": "gap"} for k in PART_CHECKS["gap"]}
    summ = {"meta": meta, "lp": lp_meta, "runs": runs, "bl0a_by_alignment": bl0a_all_c,
            "certificates": _certs_block(all_rows), "checks": checks}
    mc.dump_json(summ, out_g / "summary.json")
    blocks = [("Reduced run", meta["reduced_note"])] if d["reduced"] else []
    blocks += [("Merged LP bounds (§3.8)", mc.md_table(["c", "status", "objective", "n_vars", "nnz", "solve s"],
                                                       [[c, x.get("status"), x.get("objective"),
                                                         (x.get("size") or {}).get("n_vars"),
                                                         (x.get("size") or {}).get("nnz"), x.get("solve_s")]
                                                        for c, x in lp_meta.items()])),
               ("ALG / LB of the gap reruns (an upper bound on the gap; merged bound)",
                mc.md_table(["tag", "runs", "with LB", "median", "ci lo", "ci hi", "P1 flags"],
                            [[t, e["n_runs"], e["n_ratio"], e["ratio_LB"].get("median"), _ci(e["ratio_LB"])[0],
                              _ci(e["ratio_LB"])[1], len(e["p1_flags"])] for t, e in runs.items()])),
               ("Checks (§3.11)", _checks_table(checks))]
    _write_tables(out_g / "tables.md", "E7: gap reruns (design/sim_spec_ms4.md §3.7(e), §3.8)", blocks)
    return summ


def check_gap(rows: list, lps: dict, alignments) -> dict:
    """E7-3 (§3.11) over the gap reruns and BL0a's runs."""
    bad_rv = [_label(r) for r in rows if r.get("ratio_validity") is not None]
    no_lp, bad_lp, bad_hash = [], [], []
    for r in rows:
        lp = lps.get(int(r["c"]))
        if lp is None:
            no_lp.append(_label(r))
            continue
        if lp.get("status") != 0 or lp.get("grid") != GAP_GRID:
            bad_lp.append({**_label(r), "lp_status": lp.get("status"), "grid": lp.get("grid")})
        hashes = r.get("schedule_hashes") or [r.get("schedule_hash")]
        if lp.get("instance_hash") != r.get("instance_hash") or any(h != lp.get("schedule_hash") for h in hashes):
            bad_hash.append(_label(r))
    sched: dict = {}
    for r in rows:
        for h in (r.get("schedule_hashes") or [r.get("schedule_hash")]):
            sched.setdefault(num_key(r["c"]), set()).add(h)
    multi = {c: sorted(str(x)[:16] for x in v) for c, v in sched.items() if len(v) > 1}
    p1 = [r for r in rows if r.get("tag") != "BL2" and r.get("plan_class_p1") and r["lb"].get("ratio_LB") is not None]
    below = [{**_label(r), "tag": r["tag"], "ratio_LB": r["lb"]["ratio_LB"]} for r in p1
             if r["lb"]["ratio_LB"] < 1.0 - P1_TOL]
    fail = bool(bad_rv or bad_lp or bad_hash or multi or below)
    st = "fail" if fail else ("missing" if (not rows or no_lp) else "pass")
    return {"status": st, "claim": CHECK_CLAIMS["E7-3"], "n_runs": len(rows),
            "lp_alignments": sorted(int(c) for c in lps), "alignments": list(alignments),
            "ratio_validity_not_none": bad_rv[:50], "runs_without_lp": no_lp[:50], "n_runs_without_lp": len(no_lp),
            "lp_not_optimal": bad_lp[:50], "hash_mismatch": bad_hash[:50], "alignments_with_several_schedules": multi,
            "n_p1": len(p1), "p1_below": below[:50], "min_ratio_LB_p1": min((r["lb"]["ratio_LB"] for r in p1),
                                                                            default=None),
            "bl2_exempt": True, "tolerance": P1_TOL}


# ---------------------------------------------------------------- summary: part allow
def allow_cell(rows: list, note: str = "no run of this cell in the outputs") -> dict:
    """cells.<b0>.<mode> of allow/summary.json (§3.10; module docstring)."""
    by = {str(int(r["policy_seed"])): r for r in sorted(rows, key=lambda r: int(r["policy_seed"]))}
    acc = {s: r.get("accountings") or {} for s, r in by.items()}
    a8 = {s: r["a8"] for s, r in by.items()}
    e = {"n_runs": len(rows)}
    if not rows:
        e["note"] = note
    first = next(iter(a8.values()), {})
    for k in ("B0_rule", "B0_usd", "kappa", "gamma"):
        if rows:
            e[k] = first.get(k)
        else:
            put(e, k, None, note)
    if rows and e["kappa"] is None:
        e["kappa_note"] = KAPPA_NONE_NOTE
    # both accountings (§2.6): cost_over_bl0a is overflow_over_bl0a (the name sf_e7_allow reads, §8.2); the other
    # ratios as aggregates over the seeds with by_seed, the USD values by seed, and every field per seed
    r0 = {s: a.get("overflow_over_bl0a") for s, a in acc.items()}
    e["cost_over_bl0a"] = {**_agg(r0.values(), note), "by_seed": r0}
    for k in ("total_over_bl0a", "own_share_of_total", "overflow_over_bl0b", "total_over_bl0b"):
        v = {s: a.get(k) for s, a in acc.items()}
        e[k] = {**_agg(v.values(), note if not rows else f"{k} unavailable"), "by_seed": v}
    e["overflow_usd"] = {s: a.get("overflow_usd") for s, a in acc.items()}
    e["total_usd"] = {s: a.get("total_usd") for s, a in acc.items()}
    e["accountings"] = acc
    e["t_a"] = {s: x.get("t_a") for s, x in a8.items()}
    e["case"] = {s: x.get("certificate_case") for s, x in a8.items()}
    e["held"] = {s: (x.get("certificate") or {}).get("held") for s, x in a8.items()}
    e["aborted"] = {s: bool(x.get("aborted")) for s, x in a8.items()}
    put(e, "abort_share", _mean([float(v) for v in e["aborted"].values()]), note)
    e["certificates"] = m4.count_certificates(list(a8.values()))
    return e


def _ok_file(folder: Path, part: str, jid: str) -> Optional[dict]:
    rec = mc.read_record(folder, jid)
    if rec is None or rec.get("status") != "ok":
        return None
    return mc.read_json(run_path(folder, part, jid))


def summary_allow(out_a: Path) -> dict:
    out_a = Path(out_a)
    d = design()
    js = [j for j in jobs_all() if j.params["part"] == "allow"]
    files, ok, ignored = _part_outputs(out_a, js, "allow")
    root = e7_root(out_a)
    cells, w0 = {}, {}
    for b0 in ALLOW_B0:
        k = b0_key(b0)
        for mode in allow_modes():
            cells.setdefault(k, {})[mode] = allow_cell([r for r in _rows(files, mode=mode) if b0_key(r["b0"]) == k])
        r0 = {m: {s: v for s, v in cells[k][m]["cost_over_bl0a"]["by_seed"].items() if v is not None}
              for m in stress_modes() if cells[k][m]["n_runs"]}
        w0[k] = w0_of(r0)
    all_rows = _rows(files)
    refs = _refs_by_alignment(files)
    ref1 = refs.get(num_key(STRESS_C)) or {}
    autos = [r["a8"].get("B0_report_usd") for r in all_rows if r.get("b0") == "auto" and r.get("a8")]
    cmin = sorted({f.get("c_min_sum_usd") for f in files.values() if f.get("c_min_sum_usd") is not None})
    meta = _meta("allow", d, js, ok, ignored, alignment=STRESS_C, mu=MU_MAIN, references=ref1 or None,
                 allowances=[b0_key(b) for b in ALLOW_B0], modes=list(allow_modes()), gamma=m4.GAMMA)
    put(meta, "bl0a_usd", ref1.get("bl0a_usd"), "no run file of alignment 1")
    put(meta, "b0_auto_usd", autos[0] if autos else None, "no run at the theory point (B0 'auto')")
    meta["b0_auto_values"] = sorted({float(x) for x in autos if x is not None})
    put(meta, "c_min_sum_usd", cmin[0] if cmin else None, "no run file")
    put(meta, "kappa10_cap_usd", 10.0 * cmin[0] if cmin else None, "no run file")
    meta["kappa10_cap_note"] = ("10 sum_j C^min_j (guard.c_min of the instance's public view), the cap of Algorithm "
                                "1's allowance min{B0, kappa B_on(t)} at kappa 10 (§3.2)")
    # BL5 from part main's runs (mu = 1, alignment 1) and part stress's W0
    main_dir, stress_dir = root / "main", root / "stress"
    bl5f = _ok_file(main_dir, "main", main_id("BL5", MU_MAIN, STRESS_C))
    bl5_r0 = [r["accountings"]["overflow_over_bl0a"] for r in (bl5f or {}).get("runs", [])]
    bl5_agg = _agg(bl5_r0, f"no 'ok' output of {main_id('BL5', MU_MAIN, STRESS_C)} under {main_dir}")
    st, st_why, ign = part_summary(root, "stress")     # used only with an 'ok' e7:summary record (§2.6)
    if ign:
        ignored.append(ign)
    w_bl5 = ((st or {}).get("W0") or {}).get("BL5")
    bl5 = {"sources": {"L-tr": f"main/runs: {main_id('BL5', MU_MAIN, STRESS_C)}", "W0": "stress/summary.json W0.BL5"},
           "L-tr_aggregate": bl5_agg, "W0_detail": w_bl5}
    put(bl5, "L-tr", bl5_agg.get("median"), bl5_agg.get("median_note"))
    put(bl5, "W0", (w_bl5 or {}).get("value"), (st_why or "stress/summary.json has no W0.BL5 value") if not w_bl5
        else (w_bl5.get("value_note") or "W0 of BL5 is null"))
    ch = {"E7-1": check_certificates(all_rows), "E7-2": check_clean(all_rows),
          "E7-4": check_accounting(all_rows, refs), "E7-6": check_allowance(all_rows, sweep=True)}
    ch["E7-7"] = check_reproduction(files, main_dir, stress_dir)
    groups = {f"b0={b0_key(b)}:mode={m}": [r for r in _rows(files, mode=m) if b0_key(r["b0"]) == b0_key(b)]
              for b in ALLOW_B0 for m in allow_modes()}
    theory = [r["a8"] for r in all_rows if r.get("b0") == "auto" and r.get("a8")]
    early = [x for x in theory if x.get("aborted") and x.get("t_a") is not None and int(x["t_a"]) <= 1]
    ch["E7-11"] = {"status": "informative", "claim": CHECK_CLAIMS["E7-11"], "by_grid": abort_table(groups),
                   "theory_default": {"n_runs": len(theory), "n_abort_at_slot_1_or_earlier": len(early),
                                      "share_abort_at_slot_1_or_earlier": len(early) / len(theory) if theory else None}}
    checks = {k: {**ch[k], "part": "allow"} for k in PART_CHECKS["allow"]}
    summ = {"meta": meta, "cells": cells, "W0": w0, "bl5": bl5, "certificates": _certs_block(all_rows),
            "checks": checks}
    mc.dump_json(summ, out_a / "summary.json")
    rows = [[b, m, e["n_runs"], e["cost_over_bl0a"].get("median"), e.get("abort_share")]
            for b, by in cells.items() for m, e in by.items()]
    blocks = [("Reduced run", meta["reduced_note"])] if d["reduced"] else []
    blocks += [("Sublet's week cost / BL0a per allowance and lender mode (median over the seeds, alignment 1)",
                mc.md_table(["B0", "mode", "runs", "cost / BL0a", "abort share"], rows)),
               ("W0 per allowance", mc.md_table(["B0", "W0", "mode"], [[b, w.get("value"), w.get("mode")]
                                                                       for b, w in w0.items()])),
               ("Checks (§3.11)", _checks_table(checks))]
    _write_tables(out_a / "tables.md", "E7: allowance sweep (design/sim_spec_ms4.md §3.7(f))", blocks)
    return summ


def check_reproduction(files: dict, main_dir: Path, stress_dir: Path) -> dict:
    """E7-7: the sweep's runs at B0 = B0_SHARE x BL0a against part main's Sublet runs at mu = 1, alignment 1 (L-tr)
    and part stress's Sublet runs, seed by seed (totals to 1e-9 USD)."""
    k_rule = b0_key(m4.B0_SHARE)
    pairs, missing = [], []
    for mode in allow_modes():
        f = files.get(allow_id(m4.B0_SHARE, mode))
        ref = (_ok_file(main_dir, "main", main_id("Sublet", MU_MAIN, STRESS_C)) if mode == "L-tr"
               else _ok_file(stress_dir, "stress", stress_id(mode, "Sublet")))
        mine = {int(r["policy_seed"]): r["ALG"] for r in (f or {}).get("runs", [])}
        theirs = {int(r["policy_seed"]): r["ALG"] for r in (ref or {}).get("runs", [])}
        for s in sorted(set(mine) | set(theirs)):
            if s in mine and s in theirs:
                pairs.append({"mode": mode, "seed": s, "allow": mine[s], "reference": theirs[s],
                              "abs_diff": abs(mine[s] - theirs[s])})
            else:
                missing.append({"mode": mode, "seed": s, "in_allow": s in mine, "in_reference": s in theirs})
        if not mine or not theirs:
            missing.append({"mode": mode, "allow_file": f is not None, "reference_file": ref is not None})
    bad = [p for p in pairs if p["abs_diff"] > REL_TOL]
    st = "fail" if bad else ("pass" if pairs and not missing else "missing")
    return {"status": st, "claim": CHECK_CLAIMS["E7-7"], "b0": k_rule, "n_pairs": len(pairs), "pairs": pairs,
            "failures": bad, "missing": missing, "tolerance_usd": REL_TOL}


# ---------------------------------------------------------------- table3.json (§3.10, §9)
def _cell(agg: Optional[dict], note: Optional[str] = None) -> dict:
    """A Table III cell {median, interval, n, note} from an aggregate (median, median_ci95, n)."""
    if not isinstance(agg, dict) or agg.get("median") is None:
        # a null cell carries the reason it is null (the aggregate's note) before the caller's description
        return {"median": None, "interval": [None, None], "n": int((agg or {}).get("n") or 0),
                "note": (agg or {}).get("median_note") or note or "no value"}
    return {"median": agg["median"], "interval": list(agg.get("median_ci95") or [None, None]),
            "n": int(agg.get("n") or 0), "note": note}


def _null_cell(note: str) -> dict:
    return {"median": None, "interval": [None, None], "n": 0, "note": note}


def _labels() -> dict:
    """style.POLICIES labels of the style keys (the figure package, imported when needed)."""
    import importlib
    if str(paths.SIM) not in sys.path:
        sys.path.insert(0, str(paths.SIM))
    style = importlib.import_module("figs.style")
    keys = [v["style"] for v in TAGS.values()] + list(REF_STYLE.values())
    return {k: style.POLICIES[k].label for k in keys}


def _sha256(p: Path) -> Optional[str]:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def table3(root: Path, main: dict, others: dict, why: Optional[dict] = None) -> dict:
    """code/sim/out/e7/table3.json (§3.10, §9) from the four part summaries (main's in memory and on disk); written
    last by main's summary. A missing summary, or one not used (`why`: its e7:summary record is not 'ok',
    part_summary), leaves its cells null with notes (§2.6)."""
    root = Path(root)
    why = why or {}
    labels = _labels()
    mu1 = main["runs"][num_key(MU_MAIN)]
    gap, stress = others.get("gap") or {}, others.get("stress") or {}
    meta_m = main["meta"]
    rows = {}
    for tag in TAGS:
        e = mu1[tag]
        g = ((gap.get("runs") or {}).get(tag) or {}).get("ratio_LB") if gap else None
        w = (stress.get("W0") or {}).get(tag) if stress else None
        rows[tag] = {"label": labels[TAGS[tag]["style"]], "style_key": TAGS[tag]["style"],
                     "usd": {"overflow": _cell(e["overflow_usd"]), "total": _cell(e["total_usd"])},
                     "saving_pct": _cell(e["saving_pct"]),
                     "gap": _cell(g, None if g else (why.get("gap") or "gap/summary.json missing")),
                     "fallback_share_after_reclaims": _cell(e["fallback_share_after_reclaims"]),
                     "W0": ({"median": w["value"], "interval": list(w.get("seed_range") or [None, None]),
                             "n": int(((w.get("per_mode") or {}).get(w.get("mode")) or {}).get("n_runs") or 0),
                             "note": f"the largest 3-seed mean of r0 over the five stress modes (mode {w.get('mode')});"
                                     " interval: the range of r0 over that mode's seeds (one cell, no bootstrap)"}
                            if w and w.get("value") is not None else
                            _null_cell((w or {}).get("value_note") or why.get("stress")
                                       or "stress/summary.json missing")),
                     "abort_share": ({"median": e["abort_share"], "interval": [None, None], "n": e["n_runs"],
                                      "note": "share of the trace week runs at mu = 1 with an abort (M24)"}
                                     if is_a8(tag) and e.get("abort_share") is not None else
                                     _null_cell(e.get("abort_share_note") or "unguarded policy"))}
    # the references, analytic per alignment (median over the alignments)
    bl0a = [v for v in (meta_m.get("bl0a_usd") or {}).values() if v is not None]
    own = [v for v in (meta_m.get("own_capacity_usd") or {}).values() if v is not None]
    refs = meta_m.get("references") or {}
    b0b_o = [r["bl0b_overflow_usd"] for r in refs.values() if r.get("bl0b_overflow_usd") is not None]
    b0b_t = [r["bl0b_total_usd"] for r in refs.values() if r.get("bl0b_total_usd") is not None]
    b0a_t = [r["bl0a_total_usd"] for r in refs.values() if r.get("bl0a_total_usd") is not None]
    sav_b = [100.0 * (1.0 - r["bl0b_overflow_usd"] / r["bl0a_usd"]) for r in refs.values()
             if r.get("bl0b_overflow_usd") is not None and r.get("bl0a_usd")]
    g0 = ((gap.get("runs") or {}).get("BL0a") or {}).get("ratio_LB") if gap else None
    an = "analytic, median over the alignments"
    rows["BL0b"] = {"label": labels["bl0b"], "style_key": "bl0b",
                    "usd": {"overflow": _cell(_agg(b0b_o, "no alignment"), an),
                            "total": _cell(_agg(b0b_t, "no alignment"), an)},
                    "saving_pct": _cell(_agg(sav_b, "no alignment"), an),
                    "gap": _null_cell("analytic: no engine run, no gap (M23)"),
                    "fallback_share_after_reclaims": _null_cell("no leases"),
                    "W0": _null_cell("analytic reference: no stress run"), "abort_share": _null_cell("not guarded")}
    rows["BL0a"] = {"label": labels["bl0a"], "style_key": "bl0a",
                    "usd": {"overflow": _cell(_agg(bl0a, "no alignment"), an),
                            "total": _cell(_agg(b0a_t, "no alignment"), an)},
                    "saving_pct": _cell(_agg([0.0] * len(bl0a), "no alignment"), "0 by definition"),
                    "gap": _cell(g0, None if g0 else (why.get("gap") or "gap/summary.json missing")),
                    "fallback_share_after_reclaims": _null_cell("no leases"),
                    "W0": {"median": 1.0, "interval": [1.0, 1.0], "n": 0, "note": "1 by definition"},
                    "abort_share": _null_cell("not guarded")}
    certs = {"n": 0, "held": 0, "failures": 0, "by_case": {c: {"runs": 0, "held": 0} for c in m4.CASES}, "w_c_runs": []}
    parts_found = {}
    for p in PARTS:
        s = main if p == "main" else others.get(p)
        cb = (s or {}).get("certificates")
        parts_found[p] = cb is not None
        if not cb:
            continue
        for k in ("n", "held", "failures"):
            certs[k] += int(cb.get(k) or 0)
        for c in m4.CASES:
            for k in ("runs", "held"):
                certs["by_case"][c][k] += int(((cb.get("by_case") or {}).get(c) or {}).get(k) or 0)
        certs["w_c_runs"] += [{**x, "part": p} for x in cb.get("w_c_runs") or []]
    certs["parts_counted"] = parts_found
    sources = {}
    for p in PARTS:
        f = root / p / "summary.json"
        s = main if p == "main" else others.get(p)
        sources[p] = {"file": f"code/sim/out/e7/{p}/summary.json", "exists": f.is_file(), "sha256": _sha256(f),
                      "used": s is not None, "git_revision": ((s or {}).get("meta") or {}).get("git_revision"),
                      "reduced": ((s or {}).get("meta") or {}).get("reduced")}
        if s is None:
            sources[p]["used_note"] = why.get(p) or f"{p}/summary.json missing"
    own_by = {c: v for c, v in (meta_m.get("own_capacity_usd") or {}).items()}
    t3 = {"meta": {"exp": EXP, "spec": "design/sim_spec_ms4.md §3.10, §9", "git_revision": mc.git_revision(),
                   "written": mc._now(), "reduced": bool(meta_m.get("reduced")) or any(
                       x.get("reduced") for x in sources.values()), "sources": sources},
          "order": list(TABLE3_ROWS),
          "columns": {"usd": "USD per week, overflow (total) accounting, median; main grid, mu / beta~ = 1 (M2)",
                      "saving_pct": "100 (1 - cost / BL0a) %, overflow accounting, median",
                      "gap": "ALG / merged LP bound, slow grid, e7r menu with s5_tau5_H5, one day: median over the 12 "
                             "gap reruns (4 for BL0a), an upper bound on the ratio to OPT(sigma, omega) (Proposition "
                             "M4) against a merged bound (Proposition M6) (M39)",
                      "fallback_share_after_reclaims": "median over the main-grid runs where it is defined",
                      "W0": "the worst cost over BL0a under the five stress modes (note §5.5), overflow accounting",
                      "abort_share": "aborted runs of the 12 trace week runs at mu / beta~ = 1 (M24)"},
          "rows": {t: rows[t] for t in TABLE3_ROWS},
          "labels": {t: rows[t]["label"] for t in TABLE3_ROWS},
          "caption": {"certificates": certs, "B0_rule": m4.B0_RULE, "gamma": m4.GAMMA, "kappa": None,
                      "kappa_note": KAPPA_NONE_NOTE, "info_class_reported": m4.INFO_CLASS_REPORTED,
                      "own_capacity_usd": {"by_alignment": own_by, "median": float(np.median(own)) if own else None},
                      "scope": {"horizon_min": main["meta"]["grids"]["horizon_min"], "menu": "full (a11_default)",
                                "lender": "trace", "mu_over_beta_tilde": MU_MAIN,
                                "alignments": main["meta"]["grids"]["alignments"],
                                "policy_seeds": main["meta"]["grids"]["policy_seeds"]}}}
    if not own:
        t3["caption"]["own_capacity_usd"]["median_note"] = "no alignment with own capacity"
    mc.dump_json(t3, root / "table3.json")
    return t3


# ---------------------------------------------------------------- summary dispatch and command line
SUMMARIES = {"main": summary_main, "stress": summary_stress, "gap": summary_gap, "allow": summary_allow}


def summary(out) -> dict:
    """The summaries of the parts of E7_PART in pass-2 order (gap, stress, allow, main)."""
    ps = parts()
    return {p: SUMMARIES[p](part_dir(out, p)) for p in PASS_SUMMARIES if p in ps}


def main(argv=None) -> int:
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=argv, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
