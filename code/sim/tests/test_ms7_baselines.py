"""Tests of MS7's baselines and stress regimes (design/ms7/plan.md X4, X5; change C54; design/ms7/feasibility/
baselines.md §2, §3): the options of BL2, BL3 and BL4, A9-P (algos/a9p.py), the MPC baseline (baselines/mpc.py), the
lender groups 'region', the registry's MS7 rows, the driver layer ms7_baselines.py, the driver e7r.py, its scripts
e7r_select.py and e7r_analysis.py, and run_e7r.sh.

Quick (no raw data):
- frozen behaviour: BL2, BL3 and BL4 at their defaults reproduce the runs of commit 56b847be (before C54) bit for bit,
  report included (DIGESTS, measured with _digest on a clean tree of that commit), also with every new option passed
  at its default; params() at the defaults lists only the MS2 keys (QUIET_KEYS);
- the options: validation, contract_rule 'c2' buys only kbar (and BL4 kbar or the cheapest flagged contract) on a toy
  menu where kbar differs from k*, BL3's extras per pool and per LLM on hand-made pools and on engine runs;
- BL1 as A9 flags (ms7_baselines.BL1_AS_A9) reproduces BL1's ledger (the identity of feasibility §1(c));
- A9-P: protected_only buys only flagged contracts and its cost does not depend on the lender's schedule; with
  protected_only false it is A9 (same ledger); A9's frozen keys are unchanged;
- MPC: plan class P1, the LP's size, the forecasts, deterministic rounding, replanning every replan_slots slots,
  noticed leases never released, the oracle's driver input and information class, the holding models ('stage' plans
  releases inside the window, 'window' cannot; no release inside a billed term);
- lender groups 'region' (lender._correlated): shocks stay within a region; config validation;
- the registry's MS7 dict; COPY_PARTS['e7r']; plan class P1 of the MS7 ids and the C54 options on ms2_multi_small
  (test_policy_isolation's P1 cases cover POLICY_IDS only);
- ms7_baselines: the modes, W0+, the tags (no clash with ms5b_common.TAGS), the grids (at most 24 configurations, g00
  the as-built setting, KNOB_DEFAULTS against the classes' PARAMS), the tuned tags, L-pk's offset rule on a synthetic
  instance (also for a series whose length is not a multiple of a day), the gate;
- e7r: the job lists (weeks, modes, counts; reduced lists on the development cell only; confirm and eval need the
  selection, in a full run one of the registered script on a tune summary of HEAD), the gate; e7r_select's rules T and
  W and e7r_analysis's tables (main's seven modes before eval's), margins (per metric and per mode), best of each
  comparison set, the i.i.d. intensity curve and the checks (identity, also of MS5b rule tags, and provenance) on
  synthetic summaries; the scripts' constants against ms7_baselines; run_e7r.sh (bash -n, its argument checks).
With the a12 outputs (needs_a12): on the 2-hour E7 week instance of bench_e7f seed 101, BL1's identity, kbar != k* and
the c2 tags buying kbar, MPC's routing by site region (fewer routes than BL4's arcs), L-pk's instance (offsets moved,
sites, prices, demand and references kept, reclaims moved) and one e7r week job under L-pk and L-co-reg-1 through the
runner.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import types
from pathlib import Path

import numpy as np
import pytest

from fixtures import SIM, random_toy_config, toy_config

from sublet.algos import registry
from sublet.algos.a9 import NoticeCriticalRatio
from sublet.algos.a9p import ProtectedOnly
from sublet.algos.common import PolicyError, treated_as_protected
from sublet.baselines.cocar import CoCaRStyle
from sublet.baselines.common import c2_base_contracts, k_star
from sublet.baselines.mpc import RecedingLP, nearest_counts
from sublet.baselines.ski import SkiRental
from sublet.baselines.spothedge import Pool, SpotHedgeStyle
from sublet.drivers import run as drun
from sublet.drivers.run import make_policy
from sublet.drivers.siloed import run_siloed
from sublet.engine import EngineConfig, simulate
from sublet.experiments import e7r
from sublet.experiments import e7r_analysis as ea
from sublet.experiments import e7r_select as es
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms5b_common as m5
from sublet.experiments import ms7_baselines as m7
from sublet.instance import build_instance, public_view
from sublet.types import Buy, LenderModel, Release

RUN = SIM / "sublet" / "experiments" / "run_e7r.sh"
SPARES_LLM_PARAMS = {"n_extra": 2, **m7.SPARES_LLM}
IID = {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.3}}
EAGER = {"schedule": "eager", "params": {}}


# ---------------------------------------------------------------- digests (frozen behaviour)
def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()
                if "time_s" not in str(k) and "wall_s" not in str(k) and str(k) != "lp_seconds"}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return float(x).hex()
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def _digest(res) -> str:
    comp = {k: float(v).hex() for k, v in sorted(res.components.items())}
    leases = [[L.site, L.contract, L.gpus, L.start_slot, L.start_min, L.prepaid_end_min, L.announce_slot, L.death_min,
               L.release_min, L.end_min, L.end_cause, float(L.prepaid_usd).hex(), float(L.rent_usd).hex(), L.tag]
              for L in res.leases]
    rep = _jsonable(res.metrics.get("policy") or {})
    blob = json.dumps({"components": comp, "leases": leases, "report": rep}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


# sha256 of _digest(run) on commit 56b847be (before C54); 'multi' is ms2_multi_small.json at 720 min (lender seed 1,
# policy seed 0; BL2 through run_siloed, the sha256 of its sub-runs' digests in order), toy and rand<s> as
# tests/test_ms5b_additions.py builds them (trace: seed 0; iid: iid_step p 0.3, seed 3)
DIGESTS = {
    'toy:BL3:{}:trace': "e87378122aadfe52f43933d3f26275938f380ba3da8af44b7e239aa8418380b3",
    'toy:BL3:{}:iid': "17604d741c9efc44cdaf429ce1371f6d12d017a918710a778c73239a75b4ace1",
    'toy:BL3:{"n_extra": 0}:trace': "41348b629fa8cc5af5c3a1d720d3eb624d43151223da7297079b25bfc8b53f45",
    'toy:BL4:{}:trace': "d4d917d344239c531350104e0bfeb6d223b61b3d16b48a6d5fc587a3d5ad85bd",
    'toy:BL4:{}:iid': "e025475f00633e9109501c03b7aae43d74220ab2697c498d493f5c20e5c39906",
    'rand0:BL3:{}:trace': "78c586599eee2bcbb3195f1818411f4e37d7bc5de7e6d3c5d9ffa85b0889f3d8",
    'rand0:BL3:{"n_extra": 1, "react_at": "death"}:iid':
        "35bc6ff833bd69bcf69c31806ef688b7322583a77f90dbf74adb9899ddb9c8fa",
    'rand0:BL4:{"demand": "oracle"}:trace': "f9648b16ed0608734f2b8b54bb88cb684e6eb8c405f28a9e8852405c6f7fbe78",
    'rand1:BL3:{"n_extra": 1, "zone": "group"}:trace':
        "0b116208218ff23e174b8b5c647fa872c92c9963e0f8305e4c752b419748ff8f",
    'rand1:BL4:{"window_min": 30}:iid': "36eeeedbd4711b50cb10834b60f9159c42821b1ebcf659ed4ca8cdf3ac850992",
    'multi:BL2:{}:trace': "99e6fc253ab096d8b5edc5ab277f46b3e441883f9d0aa9be08d94b6df584f6b6",
    'multi:BL2:{"keep": "s0"}:eager': "bfd5400e1a5a8cc06b128b7cf647cc5bc4a2e57170d9a0aee66be69ffac189ea",
    'multi:BL3:{}:trace': "77ee9407776ecbbef35160bb6916e824fdb8c4c4715cabc9fac49b3112d070b8",
    'multi:BL3:{"n_extra": 0}:eager': "ca3601fcac3b40dfbfb9bd000b3602aacebcf2d1f0e15018f3c91b9bfae6b9db",
    'multi:BL4:{}:trace': "9df5e3efb9edb45705ecbc2a713f9520b25d29726d78477e530dd0b0dea43ad8",
    'multi:BL4:{}:eager': "a1c6671e52f1b36bfd61a8fea0c9b6db4a6f3dbb961d7fde8ef665a163c0260d",
}
NEW_DEFAULTS = {"BL2": {"contract_rule": "kstar"}, "BL3": {"contract_rule": "kstar", "extra_scope": "pool",
                                                         "extra_when_idle": True},
                "BL4": {"contract_rule": "kstar"}}


def _cfg(name: str) -> dict:
    if name == "toy":
        return toy_config()
    s = int(name[4:])
    return random_toy_config(np.random.default_rng(100 + s), n_clients=2, two_llms=bool(s % 2))


def _multi(lm: dict):
    spec = drun.load_run_spec({"schema_version": 1, "name": "c54", "instance": "ms2_multi_small.json",
                               "overrides": {"time.horizon_min": 720}, "lender_model": lm,
                               "policy": {"id": "BL1", "params": {}}})
    return drun.build(spec, spec["seeds"]["config"][0])


def _case_digest(name: str, params_extra: dict) -> str:
    cname, pid, rest = name.split(":", 2)
    ptxt, lname = rest.rsplit(":", 1)
    params = {**json.loads(ptxt), **params_extra}
    sp = {"policy": {"id": pid, "params": params}}
    if cname == "multi":
        inst, model, ecfg = _multi(EAGER if lname == "eager" else {})
        if pid == "BL2":
            d = run_siloed(inst, lambda sub: make_policy(sp, sub), model, ecfg, policy_seed=0)
            return hashlib.sha256("".join(_digest(r) for r in d["results"]).encode()).hexdigest()
        return _digest(simulate(inst, make_policy(sp, inst), model, ecfg, lender_seed=1, policy_seed=0))
    inst = build_instance(_cfg(cname))
    lm, seed = (IID, 3) if lname == "iid" else ({}, 0)
    model = LenderModel(**{"schedule": "trace", "information": "I1", **lm})
    res = simulate(inst, make_policy(sp, inst), model, EngineConfig(check_invariants=True), lender_seed=seed,
                   policy_seed=seed)
    assert not res.invariant_failures, res.invariant_failures[:3]
    return _digest(res)


@pytest.mark.parametrize("name", sorted(DIGESTS))
def test_defaults_reproduce_runs(name):
    """BL2, BL3 and BL4 at their defaults, and with every C54 option at its default, give the runs of 56b847be."""
    pid = name.split(":")[1]
    assert _case_digest(name, {}) == DIGESTS[name], name
    assert _case_digest(name, NEW_DEFAULTS[pid]) == DIGESTS[name], name


def test_params_quiet_at_defaults():
    assert SkiRental().params() == {"keep": "none", "defer_release": True}
    assert SpotHedgeStyle().params() == {"n_extra": 2, "react_at": "notice", "zone": "lender", "hysteresis_min": 10,
                                         "defer_release": True}
    assert CoCaRStyle().params() == {"window_min": 60, "demand": "previous"}
    for cls, new in ((SkiRental, NEW_DEFAULTS["BL2"]), (SpotHedgeStyle, NEW_DEFAULTS["BL3"]),
                     (CoCaRStyle, NEW_DEFAULTS["BL4"])):
        assert cls(**new).params() == cls().params()
        assert set(new) <= set(cls.QUIET_KEYS)          # a sibling unit (C53) may add its own quiet keys
    assert SkiRental(contract_rule="c2").params()["contract_rule"] == "c2"
    p = SpotHedgeStyle(extra_scope="llm", extra_when_idle=False).params()
    assert p["extra_scope"] == "llm" and p["extra_when_idle"] is False
    assert CoCaRStyle(contract_rule="c2").params()["contract_rule"] == "c2"
    # A9's frozen keys (tests/test_a9.py) are unchanged: A9-P is a subclass
    assert "protected_only" not in NoticeCriticalRatio.PARAMS and "protected_only" not in NoticeCriticalRatio.OWN_PARAMS
    assert NoticeCriticalRatio().params() == NoticeCriticalRatio.PARAMS


def test_option_validation():
    bad = [(SkiRental, {"contract_rule": "k*"}), (SpotHedgeStyle, {"contract_rule": "x"}),
           (SpotHedgeStyle, {"extra_scope": "zone"}), (SpotHedgeStyle, {"extra_when_idle": 1}),
           (CoCaRStyle, {"contract_rule": "c3"}), (RecedingLP, {"forecast": "arima"}),
           (RecedingLP, {"replan_slots": 0}),
           (RecedingLP, {"replan_slots": True}), (RecedingLP, {"ewma_alpha": 0.0}), (RecedingLP, {"ewma_alpha": 1.5}),
           (RecedingLP, {"rounding": "up"}), (RecedingLP, {"window_min": 0}), (RecedingLP, {"forecast": "oracle"}),
           (RecedingLP, {"forecast": "previous_day", "window_min": 1440}), (ProtectedOnly, {"protected_only": "yes"}),
           (ProtectedOnly, {"demand": "previous"})]
    for cls, kw in bad:
        with pytest.raises(PolicyError):
            cls(**kw)


# ---------------------------------------------------------------- contract_rule 'c2'
def c2_toy() -> dict:
    """A toy whose two revocable contracts share tau with different notices, so that P3 drops the cheaper one with no
    notice and kbar differs from k* (k*: cheapest)."""
    cfg = toy_config()
    cfg["contracts"] = [{"id": "h0", "tau_min": 5, "H_min": 0}, {"id": "h10", "tau_min": 5, "H_min": 10},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": 5}]
    for L, pr in zip(cfg["lenders"][:2], ((2.85, 3.0), (2.9, 3.1))):
        L["menu"] = ["h0", "h10"]
        L["prices"] = {"h0": pr[0], "h10": pr[1]}
    return cfg


def test_c2_buys_kbar():
    inst = build_instance(c2_toy())
    view = public_view(inst, "I1")
    kb, ks = c2_base_contracts(view), k_star(view)
    rev = [l for l, s in enumerate(view.sites) if s.kind != "protected"]
    assert any(kb[l, 0] != ks[l] for l in rev), "kbar equals k* on the c2 toy: the test is vacuous"
    model = LenderModel(schedule="iid_step", params={"D_slots": 1, "p": 0.3})
    for pid, params in (("BL3", {"n_extra": 0, "contract_rule": "c2"}), ("BL4", {"contract_rule": "c2"}),
                        ("MPC", {"contract_rule": "c2"}), ("BL5", {"use_current_slot": True, "contract_rule": "c2"})):
        res = simulate(inst, make_policy({"policy": {"id": pid, "params": params}}, inst), model,
                       EngineConfig(check_invariants=True), lender_seed=2, policy_seed=0)
        assert not res.invariant_failures and res.leases, pid
        for L in res.leases:
            assert L.contract == kb[L.site, 0] or treated_as_protected(view, L.contract), (pid, L)
        assert any(L.contract == kb[L.site, 0] != ks[L.site] for L in res.leases), pid
        rep = res.metrics["policy"]
        assert rep["contracts"] == [[int(k) for k in row] for row in kb], pid
    # BL2 per borrower through run_siloed
    d = run_siloed(inst, lambda sub: make_policy({"policy": {"id": "BL2", "params": {"contract_rule": "c2"}}}, sub),
                   model, EngineConfig(check_invariants=True), lender_seed=2, policy_seed=0)
    leases = [L for r in d["results"] for L in r.leases]
    assert leases and all(L.contract == kb[L.site, 0] for L in leases)


def test_bl1_identity_as_a9_flags():
    """BL1 = A9 with BL1_AS_A9 (feasibility §1(c)): the same ledger on the toys and ms2_multi_small."""
    cases = [(build_instance(_cfg(n)), LenderModel(**{"schedule": "trace", "information": "I1", **lm}),
              EngineConfig(check_invariants=True), s)
             for n in ("toy", "rand0", "rand1") for lm, s in (({}, 0), (IID, 3))]
    inst, model, ecfg = _multi(EAGER)
    cases.append((inst, model, ecfg, 1))
    for inst, model, ecfg, s in cases:
        a = simulate(inst, make_policy({"policy": {"id": "BL1", "params": {}}}, inst), model, ecfg, lender_seed=s,
                     policy_seed=s)
        b = simulate(inst, make_policy({"policy": {"id": "A9", "params": dict(m7.BL1_AS_A9)}}, inst), model, ecfg,
                     lender_seed=s, policy_seed=s)
        assert a.components["total"] == b.components["total"]
        key = [(L.site, L.contract, L.start_slot, L.end_min, L.end_cause) for L in a.leases]
        assert key == [(L.site, L.contract, L.start_slot, L.end_min, L.end_cause) for L in b.leases]


# ---------------------------------------------------------------- BL3's spares
def _pools(pol, spec):
    pol.pools = [Pool(i, llm, (i,), (0,), {0: "z"}, ("z",), {"z": 1.0}, N_tar=nt) for i, (llm, nt) in enumerate(spec)]
    pol._pools_of_llm = {}
    for p in pol.pools:
        pol._pools_of_llm.setdefault(p.llm, []).append(p)
    pol._extra_default = pol._params["extra_scope"] == "pool" and bool(pol._params["extra_when_idle"])
    pol.spare_slots = 0


def test_bl3_extras_rule():
    spec = [(0, 3), (0, 0), (0, 5), (1, 0), (1, 0)]
    pol = SpotHedgeStyle(n_extra=3)
    _pools(pol, spec)
    assert pol._extras() == {0: 3, 1: 3, 2: 3, 3: 3, 4: 3}                    # BLD-14: n_extra per pool, also idle
    pol = SpotHedgeStyle(n_extra=3, extra_when_idle=False)
    _pools(pol, spec)
    assert pol._extras() == {0: 3, 1: 0, 2: 3, 3: 0, 4: 0}
    pol = SpotHedgeStyle(n_extra=3, extra_scope="llm", extra_when_idle=False)
    _pools(pol, spec)
    assert pol._extras() == {0: 1, 1: 0, 2: 2, 3: 0, 4: 0}                    # LLM 0: pools 2, 0, 2; LLM 1 idle
    pol = SpotHedgeStyle(n_extra=5, extra_scope="llm")
    _pools(pol, spec)
    assert pol._extras() == {0: 2, 1: 1, 2: 2, 3: 3, 4: 2}                    # cyclic over (-N_tar, id)
    assert pol.spare_slots == 10


def test_bl3_llm_spares_engine():
    inst = build_instance(_cfg("rand1"))
    model = LenderModel(schedule="iid_step", params={"D_slots": 1, "p": 0.3})
    runs = {}
    for name, params in (("pool", {"n_extra": 2}), ("llm", {"n_extra": 2, "extra_scope": "llm",
                                                             "extra_when_idle": False})):
        runs[name] = simulate(inst, make_policy({"policy": {"id": "BL3", "params": params}}, inst), model,
                              EngineConfig(check_invariants=True), lender_seed=3, policy_seed=3)
        assert not runs[name].invariant_failures
    rep = runs["llm"].metrics["policy"]
    assert rep["extras"]["scope"] == "llm" and rep["extras"]["when_idle"] is False
    assert "extras" not in runs["pool"].metrics["policy"]
    gh = {k: sum(L.gpus * (L.end_min - L.start_min) for L in r.leases) for k, r in runs.items()}
    assert gh["llm"] < gh["pool"]


# ---------------------------------------------------------------- A9-P
def test_a9p_protected_only():
    for name in ("toy", "rand1"):
        inst = build_instance(_cfg(name))
        view = public_view(inst, "I1")
        tot = {}
        for lname, lm in (("trace", {}), ("iid", IID), ("eager", EAGER)):
            model = LenderModel(**{"schedule": "trace", "information": "I1", **lm})
            res = simulate(inst, make_policy({"policy": {"id": "A9P", "params": {}}}, inst), model,
                           EngineConfig(check_invariants=True), lender_seed=3, policy_seed=0)
            assert not res.invariant_failures and res.leases
            assert all(treated_as_protected(view, L.contract) for L in res.leases)
            assert all(L.announce_slot is None for L in res.leases)
            tot[lname] = res.components["total"]
            rep = res.metrics["policy"]
            assert rep["a9p"]["protected_only"] is True and rep["a9"]["insured"] == inst.n
        assert len(set(tot.values())) == 1, tot                       # lender-invariant
        model = LenderModel(schedule="iid_step", params={"D_slots": 1, "p": 0.3})
        a = simulate(inst, make_policy({"policy": {"id": "A9", "params": {}}}, inst), model,
                     EngineConfig(check_invariants=True), lender_seed=3, policy_seed=0)
        b = simulate(inst, make_policy({"policy": {"id": "A9P", "params": {"protected_only": False}}}, inst), model,
                     EngineConfig(check_invariants=True), lender_seed=3, policy_seed=0)
        assert a.components == b.components
        assert [(L.site, L.contract, L.start_slot, L.end_min) for L in a.leases] == \
            [(L.site, L.contract, L.start_slot, L.end_min) for L in b.leases]


# ---------------------------------------------------------------- MPC
def test_nearest_counts():
    assert list(nearest_counts([0.49, 0.5, 1.4999999999, 2.6, -0.2, 3.7], [0, 0, 0, 1, 0, 0],
                               [np.inf, np.inf, np.inf, 2, np.inf, 3])) == [0, 1, 1, 2, 0, 3]


def test_mpc_plan_class_and_lp():
    inst = build_instance(_cfg("rand1"))
    for params, lm in (({}, {}), ({"forecast": "ewma", "replan_slots": 3}, IID), ({"rounding": "random"}, EAGER),
                       ({"forecast": "previous_day", "window_min": 30}, {}), ({"holding": "window"}, {}),
                       ({"holding": "window", "replan_slots": 3, "rounding": "random"}, EAGER),
                       ({"replan_slots": 4, "contract_rule": "c2"}, EAGER), ({"routing": "arc"}, IID)):
        acts = []
        pol = make_policy({"policy": {"id": "MPC", "params": params}}, inst)
        o_act = pol.act

        def act(obs, o_act=o_act):
            out = o_act(obs)
            acts.extend(out)
            return out
        pol.act = act
        model = LenderModel(**{"schedule": "trace", "information": "I1", **lm})
        res = simulate(inst, pol, model, EngineConfig(check_invariants=True), lender_seed=3, policy_seed=3)
        assert not res.invariant_failures, params
        assert {type(a).__name__ for a in acts} <= {"Buy", "Release"} and any(isinstance(a, Buy) for a in acts)
        assert all(a.n_replicas == 1 for a in acts if isinstance(a, Buy))
        rep = res.metrics["policy"]
        R = int(params.get("replan_slots", 1))
        assert rep["solves"] == -(-inst.grid.T_slow // R) and rep["lp_status"] == {"0": rep["solves"]}
        L = pol._lp[pol.nW]
        Nn, Na = len(pol.triples_new), len(pol.routes)
        assert rep["routing"] == pol.routing and rep["n_routes"] == Na <= rep["n_arcs"]
        if params.get("holding") == "window":
            assert L["kind"] == "window" and L["nv"] == (pol.nW + 1) * Nn + Na * pol.nW
        else:
            assert L["kind"] == "stage" and L["nv"] == 3 * pol.nW * Nn + Na * pol.nW
        assert rep["info_class"] == "online-I1" and rep["forecast"] == params.get("forecast", "persistence")
        assert rep["holding"] == params.get("holding", "stage")
        # a noticed lease is never released by MPC (it serves until its death)
        assert not [x for x in res.leases if x.announce_slot is not None and x.end_cause == "release"]
        if lm is EAGER and R == 1:             # a lease noticed at s + 5 min dies at s + 10 min, so only a solve
            assert rep["noticed_counted"] > 0  # every slot sees it noticed
        json.dumps(rep, allow_nan=False)


def test_mpc_stage_plans_releases():
    """With holding 'stage' the LP buys for a peak and plans its release inside the window (its active count rises
    and falls); with 'window' it cannot (non-decreasing); a replica is never released inside its billed term."""
    inst = build_instance(_cfg("rand1"))
    fd = inst.clients.demand.reshape(inst.n, inst.grid.T_slow, inst.grid.phi).mean(axis=2)
    prof = {}
    for holding in ("stage", "window"):
        pol = make_policy({"policy": {"id": "MPC", "params": {"forecast": "oracle", "holding": holding}}}, inst)
        o_plan, seen = pol.plan, []

        def plan(obs, mean, o_plan=o_plan, seen=seen):
            out = o_plan(obs, mean)
            seen.append(out["lp_active"])
            return out
        pol.plan = plan
        res = simulate(inst, pol, LenderModel(schedule="trace"), EngineConfig(check_invariants=True), lender_seed=3,
                       policy_seed=3)
        assert not res.invariant_failures and np.array_equal(pol._inputs["future_demand"], fd)
        prof[holding] = seen
    assert all(all(b >= a - 1e-7 for a, b in zip(x, x[1:])) for x in prof["window"])
    assert any(max(x) > x[-1] + 0.5 for x in prof["stage"]), "no solve planned a release inside its window"
    # replanning every 3 slots executes the later stages' purchases of the last plan
    pol = make_policy({"policy": {"id": "MPC", "params": {"forecast": "oracle", "replan_slots": 3}}}, inst)
    res = simulate(inst, pol, LenderModel(schedule="trace"), EngineConfig(check_invariants=True), lender_seed=3,
                   policy_seed=3)
    assert not res.invariant_failures and res.metrics["policy"]["new_later"] > 0
    # billed term: under 'stage' no replica is released before its billed term
    pol = make_policy({"policy": {"id": "MPC", "params": {"contract_rule": "c2"}}}, build_instance(c2_toy()))
    res = simulate(build_instance(c2_toy()), pol, LenderModel(schedule="trace"), EngineConfig(check_invariants=True),
                   lender_seed=2, policy_seed=0)
    assert not res.invariant_failures
    assert all(L.end_min >= L.prepaid_end_min for L in res.leases if L.end_cause == "release")
    assert set(pol.m_P) <= {1, 2, 3} and all(pol.m_P >= 1)


def test_mpc_forecasts():
    inst = build_instance(_cfg("rand1"))
    view = public_view(inst, "I1")
    n = inst.n
    rng = np.random.default_rng(0)
    seq = [rng.uniform(0, 2, (n, 1)) for _ in range(300)]
    for f in ("persistence", "ewma", "previous_day"):
        pol = RecedingLP(forecast=f, window_min=30, ewma_alpha=0.25)
        pol.reset(view, np.random.default_rng(1))
        e = None
        for t, d in enumerate(seq):
            mean = pol._observe_demand(types.SimpleNamespace(t=t, demand=d))
            e = d[:, 0].copy() if e is None else 0.25 * d[:, 0] + 0.75 * e
        dh = pol.forecast(299, 6, mean)
        if f == "persistence":
            assert np.array_equal(dh, np.repeat(seq[-1], 6, axis=1))
        elif f == "ewma":
            assert np.allclose(dh, np.repeat(e[:, None], 6, axis=1), rtol=0, atol=1e-12)
        else:
            assert np.array_equal(dh, np.concatenate([seq[299 + i - 288] for i in range(6)], axis=1))
    fd = rng.uniform(0, 1, (n, inst.grid.T_slow))
    pol = RecedingLP(forecast="oracle", future_demand=fd)
    pol.reset(view, np.random.default_rng(1))
    assert np.array_equal(pol.forecast(3, 5, None), fd[:, 3:8])
    assert registry.needed_inputs("MPC", {"forecast": "oracle"}) == ("future_demand",)
    assert registry.needed_inputs("MPC", {}) == ()
    assert registry.info_class("MPC", {"forecast": "oracle", "window_min": 120}) == "lookahead-120min"
    assert registry.info_class("MPC", {}) == "online-I1"
    p = make_policy({"policy": {"id": "MPC", "params": {"forecast": "oracle"}}}, inst)
    assert np.array_equal(p._inputs["future_demand"], inst.clients.demand.reshape(n, inst.grid.T_slow,
                                                                                  inst.grid.phi).mean(axis=2))


# ---------------------------------------------------------------- lender groups 'region'
def region_toy() -> dict:
    cfg = toy_config()
    cfg["regions"]["list"] = ["r0", "r1"]
    L2 = copy.deepcopy(cfg["lenders"][1])
    L2.update(id="L2", region="r1", group="g2", R=[])
    cfg["lenders"][0]["R"] = [6, 7, 8]
    cfg["lenders"][1]["R"] = []
    cfg["lenders"].insert(2, L2)
    return cfg


def test_correlated_groups_region():
    from sublet.lender import build_R, resolve_params
    inst = build_instance(region_toy())
    idx = {s.lender: i for i, s in enumerate(inst.sites)}
    R = {}
    for g in ("region", "all", "none"):
        model = LenderModel(schedule="correlated", params={"p_sh": 1.0, "groups": g, "delay_slots_max": 0})
        assert resolve_params(inst, model)["groups"] == g
        R[g] = build_R(inst, model, np.random.default_rng(0))
    assert set(R["region"][idx["L1"]]) == {6, 7, 8} and len(R["region"][idx["L2"]]) == 0
    assert set(R["all"][idx["L2"]]) == {6, 7, 8} and set(R["all"][idx["L1"]]) == {6, 7, 8}
    assert len(R["none"][idx["L1"]]) == 0
    with pytest.raises(Exception, match="region"):
        resolve_params(inst, LenderModel(schedule="correlated", params={"p_sh": 1.0, "groups": "zone"}))
    spec = drun.load_run_spec({"schema_version": 1, "name": "reg", "instance": region_toy(),
                               "lender_model": {"schedule": "correlated", "params": {"p_sh": 0.5, "groups": "region"}},
                               "policy": {"id": "BL1", "params": {}}})
    assert drun._lender_model(spec, inst).params["groups"] == "region"
    from sublet import config as C
    assert C._lender_model({"schedule": "correlated", "params": {"p_sh": 0.5, "groups": "region"}})["params"][
        "groups"] == "region"
    with pytest.raises(drun.ConfigError):
        C._lender_model({"schedule": "correlated", "params": {"p_sh": 0.5, "groups": "zone"}})


# ---------------------------------------------------------------- registry, COPY_PARTS
@pytest.mark.parametrize("pid, params", [("A9P", {}), ("MPC", {}), ("MPC", {"forecast": "oracle", "replan_slots": 3}),
                                         ("BL2", {"contract_rule": "c2"}), ("BL3", SPARES_LLM_PARAMS),
                                         ("BL4", {"contract_rule": "c2"})])
def test_ms7_plan_class_p1(pid, params):
    """§2.3 (as tests/test_policy_isolation.py's test_plan_class_p1, which covers POLICY_IDS only): the MS7 ids and the
    C54 options run in plan class P1 on ms2_multi_small.json through make_policy, with the invariant checks on."""
    from fixtures import policy_actions_recorder
    spec = drun.load_run_spec({"schema_version": 1, "name": f"p1_{pid}", "instance": "ms2_multi_small.json",
                               "overrides": {"time.horizon_min": 720}, "lender_model": {"information": "I1"},
                               "policy": {"id": pid, "params": params}})
    inst, model, ecfg = drun.build(spec, spec["seeds"]["config"][0])
    recs = []

    def factory(sub):
        rec = policy_actions_recorder(make_policy(spec, sub))
        recs.append(rec)
        return rec
    if registry.entry(pid).runner == "siloed":
        d = run_siloed(inst, factory, model, ecfg, policy_seed=0)
        runs = list(zip(d["results"], recs))
    else:
        rec = factory(inst)
        runs = [(simulate(inst, rec, model, ecfg, policy_seed=0), rec)]
    kinds = set()
    for res, rec in runs:
        assert res.invariant_failures == [] and res.metrics["gpu_only_lease_slots"] == 0, (pid, params)
        kinds |= {type(a).__name__ for _, a in rec.actions}
        assert all(a.n_replicas == 1 for _, a in rec.actions if isinstance(a, Buy))
    assert "Buy" in kinds and kinds <= {"Buy", "Release", "Drain", "SetAdmission"}, (pid, kinds)


def test_registry_ms7():
    assert registry.MS7_IDS == ("A9P", "MPC")
    assert not set(registry.MS7_IDS) & (set(registry.POLICY_IDS) | set(registry.MS5B_IDS))
    assert registry.resolve("A9P") is ProtectedOnly and registry.resolve("MPC") is RecedingLP
    assert set(registry.param_names("MPC")) == set(RecedingLP.PARAMS)
    assert registry.entry("A9P").runner == registry.entry("MPC").runner == "simulate"
    assert "MPC" in drun.BASELINE_IDS
    assert mc.COPY_PARTS["e7r"] == e7r.PARTS == ("tune", "confirm", "eval")


# ---------------------------------------------------------------- ms7_baselines
def test_modes_and_w0plus():
    assert m7.NEW_MODES == ("L-iid-0.0005", "L-iid-0.002", "L-iid-0.0124", "L-co-reg-0.5", "L-co-reg-1", "L-pk")
    assert m7.EVAL_MODES == m5.conf_modes() + m7.NEW_MODES and m7.TUNE_MODES == m5.main_modes()
    assert m7.W0PLUS_MODES == m5.stress_modes() + m7.NEW_MODES and set(m7.MODE_NOTES) == set(m7.NEW_MODES)
    for p, mode in zip(m7.IID_LOW, m7.IID_LOW_MODES):
        assert m7.mode_lender_model(mode) == {"schedule": "iid_step", "params": {"D_slots": 1, "p": p}}
    assert m7.mode_lender_model("L-co-reg-0.5") == {"schedule": "correlated", "params": {"p_sh": 0.5,
                                                                                       "groups": "region"}}
    assert m7.mode_lender_model("L-pk") == {} and m7.instance_key("L-pk") == "pk"
    assert m7.instance_key("L-co-reg-1") == "base" and m7.instance_key("L-b999") == "b999"
    for mode in ("L-co-reg-2", "L-co-reg-0", "L-co-reg-x", "L-zz"):
        with pytest.raises(ValueError):
            m7.mode_lender_model(mode)
    spec = m7.week_spec("BL1", {}, mode="L-co-reg-1", c=113, horizon_min=120)
    assert spec["lender_model"] == {"schedule": "correlated", "params": {"p_sh": 1.0, "groups": "region"}}
    assert spec["seeds"]["config"] == [113]
    assert m7.week_spec("BL1", {}, mode="L-eg", c=113, horizon_min=120) == \
        m5.week_spec("BL1", {}, mode="L-eg", c=113, horizon_min=120, name="e7r")
    # SpotLake's conversion (derived): 1 - (1 - f)^(1/288), rounded down to the grid's values
    for f, p in ((0.1471, 0.0005), (0.4561, 0.002)):
        assert p <= 1 - (1 - f) ** (1 / 288) < 1.12 * p
    r = {m: 0.5 for m in m7.W0PLUS_MODES}
    r["L-pk"] = 0.9
    assert m7.w0plus_of(r) == (0.9, "L-pk", [])
    assert m7.w0plus_of({**r, "L-co-reg-1": None})[0] is None


def test_tags_and_grids():
    assert not set(m7.MS7_TAGS) & set(m5.TAGS)
    assert not set(m7.grid_tags()) & (set(m5.TAGS) | set(m7.MS7_TAGS))
    assert set(m7.EXISTING_EVAL_TAGS) <= set(m5.TAGS) and set(m7.EVAL_FIXED) <= set(m7.MS7_TAGS)
    for pid, knobs in m7.KNOB_DEFAULTS.items():
        P = registry.resolve(pid).PARAMS
        assert {k: P[k] for k in knobs} == knobs, pid
    for fam in m7.FAMILIES:
        g = m7.grid(fam)
        assert 1 <= len(g) <= m7.MAX_GRID and list(g)[0] == f"{fam}-g00"
        assert g[f"{fam}-g00"] == m7.family_default(fam), fam
        assert len({json.dumps(v, sort_keys=True) for v in g.values()}) == len(g), fam      # no duplicate
        for pid, p in g.values():
            assert p == m7.minimal(pid, p)
            registry.resolve(pid)(**p)                                                   # valid parameters
    assert sum(len(m7.grid(f)) for f in m7.FAMILIES) == 68
    assert m7.BL1_C2 == {"target": "ceil", "release": "now", "site_rule": "static", "mbb": False, "commit": False,
                         "insure": False}
    # tags at their defaults equal the confirmation's settings
    assert m7.family_default("BL3") == ("BL3", {"n_extra": 0}) and m7.family_default("BL5") == \
        ("BL5", {"use_current_slot": True})
    sel = {"tuned": {"BL3-T": {"family": "BL3", "rule": "T", "config": "BL3-g05", "policy_id": "BL3",
                               "params": {"n_extra": 0, "zone": "group"}}}}
    t = m7.tag("BL3-T", sel)
    assert (t.id, t.params, t.family, t.kind) == ("BL3", {"n_extra": 0, "zone": "group"}, "BL3", "tuned")
    with pytest.raises(KeyError):
        m7.tag("BL3-T")
    assert m7.tag("Sublet").family == "ms5b" and m7.tag("Sublet").params == "Sublet"
    tab = m7.tag_table(["BL1-c2", "BL1", "BL3-g10"])
    assert tab["BL1-c2"]["policy_id"] == "A9" and tab["BL1"]["family"] == "ms5b" and tab["BL3-g10"]["kind"] == "grid"
    assert m7.MS7_TAGS["MPC-oracle"].information == "lookahead-60min"


def _fake_inst(T=576, slow=5):
    """A stand-in for an Instance with the fields peak_aligned_config reads: two regions, three trace lenders."""
    day = 288
    ph = np.arange(T) % day
    d0 = np.where(ph == 100, 5.0, 1.0)                 # region a peaks at phase 100
    d1 = np.where(ph == 250, 4.0, 1.0)                 # region b at phase 250
    demand = np.stack([d0, d1, np.zeros(T)])[:, :, None]
    N = 5 * day
    s = np.arange(N) % day
    s4 = np.arange(1000) % day                        # a series whose length is not a multiple of a day
    S = {"A": 10.0 + (s != 30) * 5.0, "B": 10.0 + (s != 200) * 5.0, "C": 10.0 + (s != 7) * 5.0,
         "D": 10.0 + (s4 != 50) * 5.0}
    cfg = {"lenders": [{"id": "A", "kind": "trace", "region": "a", "offset": 3 * day + 17},
                       {"id": "B", "kind": "trace", "region": "b", "offset": 1000},
                       {"id": "C", "kind": "trace", "region": "c", "offset": 5},
                       {"id": "D", "kind": "trace", "region": "a", "offset": 900},
                       {"id": "P", "kind": "protected", "region": "a", "offset": 0}]}
    return types.SimpleNamespace(
        config=cfg, grid=types.SimpleNamespace(T_slow=T, slow_min=slow, phi=1), n=3,
        clients=types.SimpleNamespace(demand=demand.reshape(3, T), region=("a", "b", "c")),
        lenders=[types.SimpleNamespace(lender=k, S_full=v) for k, v in S.items()],
        sites=[types.SimpleNamespace(lender=k) for k in ("A", "B", "C", "D", "P")])


def test_peak_aligned_offsets():
    inst = _fake_inst()
    cfg, rec = m7.peak_aligned_config(inst)
    off = {e["id"]: e["offset"] for e in cfg["lenders"]}
    assert rec["region_peaks"]["a"]["phase"] == 100 and rec["region_peaks"]["b"]["phase"] == 250
    assert "c" not in rec["region_peaks"]                     # no borrower demand
    assert (off["A"] + 100) % 288 == 30 and off["A"] // 288 == 3     # minimum on the peak, base day kept
    assert (off["B"] + 250) % 288 == 200 and off["B"] // 288 == 1000 // 288
    assert off["C"] == 5 and off["P"] == 0 and rec["n_moved"] == 3
    # D (N = 1000): 288 * 3 + (50 - 100) mod 288 = 1102 would run past the series end, which shifts the phase when N is
    # not a multiple of a day; three days back the 576 steps of the horizon fit
    row = next(r for r in rec["lenders"] if r["lender"] == "D")
    assert off["D"] == 238 and row["days_back"] == 3 and (off["D"] + 100) % 288 == 50 and off["D"] + 576 <= 1000
    assert all(r["days_back"] == 0 for r in rec["lenders"] if r["moved"] and r["lender"] != "D")
    assert inst.config["lenders"][0]["offset"] == 3 * 288 + 17      # the input config is not changed


def test_registration_gate():
    files = {n: {"recorded": "a" * 64, "head": "a" * 64, "disk": "a" * 64} for n in m7.REGISTERED}
    good = {"registration_at_head": True, "dirty_paths": [], "files": files}
    assert m7.check_registration(good)[0]
    for change in ({"registration_at_head": False}, {"dirty_paths": [" M x"]}, {"dirty_paths": None},
                   {"files": {**files, "e7r_select.py": {"recorded": "a" * 64, "head": "a" * 64, "disk": "b" * 64}}},
                   {"files": {**files, "e7r_analysis.py": {"recorded": None, "head": "a" * 64, "disk": "a" * 64}}}):
        ok, why, _ = m7.check_registration({**good, **change})
        assert not ok and why.startswith("e7r does not start")
    rec = m7.registration_record()
    assert set(rec["files"]) == set(m7.REGISTERED)
    for name, f in rec["files"].items():
        assert f["disk"] == hashlib.sha256((m7.HERE / name).read_bytes()).hexdigest()


# ---------------------------------------------------------------- e7r: job lists and gate
def _selection(fams=m7.FAMILIES, alias=("BL4",), reduced=False) -> dict:
    tuned, aliases = {}, {}
    for fam in fams:
        g = m7.grid(fam)
        for rule, name in (("T", f"{fam}-g01"), ("W", f"{fam}-g01" if fam in alias else f"{fam}-g02")):
            pid, p = g[name]
            tuned[f"{fam}-{rule}"] = {"family": fam, "rule": rule, "config": name, "policy_id": pid, "params": p}
        if fam in alias:
            aliases[f"{fam}-W"] = f"{fam}-T"
    return {"meta": {"reduced": reduced}, "tuned": tuned, "aliases": aliases}


def test_e7r_jobs(monkeypatch):
    monkeypatch.delenv(e7r.REDUCED_ENV, raising=False)
    js = e7r.jobs(["tune"])
    mc.check_jobs(js)
    assert len(js) == 68 * 4 and {j.params["c"] for j in js} == set(m7.TUNE_WEEKS)
    assert all(j.params["modes"] == list(m7.TUNE_MODES) and j.params["horizon_min"] == m5.WEEK_MIN
               and j.params["policy_seeds"] == [0] for j in js)
    with pytest.raises(RuntimeError, match="selection"):
        monkeypatch.setenv("MS3_ROOT", str(Path("/nonexistent")))
        e7r.jobs(["eval"])
    sel = _selection()
    conf = e7r.jobs(["confirm"], sel)
    names = {j.params["tag"] for j in conf}
    assert names == {m7.FAMILY_DEFAULT[f] for f in m7.FAMILIES} | (set(sel["tuned"]) - set(sel["aliases"]))
    assert {j.params["c"] for j in conf} == set(m7.CONFIRM_WEEKS)
    ev = e7r.jobs(["eval"], sel)
    mc.check_jobs(ev)
    by = {}
    for j in ev:
        by.setdefault(j.params["tag"], set()).add(tuple(j.params["modes"]))
        assert j.params["c"] in m7.EVAL_WEEKS
    assert {t for t, m in by.items() if m == {m7.EVAL_MODES}} == set(m7.EVAL_FIXED) | (set(sel["tuned"])
                                                                                     - set(sel["aliases"]))
    assert by["MPC-oracle"] == {m7.REFERENCE_MODES} == {("L-tr", "L-hon")}
    assert {t for t, m in by.items() if m == {m7.EXISTING_MODES}} == set(m7.EXISTING_EVAL_TAGS)
    assert m7.EXISTING_MODES == ("L-tr",) + m7.NEW_MODES          # L-tr: the identity check against main
    assert "BL4-W" not in by and len(ev) == 16 * len(by)
    j = next(j for j in ev if j.params["tag"] == "Sublet")
    assert j.params["params"] is None and j.params["policy_id"] == "A8P"
    j = next(j for j in ev if j.params["tag"] == "BL3-T")
    assert j.params["params"] == sel["tuned"]["BL3-T"]["params"] and j.params["family"] == "BL3"


def test_e7r_reduced_and_selection_kind(monkeypatch, tmp_path):
    monkeypatch.setenv(e7r.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_ROOT", str(tmp_path))
    js = e7r.jobs(["tune"])
    assert {j.params["c"] for j in js} == {m7.REDUCED_WEEK} and {j.params["horizon_min"] for j in js} == {120}
    assert not {j.params["c"] for j in js} & (set(m7.TUNE_WEEKS) | set(m7.CONFIRM_WEEKS) | set(m7.EVAL_WEEKS))
    p = e7r.selection_path()
    p.parent.mkdir(parents=True)
    mc.dump_json(_selection(reduced=False), p)
    with pytest.raises(RuntimeError, match="full run"):
        e7r.jobs(["eval"])
    mc.dump_json(_selection(reduced=True), p)
    ev = e7r.jobs(["eval"])
    assert {j.params["c"] for j in ev} == {m7.REDUCED_WEEK}
    # the reduced cell has no runs in the confirmation's main part: its tags run under every mode there
    assert all(j.params["modes"] == list(m7.EVAL_MODES) for j in ev if j.params["tag"] in m7.EXISTING_EVAL_TAGS)
    monkeypatch.setattr(e7r, "_GATE", {})
    ok, line = e7r.check_start("eval")
    assert ok and e7r.gate("eval")["enforced"] is False, line


def test_e7r_gate_enforced(monkeypatch):
    monkeypatch.delenv(e7r.REDUCED_ENV, raising=False)
    monkeypatch.setattr(e7r, "_GATE", {})
    monkeypatch.setattr(m7, "check_registration", lambda rec=None: (False, "e7r does not start: test", {}))
    with pytest.raises(RuntimeError, match="does not start"):
        e7r.gate("tune")
    assert not e7r.check_start("tune")[0]
    monkeypatch.setattr(e7r, "_GATE", {})
    monkeypatch.setenv(e7r.REDUCED_ENV, "1")
    g = e7r.gate("tune")
    assert g["ok"] is False and g["enforced"] is False


def test_e7r_selection_check(monkeypatch, tmp_path):
    """A full run's confirm and eval read only a selection of the registered e7r_select.py on a tune summary of HEAD."""
    rec = {"head": "c" * 40, "files": {"e7r_select.py": {"recorded": "a" * 64}}}
    good = {"meta": {"reduced": False, "script_sha256": "a" * 64, "summary_git_revision": "c" * 40}}
    assert e7r.selection_check(good, rec)[0]
    for meta in ({"script_sha256": "b" * 64}, {"summary_git_revision": "d" * 40}, {"script_sha256": None}):
        ok, why = e7r.selection_check({"meta": {**good["meta"], **meta}}, rec)
        assert not ok and "selection.json" in why
    assert not e7r.selection_check(good, {**rec, "files": {}})[0]
    assert not e7r.selection_check(good, {**rec, "head": None})[0]
    monkeypatch.delenv(e7r.REDUCED_ENV, raising=False)
    monkeypatch.setenv("MS3_ROOT", str(tmp_path))
    monkeypatch.setattr(e7r, "_GATE", {"rec": rec})
    p = e7r.selection_path()
    p.parent.mkdir(parents=True)
    mc.dump_json({**_selection(), "meta": {**good["meta"], "summary_git_revision": "d" * 40}}, p)
    with pytest.raises(RuntimeError, match="tune summary"):
        e7r.need_selection()
    mc.dump_json({**_selection(), "meta": good["meta"]}, p)
    assert e7r.need_selection()["meta"] == good["meta"]


# ---------------------------------------------------------------- e7r_select and e7r_analysis
def _tune_summary(vals: dict, weeks=(113, 114, 115, 116)) -> dict:
    """vals: {tag: (r0_tr per week, W0-mode r0 per week)}; the five stress modes get the W0 value at L-eg and less."""
    table, tags = {}, {}
    for t, (tr, w0) in vals.items():
        fam = t.split("-g")[0]
        tags[t] = {"policy_id": fam, "params": {"i": t}, "family": fam}
        table[t] = {"L-tr": {str(w): {"0": v} for w, v in zip(weeks, tr)}}
        for m in es.STRESS_MODES:
            table[t][m] = {str(w): {"0": (v if m == "L-eg" or v is None else v - 0.1)} for w, v in zip(weeks, w0)}
    return {"meta": {"reduced": False, "tags": tags}, "table": table}


def test_select_rules():
    s = _tune_summary({"BL4-g00": ([0.6, 0.6, 0.6, 0.6], [1.0, 1.0, 1.0, 1.0]),
                       "BL4-g01": ([0.5, 0.7, 0.5, 0.9], [0.9, 0.9, 0.9, 0.9]),     # med_T 0.6 (tie), med_W 0.9
                       "BL4-g02": ([0.4, 0.4, 0.4, None], [0.5, 0.5, 0.5, 0.5]),    # missing run: ineligible
                       "BL5-g00": ([0.6, 0.6, 0.6, 0.6], [0.8, 0.8, 0.8, 0.8]),
                       "BL5-g01": ([0.7, 0.7, 0.7, 0.7], [0.8, 0.8, 0.8, 0.8])})
    sel = es.select(s)
    f = sel["families"]["BL4"]
    assert f["T"] == "BL4-g00" and f["W"] == "BL4-g01" and f["n_eligible"] == 2
    assert f["configs"]["BL4-g02"]["eligible"] is False and f["configs"]["BL4-g02"]["missing"] == [["116", "L-tr"]]
    assert f["configs"]["BL4-g01"]["median_r0_tr"] == 0.6 and f["configs"]["BL4-g01"]["median_W0"] == 0.9
    g = sel["families"]["BL5"]
    assert g["T"] == g["W"] == "BL5-g00" and sel["aliases"] == {"BL5-W": "BL5-T"}      # W ties broken by med_T
    assert sel["tuned"]["BL4-W"]["params"] == {"i": "BL4-g01"} and sel["families"]["BL1"]["T"] is None
    assert es.FAMILIES == m7.FAMILIES and es.STRESS_MODES == m7.W0_MODES and es.WEEKS == m7.TUNE_WEEKS
    assert es.REDUCED_WEEKS == (m7.REDUCED_WEEK,)


def _summ(table: dict, tags: dict, weeks) -> dict:
    return {"meta": {"weeks": list(weeks), "tags": tags, "reduced": False}, "table": table}


def test_analysis_tables_and_margins():
    weeks = (301, 302)

    def rows(level, modes, wk=weeks, bump=None):
        return {m: {str(w): {"0": level + (bump or {}).get((m, w), 0.0)} for w in wk} for m in modes}
    # the confirmation's tags run under the new modes and L-tr: BL1's L-tr equals main's, Sublet's does not (main's
    # runs take precedence in the table, the identity check reports the pair)
    ev_tab = {"Sublet": {**rows(0.6, ea.NEW_MODES), **rows(0.56, ("L-tr",))},
              "BL1-c2": rows(0.7, ea.CONF_MODES + ea.NEW_MODES),
              "BL4-T": rows(0.65, ea.CONF_MODES + ea.NEW_MODES,
                            bump={("L-tr", 302): -0.2, ("L-iid-0.002", 301): 0.45}),
              "A9-P": rows(1.0, ea.CONF_MODES + ea.NEW_MODES),
              "BL1": {**rows(0.9, ea.NEW_MODES), **rows(0.8, ("L-tr",))}}
    ev_tags = {"BL1-c2": {"policy_id": "A9", "params": dict(m7.BL1_C2), "family": "BL1"},
               "BL4-T": {"policy_id": "BL4", "params": {"window_min": 30}, "family": "BL4"},
               "A9-P": {"policy_id": "A9P", "params": {}, "family": "A9P"},
               "Sublet": {"policy_id": "A8P", "params": "rule", "family": "ms5b"},
               "BL1": {"policy_id": "BL1", "params": {}, "family": "ms5b"}}
    main_tab = {"Sublet": rows(0.55, ea.CONF_MODES, bump={("L-eg", 301): 0.3}), "BL1": rows(0.8, ea.CONF_MODES),
                "BL4x": rows(0.65, ea.CONF_MODES, bump={("L-tr", 302): -0.2})}
    main_tags = {"Sublet": {"policy_id": "A8P", "params": "rule"}, "BL1": {"policy_id": "BL1", "params": {}},
                 "BL4x": {"policy_id": "BL4", "params": {"window_min": 30}}}
    second = {"table": {"BL1": {"L-ad": {"301": {"0": 0.8}}}}}
    sel = {"tuned": {"BL4-T": {"config": "BL4-g02"}, "BL4-W": {"config": "BL4-g02"}}, "aliases": {"BL4-W": "BL4-T"}}
    inp = {"eval": _summ(ev_tab, ev_tags, weeks), "main": _summ(main_tab, main_tags, weeks), "second": second,
           "selection": sel, "confirm": None, "sha256": {}, "paths": {"eval": "x"}}
    a = ea.analysis(inp)
    s = a["tags"]["Sublet"]
    assert s["r0_tr"]["median"] == 0.55 and s["per_week"]["301"]["W0"] == pytest.approx(0.85)
    assert s["per_week"]["302"]["W0"] == 0.55 and s["per_week"]["302"]["W0plus"] == 0.6      # W0+ adds the new modes
    assert s["per_week"]["301"]["W0plus"] == pytest.approx(0.85) and s["RC"]["L-eg"]["max"] == pytest.approx(0.3)
    assert s["RC"]["L-pk"]["median"] == pytest.approx(0.05)
    assert s["sources"] == ["eval", "confirmation main (seven modes, before eval's)"]
    assert a["tags"]["BL4-W"]["sources"] == ["eval (alias of BL4-T)"]
    # margins in the confirmation's convention: the baseline minus Sublet, positive when Sublet costs less
    mg = a["margins"]["BL1"]["r0_tr"]
    assert mg["n"] == 2 and mg["wins"] == 2 and mg["median"] == pytest.approx(0.25)
    mg = a["margins"]["BL4-T"]["r0_tr"]
    assert (mg["wins"], mg["ties"], mg["losses"], mg["missing"], mg["losses_with_missing"]) == (1, 0, 1, 0, 1)
    assert a["margins"]["BL1-c2"]["W0plus"]["per_week"]["301"] == pytest.approx(-0.15)
    pair = a["as_built_vs_c2"][0]
    assert pair["as_built"] == "BL1" and pair["margins_c2"]["r0_tr"]["n"] == 2
    assert pair["margins_as_built"]["r0_tr"]["median"] == pytest.approx(0.25)
    assert a["tuned"]["BL4"]["W"]["alias_of"] == "BL4-T" and a["tuned"]["BL4"]["W"]["margin_W0"]["n"] == 2
    assert a["tuned"]["BL4"]["T"]["margin_r0_tr"]["wins"] == 1
    ident = {(x["eval_tag"], x["main_tag"]): x for x in a["checks"]["identity_with_confirmation"]}
    assert ident[("BL4-T", "BL4x")]["identical"] and ident[("BL1", "BL1")]["identical"]
    assert ident[("BL1", "BL1")]["n_cells"] == 2                       # L-tr on both weeks
    assert ident[("Sublet", "Sublet")]["n_cells"] == 2 and not ident[("Sublet", "Sublet")]["identical"]
    assert ident[("Sublet", "Sublet")]["max_abs_diff"] == pytest.approx(0.01)
    ids = a["checks"]["identity_summary"]
    assert (ids["pairs_with_cells"], ids["identical"], ids["all_identical"]) == (3, 2, False)
    assert ids["not_identical"] == [["Sublet", "Sublet"]]
    assert a["tags"]["BL1"]["reproduces_main"] is True and a["tags"]["Sublet"]["reproduces_main"] is False
    assert "reproduces_main" not in a["tags"]["BL1-c2"]                  # eval's runs only
    # the i.i.d. intensity curve: p = 0 from main's L-hon, the low rates from eval, 0.05 and 0.2 from main
    it = s["intensity"]
    assert [m for _p, m in it["points"]] == [m for _p, m in ea.INTENSITY]
    assert it["per_week"]["301"]["points"][0] == [0.0, 0.55] and it["per_week"]["301"]["points"][1] == [0.0005, 0.6]
    assert it["per_week"]["301"]["first_p_above_1"] is None and it["by_p"]["L-iid-0.002"]["median"] == 0.6
    it = a["tags"]["BL4-T"]["intensity"]
    assert it["per_week"]["301"]["first_p_above_1"] == 0.002 and it["per_week"]["302"]["first_p_above_1"] is None
    pv = a["checks"]["provenance"]
    assert pv["eval_selection_equal"] is False and pv["confirm_selection_equal"] is None and pv["one_commit"] is None
    assert a["checks"]["a9p_invariance"]["max_spread"] == 0.0
    ad = a["checks"]["adaptive_equivalence"]
    assert ad["n_pairs"] == 1 and ad["max_abs_diff"] == pytest.approx(0.0)
    assert a["margins"]["BL1"]["r0_by_mode"]["L-pk"]["median"] == pytest.approx(0.3)
    assert set(a["margins"]["BL1"]["r0_by_mode"]) == set(ea.CONF_MODES + ea.NEW_MODES)
    assert a["tags"]["BL1"]["r0"]["L-tr"]["median"] == 0.8 and a["tags"]["Sublet"]["r0"]["L-pk"]["n"] == 2
    # best of a set: members not run are listed and left out; aliases read as their targets
    b = a["best_of"]["as_built"]
    assert b["members"] == ["BL1"] and set(b["absent"]) == set(ea.H1_SET) - {"BL1"}
    assert b["margins"]["r0_tr"]["median"] == pytest.approx(0.25)
    assert a["best_of"]["tuned_W"]["members"] == ["BL4-T"] and "BL4-W" not in a["best_of"]["tuned_W"]["absent"]
    b = a["best_of"]["all_online"]
    assert set(b["members"]) == {"BL1", "BL1-c2", "BL4-T", "A9-P"}
    assert b["per_week"]["301"]["r0_tr"] == 0.65 and b["per_week"]["301"]["r0_tr_tag"] == "BL4-T"
    assert b["per_week"]["302"]["r0_tr"] == pytest.approx(0.45)
    mg = b["margins"]["r0_tr"]
    assert (mg["wins"], mg["losses"]) == (1, 1) and mg["min"] == pytest.approx(-0.1) and mg["max"] == pytest.approx(0.1)
    assert mg["per_week"]["301"] == pytest.approx(0.1)               # the best (BL4-T, 0.65) minus Sublet (0.55)
    md = ea.to_md(a)
    assert "margin over each baseline" in md and "best of each comparison set" in md and "intensity" in md
    # a missing value is a loss for Sublet (design/sublet_v2.md §4.5's missing-run rule)
    per_s = {"1": {"r0_tr": 0.5}, "2": {"r0_tr": 0.5}, "3": {"r0_tr": None}}
    per_b = {"1": {"r0_tr": 0.7}, "2": {"r0_tr": None}, "3": {"r0_tr": 0.4}}
    mg = ea.margin(per_s, per_b, "r0_tr", ["1", "2", "3"])
    assert (mg["n"], mg["wins"], mg["losses"], mg["missing"], mg["losses_with_missing"]) == (1, 1, 0, 2, 2)
    assert mg["per_week"] == {"1": pytest.approx(0.2), "2": None, "3": None}
    # provenance: the selection read here is the one eval and confirm recorded, all at one commit
    inp2 = copy.deepcopy(inp)
    for k in ("eval", "confirm"):
        inp2[k] = inp2[k] or _summ({}, {}, weeks)
        inp2[k]["meta"].update(selection={"sha256": "s" * 64}, git_revision="c" * 40)
    inp2["sha256"] = {"selection": "s" * 64}
    inp2["selection"] = {**sel, "meta": {"summary_git_revision": "c" * 40}}
    pv = ea.analysis(inp2)["checks"]["provenance"]
    assert pv["eval_selection_equal"] and pv["confirm_selection_equal"] and pv["one_commit"]
    inp2["confirm"]["meta"]["git_revision"] = "d" * 40
    assert ea.analysis(inp2)["checks"]["provenance"]["one_commit"] is False
    json.dumps(mc.jsonable(a), allow_nan=False)
    assert ea.H1_SET == m5.H1_SET and ea.H2B_SET == m5.H2B_SET and set(ea.SPARES_SET) <= set(m7.MS7_TAGS)
    assert ea.NEW_MODES == m7.NEW_MODES and ea.STRESS_MODES == m7.W0_MODES and ea.W0PLUS_MODES == m7.W0PLUS_MODES
    assert ea.AS_BUILT_C2 == m7.AS_BUILT_C2 and ea.FAMILY_DEFAULT == m7.FAMILY_DEFAULT
    assert ea.CONF_MODES == m7.CONF_MODES
    assert ea.ADAPTIVE_EQUIV == m7.ADAPTIVE_EQUIV


def test_analysis_main_precedence_per_cell():
    """main's cell first where main has it; a cell main lacks (the development week of a reduced run) is eval's."""
    ev = _summ({"BL1": {"L-tr": {"301": {"0": 0.8}, "302": {"0": 0.8}},
                        "L-eg": {"301": {"0": 0.9}, "302": {"0": 0.9}}}},
               {"BL1": {"policy_id": "BL1", "params": {}}}, (301, 302))
    main = _summ({"BL1": {"L-tr": {"301": {"0": 0.7}}}}, {"BL1": {"policy_id": "BL1", "params": {}}}, (301,))
    tab, src = ea.merged_table(ev, main, {})
    assert tab["BL1"]["L-tr"] == {"301": 0.7, "302": 0.8} and tab["BL1"]["L-eg"] == {"301": 0.9, "302": 0.9}
    assert src["BL1"][-1].startswith("confirmation main")
    tab, src = ea.merged_table(ev, _summ({"BL1": {}}, {}, ()), {})
    assert tab["BL1"]["L-tr"] == {"301": 0.8, "302": 0.8} and src["BL1"] == ["eval"]       # nothing of main's used
    a = ea.analysis({"eval": ev, "main": main, "second": None, "selection": None, "confirm": None, "sha256": {},
                     "paths": {"eval": "x"}})
    x = a["checks"]["identity_with_confirmation"][0]
    assert (x["n_cells"], x["identical"], x["max_abs_diff"]) == (1, False, pytest.approx(0.1))


def test_confirm_check():
    weeks = (121, 122)
    table = {}
    for t, tr, w in (("BL4", 0.6, 1.0), ("BL4-T", 0.55, 1.1), ("BL5-cur", 0.6, 0.9), ("BL5-T", 0.7, 0.8)):
        table[t] = {"L-tr": {str(x): {"0": tr} for x in weeks}}
        for m in ea.STRESS_MODES:
            table[t][m] = {str(x): {"0": w} for x in weeks}
    sel = {"aliases": {"BL4-W": "BL4-T", "BL5-W": "BL5-T"}}
    c = ea.confirm_check(_summ(table, {}, weeks), sel)
    assert c["families"]["BL4"]["T_holds"] is True and c["families"]["BL4"]["W_holds"] is False
    assert c["families"]["BL5"]["T_holds"] is False and c["families"]["BL5"]["W_holds"] is True
    assert c["families"]["MPC"]["T_holds"] is None


# ---------------------------------------------------------------- run_e7r.sh
def test_run_script_arguments():
    assert subprocess.run(["bash", "-n", str(RUN)]).returncode == 0
    r = subprocess.run(["bash", str(RUN)], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert r.returncode == 2 and "E7R_PART" in r.stderr
    r = subprocess.run(["bash", str(RUN)], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "E7R_PART": "main"})
    assert r.returncode == 2 and "unknown part" in r.stderr
    r = subprocess.run(["bash", str(RUN), "--full"], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "E7R_PART": "tune"})
    assert r.returncode == 2


# ---------------------------------------------------------------- the E7 week instance (needs the a12 outputs)
@pytest.fixture(scope="module")
def week():
    spec0 = m5.week_spec("BL0a", {}, mode="L-tr", c=101, horizon_min=120, name="c54")
    inst, model, ecfg = drun.build(spec0, 101)
    return inst, ecfg


@pytest.mark.needs_a12
def test_week_identity_and_c2(week):
    inst, ecfg = week
    view = public_view(inst, "I1")
    kb, ks = c2_base_contracts(view), k_star(view)
    J = len(view.llms)
    assert any(kb[l, j] >= 0 and kb[l, j] != ks[l] for l in range(len(view.sites)) for j in range(J))
    for mode in ("L-tr", "L-eg"):
        model = drun._lender_model(m5.week_spec("BL1", {}, mode=mode, c=101, horizon_min=120), inst)
        a = simulate(inst, make_policy({"policy": {"id": "BL1", "params": {}}}, inst), model, ecfg, lender_seed=101,
                     policy_seed=0)
        b = simulate(inst, make_policy({"policy": {"id": "A9", "params": dict(m7.BL1_AS_A9)}}, inst), model, ecfg,
                     lender_seed=101, policy_seed=0)
        assert a.components["total"] == b.components["total"] and len(a.leases) == len(b.leases)
        for name in ("BL3-0-c2", "BL4-c2", "BL1-c2"):
            t = m7.MS7_TAGS[name]
            res = simulate(inst, make_policy({"policy": {"id": t.id, "params": dict(t.params)}}, inst), model, ecfg,
                           lender_seed=101, policy_seed=0)
            assert not res.invariant_failures
            llm = {r.lease_id: r.llm for r in res.replicas}
            assert all(L.contract == kb[L.site, llm[L.id]] or treated_as_protected(view, L.contract)
                       for L in res.leases if L.id in llm), name


@pytest.mark.needs_a12
def test_week_mpc_region_routing(week):
    """On the E7 week instance delta_cl depends on the site only through its region, so MPC aggregates its routing per
    region (fewer routes than BL4's arcs); with 'arc' it keeps BL4's arcs; both buy only the contracts of their rule."""
    inst, ecfg = week
    view = public_view(inst, "I1")
    kb = c2_base_contracts(view)
    model = drun._lender_model(m5.week_spec("BL1", {}, mode="L-eg", c=101, horizon_min=120), inst)
    out = {}
    for routing in ("region", "arc"):
        pol = make_policy({"policy": {"id": "MPC", "params": {"routing": routing, "contract_rule": "c2"}}}, inst)
        res = simulate(inst, pol, model, ecfg, lender_seed=101, policy_seed=0)
        rep = res.metrics["policy"]
        assert not res.invariant_failures and rep["lp_status"] == {"0": rep["solves"]} and res.leases
        assert rep["routing"] == routing
        llm = {r.lease_id: r.llm for r in res.replicas}
        assert all(L.contract == kb[L.site, llm[L.id]] or treated_as_protected(view, L.contract)
                   for L in res.leases if L.id in llm)
        out[routing] = rep
    assert out["region"]["n_routes"] < out["arc"]["n_routes"] == out["arc"]["n_arcs"]
    assert out["region"]["lp_n_vars_max"] < out["arc"]["lp_n_vars_max"]


@pytest.mark.needs_a12
def test_week_peak_aligned(week):
    from sublet.lender import build_R
    inst, _ = week
    pk, rec = m7.peak_aligned_instance(inst)
    assert rec["n_moved"] > 0 and mc.instance_hash(pk) != mc.instance_hash(inst)
    assert [s.id for s in pk.sites] == [s.id for s in inst.sites]
    assert np.array_equal(pk.price, inst.price) and np.array_equal(pk.clients.demand, inst.clients.demand)
    assert rec["same_as_base"] == {"site_ids": True, "capacities": True, "prices": True, "references": True}
    for row in rec["lenders"]:
        if row["moved"]:
            N, base = row["series_len"], int(row["offset_base"]) % row["series_len"]
            shift = (row["slack_min_phase"] - row["region_peak_phase"]) % 288
            want = (288 * (base // 288 - row["days_back"]) + shift) % N
            assert row["offset"] == want, row
            assert row["days_back"] == 0 or N % 288
    model = LenderModel(schedule="trace")
    Ra, Rb = build_R(inst, model, np.random.default_rng(0)), build_R(pk, model, np.random.default_rng(0))
    assert any(not np.array_equal(a, b) for a, b in zip(Ra, Rb))
    cfg2, _ = m7.peak_aligned_config(inst)
    assert mc.instance_hash(build_instance(cfg2)) == mc.instance_hash(pk)          # deterministic


@pytest.mark.needs_a12
def test_week_job_through_runner(monkeypatch, tmp_path):
    monkeypatch.setenv(e7r.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_ROOT", str(tmp_path))
    monkeypatch.setattr(e7r, "_GATE", {})
    job = mc.Job(mc.job_id("e7r", "eval", k="week", tag="BL4-c2", c=101), "pool",
                 {"part": "eval", "kind": "week", "tag": "BL4-c2", "policy_id": "BL4",
                  "params": {"contract_rule": "c2"}, "family": "BL4", "c": 101,
                  "modes": ["L-tr", "L-pk", "L-co-reg-1"], "policy_seeds": [0], "horizon_min": 120})
    out = tmp_path / "out" / "e7r" / "eval"
    rec = mc.run_job("e7r", job, lambda outputs: e7r.run(job, outputs, out), out)
    assert rec["status"] == "ok", rec
    f = mc.read_json(e7r.run_path(out, job.id))
    assert {r["mode"] for r in f["runs"]} == {"L-tr", "L-pk", "L-co-reg-1"}
    assert all(r["status"] == "ok" and r["r0"] is not None for r in f["runs"])
    assert set(f["instances"]) == {"base", "pk"} and f["instances"]["pk"]["peak_aligned"]["n_moved"] > 0
    assert f["lender_models"]["L-co-reg-1"]["params"]["groups"] == "region"
    assert f["meta"]["gate"]["enforced"] is False
