"""Tests of the S1 driver sublet/experiments/s1.py and its run script run_s1.sh (design/sim_spec_ms5.md §3, §4, §2.4,
§10 row test_s1.py, §11.1).

Quick (no raw data):
- the job list of §3.8 and §4.6: 204 s1:sweep jobs (51 points x 4 alignments) and 76 s1:q28 jobs (2 variants x 9 tags
  x 4 alignments and BL3 under the default lender x 4), all pool jobs with three policy seeds, every id parses, no two
  share a record file; S1_PART selects a part's jobs; the reduced list (MS3_S1_REDUCED=1) keeps every point, variant
  and tag at alignment 1, policy seed 0 and a 2-hour horizon; every job's limit is three times its estimate and at
  least 1,800 s (§3.9), and the time constants equal the measurement files (out/ms5spec/s1_sizing_<case>.json,
  s1_rows_build.json, q28_sizing_*.json), with §11.1's totals (28.0 h and 3.7 h of single-worker time);
- the register: the 50 points and the default in the 24 rows of §3.4 plus the mu row from E7, the rows with Gamma, the
  panels of §7.1, the scenario names of calib.scenarios(), and the not_run list equal to §3.5's;
- the rows' lo, hi and span on a synthetic summary, the default included; check S1-0 on a copy of E7's summary, its
  failure on a changed cost or hash and 'missing' without E7's runs; S1-1, S1-2, Q28-1 and Q28-2 on hand-made run
  files; violation_record on a hand-made RunResult with victims; the q28 references;
- run_s1.sh with a fake driver: the two passes over the parts, the limits of --limits (a job over its limit is stopped
  by timeout at LIMIT + grace and recorded 'wall_limit' with exit 124 and its limit), S1_ONLY, resume with
  MS3_RESUME=1, and bash -n.
With the a12 outputs (needs_a12, slow):
- point_overrides for every point at alignment 1 against the overrides recorded by out/ms5spec/s1_sizing.py and
  s1_rows_build.py, and the instance hashes against s1_rows_build.json and s1_sizing_<case>_build.json (keys as those
  files hold them; wan1g is the point scen_cold_wan_1gbps), with the demand and BL0a rule of §3.4;
- run_s1.sh --reduced under a scratch MS3_ROOT (SUBLET_S1_REDUCED_ROOT if set, else a temporary folder; MS3_WORKERS
  from the environment, default 1): by default only the six jobs of E2E_ONLY (S1_ONLY: the default point and fee4,
  Q28's Sublet under L-rf, BL2 under L-vr and BL3 under L-rf and the default lender), with every selected job ok and
  both summaries written with meta.reduced true, every check row and the others listed as missing; with
  SUBLET_S1_E2E_FULL=1 the whole reduced grid (70 jobs, about 15 min on one worker; tests/fixtures_figs_ms5's
  refresh_inputs.sh runs it too), with every job ok and the check rows S1-1..S1-3 and Q28-1..Q28-3 passing.
"""
import copy
import json
import math
import os
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

from fixtures import SIM

from sublet.experiments import e7
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms4_common as m4
from sublet.experiments import s1

REPO = SIM.parents[1]
MS5SPEC = SIM / "out" / "ms5spec"
RUN_S1 = SIM / "sublet" / "experiments" / "run_s1.sh"
E7_MAIN = SIM / "out" / "e7" / "main" / "summary.json"
# measurement 1's cases (out/ms5spec/s1_sizing_<case>[_build].json) by point
SIZING_CASE = {"default": "default", "slow1": "slow1", "layer16": "layer16", "nlayers16": "nlayers16", "L16": "L16",
               "a5": "a5", "tight2": "tight2", "tight025": "tight025", "alpha02": "alpha02", "alpha06": "alpha06",
               "scen_cold_wan_1gbps": "wan1g", "prothorizon": "prothorizon", "buf999": "buf999"}
# §3.4, typed from the specification: the rows and their points
SPEC_ROWS = {
    "alpha": ["alpha02", "alpha03", "alpha05", "alpha06"], "alpha_p": ["alphap06", "alphap10"], "mu": [],
    "mu_split": ["kv05", "kv10"],
    "load_scenario": ["scen_warm_peer_rdma", "scen_ssd_optimized", "scen_ssd_stock_safetensors",
                      "scen_ssd_stock_pytorch", "scen_a5_10GBps", "scen_a5_2GBps", "scen_cold_wan_10gbps",
                      "scen_cold_wan_1gbps"],
    "phi": ["phi05"], "kappa_L": ["kappaL05", "kappaL2"], "catalog": ["a5", "catM2", "catLg4"], "precision": ["L16"],
    "gpt4o_mini": ["tiermap"], "s_S": ["sS0", "sS05"], "xi": ["xi1"], "wildchat": ["wcfull"],
    "own_capacity": ["c0p50", "c0p90"], "smoothing": ["smooth5", "smooth60"], "lease_quantile": ["lease10", "lease50"],
    "layer_width": ["layer16"], "n_layers": ["nlayers4", "nlayers16"],
    "protected_term": ["prot1h", "prot1d", "prothorizon"], "buffer_quantile": ["buf999"],
    "tightness": ["tight025", "tight1", "tight2"], "delta1": ["delta0", "delta02"], "slo_class": ["strict", "slotier"],
    "transfer_fee": ["fee4"], "slow_slot": ["slow1"]}
GAMMA_ROWS = {"kappa_L", "catalog", "precision", "gpt4o_mini", "s_S", "xi", "wildchat", "own_capacity", "smoothing",
              "lease_quantile", "layer_width", "n_layers", "buffer_quantile", "tightness"}
# §3.5: the rows and points not run
SPEC_NOT_RUN = ["warm-peer and SSD load models", "client unit 1/u", "pool width zeta", "tier map",
                "per-tier tokens-per-conversation factor", "clock alignment at local midnight",
                "non-causal smoothing window", "scenario assignment per region pair",
                "offered layers V_l as the whole block below the lease-size quantile",
                "offered layers V_l as a share of the mean lendable capacity", "a uniform kappa multiplier"]


def _json(path: Path) -> dict:
    return json.loads(Path(path).read_text())


# ---------------------------------------------------------------- the job list (§3.8, §4.6, §3.9)
def test_job_list_counts_ids_and_limits(monkeypatch):
    monkeypatch.delenv(s1.REDUCED_ENV, raising=False)
    monkeypatch.delenv("S1_PART", raising=False)
    js = s1.jobs()
    mc.check_jobs(js)
    sweep = [j for j in js if j.params["part"] == "sweep"]
    q28 = [j for j in js if j.params["part"] == "q28"]
    assert len(sweep) == 204 and len(q28) == 76 and len(js) == 280
    assert all(j.kind == "pool" and j.params["policy_seeds"] == [0, 1, 2] for j in js)
    assert all(j.params["horizon_min"] == m4.WEEK_MIN for j in js)
    assert {(j.params["point"], j.params["c"]) for j in sweep} == {(p, c) for p in s1.POINT_NAMES for c in (1, 2, 3, 4)}
    cells = {(j.params["variant"], j.params["tag"], j.params["c"]) for j in q28}
    assert cells == {(v, t, c) for v in ("rf", "vr") for t in s1.Q28_TAGS for c in (1, 2, 3, 4)} | \
        {("default", "BL3", c) for c in (1, 2, 3, 4)}
    assert s1.Q28_TAGS == ("Sublet", "A7G", "A7", "A6", "BL5", "BL1", "BL2", "BL4", "BL3")
    for j in js:
        exp, part, kv = mc.parse_job_id(j.id)
        assert exp == "s1" and part == j.params["part"]
        if part == "sweep":
            assert j.id == f"s1:sweep:pt={j.params['point']}:c={j.params['c']}"
        else:
            assert j.id == f"s1:q28:var={j.params['variant']}:pol={j.params['tag']}:c={j.params['c']}"
            assert j.params["mode"] == {"rf": "L-rf", "vr": "L-vr", "default": "L-tr"}[j.params["variant"]]
        # §3.9: the limit is three times the job's estimate (three seeds), at least 1,800 s
        assert j.est_s > 0 and j.params["limit_s"] == max(1800, math.ceil(3 * j.est_s))
    for jid in ("s1:sweep:pt=default:c=1", "s1:sweep:pt=scen_cold_wan_1gbps:c=4", "s1:sweep:pt=slow1:c=2",
                "s1:q28:var=rf:pol=Sublet:c=1", "s1:q28:var=vr:pol=BL3:c=3", "s1:q28:var=default:pol=BL3:c=4"):
        assert jid in {j.id for j in js}, jid
    by = {j.id: j for j in js}
    # §3.9's longest jobs: slow1 (about 1,850 s), tight2 (about 1,390 s), nlayers16 (about 1,130 s)
    for p, est in (("slow1", 1850), ("tight2", 1390), ("nlayers16", 1130)):
        assert abs(by[s1.sweep_id(p, 1)].est_s - est) < 5, p
    assert by[s1.sweep_id("slow1", 1)].params["limit_s"] == 5551
    assert sweep[0].params["point"] == "slow1"                        # longest first within the part
    assert all(j.params["limit_s"] == 1800 for j in q28)
    assert [j.params["part"] for j in js] == ["sweep"] * 204 + ["q28"] * 76
    # §11.1: about 28.0 h (sweep) and 3.7 h (q28) of single-worker time
    assert abs(sum(j.est_s for j in sweep) / 3600 - 28.0) < 0.1
    assert abs(sum(j.est_s for j in q28) / 3600 - 3.7) < 0.1
    # --limits' lines
    lines = s1.limits_lines(js)
    assert lines[0] == f"pool 5551 {s1.sweep_id('slow1', 1)}" and len(lines) == 280
    # S1_PART selects a part's jobs
    for part, n in (("sweep", 204), ("q28", 76)):
        monkeypatch.setenv("S1_PART", part)
        assert len(s1.jobs()) == n and {j.params["part"] for j in s1.jobs()} == {part}
    monkeypatch.setenv("S1_PART", "sweeps")
    with pytest.raises(ValueError):
        s1.jobs()
    monkeypatch.delenv("S1_PART")
    # the reduced list: every point, variant and tag at alignment 1, policy seed 0, a 2-hour horizon
    monkeypatch.setenv(s1.REDUCED_ENV, "1")
    jr = s1.jobs()
    assert len([j for j in jr if j.params["part"] == "sweep"]) == 51
    assert len([j for j in jr if j.params["part"] == "q28"]) == 19
    assert all(j.params["c"] == 1 and j.params["policy_seeds"] == [0] and j.params["horizon_min"] == 120
               and j.params["limit_s"] == 1800 for j in jr)


def test_parts_and_paths():
    assert s1.PARTS == mc.COPY_PARTS["s1"] == ("sweep", "q28")
    assert s1.PASS_JOBS == s1.PASS_SUMMARIES == ("sweep", "q28")
    root = Path("/x/out/s1")
    assert s1.part_dir(root / "sweep", "sweep") == root / "sweep" and s1.part_dir(root, "q28") == root / "q28"
    assert s1.s1_root(root / "q28") == root and s1.s1_root(root) == root
    assert s1.run_path(root / "sweep", "sweep", "s1:sweep:pt=a5:c=2") == \
        root / "sweep" / "runs" / "s1__sweep__pt__a5__c__2.json"
    assert set(s1.CHECK_CLAIMS) == set(s1.CHECK_IDS_SWEEP) | set(s1.CHECK_IDS_Q28)


def test_time_constants_equal_the_measurements():
    """EST_MEASURED_S = build_s + engine_s of measurement 1's cases, EST_UNITS = s1_rows_build.json's client units,
    EST_Q28_S = measurement 3's case walls (§3.9, §11.1)."""
    for point, case in SIZING_CASE.items():
        t = _json(MS5SPEC / f"s1_sizing_{case}.json")["run"]["times"]
        assert abs(s1.EST_MEASURED_S[point] - (t["build_s"] + t["engine_s"])) <= 0.05, point
    assert set(s1.EST_MEASURED_S) == set(SIZING_CASE)
    table = {r["point"]: r for r in _json(MS5SPEC / "s1_rows_build.json")["table"]}
    assert set(s1.EST_UNITS) | set(s1.EST_MEASURED_S) == set(s1.POINT_NAMES)
    for point, u in s1.EST_UNITS.items():
        assert table[point]["units"] == u, point
    assert _json(MS5SPEC / "s1_rows_build.json")["default_build"]["sizes"]["n_units"] == s1.EST_DEFAULT_UNITS
    for (v, tag), w in s1.EST_Q28_S.items():
        assert abs(_json(MS5SPEC / f"q28_sizing_{v}_{tag}.json")["meta"]["wall_s"] - w) <= 0.05, (v, tag)
    # §3.9: about 8,384 s per (alignment, policy seed) over the 51 points
    assert abs(sum(s1.est_run_s(p) for p in s1.POINT_NAMES) - 8384) < 2


# ---------------------------------------------------------------- the register (§3.4, §3.5, §7.1)
def test_register_points_rows_and_panels():
    assert len(s1.POINT_NAMES) == 51 and s1.POINT_NAMES[0] == "default"
    assert list(s1.ROWS) == list(SPEC_ROWS)
    for key, names in SPEC_ROWS.items():
        assert [p.name for p in s1.POINTS.values() if p.row == key] == names, key
        assert s1.ROWS[key].gamma == (key in GAMMA_ROWS), key
    assert sum(len(v) for v in SPEC_ROWS.values()) == 50
    assert set(s1.MU_POINTS) == {"mu0.2", "mu0.5", "mu2"}
    panels = {}
    for key, r in s1.ROWS.items():
        panels.setdefault(r.panel, []).append(key)
    assert {k: len(v) for k, v in panels.items()} == {"a": 9, "b": 10, "c": 6}     # (c) adds Q28's two rows
    assert all(isinstance(p.label, str) and p.label for p in s1.POINTS.values())
    with pytest.raises(KeyError):
        s1.point_overrides("smoothc", None)


def test_scenarios_are_the_a11_scenarios():
    from sublet import calib
    assert [s for s, _ in s1.SCENARIOS] == list(calib.scenarios())


def test_not_run_is_the_list_of_section_3_5():
    assert [x["row"] for x in s1.NOT_RUN] == SPEC_NOT_RUN
    assert all(x["reason"] and x["sources"] for x in s1.NOT_RUN)
    for x in s1.NOT_RUN:
        for f in x["sources"]:
            if f.startswith("code/"):
                assert (SIM.parents[1] / f).is_file(), f


def test_static_overrides():
    """The points whose overrides do not read the default build (the others are checked against the measurements
    with the a12 outputs)."""
    want = {"kv05": {"stranding.kv_share": 0.5}, "phi05": {"costs.phi": 0.5},
            "tiermap": {"borrowers.wildchat_model": "early_card_map"}, "sS0": {"borrowers.s_S": 0.0},
            "c0p90": {"borrowers.own_capacity_quantile": 90.0}, "smooth60": {"borrowers.smoothing_min": 60},
            "lease10": {"lender_defaults.lease_size_quantile": 10}, "layer16": {"lender_defaults.layer_gpus": 16},
            "nlayers4": {"lender_defaults.n_layers": 4}, "buf999": {"prices.buffer_quantile": "p99.9"},
            "tight2": {"borrowers.market_tightness": 2.0}, "delta02": {"regions.relaxed_routing_cost_over_q": 0.2},
            "strict": {"regions.default_slo_class": "strict"},
            "slotier": {"borrowers.slo_class": {"S": "strict", "M": "relaxed", "L": "relaxed"}},
            "slow1": {"time.slow_slot_min": 1}, "default": {}}
    for name, ov in want.items():
        assert s1.point_overrides(name, None) == ov, name
    a = s1.point_overrides("slotier", None)
    a["borrowers.slo_class"]["S"] = "relaxed"                          # a copy: the table is not changed
    assert s1.point_overrides("slotier", None)["borrowers.slo_class"]["S"] == "strict"
    ref = types.SimpleNamespace(config={
        "prices": {"q_gpu_usd_per_gpu_h": 7.15}, "time": {"horizon_min": 120},
        "llms": [{"id": "S", "tier": "S", "kappa_mult": 1.0}, {"id": "M", "tier": "M", "kappa_mult": 1.0},
                 {"id": "L", "tier": "L", "kappa_mult": 1.0}],
        "contracts": [{"id": "k", "tau_min": 5, "H_min": 0}, {"id": "protected", "tau_min": None, "prepaid_min": 5}],
        "regions": {"list": ["r0", "r1"]},
        "borrowers": {"xi_sources": {"r0": {"series": "s0", "offset_min": 3},
                                     "r1": {"series": "s1", "offset_min": 7}}}})
    assert s1.point_overrides("alpha02", ref) == {"prices.a0_usd_per_gpu_h": 0.2 * 7.15}
    assert s1.point_overrides("alphap10", ref) == {"prices.a_protected_usd_per_gpu_h": 7.15}
    assert s1.point_overrides("kappaL2", ref) == {"llms.2.kappa_mult": 2.0}
    assert s1.point_overrides("catM2", ref) == {"llms.1.entry": "M_g_gpu_hours"}
    assert s1.point_overrides("L16", ref) == {"llms.2.entry": "L_16bit", "lender_defaults.layer_gpus": 16}
    assert s1.point_overrides("xi1", ref) == {"borrowers.xi_sources": {"r0": {"series": "s0", "offset_min": 3},
                                                                       "r1": {"series": "s0", "offset_min": 7}}}
    pro = s1.point_overrides("prothorizon", ref)
    assert pro["menu_preset"] is None and pro["contracts"][1]["prepaid_min"] == 120
    assert pro["contracts"][0] == ref.config["contracts"][0] and ref.config["contracts"][1]["prepaid_min"] == 5
    assert s1.point_overrides("prot1d", ref)["contracts"][1]["prepaid_min"] == 1440
    sc = s1.point_overrides("scen_ssd_optimized", ref)
    assert sc == {"lender_defaults.load_scenario": "ssd_optimized",
                  "protected_per_region.load_scenario": "ssd_optimized",
                  "borrowers.xi_sources": ref.config["borrowers"]["xi_sources"]}
    assert s1.point_overrides("a5", ref)["llms"][2] == {"id": "L", "catalog": "a5_llama3", "entry": "llama3.1-405b",
                                                         "kappa_mult": 1.0}


# ---------------------------------------------------------------- rows (§3.8, M5)
def _pts(**med) -> dict:
    return {k: {"value": k, "label": k, "n_runs": 0 if v is None else 12, "saving_pct_median": v}
            for k, v in med.items()}


def test_row_lo_hi_span_with_the_default():
    e = s1.row_entry("r", _pts(a=20.0, b=35.0), 30.0, label="r", panel="a", gamma=False, default_label="d")
    assert (e["lo"], e["hi"], e["span"], e["lo_point"], e["hi_point"]) == (20.0, 35.0, 15.0, "a", "b")
    assert e["complete"] and e["default"]["saving_pct_median"] == 30.0
    # the default is an end when it lies outside the points
    e = s1.row_entry("r", _pts(a=20.0, b=25.0), 30.0, label="r", panel="a", gamma=False, default_label="d")
    assert (e["lo"], e["hi"], e["span"], e["hi_point"]) == (20.0, 30.0, 10.0, "default")
    e = s1.row_entry("r", _pts(a=40.0), 30.0, label="r", panel="a", gamma=False, default_label="d")
    assert (e["lo_point"], e["hi_point"], e["span"]) == ("default", "a", 10.0)
    # ties: 'default' first, every attaining name listed
    e = s1.row_entry("r", _pts(a=30.0, b=31.0), 30.0, label="r", panel="a", gamma=False, default_label="d")
    assert e["lo_point"] == "default" and e["lo_points"] == ["default", "a"] and e["hi_points"] == ["b"]
    # a point without runs: left out of the ends and listed
    e = s1.row_entry("r", _pts(a=None, b=10.0), 30.0, label="r", panel="a", gamma=False, default_label="d")
    assert (e["lo"], e["hi"], e["complete"], e["points_missing"]) == (10.0, 30.0, False, ["a"])
    assert e["points"]["a"]["saving_pct_median"] is None
    e = s1.row_entry("r", _pts(a=None), None, label="r", panel="a", gamma=False, default_label="d")
    assert e["lo"] is None and e["lo_note"] and e["span"] is None and e["points_missing"] == ["default", "a"]
    json.dumps(e, allow_nan=False)


def test_rows_block_on_a_synthetic_summary():
    """rows_block over every row of §3.4 from a synthetic points summary, the mu row from a synthetic E7 summary."""
    pts = {n: {"n_runs": 12, "saving_pct": {"median": float(i)}} for i, n in enumerate(s1.POINT_NAMES)}
    pts["default"]["saving_pct"]["median"] = 25.0
    e7s = {"runs": {"1": {"Sublet": {"saving_pct": {"median": 28.0}, "n_runs": 12}},
                    "0.2": {"Sublet": {"saving_pct": {"median": 29.0}, "n_runs": 12}},
                    "0.5": {"Sublet": {"saving_pct": {"median": 27.0}, "n_runs": 12}},
                    "2": {"Sublet": {"saving_pct": {"median": 20.0}, "n_runs": 12}}}}
    rows = s1.rows_block(pts, e7s)
    assert list(rows) == list(SPEC_ROWS)
    a = rows["alpha"]                                         # points 1..4, default 25
    assert (a["lo"], a["hi"], a["lo_point"], a["hi_point"], a["span"]) == (1.0, 25.0, "alpha02", "default", 24.0)
    t = rows["tightness"]
    i = s1.POINT_NAMES.index
    assert (t["lo"], t["lo_point"], t["hi"], t["hi_point"]) == (25.0, "default", i("tight2"), "tight2")
    m = rows["mu"]
    assert (m["lo"], m["hi"], m["lo_point"], m["hi_point"]) == (20.0, 29.0, "mu2", "mu0.2")
    assert m["source"]["file"] == "code/sim/out/e7/main/summary.json"
    assert m["source"]["e7_default_saving_pct_median"] == 28.0 and m["default"]["saving_pct_median"] == 25.0
    assert all(r["complete"] for r in rows.values())
    rows2 = s1.rows_block(pts, None)
    assert rows2["mu"]["lo"] == 25.0 and rows2["mu"]["points_missing"] == ["mu0.2", "mu0.5", "mu2"]


# ---------------------------------------------------------------- S1-0 (§3.10)
def _default_entry(e7s: dict) -> tuple:
    ent = copy.deepcopy(e7s["runs"]["1"]["Sublet"])
    hashes = {k.split("c=")[1]: v["instance_hash"] for k, v in e7s["meta"]["instances"].items()
              if k.startswith("mu=1:")}
    return ent, hashes


def test_s1_0_against_a_copy_of_e7s_summary():
    e7s = _json(E7_MAIN)
    ent, hashes = _default_entry(e7s)
    r = s1.check_default(ent, hashes, e7s)
    assert r["status"] == "pass", r
    assert r["n_runs"] == {"s1": 12, "e7": 12} and set(r["overflow_usd"]) == {"median", "p95", "max", "mean"}
    assert all(v["equal"] for v in r["instance_hashes"].values()) and len(r["instance_hashes"]) == 4
    # a changed cost fails
    bad = copy.deepcopy(ent)
    bad["overflow_usd"]["mean"] *= 1 + 1e-7
    r = s1.check_default(bad, hashes, e7s)
    assert r["status"] == "fail" and r["stats_differ"] == ["mean"]
    # within 1e-9 relative passes
    ok = copy.deepcopy(ent)
    ok["overflow_usd"]["median"] *= 1 + 1e-12
    assert s1.check_default(ok, hashes, e7s)["status"] == "pass"
    # another instance hash fails; a missing one leaves it missing
    h2 = {**hashes, "3": "0" * 64}
    r = s1.check_default(ent, h2, e7s)
    assert r["status"] == "fail" and r["hashes_differ"] == [3]
    h3 = {k: v for k, v in hashes.items() if k != "4"}
    assert s1.check_default(ent, h3, e7s)["status"] == "missing"
    # fewer runs fail; no E7 summary or no default run: missing
    few = copy.deepcopy(ent)
    few["n_runs"] = 11
    assert s1.check_default(few, hashes, e7s)["status"] == "fail"
    assert s1.check_default(ent, hashes, None)["status"] == "missing"
    # a job of the default point without an 'ok' record: missing (fewer runs), unless a hash already differs
    assert s1.check_default(few, hashes, e7s, missing=True)["status"] == "missing"
    assert s1.check_default(ent, h2, e7s, missing=True)["status"] == "fail"
    assert s1.check_default({"n_runs": 0}, hashes, e7s)["status"] == "missing"
    json.dumps(r, allow_nan=False)


# ---------------------------------------------------------------- S1-1, S1-2, S1-3 on hand-made run files
def _vs(**kw) -> dict:
    v = {"instance_hash": "b" * 64, "default_instance_hash": "a" * 64, "instance_equal": False, "bl0a_usd": 10.0,
         "default_bl0a_usd": 10.0, "bl0a_equal": True,
         "demand_matched": {"n_matched": 15, "only_in_point": [], "only_in_default": [], "max_abs_diff": 0.0,
                            "identical": True},
         "llms_without_clients": [], "llms_fitting_no_layer_site": [],
         "fits": {"S": {"fits_a_layer_site": True}, "M": {"fits_a_layer_site": True}, "L": {"fits_a_layer_site": True}}}
    v.update(kw)
    return v


def test_s1_1_rule():
    files = {"a": {"point": "phi05", "c": 1, "vs_default": _vs()},
             "b": {"point": "tight2", "c": 1, "vs_default": _vs(bl0a_equal=False, bl0a_usd=40.0,
                                                                 demand_matched={"identical": False})},
             "c": {"point": "sS0", "c": 1, "vs_default": _vs(llms_without_clients=["S"])},
             "d": {"point": "default", "c": 1, "vs_default": _vs(instance_equal=True)},
             "e": {"point": "L16", "c": 1, "vs_default": _vs(bl0a_equal=False)}}
    r = s1.check_built(files)
    assert r["status"] == "pass" and r["n_instances"] == 4, r["failures"]
    assert set(r["g16_fits"]) == {"L16:c=1"}
    assert r["rows_without_gamma"] == [k for k in SPEC_ROWS if k not in GAMMA_ROWS and k != "mu"]
    for name, kw, word in (("phi05", {"bl0a_equal": False}, "BL0a"),
                           ("delta0", {"demand_matched": {"identical": True, "only_in_point": [["S", "r0"]],
                                                          "only_in_default": []}}, "demand"),
                           ("kappaL2", {"instance_equal": True}, "hash"),
                           ("a5", {"llms_fitting_no_layer_site": ["L"]}, "fitting"),
                           ("sS0", {}, "without clients"), ("tight1", {"llms_without_clients": ["S"]}, "without")):
        r = s1.check_built({"x": {"point": name, "c": 2, "vs_default": _vs(**kw)}})
        assert r["status"] == "fail" and word in " ".join(r["failures"][0]["problems"]), (name, r["failures"])
    assert s1.check_built({})["status"] == "missing"
    assert s1.check_built({"a": files["a"]}, missing=True)["status"] == "missing"


def _a8_row(case="W(a)", held=True, available=True, **kw) -> dict:
    r = {"policy_seed": 0, "c": 1, "job": "j", "n_invariant_failures": 0, "tag": "Sublet",
         "a8": {"certificate": {"available": available, "held": held}, "certificate_case": case, "t_a": None}}
    r.update(kw)
    return r


def test_s1_2_and_s1_3():
    r = s1.check_certificates([_a8_row(), _a8_row("W(b)"), _a8_row("W(c)", held=False)], "S1-2")
    assert r["status"] == "pass" and r["n_w_c"] == 1 and r["certificates"]["by_case"]["W(c)"]["runs"] == 1
    assert s1.check_certificates([_a8_row("W(b)", held=False)], "S1-2")["status"] == "fail"
    assert s1.check_certificates([_a8_row(available=False, case="unavailable")], "S1-2")["status"] == "fail"
    assert s1.check_certificates([_a8_row()], "S1-2", [{"job": "j", "error": "x"}])["status"] == "fail"
    assert s1.check_certificates([], "S1-2")["status"] == "missing"
    assert s1.check_certificates([_a8_row()], "S1-2", missing=True)["status"] == "missing"
    assert s1.check_clean([_a8_row()])["status"] == "pass"
    r = s1.check_clean([_a8_row(), _a8_row(n_invariant_failures=2, invariant_failures_first=["INV2 at 3"])])
    assert r["status"] == "fail" and r["n_invariant_failures"] == 1


# ---------------------------------------------------------------- Q28-1, Q28-2 and the q28 records
RV_TRACE = {"fast": None, "slow_lb": None, "slow": "bench grid 'slow' on a run with ..."}
RV_VR = {g: "violations = 'reclaim': ..." for g in s1.RATIO_GRIDS}


def test_q28_checks_on_hand_made_rows():
    rows = [{"variant": "vr", "tag": "A6", "policy_seed": 0, "c": 1, "ratio_validity": dict(RV_VR),
             "ratio_validity_default": dict(RV_TRACE), "n_invariant_failures": 0},
            {"variant": "rf", "tag": "BL2", "policy_seed": 0, "c": 1, "ratio_validity": dict(RV_TRACE),
             "ratio_validity_default": dict(RV_TRACE), "n_invariant_failures": 0, "sub_runs": [{}, {}]}]
    assert s1.check_ratio_validity(rows, False)["status"] == "pass"
    bad = copy.deepcopy(rows)
    bad[0]["ratio_validity"]["fast"] = None                           # a vr run with a ratio
    r = s1.check_ratio_validity(bad, False)
    assert r["status"] == "fail" and r["n_vr_with_a_ratio"] == 1
    bad = copy.deepcopy(rows)
    bad[1]["ratio_validity"]["fast"] = "something"                    # an rf run that loses its ratio
    assert s1.check_ratio_validity(bad, False)["n_rf_changed"] == 1
    assert s1.check_ratio_validity(rows[:1], False)["status"] == "missing"      # no rf run
    # the run files' lender models: the L-rf half holds by construction once the model is L-rf's
    lm = {"vr": {"schedule": "trace", "information": "I1", "on_unavailable": "sell", "violations": "reclaim",
                 "params": {}},
          "rf": {"schedule": "trace", "information": "I1", "on_unavailable": "refuse", "violations": "absorb",
                 "params": {}}}
    default = {"schedule": "trace", "information": "I1", "on_unavailable": "sell", "violations": "absorb",
               "params": {}}
    files = {f"j{v}": {"variant": v, "lender_model": dict(m), "lender_model_default": dict(default)}
             for v, m in lm.items()}
    files["jd"] = {"variant": "default", "lender_model": dict(default), "lender_model_default": dict(default)}
    r = s1.check_ratio_validity(rows, False, files)
    assert r["status"] == "pass" and r["n_files_checked"] == 2 and r["n_wrong_lender_model"] == 0
    # the variant's key missing or another key changed (each variant alone, §4.4)
    for v, k, x in (("rf", "on_unavailable", "sell"), ("rf", "schedule", "eager"), ("vr", "violations", "absorb"),
                    ("vr", "on_unavailable", "refuse"), ("rf", "violations", "reclaim"), ("vr", "information", "I2")):
        bad = copy.deepcopy(files)
        bad[f"j{v}"]["lender_model"][k] = x
        r = s1.check_ratio_validity(rows, False, bad)
        assert r["status"] == "fail" and r["n_wrong_lender_model"] == 1, (v, k)
    bad = copy.deepcopy(files)
    del bad["jrf"]["lender_model_default"]
    assert s1.check_ratio_validity(rows, False, bad)["n_wrong_lender_model"] == 1
    r = s1.check_finished({}, rows, [], {}, False)
    assert r["status"] == "pass" and r["n_sub_runs"] == 2
    sub = copy.deepcopy(rows)
    sub[1]["sub_runs"] = [{"n_invariant_failures": 1}]
    assert s1.check_finished({}, sub, [], {}, False)["status"] == "fail"
    assert s1.check_finished({}, rows, [{"job": "j", "error": "E"}], {}, False)["status"] == "fail"
    r = s1.check_finished({}, rows, [], {"s1:q28:var=rf:pol=A6:c=2": "oom_at_3G"}, True)
    assert r["status"] == "fail" and r["n_job_failures"] == 1
    assert s1.check_finished({}, rows, [], {}, True)["status"] == "missing"


def test_violation_record_and_refusals():
    """violation_record on a hand-made RunResult: events, lender-slots, deficits, victims with site, lender, LLM, slot
    and GPUs, the violation deaths and the engine's metric sums; summed over two sub-runs."""
    inst = types.SimpleNamespace(
        grid=types.SimpleNamespace(slow_min=5),
        sites=[types.SimpleNamespace(id="s0"), types.SimpleNamespace(id="s1")],
        llms=[types.SimpleNamespace(id="S"), types.SimpleNamespace(id="L")])
    L = types.SimpleNamespace
    res = types.SimpleNamespace(
        violations=[{"t": 7, "lender": "a", "deficit": 3.0, "deficit_attributable": 2.0, "victims": [4, 5]},
                    {"t": 8, "lender": "a", "deficit": 1.0, "deficit_attributable": 0.0}],
        leases=[L(id=4, site=1, gpus=8, end_cause="violation"), L(id=5, site=0, gpus=1, end_cause="violation"),
                L(id=6, site=0, gpus=1, end_cause="reclaim")],
        replicas=[L(lease_id=4, llm=1), L(lease_id=5, llm=0), L(lease_id=5, llm=0)],
        metrics={"violation_lender_slots": 2, "violation_deficit_gpu_slots": 4.0, "lender_slots_checked": 10,
                 "refused": {"capacity": 1, "unavailable": 3}})
    v, vic = s1.violation_record([res], [inst])
    assert (v["events"], v["events_attributable"], v["lender_slots"], v["victims"], v["violation_deaths"]) == \
        (2, 1, 2, 2, 2)
    assert v["deficit_gpu_slots"] == 4.0 and v["deficit_attributable_gpu_slots"] == 2.0
    assert v["engine_metrics"]["violation_lender_slots"] == 2 and v["engine_metrics"]["lender_slots_checked"] == 10
    assert vic[0] == {"lease": 4, "slot": 7, "minute": 35, "lender": "a", "site": "s1", "llm": "L", "llms": ["L"],
                      "gpus": 8, "end_cause": "violation"}
    assert vic[1]["site"] == "s0" and vic[1]["llm"] == "S"
    v2, vic2 = s1.violation_record([res, res], [inst, inst])
    assert v2["events"] == 4 and v2["lender_slots"] == 4 and v2["victims"] == 4
    assert {x["sub_run"] for x in vic2} == {0, 1}
    assert s1.refusal_record([res, res]) == {"capacity": 2, "unavailable": 6}
    assert s1.refusal_record([types.SimpleNamespace(metrics={})]) == {"capacity": 0, "unavailable": 0}


def test_q28_entry_and_references():
    """q28_entry keeps E7's cost entry fields for every tag (BL3 with the null A8 fields), and the references:
    E7's runs.1.<tag> for E7's tags, the default jobs for BL3."""
    row = {"policy_seed": 0, "config_seed": 1, "c": 1, "tag": "BL3", "bl0a_usd": 10.0,
           "components": {"total": 8.0}, "accountings": m4.accountings(8.0, None, {"bl0a_usd": 10.0,
                                                                                    "own_capacity_usd": 5.0,
                                                                                    "bl0b_overflow_usd": 20.0,
                                                                                    "bl0b_total_usd": 25.0}),
           "refused": {"capacity": 0, "unavailable": 4}, "violations": {"events": 1, "victims": 2, "lender_slots": 1,
                                                                        "violation_deaths": 2},
           "ratio_validity": dict(RV_TRACE), "n_invariant_failures": 0}
    e = s1.q28_entry([row], "BL3")
    assert e["overflow_over_bl0a"]["median"] == 0.8 and e["abort_share"] is None and e["abort_share_note"]
    assert e["refusals"]["unavailable"]["median"] == 4 and e["violation_victims"]["median"] == 2
    assert e["n_runs_with_violations"] == 1 and e["ratio_validity"]["fast"] == ["None"]
    assert {k for k in e if not k.endswith("note")} >= {k for k in e7.cost_entry([], "BL5")
                                                         if not k.endswith("note")}
    s1._set_reference(e, 0.7, 30.0, "x", "none")
    assert abs(e["delta_overflow_over_bl0a"] - 0.1) < 1e-12 and e["reference"]["saving_pct_median"] == 30.0
    empty = s1.q28_entry([], "Sublet")
    s1._set_reference(empty, None, None, "x", "no E7 run")
    assert empty["delta_overflow_over_bl0a"] is None and empty["delta_overflow_over_bl0a_note"]
    assert empty["certificates"] is not None or empty.get("certificates_note")
    json.dumps(empty, allow_nan=False)
    rows = s1.q28_rows({"rf": {"Sublet": {"n_runs": 1, "saving_pct": {"median": 33.0}}}, "vr": {}}, 31.0)
    assert (rows["q28_rf"]["lo"], rows["q28_rf"]["hi"], rows["q28_rf"]["span"]) == (31.0, 33.0, 2.0)
    assert rows["q28_vr"]["lo"] == 31.0 and rows["q28_vr"]["points_missing"] == ["q28_vr"]


def test_summaries_on_empty_folders(tmp_path, monkeypatch):
    """Both summaries without any output: every point, row, cell and check present, the checks missing (or
    informative), valid JSON."""
    monkeypatch.delenv(s1.REDUCED_ENV, raising=False)
    monkeypatch.delenv("S1_PART", raising=False)
    root = tmp_path / "s1"
    sw = s1.summary_sweep(root / "sweep")
    assert set(sw["points"]) == set(s1.POINT_NAMES) and list(sw["rows"]) == list(SPEC_ROWS)
    assert list(sw["checks"]) == list(s1.CHECK_IDS_SWEEP)
    assert [sw["checks"][k]["status"] for k in s1.CHECK_IDS_SWEEP] == ["missing"] * 4 + ["informative"]
    assert len(sw["meta"]["jobs_missing"]) == 204 and sw["meta"]["e7_summary"]["exists"]
    assert sw["not_run"] == [dict(x) for x in s1.NOT_RUN]
    q = s1.summary_q28(root / "q28")
    assert set(q["runs"]) == {"rf", "vr", "default"} and set(q["runs"]["rf"]) == set(s1.Q28_TAGS)
    assert [q["checks"][k]["status"] for k in s1.CHECK_IDS_Q28] == ["missing"] * 3 + ["informative"]
    assert q["meta"]["sweep_summary"]["used"] is True                  # the empty sweep summary above
    assert q["runs"]["rf"]["A6"]["reference"]["source"].endswith("runs.1.A6")
    assert q["runs"]["rf"]["A6"]["reference"]["overflow_over_bl0a_median"] == \
        _json(E7_MAIN)["runs"]["1"]["A6"]["overflow_over_bl0a"]["median"]
    assert "q28/summary.json runs.default.BL3" in q["runs"]["vr"]["BL3"]["reference"]["source"]
    for p in ("sweep", "q28"):
        json.loads((root / p / "summary.json").read_text())
        assert (root / p / "tables.md").is_file()
    # a sweep summary whose s1:summary record is not 'ok' is not used
    mc.dump_json({"job": "s1:summary", "status": "error"}, mc.record_path(root / "sweep", "s1:summary"))
    q2 = s1.summary_q28(root / "q28")
    assert q2["meta"]["sweep_summary"]["used"] is False and "'error'" in q2["meta"]["sweep_summary"]["used_note"]


# ---------------------------------------------------------------- run_s1.sh with a fake driver
FAKE_DRIVER = '''
import json, os, sys, time
from sublet.experiments import ms3_common as mc

def jobs():
    part = os.environ.get("S1_PART", "")
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
        f.write(f"summary:{os.environ.get('S1_PART')} {time.time()} {time.time()}\\n")
    mc.dump_json({"records": len(mc.read_records(out))}, out / "summary.json")

if __name__ == "__main__":
    if "--limits" in sys.argv:
        for j in jobs():
            print(f"{j.kind} {j.params['limit_s']} {j.id}")
        sys.exit(0)
    sys.exit(mc.main("s1", jobs=jobs, run=run, summary=summary))
'''


def _scope_env() -> dict:
    if shutil.which("systemd-run") is None:
        return {"MS3_SCOPE": "0"}
    r = subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0",
                        "true"], capture_output=True, timeout=60)
    return {} if r.returncode == 0 else {"MS3_SCOPE": "0"}


def _root(path: Path) -> Path:
    (path / "out" / "e11").mkdir(parents=True, exist_ok=True)
    (path / "out" / "e11" / "summary.json").write_text("{}\n")
    return path


def _run_fake(tmp_path: Path, jobs: list, events: str = "events.txt", **extra):
    root = _root(tmp_path / "root")
    mod = tmp_path / "mod"
    mod.mkdir(exist_ok=True)
    (mod / "fake_s1.py").write_text(FAKE_DRIVER)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "FAKE_", "S1_"))}
    env.update(MS3_ROOT=str(root), MS3_WORKERS="2", MS3_POLL_S="0.2", MS3_PY=sys.executable, MS3_MODULE="fake_s1",
               PYTHONPATH=os.pathsep.join([str(mod), str(SIM)]), FAKE_JOBS=json.dumps(jobs),
               FAKE_EVENTS=str(tmp_path / events), **_scope_env(), **extra)
    p = subprocess.run(["bash", str(RUN_S1)], env=env, capture_output=True, text=True, timeout=300)
    ev = {}
    f = tmp_path / events
    for line in (f.read_text().splitlines() if f.is_file() else []):
        jid, t0, t1 = line.split()
        ev[jid] = (float(t0), float(t1))
    return p, ev, root / "out" / "s1"


FAKE_JOBS = [["s1:sweep:pt=a:c=1", "sweep", 0.3, 30], ["s1:sweep:pt=b:c=1", "sweep", 30.0, 2],
             ["s1:sweep:pt=c:c=1", "sweep", 0.3, 30], ["s1:q28:var=rf:pol=X:c=1", "q28", 0.3, 30]]


def test_run_script_passes_and_limits(tmp_path):
    p, ev, out = _run_fake(tmp_path, FAKE_JOBS, MS3_S1_TEST_GRACE_S="0")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == {"s1:sweep:pt=a:c=1", "s1:sweep:pt=c:c=1", "s1:q28:var=rf:pol=X:c=1", "summary:sweep",
                       "summary:q28"}
    sw = mc.read_records(out / "sweep")
    assert sw["s1:sweep:pt=a:c=1"]["status"] == "ok" and sw["s1:sweep:pt=c:c=1"]["status"] == "ok"
    b = sw["s1:sweep:pt=b:c=1"]                                    # stopped by timeout at its limit of 2 s
    assert b["status"] == "wall_limit" and b["exit_code"] == 124 and b["elapsed_s"] < 20, b
    assert b["timeout_limit_s"] == 2.0, b
    assert (out / "sweep" / "jobs_limits.txt").read_text().split("\n")[1] == "pool 2 s1:sweep:pt=b:c=1"
    # pass 1 runs part sweep's jobs, then part q28's; pass 2 the summaries, sweep's first
    q = ev["s1:q28:var=rf:pol=X:c=1"]
    assert all(ev[j][1] <= q[0] for j in ("s1:sweep:pt=a:c=1", "s1:sweep:pt=c:c=1"))
    assert q[1] <= ev["summary:sweep"][0] <= ev["summary:q28"][0]
    for part in ("sweep", "q28"):
        recs = mc.read_records(out / part)
        assert recs["s1:summary"]["status"] == "ok" and recs["s1:manifest"]["status"] == "ok", part
        log = (out / part / "run_s1.log").read_text()
        assert f"pass 1 (jobs), part {part}" in log and f"pass 2 (summary), part {part}" in log
        assert log.rstrip().splitlines()[-1].startswith("[run_s1] done ")
        assert (out / part / "summary.json").is_file() and (out / part / "manifest.json").is_file()
    # resume: the ok jobs are skipped, the failed one runs again (here with a limit it meets)
    jobs2 = copy.deepcopy(FAKE_JOBS)
    jobs2[1][2] = 0.3
    p, ev2, out = _run_fake(tmp_path, jobs2, events="events2.txt", MS3_RESUME="1")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev2) == {"s1:sweep:pt=b:c=1", "summary:sweep", "summary:q28"}
    assert mc.read_records(out / "sweep")["s1:sweep:pt=b:c=1"]["status"] == "ok"
    assert "s1:sweep:pt=a:c=1: ok before, skipped" in (out / "sweep" / "run_s1.log").read_text()


def test_run_script_only(tmp_path):
    """S1_ONLY runs only the matching jobs; the others have no record and both summaries are still written."""
    p, ev, out = _run_fake(tmp_path, FAKE_JOBS, S1_ONLY=r"pt=(a|c):")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == {"s1:sweep:pt=a:c=1", "s1:sweep:pt=c:c=1", "summary:sweep", "summary:q28"}
    assert "S1_ONLY='pt=(a|c):': only the matching jobs run" in (out / "sweep" / "run_s1.log").read_text()
    recs = mc.read_records(out / "sweep")
    assert "s1:sweep:pt=b:c=1" not in recs and recs["s1:summary"]["status"] == "ok"
    p, _, _ = _run_fake(tmp_path / "bad", FAKE_JOBS, events="ev_bad.txt", S1_ONLY="(")
    assert p.returncode == 2 and "S1_ONLY is not a valid extended regex" in p.stderr


def test_run_script_parses():
    assert subprocess.run(["bash", "-n", str(RUN_S1)]).returncode == 0
    assert os.access(RUN_S1, os.X_OK)


# ---------------------------------------------------------------- with the a12 outputs
@pytest.mark.needs_a12
@pytest.mark.slow
def test_point_overrides_and_instance_hashes_at_alignment_1():
    """Every point at alignment 1 on the E7 main week: point_overrides equals the overrides that s1_sizing.py and
    s1_rows_build.py recorded, and the instance hash the hash they recorded; the rows without Gamma keep the demand,
    compared client by client, and BL0a (s1_rows_build.json table[].demand_identical_matched)."""
    import gc
    rows = _json(MS5SPEC / "s1_rows_build.json")
    table = {r["point"]: r for r in rows["table"]}
    ref = s1.build_default(1, m4.WEEK_MIN)[0]
    h_ref = mc.instance_hash(ref)
    assert h_ref == rows["default_build"]["instance_hash"] == \
        _json(MS5SPEC / "s1_sizing_default_build.json")["instance"]["instance_hash"] == \
        _json(E7_MAIN)["meta"]["instances"]["mu=1:c=1"]["instance_hash"]
    for name in s1.POINT_NAMES[1:]:
        ov = json.loads(json.dumps(s1.point_overrides(name, ref)))
        want = []
        if name in rows["points"]:
            want.append((rows["points"][name]["overrides"], rows["points"][name]["instance"]["instance_hash"]))
        if name in SIZING_CASE:
            b = _json(MS5SPEC / f"s1_sizing_{SIZING_CASE[name]}_build.json")
            want.append((b["overrides"], b["instance"]["instance_hash"]))
        assert want, name
        inst = s1.build_point(name, ref, 1, m4.WEEK_MIN)[0]
        h = mc.instance_hash(inst)
        for w_ov, w_h in want:
            assert ov == w_ov, name
            assert h == w_h, name
        v = s1.vs_default(inst, ref, h, h_ref)
        gamma = s1.ROWS[s1.POINTS[name].row].gamma
        if name in table:
            assert v["demand_matched"]["identical"] == table[name]["demand_identical_matched"], name
            assert v["bl0a_ratio"] == pytest.approx(table[name]["bl0a_ratio"], rel=1e-12), name
        if not gamma:
            assert v["demand_matched"]["identical"] is True and v["bl0a_equal"] is True, name
        assert v["llms_without_clients"] == (["S"] if name == "sS0" else []), name
        assert v["llms_fitting_no_layer_site"] == [] and not v["instance_equal"], name
        del inst
        gc.collect()


@pytest.mark.needs_a12
@pytest.mark.slow
def test_default_labels_match_the_default_build():
    """Each row's default label (ROWS[...].default_label, typed in the driver and drawn by sf_s1 as an end label where
    the default point ends a bar) matches the default build as the builder resolves configs/bench_e7f.json: the
    numbers from inst.config and drivers.provision's prices, the categorical labels from the fields they name."""
    inst = s1.build_default(1, s1.REDUCED_HORIZON_MIN)[0]
    cfg, pr = inst.config, s1.prices(inst)
    lenders = [x for x in cfg["lenders"] if x.get("kind") == "trace"]
    one = lambda key: {x[key] for x in lenders}                       # noqa: E731
    assert lenders and all(len(one(k)) == 1 for k in ("n_layers", "layer_gpus", "lease_size_quantile"))
    llm = {x["id"]: x for x in cfg["llms"]}
    protected = [c for c in cfg["contracts"] if c.get("klass") == "protected"]
    assert len(protected) == 1
    g = "{:g}".format
    resolved = {
        "alpha": f"{pr['alpha']:.2f}", "alpha_p": f"{pr['alpha_p']:.2f}",
        "mu": g(cfg["stranding"]["mu_over_beta_tilde"]), "mu_split": g(cfg["stranding"]["kv_share"]),
        "phi": g(cfg["costs"]["phi"]), "kappa_L": "x" + g(llm["L"]["kappa_mult"]),
        "catalog": "MaaS" if {x["catalog"] for x in cfg["llms"]} == {"maas_a10"} else None,
        "s_S": g(cfg["borrowers"]["s_S"]),
        "xi": "per region" if set(cfg["borrowers"]["xi_sources"]) == set(cfg["regions"]["list"]) else None,
        "wildchat": cfg["borrowers"]["wildchat_model"],
        "own_capacity": "P" + g(cfg["borrowers"]["own_capacity_quantile"]),
        "smoothing": f"{cfg['borrowers']['smoothing_min']} min",
        "lease_quantile": "P" + g(one("lease_size_quantile").pop()),
        "layer_width": f"{one('layer_gpus').pop()} GPUs", "n_layers": str(one("n_layers").pop()),
        "protected_term": f"{protected[0]['prepaid_min']} min",
        "buffer_quantile": g(float(cfg["prices"]["buffer_quantile"].lstrip("p")) / 100),
        "tightness": g(cfg["borrowers"]["market_tightness"]),
        "delta1": g(cfg["regions"]["relaxed_routing_cost_over_q"]),
        "slo_class": cfg["regions"]["default_slo_class"] if cfg["borrowers"]["slo_class"] is None else None,
        "transfer_fee": g(cfg["costs"]["beta_jl_usd"]),
        "slow_slot": f"{cfg['time']['slow_slot_min']} min"}
    # the categorical rows: the a5 pair of load-time scenarios (the lenders' and the protected sites'), L's weight
    # precision in a11's catalog entry, gpt-4o-mini's tier under the borrower model's tier map (a4b)
    scen = one("load_scenario") | {cfg["protected_per_region"]["load_scenario"]}
    resolved["load_scenario"] = "a5 pair" if scen == {"a5_10GBps", "a5_2GBps"} else sorted(scen)
    a11 = json.loads((REPO / "code/analysis/out/a11_calibration.json").read_text())
    resolved["precision"] = a11["catalog"][llm["L"]["catalog"]][llm["L"]["entry"]]["precision"].replace("-", " ")
    a4b = json.loads((REPO / "code/analysis/out/a4b_wildchat_weekly.json").read_text())
    tm = a4b["borrower_model"][cfg["borrowers"]["wildchat_model"]]["tier_map"]
    assert tm == "default"
    resolved["gpt4o_mini"] = a4b["definitions"]["tier_map"]["variant_override"]["gpt-4o-mini"]
    assert set(resolved) == set(s1.ROWS)
    for key, want in resolved.items():
        assert s1.ROWS[key].default_label == want, (key, s1.ROWS[key].default_label, want)


E2E_JOBS = (s1.sweep_id("default", 1), s1.sweep_id("fee4", 1), s1.q28_id("rf", "Sublet", 1),
            s1.q28_id("vr", "BL2", 1), s1.q28_id("rf", "BL3", 1), s1.q28_id("default", "BL3", 1))
E2E_ONLY = "^(" + "|".join(re.escape(j) for j in E2E_JOBS) + ")$"


@pytest.mark.needs_a12
@pytest.mark.slow
def test_run_script_reduced_end_to_end(tmp_path):
    """run_s1.sh --reduced under a scratch MS3_ROOT, by default on the six jobs of E2E_ONLY and with
    SUBLET_S1_E2E_FULL=1 on the whole reduced grid: the selected jobs of both parts ok, both summaries with
    meta.reduced true and every check row, the A8 records of M4, the q28 records and Sublet's reference at S1's default
    point; on the whole grid also every job ok and the check rows S1-1..S1-3 and Q28-1..Q28-3 passing."""
    full = os.environ.get("SUBLET_S1_E2E_FULL") == "1"
    given = os.environ.get("SUBLET_S1_REDUCED_ROOT")
    root = _root(Path(given) if given else tmp_path / "root")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "S1_", "FAKE_"))}
    env.update(MS3_ROOT=str(root), MS3_WORKERS=os.environ.get("MS3_WORKERS", "1"), MS3_POLL_S="1",
               MS3_PY=sys.executable, **_scope_env(), **({} if full else {"S1_ONLY": E2E_ONLY}))
    p = subprocess.run(["bash", str(RUN_S1), "--reduced"], env=env, capture_output=True, text=True, timeout=7200)
    assert p.returncode == 0, p.stdout[-4000:] + p.stderr[-4000:]
    out = root / "out" / "s1"
    for part, n in (("sweep", 51), ("q28", 19)):
        recs = mc.read_records(out / part)
        listed = [ln.split()[1] for ln in (out / part / "jobs_list.txt").read_text().splitlines()]
        run = listed if full else [j for j in listed if j in E2E_JOBS]
        assert len(listed) == n and len(run) == (n if full else {"sweep": 2, "q28": 4}[part]), part
        assert all(recs[j]["status"] == "ok" and recs[j]["n_errors"] == 0 for j in run), part
        assert recs["s1:summary"]["status"] == "ok" and recs["s1:manifest"]["status"] == "ok"
        assert (out / part / "run_s1.log").read_text().rstrip().splitlines()[-1].startswith("[run_s1] done ")
        summ = _json(out / part / "summary.json")
        assert sorted(summ["meta"]["jobs_missing"]) == sorted(set(listed) - set(run)), part
    sw = _json(out / "sweep" / "summary.json")
    assert sw["meta"]["reduced"] is True and sw["meta"]["reduced_note"]
    assert list(sw["checks"]) == list(s1.CHECK_IDS_SWEEP)
    for k in ("S1-1", "S1-2", "S1-3"):
        assert sw["checks"][k]["status"] == ("pass" if full else "missing"), (k, sw["checks"][k])
    # S1-0 compares the 2-hour runs with E7's weeks: it fails in a reduced run, by construction
    assert sw["checks"]["S1-0"]["status"] == "fail" and sw["checks"]["S1-0"]["hashes_differ"] == [1]
    assert sw["checks"]["S1-4"]["status"] == "informative"
    ran = set(s1.POINT_NAMES) if full else {"default", "fee4"}
    assert all(e["n_runs"] == 1 and e["saving_pct"]["median"] is not None for k, e in sw["points"].items()
               if k in ran)
    assert list(sw["rows"]) == list(SPEC_ROWS)
    if full:
        assert all(r["lo"] is not None and r["span"] >= 0 for r in sw["rows"].values())
    assert sw["not_run"] == [dict(x) for x in s1.NOT_RUN]
    assert set(sw["meta"]["instances"]) == ran
    f = _json(s1.run_path(out / "sweep", "sweep", s1.sweep_id("fee4", 1)))
    assert f["meta"]["git_revision"] and f["horizon_min"] == 120 and f["meta"]["reduced"] is True
    a = f["runs"][0]["a8"]
    assert a["B0_rule"] == m4.B0_RULE and a["B0_usd"] == m4.B0_SHARE * f["references"]["bl0a_usd"]
    assert a["info_class_reported"] == m4.INFO_CLASS_REPORTED and a["certificate"]["available"]
    q = _json(out / "q28" / "summary.json")
    assert q["meta"]["reduced"] is True and list(q["checks"]) == list(s1.CHECK_IDS_Q28)
    for k in ("Q28-1", "Q28-2", "Q28-3"):
        assert q["checks"][k]["status"] == ("pass" if full else "missing"), (k, q["checks"][k])
    assert q["checks"]["Q28-2"]["n_files_checked"] == (18 if full else 3)
    assert q["checks"]["Q28-2"]["n_wrong_lender_model"] == 0
    cells = [(v, t) for v in ("rf", "vr") for t in s1.Q28_TAGS] if full else [("rf", "Sublet"), ("vr", "BL2"),
                                                                              ("rf", "BL3")]
    assert all(q["runs"][v][t]["n_runs"] == 1 for v, t in cells)
    assert q["runs"]["default"]["BL3"]["n_runs"] == 1
    sub = q["runs"]["rf"]["Sublet"]
    assert sub["reference_s1_default"]["saving_pct_median"] == sw["points"]["default"]["saving_pct"]["median"]
    assert q["meta"]["sweep_summary"]["used"] is True and q["meta"]["sweep_summary"]["reduced"] is True
    assert set(q["rows"]) == {"q28_rf", "q28_vr"}
    vr = _json(s1.run_path(out / "q28", "q28", s1.q28_id("vr", "BL2", 1)))
    assert vr["lender_model"]["violations"] == "reclaim" and all(vr["ratio_validity"][g] for g in s1.RATIO_GRIDS)
    r = vr["runs"][0]
    assert r["runner"] == "siloed" and set(r["refused"]) >= {"capacity", "unavailable"}
    assert {"events", "lender_slots", "deficit_gpu_slots", "deficit_attributable_gpu_slots"} <= set(r["violations"])
    rf = _json(s1.run_path(out / "q28", "q28", s1.q28_id("rf", "BL3", 1)))
    assert rf["lender_model"]["on_unavailable"] == "refuse" and rf["runs"][0]["style_key"] == "bl3"
    assert rf["ratio_validity"] == rf["ratio_validity_default"]
    json.dumps(sw, allow_nan=False)
    json.dumps(q, allow_nan=False)
