"""E5: redundancy under correlated reclaims (design/sim_spec_ms4.md §5; deliverable D33, unit U22; open choices
M15-M19, M36).

Claims: none proven (design Table 5.9). Worst-case bounds ignore correlation; E5 measures the redundancy rule of
design §3.2.6, a heuristic (algos/redundancy.py): a replica is exposed when its lease is alive, revocable, past its
guaranteed period and 60 H_k < lambda_min(P), the fastest load time of its LLM over its X3 pool P; under 'rule' a
group needs a spare when alpha < n_exp nu lambda_min (a5b_exposure_thresholds.json `spare_threshold`), under
'always2' whenever it has an exposed replica. The rule predicts that redundancy pays only for exposed units in large
pools and never triggers under long notice.

Instance (§5.2, M16). configs/bench_e7r.json (all 24 lenders, 5 regions, regional borrowers in 3 tiers, protected
sites per region, unmerged layers) with the overrides time.horizon_min 10080 (one week of 1-min routing),
time.fast_slot_min 1, stranding.mu_over_beta_tilde mu, the menu's contracts and engine.check_invariants true (the
config sets it false, §0 item 5); config seed = lender seed = alignment c, policy seed p.
Menus (M15; a11_calibration.json contracts.<k>.class): short = the spot-like s5_tau5_H0, s5_tau5_H1, s5_tau5_H2 plus
the config's protected contract; long = the AEP-82-like s5_tau5_H60, s5_tau5_H120, s5_tau5_H240 plus protected
(overrides `contracts` and `lender_defaults.menu`; tau and H from a11's contract entries, IR prices from the builder).
Demand (M15, as E6(b)'s rule M31): the builder scales demand to the lendable supply of each menu's longest window, so
each long-menu instance takes clients.demand and borrower_stats of the short-menu instance of the same mu and
alignment (instance.with_demand, as e6.e6b_instance; InstanceError if the client lists or grids differ); the menus
then differ only in contracts and lendable supply and have one BL0a, and bl0a_own_demand (BL0a on the demand the
builder gives the long menu's own instance) is recorded. The correlation levels do not change the instance.
Correlation levels (§5.3, M17), each with I1, 'sell' and 'absorb' (the config's lender model):
  trace    the config's trace lender (ms4_common.mode_lender_model('L-tr'): {})
  sh<p>    'correlated' with p_sh = p in {0.25, 0.5, 1}, groups null (the lenders' Site.group), delay_slots_max
           default (ceil(5 / slow_min) = 1)
  all1     'correlated', p_sh 1, groups 'all': Q44's L-co (q44_study.MODES['L-co'], ms4_common.mode_lender_model)
Policies (§5.4; tag: registry id, parameters, style key of figs/style.py, C18):
  A6-off      A6 {"redundancy": "off"}        a6_red_off
  A6-rule     A6 {}  (redundancy 'rule')      a6
  A6-always2  A6 {"redundancy": "always2"}    a6_always2
  BL3-0       BL3 {"n_extra": 0}              bl3_n0
  BL3-1       BL3 {"n_extra": 1}              bl3_n1
  BL3-2       BL3 {}  (n_extra 2)             bl3
  Sublet      A8 ms4_common.sublet_params(inst): inner BL5, gamma 1, kappa None, B0 = B0_SHARE x e6.bl0a_all(inst)
              of the job's own instance (M36; record B0_rule ms4_common.B0_RULE, certificate ms4_common.a8_record)
Grid (§5.5): 5 levels x 2 menus x 7 tags x 4 alignments x 3 policy seeds at mu / beta~ = 1, plus the default point
(level trace, short menu; M16) at mu / beta~ in {0.2, 0.5, 2} (Q23): 1,092 week runs in 364 jobs.

Jobs (ms3_common ids, design/sim_spec_ms4.md §2.4; one process per job, each in its own 3G scope; all pool jobs):
  e5:run:level=L:menu=M:pol=P:mu=U:c=C    the 3 policy seeds of one tag at one (level, menu, mu, alignment): the
                                          instance (and, for the long menu, the short menu's instance for its
                                          demand), the runs and the run file runs/<job>.json
The jobs have no order constraint (each builds its own instances), so run_e5.sh runs one pool pass.

Reduced job list (smoke runs and tests): MS3_E5_REDUCED=1 (run_e5.sh --reduced sets it) keeps the whole grid of
levels, menus, tags and mu but uses alignment 1, policy seed 0 and a one-day horizon (REDUCED). Default (unset or
0): the full lists above. --estimate uses the per-week-run times of §5.5 (EST_RUN_S, scaled by the horizon), with
BL3 under all1 at A8's time (EST_RUN_S_LEVEL; §5.5: 28.6 s is no bound for BL3 there).

Outputs under out/e5/ (§5.6, §2.6): runs/<job>.json (not versioned), jobs/, logs/, manifest.json, run_e5.log,
summary.json, tables.md. Numeric keys as num_key ("1", "0.2"); a missing value is null with a '<key>_note'.

summary.json (every path of the design grid is present; <level> in LEVELS, <menu> in {short, long}, <mu> in {"0.2",
"0.5", "1", "2"} (the other mu at the default point only), <tag> in TAGS):
  meta                              exp, spec, git_revision, written, reduced (reduced_note), config, horizon_min,
                                    grid {levels, menus, mus, default_point, alignments, alignments_design,
                                    policy_seeds, policy_seeds_design}, levels {level: lender model}, menus {menu:
                                    {contracts, class}}, tags {tag: {policy_id, params, style_key}}, B0_share,
                                    B0_rule, info_class_reported (Sublet), accounting 'overflow' (M2), references.
                                    <mu>.<c> (ms4_common.references of the short-menu instance: BL0a, own capacity,
                                    BL0b in both accountings, the committed price), instances {demand_menu,
                                    by_menu.<menu>.<mu>.<c> {bl0a_usd, bl0a_own_demand, demand_sha256,
                                    own_demand_sha256, instance_hash, instance_hashes_found, n_sites,
                                    n_sites_by_kind, n_contracts, contracts, lam_s {LLM: [min, max]},
                                    lam_s_max_ok}, max_rel_diff_bl0a, note}, redundancy_threshold (a5b's
                                    spare_threshold and alpha), jobs_ok, jobs_missing, ignored_outputs, run_errors
                                    {n_runs_expected (the policy seeds of the ok jobs), n_runs, n_runs_lost, jobs:
                                    [{job, tag, n_runs_expected, n_runs, errors}]} (a run that raised is recorded in
                                    its run file's errors, ms3_common.try_run, and its job stays ok)
  cells.<level>.<menu>.<mu>.<tag>   n_runs, n_runs_expected (alignments x policy seeds of the job grid), alignments,
                                    policy_seeds; cost_over_bl0a (overflow accounting, M2) and the seven fields of
                                    ms4_common.accountings (overflow_usd, total_usd, overflow_over_bl0a,
                                    total_over_bl0a, own_share_of_total, overflow_over_bl0b, total_over_bl0b), each
                                    as metrics.aggregate {n, median, p95, max, median_ci95};
                                    fallback_share_after_reclaims (aggregate over the runs where it is defined, with
                                    n_null), fallback_share, stranding_events_per_day, loads_per_day,
                                    replica_utilization, announcements_per_site_day, n_leases, n_leases_reclaimed
                                    (leases ended by a reclaim), gpu_hours (aggregates); components_over_bl0a
                                    {lease, loading, routing, fallback, stranding, total: mean}; gpu_hour_share
                                    {class: share}; redundancy (A6 tags: buys, no_site, n_exp_total, n_exp_max,
                                    spare_slot_groups as aggregates, share_runs_with_buys, share_runs_exposed; null
                                    with a note for the other tags); certificates (Sublet:
                                    ms4_common.count_certificates, abort_share, t_a, B0_rules; null otherwise)
  exposure.<level>.<menu>.<tag>     A6 tags at mu = 1: n_runs, n_runs_exposed, n_runs_with_buys, buys_total,
                                    no_site_total, placed_share (buys / (buys + no_site): the share of needed spares
                                    that found a site), spare_slot_groups_total, n_exp_total (aggregate), n_exp_max
                                    (max over the runs), lam_s {LLM: [min, max]} over the cell's instances,
                                    lam_s_max_ok; at the default point also by_mu.<mu> for its other mu ("0.2",
                                    "0.5", "2"), the same fields
  pareto.<level>.<menu>             at mu = 1: medians {tag: {cost_over_bl0a, fallback_share_after_reclaims}},
                                    a6_tags, bl3_tags, bl3_pareto (the BL3 tags whose both medians lie below those
                                    of every A6 mode, E5-4), bl3_undecided (a median missing), a6_modes_identical
                                    {n_pairs, n_identical, all_identical} (a6_identical), rule
  certificates                      every Sublet run: count_certificates {n, held, by_case, failures} plus
                                    failure_runs, w_c_runs (job, seed, t_a), abort_share, B0_rules
  checks.E5-1 ... E5-6              {status ('pass', 'fail', 'missing', 'informative'), claim, the check's inputs};
                                    E5-6 per (level, menu) over every mu of the point, with by_mu.<mu>
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
from . import ms4_common as m4
from .ms3_common import Job, job_id, num_key, put

EXP = "e5"
SPEC = "design/sim_spec_ms4.md §5"
CONFIG = "bench_e7r.json"
WEEK_MIN = 10080
A11_FILE = paths.ANALYSIS_OUT / "a11_calibration.json"
A5B_FILE = paths.ANALYSIS_OUT / "a5b_exposure_thresholds.json"
INPUT_FILES = (paths.CONFIGS / CONFIG, A11_FILE, paths.ANALYSIS_OUT / "a12_sim_inputs.json",
               paths.ANALYSIS_OUT / "a12_minute_io.npz", A5B_FILE)
# M15: the menus' revocable contracts and their a11 class (a11_calibration.json contracts.<k>.class)
MENUS = {"short": ("s5_tau5_H0", "s5_tau5_H1", "s5_tau5_H2"),
         "long": ("s5_tau5_H60", "s5_tau5_H120", "s5_tau5_H240")}
MENU_CLASS = {"short": "spot-like", "long": "AEP-82-like"}
DEMAND_MENU = "short"                 # M15: every instance carries the short menu's demand
PROTECTED_ID = "protected"            # the config's protected contract, kept in both menus
# M17: the correlation levels (§5.3)
LEVELS = ("trace", "sh0.25", "sh0.5", "sh1", "all1")
P_SH = {"sh0.25": 0.25, "sh0.5": 0.5, "sh1": 1.0}
TRACE_MODE, ALL_MODE = "L-tr", "L-co"  # q44_study.MODES of the levels trace and all1
# §5.4: tag -> (registry id, parameters; None: M36's ms4_common.sublet_params of the job's instance, style key)
TAGS = {"A6-off": ("A6", {"redundancy": "off"}, "a6_red_off"),
        "A6-rule": ("A6", {}, "a6"),
        "A6-always2": ("A6", {"redundancy": "always2"}, "a6_always2"),
        "BL3-0": ("BL3", {"n_extra": 0}, "bl3_n0"),
        "BL3-1": ("BL3", {"n_extra": 1}, "bl3_n1"),
        "BL3-2": ("BL3", {}, "bl3"),
        "Sublet": ("A8", None, "sublet")}
A6_TAGS = ("A6-off", "A6-rule", "A6-always2")
BL3_TAGS = ("BL3-0", "BL3-1", "BL3-2")
SUBLET_TAG = "Sublet"
SUBLET_INNER = "BL5"
MU_MAIN = 1.0
MUS_SWEEP = (0.2, 0.5, 2.0)            # Q23: at the default point only
DEFAULT_POINT = ("trace", "short")     # M16
ALIGNMENTS = (1, 2, 3, 4)
POLICY_SEEDS = (0, 1, 2)
REDUCED_ENV = "MS3_E5_REDUCED"
REDUCED = {"alignments": (1,), "policy_seeds": (0,), "horizon_min": 1440}
LAM_LIMIT_S = 3600.0                   # E5-2: max_l lam_s[j, l] <= 60 min, the shortest long-menu notice
COMPONENTS = ("lease", "loading", "routing", "fallback", "stranding", "total")     # q44_study.grouped
ACCOUNTING_KEYS = ("overflow_usd", "total_usd", "overflow_over_bl0a", "total_over_bl0a", "own_share_of_total",
                   "overflow_over_bl0b", "total_over_bl0b")
METRIC_KEYS = ("fallback_share", "stranding_events_per_day", "loads_per_day", "replica_utilization",
               "announcements_per_site_day")
RED_KEYS = ("buys", "buys_wide", "no_site", "n_exp_total", "n_exp_max", "spare_slot_groups")
RED_SCALARS = ("mode", "nu_per_day", "zeta", "buys", "buys_wide", "releases", "refused", "deaths", "no_site",
               "n_exp_total", "n_exp_max", "spare_slot_groups")    # buys_wide: C26's spares outside the X3 pool
# §5.5 time constants: seconds per week run (A6 E6(b)'s largest, BL3 the slowest measured baseline on the E7 week,
# Sublet its E7 week under M36); BL3 under all1 takes A8's time: there BL3 replaces each lease under notice while the
# noticed lease serves and is billed until its death (baselines/spothedge.py:14), its leases per run grow with the
# reclaims, and its week time is not measured in a versioned file (§5.5)
EST_RUN_S = {"A6": 95.6, "BL3": 28.6, "A8": 140.2}
EST_RUN_S_LEVEL = {("BL3", "all1"): EST_RUN_S["A8"]}
SAME_REL = 1e-9                        # a6_identical: totals equal to this relative tolerance
CHECK_CLAIMS = {
    "E5-1": "every run: invariant_failures empty and gpu_only_lease_slots 0; no run of an ok job lost to an error",
    "E5-2": "long menu: A6-rule and A6-always2 have n_exp_total 0 and buys 0 in every run whose instance has "
            "max_l lam_s[j, l] <= 3600 s for every LLM j (contracts with H_k >= lambda_min never create exposure, "
            "design §3.2.6); runs of an instance above the limit are listed and not checked",
    "E5-3": "A6-always2: every run with n_exp_total > 0 has buys + no_site > 0 (a spare whenever a group has an "
            "exposed replica, or no site for one; design §3.2.6)",
    "E5-4": "per (level, menu): the BL3 variants whose median cost over BL0a and median fallback share after "
            "reclaims are both below those of every A6 mode (Pareto gains; design §5.5 E5, reading), the long menu "
            "reported separately (informative)",
    "E5-5": "every Sublet run: certificate held in Theorem W's proven cases (W(a), W(b); PROVEN for the engine as "
            "implemented under C1-C3, audited); W(c) runs (CONJECTURE) counted; no Sublet run lost to an error",
    "E5-6": "the share of A6-rule runs that bought a spare, per (level, menu) over every mu / beta~ of the point and "
            "per mu (by_mu), against the rule's prediction (spares only for pools above about 32 exposed replicas at "
            "alpha = 0.40; a5b_exposure_thresholds.json spare_threshold) (informative)"}


# ---------------------------------------------------------------- settings and grid
def reduced() -> bool:
    return os.environ.get(REDUCED_ENV, "0") == "1"


def settings() -> dict:
    """The job grid's alignments, policy seeds and horizon: the full grid, or REDUCED with MS3_E5_REDUCED=1."""
    red = reduced()
    return {"reduced": red, "alignments": tuple(REDUCED["alignments"]) if red else ALIGNMENTS,
            "policy_seeds": tuple(REDUCED["policy_seeds"]) if red else POLICY_SEEDS,
            "horizon_min": int(REDUCED["horizon_min"]) if red else WEEK_MIN}


def points() -> list[tuple]:
    """(level, menu, mu) of the design grid (§5.5): every level and menu at mu = 1, then the default point (level
    trace, short menu) at the other mu values."""
    out = [(lv, mn, MU_MAIN) for lv in LEVELS for mn in MENUS]
    out += [(DEFAULT_POINT[0], DEFAULT_POINT[1], mu) for mu in MUS_SWEEP]
    return out


def est_run_s(pid: str, level: str) -> float:
    """Seconds per week run of a registry id at a correlation level (EST_RUN_S, EST_RUN_S_LEVEL; §5.5)."""
    return float(EST_RUN_S_LEVEL.get((pid, level), EST_RUN_S[pid]))


def run_job_id(level: str, menu: str, tag: str, mu, c: int) -> str:
    return job_id(EXP, "run", level=level, menu=menu, pol=tag, mu=num_key(mu), c=int(c))


def run_path(out, jid: str) -> Path:
    return Path(out) / "runs" / mc.job_file_name(jid)


def jobs() -> list[Job]:
    """The E5 jobs in run order: the points of points(), each tag of TAGS, each alignment."""
    S = settings()
    frac = S["horizon_min"] / WEEK_MIN
    out = []
    for level, menu, mu in points():
        for tag, (pid, _, _) in TAGS.items():
            for c in S["alignments"]:
                out.append(Job(run_job_id(level, menu, tag, mu, c), "pool",
                               {"level": level, "menu": menu, "tag": tag, "mu": float(mu), "c": int(c),
                                "policy_seeds": list(S["policy_seeds"]), "horizon_min": S["horizon_min"]},
                               est_s=len(S["policy_seeds"]) * est_run_s(pid, level) * frac))
    return out


# ---------------------------------------------------------------- menus, levels, instances (§5.2, §5.3)
@lru_cache(maxsize=None)
def _a11_contracts() -> dict:
    with open(A11_FILE) as f:
        return json.load(f)["contracts"]


@lru_cache(maxsize=None)
def _protected() -> dict:
    with open(paths.CONFIGS / CONFIG) as f:
        cs = json.load(f)["contracts"]
    hit = [c for c in cs if c.get("id") == PROTECTED_ID]
    if len(hit) != 1:
        raise ValueError(f"configs/{CONFIG} has {len(hit)} contracts with id {PROTECTED_ID!r}")
    return dict(hit[0])


def menu_contracts(menu: str) -> list[dict]:
    """The `contracts` override of a menu (M15): its revocable contracts {id, tau_min, H_min} with tau and H from
    a11_calibration.json contracts.<id>, then the config's protected contract."""
    if menu not in MENUS:
        raise ValueError(f"unknown E5 menu {menu!r}; known {list(MENUS)}")
    a11 = _a11_contracts()
    out = []
    for k in MENUS[menu]:
        e = a11[k]
        out.append({"id": k, "tau_min": int(e["tau_min"]), "H_min": int(e["H_min"])})
    return out + [_protected()]


def menu_classes(menu: str) -> dict:
    """{contract id: a11 class} of a menu's revocable contracts."""
    return {k: _a11_contracts()[k]["class"] for k in MENUS[menu]}


def level_lender_model(level: str) -> dict:
    """The run spec's lender model of a correlation level (§5.3, M17): {} (the config's trace lender) for 'trace';
    'correlated' with p_sh and groups null for sh0.25, sh0.5 and sh1 (delay_slots_max left to its default); Q44's
    L-co ('correlated', p_sh 1, groups 'all') for all1. The config's information I1, 'sell' and 'absorb' stay."""
    if level == "trace":
        return m4.mode_lender_model(TRACE_MODE)
    if level == "all1":
        return m4.mode_lender_model(ALL_MODE)
    if level in P_SH:
        return {"schedule": "correlated", "params": {"p_sh": P_SH[level], "groups": None}}
    raise ValueError(f"unknown E5 correlation level {level!r}; known {list(LEVELS)}")


def overrides(menu: str, mu: float, horizon_min: int = WEEK_MIN) -> dict:
    """The instance overrides of a (menu, mu) on bench_e7r.json (§5.2): one week of 1-min routing, the menu's
    contracts and lender menu, mu / beta~."""
    return {"time.horizon_min": int(horizon_min), "time.fast_slot_min": 1, "contracts": menu_contracts(menu),
            "lender_defaults.menu": list(MENUS[menu]), "stranding.mu_over_beta_tilde": float(mu)}


def e5_spec(menu: str, mu: float, c: int, level: str = "trace", policy_id: str = "BL0a",
            params: Optional[dict] = None, horizon_min: Optional[int] = None) -> dict:
    """The validated run spec (drivers.run.load_run_spec) of one policy on one (level, menu, mu, alignment):
    bench_e7r.json with overrides(), the level's lender model over the config's, engine.check_invariants true, config
    seed c = lender seed."""
    from ..drivers.run import load_run_spec
    hz = settings()["horizon_min"] if horizon_min is None else int(horizon_min)
    name = f"e5_{level}_{menu}_mu{num_key(mu)}_c{int(c)}"
    return load_run_spec({"schema_version": 1, "name": name, "instance": CONFIG, "overrides": overrides(menu, mu, hz),
                          "lender_model": level_lender_model(level), "engine": {"check_invariants": True},
                          "policy": {"id": policy_id, "params": copy.deepcopy(dict(params or {}))},
                          "seeds": {"config": [int(c)], "lender": "config", "policy": [0]}, "bench": None,
                          "out": "code/sim/out/e5/runs"})


def carry_demand(inst, ref, what: str = ""):
    """`inst` with clients.demand (instance.with_demand) and borrower_stats of `ref` (M15, as e6.e6b_instance): the
    two must have the same client lists and grid, else InstanceError."""
    from ..instance import InstanceError, with_demand
    a, b = inst.clients, ref.clients
    same = (np.array_equal(a.llm, b.llm) and a.region == b.region and a.slo_class == b.slo_class
            and a.borrowers == b.borrowers and inst.grid == ref.grid)
    if not same:
        raise InstanceError(f"E5 {what}: its clients or grid differ from the {DEMAND_MENU} menu's instance, so it "
                            "cannot take that menu's demand")
    return dataclasses.replace(with_demand(inst, ref.clients.demand),
                               borrower_stats={k: dict(v) for k, v in ref.borrower_stats.items()})


def e5_instance(menu: str, mu: float, c: int, level: str = "trace", horizon_min: Optional[int] = None) -> tuple:
    """(inst, model, ecfg, info) of one (level, menu, mu, alignment): the instance the builder gives the menu (its
    contracts, sites and lendable supply) with, for the long menu, the demand and borrower_stats of the short menu's
    instance at the same mu, alignment and horizon (carry_demand; M15); model is the level's lender model. info:
    demand_menu, bl0a_usd (e6.bl0a_all of the demand used), bl0a_own_demand (BL0a on the builder's own demand of the
    menu's instance), demand_sha256, own_demand_sha256, demand_gamma_notes (the builder's demand scaling of the
    demand used, i.e. of the short menu's instance) and own_gamma_notes (that of the menu's own instance)."""
    from ..drivers.run import build
    from .e6 import bl0a_all, demand_sha256
    inst, model, ecfg = build(e5_spec(menu, mu, c, level, horizon_min=horizon_min), int(c))
    if not ecfg.check_invariants:
        raise RuntimeError("E5 runs need check_invariants=True (§0 item 5)")
    own, own_sha, own_gamma = float(bl0a_all(inst)), demand_sha256(inst), gamma_notes(inst)
    demand_gamma = own_gamma
    if menu != DEMAND_MENU:
        ref = build(e5_spec(DEMAND_MENU, mu, c, level, horizon_min=horizon_min), int(c))[0]
        inst = carry_demand(inst, ref, f"menu {menu}, mu {num_key(mu)}, c = {int(c)}")
        demand_gamma = gamma_notes(ref)
    info = {"demand_menu": DEMAND_MENU, "bl0a_usd": float(bl0a_all(inst)), "bl0a_own_demand": own,
            "demand_sha256": demand_sha256(inst), "own_demand_sha256": own_sha, "demand_gamma_notes": demand_gamma,
            "own_gamma_notes": own_gamma}
    return inst, model, ecfg, info


def gamma_notes(inst) -> list:
    """The builder's notes on the regional demand scaling (Gamma, tightness, supply) of an instance."""
    return [n for n in inst.notes if "Gamma" in n]


def lam_range(inst) -> dict:
    """{LLM id: [min, max]} of lam_s[j, l] over the instance's sites (seconds; E5-2's condition)."""
    lam = np.asarray(inst.lam_s, dtype=np.float64)
    return {L.id: [float(lam[j].min()), float(lam[j].max())] for j, L in enumerate(inst.llms)}


def instance_info(inst) -> dict:
    """The instance record of a run file (the demand scaling notes are e5_instance's demand_gamma_notes and
    own_gamma_notes, beside it)."""
    kinds: dict = {}
    for s in inst.sites:
        kinds[s.kind] = kinds.get(s.kind, 0) + 1
    lam = lam_range(inst)
    g = inst.grid
    return {"instance_hash": mc.instance_hash(inst), "n_sites": int(inst.m), "n_sites_by_kind": kinds,
            "n_contracts": int(inst.K), "contracts": [x.id for x in inst.contracts], "n_clients": int(inst.n),
            "n_lenders_with_sites": sum(1 for lt in inst.lenders if len(lt.site_index) > 0
                                        and lt.kind not in ("protected", "synthetic")),
            "T_slow": int(g.T_slow), "T_fast": int(g.T_fast), "horizon_min": int(g.horizon_min),
            "start_mow": int(g.start_mow), "lam_s": lam,
            "lam_s_max_ok": bool(all(v[1] <= LAM_LIMIT_S for v in lam.values())),
            "lender_note": [n for n in inst.notes if "trace lenders have" in n]}


def _sha256(path) -> Optional[str]:
    p = Path(path)
    if not p.is_file():
        return None
    with open(p, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def _jsonish(x):
    """metrics._jsonable (non-finite floats as strings) for the free-form parts of run files, as e1.py writes them."""
    from ..metrics import _jsonable
    return _jsonable(x)


def _model_dict(model) -> dict:
    return {"schedule": model.schedule, "information": model.information, "on_unavailable": model.on_unavailable,
            "violations": model.violations, "params": dict(model.params or {})}


# ---------------------------------------------------------------- job: one (level, menu, tag, mu, alignment)
def run_row(res, inst, refs: dict, pid: str, params: dict, ps: int, pol, information: str, wall: float) -> dict:
    """The record of one run (§5.6): costs in both accountings (cost_over_bl0a in overflow accounting, M2), the
    metrics of metrics.run_metrics, the realized intensity, invariants, plan class, the A6 redundancy report and, for
    A8, the fields of ms4_common.a8_record (B0_rule, B0_usd, bl0a_usd, gamma, kappa, info_class_reported, the
    certificate and its case, t_a, aborted)."""
    from ..algos import registry
    from ..metrics import run_metrics
    from . import q44_study as q44
    m = run_metrics(res, inst)
    rep = res.metrics.get("policy") or {}
    total = float(res.components["total"])
    acc = m4.accountings(total, inst, refs)
    rp = {**params, **(pol.params() or {})} if callable(getattr(pol, "params", None)) else dict(params)
    ends: dict = {}
    for L in res.leases:
        ends[L.end_cause] = ends.get(L.end_cause, 0) + 1
    row = {"policy_seed": int(ps), "total": total, "components": {k: float(v) for k, v in res.components.items()},
           "grouped": q44.grouped(res.components), "accountings": acc, "cost_over_bl0a": acc["overflow_over_bl0a"],
           "fallback_share": m["fallback_share"], "fallback_share_after_reclaims": m["fallback_share_after_reclaims"],
           "stranding_events_per_day": float(m["stranding_events_per_day"]),
           "loads_per_day": float(m["loads_per_day"]), "replica_utilization": m["replica_utilization"],
           "gpu_hours_by_class": {k: float(v) for k, v in (m.get("gpu_hours_by_class") or {}).items()},
           "gpu_only_lease_slots": int(m["gpu_only_lease_slots"]),
           "n_invariant_failures": len(res.invariant_failures), "invariant_first": list(res.invariant_failures[:2]),
           "plan_class_p1": bool(q44.plan_class_p1(res, inst)), "intensity": q44.intensity(res, inst),
           "n_leases": len(res.leases), "leases_by_end_cause": ends, "schedule_hash": mc.schedule_hash(res.schedule),
           "seeds": dict(res.seeds), "resolved_params": rp,
           "info_class": registry.info_class(pid, rp, information),
           "wall_s": wall, "engine_wall_s": res.runtime.get("wall_s"), "peak_rss_mb": res.runtime.get("peak_rss_mb")}
    row["announcements_per_site_day"] = row["intensity"]["announcements_per_site_day"]
    if row["fallback_share_after_reclaims"] is None:
        row["fallback_share_after_reclaims_note"] = "no reclaim-caused capacity drop in the run"
    if pid == "A6":
        red = rep.get("redundancy") or {}
        row["redundancy"] = {k: red.get(k) for k in RED_SCALARS}
    if pid == "A8":
        row.update(m4.a8_record(res, inst, params, information))
    return row


def run_cell(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """The policy seeds of one tag at one (level, menu, mu, alignment) (§5.5): the instance (e5_instance), the
    parameters (Sublet: ms4_common.sublet_params of this instance, M36), the engine runs and the run file."""
    from ..drivers.run import driver_inputs, make_policy
    from ..engine import simulate
    from ..lender import resolve_params
    p = job.params
    level, menu, tag, mu, c = p["level"], p["menu"], p["tag"], float(p["mu"]), int(p["c"])
    hz = int(p["horizon_min"])
    t_start = time.perf_counter()
    inst, model, ecfg, dinfo = e5_instance(menu, mu, c, level, hz)
    build_s = time.perf_counter() - t_start
    pid, params, sk = TAGS[tag]
    params = m4.sublet_params(inst, inner=SUBLET_INNER) if params is None else copy.deepcopy(params)
    spec = e5_spec(menu, mu, c, level, pid, params, hz)
    inputs, imeta = driver_inputs(pid, params, inst)
    refs = m4.references(inst)
    errors: list = []
    rows = []
    for ps in p["policy_seeds"]:
        def one(ps=ps):
            t0 = time.perf_counter()
            pol = make_policy(spec, inst, inputs=inputs)
            res = simulate(inst, pol, model, ecfg, lender_seed=c, policy_seed=int(ps))
            return run_row(res, inst, refs, pid, params, ps, pol, model.information, time.perf_counter() - t0)
        row = mc.try_run(errors, f"{tag} p{ps}", one)
        if row is None:
            continue
        rows.append(row)
        print(f"[e5] {job.id} p{ps}: total {row['total']:.2f} USD ({row['cost_over_bl0a']:.4f} x BL0a), "
              f"{row['wall_s']:.1f} s", flush=True)
    rec = {"job": job.id, "exp": EXP, "level": level, "menu": menu, "tag": tag, "mu": mu, "c": c, "policy_id": pid,
           "params": params, "style_key": sk, "horizon_min": hz, "config": CONFIG,
           "overrides": overrides(menu, mu, hz), "lender_model": _model_dict(model),
           "lender_params_resolved": resolve_params(inst, model), "instance": instance_info(inst), **dinfo,
           "references": refs, "driver_inputs": imeta, "policy_seeds": list(p["policy_seeds"]), "runs": rows,
           "build_s": build_s, "errors": [{k: v for k, v in e.items() if k != "traceback"} for e in errors],
           "git_revision": mc.git_revision(), "versions": mc.versions(), "wall_s": time.perf_counter() - t_start}
    outputs.dump(_jsonish(rec), run_path(out, job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "bl0a": dinfo["bl0a_usd"], "totals": [r["total"] for r in rows]}


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    _, part, _ = mc.parse_job_id(job.id)
    if part == "run":
        return run_cell(job, outputs, out)
    raise ValueError(f"unknown E5 job {job.id!r}")


def manifest_extra(out) -> dict:
    """The instance hash of every (menu, mu, alignment) of the grid (the level does not change the instance) and the
    sha256 of the input files."""
    S = settings()
    hashes: dict = {}
    for menu, mu in sorted({(mn, mu) for _, mn, mu in points()}):
        for c in S["alignments"]:
            inst, _, _, info = e5_instance(menu, mu, c, "trace", S["horizon_min"])
            hashes[f"menu={menu}:mu={num_key(mu)}:c={int(c)}"] = {"instance_hash": mc.instance_hash(inst),
                                                                  "demand_sha256": info["demand_sha256"],
                                                                  "bl0a_usd": info["bl0a_usd"]}
    return {"instance_hashes": hashes, "settings": {k: (list(v) if isinstance(v, tuple) else v) for k, v in S.items()},
            "inputs_sha256": {str(f.relative_to(paths.REPO)): _sha256(f) for f in INPUT_FILES}}


# ---------------------------------------------------------------- summary
def _agg(values: list, note: str) -> dict:
    """metrics.aggregate of the values; without values its fields null with `note` (§2.6, null forms)."""
    a = mc.median_summary(values)
    if not values:
        for k in ("median", "p95", "max"):
            put(a, k, None, note)
        a["median_ci95_note"] = note
    return a


def _vals(rows: list, key: str) -> list:
    return [float(r[key]) for r in rows if r.get(key) is not None]


def _mean(d: dict, key: str, vals: list, note: str) -> None:
    put(d, key, float(np.mean(vals)) if vals else None, note)


def cell_entry(rows: list, tag: str, note: str = "no run of this tag at this point in the outputs",
               n_expected: Optional[int] = None) -> dict:
    """cells.<level>.<menu>.<mu>.<tag> over the runs `rows` (each with 'c' set), the same fields with or without
    runs (module docstring); n_expected the cell's runs in the job grid (default: the job grid of settings())."""
    pid = TAGS[tag][0]
    if n_expected is None:
        S = settings()
        n_expected = len(S["alignments"]) * len(S["policy_seeds"])
    e = {"n_runs": len(rows), "n_runs_expected": int(n_expected), "alignments": sorted({int(r["c"]) for r in rows}),
         "policy_seeds": sorted({int(r["policy_seed"]) for r in rows})}
    e["cost_over_bl0a"] = _agg(_vals(rows, "cost_over_bl0a"), note)
    for k in ACCOUNTING_KEYS:
        e[k] = _agg([float(r["accountings"][k]) for r in rows if r["accountings"].get(k) is not None], note)
    fr = _vals(rows, "fallback_share_after_reclaims")
    e["fallback_share_after_reclaims"] = _agg(fr, note if not rows else "no run with a reclaim-caused capacity drop")
    e["fallback_share_after_reclaims"]["n_null"] = len(rows) - len(fr)
    for k in METRIC_KEYS:
        e[k] = _agg(_vals(rows, k), note)
    e["n_leases"] = _agg(_vals(rows, "n_leases"), note)
    e["n_leases_reclaimed"] = _agg([float((r.get("leases_by_end_cause") or {}).get("reclaim", 0)) for r in rows
                                    if r.get("leases_by_end_cause") is not None], note)
    e["gpu_hours"] = _agg([float(sum(r["gpu_hours_by_class"].values())) for r in rows], note)
    comp = {}
    for k in COMPONENTS:
        _mean(comp, k, [r["grouped"][k] / r["bl0a_usd"] for r in rows if r["bl0a_usd"] > 0], note)
    e["components_over_bl0a"] = comp
    cls: dict = {}
    for r in rows:
        for k, v in r["gpu_hours_by_class"].items():
            cls[k] = cls.get(k, 0.0) + v
    tot = sum(cls.values())
    e["gpu_hour_share"] = {k: v / tot for k, v in sorted(cls.items())} if tot > 0 else {}
    if not tot > 0:
        e["gpu_hour_share_note"] = note if not rows else "no GPU-hour"
    if pid == "A6":
        red = {k: _agg([float(r["redundancy"][k]) for r in rows if (r.get("redundancy") or {}).get(k) is not None],
                       note) for k in RED_KEYS}
        put(red, "share_runs_with_buys", sum(1 for r in rows if (r["redundancy"].get("buys") or 0) > 0) / len(rows)
            if rows else None, note)
        put(red, "share_runs_exposed", sum(1 for r in rows if (r["redundancy"].get("n_exp_total") or 0) > 0)
            / len(rows) if rows else None, note)
        e["redundancy"] = red
    else:
        put(e, "redundancy", None, f"{pid} has no redundancy rule (A6 only)")
    if pid == "A8":
        cc = m4.count_certificates(rows)
        put(cc, "abort_share", sum(1 for r in rows if r.get("aborted")) / len(rows) if rows else None, note)
        cc["t_a"] = sorted(int(r["t_a"]) for r in rows if r.get("t_a") is not None)
        cc["B0_rules"] = _count(r.get("B0_rule") for r in rows)
        e["certificates"] = cc
    else:
        put(e, "certificates", None, f"{pid} is not guarded (A8 only)")
    return e


def _count(xs) -> dict:
    out: dict = {}
    for x in xs:
        out[str(x)] = out.get(str(x), 0) + 1
    return dict(sorted(out.items()))


def _placed(d: dict, buys: int, no_site: int, note: str) -> None:
    """d['placed_share'] = buys / (buys + no_site), the share of needed spares that found a site (RedundancyRule:
    no_site counts a needed spare without a site); null with `note` when no spare was needed."""
    put(d, "placed_share", buys / (buys + no_site) if buys + no_site > 0 else None, note)


def exposure_entry(rows: list, insts: list, note: str = "no run of this tag at this point in the outputs") -> dict:
    """exposure.<level>.<menu>.<tag> of an A6 tag at one mu (module docstring); `insts` the instance records of the
    cell's run files."""
    red = [r["redundancy"] for r in rows if r.get("redundancy")]
    e = {"n_runs": len(rows), "n_runs_exposed": sum(1 for x in red if (x.get("n_exp_total") or 0) > 0),
         "n_runs_with_buys": sum(1 for x in red if (x.get("buys") or 0) > 0),
         "buys_total": int(sum(x.get("buys") or 0 for x in red)),
         "no_site_total": int(sum(x.get("no_site") or 0 for x in red))}
    _placed(e, e["buys_total"], e["no_site_total"], note if not rows else "no spare needed in these runs")
    e.update(spare_slot_groups_total=int(sum(x.get("spare_slot_groups") or 0 for x in red)),
             n_exp_total=_agg([float(x["n_exp_total"]) for x in red if x.get("n_exp_total") is not None], note))
    put(e, "n_exp_max", max((int(x["n_exp_max"]) for x in red if x.get("n_exp_max") is not None), default=None), note)
    lam: dict = {}
    for i in insts:
        for j, (lo, hi) in i["lam_s"].items():
            cur = lam.get(j)
            lam[j] = [lo, hi] if cur is None else [min(cur[0], lo), max(cur[1], hi)]
    e["lam_s"] = lam
    put(e, "lam_s_max_ok", bool(all(i["lam_s_max_ok"] for i in insts)) if insts else None, note)
    if not lam:
        e["lam_s_note"] = note
    return e


def pareto_entry(cells_mu1: dict, menu: str) -> dict:
    """pareto.<level>.<menu> (E5-4): the BL3 tags whose median cost over BL0a and median fallback share after
    reclaims are both strictly below those of every A6 mode; a comparison with a missing median is undecided."""
    med = {t: {"cost_over_bl0a": cells_mu1[t]["cost_over_bl0a"]["median"],
               "fallback_share_after_reclaims": cells_mu1[t]["fallback_share_after_reclaims"]["median"]}
           for t in A6_TAGS + BL3_TAGS}
    keys = ("cost_over_bl0a", "fallback_share_after_reclaims")
    gains, undecided = [], []
    for b in BL3_TAGS:
        vals = [(med[b][k], med[a][k]) for a in A6_TAGS for k in keys]
        if any(x is None or y is None for x, y in vals):
            undecided.append(b)
        elif all(x < y for x, y in vals):
            gains.append(b)
    return {"medians": med, "a6_tags": list(A6_TAGS), "bl3_tags": list(BL3_TAGS), "bl3_pareto": gains,
            "bl3_undecided": undecided, "menu": menu,
            "rule": "a BL3 tag is listed when its median cost over BL0a and its median fallback share after reclaims "
                    "are both below those of every A6 mode (mu = 1, medians over the alignments and policy seeds)"}


def a6_identical(by_tag: dict) -> dict:
    """Whether the A6 modes ran alike at one point: over the (alignment, policy seed) pairs with a run of every A6 tag
    in `by_tag` {tag: rows}, the pairs whose totals agree to SAME_REL and whose lease counts are equal (the modes
    differ only in their spares, so such pairs had no spare that changed the run)."""
    runs = [{(int(r["c"]), int(r["policy_seed"])): r for r in by_tag.get(t, [])} for t in A6_TAGS]
    pairs = sorted(set.intersection(*(set(x) for x in runs)))
    same = 0
    for p in pairs:
        rs = [x[p] for x in runs]
        tot = [float(r["total"]) for r in rs]
        same += int(max(tot) - min(tot) <= SAME_REL * max(1.0, abs(tot[0]))
                    and len({r.get("n_leases") for r in rs}) == 1)
    e = {"n_pairs": len(pairs), "n_identical": same}
    put(e, "all_identical", same == len(pairs) if pairs else None, "no (alignment, policy seed) with a run of every "
        "A6 tag")
    return e


@lru_cache(maxsize=None)
def redundancy_threshold() -> dict:
    """a5b_exposure_thresholds.json's spare_threshold with its alpha (inputs.alpha): the rule's prediction of E5-6."""
    with open(A5B_FILE) as f:
        d = json.load(f)
    st = dict(d["spare_threshold"])
    return {"n_exp_threshold": float(st["n_exp_threshold"]), "alpha": float(d["inputs"]["alpha"]),
            "nu_per_day": float(st["nu_per_day_used"]), "lambda_s": float(st["lambda_s"]), "rule": st.get("rule"),
            "source": "code/analysis/out/a5b_exposure_thresholds.json spare_threshold, inputs.alpha"}


def _brief(r: dict, keys=()) -> dict:
    return {"job": r["job"], "policy_seed": r["policy_seed"], **{k: r.get(k) for k in keys}}


def lost_runs(data: dict) -> list:
    """The ok jobs among the run files `data` {job id: run file} with a run lost: fewer runs than policy seeds, or an
    error in the run file (a run that raised, recorded by ms3_common.try_run while the job stays ok; §2.4). Each
    {job, tag, n_runs_expected, n_runs, errors [{tag, error}]}."""
    out = []
    for jid, d in sorted(data.items()):
        want, got = len(d.get("policy_seeds") or []), len(d.get("runs") or [])
        errs = [{"tag": e.get("tag"), "error": e.get("error")} for e in d.get("errors") or []]
        if got < want or errs:
            out.append({"job": jid, "tag": d["tag"], "n_runs_expected": want, "n_runs": got, "errors": errs})
    return out


def _n_lost(lost) -> int:
    return int(sum(max(0, x["n_runs_expected"] - x["n_runs"]) for x in lost))


def _spare_counts(rows: list, thr: float, note: str) -> dict:
    """E5-6's counts over A6-rule runs: runs, runs that bought a spare and their share, n_exp_max (max, median) and the
    runs by bought or not and n_exp_max above `thr` or at most it ('below')."""
    b = {"n_runs": len(rows), "n_with_buys": 0, "bought_above": 0, "bought_below": 0, "not_bought_above": 0,
         "not_bought_below": 0}
    nx = []
    for r in rows:
        x = r["redundancy"]
        bought = (x.get("buys") or 0) > 0
        nx.append(int(x.get("n_exp_max") or 0))
        b["n_with_buys"] += int(bought)
        b[("bought_" if bought else "not_bought_") + ("above" if nx[-1] > thr else "below")] += 1
    put(b, "share_with_buys", b["n_with_buys"] / len(rows) if rows else None, note)
    b["n_exp_max"] = {}
    put(b["n_exp_max"], "max", max(nx) if nx else None, note)
    put(b["n_exp_max"], "median", float(np.median(nx)) if nx else None, note)
    return b


def build_checks(rows: list, lost: list = ()) -> dict:
    """checks.E5-1 ... E5-6 from every run row (each with job, level, menu, tag, mu, c and its instance record) and
    the lost runs of the ok jobs (lost_runs)."""
    ch = {}
    lost = list(lost)
    n_lost = _n_lost(lost)
    inv = [_brief(r, ("n_invariant_failures", "invariant_first")) for r in rows if r["n_invariant_failures"]]
    gpu = [_brief(r, ("gpu_only_lease_slots",)) for r in rows if r["gpu_only_lease_slots"]]
    ch["E5-1"] = {"status": ("pass" if not inv and not gpu and not lost else "fail") if rows or lost else "missing",
                  "n_runs": len(rows), "n_runs_expected": len(rows) + n_lost, "n_runs_lost": n_lost,
                  "lost": lost[:20], "n_invariant_failures": len(inv), "n_gpu_only_lease_slots": len(gpu),
                  "invariant_failures": inv[:20], "gpu_only_lease_slots": gpu[:20]}
    # E5-2: long menu, A6-rule and A6-always2
    e2r = [r for r in rows if r["menu"] == "long" and r["tag"] in ("A6-rule", "A6-always2")]
    ok_lam = [r for r in e2r if r["instance"]["lam_s_max_ok"]]
    unchecked = [_brief(r, ("tag", "level", "mu", "c")) | {"lam_s": r["instance"]["lam_s"]}
                 for r in e2r if not r["instance"]["lam_s_max_ok"]]
    bad = [_brief(r, ("tag", "level", "mu", "c")) | {k: r["redundancy"].get(k) for k in ("n_exp_total", "buys")}
           for r in ok_lam if (r["redundancy"].get("n_exp_total") or 0) != 0 or (r["redundancy"].get("buys") or 0) != 0]
    lam_max = {}
    for r in e2r:
        for j, (_, hi) in r["instance"]["lam_s"].items():
            lam_max[j] = max(lam_max.get(j, 0.0), hi)
    st = ("pass" if not bad else "fail") if ok_lam else "missing"
    ch["E5-2"] = {"status": st, "n_runs": len(e2r), "n_checked": len(ok_lam), "n_unchecked": len(unchecked),
                  "unchecked": unchecked[:50], "limit_s": LAM_LIMIT_S, "lam_s_max_by_llm": lam_max,
                  "n_failures": len(bad), "failures": bad[:50]}
    if st == "missing":
        ch["E5-2"]["status_note"] = ("no long-menu A6-rule or A6-always2 run" if not e2r else
                                     "every long-menu A6-rule and A6-always2 run has an LLM above the limit")
    # E5-3: A6-always2
    a2 = [r for r in rows if r["tag"] == "A6-always2"]
    exp = [r for r in a2 if (r["redundancy"].get("n_exp_total") or 0) > 0]
    bad3 = [_brief(r, ("level", "menu", "mu", "c")) | {k: r["redundancy"].get(k) for k in ("n_exp_total", "buys",
                                                                                            "no_site")}
            for r in exp if (r["redundancy"].get("buys") or 0) + (r["redundancy"].get("no_site") or 0) <= 0]
    ch["E5-3"] = {"status": ("pass" if not bad3 else "fail") if a2 else "missing", "n_runs": len(a2),
                  "n_runs_exposed": len(exp), "n_failures": len(bad3), "failures": bad3[:50],
                  "buys_total": int(sum(r["redundancy"].get("buys") or 0 for r in exp)),
                  "no_site_total": int(sum(r["redundancy"].get("no_site") or 0 for r in exp)),
                  "n_runs_exposed_none_placed": sum(1 for r in exp if not (r["redundancy"].get("buys") or 0))}
    _placed(ch["E5-3"], ch["E5-3"]["buys_total"], ch["E5-3"]["no_site_total"],
            "no spare needed in the exposed runs" if exp else "no exposed A6-always2 run")
    if a2 and not exp:
        ch["E5-3"]["vacuous_note"] = "no A6-always2 run had an exposed replica: the check holds vacuously"
    # E5-4: Pareto gains (filled in by summary from the pareto block)
    ch["E5-4"] = {"status": "informative"}
    # E5-5: Sublet's certificates
    sub = [r for r in rows if r["tag"] == SUBLET_TAG]
    cc = m4.count_certificates(sub)
    fails = [_brief(r, ("level", "menu", "mu", "c", "certificate_case", "t_a")) for r in sub
             if r.get("certificate_case") in m4.PROVEN_CASES and (r.get("certificate") or {}).get("held") is not True]
    wc = [_brief(r, ("level", "menu", "mu", "c", "t_a")) for r in sub if r.get("certificate_case") == "W(c)"]
    unav = cc["by_case"]["unavailable"]["runs"]
    sub_lost = [x for x in lost if x["tag"] == SUBLET_TAG]
    ch["E5-5"] = {"status": ("pass" if not fails and unav == 0 and not sub_lost else "fail") if sub or sub_lost
                  else "missing", "runs": cc["n"], "held": cc["held"], "by_case": cc["by_case"],
                  "n_failures": len(fails), "failures": fails[:50], "n_w_c": len(wc), "w_c_runs": wc[:50],
                  "unavailable": unav, "n_runs_lost": _n_lost(sub_lost), "lost": sub_lost[:20],
                  "B0_rules": _count(r.get("B0_rule") for r in sub)}
    # E5-6: A6-rule's spares against the rule's prediction, per (level, menu) over every mu of the point and per mu
    thr = redundancy_threshold()
    t = thr["n_exp_threshold"]
    rule = [r for r in rows if r["tag"] == "A6-rule"]
    note = "no A6-rule run at this point in the outputs"
    by: dict = {}
    for level in LEVELS:
        for menu in MENUS:
            here = [r for r in rule if (r["level"], r["menu"]) == (level, menu)]
            mus = sorted(mu for lv, mn, mu in points() if (lv, mn) == (level, menu))
            e = _spare_counts(here, t, note)
            e["by_mu"] = {num_key(mu): _spare_counts([r for r in here if float(r["mu"]) == float(mu)], t, note)
                          for mu in mus}
            by.setdefault(level, {})[menu] = e
    ch["E5-6"] = {"status": "informative", "by_level_menu": by, "threshold": thr,
                  "prediction": "spares only where a pool has more than n_exp_threshold exposed replicas (at alpha "
                                "and lambda of a5b's spare_threshold); counts per run of buys > 0 against "
                                "n_exp_max above or below that threshold, n_exp_max being the largest number of "
                                "exposed replicas in one slot summed over the run's groups (RedundancyRule.n_exp), "
                                "an upper bound on any one pool's count"}
    return ch


def _tag_rows(data: dict) -> dict:
    """(level, menu, mu key, tag) -> run rows (each with the job's keys and instance record)."""
    out: dict = {}
    for d in data.values():
        for r in d["runs"]:
            row = {**r, "job": d["job"], "level": d["level"], "menu": d["menu"], "tag": d["tag"], "mu": d["mu"],
                   "c": d["c"], "bl0a_usd": d["bl0a_usd"], "instance": d["instance"]}
            out.setdefault((d["level"], d["menu"], num_key(d["mu"]), d["tag"]), []).append(row)
    return out


def summary(out) -> dict:
    out = Path(out)
    S = settings()
    js = jobs()
    recs = mc.read_records(out)
    ok = {j.id for j in js if (recs.get(j.id) or {}).get("status") == "ok"}
    data, ignored = {}, []
    for j in js:
        path = run_path(out, j.id)
        if j.id not in ok:
            if path.is_file():
                ignored.append({"job": j.id, "status": (recs.get(j.id) or {}).get("status"),
                                "output": str(path.relative_to(out))})
            continue
        d = mc.read_json(path)
        if d is not None:
            data[j.id] = d
    by = _tag_rows(data)
    all_rows = [r for rs in by.values() for r in rs]
    lost = lost_runs(data)
    n_cell = len(S["alignments"]) * len(S["policy_seeds"])
    cells: dict = {}
    for level, menu, mu in points():
        for tag in TAGS:
            cells.setdefault(level, {}).setdefault(menu, {}).setdefault(num_key(mu), {})[tag] = \
                cell_entry(by.get((level, menu, num_key(mu), tag), []), tag, n_expected=n_cell)
    mu1 = num_key(MU_MAIN)

    def expo(level, menu, mk, tag):
        insts = [d["instance"] for d in data.values() if (d["level"], d["menu"], num_key(d["mu"]), d["tag"])
                 == (level, menu, mk, tag)]
        return exposure_entry(by.get((level, menu, mk, tag), []), insts)

    exposure: dict = {}
    pareto: dict = {}
    for level in LEVELS:
        for menu in MENUS:
            others = sorted(mu for lv, mn, mu in points() if (lv, mn) == (level, menu) and mu != MU_MAIN)
            for tag in A6_TAGS:
                e = expo(level, menu, mu1, tag)
                if others:
                    e["by_mu"] = {num_key(mu): expo(level, menu, num_key(mu), tag) for mu in others}
                exposure.setdefault(level, {}).setdefault(menu, {})[tag] = e
            p = pareto_entry(cells[level][menu][mu1], menu)
            p["a6_modes_identical"] = a6_identical({t: by.get((level, menu, mu1, t), []) for t in A6_TAGS})
            pareto.setdefault(level, {})[menu] = p
    checks = build_checks(all_rows, lost)
    gains = {lv: {mn: pareto[lv][mn]["bl3_pareto"] for mn in MENUS} for lv in LEVELS}
    ch4 = {"status": "informative", "by_level_menu": gains,
           "long_menu": {lv: gains[lv]["long"] for lv in LEVELS},
           "short_menu": {lv: gains[lv]["short"] for lv in LEVELS},
           "n_cells_with_gain": sum(1 for lv in LEVELS for mn in MENUS if gains[lv][mn]),
           "n_cells_undecided": sum(1 for lv in LEVELS for mn in MENUS if pareto[lv][mn]["bl3_undecided"]),
           "n_cells_a6_identical": sum(1 for lv in LEVELS for mn in MENUS
                                       if pareto[lv][mn]["a6_modes_identical"]["all_identical"] is True),
           "a6_identical_rule": "cells (level, menu) at mu = 1 where the three A6 modes gave the same run for every "
                                "(alignment, policy seed): there E5-4 compares BL3 with one A6 policy",
           "where": "pareto.<level>.<menu>"}
    checks["E5-4"] = ch4
    checks = {k: {"status": v.pop("status"), "claim": CHECK_CLAIMS[k], **v} for k, v in
              sorted(checks.items(), key=lambda kv: int(kv[0].split("-")[1]))}
    sub = [r for r in all_rows if r["tag"] == SUBLET_TAG]
    cc = m4.count_certificates(sub)
    cc["failure_runs"] = checks["E5-5"]["failures"]
    cc["w_c_runs"] = checks["E5-5"]["w_c_runs"]
    put(cc, "abort_share", sum(1 for r in sub if r.get("aborted")) / len(sub) if sub else None, "no Sublet run")
    cc["B0_rules"] = _count(r.get("B0_rule") for r in sub)
    # meta.instances: one record per (menu, mu, alignment) (the level does not change the instance)
    by_menu: dict = {}
    hashes: dict = {}
    refs: dict = {}
    for d in sorted(data.values(), key=lambda x: x["job"]):
        key = (d["menu"], num_key(d["mu"]), num_key(d["c"]))
        hashes.setdefault(key, set()).add(d["instance"]["instance_hash"])
        tgt = by_menu.setdefault(d["menu"], {}).setdefault(key[1], {})
        if key[2] not in tgt:
            i = d["instance"]
            tgt[key[2]] = {"bl0a_usd": d["bl0a_usd"], "bl0a_own_demand": d["bl0a_own_demand"],
                           "demand_sha256": d["demand_sha256"], "own_demand_sha256": d["own_demand_sha256"],
                           **{k: i[k] for k in ("instance_hash", "n_sites", "n_sites_by_kind", "n_contracts",
                                                "contracts", "n_lenders_with_sites", "lam_s", "lam_s_max_ok")}}
        if d["menu"] == DEMAND_MENU:
            refs.setdefault(key[1], {}).setdefault(key[2], d["references"])
    for (menu, mk, ck), hs in hashes.items():
        by_menu[menu][mk][ck]["instance_hashes_found"] = len(hs)
    rel = []
    for mk in {k for v in by_menu.values() for k in v}:
        for ck in {c for v in by_menu.values() for c in v.get(mk, {})}:
            b = [v[mk][ck]["bl0a_usd"] for v in by_menu.values() if ck in v.get(mk, {})]
            if len(b) > 1 and min(b) > 0:
                rel.append(max(b) / min(b) - 1.0)
    instances = {"demand_menu": DEMAND_MENU, "by_menu": by_menu, "max_rel_diff_bl0a": max(rel) if rel else None,
                 "note": "each menu's instance is built from its own contracts (a lender's lendable supply uses the "
                         "longest window of its menu) and takes the demand and borrower_stats of the short menu's "
                         "instance at the same mu and alignment (M15), so the menus differ only in contracts and "
                         "lendable supply and have one BL0a per (mu, alignment); bl0a_own_demand is BL0a on the demand "
                         "the builder gives the menu's own instance; the correlation level does not change the "
                         "instance"}
    if not rel:
        instances["max_rel_diff_bl0a_note"] = "fewer than two menus with runs at one (mu, alignment)"
    meta = {"exp": EXP, "spec": SPEC, "git_revision": mc.git_revision(), "versions": mc.versions(),
            "written": mc._now(), "reduced": S["reduced"], "config": f"configs/{CONFIG}",
            "horizon_min": S["horizon_min"],
            "grid": {"levels": list(LEVELS), "menus": list(MENUS), "mus": [MU_MAIN, *MUS_SWEEP],
                     "mu_main": MU_MAIN, "mu_sweep": list(MUS_SWEEP), "default_point": list(DEFAULT_POINT),
                     "alignments": list(S["alignments"]), "alignments_design": list(ALIGNMENTS),
                     "policy_seeds": list(S["policy_seeds"]), "policy_seeds_design": list(POLICY_SEEDS)},
            "levels": {lv: level_lender_model(lv) for lv in LEVELS},
            "menus": {mn: {"contracts": menu_contracts(mn), "class": MENU_CLASS[mn], "a11_classes": menu_classes(mn)}
                      for mn in MENUS},
            "tags": {t: {"policy_id": v[0], "params": v[1] if v[1] is not None else
                         {"inner": SUBLET_INNER, "gamma": m4.GAMMA, "kappa": None, "B0": m4.B0_RULE,
                          "rule": "ms4_common.sublet_params of each job's instance (M36)"},
                         "style_key": v[2]} for t, v in TAGS.items()},
            "B0_share": m4.B0_SHARE, "B0_rule": m4.B0_RULE, "info_class_reported": {SUBLET_TAG: m4.INFO_CLASS_REPORTED},
            "accounting": "overflow (cost over BL0a, M2); every cost entry also in total accounting",
            "references": refs, "instances": instances, "redundancy_threshold": redundancy_threshold(),
            "jobs_ok": len(ok), "jobs_missing": [j.id for j in js if j.id not in ok],
            "ignored_outputs": ignored,
            "run_errors": {"n_runs_expected": len(all_rows) + _n_lost(lost), "n_runs": len(all_rows),
                           "n_runs_lost": _n_lost(lost), "jobs": lost}}
    if not refs:
        meta["references_note"] = "no short-menu run in the outputs"
    if S["reduced"]:
        meta["reduced_note"] = (f"reduced job list ({REDUCED_ENV}=1): alignment {list(REDUCED['alignments'])}, policy "
                                f"seed {list(REDUCED['policy_seeds'])}, a {REDUCED['horizon_min']}-min horizon; not a "
                                "result")
    summ = {"meta": meta, "cells": cells, "exposure": exposure, "pareto": pareto, "certificates": cc,
            "checks": checks}
    mc.dump_json(summ, out / "summary.json")
    mc.write_text(tables(summ), out / "tables.md")
    return summ


def tables(s: dict) -> str:
    L = ["# E5: redundancy under correlated reclaims (design/sim_spec_ms4.md §5)", ""]
    if s["meta"].get("reduced"):
        L += [f"*{s['meta']['reduced_note']}*", ""]
    mu1 = num_key(MU_MAIN)
    for menu in MENUS:
        L.append(f"## Cost / BL0a (overflow accounting) and fallback share after reclaims, {menu} menu, mu = 1 "
                 "(medians [95% CI of the cost])")
        L.append("")
        rows = []
        for level in LEVELS:
            for tag in TAGS:
                e = s["cells"][level][menu][mu1][tag]
                co, fr = e["cost_over_bl0a"], e["fallback_share_after_reclaims"]
                rows.append([level, tag, e["n_runs"], co["median"], co["median_ci95"][0], co["median_ci95"][1],
                             fr["median"], fr["n_null"], e["n_leases"]["median"], e["n_leases_reclaimed"]["median"],
                             e["gpu_hours"]["median"]])
        L.append(mc.md_table(["level", "tag", "runs", "cost / BL0a", "ci lo", "ci hi", "fallback after reclaims",
                              "runs without a drop", "leases", "reclaimed", "GPU-hours"], rows))
    L.append(f"## Default point ({DEFAULT_POINT[0]}, {DEFAULT_POINT[1]} menu): cost / BL0a against mu")
    L.append("")
    rows = []
    dp = s["cells"][DEFAULT_POINT[0]][DEFAULT_POINT[1]]
    for tag in TAGS:
        rows.append([tag] + [dp[num_key(mu)][tag]["cost_over_bl0a"]["median"]
                             for mu in (MUS_SWEEP[0], MUS_SWEEP[1], MU_MAIN, MUS_SWEEP[2])])
    L.append(mc.md_table(["tag", "mu 0.2", "mu 0.5", "mu 1", "mu 2"], rows))
    L.append("## Exposure (A6; mu = 1 and the default point's other mu; placed: buys / (buys + no site))")
    L.append("")
    rows = []
    for lv, a in s["exposure"].items():
        for mn, b in a.items():
            for t, e in b.items():
                for mk, x in [(mu1, e)] + sorted((e.get("by_mu") or {}).items(), key=lambda kv: float(kv[0])):
                    rows.append([lv, mn, mk, t, x["n_runs"], x["n_runs_exposed"], x["n_runs_with_buys"],
                                 x["buys_total"], x["no_site_total"], x["placed_share"], x["n_exp_max"],
                                 x["lam_s_max_ok"]])
    L.append(mc.md_table(["level", "menu", "mu", "tag", "runs", "exposed", "with buys", "buys", "no site", "placed",
                          "n_exp max", "lam_s <= 3600"], rows))
    e6 = s["checks"]["E5-6"]
    L.append(f"## A6-rule's spares against the rule's threshold (E5-6: n_exp_max above "
             f"{e6['threshold']['n_exp_threshold']:.4g} or at most it)")
    L.append("")
    rows = [[lv, mn, mk, x["n_runs"], x["n_with_buys"], x["n_exp_max"]["max"], x["bought_above"], x["bought_below"],
             x["not_bought_above"], x["not_bought_below"]]
            for lv, a in e6["by_level_menu"].items() for mn, b in a.items() for mk, x in b["by_mu"].items()]
    L.append(mc.md_table(["level", "menu", "mu", "runs", "with buys", "n_exp max", "bought above", "bought below",
                          "not bought above", "not bought below"], rows))
    L.append("## Pareto gains of BL3 over every A6 mode (E5-4, mu = 1)")
    L.append("")
    L.append(mc.md_table(["level", "menu", "BL3 tags", "undecided", "A6 modes identical (pairs)"],
                         [[lv, mn, ", ".join(p["bl3_pareto"]) or "none", ", ".join(p["bl3_undecided"]) or "–",
                           f"{p['a6_modes_identical']['n_identical']} of {p['a6_modes_identical']['n_pairs']}"]
                          for lv, a in s["pareto"].items() for mn, p in a.items()]))
    c = s["certificates"]
    L.append("## Certificates (Sublet, Theorem W)")
    L.append("")
    L.append(mc.md_table(["case", "runs", "held"], [[k, v["runs"], v["held"]] for k, v in c["by_case"].items()]))
    L.append(f"abort share {c.get('abort_share')}; B0 rules {c['B0_rules']}")
    L.append("")
    L.append("## Checks (§5.7)")
    L.append("")
    L.append(mc.md_table(["check", "status"], [[k, v["status"]] for k, v in s["checks"].items()]))
    re = s["meta"]["run_errors"]
    L.append(f"runs {re['n_runs']} of {re['n_runs_expected']} in the ok jobs; lost to an error {re['n_runs_lost']}")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=argv, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
