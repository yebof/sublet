"""Tests of the E7 driver sublet/experiments/e7.py (design/sim_spec_ms4.md §3, §10 row test_e7.py).

Quick (no raw data):
- the job list of §3.10: 128 e7:main, 36 e7:links, 40 e7:stress, 42 e7:allow, 32 e7:gap_run (pool) and 4 e7:gap_lp
  (alone) jobs, every id parses, no two share a record file; E7_PART selects a part's jobs; the reduced list
  (MS3_E7_REDUCED=1) keeps every job kind at alignment 1, policy seed 0 and a 2-hour horizon;
- every A8 job of the grids carries ms4_common.sublet_params of the run's own instance (inner BL5 for Sublet, A7 for
  A7 + guard; ms4_common.B0_SHARE, B0_RULE) and the sweep its rule (theory_params for 'auto', the share otherwise),
  with the allowance record's B0_rule; the unguarded tags take their fixed parameters;
- check E7-6's rule test on hand-made A8 records (a B0 off by more than 1e-12 relative, a kappa outside the sweep, a
  wrong rule fail; the sweep's theory point passes with kappa 10); main's combined checks block (every id of §3.11
  once; a part's fail fails it, a missing part leaves it missing, E7-8 ... E7-12 informative); the null forms of an
  entry without runs keep every field (both accountings in the gap and allow entries, the LP and BL0a entries of
  gap/summary.json, E7-11's slots, a null Table III cell's reason);
- the fail paths of the checks on hand-made records: E7-1 (a proven case not held, an unavailable certificate; W(c)
  counted), E7-2 (BL2's sub-runs included), E7-4 (1e-9 relative, overflow = ALG, BL0a's total accounting), E7-3 (a P1
  run below the LP fails, BL2 and non-P1 runs are exempt, an LP not optimal or on another grid, another hash, a
  ratio_validity reason, two schedules at one alignment), E7-7 (a total off by 1e-6 USD fails, a missing seed or a
  reference whose record is not 'ok' leaves it missing); a part summary whose e7:summary record is not 'ok' is not
  used.
With the a12 outputs (needs_a12):
- the E7 week spec builds measurement 1's instance (169 sites, 21 contracts, 15 clients, T_slow 2016) with
  check_invariants true and its references; M1's routing graphs (n in {0, 2, 3}) have exactly the n links as
  cross-region arcs (measurement 9's cross_region_arcs) and the same BL0a at every n
  (allowance_need_ms4_e7_links*.json);
- the stress modes resolve on the week to Phi 84 (L-ss) and U 2016 (L-iid) (e7f_week_stress_*.json);
- the gap instance has the e7r + H5 contracts on 173 sites (e7r_h5_lp_estimate.json) and ratio_validity None at every
  alignment;
- slow: a selection of reduced jobs of every part end to end at a 1-hour horizon, then the four summaries in pass-2
  order and table3.json: the A8 records (B0_rule, B0 = B0_SHARE x BL0a of the run's own instance, info class), both
  accountings on every run, gap pairing (E7-3, E7-5 pass), E7-7's pairs, the summary keys that Fig. 4, Table III and
  sf_e7_allow read, an output whose record is not 'ok' is ignored, a part summary with a failed e7:summary record is
  not used by main's summary and table3.json, and an LP of another schedule fails E7-3.
"""
import copy
import hashlib
import json

import numpy as np
import pytest

from fixtures import SIM, assert_rel, toy_instance

from sublet.experiments import e7
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms4_common as m4
from sublet.experiments.e6 import bl0a_all

MS4SPEC = SIM / "out" / "ms4spec"


# ---------------------------------------------------------------- the job list (§3.10)
def test_job_list_counts_and_ids(monkeypatch):
    monkeypatch.delenv(e7.REDUCED_ENV, raising=False)
    monkeypatch.delenv("E7_PART", raising=False)
    js = e7.jobs()
    mc.check_jobs(js)
    by = {}
    for j in js:
        by.setdefault(j.params["kind"], []).append(j)
        assert mc.parse_job_id(j.id)[0] == "e7" and j.est_s is not None and j.est_s > 0
    assert {k: len(v) for k, v in by.items()} == {"main": 128, "links": 36, "stress": 40, "allow": 42,
                                                  "gap_run": 32, "gap_lp": 4}
    assert {j.kind for j in by["gap_lp"]} == {"alone"} and all(j.kind == "pool" for j in js if j not in by["gap_lp"])
    runs = sum(len(j.params["policy_seeds"]) for j in js if j.params["kind"] != "gap_lp")
    assert runs == 384 + 108 + 120 + 126 + 96                  # §3.10's run counts
    ids = {j.id for j in js}
    for jid in ("e7:main:pol=Sublet:mu=1:c=1", "e7:main:pol=A7G:mu=0.2:c=4", "e7:links:n=0:pol=BL1:c=3",
                "e7:stress:mode=L-iid-0.05:pol=BL4", "e7:allow:b0=auto:mode=L-tr", "e7:allow:b0=0.005:mode=L-co",
                "e7:gap_run:pol=BL2:c=2", "e7:gap_lp:c=4"):
        assert jid in ids, jid
    assert {j.params["mode"] for j in by["stress"]} == set(m4.stress_modes())
    assert {j.params["b0"] for j in by["allow"]} == set(e7.ALLOW_B0) and m4.B0_SHARE in e7.ALLOW_B0
    assert {j.params["n"] for j in by["links"]} == set(e7.LINKS) and {j.params["tag"] for j in by["links"]} == \
        set(e7.LINK_TAGS)
    assert all(j.params["horizon_min"] == m4.WEEK_MIN for j in by["main"])
    assert all(j.params["horizon_min"] == m4.DAY_MIN for j in by["gap_run"] + by["gap_lp"])
    assert all(j.params["time_limit_s"] == e7.GAP_LP_LIMIT_S == 1500.0 for j in by["gap_lp"])
    # E7_PART selects the jobs of a part (the run script lists them per part)
    for part, kinds in (("main", {"main", "links"}), ("stress", {"stress"}), ("allow", {"allow"}),
                        ("gap", {"gap_run", "gap_lp"})):
        monkeypatch.setenv("E7_PART", part)
        assert {j.params["kind"] for j in e7.jobs()} == kinds
        assert {j.params["part"] for j in e7.jobs()} == {part}
    monkeypatch.setenv("E7_PART", "mains")
    with pytest.raises(ValueError):
        e7.jobs()
    monkeypatch.delenv("E7_PART")
    # the reduced list: every job kind, alignment 1, policy seed 0, a 2-hour horizon
    monkeypatch.setenv(e7.REDUCED_ENV, "1")
    jr = e7.jobs()
    kinds = {}
    for j in jr:
        kinds[j.params["kind"]] = kinds.get(j.params["kind"], 0) + 1
    assert kinds == {"main": 32, "links": 9, "stress": 40, "allow": 42, "gap_run": 8, "gap_lp": 1}
    assert all(j.params.get("c", 1) == 1 and j.params.get("policy_seeds", [0]) == [0] for j in jr)
    assert all(j.params["horizon_min"] == e7.REDUCED_HORIZON_MIN for j in jr)


def test_parts_and_paths():
    assert e7.PARTS == mc.COPY_PARTS["e7"] == ("main", "stress", "gap", "allow")
    assert e7.PASS_JOBS == ("gap", "stress", "main", "allow") and e7.PASS_SUMMARIES[-1] == "main"
    assert set(e7.PASS_JOBS) == set(e7.PASS_SUMMARIES) == set(e7.PARTS)
    from pathlib import Path
    root = Path("/x/out/e7")
    assert e7.part_dir(root / "main", "main") == root / "main" and e7.part_dir(root, "gap") == root / "gap"
    assert e7.e7_root(root / "allow") == root and e7.e7_root(root) == root
    assert e7.run_path(root / "gap", "gap", "e7:gap_lp:c=2") == root / "gap" / "runs" / "e7__gap_lp__c__2.json"
    assert e7.lp_path(root / "gap", 3) == root / "gap" / "lb" / "lp_c3.json"
    assert set(e7.CHECK_IDS) == {x for v in e7.PART_CHECKS.values() for x in v} == set(e7.CHECK_CLAIMS)
    assert e7.TABLE3_ROWS == ("Sublet", "BL5", "BL1", "BL2", "BL4", "A7", "A7G", "A6", "BL0b", "BL0a")


# ---------------------------------------------------------------- Sublet's allowance in every A8 job (§3.3, M36)
def test_every_a8_job_carries_the_rule(monkeypatch):
    """Every A8 job of the grids gets sublet_params of the run's own instance (main, links, stress, gap) or the sweep's
    rule (allow); the parameters pass the run spec's validation and their allowance record names the rule."""
    monkeypatch.delenv(e7.REDUCED_ENV, raising=False)
    monkeypatch.delenv("E7_PART", raising=False)
    inst = toy_instance()
    bl0a = bl0a_all(inst)
    n_a8 = 0
    for j in e7.jobs():
        tag = j.params.get("tag")
        if tag is None:
            assert j.params["kind"] == "gap_lp"
            continue
        b0 = j.params.get("b0")
        p = e7.tag_params(tag, inst, b0)
        if not e7.is_a8(tag):
            assert p == {} and j.params["kind"] != "allow"
            continue
        n_a8 += 1
        inner = {"Sublet": "BL5", "A7G": "A7"}[tag]
        rec = m4.allowance_record(p, inst)
        if j.params["kind"] != "allow":
            assert p == m4.sublet_params(inst, inner) == {"inner": inner, "gamma": 1.0, "kappa": None,
                                                         "B0": m4.B0_SHARE * bl0a}
            assert rec["B0_rule"] == m4.B0_RULE and rec["kappa"] is None
        elif b0 == "auto":
            assert p == m4.theory_params("BL5") and rec["B0_rule"] == m4.THEORY_RULE and rec["kappa"] == 10.0
        else:
            assert p == m4.sublet_params(inst, "BL5", share=b0)
            assert rec["B0_rule"] == f"{mc.num_key(b0)}*BL0a" and rec["B0_usd"] == b0 * bl0a
        spec = e7.week_spec("A8", p, horizon_min=120)
        assert spec["policy"] == {"id": "A8", "params": p} and spec["engine"] == {"check_invariants": True}
    assert n_a8 == 2 * 4 * 4 + 3 * 4 + 2 * 5 + 42 + 2 * 4
    with pytest.raises(ValueError):
        e7.tag_params("BL5", inst, m4.B0_SHARE)
    assert e7.tag_params("BL2", inst) == {} and e7.TAGS["BL4"]["params"] == {}


def _a8(**kw):
    rec = {"B0_rule": m4.B0_RULE, "B0_usd": m4.B0_SHARE * 200.0, "bl0a_usd": 200.0, "gamma": 1.0, "kappa": None,
           "B0_report_usd": m4.B0_SHARE * 200.0, "info_class_reported": m4.INFO_CLASS_REPORTED,
           "certificate": {"available": True, "held": True, "gamma": 1.0, "kappa": None}, "certificate_case": "W(a)",
           "t_a": None, "aborted": False}
    rec.update(kw)
    return rec


def test_allowance_rule_check_by_hand():
    assert e7._rule_problems(_a8(), None) == []
    assert e7._rule_problems(_a8(B0_usd=m4.B0_SHARE * 200.0 * (1 + 1e-10)), None)          # B0 off by 1e-10 relative
    assert e7._rule_problems(_a8(kappa=10.0), None)
    assert e7._rule_problems(_a8(B0_rule=f"{mc.num_key(2 * m4.B0_SHARE)}*BL0a"), None)       # another share's rule
    assert e7._rule_problems(_a8(gamma=1.25), None)
    assert e7._rule_problems(_a8(B0_report_usd=1.0), None)
    assert e7._rule_problems(_a8(info_class_reported="online-I1 + a-priori N"), None)
    auto = _a8(B0_rule=m4.THEORY_RULE, kappa=10.0, B0_usd=3.0, B0_report_usd=3.0, info_class_reported="x",
               certificate={"available": True, "held": True, "gamma": 1.0, "kappa": 10.0})
    assert e7._rule_problems(auto, "auto") == [] and e7._rule_problems(auto, None)
    s0 = e7.ALLOW_B0[1]                                                     # the sweep's smallest share
    sw = _a8(B0_rule=f"{mc.num_key(s0)}*BL0a", B0_usd=s0 * 200.0, B0_report_usd=s0 * 200.0)
    assert e7._rule_problems(sw, s0) == [] and e7._rule_problems(sw, e7.ALLOW_B0[2])
    rows = [{"a8": _a8(), "bl0a_usd": 200.0, "policy_seed": 0, "job": "j", "c": 1, "b0": None},
            {"a8": _a8(), "bl0a_usd": 201.0, "policy_seed": 1, "job": "j", "c": 1, "b0": None}]
    ch = e7.check_allowance(rows)
    assert ch["status"] == "fail" and ch["n_failures"] == 1 and ch["failures"][0]["seed"] == 1
    assert e7.check_allowance(rows[:1])["status"] == "pass" and e7.check_allowance([])["status"] == "missing"


def test_combine_checks():
    local = {k: {"status": "pass"} for k in e7.PART_CHECKS["main"]}
    others = {p: {"checks": {k: {"status": "pass"} for k in e7.PART_CHECKS[p]}} for p in ("stress", "gap", "allow")}
    c = e7.combine_checks(local, others)
    assert list(c) == list(e7.CHECK_IDS)
    for k, v in c.items():
        assert v["status"] == ("informative" if k in e7.INFORMATIVE else "pass"), k
        assert set(v["parts"]) == {p for p in e7.PARTS if k in e7.PART_CHECKS[p]} and v["claim"] == e7.CHECK_CLAIMS[k]
    bad = copy.deepcopy(others)
    bad["gap"]["checks"]["E7-1"]["status"] = "fail"
    assert e7.combine_checks(local, bad)["E7-1"]["status"] == "fail"
    assert e7.combine_checks(local, {**others, "allow": None})["E7-7"]["status"] == "missing"
    assert e7.combine_checks(local, {**others, "allow": None})["E7-6"]["status"] == "missing"
    pend = copy.deepcopy(others)
    pend["stress"]["checks"]["E7-2"]["status"] = "pending"
    assert e7.combine_checks(local, pend)["E7-2"]["status"] == "pending"


def test_null_forms_keep_every_field():
    """An entry without runs keeps the fields of its non-null form, each null with its note (§2.6)."""
    for tag in ("Sublet", "BL5"):
        e = e7.cost_entry([], tag)
        assert e["n_runs"] == 0 and e["note"]
        for k in e7.ACC_FIELDS + ("saving_pct", "saving_pct_total") + e7.METRIC_FIELDS:
            assert e[k]["median"] is None and e[k]["median_note"] and e[k]["median_ci95"] == [None, None], k
        assert e["components_over_bl0a"] is None and e["gpu_hour_share"] is None
        assert e["fallback_share_after_reclaims"]["n_null"] == 0
        if tag == "Sublet":
            assert e["abort_share"] is None and e["t_a"] == [] and e["certificates"]["n"] == 0
        else:
            assert all(e[k] is None and e[k + "_note"] for k in ("abort_share", "t_a", "certificates"))
        s = e7.stress_entry([], tag)
        assert s["r0"] == {} and s["r0_mean"] is None and s["r0_mean_note"]
    a = e7.allow_cell([])
    assert a["B0_rule"] is None and a["cost_over_bl0a"]["by_seed"] == {} and a["cost_over_bl0a"]["median"] is None
    for k in ("total_over_bl0a", "own_share_of_total", "overflow_over_bl0b", "total_over_bl0b"):
        assert a[k]["median"] is None and a[k]["median_note"] and a[k]["by_seed"] == {}, k
    assert a["accountings"] == {} and a["kappa"] is None and a["kappa_note"]
    g = e7.gap_entry([], "Sublet")
    for k in e7.ACC_FIELDS + ("alg_usd", "ratio_LB"):
        assert g[k]["median"] is None and g[k]["median_note"], k
    lp = e7._lp_null("job e7:gap_lp:c=2 has no record")
    assert set(e7.LP_FIELDS) | {"file"} <= set(lp) and lp["size"] == {}
    assert all(lp[k] is None and lp[k + "_note"] for k in set(e7.LP_FIELDS) - {"size"})
    b = e7._bl0a_null("x")
    assert all(b[k] is None and b[k + "_note"] == "x" for k in e7.BL0A_FIELDS)
    # E7-11's table: no abort gives null slots with their note
    t = e7.abort_table({"g": [{"a8": _a8()}], "none": [{"a8": None}]})
    assert list(t) == ["g"] and t["g"]["t_a_first"] is None and t["g"]["t_a_first_note"] == "no abort"
    assert t["g"]["t_a_median"] is None and t["g"]["t_a_median_note"] == "no abort"
    # a null Table III cell carries the reason it is null, a cell with a value the caller's note
    assert e7._cell(e7._agg([], "no alignment"), "analytic, median over the alignments")["note"] == "no alignment"
    assert e7._cell(e7._agg([2.0], "no alignment"), "analytic")["note"] == "analytic"
    assert e7._cell(None, "gap/summary.json missing")["note"] == "gap/summary.json missing"
    json.dumps(mc.jsonable([e7.cost_entry([], "A7G"), e7.stress_entry([], "A6"), a, g, lp, b, t]), allow_nan=False)


# ---------------------------------------------------------------- the checks' fail paths on hand-made records
def _row(tag="BL5", seed=0, c=1, **kw):
    r = {"tag": tag, "policy_seed": seed, "c": c, "job": f"j:{tag}", "a8": None, "ALG": 100.0,
         "accountings": {"overflow_usd": 100.0, "total_usd": 150.0}, "own_capacity_usd": 50.0,
         "n_invariant_failures": 0, "gpu_only_lease_slots": 0, "plan_class_p1": True, "ratio_validity": None,
         "instance_hash": "ih1", "schedule_hash": "sh1", "lb": {"ratio_LB": 1.5}}
    r.update(kw)
    return r


def test_certificate_clean_and_accounting_checks_fail_paths():
    def cert(case, held, available=True):
        return {"a8": _a8(certificate_case=case, certificate={"available": available, "held": held})}
    ok = [_row("Sublet", 0, **cert("W(a)", True)), _row("Sublet", 1, **cert("W(b)", True))]
    assert e7.check_certificates(ok)["status"] == "pass" and e7.check_certificates([_row()])["status"] == "missing"
    for case in m4.PROVEN_CASES:                                # a proven case not held is a bug
        ch = e7.check_certificates(ok + [_row("Sublet", 2, **cert(case, False))])
        assert ch["status"] == "fail" and ch["n_failures"] == 1 and ch["failures"][0]["case"] == case
    ch = e7.check_certificates(ok + [_row("Sublet", 2, **cert("W(c)", False))])    # W(c) counted, not a failure
    assert ch["status"] == "pass" and ch["n_w_c"] == 1 and ch["certificates"]["by_case"]["W(c)"]["runs"] == 1
    ch = e7.check_certificates(ok + [_row("Sublet", 2, **cert("unavailable", None, available=False))])
    assert ch["status"] == "fail" and ch["n_unavailable"] == 1
    # E7-2: an invariant failure or a GPU-only lease slot, also in a BL2 sub-run
    assert e7.check_clean([_row()])["status"] == "pass" and e7.check_clean([])["status"] == "missing"
    assert e7.check_clean([_row(n_invariant_failures=1)])["status"] == "fail"
    assert e7.check_clean([_row(gpu_only_lease_slots=2)])["n_gpu_only"] == 1
    assert e7.check_clean([_row("BL2", sub_runs=[{"n_invariant_failures": 0, "gpu_only_lease_slots": 0},
                                                 {"n_invariant_failures": 3, "gpu_only_lease_slots": 0}])]
                          )["status"] == "fail"
    assert e7.check_clean([_row("BL2", sub_runs=[{"n_invariant_failures": 0, "gpu_only_lease_slots": 1}])]
                          )["status"] == "fail"
    # E7-4: total - overflow = own capacity (1e-9 relative), overflow = ALG, BL0a's total accounting
    assert e7.check_accounting([_row()])["status"] == "pass"
    assert e7.check_accounting([_row(own_capacity_usd=50.0 * (1 + 1e-8))])["status"] == "fail"
    assert e7.check_accounting([_row(ALG=100.5)])["status"] == "fail"
    assert e7.check_accounting([_row(own_capacity_usd=None)])["status"] == "fail"
    refs = {"1": {"bl0a_usd": 200.0, "own_capacity_usd": 50.0, "bl0a_total_usd": 250.0}}
    assert e7.check_accounting([_row()], refs)["status"] == "pass"
    bad = e7.check_accounting([_row()], {"1": {**refs["1"], "bl0a_total_usd": 251.0}})
    assert bad["status"] == "fail" and bad["reference_failures"][0]["c"] == "1"


def test_gap_check_fail_paths():
    lps = {1: {"status": 0, "grid": e7.GAP_GRID, "instance_hash": "ih1", "schedule_hash": "sh1"}}
    base = [_row("Sublet", 0), _row("BL5", 1)]
    assert e7.check_gap(base, lps, (1,))["status"] == "pass"
    below = 1.0 - 10 * e7.P1_TOL
    ch = e7.check_gap(base + [_row("BL2", 2, lb={"ratio_LB": 0.9})], lps, (1,))          # BL2 is exempt (§3.8)
    assert ch["status"] == "pass" and ch["bl2_exempt"] is True
    ch = e7.check_gap(base + [_row("BL5", 2, lb={"ratio_LB": below})], lps, (1,))        # a P1 run below the LP
    assert ch["status"] == "fail" and ch["p1_below"][0]["tag"] == "BL5"
    assert e7.check_gap(base + [_row("BL5", 2, plan_class_p1=False, lb={"ratio_LB": 0.9})], lps, (1,)
                        )["status"] == "pass"                                             # not in plan class P1
    assert e7.check_gap(base + [_row("A6", 2, lb={"ratio_LB": 1.0 - 0.5 * e7.P1_TOL})], lps, (1,)
                        )["status"] == "pass"                                             # within the tolerance
    for lp in ({**lps[1], "status": 1}, {**lps[1], "grid": "fast"}):
        ch = e7.check_gap(base, {1: lp}, (1,))
        assert ch["status"] == "fail" and len(ch["lp_not_optimal"]) == 2
    assert e7.check_gap(base, {1: {**lps[1], "schedule_hash": "sh0"}}, (1,))["hash_mismatch"]
    assert e7.check_gap(base, {1: {**lps[1], "instance_hash": "ih0"}}, (1,))["status"] == "fail"
    assert e7.check_gap([_row(ratio_validity="fast grid")], lps, (1,))["status"] == "fail"
    two = e7.check_gap([_row("BL5", 0), _row("BL1", 0, schedule_hash="sh2")], lps, (1,))
    assert two["status"] == "fail" and two["alignments_with_several_schedules"]
    assert e7.check_gap(base, {}, (1,))["status"] == "missing" and e7.check_gap([], lps, (1,))["status"] == "missing"
    # BL2's sub-run schedules are compared one by one
    assert e7.check_gap([_row("BL2", schedule_hash=None, schedule_hashes=["sh1", "sh9"])], lps, (1,)
                        )["status"] == "fail"


def _write_ok(folder, part, jid, runs):
    mc.dump_json({"job": jid, "status": "ok"}, mc.record_path(folder, jid))
    mc.dump_json({"runs": runs}, e7.run_path(folder, part, jid))


def test_reproduction_check_and_part_summaries(tmp_path):
    """E7-7 seed by seed (totals equal to 1e-9 USD) against main's and stress's 'ok' outputs, and part_summary: a
    part summary whose e7:summary record is not 'ok' is not used."""
    root = tmp_path / "e7"
    main_dir, stress_dir = root / "main", root / "stress"
    seeds = (0, 1)
    files = {}
    for i, mode in enumerate(e7.allow_modes()):
        tot = {s: 1000.0 + 10 * i + s for s in seeds}
        if mode == "L-tr":
            _write_ok(main_dir, "main", e7.main_id("Sublet", e7.MU_MAIN, e7.STRESS_C),
                      [{"policy_seed": s, "ALG": tot[s]} for s in seeds])
        else:
            _write_ok(stress_dir, "stress", e7.stress_id(mode, "Sublet"),
                      [{"policy_seed": s, "ALG": tot[s]} for s in seeds])
        files[e7.allow_id(m4.B0_SHARE, mode)] = {"runs": [{"policy_seed": s, "ALG": tot[s]} for s in seeds]}
    ch = e7.check_reproduction(files, main_dir, stress_dir)
    assert ch["status"] == "pass" and ch["n_pairs"] == 2 * len(e7.allow_modes()) and not ch["missing"]
    bad = copy.deepcopy(files)
    bad[e7.allow_id(m4.B0_SHARE, "L-co")]["runs"][1]["ALG"] += 1e-6
    ch = e7.check_reproduction(bad, main_dir, stress_dir)
    assert ch["status"] == "fail" and [(p["mode"], p["seed"]) for p in ch["failures"]] == [("L-co", 1)]
    short = copy.deepcopy(files)
    short[e7.allow_id(m4.B0_SHARE, "L-eg")]["runs"].pop()
    assert e7.check_reproduction(short, main_dir, stress_dir)["status"] == "missing"
    # a reference whose job record is not 'ok' is not used
    jid = e7.stress_id("L-ss", "Sublet")
    mc.dump_json({"job": jid, "status": "error"}, mc.record_path(stress_dir, jid))
    ch = e7.check_reproduction(files, main_dir, stress_dir)
    assert ch["status"] == "missing" and {"mode": "L-ss", "allow_file": True, "reference_file": False} in ch["missing"]
    # part_summary
    mc.dump_json({"meta": {"part": "gap"}, "checks": {}}, root / "gap" / "summary.json")
    s, why, ign = e7.part_summary(root, "gap")
    assert s == {"meta": {"part": "gap"}, "checks": {}} and why is None and ign is None      # no record: used
    sid = mc.job_id("e7", "summary")
    for st in ("ok", "error", "running"):
        mc.dump_json({"job": sid, "status": st}, mc.record_path(root / "gap", sid))
        s, why, ign = e7.part_summary(root, "gap")
        if st == "ok":
            assert s is not None and why is None and ign is None
        else:
            assert s is None and repr(st) in why and ign == {"job": sid, "part": "gap", "status": st,
                                                             "output": "gap/summary.json"}
    s, why, ign = e7.part_summary(root, "allow")
    assert s is None and "missing" in why and ign is None
    c = e7.combine_checks({}, {"gap": None}, {"gap": why})
    assert c["E7-3"]["status"] == "missing" and c["E7-3"]["parts"]["gap"]["note"] == why


# ---------------------------------------------------------------- instances (§3.4, §3.7)
def _week(n=None, mode="L-tr", c=1):
    from sublet.drivers.run import build
    return build(e7.week_spec("BL0a", {}, mode=mode, n=n, c=c), c)


@pytest.mark.needs_a12
def test_week_instance_and_routing_graphs():
    rec = json.loads((MS4SPEC / "e7f_week_case_Sublet.json").read_text())
    inst, model, ecfg = _week()
    kinds = [s.kind for s in inst.sites]
    assert (inst.m, kinds.count("layer"), kinds.count("protected"), inst.K, inst.n) == (169, 164, 5, 21, 15)
    assert (inst.grid.T_slow, inst.grid.T_fast) == (2016, 10080) and ecfg.check_invariants
    assert (model.schedule, model.information, model.on_unavailable, model.violations) == ("trace", "I1", "sell",
                                                                                           "absorb")
    refs = m4.references(inst)
    assert_rel(refs["bl0a_usd"], rec["references"]["bl0a_analytic_usd"], 1e-9, "BL0a")
    assert_rel(refs["own_capacity_usd"], rec["references"]["own_capacity_usd"], 1e-9, "own capacity")
    s7 = sorted(sorted(e) for e in e7.cross_region_arcs(inst))
    from sublet.config import DEFAULT_ADJACENCY
    assert s7 == sorted(sorted(e) for e in DEFAULT_ADJACENCY)
    for n in e7.LINKS:
        sub = _week(n=n)[0]
        meas = json.loads((MS4SPEC / f"allowance_need_ms4_e7_links{n}.json").read_text())       # measurement 9
        assert e7.cross_region_arcs(sub) == sorted(sorted(e) for e in m4.ROUTING_LINKS[n]) == \
            meas["cross_region_arcs"], n
        assert bl0a_all(sub) == bl0a_all(inst) and np.array_equal(sub.clients.demand, inst.clients.demand)
        assert_rel(bl0a_all(sub), meas["need"]["bl0a_usd"], 1e-9, f"BL0a at n = {n}")
        assert [(s.id, s.capacity_gpus) for s in sub.sites] == [(s.id, s.capacity_gpus) for s in inst.sites]


@pytest.mark.needs_a12
def test_stress_modes_resolve_at_a_week():
    from sublet.lender import resolve_params
    inst = _week()[0]
    for mode in m4.stress_modes():
        model = _week(mode=mode)[1]
        got = resolve_params(inst, model)
        want = json.loads((MS4SPEC / f"e7f_week_stress_Sublet_{mode}.json").read_text())["lender_params_resolved"]
        assert json.loads(json.dumps(mc.jsonable(got))) == want, mode
    assert resolve_params(inst, _week(mode="L-ss")[1])["Phi"] == 84
    for mode in ("L-iid-0.05", "L-iid-0.2"):
        assert resolve_params(inst, _week(mode=mode)[1])["U"] == 2016


@pytest.mark.needs_a12
def test_gap_instance_menu_and_ratio_validity():
    from sublet.drivers.run import ratio_validity
    est = json.loads((MS4SPEC / "e7r_h5_lp_estimate.json").read_text())
    for c in e7.ALIGNMENTS:
        inst, model, ecfg, info = m4.gap_instance(c)
        assert [k.id for k in inst.contracts] == ["s5_tau5_H5", "s5_tau5_H60", "s5_tau60_H0", "protected"]
        assert ratio_validity(e7.GAP_GRID, inst, model) is None and ecfg.check_invariants, c
        assert info["demand"] == "e7_week_day1" and info["bl0a_usd"] == bl0a_all(inst)
        if c == 1:
            assert inst.m == est["instance"]["n_sites"] == 173 and inst.n == 15 and inst.grid.T_slow == 288


# ---------------------------------------------------------------- reduced jobs of every part end to end
E2E_JOBS = ("e7:main:pol=Sublet:mu=1:c=1", "e7:main:pol=BL5:mu=1:c=1", "e7:main:pol=BL2:mu=1:c=1",
            "e7:links:n=0:pol=BL5:c=1", "e7:stress:mode=L-eg:pol=Sublet", "e7:stress:mode=L-eg:pol=BL5",
            e7.allow_id(m4.B0_SHARE, "L-tr"), e7.allow_id(m4.B0_SHARE, "L-eg"), "e7:allow:b0=auto:mode=L-tr",
            "e7:gap_lp:c=1", "e7:gap_run:pol=Sublet:c=1", "e7:gap_run:pol=BL2:c=1")


def _backup(*files) -> dict:
    return {f: f.read_bytes() for f in files}


def _restore(keep: dict) -> None:
    for f, b in keep.items():
        f.write_bytes(b)


@pytest.fixture(scope="module")
def e2e(tmp_path_factory):
    """The jobs of E2E_JOBS (reduced list, 1-hour horizon) run through ms3_common.run_job into <tmp>/e7/<part>, then
    the summaries of the four parts in pass-2 order."""
    mp = pytest.MonkeyPatch()
    mp.setenv(e7.REDUCED_ENV, "1")
    mp.delenv("E7_PART", raising=False)
    mp.setattr(e7, "REDUCED_HORIZON_MIN", 60)
    root = tmp_path_factory.mktemp("e7run") / "e7"
    js = {j.id: j for j in e7.jobs_all()}
    recs = {}
    for jid in E2E_JOBS:
        j = js[jid]
        out = root / j.params["part"]
        recs[jid] = mc.run_job("e7", j, lambda o, j=j, out=out: e7.run(j, o, out), out, resume=False)
    summ = {p: e7.SUMMARIES[p](root / p) for p in e7.PASS_SUMMARIES}
    yield {"root": root, "recs": recs, "summ": summ, "jobs": js, "mp": mp}
    mp.undo()


@pytest.mark.needs_a12
@pytest.mark.slow
def test_e2e_records_and_runs(e2e):
    root = e2e["root"]
    for jid, rec in e2e["recs"].items():
        assert rec["status"] == "ok" and rec["n_errors"] == 0, (jid, rec.get("error"), rec.get("errors"))
        assert rec["git_revision"] is not None
    n_a8 = 0
    for jid in E2E_JOBS:
        part = e2e["jobs"][jid].params["part"]
        f = json.loads(e7.run_path(root / part, part, jid).read_text())
        assert f["meta"]["git_revision"] and f["horizon_min"] == 60 and f["meta"]["reduced"] is True
        for r in f["runs"]:
            acc = r["accountings"]
            assert set(m4.accountings(1.0, None, {"bl0a_usd": 1.0, "own_capacity_usd": 1.0, "bl0b_overflow_usd": 1.0,
                                                  "bl0b_total_usd": 1.0})) <= set(acc)
            assert acc["overflow_usd"] == r["ALG"] and r["bl0a_usd"] == f["references"]["bl0a_usd"]
            assert_rel(acc["total_usd"] - acc["overflow_usd"], r["own_capacity_usd"], 1e-9, "E7-4")
            assert r["n_invariant_failures"] == 0 and r["gpu_only_lease_slots"] == 0
            if r["a8"] is None:
                continue
            n_a8 += 1
            a = r["a8"]
            assert a["certificate"]["available"] and a["certificate_case"] in m4.CASES
            if f.get("b0") == "auto":
                assert a["B0_rule"] == m4.THEORY_RULE and a["kappa"] == 10.0
            else:
                assert a["B0_rule"] == m4.B0_RULE and a["kappa"] is None and a["gamma"] == 1.0
                assert a["B0_usd"] == m4.B0_SHARE * f["references"]["bl0a_usd"] == a["B0_report_usd"]
                assert a["info_class_reported"] == m4.INFO_CLASS_REPORTED
                assert a["info_class"] == "online-I1 + a-priori N"
    assert n_a8 == 6
    bl2 = json.loads(e7.run_path(root / "main", "main", "e7:main:pol=BL2:mu=1:c=1").read_text())["runs"][0]
    assert bl2["runner"] == "siloed" and bl2["n_sub_runs"] == len(bl2["sub_runs"]) > 1
    assert_rel(sum(s["total"] for s in bl2["sub_runs"]), bl2["ALG"], 1e-9, "BL2's summed sub-runs")
    lk = json.loads(e7.run_path(root / "main", "main", "e7:links:n=0:pol=BL5:c=1").read_text())
    assert lk["cross_region_arcs"] == [] and lk["cross_region_links"] == [] and \
        lk["references"]["bl0a_usd"] == json.loads(e7.run_path(root / "main", "main", "e7:main:pol=BL5:mu=1:c=1")
                                                   .read_text())["references"]["bl0a_usd"]


@pytest.mark.needs_a12
@pytest.mark.slow
def test_e2e_gap(e2e):
    root, s = e2e["root"], e2e["summ"]["gap"]
    lp = json.loads(e7.lp_path(root / "gap", 1).read_text())
    for k in ("method", "benchmark", "grid", "status", "status_msg", "objective", "dual_bound", "gap", "size",
              "build_s", "solve_s", "peak_rss_mb", "git_revision", "time_limit_s", "instance_hash", "schedule_hash"):
        assert k in lp, k
    assert lp["grid"] == "slow" and lp["status"] == 0 and lp["time_limit_s"] == 1500.0 and lp["merged_sites"] < 173
    assert s["lp"]["1"]["status"] == 0 and s["lp"]["1"]["file"] == "lb/lp_c1.json"
    for t in ("Sublet", "BL2", "BL0a"):
        e = s["runs"][t]
        assert e["n_runs"] == 1 and e["n_ratio"] == 1 and e["ratio_LB"]["median"] > 0, t
        assert e["ratio_validity"] == [None]
        for k in e7.ACC_FIELDS:                                 # both accountings (§2.6)
            assert e[k]["median"] is not None, (t, k)
        assert e["overflow_usd"]["median"] == e["alg_usd"]["median"]
    assert set(s["lp"]["1"]) >= set(e7.LP_FIELDS) and set(s["bl0a_by_alignment"]) == {"1"}
    e10 = s["checks"]["E7-10"]
    meds = [v for v in e10["ratio_LB_median"].values() if v is not None]
    assert e10["ratio_LB_median_range"] == [min(meds), max(meds)] and "2.02" not in e10["label"]
    assert s["runs"]["A6"]["n_runs"] == 0 and s["runs"]["A6"]["ratio_LB"]["median"] is None
    b = s["bl0a_by_alignment"]["1"]
    assert b["rel_diff"] <= 1e-9 and b["analytic_usd"] == lp["bl0a_analytic_usd"]
    for k in ("E7-3", "E7-5", "E7-1", "E7-2", "E7-4", "E7-6"):
        assert s["checks"][k]["status"] == "pass", (k, s["checks"][k])
    assert set(s["checks"]) == set(e7.PART_CHECKS["gap"])
    # an LP of another schedule (an output of an earlier run) is not used, and E7-3 fails on the hash
    p = e7.lp_path(root / "gap", 1)
    keep = _backup(p, root / "gap" / "summary.json", root / "gap" / "tables.md")
    p.write_text(json.dumps({**lp, "schedule_hash": "0" * 64}))
    try:
        s2 = e7.summary_gap(root / "gap")
        assert s2["checks"]["E7-3"]["status"] == "fail" and s2["checks"]["E7-3"]["hash_mismatch"]
        assert s2["runs"]["Sublet"]["n_ratio"] == 0
    finally:
        _restore(keep)


@pytest.mark.needs_a12
@pytest.mark.slow
def test_e2e_main_stress_allow_and_table3(e2e):
    root, S = e2e["root"], e2e["summ"]
    m = S["main"]
    full = m["runs"]["1"]["Sublet"]
    assert full["n_runs"] == 1 and full["alignments"] == [1]
    for k in ("overflow_over_bl0a", "total_over_bl0a", "overflow_usd", "total_usd", "saving_pct", "saving_pct_total"):
        assert full[k]["median"] is not None and "mean" in full[k], k
    assert set(full["components_over_bl0a"]) == set(e7.COMPONENT_KEYS)
    assert_rel(full["components_over_bl0a"]["total"], full["overflow_over_bl0a"]["median"], 1e-12, "components")
    assert "n_null" in full["fallback_share_after_reclaims"] and full["certificates"]["n"] == 1
    assert isinstance(full["t_a"], list) and full["info_class_reported"] == [m4.INFO_CLASS_REPORTED]
    assert m["runs"]["1"]["BL5"]["abort_share"] is None and m["runs"]["1"]["BL5"]["abort_share_note"]
    assert {k for k in e7.cost_entry([], "Sublet") if not k.endswith("note")} == \
        {k for k in full if not k.endswith("note")}                           # the null form keeps every field
    assert m["links"]["0"]["BL5"]["n_runs"] == 1 and set(m["links"]) == {"0", "2", "3"}
    assert m["meta"]["reduced"] is True and m["meta"]["bl0a_usd"]["1"] > 0 and m["meta"]["B0_rule"] == m4.B0_RULE
    assert m["meta"]["bl0b_overflow_usd"]["1"] > 0 and m["meta"]["bl0b_total_usd"]["1"] > 0
    assert list(m["checks"]) == list(e7.CHECK_IDS)
    for k in ("E7-1", "E7-2", "E7-3", "E7-4", "E7-5", "E7-6"):
        assert m["checks"][k]["status"] == "pass", (k, m["checks"][k]["part_status"])
    assert m["checks"]["E7-7"]["status"] == "missing"          # the sweep's other modes did not run here
    assert m["checks"]["E7-9"]["parts"]["main"]["one_bl0a_per_alignment"] is True
    # stress: W0 needs the five modes, so with L-eg only it is null with value_partial
    st = S["stress"]
    w = st["W0"]["Sublet"]
    assert w["value"] is None and w["value_note"] and w["value_partial"] == st["modes"]["L-eg"]["Sublet"]["r0_mean"]
    assert set(w["modes_missing"]) == set(m4.stress_modes()) - {"L-eg"}
    assert st["modes"]["L-eg"]["Sublet"]["certificates"]["n"] == 1 and st["modes"]["L-eg"]["BL5"]["aborted"] is None
    # allow: the 10% runs reproduce the main and stress Sublet runs (E7-7's pairs); BL5 from main's runs
    al = S["allow"]
    pairs = al["checks"]["E7-7"]["pairs"]
    assert {(p["mode"], p["seed"]) for p in pairs} == {("L-tr", 0), ("L-eg", 0)}
    assert all(p["abs_diff"] <= 1e-9 for p in pairs) and not al["checks"]["E7-7"]["failures"]
    cell = al["cells"][e7.b0_key(m4.B0_SHARE)]["L-tr"]
    assert cell["B0_rule"] == m4.B0_RULE and cell["kappa"] is None and cell["kappa_note"]
    assert cell["cost_over_bl0a"]["by_seed"]["0"] is not None
    assert set(cell["accountings"]["0"]) >= set(e7.ACC_FIELDS)              # both accountings (§2.6)
    for k in ("total_over_bl0a", "own_share_of_total", "overflow_over_bl0b", "total_over_bl0b"):
        assert cell[k]["by_seed"]["0"] == cell["accountings"]["0"][k] == cell[k]["median"], k
    assert cell["cost_over_bl0a"]["median"] == cell["accountings"]["0"]["overflow_over_bl0a"]
    assert al["cells"]["auto"]["L-tr"]["B0_rule"] == m4.THEORY_RULE and al["meta"]["b0_auto_usd"] > 0
    assert_rel(al["meta"]["kappa10_cap_usd"], 10.0 * al["meta"]["c_min_sum_usd"], 1e-12, "kappa cap")
    assert al["bl5"]["L-tr"] == m["runs"]["1"]["BL5"]["overflow_over_bl0a"]["median"]
    assert al["bl5"]["W0"] is None and al["bl5"]["W0_note"]
    assert al["checks"]["E7-6"]["status"] == "pass" and al["checks"]["E7-6"]["sweep"] is True
    # table3.json: Table III's rows, labels and the sha256 of each part summary it read
    t3 = json.loads((root / "table3.json").read_text())
    assert t3["order"] == list(e7.TABLE3_ROWS) and list(t3["rows"]) == list(e7.TABLE3_ROWS)
    assert t3["labels"]["A7G"] == "PD heuristic + guard" and t3["labels"]["BL0a"] == "All-fallback"
    for p in e7.PARTS:
        src = t3["meta"]["sources"][p]
        assert src["exists"] and src["sha256"] == hashlib.sha256((root / p / "summary.json").read_bytes()).hexdigest()
    r = t3["rows"]
    assert r["Sublet"]["usd"]["overflow"]["median"] == full["overflow_usd"]["median"]
    assert r["Sublet"]["gap"]["median"] == S["gap"]["runs"]["Sublet"]["ratio_LB"]["median"]
    assert r["BL0b"]["gap"]["median"] is None and r["BL0b"]["gap"]["note"]
    assert r["BL0a"]["W0"]["median"] == 1.0 and r["BL0a"]["saving_pct"]["median"] == 0.0
    assert r["BL0a"]["usd"]["overflow"]["median"] == m["meta"]["bl0a_usd"]["1"]
    assert r["BL5"]["abort_share"]["median"] is None and r["Sublet"]["abort_share"]["median"] in (0.0, 1.0)
    for row in r.values():
        for k in ("saving_pct", "gap", "fallback_share_after_reclaims", "W0", "abort_share"):
            assert set(row[k]) == {"median", "interval", "n", "note"}, k
    cap = t3["caption"]
    assert cap["B0_rule"] == m4.B0_RULE and cap["certificates"]["n"] == 6 and cap["certificates"]["failures"] == 0
    assert cap["own_capacity_usd"]["by_alignment"]["1"] == m["meta"]["own_capacity_usd"]["1"]
    assert t3["meta"]["git_revision"] and t3["meta"]["reduced"] is True
    # an output whose job record is not 'ok' is not used (§2.6)
    jp = mc.record_path(root / "main", "e7:main:pol=Sublet:mu=1:c=1")
    keep = _backup(jp, root / "main" / "summary.json", root / "main" / "tables.md", root / "table3.json")
    jp.write_text(json.dumps({**json.loads(jp.read_text()), "status": "error"}))
    try:
        s2 = e7.summary_main(root / "main")
        assert s2["runs"]["1"]["Sublet"]["n_runs"] == 0 and s2["runs"]["1"]["Sublet"]["note"]
        assert [x["job"] for x in s2["meta"]["ignored_outputs"]] == ["e7:main:pol=Sublet:mu=1:c=1"]
        t3b = json.loads((root / "table3.json").read_text())
        assert t3b["rows"]["Sublet"]["usd"]["overflow"]["median"] is None
    finally:
        _restore(keep)
    # a part summary whose e7:summary record is not 'ok' (a failed summary job; the file an earlier run's) is not used
    sp = mc.record_path(root / "gap", mc.job_id("e7", "summary"))
    assert not sp.exists()
    keep = _backup(root / "main" / "summary.json", root / "main" / "tables.md", root / "table3.json")
    mc.dump_json({"job": mc.job_id("e7", "summary"), "status": "error"}, sp)
    try:
        s3 = e7.summary_main(root / "main")
        assert s3["checks"]["E7-3"]["status"] == "missing" and s3["checks"]["E7-3"]["part_status"] == {"gap": "missing"}
        assert "'error'" in s3["checks"]["E7-3"]["parts"]["gap"]["note"]
        assert {"job": "e7:summary", "part": "gap", "status": "error", "output": "gap/summary.json"} in \
            s3["meta"]["ignored_outputs"]
        t3c = json.loads((root / "table3.json").read_text())
        assert t3c["meta"]["sources"]["gap"]["used"] is False and t3c["meta"]["sources"]["gap"]["used_note"]
        assert t3c["rows"]["Sublet"]["gap"]["median"] is None and "'error'" in t3c["rows"]["Sublet"]["gap"]["note"]
        assert t3c["caption"]["certificates"]["parts_counted"]["gap"] is False
        assert t3c["meta"]["sources"]["stress"]["used"] is True
    finally:
        sp.unlink()
        _restore(keep)
