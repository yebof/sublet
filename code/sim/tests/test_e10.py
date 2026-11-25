"""Tests of the E10 driver sublet/experiments/e10.py (design/sim_spec_ms3.md §5, §10 row test_e10.py).

- E10-1 at m in {2, 4}, rho in {2, 16}: the R2 path (repro_c4_lower.part_a_row) reproduces c3/out/c4_lower.json
  `a` (rr, stay, pd_r1, pd_r1_min, pd_rth, pd_rth_min, LB_T) to 1e-9.
- The LB_T formula of C3-T4 equals c4_lower.json a[*].LB_T at every listed point (T = 48).
- The O1-B check function: it holds on RR-renew runs under 'adaptive' and 'safe_site' and fails on an ALG above
  the bound.
- OPT = Phi beta + a T under 'safe_site' at m = 8, k = 8 (rho = 16; check E10-4) on every drawn schedule.
- value_public on hand-made run sets: the best tag of each class, the ratio of means, and a paired bootstrap (an
  exactly proportional pair has a degenerate interval).
- bounds at m = 32 (not listed in o1_lb.json) equal o1_lb.lb_A and lb_C called through C11 (k* 21, p* 0.46 at
  rho = 16); a listed point reads o1_lb.json; m = 2 has k = 2 and LB_A null.
- E10-5 / E10-6 flags on synthetic aggregates; the job list counts and ids; a flagged e10:a output adds its
  e10:rerun job to the list, and the rerun evaluates the check on all seeds.
- needs_a12: general_core builds valid instances at m = 2 and seeds s, s + 5 give the same instance; the trace
  omega of configs/ms3_e10b_trace.json has one site per lender for the 16 lenders and that config is
  example_1day.json with the changes of §5.4 only.
"""
import json

import numpy as np
import pytest

from fixtures import SIM

from sublet.experiments import e10
from sublet.experiments import ms3_common as mc
from sublet.paths import import_ref

C3_OUT = SIM.parents[1] / "code" / "theory_checks" / "c3" / "out"


def test_e10_1_reproduces_c4_lower_a():
    rows = e10.repro_rows([(2, 2.0), (2, 16.0), (4, 2.0), (4, 16.0)])
    assert len(rows) == 4
    for r in rows:
        assert r["ref"] is not None and r["pass"], r["diff"]
        assert max(r["diff"].values()) <= 1e-9


def test_lb_T_formula_equals_c4_lower():
    ref = json.loads((C3_OUT / "c4_lower.json").read_text())["a"]
    assert len(ref) == 16
    for x in ref:
        assert e10.lb_T(float(x["rho"]), int(x["m"]), 48) == pytest.approx(x["LB_T"], abs=1e-12)
    # its T -> infinity limit is rho m / (m + rho - 1)
    assert e10.lb_T(16.0, 8, 3 * 10 ** 7) == pytest.approx(16 * 8 / 23, rel=1e-6)


def test_o1b_check_on_rr_renew_runs():
    from sublet.drivers.bench import bench_for
    fam = import_ref("fam")
    for sched, params, T in (("adaptive", {}, 48), ("safe_site", {"D_slots": 3, "k": 4, "Phi": 4}, 48)):
        F = fam.Fam(4, 16.0, 2, 1, T)
        for s in (0, 1):
            res, inst = e10.fam_run(F, sched, params, "RR", s, s)
            opt = float(bench_for(res, inst, "fam", fam=F).objective)
            alg = float(res.components["total"])
            assert e10.o1b_ok(alg, 16.0, 4, T, opt)
            assert alg <= e10.o1b_bound(16.0, 4, T, opt) * (1 + 1e-9)
    assert not e10.o1b_ok(101.0, 16.0, 4, 48, 10.0)       # min{16 (1 + 3/48) 10, 8 10 + 3} = 83
    assert e10.o1b_bound(16.0, 4, 48, 10.0) == pytest.approx(83.0)


def test_safe_site_opt_closed_form_m8_k8():
    pt = e10.point("safe_site", 16.0, 8)
    assert pt["k_star"] == 8 and pt["Phi"] == 25 and pt["T"] == 600        # o1_lb.json: k* = 8 at rho 16, m 8
    errs: list = []
    rows = e10.run_point(pt, ("RR",), range(3), errs, "test")
    assert not errs and len(rows) == 3
    for r in rows:
        assert r["OPT"] == pytest.approx(pt["Phi"] * pt["beta"] + pt["T"], abs=1e-9)
        assert r["E10_4_ok"] and r["E10_3_ok"] and r["n_invariant_failures"] == 0
    assert len({r["schedule_hash"] for r in rows}) == 3                    # one schedule per lender seed


def test_value_public_hand_made():
    by = {"RR": {0: 10.0, 1: 12.0, 2: 14.0}, "A2-th": {0: 20.0, 1: 22.0, 2: 24.0}, "MARK": {0: 5.0, 1: 6.0, 2: 7.0}}
    v = e10.value_public(by)
    assert (v["best_private"], v["best_public"], v["n_pairs"]) == ("RR", "MARK", 3)
    assert v["ratio"] == pytest.approx(2.0) and v["mean_private"] == 12.0 and v["mean_public"] == 6.0
    assert v["ci95"][0] == pytest.approx(2.0) and v["ci95"][1] == pytest.approx(2.0)   # every pair has ratio 2
    # pairing: the costs vary a lot across seeds but each pair keeps ratio 3; an unpaired resample would not
    v2 = e10.value_public({"A2-th": {0: 3.0, 1: 300.0}, "RR": {0: 6.0, 1: 600.0}, "MARK": {0: 1.0, 1: 100.0}})
    assert v2["best_private"] == "A2-th" and v2["ratio"] == pytest.approx(3.0)
    assert v2["ci95"] == pytest.approx([3.0, 3.0])
    # the interval resamples seeds: a hand computation with the same generator
    by3 = {"RR": {0: 4.0, 1: 9.0, 2: 5.0, 3: 7.0}, "MARK": {0: 2.0, 1: 3.0, 2: 4.0, 3: 2.0}}
    v3 = e10.value_public(by3, B=500, seed=3)
    a, b = np.array([4.0, 9.0, 5.0, 7.0]), np.array([2.0, 3.0, 4.0, 2.0])
    idx = np.random.default_rng(3).integers(0, 4, size=(500, 4))
    lo, hi = np.percentile(a[idx].sum(axis=1) / b[idx].sum(axis=1), [2.5, 97.5])
    assert v3["ratio"] == pytest.approx(25.0 / 11.0) and v3["ci95"] == pytest.approx([lo, hi])
    v4 = e10.value_public({"RR": {0: 1.0}})
    assert v4["ratio"] is None and "ratio_note" in v4


def test_bounds_m32_and_listed_points():
    o1 = import_ref("o1_lb")
    e = e10.bounds_entry(16.0, 32, None)
    la, k = o1.lb_A(16, 32)
    lc, p = o1.lb_C(16, 32)
    assert (e["k_star"], k) == (21, 21) and e["LB_A"] == la and e["source"]["k_star"] == "o1_lb.lb_A (C11)"
    assert e["p_star"] == p and e["p_star"] == pytest.approx(0.46) and e["LB_C_max"] == lc
    assert e["Phi"] == max(2, 600 // (21 * 3)) and e["T_safe_site"] == e["Phi"] * 21 * 3
    assert e["limit"] == pytest.approx(16 * 32 / 47) and e["LB_T"] == pytest.approx(e10.lb_T(16.0, 32, 16 * 32 * 3))
    assert e["O1B_adaptive"] is None and "O1B_adaptive_note" in e
    row = next(r for r in json.loads((C3_OUT.parent / "o1" / "out" / "o1_lb.json").read_text())["A"]
               if r["rho"] == 16 and r["m"] == "8")
    e8 = e10.bounds_entry(16.0, 8, {"opt": 100.0})
    assert (e8["k_star"], e8["LB_A"], e8["p_star"], e8["LB_C_max"]) == (row["k"], row["LB_A"], row["p"], row["LB_C"])
    assert e8["source"]["k_star"] == "o1_lb.json A"
    assert e8["O1B_adaptive"] == pytest.approx(min(16 * (1 + 3 / 384), 16 + 3 / 100.0))
    assert e8["two_h_m_plus_1"] == pytest.approx(2 * sum(1 / i for i in range(1, 9)) + 1)
    e2 = e10.bounds_entry(16.0, 2, None)
    assert e2["k_star"] == 2 and e2["LB_A"] is None and "LB_A_note" in e2


def test_flags_and_job_list(monkeypatch):
    pt = e10.point("safe_site", 16.0, 8)
    aggs = {"RR": {"ci95": [1.0, pt["LB_A"] - 0.1]}, "A2-th": {"ci95": [3.0, 40.0]},
            "MARK": {"ci95": [pt["two_h_m_plus_1"] + 0.5, 9.0]}}
    fl = e10.flags(pt, aggs)
    assert set(fl) == {"RR", "MARK"} and fl["RR"]["check"] == "E10-5" and fl["MARK"]["check"] == "E10-6"
    assert e10.flags(e10.point("safe_site", 16.0, 2), {"RR": {"ci95": [0.0, 0.5]}}) == {}    # O1-A needs m >= 3
    monkeypatch.delenv(e10.REDUCED_ENV, raising=False)
    monkeypatch.setenv("MS3_OUT", str(SIM / "out" / "e10_not_there"))
    js = e10.jobs()
    mc.check_jobs(js)
    parts = [mc.parse_job_id(j.id)[1] for j in js]
    assert parts.count("a") == 54 and parts.count("b") == 8 and parts.count("repro") == 1
    assert parts.count("b_milp") == 120 and parts.count("rerun") == 0
    assert all(j.kind == "milp" for j in js if ":b_milp:" in j.id)
    n_a = sum(len(e10.seed_pairs(j.params["sched"], t, range(30))) for j in js if ":a:" in j.id
              for t in e10.SCHED_TAGS[j.params["sched"]])
    assert n_a == 1638 + 3240                                  # §11.1
    monkeypatch.setenv(e10.REDUCED_ENV, "1")
    pr = [mc.parse_job_id(j.id)[1] for j in e10.jobs()]
    assert pr.count("a") == 27 and pr.count("b") == 4 and pr.count("b_milp") == 16


@pytest.mark.needs_a12
def test_general_core_valid_and_seed_pairs():
    from sublet.instance import from_core
    I = e10.general_core(2, 4.0, e10.E2_SERIES[0])
    assert I.T == 288 and I.a.shape == (2, 1) and list(I.g) == [1, 2]
    assert np.allclose(I.beta, [[9.0, 9.0], [18.0, 18.0]]) and I.q == pytest.approx(18.0 + 6.0 + 1.0)
    assert list(I.cl_llm) == [0, 1, 0, 1, 0, 1, 0, 1] and I.active.shape == (8, 288) and I.active.dtype == bool
    assert I.active.any() and np.all(I.active.sum(axis=1)[:-1] >= I.active.sum(axis=1)[1:])   # nested layers
    inst, sched = from_core(I, [np.zeros(0, dtype=np.int64)] * 2, slot_min=5)
    assert inst.m == 2 and inst.n == 8 and inst.grid.T_slow == 288 and inst.grid.slow_min == 5
    for sch in e10.SCHEDS_B:
        _, _, i0, b0 = e10.b_instance(sch, 2, 4.0, 0)
        _, _, i5, b5 = e10.b_instance(sch, 2, 4.0, 5)
        assert b0 == b5 and mc.instance_hash(i0) == mc.instance_hash(i5)
        _, _, i1, b1 = e10.b_instance(sch, 2, 4.0, 1)
        assert b1 != b0 and mc.instance_hash(i1) != mc.instance_hash(i0)


@pytest.mark.needs_a12
def test_trace_omega_one_site_per_lender():
    om, meta = e10.trace_omegas()
    assert len(om) == 16 and len(meta["sites"]) == 16
    for lid, site, r in zip(e10.TRACE_LENDERS, meta["sites"], om):
        assert site.startswith(lid + "/")
        assert r.dtype == np.int64 and np.all(np.diff(r) > 0) and (len(r) == 0 or (r[0] >= 0 and r[-1] < 288))
    assert sum(len(r) for r in om) > 0
    # the config is example_1day.json with the changes of §5.4 only
    base = json.loads((SIM / "configs" / "example_1day.json").read_text())
    cfg = json.loads((SIM / "configs" / e10.TRACE_CONFIG).read_text())
    assert cfg["lenders"] == [{"id": f"a2:c{i:02d}"} for i in range(16)]
    assert cfg["lender_defaults"]["n_layers"] == 1 and cfg["lender_defaults"]["menu"] == ["s5_tau10_H5"]
    assert cfg["contracts"] == [{"id": "s5_tau10_H5", "tau_min": 10, "H_min": 5},
                                {"id": "protected", "tau_min": None, "H_min": 0, "prepaid_min": 5}]
    assert cfg["time"]["horizon_min"] == 1440 and cfg["time"]["fast_slot_min"] == 5 and cfg["seed"] == 1
    for k in set(base) | set(cfg):
        if k in ("name", "lenders", "contracts", "lender_defaults", "time"):
            continue
        assert cfg[k] == base[k], k
    for k in set(base["lender_defaults"]) - {"n_layers", "menu"}:
        assert cfg["lender_defaults"][k] == base["lender_defaults"][k]
    assert {k: v for k, v in cfg["time"].items() if k != "fast_slot_min"} == \
        {k: v for k, v in base["time"].items() if k != "fast_slot_min"}
    # a 'trace' run on the core instance realizes exactly this omega at the revocable sites
    from sublet.engine import EngineConfig, simulate
    from sublet.drivers import run as drun
    from sublet.types import LenderModel
    I, omega, inst, _ = e10.b_instance("trace", 4, 16.0, 2)
    vals, _ = drun.driver_inputs("A3", {}, inst)
    res = simulate(inst, drun.make_policy({"policy": {"id": "A3", "params": {}}}, inst, inputs=vals),
                   LenderModel(schedule="trace"), EngineConfig(check_invariants=True), lender_seed=2, policy_seed=2)
    assert not res.invariant_failures
    assert all(np.array_equal(np.asarray(a), b) for a, b in zip(res.schedule.R, e10.trace_omega(4)))


def test_rerun_listed_only_for_a_flagged_point(tmp_path, monkeypatch):
    """E10-5 / E10-6 (M14): an e10:a output with a flagged tag adds e10:rerun for its point to the job list (read
    from MS3_OUT), and the rerun job runs that tag at the rerun seeds and evaluates the check on all seeds."""
    monkeypatch.delenv(e10.REDUCED_ENV, raising=False)
    out = tmp_path / "e10"
    monkeypatch.setenv("MS3_OUT", str(out))
    job = next(j for j in e10.jobs() if j.id == e10.a_id("safe_site", 4.0, 4))
    small = mc.Job(job.id, job.kind, {**job.params, "n_seeds": 3}, job.est_s)
    rec = mc.run_job("e10", small, lambda o: e10.run(small, o, out), out, resume=False)
    assert rec["status"] == "ok" and rec["runs"] == 9
    assert not any(":rerun:" in j.id for j in e10.jobs())
    path = e10.a_file(out, "safe_site", 4.0, 4)
    res = json.loads(path.read_text())
    res["flagged"] = {"RR": {"check": "E10-5", "ci95_hi": 0.0, "LB_A": 1.0}}
    path.write_text(json.dumps(res))
    rj = [j for j in e10.jobs() if ":rerun:" in j.id]
    assert [j.id for j in rj] == ["e10:rerun:sched=safe_site:rho=4:m=4"] and rj[0].params["tags"] == ["RR"]
    monkeypatch.setattr(e10, "RERUN_SEEDS", (30, 31))
    rr = mc.run_job("e10", rj[0], lambda o: e10.run(rj[0], o, out), out, resume=False)
    assert rr["status"] == "ok" and rr["runs"] == 2
    x = json.loads(e10.rerun_file(out, "safe_site", 4.0, 4).read_text())
    assert x["combined"]["RR"]["runs"] == 5 and x["still_flagged"] == {}
    assert all(r["E10_3_ok"] and r["E10_4_ok"] for r in x["runs"])
    s = e10.summary(out)
    assert s["checks"]["E10-5"]["status"] == "pass" and len(s["checks"]["E10-5"]["flagged"]) == 1
    assert s["a"]["safe_site"]["4"]["4"]["RR"]["runs"] == 3 and s["a"]["safe_site"]["4"]["16"]["RR"]["T"] > 0


def test_summary_uses_only_ok_outputs(tmp_path, monkeypatch):
    """§2.4: only 'ok' counts as done. An e10:a output whose job record is not 'ok' (left by an earlier run of a job
    that later failed or was killed) is not used by the summary, is listed in meta.ignored_outputs and flags no
    rerun; E10-4 also covers the schedules of the reruns."""
    monkeypatch.delenv(e10.REDUCED_ENV, raising=False)
    out = tmp_path / "e10"
    monkeypatch.setenv("MS3_OUT", str(out))
    job = next(j for j in e10.jobs() if j.id == e10.a_id("safe_site", 4.0, 4))
    small = mc.Job(job.id, job.kind, {**job.params, "n_seeds": 2}, job.est_s)
    assert mc.run_job("e10", small, lambda o: e10.run(small, o, out), out, resume=False)["status"] == "ok"
    s = e10.summary(out)
    assert s["a"]["safe_site"]["4"]["4"]["RR"]["runs"] == 2 and s["meta"]["ignored_outputs"] == []
    assert s["checks"]["E10-4"]["n_runs"] == 6
    path = e10.a_file(out, "safe_site", 4.0, 4)
    res = json.loads(path.read_text())
    res["flagged"] = {"RR": {"check": "E10-5", "ci95_hi": 0.0, "LB_A": 1.0}}
    path.write_text(json.dumps(res))
    jp = mc.record_path(out, small.id)
    rec = json.loads(jp.read_text())
    rec["status"] = "oom_at_3G"
    jp.write_text(json.dumps(rec))
    assert not any(":rerun:" in j.id for j in e10.jobs())
    s = e10.summary(out)
    ent = s["a"]["safe_site"]["4"]["4"]["RR"]
    assert ent["runs"] == 0 and ent["ratio"] is None and "ratio_note" in ent
    assert [(x["job"], x["status"]) for x in s["meta"]["ignored_outputs"]] == [(small.id, "oom_at_3G")]
    assert s["checks"]["E10-4"]["status"] == "missing"
