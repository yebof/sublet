"""Tests of sublet/opt/relax.py, the merged relaxation of layer sites (design/sim_spec.md §6.2, §10 S32)."""
import copy
import dataclasses

import numpy as np
import pytest

from fixtures import (CONFIGS, explicit_client, explicit_llm, inline_trace_lender, load_json, toy_config,
                      trace_schedule, with_stranding)

from sublet.engine import EngineConfig, simulate
from sublet.instance import build_instance, public_view
from sublet.lender import Lender
from sublet.opt.milp import estimate_size, solve_eager, solve_lp, solve_opt
from sublet.opt.relax import merged_relaxation
from sublet.policies import FixedPlan
from sublet.types import LenderModel, Schedule

TOL = 1e-7          # merged <= unmerged, relative (§10 S32)
GAP = 1e-9


def _series(rng, step: int, T_s: int, n: int = 20000) -> np.ndarray:
    """A 5-min slack series of n slots at 64 GPUs with dips in the first T_s slots to levels that are
    multiples of `step` (step 16 skips every other 8-GPU band, so consecutive layers often share their
    announcement sets; step 8 separates them). Dips are rare, so the P99 buffer is 0."""
    s = np.full(n, 64.0)
    lv = np.arange(64 - 3 * step, 64, step, dtype=float)
    dip = rng.random(T_s) < 0.4
    s[:T_s][dip] = rng.choice(lv, size=int(dip.sum()))
    return s


def _relax_config(seed: int):
    """Toy variant with T_s = 12, the protected site P and one inline trace lender of 2-4 layers of 8 GPUs
    (offered block at levels up to 64, v0 = 8 - V), plus a second one of 2-3 layers when the first has at
    most 3; contracts short and long; one or two clients with demand of 0-3 replica loads in steps of 0.5
    per slow slot, two LLMs (g = 1 and g = 3) for every third seed; Delta_s = 5 and Delta_f = 5 or (every
    fourth seed) 1; mu = 0 for even seeds."""
    rng = np.random.default_rng([seed, 4242])
    fast = 1 if seed % 4 == 3 else 5
    T_s = 12
    cfg = toy_config({"time.horizon_min": 5 * T_s, "time.fast_slot_min": fast}, sites=["P"])
    lenders = []
    V0 = int(rng.integers(2, 5))
    for i in range(2 if (V0 <= 3 and rng.random() < 0.5) else 1):
        step = (16, 8)[(seed + i) % 2] if i else int(rng.choice([16, 8]))
        V = V0 if i == 0 else int(rng.integers(2, 4))
        lenders.append(inline_trace_lender(_series(rng, step, T_s), f"X{i}", n_layers=V,
                                           menu=["short", "long"], prices={"short": 2.85, "long": 3.0},
                                           region="r0", lam_s=float(rng.choice([0.0, 300.0]))))
    cfg["lenders"] = lenders + cfg["lenders"]
    two = seed % 3 == 1
    if two:
        cfg["llms"] = [explicit_llm("M", 1), explicit_llm("M3", 3)]
    clients = []
    for c in range(1 + int(rng.random() < 0.5)):
        d = np.where(rng.random(T_s) < 0.75, rng.integers(1, 7, T_s) / 2, 0.0)
        clients.append(explicit_client(np.repeat(d, 5 // fast), ("M", "M3")[c % 2] if two else "M",
                                       borrower=f"b{c}"))
    cfg["borrowers"]["clients"] = clients
    if seed % 2 == 0:
        cfg["stranding"]["mu_over_beta_tilde"] = 0.0      # mu = 0: the replay is exact (§8.10)
    return cfg


def _check_site_map(inst, sched, inst_m, sched_m, smap):
    """site_map: onto, non-decreasing, runs of consecutive layer sites of one lender with identical sets
    and summed capacities; unmerged sites kept as they are; consecutive merged sites of one lender differ
    in their sets (maximal runs)."""
    m, mm = inst.m, inst_m.m
    assert smap.shape == (m,) and np.all(np.diff(smap) >= 0) and set(smap.tolist()) == set(range(mm))
    for i in range(mm):
        old = np.flatnonzero(smap == i)
        assert np.array_equal(old, np.arange(old[0], old[-1] + 1))
        new = inst_m.sites[i]
        assert all(np.array_equal(sched.R[l], sched_m.R[i]) for l in old)
        assert new.capacity_gpus == sum(inst.sites[l].capacity_gpus for l in old)
        assert all(inst.sites[l].lender == new.lender and inst.sites[l].kind == new.kind for l in old)
        assert np.array_equal(inst_m.price[i], inst.price[old[0]])
        assert np.array_equal(inst_m.lam_s[:, i], inst.lam_s[:, old[0]])
        assert np.array_equal(inst_m.clients.delta_usd_per_h[:, i], inst.clients.delta_usd_per_h[:, old[0]])
        if len(old) == 1:
            assert new is inst.sites[old[0]]
        else:
            lo, hi = inst.sites[old[0]], inst.sites[old[-1]]
            assert new.kind == "layer" and new.id == f"{new.lender}/L{lo.layer_lo}-{hi.layer_hi}"
            assert (new.layer_lo, new.layer_hi, new.local_layer_lo) == (lo.layer_lo, hi.layer_hi, lo.local_layer_lo)
            assert [inst.sites[l].layer_hi for l in old[:-1]] == [inst.sites[l].layer_lo - 1 for l in old[1:]]
    for i in range(mm - 1):
        a, b = inst_m.sites[i], inst_m.sites[i + 1]
        if a.kind == b.kind == "layer" and a.lender == b.lender:
            assert not np.array_equal(sched_m.R[i], sched_m.R[i + 1]), (a.id, b.id)
    for lt, lt_m in zip(inst.lenders, inst_m.lenders):
        assert tuple(sorted({int(smap[l]) for l in lt.site_index})) == tuple(lt_m.site_index)
    for name in ("grid", "contracts", "llms", "stranding", "billing", "units_per_replica", "name", "seed"):
        assert getattr(inst_m, name) is getattr(inst, name)
    assert inst_m.clients.demand is inst.clients.demand


def _le(a, b, what):
    assert a <= b + TOL * max(1.0, abs(b)), f"{what}: merged {a!r} > unmerged {b!r}"


@pytest.mark.slow
def test_merged_relaxation_bounds():
    """§10 S32 on 40 random toy variants with inline trace lenders of 2-4 layers (merge off): the merged
    MILP, LP and (on the 1-min variants) slow_lb MILP and LP values, and OPT_eager on some, are at most
    the unmerged ones; with mu = 0 the unmerged MILP plan, mapped by site_map, replays on inst_m at the
    unmerged objective; with the trace schedule inst_m equals the instance built with merging on, and its
    trace lender reproduces sched_m; site_map is consistent. Some variants merge, some do not."""
    n_merged = n_kept = 0
    for seed in range(40):
        cfg = _relax_config(seed)
        assert "merge_identical_layers" not in cfg["lender_model"]
        inst = build_instance(cfg)
        assert inst.config["lender_model"]["merge_identical_layers"] is False     # the default (§10 S32)
        sched = trace_schedule(inst)
        inst_m, sched_m, smap = merged_relaxation(inst, sched)
        _check_site_map(inst, sched, inst_m, sched_m, smap)
        n_merged += inst_m.m < inst.m
        n_kept += inst_m.m == inst.m
        # the merge on the trace schedule is the builder's merge (merge_identical_layers true)
        cfg2 = copy.deepcopy(cfg)
        cfg2["lender_model"]["merge_identical_layers"] = True
        inst_t = build_instance(cfg2)
        assert [(s.id, s.capacity_gpus, s.layer_lo, s.layer_hi, s.local_layer_lo, s.menu) for s in inst_t.sites] == \
            [(s.id, s.capacity_gpus, s.layer_lo, s.layer_hi, s.local_layer_lo, s.menu) for s in inst_m.sites]
        for name in ("price", "lam_s", "beta_usd"):
            assert np.array_equal(getattr(inst_t, name), getattr(inst_m, name)), name
        assert np.array_equal(inst_t.clients.delta_usd_per_h, inst_m.clients.delta_usd_per_h)
        assert np.array_equal(inst_t.clients.demand, inst_m.clients.demand)
        assert np.array_equal(inst_t.stranding.mu_fb_usd, inst.stranding.mu_fb_usd)
        R_lender = Lender(inst_m, LenderModel(), np.random.default_rng(0)).static_schedule().R
        assert all(np.array_equal(a, b) for a, b in zip(R_lender, sched_m.R))
        assert estimate_size(inst_m, sched_m)["n_vars"] > 0
        grid = "slow" if inst.grid.phi == 1 else "fast"
        opt = solve_opt(inst, sched, grid=grid, mip_rel_gap=GAP)
        opt_m = solve_opt(inst_m, sched_m, grid=grid, mip_rel_gap=GAP)
        assert opt.status == 0 and opt_m.status == 0, (seed, opt.status_msg, opt_m.status_msg)
        _le(opt_m.objective, opt.objective, f"seed {seed} MILP {grid}")
        lp, lp_m = solve_lp(inst, sched, grid=grid), solve_lp(inst_m, sched_m, grid=grid)
        assert lp.status == 0 and lp_m.status == 0
        _le(lp_m.objective, lp.objective, f"seed {seed} LP {grid}")
        if grid == "fast":
            for integral in (True, False):
                lb = solve_opt(inst, sched, grid="slow_lb", integral=integral, mip_rel_gap=GAP)
                lb_m = solve_opt(inst_m, sched_m, grid="slow_lb", integral=integral, mip_rel_gap=GAP)
                assert lb.status == 0 and lb_m.status == 0
                _le(lb_m.objective, lb.objective, f"seed {seed} slow_lb integral={integral}")
        elif seed % 5 == 0:
            ea, eb = solve_eager(inst, mip_rel_gap=GAP), solve_eager(inst_m, mip_rel_gap=GAP)
            assert ea.status == 0 and eb.status == 0
            _le(eb.objective, ea.objective, f"seed {seed} OPT_eager")
        if not inst.stranding.mu_fb_usd.any() and not inst.stranding.mu_kv_usd.any():
            plan = [dataclasses.replace(p, site=int(smap[p.site])) for p in opt.plan]
            res = simulate(inst_m, FixedPlan(plan), LenderModel(), EngineConfig())
            assert res.invariant_failures == []
            assert not any(e[1] == "refuse" for e in res.events)
            tot = res.components["total"]
            assert abs(tot - opt.objective) <= 1e-6 * max(1.0, opt.objective), (seed, tot, opt.objective)
    assert n_merged >= 10 and n_kept >= 3, (n_merged, n_kept)


def test_merged_relaxation_strict_hand():
    """Equality is not claimed (§10 S32): one lender with two 8-GPU layers of identical (empty) sets, an
    LLM with g = 3, demand 5 replica loads over 20 minutes, 'short' at 2.85 USD/GPU-h (prepaid 10 min, then
    rent), no other site, mu = 0. Unmerged, each layer holds 2 replicas: 4 x 3 x 2.85 / 3 + 1 x 3 x 7.15 / 3
    = 18.55 USD; merged, 16 GPUs hold 5 replicas: 5 x 2.85 = 14.25 USD. The LP is 14.25 in both (8/3
    replicas per layer)."""
    cfg = toy_config({"time.horizon_min": 20, "stranding.mu_over_beta_tilde": 0.0}, sites=[])
    cfg["llms"] = [explicit_llm("M", 3)]
    cfg["lenders"] = [inline_trace_lender([16.0] * 400, "X", n_layers=2, layer_gpus=8, lam_s=0.0)]
    cfg["borrowers"]["clients"] = [explicit_client([5.0] * 4, "M")]
    inst = build_instance(cfg)
    assert [s.id for s in inst.sites] == ["X/L1-1", "X/L2-2"]
    sched = trace_schedule(inst)
    assert all(len(r) == 0 for r in sched.R)
    inst_m, sched_m, smap = merged_relaxation(inst, sched)
    assert [s.id for s in inst_m.sites] == ["X/L1-2"] and inst_m.sites[0].capacity_gpus == 16.0
    assert smap.tolist() == [0, 0]
    a, b = solve_opt(inst, sched, mip_rel_gap=GAP), solve_opt(inst_m, sched_m, mip_rel_gap=GAP)
    assert a.status == 0 and b.status == 0
    assert abs(a.objective - 18.55) <= 1e-9 and abs(b.objective - 14.25) <= 1e-9, (a.objective, b.objective)
    for x in (solve_lp(inst, sched), solve_lp(inst_m, sched_m)):
        assert x.status == 0 and abs(x.objective - 14.25) <= 1e-9, x.objective


def test_merged_relaxation_kv_stranding():
    """§10 S32: the mapped plan costs no more, and with mu_kv > 0 it can cost less, since stranding_kv
    counts persisting load that leaves a site (§5.6 m_c) and a move between two merged layers is none.
    One lender, two 1-GPU layers with R = {3} on both (B = 0, v0 = 0), contract 'k' (tau 10 min, H 0,
    prepaid 10 min) at 1 USD/GPU-h, lambda 300 s, demand 1 from slot 1, mu_kv = 0.2, mu_fb = 0. Lease A
    (slot 0) dies at minute 15; its replacement must be bought at slot 2 (tau: no announcement at or after
    slot 4), when A still fills its layer, so unmerged it sits on the other layer and the load moves there
    at slot 3: 0.58333 lease + 0.2 stranding_kv; merged there is no move: 0.58333. With mu_kv = 0 both are
    0.58333, as is the LP. Engine replays (FixedPlan, per-slot routing is optimal here) of the unmerged
    optimum on inst and of its mapping on inst_m cost the same values."""
    series = [2.0] * 2000
    series[3] = 0.0
    cfg = toy_config({"time.horizon_min": 30}, sites=[])
    cfg["contracts"] = [{"id": "k", "tau_min": 10, "H_min": 0}]
    cfg["lenders"] = [inline_trace_lender(series, "X", n_layers=2, layer_gpus=1, menu=["k"], prices={"k": 1.0})]
    cfg["borrowers"]["clients"] = [explicit_client([0, 1, 1, 1, 1, 1], "M")]
    inst = build_instance(cfg)
    assert [s.id for s in inst.sites] == ["X/L1-1", "X/L2-2"] and inst.lenders[0].B_gpus == 0.0
    lease = 35 / 60          # GPU-minutes at 1 USD/GPU-h: A 10 prepaid + 5 rent, B 10 prepaid + 10 rent
    for mu_kv in (0.2, 0.0):
        with_stranding(inst, mu_kv_usd=mu_kv, mu_fb_usd=0.0)
        sched = trace_schedule(inst)
        assert [r.tolist() for r in sched.R] == [[3], [3]]
        inst_m, sched_m, smap = merged_relaxation(inst, sched)
        assert [s.id for s in inst_m.sites] == ["X/L1-2"] and smap.tolist() == [0, 0]
        a, b = solve_opt(inst, sched, mip_rel_gap=GAP), solve_opt(inst_m, sched_m, mip_rel_gap=GAP)
        assert a.status == 0 and b.status == 0
        assert abs(a.objective - (lease + mu_kv)) <= 1e-9 and abs(b.objective - lease) <= 1e-9, \
            (mu_kv, a.objective, b.objective)
        assert abs(a.components["stranding_kv"] - mu_kv) <= 1e-9 and abs(b.components["stranding_kv"]) <= 1e-9
        assert abs(a.components["lease"] - b.components["lease"]) <= 1e-9
        for x in (solve_lp(inst, sched), solve_lp(inst_m, sched_m)):
            assert x.status == 0 and abs(x.objective - lease) <= 1e-9, x.objective
        if mu_kv > 0:
            assert sorted(p.start_slot for p in a.plan) == [0, 2] and len({p.site for p in a.plan}) == 2, a.plan
            plan_m = [dataclasses.replace(p, site=int(smap[p.site])) for p in a.plan]
            for ins, plan, want in ((inst, a.plan, lease + mu_kv), (inst_m, plan_m, lease)):
                res = simulate(ins, FixedPlan(plan), LenderModel(), EngineConfig())
                assert res.invariant_failures == [] and not any(e[1] == "refuse" for e in res.events)
                assert abs(res.components["total"] - want) <= 1e-9, (res.components["total"], want)


def test_merged_relaxation_trace_sets():
    """Under the trace schedule only layers with identical sets merge, as the builder's merge does: the
    series of test_layer_sites (R_1 = {0}, R_2 = {0, 1, 2}) keeps its two sites; the series (8, 24, 24, 40,
    40, 40, 40, 40) with v0 = 1 and 4 offered layers (thresholds 16, 24, 32, 40: R = {0}, {0}, {0, 1, 2},
    {0, 1, 2}) merges into L2-3 and L4-5, and equals the instance built with merge_identical_layers true."""
    for series, V, ids in (([8, 16, 16, 24, 32, 40, 40, 48], 2, ["X/L2-2", "X/L3-3", "P"]),
                           ([8, 24, 24, 40, 40, 40, 40, 40], 4, ["X/L2-3", "X/L4-5", "P"])):
        built = {}
        for merge in (False, True):
            cfg = toy_config({"time.horizon_min": 40, "borrowers.clients.0.demand.values": [0, 0, 1, 1, 1, 1, 0, 0],
                              "lender_model.merge_identical_layers": merge}, sites=["P"])
            cfg["lenders"] = [inline_trace_lender(series, "X", n_layers=V, layer_gpus=8, lease_size_quantile=50)] \
                + cfg["lenders"]
            built[merge] = build_instance(cfg)
        inst = built[False]
        assert inst.lenders[0].v0 == 1 and inst.lenders[0].B_gpus == 0.0
        sched = trace_schedule(inst)
        inst_m, sched_m, smap = merged_relaxation(inst, sched)
        _check_site_map(inst, sched, inst_m, sched_m, smap)
        assert [s.id for s in inst_m.sites] == [s.id for s in built[True].sites] == ids
        assert [s.capacity_gpus for s in inst_m.sites] == [s.capacity_gpus for s in built[True].sites]


def test_merged_relaxation_eager_schedule():
    """Under the eager schedule every revocable set is the whole horizon, so all layer sites of a lender
    merge into one site (protected sites stay); the merged OPT_eager LP is at most the unmerged one."""
    inst = build_instance(_relax_config(2))
    sched = Schedule.eager(inst)
    inst_m, sched_m, smap = merged_relaxation(inst, sched)
    _check_site_map(inst, sched, inst_m, sched_m, smap)
    lenders = [lt.lender for lt in inst.lenders if lt.S_full is not None]
    assert [s.lender for s in inst_m.sites if s.kind == "layer"] == lenders
    assert sum(s.kind == "protected" for s in inst_m.sites) == 1
    a, b = solve_lp(inst, sched), solve_lp(inst_m, sched_m)
    assert a.status == 0 and b.status == 0
    _le(b.objective, a.objective, "eager LP")


@pytest.mark.needs_a12
def test_public_view_horizon_and_offset_free():
    """§10 S32: at the default merge setting (off) the public site list of configs/example_1day.json, ids
    and capacities, is the same for horizons of 1, 2 and 7 days and for seeds 1-5 (random offsets)."""
    base = load_json(CONFIGS / "example_1day.json")
    base["lender_model"].pop("merge_identical_layers")
    ref = None
    for days in (1, 2, 7):
        for seed in range(1, 6):
            cfg = dict(base, seed=seed, time=dict(base["time"], horizon_min=1440 * days))
            inst = build_instance(cfg)
            assert inst.config["lender_model"]["merge_identical_layers"] is False
            view = public_view(inst, "I1")
            sites = [(s.id, s.capacity_gpus) for s in view.sites]
            if ref is None:
                ref = sites
                n_layer = sum(s.kind == "layer" for s in inst.sites)
                assert n_layer == sum(lt.n_layers for lt in inst.lenders) and n_layer > 4
                assert all(s.capacity_gpus == 8 for s in inst.sites if s.kind == "layer")
            assert sites == ref, (days, seed)
