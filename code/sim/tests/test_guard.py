"""Tests of policy A8, the guard (sublet/algos/guard.py; design/q44_practical_sublet.md §3.4-§3.6, §3.10,
§6.3 test_guard.py).

Oracles: hand values for the Ratchet; standalone runs of the inner policy (no-abort identity, Theorem
G2(a)), of A2 (forced-abort identity and the safe expert's R curve), of A5 with an empty prediction (the
combiner of FB and R on core exports) and of BL0a (the FB curve); on exact core exports (from_core) the
statements of Theorem G2, Corollary G3, Lemma G5 and Proposition G6. The core-bound checks recompute
a-hat(t) from the inner's recorded actions, the run's lease records and the instance's prices, m(t) from
the ledger, C_S(t) from a standalone A2 run (same stream) and the instance's all-fallback cost, W_S(t_a)
from A2's opened columns and core.Instance.C, and B_on(t) from the demand; nothing is taken from A8's
report except the values that are compared with these. T0g's oracles recompute a-hat(t), G(t) and S(t) from
the ledger, the recorded actions, the lease and replica records and the instance; _t0g_oracle_x, for inner
policies with actions of every type, also rebuilds each replica's admission from the recorded SetAdmission
and Drain actions by the rules of sim_spec §5.4, and recomputes the robust form (and its reserve) at the slots
whose list names an object of its own list, or at every slot for an inner policy that uses on_fast.
"""
from __future__ import annotations

import dataclasses
import json
import math
from collections import defaultdict

import numpy as np
import pytest

import core
import pd as ref_pd

from fixtures import (CONFIGS, UPPER_FAMS, c3p5_case, capped_toy_instance, cm_case, g6_case, load_json,
                      policy_actions_recorder, recording_policy, upper_case)

from sublet.algos import guard
from sublet.algos.a2 import A2
from sublet.algos.a5 import A5, G2
from sublet.algos.common import PolicyError
from sublet.algos.guard import Guarded, Ratchet
from sublet.engine import EngineConfig, simulate
from sublet.instance import build_instance, from_core, units
from sublet.metrics import _jsonable
from sublet.policies.trivial import AlwaysFallback
from sublet.types import Buy, LenderModel, Release

TOL = 1e-9
GAMMAS = (1.0, G2)
ALLOWANCES = {"zero": {"B0": 0.0, "kappa": None}, "B0": {"B0": "auto", "kappa": None},
              "capped": {"B0": "auto", "kappa": 10.0}}
SCHEDS = ("oblivious", "eager", "adaptive")


def _have_a7() -> bool:
    try:
        from sublet.algos import a7
    except ImportError:
        return False
    return hasattr(a7, "PracticalSublet")


HAVE_A7 = _have_a7()
CORE_INNERS = ("BL1", "BL5", "A6") + (("A7",) if HAVE_A7 else ())


def _close(a, b, tol=TOL) -> bool:
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def _N(inst) -> int:
    """The driver input N_bound of §6.3: max(N_u T_s, 3)."""
    return max(len(units(inst).client) * inst.grid.T_slow, 3)


def _inner(pid: str, **kw):
    return guard._inner_class(pid)(**kw)


def _ms(seed: int = 3, horizon_min=None):
    """ms2_multi_small.json with config seed `seed` (cell 'ms s<seed>'), optionally on a shorter horizon."""
    cfg = load_json(CONFIGS / "ms2_multi_small.json")
    cfg["seed"] = int(seed)
    if horizon_min is not None:
        cfg["time"]["horizon_min"] = int(horizon_min)
    return build_instance(cfg)


def _lease_rows(res, tags: bool = True) -> list:
    out = []
    for L in res.leases:
        d = dataclasses.asdict(L)
        if not tags:
            d.pop("tag")
        out.append(d)
    return out


def _no_times(x):
    """A report without its wall-time fields (keys starting with 'time_s'), which differ between runs."""
    if isinstance(x, dict):
        return {k: _no_times(v) for k, v in x.items() if not str(k).startswith("time_s")}
    if isinstance(x, (list, tuple)):
        return [_no_times(v) for v in x]
    return x


def _same_ledger(a, b, what: str, tags: bool = True) -> None:
    """Bitwise identical per-slot ledgers and components, and identical lease records."""
    assert set(a.per_slot) == set(b.per_slot), what
    for k in a.per_slot:
        assert np.array_equal(a.per_slot[k], b.per_slot[k]), (what, k)
    assert a.components == b.components, what
    assert _lease_rows(a, tags) == _lease_rows(b, tags), what


# ================================================================ Ratchet (pure logic)
def _run_ratchet(rt: Ratchet, a_hat, C_S, B_on, alg=None):
    """Steps until the abort; alg[t] = ALG(t) (booked at t + 1). Returns the slots executed."""
    done = []
    for t in range(len(a_hat)):
        prev = None if alg is None or t == 0 else alg[t - 1]
        if not rt.step(t, a_hat[t], C_S[t], rt.allowance(B_on[t]), alg_prev=prev):
            return done
        done.append(t)
    return done


def test_ratchet_logic():
    """§3.4 on synthetic curves (hand oracle): the abort slot is the first t with a-hat(t) > gamma C_S(t) +
    B(t) for the constant, online and capped allowances; equality executes; no abort inside the envelope;
    m(t) = max{0, ALG(t) - a-hat(t)} booked at t + 1; T0 and T1 test values; forced abort; no return to
    mode E; a decreasing allowance and non-increasing slots are rejected."""
    C_S = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    B_on = [0.0, 0.5, 1.0, 1.0, 1.0, 1.0]
    # constant B0 = 2, gamma = 1: rhs = 3, 4, 5, 6, 7, 8; a-hat(2) = rhs(2) executes, a-hat(3) > 6 aborts
    rt = Ratchet(1.0, "T0", 2.0, None)
    assert [rt.allowance(b) for b in B_on] == [2.0] * 6
    assert _run_ratchet(rt, [2.5, 3.9, 5.0, 6.1, 0.0, 0.0], C_S, B_on) == [0, 1, 2]
    assert rt.t_a == 3 and rt.aborted and not rt.forced
    assert rt.rhs == [3.0, 4.0, 5.0, 6.0] and rt.report()["a_hat_t_a"] == 6.1
    with pytest.raises(PolicyError):
        rt.step(4, 0.0, 5.0, 2.0)                       # no return to mode E
    # online allowance (B0 never binds): rhs = C_S + B_on = 1, 2.5, 4, 5, 6, 7
    rt = Ratchet(1.0, "T0", 1e9, 1.0)
    assert [rt.allowance(b) for b in B_on] == B_on
    assert _run_ratchet(rt, [1.0, 2.5, 4.1, 0, 0, 0], C_S, B_on) == [0, 1] and rt.t_a == 2
    # capped B = min(2, 3 B_on) = 0, 1.5, 2, 2, 2, 2 with gamma = 1.5: rhs = 1.5, 4.5, 6.5, 8, 9.5, 11
    rt = Ratchet(1.5, "T1", 2.0, 3.0)
    assert [rt.allowance(b) for b in B_on] == [0.0, 1.5, 2.0, 2.0, 2.0, 2.0]
    assert _run_ratchet(rt, [1.5, 4.5, 6.5, 8.0, 9.5, 11.0 + 1e-6], C_S, B_on) == [0, 1, 2, 3, 4] and rt.t_a == 5
    # within the envelope: no abort; m booked from ALG(t) at t + 1
    rt = Ratchet(1.0, "T0", 0.5, None)
    a_hat = [c + 0.5 for c in C_S]
    alg = [1.2, 2.6, 3.0, 4.9, 5.0, 6.0]
    assert _run_ratchet(rt, a_hat, C_S, B_on, alg=alg) == list(range(6)) and rt.t_a is None
    want_m = [max(0.0, alg[t] - a_hat[t]) for t in range(5)]
    assert [rt.m[t] for t in range(5)] == want_m and 5 not in rt.m
    assert want_m == pytest.approx([0.0, 0.1, 0.0, 0.4, 0.0], abs=1e-12)
    assert rt.report()["m"] == want_m + [None]
    # the slot before the abort gets its m; the aborting slot none
    rt = Ratchet(1.0, "T0", 0.0, None)
    assert rt.step(0, 1.0, 1.0, 0.0) and not rt.step(1, 5.0, 2.0, 0.0, alg_prev=1.25)
    assert rt.m == {0: 0.25} and rt.report()["m"] == [0.25]
    # test values
    assert Ratchet(1.0, "T0").test_value(1.0, 2.0, 3.0, 4.0) == 10.0
    assert Ratchet(1.0, "T1").test_value(1.0, 2.0, 3.0, 4.0) == 3.0
    # forced abort
    rt = Ratchet(1.0, "T0", 10.0, None)
    assert rt.step(0, 0.0, 1.0, 10.0) and not rt.step(1, 0.0, 1.0, 10.0, force=True)
    assert rt.t_a == 1 and rt.forced
    # rejected inputs
    rt = Ratchet(1.0, "T0", 0.0, None)
    rt.step(0, 0.0, 1.0, 2.0)
    with pytest.raises(PolicyError):
        rt.step(1, 0.0, 1.0, 1.0)                       # B decreased
    with pytest.raises(PolicyError):
        rt.step(0, 0.0, 1.0, 2.0)                       # slot not increasing
    for bad in (dict(gamma=0.0), dict(test="T2"), dict(B0=-1.0), dict(kappa=-1.0), dict(B0=math.inf)):
        with pytest.raises(PolicyError):
            Ratchet(**{**dict(gamma=1.0, test="T0", B0=0.0, kappa=None), **bad})


def test_params():
    """A8's parameters (§6.1 item 3): defaults, domains, and N_bound for S_rbar = 'theory'. The default test is
    'T0g' with the wind-down reserve and wind_down 'auto' since the decision of 2026-10-17 (this test asserted
    test 'T0' before); 'auto' resolves to 'adaptive' under T0g and to 'keep' under T0 and T1; 'adaptive' needs T0g;
    on_unavailable is a driver input (None, 'sell', 'refuse')."""
    assert Guarded.PARAMS == {"inner": "A7", "inner_params": {}, "safe": "fb+pd", "S_rbar": "theory", "gamma": 1.0,
                              "gamma_T11": G2, "test": "T0g", "wind_down": "auto", "reserve": True, "B0": "auto",
                              "kappa": 10.0, "abort_at": None}
    assert Guarded.INPUTS == ("N_bound", "on_unavailable")
    assert Guarded(inner="BL1", safe="fb").wd == "adaptive"
    assert Guarded(inner="BL1", safe="fb", test="T0").wd == "keep"
    assert Guarded(inner="BL1", safe="fb", test="T1").wd == "keep"
    assert Guarded(inner="BL1", safe="fb", test="T0", wind_down="release").wd == "release"
    assert Guarded(inner="BL1", safe="fb", on_unavailable="refuse").on_unavailable == "refuse"
    p = Guarded(inner="BL1", N_bound=10).params()
    assert p["inner"] == "BL1" and p["inner_params"] == _inner("BL1").params() and p["kappa"] == 10.0
    with pytest.raises(PolicyError):
        Guarded(inner="BL1")                            # S_rbar = 'theory' needs N_bound
    Guarded(inner="BL1", safe="fb")                     # no R: no N_bound needed
    Guarded(inner="BL1", S_rbar=1)
    for bad in (dict(inner="A2"), dict(safe="x"), dict(S_rbar=0), dict(gamma=0), dict(gamma_T11=1.0),
                dict(test="T2"), dict(B0="x"), dict(B0=-1), dict(kappa=-2), dict(abort_at=-1), dict(abort_at=True),
                dict(inner_params=[1]), dict(foo=1), dict(wind_down="x"), dict(test="T0", wind_down="adaptive"),
                dict(reserve=1), dict(on_unavailable="never")):
        with pytest.raises(PolicyError):
            Guarded(**{"inner": "BL1", "N_bound": 10, **bad})


# ================================================================ identities
NO_ABORT = {"B0": 1e12, "kappa": None}


@pytest.mark.parametrize("inner", ("A7", "BL1", "BL5", "A6"))
def test_no_abort_identity(inner):
    """Theorem G2(a): with B0 = 1e12 and kappa = None the guard never aborts, and A8 around the inner policy
    gives a ledger and lease records identical to the inner policy alone, on ms s3 (6-h horizon, policy seeds
    0 and 1) and on a from_core C3-P5 instance under the eager lender (policy seed 0)."""
    if inner == "A7" and not HAVE_A7:
        pytest.skip("sublet/algos/a7.py (PracticalSublet) is not built yet")
    inst = _ms(3, 360)
    cases = [(inst, LenderModel(), s) for s in (0, 1)]
    I = c3p5_case(14)
    cases.append((from_core(I, [np.zeros(0, np.int64)])[0], LenderModel(schedule="eager"), 0))
    for inst_c, model, s in cases:
        alone = simulate(inst_c, _inner(inner), model, policy_seed=s)
        pol = Guarded(inner=inner, N_bound=_N(inst_c), **NO_ABORT)
        res = simulate(inst_c, pol, model, policy_seed=s)
        tag = (inner, inst_c.name, s)
        assert res.invariant_failures == [] and alone.invariant_failures == [], tag
        rep = res.metrics["policy"]
        assert rep["t_a"] is None and rep["mode"] == [["E", 0, inst_c.grid.T_slow]], tag
        _same_ledger(res, alone, str(tag))
        assert _no_times(rep["inner"]) == _no_times(alone.metrics["policy"]), tag


def _a2_run(inst, model, rbar, s):
    kw = {"rbar": rbar, "record": True}
    if rbar == "theory":
        kw["N_bound"] = _N(inst)
    pol = A2(**kw)
    res = simulate(inst, pol, model, policy_seed=s)
    assert res.invariant_failures == []
    return pol, res


def test_forced_abort_identity():
    """§6.3: with safe = 'pd' and abort_at = 0 the guard aborts at slot 0 and A8's ledger equals A2's with the
    same r-bar and policy seed (S's live set at slot 0 is A2's slot-0 purchases), lease records equal up to
    the tag: on a from_core export (Bernoulli(0.1) trace schedule), on ms s3 (6 h) with r-bar 1 and theory,
    and on the capped toy, where the pre-check drops purchases (refusals reach the planner as in A2)."""
    I = upper_case("rand", 0)
    om = core.random_omega(np.random.default_rng(7000), I, 0.1)
    cases = [("core", from_core(I, om)[0], LenderModel(), r) for r in (1, "theory")]
    cases += [("ms s3", _ms(3, 360), LenderModel(), r) for r in (1, "theory")]
    cases += [("capped toy", capped_toy_instance(), LenderModel(), 1)]
    n_drop = 0
    for name, inst, model, rbar in cases:
        for s in (0, 1):
            a2, res_a2 = _a2_run(inst, model, rbar, s)
            pol = Guarded(inner="BL1", safe="pd", S_rbar=rbar, abort_at=0, N_bound=_N(inst))
            res = simulate(inst, pol, model, policy_seed=s)
            tag = (name, rbar, s)
            assert res.invariant_failures == [], tag
            rep = res.metrics["policy"]
            assert rep["t_a"] == 0 and rep["guard"]["forced"] and rep["mode"] == [["S", 0, inst.grid.T_slow]], tag
            _same_ledger(res, res_a2, str(tag), tags=False)
            assert pol.sx.planner.rounder.opened_ref() == a2.opened_ref(), tag
            assert rep["safe"]["R"]["refused"] == res_a2.metrics["policy"]["refused"], tag
            n_drop += res_a2.metrics["policy"]["refused"]
    assert n_drop > 0                                   # the capped toy exercises refusals


# ================================================================ core bound (Theorem G2, Corollary G3, Lemma G5)
_A2_CACHE: dict = {}
_OPT_CACHE: dict = {}


def _core_inst(I, sched: str, seed: int):
    if sched == "oblivious":
        om = core.random_omega(np.random.default_rng(7000 + seed), I, 0.1)
        return from_core(I, om)[0], LenderModel()
    inst, _ = from_core(I, [np.zeros(0, np.int64)] * I.m)
    return inst, LenderModel(schedule=sched)


def _a2_core(key, I, inst, rbar, s):
    """A2 alone (same r-bar and policy generator default_rng(s)): its opened map and curve. R is eager and
    lender-independent, and from_core exports have unlimited capacity, so one run per instance serves every
    schedule (asserted: no refusal)."""
    k = (key, rbar, s)
    if k not in _A2_CACHE:
        kw = {"rbar": rbar, "record": True}
        if rbar == "theory":
            kw["N_bound"] = _N(inst)
        pol = A2(**kw)
        res = simulate(inst, pol, LenderModel(schedule="eager"), policy_rng=np.random.default_rng(s))
        assert res.invariant_failures == [] and res.metrics["policy"]["refused"] == 0
        _A2_CACHE[k] = (pol.opened_ref(), np.asarray(res.metrics["policy"]["curve"], dtype=float))
    return _A2_CACHE[k]


def _opt_eager(key, I) -> float:
    if key not in _OPT_CACHE:
        r = core.opt_eager(I)
        assert r["status"] == 0, key
        _OPT_CACHE[key] = float(r["fun"])
    return _OPT_CACHE[key]


def _b0_core(I) -> float:
    """B0 = 'auto' on a core instance (§3.10): per client, the cheapest C over the sites with delta < INF of
    the contract k*(l) = argmin (a_lk, L_k, -H_k, k) over the contracts with tau_k < T (not protected)."""
    ok = [k for k in range(I.K) if int(I.tau[k]) < I.T]
    tot = 0.0
    for c in range(I.n):
        j = int(I.cl_llm[c])
        best = math.inf
        for l in range(I.m):
            if not ok or not np.isfinite(I.delta[c, l]):
                continue
            k = min(ok, key=lambda k: (float(I.a[l, k]), int(I.L[k]), -int(I.H[k]), k))
            best = min(best, I.C(l, j, k))
        if math.isfinite(best):
            tot += best
    return tot


def _B_on_core(I) -> np.ndarray:
    """(T,) B_on(t) = sum_j min{q n_j(t), C^min_j} (Lemma G5), C^min_j over the sites some client of j can
    use (delta finite and below q) and every contract."""
    out = np.zeros(I.T)
    for j in range(I.J):
        cl = np.flatnonzero(np.asarray(I.cl_llm) == j)
        n_j = np.cumsum(np.asarray(I.active)[cl].sum(axis=0))
        sites = [l for l in range(I.m) if any(np.isfinite(I.delta[c, l]) and I.delta[c, l] < I.q for c in cl)]
        cmin = min((I.C(l, j, k) for l in sites for k in range(I.K)), default=math.inf)
        out += np.minimum(I.q * n_j, cmin)
    return out


def _combiner(fb, cr, live_cost, buy_cost, gamma):
    """C3-T11's rule with FB in the F slot (pd.combine's, per slot): [(followed 'F'/'R', switched, total)]."""
    CF = CR = tot = 0.0
    cur = None
    out = []
    for t in range(len(fb)):
        CFt, CRt = CF + fb[t], CR + cr[t]
        if cur is None:
            cur = "F" if CFt <= CRt else "R"
        prev, inc, Cy = (CF, fb[t], CRt) if cur == "F" else (CR, cr[t], CFt)
        sw = prev + inc > gamma * Cy + 1e-12
        if sw:
            cur = "R" if cur == "F" else "F"
            tot += fb[t] if cur == "F" else live_cost[t] + cr[t] - buy_cost[t]
        else:
            tot += inc
        CF, CR = CFt, CRt
        out.append((cur, sw, tot))
    return out


def _alive_at_obs(L, t: int, slow: int, fast: int) -> bool:
    """Whether lease record L was in obs.leases at slot t (bought before t, alive in the slot's first fast
    slot when the policy acted: still alive then, or released at t)."""
    if L.start_slot >= t:
        return False
    if L.release_min is not None and L.release_min == t * slow:
        return True
    return L.end_min >= t * slow + fast


def _a_hat(inst, res, t, alg_prev, acts, test, Q):
    """a-hat(t) of §3.10 from the inner's actions at t, the run's lease records and the instance's prices."""
    g = inst.grid
    slow, fast = g.slow_min, g.fast_min
    t0m, t1m = t * slow, (t + 1) * slow
    rel = {a.lease_id for a in acts if isinstance(a, Release)}
    p = rent = 0.0
    for a in acts:
        if isinstance(a, Buy):
            gp = inst.llms[a.llm].g * a.n_replicas
            pr = float(inst.price[a.site, a.contract])
            P = inst.contracts[a.contract].prepaid_min
            p += gp * pr * P / 60.0 + a.n_replicas * float(inst.beta_usd[a.llm, a.site])
            rent += gp * pr * max(0, t1m - (t0m + P)) / 60.0
    for L in res.leases:
        if L.id in rel or not _alive_at_obs(L, t, slow, fast):
            continue
        hi = t1m if L.death_min is None else min(t1m, L.death_min)
        rent += L.gpus * float(inst.price[L.site, L.contract]) * max(0, hi - max(t0m, L.prepaid_end_min)) / 60.0
    return alg_prev + p + ((rent + Q) if test == "T0" else 0.0)


def _certificate(I, inst, res, pol, rec_E, prm, opened_R, curve_R, opt_eager, tag) -> dict:
    """Theorem G2, Corollary G3 and Lemma G5 on one run of A8 on an exact core export (§3.10 certificate,
    §6.3 core bound), every quantity recomputed (module docstring). Returns a summary."""
    assert res.invariant_failures == [], (tag, res.invariant_failures[:3])
    rep = res.metrics["policy"]
    T = I.T
    gamma, test, safe = float(prm["gamma"]), prm["test"], prm["safe"]
    kappa = prm["kappa"]
    tot = np.asarray(res.per_slot["total"], dtype=float)
    alg = np.cumsum(tot)                                     # ALG(t)

    def A(t):
        return 0.0 if t < 0 else float(alg[t])
    run_cost = (np.asarray(res.per_slot["lease_rent"]) + np.asarray(res.per_slot["routing"])
                + np.asarray(res.per_slot["fallback"]))
    assert not any(np.any(np.asarray(res.per_slot[k])) for k in
                   ("stranding_kv", "stranding_fl", "stranding_fb", "stranding_pi")), tag
    # S's curve: FB = q n(t); R = A2 alone; the combiner per slot
    fb = I.q * np.asarray(I.active).sum(axis=0).astype(float)
    live_cost, buy_cost = np.zeros(T), np.zeros(T)
    for F, t0 in opened_R.items():
        _, l, j, k, s0 = F[:5]
        c, L = I.C(l, j, k), int(I.L[k])
        buy_cost[t0] += c
        for u in range(t0, min(s0 + L, T)):
            live_cost[u] += c
    if safe == "pd":
        C_S = np.cumsum(curve_R)
        follow = [("R", False)] * T
    else:
        cb = _combiner(fb, curve_R, live_cost, buy_cost, float(prm["gamma_T11"]))
        C_S = np.array([x[2] for x in cb])
        follow = [(x[0], x[1]) for x in cb]
        tot_ref, sw_ref = ref_pd.combine(I, [], fb, opened_R, curve_R, gamma=float(prm["gamma_T11"]))
        assert _close(C_S[-1], tot_ref) and sum(x[1] for x in cb) == sw_ref, tag
        assert rep["safe"]["switches"] == sw_ref, tag
    assert np.allclose(rep["safe"]["C_S_curve"], C_S, rtol=TOL, atol=TOL), tag
    assert pol.sx.planner.rounder.opened_ref() == opened_R, tag
    # allowance
    B_on = _B_on_core(I)
    assert np.allclose(rep["safe"]["B_on"], B_on, rtol=TOL, atol=TOL), tag
    B0 = _b0_core(I) if prm["B0"] == "auto" else float(prm["B0"])
    assert _close(rep["B0"], B0), (tag, rep["B0"], B0)
    B = np.full(T, B0) if kappa is None else np.minimum(B0, kappa * B_on)

    def Bt(t):
        return 0.0 if t < 0 else float(B[t])
    assert B_on[-1] <= opt_eager + TOL * max(1.0, opt_eager), (tag, B_on[-1], opt_eager)      # Lemma G5
    # a-hat(t) at the E-mode slots (through t_a), m(t), the trip
    acts = defaultdict(list)
    for t, a in rec_E.actions:
        if not isinstance(t, tuple):
            acts[t].append(a)
    t_a = rep["t_a"]
    last = T - 1 if t_a is None else t_a
    g_rep = rep["guard"]
    assert g_rep["slots"] == list(range(last + 1)), tag
    m = {}
    for t in range(last + 1):
        ah = _a_hat(inst, res, t, A(t - 1), acts[t], test, float(fb[t]))
        rhs = gamma * C_S[t] + Bt(t)
        assert _close(g_rep["a_hat"][t], ah), (tag, t, g_rep["a_hat"][t], ah)
        assert _close(g_rep["rhs"][t], rhs), (tag, t, g_rep["rhs"][t], rhs)
        if t == t_a:
            if not g_rep["forced"]:
                assert ah > rhs - TOL * max(1.0, abs(rhs)), (tag, t, ah, rhs)
            break
        assert ah <= rhs + TOL * max(1.0, abs(rhs)), (tag, t, ah, rhs)
        m[t] = max(0.0, A(t) - ah)
        assert A(t) <= rhs + m[t] + TOL * max(1.0, abs(rhs)), (tag, t)          # E-mode check
        if test == "T0":
            assert m[t] <= TOL * max(1.0, A(t)), (tag, t, m[t])                 # m = 0 under T0
        else:
            assert m[t] <= run_cost[t] + TOL * max(1.0, run_cost[t]), (tag, t, m[t], run_cost[t])
    for t, mv in enumerate(g_rep["m"]):
        if mv is not None:
            assert _close(mv, m[t]), (tag, t, mv, m[t])
    M = max(m.values(), default=0.0)
    ALG = A(T - 1)
    C_T = float(C_S[-1])
    scale = max(1.0, ALG)
    out = {"t_a": t_a, "ALG": ALG, "C_S": C_T}
    if t_a is None:
        assert ALG <= gamma * C_T + Bt(T - 1) + m[T - 1] + TOL * scale, tag              # Theorem G2(a)
    else:
        cur, sw = follow[t_a]
        W = 0.0
        if cur == "R" and not sw:
            W = sum(I.C(F[1], F[2], F[3]) for F, t0 in opened_R.items() if t0 < t_a < F[4] + int(I.L[F[3]]))
        assert _close(rep["W_S_t_a"], W), (tag, rep["W_S_t_a"], W)
        assert W <= (C_S[t_a - 1] if t_a > 0 else 0.0) + TOL * scale, tag                # Lemma G1(a)
        C_prev = float(C_S[t_a - 1]) if t_a > 0 else 0.0
        excess = (ALG - A(t_a - 1)) - (W + C_T - C_prev)
        assert excess <= TOL * scale, (tag, "S-mode excess", excess)                    # Lemma G1(b)
        bound = C_T + (gamma - 1) * C_prev + W + Bt(t_a - 1) + m.get(t_a - 1, 0.0)
        assert ALG <= bound + TOL * scale, (tag, ALG, bound)                            # Theorem G2(b)
        out["excess"] = excess
    assert ALG <= (1 + gamma) * C_T + Bt(T - 1) + M + TOL * scale, tag                     # Theorem G2(c)
    if test == "T0" and kappa is not None:
        assert ALG <= (1 + gamma) * C_T + kappa * B_on[-1] + TOL * scale, tag            # Corollary G3
    return out


COMBOS = tuple((test, safe, gm, an) for test in ("T0", "T1") for safe in ("pd", "fb+pd") for gm in GAMMAS
               for an in ALLOWANCES)        # the 24 (test, safe, gamma, allowance) of §6.3


def _core_runs(key, I, inners, combos, scheds=SCHEDS, seed=0, s=0) -> list:
    """The (test, safe, gamma, allowance) of `combos` on instance I under each schedule (seed of the oblivious
    schedule: 7000 + seed), the inner policy rotating over `inners`; returns the certificates' summaries."""
    out = []
    oe = _opt_eager(key, I)
    i = 0
    for sched in scheds:
        inst, model = _core_inst(I, sched, seed)
        opened_R, curve_R = _a2_core(key, I, inst, "theory", s)
        for (test, safe, gm, an) in combos:
            iid = inners[i % len(inners)]
            i += 1
            prm = {"test": test, "safe": safe, "gamma": gm, "gamma_T11": G2, **ALLOWANCES[an]}
            inner = _inner(iid)
            rec_E = policy_actions_recorder(inner)
            pol = Guarded(inner=rec_E, N_bound=_N(inst), **prm)
            res = simulate(inst, pol, model, policy_rng=np.random.default_rng(s))
            tag = (key, sched, test, safe, round(gm, 3), an, iid)
            out.append(_certificate(I, inst, res, pol, rec_E, prm, opened_R, curve_R, oe, tag))
    return out


@pytest.mark.parametrize("fam_name", UPPER_FAMS)
def test_core_bound_upper(fam_name):
    """§6.3 core bound on the instances of test_a2.py::test_engine_le_accounted (family `fam_name`, seeds
    0-3) under the oblivious (Bernoulli 0.1), eager and adaptive schedules, for T0 and T1, safe in {pd,
    fb+pd}, gamma in {1, 1 + 1/sqrt 2} and the allowances 0, B0 and capped (kappa 10): each of these 24
    combinations runs once per schedule, on seed i for the combinations COMBOS[i::4], with the inner policies
    BL1, BL5, A6 (and A7) in rotation. Checked (_certificate): a-hat(t) recomputed and equal to A8's, the trip
    at the first violating slot, the E-mode check with m = 0 under T0 and m(t) <= rent + routing + fallback
    of slot t under T1, the S-mode excess <= 1e-9, Theorem G2(a)-(c), Corollary G3 (T0, capped) and Lemma G5
    (B_on(T) <= OPT_eager)."""
    out = []
    for seed in range(4):
        I = upper_case(fam_name, seed)
        out += _core_runs((fam_name, seed), I, CORE_INNERS, COMBOS[seed::4], seed=seed)
    assert len(out) == len(COMBOS) * len(SCHEDS)
    n_ab = sum(o["t_a"] is not None for o in out)
    assert 0 < n_ab < len(out), (fam_name, n_ab, len(out))      # both branches of Theorem G2 occur


def test_core_bound_families():
    """§6.3 core bound on the C3-P5 instances (beta in {2, 6, 14, 30}, T = 48; beta index b runs the
    combinations COMBOS[b::4]) and the cat-and-mouse instances (m, rho) in {(2, 4), (4, 8)} (COMBOS[0::2] and
    COMBOS[1::2]) under the three schedules: every combination once per family and schedule."""
    out = []
    for b, beta in enumerate((2, 6, 14, 30)):
        out += _core_runs(("c3p5", beta), c3p5_case(beta), CORE_INNERS, COMBOS[b::4])
    for i, (m, rho) in enumerate(((2, 4), (4, 8))):
        out += _core_runs(("cm", m, rho), cm_case(m, rho), CORE_INNERS, COMBOS[i::2])
    assert len(out) == 2 * len(COMBOS) * len(SCHEDS)
    n_ab = sum(o["t_a"] is not None for o in out)
    assert 0 < n_ab < len(out), (n_ab, len(out))


def _g6_inner(n: int, buy: bool):
    """Proposition G6's inner E: one lease per client at slot 0 (scenario (i)) or nothing (scenario (ii))."""
    def make():
        return recording_policy({0: [Buy(0, 0, 0, 1) for _ in range(n)]} if buy else {})
    return make


@pytest.mark.parametrize("n", (4, 64))
def test_proposition_g6(n):
    """Proposition G6 on I_n (through the engine on from_core): OPT_eager = 3; (i) clients active at slot 1
    only and E buying one lease per client at slot 0: ALG >= 3n under T0 and T1 with the constant allowance
    B0 = 3n (B0 'auto' equals 3n here), and an abort at slot 0 under T0 with the capped allowance;
    (ii) clients active at slots 0 and 1 and E never buying: ALG >= 2n under T1 with every allowance, and an
    abort at slot 0 under T0 with B = 0. Every run also passes the core-bound certificate."""
    I1, I2 = g6_case(n, (1,)), g6_case(n, (0, 1))
    assert _close(_opt_eager(("g6", n, 1), I1), 3.0) and _close(_opt_eager(("g6", n, 2), I2), 3.0)
    assert _close(_b0_core(I1), 3 * n)
    for I, key, buy in ((I1, ("g6", n, 1), True), (I2, ("g6", n, 2), False)):
        inst, model = _core_inst(I, "eager", 0)
        opened_R, curve_R = _a2_core(key, I, inst, "theory", 0)
        for test in ("T0", "T1"):
            for safe in ("pd", "fb+pd"):
                for an in ALLOWANCES:
                    prm = {"test": test, "safe": safe, "gamma": 1.0, "gamma_T11": G2, **ALLOWANCES[an]}
                    rec_E = policy_actions_recorder(_g6_inner(n, buy)())
                    pol = Guarded(inner=rec_E, N_bound=_N(inst), **prm)
                    res = simulate(inst, pol, model, policy_rng=np.random.default_rng(0))
                    tag = ("g6", n, buy, test, safe, an)
                    o = _certificate(I, inst, res, pol, rec_E, prm, opened_R, curve_R, 3.0, tag)
                    ALG = o["ALG"]
                    if buy and an == "B0":
                        assert o["t_a"] != 0 and ALG >= 3 * n - TOL, (tag, ALG)          # (i)
                    if buy and an == "capped" and test == "T0":
                        assert o["t_a"] == 0, tag                                        # B(0) = 0
                    if not buy and test == "T1":
                        assert o["t_a"] != 0 and ALG >= 2 * n - TOL, (tag, ALG)          # (ii)
                    if not buy and test == "T0" and an == "zero":
                        assert o["t_a"] == 0, tag


# ================================================================ the safe expert's curves
def _first_refusal_slot(inst, model, s) -> tuple:
    """A2(rbar=1) alone with its refusals logged: (result, curve, first slot t at which the planner gets a
    refusal, or None)."""
    pol = A2(rbar=1)
    slots = []
    o_reset = pol.reset

    def reset(view, rng):
        o_reset(view, rng)
        o_ref = pol.planner.refuse

        def refuse(col, t, reason=""):
            slots.append(int(t))
            return o_ref(col, t, reason)
        pol.planner.refuse = refuse
    pol.reset = reset
    res = simulate(inst, pol, model, policy_seed=s)
    assert res.invariant_failures == []
    return res, np.asarray(res.metrics["policy"]["curve"], dtype=float), (min(slots) if slots else None)


def test_safe_expert_curves():
    """§6.3 safe-expert curves: safe = 'pd' gives C_S = the cumulative Rounder.curve of A2 alone on from_core
    exports and on ms s3 with S_rbar = 1 (whole day; A2 alone has no pre-check drop there, asserted), and up to
    A2's first drop on the capped toy; safe = 'fb+pd' on core exports gives A5's comb.total, switches and
    followed expert with an empty prediction; the FB curve equals BL0a's per-slot engine cost on ms s3."""
    # from_core exports, both r-bar
    for fam_name, seed in (("rand", 0), ("slo", 1), ("spiky", 2)):
        I = upper_case(fam_name, seed)
        inst, model = _core_inst(I, "oblivious", seed)
        for rbar in (1, "theory"):
            for s in (0, 1):
                opened_R, curve_R = _a2_core((fam_name, seed), I, inst, rbar, s)
                pol = Guarded(inner="BL1", safe="pd", S_rbar=rbar, N_bound=_N(inst), **NO_ABORT)
                rep = simulate(inst, pol, model, policy_rng=np.random.default_rng(s)).metrics["policy"]
                assert np.allclose(rep["safe"]["C_S_curve"], np.cumsum(curve_R), rtol=1e-12, atol=1e-12)
                # fb+pd: A5 with an empty prediction
                kw = {"N_bound": _N(inst)} if rbar == "theory" else {}
                a5 = A5(pred_cols=[], R_rbar=rbar, execute="none", **kw)
                r5 = simulate(inst, a5, model, policy_rng=np.random.default_rng(s)).metrics["policy"]
                pol = Guarded(inner="BL1", safe="fb+pd", S_rbar=rbar, N_bound=_N(inst), **NO_ABORT)
                rep = simulate(inst, pol, model, policy_rng=np.random.default_rng(s)).metrics["policy"]
                sf = rep["safe"]
                assert _close(sf["C_S"], r5["total"], 1e-12) and sf["switches"] == r5["switches"], (fam_name, rbar, s)
                assert np.allclose(sf["curve_FB"], r5["curve_FP"], rtol=1e-12, atol=1e-12)
                assert np.allclose(sf["curve_R"], r5["curve_R"], rtol=1e-12, atol=1e-12)
                assert sf["followed"] == [[{"F": "FB", "R": "R"}[w], t0, n] for w, t0, n in r5["followed"]]
    # ms s3, whole day, S_rbar = 1: A2 alone has no drop
    inst = _ms(3)
    res_a2, curve, t_ref = _first_refusal_slot(inst, LenderModel(), 0)
    assert t_ref is None and res_a2.metrics["policy"]["refused"] == 0 and res_a2.metrics["policy"]["book"]["precheck"] == 0
    pol = Guarded(inner="BL1", safe="pd", S_rbar=1, N_bound=_N(inst), **NO_ABORT)
    res = simulate(inst, pol, LenderModel(), policy_seed=0)
    rep = res.metrics["policy"]
    assert res.invariant_failures == [] and rep["t_a"] is None
    assert np.allclose(rep["safe"]["C_S_curve"], np.cumsum(curve), rtol=TOL, atol=TOL)
    # the FB curve: BL0a's per-slot engine cost
    bl0a = simulate(inst, AlwaysFallback(), LenderModel(), policy_seed=0)
    assert np.allclose(rep["safe"]["curve_FB"], bl0a.per_slot["total"], rtol=TOL, atol=TOL)
    assert _close(rep["safe"]["C_FB"], bl0a.components["total"])
    # capped toy: equal up to A2's first drop (refused at t_ref, dropped at t_ref - 1)
    inst = capped_toy_instance()
    res_a2, curve, t_ref = _first_refusal_slot(inst, LenderModel(), 0)
    assert t_ref is not None and t_ref >= 1
    pol = Guarded(inner="BL1", safe="pd", S_rbar=1, N_bound=_N(inst), **NO_ABORT)
    rep = simulate(inst, pol, LenderModel(), policy_seed=0).metrics["policy"]
    got = np.asarray(rep["safe"]["curve_S"], dtype=float)
    assert np.array_equal(got[:t_ref], curve[:t_ref]), (t_ref, got[:t_ref], curve[:t_ref])
    assert rep["safe"]["R"]["refused"] == 0                  # the shadow sees no refusal


# ================================================================ insurance family, plan class, driver
@pytest.mark.parametrize("T", (48, 192))
def test_insurance_family(T):
    """§6.3: on F3 (C3-P5, beta in {2, 6, 14, 30}, eager) at gamma = 1 with the guard of the Tier 1 study (T0,
    capped, safe fb+pd, theory r-bar; A8's default until 2026-10-17) and with the default since then (T0g with the
    reserve, R = 0 on core exports, and the adaptive wind-down) the guarded policy around A7 (when built) and BL1
    satisfies the certificate (_certificate_x: under T0g also a-hat <= T0's and the S-mode excess <= 0)."""
    inners = ("BL1",) + (("A7",) if HAVE_A7 else ())
    for beta in (2, 6, 14, 30):
        I = c3p5_case(beta, T)
        key = ("c3p5", beta, T)
        oe = _opt_eager(key, I)
        inst, model = _core_inst(I, "eager", 0)
        opened_R, curve_R = _a2_core(key, I, inst, "theory", 0)
        for iid in inners:
            for test in ("T0", "T0g"):
                prm = {"test": test, "safe": "fb+pd", "gamma": 1.0, "gamma_T11": G2, "B0": "auto", "kappa": 10.0}
                rec_E = policy_actions_recorder(_inner(iid))
                pol = Guarded(inner=rec_E, N_bound=_N(inst), **prm)
                res = simulate(inst, pol, model, policy_rng=np.random.default_rng(0))
                _certificate_x(I, inst, res, pol, rec_E, prm, opened_R, curve_R, oe, (key, iid, test))


def test_plan_class_and_report():
    """§2.3 plan class P1 for A8 through drivers.run.make_policy (driver inputs from the instance) on
    ms2_multi_small.json (12 h) around BL1, with a forced abort at slot 60 so that both modes run: actions only
    Buy (one replica), Release, Drain and SetAdmission, no GPU-only lease slot, no invariant failure; the
    report is JSON-serializable and records the abort (mode, copies of L_S(t_a), inherited leases)."""
    from sublet.drivers import run as drun
    spec = drun.load_run_spec({"schema_version": 1, "name": "guard_p1", "instance": "ms2_multi_small.json",
                               "overrides": {"time.horizon_min": 720},
                               "policy": {"id": "A8", "params": {"inner": "BL1", "abort_at": 60}}})
    inst, model, ecfg = drun.build(spec, spec["seeds"]["config"][0])
    pol = drun.make_policy(spec, inst)
    assert isinstance(pol, Guarded) and pol.N_bound == _N(inst)
    rec = policy_actions_recorder(pol)
    res = simulate(inst, rec, model, EngineConfig(check_invariants=True), policy_seed=0)
    assert res.invariant_failures == [], res.invariant_failures[:3]
    kinds = {type(a).__name__ for _, a in rec.actions}
    assert kinds <= {"Buy", "Release", "Drain", "SetAdmission"} and "Buy" in kinds, kinds
    assert all(a.n_replicas == 1 for _, a in rec.actions if isinstance(a, Buy))
    assert res.metrics["gpu_only_lease_slots"] == 0
    rep = res.metrics["policy"]
    T = inst.grid.T_slow
    assert rep["t_a"] == 60 and rep["mode"] == [["E", 0, 60], ["S", 60, T - 60]]
    assert rep["exec"]["inherited"] > 0
    json.dumps(_jsonable(rep), allow_nan=False)
    # S-mode purchases carry the guard's tags; E-mode purchases are BL1's
    by_tag = defaultdict(int)
    for L in res.leases:
        by_tag[L.tag.split(":")[0]] += 1
    assert set(by_tag) <= {"bl1", "a8"}, dict(by_tag)
    assert all(L.start_slot < 60 for L in res.leases if L.tag.startswith("bl1"))
    assert all(L.start_slot >= 60 for L in res.leases if L.tag.startswith("a8"))


@pytest.mark.parametrize("inner", ("A7", "BL1"))
def test_full_model_slot_bound(inner):
    """§3.10 in the full model (ms s3, 6 h, trace and eager, no abort): at every slot the test values
    recorded by A8 bound the slot's real cost, m(t) = max{0, ALG(t) - a-hat(t)} <= the slot's stranding under
    T0 (T0 does not bound stranding) and <= rent + routing + fallback + stranding under T1; T0's a-hat(t) is
    T1's plus the rent bound and the exact all-fallback cost of the slot (BL0a's slot cost); under trace the
    rent term is positive in some slot (A7's k* contract bills 7 min on 5-min slots; BL1 holds leases past
    their billed term), under eager every lease dies at the end of its billed term."""
    if inner == "A7" and not HAVE_A7:
        pytest.skip("sublet/algos/a7.py (PracticalSublet) is not built yet")
    inst = _ms(3, 360)
    fb = simulate(inst, AlwaysFallback(), LenderModel(), policy_seed=0).per_slot["total"]
    for sched in ("trace", "eager"):
        model = LenderModel(schedule=sched)
        reps = {}
        for test in ("T0", "T1"):
            pol = Guarded(inner=inner, test=test, N_bound=_N(inst), **NO_ABORT)
            res = simulate(inst, pol, model, policy_seed=0)
            assert res.invariant_failures == [], (inner, sched, test)
            rep = res.metrics["policy"]
            assert rep["t_a"] is None
            ps = res.per_slot
            alg = np.cumsum(ps["total"])
            strand = ps["stranding"]
            run = ps["lease_rent"] + ps["routing"] + ps["fallback"]
            a_hat = np.asarray(rep["guard"]["a_hat"], dtype=float)
            terms = np.asarray(rep["terms"], dtype=float)                    # p_E, rent_E, Q per slot
            assert np.allclose(terms[:, 2], fb, rtol=TOL, atol=TOL), (inner, sched)
            m = np.maximum(0.0, alg - a_hat)
            lim = strand if test == "T0" else run + strand
            assert np.all(m <= lim + TOL * np.maximum(1.0, alg)), (inner, sched, test, float(np.max(m - lim)))
            rec = [x for x in rep["guard"]["m"][:-1]]
            assert np.allclose(rec, m[:-1], rtol=TOL, atol=TOL)
            reps[test] = (rep, terms)
        (r0, t0), (r1, t1) = reps["T0"], reps["T1"]
        assert np.array_equal(t0, t1)
        assert np.allclose(np.asarray(r0["guard"]["a_hat"]) - np.asarray(r1["guard"]["a_hat"]),
                           t0[:, 1] + t0[:, 2], rtol=TOL, atol=TOL)
        if sched == "trace":
            assert np.any(t0[:, 1] > 0), inner                             # the rent term is exercised


# ================================================================ test T0g (§3.4, §3.10; guard.T0gBound)
# Oracles: an independent recomputation of T0g's a-hat(t) from the ledger, the inner's recorded actions, the
# lease and replica records and the instance (the realized admitting capacity, a plain greedy routing and the
# stranding bound written per client); check_guard.py's core T0g, run on the core instance with the engine's
# recorded actions replayed (check_guard.run, mode 'never'); paired T0/T0g runs with identical streams; the
# twin of S (Lemma G1(b) from slot 0) as inner policy; on exact core exports the statements of Theorem G2,
# Corollary G3 and Lemma G5 with T0g's a-hat recomputed from the records.
from sublet.algos.guard import T0gBound
from sublet.policies.base import Policy
from sublet.timing import warm_fast
from sublet.types import Drain, Load, SetAdmission, Unload

from fixtures import repeat_fast, toy_instance

FULL_MODES = (("trace", "trace", {}), ("eager", "eager", {}), ("iid", "iid_step", {"D_slots": 1, "p": 0.05}),
              ("correlated", "correlated", {"p_sh": 1.0, "groups": "all"}))   # the study's L-tr, L-eg, L-iid-0.05, L-co
GAMMAS_X = (0.25, 1.0, G2, 3.0)
T0G_TOL = 1e-9


def _full(name: str, seed: int, horizon_min=None):
    cfg = load_json(CONFIGS / f"{name}.json")
    cfg["seed"] = int(seed)
    if horizon_min is not None:
        cfg["time"]["horizon_min"] = int(horizon_min)
    return build_instance(cfg)


def _acts_by_slot(rec) -> dict:
    out = defaultdict(list)
    for t, a in rec.actions:
        assert not isinstance(t, tuple), "the inner policies of these tests issue no on_fast actions"
        out[t].append(a)
    return out


def _purchases_and_rent(inst, res, t, acts) -> tuple[float, float]:
    """(p_E(t), rent_E(t)) of §3.10 from the recorded actions at t and the lease records (as _a_hat)."""
    g = inst.grid
    slow, fast = g.slow_min, g.fast_min
    t0m, t1m = t * slow, (t + 1) * slow
    rel = {a.lease_id for a in acts if isinstance(a, Release)}
    p = rent = 0.0
    for a in acts:
        if isinstance(a, Buy):
            gp = inst.llms[a.llm].g * a.n_replicas
            pr = float(inst.price[a.site, a.contract])
            P = inst.contracts[a.contract].prepaid_min
            p += gp * pr * P / 60.0 + a.n_replicas * float(inst.beta_usd[a.llm, a.site])
            rent += gp * pr * max(0, t1m - (t0m + P)) / 60.0
    for L in res.leases:
        if L.id in rel or not _alive_at_obs(L, t, slow, fast):
            continue
        hi = t1m if L.death_min is None else min(t1m, L.death_min)
        rent += L.gpus * float(inst.price[L.site, L.contract]) * max(0, hi - max(t0m, L.prepaid_end_min)) / 60.0
    return p, rent


def _greedy_cost(clients, d, W, q, delta, ok, kinf) -> float:
    """Plain greedy routing + fallback (USD per hour) of one LLM: arcs (delta, client, site) in increasing
    order, each taking min{residual demand, residual capacity}; kappa_infinite: cheapest admitting site."""
    m = W.shape[0]
    if kinf:
        tot = 0.0
        for c in clients:
            best = min([delta[c, l] for l in range(m) if ok[c, l] and W[l] > 0] + [q])
            tot += best * d[c]
        return tot
    arcs = sorted((delta[c, l], c, l) for c in clients for l in range(m) if ok[c, l])
    rd = {c: float(d[c]) for c in clients}
    rc = [float(x) for x in W]
    tot = 0.0
    for dv, c, l in arcs:
        x = min(rd[c], rc[l])
        if x > 0:
            tot += dv * x
            rd[c] -= x
            rc[l] -= x
    return tot + q * sum(max(v, 0.0) for v in rd.values())


def _lb_served(clients, d, W, delta, ok, kinf):
    """{client: LB_c} on the load every optimal routing serves (T0gBound: (i)-(iii)) with the capacity W known."""
    m = W.shape[0]
    act = [c for c in clients if d[c] > 0]
    out = {c: 0.0 for c in clients}
    if kinf:
        for c in act:
            out[c] = float(d[c]) if any(ok[c, l] and W[l] > 0 for l in range(m)) else 0.0
        return out
    # (ii) the cheapest-site assignment fits
    load = np.zeros(m)
    best = {}
    for c in act:
        cand = [(delta[c, l], l) for l in range(m) if ok[c, l] and W[l] > 0]
        if cand:
            best[c] = min(cand)[1]
            load[best[c]] += d[c]
    fits = bool(np.all(load <= W))
    for c in act:
        if fits and c in best:
            out[c] = float(d[c])
            continue
        comp = sum(d[c2] for c2 in act if c2 != c and any(ok[c, l] and ok[c2, l] and W[l] > 0
                                                          and delta[c2, l] <= delta[c, l] for l in range(m)))
        capc = sum(W[l] for l in range(m) if ok[c, l])
        out[c] = min(float(d[c]), max(capc - comp, 0.0))
    return out


def _ub_served(clients, dprev, Wp, lbp, ok, kinf):
    m = Wp.shape[0]
    out = {}
    for c in clients:
        if kinf:
            out[c] = float(dprev[c]) if any(ok[c, l] and Wp[l] > 0 for l in range(m)) else 0.0
            continue
        sub = [c2 for c2 in clients if c2 != c and all(ok[c, l] for l in range(m) if ok[c2, l] and Wp[l] > 0)]
        cap = sum(Wp[l] for l in range(m) if ok[c, l]) - sum(lbp[c2] for c2 in sub)
        out[c] = min(float(dprev[c]), max(cap, 0.0))
    return out


def _t0g_oracle(inst, res, acts: dict, slots) -> dict:
    """T0g's a-hat(t) recomputed at the given slots, independently of guard.py: {t: (a_hat, G, S)}. The
    inner's actions must be Buy (admission 1) and Release only (asserted); the admitting capacity of every
    fast slot is the realized one, from the replica records (alive, warm, existing) and their leases (rule
    T6 on the recorded end minute), which is what T0gBound predicts when no Buy is uncertain."""
    g = inst.grid
    Ds, Df, phi, Tf = g.slow_min, g.fast_min, g.phi, g.T_fast
    J, m, n = inst.J, inst.m, inst.n
    q = np.array([L.q_usd_per_h for L in inst.llms])
    cl = np.asarray(inst.clients.llm)
    dl = np.asarray(inst.clients.delta_usd_per_h, dtype=float)
    ok = np.isfinite(dl) & (dl < q[cl][:, None])
    delta = np.where(ok, dl, np.inf)
    dem = np.asarray(inst.clients.demand, dtype=float)
    kinf = bool(inst.kappa_infinite)
    st = inst.stranding
    Tdr = np.array([L.T_dr_s for L in inst.llms])
    mu_kv, mu_fb = np.asarray(st.mu_kv_usd), np.asarray(st.mu_fb_usd)
    mu_fl = np.where((np.asarray(st.mu_fl_usd) > 0) & (Tdr > 0), st.mu_fl_usd, 0.0)
    piW = np.asarray(st.pi_usd_per_min) * float(st.W_f_min)
    clients = [[c for c in range(n) if cl[c] == j] for j in range(J)]
    for al in acts.values():
        for a in al:
            assert isinstance(a, (Buy, Release)), a
            assert not isinstance(a, Buy) or a.admission == 1.0, a
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
    leases = {L.id: L for L in res.leases}
    W = np.zeros((Tf + 1, J, m))                  # W[f + 1] = realized capacity of fast slot f (W[0] = 0)
    active = defaultdict(set)                     # fast slot -> replicas with capacity 1 there
    for r in res.replicas:
        L = leases[r.lease_id]
        lo, hi = max(int(r.warm_fast), L.start_min // Df), min(int(r.end_fast), L.end_min // Df)
        if hi > lo:
            W[lo + 1:hi + 1, r.llm, L.site] += 1.0
            for f in range(lo, hi):
                active[f].add(r.id)
    reps = {r.id: r for r in res.replicas}
    kap = (mu_kv + mu_fl + mu_fb + piW)
    out = {}
    for t in slots:
        f0 = t * phi
        p, rent = _purchases_and_rent(inst, res, t, acts.get(t, []))
        G = S = 0.0
        fl = f0 + phi - 1                             # the reserve R(t): kappa'_c UB_c at the last fast slot
        R = 0.0
        for j in range(J):
            lbl = _lb_served(clients[j], dem[:, fl], W[fl + 1, j], delta, ok, kinf)
            ubl = _ub_served(clients[j], dem[:, fl], W[fl + 1, j], lbl, ok, kinf)
            R += sum(kap[j] * ubl[c] for c in clients[j])
        for f in range(f0, f0 + phi):
            WB = np.zeros((J, m))
            for rid in sorted(active.get(f, ())):
                r = reps[rid]
                L = leases[r.lease_id]
                c = inst.contracts[L.contract]
                ends = (f + 1) * Df
                inB = (c.protected or ends <= L.start_min + c.D_min(Ds)
                       or (L.announce_slot is not None and L.announce_slot <= t and ends <= L.death_min))
                if inB:
                    WB[r.llm, L.site] += 1.0
            d = dem[:, f]
            dp = dem[:, f - 1] if f > 0 else np.zeros(n)
            for j in range(J):
                G += _greedy_cost(clients[j], d, WB[j], float(q[j]), delta, ok, kinf) * Df / 60.0
                if f > 0:
                    lbp = _lb_served(clients[j], dp, W[f, j], delta, ok, kinf)
                else:
                    lbp = {c: 0.0 for c in clients[j]}
                ub = _ub_served(clients[j], dp, W[f, j], lbp, ok, kinf)
                lb = _lb_served(clients[j], d, W[f + 1, j], delta, ok, kinf)
                if f == f0:
                    drop = bool(np.any(W[f, j] > 0))
                else:
                    drop = any(reps[rid].llm == j for rid in active.get(f - 1, set()) - active.get(f, set()))
                for c in clients[j]:
                    e = min(min(dp[c], d[c]), ub[c])
                    S += (mu_kv[j] + mu_fl[j] * drop) * e + (mu_fb[j] + piW[j] * drop) * max(e - lb[c], 0.0)
        out[t] = ((alg[t - 1] if t > 0 else 0.0) + p + rent + G + S, G, S, R)
    return out


def _t0g_full_check(inst, model, inner: str, tag, guard_kw=None) -> dict:
    """A8 around `inner` under T0g on a full-model instance: the report's a-hat, G, S and reserve R (also the one
    in the guard's test) equal the oracle's at every executed slot, and ALG(t) <= a-hat(t) there (soundness,
    including the stranding charges)."""
    rec = policy_actions_recorder(_inner(inner))
    pol = Guarded(inner=rec, test="T0g", N_bound=_N(inst), **(guard_kw if guard_kw is not None else NO_ABORT))
    res = simulate(inst, pol, model, policy_seed=0)
    assert res.invariant_failures == [], (tag, res.invariant_failures[:3])
    rep = res.metrics["policy"]
    t0g = rep["t0g"]
    T = inst.grid.T_slow
    assert t0g["robust_since"] is None and not t0g["robust_all"] and t0g["uncertain_buys"] == 0, (tag, t0g["events"])
    t_a = rep["t_a"]
    ex = [t for t in rep["guard"]["slots"] if t_a is None or t < t_a]
    assert t0g["slots"] == list(rep["guard"]["slots"]) and t0g["forms"] == {"bound": len(t0g["slots"])}, tag
    acts = _acts_by_slot(rec)
    orc = _t0g_oracle(inst, res, acts, ex)
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
    a_rep = rep["guard"]["a_hat"]
    strand = np.asarray(res.per_slot["stranding"], dtype=float)
    t0_unsound = 0
    for i, t in enumerate(ex):
        ah, G, S, R = orc[t]
        assert _close(a_rep[i], ah, T0G_TOL), (tag, t, a_rep[i], ah)
        assert _close(t0g["G"][i], G, T0G_TOL) and _close(t0g["S"][i], S, T0G_TOL), (tag, t, t0g["G"][i], G, t0g["S"][i], S)
        assert _close(t0g["reserve"][i], R, T0G_TOL), (tag, t, t0g["reserve"][i], R)              # the reserve R(t)
        assert _close(rep["guard"]["reserve"][i], R, T0G_TOL), (tag, t)                            # in the test
        assert alg[t] <= ah + T0G_TOL * max(1.0, alg[t]), (tag, t, alg[t], ah)          # sound: m(t) = 0
        p, rent = _purchases_and_rent(inst, res, t, acts.get(t, []))
        a0 = (alg[t - 1] if t > 0 else 0.0) + p + rent + t0g["Q"][i]                     # T0's a-hat
        t0_unsound += int(alg[t] > a0 + T0G_TOL * max(1.0, alg[t]))
    return {"slots": len(ex), "T": T, "strand_slots": int(np.sum(strand[ex] > 1e-12)), "t0_unsound": t0_unsound,
            "t_a": t_a}


def test_t0g_params_and_ratchet():
    """test = 'T0g' (§3.4): Ratchet and Guarded accept it (T0g is the default since 2026-10-17; this test asserted
    the default 'T0' before); T0g's test value adds the same terms as T0's (the caller passes its service term);
    other names are rejected; A8's report carries 't0g' only under T0g."""
    assert guard.TESTS == ("T0", "T1", "T0g") and Guarded.PARAMS["test"] == "T0g"
    assert Ratchet(1.0, "T0g").test_value(1.0, 2.0, 3.0, 4.0) == 10.0
    assert Guarded(inner="BL1", test="T0g", N_bound=10).params()["test"] == "T0g"
    for bad in ("t0g", "T0G", "T2"):
        with pytest.raises(PolicyError):
            Ratchet(1.0, bad)
        with pytest.raises(PolicyError):
            Guarded(inner="BL1", test=bad, N_bound=10)
    inst = _ms(3, 120)
    for test in ("T0", "T0g"):
        rep = simulate(inst, Guarded(inner="BL1", test=test, N_bound=_N(inst)), LenderModel(), policy_seed=0).metrics["policy"]
        assert ("t0g" in rep) == (test == "T0g") and rep["test"] == test


def test_t0g_full_model_sound_quick():
    """T0g is sound in the full model (quick variant of test_t0g_full_model_sound): ms s3 on a 6-h horizon under
    trace and eager, A8 around A7, BL1 and BL5 without an abort; the report's a-hat, G and S equal the oracle's
    and ALG(t) <= a-hat(t) at every slot, also where the slot has stranding charges."""
    inst = _ms(3, 360)
    strand = 0
    for name, sch, par in FULL_MODES[:2]:
        for inner in ("A7", "BL1", "BL5"):
            if inner == "A7" and not HAVE_A7:
                continue
            o = _t0g_full_check(inst, LenderModel(schedule=sch, params=dict(par)), inner, ("ms s3 6h", name, inner))
            assert o["slots"] == inst.grid.T_slow
            strand += o["strand_slots"]
    assert strand > 0                                   # the stranding term is exercised


@pytest.mark.slow
@pytest.mark.parametrize("name,seed", [("ms2_multi_small", 3), ("q44_spot_1day", 1),
                                       pytest.param("example_1day", 1, marks=pytest.mark.needs_a12)])
def test_t0g_full_model_sound(name, seed):
    """T0g is sound in the full model (§3.4, §3.10; T0gBound's proof): on the whole day of `name` (config seed
    `seed`) under the lenders trace, eager, iid_step (p = 0.05) and correlated (p_sh = 1), A8 around A7, BL1 and
    BL5 with no abort (B0 = 1e12), and with the default guard (executed slots only): T0g's a-hat, G and S equal
    the independent oracle at every executed slot and ALG(t) <= a-hat(t) there. T0, which leaves the stranding
    charges out, is exceeded by ALG(t) at some slot of these runs (so T0g bounds what T0 does not)."""
    inst = _full(name, seed)
    tot = {"strand": 0, "t0_unsound": 0}
    for mode, sch, par in FULL_MODES:
        model = LenderModel(schedule=sch, params=dict(par))
        for inner in ("A7", "BL1", "BL5"):
            if inner == "A7" and not HAVE_A7:
                continue
            for kw in (NO_ABORT, {}):
                o = _t0g_full_check(inst, model, inner, (name, seed, mode, inner, bool(kw)), kw)
                tot["strand"] += o["strand_slots"]
                tot["t0_unsound"] += o["t0_unsound"]
    assert tot["strand"] > 0 and tot["t0_unsound"] > 0, tot


# ---------------------------------------------------------------- T0g against check_guard.py's core T0g
def _check_guard():
    import check_guard
    return check_guard


class _ReplayE:
    """check_guard inner policy that replays the engine run's recorded actions: Buys by type (l, j, k) in list
    order, Releases mapped from engine lease ids (creation order) to the core leases (check_guard._UID)."""

    def __init__(self, acts: dict, cg):
        self.acts, self.cg = acts, cg
        self.uid_of: dict[int, int] = {}
        self.next_id = 0

    def decide(self, t, held, ALG):
        al = self.acts.get(t, [])
        by_uid = {L.uid: L for L in held}
        rel = [by_uid[self.uid_of[int(a.lease_id)]] for a in al if isinstance(a, Release)]
        new = []
        base = self.cg._UID[0]
        for a in al:
            if isinstance(a, Buy):
                assert a.n_replicas == 1
                new.append((int(a.site), int(a.llm), int(a.contract)))
                self.uid_of[self.next_id] = base + len(new)
                self.next_id += 1
        return rel, new


def _core_lender(cg, ctx, I, sched, om):
    if sched == "adaptive":
        return cg.Lender(ctx, "t4", None, "0")
    if sched == "eager":
        return cg.Lender(ctx, "obl", [np.arange(I.T)] * I.m, "0")
    if sched == "none":
        return cg.Lender(ctx, "obl", [np.zeros(0, dtype=int)] * I.m, "0")
    return cg.Lender(ctx, "obl", om, "0")


def _export(I, sched: str, seed: int):
    """(instance, model, core omega) of a schedule on from_core(I): 'oblivious' Bernoulli(0.1) trace sets (rng
    7000 + seed), 'none' (no announcement), 'eager' and 'adaptive' (C3-T4's lender)."""
    if sched == "oblivious":
        om = core.random_omega(np.random.default_rng(7000 + seed), I, 0.1)
        return from_core(I, om)[0], LenderModel(), om
    inst, _ = from_core(I, [np.zeros(0, np.int64)] * I.m)
    return inst, LenderModel(schedule="eager" if sched == "eager" else
                             "adaptive" if sched == "adaptive" else "trace"), None


def _extension(inst, res, t, acts) -> bool:
    """Whether a lease held after the actions of slot t is past its guaranteed window, announced by t and alive
    through the slot: the leases that T0g counts and check_guard's minimal set does not."""
    g = inst.grid
    rel = {a.lease_id for a in acts if isinstance(a, Release)}
    for L in res.leases:
        held = (L.start_slot == t) or (_alive_at_obs(L, t, g.slow_min, g.fast_min) and L.id not in rel)
        if not held:
            continue
        D = inst.contracts[L.contract].D_min(g.slow_min)
        past = D is not None and (t + 1) * g.slow_min > L.start_min + D
        if past and L.announce_slot is not None and L.announce_slot <= t and L.death_min >= (t + 1) * g.slow_min:
            return True
    return False


def test_t0g_equals_core_t0g():
    """On exact core exports T0g is check_guard.py's core T0g (§9 of C3; T0gBound docstring): the engine run of A8
    under T0g (no abort) and check_guard.run (mode 'never') with the same actions replayed on the core instance
    give equal ALG(t) and, without announcements, under the eager and the C3-T4 adaptive lenders, equal a-hat(t)
    at every slot. Under Bernoulli(0.1) trace sets T0g also counts the held leases past their window that are
    announced and alive through the slot (C3's minimal set leaves them out): a-hat(t) is equal at every slot
    without such a lease and never larger. Instances: check_c3_upper families (seeds 0, 1), C3-P5 (beta 2, 30),
    cat-and-mouse (2, 4) and (4, 8); inner policies BL1, BL5, A6 (and A7) in rotation."""
    cg = _check_guard()
    cases = [(f"{f}{s}", upper_case(f, s), s) for f in UPPER_FAMS for s in (0, 1)]
    cases += [(f"c3p5 {b}", c3p5_case(b), 0) for b in (2, 30)] + [(f"cm {m} {r}", cm_case(m, r), 0) for m, r in ((2, 4), (4, 8))]
    i = 0
    n = {"slots": 0, "ext": 0, "strict": 0}
    for name, I, seed in cases:
        for sched in ("none", "oblivious", "eager", "adaptive"):
            inst, model, om = _export(I, sched, seed)
            iid = CORE_INNERS[i % len(CORE_INNERS)]
            i += 1
            rec = policy_actions_recorder(_inner(iid))
            pol = Guarded(inner=rec, test="T0g", N_bound=_N(inst), **NO_ABORT)
            res = simulate(inst, pol, model, policy_rng=np.random.default_rng(0))
            tag = (name, sched, iid)
            assert res.invariant_failures == [], tag
            acts = _acts_by_slot(rec)
            assert len(res.leases) == sum(isinstance(a, Buy) for al in acts.values() for a in al), tag
            ctx = cg.Ctx(I, name)
            out = cg.run(ctx, cg.Guard(ctx, None, 1.0, "T0g", "zero"), _ReplayE(acts, cg),
                         _core_lender(cg, ctx, I, sched, om), mode="never")
            alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
            assert np.allclose(alg, out["cum"], rtol=1e-12, atol=1e-9), tag
            a_eng = np.asarray(res.metrics["policy"]["guard"]["a_hat"], dtype=float)
            assert res.metrics["policy"]["t0g"]["S"] == [0.0] * I.T, tag                    # no stranding on core exports
            for t in range(I.T):
                ext = _extension(inst, res, t, acts.get(t, []))
                n["slots"] += 1
                n["ext"] += int(ext)
                if not ext:
                    assert _close(a_eng[t], out["ahat"][t], 1e-12), (tag, t, a_eng[t], out["ahat"][t])
                else:
                    assert sched == "oblivious", (tag, t)
                    assert a_eng[t] <= out["ahat"][t] + 1e-9 * max(1.0, abs(out["ahat"][t])), (tag, t)
                    n["strict"] += int(a_eng[t] < out["ahat"][t] - 1e-9)
    assert n["ext"] < n["slots"], n


# ---------------------------------------------------------------- T0g aborts no earlier than T0
def _paired(inst, model, inner, kw, rng_seed=None, policy_seed=0) -> dict:
    """A8 around `inner` with identical streams under T0, under T0g's test value alone (reserve false: the T0g of
    commit d2a538d, which these tests compare with T0) and under the default T0g with the wind-down reserve:
    T0g without the reserve aborts no earlier than T0, the default aborts no later than T0g without the reserve (the
    reserve only adds to the test value), and the three runs are equal before the first abort. Returns {name: t_a}
    with the names 'T0', 'T0g' (no reserve) and 'T0gR' (default). (Before 2026-10-17 'T0g' was the default.)"""
    out = {}
    for name, extra in (("T0", {"test": "T0"}), ("T0g", {"test": "T0g", "reserve": False}), ("T0gR", {"test": "T0g"})):
        pol = Guarded(inner=inner, N_bound=_N(inst), **extra, **kw)
        if rng_seed is None:
            res = simulate(inst, pol, model, policy_seed=policy_seed)
        else:
            res = simulate(inst, pol, model, policy_rng=np.random.default_rng(rng_seed))
        assert res.invariant_failures == [], (inner, name)
        out[name] = (res.metrics["policy"]["t_a"], np.asarray(res.per_slot["total"], dtype=float))
    (ta0, c0), (tag, cg_), (taR, cR) = out["T0"], out["T0g"], out["T0gR"]
    assert tag is None or (ta0 is not None and tag >= ta0), ("T0g aborted earlier", inner, ta0, tag)
    assert taR is not None or tag is None, ("the reserve removed an abort", inner, tag, taR)
    assert tag is None or taR <= tag, ("the reserve delayed an abort", inner, tag, taR)
    first = min(x for x in (ta0, tag, taR, len(c0)) if x is not None)
    assert np.array_equal(c0[:first], cg_[:first]) and np.array_equal(c0[:first], cR[:first]), inner   # E alone
    return {"T0": ta0, "T0g": tag, "T0gR": taR}


def _no_earlier_core(cases) -> dict:
    inners = ("BL1", "BL5") + (("A7",) if HAVE_A7 else ())
    combos = [dict(safe=s, gamma=g, **ALLOWANCES[a]) for s in ("pd", "fb+pd") for g in GAMMAS_X for a in ALLOWANCES]
    i = 0
    n = {"runs": 0, "t0_abort": 0, "later": 0}
    for I in cases:
        for sched in SCHEDS:
            inst, model = _core_inst(I, sched, 0)
            for inner in inners:
                for kw in ({}, combos[i % len(combos)]):
                    o = _paired(inst, model, inner, kw, rng_seed=0)
                    n["runs"] += 1
                    n["t0_abort"] += int(o["T0"] is not None)
                    n["later"] += int(o["T0"] is not None and (o["T0g"] is None or o["T0g"] > o["T0"]))
                i += 1
    return n


def test_t0g_no_earlier_than_t0_core_quick():
    """T0g never aborts earlier than T0 (§3.4, remark T0g against T0) on exact core exports, where T0g's a-hat is
    at most T0's at every slot: paired runs (policy generator default_rng(0) for both) of A8 around A7, BL1 and
    BL5 with the default parameters and with one of safe in {pd, fb+pd} x gamma in {0.25, 1, 1 + 1/sqrt 2, 3} x
    the three allowances (in rotation) under the oblivious, eager and adaptive schedules (quick: check_c3_upper
    'rand' and 'slo' seed 0, C3-P5 beta 14, cat-and-mouse (2, 4)); T0 aborts in some runs and T0g strictly later
    or not at all in some; the paired runs are equal before the first abort."""
    n = _no_earlier_core([upper_case("rand", 0), upper_case("slo", 0), c3p5_case(14), cm_case(2, 4)])
    assert n["t0_abort"] > 0 and n["later"] > 0, n


@pytest.mark.slow
def test_t0g_no_earlier_than_t0_core():
    """test_t0g_no_earlier_than_t0_core_quick on every check_c3_upper family (seeds 0, 1), C3-P5 (beta 2, 14, 30)
    and the cat-and-mouse instances (2, 4) and (4, 8)."""
    cases = [upper_case(f, s) for f in UPPER_FAMS for s in (0, 1)] + [c3p5_case(b) for b in (2, 14, 30)] \
        + [cm_case(2, 4), cm_case(4, 8)]
    n = _no_earlier_core(cases)
    assert n["t0_abort"] > 0 and n["later"] > 0, n


def test_t0g_no_earlier_than_t0_full_quick():
    """T0g's test value aborts no earlier than T0 in the full model (quick): ms s3 on a 6-h horizon under trace and
    eager, A8 around A7, BL1 and BL5 with the default allowance, paired runs with identical streams (policy seed 0;
    _paired, which also runs the default T0g with the reserve). (In the full model T0g's a-hat can exceed T0's
    where T0 misses a slot's stranding charges, so this is a measured property there, not an identity; with the
    reserve the default T0g can abort earlier than T0, test_t0g_no_earlier_than_t0_full.)"""
    inst = _ms(3, 360)
    trips = 0
    for name, sch, par in FULL_MODES[:2]:
        for inner in ("A7", "BL1", "BL5"):
            if inner == "A7" and not HAVE_A7:
                continue
            o = _paired(inst, LenderModel(schedule=sch, params=dict(par)), inner, {})
            trips += int(o["T0"] is not None)
    assert trips > 0


def test_t0g_earlier_than_t0_toy():
    """In the full model T0g can abort earlier than T0, because T0 leaves the slot's stranding charges out: on the
    toy (L0's R from R_rate 0.3, config seed 7) under the eager lender, A8 around BL1 aborts at slot 7 under T0
    and, with T0g's test value alone (reserve false, the T0g of commit d2a538d), at slot 6. At slot 6 the T0 run
    executes BL1's actions and its real cost ALG(6) exceeds both gamma C_S(6) + B(6) and T0's a-hat(6) by the slot's
    stranding charge, while T0g's a-hat(6) is ALG(6): T0g's earlier abort is the one the real cost calls for. The
    default T0g (with the wind-down reserve; this test checked the T0g without it before 2026-10-17) aborts at slot
    5: there a-hat(5) <= gamma C_S(5) + B(5) < a-hat(5) + R(5), so the reserve alone trips it, and its run equals the
    others before slot 5."""
    from fixtures import DELETE, toy_config
    cfg = toy_config({"lenders.0.R": DELETE, "lenders.0.R_rate": 0.3})
    cfg["seed"] = 7
    inst = build_instance(cfg)
    runs = {}
    for name, kw in (("T0", dict(test="T0")), ("T0g", dict(test="T0g", reserve=False)), ("default", {})):
        res = simulate(inst, Guarded(inner="BL1", N_bound=_N(inst), **kw), LenderModel(schedule="eager"),
                       policy_seed=0)
        assert res.invariant_failures == []
        runs[name] = (res, res.metrics["policy"])
    (r0, p0), (r1, p1), (r2, p2) = runs["T0"], runs["T0g"], runs["default"]
    assert (p0["t_a"], p1["t_a"], p2["t_a"]) == (7, 6, 5)
    alg0 = np.cumsum(np.asarray(r0.per_slot["total"], dtype=float))
    strand6 = float(r0.per_slot["stranding"][6])
    rhs6 = p0["guard"]["rhs"][6]
    assert strand6 > 0 and _close(p0["guard"]["rhs"][6], p1["guard"]["rhs"][6])
    assert p0["guard"]["a_hat"][6] <= rhs6 < alg0[6]                                   # T0 executes, ALG(6) above the threshold
    assert _close(alg0[6] - p0["guard"]["a_hat"][6], strand6)                         # T0 misses exactly the stranding
    assert _close(p1["guard"]["a_hat"][6], alg0[6]) and p1["guard"]["a_hat"][6] > rhs6
    g2 = p2["guard"]
    assert g2["a_hat"][5] <= g2["rhs"][5] < g2["a_hat"][5] + g2["reserve"][5]           # the reserve trips slot 5
    assert _close(g2["a_hat"][5], p1["guard"]["a_hat"][5]) and _close(g2["rhs"][5], p1["guard"]["rhs"][5])
    tot = [np.asarray(r.per_slot["total"], dtype=float)[:5] for r in (r0, r1, r2)]
    assert np.array_equal(tot[0], tot[1]) and np.array_equal(tot[1], tot[2])


@pytest.mark.slow
@pytest.mark.parametrize("name,seed", [("ms2_multi_small", 3), ("ms2_multi_small", 4), ("q44_spot_1day", 1),
                                       ("q44_spot_1day", 2), pytest.param("example_1day", 1, marks=pytest.mark.needs_a12),
                                       pytest.param("example_1day", 2, marks=pytest.mark.needs_a12)])
def test_t0g_no_earlier_than_t0_full(name, seed):
    """T0g's test value (reserve false, the T0g of commit d2a538d) aborts no earlier than T0 on the whole day of
    `name` (config seed `seed`) under the lenders trace, eager, iid_step (p = 0.05) and correlated (p_sh = 1), A8
    around A7, BL1 and BL5 with the default allowance (paired runs with identical streams, policy seed 0); the
    runs are equal before the first abort. A measured property of these cells, not an identity of the full model
    (test_t0g_earlier_than_t0_toy). The default T0g, with the wind-down reserve, aborts no later than T0g without it
    (_paired) and, on q44_spot_1day s1 and example_1day s1, earlier than T0 in some run (until 2026-10-17 this
    test compared T0 with T0g without the reserve, then the default, and found no earlier abort)."""
    inst = _full(name, seed)
    earlier = 0
    for mode, sch, par in FULL_MODES:
        for inner in ("A7", "BL1", "BL5"):
            if inner == "A7" and not HAVE_A7:
                continue
            o = _paired(inst, LenderModel(schedule=sch, params=dict(par)), inner, {})
            earlier += int(o["T0gR"] is not None and (o["T0"] is None or o["T0gR"] < o["T0"]))
    if (name, seed) in (("q44_spot_1day", 1), ("example_1day", 1)):
        assert earlier > 0, (name, seed)


# ---------------------------------------------------------------- the twin of S under T0g
class _Twin(Policy):
    """The twin of the guard's S (§3.4, remark T0g against T0): it runs its own SafeExpert, built exactly as
    Guarded builds S from an identical copy of the policy generator (so it shares R's coins), executes S by Lemma
    G1(b) from slot 0 (buys P_S(u) at every u: R's opened columns while S follows R, copies of R's live set at a
    switch to R) and releases each lease at the end of its guaranteed window."""
    name = "twin"

    def __init__(self, safe: str, N_bound: int, rbar="theory", gamma_T11: float = G2):
        self.args = dict(safe=safe, rbar=rbar, N_bound=N_bound, gamma_T11=gamma_T11)

    def reset(self, view, rng):
        super().reset(view, rng)
        self.sx = guard.SafeExpert(view, rng, **self.args)
        self.slow = view.grid.slow_min
        self.D = [c.D_min(self.slow) for c in view.contracts]

    def act(self, obs):
        self.sx.step(obs)
        t = int(obs.t)
        acts = [Release(lid) for lid, L in obs.leases.items()
                if self.D[L.contract] is not None and L.start_min + self.D[L.contract] <= t * self.slow]
        for col in self.sx.purchases:
            l, j, k, s, iota, L = self.sx.column(col)
            acts.append(Buy(l, k, j, 1, tag="twin"))
        return acts


def _twin_runs(cases, gammas, tests=("T0g",)) -> dict:
    n = defaultdict(int)
    for I in cases:
        for sched in SCHEDS:
            inst, model = _core_inst(I, sched, 0)
            for safe in ("pd", "fb+pd"):
                for gm in gammas:
                    for an in ALLOWANCES:
                        for test in tests:
                            pol = Guarded(inner=_Twin(safe, _N(inst)), safe=safe, gamma=gm, test=test, N_bound=_N(inst),
                                          **ALLOWANCES[an])
                            res = simulate(inst, pol, model, policy_rng=np.random.default_rng(0))
                            tag = (sched, safe, gm, an, test)
                            assert res.invariant_failures == [], tag
                            rep = res.metrics["policy"]
                            n[(test, "runs")] += 1
                            if test == "T0g":
                                assert rep["t_a"] is None, ("twin aborted under T0g", tag, rep["t_a"])
                                alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
                                C_S = np.asarray(rep["safe"]["C_S_curve"], dtype=float)
                                assert np.all(alg <= C_S + TOL * np.maximum(1.0, C_S)), tag     # Lemma G1(b) from slot 0
                            else:
                                n[(test, "aborted")] += int(rep["t_a"] is not None)
    return dict(n)


def test_t0g_twin_never_aborted_quick():
    """§3.4 remark: under T0g with gamma >= 1 the guard never aborts the twin of S, whatever the allowance (quick:
    check_c3_upper 'rand' seed 0 and C3-P5 beta 14; schedules oblivious, eager and adaptive; safe pd and fb+pd;
    gamma 1, 1 + 1/sqrt 2, 3; allowances 0, B0, capped); the twin's ALG(t) <= C_S(t) at every slot; under T0 the
    same twin is aborted in some runs."""
    n = _twin_runs([upper_case("rand", 0), c3p5_case(14)], (1.0, G2, 3.0), tests=("T0g", "T0"))
    assert n[("T0g", "runs")] == 2 * 3 * 2 * 3 * 3 and n.get(("T0", "aborted"), 0) > 0, n


@pytest.mark.slow
def test_t0g_twin_never_aborted():
    """The twin claim of test_t0g_twin_never_aborted_quick on every check_c3_upper family (seeds 0, 1), C3-P5
    (beta 2, 6, 14, 30) and the cat-and-mouse instances (2, 4), (4, 8)."""
    cases = [upper_case(f, s) for f in UPPER_FAMS for s in (0, 1)] + [c3p5_case(b) for b in (2, 6, 14, 30)] \
        + [cm_case(2, 4), cm_case(4, 8)]
    n = _twin_runs(cases, (1.0, G2, 3.0))
    assert n[("T0g", "runs")] == len(cases) * 3 * 2 * 3 * 3, n


# ---------------------------------------------------------------- core bound (§6.3) with T0g and the gamma grid
def _a_hat_core_t0g(inst, res, t, alg_prev, acts) -> float:
    """T0g's a-hat(t) on an exact core export, from the records: purchases and rent as T0, and per request of
    slot t min{q, min delta over the leases of its LLM held after E's actions that are inside their guaranteed
    window or announced by t with death after the slot}: the lease records alive at the observation and not
    released by E at t, and E's Buys of t (from the recorded actions, which at an abort slot differ from the
    purchases executed there)."""
    g = inst.grid
    slow = g.slow_min
    p, rent = _purchases_and_rent(inst, res, t, acts)
    rel = {a.lease_id for a in acts if isinstance(a, Release)}
    llm_of = {r.lease_id: r.llm for r in res.replicas}
    sites = defaultdict(set)
    for a in acts:
        if isinstance(a, Buy):
            sites[int(a.llm)].add(int(a.site))                    # inside its window throughout slot t
    for L in res.leases:
        if not (L.start_slot < t and _alive_at_obs(L, t, slow, g.fast_min) and L.id not in rel):
            continue
        D = inst.contracts[L.contract].D_min(slow)
        end = (t + 1) * slow
        if D is None or end <= L.start_min + D or (L.announce_slot is not None and L.announce_slot <= t
                                                   and L.death_min >= end):
            sites[llm_of[L.id]].add(L.site)
    q = np.array([x.q_usd_per_h for x in inst.llms])
    cl = np.asarray(inst.clients.llm)
    dl = np.asarray(inst.clients.delta_usd_per_h, dtype=float)
    d = np.asarray(inst.clients.demand, dtype=float)[:, t * g.phi:(t + 1) * g.phi].sum(axis=1)
    serv = 0.0
    for c in range(inst.n):
        j = int(cl[c])
        best = min([dl[c, l] for l in sites[j] if np.isfinite(dl[c, l]) and dl[c, l] < q[j]] + [q[j]])
        serv += best * d[c] * g.fast_min / 60.0
    return alg_prev + p + rent + serv


def _certificate_x(I, inst, res, pol, rec_E, prm, opened_R, curve_R, opt_eager, tag) -> dict:
    """_certificate for the tests T0, T0g and T1: as there, with T0g's a-hat recomputed by _a_hat_core_t0g,
    m = 0 for the sound tests T0 and T0g, T0g's a-hat <= T0's at every executed slot, and Corollary G3 for both
    sound tests with the capped allowance."""
    test = prm["test"]
    if test != "T0g":
        return _certificate(I, inst, res, pol, rec_E, prm, opened_R, curve_R, opt_eager, tag)
    assert res.invariant_failures == [], (tag, res.invariant_failures[:3])
    rep = res.metrics["policy"]
    T = I.T
    gamma, safe, kappa = float(prm["gamma"]), prm["safe"], prm["kappa"]
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))

    def A(t):
        return 0.0 if t < 0 else float(alg[t])
    fb = I.q * np.asarray(I.active).sum(axis=0).astype(float)
    live_cost, buy_cost = np.zeros(T), np.zeros(T)
    for F, t0 in opened_R.items():
        _, l, j, k, s0 = F[:5]
        c, L = I.C(l, j, k), int(I.L[k])
        buy_cost[t0] += c
        for u in range(t0, min(s0 + L, T)):
            live_cost[u] += c
    if safe == "pd":
        C_S = np.cumsum(curve_R)
        follow = [("R", False)] * T
    else:
        cb = _combiner(fb, curve_R, live_cost, buy_cost, float(prm["gamma_T11"]))
        C_S = np.array([x[2] for x in cb])
        follow = [(x[0], x[1]) for x in cb]
    assert np.allclose(rep["safe"]["C_S_curve"], C_S, rtol=TOL, atol=TOL), tag
    B_on = _B_on_core(I)
    assert np.allclose(rep["safe"]["B_on"], B_on, rtol=TOL, atol=TOL), tag
    B0 = _b0_core(I) if prm["B0"] == "auto" else float(prm["B0"])
    B = np.full(T, B0) if kappa is None else np.minimum(B0, kappa * B_on)

    def Bt(t):
        return 0.0 if t < 0 else float(B[t])
    assert B_on[-1] <= opt_eager + TOL * max(1.0, opt_eager), tag                          # Lemma G5
    acts = defaultdict(list)
    for t, a in rec_E.actions:
        if not isinstance(t, tuple):
            acts[t].append(a)
    t_a = rep["t_a"]
    last = T - 1 if t_a is None else t_a
    g_rep = rep["guard"]
    assert g_rep["slots"] == list(range(last + 1)), tag
    m = {}
    for t in range(last + 1):
        ah = _a_hat_core_t0g(inst, res, t, A(t - 1), acts[t])
        ah0 = _a_hat(inst, res, t, A(t - 1), acts[t], "T0", float(fb[t]))
        rhs = gamma * C_S[t] + Bt(t)
        assert _close(g_rep["a_hat"][t], ah), (tag, t, g_rep["a_hat"][t], ah)
        assert ah <= ah0 + TOL * max(1.0, abs(ah0)), (tag, t, ah, ah0)                     # T0g <= T0 on core exports
        assert _close(g_rep["rhs"][t], rhs), (tag, t)
        if t == t_a:
            if not g_rep["forced"]:
                assert ah > rhs - TOL * max(1.0, abs(rhs)), (tag, t, ah, rhs)
            break
        assert ah <= rhs + TOL * max(1.0, abs(rhs)), (tag, t, ah, rhs)
        m[t] = max(0.0, A(t) - ah)
        assert m[t] <= TOL * max(1.0, A(t)), (tag, t, m[t])                                # m = 0 under T0g
    for t, mv in enumerate(g_rep["m"]):
        if mv is not None:
            assert _close(mv, m[t]), (tag, t, mv, m[t])
    ALG = A(T - 1)
    C_T = float(C_S[-1])
    scale = max(1.0, ALG)
    out = {"t_a": t_a, "ALG": ALG, "C_S": C_T}
    if t_a is None:
        assert ALG <= gamma * C_T + Bt(T - 1) + TOL * scale, tag                            # Theorem G2(a)
    else:
        cur, sw = follow[t_a]
        W = 0.0
        if cur == "R" and not sw:
            W = sum(I.C(F[1], F[2], F[3]) for F, t0 in opened_R.items() if t0 < t_a < F[4] + int(I.L[F[3]]))
        assert _close(rep["W_S_t_a"], W), (tag, rep["W_S_t_a"], W)
        C_prev = float(C_S[t_a - 1]) if t_a > 0 else 0.0
        excess = (ALG - A(t_a - 1)) - (W + C_T - C_prev)
        assert excess <= TOL * scale, (tag, "S-mode excess", excess)                       # Lemma G1(b)
        bound = C_T + (gamma - 1) * C_prev + W + Bt(t_a - 1)
        assert ALG <= bound + TOL * scale, (tag, ALG, bound)                               # Theorem G2(b), m = 0
    assert ALG <= (1 + gamma) * C_T + Bt(T - 1) + TOL * scale, tag                          # Theorem G2(c), M = 0
    if kappa is not None:
        assert ALG <= (1 + gamma) * C_T + kappa * B_on[-1] + TOL * scale, tag              # Corollary G3
    return out


# the 48 (test, safe, gamma, allowance) not in COMBOS: T0g on the gamma grid, T0 and T1 at gamma 0.25 and 3
COMBOS_X = tuple((test, safe, gm, an) for test in ("T0g", "T0", "T1") for safe in ("pd", "fb+pd") for gm in GAMMAS_X
                 for an in ALLOWANCES if test == "T0g" or gm in (0.25, 3.0))


def _core_runs_x(key, I, inners, combos, scheds=SCHEDS, seed=0, s=0) -> list:
    out = []
    oe = _opt_eager(key, I)
    i = 0
    for sched in scheds:
        inst, model = _core_inst(I, sched, seed)
        opened_R, curve_R = _a2_core(key, I, inst, "theory", s)
        for (test, safe, gm, an) in combos:
            iid = inners[i % len(inners)]
            i += 1
            prm = {"test": test, "safe": safe, "gamma": gm, "gamma_T11": G2, **ALLOWANCES[an]}
            rec_E = policy_actions_recorder(_inner(iid))
            pol = Guarded(inner=rec_E, N_bound=_N(inst), **prm)
            res = simulate(inst, pol, model, policy_rng=np.random.default_rng(s))
            tag = (key, sched, test, safe, round(gm, 3), an, iid)
            out.append(_certificate_x(I, inst, res, pol, rec_E, prm, opened_R, curve_R, oe, tag))
    return out


@pytest.mark.parametrize("fam_name", [f if f != "big" else pytest.param(f, marks=pytest.mark.slow) for f in UPPER_FAMS])
def test_core_bound_t0g_upper(fam_name):
    """§6.3 core bound extended to T0g and gamma in {0.25, 1, 1 + 1/sqrt 2, 3} on the instances of
    test_core_bound_upper (family `fam_name`, seeds 0-3, COMBOS_X[seed::4]) under the oblivious, eager and
    adaptive schedules: T0g's a-hat(t) recomputed from the records equals A8's and is at most T0's, m = 0, the
    trip at the first violating slot, Theorem G2(a)-(c), Corollary G3 (capped allowance), Lemma G5, the S-mode
    excess <= 1e-9; T0 and T1 at gamma 0.25 and 3 through _certificate."""
    out = []
    for seed in range(4):
        I = upper_case(fam_name, seed)
        out += _core_runs_x((fam_name, seed), I, CORE_INNERS, COMBOS_X[seed::4], seed=seed)
    assert len(out) == len(COMBOS_X) * len(SCHEDS)
    n_ab = sum(o["t_a"] is not None for o in out)
    assert 0 < n_ab < len(out), (fam_name, n_ab, len(out))


def test_core_bound_t0g_families():
    """§6.3 core bound with COMBOS_X on the C3-P5 instances (beta 2, 6, 14, 30; COMBOS_X[b::4]) and the
    cat-and-mouse instances (2, 4) and (4, 8) (COMBOS_X[0::2], COMBOS_X[1::2]) under the three schedules."""
    out = []
    for b, beta in enumerate((2, 6, 14, 30)):
        out += _core_runs_x(("c3p5", beta), c3p5_case(beta), CORE_INNERS, COMBOS_X[b::4])
    for i, (m, rho) in enumerate(((2, 4), (4, 8))):
        out += _core_runs_x(("cm", m, rho), cm_case(m, rho), CORE_INNERS, COMBOS_X[i::2])
    assert len(out) == 2 * len(COMBOS_X) * len(SCHEDS)
    n_ab = sum(o["t_a"] is not None for o in out)
    assert 0 < n_ab < len(out), (n_ab, len(out))


# ---------------------------------------------------------------- T0gBound: actions, robust form, checks
def _t0g_sound(res, tag) -> None:
    rep = res.metrics["policy"]
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
    t_a = rep["t_a"]
    for i, t in enumerate(rep["guard"]["slots"]):
        if t_a is not None and t >= t_a:
            break
        assert alg[t] <= rep["guard"]["a_hat"][i] + T0G_TOL * max(1.0, alg[t]), (tag, t, alg[t], rep["guard"]["a_hat"][i])


def _toy_fast():
    """The toy on 1-min fast slots (phi = 5) with a second client of the same LLM, both with on/off demand."""
    base = [0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0]
    rng = np.random.default_rng(5)
    d0 = [v * (0.5 + 0.5 * rng.random()) for v in repeat_fast(base, 5)]
    d1 = [float(rng.random() < 0.6) * 0.75 for _ in range(len(d0))]
    cl = load_json(CONFIGS / "toy.json")["borrowers"]["clients"][0]
    c0 = {**cl, "demand": {"kind": "array", "values": d0}}
    c1 = {**cl, "demand": {"kind": "array", "values": d1}}
    return toy_instance({"time.fast_slot_min": 1, "borrowers.clients": [c0, c1]})


def test_t0g_admission_actions():
    """T0gBound's replica model (class docstring) on the toy with 1-min fast slots: a scripted inner policy that
    buys at the three sites, sets an admission, drains at a later minute, re-drains a replica whose drain takes
    effect at the slot start (its admission is then unknown to the bound), unloads, loads and releases; every slot
    is executed (B0 = 1e12) and ALG(t) <= a-hat(t) at each; the slot whose list sets the admission of a replica
    bought in the same list uses the robust form, and only that slot; the report (a-hat, G, S and the reserve, at the
    robust slot and after it) equals _t0g_oracle_x's."""
    inst = _toy_fast()
    state = {"next_rep": 0}

    def rep_at(obs, site):
        return next((rid for rid, rv in sorted(obs.replicas.items()) if obs.leases[rv.lease_id].site == site), None)

    def lease_at(obs, site):
        return next((lid for lid, L in sorted(obs.leases.items()) if L.site == site), None)

    def plan(obs):
        t = obs.t
        if t == 0:
            return [Buy(0, 0, 0, 1), Buy(1, 1, 0, 1), Buy(2, 2, 0, 1)]
        if t == 2:
            return [SetAdmission(rep_at(obs, 0), 0.5), Drain(rep_at(obs, 1), 2 * 5 + 3)]
        if t == 3:
            return [Drain(rep_at(obs, 2), 3 * 5 + 5)]                 # takes effect at slot 4's first fast slot
        if t == 4:
            return [Drain(rep_at(obs, 2), 4 * 5 + 2)]                 # removes it before it is applied
        if t == 6:
            return [Unload(rep_at(obs, 2)), Load(lease_at(obs, 2), 0)]
        if t == 9:
            return [Release(lease_at(obs, 1))]
        if t == 11:
            return [Buy(1, 0, 0, 1), SetAdmission(state["next_rep"], 0.5)]   # a replica of this list
        if t == 13:
            return [SetAdmission(rep_at(obs, 2), 0.0)]
        return []

    def step(obs, pol):
        for r in obs.results:
            for rid in r.replica_ids:
                state["next_rep"] = max(state["next_rep"], int(rid) + 1)
        return plan(obs)
    script = {t: step for t in range(inst.grid.T_slow)}
    rec = _ObsRec(recording_policy(script))
    pol = Guarded(inner=rec, test="T0g", N_bound=_N(inst), **NO_ABORT)
    res = simulate(inst, pol, LenderModel(), policy_seed=0)
    assert res.invariant_failures == [], res.invariant_failures[:3]
    rep = res.metrics["policy"]
    assert rep["t_a"] is None
    t0g = rep["t0g"]
    assert t0g["robust_slots"] == [11] and t0g["robust_since"] is None, t0g
    assert len(res.replicas) == 5 and np.any(np.asarray(res.per_slot["stranding"]) > 0)
    _t0g_sound(res, "toy actions")
    _t0g_check_x(inst, res, rec, False, "toy actions")
    # a robust slot followed by bound slots on finite capacity with arcs that a client cannot use (ms s3, 2 h)
    inst = _ms(3, 120)
    assert not inst.kappa_infinite and not np.all(np.isfinite(inst.clients.delta_usd_per_h))
    state["next_rep"] = 0
    plan2 = {0: [Buy(0, 0, 0, 1), Buy(4, 1, 1, 1)], 2: [Buy(1, 1, 0, 1), SetAdmission(-1, 1.0)]}

    def step2(obs, pol):
        for r in obs.results:
            for rid in r.replica_ids:
                state["next_rep"] = max(state["next_rep"], int(rid) + 1)
        return [SetAdmission(state["next_rep"], 1.0) if isinstance(a, SetAdmission) else a for a in plan2.get(obs.t, [])]
    rec = _ObsRec(recording_policy({t: step2 for t in range(inst.grid.T_slow)}))
    pol = Guarded(inner=rec, test="T0g", N_bound=_N(inst), **NO_ABORT)
    res = simulate(inst, pol, LenderModel(), policy_seed=0)
    assert res.invariant_failures == [], res.invariant_failures[:3]
    t0g = res.metrics["policy"]["t0g"]
    assert t0g["robust_slots"] == [2] and np.all(np.isfinite(res.metrics["policy"]["guard"]["a_hat"])), t0g
    _t0g_sound(res, "ms robust slot")
    _t0g_check_x(inst, res, rec, False, "ms robust slot")


def test_t0g_robust_form():
    """C1: an inner policy that uses on_fast (wants_fast) gets the robust form at every slot, service(t) = Q(t) plus
    the stranding bound with every client counted; the bound stays sound and the report (a-hat, G, S and the reserve
    sum_c kappa'_c d_c(f_l) a_c) equals _t0g_oracle_x's with robust_all (toy with 1-min fast slots, a scripted inner
    with an on_fast hook)."""
    inst = _toy_fast()
    script = {0: [Buy(0, 0, 0, 1), Buy(2, 2, 0, 1)]}
    fs = {f: [] for f in range(inst.grid.T_fast)}
    rec = _ObsRec(recording_policy(script, fs))
    pol = Guarded(inner=rec, test="T0g", N_bound=_N(inst), **NO_ABORT)
    res = simulate(inst, pol, LenderModel(), policy_seed=0)
    assert res.invariant_failures == []
    t0g = res.metrics["policy"]["t0g"]
    assert t0g["robust_all"] and t0g["forms"] == {"robust": inst.grid.T_slow}
    assert np.allclose(t0g["G"], t0g["Q"], rtol=0, atol=0)
    _t0g_sound(res, "robust")
    _t0g_check_x(inst, res, rec, False, "robust", robust_all=True)


def test_t0g_online_checks():
    """The online checks of C2 and C3 (T0gBound._check): a counted Buy refused as 'unavailable' starts the cautious
    counting; a counted Buy refused for capacity, or a counted lease that ended before the minute through which
    it was counted, switches to the robust form for the rest of the run."""
    from types import SimpleNamespace as NS
    from sublet.instance import public_view
    from sublet.types import ActionResult
    view = public_view(_ms(3, 60), "I1")
    b = Buy(0, 0, 0, 1)
    for reason, cautious, robust in (("unavailable", 0, None), ("capacity", None, 0)):
        tb = T0gBound(view)
        tb.counted_acts = {0: b}
        tb._check(NS(t=0, results=[ActionResult(0, b, False, None, (), reason)], ended=[]))
        assert (tb.cautious_since, tb.robust_since) == (cautious, robust), reason
    tb = T0gBound(view)
    tb.counted_until = {7: 25}
    tb._check(NS(t=5, results=[], ended=[(7, 25, "reclaim")]))
    assert tb.robust_since is None
    tb.counted_until = {7: 25}
    tb._check(NS(t=5, results=[], ended=[(7, 23, "violation")]))
    assert tb.robust_since == 5 and tb.events[-1]["event"] == "robust"


@pytest.mark.slow
def test_t0g_refuse_and_reclaim():
    """T0g under the lender options that the soundness proof treats apart: on_unavailable = 'refuse' (I1 and I2;
    the option passed to A8, as drivers/run.py does, so that only Buys that cannot be refused are counted from slot
    0 on, the cautious route of C2) and violations = 'reclaim' (ends at slow-slot starts, before the observation, so
    C3 holds): ms s3 and q44_spot_1day s1 under trace, A8 around A7, BL1 and BL5 without an abort; the report equals
    the oracle with the cautious route (_t0g_check_x) and ALG(t) <= a-hat(t) at every slot; some refuse run has an
    'unavailable' refusal and some reclaim run a violation end. (Before 2026-10-17 this test ran without the option,
    with the cautious counting from E's first refusal.)"""
    seen = {"unavailable": 0, "victims": 0}
    for name, seed in (("ms2_multi_small", 3), ("q44_spot_1day", 1)):
        inst = _full(name, seed)
        for lm in (dict(on_unavailable="refuse"), dict(on_unavailable="refuse", information="I2"),
                   dict(violations="reclaim")):
            onu = lm.get("on_unavailable", "sell")
            for inner in ("A7", "BL1", "BL5"):
                if inner == "A7" and not HAVE_A7:
                    continue
                rec = _ObsRec(_inner(inner))
                pol = Guarded(inner=rec, test="T0g", N_bound=_N(inst), on_unavailable=onu, **NO_ABORT)
                res = simulate(inst, pol, LenderModel(schedule="trace", **lm), policy_seed=0)
                tag = (name, lm, inner)
                _t0g_check_x(inst, res, rec, False, tag, cautious=onu == "refuse", info=lm.get("information", "I1"))
                _t0g_sound(res, tag)
                seen["unavailable"] += res.metrics["refused"]["unavailable"]
                seen["victims"] += sum(len(v.get("victims", [])) for v in res.violations)
    assert seen["unavailable"] > 0 and seen["victims"] > 0, seen


# ---------------------------------------------------------------- T0g: a general oracle (every slow-slot action type)
from collections import Counter

from fixtures import with_stranding
from sublet.types import Stranding


class _ObsRec(Policy):
    """Wraps an inner policy and records, per slow slot, its action list, the ids of obs.leases, obs.replicas
    (replica id -> lease id) and obs.results; reset, wants_fast, on_fast, params and report pass through."""

    def __init__(self, inner):
        self.inner = inner
        self.name = getattr(inner, "name", type(inner).__name__)
        self.acts, self.obs_l, self.obs_r, self.results = {}, {}, {}, {}

    def reset(self, view, rng):
        self.inner.reset(view, rng)
        self.wants_fast = bool(getattr(self.inner, "wants_fast", False))
        self.acts, self.obs_l, self.obs_r, self.results = {}, {}, {}, {}

    def act(self, obs):
        out = list(self.inner.act(obs))
        t = int(obs.t)
        self.acts[t] = list(out)
        self.obs_l[t] = {int(x) for x in obs.leases}
        self.obs_r[t] = {int(rid): int(rv.lease_id) for rid, rv in obs.replicas.items()}
        self.results[t] = list(obs.results)
        return out

    def on_fast(self, obs):
        return self.inner.on_fast(obs)

    def params(self):
        return self.inner.params()

    def report(self):
        return self.inner.report()


def _realized_capacity(inst, res, rec, upto: int, auto_drain: bool):
    """The realized admitting capacity cap[r] (T_fast,) of every replica r through slow slot `upto`, rebuilt
    independently of the engine and of T0gBound from the recorded actions, the engine's buy and refuse events
    (which Buy made which lease, for the initial admission), the lease and replica records and the admission
    rules of sim_spec §5.4: a SetAdmission at slow slot t takes effect at fast slot t phi; a Drain(at) at t takes
    effect at max(t phi, ceil(at / Df)) and replaces the replica's pending drain; with auto_drain, the announcement
    of a lease at t drains its replicas at max(t Δs, death - ceil(T_dr / 60)) before the policy acts; pending
    changes apply in (effective slot, issue order) while the replica exists, and its capacity is its admission
    from warm_fast until end_fast. Returns (cap, the effective fast slots of each observed replica's pending drain
    at the observation of every slot, Counter of the refusal reasons of the Buys)."""
    g = inst.grid
    Ds, Df, phi, Tf = g.slow_min, g.fast_min, g.phi, g.T_fast
    leases = {L.id: L for L in res.leases}
    reps = {r.id: r for r in res.replicas}
    made = {r.id: r.load_start_min // Ds for r in res.replicas}
    new_at = defaultdict(list)                        # (lease, slot) -> replica ids created then
    for rid in sorted(reps):
        new_at[(reps[rid].lease_id, made[rid])].append(rid)
    evs = defaultdict(list)
    for minute, typ, pl in res.events:
        if typ in ("buy", "refuse"):
            evs[minute].append((typ, pl))
    adm0, reasons = {}, Counter()
    for t in range(upto + 1):
        buys = [a for a in rec.acts.get(t, []) if isinstance(a, Buy)]
        ev = evs.get(t * Ds, [])
        assert len(ev) == len(buys), (t, ev, buys)
        for a, (typ, pl) in zip(buys, ev):
            assert (pl["site"], pl["contract"], pl["llm"]) == (a.site, a.contract, a.llm), (t, a, pl)
            if typ == "refuse":
                reasons[pl["reason"]] += 1
                continue
            for rid in new_at[(pl["lease"], t)][:a.n_replicas]:
                adm0[rid] = float(a.admission)
    Tdr = [L.T_dr_s for L in inst.llms]
    ann = defaultdict(list)
    for L in res.leases:
        if L.announce_slot is not None:
            ann[int(L.announce_slot)].append(L.id)
    pend = defaultdict(list)                          # replica -> sorted [(eff, seq, value, is_drain)]
    cur, seq, pend_obs = {}, [0], {}
    cap = {rid: np.zeros(Tf) for rid in reps}

    def push(rid, eff, value, drain):
        if drain:
            pend[rid] = [p for p in pend[rid] if not p[3]]
        seq[0] += 1
        pend[rid] = sorted(pend[rid] + [(int(eff), seq[0], float(value), bool(drain))])

    for t in range(upto + 1):
        f0 = t * phi
        if auto_drain:
            for lid in ann.get(t, []):
                for rid, l2 in rec.obs_r.get(t, {}).items():
                    if l2 == lid:
                        at = max(t * Ds, int(leases[lid].death_min) - math.ceil(Tdr[reps[rid].llm] / 60.0))
                        push(rid, max(f0, -(-at // Df)), 0.0, True)
        pend_obs[t] = {rid: [p[0] for p in pend[rid] if p[3]] for rid in rec.obs_r.get(t, {})}
        for a in rec.acts.get(t, []):
            if isinstance(a, SetAdmission):
                push(int(a.replica_id), f0, a.value, False)
            elif isinstance(a, Drain):
                push(int(a.replica_id), max(f0, -(-int(a.at_min) // Df)), 0.0, True)
        for rid in reps:
            if made[rid] == t:
                cur[rid] = adm0.get(rid, 1.0)             # a Load's replica (and S's purchases) admit 1
        for f in range(f0, f0 + phi):
            for rid, r in reps.items():
                if made[rid] > t or f >= r.end_fast:
                    continue
                while pend[rid] and pend[rid][0][0] <= f:
                    cur[rid] = pend[rid].pop(0)[2]
                if f >= r.warm_fast:
                    cap[rid][f] = cur[rid]
    return cap, pend_obs, reasons


def _p_rent_x(inst, res, t, acts, obs_l) -> tuple[float, float]:
    """(p_E(t), rent_E(t)) of §3.10 for any action list: the Buys as in _purchases_and_rent, beta_jl per Load on a
    lease of obs, for a Load on a lease bought in the same list the largest beta_jl over the sites of the list's
    earlier Buys (audit F1; asserted to be at least the engine's charge, beta_jl at the site of the lease's record,
    a lease bought at t at one of those sites), and the rent bound over the leases of obs that the list does not
    release."""
    g = inst.grid
    t0m, t1m = t * g.slow_min, (t + 1) * g.slow_min
    leases = {L.id: L for L in res.leases}
    rel = {int(a.lease_id) for a in acts if isinstance(a, Release)}
    p = rent = 0.0
    sites = []
    for a in acts:
        if isinstance(a, Buy):
            gp = inst.llms[a.llm].g * a.n_replicas
            pr = float(inst.price[a.site, a.contract])
            P = inst.contracts[a.contract].prepaid_min
            p += gp * pr * P / 60.0 + a.n_replicas * float(inst.beta_usd[a.llm, a.site])
            rent += gp * pr * max(0, t1m - (t0m + P)) / 60.0
            sites.append(int(a.site))
        elif isinstance(a, Load) and int(a.lease_id) in obs_l:
            p += float(inst.beta_usd[a.llm, leases[int(a.lease_id)].site])
        elif isinstance(a, Load):
            ub = max(float(inst.beta_usd[a.llm, l]) for l in (sites or range(inst.m)))
            L = leases.get(int(a.lease_id))
            assert L is not None and L.start_slot == t and L.site in sites, (t, a)
            assert float(inst.beta_usd[a.llm, L.site]) <= ub, (t, a)
            p += ub
    for lid in obs_l:
        if lid in rel:
            continue
        L = leases[lid]
        hi = t1m if L.death_min is None else min(t1m, L.death_min)
        rent += L.gpus * float(inst.price[L.site, L.contract]) * max(0, hi - max(t0m, L.prepaid_end_min)) / 60.0
    return p, rent


def _names_unseen(acts, obs_l, obs_r) -> bool:
    """Whether an action list names a lease or replica that the observation does not contain (in list order: a
    released lease and its replicas, and an unloaded replica, are gone for the later actions)."""
    L = set(obs_l)
    R = {rid for rid, lid in obs_r.items() if lid in L}
    for a in acts:
        if isinstance(a, (Release, Load)):
            if int(a.lease_id) not in L:
                return True
            if isinstance(a, Release):
                L.discard(int(a.lease_id))
                R = {rid for rid in R if obs_r[rid] != int(a.lease_id)}
        elif isinstance(a, (Unload, SetAdmission, Drain)):
            if int(a.replica_id) not in R:
                return True
            if isinstance(a, Unload):
                R.discard(int(a.replica_id))
    return False


def _lb_served2(clients, d, Wc, Wh, delta, ok, kinf):
    """{client: LB_c} of T0gBound with the counted capacity Wc and the upper capacity Wh: (i) kappa_infinite; (ii)
    if Wc = Wh and the cheapest-site assignment over the sites with Wc > 0 fits Wc; else (iii) min{d_c, (sum over
    c's arcs of Wc - demand of c's competitors)^+}, a competitor having d > 0 and an arc to a site l with Wh_l > 0
    to which c has an arc, with delta_{c'l} <= delta_{cl}."""
    m = len(Wc)
    act = [c for c in clients if d[c] > 0]
    out = {c: 0.0 for c in clients}
    if kinf:
        for c in act:
            out[c] = float(d[c]) if any(ok[c, l] and Wc[l] > 0 for l in range(m)) else 0.0
        return out
    best, fits = {}, False
    if np.array_equal(Wc, Wh):
        load = np.zeros(m)
        for c in act:
            cand = [(delta[c, l], l) for l in range(m) if ok[c, l] and Wc[l] > 0]
            if cand:
                best[c] = min(cand)[1]
                load[best[c]] += d[c]
        fits = bool(np.all(load <= Wc))
    for c in act:
        if fits and c in best:
            out[c] = float(d[c])
            continue
        comp = sum(d[c2] for c2 in act if c2 != c and any(ok[c, l] and ok[c2, l] and Wh[l] > 0
                                                          and delta[c2, l] <= delta[c, l] for l in range(m)))
        capc = sum(Wc[l] for l in range(m) if ok[c, l])
        out[c] = min(float(d[c]), max(capc - comp, 0.0))
    return out


def _t0g_oracle_x(inst, res, rec, auto_drain: bool = False, cautious: bool = False,
                  info: str = "I1", robust_all: bool = False) -> tuple[dict, dict]:
    """T0g's a-hat(t), G(t), S(t) and the reserve R(t) at every executed slot, recomputed independently of guard.py
    for an inner policy that issues slow-slot actions of any type (no on_fast): ({t: (a_hat, G, S, R)},
    statistics). With `cautious` (the run passed on_unavailable 'refuse' to A8) a Buy is uncertain unless its site
    is protected or, under I2, not announced at t (t not in the realized R_l): the replicas of an accepted uncertain
    Buy have lo = 0 and hi = their realized capacity in slot t; a Buy that the engine refused as 'unavailable'
    gives, if it passes the capacity check with the GPUs of the earlier Buys of the list at its site (refused or
    not) counted, hypothetical replicas with lo = 0 and hi = its admission from warm_fast (rule T8) on, for the
    slot. R(t) = sum_c kappa'_c UB_c at the slot's last fast slot (kappa' = mu_kv + mu_fl + mu_fb + pi W_f, UB with
    W^hi and LB of that fast slot; the robust form: d_c a_c). The replicas of slot t are those that exist in its
    first fast slot after the actions (records);
    each counts its realized capacity per fast slot (_realized_capacity), except a replica whose drain pending at
    the observation takes effect at t phi and that A_E(t) drains again (the observation does not show its
    admission at t phi): lo = 0 and hi = 1 while it is warm and its lease alive. W^B counts the replicas on leases
    surely alive in the fast slot (protected, inside the guaranteed window, or announced by t with a later death),
    W^C all, W^hi the upper values; G, LB, UB, e, D and S as in T0gBound's class docstring, the quantities at f - 1
    of a slot's first fast slot from the previous slot. A slot whose list names a lease or replica that obs does
    not contain uses the robust form Q(t) + sum_f sum_c dh_c(f) a_c (mu_kv + mu_fl + mu_fb + pi W_f)_{j_c}, with the
    reserve sum_c kappa'_c d_c(f_l) a_c and, at the next slot's first fast slot, UB_c = d_c(f - 1) a_c (W^hi
    unknown); with `robust_all` (an inner that uses on_fast, condition C1 fails) every slot uses the robust form."""
    rep = res.metrics["policy"]
    t_a = rep["t_a"]
    ex = [t for t in rep["guard"]["slots"] if t_a is None or t < t_a]
    assert ex == list(range(len(ex)))
    g = inst.grid
    Ds, Df, phi = g.slow_min, g.fast_min, g.phi
    J, m, n = inst.J, inst.m, inst.n
    q = np.array([L.q_usd_per_h for L in inst.llms])
    cl = np.asarray(inst.clients.llm)
    dl = np.asarray(inst.clients.delta_usd_per_h, dtype=float)
    ok = np.isfinite(dl) & (dl < q[cl][:, None])
    delta = np.where(ok, dl, np.inf)
    dem = np.asarray(inst.clients.demand, dtype=float)
    kinf = bool(inst.kappa_infinite)
    st_ = inst.stranding
    Tdr = np.array([L.T_dr_s for L in inst.llms])
    mu_kv, mu_fb = np.asarray(st_.mu_kv_usd, dtype=float), np.asarray(st_.mu_fb_usd, dtype=float)
    mu_fl = np.where((np.asarray(st_.mu_fl_usd) > 0) & (Tdr > 0), st_.mu_fl_usd, 0.0)
    piW = np.asarray(st_.pi_usd_per_min, dtype=float) * float(st_.W_f_min)
    clients = [[c for c in range(n) if cl[c] == j] for j in range(J)]
    leases = {L.id: L for L in res.leases}
    reps = {r.id: r for r in res.replicas}
    made = {r.id: r.load_start_min // Ds for r in res.replicas}
    cap, pend_obs, reasons = (_realized_capacity(inst, res, rec, ex[-1], auto_drain) if ex and not robust_all
                              else ({}, {}, Counter()))
    for rl in rec.results.values():
        for r in rl:
            if not r.ok and isinstance(r.action, Load):
                reasons["load:" + r.reason] += 1
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
    st = Counter()
    robust_slots = []
    prevW, prevLB = np.zeros((J, m)), np.zeros(n)
    kap = mu_kv + mu_fl + mu_fb + piW
    evs = defaultdict(list)
    for minute, typ, pl in res.events:
        if typ in ("buy", "refuse"):
            evs[minute].append((typ, pl))
    announced = [set(int(x) for x in np.asarray(Rl).tolist()) for Rl in res.schedule.R]
    lam = inst.lam_ms()
    new_at = defaultdict(list)
    for rid in sorted(reps):
        new_at[(reps[rid].lease_id, made[rid])].append(rid)

    def reserve():
        R = 0.0
        for j in range(J):
            ub = _ub_served(clients[j], dem[:, fs[-1]], prevW[j], prevLB, ok, kinf)
            R += sum(kap[j] * ub[c] for c in clients[j])
        return R
    out = {}
    for t in ex:
        f0 = t * phi
        fs = list(range(f0, f0 + phi))
        acts = rec.acts.get(t, [])
        p, rent = _p_rent_x(inst, res, t, acts, rec.obs_l[t])
        st["load_then_release"] += sum(1 for i, a in enumerate(acts) if isinstance(a, Load) and any(
            isinstance(b, Release) and b.lease_id == a.lease_id for b in acts[i + 1:]))
        G = S = 0.0
        if robust_all or _names_unseen(acts, rec.obs_l[t], rec.obs_r[t]):
            robust_slots.append(t)
            coef = (mu_kv + mu_fl + mu_fb + piW)[cl] * ok.any(axis=1)
            for f in fs:
                dp = dem[:, f - 1] if f > 0 else np.zeros(n)
                G += float(np.sum(q[cl] * dem[:, f])) * Df / 60.0
                S += float(np.sum(np.minimum(dp, dem[:, f]) * coef))
            prevW, prevLB = np.full((J, m), np.inf), np.zeros(n)
            out[t] = ((alg[t - 1] if t > 0 else 0.0) + p + rent + G + S, G, S, reserve())
            continue
        # the cautious route: uncertain Buys of slot t (accepted: their replicas; refused 'unavailable': hypothetical),
        # with T0gBound's capacity replica: the list in order, Releases freeing their GPUs, every Buy that passes
        # the check adding its GPUs (also one the engine refuses as 'unavailable')
        unc, hyp = set(), []
        if cautious:
            held = defaultdict(float)
            for lid in rec.obs_l[t]:
                held[leases[lid].site] += leases[lid].gpus
            bev = iter(evs.get(t * Ds, []))
            for a in acts:
                if isinstance(a, Release):
                    held[leases[int(a.lease_id)].site] -= leases[int(a.lease_id)].gpus
                    continue
                if not isinstance(a, Buy):
                    continue
                typ, pl = next(bev)
                l, j = int(a.site), int(a.llm)
                gp = float(inst.llms[j].g * a.n_replicas)
                if held[l] + gp > inst.sites[l].capacity_gpus:
                    assert typ == "refuse", (t, a)              # T0gBound skips it; the engine refuses it
                    continue
                assert not (typ == "refuse" and pl["reason"] == "capacity"), (t, a)
                held[l] += gp
                if inst.sites[l].kind == "protected" or (info == "I2" and t not in announced[l]):
                    continue
                st["uncertain"] += 1
                if typ == "buy":
                    unc.update(new_at[(pl["lease"], t)][:a.n_replicas])
                else:
                    wf = warm_fast(t * Ds, int(lam[j, l]), Df)
                    on = np.array([float(a.admission) * (f >= wf) for f in fs])
                    hyp += [(j, l, on)] * int(a.n_replicas)
                    st["hypothetical"] += int(a.n_replicas)
        R = sorted(rid for rid, r in reps.items() if made[rid] <= t and r.end_fast > f0)
        redrain = {int(a.replica_id) for a in acts if isinstance(a, Drain)}
        lo, hi, inB = {}, {}, {}
        for rid in R:
            r = reps[rid]
            L = leases[r.lease_id]
            c = inst.contracts[L.contract]
            pe = pend_obs[t].get(rid, [])
            if rid in redrain and f0 in pe:
                on = np.array([float(r.warm_fast <= f < r.end_fast) for f in fs])
                lo[rid], hi[rid] = np.zeros(phi), on
                st["unknown"] += 1
            else:
                lo[rid] = hi[rid] = cap[rid][f0:f0 + phi].copy()
                if rid not in redrain and any(f0 < e < f0 + phi for e in pe):
                    st["view_drain"] += 1
            inB[rid] = np.array([bool(c.protected or (f + 1) * Df <= L.start_min + c.D_min(Ds)
                                      or (L.announce_slot is not None and L.announce_slot <= t
                                          and (f + 1) * Df <= L.death_min)) for f in fs])
            if rid in unc:
                lo[rid] = np.zeros(phi)
        site = {rid: (reps[rid].llm, leases[reps[rid].lease_id].site) for rid in R}
        for k, (j, l, on) in enumerate(hyp):
            key = ("hyp", t, k)
            R.append(key)
            site[key] = (j, l)
            lo[key], hi[key], inB[key] = np.zeros(phi), on, np.zeros(phi, dtype=bool)
        for i, f in enumerate(fs):
            WB, WC, WH = np.zeros((J, m)), np.zeros((J, m)), np.zeros((J, m))
            for rid in R:
                j_r, l = site[rid]
                WB[j_r, l] += lo[rid][i] * inB[rid][i]
                WC[j_r, l] += lo[rid][i]
                WH[j_r, l] += hi[rid][i]
            d = dem[:, f]
            dp = dem[:, f - 1] if f > 0 else np.zeros(n)
            LB = np.zeros(n)
            for j in range(J):
                G += _greedy_cost(clients[j], d, WB[j], float(q[j]), delta, ok, kinf) * Df / 60.0
                lb = _lb_served2(clients[j], d, WC[j], WH[j], delta, ok, kinf)
                ub = _ub_served(clients[j], dp, prevW[j], prevLB, ok, kinf)
                if i == 0:
                    D = bool(np.any(prevW[j] > 0))
                else:
                    D = any(site[rid][0] == j and hi[rid][i - 1] > lo[rid][i] for rid in R)
                for c in clients[j]:
                    LB[c] = lb[c]
                    e = min(dp[c], d[c], ub[c])
                    x = max(e - lb[c], 0.0)
                    terms = {"kv": mu_kv[j] * e, "fl": mu_fl[j] * D * e, "fb": mu_fb[j] * x, "pi": piW[j] * D * x}
                    S += sum(terms.values())
                    for k, v in terms.items():
                        st[k] += v
                    if D:
                        st["D0" if i == 0 else "D1"] += terms["fl"] + terms["pi"]
            prevW, prevLB = WH, LB
        out[t] = ((alg[t - 1] if t > 0 else 0.0) + p + rent + G + S, G, S, reserve())
    st.update({f"refused:{k}": v for k, v in reasons.items()})
    return out, {"robust_slots": robust_slots, **st}


def _t0g_check_x(inst, res, rec, auto_drain: bool, tag, cautious: bool = False, info: str = "I1",
                 robust_all: bool = False) -> dict:
    """A8 under T0g around a recorded inner policy: no robust switch; robust_all as given (an inner that uses
    on_fast: the robust form at every slot); the number of uncertain Buys is the oracle's (0 unless `cautious`); the
    report's a-hat, G, S and reserve R (also the one in the guard's test) equal _t0g_oracle_x's at every executed
    slot, its robust slots are the oracle's, and ALG(t) <= a-hat(t) there (soundness, with every stranding term).
    Returns the oracle's statistics."""
    assert res.invariant_failures == [], (tag, res.invariant_failures[:3])
    rep = res.metrics["policy"]
    t0g = rep["t0g"]
    assert t0g["robust_since"] is None and t0g["robust_all"] == bool(robust_all), (tag, t0g["events"])
    assert t0g["cautious_since"] == (0 if cautious else None), (tag, t0g["cautious_since"])
    orc, st = _t0g_oracle_x(inst, res, rec, auto_drain, cautious, info, robust_all)
    ex = sorted(orc)
    assert t0g["slots"][:len(ex)] == ex and t0g["robust_slots"] == st["robust_slots"], (tag, t0g["robust_slots"], st)
    n_unc = st.get("uncertain", 0)
    assert sum(t0g["uncertain"][:len(ex)]) == n_unc, (tag, t0g["uncertain"][:len(ex)], n_unc)
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
    for i, t in enumerate(ex):
        ah, G, S, R = orc[t]
        assert _close(rep["guard"]["a_hat"][i], ah, T0G_TOL), (tag, t, rep["guard"]["a_hat"][i], ah)
        assert _close(t0g["G"][i], G, T0G_TOL) and _close(t0g["S"][i], S, T0G_TOL), \
            (tag, t, t0g["G"][i], G, t0g["S"][i], S)
        assert _close(t0g["reserve"][i], R, T0G_TOL), (tag, t, t0g["reserve"][i], R)
        assert _close(rep["guard"]["reserve"][i], R if rep["reserve"] else 0.0, T0G_TOL), (tag, t)     # in the test
        assert alg[t] <= ah + T0G_TOL * max(1.0, alg[t]), (tag, t, alg[t], ah)
    return st



class _Script(Policy):
    """An inner policy that calls plan(obs) at every slow slot."""
    name = "script"

    def __init__(self, plan):
        self.plan = plan

    def act(self, obs):
        return list(self.plan(obs))


def test_t0g_load_then_release():
    """T0gBound counts no replica that a Load puts on a lease which a later Release of the same list ends at the slot
    start (the engine kills both at the slot start, sim_spec §5.1): on the toy (site L0 with load time 0), Buy at
    slot 2 and [Unload, Load, Release] of that lease at slot 3; the Load succeeds and its replica ends at the slot's
    first fast slot; T0g's a-hat at slot 3 is the one of the list [Unload, Release] (the toy's loading charge is 0),
    no robust switch follows, the report equals the oracle and ALG(t) <= a-hat(t) at every slot."""
    inst = toy_instance({"lenders.0.lam_s": 0.0})
    assert float(inst.beta_usd[0, 0]) == 0.0
    out = {}
    for with_load in (True, False):
        def plan(obs, with_load=with_load):
            if obs.t == 2:
                return [Buy(0, 1, 0, 1)]
            if obs.t == 3:
                lid, rid = next(iter(obs.leases)), next(iter(obs.replicas))
                return [Unload(rid), Load(lid, 0), Release(lid)] if with_load else [Unload(rid), Release(lid)]
            return []
        rec = _ObsRec(_Script(plan))
        res = simulate(inst, Guarded(inner=rec, test="T0g", safe="fb", **NO_ABORT), LenderModel(), policy_seed=0)
        st = _t0g_check_x(inst, res, rec, False, ("load-release", with_load))
        assert st["load_then_release"] == int(with_load)
        res4 = rec.results[4]
        assert all(r.ok for r in res4) and len(res4) == (3 if with_load else 2)
        if with_load:
            new = [r for r in res.replicas if r.load_start_min == 3 * inst.grid.slow_min]
            assert len(new) == 1 and new[0].end_fast == 3 * inst.grid.phi
        out[with_load] = res.metrics["policy"]["guard"]["a_hat"][3]
        alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
        assert _close(out[with_load], alg[3], T0G_TOL)              # exact on this toy
    assert _close(out[True], out[False], 1e-12), out


def _paths_instance():
    """The toy on 1-min fast slots (phi = 5) for test_t0g_replica_paths: site L0 with 2 GPUs and no announcements,
    L1 and P as in the toy, load times 60 s, two clients of LLM M (demand 2.2 and 0.8 from slot 1), all four
    stranding coefficients positive (W_f = 3 min)."""
    phi = 5
    cl = load_json(CONFIGS / "toy.json")["borrowers"]["clients"][0]
    d0 = [0.0] * phi + [2.2] * (23 * phi)
    d1 = [0.0] * phi + [0.8] * (23 * phi)
    inst = toy_instance({"time.fast_slot_min": 1, "lenders.0.capacity_gpus": 2, "lenders.0.R": [],
                         "lenders.0.lam_s": 60.0, "lenders.1.lam_s": 60.0, "lenders.2.lam_s": 60.0,
                         "borrowers.clients": [{**cl, "demand": {"kind": "array", "values": d0}},
                                               {**cl, "demand": {"kind": "array", "values": d1}}]})
    return with_stranding(inst, mu_kv_usd=0.2, mu_fl_usd=0.5, mu_fb_usd=0.4, pi_usd_per_min=0.05, W_f_min=3.0)


def test_t0g_replica_paths():
    """T0gBound's replica model on the paths that the engine's capacity rules decide (class docstring), each checked
    against the oracle (_t0g_oracle_x) slot by slot, with no robust switch and ALG(t) <= a-hat(t): a Buy refused for
    capacity at L0 (2 GPUs; at slots 0 and 9), a Load beyond its lease's GPUs (slot 1), a Drain issued at slot 2
    that takes effect inside slot 3 (the observation shows it only as ReplicaView.drain_min), a re-drain at slot 5
    of a drain pending at slot 5's first fast slot (the replica's admission there is unknown to the bound) while the
    demand exceeds the capacity, the restore by SetAdmission, and Load followed by Release of one lease (slot 8)."""
    inst = _paths_instance()
    phi, Ds = inst.grid.phi, inst.grid.slow_min
    assert phi == 5 and inst.m == 3 and inst.sites[2].kind == "protected"
    mem = {}

    def plan(obs):
        t = obs.t
        by_site = defaultdict(list)
        for rid, rv in sorted(obs.replicas.items()):
            by_site[obs.leases[rv.lease_id].site].append(rid)
        if t == 0:
            return [Buy(0, 1, 0, 1), Buy(0, 1, 0, 1), Buy(0, 1, 0, 1), Buy(2, 2, 0, 1)]
        if t == 1:
            mem["P"] = by_site[2][0]
            mem["L0"] = by_site[0][0]
            return [Load(obs.replicas[mem["P"]].lease_id, 0)]                  # the 1-GPU lease is full
        if t == 2:
            return [Drain(mem["P"], 3 * Ds + 2)]                                # inside slot 3
        if t == 4:
            return [SetAdmission(mem["P"], 1.0), Drain(mem["L0"], 5 * Ds)]      # pending at slot 5's first fast slot
        if t == 5:
            return [Drain(mem["L0"], 5 * Ds + 3)]                               # replaces it
        if t == 6:
            return [SetAdmission(mem["L0"], 1.0)]
        if t == 7:
            return [Buy(1, 0, 0, 1)]
        if t == 8:
            rid = by_site[1][0]
            lid = obs.replicas[rid].lease_id
            return [Unload(rid), Load(lid, 0), Release(lid)]
        if t == 9:
            return [Buy(0, 0, 0, 1)]                                            # L0 is full
        return []
    rec = _ObsRec(_Script(plan))
    res = simulate(inst, Guarded(inner=rec, test="T0g", safe="fb", **NO_ABORT), LenderModel(), policy_seed=0)
    st = _t0g_check_x(inst, res, rec, False, "paths")
    assert st["refused:capacity"] == 2 and st["refused:load:lease_gpus"] == 1, st
    assert st["view_drain"] >= 1 and st["unknown"] == 1 and st["load_then_release"] == 1, st
    assert st["robust_slots"] == [] and st["D1"] > 0, st
    for k in ("stranding_kv", "stranding_fl", "stranding_fb", "stranding_pi"):
        assert float(np.sum(res.per_slot[k])) > 0, k


_RICH = ({"slow": 10, "fast": 2, "horizon": 240, "H": (3, 13), "caps": (4, 3)},
         {"slow": 10, "fast": 1, "horizon": 200, "H": (1, 7), "caps": (4, 3)},
         {"slow": 6, "fast": 3, "horizon": 180, "H": (2, 4), "caps": (4, 3)},
         {"slow": 10, "fast": 5, "horizon": 200, "H": (7, 12), "caps": (2, 5)})
# the further time grids of the audit of the full-model guard (design/theory/audit_guard.md, F4; its X2 calls them
# EXTRA): variants 4-7 of _rich_instance. Notice 0 (a death at the start of the announcement slot) with fast slot =
# slow slot (phi = 1), notice 0 with phi = 5, notice equal to the slow slot with phi = 6, a fast slot that does not
# divide the notice
_RICH_EXTRA = ({"slow": 5, "fast": 5, "horizon": 150, "H": (0, 5), "caps": (3, 3)},
               {"slow": 10, "fast": 2, "horizon": 200, "H": (0, 1), "caps": (4, 4)},
               {"slow": 6, "fast": 1, "horizon": 150, "H": (6, 0), "caps": (2, 3)},
               {"slow": 12, "fast": 4, "horizon": 240, "H": (5, 23), "caps": (5, 2)})


def _rich_instance(seed: int, variant: int, kinf: bool):
    """A small full-model instance on which every term of T0g's bound is active: the toy's sites L0 and L1 (finite
    capacities, announcement slots) and P, two LLMs (1 and 2 GPUs per replica), five clients with random routing
    costs (some arcs infeasible or not below q) and on/off demand, all four stranding coefficients positive (T_dr >
    0, W_f > 0), notice periods that are not multiples of the fast slot, load times inside and beyond a slow slot,
    random loading charges, and kappa_infinite as given (the arrays are set on the built instance). Variants 0-3 are
    the time grids of _RICH, 4-7 those of _RICH_EXTRA."""
    v = (_RICH + _RICH_EXTRA)[variant]
    rng = np.random.default_rng(1000 + 17 * seed + variant)
    cfg = load_json(CONFIGS / "toy.json")
    slow, fast, hor = v["slow"], v["fast"], v["horizon"]
    cfg["time"].update(slow_slot_min=slow, fast_slot_min=fast, horizon_min=hor)
    cfg["contracts"] = [{"id": "short", "tau_min": slow, "H_min": v["H"][0]},
                        {"id": "long", "tau_min": 2 * slow, "H_min": v["H"][1]},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": slow}]
    cfg["llms"] = [cfg["llms"][0], {**cfg["llms"][0], "id": "M2", "g": 2}]
    T = hor // slow
    cfg["lenders"][0].update(capacity_gpus=v["caps"][0], R=[x for x in (3, 4, 9, 14, 15, 20, 26) if x < T])
    cfg["lenders"][1].update(capacity_gpus=v["caps"][1], R=[x for x in (2, 6, 7, 12, 18, 25) if x < T])
    base = cfg["borrowers"]["clients"][0]
    cfg["borrowers"]["clients"] = [{**base, "llm": llm, "borrowers": [f"b{k}"],
                                    "demand": {"kind": "array", "values": [1.0] * (hor // fast)}}
                                   for k, llm in enumerate(("M", "M", "M", "M2", "M2"))]
    inst = build_instance(cfg)
    n, m, J = inst.n, inst.m, inst.J
    assert (n, m, J) == (5, 3, 2)
    q = np.array([x.q_usd_per_h for x in inst.llms])
    cl = np.asarray(inst.clients.llm)
    dl = np.empty((n, m))
    for c in range(n):
        for l in range(m):
            u = rng.random()
            dl[c, l] = (np.inf if u < 0.15 else q[cl[c]] * (1.0 + rng.random()) if u < 0.25
                        else q[cl[c]] * rng.choice([0.0, 0.1, 0.1, 0.3, 0.5, 0.9]))
    inst.clients.delta_usd_per_h = dl
    Tf = inst.grid.T_fast
    dem = np.zeros((n, Tf))
    for c in range(n):
        dem[c] = np.where(rng.random(Tf) < 0.7, rng.choice([0.3, 0.7, 1.0, 1.5, 2.5]) * (0.5 + rng.random(Tf)), 0.0)
        for _ in range(3):
            a = int(rng.integers(0, Tf))
            dem[c, a:a + int(rng.integers(1, 8))] = 0.0
    inst.clients.demand = dem
    inst.stranding = Stranding(mu_kv_usd=rng.uniform(0.05, 1.0, J), mu_fl_usd=rng.uniform(0.05, 1.0, J),
                               mu_fb_usd=rng.uniform(0.05, 1.0, J), pi_usd_per_min=rng.uniform(0.01, 0.2, J),
                               W_f_min=float(rng.choice([1.0, 3.0, 7.0])))
    inst.lam_s = rng.choice([0.0, 30.0, 90.0, 250.0, 700.0, 1300.0], size=(J, m)).astype(float)
    inst.beta_usd = rng.uniform(0.0, 0.3, (J, m))
    inst.llms = tuple(dataclasses.replace(x, T_dr_s=float(rng.choice([10.0, 28.49, 200.0]))) for x in inst.llms)
    inst.kappa_infinite = bool(kinf)
    return inst


class _RandomInner(Policy):
    """An inner policy that issues valid slow-slot actions of every type at random: Buy (one or two replicas,
    admission in {0, 0.3, 0.5, 1}), Release, Load, Load followed by Release of the same lease, Unload,
    SetAdmission and Drain at a minute up to three slow slots ahead; it never names an object of its own list."""
    name = "random"

    def __init__(self, seed: int):
        self.seed = int(seed)

    def reset(self, view, rng):
        super().reset(view, rng)
        self.r = np.random.default_rng(self.seed)

    def act(self, obs):
        r, view = self.r, self.view
        if r.random() < 0.15:
            return []
        Ds, J = view.grid.slow_min, len(view.llms)
        leases = set(obs.leases)
        reps = {rid for rid, rv in obs.replicas.items() if rv.lease_id in leases}
        acts = []
        for _ in range(int(r.integers(1, 8))):
            kind = r.choice(("buy", "buy", "buy", "rel", "load", "loadrel", "unload", "adm", "adm", "drain", "drain"))
            if kind == "buy":
                l = int(r.integers(0, len(view.sites)))
                acts.append(Buy(l, int(r.choice(sorted(view.sites[l].menu))), int(r.integers(0, J)),
                                int(r.choice((1, 1, 2))), admission=float(r.choice((1.0, 1.0, 0.5, 0.3, 0.0)))))
            elif kind in ("rel", "loadrel") and leases:
                lid = int(r.choice(sorted(leases)))
                if kind == "loadrel":
                    acts.append(Load(lid, int(r.integers(0, J))))
                acts.append(Release(lid))
                leases.discard(lid)
                reps = {rid for rid in reps if obs.replicas[rid].lease_id != lid}
            elif kind == "load" and leases:
                acts.append(Load(int(r.choice(sorted(leases))), int(r.integers(0, J))))
            elif kind == "unload" and reps:
                rid = int(r.choice(sorted(reps)))
                acts.append(Unload(rid))
                reps.discard(rid)
            elif kind == "adm" and reps:
                acts.append(SetAdmission(int(r.choice(sorted(reps))), float(r.choice((0.0, 0.25, 0.5, 1.0)))))
            elif kind == "drain" and reps:
                acts.append(Drain(int(r.choice(sorted(reps))), int(obs.minute + r.integers(0, 3 * Ds))))
        return acts


RICH_MODELS = {"eager": {"schedule": "eager"}, "trace": {"schedule": "trace"},
               "iid": {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.3}},
               "traceI2": {"schedule": "trace", "information": "I2"}}


def _rich_runs(cases) -> Counter:
    """A8 under T0g (no abort) around _RandomInner on _rich_instance for (seed, variant, model, kinf, auto_drain)
    cases, each checked by _t0g_check_x; returns the summed oracle statistics."""
    tot = Counter()
    for seed, variant, mname, kinf, ad in cases:
        inst = _rich_instance(seed, variant, kinf)
        rec = _ObsRec(_RandomInner(7 * seed + variant + 1))
        pol = Guarded(inner=rec, test="T0g", safe="fb", **NO_ABORT)
        res = simulate(inst, pol, LenderModel(**RICH_MODELS[mname]), EngineConfig(auto_drain=ad), policy_seed=0)
        st = _t0g_check_x(inst, res, rec, ad, (seed, variant, mname, kinf, ad))
        tot.update({k: v for k, v in st.items() if k != "robust_slots"})
        tot["runs"] += 1
    return tot


def _assert_rich_coverage(tot: Counter) -> None:
    """Every term of S(f) and both cases of the drop factor D_j(f) contribute, and the replica paths occur: a drain
    pending at the observation that takes effect inside the slot, a re-drain of a drain pending at the slot's first
    fast slot, Load followed by Release, Buys refused for capacity and Loads refused for the lease's GPUs."""
    for k in ("kv", "fl", "fb", "pi", "D0", "D1"):
        assert tot[k] > 0, (k, tot)
    for k in ("view_drain", "unknown", "load_then_release", "refused:capacity", "refused:load:lease_gpus"):
        assert tot[k] > 0, (k, tot)


def test_t0g_stranding_terms_quick():
    """T0g's stranding bound with every coefficient positive (quick variant of test_t0g_stranding_terms): a random
    inner policy issuing every slow-slot action type on _rich_instance (3 seeds, 4 time grids, the lenders eager,
    trace, iid_step and trace under I2, kappa_infinite and auto_drain alternating; 48 runs), and A8
    around A7, BL1 and BL5 on ms s3 (6 h) with mu_kv, mu_fl, mu_fb, pi and W_f positive under trace; the report
    equals the oracle at every slot (so a missing or wrong term of S(f) or of D_j(f) fails), ALG(t) <= a-hat(t),
    and each of the four terms, both cases of D_j and the replica paths occur (_assert_rich_coverage)."""
    cases = [(s, v, mn, bool((s + v + i) % 2), bool((s + v) % 2)) for s in range(3) for v in range(4)
             for i, mn in enumerate(RICH_MODELS)]
    tot = _rich_runs(cases)
    assert tot["runs"] == 48
    _assert_rich_coverage(tot)
    inst = with_stranding(_ms(3, 360), mu_kv_usd=0.3, mu_fl_usd=0.5, mu_fb_usd=0.4, pi_usd_per_min=0.05, W_f_min=3.0)
    assert all(x.T_dr_s > 0 for x in inst.llms)
    for inner in ("A7", "BL1", "BL5"):
        if inner == "A7" and not HAVE_A7:
            continue
        o = _t0g_full_check(inst, LenderModel(schedule="trace"), inner, ("ms s3 6h stranding", inner))
        assert o["slots"] == inst.grid.T_slow and o["strand_slots"] > 0


@pytest.mark.slow
def test_t0g_stranding_terms():
    """T0g is sound with every stranding term (T0gBound's proof, steps (b)-(c)): the random inner of
    test_t0g_stranding_terms_quick on _rich_instance for 12 seeds, the 4 time grids, the lenders eager, trace,
    iid_step (p = 0.3) and trace under I2, kappa_infinite off and on, auto_drain alternating (384 runs); the report
    equals the oracle at every slot, ALG(t) <= a-hat(t), no robust switch, and every term, both cases of D_j and the
    replica paths occur (_assert_rich_coverage)."""
    cases = [(s, v, mn, kinf, bool((s + v) % 2)) for s in range(12) for v in range(4) for mn in RICH_MODELS
             for kinf in (False, True)]
    tot = _rich_runs(cases)
    assert tot["runs"] == 384
    _assert_rich_coverage(tot)


def test_t0g_refuse_first_refusal():
    """T0gBound's condition C2 under on_unavailable = 'refuse' when A8 is not told the option (on_unavailable None,
    a direct construction; class docstring): the bound presumes that the lender sells until the inner policy's
    first 'unavailable' refusal, so that slot can have ALG(t) > a-hat(t). On the toy (L0 with load time 0 and
    announcement slots 2 and 3), a Buy at L0 at slot 2 is refused as 'unavailable' under 'refuse' (I1 and I2):
    m(2) = ALG(2) - a-hat(2) = fallback 0.5958 - the counted price 0.475 > 0 (hand values), the cautious counting
    starts at slot 3 and m = 0 elsewhere; under 'sell' the same run has m = 0 and a-hat(2) = ALG(2). The run-spec
    driver, which knows the option, passes it to A8 (make_policy), so it accepts A8 with test 'T0g' under 'refuse'
    (given in the run spec or in the instance config) as under 'sell' (before 2026-10-17 it refused T0g there;
    test_t0g_refuse_cautious checks the bound with the option passed)."""
    from sublet.drivers import run as drun

    def plan(obs):
        return [Buy(0, 0, 0, 1)] if obs.t == 2 else []
    q, price = 7.15 * 5 / 60.0, 2.85 * 10 / 60.0          # fallback of one replica load for 5 min; prepaid 10 min
    for info in ("I1", "I2"):
        for onu in ("sell", "refuse"):
            inst = toy_instance({"lenders.0.lam_s": 0.0, "lenders.0.R": [2, 3]})
            pol = Guarded(inner=_Script(plan), test="T0g", safe="fb", **NO_ABORT)
            res = simulate(inst, pol, LenderModel(schedule="trace", information=info, on_unavailable=onu),
                           policy_seed=0)
            assert res.invariant_failures == []
            rep = res.metrics["policy"]
            alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
            m = rep["guard"]["m"]                              # m(t) is booked at t + 1: None at the last slot
            assert len(m) == inst.grid.T_slow and m[-1] is None and None not in m[:-1]
            m = m[:-1]
            assert _close(rep["guard"]["a_hat"][2], price, 1e-12), (info, onu, rep["guard"]["a_hat"][2])
            if onu == "sell":
                assert res.metrics["refused"]["unavailable"] == 0 and _close(alg[2], price, 1e-12)
                assert max(m) == 0.0 and rep["t0g"]["cautious_since"] is None
            else:
                assert res.metrics["refused"]["unavailable"] == 1 and _close(alg[2], q, 1e-12)
                assert _close(m[2], q - price, 1e-9) and m[2] > 0.1, (info, m[2])
                assert all(x == 0.0 for i, x in enumerate(m) if i != 2) and rep["t0g"]["cautious_since"] == 3
    spec = {"schema_version": 1, "name": "t_t0g_refuse", "instance": "toy.json"}
    for test in ("T0g", "T0"):
        for where in ("spec", "config", "sell"):
            s = dict(spec, policy={"id": "A8", "params": {"test": test, "safe": "fb"}})
            if where == "spec":
                s["lender_model"] = {"on_unavailable": "refuse"}
            elif where == "config":
                s["overrides"] = {"lender_model.on_unavailable": "refuse"}
            else:
                s["lender_model"] = {"on_unavailable": "sell"}
            s = drun.load_run_spec(s)
            inst, model, _ = drun.build(s, s["seeds"]["config"][0])
            pol = drun.make_policy(s, inst)
            want = "sell" if where == "sell" else "refuse"
            assert pol.on_unavailable == model.on_unavailable == want, (test, where)


# ================================================================ the wind-down reserve (guard.py, Theorem W)
# Oracles: the realized wind-down cost Phi(u) = sum_{v >= u} (total(v) - Q(v)) from the ledger, with Q(v) the slot's
# all-fallback cost from the instance's demand; the lease records (which leases were held at the abort, when they
# ended, that S bought nothing); the reserve R(t) recomputed by _t0g_oracle_x (and _t0g_oracle) from the records, in
# T0g's bound form and in its robust form (a list that names an object of its own list, _OwnListInner; an inner that
# uses on_fast, _FastInner); hand values on the toy; the study's recorded failures (q44_study run files at commits
# 9cf16de and d2a538d).
import copy as _copy

from sublet.experiments import q44_study as qs


def test_ratchet_reserve():
    """The reserve in the test (hand oracle): a-hat(t) + R(t) <= gamma C_S(t) + B(t) executes, equality included;
    a larger R aborts; R is recorded per slot; m(t) is booked against a-hat(t) alone; R must be finite and >= 0."""
    rt = Ratchet(1.0, "T0g", 2.0, None)
    assert rt.step(0, 1.0, 1.0, 2.0, reserve=2.0)                    # 1 + 2 = 3 = rhs
    assert not rt.step(1, 1.5, 1.0, 2.0, alg_prev=1.25, reserve=1.6)   # 1.5 + 1.6 > 3
    assert rt.t_a == 1 and rt.reserve == [2.0, 1.6] and rt.m == {0: 0.25}
    assert rt.report()["reserve"] == [2.0, 1.6]
    for bad in (-1.0, math.inf, math.nan, True):
        with pytest.raises(PolicyError):
            Ratchet(1.0, "T0g").step(0, 0.0, 1.0, 0.0, reserve=bad)


def _q_slot(inst) -> np.ndarray:
    """(T_slow,) the slot's all-fallback cost sum_c q_{j_c} sum_f d_c(f) Δf / 60 from the instance's demand."""
    g = inst.grid
    q = np.array([x.q_usd_per_h for x in inst.llms])[np.asarray(inst.clients.llm)]
    d = np.asarray(inst.clients.demand, dtype=float)
    return (q[:, None] * d).sum(axis=0)[: g.T_slow * g.phi].reshape(g.T_slow, g.phi).sum(axis=1) * g.fast_min / 60.0


def _winddown_oracle(inst, res, ref, tag) -> dict:
    """Theorem W(b) at one forced abort of A8 with safe = 'fb' (S = FB at every slot): (1) the run equals the
    no-abort reference run `ref` (same E-mode run) before t_a, and the reserve in the guard's test at t_a - 1 is the
    reference's; (2) Phi(t_a) <= R(t_a - 1), the budget, and Phi(u) <= the logged budget at every later wind-down
    slot u of 'adaptive'; (3) the core bound ALG(T) <= C_S(T) + (gamma - 1) C_S(t_a - 1) + B(t_a - 1), with C_S the
    cumulative Q (checked against the report) and B from the report; (4) lease records: no lease starts at or after
    t_a; under 'release' every lease held at t_a ends by t_a Δs and the cost after t_a is all-fallback with
    stranding in slot t_a only; under 'adaptive' every lease held at t_a ends by the release slot of the wind-down
    log, at its death, or at the horizon."""
    rep = res.metrics["policy"]
    t_a = rep["t_a"]
    g = inst.grid
    Ds = g.slow_min
    assert res.invariant_failures == [], (tag, res.invariant_failures[:3])
    assert rep["guard"]["forced"] and rep["safe"]["followed"] == [["FB", 0, g.T_slow]], tag
    tot = np.asarray(res.per_slot["total"], dtype=float)
    rtot = np.asarray(ref.per_slot["total"], dtype=float)
    assert np.array_equal(tot[:t_a], rtot[:t_a]), tag
    rrep = ref.metrics["policy"]
    R = rrep["guard"]["reserve"][t_a - 1] if t_a > 0 else 0.0
    assert t_a == 0 or rep["guard"]["reserve"][t_a - 1] == R, tag
    assert rep["budget_t_a"] == R, (tag, rep["budget_t_a"], R)
    Q = _q_slot(inst)
    C_S = np.cumsum(Q)
    assert np.allclose(rep["safe"]["C_S_curve"], C_S, rtol=1e-12, atol=1e-9), tag
    phi_u = np.cumsum((tot - Q)[::-1])[::-1]                     # Phi(u) for every u
    scale = max(1.0, float(np.sum(tot)))
    assert phi_u[t_a] <= R + TOL * scale, (tag, "Phi(t_a) > R(t_a - 1)", phi_u[t_a], R)
    wd = rep["wd"]
    for e in wd:
        assert phi_u[e["t"]] <= e["budget"] + TOL * scale, (tag, e, phi_u[e["t"]])
        assert e.get("beta_K0_le_budget", True), (tag, e)
    gamma = float(rep["gamma"])
    Bc = rep["safe"]["B_curve"]
    bound = C_S[-1] + (gamma - 1.0) * (C_S[t_a - 1] if t_a > 0 else 0.0) + (Bc[t_a - 1] if t_a > 0 else 0.0)
    assert float(np.sum(tot)) <= bound + TOL * scale, (tag, float(np.sum(tot)), bound)
    assert not any(L.start_slot >= t_a for L in res.leases), tag
    Df = g.fast_min                                              # held at t_a: alive in its first fast slot (T6)
    held = [L for L in res.leases if L.start_slot < t_a and (L.end_min >= t_a * Ds + Df or L.release_min == t_a * Ds)]
    ps = res.per_slot
    if rep["wind_down"] == "release":
        assert all(L.end_min <= t_a * Ds for L in held), tag
        after = slice(t_a + 1, None)
        assert not np.any(ps["routing"][t_a:]) and not np.any(ps["lease_rent"][t_a:]), tag
        assert not np.any(ps["stranding"][after]), tag
        assert np.allclose(ps["fallback"][t_a:], Q[t_a:], rtol=1e-12, atol=1e-12), tag
    else:
        wd_slots = [e["t"] for e in wd if e["kept"] < e["held"]]
        for L in held:
            if L.end_cause == "release":
                assert L.release_min % Ds == 0 and L.release_min // Ds in wd_slots, (tag, L)
    return {"t_a": t_a, "phi": float(phi_u[t_a]), "R": float(R), "held": len(held),
            "kept": sum(e["kept"] for e in wd), "strand_t_a": float(ps["stranding"][t_a]),
            "choices": [e["choice"] for e in wd]}


def _forced_aborts(inst, model, make_inner, rule: str, tag, slots=None, cautious=False, info="I1",
                   auto_drain=False, oracle=True, stats=None, robust_all=False, refs=None) -> list:
    """A8 (safe 'fb', T0g, wind_down `rule`, allowance B0 = 1e12 so that only the forced abort trips) around a fresh
    inner from make_inner(): one reference run without an abort, checked by _t0g_check_x (the reserve R(t)
    recomputed from the records at every slot; `robust_all` for an inner that uses on_fast), then a forced abort at
    each slot of `slots` (default: every slot), each checked by _winddown_oracle and marked robust_prev if the
    reference run's slot t_a - 1 used T0g's robust form. `stats` (a Counter) collects the reference run's violation
    victims and robust slots; `refs` (a list), if given, the reference run's RunResult."""
    onu = "refuse" if cautious else None
    kw = dict(test="T0g", safe="fb", wind_down=rule, on_unavailable=onu, **NO_ABORT)
    cfg = EngineConfig(auto_drain=auto_drain)
    rec = _ObsRec(make_inner())
    ref = simulate(inst, Guarded(inner=rec, **kw), model, cfg, policy_seed=0)
    if oracle:
        _t0g_check_x(inst, ref, rec, auto_drain, (tag, "reference"), cautious=cautious, info=info,
                     robust_all=robust_all)
    rob = set(ref.metrics["policy"]["t0g"]["robust_slots"])
    if refs is not None:
        refs.append(ref)
    if stats is not None:
        stats["victims"] += sum(len(v.get("victims", [])) for v in ref.violations)
        stats["robust_slots"] += len(rob)
    out = []
    for t_a in (range(inst.grid.T_slow) if slots is None else slots):
        res = simulate(inst, Guarded(inner=make_inner(), abort_at=int(t_a), **kw), model, cfg, policy_seed=0)
        o = _winddown_oracle(inst, res, ref, (tag, t_a))
        o["robust_prev"] = (int(t_a) - 1) in rob
        out.append(o)
    return out


FORCED_MODES = (("trace", {"schedule": "trace"}, False), ("eager", {"schedule": "eager"}, False),
                ("iid", {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.05}}, False),
                ("correlated", {"schedule": "correlated", "params": {"p_sh": 1.0, "groups": "all"}}, False),
                ("refuse", {"schedule": "trace", "on_unavailable": "refuse"}, True),
                ("reclaim", {"schedule": "trace", "violations": "reclaim"}, False))


def _assert_forced_coverage(runs: list) -> None:
    """Both wind-down cases occur: aborts with stranding in slot t_a, the adaptive rule keeping a lease (K1 or
    K2) and releasing all (K0), and a run in which the realized wind-down cost reaches its budget."""
    assert any(o["strand_t_a"] > 0 for o in runs) and any(o["held"] > 0 for o in runs)
    ch = [c for o in runs for c in o["choices"]]
    assert "K0" in ch and ("K1" in ch or "K2" in ch), Counter(ch)
    assert any(o["R"] > 0 and o["phi"] >= 0.5 * o["R"] for o in runs)


def test_reserve_forced_aborts_quick():
    """Theorem W(b) with forced aborts at every slot (quick): ms s3 on a 2-h horizon (24 slots), A8 with safe 'fb'
    around A7, BL1 and BL5 under the lenders trace, eager, iid_step (p = 0.05), correlated (p_sh = 1), trace with
    on_unavailable 'refuse' (the option passed to A8: the cautious route) and trace with violations 'reclaim'; the
    default wind-down 'adaptive'. Every run passes _winddown_oracle and every reference run the reserve oracle."""
    inst = _ms(3, 120)
    runs = []
    for name, lm, cautious in FORCED_MODES:
        for inner in ("A7", "BL1", "BL5"):
            if inner == "A7" and not HAVE_A7:
                continue
            runs += _forced_aborts(inst, LenderModel(**lm), lambda inner=inner: _inner(inner), "adaptive",
                                   ("ms s3 2h", name, inner), cautious=cautious)
    _assert_forced_coverage(runs)


def test_reserve_forced_aborts_random_quick():
    """Theorem W(b) with forced aborts at every slot for an inner policy that issues every slow-slot action type
    (_RandomInner) on _rich_instance (every stranding coefficient positive; the four time grids; kappa_infinite and
    auto_drain alternating), under eager, trace, iid_step (p = 0.3), trace under I2, and 'refuse' under I1 and I2
    (option passed); wind-down 'adaptive' on even and 'release' on odd variants. Every run passes _winddown_oracle,
    every reference run _t0g_check_x (with the cautious route's uncertain and hypothetical Buys under 'refuse')."""
    models = dict(RICH_MODELS, refuse={"schedule": "trace", "on_unavailable": "refuse"},
                  refuseI2={"schedule": "trace", "on_unavailable": "refuse", "information": "I2"})
    runs, hyp = [], 0
    for v in range(4):
        for i, (mname, lm) in enumerate(models.items()):
            kinf, ad = bool((v + i) % 2), bool(v % 2)
            inst = _rich_instance(0, v, kinf)
            cautious = mname.startswith("refuse")
            info = lm.get("information", "I1")
            rule = "adaptive" if v % 2 == 0 else "release"
            runs += _forced_aborts(inst, LenderModel(**lm), lambda v=v: _RandomInner(7 * v + 1), rule,
                                   ("rich", v, mname, kinf, ad, rule), cautious=cautious, info=info, auto_drain=ad)
    _assert_forced_coverage(runs)


class _OwnListInner(_RandomInner):
    """_RandomInner that, at about a third of its slots, starts its list with a Buy at the protected site P (unlimited
    capacity, so never refused) followed by an action on an object of that Buy: a Load onto the new lease (refused for
    its GPUs), an Unload, SetAdmission or Drain of its first replica, or a Release of the new lease. The ids are the
    engine's next ones, tracked from the accepted Buys and Loads in obs.results (before an abort every lease and
    replica of the run is the inner's). Such a list names an object that obs does not contain, so T0g uses its
    robust form at that slot (T0gBound class docstring): G = Q, the stranding bound with every client counted, the
    reserve sum_c kappa'_c d_c(f_l) a_c, and UB_c(f0 - 1) = d_c(f0 - 1) a_c at the next slot."""
    name = "ownlist"
    OWN = ("load", "unload", "adm", "drain", "release")

    def reset(self, view, rng):
        super().reset(view, rng)
        self.next_lease = self.next_rep = 0
        self.P = next(l for l, x in enumerate(view.sites) if x.kind == "protected")
        assert not math.isfinite(float(view.sites[self.P].capacity_gpus))
        self.own = Counter()

    def act(self, obs):
        for r in obs.results:
            if r.ok and isinstance(r.action, Buy):
                self.next_lease = max(self.next_lease, int(r.lease_id) + 1)
            if r.ok and isinstance(r.action, (Buy, Load)) and r.replica_ids:
                self.next_rep = max(self.next_rep, max(int(x) for x in r.replica_ids) + 1)
        acts = list(super().act(obs))
        r, view = self.r, self.view
        if r.random() < 0.35:
            lid, rid = self.next_lease, self.next_rep
            kind = str(r.choice(self.OWN))
            own = {"load": Load(lid, 0), "unload": Unload(rid), "adm": SetAdmission(rid, float(r.choice((0.0, 0.5)))),
                   "drain": Drain(rid, int(obs.minute + r.integers(0, 2 * view.grid.slow_min))),
                   "release": Release(lid)}[kind]
            buy = Buy(self.P, int(sorted(view.sites[self.P].menu)[0]), int(r.integers(0, len(view.llms))),
                      int(r.choice((1, 2))))
            acts = [buy, own] + acts
            self.own[kind] += 1
        return acts


class _FastInner(_RandomInner):
    """_RandomInner that also uses on_fast (wants_fast, so condition C1 fails and T0g uses its robust form at every
    slot): at about a third of the fast slots a SetAdmission (0, 0.5 or 1) or a Drain up to two slow slots ahead of a
    replica that exists through the slot (observed, on a lease without an announced death, not released or unloaded
    by the slot's list)."""
    name = "fast"
    wants_fast = True

    def reset(self, view, rng):
        super().reset(view, rng)
        self.n_fast = 0

    def act(self, obs):
        acts = list(super().act(obs))
        gone_l = {int(a.lease_id) for a in acts if isinstance(a, Release)}
        gone_r = {int(a.replica_id) for a in acts if isinstance(a, Unload)}
        self.fast_ok = sorted(int(rid) for rid, rv in obs.replicas.items()
                              if rv.lease_id in obs.leases and obs.leases[rv.lease_id].death_min is None
                              and rv.lease_id not in gone_l and rid not in gone_r)
        return acts

    def on_fast(self, obs):
        r, g = self.r, self.view.grid
        if not self.fast_ok or r.random() >= 0.35:
            return []
        rid = int(r.choice(self.fast_ok))
        self.n_fast += 1
        if r.random() < 0.7:
            return [SetAdmission(rid, float(r.choice((0.0, 0.5, 1.0))))]
        return [Drain(rid, int((obs.f + 1) * g.fast_min + r.integers(0, 2 * g.slow_min)))]


ROBUST_MODELS = {"eager": {"schedule": "eager"}, "trace": {"schedule": "trace"},
                 "iid": {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.3}},
                 "refuseI2": {"schedule": "trace", "on_unavailable": "refuse", "information": "I2"}}


def _assert_robust_coverage(runs: list, st: Counter) -> None:
    """The reserve of a robust slot is used: forced aborts right after a robust slot with a positive budget, some with
    stranding in slot t_a and some with a wind-down cost of at least half the budget."""
    rp = [o for o in runs if o["robust_prev"] and o["R"] > 0]
    assert st["robust_slots"] > 0 and rp, (st, len(rp))
    assert any(o["strand_t_a"] > 0 for o in rp) and any(o["phi"] >= 0.5 * o["R"] for o in rp), len(rp)


def test_reserve_robust_slots_quick():
    """Theorem W(b) and the reserve at T0g's robust slots (a list that names an object of its own list): _OwnListInner
    on _rich_instance (the four time grids; kappa_infinite and auto_drain alternating) under eager, trace, iid_step
    (p = 0.3) and 'refuse' under I2 (option passed), wind-down 'adaptive' on even and 'release' on odd variants, with
    forced aborts at every slot. Every reference run passes _t0g_check_x, so the report's reserve at a robust slot is
    sum_c kappa'_c d_c(f_l) a_c and the next slot's stranding bound uses UB_c(f0 - 1) = d_c(f0 - 1) a_c; every abort
    passes _winddown_oracle, so Phi(t_a) <= R(t_a - 1) also where t_a - 1 is a robust slot (_assert_robust_coverage);
    each own-list action type occurs."""
    runs, st, made = [], Counter(), []

    def make(seed):
        made.append(_OwnListInner(seed))
        return made[-1]
    own = Counter()
    for v in range(4):
        for i, (mname, lm) in enumerate(ROBUST_MODELS.items()):
            kinf, ad = bool((v + i) % 2), bool(v % 2)
            inst = _rich_instance(1, v, kinf)
            rule = "adaptive" if v % 2 == 0 else "release"
            made.clear()
            runs += _forced_aborts(inst, LenderModel(**lm), lambda s=11 * v + i + 3: make(s), rule,
                                   ("own", v, mname, kinf, ad, rule), cautious=mname.startswith("refuse"),
                                   info=lm.get("information", "I1"), auto_drain=ad, stats=st)
            own.update(made[0].own)                                  # the reference run's inner
    _assert_robust_coverage(runs, st)
    assert all(own[k] > 0 for k in _OwnListInner.OWN), own


def test_reserve_robust_all_quick():
    """Theorem W(b) and the reserve for an inner policy that uses on_fast (condition C1 fails: T0g's robust form at
    every slot): _FastInner on _rich_instance (the four time grids; kappa_infinite and auto_drain alternating) under
    eager, trace, iid_step (p = 0.3) and 'refuse' under I2 (option passed), wind-down 'adaptive' on even and
    'release' on odd variants, with forced aborts at every slot. Every reference run passes _t0g_check_x with
    robust_all (a-hat = ALG(t-1) + p + rent + Q + the robust stranding bound, and the reserve sum_c kappa'_c d_c(f_l)
    a_c, at every slot); every abort passes _winddown_oracle (the guard releases the inner's leases at t_a, its bound
    being robust, so every wind-down choice is K0); the inner issues fast-slot actions."""
    runs, st, made = [], Counter(), []

    def make(seed):
        made.append(_FastInner(seed))
        return made[-1]
    nfast = 0
    for v in range(4):
        for i, (mname, lm) in enumerate(ROBUST_MODELS.items()):
            kinf, ad = bool((v + i) % 2), bool((v + 1) % 2)
            inst = _rich_instance(2, v, kinf)
            rule = "adaptive" if v % 2 == 0 else "release"
            made.clear()
            runs += _forced_aborts(inst, LenderModel(**lm), lambda s=13 * v + i + 5: make(s), rule,
                                   ("fast", v, mname, kinf, ad, rule), cautious=mname.startswith("refuse"),
                                   info=lm.get("information", "I1"), auto_drain=ad, stats=st, robust_all=True)
            nfast += made[0].n_fast                                  # the reference run's fast-slot actions
    assert nfast > 0 and all(o["robust_prev"] for o in runs if o["t_a"] > 0)
    _assert_robust_coverage(runs, st)
    assert all(c == "K0" for o in runs for c in o["choices"])


@pytest.mark.slow
def test_reserve_forced_aborts():
    """test_reserve_forced_aborts_quick on the whole day of ms s3 and of q44_spot_1day s1: forced aborts at every
    12th slot (offset by the mode), A7, BL1 and BL5 with wind-down 'adaptive' and BL1 also with 'release', the six
    lender modes, each reference run checked by the reserve oracle; violation victims occur in the reference runs
    under 'reclaim'."""
    runs, st = [], Counter()
    for name, seed in (("ms2_multi_small", 3), ("q44_spot_1day", 1)):
        inst = _full(name, seed)
        for k, (mname, lm, cautious) in enumerate(FORCED_MODES):
            model = LenderModel(**lm)
            for inner, rule in (("A7", "adaptive"), ("BL1", "adaptive"), ("BL1", "release"), ("BL5", "adaptive")):
                if inner == "A7" and not HAVE_A7:
                    continue
                runs += _forced_aborts(inst, model, lambda inner=inner: _inner(inner), rule,
                                       (name, seed, mname, inner, rule), slots=range(2 * k, inst.grid.T_slow, 12),
                                       cautious=cautious, stats=st if mname == "reclaim" else None)
    _assert_forced_coverage(runs)
    assert st["victims"] > 0, st


def test_reserve_fb_pd_forced_aborts():
    """The default safe expert 'fb+pd' with forced aborts on ms s3 (6 h) under trace and eager around BL1: in every
    run in which S follows FB from t_a on (Theorem W's proven case), Phi(t_a) <= R(t_a - 1) and the certificate of
    q44_study holds with proven_case; runs in which S follows R are reported, not asserted (case (c))."""
    inst = _ms(3, 360)
    n = {"proven": 0, "other": 0}
    for sched in ("trace", "eager"):
        model = LenderModel(schedule=sched)
        for t_a in range(0, inst.grid.T_slow, 4):
            pol = Guarded(inner="BL1", abort_at=t_a, N_bound=_N(inst), **NO_ABORT)
            res = simulate(inst, pol, model, policy_seed=0)
            rep = res.metrics["policy"]
            c = qs.certificate(res, inst, rep, core_exact=False)
            if c["proven_case"]:
                n["proven"] += 1
                assert c["held"] and c["wind_down_ok"] and c["m_ok"], (sched, t_a, c)
                assert c["wind_down_cost"] <= c["budget_t_a"] + 1e-9 * max(1.0, c["ALG_T"]), (sched, t_a, c)
            else:
                n["other"] += 1
    assert n["proven"] > 0, n


def test_reserve_no_later_than_without():
    """The reserve only adds to the test value: with identical streams the default A8 (reserve on) aborts no later
    than the same A8 with reserve false, and the two runs are equal before the first abort (ms s3, 6 h, trace and
    eager, inner A7, BL1 and BL5, the default allowance); the reserve makes some run abort earlier."""
    inst = _ms(3, 360)
    earlier = 0
    for sched in ("trace", "eager"):
        model = LenderModel(schedule=sched)
        for inner in ("A7", "BL1", "BL5"):
            if inner == "A7" and not HAVE_A7:
                continue
            out = {}
            for r in (True, False):
                res = simulate(inst, Guarded(inner=inner, reserve=r, N_bound=_N(inst)), model, policy_seed=0)
                assert res.invariant_failures == []
                out[r] = (res.metrics["policy"]["t_a"], np.asarray(res.per_slot["total"], dtype=float))
            (ta1, c1), (ta0, c0) = out[True], out[False]
            assert ta1 is not None or ta0 is None, (sched, inner, ta1, ta0)
            assert ta0 is None or ta1 <= ta0, (sched, inner, ta1, ta0)
            first = min(x for x in (ta1, ta0, len(c1)) if x is not None)
            assert np.array_equal(c1[:first], c0[:first]), (sched, inner)
            earlier += int(ta1 is not None and (ta0 is None or ta1 < ta0))
    assert earlier > 0


def test_t0g_refuse_cautious():
    """T0g under on_unavailable 'refuse' with the option passed to A8 (the cautious route of condition C2): on the
    toy (L0 with load time 0, announced at slots 2 and 3), Buys at L0 at slots 2 and 5. Under I1 both are uncertain
    (L0 is not protected): a-hat(2) = the price 0.475 + the slot's fallback 0.5958 (hand values) and G = Q at both
    slots; under I2 the Buy of slot 2 (L0 announced) is uncertain and the one of slot 5 (not announced) counted, so
    a-hat(5) = ALG(5). Under 'refuse' the slot-2 Buy is refused and m = 0 at every slot (ALG(2) = 0.5958 <
    a-hat(2)); cautious_since = 0 from the start. Through drivers/run.py, A8 under 'refuse' gets the option and
    gives the same report as the direct construction."""
    from sublet.drivers import run as drun

    def plan(obs):
        return [Buy(0, 0, 0, 1)] if obs.t in (2, 5) else []
    q, price = 7.15 * 5 / 60.0, 2.85 * 10 / 60.0
    for info in ("I1", "I2"):
        inst = toy_instance({"lenders.0.lam_s": 0.0, "lenders.0.R": [2, 3]})
        pol = Guarded(inner=_Script(plan), test="T0g", safe="fb", on_unavailable="refuse", **NO_ABORT)
        res = simulate(inst, pol, LenderModel(schedule="trace", information=info, on_unavailable="refuse"),
                       policy_seed=0)
        assert res.invariant_failures == []
        rep = res.metrics["policy"]
        t0g = rep["t0g"]
        alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
        assert t0g["cautious_since"] == 0 and t0g["robust_since"] is None and res.metrics["refused"]["unavailable"] == 1
        assert _close(alg[2], q, 1e-12) and _close(rep["guard"]["a_hat"][2], price + q, 1e-12), \
            (info, rep["guard"]["a_hat"][2])
        assert t0g["uncertain"][2] == 1 and _close(t0g["G"][2], t0g["Q"][2], 1e-12)
        if info == "I1":
            assert t0g["uncertain"][5] == 1 and _close(t0g["G"][5], t0g["Q"][5], 1e-12)
        else:
            assert t0g["uncertain"][5] == 0 and _close(rep["guard"]["a_hat"][5], alg[5], 1e-12)
        assert all(x == 0.0 for x in rep["guard"]["m"][:-1]), rep["guard"]["m"]
        _t0g_sound(res, ("refuse", info))
        s = drun.load_run_spec({"schema_version": 1, "name": "t_refuse", "instance": "toy.json",
                                "overrides": {"lenders.0.lam_s": 0.0, "lenders.0.R": [2, 3]},
                                "lender_model": {"schedule": "trace", "information": info, "on_unavailable": "refuse"},
                                "policy": {"id": "A8", "params": {"safe": "fb", **NO_ABORT}}})
        I2_, model, ecfg = drun.build(s, s["seeds"]["config"][0])
        p2 = drun.make_policy(s, I2_)
        assert p2.on_unavailable == "refuse"
        p2.inner = _Script(plan)
        res2 = simulate(I2_, p2, model, ecfg, policy_seed=0)
        assert res2.metrics["policy"]["guard"]["a_hat"] == rep["guard"]["a_hat"], info


def test_reserve_refuse_sound_quick():
    """Under on_unavailable 'refuse' (option passed), ALG(t) <= a-hat(t) at every slot (no abort) for A7, BL1 and BL5
    on ms s3 (12 h) under trace with I1 and I2, and the report equals the oracle with the cautious route
    (_t0g_check_x); some Buys are refused as 'unavailable' and some counted as uncertain."""
    inst = _ms(3, 720)
    unav = unc = 0
    for info in ("I1", "I2"):
        model = LenderModel(schedule="trace", information=info, on_unavailable="refuse")
        for inner in ("A7", "BL1", "BL5"):
            if inner == "A7" and not HAVE_A7:
                continue
            rec = _ObsRec(_inner(inner))
            pol = Guarded(inner=rec, safe="fb", on_unavailable="refuse", **NO_ABORT)
            res = simulate(inst, pol, model, policy_seed=0)
            st = _t0g_check_x(inst, res, rec, False, ("refuse", info, inner), cautious=True, info=info)
            unav += res.metrics["refused"]["unavailable"]
            unc += st.get("uncertain", 0)
    assert unav > 0 and unc > 0, (unav, unc)


# the study's certificate failures (design/q44_practical_sublet.md §8.9) rerun: (block, instance, mode, cell, tag,
# policy seed, recorded test, recorded t_a, recorded core-bound slack), from the run files of commits 9cf16de
# (Q1-Q3) and d2a538d (T2_t0g) under code/sim/out/q44_study/runs/
FAILED_CELLS = [
    pytest.param("Q1", "I4", "L-iid-0.05", 7, "PS-G", 2, "T0", 82, -0.957857, id="Q1-I4-iid05-PS-G-c7-p2"),
    pytest.param("Q1", "I4", "L-iid-0.05", 1, "BL1-G", 0, "T0", 74, -1.001728, id="Q1-I4-iid05-BL1-G-c1-p0"),
    pytest.param("T2_t0g", "I4", "L-eg", 6, "BL5-G-T0g", 0, "T0g", 252, -0.090550, id="T2-I4-eg-BL5-G-c6-p0"),
    pytest.param("T2_t0g", "I4", "L-ss", 2, "PS-G-T0g", 2, "T0g", 101, -0.101453, id="T2-I4-ss-PS-G-c2-p2"),
    pytest.param("Q1", "I2", "L-ss", 7, "BL1-G", 2, "T0", 69, -1.566489, id="Q1-I2-ss-BL1-G-c7-p2",
                 marks=pytest.mark.needs_a12),
    pytest.param("T2_t0g", "I2", "L-eg", 5, "BL5-G-T0g", 0, "T0g", 22, -0.518608, id="T2-I2-eg-BL5-G-c5-p0",
                 marks=pytest.mark.needs_a12),
    pytest.param("T2_t0g", "I3", "L-ss", 2, "BL5-G-T0g", 0, "T0g", 253, -4.923325, id="T2-I3-ss-BL5-G-c2-p0",
                 marks=[pytest.mark.needs_a12, pytest.mark.slow]),
]


@pytest.mark.parametrize("block,instance,mode,cell,tag,pseed,test,t_a,slack", FAILED_CELLS)
def test_reserve_failing_cells(block, instance, mode, cell, tag, pseed, test, t_a, slack):
    """Cells of the study whose full-model certificate failed (§8.9; q44_winddown.py reruns all 170): rerun with
    the run's historical parameters (its test; T0g as at commit d2a538d: reserve false, wind_down 'keep') the run
    reproduces the recorded abort slot and core-bound slack (a shortfall), S follows FB after t_a with no copy, and
    the shortfall is the wind-down (S-mode excess = stranding + rent - routing saving after t_a, by ledger
    component). Rerun with A8's default (test T0g with the reserve, wind_down 'auto'), the certificate holds in
    Theorem W's proven case: ALG(T) <= C_S(T) + (gamma - 1) C_S(t_a - 1) + B(t_a - 1), m = 0, and the wind-down cost
    is at most the budget R(t_a - 1)."""
    from sublet.drivers import run as drun
    b = qs.load_block(block)
    inst = next(i for i in b["instances"] if i["id"] == instance)
    hist = dict(qs.POLICIES[tag]["params"], test=test)
    if test == "T0g":
        hist.update(reserve=False, wind_down="keep")
    out = {}
    for which, params in (("historical", hist), ("default", {k: v for k, v in qs.POLICIES[tag]["params"].items()
                                                            if k != "test"})):
        spec = drun.load_run_spec(qs.run_spec(b, inst, tag, mode, cell, [pseed], params))
        I, model, ecfg = drun.build(spec, cell)
        pol = drun.make_policy(spec, I)
        res = simulate(I, pol, model, ecfg, lender_seed=cell, policy_seed=pseed)
        assert res.invariant_failures == [], (which, res.invariant_failures[:3])
        rep = res.metrics["policy"]
        out[which] = (I, res, rep, qs.certificate(res, I, rep, core_exact=False))
    I, res, rep, c = out["historical"]
    assert c["test"] == test and c["t_a"] == t_a and abs(c["core_bound_slack"] - slack) <= 5e-7, \
        (c["t_a"], c["core_bound_slack"])
    assert not c["held"] and not c["core_bound_ok"] and c["e_mode_ok"] and c["m_ok"]
    assert c["W_S_t_a"] == 0.0 and all(w == "FB" for w, t0, n in rep["safe"]["followed"] if t0 + n > t_a)
    ps = res.per_slot
    Q = _q_slot(I)
    strand, rent = float(np.sum(ps["stranding"][t_a:])), float(np.sum(ps["lease_rent"][t_a:]))
    saving = float(np.sum(Q[t_a:]) - np.sum(ps["routing"][t_a:]) - np.sum(ps["fallback"][t_a:]))
    assert float(np.sum(ps["lease_prepaid"][t_a:]) + np.sum(ps["loading"][t_a:])) == 0.0
    assert _close(c["s_mode_excess"], strand + rent - saving, 1e-9) and strand + rent > 0
    I, res, rep, c = out["default"]
    assert c["test"] == "T0g" and c["reserve"] and c["wind_down"] == "adaptive"
    assert c["held"] and c["core_bound_ok"] and c["m_ok"] and c["e_mode_reserve_ok"], c
    assert c["proven_case"] and c["wind_down_ok"] and c["wind_down_cost"] <= c["budget_t_a"] + c["tol"], c


# ================================================================ the audit of the full-model guard (regressions)
# design/theory/audit_guard.md, section "Audit of the full-model guard": F1 (its X1: a Load on a lease bought in the
# same list, on the toy and with the full-model oracles on the rich instances), F2 (its X3: an inner policy that
# writes to its observation) and the coverage gaps of F4 (forced aborts under the adaptive and safe_site lenders, the
# time grids with notice 0 and with fast slot = slow slot, natural aborts around an inner policy that issues every
# action type). Oracles: hand values on the toy, the ledger, the lease records and the instance's prices;
# _t0g_check_x and _winddown_oracle. The audit's own scripts are code/sim/audit/ (outputs in code/sim/out/audit_fm/).
from sublet.algos.guard import buy_price, inner_obs, slot_terms
from sublet.instance import public_view
from sublet.types import SlowObs


def _toy_obs(inst, leases=None) -> SlowObs:
    """A slot-0 observation of the toy with the given lease views and nothing else."""
    n, phi, J, m = inst.n, inst.grid.phi, inst.J, inst.m
    return SlowObs(t=0, minute=0, demand=np.ones((n, phi)), leases=dict(leases or {}), replicas={}, notices=[],
                   ended=[], results=[], site_announced=None, served_prev=np.zeros((J, m)), fallback_prev=np.zeros(n),
                   cost_so_far=0.0)


def test_audit_f1_slot_terms_hand():
    """slot_terms prices a Load on a lease that the same list buys at the largest beta_jl over the sites of the Buys
    that precede it (audit F1; hand values on the toy with beta = 0.1, 0.4 and 0.25 at L0, L1 and P): after Buys at
    L0 and L1, 0.4; after a Buy at L0 only (the Buy at L1 comes later), 0.1, the exact charge; with no earlier Buy,
    0.4, the largest over all sites; a Load on a lease of obs, beta at its site. The Buys are priced g a P / 60 +
    n beta. T0, T0g and T1 take p_E(t) from slot_terms."""
    from sublet.types import LeaseView
    inst = toy_instance({})
    assert (inst.J, inst.m) == (1, 3)
    inst.beta_usd = np.array([[0.1, 0.4, 0.25]])
    view = public_view(inst, "I1")
    k0, k1 = sorted(inst.sites[0].menu)[0], sorted(inst.sites[1].menu)[0]
    b0, b1 = Buy(0, k0, 0, 1), Buy(1, k1, 0, 1)

    def bp(l, k):
        g, P = inst.llms[0].g, inst.contracts[k].prepaid_min
        return g * float(inst.price[l, k]) * P / 60.0 + float(inst.beta_usd[0, l])
    assert _close(buy_price(view, b0), bp(0, k0), 1e-12) and _close(buy_price(view, b1), bp(1, k1), 1e-12)
    obs = _toy_obs(inst)
    for acts, load in (([b0, b1, Load(0, 0)], 0.4), ([b0, Load(0, 0), b1], 0.1), ([Load(7, 0)], 0.4)):
        p, _ = slot_terms(view, obs, acts)
        buys = sum(bp(a.site, a.contract) for a in acts if isinstance(a, Buy))
        assert _close(p, buys + load, 1e-12), (acts, p, buys + load)
    L = LeaseView(5, 2, sorted(inst.sites[2].menu)[0], 1, 0, 0, 10 ** 6, None, None, ())
    p, _ = slot_terms(view, _toy_obs(inst, {5: L}), [Load(5, 0)])
    assert _close(p, 0.25, 1e-12), p


class _LateOwnLoad(Policy):
    """Idle until slot t_act, then [Buy(P, k, 0, 1), Unload(0), Load(0, 0)] at the protected site P (audit X1): the
    run's first lease and replica get id 0; the Unload frees the new lease's GPUs, so the engine accepts the Load."""
    name = "late-own-load"

    def __init__(self, t_act: int):
        self.t_act = int(t_act)

    def act(self, obs):
        if int(obs.t) != self.t_act:
            return []
        P = next(l for l, s in enumerate(self.view.sites) if s.kind == "protected")
        return [Buy(P, sorted(self.view.sites[P].menu)[0], 0, 1), Unload(0), Load(0, 0)]


def test_audit_f1_load_on_own_lease():
    """Audit F1 (X1): on the toy with beta = 0.4 at every site, an inner policy idle until slot T-1 that then buys a
    protected lease, unloads its replica and loads LLM 0 onto it. The engine accepts the Load and books 2 beta = 0.8
    of loading at T-1. Under T0g, T0 and T1 the purchase term p_E(T-1) is the Buy's price g a P / 60 + beta plus the
    Load's beta (from the instance's prices); under T0g and T0 m(T-1) = 0 and a-hat(T-1) = ALG(T) (exact: the toy has
    no stranding and the new replicas serve nothing in the last slot). With B0 chosen to make slot T-1's T0g test an
    equality (a-hat + R = C_S + B0), Theorem W(a) holds: ALG(T) <= gamma C_S(T) + B(T) - R(T-1). Before the fix,
    p_E missed the Load, m(T-1) = beta and Theorem W(a) failed by beta."""
    beta = 0.4
    inst = toy_instance({})
    inst.beta_usd = np.full_like(np.asarray(inst.beta_usd, dtype=float), beta)
    T = inst.grid.T_slow
    P = next(l for l, s in enumerate(inst.sites) if s.kind == "protected")
    k = sorted(inst.sites[P].menu)[0]
    pE = inst.llms[0].g * float(inst.price[P, k]) * inst.contracts[k].prepaid_min / 60.0 + 2 * beta
    for test in ("T0g", "T0", "T1"):
        res = simulate(inst, Guarded(inner=_LateOwnLoad(T - 1), test=test, safe="fb", **NO_ABORT), LenderModel(),
                       policy_seed=0)
        assert res.invariant_failures == []
        rep = res.metrics["policy"]
        alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
        assert rep["t_a"] is None and _close(float(res.per_slot["loading"][T - 1]), 2 * beta, 1e-12)
        assert sum(1 for r in res.replicas if r.load_start_min == (T - 1) * inst.grid.slow_min) == 2
        assert _close(rep["terms"][T - 1][0], pE, 1e-12), (test, rep["terms"][T - 1][0], pE)
        if test != "T1":
            ah = rep["guard"]["a_hat"][T - 1]
            assert _close(ah, alg[T - 1], 1e-12), (test, ah, alg[T - 1])                 # m(T-1) = 0, exact
    res = simulate(inst, Guarded(inner=_LateOwnLoad(T - 1), test="T0g", safe="fb", **NO_ABORT), LenderModel(),
                   policy_seed=0)
    g = res.metrics["policy"]["guard"]
    B0 = g["a_hat"][T - 1] + g["reserve"][T - 1] - g["C_S"][T - 1]
    res2 = simulate(inst, Guarded(inner=_LateOwnLoad(T - 1), test="T0g", safe="fb", B0=B0, kappa=None), LenderModel(),
                    policy_seed=0)
    g2 = res2.metrics["policy"]["guard"]
    assert res2.metrics["policy"]["t_a"] is None
    ALG = float(np.sum(res2.per_slot["total"]))
    assert ALG <= g2["C_S"][T - 1] + B0 - g2["reserve"][T - 1] + TOL * max(1.0, ALG), (ALG, g2["C_S"][T - 1], B0)
    assert all(x == 0.0 for x in g2["m"][:-1]), g2["m"]


class _OwnLoadInner(_OwnListInner):
    """X1's pattern on the rich instances (audit F1): _RandomInner that, at about a third of its slots, starts its list
    with [Buy(P, k, j, n), Unload(the Buy's first replica), Load(the new lease, j2)] at the protected site P, with
    g_j2 <= g_j, so that the Unload frees enough GPUs and the engine accepts the Load and charges beta_j2,P. The ids
    are tracked as in _OwnListInner; own['accepted'] counts the accepted Loads of this kind (from obs.results), and
    own_slots lists the slots whose list carries the pattern."""
    name = "ownload"
    OWN = ("unload_load",)

    def reset(self, view, rng):
        super().reset(view, rng)
        self.pending = None
        self.own_slots = []

    def act(self, obs):
        for r in obs.results:
            if r.ok and isinstance(r.action, Buy):
                self.next_lease = max(self.next_lease, int(r.lease_id) + 1)
            if r.ok and isinstance(r.action, (Buy, Load)) and r.replica_ids:
                self.next_rep = max(self.next_rep, max(int(x) for x in r.replica_ids) + 1)
            if r.ok and isinstance(r.action, Load) and self.pending is not None and int(r.lease_id) == self.pending:
                self.own["accepted"] += 1
        self.pending = None
        acts = list(_RandomInner.act(self, obs))
        r, view = self.r, self.view
        if r.random() < 0.35:
            lid, rid = self.next_lease, self.next_rep
            g = [x.g for x in view.llms]
            j = int(r.integers(0, len(g)))
            j2 = int(r.choice([x for x in range(len(g)) if g[x] <= g[j]]))
            buy = Buy(self.P, int(sorted(view.sites[self.P].menu)[0]), j, int(r.choice((1, 2))))
            acts = [buy, Unload(rid), Load(lid, j2)] + acts
            self.own["unload_load"] += 1
            self.own_slots.append(int(obs.t))
            self.pending = lid
        return acts


def test_audit_f1_own_load_rich_quick():
    """Audit F1 with the full-model oracles: _OwnLoadInner on _rich_instance (variants 0, 1, 4 and 5; random beta_jl
    per LLM and site) under trace, eager and 'refuse' under I2 (option passed), kappa_infinite and auto_drain
    alternating, wind-down 'adaptive' and 'release' alternating, with forced aborts at every slot. Every reference run
    passes _t0g_check_x: the report's a-hat(t) equals the oracle's, whose p_E(t) prices the Load on the new lease
    (_p_rent_x, which asserts that the lease was bought at t at the site of an earlier Buy of the list and that the
    price is at least the engine's charge), and ALG(t) <= a-hat(t) at every executed slot, the slots with an accepted
    Load of this kind included (T0g's robust form there); every abort passes _winddown_oracle. Such Loads are
    accepted in the reference runs (counted from obs.results), and in each reference run every slot whose list
    carries the pattern is one of the run's robust slots (checked slot by slot against the report's robust_slots)."""
    models = {k: ROBUST_MODELS[k] for k in ("trace", "eager", "refuseI2")}
    runs, st, made, own = [], Counter(), [], Counter()

    def make(seed):
        made.append(_OwnLoadInner(seed))
        return made[-1]
    for v in (0, 1, 4, 5):
        for i, (mname, lm) in enumerate(models.items()):
            kinf, ad = bool((v + i) % 2), bool(v % 2)
            inst = _rich_instance(4, v, kinf)
            rule = "adaptive" if (v + i) % 2 == 0 else "release"
            made.clear()
            refs = []
            runs += _forced_aborts(inst, LenderModel(**lm), lambda s=17 * v + i + 1: make(s), rule,
                                   ("ownload", v, mname, kinf, ad, rule), cautious=mname.startswith("refuse"),
                                   info=lm.get("information", "I1"), auto_drain=ad, stats=st, refs=refs)
            ref_inner = made[0]                                      # the reference run's inner
            own.update(ref_inner.own)
            assert len(refs) == 1 and len(ref_inner.own_slots) == ref_inner.own["unload_load"], (v, mname)
            rob = set(refs[0].metrics["policy"]["t0g"]["robust_slots"])
            miss = sorted(set(ref_inner.own_slots) - rob)
            assert not miss, (v, mname, miss, sorted(rob))
            st["own_slots"] += len(ref_inner.own_slots)
    assert own["unload_load"] > 0 and own["accepted"] > 0, own
    assert st["own_slots"] == own["unload_load"] and st["robust_slots"] >= own["unload_load"] > 0, (st, own)
    _assert_forced_coverage(runs)


class _Writer(Policy):
    """Audit X3's inner policy: at every slot it releases every held lease and buys one protected lease; `write` then
    writes to its observation: 'cost' sets obs.cost_so_far = 0 (before choosing its actions), 'leases', 'replicas',
    'results' and 'ended' clear those containers and 'demand' zeroes the demand array (after choosing them)."""
    name = "writer"

    def __init__(self, write=None):
        self.write = write

    def act(self, obs):
        P = next(l for l, s in enumerate(self.view.sites) if s.kind == "protected")
        if self.write == "cost":
            obs.cost_so_far = 0.0
        acts = [Release(l) for l in obs.leases] + [Buy(P, sorted(self.view.sites[P].menu)[0], 0, 1)]
        if self.write in ("leases", "replicas", "results", "ended"):
            getattr(obs, self.write).clear()
        elif self.write == "demand":
            obs.demand[...] = 0.0
        return acts


def test_audit_f2_inner_obs():
    """Audit F2 (X3): the guard's test does not depend on what the inner policy writes to its observation. On the toy
    (T0g, gamma = 1, B0 = 2, safe 'fb') each writing variant of _Writer runs exactly as the policy that does not
    write: equal per-slot ledger, a-hat(t) and abort slot (t_a = 4), and ALG(T) <= gamma C_S(T) + B(T). Before the fix
    the variants 'cost', 'leases' and 'demand' changed the test (never aborted, or aborted later or earlier), and
    'cost' gave ALG(T) above even (1 + gamma) C_S(T) + B(T). inner_obs itself: equal fields, new containers and
    arrays, shared immutable entries, PolicyError for a field of another mutable type; the records it shares (the
    entries of obs.leases, obs.replicas, obs.notices and obs.results, and the actions in the results) are frozen
    dataclasses."""
    inst = toy_instance({})

    def run(write):
        res = simulate(inst, Guarded(inner=_Writer(write), test="T0g", safe="fb", gamma=1.0, B0=2.0, kappa=None),
                       LenderModel(), policy_seed=0)
        assert res.invariant_failures == []
        return res, res.metrics["policy"]
    ref, rref = run(None)
    assert rref["t_a"] == 4
    for write in ("cost", "leases", "replicas", "results", "ended", "demand"):
        res, rep = run(write)
        assert rep["t_a"] == rref["t_a"] and rep["guard"]["a_hat"] == rref["guard"]["a_hat"], write
        for k, v in ref.per_slot.items():
            assert np.array_equal(np.asarray(res.per_slot[k]), np.asarray(v)), (write, k)
        ALG = float(np.sum(res.per_slot["total"]))
        assert ALG <= rep["safe"]["C_S_curve"][-1] + rep["safe"]["B_curve"][-1] + TOL * max(1.0, ALG), (write, ALG)
    from sublet.types import LeaseView
    L = LeaseView(3, 0, 0, 1, 0, 0, 10, None, None, ())
    obs = _toy_obs(inst, {3: L})
    obs.ended.append((1, 0, "release"))
    obs.site_announced = np.zeros(inst.m, dtype=bool)
    cp = inner_obs(obs)
    for f in dataclasses.fields(obs):
        a, b = getattr(obs, f.name), getattr(cp, f.name)
        if isinstance(a, np.ndarray):
            assert np.array_equal(a, b) and not np.shares_memory(a, b), f.name
        elif isinstance(a, (dict, list)):
            assert a == b and a is not b, f.name
        else:
            assert a == b, f.name
    assert cp.leases[3] is L and cp.ended[0] is obs.ended[0]
    cp.leases.clear()
    cp.ended.clear()
    cp.demand.fill(7.0)
    assert obs.leases == {3: L} and obs.ended == [(1, 0, "release")] and np.all(obs.demand == 1.0)
    obs.notices = set()
    with pytest.raises(PolicyError):
        inner_obs(obs)
    from sublet.types import ActionResult, Notice, ReplicaView
    for cls in (LeaseView, ReplicaView, Notice, ActionResult, Buy, Release, Load, Unload, Drain, SetAdmission):
        assert dataclasses.is_dataclass(cls) and cls.__dataclass_params__.frozen, cls


F4_MODELS = {"adaptive": {"schedule": "adaptive"},
             "safe": {"schedule": "safe_site", "params": {"D_slots": 2, "k": 2, "Phi": None}},
             "trace": {"schedule": "trace"}}


def _notice0_deaths(inst, refs) -> int:
    """Leases of the runs `refs` announced with notice 0 (death at the start of the announcement slot)."""
    Ds = inst.grid.slow_min
    return sum(1 for r in refs for L in r.leases if L.announce_slot is not None and L.death_min == L.announce_slot * Ds)


def _f4_forced(variants, models, seeds) -> tuple:
    """_forced_aborts around _RandomInner on _rich_instance for every (seed, variant, lender model): kappa_infinite,
    auto_drain and the wind-down rule alternate. Returns (the aborts' oracle records, the reference runs, the leases
    announced in the reference runs by model, the leases announced with notice 0, the cases with phi = 1)."""
    runs, refs, ann, n0, phi1 = [], [], Counter(), 0, 0
    for s in seeds:
        for v in variants:
            for i, (mname, lm) in enumerate(models.items()):
                kinf, ad = bool((s + v + i) % 2), bool((s + i) % 2)
                inst = _rich_instance(s, v, kinf)
                rule = "adaptive" if (s + v + i) % 2 == 0 else "release"
                rr = []
                cautious = lm.get("on_unavailable") == "refuse"
                runs += _forced_aborts(inst, LenderModel(**lm),
                                       lambda s=s, v=v, i=i: _RandomInner(31 * s + 7 * v + i),
                                       rule, ("f4", s, v, mname, kinf, ad, rule), cautious=cautious,
                                       info=lm.get("information", "I1"), auto_drain=ad, refs=rr)
                refs += rr
                ann[mname] += sum(1 for L in rr[0].leases if L.announce_slot is not None)
                n0 += _notice0_deaths(inst, rr)
                phi1 += int(inst.grid.phi == 1)
    return runs, refs, ann, n0, phi1


def test_audit_f4_forced_aborts_quick():
    """Audit F4: Theorem W(b) with a forced abort at every slot under the lenders adaptive (C3-T4's) and safe_site,
    which the other forced-abort tests do not use, around _RandomInner (every slow-slot action type), kappa_infinite
    and auto_drain alternating, wind-down 'adaptive' and 'release' alternating: on the time grids with notice 0
    (variants 4 and 5 of _rich_instance: notice 0 for the short contract, with fast slot = slow slot, phi = 1, on
    variant 4) under adaptive, safe_site and trace for two seeds (12 cases), and on the four grids of _RICH (variants
    0-3) under adaptive and safe_site for one seed (8 cases). Every reference run passes _t0g_check_x (a-hat, G, S
    and R equal the oracle and ALG(t) <= a-hat(t)) and every abort _winddown_oracle (Phi(u) <= the budget, the core
    bound); coverage: both lenders announce leases of the platform on both sets of grids, a lease dies at the start
    of its announcement slot (notice 0), phi = 1 occurs, and _assert_forced_coverage on each set."""
    runs, refs, ann, n0, phi1 = _f4_forced((4, 5), F4_MODELS, (0, 1))
    assert len(refs) == 12 and phi1 == 6, (len(refs), phi1)
    assert ann["adaptive"] > 0 and ann["safe"] > 0 and n0 > 0, (ann, n0)
    _assert_forced_coverage(runs)
    runs, refs, ann, _, phi1 = _f4_forced((0, 1, 2, 3), {k: F4_MODELS[k] for k in ("adaptive", "safe")}, (0,))
    assert len(refs) == 8 and phi1 == 0 and ann["adaptive"] > 0 and ann["safe"] > 0, (len(refs), phi1, ann)
    _assert_forced_coverage(runs)


@pytest.mark.slow
def test_audit_f4_forced_aborts():
    """test_audit_f4_forced_aborts_quick on the four grids of _RICH_EXTRA (variants 4-7: also notice = slow slot with
    phi = 6 and a fast slot that does not divide the notice) under adaptive, safe_site, trace, eager, iid_step (p =
    0.3), correlated (p_sh = 1), 'refuse' under I1 and I2 (option passed) and trace under I2, for two seeds (72
    cases)."""
    models = dict(F4_MODELS, eager={"schedule": "eager"},
                  iid={"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.3}},
                  corr={"schedule": "correlated", "params": {"p_sh": 1.0, "groups": "all"}},
                  refuse={"schedule": "trace", "on_unavailable": "refuse"},
                  refuseI2={"schedule": "trace", "on_unavailable": "refuse", "information": "I2"},
                  traceI2={"schedule": "trace", "information": "I2"})
    runs, refs, ann, n0, phi1 = _f4_forced((4, 5, 6, 7), models, (2, 3))
    assert len(refs) == 72 and n0 > 0 and ann["adaptive"] > 0 and ann["safe"] > 0, (len(refs), n0, ann)
    _assert_forced_coverage(runs)


def test_audit_f4_natural_aborts_quick():
    """Audit F4, natural aborts (X4's checks): A8 under T0g with the reserve, safe 'fb', gamma in {0.5, 1, 1.7} and
    B0 in {0, 0.5} (constant allowance), around _RandomInner on _rich_instance (variants 0, 4 and 5) under trace,
    adaptive and safe_site, wind-down 'adaptive' and 'release' alternating. Each run passes _t0g_check_x at its
    executed slots, and from the ledger and the instance (C_S the cumulative all-fallback cost Q): without an abort
    ALG(T) <= gamma C_S(T) + B0 - R(T-1) (Theorem W(a)); with one, ALG(T) <= C_S(T) + (gamma - 1) C_S(t_a - 1) + B0
    (Theorem W(b) with B(t_a - 1) = B0, 0 for t_a = 0) and Phi(t_a) <= R(t_a - 1). Both cases occur, and some aborts
    hold inner leases at t_a."""
    st = Counter()
    for v in (0, 4, 5):
        for i, (mname, lm) in enumerate(F4_MODELS.items()):
            inst = _rich_instance(9, v, bool((v + i) % 2))
            Q = _q_slot(inst)
            C_S = np.cumsum(Q)
            for gamma in (0.5, 1.0, 1.7):
                for B0 in (0.0, 0.5):
                    rule = ("adaptive", "release")[(v + i) % 2]
                    rec = _ObsRec(_RandomInner(97 + 13 * v + i))
                    pol = Guarded(inner=rec, test="T0g", safe="fb", gamma=gamma, B0=B0, kappa=None, wind_down=rule)
                    res = simulate(inst, pol, LenderModel(**lm), EngineConfig(auto_drain=bool(i % 2)), policy_seed=0)
                    tag = (v, mname, gamma, B0, rule)
                    _t0g_check_x(inst, res, rec, bool(i % 2), tag)
                    rep = res.metrics["policy"]
                    assert np.allclose(rep["safe"]["C_S_curve"], C_S, rtol=1e-12, atol=1e-9), tag
                    tot = np.asarray(res.per_slot["total"], dtype=float)
                    ALG = float(tot.sum())
                    tol = TOL * max(1.0, ALG)
                    t_a = rep["t_a"]
                    R = rep["guard"]["reserve"]
                    if t_a is None:
                        st["no_abort"] += 1
                        assert ALG <= gamma * C_S[-1] + B0 - R[-1] + tol, tag
                        continue
                    st["abort"] += 1
                    st["held"] += int(rep["exec"]["inherited"] > 0)
                    phi = float(np.sum(tot[t_a:] - Q[t_a:]))
                    Rp = R[t_a - 1] if t_a > 0 else 0.0
                    assert phi <= Rp + tol, (tag, t_a, phi, Rp)
                    bound = C_S[-1] + (gamma - 1.0) * (C_S[t_a - 1] if t_a > 0 else 0.0) + (B0 if t_a > 0 else 0.0)
                    assert ALG <= bound + tol, (tag, t_a, ALG, bound)
    assert st["no_abort"] > 0 and st["abort"] > 0 and st["held"] > 0, st
