"""Tests of policy A8P, the projected guard (sublet/algos/guard.py, ProjectedGuarded; design/sublet_v2.md §2.4, §2.6,
§8.1 C36, §8.3 tests/test_guard_projection.py).

Oracles: hand-made observations for the candidate ladder of §2.4 step 3 (the rule recomputed here); A8 (guard.Guarded)
around the same inner policy for the runs in which A8P must equal it (project false; project true with no projected slot
before the abort, or none at all); T0g's oracle _t0g_oracle_x of tests/test_guard.py, through _t0g_check_x (runs without
an abort) or _oracle_executed (the executed slots of a run that may abort), on the lists that A8P executed, which
recomputes a-hat(t), G(t), S(t) and the reserve R(t) from the ledger, the lease and replica records and the instance
(and checks ALG(t) <= a-hat(t)); the ledger, the instance's all-fallback cost Q(t) (C_S(t) with S on FB) and the
allowance rebuilt from the public view (guard.b0_auto, guard.c_min; at A8P's allowance 'lb' an independent
online_lb.OnlineLB) for the envelope ALG(t) + R(t) <= gamma C_S(t) + B(t); for Remark R at 'lb', A8 is A8P at project
false (Guarded.act at the same allowance; _remark_r_compare); the engine's results and ended leases against the inner
policy's recorded observations for the refusal mapping. Proposition P is checked at every E-mode slot by evaluating K0
at the slot's state (after T0gBound.begin, before the slot's commit), whether A8P executes it or not. The inner policies
_RandomInner, _OwnListInner and _FastInner are those of tests/test_guard.py (every slow-slot action type; actions on
objects of the inner's own list; on_fast); _ResultsInner (test_remark_r_coverage) adds draws that depend on every field
and on the order of the results it receives, blocks of 8 or more Buys and fast actions that the guard must drop. The
marker needs_raw: A8P with project false reproduces the stored E7 Sublet run of pilot step P0 (§5) to 1e-9 USD.
"""
from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import zlib
from collections import Counter
from types import SimpleNamespace

import numpy as np
import pytest

from fixtures import toy_instance
from test_guard import (F4_MODELS, HAVE_A7, NO_ABORT, RICH_MODELS, ROBUST_MODELS, T0G_TOL, _FastInner, _N, _ObsRec,
                        _OwnListInner, _RandomInner, _inner, _ms, _names_unseen, _no_times, _q_slot, _rich_instance,
                        _same_ledger, _t0g_check_x, _t0g_oracle_x, _toy_obs)

from sublet.algos import guard, online_lb
from sublet.algos.a5 import G2
from sublet.algos.common import PolicyError
from sublet.algos.guard import GUARD_TOL, INNER_IDS, PROJ_INNER_IDS, Guarded, ProjectedGuarded, slot_terms
from sublet.engine import EngineConfig, simulate
from sublet.instance import public_view
from sublet.metrics import _jsonable
from sublet.policies.base import Policy
from sublet.types import ActionResult, Buy, Drain, LeaseView, LenderModel, Load, Release, ReplicaView, SetAdmission, \
    Unload

ADDED = ("project", "projection", "candidates", "dropped_fast", "allowance", "online_lb")   # A8P's keys beyond A8's
ZERO = {"slots": 0, "P1": 0, "P0": 0, "K0": 0, "dropped_buys": 0, "dropped_other": 0, "guard_releases": 0}
ACTION_TYPES = ("Buy", "Release", "Load", "Unload", "SetAdmission", "Drain")
# lender models of the Proposition P runs: RICH_MODELS, 'refuse' under I1 and I2 (the option passed to A8P), and the
# adaptive (C3-T4) and safe_site lenders of F4_MODELS
P_MODELS = dict(RICH_MODELS, refuse={"schedule": "trace", "on_unavailable": "refuse"},
                refuseI2={"schedule": "trace", "on_unavailable": "refuse", "information": "I2"},
                adaptive=F4_MODELS["adaptive"], safe=F4_MODELS["safe"])
# allowances of the Proposition P runs: Algorithm 1's (constant and capped; _p_cases cycles through these three) and
# A8P's 'lb' (B = min{W_k, LB'} of online_lb.OnlineLB; kappa None)
P_ALLOWANCES = ({"B0": 0.3, "kappa": None}, {"B0": 3.0, "kappa": None}, {"B0": "auto", "kappa": 10.0},
                {"allowance": "lb", "kappa": None})
P_LB = P_ALLOWANCES[3]


def _canon(x):
    """A report as canonical JSON (non-finite floats as strings, metrics._jsonable), without wall times."""
    return json.dumps(_jsonable(_no_times(x)), sort_keys=True)


def _as_a8(rep: dict) -> dict:
    """A8P's report without the keys that A8P adds to A8's."""
    return {k: v for k, v in rep.items() if k not in ADDED}


def _same_run(res_p, res_a, tag) -> None:
    """A8P's run equals A8's: ledger, components and lease records bitwise, and the reports equal once A8P's added
    keys (and the wall times) are left out."""
    assert res_p.invariant_failures == [] and res_a.invariant_failures == [], tag
    _same_ledger(res_p, res_a, str(tag))
    assert _canon(_as_a8(res_p.metrics["policy"])) == _canon(res_a.metrics["policy"]), tag


def _e_rle(n: int) -> list:
    return [["E", 0, n]] if n else []


class _Probe(ProjectedGuarded):
    """A8P that records, at every E-mode slot: the engine's observation (results, ended, lease ids, replica -> lease),
    the inner's list A_E(t), the candidates, K0's evaluation at the slot's state (the guard's test terms and the
    budget R(t - 1)), the executed list, its candidate and its source indices. Nothing it records changes the run."""

    def reset(self, view, rng):
        super().reset(view, rng)
        self.log: dict[int, dict] = {}

    def act(self, obs):
        t = int(obs.t)
        if self.mode == "E":
            self.log[t] = {"results": list(obs.results), "ended": list(obs.ended),
                           "obs_l": {int(x) for x in obs.leases},
                           "obs_r": {int(r): int(rv.lease_id) for r, rv in obs.replicas.items()}}
        out = super().act(obs)
        e = self.log.get(t)
        if e is not None:
            e["executed"], e["mode"] = list(out), self.modes[-1]
            if e["mode"] == "E" and "cands" in e:
                e["name"] = self.cands[-1]
                e["src"] = next(c[2] for c in e["cands"] if c[1] is out)
        return out

    def candidates(self, obs, acts):
        cands = super().candidates(obs, acts)
        e = self.log[int(obs.t)]
        e["acts"], e["cands"] = list(acts), cands
        sx, rt, tb = self.sx, self.ratchet, self.t0g
        k0 = cands[-1][1]
        Q = float(sx.fb_inc)
        pE, rent = slot_terms(self.view, obs, k0)
        ev = tb.evaluate(obs, k0, Q)
        rhs = rt.gamma * float(sx.C_S) + float(rt.allowance(sx.B_on))
        # a-hat with Ratchet.test_value's association, ((ALG(t - 1) + p) + rent) + (G + S): the guard passes the
        # service term G + S as one float (ProjectedGuarded._evaluate)
        a_hat = float(obs.cost_so_far) + float(pE) + float(rent) + float(ev["G"] + ev["S"])
        e["k0"] = {"robust": bool(tb.robust), "FB": sx.followed == "FB", "pE": pE, "rent": rent, "G": ev["G"],
                   "S": ev["S"], "R": ev["reserve"], "Q": Q, "form": ev["form"], "budget": float(self.budget),
                   "a_hat": a_hat, "rhs": rhs}
        return cands


def _executed_rec(pol: _Probe) -> SimpleNamespace:
    """The executed lists of A8P's E-mode slots in the recorder shape that _t0g_check_x reads (acts, obs_l, obs_r,
    results per slot)."""
    ex = {t: e for t, e in pol.log.items() if e.get("mode") == "E"}
    return SimpleNamespace(acts={t: e["executed"] for t, e in ex.items()}, obs_l={t: e["obs_l"] for t, e in ex.items()},
                           obs_r={t: e["obs_r"] for t, e in ex.items()},
                           results={t: e["results"] for t, e in ex.items()})


def _oracle_executed(inst, res, rec, auto_drain: bool, tag, cautious: bool = False, info: str = "I1",
                     robust_all: bool = False) -> None:
    """_t0g_check_x's comparisons at the executed slots only, for a run that may abort (_t0g_check_x compares the
    report's robust slots, which include the aborting slot's evaluation, with the oracle's executed ones): the report's
    a-hat, G, S and reserve equal T0g's oracle on the executed lists, and ALG(t) <= a-hat(t)."""
    rep = res.metrics["policy"]
    t0g = rep["t0g"]
    assert t0g["robust_all"] == bool(robust_all) and t0g["cautious_since"] == (0 if cautious else None), tag
    orc, _st = _t0g_oracle_x(inst, res, rec, auto_drain, cautious, info, robust_all)
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
    for i, t in enumerate(sorted(orc)):
        ah, G, S, R = orc[t]
        assert t0g["slots"][i] == t and abs(rep["guard"]["a_hat"][i] - ah) <= T0G_TOL * max(1.0, abs(ah)), (tag, t)
        for got, want in ((t0g["G"][i], G), (t0g["S"][i], S), (t0g["reserve"][i], R), (rep["guard"]["reserve"][i], R)):
            assert abs(got - want) <= T0G_TOL * max(1.0, abs(want)), (tag, t, got, want)
        assert alg[t] <= ah + T0G_TOL * max(1.0, alg[t]), (tag, t, alg[t], ah)


def _allowance(inst, B0, kappa, allowance: str = "alg1", info: str = "I1") -> np.ndarray:
    """(T_slow,) B(t) = B0 (kappa None) or min{B0, kappa B_on(t)}, B_on(t) = sum_j min{F_j(t), C^min_j} with F_j(t)
    the cumulative all-fallback cost of LLM j from the instance's demand; B0 'auto' is guard.b0_auto. At allowance 'lb'
    the B series of an independent online_lb.OnlineLB stepped over the instance's demand (online_lb.series) under the
    view of information model `info`."""
    if allowance == "lb":
        assert kappa is None
        return online_lb.series(public_view(inst, info), inst.clients.demand)["B"]
    view = public_view(inst, "I1")
    b0 = guard.b0_auto(view) if B0 == "auto" else float(B0)
    T = inst.grid.T_slow
    if kappa is None:
        return np.full(T, b0)
    g = inst.grid
    q = np.array([x.q_usd_per_h for x in inst.llms])
    cl = np.asarray(inst.clients.llm)
    d = np.asarray(inst.clients.demand, dtype=float)[:, :T * g.phi].reshape(len(cl), T, g.phi).sum(axis=2)
    fb = q[cl][:, None] * d * g.fast_min / 60.0                     # (n, T) per client and slot
    F = np.cumsum(np.array([fb[cl == j].sum(axis=0) for j in range(inst.J)]), axis=1)
    B_on = np.minimum(F, guard.c_min(view)[:, None]).sum(axis=0)
    return np.minimum(b0, float(kappa) * B_on)


def _envelope(inst, res, gamma: float, B: np.ndarray, tag) -> int:
    """ALG(t) + R(t) <= gamma C_S(t) + B(t) + GUARD_TOL max(1, |rhs|) at every executed slot (Theorem W, step (1)),
    with ALG from the ledger, C_S(t) the cumulative Q(t) (S on FB; the report's curve is checked against it), B(t)
    rebuilt (checked against the report's) and R(t) the report's reserve (equal to the oracle's after _t0g_check_x),
    up to the routing LP's tolerance T0G_TOL. Returns the number of slots checked."""
    rep = res.metrics["policy"]
    g = rep["guard"]
    t_a = rep["t_a"]
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
    C_S = np.cumsum(_q_slot(inst))
    assert np.allclose(rep["safe"]["C_S_curve"], C_S, rtol=1e-12, atol=1e-9), tag
    n = 0
    for i, t in enumerate(g["slots"]):
        assert abs(g["B"][i] - B[t]) <= 1e-12 * max(1.0, abs(B[t])), (tag, t, g["B"][i], B[t])
        if t_a is not None and t >= t_a:
            continue
        rhs = gamma * C_S[t] + B[t]
        lhs = alg[t] + g["reserve"][i]
        assert lhs <= rhs + GUARD_TOL * max(1.0, abs(rhs)) + T0G_TOL * max(1.0, alg[t]), (tag, t, lhs, rhs)
        n += 1
    return n


def _p1_sizes(nb: int) -> list:
    """The P1 prefix lengths of §2.4 step 3(b) for n_b Buys."""
    return sorted({nb - 1, nb // 2, nb // 4, 1} - {0, nb}, reverse=True) if nb >= 2 else []


def _check_ladder(e: dict, tag) -> None:
    """The candidates of one slot against §2.4 step 3, recomputed from A_E(t) and the observation: E = A_E(t); the
    P1 prefixes (first n Buys and A^-_E(t), in A_E(t)'s order); P0 = A^-_E(t) when n_b >= 1 or A^- differs from A;
    K0 = a Release of every lease of obs and nothing else. Every candidate but E names only objects of obs."""
    acts, cands = e["acts"], e["cands"]
    L = e["obs_l"]
    R = {r for r, lid in e["obs_r"].items() if lid in L}

    def in_obs(a):
        if isinstance(a, (Release, Load)):
            return int(a.lease_id) in L
        return isinstance(a, (Unload, SetAdmission, Drain)) and int(a.replica_id) in R
    buys = [i for i, a in enumerate(acts) if isinstance(a, Buy)]
    minus = [i for i, a in enumerate(acts) if not isinstance(a, Buy) and in_obs(a)]
    want = [("E", list(range(len(acts))))]
    want += [("P1", sorted(buys[:n] + minus)) for n in _p1_sizes(len(buys))]
    if buys or len(minus) < len(acts):
        want.append(("P0", minus))
    assert [(c[0], list(c[2])) for c in cands[:-1]] == want, (tag, [(c[0], c[2]) for c in cands], want)
    for name, lst, src in cands[:-1]:
        assert lst == [acts[i] for i in src], (tag, name)
    name, lst, src = cands[-1]
    assert name == "K0" and all(isinstance(a, Release) for a in lst), tag
    assert sorted(int(a.lease_id) for a in lst) == sorted(L), tag
    for i, a in zip(src, lst):
        assert i is None or (acts[i] == a and isinstance(acts[i], Release)), (tag, i, a)
    for name, lst, _src in cands[1:]:
        assert not _names_unseen(lst, L, e["obs_r"]), (tag, name, lst)


def _check_prop_p(pol: _Probe, tag, st: Counter) -> None:
    """Proposition P at every E-mode slot at which T0gBound is in its bound form and S follows FB: K0 passes the
    guard's test, with no purchase or rent term, R_K0 = 0, G_K0 = Q(t) up to float summation and its stranding term at
    most the budget R(t - 1); and the candidate ladder (_check_ladder)."""
    for t, e in sorted(pol.log.items()):
        if "cands" not in e:
            continue
        _check_ladder(e, (tag, t))
        k = e["k0"]
        st["slots"] += 1
        if k["robust"] or not k["FB"]:
            st["k0_skip"] += 1
            continue
        st["k0_bound"] += 1
        assert k["form"] == "bound" and k["pE"] == 0.0 and k["rent"] == 0.0 and k["R"] == 0.0, (tag, t, k)
        assert abs(k["G"] - k["Q"]) <= 1e-12 * max(1.0, k["Q"]), (tag, t, k["G"], k["Q"])
        assert k["S"] <= k["budget"] + 1e-12 * max(1.0, k["budget"]), (tag, t, k["S"], k["budget"])
        assert k["a_hat"] + k["R"] <= k["rhs"] + GUARD_TOL * max(1.0, abs(k["rhs"])), (tag, t, k)
        st["k0_budget_pos"] += k["budget"] > 0 and k["S"] > 0
        st["executed:" + e["name"]] += 1


def _check_mapping(pol: _Probe, rec_in: _ObsRec, inst, tag, st: Counter) -> None:
    """The refusal mapping (§2.4 step 1) at every slot t + 1 after an E-mode slot t: after a slot executed as A_E(t)
    the inner receives the engine's results unchanged; after a projected slot it receives one result per action of
    A_E(t), at its index: the engine's result of the executed action (same action, ok, lease, replicas and reason)
    re-indexed, or ActionResult(index, action, False, None, (), 'guard') for a dropped one; a Release that the guard
    added has no result, releases a lease of obs that A_E(t) does not release, and the lease appears in obs.ended at
    t + 1 with cause 'release'."""
    Ds = inst.grid.slow_min
    for t, e in sorted(pol.log.items()):
        nxt = pol.log.get(t + 1)
        if e.get("mode") != "E" or "name" not in e or nxt is None or (t + 1) not in rec_in.results:
            continue
        acts = e["acts"]
        assert rec_in.acts[t] == acts, (tag, t)
        got, raw = rec_in.results[t + 1], nxt["results"]
        if e["name"] == "E":
            assert got == raw, (tag, t)
            st["identity"] += 1
            continue
        st["projected"] += 1
        assert [r.index for r in got] == list(range(len(acts))), (tag, t, [r.index for r in got])
        by = {r.index: r for r in raw}
        assert sorted(by) == list(range(len(e["executed"]))), (tag, t)
        used = set()
        for i, o in enumerate(e["src"]):
            r = by[i]
            if o is None:
                a = e["executed"][i]
                lid = int(a.lease_id)
                assert isinstance(a, Release) and r.ok and lid in e["obs_l"], (tag, t, a)
                assert not any(isinstance(b, Release) and int(b.lease_id) == lid for b in acts), (tag, t, a)
                assert (lid, t * Ds, "release") in nxt["ended"], (tag, t, lid, nxt["ended"])
                st["guard_releases"] += 1
                continue
            assert r.action == acts[o], (tag, t, i, o)
            assert got[o] == ActionResult(o, r.action, r.ok, r.lease_id, r.replica_ids, r.reason), (tag, t, o)
            used.add(o)
        for o, a in enumerate(acts):
            if o not in used:
                assert got[o] == ActionResult(o, a, False, None, (), "guard"), (tag, t, o, got[o])
                st["dropped:" + type(a).__name__] += 1


def _run(inst, model, inner, kw: dict, cfg=None):
    """A8P (_Probe) around `inner` wrapped in _ObsRec: (result, report, probe, recorder)."""
    rec_in = _ObsRec(inner)
    pol = _Probe(inner=rec_in, **kw)
    res = simulate(inst, pol, model, cfg or EngineConfig(), policy_seed=0)
    assert res.invariant_failures == [], res.invariant_failures[:3]
    return res, res.metrics["policy"], pol, rec_in


# ================================================================ parameters and the candidate ladder
def test_params():
    """A8P's parameters (§2.4; §5 P2 for allowance): Guarded.PARAMS with inner 'A9', project true and allowance
    'alg1'; inner ids PROJ_INNER_IDS = INNER_IDS and A9, while Guarded.PARAMS and INNER_IDS are unchanged; params()
    carries project, the inner id and the inner's resolved parameters, and allowance only when it is not 'alg1'
    (tests/test_online_lb.py tests 'lb'); inner_params reach the inner; project true needs test T0g; allowance 'lb'
    needs kappa None; PolicyError for bad values. The inner A9 is built from sublet.algos.a9 once that module exists
    (ModuleNotFoundError before)."""
    assert ProjectedGuarded.PARAMS == {**Guarded.PARAMS, "inner": "A9", "project": True, "allowance": "alg1"}
    assert ProjectedGuarded.PARAMS == {"inner": "A9", "inner_params": {}, "safe": "fb+pd", "S_rbar": "theory",
                                       "gamma": 1.0, "gamma_T11": G2, "test": "T0g", "wind_down": "auto",
                                       "reserve": True, "B0": "auto", "kappa": 10.0, "abort_at": None, "project": True,
                                       "allowance": "alg1"}
    assert Guarded.PARAMS["inner"] == "A7" and "project" not in Guarded.PARAMS
    assert ProjectedGuarded.INPUTS == Guarded.INPUTS == ("N_bound", "on_unavailable")
    assert INNER_IDS == ("A7", "A3", "A6", "BL1", "BL5") and PROJ_INNER_IDS == INNER_IDS + ("A9",)
    assert ProjectedGuarded.name == "A8P" and Guarded.name == "A8"
    pol = ProjectedGuarded(inner="BL1", safe="fb")
    p = pol.params()
    assert p["project"] is True and p["inner"] == "BL1" and pol.inner_id == "BL1" and "allowance" not in p
    assert p["inner_params"] == _inner("BL1").params() and p["test"] == "T0g" and pol.wd == "adaptive"
    pol = ProjectedGuarded(inner="BL5", inner_params={"use_current_slot": True}, N_bound=10, on_unavailable="refuse")
    assert pol.inner.params()["use_current_slot"] is True and pol.params()["inner_params"]["use_current_slot"] is True
    assert pol.on_unavailable == "refuse" and pol.N_bound == 10
    assert ProjectedGuarded(inner="BL1", safe="fb", project=False, test="T0").wd == "keep"
    for bad in (dict(inner="A2"), dict(inner="A8"), dict(project=1), dict(project="yes"), dict(test="T0"),
                dict(test="T1"), dict(foo=1), dict(inner_params=[1]), dict(safe="x"), dict(gamma=0),
                dict(on_unavailable="never"), dict(B0=-1), dict(allowance="x"), dict(allowance="lb"),
                dict(allowance="lb", kappa=10.0)):
        with pytest.raises(PolicyError):
            ProjectedGuarded(**{"inner": "BL1", "N_bound": 10, **bad})
    with pytest.raises(PolicyError):
        ProjectedGuarded(inner="BL1")                       # S_rbar = 'theory' with R in S needs N_bound
    if importlib.util.find_spec("sublet.algos.a9") is None:
        with pytest.raises(ModuleNotFoundError):
            ProjectedGuarded(safe="fb")
    else:
        pol = ProjectedGuarded(safe="fb")
        assert pol.inner_id == "A9" and type(pol.inner).__name__ == "NoticeCriticalRatio"


def _hand_obs():
    """A slot-0 observation of the toy with leases 3 (site L0) and 5 (site L1) and replicas 7 (on 3) and 8 (on 5)."""
    inst = toy_instance({})
    leases = {3: LeaseView(3, 0, 0, 1, 0, 0, 10, None, None, (7,)),
              5: LeaseView(5, 1, 0, 1, 0, 0, 10, None, None, (8,))}
    obs = _toy_obs(inst, leases)
    obs.replicas = {7: ReplicaView(7, 3, 0, "warm", 0, 0, 1.0, None), 8: ReplicaView(8, 5, 0, "warm", 0, 0, 1.0, None)}
    return inst, obs


def test_candidate_ladder_hand():
    """§2.4 step 3 on a hand-made list (hand oracle): five Buys interleaved with a Release, a Load, a SetAdmission and
    an Unload of objects of obs and with a Load, a Drain and a Release of objects that obs does not contain. A^- keeps
    the four actions on objects of obs, in order; P1 keeps the first 4, 2 and 1 Buys with A^-, in A_E(t)'s order; P0
    is A^-; K0 releases leases 3 (the inner's own Release, its index) and 5 (a guard Release). The prefix lengths for
    n_b = 1..8 Buys; a list without Buys whose actions all name objects of obs has no P0."""
    inst, obs = _hand_obs()
    pol = ProjectedGuarded(inner="BL1", safe="fb")
    b = [Buy(0, 0, 0, 1, tag=f"b{i}") for i in range(5)]
    acts = [Release(3), b[0], Load(5, 0), b[1], SetAdmission(7, 0.5), b[2], Load(99, 0), b[3], Unload(8),
            Drain(42, 10), b[4], Release(77)]
    got = [(n, s) for n, _l, s in pol.candidates(obs, acts)]
    assert got == [("E", list(range(12))), ("P1", [0, 1, 2, 3, 4, 5, 7, 8]), ("P1", [0, 1, 2, 3, 4, 8]),
                   ("P1", [0, 1, 2, 4, 8]), ("P0", [0, 2, 4, 8]), ("K0", [0, None])], got
    k0 = pol.candidates(obs, acts)[-1][1]
    assert k0 == [Release(3), Release(5)] and k0[0] is acts[0]
    assert [_p1_sizes(n) for n in range(1, 9)] == [[], [1], [2, 1], [3, 2, 1], [4, 2, 1], [5, 3, 1], [6, 3, 1],
                                                   [7, 4, 2, 1]]
    for nb in range(1, 9):
        c = pol.candidates(obs, [Buy(1, 0, 0, 1, tag=str(i)) for i in range(nb)])
        assert [x[0] for x in c] == ["E"] + ["P1"] * len(_p1_sizes(nb)) + ["P0", "K0"], nb
        assert [sum(isinstance(a, Buy) for a in x[1]) for x in c[1:-2]] == _p1_sizes(nb), nb
    assert [x[0] for x in pol.candidates(obs, [Release(5), SetAdmission(7, 0.0)])] == ["E", "K0"]
    assert [x[0] for x in pol.candidates(obs, [Unload(9)])] == ["E", "P0", "K0"]
    assert [x[0] for x in pol.candidates(obs, [])] == ["E", "K0"]
    assert pol.candidates(obs, [])[-1][2] == [None, None]


# ================================================================ identities with A8
def test_project_false_is_guarded():
    """project false gives Guarded's run bit for bit (§2.4): ledger, components, lease records and report (without
    A8P's added keys) equal to A8 around the same inner policy, on ms s3 (6 h) around BL1 and BL5 (and A7 once built)
    at Algorithm 1's defaults and at a constant allowance B0 = 0.5 (A8 around BL1 aborts at slot 0 there), and on
    _rich_instance around _RandomInner, _OwnListInner and _FastInner at small constant allowances with gamma in {0.5,
    1, G2} (natural aborts) and with a forced abort (abort_at). The added keys: project false, zero counts, every
    executed slot 'E'."""
    inst = _ms(3, 360)
    cases = []
    for inner in ("BL1", "BL5") + (("A7",) if HAVE_A7 else ()):
        for kw in ({}, {"B0": 0.5, "kappa": None}):
            cases.append((inst, LenderModel(), lambda inner=inner: inner, {"N_bound": _N(inst), **kw}, None))
    for v in range(4):
        rich = _rich_instance(3, v, bool(v % 2))
        for k, (make, gamma, B0, extra) in enumerate(((_RandomInner, 1.0, 0.3, {}), (_OwnListInner, G2, 1.0, {}),
                                                      (_FastInner, 0.5, 2.0, {}), (_RandomInner, 1.0, 1e12,
                                                                                   {"abort_at": 3 + v}))):
            mname = list(RICH_MODELS)[(v + k) % len(RICH_MODELS)]
            kw = {"safe": "fb", "gamma": gamma, "B0": B0, "kappa": None, **extra}
            cases.append((rich, LenderModel(**RICH_MODELS[mname]), lambda make=make, s=11 * v + k: make(s), kw,
                          EngineConfig(auto_drain=bool(k % 2))))
    n_abort = 0
    for inst_c, model, make, kw, cfg in cases:
        a = simulate(inst_c, Guarded(inner=make(), **kw), model, cfg or EngineConfig(), policy_seed=0)
        p = simulate(inst_c, ProjectedGuarded(inner=make(), project=False, **kw), model, cfg or EngineConfig(),
                     policy_seed=0)
        tag = (inst_c.name, kw, str(getattr(make(), "name", make())))
        _same_run(p, a, tag)
        rep = p.metrics["policy"]
        assert rep["project"] is False and rep["projection"] == ZERO and rep["dropped_fast"] == 0, tag
        n_ex = rep["t_a"] if rep["t_a"] is not None else inst_c.grid.T_slow
        assert rep["candidates"] == _e_rle(n_ex), (tag, rep["candidates"])
        n_abort += rep["t_a"] is not None
    assert n_abort >= 4


def test_no_projection_equals_a8():
    """A8P's report equals A8's for the same run when no slot before the abort is projected (§8.3). (a) No abort:
    allowance 1e12 on ms s3 (6 h) around BL1 and BL5 (policy seeds 0 and 1): every slot executes A_E(t). (b) Natural
    aborts with no projected slot before: _RandomInner on _rich_instance (variants 0, 4, 5) under the lenders adaptive,
    safe_site and trace, gamma in {0.25, 0.5, 0.8} (below 1, outside Proposition P) and constant B0 in {0, 0.5, 2}:
    each such run aborts at A8's slot and equals A8's run, at slot 0 and later. At every abort report()['guard']
    ['forced'] and at_abort['forced'] are false (the failing step of A_E(t) is recorded unforced)."""
    inst = _ms(3, 360)
    for inner in ("BL1", "BL5"):
        for s in (0, 1):
            kw = {"N_bound": _N(inst), **NO_ABORT}
            a = simulate(inst, Guarded(inner=inner, **kw), LenderModel(), policy_seed=s)
            p = simulate(inst, ProjectedGuarded(inner=inner, **kw), LenderModel(), policy_seed=s)
            _same_run(p, a, (inner, s))
            rep = p.metrics["policy"]
            assert rep["t_a"] is None and rep["project"] is True and rep["projection"] == ZERO
            assert rep["candidates"] == _e_rle(inst.grid.T_slow)
    st = Counter()
    for v in (0, 4, 5):
        for i, (mname, lm) in enumerate(F4_MODELS.items()):
            rich = _rich_instance(9, v, bool((v + i) % 2))
            for gamma in (0.25, 0.5, 0.8):
                for B0 in (0.0, 0.5, 2.0):
                    kw = {"test": "T0g", "safe": "fb", "gamma": gamma, "B0": B0, "kappa": None}
                    a = simulate(rich, Guarded(inner=_RandomInner(97 + 13 * v + i), **kw), LenderModel(**lm),
                                 policy_seed=0)
                    p = simulate(rich, ProjectedGuarded(inner=_RandomInner(97 + 13 * v + i), **kw), LenderModel(**lm),
                                 policy_seed=0)
                    tag = (v, mname, gamma, B0)
                    rep = p.metrics["policy"]
                    assert p.invariant_failures == [], tag
                    if rep["t_a"] is not None:
                        st["abort"] += 1
                        assert rep["guard"]["forced"] is False and rep["at_abort"]["forced"] is False, tag
                        assert rep["guard"]["t_a"] == rep["t_a"], tag
                    if rep["projection"]["slots"] == 0:
                        _same_run(p, a, tag)
                        if rep["t_a"] is not None:
                            st["equal_abort"] += 1
                            st["equal_abort_later"] += rep["t_a"] > 0
                    else:
                        st["projected"] += 1
    assert st["equal_abort"] > 0 and st["equal_abort_later"] > 0 and st["projected"] > 0, st


# ================================================================ Remark R (C3 §9, Definition R and Remark R)
def _lad(o, A: list) -> list:
    """Lad(o, A) of Definition R (R1), written from the definition (not ProjectedGuarded.candidates): [(name, list,
    source map)] in the order E, P1 (n' decreasing), P0, K0; source None for a Release that K0 adds."""
    L = {int(x) for x in o.leases}
    reps = {int(r) for r, rv in o.replicas.items() if int(rv.lease_id) in L}

    def names_obs(a):
        if isinstance(a, (Release, Load)):
            return int(a.lease_id) in L
        if isinstance(a, (Unload, SetAdmission, Drain)):
            return int(a.replica_id) in reps
        return False
    ib = [i for i, a in enumerate(A) if isinstance(a, Buy)]
    im = [i for i, a in enumerate(A) if not isinstance(a, Buy) and names_obs(a)]
    out = [("E", list(A), list(range(len(A))))]
    nb = len(ib)
    if nb >= 2:
        for n in sorted({nb - 1, nb // 2, nb // 4, 1} - {0, nb}, reverse=True):
            idx = sorted(ib[:n] + im)
            out.append(("P1", [A[i] for i in idx], idx))
    if len(im) < len(A):
        out.append(("P0", [A[i] for i in im], list(im)))
    first = {}
    for i, a in enumerate(A):
        if isinstance(a, Release) and int(a.lease_id) in L:
            first.setdefault(int(a.lease_id), i)
    k0 = [(A[first[lid]], first[lid]) if lid in first else (Release(lid), None) for lid in sorted(L)]
    out.append(("K0", [a for a, _s in k0], [s for _a, s in k0]))
    return out


class _Proj(Policy):
    """Proj_theta(E) of Definition R (R3), written from the definition: its own SafeExpert S' (from an identical copy
    of the policy generator) and T0gBound T', Ratchet's float conversions, A8P's allowance rule; it proposes the first
    list of Lad(o, A_E(t)) that passes, or A_E(t) when none passes or from abort_at on. Records its proposals.
    allowance 'alg1' (the default): B(t) = B0 (kappa None) or min{B0, kappa B_on(t)} from S'; 'lb' (kappa must be
    None): B(t) = min{W_k(t), LB'(t)} of its own online_lb.OnlineLB, built in reset from the view and stepped at the top
    of every act call (B0 unused). Other guard keywords (wind_down, test, ...) do not enter Proj(E) and are ignored."""
    wants_fast = False

    def __init__(self, E, *, safe="fb+pd", S_rbar="theory", N_bound=None, gamma=1.0, gamma_T11=G2, B0="auto",
                 kappa=10.0, reserve=True, abort_at=None, on_unavailable=None, allowance="alg1", **_other):
        if allowance not in ("alg1", "lb"):
            raise ValueError(f"_Proj: allowance must be 'alg1' or 'lb', got {allowance!r}")
        if allowance == "lb" and kappa is not None:
            raise ValueError(f"_Proj: allowance 'lb' needs kappa None, got {kappa!r}")
        self.E, self.name = E, getattr(E, "name", type(E).__name__)
        self.th = dict(safe=safe, S_rbar=S_rbar, N_bound=N_bound, gamma=gamma, gamma_T11=gamma_T11, B0=B0,
                       kappa=kappa, reserve=bool(reserve), abort_at=abort_at, on_unavailable=on_unavailable,
                       allowance=allowance)

    def reset(self, view, rng):
        super().reset(view, rng)
        th = self.th
        self.E.reset(view, copy.deepcopy(rng))
        self.wants_fast = bool(getattr(self.E, "wants_fast", False))
        self.S = guard.SafeExpert(view, copy.deepcopy(rng), safe=th["safe"], rbar=th["S_rbar"],
                                  N_bound=None if th["safe"] == "fb" else th["N_bound"],
                                  gamma_T11=float(th["gamma_T11"]))
        self.T = guard.T0gBound(view, robust=self.wants_fast, on_unavailable=th["on_unavailable"])
        self.g = float(th["gamma"])
        self.olb = online_lb.OnlineLB(view) if th["allowance"] == "lb" else None
        if self.olb is not None:
            self.B0 = None
        else:
            self.B0 = float(guard.b0_auto(view)) if th["B0"] == "auto" else float(th["B0"])
        self.kap = None if th["kappa"] is None else float(th["kappa"])
        self.mu, self.f_ok, self.f_rel = None, set(), set()
        self.projection, self.cands, self.dropped_fast = dict(ZERO), [], 0
        self.log: dict[int, tuple] = {}

    def _rho(self, results):
        src, dropped = self.mu
        out = [ActionResult(src[r.index], r.action, r.ok, r.lease_id, r.replica_ids, r.reason)
               for r in results if 0 <= r.index < len(src) and src[r.index] is not None]
        out += [ActionResult(i, a, False, None, (), "guard") for i, a in dropped]
        return sorted(out, key=lambda r: r.index)

    def act(self, o):
        th, t = self.th, int(o.t)
        if self.olb is not None:                                             # 'lb': B(t) from o.demand, first
            self.olb.step(o)
        oe = guard.inner_obs(o)                                              # (i)
        if self.mu is not None:
            oe.results = self._rho(o.results)
        A = list(self.E.act(oe))
        self.S.step(o)                                                       # (ii)
        if self.olb is not None:
            B = self.olb.B
        else:
            B = self.B0 if self.kap is None else min(self.B0, self.kap * float(self.S.B_on))
        Q = self.S.fb_inc
        self.T.begin(o)
        rhs = self.g * float(self.S.C_S) + float(B)
        lim = rhs + GUARD_TOL * max(1.0, abs(rhs))
        pick = None
        if th["abort_at"] is not None and t >= int(th["abort_at"]):          # (iii), forced branch
            slot_terms(self.view, o, A)
            ev = self.T.evaluate(o, A, Q)
        else:
            ev = None
            for name, Y, src in _lad(o, A):
                p, rent = slot_terms(self.view, o, Y)
                e = self.T.evaluate(o, Y, Q)
                ev = e if ev is None else ev                                 # no pass: the first evaluation, A's
                R = e["reserve"] if th["reserve"] else 0.0
                if float(o.cost_so_far) + float(p) + float(rent) + float(e["G"] + e["S"]) + R <= lim:
                    pick, ev = (name, Y, src), e
                    break
        self.T.commit(ev)                                                    # (iv)
        self.mu = None
        X = A if pick is None else pick[1]
        self.log[t] = (None if pick is None else pick[0], list(A), list(X))
        if pick is not None:
            name, _Y, src = pick
            self.cands.append(name)
            if name != "E":
                used = {i for i in src if i is not None}
                dr = [(i, a) for i, a in enumerate(A) if i not in used]
                nb = sum(1 for _i, a in dr if isinstance(a, Buy))
                pr = self.projection
                pr["slots"] += 1
                pr[name] += 1
                pr["dropped_buys"] += nb
                pr["dropped_other"] += len(dr) - nb
                pr["guard_releases"] += sum(1 for i in src if i is None)
                self.mu = (list(src), dr)
                if self.wants_fast:
                    self.f_rel = {int(a.lease_id) for a in X if isinstance(a, Release)}
                    unl = {int(a.replica_id) for a in X if isinstance(a, Unload)}
                    self.f_ok = {int(r) for r, rv in o.replicas.items() if int(rv.lease_id) in o.leases
                                 and int(rv.lease_id) not in self.f_rel and int(r) not in unl}
        return list(X)                                                       # (v)

    def on_fast(self, f):
        if self.mu is None:
            return self.E.on_fast(f)
        if f.results:
            for r in f.results:
                if r.ok and (isinstance(r.action, Buy)
                             or (isinstance(r.action, Load) and int(r.lease_id) not in self.f_rel)):
                    self.f_ok.update(int(x) for x in r.replica_ids)
            f = dataclasses.replace(f, results=self._rho(f.results))
        acts = list(self.E.on_fast(f) or [])
        keep = [a for a in acts if not isinstance(a, (Drain, SetAdmission)) or int(a.replica_id) in self.f_ok]
        self.dropped_fast += len(acts) - len(keep)
        return keep

    def report(self):
        r = getattr(self.E, "report", None)
        return r() if callable(r) else {}


class _Lists(Policy):
    """Passes a policy through and records the lists it returns to the engine (slow and fast slots)."""

    def __init__(self, pol):
        self.pol, self.slow, self.fast = pol, [], []

    def reset(self, view, rng):
        self.pol.reset(view, rng)
        self.wants_fast = bool(getattr(self.pol, "wants_fast", False))

    def act(self, obs):
        out = self.pol.act(obs)
        self.slow.append((int(obs.t), list(out)))
        return out

    def on_fast(self, f):
        out = self.pol.on_fast(f)
        self.fast.append((int(f.f), list(out or [])))
        return out

    def report(self):
        return self.pol.report()


class _ResultsInner(_FastInner):
    """The inner policy of test_remark_r_coverage (audit addendum of step P6, REMARK_R-F4): _FastInner's lists, with
    draws that depend on every field and on the order of the results it receives. Before it acts, in act and (fast
    true) at the first fast slot of a slot, it draws crc32(repr(results)) mod 4 numbers from its generator, so a
    result that differs in its index, action, ok, lease, replicas or reason, or a different order, changes its later
    lists. At each such call it checks the identity that Step 3 of Remark R's proof uses: one result per index of its
    last list, each carrying the action object it returned at that index. At a share `many` of its slots it appends a
    block of 8 to 12 Buys of one site, contract and LLM (n_b >= 8, so P1's floor(n_b / 4) rung is a list of its own),
    and at a fifth of its slots with a Buy it repeats a Buy object. With fast false it never acts in on_fast
    (wants_fast false, T0g in its bound form). With fast true it also unloads an observed replica at 30% of its slots
    (an action that P1 and P0 keep), acts in on_fast as _FastInner does (never on a replica that its own list
    releases or unloads) and, at the first fast slot of a slot whose results carry a 'guard' refusal (a projected
    slot), at half of these slots also names a replica that its own list unloaded with an ok result. R3's filter must
    drop that action: the replica no longer exists, and the engine would raise ActionError. Counters in stats:
    slow_guard and fast_guard (calls whose results carry a 'guard' refusal), slow_order and fast_order (of these,
    those with a refusal at an index below a kept result's, where the order of the remapped results matters), many,
    repeat, unloaded_named."""
    name = "results"

    def __init__(self, seed: int, fast: bool = False, many: float = 0.0):
        super().__init__(seed)
        self.fast, self.many = bool(fast), float(many)
        self.wants_fast = self.fast

    def reset(self, view, rng):
        super().reset(view, rng)
        self.last = None
        self.stats = Counter()

    def _see(self, results, where: str) -> None:
        """Step 3's identity check, the draws that depend on the results, and the counters."""
        if self.last is not None:
            assert sorted(r.index for r in results) == list(range(len(self.last))), (where, results, self.last)
            assert all(r.action is self.last[r.index] for r in results), (where, results)
        for _ in range(zlib.crc32(repr(list(results)).encode()) % 4):
            self.r.random()
        drop = [r.index for r in results if r.reason == "guard"]
        if drop:
            kept = [r.index for r in results if r.reason != "guard"]
            self.stats[where + "_guard"] += 1
            self.stats[where + "_order"] += bool(kept) and min(drop) < max(kept)

    def act(self, obs):
        self._see(obs.results, "slow")
        acts = list(super().act(obs))
        r, view = self.r, self.view
        if self.fast and r.random() < 0.3:                  # an Unload of an observed replica, kept by P1 and P0
            gone_l = {int(a.lease_id) for a in acts if isinstance(a, Release)}
            gone_r = {int(a.replica_id) for a in acts if isinstance(a, Unload)}
            reps = sorted(int(x) for x, rv in obs.replicas.items() if rv.lease_id in obs.leases
                          and int(rv.lease_id) not in gone_l and int(x) not in gone_r)
            if reps:
                rid = int(r.choice(reps))
                acts.append(Unload(rid))
                self.fast_ok = [x for x in self.fast_ok if x != rid]
        if self.many and r.random() < self.many:
            l = int(r.integers(0, len(view.sites)))
            k, j = int(sorted(view.sites[l].menu)[0]), int(r.integers(0, len(view.llms)))
            acts += [Buy(l, k, j, 1, tag=f"m{i}") for i in range(int(r.integers(8, 13)))]
            self.stats["many"] += 1
        buys = [a for a in acts if isinstance(a, Buy)]
        if buys and r.random() < 0.2:
            acts.insert(int(r.integers(0, len(acts) + 1)), buys[0])
            self.stats["repeat"] += 1
        self.last = list(acts)
        return acts

    def on_fast(self, obs):
        extra = []
        if obs.results:
            self._see(obs.results, "fast")
            unl = []
            if any(x.reason == "guard" for x in obs.results):
                unl = sorted(int(x.action.replica_id) for x in obs.results if x.ok and isinstance(x.action, Unload))
            if unl and self.r.random() < 0.5:
                extra = [SetAdmission(int(self.r.choice(unl)), 0.5)]
                self.stats["unloaded_named"] += 1
        return extra + list(super().on_fast(obs))


def _remark_r_compare(inst, model, make_inner, kw: dict, cfg, seed: int, tag, st: Counter) -> None:
    """A8P around E against A8 around Proj(E) (Remark R (a), (b)): equal lists at every slow and fast slot, equal
    ledger and lease records, equal reports once A8P's added keys are left out (Remark R(a)'s four at Algorithm 1's
    allowance; with 'lb' also allowance and online_lb), those keys equal to Proj(E)'s counters; at an abort, Proj(E)
    proposed A_E(t_a) and both steps are unforced unless abort_at forces them. A run without an abort is also compared
    with Proj(E) run alone ("What is lost": G2(a) with Proj(E) in place of E). Coverage counters in st: runs, projected
    slots per candidate, dropped fast actions, executed P1 rungs with floor(n_b / 4) Buys (n_b >= 8), aborts (forced
    or not, after a projected slot, right after one, with an inner policy that uses on_fast) and _ResultsInner's
    counters ('inner:' keys).

    At allowance 'lb' (kw holds allowance 'lb' and kappa None) A8 is ProjectedGuarded(inner=Proj(E), project=False,
    allowance='lb', kappa=None), since Guarded has no parameter 'allowance': with project false every slot is
    Guarded.act and Guarded.on_fast, bit for bit (test_project_false_is_guarded), and the only difference from Guarded
    is the allowance that Guarded.act reads, B(t) = min{W_k(t), LB'(t)} of the guard's own OnlineLB (_LBRatchet),
    which is the rule of A8P's side and of Proj(E)'s ('lb'): Remark R holds for any allowance that is nonnegative,
    nondecreasing and known at slot t, provided both guards use the same one, so this is A8 for its purpose. Both
    reports then carry A8P's keys: they are compared with those keys left out, the A8 side's keys are A8's at project
    false (project false, no projected slot, every executed slot 'E'), and allowance, online_lb and B0 (None) agree."""
    lb = kw.get("allowance", "alg1") == "lb"
    proj = _Proj(make_inner(), **kw)
    a8 = ProjectedGuarded(inner=proj, project=False, **kw) if lb else Guarded(inner=proj, **kw)
    rp, ra = _Lists(ProjectedGuarded(inner=make_inner(), **kw)), _Lists(a8)
    res_p = simulate(inst, rp, model, cfg, policy_seed=seed)
    res_a = simulate(inst, ra, model, cfg, policy_seed=seed)
    assert res_p.invariant_failures == res_a.invariant_failures, tag
    _same_ledger(res_p, res_a, str(tag))
    assert rp.slow == ra.slow and rp.fast == ra.fast, (tag, "lists")
    rep_p, rep_a = res_p.metrics["policy"], res_a.metrics["policy"]
    if lb:
        assert _canon(_as_a8(rep_p)) == _canon(_as_a8(rep_a)), (tag, "report")
        n_ex = rep_a["t_a"] if rep_a["t_a"] is not None else inst.grid.T_slow
        assert rep_a["project"] is False and rep_a["projection"] == ZERO and rep_a["dropped_fast"] == 0, tag
        assert rep_a["candidates"] == _e_rle(n_ex), (tag, rep_a["candidates"])
        assert rep_p["allowance"] == rep_a["allowance"] == "lb" and rep_p["online_lb"] == rep_a["online_lb"], tag
        assert rep_p["B0"] is None and rep_a["guard"]["B0"] is None and rep_p["kappa"] is None, tag
        assert proj.olb.t == (inst.grid.T_slow - 1 if rep_p["t_a"] is None else rep_p["t_a"]), (tag, proj.olb.t)
        assert np.array_equal(proj.olb.B_series, rep_p["safe"]["B_curve"][:len(proj.olb.B_series)]), tag
    else:
        assert "allowance" not in rep_p and "allowance" not in rep_a, tag
        assert _canon(_as_a8(rep_p)) == _canon(rep_a), (tag, "report")
    rle: list[list] = []
    for t, w in enumerate(proj.cands):
        if rle and rle[-1][0] == w:
            rle[-1][2] += 1
        else:
            rle.append([w, t, 1])
    assert rep_p["projection"] == proj.projection and rep_p["candidates"] == rle, tag
    assert rep_p["dropped_fast"] == proj.dropped_fast, tag
    st["runs"] += 1
    st["projected"] += rep_p["projection"]["slots"]
    for k in ("P1", "P0", "K0"):
        st[k] += rep_p["projection"][k]
    st["dropped_fast"] += rep_p["dropped_fast"]
    for name, A, X in proj.log.values():                                    # P1's floor(n_b / 4) rung executed
        nb = sum(isinstance(a, Buy) for a in A)
        st["P1_quarter"] += name == "P1" and nb >= 8 and sum(isinstance(a, Buy) for a in X) == nb // 4
    if isinstance(proj.E, _ResultsInner):                                   # its counters
        for k, x in proj.E.stats.items():
            st["inner:" + k] += x
    if rep_p["t_a"] is None:
        alone = _Lists(_Proj(make_inner(), **kw))
        res_s = simulate(inst, alone, model, cfg, policy_seed=seed)
        _same_ledger(res_s, res_p, str(tag) + " alone")
        assert alone.slow == rp.slow and alone.fast == rp.fast, (tag, "alone")
        st["alone_equal"] += 1
        return
    ta = int(rep_p["t_a"])
    forced = kw.get("abort_at") is not None and ta >= int(kw["abort_at"])
    assert rep_p["guard"]["forced"] is forced and rep_a["guard"]["forced"] is forced, tag
    name, A, X = proj.log[ta]
    assert name is None and X == A, (tag, "Proj(E) at t_a", name)
    st["abort_forced" if forced else "abort"] += 1
    st["abort_after_projection"] += int(any(w != "E" for w in proj.cands))
    right_after = ta >= 1 and proj.log[ta - 1][0] not in (None, "E")        # slot t_a - 1 was projected
    st[("abort_forced" if forced else "abort") + "_right_after_projection"] += right_after
    st["fast_abort_right_after_projection"] += right_after and proj.wants_fast


def test_remark_r_identity():
    """Remark R (C3 §9; design/sublet_v2.md §2.6), its code statement (f): A8P around E and A8 around Proj(E) of
    Definition R3 (_Proj, written from the definition) give equal lists at every slow and fast slot, equal ledgers,
    lease records and reports (A8P's report with its added keys left out; those keys equal Proj(E)'s counters),
    and abort at the same slot with Proj(E) proposing A_E(t_a); a run without an abort equals Proj(E) alone. Inner
    policies: _RandomInner and _OwnListInner (every slow-slot action type) on _rich_instance under the eight lender
    models of P_MODELS with the option passed under 'refuse' or not, safe 'fb' or 'fb+pd', gamma in {1, G2, 0.5,
    0.25}, constant, zero and capped allowances, abort_at, wind-down 'release' and auto_drain; _FastInner (on_fast);
    BL1 and BL5 at policy seeds 0 and 1; A9 on ms s3; and from_core exports of the core families with BL5 and a random
    inner restricted to Buys and Releases, under oblivious and adaptive lenders (92 runs at Algorithm 1's allowances).
    At A8P's allowance 'lb' (kappa None; A8 is A8P at project false, see _remark_r_compare, and Proj(E) uses its own
    OnlineLB): the random inners on _rich_instance variants 1 and 4 under the eight models of P_MODELS (gamma, safe,
    abort_at, wind-down and auto_drain varied as above), _FastInner under ROBUST_MODELS, BL1 and BL5 under 'refuse',
    and A9 on ms s3 under trace and iid_step, that is Sublet (24 runs). Coverage, at both allowances: projected slots
    of every candidate, unforced and forced aborts and runs without an abort; at Algorithm 1's also aborts after a
    projected slot."""
    from fixtures import upper_case
    from test_guard import _core_inst

    from sublet.algos.a9 import NoticeCriticalRatio
    st = Counter()
    allows = ({"B0": 0.3, "kappa": None}, {"B0": 3.0, "kappa": None}, {"B0": "auto", "kappa": 10.0},
              {"B0": 0.0, "kappa": None})
    k = 0
    for v in (0, 3, 6):                                                      # random inners
        for i, mname in enumerate(P_MODELS):
            for make in (_RandomInner, _OwnListInner):
                lm = P_MODELS[mname]
                inst = _rich_instance(5 + v, v, bool(v % 2))
                onu = "refuse" if lm.get("on_unavailable") == "refuse" else (None if k % 3 else "sell")
                kw = {"safe": "fb" if k % 4 else "fb+pd", "gamma": (1.0, G2, 0.5, 0.25)[k % 4],
                      "on_unavailable": onu, **allows[(v + i) % 4]}
                if kw["safe"] != "fb":
                    kw["N_bound"] = _N(inst)
                if k % 7 == 3:
                    kw["abort_at"] = 2 + v
                if k % 5 == 1:
                    kw["wind_down"] = "release"
                _remark_r_compare(inst, LenderModel(**lm), lambda s=17 * v + 3 + i, mk=make: mk(s), kw,
                                  EngineConfig(auto_drain=bool((v + i) % 2)), 0, ("random", v, mname, make.__name__),
                                  st)
                k += 1
    for i, (mname, lm) in enumerate(ROBUST_MODELS.items()):                  # on_fast (C1 fails)
        inst = _rich_instance(2, 0, bool(i % 2))
        for B0 in (0.5, 40.0):
            kw = {"safe": "fb", "gamma": 1.0, "B0": B0, "kappa": None,
                  "on_unavailable": "refuse" if mname.startswith("refuse") else None}
            _remark_r_compare(inst, LenderModel(**lm), lambda s=i + 5: _FastInner(s), kw, EngineConfig(), 0,
                              ("fast", mname, B0), st)
    inst = _rich_instance(0, 0, False)                                       # baselines
    for inner in ("BL1", "BL5"):
        for mname, lm in (("eager", {"schedule": "eager"}),
                          ("refuse", {"schedule": "trace", "on_unavailable": "refuse"})):
            onu = "refuse" if mname == "refuse" else "sell"
            for kw in ({"N_bound": _N(inst), "on_unavailable": onu},
                       {"safe": "fb", "B0": 0.2, "kappa": None, "on_unavailable": onu}):
                for seed in (0, 1):
                    _remark_r_compare(inst, LenderModel(**lm), lambda inner=inner: _inner(inner), kw, EngineConfig(),
                                      seed, ("bl", inner, mname, kw.get("B0"), seed), st)
    ms = _ms(3, 360)                                                         # A9
    for lm in ({"schedule": "trace"}, {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.3}}):
        for kw in ({"N_bound": _N(ms), "on_unavailable": "sell"},
                   {"safe": "fb", "B0": 0.0, "kappa": None, "gamma": 0.5, "on_unavailable": "sell"}):
            _remark_r_compare(ms, LenderModel(**lm), NoticeCriticalRatio, kw, EngineConfig(), 0,
                              ("a9", lm["schedule"], kw.get("B0")), st)

    class _CoreRandom(_RandomInner):
        name = "core_random"

        def act(self, obs):
            return [a for a in super().act(obs) if isinstance(a, (Buy, Release))]
    for fam, seed in (("rand", 0), ("spiky", 2)):                           # core exports
        I = upper_case(fam, seed)
        for sched in ("oblivious", "adaptive"):
            cinst, model = _core_inst(I, sched, seed)
            for mk in (lambda: _inner("BL5"), lambda s=seed: _CoreRandom(31 + s)):
                for allow in ({"B0": "auto", "kappa": 10.0}, {"B0": 0.0, "kappa": None, "gamma": 0.5}):
                    kw = {"safe": "fb+pd", "S_rbar": "theory", "N_bound": _N(cinst), **allow}
                    _remark_r_compare(cinst, model, mk, kw, EngineConfig(), 0, ("core", fam, sched, allow["B0"]), st)
    assert st["runs"] == 92, st
    for key in ("P1", "P0", "K0", "abort", "abort_forced", "abort_after_projection", "alone_equal"):
        assert st[key] > 0, (key, st)
    sl = Counter()                                                           # A8P's allowance 'lb' (§5 P2)
    lbk = {"allowance": "lb", "kappa": None}
    k = 0
    for v in (1, 4):                                                         # random inners
        for i, mname in enumerate(P_MODELS):
            lm = P_MODELS[mname]
            make = (_RandomInner, _OwnListInner)[(v + i) % 2]
            inst = _rich_instance(5 + v, v, bool(v % 2))
            onu = "refuse" if lm.get("on_unavailable") == "refuse" else (None if k % 3 else "sell")
            kw = {"safe": "fb" if k % 4 else "fb+pd", "gamma": (1.0, G2, 0.5, 0.25)[k % 4], "on_unavailable": onu,
                  **lbk}
            if kw["safe"] != "fb":
                kw["N_bound"] = _N(inst)
            if k % 7 == 1:                                                   # gamma >= 1: no natural abort first
                kw["abort_at"] = 2 + v
            if k % 5 == 1:
                kw["wind_down"] = "release"
            _remark_r_compare(inst, LenderModel(**lm), lambda s=19 * v + 5 + i, mk=make: mk(s), kw,
                              EngineConfig(auto_drain=bool((v + i) % 2)), 0, ("lb:random", v, mname, make.__name__),
                              sl)
            k += 1
    for i, (mname, lm) in enumerate(ROBUST_MODELS.items()):                  # on_fast (C1 fails)
        inst = _rich_instance(2, 1, bool(i % 2))
        kw = {"safe": "fb", "gamma": 1.0, "on_unavailable": "refuse" if mname.startswith("refuse") else None, **lbk}
        _remark_r_compare(inst, LenderModel(**lm), lambda s=i + 9: _FastInner(s), kw, EngineConfig(), 0,
                          ("lb:fast", mname), sl)
    inst = _rich_instance(0, 0, False)                                       # baselines
    for inner in ("BL1", "BL5"):
        kw = {"safe": "fb", "on_unavailable": "refuse", **lbk}
        _remark_r_compare(inst, LenderModel(schedule="trace", on_unavailable="refuse"),
                          lambda inner=inner: _inner(inner), kw, EngineConfig(), 1, ("lb:bl", inner), sl)
    for lm in ({"schedule": "trace"}, {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.3}}):   # A9: Sublet
        kw = {"N_bound": _N(ms), "on_unavailable": "sell", **lbk}
        _remark_r_compare(ms, LenderModel(**lm), NoticeCriticalRatio, kw, EngineConfig(), 0, ("lb:a9", lm["schedule"]),
                          sl)
    assert sl["runs"] == 16 + len(ROBUST_MODELS) + 4 == 24, sl
    for key in ("P1", "P0", "K0", "abort", "abort_forced", "alone_equal"):
        assert sl[key] > 0, ("lb", key, sl)


def test_remark_r_coverage():
    """Remark R(f)'s identity check (_remark_r_compare, as in test_remark_r_identity) on the paths of R1-R3 that
    test_remark_r_identity's grid leaves unobserved (audit addendum of step P6, REMARK_R-F4; code/sim/audit/
    x15_mutations.py records which mutations of ProjectedGuarded this test and the whole file catch), around
    _ResultsInner, whose draws depend on every field and on the order of the results it receives. (a) Without on_fast
    (T0g in its bound form), with blocks of 8 to 12 Buys at 30% of its slots: _rich_instance variants 0-7 under the
    eight lender models of P_MODELS, constant, capped and 'lb' allowances, gamma in {1, G2, 0.5}, with abort_at,
    wind-down 'release', safe 'fb+pd', auto_drain and policy seeds 0 and 1 varied (64 runs). (b) With on_fast (T0g in
    its robust form), blocks of Buys at 40% of its slots and an Unload of an observed replica at 30%: variants 0-7
    under the four lender models of ROBUST_MODELS, constant allowances 40 and 100 USD (at which robust slots pass both
    with and without projection) and gamma in {1, 1.7}, with abort_at in a third of the runs (128 runs). Coverage: in
    (a) and (b) the inner receives remapped results with 'guard' refusals at slow slots, also with a refusal at an
    index below a kept result's (where the order of R2's sort matters), every candidate is executed, P1's floor(n_b /
    4) rung among them (n_b >= 8), and runs end without an abort, with a natural abort and with a forced abort right
    after a projected slot; in (b) the inner receives remapped results at the first fast slot of a projected slot
    (also with a refusal below a kept result's index), R3's filter drops fast actions, among them actions on
    replicas that the executed list unloaded, and an abort (after which no remapping may remain) follows right after
    a projected slot. About 30 s."""
    st, sf = Counter(), Counter()
    allows = ({"B0": 0.3, "kappa": None}, {"B0": 3.0, "kappa": None}, {"B0": "auto", "kappa": 10.0},
              {"B0": 1.0, "kappa": None}, {"allowance": "lb", "kappa": None})
    k = 0
    for v in range(8):                                                       # (a) without on_fast
        for i, mname in enumerate(P_MODELS):
            lm = P_MODELS[mname]
            inst = _rich_instance(21 + v, v, bool((v + i) % 2))
            onu = "refuse" if lm.get("on_unavailable") == "refuse" else (None if k % 3 else "sell")
            kw = {"safe": "fb" if k % 3 else "fb+pd", "gamma": (1.0, G2, 1.0, 0.5)[k % 4], "on_unavailable": onu,
                  **allows[(v + i) % 5]}
            if kw["safe"] != "fb":
                kw["N_bound"] = _N(inst)
            if k % 6 == 4:
                kw["abort_at"] = 1 + k % 5
            if k % 4 == 1:
                kw["wind_down"] = "release"
            _remark_r_compare(inst, LenderModel(**lm), lambda s=101 + 7 * v + i: _ResultsInner(s, many=0.3), kw,
                              EngineConfig(auto_drain=bool(k % 2)), k % 2, ("cov", v, mname), st)
            k += 1
    k = 0
    for B0 in (40.0, 100.0):                                                 # (b) with on_fast
        for gamma in (1.0, 1.7):
            for v in range(8):
                for i, (mname, lm) in enumerate(ROBUST_MODELS.items()):
                    inst = _rich_instance(31 + v, v, bool((v + i) % 2))
                    kw = {"safe": "fb", "gamma": gamma, "B0": B0, "kappa": None,
                          "on_unavailable": "refuse" if mname.startswith("refuse") else None}
                    if k % 3 == 2:
                        kw["abort_at"] = 2 + k % 9
                    _remark_r_compare(inst, LenderModel(**lm),
                                      lambda s=31 + v + i: _ResultsInner(s, fast=True, many=0.4), kw,
                                      EngineConfig(auto_drain=bool(v % 2)), 0, ("cov:fast", B0, gamma, v, mname), sf)
                    k += 1
    assert st["runs"] == 64 and sf["runs"] == 128, (st, sf)
    for c in (st, sf):
        for key in ("P1", "P0", "K0", "P1_quarter", "alone_equal", "abort", "abort_forced",
                    "abort_right_after_projection", "abort_forced_right_after_projection", "inner:slow_guard",
                    "inner:slow_order", "inner:many", "inner:repeat"):
            assert c[key] > 0, (key, c)
    for key in ("inner:fast_guard", "inner:fast_order", "dropped_fast", "inner:unloaded_named",
                "fast_abort_right_after_projection"):
        assert sf[key] > 0, (key, sf)


# ================================================================ Proposition P, the envelope, the refusal mapping
def _p_cases(lb: bool = True):
    """(seed, variant, model, inner, allowance, gamma, auto_drain) of the Proposition P runs: _rich_instance variants
    0-7 (the time grids of _RICH and _RICH_EXTRA: notice 0, phi = 1, a fast slot that does not divide the notice), the
    eight lender models of P_MODELS, _RandomInner and _OwnListInner, Algorithm 1's allowances of P_ALLOWANCES[:3] and
    gamma in {1, G2} alternating (128 runs, first); with lb true then the same 128 cases at A8P's allowance 'lb' (P_LB,
    kappa None; 256 runs in all)."""
    out = []
    for allow in (None, P_LB) if lb else (None,):
        for v in range(8):
            for i, mname in enumerate(P_MODELS):
                for k, make in enumerate((_RandomInner, _OwnListInner)):
                    out.append((5, v, mname, make, P_ALLOWANCES[(v + i + k) % 3] if allow is None else allow,
                                (1.0, G2)[(v + i + k) % 2], bool((v + i) % 2)))
    return out


def test_proposition_p_quick():
    """Proposition P with S on FB (§2.6, §8.3), numerically: A8P (safe 'fb', test T0g with the reserve) around
    _RandomInner and _OwnListInner (every action type, Loads and actions on objects of the inner's own list included)
    on _rich_instance (every stranding coefficient positive), 256 runs (_p_cases): 128 at Algorithm 1's allowances
    (constant and capped) and the same 128 at A8P's allowance 'lb' (B = min{W_k, LB'}, kappa None), whose envelope
    uses the B series of an independent online_lb.OnlineLB (the guard's must equal it). At every E-mode slot at which
    T0gBound is in its bound form, K0 passes the guard's test (no purchase or rent term, R = 0, G = Q(t), stranding
    term at most R(t - 1)), and no run aborts (T0g stays in bound form in every run). Every slot's candidates follow
    §2.4 step 3 and name only objects of obs (P1, P0, K0); the report's a-hat, G, S and R equal T0g's oracle on the
    executed lists, with ALG(t) <= a-hat(t); ALG(t) + R(t) <= gamma C_S(t) + B(t) + GUARD_TOL at every executed slot
    from the ledger. Coverage, at both allowances: every candidate is executed, K0 with guard Releases, and K0 is
    checked at slots with a positive budget and stranding term."""
    sts = {"alg1": Counter(), "lb": Counter()}
    for seed, v, mname, make, allow, gamma, ad in _p_cases():
        lm = P_MODELS[mname]
        info = lm.get("information", "I1")
        inst = _rich_instance(seed, v, bool(v % 2))
        cautious = lm.get("on_unavailable") == "refuse"
        kw = {"safe": "fb", "gamma": gamma, "on_unavailable": "refuse" if cautious else None, **allow}
        res, rep, pol, rec_in = _run(inst, LenderModel(**lm), make(17 * v + 3), kw, EngineConfig(auto_drain=ad))
        a = allow.get("allowance", "alg1")
        st = sts[a]
        st["runs"] += 1
        tag = (seed, v, mname, make.__name__, allow, gamma, ad)
        assert rep["t_a"] is None and rep["t0g"]["robust_since"] is None, (tag, rep["t_a"], rep["t0g"]["events"][:3])
        assert rep.get("allowance", "alg1") == a, tag
        _check_prop_p(pol, tag, st)
        _t0g_check_x(inst, res, _executed_rec(pol), ad, tag, cautious=cautious, info=info)
        st["env"] += _envelope(inst, res, gamma, _allowance(inst, allow.get("B0"), allow["kappa"], a, info), tag)
        for k, x in rep["projection"].items():
            st["proj:" + k] += x
        assert sum(n for _w, _t, n in rep["candidates"]) == inst.grid.T_slow, tag
    assert sts["alg1"]["runs"] == sts["lb"]["runs"] == 128, sts
    for a, st in sts.items():
        assert st["k0_bound"] == st["slots"] > 0 and st["k0_budget_pos"] > 0, (a, st)
        for k in ("P1", "P0", "K0", "guard_releases", "dropped_buys", "dropped_other"):
            assert st["proj:" + k] > 0, (a, k, st)


def test_refusal_mapping():
    """The refusal mapping of §2.4 step 1 (_check_mapping) on projected runs: _RandomInner and _OwnListInner (dropped
    actions of every type: Buys, and Releases, Loads, Unloads, SetAdmissions and Drains of objects of the inner's own
    list or at K0) on _rich_instance, and BL1 and BL5 at Algorithm 1's defaults (safe 'fb+pd'), whose LeaseBook raises
    PolicyError for a result that does not match its staged Buy. Guard Releases appear in obs.ended with cause
    'release'; after a slot executed as A_E(t) the results are the engine's."""
    st = Counter()
    for seed, v, mname, make, allow, gamma, ad in _p_cases(lb=False)[::3]:
        lm = P_MODELS[mname]
        inst = _rich_instance(seed, v, bool(v % 2))
        onu = "refuse" if lm.get("on_unavailable") == "refuse" else None
        kw = {"safe": "fb", "gamma": gamma, "on_unavailable": onu, **allow}
        res, rep, pol, rec_in = _run(inst, LenderModel(**lm), make(17 * v + 3), kw, EngineConfig(auto_drain=ad))
        _check_mapping(pol, rec_in, inst, (seed, v, mname, make.__name__), st)
    for inner in ("BL1", "BL5"):
        for v in range(4):
            inst = _rich_instance(0, v, False)
            res, rep, pol, rec_in = _run(inst, LenderModel(), _inner(inner), {"N_bound": _N(inst)})
            assert rep["t_a"] is None, (inner, v)
            st[inner + ":projected_slots"] += rep["projection"]["slots"]
            _check_mapping(pol, rec_in, inst, (inner, v), st)
    assert st["identity"] > 0 and st["projected"] > 0 and st["guard_releases"] > 0, st
    assert st["BL1:projected_slots"] > 0 and st["BL5:projected_slots"] > 0, st
    for k in ACTION_TYPES:
        assert st["dropped:" + k] > 0, (k, st)


def test_fast_inner_runs():
    """_FastInner (condition C1 fails: T0g in its robust form at every slot) under A8P (§8.3): runs with its aborts
    counted and no assertion on them, on _rich_instance under the lenders of ROBUST_MODELS ('refuse' with the option
    passed), constant B0 in {5, 40} and gamma in {1, 1.7}. Every run has no invariant failure (the guard drops the fast
    actions on replicas of leases it released; the engine would raise ActionError), its report's a-hat, G, S and R
    equal T0g's oracle in the robust form, the envelope holds at every executed slot from the ledger, and every abort
    is unforced. Coverage: projected slots, K0, and a dropped fast action."""
    st = Counter()
    for v in range(4):
        for i, (mname, lm) in enumerate(ROBUST_MODELS.items()):
            inst = _rich_instance(2, v, bool((v + i) % 2))
            cautious = mname.startswith("refuse")
            for B0 in (5.0, 40.0):
                for gamma in (1.0, 1.7):
                    kw = {"safe": "fb", "gamma": gamma, "B0": B0, "kappa": None,
                          "on_unavailable": "refuse" if cautious else None}
                    ad = bool((v + 1) % 2)
                    res, rep, pol, rec_in = _run(inst, LenderModel(**lm), _FastInner(13 * v + i + 5), kw,
                                                 EngineConfig(auto_drain=ad))
                    tag = (v, mname, B0, gamma)
                    assert rep["t0g"]["robust_all"] is True, tag
                    _oracle_executed(inst, res, _executed_rec(pol), ad, tag, cautious=cautious,
                                     info=lm.get("information", "I1"), robust_all=True)
                    _envelope(inst, res, gamma, np.full(inst.grid.T_slow, B0), tag)
                    if rep["t_a"] is not None:
                        st["aborts"] += 1
                        assert rep["guard"]["forced"] is False and rep["at_abort"]["forced"] is False, tag
                    st["runs"] += 1
                    st["projected"] += rep["projection"]["slots"]
                    st["K0"] += rep["projection"]["K0"]
                    st["dropped_fast"] += rep["dropped_fast"]
    assert st["runs"] == 64 and st["projected"] > 0 and st["K0"] > 0 and st["dropped_fast"] > 0, st


# ================================================================ certificates and records of MS4's driver layer
def test_certify_and_a8_record():
    """ms4_common.certify and a8_record read A8P's report as A8's (§8.1, §8.3). BL1 under A8P at Algorithm 1's defaults
    (safe 'fb+pd', B0 'auto', kappa 10) on _rich_instance variants 0-3, where A8 around BL1 aborts and A8P projects
    instead: the certificate is available and held, case W(a), with the reserve in the E-mode check and m = 0;
    a8_record gives B0_rule 'auto, kappa 10', B0_usd = guard.b0_auto = the report's B0, info_class 'online-I1 +
    a-priori N' (no BL0a), t_a None. An A8P run that aborts (gamma 0.5, B0 = 0, S on FB): case W(b), held."""
    from sublet.experiments import ms4_common as m4
    n_proj = 0
    for v in range(4):
        inst = _rich_instance(0, v, False)
        params = {"inner": "BL1", "project": True}
        pol = ProjectedGuarded(N_bound=_N(inst), **params)
        res = simulate(inst, pol, LenderModel(), policy_seed=0)
        assert res.invariant_failures == []
        rep = res.metrics["policy"]
        n_proj += rep["projection"]["slots"]
        cert, case = m4.certify(res, inst)
        assert cert["available"] and cert["held"] is True and case == "W(a)", (v, cert)
        assert cert["reserve"] and cert["e_mode_reserve_ok"] and cert["m_ok"] and cert["test"] == "T0g", (v, cert)
        rec = m4.a8_record(res, inst, params)
        b0 = guard.b0_auto(public_view(inst, "I1"))
        assert rec["B0_rule"] == "auto, kappa 10" and rec["B0_usd"] == b0 == rec["B0_report_usd"] == rep["B0"], rec
        assert rec["info_class"] == rec["info_class_reported"] == "online-I1 + a-priori N", rec
        assert rec["certificate"]["held"] is True and rec["certificate_case"] == "W(a)", rec
        assert rec["t_a"] is None and rec["aborted"] is False and "ALG_per_slot" not in rec["certificate"], rec
        a8 = simulate(inst, Guarded(inner="BL1", N_bound=_N(inst)), LenderModel(), policy_seed=0)
        assert a8.metrics["policy"]["t_a"] is not None, v
    assert n_proj > 0
    inst = _rich_instance(0, 0, False)
    params = {"inner": "BL1", "safe": "fb", "gamma": 0.5, "B0": 0.0, "kappa": None}
    res = simulate(inst, ProjectedGuarded(**params), LenderModel(), policy_seed=0)
    rep = res.metrics["policy"]
    assert rep["t_a"] is not None and rep["guard"]["forced"] is False
    cert, case = m4.certify(res, inst)
    assert case == "W(b)" and cert["held"] is True and cert["proven_case"], cert
    rec = m4.a8_record(res, inst, params)
    assert rec["certificate_case"] == "W(b)" and rec["t_a"] == rep["t_a"] and rec["aborted"] is True, rec


# ================================================================ the stored E7 Sublet run (pilot step P0)
P0_TOTAL_USD = 13932.930630343202        # out/e7/main/jobs/e7__main__pol__Sublet__mu__1__c__1.json, policy seed 0
P0_INSTANCE_HASH = "f1b5be0fcf6e2cd7e084036bad5796ace7168ee277a2d908072f0152cbb49d5e"


@pytest.mark.needs_raw
@pytest.mark.needs_a12
@pytest.mark.slow
def test_e7_sublet_identity():
    """A8P with project false at Sublet-MS4's parameters (ms4_common.sublet_params(inst, 'BL5'), the driver inputs as
    drivers/run.py passes them to A8) reproduces the stored E7 Sublet run at alignment 1, policy seed 0, L-tr, mu 1 to
    1e-9 USD (13,932.930630343202 USD; out/e7/main/jobs/e7__main__pol__Sublet__mu__1__c__1.json), on the same instance
    (its hash); the policy's resolved parameters are A8's plus project false. About 150 s."""
    from sublet.algos import registry
    from sublet.drivers import run as drun
    from sublet.experiments import e7
    from sublet.experiments import ms3_common as mc
    c = 1
    spec0 = e7.week_spec("BL0a", {}, mu=1.0, mode="L-tr", c=c, seeds=(0,))
    inst, model, ecfg = drun.build(spec0, c)
    assert mc.instance_hash(inst) == P0_INSTANCE_HASH
    params = e7.tag_params("Sublet", inst)
    spec = e7.week_spec("A8", params, mu=1.0, mode="L-tr", c=c, seeds=(0,), name="e7_main_Sublet")
    vals, _ = drun.driver_inputs("A8", params, inst)
    iid, ipar = registry.inner_of("A8", params)
    kw = dict(params)
    kw["inner_params"] = {**ipar, **{k: vals[k] for k in registry.needed_inputs(iid, ipar)}}
    kw.update({k: vals[k] for k in registry.a8_own_inputs(params)})
    kw["on_unavailable"] = model.on_unavailable
    pol = ProjectedGuarded(project=False, **kw)
    assert {**drun.make_policy(spec, inst).params(), "project": False} == pol.params()
    res = simulate(inst, pol, model, ecfg, lender_seed=c, policy_seed=0)
    assert res.invariant_failures == []
    tot = float(res.components["total"])
    assert abs(tot - P0_TOTAL_USD) <= 1e-9, (tot, P0_TOTAL_USD)
