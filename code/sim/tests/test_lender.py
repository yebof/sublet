"""Tests of sublet/lender.py (design/sim_spec.md §3.5, §6; §9.2)."""
import numpy as np
import pytest

import check_c4_lower
import fam
import pd as ref_pd

from fixtures import (assert_rel, core_case, inline_trace_lender, recording_policy, site_index,
                      toy_config, toy_instance, trace_schedule)

from sublet import reclaim
from sublet.config import ConfigError
from sublet.engine import simulate
from sublet.instance import build_instance, from_core
from sublet.lender import Lender, build_R
from sublet.paths import import_a9
from sublet.policies import FixedPlan, RenewReplay
from sublet.types import Buy, LenderModel, PlannedLease, Release, Schedule

SAFE_NULL = {"D_slots": None, "k": None, "Phi": None}
IID_NULL = {"D_slots": None, "p": 0.5, "U": None}


def _R(sched_or_list):
    R = sched_or_list.R if isinstance(sched_or_list, Schedule) else sched_or_list
    return [np.asarray(r, dtype=np.int64) for r in R]


def _same_R(a, b):
    return len(a) == len(b) and all(np.array_equal(x, y) for x, y in zip(a, b))


def _sites_of(inst, lender):
    """Site indices of a lender, in increasing local_layer_lo."""
    idx = [i for i, s in enumerate(inst.sites) if s.lender == lender]
    return sorted(idx, key=lambda i: inst.sites[i].local_layer_lo)


def test_trace_R_nested():
    """R_{l,v} is a subset of R_{l,v+1}, and each layer site's set is reclaim.layer_R at its threshold."""
    rng = np.random.default_rng(11)
    t = np.arange(300)
    series = np.round(200 + 30 * np.sin(2 * np.pi * t / 12) + rng.integers(-4, 5, size=300)).clip(0)
    cfg = toy_config({"lender_model.merge_identical_layers": False}, sites=["P"])
    cfg["lenders"] = [inline_trace_lender(series, "X", n_layers=4)] + cfg["lenders"]
    insts = [build_instance(cfg)]
    cfg2 = toy_config({"lender_model.merge_identical_layers": False}, sites=["P"])
    cfg2["lenders"] = [{"id": "a1:A100-SXM4-80GB", "kind": "trace", "region": "r0", "group": "gA",
                        "menu": ["short"], "prices": {"short": 2.85}, "n_layers": 8, "layer_gpus": 8,
                        "lease_size_quantile": 25, "offset": 1000, "load_scenario": "explicit",
                        "lam_s": 300.0}] + cfg2["lenders"]
    insts.append(build_instance(cfg2))
    for inst in insts:
        lend = inst.lenders[0]
        sites = _sites_of(inst, lend.lender)
        assert len(sites) >= 2, [s.id for s in inst.sites]
        R = _R(build_R(inst, LenderModel(), np.random.default_rng(0)))
        R2 = _R(Lender(inst, LenderModel(), np.random.default_rng(0)).static_schedule())
        assert _same_R(R, R2)
        for a, b in zip(sites, sites[1:]):
            assert set(R[a]) <= set(R[b]), (inst.sites[a].id, inst.sites[b].id)
        for i in sites:
            s = inst.sites[i]
            assert np.array_equal(R[i], reclaim.layer_R(lend.S_lend, s.layer_lo * lend.layer_gpus))
            assert np.array_equal(R[i], reclaim.layer_R(lend.S_lend, s.layer_hi * lend.layer_gpus))
        prot = [i for i, s in enumerate(inst.sites) if s.kind == "protected"]
        assert all(len(R[i]) == 0 for i in prot)
    for inst in insts:                                                  # no merging
        assert len(_sites_of(inst, inst.lenders[0].lender)) == inst.lenders[0].n_layers


def test_buffer_matches_buffer_curve():
    """B_l = env x mean of a9_notice_buffer.buffer_curve at D_max over the offered contracts
    (a contract with b >= 1 is not offered and does not raise the buffer)."""
    a9 = import_a9()
    from sublet.traces import lenders as tl
    cfg = toy_config({"prices.revocable_price": "ir"}, sites=["P"])
    cfg["contracts"] = [{"id": "s5_tau5_H2", "tau_min": 5, "H_min": 2},
                        {"id": "s5_tau5_H60", "tau_min": 5, "H_min": 60},
                        {"id": "s5_tau60_H0", "tau_min": 60, "H_min": 0},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": 5}]
    menu = ["s5_tau5_H2", "s5_tau5_H60", "s5_tau60_H0"]
    for name, group in (("a1:H800", "gH"), ("a2:c05", "gC")):
        cfg["lenders"].insert(0, {"id": name, "kind": "trace", "region": "r0", "group": group, "menu": menu,
                                  "n_layers": 2, "layer_gpus": 8, "lease_size_quantile": 25, "offset": 0,
                                  "load_scenario": "explicit", "lam_s": 300.0})
    inst = build_instance(cfg)
    want_D = {"a1:H800": 5, "a2:c05": 65}       # H800 offers only s5_tau5_H2 at P99 (a11 ir_multiplier None)
    k_of = {c.id: i for i, c in enumerate(inst.contracts)}
    for L in inst.lenders:
        if L.lender not in want_D:
            continue
        S = tl.slack(L.lender)
        assert np.array_equal(L.S_full, S)
        D = want_D[L.lender]
        assert L.D_max_lender_min == D
        env = a9.buffer_curve(S, D)["env"][D]["p99"]
        assert L.B_gpus == env * S.mean(), (L.lender, L.B_gpus, env * S.mean())
        assert np.array_equal(L.S_lend, np.maximum(L.S - L.B_gpus, 0.0))
        offered = {inst.contracts[k].id for i in L.site_index for k in inst.sites[i].menu}
        assert offered == ({"s5_tau5_H2"} if L.lender == "a1:H800" else set(menu))
        for i in L.site_index:
            assert np.isfinite(inst.price[i, k_of["s5_tau5_H2"]])
            if L.lender == "a1:H800":
                assert np.isinf(inst.price[i, k_of["s5_tau5_H60"]]) and np.isinf(inst.price[i, k_of["s5_tau60_H0"]])


def _lendable_instance():
    cfg = toy_config({"time.horizon_min": 40, "borrowers.clients.0.demand.values": [1.0] * 8}, sites=["P"])
    cfg["lenders"] = [inline_trace_lender([45, 45, 35, 45, 45, 45, 45, 45], "X", n_layers=2, layer_gpus=8,
                                          lease_size_quantile=25)] + cfg["lenders"]
    return build_instance(cfg)


def test_lendable_vs_physical():
    """B ~ 10 GPUs, S_lend = (35, 35, 25, 35, ...), v0 = 2: layer 4 (threshold 32) is unavailable at
    slot 2 although S_h(2) = 35 is not below 32; the violation check at slot 2 uses S_h = 35."""
    inst = _lendable_instance()
    L = inst.lenders[0]
    assert L.lender == "X" and abs(L.B_gpus - 10.0) <= 1e-9 and L.v0 == 2
    ids = [s.id for s in inst.sites]
    assert ids[:2] == ["X/L3-3", "X/L4-4"], ids
    t = 2
    assert L.S[t] == 35.0 and L.S_lend[t] < 32 <= L.S[t]
    R = _R(build_R(inst, LenderModel(), np.random.default_rng(0)))
    assert np.array_equal(R[0], []) and np.array_equal(R[1], [2])
    lender = Lender(inst, LenderModel(), np.random.default_rng(0))
    # required = v0 * g_lay + leased = 16 + 12 = 28 <= S_h = 35 (it would exceed S_lend = 25)
    assert lender.violations(t, {"X": 12}) == []
    v = lender.violations(t, {"X": 20})
    assert len(v) == 1
    assert (v[0]["lender"], v[0]["t"], v[0]["required"], v[0]["slack"], v[0]["deficit"]) == ("X", 2, 36, 35.0, 1.0)
    assert lender.violations(0, {"X": 20}) == []


def test_eager_lifetimes():
    """Under 'eager' every reclaimed lease lives exactly D_k (FixedPlan on the toy)."""
    inst = toy_instance()
    plan = [PlannedLease(0, 0, 0, 0), PlannedLease(0, 1, 0, 3), PlannedLease(1, 0, 0, 5),
            PlannedLease(1, 1, 0, 9), PlannedLease(0, 0, 0, 20), PlannedLease(2, 2, 0, 2),
            PlannedLease(1, 1, 0, 21)]
    res = simulate(inst, FixedPlan(plan), LenderModel(schedule="eager"))
    assert res.invariant_failures == []
    assert len(res.leases) == len(plan)
    n_rec = 0
    for L in res.leases:
        c = inst.contracts[L.contract]
        if c.protected:
            assert L.end_cause == "horizon" and L.announce_slot is None
            continue
        if L.end_cause == "reclaim":
            n_rec += 1
            assert L.announce_slot == L.start_slot + c.tau_slots
            assert L.end_min - L.start_min == c.D_min(inst.grid.slow_min), L
        else:
            assert L.end_cause == "horizon" and L.start_min + c.D_min(inst.grid.slow_min) > inst.grid.horizon_min
    assert n_rec == 5
    assert _same_R(_R(res.schedule), _R(Schedule.eager(inst)))


def _fam_instance(m, rho=8, tau=2, H=1, T=96):
    F = fam.Fam(m, rho, tau, H, T)
    inst, _ = from_core(F.core_instance(), [np.zeros(0, dtype=np.int64)] * m)
    return F, inst


@pytest.mark.parametrize("m", [3, 5])
def test_safe_site_matches_fam(m):
    for (tau, H, T) in ((2, 1, 96), (1, 0, 48)):
        F, inst = _fam_instance(m, 8, tau, H, T)
        k = max(2, m)
        Phi = max(1, T // (k * F.D))
        for seed in range(5):
            ref = [o[o < T] for o in fam.safe_site_schedule(F, k, Phi, np.random.default_rng(seed))[0]]
            for params in (SAFE_NULL, {"D_slots": F.D, "k": k, "Phi": Phi}):
                model = LenderModel(schedule="safe_site", params=dict(params))
                got = _R(Lender(inst, model, np.random.default_rng(seed)).static_schedule())
                assert _same_R(got, ref), (m, tau, H, seed, params)
                assert _same_R(_R(build_R(inst, model, np.random.default_rng(seed))), ref)


def test_family_mode_errors():
    _, one = _fam_instance(1)
    with pytest.raises(ConfigError):
        Lender(one, LenderModel(schedule="safe_site", params=dict(SAFE_NULL)), np.random.default_rng(0))
    toy = toy_instance()                             # revocable D = 10 and 30 min
    h2 = toy_instance({"contracts": [{"id": "short", "tau_min": 5, "H_min": 2},
                                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": 5}],
                          "lenders.0.menu": ["short"], "lenders.0.prices": {"short": 2.85},
                          "lenders.1.menu": ["short"], "lenders.1.prices": {"short": 2.9}})   # H = 2 min
    for inst in (toy, h2):
        for model in (LenderModel(schedule="safe_site", params=dict(SAFE_NULL)),
                      LenderModel(schedule="iid_step", params=dict(IID_NULL))):
            with pytest.raises(ConfigError):
                Lender(inst, model, np.random.default_rng(0))
    _, ok = _fam_instance(3)
    Lender(ok, LenderModel(schedule="safe_site", params=dict(SAFE_NULL)), np.random.default_rng(0))
    Lender(ok, LenderModel(schedule="iid_step", params=dict(IID_NULL)), np.random.default_rng(0))


@pytest.mark.parametrize("m", [3, 5])
def test_iid_step_matches_fam(m):
    for (tau, H, T) in ((2, 1, 96), (1, 0, 48)):
        F, inst = _fam_instance(m, 8, tau, H, T)
        for seed in range(5):
            ref = fam.iid_step_schedule(F, 0.5, T // F.D, np.random.default_rng(seed))
            model = LenderModel(schedule="iid_step", params=dict(IID_NULL))
            got = _R(Lender(inst, model, np.random.default_rng(seed)).static_schedule())
            assert _same_R(got, ref), (m, tau, H, seed)
            assert _same_R(_R(build_R(inst, model, np.random.default_rng(seed))), ref)


def test_adaptive_matches_real_cost_renew():
    """RenewReplay of the rounded PD (r = 1) under 'adaptive': realized R equals
    pd.real_cost_renew(adversary=True)[1] and the lease cost equals its cost (1e-9)."""
    insts = [check_c4_lower.cm_instance(m, rho) for m in (2, 4) for rho in (2, 8)]
    insts += [core_case(seed, 0.0)[0] for seed in range(5)]
    n = 0
    for I in insts:
        pdr = ref_pd.FracPD(I).run()
        inst, _ = from_core(I, [np.zeros(0, dtype=np.int64)] * I.m)
        for s in range(4):
            x = ref_pd.round_pd(pdr, np.random.default_rng(s), r=1)
            cost, om = ref_pd.real_cost_renew(I, x["opened"], None, adversary=True)
            res = simulate(inst, RenewReplay(x["opened"]), LenderModel(schedule="adaptive"))
            assert res.invariant_failures == []
            assert _same_R(_R(res.schedule), [np.asarray(o, dtype=np.int64) for o in om]), (n, s)
            c = res.components
            assert_rel(c["lease_prepaid"] + c["lease_rent"] + c["loading"], cost, 1e-9, f"case {n} seed {s}")
        n += 1


def test_information_models():
    """I1: site_announced is None and only own notices arrive, at their announcement slots;
    I2: the bits equal the realized R membership."""
    inst = toy_instance()
    script = {0: [Buy(0, 0, 0), Buy(1, 1, 0)], 12: [Buy(0, 0, 0)], 14: [Buy(1, 0, 0)]}
    for info in ("I1", "I2"):
        pol = recording_policy(script)
        res = simulate(inst, pol, LenderModel(information=info))
        assert res.invariant_failures == []
        own = {L.id: L for L in res.leases}
        got = []
        for rec in pol.slow:
            if info == "I1":
                assert rec["site_announced"] is None
            else:
                sa = rec["site_announced"]
                assert sa.shape == (inst.m,) and sa.dtype == bool
                want = np.array([rec["t"] in set(res.schedule.R[l].tolist()) for l in range(inst.m)])
                assert np.array_equal(sa, want), rec["t"]
            for nt in rec["notices"]:
                assert nt.lease_id in own and nt.r_slot == rec["t"]
                L = own[nt.lease_id]
                assert nt.death_min == rec["t"] * inst.grid.slow_min + inst.contracts[L.contract].H_min
                got.append((nt.lease_id, rec["t"]))
        want = sorted((L.id, L.announce_slot) for L in res.leases if L.announce_slot is not None)
        assert sorted(got) == want and len(set(i for i, _ in got)) == len(got)
        assert len(want) == 3


def test_refuse_and_capacity():
    """Capacity (L0: 4 GPUs) and 'refuse' (L1: R = {10, 11})."""
    inst = toy_instance()

    def release_and_buy(obs, pol):
        first = obs.results[0]
        assert first.ok and first.lease_id is not None
        return [Release(first.lease_id), Buy(0, 1, 0, n_replicas=4)]

    script = {0: [Buy(0, 0, 0, n_replicas=5)],
              1: [Buy(0, 0, 0, n_replicas=3), Buy(0, 1, 0, n_replicas=2)],
              2: release_and_buy,
              10: [Buy(1, 0, 0)]}
    for mode in ("sell", "refuse"):
        pol = recording_policy(script)
        res = simulate(inst, pol, LenderModel(on_unavailable=mode))
        assert res.invariant_failures == []
        by_t = {rec["t"]: rec["results"] for rec in pol.slow}
        r0 = by_t[1]
        assert len(r0) == 1 and r0[0].ok is False and r0[0].reason == "capacity" and r0[0].lease_id is None
        r1 = by_t[2]
        assert [r.ok for r in r1] == [True, False] and r1[1].reason == "capacity"
        assert r1[0].reason == "" and len(r1[0].replica_ids) == 3
        r2 = by_t[3]
        assert [r.ok for r in r2] == [True, True], r2
        r10 = by_t[11]
        if mode == "sell":
            assert r10[0].ok is True
        else:
            assert r10[0].ok is False and r10[0].reason == "unavailable"
        assert sum(e[1] == "refuse" for e in res.events) == (3 if mode == "refuse" else 2)


def _violation_instance():
    series = [40.0] * 400
    series[5] = 18.0
    # merged layer sites (L1-2, L3-5) as the oracle below assumes; merging is not the subject here
    cfg = toy_config({"time.horizon_min": 60, "borrowers.clients.0.demand.values": [0.0] * 12,
                      "lender_model.merge_identical_layers": True}, sites=["P"])
    cfg["lenders"] = [inline_trace_lender(series, "X", n_layers=8, layer_gpus=8)] + cfg["lenders"]
    return build_instance(cfg)


def test_violations():
    """Slack drops to 18 GPUs at slot 5 while the platform holds 24: deficit 6 is logged; under
    'reclaim' the lender ends the latest lease at the highest layer site (LIFO) with cause 'violation'."""
    inst = _violation_instance()
    assert inst.lenders[0].B_gpus == 0.0 and inst.lenders[0].v0 == 0
    a, b = site_index(inst, "X/L1-2"), site_index(inst, "X/L3-5")
    sched = trace_schedule(inst)
    assert np.array_equal(sched.R[a], []) and np.array_equal(sched.R[b], [5])
    script = {0: [Buy(a, 0, 0, n_replicas=8), Buy(b, 0, 0, n_replicas=8)], 1: [Buy(b, 0, 0, n_replicas=8)]}
    for mode in ("absorb", "reclaim"):
        res = simulate(inst, recording_policy(script), LenderModel(violations=mode))
        assert res.invariant_failures == []
        assert len(res.violations) >= 1
        v = [x for x in res.violations if x.get("t") == 5 and x.get("lender") == "X" and "deficit" in x]
        assert len(v) >= 1 and (mode == "reclaim" or len(v) == 1), res.violations
        assert all(x.get("t") == 5 for x in res.violations if "deficit" in x), res.violations
        assert (v[0]["lender"], v[0]["required"], v[0]["slack"], v[0]["deficit"]) == ("X", 24, 18.0, 6.0)
        Ls = sorted(res.leases, key=lambda L: L.id)
        assert [(L.site, L.start_slot) for L in Ls] == [(a, 0), (b, 0), (b, 1)]
        A, B, C = Ls
        assert A.end_cause == "horizon"
        assert B.end_cause == "reclaim" and B.announce_slot == 5 and B.end_min == 30
        if mode == "absorb":
            assert C.end_cause == "reclaim" and C.end_min == 30
        else:
            assert C.end_cause == "violation" and C.end_min == 25
        assert sum(e[1] == "violation" for e in res.events) >= 1


def _owed_instance(offset: int = 0, slow: int = 5):
    """Inline lender X: 40 GPUs except 10 GPUs in 5-min slots 10-19 of a 2000-slot series (dips in 2 of
    1998 windows: P99 drop 0, B = 0), menu 'short' (D = 10 min, so D^max = 10 and h = 2 slow slots at
    Delta_s = 5, h = 10 at Delta_s = 1), layer_gpus 8, n_layers 2: Q25 = 40, v_top = 5, v0 = 3 (24 GPUs
    owed below the offered block while available)."""
    series = [40.0] * 2000
    series[10:20] = [10.0] * 10
    T_f = 120 // slow
    cfg = toy_config({"time.slow_slot_min": slow, "time.fast_slot_min": slow,
                      "borrowers.clients.0.demand.values": [0.0] * T_f}, sites=["P"])
    cfg["lenders"] = [inline_trace_lender(series, "X", n_layers=2, layer_gpus=8, offset=offset)] + cfg["lenders"]
    inst = build_instance(cfg)
    L = inst.lenders[0]
    assert L.lender == "X" and L.B_gpus == 0.0 and L.v0 == 3 and L.layer_gpus == 8 and L.D_max_lender_min == 10
    return inst


def test_owed_v0_window():
    """§6.5, S10: the v0 layers are owed only while available within the last h = ceil(D^max / Delta_s)
    slots. Hand case (_owed_instance): with no platform lease the old rule (v0 g = 24 > S = 10) reports a
    violation in each of the 10 dip slots; the new rule owes 24 at slots 10 and 11 (the 40-GPU level of slot
    9 lies h = 2 slots back at slot 11) and 8 from slot 12 on (slot 9 is h + 1 = 3 slots back), so it
    reports deficits 14 at slots 10 and 11 only, none attributable. With 8 platform GPUs: deficit 22 with 8
    attributable at slot 10, deficit 6, all attributable, at slot 12. With offset 10 the window reaches
    back before the horizon start (24 owed at slots 0 and 1, 8 at slot 2); at Delta_s = 1 (h = 10
    minutes) 24 is owed at minute 59 (minute 49 lies h back) and 8 at minute 60."""
    inst = _owed_instance()
    L = inst.lenders[0]
    lender = Lender(inst, LenderModel(), np.random.default_rng(0))
    old = [t for t in range(inst.grid.T_slow) if L.v0 * L.layer_gpus > L.S[t]]
    assert old == list(range(10, 20))
    owed = [lender.owed(t)["X"] for t in range(inst.grid.T_slow)]
    assert owed == [24] * 12 + [8] * 8 + [24] * 4, owed
    got = {t: lender.violations(t, {}) for t in range(inst.grid.T_slow)}
    assert [t for t, v in got.items() if v] == [10, 11]
    for t in (10, 11):
        (v,) = got[t]
        assert (v["lender"], v["required"], v["slack"], v["deficit"], v["owed"], v["deficit_attributable"]) == \
            ("X", 24, 10.0, 14.0, 24, 0.0)
    (v,) = lender.violations(10, {"X": 8})
    assert (v["required"], v["deficit"], v["deficit_attributable"]) == (32, 22.0, 8.0)
    (v,) = lender.violations(12, {"X": 8})
    assert (v["required"], v["deficit"], v["deficit_attributable"]) == (16, 6.0, 6.0)
    assert lender.violations(12, {"X": 2}) == []

    inst = _owed_instance(offset=10)
    lender = Lender(inst, LenderModel(), np.random.default_rng(0))
    assert inst.lenders[0].S[0] == 10.0
    assert [lender.owed(t)["X"] for t in range(4)] == [24, 24, 8, 8]
    assert [t for t in range(inst.grid.T_slow) if lender.violations(t, {})] == [0, 1]

    inst = _owed_instance(slow=1)
    lender = Lender(inst, LenderModel(), np.random.default_rng(0))
    assert inst.grid.T_slow == 120 and inst.lenders[0].S[49] == 40.0 and inst.lenders[0].S[50] == 10.0
    owed = [lender.owed(t)["X"] for t in range(120)]
    assert owed[59] == 24 and owed[60] == 8 and owed[:60] == [24] * 60 and owed[60:100] == [8] * 40
    assert [t for t in range(120) if lender.violations(t, {})] == list(range(50, 60))

    # Delta_s = 1 with offset 10: the window slots t' < 0 map to the 5-min slots 10 + floor(t'/5) = 9 and 8
    # (40 GPUs), so 24 is owed at minutes 0-9 and 8 from minute 10 (minute 0 lies h back); truncating
    # t'/5 toward 0 would map minutes -4..-1 to the dip and owe 8 from minute 6
    inst = _owed_instance(offset=10, slow=1)
    lender = Lender(inst, LenderModel(), np.random.default_rng(0))
    assert inst.lenders[0].S[0] == 10.0 and inst.lenders[0].S[49] == 10.0 and inst.lenders[0].S[50] == 40.0
    owed = [lender.owed(t)["X"] for t in range(120)]
    assert owed[:12] == [24] * 10 + [8, 8] and owed[10:50] == [8] * 40, owed[:12]
    assert [t for t in range(120) if lender.violations(t, {})] == list(range(10))


def _owed_buffer_instance():
    """Inline lender X with a positive buffer: 52 GPUs except 30 GPUs in 5-min slots 10-19 and single
    slots of 42 GPUs every 20 slots from slot 100 on (2000 slots). The 10-GPU drops occur in about 9.5% of
    the 10-min windows, so the P99 drop is 10: b = 10 / mean and B = 10 GPUs (1e-9). S_lend = S - B is 42,
    32 or 20; Q25 = 42, v_top = 5, v0 = 3 (24 GPUs), offered layers 4-5; menu 'short' (D^max = 10 min,
    h = 2 slow slots)."""
    series = [52.0] * 2000
    series[10:20] = [30.0] * 10
    for t in range(100, 1990, 20):
        series[t] = 42.0
    cfg = toy_config({"borrowers.clients.0.demand.values": [0.0] * 24}, sites=["P"])
    cfg["lenders"] = [inline_trace_lender(series, "X", n_layers=2, layer_gpus=8)] + cfg["lenders"]
    inst = build_instance(cfg)
    L = inst.lenders[0]
    assert L.lender == "X" and abs(L.B_gpus - 10.0) <= 1e-9 and L.v0 == 3 and L.D_max_lender_min == 10
    return inst


def test_owed_uses_lendable_slack():
    """§6.5, S10: owed is computed from the lendable slack S_lend = (S - B)^+, not from the physical slack
    S. Hand case _owed_buffer_instance: in the dip S = 30 >= v0 g = 24 but S_lend = 20, so from slot 12
    (slot 9 lies h + 1 back) owed = 8 floor(20 / 8) = 16, not 24. No violation without platform leases; with
    8 platform GPUs, slot 10 (owed 24, required 32 > 30) has deficit 2, all attributable, while slots 12-19
    (required 24 <= 30) have none."""
    inst = _owed_buffer_instance()
    L = inst.lenders[0]
    assert [s.id for s in inst.sites if s.lender == "X"] == ["X/L4-4", "X/L5-5"]
    assert L.S[10] == 30.0 and abs(L.S_lend[10] - 20.0) <= 1e-9 and L.S[9] == 52.0
    lender = Lender(inst, LenderModel(), np.random.default_rng(0))
    owed = [lender.owed(t)["X"] for t in range(inst.grid.T_slow)]
    assert owed == [24] * 12 + [16] * 8 + [24] * 4, owed
    assert [t for t in range(inst.grid.T_slow) if lender.violations(t, {})] == []
    got = {t: lender.violations(t, {"X": 8}) for t in range(inst.grid.T_slow)}
    assert [t for t, v in got.items() if v] == [10, 11]
    for t in (10, 11):
        (v,) = got[t]
        assert (v["required"], v["slack"], v["deficit"], v["owed"], v["deficit_attributable"]) == \
            (32, 30.0, 2.0, 24, 2.0)


def test_violations_attributable_engine():
    """Engine metrics of §6.5 on _owed_instance: a lease of 8 GPUs bought at slot 0 on the lower layer
    (R = slots 10-19) is announced at slot 10 and dies at minute 55, so it is alive at the start of slot
    10 only. Violations at slots 10 (required 32, deficit 22, attributable 8) and 11 (24, 14, 0):
    buffer_violations 2 lender-slots and 36 GPU-slots, attributable 1 and 8. AlwaysFallback: 2 and 28,
    attributable 0 and 0."""
    from sublet.metrics import run_metrics
    from sublet.policies import AlwaysFallback
    inst = _owed_instance()
    a = site_index(inst, "X/L4-4")
    res = simulate(inst, recording_policy({0: [Buy(a, 0, 0, n_replicas=8)]}), LenderModel())
    assert res.invariant_failures == []
    (L,) = res.leases
    assert L.announce_slot == 10 and L.end_min == 55
    assert [(v["t"], v["required"], v["deficit"], v["deficit_attributable"]) for v in res.violations] == \
        [(10, 32, 22.0, 8.0), (11, 24, 14.0, 0.0)]
    bv = run_metrics(res, inst)
    assert bv["buffer_violations"]["count"] == 2 and bv["buffer_violations"]["deficit_gpu_slots"] == 36.0
    assert bv["buffer_violations_attributable"]["count"] == 1
    assert bv["buffer_violations_attributable"]["deficit_gpu_slots"] == 8.0
    assert bv["buffer_violations"]["share"] == 2 / inst.grid.T_slow
    res = simulate(inst, AlwaysFallback(), LenderModel())
    bv = run_metrics(res, inst)
    assert bv["buffer_violations"]["count"] == 2 and bv["buffer_violations"]["deficit_gpu_slots"] == 28.0
    assert bv["buffer_violations_attributable"] == {"count": 0, "share": 0.0, "deficit_gpu_slots": 0.0}


def _corr_series(dips):
    """A 2000-slot 5-min series of 40 GPUs with the given (first slot, end slot, depth) dips."""
    s = np.full(2000, 40.0)
    for (t0, t1, depth) in dips:
        s[t0:t1] = depth
    return s


def _corr_instance(merge: bool = True):
    """Lenders X and Y (group G) and Z (group H), three offered layers each (local layers 1-3 at 24, 32 and 40
    GPUs). Merged (merge True): X and Y two sites each (layers {1} and {2, 3}), Z one site (layers 1-3); merge
    False gives the default structure of §10 S32, three sites per lender, in which X's onset at slot 3 is shared
    by its three layer sites and its onset at slot 12 by two."""
    cfg = toy_config({"lender_model.merge_identical_layers": merge}, sites=["P"])
    cfg["lenders"] = [inline_trace_lender(_corr_series([(3, 5, 20.0), (12, 13, 28.0)]), "X", group="G", n_layers=3),
                      inline_trace_lender(_corr_series([(8, 9, 20.0), (17, 20, 30.0)]), "Y", group="G", n_layers=3),
                      inline_trace_lender(_corr_series([(6, 7, 10.0)]), "Z", group="H", n_layers=3)] + cfg["lenders"]
    return build_instance(cfg)


def _corr_single_target_instance(merge: bool = True):
    """Lenders X (three offered layers), Y (two) and W (one), all in group G. X: local layer 1 {3, 4, 20, 22, 23},
    layers 2 and 3 also {12, 13} (merged: sites {1} and {2, 3}; without merging the onsets 3, 20 and 22 are shared
    by three layer sites and 12 by two). Y: layer 1 {8}, layer 2 {8, 9, 10, 16, 17}; W: {6}. Every site of Y and
    W is a single layer in both settings, and the source sites that reach X (Y's and W's, at local layers 1 and 2)
    lie at or below the lowest layer of X's two-layer site {2, 3} (its other site {1} is a single layer), so the
    target side cannot differ across merge settings (§6.6). X's run at slots 22-23 is truncated at the horizon
    (24 slots) for delays of 1 and 2."""
    cfg = toy_config({"lender_model.merge_identical_layers": merge}, sites=["P"])
    cfg["lenders"] = [
        inline_trace_lender(_corr_series([(3, 5, 20.0), (12, 14, 28.0), (20, 21, 10.0), (22, 24, 20.0)]), "X",
                            group="G", n_layers=3),
        inline_trace_lender(_corr_series([(8, 9, 30.0), (9, 11, 35.0), (16, 18, 35.0)]), "Y", group="G",
                            n_layers=2),
        inline_trace_lender(_corr_series([(6, 7, 39.0)]), "W", group="G", n_layers=1)] + cfg["lenders"]
    return build_instance(cfg)


def _runs(R):
    """(onset, length) of the runs of consecutive slots of a sorted set."""
    out, R = [], list(R)
    i = 0
    while i < len(R):
        j = i
        while j + 1 < len(R) and R[j + 1] == R[j] + 1:
            j += 1
        out.append((R[i], j - i + 1))
        i = j + 1
    return out


def _layers(inst, R):
    """{(lender, local layer): list} with one entry per offered layer of every layer site (a merged site gives its
    set to each of its layers), and {(site id, None): list} for the other sites: the per-layer sets, comparable
    across merge settings."""
    out = {}
    for i, s in enumerate(inst.sites):
        if s.kind != "layer":
            out[(s.id, None)] = R[i].tolist()
            continue
        for v in range(s.local_layer_lo, s.local_layer_lo + s.layer_hi - s.layer_lo + 1):
            out[(s.lender, v)] = R[i].tolist()
    return out


def _corr_members(inst, groups):
    """(lender id, group key, its revocable sites in increasing local_layer_lo) for every lender with at least one
    revocable site, in lender index order; the key is Site.group, one key for groups 'all', the lender for 'none'."""
    out = []
    for lt in inst.lenders:
        sites = [i for i in _sites_of(inst, lt.lender) if inst.sites[i].kind != "protected"]
        if sites:
            key = {"all": "all", "none": lt.lender}.get(groups, inst.sites[sites[0]].group)
            out.append((lt.lender, key, sites))
    return out


def _expected_correlated(inst, base, groups):
    """The sets of §6.6 with p_sh = 1 and no delay, written without the draw loop: every run of a source site is
    copied in place, so a revocable site i takes the whole base set of every site b of every other member of its
    group with local_layer_lo(b) <= local_layer_lo(i)."""
    out = [set(map(int, r)) for r in base]
    members = _corr_members(inst, groups)
    for l2, key2, targets in members:
        for l, key, sources in members:
            if l == l2 or key != key2:
                continue
            for i in targets:
                for b in sources:
                    if inst.sites[b].local_layer_lo <= inst.sites[i].local_layer_lo:
                        out[i] |= set(map(int, base[b]))
    return [np.array(sorted(x), dtype=np.int64) for x in out]


def _expected_correlated_draws(inst, base, p_sh, dmax, rng, groups=None):
    """The loop of §6.6 with its normative RNG order (§10 S11: one draw per (source lender, onset, target lender)),
    from the base (trace) sets: for each member l in lender index order with another member in its group, each slot
    t of U_l (the run onsets of l's sites, merged) in increasing order and each other member l2 of the group in index
    order: a Bernoulli(p_sh) draw and, if it hits, one delay d for this (l, t, l2); then every site b of l with a run
    onset at t copies that run, shifted by d and truncated to the horizon, to every site of l2 whose local_layer_lo
    is at least b's. `rng` is left in its state after the last draw."""
    T = inst.grid.T_slow
    out = [set(map(int, r)) for r in base]
    members = _corr_members(inst, groups)
    for l, key, sources in members:
        others = [x for x in members if x[1] == key and x[0] != l]
        if not others:
            continue
        run_at = {b: dict(_runs(base[b])) for b in sources}
        for t in sorted({t for b in sources for t in run_at[b]}):
            for _, _, targets in others:
                if rng.random() < p_sh:
                    d = int(rng.integers(0, dmax + 1))
                    for b in sources:
                        if t in run_at[b]:
                            for i in targets:
                                if inst.sites[i].local_layer_lo >= inst.sites[b].local_layer_lo:
                                    out[i] |= set(range(t + d, min(T, t + d + run_at[b][t])))
    return [np.array(sorted(x), dtype=np.int64) for x in out]


def _corr(inst, p_sh, groups=None, delay=0, seed=0):
    """The 'correlated' sets of build_R (equal to the Lender's static schedule) and the generator state after
    build_R."""
    m = LenderModel(schedule="correlated", params={"p_sh": p_sh, "groups": groups, "delay_slots_max": delay})
    rng = np.random.default_rng(seed)
    R = _R(build_R(inst, m, rng))
    assert _same_R(R, _R(Lender(inst, m, np.random.default_rng(seed)).static_schedule()))
    return R, rng.bit_generator.state


CORR_BASE = {("X", 1): [3, 4], ("X", 2): [3, 4, 12], ("X", 3): [3, 4, 12], ("Y", 1): [8], ("Y", 2): [8, 17, 18, 19],
             ("Y", 3): [8, 17, 18, 19], ("Z", 1): [6], ("Z", 2): [6], ("Z", 3): [6], ("P", None): []}


@pytest.mark.parametrize("merge", [True, False])
def test_correlated_shocks(merge):
    """§6.6 hand case _corr_instance, on merged sites and on one site per layer: p_sh = 0 (any groups) and groups
    'none' give the trace sets; p_sh = 1 with delay 0 gives the deterministic union (_expected_correlated) and the
    hand values per layer, for groups from Site.group and 'all'; for p_sh = 0.5 with delays up to 2 slots nesting is
    preserved and the trace sets are kept. Groups 'all' shows the target-side difference that remains across merge
    settings: Z's merged site (layers 1-3) takes only the shocks of the layer-1 sites of X and Y, while with one site
    per layer Z's layers 2 and 3 also take those of X's and Y's layer-2 sites (slots 12 and 17-19)."""
    inst = _corr_instance(merge)
    n_sites = {"X": 2, "Y": 2, "Z": 1} if merge else {"X": 3, "Y": 3, "Z": 3}
    assert {l: len(_sites_of(inst, l)) for l in n_sites} == n_sites, [s.id for s in inst.sites]
    base = _R(build_R(inst, LenderModel(), np.random.default_rng(0)))
    assert _layers(inst, base) == CORR_BASE
    for groups in (None, "all", "none"):
        assert _same_R(_corr(inst, 0.0, groups, delay=2)[0], base), groups
    assert _same_R(_corr(inst, 1.0, "none")[0], base)
    up = [3, 4, 8, 12, 17, 18, 19]
    hand = {**CORR_BASE, ("X", 1): [3, 4, 8], ("X", 2): up, ("X", 3): up, ("Y", 1): [3, 4, 8], ("Y", 2): up,
            ("Y", 3): up}
    got = _corr(inst, 1.0)[0]
    assert _same_R(got, _expected_correlated(inst, base, None))
    assert _layers(inst, got) == hand
    up = [3, 4, 6, 8, 12, 17, 18, 19]
    z_up = [3, 4, 6, 8] if merge else up
    hand = {("X", 1): [3, 4, 6, 8], ("X", 2): up, ("X", 3): up, ("Y", 1): [3, 4, 6, 8], ("Y", 2): up, ("Y", 3): up,
            ("Z", 1): [3, 4, 6, 8], ("Z", 2): z_up, ("Z", 3): z_up, ("P", None): []}
    got = _corr(inst, 1.0, "all")[0]
    assert _same_R(got, _expected_correlated(inst, base, "all"))
    assert _layers(inst, got) == hand
    for seed in range(5):
        R = _corr(inst, 0.5, delay=2, seed=seed)[0]
        for l in ("X", "Y", "Z"):
            s = _sites_of(inst, l)
            for a, b in zip(s, s[1:]):
                assert set(R[a]) <= set(R[b])
            for i in s:
                assert set(base[i]) <= set(R[i]) and (len(R[i]) == 0 or R[i].max() < inst.grid.T_slow)


@pytest.mark.parametrize("merge", [True, False])
def test_correlated_rng_order(merge):
    """§6.6 correlated shocks with p_sh = 0.5 and delays up to 2 slots, groups from Site.group and 'all', seeds 0-4,
    on _corr_instance and _corr_single_target_instance: exactly the sets of an independent implementation of the
    normative loop (one Bernoulli draw per (source lender, onset, target lender), then its delay), and the generator
    left in the same state, on merged layer sites and on one site per layer (the default of §10 S32)."""
    differ = 0
    for make in (_corr_instance, _corr_single_target_instance):
        inst = make(merge)
        base = _R(build_R(inst, LenderModel(), np.random.default_rng(0)))
        for groups in (None, "all"):
            for seed in range(5):
                got, state = _corr(inst, 0.5, groups, delay=2, seed=seed)
                rng = np.random.default_rng(seed)
                want = _expected_correlated_draws(inst, base, 0.5, 2, rng, groups)
                assert _same_R(got, want), (make.__name__, groups, seed, got, want)
                assert state == rng.bit_generator.state, (make.__name__, groups, seed)
                differ += not _same_R(got, base)
    assert differ > 0


# draws of rng.random() per (instance, groups): sum over the members l with another member in their group of
# |U_l| x (number of other members); _corr_instance: U_X = {3, 12}, U_Y = {8, 17}, U_Z = {6};
# _corr_single_target_instance: U_X = {3, 12, 20, 22}, U_Y = {8, 16}, U_W = {6}
CORR_UNIFORM_DRAWS = {("_corr_instance", None): 4, ("_corr_instance", "all"): 10, ("_corr_instance", "none"): 0,
                      ("_corr_single_target_instance", None): 14, ("_corr_single_target_instance", "all"): 14,
                      ("_corr_single_target_instance", "none"): 0}


def test_correlated_draws_merge_invariant():
    """§6.6, §10 S11: the number and order of the draws do not depend on merge_identical_layers. On _corr_instance
    and _corr_single_target_instance, where some onset of X is shared by more layer sites without merging than with
    it (so the per-site draw that the rule replaced drew more often without merging), the generator state after
    build_R is the same in both settings for the same seed (p_sh in {0, 0.5, 1}, delays up to 0 and 2 slots, groups
    from Site.group, 'all' and 'none', seeds 0-4). At p_sh = 0 (no delay draws) it is the state after the hand count
    of rng.random() draws, CORR_UNIFORM_DRAWS."""
    for make in (_corr_instance, _corr_single_target_instance):
        insts = {m: make(m) for m in (True, False)}
        shared = {}
        for m, inst in insts.items():
            base = _R(build_R(inst, LenderModel(), np.random.default_rng(0)))
            on = [t for i in _sites_of(inst, "X") for t, _ in _runs(base[i])]
            shared[m] = max(on.count(t) for t in on)
        assert shared[False] > shared[True] >= 1, (make.__name__, shared)
        for groups in (None, "all", "none"):
            for p_sh in (0.0, 0.5, 1.0):
                for delay in (0, 2):
                    for seed in range(5):
                        states = [_corr(insts[m], p_sh, groups, delay, seed)[1] for m in (True, False)]
                        assert states[0] == states[1], (make.__name__, groups, p_sh, delay, seed)
                        if p_sh == 0.0:
                            ref = np.random.default_rng(seed)
                            for _ in range(CORR_UNIFORM_DRAWS[(make.__name__, groups)]):
                                ref.random()
                            assert states[0] == ref.bit_generator.state, (make.__name__, groups, seed)


def test_correlated_merge_single_layer_targets():
    """§6.6: where the target side cannot differ (_corr_single_target_instance: the sites of Y and W are single
    layers, and the merged X site {2, 3} faces source sites at local layers 1 and 2 only), the realized per-layer
    sets are identical with merge_identical_layers on and off, for p_sh in {0.5, 1}, delays up to 0 and 2 slots,
    groups from Site.group, seeds 0-9, although X has fewer sites when merged. The shocks are exercised (some
    realized set differs from the trace set) and differ across seeds."""
    a, b = _corr_single_target_instance(True), _corr_single_target_instance(False)
    assert [len(_sites_of(a, l)) for l in ("X", "Y", "W")] == [2, 2, 1]
    assert [len(_sites_of(b, l)) for l in ("X", "Y", "W")] == [3, 2, 1]
    assert all(s.layer_lo == s.layer_hi for s in a.sites if s.lender in ("Y", "W"))
    base_a = _R(build_R(a, LenderModel(), np.random.default_rng(0)))
    base_b = _R(build_R(b, LenderModel(), np.random.default_rng(0)))
    want_base = {("X", 1): [3, 4, 20, 22, 23], ("X", 2): [3, 4, 12, 13, 20, 22, 23],
                 ("X", 3): [3, 4, 12, 13, 20, 22, 23], ("Y", 1): [8], ("Y", 2): [8, 9, 10, 16, 17], ("W", 1): [6],
                 ("P", None): []}
    assert _layers(a, base_a) == _layers(b, base_b) == want_base
    seen, shocked = set(), 0
    for p_sh in (0.5, 1.0):
        for delay in (0, 2):
            for seed in range(10):
                Ra, sa = _corr(a, p_sh, None, delay, seed)
                Rb, sb = _corr(b, p_sh, None, delay, seed)
                La = _layers(a, Ra)
                assert La == _layers(b, Rb), (p_sh, delay, seed)
                assert sa == sb
                shocked += La != want_base
                seen.add(tuple(map(tuple, La.values())))
    assert shocked > 0 and len(seen) > 2


def test_eager_protected_empty():
    inst = toy_instance()
    e = _R(Schedule.eager(inst))
    model = LenderModel(schedule="eager")
    assert _same_R(_R(Lender(inst, model, np.random.default_rng(0)).static_schedule()), e)
    assert _same_R(_R(build_R(inst, model, np.random.default_rng(0))), e)
    assert np.array_equal(e[0], np.arange(24)) and np.array_equal(e[1], np.arange(24)) and len(e[2]) == 0
