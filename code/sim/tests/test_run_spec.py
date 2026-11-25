"""Tests of the run spec, the policy registry and the drivers (design/sim_spec_ms2.md §3.7, §4; §17.2)."""
import copy
import json

import numpy as np
import pytest

from fixtures import CONFIGS, DELETE, load_json, toy_config

from sublet.algos import registry
from sublet.config import ConfigError, config_hash
from sublet.drivers import run as drun
from sublet.drivers.siloed import borrower_partition, run_siloed
from sublet.engine import simulate
from sublet.instance import build_instance, units
from sublet.policies import AlwaysFallback, FixedPlan
from sublet.policies.base import Policy
from sublet.types import PlannedLease

# §4.2: id -> (runner, information class at the default parameters)
TABLE = {"A1": ("simulate", "online-I1"), "A2": ("simulate", "online-I1"), "A3": ("simulate", "online-I1"),
         "A4": ("simulate", "online-I2"), "A5": ("simulate", "online-I1 + prediction"),
         "A6": ("simulate", "online-I1"), "RR_RENEW": ("simulate", "online-I1"),
         "MARKING": ("simulate", "online-I2"), "BL0a": ("simulate", "online-I1"),
         "BL0b": ("analytic", "hindsight-reference"), "BL1": ("simulate", "online-I1"),
         "BL2": ("siloed", "online-I1"), "BL3": ("simulate", "online-I1"), "BL4": ("simulate", "online-I1"),
         "BL5": ("simulate", "online-I1"), "BL6": ("simulate", "online-I1"), "BL7": ("simulate", "online-I1"),
         "BL8": ("bench", "offline"), "SILOED": ("siloed", None),
         "A7": ("simulate", "online-I1"), "A8": ("simulate", "online-I1 + a-priori N")}
CLASS_IDS = ("A1", "A2", "A3", "A4", "A5", "A6", "RR_RENEW", "MARKING", "BL0a", "BL1", "BL2", "BL3", "BL4", "BL5",
             "BL6", "BL7")
TOY_PLAN = [{"site": 0, "contract": 1, "llm": 0, "start_slot": 1}, [1, 0, 0, 2, 9, 1, []]]


def _spec(**kw) -> dict:
    s = {"schema_version": 1, "name": "t_toy", "instance": "toy.json", "policy": {"id": "BL0a"}}
    s.update(kw)
    return s


def _toy_r_rate() -> dict:
    """toy.json with L0's R drawn from R_rate (so the config seed changes it), as an inline config."""
    return toy_config({"lenders.0.R": DELETE, "lenders.0.R_rate": 0.3})


def _series_instance() -> dict:
    cfg = load_json(CONFIGS / "example_1day.json")
    cfg["borrowers"] = {"model": "series", "list": [
        {"id": "bA", "series": "azure2024_conv", "region": "north_america", "slo_class": "strict"},
        {"id": "bB", "series": "azure2024_code", "region": "north_america", "slo_class": "strict"}]}
    return cfg


def _same_ledger(a, b) -> bool:
    return (a.components == b.components and all(np.array_equal(a.per_slot[k], b.per_slot[k]) for k in a.per_slot)
            and [vars(x) for x in a.leases] == [vars(x) for x in b.leases]
            and [vars(x) for x in a.replicas] == [vars(x) for x in b.replicas]
            and all(np.array_equal(x, y) for x, y in zip(a.schedule.R, b.schedule.R)))


# ---------------------------------------------------------------- validation
BAD_SPECS = {
    "unknown top key": _spec(policies={"id": "BL0a"}),
    "schema_version missing": {k: v for k, v in _spec().items() if k != "schema_version"},
    "schema_version 2": _spec(schema_version=2),
    "name with a slash": _spec(name="a/b"),
    "instance missing": {k: v for k, v in _spec().items() if k != "instance"},
    "instance file missing": _spec(instance="no_such_config.json"),
    "overrides not an object": _spec(overrides=[["time.horizon_min", 60]]),
    "lender_model unknown key": _spec(lender_model={"merge_identical_layers": True}),
    "lender_model bad schedule": _spec(lender_model={"schedule": "random"}),
    "lender_model bad information": _spec(lender_model={"information": "I3"}),
    "engine unknown key": _spec(engine={"fast": True}),
    "engine bad value": _spec(engine={"check_invariants": "yes"}),
    "policy without id": _spec(policy={"params": {}}),
    "policy unknown key": _spec(policy={"id": "BL0a", "params": {}, "seed": 1}),
    "unknown policy id": _spec(policy={"id": "A99"}),
    "BL8 as a policy id": _spec(policy={"id": "BL8"}),
    "unknown parameter": _spec(policy={"id": "BL0a", "params": {"rbar": 1}}),
    "SILOED without inner": _spec(policy={"id": "SILOED", "params": {}}),
    "SILOED unknown parameter": _spec(policy={"id": "SILOED", "params": {"inner": "BL0a", "x": 1}}),
    "SILOED inner unknown parameter": _spec(policy={"id": "SILOED", "params": {"inner": "BL0a",
                                                                               "inner_params": {"x": 1}}}),
    "SILOED around SILOED": _spec(policy={"id": "SILOED", "params": {"inner": "SILOED"}}),
    "SILOED around BL0b": _spec(policy={"id": "SILOED", "params": {"inner": "BL0b"}}),
    "FIXED_PLAN unknown parameter": _spec(policy={"id": "FIXED_PLAN", "params": {"plan": [], "n": 1}}),
    "seeds unknown key": _spec(seeds={"config": [1], "bench": [0]}),
    "seeds negative": _spec(seeds={"config": [-1]}),
    "seeds bool": _spec(seeds={"policy": [True]}),
    "seeds empty list": _spec(seeds={"config": []}),
    "lender seeds not paired": _spec(seeds={"config": [1, 2], "lender": [5]}),
    "bench unknown kind": _spec(bench={"kind": "opt"}),
    "bench unknown key": _spec(bench={"kind": "omega", "solver": "highs"}),
    "bench bad grid": _spec(bench={"kind": "omega", "grid": "hourly"}),
    "bench for an analytic id": _spec(policy={"id": "BL0b"}, bench={"kind": "eager"}),
    "SILOED on merged series": _spec(instance=_series_instance(), policy={"id": "SILOED", "params": {"inner": "BL0a"}}),
    "out empty": _spec(out=""),
    # §4.1 strictness: falsy non-objects are not read as {} (null is: the field's default)
    "policy params a list": _spec(policy={"id": "BL0a", "params": []}),
    "policy params 0": _spec(policy={"id": "BL0a", "params": 0}),
    "overrides empty list": _spec(overrides=[]),
    "engine empty list": _spec(engine=[]),
    "lender_model empty list": _spec(lender_model=[]),
    "seeds empty list object": _spec(seeds=[]),
    "seeds duplicate policy seeds": _spec(seeds={"policy": [0, 0]}),
    "seeds duplicate config seeds": _spec(seeds={"config": [7, 7]}),
    "bench merged for omega": _spec(policy={"id": "BL1"}, bench={"kind": "omega", "merged": True}),
    # §15.1: every baseline runs with auto_drain false
    "baseline with auto_drain": _spec(policy={"id": "BL1"}, engine={"auto_drain": True}),
    "BL6 with auto_drain": _spec(policy={"id": "BL6", "params": {"inner": "A2"}}, engine={"auto_drain": True}),
    "SILOED baseline with auto_drain": _spec(policy={"id": "SILOED", "params": {"inner": "BL1"}},
                                             engine={"auto_drain": True}),
    "baseline with auto_drain in the instance": _spec(instance=toy_config({"engine": {"auto_drain": True}}),
                                                      policy={"id": "BL3"}),
}


@pytest.mark.parametrize("case", list(BAD_SPECS))
def test_validation(case):
    """§4.1: unknown keys, unknown parameters (also of the inner policy) and bad values raise ConfigError;
    BL8 is not a policy id; SILOED (and BL2) on a series-model instance need borrowers.merge false."""
    with pytest.raises(ConfigError):
        drun.load_run_spec(copy.deepcopy(BAD_SPECS[case]))


def test_validation_accepts_and_resolves(tmp_path):
    """Valid specs resolve with every default filled (idempotent), from a file or a dict; merge false in
    the overrides or the inline instance config admits SILOED on a series instance; make_policy raises
    ConfigError for SILOED, BL0b and BL8, which have no policy class."""
    s = drun.load_run_spec(_spec())
    assert s["seeds"] == {"config": [7], "lender": "config", "policy": "config"}
    assert s["overrides"] == {} and s["lender_model"] == {} and s["engine"] == {} and s["bench"] is None
    assert s["policy"] == {"id": "BL0a", "params": {}} and s["out"] == "code/sim/out/t_toy"
    assert drun.load_run_spec(s) == s
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(_spec(name="from_file")))
    assert drun.load_run_spec(p)["name"] == "from_file"
    ser = _series_instance()
    sil = {"id": "SILOED", "params": {"inner": "BL0a"}}
    drun.load_run_spec(_spec(instance=ser, policy=sil, overrides={"borrowers.merge": False}))
    ser2 = copy.deepcopy(ser)
    ser2["borrowers"]["merge"] = False
    drun.load_run_spec(_spec(instance=ser2, policy=sil))
    drun.load_run_spec(_spec(policy={"id": "FIXED_PLAN", "params": {"plan": TOY_PLAN}}))
    inst = build_instance(CONFIGS / "toy.json")
    for pid, par in (("SILOED", {"inner": "BL0a"}), ("BL0b", {}), ("BL8", {})):
        with pytest.raises(ConfigError):
            drun.make_policy({"policy": {"id": pid, "params": par}}, inst)
    fp = drun.make_policy({"policy": {"id": "FIXED_PLAN", "params": {"plan": TOY_PLAN}}}, inst)
    assert isinstance(fp, FixedPlan) and fp.plan == [PlannedLease(0, 1, 0, 1), PlannedLease(1, 0, 0, 2, 9, 1)]


# ---------------------------------------------------------------- seeds, files and meta
def test_seed_loops(tmp_path):
    """§4.1, §4.3: runs = config seeds x policy seeds, lender seeds paired with config seeds; each run equals
    simulate(build(spec, c), policy, model, cfg, lender_seed=l, policy_seed=p); 'config' means the config
    seed; one file <name>_c<c>_l<l>_p<p>.json per run."""
    spec = _spec(name="loops", instance=_toy_r_rate(),
                 lender_model={"schedule": "iid_step", "params": {"D_slots": 2, "p": 0.5}},
                 policy={"id": "FIXED_PLAN", "params": {"plan": TOY_PLAN}},
                 seeds={"config": [7, 8], "lender": [3, 4], "policy": [0, 1]})
    res = drun.run(spec, out_dir=tmp_path / "a")
    want = [(7, 3, 0), (7, 3, 1), (8, 4, 0), (8, 4, 1)]
    assert [(r.seeds["config"], r.seeds["lender"], r.seeds["policy"]) for r in res] == want
    names = sorted(p.name for p in (tmp_path / "a").glob("*.json"))
    assert names == sorted(f"loops_c{c}_l{l}_p{p}.json" for c, l, p in want)
    plan = [PlannedLease(0, 1, 0, 1), PlannedLease(1, 0, 0, 2, 9, 1)]
    rs = drun.load_run_spec(spec)
    for r, (c, l, p) in zip(res, want):
        inst, model, ecfg = drun.build(rs, c)
        assert inst.seed == c and model.schedule == "iid_step"
        ref = simulate(inst, FixedPlan(plan), model, ecfg, lender_seed=l, policy_seed=p)
        assert _same_ledger(r, ref), (c, l, p)
    assert any(not np.array_equal(a, b) for a, b in zip(res[0].schedule.R, res[2].schedule.R))
    cfg_runs = drun.run(_spec(name="cfgseed", instance=_toy_r_rate(), seeds={"config": [7, 9]}),
                        out_dir=tmp_path / "b")
    assert [r.seeds for r in cfg_runs] == [{"config": 7, "lender": 7, "policy": 7},
                                           {"config": 9, "lender": 9, "policy": 9}]
    i7, _, _ = drun.build(drun.load_run_spec(_spec(instance=_toy_r_rate())), 7)
    i9, _, _ = drun.build(drun.load_run_spec(_spec(instance=_toy_r_rate())), 9)
    assert not np.array_equal(i7.sites[0].R_explicit, i9.sites[0].R_explicit)
    assert sorted(p.name for p in (tmp_path / "b").glob("*.json")) == ["cfgseed_c7_l7_p7.json",
                                                                         "cfgseed_c9_l9_p9.json"]


def test_extra_meta(tmp_path):
    """§4.1, C6: each run file's meta holds run_spec_hash (config_hash of the resolved spec), policy_id,
    params, seeds and info_class next to MS1's meta; the overrides and the engine section reach the run."""
    spec = _spec(name="meta", overrides={"time.horizon_min": 60, "borrowers.clients.0.demand.values": [1] * 12,
                                         "lenders.0.R": [6, 7, 8]},
                 engine={"check_invariants": True}, seeds={"config": [7], "policy": [2]})
    res = drun.run(spec, out_dir=tmp_path)
    assert len(res) == 1 and res[0].per_slot["total"].shape == (12,)
    js = json.loads((tmp_path / "meta_c7_l7_p2.json").read_text())
    meta = js["meta"]
    assert meta["run_spec_hash"] == config_hash(drun.load_run_spec(spec))
    assert meta["policy_id"] == "BL0a" and meta["params"] == {} and meta["info_class"] == "online-I1"
    assert meta["seeds"] == {"config": 7, "lender": 7, "policy": 2}
    inst = drun.build(drun.load_run_spec(spec), 7)[0]
    assert meta["config_hash"] == config_hash(inst.config) and meta["name"] == inst.name
    ref = simulate(inst, AlwaysFallback(), policy_seed=2)
    assert js["components"] == ref.components


# ---------------------------------------------------------------- determinism
def _no_times(x):
    """A policy report without its wall-time entries (keys containing 'time' or ending in '_s'), as JSON."""
    def strip(v):
        if isinstance(v, dict):
            return {k: strip(w) for k, w in v.items() if "time" not in str(k) and not str(k).endswith("_s")}
        if isinstance(v, (list, tuple)):
            return [strip(w) for w in v]
        return v
    return json.dumps(strip(x), sort_keys=True, default=str)


DET_CASES = {
    "FIXED_PLAN": ("toy.json", {"id": "FIXED_PLAN", "params": {"plan": TOY_PLAN}}, {}),
    "A2": ("ms2_multi_small.json", {"id": "A2", "params": {}}, {}),
    "A3": ("ms2_multi_small.json", {"id": "A3", "params": {}}, {}),
    "A6": ("ms2_multi_small.json", {"id": "A6", "params": {}}, {}),
    "A6_I2": ("ms2_multi_small.json", {"id": "A6", "params": {}}, {"information": "I2"}),
    "BL3": ("ms2_multi_small.json", {"id": "BL3", "params": {}}, {}),
    "BL4": ("ms2_multi_small.json", {"id": "BL4", "params": {}}, {}),
}


@pytest.mark.parametrize("case", list(DET_CASES))
def test_determinism(case, tmp_path):
    """§2.3: the same run spec and seeds give identical ledgers (components, per-slot components, leases,
    replicas, realized schedule) and the same policy report."""
    inst_file, pol, lm = DET_CASES[case]
    spec = _spec(name=f"det_{case}", instance=inst_file, policy=pol, lender_model=lm,
                 overrides={"time.horizon_min": 360} if inst_file != "toy.json" else {},
                 seeds={"config": [3], "policy": [0, 1]})
    a = drun.run(spec, out_dir=tmp_path / "a")
    b = drun.run(spec, out_dir=tmp_path / "b")
    assert len(a) == len(b) == 2
    for x, y in zip(a, b):
        assert x.invariant_failures == [] and _same_ledger(x, y)
        assert _no_times(x.metrics["policy"]) == _no_times(y.metrics["policy"])
    fa = sorted((tmp_path / "a").glob("*.json"))
    fb = sorted((tmp_path / "b").glob("*.json"))
    assert [p.name for p in fa] == [p.name for p in fb]
    for p, q in zip(fa, fb):
        ja, jb = json.loads(p.read_text()), json.loads(q.read_text())
        assert ja["components"] == jb["components"] and ja["meta"]["run_spec_hash"] == jb["meta"]["run_spec_hash"]


# ---------------------------------------------------------------- registry
def test_registry_complete(tmp_path):
    """§4.2: the registry holds exactly the ids of the table with their runners and information classes,
    every id resolves (classes with PARAMS for the class-backed ids, functions for BL0b, BL8, SILOED);
    make_policy builds BL2 and SILOED's inner policy; run_siloed passes each borrower's sub-instance to the
    factory, and an A2 inner with rbar = 'theory' gets the N_bound of its sub-instance (M6)."""
    assert set(registry.POLICY_IDS) == set(TABLE)
    for pid, (runner, info) in TABLE.items():
        e = registry.entry(pid)
        assert e.runner == runner, pid
        if info is not None and pid not in ("BL6", "BL7"):
            assert registry.info_class(pid, {}) == info, pid
    for pid in TABLE:
        obj = registry.resolve(pid)
        if pid in CLASS_IDS:
            assert isinstance(obj, type) and issubclass(obj, Policy), pid
            assert isinstance(getattr(obj, "PARAMS", None), dict), pid
        else:
            assert callable(obj), pid
    assert registry.info_class("A2", {"rbar": "theory"}) == "online-I1 + a-priori N"
    assert registry.info_class("A6", {}, "I2") == "online-I2"
    assert registry.info_class("BL4", {"demand": "oracle"}) == "lookahead-60min"
    assert registry.info_class("BL7", {"inner": "A2"}) == "online-I1"
    ms = drun.load_run_spec(_spec(instance="ms2_multi_small.json", overrides={"time.horizon_min": 120}))
    inst, model, ecfg = drun.build(ms, 3)
    bl2 = drun.make_policy({"policy": {"id": "BL2", "params": {}}}, inst)
    assert isinstance(bl2, registry.resolve("BL2"))
    inner = {"id": "A2", "params": {"rbar": "theory"}}
    a2 = drun.make_policy({"policy": inner}, inst)
    assert isinstance(a2, registry.resolve("A2"))
    parts = borrower_partition(inst)
    assert [b for b, _ in parts] == ["b0", "b1", "b2", "b3"] and [c for _, c in parts] == [[0], [1], [2], [3]]
    seen = []

    def factory(sub):
        seen.append(sub)
        return drun.make_policy({"policy": inner}, sub)

    d = run_siloed(inst, factory, model, ecfg, policy_seed=0)
    assert len(seen) == 4 and d["borrowers"] == ["b0", "b1", "b2", "b3"] and d["invariant_failures"] == []
    T = inst.grid.T_slow
    for sub, res, (_, idx) in zip(seen, d["results"], parts):
        assert sub.n == 1 and np.array_equal(sub.clients.demand, inst.clients.demand[idx])
        want = max(len(units(sub).client) * T, 3)
        assert res.metrics["policy"]["N_bound"] == want
    assert len({r.metrics["policy"]["N_bound"] for r in d["results"]}) > 1
    assert max(r.metrics["policy"]["N_bound"] for r in d["results"]) < max(len(units(inst).client) * T, 3)
    for k in d["components"]:
        assert abs(d["components"][k] - sum(r.components[k] for r in d["results"])) <= 1e-9
    out = drun.run(_spec(name="sil", instance="ms2_multi_small.json", overrides={"time.horizon_min": 120},
                         policy={"id": "SILOED", "params": {"inner": "A2", "inner_params": {"rbar": "theory"}}},
                         seeds={"config": [3], "policy": [0]}),
                   out_dir=tmp_path)
    assert len(out) == 1 and [r.metrics["policy"]["N_bound"] for r in out[0]["results"]] == \
           [r.metrics["policy"]["N_bound"] for r in d["results"]]



def test_validation_null_fields_and_drain():
    """§4.1: a null overrides, lender_model, engine, seeds or policy.params reads as the default {}; a
    non-baseline policy may run with auto_drain (§15.1 restricts the baselines only)."""
    s = drun.load_run_spec(_spec(overrides=None, lender_model=None, engine=None, seeds=None,
                                 policy={"id": "BL0a", "params": None}))
    assert s["overrides"] == {} and s["lender_model"] == {} and s["engine"] == {}
    assert s["policy"]["params"] == {} and s["seeds"]["config"] == [7]
    s = drun.load_run_spec(_spec(policy={"id": "A2"}, engine={"auto_drain": True}))
    assert s["engine"] == {"auto_drain": True}
    drun.load_run_spec(_spec(policy={"id": "BL1"}, engine={"auto_drain": False}))
    drun.load_run_spec(_spec(policy={"id": "BL1"}, bench={"kind": "lp", "merged": True}))


def test_engine_and_lender_merge():
    """§4.1: the engine section merges key by key with the run spec's value winning; a run spec that changes
    the schedule without 'params' starts from the new schedule's default parameters."""
    cfg = toy_config()
    cfg["engine"] = {"check_invariants": False, "record_routing": True}
    spec = drun.load_run_spec(_spec(instance=cfg, engine={"check_invariants": True}))
    _, _, ecfg = drun.build(spec, 7)
    assert ecfg.check_invariants is True and ecfg.record_routing is True
    cfg2 = toy_config()
    cfg2["lender_model"] = {"schedule": "iid_step", "params": {"D_slots": 2, "p": 0.5}}
    _, model, _ = drun.build(drun.load_run_spec(_spec(instance=cfg2, lender_model={"schedule": "trace"})), 7)
    assert model.schedule == "trace"
    _, model2, _ = drun.build(drun.load_run_spec(_spec(instance=cfg2)), 7)
    assert model2.schedule == "iid_step"


def test_wrapper_inner_driver_inputs():
    """§4.2: for BL6 and BL7 the inner's driver inputs go into inner_params: BL7 around A2 with
    rbar='theory' gets N_bound = max(len(units(inst).client) T_slow, 3)."""
    inst = build_instance(CONFIGS / "toy.json")
    pol = drun.make_policy({"policy": {"id": "BL7", "params": {"inner": "A2", "inner_params": {"rbar": "theory"}}}},
                           inst)
    res = simulate(inst, pol, policy_seed=0)
    assert res.invariant_failures == []
    rep = res.metrics["policy"]
    assert rep["inner"]["N_bound"] == max(len(units(inst).client) * inst.grid.T_slow, 3)
    pol6 = drun.make_policy({"policy": {"id": "BL6", "params": {"inner": "A2", "inner_params": {"rbar": "theory"}}}},
                            inst)
    assert pol6.inner.N_bound == max(len(units(inst).client) * inst.grid.T_slow, 3)


def _toy_fast():
    """toy.json with 1-min routing (Δf = 1 < Δs = 5) and its bench section on the fast grid."""
    cfg = toy_config()
    cfg["time"]["fast_slot_min"] = 1
    cfg["borrowers"]["clients"][0]["demand"]["values"] = [float(v) for v in
                                                          np.repeat(cfg["borrowers"]["clients"][0]["demand"]["values"], 5)]
    cfg["bench"] = {"grid": "fast", "time_limit_s": 60, "mip_rel_gap": 1e-9}
    return cfg


def test_bench_fields_and_ratio(tmp_path):
    """§4.1, §15.10: a run spec's bench keys go on top of the instance config's MS1 bench section (grid 'fast'
    here); the ratio is written only for a benchmark on the run's grid with violations absorbed (the LP on the
    fast grid bounds the run: vs_bound >= 1), else None with a note (grid 'slow' with Δf < Δs, violations
    'reclaim'); a benchmark that cannot be solved (the DP's domain) is recorded and the run file written."""
    cfg = _toy_fast()
    spec = _spec(name="bf", instance=cfg, policy={"id": "BL1"}, seeds={"config": [7], "policy": [0]},
                 bench={"kind": "lp"})
    res = drun.run(spec, out_dir=tmp_path / "a")
    b = res[0].metrics["bench"]
    assert b["fields"]["grid"] == "fast" and b["grid"] == "fast" and b["ratio_note"] is None, b
    assert b["ratio"]["vs_bound"] >= 1 - 1e-9, b
    js = json.loads((tmp_path / "a" / "bf_c7_l7_p0.json").read_text())
    assert js["meta"]["bench"]["ratio"]["vs_bound"] == b["ratio"]["vs_bound"]
    res = drun.run({**spec, "bench": {"kind": "lp", "grid": "slow"}}, out_dir=tmp_path / "b")
    b = res[0].metrics["bench"]
    assert b["grid"] == "slow" and b["ratio"] is None and "slow" in b["ratio_note"] and b["objective"] is not None
    res = drun.run({**spec, "lender_model": {"violations": "reclaim"}}, out_dir=tmp_path / "c")
    b = res[0].metrics["bench"]
    assert b["ratio"] is None and "violations" in b["ratio_note"], b
    res = drun.run({**spec, "bench": {"kind": "dp"}}, out_dir=tmp_path / "d")
    b = res[0].metrics["bench"]
    assert b["objective"] is None and b["ratio"] is None and b["status_msg"].startswith("not solved"), b
    assert (tmp_path / "d" / "bf_c7_l7_p0.json").is_file()
    # the instance's own grid when the run spec gives no grid (toy.json: 'slow' with Δf = Δs)
    res = drun.run(_spec(name="bs", policy={"id": "BL1"}, seeds={"config": [7], "policy": [0]},
                         bench={"kind": "lp"}), out_dir=tmp_path / "e")
    b = res[0].metrics["bench"]
    assert b["grid"] == "slow" and b["ratio_note"] is None and b["ratio"]["vs_bound"] >= 1 - 1e-9


def test_siloed_and_analytic_files(tmp_path):
    """§4.1: runner 'siloed' writes one run file per borrower (suffix _b<i>) with policy_id, info_class,
    inner_id, borrower and clients in its meta, and <tag>_sum.json whose components are the per-borrower
    sums; BL2 likewise (inner_id BL2)."""
    ov = {"time.horizon_min": 120}
    for pid, params, inner in (("SILOED", {"inner": "A2"}, "A2"), ("BL2", {}, "BL2")):
        spec = _spec(name=f"sf_{pid}", instance="ms2_multi_small.json", overrides=ov,
                     policy={"id": pid, "params": params}, seeds={"config": [3], "policy": [0]})
        out = tmp_path / pid
        drun.run(spec, out_dir=out)
        tag = f"sf_{pid}_c3_l3_p0"
        files = sorted(out.glob(f"{tag}_b*.json"))
        assert len(files) == 4, files
        sums: dict = {}
        for i, f in enumerate(sorted(files, key=lambda x: int(x.stem.rsplit("_b", 1)[1]))):
            js = json.loads(f.read_text())
            m = js["meta"]
            assert m["policy_id"] == pid and m["inner_id"] == inner and m["borrower"] == f"b{i}", m
            assert m["clients"] == [i] and m["info_class"] == "online-I1" and m["runner"] == "siloed", m
            for k, v in js["components"].items():
                sums[k] = sums.get(k, 0.0) + v
        sm = json.loads((out / f"{tag}_sum.json").read_text())
        assert sm["meta"]["policy_id"] == pid and sm["meta"]["inner_id"] == inner
        assert sm["meta"]["borrowers"] == ["b0", "b1", "b2", "b3"]
        assert set(sm["components"]) == set(sums)
        for k, v in sums.items():
            assert abs(sm["components"][k] - v) <= 1e-9 * max(1.0, abs(v)), (pid, k)


@pytest.mark.needs_a12
def test_analytic_file(tmp_path):
    """§4.1, §15.2: BL0b (runner 'analytic') writes <name>_c<c>.json with bl0b_usd and own_capacity_usd of
    drivers.provision on the run's instance and the information class 'hindsight-reference'."""
    from sublet.drivers.provision import bl0b_usd, own_capacity_usd
    spec = _spec(name="an", instance="example_1day.json", policy={"id": "BL0b"}, seeds={"config": [1]})
    drun.run(spec, out_dir=tmp_path)
    js = json.loads((tmp_path / "an_c1.json").read_text())
    inst = drun.build(drun.load_run_spec(spec), 1)[0]
    assert js["policy_id"] == "BL0b" and js["info_class"] == "hindsight-reference"
    assert abs(js["bl0b_usd"] - bl0b_usd(inst)) <= 1e-9 * bl0b_usd(inst)
    assert abs(js["own_capacity_usd"] - own_capacity_usd(inst)) <= 1e-9 * max(1.0, own_capacity_usd(inst))
    assert js["seeds"] == {"config": 1} and js["config_hash"] == config_hash(inst.config)
