"""Tests of sublet/instance.py (design/sim_spec.md §3.4.4, §4.3, §6.1-§6.2; §9.2)."""
import dataclasses

import numpy as np
import pytest

import core

from fixtures import (A0, Q_GPU, CONFIGS, assert_arrays_close, core_omega, core_params, explicit_client,
                      explicit_llm, inline_trace_lender, toy_config, toy_instance, trace_schedule, with_capacity)

from sublet import reclaim
from sublet.instance import InstanceError, build_instance, from_core, public_view, to_core, units, validate
from sublet.types import INF, TimeGrid

TOY_DEMAND = [0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0]
CORE_FIELDS_INT = ("T", "tau", "H", "g", "cl_llm", "active")
CORE_FIELDS_FLOAT = ("a", "beta", "q", "delta")


def test_toy_builds():
    inst = toy_instance()
    validate(inst)
    assert inst.name == "toy" and inst.seed == 7
    assert inst.grid == TimeGrid(5, 5, 24, 0)
    assert inst.regions == ("r0",)
    assert (inst.m, inst.J, inst.K, inst.n) == (3, 1, 3, 1)
    assert [c.id for c in inst.contracts] == ["short", "long", "prot"]
    assert [c.tau_slots for c in inst.contracts] == [1, 2, None]
    assert [c.H_min for c in inst.contracts] == [5, 10, 0]
    assert [c.prepaid_min for c in inst.contracts] == [10, 20, 5]      # prepaid_D: P = D; protected own
    assert [s.lender for s in inst.sites] == ["L0", "L1", "P"]
    assert [s.kind for s in inst.sites] == ["synthetic", "synthetic", "protected"]
    assert [s.group for s in inst.sites] == ["g0", "g1", "gp"]
    assert [s.region for s in inst.sites] == ["r0"] * 3
    assert [s.capacity_gpus for s in inst.sites] == [4, 4, INF]
    assert [tuple(s.menu) for s in inst.sites] == [(0, 1), (0, 1), (2,)]
    assert np.array_equal(inst.sites[0].R_explicit, [6, 7, 8, 15, 16])
    assert np.array_equal(inst.sites[1].R_explicit, [10, 11])
    assert inst.sites[0].R_explicit.dtype == np.int64
    assert inst.price.shape == (3, 3)
    assert_arrays_close(inst.price, [[2.85, 3.0, INF], [2.9, 3.1, INF], [INF, INF, 5.97]], 0.0, "price")
    assert inst.lam_s.shape == (1, 3) and np.array_equal(inst.lam_s, [[300.0, 300.0, 600.0]])
    assert inst.beta_usd.shape == (1, 3) and np.all(inst.beta_usd == 0.0)
    assert np.array_equal(inst.lam_ms(), [[300000, 300000, 600000]])
    assert inst.load_scenario == ("explicit",) * 3
    llm = inst.llms[0]
    assert (llm.g, llm.tier, llm.w_in, llm.T_dr_s) == (1, "M", 0.3048, 28.49)
    assert llm.kappa_wtok_per_min == 219428.5714 and llm.q_usd_per_h == Q_GPU
    cl = inst.clients
    assert np.array_equal(cl.llm, [0]) and cl.region == ("r0",) and cl.slo_class == ("strict",)
    assert cl.borrowers == (("b0",),)
    assert cl.delta_usd_per_h.shape == (1, 3) and np.all(cl.delta_usd_per_h == 0.0)
    assert cl.demand.shape == (1, 24) and cl.demand.dtype == np.float64
    assert np.array_equal(cl.demand[0], TOY_DEMAND)
    assert inst.units_per_replica == 4 and inst.phi_load == 1.0
    assert inst.q_gpu_usd_per_h == Q_GPU and inst.a0_usd_per_gpu_h == A0
    assert inst.kappa_infinite is False and inst.billing == "prepaid_D"
    # stranding (§4.3 step 9): mu_fb = r_mu * beta~ref, beta~ref = lambda_ref (g a0 + phi g q_GPU) / 3600
    bt_ref = 300.0 * (A0 + Q_GPU) / 3600.0
    st = inst.stranding
    assert abs(st.mu_fb_usd[0] - bt_ref) <= 1e-12
    assert st.mu_kv_usd[0] == 0.0 and st.mu_fl_usd[0] == 0.0 and st.pi_usd_per_min[0] == 0.0
    assert st.W_f_min == 0.0
    assert [L.kind for L in inst.lenders] == ["synthetic", "synthetic", "protected"]
    assert [tuple(L.site_index) for L in inst.lenders] == [(0,), (1,), (2,)]
    bt = inst.beta_tilde_usd()
    assert bt.shape == (1, 3, 3) and np.isinf(bt[0, 0, 2]) and np.isinf(bt[0, 2, 0])
    assert abs(bt[0, 0, 0] - 300.0 / 3600.0 * (2.85 + Q_GPU)) <= 1e-12


def test_units_rule():
    """u = 4, demand (0.3, 0.6, 1.0, 0) in four slow slots: V_c = 4 and the activity rows of §9.2."""
    want = np.array([[1, 1, 1, 0], [1, 1, 1, 0], [0, 1, 1, 0], [0, 0, 1, 0]], dtype=bool)
    inst = toy_instance({"time.horizon_min": 20, "borrowers.clients.0.demand.values": [0.3, 0.6, 1.0, 0.0],
                         "lenders.0.R": [1], "lenders.1.R": [2]})
    U = units(inst)
    assert np.array_equal(U.client, [0, 0, 0, 0]) and np.array_equal(U.v, [1, 2, 3, 4])
    assert U.client.dtype == np.int64 and U.v.dtype == np.int64
    assert U.active.shape == (4, 4) and U.active.dtype == bool
    assert np.array_equal(U.active, want)
    # 1-min fast slots: the slot maximum counts (the values sit in one minute of each slow slot)
    vals = np.zeros(20)
    vals[[2, 5, 11]] = [0.3, 0.6, 1.0]           # minutes in slow slots 0, 1 and 2
    inst = toy_instance({"time.horizon_min": 20, "time.fast_slot_min": 1,
                         "borrowers.clients.0.demand.values": list(vals), "lenders.0.R": [1], "lenders.1.R": [2]})
    U = units(inst)
    assert np.array_equal(U.v, [1, 2, 3, 4]) and np.array_equal(U.active, want)
    # a client without demand still has one (never active) unit
    inst = toy_instance({"time.horizon_min": 20, "borrowers.clients.0.demand.values": [0.0] * 4,
                         "lenders.0.R": [1], "lenders.1.R": [2]})
    U = units(inst)
    assert np.array_equal(U.v, [1]) and not U.active.any()


def _roundtrip(I, om):
    inst, sched = from_core(I, om)
    validate(inst)
    T = I.T
    assert inst.grid == TimeGrid(60, 60, T, 0) and inst.regions == ("r0",)
    assert inst.kappa_infinite is True and inst.billing == "prepaid_D" and inst.units_per_replica == 1
    assert inst.phi_load == 0.0 and np.all(inst.lam_s == 0.0)
    assert [s.kind for s in inst.sites] == ["synthetic"] * I.m
    assert [s.id for s in inst.sites] == [f"L{l}" for l in range(I.m)]
    assert [c.id for c in inst.contracts] == [f"k{k}" for k in range(I.K)]
    assert [c.tau_slots for c in inst.contracts] == [int(x) for x in I.tau]
    assert [c.H_min for c in inst.contracts] == [int(x) * 60 for x in I.H]
    assert [c.prepaid_min for c in inst.contracts] == [int(t + h) * 60 for t, h in zip(I.tau, I.H)]
    assert all(np.isinf(s.capacity_gpus) for s in inst.sites)
    assert np.array_equal(inst.clients.demand, I.active.astype(float))
    want_b = (("b0",),) * I.n if I.owner is None else tuple((str(o),) for o in I.owner)
    assert inst.clients.borrowers == want_b
    assert sched.mode == "trace" and len(sched.R) == I.m
    for l in range(I.m):
        want = np.unique(np.asarray(om[l], dtype=np.int64))
        want = want[want < T]
        assert np.array_equal(inst.sites[l].R_explicit, want) and np.array_equal(sched.R[l], want)
    st = inst.stranding
    assert not (st.mu_kv_usd.any() or st.mu_fl_usd.any() or st.mu_fb_usd.any() or st.pi_usd_per_min.any())
    ex = to_core(inst, sched)
    assert ex.exact is True
    C = ex.core
    for f in CORE_FIELDS_INT:
        x, y = np.asarray(getattr(C, f)), np.asarray(getattr(I, f))
        assert x.shape == y.shape and np.array_equal(x, y), f
    for f in CORE_FIELDS_FLOAT:
        assert_arrays_close(getattr(C, f), getattr(I, f), 1e-12, f)
    if I.owner is None:
        assert C.owner is None
    else:
        assert np.array_equal(np.asarray(C.owner), I.owner) and np.asarray(C.owner).dtype.kind == "i"
    assert len(ex.omega) == I.m
    for l in range(I.m):
        want = np.asarray(om[l], dtype=np.int64)
        assert np.array_equal(ex.omega[l], want[want < T])
    assert np.array_equal(ex.unit_map.client, np.arange(I.n)) and np.array_equal(ex.unit_map.v, np.ones(I.n))
    return inst


def test_from_core_to_core_roundtrip():
    n = 0
    for seed in range(10):
        for rate in (0.0, 0.1, 1.0):
            I = core.random_instance(np.random.default_rng(seed), **core_params(seed))
            _roundtrip(I, core_omega(I, rate, seed))
            n += 1
    for seed in range(10):                                   # random_instance's default parameters
        for rate in (0.0, 0.1, 1.0):
            I = core.random_instance(np.random.default_rng(seed))
            _roundtrip(I, core_omega(I, rate, seed))
            n += 1
    for seed in range(5):
        for rate in (0.0, 0.1, 1.0):
            I = core.random_instance(np.random.default_rng(seed), **core_params(seed), n_borrowers=3)
            assert I.owner is not None
            _roundtrip(I, core_omega(I, rate, seed))
            n += 1
    assert n == 75
    I0 = core.random_instance(np.random.default_rng(0), T=12, m=2, J=1, n=3,
                              contracts=[(0, 1, 1.0), (2, 1, 1.25)])
    with pytest.raises(InstanceError):
        from_core(I0, [np.zeros(0, dtype=np.int64)] * 2)


def _exact_config(prepaid_prot: int) -> dict:
    """An instance meeting every exactness condition of to_core except, possibly, the protected billed term."""
    cfg = toy_config(sites=["L0", "L1"])
    cfg["contracts"] = [{"id": "r", "tau_min": 5, "H_min": 5},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": int(prepaid_prot)}]
    for L, R in zip(cfg["lenders"], ([6, 7], [10])):
        L.update({"menu": ["r", "prot"], "prices": {"r": 2.85, "prot": 5.97}, "lam_s": 0.0, "R": R})
    cfg["llms"][0]["kappa_wtok_per_min"] = "inf"
    cfg["costs"]["kappa_infinite"] = True
    cfg["units"]["per_replica"] = 1
    cfg["stranding"]["mu_over_beta_tilde"] = 0.0
    return cfg


def test_to_core_exact_flag():
    inst = toy_instance()
    ex = to_core(inst, trace_schedule(inst), not_offered="big_m")
    assert ex.exact is False and len(ex.notes) > 0 and ex.big_m_price is not None
    I = core.random_instance(np.random.default_rng(3), **core_params(3))
    om = core_omega(I, 0.1, 3)
    fi, fs = from_core(I, om)
    assert to_core(fi, fs).exact is True
    for prepaid, exact in ((120, True), (125, False)):
        inst = with_capacity(build_instance(_exact_config(prepaid)), {0: INF, 1: INF})
        validate(inst)
        assert inst.grid.horizon_min == 120
        assert to_core(inst, trace_schedule(inst)).exact is exact, prepaid


def test_to_core_raises():
    inst = toy_instance()
    with pytest.raises(InstanceError):
        to_core(inst, trace_schedule(inst))                      # non-offered pairs, not_offered='raise'
    cfg = toy_config()
    cfg["llms"] = [explicit_llm("M", 1), explicit_llm("M2", 2)]
    cfg["borrowers"]["clients"] = [explicit_client(TOY_DEMAND, "M"), explicit_client(TOY_DEMAND, "M2", borrower="b1")]
    inst2 = build_instance(cfg)
    assert [x.g for x in inst2.llms] == [1, 2]
    with pytest.raises(InstanceError):
        to_core(inst2, trace_schedule(inst2), not_offered="big_m")   # per-unit q differs across LLMs


def test_layer_sites():
    """Inline non-decreasing series (8, 16, 16, 24, 32, 40, 40, 48), buffer 0, layer_gpus 8, n_layers 2,
    lease_size_quantile 50, offset 0, horizon 8 slots: Q50 = 28, v_top = 3, v0 = 1, R_1 = {0},
    R_2 = {0, 1, 2}: sites X/L2-2 and X/L3-3 of 8 GPUs. A lender whose menu has only b >= 1 gets no site."""
    series = [8, 16, 16, 24, 32, 40, 40, 48]
    cfg = toy_config({"time.horizon_min": 40, "borrowers.clients.0.demand.values": [0, 0, 1, 1, 1, 1, 0, 0]},
                     sites=["P"])
    cfg["lenders"] = [inline_trace_lender(series, "X", n_layers=2, layer_gpus=8, lease_size_quantile=50),
                      inline_trace_lender([100, 0] * 4, "Y")] + cfg["lenders"]
    inst = build_instance(cfg)
    validate(inst)
    ids = [s.id for s in inst.sites]
    assert ids == ["X/L2-2", "X/L3-3", "P"], ids
    assert not any(s.lender == "Y" for s in inst.sites)
    assert any("Y" in note for note in inst.notes), inst.notes
    s1, s2 = inst.sites[0], inst.sites[1]
    assert s1.kind == s2.kind == "layer" and s1.capacity_gpus == s2.capacity_gpus == 8
    assert (s1.layer_lo, s1.layer_hi, s1.local_layer_lo) == (2, 2, 1)
    assert (s2.layer_lo, s2.layer_hi, s2.local_layer_lo) == (3, 3, 2)
    assert s1.group == "X" and s1.region == "r0" and tuple(s1.menu) == (0,)
    LX = next(L for L in inst.lenders if L.lender == "X")
    assert LX.B_gpus == 0.0 and LX.v0 == 1 and LX.n_layers == 2 and LX.layer_gpus == 8
    assert LX.D_max_lender_min == 10 and LX.offset_5min == 0 and tuple(LX.site_index) == (0, 1)
    assert np.array_equal(LX.S, series) and np.array_equal(LX.S_lend, series)
    assert np.array_equal(reclaim.layer_R(LX.S_lend, 16), [0])
    assert np.array_equal(reclaim.layer_R(LX.S_lend, 24), [0, 1, 2])
    sched = trace_schedule(inst)
    assert np.array_equal(sched.R[0], [0]) and np.array_equal(sched.R[1], [0, 1, 2]) and len(sched.R[2]) == 0


def test_long_window_contract_dropped():
    """§10 S35, hand case. Inline lender: 20 periods of the ramp 200, 190, ..., 80 GPUs (mean 140), menu
    's' (D = 5 min) and 'lng' (D = 60 min), layer_gpus 8, n_layers 2. 1-slot drops are 10 (0 at the jump),
    so b(5) = 10/140 and B(5) = 10; 12-slot drops are 120 - 10 i, so b(60) = 120/140 < 1 (offered) and
    B(60) = 120. At D_max 60: S_lend = (S - 120)^+ is 0 in 5 of 13 slots, Q25 = 0, v_top = 0, so 'lng' is
    dropped; at D_max 5: S_lend = S - 10 in {70, ..., 190}, Q25 = 100, v_top = 12, v0 = 10, two sites
    offering 's' only. Before §10 S35 this lender got no site."""
    series = [200.0 - 10 * i for i in range(13)] * 20
    cfg = toy_config({"time.horizon_min": 40, "borrowers.clients.0.demand.values": [0, 0, 1, 1, 1, 1, 0, 0]},
                     sites=["P"])
    cfg["contracts"] = [{"id": "s", "tau_min": 5, "H_min": 0}, {"id": "lng", "tau_min": 5, "H_min": 55},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": 5}]
    cfg["lenders"][0]["menu"] = ["prot"]
    cfg["lenders"] = [inline_trace_lender(series, "X", menu=["s", "lng"], prices={"s": 2.85, "lng": 3.0},
                                          n_layers=2, layer_gpus=8)] + cfg["lenders"]
    inst = build_instance(cfg)
    LX = inst.lenders[0]
    assert LX.lender == "X" and LX.D_max_lender_min == 5
    assert abs(LX.B_gpus - 10.0) <= 1e-9 and LX.v0 == 10 and LX.n_layers == 2
    xs = [s for s in inst.sites if s.lender == "X"]
    assert [s.id for s in xs] == ["X/L11-11", "X/L12-12"] and all(s.menu == (0,) for s in xs)
    assert np.isfinite(inst.price[0, 0]) and not np.isfinite(inst.price[0, 1])
    assert any("'lng'" in n and "S35" in n for n in inst.notes), inst.notes
    assert "1 of 1 trace lenders have at least one site" in inst.notes, inst.notes


@pytest.mark.needs_a12
def test_lambda_ref_per_lender():
    """§10 S2 (revised): lambda_ref_j is the median over the revocable lenders, one lambda_jl each, so
    the stranding costs mu of example_1day do not change with merge_identical_layers (seeds 1, 2 and 8,
    where the previous median over sites changed mu). mu_fb = r_mu beta_tilde_ref at a0 with that median
    (r_mu = 1, kv_share 0, beta_jl 0), recomputed here; the old median over the revocable sites differs
    between the two builds for some of these seeds, so the test separates the two rules."""
    from sublet import calib
    from fixtures import load_json
    base = load_json(CONFIGS / "example_1day.json")
    old_differs, merged = [], []
    for seed in (1, 2, 8):
        insts = []
        for merge in (False, True):
            cfg = dict(base, seed=seed, lender_model=dict(base["lender_model"], merge_identical_layers=merge))
            insts.append(build_instance(cfg))
        a, b = insts
        merged.append(b.m < a.m)
        for name in ("mu_fb_usd", "mu_kv_usd", "mu_fl_usd", "pi_usd_per_min"):
            assert np.array_equal(getattr(a.stranding, name), getattr(b.stranding, name)), (seed, name)
        old = []
        for inst in (a, b):
            rev = [l for l, s in enumerate(inst.sites) if any(not inst.contracts[k].protected for k in s.menu)]
            first = {}
            for l in rev:
                first.setdefault(inst.sites[l].lender, l)
            for j, x in enumerate(inst.llms):
                lam = float(np.median([inst.lam_s[j, l] for l in first.values()]))
                bt = calib.beta_tilde_usd(0.0, lam, x.g, inst.a0_usd_per_gpu_h, inst.q_gpu_usd_per_h, inst.phi_load)
                assert abs(inst.stranding.mu_fb_usd[j] - bt) <= 1e-12 * max(1.0, bt), (seed, j)
            old.append(np.median(inst.lam_s[:, rev], axis=1))
        old_differs.append(not np.array_equal(old[0], old[1]))
    assert any(merged) and any(old_differs), (merged, old_differs)


def test_lambda_ref_site_option():
    """§10 S2 (revised), beta_tilde_ref.load_time 'site': it needs exactly one revocable lender, not one
    revocable site, so a single inline trace lender with two layer sites (merge off, the default) builds
    and gives the mu of the merged build (one site), r_mu beta_tilde at its load time of 300 s; a second
    revocable lender (the toy's synthetic L0) raises ConfigError."""
    from sublet import calib
    from sublet.config import ConfigError
    insts = []
    for merge in (False, True):
        cfg = toy_config({"stranding.beta_tilde_ref.load_time": "site", "lender_model.merge_identical_layers": merge},
                         sites=["P"])
        cfg["lenders"] = [inline_trace_lender([40.0] * 400, "X", n_layers=2, lam_s=300.0)] + cfg["lenders"]
        insts.append(build_instance(cfg))
    a, b = insts
    assert [s.id for s in a.sites] == ["X/L4-4", "X/L5-5", "P"] and [s.id for s in b.sites] == ["X/L4-5", "P"]
    bt = calib.beta_tilde_usd(0.0, 300.0, 1, A0, Q_GPU, 1.0)
    for inst in (a, b):
        assert abs(inst.stranding.mu_fb_usd[0] - bt) <= 1e-12, (inst.stranding.mu_fb_usd, bt)
    assert np.array_equal(a.stranding.mu_fb_usd, b.stranding.mu_fb_usd)
    cfg = toy_config({"stranding.beta_tilde_ref.load_time": "site"}, sites=["L0", "P"])
    cfg["lenders"] = [inline_trace_lender([40.0] * 400, "X", n_layers=2, lam_s=300.0)] + cfg["lenders"]
    with pytest.raises(ConfigError, match="exactly one revocable lender, got 2"):
        build_instance(cfg)


@pytest.mark.parametrize("information", ["I1", "I2"])
def test_public_view(information):
    """public_view (§3.4.4, §5.2): no announcement sets or layer indices; layer sites renamed
    '<lender>/S<i>' by increasing local_layer_lo; capacities, menus, prices and client data kept; no
    slack series or demand."""
    cfg = toy_config({"time.horizon_min": 40, "borrowers.clients.0.demand.values": [0, 0, 1, 1, 1, 1, 0, 0],
                      "lenders.0.R": [3, 6]}, sites=["L0", "P"])
    cfg["lenders"] = [inline_trace_lender([8, 16, 16, 24, 32, 40, 40, 48], "X", n_layers=2, layer_gpus=8,
                                          lease_size_quantile=50)] + cfg["lenders"]
    inst = build_instance(cfg)
    assert [s.id for s in inst.sites] == ["X/L2-2", "X/L3-3", "L0", "P"]
    assert inst.sites[2].R_explicit is not None and inst.sites[0].layer_lo is not None
    v = public_view(inst, information)
    assert v.information == information
    assert [s.id for s in v.sites] == ["X/S0", "X/S1", "L0", "P"]
    for s, s0 in zip(v.sites, inst.sites):
        assert s.R_explicit is None and s.layer_lo is None and s.layer_hi is None and s.local_layer_lo is None
        assert (s.kind, s.lender, s.capacity_gpus, tuple(s.menu)) == (s0.kind, s0.lender, s0.capacity_gpus,
                                                                      tuple(s0.menu))
    names = {f.name for f in dataclasses.fields(v)}
    assert not names & {"lenders", "clients", "demand", "config", "notes", "seed"}, names
    assert np.array_equal(v.price, inst.price) and not v.price.flags.writeable
    assert np.array_equal(v.client_delta_usd_per_h, inst.clients.delta_usd_per_h)


def test_to_core_values():
    """to_core by value (rule T12, §3.4.4) on the toy (u = 4, Delta_s = 5) with delta = 0.5 USD per
    replica-load-hour and lambda = 300, 300, 600 s: q = 7.15 * 5 / (60 * 4), delta = 0.5 * 5 / (60 * 4),
    beta = beta~ at a0 = lambda (a0 + phi q_GPU) / 3600 with phi = 1, a = price * 5 / 60 (1e-12)."""
    inst = toy_instance()
    inst.clients.delta_usd_per_h[:] = 0.5
    ex = to_core(inst, trace_schedule(inst), not_offered="big_m")
    C = ex.core
    assert inst.units_per_replica == 4 and not ex.exact
    assert abs(C.q - 7.15 * 5 / 240) <= 1e-12
    assert np.allclose(C.delta, 0.5 * 5 / 240, rtol=0, atol=1e-12)
    assert np.allclose(C.beta[0], np.array([300.0, 300.0, 600.0]) * (2.85 + 7.15) / 3600, rtol=0, atol=1e-12)
    assert np.allclose(C.a[0, :2], np.array([2.85, 3.0]) * 5 / 60, rtol=0, atol=1e-12)
    assert np.allclose(C.a[1, :2], np.array([2.9, 3.1]) * 5 / 60, rtol=0, atol=1e-12)
    assert abs(C.a[2, 2] - 5.97 * 5 / 60) <= 1e-12
    assert list(C.g) == [1] and C.T == 24


@pytest.mark.needs_a12
def test_regional_demand_tightness():
    """example_1day: peak sum_c g_j d_c over the supply of the layer sites is 0.5; 4 clients."""
    inst = build_instance(CONFIGS / "example_1day.json")
    validate(inst)
    assert inst.n == 4
    supply = sum(s.capacity_gpus for s in inst.sites if s.kind == "layer")
    g = np.array([inst.llms[j].g for j in inst.clients.llm], dtype=float)
    peak = float((g[:, None] * inst.clients.demand).sum(axis=0).max())
    assert abs(peak / supply - 0.5) <= 1e-9, (peak, supply)
    assert sum(s.kind == "protected" for s in inst.sites) == 2
    assert {inst.llms[j].tier for j in inst.clients.llm} == {"M", "L"}
