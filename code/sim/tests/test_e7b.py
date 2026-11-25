"""Tests of MS8 unit U2's driver layer for X6, budget caps (design/ms8/plan.md D2, D4): the tags e7b_tags.py, the driver
e7b.py and run_e7b.sh, and the frozen analysis e7b_analysis.py.

Quick (no raw data):
- the tags (the seven caps of design/ms8/plan.md D2 with their inner policies and references; ms5b_common.TAGS has none
  of them);
- the job lists: part week 144 jobs and 1,488 runs (the seven caps on weeks 301-316 x the 13 modes of E7r's part eval;
  Sublet and A9 under L-tr), part sens 188 jobs and 656 runs (five points; L-tr on 301-304, the five stress modes on
  301-302; the caps, BL1 and BL1-GP at every cell; Sublet and A9 at slow1 under stress and at fee16's identity cells);
  the reduced lists (week 101, a 2-hour horizon); E7B_PART; COPY_PARTS['e7b'];
- the gate (design/ms8/registration.md at HEAD with the line 'e7b_analysis_sha256: <64 hex>', a clean tree, the
  analysis sha256 on disk and at HEAD; with a temporary registration served through ms5b_common's git helpers):
  enforced in full runs, recorded and not enforced in reduced runs, kind 'ms8_registration' in every record;
- the bound: bound_series (FB(t), B(t) policy-independent; FB(T) = BL0a; B equal to Sublet's OnlineLB series) and
  bound_fields / cap_fields on toy runs;
- the analysis on synthetic summaries (records and precedence, the identity check, excesses, W0 and W0+, margins with
  win, tie and loss counts, the inner's kept share, Sublet's certificate rows, the readings R1-R3; no p-value), its
  registration record against a temporary registration file, and the command line (exit 2 on a missing input);
- run_e7b.sh with a fake driver and a fake analysis (the part order, the analysis after part sens only, the retry, the
  refusal, E7B_ONLY, bash -n).
With the a12 outputs (needs_a12): reduced week jobs of CR-cap-B (13 modes) and Sublet, and a reduced sens job of
CR-cap-B-slot at fee16, through e7b's runner: ok records, the run file's meta with the recorded gate, the bound and cap
fields (X(T) = B(T), FB(T) = BL0a), and the part summaries.
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from fixtures import SIM, toy_config

from sublet.drivers.run import make_policy
from sublet.engine import EngineConfig, simulate
from sublet.experiments import e7b
from sublet.experiments import e7b_analysis as ea
from sublet.experiments import e7b_tags as bt
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms5b_common as m5
from sublet.experiments import ms7_baselines as m7
from sublet.instance import build_instance
from sublet.types import LenderModel

RUN = SIM / "sublet" / "experiments" / "run_e7b.sh"
SUB = {"inner": "A9", "project": True, "allowance": "lb", "kappa": None}


@pytest.fixture()
def full(monkeypatch):
    monkeypatch.delenv(e7b.REDUCED_ENV, raising=False)
    monkeypatch.delenv("E7B_PART", raising=False)


# ---------------------------------------------------------------- tags
def test_tags():
    assert bt.CAP_TAGS == ("CR-cap-B", "CR-cap-0", "CR-cap-5", "CR-cap-B-latch", "CR-cap-B-slot", "GR-cap-B",
                           "GR-cap-0")
    want = {"CR-cap-B": ("A9", "lb", "paid", "stop"), "CR-cap-0": ("A9", 0.0, "paid", "stop"),
            "CR-cap-5": ("A9", "rel:0.05", "paid", "stop"), "CR-cap-B-latch": ("A9", "lb", "paid", "latch"),
            "CR-cap-B-slot": ("A9", "lb", "slot", "stop"), "GR-cap-B": ("BL1", "lb", "paid", "stop"),
            "GR-cap-0": ("BL1", 0.0, "paid", "stop")}
    for n, (inner, X, count, ob) in want.items():
        t = bt.tag(n)
        assert t.id == "CAP" and t.params == {"inner": inner, "X": X, "count": count, "on_bind": ob}
        assert t.a9_family == (inner == "A9") and bt.INNER_TAG[n] == ("A9" if inner == "A9" else "BL1")
        assert bt.GUARD_TAG[n] == ("Sublet" if inner == "A9" else "BL1-GP")
    assert bt.B_CAPS == ("CR-cap-B", "CR-cap-B-latch", "CR-cap-B-slot", "GR-cap-B")
    assert not set(bt.CAP_TAGS) & set(m5.TAGS)
    assert bt.tag("Sublet") is m5.TAGS["Sublet"] and bt.tag_params("A9") == {}
    tt = bt.tag_table(["CR-cap-0", "BL1-GP"])
    assert tt["CR-cap-0"]["inner_tag"] == "A9" and tt["BL1-GP"]["params"] == m5.tag_params_text("BL1-GP")
    inst = build_instance(toy_config())
    for n in bt.CAP_TAGS:                                # every tag builds through make_policy
        make_policy({"policy": {"id": "CAP", "params": bt.tag_params(n, inst)}}, inst)
    assert set(ea.CAP_TAGS) == set(bt.CAP_TAGS) and ea.B_CAPS == bt.B_CAPS and ea.SENS_POINTS == e7b.SENS_POINTS
    assert ea.NEW_MODES == m7.NEW_MODES and ea.STRESS_MODES == m5.stress_modes()


# ---------------------------------------------------------------- job lists
def _runs(js) -> int:
    return sum(len(j.params["modes"]) * len(j.params["policy_seeds"]) for j in js)


def test_job_lists(full, monkeypatch):
    wk, sn = e7b.jobs(["week"]), e7b.jobs(["sens"])
    mc.check_jobs(wk + sn)
    assert len(wk) == 144 and _runs(wk) == 112 * 13 + 32
    assert {j.params["c"] for j in wk} == set(range(301, 317))
    for j in wk:
        assert j.params["horizon_min"] == m5.WEEK_MIN and j.params["policy_seeds"] == [0]
        assert j.params["modes"] == (list(m7.EVAL_MODES) if bt.is_cap(j.params["tag"]) else ["L-tr"])
        assert j.id == f"e7b:week:k=week:tag={j.params['tag']}:c={j.params['c']}" and j.kind == "pool"
    assert len(sn) == 188 and _runs(sn) == 630 + 26
    cells = {(j.params["point"], j.params["tag"], j.params["c"]): j.params["modes"] for j in sn}
    stress = list(m5.stress_modes())
    for pt in e7b.SENS_POINTS:
        for t in bt.CAP_TAGS + ("BL1", "BL1-GP"):
            for c in (301, 302):
                assert cells[(pt, t, c)] == ["L-tr"] + stress
            for c in (303, 304):
                assert cells[(pt, t, c)] == ["L-tr"]
    sub = {k: v for k, v in cells.items() if k[1] in ("Sublet", "A9")}
    assert sub == {("slow1", t, c): stress for t in ("Sublet", "A9") for c in (301, 302)} | \
        {("fee16", t, 301): ["L-tr", "L-eg"] for t in ("Sublet", "A9")} | \
        {("fee16", t, 302): ["L-eg"] for t in ("Sublet", "A9")}
    assert e7b.PARTS == mc.COPY_PARTS["e7b"] == ("week", "sens")
    monkeypatch.setenv("E7B_PART", "sens")
    assert [j.id for j in e7b.jobs()] == [j.id for j in sn]
    monkeypatch.setenv("E7B_PART", "main")
    with pytest.raises(ValueError):
        e7b.parts()


def test_reduced_lists(monkeypatch):
    monkeypatch.setenv(e7b.REDUCED_ENV, "1")
    wk, sn = e7b.jobs(["week"]), e7b.jobs(["sens"])
    assert {j.params["c"] for j in wk + sn} == {101}
    assert all(j.params["horizon_min"] == 120 for j in wk + sn)
    assert len(wk) == 9 and len(sn) == 5 * 9 + 4
    for j in sn:
        if j.params["tag"] in ("Sublet", "A9"):
            assert j.params["point"] in ("slow1", "fee16") and j.params["modes"]
        else:
            assert j.params["modes"] == ["L-tr"] + list(m5.stress_modes())


# ---------------------------------------------------------------- the gate
def _reg(**kw) -> dict:
    rec = {"head": "h" * 40, "registration": e7b.REGISTRATION, "registration_at_head": True,
           "registration_sha256": "r" * 64, "analysis_sha256_registered": "a" * 64, "analysis_sha256_head": "a" * 64,
           "analysis_sha256_disk": "a" * 64, "dirty_paths": []}
    rec.update(kw)
    return rec


def test_registration_gate(monkeypatch):
    assert e7b.check_registration(_reg())[0] is True
    for kw, frag in (({"registration_at_head": False, "analysis_sha256_registered": None}, "does not exist at HEAD"),
                     ({"dirty_paths": [" M x"]}, "dirty"), ({"dirty_paths": None}, "cannot tell"),
                     ({"analysis_sha256_registered": None}, "records no line"),
                     ({"analysis_sha256_disk": "b" * 64}, "analysis_sha256_disk"),
                     ({"analysis_sha256_head": None}, "analysis_sha256_head")):
        ok, why, _ = e7b.check_registration(_reg(**kw))
        assert not ok and frag in why, kw
    text = "# Registration\n\ne7b_analysis_sha256: " + "c" * 64 + "\ne7c_analysis_sha256: " + "d" * 64 + "\n"
    assert e7b.registered_sha256(text) == "c" * 64 and e7b.registered_sha256("no hash") is None
    # a temporary registration at HEAD, served through ms5b_common's read-only git helpers
    sha = hashlib.sha256(e7b.ANALYSIS.read_bytes()).hexdigest()
    blobs = {e7b.REGISTRATION: f"# MS8 registration\n\ne7b_analysis_sha256: {sha}\n".encode(),
             e7b.ANALYSIS_REL: e7b.ANALYSIS.read_bytes()}
    monkeypatch.setattr(m5, "file_at", lambda rev, rel: blobs.get(rel))
    monkeypatch.setattr(m5, "head_commit", lambda: "f" * 40)
    monkeypatch.setattr(m5, "dirty_paths", lambda: [])
    ok, why, rec = e7b.check_registration()
    assert ok, why
    assert rec["analysis_sha256_registered"] == rec["analysis_sha256_disk"] == rec["analysis_sha256_head"] == sha
    blobs[e7b.ANALYSIS_REL] = b"changed"
    assert e7b.check_registration()[0] is False
    # enforced in full runs, recorded in reduced runs
    monkeypatch.setattr(e7b, "registration_record", lambda: _reg(dirty_paths=[" M x"]))
    monkeypatch.setattr(e7b, "_GATE", {})
    monkeypatch.delenv(e7b.REDUCED_ENV, raising=False)
    with pytest.raises(RuntimeError, match="dirty"):
        e7b.gate()
    monkeypatch.setattr(e7b, "_GATE", {})
    monkeypatch.setenv(e7b.REDUCED_ENV, "1")
    g = e7b.gate()
    assert g["kind"] == "ms8_registration" and g["ok"] is False and g["enforced"] is False
    meta = e7b._meta_run(e7b.jobs(["week"])[0])
    assert meta["exp"] == "e7b" and meta["gate"]["kind"] == "ms8_registration" and meta["reduced"] is True
    monkeypatch.setattr(e7b, "registration_record", lambda: _reg())
    monkeypatch.setattr(e7b, "_GATE", {})
    monkeypatch.delenv(e7b.REDUCED_ENV, raising=False)
    assert e7b.gate()["ok"] is True and e7b.main(["--check-start"]) == 0


# ---------------------------------------------------------------- the bound
def test_bound_series_and_fields():
    inst = build_instance(toy_config())
    ser = e7b.bound_series(inst)
    model = LenderModel(schedule="trace", information="I1")

    def go(pid, params):
        res = simulate(inst, make_policy({"policy": {"id": pid, "params": params}}, inst), model,
                       EngineConfig(check_invariants=True), lender_seed=0, policy_seed=0)
        assert not res.invariant_failures
        return res
    bl0a = float(go("BL0a", {}).components["total"])
    assert ser["FB"][-1] == pytest.approx(bl0a, rel=1e-12) and len(ser["B"]) == inst.grid.T_slow
    sub = go("A8P", SUB)
    assert list(ser["B"]) == list(sub.metrics["policy"]["safe"]["B_curve"])
    b = e7b.bound_fields(sub, ser)
    assert b["final_excess_usd"] == pytest.approx(b["ALG_T"] - b["FB_T"] - b["B_T"]) and not b["above"]
    assert b["runtime_max_excess_usd"] <= 1e-6 and b["n_slots_above"] == 0 and len(b["series"]) == inst.grid.T_slow
    for X in ("lb", 0.0):
        res = go("CAP", {"inner": "A9", "X": X, "on_bind": "latch"})
        bb = e7b.bound_fields(res, ser)
        cf = e7b.cap_fields(res, bb)
        assert cf["fb_equal_bound"] is True and "FB_series" not in cf
        assert cf["final_excess_over_X_usd"] == pytest.approx(bb["ALG_T"] - bb["FB_T"] - cf["X_T"])
        if X == "lb":
            assert cf["X_equal_B"] is True and cf["X_T"] == bb["B_T"]
    assert e7b.cap_fields(sub, b) is None


# ---------------------------------------------------------------- the analysis on synthetic summaries
FB, BT = 100.0, 10.0
WEEKS = (301, 302)
ALL_MODES = ("L-tr",) + ea.STRESS_MODES + ("L-hon",) + ea.NEW_MODES


def _row(tag, mode, c, r0, point=None, guard=False, bound=None, cap=None, env=-1.0):
    r = {"tag": tag, "mode": mode, "c": c, "cell": str(c) if point is None else f"{point}:{c}", "seed": 0,
         "status": "ok", "r0": r0, "ALG": r0 * FB, "bl0a_usd": FB}
    if point is not None:
        r["point"] = point
    if guard:
        r["guard"] = {"B_T": BT, "held": True, "env_ok": env <= 0, "env_max_excess_usd": env, "s_fb_all": True}
    if bound is not None:
        r["bound"] = {"B_T": BT, "tol_usd": 1e-7, "runtime_max_excess_usd": bound, "runtime_max_slot": 5,
                      "n_slots_above": 3 if bound > 0 else 0, "fb_equal_bl0a": True}
    if cap is not None:
        r["cap"] = cap
    return r


CAP_OK = {"bind_slots": 2, "fb_equal_bound": True, "X_equal_B": True, "B_series_equal_bound": True}


def _ref_r0(tag, mode):
    stress = mode in ea.STRESS_MODES or mode in ea.NEW_MODES
    return {"Sublet": 0.78 if stress else 0.6, "A9": 0.9 if stress else 0.6, "BL1": 1.5 if stress else 0.7,
            "BL1-GP": 1.0 if stress else 0.7}[tag]


def _cap_r0(tag, mode, c):
    if tag == "CR-cap-0":
        return 1.0 if mode in ea.STRESS_MODES else 0.62
    if tag == "CR-cap-B" and mode == "L-eg" and c == 301:
        return 1.12                                   # above FB + B = 110 (R1)
    if tag == "CR-cap-B" and mode == "L-tr" and c == 302:
        return 0.55                                   # below Sublet's 0.6 (R3)
    return _ref_r0("A9" if tag.startswith("CR") else "BL1-GP", mode)


def _inputs(sublet_env=-1.0) -> dict:
    main = {"meta": {"git_revision": "m" * 40}, "runs": [
        _row(t, m, c, _ref_r0(t, m), guard=t in ("Sublet", "BL1-GP"), env=sublet_env)
        for t in ea.FROZEN_TAGS for m in ea.CONF_MODES for c in WEEKS]}
    ev = {"meta": {}, "runs": [_row(t, m, c, _ref_r0(t, m), guard=t in ("Sublet", "BL1-GP"))
                               for t in ea.FROZEN_TAGS for m in ("L-tr",) + ea.NEW_MODES for c in WEEKS]}
    week = {"meta": {"reduced": False}, "runs": [
        _row(t, m, c, _cap_r0(t, m, c), bound=(1.5 if _cap_r0(t, m, c) > 1.1 else -1.0), cap=CAP_OK)
        for t in ea.CAP_TAGS for m in ALL_MODES for c in WEEKS]
        + [_row(t, "L-tr", c, _ref_r0(t, "L-tr"), guard=t == "Sublet", bound=-1.0) for t in ("Sublet", "A9")
           for c in WEEKS]}
    sens = {"meta": {}, "runs": [
        _row(t, m, c, 0.7, point="fee16", bound=-1.0, guard=t == "BL1-GP")
        for t in ea.CAP_TAGS + ("BL1", "BL1-GP") for c in (301, 302, 303, 304)
        for m in (("L-tr",) + ea.STRESS_MODES if c in WEEKS else ("L-tr",))]
        + [_row("Sublet", "L-tr", 301, 0.65, point="fee16", guard=True, bound=-1.0)]}
    sweep = {"meta": {}, "runs": [_row(t, "L-tr", c, 0.65, point="fee16", guard=t == "Sublet") for t in ("Sublet", "A9")
                                  for c in (301, 302, 303, 304)]}
    w0 = {"meta": {}, "runs": [_row(t, m, c, 0.8, point="fee16", guard=t == "Sublet") for t in ("Sublet", "A9")
                               for m in ea.STRESS_MODES for c in WEEKS]}
    inp = {"week": week, "sens": sens, "main": main, "eval": ev, "sweep": sweep, "w0": w0}
    inp["sha256"] = {k: "0" * 64 for k in inp}
    inp["paths"] = {k: k for k in inp if k != "sha256"}
    return inp


def _keys(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from _keys(v)
    elif isinstance(x, list):
        for v in x:
            yield from _keys(v)


def test_analysis_on_synthetic_summaries(tmp_path):
    a = ea.analysis(_inputs(), repo=tmp_path)
    runs = {(r["part"], r["point"], r["mode"], r["week"], r["tag"]): r for r in a["runs"]}
    # precedence and the cell's B for a frozen unguarded run
    x = runs[("week", "default", "L-tr", "301", "Sublet")]
    assert x["source"] == "main" and x["final_usd"] == pytest.approx(60.0 - 110.0) and x["runtime_label"] == "series"
    x = runs[("week", "default", "L-pk", "302", "A9")]
    assert x["source"] == "eval" and x["B_from_cell"] is True and x["final_usd"] == pytest.approx(90.0 - 110.0)
    assert runs[("week", "default", "L-eg", "301", "BL1-GP")]["runtime_label"] == "envelope"
    assert runs[("week", "default", "L-eg", "301", "A9")]["runtime_label"] is None
    x = runs[("week", "default", "L-eg", "301", "CR-cap-B")]
    assert x["above"] is True and x["runtime_above"] is True and x["final_rel"] == pytest.approx(0.02)
    # identity: the week reruns and fee16's rerun equal the frozen runs
    i = a["identity"]
    assert i["holds"] is True and i["n_pairs"] == 5 and i["n_equal"] == 5
    # W0 and W0+
    w = a["W"]["week"]["default"]
    assert w["CR-cap-B"]["W0"] == {"301": 1.12, "302": 0.9} and w["Sublet"]["W0plus"] == {"301": 0.78, "302": 0.78}
    # margins: tag minus reference
    m = a["margins"]["week"]["default"]["CR-cap-B"]["Sublet"]
    assert m["r0_tr"]["deltas"] == {"301": 0.0, "302": pytest.approx(-0.05)} and m["r0_tr"]["ties"] == 1
    assert m["r0_tr"]["losses"] == 1 and m["W0"]["wins"] == 2 and m["W0"]["median"] == pytest.approx(0.23)
    assert m["r0_tr"]["missing"] == 0 and m["r0_tr"]["losses_with_missing"] == 1
    assert set(a["margins"]["week"]["default"]["GR-cap-B"]) == {"Sublet", "BL1-GP"}
    assert a["margins"]["sens"]["fee16"]["CR-cap-B"]["Sublet"]["r0_tr"]["n"] == 4
    assert a["margins"]["sens"]["fee16"]["CR-cap-B"]["Sublet"]["W0"]["n"] == 2
    # against the inner: CR-cap-0 under stress keeps none of A9's saving
    k = a["inner"]["week"]["default"]["CR-cap-0"]["stress"]
    assert k["inner"] == "A9" and k["kept_share"]["median"] == pytest.approx(0.0)
    # Sublet's rows and the readings
    assert a["sublet"]["week"]["runs"] == 2 * 13 and a["sublet"]["week"]["envelope_violations"] == 0
    r = a["readings"]
    assert r["R1"]["holds"] is True and r["R1"]["n_runs"] == 1 and r["R1"]["runs"][0]["tag"] == "CR-cap-B"
    assert r["R2"]["holds"] is True and r["R2"]["cap_median"] == 1.0 and r["R2"]["sublet_median"] == 0.78
    assert r["R3"]["by_tag"]["CR-cap-B"]["cells"] >= 1
    assert any(c["mode"] == "L-tr" and c["week"] == "302" and c["tag"] == "CR-cap-B" for c in r["R3"]["cells"])
    assert not {"p", "p_value", "wilcoxon", "sign_test", "ci", "bootstrap"} & set(_keys(a))
    # the per-run checks: week's runs all pass; sens' cap rows carry no cap block, so their checks are missing
    ck = a["checks"]
    n_week, n_cap = len(_inputs()["week"]["runs"]), len(ea.CAP_TAGS) * len(ALL_MODES) * len(WEEKS)
    assert ck["week"]["holds"] is True and ck["week"]["fb_equal_bl0a"] == {"true": n_week, "false": 0, "missing": 0}
    assert ck["week"]["cap_runs"] == n_cap and ck["week"]["cap_fb_equal_bound"]["true"] == n_cap
    assert ck["week"]["cap_X_equal_B"]["true"] == len(ea.B_CAPS) * len(ALL_MODES) * len(WEEKS)
    assert ck["sens"]["holds"] is False and ck["sens"]["cap_fb_equal_bound"]["missing"] == ck["sens"]["cap_runs"] > 0
    md = ea.to_md(a)
    assert "R1" in md and "Sublet's certificate rows" in md and "Identity with the frozen runs" in md
    assert "Per-run checks of E7b's runs" in md and "losses with missing" in md
    # a Sublet envelope violation makes R1 fail
    b = ea.analysis(_inputs(sublet_env=2.0), repo=tmp_path)
    assert b["readings"]["R1"]["holds"] is False and b["sublet"]["week"]["envelope_violations"] > 0


def test_sources_exist_and_cover_the_run_path():
    """Every file in e7b.SOURCES exists, including BL1's refusal handling, COPY_PARTS and CERT_TOL's modules."""
    base = Path(e7b.__file__).resolve().parents[2]
    assert all((base / rel).is_file() for rel in e7b.SOURCES), [r for r in e7b.SOURCES if not (base / r).is_file()]
    assert {"sublet/baselines/common.py", "sublet/experiments/ms3_common.py",
            "sublet/experiments/q44_study.py"} <= set(e7b.SOURCES)


def test_margin_stats_missing_rule():
    """A missing run is a loss for the reference: losses_with_missing = losses + missing (e7r_analysis's rule)."""
    m = ea.margin_stats({"301": -0.1, "302": None, "303": 0.2, "304": 0.0})
    assert (m["n"], m["wins"], m["ties"], m["losses"], m["missing"]) == (3, 1, 1, 1, 1)
    assert m["losses_with_missing"] == 2


def test_analysis_registration_and_cli(tmp_path):
    sha = hashlib.sha256(Path(ea.__file__).read_bytes()).hexdigest()
    assert ea.registration(sha, tmp_path) == {"path": ea.REGISTRATION, "exists": False, "registered_sha256": None,
                                              "matches": False}
    f = tmp_path / ea.REGISTRATION
    f.parent.mkdir(parents=True)
    f.write_text("# MS8 registration\n\ne7b_analysis_sha256: " + "0" * 64 + "\n")
    assert ea.registration(sha, tmp_path)["matches"] is False
    f.write_text("# MS8 registration\n\ne7b_analysis_sha256: " + sha + "\n")
    assert ea.registration(sha, tmp_path)["matches"] is True
    root = tmp_path / "root"
    assert ea.main(["--root", str(root)]) == 2                      # every input missing
    inp = _inputs()
    fs = ea.files(root)
    for k, p in fs.items():
        mc.dump_json(inp[k], p)
    fs["w0"].unlink()
    assert ea.main(["--root", str(root)]) == 2                      # one input missing
    mc.dump_json(inp["w0"], fs["w0"])
    assert ea.main(["--root", str(root)]) == 0
    out = json.loads((root / "out" / "e7b" / "analysis.json").read_text())
    assert out["meta"]["analysis_sha256"] == sha and set(out["meta"]["inputs_sha256"]) == set(fs)
    assert out["meta"]["inputs_sha256"]["main"] == hashlib.sha256(fs["main"].read_bytes()).hexdigest()
    assert (root / "out" / "e7b" / "analysis.md").is_file()


# ---------------------------------------------------------------- run_e7b.sh with a fake driver
FAKE_DRIVER = '''
import json, os, sys, time
from sublet.experiments import ms3_common as mc

def jobs():
    part = os.environ.get("E7B_PART", "")
    return [mc.Job(j, k, {"part": p, "sleep": s}) for j, k, p, s in json.loads(os.environ["FAKE_JOBS"])
            if not part or p == part]

def run(job, outputs, out):
    t0 = time.time()
    time.sleep(job.params["sleep"])
    with open(os.environ["FAKE_EVENTS"], "a") as f:
        f.write(f"{job.id} {t0} {time.time()}\\n")
    return {"runs": 0}

def summary(out):
    with open(os.environ["FAKE_EVENTS"], "a") as f:
        f.write(f"summary:{os.environ.get('E7B_PART')} {time.time()} {time.time()}\\n")
    mc.dump_json({"records": len(mc.read_records(out))}, out / "summary.json")

if __name__ == "__main__":
    if "--check-start" in sys.argv:
        ok = os.environ.get("FAKE_GATE", "1") == "1"
        print(f"[e7b] {os.environ.get('E7B_PART')}: gate {'ok' if ok else 'REFUSED'}")
        sys.exit(0 if ok else 1)
    if "--retry-list" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
        mark = os.path.join(out, "retried")
        if not os.path.exists(mark):
            open(mark, "w").close()
            for j in json.loads(os.environ.get("FAKE_RETRY", "[]")):
                print(f"pool {j}")
        sys.exit(0)
    sys.exit(mc.main("e7b", jobs=jobs, run=run, summary=summary))
'''
FAKE_ANALYSIS = '''
import os, sys, time
with open(os.environ["FAKE_EVENTS"], "a") as f:
    f.write(f"analysis:{' '.join(sys.argv[1:])} {time.time()} {time.time()}\\n")
sys.exit(int(os.environ.get("FAKE_ANALYSIS_RC", "0")))
'''
FAKE_JOBS = [["e7b:week:k=week:tag=CR-cap-B:c=101", "pool", "week", 0.3],
             ["e7b:week:k=week:tag=Sublet:c=101", "pool", "week", 0.2],
             ["e7b:sens:k=sens:pt=fee16:tag=CR-cap-0:c=101", "pool", "sens", 0.1]]


def _scope_env() -> dict:
    if shutil.which("systemd-run") is None:
        return {"MS3_SCOPE": "0"}
    r = subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0",
                        "true"], capture_output=True, timeout=60)
    return {} if r.returncode == 0 else {"MS3_SCOPE": "0"}


def _run_fake(tmp_path: Path, parts: str, events: str = "events.txt", **extra):
    root = tmp_path / "root"
    (root / "out" / "e11").mkdir(parents=True, exist_ok=True)
    (root / "out" / "e11" / "summary.json").write_text("{}\n")
    mod = tmp_path / "mod"
    mod.mkdir(exist_ok=True)
    (mod / "fake_e7b.py").write_text(FAKE_DRIVER)
    (mod / "fake_e7b_analysis.py").write_text(FAKE_ANALYSIS)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "FAKE_", "E7B_", "MS8_"))}
    env.update(MS3_ROOT=str(root), MS3_WORKERS="2", MS3_POLL_S="0.2", MS3_PY=sys.executable, MS3_MODULE="fake_e7b",
               E7B_ANALYSIS_MODULE="fake_e7b_analysis", PYTHONPATH=os.pathsep.join([str(mod), str(SIM)]),
               FAKE_JOBS=json.dumps(FAKE_JOBS), E7B_PART=parts, FAKE_EVENTS=str(tmp_path / events), **_scope_env(),
               **extra)
    p = subprocess.run(["bash", str(RUN)], env=env, capture_output=True, text=True, timeout=300)
    ev: dict = {}
    f = tmp_path / events
    for line in (f.read_text().splitlines() if f.is_file() else []):
        jid, t0, t1 = line.rsplit(" ", 2)
        ev.setdefault(jid, []).append((float(t0), float(t1)))
    return p, ev, root / "out"


def test_run_script_parts_retry_and_analysis(tmp_path):
    p, ev, out = _run_fake(tmp_path, "week sens", FAKE_RETRY=json.dumps(["e7b:week:k=week:tag=CR-cap-B:c=101"]),
                           E7B_FROZEN="/frozen/x")
    assert p.returncode == 0, p.stdout + p.stderr
    assert len(ev["e7b:week:k=week:tag=CR-cap-B:c=101"]) == 2 and len(ev["e7b:week:k=week:tag=Sublet:c=101"]) == 1
    ana = [k for k in ev if k.startswith("analysis:")]
    assert len(ana) == 1 and "--frozen /frozen/x" in ana[0] and "--root" in ana[0]
    assert ev["summary:week"][0][1] <= ev["e7b:sens:k=sens:pt=fee16:tag=CR-cap-0:c=101"][0][0]
    assert ev["summary:sens"][0][1] <= ev[ana[0]][0][0]
    for part in ("week", "sens"):
        d = out / "e7b" / part
        recs = mc.read_records(d)
        assert recs["e7b:summary"]["status"] == "ok" and recs["e7b:manifest"]["status"] == "ok", d
        log = (d / "run_e7b.log").read_text()
        assert log.rstrip().splitlines()[-1].startswith("[run_e7b] done ") and "gate ok" in log
    p, ev, out = _run_fake(tmp_path / "w", "week", events="ev_w.txt")
    assert p.returncode == 0 and not [k for k in ev if k.startswith("analysis:")]
    p, ev, out = _run_fake(tmp_path / "f", "sens", events="ev_f.txt", FAKE_ANALYSIS_RC="2")
    assert p.returncode == 1 and "e7b_analysis failed (exit 2)" in (out / "e7b" / "sens" / "run_e7b.log").read_text()


def test_run_script_refuses_and_filters(tmp_path):
    p, ev, out = _run_fake(tmp_path / "a", "week", FAKE_GATE="0")
    assert p.returncode == 2 and ev == {}
    assert "refused: part week does not start" in (out / "e7b" / "week" / "run_e7b.log").read_text()
    p, ev, out = _run_fake(tmp_path / "b", "week", E7B_ONLY="tag=Sublet:")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == {"e7b:week:k=week:tag=Sublet:c=101", "summary:week"}
    p, _, _ = _run_fake(tmp_path / "c", "", events="ev_c.txt")
    assert p.returncode == 2 and "E7B_PART must name" in p.stderr
    p, _, _ = _run_fake(tmp_path / "d", "main", events="ev_d.txt")
    assert p.returncode == 2 and "unknown part" in p.stderr


def test_run_script_parses():
    assert subprocess.run(["bash", "-n", str(RUN)]).returncode == 0
    assert os.access(RUN, os.X_OK)


# ---------------------------------------------------------------- needs_a12: reduced jobs through e7b's runner
@pytest.mark.needs_a12
def test_reduced_jobs_through_the_runner(tmp_path, monkeypatch):
    monkeypatch.setenv(e7b.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_ROOT", str(tmp_path))
    monkeypatch.setattr(e7b, "_GATE", {})
    wk = tmp_path / "out" / "e7b" / "week"
    js = {j.id: j for j in e7b.jobs_all()}
    ids = ("e7b:week:k=week:tag=CR-cap-B:c=101", "e7b:week:k=week:tag=Sublet:c=101")
    for jid in ids:
        rec = mc.run_job("e7b", js[jid], lambda o, j=js[jid]: e7b.run(j, o, wk), wk, resume=False)
        assert rec["status"] == "ok" and rec["n_errors"] == 0, rec.get("error")
    f = json.loads(e7b.run_path(wk, ids[0]).read_text())
    g = f["meta"]["gate"]
    assert f["meta"]["exp"] == "e7b" and g["kind"] == "ms8_registration" and g["enforced"] is False
    assert "confirmation" not in g and f["horizon_min"] == 120 and [r["mode"] for r in f["runs"]] == list(m7.EVAL_MODES)
    assert set(f["instances"]) == {"base", "pk"}
    for r in f["runs"]:
        assert r["status"] == "ok" and r["r0"] == pytest.approx(r["ALG"] / r["bl0a_usd"], rel=1e-12)
        b, c = r["bound"], r["cap"]
        assert b["FB_T"] == pytest.approx(r["bl0a_usd"], rel=1e-9) and len(b["series"]) == b["n_slots"] == 24
        assert b["fb_equal_bl0a"] is True
        assert c["X_equal_B"] is True and c["fb_equal_bound"] is True and c["B_series_equal_bound"] is True
        assert c["X_T"] == b["B_T"] and r["a9"] is not None
    s = json.loads(e7b.run_path(wk, ids[1]).read_text())["runs"][0]
    assert s["a8"]["B_T"] == s["bound"]["B_T"] and s["bound"]["above"] is False
    summ = e7b.summary_part("week", wk)
    assert set(summ["table"]["CR-cap-B"]) == set(m7.EVAL_MODES) and summ["meta"]["gate"]["kind"] == "ms8_registration"
    assert "101" in summ["W0"]["CR-cap-B"] and "101" in summ["W0plus"]["CR-cap-B"] and summ["meta"]["reduced"] is True
    assert (wk / "tables.md").is_file() and summ["runs"][0]["bound"].get("series") is None
    sn = tmp_path / "out" / "e7b" / "sens"
    jid = "e7b:sens:k=sens:pt=fee16:tag=CR-cap-B-slot:c=101"
    rec = mc.run_job("e7b", js[jid], lambda o, j=js[jid]: e7b.run(j, o, sn), sn, resume=False)
    assert rec["status"] == "ok" and rec["n_errors"] == 0, rec.get("error")
    f = json.loads(e7b.run_path(sn, jid).read_text())
    assert f["point"] == "fee16" and f["value"] == 16.0 and [r["mode"] for r in f["runs"]] == ["L-tr"] + \
        list(m5.stress_modes())
    assert all(r["cap"]["count"] == "slot" and r["point"] == "fee16" for r in f["runs"])
    assert all(r["bound"]["fb_equal_bl0a"] is True for r in f["runs"])
    summ = e7b.summary_part("sens", sn)
    assert "fee16:101" in summ["W0"]["CR-cap-B-slot"] and summ["meta"]["points"]["fee16"]["value"] == 16.0
