"""Tests of E5 v2: sublet/experiments/e5v2.py, run_e5v2.sh and the E5 v2 rules of ms7_sens_analysis.py
(design/ms7/plan.md X3; design/ms7/feasibility/sens.md §2 B, §3 items 2, 5, 7; change C56).

Quick (no raw data):
- the job list: 48 cell jobs (2 menus x 6 tags x E5 config seeds 301-304) and 48 mu jobs (mu 0.2, 0.5, 2 x the four
  tags x the seeds) at policy seed 0, one week; a reused tag's cell job runs sh0.25, sh0.5 and sh1 only, with the
  trace level as its identity run at (short, 301); the others run all five levels; 228 runs; the reduced list on the
  development seed 101 with a 2-hour horizon; the tags (BL3-2 is BL3 at n_extra 2);
- the summary on synthetic run files and a synthetic part second: the cells hold this driver's runs and second's
  trace and all1 runs (source 'second'), the identity runs are left out of the cells and checked by E5v2-0 (pass, a
  changed r0, a changed instance hash), and the missing runs are listed;
- the analysis's E5 v2 rules on that summary (Delta against the pair and against every baseline, BL3-2 - BL3-0);
- run_e5v2.sh: bash -n and executable.
With the a12 outputs (needs_a12, slow): two reduced cell jobs through the runner (BL3-2 on the long menu, all five
levels; BL5-cur on the short menu, the identity run and three levels) with their records and run files.
"""
import copy
import json
import os
import subprocess

import pytest

from fixtures import SIM

from sublet.experiments import e5
from sublet.experiments import e5v2
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms7_sens_analysis as sa
from sublet.experiments import s1v2 as sv

RUN = SIM / "sublet" / "experiments" / "run_e5v2.sh"


@pytest.fixture()
def full(monkeypatch):
    monkeypatch.delenv(e5v2.REDUCED_ENV, raising=False)


def test_job_list(full):
    js = e5v2.jobs()
    mc.check_jobs(js)
    cells = [j for j in js if j.params["kind"] == "cell"]
    mus = [j for j in js if j.params["kind"] == "mu"]
    assert len(cells) == 48 and len(mus) == 48
    assert e5v2.TAGS == ("Sublet", "A9", "BL1-BO", "BL5-cur", "BL3-0", "BL3-2")
    assert e5v2.REUSED_TAGS == ("Sublet", "A9", "BL3-0", "BL5-cur") and e5v2.REUSED_LEVELS == ("trace", "all1")
    for j in cells:
        p = j.params
        assert p["c"] in (301, 302, 303, 304) and p["mu"] == 1.0 and p["horizon_min"] == e5.WEEK_MIN
        if p["tag"] in e5v2.REUSED_TAGS:
            first = (p["menu"], p["c"]) == ("short", 301)
            assert p["levels"] == (["trace"] if first else []) + ["sh0.25", "sh0.5", "sh1"], j.id
            assert p["identity_levels"] == (["trace"] if first else [])
        else:
            assert p["levels"] == list(e5.LEVELS) and p["identity_levels"] == []
    assert {(j.params["mu"], j.params["tag"]) for j in mus} == {(m, t) for m in (0.2, 0.5, 2.0) for t in sv.TAGS4}
    assert all(j.params["levels"] == ["trace"] and j.params["menu"] == "short" for j in mus)
    assert sum(len(e5v2.expected_runs(j)) for j in js) == 228
    assert sum(1 for j in js for r in e5v2.expected_runs(j) if r[-1]) == 4


def test_reduced_list(monkeypatch):
    monkeypatch.setenv(e5v2.REDUCED_ENV, "1")
    js = e5v2.jobs()
    assert len(js) == 2 * 6 + 3 * 4 and {j.params["c"] for j in js} == {101}
    assert all(j.params["horizon_min"] == 120 for j in js)


def test_bl3_2_tag():
    assert sv.tag_id("BL3-2") == "BL3" and sv.tag_params("BL3-2") == {}
    from sublet.baselines.spothedge import SpotHedgeStyle
    assert SpotHedgeStyle.PARAMS["n_extra"] == 2 and e5.TAGS["BL3-2"][:2] == ("BL3", {})


def _write_job(out, job, runs, ih="H"):
    p = job.params
    rec = {"job": job.id, "status": "ok", "runs": len(runs)}
    mc.dump_json(rec, mc.record_path(out, job.id))
    f = {"kind": p["kind"], "tag": p["tag"], "menu": p["menu"], "mu": p["mu"], "c": p["c"], "instance_hash": ih,
         "runs": runs, "errors": []}
    mc.dump_json(f, e5v2.run_path(out, job.id))


def _run(tag, level, r0, ident=False):
    return {"tag": tag, "mode": level, "policy_seed": 0, "status": "ok", "r0": r0, "ALG": r0 * 100.0,
            "identity": ident, "fallback_share_after_reclaims": 0.1}


def test_summary_and_identity(full, tmp_path, monkeypatch):
    conf = tmp_path / "conf"
    second = {"table": {t: {lv: {f"{mn}:c{c}": {"0": 0.5 + 0.01 * i} for mn in e5.MENUS for c in e5v2.WEEKS}
                            for lv in ("trace", "all1")} for i, t in enumerate(e5v2.REUSED_TAGS)}}
    man = {"instance_hashes_from_outputs": {f"e7h:second:k=e5:menu=short:tag={t}:c=301": "H"
                                            for t in e5v2.REUSED_TAGS}}
    (conf / "second").mkdir(parents=True)
    mc.dump_json(second, conf / "second" / "summary.json")
    mc.dump_json(man, conf / "second" / "manifest.json")
    monkeypatch.setattr(sv, "CONF_DIR", conf)
    monkeypatch.setattr(sv, "registration_record", lambda: {"registration_at_head": False, "dirty_paths": []})
    monkeypatch.setattr(sv, "_GATE", {})
    out = tmp_path / "out"
    js = {j.id: j for j in e5v2.jobs()}
    j1 = js[e5v2.cell_id("short", "BL5-cur", 301)]
    _write_job(out, j1, [_run("BL5-cur", "trace", 0.53, True)] + [_run("BL5-cur", lv, 0.6) for lv in
                                                                  ("sh0.25", "sh0.5", "sh1")])
    j2 = js[e5v2.cell_id("short", "BL3-2", 301)]
    _write_job(out, j2, [_run("BL3-2", lv, 0.7) for lv in e5.LEVELS])
    j3 = js[e5v2.cell_id("short", "Sublet", 301)]
    _write_job(out, j3, [_run("Sublet", "trace", 0.5, True)] + [_run("Sublet", lv, 0.55) for lv in
                                                                ("sh0.25", "sh0.5", "sh1")])
    s = e5v2.summary(out)
    c = s["cells"]
    assert c["sh0.5"]["short"]["1"]["BL5-cur"]["by_c"]["301"] == 0.6 and c["sh0.5"]["short"]["1"]["BL5-cur"][
        "source"] == "e5v2"
    assert c["trace"]["short"]["1"]["BL5-cur"]["source"] == "second"
    assert c["trace"]["short"]["1"]["BL5-cur"]["by_c"]["301"] == pytest.approx(0.53)
    assert c["all1"]["long"]["1"]["Sublet"]["by_c"]["304"] == pytest.approx(0.5)
    assert c["trace"]["short"]["1"]["BL3-2"]["by_c"] == {"301": 0.7, "302": None, "303": None, "304": None}
    e0 = s["checks"]["E5v2-0"]
    assert e0["cells"]["BL5-cur:short:trace:c301"]["rel_diff"] == 0.0
    assert e0["cells"]["Sublet:short:trace:c301"]["rel_diff"] == 0.0 and e0["status"] == "missing"   # A9, BL3-0
    assert e0["runs_absent"] == ["A9:short:trace:c301", "BL3-0:short:trace:c301"]
    assert s["checks"]["E5v2-1"]["status"] == "missing" and s["missing"]
    assert s["meta"]["gate"]["enforced"] is True and s["meta"]["gate"]["ok"] is False
    # a changed r0 or instance hash fails E5v2-0
    _write_job(out, j1, [_run("BL5-cur", "trace", 0.531, True)])
    assert e5v2.summary(out)["checks"]["E5v2-0"]["failures"] == ["BL5-cur:short:trace:c301"]
    _write_job(out, j1, [_run("BL5-cur", "trace", 0.53, True)], ih="X")
    assert e5v2.summary(out)["checks"]["E5v2-0"]["status"] == "fail"
    # the analysis on the summary
    a = sa.analyse_e5v2(json.loads((out / "summary.json").read_text()))
    sh = a["cells"]["sh0.5"]["short"]["1"]
    assert sh["vs_pair"]["by_week"]["301"]["delta"] is None                     # BL1-BO has no run: a loss
    assert sh["baselines"] == ["BL1-BO", "BL5-cur", "BL3-0", "BL3-2"]
    tr = a["cells"]["trace"]["short"]["1"]
    assert tr["by_tag"]["BL3-2"]["r0"]["301"] == 0.7 and tr["bl3_spares_r0"]["by_week"]["301"] == pytest.approx(
        0.7 - 0.52)
    assert sa.E5_BASELINES == ("BL1-BO", "BL5-cur", "BL3-0", "BL3-2")
    h = a["headline"]                       # BL1-BO has no run anywhere: every cell is a loss against the pair
    assert h["n_cells"] == 13 and h["vs_pair"]["cells_all_weeks_hold"] == 0 and h["vs_pair"]["cell_weeks_hold"] == 0
    assert h["vs_pair"]["cell_weeks"] == 52 and len(h["vs_baselines"]["cells_with_failures"]) == 13
    assert h["bl3_spares_r0_median"]["trace:short"] == pytest.approx(0.18)
    assert h["sublet_saving_hi"] == pytest.approx(50.0) and h["sublet_saving_hi_cell"] == "trace:short:1"
    assert h["sublet_saving_lo"] == pytest.approx(45.0) and h["sublet_saving_lo_cell"] == "sh0.25:short:1"


def test_run_script_parses():
    assert subprocess.run(["bash", "-n", str(RUN)]).returncode == 0
    assert os.access(RUN, os.X_OK)


@pytest.mark.needs_a12
@pytest.mark.slow
def test_reduced_cell_jobs_through_the_runner(tmp_path, monkeypatch):
    monkeypatch.setenv(e5v2.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_ROOT", str(tmp_path))
    monkeypatch.setattr(sv, "_GATE", {})
    out = tmp_path / "out" / "e5v2"
    js = {j.id: j for j in e5v2.jobs()}
    for jid, levels in ((e5v2.cell_id("long", "BL3-2", 101), list(e5.LEVELS)),
                        (e5v2.cell_id("short", "BL5-cur", 101), ["trace", "sh0.25", "sh0.5", "sh1"])):
        rec = mc.run_job("e5v2", js[jid], lambda o, j=js[jid]: e5v2.run(j, o, out), out, resume=False)
        assert rec["status"] == "ok" and rec["n_errors"] == 0, rec.get("error")
        f = json.loads(e5v2.run_path(out, jid).read_text())
        assert [r["mode"] for r in f["runs"]] == levels and f["horizon_min"] == 120
        assert f["meta"]["gate"]["enforced"] is False and f["tags"][f["tag"]]["policy_id"] == sv.tag_id(f["tag"])
        for r in f["runs"]:
            assert r["status"] == "ok" and r["r0"] == pytest.approx(r["ALG"] / r["bl0a_usd"], rel=1e-12)
        assert [r["identity"] for r in f["runs"]] == [lv == "trace" and "BL5-cur" in jid for lv in levels]
