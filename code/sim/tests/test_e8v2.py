"""Tests of E8 v2 part (a): sublet/experiments/e8v2.py, run_e8v2.sh and the E8 v2 rules of ms7_sens_analysis.py
(design/ms7/plan.md X3; design/ms7/feasibility/sens.md §2 C(a), §3 items 3, 5, 7; change C56).

Quick (no raw data):
- the instance is E8's: overrides() equals e8.overrides at full scale and in the reduced lists, and run_spec with
  e8.POLICY is e8.run_spec's spec (but its name and output folder);
- the job list: e8v2:requests first, 36 pair jobs (3 tiers x 3 windows x 4 alignments at mu 1, windows from the
  largest), 6 Mooncake jobs; the four tags in every replay job and A6's identity run at (M, 15, 1) only; the reduced
  list (6 hours, tightness 0.05, windows 5 and 60, alignment 1) with its identity cell (M, 60, 1); COPY_PARTS;
- the summary on synthetic pair and Mooncake records with a synthetic E8 summary: the cells, A6's reused pairs, check
  E8v2-0 (pass, a changed C_replay), E8-1/E8-2/E8-3 failures, the guard rows; the analysis's rankings (fluid against
  replayed, Sublet's rank, its margin against the pair) and the Mooncake block;
- run_e8v2.sh: bash -n and executable.
With the raw traces and the a12 outputs (needs_raw, needs_a12, slow): the reduced request cache and one reduced pair
job (M, 60, 1: the four tags and A6) through the runner, with E8-1, E8-2 and E8-3 passing for every tag.
"""
import copy
import json
import os
import subprocess

import pytest

from fixtures import SIM

from sublet.experiments import e8
from sublet.experiments import e8v2
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms7_sens_analysis as sa
from sublet.experiments import s1v2 as sv

RUN = SIM / "sublet" / "experiments" / "run_e8v2.sh"


@pytest.fixture()
def full(monkeypatch):
    monkeypatch.delenv(e8v2.REDUCED_ENV, raising=False)
    monkeypatch.delenv(e8.REDUCED_ENV, raising=False)


def test_instance_is_e8s(full, monkeypatch):
    for t in e8.TIERS:
        for w in e8.WINDOWS:
            assert e8v2.overrides(t, w, 1.0) == e8.overrides(t, w, 1.0)
    a = e8v2.run_spec(e8.POLICY[0], e8.POLICY[1], "M", 15, 1.0, 1)
    b = e8.run_spec("M", 15, 1.0, 1)
    assert {k: v for k, v in a.items() if k not in ("name", "out")} == \
        {k: v for k, v in b.items() if k not in ("name", "out")}
    monkeypatch.setenv(e8v2.REDUCED_ENV, "1")
    monkeypatch.setenv(e8.REDUCED_ENV, "1")
    assert e8v2.overrides("S", 60, 1.0) == e8.overrides("S", 60, 1.0)


def test_job_list(full):
    js = e8v2.jobs()
    mc.check_jobs(js)
    assert js[0].id == "e8v2:requests"
    pairs = [j for j in js if j.params["kind"] == "pair"]
    moons = [j for j in js if j.params["kind"] == "mooncake"]
    assert len(pairs) == 36 and len(moons) == 6 and len(js) == 43
    assert pairs[0].id == e8v2.pair_id("S", 60, 1)
    assert {(j.params["tier"], j.params["win"], j.params["c"]) for j in pairs} == \
        {(t, w, c) for t in e8.TIERS for w in e8.WINDOWS for c in e8.ALIGNMENTS}
    for j in pairs + moons:
        assert j.params["tags"][:4] == ["Sublet", "A9", "BL1-BO", "BL5-cur"] and j.params["mu"] == 1.0
    ident = [j for j in js if j.params.get("identity_tags")]
    assert [j.id for j in ident] == [e8v2.pair_id("M", 15, 1)] and ident[0].params["tags"][-1] == "A6"
    assert {(j.params["win"], j.params["prefix"]) for j in moons} == {(w, p) for w in e8.WINDOWS for p in ("off", "on")}
    assert e8v2.identity_cell() == ("M", 15, 1)
    assert mc.COPY_PARTS["e8v2"] == ("a",)


def test_reduced_list(monkeypatch):
    monkeypatch.setenv(e8v2.REDUCED_ENV, "1")
    js = e8v2.jobs()
    assert len(js) == 1 + 3 * 2 + 2 * 2
    assert e8v2.identity_cell() == ("M", 60, 1) and e8v2.settings()["horizon_min"] == 360
    assert [j.id for j in js if j.params.get("identity_tags")] == [e8v2.pair_id("M", 60, 1)]


def _x(cf, cr, guard=None, ok=True):
    x = {"C_fluid": cf, "C_replay": cr, "error": (cr - cf) / cr, "e8_1": {"pass": ok, "tokens_rel_diff": 0.0},
         "e8_2": {"pass": True}, "e8_3": {"pass": True}, "replay": {"costs": {"routing": 1.0, "fallback": cr - 1.0,
                                                                              "stranding": 0.0, "total": cr}},
         "entry": {"status": "ok", "a8": guard}, "fluid": {"total": cf}}
    return x


def test_summary_and_analysis(full, tmp_path, monkeypatch):
    monkeypatch.setattr(sv, "registration_record", lambda: {"registration_at_head": False, "dirty_paths": []})
    monkeypatch.setattr(sv, "_GATE", {})
    e8s = {"meta": {"grid": {"horizon_min": e8.WEEK_MIN, "market_tightness": e8.TIGHTNESS}},
           "components": {"M": {"15": {"1": {"by_c": {"1": {"C_fluid": 2336.9, "C_replay": 2938.1}}}}}},
           "error": {"M": {"15": {"1": {"by_c": {"1": 0.2046}}}}},
           "mooncake": {"15": {"on": {"error": 0.8, "C_fluid": 170.0, "C_replay": 30.0}}}}
    f8 = tmp_path / "e8summary.json"
    mc.dump_json(e8s, f8)
    monkeypatch.setattr(e8v2, "E8_SUMMARY", f8)
    out = tmp_path / "out" / "e8v2" / "a"
    js = {j.id: j for j in e8v2.jobs()}
    guard = {"certificate": {"held": True, "available": True}, "certificate_case": "W(a)",
             "envelope": {"ok": True, "max_excess_usd": -1.0}, "aborted": False, "project": True, "s_fb_all": True,
             "t0g_bound_all": True, "projected_slots": 11, "projection": {"K0": 0}}
    jid = e8v2.pair_id("M", 15, 1)
    runs = {"Sublet": _x(1496.9, 2000.0, guard), "A9": _x(1493.6, 2100.0), "BL1-BO": _x(1689.1, 2050.0),
            "BL5-cur": _x(1571.7, 2200.0), "A6": _x(2336.9, 2938.1)}
    mc.dump_json({"job": jid, "status": "ok"}, mc.record_path(out, jid))
    mc.dump_json({"kind": "pair", "tier": "M", "win": 15, "c": 1, "runs": runs, "errors": []},
                 e8v2.run_path(out, "pairs", jid))
    mid = e8v2.mooncake_id(15, "on")
    mc.dump_json({"job": mid, "status": "ok"}, mc.record_path(out, mid))
    mc.dump_json({"kind": "mooncake", "win": 15, "prefix": "on", "runs": {t: _x(100.0 + i, 20.0 + i)
                                                                          for i, t in enumerate(sv.TAGS4)},
                  "errors": []}, e8v2.run_path(out, "mooncake", mid))
    s = e8v2.summary(out)
    cell = s["cells"]["M"]["15"]["1"]
    assert set(cell) == {"Sublet", "A9", "BL1-BO", "BL5-cur", "A6_identity"}
    assert cell["Sublet"]["guard"]["projected_slots"] == 11
    assert s["checks"]["E8v2-0"]["status"] == "pass" and s["reused_a6"]["M"]["15"]["1"]["error"] == 0.2046
    assert s["checks"]["E8v2-1"]["status"] == "missing" and s["checks"]["E8v2-4"]["n_runs"] == 1
    runs["A6"] = _x(2336.9, 2938.2)
    mc.dump_json({"kind": "pair", "tier": "M", "win": 15, "c": 1, "runs": runs, "errors": []},
                 e8v2.run_path(out, "pairs", jid))
    s = e8v2.summary(out)
    assert s["checks"]["E8v2-0"]["status"] == "fail"
    runs["A9"]["e8_1"]["pass"] = False
    mc.dump_json({"kind": "pair", "tier": "M", "win": 15, "c": 1, "runs": runs, "errors": []},
                 e8v2.run_path(out, "pairs", jid))
    s = e8v2.summary(out)
    assert s["checks"]["E8v2-1"]["status"] == "fail" and s["checks"]["E8v2-1"]["failures"] == [f"{jid}:A9"]
    a = sa.analyse_e8v2(json.loads((out / "summary.json").read_text()))
    e = a["cells"]["M"]["15"]["1"]
    assert e["rank_fluid"] == ["A9", "Sublet", "BL5-cur", "BL1-BO"]
    assert e["rank_replay"] == ["Sublet", "BL1-BO", "A9", "BL5-cur"]
    assert e["rank_replay_with_a6"] == e["rank_replay"] + ["A6"] and e["same_order_with_a6"] is False
    assert e["same_order"] is False and e["sublet_rank_fluid"] == 2 and e["sublet_rank_replay"] == 1
    assert e["margin_fluid"]["best"] == "BL5-cur" and e["margin_fluid"]["usd"] == pytest.approx(1571.7 - 1496.9)
    assert e["margin_replay"]["usd"] == pytest.approx(50.0) and e["E"]["A6"] == 0.2046
    agg = a["by_tier_window"]["M"]["15"]
    assert agg["n"] == 1 and agg["sublet_first_replay"] == 1 and agg["sublet_beats_pair_fluid"] == 1
    mo = a["mooncake"]["15"]["on"]
    assert mo["rank_replay"][0] == "Sublet" and mo["E"]["A6"] == 0.8
    h = a["headline"]
    r = h["E_median_range"]["Sublet"]
    assert r["lo"] == r["hi"] == pytest.approx((2000.0 - 1496.9) / 2000.0) and r["lo_cell"] == "M:15"
    assert r["n_cells"] == 1 and h["E_median_range"]["A6"]["lo"] == 0.2046
    assert h["cells"] == {"n_alignments": 36, "n": 1, "same_order": 0, "sublet_first_fluid": 0,
                          "sublet_first_replay": 1, "sublet_beats_pair_fluid": 1, "sublet_beats_pair_replay": 1}
    assert h["cells_reordered"] == ["M:15:1"]
    assert h["mooncake"]["on"]["n"] == 1 and h["mooncake"]["on"]["sublet_first_replay"] == 1
    assert sa.analyse_e8v2(None) == {"note": "no e8v2/a/summary.json"}
    # E8's runs of another scale (a reduced run) are no reference and are not reused
    e8s["meta"]["grid"]["horizon_min"] = 360
    mc.dump_json(e8s, f8)
    s = e8v2.summary(out)
    assert s["checks"]["E8v2-0"]["status"] == "missing" and s["checks"]["E8v2-0"]["same_scale"] is False
    assert s["reused_a6"]["M"]["15"]["1"]["C_fluid"] is None


def test_run_script_parses():
    assert subprocess.run(["bash", "-n", str(RUN)]).returncode == 0
    assert os.access(RUN, os.X_OK)


@pytest.mark.needs_raw
@pytest.mark.needs_a12
@pytest.mark.slow
def test_reduced_pair_job_through_the_runner(tmp_path, monkeypatch):
    monkeypatch.setenv(e8v2.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_ROOT", str(tmp_path))
    monkeypatch.setattr(sv, "_GATE", {})
    out = tmp_path / "out" / "e8v2" / "a"
    js = {j.id: j for j in e8v2.jobs()}
    for jid in ("e8v2:requests", e8v2.pair_id("M", 60, 1)):
        rec = mc.run_job("e8v2", js[jid], lambda o, j=js[jid]: e8v2.run(j, o, out), out, resume=False)
        assert rec["status"] == "ok" and rec["n_errors"] == 0, rec.get("error")
    f = json.loads(e8v2.run_path(out, "pairs", e8v2.pair_id("M", 60, 1)).read_text())
    assert set(f["runs"]) == {"Sublet", "A9", "BL1-BO", "BL5-cur", "A6"} and f["horizon_min"] == 360
    for t, x in f["runs"].items():
        assert x["e8_1"]["pass"] and x["e8_2"]["pass"] and x["e8_3"]["pass"], t
        assert x["C_fluid"] == pytest.approx(x["entry"]["ALG"], rel=1e-12) and x["entry"]["status"] == "ok"
    assert f["runs"]["Sublet"]["entry"]["a8"]["allowance"] == "lb"
