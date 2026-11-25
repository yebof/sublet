"""Tests of the shared MS4 layer experiments/ms4_common.py (design/sim_spec_ms4.md §2.1, §2.2, §2.6, §3.3, §3.7,
§10 row test_ms4_common.py).

- The B0 rule of M36: sublet_params on configs/toy.json returns inner 'BL5', gamma 1.0, kappa None and B0 = B0_SHARE *
  e6.bl0a_all(inst) exactly (B0_SHARE 0.1, B0_RULE '0.1*BL0a'); inner 'A7' for A7 + guard; a sub-instance from
  instance.restrict_clients gets its own BL0a (the sub-instances' B0 sum to the instance's, BL0a being additive over
  clients); make_policy builds A8 from the parameters and its run's allowance is B0 at every slot (Ratchet.allowance
  with kappa None: the report's guard.B and safe.B_curve); the run record (a8_record) carries B0_rule B0_RULE, B0_usd,
  bl0a_usd, gamma, kappa and info_class_reported 'online-I1 + a-priori N + a-priori BL0a' while
  registry.info_class('A8', params) stays 'online-I1 + a-priori N'; theory_params keeps B0 'auto' and kappa 10 (B0_rule
  'auto, kappa 10', B0_usd = A8's resolved B0 = guard.b0_auto); the sweep's shares give their own rules;
  count_certificates by hand; the allowance need of a need_params run (A8 executes BL5 unchanged) predicts the abort
  slot of the toy's A8 runs at smaller B0.
- Both accountings on a toy run with hand-made borrower_stats: total_usd - overflow_usd = own_capacity_usd to 1e-9,
  the ratios to BL0a and BL0b by hand, BL0b equal to provision.bl0b_usd in both accountings, BL0a in total accounting
  = BL0a + own capacity (E7-4); the null forms on an instance without borrower_stats.
- w0 on hand-made cells: one cell gives the maximum over the five stress modes of the 3-seed mean of r0; the median
  over cells; a missing run is left out; a mode without r0, or one of the five stress modes left out of the input,
  leaves W0 null; a non-stress, misspelled or unexpected mode raises.
- siloed_run on a 2-hour siloed Sublet run (the toy with two borrowers): one certificate and allowance record per
  sub-run, each with its own B0, the counts by case, summed components equal to the sub-runs' sum; BL2 through it
  equals drivers/run.run's siloed path.
- sum_bench with ms3_common.bracket on synthetic records: an empty sub-instance adds 0; exact iff every part is exact;
  the largest gap; a killed part's MILP leaves the bracket's point and hi null; parts on two grids raise.
- The instance builders without raw data: e7r_h5_overrides against Q44's block Q4, the slow grid and measurement 3's
  recorded overrides; routing_overrides (nested subgraphs of the default adjacency S7, n = 5 the config's S7);
  e7_spec against measurement 1's recorded run spec. With the a12 outputs (needs_a12): e7_spec builds measurement 1's
  week instance (169 sites, 21 contracts, 15 clients, T_slow 2016, its references) and the routing graphs n = 0, 2, 3
  keep its sites, clients, demand and BL0a, with only the cross-region arcs of the n links; gap_instance(1) reproduces
  measurement 3's e7week rerun instance (instance hash, demand sha256, BL0a, BL0a's schedule hash) and two calls give
  one hash.
"""
import json

import numpy as np
import pytest

from fixtures import SIM, assert_rel, explicit_client, toy_config, toy_instance

from sublet.algos import registry
from sublet.algos.guard import b0_auto
from sublet.config import DEFAULT_ADJACENCY
from sublet.drivers import provision
from sublet.drivers.run import build, load_run_spec, make_policy, ratio_validity, run
from sublet.engine import simulate
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms4_common as m4
from sublet.experiments import q44_study as q44
from sublet.experiments.e6 import bl0a_all
from sublet.instance import public_view, restrict_clients
from sublet.policies import AlwaysFallback

MS4SPEC = SIM / "out" / "ms4spec"
WEEK_CASE = MS4SPEC / "e7f_week_case_Sublet.json"            # measurement 1
GAP_RUNS = MS4SPEC / "e7r_h5_lp_runs_e7week.json"            # measurement 3, e7week demand
GAP_LP = MS4SPEC / "e7r_h5_lp_lp_e7week.json"
GAP_ESTIMATE = MS4SPEC / "e7r_h5_lp_estimate.json"
STRESS = ("L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co")


def _spec(instance, pid: str, params=None, name: str = "t_ms4_common") -> dict:
    return load_run_spec({"schema_version": 1, "name": name, "instance": instance, "engine": {"check_invariants": True},
                          "policy": {"id": pid, "params": dict(params or {})},
                          "seeds": {"config": [1], "lender": "config", "policy": [0]}})


def _two_borrowers() -> dict:
    """The toy with two explicit clients of borrowers b0 (the toy's demand) and b1 (another demand)."""
    cfg = toy_config()
    dem = cfg["borrowers"]["clients"][0]["demand"]["values"]
    other = [0.0, 0.5, 2.0, 1.5, 0.5, 0.0] * 4
    cfg["borrowers"]["clients"] = [explicit_client(dem, borrower="b0"), explicit_client(other, borrower="b1")]
    return cfg


def _a8_run(instance, params, c: int = 1, p: int = 0):
    spec = _spec(instance, "A8", params)
    inst, model, ecfg = build(spec, c)
    pol = make_policy(spec, inst)
    return inst, model, pol, simulate(inst, pol, model, ecfg, lender_seed=c, policy_seed=p)


# ---------------------------------------------------------------- the B0 rule (M36, §3.3)
def test_sublet_params_on_the_toy():
    """B0 = B0_SHARE * e6.bl0a_all(inst) exactly (B0_SHARE 0.1), gamma 1.0, kappa None, inner 'BL5' (Sublet) or 'A7'
    (A7 + guard); the parameters pass the run spec's validation; bad inner ids and shares raise."""
    inst = toy_instance()
    bl0a = bl0a_all(inst)
    assert bl0a > 0
    p = m4.sublet_params(inst)
    assert p == {"inner": "BL5", "gamma": 1.0, "kappa": None, "B0": 0.1 * bl0a}
    assert p["B0"] == m4.B0_SHARE * bl0a_all(inst) and m4.B0_SHARE == 0.1 and m4.B0_RULE == "0.1*BL0a"
    assert m4.sublet_params(inst, inner="A7") == {**p, "inner": "A7"}
    assert m4.sublet_params(inst, share=0.05)["B0"] == 0.05 * bl0a
    _spec("toy.json", "A8", p)
    for bad in ("BL2", "A8", "SILOED"):
        with pytest.raises(ValueError):
            m4.sublet_params(inst, inner=bad)
    with pytest.raises(ValueError):
        m4.sublet_params(inst, share=-0.01)
    with pytest.raises(TypeError):
        m4.sublet_params(inst, share=True)
    assert m4.theory_params("BL5") == {"inner": "BL5"}
    with pytest.raises(ValueError):
        m4.theory_params("BL2")


def test_sub_instance_gets_its_own_bl0a():
    """A sub-instance of restrict_clients gets B0_SHARE of its own BL0a; the sub-instances' B0 sum to the instance's."""
    from sublet.instance import build_instance
    inst = build_instance(_two_borrowers())
    full = m4.sublet_params(inst)["B0"]
    subs = [restrict_clients(inst, [c]) for c in range(inst.n)]
    b0 = [m4.sublet_params(s)["B0"] for s in subs]
    for s, b in zip(subs, b0):
        assert b == m4.B0_SHARE * bl0a_all(s) and 0 < b < full
    assert_rel(sum(b0), full, 1e-12, "sum of the sub-instances' B0")


@pytest.mark.parametrize("inner", ["BL5", "A7"])
def test_a8_allowance_is_b0_at_every_slot(inner):
    """make_policy builds A8 from sublet_params; with kappa None its allowance is B0 at every slot, whatever B_on;
    the run record carries the fields of §2.6 with B0_rule B0_RULE and info_class_reported, while
    registry.info_class is unchanged; the record is valid JSON."""
    inst0 = toy_instance()
    params = m4.sublet_params(inst0, inner=inner)
    inst, model, pol, res = _a8_run("toy.json", params)
    assert m4.sublet_params(inst, inner=inner) == params       # the built instance is the toy's
    B0 = params["B0"]
    rep = res.metrics["policy"]
    assert (rep["B0"], rep["kappa"], rep["gamma"]) == (B0, None, 1.0)
    assert rep["guard"]["B"] and all(b == B0 for b in rep["guard"]["B"])
    assert len(rep["safe"]["B_curve"]) == inst.grid.T_slow and all(b == B0 for b in rep["safe"]["B_curve"])
    assert pol.ratchet.allowance(0.0) == pol.ratchet.allowance(1e9) == B0
    rec = m4.a8_record(res, inst, params, model.information)
    assert (rec["B0_rule"], rec["B0_usd"], rec["bl0a_usd"], rec["gamma"], rec["kappa"]) == \
        (m4.B0_RULE, B0, bl0a_all(inst), 1.0, None)
    assert rec["B0_report_usd"] == B0
    assert registry.info_class("A8", params) == registry.info_class("A8", {}) == "online-I1 + a-priori N"
    assert rec["info_class"] == "online-I1 + a-priori N"
    assert rec["info_class_reported"] == m4.INFO_CLASS_REPORTED == "online-I1 + a-priori N + a-priori BL0a"
    cert = rec["certificate"]
    assert cert["available"] and "ALG_per_slot" not in cert
    assert rec["certificate_case"] in m4.CASES and rec["certificate_case"] != "unavailable"
    assert (rec["t_a"], rec["aborted"]) == (rep["t_a"], rep["aborted"])
    full, case = m4.certify(res, inst)
    assert case == rec["certificate_case"] and len(full["ALG_per_slot"]) == inst.grid.T_slow
    assert {k: v for k, v in full.items() if k != "ALG_per_slot"} == cert
    assert len(m4.a8_record(res, inst, params, per_slot=True)["certificate"]["ALG_per_slot"]) == inst.grid.T_slow
    json.dumps(mc.jsonable(rec), allow_nan=False)


def test_theory_params_keep_the_defaults():
    """theory_params: A8 resolves B0 'auto' (guard.b0_auto) and kappa 10; the record says 'auto, kappa 10' and adds
    no BL0a to the information class."""
    params = m4.theory_params("BL5")
    inst, model, pol, res = _a8_run("toy.json", params)
    rp = pol.params()
    assert (rp["B0"], rp["kappa"], rp["gamma"]) == ("auto", 10.0, 1.0)
    rec = m4.a8_record(res, inst, params, model.information)
    auto = b0_auto(public_view(inst, "I1"))
    assert (rec["B0_rule"], rec["kappa"], rec["gamma"]) == (m4.THEORY_RULE, 10.0, 1.0) == ("auto, kappa 10", 10.0, 1.0)
    assert rec["B0_usd"] == auto == rec["B0_report_usd"] == res.metrics["policy"]["B0"]
    assert rec["info_class_reported"] == rec["info_class"] == "online-I1 + a-priori N"


def test_allowance_rules_of_the_sweep():
    """The sweep's shares give '<share>*BL0a' (B0 to 1e-12); another number gives 'constant'; auto with kappa None
    names it; info_class_reported adds BL0a only for a share rule."""
    inst = toy_instance()
    bl0a = bl0a_all(inst)
    for s in (0.0025, 0.005, 0.01, 0.02, 0.05):
        r = m4.allowance_record(m4.sublet_params(inst, share=s), inst)
        assert r["B0_rule"] == f"{s:g}*BL0a" and r["B0_usd"] == s * bl0a and r["kappa"] is None
    r = m4.allowance_record({"inner": "BL5", "B0": 0.123456789, "kappa": None}, inst)
    assert (r["B0_rule"], r["B0_usd"]) == (m4.CONSTANT_RULE, 0.123456789)
    assert m4.allowance_record({"inner": "BL5", "kappa": None}, inst)["B0_rule"] == "auto, kappa None"
    r = m4.allowance_record({"inner": "BL5", "B0": 0.02 * bl0a, "kappa": 30.0}, inst)    # M36 alternative (d)
    assert (r["B0_rule"], r["kappa"]) == ("0.02*BL0a", 30.0)
    base = "online-I1 + a-priori N"
    assert m4.info_class_reported(base, "0.005*BL0a") == base + " + a-priori BL0a"
    assert m4.info_class_reported(base, m4.CONSTANT_RULE) == m4.info_class_reported(base, m4.THEORY_RULE) == base
    assert m4.info_class_reported(base + " + a-priori BL0a", "0.02*BL0a") == base + " + a-priori BL0a"


def test_count_certificates_by_hand():
    """n, held, by_case {runs, held} and the failures (proven case, not held); W(c) and unavailable counted."""
    recs = [{"certificate": {"held": True}, "certificate_case": "W(a)"},
            {"certificate": {"held": True}, "certificate_case": "W(a)"},
            {"certificate": {"held": False}, "certificate_case": "W(b)"},
            {"certificate": {"held": False}, "certificate_case": "W(c)"},
            {"certificate": {"available": False, "held": None}, "certificate_case": "unavailable"}]
    c = m4.count_certificates(recs)
    assert (c["n"], c["held"], c["failures"]) == (5, 2, 1)
    assert c["by_case"] == {"W(a)": {"runs": 2, "held": 2}, "W(b)": {"runs": 1, "held": 0},
                            "W(c)": {"runs": 1, "held": 0}, "unavailable": {"runs": 1, "held": 0}}
    assert m4.count_certificates([]) == {"n": 0, "held": 0, "failures": 0,
                                         "by_case": {k: {"runs": 0, "held": 0} for k in m4.CASES}}
    with pytest.raises(ValueError):
        m4.count_certificates([{"certificate": {}, "certificate_case": "W(d)"}])


def test_allowance_need_on_the_toy():
    """need_params' run executes BL5 unchanged (same total, no abort); allowance_need's need is max(0, max_t [a-hat +
    R - gamma C_S]) of its guard series; a run at B0 = need does not abort, and at a smaller B0 it aborts exactly at
    t_a_at_B0 (oracle: the A8 runs themselves); an aborted run and a run without a guard raise."""
    params = m4.need_params("BL5")
    assert params == {"inner": "BL5", "gamma": 1.0, "kappa": None, "B0": m4.NEED_B0}
    with pytest.raises(ValueError):
        m4.need_params("BL2")
    inst, model, pol, res = _a8_run("toy.json", params)
    spec = _spec("toy.json", "BL5")
    bl5 = simulate(inst, make_policy(spec, inst), model, build(spec, 1)[2], lender_seed=1, policy_seed=0)
    assert res.metrics["policy"]["t_a"] is None
    assert_rel(res.components["total"], bl5.components["total"], 1e-12, "A8 with need_params vs BL5")
    g = res.metrics["policy"]["guard"]
    exc = [a + r - c for a, r, c in zip(g["a_hat"], g["reserve"], g["C_S"])]
    need = m4.allowance_need(res)
    assert need["need_usd"] == max(exc) > 0 and need["need_slot"] == g["slots"][int(np.argmax(exc))]
    assert (need["gamma"], need["n_slots"]) == (1.0, inst.grid.T_slow)
    assert m4.allowance_need(res, gamma=1e6)["need_usd"] == 0.0          # gamma C_S covers every slot
    for b0 in (need["need_usd"], 0.5 * need["need_usd"], 0.1 * need["need_usd"]):
        pred = m4.allowance_need(res, b0=b0)
        _, _, _, r = _a8_run("toy.json", {"inner": "BL5", "gamma": 1.0, "kappa": None, "B0": b0})
        assert r.metrics["policy"]["t_a"] == pred["t_a_at_B0"], b0
        assert pred["B0_usd"] == b0 and pred["margin_usd"] == b0 - need["need_usd"]
        if b0 == need["need_usd"]:
            assert pred["t_a_at_B0"] is None
        else:
            assert pred["t_a_at_B0"] is not None
            with pytest.raises(ValueError):
                m4.allowance_need(r)
    with pytest.raises(ValueError):
        m4.allowance_need(bl5)


# ---------------------------------------------------------------- both accountings (Q32, M2)
def test_accountings_on_a_toy_run():
    """total_usd - overflow_usd = own_capacity_usd to 1e-9; the ratios by hand; BL0b equals provision.bl0b_usd in both
    accountings; BL0a's total-accounting cost is BL0a + own capacity (E7-4); refs given or not, the same fields."""
    inst = toy_instance()
    inst.borrower_stats = {"b0": {"llm": 0, "C0_loads": 1.5, "peak_loads": 4.0}}
    spec = _spec("toy.json", "BL5")
    _, model, ecfg = build(spec, 1)
    res = simulate(inst, make_policy(spec, inst), model, ecfg, lender_seed=1, policy_seed=0)
    x = float(res.components["total"])
    own = provision.own_capacity_usd(inst)
    assert_rel(own, 1.5 * 5.97 * inst.grid.horizon_min / 60.0, 1e-12, "own capacity")
    refs = m4.references(inst)
    bl0a, b_over, b_tot = bl0a_all(inst), provision.bl0b_usd(inst), provision.bl0b_usd(inst, accounting="total")
    assert (refs["bl0a_usd"], refs["own_capacity_usd"], refs["bl0b_overflow_usd"], refs["bl0b_total_usd"]) == \
        (bl0a, own, b_over, b_tot)
    assert refs["committed_price_usd_per_gpu_h"] == 5.97 and refs["bl0a_total_usd"] == bl0a + own
    a = m4.accountings(x, inst)
    assert a == m4.accountings(x, inst, refs=refs)
    assert set(a) == {"overflow_usd", "total_usd", "overflow_over_bl0a", "total_over_bl0a", "own_share_of_total",
                      "overflow_over_bl0b", "total_over_bl0b"}
    assert abs((a["total_usd"] - a["overflow_usd"]) - own) <= 1e-9 * max(1.0, own)
    assert a["overflow_usd"] == x
    assert_rel(a["overflow_over_bl0a"], x / bl0a, 1e-12, "overflow / BL0a")
    assert_rel(a["total_over_bl0a"], (x + own) / (bl0a + own), 1e-12, "total / (BL0a + own)")
    assert_rel(a["own_share_of_total"], own / (x + own), 1e-12, "own share")
    assert_rel(a["overflow_over_bl0b"] * b_over, x, 1e-12, "BL0b, overflow accounting")
    assert_rel(a["total_over_bl0b"] * b_tot, x + own, 1e-12, "BL0b, total accounting")
    b = m4.accountings(bl0a, inst)
    assert_rel(b["total_usd"], refs["bl0a_total_usd"], 1e-12, "BL0a in total accounting")
    assert b["overflow_over_bl0a"] == 1.0 and b["total_over_bl0a"] == 1.0
    json.dumps(mc.jsonable(a), allow_nan=False)


def test_accountings_null_forms():
    """An instance without borrower_stats: own capacity and BL0b are null with notes, the total-accounting fields
    too, the overflow fields stay; a non-finite cost raises."""
    inst = toy_instance()
    refs = m4.references(inst)
    for k in ("own_capacity_usd", "bl0b_overflow_usd", "bl0b_total_usd", "bl0a_total_usd"):
        assert refs[k] is None and refs[f"{k}_note"]
    assert refs["bl0a_usd"] == bl0a_all(inst) and refs["committed_price_usd_per_gpu_h"] == 5.97
    a = m4.accountings(10.0, inst)
    assert a["overflow_usd"] == 10.0 and a["overflow_over_bl0a"] == 10.0 / bl0a_all(inst)
    for k in ("total_usd", "total_over_bl0a", "own_share_of_total", "overflow_over_bl0b", "total_over_bl0b"):
        assert a[k] is None and a[f"{k}_note"], k
    json.dumps(mc.jsonable(a), allow_nan=False)
    for bad in (float("nan"), float("inf"), None, True):
        with pytest.raises(ValueError):
            m4.accountings(bad, inst)


# ---------------------------------------------------------------- W0 (note §5.5)
def test_w0_one_cell():
    """E7's one cell: W0 = the maximum over the five stress modes of the 3-seed mean of r0, with its mode and the seed
    range of that mode."""
    r0 = {"L-eg": [1.02, 1.01, 1.03], "L-ss": [1.05, 1.00, 1.04], "L-iid-0.05": [0.70, 0.71, 0.72],
          "L-iid-0.2": [0.84, 0.85, 0.83], "L-co": [1.01, 1.02, 1.00]}
    cells = {m: {"c1": {p: v for p, v in enumerate(vals)}} for m, vals in r0.items()}
    w = m4.w0(cells)
    means = {m: float(np.mean(v)) for m, v in r0.items()}
    best = max(means, key=means.get)
    assert best == "L-ss" and w["mode"] == best and w["value"] == means[best]
    assert w["seed_range"] == [1.00, 1.05] and w["modes_missing"] == [] and w["expected"] == list(STRESS)
    assert m4.stress_modes() == STRESS
    assert {m: w["per_mode"][m]["value"] for m in STRESS} == means
    assert all(w["per_mode"][m]["n_cells"] == 1 and w["per_mode"][m]["n_runs"] == 3 for m in STRESS)
    assert m4.w0({m: {"c1": list(v)} for m, v in r0.items()})["value"] == w["value"]     # lists as cells
    json.dumps(mc.jsonable(w), allow_nan=False)


def test_w0_cells_missing_runs_and_modes():
    """The median over cells of the per-cell seed means; a None r0 is left out and counted; a tie keeps the first mode
    in the given order; a mode without r0 leaves value null with value_partial; L-tr and NaN raise."""
    w = m4.w0({"L-eg": {"c1": [1.0, 1.2], "c2": [2.0], "c3": [0.5, None, 0.7]}}, expected=("L-eg",))
    assert w["value"] == pytest.approx(1.1, abs=1e-12) and w["mode"] == "L-eg"
    assert w["per_mode"]["L-eg"]["n_missing"] == 1 and w["per_mode"]["L-eg"]["n_runs"] == 5
    assert w["seed_range"] == [0.5, 2.0] and w["expected"] == ["L-eg"]
    assert m4.w0({"L-ss": {"c": [1.0]}, "L-eg": {"c": [1.0]}}, expected=("L-eg", "L-ss"))["mode"] == "L-ss"
    w = m4.w0({"L-eg": {"c1": [1.1]}, "L-ss": {"c1": [None, None]}}, expected=("L-eg", "L-ss"))
    assert w["value"] is None and w["value_note"] and w["value_partial"] == 1.1 and w["modes_missing"] == ["L-ss"]
    assert w["per_mode"]["L-ss"]["value"] is None and w["per_mode"]["L-ss"]["n_missing"] == 2
    json.dumps(mc.jsonable(w), allow_nan=False)
    with pytest.raises(ValueError):
        m4.w0({"L-tr": {"c1": [0.68]}})
    with pytest.raises(ValueError):
        m4.w0({"L-eg": {"c1": [float("nan")]}})


def test_w0_needs_every_expected_mode():
    """By default W0 covers the five stress modes: a mode left out of the input (its job failed) makes W0 null with
    value_partial and a null-form row, so W0 over four modes is never reported; a misspelled or unknown mode key, a
    non-stress mode and a stress mode outside `expected` raise, as does an `expected` naming a non-stress mode."""
    cells = {m: {"c1": [1.0, 1.0, 1.0]} for m in STRESS}
    cells["L-co"] = {"c1": [1.3, 1.3, 1.3]}
    assert (m4.w0(cells)["value"], m4.w0(cells)["mode"]) == (1.3, "L-co")
    four = {m: v for m, v in cells.items() if m != "L-co"}
    w = m4.w0(four)
    assert w["value"] is None and w["value_note"] and w["modes_missing"] == ["L-co"]
    assert w["value_partial"] == 1.0 and w["mode"] == "L-eg"
    assert w["per_mode"]["L-co"]["value"] is None and w["per_mode"]["L-co"]["value_note"]
    assert set(w["per_mode"]["L-co"]) == set(w["per_mode"]["L-eg"]) | {"value_note"}
    json.dumps(mc.jsonable(w), allow_nan=False)
    assert m4.w0(four, expected=[m for m in STRESS if m != "L-co"])["value"] == 1.0
    for bad in ({**four, "L-cO": cells["L-co"]}, {**cells, "L-xx": {"c1": [2.0]}}, {**cells, "L-tr": {"c1": [0.7]}}):
        with pytest.raises(ValueError):
            m4.w0(bad)
    with pytest.raises(ValueError):
        m4.w0(cells, expected=("L-eg", "L-ss"))
    for exp in (("L-eg", "L-tr"), ()):
        with pytest.raises(ValueError):
            m4.w0({"L-eg": cells["L-eg"]}, expected=exp)


# ---------------------------------------------------------------- siloed runs (§2.2, §4.5)
def test_siloed_run_sublet_two_borrowers(tmp_path):
    """A 2-hour siloed Sublet run: one sub-run per borrower, each with its own B0 = 2% of its sub-instance's BL0a,
    allowance B0 at every slot, a certificate and an allowance record; the counts by case; the summed components
    equal the sub-runs' sum (E3-3); BL2 through siloed_run equals drivers/run.run's siloed path."""
    cfg = _two_borrowers()
    spec = _spec(cfg, "SILOED", {"inner": "A8", "inner_params": {"inner": "BL5"}})
    inst, model, ecfg = build(spec, 1)
    assert inst.grid.horizon_min == 120 and inst.n == 2
    d = m4.siloed_run(inst, spec, model, ecfg, 1, 0, params_of=m4.sublet_params)
    assert d["inner_id"] == "A8" and d["borrowers"] == ["b0", "b1"] and len(d["sub_runs"]) == 2
    for row, res, sub in zip(d["sub_runs"], d["results"], d["instances"]):
        B0 = m4.B0_SHARE * bl0a_all(sub)
        assert row["params"] == {"inner": "BL5", "gamma": 1.0, "kappa": None, "B0": B0}
        assert (row["B0_rule"], row["B0_usd"], row["bl0a_usd"], row["B0_report_usd"]) == \
            (m4.B0_RULE, B0, bl0a_all(sub), B0)
        assert row["info_class_reported"] == m4.INFO_CLASS_REPORTED
        assert all(b == B0 for b in res.metrics["policy"]["safe"]["B_curve"])
        assert row["certificate"]["available"] and row["certificate_case"] in m4.CASES
        assert row["total"] == res.components["total"] and row["n_invariant_failures"] == 0
        assert row["gpu_only_lease_slots"] == 0
    assert d["sub_runs"][0]["B0_usd"] != d["sub_runs"][1]["B0_usd"]
    cnt = d["certificates"]
    assert cnt["n"] == 2 and sum(v["runs"] for v in cnt["by_case"].values()) == 2
    assert cnt == m4.count_certificates(d["sub_runs"]) and cnt["failures"] == 0
    for k, v in d["components"].items():
        assert_rel(v, sum(r["components"][k] for r in d["sub_runs"]), 1e-9, f"component {k}")
    assert_rel(d["total"], sum(r["total"] for r in d["sub_runs"]), 1e-9, "total")
    json.dumps(mc.jsonable(d["sub_runs"]), allow_nan=False)
    # BL2 with fixed parameters, as drivers/run.run builds each sub-policy
    spec2 = _spec(cfg, "BL2", {}, name="t_ms4_bl2")
    d2 = m4.siloed_run(inst, spec2, model, ecfg, 1, 0)
    ref = run(spec2, out_dir=tmp_path)[0]
    assert d2["inner_id"] == "BL2" and d2["certificates"] is None
    assert d2["components"] == ref["components"] and "B0_rule" not in d2["sub_runs"][0]


# ---------------------------------------------------------------- benchmark sums (§2.5)
def _bench(lp, milp_obj=None, dual=None, status=1, grid="slow"):
    milp = {"status": status, "grid": grid}
    if milp_obj is not None:
        milp.update(objective=milp_obj, dual_bound=dual, gap=(milp_obj - dual) / milp_obj)
    return mc.bench_values({"status": 0, "objective": lp, "grid": grid}, milp)


def test_sum_bench_and_bracket():
    """incumbent and LB summed (an empty part adds 0), exact iff every part is exact, the largest gap, the LB
    sources; bracket(siloed sum, shared) by hand; a killed MILP part leaves the incumbent, point and hi null."""
    a = _bench(10.0, 12.0, 11.0)                 # LB 11 (dual), incumbent 12, gap 1/12
    b = _bench(5.0, 5.0, 5.0, status=0)          # exact: LB 5 (the LP's, a tie), incumbent 5
    s = m4.sum_bench([a, None, b, {"empty": True}])
    assert (s["incumbent"], s["LB"], s["exact"], s["gap"]) == (17.0, 16.0, False, 1.0 / 12.0)
    assert (s["n_parts"], s["n_empty"], s["grid"]) == (4, 2, "slow")
    assert s["LB_sources"] == {"milp_dual": 1, "lp": 1}
    shared = _bench(14.0, 15.0, 14.5)
    br = mc.bracket(s, shared)
    assert (br["point"], br["lo"], br["hi"], br["exact"]) == (17.0 / 15.0, 16.0 / 15.0, 17.0 / 14.5, False)
    ex = m4.sum_bench([b, None])
    assert (ex["incumbent"], ex["LB"], ex["exact"]) == (5.0, 5.0, True)
    assert mc.bracket(ex, _bench(4.0, 4.0, 4.0, status=0))["exact"] is True
    empty = m4.sum_bench([None, {"empty": True}])
    assert (empty["incumbent"], empty["LB"], empty["exact"], empty["gap"]) == (0.0, 0.0, True, None)
    assert empty["gap_note"]
    killed = mc.bench_values({"status": 0, "objective": 9.0, "grid": "slow"}, {"status": "wall_limit"})
    k = m4.sum_bench([a, killed])
    assert k["incumbent"] is None and k["incumbent_note"] and k["LB"] == 20.0 and k["exact"] is False
    assert k["parts_without_incumbent"] == [1]
    bk = mc.bracket(k, shared)
    assert bk["point"] is None and bk["hi"] is None and bk["lo"] == 20.0 / 15.0
    json.dumps(mc.jsonable(s), allow_nan=False)
    with pytest.raises(ValueError):
        m4.sum_bench([a, _bench(1.0, 1.0, 1.0, grid="fast")])
    with pytest.raises(TypeError):
        m4.sum_bench([a, 3.0])


# ---------------------------------------------------------------- instance builders (§3.4, §3.7)
def test_e7r_h5_overrides():
    """The substitution of Q44's block Q4 (instance I2-H5), the slow grid of q44_study.GRIDS and mu = 1: the overrides
    that measurement 3 recorded (e7r_h5_lp_estimate.json)."""
    block = json.loads((q44.BLOCKS_DIR / "Q4.json").read_text())
    q4 = next(i for i in block["instances"] if i["id"] == "I2-H5")
    assert q4["overrides"] == m4.H5_OVERRIDES
    ov = m4.e7r_h5_overrides()
    assert ov == {"time.horizon_min": 1440, "time.fast_slot_min": 5, "stranding.mu_over_beta_tilde": 1.0,
                  **m4.H5_OVERRIDES}
    assert q44.GRIDS["slow"] == {"time.fast_slot_min": 5}
    assert ov == json.loads(GAP_ESTIMATE.read_text())["overrides"]
    spec = m4.e7r_h5_spec("BL0a")
    assert (spec["instance"], spec["engine"], spec["lender_model"]) == \
        ("bench_e7r.json", {"check_invariants": True}, {})
    assert spec["overrides"] == ov and m4.e7r_h5_overrides(120)["time.horizon_min"] == 120


def test_routing_overrides():
    """M1 (b): n = 0, 2, 3 are nested subgraphs of the default adjacency S7 on the config's five regions; n = 5 is the
    config's S7 (no override, the main grid); other n raise."""
    cfg = json.loads((SIM / "configs" / "bench_e7f.json").read_text())
    assert len(cfg["regions"]["list"]) == 5 and "adjacency" not in cfg["regions"]
    assert m4.routing_overrides(5) == {} and m4.ROUTING_LINKS[5] is None
    s7 = {frozenset(e) for e in DEFAULT_ADJACENCY}
    prev = set()
    for n in (0, 2, 3):
        adj = m4.routing_overrides(n)["regions.adjacency"]
        links = {frozenset(e) for e in adj}
        assert len(adj) == len(links) == n and links <= s7 and prev <= links
        assert all(x in cfg["regions"]["list"] for e in adj for x in e)
        prev = links
    for bad in (1, 4, 6, True, 2.0):
        with pytest.raises(ValueError):
            m4.routing_overrides(bad)


def test_e7_spec():
    """bench_e7f.json with time.horizon_min 10080, stranding.mu_over_beta_tilde and engine.check_invariants true: the
    run spec that measurement 1 recorded (e7f_week_case_Sublet.json, but its name and out); the mu points, the routing
    overrides and a stress mode's lender model; an override of the horizon or mu raises."""
    rec = json.loads(WEEK_CASE.read_text())["run_spec"]
    spec = m4.e7_spec("A8", {"inner": "BL5"}, name=rec["name"])
    assert {k: v for k, v in spec.items() if k != "out"} == {k: v for k, v in rec.items() if k != "out"}
    s = m4.e7_spec("BL5", mu=0.5, overrides=m4.routing_overrides(2), lender_model=m4.mode_lender_model("L-ss"))
    assert s["overrides"] == {"time.horizon_min": 10080, "stranding.mu_over_beta_tilde": 0.5,
                              "regions.adjacency": [["north_america", "south_america"],
                                                    ["east_asia", "south_southeast_asia"]]}
    assert s["lender_model"] == q44.MODES["L-ss"]["lender_model"] and s["engine"] == {"check_invariants": True}
    assert m4.mode_lender_model("L-tr") == {}
    with pytest.raises(ValueError):
        m4.mode_lender_model("L-xx")
    with pytest.raises(ValueError):
        m4.e7_spec("BL5", overrides={"time.horizon_min": 1440})


@pytest.mark.needs_a12
def test_e7_week_instance_and_routing_graphs():
    """e7_spec builds measurement 1's week instance at alignment 1 (169 sites: 164 layer, 5 protected; 21 contracts;
    15 clients; T_slow 2016; its references to 1e-9); the routing graphs n = 0, 2, 3 keep its sites, clients, demand
    and BL0a, and their cross-region arcs are exactly the n links (measurement 9's cross_region_arcs)."""
    recd = json.loads(WEEK_CASE.read_text())
    inst = build(m4.e7_spec("BL0a"), 1)[0]
    kinds = [s.kind for s in inst.sites]
    assert (inst.m, kinds.count("layer"), kinds.count("protected"), inst.K, inst.n) == (169, 164, 5, 21, 15)
    assert (inst.grid.T_slow, inst.grid.T_fast, inst.grid.horizon_min) == (2016, 10080, 10080)
    refs, want = m4.references(inst), recd["references"]
    for k, w in (("bl0a_usd", "bl0a_analytic_usd"), ("own_capacity_usd", "own_capacity_usd"),
                 ("bl0b_overflow_usd", "bl0b_overflow_usd"), ("bl0b_total_usd", "bl0b_total_usd")):
        assert_rel(refs[k], want[w], 1e-9, k)
    def arcs(x):
        d = np.asarray(x.clients.delta_usd_per_h)
        return {frozenset((x.clients.region[c], x.sites[k].region)) for c, k in zip(*np.nonzero(np.isfinite(d)))
                if x.clients.region[c] != x.sites[k].region}
    assert arcs(inst) == {frozenset(e) for e in DEFAULT_ADJACENCY}
    for n in (0, 2, 3):
        sub = build(m4.e7_spec("BL0a", overrides=m4.routing_overrides(n)), 1)[0]
        assert [(s.id, s.region, s.capacity_gpus) for s in sub.sites] == \
            [(s.id, s.region, s.capacity_gpus) for s in inst.sites]
        assert sub.regions == inst.regions and sub.clients.region == inst.clients.region
        assert np.array_equal(sub.clients.demand, inst.clients.demand) and bl0a_all(sub) == bl0a_all(inst)
        assert arcs(sub) == {frozenset(e) for e in m4.ROUTING_LINKS[n]}


@pytest.mark.needs_a12
def test_gap_instance_reproduces_measurement_3():
    """gap_instance(1): measurement 3's e7week rerun instance (e7r_h5_lp_runs_e7week.json: instance hash, demand sha256,
    BL0a under both demands; 173 sites, the e7r + H5 contracts, 15 clients, 288 slow slots on the slow grid), the week
    instance's borrower_stats, ratio_validity None; BL0a's engine run equals e6.bl0a_all and has the LP record's
    schedule hash (e7r_h5_lp_lp_e7week.json); a second call gives the same instance hash."""
    rec, lp = json.loads(GAP_RUNS.read_text()), json.loads(GAP_LP.read_text())
    inst, model, ecfg, info = m4.gap_instance(1)
    h = q44.instance_hash(inst)
    assert h == rec["instance_hash"] == lp["instance_hash"]
    assert info["demand_sha256"] == rec["instance_info"]["demand_sha256"]
    assert info["own_demand_sha256"] == rec["instance_info"]["own_demand_sha256"]
    assert_rel(info["bl0a_usd"], rec["instance_info"]["bl0a_usd"], 1e-12, "BL0a, carried demand")
    assert_rel(info["bl0a_own_demand"], rec["instance_info"]["bl0a_own_demand_usd"], 1e-12, "BL0a, own demand")
    assert info["start_mow_equal"] and info["bl0a_usd"] == bl0a_all(inst)
    assert (inst.m, inst.n, inst.grid.T_slow, inst.grid.fast_min) == (173, 15, 288, 5)
    assert [c.id for c in inst.contracts] == ["s5_tau5_H5", "s5_tau5_H60", "s5_tau60_H0", "protected"]
    wk = build(m4.e7_spec("BL0a"), 1)[0]
    assert inst.borrower_stats == wk.borrower_stats
    assert ratio_validity("slow", inst, model) is None and ecfg.check_invariants
    res = simulate(inst, AlwaysFallback(), model, ecfg, lender_seed=1, policy_seed=0)
    assert_rel(res.components["total"], bl0a_all(inst), 1e-9, "BL0a engine vs analytic (E7-5)")
    assert q44.schedule_hash(res.schedule) == lp["schedule"]["hash"]
    assert q44.instance_hash(m4.gap_instance(1)[0]) == h
