"""Tests of E7o, the out-of-sample folds (MS7 C55; design/ms7/plan.md §3 X2, design/ms7/feasibility/oos.md §3 and §4
items 6 and 8): sublet/experiments/e7o.py, e7o_analysis.py, run_e7o.sh and ms3_common.COPY_PARTS['e7o'].

Quick (no a12 outputs):
- the job lists: per fold 16 cells x 2 arms x the 15 tags (Sublet, A9, the H1 and H2b sets, CR, A9-kstar), one job per
  (cell, arm, tag) covering the 8 modes (L-tr, L-vr, the five stress modes, L-hon) at policy seed 0, config seeds
  301-316, the 72-h horizon; the reduced list: cell 0 at development seed 101 (no seed of the design), 2 hours;
- the design: each fold's evaluation window lies on the MaaS week's own clock without a wrap and outside its
  calibration window; the spot blocks are disjoint 72-h blocks of weeks 13-25 inside the series and after the
  spot calibration window; the WildChat weeks are 16 different held-out weeks; the evaluated xi weeks are the later
  halves of the BurstGPT series, the fit weeks the earlier halves, a cell's five regions use five different weeks,
  every region meets every held-out week once over cells 0-14, and each region's fit week is of the same series as
  its evaluated week and earlier (e7o.fit_week);
- the gate: refusals without the registration, without its sha256 line, with another sha256 or on a dirty tree, and
  the pass; enforced in full runs and recorded only in reduced ones;
- source_fields and sum_sources on hand-made runs; retry_list on synthetic records;
- e7o_analysis on synthetic summaries: r0, W0, RC, OOS minus IS with its sign counts, Sublet minus the cheapest H1
  baseline with the missing-run rule, the RC statistics, the source sums, the bridge to a confirmation table, the
  confirmation's rules H1, H2 and H2b on two cells (counted, not evaluated) and on 16 (evaluated, with the
  confirmation's thresholds), the instance block, and byte-identical outputs;
- run_e7o.sh with a fake driver and a fake analysis: the gate refusal (exit 2), the pass order (pool jobs, the
  missing-run rule's rerun, the summary), the parts' folders and run logs ending with the done line, E7O_ONLY, the
  analysis after the last part, the argument checks and bash -n;
- the copy check of out/e7o/ (ms3_common.check_copy with COPY_PARTS['e7o']; the analysis records its revision) on
  a synthetic tree and a fake clone.
With the a12 outputs (needs_a12): the cell config keeps the confirmation week's draws (start minute, lender regions,
load scenarios) and resolves to itself; two reduced jobs (BL1 in both arms of cell 0, fold fwd) through e7o's
runner, with the same pinned Gamma, demand and BL0a in both arms, calib_slots only in the oos arm, every mode's
run with r0 = ALG / BL0a and its lender-source block, the gate recorded and not enforced, and the summary's tables.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from fixtures import SIM

from sublet.experiments import e7o
from sublet.experiments import e7o_analysis as ea
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms5b_common as m5

RUN = SIM / "sublet" / "experiments" / "run_e7o.sh"
TAGS_STUDY = ("Sublet", "A9", "BL1", "BL1-BO", "BL2", "BL3-0", "BL4", "BL5", "BL5-cur", "BL5-tau60", "BL1-GP", "BL1N",
              "BL5N", "CR", "A9-kstar")                     # typed from oos.md §3
MODES_STUDY = ("L-tr", "L-vr", "L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co", "L-hon")


@pytest.fixture()
def reduced(monkeypatch):
    monkeypatch.setenv(e7o.REDUCED_ENV, "1")


@pytest.fixture()
def full(monkeypatch):
    monkeypatch.delenv(e7o.REDUCED_ENV, raising=False)


# ---------------------------------------------------------------- jobs and the design
def test_job_lists(full):
    assert e7o.PARTS == mc.COPY_PARTS["e7o"] == ("fwd", "rev")
    assert e7o.TAGS == TAGS_STUDY and e7o.MODES == MODES_STUDY and len(e7o.TAGS) == 15
    for part in e7o.PARTS:
        js = e7o.jobs([part])
        assert len(js) == 16 * 2 * 15 and len({j.id for j in js}) == len(js)
        mc.check_jobs(js)
        assert {j.params["c"] for j in js} == set(range(301, 317)) and all(j.kind == "pool" for j in js)
        assert all(j.params["modes"] == list(MODES_STUDY) and j.params["policy_seeds"] == [0]
                   and j.params["horizon_min"] == 4320 and j.params["part"] == part for j in js)
        assert {(j.params["cell"], j.params["arm"], j.params["tag"]) for j in js} == \
            {(k, a, t) for k in range(16) for a in ("oos", "is") for t in TAGS_STUDY}
        assert all(j.id == e7o.cell_job_id(part, j.params["arm"], j.params["tag"], j.params["cell"]) for j in js)
    est = mc.estimate(e7o.jobs(["fwd"]))
    assert 25 * 3600 < est["single_worker_s"] < 35 * 3600          # oos.md §5: about 30 CPU-h per fold


def test_reduced_job_list(reduced):
    js = e7o.jobs()
    assert len(js) == 2 * 2 * 15 and {j.params["cell"] for j in js} == {0}
    assert {j.params["c"] for j in js} == {101} and not {j.params["c"] for j in js} & set(m5.CONF_WEEKS)
    assert all(j.params["horizon_min"] == 120 for j in js)
    assert e7o.cell(0)["c"] == 101 and e7o.cell(0, reduced=False)["c"] == 301


def test_folds_and_cells(full):
    for part, f in e7o.FOLDS.items():
        lo, hi = f["maas_calib"]
        a, b = f["maas_offset"], f["maas_offset"] + e7o.HORIZON_MIN // 5
        assert b <= e7o.MAAS_SLOTS and (b <= lo or a >= hi), part                 # own clock, no wrap, held out
        assert hi - lo == 1152 and b - a == 864
    cells = [e7o.cell(k) for k in range(16)]
    blocks = sorted((c["spot_offset"], c["spot_offset"] + e7o.SPOT_BLOCK_SLOTS) for c in cells)
    assert blocks[0][0] >= e7o.SPOT_CALIB[1] == 12 * 2016
    assert all(x[1] <= y[0] for x, y in zip(blocks, blocks[1:]))
    from sublet.traces import lenders as tl
    assert blocks[-1][1] <= min(len(tl.slack(n)) for n in tl.SPOT_L7)
    weeks = [c["wildchat_week"] for c in cells]
    assert len(set(weeks)) == 16 and min(weeks) >= 37 and max(weeks) <= 72 and weeks[0] == 37 and weeks[-1] == 72
    assert not set(map(tuple, e7o.XI_HELD)) & set(map(tuple, e7o.XI_FIT))
    assert len(e7o.XI_HELD) == 15 and len(e7o.XI_FIT) == 16
    for s, n in e7o.BURST_FULL_WEEKS:
        assert {w for x, w in e7o.XI_HELD if x == s} == set(range(n - n // 2, n))
        assert {w for x, w in e7o.XI_FIT if x == s} == set(range(n - n // 2))
    for c in cells:
        for key in ("xi_eval", "xi_fit"):
            assert len({tuple(v) for v in c[key].values()}) == 5 and list(c[key]) == list(e7o.REGIONS)
        for o in e7o.REGIONS:      # a region's C0 is fitted on the earlier half of its own evaluated series
            (s, w), (s_f, w_f) = c["xi_eval"][o], c["xi_fit"][o]
            assert s_f == s and (s_f, w_f) in e7o.XI_FIT and w_f == w - e7o.HELD_START[s] and w_f < w
    assert {e7o.fit_week(*x) for x in e7o.XI_HELD} == set(e7o.XI_FIT) - {("burstgpt_3", 7)}
    for o in e7o.REGIONS:
        assert {tuple(cells[k]["xi_eval"][o]) for k in range(15)} == set(e7o.XI_HELD)
    with pytest.raises(ValueError):
        e7o.fit_week("burstgpt_1", 0)
    with pytest.raises(ValueError):
        e7o.cell(16)


@pytest.mark.needs_a12
def test_burstgpt_weeks_inside_the_series():
    from sublet.traces import borrowers as tb
    for s, n in e7o.BURST_FULL_WEEKS:
        assert tb.series_length(s) // e7o.WEEK_MIN == n


# ---------------------------------------------------------------- the gate
def _reg(**kw):
    sha = "b" * 64
    rec = {"registration_at_head": True, "analysis_sha256_registered": sha, "analysis_sha256_head": sha,
           "analysis_sha256_disk": sha, "dirty_paths": []}
    rec.update(kw)
    return rec


def test_registration_gate(monkeypatch):
    assert e7o.check_registration(_reg())[0] is True
    for kw, msg in (({"registration_at_head": False, "analysis_sha256_registered": None}, "does not exist at HEAD"),
                    ({"analysis_sha256_registered": None}, "records no line"),
                    ({"analysis_sha256_disk": "c" * 64}, "analysis_sha256_disk"),
                    ({"analysis_sha256_head": None}, "analysis_sha256_head"),
                    ({"dirty_paths": [" M x.py"]}, "dirty"), ({"dirty_paths": None}, "cannot tell")):
        ok, why, _ = e7o.check_registration(_reg(**kw))
        assert ok is False and msg in why, (kw, why)
    text = "x\ne7o_analysis_sha256: " + "d" * 64 + "\n"
    assert e7o.REG_SHA_RE.search(text).group(1) == "d" * 64
    for red, enforced in (("1", False), ("0", True)):
        monkeypatch.setenv(e7o.REDUCED_ENV, red)
        monkeypatch.setattr(e7o, "_GATE", {})
        monkeypatch.setattr(e7o, "registration_record", lambda: _reg(registration_at_head=False,
                                                                      analysis_sha256_registered=None))
        if enforced:
            with pytest.raises(RuntimeError, match="registration"):
                e7o.gate()
        else:
            g = e7o.gate()
            assert g["ok"] is False and g["enforced"] is False and "not enforced" in g["note"]


# ---------------------------------------------------------------- run entries and the rerun
def _fake_inst():
    lenders = (SimpleNamespace(lender="a2:c00", kind="maas"), SimpleNamespace(lender="a1:H800", kind="spot"),
               SimpleNamespace(lender="prot:r0", kind="protected"))
    sites = (SimpleNamespace(lender="a2:c00", kind="layer"), SimpleNamespace(lender="a2:c00", kind="layer"),
             SimpleNamespace(lender="a1:H800", kind="layer"), SimpleNamespace(lender="prot:r0", kind="protected"))
    return SimpleNamespace(lenders=lenders, sites=sites)


def _lease(site, cause, gpus=8, start=0, end=60):
    return SimpleNamespace(site=site, end_cause=cause, gpus=gpus, start_min=start, end_min=end)


def test_source_fields_and_sums():
    res = SimpleNamespace(
        violations=[{"lender": "a2:c00", "deficit": 5.0, "deficit_attributable": 5.0},
                    {"lender": "a2:c00", "deficit": 3.0, "deficit_attributable": 0.0},
                    {"lender": "a1:H800", "deficit": 2.0}],
        leases=[_lease(0, "reclaim"), _lease(1, "violation", end=30), _lease(2, "release"), _lease(3, "horizon", 1)])
    s = e7o.source_fields(res, _fake_inst())
    assert set(s) == {"maas", "spot", "protected"}
    assert s["maas"]["violation_slots"] == 2 and s["maas"]["violation_slots_attributable"] == 1
    assert s["maas"]["deficit_gpu_slots"] == 8.0 and s["maas"]["deficit_attributable_gpu_slots"] == 5.0
    assert s["maas"]["reclaims"] == 1 and s["maas"]["violation_cuts"] == 1 and s["maas"]["leases"] == 2
    assert s["maas"]["lease_gpu_h"] == 8 * 1.0 + 8 * 0.5
    assert s["spot"]["violation_slots"] == 1 and s["spot"]["violation_slots_attributable"] == 1
    assert s["spot"]["ends"] == {"release": 1} and s["protected"]["leases"] == 1
    t = e7o.sum_sources([s, s])
    assert t["maas"]["reclaims"] == 2 and t["maas"]["ends"] == {"reclaim": 2, "violation": 2}
    assert t["spot"]["deficit_gpu_slots"] == 4.0


def test_retry_list(tmp_path, monkeypatch, full):
    out = tmp_path / "fwd"
    js = [j for j in e7o.jobs(["fwd"])][:3]
    monkeypatch.setattr(e7o, "jobs_all", lambda: js)
    mc.dump_json({"job": js[0].id, "status": "ok", "n_errors": 0}, mc.record_path(out, js[0].id))
    mc.dump_json({"runs": [{"status": "ok", "r0": 1.0}]}, e7o.run_path(out, js[0].id), compact=True)
    mc.dump_json({"job": js[1].id, "status": "error"}, mc.record_path(out, js[1].id))
    mc.dump_json({"job": js[2].id, "status": "ok", "n_errors": 0}, mc.record_path(out, js[2].id))
    mc.dump_json({"runs": [{"status": "ok", "r0": 1.0, "n_invariant_failures": 2}]}, e7o.run_path(out, js[2].id),
                 compact=True)
    lines = e7o.retry_list(out)
    assert lines == [f"pool {js[1].id}", f"pool {js[2].id}"]
    assert (out / "retry" / mc.job_file_name(js[1].id)).is_file() and not mc.record_path(out, js[1].id).is_file()
    assert (out / "runs" / "retry" / mc.job_file_name(js[2].id)).is_file()
    mc.dump_json({"job": js[1].id, "status": "error"}, mc.record_path(out, js[1].id))
    assert e7o.retry_list(out) == []                                     # once per job


# ---------------------------------------------------------------- the analysis on synthetic summaries
H1 = list(m5.H1_SET)


def _row(arm, tag, mode, cell, r0, status="ok", src=None):
    return {"arm": arm, "tag": tag, "mode": mode, "cell": cell, "seed": 0, "r0": r0, "status": status,
            "sources": src or {k: {"violation_slots": 1, "violation_slots_attributable": 0, "reclaims": 2,
                                   "violation_cuts": 0, "leases": 3, "lease_gpu_h": 1.0} for k in ("maas", "spot")}}


def _summary(part: str, n_cells: int = 2, stress: float = 0.5, h2b: bool = False) -> dict:
    """n_cells cells; r0 = base(tag) + 0.1 for oos, a stress mode L-eg at + stress (W0), L-hon at -0.2; Sublet's base
    0.8, the H1 baselines' 0.9 + 0.01 i, the H2b baselines' (with h2b) 1.0; in cell 1 BL4 is missing under L-vr in the
    oos arm."""
    rows = []
    tags = ["Sublet"] + H1 + (list(m5.H2B_SET) if h2b else [])
    for cell in range(n_cells):
        for arm in ("oos", "is"):
            for t in tags:
                base = 0.8 if t == "Sublet" else 0.9 + 0.01 * H1.index(t) if t in H1 else 1.0
                base += 0.1 if arm == "oos" else 0.0
                for m in ea.MODES:
                    r0 = base + {"L-eg": stress, "L-hon": -0.2}.get(m, 0.0) + 0.001 * cell
                    if cell == 1 and arm == "oos" and t == "BL4" and m == "L-vr":
                        rows.append(_row(arm, t, m, cell, None, status="missing"))
                        continue
                    rows.append(_row(arm, t, m, cell, r0))
    return {"meta": {"part": part, "reduced": False, "design": {"tags": tags},
                     "cells": [{"k": k, "c": 301 + k} for k in range(n_cells)]}, "runs": rows}


def test_analysis_on_synthetic_summaries(tmp_path):
    conf = {"table": {"Sublet": {"L-tr": {"301": {"0": 0.7}}}}}
    d = {"parts": {"fwd": _summary("fwd"), "rev": None}, "conf": conf, "inputs": {}}
    a = ea.analyse(d)
    assert a["folds_found"] == ["fwd"] and a["folds_missing"] == ["rev"]
    f = a["folds"]["fwd"]
    pc = f["per_cell"]["oos"]["Sublet"]["0"]
    assert pc["r0"]["L-tr"] == pytest.approx(0.9) and pc["W0"] == pytest.approx(1.4) and pc["W0_mode"] == "L-eg"
    assert pc["RC"]["L-eg"] == pytest.approx(0.7) and pc["RC"]["L-tr"] == pytest.approx(0.2)
    s = f["oos_minus_is_summary"]["Sublet"]["L-tr"]
    assert (s["n"], s["n_pos"], s["n_neg"], s["median"]) == (2, 2, 0, pytest.approx(0.1))
    assert f["oos_minus_is_summary"]["BL4"]["L-vr"]["n_missing"] == 1
    v = f["sublet_vs_h1_summary"]["oos"]["L-tr"]
    assert v["n_sublet_cheaper"] == 2 and v["median"] == pytest.approx(-0.1)
    assert f["sublet_vs_h1"]["oos"]["L-tr"]["0"]["best"] == "BL1"
    vr = f["sublet_vs_h1_summary"]["oos"]["L-vr"]
    assert vr["n_missing"] == 1 and vr["n"] == 1 and f["sublet_vs_h1"]["oos"]["L-vr"]["1"]["missing"] == ["BL4"]
    st = f["sources_total"]["is"]["BL1"]["L-tr"]
    assert st["maas"]["reclaims"] == 4 and st["n_cells_missing"] == 0
    assert f["sources_total"]["oos"]["BL4"]["L-vr"]["n_cells_missing"] == 1
    assert f["bridge"]["is"]["Sublet"]["L-tr"]["0"] == pytest.approx(0.1)
    assert f["bridge"]["is"]["Sublet"]["L-tr"]["1"] is None
    rc = f["stats_rc"]["oos"]["Sublet"]
    assert rc["L-eg"]["median"] == pytest.approx(0.7) and rc["L-vr"]["n"] == 2 and set(rc) == set(ea.RC_MODES)
    assert f["stats_rc"]["oos"]["BL4"]["L-vr"]["n_missing"] == 1
    cr = f["criteria"]["oos"]                                     # two cells: counted, not evaluated
    assert cr["H1"]["L-tr"]["wins"] == 2 and cr["H1"]["L-tr"]["holds"] is None and "not evaluated" in cr["note"]
    assert cr["H1"]["L-vr"]["n_loss_cells"] == 1 and cr["H1"]["L-vr"]["margins"]["1"]["missing"] == ["BL4"]
    assert cr["H2"]["cells_below_1"] == 0 and cr["H2b"]["cells_below_set"] == 0      # no H2b tag: losses
    p1, m1 = ea.write(a, tmp_path / "a")
    p2, m2 = ea.write(ea.analyse(d), tmp_path / "b")
    assert p1.read_bytes() == p2.read_bytes() and m1.read_bytes() == m2.read_bytes()
    assert "p-value" not in m1.read_text().replace("no p-values", "")


def test_analysis_criteria_on_sixteen_cells():
    """The confirmation's rules on 16 synthetic cells: H1 holds under L-tr (16 wins, median margin 0.1) and under L-vr
    (15 wins, one cell lost by the missing run); H2 holds in the in-sample arm (W0 0.8-0.815 < 0.85 and below the
    set) and fails in the oos arm (median W0 0.9075 > 0.85); H2b holds in both; with the stress at +0.5 H2 fails."""
    a = ea.analyse({"parts": {"fwd": _summary("fwd", 16, stress=0.0, h2b=True), "rev": None}, "conf": None,
                    "inputs": {}})
    f = a["folds"]["fwd"]
    for arm in ("oos", "is"):
        cr = f["criteria"][arm]
        assert "note" not in cr and cr["thresholds"]["n_cells"] == 16
        assert cr["H1"]["L-tr"]["wins"] == 16 and cr["H1"]["L-tr"]["median_margin"] == pytest.approx(0.1)
        assert cr["H1"]["L-tr"]["holds"] is True and cr["H2b"]["holds"] is True
        assert cr["H2b"]["cells_below_per_tag"] == {t: 16 for t in m5.H2B_SET}
    vr = f["criteria"]["oos"]["H1"]["L-vr"]
    assert (vr["wins"], vr["n_loss_cells"], vr["holds"]) == (15, 1, True)
    assert f["criteria"]["is"]["H2"]["holds"] is True and f["criteria"]["is"]["H2"]["cells_below_set"] == 16
    h2 = f["criteria"]["oos"]["H2"]
    assert h2["holds"] is False and h2["median_W0"] == pytest.approx(0.9075) and h2["cells_below_1"] == 16
    b = ea.analyse({"parts": {"fwd": _summary("fwd", 16, h2b=True)}, "conf": None, "inputs": {}})
    assert b["folds"]["fwd"]["criteria"]["is"]["H2"]["holds"] is False
    md = ea.markdown(a)
    assert "H1 (L-tr)" in md and "H2b" in md and "Median RC" in md


def test_analysis_thresholds_are_the_confirmations():
    from sublet.experiments import ms5b_analysis as ma
    assert (ea.H1_WINS, ea.H1_MARGIN, ea.H2_MEDIAN) == (ma.H1_WINS, ma.H1_MARGIN, ma.H2_MEDIAN)
    assert (ea.LOSS_MARGIN, ea.LOSS_LIMIT) == (ma.LOSS_MARGIN, ma.LOSS_LIMIT)
    assert ea.H1 == m5.H1_SET and ea.H2B == m5.H2B_SET and ea.MODES == e7o.MODES and ea.ARMS == e7o.ARMS
    assert ea.FOLDS == e7o.PARTS and ea.N_CRITERIA_CELLS == e7o.N_CELLS == len(m5.CONF_WEEKS)


def test_analysis_instances_block():
    s = _summary("fwd")
    s["instances"] = {"oos": {"k1": {"instance_hash": "h", "n_instance_hashes": 1,
                                     "references": {"bl0a_usd": 10.0},
                                     "facts": {"supply_gpus": {"maas": 8.0, "spot": 0.0, "protected": 0.0},
                                               "gamma": 2.0, "C0_from": "demand_fit",
                                               "lenders": {"a2:c00": {"kind": "maas", "b": 0.1},
                                                           "a2:c01": {"kind": "maas", "b": 0.3},
                                                           "a1:H800": {"kind": "spot", "b": None}}}}}}
    x = ea.analyse({"parts": {"fwd": s}, "conf": None, "inputs": {}})["folds"]["fwd"]["instances"]
    assert x == {"oos": {"1": {"supply_gpus": {"maas": 8.0, "spot": 0.0, "protected": 0.0}, "gamma": 2.0,
                               "C0_from": "demand_fit", "bl0a_usd": 10.0, "n_instance_hashes": 1,
                               "b_median": {"maas": pytest.approx(0.2)}, "n_lenders": {"maas": 2}}}}


def test_analysis_load_from_a_root(tmp_path):
    root = tmp_path / "root"
    mc.dump_json(_summary("rev"), root / "out" / "e7o" / "rev" / "summary.json")
    d = ea.load(root)
    assert d["parts"]["fwd"] is None and d["parts"]["rev"]["meta"]["part"] == "rev" and d["conf"] is None
    assert d["inputs"]["rev"]["sha256"] and d["inputs"]["fwd"]["sha256"] is None
    assert ea.main(["--root", str(root)]) == 0
    assert (root / "out" / "e7o" / "analysis.json").is_file() and (root / "out" / "e7o" / "analysis.md").is_file()


# ---------------------------------------------------------------- run_e7o.sh with a fake driver
FAKE_DRIVER = '''
import json, os, sys, time
from sublet.experiments import ms3_common as mc

def jobs():
    part = os.environ.get("E7O_PART", "")
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
        f.write(f"summary:{os.environ.get('E7O_PART')} {time.time()} {time.time()}\\n")
    mc.dump_json({"records": len(mc.read_records(out))}, out / "summary.json")

if __name__ == "__main__":
    if "--check-start" in sys.argv:
        ok = os.environ.get("FAKE_GATE", "1") == "1"
        print(f"[e7o] gate {'ok' if ok else 'REFUSED'}")
        sys.exit(0 if ok else 1)
    if "--retry-list" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
        mark = os.path.join(out, "retried")
        if not os.path.exists(mark):
            open(mark, "w").close()
            for j in json.loads(os.environ.get("FAKE_RETRY", "[]")):
                print(f"pool {j}")
        sys.exit(0)
    sys.exit(mc.main("e7o", jobs=jobs, run=run, summary=summary))
'''
FAKE_ANALYSIS = '''
import os, sys, time
root = sys.argv[sys.argv.index("--root") + 1]
with open(os.environ["FAKE_EVENTS"], "a") as f:
    f.write(f"analysis {time.time()} {time.time()}\\n")
open(os.path.join(root, "out", "e7o", "analysis.json"), "w").write("{}\\n")
'''


def _scope_env() -> dict:
    if shutil.which("systemd-run") is None:
        return {"MS3_SCOPE": "0"}
    r = subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0",
                        "true"], capture_output=True, timeout=60)
    return {} if r.returncode == 0 else {"MS3_SCOPE": "0"}


def _run_fake(tmp_path: Path, jobs: list, parts: str, args=(), **extra):
    root = tmp_path / "root"
    (root / "out" / "e11").mkdir(parents=True, exist_ok=True)
    (root / "out" / "e11" / "summary.json").write_text("{}\n")
    mod = tmp_path / "mod"
    mod.mkdir(exist_ok=True)
    (mod / "fake_e7o.py").write_text(FAKE_DRIVER)
    (mod / "fake_e7o_analysis.py").write_text(FAKE_ANALYSIS)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "FAKE_", "E7O_"))}
    env.update(MS3_ROOT=str(root), MS3_WORKERS="2", MS3_POLL_S="0.2", MS3_PY=sys.executable, MS3_MODULE="fake_e7o",
               E7O_ANALYSIS_MODULE="fake_e7o_analysis", PYTHONPATH=os.pathsep.join([str(mod), str(SIM)]),
               FAKE_JOBS=json.dumps(jobs), E7O_PART=parts, FAKE_EVENTS=str(tmp_path / "events.txt"), **_scope_env(),
               **extra)
    p = subprocess.run(["bash", str(RUN), *args], env=env, capture_output=True, text=True, timeout=300)
    ev: dict = {}
    f = tmp_path / "events.txt"
    for line in (f.read_text().splitlines() if f.is_file() else []):
        jid, t0, t1 = line.split()
        ev.setdefault(jid, []).append((float(t0), float(t1)))
    return p, ev, root / "out"


FAKE_JOBS = [["e7o:fwd:k=cell:arm=oos:tag=A9:cell=0", "pool", "fwd", 0.3],
             ["e7o:fwd:k=cell:arm=is:tag=A9:cell=0", "pool", "fwd", 0.3],
             ["e7o:rev:k=cell:arm=oos:tag=A9:cell=0", "pool", "rev", 0.1]]


def test_run_script_passes_retry_folders_and_analysis(tmp_path):
    p, ev, out = _run_fake(tmp_path, FAKE_JOBS, "fwd rev",
                           FAKE_RETRY=json.dumps(["e7o:fwd:k=cell:arm=is:tag=A9:cell=0"]))
    assert p.returncode == 0, p.stdout + p.stderr
    assert len(ev["e7o:fwd:k=cell:arm=is:tag=A9:cell=0"]) == 2 and len(ev["e7o:fwd:k=cell:arm=oos:tag=A9:cell=0"]) == 1
    assert ev["e7o:fwd:k=cell:arm=is:tag=A9:cell=0"][1][1] <= ev["summary:fwd"][0][0]
    assert ev["summary:fwd"][0][1] <= ev["e7o:rev:k=cell:arm=oos:tag=A9:cell=0"][0][0] <= ev["summary:rev"][0][0]
    assert ev["summary:rev"][0][1] <= ev["analysis"][0][0]
    for part in ("fwd", "rev"):
        d = out / "e7o" / part
        recs = mc.read_records(d)
        assert recs["e7o:summary"]["status"] == "ok" and recs["e7o:manifest"]["status"] == "ok", d
        log = (d / "run_e7o.log").read_text()
        assert log.rstrip().splitlines()[-1].startswith("[run_e7o] done ") and "gate ok" in log
    assert "rerun once (§4.5): 1 pool job(s)" in (out / "e7o" / "fwd" / "run_e7o.log").read_text()
    assert (out / "e7o" / "analysis.json").is_file() and "analysis written" in p.stdout


def test_run_script_refuses_and_filters(tmp_path):
    p, ev, out = _run_fake(tmp_path / "a", FAKE_JOBS, "fwd", FAKE_GATE="0")
    assert p.returncode == 2 and ev == {}
    assert "refused: part fwd does not start" in (out / "e7o" / "fwd" / "run_e7o.log").read_text()
    p, ev, out = _run_fake(tmp_path / "b", FAKE_JOBS, "fwd", E7O_ONLY="arm=oos")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == {"e7o:fwd:k=cell:arm=oos:tag=A9:cell=0", "summary:fwd", "analysis"}
    p, _, _ = _run_fake(tmp_path / "c", FAKE_JOBS, "")
    assert p.returncode == 2 and "E7O_PART must name" in p.stderr
    p, _, _ = _run_fake(tmp_path / "d", FAKE_JOBS, "main")
    assert p.returncode == 2 and "unknown part" in p.stderr
    p, _, _ = _run_fake(tmp_path / "e", FAKE_JOBS, "fwd", args=("--full",))
    assert p.returncode == 2 and "usage" in p.stderr


def _fake_part(top: Path, part: str, commit: str) -> None:
    d = top / part
    mc.dump_json({"meta": {"git_revision": commit}}, d / "manifest.json")
    mc.dump_json({"meta": {"git_revision": commit, "part": part}}, d / "summary.json")
    for jid in ("e7o:summary", "e7o:manifest"):
        mc.dump_json({"job": jid, "status": "ok", "git_revision": commit}, mc.record_path(d, jid))
    mc.dump_json({"meta": {"git_revision": commit}, "runs": []}, d / "runs" / "x.json", compact=True)
    (d / "run_e7o.log").write_text("[run_e7o] part x\n[run_e7o] done 2026-11-12T00:00:00+08:00\n")


def test_copy_check_of_the_folds(tmp_path):
    """ms3_common.check_copy('e7o'): both parts with their own run logs and records, and the analysis at the top of
    out/e7o/ with its git revision (an analysis without one fails revisions_recorded)."""
    commit = "a" * 40
    root, clone = tmp_path / "root", tmp_path / "clone"
    for p in e7o.PARTS:
        _fake_part(root / "out" / "e7o", p, commit)
    (root / "out" / "e7o" / "analysis.json").write_text(json.dumps({"git_revision": commit}) + "\n")
    shutil.copytree(root / "out" / "e7o", clone / "code" / "sim" / "out" / "e7o")
    (clone / ".git").mkdir(parents=True)
    (clone / ".git" / "HEAD").write_text(commit + "\n")
    rec = mc.check_copy("e7o", clone, root)
    assert rec["pass"] is True and rec["parts"] == ["fwd", "rev"], rec["checks"]
    (root / "out" / "e7o" / "rev" / "run_e7o.log").write_text("[run_e7o] part rev\n")
    assert mc.check_copy("e7o", clone, root, record=tmp_path / "r.json")["checks"]["run_log_done"] is False
    for top in (root, clone / "code" / "sim"):
        (top / "out" / "e7o" / "analysis.json").write_text("{}\n")
    assert mc.check_copy("e7o", clone, root, record=tmp_path / "r2.json")["checks"]["revisions_recorded"] is False


def test_run_script_parses():
    assert subprocess.run(["bash", "-n", str(RUN)]).returncode == 0
    assert os.access(RUN, os.X_OK)


# ---------------------------------------------------------------- needs_a12: the cells and the runner
@pytest.mark.needs_a12
def test_cell_config_keeps_the_confirmation_draws(full):
    from sublet.config import config_hash, load_config
    from sublet.drivers import run as drun
    from sublet.experiments import ms4_common as m4
    raw = drun.instance_config(m4.e7_spec("BL0a", {}, horizon_min=4320))
    raw["seed"] = 301
    conf = load_config(raw)
    for part in e7o.PARTS:
        for arm in e7o.ARMS:
            cfg = e7o.cell_config(part, arm, 0)
            assert cfg["seed"] == 301 and cfg["time"] == conf["time"]
            for a, b in zip(cfg["lenders"], conf["lenders"]):
                assert (a["id"], a["region"], a["load_scenario"], a["group"]) == \
                    (b["id"], b["region"], b["load_scenario"], b["group"])
                if a["kind"] == "trace":
                    assert ("calib_slots" in a) == (arm == "oos")
            assert config_hash(load_config(cfg)) == config_hash(cfg)
            assert cfg["borrowers"]["wildchat_model"] == "a4c_fit" and cfg["borrowers"]["p_o_week"] == 37
    maas = [e for e in e7o.cell_config("fwd", "oos", 0)["lenders"]
            if e["kind"] == "trace" and e["id"].startswith("a2:")]
    assert {e["offset"] for e in maas} == {1152} and {tuple(e["calib_slots"]) for e in maas} == {(0, 1152)}


@pytest.mark.needs_a12
def test_reduced_jobs_through_the_runner(tmp_path, monkeypatch):
    monkeypatch.setenv(e7o.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_ROOT", str(tmp_path))
    monkeypatch.setattr(e7o, "_GATE", {})
    out = tmp_path / "out" / "e7o" / "fwd"
    js = {j.id: j for j in e7o.jobs(["fwd"])}
    ids = [e7o.cell_job_id("fwd", arm, "BL1", 0) for arm in e7o.ARMS]
    for jid in ids:
        rec = mc.run_job("e7o", js[jid], lambda o, j=js[jid]: e7o.run(j, o, out), out, resume=False)
        assert rec["status"] == "ok" and rec["n_errors"] == 0, rec.get("error")
    files = [json.loads(e7o.run_path(out, jid).read_text()) for jid in ids]
    assert [f["arm"] for f in files] == ["oos", "is"]
    assert files[0]["pinned_gamma"]["gamma"] == files[1]["pinned_gamma"]["gamma"]
    assert files[0]["instance"]["references"]["bl0a_usd"] == files[1]["instance"]["references"]["bl0a_usd"]
    for f, arm in zip(files, e7o.ARMS):
        assert f["meta"]["gate"]["enforced"] is False and f["horizon_min"] == 120 and f["cell"]["c"] == 101
        assert [r["mode"] for r in f["runs"]] == list(e7o.MODES)
        fa = f["instance"]["facts"]
        assert fa["gamma"] == f["pinned_gamma"]["gamma"] and fa["C0_from"] == "demand_fit"
        assert all((x["calib_slots"] is not None) == (arm == "oos") for x in fa["lenders"].values())
        for r in f["runs"]:
            assert r["status"] == "ok" and r["arm"] == arm and r["fold"] == "fwd" and r["cell"] == 0
            assert r["r0"] == pytest.approx(r["ALG"] / r["bl0a_usd"], rel=1e-12)
            assert set(r["sources"]) >= {"maas", "spot", "protected"}
    s = e7o.summary_part("fwd", out)
    assert s["meta"]["reduced"] is True and s["meta"]["jobs_ok"] == 2
    assert set(s["table"]) == {"oos", "is"} and s["table"]["is"]["BL1"]["L-tr"]["k0"] is not None
    assert s["W0"]["oos"]["BL1"]["k0"] == max(s["table"]["oos"]["BL1"][m]["k0"] for m in m5.stress_modes())
    assert (out / "tables.md").is_file()
