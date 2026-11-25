"""S1: sensitivity of Sublet's saving across the register, and Q28's stress variants (design/sim_spec_ms5.md §3, §4,
§2.4; deliverable D40, unit U27; open choices M1-M15, M35, M37). The supplementary tornado sf_s1 and the tables
s1_points.tex and s1_q28.tex read the two summaries (§7.1).

Instance (§3.3). The E7 main week: configs/bench_e7f.json through ms4_common.e7_spec at mu / beta~ = 1 (one week of
1-min routing on 5-min slow slots, the full a11 menu, all 24 lenders, regional borrowers, the trace lender with I1,
'sell', violations absorbed, engine.check_invariants true, unmerged layers), config seed = lender seed = alignment c.
A sweep point adds its overrides (dotted paths of drivers.run.set_path on the raw config) to e7_spec's;
point_overrides(name, ref) is the one builder of a point's overrides, ref being the default build of the same alignment
and horizon (for alpha and alpha_p the default's resolved q^GPU, for the scenario points the default's resolved
xi_sources, for the protected-term points the default's resolved contracts, for fee4 calib.beta_for_rho on the default
build), ported from out/ms5spec/s1_sizing.py and s1_rows_build.py (test_s1 checks the overrides and the instance hashes
at alignment 1 against their outputs). The builder solves Gamma again at every point (M3), so a point that changes the
supply or the LLMs keeps the default's market tightness and has its own BL0a (e6.bl0a_all on its own instance) and its
own allowance (M4).

Policy (§3.6, §4.3). Part sweep: Sublet only, A8 around BL5 with ms4_common.sublet_params(inst, 'BL5') on the point's
own instance (gamma 1, kappa None, B0 = 0.1 x BL0a; M36 of MS4, M4 here), the A8 record and certificate of
ms4_common.a8_record, info_class_reported 'online-I1 + a-priori N + a-priori BL0a'. Part q28: E7's eight tags with their
E7 parameters (e7.tag_params on the run's own instance: Sublet, A7G, A7, A6, BL5, BL1, BL2 through
ms4_common.siloed_run, BL4) and BL3 with E5's defaults (BL3 {}, n_extra 2, style key 'bl3') (M11).

Points (§3.4; POINTS, ROWS): 50 points in 24 register rows and the default point, plus the mu row read from E7's
versioned summary (M9: code/sim/out/e7/main/summary.json runs.<mu>.Sublet at mu in {0.2, 0.5, 2}, nothing rerun). The
rows and points not run, with their reasons, are NOT_RUN (§3.5, M7). Q28's variants (§4.4, M14): L-rf
(lender_model.on_unavailable 'refuse' on the trace schedule) and L-vr (lender_model.violations 'reclaim'), each alone,
through ms4_common.mode_lender_model (q44_study.MODES). Seeds (§3.7, §4.5): alignments 1-4 x policy seeds 0-2.

Jobs (§3.8, §4.6; ids by ms3_common.job_id; every job a 'pool' job with its three policy seeds in order):
  part sweep  s1:sweep:pt=<point>:c=<c>             51 points x 4 alignments (204 jobs)
  part q28    s1:q28:var=<rf|vr>:pol=<tag>:c=<c>    2 variants x 9 tags x 4 alignments (72 jobs)
              s1:q28:var=default:pol=BL3:c=<c>      BL3 under the default lender, its reference (4 jobs)
Job limits (§3.9, §11.1): three times the job's estimate, at least LIMIT_MIN_S = 1,800 s (limit_s in the job's
parameters; `--limits` prints '<kind> <limit_s> <job id>' per line, and run_s1.sh runs each job under `timeout
--foreground -k 30 (<limit_s> + 60)` and classifies a failure with that limit, as ms3_lib.sh runs a MILP job). The estimate of one week run is the build and engine time of measurement 1 where it
was measured (EST_MEASURED_S, from out/ms5spec/s1_sizing_<case>.json run.times), elsewhere the default's time scaled by
the point's client units over the default's (EST_UNITS, from out/ms5spec/s1_rows_build.json; estimate), and for part
q28 the case wall of measurement 3 (EST_Q28_S, from out/ms5spec/q28_sizing_<variant>_<tag>.json meta.wall_s); a job's
estimate is its number of policy seeds times the run's, scaled by the horizon. Jobs are listed longest first within
each part (list scheduling on the four slots).

S1_PART (environment): 'sweep', 'q28' or unset (both) selects the jobs that --list prints and the parts --summary
builds, as E7_PART does for E7. run_s1.sh runs each part with S1_PART=<part> and --out out/s1/<part>, so each part has
its own jobs/, logs/, runs/, manifest.json, summary.json, tables.md and run_s1.log (ms3_common.COPY_PARTS['s1'], C30);
a part's files go to <out> if its name is the part's, else to <out>/<part>. Pass 1 runs part sweep's jobs, then part
q28's; pass 2 the summaries of sweep and q28, since q28's summary reads sweep's (Sublet's reference, S1's default
point).

Command line (ms3_common.main, MS4 spec §2.4), run from code/sim:
  python -m sublet.experiments.s1 --list | --job ID | --summary | --estimate | --manifest  [--out DIR]
  python -m sublet.experiments.s1 --limits                  '<kind> <limit_s> <job id>' per line (run_s1.sh)
Reduced runs (smoke tests): MS3_S1_REDUCED=1 (run_s1.sh --reduced sets it) keeps every point, variant and tag, with
alignment 1 only, policy seed 0 only and a 2-hour horizon (REDUCED_HORIZON_MIN); its summaries carry meta.reduced
true and are never a result.

Run files (not versioned): <part>/runs/<job file>.json. Sweep: the point, its row, value and overrides, the instance's
sizes, hashes and references, vs_default (the facts of check S1-1 against the default build of the alignment:
instance hashes, BL0a, Gamma, client units, the demand matched client by client by (LLM, region, borrowers), the LLMs
without clients and without a fitting layer site), and per policy seed e7.run_entry's entry (ALG, both accountings,
components, metrics, invariants, the A8 record and certificate) with saving_pct and saving_pct_total. Q28: the variant,
tag, lender model, the instance's sizes, hash and references, ratio_validity and ratio_validity_default (the reasons
of drivers.run.ratio_validity for the grids fast, slow_lb and slow under the variant's and under the config's default
lender model), unavailable_share, and per policy seed e7.run_entry's (or e7.siloed_entry's) entry with saving_pct,
refused ({capacity, unavailable}: the engine's counts, summed over BL2's sub-runs), violations (events, lender-slots,
deficits, attributable deficits, the engine's sums), violation_victims (each lease ended by a violation with its site,
lender, LLM, slot and GPUs) and both ratio-validity maps, read from the RunResult as out/ms5spec/q28_sizing.py reads
them.

sweep/summary.json (§3.8)
  meta              exp, part, spec, git_revision, written, reduced (reduced_note), grids {points, alignments,
                    policy_seeds and their design values, horizon_min}, points {name: {row, value, label, gamma_row}},
                    rows_order, tag (Sublet's policy id, parameter rule, style key), B0_rule, info_class_reported_a8,
                    default_references {c: ms4_common.references of the default point's instance}, instances
                    {point: {c: {instance_hash, bl0a_usd, gamma, n_units, overrides}}}, e7_summary (file, exists,
                    sha256, git_revision, reduced), jobs_ok, jobs_missing, ignored_outputs
  points.<name>     e7.cost_entry over the point's runs (n_runs, alignments, policy_seeds, both accountings,
                    saving_pct and saving_pct_total as metrics.aggregate {n, median, p95, max, median_ci95} with mean,
                    fallback_share_after_reclaims, abort_share, t_a, certificates {n, held, by_case, failures},
                    n_runs_with_invariant_failures, ...) plus row, value, label, gamma_row, n_runs_expected,
                    bl0a_usd {c: BL0a} and overflow_over_bl0a (the aggregate of the cost over BL0a)
  rows.<row>        label, panel, gamma_row, default_label, points {name: {value, label, saving_pct_median, n_runs}},
                    default {label, saving_pct_median}, lo, hi (the lowest and highest median saving over the row's
                    points and the default), lo_point, hi_point (the first attaining name, 'default' first), lo_points,
                    hi_points (every attaining name), span = hi - lo, points_missing, complete; the mu row (source 'e7')
                    with E7's medians and their file
  not_run           NOT_RUN: {row, reason, sources} per row or point of §3.5
  certificates      ms4_common.count_certificates over every A8 run of the part, w_c_runs
  checks            S1-0 ... S1-4 (§3.10)
q28/summary.json (§4.6)
  meta              as sweep's, with variants {variant: {mode, lender_model}}, tags {tag: {policy_id, params,
                    style_key, a8}}, references {c: ms4_common.references}, instances {c: {instance_hash, ...}},
                    sweep_summary (file, used, used_note, git_revision, reduced)
  runs.<variant>.<tag>  the fields of E7's runs.<mu>.<tag> (e7.cost_entry) plus refusals {unavailable, capacity},
                    violation_events, violation_lender_slots, violation_victims (aggregates over the runs),
                    n_runs_with_violations, ratio_validity {grid: the reasons found}, reference {source,
                    overflow_over_bl0a_median, saving_pct_median} and delta_overflow_over_bl0a (the median minus the
                    reference's), for Sublet also reference_s1_default and delta_overflow_over_bl0a_s1_default;
                    variants rf and vr for the nine tags, variant default for BL3
  rows.q28_rf, rows.q28_vr   Sublet's two tornado rows (M13) in the form of the sweep's rows: the variant's median
                    saving and S1's default point
  certificates, checks   Q28-1 ... Q28-4 (§4.7)

Statuses of checks.<id>.status: pass, fail, missing, informative (MS4 spec §2.6). A check is 'missing' while a job of
its grid has no 'ok' record or no run of it exists, unless an existing run fails it; Q28-1 also fails on a job that
ended with status error, failed, oom_at_3G or wall_limit (its runs did not finish).

Status labels (copied from design/sim_spec_ms5.md §3.1, §4.1, never upgraded): S1 is a sensitivity study with no theory
claim; Theorem W(a)(b) PROVEN for the engine as implemented under C1-C3 and audited (the additive envelope with B = B0);
W(c) CONJECTURE, checked per run by the certificate.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import copy
import gc
import hashlib
import math
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .. import paths
from . import e7
from . import ms3_common as mc
from . import ms4_common as m4
from .ms3_common import Job, job_id, num_key, put

EXP = "s1"
SPEC = "design/sim_spec_ms5.md §3, §4"
PARTS = mc.COPY_PARTS[EXP]                         # ("sweep", "q28"), C30
PASS_JOBS = ("sweep", "q28")                       # run_s1.sh pass 1
PASS_SUMMARIES = ("sweep", "q28")                  # pass 2: q28's summary reads sweep's (§4.4)
ALIGNMENTS = (1, 2, 3, 4)                          # §3.7, §4.5 (M35)
POLICY_SEEDS = (0, 1, 2)
MU = 1.0                                           # the E7 main week at mu / beta~ = 1 (§3.3)
INNER = "BL5"
TAG = "Sublet"                                     # the sweep's policy (§3.6)
DEFAULT = "default"
REDUCED_ENV = "MS3_S1_REDUCED"
REDUCED_HORIZON_MIN = 120                          # a 2-hour horizon (24 slow slots)
LIMIT_MIN_S = 1800                                 # §3.9: a job's limit is 3 x its estimate, at least 1,800 s
LIMIT_FACTOR = 3.0
REL_TOL = 1e-9                                     # S1-0 (§3.10)
SPAN_INFORMATIVE_PP = 10.0                         # S1-4: the rows whose span exceeds 10 percentage points
RATIO_GRIDS = ("fast", "slow_lb", "slow")          # drivers.run.ratio_validity's grids (q28_sizing.py)
VICTIMS_MAX = 500                                  # victims listed per run (the counts are complete)
E7_SUMMARY = paths.SIM_OUT / "e7" / "main" / "summary.json"      # versioned (MS4, commit 939847ca)
E7_SUMMARY_REL = "code/sim/out/e7/main/summary.json"
E7_MUS = (0.2, 0.5, 2.0)                           # the mu row (M9)
G16_POINTS = ("a5", "L16", "layer16")              # the points with g^lay 16 (S1-1)
VIOL_METRICS = ("violation_lender_slots", "violation_lender_slots_attributable", "violation_deficit_gpu_slots",
                "violation_deficit_attributable_gpu_slots", "lender_slots_checked")
GAMMA_RE = re.compile(r"regional demand: Gamma = ([0-9.eE+-]+)")

# §3.9: seconds per week run. Measured (measurement 1, build_s + engine_s of out/ms5spec/s1_sizing_<case>.json
# run.times, one Sublet week at alignment 1 and policy seed 0; wan1g is the point scen_cold_wan_1gbps) ...
EST_MEASURED_S = {"default": 141.7, "slow1": 616.7, "layer16": 241.6, "nlayers16": 377.4, "L16": 164.5, "a5": 88.4,
                  "tight2": 463.1, "tight025": 85.0, "alpha02": 134.5, "alpha06": 144.6,
                  "scen_cold_wan_1gbps": 144.3, "prothorizon": 142.4, "buf999": 138.1}
# ... and elsewhere the default's time scaled by the point's client units at alignment 1 over the default's 2,511
# (out/ms5spec/s1_rows_build.json table[].units; estimate)
EST_DEFAULT_UNITS = 2511
EST_UNITS = {"alpha03": 2511, "alpha05": 2511, "alphap06": 2511, "alphap10": 2511, "kv05": 2511, "kv10": 2511,
             "scen_warm_peer_rdma": 2511, "scen_ssd_optimized": 2511, "scen_ssd_stock_safetensors": 2511,
             "scen_ssd_stock_pytorch": 2511, "scen_a5_10GBps": 2511, "scen_a5_2GBps": 2511,
             "scen_cold_wan_10gbps": 2511, "phi05": 2511, "kappaL05": 1859, "kappaL2": 3302, "catM2": 1925,
             "catLg4": 3694, "tiermap": 2024, "sS0": 2335, "sS05": 2810, "xi1": 3393, "wcfull": 1831, "c0p50": 2531,
             "c0p90": 2492, "smooth5": 2522, "smooth60": 2561, "lease10": 2465, "lease50": 2712, "nlayers4": 1290,
             "prot1h": 2511, "prot1d": 2511, "tight1": 5016, "delta0": 2511, "delta02": 2511, "strict": 2511,
             "slotier": 2511, "fee4": 2511}
# measurement 3's case walls (out/ms5spec/q28_sizing_<variant>_<tag>.json meta.wall_s; one week at alignment 1)
EST_Q28_S = {("rf", "Sublet"): 143.4, ("rf", "A7G"): 196.3, ("rf", "A7"): 63.6, ("rf", "A6"): 50.8,
             ("rf", "BL5"): 11.4, ("rf", "BL1"): 11.9, ("rf", "BL2"): 25.8, ("rf", "BL4"): 29.4, ("rf", "BL3"): 14.7,
             ("vr", "Sublet"): 141.2, ("vr", "A7G"): 194.8, ("vr", "A7"): 63.1, ("vr", "A6"): 49.6,
             ("vr", "BL5"): 11.1, ("vr", "BL1"): 11.9, ("vr", "BL2"): 25.6, ("vr", "BL4"): 29.0, ("vr", "BL3"): 14.7,
             ("default", "BL3"): 15.0}

# Q28 (§4.3, §4.4; M11, M14): the variants' lender modes (q44_study.MODES) and the policies
VARIANTS = {"rf": "L-rf", "vr": "L-vr", "default": "L-tr"}
STRESS_VARIANTS = ("rf", "vr")
Q28_TAGS = tuple(e7.TAGS) + ("BL3",)              # E7's eight tags (Sublet, A7G, A7, A6, BL5, BL1, BL2, BL4) and BL3
BL3 = {"id": "BL3", "params": {}, "style": "bl3"}  # E5's BL3-2 (baselines/spothedge.py PARAMS), not an E7 tag
REF_TAG_BL3 = "BL3"                                 # the tag whose reference is part q28's own default jobs

CHECK_IDS_SWEEP = ("S1-0", "S1-1", "S1-2", "S1-3", "S1-4")
CHECK_IDS_Q28 = ("Q28-1", "Q28-2", "Q28-3", "Q28-4")
CHECK_CLAIMS = {
    "S1-0": "the default point's twelve runs equal E7's (code/sim/out/e7/main/summary.json runs.1.Sublet: median, "
            "p95, max and mean of overflow_usd within 1e-9 relative, and the instance hashes of meta.instances equal)",
    "S1-1": "every point is built as §3.4 states: its instance hash differs from the default's; on the rows without "
            "Gamma the demand, compared client by client, and BL0a equal the default's exactly; the points with g^lay "
            "16 (every point, checked) have every LLM on a fitting layer site; every LLM but S at sS0 has clients",
    "S1-2": "every A8 run has its certificate (available true), and in Theorem W's proven cases (W(a), W(b); PROVEN "
            "for the engine as implemented under C1-C3, audited) it holds; W(c) runs (CONJECTURE) are counted and "
            "listed",
    "S1-3": "no run has an invariant failure",
    "S1-4": "the saving per point and the span per row (informative), with the rows whose span exceeds 10 "
            "percentage points named",
    "Q28-1": "every run of every policy under both variants (and BL3's reference runs under the default lender) "
             "finishes with no invariant failure and handles every refusal and every violation death (no error "
             "record)",
    "Q28-2": "every L-vr run reports no ratio (ratio_validity non-null for every grid) and every L-rf run on the "
             "trace schedule keeps its ratio validity as under the default lender (the same reason for every grid); "
             "every stress run file records its variant's lender model (the L-rf half holds by construction once "
             "the lender model is L-rf's)",
    "Q28-3": "every A8 run under both variants has its certificate (available true), and in Theorem W's proven "
             "cases (W(a), W(b); PROVEN for the engine as implemented under C1-C3, audited) it holds; W(c) runs "
             "(CONJECTURE) are counted and listed",
    "Q28-4": "the change of each policy's median cost over BL0a against its reference, the refusals and the "
             "violation victims (informative)"}


# ---------------------------------------------------------------- the register: points, rows, rows not run
@dataclass(frozen=True)
class Point:
    """One sweep point (§3.4): its row (a ROWS key), the swept value (a number or a text), its short label for the
    figure's end labels, and the builder of its overrides from the default build `ref` of the same alignment."""
    name: str
    row: str
    value: object
    label: str
    build: Callable


@dataclass(frozen=True)
class Row:
    """One register row of design Table 5.6 that S1 sweeps (§3.4): its label, its panel of the tornado (§7.1), whether
    its points change the demand through Gamma (M3), the default's label and the register key."""
    key: str
    label: str
    panel: str
    gamma: bool
    default_label: str
    config_key: str


def _llm_index(ref, lid: str) -> int:
    """The index of the LLM `lid` in the default build's llms (the raw config's order)."""
    ids = [x["id"] for x in ref.config["llms"]]
    if ids.count(lid) != 1:
        raise ValueError(f"the default build's llms {ids} do not hold {lid!r} exactly once")
    return ids.index(lid)


def _static(ov: dict) -> Callable:
    return lambda ref: copy.deepcopy(ov)


def _q_gpu(ref) -> float:
    return float(ref.config["prices"]["q_gpu_usd_per_gpu_h"])


def _ov_alpha(alpha: float) -> Callable:
    """a^0 = alpha x the default's resolved q^GPU (config.py does not derive a^0 from alpha; s1_sizing._ov_alpha)."""
    return lambda ref: {"prices.a0_usd_per_gpu_h": alpha * _q_gpu(ref)}


def _ov_alpha_p(alpha_p: float) -> Callable:
    """The protected price alpha_p x the default's resolved q^GPU (s1_rows_build._pt_alphap)."""
    return lambda ref: {"prices.a_protected_usd_per_gpu_h": alpha_p * _q_gpu(ref)}


def _ov_scenario(scen: str) -> Callable:
    """The a11 load-time scenario at every site, with the default's resolved xi sources and offsets pinned (a fixed
    scenario removes the step-6 permutation of config._resolve_random, after which step 7 would re-draw the
    offsets; s1_sizing._ov_wan(True), s1_rows_build._pt_scen)."""
    def f(ref):
        return {"lender_defaults.load_scenario": scen, "protected_per_region.load_scenario": scen,
                "borrowers.xi_sources": copy.deepcopy(ref.config["borrowers"]["xi_sources"])}
    return f


def _ov_kappa(lid: str, mult: float) -> Callable:
    """kappa of the LLM `lid` alone x mult (M8; s1_rows_build._pt_kappa_llm)."""
    def f(ref):
        i = _llm_index(ref, lid)
        base = float(ref.config["llms"][i].get("kappa_mult", 1.0))
        return {f"llms.{i}.kappa_mult": mult * base}
    return f


def _ov_entry(lid: str, entry: str, extra: Optional[dict] = None) -> Callable:
    """The LLM `lid` as another entry of its catalog (s1_rows_build._pt_entry; L16 with g^lay 16, M12)."""
    def f(ref):
        return {f"llms.{_llm_index(ref, lid)}.entry": entry, **copy.deepcopy(extra or {})}
    return f


def _ov_a5(ref) -> dict:
    """The a5 tiers (catalog a5_llama3; ids and kappa_mult kept) with g^lay 16 (s1_sizing._ov_a5)."""
    from ..traces.catalog import A5_TIER
    llms = [{"id": x["id"], "catalog": "a5_llama3", "entry": A5_TIER[x["tier"]], "kappa_mult": x["kappa_mult"]}
            for x in ref.config["llms"]]
    return {"llms": llms, "lender_defaults.layer_gpus": 16}


def _ov_xi1(ref) -> dict:
    """Every region takes the first region's default series at its own default offset (s1_rows_build._pt_xi1)."""
    xs = ref.config["borrowers"]["xi_sources"]
    regs = list(ref.config["regions"]["list"])
    first = xs[regs[0]]["series"]
    return {"borrowers.xi_sources": {o: {"series": first, "offset_min": int(xs[o]["offset_min"])} for o in regs}}


def _ov_protected(minutes: Optional[int]) -> Callable:
    """menu_preset null and the default's resolved contracts with the protected contract's prepaid_min set to
    `minutes` (None: the horizon) (s1_sizing._ov_contracts; an identical list gives the default's hashes)."""
    def f(ref):
        con = copy.deepcopy(ref.config["contracts"])
        m = int(ref.config["time"]["horizon_min"]) if minutes is None else int(minutes)
        for c in con:
            if c["tau_min"] is None:
                c["prepaid_min"] = m
        return {"menu_preset": None, "contracts": con}
    return f


def _ov_fee(target: float) -> Callable:
    """costs.beta_jl_usd = calib.beta_for_rho(default build, target) per LLM (M10; s1_rows_build._pt_fee)."""
    def f(ref):
        from .. import calib
        return {"costs.beta_jl_usd": calib.beta_for_rho(ref, float(target))}
    return f


# the eight a11 load-time scenarios (calib.scenarios(), checked by test_s1) and their short labels
SCENARIOS = (("warm_peer_rdma", "warm peer"), ("ssd_optimized", "SSD optimized"),
             ("ssd_stock_safetensors", "SSD safetensors"), ("ssd_stock_pytorch", "SSD PyTorch"),
             ("a5_10GBps", "10 GB/s"), ("a5_2GBps", "2 GB/s"), ("cold_wan_10gbps", "WAN 10 Gb/s"),
             ("cold_wan_1gbps", "WAN 1 Gb/s"))

# §3.4, in its order; panels of §7.1: (a) prices, costs and timing, (b) LLMs and demand, (c) lenders and contracts
ROWS = {r.key: r for r in (
    Row("alpha", "alpha = a0 / q^GPU", "a", False, "0.40", "prices.a0_usd_per_gpu_h"),
    Row("alpha_p", "alpha_p", "a", False, "0.83", "prices.a_protected_usd_per_gpu_h"),
    Row("mu", "mu / beta~", "a", False, "1", "stranding.mu_over_beta_tilde"),
    Row("mu_split", "split of mu", "a", False, "0", "stranding.kv_share"),
    Row("load_scenario", "load-time scenario", "a", False, "a5 pair",
        "lender_defaults.load_scenario, protected_per_region.load_scenario, borrowers.xi_sources"),
    Row("phi", "phi", "a", False, "1", "costs.phi"),
    Row("kappa_L", "kappa of L", "b", True, "x1", "llms.<L>.kappa_mult"),
    Row("catalog", "LLM catalog", "b", True, "MaaS", "llms, llms.<M>.entry, llms.<L>.entry"),
    Row("precision", "weight precision", "b", True, "8 bit", "llms.<L>.entry, lender_defaults.layer_gpus"),
    Row("gpt4o_mini", "gpt-4o-mini tier", "b", True, "M", "borrowers.wildchat_model"),
    Row("s_S", "s_S", "b", True, "0.25", "borrowers.s_S"),
    Row("xi", "fluctuation sources xi", "b", True, "per region", "borrowers.xi_sources"),
    Row("wildchat", "WildChat window", "b", True, "early", "borrowers.wildchat_model"),
    Row("own_capacity", "own capacity C0", "b", True, "P75", "borrowers.own_capacity_quantile"),
    Row("smoothing", "smoothing window", "b", True, "15 min", "borrowers.smoothing_min"),
    Row("lease_quantile", "lease-size quantile", "c", True, "P25", "lender_defaults.lease_size_quantile"),
    Row("layer_width", "layer width", "c", True, "8 GPUs", "lender_defaults.layer_gpus"),
    Row("n_layers", "offered layers V_l", "c", True, "8", "lender_defaults.n_layers"),
    Row("protected_term", "protected minimum billed term", "c", False, "5 min",
        "menu_preset, contracts (protected prepaid_min)"),
    Row("buffer_quantile", "buffer quantile", "c", True, "0.99", "prices.buffer_quantile"),
    Row("tightness", "market tightness", "b", True, "0.5", "borrowers.market_tightness"),
    Row("delta1", "delta_1 / q", "a", False, "0.05", "regions.relaxed_routing_cost_over_q"),
    Row("slo_class", "adjacency and SLO class", "c", False, "relaxed",
        "regions.default_slo_class, borrowers.slo_class"),
    Row("transfer_fee", "transfer fee", "a", False, "0", "costs.beta_jl_usd"),
    Row("slow_slot", "slow-loop slot", "a", False, "5 min", "time.slow_slot_min"),
)}
MU_ROW = "mu"                                      # read from E7 (M9); no point runs

_POINT_LIST = [
    Point(DEFAULT, "", None, "default", _static({})),
    Point("alpha02", "alpha", 0.2, "0.2", _ov_alpha(0.2)),
    Point("alpha03", "alpha", 0.3, "0.3", _ov_alpha(0.3)),
    Point("alpha05", "alpha", 0.5, "0.5", _ov_alpha(0.5)),
    Point("alpha06", "alpha", 0.6, "0.6", _ov_alpha(0.6)),
    Point("alphap06", "alpha_p", 0.6, "0.6", _ov_alpha_p(0.6)),
    Point("alphap10", "alpha_p", 1.0, "1.0", _ov_alpha_p(1.0)),
    Point("kv05", "mu_split", 0.5, "0.5", _static({"stranding.kv_share": 0.5})),
    Point("kv10", "mu_split", 1.0, "1", _static({"stranding.kv_share": 1.0})),
    *[Point(f"scen_{s}", "load_scenario", s, lab, _ov_scenario(s)) for s, lab in SCENARIOS],
    Point("phi05", "phi", 0.5, "0.5", _static({"costs.phi": 0.5})),
    Point("kappaL05", "kappa_L", 0.5, "x0.5", _ov_kappa("L", 0.5)),
    Point("kappaL2", "kappa_L", 2.0, "x2", _ov_kappa("L", 2.0)),
    Point("a5", "catalog", "a5 tiers", "a5 tiers", _ov_a5),
    Point("catM2", "catalog", "M on 2 GPUs", "M on 2 GPUs", _ov_entry("M", "M_g_gpu_hours")),
    Point("catLg4", "catalog", "L as 235B on 4 GPUs", "L 235B", _ov_entry("L", "L_g4")),
    Point("L16", "precision", "L at 16 bits on 16 GPUs", "16 bit",
          _ov_entry("L", "L_16bit", {"lender_defaults.layer_gpus": 16})),
    Point("tiermap", "gpt4o_mini", "L", "L", _static({"borrowers.wildchat_model": "early_card_map"})),
    Point("sS0", "s_S", 0.0, "0", _static({"borrowers.s_S": 0.0})),
    Point("sS05", "s_S", 0.5, "0.5", _static({"borrowers.s_S": 0.5})),
    Point("xi1", "xi", "Azure 2024 conversation for every region", "one series", _ov_xi1),
    Point("wcfull", "wildchat", "the whole trace", "full", _static({"borrowers.wildchat_model": "full"})),
    Point("c0p50", "own_capacity", 50.0, "P50", _static({"borrowers.own_capacity_quantile": 50.0})),
    Point("c0p90", "own_capacity", 90.0, "P90", _static({"borrowers.own_capacity_quantile": 90.0})),
    Point("smooth5", "smoothing", 5, "5 min", _static({"borrowers.smoothing_min": 5})),
    Point("smooth60", "smoothing", 60, "60 min", _static({"borrowers.smoothing_min": 60})),
    Point("lease10", "lease_quantile", 10, "P10", _static({"lender_defaults.lease_size_quantile": 10})),
    Point("lease50", "lease_quantile", 50, "P50", _static({"lender_defaults.lease_size_quantile": 50})),
    Point("layer16", "layer_width", 16, "16 GPUs", _static({"lender_defaults.layer_gpus": 16})),
    Point("nlayers4", "n_layers", 4, "4", _static({"lender_defaults.n_layers": 4})),
    Point("nlayers16", "n_layers", 16, "16", _static({"lender_defaults.n_layers": 16})),
    Point("prot1h", "protected_term", 60, "1 h", _ov_protected(60)),
    Point("prot1d", "protected_term", 1440, "1 day", _ov_protected(1440)),
    Point("prothorizon", "protected_term", "the horizon", "horizon", _ov_protected(None)),
    Point("buf999", "buffer_quantile", 0.999, "0.999", _static({"prices.buffer_quantile": "p99.9"})),
    Point("tight025", "tightness", 0.25, "0.25", _static({"borrowers.market_tightness": 0.25})),
    Point("tight1", "tightness", 1.0, "1", _static({"borrowers.market_tightness": 1.0})),
    Point("tight2", "tightness", 2.0, "2", _static({"borrowers.market_tightness": 2.0})),
    Point("delta0", "delta1", 0.0, "0", _static({"regions.relaxed_routing_cost_over_q": 0.0})),
    Point("delta02", "delta1", 0.2, "0.2", _static({"regions.relaxed_routing_cost_over_q": 0.2})),
    Point("strict", "slo_class", "every client strict", "all strict",
          _static({"regions.default_slo_class": "strict"})),
    Point("slotier", "slo_class", "S strict, M and L relaxed", "S strict",
          _static({"borrowers.slo_class": {"S": "strict", "M": "relaxed", "L": "relaxed"}})),
    Point("fee4", "transfer_fee", 4.0, "rho = 4", _ov_fee(4.0)),
    Point("slow1", "slow_slot", 1, "1 min", _static({"time.slow_slot_min": 1})),
]
POINTS = {p.name: p for p in _POINT_LIST}
POINT_NAMES = tuple(POINTS)                        # the default first, then §3.4's order (51 names)
# the mu row: E7's points (M9), named by their value
MU_POINTS = {f"mu{num_key(m)}": (float(m), num_key(m)) for m in E7_MUS}

# §3.5 (M7): listed under the figure with their reasons
NOT_RUN = (
    {"row": "warm-peer and SSD load models", "reason": "no sweep in the register",
     "sources": ["design/Sublet_design.md Table 5.6"]},
    {"row": "client unit 1/u", "reason": "no sweep in the register", "sources": ["design/Sublet_design.md Table 5.6"]},
    {"row": "pool width zeta", "reason": "no sweep in the register", "sources": ["design/Sublet_design.md Table 5.6"]},
    {"row": "tier map", "reason": "its sweep is its default", "sources": ["design/Sublet_design.md Table 5.6"]},
    {"row": "per-tier tokens-per-conversation factor", "reason": "no traced source",
     "sources": ["design/Sublet_design.md Table 5.6"]},
    {"row": "clock alignment at local midnight",
     "reason": "not built: no source for the regions' UTC offsets (MS1 spec §10 S12)",
     "sources": ["design/sim_spec.md §10 S12"]},
    {"row": "non-causal smoothing window",
     "reason": "not built: the builder has a trailing mean only (instance._trailing_mean)",
     "sources": ["code/sim/out/ms5spec/s1_rows_build.json"]},
    {"row": "scenario assignment per region pair", "reason": "not built", "sources": ["design/sim_spec_ms5.md §3.5"]},
    {"row": "offered layers V_l as the whole block below the lease-size quantile",
     "reason": "the dense arrays of A8's safe expert exceed the 3 GB cap at the week, and a one-day probe completed "
               "one slow slot in its window; the row sweeps 4 and 16 layers in its place (M37)",
     "sources": ["code/sim/out/ms5spec/s1_sizing_wholeblock_build.json",
                 "code/sim/out/ms5spec/smoke/s1_sizing_wholeblock_week_h10080.json",
                 "code/sim/out/ms5spec/smoke/s1_sizing_wholeblock_h1440.json"]},
    {"row": "offered layers V_l as a share of the mean lendable capacity", "reason": "not defined",
     "sources": ["design/sim_spec_ms5.md §3.5"]},
    {"row": "a uniform kappa multiplier",
     "reason": "identical to the default: a uniform multiplier cancels exactly through Gamma; the row varies L's "
               "kappa alone (M8)",
     "sources": ["code/sim/out/ms5spec/s1_sizing_kappa2.json"]},
)


def point_overrides(name: str, ref) -> dict:
    """The overrides of the sweep point `name` (§3.3; the one builder): dotted paths of drivers.run.set_path on the
    raw config, added to ms4_common.e7_spec's; `ref` is the default build (the E7 main week at mu = 1) of the same
    alignment and horizon. KeyError for an unknown point; ValueError where the builder of the point refuses (e.g.
    calib.beta_for_rho)."""
    if name not in POINTS:
        raise KeyError(f"point_overrides: no S1 point {name!r}; known {list(POINTS)}")
    return POINTS[name].build(ref)


# ---------------------------------------------------------------- settings
def design() -> dict:
    """The job grid: the full grid of §3.7 and §4.5, or the reduced one with MS3_S1_REDUCED=1 (module docstring)."""
    red = os.environ.get(REDUCED_ENV, "0") == "1"
    return {"reduced": red, "alignments": (1,) if red else ALIGNMENTS, "policy_seeds": (0,) if red else POLICY_SEEDS,
            "horizon_min": REDUCED_HORIZON_MIN if red else m4.WEEK_MIN}


def parts() -> list:
    v = os.environ.get("S1_PART", "")
    ps = [p for p in v.replace(",", " ").split() if p]
    bad = [p for p in ps if p not in PARTS]
    if bad:
        raise ValueError(f"S1_PART must name parts of {list(PARTS)}, got {v!r}")
    return ps or list(PARTS)


def part_dir(out, part: str) -> Path:
    o = Path(out)
    return o if o.name == part else o / part


def s1_root(out) -> Path:
    """out/s1 (the folder of the parts) from a part's folder or from out/s1 itself."""
    o = Path(out)
    return o.parent if o.name in PARTS else o


def is_a8(tag: str) -> bool:
    return tag in e7.TAGS and e7.TAGS[tag]["id"] == "A8"


def tag_id(tag: str) -> str:
    return BL3["id"] if tag == "BL3" else e7.TAGS[tag]["id"]


def tag_style(tag: str) -> str:
    return BL3["style"] if tag == "BL3" else e7.TAGS[tag]["style"]


def tag_params(tag: str, inst) -> dict:
    """Q28's parameters of `tag` on the run's own instance (§4.3): e7.tag_params for E7's tags (M36's allowance for
    the A8 tags), BL3's {} (E5's defaults). A driver never types B0."""
    if tag == "BL3":
        return copy.deepcopy(BL3["params"])
    return e7.tag_params(tag, inst)


# ---------------------------------------------------------------- job ids, paths, estimates
def sweep_id(point: str, c: int) -> str:
    return job_id(EXP, "sweep", pt=point, c=int(c))


def q28_id(variant: str, tag: str, c: int) -> str:
    return job_id(EXP, "q28", var=variant, pol=tag, c=int(c))


def run_path(out, part: str, jid: str) -> Path:
    return part_dir(out, part) / "runs" / mc.job_file_name(jid)


def est_run_s(point: str) -> float:
    """§3.9: the seconds of one week run at `point` (measured, else the default's scaled by the client units)."""
    if point in EST_MEASURED_S:
        return float(EST_MEASURED_S[point])
    return EST_MEASURED_S[DEFAULT] * float(EST_UNITS[point]) / float(EST_DEFAULT_UNITS)


def job_limit_s(est_s: float) -> int:
    """§3.9, §11.1: three times the job's estimate, at least 1,800 s (whole seconds)."""
    return int(max(LIMIT_MIN_S, math.ceil(LIMIT_FACTOR * float(est_s))))


def jobs(ps=None) -> list:
    """The S1 jobs of the parts `ps` (default: S1_PART) in run order (§3.8, §4.6): each part's jobs longest first (by
    the estimates of §3.9; ties in §3.4's order and by alignment)."""
    ps = parts() if ps is None else list(ps)
    d = design()
    al, seeds, hz = d["alignments"], list(d["policy_seeds"]), d["horizon_min"]
    scale = float(hz) / float(m4.WEEK_MIN)
    common = {"policy_seeds": seeds, "horizon_min": hz}
    out = []
    if "sweep" in ps:
        js = []
        for i, name in enumerate(POINT_NAMES):
            pt = POINTS[name]
            for c in al:
                est = len(seeds) * est_run_s(name) * scale
                js.append((-est, i, c, Job(sweep_id(name, c), "pool",
                                           {"part": "sweep", "kind": "sweep", "point": name, "row": pt.row or None,
                                            "c": int(c), "tag": TAG, "mode": "L-tr", **common,
                                            "limit_s": job_limit_s(est)}, est)))
        out += [j for *_, j in sorted(js, key=lambda x: x[:3])]
    if "q28" in ps:
        js = []
        cells = [(v, t) for v in STRESS_VARIANTS for t in Q28_TAGS] + [("default", REF_TAG_BL3)]
        for i, (v, tag) in enumerate(cells):
            for c in al:
                est = len(seeds) * EST_Q28_S[(v, tag)] * scale
                js.append((-est, i, c, Job(q28_id(v, tag, c), "pool",
                                           {"part": "q28", "kind": "q28", "variant": v, "mode": VARIANTS[v],
                                            "tag": tag, "c": int(c), **common, "limit_s": job_limit_s(est)}, est)))
        out += [j for *_, j in sorted(js, key=lambda x: x[:3])]
    return out


def jobs_all() -> list:
    """Every job of the two parts (the summaries look up the records of their own part)."""
    return jobs(list(PARTS))


# ---------------------------------------------------------------- run specs and builds
def point_spec(policy_id: str, params=None, overrides=None, *, horizon_min: int = m4.WEEK_MIN, c: int = 1,
               seeds=(0,), name: str = "s1") -> dict:
    """The validated run spec of one sweep run (§3.3): ms4_common.e7_spec at mu = 1 with the trace lender ({}: L-tr)
    and the point's overrides, seeds config [c], lender 'config', policy `seeds`."""
    return m4.e7_spec(policy_id, params, mu=MU, horizon_min=int(horizon_min), lender_model={},
                      overrides=dict(overrides or {}), name=name,
                      seeds={"config": [int(c)], "lender": "config", "policy": [int(p) for p in seeds]})


def build_default(c: int, horizon_min: int) -> tuple:
    """(inst, model, ecfg) of the default point at alignment c (the E7 main week at mu = 1)."""
    from ..drivers.run import build
    return build(point_spec("BL0a", {}, {}, horizon_min=horizon_min, c=c, name="s1_default"), int(c))


def build_point(name: str, ref, c: int, horizon_min: int) -> tuple:
    """(inst, model, ecfg, overrides) of the point `name` at alignment c, `ref` being the default build of c."""
    from ..drivers.run import build
    ov = point_overrides(name, ref)
    inst, model, ecfg = build(point_spec("BL0a", {}, ov, horizon_min=horizon_min, c=c, name=f"s1_{name}"), int(c))
    return inst, model, ecfg, ov


def gamma_of(inst) -> Optional[float]:
    """Gamma of the builder's note (6 significant digits, instance.py _regional), None if absent."""
    for n in inst.notes:
        m = GAMMA_RE.search(n)
        if m:
            return float(m.group(1))
    return None


def n_units(inst) -> int:
    from ..instance import units
    return int(len(units(inst).client))


def instance_record(inst) -> dict:
    """e7.instance_sizes plus the client units, Gamma, the LLMs (id, tier, g) and the layer supply."""
    s = e7.instance_sizes(inst)
    lay = [x for x in inst.sites if x.kind == "layer"]
    s.update(n_units=n_units(inst), gamma=gamma_of(inst),
             gamma_note="the builder's note, 6 significant digits (instance.py _regional)",
             llms=[{"id": x.id, "tier": x.tier, "g": int(x.g), "w_GB": float(x.w_GB)} for x in inst.llms],
             supply_gpus_layer=float(sum(x.capacity_gpus for x in lay)), n_layer_sites=len(lay),
             protected_prepaid_min=[int(k.prepaid_min) for k in inst.contracts if k.protected])
    return s


def demand_matched(inst, ref) -> dict:
    """The demand of the clients both builds have, matched by (LLM id, region, borrowers) without the SLO class (as
    s1_rows_build.demand_matched): the clients only in one build, the maximum absolute difference and identity over
    the matched rows."""
    def keyed(x):
        return {(x.llms[int(j)].id, x.clients.region[c], tuple(x.clients.borrowers[c])): c
                for c, j in enumerate(np.asarray(x.clients.llm))}
    a, b = keyed(inst), keyed(ref)
    both = [k for k in a if k in b]
    da, db = np.asarray(inst.clients.demand, dtype=np.float64), np.asarray(ref.clients.demand, dtype=np.float64)
    out = {"n_matched": len(both), "only_in_point": [list(k[:2]) for k in a if k not in b],
           "only_in_default": [list(k[:2]) for k in b if k not in a], "max_abs_diff": None, "identical": None}
    if both and da.shape[1] == db.shape[1]:
        diff = np.abs(da[[a[k] for k in both]] - db[[b[k] for k in both]])
        out.update(max_abs_diff=float(diff.max()), identical=bool(diff.max() == 0.0))
    elif both:
        out["note"] = f"different numbers of fast slots ({da.shape[1]} and {db.shape[1]})"
    return out


def fits(inst) -> dict:
    """Per LLM: g, the layer sites with at least g GPUs, whether one exists (s1_rows_build._fits)."""
    lay = [float(s.capacity_gpus) for s in inst.sites if s.kind == "layer"]
    mx = max(lay) if lay else 0.0
    return {x.id: {"g": int(x.g), "n_layer_sites_fitting": int(sum(c >= x.g for c in lay)),
                   "max_layer_site_gpus": mx, "fits_a_layer_site": bool(x.g <= mx)} for x in inst.llms}


def vs_default(inst, ref, ih: str, ih_ref: str) -> dict:
    """The facts of check S1-1 for a point's instance against the default build of its alignment (§3.10)."""
    from .e6 import bl0a_all
    b, b0 = float(bl0a_all(inst)), float(bl0a_all(ref))
    ids = [x.id for x in inst.llms]
    llm = np.asarray(inst.clients.llm)
    with_clients = {inst.llms[int(j)].id for j in np.unique(llm)}
    fit = fits(inst)
    return {"instance_hash": ih, "default_instance_hash": ih_ref, "instance_equal": ih == ih_ref,
            "bl0a_usd": b, "default_bl0a_usd": b0, "bl0a_equal": b == b0, "bl0a_ratio": b / b0 if b0 > 0 else None,
            "gamma": gamma_of(inst), "default_gamma": gamma_of(ref), "n_units": n_units(inst),
            "default_n_units": n_units(ref), "demand_matched": demand_matched(inst, ref),
            "llm_clients": {k: int(np.sum(llm == j)) for j, k in enumerate(ids)},
            "llms_without_clients": [k for k in ids if k not in with_clients], "fits": fit,
            "llms_fitting_no_layer_site": [k for k in ids if not fit[k]["fits_a_layer_site"]]}


def prices(inst) -> dict:
    """a^0, q^GPU, the protected price, alpha and alpha_p (provision.committed_price) of the instance."""
    from ..drivers.provision import committed_price
    q = float(inst.q_gpu_usd_per_h)
    out = {"a0_usd_per_gpu_h": float(inst.a0_usd_per_gpu_h), "q_gpu_usd_per_gpu_h": q,
           "alpha": float(inst.a0_usd_per_gpu_h) / q if q > 0 else None}
    try:
        cp = float(committed_price(inst))
        out.update(committed_price_usd_per_gpu_h=cp, alpha_p=cp / q if q > 0 else None)
    except ValueError as err:
        put(out, "committed_price_usd_per_gpu_h", None, str(err))
        put(out, "alpha_p", None, str(err))
    return out


def _meta_run(job: Job) -> dict:
    return {"exp": EXP, "job": job.id, "spec": SPEC, "git_revision": mc.git_revision(), "versions": mc.versions(),
            "written": mc._now(), "reduced": design()["reduced"]}


def _savings(e: dict) -> dict:
    a = e.get("accountings") or {}
    e["saving_pct"] = None if a.get("overflow_over_bl0a") is None else 100.0 * (1.0 - a["overflow_over_bl0a"])
    e["saving_pct_total"] = None if a.get("total_over_bl0a") is None else 100.0 * (1.0 - a["total_over_bl0a"])
    return e


# ---------------------------------------------------------------- jobs: part sweep (§3.8)
def run_sweep(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One sweep job: the default build of the alignment, the point's instance (the default's itself at the
    default point), the facts of S1-1, then the three policy seeds of Sublet on the point's instance (e7.one_run)."""
    p = job.params
    name, c, hz, seeds = p["point"], int(p["c"]), int(p["horizon_min"]), list(p["policy_seeds"])
    t0 = time.perf_counter()
    ref, model, ecfg = build_default(c, hz)
    ih_ref = mc.instance_hash(ref)
    if name == DEFAULT:
        inst, ov = ref, {}
    else:
        inst, model, ecfg, ov = build_point(name, ref, c, hz)
    build_s = time.perf_counter() - t0
    if not ecfg.check_invariants:
        raise RuntimeError("S1 runs need check_invariants=True (§0 item 5)")
    ih = mc.instance_hash(inst) if inst is not ref else ih_ref
    facts = vs_default(inst, ref, ih, ih_ref)
    if inst is not ref:
        del ref
        gc.collect()
    refs, own = m4.references(inst), e7._own(inst)
    params = m4.sublet_params(inst, INNER)
    spec = point_spec("A8", params, ov, horizon_min=hz, c=c, seeds=seeds, name=f"s1_sweep_{name}")
    errors: list = []
    rows = []
    for ps in seeds:
        e = mc.try_run(errors, f"{TAG} p{ps}", e7.one_run, spec, TAG, inst, model, ecfg, refs, own, c, int(ps))
        if e is None:
            continue
        rows.append(_savings(e))
        a8 = e.get("a8") or {}
        print(f"[s1] {name} c{c} p{ps}: ALG {e['ALG']:.4f} USD, saving {e['saving_pct']:.3f}%, t_a {a8.get('t_a')}, "
              f"case {a8.get('certificate_case')}, {e['wall_s']:.1f} s", flush=True)
    pt = POINTS[name]
    rec = {"meta": _meta_run(job), "part": "sweep", "kind": "sweep", "point": name, "row": pt.row or None,
           "value": pt.value, "label": pt.label, "gamma_row": bool(ROWS[pt.row].gamma) if pt.row else None,
           "c": c, "horizon_min": hz, "policy_seeds": seeds, "tag": TAG, "policy_id": "A8", "params": params,
           "style_key": e7.TAGS[TAG]["style"], "overrides": ov, "instance_hash": ih,
           "instance": instance_record(inst), "references": refs, "own_capacity_usd": own, "prices": prices(inst),
           "vs_default": facts, "lender_model": e7._lender_dict(model), "build_s": build_s, "runs": rows,
           "errors": [{k: v for k, v in x.items() if k != "traceback"} for x in errors]}
    outputs.dump(e7._jsonish(rec), run_path(out, "sweep", job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": ih, "bl0a_usd": refs["bl0a_usd"],
            "totals": [r["ALG"] for r in rows], "saving_pct": [r["saving_pct"] for r in rows],
            "t_a": [(r.get("a8") or {}).get("t_a") for r in rows], "wall_s_runs": [r["wall_s"] for r in rows]}


# ---------------------------------------------------------------- jobs: part q28 (§4.6)
def refusal_record(results: list) -> dict:
    """The engine's refusal counts by reason (res.metrics['refused']), summed over BL2's sub-runs."""
    by: dict = {"capacity": 0, "unavailable": 0}
    for res in results:
        for k, v in (res.metrics.get("refused") or {}).items():
            by[k] = by.get(k, 0) + int(v)
    return by


def violation_record(results: list, insts: list) -> tuple:
    """(violations, violation_victims) of a run, summed over BL2's sub-runs, as q28_sizing.violation_stats reads
    them: the events of res.violations, the lender-slots with a violation, the deficits (all and attributable), the
    victims listed under 'reclaim', the leases that ended with cause 'violation' and the engine's metric sums; each
    victim with its lease, slot, minute, lender, site, LLM (the LLM of its replicas when they have one) and GPUs."""
    n_ev = n_att = n_vic = 0
    deficit = deficit_att = 0.0
    lender_slots: set = set()
    victims: list = []
    em = {k: 0.0 for k in VIOL_METRICS}
    deaths = 0
    for ri, (res, inst) in enumerate(zip(results, insts)):
        lease = {int(L.id): L for L in res.leases}
        llms_of: dict = {}
        for r in res.replicas:
            llms_of.setdefault(int(r.lease_id), set()).add(inst.llms[int(r.llm)].id)
        for v in res.violations:
            n_ev += 1
            att = float(v.get("deficit_attributable", v["deficit"]))
            n_att += att > 0
            deficit += float(v["deficit"])
            deficit_att += att
            lender_slots.add((ri, int(v["t"]), v["lender"]))
            for lid in v.get("victims") or []:
                n_vic += 1
                if len(victims) >= VICTIMS_MAX:
                    continue
                L = lease.get(int(lid))
                lm = sorted(llms_of.get(int(lid), ()))
                victims.append({"lease": int(lid), "slot": int(v["t"]), "minute": int(v["t"]) * inst.grid.slow_min,
                                "lender": v["lender"], "site": None if L is None else inst.sites[int(L.site)].id,
                                "llm": lm[0] if len(lm) == 1 else None, "llms": lm,
                                "gpus": None if L is None else int(L.gpus),
                                "end_cause": None if L is None else L.end_cause,
                                **({"sub_run": ri} if len(results) > 1 else {})})
        deaths += sum(1 for L in res.leases if L.end_cause == "violation")
        for k in VIOL_METRICS:
            em[k] += float(res.metrics.get(k, 0) or 0)
    viol = {"events": n_ev, "events_attributable": int(n_att), "lender_slots": len(lender_slots),
            "deficit_gpu_slots": deficit, "deficit_attributable_gpu_slots": deficit_att, "victims": n_vic,
            "violation_deaths": deaths,
            "engine_metrics": {k: (v if "deficit" in k else int(v)) for k, v in em.items()},
            "victims_listed": len(victims), "victims_listed_max": VICTIMS_MAX}
    return viol, victims


def unavailable_share(res, inst) -> dict:
    """The share of revocable site-slots in R_l of the run's schedule (the purchases that 'refuse' refuses; MS1 spec
    §6.4): mean, min and max over the revocable sites (q28_sizing.unavailable_share)."""
    T = int(inst.grid.T_slow)
    sh = []
    for i, s in enumerate(inst.sites):
        if s.kind == "protected":
            continue
        R = np.asarray(res.schedule.R[i], dtype=np.int64)
        sh.append(int(np.count_nonzero((R >= 0) & (R < T))) / T if T > 0 else 0.0)
    if not sh:
        return put({"revocable_sites": 0}, "mean", None, "no revocable site")
    return {"revocable_sites": len(sh), "mean": float(np.mean(sh)), "min": float(np.min(sh)),
            "max": float(np.max(sh))}


def q28_run(spec: dict, tag: str, inst, model, ecfg, refs: dict, own, c: int, ps: int) -> tuple:
    """(entry, unavailable share) of one run of `tag` under the spec's lender model: e7.one_run's steps (the simulate
    runner, or BL2's siloed runner through ms4_common.siloed_run), keeping the RunResult(s) to read the refusals and
    the violation victims (q28_sizing.run_case's gap 1); the entry is e7.run_entry's or e7.siloed_entry's."""
    from ..algos import registry
    from ..drivers.run import driver_inputs, make_policy
    from ..engine import simulate
    pid, params = spec["policy"]["id"], dict(spec["policy"]["params"] or {})
    t0 = time.perf_counter()
    if registry.entry(pid).runner == "siloed":
        d = m4.siloed_run(inst, spec, model, ecfg, c, ps)
        e = e7.siloed_entry(d, inst, model, refs, own, tag=tag, spec=spec, ps=ps, c=c,
                            wall_s=time.perf_counter() - t0)
        results, insts = list(d["results"]), list(d["instances"])
    else:
        _, imeta = driver_inputs(pid, params, inst)
        pol = make_policy(spec, inst)
        res = simulate(inst, pol, model, ecfg, lender_seed=int(c), policy_seed=int(ps))
        e = e7.run_entry(res, inst, model, refs, own, tag=tag, spec=spec, pol=pol, ps=ps, c=c,
                         wall_s=time.perf_counter() - t0, imeta=imeta)
        results, insts = [res], [inst]
    if e.get("style_key") is None:
        e["style_key"] = tag_style(tag)                # BL3 is not an E7 tag (q28_sizing.py's gap 3)
    viol, victims = violation_record(results, insts)
    e.update(refused=refusal_record(results), violations=viol, violation_victims=victims)
    us = unavailable_share(results[0], insts[0]) if results else None
    return _savings(e), us


def run_q28(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One Q28 job (§4.6): the three policy seeds of one tag under one variant on the E7 main week of alignment c
    (the instance does not depend on the variant), with the ratio validity under the variant's lender model and under
    the config's default lender model (check Q28-2)."""
    from ..config import lender_model as config_lender_model
    from ..drivers.run import build, ratio_validity
    from ..lender import resolve_params
    p = job.params
    variant, tag, c, hz, seeds = p["variant"], p["tag"], int(p["c"]), int(p["horizon_min"]), list(p["policy_seeds"])
    mode = VARIANTS[variant]
    t0 = time.perf_counter()
    inst, model, ecfg = build(e7.week_spec("BL0a", {}, mu=MU, mode=mode, horizon_min=hz, c=c, seeds=seeds), c)
    build_s = time.perf_counter() - t0
    if not ecfg.check_invariants:
        raise RuntimeError("S1 runs need check_invariants=True (§0 item 5)")
    refs, own, ih = m4.references(inst), e7._own(inst), mc.instance_hash(inst)
    default_model = config_lender_model(inst.config)
    rv = {g: ratio_validity(g, inst, model) for g in RATIO_GRIDS}
    rv_def = {g: ratio_validity(g, inst, default_model) for g in RATIO_GRIDS}
    params = tag_params(tag, inst)
    spec = e7.week_spec(tag_id(tag), params, mu=MU, mode=mode, horizon_min=hz, c=c, seeds=seeds,
                        name=f"s1_q28_{variant}_{tag}")
    errors: list = []
    rows, us = [], None
    for ps in seeds:
        r = mc.try_run(errors, f"{tag} p{ps}", q28_run, spec, tag, inst, model, ecfg, refs, own, c, int(ps))
        if r is None:
            continue
        e, us = r
        e.update(ratio_validity=dict(rv), ratio_validity_default=dict(rv_def))
        rows.append(e)
        a8 = e.get("a8") or {}
        print(f"[s1] q28 {variant} {tag} c{c} p{ps}: ALG {e['ALG']:.4f} USD, saving {e['saving_pct']:.3f}%, refused "
              f"{e['refused']}, violation victims {e['violations']['victims']}, t_a {a8.get('t_a')}, "
              f"{e['wall_s']:.1f} s", flush=True)
    rec = {"meta": _meta_run(job), "part": "q28", "kind": "q28", "variant": variant, "mode": mode, "tag": tag,
           "policy_id": tag_id(tag), "params": params, "style_key": tag_style(tag), "c": c, "horizon_min": hz,
           "policy_seeds": seeds, "instance_hash": ih, "instance": instance_record(inst), "references": refs,
           "own_capacity_usd": own, "lender_model": e7._lender_dict(model),
           "lender_model_default": e7._lender_dict(default_model),
           "lender_params_resolved": resolve_params(inst, model), "ratio_validity": rv,
           "ratio_validity_default": rv_def, "unavailable_share": us, "overrides": spec["overrides"],
           "build_s": build_s, "runs": rows,
           "errors": [{k: v for k, v in x.items() if k != "traceback"} for x in errors]}
    outputs.dump(e7._jsonish(rec), run_path(out, "q28", job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": ih, "bl0a_usd": refs["bl0a_usd"],
            "totals": [r["ALG"] for r in rows], "refused_unavailable": [r["refused"]["unavailable"] for r in rows],
            "violation_victims": [r["violations"]["victims"] for r in rows],
            "wall_s_runs": [r["wall_s"] for r in rows]}


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    k = job.params["kind"]
    if k == "sweep":
        return run_sweep(job, outputs, out)
    if k == "q28":
        return run_q28(job, outputs, out)
    raise ValueError(f"unknown S1 job {job.id!r}")


def manifest_extra(out) -> dict:
    """The instance hash of every instance of the parts' grids (§2.4; MS4 spec §2.6): per (point, alignment) for part
    sweep (each point built from the default build of its alignment), the week instance per alignment for part q28
    (the variant does not change the instance); the sha256 of the inputs."""
    d = design()
    ps = parts()
    hashes: dict = {}
    for c in d["alignments"]:
        ref = build_default(int(c), d["horizon_min"])[0]
        h_ref = mc.instance_hash(ref)
        if "q28" in ps:
            hashes[f"q28:c={int(c)}"] = h_ref         # e7.week_spec at L-tr builds the same instance
        if "sweep" in ps:
            for name in POINT_NAMES:
                if name == DEFAULT:
                    hashes[f"sweep:pt={name}:c={int(c)}"] = h_ref
                    continue
                inst = build_point(name, ref, int(c), d["horizon_min"])[0]
                hashes[f"sweep:pt={name}:c={int(c)}"] = mc.instance_hash(inst)
                del inst
                gc.collect()
        del ref
        gc.collect()
    files = (paths.CONFIGS / m4.E7_CONFIG, E7_SUMMARY)
    return {"instance_hashes": hashes, "design": {k: (list(v) if isinstance(v, tuple) else v) for k, v in d.items()},
            "parts": ps, "reduced": d["reduced"], "B0_rule": m4.B0_RULE,
            "inputs_sha256": {str(f.relative_to(paths.REPO)): _sha256(f) for f in files}}


def _sha256(p: Path) -> Optional[str]:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


# ---------------------------------------------------------------- summaries: shared pieces
def _part_outputs(out_p: Path, js: list, part: str) -> tuple:
    """({job id: run file} of the part's jobs whose record says 'ok', the ok ids, ignored outputs, {job id: status}
    of the jobs whose record is not 'ok' ('no record' without one)): a run file present while its job's record is not
    'ok' is not used and is listed (MS4 spec §2.6)."""
    recs = mc.read_records(out_p)
    data, ok, ignored, not_ok = {}, set(), [], {}
    for j in js:
        rec = recs.get(j.id) or {}
        path = run_path(out_p, part, j.id)
        if rec.get("status") != "ok":
            not_ok[j.id] = rec.get("status") or "no record"
            if path.is_file():
                ignored.append({"job": j.id, "status": rec.get("status"), "output": str(path.relative_to(out_p))})
            continue
        d = mc.read_json(path)
        if d is not None:
            data[j.id] = d
            ok.add(j.id)
        else:
            not_ok[j.id] = "ok record without a readable run file"
    return data, ok, ignored, not_ok


def _rows(files: dict, **match) -> list:
    """The run entries of the files whose fields equal `match`, each with the job id and alignment."""
    out = []
    for jid, f in files.items():
        if all(f.get(k) == v for k, v in match.items()):
            out.extend({**r, "job": jid, "c": f.get("c"), "point": f.get("point"), "variant": f.get("variant")}
                       for r in f["runs"])
    return out


def _run_errors(files: dict, **match) -> list:
    """The run errors recorded in the matching run files (ms3_common.try_run: a run that raised)."""
    return [{"job": jid, **e} for jid, f in files.items() if all(f.get(k) == v for k, v in match.items())
            for e in f.get("errors") or []]


def _label(r: dict) -> dict:
    return {"job": r.get("job"), "seed": r.get("policy_seed"), "c": r.get("c")}


def _status(fail: bool, n: int, missing: bool = False) -> str:
    """'fail' if a run fails the check, else 'missing' without runs or while a job of the grid lacks an 'ok' record,
    else 'pass'."""
    if fail:
        return "fail"
    return "missing" if (n == 0 or missing) else "pass"


def check_certificates(rows: list, claim_id: str, run_errors: Optional[list] = None,
                       missing: bool = False) -> dict:
    """S1-2 and Q28-3 over the A8 runs (E7-1's rule): every certificate available, held in the proven cases W(a),
    W(b); W(c) runs counted and listed; a run of an A8 job that raised (no certificate) fails."""
    a8 = [r for r in rows if r.get("a8")]
    cnt = m4.count_certificates([r["a8"] for r in a8])
    unavailable = [_label(r) for r in a8 if not (r["a8"].get("certificate") or {}).get("available")]
    failures = [{**_label(r), "case": r["a8"]["certificate_case"], "t_a": r["a8"].get("t_a")} for r in a8
                if r["a8"]["certificate_case"] in m4.PROVEN_CASES
                and (r["a8"].get("certificate") or {}).get("held") is not True]
    wc = [{**_label(r), "t_a": r["a8"].get("t_a"), "held": (r["a8"].get("certificate") or {}).get("held")}
          for r in a8 if r["a8"]["certificate_case"] == "W(c)"]
    errs = list(run_errors or [])
    fail = bool(unavailable or failures or errs)
    return {"status": _status(fail, len(a8), missing), "claim": CHECK_CLAIMS[claim_id], "n_runs": len(a8),
            "certificates": cnt, "unavailable": unavailable[:50], "n_unavailable": len(unavailable),
            "failures": failures[:50], "n_failures": len(failures), "w_c_runs": wc[:200], "n_w_c": len(wc),
            "run_errors": errs[:50], "n_run_errors": len(errs)}


def _certs_block(rows: list) -> dict:
    a8 = [r for r in rows if r.get("a8")]
    cnt = m4.count_certificates([r["a8"] for r in a8])
    cnt["w_c_runs"] = [{**_label(r), "t_a": r["a8"].get("t_a")} for r in a8 if r["a8"]["certificate_case"] == "W(c)"]
    return cnt


def _read_e7_summary() -> tuple:
    """(E7's main summary or None, its source record: file, exists, sha256, git_revision, reduced)."""
    s = mc.read_json(E7_SUMMARY)
    src = {"file": E7_SUMMARY_REL, "exists": E7_SUMMARY.is_file(), "sha256": _sha256(E7_SUMMARY),
           "git_revision": ((s or {}).get("meta") or {}).get("git_revision"),
           "reduced": ((s or {}).get("meta") or {}).get("reduced")}
    if s is None:
        src["note"] = "missing or unreadable"
    return s, src


def _meta(part: str, d: dict, js: list, ok: set, ignored: list, **extra) -> dict:
    meta = {"exp": EXP, "part": part, "spec": SPEC, "git_revision": mc.git_revision(), "versions": mc.versions(),
            "written": mc._now(), "reduced": d["reduced"],
            "grids": {"alignments": list(d["alignments"]), "alignments_design": list(ALIGNMENTS),
                      "policy_seeds": list(d["policy_seeds"]), "policy_seeds_design": list(POLICY_SEEDS),
                      "horizon_min": d["horizon_min"], "horizon_min_design": m4.WEEK_MIN, "mu_over_beta_tilde": MU},
            "B0_rule": m4.B0_RULE, "info_class_reported_a8": m4.INFO_CLASS_REPORTED,
            "jobs_ok": len(ok), "jobs_missing": [j.id for j in js if j.id not in ok], "ignored_outputs": ignored}
    if d["reduced"]:
        meta["reduced_note"] = (f"reduced job list ({REDUCED_ENV}=1): alignment 1, policy seed 0, a "
                                f"{REDUCED_HORIZON_MIN}-min horizon; not a result")
    meta.update(extra)
    return meta


def _write_tables(path: Path, title: str, blocks: list) -> None:
    lines = [f"# {title}", ""]
    for head, table in blocks:
        lines += [f"## {head}", "", table, ""]
    mc.write_text("\n".join(lines) + "\n", path)


def _checks_table(checks: dict) -> str:
    return mc.md_table(["check", "status"], [[k, v.get("status")] for k, v in checks.items()])


def _ci(a: dict) -> list:
    return (a or {}).get("median_ci95") or [None, None]


def _median(entry: Optional[dict], key: str = "saving_pct") -> Optional[float]:
    return ((entry or {}).get(key) or {}).get("median")


# ---------------------------------------------------------------- rows (§3.8, M5, M6)
def row_entry(key: str, points: dict, default_median: Optional[float], *, label: str, panel: str, gamma: bool,
              default_label: str, source: Optional[dict] = None) -> dict:
    """rows.<row> (§3.8): `points` {name: {'value', 'label', 'saving_pct_median', 'n_runs'}} in the row's order and the
    default point's median saving; lo and hi are the lowest and highest median saving over the row's points with a
    median and the default (M5), lo_point and hi_point the first name attaining them ('default' first, then the
    points in order), lo_points and hi_points every attaining name, span = hi - lo; complete is false while a point
    or the default has no median (points_missing). Null with notes when no value exists."""
    cand = ([(DEFAULT, default_median)] if default_median is not None else []) + \
        [(n, p["saving_pct_median"]) for n, p in points.items() if p.get("saving_pct_median") is not None]
    missing = [n for n, p in points.items() if p.get("saving_pct_median") is None]
    if default_median is None:
        missing = [DEFAULT] + missing
    e = {"label": label, "panel": panel, "gamma_row": bool(gamma), "default_label": default_label,
         "points": points, "default": {"label": default_label}, "n_points": len(points),
         "points_missing": missing, "complete": not missing}
    put(e["default"], "saving_pct_median", default_median, "no run of the default point")
    if source is not None:
        e["source"] = source
    if not cand:
        note = "no median saving at any point of the row or the default"
        for k in ("lo", "hi", "span", "lo_point", "hi_point"):
            put(e, k, None, note)
        e["lo_points"], e["hi_points"] = [], []
        return e
    lo = min(v for _, v in cand)
    hi = max(v for _, v in cand)
    e.update(lo=lo, hi=hi, span=hi - lo, lo_points=[n for n, v in cand if v == lo],
             hi_points=[n for n, v in cand if v == hi])
    e["lo_point"], e["hi_point"] = e["lo_points"][0], e["hi_points"][0]
    return e


def rows_block(points_summary: dict, e7s: Optional[dict]) -> dict:
    """rows.<row> of sweep/summary.json for every row of ROWS (§3.4 order) from the points' summaries, and the mu row
    from E7's summary (M9)."""
    dmed = _median(points_summary.get(DEFAULT))
    out = {}
    for key, row in ROWS.items():
        if key == MU_ROW:
            runs = ((e7s or {}).get("runs") or {})
            pts = {}
            for n, (v, lab) in MU_POINTS.items():
                ent = (runs.get(num_key(v)) or {}).get(TAG) or {}
                pts[n] = {"value": v, "label": lab, "n_runs": ent.get("n_runs", 0)}
                put(pts[n], "saving_pct_median", _median(ent),
                    f"{E7_SUMMARY_REL} has no runs.{num_key(v)}.{TAG}.saving_pct.median")
            src = {"kind": "e7", "file": E7_SUMMARY_REL,
                   "paths": [f"runs.{num_key(v)}.{TAG}.saving_pct.median" for v, _ in MU_POINTS.values()],
                   "e7_default_saving_pct_median": _median(((runs.get(num_key(MU)) or {}).get(TAG)))}
            out[key] = row_entry(key, pts, dmed, label=row.label, panel=row.panel, gamma=row.gamma,
                                 default_label=row.default_label, source=src)
            continue
        pts = {}
        for name, pt in POINTS.items():
            if pt.row != key:
                continue
            ent = points_summary.get(name) or {}
            pts[name] = {"value": pt.value, "label": pt.label, "n_runs": ent.get("n_runs", 0)}
            put(pts[name], "saving_pct_median", _median(ent), "no run of this point")
        out[key] = row_entry(key, pts, dmed, label=row.label, panel=row.panel, gamma=row.gamma,
                             default_label=row.default_label, source={"kind": "s1"})
    return out


# ---------------------------------------------------------------- summary: part sweep (§3.8, §3.10)
def check_default(default_entry: Optional[dict], default_hashes: dict, e7s: Optional[dict],
                  alignments=ALIGNMENTS, missing: bool = False) -> dict:
    """S1-0: the default point's runs against E7's runs.1.Sublet: n_runs, the median, p95, max and mean of overflow_usd
    within 1e-9 relative, and per alignment the instance hash against meta.instances['mu=1:c=<c>'] (§3.10).
    'missing' without E7's summary, without a run of the default point or a hash of an alignment, and while a job of
    the default point has no 'ok' record (`missing`: its aggregates are then over fewer runs), unless an instance hash
    already differs."""
    out = {"claim": CHECK_CLAIMS["S1-0"], "reference_file": E7_SUMMARY_REL, "tolerance": REL_TOL}
    ref = (((e7s or {}).get("runs") or {}).get(num_key(MU)) or {}).get(TAG)
    inst_ref = ((e7s or {}).get("meta") or {}).get("instances") or {}
    if not isinstance(ref, dict) or not isinstance(default_entry, dict) or not default_entry.get("n_runs"):
        out.update(status="missing", note="E7's summary has no runs.1.Sublet" if not isinstance(ref, dict)
                   else "no run of the default point")
        return out
    here, there = default_entry.get("overflow_usd") or {}, ref.get("overflow_usd") or {}
    stats, bad = {}, []
    for k in ("median", "p95", "max", "mean"):
        a, b = here.get(k), there.get(k)
        rel = None if a is None or b is None else abs(a - b) / max(abs(b), 1e-300)
        stats[k] = {"s1": a, "e7": b, "rel_diff": rel}
        if rel is None or rel > REL_TOL:
            bad.append(k)
    n_ok = default_entry.get("n_runs") == ref.get("n_runs")
    hashes, bad_h, miss_h = {}, [], []
    for c in alignments:
        h = default_hashes.get(num_key(c))
        hr = (inst_ref.get(f"mu={num_key(MU)}:c={int(c)}") or {}).get("instance_hash")
        hashes[num_key(c)] = {"s1": h, "e7": hr, "equal": h is not None and h == hr}
        if h is None:
            miss_h.append(int(c))
        elif h != hr:
            bad_h.append(int(c))
    if bad_h:
        st = "fail"
    elif missing or miss_h:
        st = "missing"
    else:
        st = "fail" if (bad or not n_ok) else "pass"
    out.update(status=st, n_runs={"s1": default_entry.get("n_runs"), "e7": ref.get("n_runs")}, n_runs_equal=n_ok,
               overflow_usd=stats, stats_differ=bad, instance_hashes=hashes, hashes_differ=bad_h,
               hashes_missing=miss_h, default_jobs_missing=bool(missing))
    return out


def check_built(files: dict, missing: bool = False) -> dict:
    """S1-1 over the sweep's run files of every point but the default (§3.10): the hash differs from the default's;
    on the rows without Gamma the demand (matched client by client, no client only in one build) and BL0a equal the
    default's exactly; every LLM fits a layer site (the g^lay 16 points listed apart); every LLM has clients but S at
    sS0."""
    bad, g16 = [], {}
    n = 0
    for jid, f in sorted(files.items()):
        name = f.get("point")
        if name == DEFAULT or name not in POINTS:
            continue
        n += 1
        v, pt = f["vs_default"], POINTS[name]
        probs = []
        if v.get("instance_equal"):
            probs.append("the instance hash equals the default's")
        if not ROWS[pt.row].gamma:
            dm = v.get("demand_matched") or {}
            if not (dm.get("identical") is True and not dm.get("only_in_point") and not dm.get("only_in_default")):
                probs.append(f"the demand differs from the default's (matched max abs diff {dm.get('max_abs_diff')}, "
                             f"clients only in the point {dm.get('only_in_point')}, only in the default "
                             f"{dm.get('only_in_default')})")
            if not v.get("bl0a_equal"):
                probs.append(f"BL0a {v.get('bl0a_usd')!r} != the default's {v.get('default_bl0a_usd')!r}")
        if v.get("llms_fitting_no_layer_site"):
            probs.append(f"LLMs fitting no layer site: {v['llms_fitting_no_layer_site']}")
        want = ["S"] if name == "sS0" else []
        if list(v.get("llms_without_clients") or []) != want:
            probs.append(f"LLMs without clients {v.get('llms_without_clients')} != {want}")
        if name in G16_POINTS:
            g16[f"{name}:c={f.get('c')}"] = {k: x["fits_a_layer_site"] for k, x in (v.get("fits") or {}).items()}
        if probs:
            bad.append({"job": jid, "point": name, "c": f.get("c"), "problems": probs})
    return {"status": _status(bool(bad), n, missing), "claim": CHECK_CLAIMS["S1-1"], "n_instances": n,
            "failures": bad[:100], "n_failures": len(bad), "g16_fits": g16,
            "rows_without_gamma": [k for k, r in ROWS.items() if not r.gamma and k != MU_ROW]}


def check_clean(rows: list, missing: bool = False) -> dict:
    """S1-3: no run has an invariant failure (BL2's sub-runs do not occur in the sweep)."""
    inv = [{**_label(r), "point": r.get("point"), "first": (r.get("invariant_failures_first") or [])[:2]}
           for r in rows if r.get("n_invariant_failures")]
    return {"status": _status(bool(inv), len(rows), missing), "claim": CHECK_CLAIMS["S1-3"], "n_runs": len(rows),
            "invariant_failures": inv[:50], "n_invariant_failures": len(inv),
            "n_runs_with_gpu_only_lease_slots": sum(1 for r in rows if r.get("gpu_only_lease_slots"))}


def summary_sweep(out_s: Path) -> dict:
    out_s = Path(out_s)
    d = design()
    js = [j for j in jobs_all() if j.params["part"] == "sweep"]
    files, ok, ignored, not_ok = _part_outputs(out_s, js, "sweep")
    e7s, e7_src = _read_e7_summary()
    pts = {}
    for name, pt in POINTS.items():
        rows = _rows(files, point=name)
        e = e7.cost_entry(rows, TAG)
        e.update(row=pt.row or None, value=pt.value, label=pt.label,
                 gamma_row=bool(ROWS[pt.row].gamma) if pt.row else None,
                 n_runs_expected=len(d["alignments"]) * len(d["policy_seeds"]),
                 bl0a_usd={num_key(f["c"]): f["references"]["bl0a_usd"] for f in files.values()
                           if f.get("point") == name})
        pts[name] = e
    all_rows = _rows(files)
    instances: dict = {}
    for name in POINT_NAMES:
        by_c = {num_key(f["c"]): {"instance_hash": f["instance_hash"], "bl0a_usd": f["references"]["bl0a_usd"],
                                  "gamma": f["instance"].get("gamma"), "n_units": f["instance"].get("n_units"),
                                  "overrides": f["overrides"]}
                for f in files.values() if f.get("point") == name}
        if by_c:
            instances[name] = dict(sorted(by_c.items(), key=lambda kv: int(kv[0])))
    dref = {num_key(f["c"]): f["references"] for f in files.values() if f.get("point") == DEFAULT}
    dprices = {num_key(f["c"]): f.get("prices") for f in files.values() if f.get("point") == DEFAULT}
    meta = _meta("sweep", d, js, ok, ignored,
                 points={n: {"row": p.row or None, "value": p.value, "label": p.label,
                             "gamma_row": bool(ROWS[p.row].gamma) if p.row else None} for n, p in POINTS.items()},
                 rows_order=list(ROWS), mu_points={n: v for n, (v, _) in MU_POINTS.items()},
                 tag={"tag": TAG, "policy_id": "A8", "params": f"ms4_common.sublet_params(inst, {INNER!r})",
                      "style_key": e7.TAGS[TAG]["style"]},
                 default_references=dict(sorted(dref.items())), default_prices=dict(sorted(dprices.items())),
                 instances=instances, e7_summary=e7_src, jobs_not_ok=not_ok)
    missing = bool(not_ok)
    ch = {"S1-0": check_default(pts[DEFAULT], {c: v["instance_hash"] for c, v in instances.get(DEFAULT, {}).items()},
                                e7s, d["alignments"],
                                missing=any(sweep_id(DEFAULT, c) in not_ok for c in d["alignments"]))}
    ch["S1-1"] = check_built(files, missing)
    ch["S1-2"] = check_certificates(all_rows, "S1-2", _run_errors(files), missing)
    ch["S1-3"] = check_clean(all_rows, missing or bool(_run_errors(files)))
    rows = rows_block(pts, e7s)
    above = sorted((k for k, r in rows.items() if r.get("span") is not None and r["span"] > SPAN_INFORMATIVE_PP),
                   key=lambda k: -rows[k]["span"])
    ch["S1-4"] = {"status": "informative", "claim": CHECK_CLAIMS["S1-4"],
                  "saving_pct_median": {n: _median(e) for n, e in pts.items()},
                  "span": {k: r.get("span") for k, r in rows.items()},
                  "rows_span_above_threshold": above, "threshold_pp": SPAN_INFORMATIVE_PP,
                  "rows_incomplete": [k for k, r in rows.items() if not r["complete"]]}
    checks = {k: ch[k] for k in CHECK_IDS_SWEEP}
    summ = {"meta": meta, "points": pts, "rows": rows, "not_run": [dict(x) for x in NOT_RUN],
            "certificates": _certs_block(all_rows), "checks": checks}
    mc.dump_json(summ, out_s / "summary.json")
    _write_tables(out_s / "tables.md", "S1: sensitivity of Sublet's saving across the register "
                                       "(design/sim_spec_ms5.md §3)", tables_sweep(summ))
    return summ


def tables_sweep(s: dict) -> list:
    blocks = [("Reduced run", s["meta"]["reduced_note"])] if s["meta"].get("reduced") else []
    rows = []
    for n, e in s["points"].items():
        sp, st = e["saving_pct"], e["saving_pct_total"]
        rows.append([n, e.get("row"), e.get("label"), e["n_runs"], sp.get("median"), _ci(sp)[0], _ci(sp)[1],
                     st.get("median"), e.get("abort_share")])
    blocks.append(("Saving over BL0a per point (%, overflow accounting; median [95% CI] over the runs)",
                   mc.md_table(["point", "row", "value", "runs", "median", "ci lo", "ci hi", "total acc.",
                                "abort share"], rows)))
    rows = [[k, r["panel"], r.get("lo"), r.get("lo_point"), r.get("hi"), r.get("hi_point"), r.get("span"),
             r["complete"]] for k, r in s["rows"].items()]
    blocks.append(("Rows: lowest and highest median saving with the default included (M5)",
                   mc.md_table(["row", "panel", "lo", "at", "hi", "at", "span (pp)", "complete"], rows)))
    blocks.append(("Rows and points not run (§3.5)",
                   mc.md_table(["row", "reason"], [[x["row"], x["reason"]] for x in s["not_run"]])))
    blocks.append(("Checks (§3.10)", _checks_table(s["checks"])))
    return blocks


# ---------------------------------------------------------------- summary: part q28 (§4.6, §4.7)
def _part_summary(root: Path, part: str) -> tuple:
    """(<part>/summary.json or None, the reason it is not used or None): a part summary whose s1:summary record
    exists and is not 'ok' is not used (MS4 spec §2.6; e7.part_summary's rule)."""
    folder = Path(root) / part
    rec = mc.read_record(folder, job_id(EXP, "summary"))
    if rec is not None and rec.get("status") != "ok":
        return None, f"{part}/summary.json not used: its {job_id(EXP, 'summary')} record has status " \
                     f"{rec.get('status')!r}"
    s = mc.read_json(folder / "summary.json")
    return s, (None if s is not None else f"{part}/summary.json is missing or unreadable")


def q28_entry(rows: list, tag: str, note: str = "no run of this cell in the outputs") -> dict:
    """runs.<variant>.<tag> (§4.6): e7.cost_entry (E7's runs.<mu>.<tag> fields; for BL3, which is no E7 tag, with an
    unguarded E7 tag, which selects only the null A8 fields) plus the refusals, violations and victims as aggregates
    over the runs and the ratio-validity reasons found."""
    e = e7.cost_entry(rows, tag if tag in e7.TAGS else "BL5", note)
    e["refusals"] = {k: e7._agg([(r.get("refused") or {}).get(k) for r in rows], note) for k in
                     ("unavailable", "capacity")}
    for k, src in (("violation_events", "events"), ("violation_lender_slots", "lender_slots"),
                   ("violation_victims", "victims"), ("violation_deaths", "violation_deaths")):
        e[k] = e7._agg([(r.get("violations") or {}).get(src) for r in rows], note)
    e["n_runs_with_violations"] = sum(1 for r in rows if (r.get("violations") or {}).get("events"))
    e["n_runs_with_victims"] = sum(1 for r in rows if (r.get("violations") or {}).get("victims"))
    e["ratio_validity"] = {g: sorted({str((r.get("ratio_validity") or {}).get(g)) for r in rows}) for g in RATIO_GRIDS}
    e["ratio_validity_note"] = "the distinct reasons of drivers.run.ratio_validity over the runs ('None': a ratio is " \
                               "meaningful)"
    return e


def _set_reference(e: dict, ref_med: Optional[float], ref_sav: Optional[float], source: str, note: str,
                   suffix: str = "") -> None:
    r = {"source": source}
    put(r, "overflow_over_bl0a_median", ref_med, note)
    put(r, "saving_pct_median", ref_sav, note)
    e["reference" + suffix] = r
    m = (e.get("overflow_over_bl0a") or {}).get("median")
    put(e, "delta_overflow_over_bl0a" + suffix, None if m is None or ref_med is None else m - ref_med,
        "no median of this cell or of its reference" if m is None or ref_med is None else None)


def check_finished(files: dict, rows: list, errors: list, failed_jobs: dict, missing: bool) -> dict:
    """Q28-1: every run finishes with no invariant failure (BL2's sub-runs included) and no error record; a job that
    ended with status error, failed, oom_at_3G or wall_limit fails it (its runs did not finish)."""
    inv = []
    for r in rows:
        subs = r.get("sub_runs") or []
        if r.get("n_invariant_failures") or any(s.get("n_invariant_failures") for s in subs):
            inv.append({**_label(r), "tag": r.get("tag"), "variant": r.get("variant"),
                        "first": (r.get("invariant_failures_first") or [])[:2]})
    jf = [{"job": j, "status": s} for j, s in sorted(failed_jobs.items())]
    fail = bool(inv or errors or jf)
    return {"status": _status(fail, len(rows), missing), "claim": CHECK_CLAIMS["Q28-1"], "n_runs": len(rows),
            "n_sub_runs": sum(len(r.get("sub_runs") or []) for r in rows), "invariant_failures": inv[:50],
            "n_invariant_failures": len(inv), "run_errors": errors[:50], "n_run_errors": len(errors),
            "job_failures": jf[:50], "n_job_failures": len(jf),
            "refusals_unavailable_total": sum(int((r.get("refused") or {}).get("unavailable") or 0) for r in rows),
            "violation_deaths_total": sum(int((r.get("violations") or {}).get("violation_deaths") or 0)
                                          for r in rows)}


def check_ratio_validity(rows: list, missing: bool, files: Optional[dict] = None) -> dict:
    """Q28-2: every L-vr run has a reason for every grid (no ratio); every L-rf run has, grid by grid, the reason of
    the same instance under the config's default lender model (on the trace schedule). drivers.run.ratio_validity
    reads only the grid, the instance and the lender model, so the L-rf half holds by construction once the run's
    lender model is L-rf's; the check therefore also requires every stress run file of `files` to record its
    variant's lender model: the file's default lender model (lender_model_default) with the keys of
    ms4_common.mode_lender_model (schedule 'trace', and on_unavailable 'refuse' for L-rf or violations 'reclaim' for
    L-vr) and no other change, so that each variant runs alone (§4.4)."""
    vr_bad, rf_bad, model_bad = [], [], []
    for jid, f in sorted((files or {}).items()):
        v = f.get("variant")
        if v not in STRESS_VARIANTS:
            continue
        want = {**(f.get("lender_model_default") or {}), **m4.mode_lender_model(VARIANTS[v])}
        got = f.get("lender_model") or {}
        if not f.get("lender_model_default") or got != want:
            model_bad.append({"job": jid, "variant": v, "lender_model": got, "want": want})
    n_vr = n_rf = 0
    for r in rows:
        rv, rd = r.get("ratio_validity") or {}, r.get("ratio_validity_default") or {}
        if r.get("variant") == "vr":
            n_vr += 1
            if any(rv.get(g) is None for g in RATIO_GRIDS):
                vr_bad.append({**_label(r), "tag": r.get("tag"), "ratio_validity": rv})
        elif r.get("variant") == "rf":
            n_rf += 1
            if any(rv.get(g, "absent") != rd.get(g, "absent") for g in RATIO_GRIDS) or not rv:
                rf_bad.append({**_label(r), "tag": r.get("tag"), "ratio_validity": rv, "default": rd})
    fail = bool(vr_bad or rf_bad or model_bad)
    return {"status": _status(fail, min(n_vr, n_rf), missing), "claim": CHECK_CLAIMS["Q28-2"], "grids":
            list(RATIO_GRIDS), "n_vr": n_vr, "n_rf": n_rf, "vr_with_a_ratio": vr_bad[:50], "n_vr_with_a_ratio":
            len(vr_bad), "rf_changed": rf_bad[:50], "n_rf_changed": len(rf_bad),
            "n_files_checked": sum(1 for f in (files or {}).values() if f.get("variant") in STRESS_VARIANTS),
            "wrong_lender_model": model_bad[:50], "n_wrong_lender_model": len(model_bad)}


def q28_rows(runs: dict, s1_default: Optional[float]) -> dict:
    """rows.q28_rf and rows.q28_vr: Sublet's two tornado rows (M13) in the sweep's form (row_entry), the variant's
    median saving against S1's default point."""
    out = {}
    for v, label in (("rf", "Q28: refusals (L-rf)"), ("vr", "Q28: violations as reclaims (L-vr)")):
        ent = (runs.get(v) or {}).get(TAG) or {}
        pts = {f"q28_{v}": {"value": VARIANTS[v], "label": VARIANTS[v], "n_runs": ent.get("n_runs", 0)}}
        put(pts[f"q28_{v}"], "saving_pct_median", _median(ent), "no run of this cell")
        out[f"q28_{v}"] = row_entry(f"q28_{v}", pts, s1_default, label=label, panel="c", gamma=False,
                                    default_label="L-tr", source={"kind": "q28", "runs": f"runs.{v}.{TAG}",
                                                                  "default": "sweep/summary.json points.default"})
    return out


def summary_q28(out_q: Path) -> dict:
    out_q = Path(out_q)
    d = design()
    js = [j for j in jobs_all() if j.params["part"] == "q28"]
    files, ok, ignored, not_ok = _part_outputs(out_q, js, "q28")
    e7s, e7_src = _read_e7_summary()
    sw, sw_why = _part_summary(s1_root(out_q), "sweep")
    sw_src = {"file": "sweep/summary.json", "used": sw is not None,
              "git_revision": ((sw or {}).get("meta") or {}).get("git_revision"),
              "reduced": ((sw or {}).get("meta") or {}).get("reduced")}
    if sw_why:
        sw_src["used_note"] = sw_why
    s1_def = (sw or {}).get("points", {}).get(DEFAULT) if sw else None
    runs: dict = {}
    for v in STRESS_VARIANTS:
        for tag in Q28_TAGS:
            runs.setdefault(v, {})[tag] = q28_entry(_rows(files, variant=v, tag=tag), tag)
    runs["default"] = {REF_TAG_BL3: q28_entry(_rows(files, variant="default", tag=REF_TAG_BL3), REF_TAG_BL3)}
    e7runs = (((e7s or {}).get("runs") or {}).get(num_key(MU)) or {})
    bl3_ref = runs["default"][REF_TAG_BL3]
    for v in STRESS_VARIANTS:
        for tag, e in runs[v].items():
            if tag == REF_TAG_BL3:
                _set_reference(e, _median(bl3_ref, "overflow_over_bl0a"), _median(bl3_ref),
                               "q28/summary.json runs.default.BL3 (this part's default jobs)",
                               "no run of BL3 under the default lender")
            else:
                _set_reference(e, _median(e7runs.get(tag), "overflow_over_bl0a"), _median(e7runs.get(tag)),
                               f"{E7_SUMMARY_REL} runs.{num_key(MU)}.{tag}",
                               f"{E7_SUMMARY_REL} has no runs.{num_key(MU)}.{tag}")
            if tag == TAG:
                _set_reference(e, _median(s1_def, "overflow_over_bl0a"), _median(s1_def),
                               "sweep/summary.json points.default", sw_why or "no run of S1's default point",
                               suffix="_s1_default")
    all_rows = _rows(files)
    stress_rows = [r for r in all_rows if r.get("variant") in STRESS_VARIANTS]
    refs = {num_key(f["c"]): f["references"] for f in files.values()}
    inst_meta = {}
    for f in files.values():
        inst_meta.setdefault(num_key(f["c"]), {**f["instance"], "instance_hash": f["instance_hash"],
                                               "unavailable_share": f.get("unavailable_share")})
    hashes_by_c = {}
    for f in files.values():
        hashes_by_c.setdefault(num_key(f["c"]), set()).add(f["instance_hash"])
    variants_meta = {}
    for v, mode in VARIANTS.items():
        variants_meta[v] = {"mode": mode, "lender_model": m4.mode_lender_model(mode)}
    meta = _meta("q28", d, js, ok, ignored,
                 variants=variants_meta, stress_variants=list(STRESS_VARIANTS),
                 tags={t: {"policy_id": tag_id(t), "params": ("ms4_common.sublet_params(inst, %r)"
                                                              % e7.TAGS[t]["inner"]) if is_a8(t)
                           else (BL3["params"] if t == "BL3" else e7.TAGS[t]["params"]),
                           "style_key": tag_style(t), "a8": is_a8(t)} for t in Q28_TAGS},
                 references=dict(sorted(refs.items())), instances=dict(sorted(inst_meta.items())),
                 one_instance_per_alignment={c: len(h) == 1 for c, h in sorted(hashes_by_c.items())},
                 e7_summary=e7_src, sweep_summary=sw_src, jobs_not_ok=not_ok)
    missing = bool(not_ok)
    failed_jobs = {j: s for j, s in not_ok.items() if s in ("error", "failed", "oom_at_3G", "wall_limit")}
    errs = _run_errors(files)
    ch = {"Q28-1": check_finished(files, all_rows, errs, failed_jobs, missing),
          "Q28-2": check_ratio_validity(stress_rows, missing, files),
          "Q28-3": check_certificates(stress_rows, "Q28-3",
                                      [x for v in STRESS_VARIANTS for t in Q28_TAGS if is_a8(t)
                                       for x in _run_errors(files, variant=v, tag=t)], missing)}
    delta = {v: {t: e.get("delta_overflow_over_bl0a") for t, e in runs[v].items()} for v in STRESS_VARIANTS}
    ch["Q28-4"] = {"status": "informative", "claim": CHECK_CLAIMS["Q28-4"],
                   "delta_overflow_over_bl0a": delta,
                   "delta_overflow_over_bl0a_s1_default": {v: runs[v][TAG].get("delta_overflow_over_bl0a_s1_default")
                                                           for v in STRESS_VARIANTS},
                   "saving_pct_median": {v: {t: _median(e) for t, e in runs[v].items()} for v in runs},
                   "refusals_unavailable_median": {v: {t: e["refusals"]["unavailable"].get("median")
                                                       for t, e in runs[v].items()} for v in runs},
                   "violation_victims_median": {v: {t: e["violation_victims"].get("median")
                                                    for t, e in runs[v].items()} for v in runs},
                   "n_runs_with_violations": {v: {t: e["n_runs_with_violations"] for t, e in runs[v].items()}
                                              for v in runs},
                   "saving_rises": {v: sorted(t for t, x in delta[v].items() if x is not None and x < 0)
                                    for v in STRESS_VARIANTS}}
    checks = {k: ch[k] for k in CHECK_IDS_Q28}
    summ = {"meta": meta, "runs": runs, "rows": q28_rows(runs, _median(s1_def)),
            "certificates": _certs_block(all_rows), "checks": checks}
    mc.dump_json(summ, out_q / "summary.json")
    _write_tables(out_q / "tables.md", "S1: Q28's stress variants (design/sim_spec_ms5.md §4)", tables_q28(summ))
    return summ


def tables_q28(s: dict) -> list:
    blocks = [("Reduced run", s["meta"]["reduced_note"])] if s["meta"].get("reduced") else []
    rows = []
    for v, by in s["runs"].items():
        for t, e in by.items():
            o = e["overflow_over_bl0a"]
            rows.append([v, t, e["n_runs"], o.get("median"), _ci(o)[0], _ci(o)[1], _median(e),
                         e["refusals"]["unavailable"].get("median"), e["violation_victims"].get("median"),
                         (e.get("reference") or {}).get("overflow_over_bl0a_median"),
                         e.get("delta_overflow_over_bl0a")])
    blocks.append(("Week cost over BL0a per variant and policy (median [95% CI] over the runs)",
                   mc.md_table(["variant", "tag", "runs", "cost / BL0a", "ci lo", "ci hi", "saving %",
                                "refusals", "victims", "reference", "delta"], rows)))
    blocks.append(("Checks (§4.7)", _checks_table(s["checks"])))
    return blocks


# ---------------------------------------------------------------- summary dispatch and command line
SUMMARIES = {"sweep": summary_sweep, "q28": summary_q28}


def summary(out) -> dict:
    """The summaries of the parts of S1_PART in pass-2 order (sweep, q28)."""
    ps = parts()
    return {p: SUMMARIES[p](part_dir(out, p)) for p in PASS_SUMMARIES if p in ps}


def limits_lines(js=None) -> list:
    """'<kind> <limit_s> <job id>' per job (run_s1.sh's jobs_limits.txt)."""
    return [f"{j.kind} {int(j.params['limit_s'])} {j.id}" for j in (jobs() if js is None else js)]


def main(argv=None) -> int:
    """ms3_common.main's command line, plus --limits (the job limits of §3.9 for run_s1.sh)."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--limits" in args:
        ap = argparse.ArgumentParser(prog=f"python -m sublet.experiments.{EXP} --limits",
                                     description="the jobs of S1_PART with their limits, '<kind> <limit_s> <id>'")
        ap.add_argument("--limits", action="store_true", required=True)
        ap.parse_args(args)
        js = jobs()
        mc.check_jobs(js)
        for line in limits_lines(js):
            print(line)
        return 0
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=args, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
