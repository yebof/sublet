"""Tests of the shared MS3 driver layer (design/sim_spec_ms3.md §2.4-§2.6, §0 items 2-3, §10).

- Q39's lower-bound rule on synthetic SolveResults (lb_record: LP above and below the dual bound, gap at and
  above 1e-4, a MILP without incumbent, a killed MILP, invalid ratios) and the bracket rule of M4 (oracle: hand
  computation, and lo <= true ratio <= hi on random benchmark values);
- ratio_of_means against a hand computation of the ratio and of its run bootstrap;
- job ids, records, resume, the .partial renames, the exit-code rule of §0 item 2 on synthetic records
  (elapsed below and at LIMIT + 60 s), max_workers with and without e11/summary.json (temporary root: 4 and 0),
  the driver command line;
- check E11-0 (--check-e11) on temporary folders: an exact copy passes; a changed byte, a file missing on either
  side, or a run file with another recorded revision fails with the path named;
- the copy check of an experiment (--check-copy, §1.2 "Where the runs run") on a fake clone (a .git/HEAD and a
  fake out/<exp> tree in the drivers' shape): an exact copy passes, with its tree digest; a sha256 mismatch, a file
  on one side only, a symbolic link, a recorded revision other than the clone's commit (HEAD read as a hash, a
  loose ref or packed-refs), a JSON file without a revision (except a failure record and E2's MILP files), a
  missing or failed summary, a job record still 'running', a run log without ms3_finish's done line fail with the
  path named; malformed files (binary JSON, a folder named *.json, a list as revision) fail without a crash; e6's
  two parts;
- the slot semaphore of ms3_lib.sh with a fake driver module: two run scripts at once with N in {0, 2, 4}
  never have more than N jobs nor more than 2 MILP jobs at a time (start and end times written by the jobs),
  an 'alone' job runs with no other job, two jobs with N = 1 serialize, a killed job frees its slot and is
  recorded as oom_at_3G, MILP jobs that exit 124 or are killed early are recorded as wall_limit and
  oom_at_3G, and MS3_RESUME=1 skips the jobs whose record says ok; --list and --manifest run under the 3G cap
  (the manifest holding a slot, with a record); a waiting 'alone' job gets the slots freed while it waits (the
  turnstile). Every process is killed only by PID.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import numpy as np
import pytest

from fixtures import SIM, toy_instance

from sublet.experiments import ms3_common as mc
from sublet.experiments import q44_study as qs
from sublet.types import LenderModel, SolveResult

LIB = SIM / "sublet" / "experiments" / "ms3_lib.sh"


# ---------------------------------------------------------------- Q39's lower bound (§2.5)
def _sr(method="milp", status=1, objective=None, dual_bound=None, gap=None, grid="slow", benchmark="omega"):
    return SolveResult(method=method, benchmark=benchmark, grid=grid, status=status, status_msg="", objective=objective,
                       dual_bound=dual_bound, gap=gap, plan=None, components={}, size={}, build_s=0.0, solve_s=0.0,
                       peak_rss_mb=0.0)


def _lp(v, status=0, grid="slow"):
    return _sr("lp", status, v, v, 0.0, grid)


def test_lb_record_lp_above_and_below_the_dual_bound():
    """LB = max(LP, dual bound) with its source; ratio_LB = ALG/LB, ratio_inc = ALG/incumbent; a tie is the LP's."""
    milp = _sr(objective=120.0, dual_bound=95.0, gap=25.0 / 120.0)
    r = mc.lb_record(150.0, _lp(100.0), milp)
    assert (r["LB"], r["LB_source"], r["ratio_LB"], r["ratio_inc"]) == (100.0, "lp", 1.5, 1.25)
    assert (r["gap"], r["exact"], r["milp_status"], r["lp_status"]) == (25.0 / 120.0, False, 1, 0)
    assert (r["ALG"], r["LP"], r["dual_bound"], r["incumbent"], r["grid"]) == (150.0, 100.0, 95.0, 120.0, "slow")
    r = mc.lb_record(150.0, _lp(90.0), milp)
    assert (r["LB"], r["LB_source"], r["ratio_LB"]) == (95.0, "milp_dual", 150.0 / 95.0)
    r = mc.lb_record(150.0, _lp(95.0), milp)
    assert (r["LB"], r["LB_source"]) == (95.0, "lp")
    # a benchmark record read back from JSON gives the same record
    js = {"status": 1, "objective": 120.0, "dual_bound": 95.0, "gap": 25.0 / 120.0, "grid": "slow"}
    assert mc.lb_record(150.0, {"status": 0, "objective": 90.0, "grid": "slow"}, js) == \
        mc.lb_record(150.0, _lp(90.0), milp)
    json.dumps(r, allow_nan=False)


def test_lb_record_gap_rule():
    """exact iff the MILP's gap is at most 1e-4 (and it has an incumbent)."""
    for gap, exact in ((0.0, True), (1e-4, True), (1.0001e-4, False), (0.0136, False)):
        r = mc.lb_record(10.0, _lp(9.0), _sr(status=0 if gap == 0 else 1, objective=9.5, dual_bound=9.4, gap=gap))
        assert r["exact"] is exact, gap
        assert r["LB"] == 9.4 and r["LB_source"] == "milp_dual"


def test_lb_record_without_incumbent_and_killed():
    """A MILP at its limit without incumbent keeps its dual bound and has no ratio_inc; a MILP job killed at the hard
    wall-clock limit or by the cap (its record) or not run at all leaves the LP as LB; with no valid bound (an LP at
    a limit) LB and ratio_LB are null with notes."""
    r = mc.lb_record(10.0, _lp(7.0), _sr(status=1, objective=None, dual_bound=8.0, gap=None))
    assert (r["LB"], r["LB_source"], r["ratio_LB"], r["ratio_inc"], r["exact"]) == (8.0, "milp_dual", 1.25, None, False)
    assert "no incumbent" in r["ratio_inc_note"]
    for killed in ({"status": "wall_limit", "exit_code": 124}, {"status": "oom_at_3G", "exit_code": 137}, None):
        r = mc.lb_record(10.0, _lp(8.0), killed)
        assert (r["LB"], r["LB_source"], r["ratio_LB"], r["ratio_inc"], r["gap"], r["exact"]) == \
            (8.0, "lp", 1.25, None, None, False)
        assert r["milp_status"] == (killed or {}).get("status")
    # a MILP with status 2 (infeasible) or 4 gives no bound
    r = mc.lb_record(10.0, _lp(8.0), _sr(status=4, objective=9.0, dual_bound=9.0, gap=0.0))
    assert (r["LB"], r["LB_source"], r["incumbent"]) == (8.0, "lp", None)
    r = mc.lb_record(10.0, _lp(8.0, status=1), None)
    assert r["LB"] is None and r["ratio_LB"] is None and "no valid lower bound" in r["LB_note"]
    assert r["ratio_LB_note"]
    json.dumps(r, allow_nan=False)
    with pytest.raises(ValueError, match="different grids"):
        mc.lb_record(10.0, _lp(8.0, grid="slow"), _sr(objective=9.0, dual_bound=8.5, gap=0.05, grid="fast"))
    with pytest.raises(ValueError, match="finite"):
        mc.lb_record(float("nan"), _lp(8.0), None)


def test_lb_record_validity():
    """ratio_LB (and ratio_inc) are null with the reason of drivers.run.ratio_validity for a run whose violations
    are not absorbed, or with an explicit reason; valid on the toy (Δf = Δs) with violations absorbed; for records
    without a grid, null with the violations reason or with 'benchmark grid unknown'."""
    inst = toy_instance()
    milp = _sr(objective=9.0, dual_bound=8.5, gap=0.5 / 9.0)
    ok = mc.lb_record(10.0, _lp(8.0), milp, inst=inst, model=LenderModel())
    assert ok["ratio_LB"] == 10.0 / 8.5 and "ratio_note" not in ok
    bad = mc.lb_record(10.0, _lp(8.0), milp, inst=inst, model=LenderModel(violations="reclaim"))
    assert bad["ratio_LB"] is None and bad["ratio_inc"] is None and "violations" in bad["ratio_note"]
    assert bad["LB"] == 8.5                          # the bound itself is kept
    r = mc.lb_record(10.0, _lp(8.0), milp, reason="bench grid 'slow' on a run with 1-min routing")
    assert r["ratio_LB"] is None and r["ratio_note"].startswith("bench grid")
    # records that do not name their grid: the violations rule still applies, and with violations absorbed the
    # ratio is not reported either, since the grid rule cannot be checked
    lp_ng, milp_ng = {"status": 0, "objective": 8.0}, {"status": 1, "objective": 9.0, "dual_bound": 8.5, "gap": 0.05}
    ng = mc.lb_record(10.0, lp_ng, milp_ng, inst=inst, model=LenderModel(violations="reclaim"))
    assert ng["grid"] is None and ng["ratio_LB"] is None and ng["ratio_inc"] is None
    assert "violations" in ng["ratio_note"] and ng["LB"] == 8.5
    ng = mc.lb_record(10.0, lp_ng, milp_ng, inst=inst, model=LenderModel())
    assert ng["ratio_LB"] is None and ng["ratio_note"] == "benchmark grid unknown: ratio validity not checked"
    plain = mc.lb_record(10.0, lp_ng, milp_ng)                  # no instance given: no validity check, as before
    assert plain["ratio_LB"] == 10.0 / 8.5 and "ratio_note" not in plain


def test_bracket_rule():
    """M4: point = inc_e/inc_w, lo = LB_e/inc_w, hi = inc_e/LB_w; exact iff both gaps <= 1e-4; the true ratio of
    any optima consistent with the bounds lies in [lo, hi]."""
    e = mc.bench_values(_lp(150.0, ), _sr(objective=200.0, dual_bound=190.0, gap=0.05, benchmark="eager"))
    w = mc.bench_values(_lp(90.0), _sr(objective=100.0, dual_bound=95.0, gap=0.05))
    b = mc.bracket(e, w)
    assert (b["point"], b["lo"], b["hi"], b["exact"]) == (2.0, 1.9, 200.0 / 95.0, False)
    ex = mc.bracket(mc.bench_values(None, _sr(status=0, objective=200.0, dual_bound=199.99, gap=5e-5)),
                    mc.bench_values(None, _sr(status=0, objective=100.0, dual_bound=100.0, gap=0.0)))
    assert ex["exact"] is True and ex["lo"] <= ex["point"] <= ex["hi"]
    # lb_record outputs work as inputs, and a missing incumbent leaves the point and one end null
    nb = mc.bracket(mc.lb_record(300.0, _lp(150.0), _sr(objective=200.0, dual_bound=190.0, gap=0.05)),
                    mc.lb_record(120.0, _lp(90.0), {"status": "wall_limit"}))
    assert nb["point"] is None and nb["lo"] is None and nb["hi"] == 200.0 / 90.0 and nb["point_note"]
    rng = np.random.default_rng(3)
    for _ in range(200):
        opt_e, opt_w = rng.uniform(50, 200, size=2)
        le, lw = opt_e * rng.uniform(0.8, 1.0), opt_w * rng.uniform(0.8, 1.0)
        ie, iw = opt_e * rng.uniform(1.0, 1.2), opt_w * rng.uniform(1.0, 1.2)
        b = mc.bracket({"LB": le, "incumbent": ie}, {"LB": lw, "incumbent": iw})
        assert b["lo"] <= opt_e / opt_w <= b["hi"]
    with pytest.raises(ValueError, match="contradict"):
        mc.bracket({"LB": 10.0, "incumbent": 11.0}, {"LB": 100.0, "incumbent": 1.0})


# ---------------------------------------------------------------- aggregation (M13)
def test_ratio_of_means_by_hand():
    """E[ALG]/E[OPT] = sum ALG / sum OPT; the interval resamples run indices (one index set for both arrays per
    resample, default_rng(seed)), percentiles 2.5 and 97.5; proportional runs give a degenerate interval."""
    alg, opt = [3.0, 5.0, 4.0, 10.0, 2.0], [2.0, 2.0, 3.0, 4.0, 2.0]
    r = mc.ratio_of_means(alg, opt, B=500, seed=7)
    assert r["ratio"] == 24.0 / 13.0 and r["n"] == 5 and r["mean_alg"] == 4.8 and r["mean_opt"] == 2.6
    rng = np.random.default_rng(7)
    idx = rng.integers(0, 5, size=(500, 5))
    a, o = np.array(alg), np.array(opt)
    want = np.percentile(a[idx].sum(axis=1) / o[idx].sum(axis=1), [2.5, 97.5])
    assert r["ci95"] == [float(want[0]), float(want[1])]
    assert r["ci95"][0] <= r["ratio"] <= r["ci95"][1]
    p = mc.ratio_of_means(2 * np.arange(1.0, 9.0), np.arange(1.0, 9.0))
    assert p["ratio"] == 2.0 and p["ci95"] == pytest.approx([2.0, 2.0], abs=1e-12) and p["B"] == 2000
    assert mc.ratio_of_means(alg, opt, B=500, seed=7) == r                    # deterministic
    assert mc.ratio_of_means([], [])["ratio"] is None
    assert mc.ratio_of_means([1.0], [0.0])["ratio"] is None
    with pytest.raises(ValueError, match="paired"):
        mc.ratio_of_means([1.0, 2.0], [1.0])
    m = mc.median_summary([1.0, 2.0, 3.0])
    assert m["median"] == 2.0 and m["n"] == 3 and len(m["median_ci95"]) == 2


# ---------------------------------------------------------------- ids, JSON, outputs
def test_job_ids_and_keys():
    assert mc.job_id("e1", "cell", sched="adaptive", rho=4, mu=1, c=2) == "e1:cell:sched=adaptive:rho=4:mu=1:c=2"
    assert mc.parse_job_id("e1:cell:sched=adaptive:rho=4:mu=1:c=2") == \
        ("e1", "cell", {"sched": "adaptive", "rho": "4", "mu": "1", "c": "2"})
    assert [mc.num_key(x) for x in (1.5, 16, 1, 0.2, 16.0, np.float64(0.715))] == \
        ["1.5", "16", "1", "0.2", "16", "0.715"]
    with pytest.raises(ValueError, match="not given back"):
        mc.num_key(1 / 3)
    assert mc.num_key(1 / 3, strict=False) == "0.333333"
    for kw in ({"part": "a:b"}, {"part": "p", "x": "a=b"}, {"part": "p", "x": ""}, {"part": "p", "x": "a b"}):
        with pytest.raises(ValueError):
            mc.job_id("e1", **kw)
    for bad in ("e1", "e1::x", "e1:p:noeq", "e1:p:a=1:a=2"):
        with pytest.raises(ValueError):
            mc.parse_job_id(bad)
    with pytest.raises(ValueError, match="kind"):
        mc.Job("e1:p", "big")
    with pytest.raises(ValueError, match="duplicate"):
        mc.check_jobs([mc.Job("e1:p:a=1"), mc.Job("e1:p:a=1")])
    with pytest.raises(ValueError, match="share the record file"):
        mc.check_jobs([mc.Job("e1:p:a=b"), mc.Job("e1:p=a=b")])
    # the record file follows q44_study.job_file_name, and ms3_lib.sh's ms3_job_name gives the same stem
    ids = ["e1:cell:sched=adaptive:rho=4:mu=1:c=2", "e2:game", "e6:a:lam=0.715:H=1.5", "e10:x:m=32:tag=A3-rot"]
    for i in ids:
        assert mc.job_file_name(i) == qs.job_file_name(i)
    out = subprocess.run(["bash", "-c", 'source "$1"; shift; for j in "$@"; do ms3_job_name "$j"; echo; done',
                          "x", str(LIB)] + ids, capture_output=True, text=True, timeout=30,
                         env={**os.environ, "MS3_PY": sys.executable})
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == [mc.job_file_name(i)[:-5] for i in ids]


def test_json_conventions(tmp_path):
    """JSON with allow_nan=False: numpy values become Python numbers, a non-finite value raises (written as null
    with a '*_note' key by put); dump_json leaves no .partial file."""
    obj = {"a": np.float64(1.5), "b": np.int64(3), "c": np.array([1, 2]), "d": (np.bool_(True), None), "e": Path("x")}
    p = mc.dump_json(obj, tmp_path / "s" / "x.json")
    assert json.loads(p.read_text()) == {"a": 1.5, "b": 3, "c": [1, 2], "d": [True, None], "e": "x"}
    assert not list(tmp_path.rglob("*.partial"))
    with pytest.raises(ValueError, match=r"\$\.r\[1\]"):
        mc.jsonable({"r": [1.0, float("inf")]})
    with pytest.raises(ValueError):
        mc.dump_json({"x": np.nan}, tmp_path / "y.json")
    assert not (tmp_path / "y.json").exists()
    # numeric keys follow §2.4 (format(float(x), "g")), so the grid's JSON paths exist (e.g. ratios.adaptive.4.1)
    keyed = {16.0: "a", 1.0: "b", np.float64(2.0): "c", 4: {0.2: "d", np.int64(1): "e"}, "x": 1}
    p = mc.dump_json(keyed, tmp_path / "k.json")
    assert json.loads(p.read_text()) == {"16": "a", "1": "b", "2": "c", "4": {"0.2": "d", "1": "e"}, "x": 1}
    for bad in ({None: 1}, {(1, 2): 1}, {True: 1}, {Path("a"): 1}):
        with pytest.raises(TypeError, match="key"):
            mc.jsonable(bad)
    with pytest.raises(ValueError, match="two keys"):
        mc.jsonable({1.0: "a", "1": "b"})
    with pytest.raises(ValueError, match=r"\$\.r"):
        mc.jsonable({"r": {1 / 3: 0}})                      # a key that its string does not give back
    d = {}
    mc.put(d, "ratio", float("nan"), "no runs")
    mc.put(d, "lb", None)
    mc.put(d, "n", 3)
    assert d == {"ratio": None, "ratio_note": "no runs", "lb": None, "lb_note": "missing", "n": 3}
    assert mc.md_table(["a", "b"], [[1.23456, None], ["x|y", 2]]) == \
        "| a | b |\n|---|---|\n| 1.235 | – |\n| x\\|y | 2 |\n"


def test_job_outputs_partial_renames(tmp_path):
    """Outputs are written as <name>.partial and renamed only by commit(); discard() removes them; a registered
    output that was never written makes commit() fail before any rename."""
    o = mc.JobOutputs()
    t1 = o.dump({"x": 1}, tmp_path / "a" / "one.json")
    t2 = o.write_text("hello\n", tmp_path / "two.txt")
    assert t1.name == "one.json.partial" and t2.name == "two.txt.partial"
    assert not (tmp_path / "a" / "one.json").exists() and mc.stale_partials(tmp_path) == sorted([t1, t2])
    assert o.commit() == [(tmp_path / "a" / "one.json").resolve(), (tmp_path / "two.txt").resolve()]
    assert json.loads((tmp_path / "a" / "one.json").read_text()) == {"x": 1} and not mc.stale_partials(tmp_path)
    o2 = mc.JobOutputs()
    o2.dump({}, tmp_path / "three.json")
    o2.partial(tmp_path / "never.json")
    with pytest.raises(FileNotFoundError):
        o2.commit()
    assert not (tmp_path / "three.json").exists()
    o2.discard()
    assert not mc.stale_partials(tmp_path)
    with pytest.raises(ValueError, match="twice"):
        o.partial(tmp_path / "two.txt")


# ---------------------------------------------------------------- records, resume, exit codes
def test_run_job_records_and_resume(tmp_path, monkeypatch):
    """A job's record: status ok, runs, errors of single runs (the job goes on; tracebacks not in the record), the
    slots it held, git revision, versions, wall time and peak RSS; outputs renamed from .partial at the end. A
    raising job is 'error' and leaves no output. With MS3_RESUME=1 an ok job is skipped (its function is not
    called), an 'error' job runs again; without it every job runs."""
    monkeypatch.setenv("MS3_SLOTS", "slot2,milp1")
    monkeypatch.delenv("MS3_RESUME", raising=False)
    out = tmp_path / "e9x"
    calls = []

    def fn(outputs):
        calls.append(1)
        errors = []
        outputs.dump({"v": 1}, out / "runs" / "r1.json")
        assert mc.try_run(errors, "BL0a", lambda: 1 / 0) is None
        assert mc.try_run(errors, "A2", lambda x: x + 1, 1) == 2
        return {"runs": 2, "errors": errors, "note": "small"}

    job = mc.Job(mc.job_id("e9x", "cell", rho=4), "milp", {"rho": 4}, est_s=5.0)
    rec = mc.run_job("e9x", job, fn, out)
    assert rec["status"] == "ok" and rec["runs"] == 2 and rec["n_errors"] == 1
    assert rec["errors"] == [{"tag": "BL0a", "error": "ZeroDivisionError: division by zero"}]
    assert rec["slots"] == ["slot2", "milp1"] and rec["kind"] == "milp" and rec["milp_limit_s"] == 300
    assert rec["result"] == {"note": "small"} and rec["outputs"] == ["runs/r1.json"]
    assert rec["peak_rss_kb"] > 0 and rec["wall_s"] >= 0 and rec["versions"]["sublet"] and "git_revision" in rec
    disk = json.loads(mc.record_path(out, job.id).read_text())
    assert disk["status"] == "ok" and mc.record_path(out, job.id).name == "e9x__cell__rho__4.json"
    assert (out / "runs" / "r1.json").is_file() and not mc.stale_partials(out)
    assert mc.is_done(out, job.id) is False                              # MS3_RESUME unset
    mc.run_job("e9x", job, fn, out)
    assert len(calls) == 2
    monkeypatch.setenv("MS3_RESUME", "1")
    assert mc.is_done(out, job.id) is True
    again = mc.run_job("e9x", job, fn, out)
    assert len(calls) == 2 and again["skipped"] is True and again["status"] == "ok"
    assert mc.run_job("e9x", job, fn, out, resume=False)["status"] == "ok" and len(calls) == 3

    def boom(outputs):
        outputs.dump({"half": True}, out / "runs" / "r2.json")
        raise RuntimeError("solver crashed")

    bad = mc.Job(mc.job_id("e9x", "cell", rho=8))
    rec = mc.run_job("e9x", bad, boom, out)
    assert rec["status"] == "error" and "RuntimeError: solver crashed" in rec["error"] and rec["traceback"]
    assert not (out / "runs" / "r2.json").exists() and not mc.stale_partials(out)
    assert mc.is_done(out, bad.id) is False
    assert mc.run_job("e9x", bad, lambda o: {"runs": 1}, out)["status"] == "ok"     # resume reruns an error


def test_killed_job_leaves_no_output(tmp_path):
    """A job process killed by PID (SIGKILL) during its run leaves its record at 'running', a .partial file and no
    final output; record_failure with exit 137 and no timeout then records oom_at_3G with the rule."""
    out = tmp_path / "e9k"
    code = textwrap.dedent(f"""
        import os, sys, time
        sys.path.insert(0, {str(SIM)!r})
        from sublet.experiments import ms3_common as mc
        def fn(outputs):
            outputs.dump({{"half": True}}, {str(out / "runs" / "r.json")!r})
            print("PID", os.getpid(), flush=True)
            time.sleep(60)
        mc.run_job("e9k", mc.Job("e9k:hang"), fn, {str(out)!r})
    """)
    proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True, cwd=str(SIM))
    try:
        line = proc.stdout.readline()
        assert line.startswith("PID"), line
        os.kill(proc.pid, signal.SIGKILL)
        assert proc.wait(timeout=30) == -signal.SIGKILL
    finally:
        if proc.poll() is None:
            proc.kill()
    rec = mc.read_record(out, "e9k:hang")
    assert rec["status"] == "running"
    assert not (out / "runs" / "r.json").exists() and (out / "runs" / "r.json.partial").is_file()
    new = mc.record_failure(out, "e9k:hang", 137, elapsed_s=1.5, peak_kb=81234, slots=["slot0"])
    assert new["status"] == "oom_at_3G" and "without timeout" in new["rule"] and new["exit_code"] == 137
    assert new["elapsed_s"] == 1.5 and new["peak_rss_kb_time"] == 81234 and new["slots"] == ["slot0"]
    assert mc.read_record(out, "e9k:hang")["status"] == "oom_at_3G"


def test_exit_code_rule():
    """§0 item 2 on synthetic records: a MILP job (LIMIT 300, timeout at 360 s) with exit 124 is wall_limit, with
    exit 137 wall_limit at elapsed >= 360 s and oom_at_3G below; a job without timeout with exit 137 is oom_at_3G;
    other codes are failed (error if the job recorded one); exit 0 changes nothing only with an ok record."""
    c = mc.classify_exit
    assert c(124, 361.2, 300)[0] == "wall_limit" and "exit 124" in c(124, 361.2, 300)[1]
    assert c(137, 390.0, 300)[0] == "wall_limit" and "SIGKILL" in c(137, 390.0, 300)[1]
    assert c(137, 360.0, 300)[0] == "wall_limit"
    assert c(137, 359.99, 300)[0] == "oom_at_3G" and "OOM" in c(137, 359.99, 300)[1]
    assert c(137, 12.0, 300)[0] == "oom_at_3G"
    assert c(137, None, 300)[0] == "oom_at_3G"
    assert c(137, 5000.0, None)[0] == "oom_at_3G" and "without timeout" in c(137, 5000.0, None)[1]
    assert c(124, 10.0, None) == ("failed", "exit 124")
    assert c(1, 3.0, None) == ("failed", "exit 1") and c(2, 3.0, 300) == ("failed", "exit 2")
    assert c(1, 3.0, None, "error")[0] == "error"
    assert c(0, 3.0, None, "ok")[0] is None
    assert c(0, 3.0, None, "running")[0] == "failed" and c(0, 3.0, None, None)[0] == "failed"
    assert mc.wall_timeout_s() == 360.0 and mc.WALL_GRACE_S == 60 and mc.KILL_AFTER_S == 30


def test_record_failure_updates(tmp_path):
    """record_failure keeps the job's own fields, adds exit code, elapsed time, peak RSS, rule and slots, keeps an
    ok record unchanged on exit 0, and records the status a killed record had before."""
    out = tmp_path / "e9r"
    mc.dump_json({"job": "e9r:m", "status": "running", "kind": "milp", "runs": 0}, mc.record_path(out, "e9r:m"))
    rec = mc.record_failure(out, "e9r:m", 137, elapsed_s=391.0, peak_kb=1.2e6, limit_s=300, slots=["slot1", "milp0"])
    assert rec["status"] == "wall_limit" and rec["kind"] == "milp" and rec["timeout_limit_s"] == 300.0
    assert rec["slots"] == ["slot1", "milp0"] and "status_before" not in rec
    mc.dump_json({"job": "e9r:ok", "status": "ok"}, mc.record_path(out, "e9r:ok"))
    assert mc.record_failure(out, "e9r:ok", 0) is None and mc.read_record(out, "e9r:ok") == {"job": "e9r:ok",
                                                                                               "status": "ok"}
    mc.dump_json({"job": "e9r:e", "status": "error", "error": "x"}, mc.record_path(out, "e9r:e"))
    assert mc.record_failure(out, "e9r:e", 1)["status"] == "error"
    assert mc.record_failure(out, "e9r:none", 3)["status"] == "failed"         # no record at all
    mc.dump_json({"job": "e9r:ok2", "status": "ok"}, mc.record_path(out, "e9r:ok2"))
    assert mc.record_failure(out, "e9r:ok2", 137)["status_before"] == "ok"
    assert set(mc.read_records(out)) == {"e9r:m", "e9r:ok", "e9r:e", "e9r:none", "e9r:ok2"}


def test_max_workers(tmp_path, monkeypatch):
    """N = min(MS3_WORKERS, 4) (default 4) with <root>/out/e11/summary.json, 0 without it; the command line
    prints it; the MILP limit is MS3_MILP_LIMIT (default 300)."""
    monkeypatch.delenv("MS3_WORKERS", raising=False)
    assert mc.max_workers(tmp_path) == 0
    (tmp_path / "out" / "e11").mkdir(parents=True)
    (tmp_path / "out" / "e11" / "summary.json").write_text("{}")
    assert mc.max_workers(tmp_path) == 4
    for v, n in (("2", 2), ("9", 4), ("0", 0), ("-3", 0), ("1", 1)):
        monkeypatch.setenv("MS3_WORKERS", v)
        assert mc.max_workers(tmp_path) == n
    monkeypatch.setenv("MS3_WORKERS", "x")
    with pytest.raises(ValueError):
        mc.max_workers(tmp_path)
    monkeypatch.setenv("MS3_WORKERS", "3")
    monkeypatch.setenv("MS3_ROOT", str(tmp_path))
    assert mc.ms3_root() == tmp_path.resolve() and mc.max_workers() == 3
    assert mc.slots_dir() == tmp_path.resolve() / "out" / ".ms3_slots"
    assert mc.out_dir("e1") == tmp_path.resolve() / "out" / "e1"
    out = subprocess.run([sys.executable, "-m", "sublet.experiments.ms3_common", "--max-workers", "--root",
                          str(tmp_path)], cwd=str(SIM), capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and out.stdout.strip() == "3", out.stderr
    monkeypatch.delenv("MS3_ROOT")
    assert mc.ms3_root() == SIM.resolve()
    assert mc.milp_limit_s() == 300
    monkeypatch.setenv("MS3_MILP_LIMIT", "30")
    assert mc.milp_limit_s() == 30 and mc.wall_timeout_s() == 90.0


# ---------------------------------------------------------------- check E11-0 (§2.4, §3.2 step 1, §3.3)
E11_FILES = {
    "manifest.json": {"meta": {"git_revision": mc.E11_REVISION}, "jobs": []},
    "summary.json": {"checks": {}},
    "jobs/Q0__x.json": {"job": "Q0:x", "status": "ok"},
    "runs/Q0/I1/1min/L-tr/A6_c3_l3_p0.json": {"meta": {"git_revision": mc.E11_REVISION}, "components": {}},
    "runs/Q0/I1/1min/L-tr/cell_c3.json": {"git_revision": mc.E11_REVISION, "runs": 2},
    "runs/Q4/I2-H5/1min/L-eg/BL2_c6_l6_p2_sum.json": {"meta": {"name": "example_1day"}, "components": {}},
}


def _e11_tree(top: Path) -> Path:
    for rel, obj in E11_FILES.items():
        p = top / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj) + "\n")
    (top / "logs").mkdir()
    (top / "logs" / "Q0__x.log").write_bytes(b"line one\nline two\n")
    (top / "run_q44_study.log").write_text("[run_q44_study] start\n[run_q44_study] done 2026-10-19\n")
    return top


@pytest.fixture
def e11_pair(tmp_path):
    """A temporary root whose out/e11 is an exact copy (shutil.copytree) of a fake clone folder."""
    clone = _e11_tree(tmp_path / "clone" / "code" / "sim" / "out" / "e11")
    root = tmp_path / "root"
    shutil.copytree(clone, root / "out" / "e11")
    return root, clone


def test_check_e11_exact_copy_passes(e11_pair):
    """An exact copy passes; the record lands in <root>/out/ms3_e11_0.json with the counts, the manifest's
    revision, the BL2 sum without a revision and the checking code's revision; the command line exits 0."""
    root, clone = e11_pair
    res = mc.check_e11(clone, root)
    assert res["pass"] is True and all(res["checks"].values())
    assert (res["n_files_copy"], res["n_files_clone"], res["n_files_compared"]) == (8, 8, 8)
    assert res["manifest_git_revision"] == mc.E11_REVISION and res["n_run_files"] == 3
    assert res["run_revisions_found"] == {mc.E11_REVISION: 2}
    assert (res["n_runs_no_revision"], res["n_runs_no_revision_sum"], res["n_runs_no_revision_other"]) == (1, 1, 0)
    assert res["e11_log_done"] is True and res["clone"] == str(clone.resolve()) and "git_revision" in res["checked_by"]
    disk = json.loads((root / "out" / "ms3_e11_0.json").read_text())
    assert disk["pass"] is True and disk["n_files_copy"] == 8 and disk["time"]
    out = subprocess.run([sys.executable, "-m", "sublet.experiments.ms3_common", "--check-e11", str(clone), "--root",
                          str(root)], cwd=str(SIM), capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and "check E11-0 pass" in out.stdout, out.stdout + out.stderr


def test_check_e11_changed_byte_fails(e11_pair):
    """One changed byte in a file of the copy (same size) fails the sha256 comparison with the path named; the
    command line writes the record and exits 1."""
    root, clone = e11_pair
    p = root / "out" / "e11" / "logs" / "Q0__x.log"
    data = bytearray(p.read_bytes())
    data[5] ^= 0x01
    p.write_bytes(bytes(data))
    res = mc.check_e11(clone, root)
    assert res["pass"] is False and res["checks"]["same_sha256"] is False and res["checks"]["same_file_list"]
    assert res["sha256_mismatch"] == ["logs/Q0__x.log"] and res["n_sha256_mismatch"] == 1
    (root / "out" / "ms3_e11_0.json").unlink()
    out = subprocess.run([sys.executable, "-m", "sublet.experiments.ms3_common", "--check-e11", str(clone), "--root",
                          str(root)], cwd=str(SIM), capture_output=True, text=True, timeout=60)
    assert out.returncode == 1 and "FAIL" in out.stdout and "same_sha256" in out.stdout, out.stdout + out.stderr
    assert json.loads((root / "out" / "ms3_e11_0.json").read_text())["sha256_mismatch"] == ["logs/Q0__x.log"]


@pytest.mark.parametrize("side", ["copy", "clone"])
def test_check_e11_missing_file_fails(e11_pair, side):
    """A file missing on either side fails with the path named under the other side's list."""
    root, clone = e11_pair
    rel = "runs/Q4/I2-H5/1min/L-eg/BL2_c6_l6_p2_sum.json"
    ((root / "out" / "e11") if side == "copy" else clone).joinpath(rel).unlink()
    res = mc.check_e11(clone, root)
    assert res["pass"] is False and res["checks"]["same_file_list"] is False
    key, other = ("only_in_clone", "only_in_copy") if side == "copy" else ("only_in_copy", "only_in_clone")
    assert res[key] == [rel] and res[f"n_{key}"] == 1 and res[other] == []


def test_check_e11_other_revision_fails(e11_pair):
    """A run file (in both folders, so the sha256 agree) whose recorded revision differs fails with the path named,
    for meta.git_revision and for the top-level revision of a cell file; so does another manifest revision, a run
    file without a revision that is not a BL2 sum, and a run file that is not JSON; a missing folder raises."""
    root, clone = e11_pair
    copy = root / "out" / "e11"

    def both(rel, text):
        for top in (copy, clone):
            (top / rel).write_text(text)

    run, cell = "runs/Q0/I1/1min/L-tr/A6_c3_l3_p0.json", "runs/Q0/I1/1min/L-tr/cell_c3.json"
    both(run, json.dumps({"meta": {"git_revision": "472b353" + "0" * 33}}))
    both(cell, json.dumps({"git_revision": "0" * 40}))
    res = mc.check_e11(clone, root)
    assert res["pass"] is False and res["checks"]["same_sha256"] and res["checks"]["run_revisions"] is False
    assert res["run_revision_differs"] == sorted([run, cell]) and res["n_run_revision_differs"] == 2
    both(run, json.dumps({"meta": {"git_revision": mc.E11_REVISION}}))
    both(cell, json.dumps({"git_revision": mc.E11_REVISION}))
    assert mc.check_e11(clone, root)["pass"] is True
    both("manifest.json", json.dumps({"meta": {"git_revision": "0" * 40}}))
    res = mc.check_e11(clone, root)
    assert res["pass"] is False and res["checks"]["manifest_revision"] is False and res["manifest_git_revision"]
    both("manifest.json", json.dumps(E11_FILES["manifest.json"]))
    both(run, json.dumps({"meta": {"name": "x"}}))
    res = mc.check_e11(clone, root)
    assert res["pass"] is False and res["runs_no_revision_other"] == [run]
    both(run, "{not json")
    res = mc.check_e11(clone, root)
    assert res["pass"] is False and res["runs_unreadable"] == [run]
    with pytest.raises(FileNotFoundError):
        mc.check_e11(clone.parent / "nope", root)
    with pytest.raises(ValueError, match="copy itself"):
        mc.check_e11(copy, root)


# ---------------------------------------------------------------- the copy check of an experiment (§1.2)
COMMIT = "f10237bb39ab101b9831afcee79121d0fa4e1979"


def _exp_files(exp: str, commit: str = COMMIT) -> dict:
    """One experiment folder (or part) in the drivers' shape: records with a top-level git_revision (job records,
    cell files, lb records, the summary and manifest records), files with meta.git_revision (manifest, summary, run
    files), a record written by --record-failure for a job without a record of its own (no revision, its rule),
    non-JSON logs and the run log."""
    return {
        "manifest.json": {"meta": {"exp": exp, "git_revision": commit}, "jobs": []},
        "summary.json": {"meta": {"exp": exp, "git_revision": commit}, "checks": {}},
        f"jobs/{exp}__cell__c__1.json": {"job": f"{exp}:cell:c=1", "status": "ok", "git_revision": commit},
        f"jobs/{exp}__milp__c__1.json": {"job": f"{exp}:milp:c=1", "status": "wall_limit", "git_revision": commit},
        f"jobs/{exp}__milp__c__2.json": {"job": f"{exp}:milp:c=2", "status": "failed", "exit_code": 3,
                                         "rule": "exit 3"},
        f"jobs/{exp}__summary.json": {"job": f"{exp}:summary", "status": "ok", "git_revision": commit},
        f"jobs/{exp}__manifest.json": {"job": f"{exp}:manifest", "status": "ok", "git_revision": commit},
        "runs/c=1/cell.json": {"git_revision": commit, "runs": 2},
        "runs/c=1/A2_p0.json": {"meta": {"git_revision": commit}, "components": {}},
        "lb/c=1/lp_0123456789abcdef.json": {"job": f"{exp}:cell:c=1", "git_revision": commit, "status": 0},
    }


def _exp_tree(top: Path, exp: str, done: bool = True) -> Path:
    for rel, obj in _exp_files(exp).items():
        p = top / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=1) + "\n")
    (top / "logs").mkdir(exist_ok=True)
    (top / "logs" / f"{exp}__cell__c__1.log").write_bytes(b"run one\nrun two\n")
    (top / "logs" / f"{exp}__cell__c__1.time").write_text("123456 7.5\n")
    (top / "tables.md").write_text("# tables\n")
    lines = [f"[run_{exp}] start 2026-10-20T07:35:00+08:00 on host: 4 slot(s) now, out code/sim/out/{exp}",
             f"[time] {exp}:cell:c=1 peak RSS 123456 KB, 7.5 s, exit 0", f"[run_{exp}] pool jobs done 2026-10-20"]
    if done:
        lines.append(f"[run_{exp}] done 2026-10-20T08:00:00+08:00")
    (top / f"run_{exp}.log").write_text("\n".join(lines) + "\n")
    return top


def _clone_repo(path: Path, head: str = COMMIT + "\n") -> Path:
    (path / ".git").mkdir(parents=True)
    (path / ".git" / "HEAD").write_text(head)
    return path


@pytest.fixture
def copy_pair(tmp_path):
    """(root, clone, exp): a fake clone (repository root with .git/HEAD at COMMIT) with code/sim/out/e1, and a
    temporary MS3 root whose out/e1 is an exact copy of it."""
    clone = _clone_repo(tmp_path / "clone")
    src = _exp_tree(clone / "code" / "sim" / "out" / "e1", "e1")
    root = tmp_path / "root"
    shutil.copytree(src, root / "out" / "e1")
    return root, clone, "e1"


def _copy_cli(*args):
    return subprocess.run([sys.executable, "-m", "sublet.experiments.ms3_common", *map(str, args)], cwd=str(SIM),
                          capture_output=True, text=True, timeout=60)


def test_check_copy_exact_copy_passes(copy_pair):
    """An exact copy passes: equal file lists and sha256, every recorded revision the clone's commit, the files without
    one counted by kind, the job records counted by status (none 'running'), the run log's last line ms3_finish's;
    the record lands in <root>/out/ms3_copy_e1.json; the command line prints one line and exits 0."""
    root, clone, exp = copy_pair
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is True and all(res["checks"].values()), res["checks"]
    assert res["clone_commit"] == COMMIT and res["parts"] == [] and res["n_files_copy"] == res["n_files_clone"] == 14
    assert (res["n_json"], res["revisions_found"], res["n_revision_differs"]) == (10, {COMMIT: 9}, 0)
    assert res["no_revision_by_kind"] == {"jobs": 1} and res["n_no_revision"] == 1
    assert res["n_no_revision_unexpected"] == 0 and res["n_symlinks"] == 0
    assert res["records_by_status"] == {"failed": 1, "ok": 3, "wall_limit": 1} and res["n_running"] == 0
    assert res["summaries"]["e1"] == {"file": "summary.json", "exists": True, "object": True, "summary_record": "ok",
                                      "manifest_record": "ok", "ok": True}
    assert res["tree_sha256"] == mc.tree_digest(root / "out" / exp) == mc.tree_digest(clone / "code/sim/out/e1")
    assert res["manifest_git_revision"] == {"e1": COMMIT} and res["run_logs"]["e1"]["done"] is True
    assert res["run_logs"]["e1"]["file"] == "run_e1.log" and "git_revision" in res["checked_by"] and res["time"]
    disk = json.loads((root / "out" / "ms3_copy_e1.json").read_text())
    assert disk["pass"] is True and disk["exp"] == "e1" and disk["clone"] == str(clone.resolve())
    (root / "out" / "ms3_copy_e1.json").unlink()
    out = _copy_cli("--check-copy", exp, clone, "--root", root)
    assert out.returncode == 0 and len(out.stdout.strip().splitlines()) == 1, out.stdout + out.stderr
    assert "copy check e1 pass" in out.stdout and COMMIT in out.stdout
    assert json.loads((root / "out" / "ms3_copy_e1.json").read_text())["pass"] is True
    rep = root / "elsewhere.json"
    assert mc.check_copy(exp, clone, root, rep)["pass"] and json.loads(rep.read_text())["pass"]


def test_check_copy_sha256_mismatch_fails(copy_pair):
    """One changed byte (same size) fails same_sha256 with the path named; the command line exits 1 with FAIL."""
    root, clone, exp = copy_pair
    p = root / "out" / exp / "logs" / "e1__cell__c__1.log"
    data = bytearray(p.read_bytes())
    data[2] ^= 0x01
    p.write_bytes(bytes(data))
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is False and res["checks"]["same_sha256"] is False and res["checks"]["same_file_list"]
    assert res["sha256_mismatch"] == ["logs/e1__cell__c__1.log"] and res["n_sha256_mismatch"] == 1
    out = _copy_cli("--check-copy", exp, clone, "--root", root)
    assert out.returncode == 1 and "FAIL" in out.stdout and "same_sha256" in out.stdout, out.stdout + out.stderr


@pytest.mark.parametrize("side", ["copy", "clone"])
def test_check_copy_file_on_one_side_fails(copy_pair, side):
    """A run file present on one side only (runs/ is compared too) fails same_file_list with the path named."""
    root, clone, exp = copy_pair
    rel = "runs/c=1/A2_p0.json"
    top = (root / "out" / exp) if side == "copy" else (clone / "code" / "sim" / "out" / exp)
    top.joinpath(rel).unlink()
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is False and res["checks"]["same_file_list"] is False
    key, other = ("only_in_clone", "only_in_copy") if side == "copy" else ("only_in_copy", "only_in_clone")
    assert res[key] == [rel] and res[f"n_{key}"] == 1 and res[other] == []


def test_check_copy_wrong_revision_fails(copy_pair):
    """A JSON file (in both folders, so the sha256 agree) whose recorded revision is not the clone's commit fails
    'revisions' with the path named (top-level git_revision and meta.git_revision); another manifest revision fails
    'manifest_revision'; a JSON file that does not parse fails 'json_readable'. The commit is also read through a
    ref (loose and packed); a clone without .git or a missing folder raises, and the command line exits 2."""
    root, clone, exp = copy_pair
    copy = root / "out" / exp

    def both(rel, text):
        for top in (copy, clone / "code" / "sim" / "out" / exp):
            (top / rel).write_text(text)

    rec, run = "jobs/e1__cell__c__1.json", "runs/c=1/A2_p0.json"
    both(rec, json.dumps({"job": "e1:cell:c=1", "status": "ok", "git_revision": "0" * 40}))
    both(run, json.dumps({"meta": {"git_revision": "1" * 40}}))
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is False and res["checks"]["same_sha256"] and res["checks"]["revisions"] is False
    assert res["revision_differs"] == sorted([rec, run]) and res["n_revision_differs"] == 2
    both(rec, json.dumps({"job": "e1:cell:c=1", "status": "ok", "git_revision": COMMIT}))
    both(run, json.dumps({"meta": {"git_revision": COMMIT}}))
    assert mc.check_copy(exp, clone, root)["pass"] is True
    both("manifest.json", json.dumps({"meta": {"git_revision": "2" * 40}}))
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is False and res["checks"]["manifest_revision"] is False and res["checks"]["revisions"] is False
    assert res["manifest_git_revision"] == {"e1": "2" * 40}
    both("manifest.json", json.dumps(_exp_files(exp)["manifest.json"]))
    both(run, "{not json")
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is False and res["checks"]["json_readable"] is False and res["json_unreadable"] == [run]
    both(run, json.dumps({"meta": {"git_revision": COMMIT}}))
    # HEAD as a ref: the loose ref file, then packed-refs (another commit there fails 'revisions')
    (clone / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    with pytest.raises(ValueError, match="resolves to no commit"):
        mc.check_copy(exp, clone, root)
    (clone / ".git" / "refs" / "heads").mkdir(parents=True)
    (clone / ".git" / "refs" / "heads" / "main").write_text(COMMIT + "\n")
    assert mc.clone_commit(clone) == COMMIT and mc.check_copy(exp, clone, root)["pass"] is True
    (clone / ".git" / "refs" / "heads" / "main").unlink()
    (clone / ".git" / "packed-refs").write_text(f"# pack-refs with: peeled\n{'3' * 40} refs/heads/main\n")
    assert mc.clone_commit(clone) == "3" * 40 and mc.check_copy(exp, clone, root)["pass"] is False
    shutil.rmtree(clone / ".git")
    with pytest.raises(FileNotFoundError):
        mc.check_copy(exp, clone, root)
    assert _copy_cli("--check-copy", exp, clone, "--root", root).returncode == 2
    _clone_repo(clone)
    with pytest.raises(FileNotFoundError):
        mc.check_copy("e10", clone, root)
    with pytest.raises(ValueError, match="own check"):
        mc.check_copy("e11", clone, root)
    with pytest.raises(ValueError, match="copy itself"):
        mc.check_copy(exp, clone, clone / "code" / "sim")          # the clone's own out/e1 as the copy


def test_check_copy_running_record_fails(copy_pair):
    """A job record still 'running' (killed before any rule applied, §2.4) fails the check with its path; a record
    with a status outside §2.4's fails record_statuses_known."""
    root, clone, exp = copy_pair
    rec = {"job": "e1:cell:c=2", "status": "running", "git_revision": COMMIT}
    for top in (root / "out" / exp, clone / "code" / "sim" / "out" / exp):
        (top / "jobs" / "e1__cell__c__2.json").write_text(json.dumps(rec))
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is False and res["checks"]["no_running_records"] is False and res["checks"]["same_sha256"]
    assert res["running_records"] == ["jobs/e1__cell__c__2.json"] and res["records_by_status"]["running"] == 1
    rec["status"] = "done"
    for top in (root / "out" / exp, clone / "code" / "sim" / "out" / exp):
        (top / "jobs" / "e1__cell__c__2.json").write_text(json.dumps(rec))
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is False and res["checks"]["no_running_records"] and not res["checks"]["record_statuses_known"]
    assert res["unknown_status_records"] == ["jobs/e1__cell__c__2.json"]


def test_check_copy_missing_done_line_fails(copy_pair):
    """A run log whose last line is not ms3_finish's '[run_e1] done ...' (the script was stopped, or another
    script's line) fails run_log_done; so does a missing run log."""
    root, clone, exp = copy_pair
    for top in (root / "out" / exp, clone / "code" / "sim" / "out" / exp):
        _exp_tree(top, exp, done=False)
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is False and res["checks"]["run_log_done"] is False and res["checks"]["same_sha256"]
    assert res["run_logs"]["e1"]["last_line"] == "[run_e1] pool jobs done 2026-10-20"
    for top in (root / "out" / exp, clone / "code" / "sim" / "out" / exp):
        with open(top / "run_e1.log", "a") as f:
            f.write("[run_e10] done 2026-10-20T08:00:00+08:00\n")
    assert mc.check_copy(exp, clone, root)["checks"]["run_log_done"] is False
    for top in (root / "out" / exp, clone / "code" / "sim" / "out" / exp):
        (top / "run_e1.log").unlink()
    res = mc.check_copy(exp, clone, root)
    assert res["run_logs"]["e1"]["exists"] is False and res["checks"]["run_log_done"] is False


def test_check_copy_e6_parts(tmp_path):
    """e6: the folder out/e6 with its parts a and b, each with its own manifest, job records and run log
    run_e6.log; both parts done passes, with the records counted per part and the files without a revision per
    part and kind; a part whose log lacks the done line fails, naming that part."""
    clone = _clone_repo(tmp_path / "clone")
    for part in ("a", "b"):
        _exp_tree(clone / "code" / "sim" / "out" / "e6" / part, "e6")
    root = tmp_path / "root"
    shutil.copytree(clone / "code" / "sim" / "out" / "e6", root / "out" / "e6")
    res = mc.check_copy("e6", clone, root)
    assert res["pass"] is True and res["parts"] == ["a", "b"] and res["n_files_copy"] == 28
    assert set(res["run_logs"]) == {"a", "b"} and res["run_logs"]["b"]["file"] == "b/run_e6.log"
    assert res["manifest_git_revision"] == {"a": COMMIT, "b": COMMIT}
    assert res["records_by_part"]["a"] == res["records_by_part"]["b"] == {"failed": 1, "ok": 3, "wall_limit": 1}
    assert res["records_by_status"] == {"failed": 2, "ok": 6, "wall_limit": 2}
    assert set(res["summaries"]) == {"a", "b"} and res["summaries"]["b"]["file"] == "b/summary.json"
    assert res["no_revision_by_kind"] == {"a/jobs": 1, "b/jobs": 1}
    for top in (root / "out" / "e6" / "b", clone / "code" / "sim" / "out" / "e6" / "b"):
        _exp_tree(top, "e6", done=False)
    res = mc.check_copy("e6", clone, root)
    assert res["pass"] is False and res["checks"]["run_log_done"] is False
    assert res["run_logs"]["a"]["done"] is True and res["run_logs"]["b"]["done"] is False
    shutil.rmtree(root / "out" / "e6" / "b")
    res = mc.check_copy("e6", clone, root)
    assert res["pass"] is False and not res["checks"]["same_file_list"] and res["run_logs"]["b"]["exists"] is False


def _both(root: Path, clone: Path, exp: str, rel: str, data) -> None:
    """Write `data` (bytes, text, or a JSON object) at `rel` in the copy and in the clone (equal sha256)."""
    for top in (root / "out" / exp, clone / "code" / "sim" / "out" / exp):
        p = top / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            p.write_bytes(data)
        else:
            p.write_text(data if isinstance(data, str) else json.dumps(data))


def test_check_copy_summary_missing_or_failed_fails(copy_pair):
    """summary_ok: the summary must exist and parse to an object, and the records '<exp>:summary' and '<exp>:manifest'
    must say 'ok' (ms3_finish writes the done line whatever happened, so a failed summary job would pass otherwise);
    the command line exits 1 with the record written."""
    root, clone, exp = copy_pair
    for top in (root / "out" / exp, clone / "code" / "sim" / "out" / exp):
        (top / "summary.json").unlink()
    _both(root, clone, exp, "jobs/e1__summary.json", {"job": "e1:summary", "status": "failed", "git_revision": COMMIT,
                                                      "exit_code": 1, "rule": "exit 1"})
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is False and [k for k, v in res["checks"].items() if not v] == ["summary_ok"]
    assert res["summaries"]["e1"] == {"file": "summary.json", "exists": False, "object": False,
                                      "summary_record": "failed", "manifest_record": "ok", "ok": False}
    out = _copy_cli("--check-copy", exp, clone, "--root", root)
    assert out.returncode == 1 and "summary_ok" in out.stdout and (root / "out" / "ms3_copy_e1.json").is_file()
    _both(root, clone, exp, "summary.json", _exp_files(exp)["summary.json"])
    assert mc.check_copy(exp, clone, root)["checks"]["summary_ok"] is False          # the record still says failed
    _both(root, clone, exp, "jobs/e1__summary.json", _exp_files(exp)["jobs/e1__summary.json"])
    assert mc.check_copy(exp, clone, root)["pass"] is True
    for top in (root / "out" / exp, clone / "code" / "sim" / "out" / exp):
        (top / "jobs" / "e1__manifest.json").unlink()
    res = mc.check_copy(exp, clone, root)
    assert res["checks"]["summary_ok"] is False and res["summaries"]["e1"]["manifest_record"] is None
    _both(root, clone, exp, "jobs/e1__manifest.json", _exp_files(exp)["jobs/e1__manifest.json"])
    _both(root, clone, exp, "summary.json", [1, 2])                                 # valid JSON, not an object
    res = mc.check_copy(exp, clone, root)
    assert res["checks"]["summary_ok"] is False and res["summaries"]["e1"]["object"] is False


def test_check_copy_revisions_recorded(tmp_path, copy_pair):
    """revisions_recorded: every JSON file records a revision, except a failure record without git_revision (with
    its rule) and E2's MILP files (runs/joint/, runs/ep_milp/, COPY_NO_REVISION); a missing or null revision fails
    with the path named, so do a failure record without its rule and a non-string revision."""
    root, clone, exp = copy_pair
    _both(root, clone, exp, "summary.json", {"meta": {"exp": exp}, "checks": {}})
    _both(root, clone, exp, "runs/c=1/cell.json", {"git_revision": None, "runs": 2})
    _both(root, clone, exp, "jobs/e1__milp__c__2.json", {"job": "e1:milp:c=2", "status": "failed", "exit_code": 3})
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is False and [k for k, v in res["checks"].items() if not v] == ["revisions_recorded"]
    assert res["no_revision_unexpected"] == ["jobs/e1__milp__c__2.json", "runs/c=1/cell.json", "summary.json"]
    assert res["no_revision_by_kind"] == {"jobs": 1, "runs": 1, "summary.json": 1}
    for rel in ("summary.json", "runs/c=1/cell.json", "jobs/e1__milp__c__2.json"):
        _both(root, clone, exp, rel, _exp_files(exp)[rel])
    _both(root, clone, exp, "runs/c=1/A2_p0.json", {"meta": {"git_revision": ["x"]}})   # not a string: crashed before
    res = mc.check_copy(exp, clone, root)
    assert res["checks"]["revisions"] is False and res["revision_differs"] == ["runs/c=1/A2_p0.json"]
    assert res["checks"]["revisions_recorded"] and '<["x"]>' in res["revisions_found"]
    # E2: its joint and E2-5 MILP files record no revision (their job records do)
    clone2 = _clone_repo(tmp_path / "clone2")
    src = _exp_tree(clone2 / "code" / "sim" / "out" / "e2", "e2")
    for rel in ("runs/joint/e2__joint__x.json", "runs/joint/e2__joint__x.lp.json",
                "runs/ep_milp/e2__ep_milp__i__0.json"):
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(json.dumps({"lender": "a2.c05", "stage": "test"}))
    root2 = tmp_path / "root2"
    shutil.copytree(src, root2 / "out" / "e2")
    res = mc.check_copy("e2", clone2, root2)
    assert res["pass"] is True and res["no_revision_by_kind"] == {"jobs": 1, "runs": 3}
    assert res["no_revision_allowed_under"] == ["runs/joint/", "runs/ep_milp/"]
    _both(root2, clone2, "e2", "runs/game/e2__game.json", {"rows": []})
    res = mc.check_copy("e2", clone2, root2)
    assert res["checks"]["revisions_recorded"] is False and res["no_revision_unexpected"] == ["runs/game/e2__game.json"]


def test_check_copy_malformed_files_fail_without_a_crash(copy_pair):
    """Malformed files give a record and a fail, never a traceback: binary job records and manifests fail
    json_readable (and record_statuses_known, manifest_revision), a folder named jobs/<x>.json is not a record, and
    the command line exits 1 with the record written."""
    root, clone, exp = copy_pair
    _both(root, clone, exp, "jobs/sub.json/inner.txt", "a folder named like a record\n")
    assert mc.check_copy(exp, clone, root)["pass"] is True
    _both(root, clone, exp, "jobs/e1__cell__c__9.json", b"\xff\xfe\x00binary")
    res = mc.check_copy(exp, clone, root)
    assert res["checks"]["json_readable"] is False and res["checks"]["record_statuses_known"] is False
    assert res["json_unreadable"] == ["jobs/e1__cell__c__9.json"] and res["records_by_status"]["unreadable"] == 1
    _both(root, clone, exp, "manifest.json", b"\x80\x81")
    res = mc.check_copy(exp, clone, root)
    assert res["checks"]["manifest_revision"] is False and res["manifest_git_revision"] == {"e1": None}
    (root / "out" / "ms3_copy_e1.json").unlink()
    out = _copy_cli("--check-copy", exp, clone, "--root", root)
    assert out.returncode == 1 and "Traceback" not in out.stderr, out.stderr
    assert json.loads((root / "out" / "ms3_copy_e1.json").read_text())["pass"] is False


def test_check_copy_symlink_and_tree_digest(copy_pair):
    """A symbolic link in either folder fails no_symlinks (a link is compared by its target text only); the record's
    tree_sha256 is tree_digest of the copy and changes with any file of it."""
    root, clone, exp = copy_pair
    d0 = mc.check_copy(exp, clone, root)["tree_sha256"]
    for top in (root / "out" / exp, clone / "code" / "sim" / "out" / exp):
        os.symlink("tables.md", top / "link.md")
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is False and [k for k, v in res["checks"].items() if not v] == ["no_symlinks"]
    assert res["symlinks"] == ["clone:link.md", "copy:link.md"] and res["tree_sha256"] != d0
    for top in (root / "out" / exp, clone / "code" / "sim" / "out" / exp):
        (top / "link.md").unlink()
    assert mc.check_copy(exp, clone, root)["tree_sha256"] == d0
    (root / "out" / exp / "tables.md").write_text("# tables, changed\n")
    assert mc.tree_digest(root / "out" / exp) != d0


def test_tree_digest_of_the_versioned_files(copy_pair):
    """tree_sha256_versioned leaves out the run files runs/ (not versioned, M45), at the experiment's folder or a
    part's (e6): a checkout without them recomputes it, and a change of a versioned file changes it."""
    root, clone, exp = copy_pair
    top = root / "out" / exp
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is True and res["tree_sha256_versioned"] == mc.tree_digest(top, exp)
    assert any(p.startswith("runs/") for p in mc._tree(top)) and res["tree_sha256_versioned"] != res["tree_sha256"]
    shutil.rmtree(top / "runs")
    assert mc.tree_digest(top, exp) == res["tree_sha256_versioned"] and mc.tree_digest(top) != res["tree_sha256"]
    (top / "tables.md").write_text("# tables, changed\n")
    assert mc.tree_digest(top, exp) != res["tree_sha256_versioned"]
    assert mc._unversioned("e6", "a/runs/x.json") and not mc._unversioned("e6", "a/jobs/x.json")
    assert mc._unversioned("e1", "runs/c=1/x.json") and not mc._unversioned("e1", "jobs/runs.json")
    assert not mc._unversioned("e1", "a/runs/x.json")


def test_driver_command_line(tmp_path, capsys, monkeypatch):
    """main(): --list prints '<kind> <id>'; --job runs one job (exit 0 iff ok, 2 for an unknown id); --estimate
    prints the jobs and the totals (list scheduling: pool on N slots, alone serially, MILP on 2 slots); --summary
    runs the summary under the record '<exp>:summary'; --manifest writes the job list with the statuses."""
    monkeypatch.delenv("MS3_RESUME", raising=False)
    jobs = [mc.Job("e9c:p:i=1", "pool", {"i": 1}, 10.0), mc.Job("e9c:p:i=2", "pool", {"i": 2}, 10.0),
            mc.Job("e9c:a", "alone", {}, 30.0), mc.Job("e9c:m:i=1", "milp", {}, 100.0),
            mc.Job("e9c:m:i=2", "milp", {}, 100.0), mc.Job("e9c:m:i=3", "milp", {}, 100.0),
            mc.Job("e9c:x", "pool", {}, None)]
    ran = []

    def run(job, outputs, out):
        ran.append(job.id)
        if job.id == "e9c:x":
            raise RuntimeError("bad job")
        outputs.dump({"id": job.id}, out / "runs" / f"{mc.job_file_name(job.id)}")
        return {"runs": 1}

    def summary(out):
        mc.dump_json({"jobs": sorted(mc.read_records(out))}, out / "summary.json")

    def main(*args):
        return mc.main("e9c", jobs=lambda: jobs, run=run, summary=summary, script=__file__, argv=list(args))

    out = tmp_path / "e9c"
    assert main("--list") == 0
    assert capsys.readouterr().out.splitlines() == [f"{j.kind} {j.id}" for j in jobs]
    assert main("--estimate", "--workers", "4") == 0
    txt = capsys.readouterr().out
    assert "pool  e9c:p:i=1  est 10 s" in txt and "e9c:x  est ? s" in txt and "(1 without an estimate)" in txt
    e = mc.estimate(jobs, 4)
    assert (e["pool_wall_s"], e["alone_s"], e["milp_wall_s"], e["single_worker_s"]) == (10.0, 30.0, 200.0, 350.0)
    assert mc.estimate(jobs, 1)["pool_wall_s"] == 20.0 and mc.estimate(jobs, 1)["milp_wall_s"] == 300.0
    assert main("--job", "e9c:p:i=1", "--out", str(out)) == 0
    assert main("--job", "e9c:x", "--out", str(out)) == 1
    assert main("--job", "e9c:nope", "--out", str(out)) == 2
    assert ran == ["e9c:p:i=1", "e9c:x"]
    assert main("--summary", "--out", str(out)) == 0
    assert json.loads((out / "summary.json").read_text())["jobs"] == ["e9c:p:i=1", "e9c:summary", "e9c:x"]
    assert mc.read_record(out, "e9c:summary")["status"] == "ok"
    monkeypatch.setenv("MS3_RESUME", "1")
    assert main("--summary", "--out", str(out)) == 0 and not mc.read_record(out, "e9c:summary").get("skipped")
    assert main("--job", "e9c:p:i=1", "--out", str(out)) == 0 and ran == ["e9c:p:i=1", "e9c:x"]   # skipped
    assert main("--manifest", "--out", str(out)) == 0
    assert mc.read_record(out, "e9c:manifest")["status"] == "ok"            # like the summary: a record, never skipped
    m = json.loads((out / "manifest.json").read_text())
    st = {r["id"]: r["status"] for r in m["jobs"]}
    assert st["e9c:p:i=1"] == "ok" and st["e9c:x"] == "error" and st["e9c:a"] is None
    assert m["meta"]["exp"] == "e9c" and m["meta"]["script_sha256"] and m["jobs"][0]["params"] == {"i": 1}
    assert "e9c:manifest" not in st and "e9c:summary" not in st
    with pytest.raises(ValueError, match="records of --summary and --manifest"):
        mc.main("e9c", jobs=lambda: [mc.Job("e9c:manifest")], run=run, argv=["--list"])
    capsys.readouterr()


# ---------------------------------------------------------------- the slot semaphore of ms3_lib.sh (§2.4, M44)
FAKE_DRIVER = '''\
"""Fake MS3 driver for tests/test_ms3_common.py: jobs from FAKE_JOBS ([[kind, id, action], ...]); a job writes
'<id> <kind> <t0> <t1> <slots>' to FAKE_EVENTS. Actions: a number of seconds to sleep, 'hang' (write the PID to
FAKE_PIDFILE, sleep 120 s), 'exit124', 'kill9' (SIGKILL to itself), 'raise'."""
import json, os, signal, sys, time
from pathlib import Path
from sublet.experiments import ms3_common as mc

EXP = os.environ["FAKE_EXP"]


def _where():
    """Append '<option> <cgroup> <memory.max>' to FAKE_CGROUP_LOG (if set): the cap the process runs under."""
    f = os.environ.get("FAKE_CGROUP_LOG")
    if not f:
        return
    cg = Path("/proc/self/cgroup").read_text().strip().splitlines()[-1].split(":", 2)[2]
    mm = Path("/sys/fs/cgroup" + cg) / "memory.max"
    cap = mm.read_text().strip() if mm.is_file() else "?"
    with open(f, "a") as fh:
        fh.write(f"{sys.argv[1] if len(sys.argv) > 1 else '?'} {cg} {cap}\\n")


def jobs():
    _where()
    return [mc.Job(i, k, {"action": a}, a if isinstance(a, (int, float)) else None)
            for k, i, a in json.loads(os.environ["FAKE_JOBS"])]


def run(job, outputs, out):
    a = job.params["action"]
    t0 = time.time()
    if a == "hang":
        Path(os.environ["FAKE_PIDFILE"]).write_text(str(os.getpid()))
        time.sleep(120)
    elif a == "exit124":
        os._exit(124)
    elif a == "kill9":
        os.kill(os.getpid(), signal.SIGKILL)
    elif a == "raise":
        raise RuntimeError("fake failure")
    else:
        time.sleep(float(a))
    t1 = time.time()
    with open(os.environ["FAKE_EVENTS"], "a") as f:
        f.write(f"{job.id} {job.kind} {t0:.6f} {t1:.6f} {os.environ.get('MS3_SLOTS', '')}\\n")
    outputs.dump({"id": job.id}, Path(out) / "runs" / mc.job_file_name(job.id))
    return {"runs": 1}


def summary(out):
    mc.dump_json({"records": len(mc.read_records(out))}, Path(out) / "summary.json")


if __name__ == "__main__":
    sys.exit(mc.main(EXP, jobs=jobs, run=run, summary=summary))
'''

RUN_SCRIPT = '''\
set -u
source "$1"
ms3_init "$FAKE_EXP"
ms3_list
ms3_manifest
ms3_run_jobs pool
ms3_run_jobs alone
ms3_run_jobs milp
ms3_manifest
ms3_summary
ms3_finish
'''


def _scope_works() -> bool:
    if shutil.which("systemd-run") is None:
        return False
    r = subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0",
                        "true"], capture_output=True, timeout=60)
    return r.returncode == 0


@pytest.fixture(scope="module")
def scope_env():
    return {} if _scope_works() else {"MS3_SCOPE": "0"}


def _root(tmp_path: Path, e11: bool) -> Path:
    root = tmp_path / "root"
    (root / "out").mkdir(parents=True)
    if e11:
        (root / "out" / "e11").mkdir()
        (root / "out" / "e11" / "summary.json").write_text("{}\n")
    mod = tmp_path / "mod"
    mod.mkdir()
    (mod / "fake_ms3_exp.py").write_text(FAKE_DRIVER)
    (tmp_path / "run_fake.sh").write_text(RUN_SCRIPT)
    return root


def _env(tmp_path, root, n, exp, jobs, scope_env, **extra) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("MS3_")}
    env.update(MS3_ROOT=str(root), MS3_WORKERS=str(n), MS3_POLL_S="0.2", MS3_PY=sys.executable,
               MS3_MODULE="fake_ms3_exp", PYTHONPATH=os.pathsep.join([str(tmp_path / "mod"), str(SIM)]),
               FAKE_EXP=exp, FAKE_JOBS=json.dumps(jobs), FAKE_EVENTS=str(tmp_path / "events.txt"),
               FAKE_PIDFILE=str(tmp_path / f"{exp}.pid"), FAKE_CGROUP_LOG=str(tmp_path / "cgroups.txt"), **scope_env)
    env.update({k: str(v) for k, v in extra.items()})
    return env


def _start(tmp_path, env):
    return subprocess.Popen(["bash", str(tmp_path / "run_fake.sh"), str(LIB)], env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, cwd=str(tmp_path))


def _finish(procs, timeout=180) -> list[tuple[int, str]]:
    res = []
    try:
        for p in procs:
            out, _ = p.communicate(timeout=timeout)
            res.append((p.returncode, out))
    finally:
        for p in procs:
            if p.poll() is None:
                p.kill()                    # by PID (Popen.kill sends SIGKILL to that process)
    return res


def _events(tmp_path) -> list[dict]:
    f = tmp_path / "events.txt"
    rows = []
    for line in (f.read_text().splitlines() if f.is_file() else []):
        jid, kind, t0, t1, *slots = line.split()
        rows.append({"id": jid, "kind": kind, "t0": float(t0), "t1": float(t1),
                     "slots": slots[0].split(",") if slots else []})
    return rows


def _max_overlap(rows) -> int:
    ev = sorted([(r["t0"], 1) for r in rows] + [(r["t1"], -1) for r in rows], key=lambda e: (e[0], e[1]))
    cur = best = 0
    for _, d in ev:
        cur += d
        best = max(best, cur)
    return best


def _jobs(exp: str, dur: float) -> list:
    return ([["pool", f"{exp}:p:i={i}", dur] for i in range(4)] + [["alone", f"{exp}:a", dur]]
            + [["milp", f"{exp}:m:i={i}", dur] for i in range(3)])


@pytest.mark.parametrize("n", [0, 2, 4])
def test_semaphore_two_scripts(tmp_path, scope_env, n):
    """Two run scripts at once (4 pool, 1 alone, 3 MILP jobs each): with N = 0 both exit 2 with 'E11 has not
    finished (§3.2)' before their first job; with N = 2 and 4 every job runs once, never more than N at a time
    nor more than 2 MILP jobs, the 'alone' jobs overlap no other job and hold slot0 ... slot<N-1>, a pool job holds
    one slot below N and a MILP job one slot and one MILP lock; every job's record says ok, with its slots, and
    so do the records of the summary and of the manifest (written twice, each time holding one slot); with a
    working systemd user manager, every process of the driver (--list and --manifest included) runs under the
    3G cap."""
    root = _root(tmp_path, e11=n > 0)
    exps = ("t1", "t2")
    procs = [_start(tmp_path, _env(tmp_path, root, n, e, _jobs(e, 0.6), scope_env)) for e in exps]
    res = _finish(procs)
    if n == 0:
        for rc, out in res:
            assert rc == 2 and "E11 has not finished (§3.2)" in out, out
        assert not _events(tmp_path) and not (root / "out" / "t1").exists()
        return
    for rc, out in res:
        assert rc == 0, out
    rows = _events(tmp_path)
    assert sorted(r["id"] for r in rows) == sorted(j[1] for e in exps for j in _jobs(e, 0))
    assert _max_overlap(rows) <= n
    assert _max_overlap([r for r in rows if r["kind"] == "milp"]) <= 2
    assert _max_overlap([r for r in rows if r["kind"] == "pool"]) >= 2          # the jobs do run in parallel
    for a in (r for r in rows if r["kind"] == "alone"):
        others = [r for r in rows if r is not a and r["t0"] < a["t1"] and a["t0"] < r["t1"]]
        assert not others, (a, others)
        assert a["slots"] == [f"slot{i}" for i in range(n)]
    for r in rows:
        if r["kind"] == "pool":
            assert len(r["slots"]) == 1 and r["slots"][0] in {f"slot{i}" for i in range(n)}
        elif r["kind"] == "milp":
            assert len(r["slots"]) == 2 and r["slots"][0] in {f"slot{i}" for i in range(n)} \
                and r["slots"][1] in {"milp0", "milp1"}
    for e in exps:
        out = root / "out" / e
        recs = mc.read_records(out)
        assert {i for i, r in recs.items() if r["status"] == "ok"} == \
            {j[1] for j in _jobs(e, 0)} | {f"{e}:summary", f"{e}:manifest"}
        assert all(recs[j[1]]["slots"] for j in _jobs(e, 0))
        assert len(recs[f"{e}:manifest"]["slots"]) == 1 and recs[f"{e}:manifest"]["kind"] == "pool"
        log = (out / f"run_{e}.log").read_text()
        assert log.count("[time] ") == 11 and log.count(f"[time] {e}:manifest peak RSS ") == 2
        assert f"[time] {e}:a peak RSS " in log and "exit 0" in log
        assert json.loads((out / "summary.json").read_text())["records"] >= 8
        assert (out / "jobs_list.txt").read_text().splitlines()[0] == f"pool {e}:p:i=0"
        assert json.loads((out / "manifest.json").read_text())["jobs"][0]["status"] == "ok"
        assert (out / "logs" / f"{mc.job_file_name(e + ':a')[:-5]}.log").is_file()
    locks = {p.name for p in (root / "out" / ".ms3_slots").iterdir()}
    assert {"slot0", "milp0"} <= locks <= {f"slot{i}" for i in range(n)} | {"milp0", "milp1", "gate"}
    procs = [ln.split() for ln in (tmp_path / "cgroups.txt").read_text().splitlines()]
    assert {p[0] for p in procs} == {"--list", "--manifest", "--job", "--summary"}
    assert sum(p[0] == "--list" for p in procs) == 2 and sum(p[0] == "--manifest" for p in procs) == 4
    if not scope_env:                                   # MS3_SCOPE=0 only where systemd-run cannot make a scope
        assert all(p[1].endswith(".scope") and p[2] == str(3 * 1024 ** 3) for p in procs), procs


def test_semaphore_n1_serializes_and_resume(tmp_path, scope_env):
    """With N = 1 two pool jobs and a MILP job run one after another; a job that raises is recorded as 'error' and
    exits 1; with MS3_RESUME=1 a second run skips the jobs whose record says ok and reruns only the failed one."""
    root = _root(tmp_path, e11=True)
    jobs = [["pool", "t1:p:i=0", 0.5], ["pool", "t1:p:i=1", 0.5], ["pool", "t1:bad", "raise"], ["milp", "t1:m", 0.5]]
    (rc, out), = _finish([_start(tmp_path, _env(tmp_path, root, 1, "t1", jobs, scope_env))])
    assert rc == 0, out
    rows = sorted(_events(tmp_path), key=lambda r: r["t0"])
    assert {r["id"] for r in rows[:2]} == {"t1:p:i=0", "t1:p:i=1"} and rows[2]["id"] == "t1:m"
    assert _max_overlap(rows) == 1 and all(a["t1"] <= b["t0"] for a, b in zip(rows, rows[1:]))
    o = root / "out" / "t1"
    bad = mc.read_record(o, "t1:bad")
    assert bad["status"] == "error" and bad["exit_code"] == 1 and "recorded an error" in bad["rule"]
    (rc, out), = _finish([_start(tmp_path, _env(tmp_path, root, 1, "t1", jobs, scope_env, MS3_RESUME=1))])
    assert rc == 0, out
    assert len(_events(tmp_path)) == 3                                           # nothing ran again
    log = (o / "run_t1.log").read_text()
    for j in ("t1:p:i=0", "t1:p:i=1", "t1:m"):
        assert f"{j}: ok before, skipped" in log
    assert log.count("[time] t1:bad ") == 2 and mc.read_record(o, "t1:bad")["status"] == "error"


def test_semaphore_killed_job_frees_its_slot(tmp_path, scope_env):
    """With N = 1 a hanging job of one script holds the only slot and a job of a second script waits; the hanging
    job, killed by its PID, is recorded as oom_at_3G (exit 137 without timeout) with the slot it held, and the
    waiting job starts only then. MILP jobs that exit 124 or are killed early (exit 137 before LIMIT + 60 s) are
    recorded as wall_limit and oom_at_3G."""
    root = _root(tmp_path, e11=True)
    ja = [["pool", "t1:hang", "hang"], ["milp", "t1:m124", "exit124"], ["milp", "t1:m137", "kill9"]]
    jb = [["pool", "t2:after", 0.2]]
    pa = _start(tmp_path, _env(tmp_path, root, 1, "t1", ja, scope_env))
    procs = [pa]
    pidfile = tmp_path / "t1.pid"
    try:
        t_end = time.time() + 120
        while not pidfile.is_file() and time.time() < t_end and pa.poll() is None:
            time.sleep(0.1)
        assert pidfile.is_file(), "the hanging job never started"
        pb = _start(tmp_path, _env(tmp_path, root, 1, "t2", jb, scope_env))
        procs.append(pb)
        time.sleep(2.0)
        assert not _events(tmp_path)                       # the second script's job waits for the slot
        pid = int(pidfile.read_text())
        t_kill = time.time()
        os.kill(pid, signal.SIGKILL)
        res = _finish(procs, timeout=120)
    finally:
        for p in procs:
            if p.poll() is None:
                p.kill()
        if pidfile.is_file():
            try:
                os.kill(int(pidfile.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
    for rc, out in res:
        assert rc == 0, out
    rows = _events(tmp_path)
    assert [r["id"] for r in rows] == ["t2:after"] and rows[0]["t0"] >= t_kill and rows[0]["slots"] == ["slot0"]
    o = root / "out" / "t1"
    h = mc.read_record(o, "t1:hang")
    assert h["status"] == "oom_at_3G" and h["exit_code"] == 137 and "without timeout" in h["rule"]
    assert h["slots"] == ["slot0"] and h["elapsed_s"] is not None and h["peak_rss_kb_time"] > 0
    m1, m2 = mc.read_record(o, "t1:m124"), mc.read_record(o, "t1:m137")
    assert (m1["status"], m1["exit_code"], m1["timeout_limit_s"]) == ("wall_limit", 124, 300.0)
    assert (m2["status"], m2["exit_code"]) == ("oom_at_3G", 137) and "< LIMIT + 60" in m2["rule"]
    assert m1["slots"][0] == "slot0" and m1["slots"][1] in ("milp0", "milp1")
    log = (o / "run_t1.log").read_text()
    assert "[time] t1:hang peak RSS " in log and ", exit 137" in log and "[time] t1:m124 " in log
    assert mc.read_record(root / "out" / "t2", "t2:after")["status"] == "ok"


ACQUIRE = '''\
set -u
source "$1"
mkdir -p "$MS3_SLOT_DIR"
_ms3_acquire "$2"
echo "$MS3_SLOTS" > "$3.partial" && mv "$3.partial" "$3"
while [ ! -e "$4" ]; do sleep 0.05; done
'''


def _locked(path: Path, mode: int) -> bool:
    """True iff `path` cannot be locked now with flock(2) `mode` (LOCK_SH or LOCK_EX) by another process."""
    import fcntl
    with open(path, "a") as f:
        try:
            fcntl.flock(f, mode | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(f, fcntl.LOCK_UN)
        return False


def _wait_for(cond, timeout=30.0) -> bool:
    t_end = time.time() + timeout
    while time.time() < t_end:
        if cond():
            return True
        time.sleep(0.05)
    return cond()


def test_semaphore_alone_waiter_gets_freed_slots(tmp_path):
    """The turnstile: with N = 2 and slot1 held by a running job, a waiting 'alone' job takes slot0 and the gate
    exclusively; pool and MILP launches of other scripts then take no slot, so the freed slot1 goes to the 'alone'
    job, which opens the gate once it holds both slots; when it ends, the pool and MILP launches get their slots
    and hold no lock on the gate. Locks are taken in this process with flock(2), as flock(1) does."""
    import fcntl
    root = _root(tmp_path, e11=True)
    slots = root / "out" / ".ms3_slots"
    slots.mkdir(parents=True)
    (tmp_path / "acquire.sh").write_text(ACQUIRE)
    env = {k: v for k, v in os.environ.items() if not k.startswith("MS3_")}
    env.update(MS3_ROOT=str(root), MS3_WORKERS="2", MS3_POLL_S="0.1", MS3_PY=sys.executable)
    procs = {}

    def start(name, kind):
        procs[name] = subprocess.Popen(["bash", str(tmp_path / "acquire.sh"), str(LIB), kind,
                                        str(tmp_path / f"{name}.slots"), str(tmp_path / f"{name}.stop")],
                                       env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def got(name):
        f = tmp_path / f"{name}.slots"
        return f.read_text().strip() if f.is_file() else None

    def stop(name):
        (tmp_path / f"{name}.stop").write_text("")
        procs[name].communicate(timeout=30)

    running = open(slots / "slot1", "a")
    try:
        fcntl.flock(running, fcntl.LOCK_EX)                       # a job of another script holds slot1
        start("alone", "alone")
        assert _wait_for(lambda: _locked(slots / "gate", fcntl.LOCK_SH) and _locked(slots / "slot0", fcntl.LOCK_EX))
        start("pool", "pool")
        start("milp", "milp")
        time.sleep(1.0)                                           # about 10 polls each
        assert got("pool") is None and got("milp") is None and got("alone") is None
        fcntl.flock(running, fcntl.LOCK_UN)                       # that job ends: its slot goes to the 'alone' job
        assert _wait_for(lambda: got("alone") is not None)
        assert got("alone") == "slot0,slot1"
        assert _wait_for(lambda: not _locked(slots / "gate", fcntl.LOCK_SH))      # the gate is open again
        time.sleep(0.5)
        assert got("pool") is None and got("milp") is None        # every slot is held by the 'alone' job
        stop("alone")
        assert _wait_for(lambda: got("pool") is not None and got("milp") is not None)
        p, m = got("pool"), got("milp").split(",")
        assert {p, m[0]} == {"slot0", "slot1"} and m[1] in ("milp0", "milp1")
        assert not _locked(slots / "gate", fcntl.LOCK_EX)         # holders of a slot hold no lock on the gate
        stop("pool")
        stop("milp")
    finally:
        running.close()
        for pr in procs.values():
            if pr.poll() is None:
                pr.kill()                                         # by PID
                pr.wait(timeout=30)


def test_check_copy_retry_wrappers(tmp_path, copy_pair):
    """MS7 addition C60: a retry wrapper (retry/<name>.json, written when ms3_lib.sh's rerun-once rule moves a failed
    job's record) records its first record's git_revision, which must be the clone's commit; a wrapper around a
    failure record without git_revision (with its rule) is allowed, one without a first record is not."""
    root, clone, exp = copy_pair
    base = mc.check_copy(exp, clone, root)
    commit, n0 = base["clone_commit"], base["n_no_revision"]
    wrap = {"job": "e1:milp:c=2", "moved": "2026-11-10T00:00:00", "rule": "rerun once",
            "first_record": {"job": "e1:milp:c=2", "status": "failed", "git_revision": commit}}
    _both(root, clone, exp, "retry/e1__milp__c__2.json", wrap)
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is True and res["n_no_revision"] == n0
    wrap["first_record"]["git_revision"] = "0" * 40
    _both(root, clone, exp, "retry/e1__milp__c__2.json", wrap)
    res = mc.check_copy(exp, clone, root)
    assert res["checks"]["revisions"] is False and res["revision_differs"] == ["retry/e1__milp__c__2.json"]
    del wrap["first_record"]["git_revision"]
    wrap["first_record"]["rule"] = "record-failure"
    _both(root, clone, exp, "retry/e1__milp__c__2.json", wrap)
    res = mc.check_copy(exp, clone, root)
    assert res["pass"] is True and res["n_no_revision"] == n0 + 1 and res["n_no_revision_unexpected"] == 0
    _both(root, clone, exp, "retry/e1__milp__c__2.json", {"job": "e1:milp:c=2", "rule": "rerun once"})
    res = mc.check_copy(exp, clone, root)
    assert res["checks"]["revisions_recorded"] is False
    assert res["no_revision_unexpected"] == ["retry/e1__milp__c__2.json"]
