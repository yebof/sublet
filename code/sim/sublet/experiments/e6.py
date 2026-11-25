"""E6: contract menu and protection (design/sim_spec_ms3.md §7; deliverable D26; open choices M26-M31, with M19's
four time alignments).

E6(a), when protection pays (§7.1; Fig. 7(c), supplement). E2's 220 cells, series, layers and alignments (four at
mu / beta~ = 1, one at the other mu values, M19), schedule `trace`, with the protected price per (lender, H, row r)
a_p = r a_lk (`prices.a_protected_usd_per_gpu_h`, a_lk the cell's revocable IR price), rows r = alpha_p / alpha in
ROWS (the design's six plus 1.65, 1.7, 1.75, M26), and lambda' in {a5, 0}: a5 = a5_2GBps at the protected site; 0 =
the protected site with load_scenario 'explicit', lam_s 0, the revocable site keeping a5_2GBps (M27).
Evaluation without a run per row (M28): A1's plan is (i) cold, not insured = BL7's plan, (ii) insured (INS = A1
{insure: always}) or (iii) warm, not insured (WARM = A1 {reaction: prewarm_if_feasible, insure: never}); INS and
WARM run once per (cell, series, layer with a band, lambda', alignment) at the reference row r = 1.1 and mu / beta~ =
1, and their cost at row r and mu is A + a_p(r) G + mu_fb(mu) W, with G = sum(prepaid_usd + rent_usd) / a_p(1.1) over
the protected leases of RunResult.leases (billed GPU-hours, loading included), W = components.stranding_fb /
mu_fb(1) and A the rest (the config sets kv_share, mu_fl and pi to 0, so stranding is stranding_fb only); mu_fb(mu) =
mu beta~_ref. BL7's cost is that of E2's run of the same key whose plan is cold and not insured (E2's rule `cold`,
which is A1 where A1 reacts cold); where E2's A1 insures (at the default protected price), BL7 {inner A1, site_rev}
runs itself at that mu. A1's decision per (cell, row, mu, lambda') is computed once, at alignment 1, with c2rule on
the PublicView of the instance at that row's price, that mu and that lambda' (c2_units with rep_site the protected
site, insure_up_front(units, 'lb_react'), the C2-SW reaction c2_thresholds(..., bw)): 'ins' if it insures, else
'warm' if the reaction is warm, else 'cold'; the summary applies the mu = 1 decisions to the alignments 2-4.
Heatmap value (M29): per (group, lambda', mu, H, r) the median over the group's (lender, series) pairs (at mu = 1
the (lender, series, alignment) triples) of sum_k cost_BL7 / sum_k cost_A1 over the layers with a band.
Boundary (M30): r*(H) = the largest r in [2 - alpha, 2.5] with r < LB_react(H; alpha, alpha_p = r alpha, mu,
lambda), by bisection to 1e-3 (r* = 2 - alpha if none, 2.5 if every r qualifies), with the certified bound
necessity_lb.lb_all(dict(b=1, a=alpha, ap=r alpha, mu=mu, lam=lambda, rrl=False), H, include_insure=False)[0]
(C2-T3 PROVEN, switch cost beta, tau = 0) through paths.import_c2 (C11), and r*_grid with the grid value
families.lb_react (A1's test; a grid value, not certified); alpha = the median alpha_k of e2_reactions.json at the
contract s5_tau5_H<H> over the 20 MaaS clusters (maas) or over the pools with an A1 cell at H (spot, only where at
least two pools have one, M23), lambda = 1 / (alpha + phi) at a5 and 0 at lambda' = 0, H in C2 units H_min 60 /
(lambda_s (alpha + phi)) (phi, lambda_s from e2_reactions.json meta.setting).
E6-1 (§7.1): part (a) the harness's INS worst ratio (repro_c2sw_scan.grid_worst with c2rule.ins_plan, as
test_c2_harness.py::_ins_and_rrl) at mu = 1, lambda = inputs.lambda_default of por_default.json, for each row with
alpha_p = r alpha < 1 and each H_BASE point (Hs / beta_s beta~ units), within [CR_ins (1 - 1e-3), CR_ins + 1e-9],
CR_ins = max(2 - alpha, alpha_p / alpha); part (b) at each (row, H, mu, lambda') of (a), mu in the mu grid and
lambda' in {a5, 0}, c2rule.insure_up_front(units, 'lb_react') against "alpha_p <= alpha (2 - alpha) or CR_ins < LB"
with LB = families.lb_react(model.Params(...))[0] called directly, and A1 built at each row's protected price on a
one-day E2 instance (E6_1_LENDER, E6_1_SERIES, H in E6_1_A1_H) reports `insured` equal to that formula at A1's own
units.

E6(b), menus of growing richness (§7.2, M31; supplement). configs/bench_e7r.json, one week of 1-min routing, A6 {}
(practical), cumulative menus R (s5_tau5_H2, s5_tau5_H60, no protected sites), R+P (plus protected), R+P+1h (plus
s5_tau60_H0, s5_tau60_H60), R+P+1h+H (plus s5_tau5_H5, H15, H30, H120, H240), IR prices from the builder; 4
alignments (config seeds 1-4, lender seed = config seed) x 3 policy seeds (0-2) per menu at mu = 1 and mu / beta~ in
{0.2, 0.5, 2} at R+P. BL0a (analytic: sum over clients of q_j x demand) is the reference. Every menu's instance has
the demand of menu R's instance at the same alignment (e6b_instance; M31),
so that the menus differ only in their contracts and lendable supply: the builder scales the series
demand to the lendable supply, which depends on the longest window of the menu (R+P+1h+H's 245-min window gives its
own instance less demand), and E6(b) replaces clients.demand and borrower_stats of the other menus' instances by
menu R's (instance.with_demand; the client lists are identical).

Status labels (copied from design/sim_spec_ms3.md §7.1, never upgraded): C2-T2 PROVEN for insurance held to the end
of the demand (insuring up front has ratio exactly CR_ins = max(2 - alpha, alpha_p / alpha) and is the right
worst-case choice iff alpha_p / alpha < CR_react(H)); C2-T3 PROVEN for tau = 0 (LB_react(H) <= CR_react(H)); C2-P7
lower bound PROVEN, equality VERIFIED NUMERICALLY; C3-P5 PROVEN.

Command line (ms3_common.main, §2.4), run from code/sim:
  python -m sublet.experiments.e6 --list | --job ID | --summary | --estimate | --manifest  [--out DIR]
E6_PART (environment): 'a', 'b' or unset (both) selects the jobs that --list prints and the parts --summary builds.
run_e6.sh [--reduced] [a] [b] runs part a with E6_PART=a and --out out/e6/a (only once out/e2/summary.json exists) and
part b with E6_PART=b and --out out/e6/b, so the job records are under e6/a/jobs/ and e6/b/jobs/; a part's files are
written to <out> if its name is the part's letter, else to <out>/<letter>.
Jobs (lender ids written with '.' for ':', as in e2.py):
  e6:a:lender=<L>:H=<H>:c=<C>            pool  E6(a) of one cell and alignment: the INS and WARM runs at both
                                               lambda', the BL7 costs (E2's runs, or BL7 runs where E2's A1
                                               insures), at c = 1 the decisions of every (row, mu, lambda') and the
                                               reruns of E6-2 and E6-3; it reads E2's run files (run run_e2.sh first)
  e6:a_boundary:mu=<U>:lam=<a5|0>:group=<maas|spot>   pool  the boundary r*(H) of one (mu, lambda', group)
  e6:a_c2t2                              pool  E6-1 (a) and (b)
  e6:b:menu=<R|R+P|R+P+1h|R+P+1h+H>:mu=<U>:c=<C>     pool  E6(b): the 3 policy seeds of one (menu, mu, alignment)
(§7.1 writes the boundary jobs as e6:a:boundary:mu=..., which ms3_common.parse_job_id rejects: every part after the
second needs '='; and §7.1 names no job for E6-1, whose inputs the claims report needs, so it runs as e6:a_c2t2.)
--estimate uses the constants of §11.1: 1.8 s per INS, WARM or BL7 run, 3.19 s per A1 decision outside the first
clause (one families.lb_react call; also per lb_react call and per INS worst-ratio grid of E6-1); per boundary bisection
step the certified bound at the measured times (0.51 s up to H = 14.3 beta~, 4.4, 15.8 and 64.7 s up to 28.6, 57.2 and
above) plus 2.5 s for the grid value, 11 steps per H; 3 x 47.3 s per E6(b) week run (the bound of §7.2).

Reduced runs (smoke tests): MS3_E6_REDUCED=1 (run_e6.sh --reduced sets it) sets MS3_E2_REDUCED=1 in its own process,
so that E6(a) uses E2's reduced cells, series, horizon and alignments (and reads the reduced E2 runs), runs the
boundary at mu = 1 only on the reduced H grid, E6-1 on rows {1.5, 2}, H_BASE points {0, 0.5}, mu = 1, A1 at H = 0, and
E6(b) for one day with config seed 1 and policy seed 0, every menu at mu = 1 and R+P at the other mu values; selected
keys of E6-2 and E6-3 every 10th and every 3rd key of the reduced lists. Default (unset or 0): the full lists.

Outputs (§7.1, §7.2): code/sim/out/e6/a/: runs/cells/<job>.json, runs/boundary/<job>.json, runs/c2t2.json (not
versioned), jobs/, logs/, manifest.json, run_e6.log, heatmap.json, boundary.json, summary.json, tables.md;
code/sim/out/e6/b/: runs/<job>.json, jobs/, logs/, manifest.json, run_e6.log, summary.json, tables.md. Numeric keys
as §2.4 ("1.1", "1", "60"); missing values null with a "*_note" key (§2.6).

heatmap.json (<group> in {maas, spot}, <lam'> in {a5, 0}, <mu> the mu grid, <H> minutes, <r> the rows):
  meta                               rows, H grid, mu grid, groups, alignments, sources, notes, git_revision
  cells.<group>.<lam'>.<mu>.<H>.<r>  value (median over the pairs or triples of sum_k BL7 / sum_k A1), ci95 (the
                                     percentile bootstrap of the median, metrics.aggregate, B = 2000, seed 0), p95,
                                     n_pairs, n_alignments, alignments, n_lenders, share_insured (share of the pairs
                                     where A1 insures), kind_counts {ins, warm, cold} (A1's plan over the pairs),
                                     react_over_ins {median, ci95} (sum_k cost of A1's reaction plan, WARM if its
                                     reaction is warm else BL7, over sum_k INS: above 1 where insuring pays on the
                                     traces, E6-5); every field null with its '*_note', and `note`, where no pair
                                     exists (spot: fewer than two pools, M23)
boundary.json:
  meta                               the inputs, the bound and its status, git_revision
  rows.<mu>.<lam'>.<group>           parallel lists over the H with a value (columns): H, H_min, H_c2, alpha, lam_c2,
                                     r_star, r_star_grid, diff (r_star_grid - r_star), lb_at_r_star (certified bound at
                                     r_star alpha), lb_grid_at_r_star_grid, calls, calls_grid, note, seconds; and
                                     H_skipped [{H, note}] (spot: fewer than two pools with an A1 cell, M23); null
                                     with `<group>_note` for a listed boundary job without an 'ok' output
e6/a/summary.json:
  meta                               settings, cells, groups, status labels, sources, jobs_ok, jobs_missing
  decisions.<lender>.<H>             {<r>: {<mu>: {<lam'>: plan ('ins' | 'warm' | 'cold')}}} of alignment 1
  decision_counts.<lam'>.<mu>.<r>    {ins, warm, cold, first_clause} over the cells
  checks.<id>                        one entry per check of §7.3, keyed by its id (E6-1 ... E6-5 here, E6-6 in
                                     e6/b), each with `status` ('pass', 'fail', 'missing' (no input to check) or
                                     'informative'; the vocabulary of the E1 and E10 summaries) and `claim` (the
                                     content of §7.3 with its status labels):
  checks.E6-1                        a {n, n_fail, rows [{r, Hs, H, w_ins, CR_ins, ok}]}, b {n, n_fail, rows,
                                     a1 {n, n_fail, rows}}, pass; or pass null with a note if e6:a_c2t2 did not run
  checks.E6-2                        reruns [{key, lam, plan, r, mu, predicted, total, rel, plan_equal}], n, n_fail,
                                     units_across_alignments {n, n_fail, failures}, pass (1e-9 relative)
  checks.E6-3                        rows [{key, bl7, e2_cold, abs_diff}], n, n_fail, pass (1e-9 USD)
  checks.E6-4                        n_pairs (pairs whose plan is cold in every layer), max_abs_dev (|value - 1|),
                                     pass (exactly 1)
  checks.E6-5                        disagreements [{group, lam, mu, H, r, r_star, react_over_ins, insure_pays,
                                     boundary_insures}], n_cells, n_disagree (informative)
e6/b/summary.json:
  meta                               menus (contract lists), policy, seeds, horizon, sources, jobs_ok, jobs_missing,
                                     instances {demand_menu ('R'), by_menu.<menu>.<c> {bl0a, bl0a_own_demand,
                                     demand_load_h, demand_sha256, n_sites, n_contracts} at mu = 1,
                                     max_rel_diff_bl0a (largest max/min - 1 of BL0a over the menus at one alignment;
                                     0, every menu having menu R's demand), note}; bl0a_own_demand is BL0a on the
                                     demand the builder gives the menu's own instance (scaled to its lendable supply,
                                     so lower for a menu with a longer longest window), for the record
  menus.<menu>.<mu>                  cost_over_bl0a {median, median_ci95, p95, max, n, mean, mean_ci95} over the runs,
                                     cost_R_over_cost {median, median_ci95, ..., n} over the runs paired by
                                     (alignment, policy seed) (mu = 1; null with a note elsewhere),
                                     cost_R_over_cost_bl0a (the same pairs, each cost over its run's BL0a),
                                     gpu_hour_share {<class>: share} (the runs' GPU-hours per contract class, summed,
                                     over their sum), components_over_bl0a {<component>: mean over the runs}, n_runs,
                                     alignments, policy_seeds, bl0a_by_alignment {<c>: USD}; a listed (menu, mu)
                                     without runs has `note`, n_runs 0 and every field null with its '*_note'
  checks.E6-6                        status, claim, n_runs, n_invariant_failures, n_gpu_only_lease_slots, pass
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import dataclasses
import hashlib
import math
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

from .. import paths
from . import e2
from . import ms3_common as mc

EXP = "e6"
SPEC = "design/sim_spec_ms3.md §7"
ROWS = (1.1, 1.25, 1.5, 1.65, 1.7, 1.75, 2.0, 2.5, 3.0)     # M26: the design's six plus 1.65, 1.7, 1.75
R_REF = 1.1                       # the reference row of the INS and WARM runs (§7.1)
LAMS = ("a5", "0")                # lambda' (M27)
PLANS = ("ins", "warm")
E62_EVERY, E63_EVERY = 100, 10    # E6-2: every 100th (cell, series, layer) key; E6-3: every 10th MaaS key
E62_RERUNS = ((3.0, 1.0, ("ins", "warm")), (1.1, 2.0, ("warm",)))   # (r, mu, plans) of E6-2
R_HI, R_TOL = 2.5, 1e-3           # M30: the boundary's interval end and bisection tolerance
REL_TOL = 1e-9
E6_1_LENDER, E6_1_SERIES, E6_1_A1_H = "a2:c00", "azure2024_conv", (0, 2)
E6B_CONFIG = "bench_e7r.json"
E6B_POLICY_SEEDS = (0, 1, 2)
E6B_DEFAULT_MENU = "R+P"
E6B_DEMAND_MENU = "R"             # M31: every menu runs on the demand of menu R's instance (e6b_instance)


def _c(id_: str, tau: int, H: int) -> dict:
    return {"id": id_, "tau_min": tau, "H_min": H}


_R = [_c("s5_tau5_H2", 5, 2), _c("s5_tau5_H60", 5, 60)]
_1H = [_c("s5_tau60_H0", 60, 0), _c("s5_tau60_H60", 60, 60)]
_HX = [_c(f"s5_tau5_H{h}", 5, h) for h in (5, 15, 30, 120, 240)]
MENUS = {"R": (_R, False), "R+P": (_R, True), "R+P+1h": (_R + _1H, True), "R+P+1h+H": (_R + _1H + _HX, True)}
# §11.1 time constants
EST_RUN_S = 1.8
EST_DECISION_S = 3.19
EST_CERT_S = ((14.3, 0.51), (28.6, 4.4), (57.2, 15.8), (math.inf, 64.7))
EST_GRID_S = 2.5
EST_STEPS = 11
EST_E6B_RUN_S = 3 * 47.3
REDUCED = {"boundary_mu": (1.0,), "e6_1_rows": (1.5, 2.0), "e6_1_hs": (0.0, 0.5), "e6_1_mus": (1.0,),
           "e6_1_a1_H": (0,), "e6b_horizon_min": 1440, "e6b_alignments": (1,), "e6b_policy_seeds": (0,),
           "e62_every": 10, "e63_every": 3}
STATUS_LABELS = {
    "C2-T2": "PROVEN for insurance held to the end of the demand",
    "C2-T3": "PROVEN for tau = 0 (LB_react(H) <= CR_react(H))",
    "C2-P7": "lower bound PROVEN, equality VERIFIED NUMERICALLY",
    "C3-P5": "PROVEN",
    "families.lb_react": "a grid value, not certified (MS2 spec M21)",
    "necessity_lb.lb_all": "certified lower bound on CR_react (interval method; C2-T3 PROVEN)"}
# summary checks.<id>.claim: the content of §7.3 with the status labels of §7.1 (copied, never upgraded)
CHECK_CLAIMS = {
    "E6-1": "C2-T2 (PROVEN for insurance held to the end of the demand): (a) the harness's INS worst ratio lies in "
            "[CR_ins (1 - 1e-3), CR_ins + 1e-9], CR_ins = max(2 - alpha, alpha_p / alpha); (b) c2rule.insure_up_front"
            "(units, 'lb_react') equals the direct formula with families.lb_react, and A1 built at the row's "
            "protected price reports the same `insured` (exact)",
    "E6-2": "linearity in a_p and in mu (M28): INS and WARM rerun at r = 3, mu / beta~ = 1 and WARM at r = 1.1, "
            "mu / beta~ = 2 give A + a_p G + mu_fb W with the reference run's plan; A1's C2 units at c in {2, 3, 4} "
            "equal those at c = 1 (1e-9 relative)",
    "E6-3": "BL7 equals E2's cold, non-insured run of the same key (alignment 1, mu = 1, every 10th MaaS key; "
            "1e-9 USD)",
    "E6-4": "where A1 neither insures nor pre-warms, the cell value is exactly 1",
    "E6-5": "the cells where insuring pays on the traces (react_over_ins above 1) and the boundary r < r*(H) "
            "(certified LB_react, C2-T3 PROVEN for tau = 0) disagree (informative)",
    "E6-6": "E6(b) runs: no invariant failure, no GPU-only lease slot"}


# ---------------------------------------------------------------- settings
def reduced() -> bool:
    return os.environ.get("MS3_E6_REDUCED", "0") == "1"


def parts() -> list:
    v = os.environ.get("E6_PART", "")
    ps = [p for p in v.replace(",", " ").split() if p]
    bad = [p for p in ps if p not in ("a", "b")]
    if bad:
        raise ValueError(f"E6_PART must name the parts a and/or b, got {v!r}")
    return ps or ["a", "b"]


def part_dir(out, part: str) -> Path:
    o = Path(out)
    return o if o.name == part else o / part


def e2_out() -> Path:
    """E2's output folder (E6(a) reads its run files): <root>/out/e2."""
    return mc.out_dir("e2")


def num(x) -> str:
    return e2.num(x)


def mus() -> tuple:
    return e2.mu_grid()


def alignments_of(mu: float) -> tuple:
    return tuple(e2.settings()["alignments"]) if abs(mu - 1.0) <= 1e-12 else (1,)


def prot_overrides(a_p: Optional[float], lam: str) -> dict:
    """Overrides of the E2 base instance: the protected price (USD per GPU-hour) and lambda' (M27)."""
    ov = {}
    if a_p is not None:
        ov["prices.a_protected_usd_per_gpu_h"] = float(a_p)
    if lam == "0":
        ov.update({"lenders.1.load_scenario": "explicit", "lenders.1.lam_s": 0.0})
    elif lam != "a5":
        raise ValueError(f"lambda' must be 'a5' or '0', got {lam!r}")
    return ov


# ---------------------------------------------------------------- E6(a): one cell and alignment
def a_job_id(lender: str, H, c: int) -> str:
    return mc.job_id(EXP, "a", lender=e2.lender_key(lender), H=int(H), c=int(c))


def a_run_path(out_a, lender: str, H, c: int) -> Path:
    return Path(out_a) / "runs" / "cells" / mc.job_file_name(a_job_id(lender, H, c))


def e62_selected(lender: str, H, series: str, k: int) -> bool:
    """E6-2's keys: every 100th (cell, series, layer) key of alignment 1, keys ordered by the cells of
    e2.all_cells(), the series of e2.SERIES and the layers 1-8 (reduced runs: every 10th of the reduced lists)."""
    cl = list(e2.cells()) if reduced() else list(e2.all_cells())
    ser = list(e2.settings()["series"])
    i = (cl.index((lender, int(H))) * len(ser) + ser.index(series)) * e2.K_LAYERS + (k - 1)
    return i % (REDUCED["e62_every"] if reduced() else E62_EVERY) == 0


def e63_selected(lender: str, H, series: str, k: int) -> bool:
    """E6-3's keys: every 10th MaaS (cell, series, layer) key, in the order of e62_selected (reduced: every 3rd)."""
    if e2.group_of(lender) != "maas":
        return False
    cl = [x for x in (e2.cells() if reduced() else e2.all_cells()) if e2.group_of(x[0]) == "maas"]
    ser = list(e2.settings()["series"])
    i = (cl.index((lender, int(H))) * len(ser) + ser.index(series)) * e2.K_LAYERS + (k - 1)
    return i % (REDUCED["e63_every"] if reduced() else E63_EVERY) == 0


def plan_signature(res) -> list:
    """The lease records of a run without prices (E6-2)."""
    return [[L.site, L.contract, L.gpus, L.start_slot, L.start_min, L.prepaid_end_min, L.announce_slot, L.death_min,
             L.release_min, L.end_min, L.end_cause, L.tag] for L in res.leases]


def decompose(res, inst, a_p: float, mu_fb: float) -> dict:
    """{A, G, W, total} of a run (M28): G = billed protected GPU-hours = sum(prepaid_usd + rent_usd) / a_p over the
    protected leases, W = stranding_fb / mu_fb (stranded replica loads), A = total - a_p G - mu_fb W."""
    prot = {k for k, c in enumerate(inst.contracts) if c.protected}
    billed = float(sum(L.prepaid_usd + L.rent_usd for L in res.leases if L.contract in prot))
    G = billed / a_p
    W = float(res.components["stranding_fb"]) / mu_fb if mu_fb > 0 else 0.0
    total = float(res.components["total"])
    return {"A": total - a_p * G - mu_fb * W, "G": G, "W": W, "total": total}


def plan_cost(x: dict, a_p: float, mu_fb: float) -> float:
    return x["A"] + a_p * x["G"] + mu_fb * x["W"]


def c2rule_decision(inst, band: int, prot: int) -> dict:
    """A1's decision at the instance's own protected price, mu and lambda' (§7.1): c2_units on the PublicView
    (rep_site the protected site, switch c2sw), insure_up_front(units, 'lb_react') and the C2-SW reaction."""
    from ..algos import c2rule
    from ..instance import public_view
    view = public_view(inst, "I1")
    k_r = e2._rev_contract(inst, band)
    lp = c2rule.cheapest_protected(view, 0, [0], sites=[prot])
    if lp is None:
        raise ValueError(f"no protected contract at site {prot}")
    l_p, k_p = lp
    u = c2rule.c2_units(view, 0, band, k_r, l_prot=l_p, k_prot=k_p, rep_site=l_p, switch="c2sw")
    first = bool(u.ap <= u.alpha * (2 - u.alpha))
    insured = bool(c2rule.insure_up_front(u, "lb_react"))
    th = c2rule.c2_thresholds(u.alpha, u.ap, u.mu, u.lam, 1.0, u.bw)
    plan = "ins" if insured else ("warm" if th.react == "warm" else "cold")
    return {"plan": plan, "insured": insured, "reaction": th.react, "first_clause": first, "units": u.as_dict()}


def _e2_cold(e2d: dict, series: str, k: int) -> Optional[dict]:
    """E2's cold, non-insured run of a key under `trace` (rule cold, resolved), None if A1 insures there or the
    record is missing."""
    try:
        L = e2d["series"][series]["layers"][k - 1]
    except (KeyError, IndexError):
        return None
    rules = (L.get("trace") or {}).get("rules") or {}
    a = rules.get("a1")
    if a is None or a.get("insured"):
        return None
    x = e2._resolve(rules, "cold")
    if x is None or x.get("insured"):
        return None
    return x


def run_a_cell(job, outputs, out) -> dict:
    p = job.params
    lender, H, c = p["lender"], int(p["H"]), int(p["c"])
    out_a = part_dir(out, "a")
    S = e2.settings()
    job_mus = mus() if c == 1 else (1.0,)
    errors: list = []
    n_runs = 0
    # E2's run files of this cell and alignment
    e2d = {}
    for mu in job_mus:
        jid = e2.cell_job_id(lender, H, mu, c)
        rec = mc.read_record(e2_out(), jid)
        if not rec or rec.get("status") != "ok":
            raise RuntimeError(f"E2 job {jid} has no 'ok' record under {e2_out()} (run run_e2.sh first)")
        d = mc.read_json(e2.cell_run_path(e2_out(), lender, H, mu, c))
        if d is None:
            raise RuntimeError(f"E2 run file of {jid} is missing under {e2_out()}")
        e2d[mu] = d
    series_out, e62, e63 = {}, [], []
    a_k = bt_ref = None
    decisions: dict = {}
    for series in S["series"]:
        spec1 = e2.run_spec(lender, series, H, 1.0, c)
        inst1, model, ecfg = e2.build_base(spec1, c)
        if float((inst1.config.get("stranding") or {}).get("kv_share", 0.0)) != 0.0:
            raise ValueError("E6(a)'s linear evaluation needs stranding.kv_share = 0 (§7.1, M28)")
        lay, _ = e2.layers_of(inst1)
        bands, prot = e2.band_sites(inst1), e2.prot_site(inst1)
        if not bands:
            raise ValueError(f"{lender} at {e2.contract_id(H)} offers no band")
        b0 = min(bands)                                         # the lowest layer with a band
        a_k = float(inst1.price[bands[b0], e2._rev_contract(inst1, bands[b0])])
        bt_ref = float(inst1.stranding.mu_fb_usd[0])           # mu_fb at mu / beta~ = 1, i.e. beta~_ref
        a_ref = R_REF * a_k
        # the reference instances of the two lambda'
        inst_ref = {lam: e2.build_base(e2.run_spec(lender, series, H, 1.0, c, extra=prot_overrides(a_ref, lam)),
                                       c)[0] for lam in LAMS}
        layers = []
        for k in range(1, e2.K_LAYERS + 1):
            L = {"k": k, "bandless": k not in bands, "bl0a": e2.bl0a_usd(inst1, lay[k - 1])}
            if k not in bands:
                layers.append(L)
                continue
            band = bands[k]
            for plan in PLANS:
                L[plan] = {}
                for lam in LAMS:
                    ik = e2.single_band(inst_ref[lam], k, lay)
                    res = mc.try_run(errors, f"{series} layer {k} {plan} lam' {lam}", e2.simulate_rule, spec1, plan,
                                     band, prot, ik, model, ecfg, c)
                    if res is None:
                        continue
                    n_runs += 1
                    rr = e2.run_record(res)
                    x = decompose(res, ik, a_ref, bt_ref)
                    x.update(units=(e2.a1_report(res) or {}).get("units"), insured=rr["insured"],
                             reaction=rr["reaction"], invariant_failures=rr["invariant_failures"],
                             gpu_only_lease_slots=rr["gpu_only_lease_slots"])
                    L[plan][lam] = x
                    if c == 1 and e62_selected(lender, H, series, k):
                        sig = plan_signature(res)
                        for r, mu, plans in E62_RERUNS:
                            if plan not in plans:
                                continue
                            spec_r = e2.run_spec(lender, series, H, mu, c, extra=prot_overrides(r * a_k, lam))
                            ir = e2.single_band(e2.build_base(spec_r, c)[0], k, lay)
                            rx = mc.try_run(errors, f"E6-2 {series} {k} {plan} {lam} r {r} mu {mu}", e2.simulate_rule,
                                            spec_r, plan, band, prot, ir, model, ecfg, c)
                            if rx is None:
                                continue
                            n_runs += 1
                            pred = plan_cost(x, r * a_k, mu * bt_ref)
                            tot = float(rx.components["total"])
                            e62.append({"key": [lender, H, series, k], "lam": lam, "plan": plan, "r": r, "mu": mu,
                                        "predicted": pred, "total": tot, "rel": e2._rel_diff(tot, pred),
                                        "plan_equal": plan_signature(rx) == sig})
            # BL7 per mu: E2's cold, non-insured run, or BL7 itself where E2's A1 insures
            L["bl7"] = {}
            for mu in job_mus:
                x = _e2_cold(e2d[mu], series, k)
                if x is not None:
                    L["bl7"][num(mu)] = {"total": float(x["total"]), "source": "e2"}
                    continue
                spec_m = e2.run_spec(lender, series, H, mu, c)
                im = e2.single_band(e2.build_base(spec_m, c)[0], k, lay)
                res = mc.try_run(errors, f"{series} layer {k} bl7 mu {mu}", e2.simulate_rule, spec_m, "bl7", band, prot,
                                 im, model, ecfg, c)
                if res is None:
                    continue
                n_runs += 1
                rr = e2.run_record(res)
                L["bl7"][num(mu)] = {"total": rr["total"], "source": "run",
                                     "invariant_failures": rr["invariant_failures"],
                                     "gpu_only_lease_slots": rr["gpu_only_lease_slots"]}
            # E6-3: BL7 itself against E2's cold, non-insured run (alignment 1, mu = 1, every 10th MaaS key)
            if c == 1 and e63_selected(lender, H, series, k):
                x = _e2_cold(e2d[1.0], series, k)
                im = e2.single_band(inst1, k, lay)
                res = mc.try_run(errors, f"E6-3 {series} layer {k}", e2.simulate_rule, spec1, "bl7", band, prot, im,
                                 model, ecfg, c)
                if res is not None:
                    n_runs += 1
                    tot = float(res.components["total"])
                    e63.append({"key": [lender, H, series, k], "bl7": tot,
                                "e2_cold": None if x is None else float(x["total"]),
                                "abs_diff": None if x is None else abs(tot - float(x["total"])),
                                "note": None if x is not None else "E2's A1 insures here: no cold run to compare"})
            layers.append(L)
        series_out[series] = {"layers": layers, "a_k": a_k, "beta_tilde_ref": bt_ref, "n_bands": len(bands)}
        # A1's decisions per (row, mu, lambda'), alignment 1, on the first series' instance
        if c == 1 and not decisions:
            for r in ROWS:
                for mu in mus():
                    for lam in LAMS:
                        spec_d = e2.run_spec(lender, series, H, mu, c, extra=prot_overrides(r * a_k, lam))
                        idc = e2.single_band(e2.build_base(spec_d, c)[0], b0, lay)
                        d = mc.try_run(errors, f"decision r {r} mu {mu} lam' {lam}", c2rule_decision, idc,
                                       bands[b0], prot)
                        if d is not None:
                            decisions.setdefault(num(r), {}).setdefault(num(mu), {})[lam] = d
    data = {"meta": {"job": job.id, "exp": EXP, "spec": SPEC, "git_revision": mc.git_revision(),
                     "versions": mc.versions(), "e2_out": str(e2_out())},
            "cell": {"lender": lender, "group": e2.group_of(lender), "H": H, "c": c, "contract": e2.contract_id(H),
                     "a_k": a_k, "beta_tilde_ref": bt_ref, "r_ref": R_REF, "mus": list(job_mus)},
            "series": series_out, "decisions": decisions, "checks": {"E6_2": e62, "E6_3": e63}}
    outputs.dump(data, a_run_path(out_a, lender, H, c), compact=True)
    return {"runs": n_runs, "errors": errors, "a_k": a_k, "n_decisions": sum(len(v2) for v in decisions.values()
                                                                             for v2 in v.values()),
            "E6_2": {"n": len(e62), "n_fail": sum(1 for x in e62 if x["rel"] > REL_TOL or not x["plan_equal"])},
            "E6_3": {"n": len(e63), "n_fail": sum(1 for x in e63 if x["abs_diff"] is not None
                                                  and x["abs_diff"] > REL_TOL)}}


# ---------------------------------------------------------------- E6(a): the boundary (M30)
def boundary_job_id(mu, lam: str, group: str) -> str:
    return mc.job_id(EXP, "a_boundary", mu=num(mu), lam=lam, group=group)


@lru_cache(maxsize=None)
def setting() -> dict:
    return dict(e2.reactions()["meta"]["setting"])


def boundary_inputs(H: int, group: str) -> Optional[dict]:
    """alpha (median alpha_k at s5_tau5_H<H> over the group's lenders with an A1 cell; spot: None with fewer than two
    pools, M23), and H in C2 units."""
    lenders = e2.maas_lenders() if group == "maas" else tuple(e2.spot_pools_by_H().get(int(H), []))
    if group == "spot" and len(lenders) < 2:
        return None
    al = [e2.reaction_row(l, H, mus()[0])["alpha_k"] for l in lenders]
    if not al:
        return None
    a = float(np.median(al))
    s = setting()
    phi, lam_s = float(s["phi"]), float(s["lam_s"])
    return {"alpha": a, "H_c2": int(H) * 60.0 / (lam_s * (a + phi)), "phi": phi, "lambda_s": lam_s,
            "n_lenders": len(al)}


def lb_certified(alpha: float, ap: float, mu: float, lam: float, H: float) -> float:
    c2 = paths.import_c2()
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        return float(c2.necessity_lb.lb_all(dict(b=1.0, a=alpha, ap=ap, mu=mu, lam=lam, rrl=False), H,
                                            include_insure=False)[0])


def lb_grid(alpha: float, ap: float, mu: float, lam: float, H: float) -> float:
    c2 = paths.import_c2()
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        return float(c2.families.lb_react(c2.model.Params(mu=mu, alpha=alpha, ap=ap, H=H, lam=lam))[0])


def bisect_boundary(alpha: float, lb, r_hi: float = R_HI, tol: float = R_TOL) -> dict:
    """The largest r in [2 - alpha, r_hi] with r < lb(r) by bisection to `tol` (§7.1, M30): {r_star, lb_at_r_star,
    calls, note}; r_star = 2 - alpha if lb(2 - alpha) <= 2 - alpha, r_hi if r_hi < lb(r_hi)."""
    lo, hi = 2.0 - alpha, float(r_hi)
    v_lo = lb(lo)
    calls = 1
    if not lo < v_lo:
        return {"r_star": lo, "lb_at_r_star": v_lo, "calls": calls, "note": "no r qualifies: r* = 2 - alpha"}
    v_hi = lb(hi)
    calls += 1
    if hi < v_hi:
        return {"r_star": hi, "lb_at_r_star": v_hi, "calls": calls, "note": f"every r qualifies: r* = {hi:g}"}
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        v = lb(mid)
        calls += 1
        if mid < v:
            lo, v_lo = mid, v
        else:
            hi = mid
    return {"r_star": lo, "lb_at_r_star": v_lo, "calls": calls, "note": None}


def run_boundary(job, outputs, out) -> dict:
    p = job.params
    mu, lam, group = float(p["mu"]), p["lam"], p["group"]
    rows, skipped = [], []
    for H in boundary_H():
        bi = boundary_inputs(H, group)
        if bi is None:
            skipped.append({"H": int(H), "note": "fewer than two spot pools with an A1 cell (M23)"})
            continue
        a, Hc = bi["alpha"], bi["H_c2"]
        lam_c2 = 1.0 / (a + bi["phi"]) if lam == "a5" else 0.0
        t0 = time.perf_counter()
        cert = bisect_boundary(a, lambda r: lb_certified(a, r * a, mu, lam_c2, Hc))
        t1 = time.perf_counter()
        grid = bisect_boundary(a, lambda r: lb_grid(a, r * a, mu, lam_c2, Hc))
        rows.append({"H": int(H), "H_min": int(H), "H_c2": Hc, "alpha": a, "lam_c2": lam_c2,
                     "n_lenders": bi["n_lenders"],
                     "r_star": cert["r_star"], "lb_at_r_star": cert["lb_at_r_star"], "calls": cert["calls"],
                     "r_star_grid": grid["r_star"], "lb_grid_at_r_star_grid": grid["lb_at_r_star"],
                     "calls_grid": grid["calls"], "diff": grid["r_star"] - cert["r_star"], "note": cert["note"],
                     "note_grid": grid["note"], "seconds": t1 - t0, "seconds_grid": time.perf_counter() - t1})
    rec = {"job": job.id, "mu": mu, "lam": lam, "group": group, "rows": rows, "H_skipped": skipped,
           "git_revision": mc.git_revision()}
    outputs.dump(rec, part_dir(out, "a") / "runs" / "boundary" / mc.job_file_name(job.id))
    return {"runs": 0, "errors": [], "n_H": len(rows), "calls": sum(r["calls"] + r["calls_grid"] for r in rows)}


def boundary_H() -> tuple:
    return tuple(e2.settings()["H"])


def boundary_mus() -> tuple:
    return REDUCED["boundary_mu"] if reduced() else mus()


# ---------------------------------------------------------------- E6-1 (§7.1): C2-T2 and A1's insurance rule
def e6_1(rows=None, hs=None, mus_=None, lams=LAMS, a1_H=None, a1: bool = True) -> dict:
    """E6-1 (a) and (b) (module docstring). Defaults: the E6(a) rows with alpha_p < 1 at the default alpha, the
    H_BASE points, the mu grid, both lambda' and A1 at E6_1_A1_H."""
    from ..algos import c2rule
    from ..experiments.repro_c2sw_scan import grid_worst
    c2 = paths.import_c2()
    gi = e2.game_inputs()
    AL, LAM, BS = gi["AL"], gi["LAM"], gi["BS"]
    rows = [r for r in (ROWS if rows is None else rows) if r * AL < 1]
    hs = e2.h_base() if hs is None else list(hs)
    mus_ = mus() if mus_ is None else tuple(mus_)
    a1_H = E6_1_A1_H if a1_H is None else tuple(a1_H)
    lam_of = {"a5": LAM, "0": 0.0}
    s = setting()
    bt = float(s["beta_tilde_ref_usd"])
    part_a, part_b, part_a1 = [], [], []
    for r in rows:
        ap = r * AL
        for Hs in hs:
            H = Hs / BS
            th = c2rule.c2_thresholds(AL, ap, 1.0, LAM)
            plan = c2rule.ins_plan(th)
            P = c2.model.Params(mu=1.0, alpha=AL, ap=ap, H=H, lam=LAM)
            w, _ = grid_worst(P, lambda R, plan=plan: plan, lambda xs, R, P=P: c2.model.opt_cost(xs, R, P), th.s0)
            cr = max(2 - AL, ap / AL)
            part_a.append({"r": r, "Hs": Hs, "H": H, "w_ins": float(w), "CR_ins": cr,
                           "ok": bool(cr * (1 - 1e-3) <= w <= cr + 1e-9)})
            for mu in mus_:
                for lam in lams:
                    lm = lam_of[lam]
                    u = c2rule.C2Units(alpha=AL, ap=ap, mu=mu, lam=lm, bw=ap * lm, H=H, beta_tilde_usd=bt,
                                       time_unit_h=bt / float(s["q_usd_per_h"]))
                    dec = bool(c2rule.insure_up_front(u, "lb_react"))
                    first = bool(ap <= AL * (2 - AL))
                    lb = None if first else lb_grid(AL, ap, mu, lm, H)
                    direct = first or (max(2 - AL, ap / AL) < lb)
                    part_b.append({"r": r, "Hs": Hs, "mu": mu, "lam": lam, "insure_up_front": dec, "direct": direct,
                                   "LB_react": lb, "ok": dec == direct})
    if a1:
        from ..instance import public_view
        for H in a1_H:
            spec0 = e2.run_spec(E6_1_LENDER, E6_1_SERIES, H, 1.0, 1, horizon_min=e2.DAY_MIN)
            inst0 = e2.build_base(spec0, 1)[0]
            bands, prot = e2.band_sites(inst0), e2.prot_site(inst0)
            b0 = min(bands)
            a_k = float(inst0.price[bands[b0], e2._rev_contract(inst0, bands[b0])])
            lay, _ = e2.layers_of(inst0)
            for r in rows:
                for mu in mus_:
                    for lam in lams:
                        spec = e2.run_spec(E6_1_LENDER, E6_1_SERIES, H, mu, 1, horizon_min=e2.DAY_MIN,
                                           extra=prot_overrides(r * a_k, lam))
                        ik = e2.single_band(e2.build_base(spec, 1)[0], b0, lay)
                        pol = e2.make_rule_policy(spec, "a1", bands[b0], prot, ik)
                        pol.reset(public_view(ik, "I1"), np.random.default_rng(0))
                        u = pol.units
                        first = bool(u.ap <= u.alpha * (2 - u.alpha))
                        lb = None if first else lb_grid(u.alpha, u.ap, u.mu, u.lam, u.H)
                        direct = first or (max(2 - u.alpha, u.ap / u.alpha) < lb)
                        part_a1.append({"H_min": int(H), "r": r, "mu": mu, "lam": lam, "a_p": r * a_k,
                                        "insured": bool(pol.insured), "direct": bool(direct), "LB_react": lb,
                                        "units": u.as_dict(), "ok": bool(pol.insured) == bool(direct)})
    na = sum(1 for x in part_a if not x["ok"])
    nb = sum(1 for x in part_b if not x["ok"])
    n1 = sum(1 for x in part_a1 if not x["ok"])
    return {"a": {"n": len(part_a), "n_fail": na, "rows": part_a, "mu": 1.0, "lam": LAM},
            "b": {"n": len(part_b), "n_fail": nb, "rows": part_b,
                  "a1": {"n": len(part_a1), "n_fail": n1, "rows": part_a1, "lender": E6_1_LENDER,
                         "series": E6_1_SERIES, "horizon_min": e2.DAY_MIN}},
            "pass": na == 0 and nb == 0 and n1 == 0, "inputs": "code/theory_checks/c2/out/por_default.json inputs"}


def run_c2t2(job, outputs, out) -> dict:
    if reduced():
        res = e6_1(rows=REDUCED["e6_1_rows"], hs=REDUCED["e6_1_hs"], mus_=REDUCED["e6_1_mus"],
                   a1_H=REDUCED["e6_1_a1_H"])
    else:
        res = e6_1()
    res.update(job=job.id, git_revision=mc.git_revision(), reduced=reduced())
    outputs.dump(res, part_dir(out, "a") / "runs" / "c2t2.json")
    return {"runs": 0, "errors": [], "pass": res["pass"], "n_fail": [res["a"]["n_fail"], res["b"]["n_fail"],
                                                                      res["b"]["a1"]["n_fail"]]}


# ---------------------------------------------------------------- E6(b) (§7.2, M31)
def b_job_id(menu: str, mu, c: int) -> str:
    return mc.job_id(EXP, "b", menu=menu, mu=num(mu), c=int(c))


def e6b_horizon() -> int:
    return REDUCED["e6b_horizon_min"] if reduced() else e2.HORIZON_MIN


def e6b_spec(menu: str, mu: float, c: int) -> dict:
    from ..drivers.run import load_run_spec
    rev, prot = MENUS[menu]
    ov = {"time.horizon_min": e6b_horizon(), "time.fast_slot_min": 1,
          "contracts": [dict(x) for x in rev] + ([dict(e2.PROTECTED)] if prot else []),
          "lender_defaults.menu": [x["id"] for x in rev], "stranding.mu_over_beta_tilde": float(mu)}
    if not prot:
        ov.update({"protected_per_region.enabled": False, "protected_per_region.menu": []})
    name = f"e6b_{menu.replace('+', '_')}_mu{num(mu)}_c{int(c)}"
    return load_run_spec({"schema_version": 1, "name": name, "instance": E6B_CONFIG, "overrides": ov,
                          "lender_model": {}, "engine": {"check_invariants": True},
                          "policy": {"id": "A6", "params": {}}, "seeds": {"config": [int(c)]}, "bench": None,
                          "out": "code/sim/out/e6/b/runs"})


def bl0a_all(inst) -> float:
    """BL0a's analytic cost: sum over clients of q_j x the demand in replica-load-hours (M47)."""
    q = np.array([inst.llms[int(j)].q_usd_per_h for j in inst.clients.llm], dtype=np.float64)
    d = np.asarray(inst.clients.demand, dtype=np.float64).sum(axis=1)
    return float(np.sum(q * d) * inst.grid.fast_min / 60.0)


def demand_sha256(inst) -> str:
    return hashlib.sha256(np.ascontiguousarray(inst.clients.demand, dtype=np.float64).tobytes()).hexdigest()


def e6b_instance(menu: str, mu: float, c: int) -> tuple:
    """(inst, model, ecfg, info) of one E6(b) job: the instance the builder gives `menu` (its contracts, sites and
    lendable supply) with the demand of menu R's instance at the same mu, alignment c and horizon (M31): for a menu
    other than R, clients.demand (instance.with_demand) and borrower_stats are menu R's. The builder scales the series
    demand to the lendable supply, which depends on the longest window of the menu; the client lists do not depend on
    it, and InstanceError is raised if they differ. info: demand_menu, bl0a_own_demand (BL0a on the menu's own
    demand), demand_sha256 (of the demand used)."""
    from ..drivers.run import build
    from ..instance import InstanceError, with_demand
    inst, model, ecfg = build(e6b_spec(menu, mu, c), c)
    own = bl0a_all(inst)
    if menu != E6B_DEMAND_MENU:
        ref = build(e6b_spec(E6B_DEMAND_MENU, mu, c), c)[0]
        a, b = inst.clients, ref.clients
        same = (np.array_equal(a.llm, b.llm) and a.region == b.region and a.slo_class == b.slo_class
                and a.borrowers == b.borrowers and inst.grid == ref.grid)
        if not same:
            raise InstanceError(f"E6(b) menu {menu}, c = {c}: its clients or grid differ from menu "
                                f"{E6B_DEMAND_MENU}'s, so it cannot take that menu's demand")
        inst = dataclasses.replace(with_demand(inst, ref.clients.demand),
                                   borrower_stats={k: dict(v) for k, v in ref.borrower_stats.items()})
    info = {"demand_menu": E6B_DEMAND_MENU, "bl0a_own_demand": own, "demand_sha256": demand_sha256(inst)}
    return inst, model, ecfg, info


def run_b(job, outputs, out) -> dict:
    from ..drivers.run import driver_inputs, make_policy
    from ..engine import simulate
    p = job.params
    menu, mu, c = p["menu"], float(p["mu"]), int(p["c"])
    spec = e6b_spec(menu, mu, c)
    inst, model, ecfg, dinfo = e6b_instance(menu, mu, c)
    inputs, meta = driver_inputs("A6", spec["policy"]["params"], inst)
    bl0 = bl0a_all(inst)
    errors, runs = [], []
    for ps in (REDUCED["e6b_policy_seeds"] if reduced() else E6B_POLICY_SEEDS):
        t0 = time.perf_counter()
        pol = make_policy(spec, inst, inputs=inputs)
        res = mc.try_run(errors, f"policy seed {ps}", simulate, inst, pol, model, ecfg, lender_seed=c, policy_seed=ps)
        if res is None:
            continue
        m = res.metrics
        runs.append({"policy_seed": int(ps), "total": float(res.components["total"]),
                     "components": {k: float(v) for k, v in res.components.items()},
                     "gpu_hours_by_class": {k: float(v) for k, v in (m.get("gpu_hours_by_class") or {}).items()},
                     "n_leases": len(res.leases), "invariant_failures": len(res.invariant_failures),
                     "invariant_first": list(res.invariant_failures[:2]),
                     "gpu_only_lease_slots": int(m.get("gpu_only_lease_slots", 0)), "wall_s": time.perf_counter() - t0,
                     "peak_rss_mb": res.runtime.get("peak_rss_mb")})
    rec = {"job": job.id, "menu": menu, "mu": mu, "c": c, "bl0a": bl0, "n_sites": inst.m, "n_contracts": inst.K,
           "demand_load_h": float(np.asarray(inst.clients.demand, dtype=np.float64).sum()) * inst.grid.fast_min / 60.0,
           **dinfo,
           "contracts": [x.id for x in inst.contracts], "driver_inputs": meta, "runs": runs,
           "git_revision": mc.git_revision(), "horizon_min": e6b_horizon()}
    outputs.dump(rec, part_dir(out, "b") / "runs" / mc.job_file_name(job.id))
    return {"runs": len(runs), "errors": errors, "bl0a": bl0,
            "totals": [x["total"] for x in runs]}


def e6b_list() -> list:
    """(menu, mu, c) of the E6(b) jobs: every menu at mu = 1 and the default menu R+P at the other mu values,
    alignments 1-4 (reduced: 1)."""
    cs = REDUCED["e6b_alignments"] if reduced() else e2.ALIGNMENTS
    out = [(m, 1.0, c) for m in MENUS for c in cs]
    out += [(E6B_DEFAULT_MENU, mu, c) for mu in mus() if abs(mu - 1.0) > 1e-12 for c in cs]
    return out


# ---------------------------------------------------------------- jobs and estimates
def _cert_s(Hc: float) -> float:
    for top, s in EST_CERT_S:
        if Hc <= top:
            return s
    return EST_CERT_S[-1][1]


def a_cell_est_s(lender: str, H: int, c: int) -> float:
    n_ser = len(e2.settings()["series"])
    keys = n_ser * e2.K_LAYERS
    runs = keys * len(PLANS) * len(LAMS)
    job_mus = mus() if c == 1 else (1.0,)
    ins = sum(1 for mu in job_mus if e2.reaction_row(lender, H, mu).get("insure_up_front"))
    runs += ins * keys
    calls = 0
    if c == 1:
        a = float(e2.reaction_row(lender, H, mus()[0])["alpha_k"])
        calls = sum(1 for r in ROWS if r * a > a * (2 - a)) * len(mus()) * len(LAMS)
        if e2.group_of(lender) == "maas":
            runs += keys // E63_EVERY
    return EST_RUN_S * runs + EST_DECISION_S * calls


def boundary_est_s(group: str) -> float:
    t = 0.0
    for H in boundary_H():
        bi = boundary_inputs(H, group)
        if bi is not None:
            t += EST_STEPS * (_cert_s(bi["H_c2"]) + EST_GRID_S)
    return t


def c2t2_est_s() -> float:
    gi = e2.game_inputs()
    rows = [r for r in (REDUCED["e6_1_rows"] if reduced() else ROWS) if r * gi["AL"] < 1]
    hs = REDUCED["e6_1_hs"] if reduced() else e2.h_base()
    ms = REDUCED["e6_1_mus"] if reduced() else mus()
    a1h = REDUCED["e6_1_a1_H"] if reduced() else E6_1_A1_H
    outside = [r for r in rows if r > 2 - gi["AL"]]
    calls = 2 * len(outside) * len(hs) * len(ms) * len(LAMS) + 2 * len(outside) * len(a1h) * len(ms) * len(LAMS)
    return EST_DECISION_S * (calls + len(rows) * len(hs))


def jobs(ps=None) -> list:
    """The E6 jobs of the parts `ps` (default: E6_PART), in run order: part a's alignment-1 cells, boundaries and
    E6-1, then the alignments 2-4; part b's (menu, mu, alignment) jobs."""
    ps = parts() if ps is None else list(ps)
    out = []
    S = e2.settings()
    if "a" in ps:
        for lender, H in e2.cells():
            out.append(mc.Job(a_job_id(lender, H, 1), "pool", {"part": "a", "kind": "cell", "lender": lender,
                                                                "H": int(H), "c": 1}, a_cell_est_s(lender, H, 1)))
        for mu in boundary_mus():
            for lam in LAMS:
                for g in ("maas", "spot"):
                    out.append(mc.Job(boundary_job_id(mu, lam, g), "pool",
                                      {"part": "a", "kind": "boundary", "mu": float(mu), "lam": lam, "group": g},
                                      boundary_est_s(g)))
        out.append(mc.Job(mc.job_id(EXP, "a_c2t2"), "pool", {"part": "a", "kind": "c2t2"}, c2t2_est_s()))
        for c in S["alignments"]:
            if c == 1:
                continue
            for lender, H in e2.cells():
                out.append(mc.Job(a_job_id(lender, H, c), "pool", {"part": "a", "kind": "cell", "lender": lender,
                                                                    "H": int(H), "c": int(c)},
                                  a_cell_est_s(lender, H, c)))
    if "b" in ps:
        n_seeds = len(REDUCED["e6b_policy_seeds"] if reduced() else E6B_POLICY_SEEDS)
        for menu, mu, c in e6b_list():
            out.append(mc.Job(b_job_id(menu, mu, c), "pool", {"part": "b", "kind": "b", "menu": menu,
                                                               "mu": float(mu), "c": int(c)}, n_seeds * EST_E6B_RUN_S))
    return out


def run(job, outputs, out) -> dict:
    k = job.params["kind"]
    fn = {"cell": run_a_cell, "boundary": run_boundary, "c2t2": run_c2t2, "b": run_b}[k]
    return fn(job, outputs, out)


def manifest_extra(out) -> dict:
    """Instance hashes: part a's reference instances (r = 1.1, both lambda') per cell job and series, part b's
    instance per job (with menu R's demand, e6b_instance); the sha256 of the input files."""
    hashes = {}
    for j in jobs():
        p = j.params
        if p["kind"] == "cell":
            h = {}
            for s in e2.settings()["series"]:
                inst = e2.build_base(e2.run_spec(p["lender"], s, p["H"], 1.0, p["c"]), p["c"])[0]
                bands = e2.band_sites(inst)
                if not bands:
                    continue
                a_k = float(inst.price[bands[min(bands)], e2._rev_contract(inst, bands[min(bands)])])
                h[s] = {lam: mc.instance_hash(e2.build_base(e2.run_spec(p["lender"], s, p["H"], 1.0, p["c"],
                                                                        extra=prot_overrides(R_REF * a_k, lam)),
                                                            p["c"])[0]) for lam in LAMS}
            hashes[j.id] = h
        elif p["kind"] == "b":
            hashes[j.id] = mc.instance_hash(e6b_instance(p["menu"], p["mu"], p["c"])[0])
    files = (e2.REACTIONS, e2.A11_FILE, e2.A12_FILE, e2.POR_FILE, paths.CONFIGS / E6B_CONFIG)
    return {"instance_hashes": hashes, "inputs_sha256": {str(f.relative_to(paths.REPO)): e2._sha256(f) for f in files},
            "reduced": reduced(), "parts": parts()}


# ---------------------------------------------------------------- summaries
def _cell_null(note: str) -> dict:
    """A heatmap cell without a value: the cell fields, null with their '*_note' (§2.6), and `note`."""
    return {"value": None, "value_note": note, "ci95": [None, None], "ci95_note": note, "p95": None,
            "p95_note": note, "n_pairs": 0, "n_alignments": 0, "alignments": [], "n_lenders": 0,
            "share_insured": None, "share_insured_note": note, "kind_counts": None, "kind_counts_note": note,
            "react_over_ins": None, "react_over_ins_note": note, "note": note}


def summary_a(out_a: Path) -> dict:
    out_a = Path(out_a)
    S = e2.settings()
    js = [j for j in jobs_all() if j.params["part"] == "a"]
    recs = mc.read_records(out_a)
    ok = {j.id for j in js if (recs.get(j.id) or {}).get("status") == "ok"}
    data = {}            # (lender, H, c) -> run file
    for j in js:
        if j.params["kind"] == "cell" and j.id in ok:
            d = mc.read_json(a_run_path(out_a, j.params["lender"], j.params["H"], j.params["c"]))
            if d is not None:
                data[(j.params["lender"], int(j.params["H"]), int(j.params["c"]))] = d
    dec = {(l, H): d["decisions"] for (l, H, c), d in data.items() if c == 1 and d.get("decisions")}
    # per pair (lender, H, c, series): the layers with a band
    pairs = {}
    for (l, H, c), d in data.items():
        for s, so in d["series"].items():
            pairs[(l, H, c, s)] = {"a_k": d["cell"]["a_k"], "bt": d["cell"]["beta_tilde_ref"],
                                   "layers": [L for L in so["layers"] if not L["bandless"]]}

    def pair_sums(pk, r: float, mu: float, lam: str):
        """(sum BL7, sum A1, sum INS, sum reaction plan, plan) of one pair at (r, mu, lam'), or None."""
        l, H, c, s = pk
        dd = (dec.get((l, H)) or {}).get(num(r), {}).get(num(mu), {}).get(lam)
        if dd is None:
            return None
        P = pairs[pk]
        a_p, mfb = r * P["a_k"], mu * P["bt"]
        sb = sa = si = sr = 0.0
        for L in P["layers"]:
            b7 = (L.get("bl7") or {}).get(num(mu))
            ins = (L.get("ins") or {}).get(lam)
            warm = (L.get("warm") or {}).get(lam)
            if b7 is None or ins is None or warm is None:
                return None
            cb, ci, cw = b7["total"], plan_cost(ins, a_p, mfb), plan_cost(warm, a_p, mfb)
            sb += cb
            si += ci
            sr += cw if dd["reaction"] == "warm" else cb
            sa += {"ins": ci, "warm": cw, "cold": cb}[dd["plan"]]
        return sb, sa, si, sr, dd["plan"]

    groups = {"maas": list(e2.maas_lenders()), "spot": list(e2.spot_pools())}
    by_H = {}
    for pk in pairs:
        by_H.setdefault(pk[1], []).append(pk)
    cells_out, e64_dev, e64_n, e65 = {}, [], 0, []
    bnd = {}
    for j in js:
        if j.params["kind"] == "boundary" and j.id in ok:
            d = mc.read_json(part_dir(out_a, "a") / "runs" / "boundary" / mc.job_file_name(j.id))
            if d:
                bnd[(num(d["mu"]), d["lam"], d["group"])] = {r["H"]: r for r in d["rows"]}
    for g, lenders in groups.items():
        for lam in LAMS:
            for mu in mus():
                for H in S["H"]:
                    for r in ROWS:
                        vals, react, kinds, cs, ls = [], [], {"ins": 0, "warm": 0, "cold": 0}, set(), set()
                        for (l, h, c, s) in by_H.get(H, []):
                            if l not in lenders or c not in alignments_of(mu):
                                continue
                            ps_ = pair_sums((l, h, c, s), r, mu, lam)
                            if ps_ is None:
                                continue
                            sb, sa, si, sr, plan = ps_
                            if not sa > 0 or not si > 0:
                                continue
                            vals.append(sb / sa)
                            react.append(sr / si)
                            kinds[plan] += 1
                            cs.add(c)
                            ls.add(l)
                            if plan == "cold":
                                e64_n += 1
                                e64_dev.append(abs(sb / sa - 1.0))
                        tgt = cells_out.setdefault(g, {}).setdefault(lam, {}).setdefault(num(mu), {}) \
                            .setdefault(num(H), {})
                        if g == "spot" and len(ls) < 2:
                            tgt[num(r)] = _cell_null(f"fewer than two spot pools with data at H = {H} min (M23)")
                            continue
                        if not vals:
                            tgt[num(r)] = _cell_null("no pair with data")
                            continue
                        a = mc.median_summary(vals)
                        ar = mc.median_summary(react)
                        n = len(vals)
                        tgt[num(r)] = {"value": a["median"], "ci95": a["median_ci95"], "p95": a["p95"], "n_pairs": n,
                                       "n_alignments": len(cs), "alignments": sorted(cs), "n_lenders": len(ls),
                                       "share_insured": kinds["ins"] / n, "kind_counts": kinds,
                                       "react_over_ins": {"median": ar["median"], "ci95": ar["median_ci95"]}}
                        # E6-5 (informative): insuring pays on the traces outside r < r*, or the reverse
                        b = bnd.get((num(mu), lam, g), {}).get(H)
                        if b is not None:
                            pays = ar["median"] > 1.0
                            says = r < b["r_star"]
                            if pays != says:
                                e65.append({"group": g, "lam": lam, "mu": mu, "H": H, "r": r, "r_star": b["r_star"],
                                            "react_over_ins": ar["median"], "insure_pays": bool(pays),
                                            "boundary_insures": bool(says)})
    heat = {"meta": {"spec": "design/sim_spec_ms3.md §7.1 (M26-M30)", "rows": list(ROWS), "H": list(S["H"]),
                     "mu": list(mus()), "lam": {"a5": "a5_2GBps at the protected site", "0": "lambda' = 0 at the "
                                                "protected site (explicit, lam_s 0), a5_2GBps at the revocable site"},
                     "groups": groups, "alignments": {num(mu): list(alignments_of(mu)) for mu in mus()},
                     "value": "median over the (lender, series[, alignment]) pairs of sum_k cost_BL7 / sum_k cost_A1 "
                              "over the layers with a band (M29)",
                     "git_revision": mc.git_revision(), "written": mc._now(), "reduced": reduced()},
            "cells": cells_out}
    mc.dump_json(heat, out_a / "heatmap.json")
    # boundary.json: columns per (mu, lam', group)
    rows_b = {}
    cols = ("H", "H_min", "H_c2", "alpha", "lam_c2", "r_star", "r_star_grid", "diff", "lb_at_r_star",
            "lb_grid_at_r_star_grid", "calls", "calls_grid", "note", "seconds")
    for j in js:
        if j.params["kind"] != "boundary":
            continue
        d = (mc.read_json(part_dir(out_a, "a") / "runs" / "boundary" / mc.job_file_name(j.id))
             if j.id in ok else None)
        tgt = rows_b.setdefault(num(j.params["mu"]), {}).setdefault(j.params["lam"], {})
        if not d:              # a listed boundary job without an 'ok' output: null with a note (§2.6)
            tgt[j.params["group"]] = None
            tgt[j.params["group"] + "_note"] = f"job {j.id} has no 'ok' record"
            continue
        col = {k: [r[k] for r in d["rows"]] for k in cols}
        col["H_skipped"] = d["H_skipped"]
        tgt[d["group"]] = col
    boundary = {"meta": {"spec": "design/sim_spec_ms3.md §7.1 (M30)",
                         "bound": "necessity_lb.lb_all(dict(b=1, a=alpha, ap=r alpha, mu=mu, lam=lambda, rrl=False), "
                                  "H, include_insure=False)[0] (certified; C2-T3 PROVEN, switch cost beta, tau = 0)",
                         "grid_value": "families.lb_react(model.Params(mu, alpha, ap, H, lam))[0] (a grid value, not "
                                       "certified)",
                         "interval": [None, R_HI], "interval_note": "r in [2 - alpha, 2.5]", "tolerance": R_TOL,
                         "inputs": "alpha: median alpha_k of code/sim/out/ms2_checks/e2_reactions.json at "
                                   "s5_tau5_H<H>; phi and lambda_s from its meta.setting",
                         "setting": {k: setting()[k] for k in ("phi", "lam_s", "q_usd_per_h")},
                         "git_revision": mc.git_revision(), "written": mc._now(), "reduced": reduced()},
                "rows": rows_b}
    mc.dump_json(boundary, out_a / "boundary.json")
    # checks
    e62 = [x for (l, H, c), d in data.items() for x in d["checks"]["E6_2"]]
    e62_fail = [x for x in e62 if x["rel"] > REL_TOL or not x["plan_equal"]]
    units_fail, n_units = [], 0
    for (l, H, c), d in data.items():
        if c == 1 or (l, H, 1) not in data:
            continue
        ref = data[(l, H, 1)]
        for s, so in d["series"].items():
            for L in so["layers"]:
                if L["bandless"]:
                    continue
                R = next((x for x in ref["series"].get(s, {}).get("layers", []) if x["k"] == L["k"]), None)
                for plan in PLANS:
                    for lam in LAMS:
                        u = ((L.get(plan) or {}).get(lam) or {}).get("units")
                        u1 = (((R or {}).get(plan) or {}).get(lam) or {}).get("units")
                        if u is None or u1 is None:
                            continue
                        n_units += 1
                        bad = [f for f in u1 if u1[f] is not None and u.get(f) is not None
                               and e2._rel_diff(u[f], u1[f]) > REL_TOL] + \
                              [f for f in u1 if (u1[f] is None) != (u.get(f) is None)]
                        if bad:
                            units_fail.append({"lender": l, "H": H, "c": c, "series": s, "k": L["k"], "plan": plan,
                                               "lam": lam, "fields": bad})
    e63 = [x for (l, H, c), d in data.items() for x in d["checks"]["E6_3"]]
    e63_fail = [x for x in e63 if x["abs_diff"] is not None and x["abs_diff"] > REL_TOL]
    c2t2 = mc.read_json(part_dir(out_a, "a") / "runs" / "c2t2.json")
    jid_c2t2 = mc.job_id(EXP, "a_c2t2")
    checks = {
        "E6-1": ({k: c2t2[k] for k in ("a", "b", "pass")} if (c2t2 and jid_c2t2 in ok) else
                 {"pass": None, "pass_note": "job e6:a_c2t2 has no 'ok' record"}),
        "E6-2": {"reruns": e62, "n": len(e62), "n_fail": len(e62_fail), "failures": e62_fail[:50],
                 "units_across_alignments": {"n": n_units, "n_fail": len(units_fail), "failures": units_fail[:50]},
                 "tolerance": REL_TOL, "pass": bool(e62) and not e62_fail and not units_fail},
        "E6-3": {"rows": e63, "n": len(e63), "n_fail": len(e63_fail), "tolerance_usd": REL_TOL,
                 "n_without_e2_cold": sum(1 for x in e63 if x["abs_diff"] is None),
                 "pass": bool([x for x in e63 if x["abs_diff"] is not None]) and not e63_fail},
        "E6-4": {"n_pairs": e64_n, "max_abs_dev": max(e64_dev) if e64_dev else None,
                 "pass": all(x == 0.0 for x in e64_dev)},
        "E6-5": {"disagreements": e65[:500], "n_disagree": len(e65),
                 "n_cells": sum(1 for g in cells_out.values() for a in g.values() for m in a.values()
                                for h in m.values() for x in h.values() if x.get("value") is not None),
                 "informative": True}}
    checked = {"E6-1": checks["E6-1"]["pass"] is not None, "E6-2": bool(e62),
               "E6-3": any(x["abs_diff"] is not None for x in e63), "E6-4": e64_n > 0}
    checks = {k: {"status": ("informative" if k == "E6-5" else
                             ("pass" if v["pass"] else "fail") if checked[k] else "missing"),
                  "claim": CHECK_CLAIMS[k], **v} for k, v in checks.items()}
    merged = {}
    for (l, H), d in sorted(dec.items()):
        merged.setdefault(l, {})[num(H)] = {rk: {mk: {lam: x["plan"] for lam, x in v2.items()} for mk, v2 in v1.items()}
                                            for rk, v1 in d.items()}
    dc = {}
    for (l, H), d in dec.items():
        for rk, v1 in d.items():
            for mk, v2 in v1.items():
                for lam, x in v2.items():
                    t = dc.setdefault(lam, {}).setdefault(mk, {}).setdefault(rk, {"ins": 0, "warm": 0, "cold": 0,
                                                                                  "first_clause": 0})
                    t[x["plan"]] += 1
                    t["first_clause"] += int(bool(x["first_clause"]))
    meta ={"exp": EXP, "part": "a", "spec": SPEC + ".1", "git_revision": mc.git_revision(), "versions": mc.versions(),
            "written": mc._now(), "reduced": reduced(), "rows": list(ROWS), "r_ref": R_REF, "lam": list(LAMS),
            "settings": {k: (list(v) if isinstance(v, tuple) else v) for k, v in S.items()},
            "cells": [[l, h] for l, h in e2.cells()], "groups": groups, "status_labels": STATUS_LABELS,
            "sources": {"e2_runs": "code/sim/out/e2/runs/cells (the same layout under MS3_ROOT)",
                        "reactions": "code/sim/out/ms2_checks/e2_reactions.json",
                        "por_default": "code/theory_checks/c2/out/por_default.json"},
            "jobs_ok": len(ok), "jobs_missing": [j.id for j in js if j.id not in ok]}
    summ = {"meta": meta, "decisions": merged, "decision_counts": dc, "checks": checks}
    mc.dump_json(summ, out_a / "summary.json")
    mc.write_text(tables_a(summ, heat, boundary), out_a / "tables.md")
    return summ


def tables_a(summ: dict, heat: dict, boundary: dict) -> str:
    out = ["# E6(a): when protection pays (design/sim_spec_ms3.md §7.1)", ""]
    for g in ("maas", "spot"):
        for lam in LAMS:
            m = heat["cells"].get(g, {}).get(lam, {}).get(num(1.0), {})
            out.append(f"## BL7 / A1, group {g}, lambda' = {lam}, mu = 1 (median; rows r, columns H in minutes)")
            Hs = list(m)
            rows = []
            for r in ROWS:
                rows.append([r] + [m[h].get(num(r), {}).get("value") for h in Hs])
            out += [mc.md_table(["r"] + Hs, rows), ""]
    b = boundary["rows"].get(num(1.0), {}).get("a5", {}).get("maas")
    if b:
        out.append("## Boundary r*(H), MaaS, lambda' = a5, mu = 1")
        out += [mc.md_table(["H (min)", "alpha", "r*", "r*_grid"],
                            [[h, a, r, rg] for h, a, r, rg in zip(b["H"], b["alpha"], b["r_star"], b["r_star_grid"])]),
                ""]
    out.append("## Checks")
    out += [mc.md_table(["check", "status"], [[k, v["status"]] for k, v in summ["checks"].items()]), ""]
    return "\n".join(out) + "\n"


def summary_b(out_b: Path) -> dict:
    out_b = Path(out_b)
    js = [j for j in jobs_all() if j.params["part"] == "b"]
    recs = mc.read_records(out_b)
    ok = {j.id for j in js if (recs.get(j.id) or {}).get("status") == "ok"}
    data = {}
    for j in js:
        if j.id in ok:
            d = mc.read_json(part_dir(out_b, "b") / "runs" / mc.job_file_name(j.id))
            if d:
                data[(d["menu"], num(d["mu"]), int(d["c"]))] = d
    menus = {}
    n_runs = n_inv = n_gpu = 0
    for menu in MENUS:
        for mu in mus():
            rs = [(c, r, d["bl0a"]) for (m, mk, c), d in sorted(data.items()) if m == menu and mk == num(mu)
                  for r in d["runs"]]
            tgt = menus.setdefault(menu, {})
            if not rs:
                if (menu, mu) in {(m, u) for m, u, _ in e6b_list()}:
                    tgt[num(mu)] = _menu_null("no run with data")
                continue
            for _, r, _ in rs:
                n_runs += 1
                n_inv += int(r["invariant_failures"] > 0)
                n_gpu += int(r["gpu_only_lease_slots"] > 0)
            co = [r["total"] / b for _, r, b in rs if b > 0]
            a = mc.median_summary(co)
            a.update(mean=float(np.mean(co)) if co else None, mean_ci95=_mean_ci(co))
            # cost(R) / cost(menu), paired by (alignment, policy seed), at mu = 1; and the same ratio of the costs
            # over each run's own BL0a (equal to the first up to rounding, since every menu has menu R's demand and
            # so the same BL0a at an alignment, meta.instances; kept as the check of that)
            if abs(mu - 1.0) <= 1e-12:
                base = {(c, r["policy_seed"]): (r["total"], d["bl0a"]) for (m, mk, c), d in data.items()
                        if m == "R" and mk == num(1.0) for r in d["runs"]}
                pairs_ = [(base[(c, r["policy_seed"])], (r["total"], b)) for c, r, b in rs
                          if (c, r["policy_seed"]) in base and r["total"] > 0]
                ratios = [x[0] / y[0] for x, y in pairs_]
                ratios_n = [(x[0] / x[1]) / (y[0] / y[1]) for x, y in pairs_ if x[1] > 0 and y[1] > 0]
                crc = mc.median_summary(ratios) if ratios else _b_null("no paired run of menu R")
                crn = mc.median_summary(ratios_n) if ratios_n else _b_null("no paired run of menu R")
            else:
                crc = crn = _b_null("menu R runs at mu = 1 only")
            cls = {}
            for _, r, _ in rs:
                for k, v in r["gpu_hours_by_class"].items():
                    cls[k] = cls.get(k, 0.0) + v
            tot_h = sum(cls.values())
            share = {k: v / tot_h for k, v in sorted(cls.items())} if tot_h > 0 else {}
            comp = {k: float(np.mean([r["components"].get(k, 0.0) / b for _, r, b in rs if b > 0]))
                    for k in ("lease_prepaid", "lease_rent", "lease", "loading", "routing", "fallback", "stranding",
                              "total")}
            tgt[num(mu)] = {"cost_over_bl0a": a, "cost_R_over_cost": crc, "cost_R_over_cost_bl0a": crn,
                            "gpu_hour_share": share, "components_over_bl0a": comp, "n_runs": len(rs),
                            "alignments": sorted({c for c, _, _ in rs}),
                            "policy_seeds": sorted({r["policy_seed"] for _, r, _ in rs}),
                            "bl0a_by_alignment": {num(c): b for c, _, b in sorted(rs, key=lambda t: t[0])}}
            if not share:
                tgt[num(mu)]["gpu_hour_share_note"] = "no GPU-hour"
    checks = {"E6-6": {"status": ("pass" if n_inv == 0 and n_gpu == 0 else "fail") if n_runs else "missing",
                       "claim": CHECK_CLAIMS["E6-6"], "n_runs": n_runs, "n_invariant_failures": n_inv,
                       "n_gpu_only_lease_slots": n_gpu, "pass": n_runs > 0 and n_inv == 0 and n_gpu == 0}}
    # each menu's instance per alignment (mu = 1): its own contracts, sites and lendable supply with menu R's demand
    # (e6b_instance); bl0a_own_demand is BL0a on the demand the builder scales to the menu's own lendable supply
    inst_by = {m: {num(c): {k: d.get(k) for k in ("bl0a", "bl0a_own_demand", "demand_load_h", "demand_sha256",
                                                   "n_sites", "n_contracts")}
                   for (mm, mk, c), d in sorted(data.items()) if mm == m and mk == num(1.0)} for m in MENUS}
    rel = []
    for c in sorted({c for v in inst_by.values() for c in v}):
        b = [v[c]["bl0a"] for v in inst_by.values() if c in v and v[c]["bl0a"]]
        if len(b) > 1:
            rel.append(max(b) / min(b) - 1.0)
    instances = {"demand_menu": E6B_DEMAND_MENU, "by_menu": inst_by, "max_rel_diff_bl0a": max(rel) if rel else None,
                 "note": "each menu's instance is built from its own contracts (a lender's lendable supply uses the "
                         "longest window of its menu, D_max) and takes the demand of menu R's instance at the same "
                         "alignment (the builder would scale the series demand to the menu's own supply, "
                         "borrowers.market_tightness; bl0a_own_demand), so the menus differ only in contracts and "
                         "lendable supply and have one BL0a per alignment"}
    if not rel:
        instances["max_rel_diff_bl0a_note"] = "fewer than two menus with runs at an alignment"
    meta = {"exp": EXP, "part": "b", "spec": SPEC + ".2", "git_revision": mc.git_revision(), "written": mc._now(),
            "instances": instances,
            "reduced": reduced(), "config": f"configs/{E6B_CONFIG}", "horizon_min": e6b_horizon(),
            "policy": {"id": "A6", "params": {}},
            "menus": {m: {"revocable": [x["id"] for x in rev], "protected": prot} for m, (rev, prot) in MENUS.items()},
            "policy_seeds": list(REDUCED["e6b_policy_seeds"] if reduced() else E6B_POLICY_SEEDS),
            "alignments": list(REDUCED["e6b_alignments"] if reduced() else e2.ALIGNMENTS),
            "jobs_ok": len(ok), "jobs_missing": [j.id for j in js if j.id not in ok]}
    summ = {"meta": meta, "menus": menus, "checks": checks}
    mc.dump_json(summ, out_b / "summary.json")
    rows = []
    for menu, v in menus.items():
        for mk, x in v.items():
            co = x.get("cost_over_bl0a") or {}
            rows.append([menu, mk, co.get("median"), (x.get("cost_R_over_cost") or {}).get("median"),
                         x.get("n_runs")])
    mc.write_text("# E6(b): menus of growing richness (design/sim_spec_ms3.md §7.2)\n\n"
                  + mc.md_table(["menu", "mu", "cost / BL0a (median)", "cost(R) / cost", "runs"], rows)
                  + f"\nE6-6: {checks['E6-6']['status']}\n", out_b / "tables.md")
    return summ


def _b_null(note: str, mean: bool = False) -> dict:
    """An aggregate of E6(b) without a value (median_summary's fields, with mean and mean_ci95 for cost_over_bl0a),
    each null with its '*_note' (§2.6), and `note`."""
    d = {"n": 0, "median": None, "median_note": note, "median_ci95": [None, None], "median_ci95_note": note,
         "p95": None, "p95_note": note, "max": None, "max_note": note, "note": note}
    if mean:
        d.update(mean=None, mean_note=note, mean_ci95=[None, None], mean_ci95_note=note)
    return d


def _menu_null(note: str) -> dict:
    """menus.<menu>.<mu> without runs: the fields of a menu entry, null with their '*_note' (§2.6), and `note`."""
    return {"note": note, "cost_over_bl0a": _b_null(note, mean=True), "cost_R_over_cost": _b_null(note),
            "cost_R_over_cost_bl0a": _b_null(note), "gpu_hour_share": None, "gpu_hour_share_note": note,
            "components_over_bl0a": None, "components_over_bl0a_note": note, "n_runs": 0, "alignments": [],
            "policy_seeds": [], "bl0a_by_alignment": {}}


def _mean_ci(v, B: int = 2000, seed: int = 0) -> list:
    """95% percentile bootstrap interval of the mean (B resamples, default_rng(seed))."""
    x = np.asarray(v, dtype=np.float64)
    if len(x) == 0:
        return [None, None]
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), size=(B, len(x)))].mean(axis=1)
    lo, hi = np.percentile(m, [2.5, 97.5])
    return [float(lo), float(hi)]


def jobs_all() -> list:
    """Every job of both parts (the summaries look up the records of their own part)."""
    return jobs(["a", "b"])


def summary(out) -> dict:
    res = {}
    for p in parts():
        res[p] = (summary_a if p == "a" else summary_b)(part_dir(out, p))
    return res


def main(argv=None) -> int:
    if reduced():
        os.environ["MS3_E2_REDUCED"] = "1"      # E6(a) reads E2's reduced runs (module docstring)
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=argv, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
