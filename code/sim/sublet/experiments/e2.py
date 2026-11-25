"""E2: the value and price of notice (design/sim_spec_ms3.md §6; deliverable D25; open choices M16-M25, M46-M48,
M50, with M19's four time alignments).

Setting (§6.2). Tier M, the 20 MaaS clusters and the four spot pools of a11_calibration.json (`inputs.maas_lenders`,
`inputs.spot_L7_lenders`), one revocable contract s5_tau5_H<H> (tau one 5-min slot, M16) at its IR price plus
`protected`, H in `inputs.H_menu_min`, load scenario a5_2GBps at the lender's and the protected site (M17), mu /
beta~_ref in `inputs.mu_over_beta_tilde`, schedules `trace` and `eager`. A cell (lender, H) runs iff the contract is
offered and alpha_k < 1 (MS2 spec M59): the rows of code/sim/out/ms2_checks/e2_reactions.json with contract
s5_tau5_H* and a kind other than 'alpha>=1'. Time alignments (config seeds, M19): c in {1, 2, 3, 4} at mu / beta~ = 1
under `trace`, c = 1 at the other mu values and under `eager`.

Instances (§6.3). The base instance of (lender, series, H, mu, c) is configs/ms2_single_site.json with one week of
1-min routing, seed c, the cell's two contracts, lender 0 a trace lender with 8 offered layers of 8 GPUs and the
series borrower b0 (series azure2024_code, azure2024_conv, burstgpt_1, burstgpt_2, burstgpt_3). `layers_of` rescales
the client's overflow x so that its P99.5 spans K = 8 layers of one replica load (M18, a7's construction); demand
layer k is on in fast slot f iff x'(f) >= k and is paired with band k, the layer site with local_layer_lo = k.
`single_band(inst, k)` gives layer k as the one client's demand with every site but band k and the protected site
masked (delta = INF); a band-less layer (the lender offers fewer than k layers) has every layer site masked (M48).
`episode_instance(inst_k, band, R_band, f_a, f_b)` is one on-period [f_a, f_b) of a layer (M21): the horizon cut to
the on-period plus ceil(D_k / 5) + 1 slow slots, demand 1 on the on-period only, every layer site synthetic (band k
with R = [r*, T_e) from the band's first announcement r* at or after the episode's first slow slot in the week's
realized trace schedule, the masked bands with R empty) and the lender's trace replaced by a synthetic one; it runs
under LenderModel(schedule='trace', on_unavailable='refuse'): one on-period, one supply window, C2's setting.

Rules (§6.4; rule keys a1, cold, prewarm, bl6, bl0a): A1 {site_rev: band, site_prot: protected} (ALG*, the design
default), A1 with reaction 'cold' ("always cold"), A1 with reaction 'prewarm_if_feasible' ("pre-warm if H >= lambda"),
BL6 around that A1 (notice-oblivious) and the analytic all-fallback cost q_j x demand (BL0a, M47). Which rules run
(Q42 (a), M22): at mu = 1 every policy rule on every cell under both schedules (BL6 only at H > 0: at H = 0 it equals
A1); at mu != 1 under `trace` A1, the fixed rule whose reaction differs from A1's resolved reaction (none where A1
insures) and BL6 (H > 0); under `eager` A1 and BL6 (H > 0). A rule that is not run because it coincides with A1 (A1
insures, or A1's resolved reaction is the rule's, or BL6 at H = 0) is recorded as {"same_as": "a1", "why": ...} and
takes A1's values in the summary; a rule not run under `eager` at mu != 1 has no value there. The rules are decided
per layer from A1's own report (insured, reaction). Every engine run has check_invariants = True.

Benchmarks (§6.5). Per (cell, series, layer, schedule) the single-site DP opt.dp.solve_dp(inst_k, A1's realized
schedule, grid 'fast'); a band-less layer: the protected-only DP on its instance's static schedule; per episode
solve_dp(e, its realized schedule, grid 'fast', refuse_unavailable=True). A DP that raises DomainError is recorded
and its layer or episode excluded, with the count. E2-6 (M46): on 1-day instances (slow slots 0-287) the joint
optimum opt.milp.solve_opt (grid 'fast', HiGHS limit ms3_common.milp_limit_s()) of one client whose demand is the sum
of the 8 layers against the sum of the layers' DPs.

The exact C2 game on a finer H grid (§6.6): det_game.solve_det (switch cost beta~) and model_switch_cost.solve_det_bw
(C2-SW, b_w = inputs.bw_default) with por_default.py's Part A settings (dt 0.05, T = Hs + 13, Rmax = Hs + 6, beta_s =
1.65 (1 - alpha)), every input read from code/theory_checks/c2/out/por_default.json; grid points round(i / 20, 12) and
round(i / 10, 12). Minutes: H_min = (Hs / beta_s) lambda_s (alpha + phi) / 60 with lambda_s the a5_2GBps load time of
tier M (a11 load_time_s.maas_a10.M.a5_2GBps).

Status labels (copied from design/sim_spec_ms3.md §6.1, never upgraded): C2-T4 PROVEN under (C'), tau = 0, switch cost
beta, site-window semantics; C2-Cor5 PROVEN under (C) with the proviso of C2-Cor5(3); the threshold form at
mu / beta~ = 1 at the default switch cost VERIFIED NUMERICALLY (c2/audit/out/model_switch_cost_default.txt); every
per-lender H*_mu at a lender's IR price is the C2-SW formula, CONJECTURE; C2-P8 lower bound PROVEN, table values
interval-certified, equality VERIFIED NUMERICALLY at alpha = 0.3, CONJECTURE in general; C3-P6 PROVEN; the DP equals
OPT on its domain (Claim D2) CONJECTURE. Trace episodes leave C2's core, so per-episode ratios are diagnostics.

Command line (ms3_common.main, §2.4), run from code/sim:
  python -m sublet.experiments.e2 --list | --job ID | --summary | --estimate | --manifest  [--out DIR]
Jobs (lender ids are written with '.' for ':' in job ids, e.g. a2.c05, a1.A100-SXM4-80GB, since ':' separates the
parts of an id):
  e2:cell:lender=<L>:H=<H>:mu=<U>:c=<C>     pool  one (cell, mu, alignment): 5 series x 8 layers under the schedules
                                                  of the alignment, the rules, the week DPs and, under `trace`, every
                                                  episode of every layer with a band (§6.8)
  e2:game:switch=<beta|c2sw>:mu=<U>:lam=<0|0.715>  alone  the C2 game cells of §6.6 for one (switch, mu, lambda),
                                                  computed by an internal pool of N processes, N = the number of
                                                  slotK lock files the job holds (MS3_SLOTS; 1 without it)
  e2:joint:lender=<L>:series=<S>:H=<H>      milp  E2-6 (M46): one 1-day joint MILP with its LP, at mu = 1, c = 1
  e2:ep_milp:i=<i>                          milp  E2-5: the i-th episode (sorted by job id, series, layer, f_a) whose
                                                  per-episode ratio is below 1 - 1e-9 in some rule, solved by
                                                  opt.milp.solve_opt (grid 'fast', refuse_unavailable); a no-op when
                                                  there is no i-th such episode (8 jobs, run after the pool jobs)
--estimate uses the time constants of §11.1: 505 s per cell job at mu != 1, 740 s at mu = 1 and c = 1, 410 s at mu = 1
and c > 1 (§6.8); 20 s per C2 game cell, summed over the job's cells (single-worker time; the job runs them on its
slots); 360 s per joint MILP (the hard limit LIMIT + 60 s); the E2-5 jobs have no constant (seconds when no episode
qualifies, at most LIMIT + 60 s).

Reduced runs (smoke tests): MS3_E2_REDUCED=1 in the environment (run_e2.sh --reduced sets it) selects the lenders
a1:A100-SXM4-80GB, a1:A800-SXM4-80GB, a2:c00, a2:c05, H in {0, 2, 60}, alignments {1, 2} at mu = 1, the series
azure2024_conv, a one-day horizon, the C2 game at the H_BASE points of the main job and Hs in {0, 1} elsewhere, one
joint MILP (a2:c05, azure2024_conv, H = 60) and one E2-5 job; default (unset or 0): the full lists above.

Outputs (code/sim/out/e2/, §6.8): runs/cells/<job>.json (per cell job: every run's totals and components, A1's
report fields insured, reaction and counts, every DP value and status, the band-less layers, the per-episode columns
{layer, f_a, f_b, window_end, opt, opt_status, bl0a, alg.<rule>}), runs/game/, runs/joint/ (with the pre-MILP records
*.lp.json), runs/ep_milp/ (not versioned); jobs/, logs/,
manifest.json, run_e2.log (versioned); game.json, joint_milp.json, summary.json, tables.md (versioned, written by
--summary). Numeric keys as §2.4 (num_key: "0.2", "1", "60"); missing values are null with a "*_note" key (§2.6).

summary.json (every key path; <group> in {maas, spot, <pool id>, maas_q1 .. maas_q4}, <H> the minutes of the H grid,
<mu> the mu / beta~_ref values, <sched> in {trace, eager}, <rule> in {a1, cold, prewarm, bl6, bl0a}, <c> the
alignment):
  meta                     exp, spec, git_revision, written, reduced, settings (H grid, mu grid, series, alignments,
                           horizon), cells [[lender, H]], cells_without_sites [[lender, H]] (offered with
                           alpha_k < 1, but no layer site in the builder; no job) and its note, groups {group:
                           [lenders]}, maas_quartiles {maas_q<i>: [lenders]} (M50: by the median alpha_k over the H
                           grid, ascending), spot_pools_by_H
                           {<H>: [pools with an A1 cell]}, status_labels, sources, jobs_ok, jobs_missing
  episodes.<group>.<H>.<mu>.<rule>     per-episode ALG_e / OPT_e under `trace` over every episode of the group's
                           layers with a band (pooled over lenders, series, layers and, at mu = 1, the four alignments):
                           median, median_ci95, p95, p95_ci95 (95% percentile bootstrap, B = 2000, seed 0, the draws of
                           metrics.aggregate), max, n, n_alignments, alignments, n_lenders, ran (false where the rule
                           takes A1's values everywhere), by_alignment.<c> (the same fields per alignment); every field
                           null with `note` where no value exists (spot: fewer than two pools with data, M23)
  totals.<group>.<H>.<mu>.<sched>.<rule>  over the group's (lender, series) pairs (at mu = 1 under `trace` the (lender,
                           series, alignment) triples): cost_over_bl0a (sum of ALG over the 8 layers / sum of BL0a),
                           whole_trace_ratio (sum of ALG / sum of DP over the layers with a band whose DP solved),
                           cost_per_demand_h (USD per replica-load-hour), each {median, median_ci95, p95, max, n}
                           (metrics.aggregate);
                           components and components_over_bl0a (median over the pairs of each ledger component summed
                           over the 8 layers: lease_prepaid, lease_rent, lease, loading, routing, fallback, stranding,
                           stranding_fb, total; a band-less layer counts its fallback cost), n_pairs, n_alignments,
                           alignments, by_alignment.<c> (the same fields per alignment); where no value exists (spot:
                           fewer than two pools with data, M23) the entry has `note`, n_pairs 0 and every field null
                           with its '*_note'
  best_H.<group>.<mu>.<sched>.<rule>   the H with the smallest median cost_over_bl0a: H, H_min (both minutes),
                           cost_over_bl0a, median_ci95
  coincide.<group>.<H>.<mu>            true iff the pre-warm rule's values (week totals of every layer and every
                           per-episode value, `trace`) equal A1's to 1e-9 relative in every cell and alignment of the
                           group (null with a note where nothing is compared); the figure draws `prewarm` where false
  cold_equals_a1.<group>.<H>.<mu>      the same for the "always cold" rule
  coincide_detail.<group>.<H>.<mu>     {prewarm, cold}: n_compared, n_differ, ran_in (cells where the rule was run)
  bandless.<lender>.<H>.<c>            band-less layers summed over the series (from the mu = 1 job of the alignment):
                           layers, sum_dp, sum_fallback, dp_status_ok
  checks.<id>              one entry per check of §6.9, keyed by its id (E2-1 ... E2-7, E2-3b), each with `status`
                           (the vocabulary of the E1 and E10 summaries: 'pass', 'fail', 'missing' (no input to check),
                           'pending' (E2-5: an episode below the threshold whose MILP job has not run, or ran on a
                           stale candidate list), 'explained' (E2-5: every such episode a confirmed counterexample to
                           Claim D2), 'informative') and `claim` (the content of §6.9 with its status labels):
  checks.E2-1              rows (Hs, CR, CR_ref, diff), max_abs_diff, missing_Hs, tolerance, pass (|diff| <= 1e-12 at
                           mu = 1, lambda = inputs.lambda_default, Hs = H_BASE), file
  checks.E2-2              (a) n_rows, mismatches [{lender, H, mu, field, recomputed, row}], n_rows_alpha_kind,
                           alpha_kind_mismatches [{lender, H, mu, kind, alpha_k}] (every s5_tau5_H* row: kind
                           'alpha>=1' iff alpha_k >= 1, §6.2), pass; (b) n_cells, differences [{lender, H, mu, field,
                           a1, row, rel}] above 1e-9 relative (informative); `status` is that of (a)
  checks.E2-3              at mu = 1, over the week runs and the episode runs: n_compared (n_compared_week,
                           n_compared_episodes), max_abs_diff_a1_cold (runs where A1 does not insure: every ledger
                           component of "always cold" against A1's), max_abs_diff_insured (cold and prewarm against
                           a1 where A1 insures), violations [...], pass (1e-9 USD)
  checks.E2-3b             n_bandless, max_dp_minus_fallback, violations, pass
  checks.E2-4              n_runs, n_invariant_failures, n_gpu_only_lease_slots, n_dp, n_dp_not_optimal,
                           n_dp_domain_error, examples, pass
  checks.E2-5              n_episodes, min_ratio, n_below, below [...] (up to 50), milp [the E2-5 MILP records:
                           episode, dp, incumbent, dual_bound, LB, alg, verdict], unresolved, n_candidates (the
                           episodes below ratio 1 - 1e-9 in the cell job records), ep_milp_stale (E2-5 jobs that ran
                           on another candidate list, with a note), pass
  checks.E2-6              rows of joint_milp.json (informative; a joint job stopped at the wall limit gives its LP as
                           LB, §2.5)
  checks.E2-7              per group: n_at_or_above_hstar, n_above_2_minus_alpha (A1, per-episode ratio above
                           2 - alpha_k at H >= H*_mu of the cell's e2_reactions row; informative, not a bug)
game.json: rows [{switch, mu, lam, lam_key, Hs, H_beta, H_min, CR, CR_react, CR_ins, PoR, plan_type, grids, seconds}]
  and meta (settings, inputs, git_revision, two_minus_alpha, minutes_per_beta_tilde, hstar.<mu>.<lam>: C2-T4's
  threshold with switch cost beta, c2rule.c2_thresholds(AL, AP, mu, lam, 1.0, None).Hstar, as {H_beta, Hs, H_min};
  jobs_missing; cells_failed {job: [Hs]}: cells whose solver raised, recorded in the job's errors and left out).
joint_milp.json: rows [{lender, series, H, mu, c, T_slow, sum_dp, dp_by_layer, lp, milp {status, objective,
  dual_bound, gap, ...}, LP, dual_bound, incumbent, gap, exact, LB, LB_source, lp_status, milp_status, grid,
  ratio_sum_dp_over_LB, ratio_sum_dp_over_incumbent, milp_limit_s, errors}]; a joint job whose record is wall_limit
  or oom_at_3G gives the row of its pre-MILP record runs/joint/<record name>.lp.json with LB = the LP and a note.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import copy
import dataclasses
import hashlib
import json
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

from .. import paths
from . import ms3_common as mc

EXP = "e2"
SPEC = "design/sim_spec_ms3.md §6"
CONFIG = "ms2_single_site.json"
REACTIONS = paths.SIM_OUT / "ms2_checks" / "e2_reactions.json"
A11_FILE = paths.ANALYSIS_OUT / "a11_calibration.json"
A12_FILE = paths.ANALYSIS_OUT / "a12_sim_inputs.json"
POR_FILE = paths.C2 / "out" / "por_default.json"

# §6.2-§6.3 parameters of the cells and instances
SERIES = ("azure2024_code", "azure2024_conv", "burstgpt_1", "burstgpt_2", "burstgpt_3")
TIER, REGION, LOAD_SCENARIO = "M", "europe", "a5_2GBps"
TAU_MIN = 5                     # M16: tau = one 5-min slot
PROTECTED = {"id": "protected", "tau_min": None, "H_min": 0, "prepaid_min": 5}
K_LAYERS, LAYER_GPUS, LEASE_QUANTILE = 8, 8, 25
LAYER_PERCENTILE = 99.5         # M18: the overflow's P99.5 spans the K layers (a7)
ALIGNMENTS = (1, 2, 3, 4)       # M19: config seeds at mu / beta~ = 1 under `trace`
HORIZON_MIN = 10080             # one week, also for the spot pools (M20)
DAY_MIN = 1440                  # E2-6's 1-day instances (M46)
POLICY_RULES = ("a1", "cold", "prewarm", "bl6")
RULES = POLICY_RULES + ("bl0a",)
SCHEDULES = ("trace", "eager")
REL_TOL = 1e-9                  # E2-3, E2-5, coincidences
E2_1_TOL = 1e-12
# summary checks.<id>.claim: the content of §6.9 with the status labels of §6.1 (copied, never upgraded)
CHECK_CLAIMS = {
    "E2-1": "the exact C2 game on the finer H grid (det_game.solve_det, switch cost beta~) reproduces por_default.json "
            "table_por_switch_beta at mu = 1, lambda = inputs.lambda_default, Hs in H_BASE (exact to 1e-12)",
    "E2-2": "(a) the cell kinds, A1's insurance decision and its reaction per mu, recomputed by c2rule at each "
            "e2_reactions.json row's units, equal the row's (exact); (b) A1's units of the run against the row's "
            "(informative)",
    "E2-3": "Q42 (a) at mu = 1 on every cell: A1 and 'always cold' give identical ledgers where A1 does not insure, "
            "all three rules where it insures (1e-9 USD)",
    "E2-3b": "band-less layers (M48): every band-less DP value at most the layer's fallback cost (1e-9 USD)",
    "E2-4": "every run: invariant_failures empty, gpu_only_lease_slots 0; every DP within its domain (status optimal)",
    "E2-5": "per-episode ratio at least 1 - 1e-9 (the DP is OPT on the episode's domain, Claim D2 CONJECTURE); below "
            "it a bug unless opt.milp.solve_opt returns an incumbent below the DP value (a counterexample to Claim "
            "D2: explained)",
    "E2-6": "the sum of the layers' DPs against the joint MILP's lower bound on 1-day instances (M46; whether the sum "
            "equals the joint optimum is open, MS1 spec §7.6; informative)",
    "E2-7": "per-episode ratios above 2 - alpha at H >= H*_mu are not bugs on trace episodes (C2-T4 PROVEN under "
            "(C'), tau = 0; the per-lender H*_mu is the C2-SW formula, CONJECTURE; informative)"}
N_EP_MILP = 8                   # E2-5 jobs
JOINT_KEYS = tuple((l, s, h) for l in ("a2:c05", "a1:A100-SXM4-80GB") for s in ("azure2024_conv", "burstgpt_1")
                   for h in (0, 60))   # §6.5 (M46): lenders, series, H at mu = 1, `trace`, alignment 1
# §11.1 time constants (estimates from MS3-spec measurements)
EST_CELL_S = {"mu_ne_1": 505.0, "mu1_c1": 740.0, "mu1_c_gt_1": 410.0}
EST_GAME_CELL_S = 20.0
EST_JOINT_S = 360.0
# reduced job lists for smoke tests (MS3_E2_REDUCED=1)
REDUCED = {"lenders": ("a1:A100-SXM4-80GB", "a1:A800-SXM4-80GB", "a2:c00", "a2:c05"), "H": (0, 2, 60),
           "alignments": (1, 2), "series": ("azure2024_conv",), "horizon_min": 1440, "game_supp": (0.0, 1.0),
           "joint": (("a2:c05", "azure2024_conv", 60),), "ep_milp": 1}
COMPONENT_KEYS = ("lease_prepaid", "lease_rent", "lease", "loading", "routing", "fallback", "stranding",
                  "stranding_fb", "total")
STATUS_LABELS = {
    "C2-T4": "PROVEN under (C'), tau = 0, switch cost beta, site-window semantics",
    "C2-Cor5": "PROVEN under (C) with the proviso of C2-Cor5(3)",
    "threshold form at mu/beta~ = 1, default switch cost": "VERIFIED NUMERICALLY "
                                                            "(c2/audit/out/model_switch_cost_default.txt)",
    "per-lender H*_mu at a lender's IR price (C2-SW formula)": "CONJECTURE (code/sim/out/ms2_checks/e2_reactions.json, "
                                                               "field status)",
    "C2-P8": "lower bound PROVEN, table values interval-certified, equality VERIFIED NUMERICALLY at alpha = 0.3, "
             "CONJECTURE in general",
    "C3-P6": "PROVEN (a remark)",
    "Claim D2 (single-site DP = OPT on its domain)": "CONJECTURE",
    "A1": "2 - alpha claimed only with the C2-T4 thresholds; no ratio claimed at the default switch cost (Q17)"}


# ---------------------------------------------------------------- inputs and settings
@lru_cache(maxsize=None)
def _json(path: str) -> dict:
    return json.loads(Path(path).read_text())


def a11() -> dict:
    return _json(str(A11_FILE))


def por() -> dict:
    return _json(str(POR_FILE))


def reactions() -> dict:
    return _json(str(REACTIONS))


def reduced() -> bool:
    return os.environ.get("MS3_E2_REDUCED", "0") == "1"


def _sha256(path) -> Optional[str]:
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def h_grid() -> tuple:
    return tuple(int(h) for h in a11()["inputs"]["H_menu_min"])


def mu_grid() -> tuple:
    return tuple(float(m) for m in a11()["inputs"]["mu_over_beta_tilde"])


def maas_lenders() -> tuple:
    return tuple(a11()["inputs"]["maas_lenders"])


def spot_pools() -> tuple:
    return tuple(a11()["inputs"]["spot_L7_lenders"])


def settings() -> dict:
    """The lists of this run (full, or reduced with MS3_E2_REDUCED=1)."""
    r = reduced()
    return {"reduced": r, "H": REDUCED["H"] if r else h_grid(), "mu": mu_grid(),
            "series": REDUCED["series"] if r else SERIES, "alignments": REDUCED["alignments"] if r else ALIGNMENTS,
            "horizon_min": REDUCED["horizon_min"] if r else HORIZON_MIN,
            "lenders": REDUCED["lenders"] if r else maas_lenders() + spot_pools()}


def num(x) -> str:
    """JSON / job-id key of a grid number (§2.4); lambda_default 0.7150000000000001 gives '0.715'."""
    return mc.num_key(x, strict=False)


def lender_key(lid: str) -> str:
    """A lender id inside a job id: ':' (the separator of job id parts) written as '.'."""
    return lid.replace(":", ".")


def lender_of_key(key: str) -> str:
    known = {lender_key(x): x for x in maas_lenders() + spot_pools()}
    if key not in known:
        raise ValueError(f"unknown lender key {key!r}")
    return known[key]


def group_of(lender: str) -> str:
    return "maas" if lender in maas_lenders() else "spot"


def contract_id(H) -> str:
    return f"s5_tau5_H{int(H)}"


@lru_cache(maxsize=None)
def _rows() -> dict:
    """{(lender, H, mu): e2_reactions row} of the contracts s5_tau5_H*."""
    out = {}
    for r in reactions()["rows"]:
        if r["contract"].startswith("s5_tau5_H"):
            out[(r["lender"], int(r["H_min"]), float(r["mu_over_beta_tilde_ref"]))] = r
    return out


def reaction_row(lender: str, H, mu) -> dict:
    for (l, h, m), r in _rows().items():
        if l == lender and h == int(H) and abs(m - float(mu)) <= 1e-12:
            return r
    raise KeyError(f"no e2_reactions row for {lender}, {contract_id(H)}, mu {mu}")


@lru_cache(maxsize=None)
def layer_sites(lender: str, H) -> int:
    """The number of layer sites the instance builder gives `lender` under the one contract s5_tau5_H<H> (sim_spec
    §4.3 step 2 and §10 S35: none when no layer of LAYER_GPUS GPUs fits under the LEASE_QUANTILE quantile of the
    lendable slack at the contract's window). It depends on neither the series, mu nor the config seed: v_top is a
    quantile over the whole slack series, and the seed draws only the offset."""
    from .. import instance as instance_mod
    from ..config import load_config
    from ..drivers.run import instance_config
    cfg = instance_config(run_spec(lender, SERIES[0], H, 1.0, 1))
    cfg["seed"] = 1
    cfg = load_config(cfg)
    t = cfg["time"]
    slow = t["slow_slot_min"]
    grid = instance_mod.TimeGrid(slow, t["fast_slot_min"], t["horizon_min"] // slow, t["start_minute_of_week"])
    contracts = tuple(instance_mod._contract(c, slow, cfg["billing"]) for c in cfg["contracts"])
    ls = instance_mod._trace_lender(cfg["lenders"][0], cfg, grid, contracts, [],
                                    cfg["lender_model"]["merge_identical_layers"])
    return 0 if ls is None else sum(s.kind == "layer" for s in ls.sites)


@lru_cache(maxsize=None)
def _offered_cells() -> tuple:
    """(lender, H) offered with alpha_k < 1 in e2_reactions, sorted by (lender, H)."""
    lenders = set(maas_lenders() + spot_pools())
    return tuple(sorted({(l, h) for (l, h, _), r in _rows().items() if l in lenders and r["kind"] != "alpha>=1"}))


@lru_cache(maxsize=None)
def all_cells() -> tuple:
    """Every (lender, H) cell that runs A1 (§6.2): offered and alpha_k < 1, and the instance builder gives the
    lender at least one layer site (layer_sites), sorted by (lender, H)."""
    return tuple(x for x in _offered_cells() if layer_sites(*x) > 0)


@lru_cache(maxsize=None)
def cells_without_sites() -> tuple:
    """The offered cells with alpha_k < 1 that run nothing, since the builder gives the lender no layer site."""
    return tuple(x for x in _offered_cells() if layer_sites(*x) == 0)


def cells() -> tuple:
    """The cells of this run (all_cells, or its reduced subset)."""
    s = settings()
    return tuple(x for x in all_cells() if x[0] in s["lenders"] and x[1] in s["H"])


@lru_cache(maxsize=None)
def maas_quartiles() -> dict:
    """M50: the 20 MaaS clusters ordered by their median alpha_k over the H grid (e2_reactions alpha_k, contracts
    s5_tau5_H*; ties by lender id), 5 per quartile, maas_q1 the cheapest."""
    med = {}
    for l in maas_lenders():
        a = [r["alpha_k"] for (ll, h, m), r in _rows().items() if ll == l and m == mu_grid()[0]]
        med[l] = float(np.median(a))
    order = sorted(med, key=lambda l: (med[l], l))
    n = len(order) // 4
    return {f"maas_q{i + 1}": order[i * n:(i + 1) * n] for i in range(4)}


def groups() -> dict:
    """{group: lenders} (§6.7): maas, spot, each pool id and the MaaS quartiles (M50)."""
    g = {"maas": list(maas_lenders()), "spot": list(spot_pools())}
    g.update({p: [p] for p in spot_pools()})
    g.update(maas_quartiles())
    return g


def spot_pools_by_H() -> dict:
    """{H: pools with an A1 cell at H} (M23)."""
    out = {h: [] for h in h_grid()}
    for l, h in all_cells():
        if l in spot_pools():
            out[h].append(l)
    return out


# ---------------------------------------------------------------- instances (§6.3)
def overrides(lender: str, series: str, H, mu, c: int, horizon_min: Optional[int] = None) -> dict:
    """The overrides of configs/ms2_single_site.json for the base instance of (lender, series, H, mu, c)."""
    k = contract_id(H)
    return {"time.horizon_min": int(horizon_min if horizon_min is not None else settings()["horizon_min"]),
            "time.fast_slot_min": 1, "seed": int(c),
            "contracts": [{"id": k, "tau_min": TAU_MIN, "H_min": int(H)}, dict(PROTECTED)],
            "lenders.0": {"id": lender, "kind": "trace", "region": REGION, "group": lender, "n_layers": K_LAYERS,
                          "layer_gpus": LAYER_GPUS, "lease_size_quantile": LEASE_QUANTILE, "offset": "random",
                          "load_scenario": LOAD_SCENARIO, "menu": [k]},
            "borrowers": {"model": "series", "list": [{"id": "b0", "series": series, "tier": TIER, "region": REGION,
                                                       "slo_class": "strict"}],
                          "own_capacity_quantile": 75, "smoothing_min": 15, "market_tightness": 0.5},
            "stranding.mu_over_beta_tilde": float(mu)}


def run_spec(lender: str, series: str, H, mu, c: int, *, extra: Optional[dict] = None,
             horizon_min: Optional[int] = None, pid: str = "A1", params: Optional[dict] = None) -> dict:
    """The resolved run spec (drivers.run.load_run_spec) of the base instance; `extra` adds overrides (E6(a): the
    protected price and load time)."""
    from ..drivers.run import load_run_spec
    ov = overrides(lender, series, H, mu, c, horizon_min)
    ov.update(copy.deepcopy(extra or {}))
    name = f"e2_{lender_key(lender)}_{series}_H{int(H)}_mu{num(mu)}_c{int(c)}"
    return load_run_spec({"schema_version": 1, "name": name, "instance": CONFIG, "overrides": ov, "lender_model": {},
                          "engine": {"check_invariants": True}, "policy": {"id": pid, "params": dict(params or {})},
                          "seeds": {"config": [int(c)]}, "bench": None, "out": "code/sim/out/e2/runs"})


def build_base(spec: dict, c: int):
    """(inst, trace lender model, engine config) of a run spec for config seed c (drivers.run.build)."""
    from ..drivers.run import build
    return build(spec, int(c))


def layers_of(inst, K: int = K_LAYERS, q: float = LAYER_PERCENTILE) -> tuple:
    """(layers (K, T_fast) of 0/1 floats, P_q of the overflow): x' = K x / P_q(x) of the client's overflow x in
    replica loads per fast slot; layer k (1-based) is on in fast slot f iff x'(f) >= k (M18)."""
    x = np.asarray(inst.clients.demand[0], dtype=np.float64)
    p = float(np.percentile(x, q))
    xs = K * x / p if p > 0 else np.zeros_like(x)
    return np.stack([(xs >= k).astype(np.float64) for k in range(1, K + 1)]), p


def band_sites(inst) -> dict:
    """{k: site index} of the layer sites by local_layer_lo (band k is paired with layer k, bottom first)."""
    return {int(s.local_layer_lo): l for l, s in enumerate(inst.sites)
            if s.kind == "layer" and s.local_layer_lo is not None}


def prot_site(inst) -> int:
    ps = [l for l, s in enumerate(inst.sites) if s.kind == "protected"]
    if len(ps) != 1:
        raise ValueError(f"expected one protected site, got {ps}")
    return ps[0]


def single_band(inst, k: int, layers=None):
    """Layer k as the one client's demand (instance.with_demand), delta = INF at every site except band k and the
    protected site (a pure dataclasses.replace); a band-less layer has every layer site masked (M48)."""
    from ..instance import with_demand
    from ..types import INF
    if layers is None:
        layers = layers_of(inst)[0]
    out = with_demand(inst, np.asarray(layers[k - 1], dtype=np.float64)[None, :])
    keep = {prot_site(inst)}
    b = band_sites(inst).get(int(k))
    if b is not None:
        keep.add(b)
    delta = np.array(out.clients.delta_usd_per_h, dtype=np.float64, copy=True)
    for l in range(out.m):
        if l not in keep:
            delta[0, l] = INF
    return dataclasses.replace(out, clients=dataclasses.replace(out.clients, delta_usd_per_h=delta))


def on_periods(on) -> list:
    """[(f_a, f_b)]: the maximal runs [f_a, f_b) of fast slots with on > 0, in time order."""
    on = np.asarray(on) > 0
    if not on.any():
        return []
    d = np.diff(np.r_[0, on.astype(np.int8), 0])
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


def _rev_contract(inst, site: int) -> int:
    ks = [k for k in inst.sites[site].menu if not inst.contracts[k].protected]
    if len(ks) != 1:
        raise ValueError(f"site {inst.sites[site].id} offers {len(ks)} revocable contracts, expected 1")
    return ks[0]


def episode_instance(inst_k, band: int, R_band, f_a: int, f_b: int):
    """(episode instance, window_end) of the on-period [f_a, f_b) (fast slots) of a single-band instance (§6.3,
    M21): restrict_horizon(inst_k, t0, T_e) with t0 = floor(f_a / phi_b), T_e = ceil(f_b / phi_b) - t0 +
    ceil(D_k / slow) + 1 (capped at the horizon), demand 1 on [f_a, f_b) only, every layer site synthetic: band k
    with R = [r*, T_e), r* the band's first announcement at or after t0 in R_band (the week's realized trace
    schedule; none: R empty), the other bands with R empty, and the band's lender trace synthetic (same
    site_index). window_end: R is not empty."""
    from ..instance import restrict_horizon, validate, with_demand
    from ..types import LenderTrace
    g = inst_k.grid
    phi_b = g.phi
    f_a, f_b = int(f_a), int(f_b)
    t0 = f_a // phi_b
    D = inst_k.contracts[_rev_contract(inst_k, band)].D_min(g.slow_min)
    T_e = min(-(-f_b // phi_b) - t0 + -(-int(D) // g.slow_min) + 1, g.T_slow - t0)
    e = restrict_horizon(inst_k, t0, T_e)
    d = np.zeros((1, e.grid.T_fast))
    d[0, f_a - t0 * phi_b:f_b - t0 * phi_b] = 1.0
    e = with_demand(e, d)
    R = np.asarray(R_band, dtype=np.int64)
    R = R[R >= t0] - t0
    Rw = (np.arange(int(R[0]), T_e, dtype=np.int64) if len(R) and int(R[0]) < T_e
          else np.zeros(0, dtype=np.int64))
    sites = []
    for i, s in enumerate(e.sites):
        if s.kind == "layer":
            s = dataclasses.replace(s, kind="synthetic", layer_lo=None, layer_hi=None, local_layer_lo=None,
                                    R_explicit=(Rw.copy() if i == band else np.zeros(0, dtype=np.int64)))
        sites.append(s)
    lid = e.sites[band].lender
    lenders = tuple(LenderTrace(lender=lt.lender, kind="synthetic", series=None, S_full=None, S=None, B_gpus=0.0,
                                S_lend=None, v0=0, n_layers=0, layer_gpus=0, D_max_lender_min=0, offset_5min=0,
                                site_index=lt.site_index) if lt.lender == lid else lt for lt in e.lenders)
    out = dataclasses.replace(e, sites=tuple(sites), lenders=lenders,
                              notes=list(e.notes) + [f"episode [{f_a}, {f_b}) fast slots, window {len(Rw) > 0}"])
    validate(out)
    return out, bool(len(Rw) > 0)


def bl0a_usd(inst, demand) -> float:
    """BL0a's analytic cost of one client of LLM 0: q_j x the demand in replica-load-hours (M47)."""
    d = np.asarray(demand, dtype=np.float64)
    return float(inst.llms[0].q_usd_per_h) * float(d.sum()) * inst.grid.fast_min / 60.0


def static_schedule(inst, model, c: int):
    """The static announcement sets of a non-adaptive lender model (lender.Lender.static_schedule)."""
    from ..config import rng_streams
    from ..lender import Lender
    return Lender(inst, model, rng_streams(int(c))["lender"]).static_schedule()


# ---------------------------------------------------------------- rules and runs (§6.4)
def policy_params(rule: str, band: int, prot: int) -> tuple:
    """(policy id, params) of a rule key: the E2 rules and E6(a)'s plans ins, warm and bl7 (§7.1)."""
    a1 = {"site_rev": int(band), "site_prot": int(prot)}
    table = {"a1": ("A1", a1),
             "cold": ("A1", {**a1, "reaction": "cold"}),
             "prewarm": ("A1", {**a1, "reaction": "prewarm_if_feasible"}),
             "bl6": ("BL6", {"inner": "A1", "inner_params": dict(a1)}),
             "ins": ("A1", {**a1, "insure": "always"}),
             "warm": ("A1", {**a1, "reaction": "prewarm_if_feasible", "insure": "never"}),
             "bl7": ("BL7", {"inner": "A1", "inner_params": {"site_rev": int(band)}})}
    if rule not in table:
        raise ValueError(f"unknown rule {rule!r}")
    return table[rule]


def make_rule_policy(spec: dict, rule: str, band: int, prot: int, inst):
    """The rule's policy for `inst` through drivers.run.make_policy (§2.2)."""
    from ..drivers.run import make_policy
    pid, params = policy_params(rule, band, prot)
    return make_policy({**spec, "policy": {"id": pid, "params": params}}, inst)


def simulate_rule(spec: dict, rule: str, band: int, prot: int, inst, model, ecfg, c: int):
    from ..engine import simulate
    pol = make_rule_policy(spec, rule, band, prot, inst)
    return simulate(inst, pol, model, ecfg, lender_seed=int(c), policy_seed=int(c))


def a1_report(res) -> dict:
    """A1's report of a run (the inner's for BL6 and BL7)."""
    rep = (res.metrics or {}).get("policy") or {}
    if "wrapper" in rep:
        rep = rep.get("inner") or {}
    return rep


def run_record(res) -> dict:
    """Totals, ledger components, A1's report fields and the run's checks (E2-4) of one engine run."""
    rep = a1_report(res)
    comp = {k: float(v) for k, v in res.components.items()}
    return {"total": comp["total"], "components": comp, "insured": rep.get("insured"),
            "reaction": rep.get("reaction"), "counts": rep.get("counts"), "n_leases": len(res.leases),
            "invariant_failures": len(res.invariant_failures), "invariant_first": list(res.invariant_failures[:2]),
            "gpu_only_lease_slots": int((res.metrics or {}).get("gpu_only_lease_slots", 0))}


def dp_record(inst, sched, **kw) -> dict:
    """opt.dp.solve_dp value (grid 'fast', value only) with its status; DomainError recorded, not raised (§6.5)."""
    from ..opt.dp import DomainError, solve_dp
    try:
        r = solve_dp(inst, sched, grid="fast", return_plan=False, **kw)
    except DomainError as err:
        return {"value": None, "value_note": "outside the DP's domain", "status": "domain_error",
                "error": str(err)[:300]}
    return {"value": float(r.objective), "status": r.status_msg, "n_states": r.size.get("n_states"),
            "solve_s": r.solve_s}


def rules_for(mu: float, sched: str, H: int, insured: bool, reaction: str) -> tuple:
    """(rules run after A1, {rule: why} of the rules that take A1's values, rules without a value) (§6.4, M22)."""
    bl6 = ["bl6"] if int(H) > 0 else []
    if abs(float(mu) - 1.0) <= 1e-12:
        run = ["cold", "prewarm"] + bl6
    elif sched == "trace":
        run = ([] if insured else ["prewarm" if reaction == "cold" else "cold"]) + bl6
    else:
        run = bl6
    filled, missing = {}, []
    for r in ("cold", "prewarm", "bl6"):
        if r in run:
            continue
        if r == "bl6":
            filled[r] = "BL6 = A1 at H = 0 (not run, §6.4)"
        elif insured:
            filled[r] = "A1 insures: the fixed rules share its insurance branch (Q42 (a), M22)"
        elif (r == "cold" and reaction == "cold") or (r == "prewarm" and reaction == "warm"):
            filled[r] = f"A1's resolved reaction is {reaction!r} (Q42 (a), M22)"
        else:
            missing.append(r)
    return run, filled, missing


def _rel_diff(a, b) -> float:
    return abs(float(a) - float(b)) / max(1.0, abs(float(b)))


def _max_comp_diff(x: dict, y: dict) -> float:
    keys = set(x["components"]) | set(y["components"])
    return max((abs(x["components"].get(k, 0.0) - y["components"].get(k, 0.0)) for k in keys), default=0.0)


# ---------------------------------------------------------------- E2-2 (a): the cell kinds by c2rule
UNIT_FIELDS = ("alpha", "ap", "mu", "lam", "bw", "H", "beta_tilde_usd", "time_unit_h")


def row_kind(row: dict) -> dict:
    """The kind, insurance decision and C2-SW reaction of an e2_reactions row, recomputed by c2rule at the row's
    own units (E2-2 (a))."""
    from ..algos.c2rule import C2Units, c2_thresholds, insure_up_front
    u = C2Units(**row["units"])
    first = bool(u.ap <= u.alpha * (2 - u.alpha))
    th = c2_thresholds(u.alpha, u.ap, u.mu, u.lam, 1.0, u.bw)
    return {"kind": "first-clause" if first else "Cprime", "insure_up_front": bool(insure_up_front(u, "lb_react")),
            "reaction": {"cold": "cold", "warm": "pre-warm"}[th.react]}


def e2_2(row: dict, a1_units: Optional[dict]) -> dict:
    out = {"a": [], "b": []}
    got = row_kind(row)
    for f, v in got.items():
        if v != row[f]:
            out["a"].append({"field": f, "recomputed": v, "row": row[f]})
    if a1_units:
        for f in UNIT_FIELDS:
            a, b = a1_units.get(f), row["units"].get(f)
            if a is None or b is None:
                if a != b:
                    out["b"].append({"field": f, "a1": a, "row": b, "rel": None})
                continue
            rel = abs(float(a) - float(b)) / max(abs(float(b)), 1e-300)
            if rel > REL_TOL:
                out["b"].append({"field": f, "a1": a, "row": b, "rel": rel})
    return out


# ---------------------------------------------------------------- job ids
def cell_job_id(lender: str, H, mu, c: int) -> str:
    return mc.job_id(EXP, "cell", lender=lender_key(lender), H=int(H), mu=num(mu), c=int(c))


def cell_run_path(out, lender: str, H, mu, c: int) -> Path:
    """runs/cells/<record name> of a cell job (E6(a) reads it)."""
    return Path(out) / "runs" / "cells" / mc.job_file_name(cell_job_id(lender, H, mu, c))


def game_job_id(switch: str, mu, lam_key: str) -> str:
    return mc.job_id(EXP, "game", switch=switch, mu=num(mu), lam=lam_key)


# ---------------------------------------------------------------- the cell job (§6.8)
def run_cell(job, outputs, out) -> dict:
    p = job.params
    lender, H, mu, c = p["lender"], int(p["H"]), float(p["mu"]), int(p["c"])
    S = settings()
    scheds = SCHEDULES if c == 1 else ("trace",)
    row = reaction_row(lender, H, mu)
    errors: list = []
    n_runs = 0
    tally = {"n_runs": 0, "n_invariant_failures": 0, "n_gpu_only_lease_slots": 0, "n_dp": 0, "n_dp_not_optimal": 0,
             "n_dp_domain_error": 0, "examples": []}
    e23 = {"n_compared": 0, "n_compared_week": 0, "n_compared_episodes": 0, "max_abs_diff_a1_cold": 0.0,
           "max_abs_diff_insured": 0.0, "violations": []}
    e25 = {"n_episodes": 0, "min_ratio": None, "n_below": 0, "below": []}
    is_mu1 = abs(mu - 1.0) <= 1e-12
    a1_first: Optional[dict] = None
    rules_log: dict = {}
    series_out = {}

    def compare_e23(ra, recs, where, kind):
        """E2-3 (Q42 (a)), mu = 1: 'always cold' gives A1's ledger where A1 does not insure, 'always cold' and
        'pre-warm' give it where A1 insures (every ledger component to 1e-9 USD); week runs and episode runs."""
        ins = bool(ra.get("insured"))
        for r in (("cold", "prewarm") if ins else ("cold",)):
            x = recs.get(r)
            if x is None or "same_as" in x:
                continue
            dlt = _max_comp_diff(ra, x)
            e23["n_compared"] += 1
            e23[f"n_compared_{kind}"] += 1
            key = "max_abs_diff_insured" if ins else "max_abs_diff_a1_cold"
            e23[key] = max(e23[key], dlt)
            if dlt > REL_TOL and len(e23["violations"]) < 20:
                e23["violations"].append({"where": where, "rule": r, "insured": ins, "diff": dlt})

    def count(rec, where):
        tally["n_runs"] += 1
        if rec["invariant_failures"]:
            tally["n_invariant_failures"] += 1
            if len(tally["examples"]) < 10:
                tally["examples"].append({"where": where, "invariant": rec["invariant_first"]})
        if rec["gpu_only_lease_slots"]:
            tally["n_gpu_only_lease_slots"] += 1
            if len(tally["examples"]) < 10:
                tally["examples"].append({"where": where, "gpu_only_lease_slots": rec["gpu_only_lease_slots"]})

    def count_dp(d, where):
        tally["n_dp"] += 1
        if d["status"] == "domain_error":
            tally["n_dp_domain_error"] += 1
        elif d["status"] != "optimal":
            tally["n_dp_not_optimal"] += 1
        if d["status"] != "optimal" and len(tally["examples"]) < 10:
            tally["examples"].append({"where": where, "dp_status": d["status"], "error": d.get("error")})

    for series in S["series"]:
        spec = run_spec(lender, series, H, mu, c)
        inst, model, ecfg = build_base(spec, c)
        lay, p995 = layers_of(inst)
        bands, prot = band_sites(inst), prot_site(inst)
        models = {"trace": model, "eager": dataclasses.replace(model, schedule="eager", params={})}
        refuse = dataclasses.replace(model, schedule="trace", on_unavailable="refuse")
        layers_out = []
        ep = {"layer": [], "f_a": [], "f_b": [], "window_end": [], "opt": [], "opt_status": [], "bl0a": [],
              "alg": {}}
        for k in range(1, K_LAYERS + 1):
            dem = lay[k - 1]
            dh = float(dem.sum()) * inst.grid.fast_min / 60.0
            L = {"k": k, "band": None, "bandless": k not in bands, "demand_load_h": dh, "bl0a": bl0a_usd(inst, dem),
                 "on_share": float(dem.mean()), "n_on_periods": len(on_periods(dem))}
            inst_k = single_band(inst, k, lay)
            if k not in bands:
                for sched in scheds:
                    d = dp_record(inst_k, static_schedule(inst_k, models[sched], c))
                    count_dp(d, f"{series} layer {k} {sched} band-less")
                    L[sched] = {"dp": d, "rules": {}}
                layers_out.append(L)
                continue
            band = bands[k]
            L["band"] = inst.sites[band].id
            for sched in scheds:
                where = f"{series} layer {k} {sched}"
                rec_s = {"dp": None, "rules": {}, "not_run": []}
                res_a1 = mc.try_run(errors, f"{where} a1", simulate_rule, spec, "a1", band, prot, inst_k,
                                    models[sched], ecfg, c)
                if res_a1 is None:
                    L[sched] = rec_s
                    continue
                n_runs += 1
                ra = run_record(res_a1)
                count(ra, f"{where} a1")
                rep = a1_report(res_a1)
                if a1_first is None:
                    a1_first = {k_: rep.get(k_) for k_ in ("insured", "reaction", "status", "n_s0", "s0_min", "units",
                                                           "rrl")}
                run_rules, filled, missing = rules_for(mu, sched, H, bool(rep.get("insured")), rep.get("reaction"))
                rules_log.setdefault(sched, {"run": ["a1"] + run_rules, "filled": filled, "not_run": missing})
                rec_s["rules"]["a1"] = ra
                results = {"a1": res_a1}
                for r in run_rules:
                    res = mc.try_run(errors, f"{where} {r}", simulate_rule, spec, r, band, prot, inst_k,
                                     models[sched], ecfg, c)
                    if res is None:
                        continue
                    n_runs += 1
                    rec_s["rules"][r] = run_record(res)
                    count(rec_s["rules"][r], f"{where} {r}")
                    results[r] = res
                for r, why in filled.items():
                    rec_s["rules"][r] = {"same_as": "a1", "why": why}
                rec_s["not_run"] = missing
                rec_s["dp"] = dp_record(inst_k, res_a1.schedule)
                count_dp(rec_s["dp"], where)
                # E2-3: at mu = 1 the fixed rules coincide with A1 (Q42 (a))
                if is_mu1:
                    compare_e23(ra, rec_s["rules"], where, "week")
                L[sched] = rec_s
                if sched != "trace":
                    continue
                # episodes of this layer (§6.3, M21), `trace` only
                R_band = np.asarray(res_a1.schedule.R[band], dtype=np.int64)
                ep_rules = [r for r in ("a1",) + tuple(run_rules) if r in results]
                for r in ep_rules:
                    ep["alg"].setdefault(r, [None] * len(ep["layer"]))
                for (fa, fb) in on_periods(dem):
                    ep["layer"].append(k)
                    ep["f_a"].append(int(fa))
                    ep["f_b"].append(int(fb))
                    b0 = float(inst.llms[0].q_usd_per_h) * (fb - fa) * inst.grid.fast_min / 60.0
                    ep["bl0a"].append(b0)
                    for r in ep["alg"]:
                        ep["alg"][r].append(None)
                    e_inst = mc.try_run(errors, f"{where} episode [{fa}, {fb}) build", episode_instance, inst_k, band,
                                        R_band, fa, fb)
                    if e_inst is None:
                        ep["window_end"].append(None)
                        ep["opt"].append(None)
                        ep["opt_status"].append("build_error")
                        continue
                    e, wend = e_inst
                    ep["window_end"].append(wend)
                    sched_e = None
                    ep_recs = {}
                    for r in ep_rules:
                        res = mc.try_run(errors, f"{where} episode [{fa}, {fb}) {r}", simulate_rule, spec, r, band,
                                         prot, e, refuse, ecfg, c)
                        if res is None:
                            continue
                        n_runs += 1
                        rr = run_record(res)
                        count(rr, f"{where} episode [{fa}, {fb}) {r}")
                        ep["alg"][r][-1] = rr["total"]
                        ep_recs[r] = rr
                        sched_e = res.schedule
                    if is_mu1 and "a1" in ep_recs:
                        compare_e23(ep_recs["a1"], ep_recs, f"{where} episode [{fa}, {fb})", "episodes")
                    if sched_e is None:
                        ep["opt"].append(None)
                        ep["opt_status"].append("no_run")
                        continue
                    d = dp_record(e, sched_e, refuse_unavailable=True)
                    count_dp(d, f"{where} episode [{fa}, {fb})")
                    ep["opt"].append(d["value"])
                    ep["opt_status"].append(d["status"])
                    if d["value"] is None or not d["value"] > 0:
                        continue
                    e25["n_episodes"] += 1
                    vals = {r: ep["alg"][r][-1] for r in ep_rules}
                    vals["bl0a"] = b0
                    for r, v in vals.items():
                        if v is None:
                            continue
                        ratio = v / d["value"]
                        if e25["min_ratio"] is None or ratio < e25["min_ratio"]:
                            e25["min_ratio"] = ratio
                        if ratio < 1.0 - REL_TOL:
                            e25["n_below"] += 1
                            if len(e25["below"]) < 50:
                                e25["below"].append({"series": series, "layer": k, "f_a": int(fa), "f_b": int(fb),
                                                     "rule": r, "alg": v, "opt": d["value"], "ratio": ratio})
            layers_out.append(L)
        series_out[series] = {"p995_loads": p995, "n_bands": len(bands), "band_ids": [inst.sites[bands[k]].id
                                                                                       for k in sorted(bands)],
                              "price_rev": float(inst.price[bands[min(bands)], _rev_contract(inst, bands[min(bands)])])
                              if bands else None,
                              "start_minute_of_week": int(inst.grid.start_mow), "layers": layers_out, "episodes": ep}
    e22 = e2_2(row, (a1_first or {}).get("units"))
    data = {"meta": {"job": job.id, "exp": EXP, "spec": SPEC, "git_revision": mc.git_revision(),
                     "versions": mc.versions(), "settings": {k: (list(v) if isinstance(v, tuple) else v)
                                                             for k, v in S.items()}},
            "cell": {"lender": lender, "group": group_of(lender), "H": H, "mu": mu, "c": c,
                     "contract": contract_id(H), "row": {k: row.get(k) for k in
                                                         ("kind", "insure_up_front", "reaction", "alpha_k",
                                                          "H_star_mu_s", "status", "first_clause", "units")}},
            "a1": a1_first, "rules": rules_log, "schedules": list(scheds), "series": series_out,
            "checks": {"E2_2": e22, "E2_3": e23, "E2_4": tally, "E2_5": e25}}
    outputs.dump(data, cell_run_path(out, lender, H, mu, c), compact=True)
    a1s = {k_: (a1_first or {}).get(k_) for k_ in ("insured", "reaction", "status")}
    return {"runs": n_runs, "errors": errors, "a1": a1s, "rules": rules_log,
            "E2_2": {"a": len(e22["a"]), "b": len(e22["b"])}, "E2_3": {k_: e23[k_] for k_ in
                                                                      ("n_compared", "n_compared_week",
                                                                       "n_compared_episodes", "max_abs_diff_a1_cold",
                                                                       "max_abs_diff_insured")},
            "E2_4": {k_: v for k_, v in tally.items() if k_ != "examples"},
            "E2_5": {"n_episodes": e25["n_episodes"], "min_ratio": e25["min_ratio"], "n_below": e25["n_below"],
                     "below": e25["below"][:20]}}


# ---------------------------------------------------------------- the C2 game (§6.6)
def game_inputs() -> dict:
    """por_default.json `inputs` and derived values used by the game, and the minute mapping."""
    inp = por()["inputs"]
    AL, AP = float(inp["alpha"]), float(inp["alpha_p"])
    lam_s = float(a11()["load_time_s"]["maas_a10"][TIER][LOAD_SCENARIO])
    BS = float(por()["derived"]["beta_s"])          # por_default.py's BS = 1.65 (1 - alpha), the same float
    return {"AL": AL, "AP": AP, "LAM": float(inp["lambda_default"]), "BW": float(inp["bw_default"]),
            "PHI": float(inp["phi"]), "MUS": tuple(float(m) for m in inp["mu_over_beta_tilde"]), "BS": BS,
            "DT": float(por()["derived"]["dt"]), "lambda_s": lam_s,
            "min_per_beta_tilde": lam_s * (AL + float(inp["phi"])) / 60.0,
            "two_minus_alpha": float(por()["derived"]["two_minus_alpha"])}


def h_base() -> list:
    """por_default.py's H_BASE: the Hs of table_por_switch_beta at mu = 1, lambda = inputs.lambda_default."""
    gi = game_inputs()
    return sorted({float(r["Hs"]) for r in por()["table_por_switch_beta"]
                   if float(r["mu"]) == 1.0 and float(r["lam"]) == gi["LAM"]})


def lam_keys() -> dict:
    """{lam key: lambda in beta~ units}: '0' and the key of inputs.lambda_default ('0.715')."""
    lam = game_inputs()["LAM"]
    return {num(0.0): 0.0, num(lam): lam}


def game_grid(switch: str, mu: float, lam_key: str) -> dict:
    """{Hs: [grid names]} of one game job (§6.6): 'main' (M24: mu = 1, lambda_default, switch beta: Hs = round(i /
    20, 12) for i = 0..25 plus the H_BASE points above 1.25) and 'supp' (Hs = round(i / 10, 12) up to 2 at mu <= 1
    and up to 6 at mu = 2). Reduced runs: the main points at H_BASE and the supp points of REDUCED['game_supp']."""
    lam_main = num(game_inputs()["LAM"])
    out: dict = {}
    if reduced():
        supp = [x for x in REDUCED["game_supp"]]
        main = list(h_base())
    else:
        top = 20 if mu <= 1.0 else 60
        supp = [round(i / 10, 12) for i in range(0, top + 1)]
        main = [round(i / 20, 12) for i in range(0, 26)] + [h for h in h_base() if h > 1.25]
    if switch == "beta" and abs(mu - 1.0) <= 1e-12 and lam_key == lam_main:
        for h in main:
            out.setdefault(float(h), []).append("main")
    for h in supp:
        out.setdefault(float(h), []).append("supp")
    return dict(sorted(out.items()))


def game_jobs_params() -> list:
    """(switch, mu, lam key) of the 10 game jobs: 8 with switch beta (mu x lambda in {0, lambda_default}) and 2 C2-SW
    jobs at mu in {1, 2}, lambda_default."""
    gi = game_inputs()
    out = [("beta", mu, lk) for mu in gi["MUS"] for lk in lam_keys()]
    out += [("c2sw", mu, num(gi["LAM"])) for mu in gi["MUS"] if mu >= 1.0]
    return out


def _game_cell(args) -> dict:
    """One C2 game cell, exactly por_default.py's exact(): solve_det (switch beta~, full_plans False,
    return_detail) or solve_det_bw (b_w), with dt, T = Hs + 13, Rmax = Hs + 6 in beta_s units."""
    switch, mu, lam, Hs, gi = args
    c2 = paths.import_c2()
    t0 = time.perf_counter()
    BS = gi["BS"]
    P = c2.model.Params(H=Hs, alpha=gi["AL"], ap=gi["AP"], mu=mu * BS, lam=lam * BS, beta=BS)
    row = {"switch": switch, "mu": mu, "lam": lam, "lam_key": num(lam), "Hs": Hs, "H_beta": Hs / BS,
           "H_min": Hs / BS * gi["min_per_beta_tilde"]}
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        if switch == "beta":
            r = c2.det_game.solve_det(P, dt=gi["DT"], T=Hs + 13.0, Rmax=Hs + 6.0, full_plans=False, return_detail=True)
            row.update(CR=float(r["CR"]), CR_react=float(r["CR_react_class"]), CR_ins=float(r["CR_ins_class"]))
        else:
            r = c2.model_switch_cost.solve_det_bw(P, gi["BW"] * BS, dt=gi["DT"], T=Hs + 13.0, Rmax=Hs + 6.0)
            row.update(CR=float(r["CR"]), CR_react=None, CR_react_note="solve_det_bw returns CR* and the plan only",
                       CR_ins=None, CR_ins_note="solve_det_bw returns CR* and the plan only")
    row["PoR"] = row["CR"] / gi["two_minus_alpha"]
    row["plan_type"] = str(r["plan"][0])
    row["seconds"] = time.perf_counter() - t0
    return row


def _game_cell_safe(args) -> dict:
    """{'row': _game_cell(args)}, or {'error': {tag, error, traceback}} if the cell raised (§2.4: an error of one
    run is recorded and the job goes on)."""
    errs: list = []
    row = mc.try_run(errs, f"game cell Hs {args[3]:g}", _game_cell, args)
    return {"row": row} if row is not None else {"error": errs[0]}


def game_slots() -> int:
    """Processes of an all-slot game job: the slot lock files it holds (MS3_SLOTS), at least 1."""
    return max(1, len([s for s in mc.slots_from_env() if s.startswith("slot")]))


def run_game(job, outputs, out, cell=_game_cell_safe) -> dict:
    p = job.params
    switch, mu, lam_key = p["switch"], float(p["mu"]), p["lam"]
    lam = lam_keys()[lam_key]
    gi = game_inputs()
    grid = game_grid(switch, mu, lam_key)
    args = [(switch, mu, lam, h, gi) for h in sorted(grid, reverse=True)]     # longest first
    n = min(game_slots(), len(args)) if args else 1
    if n > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(n) as pool:
            got = pool.map(cell, args, chunksize=1)
    else:
        got = [cell(a) for a in args]
    rows = [g["row"] for g in got if "row" in g]
    errors = [g["error"] for g in got if "error" in g]
    for r in rows:
        r["grids"] = grid[r["Hs"]]
    rows.sort(key=lambda r: r["Hs"])
    outputs.dump({"job": job.id, "switch": switch, "mu": mu, "lam": lam, "lam_key": lam_key, "processes": n,
                  "git_revision": mc.git_revision(), "rows": rows,
                  "failed_Hs": [float(a[3]) for a, g in zip(args, got) if "error" in g]},
                 Path(out) / "runs" / "game" / mc.job_file_name(job.id))
    return {"runs": len(rows), "errors": errors, "processes": n, "cells": len(rows), "cells_failed": len(errors)}


def game_meta() -> dict:
    """game.json meta: the inputs, the minute mapping and C2-T4's thresholds hstar.<mu>.<lam> (switch beta)."""
    from ..algos.c2rule import c2_thresholds
    gi = game_inputs()
    hs = {}
    for mu in gi["MUS"]:
        for lk, lam in lam_keys().items():
            h = float(c2_thresholds(gi["AL"], gi["AP"], mu, lam, 1.0, None).Hstar)
            hs.setdefault(num(mu), {})[lk] = {"H_beta": h, "Hs": h * gi["BS"], "H_min": h * gi["min_per_beta_tilde"]}
    return {"spec": "design/sim_spec_ms3.md §6.6", "source": "code/theory_checks/c2/out/por_default.json (inputs)",
            "settings": {"dt": gi["DT"], "T": "Hs + 13", "Rmax": "Hs + 6", "beta_s": gi["BS"],
                         "full_plans": False, "switch_beta": "det_game.solve_det (return_detail)",
                         "switch_c2sw": f"model_switch_cost.solve_det_bw, b_w = {gi['BW']}"},
            "inputs": {"alpha": gi["AL"], "alpha_p": gi["AP"], "lambda_default": gi["LAM"], "bw_default": gi["BW"],
                       "phi": gi["PHI"], "mu_over_beta_tilde": list(gi["MUS"])},
            "two_minus_alpha": gi["two_minus_alpha"], "lambda_s": gi["lambda_s"],
            "minutes_per_beta_tilde": gi["min_per_beta_tilde"],
            "minutes_note": "H_min = (Hs / beta_s) lambda_s (alpha + phi) / 60, lambda_s = a11 "
                            "load_time_s.maas_a10.M.a5_2GBps",
            "hstar": hs, "hstar_note": "C2-T4's threshold H*_mu with switch cost beta "
                                       "(c2rule.c2_thresholds(AL, AP, mu, lam, 1.0, None).Hstar)"}


# ---------------------------------------------------------------- E2-6: DP sum against the joint MILP (§6.5, M46)
def joint_job_id(lender: str, series: str, H) -> str:
    return mc.job_id(EXP, "joint", lender=lender_key(lender), series=series, H=int(H))


def _solve_record(sr) -> dict:
    if sr is None:
        return None
    return {"status": sr.status, "status_msg": sr.status_msg, "objective": sr.objective, "dual_bound": sr.dual_bound,
            "gap": sr.gap, "grid": sr.grid, "size": dict(sr.size), "build_s": sr.build_s, "solve_s": sr.solve_s,
            "peak_rss_mb": sr.peak_rss_mb}


def joint_lp_path(out, jid: str) -> Path:
    """runs/joint/<record name>.lp.json: the joint job's record written before its MILP starts (the LP and the
    layers' DPs), so that a job stopped at the hard wall-clock limit keeps the LP as its LB (§2.5)."""
    return Path(out) / "runs" / "joint" / (mc.job_file_name(jid)[:-len(".json")] + ".lp.json")


def _joint_record(base: dict, b: dict, milp: Optional[dict]) -> dict:
    """A joint_milp.json row: `base` (the instance, the layers' DPs, the LP), the MILP's record and the benchmark
    values b of ms3_common.bench_values, with sum DP / LB_joint and sum DP / incumbent (E2-6)."""
    sum_dp = base.get("sum_dp")
    rec = {**base, "milp": milp, **b,
           "ratio_sum_dp_over_LB": (sum_dp / b["LB"]) if (sum_dp is not None and b.get("LB")) else None,
           "ratio_sum_dp_over_incumbent": (sum_dp / b["incumbent"]) if (sum_dp is not None and b.get("incumbent"))
           else None}
    for k in ("ratio_sum_dp_over_LB", "ratio_sum_dp_over_incumbent"):
        if rec[k] is None:
            rec[f"{k}_note"] = "no value (a DP outside its domain, or no LB / incumbent)"
    return rec


def joint_rows(out, js, recs: dict) -> list:
    """The rows of joint_milp.json: the run file of every 'ok' joint job; for a joint job stopped at the hard
    wall-clock limit or by the cap (status wall_limit or oom_at_3G, §0 item 2), its pre-MILP record with LB = the
    LP (§2.5, Q39) and the job's status as the MILP's."""
    rows = []
    for j in js:
        if j.params["part"] != "joint":
            continue
        st = (recs.get(j.id) or {}).get("status")
        if st == "ok":
            d = mc.read_json(Path(out) / "runs" / "joint" / mc.job_file_name(j.id))
            if d:
                rows.append(d)
        elif st in ("wall_limit", "oom_at_3G"):
            pre = mc.read_json(joint_lp_path(out, j.id))
            if pre:
                pre.pop("stage", None)
                row = _joint_record(pre, mc.bench_values(pre.get("lp"), {"status": st}), {"status": st})
                row["note"] = f"the MILP job ended as {st}: LB is the LP (§2.5)"
                rows.append(row)
    return rows


def run_joint(job, outputs, out) -> dict:
    from ..instance import restrict_horizon, with_demand
    from ..opt.milp import solve_lp, solve_opt
    p = job.params
    lender, series, H = p["lender"], p["series"], int(p["H"])
    mu, c = 1.0, 1
    errors: list = []
    spec = run_spec(lender, series, H, mu, c)
    inst, model, ecfg = build_base(spec, c)
    lay, _ = layers_of(inst)
    T_day = min(DAY_MIN // inst.grid.slow_min, inst.grid.T_slow)
    day = restrict_horizon(inst, 0, T_day)
    lay_d = lay[:, :T_day * inst.grid.phi]
    sched = static_schedule(day, model, c)
    bands = band_sites(day)
    dps = []
    for k in range(1, K_LAYERS + 1):
        d = dp_record(single_band(day, k, lay_d), sched)
        dps.append({"k": k, "band": day.sites[bands[k]].id if k in bands else None, **d})
    vals = [d["value"] for d in dps]
    sum_dp = float(sum(vals)) if all(v is not None for v in vals) else None
    joint = with_demand(day, lay_d.sum(axis=0)[None, :])
    lp = mc.try_run(errors, "LP", solve_lp, joint, sched, grid="fast", return_plan=False)
    base = {"lender": lender, "series": series, "H": H, "mu": mu, "c": c, "T_slow": T_day, "sum_dp": sum_dp,
            "dp_by_layer": dps, "lp": _solve_record(lp), "milp_limit_s": mc.milp_limit_s()}
    # complete before the MILP starts (atomic rename): the LP bound survives a kill at the wall limit (§2.5)
    mc.dump_json({**base, "stage": "written before the MILP started"}, joint_lp_path(out, job.id))
    milp = mc.try_run(errors, "MILP", solve_opt, joint, sched, grid="fast", time_limit_s=mc.milp_limit_s(),
                      return_plan=False)
    b = mc.bench_values(lp, milp)
    rec = _joint_record(base, b, _solve_record(milp))
    rec["errors"] = [e["error"] for e in errors]
    if any(isinstance(e.get("error"), str) and e["error"].startswith("SizeError") for e in errors):
        rec["size_gate"] = "S36 gate: the model is above max_vars or the memory budget"
    outputs.dump(rec, Path(out) / "runs" / "joint" / mc.job_file_name(job.id))
    return {"runs": 0, "errors": errors, "sum_dp": sum_dp, "LB": b.get("LB"), "gap": b.get("gap")}


# ---------------------------------------------------------------- E2-5: MILPs on the episodes below ratio 1
def ep_milp_candidates(out) -> list:
    """The episodes whose per-episode ratio is below 1 - 1e-9 in some rule, from the cell job records (result.E2_5.
    below, at most 20 per job), one entry per episode, sorted by (job id, series, layer, f_a)."""
    eps = {}
    for jid, rec in sorted(mc.read_records(out).items()):
        if not jid.startswith(f"{EXP}:cell:") or not rec or rec.get("status") != "ok":
            continue
        for b in ((rec.get("result") or {}).get("E2_5") or {}).get("below") or []:
            key = (jid, b["series"], int(b["layer"]), int(b["f_a"]))
            eps.setdefault(key, {"job": jid, **{k: b[k] for k in ("series", "layer", "f_a", "f_b")}, "rules": []})
            eps[key]["rules"].append({k: b[k] for k in ("rule", "alg", "opt", "ratio")})
    return [eps[k] for k in sorted(eps)]


def run_ep_milp(job, outputs, out) -> dict:
    from ..opt.milp import solve_lp, solve_opt
    i = int(job.params["i"])
    cand = ep_milp_candidates(out)
    rec = {"i": i, "n_candidates": len(cand)}
    errors: list = []
    if i >= len(cand):
        rec["note"] = f"no episode number {i} below ratio 1 - 1e-9 ({len(cand)} in all)"
        outputs.dump(rec, Path(out) / "runs" / "ep_milp" / mc.job_file_name(job.id))
        return {"runs": 0, "errors": [], "n_candidates": len(cand)}
    e = cand[i]
    _, _, kv = mc.parse_job_id(e["job"])
    lender, H, mu, c = lender_of_key(kv["lender"]), int(kv["H"]), float(kv["mu"]), int(kv["c"])
    spec = run_spec(lender, e["series"], H, mu, c)
    inst, model, ecfg = build_base(spec, c)
    lay, _ = layers_of(inst)
    k = int(e["layer"])
    band = band_sites(inst)[k]          # single_band keeps the protected site (prot_site)
    inst_k = single_band(inst, k, lay)
    R_band = static_schedule(inst_k, model, c).R[band]
    ei, wend = episode_instance(inst_k, band, R_band, e["f_a"], e["f_b"])
    sched_e = static_schedule(ei, dataclasses.replace(model, on_unavailable="refuse"), c)
    dp = dp_record(ei, sched_e, refuse_unavailable=True)
    lp = mc.try_run(errors, "LP", solve_lp, ei, sched_e, grid="fast", refuse_unavailable=True, return_plan=False)
    milp = mc.try_run(errors, "MILP", solve_opt, ei, sched_e, grid="fast", refuse_unavailable=True,
                      time_limit_s=mc.milp_limit_s(), return_plan=False)
    b = mc.bench_values(lp, milp)
    verdicts = []
    for r in e["rules"]:
        lbr = mc.lb_record(r["alg"], lp, milp)
        below_lb = lbr["LB"] is not None and r["alg"] < lbr["LB"] * (1 - REL_TOL)
        counter = (b["incumbent"] is not None and dp["value"] is not None
                   and b["incumbent"] < dp["value"] * (1 - REL_TOL))
        verdicts.append({**r, "lb_record": lbr, "alg_below_LB": bool(below_lb),
                         "verdict": "bug" if below_lb else ("explained: counterexample to Claim D2" if counter
                                                            else "bug")})
    rec.update(episode=e, lender=lender, H=H, mu=mu, c=c, window_end=wend, dp=dp, lp=_solve_record(lp),
               milp=_solve_record(milp), **b, rules=verdicts, milp_limit_s=mc.milp_limit_s(),
               errors=[x["error"] for x in errors])
    outputs.dump(rec, Path(out) / "runs" / "ep_milp" / mc.job_file_name(job.id))
    return {"runs": 0, "errors": errors, "verdicts": [v["verdict"] for v in verdicts]}


# ---------------------------------------------------------------- jobs and estimates
def cell_est_s(mu: float, c: int) -> float:
    if abs(mu - 1.0) > 1e-12:
        return EST_CELL_S["mu_ne_1"]
    return EST_CELL_S["mu1_c1"] if c == 1 else EST_CELL_S["mu1_c_gt_1"]


def jobs() -> list:
    """Every E2 job in run order: the cell jobs (mu = 1, c = 1 first, then mu != 1, then the alignments 2-4), the
    game jobs, the joint MILPs and the E2-5 MILP jobs."""
    S = settings()
    out = []
    order = [(mu, 1) for mu in S["mu"] if abs(mu - 1.0) <= 1e-12] + \
            [(mu, 1) for mu in S["mu"] if abs(mu - 1.0) > 1e-12] + \
            [(mu, c) for mu in S["mu"] if abs(mu - 1.0) <= 1e-12 for c in S["alignments"] if c != 1]
    for mu, c in order:
        for lender, H in cells():
            out.append(mc.Job(cell_job_id(lender, H, mu, c), "pool",
                              {"part": "cell", "lender": lender, "H": int(H), "mu": float(mu), "c": int(c)},
                              cell_est_s(mu, c)))
    for switch, mu, lk in game_jobs_params():
        n = len(game_grid(switch, mu, lk))
        out.append(mc.Job(game_job_id(switch, mu, lk), "alone",
                          {"part": "game", "switch": switch, "mu": float(mu), "lam": lk, "cells": n},
                          n * EST_GAME_CELL_S))
    for lender, series, H in (REDUCED["joint"] if reduced() else JOINT_KEYS):
        out.append(mc.Job(joint_job_id(lender, series, H), "milp",
                          {"part": "joint", "lender": lender, "series": series, "H": int(H)}, EST_JOINT_S))
    for i in range(REDUCED["ep_milp"] if reduced() else N_EP_MILP):
        out.append(mc.Job(mc.job_id(EXP, "ep_milp", i=i), "milp", {"part": "ep_milp", "i": i}, None))
    return out


def run(job, outputs, out) -> dict:
    part = job.params["part"]
    fn = {"cell": run_cell, "game": run_game, "joint": run_joint, "ep_milp": run_ep_milp}[part]
    return fn(job, outputs, out)


def manifest_extra(out) -> dict:
    """The instance hashes (q44_study.instance_hash) of every cell job's base instances per series and of the
    joint instances, and the sha256 of the input files."""
    hashes = {}
    for j in jobs():
        p = j.params
        if p["part"] == "cell":
            hashes[j.id] = {s: mc.instance_hash(build_base(run_spec(p["lender"], s, p["H"], p["mu"], p["c"]),
                                                           p["c"])[0]) for s in settings()["series"]}
        elif p["part"] == "joint":
            hashes[j.id] = mc.instance_hash(build_base(run_spec(p["lender"], p["series"], p["H"], 1.0, 1), 1)[0])
    inputs = {str(f.relative_to(paths.REPO)): _sha256(f) for f in (REACTIONS, A11_FILE, A12_FILE, POR_FILE)}
    return {"instance_hashes": hashes, "inputs_sha256": inputs, "reduced": reduced(),
            "settings": {k: (list(v) if isinstance(v, tuple) else v) for k, v in settings().items()}}


# ---------------------------------------------------------------- summary (§6.7, §6.9)
BOOT_B, BOOT_SEED = 2000, 0


def agg(values) -> dict:
    """median, median_ci95, p95, p95_ci95, max, n: metrics.aggregate's percentile bootstrap (B = 2000, seed 0, the
    same resample draws) for the median and the P95 of each resample."""
    v = np.asarray([x for x in values if x is not None], dtype=np.float64)
    n = len(v)
    if n == 0:
        return {"n": 0, "median": None, "median_note": "no value", "median_ci95": [None, None],
                "median_ci95_note": "no value", "p95": None, "p95_note": "no value", "p95_ci95": [None, None],
                "p95_ci95_note": "no value", "max": None, "max_note": "no value"}
    rng = np.random.default_rng(BOOT_SEED)
    meds, p95s = np.empty(BOOT_B), np.empty(BOOT_B)
    rows = max(1, min(BOOT_B, 4_000_000 // n))
    for a in range(0, BOOT_B, rows):
        b = min(BOOT_B, a + rows)
        idx = rng.integers(0, n, size=(b - a, n))
        q = np.percentile(v[idx], [50, 95], axis=1)
        meds[a:b], p95s[a:b] = q[0], q[1]
    lo, hi = np.percentile(meds, [2.5, 97.5])
    plo, phi_ = np.percentile(p95s, [2.5, 97.5])
    return {"n": int(n), "median": float(np.median(v)), "median_ci95": [float(lo), float(hi)],
            "p95": float(np.percentile(v, 95)), "p95_ci95": [float(plo), float(phi_)], "max": float(v.max())}


def agg_median(values) -> dict:
    """metrics.aggregate (median, median_ci95, p95, max, n) of the totals, with a note when there is no value."""
    v = [x for x in values if x is not None]
    if not v:
        return _agg_null("no value")
    return mc.median_summary(v)


def _agg_null(note: str) -> dict:
    """agg_median's fields with no value, each null with its '*_note' (§2.6), and `note`."""
    return {"n": 0, "median": None, "median_note": note, "median_ci95": [None, None], "median_ci95_note": note,
            "p95": None, "p95_note": note, "max": None, "max_note": note, "note": note}


def _null(note: str, fields=("median", "p95")) -> dict:
    """agg's fields (per-episode entries) with no value, each null with its '*_note' (§2.6), and `note`."""
    d = {"n": 0, "note": note}
    for f in fields:
        d[f] = None
        d[f"{f}_note"] = note
        d[f"{f}_ci95"] = [None, None]
        d[f"{f}_ci95_note"] = note
    d.update(max=None, max_note=note, n_alignments=0, alignments=[], n_lenders=0, ran=None, ran_note=note,
             by_alignment={})
    return d


def _best_H_null(note: str) -> dict:
    """A best_H entry without a minimizer: its fields, null with their '*_note' (§2.6), and `note`."""
    return {"H": None, "H_note": note, "H_min": None, "H_min_note": note, "cost_over_bl0a": None,
            "cost_over_bl0a_note": note, "median_ci95": [None, None], "median_ci95_note": note, "note": note}


def _totals_null(note: str) -> dict:
    """A totals entry without a value: the fields of _totals_entry, null with notes (§2.6)."""
    return {"note": note, "n_pairs": 0, "cost_over_bl0a": _agg_null(note), "whole_trace_ratio": _agg_null(note),
            "cost_per_demand_h": _agg_null(note), "components": None, "components_note": note,
            "components_over_bl0a": None, "components_over_bl0a_note": note, "n_dp_excluded": 0, "n_alignments": 0,
            "alignments": [], "n_lenders": 0, "by_alignment": {}}


def _resolve(rules: dict, r: str) -> Optional[dict]:
    x = rules.get(r)
    if x is None:
        return None
    if "same_as" in x:
        return rules.get(x["same_as"])
    return x


def _arr(values) -> np.ndarray:
    return np.array([np.nan if v is None else v for v in values], dtype=np.float64)


def _comp(rec: dict) -> dict:
    c = rec["components"]
    return {k: float(c.get(k, 0.0)) for k in COMPONENT_KEYS}


def _comp_fallback(bl0a: float) -> dict:
    out = {k: 0.0 for k in COMPONENT_KEYS}
    out["fallback"] = out["total"] = float(bl0a)
    return out


class _Collect:
    """The values of the summary, read from the cell run files one at a time."""

    def __init__(self):
        self.pairs = {}        # (lender, H, mu, sched, c, series) -> pair values
        self.eps = {}          # (lender, H, mu, c, rule) -> list of ratio arrays
        self.ran = {}          # (lender, H, mu, c, rule) -> rule ran (not filled) in some layer
        self.coinc = {}        # (lender, H, mu, c, rule in {prewarm, cold}) -> [n_compared, n_differ, ran]
        self.bandless = {}     # (lender, H, c) -> dict
        self.bandless_all = []
        self.e22a, self.e22b, self.e23, self.e24, self.e25 = [], [], [], [], []
        self.e27 = {}          # (lender, H) -> [n eligible, n above]
        self.a1 = {}           # (lender, H, mu, c) -> {insured, reaction}
        self.n_e22 = 0

    def add(self, d: dict) -> None:
        cell = d["cell"]
        lender, H, mu, c = cell["lender"], int(cell["H"]), float(cell["mu"]), int(cell["c"])
        self.a1[(lender, H, mu, c)] = d.get("a1") or {}
        self.n_e22 += 1
        ch = d["checks"]
        for x in ch["E2_2"]["a"]:
            self.e22a.append({"lender": lender, "H": H, "mu": mu, **x})
        for x in ch["E2_2"]["b"]:
            self.e22b.append({"lender": lender, "H": H, "mu": mu, "c": c, **x})
        self.e23.append({"lender": lender, "H": H, "mu": mu, "c": c, **ch["E2_3"]})
        self.e24.append({"lender": lender, "H": H, "mu": mu, "c": c, **ch["E2_4"]})
        self.e25.append({"lender": lender, "H": H, "mu": mu, "c": c, **ch["E2_5"]})
        hstar_s = (cell.get("row") or {}).get("H_star_mu_s")
        alpha_k = (cell.get("row") or {}).get("alpha_k")
        bl = {"layers": 0, "sum_dp": 0.0, "sum_fallback": 0.0, "dp_status_ok": True}
        for series, s in d["series"].items():
            for sched in d["schedules"]:
                pv = {"alg": {}, "alg_band": {}, "dp_band": 0.0, "dp_all": 0.0, "bl0a": 0.0, "bl0a_band": 0.0,
                      "demand_h": 0.0, "comp": {}, "n_dp_excluded": 0, "ok": True}
                rule_ok = {r: True for r in RULES}
                for L in s["layers"]:
                    pv["bl0a"] += L["bl0a"]
                    pv["demand_h"] += L["demand_load_h"]
                    ls = L.get(sched) or {}
                    dpv = (ls.get("dp") or {}).get("value")
                    if L["bandless"]:
                        if dpv is not None:
                            pv["dp_all"] += dpv
                        if sched == "trace":
                            bl["layers"] += 1
                            bl["sum_fallback"] += L["bl0a"]
                            if dpv is None:
                                bl["dp_status_ok"] = False
                            else:
                                bl["sum_dp"] += dpv
                            self.bandless_all.append({"lender": lender, "H": H, "mu": mu, "c": c, "series": series,
                                                      "k": L["k"], "dp": dpv, "fallback": L["bl0a"]})
                        for r in RULES:
                            pv["alg"][r] = pv["alg"].get(r, 0.0) + L["bl0a"]
                            cc = pv["comp"].setdefault(r, {k: 0.0 for k in COMPONENT_KEYS})
                            for k, v in _comp_fallback(L["bl0a"]).items():
                                cc[k] += v
                        continue
                    rules = ls.get("rules") or {}
                    for r in POLICY_RULES:
                        x = _resolve(rules, r)
                        if x is None:
                            rule_ok[r] = False
                            continue
                        pv["alg"][r] = pv["alg"].get(r, 0.0) + x["total"]
                        cc = pv["comp"].setdefault(r, {k: 0.0 for k in COMPONENT_KEYS})
                        for k, v in _comp(x).items():
                            cc[k] += v
                        if dpv is not None:
                            pv["alg_band"][r] = pv["alg_band"].get(r, 0.0) + x["total"]
                    pv["alg"]["bl0a"] = pv["alg"].get("bl0a", 0.0) + L["bl0a"]
                    cc = pv["comp"].setdefault("bl0a", {k: 0.0 for k in COMPONENT_KEYS})
                    for k, v in _comp_fallback(L["bl0a"]).items():
                        cc[k] += v
                    if dpv is None:
                        pv["n_dp_excluded"] += 1
                    else:
                        pv["dp_band"] += dpv
                        pv["dp_all"] += dpv
                        pv["alg_band"]["bl0a"] = pv["alg_band"].get("bl0a", 0.0) + L["bl0a"]
                for r, ok in rule_ok.items():
                    if not ok:
                        pv["alg"].pop(r, None)
                        pv["alg_band"].pop(r, None)
                        pv["comp"].pop(r, None)
                self.pairs[(lender, H, mu, sched, c, series)] = pv
                # coincidences (trace): week totals per layer
                if sched == "trace":
                    for L in s["layers"]:
                        rules = (L.get("trace") or {}).get("rules") or {}
                        a = rules.get("a1")
                        if L["bandless"] or a is None:
                            continue
                        for r in ("prewarm", "cold"):
                            x = rules.get(r)
                            if x is None:
                                continue
                            st = self.coinc.setdefault((lender, H, mu, c, r), [0, 0, False])
                            st[0] += 1
                            if "same_as" not in x:
                                st[2] = True
                                if _rel_diff(x["total"], a["total"]) > REL_TOL:
                                    st[1] += 1
            # episodes (trace): a rule's value is its own where it ran, A1's in the layers where it takes A1's
            # values (same_as), missing elsewhere
            ep = s["episodes"]
            n = len(ep["layer"])
            if n == 0:
                continue
            layer_rules = {L["k"]: ((L.get("trace") or {}).get("rules") or {}) for L in s["layers"]}
            lay = np.asarray(ep["layer"], dtype=np.int64)
            opt = _arr(ep["opt"])
            ok = np.isfinite(opt) & (opt > 0)
            av = _arr(ep["alg"]["a1"]) if "a1" in ep["alg"] else None
            for r in RULES:
                if r == "bl0a":
                    vals, ranmask = _arr(ep["bl0a"]), np.ones(n, dtype=bool)
                else:
                    vals, ranmask = np.full(n, np.nan), np.zeros(n, dtype=bool)
                    if r in ep["alg"]:
                        v = _arr(ep["alg"][r])
                        ranmask = np.isfinite(v)
                        vals[ranmask] = v[ranmask]
                    if av is not None:
                        for k, rules in layer_rules.items():
                            x = rules.get(r)
                            if x is not None and "same_as" in x:
                                m = (lay == k) & ~ranmask
                                vals[m] = av[m]
                m = ok & np.isfinite(vals)
                if not m.any():
                    continue
                self.eps.setdefault((lender, H, mu, c, r), []).append(vals[m] / opt[m])
                self.ran[(lender, H, mu, c, r)] = self.ran.get((lender, H, mu, c, r), False) or bool(ranmask.any())
                if r in ("prewarm", "cold") and av is not None and ranmask.any():
                    mm = m & ranmask & np.isfinite(av)
                    st = self.coinc.setdefault((lender, H, mu, c, r), [0, 0, False])
                    st[0] += int(mm.sum())
                    st[1] += int(np.sum(np.abs(vals[mm] - av[mm]) > REL_TOL * np.maximum(1.0, np.abs(av[mm]))))
                    st[2] = True
            if av is not None and hstar_s is not None and alpha_k is not None and H * 60.0 >= float(hstar_s):
                m = ok & np.isfinite(av)
                st = self.e27.setdefault((lender, H, mu), [0, 0])
                st[0] += int(m.sum())
                st[1] += int(np.sum(av[m] / opt[m] > 2.0 - float(alpha_k)))
        if abs(mu - 1.0) <= 1e-12:
            self.bandless[(lender, H, c)] = bl


def _group_lenders(g: str) -> list:
    return groups()[g]


def _episodes_entry(C: _Collect, g: str, H: int, mu: float, r: str, alignments) -> dict:
    lenders = [l for l in _group_lenders(g)]
    arrs, cs, ls = [], set(), set()
    by_c = {}
    for l in lenders:
        for c in alignments:
            xs = C.eps.get((l, H, mu, c, r))
            if not xs:
                continue
            a = np.concatenate(xs)
            arrs.append(a)
            cs.add(c)
            ls.add(l)
            by_c.setdefault(c, []).append(a)
    if g == "spot" and len(ls) < 2:
        return _null(f"fewer than two spot pools with data at H = {H} min (M23)")
    if not arrs:
        return _null("no data (no A1 cell, or the job did not run)")
    e = agg(np.concatenate(arrs))
    ran = any(C.ran.get((l, H, mu, c, r), False) for l in ls for c in cs)
    e.update(n_alignments=len(cs), alignments=sorted(cs), n_lenders=len(ls), ran=bool(ran))
    if not ran:
        e["ran_note"] = "the rule coincides with A1 here and takes A1's values (Q42 (a), M22)"
    e["by_alignment"] = {num(c): agg(np.concatenate(v)) for c, v in sorted(by_c.items())}
    return e


def _totals_entry(C: _Collect, g: str, H: int, mu: float, sched: str, r: str, alignments, series) -> dict:
    lenders = _group_lenders(g)
    rows = []
    for l in lenders:
        for c in alignments:
            for s in series:
                pv = C.pairs.get((l, H, mu, sched, c, s))
                if pv is None or r not in pv["alg"]:
                    continue
                rows.append((l, c, pv))
    ls = {l for l, _, _ in rows}
    if g == "spot" and len(ls) < 2:
        return _totals_null(f"fewer than two spot pools with data at H = {H} min (M23)")
    if not rows:
        return _totals_null("not run under eager at mu != 1 (§6.4)" if sched == "eager" and r in ("cold", "prewarm")
                            else "no data (no A1 cell, or the job did not run)")

    def fields(rr):
        co = [pv["alg"][r] / pv["bl0a"] for _, _, pv in rr if pv["bl0a"] > 0]
        wt = [pv["alg_band"][r] / pv["dp_band"] for _, _, pv in rr if r in pv["alg_band"] and pv["dp_band"] > 0]
        cd = [pv["alg"][r] / pv["demand_h"] for _, _, pv in rr if pv["demand_h"] > 0]
        comp = {k: float(np.median([pv["comp"][r][k] for _, _, pv in rr])) for k in COMPONENT_KEYS}
        cob = {k: float(np.median([pv["comp"][r][k] / pv["bl0a"] for _, _, pv in rr if pv["bl0a"] > 0]))
               for k in COMPONENT_KEYS} if any(pv["bl0a"] > 0 for _, _, pv in rr) else None
        f = {"cost_over_bl0a": agg_median(co), "whole_trace_ratio": agg_median(wt),
             "cost_per_demand_h": agg_median(cd),
             "components": comp, "components_over_bl0a": cob, "n_pairs": len(rr),
             "n_dp_excluded": int(sum(pv["n_dp_excluded"] for _, _, pv in rr))}
        if cob is None:
            f["components_over_bl0a_note"] = "BL0a is 0"
        return f
    e = fields(rows)
    cs = sorted({c for _, c, _ in rows})
    e.update(n_alignments=len(cs), alignments=cs, n_lenders=len(ls))
    e["by_alignment"] = {num(c): fields([x for x in rows if x[1] == c]) for c in cs}
    return e


def _alignments_of(mu: float, sched: str) -> tuple:
    S = settings()
    return tuple(S["alignments"]) if (abs(mu - 1.0) <= 1e-12 and sched == "trace") else (1,)


def _status(ok: bool) -> str:
    """A check's status from its pass condition ('pass' or 'fail'; the summary sets 'missing' where nothing was
    checked)."""
    return "pass" if ok else "fail"


def check_e2_1(rows: list) -> dict:
    """E2-1: the game's rows at mu = 1, lambda = inputs.lambda_default, Hs in H_BASE against por_default.json
    table_por_switch_beta (exact to 1e-12)."""
    gi = game_inputs()
    ref = {float(r["Hs"]): float(r["CR"]) for r in por()["table_por_switch_beta"]
           if float(r["mu"]) == 1.0 and float(r["lam"]) == gi["LAM"]}
    got = {float(r["Hs"]): float(r["CR"]) for r in rows
           if r["switch"] == "beta" and float(r["mu"]) == 1.0 and float(r["lam"]) == gi["LAM"]}
    out = []
    for h in h_base():
        v = got.get(h)
        out.append({"Hs": h, "CR": v, "CR_ref": ref.get(h), "diff": None if v is None else abs(v - ref[h])})
    diffs = [x["diff"] for x in out if x["diff"] is not None]
    missing = [x["Hs"] for x in out if x["CR"] is None]
    return {"rows": out, "max_abs_diff": max(diffs) if diffs else None, "missing_Hs": missing,
            "tolerance": E2_1_TOL, "pass": bool(diffs) and not missing and max(diffs) <= E2_1_TOL,
            "file": "code/theory_checks/c2/out/por_default.json (table_por_switch_beta)"}


def summary(out) -> dict:
    out = Path(out)
    S = settings()
    recs = mc.read_records(out)
    js = jobs()
    ok = {j.id for j in js if (recs.get(j.id) or {}).get("status") == "ok"}
    C = _Collect()
    for j in js:
        if j.params["part"] != "cell" or j.id not in ok:
            continue
        p = j.params
        path = cell_run_path(out, p["lender"], p["H"], p["mu"], p["c"])
        d = mc.read_json(path)
        if d is not None:
            C.add(d)
            del d
    # the game, the joint MILPs and the E2-5 MILPs
    game_rows, game_failed = [], {}
    for j in js:
        if j.params["part"] == "game" and j.id in ok:
            d = mc.read_json(out / "runs" / "game" / mc.job_file_name(j.id))
            if d:
                game_rows += d["rows"]
                if d.get("failed_Hs"):
                    game_failed[j.id] = d["failed_Hs"]
    game_rows.sort(key=lambda r: (r["switch"], r["mu"], r["lam"], r["Hs"]))
    game = {"meta": {**game_meta(), "git_revision": mc.git_revision(), "written": mc._now(),
                     "jobs_missing": [j.id for j in js if j.params["part"] == "game" and j.id not in ok],
                     "cells_failed": game_failed},
            "rows": game_rows}
    mc.dump_json(game, out / "game.json")
    joint = joint_rows(out, js, recs)
    mc.dump_json({"meta": {"spec": "design/sim_spec_ms3.md §6.5 (E2-6, M46)", "git_revision": mc.git_revision(),
                           "written": mc._now(), "milp_limit_s": mc.milp_limit_s()}, "rows": joint},
                 out / "joint_milp.json")
    epm = [mc.read_json(out / "runs" / "ep_milp" / mc.job_file_name(j.id)) for j in js
           if j.params["part"] == "ep_milp" and j.id in ok]
    epm = [x for x in epm if x and "episode" in x]

    G = groups()
    Hs, MUs = S["H"], S["mu"]
    episodes, totals, best, coinc, cold_eq, cdetail = {}, {}, {}, {}, {}, {}
    for g in G:
        for H in Hs:
            for mu in MUs:
                for r in RULES:
                    episodes.setdefault(g, {}).setdefault(num(H), {}).setdefault(num(mu), {})[r] = \
                        _episodes_entry(C, g, H, mu, r, _alignments_of(mu, "trace"))
                for sched in SCHEDULES:
                    for r in RULES:
                        totals.setdefault(g, {}).setdefault(num(H), {}).setdefault(num(mu), {}) \
                            .setdefault(sched, {})[r] = _totals_entry(C, g, H, mu, sched, r,
                                                                      _alignments_of(mu, sched), S["series"])
                # coincidences (trace)
                det = {}
                for r in ("prewarm", "cold"):
                    nc = nd = 0
                    ran_in, ls = [], set()
                    for l in G[g]:
                        for c in _alignments_of(mu, "trace"):
                            st = C.coinc.get((l, H, mu, c, r))
                            if st is None:
                                continue
                            nc += st[0]
                            nd += st[1]
                            ls.add(l)
                            if st[2]:
                                ran_in.append([l, c])
                    det[r] = {"n_compared": nc, "n_differ": nd, "ran_in": ran_in, "n_lenders": len(ls)}
                cdetail.setdefault(g, {}).setdefault(num(H), {})[num(mu)] = det
                for r, tgt in (("prewarm", coinc), ("cold", cold_eq)):
                    d = tgt.setdefault(g, {}).setdefault(num(H), {})
                    if det[r]["n_compared"] == 0:
                        mc.put(d, num(mu), None, "nothing compared (no cell of the group with data)")
                    elif g == "spot" and det[r]["n_lenders"] < 2:
                        mc.put(d, num(mu), None, f"fewer than two spot pools with data at H = {H} min (M23)")
                    else:
                        d[num(mu)] = det[r]["n_differ"] == 0
        for mu in MUs:
            for sched in SCHEDULES:
                for r in RULES:
                    cand = []
                    for H in Hs:
                        e = totals[g][num(H)][num(mu)][sched][r]
                        v = (e.get("cost_over_bl0a") or {}).get("median")
                        if v is not None:
                            cand.append((v, H, e["cost_over_bl0a"].get("median_ci95")))
                    tgt = best.setdefault(g, {}).setdefault(num(mu), {}).setdefault(sched, {})
                    if cand:
                        v, H, ci = min(cand, key=lambda t: (t[0], t[1]))
                        tgt[r] = {"H": H, "H_min": H, "cost_over_bl0a": v, "median_ci95": ci}
                    else:
                        tgt[r] = _best_H_null("no H with a value")
    bandless = {}
    for (l, H, c), b in sorted(C.bandless.items()):
        bandless.setdefault(l, {}).setdefault(num(H), {})[num(c)] = b
    # checks
    e23_all = [x for x in C.e23 if abs(x["mu"] - 1.0) <= 1e-12]
    e23 = {"n_cells": len(e23_all), "n_compared": int(sum(x["n_compared"] for x in e23_all)),
           "n_compared_week": int(sum(x.get("n_compared_week", 0) for x in e23_all)),
           "n_compared_episodes": int(sum(x.get("n_compared_episodes", 0) for x in e23_all)),
           "max_abs_diff_a1_cold": max((x["max_abs_diff_a1_cold"] for x in e23_all), default=None),
           "max_abs_diff_insured": max((x["max_abs_diff_insured"] for x in e23_all), default=None),
           "violations": [v for x in e23_all for v in x["violations"]][:50], "tolerance_usd": REL_TOL}
    e23["pass"] = not e23["violations"] and e23["n_compared"] > 0
    e23b_v = [x for x in C.bandless_all if x["dp"] is not None and x["dp"] > x["fallback"] + REL_TOL]
    e23b = {"n_bandless": len(C.bandless_all),
            "max_dp_minus_fallback": max((x["dp"] - x["fallback"] for x in C.bandless_all if x["dp"] is not None),
                                         default=None),
            "n_dp_missing": sum(1 for x in C.bandless_all if x["dp"] is None), "violations": e23b_v[:50],
            "pass": not e23b_v}
    keys4 = ("n_runs", "n_invariant_failures", "n_gpu_only_lease_slots", "n_dp", "n_dp_not_optimal",
             "n_dp_domain_error")
    e24 = {k: int(sum(x.get(k, 0) for x in C.e24)) for k in keys4}
    e24["examples"] = [dict(lender=x["lender"], H=x["H"], mu=x["mu"], c=x["c"], **ex) for x in C.e24
                       for ex in x.get("examples", [])][:30]
    e24["pass"] = (e24["n_invariant_failures"] == 0 and e24["n_gpu_only_lease_slots"] == 0
                   and e24["n_dp_not_optimal"] == 0 and e24["n_dp_domain_error"] == 0)
    below = [dict(lender=x["lender"], H=x["H"], mu=x["mu"], c=x["c"], **b) for x in C.e25 for b in x["below"]]
    mins = [x["min_ratio"] for x in C.e25 if x["min_ratio"] is not None]
    resolved = {(m["episode"]["job"], m["episode"]["series"], m["episode"]["layer"], m["episode"]["f_a"]): m
                for m in epm}
    cand_keys = []
    for b in below:
        jid = cell_job_id(b["lender"], b["H"], b["mu"], b["c"])
        key = (jid, b["series"], b["layer"], b["f_a"])
        if key not in cand_keys:
            cand_keys.append(key)
    unresolved = [list(k) for k in cand_keys if k not in resolved]
    verdicts = [v["verdict"] for m in epm for v in m.get("rules", [])]
    # an E2-5 job that saw another candidate list than the cell records give now (a cell job reran after it, e.g.
    # under MS3_RESUME=1, which skips the job's 'ok' record)
    n_cand = len(ep_milp_candidates(out))
    stale = []
    for j in js:
        if j.params["part"] == "ep_milp" and j.id in ok:
            d = mc.read_json(out / "runs" / "ep_milp" / mc.job_file_name(j.id))
            if d is not None and d.get("n_candidates") != n_cand:
                stale.append(j.id)
    e25 = {"n_episodes": int(sum(x["n_episodes"] for x in C.e25)), "min_ratio": min(mins) if mins else None,
           "n_below": int(sum(x["n_below"] for x in C.e25)), "below": below[:50],
           "milp": [{"episode": m["episode"], "dp": (m.get("dp") or {}).get("value"), "incumbent": m.get("incumbent"),
                     "dual_bound": m.get("dual_bound"), "LB": m.get("LB"), "rules": m.get("rules")} for m in epm],
           "unresolved": unresolved, "tolerance": REL_TOL, "n_candidates": n_cand, "ep_milp_stale": stale}
    if stale:
        e25["ep_milp_stale_note"] = ("these E2-5 jobs ran on another candidate list than the cell job records give "
                                     "now: rerun them without MS3_RESUME")
    e25["pass"] = e25["n_below"] == 0 or (not unresolved and not stale
                                          and all(v.startswith("explained") for v in verdicts))
    e27 = {}
    for g in G:
        n_e = n_a = 0
        for (l, H, mu), (a, b) in C.e27.items():
            if l in G[g]:
                n_e += a
                n_a += b
        e27[g] = {"n_at_or_above_hstar": n_e, "n_above_2_minus_alpha": n_a}
    rows_e1 = [r for r in game_rows]
    n_rows = len({(x["lender"], x["H"], x["mu"]) for x in C.e23})
    # the kind 'alpha>=1' (the cell does not run, §6.2) of every s5_tau5_H* row against its alpha_k
    alpha_kind = [{"lender": l, "H": h, "mu": m, "kind": r["kind"], "alpha_k": r["alpha_k"]}
                  for (l, h, m), r in sorted(_rows().items())
                  if (r["kind"] == "alpha>=1") != (float(r["alpha_k"]) >= 1.0)]
    e21 = check_e2_1(rows_e1)
    e22 = {"a": {"n_rows": n_rows, "mismatches": C.e22a, "n_rows_alpha_kind": len(_rows()),
                 "alpha_kind_mismatches": alpha_kind, "pass": not C.e22a and not alpha_kind},
           "b": {"n_cells": C.n_e22, "differences": C.e22b[:200], "n_differences": len(C.e22b),
                 "informative": True}}
    has_cells = bool(C.e23)
    e21["status"] = "missing" if e21["missing_Hs"] else _status(e21["pass"])
    e22["status"] = _status(e22["a"]["pass"]) if n_rows else "missing"
    e23["status"] = _status(e23["pass"]) if e23["n_compared"] else "missing"
    e23b["status"] = _status(e23b["pass"]) if has_cells else "missing"
    e24["status"] = _status(e24["pass"]) if e24["n_runs"] else "missing"
    if not e25["n_episodes"]:
        e25["status"] = "missing"
    elif not e25["n_below"]:
        e25["status"] = "pass"
    elif unresolved or stale:
        e25["status"] = "pending"
    else:
        e25["status"] = "explained" if e25["pass"] else "fail"
    e26 = {"rows": [{k: x.get(k) for k in ("lender", "series", "H", "sum_dp", "LP", "dual_bound", "incumbent", "gap",
                                         "LB", "LB_source", "ratio_sum_dp_over_LB", "milp_status")} for x in joint],
           "informative": True, "status": "informative"}
    e27 = {"by_group": e27, "informative": True, "status": "informative",
           "note": "A1's per-episode ratio above 2 - alpha_k at H >= H*_mu of the cell's e2_reactions row "
                   "(C2-SW formula, CONJECTURE); not a bug on trace episodes (design E2 reading)"}
    checks = {k: {"status": e["status"], "claim": CHECK_CLAIMS[k], **e}
              for k, e in (("E2-1", e21), ("E2-2", e22), ("E2-3", e23), ("E2-3b", e23b), ("E2-4", e24),
                           ("E2-5", e25), ("E2-6", e26), ("E2-7", e27))}
    meta = {"exp": EXP, "spec": SPEC, "git_revision": mc.git_revision(), "versions": mc.versions(),
            "written": mc._now(), "reduced": S["reduced"],
            "settings": {k: (list(v) if isinstance(v, tuple) else v) for k, v in S.items()},
            "cells": [[l, h] for l, h in cells()], "cells_without_sites": [[l, h] for l, h in cells_without_sites()],
            "cells_without_sites_note": "offered with alpha_k < 1 in e2_reactions, but the instance builder gives "
                                        "the lender no layer site (sim_spec §4.3 step 2, §10 S35); no job runs",
            "groups": G, "maas_quartiles": maas_quartiles(),
            "spot_pools_by_H": {num(h): v for h, v in spot_pools_by_H().items()}, "status_labels": STATUS_LABELS,
            "rules": {"a1": "A1 (ALG*, the design default)", "cold": "A1, reaction cold (always cold)",
                      "prewarm": "A1, reaction prewarm_if_feasible (pre-warm if H >= lambda)",
                      "bl6": "BL6 around A1 (notice-oblivious)", "bl0a": "all-fallback, analytic"},
            "sources": {"reactions": "code/sim/out/ms2_checks/e2_reactions.json",
                        "calibration": "code/analysis/out/a11_calibration.json",
                        "series": "code/analysis/out/a12_sim_inputs.json",
                        "game": "code/theory_checks/c2/out/por_default.json"},
            "jobs_ok": len(ok), "jobs_missing": [j.id for j in js if j.id not in ok]}
    summ = {"meta": meta, "episodes": episodes, "totals": totals, "best_H": best, "coincide": coinc,
            "cold_equals_a1": cold_eq, "coincide_detail": cdetail, "bandless": bandless, "checks": checks}
    mc.dump_json(summ, out / "summary.json")
    mc.write_text(tables(summ, game), out / "tables.md")
    return summ


def tables(summ: dict, game: dict) -> str:
    """tables.md: the summary as markdown tables (§2.6)."""
    S = settings()
    out = ["# E2: the value and price of notice (design/sim_spec_ms3.md §6)", ""]
    for g in ("maas", "spot"):
        out.append(f"## Per-episode ALG/OPT, `trace`, mu = 1, group {g} (median [P95], n)")
        hdr = ["H (min)"] + list(RULES)
        rows = []
        for H in S["H"]:
            e = summ["episodes"][g][num(H)].get(num(1.0), {})
            rows.append([H] + [("–" if (e.get(r) or {}).get("median") is None else
                                f"{e[r]['median']:.4g} [{e[r]['p95']:.4g}], {e[r]['n']}") for r in RULES])
        out += [mc.md_table(hdr, rows), ""]
    for g in ("maas", "spot"):
        out.append(f"## Total cost / BL0a, `trace`, mu = 1, group {g} (median over pairs, n)")
        rows = []
        for H in S["H"]:
            e = summ["totals"][g][num(H)].get(num(1.0), {}).get("trace", {})
            rows.append([H] + [("–" if (e.get(r, {}).get("cost_over_bl0a") or {}).get("median") is None else
                                f"{e[r]['cost_over_bl0a']['median']:.4g}, {e[r]['n_pairs']}") for r in RULES])
        out += [mc.md_table(["H (min)"] + list(RULES), rows), ""]
    out.append("## Checks")
    rows = []
    for k, v in summ["checks"].items():
        if k == "E2-2":
            rows.append(["E2-2 (a)", v["status"]])
            rows.append(["E2-2 (b)", f"informative, {v['b']['n_differences']} differences"])
        else:
            rows.append([k, v["status"]])
    out += [mc.md_table(["check", "status"], rows), ""]
    out.append(f"## C2 game rows: {len(game['rows'])}")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=argv, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
