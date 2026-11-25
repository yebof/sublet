"""Tests of the baselines BL0a-BL8 (design/sim_spec_ms2.md §15; §17.2 test_baselines.py; checks 3i-3l).

Policies are built through the registry (drivers.run.make_policy). Reference values come from
code/theory_checks/c3/out/c4_lower.json (parts (a)-(d)); OPT denominators are fam.opt_dp on the
realized schedule (part (a)) and core.opt_eager (parts (b)-(d), the reference's own MILP), the
offline class values of the random lines solve_eager at mip_rel_gap 1e-9. §3 gives no interfaces for
the baselines' internals; where a test needs one it uses the module's functions (cocar.round_counts,
cocar.omega_share, cocar.repair_counts) or the report's fields ('pools' and 'events' of BL3).
"""
from __future__ import annotations

import copy
import json
import math

import numpy as np
import pytest

import core
import fam

from fixtures import A0, CM_ROWS, c4l_b, c4l_d, cm_case, explicit_client, explicit_llm, site_index, toy_config, \
    toy_instance, with_capacity

from sublet.algos import registry
from sublet.drivers.provision import bl0b_usd, own_capacity_usd
from sublet.drivers.run import make_policy
from sublet.drivers.siloed import run_siloed
from sublet.engine import EngineConfig, simulate
from sublet.instance import build_instance, from_core, public_view, validate
from sublet.opt.milp import solve_eager
from sublet.paths import C3
from sublet.policies.trivial import AlwaysFallback
from sublet.types import INF, ActionResult, Buy, LeaseView, LenderModel, Notice, ReplicaView, SlowObs

C4 = json.loads((C3 / "out" / "c4_lower.json").read_text())
TOL = 1e-9
TOL_MILP = 2e-4
MILP_KW = dict(mip_rel_gap=1e-9, time_limit_s=600.0)


def _make(pid, params, inst, inputs=None):
    return make_policy({"policy": {"id": pid, "params": dict(params or {})}}, inst, inputs=inputs)


def _sim(inst, pol, schedule="trace", information="I1", rng=None, seed=0, violations="absorb"):
    res = simulate(inst, pol, LenderModel(schedule=schedule, information=information, violations=violations),
                   EngineConfig(auto_drain=False, check_invariants=True), lender_seed=seed,
                   policy_seed=None if rng is not None else seed, policy_rng=rng)
    assert not res.invariant_failures, res.invariant_failures[:5]
    return res


def _core(I):
    return from_core(I, [np.zeros(0, dtype=np.int64)] * I.m)[0]


def _close(a, b, tol=TOL):
    return abs(a - b) <= tol * max(1.0, abs(b))


# ---------------------------------------------------------------- BL0a, BL0b
def test_bl0a():
    """§15.2: BL0a is MS1's AlwaysFallback; its run equals a direct AlwaysFallback run."""
    inst = toy_instance()
    pol = _make("BL0a", {}, inst)
    assert type(pol) is AlwaysFallback
    a = _sim(inst, pol)
    b = _sim(inst, AlwaysFallback())
    assert a.components == b.components and a.components["total"] > 0


def test_bl0b_formula():
    """§15.2 (M42): bl0b_usd = sum_b g_jb (peak_b - C0_b) a_commit T_h ('overflow') or sum_b g_jb peak_b
    a_commit T_h ('total'), own_capacity_usd = sum_b g_jb C0_b a_commit T_h, with a_commit the cheapest
    protected price of the instance by default; by hand from borrower_stats (1e-12)."""
    cfg = toy_config()
    cfg["llms"] = [explicit_llm("M", 1), explicit_llm("M2", 2)]
    inst = build_instance(cfg)
    inst.borrower_stats = {"b0": {"llm": 0, "C0_loads": 1.5, "peak_loads": 4.0},
                           "b1": {"llm": 1, "C0_loads": 0.25, "peak_loads": 2.0},
                           "b2": {"llm": 0, "C0_loads": 0.0, "peak_loads": 0.5}}
    a_p = min(float(inst.price[l, k]) for l, s in enumerate(inst.sites) for k in s.menu
              if inst.contracts[k].protected)
    assert a_p == 5.97
    T_h = inst.grid.horizon_min / 60.0
    for a in (None, 3.0):
        ac = a_p if a is None else a
        over = (1 * (4.0 - 1.5) + 2 * (2.0 - 0.25) + 1 * 0.5) * ac * T_h
        tot = (1 * 4.0 + 2 * 2.0 + 1 * 0.5) * ac * T_h
        own = (1 * 1.5 + 2 * 0.25 + 0.0) * ac * T_h
        kw = {} if a is None else {"a_commit": a}
        assert _close(bl0b_usd(inst, **kw), over, 1e-12)
        assert _close(bl0b_usd(inst, accounting="total", **kw), tot, 1e-12)
        assert _close(own_capacity_usd(inst, **kw), own, 1e-12)
        assert _close(bl0b_usd(inst, accounting="total", **kw), over + own, 1e-12)


# ---------------------------------------------------------------- BL1
def test_bl1_stay_c4_lower_a():
    """§15.3: BL1 with site_order='index' on the cat-and-mouse instances under the adaptive lender re-buys
    at site 0 at every death and reproduces the 'stay' column of c4_lower.json a[*] (cost over
    fam.opt_dp on the realized R, 1e-9)."""
    assert len(CM_ROWS) == len(C4["a"]) == 16
    for (m, rho), ref in zip(CM_ROWS, C4["a"]):
        assert (ref["m"], ref["rho"]) == (m, rho)
        I = cm_case(m, rho)
        inst = _core(I)
        res = _sim(inst, _make("BL1", {"site_order": "index"}, inst), schedule="adaptive")
        assert {L.site for L in res.leases} == {0}
        F = fam.Fam(m, rho, int(I.tau[0]), int(I.H[0]), I.T)
        opt = fam.opt_dp(F, [np.asarray(r, dtype=np.int64) for r in res.schedule.R])[0]
        assert _close(res.components["total"] / opt, ref["stay"]), (m, rho, res.components["total"] / opt, ref["stay"])


# ---------------------------------------------------------------- BL2
def _one_site(demand, *, slot_min=1, contracts=(("rev", 1, 0),), price=A0, lam=0.0, beta_jl=0.3, R=(),
              llm_g=1):
    """One synthetic revocable site 'R' (unlimited capacity, explicit R) next to the toy's protected site, one
    client with demand per slot (Δs = Δf = slot_min), beta_jl > 0 so that s0 > 0 at lambda = 0."""
    cfg = toy_config(sites=["L0", "P"])
    cfg["time"] = {"slow_slot_min": slot_min, "fast_slot_min": slot_min, "horizon_min": slot_min * len(demand),
                   "start_minute_of_week": 0}
    cfg["costs"]["beta_jl_usd"] = float(beta_jl)
    cfg["contracts"] = [{"id": i, "tau_min": t, "H_min": h} for i, t, h in contracts] + \
                       [{"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": slot_min}]
    cfg["llms"] = [explicit_llm("M", llm_g)]
    L0, P = cfg["lenders"]
    L0.update({"id": "R", "menu": [i for i, _, _ in contracts], "prices": {i: float(price) for i, _, _ in contracts},
               "capacity_gpus": 1000, "R": sorted(int(r) for r in R), "lam_s": float(lam)})
    P.update({"lam_s": float(lam)})
    cfg["borrowers"]["clients"] = [explicit_client([float(v) for v in demand])]
    inst = build_instance(cfg)
    with_capacity(inst, {site_index(inst, "R"): INF})
    validate(inst)
    return inst


def _a7_buy_slots(need, s_thr, keep=0.0):
    """The buy rule of code/analysis/a7_policy_sim.py::layer_cost_online (lines 21-39), without reclaims."""
    held, run, idle, out = False, 0, 0, []
    for t, nd in enumerate(need):
        run = run + 1 if nd else 0
        if not held and nd and run > s_thr:
            held, idle = True, 0
            out.append(t)
        if held:
            idle = 0 if nd else idle + 1
            if idle > keep:
                held = False
    return out


def test_bl2_vs_a7():
    """§15.4: on a 1-min synthetic instance with one client at level 1 (one replica layer) and lambda = 0,
    BL2's purchase slots equal a7's buy rule with s_thr = s0 (C2's s0 = 60 beta~ / (q_j - g a) minutes,
    one slot per minute); its releases may come one slot apart by design and are not compared."""
    rng = np.random.default_rng(17)
    d = []
    while len(d) < 240:
        d += [1.0] * int(rng.integers(1, 13)) + [0.0] * int(rng.integers(1, 6))
    d = d[:240]
    inst = _one_site(d)
    view = public_view(inst, "I1")
    l, k = site_index(inst, "R"), [c.id for c in inst.contracts].index("rev")
    s0 = 60.0 * float(view.beta_tilde_usd[0, l, k]) / (view.llms[0].q_usd_per_h - float(view.price[l, k]))
    assert 1 < s0 < 12 and abs(s0 - round(s0)) > 1e-6
    res = _sim(inst, _make("BL2", {}, inst))
    got = sorted(L.start_slot for L in res.leases)
    want = _a7_buy_slots([x > 0 for x in d], s0)
    assert got == want and len(want) > 3, (got, want)


# ---------------------------------------------------------------- BL3
def _bl3_instance():
    """Three synthetic lenders (zones) L0, L1, L2 with one site each and prices 2.85 < 2.9 < 3.0, the toy's
    protected site; clients c0, c1 of LLM M (g = 1) and c2 of M2 (g = 2), all in r0."""
    cfg = toy_config()
    L2 = copy.deepcopy(cfg["lenders"][1])
    L2.update({"id": "L2", "group": "g2", "prices": {"short": 3.0, "long": 3.2}, "R": []})
    cfg["lenders"].insert(2, L2)
    for L in cfg["lenders"][:3]:
        L.update({"capacity_gpus": 64, "R": []})
    cfg["llms"] = [explicit_llm("M", 1), explicit_llm("M2", 2)]
    T_f = cfg["time"]["horizon_min"] // cfg["time"]["fast_slot_min"]
    cfg["borrowers"]["clients"] = [explicit_client([0.0] * T_f, "M", borrower="b0"),
                                   explicit_client([0.0] * T_f, "M", borrower="b1"),
                                   explicit_client([0.0] * T_f, "M2", borrower="b2")]
    return build_instance(cfg)


def _obs(inst, t, leases=(), replicas=(), notices=(), ended=(), results=()):
    return SlowObs(t=t, minute=t * inst.grid.slow_min, demand=np.zeros((inst.n, inst.grid.phi)),
                   leases={L.id: L for L in leases}, replicas={r.id: r for r in replicas}, notices=list(notices),
                   ended=list(ended), results=list(results), site_announced=None,
                   served_prev=np.zeros((inst.J, inst.m)), fallback_prev=np.zeros(inst.n), cost_so_far=0.0)


def test_bl3_lists():
    """§15.5 (M43, M55): one pool per (LLM, usable-site set), so one N_Extra per pool (2 launches per pool,
    not per client); launches go to the cheapest zone of Z_A not used by the pool's replicas; a notice on a
    pool lease preempts its zone (Z_A -> Z_P); a violation death preempts its zone too; when |Z_A| < 2
    the lists are rebalanced (Z_A <- Z_A u Z_P, Z_P <- {})."""
    inst = _bl3_instance()
    view = public_view(inst, "I1")
    pol = _make("BL3", {"n_extra": 2}, inst)
    pol.reset(view, np.random.default_rng(0))
    zone = {l: s.lender for l, s in enumerate(view.sites)}
    acts0 = pol.act(_obs(inst, 0))
    buys = [(i, a) for i, a in enumerate(acts0) if isinstance(a, Buy)]
    assert len(buys) == 4, acts0                                 # 2 pools x N_Extra = 2
    rep = pol.report()
    pools = sorted(rep["pools"], key=lambda p: p["llm"])
    assert [sorted(p["clients"]) for p in pools] == [[0, 1], [2]]
    for p in pools:
        sites = [a.site for _, a in buys if a.llm == p["llm"]]
        assert len(sites) == 2 and len({zone[s] for s in sites}) == 2, sites       # used zones excluded
        assert {zone[s] for s in sites} == {"L0", "L1"}                            # the two cheapest zones
    # t = 1: results; leases alive and loading
    leases, results, reps = {}, [], []
    for n, (i, a) in enumerate(buys):
        lid = 100 + n
        leases[lid] = LeaseView(id=lid, site=a.site, contract=a.contract, gpus=inst.llms[a.llm].g * a.n_replicas,
                                start_slot=0, start_min=0, prepaid_end_min=10, announce_slot=None, death_min=None,
                                replicas=(lid * 10,))
        reps.append(ReplicaView(id=lid * 10, lease_id=lid, llm=a.llm, state="loading", load_start_min=0,
                                warm_fast=99, admission=1.0, drain_min=None))
        results.append(ActionResult(index=i, action=a, ok=True, lease_id=lid, replica_ids=(lid * 10,), reason=""))
    assert [a for a in pol.act(_obs(inst, 1, leases.values(), reps, results=results)) if isinstance(a, Buy)] == []
    p0 = min(rep["pools"], key=lambda p: p["llm"])["id"]
    l_L0 = [lid for lid, L in leases.items() if zone[L.site] == "L0" and inst.llms[0].g == L.gpus][0]
    # t = 2: a notice on pool 0's lease in zone L0: preempt L0, relaunch in the unused zone L2
    n0 = Notice(lease_id=l_L0, r_slot=2, death_min=2 * inst.grid.slow_min + 5)
    a2 = pol.act(_obs(inst, 2, leases.values(), reps, notices=[n0]))
    rep = pol.report()
    P0 = [p for p in rep["pools"] if p["id"] == p0][0]
    assert [2, p0, "preempt", "L0"] in rep["events"]
    assert P0["Z_P"] == ["L0"] and "L0" not in P0["Z_A"]
    new = [a for a in a2 if isinstance(a, Buy)]
    assert len(new) == 1 and zone[new[0].site] == "L2" and new[0].llm == 0, a2
    # t = 3: pool 0's lease in zone L1 died by a violation: preempt L1, |Z_A| = 1 < 2, rebalance
    l_L1 = [lid for lid, L in leases.items() if zone[L.site] == "L1" and L.gpus == 1][0]
    alive = [L for lid, L in leases.items() if lid != l_L1]
    i_new = [i for i, a in enumerate(a2) if isinstance(a, Buy)][0]
    L_new = LeaseView(id=200, site=new[0].site, contract=new[0].contract, gpus=1, start_slot=2, start_min=10,
                      prepaid_end_min=20, announce_slot=None, death_min=None, replicas=(2000,))
    res3 = [ActionResult(index=i_new, action=new[0], ok=True, lease_id=200, replica_ids=(2000,), reason="")]
    pol.act(_obs(inst, 3, alive + [L_new], reps, ended=[(l_L1, 15, "violation")], results=res3))
    rep = pol.report()
    P0 = [p for p in rep["pools"] if p["id"] == p0][0]
    assert [3, p0, "preempt", "L1"] in rep["events"] and [3, p0, "rebalance", None] in rep["events"], rep["events"]
    assert sorted(P0["Z_A"]) == ["L0", "L1", "L2"] and P0["Z_P"] == []


# ---------------------------------------------------------------- BL4
def test_bl4_rounding():
    """§15.6: the rounding n = floor(n+) + Bernoulli(frac) is unbiased within 4 standard errors over 2,000
    aux seeds and keeps kept counts in [pre, held]; omega by hand for a load longer than one slow slot; the
    repair respects capacity and never removes a pre lease; through the engine BL4 buys single-replica
    leases only and reaches a protected-only site through its arcs; the oracle variant is labeled
    lookahead-60min."""
    from sublet.baselines.cocar import omega_share, repair_counts, round_counts
    vals, lo, hi = [0.3, 1.7, 2.5, 1.4], [0, 0, 0, 1], [np.inf, np.inf, np.inf, 2]
    S = 2000
    draws = np.array([round_counts(vals, lo, hi, np.random.default_rng(s)) for s in range(S)])
    for i, v in enumerate(vals):
        x = draws[:, i]
        assert set(np.unique(x)) <= {math.floor(v), math.ceil(v)}
        se = x.std(ddof=1) / math.sqrt(S)
        assert abs(x.mean() - v) <= 4 * se, (v, x.mean(), se)
    assert draws[:, 3].min() >= 1 and draws[:, 3].max() <= 2
    assert np.all(round_counts([1.0, 2.0], [1, 2], [1, 2], np.random.default_rng(0)) == [1, 2])
    # omega: lambda = 600 s and 420 s on 5-min slots
    assert [omega_share(600.0, i, 5) for i in range(4)] == [0.0, 0.0, 1.0, 1.0]
    assert [round(omega_share(420.0, i, 5), 12) for i in range(3)] == [0.0, 0.6, 1.0]
    # repair: site 0 has capacity 4 GPUs; three triples there with g = 1, 2, 1
    new, keep, removed = repair_counts([0, 0, 0], [1.0, 2.0, 1.0], np.array([2, 1, 0]), np.array([0, 0, 2]),
                                       np.array([0, 0, 2]), [5.0, 1.0, 0.0], [0.0, 0.0, 0.0], {0: 4.0})
    assert (1 * (new[0] + keep[0]) + 2 * (new[1] + keep[1]) + 1 * (new[2] + keep[2])) <= 4
    assert keep[2] == 2 and removed >= 1 and new[1] == 0             # the smallest benefit goes first; pre kept
    # engine: a client whose only SLO-feasible site is the protected site P; demand on most slots
    cfg = toy_config()
    for L in cfg["lenders"][:2]:
        L["region"] = "r1"
    cfg["regions"]["list"] = ["r0", "r1"]
    cfg["regions"]["adjacency"] = []
    cfg["time"]["horizon_min"] = 240
    cfg["prices"]["a_protected_usd_per_gpu_h"] = 4.0
    cfg["lenders"][2]["lam_s"] = 60.0
    cfg["borrowers"]["clients"][0]["demand"]["values"] = [1.0] * 48
    inst = build_instance(cfg)
    view = public_view(inst, "I1")
    lp = site_index(inst, "P")
    assert np.isfinite(view.client_delta_usd_per_h[0, lp])
    assert not np.isfinite(view.client_delta_usd_per_h[0, site_index(inst, "L0")])
    res = _sim(inst, _make("BL4", {}, inst))
    bl4 = [L for L in res.leases if L.tag.startswith("bl4")]
    assert bl4 and all(L.site == lp for L in bl4)
    assert all(L.gpus == inst.llms[0].g for L in res.leases)
    # the oracle variant
    assert registry.info_class("BL4", {"demand": "oracle"}) == "lookahead-60min"
    pol = _make("BL4", {"demand": "oracle"}, inst)
    _sim(inst, pol)
    assert pol.report()["info_class"] == "lookahead-60min"


# ---------------------------------------------------------------- BL5
def _rr_rule(dbar, c, M, deaths=()):
    """Fetch and evict slots of §15.7 on a scalar sequence (use_current_slot False): at slot t the rule uses
    slots l <= t - 1; fetch iff not hosting and P(t-1) - min_{t_evict < tau <= t-1} P(tau-1) >= M (then
    t_fetch = t - 1); evict iff hosting and P(t-1) - max_{t_fetch < tau <= t-1} P(tau-1) < -M (then
    t_evict = t - 1); a death observed at slot t is a forced eviction (hosting off, t_evict = t)."""
    g = [x - c for x in dbar]                      # x (1 - delta/q) - c with delta = 0, x = min(dbar, 1)
    P = np.concatenate([[0.0], np.cumsum(g)])     # P[i + 1] = P(i), P[0] = P(-1)
    Pf = lambda i: float(P[i + 1])
    hosting, mark, fetch, evict = False, -1, [], []
    for t in range(len(dbar)):
        if t in deaths and hosting:
            hosting, mark = False, t
            continue
        taus = range(mark + 1, t)
        if not taus:
            continue
        if not hosting and Pf(t - 1) - min(Pf(tau - 1) for tau in taus) >= M:
            hosting, mark = True, t - 1
            fetch.append(t)
        elif hosting and Pf(t - 1) - max(Pf(tau - 1) for tau in taus) < -M:
            hosting, mark = False, t - 1
            evict.append(t)
    return fetch, evict


def test_bl5_vs_alg1():
    """§15.7: on one unlimited synthetic site with lambda = 0 and a billed term of one slot, BL5's fetch slots
    (lease starts) and evict slots (releases) equal a direct transcription of the rule on the scalar
    sequence dbar (one replica layer); a reclaim death forces an eviction, after which a re-fetch needs
    fresh evidence."""
    rng = np.random.default_rng(5)
    d = []
    while len(d) < 200:
        d += [float(v) for v in rng.uniform(0.6, 1.0, int(rng.integers(5, 25)))] + \
             [float(v) for v in rng.uniform(0.0, 0.2, int(rng.integers(5, 25)))]
    d = [round(x, 3) for x in d[:200]]
    for R in ((), None):
        if R is None:
            inst0 = _one_site(d, slot_min=5, contracts=(("rev", 5, 0),), beta_jl=0.5)
            res0 = _sim(inst0, _make("BL5", {}, inst0))
            first = min(res0.leases, key=lambda L: L.start_slot)
            R = (first.start_slot + 2,)
        inst = _one_site(d, slot_min=5, contracts=(("rev", 5, 0),), beta_jl=0.5, R=R)
        view = public_view(inst, "I1")
        l, k = site_index(inst, "R"), 0
        q = view.llms[0].q_usd_per_h
        c = view.llms[0].g * float(view.price[l, k]) / q
        M = 60.0 * float(view.beta_tilde_usd[0, l, k]) / (q * view.grid.slow_min)
        res = _sim(inst, _make("BL5", {}, inst))
        deaths = {L.end_min // 5 for L in res.leases if L.end_cause == "reclaim"}
        assert len(deaths) == len(R), (R, deaths)
        fetch, evict = _rr_rule(d, c, M, deaths)
        got_f = sorted(L.start_slot for L in res.leases)
        got_e = sorted(L.release_min // 5 for L in res.leases if L.end_cause == "release")
        assert got_f == fetch and got_e == evict and len(fetch) > 2, (R, got_f, fetch, got_e, evict)


# ---------------------------------------------------------------- BL6, BL7, siloed: c4_lower (b)-(d)
def test_bl6_c4_lower_c():
    """Check 3j: single(48, [(2, H)], 20.0, [1.0]), H in {0, 1, 2, 4, 8}, schedule eager, policy seeds 0-3:
    BL6 (inner A2, rbar = 1) engine total / core.opt_eager equals c4_lower.json c[*].ratio (1e-9)."""
    import check_c4_lower
    assert [r["H"] for r in C4["c"]] == [0, 1, 2, 4, 8]
    for ref in C4["c"]:
        I = check_c4_lower.single(48, [(2, ref["H"])], 20.0, [1.0])
        opt = core.opt_eager(I)["fun"]
        inst = _core(I)
        for s in range(4):
            pol = _make("BL6", {"inner": "A2", "inner_params": {"rbar": 1}}, inst)
            r = _sim(inst, pol, schedule="eager", rng=np.random.default_rng(s)).components["total"] / opt
            assert _close(r, ref["ratio"]), (ref["H"], s, r, ref["ratio"])


def test_bl7_c4_lower_b():
    """Check 3i: the four (b) instances (beta in {2, 6, 14, 30}), schedule eager, policy seeds 0-9: BL7
    (inner A2, rbar = 1) engine total / full-menu core.opt_eager equals c4_lower.json b[*].ratio (1e-9)."""
    for ref in C4["b"]:
        I, _ = c4l_b(ref["beta"])
        full = core.opt_eager(I)["fun"]
        inst = _core(I)
        for s in range(10):
            pol = _make("BL7", {"inner": "A2", "inner_params": {"rbar": 1}}, inst)
            r = _sim(inst, pol, schedule="eager", rng=np.random.default_rng(s)).components["total"] / full
            assert _close(r, ref["ratio"]), (ref["beta"], s, r, ref["ratio"])


def test_siloed_c4_lower_d():
    """Check 3k: the instances of part_d_constructed (b in {1, 2, 4, 8, 16}): run_siloed(A2, rbar = 1) total /
    shared core.opt_eager equals c4_lower.json d[*].ratio (1e-9), and shared A2 / OPT = 1."""
    for ref in C4["d"]:
        I = c4l_d(ref["b"])
        opt = core.opt_eager(I)["fun"]
        inst = _core(I)
        d = run_siloed(inst, lambda sub: _make("A2", {"rbar": 1}, sub), LenderModel(schedule="eager"),
                       EngineConfig(), lender_seed=0, policy_seed=0)
        assert not d["invariant_failures"] and len(d["borrowers"]) == ref["b"]
        assert _close(d["components"]["total"] / opt, ref["ratio"]), (ref["b"], d["components"]["total"] / opt)
        sh = _sim(inst, _make("A2", {"rbar": 1}, inst), schedule="eager")
        assert _close(sh.components["total"] / opt, 1.0)


# ---------------------------------------------------------------- random lines (checks 3i-3l, slow)
def _eager_value(I):
    r = solve_eager(_core(I), **MILP_KW)
    assert r.status == 0, r.status_msg
    return r


def _notice_oblivious(I):
    """The class value of C3-P6 as an eager instance: H' = 0, a' = a D / tau (§17.2)."""
    J = copy.deepcopy(I)
    tau, H = np.asarray(I.tau), np.asarray(I.H)
    J.a = np.asarray(I.a, dtype=float) * ((tau + H) / tau)[None, :]
    J.H = np.zeros_like(H)
    return J


def _b_random(seed):
    return core.random_instance(np.random.default_rng(9000 + seed), T=36, m=4, J=2, n=8)


def _c_random(seed):
    return core.random_instance(np.random.default_rng(9100 + seed), T=36, m=4, J=2, n=8,
                                contracts=[(1, 2, 1.0), (4, 4, 1.25), (12, 6, 1.6)])


def _d_random(seed, b):
    return core.random_instance(np.random.default_rng(9200 + seed), T=36, m=4, J=1, n=16, n_borrowers=b)


@pytest.mark.slow
def test_c4_lower_random_offline(capsys):
    """Checks 3i-3k offline: b_random (solve_eager on the contract subsets [0, 1] and [0] over the full menu),
    c_random (the notice-oblivious transform over solve_eager) and d_random (per-owner solve_eager summed over
    shared) equal the per-seed JSON ratios within 2e-4 relative (the reference MILPs ran at mip_rel_gap
    1e-4, the build at 1e-9); the largest deviation is reported."""
    dev = {}
    for ref in C4["b_random"]:
        I = _b_random(ref["seed"])
        full = _eager_value(I).objective
        for key, sub in (("rev_over_full", [0, 1]), ("spot_over_full", [0])):
            v = _eager_value(I.subset(contracts=sub)).objective / full
            assert _close(v, ref[key], TOL_MILP), ("b_random", ref["seed"], key, v, ref[key])
            dev[("b", ref["seed"], key)] = abs(v - ref[key]) / ref[key]
    for ref in C4["c_random"]:
        I = _c_random(ref["seed"])
        v = _eager_value(_notice_oblivious(I)).objective / _eager_value(I).objective
        assert _close(v, ref["ratio"], TOL_MILP), ("c_random", ref["seed"], v, ref["ratio"])
        dev[("c", ref["seed"])] = abs(v - ref["ratio"]) / ref["ratio"]
    for ref in C4["d_random"]:
        I = _d_random(ref["seed"], ref["b"])
        silo = sum(_eager_value(I.subset(clients=np.nonzero(I.owner == o)[0])).objective
                   for o in range(ref["b"]) if np.any(I.owner == o))
        v = silo / _eager_value(I).objective
        assert _close(v, ref["ratio"], TOL_MILP), ("d_random", ref["seed"], ref["b"], v, ref["ratio"])
        dev[("d", ref["seed"], ref["b"])] = abs(v - ref["ratio"]) / ref["ratio"]
    worst = max(dev, key=dev.get)
    with capsys.disabled():
        print(f"\n[test_c4_lower_random_offline] largest relative deviation {dev[worst]:.3e} at {worst}")


@pytest.mark.slow
def test_c4_lower_random_online_ge_offline():
    """Check 3l: on the random instances of (b)-(d), under schedule eager, the online costs are at least the
    offline class values (lower end: the MILP's dual bound, -1e-9 relative): A2 (rbar = 1) on the contract
    subsets and BL7 (inner A2) on the full menu, policy seeds 0-9; BL6 (inner A2) policy seeds 0-3 against the
    notice-oblivious class value; siloed A2 policy seeds 0-9 against the sum of per-owner OPT."""
    def low(r):
        return (r.dual_bound if r.dual_bound is not None else r.objective) * (1 - 1e-9) - 1e-9

    for ref in C4["b_random"]:
        I = _b_random(ref["seed"])
        for sub in ([0, 1], [0], None):
            Isub = I if sub is None else I.subset(contracts=sub)
            lb = low(_eager_value(Isub))
            inst = _core(Isub)
            for s in range(10):
                pid, params = ("BL7", {"inner": "A2", "inner_params": {"rbar": 1}}) if sub is None else ("A2", {"rbar": 1})
                tot = _sim(inst, _make(pid, params, inst), schedule="eager", rng=np.random.default_rng(s)).components["total"]
                assert tot >= lb, ("b_random", ref["seed"], sub, s, tot, lb)
    for ref in C4["c_random"]:
        I = _c_random(ref["seed"])
        lb = low(_eager_value(_notice_oblivious(I)))
        inst = _core(I)
        for s in range(4):
            pol = _make("BL6", {"inner": "A2", "inner_params": {"rbar": 1}}, inst)
            tot = _sim(inst, pol, schedule="eager", rng=np.random.default_rng(s)).components["total"]
            assert tot >= lb, ("c_random", ref["seed"], s, tot, lb)
    for ref in C4["d_random"]:
        I = _d_random(ref["seed"], ref["b"])
        lb = sum(low(_eager_value(I.subset(clients=np.nonzero(I.owner == o)[0])))
                 for o in range(ref["b"]) if np.any(I.owner == o))
        inst = _core(I)
        for s in range(10):
            d = run_siloed(inst, lambda sub: _make("A2", {"rbar": 1}, sub), LenderModel(schedule="eager"),
                           EngineConfig(), lender_seed=s, policy_seed=s)
            assert not d["invariant_failures"]
            assert d["components"]["total"] >= lb, ("d_random", ref["seed"], ref["b"], s, d["components"]["total"], lb)


# ---------------------------------------------------------------- §15.1 common rules
def _hobs(inst, t, D=None, leases=(), replicas=(), notices=(), ended=(), results=()):
    """SlowObs at slot t with every client's fast slots at demand D[c] (default 0)."""
    n, phi = inst.n, inst.grid.phi
    dem = np.zeros((n, phi)) if D is None else np.repeat(np.asarray(D, dtype=float).reshape(n, 1), phi, axis=1)
    return SlowObs(t=t, minute=t * inst.grid.slow_min, demand=dem, leases={L.id: L for L in leases},
                   replicas={r.id: r for r in replicas}, notices=list(notices), ended=list(ended),
                   results=list(results), site_announced=None, served_prev=np.zeros((inst.J, inst.m)),
                   fallback_prev=np.zeros(n), cost_so_far=0.0)


def test_kstar_usable_and_ties():
    """§15.1: k*(l) minimizes (a_lk, P_k, -H_k, k): with equal price and billed term the longest notice wins,
    with equal price the shorter billed term wins; a usable arc needs delta + g a_{l k*} < q_j; equal site
    scores are broken by the site order pi (M7), not by the index."""
    from sublet.baselines.common import SiteTable, k_star
    ids = lambda inst: [c.id for c in inst.contracts]
    inst = toy_instance({"billing": "per_slot", "lenders.0.prices.long": 2.85})
    v = public_view(inst, "I1")
    assert v.contracts[0].prepaid_min == v.contracts[1].prepaid_min
    assert k_star(v)[site_index(inst, "L0")] == ids(inst).index("long")          # H 10 > H 5
    inst2 = toy_instance({"lenders.0.prices.long": 2.85})                          # prepaid_D: P 10 < 20
    v2 = public_view(inst2, "I1")
    assert v2.contracts[0].prepaid_min < v2.contracts[1].prepaid_min
    assert k_star(v2)[site_index(inst2, "L0")] == ids(inst2).index("short")
    assert k_star(v2)[site_index(inst2, "P")] == -1                                 # only a flagged contract
    hi = toy_instance({"lenders.0.prices.short": 7.5, "lenders.0.prices.long": 7.6})  # g a > q = 7.15
    st = SiteTable(public_view(hi, "I1"), np.arange(hi.m))
    assert not st.usable[0, site_index(hi, "L0")] and st.usable[0, site_index(hi, "L1")]
    tie = toy_instance({"lenders.1.prices.short": 2.85, "lenders.1.prices.long": 3.0})
    vt = public_view(tie, "I1")
    l0, l1 = site_index(tie, "L0"), site_index(tie, "L1")
    st = SiteTable(vt, np.array([l1, l0, site_index(tie, "P")]))
    assert st.score[0, l0] == st.score[0, l1]
    assert st.best_static(0) == l1
    assert SiteTable(vt, np.arange(tie.m)).best_static(0) == l0


def test_bl1_target_and_release_order():
    """§15.3: N_c = ceil(D_c - 1e-9) (D the slot maximum, or the mean with demand_stat 'mean'); the surplus is
    released highest rent rate first (L1's 2.9 before L0's 2.85)."""
    from sublet.baselines.greedy import GreedyLease
    inst = toy_instance()
    pol = GreedyLease()
    pol.reset(public_view(inst, "I1"), np.random.default_rng(0))
    for D, want in ((1.0, 1), (1.2, 2), (0.0, 0), (1e-12, 0), (2.0, 2)):
        assert list(pol.target(_hobs(inst, 0, [D]))) == [want], D
    fast = toy_instance({"time.fast_slot_min": 1, "borrowers.clients.0.demand.values": [0.0] * 120})
    for stat, want in (("max", 2), ("mean", 1)):
        p = GreedyLease(demand_stat=stat)
        p.reset(public_view(fast, "I1"), np.random.default_rng(0))
        obs = _hobs(fast, 0)
        obs.demand[0, :] = [2.0, 0.0, 0.0, 0.0, 0.0]
        assert list(p.target(obs)) == [want], stat
    # release order: L0 at 1 GPU, demand 2 buys at L0 and L1; at t = 1 (past the 5-min prepaid term of
    # per_slot billing) demand 1 releases the dearer L1 lease
    cap = toy_instance({"lenders.0.capacity_gpus": 1, "lenders.0.R": [], "lenders.1.R": [], "billing": "per_slot"})
    v = public_view(cap, "I1")
    pol = GreedyLease()
    pol.reset(v, np.random.default_rng(0))
    a0 = [a for a in pol.act(_hobs(cap, 0, [2.0])) if isinstance(a, Buy)]
    assert sorted(a.site for a in a0) == sorted([site_index(cap, "L0"), site_index(cap, "L1")])
    leases = [LeaseView(10 + i, a.site, a.contract, 1, 0, 0, 5, None, None, ()) for i, a in enumerate(a0)]
    res = [ActionResult(i, a, True, 10 + i, (), "") for i, a in enumerate(a0)]
    from sublet.types import Release
    acts = pol.act(_hobs(cap, 1, [1.0], leases=leases, results=res))
    dear = [L.id for L in leases if L.site == site_index(cap, "L1")][0]
    assert [a for a in acts if isinstance(a, Release)] == [Release(dear)], acts


def test_refusal_marks_site_unavailable():
    """§15.1: a refused (or pre-check dropped) Buy marks its site unavailable to the baseline for the slot in
    which it is reported: BL1 and BL5 re-buy at the other site in that slot; BL3 launches in another zone."""
    from sublet.baselines.greedy import GreedyLease
    from sublet.baselines.retrorenting import RetroRentingStyle
    inst = toy_instance({"lenders.0.R": [], "lenders.1.R": []})
    v = public_view(inst, "I1")
    for cls in (GreedyLease, RetroRentingStyle):
        pol = cls()
        pol.reset(v, np.random.default_rng(0))
        first, t = [], 0
        while not first:
            first = [a for a in pol.act(_hobs(inst, t, [1.0])) if isinstance(a, Buy)]
            t += 1
            assert t < 20, cls
        l0 = first[0].site
        r = ActionResult(0, first[0], False, None, (), "capacity")
        again = [a for a in pol.act(_hobs(inst, t, [1.0], results=[r])) if isinstance(a, Buy)]
        assert len(again) == 1 and again[0].site != l0, (cls.__name__, l0, again)
        assert pol.report()["counts"]["refused"] == 1
    # BL3: the pool-0 launch in zone L0 is refused at t = 1: the relaunch goes to the unused zone L2
    inst3 = _bl3_instance()
    v3 = public_view(inst3, "I1")
    pol = _make("BL3", {"n_extra": 2}, inst3)
    pol.reset(v3, np.random.default_rng(0))
    zone = {l: s.lender for l, s in enumerate(v3.sites)}
    acts0 = pol.act(_obs(inst3, 0))
    buys = [(i, a) for i, a in enumerate(acts0) if isinstance(a, Buy)]
    i_ref, b_ref = next((i, a) for i, a in buys if a.llm == 0 and zone[a.site] == "L0")
    leases, results, reps = [], [], []
    for n, (i, a) in enumerate(buys):
        if i == i_ref:
            results.append(ActionResult(i, a, False, None, (), "capacity"))
            continue
        lid = 100 + n
        leases.append(LeaseView(lid, a.site, a.contract, inst3.llms[a.llm].g, 0, 0, 10, None, None, (lid * 10,)))
        reps.append(ReplicaView(lid * 10, lid, a.llm, "loading", 0, 99, 1.0, None))
        results.append(ActionResult(i, a, True, lid, (lid * 10,), ""))
    a1 = [a for a in pol.act(_obs(inst3, 1, leases, reps, results=results)) if isinstance(a, Buy)]
    assert len(a1) == 1 and a1[0].llm == 0 and zone[a1[0].site] == "L2", a1


def test_rule_br():
    """§15.1 rule BR (M41): with tau 5 min and H 30 min (billed term 35 min) and demand on in slots 0, 3, 4
    only, the release decided at slot 1 is deferred to the first slot at or after the billed term, cancelled
    when the demand returns at slot 3 (one lease, no re-buy), and executed at minute 35 after the demand ends
    (BL1, BL2, BL3 with n_extra 0 and no hysteresis; BL5, which fetches one slot later, at minute 40); with
    defer_release=False every policy releases inside the billed term and buys a second lease."""
    from fixtures import explicit_client
    cfg = toy_config()
    cfg["time"]["horizon_min"] = 5 * 18
    cfg["time"]["fast_slot_min"] = 1
    cfg["contracts"][0].update({"tau_min": 5, "H_min": 30})
    for L in cfg["lenders"][:2]:
        L.update({"R": [], "lam_s": 0.0})
    cfg["lenders"][2]["lam_s"] = 0.0
    dA = [1, 0, 0, 1, 1] + [0] * 13
    cfg["borrowers"]["clients"] = [explicit_client([float(x) for x in dA for _ in range(5)])]
    inst = build_instance(cfg)
    for pid, extra, start in (("BL1", {}, 0), ("BL2", {}, 0), ("BL3", {"n_extra": 0, "hysteresis_min": 0}, 0),
                              ("BL5", {}, 1)):
        res = _sim(inst, _make(pid, {**extra, "defer_release": True}, inst))
        got = [(L.start_slot, L.prepaid_end_min, L.release_min) for L in res.leases]
        assert got == [(start, 5 * start + 35, 5 * start + 35)], (pid, got)
        res = _sim(inst, _make(pid, {**extra, "defer_release": False}, inst))
        assert len(res.leases) == 2 and all(L.release_min < L.prepaid_end_min for L in res.leases), \
            (pid, [(L.start_slot, L.prepaid_end_min, L.release_min) for L in res.leases])


# ---------------------------------------------------------------- BL2, BL1 against a7 with releases and reclaims
def _a7_layer(need, kills, s_thr, keep, tau=1):
    """a7_policy_sim.layer_cost_online's rule (lines 21-39) with the engine's timing on 1-min slots: a reclaim
    at t ends a lease bought at s iff t >= s + tau; the purchase test does not read availability; a release
    decided at t takes effect at t. Returns (buy, release, death) minutes."""
    held, run, idle, s = False, 0, 0, None
    buys, rels, deaths = [], [], []
    for t in range(len(need)):
        if held and t in kills and t >= s + tau:
            held = False
            deaths.append(t)
        run = run + 1 if need[t] else 0
        if held:
            idle = 0 if need[t] else idle + 1
            if idle > keep:
                held = False
                rels.append(t)
        if not held and need[t] and run > s_thr:
            held, idle, s = True, 0, t
            buys.append(t)
    return buys, rels, deaths


def test_bl1_bl2_vs_a7_with_reclaims():
    """§15.3, §15.4 against a7's layer rule (reclaims included): integer demand of nested layers (levels 0-3)
    on one unlimited site at 1-min slots (tau 1 min, H 0, lambda 0), random reclaim slots: BL1 (threshold 0),
    BL2 (threshold s0) and BL2 with keep='s0' have the purchase, release and death minutes of a7's rule
    summed over the layers."""
    rng = np.random.default_rng(23)
    for case in range(3):
        T = 240
        D = np.zeros(T)
        t = 0
        while t < T:
            n = int(rng.integers(3, 25))
            D[t:t + n] = int(rng.integers(0, 4))
            t += n
        kills = sorted(int(x) for x in np.flatnonzero(rng.random(T) < 0.04))
        inst = _one_site(D, R=kills, beta_jl=0.3)
        view = public_view(inst, "I1")
        l = site_index(inst, "R")
        q = view.llms[0].q_usd_per_h
        s0 = 60.0 * float(view.beta_tilde_usd[0, l, 0]) / (q - float(view.price[l, 0]))
        for pid, params, s_thr, keep in (("BL1", {}, 0.0, 0), ("BL2", {}, s0, 0), ("BL2", {"keep": "s0"}, s0, s0)):
            res = _sim(inst, _make(pid, params, inst))
            got = (sorted(L.start_slot for L in res.leases),
                   sorted(L.end_min for L in res.leases if L.end_cause == "release"),
                   sorted(L.end_min for L in res.leases if L.end_cause == "reclaim"))
            want = [[], [], []]
            for k in range(1, 4):
                b, r, d = _a7_layer([x >= k for x in D], set(kills), s_thr, keep)
                want[0] += b
                want[1] += r
                want[2] += d
            want = tuple(sorted(x) for x in want)
            assert got == want, (case, pid, params, [sorted(set(g) ^ set(w))[:8] for g, w in zip(got, want)])
            assert got[2], (case, pid)                          # some reclaims happen


def test_bl2_keep_s0_and_rebuy_at_death():
    """§15.4: keep='s0' releases only after idle Δs > s0 (purchase slots of a7's rule with keep = s0, different
    from keep 0); a reclaim does not reset run_v, so an active layer re-buys in the slot where the death is
    observed."""
    rng = np.random.default_rng(17)
    d = []
    while len(d) < 240:
        d += [1.0] * int(rng.integers(1, 13)) + [0.0] * int(rng.integers(1, 6))
    d = d[:240]
    inst = _one_site(d)
    view = public_view(inst, "I1")
    l, k = site_index(inst, "R"), [c.id for c in inst.contracts].index("rev")
    s0 = 60.0 * float(view.beta_tilde_usd[0, l, k]) / (view.llms[0].q_usd_per_h - float(view.price[l, k]))
    res = _sim(inst, _make("BL2", {"keep": "s0"}, inst))
    got = sorted(L.start_slot for L in res.leases)
    assert got == _a7_buy_slots([x > 0 for x in d], s0, keep=s0)
    assert got != _a7_buy_slots([x > 0 for x in d], s0, keep=0.0)
    inst2 = _one_site([1.0] * 60, R=(20,))
    res2 = _sim(inst2, _make("BL2", {}, inst2))
    dead = [L for L in res2.leases if L.end_cause == "reclaim"]
    assert len(dead) == 1 and dead[0].end_min == 20
    assert 20 in {L.start_slot for L in res2.leases}, [(L.start_slot, L.end_min, L.end_cause) for L in res2.leases]


# ---------------------------------------------------------------- BL3 details
def _bl3_obs(inst, t, dbar, leases=(), replicas=(), notices=(), ended=(), results=()):
    o = _obs(inst, t, leases, replicas, notices, ended, results)
    o.demand[:, :] = np.asarray(dbar, dtype=float)[:, None]
    return o


def _bl3_leases(inst, buys, t0, first_id, state="loading"):
    leases, reps, results = [], [], []
    for n, (i, a) in enumerate(buys):
        lid = first_id + n
        leases.append(LeaseView(lid, a.site, a.contract, inst.llms[a.llm].g, t0, 5 * t0, 5 * t0 + 10, None, None,
                                (lid * 10,)))
        reps.append(ReplicaView(lid * 10, lid, a.llm, state, 0, 99, 1.0, None))
        results.append(ActionResult(i, a, True, lid, (lid * 10,), ""))
    return leases, reps, results


def test_bl3_hysteresis_return_death_and_group():
    """§15.5 (M43): N_Tar follows N_Can only after ceil(hysteresis_min / Δs) = 2 consecutive slots above (or
    below) it; a preempted zone returns to Z_A when a pool replica there is first reported warm; with
    react_at='death' a notice preempts nothing and the death does; with zone='group' two lenders of one
    correlation group form one zone."""
    inst = _bl3_instance()
    v = public_view(inst, "I1")
    zone = {l: s.lender for l, s in enumerate(v.sites)}
    pol = _make("BL3", {"n_extra": 0}, inst)
    pol.reset(v, np.random.default_rng(0))
    ntar = []
    for t, d0 in enumerate([0, 1, 0, 1, 1, 1, 0, 0]):
        pol.act(_bl3_obs(inst, t, [d0, 0, 0]))
        ntar.append(min(pol.report()["pools"], key=lambda p: p["llm"])["N_tar"])
    assert ntar == [0, 0, 0, 0, 1, 1, 1, 0], ntar
    # zone return: pool 0 with N_Tar 2 + 2 spares launches L0, L1, L2, L0; one L0 lease dies (violation)
    pol = _make("BL3", {"n_extra": 2}, inst)
    pol.reset(v, np.random.default_rng(0))
    a0 = [(i, a) for i, a in enumerate(pol.act(_bl3_obs(inst, 0, [1.0, 1.0, 0.0]))) if isinstance(a, Buy)]
    p0 = [(i, a) for i, a in a0 if a.llm == 0]
    assert sorted(zone[a.site] for _, a in p0) == ["L0", "L0", "L1", "L2"], [zone[a.site] for _, a in p0]
    leases, reps, res = _bl3_leases(inst, a0, 0, 100)
    pol.act(_bl3_obs(inst, 1, [1.0, 1.0, 0.0], leases, reps, results=res))
    l0s = [L.id for L in leases if zone[L.site] == "L0" and L.gpus == 1]
    alive = [L for L in leases if L.id != l0s[0]]
    pol.act(_bl3_obs(inst, 2, [1.0, 1.0, 0.0], alive, reps, ended=[(l0s[0], 10, "violation")]))
    pid0 = min(pol.report()["pools"], key=lambda p: p["llm"])["id"]
    P0 = [p for p in pol.report()["pools"] if p["id"] == pid0][0]
    assert P0["Z_P"] == ["L0"], P0
    warm = [ReplicaView(r.id, r.lease_id, r.llm, "warm" if r.lease_id == l0s[1] else r.state, 0, 1, 1.0, None)
            for r in reps]
    pol.act(_bl3_obs(inst, 3, [1.0, 1.0, 0.0], alive, warm))
    rep = pol.report()
    assert [3, pid0, "return", "L0"] in rep["events"], rep["events"]
    P0 = [p for p in rep["pools"] if p["id"] == pid0][0]
    assert P0["Z_P"] == [] and sorted(P0["Z_A"]) == ["L0", "L1", "L2"]
    # react_at = 'death'
    for react, at_notice in (("notice", True), ("death", False)):
        pol = _make("BL3", {"n_extra": 2, "react_at": react}, inst)
        pol.reset(v, np.random.default_rng(0))
        a0 = [(i, a) for i, a in enumerate(pol.act(_bl3_obs(inst, 0, [0, 0, 0]))) if isinstance(a, Buy)]
        leases, reps, res = _bl3_leases(inst, a0, 0, 100)
        pol.act(_bl3_obs(inst, 1, [0, 0, 0], leases, reps, results=res))
        lid = [L.id for L in leases if zone[L.site] == "L0" and L.gpus == 1][0]
        pid0 = min(pol.report()["pools"], key=lambda p: p["llm"])["id"]
        pol.act(_bl3_obs(inst, 2, [0, 0, 0], leases, reps, notices=[Notice(lid, 2, 15)]))
        assert ([2, pid0, "preempt", "L0"] in pol.report()["events"]) == at_notice, react
        alive = [L for L in leases if L.id != lid]
        pol.act(_bl3_obs(inst, 3, [0, 0, 0], alive, reps, ended=[(lid, 15, "reclaim")]))
        ev = pol.report()["events"]
        assert any(e[1] == pid0 and e[2] == "preempt" and e[3] == "L0" for e in ev), (react, ev)
        if not at_notice:
            assert [3, pid0, "preempt", "L0"] in ev
    # zone = 'group': L0 and L1 in one correlation group
    cfg = toy_config()
    L2 = copy.deepcopy(cfg["lenders"][1])
    L2.update({"id": "L2", "group": "g2", "prices": {"short": 3.0, "long": 3.2}, "R": []})
    cfg["lenders"].insert(2, L2)
    cfg["lenders"][1]["group"] = "g0"
    for L in cfg["lenders"][:3]:
        L.update({"capacity_gpus": 64, "R": []})
    inst_g = build_instance(cfg)
    vg = public_view(inst_g, "I1")
    pol = _make("BL3", {"n_extra": 2, "zone": "group"}, inst_g)
    pol.reset(vg, np.random.default_rng(0))
    buys = [a for a in pol.act(_hobs(inst_g, 0)) if isinstance(a, Buy)]
    assert pol.report()["pools"][0]["zones"] == ["g0", "g2"]
    assert sorted(vg.sites[a.site].group for a in buys) == ["g0", "g2"], [vg.sites[a.site].id for a in buys]


# ---------------------------------------------------------------- BL4 details
def test_bl4_forecast_announced_and_keep_oldest():
    """§15.6: the 'previous' forecast is the previous window's slot means shifted by W, and slot 0's mean held
    constant in the first window; an announced held lease is not planned as owned (M44): absent from 'held',
    its GPUs off the site's capacity row; at a window start the kept count of past-term leases keeps the
    oldest (lowest id) and releases the rest."""
    from sublet.baselines.cocar import CoCaRStyle
    from sublet.types import Release
    inst = toy_instance({"time.fast_slot_min": 1, "borrowers.clients.0.demand.values": [0.0] * 120})
    v = public_view(inst, "I1")
    pol = CoCaRStyle(window_min=10)
    pol.reset(v, np.random.default_rng(0))
    means = [0.2, 0.8, 0.5]                       # slots 0-2: the window starting at t0 = 2 reads slots 0, 1
    for t, mu in enumerate(means):
        o = _hobs(inst, t)
        o.demand[0, :] = [mu * 5, 0, 0, 0, 0]
        pol.hist.push(o)
    assert np.allclose(pol._dhat(2, 2), [[means[0], means[1]]])
    pol2 = CoCaRStyle(window_min=10)
    pol2.reset(v, np.random.default_rng(0))
    o0 = _hobs(inst, 0)
    o0.demand[0, :] = [1.0, 0, 0, 0, 0]
    pol2.hist.push(o0)
    assert np.allclose(pol2._dhat(0, 2), [[0.2, 0.2]])
    # M44: an announced held lease
    toy = toy_instance()
    vt = public_view(toy, "I1")
    l0 = site_index(toy, "L0")
    k = [c.id for c in toy.contracts].index("short")
    pol3 = CoCaRStyle()
    pol3.reset(vt, np.random.default_rng(0))
    pol3.lease_triple = {5: (0, l0, k), 6: (0, l0, k)}
    ann = LeaseView(5, l0, k, 1, 0, 0, 10, 2, 30, ())
    held = LeaseView(6, l0, k, 1, 0, 0, 10, None, None, ())
    o = _hobs(toy, 0, [1.0], leases=[ann, held])
    pol3.hist.push(o)
    plan = pol3.plan_window(o)
    assert plan["held"][(0, l0, k)] == [6] and pol3.rep["announced_skipped"] == 1
    assert plan["cap"][l0] == float(vt.sites[l0].capacity_gpus) - 1
    # keep the oldest past-term leases: three held at t0 = 12 (past their billed term), kept count 1
    pol4 = CoCaRStyle()
    pol4.reset(vt, np.random.default_rng(0))
    tr = (0, l0, k)
    pol4.lease_triple = {9: tr, 3: tr, 5: tr}
    leases = [LeaseView(i, l0, k, 1, 0, 0, 10, None, None, ()) for i in (9, 3, 5)]
    pol4.plan_window = lambda obs: {"triples": [tr], "held": {tr: [9, 3, 5]}, "keep": [1], "new": [0]}
    acts = pol4.act(_hobs(toy, 12, [1.0], leases=leases))
    assert sorted(a.lease_id for a in acts if isinstance(a, Release)) == [5, 9], acts


# ---------------------------------------------------------------- BL5 options
def _rr_rule_opts(dbar, c, M, deaths=(), lookback=None, use_current=False):
    """_rr_rule with a look-back of u slots (RR_u: tau in (max(mark, idx - u), idx]) and the use_current_slot
    timing (idx = t: slot t is used and t_fetch = t; else idx = t - 1)."""
    g = [x - c for x in dbar]
    P = np.concatenate([[0.0], np.cumsum(g)])
    Pf = lambda i: float(P[i + 1])
    hosting, mark, fetch, evict = False, -1, [], []
    for t in range(len(dbar)):
        if t in deaths and hosting:
            hosting, mark = False, t
            continue
        idx = t if use_current else t - 1
        lo = mark if lookback is None else max(mark, idx - lookback)
        taus = range(lo + 1, idx + 1)
        if not taus:
            continue
        if not hosting and Pf(idx) - min(Pf(tau - 1) for tau in taus) >= M:
            hosting, mark = True, idx
            fetch.append(t)
        elif hosting and Pf(idx) - max(Pf(tau - 1) for tau in taus) < -M:
            hosting, mark = False, idx
            evict.append(t)
    return fetch, evict


def test_bl5_options():
    """§15.7: BL5 with lookback = u (RR_u) and with use_current_slot=True equals the rule transcribed with
    those options (fetch and evict slots), and both differ from the default; refetch_after_reclaim='immediate'
    re-buys in the death slot, the default needs fresh evidence first."""
    rng = np.random.default_rng(5)
    d = []
    while len(d) < 200:
        d += [float(v) for v in rng.uniform(0.6, 1.0, int(rng.integers(5, 25)))] + \
             [float(v) for v in rng.uniform(0.0, 0.2, int(rng.integers(5, 25)))]
    d = [round(x, 3) for x in d[:200]]
    inst = _one_site(d, slot_min=5, contracts=(("rev", 5, 0),), beta_jl=0.5)
    view = public_view(inst, "I1")
    l = site_index(inst, "R")
    q = view.llms[0].q_usd_per_h
    c = view.llms[0].g * float(view.price[l, 0]) / q
    M = 60.0 * float(view.beta_tilde_usd[0, l, 0]) / (q * view.grid.slow_min)
    base = _rr_rule_opts(d, c, M)
    for params, kw in (({"lookback": 3}, {"lookback": 3}), ({"use_current_slot": True}, {"use_current": True})):
        res = _sim(inst, _make("BL5", params, inst))
        got_f = sorted(L.start_slot for L in res.leases)
        got_e = sorted(L.release_min // 5 for L in res.leases if L.end_cause == "release")
        want = _rr_rule_opts(d, c, M, **kw)
        assert (got_f, got_e) == want and want != base, (params, got_f, want[0], got_e, want[1])
    res0 = _sim(inst, _make("BL5", {}, inst))
    first = min(res0.leases, key=lambda L: L.start_slot)
    R = (first.start_slot + 2,)
    instR = _one_site(d, slot_min=5, contracts=(("rev", 5, 0),), beta_jl=0.5, R=R)
    for mode, rebuy in (("immediate", True), ("rule", False)):
        res = _sim(instR, _make("BL5", {"refetch_after_reclaim": mode}, instR))
        dead = [L for L in res.leases if L.end_cause == "reclaim"]
        assert len(dead) == 1
        t_d = dead[0].end_min // 5
        assert (t_d in {L.start_slot for L in res.leases}) == rebuy, (mode, t_d, sorted(L.start_slot for L in res.leases))


# ---------------------------------------------------------------- BL6 and BL8
def test_bl6_release_at_notice_and_blind():
    """§15.8 (M46): BL6 (inner A1, per_slot billing, H = 60 min) releases a noticed lease at the notice slot r
    (release_min = r Δs) and shows the inner the slot of an H = 0 notice: the lease absent, its end
    (lease, r Δs, 'reclaim') in obs.ended and the notice with death_min = r Δs; with mode 'notice_blind' the inner
    sees no notice and no announce_slot or death_min, and the lease lives until its death."""
    from fixtures import onesite_c2
    r = 8
    inst, _ = onesite_c2([1.0] * 30, [r], H_min=60, billing="per_slot")
    seen = {}
    for mode in ("as_if_H0", "notice_blind"):
        pol = _make("BL6", {"inner": "A1", "mode": mode, "inner_params": {"insure": "never"}}, inst)
        rec = []
        o = pol.inner.act
        pol.inner.act = lambda obs, o=o, rec=rec: (rec.append(obs), o(obs))[1]
        res = _sim(inst, pol)
        ann = [L for L in res.leases if L.announce_slot == r]
        assert len(ann) == 1, (mode, [(L.start_slot, L.announce_slot) for L in res.leases])
        L = ann[0]
        at_r = [x for x in rec if x.t == r][0]
        if mode == "as_if_H0":
            assert L.end_cause == "release" and L.release_min == r * 5, L
            assert L.id not in at_r.leases and (L.id, r * 5, "reclaim") in at_r.ended
            assert [(n.lease_id, n.death_min) for n in at_r.notices] == [(L.id, r * 5)]
            assert pol.report()["released_at_notice"] == 1
        else:
            assert L.end_cause == "reclaim" and L.end_min == r * 5 + 60, L
            assert all(x.notices == [] for x in rec)
            assert all(lv.announce_slot is None and lv.death_min is None for x in rec for lv in x.leases.values())
        seen[mode] = [(x.start_slot, x.end_min, x.end_cause) for x in res.leases]
    assert seen["as_if_H0"] != seen["notice_blind"]


def test_bl8_dispatch():
    """§15.10: bench_for(res, inst, kind) equals the direct call: 'omega' solve_opt on the realized schedule,
    'eager' solve_eager, 'lp' solve_lp (on merged_relaxation with merged=True), 'dp' solve_dp on a single-site
    instance, 'fam' fam.opt_dp on a family instance; for a run under on_unavailable='refuse' 'omega' and
    'eager' use the run's refusal sets (refuse_sched), which change OPT_eager here."""
    from fixtures import fixed_76_case
    from sublet.drivers.bench import bench_for
    from sublet.opt.dp import solve_dp
    from sublet.opt.milp import solve_eager, solve_lp, solve_opt
    from sublet.opt.relax import merged_relaxation
    kw = dict(grid="slow", time_limit_s=60.0, mip_rel_gap=1e-9)
    inst = toy_instance()
    res = _sim(inst, _make("BL1", {}, inst))
    pairs = [("omega", {}, solve_opt(inst, res.schedule, **kw)), ("eager", {}, solve_eager(inst, **kw)),
             ("lp", {}, solve_lp(inst, res.schedule, **kw))]
    im, sm, _ = merged_relaxation(inst, res.schedule)
    pairs.append(("lp", {"merged": True}, solve_lp(im, sm, **kw)))
    for kind, extra, want in pairs:
        got = bench_for(res, inst, kind, mip_rel_gap=1e-9, time_limit_s=60.0, **extra)
        assert got.status == want.status and _close(got.objective, want.objective), (kind, extra, got.objective,
                                                                                      want.objective)
    # refuse run: L0, the cheapest site, refuses every purchase
    instR = toy_instance({"lenders.0.R": list(range(24))})
    resR = simulate(instR, _make("BL1", {}, instR), LenderModel(on_unavailable="refuse"),
                    EngineConfig(auto_drain=False, check_invariants=True), policy_seed=0)
    assert not resR.invariant_failures
    eR = solve_eager(instR, refuse_sched=resR.schedule, **kw)
    assert not _close(eR.objective, solve_eager(instR, **kw).objective)
    for kind, want in (("omega", solve_opt(instR, resR.schedule, refuse_unavailable=True, refuse_sched=resR.schedule,
                                           **kw)), ("eager", eR)):
        got = bench_for(resR, instR, kind, refuse_unavailable=True, mip_rel_gap=1e-9, time_limit_s=60.0)
        assert _close(got.objective, want.objective), (kind, got.objective, want.objective)
    # dp on a single-site instance
    inst1, _ = fixed_76_case()
    res1 = _sim(inst1, _make("BL1", {}, inst1))
    assert _close(bench_for(res1, inst1, "dp").objective, solve_dp(inst1, res1.schedule).objective)
    # fam on a family instance
    F = fam.Fam(3, 4.0, 2, 1, 24)
    om = [np.array([5, 11], dtype=np.int64), np.array([8], dtype=np.int64), np.zeros(0, dtype=np.int64)]
    instF, _ = from_core(F.core_instance(), om)
    resF = _sim(instF, _make("RR_RENEW", {}, instF))
    got = bench_for(resF, instF, "fam")
    want = fam.opt_dp(F, [np.asarray(r, dtype=np.int64) for r in resF.schedule.R])[0]
    assert got.status == 0 and _close(got.objective, want)
