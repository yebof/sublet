"""E4: predictions (design/sim_spec_ms4.md §6; deliverable D34, unit U23; open choices M9-M14, M37).

E4 runs A5 (the psi-interpolated fractional PDs and the doubling combiner), A6 with predictions (A5's combiner and the
handler's test (a)) and A6 without predictions (the week reference) on E1's trace instance with one series borrower
per panel, under E4's 13 predictions of the demand (drivers/perturb.py: the previous-day predictor, its phase,
amplitude and burst perturbations, the empty and the exact prediction). The predicted plan P-hat (the OPT_eager plan
of each predicted day, drivers.predict.plan_daily with method 'auto') is computed once per (panel, alignment,
prediction, day), and per mu at the default point, by its own MILP job, and every run gets it through the driver
inputs pred_cols and pred_demand (`given`), so that no run re-solves it (M14). On the ratio day d* of each (panel,
alignment) (M13) A5's runs are bounded from below by Q39's rule against OPT_eager of that day (ms3_common.lb_record),
and the x of the figure sf_e4 is q eta_{d*} / LB_eager (§6.8, perturb.eta_q). The fractional PDs (the psi-PDs and A2's
plain PD) are costs of the PDs' covering program over the aligned columns, which counts no capacity (the psi-PDs get
every active unit as a request of its client without layering, algos/a5.py), not of the full model that OPT_eager
prices; so each fractional series is also given over LP_core, the LP of that program on the ratio day
(drivers.predict.aligned_lp, R7's LPal on the core), next to Q39's LB (§6.6). Sublet is not in E4 (plan decision 8).

Status labels (copied from §6.1, never upgraded): C3-T9 (PROVEN; numerically checked): the psi-PD has consistency
2 / (1 - psi) and robustness 2 ln(1 + (mK + 2) / psi); C3-T11 (PROVEN; numerically checked): the combiner satisfies
ALG <= 5.83 min{C_FP, C_R} pathwise; C3-L10 (PROVEN; numerically checked): c(P-hat(sigma)) <= OPT_eager(sigma) + q eta
for P-hat = OPT_eager(sigma-hat); O2, integral consistency 1 + O(psi), CONJECTURE. The trace instances are no exact
core exports, so their ratios are diagnostics (E4-5).

Instance (§6.3, M10): configs/bench_e1.json with e1.MENU (time.fast_slot_min 5, the slow grid; s5_tau5_H60,
s5_tau60_H0, protected), llms [M], time.horizon_min 10080 (one week), one series borrower per panel ({id <panel>0,
series, week_index 0, tier M, region north_america}, own_capacity_quantile 75, smoothing_min 15, market_tightness
0.5), the trace lender with I1, 'sell' and violations absorbed, engine.check_invariants true and
stranding.mu_over_beta_tilde mu (1; and 0.2, 0.5, 2 at the default point, the unperturbed previous-day prediction);
alignments c in {1, 2} (config seed = lender seed = c), policy seeds {0, 1, 2}. Panels:
  azure     azure2024_conv week 0
  burstgpt  burstgpt_2__ChatGPT__api week 0
Every run routes on the slow grid, the week runs too (a departure from design §5.2.4's 1-min routing of
system-facing cost runs, M10, §13 item 4), so that the ratio-day instance restrict_horizon(week, d* 288, 288) shares
its benchmark's model and one P-hat cache serves the week and the ratio day.

Jobs (§6.5, §6.7; job ids by ms3_common.job_id, numbers as num_key; prediction keys of perturb.PREDICTIONS, 'none'
for A6 without predictions):
  milp  e4:phat:panel=P:c=C:mu=U:pred=X:day=D   P-hat of day D (1-6): plan_daily(method 'auto') on
                                                restrict_horizon(week, (D - 1) 288, 2 288) with that window's
                                                prediction, the S36 gate and the override bench.time_limit_s =
                                                ms3_common.milp_limit_s() (plan_daily reads its limit there; the LP
                                                substitute's rounding draws from config.rng_streams(seed)['bench'], as
                                                the measurement script did); a day whose prediction is zero records an
                                                empty plan (method 'none', no MILP) -> runs/phat/<job>.json (the
                                                window's columns), lb/phat/panel=P/c=C/mu=U/pred=X/day=D.json
  milp  e4:eager:panel=P:c=C                    OPT_eager of the ratio day by MILP (solve_eager, time_limit_s =
                                                milp_limit_s(), mip_rel_gap 1e-4, slow grid), its LP (solve_lp of the
                                                eager schedule) and LP_core (aligned_lp of the day), both LPs written
                                                as soon as they are solved, so that a wall-limit kill leaves the LP as
                                                Q39's LB -> lb/eager/panel=P/c=C/lp.json, lp_core.json, milp.json
  pool  e4:pcols:panel=P:c=C:mu=U:pred=X        the six days' columns, start slots shifted by (D - 1) 288, with the
                                                day records and the week instance's hash -> runs/pcols/<job>.json (an
                                                error unless every day job's record is 'ok')
  pool  e4:week:panel=P:c=C:mu=U:pred=X         the week runs of A5 and A6-pred (pred=none: A6 without predictions)
                                                at every policy seed -> runs/week/<job>.json
  pool  e4:ratio:panel=P:c=C:pred=X             A5 on the ratio day at every policy seed (mu = 1), with q eta_{d*}
                                                -> runs/ratio/<job>.json
  pool  e4:repro                                E4-1: repro_c5_la.main(['--workers', '1', '--out', <out>/repro]) with
                                                the job's absolute out folder (its JSON files record no git revision,
                                                C20), then the comparison with R7's reference files ->
                                                repro/, repro_check.json
Grid: P-hat at mu = 1 for the 13 predictions and at mu in {0.2, 0.5, 2} for 'prev': 6 days x (2 x 2 x 13 + 2 x 2 x 3)
= 384 MILP jobs; 4 eager MILP jobs; 64 pcols jobs; 80 week jobs (2 x 2 x 14 at mu = 1, 2 x 2 x 3 x 2 at the other
mu: 432 runs); 52 ratio jobs (156 runs); e4:repro. run_e4.sh runs the MILP jobs, then a filtered pool pass of the
e4:pcols jobs, then the other pool jobs (whose week and ratio jobs read runs/pcols/), the manifest and the summary.
Tags (registry id, parameters; style keys of §6.6, §8.2):
  A5       A5 {"psi_list": [0.1, 0.3, 0.5]}   psi_01, psi_03, psi_05 (report psi[i].P), a2_frac (report P, psi = 1),
                                              a5 (the combiner's run, engine total)
  A6-pred  A6 {"predictions": true}           extract only
  A6       A6 {}                              extract only (the week reference)
Ratio day (M13): per (panel, alignment) the first day d* >= 1 whose previous day has demand (ratio_day: Azure day 2,
BurstGPT day 1); the ratio-day runs get the cached columns of day d*, shifted by -d* 288, and the prediction of that
day, at mu = 1 only (§1.5 item 12).

Reduced job list (smoke runs and tests): MS3_E4_REDUCED=1 (run_e4.sh --reduced sets it, with MS3_MILP_LIMIT 10 s
unless set) keeps both panels, alignment 1, policy seed 0, the predictions REDUCED['predictions'] (one per kind),
mu = 1 and the default point at mu = 2 only, on 2-hour "days" (24 slow slots) of the window restrict_horizon(week,
444, 72): three days from 13:00 of day 1 (the measurement script's smoke window; Azure has no overflow on day 0 of the
week), so that P-hat has days 1 and 2. e4:repro is unchanged. Default (unset or 0): the full lists above.

Outputs under out/e4/ (§6.10, §2.6): runs/ (not versioned: phat/, pcols/, week/, ratio/), lb/ (versioned: phat/ and
eager/), repro/ (E4-1's outputs, no git revision, C20), repro_check.json, summary.json, tables.md, manifest.json,
jobs/, logs/, run_e4.log.

summary.json (keys of §6.10; <panel> azure | burstgpt, <c> "1" | "2", <mu> "1" | "0.2" | "0.5" | "2", <pred> the
prediction keys; ratio, week and combiner hold every path of the design grid, a value the runs did not produce is null
with a '<key>_note'; phat and eager list the jobs of the run's grid):
  meta                          exp, spec, git_revision, written, reduced (reduced_note), config, menu, llms,
                                horizon_min, lender_model, panels, alignments (and _design), policy_seeds (and
                                _design), mu_main, mu_points (and _design), predictions {key: label} (the 13 and
                                'none'), predictions_run, tags, series, ratio_day.<panel>.<c> (d*), day_slots, window,
                                milp {limit_s, mip_rel_gap, grid}, combiner_bound, status_labels, jobs {n, by_status,
                                not_ok}, ignored_outputs (outputs present whose job record is not 'ok': not used, §2.4)
  phat.<panel>.<c>.<mu>.<pred>  days.<D> {method ('milp', 'lp_round' or 'none': an empty plan), status, objective,
                                gap, LB, incumbent, exact, n_cols, wall_s}, n_cols, methods {milp, lp_round, none},
                                assembled (the e4:pcols record is 'ok') (E4-4)
  eager.<panel>.<c>             OPT_eager of the ratio day: ms3_common.bench_values of its LP and MILP (LB = max(LP,
                                dual bound), LB_source, incumbent, gap, exact, lp_status, milp_status, grid) with LP,
                                dual_bound, d_star, instance_hash, time_limit_s, size, LP_core and LP_core_status; the
                                LP files are used if the job's record is 'ok', 'wall_limit' or 'oom_at_3G' (§2.5),
                                else listed in meta.ignored_outputs; a record whose instance hash differs from the
                                ratio runs' is not used (status 'stale')
  ratio.<panel>.<pred>.<series> x (median over the alignments of q eta_{d*} / LB_eager, §6.8), x_by_c, eta_q_by_c,
                                LB_by_c, ratio_LB and ratio_inc (metrics.aggregate of ALG / LB and ALG / incumbent
                                over 2 alignments x 3 seeds), the flat copies median, median_ci95, inc_median, n_runs,
                                style_key, label, cost_model ('pd_covering' or 'full'); for the fractional series
                                ratio_core (aggregate of ALG / LP_core), core_median, core_median_ci95, x_core (median
                                over the alignments of q eta_{d*} / LP_core), x_core_by_c, LP_core_by_c (null with
                                notes for a5); series psi_01, psi_03, psi_05 (A5's psi[i].P), a2_frac (P) and a5
                                (engine total)
  week.<panel>.<mu>.<pred>.<tag>  cost_over_a6 (aggregate of the week cost over A6 without predictions of the same
                                (panel, alignment, mu, seed)), median, median_ci95, n_pairs, cost_usd (aggregate),
                                mean_cost_usd, n_runs; tags A5 and A6-pred; week.<panel>.<mu>.none.A6 holds the
                                reference's cost_usd, mean_cost_usd and n_runs (E4-6)
  combiner.<panel>.<pred>.<tag> n, C_FP_mean, C_R_mean, accounted_total_mean, real_over_min (aggregate of the engine
                                total over min{C_FP, C_R}), max_real_over_min, n_above_bound (> 5.83), switches_mean;
                                tags A5 and A6-pred (the week runs at mu = 1) and A5-day (the ratio-day runs) (E4-5)
  core_export                   per instance (<panel>:c=<c>:mu=<mu> for a week, <panel>:c=<c>:day for a ratio day):
                                exact, exportable, notes, or why for 'not exportable' (E4-5)
  checks.E4-1 ... E4-6          status 'pass' | 'fail' | 'informative' | 'missing' with claim and inputs (§6.9);
                                E4-2's bracket: per ratio-day (panel, alignment, prediction) ms3_common.bracket of
                                P-hat's day record over OPT_eager with bound 1 + x, refuted (lo > 1 + x) and confirmed
                                (hi <= 1 + q eta / incumbent_eager)
repro_check.json: files.<reference> {got, lines_equal, n_lines_got, n_lines_ref, first_diffs} for c5_la.txt and
  c5_la_nearest.txt (code/theory_checks/c3/out/); json.<reference> {max_rel_diff, n_compared, n_mismatch, mismatches}
  against c5_la.json and c5_la_nearest.json; core_eta {n_rows, n_eta_chk_false, rows_false} (C3-L10 on the core);
  quick; pass (both text files equal line by line and not quick); meta.

Command line (ms3_common.main, §2.4), run from code/sim through run_e4.sh (ms3_lib.sh):
  python -m sublet.experiments.e4 --list | --job ID | --summary | --estimate | --manifest  [--out DIR]
--estimate uses the constants of §11.1: a MILP job at the limit + 60 s; a week run of A5 19.5 s, of A6 6.0 s; a
ratio-day run 7.5 s (Azure) and 6.7 s (BurstGPT), A5's measured week time times the ratio day's share of the week's
overflow; 1 s per job for the build; e4:repro 251.4 s (the summed instance times of
code/sim/out/ms2_checks/c5_la_repro.json).
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

from ..drivers import perturb
from . import ms3_common as mc
from .ms3_common import Job, job_id, num_key, put

EXP = "e4"
SPEC = "design/sim_spec_ms4.md §6"
CONFIG = "bench_e1.json"
WEEK_MIN = 10080
DAY_MIN = 1440
PANELS = {"azure": {"series": "azure2024_conv", "week_index": 0},
          "burstgpt": {"series": "burstgpt_2__ChatGPT__api", "week_index": 0}}
REGION, TIER = "north_america", "M"
LLM_M = {"id": "M", "catalog": "maas_a10", "entry": "M", "kappa_mult": 1.0}
BORROWERS = {"own_capacity_quantile": 75, "smoothing_min": 15, "market_tightness": 0.5}
LENDER_MODEL = {"schedule": "trace", "information": "I1", "on_unavailable": "sell", "violations": "absorb"}
MU_MAIN = 1.0
MU_POINTS = (0.2, 0.5, 2.0)
DEFAULT_PRED = "prev"                  # the default point of the mu points: the unperturbed previous-day prediction
ALIGNMENTS = (1, 2)                    # config seeds = lender seeds
POLICY_SEEDS = (0, 1, 2)
PSI_LIST = (0.1, 0.3, 0.5)
TAGS = {"A5": ("A5", {"psi_list": list(PSI_LIST)}),
        "A6-pred": ("A6", {"predictions": True}),
        "A6": ("A6", {})}
PRED_TAGS = ("A5", "A6-pred")
REF_TAG = "A6"
DAY_TAG = "A5-day"                     # the combiner entries of the ratio-day runs
SERIES = ("psi_01", "psi_03", "psi_05", "a2_frac", "a5")           # style keys of sf_e4 (§6.6, §8.2)
PSI_SERIES = dict(zip(SERIES[:3], PSI_LIST))
FRAC_SERIES = SERIES[:4]               # costs of the PDs' covering program (no capacity), also over LP_core (§6.6)
COMB_BOUND = 5.83                      # C3-T11's factor (gamma = 1 + 1 / sqrt 2)
BENCH_GRID = "slow"
MILP_GAP = 1e-4
TOL = 1e-9
REPRO_DIR = "repro"
REDUCED_ENV = "MS3_E4_REDUCED"
REDUCED = {"alignments": (1,), "policy_seeds": (0,), "mu_points": (2.0,),
           "predictions": ("prev", "phase30", "amp1.5", "del_p90", "inj3x30", "empty", "exact"),
           "window": (444, 72), "day_slots": 24}
# time constants of §11.1 (seconds; MS4-spec measurement 5, e4_pred_sizing_*_weekruns.json, and MS2's R7)
EST_BUILD_S = 1.0
EST_A5_WEEK_S = 19.5
EST_A6_WEEK_S = 6.0
# a ratio-day run of A5: its week time times the ratio day's share of the week's overflow (Azure 19.46 s x 141.05 /
# 365.60, BurstGPT 18.32 s x 123.08 / 338.11; e4_pred_sizing_<panel>_weekruns.json, _phat.json sizes.week): A5's time
# grows with the day's demand, and d* is a heavy day
EST_DAY_RUN_S = {"azure": 7.5, "burstgpt": 6.7}
EST_PCOLS_S = 1.0
EST_REPRO_S = 251.4
STATUS_LABELS = {"C3-T9": "PROVEN; numerically checked", "C3-T11": "PROVEN; numerically checked",
                 "C3-L10": "PROVEN; numerically checked", "O2": "CONJECTURE"}
CHECK_CLAIMS = {
    "E4-1": "job e4:repro reruns repro_c5_la and reproduces MS2 spec §17.3 R7 (c3/out/c5_la.txt (a) and (b), "
            "c5_la_nearest.txt) to its printed digits: E4's bug test of C3-T9 and C3-T11 (PROVEN; numerically "
            "checked) and the combiner on exact core instances",
    "E4-2": "C3-L10 (PROVEN; numerically checked): c(P-hat(sigma)) <= OPT_eager(sigma) + q eta; on the core every row "
            "of repro/c5_la_repro.json has eta_chk true (else a bug); on the trace ratio days the slack "
            "incumbent_eager + q eta + (incumbent_P-hat - LB_P-hat) - C_FP per run (C_FP counts no capacity, so "
            "the slack is lenient), and the bracket of P-hat's MILP (OPT_eager(sigma-hat)) over OPT_eager(sigma), "
            "whose end lo is tested against 1 + x (the lemma's step OPT_eager(sigma-hat) <= OPT_eager(sigma) + q "
            "eta, in the full model), reported",
    "E4-3": "every run: no invariant failure, no GPU-only lease slot; every ratio-day run: ratio_validity None "
            "(slow grid, violations absorbed)",
    "E4-4": "the method of each P-hat day (milp, lp_round, none) and the MILPs' statuses and gaps",
    "E4-5": "every A5 and A6-pred run: real cost over min{C_FP, C_R} against C3-T11's 5.83 (proven for the accounted "
            "cost on the core with eager accounting); each instance's core export (to_core with not_offered "
            "'big_m') with its exact and notes, or 'not exportable'; a bug only on an exact core export",
    "E4-6": "week cost of A5 and A6-pred over A6 without predictions of the same (panel, alignment, mu, seed), per "
            "(panel, prediction) (M37: reported as measured, no gain claimed)",
}


# ---------------------------------------------------------------- grid and jobs
def design() -> dict:
    """The job grid: the full grid of §6.3-§6.7, or the reduced one with MS3_E4_REDUCED=1 (module docstring)."""
    red = os.environ.get(REDUCED_ENV, "0") == "1"
    n_days = REDUCED["window"][1] // REDUCED["day_slots"] if red else WEEK_MIN // DAY_MIN
    return {"reduced": red, "panels": tuple(PANELS),
            "alignments": REDUCED["alignments"] if red else ALIGNMENTS,
            "policy_seeds": REDUCED["policy_seeds"] if red else POLICY_SEEDS,
            "mu_points": REDUCED["mu_points"] if red else MU_POINTS,
            "predictions": REDUCED["predictions"] if red else tuple(perturb.PREDICTIONS),
            "window": list(REDUCED["window"]) if red else None,
            "day_slots": REDUCED["day_slots"] if red else None, "n_days": n_days}


def mus(d: Optional[dict] = None) -> tuple:
    d = d or design()
    return (MU_MAIN,) + tuple(d["mu_points"])


def preds_at(mu: float, d: Optional[dict] = None) -> tuple:
    """The predictions with a P-hat and week runs at mu: every one of the grid at mu = 1, the default point (the
    unperturbed previous-day prediction) at the other mu (§6.3, §6.7)."""
    d = d or design()
    return tuple(d["predictions"]) if float(mu) == MU_MAIN else (DEFAULT_PRED,)


def days(d: Optional[dict] = None) -> tuple:
    """The predicted days 1 .. n_days - 1 (day 0 has no prediction, MS2 spec M38)."""
    d = d or design()
    return tuple(range(1, d["n_days"]))


def phat_id(panel, c, mu, pred, day) -> str:
    return job_id(EXP, "phat", panel=panel, c=int(c), mu=float(mu), pred=pred, day=int(day))


def eager_id(panel, c) -> str:
    return job_id(EXP, "eager", panel=panel, c=int(c))


def pcols_id(panel, c, mu, pred) -> str:
    return job_id(EXP, "pcols", panel=panel, c=int(c), mu=float(mu), pred=pred)


def week_id(panel, c, mu, pred) -> str:
    return job_id(EXP, "week", panel=panel, c=int(c), mu=float(mu), pred=pred)


def ratio_id(panel, c, pred) -> str:
    return job_id(EXP, "ratio", panel=panel, c=int(c), pred=pred)


def repro_id() -> str:
    return job_id(EXP, "repro")


def jobs() -> list[Job]:
    d = design()
    milp_s = mc.wall_timeout_s()
    seeds = list(d["policy_seeds"])
    common = {"window": d["window"], "day_slots": d["day_slots"]}
    ns = len(seeds)
    out = []
    for panel in d["panels"]:
        for c in d["alignments"]:
            for mu in mus(d):
                for pred in preds_at(mu, d):
                    for D in days(d):
                        out.append(Job(phat_id(panel, c, mu, pred, D), "milp",
                                       {"panel": panel, "c": int(c), "mu": float(mu), "pred": pred, "day": int(D),
                                        **common}, est_s=milp_s))
    for panel in d["panels"]:
        for c in d["alignments"]:
            out.append(Job(eager_id(panel, c), "milp", {"panel": panel, "c": int(c), **common}, est_s=milp_s))
    for panel in d["panels"]:
        for c in d["alignments"]:
            for mu in mus(d):
                for pred in preds_at(mu, d):
                    out.append(Job(pcols_id(panel, c, mu, pred), "pool",
                                   {"panel": panel, "c": int(c), "mu": float(mu), "pred": pred,
                                    "days": list(days(d)), **common}, est_s=EST_PCOLS_S))
    for panel in d["panels"]:
        for c in d["alignments"]:
            for mu in mus(d):
                for pred in preds_at(mu, d) + (perturb.NONE_KEY,):
                    tags = [REF_TAG] if pred == perturb.NONE_KEY else list(PRED_TAGS)
                    est = EST_BUILD_S + ns * (EST_A6_WEEK_S if pred == perturb.NONE_KEY
                                              else EST_A5_WEEK_S + EST_A6_WEEK_S)
                    out.append(Job(week_id(panel, c, mu, pred), "pool",
                                   {"panel": panel, "c": int(c), "mu": float(mu), "pred": pred, "tags": tags,
                                    "policy_seeds": seeds, **common}, est_s=est))
    for panel in d["panels"]:
        for c in d["alignments"]:
            for pred in d["predictions"]:
                out.append(Job(ratio_id(panel, c, pred), "pool",
                               {"panel": panel, "c": int(c), "mu": MU_MAIN, "pred": pred, "tags": ["A5"],
                                "policy_seeds": seeds, **common}, est_s=EST_BUILD_S + ns * EST_DAY_RUN_S[panel]))
    out.append(Job(repro_id(), "pool", {"script": "sublet.experiments.repro_c5_la", "workers": 1, "out": REPRO_DIR},
                   est_s=EST_REPRO_S))
    return out


# ---------------------------------------------------------------- paths
def _seg(k: str, v) -> str:
    return f"{k}={num_key(v) if isinstance(v, float) else v}"


def phat_lb_file(out, panel, c, mu, pred, day) -> Path:
    return (Path(out) / "lb" / "phat" / _seg("panel", panel) / _seg("c", int(c)) / _seg("mu", float(mu))
            / _seg("pred", pred) / f"{_seg('day', int(day))}.json")


def eager_lp_file(out, panel, c) -> Path:
    return Path(out) / "lb" / "eager" / _seg("panel", panel) / _seg("c", int(c)) / "lp.json"


def eager_core_file(out, panel, c) -> Path:
    return Path(out) / "lb" / "eager" / _seg("panel", panel) / _seg("c", int(c)) / "lp_core.json"


def eager_milp_file(out, panel, c) -> Path:
    return Path(out) / "lb" / "eager" / _seg("panel", panel) / _seg("c", int(c)) / "milp.json"


def run_file(out, kind: str, jid: str) -> Path:
    """runs/<kind>/<job's record file name>: kind 'phat' (the window's columns), 'pcols', 'week' or 'ratio'."""
    return Path(out) / "runs" / kind / mc.job_file_name(jid)


def pcols_file(out, panel, c, mu, pred) -> Path:
    return run_file(out, "pcols", pcols_id(panel, c, mu, pred))


# ---------------------------------------------------------------- instances (§6.3, M10)
def overrides(panel: str, mu: float, extra: Optional[dict] = None) -> dict:
    """The instance overrides of a panel at mu: e1.MENU (slow grid), llms [M], one week, one series borrower in
    north_america and stranding.mu_over_beta_tilde mu; `extra` on top (the P-hat jobs' bench.time_limit_s)."""
    from .e1 import MENU
    if panel not in PANELS:
        raise ValueError(f"unknown E4 panel {panel!r}; known {list(PANELS)}")
    ov = copy.deepcopy(MENU)
    ov.update({"time.horizon_min": WEEK_MIN, "llms": [dict(LLM_M)],
               "borrowers": {"model": "series",
                             "list": [{"id": f"{panel}0", "series": PANELS[panel]["series"],
                                       "week_index": PANELS[panel]["week_index"], "tier": TIER, "region": REGION}],
                             **BORROWERS},
               "stranding.mu_over_beta_tilde": float(mu)})
    ov.update(copy.deepcopy(dict(extra or {})))
    return ov


def run_spec(tag: str, ov: dict, c: int, seeds=(0,)) -> dict:
    """The validated run spec of one tag (drivers.run.load_run_spec): bench_e1 with the overrides, the trace lender
    (I1, 'sell', violations absorbed), invariant checks on; a tag outside TAGS is a policy id without parameters."""
    from ..drivers import run as drun
    pid, params = TAGS[tag] if tag in TAGS else (tag, {})
    return drun.load_run_spec({"schema_version": 1, "name": f"e4_{tag}".replace("-", "_"), "instance": CONFIG,
                               "overrides": copy.deepcopy(ov), "lender_model": dict(LENDER_MODEL),
                               "engine": {"check_invariants": True},
                               "policy": {"id": pid, "params": copy.deepcopy(params)},
                               "seeds": {"config": [int(c)], "lender": "config", "policy": [int(p) for p in seeds]},
                               "bench": None, "out": "code/sim/out/e4"})


def week_instance(panel: str, c: int, mu: float, window=None, extra: Optional[dict] = None) -> tuple:
    """(inst, model, ecfg) of the week instance of (panel, alignment c, mu); with `window` [t0, T] (reduced runs) the
    instance is restrict_horizon(inst, t0, T) after the build."""
    from ..drivers import run as drun
    from ..instance import restrict_horizon
    inst, model, ecfg = drun.build(run_spec("BL0a", overrides(panel, mu, extra), c), int(c))
    if not ecfg.check_invariants:
        raise RuntimeError("E4 runs need check_invariants=True (§0 item 5)")
    if window:
        inst = restrict_horizon(inst, int(window[0]), int(window[1]))
    return inst, model, ecfg


def day_slots_of(inst, day_slots=None) -> int:
    """Slow slots per day: `day_slots` (reduced runs) or 1440 / Δs."""
    return int(day_slots) if day_slots else DAY_MIN // inst.grid.slow_min


def predicted(inst, pred: str, c: int, ds: int) -> np.ndarray:
    """The (n, T_fast) predicted demand of prediction `pred` on the instance (perturb.prediction, days of ds slow
    slots)."""
    return perturb.prediction(inst.clients.demand, pred, day_fast=ds * inst.grid.phi, fast_min=inst.grid.fast_min,
                              c=int(c))


def demand_per_day(inst, ds: int) -> list[float]:
    """Realized demand per day of ds slow slots in replica-load-hours (the sum over clients)."""
    d = np.asarray(inst.clients.demand, dtype=np.float64)
    f = ds * inst.grid.phi
    n = -(-inst.grid.T_fast // f)
    return [float(d[:, k * f:(k + 1) * f].sum()) * inst.grid.fast_min / 60.0 for k in range(n)]


def ratio_day(inst, ds: int) -> int:
    """M13: the first day d* >= 1 whose previous day has demand (a nonempty previous-day prediction; the rule of
    out/ms4spec/e4_pred_sizing.py --part phat). It reads only the zero pattern of the demand, which does not depend
    on the alignment. ValueError if no day qualifies."""
    per = demand_per_day(inst, ds)
    for d in range(1, len(per)):
        if per[d - 1] > 0.0:
            return d
    raise ValueError("no day d >= 1 of the horizon has a previous day with demand (every prediction is empty)")


def ratio_instance(inst, ds: int) -> tuple:
    """(restrict_horizon(inst, d* ds, ds), d*): the ratio-day instance (§6.7)."""
    from ..instance import restrict_horizon
    d = ratio_day(inst, ds)
    return restrict_horizon(inst, d * ds, min(ds, inst.grid.T_slow - d * ds)), d


# ---------------------------------------------------------------- small records
def solve_record(sr, **extra) -> dict:
    """The fields of e1._solve_record (§2.5, "Records") of a SolveResult, with git_revision."""
    size = sr.size or {}
    return {**extra, "method": sr.method, "benchmark": sr.benchmark, "grid": sr.grid, "status": sr.status,
            "status_msg": sr.status_msg, "objective": sr.objective, "dual_bound": sr.dual_bound, "gap": sr.gap,
            "size": {k: size.get(k) for k in ("n_vars", "n_int", "n_rows", "nnz") if k in size},
            "build_s": sr.build_s, "solve_s": sr.solve_s, "peak_rss_mb": sr.peak_rss_mb,
            "git_revision": mc.git_revision()}


def _finite(v) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def phat_bounds(rec: dict) -> dict:
    """incumbent, LB and exact of one P-hat day (E4-2's slack term incumbent - LB): for a MILP day with status 0 or 1
    the MILP's objective and objective - gap max(1, |objective|) (the gap rule of opt.milp), exact iff gap <= 1e-4;
    0, 0 and true for an empty plan; null with notes otherwise (an lp_round day: the plan's cost is not computed)."""
    if rec.get("method") == "none":
        return {"incumbent": 0.0, "LB": 0.0, "exact": True}
    obj, gap = _finite(rec.get("objective")), _finite(rec.get("gap"))
    if rec.get("method") == "milp" and rec.get("status") in (0, 1) and obj is not None and gap is not None:
        return {"incumbent": obj, "LB": obj - gap * max(1.0, abs(obj)), "exact": bool(gap <= mc.EXACT_GAP)}
    note = f"no MILP incumbent (method {rec.get('method')!r}, status {rec.get('status')!r})"
    return {"incumbent": None, "incumbent_note": note, "LB": None, "LB_note": note, "exact": False}


def _jsonish(x):
    """metrics._jsonable (non-finite floats as strings) for the free-form parts of run files."""
    from ..metrics import _jsonable
    return _jsonable(x)


def _rel(p, base) -> str:
    try:
        return str(Path(p).resolve().relative_to(Path(base).resolve()))
    except ValueError:
        return str(p)


def _meta(job: Job, **kv) -> dict:
    return {"exp": EXP, "job": job.id, **kv, "git_revision": mc.git_revision(), "versions": mc.versions(),
            "written": mc._now()}


def core_export(inst, sched) -> Optional[dict]:
    """E4-5: instance.to_core(inst, sched, not_offered='big_m') of a run's schedule (the default 'raise' raises on E4's
    instance, whose protected sites offer only 'protected' and layer sites only the revocable menu): exact and notes,
    or exportable false with the InstanceError (e.g. per-unit fallback costs that differ across LLMs), which counts
    as not exact. None without a schedule."""
    from ..instance import InstanceError, to_core
    if sched is None:
        return None
    try:
        ex = to_core(inst, sched, not_offered="big_m")
    except InstanceError as err:
        return {"exact": False, "exportable": False, "why": f"not exportable: {type(err).__name__}: {err}"}
    return {"exact": bool(ex.exact), "exportable": True, "notes": list(ex.notes)[:10]}


def report_brief(pid: str, rep: dict) -> dict:
    """The scalar parts of A5's and A6's reports that E4 uses (the per-slot curves and the opened map left out)."""
    if pid == "A5":
        pr = rep.get("prediction") or {}
        return {"C_FP": rep.get("C_FP"), "C_R": rep.get("C_R"), "total": rep.get("total"),
                "switches": rep.get("switches"), "gamma": rep.get("gamma"), "P": rep.get("P"),
                "dual_feasibility": rep.get("dual_feasibility"), "d": rep.get("d"), "rbar": rep.get("rbar"),
                "psi": [dict(x) for x in rep.get("psi") or []],
                "prediction": {"n_cols": pr.get("n_cols"), "p_max": pr.get("p_max"), "label": pr.get("label")}}
    comb = rep.get("combiner")
    return {"combiner": None if comb is None else {k: comb.get(k) for k in ("C_FP", "C_R", "total", "switches",
                                                                              "gamma", "n_pred_cols", "label")}}


def combiner_of(pid: str, rep: dict) -> Optional[dict]:
    """(C_FP, C_R, accounted total, switches) of a run with a combiner (A5, A6 with predictions), else None."""
    c = rep if pid == "A5" else (rep.get("combiner") if isinstance(rep.get("combiner"), dict) else None)
    if c is None or c.get("C_FP") is None:
        return None
    return {"C_FP": float(c["C_FP"]), "C_R": float(c["C_R"]), "accounted_total": float(c["total"]),
            "switches": int(c["switches"])}


def engine_run(tag: str, spec: dict, inst, model, ecfg, c: int, ps: int, given: dict, label: str,
               bench_grid: Optional[str] = None) -> tuple[dict, object]:
    """One engine run of a tag with the driver inputs `given` (pred_cols, pred_demand: the cached P-hat and the
    prediction; only those the policy needs are passed, so drivers.run.driver_inputs computes nothing, M14): the
    run's row and its RunResult."""
    from ..algos import registry
    from ..drivers import run as drun
    from ..engine import simulate
    pid, params = TAGS[tag]
    need = registry.needed_inputs(pid, params)
    inp = {k: v for k, v in given.items() if k in need}
    missing = [k for k in need if k not in inp]
    if missing:
        raise RuntimeError(f"{tag}: driver inputs {missing} not given (E4 never plans inside a run, M14)")
    t0 = time.perf_counter()
    pol = drun.make_policy(spec, inst, inputs=inp)
    _, imeta = drun.driver_inputs(pid, params, inst, inp)
    t1 = time.perf_counter()
    res = simulate(inst, pol, model, ecfg, lender_seed=int(c), policy_seed=int(ps))
    t2 = time.perf_counter()
    rep = res.metrics.get("policy") or {}
    rp = {**params, **(pol.params() or {})}
    comb = combiner_of(pid, rep)
    total = float(res.components["total"])
    row = {"tag": tag, "policy_id": pid, "params": params, "resolved_params": rp, "p": int(ps),
           "label": label if need else None,
           "info_class": registry.info_class(pid, rp, model.information, label if need else None),
           "inputs_given": sorted(inp), "driver_inputs": imeta, "seeds": dict(res.seeds),
           "total": total, "components": dict(res.components),
           "n_invariant_failures": len(res.invariant_failures),
           "invariant_failures": list(res.invariant_failures)[:20],
           "gpu_only_lease_slots": int(res.metrics.get("gpu_only_lease_slots", 0)),
           "schedule_hash": mc.schedule_hash(res.schedule),
           "n_announcements": int(sum(len(r) for r in res.schedule.R)),
           "report": report_brief(pid, rep), "combiner": comb,
           "real_over_min": (total / min(comb["C_FP"], comb["C_R"])
                             if comb is not None and min(comb["C_FP"], comb["C_R"]) > 0 else None),
           "make_policy_s": t1 - t0, "engine_s": t2 - t1, "wall_s": time.perf_counter() - t0,
           "runtime": {k: res.runtime.get(k) for k in ("wall_s", "policy_s", "routing_s", "peak_rss_mb")}}
    if bench_grid is not None:
        row["ratio_validity"] = drun.ratio_validity(bench_grid, inst, model)
    print(f"[e4] {tag} p{ps}: total {total:.4f} USD, engine {t2 - t1:.2f} s"
          + ("" if comb is None else f", C_FP {comb['C_FP']:.2f}, C_R {comb['C_R']:.2f}, switches {comb['switches']}"),
          flush=True)
    return row, res


# ---------------------------------------------------------------- P-hat (§6.5, M14)
def load_pcols(out, panel: str, c: int, mu: float, pred: str, inst_hash: str, label: str) -> tuple:
    """(PredictedCols, the pcols file) of (panel, c, mu, pred) from runs/pcols/, labeled `label`; an error unless the
    e4:pcols job's record is 'ok' and its file names the instance hash `inst_hash`."""
    from ..drivers.predict import PredictedCols
    jid = pcols_id(panel, c, mu, pred)
    rec = mc.read_record(out, jid)
    if rec is None or rec.get("status") != "ok":
        raise FileNotFoundError(f"{jid} has no 'ok' record (status {None if rec is None else rec.get('status')!r}):"
                                " run the P-hat jobs and e4:pcols first")
    d = mc.read_json(pcols_file(out, panel, c, mu, pred))
    if d is None:
        raise FileNotFoundError(f"{pcols_file(out, panel, c, mu, pred)} is missing")
    if d["instance_hash"] != inst_hash:
        raise RuntimeError(f"{jid}: P-hat of instance {d['instance_hash'][:12]}, the run's is {inst_hash[:12]}")
    return PredictedCols([tuple(int(v) for v in F) for F in d["cols"]], days=d["days"], label=label), d


def run_phat(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One P-hat day (§6.5): plan_daily on the two-day window with its prediction, or an empty plan."""
    from ..config import rng_streams
    from ..drivers.predict import plan_daily
    from ..instance import restrict_horizon
    p = job.params
    panel, c, mu, pred, D = p["panel"], int(p["c"]), float(p["mu"]), p["pred"], int(p["day"])
    limit = mc.milp_limit_s()
    t_start = time.perf_counter()
    inst, _, _ = week_instance(panel, c, mu, p.get("window"), extra={"bench.time_limit_s": limit})
    ds = day_slots_of(inst, p.get("day_slots"))
    phi = inst.grid.phi
    n_days = -(-inst.grid.T_slow // ds)
    if not 1 <= D < n_days:
        raise ValueError(f"{job.id}: day {D} is not a predicted day (1 .. {n_days - 1})")
    T_win = min(2 * ds, inst.grid.T_slow - (D - 1) * ds)
    two = restrict_horizon(inst, (D - 1) * ds, T_win)
    full = predicted(inst, pred, c, ds)
    wpred = full[:, (D - 1) * ds * phi:((D - 1) * ds + T_win) * phi]
    day_pred = wpred[:, ds * phi:]
    ih = mc.instance_hash(inst)
    if not np.any(day_pred > 0):
        plan = {"day": 1, "t0": ds, "T": T_win - ds, "method": "none", "status": "empty", "objective": 0.0,
                "gap": 0.0, "n_cols": 0, "wall_s": 0.0, "note": "the prediction is zero on the day: an empty plan, "
                                                               "no MILP (§6.5)"}
        cols = []
    else:
        pc = plan_daily(two, wpred, day_slots=ds, method="auto", rng=rng_streams(inst.seed)["bench"])
        if len(pc.days) != 1:
            raise RuntimeError(f"{job.id}: plan_daily planned {len(pc.days)} days of the two-day window, not 1")
        plan = dict(pc.days[0])
        cols = [tuple(int(v) for v in F) for F in pc]
    bench = two.config.get("bench") or {}
    rec = {"job": job.id, "exp": EXP, "kind": "phat", "panel": panel, "c": c, "mu": mu, "pred": pred,
           "label": perturb.LABELS[pred], "day": D, "day_slots": ds, "window": [(D - 1) * ds, T_win],
           "method": plan.get("method"), "status": plan.get("status"), "objective": plan.get("objective"),
           "gap": plan.get("gap"), "n_cols": len(cols), "wall_s": plan.get("wall_s"), **phat_bounds(plan),
           "plan_daily": plan, "grid": BENCH_GRID, "time_limit_s": float(bench.get("time_limit_s", limit)),
           "mip_rel_gap": float(bench.get("mip_rel_gap", MILP_GAP)), "instance_hash": ih,
           "window_hash": mc.instance_hash(two), "pred_sha256": perturb.pred_sha256(day_pred),
           "predicted_load_h": float(day_pred.sum()) * inst.grid.fast_min / 60.0,
           "job_wall_s": time.perf_counter() - t_start, "git_revision": mc.git_revision()}
    outputs.dump(rec, phat_lb_file(out, panel, c, mu, pred, D))
    outputs.dump({"meta": _meta(job), "instance_hash": ih, "day": D, "day_slots": ds, "window_t0": (D - 1) * ds,
                  "cols": [list(F) for F in cols]}, run_file(out, "phat", job.id), compact=True)
    print(f"[e4] {job.id}: method {rec['method']}, status {rec['status']}, objective {rec['objective']}, gap "
          f"{rec['gap']}, {len(cols)} columns, {rec['wall_s']} s", flush=True)
    return {"runs": 0, "method": rec["method"], "status": rec["status"], "gap": rec["gap"], "n_cols": len(cols)}


def run_pcols(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """The P-hat cache of (panel, c, mu, pred) (§6.5): the day jobs' columns, start slots shifted by (D - 1) ds."""
    p = job.params
    panel, c, mu, pred = p["panel"], int(p["c"]), float(p["mu"]), p["pred"]
    inst, _, _ = week_instance(panel, c, mu, p.get("window"))
    ih = mc.instance_hash(inst)
    ds = day_slots_of(inst, p.get("day_slots"))
    cols, recs, bad = [], [], []
    for D in p["days"]:
        jid = phat_id(panel, c, mu, pred, D)
        r = mc.read_record(out, jid)
        lb = mc.read_json(phat_lb_file(out, panel, c, mu, pred, D))
        cf = mc.read_json(run_file(out, "phat", jid))
        if r is None or r.get("status") != "ok" or lb is None or cf is None:
            bad.append(f"{jid} ({'no record' if r is None else r.get('status')})")
            continue
        if lb["instance_hash"] != ih or cf["instance_hash"] != ih:
            raise RuntimeError(f"{jid}: P-hat day of another instance ({lb['instance_hash'][:12]}, the week's "
                               f"{ih[:12]}): rerun the day job")
        sh = (int(D) - 1) * ds
        cols += [(int(F[0]), int(F[1]), int(F[2]), int(F[3]) + sh) for F in cf["cols"]]
        recs.append({"day": int(D), "t0": int(D) * ds, **{k: lb.get(k) for k in (
            "method", "status", "objective", "gap", "n_cols", "wall_s", "incumbent", "LB", "exact", "time_limit_s",
            "pred_sha256")}, "milp_size": (lb.get("plan_daily") or {}).get("milp_size")})
    if bad:
        raise RuntimeError(f"P-hat day jobs without an 'ok' output: {bad}")
    doc = {"meta": _meta(job), "panel": panel, "c": c, "mu": mu, "pred": pred, "label": perturb.LABELS[pred],
           "instance_hash": ih, "day_slots": ds, "days": recs, "n_cols": len(cols), "cols": [list(F) for F in cols],
           "methods": {m: sum(1 for x in recs if x["method"] == m) for m in ("milp", "lp_round", "none")}}
    outputs.dump(doc, pcols_file(out, panel, c, mu, pred), compact=True)
    return {"runs": 0, "n_cols": len(cols), "methods": doc["methods"], "instance_hash": ih}


# ---------------------------------------------------------------- runs (§6.7)
def run_week(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """The week runs of one (panel, c, mu, pred) at every policy seed (§6.7): A5 and A6-pred with the cached P-hat,
    or A6 without predictions (pred 'none')."""
    p = job.params
    panel, c, mu, pred = p["panel"], int(p["c"]), float(p["mu"]), p["pred"]
    t_start = time.perf_counter()
    inst, model, ecfg = week_instance(panel, c, mu, p.get("window"))
    ih = mc.instance_hash(inst)
    ds = day_slots_of(inst, p.get("day_slots"))
    lab = perturb.LABELS[pred]
    extra: dict = {}
    if pred == perturb.NONE_KEY:
        given = {}
    else:
        pd_ = predicted(inst, pred, c, ds)
        pc, pdoc = load_pcols(out, panel, c, mu, pred, ih, lab)
        given = {"pred_cols": pc, "pred_demand": pd_}
        extra = {"pcols_file": _rel(pcols_file(out, panel, c, mu, pred), out), "pcols_n_cols": len(pc),
                 "phat_days": pdoc["days"], "pred_sha256": perturb.pred_sha256(pd_),
                 "eta_q_by_day": perturb.eta_q_days(inst, inst.clients.demand, pd_, ds)}
    ov = overrides(panel, mu)
    errors, rows, first = [], [], {}
    for tag in p["tags"]:
        spec = run_spec(tag, ov, c, p["policy_seeds"])
        for ps in p["policy_seeds"]:
            def one(tag=tag, spec=spec, ps=ps):
                row, res = engine_run(tag, spec, inst, model, ecfg, c, ps, given, lab)
                rows.append(row)
                first.setdefault("schedule", res.schedule)
            mc.try_run(errors, f"{tag}_p{ps}", one)
    doc = {"meta": _meta(job, panel=panel, c=c, mu=mu, pred=pred, predictions={pred: lab}, instance_hash=ih,
                         config=CONFIG, overrides=ov, lender_model=dict(LENDER_MODEL), day_slots=ds,
                         window=p.get("window")),
           **extra, "core_export": core_export(inst, first.get("schedule")), "runs": rows,
           "errors": [{k: v for k, v in e.items() if k != "traceback"} for e in errors],
           "wall_s": time.perf_counter() - t_start}
    outputs.dump(_jsonish(doc), run_file(out, "week", job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": ih}


def run_ratio(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """A5 on the ratio day of (panel, c) at mu = 1 under one prediction (§6.7, M13): the cached columns of day d*,
    shifted by -d* ds, the prediction of that day, q eta_{d*} (§6.8) and ratio_validity on the slow grid."""
    from ..drivers.predict import PredictedCols
    p = job.params
    panel, c, pred = p["panel"], int(p["c"]), p["pred"]
    t_start = time.perf_counter()
    inst, model, ecfg = week_instance(panel, c, MU_MAIN, p.get("window"))
    ih_week = mc.instance_hash(inst)
    ds = day_slots_of(inst, p.get("day_slots"))
    day, d_star = ratio_instance(inst, ds)
    ih = mc.instance_hash(day)
    lab = perturb.LABELS[pred]
    F = ds * inst.grid.phi
    pd_ = predicted(inst, pred, c, ds)
    pred_day = np.ascontiguousarray(pd_[:, d_star * F:d_star * F + day.grid.T_fast])
    pcw, pdoc = load_pcols(out, panel, c, MU_MAIN, pred, ih_week, lab)
    lo, hi = d_star * ds, d_star * ds + day.grid.T_slow
    cols = [(l, j, k, s - lo) for (l, j, k, s) in pcw if lo <= s < hi]
    drec = next((r for r in pdoc["days"] if int(r["day"]) == d_star), None)
    if drec is None:
        raise RuntimeError(f"{job.id}: the P-hat cache has no record of day {d_star}")
    pc = PredictedCols(cols, days=[{**drec, "t0": 0}], label=lab)
    eta = perturb.eta_q(day, day.clients.demand, pred_day, 0, ds)
    ov = overrides(panel, MU_MAIN)
    errors, rows, first = [], [], {}
    for tag in p["tags"]:
        spec = run_spec(tag, ov, c, p["policy_seeds"])
        for ps in p["policy_seeds"]:
            def one(tag=tag, spec=spec, ps=ps):
                row, res = engine_run(tag, spec, day, model, ecfg, c, ps, {"pred_cols": pc, "pred_demand": pred_day},
                                      lab, bench_grid=BENCH_GRID)
                rows.append(row)
                first.setdefault("schedule", res.schedule)
            mc.try_run(errors, f"{tag}_p{ps}", one)
    from ..drivers.run import ratio_validity
    doc = {"meta": _meta(job, panel=panel, c=c, mu=MU_MAIN, pred=pred, predictions={pred: lab}, instance_hash=ih,
                         week_instance_hash=ih_week, d_star=d_star, day_slots=ds, window=p.get("window"),
                         config=CONFIG, overrides=ov, lender_model=dict(LENDER_MODEL)),
           "d_star": d_star, "eta_q": eta, "phat_day": drec, "n_cols": len(cols),
           "pred_sha256": perturb.pred_sha256(pred_day), "ratio_validity": ratio_validity(BENCH_GRID, day, model),
           "core_export": core_export(day, first.get("schedule")), "runs": rows,
           "errors": [{k: v for k, v in e.items() if k != "traceback"} for e in errors],
           "wall_s": time.perf_counter() - t_start}
    outputs.dump(_jsonish(doc), run_file(out, "ratio", job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": ih, "d_star": d_star, "eta_q": eta}


def core_record(day, **common) -> dict:
    """LP_core of a ratio day (§6.6): drivers.predict.aligned_lp, the LP of the PDs' covering program over the aligned
    columns (no capacity; R7's LPal on the core), at most every fractional PD's cost on the day. Status 'optimal' with
    its objective, or aligned_lp's status ('over_gate', 'lp_status_<n>') with objective null."""
    from ..drivers.predict import aligned_lp
    t0 = time.perf_counter()
    al = aligned_lp(day)
    return {"kind": "lp_core", **common, "benchmark": "lp_aligned", "method": "aligned_lp", "grid": BENCH_GRID,
            "status": al["status"], "objective": al["fun"], "n_cols": len(al["cols"]), "size": dict(al["size"]),
            "wall_s": time.perf_counter() - t0, "git_revision": mc.git_revision()}


def run_eager(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """OPT_eager of the ratio day of (panel, c) by MILP and its LP, and LP_core (§6.6, §6.7): the two LP records are
    written at once (a kill at the hard wall-clock limit leaves the LP as Q39's LB, §2.5), the MILP's through the
    job's outputs."""
    from ..opt.milp import solve_eager, solve_lp
    from ..types import Schedule
    p = job.params
    panel, c = p["panel"], int(p["c"])
    limit = mc.milp_limit_s()
    t0 = time.perf_counter()
    inst, model, _ = week_instance(panel, c, MU_MAIN, p.get("window"))
    ds = day_slots_of(inst, p.get("day_slots"))
    day, d_star = ratio_instance(inst, ds)
    ih = mc.instance_hash(day)
    eager = Schedule.eager(day)
    sh = mc.schedule_hash(eager)
    common = {"job": job.id, "panel": panel, "c": c, "mu": MU_MAIN, "d_star": d_star, "day_slots": ds,
              "instance_hash": ih, "week_instance_hash": mc.instance_hash(inst), "schedule_hash": sh}
    t1 = time.perf_counter()
    lp = solve_lp(day, eager, grid=BENCH_GRID, allow_large=True, return_plan=False)
    lp_rec = solve_record(lp, kind="lp", **common, time_limit_s=None, wall_s=time.perf_counter() - t1)
    mc.dump_json(lp_rec, eager_lp_file(out, panel, c))
    print(f"[e4] {job.id}: LP status {lp.status}, objective {lp.objective}, {lp_rec['wall_s']:.1f} s", flush=True)
    core = core_record(day, **common)
    mc.dump_json(core, eager_core_file(out, panel, c))
    print(f"[e4] {job.id}: LP_core status {core['status']}, objective {core['objective']}, "
          f"{core['size']['n_vars']} variables, {core['wall_s']:.1f} s", flush=True)
    t2 = time.perf_counter()
    sr = solve_eager(day, grid=BENCH_GRID, time_limit_s=limit, mip_rel_gap=MILP_GAP, allow_large=True,
                     return_plan=False)
    rec = solve_record(sr, kind="milp", **common, time_limit_s=limit, mip_rel_gap=MILP_GAP,
                       wall_s=time.perf_counter() - t2, job_wall_s=time.perf_counter() - t0)
    outputs.dump(rec, eager_milp_file(out, panel, c))
    print(f"[e4] {job.id}: MILP status {sr.status} ({sr.status_msg}), objective {sr.objective}, dual bound "
          f"{sr.dual_bound}, gap {sr.gap}, {rec['size']}, {rec['wall_s']:.1f} s", flush=True)
    return {"runs": 0, "d_star": d_star, "lp": lp.objective, "lp_core": core["objective"], "status": sr.status,
            "objective": sr.objective,
            "dual_bound": sr.dual_bound, "gap": sr.gap, "n_vars": rec["size"].get("n_vars")}


# ---------------------------------------------------------------- E4-1 (job e4:repro)
REPRO_FILES = (("c5_la_repro.txt", "c5_la.txt"), ("c5_la_nearest_repro.txt", "c5_la_nearest.txt"))
REPRO_JSON = (("c5_la_repro.json", "c5_la.json"), ("c5_la_nearest_repro.json", "c5_la_nearest.json"))
MAX_LISTED = 20


def _walk(ref, got, where: str, acc: dict) -> None:
    """Compare a reference JSON tree with a reproduction: every key of a reference object must be in the
    reproduction's (extra keys are allowed), lists by position, numbers to the relative difference |a - b| /
    max(1, |b|), other values by equality."""
    if isinstance(ref, dict):
        if not isinstance(got, dict):
            acc["mismatches"].append(f"{where}: not an object")
            return
        for k, v in ref.items():
            if k not in got:
                acc["mismatches"].append(f"{where}.{k}: missing")
                continue
            _walk(v, got[k], f"{where}.{k}", acc)
        return
    if isinstance(ref, list):
        if not isinstance(got, list) or len(got) != len(ref):
            acc["mismatches"].append(f"{where}: list of {len(got) if isinstance(got, list) else None} items, "
                                     f"reference {len(ref)}")
            return
        for i, (a, b) in enumerate(zip(ref, got)):
            _walk(a, b, f"{where}[{i}]", acc)
        return
    if isinstance(ref, (int, float)) and not isinstance(ref, bool) and isinstance(got, (int, float)) \
            and not isinstance(got, bool):
        acc["n"] += 1
        if math.isfinite(ref) and math.isfinite(got):
            acc["max"] = max(acc["max"], abs(got - ref) / max(1.0, abs(ref)))
        elif ref != got:
            acc["mismatches"].append(f"{where}: {got!r} != {ref!r}")
        return
    acc["n"] += 1
    if ref != got:
        acc["mismatches"].append(f"{where}: {got!r} != {ref!r}")


def repro_compare(rdir, ref_dir=None) -> dict:
    """E4-1 and E4-2 (core) on a reproduction folder `rdir` written by repro_c5_la: c5_la_repro.txt and
    c5_la_nearest_repro.txt line by line against the reference files of code/theory_checks/c3/out/ (or `ref_dir`),
    the JSON values against c5_la.json and c5_la_nearest.json (_walk), and C3-L10 on the core (every row of
    c5_la_repro.json has eta_chk true). pass iff both text files are equal line by line (R7's printed digits) and
    the reproduction is not a --quick run."""
    from ..paths import C3
    rdir = Path(rdir)
    ref = Path(ref_dir) if ref_dir is not None else C3 / "out"
    files = {}
    for got_name, ref_name in REPRO_FILES:
        g, r = rdir / got_name, ref / ref_name
        gl = g.read_text().splitlines() if g.is_file() else None
        rl = r.read_text().splitlines() if r.is_file() else None
        e = {"got": got_name, "lines_equal": gl is not None and gl == rl,
             "n_lines_got": None if gl is None else len(gl), "n_lines_ref": None if rl is None else len(rl)}
        if gl is None:
            e["note"] = f"{g} is missing"
        e["first_diffs"] = [] if gl is None or rl is None else [
            {"line": i + 1, "got": a, "ref": b} for i, (a, b) in enumerate(zip(gl, rl)) if a != b][:5]
        files[ref_name] = e
    js = {}
    for got_name, ref_name in REPRO_JSON:
        g, r = mc.read_json(rdir / got_name), mc.read_json(ref / ref_name)
        acc = {"n": 0, "max": 0.0, "mismatches": []}
        if g is None or r is None:
            js[ref_name] = put({"n_compared": 0, "n_mismatch": None, "mismatches": []}, "max_rel_diff", None,
                               f"{got_name if g is None else ref_name} missing or not JSON")
            continue
        _walk(r, g.get("runs"), "runs", acc)
        js[ref_name] = {"max_rel_diff": acc["max"], "n_compared": acc["n"], "n_mismatch": len(acc["mismatches"]),
                        "mismatches": acc["mismatches"][:MAX_LISTED]}
    got = mc.read_json(rdir / "c5_la_repro.json") or {}
    rows = [{"seed": run.get("seed"), "kind": row.get("kind"), "par": row.get("par"), "eta": row.get("eta"),
             "eta_chk": row.get("eta_chk"), "cPhat": row.get("cPhat")}
            for run in got.get("runs") or [] for row in run.get("rows") or []]
    bad = [r for r in rows if r["eta_chk"] is not True]
    quick = bool((got.get("meta") or {}).get("quick"))
    return {"files": files, "json": js,
            "core_eta": {"n_rows": len(rows), "n_eta_chk_false": len(bad), "rows_false": bad[:MAX_LISTED]},
            "quick": quick, "pass": bool(all(e["lines_equal"] for e in files.values()) and not quick),
            "reference_dir": str(ref)}


def run_repro(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """E4-1 (§6.9): repro_c5_la.main(['--workers', '1', '--out', <out>/repro]) with the absolute out folder (a
    relative code/sim/out/... would resolve against the job's working directory code/sim), then repro_compare.
    repro_c5_la writes its four files itself (they record no git revision, C20); repro_check.json records it."""
    from . import repro_c5_la
    rdir = Path(out).resolve() / REPRO_DIR
    argv = ["--workers", "1", "--out", str(rdir)]
    t0 = time.perf_counter()
    rc = repro_c5_la.main(argv)
    if rc != 0:
        raise RuntimeError(f"repro_c5_la.main({argv}) returned {rc}")
    chk = repro_compare(rdir)
    chk["meta"] = _meta(job, script="sublet.experiments.repro_c5_la", argv=argv, out=str(rdir),
                        seconds=time.perf_counter() - t0)
    outputs.dump(chk, Path(out) / "repro_check.json")
    return {"runs": 0, "pass": chk["pass"], "n_eta_chk_false": chk["core_eta"]["n_eta_chk_false"]}


# ---------------------------------------------------------------- dispatch
def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    _, part, _ = mc.parse_job_id(job.id)
    fn = {"phat": run_phat, "eager": run_eager, "pcols": run_pcols, "week": run_week, "ratio": run_ratio,
          "repro": run_repro}.get(part)
    if fn is None:
        raise ValueError(f"unknown E4 job {job.id!r}")
    return fn(job, outputs, out)


def manifest_extra(out: Path) -> dict:
    """The instance hash of every week instance (panel, c, mu) and ratio-day instance (panel, c) of the grid (§2.6),
    with d* per (panel, c)."""
    d = design()
    hashes, day_hashes, dstar = {}, {}, {}
    for panel in d["panels"]:
        for c in d["alignments"]:
            for mu in mus(d):
                inst, _, _ = week_instance(panel, c, mu, d["window"])
                hashes[f"panel={panel}:c={int(c)}:mu={num_key(mu)}"] = mc.instance_hash(inst)
                if float(mu) == MU_MAIN:
                    day, ds_ = ratio_instance(inst, day_slots_of(inst, d["day_slots"]))
                    day_hashes[f"panel={panel}:c={int(c)}"] = mc.instance_hash(day)
                    dstar.setdefault(panel, {})[str(int(c))] = ds_
    return {"instance_hashes": hashes, "ratio_day_instance_hashes": day_hashes, "ratio_day": dstar,
            "predictions": dict(perturb.LABELS),
            "design": {k: (list(v) if isinstance(v, tuple) else v) for k, v in d.items()}}


# ---------------------------------------------------------------- summary (§6.10)
def _ok_output(out: Path, recs: dict, jid: str, path, ignored: Optional[list] = None) -> Optional[dict]:
    """The JSON output `path` of job `jid`, or None unless the job's record says 'ok' (§2.4); an output that exists
    while its record is not 'ok' is not used and is listed in `ignored`."""
    rec = recs.get(jid)
    if rec is None or rec.get("status") != "ok":
        if ignored is not None and Path(path).is_file():
            ignored.append({"job": jid, "status": None if rec is None else rec.get("status"),
                            "output": _rel(path, out)})
        return None
    return mc.read_json(path)


def _agg(values: list, note: str) -> dict:
    a = mc.median_summary(values)
    if not values:
        for k in ("median", "p95", "max"):
            put(a, k, None, note)
        a["median_ci95_note"] = note
    return a


def _median(vals) -> Optional[float]:
    v = [x for x in vals if x is not None]
    return float(np.median(v)) if v else None


def _checked(rec: dict, ih: Optional[str], what: str) -> dict:
    """A benchmark record whose instance hash differs from the ratio runs' (left by an earlier run of its job) is not
    used: {'status': 'stale', ...}. Stand-ins without a hash (missing, killed) pass unchanged."""
    if ih is None or rec.get("instance_hash") is None or rec["instance_hash"] == ih:
        return rec
    return {"status": "stale", "stale_note": f"{what} record {rec.get('job')!r}: its instance hash differs from the "
                                             "ratio-day runs' (an output of an earlier run of the job; rerun it)"}


LP_JOB_STATUSES = ("ok", "wall_limit", "oom_at_3G")     # job records under which the pre-MILP LP files are used


def _pre_milp_output(out: Path, recs: dict, jid: str, path, ignored: list) -> dict:
    """A file the eager job writes before its MILP (lp.json, lp_core.json): used if the job's record is 'ok' or a kill
    at the hard wall-clock limit or by the cap ('wall_limit', 'oom_at_3G': the LP is then Q39's LB, §2.5, as e2's
    joint rows); otherwise not used, listed in `ignored`, and {'status': <the job's status>}; {'status': 'missing'}
    without a record or a file."""
    rec = recs.get(jid)
    st = None if rec is None else rec.get("status")
    if st not in LP_JOB_STATUSES:
        if Path(path).is_file():
            ignored.append({"job": jid, "status": st, "output": _rel(path, out)})
        return {"status": st or "missing"}
    return mc.read_json(path) or {"status": "missing"}


def _eager_inputs(out: Path, recs: dict, panel: str, c: int, ih: Optional[str], ignored: list) -> tuple:
    """(LP record, MILP record, LP_core record; each a record or a stand-in) of the ratio day of (panel, c): the LP
    files by _pre_milp_output, the MILP file if the job's record is 'ok', else {'status': <the job's status>} or
    {'status': 'missing'}; each checked against the ratio runs' instance hash `ih` (or the MILP's or the LP's where no
    ratio run exists)."""
    jid = eager_id(panel, c)
    lp = _pre_milp_output(out, recs, jid, eager_lp_file(out, panel, c), ignored)
    core = _pre_milp_output(out, recs, jid, eager_core_file(out, panel, c), ignored)
    milp = _ok_output(out, recs, jid, eager_milp_file(out, panel, c), ignored)
    if milp is None:
        rec = recs.get(jid)
        milp = {"status": rec.get("status") if rec is not None and rec.get("status") != "ok" else "missing"}
    ref = ih or milp.get("instance_hash") or lp.get("instance_hash")
    return _checked(lp, ref, "LP"), _checked(milp, ref, "MILP"), _checked(core, ref, "LP_core")


def _core_value(core: dict) -> Optional[float]:
    """LP_core's objective if aligned_lp solved it ('optimal'), else None."""
    return _finite(core.get("objective")) if core.get("status") == "optimal" else None


def _series_value(run: dict, s: str) -> Optional[float]:
    """ALG of one series of a ratio-day A5 run: psi[i].P for psi_01, psi_03, psi_05, P (psi = 1) for a2_frac, the
    engine total for a5 (§6.6)."""
    rep = run.get("report") or {}
    if s == "a5":
        return _finite(run.get("total"))
    if s == "a2_frac":
        return _finite(rep.get("P"))
    psi = PSI_SERIES[s]
    for x in rep.get("psi") or []:
        if abs(float(x.get("psi", -1.0)) - psi) <= 1e-12:
            return _finite(x.get("P"))
    return None


def _phat_entry(r: Optional[dict], note: str) -> dict:
    keys = ("method", "status", "objective", "gap", "LB", "incumbent", "exact", "n_cols", "wall_s")
    if r is None:
        e = {}
        for k in keys:
            put(e, k, None, note)
        return e
    return {k: r.get(k) for k in keys}


def _combiner_entry(runs: list, note: str) -> dict:
    cs = [r for r in runs if r.get("combiner")]
    rom = [r["real_over_min"] for r in cs if r.get("real_over_min") is not None]
    e = {"n": len(cs), "bound": COMB_BOUND, "real_over_min": _agg(rom, note)}
    for k, vals in (("C_FP_mean", [r["combiner"]["C_FP"] for r in cs]),
                    ("C_R_mean", [r["combiner"]["C_R"] for r in cs]),
                    ("accounted_total_mean", [r["combiner"]["accounted_total"] for r in cs]),
                    ("switches_mean", [r["combiner"]["switches"] for r in cs]),
                    ("real_mean", [r["total"] for r in cs])):
        put(e, k, float(np.mean(vals)) if vals else None, note)
    put(e, "max_real_over_min", max(rom) if rom else None, note)
    e["n_above_bound"] = sum(1 for v in rom if v > COMB_BOUND * (1 + TOL))
    return e


def summary(out) -> dict:
    out = Path(out)
    d = design()
    al, seeds = d["alignments"], d["policy_seeds"]
    js = jobs()
    recs = mc.read_records(out)
    ignored: list = []
    # ---- P-hat days (E4-4)
    phat, phat_rows = {}, []
    for panel in d["panels"]:
        for c in al:
            for mu in mus(d):
                for pred in preds_at(mu, d):
                    dd, ns = {}, []
                    for D in days(d):
                        jid = phat_id(panel, c, mu, pred, D)
                        r = _ok_output(out, recs, jid, phat_lb_file(out, panel, c, mu, pred, D), ignored)
                        st = (recs.get(jid) or {}).get("status")
                        e = _phat_entry(r, f"no 'ok' output of {jid} (job status {st!r})")
                        if r is None:
                            e["job_status"] = st
                        dd[str(D)] = e
                        phat_rows.append({"panel": panel, "c": c, "mu": mu, "pred": pred, "day": D, "ok": r is not None,
                                          "job_status": st, **{k: e.get(k) for k in ("method", "status", "gap")}})
                        ns.append(e.get("n_cols"))
                    ent = {"days": dd, "methods": {m: sum(1 for x in dd.values() if x.get("method") == m)
                                                   for m in ("milp", "lp_round", "none")},
                           "assembled": (recs.get(pcols_id(panel, c, mu, pred)) or {}).get("status") == "ok"}
                    put(ent, "n_cols", sum(ns) if all(n is not None for n in ns) else None,
                        "a day without an 'ok' output")
                    phat.setdefault(panel, {}).setdefault(str(c), {}).setdefault(num_key(mu), {})[pred] = ent
    # ---- run outputs
    week_docs, ratio_docs = {}, {}
    for panel in d["panels"]:
        for c in al:
            for mu in mus(d):
                for pred in preds_at(mu, d) + (perturb.NONE_KEY,):
                    jid = week_id(panel, c, mu, pred)
                    doc = _ok_output(out, recs, jid, run_file(out, "week", jid), ignored)
                    if doc is not None:
                        week_docs[(panel, c, float(mu), pred)] = doc
            for pred in d["predictions"]:
                jid = ratio_id(panel, c, pred)
                doc = _ok_output(out, recs, jid, run_file(out, "ratio", jid), ignored)
                if doc is not None:
                    ratio_docs[(panel, c, pred)] = doc
    # ---- OPT_eager of the ratio days
    eager, eager_in, dstar = {}, {}, {}
    for panel in d["panels"]:
        for c in al:
            ih = next((doc["meta"]["instance_hash"] for (pp, cc, _), doc in ratio_docs.items()
                       if pp == panel and cc == c), None)
            lp, milp, core = _eager_inputs(out, recs, panel, c, ih, ignored)
            eager_in[(panel, c)] = (lp, milp, core)
            b = mc.bench_values(lp, milp)
            ent = {**b, "LP_record_status": lp.get("status"), "MILP_record_status": milp.get("status")}
            put(ent, "LP_core", _core_value(core), f"no solved LP_core of the ratio day (status {core.get('status')!r})")
            ent["LP_core_status"] = core.get("status")
            src = milp if milp.get("d_star") is not None else lp
            ds_ = next((doc["d_star"] for (pp, cc, _), doc in ratio_docs.items() if pp == panel and cc == c),
                       src.get("d_star"))
            for k, v in (("d_star", ds_), ("instance_hash", src.get("instance_hash")),
                         ("time_limit_s", milp.get("time_limit_s")), ("size", milp.get("size") or lp.get("size"))):
                put(ent, k, v, "no LP or MILP record of the ratio day")
            for x in (lp, milp, core):
                if x.get("status") == "stale":
                    ent.setdefault("stale_notes", []).append(x["stale_note"])
            eager.setdefault(panel, {})[str(c)] = ent
            if ds_ is not None:
                dstar.setdefault(panel, {})[str(c)] = int(ds_)
            else:
                dstar.setdefault(panel, {})[str(c)] = None
                dstar[panel][f"{c}_note"] = "no ratio-day job or eager record"
    # ---- ratio-day series (sf_e4)
    ratio = {}
    for panel in PANELS:
        for pred in perturb.PREDICTIONS:
            for s in SERIES:
                frac = s in FRAC_SERIES
                vl, vi, vc, xs, xcs, etas, lbs, lcs, n = [], [], [], {}, {}, {}, {}, {}, 0
                for c in al:
                    doc = ratio_docs.get((panel, c, pred))
                    if doc is None:
                        continue
                    lp, milp, core = eager_in[(panel, c)]
                    b = mc.bench_values(lp, milp)
                    lc = _core_value(core)
                    etas[str(c)] = doc["eta_q"]
                    lbs[str(c)] = b["LB"]
                    xs[str(c)] = doc["eta_q"] / b["LB"] if b["LB"] else None
                    if frac:
                        lcs[str(c)] = lc
                        xcs[str(c)] = doc["eta_q"] / lc if lc else None
                    for r in doc["runs"]:
                        alg = _series_value(r, s)
                        if alg is None:
                            continue
                        lb = mc.lb_record(alg, lp, milp, reason=r.get("ratio_validity"))
                        n += 1
                        if lb.get("ratio_LB") is not None:
                            vl.append(lb["ratio_LB"])
                        if lb.get("ratio_inc") is not None:
                            vi.append(lb["ratio_inc"])
                        if frac and lc:
                            vc.append(alg / lc)
                note = "no ratio-day run with a lower bound for this (panel, prediction)"
                ent = {"style_key": s, "label": perturb.LABELS[pred], "n_runs": n,
                       "cost_model": "pd_covering" if frac else "full", "x_by_c": xs, "eta_q_by_c": etas,
                       "LB_by_c": lbs, "ratio_LB": _agg(vl, note), "ratio_inc": _agg(vi, note)}
                put(ent, "x", _median(xs.values()), "no ratio-day run or no positive LB_eager")
                ent["median"], ent["median_ci95"] = ent["ratio_LB"]["median"], ent["ratio_LB"]["median_ci95"]
                if ent["median"] is None:
                    put(ent, "median", None, note)
                    ent["median_ci95_note"] = note
                put(ent, "inc_median", ent["ratio_inc"]["median"], "no ratio-day run with an incumbent")
                # the fractional series over their own program's LP (§6.6); the combiner's run is a full-model cost
                cnote = ("no ratio-day run with a positive LP_core for this (panel, prediction)" if frac else
                         "the combiner's run is a full-model (engine) cost: only ratio_LB and ratio_inc apply")
                ent.update(LP_core_by_c=lcs, x_core_by_c=xcs, ratio_core=_agg(vc, cnote))
                put(ent, "x_core", _median(xcs.values()), cnote)
                put(ent, "core_median", ent["ratio_core"]["median"], cnote)
                ent["core_median_ci95"] = ent["ratio_core"]["median_ci95"]
                if ent["core_median"] is None:
                    ent["core_median_ci95_note"] = cnote
                ratio.setdefault(panel, {}).setdefault(pred, {})[s] = ent
    # ---- week costs over A6 without predictions (E4-6)
    week = {}
    for panel in PANELS:
        for mu in (MU_MAIN,) + MU_POINTS:
            tgt = week.setdefault(panel, {}).setdefault(num_key(mu), {})
            for pred in (tuple(perturb.PREDICTIONS) if mu == MU_MAIN else (DEFAULT_PRED,)):
                for tag in PRED_TAGS:
                    ratios_, costs = [], []
                    for c in al:
                        doc, ref = week_docs.get((panel, c, float(mu), pred)), \
                            week_docs.get((panel, c, float(mu), perturb.NONE_KEY))
                        if doc is None:
                            continue
                        base = {r["p"]: r["total"] for r in (ref or {}).get("runs", []) if r["tag"] == REF_TAG}
                        for r in doc["runs"]:
                            if r["tag"] != tag:
                                continue
                            costs.append(r["total"])
                            if base.get(r["p"]):
                                ratios_.append(r["total"] / base[r["p"]])
                    note = "no paired week run of this tag and of A6 without predictions"
                    e = {"cost_over_a6": _agg(ratios_, note), "n_pairs": len(ratios_),
                         "cost_usd": _agg(costs, "no week run"), "n_runs": len(costs)}
                    e["median"], e["median_ci95"] = e["cost_over_a6"]["median"], e["cost_over_a6"]["median_ci95"]
                    if e["median"] is None:
                        put(e, "median", None, note)
                        e["median_ci95_note"] = note
                    put(e, "mean_cost_usd", float(np.mean(costs)) if costs else None, "no week run")
                    tgt.setdefault(pred, {})[tag] = e
            refc = [r["total"] for c in al for r in (week_docs.get((panel, c, float(mu), perturb.NONE_KEY)) or {})
                    .get("runs", []) if r["tag"] == REF_TAG]
            e = {"cost_usd": _agg(refc, "no week run of A6 without predictions"), "n_runs": len(refc)}
            put(e, "mean_cost_usd", float(np.mean(refc)) if refc else None, "no week run of A6 without predictions")
            tgt[perturb.NONE_KEY] = {REF_TAG: e}
    # ---- combiner (E4-5)
    combiner = {}
    for panel in PANELS:
        for pred in perturb.PREDICTIONS:
            tgt = combiner.setdefault(panel, {}).setdefault(pred, {})
            for tag in PRED_TAGS:
                runs = [r for c in al for r in (week_docs.get((panel, c, MU_MAIN, pred)) or {}).get("runs", [])
                        if r["tag"] == tag]
                tgt[tag] = _combiner_entry(runs, "no week run with a combiner")
            runs = [r for c in al for r in (ratio_docs.get((panel, c, pred)) or {}).get("runs", [])]
            tgt[DAY_TAG] = _combiner_entry(runs, "no ratio-day run with a combiner")
    # ---- core exports (E4-5)
    core = {}
    for (panel, c, mu, _), doc in sorted(week_docs.items(), key=lambda kv: str(kv[0])):
        if doc.get("core_export") is not None:
            core.setdefault(f"{panel}:c={c}:mu={num_key(mu)}", doc["core_export"])
    for (panel, c, _), doc in sorted(ratio_docs.items(), key=lambda kv: str(kv[0])):
        if doc.get("core_export") is not None:
            core.setdefault(f"{panel}:c={c}:day", doc["core_export"])
    repro = _ok_output(out, recs, repro_id(), out / "repro_check.json", ignored)
    checks = build_checks(phat_rows, week_docs, ratio_docs, eager, core, repro, week)
    by_status: dict = {}
    for j in js:
        st = str((recs.get(j.id) or {}).get("status"))
        by_status[st] = by_status.get(st, 0) + 1
    not_ok = [j.id for j in js if (recs.get(j.id) or {}).get("status") != "ok"]
    from .e1 import MENU
    ds_run = next((doc["meta"]["day_slots"] for doc in list(ratio_docs.values()) + list(week_docs.values())),
                  d["day_slots"])
    meta = {"exp": EXP, "spec": SPEC, "git_revision": mc.git_revision(), "written": mc._now(), "reduced": d["reduced"],
            "config": CONFIG, "menu": MENU, "llms": [LLM_M], "horizon_min": WEEK_MIN, "lender_model": LENDER_MODEL,
            "panels": {k: {**v, "region": REGION, "tier": TIER} for k, v in PANELS.items()},
            "alignments": list(al), "alignments_design": list(ALIGNMENTS), "policy_seeds": list(seeds),
            "policy_seeds_design": list(POLICY_SEEDS), "mu_main": MU_MAIN, "mu_points": list(d["mu_points"]),
            "mu_points_design": list(MU_POINTS), "default_prediction": DEFAULT_PRED,
            "predictions": dict(perturb.LABELS), "predictions_run": list(d["predictions"]),
            "tags": {t: {"policy_id": v[0], "params": v[1]} for t, v in TAGS.items()}, "series": list(SERIES),
            "ratio_day": dstar, "day_slots": ds_run, "window": d["window"],
            "milp": {"limit_s": mc.milp_limit_s(), "mip_rel_gap": MILP_GAP, "grid": BENCH_GRID},
            "combiner_bound": COMB_BOUND, "status_labels": STATUS_LABELS,
            "jobs": {"n": len(js), "by_status": dict(sorted(by_status.items())), "not_ok": not_ok[:200],
                     "n_not_ok": len(not_ok)},
            "ignored_outputs": list({x["job"]: x for x in ignored}.values())}
    if ds_run is None:
        meta["day_slots_note"] = "no run output: 1440 / Δs of the instance"
    if d["reduced"]:
        meta["reduced_note"] = (f"reduced job list ({REDUCED_ENV}=1): alignment 1, policy seed 0, predictions "
                                f"{list(REDUCED['predictions'])}, mu 1 and {list(REDUCED['mu_points'])}, 2-h days of "
                                f"restrict_horizon(week, {REDUCED['window'][0]}, {REDUCED['window'][1]}); not a result")
    summ = {"meta": meta, "phat": phat, "eager": eager, "ratio": ratio, "week": week, "combiner": combiner,
            "core_export": core, "checks": checks}
    mc.dump_json(summ, out / "summary.json")
    mc.write_text(tables(summ), out / "tables.md")
    return summ


def build_checks(phat_rows: list, week_docs: dict, ratio_docs: dict, eager: dict, core: dict, repro,
                 week: dict) -> dict:
    ch = {}
    # E4-1
    if repro is None:
        ch["E4-1"] = {"status": "missing", "claim": CHECK_CLAIMS["E4-1"], "why": "repro_check.json missing (job "
                                                                                   "e4:repro)"}
    else:
        ch["E4-1"] = {"status": "pass" if repro["pass"] else "fail", "claim": CHECK_CLAIMS["E4-1"],
                      "files": repro["files"], "json": repro["json"], "quick": repro["quick"]}
    # E4-2: core (bug test), the trace slack and the bracket of §2.5 (informative)
    rows, miss = [], 0
    for (panel, c, pred), doc in sorted(ratio_docs.items(), key=lambda kv: str(kv[0])):
        b = (eager.get(panel) or {}).get(str(c)) or {}
        inc_e = b.get("incumbent")
        pd_ = doc.get("phat_day") or {}
        term = (pd_["incumbent"] - pd_["LB"]) if pd_.get("incumbent") is not None and pd_.get("LB") is not None \
            else None
        for r in doc["runs"]:
            cfp = (r.get("combiner") or {}).get("C_FP")
            if inc_e is None or term is None or cfp is None:
                miss += 1
                continue
            rows.append({"panel": panel, "c": c, "pred": pred, "p": r["p"], "slack": inc_e + doc["eta_q"] + term - cfp,
                         "incumbent_eager": inc_e, "eta_q": doc["eta_q"], "phat_gap_term": term, "C_FP": cfp})
    trace = {"status": "informative", "n_runs": len(rows), "n_without_inputs": miss,
             "n_negative": sum(1 for x in rows if x["slack"] < -TOL), "rows": rows[:200]}
    put(trace, "min_slack", min((x["slack"] for x in rows), default=None), "no ratio-day run with its inputs")
    # the bracket of §2.5: P-hat's day MILP (OPT_eager(sigma-hat)) over OPT_eager(sigma) on the ratio day
    brs = []
    for (panel, c, pred), doc in sorted(ratio_docs.items(), key=lambda kv: str(kv[0])):
        b = (eager.get(panel) or {}).get(str(c)) or {}
        pd_ = doc.get("phat_day") or {}
        br = mc.bracket({k: pd_.get(k) for k in ("incumbent", "LB", "exact", "gap")}, b)
        lb_e, inc_e, eq = _finite(b.get("LB")), _finite(b.get("incumbent")), doc["eta_q"]
        row = {"panel": panel, "c": c, "pred": pred, "eta_q": eq,
               **{k: v for k, v in br.items() if k not in ("gap_eager", "gap_omega")},
               "gap_phat": br["gap_eager"], "gap_opt_eager": br["gap_omega"]}
        put(row, "bound", 1.0 + eq / lb_e if lb_e else None, "no positive LB_eager")
        row["refuted"] = bool(br["lo"] is not None and row["bound"] is not None
                              and br["lo"] > row["bound"] * (1 + TOL))
        row["confirmed"] = bool(br["hi"] is not None and inc_e and br["hi"] <= (1.0 + eq / inc_e) * (1 + TOL))
        brs.append(row)
    bracket = {"status": "informative", "end_tested": "lo against bound = 1 + x (lo > bound refutes the step "
                                                      "whatever the gaps; hi <= 1 + q eta / incumbent_eager confirms it)",
               "n": len(brs), "n_without_values": sum(1 for x in brs if x["lo"] is None or x["bound"] is None),
               "n_refuted": sum(1 for x in brs if x["refuted"]), "n_confirmed": sum(1 for x in brs if x["confirmed"]),
               "rows": brs[:200]}
    if repro is None:
        ch["E4-2"] = {"status": "missing", "claim": CHECK_CLAIMS["E4-2"], "core": None,
                      "core_note": "repro_check.json missing (job e4:repro)", "trace": trace, "bracket": bracket}
    else:
        ce = repro["core_eta"]
        ok = ce["n_rows"] > 0 and ce["n_eta_chk_false"] == 0
        ch["E4-2"] = {"status": "pass" if ok else "fail", "claim": CHECK_CLAIMS["E4-2"], "core": ce, "trace": trace,
                      "bracket": bracket}
    # E4-3
    allr = [(f"week:{k}", r) for k, doc in week_docs.items() for r in doc["runs"]] + \
        [(f"ratio:{k}", r) for k, doc in ratio_docs.items() for r in doc["runs"]]
    inv = [f"{k} {r['tag']} p{r['p']}" for k, r in allr if r["n_invariant_failures"]]
    gpu = [f"{k} {r['tag']} p{r['p']}" for k, r in allr if r["gpu_only_lease_slots"]]
    rv = [f"ratio:{k} {r['tag']} p{r['p']}: {r.get('ratio_validity')}" for k, doc in ratio_docs.items()
          for r in doc["runs"] if r.get("ratio_validity") is not None]
    ch["E4-3"] = {"status": ("pass" if not (inv or gpu or rv) else "fail") if allr else "missing",
                  "claim": CHECK_CLAIMS["E4-3"], "n_runs": len(allr),
                  "n_ratio_runs": sum(len(doc["runs"]) for doc in ratio_docs.values()),
                  "invariant_failures": inv[:20], "gpu_only_lease_slots": gpu[:20], "ratio_validity_not_none": rv[:20]}
    # E4-4
    ok_rows = [r for r in phat_rows if r["ok"]]
    gaps = [r["gap"] for r in ok_rows if r["method"] == "milp" and _finite(r["gap"]) is not None]
    ch["E4-4"] = {"status": "informative" if ok_rows else "missing", "claim": CHECK_CLAIMS["E4-4"],
                  "n_days": len(phat_rows), "n_ok": len(ok_rows),
                  "methods": {m: sum(1 for r in ok_rows if r["method"] == m) for m in ("milp", "lp_round", "none")},
                  "milp_status": {str(s): sum(1 for r in ok_rows if r["method"] == "milp" and r["status"] == s)
                                  for s in sorted({r["status"] for r in ok_rows if r["method"] == "milp"}, key=str)},
                  "n_at_limit": sum(1 for r in ok_rows if r["method"] == "milp" and r["status"] == 1),
                  "max_gap": max(gaps) if gaps else None,
                  "lp_round_days": [f"{r['panel']}:c={r['c']}:mu={num_key(r['mu'])}:{r['pred']}:day={r['day']}"
                                    for r in ok_rows if r["method"] == "lp_round"][:50],
                  "not_ok": [{"panel": r["panel"], "c": r["c"], "mu": num_key(r["mu"]), "pred": r["pred"],
                              "day": r["day"], "job_status": r["job_status"]} for r in phat_rows if not r["ok"]][:50]}
    # E4-5
    ex_by = {}
    for (panel, c, mu, _), doc in week_docs.items():
        ex_by[("week", panel, c, mu)] = bool((doc.get("core_export") or {}).get("exact"))
    comb_runs = [(("week", panel, c, mu), r) for (panel, c, mu, pred), doc in week_docs.items() for r in doc["runs"]
                 if r["tag"] in PRED_TAGS] + \
        [(("ratio", panel, c), r) for (panel, c, pred), doc in ratio_docs.items() for r in doc["runs"]]
    ex_ratio = {("ratio", p_, c_): bool((doc.get("core_export") or {}).get("exact"))
                for (p_, c_, _), doc in ratio_docs.items()}
    ex_by.update(ex_ratio)
    rom = [(k, r["real_over_min"]) for k, r in comb_runs if r.get("real_over_min") is not None]
    above = [(k, v) for k, v in rom if v > COMB_BOUND * (1 + TOL)]
    bugs = [{"instance": ":".join(map(str, k)), "real_over_min": v} for k, v in above if ex_by.get(k)]
    e5 = {"status": ("fail" if bugs else "informative") if rom else "missing", "claim": CHECK_CLAIMS["E4-5"],
          "bound": COMB_BOUND, "n_runs": len(rom), "n_above_bound": len(above), "bugs_on_exact_exports": bugs,
          "core_export": {"n_instances": len(core), "n_exact": sum(1 for v in core.values() if v.get("exact")),
                          "n_not_exportable": sum(1 for v in core.values() if v.get("exportable") is False)}}
    put(e5, "max_real_over_min", max((v for _, v in rom), default=None), "no run with a combiner")
    ch["E4-5"] = e5
    # E4-6
    rows6 = []
    for panel, by_mu in week.items():
        for mk, by_p in by_mu.items():
            for pred, by_t in by_p.items():
                for tag, e in by_t.items():
                    if tag in PRED_TAGS and e.get("median") is not None:
                        rows6.append({"panel": panel, "mu": mk, "pred": pred, "tag": tag, "median": e["median"],
                                      "n_pairs": e["n_pairs"]})
    ch["E4-6"] = {"status": "informative" if rows6 else "missing", "claim": CHECK_CLAIMS["E4-6"],
                  "n_entries": len(rows6), "entries": rows6}
    return ch


def tables(s: dict) -> str:
    L = ["# E4: predictions (design/sim_spec_ms4.md §6)", ""]
    if s["meta"].get("reduced"):
        L += [f"*{s['meta']['reduced_note']}*", ""]
    L += ["## P-hat days (E4-4): methods and MILP statuses", ""]
    rows = []
    for panel, by_c in s["phat"].items():
        for ck, by_mu in by_c.items():
            for mk, by_p in by_mu.items():
                for pred, e in by_p.items():
                    gaps = [x.get("gap") for x in e["days"].values() if x.get("method") == "milp"
                            and x.get("gap") is not None]
                    rows.append([panel, ck, mk, pred, e["methods"]["milp"], e["methods"]["lp_round"],
                                 e["methods"]["none"], e.get("n_cols"), max(gaps) if gaps else None, e["assembled"]])
    L.append(mc.md_table(["panel", "c", "mu", "pred", "milp", "lp_round", "none", "columns", "max gap", "assembled"],
                         rows))
    L += ["## OPT_eager of the ratio day, and LP_core (the PDs' covering program)", ""]
    L.append(mc.md_table(["panel", "c", "d*", "LB", "LB source", "incumbent", "gap", "MILP status", "LP_core"],
                         [[p, ck, e.get("d_star"), e.get("LB"), e.get("LB_source"), e.get("incumbent"), e.get("gap"),
                           e.get("milp_status"), e.get("LP_core")]
                          for p, by_c in s["eager"].items() for ck, e in by_c.items()]))
    L += ["## Ratio day: x = q eta / LB_eager and ALG / LB (median over alignments x seeds)", ""]
    L.append(mc.md_table(["panel", "pred", "x"] + list(SERIES),
                         [[p, pred, by_s[SERIES[0]].get("x")] + [by_s[x].get("median") for x in SERIES]
                          for p, by_p in s["ratio"].items() for pred, by_s in by_p.items()]))
    L += ["## Ratio day, fractional series over LP_core: x_core = q eta / LP_core and ALG / LP_core (median)", ""]
    L.append(mc.md_table(["panel", "pred", "x_core"] + list(FRAC_SERIES),
                         [[p, pred, by_s[FRAC_SERIES[0]].get("x_core")] + [by_s[x].get("core_median")
                                                                            for x in FRAC_SERIES]
                          for p, by_p in s["ratio"].items() for pred, by_s in by_p.items()]))
    L += ["## E4-2: P-hat's MILP over OPT_eager on the ratio day (bracket of §2.5; lo tested against 1 + x)", ""]
    br = s["checks"]["E4-2"]["bracket"]
    L.append(mc.md_table(["panel", "c", "pred", "point", "lo", "hi", "1 + x", "refuted", "confirmed"],
                         [[r["panel"], r["c"], r["pred"], r["point"], r["lo"], r["hi"], r["bound"], r["refuted"],
                           r["confirmed"]] for r in br["rows"]]))
    L += ["## Week cost over A6 without predictions (E4-6; median over alignments x seeds)", ""]
    L.append(mc.md_table(["panel", "mu", "pred", "A5", "A6-pred", "pairs"],
                         [[p, mk, pred, by_t["A5"].get("median"), by_t["A6-pred"].get("median"),
                           by_t["A5"].get("n_pairs")]
                          for p, by_mu in s["week"].items() for mk, by_p in by_mu.items()
                          for pred, by_t in by_p.items() if pred != perturb.NONE_KEY]))
    L += ["## Combiner: real cost over min{C_FP, C_R} (E4-5; median, max)", ""]
    L.append(mc.md_table(["panel", "pred", "tag", "runs", "C_FP", "C_R", "median", "max", "> 5.83"],
                         [[p, pred, tag, e["n"], e.get("C_FP_mean"), e.get("C_R_mean"), e["real_over_min"]["median"],
                           e.get("max_real_over_min"), e["n_above_bound"]]
                          for p, by_p in s["combiner"].items() for pred, by_t in by_p.items()
                          for tag, e in by_t.items()]))
    L += ["## Checks (§6.9)", ""]
    L.append(mc.md_table(["check", "status"], [[k, v["status"]] for k, v in s["checks"].items()]))
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                     description=__doc__))
