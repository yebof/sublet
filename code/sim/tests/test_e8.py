"""Tests of the E8 driver sublet/experiments/e8.py and its run script run_e8.sh (design/sim_spec_ms4.md §7.3, §7.8,
§7.9, §2.4-§2.6).

Quick: the job list (1 + 144 + 6 jobs, ids, kinds, the order with the largest window first, an estimate for every
job, the reduced list), the instance overrides per tier, the cost error and the peak hour on hand values, the summary
on synthetic job outputs (statuses of E8-1 ... E8-5, null forms, only 'ok' outputs used, an 'ok' record without its
run file listed as missing), and run_e8.sh's filtered passes with a fake driver (e8:requests first, then the first
e8:pair job alone, then the rest; no replay job without an ok e8:requests and its cache files; under MS3_RESUME=1 in
a tree without runs/ e8:requests is rerun and the first e8:pair job is logged as not timed). needs_a12 + needs_raw:
the reduced e8:requests, e8:pair and e8:mooncake jobs end to end in a temporary MS3_ROOT.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from sublet.experiments import e8
from sublet.experiments import ms3_common as mc

SIM = Path(__file__).resolve().parents[1]
RUN_E8 = SIM / "sublet" / "experiments" / "run_e8.sh"


# ---------------------------------------------------------------- jobs and instances
def test_job_list_full(monkeypatch):
    monkeypatch.delenv("MS3_E8_REDUCED", raising=False)
    js = e8.jobs()
    mc.check_jobs(js)
    kinds = [j.params["kind"] for j in js]
    assert len(js) == 151 and kinds.count("requests") == 1 and kinds.count("pair") == 144
    assert kinds.count("mooncake") == 6 and all(j.kind == "pool" for j in js)
    assert js[0].id == "e8:requests" and js[1].id == "e8:pair:tier=S:win=60:mu=1:c=1"     # the most copies
    wins = [j.params["win"] for j in js if j.params["kind"] == "pair" and j.params["tier"] == "S"]
    assert wins == [60] * 16 + [15] * 16 + [5] * 16
    assert all(j.est_s > 0 for j in js)
    est = {(j.params["tier"], j.params["win"]): j.est_s for j in js if j.params["kind"] == "pair"}
    assert all(est[(t, 5)] <= est[(t, 15)] <= est[(t, 60)] for t in "SML")
    pairs = {(j.params["tier"], j.params["win"], j.params["mu"], j.params["c"]) for j in js if kinds[js.index(j)] ==
             "pair"}
    assert pairs == {(t, w, u, c) for t in "SML" for w in (5, 15, 60) for u in (1.0, 0.2, 0.5, 2.0)
                     for c in (1, 2, 3, 4)}
    assert {j.id for j in js if j.params["kind"] == "mooncake"} == \
        {f"e8:mooncake:win={w}:prefix={p}" for w in (5, 15, 60) for p in ("off", "on")}
    for j in js:
        assert mc.parse_job_id(j.id)[0] == "e8"


def test_job_list_reduced(monkeypatch):
    monkeypatch.setenv("MS3_E8_REDUCED", "1")
    js = e8.jobs()
    assert len(js) == 1 + 12 + 4 and e8.settings()["horizon_min"] == 360
    assert js[0].params["horizon_min"] == 360 and js[1].id == "e8:pair:tier=S:win=60:mu=1:c=1"


@pytest.mark.parametrize("tier", ["S", "M", "L"])
def test_overrides_per_tier(monkeypatch, tier):
    monkeypatch.delenv("MS3_E8_REDUCED", raising=False)
    ov = e8.overrides(tier, 60, 0.5)
    assert ov["time.fast_slot_min"] == 1 and ov["time.horizon_min"] == 10080
    assert ov["llms"] == [{"id": tier, "catalog": "maas_a10", "entry": tier, "kappa_mult": 1.0}]
    b = ov["borrowers"]
    assert b["model"] == "series" and b["smoothing_min"] == 60 and b["market_tightness"] == 0.5
    assert b["list"] == [{"id": "azure0", "series": "azure2024_conv", "week_index": 0, "tier": tier,
                          "region": "north_america"}]
    assert ov["stranding.mu_over_beta_tilde"] == 0.5
    assert [c["id"] for c in ov["contracts"]] == ["s5_tau5_H60", "s5_tau60_H0", "protected"]
    spec = e8.run_spec(tier, 60, 0.5, 3)
    assert spec["engine"] == {"check_invariants": True, "record_routing": True}
    assert spec["policy"] == {"id": "A6", "params": {}} and spec["seeds"]["policy"] == [0]
    assert spec["lender_model"] == e8.LENDER_MODEL
    with pytest.raises(ValueError):
        e8.overrides("X", 5, 1.0)


def test_cost_error_and_peak_hour():
    import numpy as np
    fl = {"lease": 10.0, "loading": 1.0, "routing": 2.0, "fallback": 30.0, "stranding": 1.0, "total": 44.0}
    r = e8.cost_error(fl, {"routing": 1.0, "fallback": 40.0, "stranding": 3.0})
    assert r["C_fluid"] == 44.0 and r["C_replay"] == 55.0 and r["error"] == pytest.approx(11.0 / 55.0)
    z = e8.cost_error({**fl, "total": 33.0, "lease": 0.0, "loading": 0.0}, {"routing": 0, "fallback": 0,
                                                                            "stranding": 0})
    assert z["error"] is None and z["error_note"]
    d = np.zeros(180)
    d[70:80] = 1.0
    d[150:155] = 3.0
    assert e8.peak_hour(d, 1) == (2, 15.0)
    with pytest.raises(ValueError):
        e8.peak_hour(np.zeros(30), 1)


# ---------------------------------------------------------------- the summary on synthetic outputs
def _pair_rec(jid, t, w, u, c, err, *, ok1=True, ok2=True, ok3=True):
    costs = {"routing": 1.0, "fallback": 5.0, "stranding": 0.5, "total": 6.5}
    fl = {"lease": 3.0, "loading": 0.0, "routing": 1.0, "fallback": 4.0, "stranding": 0.5, "total": 8.5}
    return {"job": jid, "tier": t, "win": w, "mu": u, "c": c, "fluid": fl, "replay": {"costs": costs},
            "C_fluid": 8.5, "C_replay": 9.5, "error": err, "scale": {"gamma": 9.0, "own_slots": 100, "C0_loads": 0.8},
            "policy": {"id": "A6", "params": {"variant": "practical"}, "info_class": "online-I1",
                       "driver_inputs": {}},
            "service": {"n_seq": 128}, "e8_1": {"pass": ok1, "tokens_rel_diff": 1e-15},
            "e8_2": {"pass": ok2, "routing": {"rel_diff": 1e-16}, "fallback": {"rel_diff": 2e-16},
                     "stranding": {"rel_diff": 0.0}},
            "e8_3": {"pass": ok3, "n_invariant_failures": 0 if ok3 else 2, "gpu_only_lease_slots": 0},
            "fluid_s": 1.0, "replay_s": 2.0, "git_revision": "x"}


def _moon_rec(jid, w, p, err):
    return {"job": jid, "win": w, "prefix": p, "error": err, "C_fluid": 5.0, "C_replay": 6.0, "gamma_mc": 30.0,
            "copies": 1000, "mooncake_trace": {"block_hit_ratio_infinite_cache": 0.366},
            "fluid": {k: 1.0 for k in e8.COMPONENTS}, "replay": {"costs": {"routing": 0, "fallback": 1,
                                                                            "stranding": 0, "total": 1},
                                                                  "hits": {"hit_ratio": 0.1 if p == "on" else None}},
            "hour": {"index": 3, "start_s": 10800}, "e8_1": {"pass": True, "tokens_rel_diff": 0.0},
            "e8_3": {"pass": True, "n_invariant_failures": 0, "gpu_only_lease_slots": 0}, "git_revision": "x"}


def _write(out: Path, jid: str, status: str, sub: str = None, rec=None):
    mc.dump_json({"job": jid, "status": status, "wall_s": 3.0}, mc.record_path(out, jid))
    if rec is not None:
        mc.dump_json(rec, e8.run_path(out, sub, jid))


def test_summary_on_synthetic_outputs(tmp_path, monkeypatch):
    monkeypatch.setenv("MS3_E8_REDUCED", "1")
    out = tmp_path / "e8"
    js = e8.jobs()
    errs = {}
    for i, j in enumerate(js):
        p = j.params
        if p["kind"] == "pair":
            errs[j.id] = 0.1 + 0.01 * i
            _write(out, j.id, "ok", "pairs", _pair_rec(j.id, p["tier"], p["win"], p["mu"], p["c"], errs[j.id]))
        elif p["kind"] == "mooncake":
            _write(out, j.id, "ok", "mooncake", _moon_rec(j.id, p["win"], p["prefix"], -0.2))
    bad = "e8:pair:tier=M:win=60:mu=2:c=1"
    _write(out, bad, "error", "pairs", _pair_rec(bad, "M", 60, 2.0, 1, 9.0, ok1=False))      # not used
    s = e8.summary(out)
    assert s["meta"]["reduced"] and bad in s["meta"]["jobs_missing"]
    assert s["meta"]["ignored_outputs"][0]["job"] == bad
    assert s["error"]["M"]["60"]["2"]["median"] is None and s["error"]["M"]["60"]["2"]["n"] == 0
    assert s["error"]["S"]["5"]["1"]["median"] == pytest.approx(errs["e8:pair:tier=S:win=5:mu=1:c=1"])
    assert s["error"]["S"]["5"]["1"]["by_c"] == {"1": pytest.approx(errs["e8:pair:tier=S:win=5:mu=1:c=1"])}
    assert s["components"]["L"]["5"]["1"]["replay"]["fallback"] == 5.0
    assert s["components"]["L"]["5"]["1"]["alignments"] == [1] and s["components"]["M"]["60"]["2"]["alignments"] == []
    assert s["meta"]["scale"]["S"]["5"] == {"gamma_by_c": {"1": 9.0}, "own_slots_by_c": {"1": 100},
                                            "C0_loads_by_c": {"1": 0.8}}
    assert s["meta"]["policy_resolved"]["info_class"] == "online-I1" and s["meta"]["outputs_missing"] == []
    assert s["mooncake"]["5"]["on"]["error"] == -0.2 and s["mooncake"]["60"]["off"]["hit_ratio"] is None
    ch = s["checks"]
    assert [ch[k]["status"] for k in ("E8-1", "E8-2", "E8-3", "E8-4", "E8-5")] == \
        ["pass", "pass", "pass", "informative", "informative"]
    assert ch["E8-1"]["n"] == 11 + 4 and ch["E8-1"]["n_expected"] == 16
    assert all(ch[k]["claim"] for k in ch)
    assert (out / "tables.md").read_text().startswith("# E8")
    # a failing replay and a fluid run with an invariant failure are bugs
    j = "e8:pair:tier=S:win=5:mu=1:c=1"
    _write(out, j, "ok", "pairs", _pair_rec(j, "S", 5, 1.0, 1, 0.1, ok1=False, ok3=False))
    s = e8.summary(out)
    assert s["checks"]["E8-1"]["status"] == "fail" and s["checks"]["E8-3"]["status"] == "fail"
    assert s["checks"]["E8-1"]["failures"] == [j] and s["checks"]["E8-2"]["status"] == "pass"
    # an ok record whose run file is gone is missing, not silently dropped
    gone = "e8:pair:tier=L:win=5:mu=1:c=1"
    e8.run_path(out, "pairs", gone).unlink()
    s = e8.summary(out)
    assert gone in s["meta"]["jobs_missing"] and [u["job"] for u in s["meta"]["outputs_missing"]] == [gone]
    assert s["meta"]["jobs_ok"] == len(js) - 3                  # no e8:requests record, the error job, the lost file
    assert s["error"]["L"]["5"]["1"]["median"] is None and "run file" in s["error"]["L"]["5"]["1"]["note"]
    assert s["checks"]["E8-1"]["n"] == 14 and s["checks"]["E8-1"]["n_expected"] == 16
    # nothing to check
    s = e8.summary(tmp_path / "empty")
    assert [s["checks"][k]["status"] for k in ("E8-1", "E8-2", "E8-3", "E8-4", "E8-5")] == ["missing"] * 5
    json.dumps(s, allow_nan=False)


# ---------------------------------------------------------------- run_e8.sh with a fake driver
FAKE_DRIVER = '''
import json, os, sys, time
from sublet.experiments import ms3_common as mc

def jobs():
    return [mc.Job(j, "pool", {}) for j in json.loads(os.environ["FAKE_JOBS"])]

def run(job, outputs, out):
    t0 = time.time()
    time.sleep(0.4)
    with open(os.environ["FAKE_EVENTS"], "a") as f:
        f.write(f"{job.id} {t0} {time.time()}\\n")
    if job.id == os.environ.get("FAKE_FAIL"):
        raise RuntimeError("fake failure")
    if job.id == "e8:requests" and not os.environ.get("FAKE_NO_CACHE"):
        d = out / "runs" / "requests"
        d.mkdir(parents=True, exist_ok=True)
        for f in ("azure2024_conv.json", "azure2024_conv_t_s.npy", "azure2024_conv_inp.npy",
                  "azure2024_conv_out.npy"):
            (d / f).write_text("x")
    return {"runs": 0}

def summary(out):
    mc.dump_json({"records": len(mc.read_records(out))}, out / "summary.json")

if __name__ == "__main__":
    sys.exit(mc.main("e8", jobs=jobs, run=run, summary=summary))
'''


def _scope_env() -> dict:
    if shutil.which("systemd-run") is None:
        return {"MS3_SCOPE": "0"}
    r = subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0",
                        "true"], capture_output=True, timeout=60)
    return {} if r.returncode == 0 else {"MS3_SCOPE": "0"}


def _run_script(tmp_path: Path, jobs: list, fail=None, events: str = "events.txt", **extra):
    root = tmp_path / "root"
    (root / "out" / "e11").mkdir(parents=True, exist_ok=True)
    (root / "out" / "e11" / "summary.json").write_text("{}\n")
    mod = tmp_path / "mod"
    mod.mkdir(exist_ok=True)
    (mod / "fake_e8.py").write_text(FAKE_DRIVER)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "FAKE_"))}
    env.update(MS3_ROOT=str(root), MS3_WORKERS="2", MS3_POLL_S="0.2", MS3_PY=sys.executable, MS3_MODULE="fake_e8",
               PYTHONPATH=os.pathsep.join([str(mod), str(SIM)]), FAKE_JOBS=json.dumps(jobs),
               FAKE_EVENTS=str(tmp_path / events), **_scope_env(), **extra)
    if fail:
        env["FAKE_FAIL"] = fail
    p = subprocess.run(["bash", str(RUN_E8)], env=env, capture_output=True, text=True, timeout=300)
    ev = {}
    f = tmp_path / events
    for line in (f.read_text().splitlines() if f.is_file() else []):
        jid, t0, t1 = line.split()
        ev[jid] = (float(t0), float(t1))
    return p, ev, root / "out" / "e8"


JOBS = ["e8:requests", "e8:pair:tier=S:win=5:mu=1:c=1", "e8:pair:tier=S:win=5:mu=1:c=2",
        "e8:pair:tier=S:win=5:mu=1:c=3", "e8:mooncake:win=5:prefix=off"]


def test_run_script_filtered_passes(tmp_path):
    p, ev, out = _run_script(tmp_path, JOBS)
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == set(JOBS)
    req, first = ev[JOBS[0]], ev[JOBS[1]]
    assert all(req[1] <= ev[j][0] for j in JOBS[1:])                   # the cache before every replay job
    assert all(first[1] <= ev[j][0] for j in JOBS[2:])                 # the first pair job alone
    rest = [ev[j] for j in JOBS[2:]]
    assert any(a[0] < b[1] and b[0] < a[1] for i, a in enumerate(rest) for b in rest[i + 1:])  # then in parallel
    log = (out / "run_e8.log").read_text()
    assert f"first e8:pair job {JOBS[1]} timed alone: " in log and "3 remaining e8:pair" in log
    assert log.rstrip().splitlines()[-1].startswith("[run_e8] done ")
    assert (out / "jobs_list.txt").read_text().split() == " ".join(f"pool {j}" for j in JOBS).split()
    recs = mc.read_records(out)
    assert all(recs[j]["status"] == "ok" for j in JOBS) and recs["e8:summary"]["status"] == "ok"


def test_run_script_stops_without_the_cache(tmp_path):
    p, ev, out = _run_script(tmp_path, JOBS, fail="e8:requests")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == {"e8:requests"}
    assert "e8:requests has no ok record or its cache files" in (out / "run_e8.log").read_text()
    assert mc.read_records(out)["e8:requests"]["status"] == "error"


def test_run_script_stops_with_an_ok_record_but_no_cache_files(tmp_path):
    p, ev, out = _run_script(tmp_path, JOBS, FAKE_NO_CACHE="1")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == {"e8:requests"} and mc.read_records(out)["e8:requests"]["status"] == "ok"
    assert "the replay jobs are not run" in (out / "run_e8.log").read_text()


def test_run_script_resume_rebuilds_a_missing_cache(tmp_path):
    """MS3_RESUME=1 in a tree with the job records but without runs/ (the repository after the copy): e8:requests
    is rerun, the ok replay jobs are skipped, and the first e8:pair job is logged as not timed."""
    p, ev, out = _run_script(tmp_path, JOBS)
    assert p.returncode == 0 and set(ev) == set(JOBS)
    shutil.rmtree(out / "runs")
    p, ev, out = _run_script(tmp_path, JOBS, events="events2.txt", MS3_RESUME="1")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == {"e8:requests"} and (out / "runs" / "requests" / "azure2024_conv_t_s.npy").is_file()
    log = (out / "run_e8.log").read_text()
    assert "request cache in runs/requests/ is incomplete: rerun" in log
    assert f"first e8:pair job {JOBS[1]}: ok before, not timed" in log
    assert f"{JOBS[2]}: ok before, skipped" in log


# ---------------------------------------------------------------- the reduced jobs end to end
@pytest.mark.needs_a12
@pytest.mark.needs_raw
def test_reduced_jobs_end_to_end(tmp_path, monkeypatch):
    """e8:requests, one e8:pair and one e8:mooncake job of the reduced list in a temporary root: records ok, E8-1,
    E8-2 and E8-3 pass, the run files record the git revision, the summary has meta.reduced true."""
    root = tmp_path / "root"
    (root / "out").mkdir(parents=True)
    monkeypatch.setenv("MS3_ROOT", str(root))
    monkeypatch.setenv("MS3_E8_REDUCED", "1")
    monkeypatch.delenv("MS3_RESUME", raising=False)
    for jid in ("e8:requests", "e8:pair:tier=L:win=5:mu=1:c=1", "e8:mooncake:win=5:prefix=on"):
        assert e8.main(["--job", jid]) == 0
    out = root / "out" / "e8"
    pr = mc.read_json(e8.run_path(out, "pairs", "e8:pair:tier=L:win=5:mu=1:c=1"))
    assert pr["e8_1"]["pass"] and pr["e8_2"]["pass"] and pr["e8_3"]["pass"] and pr["git_revision"] == mc.git_revision()
    assert pr["error"] is not None and pr["replay"]["counts"]["copies"] > 0
    fl = mc.read_json(e8.run_path(out, "fluid", "e8:pair:tier=L:win=5:mu=1:c=1"))
    assert fl["meta"]["git_revision"] == mc.git_revision() and "per_slot" in fl
    mo = mc.read_json(e8.run_path(out, "mooncake", "e8:mooncake:win=5:prefix=on"))
    assert mo["e8_1"]["pass"] and mo["replay"]["hits"]["hit_ratio"] is not None
    assert e8.main(["--summary"]) == 0
    s = mc.read_json(out / "summary.json")
    assert s["meta"]["reduced"] and s["checks"]["E8-1"]["status"] == "pass"
