"""Tests of the naive spend cap CAP (design/ms8/plan.md D2, X6; sublet/algos/budget_cap.py) and of its registry row.

Quick (no raw data):
- the registry: CAP in registry.MS8 (MS8_IDS == ('CAP',)), not in POLICY_IDS, MS5B or MS7 (their pins unchanged),
  make_policy builds it, info class online-I1, no driver input; the parameter checks (X, count, on_bind, inner,
  inner_params, an inner that uses on_fast);
- X = 1e18 reproduces the inner policy alone bit for bit (ledger components, lease records and the inner's report) for
  A9, BL1 and BL5 on configs/toy.json under the trace lender and i.i.d. announcements, for every count and on_bind;
- Proposition N (design/theory/naive_caps.md) through the engine: on I_n the 'paid' cap pays 3n, the 'slot' cap 2n and
  A8P ('lb') 2n; on J_T the 'stop' caps pay T (linear in T), the latching caps X + 3 ('paid') and X + 2 ('slot'), A8P 3
  = FB + B(T) (K0 releases the lease); on K_n (stranding mu^fb, eager lender, tau = 1 slot) every cap pays FB + n mu,
  while A8P stays at or below FB + B(T) and at its constant allowance B0 = X below FB + X; on U_n (a lease at a site
  no client can use, priced Q(0), core model) no cap binds and every cap pays 2 n q against FB = n q (the 'slot' count
  prices the slot's service at 0), while A8P at B0 = X drops the purchase once n q > X;
- latch semantics (one release of every held lease, the inner never called again) and stop semantics (Buys dropped,
  Releases kept, the inner's results remapped with reason 'cap');
- the allowances: X(t) = B(t) of OnlineLB ('lb'; X(T) equals Sublet's B_T on the same instance), eps FB(t - 1)
  ('rel:<eps>'), a constant; FB(T) = BL0a; the cap's test reads the engine's observation, not the inner's copy.
With the a12 outputs (needs_a12): X = 1e18 reproduces A9 and BL1 on the reduced cell bench_e7f 101 (2 hours, L-tr and
L-eg), and the CR-cap-B and Sublet runs there have the same B(T).
"""
import dataclasses
import hashlib
import json

import numpy as np
import pytest

from fixtures import g6_case, toy_config

from sublet.algos import registry
from sublet.algos.budget_cap import BudgetCapped, parse_X
from sublet.algos.common import PolicyError
from sublet.algos.guard import ProjectedGuarded, fallback_by_client
from sublet.algos.online_lb import series
from sublet.drivers.run import make_policy
from sublet.engine import EngineConfig, simulate
from sublet.instance import build_instance, from_core, public_view
from sublet.policies.base import Policy
from sublet.types import Buy, LenderModel, Release

import core

IID = {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.3}}
SUB = {"inner": "A9", "project": True, "allowance": "lb", "kappa": None}
CAPS = (("paid", "stop"), ("paid", "latch"), ("slot", "stop"), ("slot", "latch"))
TOL = 1e-9


# ---------------------------------------------------------------- helpers
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


def _ledger(res) -> str:
    """sha256 of the ledger components and the lease records (tests/test_ms7_lag._digest without the report)."""
    comp = {k: float(v).hex() for k, v in sorted(res.components.items())}
    leases = [[L.site, L.contract, L.gpus, L.start_slot, L.start_min, L.prepaid_end_min, L.announce_slot, L.death_min,
               L.release_min, L.end_min, L.end_cause, float(L.prepaid_usd).hex(), float(L.rent_usd).hex(), L.tag]
              for L in res.leases]
    blob = json.dumps({"components": comp, "leases": leases}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def _run(inst, pid, params, lm=None, seed=0):
    pol = make_policy({"policy": {"id": pid, "params": dict(params)}}, inst)
    model = LenderModel(**{"schedule": "trace", "information": "I1", **(lm or {})})
    res = simulate(inst, pol, model, EngineConfig(check_invariants=True), lender_seed=seed, policy_seed=seed)
    assert not res.invariant_failures, res.invariant_failures[:3]
    return res


class Script(Policy):
    """A scripted inner policy: {t: list of actions, or callable(obs) -> list}; records the results it sees and the
    slots at which it was called."""
    name = "script"

    def __init__(self, plan=None, mutate=False):
        self.plan, self.mutate = dict(plan or {}), mutate

    def reset(self, view, rng):
        super().reset(view, rng)
        self.calls, self.results = [], {}

    def act(self, obs):
        t = int(obs.t)
        self.calls.append(t)
        self.results[t] = list(obs.results)
        if self.mutate:
            obs.cost_so_far = -1e9                 # a write to its own copy: the cap must not see it
            obs.leases.clear()
        a = self.plan.get(t, [])
        return list(a(obs) if callable(a) else a)


def _eng(inst, pol, schedule="trace"):
    res = simulate(inst, pol, LenderModel(schedule=schedule), policy_rng=np.random.default_rng(0))
    assert not res.invariant_failures, res.invariant_failures[:3]
    return float(res.components["total"]), res


def _J(T):
    act = np.zeros((1, T), dtype=bool)
    act[0, 0] = True
    I = core.Instance(T=T, tau=np.array([1]), H=np.array([0]), a=np.array([[1.0]]), beta=np.array([[0.0]]),
                      g=np.array([1]), q=2.0, cl_llm=np.zeros(1, dtype=int), delta=np.zeros((1, 1)), active=act)
    return from_core(I, [np.zeros(0, np.int64)])[0]


def _K(n, q=1.0, mu=0.5):
    I = core.Instance(T=3, tau=np.array([1]), H=np.array([0]), a=np.array([[n * q]]), beta=np.array([[0.0]]),
                      g=np.array([1]), q=q, cl_llm=np.zeros(n, dtype=int), delta=np.zeros((n, 1)),
                      active=np.ones((n, 3), dtype=bool))
    inst = from_core(I, [np.zeros(0, np.int64)])[0]
    st = inst.stranding
    inst.stranding = dataclasses.replace(st, mu_fb_usd=np.full(len(np.atleast_1d(st.mu_fb_usd)), float(mu)))
    return inst


# ---------------------------------------------------------------- registry and parameters
def test_registry_ms8():
    assert registry.MS8_IDS == ("CAP",)
    assert not set(registry.MS8_IDS) & (set(registry.POLICY_IDS) | set(registry.MS5B_IDS) | set(registry.MS7_IDS))
    assert registry.MS7_IDS == ("A9P", "MPC") and registry.MS5B_IDS == ("A9", "A8P")
    e = registry.entry("CAP")
    assert e.runner == "simulate" and e.info == "online-I1" and registry.resolve("CAP") is BudgetCapped
    assert registry.param_names("CAP") == ("inner", "inner_params", "X", "count", "on_bind")
    assert registry.needed_inputs("CAP", {"inner": "BL1"}) == () and registry.info_class("CAP", {}) == "online-I1"
    assert registry.inner_of("CAP", {}) is None and registry.CAP_INNER_IDS == ("A9", "BL1", "BL5")
    inst = build_instance(toy_config())
    pol = make_policy({"policy": {"id": "CAP", "params": {"inner": "BL1", "X": 0.0}}}, inst)
    assert isinstance(pol, BudgetCapped) and pol.params()["inner"] == "BL1" and pol.params()["X"] == 0.0


def test_parameters():
    assert parse_X("lb") == ("lb", 0.0) and parse_X("rel:0.05") == ("rel", 0.05) and parse_X(3) == ("const", 3.0)
    for bad in ("rel:-1", "rel:x", "foo", -1.0, float("inf"), True, None):
        with pytest.raises(PolicyError):
            BudgetCapped(X=bad)
    for kw in ({"count": "all"}, {"on_bind": "halt"}, {"inner": "A6"}, {"inner_params": []},
               {"inner": Script(), "inner_params": {"a": 1}}, {"foo": 1}):
        with pytest.raises(PolicyError):
            BudgetCapped(**kw)

    class Fast(Script):
        def reset(self, view, rng):
            super().reset(view, rng)
            self.wants_fast = True
    pol = BudgetCapped(inner=Fast())
    with pytest.raises(PolicyError, match="on_fast"):
        _eng(_J(4), pol)


# ---------------------------------------------------------------- X huge: the inner alone, bit for bit
@pytest.mark.parametrize("inner", ("A9", "BL1", "BL5"))
@pytest.mark.parametrize("lm", ({}, IID), ids=("trace", "iid0.3"))
def test_huge_allowance_is_the_inner(inner, lm):
    inst = build_instance(toy_config())
    a = _run(inst, inner, {}, lm, 3)
    rep_a = _jsonable(a.metrics.get("policy") or {})
    for count, ob in CAPS:
        b = _run(inst, "CAP", {"inner": inner, "X": 1e18, "count": count, "on_bind": ob}, lm, 3)
        assert _ledger(b) == _ledger(a), (inner, count, ob)
        rep = b.metrics["policy"]
        assert _jsonable(rep["inner"]) == rep_a and rep["cap"]["bind_slots"] == 0 and rep["cap"]["latch_t"] is None


# ---------------------------------------------------------------- Proposition N through the engine
@pytest.mark.parametrize("n", (4, 64))
def test_I_n(n):
    """(a): 'paid' 3n (stop), 'slot' 2n, A8P at 'lb' 2n, against FB = 2n (Proposition G6(i)'s I_n, eager lender)."""
    inst = from_core(g6_case(n, (1,)), [np.zeros(0, np.int64)])[0]
    buys = {0: [Buy(0, 0, 0, 1)] * n}
    got = {}
    for count, ob in (("paid", "stop"), ("slot", "stop")):
        got[count], res = _eng(inst, BudgetCapped(inner=Script(buys), X=3.0, count=count, on_bind=ob), "eager")
        assert res.metrics["policy"]["cap"]["FB_T"] == pytest.approx(2 * n, abs=TOL)
    alg, res = _eng(inst, ProjectedGuarded(inner=Script(buys), allowance="lb", kappa=None, safe="fb"), "eager")
    assert got["paid"] == pytest.approx(3 * n, abs=TOL) and got["slot"] == pytest.approx(2 * n, abs=TOL)
    assert alg == pytest.approx(2 * n, abs=TOL)
    assert alg <= 2 * n + res.metrics["policy"]["online_lb"]["B_T"] + TOL


@pytest.mark.parametrize("T", (5, 50))
def test_J_T_stop_grows_and_latch_stops(T):
    """(b): the 'stop' caps pay T (excess T - 2 - X), the latching caps X + 3 ('paid') and X + 2 ('slot'), A8P 3 (K0)."""
    inst = _J(T)
    for X in (0.0, 1.0):
        for count, ob in CAPS:
            inner = Script({0: [Buy(0, 0, 0, 1)]})
            alg, res = _eng(inst, BudgetCapped(inner=inner, X=X, count=count, on_bind=ob))
            want = T if ob == "stop" else (X + 3 if count == "paid" else X + 2)
            assert alg == pytest.approx(want, abs=TOL), (T, X, count, ob)
            cap = res.metrics["policy"]["cap"]
            if ob == "latch":                        # one release at the latch slot; the inner never called again
                assert cap["latch_t"] == int(want) and cap["latch_releases"] == 1 and cap["after_latch_releases"] == 0
                assert inner.calls == list(range(cap["latch_t"] + 1))     # called at the latch slot, not after
            else:
                assert cap["latch_t"] is None and inner.calls == list(range(T))
    alg, res = _eng(inst, ProjectedGuarded(inner=Script({0: [Buy(0, 0, 0, 1)]}), allowance="lb", kappa=None,
                                           safe="fb"))
    assert alg == pytest.approx(3.0, abs=TOL) and res.metrics["policy"]["online_lb"]["B_T"] == pytest.approx(1.0)
    assert res.metrics["policy"]["projection"]["K0"] == 1


@pytest.mark.parametrize("n", (4, 64))
def test_K_n_stranding(n):
    """(c): with mu^fb = 0.5 under the eager lender (tau = 1 slot, H = 0), every cap pays FB + n mu; A8P at 'lb' stays at
    or below FB + B(T), and at the constant allowance B0 = X below FB + X."""
    mu, inst = 0.5, _K(n)
    fb = 3.0 * n
    for X in (0.0, 5.0):
        for count, ob in CAPS:
            alg, res = _eng(inst, BudgetCapped(inner=Script({0: [Buy(0, 0, 0, 1)]}), X=X, count=count, on_bind=ob),
                            "eager")
            assert alg == pytest.approx(fb + n * mu, abs=TOL), (n, X, count, ob)
            assert res.components["stranding"] == pytest.approx(n * mu, abs=TOL)
        alg, res = _eng(inst, ProjectedGuarded(inner=Script({0: [Buy(0, 0, 0, 1)]}), allowance="alg1", B0=X,
                                               kappa=None, safe="fb"), "eager")
        assert alg <= fb + X + TOL
    alg, res = _eng(inst, ProjectedGuarded(inner=Script({0: [Buy(0, 0, 0, 1)]}), allowance="lb", kappa=None,
                                           safe="fb"), "eager")
    assert alg <= fb + res.metrics["policy"]["online_lb"]["B_T"] + TOL


def _U(n, q=1.0):
    I = core.Instance(T=1, tau=np.array([1]), H=np.array([0]), a=np.array([[1.0], [n * q]]),
                      beta=np.array([[0.0, 0.0]]), g=np.array([1]), q=q, cl_llm=np.zeros(n, dtype=int),
                      delta=np.column_stack([np.zeros(n), np.full(n, np.inf)]), active=np.ones((n, 1), dtype=bool))
    return from_core(I, [np.zeros(0, np.int64)] * 2)[0]


@pytest.mark.parametrize("n", (4, 64))
def test_U_n_service_unpriced(n):
    """(d): a lease at site 1 (delta = inf for every client) priced n q = Q(0) passes every cap, 'slot' included
    (n q <= FB(-1) + Q(0) + X), and the slot still falls back: ALG = 2 n q against FB = n q; A8P at B0 = X prices the
    service by G(0) = Q(0) and pays n q once n q > X, else 2 n q <= FB + X."""
    inst, fb = _U(n), float(n)
    for X in (0.0, 5.0):
        for count, ob in CAPS:
            alg, res = _eng(inst, BudgetCapped(inner=Script({0: [Buy(1, 0, 0, 1)]}), X=X, count=count, on_bind=ob))
            cap = res.metrics["policy"]["cap"]
            assert alg == pytest.approx(2 * fb, abs=TOL) and cap["bind_slots"] == 0, (n, X, count, ob)
            assert cap["FB_T"] == pytest.approx(fb, abs=TOL) and len(res.leases) == 1
        alg, _ = _eng(inst, ProjectedGuarded(inner=Script({0: [Buy(1, 0, 0, 1)]}), allowance="alg1", B0=X,
                                             kappa=None, safe="fb"))
        assert alg == pytest.approx(2 * fb if fb <= X else fb, abs=TOL) and alg <= fb + X + TOL


# ---------------------------------------------------------------- stop semantics and the inner's results
def test_stop_drops_buys_keeps_releases_and_remaps():
    """At a bind under 'stop' the slot's Buys are dropped and its Releases executed; at the next slot the inner sees the
    dropped Buy as ok=False with reason 'cap' and the executed Release at its own index."""
    inst = _J(8)
    plan = {0: [Buy(0, 0, 0, 1)], 3: lambda obs: [Buy(0, 0, 0, 1)] + [Release(int(l)) for l in sorted(obs.leases)]}
    inner = Script(plan)
    alg, res = _eng(inst, BudgetCapped(inner=inner, X=0.0, count="paid", on_bind="stop"))
    cap = res.metrics["policy"]["cap"]
    assert cap["first_bind"] == 3 and cap["dropped_buys"] == 1 and cap["dropped_other"] == 0
    r4 = inner.results[4]
    assert [(r.index, type(r.action).__name__, r.ok, r.reason) for r in r4] == [(0, "Buy", False, "cap"),
                                                                                 (1, "Release", True, "")]
    assert alg == pytest.approx(3.0, abs=TOL) and len(res.leases) == 1     # the lease of slot 0 rented through slot 2


def test_test_reads_the_engine_observation():
    """An inner policy that writes to its observation (cost so far, leases) does not change the cap's test."""
    inst = _J(6)
    a, ra = _eng(inst, BudgetCapped(inner=Script({0: [Buy(0, 0, 0, 1)]}), X=0.0, on_bind="latch"))
    b, rb = _eng(inst, BudgetCapped(inner=Script({0: [Buy(0, 0, 0, 1)]}, mutate=True), X=0.0, on_bind="latch"))
    assert a == b and ra.metrics["policy"]["cap"]["latch_t"] == rb.metrics["policy"]["cap"]["latch_t"] == 3


# ---------------------------------------------------------------- the allowances
def test_allowance_series_and_sublet_B():
    """'lb': X(t) = B(t) of OnlineLB = online_lb.series' B, and X(T) equals Sublet's B_T on the same instance;
    'rel:eps': X(t) = eps FB(t - 1); a constant; FB(T) = BL0a's cost."""
    inst = build_instance(toy_config())
    view = public_view(inst, "I1")
    d = np.asarray(inst.clients.demand, dtype=np.float64)
    B = series(view, d)["B"]
    phi = inst.grid.phi
    Q = [float(fallback_by_client(view, d[:, t * phi:(t + 1) * phi]).sum()) for t in range(inst.grid.T_slow)]
    fb = np.cumsum(Q)
    bl0a = float(_run(inst, "BL0a", {}).components["total"])
    sub = _run(inst, "A8P", SUB).metrics["policy"]["online_lb"]["B_T"]
    for X, want in (("lb", B), ("rel:0.05", 0.05 * np.concatenate([[0.0], fb[:-1]])), (2.5, np.full(len(B), 2.5))):
        cap = _run(inst, "CAP", {"inner": "A9", "X": X}).metrics["policy"]["cap"]
        assert np.allclose(cap["X_series"], want, rtol=1e-12, atol=1e-12), X
        assert cap["B_series"] == list(B) and cap["B_T"] == sub
        assert cap["FB_T"] == pytest.approx(bl0a, rel=1e-12) and np.allclose(cap["FB_series"], fb, rtol=1e-12)
    assert _run(inst, "CAP", {"inner": "A9", "X": "lb"}).metrics["policy"]["cap"]["X_T"] == sub


# ---------------------------------------------------------------- needs_a12: the reduced cell
@pytest.mark.needs_a12
def test_reduced_cell_identity_and_B():
    """On bench_e7f 101 (2 hours) under L-tr and L-eg: CAP with X = 1e18 around A9 and BL1 reproduces the inner alone's
    ledger bit for bit, and CR-cap-B's X(T) equals Sublet's B_T."""
    from sublet.drivers import run as drun
    from sublet.experiments import ms5b_common as m5
    spec0 = m5.week_spec("BL0a", {}, mode="L-tr", c=101, horizon_min=120, name="t_cap")
    inst, _, ecfg = drun.build(spec0, 101)
    for mode in ("L-tr", "L-eg"):
        def go(pid, params):
            spec = m5.week_spec(pid, params, mode=mode, c=101, horizon_min=120, name="t_cap")
            res = simulate(inst, make_policy(spec, inst), drun._lender_model(spec, inst), ecfg, lender_seed=101,
                           policy_seed=0)
            assert not res.invariant_failures
            return res
        for inner in ("A9", "BL1"):
            assert _ledger(go("CAP", {"inner": inner, "X": 1e18})) == _ledger(go(inner, {})), (mode, inner)
        sub = go("A8P", SUB).metrics["policy"]["online_lb"]["B_T"]
        assert go("CAP", {"inner": "A9", "X": "lb"}).metrics["policy"]["cap"]["X_T"] == sub
