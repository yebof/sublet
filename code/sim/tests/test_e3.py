"""Tests of the E3 driver sublet/experiments/e3.py and its run script (design/sim_spec_ms4.md §4, §10 row test_e3.py).

- The job list (quick): 36 cells at u = 8 only (M41), 36 shared and 348 per-borrower MILP jobs (384) and e3:gate,
  every id parses (§2.4, the key 'part' of §4.7), the reduced list (MS3_E3_REDUCED=1), the estimate of §4.7 (324
  shared runs x 1.2 s and 3,132 sub-runs x 2 s in the cell jobs; 19.2 h of MILP wall time on 2 slots); the filters of
  run_e3.sh's passes select the gate cell, its 9 MILP jobs, e3:gate and the 4 part=b00 jobs at b = 1 (§4.4, §4.7);
  the script parses (bash -n).
- With the a12 outputs (needs_a12): the fixed order of the 64 M-tier week slices (§4.4) against measurement 4's
  recorded slices at b = 32 (code/sim/out/ms4spec/e3_sizing_b32_sizes.json); the overrides of §4.3; under normalize
  'mean' (C24, M7) equal borrower means in the siloed instance, the shared client equal to their sum with one Gamma,
  equal overflow shares, and the sub-instances' B0 summing to B0_SHARE x the shared BL0a (§4.5); the reduced cells at
  b = 1 and b = 8: the b = 1 identity (E3-2: the sub-instance is the shared instance, siloed and shared totals equal
  to 1e-9 USD), every Sublet run and Sublet-siloed sub-run with its own B0 (ms4_common.sublet_params of its own
  (sub-)instance; never typed here) and certificate, E3-3 and E3-4 on the records.
- The MILPs, the gate and the summary (needs_a12, slow): the siloed OPT as the sum of the sub-instance MILP records
  (ms4_common.sum_bench), the bracket with lo <= b, the b00 copy at b = 1, the empty record of a borrower without a
  client, the gate job's record gate.json (config hash, borrowers, MILP sizes, bracket, allowance needs with margin
  and t_a_at_B0) and --check-gate, the summary's checks E3-1 ... E3-7 and the key paths that Fig. 4(c), sf_e3_util
  and sf_e3_mu read (§8.1, §8.2); a MILP job whose cell record carries another schedule hash is an error;
  a stale MILP record is not used; on a copy of the outputs, the failure paths: the b00 job at b = 1 failing while the
  shared job is killed or has no record, the summary's b00 part taken from the shared record (stale_copies), the
  killed shared MILP leaving the b = 1 point open against its LP, --check-gate and E3-7 refusing another MILP limit,
  E3-3 failing on a tampered sub-run row, and a 'size_gate' record with the LP as LB.
"""
import json
import re
import subprocess

import numpy as np
import pytest

from fixtures import SIM

from sublet.experiments import e3
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms4_common as m4

RUN_E3 = SIM / "sublet" / "experiments" / "run_e3.sh"
SIZES_B32 = SIM / "out" / "ms4spec" / "e3_sizing_b32_sizes.json"      # measurement 4


def _filters() -> dict:
    """The pass filters NAME='regex' of run_e3.sh."""
    return dict(re.findall(r"^(\w+_RE)='([^']*)'$", RUN_E3.read_text(), flags=re.M))


def _lines(js) -> list[str]:
    return [f"{j.kind} {j.id}" for j in js]


def _job(js, jid):
    return next(j for j in js if j.id == jid)


# ---------------------------------------------------------------- job list and run script (quick)
def test_job_list_counts_and_ids(monkeypatch):
    monkeypatch.delenv(e3.REDUCED_ENV, raising=False)
    monkeypatch.delenv("MS3_MILP_LIMIT", raising=False)
    js = e3.jobs()
    mc.check_jobs(js)
    kinds = [j.kind for j in js]
    assert kinds.count("pool") == 36 + 1 and kinds.count("milp") == 384 and "alone" not in kinds
    ids = [j.id for j in js]
    assert sum(i.endswith(":part=shared") for i in ids) == 36
    assert sum(":part=b" in i for i in ids) == 348                      # (63 x 4) + (8 x 12), §4.7
    assert "e3:cell:b=8:u=8:mu=0.2:c=4" in ids and "e3:milp:b=32:u=8:mu=1:c=3:part=b31" in ids
    assert e3.US == (8,) and e3.REDUCED["us"] == (8,)                    # M41: no u sweep
    assert all(mc.parse_job_id(i)[2]["u"] == "8" for i in ids if i != e3.GATE_ID) and e3.GATE_CELL[1] == 8
    assert ids[-1] == e3.GATE_ID == "e3:gate"
    for i in ids:
        exp, part, kv = mc.parse_job_id(i)
        assert exp == "e3" and part in ("cell", "milp", "gate")
        if part == "milp":
            assert kv["part"] == "shared" or re.fullmatch(r"b\d\d", kv["part"])
    cells = [j for j in js if ":cell:" in j.id]
    assert sum(len(j.params["policy_seeds"]) * 6 for j in cells) == 324 * 2      # shared and siloed runs
    assert sum(len(j.params["policy_seeds"]) * 3 * j.params["b"] for j in cells) == 3132     # sub-runs, §4.7
    assert all(j.est_s is not None for j in js)
    est = mc.estimate(js, 4)
    assert est["milp_wall_s"] / 3600 == pytest.approx(19.2, abs=1e-6)            # §4.7: 384 x 360 s on 2 slots
    runs_s = sum(j.est_s for j in cells) - sum((1 + j.params["b"]) * e3.EST_LP_S for j in cells)
    assert runs_s == pytest.approx(324 * 1.2 + 3132 * 2.0, abs=1e-6)             # §4.7: 6,652.8 s, about 1.8 h
    with pytest.raises(ValueError):
        e3.milp_id(8, 8, 1.0, 1, "b8")
    with pytest.raises(ValueError):
        e3.milp_id(8, 8, 1.0, 1, "x:y")
    monkeypatch.setenv(e3.REDUCED_ENV, "1")
    jr = e3.jobs()
    assert [j.kind for j in jr].count("pool") == 3 + 1 and [j.kind for j in jr].count("milp") == 20
    assert all(j.params["horizon"] == list(e3.REDUCED["horizon"]) for j in jr)
    assert e3.cell_id(*e3.GATE_CELL) in [j.id for j in jr]


@pytest.mark.parametrize("reduced", [False, True])
def test_run_script_filters(monkeypatch, reduced):
    if reduced:
        monkeypatch.setenv(e3.REDUCED_ENV, "1")
    else:
        monkeypatch.delenv(e3.REDUCED_ENV, raising=False)
    f = _filters()
    assert set(f) == {"GATE_CELL_RE", "GATE_MILP_RE", "GATE_JOB_RE", "B00_RE"}
    lines = _lines(e3.jobs())

    def sel(name):
        return [ln for ln in lines if re.search(f[name], ln)]
    assert sel("GATE_CELL_RE") == ["pool " + e3.cell_id(*e3.GATE_CELL)]
    gm = sel("GATE_MILP_RE")
    assert len(gm) == 9 and all(ln.startswith("milp e3:milp:b=8:u=8:mu=1:c=1:part=") for ln in gm)
    assert sel("GATE_JOB_RE") == ["pool e3:gate"]
    b00 = sel("B00_RE")
    assert len(b00) == (1 if reduced else 4)
    assert all(re.search(r":b=1:.*:part=b00$", ln) for ln in b00)
    assert not [ln for ln in lines if ":b=1:" in ln and ln.endswith(":part=b00") and ln not in b00]


def test_run_script_parses():
    r = subprocess.run(["bash", "-n", str(RUN_E3)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    text = RUN_E3.read_text()
    for s in ('source "$(dirname "$0")/ms3_lib.sh"', "ms3_init e3", "--check-gate", "export MS3_RESUME=1",
              "ms3_summary", "ms3_finish", "MS3_E3_REDUCED=1"):
        assert s in text


# ---------------------------------------------------------------- slices, overrides, normalization (needs_a12)
@pytest.mark.needs_a12
def test_slice_order_and_overrides():
    sl = e3.m_slices()
    assert len(sl) == e3.N_SLICES == 64
    assert sl[:2] == [("azure2024_conv", 0), ("azure2024_code", 0)]
    assert sl[2:8] == [(s, 0) for s in e3.BURST_SPLITS]                          # round-robin by week index
    weeks = {s: sum(1 for x, _ in sl if x == s) for s in e3.BURST_SPLITS}
    assert list(weeks.values()) == [8, 8, 8, 8, 15, 15]
    assert sl[-2:] == [("burstgpt_3__ChatGPT__conv", 14), ("burstgpt_3__ChatGPT__api", 14)]
    rec = json.loads(SIZES_B32.read_text())
    assert [list(x) for x in sl[:32]] == rec["borrower_slices"]                 # measurement 4's order at b = 32
    bl = e3.borrower_list(8)
    assert [x["id"] for x in bl] == [f"b{i:02d}" for i in range(8)]
    assert all(x["tier"] == "M" and x["region"] == "europe" for x in bl)
    with pytest.raises(ValueError):
        e3.borrower_list(65)
    ov = e3.overrides(8, 16, False, 0.5)
    from sublet.experiments.e1 import MENU
    assert all(ov[k] == v for k, v in MENU.items())
    assert ov["regions.list"] == ["europe"] and ov["regions.adjacency"] == [] and ov["units.per_replica"] == 16
    assert ov["stranding.mu_over_beta_tilde"] == 0.5 and ov["time.horizon_min"] == 1440
    assert ov["llms"] == [e3.LLM_M]
    bo = ov["borrowers"]
    assert (bo["model"], bo["merge"], bo["normalize"], bo["own_capacity_quantile"], bo["smoothing_min"],
            bo["market_tightness"]) == ("series", False, "mean", 75, 15, 0.5)
    # the overrides of measurement 4 (e3_sizing.py) plus mu and normalize
    rec8 = json.loads((SIM / "out" / "ms4spec" / "e3_sizing_b8_sizes.json").read_text())["overrides"]["shared"]
    ours = e3.overrides(8, 8, True)
    assert {k: v for k, v in ours.items() if k not in ("stranding.mu_over_beta_tilde", "borrowers")} == \
        {k: v for k, v in rec8.items() if k != "borrowers"}
    assert {k: v for k, v in ours["borrowers"].items() if k != "normalize"} == rec8["borrowers"]


@pytest.mark.needs_a12
def test_normalize_gives_equal_borrowers():
    from sublet.experiments.e6 import bl0a_all
    sh, model, ecfg, _ = e3.build_instance(8, 8, 1.0, 1, True)
    si, _, _, _ = e3.build_instance(8, 8, 1.0, 1, False)
    assert ecfg.check_invariants and model.schedule == "trace" and model.violations == "absorb"
    assert sh.n == 1 and si.n == 7                                     # b03 has no overflow on the day (§4.2)
    means = np.asarray(si.clients.demand, dtype=np.float64).mean(axis=1)
    assert np.max(np.abs(means / means[0] - 1)) <= 1e-9                # every borrower's overflow has mean 1 x Gamma
    assert np.allclose(np.asarray(sh.clients.demand)[0], np.asarray(si.clients.demand).sum(axis=0), rtol=1e-9,
                       atol=0)
    g = [n for n in sh.notes if "Gamma" in n]
    assert g and g == [n for n in si.notes if "Gamma" in n]
    assert sh.borrower_stats["b03"]["normalize_factor"] is None
    assert all(sh.borrower_stats[f"b{i:02d}"]["normalize_factor"] > 0 for i in range(8) if i != 3)
    bb = e3.borrower_block(sh, si, 8)
    assert bb["dropped"] == ["b03"] and bb["n_kept"] == 7
    shares = [x["share"] for x in bb["list"] if x["kept"]]
    assert max(abs(s - 1 / 7) for s in shares) <= 1e-9
    subs = e3.sub_instances(si)
    b0 = [m4.sublet_params(s)["B0"] for s in subs.values()]
    assert sum(b0) == pytest.approx(m4.sublet_params(sh)["B0"], rel=1e-9)
    assert m4.sublet_params(sh)["B0"] == m4.B0_SHARE * bl0a_all(sh)
    hs = {mc.schedule_hash(e3.trace_schedule(s, model, 1)) for s in subs.values()}
    assert hs == {mc.schedule_hash(e3.trace_schedule(sh, model, 1))}  # one realized schedule per alignment


# ---------------------------------------------------------------- the reduced cells at b = 1 and b = 8 (needs_a12)
@pytest.fixture(scope="module")
def cells(tmp_path_factory):
    """The reduced cell jobs (b, u, mu, c) = (1, 8, 1, 1) and (8, 8, 1, 1) in a temporary out/e3."""
    out = tmp_path_factory.mktemp("e3") / "e3"
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv(e3.REDUCED_ENV, "1")
        js = e3.jobs()
        recs = {}
        for b in (1, 8):
            j = _job(js, e3.cell_id(b, 8, 1.0, 1))
            recs[b] = mc.run_job("e3", j, lambda o, j=j: e3.run(j, o, out), out, resume=False)
    return out, recs


def _cell(out, b):
    return json.loads(e3.cell_file(out, b, 8, 1.0, 1).read_text())


@pytest.mark.needs_a12
def test_cell_b1_identity(cells, monkeypatch):
    out, recs = cells
    assert recs[1]["status"] == "ok" and recs[1]["runs"] == 6 and recs[1]["n_errors"] == 0, recs[1].get("errors")
    cr = _cell(out, 1)
    assert cr["horizon"] == list(e3.REDUCED["horizon"]) and cr["policy_seeds"] == [0]
    assert cr["instances"]["sub"]["b00"] == cr["instances"]["shared"]          # E3-2
    by = {r["tag"]: r for r in cr["runs"]}
    assert set(by) == set(e3.TAGS)
    assert abs(by["Sublet-siloed"]["ALG"] - by["Sublet"]["ALG"]) <= 1e-9
    assert abs(by["A6-siloed"]["ALG"] - by["A6"]["ALG"]) <= 1e-9
    assert by["Sublet-siloed"]["sub_runs"][0]["B0_usd"] == by["Sublet"]["B0_usd"]
    for r in cr["runs"]:
        assert r["n_invariant_failures"] == 0 and r["gpu_only_lease_slots"] == 0 and r["ratio_validity"] is None
        if r["mode"] == "siloed":
            assert r["components_sum_abs_diff"] <= 1e-9 and r["n_sub_runs"] == 1
    assert cr["schedule_mismatch"] == []
    assert set(cr["lps"]) == {"shared", "b00"} and all(x["status"] == 0 for x in cr["lps"].values())


@pytest.mark.needs_a12
def test_cell_b8_sublet_sub_runs(cells):
    """Each Sublet-siloed sub-run has its own B0 = B0_SHARE x BL0a of its sub-instance (M36, §4.5) and its own
    certificate (M28); the shared Sublet run has the shared instance's; both accountings on every cost entry."""
    from sublet.experiments.e6 import bl0a_all
    out, recs = cells
    assert recs[8]["status"] == "ok" and recs[8]["n_errors"] == 0, recs[8].get("errors")
    cr = _cell(out, 8)
    hz = cr["horizon"]
    sh, _, _, _ = e3.build_instance(8, 8, 1.0, 1, True, hz)
    si, _, _, _ = e3.build_instance(8, 8, 1.0, 1, False, hz)
    subs = e3.sub_instances(si)
    assert mc.instance_hash(sh) == cr["instances"]["shared"]
    assert {bid: mc.instance_hash(s) for bid, s in subs.items()} == cr["instances"]["sub"]
    by = {r["tag"]: r for r in cr["runs"]}
    s = by["Sublet"]
    assert s["B0_rule"] == m4.B0_RULE and s["B0_usd"] == m4.B0_SHARE * bl0a_all(sh) == s["bl0a_usd"] * m4.B0_SHARE
    assert (s["gamma"], s["kappa"]) == (1.0, None) and s["info_class_reported"] == m4.INFO_CLASS_REPORTED
    assert s["certificate"]["available"] and s["certificate_case"] in m4.CASES
    ss = by["Sublet-siloed"]
    assert ss["n_sub_runs"] == len(subs) == 7 and [x["borrower"] for x in ss["sub_runs"]] == list(subs)
    for x in ss["sub_runs"]:
        bl = bl0a_all(subs[x["borrower"]])
        assert x["bl0a_usd"] == bl and x["B0_usd"] == m4.B0_SHARE * bl
        if bl > 0:
            assert x["B0_rule"] == m4.B0_RULE
        assert x["certificate"]["available"] and x["certificate_case"] in m4.CASES
        assert x["certificate"]["held"] or x["certificate_case"] == "W(c)"
        assert x["schedule_hash"] == cr["schedule_hash"]
    assert ss["certificates"]["n"] == 7 and sum(v["runs"] for v in ss["certificates"]["by_case"].values()) == 7
    assert sum(x["B0_usd"] for x in ss["sub_runs"]) == pytest.approx(s["B0_usd"], rel=1e-9)
    assert by["A6-siloed"]["certificates"] is None and "B0_usd" not in by["BL2"]
    for r in cr["runs"]:
        a = r["accountings"]
        assert set(m4.accountings(r["ALG"], sh, cr["references"])) == set(a)
        assert a["total_usd"] - a["overflow_usd"] == pytest.approx(cr["references"]["own_capacity_usd"], abs=1e-9)
        if r["mode"] == "siloed":
            comp = {k: sum(x["components"][k] for x in r["sub_runs"]) for k in r["components"]}
            assert all(abs(comp[k] - r["components"][k]) <= 1e-9 for k in comp)          # E3-3
            assert r["per_slot_abs_diff"] <= 1e-9 and abs(r["ALG"] - sum(x["ALG"] for x in r["sub_runs"])) <= 1e-9
    bb = cr["borrowers"]
    assert bb["dropped"] == ["b03"] and len(bb["list"]) == 8
    assert cr["bl0a"]["siloed"] == pytest.approx(cr["bl0a"]["shared"], rel=1e-9)


# ---------------------------------------------------------------- MILPs, gate, summary (needs_a12, slow)
@pytest.mark.needs_a12
@pytest.mark.slow
def test_milps_gate_and_summary(cells, monkeypatch, tmp_path):
    out, _ = cells
    monkeypatch.setenv(e3.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_MILP_LIMIT", "10")
    js = e3.jobs()

    def run(jid):
        j = _job(js, jid)
        return mc.run_job("e3", j, lambda o: e3.run(j, o, out), out, resume=False)
    # b = 8: the shared MILP and one per listed borrower (b03 has no client: OPT 0, no MILP)
    for part in ["shared"] + e3.borrower_ids(8):
        r = run(e3.milp_id(8, 8, 1.0, 1, part))
        assert r["status"] == "ok" and r["milp_limit_s"] == 10, r.get("error")
    empty = json.loads(e3.milp_file(out, 8, 8, 1.0, 1, "b03").read_text())
    assert empty["empty"] is True and empty["objective"] == 0.0 and empty["status"] == "empty"
    recs = {p: json.loads(e3.milp_file(out, 8, 8, 1.0, 1, p).read_text()) for p in ["shared"] + e3.borrower_ids(8)}
    cr = _cell(out, 8)
    for p, rec in recs.items():
        if p == "b03":
            continue
        assert rec["status"] in (0, 1) and rec["time_limit_s"] == 10 and rec["grid"] == "slow"
        assert rec["instance_hash"] == (cr["instances"]["shared"] if p == "shared" else cr["instances"]["sub"][p])
        assert rec["schedule_hash"] == cr["schedule_hash"] and rec["estimate"]["n_vars"] == rec["size"]["n_vars"]
        assert rec["git_revision"] is not None
    # the siloed OPT is the sum of the sub-instance MILPs (§4.6)
    bench = e3.cell_benchmarks(out, cr)
    inc = sum(recs[p]["objective"] for p in e3.borrower_ids(8))
    assert bench["siloed"]["incumbent"] == pytest.approx(inc, rel=1e-12) and bench["siloed"]["n_empty"] == 1
    lbs = [mc.bench_values(json.loads((out / cr["lps"][p]["file"]).read_text()), recs[p])["LB"]
           for p in e3.borrower_ids(8) if p != "b03"]
    assert bench["siloed"]["LB"] == pytest.approx(sum(lbs), rel=1e-12)
    br = bench["bracket"]
    assert br["lo"] <= br["point"] * (1 + 1e-9) and br["point"] <= br["hi"] * (1 + 1e-9) and br["lo"] <= 8
    assert br["point"] == pytest.approx(inc / recs["shared"]["objective"], rel=1e-12)
    # b = 1: the b00 job copies the shared record (E3-2)
    assert run(e3.milp_id(1, 8, 1.0, 1, "shared"))["status"] == "ok"
    assert run(e3.milp_id(1, 8, 1.0, 1, "b00"))["status"] == "ok"
    sh1 = json.loads(e3.milp_file(out, 1, 8, 1.0, 1, "shared").read_text())
    b00 = json.loads(e3.milp_file(out, 1, 8, 1.0, 1, "b00").read_text())
    assert b00["copied_from"] == e3.milp_id(1, 8, 1.0, 1, "shared") and b00["objective"] == sh1["objective"]
    assert b00["dual_bound"] == sh1["dual_bound"] and b00["job"] == e3.milp_id(1, 8, 1.0, 1, "b00")
    # the gate (§4.4)
    g_rec = run(e3.GATE_ID)
    assert g_rec["status"] == "ok" and g_rec["n_errors"] == 0, g_rec.get("errors")
    g = json.loads(e3.gate_file(out).read_text())
    assert g["config_hash"] == e3.grid_config_hash() and g["hash_check"] == {"instance": True, "schedule": True}
    assert g["meta"]["reduced"] is True and g["meta"]["B0_rule"] == m4.B0_RULE and g["meta"]["git_revision"]
    assert [x["id"] for x in g["borrowers"]["list"]] == e3.borrower_ids(8) and g["borrowers"]["dropped"] == ["b03"]
    assert set(g["milp"]) == {"shared", *e3.borrower_ids(8)} and g["milp"]["shared"]["job_status"] == "ok"
    assert g["milp"]["shared"]["size"]["n_vars"] > 0 and g["milp"]["shared"]["solve_s"] is not None
    assert {k: g["bracket"][k] for k in ("point", "lo", "hi")} == {k: br[k] for k in ("point", "lo", "hi")}
    al = g["allowance"]
    assert set(al["sub_runs"]) == set(cr["instances"]["sub"]) and al["n_sub_runs"] == 7
    from sublet.experiments.e6 import bl0a_all
    for x in [al["shared"], *al["sub_runs"].values()]:
        assert x["B0_rule"] == m4.B0_RULE and x["B0_usd"] == pytest.approx(m4.B0_SHARE * x["bl0a_usd"], rel=1e-12)
        assert x["margin_usd"] == pytest.approx(x["B0_usd"] - x["need_usd"], abs=1e-9)
        assert (x["t_a_at_B0"] is None) == (x["margin_usd"] >= 0) or abs(x["margin_usd"]) < 1e-6
        assert x["n_invariant_failures"] == 0
    sh8, _, _, _ = e3.build_instance(8, 8, 1.0, 1, True, cr["horizon"])
    assert al["shared"]["bl0a_usd"] == bl0a_all(sh8)
    bl5 = next(r for r in cr["runs"] if r["tag"] == "BL5")
    assert al["shared"]["total_usd"] == pytest.approx(bl5["ALG"], rel=1e-12)      # A8 executes BL5 unchanged
    assert e3.check_gate(out)[0]
    # the summary
    s = e3.summary(out)
    assert json.loads((out / "summary.json").read_text()) == json.loads(json.dumps(s))
    assert (out / "tables.md").is_file() and s["meta"]["reduced"] is True and s["meta"]["B0_rule"] == m4.B0_RULE
    assert set(s["checks"]) == {f"E3-{i}" for i in range(1, 8)}
    st = {k: v["status"] for k, v in s["checks"].items()}
    assert st == {"E3-1": "pass", "E3-2": "pass", "E3-3": "pass", "E3-4": "pass", "E3-5": "pass",
                  "E3-6": "informative", "E3-7": "informative"}, st
    assert s["checks"]["E3-7"]["config_hash_equal"] is True and s["checks"]["E3-7"]["milp_limit_equal"] is True
    e33 = s["checks"]["E3-3"]
    assert e33["n_runs"] == 6 and e33["n_per_slot_missing"] == 0 and e33["max_abs_diff_per_slot"] <= 1e-9
    assert e33["max_abs_diff"] <= 1e-9 and e33["max_abs_diff_alg"] <= 1e-9
    for b in e3.BS:                                        # Fig. 4(c), sf_e3_util: every path of the grid
        for u in e3.US:
            o = s["opt"][str(b)][str(u)]["1"]
            assert all(k in o for k in ("point_median", "lo_min", "hi_max", "exact", "open", "by_alignment"))
            for tag in e3.TAGS:
                e = s["ratios"][str(b)][str(u)]["1"][tag]
                assert all(k in e for k in ("median", "median_ci95", "inc_median", "n", "ratio_LB", "ratio_inc"))
                ut = s["util"][str(b)][str(u)]["1"][tag]
                assert "median_ci95" in ut["replica_utilization"] and "median_ci95" in ut["loads_per_day"]
                assert "overflow_over_bl0a" in s["cost_over_bl0a"][str(b)][str(u)]["1"][tag]
    for mu in ("0.2", "0.5", "1", "2"):                    # sf_e3_mu
        assert set(s["ratios"]["8"]["8"][mu]) == set(e3.TAGS) and "point_median" in s["opt"]["8"]["8"][mu]
    e = s["ratios"]["8"]["8"]["1"]
    lb = mc.lb_record(e3_alg(cr, "Sublet"), json.loads((out / cr["lps"]["shared"]["file"]).read_text()),
                      recs["shared"])
    assert e["Sublet"]["n"] == 1 and e["Sublet"]["median"] == pytest.approx(lb["ratio_LB"])
    assert e["Sublet"]["inc_median"] == pytest.approx(lb["ratio_inc"]) and e["Sublet"]["open"] is False
    assert s["ratios"]["8"]["8"]["1"]["BL2"]["n"] == 1 and s["ratios"]["32"]["8"]["1"]["Sublet"]["median"] is None
    o = s["opt"]["8"]["8"]["1"]
    assert o["point_median"] == pytest.approx(br["point"]) and o["n_alignments"] == 1 and o["n_cells"] == 1
    assert s["opt"]["32"]["8"]["1"]["point_median"] is None and "point_median_note" in s["opt"]["32"]["8"]["1"]
    assert s["opt"]["32"]["8"]["1"]["open"] is True and "open_note" in s["opt"]["32"]["8"]["1"]   # no cell: open
    assert s["ratios"]["32"]["8"]["1"]["Sublet"]["open"] is True
    assert s["milp"]["copied"] == [e3.milp_id(1, 8, 1.0, 1, "b00")] and s["milp"]["counts"]["siloed"]["empty"] == 1
    assert s["milp"]["stale_copies"] == [] and s["milp"]["counts"]["siloed"]["copied"] == 1
    assert s["milp"]["wall_limit_kills"] == [] and s["opt"]["1"]["8"]["1"]["point_median"] == 1.0
    nk = s["borrowers"]["8"]["8"]["n_kept"]                                      # null form of a missing alignment
    assert nk["1"] == 7 and nk["2"] is None and "2_note" in nk
    assert s["certificates"]["all"]["n"] == 2 + 1 + 7 and s["certificates"]["all"]["failures"] == 0
    assert s["borrowers"]["8"]["8"]["by_alignment"]["1"]["dropped"] == ["b03"]
    assert s["meta"]["references"]["8"]["8"]["1"]["1"]["bl0a_usd"] == pytest.approx(cr["bl0a"]["shared"])
    # a stale MILP record is not used; the LB falls back to the LP
    p = e3.milp_file(out, 8, 8, 1.0, 1, "shared")
    good = p.read_text()
    p.write_text(json.dumps({**recs["shared"], "schedule_hash": "f" * 64}))
    s2 = e3.summary(out)
    assert s2["milp"]["stale"] == [e3.milp_id(8, 8, 1.0, 1, "shared")]
    assert s2["ratios"]["8"]["8"]["1"]["Sublet"]["open"] is True and s2["opt"]["8"]["8"]["1"]["open"] is True
    p.write_text(good)
    # --check-gate refuses another grid's gate; a MILP job refuses a cell record with another schedule hash
    gp = e3.gate_file(out)
    gate_text = gp.read_text()
    gp.write_text(json.dumps({**g, "config_hash": "0" * 64}))
    assert not e3.check_gate(out)[0] and e3.main(["--check-gate", "--out", str(out)]) == 1
    gp.write_text(gate_text)
    assert e3.main(["--check-gate", "--out", str(out)]) == 0
    cp = e3.cell_file(out, 8, 8, 1.0, 1)
    cell_text = cp.read_text()
    cp.write_text(json.dumps({**cr, "schedule_hash": "0" * 64}))
    jr = mc.record_path(out, e3.milp_id(8, 8, 1.0, 1, "shared"))
    jr_text = jr.read_text()
    rb = run(e3.milp_id(8, 8, 1.0, 1, "shared"))
    assert rb["status"] == "error" and "schedule hash" in rb["error"]
    cp.write_text(cell_text)
    jr.write_text(jr_text)
    _failure_paths(out, tmp_path / "e3", js, cr, monkeypatch)


def _failure_paths(out, o2, js, cr8, monkeypatch):
    """The failure paths of §4.6 and §4.7 on a copy of the outputs of test_milps_gate_and_summary."""
    import shutil
    import sublet.opt.milp as om
    shutil.copytree(out, o2)

    def run(jid):
        j = _job(js, jid)
        return mc.run_job("e3", j, lambda o: e3.run(j, o, o2), o2, resume=False)
    sid, bid = e3.milp_id(1, 8, 1.0, 1, "shared"), e3.milp_id(1, 8, 1.0, 1, "b00")
    rp, lbp = mc.record_path(o2, sid), e3.milp_file(o2, 1, 8, 1.0, 1, "shared")
    rec_text, lb_text = rp.read_text(), lbp.read_text()
    # the shared job killed at the wall limit (as ms3_common --record-failure records it; its output discarded):
    # the b00 job fails, the b = 1 point is open against the LP alone, and the kill is counted once
    rp.write_text(json.dumps({**json.loads(rec_text), "status": "wall_limit"}))
    lbp.unlink()
    r = run(bid)
    assert r["status"] == "error" and "'wall_limit', not 'ok'" in r["error"]
    s = e3.summary(o2)
    o1, e1 = s["opt"]["1"]["8"]["1"], s["ratios"]["1"]["8"]["1"]["Sublet"]
    assert o1["open"] is True and o1["point_median"] is None and o1["by_alignment"]["1"]["siloed"]["incumbent"] is None
    assert e1["lp_only"] == 1 and e1["open"] is True and e1["median"] is not None
    assert s["ratios"]["1"]["8"]["1"]["Sublet"]["share_exact"] == 0
    assert s["milp"]["wall_limit_kills"] == [sid] and s["milp"]["copied"] == [bid]
    assert [x["job"] for x in s["milp"]["stale_copies"]] == [bid]
    assert s["milp"]["counts"]["shared"]["wall_limit"] == 1 and "wall_limit" not in s["milp"]["counts"]["siloed"]
    # no final record of the shared job: the b00 job fails
    rp.unlink()
    r = run(bid)
    assert r["status"] == "error" and "None, not 'ok'" in r["error"]
    # the shared job 'ok' again (a resume reran it): the b00 job copies it, and the b = 1 point is exactly 1
    rp.write_text(rec_text)
    lbp.write_text(lb_text)
    assert run(bid)["status"] == "ok"
    s = e3.summary(o2)
    assert s["milp"]["stale_copies"] == [] and s["opt"]["1"]["8"]["1"]["point_median"] == 1.0
    assert s["opt"]["1"]["8"]["1"]["open"] is False
    # a later shared record (another incumbent, the same hashes): the b00 copy is stale and the shared record used
    rec = json.loads(lb_text)
    lbp.write_text(json.dumps({**rec, "objective": rec["objective"] * 1.01}))
    s = e3.summary(o2)
    assert [x["job"] for x in s["milp"]["stale_copies"]] == [bid] and s["opt"]["1"]["8"]["1"]["point_median"] == 1.0
    lbp.write_text(lb_text)
    # another MILP limit: --check-gate refuses the gate, E3-7 fails and the records are listed
    monkeypatch.setenv("MS3_MILP_LIMIT", "30")
    ok, msg = e3.check_gate(o2)
    assert not ok and "MILP limit" in msg and e3.main(["--check-gate", "--out", str(o2)]) == 1
    s = e3.summary(o2)
    assert s["checks"]["E3-7"]["status"] == "fail" and s["checks"]["E3-7"]["milp_limit_equal"] is False
    listed = {x["job"] for x in s["milp"]["limit_mismatch"] if x["kind"] == "milp"}
    assert {e3.milp_id(8, 8, 1.0, 1, p) for p in ["shared"] + e3.borrower_ids(8) if p != "b03"} <= listed
    assert bid not in listed and e3.milp_id(8, 8, 1.0, 1, "b03") not in listed      # copies and empty records
    monkeypatch.setenv("MS3_MILP_LIMIT", "10")
    assert e3.check_gate(o2)[0]
    # E3-3 recomputes the sums from the stored rows: a tampered sub-run row fails it
    cp = e3.cell_file(o2, 8, 8, 1.0, 1)
    c2 = json.loads(cp.read_text())
    row = next(r for r in c2["runs"] if r["tag"] == "Sublet-siloed")
    row["sub_runs"][0]["components"]["lease_rent"] += 1.0
    cp.write_text(json.dumps(c2))
    e33 = e3.summary(o2)["checks"]["E3-3"]
    assert e33["status"] == "fail" and e33["max_abs_diff"] == pytest.approx(1.0) and len(e33["failures"]) == 1
    # a model over the S36 gate is not solved: status 'size_gate', and the LP stays the LB (§4.6)
    sh1, model, _, _ = e3.build_instance(1, 8, 1.0, 1, True, cr8["horizon"])

    def refuse(*a, **kw):
        raise om.SizeError("model has 1 variables > max_vars = 0 (test)")
    monkeypatch.setattr(om, "solve_opt", refuse)
    g = e3.solve_bench(sh1, e3.trace_schedule(sh1, model, 1), "milp", 10, job=sid, kind="milp", part="shared")
    assert g["status"] == "size_gate" and g["objective"] is None and g["dual_bound"] is None
    assert g["estimate"]["n_vars"] > 0 and g["time_limit_s"] == 10 and g["grid"] == "slow"
    lp1 = json.loads((o2 / _cell(o2, 1)["lps"]["shared"]["file"]).read_text())
    v = mc.bench_values(lp1, g)
    assert v["LB_source"] == "lp" and v["LB"] == lp1["objective"] and v["incumbent"] is None
    assert v["milp_status"] == "size_gate"


def e3_alg(cr: dict, tag: str) -> float:
    return next(r["ALG"] for r in cr["runs"] if r["tag"] == tag)
