"""Tests of S1 v2 and unit B4's shared layer: sublet/experiments/s1v2.py, run_s1v2.sh and the S1 v2 rules of
ms7_sens_analysis.py (design/ms7/plan.md X3, D6; design/ms7/feasibility/sens.md §2 A, §3 items 1, 5, 7; change C56).

Quick (no raw data):
- the job lists: 228 sweep jobs (57 points x weeks 301-304) and 22 w0 jobs (the 8 load-scenario and 3 fee points x
  weeks 301-302), every one a pool job at policy seed 0 with its tags (the four, BL4 in w0) and its modes (L-tr, the
  five stress modes in w0), a limit of at least 1,800 s and three times its estimate; the reduced lists only on the
  development week 101 with a 2-hour horizon; COPY_PARTS['s1v2'];
- the points: S1's 50 points but buf999 with S1's own builders, the mu row through e7_spec's mu, kappa of M alone,
  the fee targets 8 and 16; the rows (kappa_M beside kappa_L); the reused points and NOT_RUN;
- the specs: the default point under L-tr and every stress mode is ms5b_common.week_spec's spec, and buf999 is the
  confirmation's L-b999 spec (so its runs can be read from part second);
- the tags (ms5b_common's and BL3-2) and the registration gate on synthetic records (refusals, the recorded and not
  enforced reduced gate, the enforced full gate) and on a synthetic registration (its line
  'ms7_sens_analysis_sha256: <64 hex>' only); every full job of s1v2, e5v2, e8v2 and e9v2 raising before it builds
  anything while the gate refuses;
- S1v2-0 on synthetic run files against a synthetic part main (pass, a changed r0, a changed hash, missing), the
  reused block, S1v2-1's rule, the guard and clean checks on hand-made rows;
- the analysis's S1 v2 rules on a synthetic summary (savings, Delta against the pair, weeks_hold with a loss, flips,
  rows, W0's ordering, the headline blocks), the seed spread's rule, its determinism and its provenance (its sha256
  against the registration's line, the inputs' gates, registered_full_inputs);
- run_s1v2.sh with a fake driver: the gate refusal (exit 2), the two passes over the parts with the limits, S1V2_ONLY,
  and bash -n.
With the confirmation's outputs (needs_ms5b_out): the seed spread on parts main and seeds is the feasibility study's
(§1.2: Sublet 0, BL5-cur 0.0079, BL1 0.0096).
With the a12 outputs (needs_a12, slow): the default point at week 301 builds main's instance (its manifest's hash) and
S1's points at alignment 1 build S1's instances (out/ms5spec/s1_rows_build.json); run_s1v2.sh --reduced under a
scratch MS3_ROOT for the default and fee16 sweep jobs and fee16's w0 job, every job ok, both summaries with
meta.reduced true and the analysis on them.
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

from fixtures import SIM

from sublet.experiments import ms3_common as mc
from sublet.experiments import ms4_common as m4
from sublet.experiments import ms5b_common as m5
from sublet.experiments import ms7_sens_analysis as sa
from sublet.experiments import s1
from sublet.experiments import s1v2 as sv

RUN = SIM / "sublet" / "experiments" / "run_s1v2.sh"
MS5SPEC = SIM / "out" / "ms5spec"
NEW_POINTS = {"mu0.2", "mu0.5", "mu2", "kappaM05", "kappaM2", "fee8", "fee16"}


@pytest.fixture()
def full(monkeypatch):
    monkeypatch.delenv(sv.REDUCED_ENV, raising=False)
    monkeypatch.delenv("S1V2_PART", raising=False)


# ---------------------------------------------------------------- job lists
def test_job_lists(full):
    js = sv.jobs_all()
    mc.check_jobs(js)
    sweep = [j for j in js if j.params["part"] == "sweep"]
    w0 = [j for j in js if j.params["part"] == "w0"]
    assert len(sweep) == 57 * 4 and len(w0) == 11 * 2
    assert {(j.params["point"], j.params["c"]) for j in sweep} == {(p, c) for p in sv.POINT_NAMES for c in sv.WEEKS}
    assert {(j.params["point"], j.params["c"]) for j in w0} == {(p, c) for p in sv.W0_POINTS for c in (301, 302)}
    for j in js:
        p = j.params
        assert j.kind == "pool" and p["policy_seeds"] == [0] and p["horizon_min"] == m4.WEEK_MIN
        assert mc.parse_job_id(j.id)[:2] == ("s1v2", p["part"])
        assert p["limit_s"] >= 1800 and p["limit_s"] >= 3 * j.est_s - 1
        if p["part"] == "sweep":
            assert p["tags"] == ["Sublet", "A9", "BL1-BO", "BL5-cur"] and p["modes"] == ["L-tr"]
        else:
            assert p["tags"] == ["Sublet", "A9", "BL1-BO", "BL5-cur", "BL4"] and p["modes"] == list(m5.stress_modes())
        assert p["mu"] == sv.POINTS[p["point"]].mu
    assert sweep[0].params["point"] == "slow1" and sweep[0].est_s >= 2000.0      # longest first
    assert len(sv.expected_runs(sweep[0])) == 4 and len(sv.expected_runs(w0[0])) == 25
    assert sv.PARTS == mc.COPY_PARTS["s1v2"] == ("sweep", "w0")
    assert [l.split()[2] for l in _limits_lines(js)] == [j.id for j in js]


def _limits_lines(js):
    return [f"{j.kind} {int(j.params['limit_s'])} {j.id}" for j in js]


def test_reduced_lists(monkeypatch):
    monkeypatch.setenv(sv.REDUCED_ENV, "1")
    js = sv.jobs_all()
    assert len(js) == 57 + 11
    assert {j.params["c"] for j in js} == {101} and all(j.params["horizon_min"] == 120 for j in js)
    assert not any(j.params["c"] in sv.WEEKS for j in js)


def test_parts_env(monkeypatch, full):
    monkeypatch.setenv("S1V2_PART", "w0")
    assert {j.params["part"] for j in sv.jobs()} == {"w0"}
    monkeypatch.setenv("S1V2_PART", "q28")
    with pytest.raises(ValueError):
        sv.parts()


# ---------------------------------------------------------------- points and rows
def test_points_and_rows():
    assert sv.POINT_NAMES[0] == "default" and len(sv.POINTS) == 57
    assert set(sv.POINTS) == (set(s1.POINTS) - {"buf999"}) | NEW_POINTS
    for n, p in s1.POINTS.items():
        if n != "buf999":
            assert sv.POINTS[n].build is p.build and sv.POINTS[n].row == p.row and sv.POINTS[n].mu == 1.0
    assert {n: sv.POINTS[n].mu for n in ("mu0.2", "mu0.5", "mu2")} == {"mu0.2": 0.2, "mu0.5": 0.5, "mu2": 2.0}
    ref = types.SimpleNamespace(config={"llms": [{"id": "S", "kappa_mult": 1.0}, {"id": "M", "kappa_mult": 1.5},
                                                 {"id": "L"}]})
    assert sv.POINTS["kappaM05"].build(ref) == {"llms.1.kappa_mult": 0.75}
    assert sv.POINTS["kappaM2"].build(ref) == {"llms.1.kappa_mult": 3.0}
    assert sv.POINTS["mu2"].build(ref) == {}
    rows = list(sv.ROWS)
    assert rows.index("kappa_M") == rows.index("kappa_L") + 1 and sv.ROWS["kappa_M"].gamma is True
    assert sv.ROWS_ORDER[-2:] == ("q28_rf", "q28_vr")
    assert sv.W0_POINTS == tuple(f"scen_{s}" for s, _ in s1.SCENARIOS) + ("fee4", "fee8", "fee16")
    assert set(sv.REUSED) == {"buf999", "q28_rf", "q28_vr"}
    assert {x["row"] for x in sv.NOT_RUN} >= {"buf999", "q28_rf", "q28_vr", "a uniform kappa multiplier"}


def test_fee_targets(monkeypatch):
    from sublet import calib
    got = []
    monkeypatch.setattr(calib, "beta_for_rho", lambda ref, t: got.append(t) or {"S": t})
    ref = types.SimpleNamespace(config={})
    assert sv.POINTS["fee8"].build(ref) == {"costs.beta_jl_usd": {"S": 8.0}}
    assert sv.POINTS["fee16"].build(ref) == {"costs.beta_jl_usd": {"S": 16.0}}
    assert got == [8.0, 16.0]


def test_specs_are_the_confirmations():
    """The default point's spec is ms5b_common.week_spec's under L-tr and each stress mode; buf999's spec under L-tr is
    the confirmation's L-b999 spec; a mu point sets mu through e7_spec's argument."""
    params = m5.sublet_v2_params()
    for mode in ("L-tr",) + m5.stress_modes():
        a = sv.point_spec("A8P", params, {}, mode=mode, c=301, seeds=(0,), name="x")
        b = m5.week_spec("A8P", params, mode=mode, c=301, seeds=(0,), name="x")
        assert a == b, mode
    a = sv.point_spec("BL0a", {}, sv.POINTS["default"].build(None) | m5.B999_OVERRIDES, c=302, name="y")
    assert a == m5.week_spec("BL0a", {}, mode=m5.B999_MODE, c=302, name="y")
    s = sv.point_spec("BL1", {}, {}, mu=0.5, c=301)
    assert s["overrides"]["stranding.mu_over_beta_tilde"] == 0.5


# ---------------------------------------------------------------- tags and the gate
def test_tags():
    assert sv.TAGS4 == ("Sublet", "A9", "BL1-BO", "BL5-cur") and sv.H1_PAIR == ("BL1-BO", "BL5-cur")
    assert sv.tag_id("Sublet") == "A8P" and sv.tag_params("Sublet", object()) == m5.sublet_v2_params()
    assert sv.tag_id("BL3-2") == "BL3" and sv.tag_params("BL3-2") == {} and sv.tag_params("BL3-0") == {"n_extra": 0}
    t = sv.tag_table(["BL3-2", "Sublet"])
    assert list(t) == ["BL3-2", "Sublet"] and t["BL3-2"]["policy_id"] == "BL3" and t["Sublet"]["policy_id"] == "A8P"
    assert sv.a9_family("A9") and sv.a9_family("Sublet") and not sv.a9_family("BL4")


def _rec(**kw):
    base = {"head": "h", "registration_at_head": True, "registration_sha256": "r", "analysis_sha256_disk": "a" * 64,
            "analysis_sha256_head": "a" * 64, "analysis_sha256_registered": "a" * 64, "dirty_paths": []}
    return {**base, **kw}


def test_registration_gate(monkeypatch):
    assert sv.check_registration(_rec())[0] is True
    for bad, word in ((dict(registration_at_head=False, analysis_sha256_registered=None), "does not exist"),
                      (dict(analysis_sha256_registered=None), "records no line 'ms7_sens_analysis_sha256"),
                      (dict(analysis_sha256_head="b" * 64), "analysis_sha256_head bbbbbbbbbbbb differs"),
                      (dict(analysis_sha256_disk="b" * 64), "analysis_sha256_disk bbbbbbbbbbbb differs"),
                      (dict(dirty_paths=[" M x"]), "dirty"), (dict(dirty_paths=None), "cannot tell")):
        ok, why, _ = sv.check_registration(_rec(**bad))
        assert not ok and word in why, bad
    monkeypatch.setattr(sv, "registration_record", lambda: _rec(registration_at_head=False))
    monkeypatch.setattr(sv, "_GATE", {})
    g = sv.gate(True)
    assert g["ok"] is False and g["enforced"] is False and "not enforced" in g["note"]
    with pytest.raises(RuntimeError, match="does not exist at HEAD"):
        sv.gate(False)
    assert sv.gate_state(False)["enforced"] is True
    assert sv.check_start("s1v2", False) == 1 and sv.check_start("s1v2", True) == 0


def test_registration_record_reads_its_line(monkeypatch):
    """The registration's line 'ms7_sens_analysis_sha256: <64 hex>' (and no other 64-hex string) is the registered
    sha256; another unit's line does not count."""
    sha = hashlib.sha256(sv.ANALYSIS_FILE.read_bytes()).hexdigest()
    files = {sv.REGISTRATION: f"# MS7 registration\n\ne7c_analysis_sha256: {'1' * 64}\nms7_sens_analysis_sha256: "
                              f"{sha}\n".encode(), sv.ANALYSIS_REL: sv.ANALYSIS_FILE.read_bytes()}
    monkeypatch.setattr(m5, "file_at", lambda rev, rel: files.get(rel))
    monkeypatch.setattr(m5, "dirty_paths", lambda: [])
    monkeypatch.setattr(m5, "head_commit", lambda: "abc")
    rec = sv.registration_record()
    assert rec["analysis_sha256_registered"] == sha == rec["analysis_sha256_disk"] == rec["analysis_sha256_head"]
    assert sv.check_registration(rec)[0] is True
    for text in (f"| ms7_sens_analysis.py | {sha} |\n", f"e7c_analysis_sha256: {sha}\n",
                 f"ms7_sens_analysis_sha256: {sha[:-1]}\n"):
        files[sv.REGISTRATION] = text.encode()
        rec = sv.registration_record()
        assert rec["analysis_sha256_registered"] is None and sv.check_registration(rec)[0] is False, text
    files[sv.REGISTRATION] = f"ms7_sens_analysis_sha256: {'0' * 64}\n".encode()
    ok, why, _ = sv.check_registration(sv.registration_record())
    assert not ok and "differs from the registration's 000000000000" in why
    files.pop(sv.REGISTRATION)
    ok, why, _ = sv.check_registration(sv.registration_record())
    assert not ok and "does not exist at HEAD" in why


def test_full_jobs_refuse_without_registration(monkeypatch, tmp_path):
    """Every full job of the four drivers raises before it builds anything while the gate refuses (D6); the gate's
    regex is the analysis's (the analysis records the same line)."""
    from sublet.experiments import e5v2, e8v2, e9v2
    for env in (sv.REDUCED_ENV, e5v2.REDUCED_ENV, e8v2.REDUCED_ENV, e9v2.REDUCED_ENV, "S1V2_PART"):
        monkeypatch.delenv(env, raising=False)
    monkeypatch.setattr(sv, "registration_record", lambda: _rec(registration_at_head=False,
                                                                analysis_sha256_registered=None))
    monkeypatch.setattr(sv, "_GATE", {})
    firsts = {"s1v2:sweep": sv.jobs(["sweep"])[0], "s1v2:w0": sv.jobs(["w0"])[0], "e5v2": e5v2.jobs()[0],
              "e5v2:mu": [j for j in e5v2.jobs() if j.params["kind"] == "mu"][0]}
    firsts.update({f"e8v2:{k}": next(j for j in e8v2.jobs() if j.params["kind"] == k)
                   for k in ("requests", "pair", "mooncake")})
    firsts.update({"e9v2:run": e9v2.jobs()[0], "e9v2:split": e9v2.jobs()[-1]})
    mods = {"s1v2": sv, "e5v2": e5v2, "e8v2": e8v2, "e9v2": e9v2}
    for name, j in firsts.items():
        with pytest.raises(RuntimeError, match="does not start"):
            mods[name.split(":")[0]].run(j, None, tmp_path)
        assert not any(tmp_path.iterdir()), name
    assert sa.REG_SHA_RE.pattern == sv.REG_SHA_RE.pattern and sa.REGISTRATION == sv.REGISTRATION


def test_analysis_records_registration(tmp_path, monkeypatch):
    """The analysis's meta: its sha256 beside the registration's line, the inputs' gates, and registered_full_inputs
    true only for a matching sha256 and full, gated inputs."""
    monkeypatch.setattr(mc, "git_revision", lambda: "rev")
    base = {"Sublet": {"301": 0.5}, "A9": {"301": 0.49}, "BL1-BO": {"301": 0.6}, "BL5-cur": {"301": 0.58}}
    gate = {"kind": sv.GATE_KIND, "ok": True, "enforced": True}
    sweep = _summary({"default": base})
    sweep["meta"].update(reduced=False, gate=gate, git_revision="g")
    w0 = {"meta": {"grids": {"weeks": [301]}, "reduced": False, "gate": gate, "git_revision": "g"}, "W0": {},
          "reduced_default_W0": {}}
    root, repo = tmp_path / "root", tmp_path / "repo"
    for part, s in (("sweep", sweep), ("w0", w0)):
        (root / "out" / "s1v2" / part).mkdir(parents=True)
        mc.dump_json(s, root / "out" / "s1v2" / part / "summary.json")
    sha = hashlib.sha256(Path(sa.__file__).read_bytes()).hexdigest()
    (repo / "design" / "ms7").mkdir(parents=True)
    reg = repo / sv.REGISTRATION
    reg.write_text(f"e7c_analysis_sha256: {'1' * 64}\nms7_sens_analysis_sha256: {sha}\n")
    m = sa.run_analysis(["s1v2"], root, repo)["s1v2"]["meta"]
    assert m["analysis_sha256"] == sha and m["registration"]["matches"] is True and m["registered_full_inputs"] is True
    assert [x["gate_ok"] for x in m["input_records"]] == [True, True] and m["reduced"] is False
    reg.write_text(f"ms7_sens_analysis_sha256: {'0' * 64}\n")
    m = sa.run_analysis(["s1v2"], root, repo)["s1v2"]["meta"]
    assert m["registration"]["matches"] is False and m["registered_full_inputs"] is False
    reg.write_text(f"ms7_sens_analysis_sha256: {sha}\n")
    w0["meta"]["gate"] = {"kind": sv.GATE_KIND, "ok": False, "enforced": False}
    w0["meta"]["reduced"] = True
    mc.dump_json(w0, root / "out" / "s1v2" / "w0" / "summary.json")
    m = sa.run_analysis(["s1v2"], root, repo)["s1v2"]["meta"]
    assert m["registration"]["matches"] is True and m["registered_full_inputs"] is False and m["reduced"] is True
    assert "matches True; registered full inputs False" in (root / "out" / "s1v2" / "analysis.md").read_text()
    reg.unlink()
    a = sa.run_analysis(["s1v2"], root, repo, conf_dir=tmp_path / "noconf")["s1v2"]
    assert a["meta"]["registration"] == {"path": sv.REGISTRATION, "exists": False, "registered_sha256": None,
                                         "analysis_sha256": sha, "matches": False}
    assert a["seed_spread"] == {"note": "the confirmation's main or seeds summary is missing"}
    assert a["meta"]["confirmation_inputs"] == {"out/sublet_v2/main/summary.json": None,
                                                "out/sublet_v2/seeds/summary.json": None}


def test_seed_spread_rule():
    main = {"table": {"Sublet": {"L-tr": {"301": {"0": 0.5}, "302": {"0": 0.6}}},
                      "BL1": {"L-tr": {"301": {"0": 0.7}, "302": {"0": 0.8}}, "L-eg": {"301": {"0": 0.9}}}}}
    seeds = {"table": {"Sublet": {"L-tr": {"301": {"1": 0.5, "2": 0.5}, "302": {"1": 0.6, "2": None}}},
                       "BL1": {"L-tr": {"301": {"1": 0.71, "2": 0.68}, "302": {"1": 0.8, "2": 0.8}},
                               "L-eg": {"301": {"1": 0.93}, "302": {"1": 1.0}}}}}
    s = sa.seed_spread(main, seeds)
    assert s["by_tag"]["Sublet"] == {"max_abs_diff": 0.0, "at": "L-tr:301:1", "n_pairs": 3, "n_missing": 1}
    b = s["by_tag"]["BL1"]
    assert b["max_abs_diff"] == pytest.approx(0.03) and b["at"] == "L-eg:301:1"
    assert b["n_pairs"] == 5 and b["n_missing"] == 1 and s["seeds"] == ["1", "2"] and s["weeks"] == ["301", "302"]
    assert "note" in sa.seed_spread(None, seeds)
    a = sa.analyse_s1v2(_summary({"default": {t: {"301": 0.5, "302": 0.5} for t in sv.TAGS4}}), None, (main, seeds))
    assert a["headline"]["seed_spread_max"]["BL1"] == pytest.approx(0.03) and "seed_spread" in a


@pytest.mark.needs_ms5b_out("sublet_v2/main/summary.json", "sublet_v2/seeds/summary.json")
def test_seed_spread_on_the_confirmation():
    """The feasibility study's seed spread (§1.2): Sublet 0, BL5-cur 0.0079, BL1 0.0096 over weeks 301-304 and the
    seven modes."""
    main = mc.read_json(sa.CONF_DIR / "main" / "summary.json")
    seeds = mc.read_json(sa.CONF_DIR / "seeds" / "summary.json")
    s = sa.seed_spread(main, seeds)["by_tag"]
    assert s["Sublet"]["max_abs_diff"] == 0.0 and s["Sublet"]["n_pairs"] == 4 * 7 * 2
    assert s["BL5-cur"]["max_abs_diff"] == pytest.approx(0.0079, abs=5e-5)
    assert s["BL1"]["max_abs_diff"] == pytest.approx(0.0096, abs=5e-5)
    assert all(x["n_missing"] == 0 for x in s.values())


# ---------------------------------------------------------------- checks on synthetic files
def _file(point, c, r0s, ih="H", facts=None):
    return {"point": point, "c": c, "instance_hash": ih, "vs_default": facts or {},
            "runs": [{"tag": t, "policy_seed": 0, "r0": v} for t, v in r0s.items()], "references": {"bl0a_usd": 1.0}}


def test_check_identity():
    r0 = {"Sublet": 0.55, "A9": 0.54, "BL1-BO": 0.6, "BL5-cur": 0.62}
    files = {f"j{c}": _file("default", c, {t: v + c / 1e4 for t, v in r0.items()}, ih=f"H{c}") for c in sv.WEEKS}
    main_s = {"table": {t: {"L-tr": {str(c): {"0": v + c / 1e4} for c in sv.WEEKS}} for t, v in r0.items()}}
    main_m = {"instance_hashes_from_outputs": {f"e7h:main:k=week:tag={t}:c={c}": {"base": f"H{c}"}
                                               for t in r0 for c in sv.WEEKS}}
    assert sv.check_identity(files, sv.WEEKS, main_s, main_m)["status"] == "pass"
    bad = copy.deepcopy(main_s)
    bad["table"]["A9"]["L-tr"]["302"]["0"] += 1e-6
    res = sv.check_identity(files, sv.WEEKS, bad, main_m)
    assert res["status"] == "fail" and res["failures"] == ["A9:c302"]
    bad_m = copy.deepcopy(main_m)
    bad_m["instance_hashes_from_outputs"]["e7h:main:k=week:tag=Sublet:c=304"]["base"] = "X"
    assert sv.check_identity(files, sv.WEEKS, main_s, bad_m)["failures"] == ["Sublet:c304"]
    assert sv.check_identity(files, sv.WEEKS, None, None)["status"] == "missing"
    part = {k: v for k, v in files.items() if k != "j303"}
    assert sv.check_identity(part, sv.WEEKS, main_s, main_m)["status"] == "missing"


def test_check_built_and_reused():
    good = {"instance_equal": False, "demand_matched": {"identical": True, "only_in_point": [], "only_in_default": []},
            "bl0a_equal": True, "llms_without_clients": [], "llms_fitting_no_layer_site": []}
    files = {"a": _file("mu0.5", 301, {}, facts=good), "b": _file("kappaM2", 301, {},
                                                                     facts={**good, "bl0a_equal": False})}
    assert sv.check_built(files)["status"] == "pass"            # kappa_M is a Gamma row: BL0a may change
    files["c"] = _file("fee8", 301, {}, facts={**good, "bl0a_equal": False})
    res = sv.check_built(files)
    assert res["status"] == "fail" and res["failures"][0]["point"] == "fee8"
    second = {"table": {"Sublet": {"L-b999": {"301": {"0": 0.5}}, "L-rf": {"301": {"0": 0.6}}}}}
    rb = sv.reused_block(second, (301, 302), ("Sublet", "A9"))
    assert rb["buf999"]["by_tag"]["Sublet"] == {"301": 0.5, "302": None} and rb["q28_rf"]["mode"] == "L-rf"
    assert rb["q28_vr"]["by_tag"]["A9"] == {"301": None, "302": None}


def _guard(**kw):
    g = {"held": True, "case": "W(a)", "env_ok": True, "aborted": False, "project": True, "s_fb_all": True,
         "t0g_bound_all": True, "switches": 0, "robust_slots": 0, "projected_slots": 2, "projection": {"K0": 0}}
    return {**g, **kw}


def test_guard_and_clean_checks():
    rows = [{"job": "j", "tag": "Sublet", "mode": "L-tr", "seed": 0, "status": "ok", "guard": _guard()},
            {"job": "j", "tag": "A9", "mode": "L-tr", "seed": 0, "status": "ok"}]
    assert sv.guard_check(rows)["status"] == "pass" and sv.guard_check(rows)["summary"]["projected_slots"] == 2
    for bad in (dict(held=False), dict(env_ok=False), dict(aborted=True), dict(case="unavailable")):
        r2 = copy.deepcopy(rows)
        r2[0]["guard"].update(bad)
        assert sv.guard_check(r2)["status"] == "fail", bad
    r2 = copy.deepcopy(rows)
    r2[0]["guard"].update(case="W(c)", held=False)
    assert sv.guard_check(r2)["status"] == "pass" and sv.guard_check(r2)["n_w_c"] == 1
    assert sv.guard_check([])["status"] == "missing"
    assert sv.clean_check(rows, [], [], {})["status"] == "pass"
    r3 = copy.deepcopy(rows)
    r3[1]["status"] = "invariant_failure"
    assert sv.clean_check(r3, [], [], {})["status"] == "fail"
    assert sv.clean_check(rows, [], [{"job": "x"}], {})["status"] == "missing"
    assert sv.clean_check(rows, [], [], {"x": "oom_at_3G"})["status"] == "fail"


# ---------------------------------------------------------------- the analysis's S1 v2 rules
def _summary(r0: dict, reused=None, w0=None):
    """A sweep summary in s1v2's shape: r0 {point: {tag: {week: r0}}}."""
    table = {}
    for p, by in r0.items():
        for t, x in by.items():
            for w, v in x.items():
                table.setdefault(t, {}).setdefault("L-tr", {}).setdefault(p, {})[w] = {"0": v}
    pts = {p: {"row": sv.POINTS[p].row or None, "value": sv.POINTS[p].value, "label": sv.POINTS[p].label}
           for p in r0}
    return {"meta": {"grids": {"weeks": [301, 302]}, "rows_order": list(sv.ROWS_ORDER)}, "table": table,
            "points": pts, "reused": reused or {}}


def test_analysis_s1v2_rules(tmp_path):
    base = {"Sublet": {"301": 0.5, "302": 0.5}, "A9": {"301": 0.49, "302": 0.52},
            "BL1-BO": {"301": 0.6, "302": 0.55}, "BL5-cur": {"301": 0.58, "302": 0.45}}
    flip = copy.deepcopy(base)
    flip["BL5-cur"]["302"] = None                                  # a missing run: a loss
    s = _summary({"default": base, "mu2": flip},
                 reused={"buf999": {"row": "buffer_quantile", "value": 0.999, "label": "0.999",
                                    "by_tag": {t: dict(v) for t, v in base.items()}}})
    a = sa.analyse_s1v2(s, None)
    d = a["points"]["default"]
    assert d["by_tag"]["Sublet"]["median_saving_pct"] == pytest.approx(50.0)
    assert d["vs_pair"]["by_week"]["301"]["delta"] == pytest.approx(0.08)        # min(0.6, 0.58) - 0.5
    assert d["vs_pair"]["by_week"]["302"]["delta"] == pytest.approx(-0.05)       # BL5-cur 0.45 beats Sublet
    assert d["vs_pair"]["weeks_hold"] == 1 and d["vs_pair"]["n_weeks"] == 2
    assert d["sublet_minus_a9_r0"]["by_week"]["301"] == pytest.approx(0.01)
    m = a["points"]["mu2"]["vs_pair"]
    assert m["loss_weeks"] == ["302"] and m["weeks_hold"] == 1
    assert a["points"]["buf999"]["source"] == "second" and a["points"]["buf999"]["row"] == "buffer_quantile"
    assert {f["point"] for f in a["flips"]} == {"default", "mu2", "buf999"}
    assert a["rows"]["mu"]["points"] == ["mu2"] and a["rows"]["mu"]["lo_point"] in ("default", "mu2")
    w0 = {"meta": {"grids": {"weeks": [301]}},
          "W0": {t: {"fee8": {"301": {"W0": v}}} for t, v in
                 (("Sublet", 0.8), ("A9", 0.9), ("BL1-BO", 1.1), ("BL5-cur", 1.2), ("BL4", 1.05))},
          "reused_default_W0": {t: {"301": v} for t, v in
                                (("Sublet", 0.75), ("A9", 0.7), ("BL1-BO", 1.1), ("BL5-cur", 1.2), ("BL4", 0.74))}}
    aw = sa.analyse_w0(w0)
    assert aw["points"]["fee8"]["weeks_hold"] == 1 and aw["points"]["default"]["holds"] == {"301": False}
    hw = aw["headline"]
    assert hw["points_all_weeks_hold"] == 1 and hw["points_with_failures"] == ["default"]     # BL4 0.74 < 0.75
    assert hw["sublet_W0_max"] == 0.8 and hw["sublet_W0_max_at"] == "fee8:301" and hw["sublet_W0_below_1"] == 2
    assert sa.TAGS4 == sv.TAGS4 and sa.PAIR == sv.H1_PAIR and set(sa.W0_SET) == set(sv.W0_TAGS) - {"Sublet", "A9"}
    assert sa.SPAN_PP == s1.SPAN_INFORMATIVE_PP and sa.Q28_POINTS == ("q28_rf", "q28_vr")


def test_analysis_s1v2_headline():
    """The headline over the register points (Q28's variants apart): Sublet's lowest and highest median saving with
    their points, the default's, the rows whose span exceeds 10 pp, the points and point-weeks in which the ordering
    holds, Sublet - A9, and Q28's variants by tag."""
    def by(sub, a9=0.5, b1=0.6, b5=0.62):
        return {"Sublet": {"301": sub[0], "302": sub[1]}, "A9": {"301": a9, "302": a9},
                "BL1-BO": {"301": b1, "302": b1}, "BL5-cur": {"301": b5, "302": b5}}
    s = _summary({"default": by((0.5, 0.52)), "alpha02": by((0.3, 0.32)), "alpha06": by((0.7, 0.65))},
                 reused={"q28_rf": {"row": "q28_rf", "value": "L-rf", "label": "L-rf",
                                    "by_tag": by((0.9, 0.95), a9=0.85)}})
    h = sa.analyse_s1v2(s, None)["headline"]
    assert h["register_points"] == ["alpha02", "alpha06", "default"] and h["n_points"] == 3
    assert h["Sublet"]["lo"] == pytest.approx(32.5) and h["Sublet"]["lo_point"] == "alpha06"
    assert h["Sublet"]["hi"] == pytest.approx(69.0) and h["Sublet"]["hi_point"] == "alpha02"
    assert h["Sublet"]["default"] == pytest.approx(49.0) and h["BL1-BO"]["lo"] == pytest.approx(40.0)
    assert h["rows_span_above"] == ["alpha"] and h["max_span"] == pytest.approx(36.5) and h["max_span_row"] == "alpha"
    assert h["points_all_weeks_hold"] == 2 and h["points_with_flips"] == ["alpha06"]      # 0.7, 0.65 > 0.6
    assert h["point_weeks_hold"] == 4 and h["point_weeks"] == 6
    assert h["sublet_minus_a9_r0_median"] == pytest.approx(0.01)
    assert h["q28"]["q28_rf"]["weeks_hold"] == 0 and h["q28"]["q28_rf"]["by_tag"]["A9"] == pytest.approx(15.0)


def test_analysis_is_deterministic(tmp_path, monkeypatch):
    monkeypatch.setattr(mc, "git_revision", lambda: "rev")
    base = {"Sublet": {"301": 0.5, "302": 0.5}, "A9": {"301": 0.49, "302": 0.52},
            "BL1-BO": {"301": 0.6, "302": 0.55}, "BL5-cur": {"301": 0.58, "302": 0.45}}
    d = tmp_path / "out" / "s1v2" / "sweep"
    d.mkdir(parents=True)
    mc.dump_json(_summary({"default": base}), d / "summary.json")
    sa.run_analysis(["s1v2"], tmp_path)
    a = (tmp_path / "out" / "s1v2" / "analysis.json").read_bytes()
    sa.run_analysis(["s1v2"], tmp_path)
    assert (tmp_path / "out" / "s1v2" / "analysis.json").read_bytes() == a
    j = json.loads(a)
    assert j["meta"]["git_revision"] == "rev" and j["meta"]["inputs"]["out/s1v2/w0/summary.json"] is None
    assert "no s1v2/w0/summary.json" == j["w0_note"]
    assert (tmp_path / "out" / "s1v2" / "analysis.md").is_file()


# ---------------------------------------------------------------- run_s1v2.sh with a fake driver
FAKE_DRIVER = '''
import json, os, sys, time
from sublet.experiments import ms3_common as mc

def jobs():
    part = os.environ.get("S1V2_PART", "")
    return [mc.Job(j, "pool", {"part": p, "sleep": s, "limit_s": lim})
            for j, p, s, lim in json.loads(os.environ["FAKE_JOBS"]) if not part or p == part]

def run(job, outputs, out):
    t0 = time.time()
    time.sleep(job.params["sleep"])
    with open(os.environ["FAKE_EVENTS"], "a") as f:
        f.write(f"{job.id} {t0} {time.time()}\\n")
    return {"runs": 0}

def summary(out):
    with open(os.environ["FAKE_EVENTS"], "a") as f:
        f.write(f"summary:{os.environ.get('S1V2_PART')} {time.time()} {time.time()}\\n")
    mc.dump_json({"records": len(mc.read_records(out))}, out / "summary.json")

if __name__ == "__main__":
    if "--check-start" in sys.argv:
        ok = os.environ.get("FAKE_GATE", "1") == "1"
        print(f"[s1v2] gate {'ok' if ok else 'REFUSED'}")
        sys.exit(0 if ok else 1)
    if "--limits" in sys.argv:
        for j in jobs():
            print(f"{j.kind} {j.params['limit_s']} {j.id}")
        sys.exit(0)
    sys.exit(mc.main("s1v2", jobs=jobs, run=run, summary=summary))
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
    (mod / "fake_s1v2.py").write_text(FAKE_DRIVER)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "FAKE_", "S1V2_"))}
    env.update(MS3_ROOT=str(root), MS3_WORKERS="2", MS3_POLL_S="0.2", MS3_PY=sys.executable, MS3_MODULE="fake_s1v2",
               PYTHONPATH=os.pathsep.join([str(mod), str(SIM)]), FAKE_JOBS=json.dumps(jobs),
               FAKE_EVENTS=str(tmp_path / events), **_scope_env(), **extra)
    p = subprocess.run(["bash", str(RUN)], env=env, capture_output=True, text=True, timeout=300)
    ev = {}
    f = tmp_path / events
    for line in (f.read_text().splitlines() if f.is_file() else []):
        jid, t0, t1 = line.split()
        ev[jid] = (float(t0), float(t1))
    return p, ev, root / "out" / "s1v2"


FAKE_JOBS = [["s1v2:sweep:pt=a:c=301", "sweep", 0.3, 30], ["s1v2:sweep:pt=b:c=301", "sweep", 30.0, 2],
             ["s1v2:w0:pt=a:c=301", "w0", 0.3, 30]]


def test_run_script_passes_limits_and_gate(tmp_path):
    p, ev, out = _run_fake(tmp_path / "ok", FAKE_JOBS, MS3_S1V2_TEST_GRACE_S="0")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == {"s1v2:sweep:pt=a:c=301", "s1v2:w0:pt=a:c=301", "summary:sweep", "summary:w0"}
    b = mc.read_records(out / "sweep")["s1v2:sweep:pt=b:c=301"]
    assert b["status"] == "wall_limit" and b["exit_code"] == 124 and b["timeout_limit_s"] == 2.0, b
    assert ev["s1v2:w0:pt=a:c=301"][1] <= ev["summary:sweep"][0] <= ev["summary:w0"][0]
    for part in ("sweep", "w0"):
        recs = mc.read_records(out / part)
        assert recs["s1v2:summary"]["status"] == "ok" and recs["s1v2:manifest"]["status"] == "ok", part
        log = (out / part / "run_s1v2.log").read_text()
        assert "gate ok" in log and log.rstrip().splitlines()[-1].startswith("[run_s1v2] done ")
    p, ev, out = _run_fake(tmp_path / "refused", FAKE_JOBS, events="ev2.txt", FAKE_GATE="0")
    assert p.returncode == 2 and ev == {}
    assert "refused: part sweep does not start" in (out / "sweep" / "run_s1v2.log").read_text()
    p, ev, out = _run_fake(tmp_path / "only", FAKE_JOBS, events="ev3.txt", S1V2_PART="sweep",
                           S1V2_ONLY="pt=a:")
    assert p.returncode == 0 and set(ev) == {"s1v2:sweep:pt=a:c=301", "summary:sweep"}
    assert not (out / "w0").exists()
    p, _, _ = _run_fake(tmp_path / "bad", FAKE_JOBS, events="ev4.txt", S1V2_PART="q28")
    assert p.returncode == 2 and "unknown part" in p.stderr


def test_run_script_parses():
    assert subprocess.run(["bash", "-n", str(RUN)]).returncode == 0
    assert os.access(RUN, os.X_OK)


# ---------------------------------------------------------------- with the a12 outputs
@pytest.mark.needs_a12
@pytest.mark.slow
def test_builds_are_mains_and_s1s():
    """The default point at week 301 builds part main's instance (its manifest's hash), and S1's points at alignment 1
    build the instances S1 recorded (out/ms5spec/s1_rows_build.json), through s1v2's builders."""
    main_m = mc.read_json(sv.conf_file("main", "manifest.json"))
    ref = sv.build_ref(301, m4.WEEK_MIN)[0]
    assert mc.instance_hash(ref) == \
        main_m["instance_hashes_from_outputs"]["e7h:main:k=week:tag=Sublet:c=301"]["base"]
    rows = mc.read_json(MS5SPEC / "s1_rows_build.json")
    ref1 = sv.build_ref(1, m4.WEEK_MIN)[0]
    assert mc.instance_hash(ref1) == rows["default_build"]["instance_hash"]
    for name in ("alpha03", "kappaL2", "smooth60"):
        inst = sv.build_point(name, ref1, 1, m4.WEEK_MIN)[0]
        assert mc.instance_hash(inst) == rows["points"][name]["instance"]["instance_hash"], name


@pytest.mark.needs_a12
@pytest.mark.slow
def test_run_script_reduced_end_to_end(tmp_path):
    """run_s1v2.sh --reduced on the default and fee16 sweep jobs and fee16's w0 job (S1V2_ONLY): every job ok, both
    summaries with meta.reduced true and the gate recorded, not enforced; the default's identity check 'missing' (week
    101 is no confirmation week); the analysis on the two summaries."""
    root = tmp_path / "root"
    (root / "out" / "e11").mkdir(parents=True)
    (root / "out" / "e11" / "summary.json").write_text("{}\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "S1V2_", "FAKE_"))}
    env.update(MS3_ROOT=str(root), MS3_WORKERS=os.environ.get("MS3_WORKERS", "2"), MS3_POLL_S="1",
               MS3_PY=sys.executable, S1V2_ONLY="pt=(default|fee16):", **_scope_env())
    p = subprocess.run(["bash", str(RUN), "--reduced"], env=env, capture_output=True, text=True, timeout=3600)
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-3000:]
    out = root / "out" / "s1v2"
    recs = mc.read_records(out / "sweep")
    for jid in ("s1v2:sweep:pt=default:c=101", "s1v2:sweep:pt=fee16:c=101"):
        assert recs[jid]["status"] == "ok" and recs[jid]["n_errors"] == 0, recs.get(jid)
    assert mc.read_records(out / "w0")["s1v2:w0:pt=fee16:c=101"]["status"] == "ok"
    s = json.loads((out / "sweep" / "summary.json").read_text())
    w = json.loads((out / "w0" / "summary.json").read_text())
    assert s["meta"]["reduced"] is True and s["meta"]["gate"]["enforced"] is False
    assert s["checks"]["S1v2-0"]["status"] == "missing" and s["checks"]["S1v2-2"]["n_runs"] == 2
    assert s["checks"]["S1v2-2"]["status"] in ("pass", "missing") and not s["checks"]["S1v2-2"]["n_unavailable"]
    for t in sv.TAGS4:
        assert s["table"][t]["L-tr"]["default"]["101"]["0"] is not None
    assert all(r["status"] == "ok" for r in s["runs"]) and len(s["runs"]) == 8
    assert w["W0"]["Sublet"]["fee16"]["101"]["W0"] is not None and len(w["runs"]) == 25
    a = sa.run_analysis(["s1v2"], root)["s1v2"]
    assert a["meta"]["reduced"] is True and a["points"]["default"]["vs_pair"]["n_weeks"] == 1
    assert a["w0"]["points"]["fee16"]["W0"]["BL4"]["101"] is not None
