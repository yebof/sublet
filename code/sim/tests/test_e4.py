"""Tests of the E4 driver sublet/experiments/e4.py (design/sim_spec_ms4.md §6, §10 row test_e4.py, test_perturb.py).

- The job list: the counts of §6.5 and §6.7 (384 P-hat day MILPs, 4 OPT_eager MILPs, 64 pcols jobs, 80 week jobs
  with 432 runs, 52 ratio-day jobs with 156 runs, e4:repro) and the reduced list (MS3_E4_REDUCED=1); every id parses
  (§2.4) and has its own record file.
- E4-1's comparison (repro_compare) on hand-made files (equal, one changed line, a --quick run, a row with eta_chk
  false) and, once run_ms2_checks.sh has written them, on MS2's own R7 outputs (needs_ms2_checks).
- phat_bounds: the incumbent and LB of a P-hat day from its MILP record (the gap rule of opt.milp).
- The ratio-day rule of M13 on the week instances (needs_a12): Azure day 2, BurstGPT day 1 at alignment 1 (as
  out/ms4spec/e4_pred_sizing_<panel>_phat.json results.day under its day_rule), the same day at alignment 2, and the
  week's daily overflow of measurement 5 (sizes.week.demand_load_h_per_day).
- A P-hat day job plans the same day instance as plan_daily over the whole horizon: the same objective and columns
  (needs_a12; the reduced BurstGPT window, whose MILPs solve to optimality).
- One reduced (panel, alignment) end to end (needs_a12, about 15 s): P-hat computed once per (panel, alignment,
  prediction, day) by its day jobs and assembled by e4:pcols, then passed as pred_cols and pred_demand, so that
  drivers.run.driver_inputs plans nothing inside a run (drivers.predict.plan_daily replaced by a function that
  raises); the ratio-day runs with q eta, the exact prediction at eta 0; the summary's keys and checks; the
  fractional series over LP_core (aligned_lp of the ratio day) at least 1, the combiner's run without core fields;
  E4-2's bracket of P-hat's MILP over OPT_eager (the exact prediction's point 1, nothing refuted); a P-hat cache of
  another instance is refused; a MILP job killed at the wall-clock limit leaves its LP as Q39's LB, while the LP of a
  job that ended in an error is not used and is listed in meta.ignored_outputs.
"""
import json

import numpy as np
import pytest

from fixtures import SIM

from sublet.drivers import perturb
from sublet.experiments import e4
from sublet.experiments import ms3_common as mc

MS4SPEC = SIM / "out" / "ms4spec"


def test_job_list_counts_and_ids(monkeypatch):
    monkeypatch.delenv(e4.REDUCED_ENV, raising=False)
    js = e4.jobs()
    mc.check_jobs(js)
    parts = [mc.parse_job_id(j.id)[1] for j in js]
    assert {p: parts.count(p) for p in set(parts)} == {"phat": 384, "eager": 4, "pcols": 64, "week": 80,
                                                        "ratio": 52, "repro": 1}
    assert all(j.kind == "milp" for j in js if mc.parse_job_id(j.id)[1] in ("phat", "eager"))
    assert all(j.kind == "pool" for j in js if mc.parse_job_id(j.id)[1] not in ("phat", "eager"))
    week = [j for j in js if ":week:" in j.id]
    assert sum(len(j.params["tags"]) * len(j.params["policy_seeds"]) for j in week) == 432
    assert sum(len(j.params["tags"]) * len(j.params["policy_seeds"]) for j in week if j.params["mu"] == 1.0) == 324
    ratio = [j for j in js if ":ratio:" in j.id]
    assert sum(len(j.params["policy_seeds"]) for j in ratio) == 156 and all(j.params["tags"] == ["A5"] for j in ratio)
    ids = {j.id for j in js}
    assert "e4:phat:panel=azure:c=2:mu=1:pred=amp0.75:day=6" in ids
    assert "e4:phat:panel=burstgpt:c=1:mu=0.2:pred=prev:day=1" in ids
    assert "e4:phat:panel=burstgpt:c=1:mu=0.2:pred=exact:day=1" not in ids     # the mu points: prev only
    assert "e4:week:panel=azure:c=1:mu=2:pred=none" in ids and "e4:eager:panel=azure:c=2" in ids
    assert "e4:ratio:panel=azure:c=1:pred=inj3x30" in ids and "e4:repro" in ids
    assert all(j.est_s is not None for j in js)
    monkeypatch.setenv(e4.REDUCED_ENV, "1")
    jr = e4.jobs()
    mc.check_jobs(jr)
    pr = [mc.parse_job_id(j.id)[1] for j in jr]
    assert {p: pr.count(p) for p in set(pr)} == {"phat": 32, "eager": 2, "pcols": 16, "week": 20, "ratio": 14,
                                                  "repro": 1}
    assert all(j.params["window"] == [444, 72] and j.params["day_slots"] == 24 for j in jr if "window" in j.params)
    assert {mc.parse_job_id(j.id)[2]["day"] for j in jr if ":phat:" in j.id} == {"1", "2"}


def _write_repro(rdir, ref, *, quick=False, change=None, eta_false=False):
    rdir.mkdir(parents=True, exist_ok=True)
    ref.mkdir(parents=True, exist_ok=True)
    txt = "10 random instances\n  exact 0 c(P)/OPT mean  1.000\n"
    near = "T9 nearest\nmax d: 14\n"
    rows = [{"kind": "exact", "par": 0, "cPhat": 2.5, "eta": 0, "eta_chk": True, "lam": [{"lam": 0.1, "P": 1.0}]}]
    (ref / "c5_la.txt").write_text(txt)
    (ref / "c5_la_nearest.txt").write_text(near)
    (ref / "c5_la.json").write_text(json.dumps([{"seed": 0, "OPT": 2.5, "rows": rows}]))
    (ref / "c5_la_nearest.json").write_text(json.dumps([{"seed": 0, "rows": [{"kind": "exact", "d": 14}]}]))
    got_rows = [{**rows[0], "n_pred_cols": 3, "eta_chk": not eta_false,
                 "lam": [{"lam": 0.1, "P": 1.0 + (1e-12 if change is None else 0.0)}]}]
    (rdir / "c5_la_repro.txt").write_text(txt if change is None else txt.replace("1.000", change))
    (rdir / "c5_la_nearest_repro.txt").write_text(near)
    (rdir / "c5_la_repro.json").write_text(json.dumps({"meta": {"quick": quick},
                                                       "runs": [{"seed": 0, "OPT": 2.5, "LPal": 2.0,
                                                                 "rows": got_rows}]}))
    (rdir / "c5_la_nearest_repro.json").write_text(json.dumps({"meta": {"quick": quick},
                                                               "runs": [{"seed": 0, "rows": [{"kind": "exact",
                                                                                              "d": 14}]}]}))


def test_repro_compare_by_hand(tmp_path):
    ref = tmp_path / "ref"
    _write_repro(tmp_path / "a", ref)
    r = e4.repro_compare(tmp_path / "a", ref)
    assert r["pass"] and all(e["lines_equal"] for e in r["files"].values())
    assert r["json"]["c5_la.json"]["n_mismatch"] == 0 and r["json"]["c5_la.json"]["max_rel_diff"] <= 1e-11
    assert r["core_eta"] == {"n_rows": 1, "n_eta_chk_false": 0, "rows_false": []}
    _write_repro(tmp_path / "b", ref, change="1.001")
    r = e4.repro_compare(tmp_path / "b", ref)
    assert not r["pass"] and r["files"]["c5_la.txt"]["first_diffs"][0]["line"] == 2
    assert r["files"]["c5_la_nearest.txt"]["lines_equal"]
    _write_repro(tmp_path / "c", ref, quick=True)
    assert not e4.repro_compare(tmp_path / "c", ref)["pass"]
    _write_repro(tmp_path / "d", ref, eta_false=True)
    r = e4.repro_compare(tmp_path / "d", ref)
    assert r["core_eta"]["n_eta_chk_false"] == 1 and r["json"]["c5_la.json"]["n_mismatch"] == 1
    r = e4.repro_compare(tmp_path / "missing", ref)
    assert not r["pass"] and r["files"]["c5_la.txt"]["note"].endswith("is missing")
    assert r["json"]["c5_la.json"]["max_rel_diff"] is None and r["core_eta"]["n_rows"] == 0


@pytest.mark.needs_ms2_checks("c5_la_repro.json", "c5_la_repro.txt", "c5_la_nearest_repro.json",
                              "c5_la_nearest_repro.txt")
def test_repro_compare_on_ms2_r7_outputs():
    from fixtures import ms2_checks_dir
    r = e4.repro_compare(ms2_checks_dir())
    assert r["pass"] and not r["quick"]
    for k in ("c5_la.json", "c5_la_nearest.json"):
        assert r["json"][k]["n_mismatch"] == 0 and r["json"][k]["max_rel_diff"] <= 1e-9 and r["json"][k]["n_compared"]
    assert r["core_eta"]["n_rows"] == 90 and r["core_eta"]["n_eta_chk_false"] == 0


def test_phat_bounds():
    b = e4.phat_bounds({"method": "milp", "status": 1, "objective": 200.0, "gap": 0.005})
    assert b["incumbent"] == 200.0 and b["LB"] == pytest.approx(199.0) and not b["exact"]
    b = e4.phat_bounds({"method": "milp", "status": 0, "objective": 0.5, "gap": 5e-5})
    assert b["LB"] == pytest.approx(0.5 - 5e-5) and b["exact"]          # gap over max(1, |objective|)
    assert e4.phat_bounds({"method": "none", "status": "empty"}) == {"incumbent": 0.0, "LB": 0.0, "exact": True}
    b = e4.phat_bounds({"method": "lp_round", "status": "optimal", "objective": 10.0})
    assert b["incumbent"] is None and b["LB"] is None and "LB_note" in b


@pytest.mark.needs_a12
def test_ratio_day_rule_and_week_demand():
    for panel, d_star in (("azure", 2), ("burstgpt", 1)):
        inst, _, ecfg = e4.week_instance(panel, 1, 1.0)
        assert ecfg.check_invariants and inst.grid.fast_min == inst.grid.slow_min == 5 and inst.grid.T_slow == 2016
        ds = e4.day_slots_of(inst)
        assert ds == 288 and e4.ratio_day(inst, ds) == d_star
        day, d = e4.ratio_instance(inst, ds)
        assert d == d_star and day.grid.T_slow == 288
        assert np.array_equal(day.clients.demand, inst.clients.demand[:, d_star * 288:(d_star + 1) * 288])
        inst2, _, _ = e4.week_instance(panel, 2, 1.0)
        assert e4.ratio_day(inst2, ds) == d_star                     # the zero pattern does not depend on c
        meas = MS4SPEC / f"e4_pred_sizing_{panel}_phat.json"
        if meas.is_file():
            m = json.loads(meas.read_text())
            assert m["results"]["day"] == d_star and m["day_rule"].startswith("default: the first day d >= 1")
            assert e4.demand_per_day(inst, ds) == pytest.approx(m["sizes"]["week"]["demand_load_h_per_day"],
                                                                rel=1e-9, abs=1e-9)
            assert inst.n == 1 and inst.m == m["sizes"]["week"]["sites"]


@pytest.mark.needs_a12
def test_phat_day_job_plans_the_week_day(tmp_path, monkeypatch):
    from sublet.config import rng_streams
    from sublet.drivers.predict import plan_daily
    monkeypatch.setenv(e4.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_MILP_LIMIT", "20")
    js = {j.id: j for j in e4.jobs()}
    out = tmp_path / "e4"
    for D in (1, 2):
        j = js[e4.phat_id("burstgpt", 1, 1.0, "amp1.5", D)]
        rec = mc.run_job("e4", j, lambda o, j=j: e4.run(j, o, out), out, resume=False)
        assert rec["status"] == "ok" and rec["milp_limit_s"] == 20
    inst, _, _ = e4.week_instance("burstgpt", 1, 1.0, [444, 72], extra={"bench.time_limit_s": 20})
    pred = e4.predicted(inst, "amp1.5", 1, 24)
    full = plan_daily(inst, pred, day_slots=24, method="auto", rng=rng_streams(inst.seed)["bench"])
    cols = []
    for D in (1, 2):
        lb = json.loads(e4.phat_lb_file(out, "burstgpt", 1, 1.0, "amp1.5", D).read_text())
        w = json.loads(e4.run_file(out, "phat", e4.phat_id("burstgpt", 1, 1.0, "amp1.5", D)).read_text())
        assert lb["method"] == full.days[D - 1]["method"] == "milp" and lb["status"] == 0
        assert lb["objective"] == pytest.approx(full.days[D - 1]["objective"], rel=1e-9)
        assert lb["grid"] == "slow" and lb["time_limit_s"] == 20 and lb["git_revision"] == mc.git_revision()
        assert lb["label"] == "perturbation:amplitude:1.5" and lb["incumbent"] == lb["objective"]
        cols += [(F[0], F[1], F[2], F[3] + (D - 1) * 24) for F in w["cols"]]
    assert sorted(cols) == sorted(tuple(F) for F in full)


def _run(js, out, jid):
    j = js[jid]
    return mc.run_job("e4", j, lambda o: e4.run(j, o, out), out, resume=False)


@pytest.mark.needs_a12
def test_reduced_panel_end_to_end(tmp_path, monkeypatch):
    from sublet.drivers import predict
    monkeypatch.setenv(e4.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_MILP_LIMIT", "20")
    js = {j.id: j for j in e4.jobs()}
    out = tmp_path / "e4"
    P, c = "burstgpt", 1
    for pred in ("prev", "exact"):
        for D in (1, 2):
            assert _run(js, out, e4.phat_id(P, c, 1.0, pred, D))["status"] == "ok"
        r = _run(js, out, e4.pcols_id(P, c, 1.0, pred))
        assert r["status"] == "ok" and r["result"]["methods"]["milp"] == 2
    assert _run(js, out, e4.eager_id(P, c))["status"] == "ok"

    def no_plan(*a, **k):
        raise AssertionError("plan_daily called inside a run (M14)")
    monkeypatch.setattr(predict, "plan_daily", no_plan)
    for jid in (e4.week_id(P, c, 1.0, "prev"), e4.week_id(P, c, 1.0, "none"), e4.ratio_id(P, c, "prev"),
                e4.ratio_id(P, c, "exact")):
        rec = _run(js, out, jid)
        assert rec["status"] == "ok" and rec["n_errors"] == 0, rec.get("errors")
    pc = json.loads(e4.pcols_file(out, P, c, 1.0, "prev").read_text())
    wk = json.loads(e4.run_file(out, "week", e4.week_id(P, c, 1.0, "prev")).read_text())
    assert [r["tag"] for r in wk["runs"]] == ["A5", "A6-pred"] and wk["pcols_n_cols"] == pc["n_cols"] > 0
    for r in wk["runs"]:
        assert r["driver_inputs"] == {k: "given" for k in r["inputs_given"]} and "pred_cols" in r["inputs_given"]
        assert r["n_invariant_failures"] == 0 and r["gpu_only_lease_slots"] == 0 and r["combiner"] is not None
        assert r["info_class"] == "online-I1 + prediction:previous-day"
    a5 = wk["runs"][0]["report"]
    assert a5["prediction"] == {"n_cols": pc["n_cols"], "p_max": a5["prediction"]["p_max"], "label": "previous-day"}
    assert [x["psi"] for x in a5["psi"]] == [0.1, 0.3, 0.5]
    assert len(wk["eta_q_by_day"]) == 3 and wk["eta_q_by_day"][0] > 0      # day 0 has no prediction
    ref = json.loads(e4.run_file(out, "week", e4.week_id(P, c, 1.0, "none")).read_text())
    assert [r["tag"] for r in ref["runs"]] == ["A6"] and ref["runs"][0]["inputs_given"] == []
    ex = json.loads(e4.run_file(out, "ratio", e4.ratio_id(P, c, "exact")).read_text())
    pv = json.loads(e4.run_file(out, "ratio", e4.ratio_id(P, c, "prev")).read_text())
    assert ex["eta_q"] == 0.0 and pv["eta_q"] > 0 and ex["d_star"] == pv["d_star"] == 1
    assert ex["ratio_validity"] is None and ex["runs"][0]["ratio_validity"] is None
    assert ex["phat_day"]["day"] == 1 and ex["n_cols"] == sum(1 for F in json.loads(
        e4.pcols_file(out, P, c, 1.0, "exact").read_text())["cols"] if 24 <= F[3] < 48)
    # the summary: every path of §6.10, the checks E4-1 ... E4-6
    s = e4.summary(out)
    assert json.loads((out / "summary.json").read_text()) == json.loads(json.dumps(s))
    assert (out / "tables.md").is_file()
    assert set(s["checks"]) == {f"E4-{i}" for i in range(1, 7)}
    assert s["checks"]["E4-1"]["status"] == "missing" and s["checks"]["E4-3"]["status"] == "pass"
    assert s["checks"]["E4-2"]["trace"]["n_runs"] == 2 and s["checks"]["E4-5"]["n_runs"] == 4
    assert s["meta"]["reduced"] and s["meta"]["ratio_day"]["burstgpt"]["1"] == 1
    assert s["meta"]["predictions"] == perturb.LABELS and s["meta"]["ignored_outputs"] == []
    for panel in e4.PANELS:
        for pred in perturb.PREDICTIONS:
            for ser in e4.SERIES:
                ent = s["ratio"][panel][pred][ser]
                assert all(k in ent for k in ("x", "ratio_LB", "ratio_inc", "median", "n_runs")), (panel, pred, ser)
            assert set(s["combiner"][panel][pred]) == {"A5", "A6-pred", "A5-day"}
        for mk in ("1", "0.2", "0.5", "2"):
            assert "none" in s["week"][panel][mk] and "prev" in s["week"][panel][mk]
    e = s["ratio"][P]["exact"]["a5"]
    assert e["n_runs"] == 1 and e["x"] == 0.0 and e["median"] is not None
    assert s["ratio"][P]["prev"]["psi_01"]["x"] == pytest.approx(pv["eta_q"] / s["eager"][P]["1"]["LB"])
    assert s["week"][P]["1"]["prev"]["A5"]["n_pairs"] == 1 and s["week"][P]["1"]["phase30"]["A5"]["median"] is None
    assert s["phat"][P]["1"]["1"]["prev"]["assembled"] and s["phat"][P]["1"]["1"]["prev"]["methods"]["milp"] == 2
    assert s["eager"][P]["1"]["LB_source"] in ("lp", "milp_dual") and s["eager"][P]["1"]["d_star"] == 1
    # LP_core: the PDs' covering program, a lower bound on every fractional series; the combiner's run has none
    core = json.loads(e4.eager_core_file(out, P, c).read_text())
    assert core["status"] == "optimal" and core["grid"] == "slow" and core["git_revision"] == mc.git_revision()
    assert core["instance_hash"] == ex["meta"]["instance_hash"]
    assert s["eager"][P]["1"]["LP_core"] == core["objective"] > 0
    for pred, doc in (("prev", pv), ("exact", ex)):
        for ser in e4.FRAC_SERIES:
            ent = s["ratio"][P][pred][ser]
            vals = [e4._series_value(r, ser) for r in doc["runs"]]
            assert ent["cost_model"] == "pd_covering" and ent["ratio_core"]["n"] == len(vals) == 1
            assert all(v >= core["objective"] * (1 - 1e-9) for v in vals), (pred, ser, vals)
            assert ent["core_median"] == pytest.approx(vals[0] / core["objective"])
            assert ent["x_core"] == pytest.approx(ent["eta_q_by_c"]["1"] / core["objective"])
        a5e = s["ratio"][P][pred]["a5"]
        assert a5e["cost_model"] == "full" and a5e["core_median"] is None and "core_median_note" in a5e
        assert a5e["x_core"] is None and a5e["ratio_core"]["median"] is None
    # E4-2's bracket (§2.5): P-hat's MILP of day d* over OPT_eager of the ratio day
    br = {r["pred"]: r for r in s["checks"]["E4-2"]["bracket"]["rows"]}
    assert set(br) == {"prev", "exact"} and s["checks"]["E4-2"]["bracket"]["n_refuted"] == 0
    assert br["exact"]["point"] == pytest.approx(1.0, abs=2e-4) and br["exact"]["bound"] == 1.0
    assert br["prev"]["bound"] == pytest.approx(1.0 + pv["eta_q"] / s["eager"][P]["1"]["LB"])
    assert br["prev"]["lo"] <= br["prev"]["point"] <= br["prev"]["hi"]
    # the eager MILP killed at the wall-clock limit: its LP (written before the MILP) is Q39's LB
    lp = json.loads(e4.eager_lp_file(out, P, c).read_text())
    e4.eager_milp_file(out, P, c).unlink()
    jp = mc.record_path(out, e4.eager_id(P, c))
    jp.write_text(json.dumps({**json.loads(jp.read_text()), "status": "wall_limit"}))
    s2 = e4.summary(out)
    assert s2["eager"][P]["1"]["LB_source"] == "lp" and s2["eager"][P]["1"]["LB"] == pytest.approx(lp["objective"])
    assert s2["eager"][P]["1"]["milp_status"] == "wall_limit" and s2["ratio"][P]["exact"]["a5"]["inc_median"] is None
    assert s2["meta"]["ignored_outputs"] == [] and s2["eager"][P]["1"]["LP_core"] == core["objective"]
    # ... while a job that ended in an error leaves no LB: its LP files are not used and are listed (§2.6)
    jp.write_text(json.dumps({**json.loads(jp.read_text()), "status": "error"}))
    s3 = e4.summary(out)
    assert s3["eager"][P]["1"]["LB"] is None and s3["eager"][P]["1"]["LP_core"] is None
    assert s3["eager"][P]["1"]["lp_status"] == "error" and s3["ratio"][P]["exact"]["a5"]["median"] is None
    assert [x["job"] for x in s3["meta"]["ignored_outputs"]] == [e4.eager_id(P, c)]
    # a P-hat cache of another instance is refused by the runs (no re-solve)
    pf = e4.pcols_file(out, P, c, 1.0, "prev")
    pf.write_text(json.dumps({**pc, "instance_hash": "0" * 64}))
    rb = _run(js, out, e4.ratio_id(P, c, "prev"))
    assert rb["status"] == "error" and "P-hat of instance" in rb["error"]
