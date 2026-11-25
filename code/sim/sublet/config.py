"""Load, validate and resolve simulator configs (design/sim_spec.md §4.1-§4.2, §10).

`load_config` returns the resolved config: every default of §4.2 applied, the presets expanded
(`menu_preset` into `contracts`, `lenders_preset` and `lender_defaults` into `lenders`; the
lenders of `protected_per_region` are added by the builder from that resolved field), every
"a11" price replaced by its number from a11_calibration.json, and every "random" or "auto"
value drawn with the "build" stream of `rng_streams(seed)` in the order of §4.3:
  1. time.start_minute_of_week; 2. R of synthetic lenders given by R_rate; 3. regions of the
  lenders with region "auto"; 5. trace offsets; 6. load scenarios "auto"; 7. the offsets of
  the default WildChat fluctuation sources.
The resolved config is itself a valid config and resolves to itself, so
`build_instance(inst.config)` rebuilds the same instance. A synthetic lender's resolved entry
keeps its R_rate next to the drawn R; whenever R is present it is used.
Unknown keys and invalid values raise ConfigError.

MS3 addition (design/sim_spec_ms3.md §2.3, C10): `costs.beta_jl_usd` may be an object {LLM id: USD}, a
transfer fee per LLM (the same at every site); it must name every LLM and no other id. A number keeps the
MS1 meaning (one fee for every (j, l)).

MS4 addition (design/sim_spec_ms4.md §2.3, C24): `borrowers.normalize` of the series model, "none" (the default,
the MS1-MS3 builder) or "mean" (each borrower's overflow scaled to mean 1 before Gamma, instance.py). The regional and
explicit models reject the key. The resolved config carries it only when it is "mean", so the resolved config and
its hash are unchanged for every config without it or with "none".

MS7 addition (design/ms7/plan.md §3 X2, design/ms7/feasibility/oos.md §3 and §4 item 1; change C55), the keys of
the out-of-sample folds. Each is carried in the resolved config only when it is set, as MS4 C24, so the resolved
config and its hash are unchanged for every config without them; none draws from the build stream.
  lenders[].calib_slots (also under lender_defaults; trace lenders only): [lo, hi), 0 <= lo < hi <= the length of
      the lender's slack series in 5-min slots: the calibration window. The builder fits the buffer, B, v_top, the
      menu pruning and the IR prices on S_full[lo:hi] and replays the whole series as before (instance.py). A
      synthetic lender ignores a calib_slots of lender_defaults and rejects its own.
  borrowers (regional model):
      wildchat_model 'a4c_fit'   p_o and r_oj of the fit part of the early window (traces.borrowers.A4C_MODELS)
      p_o_week                   an index of traces.borrowers.wildchat_weeks(): the evaluated demand takes that
                                 calendar week's own profile in place of the model's averaged p_o
      demand_fit                 {xi_sources: {region: {series, offset_min}} (every region, explicit offsets),
                                 horizon_min (>= 1), start_minute_of_week}: the fit-period demand share x p_o (of
                                 wildchat_model) x xi of these sources; own capacity C0 (own_capacity_quantile of its
                                 smoothed series) and, without gamma, Gamma's peak come from it, not from the
                                 evaluated horizon
      gamma                      Gamma (> 0) as given (pinned), instead of tightness x supply / peak.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np

from . import calib
from .paths import CONFIGS
from .types import LenderModel
from .traces import borrowers as tb
from .traces import catalog as tc
from .traces import lenders as tl


class ConfigError(ValueError):
    """Invalid config."""


SCHEMA_VERSION = 1
ENGINE_FIELDS = ("auto_drain", "record_routing", "check_invariants", "tol")   # allowed keys of cfg['engine']
MIN_PER_WEEK = 10080
A4B_REGIONS = ("north_america", "europe", "east_asia", "south_southeast_asia", "south_america")
DEFAULT_ADJACENCY = (("north_america", "europe"), ("north_america", "south_america"),
                     ("north_america", "east_asia"), ("europe", "south_southeast_asia"),
                     ("east_asia", "south_southeast_asia"))   # §10 S7
XI_DEFAULT_SOURCES = ("azure2024_conv", "azure2024_code", "burstgpt_1", "burstgpt_2", "burstgpt_3")   # S23
LENDER_GROUPS = ("maas20", "spot_L7", "all24", "spot_all")
DEFAULT_SCENARIOS = ("a5_10GBps", "a5_2GBps")   # §4.3 step 6, §10 S6
SLO_CLASSES = ("strict", "relaxed")
NORMALIZE = ("none", "mean")                     # borrowers.normalize of the series model (MS4 C24)
SCHEDULES = ("trace", "eager", "adaptive", "safe_site", "iid_step", "correlated")
SCHEDULE_PARAMS = {   # allowed params per schedule with their defaults; None = resolved by Lender
    "trace": {}, "eager": {}, "adaptive": {},
    "safe_site": {"D_slots": None, "k": None, "Phi": None},
    "iid_step": {"D_slots": None, "p": 0.5, "U": None},
    "correlated": {"p_sh": "required", "groups": None, "delay_slots_max": None},
}

TOP_KEYS = ("schema_version", "name", "seed", "time", "billing", "prices", "contracts", "menu_preset", "llms",
            "lenders", "lenders_preset", "lender_defaults", "protected_per_region", "lender_model", "regions",
            "borrowers", "costs", "stranding", "units", "engine", "bench")
LENDER_KEYS = ("id", "kind", "series", "series_values", "region", "group", "menu", "n_layers", "layer_gpus",
               "lease_size_quantile", "offset", "load_scenario", "lam_s", "capacity_gpus", "prices", "R", "R_rate",
               "calib_slots")                    # calib_slots: MS7 C55
WILDCHAT_MODELS = ("early", "full", "early_card_map") + tb.A4C_MODELS     # 'a4c_fit': MS7 C55
REGIONAL_KEYS = ("model", "wildchat_model", "s_S", "xi_sources", "own_capacity_quantile", "smoothing_min",
                 "market_tightness", "slo_class", "p_o_week", "demand_fit", "gamma")    # the last three: MS7 C55
DEMAND_FIT_KEYS = ("xi_sources", "horizon_min", "start_minute_of_week")


# ---------------------------------------------------------------- small validators
def _fail(path: str, msg: str):
    raise ConfigError(f"{path}: {msg}" if path else msg)


def _obj(v, path: str, allowed) -> dict:
    if v is None:
        v = {}
    if not isinstance(v, dict):
        _fail(path, f"expected an object, got {type(v).__name__}")
    bad = [k for k in v if k not in allowed]
    if bad:
        _fail(path, f"unknown key(s) {bad}; allowed: {list(allowed)}")
    return v


def _is_int(v) -> bool:
    return isinstance(v, (int, np.integer)) and not isinstance(v, bool)


def _is_num(v) -> bool:
    return (isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool)
            and math.isfinite(float(v)))


def _int(v, path: str, lo: Optional[int] = None, hi: Optional[int] = None) -> int:
    if not _is_int(v):
        _fail(path, f"expected an integer, got {v!r}")
    v = int(v)
    if lo is not None and v < lo:
        _fail(path, f"must be >= {lo}, got {v}")
    if hi is not None and v > hi:
        _fail(path, f"must be <= {hi}, got {v}")
    return v


def _num(v, path: str, lo: Optional[float] = None, hi: Optional[float] = None, lo_open: bool = False) -> float:
    if not _is_num(v):
        _fail(path, f"expected a finite number, got {v!r}")
    v = float(v)
    if lo is not None and (v < lo or (lo_open and v == lo)):
        _fail(path, f"must be {'>' if lo_open else '>='} {lo}, got {v}")
    if hi is not None and v > hi:
        _fail(path, f"must be <= {hi}, got {v}")
    return v


def _bool(v, path: str) -> bool:
    if not isinstance(v, bool):
        _fail(path, f"expected true or false, got {v!r}")
    return v


def _str(v, path: str) -> str:
    if not isinstance(v, str) or not v:
        _fail(path, f"expected a non-empty string, got {v!r}")
    return v


def _choice(v, path: str, options) -> Any:
    if v not in options:
        _fail(path, f"{v!r} is not one of {list(options)}")
    return v


# ---------------------------------------------------------------- public helpers
def rng_streams(seed: int) -> dict[str, np.random.Generator]:
    """Four independent generators from SeedSequence(seed).spawn(4): 'build', 'lender', 'policy', 'bench'."""
    ss = np.random.SeedSequence(int(seed)).spawn(4)
    return {k: np.random.default_rng(s) for k, s in zip(("build", "lender", "policy", "bench"), ss)}


def config_hash(cfg: dict) -> str:
    """sha256 hex of json.dumps(cfg, sort_keys=True, separators=(',', ':'))."""
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def lender_model(cfg: dict) -> LenderModel:
    """LenderModel from the resolved cfg['lender_model'] (merge_identical_layers stays a builder field)."""
    if "lender_model" in cfg:
        lm = cfg["lender_model"]
    else:   # a full config without lender_model, or the lender_model object itself
        lm = {} if "schema_version" in cfg else cfg
    return LenderModel(schedule=lm.get("schedule", "trace"), information=lm.get("information", "I1"),
                       on_unavailable=lm.get("on_unavailable", "sell"), violations=lm.get("violations", "absorb"),
                       params=dict(lm.get("params", {}) or {}))


def _read(src) -> dict:
    if isinstance(src, dict):
        return copy.deepcopy(src)
    if not isinstance(src, (str, Path)):
        raise ConfigError(f"config source must be a path or a dict, got {type(src).__name__}")
    p = Path(src)
    if not p.is_file() and (CONFIGS / p).is_file():
        p = CONFIGS / p
    try:
        with open(p) as f:
            cfg = json.load(f)
    except FileNotFoundError:
        raise ConfigError(f"config file {src} not found") from None
    except json.JSONDecodeError as e:
        raise ConfigError(f"config file {p} is not valid JSON: {e}") from None
    if not isinstance(cfg, dict):
        raise ConfigError(f"config file {p} does not hold a JSON object")
    return cfg


# ---------------------------------------------------------------- sections
def _time(t) -> dict:
    t = _obj(t, "time", ("slow_slot_min", "fast_slot_min", "horizon_min", "start_minute_of_week", "clock_alignment"))
    slow = _int(t.get("slow_slot_min", 5), "time.slow_slot_min", 1)
    fast = _int(t.get("fast_slot_min", 1), "time.fast_slot_min", 1)
    if slow % fast:
        _fail("time.fast_slot_min", f"{fast} does not divide slow_slot_min {slow}")
    if "horizon_min" not in t:
        _fail("time.horizon_min", "required")
    hz = _int(t["horizon_min"], "time.horizon_min", 1)
    if hz % slow:
        _fail("time.horizon_min", f"{hz} is not a multiple of slow_slot_min {slow}")
    mow = t.get("start_minute_of_week", 0)
    if mow != "random":
        mow = _int(mow, "time.start_minute_of_week", 0, MIN_PER_WEEK - 1)
    ca = t.get("clock_alignment", "random_offset")
    if ca == "local_midnight":
        _fail("time.clock_alignment", "'local_midnight' is reserved and not built in MS1 (sim_spec §10 S12)")
    _choice(ca, "time.clock_alignment", ("random_offset",))
    return {"slow_slot_min": slow, "fast_slot_min": fast, "horizon_min": hz, "start_minute_of_week": mow,
            "clock_alignment": ca}


def _prices(p) -> dict:
    p = _obj(p, "prices", ("a0_usd_per_gpu_h", "q_gpu_usd_per_gpu_h", "a_protected_usd_per_gpu_h",
                           "revocable_price", "buffer_quantile", "multipliers"))
    a11 = calib.prices()
    out = {}
    for key, ref in (("a0_usd_per_gpu_h", "a0"), ("q_gpu_usd_per_gpu_h", "q_gpu"), ("a_protected_usd_per_gpu_h", "a_p")):
        v = p.get(key, "a11")
        out[key] = a11[ref] if v == "a11" else _num(v, f"prices.{key}", 0.0, lo_open=True)
    out["revocable_price"] = _choice(p.get("revocable_price", "ir"), "prices.revocable_price",
                                     ("ir", "a0", "multiplier", "explicit"))
    out["buffer_quantile"] = _choice(p.get("buffer_quantile", "p99"), "prices.buffer_quantile", ("p99", "p99.9"))
    m = p.get("multipliers") or {}
    if not isinstance(m, dict):
        _fail("prices.multipliers", "expected an object contract id -> multiplier")
    out["multipliers"] = {_str(k, "prices.multipliers"): _num(v, f"prices.multipliers.{k}", 0.0, lo_open=True)
                          for k, v in m.items()}
    return out


def _preset_contracts(name, slow: int) -> list[dict]:
    _choice(name, "menu_preset", ("a11_default",))
    if slow not in (1, 5):
        _fail("menu_preset", f"'a11_default' exists only for slow slots of 1 and 5 min, not {slow}")
    out = []
    for k, c in calib.A11["contracts"].items():
        if k != "protected" and c["slot_min"] == slow:
            out.append({"id": k, "tau_min": c["tau_min"], "H_min": c["H_min"], "klass": c["class"]})
    out.append({"id": "protected", "tau_min": None, "H_min": 0, "prepaid_min": slow, "klass": "protected"})
    return out


def _contracts(cfg: dict, slow: int) -> list[dict]:
    if "contracts" in cfg and cfg.get("menu_preset") is not None:
        _fail("contracts", "give either contracts or menu_preset, not both")
    raw = cfg["contracts"] if "contracts" in cfg else _preset_contracts(cfg.get("menu_preset", "a11_default"), slow)
    if not isinstance(raw, list) or not raw:
        _fail("contracts", "expected a non-empty list")
    out, ids = [], set()
    for i, c in enumerate(raw):
        path = f"contracts[{i}]"
        c = _obj(c, path, ("id", "tau_min", "H_min", "prepaid_min", "klass"))
        cid = _str(c.get("id"), f"{path}.id")
        if cid in ids:
            _fail(f"{path}.id", f"duplicate contract id {cid!r}")
        ids.add(cid)
        if "tau_min" not in c:
            _fail(f"{path}.tau_min", "required (null for a protected contract)")
        tau = c["tau_min"]
        H = _int(c.get("H_min", 0), f"{path}.H_min", 0)
        e = {"id": cid, "tau_min": None, "H_min": H}
        if tau is None:
            if H != 0:
                _fail(f"{path}.H_min", f"a protected contract has H_min 0, got {H}")
            e["prepaid_min"] = _int(c.get("prepaid_min", slow), f"{path}.prepaid_min", 0)
        else:
            tau = _int(tau, f"{path}.tau_min", slow)
            if tau % slow:
                _fail(f"{path}.tau_min", f"{tau} is not a multiple of slow_slot_min {slow}")
            if "prepaid_min" in c:
                _fail(f"{path}.prepaid_min", "only protected contracts give prepaid_min (revocable: from billing)")
            e["tau_min"] = tau
        e["klass"] = _str(c["klass"], f"{path}.klass") if c.get("klass") is not None \
            else calib.contract_klass(e["tau_min"], H, slow)
        out.append(e)
    return out


def _llms(raw) -> list[dict]:
    if not isinstance(raw, list) or not raw:
        _fail("llms", "required: a non-empty list")
    out, ids = [], set()
    expl_keys = ("g", "w_GB", "kappa_wtok_per_min", "w_in", "T_dr_s")
    for i, x in enumerate(raw):
        path = f"llms[{i}]"
        x = _obj(x, path, ("id", "catalog", "entry", "tier", "kappa_mult") + expl_keys)
        lid = _str(x.get("id"), f"{path}.id")
        if lid in ids:
            _fail(f"{path}.id", f"duplicate LLM id {lid!r}")
        ids.add(lid)
        cat = _choice(x.get("catalog", "maas_a10"), f"{path}.catalog", ("maas_a10", "a5_llama3", "explicit"))
        e = {"id": lid, "catalog": cat}
        if cat == "explicit":
            if x.get("entry") is not None:
                _fail(f"{path}.entry", "an explicit LLM has no catalog entry")
            for k in expl_keys + ("tier",):
                if k not in x:
                    _fail(f"{path}.{k}", "required for catalog 'explicit'")
            e["tier"] = _str(x["tier"], f"{path}.tier")
            e["g"] = _int(x["g"], f"{path}.g", 1)
            e["w_GB"] = _num(x["w_GB"], f"{path}.w_GB", 0.0)
            kap = x["kappa_wtok_per_min"]
            e["kappa_wtok_per_min"] = "inf" if kap == "inf" else _num(kap, f"{path}.kappa_wtok_per_min", 0.0,
                                                                       lo_open=True)
            e["w_in"] = _num(x["w_in"], f"{path}.w_in", 0.0)
            e["T_dr_s"] = _num(x["T_dr_s"], f"{path}.T_dr_s", 0.0)
        else:
            bad = [k for k in expl_keys if k in x]
            if bad:
                _fail(path, f"{bad} are given only for catalog 'explicit'")
            name = _str(x.get("entry"), f"{path}.entry")
            try:
                ent = tc.entry(cat, name)
            except KeyError as err:
                _fail(f"{path}.entry", str(err))
            tier = ent.get("tier") or tc.tier_of_a5(name)
            if x.get("tier") is not None and x["tier"] != tier:
                _fail(f"{path}.tier", f"catalog entry {cat}:{name} has tier {tier!r}, not {x['tier']!r}")
            e["entry"], e["tier"] = name, tier
        e["kappa_mult"] = _num(x.get("kappa_mult", 1.0), f"{path}.kappa_mult", 0.0, lo_open=True)
        out.append(e)
    return out


def _regions(r) -> dict:
    r = _obj(r, "regions", ("list", "adjacency", "default_slo_class", "relaxed_routing_cost_over_q"))
    lst = r.get("list", list(A4B_REGIONS))
    if not isinstance(lst, list) or not lst:
        _fail("regions.list", "expected a non-empty list")
    lst = [_str(x, "regions.list") for x in lst]
    if len(set(lst)) != len(lst):
        _fail("regions.list", "duplicate region")
    if "adjacency" in r:
        adj = r["adjacency"]
        if not isinstance(adj, list):
            _fail("regions.adjacency", "expected a list of pairs")
        out_adj = []
        for i, pr in enumerate(adj):
            if not isinstance(pr, list) or len(pr) != 2 or pr[0] == pr[1]:
                _fail(f"regions.adjacency[{i}]", f"expected a pair of two regions, got {pr!r}")
            for x in pr:
                _choice(x, f"regions.adjacency[{i}]", lst)
            out_adj.append([pr[0], pr[1]])
    else:
        out_adj = [list(e) for e in DEFAULT_ADJACENCY if e[0] in lst and e[1] in lst]
    return {"list": lst, "adjacency": out_adj,
            "default_slo_class": _choice(r.get("default_slo_class", "relaxed"), "regions.default_slo_class",
                                         SLO_CLASSES),
            "relaxed_routing_cost_over_q": _num(r.get("relaxed_routing_cost_over_q", 0.05),
                                                "regions.relaxed_routing_cost_over_q", 0.0)}


def _lender(raw: dict, own: dict, i: int, ctx: dict) -> dict:
    """Validate one lender (raw = lender_defaults merged with the lender's own entry `own`)."""
    path = f"lenders[{i}]"
    raw = _obj(raw, path, LENDER_KEYS)
    lid = _str(raw.get("id"), f"{path}.id")
    kind = _choice(raw.get("kind", "trace"), f"{path}.kind", ("trace", "protected", "synthetic"))
    path = f"lenders[{i}] ({lid})"
    con = ctx["contracts"]
    rev_ids = [c["id"] for c in con if c["tau_min"] is not None]
    prot_ids = [c["id"] for c in con if c["tau_min"] is None]

    def not_for(keys, why):
        for k in keys:
            if own.get(k) is not None:
                _fail(f"{path}.{k}", why)

    e = {"id": lid, "kind": kind}
    # trace fields
    if kind == "trace":
        sv = raw.get("series_values")
        if sv is not None:
            if raw.get("series") is not None and own.get("series") is not None:
                _fail(f"{path}.series", "give series or series_values, not both")
            if not isinstance(sv, list) or len(sv) < 2:
                _fail(f"{path}.series_values", "expected a list of at least two numbers")
            e["series"] = None
            e["series_values"] = [_num(v, f"{path}.series_values", 0.0) for v in sv]
        else:
            s = raw.get("series", lid) or lid
            if s not in ctx["trace_names"]:
                _fail(f"{path}.series", f"unknown trace series {s!r}")
            e["series"], e["series_values"] = s, None
    else:
        not_for(("series", "series_values"), f"only trace lenders have a slack series (kind {kind!r})")
        e["series"], e["series_values"] = None, None
    e["region"] = raw.get("region", "auto") or "auto"
    if e["region"] != "auto":
        _choice(e["region"], f"{path}.region", ctx["regions"])
    e["group"] = _str(raw.get("group", "auto") or "auto", f"{path}.group")
    menu = raw.get("menu")
    if menu is None:
        menu = prot_ids if kind == "protected" else rev_ids
    if not isinstance(menu, list) or not menu:
        _fail(f"{path}.menu", "expected a non-empty list of contract ids")
    for k in menu:
        _choice(k, f"{path}.menu", [c["id"] for c in con])
    if len(set(menu)) != len(menu):
        _fail(f"{path}.menu", "duplicate contract id")
    if kind == "protected" and any(k in rev_ids for k in menu):
        _fail(f"{path}.menu", "a protected lender offers only protected contracts")
    e["menu"] = list(menu)
    e["n_layers"] = _int(raw.get("n_layers", 8), f"{path}.n_layers", 1)
    e["layer_gpus"] = _int(raw.get("layer_gpus", 8), f"{path}.layer_gpus", 1)
    e["lease_size_quantile"] = _choice(raw.get("lease_size_quantile", 25), f"{path}.lease_size_quantile", (10, 25, 50))
    off = raw.get("offset", "random")
    if kind != "trace":
        off = 0
    elif off != "random":
        off = _int(off, f"{path}.offset", 0)
    e["offset"] = off
    sc = raw.get("load_scenario", "auto")
    _choice(sc, f"{path}.load_scenario", ["auto", "explicit"] + calib.scenarios())
    e["load_scenario"] = sc
    lam = raw.get("lam_s")
    if sc == "explicit":
        if lam is None:
            _fail(f"{path}.lam_s", "required with load_scenario 'explicit'")
        if isinstance(lam, dict):
            miss = [x for x in ctx["llm_ids"] if x not in lam]
            extra = [x for x in lam if x not in ctx["llm_ids"]]
            if miss or extra:
                _fail(f"{path}.lam_s", f"must give every LLM (missing {miss}, unknown {extra})")
            lam = {k: _num(v, f"{path}.lam_s.{k}", 0.0) for k, v in lam.items()}
        else:
            lam = _num(lam, f"{path}.lam_s", 0.0)
    else:
        not_for(("lam_s",), "lam_s is given only with load_scenario 'explicit'")
        lam = None
    e["lam_s"] = lam
    cap = raw.get("capacity_gpus")
    if kind == "trace":
        not_for(("capacity_gpus",), "a trace lender's capacity comes from its layers")
        cap = None
    elif kind == "synthetic":
        if cap is None:
            _fail(f"{path}.capacity_gpus", "required for a synthetic lender")
        cap = _num(cap, f"{path}.capacity_gpus", 0.0, lo_open=True)
    elif cap is not None:
        cap = _num(cap, f"{path}.capacity_gpus", 0.0, lo_open=True)
    e["capacity_gpus"] = cap
    pr = raw.get("prices") or {}
    if not isinstance(pr, dict):
        _fail(f"{path}.prices", "expected an object contract id -> USD/GPU-h")
    for k, v in pr.items():
        if k not in e["menu"]:
            _fail(f"{path}.prices", f"contract {k!r} is not on the lender's menu")
        _num(v, f"{path}.prices.{k}", 0.0, lo_open=True)
    if kind == "trace" and ctx["revocable_price"] != "explicit":
        bad = [k for k in pr if k in rev_ids]
        if bad:
            _fail(f"{path}.prices", f"revocable prices of a trace lender need revocable_price 'explicit' "
                                    f"(got {ctx['revocable_price']!r}); remove {bad}")
    need = kind == "synthetic" or (kind == "trace" and ctx["revocable_price"] == "explicit")
    if need:
        miss = [k for k in e["menu"] if k in rev_ids and k not in pr]
        if miss:
            _fail(f"{path}.prices", f"required for the revocable contracts {miss}")
    e["prices"] = {k: float(v) for k, v in pr.items()}
    if kind == "synthetic":
        R, rate = raw.get("R"), raw.get("R_rate")
        if rate is not None:
            rate = _num(rate, f"{path}.R_rate", 0.0, 1.0)
        if R is not None:
            if not isinstance(R, list):
                _fail(f"{path}.R", "expected a list of slow slots")
            R = [_int(r, f"{path}.R", 0, ctx["T_slow"] - 1) for r in R]
        elif rate is None:
            R = []
        e["R"], e["R_rate"] = R, rate
    else:
        not_for(("R", "R_rate"), "only synthetic lenders take R or R_rate")
        e["R"], e["R_rate"] = None, None
    # MS7 C55: the calibration window [lo, hi) of a trace lender, kept only when set (the hashes without it are
    # unchanged); a calib_slots of lender_defaults does not apply to the other kinds
    cs = raw.get("calib_slots")
    if kind != "trace":
        not_for(("calib_slots",), "only trace lenders take calib_slots (a calibration window of the slack series)")
    elif cs is not None:
        if not isinstance(cs, (list, tuple)) or len(cs) != 2:
            _fail(f"{path}.calib_slots", f"expected [lo, hi] in 5-min slots, got {cs!r}")
        n = len(e["series_values"]) if e["series"] is None else len(tl.slack(e["series"]))
        lo = _int(cs[0], f"{path}.calib_slots[0]", 0)
        hi = _int(cs[1], f"{path}.calib_slots[1]", lo + 1, n)
        e["calib_slots"] = [lo, hi]
    return e


def _lenders(cfg: dict, ctx: dict) -> list[dict]:
    preset = cfg.get("lenders_preset")
    base = []
    if preset is not None:
        _choice(preset, "lenders_preset", LENDER_GROUPS)
        base = [{"id": n} for n in tl.lender_names(preset)]
    own = cfg.get("lenders", [])
    if not isinstance(own, list):
        _fail("lenders", "expected a list")
    defaults = _obj(cfg.get("lender_defaults", {}), "lender_defaults", LENDER_KEYS)
    if "id" in defaults:
        _fail("lender_defaults.id", "lender_defaults cannot set id")
    out, ids = [], set()
    for i, x in enumerate(base + own):
        if not isinstance(x, dict):
            _fail(f"lenders[{i}]", "expected an object")
        e = _lender({**defaults, **x}, x, i, ctx)
        if e["id"] in ids:
            _fail(f"lenders[{i}].id", f"duplicate lender id {e['id']!r}")
        ids.add(e["id"])
        out.append(e)
    return out


def _protected_per_region(p, ctx: dict) -> dict:
    p = _obj(p, "protected_per_region", ("enabled", "menu", "capacity_gpus", "load_scenario"))
    prot_ids = [c["id"] for c in ctx["contracts"] if c["tau_min"] is None]
    en = _bool(p.get("enabled", False), "protected_per_region.enabled")
    menu = p.get("menu")
    if menu is None:
        menu = prot_ids
    if not isinstance(menu, list):
        _fail("protected_per_region.menu", "expected a list of contract ids")
    for k in menu:
        _choice(k, "protected_per_region.menu", prot_ids)
    if en and not menu:
        _fail("protected_per_region.menu", "enabled, but there is no protected contract")
    cap = p.get("capacity_gpus")
    if cap is not None:
        cap = _num(cap, "protected_per_region.capacity_gpus", 0.0, lo_open=True)
    sc = _choice(p.get("load_scenario", "a5_2GBps"), "protected_per_region.load_scenario", calib.scenarios())
    return {"enabled": en, "menu": list(menu), "capacity_gpus": cap, "load_scenario": sc}


def _lender_model(m) -> dict:
    m = _obj(m, "lender_model", ("schedule", "information", "on_unavailable", "violations",
                                 "merge_identical_layers", "params"))
    sch = _choice(m.get("schedule", "trace"), "lender_model.schedule", SCHEDULES)
    out = {"schedule": sch,
           "information": _choice(m.get("information", "I1"), "lender_model.information", ("I1", "I2")),
           "on_unavailable": _choice(m.get("on_unavailable", "sell"), "lender_model.on_unavailable", ("sell", "refuse")),
           "violations": _choice(m.get("violations", "absorb"), "lender_model.violations", ("absorb", "reclaim")),
           # default False (§10 S32): one site per offered layer, so the public site list depends on
           # neither the horizon nor the offset; True merges layers whose announcement sets over the
           # horizon are identical, which reveals that structure to policies (§6.2)
           "merge_identical_layers": _bool(m.get("merge_identical_layers", False),
                                           "lender_model.merge_identical_layers")}
    if out["on_unavailable"] == "refuse" and sch not in ("trace", "correlated"):
        _fail("lender_model.on_unavailable", f"'refuse' needs schedule 'trace' or 'correlated', not {sch!r} (§6.4)")
    allowed = SCHEDULE_PARAMS[sch]
    p = _obj(m.get("params", {}), "lender_model.params", tuple(allowed))
    par = {}
    for k, d in allowed.items():
        v = p.get(k, None if d == "required" else d)
        path = f"lender_model.params.{k}"
        if d == "required" and v is None:
            _fail(path, f"required for schedule {sch!r}")
        if k in ("D_slots", "Phi", "U") and v is not None:
            v = _int(v, path, 1)
        elif k == "k" and v is not None:
            v = _int(v, path, 1)
        elif k == "delay_slots_max" and v is not None:
            v = _int(v, path, 0)
        elif k in ("p", "p_sh"):
            v = _num(v, path, 0.0, 1.0)
        elif k == "groups" and v is not None:
            v = _choice(v, path, ("all", "none", "region"))      # 'region': MS7 C54 (lender._correlated)
        par[k] = v
    out["params"] = par
    return out


def _slo_map(m, path: str, regions, tiers) -> Optional[dict]:
    if m is None:
        return None
    if not isinstance(m, dict):
        _fail(path, "expected an object '<region>:<tier>' | '<region>' | '<tier>' -> slo class")
    for k, v in m.items():
        parts = k.split(":")
        ok = (len(parts) == 2 and parts[0] in regions and parts[1] in tiers) or \
             (len(parts) == 1 and (k in regions or k in tiers))
        if not ok:
            _fail(path, f"key {k!r} is not '<region>:<tier>', '<region>' or '<tier>'")
        _choice(v, f"{path}.{k}", SLO_CLASSES)
    return dict(m)


def _default_series_tier(name: str) -> Optional[str]:
    """Design Table 5.5: Azure -> M; BurstGPT ChatGPT -> M, GPT-4 -> L; unsplit BurstGPT: none."""
    if name.startswith("azure"):
        return "M"
    if "__ChatGPT__" in name:
        return "M"
    if "__GPT-4__" in name:
        return "L"
    return None


def _overflow_common(b: dict, path: str) -> dict:
    return {"own_capacity_quantile": _num(b.get("own_capacity_quantile", 75), f"{path}.own_capacity_quantile", 0.0, 100.0),
            "smoothing_min": _int(b.get("smoothing_min", 15), f"{path}.smoothing_min", 1),
            "market_tightness": _num(b.get("market_tightness", 0.5), f"{path}.market_tightness", 0.0, lo_open=True)}


def _tier_llm(llms: list[dict], tier: str, path: str) -> str:
    ids = [x["id"] for x in llms if x["tier"] == tier]
    if len(ids) != 1:
        _fail(path, f"tier {tier!r} must appear exactly once among llms[].tier (found {ids})")
    return ids[0]


def _oos_borrowers(b: dict, regions, names) -> dict:
    """The MS7 keys of the regional model (C55; module docstring) that are set, validated: p_o_week (an index of
    traces.borrowers.wildchat_weeks()), demand_fit ({xi_sources, horizon_min, start_minute_of_week}, every region with
    an explicit series and offset: no draw) and gamma (> 0). The returned dict holds only the keys given."""
    out = {}
    if b.get("p_o_week") is not None:
        n = len(tb.wildchat_weeks())
        out["p_o_week"] = _int(b["p_o_week"], "borrowers.p_o_week", 0, n - 1)
    if b.get("demand_fit") is not None:
        f = _obj(b["demand_fit"], "borrowers.demand_fit", DEMAND_FIT_KEYS)
        xs = f.get("xi_sources")
        if not isinstance(xs, dict):
            _fail("borrowers.demand_fit.xi_sources", "required: an object region -> {series, offset_min}")
        miss = [o for o in regions if o not in xs]
        if miss:
            _fail("borrowers.demand_fit.xi_sources", f"no source for region(s) {miss}")
        src = {}
        for o, v in xs.items():
            _choice(o, "borrowers.demand_fit.xi_sources", regions)
            v = _obj(v, f"borrowers.demand_fit.xi_sources.{o}", ("series", "offset_min"))
            s = _choice(v.get("series"), f"borrowers.demand_fit.xi_sources.{o}.series", names)
            src[o] = {"series": s, "offset_min": _int(v.get("offset_min"), f"borrowers.demand_fit.xi_sources.{o}."
                                                                         "offset_min (explicit)", 0)}
        if "horizon_min" not in f:
            _fail("borrowers.demand_fit.horizon_min", "required")
        out["demand_fit"] = {"xi_sources": {o: src[o] for o in regions},
                             "horizon_min": _int(f["horizon_min"], "borrowers.demand_fit.horizon_min", 1),
                             "start_minute_of_week": _int(f.get("start_minute_of_week", 0),
                                                          "borrowers.demand_fit.start_minute_of_week", 0,
                                                          MIN_PER_WEEK - 1)}
    if b.get("gamma") is not None:
        out["gamma"] = _num(b["gamma"], "borrowers.gamma", 0.0, lo_open=True)
    return out


def _borrowers(b, ctx: dict) -> dict:
    if b is None:
        _fail("borrowers", "required")
    if not isinstance(b, dict) or "model" not in b:
        _fail("borrowers.model", "required: 'regional', 'series' or 'explicit'")
    model = _choice(b["model"], "borrowers.model", ("regional", "series", "explicit"))
    regions, llms = ctx["regions"], ctx["llms"]
    dflt_slo = ctx["default_slo_class"]
    if model == "regional":
        b = _obj(b, "borrowers", REGIONAL_KEYS)
        wm = _choice(b.get("wildchat_model", "early"), "borrowers.wildchat_model", WILDCHAT_MODELS)
        p_o, r_oj = tb.wildchat(wm)
        for o in regions:
            if o not in p_o:
                _fail("regions.list", f"region {o!r} has no WildChat profile (regional borrowers need a4b regions)")
        sS = _num(b.get("s_S", 0.25), "borrowers.s_S", 0.0, 1.0)
        need = set()
        if sS < 1 and any(r_oj[o].get("M", 0) > 0 for o in regions):
            need.add("M")
        if sS < 1 and any(r_oj[o].get("L", 0) > 0 for o in regions):
            need.add("L")
        if sS > 0:
            need.add("S")
        for t in sorted(need):
            _tier_llm(llms, t, "llms")
        xs = b.get("xi_sources", "default")
        names = tb.series_names()
        if xs == "default":
            xs_out = "default"
        else:
            if not isinstance(xs, dict):
                _fail("borrowers.xi_sources", "expected 'default' or an object region -> {series, offset_min}")
            xs_out = {}
            for o in regions:
                if o not in xs:
                    _fail("borrowers.xi_sources", f"no source for region {o!r}")
            for o, v in xs.items():
                _choice(o, "borrowers.xi_sources", regions)
                v = _obj(v, f"borrowers.xi_sources.{o}", ("series", "offset_min"))
                s = _choice(v.get("series"), f"borrowers.xi_sources.{o}.series", names)
                off = v.get("offset_min", "random")
                if off != "random":
                    off = _int(off, f"borrowers.xi_sources.{o}.offset_min", 0)
                xs_out[o] = {"series": s, "offset_min": off}
            xs_out = {o: xs_out[o] for o in regions}
        out = {"model": model, "wildchat_model": wm, "s_S": sS, "xi_sources": xs_out,
               **_overflow_common(b, "borrowers"),
               "slo_class": _slo_map(b.get("slo_class"), "borrowers.slo_class", regions, ["S", "M", "L"])}
        out.update(_oos_borrowers(b, regions, names))       # MS7 C55: only the keys that are set
        return out
    if model == "series":
        b = _obj(b, "borrowers", ("model", "list", "own_capacity_quantile", "smoothing_min", "market_tightness",
                                  "merge", "normalize"))
        lst = b.get("list")
        if not isinstance(lst, list) or not lst:
            _fail("borrowers.list", "required: a non-empty list")
        names = tb.series_names()
        out_l, ids = [], set()
        for i, x in enumerate(lst):
            path = f"borrowers.list[{i}]"
            x = _obj(x, path, ("id", "series", "week_index", "tier", "region", "slo_class"))
            bid = _str(x.get("id"), f"{path}.id")
            if bid in ids:
                _fail(f"{path}.id", f"duplicate borrower id {bid!r}")
            ids.add(bid)
            s = _choice(x.get("series"), f"{path}.series", names)
            wk = x.get("week_index")
            if wk is not None:
                wk = _int(wk, f"{path}.week_index", 0)
            tier = x.get("tier") or _default_series_tier(s)
            if tier is None:
                _fail(f"{path}.tier", f"series {s!r} mixes ChatGPT and GPT-4: give its tier")
            _tier_llm(llms, tier, f"{path}.tier")
            if "region" not in x:
                _fail(f"{path}.region", "required")
            reg = _choice(x["region"], f"{path}.region", regions)
            slo = _choice(x.get("slo_class") or dflt_slo, f"{path}.slo_class", SLO_CLASSES)
            out_l.append({"id": bid, "series": s, "week_index": wk, "tier": tier, "region": reg, "slo_class": slo})
        # merge (MS2 C3): true merges the borrowers of one (tier, region, SLO class) into one client;
        # false keeps one client per borrower (siloed runs, design/sim_spec_ms2.md §15.9)
        out = {"model": model, "list": out_l, **_overflow_common(b, "borrowers"),
               "merge": _bool(b.get("merge", True), "borrowers.merge")}
        # normalize (MS4 C24): kept in the resolved config only when it is "mean" (the hashes of "none" are MS3's)
        if _choice(b.get("normalize", "none"), "borrowers.normalize", NORMALIZE) == "mean":
            out["normalize"] = "mean"
        return out
    b = _obj(b, "borrowers", ("model", "clients"))
    cl = b.get("clients")
    if not isinstance(cl, list) or not cl:
        _fail("borrowers.clients", "required: a non-empty list")
    out_c = []
    for i, x in enumerate(cl):
        path = f"borrowers.clients[{i}]"
        x = _obj(x, path, ("llm", "region", "slo_class", "borrowers", "demand"))
        llm = _choice(x.get("llm"), f"{path}.llm", ctx["llm_ids"])
        if "region" not in x:
            _fail(f"{path}.region", "required")
        reg = _choice(x["region"], f"{path}.region", regions)
        slo = _choice(x.get("slo_class") or dflt_slo, f"{path}.slo_class", SLO_CLASSES)
        bor = x.get("borrowers", ["b0"])
        if not isinstance(bor, list) or not bor:
            _fail(f"{path}.borrowers", "expected a non-empty list of borrower ids")
        bor = [_str(v, f"{path}.borrowers") for v in bor]
        d = _obj(x.get("demand"), f"{path}.demand", ("kind", "values", "on_mean_min", "off_mean_min", "level", "seed"))
        kind = _choice(d.get("kind"), f"{path}.demand.kind", ("array", "onoff"))
        if kind == "array":
            v = d.get("values")
            if not isinstance(v, list) or len(v) != ctx["T_fast"]:
                _fail(f"{path}.demand.values", f"expected a list of T_fast = {ctx['T_fast']} values")
            dd = {"kind": "array", "values": [_num(y, f"{path}.demand.values", 0.0) for y in v]}
        else:
            fm = ctx["fast_min"]
            dd = {"kind": "onoff",
                  "on_mean_min": _num(d.get("on_mean_min"), f"{path}.demand.on_mean_min", float(fm)),
                  "off_mean_min": _num(d.get("off_mean_min"), f"{path}.demand.off_mean_min", float(fm)),
                  "level": _num(d.get("level"), f"{path}.demand.level", 0.0),
                  "seed": _int(d.get("seed"), f"{path}.demand.seed", 0)}
        out_c.append({"llm": llm, "region": reg, "slo_class": slo, "borrowers": bor, "demand": dd})
    return {"model": model, "clients": out_c}


def _beta_jl(b, llm_ids) -> Union[float, dict]:
    """costs.beta_jl_usd: a number (one fee for every (j, l)) or, MS3 C10, an object {LLM id: USD} that gives
    every LLM and no other id; resolved in the order of llms[]."""
    if not isinstance(b, dict):
        return _num(b, "costs.beta_jl_usd", 0.0)
    miss = [x for x in llm_ids if x not in b]
    extra = [x for x in b if x not in llm_ids]
    if miss or extra:
        _fail("costs.beta_jl_usd", f"must give every LLM (missing {miss}, unknown {extra})")
    return {x: _num(b[x], f"costs.beta_jl_usd.{x}", 0.0) for x in llm_ids}


def _costs(c, llm_ids) -> dict:
    c = _obj(c, "costs", ("phi", "beta_jl_usd", "kappa_infinite"))
    return {"phi": _num(c.get("phi", 1.0), "costs.phi", 0.0),
            "beta_jl_usd": _beta_jl(c.get("beta_jl_usd", 0.0), llm_ids),
            "kappa_infinite": _bool(c.get("kappa_infinite", False), "costs.kappa_infinite")}


def _stranding(s) -> dict:
    s = _obj(s, "stranding", ("mu_over_beta_tilde", "kv_share", "mu_fl_over_beta_tilde", "pi_over_q", "W_f_min",
                              "beta_tilde_ref"))
    pi = _num(s.get("pi_over_q", 0.0), "stranding.pi_over_q", 0.0)
    if 0 < pi < 1:
        _fail("stranding.pi_over_q", f"must be 0 or >= 1 (design §1.5.5 requires pi >= q), got {pi}")
    # load_time 'median_site' (the name is kept) is the median over the revocable lenders and 'site' needs
    # exactly one revocable lender (§10 S2 revised; the builder checks it)
    ref = _obj(s.get("beta_tilde_ref", {}), "stranding.beta_tilde_ref", ("price", "load_time"))
    return {"mu_over_beta_tilde": _num(s.get("mu_over_beta_tilde", 1.0), "stranding.mu_over_beta_tilde", 0.0),
            "kv_share": _num(s.get("kv_share", 0.0), "stranding.kv_share", 0.0, 1.0),
            "mu_fl_over_beta_tilde": _num(s.get("mu_fl_over_beta_tilde", 0.0), "stranding.mu_fl_over_beta_tilde", 0.0),
            "pi_over_q": pi,
            "W_f_min": _num(s.get("W_f_min", 0), "stranding.W_f_min", 0.0),
            "beta_tilde_ref": {"price": _choice(ref.get("price", "a0"), "stranding.beta_tilde_ref.price", ("a0",)),
                               "load_time": _choice(ref.get("load_time", "median_site"),
                                                    "stranding.beta_tilde_ref.load_time", ("median_site", "site"))}}


def _engine(e) -> dict:
    e = _obj(e, "engine", ENGINE_FIELDS)
    out = {}
    for k, v in e.items():
        out[k] = _num(v, f"engine.{k}", 0.0, lo_open=True) if k == "tol" else _bool(v, f"engine.{k}")
    return out


def _bench(b) -> dict:
    b = _obj(b, "bench", ("grid", "time_limit_s", "mip_rel_gap", "max_vars"))
    return {"grid": _choice(b.get("grid", "slow"), "bench.grid", ("slow", "fast", "slow_lb")),
            "time_limit_s": _num(b.get("time_limit_s", 300.0), "bench.time_limit_s", 0.0, lo_open=True),
            "mip_rel_gap": _num(b.get("mip_rel_gap", 1e-4), "bench.mip_rel_gap", 0.0),
            "max_vars": _int(b.get("max_vars", 200_000), "bench.max_vars", 1)}


# ---------------------------------------------------------------- resolution of "random" and "auto"
def _series_len(e: dict) -> int:
    return len(e["series_values"]) if e["series"] is None else len(tl.slack(e["series"]))


def _resolve_random(out: dict, rng: np.random.Generator) -> None:
    """Draw every "random" / "auto" value with the build stream, in the order of §4.3."""
    t = out["time"]
    T_slow = t["horizon_min"] // t["slow_slot_min"]
    # 1. grid
    if t["start_minute_of_week"] == "random":
        t["start_minute_of_week"] = int(rng.integers(0, MIN_PER_WEEK))
    # 2. lenders: synthetic R from R_rate
    for e in out["lenders"]:
        if e["kind"] == "synthetic" and e["R"] is None:
            e["R"] = np.flatnonzero(rng.random(T_slow) < e["R_rate"]).astype(int).tolist()
    # groups (no draws): series keys by traces.lenders.groups('site_id'), others by their id
    for e in out["lenders"]:
        if e["group"] == "auto":
            e["group"] = tl.group_of(e["series"]) if e["series"] is not None else e["id"]
    # 3. regions of auto lenders: permute their correlation groups, deal them to the regions round-robin
    auto = [e for e in out["lenders"] if e["region"] == "auto"]
    if auto:
        grp = list(dict.fromkeys(e["group"] for e in auto))
        perm = rng.permutation(len(grp))
        regs = out["regions"]["list"]
        reg_of = {grp[g]: regs[i % len(regs)] for i, g in enumerate(perm)}
        for e in auto:
            e["region"] = reg_of[e["group"]]
    # 5. offsets of trace lenders, uniform in [0, len(S_full)) 5-min slots
    for e in out["lenders"]:
        if e["kind"] == "trace" and e["offset"] == "random":
            e["offset"] = int(rng.integers(0, _series_len(e)))
    # 6. load scenarios 'auto': the first ceil(n/2) of a permutation get a5_10GBps, the rest a5_2GBps
    auto = [e for e in out["lenders"] if e["load_scenario"] == "auto"]
    if auto:
        perm = rng.permutation(len(auto))
        n10 = math.ceil(len(auto) / 2)
        for rank, i in enumerate(perm):
            auto[i]["load_scenario"] = DEFAULT_SCENARIOS[0] if rank < n10 else DEFAULT_SCENARIOS[1]
    # 7. demand: offsets of the WildChat fluctuation sources
    b = out["borrowers"]
    if b["model"] == "regional":
        regs = out["regions"]["list"]
        if b["xi_sources"] == "default":
            b["xi_sources"] = {o: {"series": XI_DEFAULT_SOURCES[i % len(XI_DEFAULT_SOURCES)], "offset_min": "random"}
                               for i, o in enumerate(regs)}
        for o in regs:
            v = b["xi_sources"][o]
            if v["offset_min"] == "random":
                v["offset_min"] = int(rng.integers(0, tb.series_length(v["series"])))


# ---------------------------------------------------------------- entry point
def load_config(src: Union[str, Path, dict]) -> dict:
    """Parse, apply defaults (§4.2), validate and resolve; returns the resolved dict."""
    cfg = _read(src)
    _obj(cfg, "", TOP_KEYS)
    if "schema_version" not in cfg:
        _fail("schema_version", "required")
    if _int(cfg["schema_version"], "schema_version") != SCHEMA_VERSION:
        _fail("schema_version", f"must be {SCHEMA_VERSION}")
    name = _str(cfg.get("name"), "name")
    seed = _int(cfg.get("seed", 0), "seed", 0)
    time = _time(cfg.get("time"))
    slow, fast = time["slow_slot_min"], time["fast_slot_min"]
    billing = _choice(cfg.get("billing", "prepaid_D"), "billing", ("prepaid_D", "per_slot", "commit_tau"))
    prices = _prices(cfg.get("prices"))
    contracts = _contracts(cfg, slow)
    llms = _llms(cfg.get("llms"))
    regions = _regions(cfg.get("regions"))
    ctx = {"contracts": contracts, "regions": regions["list"], "llm_ids": [x["id"] for x in llms], "llms": llms,
           "revocable_price": prices["revocable_price"], "T_slow": time["horizon_min"] // slow,
           "T_fast": time["horizon_min"] // fast, "fast_min": fast, "default_slo_class": regions["default_slo_class"],
           "trace_names": tl.all_names()}
    lenders = _lenders(cfg, ctx)
    ppr = _protected_per_region(cfg.get("protected_per_region"), ctx)
    if ppr["enabled"]:
        for o in regions["list"]:
            if f"prot:{o}" in {e["id"] for e in lenders}:
                _fail("protected_per_region", f"lender id 'prot:{o}' is already used")
    if any(e["kind"] == "trace" for e in lenders) and slow not in (1, 5):
        _fail("time.slow_slot_min", f"must be 1 or 5 with trace lenders (5-min slack series), got {slow}")
    if prices["revocable_price"] == "multiplier":
        used = {k for e in lenders if e["kind"] == "trace" for k in e["menu"]}
        miss = [c["id"] for c in contracts if c["tau_min"] is not None and c["id"] in used
                and c["id"] not in prices["multipliers"]]
        if miss:
            _fail("prices.multipliers", f"revocable_price 'multiplier' needs a multiplier for {miss}")
    for k in prices["multipliers"]:
        _choice(k, "prices.multipliers", [c["id"] for c in contracts])
    if not lenders and not ppr["enabled"]:
        _fail("lenders", "no lender: give lenders, lenders_preset or protected_per_region")
    lm = _lender_model(cfg.get("lender_model"))
    borrowers = _borrowers(cfg.get("borrowers"), ctx)
    costs = _costs(cfg.get("costs"), ctx["llm_ids"])
    if costs["kappa_infinite"]:
        fin = [x["id"] for x in llms if x.get("kappa_wtok_per_min") != "inf"]
        if fin:
            _fail("costs.kappa_infinite", f"needs kappa_wtok_per_min 'inf' for every LLM; finite for {fin}")
    out = {"schema_version": SCHEMA_VERSION, "name": name, "seed": seed, "time": time, "billing": billing,
           "prices": prices, "contracts": contracts, "llms": llms, "lenders": lenders,
           "protected_per_region": ppr, "lender_model": lm, "regions": regions, "borrowers": borrowers,
           "costs": costs, "stranding": _stranding(cfg.get("stranding")),
           "units": {"per_replica": _int(_obj(cfg.get("units", {}), "units", ("per_replica",)).get("per_replica", 8),
                                         "units.per_replica", 1)},
           "engine": _engine(cfg.get("engine")), "bench": _bench(cfg.get("bench"))}
    _resolve_random(out, rng_streams(seed)["build"])
    return out
