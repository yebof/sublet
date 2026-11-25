"""Tests of the Q44 study driver (design/q44_practical_sublet.md §5, §6.1 items 5-7, §6.3).

- the registry rows and driver branches of A7 and A8 (§6.1 item 5): information classes, driver inputs
  (A8's own N_bound only with S_rbar = 'theory', the inner's inputs in inner_params), the inner check
  against A8_INNER_IDS, auto_drain for a guarded baseline;
- the block files build the run matrix of §5.5 (cell-modes per block, the I1 demand-seed cells, the held-out
  versus tuning cells, the 53 family instance-modes); oracle: the note's tables;
- the certificate of §3.10 on hand-made ledgers (oracle: hand computation);
- the smoke run of §6.3: q44_study.py on toy.json with two modes (and a small family block) writes the run
  files, the LB files and summary.json with the keys of D1-D6, the duplicate cell is dropped, and the
  certificate holds on every guarded run (needs A7 and A8).
"""
import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from fixtures import CONFIGS, DELETE, load_json, toy_config

from sublet.algos import registry
from sublet.config import ConfigError
from sublet.drivers import run as drun
from sublet.experiments import q44_study as qs


def _spec(**kw) -> dict:
    s = {"schema_version": 1, "name": "t_q44", "instance": "toy.json", "policy": {"id": "BL0a"}}
    s.update(kw)
    return s


# ---------------------------------------------------------------- registry and driver (§6.1 item 5)
def test_registry_a7_a8_rows():
    """A7 and A8 are registry ids with runner 'simulate'; A8 stays out of WRAPPERS and INNER_IDS; its inner ids
    are A8_INNER_IDS; info_class('A8', {}) = 'online-I1 + a-priori N', without the suffix for S_rbar = 1; A8's
    driver inputs are its own N_bound (S_rbar = 'theory') plus the inner's."""
    for pid in ("A7", "A8"):
        assert registry.entry(pid).runner == "simulate"
    assert "A8" not in registry.WRAPPERS and "A8" not in registry.INNER_IDS
    assert registry.A8_INNER_IDS == ("A7", "A3", "A6", "BL1", "BL5")
    assert registry.info_class("A7", {}) == "online-I1"
    assert registry.info_class("A8", {}) == "online-I1 + a-priori N"
    assert registry.info_class("A8", {"S_rbar": 1}) == "online-I1"
    assert registry.info_class("A8", {"inner": "A6", "inner_params": {"variant": "theory"}}) == \
        "online-I1 + a-priori N"
    assert registry.needed_inputs("A7", {}) == ()
    assert registry.needed_inputs("A8", {}) == ("N_bound",)
    assert registry.needed_inputs("A8", {"S_rbar": 1}) == ()
    assert registry.needed_inputs("A8", {"S_rbar": 1, "inner": "A6", "inner_params": {"variant": "theory"}}) == \
        ("N_bound",)
    assert registry.inner_of("A8", {}) == ("A7", {})
    assert registry.inner_of("A8", {"inner": "BL5", "inner_params": {"x": 1}}) == ("BL5", {"x": 1})
    # safe = 'fb' builds no R, so A8 reads no N (guard.Guarded) and its class has no a-priori N
    assert registry.needed_inputs("A8", {"safe": "fb"}) == () and registry.info_class("A8", {"safe": "fb"}) == "online-I1"
    assert registry.needed_inputs("A8", {"safe": "pd"}) == ("N_bound",)
    # the guard's own list of inner ids is the registry's (guard.py does not import the registry)
    from sublet.algos import guard
    assert guard.INNER_IDS == registry.A8_INNER_IDS
    # the registry's A8 defaults are the class's (the default test is T0g since the decision of 2026-10-17; this
    # assertion covered inner, S_rbar and safe before and now covers the test as well)
    keys = ("inner", "S_rbar", "safe", "test")
    assert dict(registry.entry("A8").defaults) == {k: guard.Guarded.PARAMS[k] for k in keys}
    assert registry.entry("A8").default("test") == "T0g"


class _FakeA8:
    """Stands in for guard.Guarded in the routing test: records its keywords."""
    PARAMS = {"inner": "A7", "inner_params": {}, "safe": "fb+pd", "S_rbar": "theory", "gamma": 1.0,
              "gamma_T11": 1.7, "test": "T0g", "wind_down": "auto", "reserve": True, "B0": "auto", "kappa": 10.0,
              "abort_at": None}
    INPUTS = ("N_bound", "on_unavailable")

    def __init__(self, **kw):
        self.kw = kw


def test_make_policy_a8_routing(monkeypatch):
    """§6.1 item 5: make_policy gives A8 its own N_bound iff S_rbar = 'theory' and the inner's driver inputs in
    inner_params (N_bound of an inner A6 with variant 'theory'); the inner must be one of A8_INNER_IDS; a guarded
    baseline runs with auto_drain false (§15.1)."""
    real = registry.resolve
    monkeypatch.setattr(registry, "resolve", lambda pid: _FakeA8 if pid == "A8" else real(pid))
    from sublet.instance import build_instance, units
    inst = build_instance(CONFIGS / "toy.json")
    N = max(len(units(inst).client) * inst.grid.T_slow, 3)
    p = drun.make_policy({"policy": {"id": "A8", "params": {}}}, inst)
    assert p.kw["N_bound"] == N and p.kw["inner_params"] == {}
    assert p.kw["on_unavailable"] == "sell"                     # the run's lender option (toy.json: 'sell')
    p = drun.make_policy({"policy": {"id": "A8", "params": {}}, "lender_model": {"on_unavailable": "refuse"}}, inst)
    assert p.kw["on_unavailable"] == "refuse"
    p = drun.make_policy({"policy": {"id": "A8", "params": {"S_rbar": 1, "inner": "A6",
                                                            "inner_params": {"variant": "theory"}}}}, inst)
    assert "N_bound" not in p.kw and p.kw["inner_params"] == {"variant": "theory", "N_bound": N}
    p = drun.make_policy({"policy": {"id": "A8", "params": {"inner": "BL1"}}}, inst)
    assert p.kw["N_bound"] == N and p.kw["inner_params"] == {}
    for bad in ({"inner": "A2"}, {"inner": "A8"}, {"inner": "BL2"}, {"inner": "BL6"}, {"gamma_typo": 1}):
        with pytest.raises(ConfigError):
            drun.load_run_spec(_spec(policy={"id": "A8", "params": bad}))
    with pytest.raises(ConfigError):
        drun.load_run_spec(_spec(policy={"id": "A8", "params": {"inner": "BL5"}}, engine={"auto_drain": True}))
    drun.load_run_spec(_spec(policy={"id": "A8", "params": {"inner": "A6"}}, engine={"auto_drain": True}))


# ---------------------------------------------------------------- the run matrix (§5.2-§5.5)
def test_blocks_run_matrix():
    """The block files build the note's run matrix: Q1 154 cell-modes (I1 6 cells, I2 8, I4 8 x 7 modes), Q2 16,
    Q3 32, Q4 24, Q5 48 cell-modes and 48 LP jobs (alone), Q6 53 family instance-modes with 11 policies x 10 runs
    (RR_RENEW and MARKING not on F3: 5,670 runs); the I1 cells are config seeds 3, 4, 7 x demand seeds {as
    configured, +100}, (3, as configured) is I1's only tuning cell, I4 has none; PS-GR runs on I1 and I2 only;
    the Tier 2 blocks exist and are not in TIER1."""
    want = {"Q0": (1, 0), "Q1": (154, 0), "Q2": (16, 0), "Q3": (32, 0), "Q4": (24, 0), "Q5": (48, 48), "Q6": (53, 0)}
    rows = {r["block"]: r for r in qs.describe(list(qs.TIER1))}
    for b, (cm, lb) in want.items():
        assert (rows[b]["cell_modes"], rows[b]["lb_jobs"]) == (cm, lb), (b, rows[b])
    assert rows["Q5"]["alone"] == 48 and rows["Q6"]["runs"] == 5670
    q1 = qs.load_block("Q1")
    ms = load_json(CONFIGS / "ms2_multi_small.json")
    d100 = next(i for i in q1["instances"] if i["id"] == "I1-d100")
    assert d100["overrides"] == {f"borrowers.clients.{i}.demand.seed": c["demand"]["seed"] + 100
                                 for i, c in enumerate(ms["borrowers"]["clients"])}
    tuning = {(i["id"], c) for i in q1["instances"] for c in i["tuning_seeds"]}
    assert tuning == {("I1", 3), ("I2", 1)}
    cells = {i["family"]: 0 for i in q1["instances"]}
    for i in q1["instances"]:
        cells[i["family"]] += len(i["config_seeds"])
        assert ("PS-GR" in qs.instance_policies(q1, i)) == (i["family"] in ("I1", "I2"))
        assert qs.instance_policies(q1, i)[0] == "BL0a"
    assert cells == {"I1": 6, "I2": 8, "I4": 8}
    q2 = qs.load_block("Q2")
    assert {i["family"] for i in q2["instances"]} == {"I3"} and q2["instances"][0]["tuning_seeds"] == [1]
    q6 = qs.load_block("Q6")
    fam = {f["id"]: f for f in q6["families"]}
    assert (fam["F1"]["m"], fam["F1"]["rho"], fam["F1"]["T"], fam["F1"]["modes"]) == ([2, 4, 8], [4, 8, 16], 48, ["F-ad"])
    assert (fam["F2"]["m"], fam["F2"]["rho"], fam["F2"]["modes"]) == ([2, 4, 8, 16], [4, 16, 64], ["F-ss", "F-iid", "F-eg"])
    assert (fam["F3"]["beta"], fam["F3"]["T"]) == ([2, 6, 14, 30], [48, 192])
    for b in ("T2_vr_rf", "T2_ad", "T2_stress", "T2_guard", "T2_e7r", "T2_bl8"):
        assert qs.load_block(b)["tier"] == 2 and b not in qs.TIER1
    assert qs.MODES["L-ss"]["lender_model"]["params"] == {"D_slots": 12, "k": 2}
    assert [qs.MODES[f"L-iid-{p}"]["lender_model"]["params"]["p"] for p in ("0.0124", "0.05", "0.2")] == [0.0124, 0.05, 0.2]
    assert qs.MODES["L-co"]["lender_model"]["params"] == {"p_sh": 1.0, "groups": "all"}


def test_estimate_tier1():
    """run_q44_study.sh --dry-run (q44_study.estimate): one entry per Tier 1 job in list order (the 376 jobs of
    --list: Q0 1, Q1 154, Q2 16, Q3 32, Q4 24, Q5 96 of which the 48 LPs are alone, Q6 53), every estimate
    positive, the per-block sums add up to the single-worker total, and the wall time with two workers is the
    pool's list schedule plus the alone jobs, between half the pool time and the single-worker total."""
    e = qs.estimate(list(qs.TIER1), workers=2)
    ids = [j["id"] for b in qs.TIER1 for j in qs.list_jobs(qs.load_block(b))]
    assert [j["id"] for j in e["jobs"]] == ids and len(ids) == 376
    assert {b["block"]: (b["jobs"], b["alone"]) for b in e["blocks"]} == \
        {"Q0": (1, 0), "Q1": (154, 0), "Q2": (16, 0), "Q3": (32, 0), "Q4": (24, 0), "Q5": (96, 48), "Q6": (53, 0)}
    assert all(j["est_s"] > 0 for j in e["jobs"])
    assert e["single_worker_s"] == pytest.approx(sum(b["single_worker_s"] for b in e["blocks"]), rel=1e-12)
    pool = sum(j["est_s"] for j in e["jobs"] if not j["alone"])
    assert e["alone_s"] == pytest.approx(sum(j["est_s"] for j in e["jobs"] if j["alone"]), rel=1e-12)
    assert pool / 2 - 1e-9 <= e["pool_wall_s"] <= pool + 1e-9
    assert e["wall_s"] == pytest.approx(e["pool_wall_s"] + e["alone_s"], rel=1e-12) and e["wall_s"] <= e["single_worker_s"]
    one = qs.estimate(list(qs.TIER1), workers=1)
    assert one["wall_s"] == pytest.approx(one["single_worker_s"], rel=1e-12)


def test_spot_config_builds():
    """configs/q44_spot_1day.json (instance I4) is example_1day.json with the lenders A100, A800 and GPU-series-2."""
    a = load_json(CONFIGS / "q44_spot_1day.json")
    b = load_json(CONFIGS / "example_1day.json")
    assert [x["id"] for x in a["lenders"]] == ["a1:A100-SXM4-80GB", "a1:A800-SXM4-80GB", "a1:GPU-series-2"]
    assert {k: v for k, v in a.items() if k not in ("name", "lenders")} == \
        {k: v for k, v in b.items() if k not in ("name", "lenders")}
    drun.load_run_spec(_spec(instance="q44_spot_1day.json"))


# ---------------------------------------------------------------- the certificate (§3.10)
def _res(total, extra=None):
    T = len(total)
    ps = {k: np.zeros(T) for k in ("lease_prepaid", "lease_rent", "loading", "routing", "fallback", "stranding_kv",
                                    "stranding_fl", "stranding_fb", "stranding_pi")}
    ps.update({k: np.asarray(v, dtype=float) for k, v in (extra or {}).items()})
    ps["total"] = np.asarray(total, dtype=float)
    return SimpleNamespace(per_slot=ps)


def _rep(test, gamma, t_a, C_S, B, a_hat, W=None):
    slots = list(range(len(a_hat)))
    return {"test": test, "gamma": gamma, "kappa": 10.0, "t_a": t_a, "W_S_t_a": W,
            "guard": {"slots": slots, "a_hat": a_hat, "B": B}, "safe": {"C_S_curve": C_S, "B_on": [0.1] * len(C_S)}}


def test_certificate_by_hand():
    """§3.10 on hand-made ledgers (T = 3): without an abort the core bound is gamma C_S(T) + B(T) + m(T) and m is
    max{0, ALG - a-hat}; with an abort at t_a = 2 the bound is C_S(T) + (gamma - 1) C_S(t_a - 1) + W_S(t_a) +
    B(t_a - 1) + m(t_a - 1) and the S-mode excess [ALG(T) - ALG(t_a - 1)] - [W_S + C_S(T) - C_S(t_a - 1)]; a
    ledger above the bound fails it; under T0 an m above the slot's stranding fails m_ok."""
    # no abort: ALG = 1, 2, 3; C_S = 1, 2, 3; B = 0.5; a-hat = ALG (m = 0)
    c = qs.certificate(_res([1, 1, 1]), None, _rep("T0", 1.0, None, [1, 2, 3], [0.5] * 3, [1, 2, 3]), core_exact=False)
    assert c["held"] and c["core_bound_ok"] and abs(c["core_bound_rhs"] - 3.5) < 1e-12 and c["m_max"] == 0
    # abort at 2: ALG = 1, 2, 5; C_S = 1, 2, 4; B = 0.5; W = 0.25; gamma 1.5 -> rhs = 4 + 0.5 * 2 + 0.25 + 0.5 = 5.75
    r = _rep("T0", 1.5, 2, [1, 2, 4], [0.5] * 3, [1, 2, 9], W=0.25)
    c = qs.certificate(_res([1, 1, 3]), None, r, core_exact=False)
    assert c["aborted"] and abs(c["core_bound_rhs"] - 5.75) < 1e-12 and c["core_bound_ok"]
    assert abs(c["s_mode_excess"] - ((5 - 2) - (0.25 + 4 - 2))) < 1e-12 and c["executed_slots"] == 2
    c = qs.certificate(_res([1, 1, 4]), None, r, core_exact=False)          # ALG(T) = 6 > 5.75
    assert not c["core_bound_ok"] and not c["held"]
    # T0 with a-hat below ALG at slot 0 by 0.4 and no stranding: m(0) = 0.4 > 0 fails m_ok; with 0.4 stranding it holds
    r = _rep("T0", 1.0, None, [2, 3, 4], [1.0] * 3, [0.6, 2, 3])
    assert not qs.certificate(_res([1, 1, 1]), None, r, core_exact=False)["m_ok"]
    assert qs.certificate(_res([1, 1, 1], {"stranding_fb": [0.4, 0, 0]}), None, r, core_exact=False)["m_ok"]
    # E-mode check: ALG(0) = 3 > gamma C_S(0) + B(0) + m(0) = 1 + 0.5 + 0 (a-hat = 3)
    c = qs.certificate(_res([3, 0, 0]), None, _rep("T0", 1.0, None, [1, 4, 4], [0.5] * 3, [3, 3, 3]), core_exact=False)
    assert not c["e_mode_ok"]
    # a report without the guard's curves gives an unavailable certificate, not an exception
    assert qs.certificate(_res([1, 1]), None, {"test": "T0"}, core_exact=False)["available"] is False


def test_certificate_reserve_by_hand():
    """The certificate of a T0g run with the wind-down reserve (q44_study.certificate; guard.py Theorem W) on hand-made
    ledgers (T = 3, gamma = 1, B = 0.5): abort at t_a = 2 with S following FB, C_S = 1, 2, 4, R = 0.5, 0.3 at the
    executed slots: the budget is R(1) = 0.3; the wind-down cost (S-mode excess) [ALG(3) - ALG(1)] - [C_S(3) -
    C_S(1)] is 0.2 <= 0.3 for ALG = 1, 2, 4.2 (held, proven case) and 0.4 > 0.3 for ALG = 1, 2, 4.4 (wind_down_ok
    false, not held, although the core bound 4 + 0.5 = 4.5 holds); ALG(t) + R(t) <= C_S(t) + B(t) + m(t) is checked
    at the executed slots (ALG(1) + R(1) = 2.3 <= 2.5; with R(1) = 0.6 it fails and the certificate is not held,
    although the core bound, the E-mode check, m and the wind-down check hold); with S following R after t_a the run
    is not in the proven case and only the earlier checks count; a run without the reserve record keeps the earlier
    T0g checks."""
    def rep(alg_last, followed, reserve=(0.5, 0.3, 0.9), wd="adaptive"):
        r = _rep("T0g", 1.0, 2, [1, 2, 4], [0.5] * 3, [1, 2, 9], W=0.0)
        r["guard"]["reserve"] = list(reserve)
        r["safe"]["followed"] = followed
        r["wind_down"] = wd
        return r, _res([1, 1, alg_last - 2])
    fb = [["FB", 0, 3]]
    r, res = rep(4.2, fb)
    c = qs.certificate(res, None, r, core_exact=False)
    assert c["reserve"] and c["proven_case"] and c["fb_after_t_a"] and abs(c["budget_t_a"] - 0.3) < 1e-12
    assert abs(c["wind_down_cost"] - 0.2) < 1e-12 and c["wind_down_ok"] and c["e_mode_reserve_ok"] and c["held"]
    r, res = rep(4.4, fb)
    c = qs.certificate(res, None, r, core_exact=False)
    assert c["core_bound_ok"] and not c["wind_down_ok"] and not c["held"]
    r, res = rep(4.4, [["FB", 0, 2], ["R", 2, 1]])
    c = qs.certificate(res, None, r, core_exact=False)
    assert not c["proven_case"] and not c["wind_down_ok"] and c["held"]          # case (c): measured only
    r, res = rep(4.4, fb, wd="keep")
    assert not qs.certificate(res, None, r, core_exact=False)["proven_case"]
    r, res = rep(4.2, fb, reserve=(0.5, 0.6, 0.9))                               # ALG(1) + R(1) = 2.6 > 2.5
    c = qs.certificate(res, None, r, core_exact=False)
    assert c["core_bound_ok"] and c["e_mode_ok"] and c["m_ok"] and c["proven_case"] and c["wind_down_ok"], c
    assert not c["e_mode_reserve_ok"] and not c["held"], c                      # fails by the reserve check alone
    r, res = rep(4.4, fb)
    del r["guard"]["reserve"]
    c = qs.certificate(res, None, r, core_exact=False)
    assert not c["reserve"] and "wind_down_ok" not in c and c["held"]


def test_params_check():
    """q44_summary.params_check (§5.4) on hand-made rows: GUARD_DEFAULTS are guard.Guarded's defaults (test T0g,
    wind_down auto, reserve true); PS-G runs with A8's resolved default parameters pass as 'current'; runs with the
    historical T0 defaults (as recorded by the Tier 1 run files: test T0, no wind_down, no reserve) pass as 'T0'; both
    together are 'mixed'; a PS-G run with reserve false (the T0g of commit d2a538d, outside Theorem W) or with another
    test fails, with the mismatch named; rows of other tags are not checked."""
    from sublet.algos import guard
    from sublet.experiments import q44_summary as qsum
    P = guard.Guarded.PARAMS
    assert all(P[k] == pytest.approx(v) if isinstance(v, float) else P[k] == v for k, v in qs.GUARD_DEFAULTS.items())
    cur = {k: copy.deepcopy(v) for k, v in P.items() if k != "inner_params"}
    old = {"safe": "fb+pd", "S_rbar": "theory", "gamma": 1.0, "gamma_T11": 1.7071067811865475, "test": "T0",
           "B0": "auto", "kappa": 10.0, "abort_at": None, "inner": "A7"}

    def check(*params, tag="PS-G"):
        rows = [{"tag": tag, "params": p, "file": f"r{i}.json"} for i, p in enumerate(params)]
        return qsum.params_check(SimpleNamespace(rows=rows))
    c = check(cur, cur)
    assert c["status"] == "pass" and c["defaults"] == {"current": 2} and c["runs"] == 2, c
    c = check(old)
    assert c["status"] == "pass" and c["defaults"] == {"T0": 1}, c
    assert check(cur, old)["status"] == "mixed"
    for k, v in (("reserve", False), ("test", "T1"), ("wind_down", "keep")):
        c = check(cur, {**cur, k: v})
        assert c["status"] == "fail" and [m["param"] for m in c["mismatches"]] == [k], (k, c)
    assert check({**cur, "reserve": False}, tag="PS-G-T0g")["status"] == "not run"


# ---------------------------------------------------------------- the smoke run (§6.3)
def _toy_rate() -> dict:
    """toy.json with L0's R drawn from R_rate, so that config seeds 7 and 8 build different instances."""
    return toy_config({"lenders.0.R": DELETE, "lenders.0.R_rate": 0.3})


def _blocks(tmp_path):
    bd = tmp_path / "blocks"
    bd.mkdir()
    inst = {"id": "I1", "family": "I1", "config": _toy_rate(), "overrides": {}, "config_seeds": [7, 8],
            "tuning_seeds": [7]}
    dup = {**copy.deepcopy(inst), "id": "I1-dup", "config_seeds": [8], "tuning_seeds": []}
    q1 = {"block": "Q1", "tier": 1, "grid": "1min", "lb": None, "description": "toy smoke (§6.3), own grid",
          "policies": ["BL0a", "BL1", "BL2", "BL5", "PS", "PS-G", "BL1-G", "BL5-G"], "policy_seeds": [0, 1],
          "modes": ["L-tr", "L-eg"], "instances": [inst, dup]}
    q5 = {**copy.deepcopy(q1), "block": "Q5", "grid": "slow", "lb": "per_schedule",
          "description": "toy smoke (§6.3), slow grid with LBs"}
    q6 = {"block": "Q6", "tier": 1, "grid": "core", "lb": "exact", "description": "family smoke",
          "policies": ["PS", "PS-G", "PS-GR", "BL1", "BL1-G", "RR_RENEW"], "policy_seeds": [0, 1],
          "families": [{"id": "F1", "kind": "fam", "m": [2], "rho": [4], "tau": 2, "H": 1, "T": 48, "modes": ["F-ad"]},
                       {"id": "F3", "kind": "c3p5", "beta": [14], "T": [48], "modes": ["F-eg"],
                        "exclude_policies": ["RR_RENEW"]}]}
    for b in (q1, q5, q6):
        (bd / f"{b['block']}.json").write_text(json.dumps(b))
    return bd


def test_study_smoke(tmp_path, monkeypatch):
    """§6.3: q44_study.py on toy.json with two modes (L-tr, L-eg; two config seeds, two policy seeds; block Q1 on
    the toy's own grid, block Q5 on the slow grid with LBs) and a small family block writes one run file per run
    (BL2: the _sum file), one LB file per oblivious slow-grid cell-mode and per family schedule (per run under
    F1's adaptive lender), the cell and job records, and summary.json with D1-D6 and the checks; the duplicate
    cell (I1-dup, 8) is dropped; every guarded run's certificate holds (V6 on the family runs)."""
    pytest.importorskip("sublet.algos.a7")
    pytest.importorskip("sublet.algos.guard")
    from sublet.experiments import q44_summary as qsum
    out = tmp_path / "q44"
    monkeypatch.setenv("SUBLET_Q44_DIR", str(out))
    bd = _blocks(tmp_path)
    assert qs.out_root() == out
    jobs = [j for b in ("Q1", "Q5", "Q6") for j in qs.list_jobs(qs.load_block(b, bd))]
    assert sum(1 for j in jobs if j["kind"] == "lb") == 6 and all(j["alone"] for j in jobs if j["kind"] == "lb")
    for j in jobs:
        rec = qs.run_job(j["id"], out, bd)
        assert rec["status"] == "ok", (j["id"], rec)
    qs.manifest(["Q1", "Q5", "Q6"], out, bd)
    for blk, grid in (("Q1", "1min"), ("Q5", "slow")):
        for inst, c in (("I1", 7), ("I1", 8), ("I1-dup", 8)):
            for md in ("L-tr", "L-eg"):
                d = out / "runs" / blk / inst / grid / md
                for tag in ("BL0a", "BL1", "BL5", "PS", "PS-G", "BL1-G", "BL5-G"):
                    for p in (0, 1):
                        js = json.loads((d / f"{tag}_c{c}_l{c}_p{p}.json").read_text())
                        assert js["q44"]["tag"] == tag and js["meta"]["run_spec_name"] == tag
                        assert js["meta"]["git_revision"] and \
                            js["q44"]["intensity"]["announcements_per_site_day"] is not None
                assert (d / f"BL2_c{c}_l{c}_p0_sum.json").is_file() and (d / f"cell_c{c}.json").is_file()
                assert (out / "lb" / blk / inst / md / f"lb_c{c}_l{c}.json").is_file() == (blk == "Q5")
    assert (out / "lb" / "Q6" / "F3_b14_T48" / "F-eg" / "lb_c0_l0.json").is_file()
    assert (out / "lb" / "Q6" / "F1_m2_r4" / "F-ad" / "PS-G_c0_l0_p1.json").is_file()      # per run (adaptive)
    S = qsum.summarize(out, fig=True)
    js = json.loads((out / "summary.json").read_text())
    for k in ("D1", "D2", "D3", "D4", "D5", "D6", "checks", "certificate_full_model"):
        assert k in js, k
    assert (out / "tables.md").is_file() and len(S["figures"]) == 3
    assert S["duplicates"] and all(d["cell"][2] == "I1-dup" for d in S["duplicates"])
    assert S["D1"]["I1"]["cells"] == [["I1", 8]]           # c7 is the tuning cell, (I1-dup, 8) a duplicate
    assert S["D1"]["I1"]["r_best"]["PS-G"]["median"] is not None
    for v in ("V2", "V4", "V5", "V6", "V7", "PS-G_params"):
        assert S["checks"][v]["status"] == "pass", (v, S["checks"][v])
    assert S["certificate_full_model"]["all_held"], S["certificate_full_model"]
    assert S["D5"]["certificate"]["all_held"]
    assert S["D5"]["families"]["F1"]["F1_m2_r4:F-ad"]["ratio"]["BL1"]["mean"] == pytest.approx(3.3684210526, rel=1e-9)
    assert S["D5"]["families"]["F3"]["F3_b14_T48:F-eg"]["ratio"]["PS"]["mean"] == pytest.approx(5.026, abs=5e-4)
    for r in qsum.load_runs(out)[0]:
        if r["policy_id"] == "A8":
            assert r["certificate"]["available"] and r["certificate"]["held"], r["file"]


def test_out_root_is_absolute(tmp_path, monkeypatch):
    """A relative output folder is resolved against the working directory, not left relative: drivers.run
    resolves a relative out_dir against the repository root, so a relative root would split one job's run
    files from the files the study reads back (the first Tier 1 run lost 275 jobs that way)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SUBLET_Q44_DIR", raising=False)
    assert qs.out_root("rel/q44") == tmp_path / "rel" / "q44"
    monkeypatch.setenv("SUBLET_Q44_DIR", "env/q44")
    assert qs.out_root() == tmp_path / "env" / "q44"
    assert qs.out_root().is_absolute() and qs.out_root(None).is_absolute()
    d = qs.out_root("rel/q44") / "runs"
    assert drun._out_dir({"out": "unused"}, d) == d


# ---------------------------------------------------------------- Tier 2 block T2_t0g (test T0g against T0)
def test_t2_t0g_block_matches_tier1():
    """T2_t0g reruns the A8 rows PS-G, BL1-G and BL5-G of Q1, Q2 and Q6 under test T0g with the same cells, modes
    and seeds: every T0g tag is its T0 partner's parameters plus test = 'T0g'; the instances are Q1's and Q2's
    (config, overrides, config and tuning seeds, modes) and the families Q6's (values, modes, policy seeds); its
    jobs are the cell-modes of Q1 and Q2 and the family instance-modes of Q6 (223 jobs, none alone), and the
    dry-run estimate covers each of them."""
    t2 = qs.load_block("T2_t0g")
    assert t2["tier"] == 2 and "T2_t0g" not in qs.TIER1 and t2["policies"] == list(qs.T0G_PAIRS)
    for tg, base in qs.T0G_PAIRS.items():
        assert qs.POLICIES[tg] == {"id": "A8", "params": {**qs.POLICIES[base]["params"], "test": "T0g"}}
        assert qs.POLICIES[base]["id"] == "A8" and "test" not in qs.POLICIES[base]["params"]
    q1, q2, q6 = (qs.load_block(b) for b in ("Q1", "Q2", "Q6"))
    keys = ("config", "overrides", "config_seeds", "tuning_seeds")
    ref = {i["id"]: (i, q1["modes"]) for i in q1["instances"]} | {i["id"]: (i, q2["modes"]) for i in q2["instances"]}
    assert {i["id"] for i in t2["instances"]} == set(ref)
    for i in t2["instances"]:
        r, modes = ref[i["id"]]
        assert all(i[k] == r[k] for k in keys) and qs.instance_modes(t2, i) == modes, i["id"]
        assert qs.instance_policies(t2, i) == ["BL0a"] + list(qs.T0G_PAIRS)
    assert t2["policy_seeds"] == q1["policy_seeds"] == q2["policy_seeds"] and t2["grid"] == q1["grid"]
    fam6 = {f["id"]: f for f in q6["families"]}
    for f in t2["families"]:
        g = fam6[f["id"]]
        assert all(f[k] == g[k] for k in ("kind", "m", "rho", "tau", "H", "T", "beta", "modes") if k in g)
        assert f["policy_seeds"] == q6["policy_seeds"]
    ids = [j["id"].split(":", 1)[1] for j in qs.list_jobs(t2)]
    want = [j["id"].split(":", 1)[1] for b in (q1, q2, q6) for j in qs.list_jobs(b) if j["kind"] in ("cells", "family")]
    assert sorted(ids) == sorted(want) and len(ids) == 223
    e = qs.estimate(["T2_t0g"], workers=2)
    assert len(e["jobs"]) == 223 and all(j["est_s"] > 0 for j in e["jobs"]) and e["alone_s"] == 0
    assert {qs._tag_class(t) for t in qs.T0G_PAIRS} == {"t0g"}


def test_tier2_instance_ref_block():
    """The Tier 2 table takes r_best's renting baselines (and BL0a) from an instance's own ref_block when it names
    one, else from the block's: T2_t0g names Q1, and Q2 for I3, whose cells are Q2's. On hand-made cell means
    (oracle: hand computation) I3's r_best uses Q2's BL1, BL2 and BL5 (not a decoy row of Q1), I1's uses Q1's; a
    block without per-instance references (T2_guard) reports none, and an instance key ref_block passes the block
    check."""
    pytest.importorskip("sublet.algos.guard")
    from sublet.experiments import q44_summary as qsum
    assert qsum._ref_blocks("T2_t0g") == ("Q1", {"I3": "Q2"}) and qsum._ref_blocks("T2_guard") == ("Q1", {})
    assert "ref_block" in qs.INSTANCE_KEYS and qs.load_block("T2_t0g")["instances"][-1]["ref_block"] == "Q2"
    st = qsum.Study.__new__(qsum.Study)
    k3 = ("T2_t0g", "I3", "I3", "c1", "1min", "L-tr")
    k1 = ("T2_t0g", "I1", "I1", "c3", "1min", "L-tr")
    kg = ("T2_guard", "I1", "I1", "c3", "1min", "L-tr")
    st.rows = [{"block": "T2_t0g", "tier": 2}, {"block": "T2_guard", "tier": 2}]
    st.cm = {k3: {"BL0a": 10.0, "PS-G-T0g": 6.0}, ("Q2",) + k3[1:]: {"BL1": 4.0, "BL2": 5.0, "BL5": 3.0},
             ("Q1",) + k3[1:]: {"BL1": 1.0, "BL2": 1.0, "BL5": 1.0},
             k1: {"BL0a": 8.0, "PS-G-T0g": 4.0}, ("Q1",) + k1[1:]: {"BL1": 2.0, "BL2": 2.5, "BL5": 3.0},
             kg: {"BL0a": 8.0, "PS-G-T0g": 5.0}}
    st.dups, st.tags = set(), ["BL0a", "PS-G-T0g"]
    out = qsum.tier2(st)
    t = out["T2_t0g"]
    assert t["ref_block"] == "Q1" and t["ref_block_by_instance"] == {"I3": "Q2"}
    assert t["table"]["I3|L-tr"]["PS-G-T0g"] == {"r0": 0.6, "r_best": 2.0}
    assert t["table"]["I1|L-tr"]["PS-G-T0g"] == {"r0": 0.5, "r_best": 2.0}
    assert "ref_block_by_instance" not in out["T2_guard"] and out["T2_guard"]["table"]["I1|L-tr"]["PS-G-T0g"] == \
        {"r0": 0.625, "r_best": 2.5}


def test_summary_t0g_pairing(tmp_path, monkeypatch):
    """q44_summary pairs T0g runs with T0 runs of the same base tag (t0g_pairs): on the toy (two cells, L-tr and
    L-eg, two policy seeds) and a small family (F3, beta 14, T = 48), blocks Q1 and Q6 with the T0 variants PS-G-T0,
    BL1-G-T0 and BL5-G-T0 (before 2026-10-17, when T0 was A8's default, these blocks ran PS-G, BL1-G and BL5-G) and
    block T2_t0g with the T0g tags; every T0g run is paired (same cell, mode and seeds) and has the wind-down
    reserve; the abort classes of each tag and mode add up to its pairs; on the family (exact core export, R = 0,
    T0g <= T0 at every slot) T0g never aborts earlier and the certificate holds; on the toy every T0g run has
    m = 0, passes the E-mode checks with and without the reserve, and in Theorem W's proven case its wind-down
    cost is at most its budget; summary.json has 'T0g' and tables.md its section; without T0g runs neither
    appears. (On the toy, T0g can abort earlier than T0: test_guard.py::test_t0g_earlier_than_t0_toy.)"""
    pytest.importorskip("sublet.algos.guard")
    from sublet.experiments import q44_summary as qsum
    out = tmp_path / "q44"
    monkeypatch.setenv("SUBLET_Q44_DIR", str(out))
    bd = tmp_path / "blocks"
    bd.mkdir()
    inst = {"id": "I1", "family": "I1", "config": _toy_rate(), "overrides": {}, "config_seeds": [7, 8],
            "tuning_seeds": [7]}
    tags0 = ["BL0a", "BL1", "BL5", "PS-G-T0", "BL1-G-T0", "BL5-G-T0"]
    fam = [{"id": "F3", "kind": "c3p5", "beta": [14], "T": [48], "modes": ["F-eg"]}]
    blocks = [{"block": "Q1", "tier": 1, "grid": "1min", "lb": None, "policies": tags0, "policy_seeds": [0, 1],
               "modes": ["L-tr", "L-eg"], "instances": [inst]},
              {"block": "Q6", "tier": 1, "grid": "core", "lb": "exact", "policies": ["PS-G-T0", "BL1-G-T0", "BL5-G-T0"],
               "policy_seeds": [0, 1], "families": fam},
              {"block": "T2_t0g", "tier": 2, "grid": "1min", "lb": None, "ref_block": "Q1",
               "policies": list(qs.T0G_PAIRS), "policy_seeds": [0, 1], "modes": ["L-tr", "L-eg"],
               "instances": [copy.deepcopy(inst)], "families": [{**copy.deepcopy(fam[0]), "policy_seeds": [0, 1]}]}]
    for b in blocks:
        (bd / f"{b['block']}.json").write_text(json.dumps(b))
    for b in ("Q1", "Q6"):
        for j in qs.list_jobs(qs.load_block(b, bd)):
            assert qs.run_job(j["id"], out, bd)["status"] == "ok", j["id"]
    S0 = qsum.summarize(out, fig=False)
    assert "T0g" not in S0 and "T0g against T0" not in (out / "tables.md").read_text()
    for j in qs.list_jobs(qs.load_block("T2_t0g", bd)):
        assert qs.run_job(j["id"], out, bd)["status"] == "ok", j["id"]
    S = qsum.summarize(out, fig=False)
    T = S["T0g"]
    assert set(T["pairs"]) == {"I1", "F3"}
    n = 0
    for fam_id, mm in T["pairs"].items():
        for md, tt in mm.items():
            assert set(tt) == set(qs.T0G_PAIRS), (fam_id, md)
            for tg, e in tt.items():
                assert e["unpaired"] == 0 and e["pairs"] == (4 if fam_id == "I1" else 2), (fam_id, md, tg, e)
                assert e["reserve"] == e["pairs"], (fam_id, md, tg, e)
                trips = [k for k in ("earlier", "same", "later", "T0g_none_T0_abort", "T0g_abort_T0_none")]
                both0 = e["pairs"] - round(e["pairs"] * e["trips_per_run_T0"]) - e["T0g_abort_T0_none"]
                assert sum(e[k] for k in trips) + both0 == e["pairs"], (fam_id, md, tg, e)
                if fam_id == "F3":
                    assert e["earlier"] == 0 and e["T0g_abort_T0_none"] == 0, (fam_id, md, tg, e)
                n += e["pairs"]
    assert n == 3 * (2 * 4 + 2)
    assert T["certificate_core"]["all_held"], T["certificate_core"]
    full = T["certificate_full_model"]["by_tag_mode"]
    assert sum(v["runs"] for v in full.values()) == 3 * 2 * 4
    assert all(v["m_fail"] == 0 and v["e_mode_fail"] == 0 and v["available"] == v["runs"] for v in full.values()), full
    assert all(v["reserve"] == v["runs"] and v["e_mode_reserve_fail"] == 0 and v["wind_down_fail"] == 0
               for v in full.values()), full
    assert "T0g against T0" in (out / "tables.md").read_text()
    assert set(S) - set(S0) == {"T0g"}
