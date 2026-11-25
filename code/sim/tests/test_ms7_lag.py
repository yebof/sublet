"""Tests of MS7 unit B1, the causal-demand rerun (design/ms7/plan.md X1, D6; change C53; design/ms7/feasibility/
causal.md): the demand options of the baselines, the E7c tags, the driver e7c.py and run_e7c.sh, the hooks of
e7h.run_week and the analysis e7c_analysis.py.

Quick (no raw data):
- frozen behaviour: BL1 (with and without demand_lag 1), BL2, BL3, BL4, BL5, A9 (with and without demand_lag 1) and
  A8P at Sublet's parameters around A9 and BL1 (with and without the inner lag) on configs/toy.json under the trace
  lender and i.i.d. announcements, and BL2, BL3-0 and BL4 on four random toys, give runs whose digest (every ledger
  component, every lease record and the policy's report, wall-clock keys left out; test_ms5b_additions._digest)
  equals the digest of the same run on commit 56b847be, the last commit before C53 (DIGESTS_C53, measured on a
  clean copy of that commit's code/sim); passing the new options at their defaults gives the same digests;
- the options: Baseline.demand_of (moved from greedy.py unchanged) for BL2 and BL3, zeros for t < L, idempotent
  within a slot; BL2 and BL3 with demand_lag 1 make the decisions of BL2 and BL3 on the demand shifted by one slot
  (lenders without reclaims); params() at the defaults as before C53 (QUIET_KEYS), PolicyError for bad values,
  BL5 still refuses demand_lag; BL4's 'previous0': zeros in the first window, 'previous''s windows after it, no buy
  in the first window on a toy whose slot 0 has demand, information class online-I1 and no driver input;
- the tags (typed from design/ms7/feasibility/causal.md, RECOMMENDED DESIGN item 1) and their policies through
  make_policy (the inner lag of Sublet-lag and BL1-GP-lag), the lagged sets against ms5b_common's H1 and H2b sets,
  ms5b_common.TAGS unchanged;
- the job lists (gate 24 jobs and 96 runs, lag 176 jobs and 1,232 runs; reduced: week 101, 2-hour horizon), the
  gate (registration, clean tree, the analysis sha256; part lag after a passed part gate at HEAD; recorded and not
  enforced in reduced runs; never the confirmation's gate in a record), the identity checks of part gate, the
  hooks of e7h.run_week, COPY_PARTS['e7c'];
- the analysis on synthetic summaries (per policy with the weeks below 1, margins in H1's convention through
  ms5b_common.paired_margins with win, tie and loss counts and min-max, lagged minus revealed with BL5 against
  BL5-cur beside the revealed values, the guard, the identity Sublet-lag = A9-lag without projection, the gate, the
  registration record of the analysis sha256; no p-value);
With the versioned confirmation summaries (needs_ms5b_out): part gate's references hold every checked cell.
- run_e7c.sh with a fake driver (the pass order, the retry, the parts' folders, the refusal, E7C_ONLY, bash -n).
With the a12 outputs (needs_a12): reduced BL2-lag and BL4-lag week jobs through e7c's runner (run file, meta, gate
kind, parameters) and their summary.
"""
import copy
import hashlib
import inspect
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from fixtures import SIM, random_toy_config, toy_config

from sublet.algos import registry
from sublet.algos.common import PolicyError
from sublet.baselines.cocar import CoCaRStyle
from sublet.baselines.common import Baseline
from sublet.baselines.greedy import GreedyLease
from sublet.baselines.retrorenting import RetroRentingStyle
from sublet.baselines.ski import SkiRental
from sublet.baselines.spothedge import SpotHedgeStyle
from sublet.drivers.run import make_policy
from sublet.engine import EngineConfig, simulate
from sublet.experiments import e7c
from sublet.experiments import e7c_analysis as ea
from sublet.experiments import e7c_tags as ct
from sublet.experiments import e7h
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms5b_common as m5
from sublet.instance import build_instance, public_view
from sublet.types import LenderModel, SlowObs

RUN = SIM / "sublet" / "experiments" / "run_e7c.sh"
IID = {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.3}}
SUB = {"inner": "A9", "project": True, "allowance": "lb", "kappa": None}
QUIET = {"lenders.0.R": [], "lenders.1.R": []}

# sha256 of _digest(run) on commit 56b847be (before C53), per case of _cases()
DIGESTS_C53 = {
    'rand0:BL2:{}:trace': "5858437d8d88f2b1a6366536a84f2149de3cee979e36ea58f540bde189fece48",
    'rand0:BL3:{"n_extra": 0}:trace': "bd7f57389243f87f090b00ecbc97936ba23f82d81fa8516ab7f334aef9c3d4d7",
    'rand0:BL4:{}:trace': "44452f7a68e09a9a99a4599805b9f34f7fc61a53512090e68a9ea97ce32128d7",
    'rand1:BL2:{}:trace': "ae5c4576cf402f004e439995de73257bf7709b71cbf8ad5fc863f7abd77a1ba3",
    'rand1:BL3:{"n_extra": 0}:trace': "059e298254e7cfe13305ebe4d218ef00f5bfc55a1dfb4a88672dcf2fcf1fb414",
    'rand1:BL4:{}:trace': "973e838b55637b4db5acd2392eadfe8380d7842ae8a8d055ee9bbefedcede131",
    'rand2:BL2:{}:trace': "8b92a791d9544d2c866bc77264f9d9f6948b70456603a8809029f87d36db6cd2",
    'rand2:BL3:{"n_extra": 0}:trace': "fe34ce5b67707881b533056191cba42da1189cacbc949658830cf674c011f1d5",
    'rand2:BL4:{}:trace': "1d58e370c878dd318a03a8d924178a96964ccbaa168f4135cb4f689c733bc74e",
    'rand3:BL2:{}:trace': "b5feda82180ef11bc546a14a90924c43f995fc4cefe891347603c956f64aaf79",
    'rand3:BL3:{"n_extra": 0}:trace': "3e38db028d8ada698a1c1a2ae3b90bf829d14e175e660e10b305d5fae26624e1",
    'rand3:BL4:{}:trace': "60439a32ed87fbaebcf7562c0996a04905b6cbfe11c9441197930e4d7cd7f25a",
    'toy:A8P:{"allowance": "lb", "inner": "A9", "inner_params": {"demand_lag": 1}, "kappa": null, "project": true}:'
    'iid0.3': "ab7e36addd3fe67b4d16ff23589de0390ffe9097a0e85af12838f01ae2460fdd",
    'toy:A8P:{"allowance": "lb", "inner": "A9", "inner_params": {"demand_lag": 1}, "kappa": null, "project": true}:'
    'trace': "09f721752b288ec1a5272678a09bc5b58d0ba905204ce37b168e6612beb2858a",
    'toy:A8P:{"allowance": "lb", "inner": "A9", "kappa": null, "project": true}:iid0.3':
        "5503f2d7989380eeafc39ba39d2294105f113a594669b2e0bb879d05845fe1a9",
    'toy:A8P:{"allowance": "lb", "inner": "A9", "kappa": null, "project": true}:trace':
        "df80b5c803a218679e1fe3f9dc9bd0dbc310ae191551ffb0945a6213f16880fa",
    'toy:A8P:{"allowance": "lb", "inner": "BL1", "inner_params": {"demand_lag": 1}, "kappa": null, "project": true}:'
    'iid0.3': "1110618982c7f1ddfd2f179d5e9e932ec71e9eef70f262ab4c3582d089453d15",
    'toy:A8P:{"allowance": "lb", "inner": "BL1", "inner_params": {"demand_lag": 1}, "kappa": null, "project": true}:'
    'trace': "d023d854054ce31770d3700d5ea4ad0cbe07f3e0a7aab8b4f74ec393a3c09da4",
    'toy:A8P:{"allowance": "lb", "inner": "BL1", "kappa": null, "project": true}:iid0.3':
        "9bcde8d7db9e1256fe07be230ccd7c907243ad71790bc05e9f93d7eacb76640c",
    'toy:A8P:{"allowance": "lb", "inner": "BL1", "kappa": null, "project": true}:trace':
        "16658c0676aa70ccfd72de5c1ff388848edd7e6d42a3ef2901a5d6ed78b1009d",
    'toy:A9:{"demand_lag": 1}:iid0.3': "06d1c2f39514985150d4bf69f988dc0e861d83b62277a8b3dd5ff46f3f6b0bec",
    'toy:A9:{"demand_lag": 1}:trace': "0dbb2a65566c55f40aae395fa3690901427d6a4c42c657f2c09e9e3bd9d43287",
    'toy:A9:{}:iid0.3': "31c31e26bf41d4fff69a23bc61dd3c6c865d5b373fef58591be29ebc73d6de47",
    'toy:A9:{}:trace': "8e4a3765e46a4c92a63c88f174e24da9c88291e1aadf0a7206a5c116f0b9784b",
    'toy:BL1:{"demand_lag": 1}:iid0.3': "838bb8be3967f9377a6519c8fbb96d944e72c3114c31e669dff7ed2d0e4be91d",
    'toy:BL1:{"demand_lag": 1}:trace': "af091ed2633f4fa4599b4844d73185ca7f40bfe26e83dbcb44e2fa95ccc8d616",
    'toy:BL1:{}:iid0.3': "ef6463320ce8449a0fa416f9ece18ac567507f2b2b04e156f332d866e59032d2",
    'toy:BL1:{}:trace': "405d865c071993b1a1e7b56140f6bdcc29a73aa0adf3d52148ad4d322d97f855",
    'toy:BL2:{"keep": "s0"}:iid0.3': "99adfb1ce5c248366426410bc68ca6949ad6b5d48e7547395085a5b66bd549c3",
    'toy:BL2:{"keep": "s0"}:trace': "bc579a43d702ee085a7ecd439d77835453e151782b7fa38506537bb0abeaee79",
    'toy:BL2:{}:iid0.3': "ab641eefea57e7189a222a40891e54c52b4924b8c619557644ff193eacce3fca",
    'toy:BL2:{}:trace': "28d519aeb617fd4afe7c674b25314eed42f79858f2bc94b6c5f64a76edfeadf3",
    'toy:BL3:{"n_extra": 0}:iid0.3': "1ffd5ac3c5f8d3066e0f01ceb701a6acf89b4e2e28b2fd337ce41665070d7c22",
    'toy:BL3:{"n_extra": 0}:trace': "41348b629fa8cc5af5c3a1d720d3eb624d43151223da7297079b25bfc8b53f45",
    'toy:BL3:{}:iid0.3': "17604d741c9efc44cdaf429ce1371f6d12d017a918710a778c73239a75b4ace1",
    'toy:BL3:{}:trace': "e87378122aadfe52f43933d3f26275938f380ba3da8af44b7e239aa8418380b3",
    'toy:BL4:{}:iid0.3': "e025475f00633e9109501c03b7aae43d74220ab2697c498d493f5c20e5c39906",
    'toy:BL4:{}:trace': "d4d917d344239c531350104e0bfeb6d223b61b3d16b48a6d5fc587a3d5ad85bd",
    'toy:BL5:{}:iid0.3': "cdff81b5724888100d62e1dd0d071ca629933f1f40cc93d75aa46a372154f226",
    'toy:BL5:{}:trace': "0602d6a414ad7fecb0e94e8fc834124ccb01c18f6ffe0cc43ec0fff3374fa411",
}
# the new options at their defaults, per registry id (A8P: none of its own)
NEW_DEFAULTS = {"BL1": {"demand_lag": 0}, "BL2": {"demand_lag": 0}, "BL3": {"demand_lag": 0},
                "BL4": {"demand": "previous"}, "BL5": {}, "A9": {}, "A8P": {}}


# ---------------------------------------------------------------- runs and digests
def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items() if "time_s" not in str(k) and "wall_s" not in str(k)}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return float(x).hex()
    return x


def _digest(res) -> str:
    """tests/test_ms5b_additions._digest."""
    comp = {k: float(v).hex() for k, v in sorted(res.components.items())}
    leases = [[L.site, L.contract, L.gpus, L.start_slot, L.start_min, L.prepaid_end_min, L.announce_slot, L.death_min,
               L.release_min, L.end_min, L.end_cause, float(L.prepaid_usd).hex(), float(L.rent_usd).hex(), L.tag]
              for L in res.leases]
    rep = _jsonable(res.metrics.get("policy") or {})
    blob = json.dumps({"components": comp, "leases": leases, "report": rep}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def _cases() -> dict:
    """{name: (config, policy id, params, lender model fields, seed)}, the cases of DIGESTS_C53."""
    toy = toy_config()
    out = {}
    for pid, params in (("BL1", {}), ("BL1", {"demand_lag": 1}), ("BL2", {}), ("BL2", {"keep": "s0"}), ("BL3", {}),
                        ("BL3", {"n_extra": 0}), ("BL4", {}), ("BL5", {}), ("A9", {}), ("A9", {"demand_lag": 1}),
                        ("A8P", {**SUB, "inner": "BL1"}),
                        ("A8P", {**SUB, "inner": "BL1", "inner_params": {"demand_lag": 1}}),
                        ("A8P", SUB), ("A8P", {**SUB, "inner_params": {"demand_lag": 1}})):
        out[f"toy:{pid}:{json.dumps(params, sort_keys=True)}:trace"] = (toy, pid, params, {}, 0)
        out[f"toy:{pid}:{json.dumps(params, sort_keys=True)}:iid0.3"] = (toy, pid, params, IID, 3)
    for s in range(4):
        cfg = random_toy_config(np.random.default_rng(100 + s), n_clients=2, two_llms=bool(s % 2))
        for pid, params in (("BL2", {}), ("BL3", {"n_extra": 0}), ("BL4", {})):
            out[f"rand{s}:{pid}:{json.dumps(params, sort_keys=True)}:trace"] = (cfg, pid, params, {}, s)
    return out


CASES = _cases()


def _run(inst, pid, params, lm=None, seed=0):
    pol = make_policy({"policy": {"id": pid, "params": dict(params)}}, inst)
    model = LenderModel(**{"schedule": "trace", "information": "I1", **(lm or {})})
    res = simulate(inst, pol, model, EngineConfig(check_invariants=True), lender_seed=seed, policy_seed=seed)
    assert not res.invariant_failures, res.invariant_failures[:3]
    return res


def _with_defaults(pid, params) -> dict:
    """params with the C53 options of the policy (or of A8P's inner BL1) at their defaults."""
    if pid == "A8P":
        if params.get("inner") == "BL1":
            return {**params, "inner_params": {"demand_lag": 0, **dict(params.get("inner_params") or {})}}
        return dict(params)
    return {**NEW_DEFAULTS[pid], **params}


@pytest.mark.parametrize("name", sorted(CASES))
def test_defaults_reproduce_runs(name):
    """Every run of DIGESTS_C53 equals that of commit 56b847be bit for bit, report included, also with the new options
    passed at their defaults."""
    assert set(CASES) == set(DIGESTS_C53)
    cfg, pid, params, lm, seed = CASES[name]
    inst = build_instance(cfg)
    assert _digest(_run(inst, pid, params, lm, seed)) == DIGESTS_C53[name], name
    assert _digest(_run(inst, pid, _with_defaults(pid, params), lm, seed)) == DIGESTS_C53[name], name


# ---------------------------------------------------------------- the options
def test_option_keys_validation_and_registry():
    # subset checks: C54 (test_ms7_baselines.py) adds further keys to the same classes
    assert SkiRental.PARAMS.items() >= {"keep": "none", "defer_release": True, "demand_lag": 0}.items()
    assert SpotHedgeStyle.PARAMS.items() >= {"n_extra": 2, "react_at": "notice", "zone": "lender",
                                             "hysteresis_min": 10, "defer_release": True, "demand_lag": 0}.items()
    assert CoCaRStyle.PARAMS.items() >= {"window_min": 60, "demand": "previous"}.items()
    # params() at the defaults: the keys before C53; a set option is listed
    assert SkiRental().params() == SkiRental(demand_lag=0).params() == {"keep": "none", "defer_release": True}
    assert SpotHedgeStyle().params() == {"n_extra": 2, "react_at": "notice", "zone": "lender", "hysteresis_min": 10,
                                         "defer_release": True}
    assert SkiRental(demand_lag=1).params()["demand_lag"] == 1
    assert SpotHedgeStyle(n_extra=0, demand_lag=1).params()["demand_lag"] == 1
    assert CoCaRStyle(demand="previous0").params() == {"window_min": 60, "demand": "previous0"}
    # demand_of is Baseline's, shared by BL1, BL2, BL3 (and inherited, unused, by A9)
    assert GreedyLease.demand_of is Baseline.demand_of is SkiRental.demand_of is SpotHedgeStyle.demand_of
    assert "demand_of" not in GreedyLease.__dict__
    for cls, kw in ((SkiRental, {"demand_lag": -1}), (SkiRental, {"demand_lag": True}),
                    (SkiRental, {"demand_lag": 0.5}), (SpotHedgeStyle, {"demand_lag": -1}),
                    (SpotHedgeStyle, {"demand_lag": "1"}),
                    (CoCaRStyle, {"demand": "previous1"}), (CoCaRStyle, {"demand_lag": 1}),
                    (RetroRentingStyle, {"demand_lag": 1})):
        with pytest.raises(PolicyError):
            cls(**kw)
    for pid in ("BL2", "BL3"):
        assert "demand_lag" in registry.param_names(pid)
    assert registry.info_class("BL4", {"demand": "previous0"}) == "online-I1"
    assert registry.needed_inputs("BL4", {"demand": "previous0"}) == ()
    assert registry.info_class("BL2", {"demand_lag": 1}) == registry.info_class("BL3", {"demand_lag": 1}) == "online-I1"


def _obs(inst, t: int, D: float) -> SlowObs:
    n, phi = inst.n, inst.grid.phi
    return SlowObs(t=t, minute=t * inst.grid.slow_min, demand=np.full((n, phi), float(D)), leases={}, replicas={},
                   notices=[], ended=[], results=[], site_announced=None, served_prev=np.zeros((inst.J, inst.m)),
                   fallback_prev=np.zeros(n), cost_so_far=0.0)


@pytest.mark.parametrize("cls,kw", [(SkiRental, {}), (SpotHedgeStyle, {"n_extra": 0})])
def test_demand_of(cls, kw):
    """Baseline.demand_of for BL2 and BL3: obs.demand itself without a lag, slot t - L's demand with demand_lag L (zeros
    for t < L), the same array when called twice in a slot; act reads it."""
    inst = build_instance(toy_config())
    v = public_view(inst, "I1")
    seq = [0.0, 1.5, 0.3, 2.0, 0.0, 1.0]
    for lag in (0, 1, 2):
        pol = cls(**kw, demand_lag=lag)
        pol.reset(v, np.random.default_rng(0))
        for t, D in enumerate(seq):
            obs = _obs(inst, t, D)
            if lag == 0:
                assert pol.demand_of(obs) is obs.demand
            want = seq[t - lag] if t >= lag else 0.0
            a = pol.demand_of(obs)
            assert np.all(a == want) and a.shape == obs.demand.shape, (cls.__name__, lag, t)
            assert np.array_equal(pol.demand_of(obs), a)
            pol.act(obs)
            assert len(pol._lagged) <= lag + 1


def _shifted(cfg: dict, phi: int) -> dict:
    out = copy.deepcopy(cfg)
    for cl in out["borrowers"]["clients"]:
        d = list(cl["demand"]["values"])
        cl["demand"]["values"] = [0.0] * phi + d[:-phi]
    return out


@pytest.mark.parametrize("pid,params", [("BL2", {}), ("BL2", {"keep": "s0"}), ("BL3", {"n_extra": 0}), ("BL3", {})])
def test_lag_is_the_shifted_demand(pid, params):
    """BL2 and BL3 with demand_lag 1 make the decisions of BL2 and BL3 on the demand shifted by one slow slot (lenders
    without reclaims, so the lender does not depend on the decisions): the toy and a random toy with 1-minute fast
    slots; and the lag changes the decisions."""
    rec = lambda res: [(L.site, L.contract, L.start_slot, L.release_min, L.end_cause) for L in res.leases]
    cfgs = [toy_config(QUIET)]
    r = random_toy_config(np.random.default_rng(7), fast_min=1, n_clients=2)
    r["lenders"][0]["R"], r["lenders"][1]["R"] = [], []
    cfgs.append(r)
    for cfg in cfgs:
        inst = build_instance(cfg)
        lagged = _run(inst, pid, {**params, "demand_lag": 1})
        shifted = _run(build_instance(_shifted(cfg, inst.grid.phi)), pid, params)
        assert rec(lagged) and rec(lagged) == rec(shifted), (pid, params)
        assert rec(lagged) != rec(_run(inst, pid, params))


def test_bl2_lag_reaches_every_siloed_sub_run():
    """BL2-lag through ms4_common.siloed_run (the runner of E7's and E7h's BL2 rows) on the toy with two borrowers:
    every borrower's sub-policy has demand_lag 1 in its resolved parameters (none at the default), and the lag
    changes the run."""
    from fixtures import explicit_client
    from sublet.drivers.run import build, load_run_spec
    from sublet.experiments import ms4_common as m4
    cfg = toy_config(QUIET)
    dem = cfg["borrowers"]["clients"][0]["demand"]["values"]
    cfg["borrowers"]["clients"] = [explicit_client(dem, borrower="b0"),
                                   explicit_client([0.0, 0.5, 2.0, 1.5, 0.5, 0.0] * 4, borrower="b1")]
    out = {}
    for lag in (0, 1):
        spec = load_run_spec({"schema_version": 1, "name": "t_ms7_bl2", "instance": cfg,
                              "engine": {"check_invariants": True},
                              "policy": {"id": "BL2", "params": {"demand_lag": lag} if lag else {}},
                              "seeds": {"config": [1], "lender": "config", "policy": [0]}})
        inst, model, ecfg = build(spec, 1)
        d = m4.siloed_run(inst, spec, model, ecfg, 1, 0)
        assert d["inner_id"] == "BL2" and len(d["sub_runs"]) == 2
        for row in d["sub_runs"]:
            assert row["n_invariant_failures"] == 0
            assert row["resolved_params"].get("demand_lag", 0) == lag
            assert ("demand_lag" in row["resolved_params"]) == bool(lag)
        out[lag] = d["components"]["total"]
    assert out[0] != out[1]


def test_bl4_previous0():
    """'previous0': zeros as dhat in the first window, 'previous''s forecast in every later window; on a toy whose
    every slot has demand 1 'previous' buys at slot 0 and 'previous0' buys nothing in the first window; the report's
    information class is online-I1."""
    inst = build_instance(toy_config({"time.fast_slot_min": 1, "borrowers.clients.0.demand.values": [0.0] * 120}))
    v = public_view(inst, "I1")
    pols = {}
    for dem in ("previous", "previous0"):
        p = CoCaRStyle(window_min=10, demand=dem)
        p.reset(v, np.random.default_rng(0))
        for t, mu in enumerate([0.2, 0.8, 0.5]):
            o = _obs(inst, t, 0.0)
            o.demand[0, :] = [mu * 5, 0, 0, 0, 0]
            p.hist.push(o)
        pols[dem] = p
    assert np.allclose(pols["previous"]._dhat(0, 2), [[0.2, 0.2]])
    assert np.array_equal(pols["previous0"]._dhat(0, 2), np.zeros((1, 2)))
    assert np.array_equal(pols["previous0"]._dhat(2, 2), pols["previous"]._dhat(2, 2))
    assert np.allclose(pols["previous0"]._dhat(2, 2), [[0.2, 0.8]])
    one = toy_config({**QUIET, "borrowers.clients.0.demand.values": [1] * 24})
    runs = {dem: _run(build_instance(one), "BL4", {"demand": dem}) for dem in ("previous", "previous0")}
    nW = 60 // build_instance(one).grid.slow_min
    assert any(L.start_slot == 0 for L in runs["previous"].leases)
    assert runs["previous0"].leases and min(L.start_slot for L in runs["previous0"].leases) >= nW
    assert runs["previous0"].metrics["policy"]["info_class"] == "online-I1"
    assert runs["previous0"].metrics["policy"]["demand"] == "previous0"


# ---------------------------------------------------------------- the tags
# typed from design/ms7/feasibility/causal.md, RECOMMENDED DESIGN item 1 (None: an instance-dependent rule)
SPEC_LAG = {"Sublet-lag": ("A8P", None), "A9-lag": ("A9", {"demand_lag": 1}), "BL1-lag": ("BL1", {"demand_lag": 1}),
            "BL1-BO-lag": ("BL1", {"backoff_cap": 288, "demand_lag": 1}), "BL2-lag": ("BL2", {"demand_lag": 1}),
            "BL3-0-lag": ("BL3", {"n_extra": 0, "demand_lag": 1}), "BL4-lag": ("BL4", {"demand": "previous0"}),
            "BL5-tau60-lag": ("BL5", {"tau_min": 60}), "BL5N-lag": ("BL5", {"contract_rule": "c2", "mbb": True}),
            "BL1N-lag": ("A9", {"target": "ceil", "release": "now", "demand_lag": 1}), "BL1-GP-lag": ("A8P", None)}


def test_tags():
    assert ct.LAG_TAGS == tuple(SPEC_LAG) and len(ct.LAG_TAGS) == 11
    for t, (pid, params) in SPEC_LAG.items():
        tg = ct.tag(t)
        assert tg.id == pid and tg.kind == "lag", t
        if params is not None:
            assert tg.params == params and ct.tag_params(t) == params, t
        assert ct.REVEALED_OF[t] in m5.TAGS, t
        assert (t in m5.TAGS) == (t in ct.SHARED), t
    for t in ct.SHARED:
        assert ct.TAGS[t] is m5.TAGS[t]
    assert not any(t.endswith("-lag") and t not in ct.SHARED for t in m5.TAGS)        # ms5b_common.TAGS unchanged
    assert ct.tag("BL2") is m5.TAGS["BL2"] and ct.tag_params("BL3-0") == {"n_extra": 0}
    with pytest.raises(KeyError):
        ct.tag("BL9-lag")
    assert set(ct.H1_LAGGED) == set(m5.H1_SET) and set(ct.NOTICE_LAGGED) == set(m5.H2B_SET)
    assert set(ct.H1_LAGGED.values()) <= set(ct.LAG_TAGS) | set(ct.LAGGED_FROM_MAIN)
    assert ct.LAGGED_FROM_MAIN == {"BL5": "BL5"} and ct.REVEALED_OF_MAIN == {"BL5": "BL5-cur"}
    assert m5.TAGS["BL5"].params == {} and not m5.TAGS["BL5"].params.get("use_current_slot")
    inst = build_instance(toy_config())
    assert ct.tag_params("Sublet-lag", inst) == {**m5.sublet_v2_params(inst), "inner_params": {"demand_lag": 1}}
    assert ct.tag_params("BL1-GP-lag", inst) == {**m5.tag_params("BL1-GP", inst), "inner_params": {"demand_lag": 1}}
    with pytest.raises(ValueError):
        ct.tag_params("BL1-GP-lag")
    for t in ct.LAG_TAGS:
        pol = make_policy({"policy": {"id": ct.tag(t).id, "params": ct.tag_params(t, inst)}}, inst)
        inner = getattr(pol, "inner", None)
        got = (inner.params() if t in ct.GUARD_REALIZED else pol.params())
        if t != "BL4-lag" and not t.startswith("BL5"):
            assert got["demand_lag"] == 1, t
    tab = ct.tag_table(["BL1-GP-lag", "Sublet-lag", "BL2"])
    assert tab["BL1-GP-lag"]["guard_reads_realized_slot"] is True and tab["Sublet-lag"]["revealed"] == "Sublet"
    assert tab["BL2"] == m5.tag_table(["BL2"])["BL2"] and ct.is_guarded("BL1-GP-lag") and not ct.is_guarded("BL2-lag")


# ---------------------------------------------------------------- jobs, gate, identity checks
def test_jobs(monkeypatch):
    monkeypatch.delenv(e7c.REDUCED_ENV, raising=False)
    g, lag = e7c.jobs(["gate"]), e7c.jobs(["lag"])
    mc.check_jobs(e7c.jobs_all())
    assert len(g) == 24 and sum(len(e7h.expected_runs(j)) for j in g) == 96
    assert len(lag) == 176 and sum(len(e7h.expected_runs(j)) for j in lag) == 1232
    for j in g + lag:
        p = j.params
        assert j.kind == "pool" and p["kind"] == "week" and p["policy_seeds"] == [0] and p["horizon_min"] == m5.WEEK_MIN
        assert j.id == mc.job_id("e7c", p["part"], k="week", tag=p["tag"], c=p["c"])
    assert {(j.params["tag"], j.params["c"]) for j in lag} == {(t, c) for t in ct.LAG_TAGS for c in range(301, 317)}
    assert all(j.params["modes"] == list(m5.conf_modes()) for j in lag)
    a = [j for j in g if j.params["tag"] in e7c.GATE_DEFAULT_TAGS]
    b = [j for j in g if j.params["tag"] in e7c.GATE_LAG_TAGS]
    assert {j.params["c"] for j in a} == {301, 302} and all(j.params["modes"] == list(m5.conf_modes()) for j in a)
    assert {j.params["c"] for j in b} == {301, 302, 303, 304} and all(j.params["modes"] == ["L-tr"] for j in b)
    monkeypatch.setenv(e7c.REDUCED_ENV, "1")
    red = e7c.jobs_all()
    assert {j.params["c"] for j in red} == {101} and {j.params["horizon_min"] for j in red} == {120}
    assert len(red) == len(e7c.GATE_DEFAULT_TAGS) + len(e7c.GATE_LAG_TAGS) + len(ct.LAG_TAGS)
    monkeypatch.setenv("E7C_PART", "lag")
    assert e7c.parts() == ["lag"]
    monkeypatch.setenv("E7C_PART", "main")
    with pytest.raises(ValueError):
        e7c.parts()
    assert mc.COPY_PARTS["e7c"] == e7c.PARTS == ("gate", "lag")


def _reg(**kw) -> dict:
    rec = {"head": "h" * 40, "registration": e7c.REGISTRATION, "registration_at_head": True,
           "registration_sha256": "r" * 64, "analysis_sha256_registered": "a" * 64, "analysis_sha256_head": "a" * 64,
           "analysis_sha256_disk": "a" * 64, "dirty_paths": []}
    rec.update(kw)
    return rec


def test_registration_gate(monkeypatch):
    assert e7c.check_registration(_reg())[0] is True
    for kw, frag in (({"registration_at_head": False, "analysis_sha256_registered": None}, "does not exist at HEAD"),
                     ({"dirty_paths": [" M x"]}, "dirty"), ({"dirty_paths": None}, "cannot tell"),
                     ({"analysis_sha256_registered": None}, "records no line"),
                     ({"analysis_sha256_disk": "b" * 64}, "analysis_sha256_disk"),
                     ({"analysis_sha256_head": None}, "analysis_sha256_head")):
        ok, why, _ = e7c.check_registration(_reg(**kw))
        assert not ok and frag in why, kw
    text = "# Registration\n\ne7c_analysis_sha256: " + "c" * 64 + "\nother_sha256: " + "d" * 64 + "\n"
    assert e7c.registered_sha256(text) == "c" * 64 and e7c.registered_sha256("no hash") is None
    gp = {"exists": True, "reduced": False, "git_revision": "h" * 40, "pass": True, "n_checks": 96, "n_equal": 96}
    assert e7c.check_gate_part(gp, "h" * 40)[0] is True
    for kw in ({"exists": False}, {"reduced": True}, {"git_revision": "x" * 40}, {"pass": False}):
        assert e7c.check_gate_part({**gp, **kw}, "h" * 40)[0] is False, kw
    # enforced in full runs, recorded in reduced runs; part lag also reads part gate's summary
    monkeypatch.setattr(e7c, "registration_record", lambda: _reg(dirty_paths=[" M x"]))
    monkeypatch.setattr(e7c, "_GATE", {})
    monkeypatch.delenv(e7c.REDUCED_ENV, raising=False)
    with pytest.raises(RuntimeError, match="dirty"):
        e7c.gate("gate")
    monkeypatch.setattr(e7c, "_GATE", {})
    monkeypatch.setenv(e7c.REDUCED_ENV, "1")
    g = e7c.gate("lag")
    assert g["kind"] == "ms7_registration" and g["ok"] is False and g["enforced"] is False and "gate_part" in g
    job = e7c.jobs(["lag"])[0]
    meta = e7c._meta_run(job)
    assert meta["exp"] == "e7c" and meta["gate"]["kind"] == "ms7_registration" and "confirmation" not in meta["gate"]
    monkeypatch.setattr(e7c, "registration_record", lambda: _reg())
    monkeypatch.setattr(e7c, "gate_part_record", lambda root=None: dict(gp))
    monkeypatch.setattr(e7c, "_GATE", {})
    monkeypatch.delenv(e7c.REDUCED_ENV, raising=False)
    assert e7c.gate("lag")["ok"] is True
    monkeypatch.setattr(e7c, "gate_part_record", lambda root=None: {**gp, "pass": False})
    monkeypatch.setattr(e7c, "_GATE", {})
    with pytest.raises(RuntimeError, match="identity checks did not pass"):
        e7c.gate("lag")


def _table(entries) -> dict:
    t: dict = {}
    for (tag, mode, cell), v in entries.items():
        t.setdefault(tag, {}).setdefault(mode, {}).setdefault(cell, {})["0"] = v
    return t


def test_identity_checks():
    a = {(t, m, str(c)): 0.5 + 0.01 * i for i, (t, m, c) in enumerate(
        (t, m, c) for t in e7c.GATE_DEFAULT_TAGS for m in m5.conf_modes() for c in e7c.GATE_DEFAULT_WEEKS)}
    b = {(t, "L-tr", str(c)): 0.6 + 0.01 * i for i, (t, c) in enumerate(
        (t, c) for t in e7c.GATE_LAG_TAGS for c in e7c.GATE_LAG_WEEKS)}
    refs = {"a": {"part": "main", "table": _table(a)}, "b": {"part": "second", "table": _table(b)}}
    ours = _table({**a, **b})
    d = e7c.identity_checks(ours, refs, reduced=False)
    assert d["pass"] is True and d["n_checks"] == d["n_equal"] == 96 and d["max_abs_diff"] == 0.0
    k = ("BL2", "L-eg", "302")
    bad = _table({**a, **b, k: a[k] + 1e-15})
    d = e7c.identity_checks(bad, refs, reduced=False)
    assert d["pass"] is False and d["n_differ"] == 1 and d["max_abs_diff"] > 0
    miss = {**a, **b}
    del miss[("Sublet-lag", "L-tr", "303")]
    d = e7c.identity_checks(_table(miss), refs, reduced=False)
    assert d["pass"] is False and d["n_missing_run"] == 1
    d = e7c.identity_checks(ours, {"a": refs["a"], "b": {"part": "second", "table": None}}, reduced=False)
    assert d["pass"] is False and d["n_no_reference"] == 12
    d = e7c.identity_checks(ours, refs, reduced=True)
    assert d["pass"] is False and d["n_no_reference"] == d["n_checks"] == 6 * 7 + 3 and "note" in d


@pytest.mark.needs_ms5b_out("sublet_v2/main/summary.json", "sublet_v2/second/summary.json")
def test_gate_references_hold_every_cell():
    """The versioned references of part gate (this repository's out/sublet_v2/{main,second}/summary.json) hold an r0
    for every checked cell, and their sha256 is recorded."""
    r = e7c.reference_tables()
    for k in ("a", "b"):
        assert r[k]["sha256"] and r[k]["table"]
    d = e7c.identity_checks(_table({}), r, reduced=False)
    assert d["n_no_reference"] == 0 and d["n_missing_run"] == 96


def test_run_week_hooks():
    sig = inspect.signature(e7h.run_week)
    assert sig.parameters["tags"].default is None and sig.parameters["meta_of"].default is None
    assert sig.parameters["tags"].kind is inspect.Parameter.KEYWORD_ONLY
    src = inspect.getsource(e7c.run)
    assert "tags=ct" in src and "meta_of=_meta_run" in src


# ---------------------------------------------------------------- the analysis
def _summ(entries, runs=(), meta=None) -> dict:
    return {"meta": meta or {"reduced": False, "git_revision": "h" * 40}, "table": _table(entries), "runs": list(runs)}


def _week_vals(tag, w, r0, stress=0.9, hon=0.4):
    out = {(tag, "L-tr", w): r0, (tag, "L-hon", w): hon}
    for i, m in enumerate(m5.stress_modes()):
        out[(tag, m, w)] = stress - 0.01 * i
    return out


def test_analysis_on_synthetic_summaries():
    weeks = ["301", "302", "303"]
    lag, main = {}, {}
    for i, w in enumerate(weeks):
        lag.update(_week_vals("Sublet-lag", w, 0.60 + 0.01 * i, stress=0.75))
        lag.update(_week_vals("A9-lag", w, 0.60 + 0.01 * i, stress=0.75))
        for j, t in enumerate(("BL1-lag", "BL1-BO-lag", "BL2-lag", "BL3-0-lag", "BL4-lag")):
            lag.update(_week_vals(t, w, 0.70 + 0.01 * j, stress=1.10 + 0.01 * j))
        for j, t in enumerate(("BL5-tau60-lag", "BL1-GP-lag", "BL1N-lag", "BL5N-lag")):
            lag.update(_week_vals(t, w, 0.55 + 0.01 * j, stress=0.70 + 0.03 * j))
        main.update(_week_vals("BL5", w, 0.68 if w != "302" else 0.55, stress=1.05))
        main.update(_week_vals("BL5-cur", w, 0.62, stress=1.00))
        for t in ct.REVEALED_OF.values():
            main.update(_week_vals(t, w, 0.50, stress=0.80))
    del lag[("BL2-lag", "L-co", "303")]                         # a missing stress run: W0 of week 303 is missing
    g = lambda ps, ab=False: {"projected_slots": ps, "aborted": ab, "held": True, "env_ok": True, "projection": {}}
    runs = [{"tag": "Sublet-lag", "mode": m, "cell": w, "seed": 0, "status": "ok", "r0": lag[("Sublet-lag", m, w)],
             "guard": g(3 if (w, m) == ("302", "L-eg") else 0)} for w in weeks for m in m5.conf_modes()]
    runs += [{"tag": "BL1-GP-lag", "mode": m, "cell": w, "seed": 0, "status": "ok", "r0": 0.0, "guard": g(100)}
             for w in weeks for m in m5.conf_modes()]
    s = {"lag": _summ(lag, runs), "main": _summ(main),
         "gate": {"meta": {"reduced": False, "git_revision": "h" * 40},
                  "decision": {"pass": True, "n_checks": 96, "n_equal": 96}}, "inputs": {}}
    a = ea.analyse(s)
    assert a["meta"]["weeks"] == weeks and a["policies"][-1] == "BL5"
    assert a["meta"]["weeks_are_confirmation_weeks"] is False
    pp = a["per_policy"]
    assert pp["Sublet-lag"]["r0"]["median"] == pytest.approx(0.61) and pp["Sublet-lag"]["W0"]["max"] == 0.75
    assert pp["Sublet-lag"]["RC"]["weeks"]["301"] == pytest.approx(0.60 - 0.4)
    assert pp["BL5"]["r0"]["weeks"]["302"] == 0.55 and pp["BL2-lag"]["W0"]["n_missing"] == 1
    assert pp["Sublet-lag"]["W0"]["n_below_1"] == 3 and pp["BL2-lag"]["W0"]["n_below_1"] == 0
    assert pp["BL5"]["r0"]["n_below_1"] == 3 and "n_below_1" not in pp["BL5"]["RC"]
    # margins against H1's lagged set in H1's convention (min over the set minus Sublet-lag; ms5b_common.
    # paired_margins): the cheapest L-tr r0 is BL5's (main) in every week, below Sublet-lag's in week 302 only
    h = a["margins"]["h1"]["r0"]
    assert h["weeks"]["302"]["best"] == "BL5" and h["weeks"]["302"]["delta"] == pytest.approx(0.55 - 0.61)
    assert h["weeks"]["301"]["best"] == "BL5" and h["weeks"]["301"]["delta"] == pytest.approx(0.68 - 0.60)
    assert (h["n_wins"], h["n_losses"], h["n_ties"], h["n_lost_missing"]) == (2, 1, 0, 0)
    assert h["weeks"]["301"]["sublet"] == pytest.approx(0.60) and h["weeks"]["301"]["best_value"] == 0.68
    sub = {x: lag[("Sublet-lag", "L-tr", x)] for x in weeks}
    oth = {t: {x: (main if t == "BL5" else lag)[(t, "L-tr", x)] for x in weeks} for t in ea.H1_SET}
    want = m5.paired_margins(sub, oth, weeks)
    assert all(h["weeks"][x]["delta"] == want[x]["delta"] and h["weeks"][x]["best"] == want[x]["best"]
               for x in weeks)                                   # the function of ms5b_analysis.h1
    w = a["margins"]["h1"]["W0"]
    assert w["n_lost_missing"] == 1 and w["weeks"]["303"]["missing"] == ["BL2-lag"] and w["n_wins"] == 2
    assert w["weeks"]["303"]["delta"] is None and w["n"] == 2
    assert w["min"] == w["max"] == pytest.approx(1.05 - 0.75)
    nt = a["margins"]["notice"]["r0"]
    assert nt["n_losses"] == 3 and nt["n_wins"] == 0 and nt["max"] == pytest.approx(0.55 - 0.60)
    assert nt["weeks"]["303"]["best"] == "BL5-tau60-lag"
    assert a["margins"]["notice"]["W0"]["weeks"]["301"]["best"] == "BL5-tau60-lag"
    # lagged minus revealed: BL5 (main) against BL5-cur; a lag tag against main's counterpart; the revealed values
    d = a["lag_minus_revealed"]
    assert d["BL5"]["revealed"] == "BL5-cur" and d["BL5"]["r0"]["weeks"]["302"] == pytest.approx(0.55 - 0.62)
    assert d["BL5"]["r0"]["revealed"]["median"] == 0.62 and d["BL5"]["W0"]["revealed"]["max"] == 1.00
    assert d["Sublet-lag"]["revealed"] == "Sublet" and d["Sublet-lag"]["r0"]["min"] == pytest.approx(0.10)
    assert d["Sublet-lag"]["r0"]["revealed"]["weeks"] == {x: 0.50 for x in weeks}
    assert d["BL5-tau60-lag"]["revealed"] == "BL5-tau60" and d["BL1-GP-lag"]["lagged_from"] == "lag"
    # the guard and the identity (the projected run is left out)
    gd = a["guard"]["by_tag"]
    assert gd["Sublet-lag"] == {"runs": 21, "runs_projected": 1, "projected_slots": 3, "aborts": 0, "held": 21,
                                "envelope_violations": 0, "K0": 0}
    assert gd["BL1-GP-lag"]["projected_slots"] == 2100
    i = a["identity"]
    assert i["n_pairs"] == 20 and i["n_exact"] == 20 and i["holds"] is True and i["n_left_out"] == 1
    runs[1]["r0"] += 1e-12
    i2 = ea.identity(s)
    assert i2["holds"] is False and i2["max_abs_diff"] == pytest.approx(1e-12, rel=1e-3)
    assert a["gate"]["pass"] is True and a["gate"]["same_commit"] is True
    # no p-value, no interval (D4)
    def keys(x):
        if isinstance(x, dict):
            for k, v in x.items():
                yield k
                yield from keys(v)
        elif isinstance(x, list):
            for v in x:
                yield from keys(v)
    bad = {"p", "p_value", "wilcoxon", "sign_test", "ci", "bootstrap"}
    assert not bad & set(keys(a))
    md = ea.report(a)
    assert "Margin of Sublet-lag against H1's set, r0" in md and "holds True" in md and "wins (delta > 0) 2" in md


def test_analysis_registration_record(tmp_path):
    """meta.registration: the analysis file's sha256 against the line 'e7c_analysis_sha256: <64 hex>' of
    design/ms7/registration.md in the repository's working tree; a mismatch or a missing file is recorded, not hidden;
    the 16 confirmation weeks are recognized."""
    sha = hashlib.sha256(Path(ea.__file__).read_bytes()).hexdigest()
    assert ea.registration(sha, tmp_path) == {"path": e7c.REGISTRATION, "exists": False, "registered_sha256": None,
                                              "matches": False}
    f = tmp_path / e7c.REGISTRATION
    f.parent.mkdir(parents=True)
    f.write_text("# Registration\n\ne7c_analysis_sha256: " + "0" * 64 + "\n")
    r = ea.registration(sha, tmp_path)
    assert r["exists"] is True and r["registered_sha256"] == "0" * 64 and r["matches"] is False
    f.write_text("# Registration\n\ne7c_analysis_sha256: " + sha + "\n")
    assert ea.registration(sha, tmp_path)["matches"] is True
    lag = {}
    for x in ea.WEEKS_FULL:
        lag.update(_week_vals("Sublet-lag", x, 0.6))
    a = ea.analyse({"lag": _summ(lag), "inputs": {}}, repo=tmp_path)
    assert a["meta"]["registration"]["matches"] is True and a["meta"]["analysis_sha256"] == sha
    assert a["meta"]["weeks_are_confirmation_weeks"] is True and a["meta"]["n_weeks"] == 16
    assert ea.WEEKS_FULL == [str(c) for c in range(301, 317)]


def test_analysis_cli(tmp_path):
    root = tmp_path / "root"
    assert ea.main(["--root", str(root)]) == 2
    lag = _week_vals("Sublet-lag", "301", 0.6)
    mc.dump_json(_summ(lag), root / "out" / "e7c" / "lag" / "summary.json")
    assert ea.main(["--root", str(root)]) == 0
    a = json.loads((root / "out" / "e7c" / "analysis.json").read_text())
    assert a["meta"]["n_weeks"] == 1 and a["meta"]["inputs"]["main"]["sha256"] is None
    assert a["meta"]["analysis_sha256"] == hashlib.sha256(Path(ea.__file__).read_bytes()).hexdigest()
    assert (root / "out" / "e7c" / "analysis.md").is_file()


# ---------------------------------------------------------------- run_e7c.sh with a fake driver
FAKE_DRIVER = '''
import json, os, sys, time
from sublet.experiments import ms3_common as mc

def jobs():
    part = os.environ.get("E7C_PART", "")
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
        f.write(f"summary:{os.environ.get('E7C_PART')} {time.time()} {time.time()}\\n")
    mc.dump_json({"records": len(mc.read_records(out))}, out / "summary.json")

if __name__ == "__main__":
    if "--check-start" in sys.argv:
        ok = os.environ.get("FAKE_GATE", "1") == "1"
        print(f"[e7c] {os.environ.get('E7C_PART')}: gate {'ok' if ok else 'REFUSED'}")
        sys.exit(0 if ok else 1)
    if "--retry-list" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
        mark = os.path.join(out, "retried")
        if not os.path.exists(mark):
            open(mark, "w").close()
            for j in json.loads(os.environ.get("FAKE_RETRY", "[]")):
                print(f"pool {j}")
        sys.exit(0)
    sys.exit(mc.main("e7c", jobs=jobs, run=run, summary=summary))
'''
FAKE_JOBS = [["e7c:gate:k=week:tag=BL2:c=101", "pool", "gate", 0.3],
             ["e7c:gate:k=week:tag=A9-lag:c=101", "pool", "gate", 0.2],
             ["e7c:lag:k=week:tag=BL2-lag:c=101", "pool", "lag", 0.1]]


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
    (mod / "fake_e7c.py").write_text(FAKE_DRIVER)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "FAKE_", "E7C_"))}
    env.update(MS3_ROOT=str(root), MS3_WORKERS="2", MS3_POLL_S="0.2", MS3_PY=sys.executable, MS3_MODULE="fake_e7c",
               PYTHONPATH=os.pathsep.join([str(mod), str(SIM)]), FAKE_JOBS=json.dumps(FAKE_JOBS), E7C_PART=parts,
               FAKE_EVENTS=str(tmp_path / events), **_scope_env(), **extra)
    p = subprocess.run(["bash", str(RUN)], env=env, capture_output=True, text=True, timeout=300)
    ev: dict = {}
    f = tmp_path / events
    for line in (f.read_text().splitlines() if f.is_file() else []):
        jid, t0, t1 = line.split()
        ev.setdefault(jid, []).append((float(t0), float(t1)))
    return p, ev, root / "out"


def test_run_script_passes_retry_and_folders(tmp_path):
    p, ev, out = _run_fake(tmp_path, "gate lag", FAKE_RETRY=json.dumps(["e7c:gate:k=week:tag=BL2:c=101"]))
    assert p.returncode == 0, p.stdout + p.stderr
    assert len(ev["e7c:gate:k=week:tag=BL2:c=101"]) == 2 and len(ev["e7c:gate:k=week:tag=A9-lag:c=101"]) == 1
    assert ev["summary:gate"][0][1] <= ev["e7c:lag:k=week:tag=BL2-lag:c=101"][0][0] <= ev["summary:lag"][0][0]
    assert ev["e7c:gate:k=week:tag=BL2:c=101"][1][1] <= ev["summary:gate"][0][0]
    for part in ("gate", "lag"):
        d = out / "e7c" / part
        recs = mc.read_records(d)
        assert recs["e7c:summary"]["status"] == "ok" and recs["e7c:manifest"]["status"] == "ok", d
        log = (d / "run_e7c.log").read_text()
        assert log.rstrip().splitlines()[-1].startswith("[run_e7c] done ") and "gate ok" in log
    assert "rerun once (design/sublet_v2.md §4.5): 1 pool job(s)" in (out / "e7c" / "gate" / "run_e7c.log").read_text()


def test_run_script_refuses_and_filters(tmp_path):
    p, ev, out = _run_fake(tmp_path / "a", "lag", FAKE_GATE="0")
    assert p.returncode == 2 and ev == {}
    assert "refused: part lag does not start" in (out / "e7c" / "lag" / "run_e7c.log").read_text()
    p, ev, out = _run_fake(tmp_path / "b", "gate", E7C_ONLY="tag=A9-lag:")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == {"e7c:gate:k=week:tag=A9-lag:c=101", "summary:gate"}
    p, _, _ = _run_fake(tmp_path / "c", "", events="ev_c.txt")
    assert p.returncode == 2 and "E7C_PART must name" in p.stderr
    p, _, _ = _run_fake(tmp_path / "d", "main", events="ev_d.txt")
    assert p.returncode == 2 and "unknown part" in p.stderr


def test_run_script_parses():
    assert subprocess.run(["bash", "-n", str(RUN)]).returncode == 0
    assert os.access(RUN, os.X_OK)


# ---------------------------------------------------------------- needs_a12: reduced jobs through e7c's runner
@pytest.mark.needs_a12
def test_reduced_week_jobs_through_the_runner(tmp_path, monkeypatch):
    """Reduced BL2-lag (siloed runner) and BL4-lag week jobs (week 101, 2-hour horizon, the seven modes) through
    e7c.run: ok records, the run file's meta with E7c's gate (recorded, not enforced) and no confirmation gate, the
    lag in every borrower sub-run's resolved parameters, BL4's 'previous0' in its report, r0 = ALG / BL0a, and the
    summary's table, W0 and RC."""
    monkeypatch.setenv(e7c.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_ROOT", str(tmp_path))
    monkeypatch.setattr(e7c, "_GATE", {})
    out = tmp_path / "out" / "e7c" / "lag"
    js = {j.id: j for j in e7c.jobs(["lag"])}
    ids = ("e7c:lag:k=week:tag=BL2-lag:c=101", "e7c:lag:k=week:tag=BL4-lag:c=101")
    for jid in ids:
        rec = mc.run_job("e7c", js[jid], lambda o, j=js[jid]: e7c.run(j, o, out), out, resume=False)
        assert rec["status"] == "ok" and rec["n_errors"] == 0, rec.get("error")
    f = json.loads(e7h.run_path(out, ids[0]).read_text())
    g = f["meta"]["gate"]
    assert f["meta"]["exp"] == "e7c" and g["kind"] == "ms7_registration" and g["enforced"] is False
    assert "confirmation" not in g and "pilot" not in g
    assert f["horizon_min"] == 120 and [r["mode"] for r in f["runs"]] == list(m5.conf_modes())
    assert f["params"]["base"] == {"demand_lag": 1} and f["tags"]["BL2-lag"]["revealed"] == "BL2"
    for r in f["runs"]:
        assert r["status"] == "ok" and r["r0"] == pytest.approx(r["ALG"] / r["bl0a_usd"], rel=1e-12)
        assert r["params"] == {"demand_lag": 1} and r["runner"] == "siloed" and len(r["sub_runs"]) > 1
    h = json.loads(e7h.run_path(out, ids[1]).read_text())
    for r in h["runs"]:
        assert r["params"] == {"demand": "previous0"} and r["status"] == "ok"
    s = e7c.summary_part("lag", out)
    assert set(s["table"]["BL2-lag"]) == set(m5.conf_modes()) and s["meta"]["gate"]["kind"] == "ms7_registration"
    assert "confirmation_gate" not in s["meta"] and s["meta"]["reduced"] is True
    assert "BL2-lag" in s["W0"]["0"] and "L-tr" in s["RC"]["BL2-lag"]
    assert (out / "tables.md").is_file()
