"""Tests of the E6 driver (design/sim_spec_ms3.md §7, §10 row test_e6.py).

- E6-2 and E6-3 on one MaaS key (a2:c00 at H = 1 min, azure2024_conv, one day): INS and WARM at the reference row
  r = 1.1 and mu / beta~ = 1, rerun at r = 3 (INS, WARM) and at mu / beta~ = 2 (WARM), give A + a_p G + mu_fb W with
  the same plan (lease records without prices); BL7 equals A1's cold, non-insured run of the key;
- G from the lease records equals the protected leases' billed GPU-hours recomputed by hand from their times;
- the decision per row from c2rule equals A1's own decision when A1 is built at that row's protected price;
- the boundary bisection (certified bound) returns r* with r* < LB(r* alpha) and r* + 1e-3 >= LB((r* + 1e-3) alpha),
  and r* <= r*_grid, at H = 0 for the MaaS median alpha (about 15 s: the grid value takes about 1 s per call);
- test_e6_1: E6-1 (a) and (b) (slow; 'quick' on a subset, 'all' on the full grid of §7.1).
"""
import numpy as np
import pytest

from fixtures import assert_rel

from sublet.experiments import e2, e6

DAY = 1440
KEY = ("a2:c00", 1, "azure2024_conv")       # H = 1 min < lambda: WARM cannot pre-warm; layers 1-3 strand on day 0


def _inst(mu=1.0, a_p=None, lam="a5", lender=KEY[0], H=KEY[1], series=KEY[2]):
    spec = e2.run_spec(lender, series, H, mu, 1, horizon_min=DAY, extra=e6.prot_overrides(a_p, lam))
    inst, model, ecfg = e2.build_base(spec, 1)
    return spec, inst, model, ecfg


@pytest.fixture(scope="module")
def key_runs():
    """The reference runs of KEY (INS, WARM at r = 1.1, mu = 1, lambda' = a5) on the top layer with an
    announcement, and the instance's a_k and beta~_ref."""
    spec, inst, model, ecfg = _inst()
    lay, _ = e2.layers_of(inst)
    bands, prot = e2.band_sites(inst), e2.prot_site(inst)
    b0 = min(bands)
    a_k = float(inst.price[bands[b0], e2._rev_contract(inst, bands[b0])])
    bt = float(inst.stranding.mu_fb_usd[0])
    spec_r, inst_r, _, _ = _inst(a_p=e6.R_REF * a_k)
    out = {"spec": spec, "inst": inst, "model": model, "ecfg": ecfg, "lay": lay, "bands": bands, "prot": prot,
           "a_k": a_k, "bt": bt, "runs": {}}
    for k in sorted(bands, reverse=True):
        ik = e2.single_band(inst_r, k, lay)
        warm = e2.simulate_rule(spec_r, "warm", bands[k], prot, ik, model, ecfg, 1)
        if warm.components["stranding_fb"] > 0:
            ins = e2.simulate_rule(spec_r, "ins", bands[k], prot, ik, model, ecfg, 1)
            out.update(k=k, ik=ik, runs={"warm": warm, "ins": ins})
            break
    assert out["runs"], "no layer of KEY strands under WARM"
    return out


@pytest.mark.needs_a12
def test_e6_2_linearity_in_ap_and_mu(key_runs):
    R = key_runs
    k, band, prot, a_k, bt = R["k"], R["bands"][R["k"]], R["prot"], R["a_k"], R["bt"]
    ref = {p: e6.decompose(res, R["ik"], e6.R_REF * a_k, bt) for p, res in R["runs"].items()}
    assert ref["ins"]["W"] == 0.0 and ref["ins"]["G"] > 0 and ref["warm"]["W"] > 0
    for p, res in R["runs"].items():
        assert not res.invariant_failures
        assert_rel(e6.plan_cost(ref[p], e6.R_REF * a_k, bt), res.components["total"], 1e-12, f"{p} at r_ref")
    for r, mu, plans in e6.E62_RERUNS:
        spec, inst, model, ecfg = _inst(mu=mu, a_p=r * a_k)
        ik = e2.single_band(inst, k, R["lay"])
        for p in plans:
            res = e2.simulate_rule(spec, p, band, prot, ik, model, ecfg, 1)
            assert_rel(res.components["total"], e6.plan_cost(ref[p], r * a_k, mu * bt), 1e-9, f"{p} r {r} mu {mu}")
            assert e6.plan_signature(res) == e6.plan_signature(R["runs"][p]), (p, r, mu)
    assert float(inst.stranding.mu_fb_usd[0]) == pytest.approx(2.0 * bt, rel=1e-15)


@pytest.mark.needs_a12
def test_e6_2_warm_that_prewarms():
    """Plan (iii) with pre-warm purchases (G > 0): a2:c00 at H = 2 min, where WARM buys protected capacity on a
    notice; at both lambda' its reruns at r = 3 (mu 1) and at mu / beta~ = 2 (r = 1.1) give A + a_p G + mu_fb W with
    the reference run's plan."""
    lender, H, series = "a2:c00", 2, "azure2024_conv"
    spec, inst, model, ecfg = _inst(lender=lender, H=H, series=series)
    lay, _ = e2.layers_of(inst)
    bands, prot = e2.band_sites(inst), e2.prot_site(inst)
    a_k = float(inst.price[bands[min(bands)], e2._rev_contract(inst, bands[min(bands)])])
    bt = float(inst.stranding.mu_fb_usd[0])
    found = 0
    for lam in e6.LAMS:
        spec_r, inst_r, _, _ = _inst(lender=lender, H=H, series=series, a_p=e6.R_REF * a_k, lam=lam)
        for k in sorted(bands):
            ik = e2.single_band(inst_r, k, lay)
            ref = e2.simulate_rule(spec_r, "warm", bands[k], prot, ik, model, ecfg, 1)
            x = e6.decompose(ref, ik, e6.R_REF * a_k, bt)
            if not x["G"] > 0:
                continue
            found += 1
            for r, mu in ((3.0, 1.0), (1.1, 2.0)):
                spec_x, inst_x, _, _ = _inst(lender=lender, H=H, series=series, mu=mu, a_p=r * a_k, lam=lam)
                res = e2.simulate_rule(spec_x, "warm", bands[k], prot, e2.single_band(inst_x, k, lay), model, ecfg, 1)
                assert_rel(res.components["total"], e6.plan_cost(x, r * a_k, mu * bt), 1e-9, f"warm {lam} {k} {r} {mu}")
                assert e6.plan_signature(res) == e6.plan_signature(ref), (lam, k, r, mu)
            break
    assert found == len(e6.LAMS)


@pytest.mark.needs_a12
def test_e6b_bl0a_analytic_equals_engine(monkeypatch):
    """E6(b)'s reference BL0a (sum over clients of q_j x demand, M47) equals the engine's BL0a on one day of
    bench_e7r (the reduced horizon) under the poorest and the richest menu, on the instances the jobs run
    (e6b_instance: menu R's demand)."""
    from sublet.drivers.run import make_policy
    from sublet.engine import simulate
    monkeypatch.setenv("MS3_E6_REDUCED", "1")
    for menu in ("R", "R+P+1h+H"):
        spec = e6.e6b_spec(menu, 1.0, 1)
        inst, model, ecfg, _ = e6.e6b_instance(menu, 1.0, 1)
        assert inst.grid.T_fast * inst.grid.fast_min == DAY
        res = simulate(inst, make_policy({**spec, "policy": {"id": "BL0a", "params": {}}}, inst), model, ecfg,
                       lender_seed=1, policy_seed=0)
        assert_rel(res.components["total"], e6.bl0a_all(inst), 1e-9, f"BL0a {menu}")


@pytest.mark.needs_a12
@pytest.mark.parametrize("mu", [1.0, 0.2])
def test_e6b_menus_have_menu_r_demand(monkeypatch, mu):
    """§7.2, M31: every menu's instance (e6b_instance, one day of bench_e7r at alignment 1) has exactly the demand,
    borrower_stats and so the BL0a of menu R's instance, while its contracts are the menu's own and its sites and
    lendable supply are its builder's. R+P+1h+H's own builder demand differs (its longest window, 245 min, gives it
    less lendable supply), so the replacement is needed; the run record and meta.instances carry the BL0a on the
    builder's demand as bl0a_own_demand."""
    from sublet.drivers.run import build
    monkeypatch.setenv("MS3_E6_REDUCED", "1")
    ref, _, _, ref_info = e6.e6b_instance("R", mu, 1)
    assert ref_info["demand_menu"] == e6.E6B_DEMAND_MENU == "R" and ref_info["bl0a_own_demand"] == e6.bl0a_all(ref)
    for menu, (rev, prot) in e6.MENUS.items():
        inst, _, _, info = e6.e6b_instance(menu, mu, 1)
        assert np.array_equal(inst.clients.demand, ref.clients.demand), menu
        assert inst.borrower_stats == ref.borrower_stats, menu
        assert e6.bl0a_all(inst) == e6.bl0a_all(ref) and info["demand_sha256"] == ref_info["demand_sha256"], menu
        assert [c.id for c in inst.contracts] == [x["id"] for x in rev] + (["protected"] if prot else []), menu
        own = build(e6.e6b_spec(menu, mu, 1), 1)[0]
        assert [s.id for s in inst.sites] == [s.id for s in own.sites], menu
        assert np.array_equal(inst.price, own.price, equal_nan=True), menu
        assert info["bl0a_own_demand"] == e6.bl0a_all(own), menu
    own = build(e6.e6b_spec("R+P+1h+H", mu, 1), 1)[0]
    supply = {m: sum(s.capacity_gpus for s in i.sites if s.kind == "layer")
              for m, i in (("R", ref), ("R+P+1h+H", own))}
    assert supply["R+P+1h+H"] < supply["R"]
    assert e6.bl0a_all(own) < e6.bl0a_all(ref)


@pytest.mark.needs_a12
def test_e6b_summary_shows_one_bl0a_per_alignment(monkeypatch, tmp_path):
    """run_b writes each job's BL0a on the instance it runs (menu R's demand) and summary_b's meta.instances shows
    one BL0a per alignment over the menus (max_rel_diff_bl0a exactly 0), with the builder's own BL0a kept as
    bl0a_own_demand; cost_R_over_cost_bl0a is still written. The reduced job list (one day, alignment 1, policy seed
    0); the A6 runs are replaced by a stub (driver inputs, policy and simulate), so only the instances are real."""
    import types

    from sublet.drivers import run as drun
    from sublet.experiments import ms3_common as mc
    monkeypatch.setenv("MS3_E6_REDUCED", "1")
    monkeypatch.setattr(drun, "driver_inputs", lambda *a, **k: ({}, {}))
    monkeypatch.setattr(drun, "make_policy", lambda *a, **k: None)
    fake = types.SimpleNamespace(components={"total": 1.0, "lease": 0.5, "fallback": 0.5}, metrics={}, leases=[],
                                 invariant_failures=[], runtime={})
    monkeypatch.setattr(e6.mc, "try_run", lambda errors, tag, fn, *a, **k: fake)
    out = tmp_path / "b"
    jobs = [j for j in e6.jobs(["b"]) if j.params["kind"] == "b"]
    assert {(j.params["menu"], j.params["mu"], j.params["c"]) for j in jobs} == set(e6.e6b_list())
    for j in jobs:
        rec = mc.run_job(e6.EXP, j, lambda o, j=j: e6.run(j, o, out), out=out, resume=False)
        assert rec["status"] == "ok", rec.get("error")
    summ = e6.summary_b(out)
    inst = summ["meta"]["instances"]
    assert inst["demand_menu"] == "R" and inst["max_rel_diff_bl0a"] == 0.0
    by = inst["by_menu"]
    assert set(by) == set(e6.MENUS) and all(set(v) == {"1"} for v in by.values())
    assert len({v["1"]["bl0a"] for v in by.values()}) == 1 and len({v["1"]["demand_sha256"] for v in by.values()}) == 1
    assert by["R+P+1h+H"]["1"]["bl0a_own_demand"] < by["R"]["1"]["bl0a"] == by["R"]["1"]["bl0a_own_demand"]
    for menu, v in summ["menus"].items():
        assert v["1"]["bl0a_by_alignment"] == {"1": by["R"]["1"]["bl0a"]}
        assert v["1"]["cost_R_over_cost_bl0a"]["median"] == pytest.approx(v["1"]["cost_R_over_cost"]["median"],
                                                                         rel=1e-12)


@pytest.mark.needs_a12
def test_e6_3_bl7_equals_cold_run(key_runs):
    R = key_runs
    spec, inst, model, ecfg = R["spec"], R["inst"], R["model"], R["ecfg"]
    ik = e2.single_band(inst, R["k"], R["lay"])
    band, prot = R["bands"][R["k"]], R["prot"]
    a1 = e2.simulate_rule(spec, "a1", band, prot, ik, model, ecfg, 1)
    rep = e2.a1_report(a1)
    assert rep["insured"] is False and rep["reaction"] == "cold"
    bl7 = e2.simulate_rule(spec, "bl7", band, prot, ik, model, ecfg, 1)
    assert e2.a1_report(bl7)["rrl"] is True
    assert abs(bl7.components["total"] - a1.components["total"]) <= 1e-9
    assert e6.plan_signature(bl7) == e6.plan_signature(a1)


@pytest.mark.needs_a12
def test_G_from_lease_records(key_runs):
    """G = sum(prepaid_usd + rent_usd) / a_p over the protected leases equals their billed GPU-hours from the lease
    times: gpus (prepaid_min + (end_min - prepaid_end_min)^+) / 60 on the 1-min grid."""
    R = key_runs
    res, inst = R["runs"]["ins"], R["ik"]
    a_p = e6.R_REF * R["a_k"]
    prot = {k for k, c in enumerate(inst.contracts) if c.protected}
    hand = 0.0
    for L in res.leases:
        if L.contract not in prot:
            continue
        P = inst.contracts[L.contract].prepaid_min
        hand += L.gpus * (P + max(0, L.end_min - L.prepaid_end_min)) / 60.0
    assert hand > 0
    assert_rel(e6.decompose(res, inst, a_p, R["bt"])["G"], hand, 1e-9, "G")


@pytest.mark.needs_a12
def test_decision_per_row_equals_a1():
    from sublet.instance import public_view
    # rows inside the first clause (1.5), and outside it at both lambda' (one families.lb_react call each)
    for lender, H, rows, mus in (("a2:c05", 60, (1.5, 1.75, 3.0), (1.0,)),
                                 ("a1:A800-SXM4-80GB", 0, (2.0,), (1.0, 2.0))):
        spec, inst, _, _ = _inst(lender=lender, H=H)
        bands, prot = e2.band_sites(inst), e2.prot_site(inst)
        b0 = min(bands)
        a_k = float(inst.price[bands[b0], e2._rev_contract(inst, bands[b0])])
        lay, _ = e2.layers_of(inst)
        for r in rows:
            for lam in e6.LAMS:
                for mu in mus:
                    spec_r, inst_r, _, _ = _inst(lender=lender, H=H, mu=mu, a_p=r * a_k, lam=lam)
                    ik = e2.single_band(inst_r, b0, lay)
                    d = e6.c2rule_decision(ik, bands[b0], prot)
                    pol = e2.make_rule_policy(spec_r, "a1", bands[b0], prot, ik)
                    pol.reset(public_view(ik, "I1"), np.random.default_rng(0))
                    assert d["insured"] == bool(pol.insured), (lender, H, r, lam, mu)
                    assert d["reaction"] == pol.reaction or d["insured"], (lender, H, r, lam, mu)
                    assert d["units"] == pol.units.as_dict()
                    assert d["plan"] == ("ins" if pol.insured else ("warm" if pol.reaction == "warm" else "cold"))


@pytest.mark.needs_a12
def test_boundary_bisection():
    for H in (0,):
        bi = e6.boundary_inputs(H, "maas")
        a, Hc = bi["alpha"], bi["H_c2"]
        lam = 1.0 / (a + bi["phi"])
        lb = lambda r: e6.lb_certified(a, r * a, 1.0, lam, Hc)          # noqa: E731
        res = e6.bisect_boundary(a, lb)
        rs = res["r_star"]
        assert 2 - a <= rs <= e6.R_HI
        assert rs < lb(rs) and res["lb_at_r_star"] == lb(rs)
        assert rs + e6.R_TOL >= lb(rs + e6.R_TOL)
        grid = e6.bisect_boundary(a, lambda r: e6.lb_grid(a, r * a, 1.0, lam, Hc))
        assert rs <= grid["r_star"] + 1e-12
    # the case without a qualifying r: lb at or below 2 - alpha
    res = e6.bisect_boundary(0.4, lambda r: 1.0)
    assert res["r_star"] == 2 - 0.4 and res["calls"] == 1 and res["note"]


@pytest.mark.slow
@pytest.mark.needs_a12
@pytest.mark.parametrize("subset", [pytest.param(True, id="quick"), pytest.param(False, id="all")])
def test_e6_1(subset):
    """E6-1 (§7.1): (a) the harness's INS worst ratio within [CR_ins (1 - 1e-3), CR_ins + 1e-9]; (b)
    insure_up_front equals the formula with LB from families.lb_react called directly, and A1 built at the row's
    protected price on a one-day E2 instance reports the same insured."""
    if subset:
        res = e6.e6_1(rows=(1.5, 2.0), hs=(0.0, 0.5), mus_=(1.0,), a1_H=(0,))
    else:
        res = e6.e6_1()
    assert res["a"]["n"] > 0 and res["a"]["n_fail"] == 0, [x for x in res["a"]["rows"] if not x["ok"]][:3]
    assert res["b"]["n"] > 0 and res["b"]["n_fail"] == 0, [x for x in res["b"]["rows"] if not x["ok"]][:3]
    assert res["b"]["a1"]["n"] > 0 and res["b"]["a1"]["n_fail"] == 0, [x for x in res["b"]["a1"]["rows"]
                                                                       if not x["ok"]][:3]
    assert res["pass"]
    assert all(r * e2.game_inputs()["AL"] < 1 for r in {x["r"] for x in res["a"]["rows"]})
    if not subset:
        assert sorted({x["r"] for x in res["a"]["rows"]}) == [1.1, 1.25, 1.5, 1.65, 1.7, 1.75, 2.0, 2.5]
        assert res["a"]["n"] == 8 * 8 and res["b"]["n"] == 8 * 8 * 4 * 2
