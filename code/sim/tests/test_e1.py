"""Tests of the E1 driver sublet/experiments/e1.py (design/sim_spec_ms3.md §4, §10 row test_e1.py).

- The single-site tightness family (§4.4) by solve_core: at T = 60 it equals c3/out/c3_benchmark.json `a`
  (OPT_eager, OPT_none, OPTeager_over_OPTnone) and at T = 600 the closed forms OPT = beta + a T and
  OPT_eager = ceil(T / D) (beta + a D), exactly (status 0, gap <= 1e-9); tight_check passes on these rows.
- The job list: the counts of §4.3 (2 small pool jobs and 72 cells; 496 MILPs: 444 adaptive omega, 20 trace
  omega, 32 eager) and the reduced list (MS3_E1_REDUCED=1); every id parses (§2.4).
- One E1 cell end to end (needs_a12, slow): the reduced 2-hour instance of bench_e1 (restrict_horizon(inst, 0,
  24) after the build) under 'adaptive' at rho* = 16, mu = 1, c = 1, every tag at policy seed 0: the runs with
  their realized schedules, the LPs, one MILP with a 30-s limit (MS3_MILP_LIMIT), lb_record, the A8
  certificate, the summary with every key path of §4.3 that Figs. 5(b), 5(a) and sf_e1_sched read; a MILP job
  whose stored schedule hash does not match the run file is an error.
"""
import json
import math

import pytest

from fixtures import SIM

from sublet.experiments import e1
from sublet.experiments import ms3_common as mc

C3_BENCH = SIM.parents[1] / "code" / "theory_checks" / "c3" / "out" / "c3_benchmark.json"


def test_tight_family_reproduces_c3_benchmark_and_the_closed_forms():
    rows = e1.tight_rows(Ts=(60, 600))
    ref = json.loads(C3_BENCH.read_text())["a"]
    by = {(r["T"], r["rho"]): r for r in rows}
    assert len(rows) == 10
    for x in ref:
        r = by[(60, float(x["rho"]))]
        assert r["OPT_eager"] == pytest.approx(x["OPT_eager"], abs=1e-9)
        assert r["OPT_none"] == pytest.approx(x["OPT_none"], abs=1e-9)
        assert r["ratio"] == pytest.approx(x["OPTeager_over_OPTnone"], abs=1e-9)
    for r in rows:
        beta = (r["rho"] - 1.0) * 3
        assert r["status_none"] == 0 and r["status_eager"] == 0
        assert (r["gap_none"] or 0.0) <= 1e-9 and (r["gap_eager"] or 0.0) <= 1e-9
        assert r["OPT_none"] == pytest.approx(beta + r["T"], abs=1e-9)
        assert r["OPT_eager"] == pytest.approx(math.ceil(r["T"] / 3) * (beta + 3.0), abs=1e-9)
        assert r["ratio"] <= max(2.0, r["rho"]) + 1e-9          # C3-L2 on an exact core instance (E1-4)
    chk = e1.tight_check(rows, ref)
    assert chk["pass"] and chk["n_T60_compared"] == 5 and chk["max_abs_diff_T60_vs_reference"] <= 1e-9


def test_job_list_counts_and_ids(monkeypatch):
    monkeypatch.delenv(e1.REDUCED_ENV, raising=False)
    js = e1.jobs()
    mc.check_jobs(js)
    kinds = [j.kind for j in js]
    assert kinds.count("pool") == 2 + 72 and kinds.count("milp") == 496 and "alone" not in kinds
    ids = [j.id for j in js]
    assert sum(i.startswith("e1:milp:sched=adaptive:") for i in ids) == 444
    assert sum(i.startswith("e1:milp:sched=trace:") and i.endswith(":bench=omega") for i in ids) == 20
    assert sum(i.startswith("e1:milp:bench=eager:") for i in ids) == 32
    assert "e1:cell:sched=adaptive:rho=4:mu=1:c=2" in ids and "e1:cell:sched=adaptive:rho=4:mu=0.2:c=4" in ids
    assert "e1:milp:sched=adaptive:rho=1.5:mu=1:c=1:tag=A3-rot:p=2" in ids
    for i in ids:
        mc.parse_job_id(i)
    cells = [j for j in js if ":cell:" in j.id]
    runs = sum(len(j.params["tags"]) * len(j.params["policy_seeds"]) for j in cells)
    assert runs == 924                                         # 240 + 480 + 144 + 60 (§4.3)
    assert all(j.est_s is not None for j in js)
    monkeypatch.setenv(e1.REDUCED_ENV, "1")
    jr = e1.jobs()
    assert [j.kind for j in jr].count("pool") == 2 + 18 and [j.kind for j in jr].count("milp") == 50
    assert all(j.params.get("horizon_slots") == e1.REDUCED_HORIZON_SLOTS for j in jr if ":cell:" in j.id)


def _job(js, jid):
    return next(j for j in js if j.id == jid)


@pytest.mark.needs_a12
@pytest.mark.slow
def test_one_cell_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setenv(e1.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_MILP_LIMIT", "30")
    out = tmp_path / "e1"
    js = e1.jobs()
    cell = _job(js, e1.cell_id("adaptive", 16.0, 1.0, 1))
    rec = mc.run_job("e1", cell, lambda o: e1.run(cell, o, out), out, resume=False)
    assert rec["status"] == "ok" and rec["runs"] == 5 and rec["n_errors"] == 0, rec.get("errors")
    cr = json.loads(e1.cell_file(out, "adaptive", 16.0, 1.0, 1).read_text())
    assert cr["rho_check"]["pass"] and set(cr["fees"]) == {"M", "L"} and min(cr["fees"].values()) > 0
    assert cr["horizon_slots"] == 24 and len(cr["runs"]) == 5
    for row in cr["runs"]:
        run = json.loads((out / row["file"]).read_text())
        assert run["meta"]["schedule_hash"] == row["schedule_hash"] and len(run["schedule"]["R"]) > 0
        assert run["n_invariant_failures"] == 0 and run["ratio_validity"] is None
        assert (out / row["lp_file"]).is_file()
    sub = next(r for r in cr["runs"] if r["tag"] == "Sublet")
    assert sub["certificate"]["available"] and sub["certificate"]["held"]
    a2 = next(r for r in cr["runs"] if r["tag"] == "A2-r1")
    assert a2["P"] is not None and a2["P"] > 0
    # one MILP with the 30-s limit, then Q39's record of that run
    mj = _job(js, e1.milp_omega_id("adaptive", 16.0, 1.0, 1, "A2-th", 0))
    mr = mc.run_job("e1", mj, lambda o: e1.run(mj, o, out), out, resume=False)
    assert mr["status"] == "ok" and mr["milp_limit_s"] == 30
    milp = json.loads(e1.milp_omega_file(out, "adaptive", 16.0, 1.0, 1, "A2-th", 0).read_text())
    assert milp["status"] in (0, 1) and milp["time_limit_s"] == 30 and milp["size"]["n_vars"] > 0
    row = next(r for r in cr["runs"] if r["tag"] == "A2-th")
    lb = mc.lb_record(row["ALG"], json.loads((out / row["lp_file"]).read_text()), milp, reason=row["ratio_validity"])
    assert lb["LB"] is not None and lb["ratio_LB"] >= 1 - 1e-6 and lb["incumbent"] is not None
    # a tampered schedule hash is refused before solving
    bad = json.loads(e1.cell_file(out, "adaptive", 16.0, 1.0, 1).read_text())
    next(r for r in bad["runs"] if r["tag"] == "A3-ref")["schedule_hash"] = "0" * 64
    e1.cell_file(out, "adaptive", 16.0, 1.0, 1).write_text(json.dumps(bad))
    mb = _job(js, e1.milp_omega_id("adaptive", 16.0, 1.0, 1, "A3-ref", 0))
    rb = mc.run_job("e1", mb, lambda o: e1.run(mb, o, out), out, resume=False)
    assert rb["status"] == "error" and "schedule hash" in rb["error"]
    e1.cell_file(out, "adaptive", 16.0, 1.0, 1).write_text(json.dumps(cr))
    # the summary: every key path of the design grid (§4.3), values where the runs exist, null with notes elsewhere
    s = e1.summary(out)
    assert json.loads((out / "summary.json").read_text()) == json.loads(json.dumps(s))
    assert (out / "tables.md").is_file()
    for sched in e1.SCHEDS:
        for r in e1.RHOS:
            for tag in e1.cell_tags(sched, 1.0):
                ent = s["ratios"][sched][mc.num_key(r)]["1"][tag]
                for k in ("ratio_LB", "ratio_inc", "median", "median_ci95", "inc_median", "share_exact", "max_gap",
                          "n_runs"):
                    assert k in ent, (sched, r, tag, k)
    for mu in e1.MUS_SWEEP:
        assert set(s["ratios"]["adaptive"]["4"][mc.num_key(mu)]) == set(e1.MAIN_TAGS)
    e = s["ratios"]["adaptive"]["16"]["1"]
    assert e["A2-th"]["n_runs"] == 1 and e["A2-th"]["ratio_LB"]["median"] == pytest.approx(lb["ratio_LB"])
    assert e["A2-th"]["inc_median"] == pytest.approx(lb["ratio_inc"]) and e["A2-th"]["share_exact"] in (0.0, 1.0)
    assert e["A2-r1"]["P_over_LB"]["n"] == 1 and e["A2-r1"]["a2_frac"] == e["A2-r1"]["P_over_LB"]
    assert e["Sublet"]["median"] is not None
    assert s["ratios"]["trace"]["16"]["1"]["Sublet"]["median"] is None
    assert "median_note" in s["ratios"]["trace"]["16"]["1"]["Sublet"]
    for r in e1.RHOS:
        for c in e1.ALIGNMENTS:
            b = s["brackets"]["trace"][mc.num_key(r)][str(c)]
            assert all(k in b for k in ("point", "lo", "hi", "exact", "rho_instance"))
    assert s["meta"]["fees"]["16"]["1"]["beta_jl_usd"] == cr["fees"]
    assert s["certificates"]["by_case"]["W(a)"]["runs"] + s["certificates"]["by_case"]["W(b)"]["runs"] + \
        s["certificates"]["by_case"]["W(c)"]["runs"] == 1
    assert set(s["checks"]) == {f"E1-{i}" for i in range(1, 9)}
    assert s["checks"]["E1-2"]["status"] == "pass" and s["checks"]["E1-6"]["status"] == "pass"
    assert s["checks"]["E1-5"]["status"] == "pass"
    assert s["milp"]["counts"]["omega_adaptive"].get("0", 0) + s["milp"]["counts"]["omega_adaptive"].get("1", 0) == 1
    assert s["milp"]["stale"] == [] and s["meta"]["ignored_outputs"] == []
    # a MILP record of another schedule (left by an earlier run of its job) is not used: the LB falls back to the LP
    mp = e1.milp_omega_file(out, "adaptive", 16.0, 1.0, 1, "A2-th", 0)
    bad_milp = {**milp, "schedule_hash": "f" * 64}
    mp.write_text(json.dumps(bad_milp))
    s2 = e1.summary(out)
    assert s2["milp"]["stale"] == [mj.id]
    assert s2["milp"]["counts"]["omega_adaptive"] == {"stale": 1, "error": 1, "missing": 3}
    lp_obj = json.loads((out / row["lp_file"]).read_text())["objective"]
    e_th = s2["ratios"]["adaptive"]["16"]["1"]["A2-th"]
    assert e_th["ratio_inc"]["n"] == 0 and e_th["median"] == pytest.approx(row["ALG"] / lp_obj)
    mp.write_text(json.dumps(milp))
    # an output whose job record is not 'ok' (a later run of the job failed or was killed) is not used (§2.4)
    jp = mc.record_path(out, cell.id)
    rec_c = json.loads(jp.read_text())
    jp.write_text(json.dumps({**rec_c, "status": "error"}))
    s3 = e1.summary(out)
    assert s3["ratios"]["adaptive"]["16"]["1"]["A2-th"]["n_runs"] == 0
    assert [(x["job"], x["status"]) for x in s3["meta"]["ignored_outputs"]] == [(cell.id, "error")]
    assert s3["checks"]["E1-2"]["status"] == "missing" and s3["meta"]["grid"]["cells_found"] == 0
