"""Tests of the backward-compatible MS1 additions C1-C9 (design/sim_spec_ms2.md §2.4, §3.1; §17.2)."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from fixtures import (CONFIGS, SIM, assert_arrays_close, assert_rel, core_case, explicit_client, load_json,
                      toy_config, toy_instance)

from sublet.config import rng_streams
from sublet.engine import simulate
from sublet.instance import (InstanceError, active_units, build_instance, from_core, restrict_clients,
                             restrict_horizon, units, validate, with_demand)
from sublet.metrics import run_metrics, write_run
from sublet.policies import AlwaysFallback, FixedPlan
from sublet.policies.base import Policy
from sublet.timing import first_dead_fast, latest_prewarm_slot, warm_fast
from sublet.types import LenderModel, PlannedLease, TimeGrid

THEORY = SIM.parents[1] / "code" / "theory_checks"
RUNTIME_KEYS = ("policy_act_s_mean", "policy_act_s_p50", "policy_act_s_p99", "policy_act_s_max",
                "n_alive_leases_max")


# ---------------------------------------------------------------- C1 active_units
def _slot_max(inst) -> np.ndarray:
    g = inst.grid
    return inst.clients.demand.reshape(inst.n, g.T_slow, g.phi).max(axis=2)


def _units_per_slot(inst) -> np.ndarray:
    """(n, T_slow) column sums of units(inst).active per client."""
    ut = units(inst)
    out = np.zeros((inst.n, inst.grid.T_slow), dtype=np.int64)
    np.add.at(out, ut.client, ut.active.astype(np.int64))
    return out


def _active_per_slot(inst) -> np.ndarray:
    D = _slot_max(inst)
    out = np.stack([active_units(D[:, t], inst.units_per_replica) for t in range(inst.grid.T_slow)], axis=1)
    assert out.dtype == np.int64
    return out


def _count(D: float, u: int) -> int:
    """#{i >= 0 : i / u < D} by direct enumeration (float division, strict comparison)."""
    i = 0
    while i / u < D:
        i += 1
    return i


def _random_D(rng, u: int, n: int, T: int, exact: bool) -> np.ndarray:
    """Slot maxima: zeros, uniform values in (0, 3) and (with exact) exact multiples k / u."""
    D = rng.uniform(0.0, 3.0, size=(n, T))
    D[rng.random((n, T)) < 0.2] = 0.0
    if exact:
        mask = rng.random((n, T)) < 0.4
        D[mask] = rng.integers(1, 3 * u + 1, size=int(mask.sum())) / u
    return D


def _toy_with_demand(D: np.ndarray, u: int):
    """A toy instance (Δs = Δf = 5) with one explicit client per row of D (per slow slot) and u units."""
    cfg = toy_config({"units.per_replica": int(u)})
    n, T = D.shape
    cfg["time"]["horizon_min"] = 5 * T
    cfg["lenders"][0]["R"] = [r for r in cfg["lenders"][0]["R"] if r < T]
    cfg["lenders"][1]["R"] = [r for r in cfg["lenders"][1]["R"] if r < T]
    cfg["borrowers"]["clients"] = [explicit_client(D[c].tolist(), borrower=f"b{c}") for c in range(n)]
    return build_instance(cfg)


def test_active_units_matches_units():
    """C1 (M57): active_units per slot equals the column sums of units(inst).active per client on toy.json
    (u = 4), the two MS2 configs (u = 4 and 8), from_core instances (u = 1), and random D for u in
    {1, 2, 4, 8} including exact multiples of 1/u; for u in {3, 10} where |u D - round(u D)| > 1e-9. On
    random D it also equals the direct count #{i >= 0 : i / u < D}."""
    insts = [toy_instance(), build_instance(CONFIGS / "ms2_multi_small.json"),
             build_instance(CONFIGS / "ms2_single_site.json")]
    insts += [from_core(*core_case(seed, 0.2))[0] for seed in range(12)]
    for inst in insts:
        assert np.array_equal(_active_per_slot(inst), _units_per_slot(inst)), inst.name
    assert [i.units_per_replica for i in insts[:3]] == [4, 4, 8] and insts[3].units_per_replica == 1
    rng = np.random.default_rng(57)
    for u in (1, 2, 4, 8, 3, 10):
        for rep in range(3):
            D = _random_D(rng, u, 5, 24, exact=u in (1, 2, 4, 8))
            if u in (3, 10):
                far = np.abs(u * D - np.round(u * D)) > 1e-9
                D = np.where(far | (D == 0), D, D + 0.25 / u)
                assert np.all((np.abs(u * D - np.round(u * D)) > 1e-9) | (D == 0))
            inst = _toy_with_demand(D, u)
            assert np.array_equal(_slot_max(inst), D)
            got = _active_per_slot(inst)
            assert np.array_equal(got, _units_per_slot(inst)), (u, rep)
            want = np.array([[_count(float(x), u) for x in row] for row in D], dtype=np.int64)
            assert np.array_equal(got, want), (u, rep)
    assert np.array_equal(active_units(np.array([0.0, -1.0, 1e-300, 0.25, 0.5, 2.0]), 4),
                          np.array([0, 0, 1, 1, 2, 8]))


# ---------------------------------------------------------------- C2 derived instances
def _toy3(seed: int = 3):
    rng = np.random.default_rng(seed)
    cfg = toy_config()
    cfg["borrowers"]["clients"] = [explicit_client(np.round(rng.uniform(0, 2, 24), 3).tolist(), borrower=f"b{c}")
                                   for c in range(3)]
    return build_instance(cfg)


def _example_1day():
    return build_instance(CONFIGS / "example_1day.json")


@pytest.mark.parametrize("case", ["toy", pytest.param("example_1day", marks=pytest.mark.needs_a12)])
def test_restrict_clients(case):
    """C2: restrict_clients keeps the listed clients in the given order with their Gamma-scaled demand rows,
    delta rows and borrowers, the sites, prices and stranding; borrower_stats restricted to their borrowers;
    config['derived']; the sub-instances validate and the AlwaysFallback costs of a partition sum to the
    full cost (1e-12)."""
    inst = _toy3() if case == "toy" else _example_1day()
    if case == "toy":
        inst.borrower_stats = {f"b{c}": {"llm": 0, "C0_loads": 0.1 * c, "peak_loads": 1.0 + c} for c in range(3)}
    n = inst.n
    assert n >= 2
    parts = [list(range(n - 1, -1, -2)), list(range(n - 2, -1, -2))]
    full = simulate(inst, AlwaysFallback()).components["total"]
    tot = 0.0
    for idx in parts:
        sub = restrict_clients(inst, idx)
        validate(sub)
        assert sub.n == len(idx)
        assert np.array_equal(sub.clients.demand, inst.clients.demand[idx])
        assert np.array_equal(sub.clients.delta_usd_per_h, inst.clients.delta_usd_per_h[idx])
        assert np.array_equal(sub.clients.llm, inst.clients.llm[idx])
        assert sub.clients.borrowers == tuple(inst.clients.borrowers[i] for i in idx)
        assert sub.clients.region == tuple(inst.clients.region[i] for i in idx)
        assert sub.sites is inst.sites or [s.id for s in sub.sites] == [s.id for s in inst.sites]
        assert np.array_equal(sub.price, inst.price) and np.array_equal(sub.lam_s, inst.lam_s)
        assert np.array_equal(sub.stranding.mu_fb_usd, inst.stranding.mu_fb_usd)
        keep = {b for i in idx for b in inst.clients.borrowers[i]}
        assert sub.borrower_stats == {b: v for b, v in inst.borrower_stats.items() if b in keep}
        assert sub.config["derived"]["restrict_clients"] == idx
        tot += simulate(sub, AlwaysFallback()).components["total"]
    assert_rel(tot, full, 1e-12, "partition of AlwaysFallback costs")
    for bad in ([], [0, 0], [n]):
        with pytest.raises(InstanceError):
            restrict_clients(inst, bad)


def test_with_demand():
    """C2: with_demand replaces clients.demand (n, T_fast) and nothing else; the AlwaysFallback cost equals
    the cost on the instance built with that demand; a wrong shape or a negative value raises."""
    inst = _toy3()
    rng = np.random.default_rng(4)
    d = np.round(rng.uniform(0, 1.5, inst.clients.demand.shape), 3)
    wd = with_demand(inst, d)
    validate(wd)
    assert np.array_equal(wd.clients.demand, d) and wd.clients.demand is not d
    assert np.array_equal(inst.clients.demand, _toy3().clients.demand)        # the original is unchanged
    assert np.array_equal(wd.clients.delta_usd_per_h, inst.clients.delta_usd_per_h)
    assert wd.grid == inst.grid and [s.id for s in wd.sites] == [s.id for s in inst.sites]
    cfg = toy_config()
    cfg["borrowers"]["clients"] = [explicit_client(d[c].tolist(), borrower=f"b{c}") for c in range(3)]
    direct = build_instance(cfg)
    assert_rel(simulate(wd, AlwaysFallback()).components["total"],
               simulate(direct, AlwaysFallback()).components["total"], 1e-12, "with_demand")
    with pytest.raises(InstanceError):
        with_demand(inst, d[:, :-1])
    bad = d.copy()
    bad[0, 0] = -1.0
    with pytest.raises(InstanceError):
        with_demand(inst, bad)


def _slice_core(I, om, t0: int, T: int):
    I2 = copy.deepcopy(I)
    I2.T = T
    I2.active = I.active[:, t0:t0 + T].copy()
    om2 = [np.asarray(o, dtype=np.int64)[(np.asarray(o) >= t0) & (np.asarray(o) < t0 + T)] - t0 for o in om]
    return I2, om2


@pytest.mark.parametrize("case", ["from_core", pytest.param("example_1day", marks=pytest.mark.needs_a12)])
def test_restrict_horizon(case):
    """C2: restrict_horizon(from_core(I, omega), t0, T) equals from_core of the sliced core instance and sets
    (demand, R, contracts, prices, clients; engine runs identical); start_mow is advanced by t0 * slow_min
    (from_core sets 0, so the two differ there by the rule of §3.1); t0 * slow_min not a multiple of 5 raises.
    On example_1day (trace lenders) owed_series, S and S_lend of the restricted instance equal the slices."""
    if case == "example_1day":
        from sublet.lender import build_R, owed_series
        inst = _example_1day()
        t0, T = 96, 120
        sub = restrict_horizon(inst, t0, T)
        validate(sub)
        assert sub.grid.T_slow == T and sub.grid.start_mow == (inst.grid.start_mow + t0 * 5) % 10080
        assert np.array_equal(sub.clients.demand, inst.clients.demand[:, t0 * 5:(t0 + T) * 5])
        n_trace = 0
        for li, (a, b) in enumerate(zip(inst.lenders, sub.lenders)):
            assert np.array_equal(owed_series(inst, li)[t0:t0 + T], owed_series(sub, li)), a.lender
            if a.S is not None:
                n_trace += 1
                assert np.array_equal(a.S[t0:t0 + T], b.S) and np.array_equal(a.S_lend[t0:t0 + T], b.S_lend)
        assert n_trace >= 1
        R_full = build_R(inst, LenderModel(), np.random.default_rng(0))
        R_sub = build_R(sub, LenderModel(), np.random.default_rng(0))
        for a, b in zip(R_full, R_sub):
            assert np.array_equal(a[(a >= t0) & (a < t0 + T)] - t0, b)
        return
    for seed in range(6):
        for rate in (0.3, 1.0):
            I, om = core_case(seed, rate)
            inst, _ = from_core(I, om)
            t0, T = 3 + seed % 2, I.T - 7
            sub = restrict_horizon(inst, t0, T)
            validate(sub)
            ref, ref_sched = from_core(*_slice_core(I, om, t0, T))
            assert (sub.grid.slow_min, sub.grid.fast_min, sub.grid.T_slow) == \
                   (ref.grid.slow_min, ref.grid.fast_min, ref.grid.T_slow)
            assert sub.grid.start_mow == (inst.grid.start_mow + t0 * inst.grid.slow_min) % 10080
            assert ref.grid.start_mow == 0
            assert sub.contracts == ref.contracts and sub.llms == ref.llms
            for a, b in zip(sub.sites, ref.sites):
                assert (a.id, a.kind, a.menu, a.capacity_gpus) == (b.id, b.kind, b.menu, b.capacity_gpus)
                assert np.array_equal(a.R_explicit, b.R_explicit)
            assert all(np.array_equal(a.R_explicit, r) for a, r in zip(sub.sites, ref_sched.R))
            for name in ("price", "lam_s", "beta_usd"):
                assert np.array_equal(getattr(sub, name), getattr(ref, name)), name
            for name in ("llm", "delta_usd_per_h", "demand"):
                assert np.array_equal(getattr(sub.clients, name), getattr(ref.clients, name)), name
            assert sub.clients.borrowers == ref.clients.borrowers
            plan = [PlannedLease(0, 1 % I.K, 0, 2), PlannedLease(I.m - 1, 0, int(I.cl_llm[0]), 0, 5)]
            for pol in (lambda: AlwaysFallback(), lambda: FixedPlan(plan)):
                a, b = simulate(sub, pol()), simulate(ref, pol())
                assert a.components == b.components, (seed, rate)
                assert all(np.array_equal(a.per_slot[k], b.per_slot[k]) for k in a.per_slot)
    I, om = core_case(1, 0.3)
    fi1, _ = from_core(I, om, slot_min=1)
    with pytest.raises(InstanceError):
        restrict_horizon(fi1, 3, 5)
    restrict_horizon(fi1, 5, 5)
    with pytest.raises(InstanceError):
        restrict_horizon(fi1, 0, fi1.grid.T_slow + 1)


# ---------------------------------------------------------------- C3, C4 (series and regional demand)
def _series_config(merge):
    from sublet.traces import borrowers as tb
    az = [s for s in tb.series_names() if s.startswith("azure")][:2]
    assert len(az) == 2, tb.series_names()
    cfg = load_json(CONFIGS / "example_1day.json")
    cfg["name"] = "series_merge"
    cfg["seed"] = 1
    cfg["borrowers"] = {"model": "series", "list": [
        {"id": "bA", "series": az[0], "region": "north_america", "slo_class": "strict"},
        {"id": "bB", "series": az[1], "region": "north_america", "slo_class": "strict"},
        {"id": "bC", "series": az[0], "week_index": 0, "region": "europe", "slo_class": "relaxed"}]}
    if merge is not None:
        cfg["borrowers"]["merge"] = merge
    return cfg


@pytest.mark.needs_a12
def test_borrowers_merge_false():
    """C3: two series borrowers with the same (tier, region, SLO): merge = true (the default) gives one
    client for both, false two, whose demands sum to the merged one (1e-12); the same Gamma (borrower_stats
    carry the Gamma factor and are equal; the builder notes print the same Gamma)."""
    merged = build_instance(_series_config(None))
    split = build_instance(_series_config(False))
    assert merged.config["borrowers"]["merge"] is True and split.config["borrowers"]["merge"] is False
    assert merged.n == 2 and split.n == 3
    iAB = merged.clients.borrowers.index(("bA", "bB"))
    iA, iB = split.clients.borrowers.index(("bA",)), split.clients.borrowers.index(("bB",))
    assert_arrays_close(split.clients.demand[iA] + split.clients.demand[iB], merged.clients.demand[iAB], 1e-12,
                        "summed split demand")
    iC, jC = merged.clients.borrowers.index(("bC",)), split.clients.borrowers.index(("bC",))
    assert np.array_equal(merged.clients.demand[iC], split.clients.demand[jC])
    assert set(merged.borrower_stats) == set(split.borrower_stats) == {"bA", "bB", "bC"}
    for b, st in split.borrower_stats.items():
        for k in ("C0_loads", "peak_loads"):
            assert_rel(merged.borrower_stats[b][k], st[k], 1e-12, f"{b} {k}")
    gam = [[n for n in x.notes if "Gamma" in n] for x in (merged, split)]
    assert len(gam[0]) == 1 and gam[0] == gam[1], gam


def _trailing(x_ext: np.ndarray, w: int) -> np.ndarray:
    """Mean over the last w minutes (x_ext has w - 1 lead-in minutes)."""
    return np.lib.stride_tricks.sliding_window_view(x_ext, w).mean(axis=1)


@pytest.mark.needs_a12
@pytest.mark.parametrize("model", ["series", "regional"])
def test_borrower_stats(model):
    """C4: borrower_stats per borrower id: 'llm', and C0_loads = Gamma C0 / kappa_j and peak_loads = Gamma
    max x^sm / kappa_j recomputed from the smoothed series (series model: trailing mean of the weighted
    tokens, C0 at the own-capacity quantile, Gamma = tightness x supply / peak of the summed GPU overflow);
    on both models, with Δf = 1, max_f d_c(f) = peak_loads - C0_loads for a one-borrower client whose
    overflow is positive (the builder's demand is Gamma (x^sm - C0)^+ / kappa per minute); peak >= C0."""
    if model == "series":
        cfg = _series_config(False)
    else:
        cfg = load_json(CONFIGS / "example_1day.json")
    inst = build_instance(cfg)
    assert inst.grid.fast_min == 1
    st = inst.borrower_stats
    assert st and all(set(v) == {"llm", "C0_loads", "peak_loads"} for v in st.values())
    for b, v in st.items():
        assert v["peak_loads"] >= v["C0_loads"] >= 0, (b, v)
    checked = 0
    for c, bor in enumerate(inst.clients.borrowers):
        if len(bor) != 1:
            continue
        v = st[bor[0]]
        assert v["llm"] == int(inst.clients.llm[c])
        dmax = float(inst.clients.demand[c].max())
        assert dmax > 0
        assert_rel(dmax, v["peak_loads"] - v["C0_loads"], 1e-9 * max(1.0, v["peak_loads"]), f"client {c} {bor}")
        checked += 1
    assert checked >= 1
    if model != "series":
        return
    from sublet.traces import borrowers as tb
    b = inst.config["borrowers"]
    sm, q, tight = b["smoothing_min"], b["own_capacity_quantile"], b["market_tightness"]
    T_min = inst.grid.horizon_min
    i = np.arange(-(sm - 1), T_min, dtype=np.int64)
    supply = float(sum(s.capacity_gpus for s in inst.sites if s.kind == "layer"))
    by_tier = {x.tier: j for j, x in enumerate(inst.llms)}
    own, tot = {}, np.zeros(T_min)
    for x in b["list"]:
        j = by_tier[x["tier"]]
        L = inst.llms[j]
        w = tb.weighted(tb.load_series(x["series"]), L.w_in)
        start = (x["week_index"] or 0) * 10080
        xs = _trailing(w[(start + i) % len(w)], sm)
        assert xs.shape == (T_min,)
        C0 = float(np.percentile(xs, q))
        own[x["id"]] = (j, C0, float(xs.max()))
        tot += L.g * np.maximum(xs - C0, 0.0) / L.kappa_wtok_per_min
    gam = tight * supply / float(tot.max())
    for bid, (j, C0, peak) in own.items():
        kap = inst.llms[j].kappa_wtok_per_min
        assert st[bid]["llm"] == j
        assert_rel(st[bid]["C0_loads"], gam * C0 / kap, 1e-12, f"{bid} C0_loads")
        assert_rel(st[bid]["peak_loads"], gam * peak / kap, 1e-12, f"{bid} peak_loads")


# ---------------------------------------------------------------- C5 seeds, C6/C7 report and runtime
class _Grab(Policy):
    """Keeps the generator it gets and draws from it; reports a fixed dict."""
    name = "grab"

    def reset(self, view, rng):
        super().reset(view, rng)
        self.rng_seen = rng
        self.draws = rng.random(3)

    def act(self, obs):
        return []

    def report(self):
        return {"n": 3, "arr": [0, 1, 2], "label": "grab"}


def _family_instance():
    import fam
    F = fam.Fam(4, 8, 2, 1, 48)
    return from_core(F.core_instance(), [np.zeros(0, np.int64)] * 4)[0]


def test_simulate_seeds():
    """C5: under safe_site, policy seeds 0 and 1 with one lender seed give the same realized R (another
    lender seed another R); the policy generator is rng_streams(policy_seed)['policy']; policy_rng is
    passed unchanged; RunResult.seeds = {'config', 'lender', 'policy'} ('injected' for policy_rng); without
    the new keywords the MS1 behavior (one seed for both) is kept."""
    inst = _family_instance()
    model = LenderModel(schedule="safe_site")
    p0, p1 = _Grab(), _Grab()
    r0 = simulate(inst, p0, model, lender_seed=11, policy_seed=0)
    r1 = simulate(inst, p1, model, lender_seed=11, policy_seed=1)
    r2 = simulate(inst, _Grab(), model, lender_seed=12, policy_seed=0)
    assert all(np.array_equal(a, b) for a, b in zip(r0.schedule.R, r1.schedule.R))
    assert any(not np.array_equal(a, b) for a, b in zip(r0.schedule.R, r2.schedule.R))
    assert r0.seeds == {"config": inst.seed, "lender": 11, "policy": 0}
    assert r1.seeds == {"config": inst.seed, "lender": 11, "policy": 1}
    assert np.array_equal(p0.draws, rng_streams(0)["policy"].random(3))
    assert np.array_equal(p1.draws, rng_streams(1)["policy"].random(3))
    g = np.random.default_rng(5)
    pg = _Grab()
    rg = simulate(inst, pg, model, lender_seed=11, policy_rng=g)
    assert pg.rng_seen is g and rg.seeds == {"config": inst.seed, "lender": 11, "policy": "injected"}
    assert np.array_equal(pg.draws, np.random.default_rng(5).random(3))
    assert all(np.array_equal(a, b) for a, b in zip(r0.schedule.R, rg.schedule.R))
    toy = toy_instance()
    pm = _Grab()
    rm = simulate(toy, pm)
    assert rm.seeds == {"config": 7, "lender": 7, "policy": 7}
    assert np.array_equal(pm.draws, rng_streams(7)["policy"].random(3))
    rs = simulate(toy, _Grab(), seed=9)
    assert rs.seeds == {"config": 7, "lender": 9, "policy": 9}


def test_policy_report_and_runtime(tmp_path):
    """C6, C7: metrics['policy'] = report() ({} for an MS1 policy); run_metrics copies it; write_run with
    extra_meta writes the keys into meta; the runtime keys policy_act_s_* and n_alive_leases_max exist
    (n_alive_leases_max = 2 for two overlapping leases)."""
    inst = _family_instance()
    res = simulate(inst, _Grab(), policy_rng=np.random.default_rng(1))
    assert res.metrics["policy"] == _Grab().report()
    assert run_metrics(res, inst)["policy"] == _Grab().report()
    for k in RUNTIME_KEYS:
        assert k in res.runtime, k
    assert res.runtime["policy_act_s_mean"] >= 0 and res.runtime["policy_act_s_max"] >= res.runtime["policy_act_s_p50"]
    extra = {"run_spec_hash": "abc", "policy_id": "X", "params": {"a": 1}, "seeds": res.seeds,
             "info_class": "online-I1"}
    path = tmp_path / "run.json"
    write_run(res, inst, path, extra_meta=extra)
    js = json.loads(path.read_text())
    for k, v in extra.items():
        assert js["meta"][k] == v, k
    assert js["metrics"]["policy"] == _Grab().report()
    toy = toy_instance()
    fp = simulate(toy, FixedPlan([PlannedLease(0, 1, 0, 1), PlannedLease(1, 0, 0, 2, 5)]))
    assert fp.metrics["policy"] == {}
    assert fp.runtime["n_alive_leases_max"] == 2
    assert simulate(toy, AlwaysFallback()).runtime["n_alive_leases_max"] == 0


# ---------------------------------------------------------------- C8 timing
def test_timing_helpers():
    """C8: warm_fast gives MS1's test_warm_time_hand values (λ = 420 s bought at minute 5: fast slot 3 at
    Δf = 5, 12 at Δf = 1); latest_prewarm_slot by hand at Δs = 5, Δf = 1, r = 6, E = 35: slot 6 for
    λ = 60 s and 300 s, None for 301 s; trap T1 at Δf = 5, H = 2 (E = 32): slot 6 for λ = 0, None for λ > 0."""
    assert warm_fast(5, 420_000, 5) == 3 and warm_fast(5, 420_000, 1) == 12
    assert warm_fast(30, 0, 5) == 6 and warm_fast(30, 1, 5) == 7 and warm_fast(30, 60_000, 1) == 31
    assert first_dead_fast(35, 1) == 35 and first_dead_fast(32, 5) == 6 and first_dead_fast(30, 5) == 6
    g1 = TimeGrid(5, 1, 12)
    assert latest_prewarm_slot(6, 35, 60_000, g1) == 6
    assert latest_prewarm_slot(6, 35, 300_000, g1) == 6
    assert latest_prewarm_slot(6, 35, 301_000, g1) is None
    assert latest_prewarm_slot(6, 40, 301_000, g1) == 6
    assert latest_prewarm_slot(6, 42, 301_000, g1) == 7
    g5 = TimeGrid(5, 5, 12)
    assert latest_prewarm_slot(6, 32, 0, g5) == 6
    assert latest_prewarm_slot(6, 32, 1, g5) is None
    assert latest_prewarm_slot(6, 32, 120_000, g5) is None
    # by definition: the latest t in [r, E // Δs] with warm_fast(t Δs) <= first_dead_fast(E)
    for lam in (0, 1, 59_999, 60_000, 299_999, 300_000, 301_000, 900_000):
        for E in range(30, 61):
            for g in (g1, g5):
                ts = [t for t in range(6, E // 5 + 1)
                      if warm_fast(t * 5, lam, g.fast_min) <= first_dead_fast(E, g.fast_min)]
                assert latest_prewarm_slot(6, E, lam, g) == (max(ts) if ts else None), (lam, E, g)


# ---------------------------------------------------------------- C9 importers
def _pyc_snapshot() -> dict:
    return {str(p): p.stat().st_mtime_ns for p in THEORY.rglob("*.pyc")}


def test_import_ref():
    """C9: import_c2 returns model, families and model_switch_cost; import_ref returns each allowed
    reference module from its folder and refuses the others; the set of *.pyc files under
    code/theory_checks/ and their mtimes are the same before and after the imports, also in a fresh
    interpreter that allows bytecode writing (paths switches it off around every reference import)."""
    from sublet import paths
    ns = paths.import_c2()
    assert hasattr(ns.model, "Params") and hasattr(ns.model, "opt_cost") and hasattr(ns.model, "INF")
    assert hasattr(ns.families, "lb_react") and hasattr(ns.model_switch_cost, "opt_cost_bw")
    assert Path(ns.model.__file__).resolve().parent == paths.C2.resolve()
    assert Path(ns.families.__file__).resolve().parent == paths.C2.resolve()
    assert Path(ns.model_switch_cost.__file__).resolve().parent == (paths.C2 / "audit").resolve()
    names = ("core", "pd", "fam", "o1_ub", "check_c4_lower", "check_c3_upper", "check_c3_benchmark", "check_c5_la")
    assert set(paths.REF_MODULES) == set(names)
    for nm in names:
        mod = paths.import_ref(nm)
        assert Path(mod.__file__).stem == nm
        assert Path(mod.__file__).resolve().parent == (paths.O1 if nm in ("fam", "o1_ub") else paths.C3).resolve()
    for bad in ("alg_check_targeted", "a2_P_equiv_and_termination", "recheck_c2", "switch_cost_crossover", "os"):
        with pytest.raises(ValueError):
            paths.import_ref(bad)
    before = _pyc_snapshot()
    code = ("import sys; sys.dont_write_bytecode = True; sys.path.insert(0, %r)\n"
            "from sublet import paths\n"
            "sys.dont_write_bytecode = False\n"
            "ns = paths.import_c2()\n"
            "mods = [paths.import_ref(n) for n in sorted(paths.REF_MODULES)]\n"
            "assert sys.dont_write_bytecode is False\n"
            "print(len(mods), ns.model.__name__)\n") % str(SIM)
    env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
    env["OMP_NUM_THREADS"] = "1"
    out = subprocess.run([sys.executable, "-c", code], cwd=str(SIM), env=env, capture_output=True, text=True,
                         timeout=300)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == [str(len(names)), "model"]
    assert _pyc_snapshot() == before
