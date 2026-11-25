"""Tests of E9 v2: sublet/experiments/e9v2.py (with TimedProjectedGuarded), run_e9v2.sh and the E9 v2 rules of
ms7_sens_analysis.py (design/ms7/plan.md X3; design/ms7/feasibility/sens.md §2 D, §3 items 4, 5, 7; change C56).

Quick (no raw data):
- the job list: FIRST_JOB (e7f_V64_SML, Sublet, c 1) first, then the other 127 runs (16 points x Sublet and A9 x 4
  alignments) and 16 split jobs, all 'alone'; the reduced list (alignment 1, a 2-hour horizon);
- the limits: FIRST_LIMIT_S for the first job, the static limits (floors, three times the estimate) before it has a
  record, and limits scaled by its wall time over its estimate (never below the static ones) once it is 'ok'; the
  estimates scale E9's measured Sublet-MS4 day (out/e9/summary.json), with e9.est_run_s as the fallback;
- TimedProjectedGuarded: Sublet's run with the timers equals the uninstrumented run bit for bit (the digests: ALG, the
  components, the per-slot cost series, the policy report, the schedule hash) on ms2_multi_small under a stress
  lender, and its split adds up (guard = act - inner, the parts and 'other'); timed() refuses another class;
- the summary on synthetic run files (E9v2-4 against a synthetic E9 summary, E9v2-5 with an equal and a different
  split, the split used only when identical) and the analysis's per-slot overhead (Sublet - A9);
- run_e9v2.sh with a fake driver: the first job alone first, the limits again after it, the rest, the gate refusal,
  and bash -n.
With the a12 outputs (needs_a12, slow): the reduced run jobs of e7r_V1_SML (Sublet and A9) and its split job through
the runner, with E9v2-5 passing and the analysis's overhead on them; the timed guard on example_1day under L-eg.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from fixtures import SIM

from sublet.experiments import e9
from sublet.experiments import e9v2
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms5b_common as m5
from sublet.experiments import ms7_sens_analysis as sa
from sublet.experiments import s1v2 as sv

RUN = SIM / "sublet" / "experiments" / "run_e9v2.sh"


@pytest.fixture()
def full(monkeypatch):
    monkeypatch.delenv(e9v2.REDUCED_ENV, raising=False)


def test_job_list(full):
    js = e9v2.jobs()
    mc.check_jobs(js)
    assert js[0].id == e9v2.FIRST_JOB == "e9v2:run:pt=e7f_V64_SML:pol=Sublet:c=1"
    runs = [j for j in js if j.params["kind"] == "run"]
    splits = [j for j in js if j.params["kind"] == "split"]
    assert len(runs) == 128 and len(splits) == 16 and all(j.kind == "alone" for j in js)
    assert {(j.params["point"], j.params["tag"], j.params["c"]) for j in runs} == \
        {(p, t, c) for p in e9.RUN_POINTS for t in ("Sublet", "A9") for c in e9.ALIGNMENTS}
    assert {j.params["point"] for j in splits} == set(e9.RUN_POINTS) and {j.params["c"] for j in splits} == {1}
    assert js[-16:] == splits and all(j.params["horizon_min"] == e9.DAY_MIN for j in js)


def test_reduced_list(monkeypatch):
    monkeypatch.setenv(e9v2.REDUCED_ENV, "1")
    js = e9v2.jobs()
    assert len(js) == 16 * 2 + 16 and {j.params["c"] for j in js} == {1}
    assert all(j.params["horizon_min"] == 120 for j in js) and js[0].id == e9v2.FIRST_JOB


def test_limits(full, tmp_path):
    lim = dict((j, l) for l, j in e9v2.limits(tmp_path))
    js = {j.id: j for j in e9v2.jobs()}
    assert lim[e9v2.FIRST_JOB] == e9v2.FIRST_LIMIT_S
    for jid, j in js.items():
        if jid != e9v2.FIRST_JOB:
            assert lim[jid] == j.params["limit_s"] >= max(900, 3 * j.est_s - 1)
    assert lim[e9v2.run_id("e7f_V64_SML", "A9", 2)] >= 7200
    first = js[e9v2.FIRST_JOB]
    mc.dump_json({"job": e9v2.FIRST_JOB, "status": "ok", "wall_s": 2.0 * first.est_s},
                 mc.record_path(tmp_path, e9v2.FIRST_JOB))
    lim2 = dict((j, l) for l, j in e9v2.limits(tmp_path))
    for jid, j in js.items():
        if jid != e9v2.FIRST_JOB:
            assert lim2[jid] >= lim[jid] and lim2[jid] >= 6 * j.est_s - 1
    mc.dump_json({"job": e9v2.FIRST_JOB, "status": "ok", "wall_s": 0.01 * first.est_s},
                 mc.record_path(tmp_path, e9v2.FIRST_JOB))
    assert dict((j, l) for l, j in e9v2.limits(tmp_path)) == lim          # never below the static limits


def test_estimates_use_e9s_measured_days(full, monkeypatch):
    """est_run_s scales E9's measured Sublet-MS4 day (out/e9/summary.json, median job_s) by SUBLET_OVER_MS4 and falls
    back to e9.est_run_s without a summary value."""
    e9s = mc.read_json(e9v2.E9_SUMMARY)
    monkeypatch.setattr(e9v2, "_E9_DAY", {})
    for p in ("e7f_V64_SML", "e7f_V32_SML", "e7r_V8_SML"):
        day = e9s["points"][p]["policies"]["Sublet"]["median"]["job_s"]
        V = e9.parse_point(p)[1]
        s = e9v2.SUBLET_OVER_MS4.get(V, 2.0) * day
        assert e9v2.e9_day_s(p) == pytest.approx(day)
        assert e9v2.est_run_s(p, "Sublet") == pytest.approx(s + e9v2.A9_TABLE_S.get(V, e9v2.EST_TABLE_S))
        assert e9v2.est_run_s(p, "A9") == pytest.approx(e9v2.A9_OVER_SUBLET * s
                                                         + e9v2.A9_TABLE_S.get(V, e9v2.EST_TABLE_S))
    monkeypatch.setattr(e9v2, "_E9_DAY", {"points": {}})
    assert e9v2.e9_day_s("e7f_V8_SML") == pytest.approx(e9.est_run_s("e7f_V8_SML", "Sublet"))


def _small(mode_p: float = 0.3, horizon: int = 240):
    from sublet.drivers import run as drun
    spec = drun.load_run_spec({"schema_version": 1, "name": "t9", "instance": "ms2_multi_small.json",
                               "overrides": {"time.horizon_min": horizon},
                               "lender_model": {"schedule": "iid_step", "params": {"D_slots": 1, "p": mode_p}},
                               "engine": {"check_invariants": True},
                               "policy": {"id": "A8P", "params": m5.sublet_v2_params()}})
    inst, model, ecfg = drun.build(spec, 1)
    return spec, inst, model, ecfg


def test_timed_guard_is_bit_for_bit():
    from sublet.drivers import run as drun
    from sublet.engine import simulate
    for p in (0.3, 0.8):
        spec, inst, model, ecfg = _small(p)
        a = simulate(inst, drun.make_policy(spec, inst), model, ecfg, lender_seed=1, policy_seed=0)
        pol = e9v2.timed(drun.make_policy(spec, inst))
        assert type(pol) is e9v2.TimedProjectedGuarded
        b = simulate(inst, pol, model, ecfg, lender_seed=1, policy_seed=0)
        assert e9v2.digests(a) == e9v2.digests(b), p
        assert a.metrics["policy"] == b.metrics["policy"]
        sr = e9v2.split_record(pol, inst.grid.T_slow)
        n = inst.grid.T_slow
        assert sr["counts"]["slots"] == n == len(pol.split_slots)
        m = sr["per_slot_mean_s"]
        assert m["guard"] == pytest.approx(m["act"] - m["inner_act"], abs=1e-12)
        assert m["other"] == pytest.approx(m["guard"] - m["lb"] - m["safe"] - m["test"] - m["projection"],
                                           abs=1e-12)
        assert sr["totals_s"]["act"] >= sr["totals_s"]["inner_act"] > 0 and sr["totals_s"]["lb"] > 0
        assert sr["counts"]["evaluations"] >= n
    with pytest.raises(TypeError):
        e9v2.timed(object())


def _runfile(point, tag, c, act, slow, kind="run", digest="d", ih="H", split=None):
    f = {"meta": {"job": (e9v2.split_id(point, c) if kind == "split" else e9v2.run_id(point, tag, c)),
                  "loadavg_start": [0.1, 0.1, 0.1]},
         "kind": kind, "point": point, "tag": tag, "c": c, "instance_hash": ih, "digests": {"ALG": 1.0, "x": digest},
         "timing": {"slow_loop_s_per_h": slow, "hours": 2.0, "n_slow_steps": 24, "policy_act_s_mean": act,
                    "policy_act_s_sum": act * 24},
         "instance": {"n_sites": 10, "sites_x_llms": 30, "grid": {"T_slow": 24, "T_fast": 120}},
         "memory": {"peak_rss_mb": 100.0, "fits_cap": True}, "runs": [{"r0": 0.5, "n_invariant_failures": 0}]}
    if split is not None:
        f["split"] = split
    return f


def test_summary_and_analysis(full, tmp_path, monkeypatch):
    monkeypatch.setattr(sv, "registration_record", lambda: {"registration_at_head": False, "dirty_paths": []})
    monkeypatch.setattr(sv, "_GATE", {})
    p = "e7r_V1_SML"
    e9s = {"meta": {"horizon_min": e9.DAY_MIN},
           "points": {p: {"by_alignment": {"1": {"instance_hash": "H"}, "2": {"instance_hash": "H2"}}}},
           "lp": {p: {"n_runs": 4}}}
    f9 = tmp_path / "e9summary.json"
    mc.dump_json(e9s, f9)
    monkeypatch.setattr(e9v2, "E9_SUMMARY", f9)
    out = tmp_path / "out"
    files = [_runfile(p, "Sublet", 1, 0.03, 5.0), _runfile(p, "A9", 1, 0.01, 4.0),
             _runfile(p, "Sublet", 2, 0.05, 6.0, ih="X"), _runfile(p, "A9", 2, 0.02, 5.0, ih="H2"),
             _runfile(p, "Sublet", 1, 0.03, 5.0, kind="split",
                      split={"per_slot_mean_s": {"guard": 0.02, "act": 0.03, "inner_act": 0.01}})]
    for f in files:
        mc.dump_json({"job": f["meta"]["job"], "status": "ok"}, mc.record_path(out, f["meta"]["job"]))
        mc.dump_json(f, e9v2.run_path(out, f["meta"]["job"]))
    s = e9v2.summary(out)
    e = s["points"][p]
    assert e["split"]["identical"] is True and e["split"]["split"]["per_slot_mean_s"]["guard"] == 0.02
    assert s["checks"]["E9v2-5"]["status"] == "missing"          # the other 15 points have no split
    assert s["checks"]["E9v2-4"]["status"] == "fail" and s["checks"]["E9v2-4"]["differ"][0]["instance_hash"] == "X"
    assert s["lp"] == {p: {"n_runs": 4}}
    a = sa.analyse_e9v2(json.loads((out / "summary.json").read_text()))
    x = a["points"][p]
    assert x["by_alignment"]["1"]["act_overhead_s_per_slot"] == pytest.approx(0.02)
    assert x["by_alignment"]["1"]["slow_step_overhead_s_per_slot"] == pytest.approx((5.0 - 4.0) * 2.0 / 24)
    assert x["act_overhead_s_per_slot_median"] == pytest.approx(0.025) and x["act_ratio_median"] == pytest.approx(
        (3.0 + 2.5) / 2)
    assert x["split"]["per_slot_mean_s"]["guard"] == 0.02
    h = a["headline"]
    assert h["act_overhead_s_per_slot_max"] == pytest.approx(0.025) and h["act_overhead_s_per_slot_max_point"] == p
    assert h["act_ratio_max"] == pytest.approx(2.75) and h["peak_rss_mb_max"] == 100.0
    assert set(h["largest_point_by_menu"]) == {"full", "reduced"} and h["cap_mb"] == e9.CAP_MB
    assert h["largest_point_by_menu"]["full"]["point"] == e9.LARGEST["e7f"] and sa.LARGEST["reduced"] == \
        e9.LARGEST["e7r"] and sa.REAL_TIME_S_PER_H == e9.REAL_TIME_S_PER_H
    assert sa._real_time(400.0) == pytest.approx(9.0) and sa._real_time(None) is None
    # a split that differs from its run is not used
    bad = _runfile(p, "Sublet", 1, 0.03, 5.0, kind="split", digest="other", split={"per_slot_mean_s": {}})
    mc.dump_json(bad, e9v2.run_path(out, bad["meta"]["job"]))
    s = e9v2.summary(out)
    assert s["checks"]["E9v2-5"]["status"] == "fail" and "split" not in s["points"][p]["split"]
    assert s["checks"]["E9v2-5"]["splits"][0]["differs"] == ["x"]
    # E9's summary at another horizon (a reduced run) is no reference: no instance comparison, no LP copy
    e9s["meta"]["horizon_min"] = 120
    mc.dump_json(e9s, f9)
    s = e9v2.summary(out)
    assert s["checks"]["E9v2-4"]["status"] == "missing" and s["checks"]["E9v2-4"]["same_scale"] is False
    assert s["lp"] is None


# ---------------------------------------------------------------- run_e9v2.sh with a fake driver
FAKE_DRIVER = '''
import json, os, sys, time
from sublet.experiments import ms3_common as mc

def jobs():
    return [mc.Job(j, "alone", {"sleep": s, "limit_s": lim}) for j, s, lim in json.loads(os.environ["FAKE_JOBS"])]

def run(job, outputs, out):
    t0 = time.time()
    time.sleep(job.params["sleep"])
    with open(os.environ["FAKE_EVENTS"], "a") as f:
        f.write(f"{job.id} {t0} {time.time()}\\n")
    return {"runs": 0}

def summary(out):
    mc.dump_json({"records": len(mc.read_records(out))}, out / "summary.json")

if __name__ == "__main__":
    if "--check-start" in sys.argv:
        ok = os.environ.get("FAKE_GATE", "1") == "1"
        print(f"[e9v2] gate {'ok' if ok else 'REFUSED'}")
        sys.exit(0 if ok else 1)
    if "--limits" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
        first = jobs()[0].id
        done = (mc.read_record(out, first) or {}).get("status") == "ok"
        with open(os.environ["FAKE_EVENTS"], "a") as f:
            f.write(f"limits:{int(done)} {time.time()} {time.time()}\\n")
        for j in jobs():
            print(f"{j.params['limit_s'] * (2 if done else 1)} {j.id}")
        sys.exit(0)
    sys.exit(mc.main("e9v2", jobs=jobs, run=run, summary=summary))
'''


def _scope_env() -> dict:
    if shutil.which("systemd-run") is None:
        return {"MS3_SCOPE": "0"}
    r = subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0",
                        "true"], capture_output=True, timeout=60)
    return {} if r.returncode == 0 else {"MS3_SCOPE": "0"}


def _run_fake(tmp_path: Path, jobs: list, events: str = "events.txt", **extra):
    root = tmp_path / "root"
    (root / "out" / "e11").mkdir(parents=True, exist_ok=True)
    (root / "out" / "e11" / "summary.json").write_text("{}\n")
    mod = tmp_path / "mod"
    mod.mkdir(exist_ok=True)
    (mod / "fake_e9v2.py").write_text(FAKE_DRIVER)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "FAKE_", "E9V2_"))}
    env.update(MS3_ROOT=str(root), MS3_WORKERS="2", MS3_POLL_S="0.2", MS3_PY=sys.executable, MS3_MODULE="fake_e9v2",
               PYTHONPATH=os.pathsep.join([str(mod), str(SIM)]), FAKE_JOBS=json.dumps(jobs),
               FAKE_EVENTS=str(tmp_path / events), **_scope_env(), **extra)
    p = subprocess.run(["bash", str(RUN)], env=env, capture_output=True, text=True, timeout=300)
    ev = {}
    f = tmp_path / events
    for line in (f.read_text().splitlines() if f.is_file() else []):
        jid, t0, t1 = line.split()
        ev.setdefault(jid, []).append((float(t0), float(t1)))
    return p, ev, root / "out" / "e9v2"


FAKE_JOBS = [["e9v2:run:pt=e7f_V64_SML:pol=Sublet:c=1", 0.3, 30], ["e9v2:run:pt=e7f_V1_SML:pol=A9:c=1", 0.2, 30],
             ["e9v2:split:pt=e7f_V1_SML:c=1", 0.2, 30]]


def test_run_script_first_job_then_limits_then_rest(tmp_path):
    p, ev, out = _run_fake(tmp_path / "ok", FAKE_JOBS)
    assert p.returncode == 0, p.stdout + p.stderr
    first = ev["e9v2:run:pt=e7f_V64_SML:pol=Sublet:c=1"][0]
    assert ev["limits:0"][0][1] <= first[0] and first[1] <= ev["limits:1"][0][0]
    assert ev["limits:1"][0][1] <= ev["e9v2:run:pt=e7f_V1_SML:pol=A9:c=1"][0][0]
    assert ev["e9v2:run:pt=e7f_V1_SML:pol=A9:c=1"][0][1] <= ev["e9v2:split:pt=e7f_V1_SML:c=1"][0][0]
    assert (out / "jobs_limits.txt").read_text().split("\n")[1] == "60 e9v2:run:pt=e7f_V1_SML:pol=A9:c=1"
    recs = mc.read_records(out)
    assert all(recs[j]["status"] == "ok" for j, *_ in FAKE_JOBS) and recs["e9v2:summary"]["status"] == "ok"
    log = (out / "run_e9v2.log").read_text()
    assert "timed alone" in log and log.rstrip().splitlines()[-1].startswith("[run_e9v2] done ")
    p, ev, out = _run_fake(tmp_path / "refused", FAKE_JOBS, events="ev2.txt", FAKE_GATE="0")
    assert p.returncode == 2 and not any(k.startswith("e9v2:") for k in ev)


def test_run_script_parses():
    assert subprocess.run(["bash", "-n", str(RUN)]).returncode == 0
    assert os.access(RUN, os.X_OK)


# ---------------------------------------------------------------- with the a12 outputs
@pytest.mark.needs_a12
@pytest.mark.slow
def test_reduced_runs_and_split_through_the_runner(tmp_path, monkeypatch):
    monkeypatch.setenv(e9v2.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_ROOT", str(tmp_path))
    monkeypatch.setattr(sv, "_GATE", {})
    out = tmp_path / "out" / "e9v2"
    js = {j.id: j for j in e9v2.jobs()}
    p = "e7r_V1_SML"
    for jid in (e9v2.run_id(p, "Sublet", 1), e9v2.run_id(p, "A9", 1), e9v2.split_id(p, 1)):
        rec = mc.run_job("e9v2", js[jid], lambda o, j=js[jid]: e9v2.run(j, o, out), out, resume=False)
        assert rec["status"] == "ok", rec.get("error")
    s = e9v2.summary(out)
    e = s["points"][p]
    assert e["split"]["identical"] is True and e["split"]["split"]["counts"]["slots"] == 24
    assert s["checks"]["E9v2-5"]["splits"] == [{"point": p, "c": 1, "equal": True, "differs": []}]
    assert e["policies"]["Sublet"]["by_alignment"]["1"]["policy_act_s_mean"] > 0
    a = sa.analyse_e9v2(json.loads((out / "summary.json").read_text()))
    assert a["points"][p]["by_alignment"]["1"]["act_overhead_s_per_slot"] is not None


@pytest.mark.needs_a12
@pytest.mark.slow
def test_timed_guard_on_example_1day():
    from sublet.drivers import run as drun
    from sublet.engine import simulate
    spec = drun.load_run_spec({"schema_version": 1, "name": "t9d", "instance": "example_1day.json",
                               "overrides": {"time.horizon_min": 360},
                               "lender_model": m5.mode_lender_model("L-eg"), "engine": {"check_invariants": True},
                               "policy": {"id": "A8P", "params": m5.sublet_v2_params()}})
    inst, model, ecfg = drun.build(spec, 1)
    a = simulate(inst, drun.make_policy(spec, inst), model, ecfg, lender_seed=1, policy_seed=0)
    pol = e9v2.timed(drun.make_policy(spec, inst))
    b = simulate(inst, pol, model, ecfg, lender_seed=1, policy_seed=0)
    assert e9v2.digests(a) == e9v2.digests(b)
