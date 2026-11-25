"""Tests of the E9 driver sublet/experiments/e9.py and its run script run_e9.sh (design/sim_spec_ms5.md §5, §2.4,
§10 row test_e9.py).

Quick (no raw data):
- e9.point_overrides against out/ms5spec/e9_sizing.py's point builder at every point of its grid (2 bases x 7 V x 3
  LLM sets) and against the overrides that e9_sizing_grid.json records; the driver's constants against the script's
  (bases, V, LLM sets, the run limits, the LP's limits);
- the job list of §5.7: 128 e9:run and 28 e9:lp jobs, every one 'alone', the runs in the order of the points (Sublet,
  then A6, over the alignments), then the LPs; the limits (measurement 4's case limits of out/ms5spec/run_all.sh's
  E9_RUNS, 900 s at the four added e7r points, whose estimates need far less, 1800 s for the LPs with HiGHS's 1500 s)
  and --limits' lines; the reduced list (every point and job kind, alignment 1, policy seed 0, a 2-hour horizon);
- the LP gate of M18 on the measured estimates of e9_sizing_grid.json: every e7r SML point under 2800 MB, every e7f
  point with three LLMs above it;
- C27's keys on synthetic runtimes: the loops per simulated hour (slow_step_s_sum / hours, fast_step_s_sum / hours),
  the setup apart (build, driver inputs, the policy's construction, reset_s), the medians and ranges over four
  alignments, null forms with notes; E9-2's rule (counts, and the step sums with reset_s and finish_s at most wall_s +
  1e-6 s) on runtimes that pass and fail; HiGHS's model status parsed from the solver message;
- the summary on hand-made job outputs: E9-1 ... E9-5 with their pass, fail and missing paths (an error record, an ok
  record without its run file, an invariant failure, a step sum above the wall, an unavailable or unheld certificate,
  an LP skipped by the gate or not optimal), outputs whose record is not 'ok' ignored, entries without runs keeping
  every field;
- run_e9.sh with a fake driver: the job list, the limits file, the manifest twice and the summary; every job alone
  (holding every slot), one at a time in list order; a job over its limit killed by timeout and recorded as
  wall_limit with exit 124 and its limit; E9_ONLY; MS3_RESUME skips ok jobs; the done line; bash -n.
With the a12 outputs (needs_a12):
- the sizes of e7f V1 SML, e7r V8 SML and e7f V8 S (sites, units, sites x LLMs) against e9_sizing_grid.json, with the
  invariant checks on, unmerged layers and the trace lender;
- run_e9.sh --reduced under a scratch MS3_ROOT with E9_ONLY on the smallest run point and LP: summary.json with
  meta.reduced true and every check row, the run files with their git revision, C27's counts, the LP optimal.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from fixtures import SIM

from sublet.experiments import e9
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms4_common as m4

MS5SPEC = SIM / "out" / "ms5spec"
RUN_E9 = SIM / "sublet" / "experiments" / "run_e9.sh"
GRID = MS5SPEC / "e9_sizing_grid.json"


def _e9_sizing():
    """out/ms5spec/e9_sizing.py, loaded as a module (its functions import the package lazily)."""
    spec = importlib.util.spec_from_file_location("e9_sizing_ms5spec", MS5SPEC / "e9_sizing.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- points (§5.3)
def test_point_overrides_match_the_measurement():
    s = _e9_sizing()
    assert e9.BASES == s.BASES and e9.VS == s.VS and e9.LLM_SETS == s.LLM_SETS and e9.DAY_MIN == s.DAY_MIN
    grid = json.loads(GRID.read_text())["points"]
    assert len(grid) == 42
    for name in s.grid_points():
        assert e9.parse_point(name) == s.parse_point(name)
        for hz in (e9.DAY_MIN, e9.REDUCED_HORIZON_MIN):
            assert e9.point_overrides(name, hz) == s.point_overrides(name, hz), (name, hz)
        assert e9.point_overrides(name) == grid[name]["overrides"], name
    assert set(e9.RUN_POINTS) <= set(grid) and len(set(e9.RUN_POINTS)) == 16
    assert e9.LP_POINTS == tuple(f"e7r_V{v}_SML" for v in e9.VS) and set(e9.LP_POINTS) <= set(e9.RUN_POINTS)
    assert e9.RUN_POINTS == tuple(f"e7f_V{v}_SML" for v in e9.VS) + ("e7f_V8_S", "e7f_V8_ML") + e9.LP_POINTS
    for bad in ("e7x_V8_SML", "e7f_8_SML", "e7f_V0_SML", "e7f_V8_SM", "e7f_V8", "e7f_Vx_SML"):
        with pytest.raises(ValueError):
            e9.parse_point(bad)
    # the SML points keep the configs' llms and s_S 0.25; ML and S set both
    assert "llms" not in e9.point_overrides("e7r_V4_SML")
    assert e9.point_overrides("e7f_V8_ML")["borrowers.s_S"] == 0.0
    assert [x["id"] for x in e9.point_overrides("e7f_V8_S")["llms"]] == ["S"]


def test_point_spec():
    sp = e9.point_spec("e7f_V16_ML", "A8", m4.need_params("BL5"), c=3, horizon_min=120)
    assert sp["instance"] == m4.E7_CONFIG and sp["engine"] == {"check_invariants": True}
    assert sp["seeds"] == {"config": [3], "lender": "config", "policy": [e9.POLICY_SEED]}
    assert sp["overrides"] == e9.point_overrides("e7f_V16_ML", 120) and sp["lender_model"] == {}
    assert sp["policy"] == {"id": "A8", "params": m4.need_params("BL5")}
    assert e9.point_spec("e7r_V1_SML", "A6")["instance"] == m4.E7R_CONFIG


# ---------------------------------------------------------------- jobs and limits (§5.7)
def _run_all_limits() -> dict:
    """out/ms5spec/run_all.sh's E9_RUNS: {point: {'Sublet': s, 'A6': s}}."""
    text = (MS5SPEC / "run_all.sh").read_text()
    m = re.search(r"E9_RUNS=\(([^)]*)\)", text)
    out = {}
    for item in m.group(1).split():
        p, a, b = item.split(":")
        out[p] = {"Sublet": int(a), "A6": int(b)}
    return out


def test_job_list_and_limits(monkeypatch):
    monkeypatch.delenv(e9.REDUCED_ENV, raising=False)
    js = e9.jobs()
    mc.check_jobs(js)
    assert len(js) == 156 and all(j.kind == "alone" for j in js)
    runs = [j for j in js if j.params["kind"] == "run"]
    lps = [j for j in js if j.params["kind"] == "lp"]
    assert len(runs) == 128 and len(lps) == 28 and js == runs + lps          # the runs, then the LPs
    for j in js:
        exp, part, kv = mc.parse_job_id(j.id)
        assert exp == "e9" and part == j.params["kind"] and kv["pt"] == j.params["point"]
        assert kv["c"] == str(j.params["c"]) and j.est_s is not None and j.est_s > 0
        assert j.params["horizon_min"] == e9.DAY_MIN
    assert runs[0].id == "e9:run:pt=e7f_V1_SML:pol=Sublet:c=1" and runs[4].id == "e9:run:pt=e7f_V1_SML:pol=A6:c=1"
    assert [j.params["point"] for j in runs[::8]] == list(e9.RUN_POINTS)      # the order of the points
    assert lps[0].id == "e9:lp:pt=e7r_V1_SML:c=1" and lps[-1].id == "e9:lp:pt=e7r_V64_SML:c=4"
    assert {(j.params["point"], j.params["tag"], j.params["c"]) for j in runs} == \
        {(p, t, c) for p in e9.RUN_POINTS for t in ("Sublet", "A6") for c in e9.ALIGNMENTS}
    assert all(j.params["policy_seed"] == 0 for j in runs)
    # limits: measurement 4's case limits, 900 s at the four added e7r points, 1800 s for the LPs
    meas = _run_all_limits()
    assert len(meas) == 12
    for j in runs:
        p, t = j.params["point"], j.params["tag"]
        want = meas[p][t] if p in meas else 900
        assert j.params["limit_s"] == e9.run_limit_s(p, t) == want, j.id
    added = sorted(set(e9.RUN_POINTS) - set(meas))
    assert added == sorted(f"e7r_V{v}_SML" for v in (2, 4, 16, 32))
    for p in added:                     # their estimates need far less than the 900-s limit (§5.8)
        for t in ("Sublet", "A6"):
            assert 0 < e9.est_run_s(p, t) <= 0.25 * e9.RUN_LIMIT_DEFAULT_S, (p, t)
    assert e9.est_run_s("e7r_V32_SML", "Sublet") == pytest.approx(500.4 * 353.1 / 1357.6)
    assert e9.est_run_s("e7r_V16_SML", "A6") == pytest.approx(13.1 * 41.8 / 17.4)
    for j in lps:
        assert j.params["limit_s"] == e9.LP_LIMIT_S == 1800 and j.params["time_limit_s"] == 1500.0
        assert j.params["gate_mb"] == e9.LP_GATE_MB == 2800.0
    lim = [ln.split() for ln in e9.limits_text().splitlines()]
    assert [x[1] for x in lim] == [j.id for j in js] and [int(x[0]) for x in lim] == [j.params["limit_s"] for j in js]
    counts = {}
    for x in lim:
        counts[int(x[0])] = counts.get(int(x[0]), 0) + 1
    assert counts == {900: 100, 1800: 40, 3600: 8, 7200: 8}
    s = _e9_sizing()
    assert e9.RUN_LIMIT_S == s.RUN_TIMEOUT_S and e9.RUN_LIMIT_DEFAULT_S == s.RUN_TIMEOUT_DEFAULT_S
    assert e9.LP_LIMIT_S == s.LP_TIMEOUT_S and e9.LP_TIME_LIMIT_S == s.LP_TIME_LIMIT_S
    # the reduced list: every point and job kind, alignment 1, policy seed 0, a 2-hour horizon
    monkeypatch.setenv(e9.REDUCED_ENV, "1")
    jr = e9.jobs()
    assert len(jr) == 16 * 2 + 7 and all(j.params["c"] == 1 and j.params["horizon_min"] == 120 for j in jr)
    assert {j.params["kind"] for j in jr} == {"run", "lp"} and e9.design()["reduced"] is True


def test_limits_command_line(capsys, monkeypatch):
    monkeypatch.delenv(e9.REDUCED_ENV, raising=False)
    assert e9.main(["--limits"]) == 0
    out = capsys.readouterr().out
    assert out == e9.limits_text() and out.splitlines()[0] == "900 e9:run:pt=e7f_V1_SML:pol=Sublet:c=1"


def test_lp_gate_on_the_measured_estimates():
    pts = json.loads(GRID.read_text())["points"]

    def est(p):
        return pts[p]["lp_estimate"]["merged"]["est_mb_lp"]
    for p in e9.LP_POINTS:
        assert e9.lp_gate(est(p)), (p, est(p))
    assert max(est(p) for p in e9.LP_POINTS) == pytest.approx(2744, abs=1)
    for v in e9.VS:                                     # E7's menu: every three-LLM point above the gate (M17)
        assert not e9.lp_gate(est(f"e7f_V{v}_SML")), v
    assert e9.lp_gate(est("e7f_V1_S")) and e9.lp_gate(est("e7f_V2_S"))
    assert not e9.lp_gate(e9.LP_GATE_MB) and e9.lp_gate(e9.LP_GATE_MB - 1e-9)
    assert not e9.lp_gate(None) and not e9.lp_gate(float("nan"))


# ---------------------------------------------------------------- C27's keys: timing, aggregation, E9-2's rule
def _rt(i: int = 0, **kw) -> dict:
    """A runtime with C27's keys for one day (288 slow and 1440 fast steps)."""
    rt = {"wall_s": 100.0 + i, "slow_step_s_p50": 0.1, "slow_step_s_p99": 0.5 + i, "fast_step_s_p50": 0.001,
          "fast_step_s_p99": 0.004, "routing_s": 3.0, "routing_lp_s": 1.0, "routing_lp_calls": 7, "policy_s": 70.0,
          "peak_rss_mb": 300.0, "n_alive_leases_max": 9, "reset_s": 2.0 + i, "slow_step_s_sum": 72.0 + i,
          "slow_step_s_max": 2.0 + i, "n_slow_steps": 288, "fast_step_s_sum": 24.0, "fast_step_s_max": 0.01,
          "n_fast_steps": 1440, "check_s": 0.5, "finish_s": 0.25}
    rt.update(kw)
    return rt


SETUP = {"build_s": 1.0, "driver_inputs_s": 0.5, "make_policy_s": 0.25}


def test_timing_fields_from_c27_keys():
    t = e9.timing_fields(_rt(), 24.0, SETUP)
    assert t["slow_loop_s_per_h"] == 3.0 and t["fast_loop_s_per_h"] == 1.0 and t["loops_s_per_h"] == 4.0
    assert t["check_s_per_h"] == pytest.approx(0.5 / 24) and t["engine_s_per_h"] == pytest.approx(100.0 / 24)
    assert t["setup_s"] == 1.0 + 0.5 + 0.25 + 2.0 and t["reset_s"] == 2.0      # the setup apart from the loops
    assert (t["slow_step_p99_s"], t["slow_step_max_s"], t["fast_step_p99_s"]) == (0.5, 2.0, 0.004)
    assert t["n_slow_steps"] == 288 and isinstance(t["n_slow_steps"], int) and t["routing_lp_calls"] == 7
    assert t["engine_wall_s"] == 100.0 and t["finish_s"] == 0.25
    # a missing key gives null with its note, and the sums that need it as well
    t2 = e9.timing_fields(_rt(fast_step_s_sum=None), 24.0, {})
    assert t2["fast_loop_s_per_h"] is None and t2["fast_loop_s_per_h_note"] and t2["loops_s_per_h"] is None
    assert t2["setup_s"] is None and t2["build_s_note"] and t2["slow_loop_s_per_h"] == 3.0
    with pytest.raises(ValueError):
        e9.timing_fields(_rt(), 0.0, SETUP)
    json.dumps(mc.jsonable([t, t2]), allow_nan=False)


def test_aggregation_over_four_alignments():
    by = {str(c): e9.timing_fields(_rt(c), 24.0, SETUP) for c in (1, 2, 3, 4)}
    a = e9.agg_alignments(by, ("slow_loop_s_per_h", "setup_s", "slow_step_max_s", "fast_loop_s_per_h"))
    assert a["n"] == 4 and a["alignments"] == [1, 2, 3, 4]
    sl = [(72.0 + c) / 24 for c in (1, 2, 3, 4)]
    assert a["median"]["slow_loop_s_per_h"] == pytest.approx((sl[1] + sl[2]) / 2)
    assert a["min"]["slow_loop_s_per_h"] == pytest.approx(sl[0]) and a["max"]["slow_loop_s_per_h"] == \
        pytest.approx(sl[3])
    assert a["median"]["setup_s"] == pytest.approx(1.75 + 4.5) and a["max"]["slow_step_max_s"] == 6.0
    assert a["min"]["fast_loop_s_per_h"] == a["max"]["fast_loop_s_per_h"] == 1.0
    by["2"]["setup_s"] = None                           # a value missing at one alignment is left out
    a = e9.agg_alignments(by, ("setup_s",))
    assert a["min"]["setup_s"] == pytest.approx(1.75 + 3.0) and a["median"]["setup_s"] == pytest.approx(1.75 + 5.0)
    e = e9.agg_alignments({}, ("setup_s",))
    assert e["n"] == 0 and e["median"]["setup_s"] is None and e["median"]["setup_s_note"] == "no run"
    assert e["min"]["setup_s"] is None and e["max"]["setup_s_note"]


def test_step_check_rule():
    ok = e9.step_check(_rt(), 288, 1440)
    assert ok["ok"] and ok["excess_s"] == pytest.approx(72 + 24 + 2 + 0.25 - 100) and ok["tolerance_s"] == 1e-6
    tight = _rt(finish_s=100.0 - 72 - 24 - 2)          # the sums equal the wall
    assert e9.step_check(tight, 288, 1440)["ok"]
    assert e9.step_check(_rt(finish_s=tight["finish_s"] + 0.5e-6), 288, 1440)["ok"]      # within 1e-6 s
    over = e9.step_check(_rt(finish_s=tight["finish_s"] + 2e-6), 288, 1440)
    assert not over["ok"] and over["excess_s"] == pytest.approx(2e-6) and "exceed wall_s" in over["problems"][0]
    assert not e9.step_check(_rt(n_slow_steps=287), 288, 1440)["ok"]
    assert not e9.step_check(_rt(n_fast_steps=288), 288, 1440)["ok"]
    nofin = e9.step_check(_rt(finish_s=None), 288, 1440)
    assert not nofin["ok"] and nofin["excess_s"] is None and "finish_s" in nofin["problems"][0]
    assert e9.step_check(_rt(n_slow_steps=24, n_fast_steps=120), 24, 120)["ok"]          # the reduced grid


def test_highs_status():
    assert e9.highs_status("Optimization terminated successfully. (HiGHS Status 7: Optimal)") == (7, "Optimal")
    assert e9.highs_status("Time limit reached. (HiGHS Status 13: Time limit reached)") == (13, "Time limit reached")
    assert e9.highs_status("empty model") == (None, None) and e9.highs_status(None) == (None, None)


# ---------------------------------------------------------------- the summary on hand-made job outputs
def _a8(case="W(a)", held=True, available=True, t_a=None):
    return {"B0_rule": m4.B0_RULE, "B0_usd": 10.0, "certificate": {"available": available, "held": held},
            "certificate_case": case, "t_a": t_a, "aborted": t_a is not None}


def _run_file(point, tag, c, rt=None, inv=0, a8=None, fits=True):
    rt = rt or _rt(c)
    jid = e9.run_id(point, tag, c)
    tm = e9.timing_fields(rt, 24.0, SETUP)
    tm.update(job_s=105.0, job_s_per_h=105.0 / 24)
    return {"meta": {"exp": "e9", "job": jid, "git_revision": "0" * 40, "host": "h", "loadavg_start": [0.1, 0, 0]},
            "kind": "run", "point": point, "base": e9.parse_point(point)[0], "tag": tag, "c": c,
            "instance_hash": f"ih-{point}-{c}",
            "instance": {"n_sites": 28, "n_sites_by_kind": {"layer": 23, "protected": 5}, "n_llms": 3, "n_contracts": 4,
                         "n_revocable_contracts": 3, "sites_x_llms": 84, "n_clients": 15, "n_units": 340 + c,
                         "bl0a_usd": 200.0 + c, "demand_load_h": 9.0, "grid": {"T_slow": 288, "T_fast": 1440}},
            "references": {"bl0a_usd": 200.0 + c, "own_capacity_usd": 50.0},
            "timing": tm, "steps_check": e9.step_check(rt, 288, 1440),
            "memory": {"peak_rss_mb": 250.0 + c, "scope_memory_peak_mb": 240.0, "fits_cap": fits},
            "runs": [{"accountings": {"overflow_usd": 120.0, "overflow_over_bl0a": 0.6, "total_over_bl0a": 0.7},
                      "n_invariant_failures": inv, "invariant_failures_first": ["x"] if inv else [], "n_leases": 4,
                      "runtime": rt, "a8": (a8 or _a8()) if tag == "Sublet" else None}]}


def _lp_file(point, c, status=0, highs=7, skipped=False, fits=True):
    jid = e9.lp_id(point, c)
    m = {k: 1.0 for k in e9.LP_METRICS}
    m.update(n_sites_merged=20.0 + c, s_per_h=10.0 * c, solve_s=200.0 + c, objective_over_bl0a=0.43)
    return {"meta": {"exp": "e9", "job": jid, "git_revision": "0" * 40, "loadavg_start": [0.2, 0, 0]}, "kind": "lp",
            "point": point, "c": c, "instance_hash": f"ih-{point}-{c}", "schedule_hash": "sh",
            "instance": {"n_sites": 28, "n_units": 340 + c, "bl0a_usd": 200.0 + c},
            "lp": {"skipped": skipped, "skip_reason": "gate" if skipped else None,
                   "status": None if skipped else status,
                   "status_msg": f"(HiGHS Status {highs}: X)", "highs_model_status": None if skipped else highs,
                   "highs_model_status_text": "X"},
            "metrics": m, "memory": {"peak_rss_mb": 900.0, "fits_cap": fits}}


def _write(out, jid, status="ok", data=None):
    mc.dump_json({"job": jid, "status": status}, mc.record_path(out, jid))
    if data is not None:
        mc.dump_json(data, e9.run_path(out, jid))


def test_summary_on_hand_made_outputs(tmp_path, monkeypatch):
    monkeypatch.setenv(e9.REDUCED_ENV, "1")            # 39 jobs: alignment 1
    out = tmp_path / "e9"
    js = e9.jobs()
    for j in js:                                       # every job ok with a clean output
        p = j.params
        _write(out, j.id, data=_run_file(p["point"], p["tag"], 1) if p["kind"] == "run" else _lp_file(p["point"], 1))
    s = e9.summary(out)
    assert list(s["checks"]) == list(e9.CHECK_IDS)
    assert [s["checks"][k]["status"] for k in e9.CHECK_IDS] == ["pass"] * 4 + ["informative"]
    assert s["meta"]["reduced"] is True and s["meta"]["reduced_note"] and s["meta"]["jobs_ok"] == 39
    assert s["meta"]["jobs_missing"] == [] and s["meta"]["limits"]["run"]["e7f_V64_SML"] == {"Sublet": 7200,
                                                                                              "A6": 3600}
    assert list(s["points"]) == list(e9.RUN_POINTS) and list(s["lp"]) == list(e9.LP_POINTS)
    p = s["points"]["e7f_V1_SML"]
    assert p["base"] == "e7f" and p["menu"] == "full" and p["V"] == 1 and p["sites_x_llms"] == 84 and not p["lp_point"]
    assert p["n_sites_merged"] is None and p["n_sites_merged_note"] and p["bl0a_usd"] == {"1": 201.0}
    pe = p["policies"]["Sublet"]
    assert pe["n_runs"] == 1 and pe["median"]["slow_loop_s_per_h"] == pytest.approx(73 / 24)
    assert pe["by_alignment"]["1"]["certificate_case"] == "W(a)" and pe["certificates"]["n"] == 1
    assert p["policies"]["A6"]["certificates"] is None and p["policies"]["A6"]["certificates_note"]
    assert s["points"]["e7r_V8_SML"]["n_sites_merged"] == 21.0 and s["points"]["e7r_V8_SML"]["lp_point"]
    lp = s["lp"]["e7r_V8_SML"]
    assert lp["n_runs"] == 1 and lp["median"]["s_per_h"] == 10.0 and lp["by_alignment"]["1"]["highs_model_status"] == 7
    assert lp["by_alignment"]["1"]["instance_hash_equal_runs"] is True
    big = s["checks"]["E9-5"]["largest_point_by_menu"]
    assert big["full"]["point"] == "e7f_V64_SML" and big["reduced"]["point"] == "e7r_V64_SML"
    assert big["full"]["policies"]["Sublet"]["real_time_over_loops"] == pytest.approx(3600 / (73 / 24 + 1.0))
    assert (out / "tables.md").read_text().startswith("# E9: scalability")
    json.dumps(s, allow_nan=False)
    # an entry without runs keeps every field of its non-null form (§2.6)
    empty = e9.policy_entry([], "Sublet")
    assert {k for k in empty if not k.endswith("note")} == {k for k in pe if not k.endswith("note")}
    assert set(empty["median"]) - {k for k in empty["median"] if k.endswith("_note")} == set(e9.RUN_METRICS)
    el = e9.lp_entry([])
    assert el["n_runs"] == 0 and el["median"]["s_per_h"] is None and el["median"]["s_per_h_note"]

    def check(jid, *, status="ok", data=None, keep=False):
        if not keep:
            _write(out, jid, status, data)
        return e9.summary(out)["checks"]
    rid, lid = e9.run_id("e7f_V8_S", "A6", 1), e9.lp_id("e7r_V4_SML", 1)
    good_r, good_l = _run_file("e7f_V8_S", "A6", 1), _lp_file("e7r_V4_SML", 1)
    # E9-1: a failed job fails, a missing run file leaves it missing, an invariant failure or the cap fails
    ch = check(rid, status="oom_at_3G")
    assert ch["E9-1"]["status"] == "fail" and ch["E9-1"]["failed"][0]["status"] == "oom_at_3G"
    assert {"job": rid, "status": "oom_at_3G", "output": f"runs/{mc.job_file_name(rid)}"} in \
        e9.summary(out)["meta"]["ignored_outputs"]                  # an output whose record is not 'ok' is not used
    e9.run_path(out, rid).unlink()
    ch = check(rid)                                                 # an 'ok' record without its run file
    assert ch["E9-1"]["status"] == "missing" and ch["E9-1"]["n_missing"] == 1
    assert ch["E9-1"]["missing"][0]["note"] == "ok record without its run file"
    ch = check(rid, status="running", data=good_r)
    assert ch["E9-1"]["status"] == "missing" and ch["E9-1"]["missing"][0]["note"] == "no 'ok' record"
    assert check(rid, data=_run_file("e7f_V8_S", "A6", 1, inv=2))["E9-1"]["status"] == "fail"
    assert check(rid, data=_run_file("e7f_V8_S", "A6", 1, fits=False))["E9-1"]["n_over_cap"] == 1
    # E9-2: a step sum above the wall, a wrong count
    ch = check(rid, data=_run_file("e7f_V8_S", "A6", 1, rt=_rt(1, finish_s=10.0)))
    assert ch["E9-2"]["status"] == "fail" and ch["E9-2"]["failures"][0]["job"] == rid and ch["E9-1"]["status"] == \
        "pass"
    assert check(rid, data=_run_file("e7f_V8_S", "A6", 1, rt=_rt(1, n_fast_steps=1439)))["E9-2"]["status"] == "fail"
    check(rid, data=good_r)
    # E9-3: an unavailable certificate, a proven case not held fail; W(c) is counted
    sid = e9.run_id("e7f_V8_S", "Sublet", 1)
    for a8, st in ((_a8(available=False, case="unavailable", held=None), "fail"), (_a8("W(b)", False, t_a=3), "fail"),
                   (_a8("W(c)", False, t_a=3), "pass")):
        ch = check(sid, data=_run_file("e7f_V8_S", "Sublet", 1, a8=a8))
        assert ch["E9-3"]["status"] == st, a8
    assert ch["E9-3"]["n_w_c"] == 1 and ch["E9-3"]["certificates"]["by_case"]["W(c)"]["runs"] == 1
    check(sid, data=_run_file("e7f_V8_S", "Sublet", 1))
    # E9-4: an LP skipped by the gate, not optimal, or a failed LP job fails; a missing one leaves it missing
    assert check(lid, data=_lp_file("e7r_V4_SML", 1, skipped=True))["E9-4"]["status"] == "fail"
    assert check(lid, data=_lp_file("e7r_V4_SML", 1, status=1, highs=13))["E9-4"]["n_not_optimal"] == 1
    assert check(lid, data=_lp_file("e7r_V4_SML", 1, highs=8))["E9-4"]["status"] == "fail"
    assert check(lid, status="wall_limit", data=good_l)["E9-4"]["status"] == "fail"
    mc.record_path(out, lid).unlink()
    assert check(lid, keep=True)["E9-4"]["status"] == "missing"
    ch = check(lid, data=good_l)
    assert [ch[k]["status"] for k in e9.CHECK_IDS] == ["pass"] * 4 + ["informative"]
    # no outputs at all: every property check missing
    s0 = e9.summary(tmp_path / "empty")
    assert [s0["checks"][k]["status"] for k in e9.CHECK_IDS] == ["missing"] * 4 + ["informative"]
    assert s0["points"]["e7r_V1_SML"]["n_sites"] is None and s0["points"]["e7r_V1_SML"]["n_sites_note"]
    json.dumps(s0, allow_nan=False)


# ---------------------------------------------------------------- run_e9.sh with a fake driver
FAKE_DRIVER = '''
import json, os, sys, time
from sublet.experiments import ms3_common as mc

SPEC = json.loads(os.environ["FAKE_JOBS"])          # [[id, limit s, sleep s], ...]

def jobs():
    return [mc.Job(j, "alone", {"limit_s": lim, "sleep": sl}) for j, lim, sl in SPEC]

def run(job, outputs, out):
    t0 = time.time()
    with open(os.environ["FAKE_EVENTS"], "a") as f:
        f.write(f"start {job.id} {t0} {os.environ.get('MS3_SLOTS')}\\n")
    time.sleep(job.params["sleep"])
    with open(os.environ["FAKE_EVENTS"], "a") as f:
        f.write(f"end {job.id} {time.time()}\\n")
    outputs.dump({"meta": {"git_revision": "x"}}, out / "runs" / mc.job_file_name(job.id))
    return {"runs": 1}

def summary(out):
    mc.dump_json({"records": {k: v.get("status") for k, v in mc.read_records(out).items()}}, out / "summary.json")

if __name__ == "__main__":
    if "--limits" in sys.argv:
        sys.stdout.write("".join(f"{lim} {j}\\n" for j, lim, _ in SPEC))
        sys.exit(0)
    sys.exit(mc.main("e9", jobs=jobs, run=run, summary=summary))
'''


def _scope_env() -> dict:
    if shutil.which("systemd-run") is None:
        return {"MS3_SCOPE": "0"}
    r = subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0",
                        "true"], capture_output=True, timeout=60)
    return {} if r.returncode == 0 else {"MS3_SCOPE": "0"}


def _run_script(tmp_path: Path, spec: list, events: str = "events.txt", **extra):
    root = tmp_path / "root"
    (root / "out" / "e11").mkdir(parents=True, exist_ok=True)
    (root / "out" / "e11" / "summary.json").write_text("{}\n")
    mod = tmp_path / "mod"
    mod.mkdir(exist_ok=True)
    (mod / "fake_e9.py").write_text(FAKE_DRIVER)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "FAKE_", "E9_"))}
    env.update(MS3_ROOT=str(root), MS3_WORKERS="2", MS3_POLL_S="0.2", MS3_PY=sys.executable, MS3_MODULE="fake_e9",
               PYTHONPATH=os.pathsep.join([str(mod), str(SIM)]), FAKE_JOBS=json.dumps(spec),
               FAKE_EVENTS=str(tmp_path / events), **_scope_env(), **extra)
    p = subprocess.run(["bash", str(RUN_E9)], env=env, capture_output=True, text=True, timeout=300)
    ev = {}
    f = tmp_path / events
    for line in (f.read_text().splitlines() if f.is_file() else []):
        kind, jid, t, *rest = line.split()
        ev.setdefault(jid, {})[kind] = float(t)
        if rest:
            ev[jid]["slots"] = rest[0]
    return p, ev, root / "out" / "e9"


SPEC = [["e9:run:pt=e7f_V1_SML:pol=Sublet:c=1", 30, 0.3], ["e9:run:pt=e7f_V1_SML:pol=A6:c=1", 30, 0.3],
        ["e9:run:pt=e7f_V2_SML:pol=Sublet:c=1", 1, 5.0], ["e9:lp:pt=e7r_V1_SML:c=1", 30, 0.3]]


def test_run_script_alone_in_order_with_limits(tmp_path):
    p, ev, out = _run_script(tmp_path, SPEC, MS3_E9_TEST_GRACE_S="0")
    assert p.returncode == 0, p.stdout + p.stderr
    ids = [s[0] for s in SPEC]
    assert set(ev) == set(ids)
    starts = sorted(ids, key=lambda j: ev[j]["start"])
    assert starts == ids                                        # in list order
    for a, b in zip(ids, ids[1:]):                              # one at a time (the killed job has no end)
        assert ev[b]["start"] >= ev[a].get("end", ev[a]["start"] + 1.0), (a, b)
    assert all(ev[j]["slots"] == "slot0,slot1" for j in ids)    # every slot (MS3_WORKERS=2)
    recs = mc.read_records(out)
    killed = recs[ids[2]]
    assert killed["status"] == "wall_limit" and killed["exit_code"] == 124 and killed["timeout_limit_s"] == 1.0
    assert "end" not in ev[ids[2]] and ev[ids[3]]["start"] >= ev[ids[2]]["start"] + 1.0
    assert all(recs[j]["status"] == "ok" for j in ids if j != ids[2])
    assert recs["e9:manifest"]["status"] == "ok" and recs["e9:summary"]["status"] == "ok"
    assert (out / "jobs_limits.txt").read_text().split() == " ".join(f"{s[1]} {s[0]}" for s in SPEC).split()
    assert (out / "jobs_list.txt").read_text().split() == " ".join(f"alone {s[0]}" for s in SPEC).split()
    log = (out / "run_e9.log").read_text()
    assert f"alone {ids[2]} holds slot0,slot1, limit 1 s" in log and "alone jobs done (4 run)" in log
    assert log.rstrip().splitlines()[-1].startswith("[run_e9] done ")
    assert json.loads((out / "summary.json").read_text())["records"][ids[2]] == "wall_limit"


def test_run_script_only_and_resume(tmp_path):
    fast = [[j, 30, 0.2] for j, _, _ in SPEC]
    p, ev, out = _run_script(tmp_path, fast, E9_ONLY=r"^e9:run:pt=e7f_V1_SML:")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == {SPEC[0][0], SPEC[1][0]}
    assert "E9_ONLY='^e9:run:pt=e7f_V1_SML:': only the matching jobs run" in (out / "run_e9.log").read_text()
    p, ev, out = _run_script(tmp_path, fast, events="events2.txt", MS3_RESUME="1")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == {SPEC[2][0], SPEC[3][0]}                   # the ok jobs are skipped
    log = (out / "run_e9.log").read_text()
    assert f"{SPEC[0][0]}: ok before, skipped" in log
    p = subprocess.run(["bash", str(RUN_E9), "--bogus"], capture_output=True, text=True, timeout=60)
    assert p.returncode == 2 and "usage" in p.stderr


def test_run_script_parses():
    assert subprocess.run(["bash", "-n", str(RUN_E9)]).returncode == 0
    assert os.access(RUN_E9, os.X_OK)


# ---------------------------------------------------------------- instances (needs a12)
@pytest.mark.needs_a12
def test_point_sizes_against_the_grid():
    grid = json.loads(GRID.read_text())["points"]
    for point in ("e7f_V1_SML", "e7r_V8_SML", "e7f_V8_S"):
        inst, model, ecfg, _ = e9.build_point(point, 1, e9.DAY_MIN)
        sz, want = e9.instance_sizes(inst), grid[point]["instance"]
        for k in ("n_sites", "n_sites_by_kind", "n_units", "sites_x_llms", "n_clients", "n_contracts", "n_llms"):
            assert sz[k] == want[k], (point, k)
        assert sz["bl0a_usd"] == pytest.approx(want["bl0a_usd"], rel=1e-12)
        assert ecfg.check_invariants and (model.schedule, model.information, model.on_unavailable,
                                          model.violations) == ("trace", "I1", "sell", "absorb")
        assert inst.config["lender_model"]["merge_identical_layers"] is False
        assert (inst.grid.T_slow, inst.grid.T_fast) == (288, 1440)
        assert e9.tag_params("Sublet", inst) == m4.sublet_params(inst, "BL5") and e9.tag_params("A6", inst) == {}


# ---------------------------------------------------------------- run_e9.sh --reduced end to end (needs a12)
@pytest.mark.needs_a12
@pytest.mark.slow
def test_run_script_reduced_end_to_end(tmp_path):
    """run_e9.sh --reduced under a scratch MS3_ROOT, with E9_ONLY on the smallest run point (both policies) and the
    smallest LP point; the other jobs stay missing."""
    root = tmp_path / "root"
    (root / "out" / "e11").mkdir(parents=True)
    (root / "out" / "e11" / "summary.json").write_text("{}\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "E9_"))}
    env.update(MS3_ROOT=str(root), MS3_POLL_S="0.5", MS3_PY=sys.executable, **_scope_env(),
               E9_ONLY=r"^e9:(run:pt=e7f_V1_SML:|lp:pt=e7r_V1_SML:)")
    p = subprocess.run(["bash", str(RUN_E9), "--reduced"], env=env, capture_output=True, text=True, timeout=1200,
                       cwd=str(SIM))
    assert p.returncode == 0, p.stdout + p.stderr
    out = root / "out" / "e9"
    s = json.loads((out / "summary.json").read_text())
    assert s["meta"]["reduced"] is True and s["meta"]["git_revision"] and list(s["checks"]) == list(e9.CHECK_IDS)
    assert s["meta"]["jobs_ok"] == 3 and len(s["meta"]["jobs_missing"]) == 36
    ch = s["checks"]
    assert ch["E9-2"]["status"] == "pass" and ch["E9-2"]["grids"] == [[24, 120]] and ch["E9-3"]["status"] == "pass"
    assert ch["E9-1"]["status"] == "missing" and ch["E9-1"]["n_failed"] == 0 and ch["E9-1"]["n_runs"] == 2
    assert ch["E9-4"]["status"] == "missing" and ch["E9-4"]["n_not_optimal"] == 0 and ch["E9-4"]["n_lps"] == 1
    lp = s["lp"]["e7r_V1_SML"]["by_alignment"]["1"]
    assert lp["status"] == 0 and lp["highs_model_status"] == 7 and lp["objective_over_bl0a"] > 0
    for tag in ("Sublet", "A6"):
        r = s["points"]["e7f_V1_SML"]["policies"][tag]["by_alignment"]["1"]
        assert (r["n_slow_steps"], r["n_fast_steps"]) == (24, 120) and r["n_invariant_failures"] == 0
        assert r["slow_loop_s_per_h"] > 0 and r["setup_s"] >= r["reset_s"] >= 0 and r["steps_ok"] is True
    a = s["points"]["e7f_V1_SML"]["policies"]["Sublet"]["by_alignment"]["1"]
    assert a["B0_rule"] == m4.B0_RULE and a["certificate_case"] in m4.CASES
    recs = mc.read_records(out)
    for jid in (e9.run_id("e7f_V1_SML", "Sublet", 1), e9.run_id("e7f_V1_SML", "A6", 1), e9.lp_id("e7r_V1_SML", 1)):
        assert recs[jid]["status"] == "ok" and recs[jid]["git_revision"], jid
        f = json.loads(e9.run_path(out, jid).read_text())
        assert f["meta"]["git_revision"] == recs[jid]["git_revision"] and f["meta"]["reduced"] is True
        assert f["meta"]["loadavg_start"] is not None and f["horizon_min"] == 120
    man = json.loads((out / "manifest.json").read_text())
    assert len(man["jobs"]) == 39 and len(man["instance_hashes"]) == 16
    assert man["instance_hashes"]["e7f_V1_SML:c=1"] == s["points"]["e7f_V1_SML"]["by_alignment"]["1"]["instance_hash"]
    log = (out / "run_e9.log").read_text()
    assert log.rstrip().splitlines()[-1].startswith("[run_e9] done ") and "limit 900 s" in log and "limit 1800 s" in log
