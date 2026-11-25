"""X10: Lemma G5'(c) pathwise. On every engine run, whatever the policy (on_fast included) and the lender, and at
every slow slot t, ALG(t) >= LB'(t), up to the routing's tolerance.

Claim and source. design/theory/c3_c4_c5_general.md §9, Lemma G5' (per-group online lower bound), part (c) (full
model, pathwise), PROVEN (audited: design/theory/audit_guard.md, "Audit addendum (P6)", written for step P6 of
design/sublet_v2.md §5).
A violation is LB'(t) - ALG(t) > TOL max(1, ALG(t)) at some slow slot, TOL = 1e-9.

Oracle. LB'(t) is computed here from the text's full-model definition, independently of the prototype
(experiments/ms5b_proto/lb.py) and of the built allowance (algos/online_lb.py, written later): groups = the
connected components, with at least one site, of the bipartite graph of usable arcs (client c of LLM j, site l) with
delta_cl finite and < q_j (the engine's arc_ok), found by a search over the graph; zeta_k = P_k / (ceil(P_k / Delta_f)
Delta_f) (1 if P_k = 0); Lambda^ms_jl = round(1000 Lambda_jl) (rule T8); theta_jl = ceil(Lambda^ms_jl / (60000
Delta_f)); Lambda-bar_jl = min(Lambda_jl / 60, theta_jl Delta_f) minutes; r_Gamma = min zeta_k g_j a_lk over the
group's sites and their menus; entry cost beta-hat = min beta_jl + r_Gamma min Lambda-bar_jl / 60; capacitated:
LB'_Gamma(t) = min over integers nu >= 0 of nu beta-hat + Delta_f/60 sum_{f <= f_t} h_f(min(nu, n°_f)), h_f(n) = n r +
q_j (d_Gamma(f) - n)^+, with the text's closed-form least minimizer n°_f (nu enumerated over 0..max_f n°_f, which the
proof of (a) shows is enough); uncapacitated: min{Delta_f/60 sum q_j d_Gamma, beta-hat + Delta_f/60 sum min(r, q_j
d_Gamma)}; LB'(t) = sum over groups at f_t = (t + 1) phi - 1. ALG(t) is the cumulative sum of the engine's per-slot
ledger total (RunResult.per_slot['total']).

Proof steps checked on every run (failures are counted as step failures and make the script exit 1), from the run's
records (lease and replica records, the ledger, the routing record of EngineConfig(record_routing=True)), not from
the engine's internal state:
  step 1    per lease, the charges booked through t (prepaid at its purchase slot, rent G a Delta_f/60 per alive fast
            slot from rent_from_fast = max(s phi, ceil((start + P_k)/Delta_f)), rule T7) are >= zeta_k G a
            Delta_f/60 |A_L n [0, f_t]|; the recomputed charges equal the ledger's lease components slot by slot;
  step 2    at every fast slot, the replicas that exist on a lease use at most its GPUs, and a replica's existence
            interval [load fast slot, end_fast) lies in its lease's alive interval;
  step 3    warm_fast = t_rho phi + theta_jl for every replica (rule T8 with theta computed here);
  step 4    per group and fast slot, its clients' fallback q_j sum_c b_c(f) >= psi_Gamma(f) (capacitated:
            q_j (d - y)^+, uncapacitated: q_j d [y = 0], y = warm replicas of j_Gamma at the group's sites);
  step 5    per group and slot, the charges attributed to the group (loading charge plus share zeta_k g_j a_lk
            Delta_f/60 per existing fast slot <= f_t of every replica of j_Gamma at a group site that is warm by f_t,
            plus its clients' fallback through f_t) >= V beta-hat + Delta_f/60 sum (r y + psi) >= LB'_Gamma(t); and
            min_{0 <= n <= nu} h_f(n) = h_f(min(nu, n°_f)) for every nu up to ceil(max d) + 2 (n° is the least
            minimizer);
  step 6    the attributed charges summed over the groups are <= ALG(t);
  engine    the engine's own invariants (INV1-INV8, RunResult.invariant_failures), and the ledger total equals the sum
            of its nine components slot by slot.

Runs. A policy fuzzer (class Fuzz) in six styles: 'track' (per group a target replica count from the slot's demand,
with noise, bought as several replicas per lease on the cheapest zeta-adjusted contract or loaded onto free GPUs of
a held lease; leases released when their rent would start inside the slot, i.e. inside the prepaid region, and a
few at random), 'exact' (the lower bound's own plan without noise: the peak demand rounded up, one replica under
kappa_infinite, the cheapest zeta-adjusted contract, every lease released at the first slot that would pay rent;
it drives ALG(t) onto LB'(t) where the bound is attained, e.g. probe 0), 'random' (random Buy of 1-3 replicas with
admission 0, 0.3 or 1, Load of any LLM onto a held lease, Unload, Release, SetAdmission, Drain), 'swap' (Unload a
replica and Load another LLM onto the freed GPUs in the same list; Loads into free GPUs; Buys of 2-3 replicas),
'hog' (fills every revocable site to its capacity with leases of several replicas and keeps them, plus the random
actions at a third of the slots, so that buffer violations hit the platform), 'mixed' (track, random and swap);
every style but 'track' and 'exact' uses the fast-loop hook (wants_fast) and issues Drain and SetAdmission from
on_fast, also on replicas created in the same slot. Instances: the variant builders of
code/theory_checks/c3/check_g5p.py, copied (36 toy variants, 16 ms2_multi_small variants with its perturbation, 5
probes; not imported, since that script imports the prototype), the eight time grids of
tests/test_guard.py::_rich_instance (all four stranding coefficients positive, two LLMs), and four windows of
configs/q44_spot_1day.json at config seed 1 (instance.restrict_horizon to slow slots [60, 84), [66, 90), [136, 160),
[160, 190), where 'hog' meets buffer violations; needs the raw spot traces), each variant in turn. Half of the runs
mutate their instance: arcs pushed to infinity, to [q, 1.5 q) or below q/2 (groups split by routing costs), load
times with fractional milliseconds and near whole fast slots (in and next to the load-time corner), loading charges
scaled and shifted (beta > 0), prepaid terms that are not multiples of the fast slot, kappa_infinite flipped, demand
scaled, a second LLM added to one-LLM instances. Lender modes: trace, trace under I2, eager, adaptive, iid_step,
safe_site, correlated, trace with on_unavailable 'refuse' (I1 and I2), and with violations 'reclaim': trace (I1,
I2, and with 'refuse') and correlated; the spot windows draw only the 'reclaim' modes and the styles hog, mixed and
swap. A mode an instance does not admit (ConfigError) is counted and replaced by 'trace'. Style, mutation, lender
mode and EngineConfig(auto_drain) are drawn from a generator seeded by the run index, so the output is
deterministic.

Negative controls (reported, not part of the exit status): the three differences of the prototype that C3 §9 lists
under "Relation to the prototype" (rent rate without zeta_k; the all-fallback shortcut for r >= q_j under
kappa_infinite; entry cost with Lambda / 60 in place of Lambda-bar), each evaluated on every run; the output counts
the runs and slots at which the variant exceeds ALG(t) + tolerance, which shows that the fuzzed runs reach the
bound where these differences matter. The output also counts the tight slots, |ALG(t) - LB'(t)| <= tolerance with
LB'(t) > 0.

Usage: x10_g5p_pathwise.py [n_runs] [--reduced]   (default 20700 runs, 300 per instance variant, about 10 min;
--reduced: 345 runs). One worker.
Audit addendum of design/sublet_v2.md §5, step P6; code/sim/audit/, run by run_all.sh, output
code/sim/out/audit_fm/x10_out.txt. Exit status 1 on a violation, a step failure, an engine invariant failure or a
run that raises."""
import copy
import dataclasses
import json
import math
import sys
import time
import traceback
from collections import Counter

import numpy as np

import audit_env  # noqa: F401
from audit_env import SIM, TG
from sublet.config import ConfigError, lender_model, load_config, rng_streams
from sublet.engine import Engine, EngineConfig
from sublet.instance import build_instance, restrict_horizon, validate, with_demand
from sublet.lender import Lender
from sublet.policies.base import Policy
from sublet.types import Buy, Drain, LenderModel, Load, Release, SetAdmission, Stranding, Unload

TOL = 1e-9
CONTROLS = ("nozeta", "shortcut", "lam")
CONFIGS = SIM / "configs"
N_TOY, N_MS2, N_PROBE, N_RICH = 36, 16, 5, 8
SPOT_WINDOWS = ((60, 24), (66, 24), (136, 24), (160, 30))     # slow-slot windows of q44_spot_1day (seed 1)
STYLES = ("track", "random", "swap", "mixed", "exact")
SPOT_STYLES = ("hog", "hog", "mixed", "swap")
SPOT_MODES = ("reclaim", "corr_reclaim", "refuse_reclaim", "reclaimI2")
MODES = {
    "trace": {"schedule": "trace"},
    "traceI2": {"schedule": "trace", "information": "I2"},
    "eager": {"schedule": "eager"},
    "adaptive": {"schedule": "adaptive"},
    "iid": {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.3}},
    "safe": {"schedule": "safe_site", "params": {"D_slots": 2, "k": 2, "Phi": None}},
    "corr": {"schedule": "correlated", "params": {"p_sh": 1.0, "groups": "all"}},
    "refuse": {"schedule": "trace", "on_unavailable": "refuse"},
    "refuseI2": {"schedule": "trace", "on_unavailable": "refuse", "information": "I2"},
    "reclaim": {"schedule": "trace", "violations": "reclaim"},
    "corr_reclaim": {"schedule": "correlated", "violations": "reclaim", "params": {"p_sh": 1.0, "groups": "all"}},
    "refuse_reclaim": {"schedule": "trace", "on_unavailable": "refuse", "violations": "reclaim"},
    "reclaimI2": {"schedule": "trace", "violations": "reclaim", "information": "I2"},
}


# ================================================================ LB' from C3 §9 (full-model form)
def groups_of(q, cl, dl, m):
    """Groups of the text: per LLM j, the connected components with at least one site of the bipartite graph on the
    clients of j and the sites, edges the usable arcs (delta finite and < q_j). Returns [(j, clients, sites)]."""
    out = []
    for j in range(len(q)):
        cs = [int(c) for c in np.flatnonzero(np.asarray(cl) == j)]
        arcs = {c: [l for l in range(m) if math.isfinite(dl[c, l]) and dl[c, l] < q[j]] for c in cs}
        by_site = {}
        for c in cs:
            for l in arcs[c]:
                by_site.setdefault(l, []).append(c)
        seen = set()
        for c0 in cs:
            if c0 in seen or not arcs[c0]:
                continue
            comp_c, comp_s, stack = {c0}, set(), [("c", c0)]
            seen.add(c0)
            while stack:
                kind, v = stack.pop()
                if kind == "c":
                    for l in arcs[v]:
                        if l not in comp_s:
                            comp_s.add(l)
                            stack.append(("s", l))
                else:
                    for c in by_site[v]:
                        if c not in comp_c:
                            comp_c.add(c)
                            seen.add(c)
                            stack.append(("c", c))
            out.append((j, sorted(comp_c), sorted(comp_s)))
    return out


def zeta_of(P, Df):
    P = int(P)
    return 1.0 if P <= 0 else P / (math.ceil(P / Df) * Df)


def lam_ms_of(lam_s):
    """Rule T8: Lambda^ms = round(1000 Lambda) (half to even, as numpy's round of the float product)."""
    return np.array([[int(round(1000.0 * float(x))) for x in row] for row in np.asarray(lam_s, dtype=float)],
                    dtype=np.int64)


def theta_of(lam_ms, Df):
    return -(-lam_ms // (60000 * int(Df)))


def lb_prime(inst, variant=None):
    """LB'(t) of C3 §9 (full-model form) and the per-group data. Returns (LB (T_slow,), groups), each group a dict
    with j, clients, sites, r, q, bhat, d (T_fast,), n0 (T_fast,) or None, LBf (T_fast,) and LBs (T_slow,).
    variant (negative controls, the three differences of the prototype that C3 §9 lists under "Relation to the
    prototype"): 'nozeta' (rent rate without zeta_k), 'shortcut' (a group with r >= q_j on all-fallback also under
    kappa_infinite), 'lam' (entry cost with Lambda / 60 loading minutes in place of Lambda-bar)."""
    g = inst.grid
    Df, phi, Ts = int(g.fast_min), int(g.phi), int(g.T_slow)
    q = [float(x.q_usd_per_h) for x in inst.llms]
    gj = [int(x.g) for x in inst.llms]
    lam_s = np.asarray(inst.lam_s, dtype=float)
    lam_ms = lam_ms_of(lam_s)
    theta = theta_of(lam_ms, Df)
    Lbar = lam_s / 60.0 if variant == "lam" else np.minimum(lam_s / 60.0, theta * Df)
    zeta = [1.0 if variant == "nozeta" else zeta_of(c.prepaid_min, Df) for c in inst.contracts]
    D = np.asarray(inst.clients.demand, dtype=float)
    beta = np.asarray(inst.beta_usd, dtype=float)
    price = np.asarray(inst.price, dtype=float)
    LB = np.zeros(Ts)
    out = []
    for j, cs, ss in groups_of(q, inst.clients.llm, np.asarray(inst.clients.delta_usd_per_h, dtype=float), inst.m):
        r = min(zeta[k] * gj[j] * float(price[l, k]) for l in ss for k in inst.sites[l].menu)
        bhat = min(float(beta[j, l]) for l in ss) + r * min(float(Lbar[j, l]) for l in ss) / 60.0
        d = D[cs].sum(axis=0)
        qj = q[j]
        if inst.kappa_infinite and variant == "shortcut" and r >= qj:
            LBf, n0 = np.cumsum(qj * d) * Df / 60.0, None
        elif inst.kappa_infinite:
            e1 = np.cumsum(qj * d) * Df / 60.0
            e2 = bhat + np.cumsum(np.minimum(r, qj * d)) * Df / 60.0
            LBf, n0 = np.minimum(e1, e2), None
        else:
            if r < qj:
                fl = np.floor(d)
                n0 = (fl + (qj * (d - fl) > r)).astype(np.int64)
            else:
                n0 = np.zeros(d.shape, dtype=np.int64)
            nus = np.arange(int(n0.max()) + 1 if n0.size else 1)[:, None]
            n = np.minimum(nus, n0[None, :])
            h = n * r + qj * np.maximum(d[None, :] - n, 0.0)
            LBf = (nus * bhat + np.cumsum(h, axis=1) * Df / 60.0).min(axis=0)
        LBs = LBf[phi - 1::phi][:Ts]
        LB += LBs
        out.append(dict(j=j, clients=cs, sites=ss, r=r, q=qj, bhat=bhat, d=d, n0=n0, LBf=LBf, LBs=LBs))
    return LB, out


def corner_pairs(inst):
    """(j, l) in the load-time corner: Lambda^ms a multiple of 60000 Delta_f and 1000 Lambda > Lambda^ms."""
    lam_s = np.asarray(inst.lam_s, dtype=float)
    lam_ms = lam_ms_of(lam_s)
    Df = int(inst.grid.fast_min)
    return {(j, l) for j in range(inst.J) for l in range(inst.m)
            if lam_ms[j, l] % (60000 * Df) == 0 and 1000.0 * lam_s[j, l] > lam_ms[j, l]}


# ================================================================ instances (variant builders copied from check_g5p.py)
def _load(name):
    return json.load(open(CONFIGS / name))


def _toy_spec(i):
    rng = np.random.default_rng(5000 + i)
    cfg = _load("toy.json")
    cfg["name"] = f"toy_v{i}"
    cfg["seed"] = 100 + i
    if i == 0:
        return cfg
    if i == 1:
        cfg["llms"][0]["kappa_wtok_per_min"] = "inf"
        cfg["costs"]["kappa_infinite"] = True
        return cfg
    kinf = i % 2 == 1
    billing = ("prepaid_D", "per_slot", "commit_tau")[(i // 2) % 3]
    dear = (i // 6) % 2 == 1
    fast = 5 if i < 12 else 1
    T_slow = 24
    q = float(rng.uniform(4.0, 10.0))
    g = int(rng.choice([1, 2]))
    cfg["billing"] = billing
    cfg["time"] = {"slow_slot_min": 5, "fast_slot_min": fast, "horizon_min": 5 * T_slow, "start_minute_of_week": 0}
    cfg["prices"]["q_gpu_usd_per_gpu_h"] = q
    cfg["prices"]["a_protected_usd_per_gpu_h"] = float(rng.uniform(1.0, 1.6) * q if dear else
                                                       rng.uniform(0.3, 1.3) * q)
    cfg["contracts"] = [{"id": "short", "tau_min": 5, "H_min": int(rng.choice([0, 2, 5]))},
                        {"id": "long", "tau_min": int(rng.choice([5, 10, 15])), "H_min": int(rng.choice([0, 3, 10]))},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": int(rng.choice([5, 10]))}]
    cfg["llms"][0]["g"] = g
    lo, hi = (1.0, 1.6) if dear else (0.2, 0.9)
    for e in cfg["lenders"]:
        if e["kind"] == "synthetic":
            e["prices"] = {"short": float(rng.uniform(lo, hi) * q), "long": float(rng.uniform(lo, hi) * q)}
            e["capacity_gpus"] = [2, 4, 8, 64][int(rng.integers(4))]
            rate = float(rng.choice([0.1, 0.3, 0.6]))
            e["R"] = np.flatnonzero(rng.random(T_slow) < rate).astype(int).tolist()
            e["lam_s"] = float(rng.choice([0.0, 30.0, 150.0, 300.0, 600.0, 1200.0]))
        else:
            e["lam_s"] = float(rng.choice([0.0, 300.0, 900.0]))
    cfg["costs"]["beta_jl_usd"] = float(rng.choice([0.0, 0.02, 0.2, 1.0]))
    cfg["stranding"]["mu_over_beta_tilde"] = float(rng.choice([0.0, 0.5, 1.0]))
    cfg["stranding"]["kv_share"] = float(rng.choice([0.0, 0.5]))
    if kinf:
        cfg["llms"][0]["kappa_wtok_per_min"] = "inf"
        cfg["costs"]["kappa_infinite"] = True
    n_cl = 1 + int(rng.random() < 0.5)
    phi = 5 // fast
    clients = []
    for c in range(n_cl):
        lev = rng.choice([0.0, 0.4, 1.0, 1.5, 2.5, 3.7], size=T_slow, p=[0.3, 0.1, 0.2, 0.15, 0.15, 0.1])
        dem = np.repeat(lev, phi)
        if phi > 1:
            dem = dem * rng.uniform(0.7, 1.3, size=dem.size)
        scale = float(rng.choice([0.5, 1.0, 2.0]))
        clients.append({"llm": "M", "region": "r0", "slo_class": "strict", "borrowers": [f"b{c}"],
                        "demand": {"kind": "array", "values": [round(float(x) * scale, 6) for x in dem]}})
    cfg["borrowers"] = {"model": "explicit", "clients": clients}
    return cfg


def _ms2_spec(i):
    rng = np.random.default_rng(6000 + i)
    cfg = _load("ms2_multi_small.json")
    cfg["name"] = f"ms2_v{i}"
    cfg["seed"] = 200 + i
    if i in (0, 1):
        cfg["time"]["horizon_min"] = 120
        if i == 1:
            for x in cfg["llms"]:
                x["kappa_wtok_per_min"] = "inf"
            cfg["costs"]["kappa_infinite"] = True
        return cfg, None
    kinf = i % 2 == 1
    fast = 1 if i < 10 else 5
    cfg["time"]["fast_slot_min"] = fast
    cfg["time"]["horizon_min"] = int(rng.choice([60, 90])) if fast == 1 else int(rng.choice([120, 240]))
    cfg["billing"] = ("prepaid_D", "per_slot", "commit_tau")[i % 3]
    cfg["lender_defaults"]["offset"] = "random"
    cfg["prices"]["q_gpu_usd_per_gpu_h"] = float(rng.uniform(4.0, 12.0))
    cfg["stranding"]["mu_over_beta_tilde"] = float(rng.choice([0.0, 1.0]))
    cfg["stranding"]["kv_share"] = float(rng.choice([0.0, 0.3]))
    if kinf:
        for x in cfg["llms"]:
            x["kappa_wtok_per_min"] = "inf"
        cfg["costs"]["kappa_infinite"] = True
    pert = {"price_lo": 0.4, "price_hi": 3.0, "lam_hi": 3.0, "beta": float(rng.choice([0.0, 0.05, 0.5])),
            "demand_scale": float(rng.choice([0.5, 1.0, 2.0, 3.0])), "seed": 6500 + i}
    return cfg, pert


def _probe_spec(i):
    cfg = _load("toy.json")
    cfg["name"] = f"probe_v{i}"
    cfg["seed"] = 300 + i
    fast = 1 if i == 1 else 5
    phi = 5 // fast
    T_slow = 24
    kinf = i in (2, 3)
    H = 5 if kinf else 2
    price = 12.0 if kinf else 1.0
    cfg["billing"] = "per_slot" if i == 4 else "prepaid_D"
    cfg["time"] = {"slow_slot_min": 5, "fast_slot_min": fast, "horizon_min": 5 * T_slow, "start_minute_of_week": 0}
    cfg["prices"]["q_gpu_usd_per_gpu_h"] = 10.0
    cfg["prices"]["a_protected_usd_per_gpu_h"] = 12.0 if kinf else 5.0
    cfg["contracts"] = [{"id": "short", "tau_min": 5, "H_min": H},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": 5}]
    cfg["lenders"] = [{"id": "L0", "kind": "synthetic", "region": "r0", "group": "g0", "menu": ["short"],
                       "prices": {"short": price}, "capacity_gpus": 64, "R": [], "load_scenario": "explicit",
                       "lam_s": 0.0},
                      {"id": "P", "kind": "protected", "region": "r0", "group": "gp", "menu": ["prot"],
                       "capacity_gpus": None, "load_scenario": "explicit", "lam_s": 0.0}]
    cfg["costs"]["beta_jl_usd"] = 0.0
    cfg["stranding"]["mu_over_beta_tilde"] = 0.0
    if kinf:
        cfg["llms"][0]["kappa_wtok_per_min"] = "inf"
        cfg["costs"]["kappa_infinite"] = True
    n_cl = 2 if i == 2 else 1
    cfg["borrowers"] = {"model": "explicit", "clients": [
        {"llm": "M", "region": "r0", "slo_class": "strict", "borrowers": [f"b{c}"],
         "demand": {"kind": "array", "values": [1.0] * (T_slow * phi)}} for c in range(n_cl)]}
    return cfg


def _perturb(inst, pert):
    """check_g5p.py's instance perturbation (prices, load times, loading charges, demand scale)."""
    if not pert:
        return inst
    rng = np.random.default_rng(pert["seed"])
    pr = np.array(inst.price, dtype=np.float64, copy=True)
    fac = rng.uniform(pert["price_lo"], pert["price_hi"], size=pr.shape)
    inst = dataclasses.replace(inst, price=np.where(np.isfinite(pr), pr * fac, pr),
                               lam_s=np.asarray(inst.lam_s, dtype=np.float64) * rng.uniform(0.0, pert["lam_hi"],
                                                                                           size=inst.lam_s.shape),
                               beta_usd=np.asarray(inst.beta_usd, dtype=np.float64) + pert["beta"])
    validate(inst)
    s = pert.get("demand_scale", 1.0)
    if s != 1.0:
        inst = with_demand(inst, np.asarray(inst.clients.demand) * s)
    return inst


_BASE = {}


def base_instance(fam, i):
    """(instance, default LenderModel, lender seed); cached per (family, variant)."""
    key = (fam, i)
    if key not in _BASE:
        if fam == "toy":
            cfg, pert = _toy_spec(i), None
        elif fam == "ms2":
            cfg, pert = _ms2_spec(i)
        elif fam == "probe":
            cfg, pert = _probe_spec(i), None
        if fam == "rich":
            inst = TG._rich_instance(3 + i, i, False)
            model = LenderModel(schedule="trace")
        elif fam == "spot":
            inst = restrict_horizon(TG._full("q44_spot_1day", 1), *SPOT_WINDOWS[i])
            model = LenderModel(schedule="trace")
        else:
            inst = _perturb(build_instance(copy.deepcopy(cfg)), pert)
            model = lender_model(load_config(copy.deepcopy(cfg)))
        _BASE[key] = (inst, model, int(inst.seed))
    return _BASE[key]


def add_llm(inst, rng):
    """A second LLM (copy of LLM 0 with g in {1, 2}, q = g q_GPU, its own load times and loading charges) serving a
    random half of the clients (at least one client keeps LLM 0 when there are two or more)."""
    x = inst.llms[0]
    g2 = int(rng.choice([1, 2]))
    llm2 = dataclasses.replace(x, id="M_x", g=g2, q_usd_per_h=float(g2 * inst.q_gpu_usd_per_h))
    lam2 = np.asarray(inst.lam_s, dtype=float)[0] * rng.uniform(0.3, 1.7, size=inst.m)
    beta2 = np.asarray(inst.beta_usd, dtype=float)[0] * rng.uniform(0.5, 1.5) + float(rng.choice([0.0, 0.05]))
    st = inst.stranding
    st2 = Stranding(*(np.append(np.asarray(getattr(st, k), dtype=float), getattr(st, k)[0])
                      for k in ("mu_kv_usd", "mu_fl_usd", "mu_fb_usd", "pi_usd_per_min")), W_f_min=st.W_f_min)
    cl = np.array(inst.clients.llm, dtype=np.int64, copy=True)
    n = inst.n
    sel = rng.random(n) < 0.5
    if n >= 2:
        sel[int(rng.integers(n))] = False
        if not sel.any():
            sel[int(rng.integers(n))] = True
    cl[sel] = 1
    dl = np.array(inst.clients.delta_usd_per_h, dtype=float, copy=True)
    q2 = llm2.q_usd_per_h
    dl[sel] = np.where(np.isfinite(dl[sel]), np.minimum(dl[sel] * q2 / x.q_usd_per_h, 1e6), dl[sel])
    return dataclasses.replace(inst, llms=(x, llm2), lam_s=np.vstack([inst.lam_s, lam2]),
                               beta_usd=np.vstack([inst.beta_usd, beta2]), stranding=st2,
                               clients=dataclasses.replace(inst.clients, llm=cl, delta_usd_per_h=dl))


def mutate(inst, rng):
    """Instance mutation of the module docstring."""
    if inst.J == 1 and rng.random() < 0.6:
        inst = add_llm(inst, rng)
    m, n, J = inst.m, inst.n, inst.J
    q = np.array([x.q_usd_per_h for x in inst.llms])
    cl = np.asarray(inst.clients.llm)
    dl = np.array(inst.clients.delta_usd_per_h, dtype=np.float64, copy=True)
    for c in range(n):
        for l in range(m):
            u = rng.random()
            if u < 0.2:
                dl[c, l] = np.inf
            elif u < 0.3:
                dl[c, l] = q[cl[c]] * rng.uniform(1.0, 1.5)
            elif u < 0.5:
                dl[c, l] = q[cl[c]] * rng.uniform(0.0, 0.5)
    Df = int(inst.grid.fast_min)
    lam = np.asarray(inst.lam_s, dtype=np.float64) * rng.uniform(0.0, 2.0, size=(J, m))
    lam = np.round(lam, 3) + rng.choice([0.0, 0.0001, 0.00025, 0.0005, 0.0007, 0.12345], size=(J, m))
    near = rng.random((J, m)) < 0.4
    k = rng.integers(0, 4, size=(J, m))
    off = rng.choice([-0.0004, 0.0003, 0.0004, 0.00049, 0.0006], size=(J, m))
    lam = np.maximum(np.where(near, 60.0 * Df * k + off, lam), 0.0)
    beta = np.asarray(inst.beta_usd, dtype=np.float64) * rng.uniform(0.0, 2.0) + rng.choice([0.0, 0.01, 0.3])
    kw = dict(clients=dataclasses.replace(inst.clients, delta_usd_per_h=dl), lam_s=lam, beta_usd=beta)
    if rng.random() < 0.7:
        cs = []
        for ct in inst.contracts:
            P = int(ct.prepaid_min)
            if rng.random() < 0.6:
                P = int(rng.choice([1, 2, 3, 4, 6, 7, 8, 11, 13, 17, 23]))
            cs.append(dataclasses.replace(ct, prepaid_min=P))
        kw["contracts"] = tuple(cs)
    if rng.random() < 0.3:
        kw["kappa_infinite"] = not inst.kappa_infinite
    if rng.random() < 0.3:
        kw["clients"] = dataclasses.replace(kw["clients"], demand=np.asarray(inst.clients.demand) *
                                            float(rng.choice([0.3, 2.0, 3.5])))
    out = dataclasses.replace(inst, **kw)
    validate(out)
    return out


# ================================================================ the policy fuzzer
class Fuzz(Policy):
    """Policy fuzzer of the module docstring. Never names an object that an earlier action of its own list has
    released or unloaded (the engine raises on those), so every list is well formed."""
    name = "fuzz"

    def __init__(self, seed, style):
        self.seed, self.style = int(seed), style

    def reset(self, view, rng):
        super().reset(view, rng)
        self.r = np.random.default_rng(self.seed)
        self.wants_fast = self.style not in ("track", "exact")
        v = view
        self.q = [float(x.q_usd_per_h) for x in v.llms]
        self.g = [int(x.g) for x in v.llms]
        self.groups = groups_of(self.q, v.client_llm, np.asarray(v.client_delta_usd_per_h, dtype=float), len(v.sites))
        Df = v.grid.fast_min
        self.cheap = []
        for j, cs, ss in self.groups:
            best = min(((zeta_of(v.contracts[k].prepaid_min, Df) * float(v.price[l, k]), l, k)
                        for l in ss for k in v.sites[l].menu), default=None)
            self.cheap.append(best)
        self.live = {}
        self.n_fast_acts = 0

    def act(self, obs):
        v, r = self.view, self.r
        Ds, Df, J = v.grid.slow_min, v.grid.fast_min, len(v.llms)
        minute = int(obs.minute)
        leases = obs.leases
        reps = {rid: rv for rid, rv in obs.replicas.items() if rv.lease_id in leases}
        dead_l, dead_r = set(), set()
        free = {lid: L.gpus - sum(self.g[reps[x].llm] for x in L.replicas if x in reps) for lid, L in leases.items()}
        acts = []

        def alive_l():
            return sorted(l for l in leases if l not in dead_l)

        def alive_r():
            return sorted(x for x in reps if x not in dead_r)

        def release(lid):
            acts.append(Release(lid))
            dead_l.add(lid)
            dead_r.update(x for x in reps if reps[x].lease_id == lid)

        def unload(rid):
            acts.append(Unload(rid))
            dead_r.add(rid)
            free[reps[rid].lease_id] += self.g[reps[rid].llm]

        def load(lid, j):
            acts.append(Load(lid, j))
            if free[lid] >= self.g[j]:
                free[lid] -= self.g[j]

        st = self.style
        if st == "exact":
            # the lower bound's own plan: per group the slot's peak demand rounded up (one replica under
            # kappa_infinite), bought on the cheapest zeta-adjusted contract with admission 1, every lease released at
            # the first slot whose first fast slot would pay rent (rule T7: rent from ceil(prepaid end / Delta_f))
            for lid in alive_l():
                if -(-leases[lid].prepaid_end_min // Df) * Df <= minute:
                    release(lid)
            for gi, (j, cs, ss) in enumerate(self.groups):
                dmax = float(obs.demand[cs].max(axis=1).sum()) if cs else 0.0
                tgt = min(1, int(math.ceil(dmax - 1e-12))) if v.kappa_infinite else int(math.ceil(dmax - 1e-12))
                have = sum(1 for x in alive_r() if reps[x].llm == j and leases[reps[x].lease_id].site in ss)
                if tgt > have and self.cheap[gi] is not None and self.cheap[gi][0] * self.g[j] < self.q[j]:
                    _, l, k = self.cheap[gi]
                    acts.append(Buy(int(l), int(k), int(j), int(tgt - have)))
        if st in ("track", "mixed"):
            for gi, (j, cs, ss) in enumerate(self.groups):
                dmax = float(obs.demand[cs].max(axis=1).sum()) if cs else 0.0
                tgt = int(math.ceil(dmax * float(r.choice([0.5, 1.0, 1.0, 1.5]))))
                if v.kappa_infinite:
                    tgt = min(tgt, 1 + int(r.random() < 0.2))
                have = sum(1 for x in alive_r() if reps[x].llm == j and leases[reps[x].lease_id].site in ss)
                if tgt > have and self.cheap[gi] is not None:
                    hosts = [l for l in alive_l() if leases[l].site in ss and free[l] >= self.g[j]]
                    if hosts and r.random() < 0.4:
                        load(int(r.choice(hosts)), j)
                        continue
                    _, l, k = self.cheap[gi]
                    if r.random() < 0.3:
                        l = int(r.choice(ss))
                        k = int(r.choice(sorted(v.sites[l].menu)))
                    acts.append(Buy(int(l), int(k), int(j), int(min(tgt - have, 4)),
                                    admission=float(r.choice([1.0, 1.0, 0.5, 0.3]))))
            for lid in alive_l():
                L = leases[lid]
                if (L.prepaid_end_min <= minute + Ds and r.random() < 0.7) or r.random() < 0.04:
                    release(lid)
        if st == "hog":
            held = {}
            for lid in alive_l():
                held[leases[lid].site] = held.get(leases[lid].site, 0) + leases[lid].gpus
            for l, site in enumerate(v.sites):
                if site.kind == "protected":
                    continue
                j = int(r.integers(J))
                room = site.capacity_gpus - held.get(l, 0)
                if self.g[j] <= room:
                    k = min(site.menu, key=lambda k: float(v.price[l, k]))
                    nb = int(min(room // self.g[j], 3))
                    acts.append(Buy(l, int(k), j, nb, admission=float(r.choice([1.0, 1.0, 0.5]))))
                    held[l] = held.get(l, 0) + nb * self.g[j]
        if st in ("random", "mixed") or (st == "hog" and r.random() < 0.33):
            for _ in range(int(r.integers(0, 5))):
                u = r.random()
                al, ar = alive_l(), alive_r()
                if u < 0.3:
                    l = int(r.integers(len(v.sites)))
                    acts.append(Buy(l, int(r.choice(sorted(v.sites[l].menu))), int(r.integers(J)),
                                    int(r.integers(1, 4)), admission=float(r.choice([0.0, 0.3, 1.0]))))
                elif u < 0.48 and al:
                    load(int(r.choice(al)), int(r.integers(J)))
                elif u < 0.6 and ar:
                    unload(int(r.choice(ar)))
                elif u < 0.72 and al:
                    release(int(r.choice(al)))
                elif u < 0.86 and ar:
                    acts.append(SetAdmission(int(r.choice(ar)), float(r.choice([0.0, 0.25, 0.5, 1.0]))))
                elif ar:
                    acts.append(Drain(int(r.choice(ar)), int(minute + r.integers(0, 3 * Ds))))
        if st in ("swap", "mixed"):
            ar = alive_r()
            if ar and r.random() < 0.6:
                rid = int(r.choice(ar))
                lid = reps[rid].lease_id
                unload(rid)
                others = [j for j in range(J) if j != reps[rid].llm] or [reps[rid].llm]
                load(lid, int(r.choice(others)))
            for lid in alive_l():
                if free[lid] > 0 and r.random() < 0.5:
                    load(lid, int(r.integers(J)))
            if r.random() < 0.5:
                l = int(r.integers(len(v.sites)))
                acts.append(Buy(l, int(r.choice(sorted(v.sites[l].menu))), int(r.integers(J)), int(r.integers(2, 4)),
                                admission=float(r.choice([0.3, 1.0]))))
            if st == "swap" and r.random() < 0.3:
                for lid in alive_l():
                    if leases[lid].prepaid_end_min > minute and r.random() < 0.5:
                        release(lid)
        # replicas on which on_fast may act during this slot: end minute of their lease (death or horizon)
        T_min = v.grid.T_slow * Ds
        self.live = {x: (leases[reps[x].lease_id].death_min if leases[reps[x].lease_id].death_min is not None
                         else T_min) for x in alive_r()}
        self.lease_end = {l: (minute if l in dead_l else leases[l].death_min if leases[l].death_min is not None
                              else T_min) for l in leases}
        return acts

    def on_fast(self, obs):
        v, r = self.view, self.r
        Df = v.grid.fast_min
        T_min = v.grid.T_slow * v.grid.slow_min
        for res in obs.results:
            if res.ok and isinstance(res.action, (Buy, Load)):
                end = T_min if isinstance(res.action, Buy) else self.lease_end.get(res.lease_id, T_min)
                for x in res.replica_ids:
                    self.live[int(x)] = end
        f = int(obs.f)
        cand = sorted(x for x, end in self.live.items() if (f + 1) * Df <= end)
        out = []
        if cand and r.random() < 0.3:
            for _ in range(int(r.integers(1, 3))):
                x = int(r.choice(cand))
                if r.random() < 0.5:
                    out.append(SetAdmission(x, float(r.choice([0.0, 0.3, 0.5, 1.0]))))
                else:
                    out.append(Drain(x, int((f + int(r.integers(1, 4))) * Df)))
        self.n_fast_acts += len(out)
        return out


# ================================================================ checks of one run
def check_run(inst, res, st, tag, bad):
    """LB' against ALG and the proof steps; updates the counters st and the failure list bad. Returns the run's
    minimum slack (absolute, relative)."""
    g = inst.grid
    Df, phi, Ts, Tf, Ds = int(g.fast_min), int(g.phi), int(g.T_slow), int(g.T_fast), int(g.slow_min)
    ft = (np.arange(Ts) + 1) * phi - 1
    tot = np.asarray(res.per_slot["total"], dtype=float)
    ALG = np.cumsum(tot)
    LB, groups = lb_prime(inst)

    def fail(kind, detail):
        st["fail:" + kind] += 1
        if len(bad) < 40:
            bad.append((kind, tag, detail))

    def tolv(x):
        return TOL * np.maximum(1.0, np.abs(x))

    # the claim
    st["slots"] += Ts
    slack = ALG - LB
    rel = slack / np.maximum(1.0, ALG)
    viol = np.flatnonzero(-slack > tolv(ALG))
    tight = int(np.sum((np.abs(slack) <= tolv(ALG)) & (LB > TOL)))
    st["tight slots"] += tight
    st["runs with a tight slot"] += int(tight > 0)
    st["violations"] += len(viol)
    for t in viol[:3]:
        fail("CLAIM ALG(t) >= LB'(t)", f"t={int(t)} ALG={ALG[t]!r} LB'={LB[t]!r}")
    # engine invariants and the ledger
    for s in res.invariant_failures:
        fail("engine invariant", s)
    comp = sum(np.asarray(res.per_slot[c], dtype=float) for c in
               ("lease_prepaid", "lease_rent", "loading", "routing", "fallback", "stranding_kv", "stranding_fl",
                "stranding_fb", "stranding_pi"))
    if np.any(np.abs(comp - tot) > tolv(tot)):
        fail("ledger total != sum of components", f"max diff {np.max(np.abs(comp - tot))!r}")
    st["checks:ledger"] += Ts

    price = np.asarray(inst.price, dtype=float)
    zeta = [zeta_of(c.prepaid_min, Df) for c in inst.contracts]
    gj = [int(x.g) for x in inst.llms]
    lam_ms = lam_ms_of(inst.lam_s)
    theta = theta_of(lam_ms, Df)
    # step 1: lease charges
    lease_by_id = {L.id: L for L in res.leases}
    charge_slot = np.zeros(Ts)
    alive_iv = {}
    for L in res.leases:
        a = float(price[L.site, L.contract])
        c = inst.contracts[L.contract]
        f_lo = L.start_min // Df
        f_hi = min(L.end_min // Df, Tf)
        alive_iv[L.id] = (f_lo, max(f_lo, f_hi))
        rent_from = max(L.start_slot * phi, -(-(L.start_min + c.prepaid_min) // Df))
        per = np.zeros(Ts)
        pre = L.gpus * a * c.prepaid_min / 60.0
        per[L.start_slot] += pre
        rf = np.arange(max(rent_from, f_lo), max(f_lo, f_hi))
        np.add.at(per, rf // phi, L.gpus * a * Df / 60.0)
        charge_slot += per
        if abs(pre - L.prepaid_usd) > TOL * max(1.0, pre) or \
                abs(len(rf) * L.gpus * a * Df / 60.0 - L.rent_usd) > TOL * max(1.0, L.rent_usd):
            fail("step 1: lease record != rule T7", f"lease {L.id} prepaid {L.prepaid_usd!r}/{pre!r} rent "
                                                     f"{L.rent_usd!r}/{len(rf) * L.gpus * a * Df / 60.0!r}")
        cum = np.cumsum(per)
        n_al = np.clip(ft + 1 - f_lo, 0, max(0, f_hi - f_lo))
        lower = zeta[L.contract] * L.gpus * a * Df / 60.0 * n_al
        st["checks:step1"] += Ts
        if np.any(lower - cum > tolv(cum)):
            t = int(np.argmax(lower - cum))
            fail("step 1: lease charges >= zeta G a Df/60 |A_L n [0,f_t]|", f"lease {L.id} t={t} {cum[t]!r} < {lower[t]!r}")
    led = np.asarray(res.per_slot["lease_prepaid"], dtype=float) + np.asarray(res.per_slot["lease_rent"], dtype=float)
    if np.any(np.abs(charge_slot - led) > tolv(led)):
        fail("step 1: recomputed lease charges != ledger", f"max diff {np.max(np.abs(charge_slot - led))!r}")
    # steps 2 and 3: GPUs per lease, existence and warm-up
    use = {L.id: np.zeros(Tf + 1, dtype=np.int64) for L in res.leases}
    for rp in res.replicas:
        L = lease_by_id[rp.lease_id]
        lo, hi = alive_iv[L.id]
        x0 = rp.load_start_min // Df
        x1 = min(rp.end_fast, Tf)
        st["checks:step2"] += 1
        if x1 > x0 and (x0 < lo or x1 > hi):
            fail("step 2: replica exists outside its lease's alive slots", f"replica {rp.id} [{x0},{x1}) lease [{lo},{hi})")
        if x1 > x0:
            use[L.id][x0] += gj[rp.llm]
            use[L.id][x1] -= gj[rp.llm]
        st["checks:step3"] += 1
        if rp.warm_fast != (rp.load_start_min // Ds) * phi + int(theta[rp.llm, L.site]):
            fail("step 3: warm_fast != t_rho phi + theta", f"replica {rp.id} warm {rp.warm_fast} theta "
                                                          f"{int(theta[rp.llm, L.site])}")
    for L in res.leases:
        u = np.cumsum(use[L.id])[:Tf]
        if np.any(u > L.gpus):
            fail("step 2: replicas use more GPUs than their lease", f"lease {L.id} max {int(u.max())} > {L.gpus}")
    # steps 4-6 per group
    b = np.asarray(res.routing["b"], dtype=float)
    attributed = np.zeros(Ts)
    for gr in groups:
        j, cs, ss, r, qj, bhat = gr["j"], gr["clients"], set(gr["sites"]), gr["r"], gr["q"], gr["bhat"]
        y = np.zeros(Tf + 1)
        A = np.zeros(Ts)
        first_warm = []
        for rp in res.replicas:
            L = lease_by_id[rp.lease_id]
            if rp.llm != j or L.site not in ss:
                continue
            x0, x1 = rp.load_start_min // Df, min(rp.end_fast, Tf)
            w0 = max(rp.warm_fast, x0)
            if w0 >= x1:
                continue
            y[w0] += 1
            y[x1] -= 1
            first_warm.append(w0)
            share = zeta[L.contract] * gj[j] * float(price[L.site, L.contract]) * Df / 60.0
            ex = np.clip(ft + 1 - x0, 0, x1 - x0)
            A += np.where(ft >= w0, rp.beta_usd + share * ex, 0.0)
        y = np.cumsum(y)[:Tf]
        d = gr["d"]
        fb = qj * b[cs].sum(axis=0)
        psi = qj * np.maximum(d - y, 0.0) if not inst.kappa_infinite else qj * d * (y == 0)
        st["checks:step4"] += Tf
        if np.any(psi - fb > tolv(psi)):
            f = int(np.argmax(psi - fb))
            fail("step 4: fallback of the group >= psi", f"group j={j} sites {sorted(ss)} f={f} {fb[f]!r} < {psi[f]!r}")
        fbc = np.cumsum(fb)[ft] * Df / 60.0
        A += fbc
        fw = np.sort(np.array(first_warm, dtype=np.int64))
        V = np.searchsorted(fw, ft, side="right")
        S5 = V * bhat + np.cumsum(r * y + psi)[ft] * Df / 60.0
        st["checks:step5"] += Ts
        if np.any(S5 - A > tolv(A)):
            t = int(np.argmax(S5 - A))
            fail("step 5: attributed >= V bhat + sum (r y + psi)", f"group j={j} t={t} {A[t]!r} < {S5[t]!r}")
        if np.any(gr["LBs"] - S5 > tolv(S5)):
            t = int(np.argmax(gr["LBs"] - S5))
            fail("step 5: V bhat + sum (r y + psi) >= LB'_Gamma", f"group j={j} t={t} {S5[t]!r} < {gr['LBs'][t]!r}")
        if gr["n0"] is not None:
            N = int(math.ceil(float(d.max()))) + 2 if d.size else 2
            ns = np.arange(N + 1)[:, None]
            H = ns * r + qj * np.maximum(d[None, :] - ns, 0.0)
            cm = np.minimum.accumulate(H, axis=0)
            n = np.minimum(ns, gr["n0"][None, :])
            Hn = n * r + qj * np.maximum(d[None, :] - n, 0.0)
            st["checks:step5 n°"] += cm.size
            if np.any(np.abs(cm - Hn) > TOL * np.maximum(1.0, np.abs(cm))):
                fail("step 5: min_{n<=nu} h(n) == h(min(nu, n°))", f"group j={j}")
        attributed += A
    st["checks:step6"] += Ts
    if np.any(attributed - ALG > tolv(ALG)):
        t = int(np.argmax(attributed - ALG))
        fail("step 6: sum of attributed charges <= ALG(t)", f"t={t} {attributed[t]!r} > {ALG[t]!r}")
    for var in CONTROLS:
        LBv, _ = lb_prime(inst, var)
        ex = np.max(LBv - ALG - tolv(ALG))
        if ex > 0:
            st[f"control {var} runs"] += 1
            st[f"control {var} slots"] += int(np.sum(LBv - ALG > tolv(ALG)))
    i = int(np.argmin(slack))
    j = int(np.argmin(rel))
    return float(slack[i]), float(rel[j]), groups


# ================================================================ one run
def run_spec(s):
    """Fixed run list: the family variant cycles with the run index; style, mutation, lender mode and auto_drain are
    drawn from a generator seeded by the run index."""
    fams = [("toy", i) for i in range(N_TOY)] + [("ms2", i) for i in range(N_MS2)] + \
           [("probe", i) for i in range(N_PROBE)] + [("rich", i) for i in range(N_RICH)] + \
           [("spot", i) for i in range(len(SPOT_WINDOWS))]
    fam, i = fams[s % len(fams)]
    rng = np.random.default_rng(70000 + s)
    style = str(rng.choice(SPOT_STYLES if fam == "spot" else STYLES))
    mut = bool(rng.random() < 0.5)
    mode = str(rng.choice(SPOT_MODES if fam == "spot" else list(MODES)))
    return fam, i, style, mut, mode, bool(rng.random() < 0.5)


def one_run(s, st, bad, worst):
    fam, i, style, mut, mode, ad = run_spec(s)
    inst, model0, ls = base_instance(fam, i)
    rng = np.random.default_rng(90000 + s)
    if mut:
        inst = mutate(inst, rng)
    tag = f"run {s} {fam}_v{i} style={style} mut={int(mut)} mode={mode} auto_drain={int(ad)}"
    pol = Fuzz(80000 + s, style)
    model = LenderModel(**MODES[mode])
    try:
        lender = Lender(inst, model, rng_streams(ls + s)["lender"])
    except ConfigError:
        st[f"mode skipped: {mode}"] += 1
        mode, model = "trace", LenderModel(schedule="trace")
        lender = Lender(inst, model, rng_streams(ls + s)["lender"])
    res = Engine(inst, lender, pol, EngineConfig(check_invariants=True, record_routing=True, auto_drain=ad),
                 rng_streams(s)["policy"]).run()
    smin, rmin, groups = check_run(inst, res, st, tag, bad)
    # features
    st["runs"] += 1
    st[f"family {fam}"] += 1
    st[f"style {style}"] += 1
    st[f"mode {mode}"] += 1
    st["mutated"] += int(mut)
    st["auto_drain"] += int(ad)
    kinf = bool(inst.kappa_infinite)
    st["kappa_infinite"] += int(kinf)
    st["capacitated"] += int(not kinf)
    st["several groups"] += int(len(groups) >= 2)
    per_llm = Counter(gr["j"] for gr in groups)
    st["an LLM with several groups (split)"] += int(any(v >= 2 for v in per_llm.values()))
    st["several LLMs"] += int(inst.J >= 2)
    Df = int(inst.grid.fast_min)
    offered = {k for s_ in inst.sites for k in s_.menu}
    st["Delta_f not dividing an offered P_k"] += int(any(zeta_of(inst.contracts[k].prepaid_min, Df) < 1.0
                                                         for k in offered))
    st["leases with zeta_k < 1"] += sum(1 for L in res.leases if zeta_of(inst.contracts[L.contract].prepaid_min, Df) < 1)
    corner = corner_pairs(inst)
    st["load-time corner in instance"] += int(bool(corner))
    lease_by_id = {L.id: L for L in res.leases}
    loads = [rp for rp in res.replicas if rp.load_start_min > lease_by_id[rp.lease_id].start_min]
    st["Loads accepted (replica loaded after its lease's purchase)"] += len(loads)
    st["runs with an accepted Load"] += int(bool(loads))
    st["replicas loaded in the load-time corner"] += sum(1 for rp in res.replicas
                                                         if (rp.llm, lease_by_id[rp.lease_id].site) in corner)
    llms_on = {}
    for rp in res.replicas:
        llms_on.setdefault(rp.lease_id, set()).add(rp.llm)
    st["leases with several LLMs over their life"] += sum(1 for v in llms_on.values() if len(v) >= 2)
    multi_rep = Counter((rp.lease_id) for rp in res.replicas if rp.load_start_min == lease_by_id[rp.lease_id].start_min)
    st["leases bought with several replicas"] += sum(1 for v in multi_rep.values() if v >= 2)
    sim = 0
    for lid, js in llms_on.items():
        if len(js) < 2:
            continue
        rs = [rp for rp in res.replicas if rp.lease_id == lid]
        for a in rs:
            if any(b_.llm != a.llm and max(a.load_start_min // Df, b_.load_start_min // Df) < min(a.end_fast, b_.end_fast)
                   for b_ in rs):
                sim += 1
                break
    st["leases with several LLMs at once"] += sim
    ev = Counter(e[1] for e in res.events)
    for k in ("unload", "release", "drain", "admission", "refuse", "announce"):
        st[f"events {k}"] += ev.get(k, 0)
    st["releases inside the prepaid region"] += sum(1 for L in res.leases if L.release_min is not None
                                                    and L.release_min < L.prepaid_end_min)
    st["violation victims"] += sum(len(v.get("victims", [])) for v in res.violations)
    st["on_fast actions"] += pol.n_fast_acts
    st["routing LP calls"] += int(res.runtime.get("routing_lp_calls", 0))
    if smin < worst["abs"][0]:
        worst["abs"] = (smin, tag)
    if rmin < worst["rel"][0]:
        worst["rel"] = (rmin, tag)
    fk = f"family {fam}"
    worst.setdefault(fk, (np.inf, ""))
    if rmin < worst[fk][0]:
        worst[fk] = (rmin, tag)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reduced = "--reduced" in sys.argv
    n_runs = int(args[0]) if args else (345 if reduced else 20700)
    t0 = time.time()
    st, bad = Counter(), []
    worst = {"abs": (np.inf, ""), "rel": (np.inf, "")}
    errors = []
    for s in range(n_runs):
        try:
            one_run(s, st, bad, worst)
        except Exception as e:  # a run that cannot be checked is a failure of the audit
            errors.append((s, run_spec(s), f"{type(e).__name__}: {e}", traceback.format_exc(limit=3)))
    wall = time.time() - t0
    nfail = sum(v for k, v in st.items() if k.startswith("fail:") and not k.startswith("fail:CLAIM"))
    L = ["X10: Lemma G5'(c) pathwise, ALG(t) >= LB'(t) at every slow slot of every engine run "
         "(design/theory/c3_c4_c5_general.md §9, Lemma G5'(c); audit addendum, design/sublet_v2.md §5 step P6)",
         "oracle: LB' from the text's full-model definition, computed independently in this script (not online_lb.py, "
         "not the prototype lb.py); proof steps 1-6 checked from the run's records; script code/sim/audit/"
         "x10_g5p_pathwise.py",
         f"runs: {st['runs']} of {n_runs} ({'reduced' if reduced else 'default'}), slow slots checked: {st['slots']}, "
         f"run errors: {len(errors)}, wall time {wall:.0f} s on one worker",
         f"tolerance: violation iff LB'(t) - ALG(t) > {TOL:g} max(1, ALG(t))", ""]
    L.append("runs by family, style, lender mode:")
    for pre in ("family ", "style ", "mode ", "mode skipped: "):
        L.append(f"  {pre.strip(' :')}: " + (", ".join(f"{k[len(pre):]} {v}" for k, v in sorted(st.items())
                                                     if k.startswith(pre) and not (pre == "mode " and
                                                                                   k.startswith("mode skipped")))
                                             or "none"))
    L.append("features (runs, unless the line counts objects):")
    for k in ("mutated", "auto_drain", "kappa_infinite", "capacitated", "several groups",
              "an LLM with several groups (split)", "several LLMs", "Delta_f not dividing an offered P_k",
              "leases with zeta_k < 1", "load-time corner in instance", "replicas loaded in the load-time corner",
              "runs with an accepted Load", "Loads accepted (replica loaded after its lease's purchase)",
              "leases bought with several replicas", "leases with several LLMs over their life",
              "leases with several LLMs at once", "releases inside the prepaid region", "events unload",
              "events release", "events drain", "events admission", "on_fast actions", "events refuse",
              "events announce", "violation victims", "routing LP calls"):
        L.append(f"  {k}: {st[k]}")
    L.append("negative controls (the prototype's three differences; LB' variant above ALG(t) + tolerance at some slot):")
    for var in CONTROLS:
        L.append(f"  {var}: runs {st[f'control {var} runs']}, slots {st[f'control {var} slots']}")
    L.append("checks (evaluations):")
    L.append("  " + ", ".join(f"{k[len('checks:'):]} {v}" for k, v in sorted(st.items()) if k.startswith("checks:")))
    L.append(f"tight slots (|ALG(t) - LB'(t)| <= tolerance with LB'(t) > 0): {st['tight slots']} in "
             f"{st['runs with a tight slot']} runs")
    L.append(f"minimum slack ALG(t) - LB'(t): {worst['abs'][0]:.6e} ({worst['abs'][1]})")
    L.append(f"minimum relative slack (ALG(t) - LB'(t)) / max(1, ALG(t)): {worst['rel'][0]:.6e} ({worst['rel'][1]})")
    for k in sorted(x for x in worst if x.startswith("family ")):
        L.append(f"  {k}: minimum relative slack {worst[k][0]:.6e} ({worst[k][1]})")
    L.append("failures by kind: " + (", ".join(f"{k[5:]} {v}" for k, v in sorted(st.items()) if k.startswith("fail:"))
                                     or "none"))
    for kind, tag, detail in bad[:20]:
        L.append(f"  FAIL {kind}: {tag}: {detail}")
    for s, spec, msg, tb in errors[:10]:
        L.append(f"  ERROR run {s} {spec}: {msg}")
        L.append("    " + tb.strip().replace("\n", "\n    "))
    L.append(f"step and invariant failures: {nfail}")
    L.append(f"violations: {st['violations']}")
    print("\n".join(L), flush=True)
    return int(st["violations"] > 0 or nfail > 0 or len(errors) > 0)


if __name__ == "__main__":
    if main():   # exit status 1 on a violation, a step failure or a run error (run_all.sh counts it)
        print("x10: a violation of ALG(t) >= LB'(t), a failed proof step or a run error", file=sys.stderr)
        sys.exit(1)
