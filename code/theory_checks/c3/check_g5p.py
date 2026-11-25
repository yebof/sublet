"""Numerical check of the proposed Lemma G5' (online lower bound LB'(T) <= OPT(sigma, omega)).

Claim and source. design/sublet_v2.md §2.5 (pilot-gated alternative allowance of D2: B(t) = min{W_k(t), LB'(t)},
kappa = 1) and §5 rows P2a and P2: "Lemma G5' (LB' <= OPT(sigma, omega) in the full model) has only a sketch". The
statement and the sketch are the docstring of the prototype code/sim/sublet/experiments/ms5b_proto/lb.py (a copy of
dev:guard_allowance/lb.py): per LLM j, groups g = connected components of the bipartite graph of arcs (client c of j,
site l) with delta_cl finite and < q_j; r_g = min over the group's sites and offered contracts of g_j a_lk; K_g =
beta_g + r_g lambda_g / 60 (minima over the group's sites); c_f(n) = n r_g + q_j (d_g(f) - n)^+, or with
kappa_infinite c_f(n) = q_j d_g(f) [n = 0] + r_g [n >= 1]; LB_g(t) = min over N >= 0 of N K_g + sum_{f <= t}
c_f(min(N, n_f)) Delta_f / 60; LB'(t) = sum_g LB_g(t). The sketch's rent step: each warm replica pays at least r_g
per hour while alive. Lemma G5' is now written in design/theory/c3_c4_c5_general.md §9 for a corrected bound (no
shortcut under kappa_infinite, rents scaled by rho_k, loading minutes capped at whole fast slots), which is at most
LB'_rho below; it is CONJECTURE (written proof, audit pending). This script is evidence, not a proof, and it does not
change that label.

Three bounds are compared with exact optima.
  LB'        lb.py's value, computed exactly as the pilot computes it: run_proj.inst_dict(inst, view) with view =
             instance.public_view(inst, model.information), lb.lb_series(d); W_k(t) by run_proj.wk_series(view, d)
             (information). Imported from the prototype copies; no formula of theirs is copied here.
  LB'_doc    the docstring's definition evaluated independently of lb.lb_series's closed forms: groups and
             (r_g, K_g, q_j) from lb.groups and lb.group_params, the minimum over 0 <= n <= N by enumeration, and,
             with kappa_infinite, min{q sum_f d_g(f), K_g + sum_f min(r_g, q d_g(f))} (times Delta_f / 60) for every
             group with an offered contract. lb.lb_series puts a group with r_g >= q_j on all-fallback before it
             reads kappa_infinite (the 'shortcut'); the docstring has no such case, and with kappa_infinite one
             replica serves the group's whole load (design/sim_spec.md §5.5, §8.2 (C3)), so a group with
             q_j d_g(f) > r_g >= q_j at some f is cheaper served than on fallback.
  LB'_rho    LB'_doc on the instance data with every price a_lk replaced by rho_k a_lk, rho_k = P_k /
             (Delta_f ceil(P_k / Delta_f)) for P_k > 0 and 1 for P_k = 0 (P_k the minimum billed term). By rules T6
             and T7 of design/sim_spec.md §3.1 a lease alive in n whole fast slots is charged
             G a (P_k + Delta_f (n - ceil(P_k / Delta_f))^+) / 60 >= rho_k G a Delta_f n / 60, with equality at
             n = ceil(P_k / Delta_f); so the sketch's rent step holds with rate rho_k g_j a_lk, and with g_j a_lk
             only when every P_k is a multiple of Delta_f (hypothesis H1: then LB'_rho = LB'_doc). H1 holds on every
             config in code/sim/configs (Delta_f = 1, or Delta_f = 5 with P_k in multiples of 5 on toy.json,
             ms3_e10b_trace.json and E1/E3's menu e1.MENU) and on core exports (instance.from_core).

(a) Engine instances (sublet.Instance), compared with the simulator's offline optimum: opt.milp.solve_opt on the
    'fast' bench grid (Delta_b = Delta_f; rule T10: the bench model is then the engine's model), whose optimum is
    OPT_P1(sigma, omega) of design/sim_spec.md §8.2 (MILP = OPT_P1, "Exactness"; every engine run of a P1 policy
    under omega with violations absorbed costs at least OPT_P1, proof of Proposition M4(b)), mip_rel_gap 1e-9, 120 s;
    and its LP relaxation (integral=False; LB'/LP is information: LB' <= LP is not claimed). Schedules omega:
    'trace' (the lender's static schedule: Lender(inst, model, rng_streams(lender seed)['lender']).static_schedule(),
    lender seed = config seed), 'eager' (Schedule.eager) and 'none' (no announcement at any site). Instances: 36
    variants of configs/toy.json (variant 0 the config itself, variant 1 with kappa_infinite), 16 variants of
    configs/ms2_multi_small.json (variant 0 the config at a 2-h horizon, variant 1 with kappa_infinite), 16 E3-like
    one-day instances (experiments/e3.build_instance at b in {1, 2, 4}, u = 8, mu = 1, config seeds 101-104,
    shared or siloed, instance.restrict_horizon to 24 or 36 slow slots inside 13:00-21:00, demand scaled by
    0.05-0.4, half of them with perturbed prices, load times, loading charges and q) and 5 probes built from toy.json
    for the two boundary cases above (probe 0: P_k = 7 min on 5-min fast slots, one site, constant demand 1;
    probe 1: probe 0 on 1-min fast slots; probe 4: probe 0 with per_slot billing (P_k = 0); probe 2:
    kappa_infinite, every price above q, two always-active clients of one LLM; probe 3: probe 2 with one client).
    The random variants draw billing (prepaid_D, per_slot, commit_tau), kappa_infinite (toy and ms2: the config
    needs explicit demand), fast slots of 1 or 5 min, prices (the 'dear' toy variants have every price >= q),
    load times 0-1200 s, loading charges, capacities, contracts, stranding, one or two clients (toy) and demand
    scales, from fixed seeds (5000 + i, 6000 + i, 6500 + i, 7000 + i, 7500 + i).
(b) The core family instances of block Q6 (experiments/q44_blocks/Q6.json; q44_study.family_instances and
    family_core: F1 = Fam(m, rho, 2, 1, 48), F2 = Fam(m, rho, 2, 1, 96), F3 = check_c4_lower.single(T, [(1, 1),
    (T, 0)], beta, [1.0, 1.3]); 29 instances), exported by instance.from_core as q44_study does, compared with exact
    optima: OPT(sigma, none) (fam.opt_dp on F1/F2, core.opt_omega on F3), OPT_eager (core.opt_eager; on F1/F2 also
    fam.opt_dp under announcements at every slot), OPT(sigma, omega) for the family modes' schedules (F2: safe_site
    and iid_step at lender seeds 0-9, by fam.opt_dp; F1: the realized schedules of BL1 and BL5 at policy seeds 0-2
    under the adaptive lender F-ad, by q44_study._family_lb, i.e. fam.opt_dp), and the engine MILP solve_opt on the
    from_core instance under 'none' and 'eager' (Claim M3 of design/sim_spec.md §8.3 says it equals the core).

Checks. Violation of a bound: bound > (1 + 1e-9) OPT for an exact OPT (MILP status 0, or a DP), or bound > (1 + 1e-9)
x the MILP's incumbent at any status (the incumbent is a feasible plan, so it is >= OPT_P1). Unresolved: a MILP that
stops at its limit with dual bound < bound <= incumbent. A violation is explained if LB'_rho holds on that
instance and schedule and the instance has a boundary case that accounts for it: for LB', an active shortcut or a
failure of H1; for LB'_doc, a failure of H1. Every violation of LB'_rho is unexplained. Implementation checks:
LB'(t) nondecreasing in t; non-anticipation (LB'(t) and W_k(t) at t = T/2 unchanged when the demand after slot t is
set to 0).

What the MILP cannot test. OPT_P1 is the optimum over plans of class P1 (one LLM per lease, loaded at purchase, never
reloaded; releases at slow-slot starts); the engine also allows Load onto a held lease, Unload, several LLMs on one
lease, admissions below 1 and drains, and a policy that uses them can cost less than OPT_P1 (design/sim_spec.md §8.1,
§10 S15). A pass therefore shows the bound only over P1 plans. With every stranding charge 0 the engine replays an
optimal MILP plan at the MILP's objective (§8.10), so a violation against OPT_P1 is then a violation against an
engine run; with stranding charges the MILP routes across slots more freely than the engine (§8.10), and a
violation is one against OPT_P1, which bounds every engine run of a P1 policy from below (Proposition M4(b)).

Needs the raw traces of /mnt/data/datasets and code/analysis/out/a12_* for part (a)'s E3 instances (G5P_SKIP_E3=1
skips them). Imports the simulator (code/sim) and the prototype copies; run under a 3 GB memory cap. Workers: env
G5P_WORKERS (default 2). Output: out/g5p.json, out/g5p.txt. Exit status 1 iff some violation is unexplained or a
build fails.
"""
import copy
import dataclasses
import json
import math
import multiprocessing as mp
import os
import sys
import time

os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SIM = os.path.join(ROOT, 'code', 'sim')
PROTO = os.path.join(SIM, 'sublet', 'experiments', 'ms5b_proto')
CONFIGS = os.path.join(SIM, 'configs')
OUT = os.path.join(HERE, 'out')
for p in (SIM, PROTO):
    if p not in sys.path:
        sys.path.insert(0, p)
import run_proj as RP  # noqa: E402  (prototype copy; inserts its own folder and code/sim)
import lb as L  # noqa: E402  (prototype copy, imported by run_proj too)

TOL = 1e-9
GAP = 1e-9
TL = 120.0
N_TOY, N_MS2, N_E3, N_PROBE = 36, 16, 16, 5
SCHEDS = ('trace', 'eager', 'none')
KEYS = ('lbpy', 'doc', 'rho')
KEY_LB = {'lbpy': 'LB_T', 'doc': 'LB_doc_T', 'rho': 'LB_rho_T'}
KEY_NAME = {'lbpy': "LB' (lb.py)", 'doc': "LB'_doc", 'rho': "LB'_rho"}


# ---------------------------------------------------------------- the bounds
def lb_doc(d):
    """LB'_doc(T) on the instance data d (run_proj.inst_dict's dict): the definition of lb.py's docstring evaluated
    without lb.lb_series's closed forms (module docstring). Returns (value, groups where lb.lb_series's r >= q
    shortcut is active under kappa_infinite and lowers the group's value)."""
    Df = int(d['fast_min'])
    D = np.asarray(d['demand'], dtype=np.float64)
    kinf = bool(d['kinf'])
    tot, short = 0.0, []
    for gr in L.groups(d):
        p = L.group_params(d, gr)
        r, q, K = float(p['r']), float(p['q']), float(p['K'])
        dg = D[gr['clients']].sum(axis=0)
        fb = q * float(dg.sum()) * Df / 60.0
        if not np.isfinite(r):
            tot += fb
            continue
        if kinf:
            v = min(fb, K + float(np.minimum(r, q * dg).sum()) * Df / 60.0)
            if r >= q and v < fb * (1 - 1e-12):
                short.append({'llm': int(gr['llm']), 'clients': list(map(int, gr['clients'])), 'r': r, 'q': q,
                              'K': K, 'max_d': float(dg.max()), 'LB_g_doc': v, 'LB_g_lbpy': fb})
            tot += v
            continue
        nmax = int(math.ceil(float(dg.max()) - 1e-12)) + 1 if dg.size else 0
        n = np.arange(nmax + 1, dtype=np.float64)[:, None]
        cost = n * r + q * np.maximum(dg[None, :] - n, 0.0)
        run = np.minimum.accumulate(cost, axis=0)           # min over 0 <= n <= N
        vals = np.arange(nmax + 1) * K + run.sum(axis=1) * Df / 60.0
        tot += float(vals.min())
    return tot, short


def rho_factors(d):
    """(K,) rho_k = P_k / (Delta_f ceil(P_k / Delta_f)) for P_k > 0, else 1 (module docstring, LB'_rho)."""
    P = np.asarray(d['prepaid_min'], dtype=np.float64)
    Df = float(d['fast_min'])
    p = np.ceil(P / Df)
    return np.where(P > 0, P / (Df * np.maximum(p, 1.0)), 1.0)


def lb_terms(inst, view):
    """LB'(t), W_k(t) as the pilot computes them, LB'_doc(T), LB'_rho(T), H1 and the implementation checks."""
    d = RP.inst_dict(inst, view)
    LBv, Wfl, info = L.lb_series(d)
    Wk = RP.wk_series(view, d)
    doc, short = lb_doc(d)
    rho = rho_factors(d)
    offered = np.asarray(d['menu_mask'], dtype=bool).any(axis=0)
    h1 = bool(np.all(rho[offered] == 1.0))
    d_rho = dict(d)
    d_rho['price'] = np.asarray(d['price'], dtype=np.float64) * rho[None, :]
    lb_rho, _ = lb_doc(d_rho)
    Ts, phi = len(LBv), int(d['phi'])
    t = Ts // 2
    d2 = dict(d)
    dem = np.array(d['demand'], dtype=np.float64, copy=True)
    dem[:, (t + 1) * phi:] = 0.0
    d2['demand'] = dem
    LB2, _, _ = L.lb_series(d2)
    Wk2 = RP.wk_series(view, d2)
    groups = [{'llm': int(g['llm']), 'n_clients': len(g['clients']), 'n_sites': int(g.get('n_sites', len(g.get('sites', [])))),
               'r': float(g['r']), 'q': float(g['q']), 'K': float(g['K']), 'Nmax': int(g['Nmax'])} for g in info]
    return {'LB_T': float(LBv[-1]), 'LB_doc_T': float(doc), 'LB_rho_T': float(lb_rho), 'Wk_T': float(Wk[-1]),
            'Wfleet_T': float(Wfl[-1]), 'H1': h1, 'rho_k': [float(x) for x in rho],
            'shortcut_groups': short, 'groups': groups,
            'impl_monotone_viol': float(max(0.0, -float(np.min(np.diff(LBv))))) if Ts > 1 else 0.0,
            'impl_nonanticipation_diff': float(max(abs(LB2[t] - LBv[t]), abs(Wk2[t] - Wk[t]))),
            'kinf': bool(d['kinf']), 'phi': phi, 'T_fast': int(dem.shape[1]), 'T_slow': Ts,
            'max_demand': float(np.max(d['demand'])) if np.size(d['demand']) else 0.0}


def judge(lb, obj, dual, status, exact=None):
    """'viol' (lb > incumbent, or > OPT at status 0), 'unresolved' (limit: dual < lb <= incumbent) or 'ok'."""
    if obj is None or not np.isfinite(obj):
        return 'no_incumbent'
    if lb > obj * (1 + TOL) + 1e-12:
        return 'viol'
    if status != 0 and (dual is None or lb > dual * (1 + TOL) + 1e-12):
        return 'unresolved'
    return 'ok'


def explain(rec, e):
    """Per bound: None (no violation), 'shortcut', 'H1', 'shortcut+H1' or 'UNEXPLAINED' (module docstring)."""
    out = {}
    rho_ok = e['judge_rho'] != 'viol'
    for key in KEYS:
        if e[f'judge_{key}'] != 'viol':
            out[key] = None
            continue
        why = []
        if key == 'lbpy' and rec['shortcut_groups']:
            why.append('shortcut')
        if key in ('lbpy', 'doc') and not rec['H1']:
            why.append('H1')
        out[key] = '+'.join(why) if (why and rho_ok) else 'UNEXPLAINED'
    return out


# ---------------------------------------------------------------- engine instances (part a)
def _toy_spec(i):
    rng = np.random.default_rng(5000 + i)
    cfg = json.load(open(os.path.join(CONFIGS, 'toy.json')))
    cfg['name'] = f'toy_v{i}'
    cfg['seed'] = 100 + i
    desc = {'base': 'toy.json'}
    if i == 0:
        return cfg, {**desc, 'variant': 'config as is'}
    if i == 1:
        cfg['llms'][0]['kappa_wtok_per_min'] = 'inf'
        cfg['costs']['kappa_infinite'] = True
        return cfg, {**desc, 'variant': 'config with kappa_infinite'}
    kinf = i % 2 == 1
    billing = ('prepaid_D', 'per_slot', 'commit_tau')[(i // 2) % 3]
    dear = (i // 6) % 2 == 1
    fast = 5 if i < 12 else 1
    T_slow = 24
    q = float(rng.uniform(4.0, 10.0))
    g = int(rng.choice([1, 2]))
    cfg['billing'] = billing
    cfg['time'] = {'slow_slot_min': 5, 'fast_slot_min': fast, 'horizon_min': 5 * T_slow, 'start_minute_of_week': 0}
    cfg['prices']['q_gpu_usd_per_gpu_h'] = q
    cfg['prices']['a_protected_usd_per_gpu_h'] = float(rng.uniform(1.0, 1.6) * q if dear else
                                                       rng.uniform(0.3, 1.3) * q)
    cfg['contracts'] = [{'id': 'short', 'tau_min': 5, 'H_min': int(rng.choice([0, 2, 5]))},
                        {'id': 'long', 'tau_min': int(rng.choice([5, 10, 15])), 'H_min': int(rng.choice([0, 3, 10]))},
                        {'id': 'prot', 'tau_min': None, 'H_min': 0, 'prepaid_min': int(rng.choice([5, 10]))}]
    cfg['llms'][0]['g'] = g
    lo, hi = (1.0, 1.6) if dear else (0.2, 0.9)
    for e in cfg['lenders']:
        if e['kind'] == 'synthetic':
            e['prices'] = {'short': float(rng.uniform(lo, hi) * q), 'long': float(rng.uniform(lo, hi) * q)}
            e['capacity_gpus'] = [2, 4, 8, 64][int(rng.integers(4))]
            rate = float(rng.choice([0.1, 0.3, 0.6]))
            e['R'] = np.flatnonzero(rng.random(T_slow) < rate).astype(int).tolist()
            e['lam_s'] = float(rng.choice([0.0, 30.0, 150.0, 300.0, 600.0, 1200.0]))
        else:
            e['lam_s'] = float(rng.choice([0.0, 300.0, 900.0]))
    cfg['costs']['beta_jl_usd'] = float(rng.choice([0.0, 0.02, 0.2, 1.0]))
    cfg['stranding']['mu_over_beta_tilde'] = float(rng.choice([0.0, 0.5, 1.0]))
    cfg['stranding']['kv_share'] = float(rng.choice([0.0, 0.5]))
    if kinf:
        cfg['llms'][0]['kappa_wtok_per_min'] = 'inf'
        cfg['costs']['kappa_infinite'] = True
    n_cl = 1 + int(rng.random() < 0.5)
    phi = 5 // fast
    clients = []
    for c in range(n_cl):
        lev = rng.choice([0.0, 0.4, 1.0, 1.5, 2.5, 3.7], size=T_slow, p=[0.3, 0.1, 0.2, 0.15, 0.15, 0.1])
        dem = np.repeat(lev, phi)
        if phi > 1:
            dem = dem * rng.uniform(0.7, 1.3, size=dem.size)
        scale = float(rng.choice([0.5, 1.0, 2.0]))
        clients.append({'llm': 'M', 'region': 'r0', 'slo_class': 'strict', 'borrowers': [f'b{c}'],
                        'demand': {'kind': 'array', 'values': [round(float(x) * scale, 6) for x in dem]}})
    cfg['borrowers'] = {'model': 'explicit', 'clients': clients}
    return cfg, {**desc, 'variant': 'random', 'kinf': kinf, 'billing': billing, 'dear': dear, 'fast_min': fast,
                 'q_gpu': q, 'g': g, 'n_clients': n_cl}


def _ms2_spec(i):
    rng = np.random.default_rng(6000 + i)
    cfg = json.load(open(os.path.join(CONFIGS, 'ms2_multi_small.json')))
    cfg['name'] = f'ms2_v{i}'
    cfg['seed'] = 200 + i
    desc = {'base': 'ms2_multi_small.json'}
    if i in (0, 1):
        cfg['time']['horizon_min'] = 120
        if i == 1:
            for x in cfg['llms']:
                x['kappa_wtok_per_min'] = 'inf'
            cfg['costs']['kappa_infinite'] = True
        return cfg, {**desc, 'variant': 'config at 120 min' + (' with kappa_infinite' if i else ''),
                     'perturb': None}
    kinf = i % 2 == 1
    fast = 1 if i < 10 else 5
    cfg['time']['fast_slot_min'] = fast
    cfg['time']['horizon_min'] = int(rng.choice([60, 90])) if fast == 1 else int(rng.choice([120, 240]))
    cfg['billing'] = ('prepaid_D', 'per_slot', 'commit_tau')[i % 3]
    cfg['lender_defaults']['offset'] = 'random'
    cfg['prices']['q_gpu_usd_per_gpu_h'] = float(rng.uniform(4.0, 12.0))
    cfg['stranding']['mu_over_beta_tilde'] = float(rng.choice([0.0, 1.0]))
    cfg['stranding']['kv_share'] = float(rng.choice([0.0, 0.3]))
    if kinf:
        for x in cfg['llms']:
            x['kappa_wtok_per_min'] = 'inf'
        cfg['costs']['kappa_infinite'] = True
    pert = {'price_lo': 0.4, 'price_hi': 3.0, 'lam_hi': 3.0, 'beta': float(rng.choice([0.0, 0.05, 0.5])),
            'demand_scale': float(rng.choice([0.5, 1.0, 2.0, 3.0])), 'seed': 6500 + i}
    return cfg, {**desc, 'variant': 'random', 'kinf': kinf, 'fast_min': fast, 'billing': cfg['billing'],
                 'horizon_min': cfg['time']['horizon_min'], 'perturb': pert}


def _probe_spec(i):
    """The five boundary probes of the module docstring, from toy.json: one revocable site, beta = 0, lambda = 0,
    q_GPU = 10 USD/GPU-h, no stranding charge, 2 h."""
    cfg = json.load(open(os.path.join(CONFIGS, 'toy.json')))
    cfg['name'] = f'probe_v{i}'
    cfg['seed'] = 300 + i
    fast = 1 if i == 1 else 5
    phi = 5 // fast
    T_slow = 24
    kinf = i in (2, 3)
    H = 5 if kinf else 2
    price = 12.0 if kinf else 1.0
    cfg['billing'] = 'per_slot' if i == 4 else 'prepaid_D'
    cfg['time'] = {'slow_slot_min': 5, 'fast_slot_min': fast, 'horizon_min': 5 * T_slow, 'start_minute_of_week': 0}
    cfg['prices']['q_gpu_usd_per_gpu_h'] = 10.0
    cfg['prices']['a_protected_usd_per_gpu_h'] = 12.0 if kinf else 5.0
    cfg['contracts'] = [{'id': 'short', 'tau_min': 5, 'H_min': H},
                        {'id': 'prot', 'tau_min': None, 'H_min': 0, 'prepaid_min': 5}]
    cfg['lenders'] = [{'id': 'L0', 'kind': 'synthetic', 'region': 'r0', 'group': 'g0', 'menu': ['short'],
                       'prices': {'short': price}, 'capacity_gpus': 64, 'R': [], 'load_scenario': 'explicit',
                       'lam_s': 0.0},
                      {'id': 'P', 'kind': 'protected', 'region': 'r0', 'group': 'gp', 'menu': ['prot'],
                       'capacity_gpus': None, 'load_scenario': 'explicit', 'lam_s': 0.0}]
    cfg['costs']['beta_jl_usd'] = 0.0
    cfg['stranding']['mu_over_beta_tilde'] = 0.0
    if kinf:
        cfg['llms'][0]['kappa_wtok_per_min'] = 'inf'
        cfg['costs']['kappa_infinite'] = True
    n_cl = 2 if i == 2 else 1
    cfg['borrowers'] = {'model': 'explicit', 'clients': [
        {'llm': 'M', 'region': 'r0', 'slo_class': 'strict', 'borrowers': [f'b{c}'],
         'demand': {'kind': 'array', 'values': [1.0] * (T_slow * phi)}} for c in range(n_cl)]}
    what = {0: 'P = 7 min on 5-min fast slots (H1 fails)', 1: 'probe 0 on 1-min fast slots (H1 holds)',
            2: 'kappa_infinite, prices 12 > q 10, two clients (shortcut active)',
            3: 'probe 2 with one client (shortcut inactive)', 4: 'probe 0 with per_slot billing (P = 0, H1 holds)'}
    return cfg, {'base': 'toy.json', 'variant': f'probe {i}: {what[i]}', 'kinf': kinf, 'fast_min': fast}


E3_BM = ((1, True), (2, True), (2, False), (4, True), (4, False))


def _e3_spec(i):
    rng = np.random.default_rng(7000 + i)
    b, merge = E3_BM[i % len(E3_BM)]
    c = 101 + i % 4
    t0 = int(rng.choice([156, 168, 180, 192, 216, 240]))
    T = int(rng.choice([24, 36]))
    pert = {'demand_scale': float(rng.choice([0.05, 0.1, 0.2, 0.4])), 'seed': 7500 + i}
    if i % 2 == 1:
        pert.update({'price_lo': 0.5, 'price_hi': 3.0, 'lam_hi': 3.0, 'beta': float(rng.choice([0.0, 0.05, 0.5])),
                     'q_lo': 0.6, 'q_hi': 1.5})
    return None, {'base': 'e3.build_instance', 'b': b, 'u': 8, 'mu': 1.0, 'c': c, 'merge': merge,
                  'horizon': [t0, T], 'perturb': pert}


def _perturb(inst, pert):
    """Instance-level perturbation: offered prices x U[price_lo, price_hi] per (site, contract), load times x
    U[0, lam_hi] per (LLM, site), loading charges + beta, q x U[q_lo, q_hi] per LLM, demand x demand_scale."""
    from sublet.instance import validate, with_demand
    if not pert:
        return inst
    rng = np.random.default_rng(pert['seed'])
    kw = {}
    if 'price_lo' in pert:
        pr = np.array(inst.price, dtype=np.float64, copy=True)
        fac = rng.uniform(pert['price_lo'], pert['price_hi'], size=pr.shape)
        kw['price'] = np.where(np.isfinite(pr), pr * fac, pr)
        kw['lam_s'] = np.asarray(inst.lam_s, dtype=np.float64) * rng.uniform(0.0, pert['lam_hi'], size=inst.lam_s.shape)
        kw['beta_usd'] = np.asarray(inst.beta_usd, dtype=np.float64) + pert['beta']
    if 'q_lo' in pert:
        kw['llms'] = tuple(dataclasses.replace(x, q_usd_per_h=float(x.q_usd_per_h * rng.uniform(pert['q_lo'],
                                                                                                pert['q_hi'])))
                           for x in inst.llms)
    if kw:
        inst = dataclasses.replace(inst, **kw)
        validate(inst)
    s = pert.get('demand_scale', 1.0)
    if s != 1.0:
        inst = with_demand(inst, np.asarray(inst.clients.demand) * s)
    return inst


def build_engine(spec):
    from sublet.config import lender_model, load_config, rng_streams
    from sublet.instance import build_instance
    from sublet.lender import Lender
    fam, i = spec['family'], spec['i']
    if fam == 'e3':
        from sublet.experiments import e3
        _, desc = _e3_spec(i)
        inst, model, _ecfg, _ov = e3.build_instance(desc['b'], desc['u'], desc['mu'], desc['c'], desc['merge'],
                                                    horizon=desc['horizon'])
        inst = _perturb(inst, desc['perturb'])
        trace = e3.trace_schedule(inst, model, desc['c'])
        ls = desc['c']
    else:
        cfg, desc = {'toy': _toy_spec, 'ms2': _ms2_spec, 'probe': _probe_spec}[fam](i)
        inst = build_instance(copy.deepcopy(cfg))
        model = lender_model(load_config(copy.deepcopy(cfg)))
        inst = _perturb(inst, desc.get('perturb'))
        ls = int(inst.seed)
        trace = Lender(inst, model, rng_streams(ls)['lender']).static_schedule()
    return inst, model, trace, ls, desc


def engine_case(spec):
    from sublet.instance import public_view
    from sublet.opt.milp import SizeError, solve_opt
    from sublet.types import Schedule
    t0 = time.perf_counter()
    name = f"{spec['family']}_v{spec['i']}"
    try:
        inst, model, trace, ls, desc = build_engine(spec)
    except Exception as exc:  # a variant the builder rejects is reported, never silently dropped
        return {'name': name, 'family': spec['family'], 'error': f'build: {type(exc).__name__}: {exc}'}
    view = public_view(inst, model.information)
    rec = {'name': name, 'family': spec['family'], 'desc': desc, 'lender_seed': ls, 'm': inst.m, 'n': inst.n,
           'J': inst.J, 'billing': inst.billing, 'fast_min': inst.grid.fast_min,
           'contracts': [[k.id, k.tau_slots, k.H_min, k.prepaid_min] for k in inst.contracts],
           **lb_terms(inst, view)}
    empty = Schedule('none', tuple(np.zeros(0, dtype=np.int64) for _ in inst.sites), True)
    rec['sched'] = {}
    for sn, sch in (('trace', trace), ('eager', Schedule.eager(inst)), ('none', empty)):
        e = {'n_announcements': int(sum(len(r) for r in sch.R))}
        try:
            r = solve_opt(inst, sch, grid='fast', time_limit_s=TL, mip_rel_gap=GAP, return_plan=False)
            lp = solve_opt(inst, sch, grid='fast', integral=False, time_limit_s=TL, return_plan=False)
        except SizeError as exc:
            e['error'] = f'SizeError: {exc}'
            rec['sched'][sn] = e
            continue
        obj = float(r.objective) if r.objective is not None else None
        dual = float(r.dual_bound) if r.dual_bound is not None else None
        e.update({'OPT': obj, 'dual': dual, 'status': int(r.status), 'gap': r.gap, 'status_msg': r.status_msg,
                  'LP': float(lp.objective) if lp.objective is not None else None, 'LP_status': int(lp.status),
                  'n_vars': int(r.size.get('n_vars', 0)), 'n_int': int(r.size.get('n_int', 0)),
                  'solve_s': float(r.solve_s), 'peak_rss_mb': float(r.peak_rss_mb)})
        for key in KEYS:
            v = rec[KEY_LB[key]]
            e[f'ratio_{key}'] = v / obj if obj else (0.0 if v <= 0 else math.inf)
            e[f'judge_{key}'] = judge(v, obj, dual, int(r.status))
        e['explain'] = explain(rec, e)
        e['ratio_dual'] = rec['LB_T'] / dual if dual else None
        e['ratio_LP'] = rec['LB_T'] / e['LP'] if e['LP'] else None
        e['Wk_over_OPT'] = rec['Wk_T'] / obj if obj else None
        e['B_over_OPT'] = min(rec['Wk_T'], rec['LB_T']) / obj if obj else None
        rec['sched'][sn] = e
    rec['wall_s'] = time.perf_counter() - t0
    return rec


# ---------------------------------------------------------------- Q6 families (part b)
def family_case(arg):
    from sublet.drivers import run as drun
    from sublet.engine import EngineConfig, simulate
    from sublet.experiments import q44_study as Q
    from sublet.config import rng_streams
    from sublet.instance import from_core, public_view
    from sublet.lender import Lender
    from sublet.opt.milp import solve_opt
    from sublet.paths import import_ref
    from sublet.types import LenderModel, Schedule
    fam, v = arg
    t0 = time.perf_counter()
    core = import_ref('core')
    fm = import_ref('fam')
    fid = Q._fam_instance_id(fam, **v)
    I, F, desc = Q.family_core(fam, v)
    m, T = int(I.a.shape[0]), int(I.T)
    empty = [np.zeros(0, dtype=np.int64) for _ in range(m)]
    inst, _ = from_core(I, empty)
    view = public_view(inst, 'I1')
    rec = {'name': fid, 'family': fam['id'], 'core_instance': desc, 'm': m, 'T': T, **lb_terms(inst, view)}
    opts = []                                       # (label, value, exact, status)
    if F is not None:
        opts.append(('none (fam.opt_dp)', fm.opt_dp(F, [np.zeros(0, dtype=int)] * m)[0], True, 0))
        opts.append(('eager (fam.opt_dp)', fm.opt_dp(F, [np.arange(T)] * m)[0], True, 0))
    else:
        r = core.opt_omega(I, [np.zeros(0, dtype=int)] * m)
        opts.append(('none (core.opt_omega)', r['fun'], r['status'] == 0, r['status']))
    r = core.opt_eager(I)
    opts.append(('eager (core.opt_eager)', r['fun'], r.get('status', 0) == 0, r.get('status', 0)))
    for md in fam['modes']:
        fmode = Q.FAMILY_MODES[md]
        model = LenderModel(schedule=fmode['schedule'], information='I1', params=dict(fmode['params']))
        if fmode['schedule'] == 'adaptive':
            for inner in ('BL1', 'BL5'):
                for ps in (0, 1, 2):
                    inst_r, _ = from_core(I, empty)
                    vals, _ = drun.driver_inputs(inner, {}, inst_r)
                    pol = drun.make_policy({'policy': {'id': inner, 'params': {}}}, inst_r, inputs=vals)
                    res = simulate(inst_r, pol, model, EngineConfig(check_invariants=True), lender_seed=0,
                                   policy_seed=ps)
                    val, meta = Q._family_lb(fam, F, I, res, inst_r)
                    opts.append((f'{md} {inner} p{ps} ({meta["method"]})', val, meta.get('status', 0) == 0,
                                 meta.get('status', 0)))
        elif fmode['schedule'] in ('safe_site', 'iid_step') and F is not None:
            for ls in range(10):
                sch = Lender(inst, model, rng_streams(ls)['lender']).static_schedule()
                om = [np.asarray(x, dtype=int) for x in sch.R]
                opts.append((f'{md} l{ls} (fam.opt_dp)', fm.opt_dp(F, om)[0], True, 0))
    for sn, sch in (('none', Schedule('none', tuple(empty), True)), ('eager', Schedule.eager(inst))):
        r = solve_opt(inst, sch, grid='slow', time_limit_s=TL, mip_rel_gap=GAP, return_plan=False)
        opts.append((f'{sn} (engine MILP on from_core)', float(r.objective), r.status == 0, int(r.status)))
    rec['opts'] = []
    for (lab, val, exact, st) in opts:
        e = {'label': lab, 'OPT': float(val), 'exact': bool(exact), 'status': int(st)}
        for key in KEYS:
            lbv = rec[KEY_LB[key]]
            e[f'ratio_{key}'] = lbv / val if val else (0.0 if lbv <= 0 else math.inf)
            e[f'judge_{key}'] = ('viol' if lbv > val * (1 + TOL) + 1e-12 else 'ok') if exact else 'not_exact'
        e['explain'] = explain(rec, e)
        rec['opts'].append(e)
    rec['min_exact_OPT'] = min(e['OPT'] for e in rec['opts'] if e['exact'])
    rec['ratio_to_min'] = rec['LB_T'] / rec['min_exact_OPT']
    rec['wall_s'] = time.perf_counter() - t0
    return rec


# ---------------------------------------------------------------- report
def _fmt_ratio(x):
    return '-' if x is None else f'{x:.4f}'


def _f6(x):
    return '-' if x is None else f'{x:.6f}'


def _best(rows):
    """(max ratio, where) over rows of (ratio, where)."""
    rows = [x for x in rows if x[0] is not None]
    return max(rows, key=lambda x: x[0]) if rows else (None, None)


def main():
    t_start = time.time()
    os.makedirs(OUT, exist_ok=True)
    workers = int(os.environ.get('G5P_WORKERS', '2'))
    skip_e3 = os.environ.get('G5P_SKIP_E3', '0') == '1'
    specs = ([{'family': 'toy', 'i': i} for i in range(N_TOY)] + [{'family': 'ms2', 'i': i} for i in range(N_MS2)]
             + ([] if skip_e3 else [{'family': 'e3', 'i': i} for i in range(N_E3)])
             + [{'family': 'probe', 'i': i} for i in range(N_PROBE)])
    from sublet.experiments import q44_study as Q
    block = json.load(open(os.path.join(SIM, 'sublet', 'experiments', 'q44_blocks', 'Q6.json')))
    fargs = [(fam, v) for fam in block['families'] for v in Q.family_instances(fam)]
    ctx = mp.get_context('fork')
    with ctx.Pool(workers) as pool:
        eng = pool.map(engine_case, specs, chunksize=1)
        t_eng = time.time() - t_start
        fams = pool.map(family_case, fargs, chunksize=1)
    t_all = time.time() - t_start
    t_fam = t_all - t_eng

    errors = [{'name': r['name'], 'error': r['error']} for r in eng if 'error' in r]
    viol = {k: [] for k in KEYS}            # (where, explanation)
    unres = {k: [] for k in KEYS}
    ratios = {k: [] for k in KEYS}          # (ratio, where, exact, inside): inside = H1 and no active shortcut
    other = {'dual': [], 'LP': []}
    statuses = {}
    n_solves = 0
    lbdiff = {'doc': [], 'rho': []}
    impl = {'monotone': 0.0, 'nonanticipation': 0.0}
    for r in eng + fams:
        if 'error' in r:
            continue
        impl['monotone'] = max(impl['monotone'], r['impl_monotone_viol'])
        impl['nonanticipation'] = max(impl['nonanticipation'], r['impl_nonanticipation_diff'])
        for key in ('doc', 'rho'):
            if abs(r['LB_T'] - r[KEY_LB[key]]) > 1e-9 * max(1.0, abs(r['LB_T'])):
                lbdiff[key].append(r['name'])
        inside = r['H1'] and not r['shortcut_groups']
        rows = list(r['sched'].items()) if 'sched' in r else [(e['label'], e) for e in r['opts']]
        for sn, e in rows:
            where = f"{r['name']} {sn}"
            if 'error' in e:
                errors.append({'name': where, 'error': e['error']})
                continue
            if 'sched' in r:
                n_solves += 1
                statuses[e['status']] = statuses.get(e['status'], 0) + 1
                exact = e['status'] == 0
                other['dual'].append((e['ratio_dual'], where))
                other['LP'].append((e['ratio_LP'], where))
            else:
                exact = e['exact']
                if not exact:
                    continue
            for key in KEYS:
                if e[f'judge_{key}'] == 'viol':
                    viol[key].append((where, e['explain'][key]))
                elif e[f'judge_{key}'] == 'unresolved':
                    unres[key].append(where)
                ratios[key].append((e[f'ratio_{key}'], where, exact, inside))
    unexplained = [(k, w) for k in KEYS for (w, x) in viol[k] if x == 'UNEXPLAINED']
    n_viol = sum(len(v) for v in viol.values())
    fam_counts = {}
    for r in eng:
        fam_counts[r['family']] = fam_counts.get(r['family'], 0) + 1
    mx = {}
    for key in KEYS:
        mx[key] = {'all': _best([(x[0], x[1]) for x in ratios[key]]),
                   'exact': _best([(x[0], x[1]) for x in ratios[key] if x[2]]),
                   'inside_H1_no_shortcut': _best([(x[0], x[1]) for x in ratios[key] if x[3]]),
                   'engine': _best([(x[0], x[1]) for x in ratios[key] if not x[1].startswith('F')]),
                   'families': _best([(x[0], x[1]) for x in ratios[key] if x[1].startswith('F')])}
    summary = {'n_engine_instances': len(eng), 'engine_by_family': fam_counts, 'n_errors': len(errors),
               'errors': errors, 'n_milp_solves': n_solves,
               'milp_status_counts': {str(k): v for k, v in sorted(statuses.items())},
               'n_family_instances': len(fams),
               'n_family_exact_opts': sum(1 for r in fams for e in r['opts'] if e['exact']),
               'violations': {k: viol[k] for k in KEYS}, 'unresolved': {k: unres[k] for k in KEYS},
               'unexplained_violations': unexplained, 'total_violations': n_viol,
               'max_ratio': mx, 'max_ratio_LB_over_dual': _best(other['dual']),
               'max_ratio_LB_over_LP': _best(other['LP']),
               'instances_H1_fails': [r['name'] for r in eng + fams if 'error' not in r and not r['H1']],
               'instances_shortcut_active': [r['name'] for r in eng + fams if 'error' not in r and r['shortcut_groups']],
               'instances_LB_differs_from': lbdiff, 'impl_checks_max': impl,
               'runtime_s': {'engine': t_eng, 'families': t_fam, 'total': t_all}, 'workers': workers,
               'skip_e3': skip_e3}
    meta = {'script': 'code/theory_checks/c3/check_g5p.py', 'tol': TOL, 'mip_rel_gap': GAP, 'time_limit_s': TL,
            'schedules': list(SCHEDS), 'prototype_sha256': {f: _sha(os.path.join(PROTO, f)) for f in ('lb.py', 'run_proj.py')},
            'started': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(t_start))}
    json.dump({'meta': meta, 'summary': summary, 'engine': eng, 'families': fams},
              open(os.path.join(OUT, 'g5p.json'), 'w'), indent=1, default=_json_default)

    Lx = []
    A = Lx.append
    A("Lemma G5' check (proposed; design/sublet_v2.md §2.5, §5 P2a/P2; statement: docstring of "
      "code/sim/sublet/experiments/ms5b_proto/lb.py); script check_g5p.py")
    A(f"LB': lb.lb_series of the prototype copy (sha256 lb.py {meta['prototype_sha256']['lb.py'][:16]}, run_proj.py "
      f"{meta['prototype_sha256']['run_proj.py'][:16]}); LB'_doc: the docstring's definition evaluated independently; "
      f"LB'_rho: LB'_doc with prices a_lk rho_k (rho_k = P_k / (Delta_f ceil(P_k / Delta_f)); = LB'_doc under H1)")
    A(f"(a) engine instances: {len(eng)} ({', '.join(f'{k} {v}' for k, v in fam_counts.items())}); OPT = "
      f"opt.milp.solve_opt on the fast grid (OPT_P1), mip_rel_gap {GAP:g}, time limit {TL:g} s; schedules trace, "
      f"eager, none; MILP solves {n_solves}, status counts {summary['milp_status_counts']}")
    A(f"(b) Q6 family instances: {len(fams)}; exact optima compared: {summary['n_family_exact_opts']}")
    A(f"runtime {t_all:.0f} s on {workers} workers (engine part {t_eng:.0f} s, families {t_fam:.0f} s)")
    A(f"TOTAL VIOLATIONS: {n_viol}  (" + ', '.join(f"{KEY_NAME[k]} {len(viol[k])}" for k in KEYS) + ")")
    A(f"UNEXPLAINED VIOLATIONS: {len(unexplained)}" + (f"  {unexplained}" if unexplained else ''))
    A(f"build or solver errors: {len(errors)}" + (f"  {errors}" if errors else ''))
    A("unresolved (MILP at its limit with dual < bound <= incumbent): "
      + ', '.join(f"{KEY_NAME[k]} {len(unres[k])}" for k in KEYS))
    A(f"instances where H1 fails (some offered P_k not a multiple of Delta_f): "
      f"{len(summary['instances_H1_fails'])} {summary['instances_H1_fails']}")
    A(f"instances where lb.py's r >= q shortcut is active under kappa_infinite: "
      f"{len(summary['instances_shortcut_active'])} {summary['instances_shortcut_active']}")
    A('')
    A('Maximum ratio bound/OPT (over every exact OPT and every MILP incumbent; "inside" = H1 holds and no active '
      'shortcut)')
    for key in KEYS:
        m_ = mx[key]
        A(f"  {KEY_NAME[key]:12s} all {_f6(m_['all'][0])} at {m_['all'][1]}; at exact OPT {_f6(m_['exact'][0])} at "
          f"{m_['exact'][1]}; inside {_f6(m_['inside_H1_no_shortcut'][0])} at {m_['inside_H1_no_shortcut'][1]}; "
          f"families {_f6(m_['families'][0])} at {m_['families'][1]}")
    A(f"  LB'/dual bound (engine): {_f6(summary['max_ratio_LB_over_dual'][0])} at {summary['max_ratio_LB_over_dual'][1]}")
    A(f"  LB'/LP (engine; information, LB' <= LP is not claimed): {_f6(summary['max_ratio_LB_over_LP'][0])} at "
      f"{summary['max_ratio_LB_over_LP'][1]}")
    A(f"instances where LB' differs from LB'_doc: {len(lbdiff['doc'])} {lbdiff['doc']}; from LB'_rho: "
      f"{len(lbdiff['rho'])} {lbdiff['rho']}")
    A(f"impl. LB'(t) nondecreasing: max decrease {impl['monotone']:.3e}; impl. non-anticipation at T/2: max |diff| "
      f"{impl['nonanticipation']:.3e}")
    for key in KEYS:
        if viol[key]:
            A(f"violations of {KEY_NAME[key]} (explanation): " + '; '.join(f"{w} ({x})" for w, x in viol[key]))
    A('')
    A("(a) engine instances: LB'(T), LB'_doc(T), LB'_rho(T), W_k(T); per schedule OPT (MILP), status, LB'/OPT, "
      "LB'_rho/OPT, LB'/LP")
    A("  instance    kinf H1 bill       phi  T_f  maxd     LB'      LB'_doc   LB'_rho    W_k     | trace | eager | none")
    for r in eng:
        if 'error' in r:
            A(f"  {r['name']:11s} ERROR {r['error']}")
            continue
        cells = []
        for sn in SCHEDS:
            e = r['sched'].get(sn, {})
            if 'OPT' not in e:
                cells.append(e.get('error', 'missing'))
                continue
            cells.append(f"{e['OPT']:.4f} {e['status']} {e['ratio_lbpy']:.4f} {e['ratio_rho']:.4f} "
                         f"{_fmt_ratio(e['ratio_LP'])}")
        flag = ' SHORTCUT' if r['shortcut_groups'] else ''
        A(f"  {r['name']:11s} {str(r['kinf'])[0]:4s} {str(r['H1'])[0]:2s} {r['billing']:10s} {r['phi']:3d} "
          f"{r['T_fast']:4d} {r['max_demand']:6.2f} {r['LB_T']:9.4f} {r['LB_doc_T']:9.4f} {r['LB_rho_T']:9.4f} "
          f"{r['Wk_T']:9.4f} | " + ' | '.join(cells) + flag)
    A('')
    A("(b) Q6 families: LB'(T) (= LB'_doc = LB'_rho unless listed above), W_k(T), the exact optima (minimum, count), "
      "LB'/min OPT, OPT(none), OPT_eager, engine MILP none/eager")
    for r in fams:
        get = {e['label']: e['OPT'] for e in r['opts']}
        none = next(v for k, v in get.items() if k.startswith('none ('))
        A(f"  {r['name']:13s} {r['LB_T']:9.3f} {r['Wk_T']:9.3f} {r['min_exact_OPT']:9.3f} "
          f"{sum(e['exact'] for e in r['opts']):3d} {r['ratio_to_min']:9.5f} {none:9.3f} "
          f"{get['eager (core.opt_eager)']:9.3f} {get['none (engine MILP on from_core)']:9.3f}/"
          f"{get['eager (engine MILP on from_core)']:9.3f}")
    txt = '\n'.join(Lx)
    print(txt)
    open(os.path.join(OUT, 'g5p.txt'), 'w').write(txt + '\n')
    sys.exit(1 if (unexplained or errors) else 0)


def _sha(p):
    import hashlib
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


if __name__ == '__main__':
    main()
