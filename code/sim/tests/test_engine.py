"""Tests of sublet/engine.py, ledger.py and policies/ (design/sim_spec.md §3.6, §5; §9.2)."""
import copy
import json

import numpy as np
import pytest

import pd as ref_pd

from fixtures import (BILLING, CONFIGS, DELETE, _build_single, assert_rel, c3b_case, core_case, explicit_client,
                      explicit_llm, full_variant, random_plan, random_toy_config, recording_policy, repeat_fast,
                      single_site_case, single_site_config, toy_config, toy_instance, trace_schedule,
                      with_capacity, with_stranding)

from sublet import engine as engine_mod
from sublet.engine import ActionError, EngineConfig, simulate
from sublet.instance import build_instance, from_core
from sublet.ledger import COMPONENTS, check_invariants
from sublet.metrics import run_metrics
from sublet.opt.dp import solve_dp
from sublet.opt.milp import solve_lp, solve_opt
from sublet.policies import AlwaysFallback, FixedPlan, RenewReplay
from sublet.types import INF, Buy, Drain, LenderModel, PlannedLease, Release, SetAdmission, Unload

TOY_DEMAND = [0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0]
REC = EngineConfig(record_routing=True)


def _service(c):
    return c["routing"] + c["fallback"]


def _lease_cost(c):
    return c["lease_prepaid"] + c["lease_rent"] + c["loading"]


def _random_variant(seed):
    """A random toy variant of test_invariants_random with a random FixedPlan and mu_fb > 0; the 20 seeds
    cover the three billing modes with both fast slots (5 and 1 min)."""
    rng = np.random.default_rng([seed, 99])
    cfg = random_toy_config(rng, billing=BILLING[seed % 3], fast_min=(5, 1)[(seed // 3) % 2],
                            two_llms=bool(seed % 4 == 3))
    inst = build_instance(cfg)
    with_stranding(inst, mu_fb_usd=float(rng.uniform(0.1, 1.0)),
                   mu_kv_usd=float(rng.uniform(0.05, 0.5)) if seed % 2 else 0.0)
    return inst, random_plan(inst, rng)


def test_always_fallback_cost():
    """AlwaysFallback costs sum_c q_j d_c Delta_f / 60; every other component is 0 (1e-12)."""
    cases = [toy_instance(),
             toy_instance({"time.fast_slot_min": 1, "borrowers.clients.0.demand.values": repeat_fast(TOY_DEMAND, 5)})]
    cfg = toy_config()
    cfg["llms"] = [explicit_llm("M", 1), explicit_llm("M2", 2)]
    cfg["borrowers"]["clients"] = [explicit_client(TOY_DEMAND, "M"),
                                   explicit_client([0.5 * x for x in TOY_DEMAND[::-1]], "M2", borrower="b1")]
    cases.append(build_instance(cfg))
    for inst in cases:
        res = simulate(inst, AlwaysFallback(), cfg=REC)
        q = np.array([inst.llms[j].q_usd_per_h for j in inst.clients.llm])
        want = float((q[:, None] * inst.clients.demand).sum() * inst.grid.fast_min / 60.0)
        c = res.components
        assert abs(c["fallback"] - want) <= 1e-12 * max(1.0, want)
        assert abs(c["total"] - want) <= 1e-12 * max(1.0, want)
        for k in COMPONENTS:
            if k != "fallback":
                assert abs(c[k]) <= 1e-12, (k, c[k])
        assert res.leases == [] and res.replicas == [] and res.invariant_failures == []
    assert abs(simulate(cases[0], AlwaysFallback()).components["total"] - 7.15 * 16 * 5 / 60) <= 1e-12


def test_invariants_random():
    """20 random toy variants under FixedPlan with record_routing: no invariant failures."""
    for seed in range(20):
        inst, plan = _random_variant(seed)
        res = simulate(inst, FixedPlan(plan), cfg=REC)
        assert res.invariant_failures == [], (seed, res.invariant_failures)
        assert check_invariants(res, inst) == [], seed
        assert res.routing is not None and res.routing["b"].dtype == np.float64
        tot = sum(res.components[k] for k in COMPONENTS)
        assert abs(tot - res.components["total"]) <= 1e-9 * max(1.0, abs(tot))


def test_no_lease_dies_before_D():
    """Every reclaimed lease: end - start >= D_k, with end = r Delta_s + H_k and r >= s + tau_k."""
    n = 0
    for seed in range(20):
        inst, plan = _random_variant(seed)
        for schedule in ("trace", "eager", "adaptive"):
            res = simulate(inst, FixedPlan(plan), LenderModel(schedule=schedule))
            assert res.invariant_failures == []
            for L in res.leases:
                c = inst.contracts[L.contract]
                if c.protected:
                    assert L.end_cause != "reclaim" and L.announce_slot is None
                if L.end_cause != "reclaim":
                    continue
                n += 1
                assert L.end_min - L.start_min >= c.D_min(inst.grid.slow_min), L
                assert L.announce_slot >= L.start_slot + c.tau_slots
                assert L.end_min == L.death_min == L.announce_slot * inst.grid.slow_min + c.H_min
    assert n > 20


BILLING_HAND = {   # (prepaid, rent) of the short lease, the long lease and the protected lease
    "prepaid_D": ((0.475, 1.1875), (1.0, 1.0), (0.4975, 0.4975)),
    "per_slot": ((0.0, 1.6625), (0.0, 2.0), (0.4975, 0.4975)),
    "commit_tau": ((0.2375, 1.425), (0.5, 1.5), (0.4975, 0.4975)),
}


@pytest.mark.parametrize("fast", [5, 1])
@pytest.mark.parametrize("billing", list(BILLING_HAND))
def test_billing_modes_hand(billing, fast):
    """L0 (R = {6, 7, 8, 15, 16}): a short lease (2.85 USD/GPU-h, dies at minute 35) and a long lease
    (3.0, dies at minute 40) bought at slot 0, and a protected lease (5.97, prepaid 5 min) held over
    slots 3-4; prepaid and rent by hand for the three billing modes (1e-12)."""
    inst = toy_instance({"billing": billing, "time.fast_slot_min": fast,
                         "borrowers.clients.0.demand.values": repeat_fast(TOY_DEMAND, 5 // fast)},
                        sites=["L0", "P"])
    plan = [PlannedLease(0, 0, 0, 0), PlannedLease(0, 1, 0, 0), PlannedLease(1, 2, 0, 3, release_slot=5)]
    res = simulate(inst, FixedPlan(plan), cfg=REC)
    assert res.invariant_failures == []
    Ls = sorted(res.leases, key=lambda L: L.id)
    assert [(L.contract, L.start_min) for L in Ls] == [(0, 0), (1, 0), (2, 15)]
    P = {"prepaid_D": (10, 20), "per_slot": (0, 0), "commit_tau": (5, 10)}[billing]
    assert [L.prepaid_end_min for L in Ls] == [P[0], P[1], 20]
    assert [(L.announce_slot, L.death_min, L.end_min, L.end_cause) for L in Ls] == \
        [(6, 35, 35, "reclaim"), (6, 40, 40, "reclaim"), (None, None, 25, "release")]
    for L, (pp, rent) in zip(Ls, BILLING_HAND[billing]):
        assert abs(L.prepaid_usd - pp) <= 1e-12 and abs(L.rent_usd - rent) <= 1e-12, (L, pp, rent)
    c = res.components
    assert abs(c["lease_prepaid"] - sum(x[0] for x in BILLING_HAND[billing])) <= 1e-12
    assert abs(c["lease_rent"] - sum(x[1] for x in BILLING_HAND[billing])) <= 1e-12


def test_spot_like_example():
    """§3.1: tau = 1 slot, H = 2 min, prepaid D = 7 min, bought at slot 10, first announcement >= 11
    at slot 13: announced at minute 65, dies at 67, alive in fast slots 50-66, prepaid 50-56."""
    inst = toy_instance({"time.fast_slot_min": 1, "borrowers.clients.0.demand.values": repeat_fast(TOY_DEMAND, 5),
                         "contracts.0.H_min": 2, "lenders.0.R": [3, 13, 20], "lenders.0.lam_s": 0.0},
                        sites=["L0", "P"])
    assert inst.contracts[0].prepaid_min == 7
    res = simulate(inst, FixedPlan([PlannedLease(0, 0, 0, 10)]), cfg=REC)
    assert res.invariant_failures == []
    (L,) = res.leases
    assert (L.start_slot, L.start_min, L.prepaid_end_min) == (10, 50, 57)
    assert (L.announce_slot, L.death_min, L.end_min, L.end_cause) == (13, 67, 67, "reclaim")
    assert abs(L.prepaid_usd - 7 * 2.85 / 60) <= 1e-12 and abs(L.rent_usd - 10 * 2.85 / 60) <= 1e-12
    W = res.routing["W"]
    assert W.shape == (1, 2, 120)
    assert np.array_equal(np.flatnonzero(W[0, 0] > 0), np.arange(50, 67))
    (r,) = res.replicas
    assert (r.load_start_min, r.warm_fast, r.end_fast) == (50, 50, 67)
    assert ("announce" in {e[1] for e in res.events}) and any(e[0] == 65 and e[1] == "announce" for e in res.events)


def test_ended_on_boundary():
    """A short lease (H = 5 min) bought at slot 0 dies at minute 35 = 7 * 5: absent from
    SlowObs.leases at slot 7 and listed in SlowObs.ended there, once."""
    inst = toy_instance()
    pol = recording_policy({0: [Buy(0, 0, 0)]})
    res = simulate(inst, pol)
    (L,) = res.leases
    assert L.end_min == 35 and L.end_cause == "reclaim"
    by_t = {rec["t"]: rec for rec in pol.slow}
    assert L.id in by_t[6]["leases"] and by_t[6]["ended"] == []
    assert L.id not in by_t[7]["leases"]
    assert by_t[7]["ended"] == [(L.id, 35, "reclaim")]
    assert all(rec["ended"] == [] for t, rec in by_t.items() if t != 7)
    assert [n.lease_id for n in by_t[6]["notices"]] == [L.id]


def test_partial_slot_death():
    """Rule T6 with Delta_f = Delta_s = 5 and H = 2 min: a 4-GPU lease at L0 (capacity 4) bought at slot 0
    is announced at slot 6 and dies at minute 32, so it is not alive in fast slot 6 (minutes 30-34): it is
    absent from SlowObs.leases at slot 6, a 4-GPU purchase at slot 6 is accepted, and the old lease serves
    nothing from fast slot 6 (the new one is warm from slot 7, lambda = 300 s)."""
    inst = toy_instance({"contracts.0.H_min": 2, "lenders.0.R": [6]}, sites=["L0", "P"])
    pol = recording_policy({0: [Buy(0, 0, 0, n_replicas=4)], 6: [Buy(0, 0, 0, n_replicas=4)]})
    res = simulate(inst, pol, cfg=REC)
    assert res.invariant_failures == []
    by_t = {r["t"]: r for r in pol.slow}
    assert 0 in by_t[5]["leases"] and 0 not in by_t[6]["leases"]
    assert [(r.ok, r.lease_id) for r in by_t[7]["results"]] == [(True, 1)]
    L0 = next(L for L in res.leases if L.id == 0)
    assert (L0.announce_slot, L0.death_min, L0.end_min, L0.end_cause) == (6, 32, 32, "reclaim")
    W = res.routing["W"][0, 0]
    assert list(W[4:9]) == [4.0, 4.0, 0.0, 4.0, 4.0], W[4:9]
    # rent: prepaid 7 min, rent-bearing fast slots from ceil(7/5) = 2 to the first dead slot 6
    assert abs(L0.rent_usd - 4 * 2.85 * 5 / 60 * 4) <= 1e-12


@pytest.mark.parametrize("fast", [5, 1])
def test_warm_time_hand(fast):
    """Rule T8 with a load time that is not a multiple of the fast slot: lambda = 420 s at L0, a lease
    bought at slot 1 (minute 5) is warm from minute 12, i.e. from the first fast slot starting at or
    after it: fast slot 3 (Delta_f = 5) or 12 (Delta_f = 1)."""
    inst = toy_instance({"time.fast_slot_min": fast, "lenders.0.lam_s": 420.0,
                         "borrowers.clients.0.demand.values": repeat_fast(TOY_DEMAND, 5 // fast)},
                        sites=["L0", "P"])
    res = simulate(inst, FixedPlan([PlannedLease(0, 1, 0, 1)]), cfg=REC)
    assert res.invariant_failures == []
    (r,) = res.replicas
    want = 3 if fast == 5 else 12
    assert r.warm_fast == want
    W = res.routing["W"][0, 0]
    assert W[want - 1] == 0.0 and W[want] == 1.0


def test_ids_and_results():
    inst = toy_instance({"time.fast_slot_min": 1, "borrowers.clients.0.demand.values": repeat_fast(TOY_DEMAND, 5)})
    script = {0: [Buy(0, 0, 0, n_replicas=2), Buy(0, 0, 0, n_replicas=5), Buy(1, 0, 0)],
              2: [Unload(2)],
              3: [Buy(0, 1, 0)]}
    pol = recording_policy(script, wants_fast=True)
    res = simulate(inst, pol)
    assert res.invariant_failures == []
    assert [L.id for L in sorted(res.leases, key=lambda L: L.id)] == [0, 1, 2]
    assert [r.id for r in sorted(res.replicas, key=lambda r: r.id)] == [0, 1, 2, 3]
    assert {r.id: r.lease_id for r in res.replicas} == {0: 0, 1: 0, 2: 1, 3: 2}
    f0 = [x for x in pol.fast if x["f"] == 0]
    assert len(f0) == 1 and [r.ok for r in f0[0]["results"]] == [True, False, True]
    assert [r.lease_id for r in f0[0]["results"]] == [0, None, 1]
    assert tuple(f0[0]["results"][0].replica_ids) == (0, 1) and f0[0]["results"][1].reason == "capacity"
    assert all(x["results"] == [] for x in pol.fast if x["f"] in (1, 2, 3, 4))
    f15 = [x for x in pol.fast if x["f"] == 15]
    assert len(f15) == 1 and [r.lease_id for r in f15[0]["results"]] == [2]
    by_t = {rec["t"]: rec for rec in pol.slow}
    assert [r.index for r in by_t[1]["results"]] == [0, 1, 2]
    assert res.metrics["gpu_only_lease_slots"] >= 1
    res0 = simulate(inst, recording_policy({0: [Buy(0, 0, 0, n_replicas=2), Buy(1, 0, 0)]}))
    assert res0.metrics["gpu_only_lease_slots"] == 0
    for bad in ([Buy(0, 0, 0, n_replicas=0)], [Buy(2, 0, 0)], [Release(99)], [Buy(7, 0, 0)]):
        with pytest.raises(ActionError):
            simulate(inst, recording_policy({1: bad}))


def test_admission_view_in_force():
    """§10 S33: SlowObs.replicas[r].admission at slot t is the admission in force from fast slot t*phi,
    so pending changes effective at or before t*phi are reflected. Toy L0 + P (phi = 1): Buy at slot 0,
    Drain(0, at_min=10) at slot 1 -> the view shows 1.0 at slot 1 and 0.0 at slot 2 (minute 10), when the
    routing capacity is already 0 (the case of the MS1 review, issue E2). A SetAdmission(1, 0.5) from on_fast
    in fast slot 3 (effective from 4) shows at slot 4; a drain issued at slot 1 for minute 15 shows only
    from slot 3. With phi = 5, a drain for minute 12 issued at slot 1 is not in force at slot 2 (fast
    slot 10) and is at slot 3."""
    inst = toy_instance(sites=["L0", "P"])
    pol = recording_policy({0: [Buy(0, 0, 0, n_replicas=2)], 1: [Drain(0, 10), Drain(1, 15)]},
                           fast_script={3: [SetAdmission(1, 0.5)]})
    res = simulate(inst, pol, cfg=REC)
    assert res.invariant_failures == []
    by_t = {rec["t"]: rec for rec in pol.slow}
    adm = {t: (by_t[t]["replicas"][0].admission, by_t[t]["replicas"][1].admission) for t in (1, 2, 3, 4)}
    assert adm == {1: (1.0, 1.0), 2: (0.0, 1.0), 3: (0.0, 0.0), 4: (0.0, 0.5)}, adm
    assert by_t[2]["replicas"][0].drain_min == 10 and by_t[2]["replicas"][1].drain_min == 15
    W = res.routing["W"][0, 0]
    assert W[2] == 1.0 and W[3] == 0.0 and W[4] == 0.5          # replica 0 drained from fast slot 2
    inst5 = toy_instance({"time.fast_slot_min": 1, "borrowers.clients.0.demand.values": repeat_fast(TOY_DEMAND, 5)},
                         sites=["L0", "P"])
    pol = recording_policy({0: [Buy(0, 0, 0)], 1: [Drain(0, 12)]})
    res = simulate(inst5, pol, cfg=REC)
    assert res.invariant_failures == []
    by_t = {rec["t"]: rec for rec in pol.slow}
    assert [by_t[t]["replicas"][0].admission for t in (1, 2, 3)] == [1.0, 1.0, 0.0]
    W = res.routing["W"][0, 0]
    assert W[11] == 1.0 and W[12] == 0.0


def _stranding_instance(lam_P, mu_fb, mu_kv):
    demand = [0.8] * 7 + [0.5] * 17
    inst = toy_instance({"borrowers.clients.0.demand.values": demand, "lenders.0.R": [6],
                         "lenders.0.lam_s": 0.0, "lenders.2.lam_s": float(lam_P)}, sites=["L0", "P"])
    return with_stranding(inst, mu_fb_usd=mu_fb, mu_kv_usd=mu_kv, mu_fl_usd=0.0, pi_usd_per_min=0.0)


def test_stranding_hand():
    """(a) the L0 lease dies at fast slot 7 with live demand: w = d_hat = min(0.8, 0.5), charge mu_fb * 0.5;
    (b) a protected replica pre-warmed from slot 6 takes over: no stranding_fb; (c) the protected replica
    turns warm exactly at slot 7: the load moves L0 -> P, m = 0.5, charge mu_kv * 0.5, no stranding_fb."""
    inst = _stranding_instance(600.0, 0.4, 0.0)
    res = simulate(inst, FixedPlan([PlannedLease(0, 0, 0, 0)]), cfg=REC)
    assert res.invariant_failures == []
    c = res.components
    assert abs(c["stranding_fb"] - 0.4 * 0.5) <= 1e-12 and abs(res.per_slot["stranding_fb"][7] - 0.2) <= 1e-12
    assert abs(c["stranding_kv"]) <= 1e-12
    m = run_metrics(res, inst)
    assert abs(m["stranded_load_fb"] - 0.5) <= 1e-12 and abs(m["stranded_load_any"] - 0.5) <= 1e-12
    # (b) pre-warmed replacement (lambda_P = 300 s: bought at slot 5, warm from fast slot 6)
    inst = _stranding_instance(300.0, 0.4, 0.0)
    res = simulate(inst, FixedPlan([PlannedLease(0, 0, 0, 0), PlannedLease(1, 2, 0, 5)]), cfg=REC)
    assert res.invariant_failures == []
    assert abs(res.components["stranding_fb"]) <= 1e-12
    (rp,) = [r for r in res.replicas if r.lease_id == 1]
    assert rp.warm_fast == 6
    # (c) re-routing between sites (lambda_P = 600 s: warm from fast slot 7)
    inst = _stranding_instance(600.0, 0.4, 0.3)
    res = simulate(inst, FixedPlan([PlannedLease(0, 0, 0, 0), PlannedLease(1, 2, 0, 5)]), cfg=REC)
    assert res.invariant_failures == []
    c = res.components
    assert abs(c["stranding_kv"] - 0.3 * 0.5) <= 1e-12 and abs(c["stranding_fb"]) <= 1e-12
    assert abs(res.per_slot["stranding_kv"][7] - 0.15) <= 1e-12
    m = run_metrics(res, inst)
    assert abs(m["stranded_load_any"] - 0.5) <= 1e-12 and abs(m["stranded_load_fb"]) <= 1e-12


def _lead_instance():
    inst = toy_instance({"borrowers.clients.0.demand.values": [0.8] * 7 + [0.5] * 17, "lenders.0.R": [6],
                         "lenders.0.lam_s": 0.0, "lenders.2.lam_s": 600.0}, sites=["L0", "P"])
    return with_stranding(inst, mu_fl_usd=0.3, pi_usd_per_min=0.01, W_f_min=10.0, mu_fb_usd=0.0, mu_kv_usd=0.0)


@pytest.mark.parametrize("case", ["reclaim", "release", "drain_announced"])
def test_lead_time_hand(case):
    """Lead time h (§5.6, S22) in stranding_fl = mu_fl (1 - 60 h / T_dr)^+ m and stranding_pi =
    pi (W_f - h)^+ w, by hand: toy L0 and P, Delta_s = Delta_f = 5, demand 0.8 in slots 0-6 and 0.5 after,
    lambda_L0 = 0, T_dr = 28.49 s, mu_fl = 0.3, pi = 0.01 USD per load-minute, W_f = 10 min (1e-12).
    A short lease (tau 1 slot, H 5 min) bought at slot 0 is announced at slot 6 and dies at minute 35.
    (reclaim) the drop at fast slot 7 has lead H = 5, m = w = min(0.8, 0.5): fl = 0, pi = 0.01 * 5 * 0.5;
    (release) a release at slot 3 (unannounced) has lead 15 - 15 = 0, m = w = 0.8: fl = 0.3 * 0.8,
              pi = 0.01 * 10 * 0.8;
    (drain_announced) a drain from minute 30 issued at the announcement slot 6 is a drop of a replica on
              an announced lease, lead H = 5 (not 30 - 30), m = w = 0.8: fl = 0, pi = 0.01 * 5 * 0.8."""
    script = {0: [Buy(0, 0, 0)]}
    if case == "release":
        script[3] = [Release(0)]
    elif case == "drain_announced":
        script[6] = [Drain(0, 30)]
    want = {"reclaim": (0.0, 0.025), "release": (0.24, 0.08), "drain_announced": (0.0, 0.04)}[case]
    res = simulate(_lead_instance(), recording_policy(script), cfg=REC)
    assert res.invariant_failures == []
    c = res.components
    assert abs(c["stranding_fl"] - want[0]) <= 1e-12 and abs(c["stranding_pi"] - want[1]) <= 1e-12, c


def test_fixedplan_replays_milp_core():
    """from_core(core_case(seed 0-9)): FixedPlan of the MILP plan costs the MILP objective (1e-6)."""
    for seed in range(10):
        for rate in (0.0, 0.2):
            I, om = core_case(seed, rate)
            inst, sched = from_core(I, om)
            sol = solve_opt(inst, sched, mip_rel_gap=1e-9)
            assert sol.status == 0 and sol.plan is not None
            res = simulate(inst, FixedPlan(sol.plan))
            assert res.invariant_failures == []
            assert_rel(res.components["total"], sol.objective, 1e-6, f"seed {seed} rate {rate}")


def test_fixedplan_replays_milp_full():
    """10 toy variants (lambda = 300 s, two clients with demand in [0, 1], finite capacity, mu = 0,
    Delta_f = Delta_s): FixedPlan of the MILP plan costs the objective (1e-6)."""
    for i in range(10):
        inst, sched = full_variant(i)
        sol = solve_opt(inst, sched, mip_rel_gap=1e-9)
        assert sol.status == 0
        res = simulate(inst, FixedPlan(sol.plan))
        assert res.invariant_failures == []
        assert not any(e[1] == "refuse" for e in res.events)
        assert_rel(res.components["total"], sol.objective, 1e-6, f"variant {i}")


def _offgrid_variant(i):
    """Toy variant whose contracts have H in {2, 7, 12} min and whose load times (120 or 420 s) are not
    multiples of the fast slot (5 min for even i, solved on grid 'slow'; 1 min for odd i, grid 'fast');
    two clients with demand in [0, 1], the toy's finite capacities, mu = 0."""
    rng = np.random.default_rng([i, 71])
    fast = (5, 1)[i % 2]
    cfg = random_toy_config(rng, fast_min=fast, lam=float(rng.choice([120.0, 420.0])), n_clients=2,
                            two_llms=bool((i // 2) % 2), demand_hi=1.0, p_on=0.75)
    cfg["contracts"][0]["H_min"] = int(rng.choice([2, 7]))
    cfg["contracts"][1]["H_min"] = int(rng.choice([2, 7, 12]))
    cfg["stranding"]["mu_over_beta_tilde"] = 0.0
    inst = build_instance(cfg)
    return inst, trace_schedule(inst), ("slow" if fast == 5 else "fast")


def test_fixedplan_replays_milp_offgrid():
    """8 toy variants with deaths and warm times inside fast slots (rules T6, T8): FixedPlan of the MILP
    plan on the engine's grid costs the objective (1e-6, §8.10 with mu = 0)."""
    for i in range(8):
        inst, sched, grid = _offgrid_variant(i)
        sol = solve_opt(inst, sched, grid=grid, mip_rel_gap=1e-9)
        assert sol.status == 0
        res = simulate(inst, FixedPlan(sol.plan), cfg=REC)
        assert res.invariant_failures == []
        assert not any(e[1] == "refuse" for e in res.events)
        assert_rel(res.components["total"], sol.objective, 1e-6, f"variant {i} ({grid})")


def _routing_variant(i, single):
    """Toy variants with routing costs 0 at L0 and 0.6 USD per load-hour at L1 and P, demand up to two
    replica loads, Delta_f = Delta_s, mu = 0; with `single` one client and L0 of 1 GPU (the overflow
    of the cheapest site goes to the next one), else one or two clients and the toy's capacities."""
    rng = np.random.default_rng([i, 62 if single else 61])
    cfg = random_toy_config(rng, fast_min=5, lam=300.0, n_clients=1 if single else int(rng.integers(1, 3)),
                            demand_hi=2.0, p_on=0.9 if single else 0.7)
    if single:
        cfg["lenders"][0]["capacity_gpus"] = 1
    cfg["stranding"]["mu_over_beta_tilde"] = 0.0
    inst = build_instance(cfg)
    inst.clients.delta_usd_per_h[:, 1:] = 0.6
    return inst, trace_schedule(inst)


def test_fixedplan_replays_milp_unequal_delta():
    """Routing between sites of unequal cost (§5.5): with mu = 0 per-slot routing is optimal, so FixedPlan
    of the MILP plan costs the objective (1e-6), on 10 multi-client variants (greedy and LP paths) and
    12 single-client variants whose demand overflows the cheapest site."""
    overflow = 0
    for single, n in ((False, 10), (True, 12)):
        for i in range(n):
            inst, sched = _routing_variant(i, single)
            sol = solve_opt(inst, sched, mip_rel_gap=1e-9)
            assert sol.status == 0
            res = simulate(inst, FixedPlan(sol.plan), cfg=REC)
            assert res.invariant_failures == []
            assert_rel(res.components["total"], sol.objective, 1e-6, f"variant {i} single={single}")
            if single:
                W, d = res.routing["W"][0], inst.clients.demand[0]
                overflow += int(np.sum((W[0] > 0) & (d > W[0]) & (W[1:].sum(axis=0) > 0)))
    assert overflow > 0


def test_infeasible_arc_unused():
    """A client whose arc to L0 is SLO-infeasible (delta = INF, not kappa_infinite) gets nothing from a
    lease at L0: with that lease and a protected lease held over slots 10-15 (warm from 12), the
    fallback is 12 of the toy's 16 demand slot-loads, 7.15 * 12 * 5 / 60 = 7.15 USD (1e-12), and the
    routing record has no load at L0."""
    inst = toy_instance(sites=["L0", "P"])
    inst.clients.delta_usd_per_h[0, 0] = INF
    plan = [PlannedLease(0, 0, 0, 0), PlannedLease(1, 2, 0, 10, release_slot=16)]
    res = simulate(inst, FixedPlan(plan), cfg=REC)
    assert res.invariant_failures == []
    assert abs(res.components["fallback"] - 7.15) <= 1e-12 and abs(res.components["routing"]) <= 1e-12
    assert not any(arr.any() for (c, l), arr in res.routing["x"].items() if l == 0)
    assert res.routing["W"][0, 0].max() == 1.0
    # a router that serves the client on the infeasible arc is reported by the online INV3
    orig = engine_mod.Engine._route

    def route_to_L0(self, f, W):
        x = orig(self, f, W)
        if W[0, 0] > 0 and self.demand[0, f] > 0 and x[0].sum() == 0:
            x[0, 0] = min(self.demand[0, f], W[0, 0])
        return x

    engine_mod.Engine._route = route_to_L0
    try:
        r2 = simulate(inst, FixedPlan(plan))
    finally:
        engine_mod.Engine._route = orig
    assert any(f.startswith("INV3 fast slot") and "forbidden arc" in f for f in r2.invariant_failures)


def test_invariant_checker_detects():
    """The invariant checks fire (§5.7): a correct toy run, tampered in one field at a time, is reported
    by the named invariant of check_invariants; a router that over-serves by 1.5x is reported online."""
    inst = toy_instance()
    plan = [PlannedLease(0, 0, 0, 0), PlannedLease(1, 1, 0, 4, release_slot=12), PlannedLease(2, 2, 0, 10)]
    res = simulate(inst, FixedPlan(plan), cfg=REC)
    assert res.invariant_failures == [] and check_invariants(res, inst) == []
    rec = next(L for L in res.leases if L.end_cause == "reclaim")

    def fires(r, name):
        return any(f.startswith(name) for f in check_invariants(r, inst))

    r = copy.deepcopy(res)
    L = next(x for x in r.leases if x.id == rec.id)
    L.end_min += 1
    L.death_min += 1
    assert fires(r, "INV1")
    r = copy.deepcopy(res)
    r.per_slot["fallback"][3] += 0.1
    assert fires(r, "INV4")
    r = copy.deepcopy(res)
    next(x for x in r.leases if x.id == rec.id).rent_usd += 0.01
    assert fires(r, "INV5")
    r = copy.deepcopy(res)
    r.leases[0].gpus += 4
    assert fires(r, "INV6")
    r = copy.deepcopy(res)
    r.routing["b"][0, 3] += 0.25
    assert fires(r, "INV2 (post hoc)")
    r = copy.deepcopy(res)
    k = next(iter(r.routing["x"]))
    r.routing["x"][k] = r.routing["x"][k] * 1.5
    assert fires(r, "INV2 (post hoc)") or fires(r, "INV3 (post hoc)")
    # stranding_fb moved between two slots, per-slot totals adjusted: only INV8 can see it
    r = copy.deepcopy(res)
    for key in ("stranding_fb", "total") + (("stranding",) if "stranding" in r.per_slot else ()):
        r.per_slot[key][7] += 0.05
        r.per_slot[key][8] -= 0.05
    fails = check_invariants(r, inst)
    assert any(f.startswith("INV8 (post hoc)") for f in fails) and not any(f.startswith("INV4") for f in fails)

    orig = engine_mod.Engine._route

    def over_route(self, f, W):
        x = orig(self, f, W)
        return x * 1.5

    engine_mod.Engine._route = over_route
    try:
        r2 = simulate(inst, FixedPlan(plan))
    finally:
        engine_mod.Engine._route = orig
    assert any(f.startswith("INV2 fast slot") or f.startswith("INV3 fast slot") for f in r2.invariant_failures)
    assert r2.routing is None


def _adm_case():
    """A DP plan with an admission_off interval (§7.5), by hand: T_s = 6, Delta = 5, revocable site with
    R = {2, ..., 5} and refuse_unavailable, contract tau 3 slots, H 0, P 15 min at 1 USD/GPU-h (0.25 per
    lease), protected site at 50 USD/GPU-h, lambda 0, q = 7.15, mu_fb = 3, demand (1, 0, 1, 1, 1, 1).
    The lease from slot 0 dies at minute 15 (slot 3); serving it in slot 2 would strand load 1 at slot 3
    (3 USD), so it serves slot 0 only and is admission-off in slot 2: 0.25 + 4 x 7.15 / 12 = 2.63333."""
    cfg = single_site_config(6, 5, [("r1", 15, 0)], {"r1": 1.0}, 50.0, [2, 3, 4, 5], 0.0, 0.0,
                             [1, 0, 1, 1, 1, 1], "prepaid_D")
    inst, sched = _build_single(cfg, unlimited=True, mu_fb=3.0)
    return inst, sched, 0.25 + 4 * 7.15 / 12


def test_fixedplan_replays_dp():
    """10 single_site_case instances with mu_fb > 0 and mu_fl = pi = 0 on each grid, and the hand case
    with an admission_off interval: FixedPlan of the DP plan costs the DP objective (1e-9)."""
    for grid in ("slow", "fast"):
        for seed in range(10):
            inst, sched = single_site_case(seed, grid)
            if not inst.stranding.mu_fb_usd.any():
                with_stranding(inst, mu_fb_usd=0.6)
            assert inst.stranding.mu_fb_usd[0] > 0 and not inst.stranding.mu_fl_usd.any()
            sol = solve_dp(inst, sched, grid=grid)
            assert sol.status == 0 and sol.plan is not None
            res = simulate(inst, FixedPlan(sol.plan), cfg=REC)
            assert res.invariant_failures == []
            assert_rel(res.components["total"], sol.objective, 1e-9, f"seed {seed} grid {grid}")
    inst, sched, want = _adm_case()
    sol = solve_dp(inst, sched, refuse_unavailable=True)
    assert sol.status == 0 and abs(sol.objective - want) <= 1e-9
    assert any(pl.admission_off for pl in sol.plan), sol.plan
    res = simulate(inst, FixedPlan(sol.plan), LenderModel(on_unavailable="refuse"), cfg=REC)
    assert res.invariant_failures == [] and not any(e[1] == "refuse" for e in res.events)
    assert abs(res.components["total"] - want) <= 1e-9 and abs(res.components["stranding_fb"]) <= 1e-12


def test_auto_drain_hand():
    """auto_drain (§5.1 step 1, §5.4) at Delta_f = 1: a short lease (H = 5) at L0 announced at slot 6 dies
    at minute 35; T_dr = 28.49 s, so its replica drains from minute max(30, 35 - ceil(28.49 / 60)) = 34:
    admitting capacity 1 in fast slots 32-33 and 0 from 34."""
    inst = toy_instance({"time.fast_slot_min": 1, "borrowers.clients.0.demand.values": [1.0] * 120,
                         "lenders.0.R": [6], "lenders.0.lam_s": 0.0}, sites=["L0", "P"])
    res = simulate(inst, recording_policy({0: [Buy(0, 0, 0)]}), cfg=EngineConfig(auto_drain=True,
                                                                                  record_routing=True))
    assert res.invariant_failures == []
    assert list(res.routing["W"][0, 0, 32:36]) == [1.0, 1.0, 0.0, 0.0]
    assert any(e[1] == "drain" and e[2]["at_min"] == 34 for e in res.events)


def test_fixedplan_admission_at_purchase():
    """FixedPlan (§5.8): an admission_off interval [2, 4) that starts at the purchase slot 2 (L0, lambda 0)
    is applied through Buy.admission: admitting capacity 0 in fast slots 2-3 and 1 from slot 4."""
    inst = toy_instance({"lenders.0.lam_s": 0.0}, sites=["L0", "P"])
    res = simulate(inst, FixedPlan([PlannedLease(0, 0, 0, 2, admission_off=((2, 4),))]), cfg=REC)
    assert res.invariant_failures == []
    assert list(res.routing["W"][0, 0, 1:6]) == [0.0, 0.0, 0.0, 1.0, 1.0]


def test_renew_replay_vs_reference():
    """check_c3_benchmark part (b)/(c) instances: RenewReplay of the rounded PD plans (10 seeds x
    {theory r, r = 1}) under omega: lease cost = real_cost_renew (1e-9); service <= service_cost_given_open
    (+1e-9); total <= 2 cost_pr (+1e-6; design check 4, VERIFIED NUMERICALLY on these instances only)."""
    for seed in range(10):
        I, _ = c3b_case(seed, 0.0)
        pdr = ref_pd.FracPD(I).run()
        rnd = [ref_pd.round_pd(pdr, np.random.default_rng(s)) for s in range(10)] + \
              [ref_pd.round_pd(pdr, np.random.default_rng(s), r=1) for s in range(10)]
        for rate in (0.0, 0.02, 0.1, 0.3, 1.0):
            I2, om = c3b_case(seed, rate)
            inst, sched = from_core(I2, om)
            for i, x in enumerate(rnd):
                cost, _ = ref_pd.real_cost_renew(I2, x["opened"], om)
                serv = float(ref_pd.service_cost_given_open(I2, x["opened"]).sum())
                res = simulate(inst, RenewReplay(x["opened"]))
                assert res.invariant_failures == []
                c = res.components
                tag = f"seed {seed} rate {rate} rounding {i}"
                assert_rel(_lease_cost(c), cost, 1e-9, tag)
                assert _service(c) <= serv + 1e-9, tag
                assert c["total"] <= 2 * x["cost_pr"] + 1e-6, tag


def _hand_lp_instance(case):
    """The two plans of test_lp_bound_below_engine that release inside the billed term (§9.2)."""
    cfg = toy_config(sites=["L0"])
    cfg["prices"]["q_gpu_usd_per_gpu_h"] = 60.0
    cfg["contracts"] = [{"id": "c", "tau_min": 5, "H_min": 2}]
    cfg["lenders"][0].update({"menu": ["c"], "prices": {"c": 6.0}, "R": [], "lam_s": 0.0, "capacity_gpus": 1})
    cfg["stranding"]["mu_over_beta_tilde"] = 0.0
    if case == "i":
        cfg["time"] = {"slow_slot_min": 5, "fast_slot_min": 5, "horizon_min": 20, "start_minute_of_week": 0}
        cfg["llms"] = [explicit_llm("j1", 1), explicit_llm("j2", 1)]
        cfg["borrowers"]["clients"] = [explicit_client([1, 0, 0, 0], "j1"),
                                       explicit_client([0, 1, 1, 1], "j2", borrower="b1")]
        plan = [PlannedLease(0, 0, 0, 0, release_slot=1), PlannedLease(0, 0, 1, 1)]
        return build_instance(cfg), plan, 1.9
    cfg["time"] = {"slow_slot_min": 5, "fast_slot_min": 1, "horizon_min": 10, "start_minute_of_week": 0}
    cfg["borrowers"]["clients"] = [explicit_client([1] * 5 + [0] * 5)]
    inst = with_capacity(build_instance(cfg), {0: INF})
    return inst, [PlannedLease(0, 0, 0, 0, release_slot=1)], 0.7


def test_lp_bound_below_engine():
    """Proposition M4 (b): solve_lp on the engine's grid is at most the engine cost of AlwaysFallback
    and of random FixedPlans (+1e-9); and the two hand plans that release inside the billed term."""
    rng = np.random.default_rng(4)
    insts = [toy_instance(), build_instance(random_toy_config(np.random.default_rng(5), fast_min=1))]
    for seed in range(4):
        insts.append(from_core(*core_case(seed, 0.2))[0])
    for inst in insts:
        pols = [AlwaysFallback()] + [FixedPlan(random_plan(inst, rng, admission=bool(i % 2))) for i in range(4)]
        for pol in pols:
            res = simulate(inst, pol)
            assert res.invariant_failures == []
            lp = solve_lp(inst, res.schedule, grid="fast", mip_rel_gap=1e-9)
            assert lp.status == 0
            tot = res.components["total"]
            assert lp.objective <= tot + 1e-9 * max(1.0, abs(tot)), (inst.name, lp.objective, res.components)
    for case in ("i", "ii"):
        inst, plan, hand = _hand_lp_instance(case)
        res = simulate(inst, FixedPlan(plan), cfg=REC)
        assert res.invariant_failures == []
        assert abs(res.components["total"] - hand) <= 1e-9, (case, res.components)
        sched = res.schedule
        opt = solve_opt(inst, sched, grid="fast", mip_rel_gap=1e-9)
        assert opt.status == 0 and abs(opt.objective - hand) <= 1e-9, (case, opt.objective)
        lp = solve_lp(inst, sched, grid="fast")
        assert lp.status == 0 and lp.objective <= hand + 1e-9


@pytest.mark.needs_a12
def test_always_fallback_no_attributable_violations():
    """§6.5, S10: AlwaysFallback holds no lease, so no buffer violation is attributable to it. On a one-week
    instance with lenders a2:c15 and a2:c01 (example_1day's menu), the old requirement v0*g (the v0 layers
    committed at every slot) exceeds the physical slack S in 149 lender-slots (143 at c15, 6 at c01),
    counted here from the series directly; under the owed rule those v0 layers had been unavailable for
    longer than D^max and are no longer owed, so the run logs no violation at all."""
    with open(CONFIGS / "example_1day.json") as f:
        base = json.load(f)
    cfg = dict(base, time=dict(base["time"], horizon_min=7 * 1440),
               lenders=[{"id": "a2:c15"}, {"id": "a2:c01"}])
    inst = build_instance(cfg)
    res = simulate(inst, AlwaysFallback(), LenderModel())
    assert res.invariant_failures == [] and res.leases == []
    old = {lt.lender: int(np.sum(lt.v0 * lt.layer_gpus > lt.S)) for lt in inst.lenders if lt.S is not None}
    assert old == {"a2:c15": 143, "a2:c01": 6}
    bv = run_metrics(res, inst)
    assert bv["buffer_violations_attributable"]["count"] == 0
    assert bv["buffer_violations_attributable"]["deficit_gpu_slots"] == 0.0
    assert all(v["deficit_attributable"] == 0.0 for v in res.violations)
    assert bv["buffer_violations"]["count"] == len({(v["lender"], v["t"]) for v in res.violations}) == 0


def test_determinism():
    """Same config and seed: identical instances and identical components."""
    cfg = toy_config({"lenders.0.R": DELETE, "lenders.0.R_rate": 0.3})
    a, b = build_instance(cfg), build_instance(cfg)
    assert np.array_equal(a.sites[0].R_explicit, b.sites[0].R_explicit)
    plan = random_plan(a, np.random.default_rng(8))
    for model in (LenderModel(), LenderModel(schedule="adaptive")):
        r1 = simulate(a, FixedPlan(plan), model)
        r2 = simulate(b, FixedPlan(plan), model)
        assert r1.components == r2.components
        assert all(np.array_equal(x, y) for x, y in zip(r1.schedule.R, r2.schedule.R))
        for k in r1.per_slot:
            assert np.array_equal(r1.per_slot[k], r2.per_slot[k])
    r3 = simulate(a, AlwaysFallback(), seed=3)
    r4 = simulate(a, AlwaysFallback(), seed=3)
    assert r3.components == r4.components
