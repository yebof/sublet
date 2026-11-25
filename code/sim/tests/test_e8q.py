"""Tests of E8q (X7): sublet/experiments/e8q.py, run_e8q.sh and e8q_analysis.py (design/ms8/plan.md D1, D4;
design/ms8/scout_x7_queue.md §2 test 7, §4).

Quick (no raw data):
- the job list: e8q:requests first, 36 cell jobs (3 tiers x 3 windows from the largest x 4 alignments at mu 1), each
  with the four tags, the bill BL0a and W in {0, 1, 2.5, 10}; the reduced list (E8 v2's: 6 cells), which needs
  MS3_E8V2_REDUCED with MS3_E8Q_REDUCED; the grid is E8 v2's;
- the gate on synthetic records (no registration, dirty tree, a wrong or missing sha256 line, ok), on a temporary
  registration file (its line 'e8q_analysis_sha256: <64 hex>' only), enforced in full runs (every full job raises
  before it builds anything) and recorded in reduced runs; the analysis's own registration check on a temporary
  repository;
- the summary on cell records made by real QueueReplay states on a small stream (cells, E8 v2's reference, checks,
  the pooled histograms of hist.json) and the analysis on it: Q-0 (pass, a changed C_replay, another grid), Q-1
  (Delta, wins, same order, the holding rule), Q-2 (shares, TTFT percentiles and SLO attainment, also on hand
  histograms with D_fb and W shifts), Q-3 (the four parts add up to the gap), exit 2 on a missing input;
- run_e8q.sh with a fake driver (the gate refusal, exit 2; the passes; E8Q_ONLY), bash -n and executable.
With the raw traces and the a12 outputs (needs_raw, needs_a12, slow): run_e8q.sh --reduced on the cell (M, 60, 1)
under a scratch MS3_ROOT, every job ok, E8q-1 to E8q-3 passing, and at W = 0 C_fluid and C_replay of every tag equal
to E8 v2's reduced pair job on the same cell (the identity Q-0 checks at full scale), with the analysis on the output.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from fixtures import SIM

from sublet import replay as rp
from sublet.experiments import e8
from sublet.experiments import e8q
from sublet.experiments import e8q_analysis as qa
from sublet.experiments import e8v2
from sublet.experiments import ms3_common as mc
from sublet.experiments import s1v2 as sv
from sublet.replay import queue as rq
from sublet.replay.loop import Placement, ServiceModel

RUN = SIM / "sublet" / "experiments" / "run_e8q.sh"
SHA = "ab" * 32


@pytest.fixture()
def full(monkeypatch):
    for k in (e8q.REDUCED_ENV, e8v2.REDUCED_ENV, e8.REDUCED_ENV):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(e8q, "_GATE", {})


# ---------------------------------------------------------------- jobs and settings
def test_job_list(full):
    js = e8q.jobs()
    mc.check_jobs(js)
    assert js[0].id == "e8q:requests" and len(js) == 37
    cells = js[1:]
    assert cells[0].id == e8q.cell_id("S", 60, 1) == "e8q:cell:tier=S:win=60:c=1"
    assert {(j.params["tier"], j.params["win"], j.params["c"]) for j in cells} == \
        {(t, w, c) for t in e8.TIERS for w in e8.WINDOWS for c in e8.ALIGNMENTS}
    for j in cells:
        assert j.params["tags"] == ["Sublet", "A9", "BL1-BO", "BL5-cur"] and j.params["bill"] == "BL0a"
        assert j.params["waits"] == [0.0, 1.0, 2.5, 10.0] and j.params["mu"] == 1.0 and j.kind == "pool"
    S = e8q.settings()
    assert {k: v for k, v in S.items() if k != "waits"} == e8v2.settings() and S["waits"] == e8q.WAITS
    assert e8q.W_STAR in e8q.WAITS and e8q.TAGS == sv.TAGS4
    assert "e8q" not in mc.COPY_PARTS                      # one folder out/e8q/, no parts


def test_reduced_list(full, monkeypatch):
    monkeypatch.setenv(e8q.REDUCED_ENV, "1")
    with pytest.raises(RuntimeError):
        e8q.jobs()                                         # E8 v2's builders would build the full instance
    monkeypatch.setenv(e8v2.REDUCED_ENV, "1")
    js = e8q.jobs()
    assert len(js) == 1 + 3 * 2 and e8q.settings()["horizon_min"] == 360
    assert [j.id for j in js[1:3]] == [e8q.cell_id("S", 60, 1), e8q.cell_id("S", 5, 1)]


# ---------------------------------------------------------------- the gate
def test_gate_rules(full, tmp_path, monkeypatch):
    good = {"registration_at_head": True, "dirty_paths": [], "analysis_sha256_registered": SHA,
            "analysis_sha256_disk": SHA, "analysis_sha256_head": SHA}
    ok, why, _ = e8q.check_registration(good)
    assert ok and "as registered" in why
    for change, frag in ((dict(registration_at_head=False, analysis_sha256_registered=None), "does not exist"),
                         (dict(dirty_paths=[" M x.py"]), "dirty"), (dict(dirty_paths=None), "cannot tell"),
                         (dict(analysis_sha256_registered=None), "records no line"),
                         (dict(analysis_sha256_disk="cd" * 32), "analysis_sha256_disk"),
                         (dict(analysis_sha256_head=None), "analysis_sha256_head")):
        ok, why, _ = e8q.check_registration({**good, **change})
        assert not ok and frag in why, change
    reg = tmp_path / "registration.md"
    reg.write_text(f"# MS8 registration\n\ne7b_analysis_sha256: {'cd' * 32}\ne8q_analysis_sha256: {SHA}\n")
    assert e8q.registered_sha256(reg.read_text()) == SHA
    assert e8q.registered_sha256("e8q_analysis_sha256: abc\n") is None and e8q.registered_sha256(None) is None
    assert e8q.registered_sha256(f"x e8q_analysis_sha256: {SHA}\n") is None       # only a line of its own
    # enforced in a full run: every full job raises before it builds anything
    monkeypatch.setattr(e8q, "registration_record", lambda: {**good, "registration_at_head": False})
    monkeypatch.setattr(e8v2, "build", lambda *a, **k: pytest.fail("built before the gate"))
    for j in e8q.jobs()[:2]:
        with pytest.raises(RuntimeError, match="does not start"):
            e8q.run(j, mc.JobOutputs(), tmp_path)
    assert e8q.check_start() == 1
    # recorded, not enforced, in a reduced run
    monkeypatch.setattr(e8q, "_GATE", {})
    monkeypatch.setenv(e8q.REDUCED_ENV, "1")
    g = e8q.gate()
    assert g["ok"] is False and g["enforced"] is False and g["kind"] == "ms8_registration"
    assert e8q.check_start() == 0
    monkeypatch.setattr(e8q, "_GATE", {})
    monkeypatch.delenv(e8q.REDUCED_ENV)
    monkeypatch.setattr(e8q, "registration_record", lambda: dict(good))
    assert e8q.gate()["ok"] is True and e8q.gate()["enforced"] is True


def test_analysis_registration_on_a_temporary_repository(tmp_path):
    sha = "ef" * 32
    assert qa.registration(sha, tmp_path)["exists"] is False
    f = tmp_path / "design" / "ms8" / "registration.md"
    f.parent.mkdir(parents=True)
    f.write_text(f"e8q_analysis_sha256: {sha}\n")
    r = qa.registration(sha, tmp_path)
    assert r["exists"] and r["matches"] and r["registered_sha256"] == sha
    assert qa.registration("00" * 32, tmp_path)["matches"] is False
    assert qa.REGISTRATION == e8q.REGISTRATION and qa.REG_SHA_RE.pattern == e8q.REG_SHA_RE.pattern


# ---------------------------------------------------------------- synthetic cell records
def _svc():
    return ServiceModel(tier="M", a5_tier="test", n_seq=16, tpot_s=0.02, w_in=0.3, kappa_wtok_per_min=60 * 16 / 0.02)


def _states(seed: int, n_sec: int = 300):
    """Real QueueReplay results on a small stream: one placement for the tags (the same copies and placement, so
    they differ by their fluid lease only) and the zero placement for the bill, at every W."""
    rng = np.random.default_rng(seed)
    n = rng.poisson(1.6 * n_sec)
    t = np.sort(rng.random(n) * n_sec)
    inp, out = rng.integers(1, 3000, n).astype(float), rng.integers(1, 400, n).astype(float)
    T = n_sec // 60
    W = rng.integers(0, 4, size=(3, T)).astype(float) / 8.0
    plan = Placement(W=W, delta=np.array([0.5, 0.1, 0.2]), ok=np.ones(3, bool), q=7.15, mu_fb=0.2, fast_min=1,
                     site_ids=("a", "b", "c"))
    svc = _svc()
    idx = rp.StreamIndex.build(t, n_sec)
    ring = rp.ring_size(float((0.3 * inp + out).max()), svc)
    d = np.where(np.arange(T) % 2 == 0, 1.0, 0.0)
    cls = np.array([rq.RECLAIM, rq.LOAD, rq.OVERFLOW, rq.BASE, rq.OVERFLOW][:T], np.int8)
    sts = [rq.QueueReplay(p, svc, 8, ring, w, c_, d, 12000.0, n_sec)
           for p, c_ in ((plan, cls), (rq.zero_placement(plan), rq.demand_classes(d))) for w in e8q.WAITS]
    lock = rq.run_lockstep(rq.QCopier(t, inp, out, idx, 2.3, 0.3, seed=4), sts, n_sec, 12000.0)
    res = [s.finish(lock["copier"]) for s in sts]
    k = len(e8q.WAITS)
    return res[:k], res[k:]


LEASE = {"Sublet": 1.0, "A9": 1.5, "BL1-BO": 3.0, "BL5-cur": 2.0}


def _cell_record(tier, win, c, seed, guard=None, lease=LEASE):
    tag_states, bill_states = _states(seed)
    runs = {}
    for tg in e8q.TAGS:
        fl = {"lease": lease[tg], "loading": 0.25, "routing": 0.01, "fallback": 0.05, "stranding": 0.002}
        fl["total"] = sum(fl.values())
        x = {"tag": tg, "fluid": fl, "lease_usd": fl["lease"] + fl["loading"],
             "headroom": {"share_all": 0.4, "share_overflow": 0.2}, "classes": {"reclaim": 1},
             "e8_2": {"pass": True}, "e8_3": {"pass": True}, "n_leases": 3, "n_announced": 1,
             "entry": {"status": "ok", "a8": guard if tg == "Sublet" else None}, "by_W": {}}
        for w, r in zip(e8q.WAITS, tag_states):
            err = e8.cost_error(fl, r["costs"])
            x["by_W"][e8q.wkey(w)] = {**err, "gap_usd": err["C_replay"] - err["C_fluid"], **e8q._state_brief(r)}
        runs[tg] = x
    bl = 0.4
    fb = {k: 0.0 for k in e8.COMPONENTS}
    fb.update(fallback=bl, total=bl)
    runs["BL0a"] = {"tag": "BL0a", "fluid": fb, "lease_usd": 0.0, "classes": {}, "by_W": {}}
    for w, r in zip(e8q.WAITS, bill_states):
        err = e8.cost_error(fb, r["costs"])
        runs["BL0a"]["by_W"][e8q.wkey(w)] = {**err, "gap_usd": err["C_replay"] - err["C_fluid"],
                                            **e8q._state_brief(r)}
    return {"kind": "cell", "tier": tier, "win": win, "c": c, "runs": runs, "errors": [], "service": {"tier": tier},
            "prefill_tok_per_s": 12000.0}


GUARD = {"certificate": {"held": True, "available": True}, "certificate_case": "W(a)",
         "envelope": {"ok": True, "max_excess_usd": -1.0}, "aborted": False, "project": True, "s_fb_all": True,
         "t0g_bound_all": True, "projected_slots": 3, "projection": {"K0": 0}}


def _write_cells(out, cells):
    for (t, w, c), rec in cells.items():
        jid = e8q.cell_id(t, w, c)
        mc.dump_json({"job": jid, "status": "ok"}, mc.record_path(out, jid))
        mc.dump_json(rec, e8q.run_path(out, jid), compact=True)


def _e8v2_ref(cells, horizon=e8.WEEK_MIN, tight=e8.TIGHTNESS):
    out = {"meta": {"grid": {"horizon_min": horizon, "market_tightness": tight}}, "cells": {}}
    for (t, w, c), rec in cells.items():
        for tg in e8q.TAGS:
            x = rec["runs"][tg]
            out["cells"].setdefault(t, {}).setdefault(str(w), {}).setdefault(str(c), {})[tg] = {
                "C_fluid": x["fluid"]["total"], "C_replay": x["by_W"]["0"]["C_replay"]}
    return out


def test_summary_and_analysis(full, tmp_path, monkeypatch):
    monkeypatch.setattr(e8q, "registration_record", lambda: {"registration_at_head": False, "dirty_paths": []})
    root = tmp_path / "root"
    out = root / "out" / "e8q"
    cells = {("M", 15, 1): _cell_record("M", 15, 1, 0, GUARD), ("M", 15, 2): _cell_record("M", 15, 2, 1, GUARD),
             ("L", 5, 1): _cell_record("L", 5, 1, 2, GUARD,
                                       lease={"Sublet": 3.0, "A9": 1.5, "BL1-BO": 1.0, "BL5-cur": 2.0})}
    _write_cells(out, cells)
    ref = _e8v2_ref(cells)
    f8 = root / "out" / "e8v2" / "a" / "summary.json"
    mc.dump_json(ref, f8)
    monkeypatch.setattr(e8q, "E8V2_SUMMARY", f8)
    s = e8q.summary(out)
    c = s["cells"]["M"]["15"]["1"]
    assert set(c) == {"Sublet", "A9", "BL1-BO", "BL5-cur", "BL0a"}
    assert set(c["Sublet"]["by_W"]) == {"0", "1", "2.5", "10"} and c["Sublet"]["guard"]["projected_slots"] == 3
    assert c["Sublet"]["e8v2"]["C_replay"] == c["Sublet"]["by_W"]["0"]["C_replay"]
    assert "hist" not in c["Sublet"]["by_W"]["2.5"]["by_class"]["base"]
    assert s["checks"]["E8q-1"]["status"] == "missing" and s["checks"]["E8q-1"]["n"] == 3 * 5 * 4
    assert not s["checks"]["E8q-1"]["failures"] and s["checks"]["E8q-4"]["n_runs"] == 3
    h = json.loads((out / "hist.json").read_text())
    pooled = sum(rq.dense(h["tiers"]["M"]["Sublet"]["2.5"][cn][kn]).sum() for cn in rq.CLASSES for kn in rq.KINDS)
    assert pooled == sum(cells[k]["runs"]["Sublet"]["by_W"]["2.5"]["counts"]["copies"] for k in cells if k[0] == "M")
    # the analysis
    a = qa.run_analysis(root, repo=tmp_path)
    assert a["q0"]["status"] == "missing" and a["q0"]["n"] == a["q0"]["n_equal"] == 12
    assert a["q0"]["n_missing"] == 33 * 4 and a["q0"]["n_expected"] == 36 * 4
    o = a["q1"]["overall"]
    assert o["0"]["n_cells"] == 36 and o["0"]["n_with_delta"] == 3 and o["0"]["wins"] == 2 and o["2.5"]["wins"] == 2
    e = a["q1"]["cells"]["2.5"]["M"]["15"]["1"]
    assert e["best_of_pair"] == "BL5-cur" and e["delta_usd"] == pytest.approx(1.0) and e["win"] is True
    assert e["rank_replay"] == ["Sublet", "A9", "BL5-cur", "BL1-BO"] == e["rank_fluid"] and e["same_order"]
    assert e["delta"] == pytest.approx(1.0 / e["bill"])
    el = a["q1"]["cells"]["2.5"]["L"]["5"]["1"]
    assert el["win"] is False and el["delta_usd"] == pytest.approx(-2.0)
    r = a["q1"]["rule"]
    assert r["wins_hold"] is True and r["E_falls"] == (r["sublet_E_median_w_star"] < r["sublet_E_median_w0"])
    # review finding 1: |E|, the cells with E < 0 and the bill's own E, per W (descriptive, not part of 'holds')
    import statistics
    for W in ("0", "2.5"):
        es = [x["tags"]["Sublet"]["E"] for t in a["q1"]["cells"][W].values() for y in t.values() for x in y.values()
              if x["tags"]["Sublet"]["E"] is not None]
        bs = [x["bill_E"] for t in a["q1"]["cells"][W].values() for y in t.values() for x in y.values()
              if x["bill_E"] is not None]
        assert len(es) == 3 and len(bs) == 3
        assert o[W]["E_abs_median"]["Sublet"] == pytest.approx(statistics.median(abs(v) for v in es))
        assert o[W]["n_E_negative"]["Sublet"] == sum(1 for v in es if v < 0)
        assert o[W]["bill_E_median"] == pytest.approx(statistics.median(bs))
        assert o[W]["bill_n_E_negative"] == sum(1 for v in bs if v < 0)
    assert r["abs_E_falls"] == (r["sublet_E_abs_median_w_star"] < r["sublet_E_abs_median_w0"])
    assert r["bill_E_median_w_star"] == o["2.5"]["bill_E_median"]
    assert set(a["headline"]["bill_E_median"]) == set(o) and "abs_E_falls" in a["headline"]["rule"]
    q2 = a["q2"]["by_tier"]["M"]["Sublet"]["2.5"]
    allc = q2["all"]
    assert allc["copies"] == sum(q2[cn]["copies"] for cn in rq.CLASSES) > 0
    assert 0 <= allc["fallback_share"] <= 1 and allc["ttft"]["1"]["n"] == allc["copies"]
    assert allc["ttft"]["1"]["slo_s"] == 2.5 and a["q2"]["by_tier"]["L"]["Sublet"]["0"]["all"]["ttft"]["1"][
        "slo_s"] == 4.0
    assert a["q3"]["max_abs_residual_usd"] < 1e-9
    p = a["q3"]["overall"]["2.5"]["Sublet"]
    assert p["n"] == 3 and p["gap_usd"] is not None
    md = (out / "analysis.md").read_text()
    assert "Q-0" in md and "## Headline" in md and "bill E median" in md
    assert a["meta"]["registered_full_inputs"] is False and len(a["meta"]["inputs"]) == 3
    # Q-0 fails on a changed C_replay; another grid is no reference
    ref["cells"]["M"]["15"]["1"]["A9"]["C_replay"] *= 1 + 1e-6
    mc.dump_json(ref, f8)
    a = qa.run_analysis(root, repo=tmp_path)
    assert a["q0"]["status"] == "fail" and a["q0"]["failures"] == ["M:15:1:A9"]
    ref["meta"]["grid"]["horizon_min"] = 360
    mc.dump_json(ref, f8)
    assert qa.run_analysis(root, repo=tmp_path)["q0"]["status"] == "no reference"
    # a missing input: exit 2, nothing written
    (out / "hist.json").unlink()
    (out / "analysis.json").unlink()
    assert qa.main(["--root", str(root)]) == 2 and not (out / "analysis.json").exists()


def test_ttft_stats_on_hand_histograms():
    n = qa._dense(None, 101).shape[0]
    served = np.zeros(n, np.int64)
    fb = np.zeros(n, np.int64)
    fbw = np.zeros(n, np.int64)
    served[[10, 20]] = [50, 40]           # 0.10-0.11 s and 0.20-0.21 s
    fb[5] = 9                             # prefill 0.05 s, + D_fb 0.5 s -> bin 55
    fbw[5] = 1                            # + D_fb 0.5 + W 0.2 -> bin 75
    st = qa.ttft_stats(served, fb, fbw, 0.2, 0.5, 0.25, 0.01)
    assert st["n"] == 100 and st["p50"] == pytest.approx(0.11) and st["p99"] == pytest.approx(0.56)
    assert st["p999"] == pytest.approx(0.76) and st["slo_attainment"] == pytest.approx(0.9)
    st = qa.ttft_stats(served, fb, fbw, 0.2, 2.0, 0.25, 0.01)          # 2 s beyond the last bin (1 s)
    assert st["p99"] is None and "last bin" in st["p99_note"] and st["p50"] == pytest.approx(0.11)
    assert qa.ttft_stats(served * 0, fb * 0, fbw * 0, 0.2, 0.5, 0.25, 0.01)["p50"] is None
    h = np.arange(10)
    assert qa._shift(h, 3).sum() == h.sum() and qa._shift(h, 3)[-1] == 7 + 8 + 9 + 6
    assert qa._shift(h, 20)[-1] == h.sum()


def test_decompose_adds_up():
    x = {"fluid": {"routing": 1.0, "fallback": 5.0, "stranding": 0.5},
         "by_W": {"0": {"gap_usd": 4.5, "replay": {"routing": 0.5, "fallback": 9.0, "stranding": 1.0},
                        "fallback_by_demand": {"zero": {"usd": 2.0}, "positive": {"usd": 7.0}}}}}
    p = qa.decompose(x, "0")
    assert p == {"fallback_zero_demand": 2.0, "fallback_overflow": 2.0, "stranding": 0.5, "routing": -0.5,
                 "gap_usd": 4.5, "residual_usd": 0.5}
    assert qa.decompose({}, "0") is None


# ---------------------------------------------------------------- run_e8q.sh with a fake driver
FAKE_DRIVER = '''
import json, os, sys, time
from pathlib import Path
from sublet.experiments import ms3_common as mc

def jobs():
    return [mc.Job(j, "pool", {"sleep": s}) for j, s in json.loads(os.environ["FAKE_JOBS"])]

def run(job, outputs, out):
    time.sleep(job.params["sleep"])
    if job.id == "e8q:requests":
        for f in ("azure2024_conv.json", "azure2024_conv_t_s.npy", "azure2024_conv_inp.npy", "azure2024_conv_out.npy"):
            outputs.write_text("x", Path(out) / "runs" / "requests" / f)
    with open(os.environ["FAKE_EVENTS"], "a") as f:
        f.write(f"{job.id}\\n")
    return {"runs": 0}

def summary(out):
    with open(os.environ["FAKE_EVENTS"], "a") as f:
        f.write("summary\\n")
    mc.dump_json({"records": len(mc.read_records(out))}, out / "summary.json")

if __name__ == "__main__":
    if "--check-start" in sys.argv:
        ok = os.environ.get("FAKE_GATE", "1") == "1"
        print(f"[e8q] gate {'ok' if ok else 'REFUSED'}")
        sys.exit(0 if ok else 1)
    sys.exit(mc.main("e8q", jobs=jobs, run=run, summary=summary))
'''


def _scope_env() -> dict:
    if shutil.which("systemd-run") is None:
        return {"MS3_SCOPE": "0"}
    r = subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0",
                        "true"], capture_output=True, timeout=60)
    return {} if r.returncode == 0 else {"MS3_SCOPE": "0"}


FAKE_JOBS = [["e8q:requests", 0.1], ["e8q:cell:tier=S:win=60:c=1", 0.2], ["e8q:cell:tier=M:win=5:c=1", 0.1],
             ["e8q:cell:tier=L:win=5:c=1", 0.1]]


def _run_fake(tmp_path: Path, events: str = "events.txt", args=(), **extra):
    root = tmp_path / "root"
    (root / "out" / "e11").mkdir(parents=True, exist_ok=True)
    (root / "out" / "e11" / "summary.json").write_text("{}\n")
    mod = tmp_path / "mod"
    mod.mkdir(exist_ok=True)
    (mod / "fake_e8q.py").write_text(FAKE_DRIVER)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "FAKE_", "E8Q_"))}
    env.update(MS3_ROOT=str(root), MS3_WORKERS="2", MS3_POLL_S="0.2", MS3_PY=sys.executable, MS3_MODULE="fake_e8q",
               PYTHONPATH=os.pathsep.join([str(mod), str(SIM)]), FAKE_JOBS=json.dumps(FAKE_JOBS),
               FAKE_EVENTS=str(tmp_path / events), **_scope_env(), **extra)
    p = subprocess.run(["bash", str(RUN), *args], env=env, capture_output=True, text=True, timeout=300)
    f = tmp_path / events
    ev = f.read_text().split() if f.is_file() else []
    return p, ev, root / "out" / "e8q"


def test_run_script_with_a_fake_driver(tmp_path):
    p, ev, out = _run_fake(tmp_path / "ok")
    assert p.returncode == 0, p.stdout + p.stderr
    assert ev[0] == "e8q:requests" and ev[1] == "e8q:cell:tier=S:win=60:c=1" and ev[-1] == "summary"
    assert set(ev) == {j for j, _ in FAKE_JOBS} | {"summary"}
    recs = mc.read_records(out)
    assert recs["e8q:summary"]["status"] == "ok" and recs["e8q:manifest"]["status"] == "ok"
    log = (out / "run_e8q.log").read_text()
    assert "gate ok" in log and "timed alone" in log and log.rstrip().splitlines()[-1].startswith("[run_e8q] done ")
    p, ev, out = _run_fake(tmp_path / "refused", FAKE_GATE="0")
    assert p.returncode == 2 and ev == []
    assert "refused: E8q does not start" in (out / "run_e8q.log").read_text()
    p, ev, out = _run_fake(tmp_path / "only", E8Q_ONLY="tier=L:")
    assert p.returncode == 0 and set(ev) == {"e8q:requests", "e8q:cell:tier=L:win=5:c=1", "summary"}
    p, _, _ = _run_fake(tmp_path / "bad", E8Q_ONLY="(")
    assert p.returncode == 2 and "not a valid extended regex" in p.stderr
    p, _, _ = _run_fake(tmp_path / "mix", MS3_E8Q_REDUCED="1")
    assert p.returncode == 2 and "must agree" in p.stderr


def test_run_script_parses():
    assert subprocess.run(["bash", "-n", str(RUN)]).returncode == 0
    assert os.access(RUN, os.X_OK)


# ---------------------------------------------------------------- with the raw traces and the a12 outputs
@pytest.mark.needs_raw
@pytest.mark.needs_a12
@pytest.mark.slow
def test_reduced_run_end_to_end_and_identity_with_e8v2(tmp_path, monkeypatch):
    """run_e8q.sh --reduced on (M, 60, 1); then E8 v2's reduced request cache and pair job on the same cell in another
    scratch root: at W = 0 every tag's C_fluid and C_replay equal E8 v2's (1e-9 relative; in fact bit for bit)."""
    root = tmp_path / "root"
    (root / "out" / "e11").mkdir(parents=True)
    (root / "out" / "e11" / "summary.json").write_text("{}\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "E8Q_", "FAKE_"))}
    env.update(MS3_ROOT=str(root), MS3_WORKERS=os.environ.get("MS3_WORKERS", "2"), MS3_POLL_S="1",
               MS3_PY=sys.executable, E8Q_ONLY="tier=M:win=60:", **_scope_env())
    p = subprocess.run(["bash", str(RUN), "--reduced"], env=env, capture_output=True, text=True, timeout=3600)
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-3000:]
    out = root / "out" / "e8q"
    jid = e8q.cell_id("M", 60, 1)
    recs = mc.read_records(out)
    assert recs["e8q:requests"]["status"] == "ok" and recs[jid]["status"] == "ok" and recs[jid]["n_errors"] == 0
    s = json.loads((out / "summary.json").read_text())
    assert s["meta"]["reduced"] is True and s["meta"]["gate"]["enforced"] is False
    for k in ("E8q-1", "E8q-2", "E8q-3"):
        assert not s["checks"][k]["failures"] and s["checks"][k]["n"] > 0, k
    cell = s["cells"]["M"]["60"]["1"]
    for tg in e8q.TAGS + ("BL0a",):
        assert cell[tg]["status"] == "ok" and all(cell[tg]["by_W"][w]["conservation_pass"] for w in cell[tg]["by_W"])
    # E8 v2's pair job on the same reduced cell
    monkeypatch.setenv(e8v2.REDUCED_ENV, "1")
    monkeypatch.setenv(e8.REDUCED_ENV, "1")
    monkeypatch.setattr(sv, "_GATE", {})
    r2 = tmp_path / "e8v2root"
    o2 = r2 / "out" / "e8v2" / "a"
    js = {j.id: j for j in e8v2.jobs()}
    for j in ("e8v2:requests", e8v2.pair_id("M", 60, 1)):
        rec = mc.run_job("e8v2", js[j], lambda o, jj=js[j]: e8v2.run(jj, o, o2), o2, resume=False)
        assert rec["status"] == "ok" and rec["n_errors"] == 0, rec.get("error")
    f = json.loads(e8v2.run_path(o2, "pairs", e8v2.pair_id("M", 60, 1)).read_text())
    for tg in e8q.TAGS:
        x = f["runs"][tg]
        assert cell[tg]["C_fluid"] == x["C_fluid"], tg
        assert cell[tg]["by_W"]["0"]["C_replay"] == x["C_replay"], tg
        assert cell[tg]["by_W"]["0"]["replay"] == x["replay"]["costs"], tg
    # the analysis on the reduced output (E8 v2's full summary is of another grid: no reference)
    shutil.copy(e8q.E8V2_SUMMARY, (root / "out" / "e8v2" / "a").mkdir(parents=True) or
                root / "out" / "e8v2" / "a" / "summary.json")
    a = qa.run_analysis(root)
    assert a["meta"]["reduced"] is True and a["q0"]["status"] == "no reference"
    assert a["q1"]["overall"]["0"]["n_with_delta"] == 1 and a["q3"]["max_abs_residual_usd"] < 1e-6
