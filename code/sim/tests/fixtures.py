"""Test fixtures of the Sublet simulator (design/sim_spec.md §9.1).

Config fixtures start from `configs/toy.json`; reference instances are rebuilt in the exact
draw order of the theory check scripts (`core`, `check_c3_benchmark`, `check_c4_lower`,
`fam`), which conftest.py puts on sys.path. Sublet modules are imported inside the
functions, so that a test module needs only the parts of the package it exercises.
"""
from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path
from typing import Optional

import numpy as np

import core
import fam
import check_c4_lower

from sublet.types import INF, Schedule

SIM = Path(__file__).resolve().parents[1]
CONFIGS = SIM / "configs"
TOY_PATH = CONFIGS / "toy.json"
DELETE = object()          # override value that removes a key

A0, Q_GPU = 2.85, 7.15     # toy prices (USD per GPU-hour)


# ---------------------------------------------------------------- numerics
def rel_close(a: float, b: float, tol: float) -> bool:
    """|a - b| <= tol * max(1, |b|) (§9.1)."""
    return abs(a - b) <= tol * max(1.0, abs(b))


def assert_rel(a: float, b: float, tol: float, what: str = "") -> None:
    assert a is not None and b is not None, f"{what}: None value ({a}, {b})"
    assert rel_close(float(a), float(b), tol), f"{what}: {a!r} != {b!r} (tol {tol})"


def assert_arrays_close(a, b, tol: float, what: str = "") -> None:
    """Equal shapes, equal infinite entries, finite entries relatively close."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    assert a.shape == b.shape, f"{what}: shape {a.shape} != {b.shape}"
    ia, ib = np.isinf(a), np.isinf(b)
    assert np.array_equal(ia, ib) and np.array_equal(a[ia], b[ib]), f"{what}: infinite entries differ"
    fa, fb = a[~ia], b[~ib]
    assert np.all(np.abs(fa - fb) <= tol * np.maximum(1.0, np.abs(fb))), f"{what}: {a} != {b}"


# ---------------------------------------------------------------- configs
def load_json(path) -> dict:
    with open(path) as f:
        return json.load(f)


def set_path(cfg: dict, path: str, value) -> None:
    """Set cfg[a][b]...[z] = value for path 'a.b....z'; integer parts index lists.
    Missing dict levels are created; value DELETE removes the key."""
    keys = path.split(".")
    cur = cfg
    for k in keys[:-1]:
        if isinstance(cur, list):
            cur = cur[int(k)]
        else:
            cur = cur.setdefault(k, {})
    last = keys[-1]
    if isinstance(cur, list):
        if value is DELETE:
            del cur[int(last)]
        else:
            cur[int(last)] = value
    elif value is DELETE:
        cur.pop(last, None)
    else:
        cur[last] = value


def apply_overrides(cfg: dict, overrides: Optional[dict] = None, **kw) -> dict:
    """Apply dotted-path overrides in order: first the dict, then the keywords ('__' stands for '.')."""
    for path, value in list((overrides or {}).items()) + [(p.replace("__", "."), v) for p, v in kw.items()]:
        set_path(cfg, path, value if value is DELETE else copy.deepcopy(value))
    return cfg


def toy_config(overrides: Optional[dict] = None, *, sites: Optional[list] = None, **kw) -> dict:
    """Deep copy of configs/toy.json with dotted-path overrides (lender indices refer to the
    original order L0, L1, P) and an optional subset `sites` of lender ids, applied after them."""
    cfg = apply_overrides(load_json(TOY_PATH), overrides, **kw)
    if sites is not None:
        keep = set(sites)
        unknown = keep - {L["id"] for L in cfg["lenders"]}
        assert not unknown, f"unknown lenders {unknown}"
        cfg["lenders"] = [L for L in cfg["lenders"] if L["id"] in keep]
    return cfg


def toy_instance(overrides: Optional[dict] = None, *, sites: Optional[list] = None, **kw):
    from sublet.instance import build_instance
    return build_instance(toy_config(overrides, sites=sites, **kw))


def repeat_fast(values, phi: int) -> list:
    """Demand per fast slot from demand per slow slot (each value repeated phi times)."""
    return [float(v) for v in np.repeat(np.asarray(values, dtype=float), phi)]


def explicit_client(values, llm: str = "M", region: str = "r0", slo: str = "strict", borrower: str = "b0") -> dict:
    return {"llm": llm, "region": region, "slo_class": slo, "borrowers": [borrower],
            "demand": {"kind": "array", "values": [float(v) for v in values]}}


def explicit_llm(id_: str = "M", g: int = 1, kappa="toy") -> dict:
    """An explicit LLM entry like the toy's (tier M); kappa 'toy' keeps the toy's goodput."""
    e = copy.deepcopy(load_json(TOY_PATH)["llms"][0])
    e["id"], e["g"] = id_, int(g)
    if kappa != "toy":
        e["kappa_wtok_per_min"] = kappa
    return e


def inline_trace_lender(values, id_: str = "X", **fields) -> dict:
    """A trace lender with an inline 5-min slack series (`series_values`, §4.2); offset 0,
    region 'r0', explicit load time 300 s and an explicit price 2.85 for the toy's 'short'."""
    L = {"id": id_, "kind": "trace", "series_values": [float(v) for v in values], "region": "r0",
         "group": id_, "menu": ["short"], "prices": {"short": 2.85}, "n_layers": 2, "layer_gpus": 8,
         "lease_size_quantile": 25, "offset": 0, "load_scenario": "explicit", "lam_s": 300.0}
    L.update(fields)
    return L


# ---------------------------------------------------------------- instance patches
def with_capacity(inst, caps: dict):
    """Set Site.capacity_gpus of the given site indices (INF = unlimited); returns inst."""
    sites = list(inst.sites)
    for i, c in caps.items():
        sites[i] = dataclasses.replace(sites[i], capacity_gpus=float(c))
    inst.sites = tuple(sites)
    return inst


def with_stranding(inst, **fields):
    """Replace stranding fields: arrays (or scalars broadcast to (J,)) for mu_kv_usd, mu_fl_usd,
    mu_fb_usd, pi_usd_per_min; W_f_min a float. Returns inst."""
    st = inst.stranding
    kw = {}
    for name in ("mu_kv_usd", "mu_fl_usd", "mu_fb_usd", "pi_usd_per_min"):
        if name in fields:
            kw[name] = np.broadcast_to(np.asarray(fields[name], dtype=float), (inst.J,)).copy()
    if "W_f_min" in fields:
        kw["W_f_min"] = float(fields["W_f_min"])
    inst.stranding = dataclasses.replace(st, **kw)
    return inst


def site_index(inst, site_id: str) -> int:
    ids = [s.id for s in inst.sites]
    assert site_id in ids, f"{site_id} not in {ids}"
    return ids.index(site_id)


def trace_schedule(inst, model=None, seed: int = 0) -> Schedule:
    """The 'trace' schedule of an instance: R_explicit at synthetic sites and the empty set at
    protected sites; instances with layer sites use lender.build_R."""
    if all(s.kind in ("synthetic", "protected") for s in inst.sites):
        empty = np.zeros(0, dtype=np.int64)
        return Schedule("trace", tuple(
            np.asarray(s.R_explicit, dtype=np.int64).copy() if s.kind == "synthetic" and s.R_explicit is not None
            else empty.copy() for s in inst.sites), True)
    from sublet.lender import build_R
    from sublet.types import LenderModel
    model = model or LenderModel()
    return Schedule(model.schedule, tuple(np.asarray(r, dtype=np.int64) for r in
                                          build_R(inst, model, np.random.default_rng(seed))), True)


def empty_schedule(inst) -> Schedule:
    return Schedule("trace", tuple(np.zeros(0, dtype=np.int64) for _ in inst.sites), True)


# ---------------------------------------------------------------- reference instances (§9.1)
def core_params(seed: int) -> dict:
    """Parameter map of core_case (§9.1)."""
    return dict(T=(24, 36)[seed % 2], m=(3, 4)[(seed // 2) % 2], J=(1, 2)[(seed // 4) % 2],
                n=(6, 8)[(seed // 8) % 2], slo=0.7 if seed % 3 == 0 else None)


def core_omega(I, rate: float, seed: int) -> list:
    if rate == 1.0:
        return [np.arange(I.T)] * I.m
    return core.random_omega(np.random.default_rng(7000 + seed), I, rate)


def core_case(seed: int, rate: float):
    """(core.Instance, omega): core.random_instance(default_rng(seed), **core_params(seed)) and
    core.random_omega(default_rng(7000 + seed), I, rate), or every slot at rate 1.0."""
    I = core.random_instance(np.random.default_rng(seed), **core_params(seed))
    return I, core_omega(I, rate, seed)


def c3b_case(seed: int, rate: float):
    """The instances of check_c3_benchmark.run_b (part (b)), with its omega."""
    I = core.random_instance(np.random.default_rng(5000 + seed), T=36, m=4, J=2, n=8,
                             slo=0.7 if seed % 2 else None)
    om = core.random_omega(np.random.default_rng(7000 + seed), I, rate) if rate < 1 else [np.arange(I.T)] * I.m
    return I, om


def c4l_b(beta: float):
    """check_c4_lower part (b): (full-menu instance, revocable-only instance)."""
    I = check_c4_lower.single(48, [(1, 1), (48, 0)], beta, [1.0, 1.3])
    return I, I.subset(contracts=[0])


def c4l_d(b: int):
    """check_c4_lower.part_d_constructed's instance for b borrowers."""
    T = 24
    return core.Instance(T=T, tau=np.array([T]), H=np.array([0]), a=np.array([[1.0]]),
                         beta=np.array([[10.0]]), g=np.array([1]), q=1e3,
                         cl_llm=np.zeros(b, dtype=int), delta=np.zeros((b, 1)),
                         active=np.ones((b, T), dtype=bool), owner=np.arange(b))


def c4l_e(seed: int):
    """check_c4_lower.part_e's instance, in its exact draw order."""
    rng = np.random.default_rng(9300 + seed)
    T = 40
    I = check_c4_lower.single(T, [(1, 0), (3, 1), (10, 6)], float(rng.uniform(1, 6)), [1.0, 0.8, 0.6])
    I.q = float(rng.uniform(2, 8))
    I.active = (rng.random((1, T)) < rng.uniform(0.2, 0.8))
    return I


FAM_SCHEDULES = ("bern0.02", "bern0.2", "iid0.5", "safe")


def fam_case(m: int, rho: float, tau: int, H: int, T: int, sched: str, seed: int):
    """(fam.Fam, omega) with omega drawn from a fresh default_rng(seed) (§9.1)."""
    F = fam.Fam(m, rho, tau, H, T)
    rng = np.random.default_rng(seed)
    if sched.startswith("bern"):
        om = fam.bernoulli_schedule(F, float(sched[4:]), rng)
    elif sched == "iid0.5":
        om = fam.iid_step_schedule(F, 0.5, T // F.D, rng)
    elif sched == "safe":
        if m < 2:
            raise ValueError("the safe-site schedule needs m >= 2")
        k = max(2, m)
        om = fam.safe_site_schedule(F, k, max(1, T // (k * F.D)), rng)[0]
    else:
        raise ValueError(sched)
    return F, [np.asarray(o[o < T], dtype=np.int64) for o in om]


# ---------------------------------------------------------------- single-site DP-domain cases
def _onoff_runs(rng, n: int, level: float, mean_run: float = 3.0) -> np.ndarray:
    """On/off series of length n: alternating geometric runs (mean `mean_run` slots)."""
    d = np.zeros(n)
    t, on = 0, bool(rng.random() < 0.5)
    while t < n:
        L = int(rng.geometric(1.0 / mean_run))
        if on:
            d[t:t + L] = level
        t += L
        on = not on
    return d


def _runs_R(rng, T_s: int, rate: float = 0.2) -> list:
    """Announcement runs of consecutive slots (lengths 1-3), separated by at least one slot."""
    R, t = [], 0
    while t < T_s:
        if rng.random() < rate:
            L = int(rng.integers(1, 4))
            R.extend(range(t, min(T_s, t + L)))
            t += L + 1
        else:
            t += 1
    return R


def single_site_config(T_s: int, fast_min: int, contracts: list, prices: dict, price_prot: float,
                       R: list, lam_rev: float, lam_prot: float, demand, billing: str,
                       mu_ratio: float = 0.0, cap_rev: int = 64) -> dict:
    """One synthetic revocable site 'S0' with the contracts `contracts` [(id, tau_min, H_min)] and
    one protected site 'P' (contract 'prot', prepaid 5 min), one client of the toy LLM (g = 1),
    q = 7.15, delta = 0, beta = 0, slow slot 5 min."""
    cfg = toy_config(sites=["L0", "P"])
    cfg["name"] = "single_site"
    cfg["time"] = {"slow_slot_min": 5, "fast_slot_min": int(fast_min), "horizon_min": 5 * int(T_s),
                   "start_minute_of_week": 0}
    cfg["billing"] = billing
    cfg["prices"]["a_protected_usd_per_gpu_h"] = float(price_prot)
    cfg["contracts"] = [{"id": k, "tau_min": int(t), "H_min": int(h)} for k, t, h in contracts] + \
                       [{"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": 5}]
    L0, P = cfg["lenders"]
    L0.update({"id": "S0", "menu": [k for k, _, _ in contracts],
               "prices": {k: float(prices[k]) for k, _, _ in contracts}, "capacity_gpus": int(cap_rev),
               "R": sorted(set(int(r) for r in R)), "lam_s": float(lam_rev)})
    P.update({"lam_s": float(lam_prot)})
    cfg["borrowers"]["clients"] = [explicit_client(demand)]
    cfg["stranding"]["mu_over_beta_tilde"] = float(mu_ratio)
    return cfg


def _build_single(cfg: dict, unlimited: bool = True, mu_fb: Optional[float] = None):
    from sublet.instance import build_instance, validate
    inst = build_instance(cfg)
    if unlimited:
        with_capacity(inst, {i: INF for i in range(inst.m)})
    if mu_fb is not None:
        with_stranding(inst, mu_fb_usd=mu_fb)
    validate(inst)
    return inst, trace_schedule(inst)


_KIND_ID = {"bern": 1, "runs": 2, "near": 3, "fast": 4}


def single_site_case(seed: int, grid: str = "slow", kind: Optional[str] = None):
    """(Instance, Schedule) of the random DP-domain generator of test_dp_equals_milp_single_site.

    kind 'bern' (grid 'slow'): T_s in [24, 48], revocable (1 slot, 5 min) and (2 slots, 15 min) at
      one site, protected (prepaid 5 min) at another, R Bernoulli(0.15), lambda in {0, 300, 600} s,
      on/off demand of level 0.5 or 1, mu_fb / beta~ in {0, 1, 2}, billing prepaid_D or per_slot.
    kind 'runs' (grid 'slow'): as 'bern' with R made of runs of consecutive slots (lengths 1-3),
      H in {0, 2, 5} min and lambda in {600, 900} s, so that several leases load at once.
    kind 'near' (grid 'slow'): near the fixed instance of §7.6: T_s in [14, 18], contracts (1 slot,
      5 min) and (2 slots, 5 min) at 2.6-3.8 USD/GPU-h, protected 4.3-7.0, lambda in {600, 900} s,
      mu_fb in {0.3, 0.6, 1.2} USD, demand on with probability 0.85, R with a run of announcements
      in the second half, prepaid_D.
    kind 'fast' (grid 'fast': Delta_s = 5, Delta_f = 1): T_s in [8, 16], contracts (1 slot, H) with
      H = 2 (even seeds) or 7 (odd seeds) min and (2 slots, H') with H' in {0, 2, 7}, lambda in
      {0, 120, 300, 420} s, per-minute on/off demand, billing prepaid_D, per_slot or commit_tau.
    Capacities are unlimited (patched to INF after the build)."""
    kind = kind or ("bern" if grid == "slow" else "fast")
    if (kind == "fast") != (grid == "fast"):
        raise ValueError(f"kind {kind!r} does not fit grid {grid!r}")
    rng = np.random.default_rng([seed, _KIND_ID[kind]])
    mu_fb = None
    if kind in ("bern", "runs"):
        T_s = int(rng.integers(24, 49))
        if kind == "bern":
            contracts = [("r1", 5, 5), ("r2", 10, 15)]
            R = list(np.flatnonzero(rng.random(T_s) < 0.15))
            lam = [float(rng.choice([0.0, 300.0, 600.0])) for _ in range(2)]
        else:
            contracts = [("r1", 5, int(rng.choice([0, 2, 5]))), ("r2", 10, int(rng.choice([0, 2, 5])))]
            R = _runs_R(rng, T_s)
            lam = [float(rng.choice([600.0, 900.0])) for _ in range(2)]
        level = float(rng.choice([0.5, 1.0]))
        demand = _onoff_runs(rng, T_s, level)
        mu_ratio = float(rng.choice([0.0, 1.0, 2.0]))
        billing = str(rng.choice(["prepaid_D", "per_slot"]))
        prices = {"r1": float(rng.uniform(2.6, 3.8)), "r2": float(rng.uniform(2.6, 3.8))}
        price_prot = float(rng.uniform(4.3, 7.0))
        fast_min = 5
    elif kind == "near":
        T_s = int(rng.integers(14, 19))
        contracts = [("r1", 5, 5), ("r2", 10, 5)]
        prices = {"r1": float(rng.uniform(2.6, 3.8)), "r2": float(rng.uniform(2.6, 3.8))}
        price_prot = float(rng.uniform(4.3, 7.0))
        lam = [float(rng.choice([600.0, 900.0])) for _ in range(2)]
        mu_fb = float(rng.choice([0.3, 0.6, 1.2]))
        demand = np.where(rng.random(T_s) < 0.85, 1.0, 0.0)
        st = int(rng.integers(T_s // 2, T_s - 2))
        run = list(range(st, min(T_s, st + int(rng.integers(2, 5)))))
        R = sorted(set(run) | set(np.flatnonzero(rng.random(T_s) < 0.15)))
        mu_ratio, billing, fast_min = 0.0, "prepaid_D", 5
    else:   # fast
        T_s = int(rng.integers(8, 17))
        contracts = [("r1", 5, 2 if seed % 2 == 0 else 7), ("r2", 10, int(rng.choice([0, 2, 7])))]
        prices = {"r1": float(rng.uniform(2.6, 3.8)), "r2": float(rng.uniform(2.6, 3.8))}
        price_prot = float(rng.uniform(4.3, 7.0))
        R = list(np.flatnonzero(rng.random(T_s) < 0.2))
        lam = [float(rng.choice([0.0, 120.0, 300.0, 420.0])) for _ in range(2)]
        level = float(rng.choice([0.5, 1.0]))
        demand = _onoff_runs(rng, 5 * T_s, level, mean_run=8.0)
        mu_ratio = float(rng.choice([0.0, 1.0, 2.0]))
        billing = str(rng.choice(["prepaid_D", "per_slot", "commit_tau"]))
        fast_min = 1
    cfg = single_site_config(T_s, fast_min, contracts, prices, price_prot, R, lam[0], lam[1], demand,
                             billing, mu_ratio)
    return _build_single(cfg, unlimited=True, mu_fb=mu_fb)


FIXED_76_DEMAND = (1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0)


def fixed_76_case(unlimited: bool = True):
    """The fixed instance of §7.6 / §9.2: T_s = 16, revocable site with R = {2, 7, 12, 13, 14} and
    contracts (1 slot, 5 min, 3.505) and (2 slots, 5 min, 2.893), protected site (prepaid 5 min,
    4.748), lambda = 600 s at both, g = 1, q = 7.15, delta = beta = 0, mu_fb = 1 USD, prepaid_D,
    unlimited capacity (with unlimited=False the revocable site keeps 64 GPUs)."""
    cfg = single_site_config(16, 5, [("r1", 5, 5), ("r2", 10, 5)], {"r1": 3.505, "r2": 2.893}, 4.748,
                             [2, 7, 12, 13, 14], 600.0, 600.0, FIXED_76_DEMAND, "prepaid_D")
    return _build_single(cfg, unlimited=unlimited, mu_fb=1.0)


# ---------------------------------------------------------------- random toy variants and plans
BILLING = ("prepaid_D", "per_slot", "commit_tau")


def random_toy_config(rng, *, fast_min: Optional[int] = None, billing: Optional[str] = None,
                      lam: Optional[float] = None, n_clients: Optional[int] = None, two_llms: bool = False,
                      demand_hi: float = 2.0, p_on: float = 0.7, R_rate: float = 0.25) -> dict:
    """A toy variant: random R at L0 and L1, load times, billing mode, fast slot (5 or 1 min) and
    demand of one or two clients (uniform in [0, demand_hi] with probability p_on per fast slot).
    With two_llms the clients alternate between M (g = 1) and M2 (g = 2)."""
    fast = int(fast_min or rng.choice([5, 1]))
    T_s = 24
    T_f = T_s * (5 // fast)
    cfg = toy_config()
    cfg["time"]["fast_slot_min"] = fast
    cfg["billing"] = str(billing or rng.choice(BILLING))
    for i in (0, 1):
        cfg["lenders"][i]["R"] = [int(x) for x in np.flatnonzero(rng.random(T_s) < R_rate)]
    for i in (0, 1, 2):
        cfg["lenders"][i]["lam_s"] = float(lam if lam is not None else rng.choice([0.0, 300.0]))
    names = ["M"]
    if two_llms:
        cfg["llms"] = [explicit_llm("M", 1), explicit_llm("M2", 2)]
        names = ["M", "M2"]
    n = int(n_clients or rng.integers(1, 3))
    clients = []
    for c in range(n):
        d = np.where(rng.random(T_f) < p_on, rng.uniform(0.0, demand_hi, T_f), 0.0)
        clients.append(explicit_client(np.round(d, 3), names[c % len(names)], borrower=f"b{c}"))
    cfg["borrowers"]["clients"] = clients
    return cfg


def random_plan(inst, rng, n_max: int = 6, admission: bool = True) -> list:
    """Random PlannedLeases (any site, offered contract, LLM; release after the purchase slot or
    never; n in {1, 2}; optional admission_off intervals, sorted, disjoint and non-adjacent)."""
    from sublet.types import PlannedLease
    T_s, phi = inst.grid.T_slow, inst.grid.phi
    plan = []
    for _ in range(int(rng.integers(1, n_max + 1))):
        site = int(rng.integers(inst.m))
        k = int(rng.choice(list(inst.sites[site].menu)))
        j = int(rng.integers(inst.J))
        s = int(rng.integers(0, T_s))
        rel = None if (s == T_s - 1 or rng.random() < 0.5) else int(rng.integers(s + 1, T_s))
        adm = []
        if admission and rng.random() < 0.4:
            hi = (rel if rel is not None else T_s) * phi
            pts = sorted(set(int(x) for x in rng.integers(s * phi, hi + 1, size=4)))
            for a, b in zip(pts[0::2], pts[1::2]):
                if b > a and (not adm or a > adm[-1][1]):
                    adm.append((a, b))
        plan.append(PlannedLease(site, k, j, s, rel, int(rng.integers(1, 3)), tuple(adm)))
    return plan


def full_variant(i: int):
    """Toy variant i of test_fixedplan_replays_milp_full: lambda = 300 s, two clients with demand in
    [0, 1] (two LLMs for odd i), the toy's finite capacities, mu = 0, Delta_f = Delta_s."""
    from sublet.instance import build_instance
    rng = np.random.default_rng([i, 31])
    cfg = random_toy_config(rng, fast_min=5, lam=300.0, n_clients=2, two_llms=bool(i % 2), demand_hi=1.0,
                            p_on=0.75)
    cfg["stranding"]["mu_over_beta_tilde"] = 0.0
    inst = build_instance(cfg)
    assert not inst.stranding.mu_fb_usd.any() and not inst.stranding.mu_kv_usd.any()
    return inst, trace_schedule(inst)


# ---------------------------------------------------------------- recording policy
def recording_policy(script=None, fast_script=None, wants_fast: bool = False):
    """A policy that replays a script and records what it observes.

    script: {t: list of actions, or callable(obs, policy) -> list}; fast_script likewise keyed by
    fast slot f (only Drain / SetAdmission). Records per slow slot: t, lease ids in obs.leases,
    notices, ended, results and site_announced; per fast slot: f and results."""
    from sublet.policies.base import Policy

    class Recorder(Policy):
        name = "recorder"

        def __init__(self):
            self.script = dict(script or {})
            self.fast_script = dict(fast_script or {})
            self._wants_fast = bool(wants_fast or fast_script)
            self.slow, self.fast, self.view = [], [], None

        def reset(self, view, rng):
            self.view = view
            self.slow, self.fast = [], []
            self.wants_fast = self._wants_fast

        def act(self, obs):
            self.slow.append(dict(
                t=obs.t, minute=obs.minute, leases=dict(obs.leases), replicas=dict(obs.replicas),
                notices=list(obs.notices), ended=list(obs.ended), results=list(obs.results),
                site_announced=None if obs.site_announced is None else np.array(obs.site_announced, copy=True)))
            a = self.script.get(obs.t, [])
            return list(a(obs, self) if callable(a) else a)

        def on_fast(self, obs):
            self.fast.append(dict(f=obs.f, results=list(obs.results)))
            a = self.fast_script.get(obs.f, [])
            return list(a(obs, self) if callable(a) else a)

    return Recorder()


# ================================================================ MS2 (design/sim_spec_ms2.md §17.1)
# Reference instances of the MS2 checks, rebuilt in the exact draw order of the reference scripts.
# Import-safe reference modules (check_c3_upper, check_c5_la, o1_ub) are imported inside the
# functions; c3/audit/a2_P_equiv_and_termination.py runs on import (§0 rule 5) and is transcribed.

UPPER_FAMS = ("rand", "slo", "setcover", "spiky", "big")      # check_c3_upper families, seeds 0-11
UPPER_SEEDS = tuple(range(12))
AUDIT_TAGS = {"rand": (None, False), "slo": (0.4, False), "ties": (None, True)}   # tag -> (slo, tie)
CM_ROWS = tuple((m, rho) for m in (2, 3, 4, 6) for rho in (2, 4, 8, 16))     # check_c4_lower part (a)
# o1_ub.main's job list, in its order: (m, rho, tau, H, seed) with T = 96
O1_JOBS = tuple((m, rho, tau, H, seed) for m in (2, 3, 5, 8) for rho in (2, 8, 32)
                for (tau, H) in ((1, 0), (2, 1), (1, 3)) for seed in range(2))
O1_T = 96


def upper_case(fam_name: str, seed: int):
    """check_c3_upper.make(fam, seed): the core instances of check 2a (families UPPER_FAMS, seeds 0-11)."""
    import check_c3_upper
    return check_c3_upper.make(fam_name, seed)


def audit_case(tag: str, seed: int):
    """The families of c3/audit/a2_P_equiv_and_termination.py part (2) (lines 67-74, transcribed: the
    module runs its audit on import): random_instance(default_rng(700 + seed), T=24, m=6 if tie else 4,
    J=1, n=6, K=3, slo=0.4 for 'slo'); for 'ties' delta[:] = 0.05, beta[:] = 5.0, a[:] = 1.0. Seeds 0-5."""
    slo, tie = AUDIT_TAGS[tag]
    rng = np.random.default_rng(700 + seed)
    I = core.random_instance(rng, T=24, m=6 if tie else 4, J=1, n=6, K=3, slo=slo)
    if tie:
        I.delta[:] = 0.05
        I.beta[:] = 5.0
        I.a[:] = 1.0
    return I


@dataclasses.dataclass(frozen=True, eq=False)
class C5Pred:
    """One prediction of c5_case: noise kind and parameter, predicted core instance, predicted plan."""
    kind: str
    par: float
    Ip: object                 # core.Instance with the predicted activity mask
    P: tuple                   # predicted columns (l, j, k, s) = drivers.predict.plan_core(Ip)


_C5_CACHE: dict = {}


def c5_case(seed: int):
    """(I, preds) of check_c5_la.job(seed) and check_c5_la_nearest.job(seed): I =
    random_instance(default_rng(11000 + seed), T=36, m=4, J=2, n=8); preds[i] for the i-th entry of
    check_c5_la.NOISE, each mask drawn with a fresh default_rng(12000 + seed) (check_c5_la.py:54; a
    generator shared across the nine would change the second and third flip masks, §13.2), and P-hat
    = drivers.predict.plan_core(Ip) (the reference's core.opt_eager_cols of a MILP). Cached per seed
    (nine MILPs); callers must not modify the returned objects."""
    if seed in _C5_CACHE:
        return _C5_CACHE[seed]
    import check_c5_la
    from sublet.drivers.predict import plan_core
    I = core.random_instance(np.random.default_rng(11000 + seed), T=36, m=4, J=2, n=8)
    preds = []
    for kind, par in check_c5_la.NOISE:
        Ip = check_c5_la.predicted(I, kind, par, np.random.default_rng(12000 + seed))
        preds.append(C5Pred(kind, par, Ip, tuple(tuple(int(v) for v in col) for col in plan_core(Ip))))
    _C5_CACHE[seed] = (I, tuple(preds))
    return _C5_CACHE[seed]


def o1_case(m: int, rho: float, tau: int, H: int, seed: int, T: int = O1_T):
    """(fam.Fam(m, rho, tau, H, T), [(name, omega)]) with omega from o1_ub.schedules(F, default_rng(seed))
    (bern0.005 ... bern0.500, safe, iid0.5, onesite, adaptiveRR, in that order), every set truncated
    to [0, T) as int64 (adaptiveRR's last announcement can lie at or past T)."""
    import o1_ub
    F = fam.Fam(m, rho, tau, H, T)
    out = []
    for name, om in o1_ub.schedules(F, np.random.default_rng(seed)):
        out.append((name, [np.asarray(o, dtype=np.int64)[np.asarray(o, dtype=np.int64) < T] for o in om]))
    return F, out


def cm_case(m: int, rho: float):
    """check_c4_lower.cm_instance(m, rho): the cat-and-mouse instance of part (a) (T = 48, tau = 2, H = 1, a = 1)."""
    return check_c4_lower.cm_instance(m, rho)


def onesite_c2(demand, R=(), *, slot_min: int = 5, rev_contracts=None, tau_slots: int = 1, H_min: int = 5,
               a_rev: float = A0, a_prot: float = 5.97, lam_rev: float = 300.0, lam_prot: float = 300.0,
               mu_over_beta_tilde: float = 1.0, q_gpu: float = Q_GPU, a0: float = A0, prot_prepaid_min=None,
               billing: str = "prepaid_D", cap_rev=None, mu_fb: Optional[float] = None):
    """(Instance, Schedule) of a synthetic single-site instance for A1 (§9.4): one synthetic revocable
    site 'R' (explicit announcement set R, capacity cap_rev or unlimited), one protected site 'P'
    (contract 'prot', prepaid prot_prepaid_min, default one slot), one client of the toy LLM (g = 1,
    q = q_gpu) in region r0 with demand `demand` per slot (Δs = Δf = slot_min), delta = beta_jl = 0,
    phi = 1, explicit load times lam_rev and lam_prot (seconds). The revocable menu is rev_contracts,
    a list of (id, tau_min, H_min, price), default [('rev', tau_slots * slot_min, H_min, a_rev)].
    mu_fb (USD) replaces the builder's mu_fb = mu_over_beta_tilde * beta_tilde_ref if given."""
    from sublet.instance import build_instance, validate
    T_s = len(demand)
    rev = rev_contracts if rev_contracts is not None else [("rev", tau_slots * slot_min, H_min, a_rev)]
    cfg = toy_config(sites=["L0", "P"])
    cfg["name"] = "onesite_c2"
    cfg["time"] = {"slow_slot_min": int(slot_min), "fast_slot_min": int(slot_min), "horizon_min": int(slot_min) * T_s,
                   "start_minute_of_week": 0}
    cfg["billing"] = billing
    cfg["prices"] = {"a0_usd_per_gpu_h": float(a0), "q_gpu_usd_per_gpu_h": float(q_gpu),
                     "a_protected_usd_per_gpu_h": float(a_prot), "revocable_price": "explicit"}
    cfg["contracts"] = [{"id": k, "tau_min": int(t), "H_min": int(h)} for k, t, h, _ in rev] + \
                       [{"id": "prot", "tau_min": None, "H_min": 0,
                         "prepaid_min": int(slot_min if prot_prepaid_min is None else prot_prepaid_min)}]
    L0, P = cfg["lenders"]
    L0.update({"id": "R", "group": "gR", "menu": [k for k, _, _, _ in rev], "prices": {k: float(a) for k, _, _, a in rev},
               "capacity_gpus": 1000 if cap_rev is None else cap_rev, "R": sorted(set(int(r) for r in R)),
               "lam_s": float(lam_rev)})
    P.update({"lam_s": float(lam_prot), "menu": ["prot"]})
    cfg["borrowers"]["clients"] = [explicit_client([float(v) for v in demand])]
    cfg["stranding"]["mu_over_beta_tilde"] = float(mu_over_beta_tilde)
    inst = build_instance(cfg)
    if cap_rev is None:
        with_capacity(inst, {0: INF})
    if mu_fb is not None:
        with_stranding(inst, mu_fb_usd=mu_fb)
    validate(inst)
    return inst, trace_schedule(inst)


# ---------------------------------------------------------------- MS2 helpers
def policy_actions_recorder(policy):
    """Wrap `policy` so that every action list it returns (act and on_fast) is recorded in
    wrapper.actions as (slot or ('fast', f), action); reset, wants_fast, params and report pass through."""
    from sublet.policies.base import Policy

    class ActionRecorder(Policy):
        def __init__(self, inner):
            self.inner = inner
            self.name = getattr(inner, "name", type(inner).__name__)
            self.actions: list = []

        def reset(self, view, rng):
            self.inner.reset(view, rng)
            self.wants_fast = bool(getattr(self.inner, "wants_fast", False))

        def act(self, obs):
            out = list(self.inner.act(obs))
            self.actions += [(obs.t, a) for a in out]
            return out

        def on_fast(self, obs):
            out = list(self.inner.on_fast(obs))
            self.actions += [(("fast", obs.f), a) for a in out]
            return out

        def params(self):
            return self.inner.params()

        def report(self):
            return self.inner.report()

    return ActionRecorder(policy)


def capped_toy_instance():
    """The toy with 1-GPU sites L0 and L1 (R empty) and client 0 at demand 2.0: purchases of the PD's
    capacity layers beyond the first are dropped by the pre-check (refusals of §6.5)."""
    cfg = toy_config({"lenders.0.capacity_gpus": 1, "lenders.1.capacity_gpus": 1, "lenders.0.R": [],
                      "lenders.1.R": []})
    cfg["borrowers"]["clients"][0]["demand"]["values"] = [2.0] * 24
    from sublet.instance import build_instance
    return build_instance(cfg)


def refusal_recorder(pol) -> dict:
    """Wrap pol.reset of a policy with an execution layer `pol.layer` and a planner `pol.planner` (A3, A6)
    so that the run records the layer's staged purchases (t, slot key, kind), its opened windows
    (slot key, t0, s, L) and the planner's refused columns (t, slot key, s0, L). Returns the dict of the
    three lists, filled during the run."""
    rec: dict = {"staged": [], "opened": [], "refused": []}
    o_reset = pol.reset

    def reset(view, rng):
        o_reset(view, rng)
        lay, pl = pol.layer, pol.planner
        o_stage, o_open, o_ref = lay._stage_buy, lay.open, pl.refuse

        def _stage_buy(sl, site, contract, t, kind, tag, obs):
            rec["staged"].append((int(t), sl.key, kind))
            return o_stage(sl, site, contract, t, kind, tag, obs)

        def open_(key, t0, s, L):
            rec["opened"].append((tuple(int(x) for x in key), int(t0), int(s), int(L)))
            return o_open(key, t0, s, L)

        def refuse(col, t, reason=""):
            l, j, k, s0, iota, L = pl.column(col)
            rec["refused"].append((int(t), (l, j, k, iota), int(s0), int(L)))
            return o_ref(col, t, reason)
        lay._stage_buy, lay.open, pl.refuse = _stage_buy, open_, refuse
    pol.reset = reset
    return rec


def purchases_in_refused_windows(rec: dict) -> list:
    """Staged purchases of a logical slot at slots t in [t_ref, s0 + L) of a column of that slot refused at
    t_ref that no other opened window of the slot covers (M11, no retry of a refused column: must be
    empty). Entries (t_ref, slot key, s0, L, t, kind)."""
    bad = []
    for t_ref, key, s0, L in rec["refused"]:
        for t, k2, kind in rec["staged"]:
            if k2 != key or not t_ref <= t < s0 + L:
                continue
            if not any(w[0] == key and w[2] != s0 and w[1] <= t < w[2] + w[3] for w in rec["opened"]):
                bad.append((t_ref, key, s0, L, t, kind))
    return bad


def lease_cost(components: dict) -> float:
    """lease_prepaid + lease_rent + loading of a run's components."""
    return components["lease_prepaid"] + components["lease_rent"] + components["loading"]


def ms2_checks_dir() -> Path:
    """Folder of the informative MS2 outputs written by tests (conftest.MS2_CHECKS_DIR)."""
    import os
    return Path(os.environ.get("SUBLET_MS2_CHECKS_DIR") or (SIM / "out" / "ms2_checks"))


# ---------------------------------------------------------------- Q44 guard (design/q44_practical_sublet.md §3.6, §6.3)
def g6_case(n: int, active_slots=(1,)):
    """Proposition G6's core instance I_n: one site, one LLM, one contract with tau = 1, H = 1 (D = 2),
    g = a = beta = 1 (so C = 3), q = 2, n co-located clients with delta = 0, T = 2, every client active
    in the slots of `active_slots` only."""
    T = 2
    act = np.zeros((n, T), dtype=bool)
    for t in active_slots:
        act[:, int(t)] = True
    return core.Instance(T=T, tau=np.array([1]), H=np.array([1]), a=np.array([[1.0]]), beta=np.array([[1.0]]),
                         g=np.array([1]), q=2.0, cl_llm=np.zeros(n, dtype=int), delta=np.zeros((n, 1)), active=act)


def c3p5_case(beta: float, T: int = 48):
    """The C3-P5 insurance instance of family F3 (check_c4_lower.part_b at horizon T):
    check_c4_lower.single(T, [(1, 1), (T, 0)], beta, [1.0, 1.3]) (full menu, q = 1e4)."""
    return check_c4_lower.single(int(T), [(1, 1), (int(T), 0)], beta, [1.0, 1.3])
