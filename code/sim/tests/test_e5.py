"""Tests of the E5 driver (design/sim_spec_ms4.md §5, §10 row test_e5.py).

Quick (no raw data, no a12 outputs):
- the grid of §5.5: 364 pool jobs (280 at mu / beta~ = 1, 84 at the default point trace / short), ids
  e5:run:level=L:menu=M:pol=P:mu=U:c=C, the reduced list (alignment 1, policy seed 0, one day);
- the short and long menus by a11's contract classes (spot-like, AEP-82-like), tau and H from a11, the config's
  protected contract in both; the correlation levels' lender models (L-co for all1); the tags, their registry ids,
  parameters and style keys (the keys of figs/style.py SUPP_POLICIES_MS4['sf_e5']); Sublet's parameters are M36's
  ms4_common.sublet_params (no typed B0);
- the checks E5-1, E5-2, E5-3, E5-5 on hand-made run rows (pass, fail, unchecked, vacuous, a run lost to an error),
  E5-6's counts per (level, menu) and per mu against a5b's threshold, and E5-4's Pareto rule and the A6 identity on
  hand-made cells; the null form of a cell without runs keeps the fields of a cell with runs; the summary of a
  hand-made out folder with one errored run lists it in meta.run_errors and fails E5-1 and E5-5; run_e5.sh parses.
With the a12 outputs (needs_a12), on bench_e7r at alignment 1:
- the long menu's instance carries the short menu's demand and borrower_stats (one BL0a, bl0a_own_demand the
  builder's own, the Gamma notes of the demand used), its own contracts and sites; the level does not change the
  instance; carry_demand refuses a mismatched client list;
- the levels resolve on the instance (delay_slots_max 1, groups null or 'all');
- check E5-2 on a short horizon (6 h): A6-rule and A6-always2 on the long menu under trace and all1 have n_exp_total 0
  and buys 0, with max lam_s at most 3600 s; E5-3 on an exposed run (the short menu's A6-always2 under trace at
  mu / beta~ = 0.2: spares bought or no site, not vacuous); each tag's parameters reach its policy (BL3's n_extra,
  A6's redundancy mode); a Sublet job's B0 is B0_SHARE x e6.bl0a_all of the job's own instance with B0_RULE, kappa
  None, gamma 1, its certificate held; the summary of these jobs has every key of §5.6 and every check of §5.7.
"""
import dataclasses
import json
import subprocess

import numpy as np
import pytest

from fixtures import SIM, assert_rel

from sublet.experiments import e5
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms4_common as m4
from sublet.experiments import q44_study as q44

SHORT_HZ = 360                         # 6 h: the short horizon of the needs_a12 runs


# ---------------------------------------------------------------- quick
def test_grid_and_job_ids(monkeypatch):
    monkeypatch.delenv(e5.REDUCED_ENV, raising=False)
    js = e5.jobs()
    mc.check_jobs(js)
    assert len(js) == 364 and all(j.kind == "pool" for j in js)
    at1 = [j for j in js if j.params["mu"] == 1.0]
    assert len(at1) == 5 * 2 * 7 * 4 == 280
    other = [j for j in js if j.params["mu"] != 1.0]
    assert len(other) == 3 * 7 * 4 == 84
    assert {(j.params["level"], j.params["menu"]) for j in other} == {e5.DEFAULT_POINT}
    assert {j.params["mu"] for j in other} == {0.2, 0.5, 2.0}
    assert sum(len(j.params["policy_seeds"]) for j in js) == 1092
    j = js[0]
    assert j.id == "e5:run:level=trace:menu=short:pol=A6-off:mu=1:c=1"
    exp, part, kv = mc.parse_job_id(j.id)
    assert (exp, part) == ("e5", "run") and set(kv) == {"level", "menu", "pol", "mu", "c"}
    assert {kv["level"] for kv in (mc.parse_job_id(x.id)[2] for x in js)} == set(e5.LEVELS)
    assert all(x.params["horizon_min"] == e5.WEEK_MIN and x.est_s > 0 for x in js)
    for x in js:                       # §5.5: BL3 under all1 at A8's time per week run, else EST_RUN_S
        pid = e5.TAGS[x.params["tag"]][0]
        want = e5.EST_RUN_S["A8"] if (pid, x.params["level"]) == ("BL3", "all1") else e5.EST_RUN_S[pid]
        assert x.est_s == pytest.approx(3 * want)
    monkeypatch.setenv(e5.REDUCED_ENV, "1")
    red = e5.jobs()
    assert len(red) == 91 and {x.params["c"] for x in red} == {1}
    assert all(x.params["policy_seeds"] == [0] and x.params["horizon_min"] == 1440 for x in red)


def test_menus_by_a11_class():
    a11 = json.loads((SIM.parents[1] / "code" / "analysis" / "out" / "a11_calibration.json").read_text())["contracts"]
    cfg = json.loads((SIM / "configs" / "bench_e7r.json").read_text())
    prot = next(c for c in cfg["contracts"] if c["id"] == "protected")
    for menu, cls in (("short", "spot-like"), ("long", "AEP-82-like")):
        cs = e5.menu_contracts(menu)
        assert [c["id"] for c in cs] == list(e5.MENUS[menu]) + ["protected"] and cs[-1] == prot
        for c in cs[:-1]:
            assert a11[c["id"]]["class"] == cls == e5.MENU_CLASS[menu]
            assert (c["tau_min"], c["H_min"]) == (a11[c["id"]]["tau_min"], a11[c["id"]]["H_min"]) and c["tau_min"] == 5
        assert set(e5.menu_classes(menu).values()) == {cls}
        ov = e5.overrides(menu, 0.5)
        assert ov["lender_defaults.menu"] == list(e5.MENUS[menu]) and ov["time.horizon_min"] == 10080
        assert ov["time.fast_slot_min"] == 1 and ov["stranding.mu_over_beta_tilde"] == 0.5
    assert [a11[k]["H_min"] for k in e5.MENUS["short"]] == [0, 1, 2]
    assert [a11[k]["H_min"] for k in e5.MENUS["long"]] == [60, 120, 240]
    with pytest.raises(ValueError):
        e5.menu_contracts("medium")


def test_levels_and_tags():
    from figs import style
    assert e5.level_lender_model("trace") == {}
    for lv, p in (("sh0.25", 0.25), ("sh0.5", 0.5), ("sh1", 1.0)):
        assert e5.level_lender_model(lv) == {"schedule": "correlated", "params": {"p_sh": p, "groups": None}}
    assert e5.level_lender_model("all1") == q44.MODES["L-co"]["lender_model"]
    with pytest.raises(ValueError):
        e5.level_lender_model("sh0.75")
    assert set(e5.TAGS) == {"A6-off", "A6-rule", "A6-always2", "BL3-0", "BL3-1", "BL3-2", "Sublet"}
    assert {t: v[0] for t, v in e5.TAGS.items()} == {"A6-off": "A6", "A6-rule": "A6", "A6-always2": "A6",
                                                       "BL3-0": "BL3", "BL3-1": "BL3", "BL3-2": "BL3", "Sublet": "A8"}
    assert e5.TAGS["A6-off"][1] == {"redundancy": "off"} and e5.TAGS["A6-rule"][1] == {}
    assert e5.TAGS["A6-always2"][1] == {"redundancy": "always2"}
    assert [e5.TAGS[t][1] for t in e5.BL3_TAGS] == [{"n_extra": 0}, {"n_extra": 1}, {}]
    assert e5.TAGS["Sublet"][1] is None            # M36: ms4_common.sublet_params of each job's instance
    keys = [v[2] for v in e5.TAGS.values()]
    # C47: the driver keeps the style key 'sublet' that its run records carry (A8 around the lagged BL5 at MS4's
    # allowance); since the MS6 gate's C46, sf_e5 draws that policy as sublet_ms4 (design/ms6_spec.md M2, M4)
    drawn = {"sublet_ms4" if k == "sublet" else k for k in keys}
    assert drawn == set(style.SUPP_POLICIES_MS4["sf_e5"]) and all(k in style.POLICIES for k in keys)


def _row(job, tag, menu="long", level="trace", mu=1.0, *, n_exp=0, buys=0, no_site=0, lam_ok=True, inv=0,
         gpu=0, case=None, held=None, n_exp_max=None):
    r = {"job": job, "tag": tag, "menu": menu, "level": level, "mu": mu, "c": 1, "policy_seed": 0,
         "n_invariant_failures": inv, "invariant_first": [], "gpu_only_lease_slots": gpu,
         "instance": {"lam_s": {"S": [60.0, 64.0], "L": [95.0, 3700.0 if not lam_ok else 239.0]},
                      "lam_s_max_ok": lam_ok}}
    if e5.TAGS[tag][0] == "A6":
        r["redundancy"] = {"n_exp_total": n_exp, "buys": buys, "no_site": no_site,
                           "n_exp_max": min(n_exp, 1) if n_exp_max is None else n_exp_max}
    if tag == "Sublet":
        r.update(certificate={"available": case != "unavailable", "held": held}, certificate_case=case,
                 B0_rule=m4.B0_RULE, t_a=None if case == "W(a)" else 3, aborted=case != "W(a)")
    return r


def test_checks_on_hand_rows():
    good = [_row("a", "A6-rule"), _row("b", "A6-always2"), _row("c", "A6-always2", menu="short", n_exp=4, no_site=4),
            _row("d", "Sublet", case="W(a)", held=True), _row("e", "Sublet", case="W(b)", held=True),
            _row("f", "BL3-2")]
    ch = e5.build_checks(good)
    assert ch["E5-1"]["status"] == "pass" and ch["E5-2"]["status"] == "pass" and ch["E5-2"]["n_checked"] == 2
    assert ch["E5-1"]["n_runs_expected"] == 6 and ch["E5-1"]["n_runs_lost"] == 0
    assert ch["E5-3"]["status"] == "pass" and ch["E5-3"]["n_runs_exposed"] == 1
    assert ch["E5-3"]["placed_share"] == 0.0 and ch["E5-3"]["n_runs_exposed_none_placed"] == 1   # no site, no spare
    assert ch["E5-5"]["status"] == "pass" and ch["E5-5"]["by_case"]["W(b)"] == {"runs": 1, "held": 1}
    assert ch["E5-5"]["B0_rules"] == {m4.B0_RULE: 2}
    assert ch["E5-6"]["status"] == "informative" and ch["E5-6"]["threshold"]["n_exp_threshold"] > 30
    # a run lost to an error (lost_runs of an ok job): E5-1 fails, and E5-5 for a Sublet job
    lost = [{"job": "x", "tag": "Sublet", "n_runs_expected": 3, "n_runs": 2,
             "errors": [{"tag": "Sublet p1", "error": "RuntimeError: crash"}]}]
    ch = e5.build_checks(good, lost)
    assert ch["E5-1"]["status"] == "fail" and ch["E5-1"]["n_runs_lost"] == 1 and ch["E5-1"]["n_runs_expected"] == 7
    assert ch["E5-5"]["status"] == "fail" and ch["E5-5"]["n_runs_lost"] == 1 and ch["E5-5"]["lost"] == lost
    ch = e5.build_checks([], lost)
    assert ch["E5-1"]["status"] == "fail" and ch["E5-5"]["status"] == "fail" and ch["E5-3"]["status"] == "missing"
    # failures
    bad = good + [_row("g", "A6-rule", buys=1), _row("h", "A6-always2", menu="short", n_exp=2),
                  _row("i", "Sublet", case="W(a)", held=False), _row("j", "BL3-0", inv=1)]
    ch = e5.build_checks(bad)
    assert ch["E5-1"]["status"] == "fail" and ch["E5-1"]["n_invariant_failures"] == 1
    assert ch["E5-2"]["status"] == "fail" and [x["job"] for x in ch["E5-2"]["failures"]] == ["g"]
    assert ch["E5-3"]["status"] == "fail" and [x["job"] for x in ch["E5-3"]["failures"]] == ["h"]
    assert ch["E5-5"]["status"] == "fail" and ch["E5-5"]["n_failures"] == 1
    # W(c) is counted, not a failure; an instance above 3600 s is listed and not checked
    ch = e5.build_checks([_row("k", "Sublet", case="W(c)", held=False),
                          _row("l", "A6-rule", n_exp=3, buys=1, lam_ok=False)])
    assert ch["E5-5"]["status"] == "pass" and ch["E5-5"]["n_w_c"] == 1
    assert ch["E5-2"]["status"] == "missing" and ch["E5-2"]["n_unchecked"] == 1 and "status_note" in ch["E5-2"]
    assert ch["E5-3"]["status"] == "missing"
    # an always2 run without exposure: E5-3 holds vacuously
    ch = e5.build_checks([_row("m", "A6-always2", menu="short")])
    assert ch["E5-3"]["status"] == "pass" and "vacuous_note" in ch["E5-3"]
    assert ch["E5-3"]["placed_share"] is None and "placed_share_note" in ch["E5-3"]
    assert e5.build_checks([])["E5-1"]["status"] == "missing"


def test_e5_6_counts():
    thr = e5.redundancy_threshold()["n_exp_threshold"]
    hi, lo = int(thr) + 8, 2
    rows = [_row("a", "A6-rule", "short", "trace", 0.2, n_exp=500, buys=3, n_exp_max=hi),     # bought, above
            _row("b", "A6-rule", "short", "trace", 0.5, n_exp=400, n_exp_max=hi),             # not bought, above
            _row("c", "A6-rule", "short", "trace", 1.0, n_exp=5, n_exp_max=lo),               # not bought, below
            _row("d", "A6-rule", "short", "trace", 2.0, n_exp=5, buys=1, n_exp_max=lo),       # bought, below
            _row("e", "A6-rule", "long", "all1", 1.0),                                        # no exposure
            _row("f", "A6-always2", "short", "trace", 0.2, n_exp=500, buys=9, n_exp_max=hi)]  # not A6-rule
    by = e5.build_checks(rows)["E5-6"]["by_level_menu"]
    assert set(by) == set(e5.LEVELS) and all(set(v) == set(e5.MENUS) for v in by.values())
    ts = by["trace"]["short"]
    assert (ts["n_runs"], ts["n_with_buys"], ts["share_with_buys"]) == (4, 2, 0.5)
    assert (ts["bought_above"], ts["bought_below"], ts["not_bought_above"], ts["not_bought_below"]) == (1, 1, 1, 1)
    assert ts["n_exp_max"] == {"max": hi, "median": (hi + lo) / 2}
    assert set(ts["by_mu"]) == {"0.2", "0.5", "1", "2"}           # every mu of the default point is counted
    assert (ts["by_mu"]["0.2"]["bought_above"], ts["by_mu"]["0.5"]["not_bought_above"]) == (1, 1)
    assert ts["by_mu"]["1"]["n_runs"] == 1 and ts["by_mu"]["1"]["not_bought_below"] == 1
    al = by["all1"]["long"]
    assert set(al["by_mu"]) == {"1"} and (al["n_runs"], al["not_bought_below"], al["share_with_buys"]) == (1, 1, 0.0)
    e = by["sh1"]["short"]                                        # no run: the null form
    assert e["n_runs"] == 0 and e["share_with_buys"] is None and e["n_exp_max"]["max"] is None
    assert "share_with_buys_note" in e
    assert {k for k in e["by_mu"]["1"] if not k.endswith("_note")} == set(ts["by_mu"]["1"])


def _cells(vals: dict) -> dict:
    """cells.<..>.1 with the cost and fallback medians of `vals` {tag: (cost, fallback)}."""
    out = {}
    for t in e5.TAGS:
        c, f = vals.get(t, (None, None))
        out[t] = {"cost_over_bl0a": {"median": c}, "fallback_share_after_reclaims": {"median": f}}
    return out


def test_pareto_rule():
    v = {"A6-off": (1.0, 0.5), "A6-rule": (1.1, 0.4), "A6-always2": (1.2, 0.45),
         "BL3-0": (0.9, 0.3), "BL3-1": (0.95, 0.45), "BL3-2": (0.8, None)}
    p = e5.pareto_entry(_cells(v), "long")
    assert p["bl3_pareto"] == ["BL3-0"] and p["bl3_undecided"] == ["BL3-2"]
    assert p["medians"]["BL3-1"] == {"cost_over_bl0a": 0.95, "fallback_share_after_reclaims": 0.45}
    v["BL3-0"] = (1.0, 0.3)              # equal to A6-off's cost: no strict gain
    assert e5.pareto_entry(_cells(v), "long")["bl3_pareto"] == []


def test_a6_identical():
    def r(tag, c, total, n_leases=10):
        return {"tag": tag, "c": c, "policy_seed": 0, "total": total, "n_leases": n_leases}
    same = {t: [r(t, 1, 100.0), r(t, 2, 50.0)] for t in e5.A6_TAGS}
    assert e5.a6_identical(same) == {"n_pairs": 2, "n_identical": 2, "all_identical": True}
    diff = dict(same, **{"A6-always2": [r("A6-always2", 1, 100.5), r("A6-always2", 2, 50.0, 11)]})
    assert e5.a6_identical(diff) == {"n_pairs": 2, "n_identical": 0, "all_identical": False}
    part = dict(same, **{"A6-off": [r("A6-off", 1, 100.0)]})    # only alignment 1 has every A6 tag
    assert e5.a6_identical(part)["n_pairs"] == 1
    e = e5.a6_identical({"A6-rule": [r("A6-rule", 1, 1.0)]})
    assert e["n_pairs"] == 0 and e["all_identical"] is None and "all_identical_note" in e


def _keys(d, pre=""):
    out = set()
    for k, v in d.items():
        out.add(pre + k)
        if isinstance(v, dict) and k not in ("gpu_hour_share", "B0_rules"):
            out |= _keys(v, pre + k + ".")
    return out


def _run_row(ps=0):
    """A run row of a run file (run_row's fields that the summary reads)."""
    return {"policy_seed": ps, "total": 90.0, "cost_over_bl0a": 0.9,
            "accountings": {"overflow_usd": 90.0, "total_usd": 190.0, "overflow_over_bl0a": 0.9,
                            "total_over_bl0a": 0.95, "own_share_of_total": 100 / 190, "overflow_over_bl0b": 0.1,
                            "total_over_bl0b": 0.2},
            "fallback_share_after_reclaims": None, "fallback_share": 0.2, "stranding_events_per_day": 3.0,
            "loads_per_day": 4.0, "replica_utilization": 0.5, "announcements_per_site_day": 20.0,
            "grouped": {k: 10.0 for k in e5.COMPONENTS}, "gpu_hours_by_class": {"revocable": 5.0},
            "n_leases": 7, "leases_by_end_cause": {"release": 5, "reclaim": 2},
            "n_invariant_failures": 0, "invariant_first": [], "gpu_only_lease_slots": 0,
            "redundancy": {"buys": 0, "no_site": 0, "n_exp_total": 2, "n_exp_max": 1, "spare_slot_groups": 0},
            "certificate": {"available": True, "held": True}, "certificate_case": "W(a)", "B0_rule": m4.B0_RULE,
            "t_a": None, "aborted": False}


def test_cell_null_form_keeps_fields():
    run = {**_run_row(), "c": 1, "bl0a_usd": 100.0}
    for tag in ("A6-rule", "BL3-1", "Sublet"):
        full, empty = e5.cell_entry([run], tag), e5.cell_entry([], tag)
        assert _keys(full) - {k for k in _keys(full) if k.endswith("_note")} <= _keys(empty), tag
        assert empty["n_runs"] == 0 and empty["cost_over_bl0a"]["median"] is None
        assert full["fallback_share_after_reclaims"]["n_null"] == 1
        json.dumps(mc.jsonable(full), allow_nan=False)
    a6 = e5.cell_entry([run], "A6-rule")
    assert a6["redundancy"]["share_runs_exposed"] == 1.0 and a6["certificates"] is None
    assert a6["components_over_bl0a"]["total"] == pytest.approx(0.1)
    assert (a6["n_leases"]["median"], a6["n_leases_reclaimed"]["median"], a6["gpu_hours"]["median"]) == (7, 2, 5)
    assert e5.cell_entry([], "A6-rule", n_expected=12)["n_runs_expected"] == 12


def test_summary_lists_lost_runs(tmp_path, monkeypatch):
    """A hand-made out folder: two ok jobs, one with its run and one (Sublet) whose only run raised."""
    monkeypatch.setenv(e5.REDUCED_ENV, "1")
    inst = {"instance_hash": "h", "n_sites": 3, "n_sites_by_kind": {"maas": 3}, "n_contracts": 4,
            "contracts": list(e5.MENUS["short"]) + ["protected"], "n_lenders_with_sites": 1,
            "lam_s": {"S": [60.0, 64.0]}, "lam_s_max_ok": True}
    refs = {"bl0a_usd": 100.0, "own_capacity_usd": 100.0}

    def put_job(tag, runs, errors):
        jid = e5.run_job_id("trace", "short", tag, 1.0, 1)
        d = {"job": jid, "level": "trace", "menu": "short", "tag": tag, "mu": 1.0, "c": 1, "bl0a_usd": 100.0,
             "bl0a_own_demand": 100.0, "demand_sha256": "d", "own_demand_sha256": "d", "instance": inst,
             "references": refs, "policy_seeds": [0], "runs": runs, "errors": errors}
        mc.dump_json(d, e5.run_path(tmp_path, jid))
        mc.dump_json({"job": jid, "status": "ok", "n_errors": len(errors)}, mc.record_path(tmp_path, jid))
        return jid

    put_job("A6-rule", [_run_row()], [])
    jid = put_job("Sublet", [], [{"tag": "Sublet p0", "error": "RuntimeError: simulated crash"}])
    s = e5.summary(tmp_path)
    re = s["meta"]["run_errors"]
    assert (re["n_runs_expected"], re["n_runs"], re["n_runs_lost"]) == (2, 1, 1)
    assert re["jobs"] == [{"job": jid, "tag": "Sublet", "n_runs_expected": 1, "n_runs": 0,
                           "errors": [{"tag": "Sublet p0", "error": "RuntimeError: simulated crash"}]}]
    ch = s["checks"]
    assert ch["E5-1"]["status"] == "fail" and ch["E5-1"]["n_runs_lost"] == 1
    assert ch["E5-5"]["status"] == "fail" and ch["E5-5"]["runs"] == 0 and ch["E5-5"]["n_runs_lost"] == 1
    c = s["cells"]["trace"]["short"]["1"]
    assert (c["Sublet"]["n_runs"], c["Sublet"]["n_runs_expected"], c["A6-rule"]["n_runs"]) == (0, 1, 1)
    assert s["meta"]["jobs_ok"] == 2 and len(s["meta"]["jobs_missing"]) == 89
    assert "lost to an error 1" in (tmp_path / "tables.md").read_text()


def test_run_script_parses():
    sh = SIM / "sublet" / "experiments" / "run_e5.sh"
    assert subprocess.run(["bash", "-n", str(sh)]).returncode == 0
    text = sh.read_text()
    assert "MS3_E5_REDUCED=1" in text and "ms3_init e5" in text and "ms3_finish" in text


# ---------------------------------------------------------------- needs_a12: instances and runs
@pytest.mark.needs_a12
def test_long_menu_carries_short_demand():
    from sublet.drivers.run import build
    from sublet.experiments.e6 import bl0a_all
    from sublet.instance import InstanceError
    s, _, _, si = e5.e5_instance("short", 1.0, 1, "trace", SHORT_HZ)
    l, _, _, li = e5.e5_instance("long", 1.0, 1, "trace", SHORT_HZ)
    assert np.array_equal(l.clients.demand, s.clients.demand) and l.borrower_stats == s.borrower_stats
    assert bl0a_all(l) == bl0a_all(s) == li["bl0a_usd"] == si["bl0a_usd"] == si["bl0a_own_demand"]
    assert li["demand_sha256"] == si["demand_sha256"] and li["own_demand_sha256"] != li["demand_sha256"]
    # the Gamma notes: the long menu records the scaling of the demand it carries next to its own
    assert si["own_gamma_notes"] and li["own_gamma_notes"]
    assert li["demand_gamma_notes"] == si["demand_gamma_notes"] == si["own_gamma_notes"] == e5.gamma_notes(s)
    own = build(e5.e5_spec("long", 1.0, 1, horizon_min=SHORT_HZ), 1)[0]
    assert li["bl0a_own_demand"] == bl0a_all(own) != li["bl0a_usd"]
    assert [x.id for x in l.contracts] == list(e5.MENUS["long"]) + ["protected"]
    assert [x.id for x in s.contracts] == list(e5.MENUS["short"]) + ["protected"]
    assert [x.id for x in l.sites] == [x.id for x in own.sites] and l.m < s.m
    # the level does not change the instance
    l2 = e5.e5_instance("long", 1.0, 1, "all1", SHORT_HZ)[0]
    assert mc.instance_hash(l2) == mc.instance_hash(l)
    # the client-list check
    other = dataclasses.replace(s, clients=dataclasses.replace(s.clients, region=list(reversed(s.clients.region))))
    with pytest.raises(InstanceError):
        e5.carry_demand(own, other, "test")


@pytest.mark.needs_a12
def test_levels_resolve_on_the_instance():
    from sublet.drivers.run import build
    from sublet.lender import resolve_params
    for lv, want in (("sh0.5", {"p_sh": 0.5, "groups": None, "delay_slots_max": 1}),
                     ("all1", {"p_sh": 1.0, "groups": "all", "delay_slots_max": 1}), ("trace", {})):
        inst, model, ecfg = build(e5.e5_spec("short", 1.0, 1, lv, horizon_min=SHORT_HZ), 1)
        assert resolve_params(inst, model) == want, lv
        assert (model.information, model.on_unavailable, model.violations) == ("I1", "sell", "absorb")
        assert ecfg.check_invariants is True
        assert model.schedule == ("trace" if lv == "trace" else "correlated")


# (level, menu, tag, mu / beta~): E5-2's long-menu runs, E5-3's exposed run (A6-always2 at mu 0.2 at the default
# point; at mu 1 the 6-h runs have no exposed replica), the tags whose parameters are checked, and Sublet
RUNS = (("all1", "long", "A6-rule", 1.0), ("all1", "long", "A6-always2", 1.0), ("trace", "long", "A6-rule", 1.0),
        ("trace", "long", "A6-always2", 1.0), ("all1", "short", "A6-always2", 1.0),
        ("trace", "short", "A6-always2", 0.2), ("trace", "short", "A6-off", 1.0), ("trace", "short", "BL3-0", 1.0),
        ("trace", "short", "BL3-2", 1.0), ("trace", "short", "Sublet", 1.0))


@pytest.fixture(scope="module")
def short_runs(tmp_path_factory):
    """The jobs of RUNS at alignment 1, policy seed 0, on a 6-h horizon (the reduced job list with its horizon
    patched), run through ms3_common.run_job into a temporary out folder, with the summary."""
    out = tmp_path_factory.mktemp("e5")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv(e5.REDUCED_ENV, "1")
        mp.setitem(e5.REDUCED, "horizon_min", SHORT_HZ)
        by = {j.id: j for j in e5.jobs()}
        recs = {}
        for k in RUNS:
            j = by[e5.run_job_id(*k, 1)]
            recs[k] = mc.run_job(e5.EXP, j, lambda o, j=j: e5.run(j, o, out), out=out, resume=False)
        summ = e5.summary(out)
    files = {k: mc.read_json(e5.run_path(out, e5.run_job_id(*k, 1))) for k in RUNS}
    return {"out": out, "recs": recs, "files": files, "summary": summ}


@pytest.mark.needs_a12
def test_e5_2_on_a_short_horizon(short_runs):
    for k, rec in short_runs["recs"].items():
        assert rec["status"] == "ok" and rec["n_errors"] == 0, (k, rec.get("error"), rec.get("errors"))
    for (lv, mn, tag, _), d in short_runs["files"].items():
        assert d["horizon_min"] == SHORT_HZ and d["instance"]["lam_s_max_ok"] is True
        assert all(hi <= e5.LAM_LIMIT_S for _, hi in d["instance"]["lam_s"].values())
        for r in d["runs"]:
            assert r["n_invariant_failures"] == 0 and r["gpu_only_lease_slots"] == 0
            if mn == "long" and tag in ("A6-rule", "A6-always2"):
                assert r["redundancy"]["n_exp_total"] == 0 and r["redundancy"]["buys"] == 0, (lv, tag)
            if tag == "A6-always2" and r["redundancy"]["n_exp_total"] > 0:      # E5-3's property
                assert r["redundancy"]["buys"] + r["redundancy"]["no_site"] > 0
    ch = short_runs["summary"]["checks"]
    assert ch["E5-2"]["status"] == "pass" and ch["E5-2"]["n_checked"] == 4 and ch["E5-2"]["n_unchecked"] == 0
    assert ch["E5-1"]["status"] == "pass" and ch["E5-3"]["status"] == "pass"
    assert ch["E5-1"]["n_runs"] == ch["E5-1"]["n_runs_expected"] == len(RUNS) and ch["E5-1"]["n_runs_lost"] == 0


@pytest.mark.needs_a12
def test_e5_3_on_an_exposed_run(short_runs):
    r = short_runs["files"][("trace", "short", "A6-always2", 0.2)]["runs"][0]["redundancy"]
    assert r["mode"] == "always2" and r["n_exp_total"] > 0 and r["buys"] + r["no_site"] > 0
    s = short_runs["summary"]
    ch = s["checks"]["E5-3"]
    assert ch["status"] == "pass" and ch["n_runs_exposed"] >= 1 and "vacuous_note" not in ch
    assert ch["buys_total"] + ch["no_site_total"] >= r["buys"] + r["no_site"] and ch["placed_share"] is not None
    x = s["exposure"]["trace"]["short"]["A6-always2"]["by_mu"]["0.2"]
    assert (x["n_runs"], x["n_runs_exposed"], x["buys_total"], x["no_site_total"]) == (1, 1, r["buys"], r["no_site"])
    assert set(s["exposure"]["trace"]["short"]["A6-always2"]["by_mu"]) == {"0.2", "0.5", "2"}
    assert "by_mu" not in s["exposure"]["all1"]["long"]["A6-always2"]


@pytest.mark.needs_a12
def test_tag_params_reach_the_policy(short_runs):
    n_extra = {"BL3-0": 0, "BL3-2": 2}            # BL3-2: BL3's default (baselines/spothedge.py:60)
    mode = {"A6-off": "off", "A6-rule": "rule", "A6-always2": "always2"}
    seen = set()
    for (lv, mn, tag, mu), d in short_runs["files"].items():
        assert d["style_key"] == e5.TAGS[tag][2] and (tag == "Sublet" or d["params"] == e5.TAGS[tag][1])
        for r in d["runs"]:
            if tag in n_extra:
                assert r["resolved_params"]["n_extra"] == n_extra[tag] and "redundancy" not in r, tag
            if tag in mode:
                assert r["redundancy"]["mode"] == r["resolved_params"]["redundancy"] == mode[tag], tag
            seen.add(tag)
    assert seen >= set(n_extra) | set(mode)
    p = short_runs["summary"]["pareto"]["trace"]["short"]["a6_modes_identical"]
    assert p["n_pairs"] == 0 and p["all_identical"] is None      # A6-rule at (trace, short, mu 1) is not in RUNS


@pytest.mark.needs_a12
def test_sublet_job_takes_m36_allowance(short_runs):
    from sublet.experiments.e6 import bl0a_all
    d = short_runs["files"][("trace", "short", "Sublet", 1.0)]
    inst = e5.e5_instance("short", 1.0, 1, "trace", SHORT_HZ)[0]
    b0 = m4.B0_SHARE * bl0a_all(inst)
    assert d["params"] == m4.sublet_params(inst) and d["params"]["B0"] == b0
    assert d["params"]["inner"] == "BL5" and d["params"]["kappa"] is None and d["params"]["gamma"] == 1.0
    assert d["bl0a_usd"] == bl0a_all(inst)
    for r in d["runs"]:
        assert r["B0_rule"] == m4.B0_RULE and r["B0_usd"] == b0 and r["bl0a_usd"] == bl0a_all(inst)
        assert_rel(r["B0_report_usd"], b0, 1e-12, "A8's resolved B0")
        assert r["info_class_reported"] == m4.INFO_CLASS_REPORTED and r["info_class"] == "online-I1 + a-priori N"
        assert r["certificate"]["available"] and r["certificate_case"] in m4.CASES
        if r["certificate_case"] in m4.PROVEN_CASES:
            assert r["certificate"]["held"] is True
        assert "ALG_per_slot" not in r["certificate"]
    assert short_runs["summary"]["checks"]["E5-5"]["status"] == "pass"


@pytest.mark.needs_a12
def test_summary_keys(short_runs):
    s = short_runs["summary"]
    assert set(s) == {"meta", "cells", "exposure", "pareto", "certificates", "checks"}
    assert list(s["checks"]) == [f"E5-{i}" for i in range(1, 7)]
    assert all(v["status"] in ("pass", "fail", "missing", "pending", "explained", "informative") and v["claim"]
               for v in s["checks"].values())
    assert s["meta"]["reduced"] is True and "reduced_note" in s["meta"]
    assert s["meta"]["B0_rule"] == m4.B0_RULE and s["meta"]["B0_share"] == m4.B0_SHARE
    assert set(s["cells"]) == set(e5.LEVELS)
    for lv in e5.LEVELS:
        assert set(s["cells"][lv]) == {"short", "long"} and set(s["exposure"][lv]["long"]) == set(e5.A6_TAGS)
        assert set(s["pareto"][lv]) == {"short", "long"}
    assert set(s["cells"]["trace"]["short"]) == {"0.2", "0.5", "1", "2"} and set(s["cells"]["all1"]["long"]) == {"1"}
    c = s["cells"]["all1"]["long"]["1"]["A6-rule"]
    assert c["n_runs"] == 1 and c["cost_over_bl0a"]["n"] == 1 and c["redundancy"]["buys"]["max"] == 0
    for k in e5.ACCOUNTING_KEYS + ("n_leases", "n_leases_reclaimed", "gpu_hours"):
        assert c[k]["n"] == 1, k
    assert c["n_runs_expected"] == 1 and c["n_leases"]["median"] > 0
    assert s["meta"]["run_errors"] == {"n_runs_expected": len(RUNS), "n_runs": len(RUNS), "n_runs_lost": 0,
                                       "jobs": []}
    assert all("placed_share" in s["exposure"][lv][mn][t] for lv in e5.LEVELS for mn in e5.MENUS for t in e5.A6_TAGS)
    assert all("a6_modes_identical" in s["pareto"][lv][mn] for lv in e5.LEVELS for mn in e5.MENUS)
    assert set(s["checks"]["E5-6"]["by_level_menu"]["trace"]["short"]["by_mu"]) == {"0.2", "0.5", "1", "2"}
    assert s["cells"]["sh1"]["short"]["1"]["A6-rule"]["n_runs"] == 0
    inst = s["meta"]["instances"]["by_menu"]
    assert inst["long"]["1"]["1"]["bl0a_usd"] == inst["short"]["1"]["1"]["bl0a_usd"]
    assert inst["long"]["1"]["1"]["bl0a_own_demand"] != inst["long"]["1"]["1"]["bl0a_usd"]
    assert inst["long"]["1"]["1"]["instance_hashes_found"] == 1
    assert s["meta"]["instances"]["max_rel_diff_bl0a"] == 0.0
    refs = s["meta"]["references"]["1"]["1"]
    assert set(refs) >= {"bl0a_usd", "own_capacity_usd", "bl0b_overflow_usd", "bl0b_total_usd",
                         "committed_price_usd_per_gpu_h"}
    assert s["certificates"]["n"] == 1 and s["certificates"]["B0_rules"] == {m4.B0_RULE: 1}
    assert len(s["meta"]["jobs_missing"]) == 91 - len(RUNS)
    assert (short_runs["out"] / "tables.md").is_file()
