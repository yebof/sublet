"""Run specs, policy construction and seed loops (design/sim_spec_ms2.md §4).

A run spec (§4.1) names an instance config, overrides, the lender model and engine options, a
policy id of the registry (§4.2) with its parameters, the seeds and an optional BL8 benchmark.
`load_run_spec` validates it as strictly as `load_config` and fills the defaults; `build` makes
the instance, lender model and engine config of one config seed; `make_policy` builds the policy
of a class-backed id with the driver inputs computed from the instance; `run` loops over the
seeds, dispatches on the registry runner and writes the run files.

Seeds (§4.3): runs = config seeds x policy seeds, lender seeds paired with config seeds;
'config' means "the config seed", which reproduces MS1's simulate(inst, policy, model, cfg).
Policy modules are imported only when a run needs them (registry.resolve), never at import.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Optional, Union

import numpy as np

from .. import config as C
from ..algos import registry
from ..algos.common import PolicyError
from ..engine import EngineConfig, engine_config, simulate
from ..instance import build_instance, units
from ..metrics import _jsonable, ratio, write_run
from ..paths import REPO
from ..policies.base import Policy
from ..types import Instance, LenderModel, PlannedLease
from .siloed import run_siloed

ConfigError = C.ConfigError

SCHEMA_VERSION = 1
RUN_KEYS = ("schema_version", "name", "instance", "overrides", "lender_model", "engine", "policy", "seeds",
            "bench", "out")
LENDER_MODEL_KEYS = ("schedule", "information", "on_unavailable", "violations", "params")
BENCH_KINDS = ("omega", "eager", "lp", "dp", "fam")
BENCH_KEYS = ("kind", "grid", "time_limit_s", "mip_rel_gap", "max_vars", "merged")
BASELINE_IDS = ("BL0a", "BL1", "BL2", "BL3", "BL4", "BL5", "BL6", "BL7",   # §15.1: auto_drain is off for them
                "MPC")                                                     # MS7 C54 (baselines/mpc.py)
MS1_BENCH_FIELDS = ("grid", "time_limit_s", "mip_rel_gap", "max_vars")
N_BOUND_SOURCE = "units(inst) x T_slow (a-priori)"
PRED_LABEL = "previous-day"
_NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")


# ---------------------------------------------------------------- helpers
def _fail(path: str, msg: str):
    raise ConfigError(f"run spec {path}: {msg}" if path else f"run spec: {msg}")


def _read(src) -> dict:
    if isinstance(src, dict):
        return copy.deepcopy(src)
    if not isinstance(src, (str, Path)):
        _fail("", f"expected a path or a dict, got {type(src).__name__}")
    p = Path(src)
    try:
        with open(p) as f:
            out = json.load(f)
    except FileNotFoundError:
        raise ConfigError(f"run spec file {src} not found") from None
    except json.JSONDecodeError as e:
        raise ConfigError(f"run spec file {p} is not valid JSON: {e}") from None
    if not isinstance(out, dict):
        _fail("", f"file {p} does not hold a JSON object")
    return out


def set_path(cfg: dict, path: str, value) -> None:
    """cfg[a][b]...[z] = value for the dotted path 'a.b....z' (integer parts index lists; missing
    dict levels are created), as tests/fixtures.py::set_path."""
    keys = path.split(".")
    cur = cfg
    for k in keys[:-1]:
        if isinstance(cur, list):
            try:
                cur = cur[int(k)]
            except (ValueError, IndexError):
                _fail(f"overrides.{path}", f"no list element {k!r}")
        elif isinstance(cur, dict):
            cur = cur.setdefault(k, {})
        else:
            _fail(f"overrides.{path}", f"{k!r} is below a value that is neither an object nor a list")
    last = keys[-1]
    if isinstance(cur, list):
        try:
            cur[int(last)] = value
        except (ValueError, IndexError):
            _fail(f"overrides.{path}", f"no list element {last!r}")
    elif isinstance(cur, dict):
        cur[last] = value
    else:
        _fail(f"overrides.{path}", "the parent is neither an object nor a list")


def instance_config(spec: dict) -> dict:
    """The raw instance config of a run spec (file or inline object) with its overrides applied, before
    load_config (so before the seed's draws)."""
    src = spec["instance"]
    cfg = C._read(src) if isinstance(src, (str, Path)) else copy.deepcopy(src)
    for path, value in (spec.get("overrides") or {}).items():
        set_path(cfg, path, copy.deepcopy(value))
    return cfg


def _int_list(v, path: str, what: str, unique: bool = False) -> list[int]:
    if not isinstance(v, list) or not v:
        _fail(path, f"expected 'config' or a non-empty list of {what}")
    out = []
    for x in v:
        if isinstance(x, bool) or not isinstance(x, (int, np.integer)) or x < 0:
            _fail(path, f"expected integers >= 0, got {x!r}")
        out.append(int(x))
    if unique and len(set(out)) != len(out):
        _fail(path, f"duplicate {what} {sorted({x for x in out if out.count(x) > 1})} (their runs would share a file)")
    return out


def _object(raw: dict, key: str, path: Optional[str] = None) -> dict:
    """raw[key] as an object: {} if the key is missing or null; ConfigError for any other non-object
    (a falsy list, 0 or '' is not read as {})."""
    v = raw.get(key)
    if v is None:
        return {}
    if not isinstance(v, dict):
        _fail(path or key, f"expected an object, got {type(v).__name__}")
    return v


def _check_params(pid: str, params, path: str, inner_of: Optional[str] = None) -> None:
    """Parameter keys of `pid` against its PARAMS (or the registry's list), recursively for the inner
    id of BL6, BL7, SILOED, A8 (whose inner id must be one of registry.A8_INNER_IDS) and A8P (one of
    registry.A8P_INNER_IDS; design/sublet_v2.md §8.1 C35)."""
    if not isinstance(params, dict):
        _fail(path, f"expected an object, got {type(params).__name__}")
    try:
        e = registry.entry(pid)
    except (KeyError, TypeError) as err:
        _fail(path, f"unknown policy id {pid!r} ({err})")
    if inner_of is not None:
        if inner_of in registry.WRAPPERS and pid not in registry.INNER_IDS:
            _fail(path, f"{inner_of} wraps one of {list(registry.INNER_IDS)}, not {pid!r}")
        if inner_of == "A8" and pid not in registry.A8_INNER_IDS:
            _fail(path, f"A8 guards one of {list(registry.A8_INNER_IDS)}, not {pid!r}")
        if inner_of == "A8P" and pid not in registry.A8P_INNER_IDS:
            _fail(path, f"A8P guards one of {list(registry.A8P_INNER_IDS)}, not {pid!r}")
        if e.runner != "simulate" or not e.policy_class or pid in registry.WRAPPERS:
            _fail(path, f"{pid!r} cannot be the inner policy of {inner_of}")
    try:
        names = registry.param_names(pid)
    except ImportError as err:
        raise ConfigError(f"run spec {path}: the policy module of {pid} is not available ({err})") from None
    unknown = sorted(set(params) - set(names or ()))
    if unknown:
        _fail(path, f"unknown parameter(s) {unknown} of {pid}; allowed {sorted(names or ())}")
    inner = registry.inner_of(pid, params)
    if inner is not None:
        if inner[0] is None:
            _fail(path, f"{pid} needs the parameter 'inner'")
        _check_params(inner[0], inner[1], f"{path}.inner_params", inner_of=pid)


# ---------------------------------------------------------------- run spec
def load_run_spec(src) -> dict:
    """Validate a run spec (§4.1; a JSON file or a dict) and return it resolved, with every default
    filled. ConfigError on unknown keys or values, for policy id BL8 (benchmarks run through
    `bench`), and for BL2 and SILOED on a series-model instance unless borrowers.merge is false."""
    raw = _read(src)
    bad = [k for k in raw if k not in RUN_KEYS]
    if bad:
        _fail("", f"unknown key(s) {bad}; allowed: {list(RUN_KEYS)}")
    if raw.get("schema_version") != SCHEMA_VERSION or isinstance(raw.get("schema_version"), bool):
        _fail("schema_version", f"required, must be {SCHEMA_VERSION}")
    name = raw.get("name")
    if not isinstance(name, str) or not _NAME_RE.match(name):
        _fail("name", f"required: a non-empty name of letters, digits, '_', '.', '-', got {name!r}")
    inst_src = raw.get("instance")
    if isinstance(inst_src, str):
        if not inst_src:
            _fail("instance", "empty file name")
    elif not isinstance(inst_src, dict):
        _fail("instance", "required: a config file under code/sim/configs/ or an inline config object")
    if raw.get("overrides") is not None and not isinstance(raw["overrides"], dict):
        _fail("overrides", "expected an object of dotted paths")
    ov = _object(raw, "overrides")
    if any(not isinstance(k, str) or not k for k in ov):
        _fail("overrides", "expected an object of dotted paths")
    lm = _object(raw, "lender_model")
    bad = [k for k in lm if k not in LENDER_MODEL_KEYS]
    if bad:
        _fail("lender_model", f"unknown key(s) {bad}; allowed: {list(LENDER_MODEL_KEYS)} (builder fields such "
                              "as merge_identical_layers go into overrides)")
    choices = {"schedule": C.SCHEDULES, "information": ("I1", "I2"), "on_unavailable": ("sell", "refuse"),
               "violations": ("absorb", "reclaim")}
    for k, opts in choices.items():
        if k in lm and lm[k] not in opts:
            _fail(f"lender_model.{k}", f"{lm[k]!r} is not one of {list(opts)}")
    if "params" in lm and not isinstance(lm["params"], dict):
        _fail("lender_model.params", "expected an object")
    eng = _object(raw, "engine")
    try:
        C._engine(eng)
    except ConfigError as err:
        _fail("engine", str(err))
    pol = raw.get("policy")
    if not isinstance(pol, dict) or "id" not in pol:
        _fail("policy", "required: an object with 'id' (and 'params')")
    bad = [k for k in pol if k not in ("id", "params")]
    if bad:
        _fail("policy", f"unknown key(s) {bad}; allowed: ['id', 'params']")
    pid = pol["id"]
    if pid == "BL8":
        _fail("policy.id", "BL8 is not a policy id: offline benchmarks run through the field 'bench'")
    try:
        e = registry.entry(pid)
    except (KeyError, TypeError):
        _fail("policy.id", f"unknown policy id {pid!r}; known: {list(registry.POLICY_IDS) + list(registry.MS5B_IDS)}")
    params = pol.get("params")
    params = {} if params is None else params
    _check_params(pid, params, "policy.params")

    cfg = instance_config({"instance": inst_src, "overrides": ov})
    seed0 = cfg.get("seed", 0)
    sd = _object(raw, "seeds")
    bad = [k for k in sd if k not in ("config", "lender", "policy")]
    if bad:
        _fail("seeds", f"unknown key(s) {bad}; allowed: ['config', 'lender', 'policy']")
    s_cfg = _int_list(sd.get("config", [seed0]), "seeds.config", "config seeds", unique=True)
    s_len = sd.get("lender", "config")
    if s_len != "config":
        s_len = _int_list(s_len, "seeds.lender", "lender seeds")
        if len(s_len) != len(s_cfg):
            _fail("seeds.lender", f"{len(s_len)} lender seeds for {len(s_cfg)} config seeds (they are paired)")
    s_pol = sd.get("policy", "config")
    if s_pol != "config":
        s_pol = _int_list(s_pol, "seeds.policy", "policy seeds", unique=True)

    bench = raw.get("bench")
    if bench is not None:
        if not isinstance(bench, dict):
            _fail("bench", "expected null or an object")
        bad = [k for k in bench if k not in BENCH_KEYS]
        if bad:
            _fail("bench", f"unknown key(s) {bad}; allowed: {list(BENCH_KEYS)}")
        if bench.get("kind") not in BENCH_KINDS:
            _fail("bench.kind", f"required, one of {list(BENCH_KINDS)}")
        try:
            C._bench({k: v for k, v in bench.items() if k not in ("kind", "merged")})
        except ConfigError as err:
            _fail("bench", str(err))
        if "merged" in bench and not isinstance(bench["merged"], bool):
            _fail("bench.merged", "expected true or false")
        if "merged" in bench and bench.get("kind") != "lp":
            _fail("bench.merged", f"only for kind 'lp' (the merged relaxation's LP), not {bench.get('kind')!r}")
        if e.runner != "simulate":
            _fail("bench", f"a benchmark needs an engine run; {pid} has runner {e.runner!r}")
    out = raw.get("out", f"code/sim/out/{name}")
    if not isinstance(out, str) or not out:
        _fail("out", "expected a non-empty path")

    # §15.1: every baseline (also inside SILOED, BL6, BL7, A8 and A8P) runs with auto_drain false
    ce = cfg.get("engine") if isinstance(cfg.get("engine"), dict) else {}
    if {**ce, **eng}.get("auto_drain") is True:
        inner = registry.inner_of(pid, params) if pid == "SILOED" or pid in registry.GUARD_IDS else None
        if pid in BASELINE_IDS or (inner is not None and inner[0] in BASELINE_IDS):
            _fail("engine.auto_drain", f"{pid if inner is None else pid + ' around ' + str(inner[0])} is a "
                                       "baseline, which runs with auto_drain false (§15.1)")
    # A8 and A8P with test T0g run under every lender option: make_policy passes them the run's on_unavailable, and
    # under 'refuse' T0gBound counts every Buy that the lender could refuse as uncertain from slot 0 (condition C2)
    if e.runner == "siloed":
        b = cfg.get("borrowers") or {}
        if isinstance(b, dict) and b.get("model") == "series" and b.get("merge", True) is not False:
            _fail("policy.id", f"{pid} runs per borrower: on a series-model instance set borrowers.merge "
                               "to false (instance config or overrides)")
    return {"schema_version": SCHEMA_VERSION, "name": name, "instance": copy.deepcopy(inst_src),
            "overrides": copy.deepcopy(ov), "lender_model": copy.deepcopy(lm), "engine": dict(eng),
            "policy": {"id": pid, "params": copy.deepcopy(params)},
            "seeds": {"config": s_cfg, "lender": s_len, "policy": s_pol},
            "bench": copy.deepcopy(bench), "out": out}


def _lender_model(spec: dict, inst: Instance) -> LenderModel:
    """The instance config's lender model with the run spec's keys on top (each given key wins; a
    changed schedule without 'params' starts from the new schedule's default parameters)."""
    base = {k: v for k, v in inst.config.get("lender_model", {}).items() if k in LENDER_MODEL_KEYS}
    given = spec.get("lender_model") or {}
    if "schedule" in given and given["schedule"] != base.get("schedule") and "params" not in given:
        base["params"] = {}
    merged = {**base, **copy.deepcopy(given)}
    return C.lender_model(C._lender_model(merged))


def build(spec: dict, config_seed: int) -> tuple[Instance, LenderModel, EngineConfig]:
    """Instance (the instance config with the overrides and seed = config_seed), lender model and
    engine config (instance config's sections, merged key by key with the run spec's) of one run."""
    cfg = instance_config(spec)
    cfg["seed"] = int(config_seed)
    inst = build_instance(cfg)
    model = _lender_model(spec, inst)
    eng = {**(inst.config.get("engine") or {}), **(spec.get("engine") or {})}
    return inst, model, engine_config(eng)


# ---------------------------------------------------------------- policies
def _planned_lease(x, i: int) -> PlannedLease:
    if isinstance(x, PlannedLease):
        return x
    try:
        if isinstance(x, dict):
            d = dict(x)
            d["admission_off"] = tuple(tuple(int(v) for v in ab) for ab in d.get("admission_off", ()))
            return PlannedLease(**d)
        if isinstance(x, (list, tuple)):
            v = list(x)
            if len(v) > 6:
                v[6] = tuple(tuple(int(w) for w in ab) for ab in v[6])
            return PlannedLease(*v)
    except (TypeError, ValueError) as err:
        raise ConfigError(f"run spec policy.params.plan[{i}]: {err}") from None
    raise ConfigError(f"run spec policy.params.plan[{i}]: expected an object or a list of PlannedLease fields")


def driver_inputs(policy_id: str, params: dict, inst: Instance,
                  given: Optional[dict] = None) -> tuple[dict, dict]:
    """(inputs, meta): the driver inputs of §4.2 that `policy_id` with `params` needs, computed from
    `inst` unless given: N_bound = max(N_u T_s, 3) with N_u = len(units(inst).client) (a hindsight
    statistic used as C3-T2's a-priori N, M6); pred_demand = previous-day demand (n, T_fast) and
    pred_cols = drivers.predict.plan_daily on it (the driver's 'bench' stream of the config seed for
    LP rounding); future_demand = realized slot means (n, T_slow) (lookahead). `meta` records the
    sources for the run file."""
    given = dict(given or {})
    bad = [k for k in given if k not in registry.INPUTS]
    if bad:
        raise ConfigError(f"unknown driver input(s) {bad}; allowed {list(registry.INPUTS)}")
    need = registry.needed_inputs(policy_id, params)
    out, meta = {}, {}
    for k in need:
        if k in given:
            out[k] = given[k]
            meta[k] = "given"
    if "N_bound" in need and "N_bound" not in out:
        out["N_bound"] = max(len(units(inst).client) * inst.grid.T_slow, 3)
        meta["N_bound"] = int(out["N_bound"])
        meta["N_bound_source"] = N_BOUND_SOURCE
    if ("pred_cols" in need and "pred_cols" not in out) or ("pred_demand" in need and "pred_demand" not in out):
        from . import predict      # U10; imported only when a run needs predictions
        g = inst.grid
        pred_demand = out.get("pred_demand")
        if pred_demand is None:
            pred_demand = predict.previous_day(inst.clients.demand, 1440 // g.fast_min)
            if "pred_demand" in need:
                out["pred_demand"] = pred_demand
                meta["pred_demand"] = PRED_LABEL
        if "pred_cols" in need and "pred_cols" not in out:
            out["pred_cols"] = predict.plan_daily(inst, pred_demand, day_slots=1440 // g.slow_min,
                                                  method="auto", rng=C.rng_streams(inst.seed)["bench"])
            if hasattr(out["pred_cols"], "label"):
                out["pred_cols"].label = PRED_LABEL      # §13.1: the label of the prediction's class
            meta["pred_cols"] = PRED_LABEL
    if "future_demand" in need and "future_demand" not in out:
        g = inst.grid
        out["future_demand"] = inst.clients.demand.reshape(inst.n, g.T_slow, g.phi).mean(axis=2)
        meta["future_demand"] = "realized slot means (n, T_slow)"
    return out, meta


def _make_policy(spec: dict, inst: Instance, inputs: Optional[dict] = None) -> tuple[Policy, dict]:
    pol = spec.get("policy") or {}
    pid = pol.get("id")
    params = dict(pol.get("params") or {})
    try:
        e = registry.entry(pid)
    except (KeyError, TypeError):
        known = list(registry.POLICY_IDS) + list(registry.MS5B_IDS)
        raise ConfigError(f"unknown policy id {pid!r}; known: {known}") from None
    if not e.policy_class:
        raise ConfigError(f"{pid} has no policy class (runner {e.runner!r}); run it through drivers.run.run"
                          + (" with the run spec's 'bench' field" if pid == "BL8" else ""))
    _check_params(pid, params, "policy.params")
    cls = registry.resolve(pid)
    kw = copy.deepcopy(params)
    if pid == "FIXED_PLAN":
        kw["plan"] = [_planned_lease(x, i) for i, x in enumerate(params.get("plan", []))]
    vals, meta = driver_inputs(pid, params, inst, inputs)
    if pid in registry.WRAPPERS:
        kw["inner_params"] = {**dict(params.get("inner_params") or {}), **vals}
    elif pid in registry.GUARD_IDS:
        # Q44 note §6.1 item 5: A8's own N_bound (S_rbar = 'theory', R in S); the inner's inputs in inner_params.
        # A8P (design/sublet_v2.md §8.1 C35) as A8, with its own entry's defaults (inner 'A9')
        iid, ipar = registry.inner_of(pid, params)
        inner_need = registry.needed_inputs(iid, ipar)
        kw["inner_params"] = {**ipar, **{k: vals[k] for k in inner_need}}
        kw.update({k: vals[k] for k in registry.a8_own_inputs(params, pid)})
        # the lender's sale rule of this run (guard.T0gBound, condition C2: under 'refuse' T0g counts as uncertain
        # every Buy the lender could refuse, from slot 0), from the run spec's lender model over the instance's
        kw["on_unavailable"] = _lender_model(spec, inst).on_unavailable
    else:
        kw.update(vals)
    try:
        return cls(**kw), meta
    except PolicyError as err:
        raise ConfigError(f"policy {pid}: {err}") from err


def make_policy(spec: dict, inst: Instance, *, inputs: Optional[dict] = None) -> Policy:
    """The policy of a class-backed id (A1-A9, A8P, RR_RENEW, MARKING, BL0a, BL1-BL7, and FIXED_PLAN),
    whatever its runner, with the driver inputs computed from `inst` (§4.2; `inputs` overrides
    them, e.g. pred_cols in tests). For BL6 and BL7 the inner id's driver inputs go into
    `inner_params`; A8 and A8P get their own N_bound (S_rbar = 'theory' and safe not 'fb'), the inner id's inputs
    in `inner_params` (Q44 note §6.1 item 5; design/sublet_v2.md §8.1 C35) and the run's lender option
    `on_unavailable` (from the run spec's lender model over the instance config's; guard.T0gBound, condition
    C2). ConfigError for SILOED, BL0b and BL8 (no policy class), unknown ids or parameters, and for a
    PolicyError of the constructor."""
    return _make_policy(spec, inst, inputs)[0]


# ---------------------------------------------------------------- runs
def _out_dir(spec: dict, out_dir) -> Path:
    p = Path(out_dir if out_dir is not None else spec["out"])
    return p if p.is_absolute() else REPO / p


def _resolved_params(spec_params: dict, pol: Optional[Policy]) -> dict:
    got = {}
    if pol is not None and callable(getattr(pol, "params", None)):
        got = pol.params() or {}
    return {**spec_params, **got}


def _extra_meta(spec: dict, pid: str, params: dict, seeds: dict, info: str, inputs_meta: dict,
                runner: str) -> dict:
    return {"run_spec_hash": C.config_hash(spec), "run_spec_name": spec["name"], "policy_id": pid,
            "params": params, "seeds": dict(seeds), "info_class": info, "runner": runner,
            "driver_inputs": inputs_meta}


def bench_fields(spec: dict, inst: Instance) -> dict:
    """The resolved BL8 fields of a run: the instance config's MS1 `bench` section with the run spec's
    `bench` keys on top (each given key wins; the rule of `engine` and `lender_model`, §4.1)."""
    base = {k: v for k, v in (inst.config.get("bench") or {}).items() if k in MS1_BENCH_FIELDS}
    return {**base, **dict(spec["bench"])}


def ratio_validity(grid: str, inst: Instance, model: LenderModel) -> Optional[str]:
    """None if a ratio to a BL8 value computed on bench grid `grid` is meaningful for a run of `inst`
    under `model`, else the reason (§15.10, design §5.2.4): ratios only for runs on the benchmark's
    grid with violations absorbed. Grid 'slow' is the run's grid only when Δf = Δs; with 1-min routing
    it is the slow-grid approximation, which bounds the engine's optimum in neither direction (MS1
    §8.5); 'fast' is the engine's model and 'slow_lb' the lower bound for 1-min runs (MS1 §8.6)."""
    g = inst.grid
    if grid == "slow" and g.fast_min < g.slow_min:
        return (f"bench grid 'slow' on a run with Δf = {g.fast_min} < Δs = {g.slow_min} min: the slow-grid "
                "approximation bounds the run's optimum in neither direction")
    if model.violations != "absorb":
        return f"violations = {model.violations!r}: the realized schedule is no valid omega for the benchmark"
    return None


def _bench(spec: dict, res, inst: Instance, model: LenderModel) -> dict:
    from . import bench as dbench      # U11 (BL8); imported only when a run spec asks for a benchmark
    b = bench_fields(spec, inst)
    kind = b["kind"]
    kw = {k: v for k, v in b.items() if k != "kind"}
    # a RunResult does not record on_unavailable: a 'refuse' run's schedule holds refusal sets (MS1 §8.1)
    try:
        sr = dbench.bench_for(res, inst, kind, refuse_unavailable=(model.on_unavailable == "refuse"), **kw)
    except ValueError as err:          # e.g. DomainError of the DP: recorded, the run file is still written
        out = {"kind": kind, "fields": kw, "method": None, "benchmark": None, "grid": kw.get("grid"),
               "status": None, "status_msg": f"not solved: {type(err).__name__}: {err}", "objective": None,
               "dual_bound": None, "gap": None, "ratio": None, "ratio_note": "no benchmark value", "size": None,
               "solve_s": None}
        res.metrics["bench"] = out
        return out
    why = ratio_validity(sr.grid, inst, model)
    out = {"kind": kind, "fields": kw, "method": sr.method, "benchmark": sr.benchmark, "grid": sr.grid,
           "status": sr.status, "status_msg": sr.status_msg, "objective": sr.objective, "dual_bound": sr.dual_bound,
           "gap": sr.gap, "ratio": None if why else ratio(res.components["total"], sr), "ratio_note": why,
           "size": sr.size, "solve_s": sr.solve_s}
    res.metrics["bench"] = out
    return out


def _write_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(obj), indent=1, allow_nan=False) + "\n")


def run(spec: Union[dict, str, Path], out_dir=None) -> list:
    """Run a spec over its seeds (§4.1, §4.3) and write the run files into `out_dir` (default: the
    spec's `out`, relative to the repository). Per run: runner 'simulate' gives a RunResult and
    `<name>_c<c>_l<l>_p<p>.json` (metrics.write_run with extra_meta); 'siloed' gives the dict of
    run_siloed, one such file per borrower (suffix `_b<i>`) and `<name>_c<c>_l<l>_p<p>_sum.json`;
    'analytic' (BL0b, once per config seed) gives {'bl0b_usd', 'own_capacity_usd', ...} and
    `<name>_c<c>.json`."""
    spec = load_run_spec(spec)
    pid, params = spec["policy"]["id"], spec["policy"]["params"]
    e = registry.entry(pid)
    out = _out_dir(spec, out_dir)
    name, sd = spec["name"], spec["seeds"]
    results: list = []
    for i, c in enumerate(sd["config"]):
        inst, model, ecfg = build(spec, c)
        lseed = c if sd["lender"] == "config" else sd["lender"][i]
        if e.runner == "analytic":
            from . import provision    # U11 (BL0b)
            own_kw = {"a_commit": params["a_commit"]} if "a_commit" in params else {}
            try:
                bl0b = float(provision.bl0b_usd(inst, **params))
                own = float(provision.own_capacity_usd(inst, **own_kw))
            except ValueError as err:     # e.g. no borrower_stats: explicit and from_core instances (C4)
                raise ConfigError(f"policy {pid} on instance {inst.name!r}: {err}") from err
            d = {"policy_id": pid, "params": dict(params), "info_class": registry.info_class(pid, params),
                 "bl0b_usd": bl0b, "own_capacity_usd": own,
                 "seeds": {"config": int(c)}, "run_spec_hash": C.config_hash(spec), "run_spec_name": name,
                 "config_hash": C.config_hash(inst.config), "horizon_h": inst.grid.horizon_min / 60.0}
            _write_json(d, out / f"{name}_c{c}.json")
            results.append(d)
            continue
        for p in ([c] if sd["policy"] == "config" else sd["policy"]):
            tag = f"{name}_c{c}_l{lseed}_p{p}"
            if e.runner == "simulate":
                pol, imeta = _make_policy(spec, inst)
                res = simulate(inst, pol, model, ecfg, lender_seed=lseed, policy_seed=p)
                rp = _resolved_params(params, pol)
                label = imeta.get("pred_cols") or imeta.get("pred_demand")
                extra = _extra_meta(spec, pid, rp, res.seeds,
                                    registry.info_class(pid, rp, model.information, label), imeta, e.runner)
                if spec["bench"] is not None:
                    extra["bench"] = _bench(spec, res, inst, model)
                write_run(res, inst, out / f"{tag}.json", extra_meta=extra)
                results.append(res)
                continue
            # runner 'siloed': BL2 itself, or SILOED around its inner id
            if pid == "SILOED":
                iid, ipar = registry.inner_of(pid, params)
                inner_spec = {**spec, "policy": {"id": iid, "params": ipar}}
            else:
                iid, ipar, inner_spec = pid, params, spec
            built: list = []

            def factory(sub: Instance, _s=inner_spec, _b=built) -> Policy:
                pol_b, meta_b = _make_policy(_s, sub)
                _b.append((pol_b, meta_b))
                return pol_b

            d = run_siloed(inst, factory, model, ecfg, lender_seed=lseed, policy_seed=p)
            for bi, (b, idx, res_b, sub) in enumerate(zip(d["borrowers"], d["clients"], d["results"],
                                                          d["instances"])):
                pol_b, meta_b = built[bi]
                rp = _resolved_params(ipar, pol_b)
                label = meta_b.get("pred_cols") or meta_b.get("pred_demand")
                extra = _extra_meta(spec, pid, rp, res_b.seeds,
                                    registry.info_class(iid, rp, model.information, label), meta_b, e.runner)
                extra.update(inner_id=iid, borrower=b, clients=idx)
                write_run(res_b, sub, out / f"{tag}_b{bi}.json", extra_meta=extra)
            _write_json({"meta": {"name": inst.name, "run_spec_hash": C.config_hash(spec), "run_spec_name": name,
                                  "policy_id": pid, "inner_id": iid, "params": dict(params),
                                  "info_class": registry.info_class(pid, params, model.information),
                                  "seeds": d["seeds"], "config_hash": C.config_hash(inst.config),
                                  "borrowers": d["borrowers"], "clients": d["clients"]},
                         "components": d["components"], "invariant_failures": d["invariant_failures"]},
                        out / f"{tag}_sum.json")
            results.append(d)
    return results


__all__ = ["ConfigError", "load_run_spec", "build", "make_policy", "driver_inputs", "instance_config",
           "set_path", "run", "bench_fields", "ratio_validity", "BASELINE_IDS"]
