"""Tests of the E2 driver (design/sim_spec_ms3.md §6, §10 row test_e2.py).

- layering (M18): the layers are nested 0/1 series and their sum equals sum_k 1[x' >= k] = min(floor(x'), 8);
- band pairing: layer k with the layer site of local_layer_lo k, bottom first;
- single_band passes the single-site DP's domain check (with a band and band-less);
- episode_instance (M21): one supply window (no purchase from r* on, the refusals counted by A1 and the engine
  alike), demand 1 on the on-period and 0 outside, the horizon T_e of §6.3, synthetic sites and lender;
- on hand-built episodes (no window) A1's and the DP's costs equal hand values;
- BL0a's analytic cost equals the engine's BL0a (M47);
- which rules run (Q42 (a), M22) and the coincidence logic of the summary on a hand-made run file;
- a band-less layer (M48): its DP value is at most its fallback cost and equals it with a_p >= q_j / g_j; in a cell
  job no rule runs on it and the summary counts it (slow, with the coincidence detection on a cell where A1 = cold);
- the summary's bootstrap draws equal metrics.aggregate's.
Instances are one-day E2 base instances (needs_a12).
"""
import dataclasses

import numpy as np
import pytest

from fixtures import assert_rel

from sublet.config import ConfigError
from sublet.experiments import e2
from sublet.experiments import ms3_common as mc

DAY = 1440


def _base(lender="a2:c05", H=60, mu=1.0, c=1, series="azure2024_conv", extra=None):
    spec = e2.run_spec(lender, series, H, mu, c, horizon_min=DAY, extra=extra)
    inst, model, ecfg = e2.build_base(spec, c)
    return spec, inst, model, ecfg


@pytest.fixture(scope="module")
def c05():
    return _base()


@pytest.fixture(scope="module")
def a100():
    return _base(lender="a1:A100-SXM4-80GB", H=60)


# ---------------------------------------------------------------- layers and bands
@pytest.mark.needs_a12
def test_layers_nested_and_sum(c05):
    _, inst, _, _ = c05
    lay, p = e2.layers_of(inst)
    x = np.asarray(inst.clients.demand[0], dtype=np.float64)
    assert p == float(np.percentile(x, 99.5)) and p > 0
    xs = e2.K_LAYERS * x / p
    assert lay.shape == (e2.K_LAYERS, inst.grid.T_fast)
    assert set(np.unique(lay).tolist()) <= {0.0, 1.0}
    for k in range(1, e2.K_LAYERS):
        assert np.all(lay[k] <= lay[k - 1]), k                     # nested: layer k+1 on implies layer k on
    ref = sum((xs >= k).astype(np.float64) for k in range(1, e2.K_LAYERS + 1))
    assert np.array_equal(lay.sum(axis=0), ref)
    assert np.array_equal(lay.sum(axis=0), np.minimum(np.floor(xs), e2.K_LAYERS))
    assert lay[0].sum() > 0


@pytest.mark.needs_a12
def test_layers_do_not_depend_on_H():
    """The layers of (lender, series, alignment) are the same at every H, also where the builder scales the demand
    differently (a lender's lendable supply depends on its menu's window, and the series demand is scaled to the
    supply): x' = 8 x / P99.5(x) does not change when x is scaled (M18)."""
    lay0, d0 = None, set()
    for H in (0, 60):
        _, inst, _, _ = _base(lender="a1:A100-SXM4-80GB", H=H, c=2, series="burstgpt_1")
        lay, _ = e2.layers_of(inst)
        d0.add(round(float(np.asarray(inst.clients.demand).sum()), 6))
        if lay0 is None:
            lay0 = lay
        assert np.array_equal(lay, lay0), H
    assert len(d0) == 2                                            # the demand scale differs between the two H


@pytest.mark.needs_a12
def test_band_pairing(c05, a100):
    for _, inst, _, _ in (c05, a100):
        bands = e2.band_sites(inst)
        assert sorted(bands) == list(range(1, len(bands) + 1))
        lo = [inst.sites[bands[k]].layer_lo for k in sorted(bands)]
        assert lo == sorted(lo) and len(set(lo)) == len(lo)       # bottom first
        for k, l in bands.items():
            assert inst.sites[l].kind == "layer" and inst.sites[l].local_layer_lo == k
        assert inst.sites[e2.prot_site(inst)].kind == "protected"
    assert len(e2.band_sites(c05[1])) == 8 and len(e2.band_sites(a100[1])) == 7   # e2_layers_probe.json, n_bands


@pytest.mark.needs_a12
def test_single_band_in_dp_domain(c05, a100):
    from sublet.opt.dp import dp_domain
    from sublet.types import INF
    for (_, inst, model, _), ks in ((c05, (1, 8)), (a100, (1, 8))):
        lay, _ = e2.layers_of(inst)
        bands, prot = e2.band_sites(inst), e2.prot_site(inst)
        for k in ks:
            ik = e2.single_band(inst, k, lay)
            assert np.array_equal(ik.clients.demand[0], lay[k - 1])
            fin = set(np.flatnonzero(np.isfinite(ik.clients.delta_usd_per_h[0])).tolist())
            assert fin == ({bands[k], prot} if k in bands else {prot})
            assert all(ik.clients.delta_usd_per_h[0, l] == INF for l in range(ik.m) if l not in fin)
            sched = e2.static_schedule(ik, model, 1)
            assert dp_domain(ik, sched, "fast") == [], (k, dp_domain(ik, sched, "fast"))


# ---------------------------------------------------------------- episodes
@pytest.mark.needs_a12
def test_episode_instance_one_window(c05):
    from sublet.opt.dp import solve_dp
    spec, inst, model, ecfg = c05
    lay, _ = e2.layers_of(inst)
    bands, prot = e2.band_sites(inst), e2.prot_site(inst)
    refuse = dataclasses.replace(model, on_unavailable="refuse")
    k = 8                                                           # the top band: announced most often
    ik = e2.single_band(inst, k, lay)
    R_band = e2.static_schedule(ik, model, 1).R[bands[k]]
    found = 0
    for fa, fb in e2.on_periods(lay[k - 1]):
        e, wend = e2.episode_instance(ik, bands[k], R_band, fa, fb)
        phi = inst.grid.phi
        t0 = fa // phi
        D = inst.contracts[e2._rev_contract(inst, bands[k])].D_min(inst.grid.slow_min)
        assert e.grid.T_slow == min(-(-fb // phi) - t0 + -(-D // inst.grid.slow_min) + 1, inst.grid.T_slow - t0)
        d = e.clients.demand[0]
        on = np.zeros_like(d)
        on[fa - t0 * phi:fb - t0 * phi] = 1.0
        assert np.array_equal(d, on)                               # 1 on the on-period, 0 outside
        assert all(s.kind != "layer" for s in e.sites)
        R = np.asarray(R_band)
        R = R[R >= t0] - t0
        exp = np.arange(int(R[0]), e.grid.T_slow) if len(R) and R[0] < e.grid.T_slow else np.zeros(0, int)
        assert np.array_equal(e.sites[bands[k]].R_explicit, exp) and wend == bool(len(exp))
        assert all(len(e.sites[l].R_explicit) == 0 for l in bands.values() if l != bands[k])
        lt = next(x for x in e.lenders if x.lender == e.sites[bands[k]].lender)
        assert lt.kind == "synthetic" and lt.S is None and tuple(lt.site_index) == tuple(
            next(x for x in inst.lenders if x.lender == lt.lender).site_index)
        if not wend:
            continue
        found += 1
        res = e2.simulate_rule(spec, "a1", bands[k], prot, e, refuse, ecfg, 1)
        r_star = int(exp[0])
        assert all(L.start_slot < r_star for L in res.leases if L.site == bands[k])   # one window: no purchase from r*
        rep = e2.a1_report(res)
        assert rep["counts"]["refused"] == int(res.metrics["refused"].get("unavailable", 0))
        assert not res.invariant_failures
        dp = solve_dp(e, res.schedule, grid="fast", refuse_unavailable=True, return_plan=False)
        assert dp.status_msg == "optimal" and res.components["total"] >= dp.objective * (1 - 1e-9)
        if found >= 3:
            break
    assert found >= 1


@pytest.mark.needs_a12
def test_hand_built_episodes(c05):
    """No supply window (R empty): A1 starts its clock at the episode's first slot, buys n_s0 slots in, its replica
    is warm after ceil(lambda / 1 min) minutes, and it releases at the episode end (after the billed term); OPT buys
    at the first slot. Short episodes cost the fallback for both."""
    from sublet.opt.dp import solve_dp
    from sublet.timing import warm_fast
    spec, inst, model, ecfg = c05
    lay, _ = e2.layers_of(inst)
    bands, prot = e2.band_sites(inst), e2.prot_site(inst)
    k = 1
    ik = e2.single_band(inst, k, lay)
    refuse = dataclasses.replace(model, on_unavailable="refuse")
    q = float(inst.llms[0].q_usd_per_h)
    a = float(inst.price[bands[k], e2._rev_contract(inst, bands[k])])
    slow = inst.grid.slow_min
    lam_ms = int(inst.lam_ms()[0, bands[k]])
    w = warm_fast(0, lam_ms, inst.grid.fast_min)                   # minutes on fallback while loading (1-min grid)
    ta = 100                                                        # slow slot of the episode start
    for L_min in (120, 3):
        fa, fb = ta * slow, ta * slow + L_min
        e, wend = e2.episode_instance(ik, bands[k], np.zeros(0, dtype=np.int64), fa, fb)
        assert not wend
        res = e2.simulate_rule(spec, "a1", bands[k], prot, e, refuse, ecfg, 1)
        dp = solve_dp(e, res.schedule, grid="fast", refuse_unavailable=True, return_plan=False)
        n_s0 = e2.a1_report(res)["n_s0"]
        if L_min == 3:
            assert_rel(res.components["total"], q * L_min / 60.0, 1e-12, "A1, short episode")
            assert_rel(dp.objective, q * L_min / 60.0, 1e-12, "DP, short episode")
            continue
        D = inst.contracts[e2._rev_contract(inst, bands[k])].prepaid_min
        assert L_min - slow * n_s0 >= D                             # the billed term ends before the release
        alg = (q * (slow * n_s0 + w) + a * (L_min - slow * n_s0)) / 60.0
        opt = (q * w + a * L_min) / 60.0
        assert_rel(res.components["total"], alg, 1e-12, "A1, no window")
        assert_rel(dp.objective, opt, 1e-12, "DP, no window")


@pytest.mark.needs_a12
def test_bl0a_analytic_equals_engine(c05):
    from sublet.drivers.run import make_policy
    from sublet.engine import simulate
    spec, inst, model, ecfg = c05
    lay, _ = e2.layers_of(inst)
    for k in (1, 5):
        ik = e2.single_band(inst, k, lay)
        pol = make_policy({**spec, "policy": {"id": "BL0a", "params": {}}}, ik)
        res = simulate(ik, pol, model, ecfg, lender_seed=1, policy_seed=1)
        assert_rel(res.components["total"], e2.bl0a_usd(inst, lay[k - 1]), 1e-9, f"BL0a layer {k}")


@pytest.mark.needs_a12
def test_bandless_dp_at_most_fallback(a100):
    """M48: the protected-only DP of a band-less layer is at most its fallback cost, and equals it once the protected
    price reaches q_j / g_j (no protected minute cheaper than fallback)."""
    from sublet.opt.dp import solve_dp
    spec, inst, model, _ = a100
    lay, _ = e2.layers_of(inst)
    k = 8
    assert k not in e2.band_sites(inst)
    fb = e2.bl0a_usd(inst, lay[k - 1])
    ik = e2.single_band(inst, k, lay)
    d = solve_dp(ik, e2.static_schedule(ik, model, 1), grid="fast", return_plan=False)
    assert d.status_msg == "optimal" and d.objective <= fb + 1e-9
    L = inst.llms[0]
    _, hi, model_hi, _ = _base(lender="a1:A100-SXM4-80GB", H=60,
                               extra={"prices.a_protected_usd_per_gpu_h": L.q_usd_per_h / L.g})
    lay_hi, _ = e2.layers_of(hi)
    assert np.array_equal(lay_hi, lay)
    ih = e2.single_band(hi, k, lay_hi)
    d_hi = solve_dp(ih, e2.static_schedule(ih, model_hi, 1), grid="fast", return_plan=False)
    assert_rel(d_hi.objective, fb, 1e-9, "band-less DP at a_p = q_j / g_j")


# ---------------------------------------------------------------- rules and the summary logic
def test_rules_for():
    run, filled, missing = e2.rules_for(1.0, "trace", 60, False, "cold")
    assert run == ["cold", "prewarm", "bl6"] and not filled and not missing
    run, filled, missing = e2.rules_for(1.0, "eager", 0, True, "warm")
    assert run == ["cold", "prewarm"] and list(filled) == ["bl6"] and not missing
    run, filled, _ = e2.rules_for(0.2, "trace", 60, False, "cold")
    assert run == ["prewarm", "bl6"] and list(filled) == ["cold"]
    run, filled, _ = e2.rules_for(2.0, "trace", 60, False, "warm")
    assert run == ["cold", "bl6"] and list(filled) == ["prewarm"]
    run, filled, _ = e2.rules_for(0.5, "trace", 5, True, "cold")
    assert run == ["bl6"] and sorted(filled) == ["cold", "prewarm"]
    run, filled, missing = e2.rules_for(0.5, "eager", 5, False, "cold")
    assert run == ["bl6"] and list(filled) == ["cold"] and missing == ["prewarm"]


def _rec(total, insured=False, reaction="cold", fallback=None):
    comp = {k: 0.0 for k in ("lease_prepaid", "lease_rent", "lease", "loading", "routing", "fallback", "stranding",
                             "stranding_fb", "total")}
    comp.update(total=total, fallback=total if fallback is None else fallback)
    return {"total": total, "components": comp, "insured": insured, "reaction": reaction, "invariant_failures": 0,
            "gpu_only_lease_slots": 0}


def _doc(prewarm_total=10.0, prewarm_eps=(2.0, 3.0)):
    """A hand-made cell run file: one series, layer 1 with a band (A1 10 USD, cold = A1, pre-warm run), layer 2
    band-less (fallback 4 USD, protected-only DP 3 USD), two episodes of layer 1."""
    rules = {"a1": _rec(10.0), "cold": {"same_as": "a1", "why": "test"}, "prewarm": _rec(prewarm_total),
             "bl6": _rec(11.0)}
    L1 = {"k": 1, "band": "x/L1", "bandless": False, "demand_load_h": 2.0, "bl0a": 14.3,
          "trace": {"dp": {"value": 8.0, "status": "optimal"}, "rules": rules, "not_run": []}}
    L2 = {"k": 2, "band": None, "bandless": True, "demand_load_h": 0.5, "bl0a": 4.0,
          "trace": {"dp": {"value": 3.0, "status": "optimal"}, "rules": {}}}
    ep = {"layer": [1, 1], "f_a": [0, 50], "f_b": [20, 70], "window_end": [True, False], "opt": [1.0, 2.0],
          "opt_status": ["optimal", "optimal"], "bl0a": [2.4, 2.4],
          "alg": {"a1": [2.0, 3.0], "prewarm": list(prewarm_eps), "bl6": [2.5, 3.0]}}
    return {"cell": {"lender": "a2:c05", "group": "maas", "H": 60, "mu": 0.2, "c": 1,
                     "row": {"H_star_mu_s": 1e9, "alpha_k": 0.44}},
            "a1": {"insured": False, "reaction": "cold"}, "schedules": ["trace"],
            "series": {"azure2024_conv": {"layers": [L1, L2], "episodes": ep}},
            "checks": {"E2_2": {"a": [], "b": []}, "E2_3": {"n_compared": 0, "max_abs_diff_a1_cold": 0.0,
                                                           "max_abs_diff_insured": 0.0, "violations": []},
                       "E2_4": {"n_runs": 0, "examples": []},
                       "E2_5": {"n_episodes": 2, "min_ratio": 1.0, "n_below": 0, "below": []}}}


def test_summary_logic_on_a_hand_made_run_file():
    C = e2._Collect()
    C.add(_doc())
    key = ("a2:c05", 60, 0.2, 1)
    st_cold, st_pre = C.coinc[key + ("cold",)], C.coinc[key + ("prewarm",)]
    assert st_cold[1] == 0 and not st_cold[2]                      # filled from A1: equal, not run
    assert st_pre[1] == 0 and st_pre[2] and st_pre[0] == 3          # week layer and two episodes compared
    e = e2._episodes_entry(C, "maas", 60, 0.2, "cold", (1,))
    assert e["n"] == 2 and e["median"] == 1.75 and e["ran"] is False  # A1's ratios 2/1 and 3/2
    assert e2._episodes_entry(C, "maas", 60, 0.2, "bl0a", (1,))["median"] == pytest.approx((2.4 + 1.2) / 2)
    t = e2._totals_entry(C, "maas", 60, 0.2, "trace", "a1", (1,), ("azure2024_conv",))
    assert t["n_pairs"] == 1
    assert t["cost_over_bl0a"]["median"] == pytest.approx((10.0 + 4.0) / (14.3 + 4.0))   # band-less: fallback
    assert t["whole_trace_ratio"]["median"] == pytest.approx(10.0 / 8.0)                  # layers with a band
    assert t["components"]["fallback"] == pytest.approx(10.0 + 4.0)
    tn = e2._totals_entry(C, "spot", 60, 0.2, "trace", "a1", (1,), ("azure2024_conv",))     # M23: no spot pool
    assert tn["n_pairs"] == 0 and tn["note"] and tn["components"] is None and tn["components_note"]
    assert set(tn["cost_over_bl0a"]) == set(t["cost_over_bl0a"]) | {"note"} | {
        f + "_note" for f in ("median", "median_ci95", "p95", "max")}    # §2.6: the non-null fields, null with notes
    assert C.bandless == {}and C.bandless_all[0]["dp"] == 3.0 and C.bandless_all[0]["fallback"] == 4.0
    C2 = e2._Collect()
    C2.add(_doc(prewarm_total=12.0, prewarm_eps=(2.0, 3.5)))
    st = C2.coinc[key + ("prewarm",)]
    assert st[1] == 2 and st[2]                                     # the week layer and one episode differ


def test_agg_matches_metrics_aggregate():
    from sublet.metrics import aggregate
    rng = np.random.default_rng(3)
    for n in (1, 7, 500):
        v = rng.lognormal(size=n)
        a, b = e2.agg(v), aggregate(v)
        assert a["n"] == b["n"] and a["median"] == b["median"] and a["max"] == b["max"]
        assert a["p95"] == pytest.approx(b["p95"], rel=1e-15)
        for x, y in zip(a["median_ci95"], b["median_ci95"]):
            assert x == pytest.approx(y, rel=1e-12)
        assert a["p95_ci95"][0] <= a["p95"] <= a["p95_ci95"][1] + 1e-12 or n == 1
    assert e2.agg([])["median"] is None and e2.agg([])["median_note"]


def test_game_job_records_a_failed_cell(tmp_path, monkeypatch):
    """§2.4: a game cell whose solver raises is recorded in the job's errors and left out of its rows; the job goes on
    and its record is 'ok' (no solver runs here: _game_cell is replaced)."""
    monkeypatch.setenv("MS3_E2_REDUCED", "1")
    monkeypatch.delenv("MS3_SLOTS", raising=False)

    def fake(args):
        if args[3] == 0.5:
            raise RuntimeError("solver failed")
        return {"switch": args[0], "mu": args[1], "lam": args[2], "Hs": args[3], "CR": 1.7}
    monkeypatch.setattr(e2, "_game_cell", fake)
    lam_key = e2.num(e2.game_inputs()["LAM"])
    job = next(j for j in e2.jobs() if j.id == e2.game_job_id("beta", 1.0, lam_key))
    out = tmp_path / "e2"
    rec = mc.run_job("e2", job, lambda o: e2.run(job, o, out), out)
    assert rec["status"] == "ok" and rec["n_errors"] == 1 and "solver failed" in rec["errors"][0]["error"]
    d = mc.read_json(out / "runs" / "game" / mc.job_file_name(job.id))
    hs = [r["Hs"] for r in d["rows"]]
    assert 0.5 not in hs and d["failed_Hs"] == [0.5] and len(hs) == len(e2.game_grid("beta", 1.0, lam_key)) - 1


def test_joint_rows_fall_back_to_the_lp(tmp_path):
    """§2.5: a joint MILP job stopped at the hard wall-clock limit keeps its LP as LB (its pre-MILP record); an 'ok'
    job gives its run file; a job without a record gives no row."""
    out = tmp_path / "e2"
    js = [j for j in e2.jobs() if j.params["part"] == "joint"][:3]
    pre = {"lender": "a2:c05", "series": "azure2024_conv", "H": 60, "mu": 1.0, "c": 1, "T_slow": 288, "sum_dp": 11.0,
           "dp_by_layer": [], "lp": {"status": 0, "objective": 10.0, "dual_bound": None, "gap": None, "grid": "fast"},
           "milp_limit_s": 300, "stage": "written before the MILP started"}
    mc.dump_json(pre, e2.joint_lp_path(out, js[0].id))
    mc.dump_json({"job": js[0].id, "status": "wall_limit"}, mc.record_path(out, js[0].id))
    mc.dump_json({"job": js[1].id, "status": "ok"}, mc.record_path(out, js[1].id))
    mc.dump_json({"lender": "x", "sum_dp": 1.0}, out / "runs" / "joint" / mc.job_file_name(js[1].id))
    rows = e2.joint_rows(out, js, mc.read_records(out))
    assert len(rows) == 2
    r = rows[0]
    assert r["LB"] == 10.0 and r["LB_source"] == "lp" and r["milp_status"] == "wall_limit" and r["incumbent"] is None
    assert r["ratio_sum_dp_over_LB"] == pytest.approx(1.1) and r["ratio_sum_dp_over_incumbent"] is None
    assert r["ratio_sum_dp_over_incumbent_note"] and "stage" not in r and r["note"]
    assert rows[1] == {"lender": "x", "sum_dp": 1.0}


def test_job_ids_and_keys():
    jid = e2.cell_job_id("a1:A100-SXM4-80GB", 60, 0.2, 3)
    assert jid == "e2:cell:lender=a1.A100-SXM4-80GB:H=60:mu=0.2:c=3"
    _, part, kv = mc.parse_job_id(jid)
    assert part == "cell" and e2.lender_of_key(kv["lender"]) == "a1:A100-SXM4-80GB"
    assert e2.num(e2.game_inputs()["LAM"]) == "0.715" and e2.num(1.0) == "1" and e2.num(0.2) == "0.2"
    js = e2.jobs()
    cells = [j for j in js if j.params["part"] == "cell"]
    # §6.2: 220 offered cells with alpha_k < 1, of which 5 get no layer site in the builder (S35)
    assert len(e2._offered_cells()) == 220
    assert e2.cells_without_sites() == (("a1:A800-SXM4-80GB", 10), ("a1:A800-SXM4-80GB", 15), ("a1:H800", 0),
                                        ("a1:H800", 1), ("a1:H800", 2))
    assert len(e2.all_cells()) == 215 and len(cells) == 215 * 4 + 215 * 3          # §6.8: 1,505 jobs
    assert not set(e2.all_cells()) & set(e2.cells_without_sites())
    assert sum(1 for j in js if j.kind == "alone") == 10 and sum(1 for j in js if j.params["part"] == "joint") == 8
    sp = e2.spot_pools_by_H()
    assert [h for h in e2.h_grid() if len(sp[h]) >= 2] == [0, 1, 2, 5]                # M23: spot up to 5 min
    q = e2.maas_quartiles()
    assert sorted(sum(q.values(), [])) == sorted(e2.maas_lenders()) and all(len(v) == 5 for v in q.values())


@pytest.mark.needs_a12
@pytest.mark.parametrize("lender,H", [("a1:A800-SXM4-80GB", 5), ("a1:A800-SXM4-80GB", 10), ("a1:H800", 0),
                                      ("a2:c05", 60)])
def test_layer_sites_match_the_builder(lender, H):
    """layer_sites counts the layer sites of the built instance, for every series and alignment; with none the
    builder cannot size the demand (supply 0), which is why such a cell runs no job."""
    n = e2.layer_sites(lender, H)
    for series, c in (("azure2024_conv", 1), ("burstgpt_2", 3)):
        spec = e2.run_spec(lender, series, H, 1.0, c)
        if n == 0:
            with pytest.raises(ConfigError, match="supply 0"):
                e2.build_base(spec, c)
        else:
            inst = e2.build_base(spec, c)[0]
            assert sum(s.kind == "layer" for s in inst.sites) == n
    assert (n > 0) == ((lender, H) in e2.all_cells())


# ---------------------------------------------------------------- cell jobs (slow)
@pytest.mark.needs_a12
@pytest.mark.slow
def test_cell_jobs_bandless_and_coincidence(tmp_path, monkeypatch):
    """Two reduced cell jobs and the summary: a1:A100-SXM4-80GB at H = 60 (7 bands, so layer 8 is band-less; A1
    insures by the first clause, so at mu = 1 the three rules coincide, E2-3) and a2:c05 at H = 2, mu = 0.2 (A1
    reacts cold: the rule 'cold' takes A1's values and the summary says cold_equals_a1)."""
    monkeypatch.setenv("MS3_E2_REDUCED", "1")
    out = tmp_path / "e2"
    jobs = {j.id: j for j in e2.jobs()}
    for jid in (e2.cell_job_id("a1:A100-SXM4-80GB", 60, 1.0, 1), e2.cell_job_id("a2:c05", 2, 0.2, 1)):
        rec = mc.run_job("e2", jobs[jid], lambda o, j=jobs[jid]: e2.run(j, o, out), out)
        assert rec["status"] == "ok" and rec["n_errors"] == 0, rec.get("error")
    d = mc.read_json(e2.cell_run_path(out, "a1:A100-SXM4-80GB", 60, 1.0, 1))
    L8 = d["series"]["azure2024_conv"]["layers"][7]
    assert L8["bandless"] and L8["trace"]["rules"] == {} and L8["eager"]["rules"] == {}
    assert L8["trace"]["dp"]["value"] <= L8["bl0a"] + 1e-9
    assert d["a1"]["insured"] is True
    d2 = mc.read_json(e2.cell_run_path(out, "a2:c05", 2, 0.2, 1))
    assert d2["a1"]["reaction"] == "cold" and not d2["a1"]["insured"]
    assert "cold" in d2["rules"]["trace"]["filled"] and "prewarm" in d2["rules"]["trace"]["run"]
    s = e2.summary(out)
    b = s["bandless"]["a1:A100-SXM4-80GB"]["60"]["1"]
    assert b["layers"] == 1 and b["sum_dp"] <= b["sum_fallback"] + 1e-9
    ch = s["checks"]                       # keyed by the check ids of §6.9, each with a status and its claim
    assert set(ch) == {"E2-1", "E2-2", "E2-3", "E2-3b", "E2-4", "E2-5", "E2-6", "E2-7"}
    assert all(v["status"] in ("pass", "fail", "missing", "pending", "explained", "informative") and v["claim"]
               for v in ch.values())
    assert ch["E2-3b"]["status"] == "pass" and ch["E2-3b"]["n_bandless"] >= 1
    assert ch["E2-3"]["max_abs_diff_insured"] == 0.0 and ch["E2-3"]["status"] == "pass"
    assert ch["E2-3"]["n_compared_week"] > 0 and ch["E2-3"]["n_compared_episodes"] > 0
    assert ch["E2-2"]["status"] == "pass" and ch["E2-2"]["a"]["n_rows_alpha_kind"] == len(e2._rows()) > 0
    assert ch["E2-1"]["status"] == "missing"         # no game job ran here
    a1_rec = d["series"]["azure2024_conv"]["layers"][0]["trace"]["rules"]["a1"]
    assert a1_rec["counts"]["episodes"] > 0                        # A1's report counts in the run file (§6.8)
    assert s["cold_equals_a1"]["maas"]["2"]["0.2"] is True
    assert ch["E2-4"]["status"] == "pass" and ch["E2-5"]["min_ratio"] >= 1 - 1e-9
    assert ch["E2-5"]["status"] == "pass" and ch["E2-6"]["status"] == ch["E2-7"]["status"] == "informative"
    # the key paths Fig. 7 and the supplement read (§8.6, §8.7)
    for g in ("maas", "spot", "a1:A100-SXM4-80GB", "maas_q1"):
        for r in e2.RULES:
            assert "median" in s["episodes"][g]["60"]["1"][r] and "p95" in s["episodes"][g]["60"]["1"][r]
        assert "cost_over_bl0a" in s["totals"][g]["60"]["1"]["trace"]["a1"]
        assert "H" in s["best_H"][g]["1"]["trace"]["a1"]
        assert "1" in s["coincide"][g]["60"] or "1_note" in s["coincide"][g]["60"]
    e = s["episodes"]["maas"]["2"]["0.2"]["a1"]
    assert e["n"] > 0 and e["median_ci95"][0] <= e["median"] <= e["median_ci95"][1] and "by_alignment" in e
    assert s["episodes"]["spot"]["60"]["1"]["a1"]["median"] is None                     # M23: one pool at 60 min
    assert s["meta"]["maas_quartiles"] == e2.maas_quartiles()
