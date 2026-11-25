"""Tests of policy A2 (sublet/algos/a2.py) through the engine on from_core instances
(design/sim_spec_ms2.md §6.6, §6.7; exit check 3i, A2 columns; §17.2)."""
import json
from collections import defaultdict

import numpy as np
import pytest

import check_c4_lower
import core
import pd as ref_pd

from fixtures import CONFIGS, UPPER_FAMS, lease_cost, upper_case

from sublet.algos.a2 import A2
from sublet.engine import simulate
from sublet.instance import from_core, units
from sublet.types import LenderModel

TC = CONFIGS.parents[1] / "theory_checks" / "c3"
TOL = 1e-9
SCHEDULES = ("trace_bern0.1", "adaptive")


def _close(a, b, tol=TOL) -> bool:
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def _N_bound(inst) -> int:
    """The driver input N of §6.3: max(N_u T_s, 3) with N_u = len(units(inst).client)."""
    return max(len(units(inst).client) * inst.grid.T_slow, 3)


def _a2(inst, rbar, **kw):
    if rbar == "theory":
        return A2(rbar="theory", N_bound=_N_bound(inst), record=True, **kw)
    return A2(rbar=1, record=True, **kw)


def _instance(I, sched: str, seed: int):
    """(Instance, LenderModel): from_core with no announcement (empty), a Bernoulli(0.1) trace schedule
    (core.random_omega(default_rng(7000 + seed), I, 0.1)) or the adaptive lender."""
    if sched == "trace_bern0.1":
        om = core.random_omega(np.random.default_rng(7000 + seed), I, 0.1)
        return from_core(I, om)[0], LenderModel()
    inst, _ = from_core(I, [np.zeros(0, np.int64)] * I.m)
    return inst, LenderModel(schedule="adaptive" if sched == "adaptive" else "trace")


def _report_opened(rep: dict) -> dict:
    return {tuple(k): t for k, t in rep["opened_map"]}


@pytest.mark.parametrize("fam_name", UPPER_FAMS)
def test_online_equals_offline(fam_name):
    """simulate(from_core(upper_case), A2(rbar), policy_rng=default_rng(s)), instances 0-3 of the family,
    s = 0..3, r-bar in {1, theory}: the opened map and cost_pr equal round_pd(FracPD(I).run(),
    default_rng(s), r)'s (the online run reproduces the offline rounding)."""
    for seed in range(4):
        I = upper_case(fam_name, seed)
        pdr = ref_pd.FracPD(I).run()
        inst, model = _instance(I, "empty", seed)
        assert _N_bound(inst) == max(I.n * I.T, 3)
        for rbar in ("theory", 1):
            for s in range(4):
                x = ref_pd.round_pd(pdr, np.random.default_rng(s), r=None if rbar == "theory" else 1)
                pol = _a2(inst, rbar)
                res = simulate(inst, pol, model, policy_rng=np.random.default_rng(s))
                tag = f"{fam_name}/{seed} r={rbar} s={s}"
                assert res.invariant_failures == [], tag
                rep = res.metrics["policy"]
                assert rep["rbar"] == x["r"], tag
                assert _report_opened(rep) == x["opened"], tag
                assert pol.opened_ref() == x["opened"], tag
                assert rep["opened"] == len(x["opened"]) and rep["refused"] == 0, tag
                assert _close(rep["cost_pr"], x["cost_pr"]), (tag, rep["cost_pr"], x["cost_pr"])
                assert _close(rep["cost_an"], x["cost_an"]) and rep["n_fix_an"] == x["n_fix_an"], tag
                assert _close(rep["P"], pdr.primal()) and rep["d"] == pdr.d, tag


@pytest.mark.parametrize("sched", SCHEDULES)
def test_engine_le_accounted(sched):
    """§6.2, §6.6 on the same runs (instances 0-3 of every family, s = 0..3, both r-bar) under a Bernoulli(0.1)
    trace schedule and the adaptive lender: the engine's lease_prepaid + lease_rent + loading equals the
    sum of C_F over the opened columns (1e-9); the engine total is at most cost_pr and at most that sum plus
    pd.service_cost_given_open(I, opened).sum() (+1e-9)."""
    worst = []
    for fam_name in UPPER_FAMS:
        for seed in range(4):
            I = upper_case(fam_name, seed)
            inst, model = _instance(I, sched, seed)
            for rbar in ("theory", 1):
                for s in range(4):
                    pol = _a2(inst, rbar)
                    res = simulate(inst, pol, model, policy_rng=np.random.default_rng(s))
                    tag = f"{sched} {fam_name}/{seed} r={rbar} s={s}"
                    assert res.invariant_failures == [], tag
                    rep = res.metrics["policy"]
                    opened = _report_opened(rep)
                    sumC = sum(I.C(F[1], F[2], F[3]) for F in opened)
                    c = res.components
                    assert _close(lease_cost(c), sumC), (tag, lease_cost(c), sumC)
                    serv = float(ref_pd.service_cost_given_open(I, opened).sum())
                    tot = c["total"]
                    assert tot <= rep["cost_pr"] + TOL * max(1.0, rep["cost_pr"]), (tag, tot, rep["cost_pr"])
                    assert tot <= sumC + serv + TOL * max(1.0, sumC + serv), (tag, tot, sumC + serv)
                    worst.append(tot / rep["cost_pr"])
    assert max(worst) <= 1 + TOL


def test_c4_lower_b_pd_columns():
    """Check 3i (A2 columns): check_c4_lower.single(48, [(1, 1), (48, 0)], beta, [1.0, 1.3]),
    beta in {2, 6, 14, 30}, schedule eager, A2 with r-bar = 1 and policy_rng = default_rng(s), s = 0..9:
    mean cost_pr / full-menu core.opt_eager equals c4_lower.json b[*].pd_r1_ratio, and P / OPT equals
    frac_ratio (1e-9)."""
    rows = json.loads((TC / "out" / "c4_lower.json").read_text())["b"]
    assert [r["beta"] for r in rows] == [2, 6, 14, 30]
    for row in rows:
        I = check_c4_lower.single(48, [(1, 1), (48, 0)], row["beta"], [1.0, 1.3])
        oe = core.opt_eager(I)
        assert oe["status"] == 0
        full = oe["fun"]
        inst, _ = from_core(I, [np.zeros(0, np.int64)])
        cost, P = [], []
        for s in range(10):
            res = simulate(inst, A2(rbar=1), LenderModel(schedule="eager"), policy_rng=np.random.default_rng(s))
            assert res.invariant_failures == []
            cost.append(res.metrics["policy"]["cost_pr"])
            P.append(res.metrics["policy"]["P"])
        assert max(P) == min(P)
        assert _close(np.mean(cost) / full, row["pd_r1_ratio"]), (row["beta"], np.mean(cost) / full, row["pd_r1_ratio"])
        assert _close(P[0] / full, row["frac_ratio"]), (row["beta"], P[0] / full, row["frac_ratio"])


@pytest.mark.parametrize("sched", ("eager", "adaptive", "trace_bern0.1"))
def test_every_window_realized(sched):
    """§6.6: under eager, adaptive and a Bernoulli trace schedule, every opened column F = (l, j, k, s) opened
    at t0 has an alive lease of its type (site l, contract k, a replica of LLM j) bought at t0 and alive in
    every fast slot of [t0, min(s + L_k, T)) (instances 0-1 of every family, both r-bar, s = 0, 1)."""
    for fam_name in UPPER_FAMS:
        for seed in range(2):
            I = upper_case(fam_name, seed)
            if sched == "eager":
                inst, _ = from_core(I, [np.zeros(0, np.int64)] * I.m)
                model = LenderModel(schedule="eager")
            else:
                inst, model = _instance(I, sched, seed)
            g = inst.grid
            for rbar in ("theory", 1):
                for s in range(2):
                    res = simulate(inst, _a2(inst, rbar), model, policy_rng=np.random.default_rng(s))
                    tag = f"{sched} {fam_name}/{seed} r={rbar} s={s}"
                    assert res.invariant_failures == [], tag
                    need = defaultdict(list)                  # (l, j, k, t0) -> window ends
                    for F, t0 in _report_opened(res.metrics["policy"]).items():
                        _, l, j, k, s0 = F[:5]
                        need[(l, j, k, t0)].append(min(s0 + int(I.L[k]), g.T_slow))
                    llm_of = {r.lease_id: r.llm for r in res.replicas}
                    have = defaultdict(list)
                    for L in res.leases:
                        have[(L.site, llm_of[L.id], L.contract, L.start_slot)].append(L)
                    for key, ends in need.items():
                        leases = have.get(key, [])
                        assert len(leases) == len(ends), (tag, key, len(leases), len(ends))
                        for L, e in zip(sorted(leases, key=lambda x: x.end_min), sorted(ends)):
                            assert L.start_min == key[3] * g.slow_min, (tag, key)
                            assert L.end_min >= e * g.slow_min, (tag, key, L.end_min, e)
                    assert sum(len(v) for v in have.values()) == sum(len(v) for v in need.values()), tag


# ---------------------------------------------------------------- full model: layering, refusals, release slot
def _demand_obs(inst, t):
    """The planner's input at slow slot t: the demand of the slot's fast slots (§5.1, engine mode)."""
    from types import SimpleNamespace
    g = inst.grid
    return SimpleNamespace(t=t, demand=inst.clients.demand[:, t * g.phi:(t + 1) * g.phi])


def test_layering_engine_mode():
    """§6.4 as A2Planner runs it (Layering.iota_vec through pd.request) on configs/ms2_multi_small.json, 60
    slots, policy_streams(default_rng(0)), replayed independently: the requests of slot t are the units
    (c, v), v = 1..#{i >= 0: i/u < D_c(t)}, client ascending; each aligned candidate (l, j, k, s, iota) has
    s = floor(t / L_k) L_k and iota = the index of the unit's own host set at (l, j, k), else the smallest
    index with fewer than u units; each practical assignment is one of the request's candidates; no host
    set exceeds u units; units not active in a slot leave their host sets; some iota >= 1 occurs."""
    from sublet.algos.a2 import A2Planner
    from sublet.algos.common import policy_streams
    from sublet.instance import build_instance, public_view
    inst = build_instance(CONFIGS / "ms2_multi_small.json")
    v = public_view(inst, "I1")
    assert not v.kappa_infinite
    st = policy_streams(np.random.default_rng(0))
    pl = A2Planner(v, st["main"], st["order"])
    assert pl.layering.active
    u = int(v.units_per_replica)
    log, cur = [], {}
    o_req, o_proc = pl.pd.request, pl.rounder.process

    def req(c, t, *, iota=None, excluded=None):
        out = o_req(c, t, iota=iota, excluded=excluded)
        cur["keys"] = [pl.pd.ref_key(x) for x in out.cols]
        return out

    def proc(out, unit=None):
        r = o_proc(out, unit)
        log.append((int(out.t), unit, cur["keys"], pl.rounder.last_assignment))
        return r
    pl.pd.request, pl.rounder.process = req, proc
    T = 60
    g = inst.grid
    for t in range(T):
        pl.slot(_demand_obs(inst, t))
    L = [int(x) for x in pl.pd.L]
    host: dict = {}
    where: dict = {}
    i = n_iota = max_iota = 0
    for t in range(T):
        D = inst.clients.demand[:, t * g.phi:(t + 1) * g.phi].max(axis=1)
        want = []
        for c in range(inst.n):
            nc = 0
            while D[c] > 0 and nc / u < D[c]:
                nc += 1
            want += [(c, w) for w in range(1, nc + 1)]
        assert [x[1] for x in log if x[0] == t] == want, t
        active = set()
        for unit in want:
            _, _, keys, asg = log[i]
            i += 1
            for key in keys:
                assert key[0] == "A", key
                l, j, k, s0 = key[1:5]
                io = key[5] if len(key) > 5 else 0
                w = where.get(unit)
                if w is not None and w[0] == (l, j, k):
                    exp = w[1]
                else:
                    hs = host.get((l, j, k), [])
                    exp = next((x for x, h in enumerate(hs) if len(h) < u), len(hs))
                assert io == exp, (t, unit, key, exp)
                assert s0 == (t // L[k]) * L[k], (t, key)
                max_iota = max(max_iota, io)
                n_iota += io > 0
            w = where.pop(unit, None)
            if w is not None:
                host[w[0]][w[1]].discard(unit)
            if asg is not None:
                l, j, k, s0, io = asg
                assert ("A", l, j, k, s0) + ((io,) if io else ()) in keys, (t, unit, asg)
                hs = host.setdefault((l, j, k), [])
                while len(hs) <= io:
                    hs.append(set())
                hs[io].add(unit)
                where[unit] = ((l, j, k), io)
                assert len(hs[io]) <= u, (t, (l, j, k), io)
            active.add(unit)
        for unit in [x for x in where if x not in active]:
            w = where.pop(unit)
            host[w[0]][w[1]].discard(unit)
    assert i == len(log) and max_iota >= 1 and n_iota > 0


def _capped_toy():
    """toy.json with L0 and L1 at 1 GPU each, R empty, demand 2.0 (8 units, u = 4): A2 opens several columns
    at one site in a slot, and the pre-check of LeaseBook.assemble drops the purchases beyond capacity."""
    from fixtures import toy_config
    from sublet.instance import build_instance
    cfg = toy_config({"lenders.0.capacity_gpus": 1, "lenders.1.capacity_gpus": 1, "lenders.0.R": [],
                      "lenders.1.R": []})
    cfg["borrowers"]["clients"][0]["demand"]["values"] = [2.0] * 24
    return build_instance(cfg)


def _refusal_run(inst, model, s):
    """A2(rbar=1) with its PD requests and refusals logged: (result, candidate log [(t, cols)], refusal log
    [(col, t, reason, column, cost_pr before, cost_pr after, in opened, is_open)])."""
    pol = A2(rbar=1, record=True)
    cands, refs = [], []
    o_reset = pol.reset

    def reset(view, rng):
        o_reset(view, rng)
        pl = pol.planner
        o_req, o_ref = pl.pd.request, pl.refuse

        def req(c, t, *, iota=None, excluded=None):
            out = o_req(c, t, iota=iota, excluded=excluded)
            cands.append((int(t), [int(x) for x in out.cols]))
            return out

        def refuse(col, t, reason=""):
            before = pl.rounder.cost_pr
            o_ref(col, t, reason)
            refs.append((int(col), int(t), reason, pl.column(col), before, pl.rounder.cost_pr,
                         int(col) in pl.rounder.opened, pl.rounder.is_open(col)))
        pl.pd.request, pl.refuse = req, refuse
    pol.reset = reset
    res = simulate(inst, pol, model, policy_rng=np.random.default_rng(s))
    return res, cands, refs


def test_refusals():
    """§6.5 (M11) end to end: a purchase dropped by the pre-check (toy with 1-GPU sites) or refused by the
    engine (ms2_multi_small under on_unavailable='refuse') refuses its column at t + 1: the column leaves the
    candidate lists of every request in [t + 1, s + L_k), leaves the opened set (not is_open), and cost_pr is
    unchanged by the refusal; report()['refused'] and refused_by_reason count the refusals."""
    from fixtures import load_json
    from sublet.instance import build_instance
    cfg = load_json(CONFIGS / "ms2_multi_small.json")
    cfg["time"]["horizon_min"] = 720
    cases = [("toy capped", _capped_toy(), LenderModel(), "precheck"),
             ("ms2 refuse", build_instance(cfg), LenderModel(on_unavailable="refuse"), "unavailable")]
    for name, inst, model, reason in cases:
        res, cands, refs = _refusal_run(inst, model, 0)
        assert res.invariant_failures == [], name
        rep = res.metrics["policy"]
        assert len(refs) > 0 and rep["refused"] == len(refs), (name, len(refs), rep["refused"])
        by = {}
        for r in refs:
            by[r[2]] = by.get(r[2], 0) + 1
        assert rep["refused_by_reason"] == by and by.get(reason, 0) > 0, (name, by)
        for col, t, why, (l, j, k, s0, io, L), before, after, in_open, is_open in refs:
            assert before == after and not in_open and not is_open, (name, col, t)
            for tt, cols in cands:
                if t <= tt < s0 + L:
                    assert col not in cols, (name, col, t, tt)
        assert rep["leases"]["refused"] == len(refs)


def test_refusal_ends_with_window():
    """§6.5: a refused column is excluded until its window [s, s + L) ends; at slot s + L it is a candidate
    again (no longer in the planner's refused set)."""
    from fixtures import toy_instance
    from sublet.algos.a2 import A2Planner
    from sublet.instance import public_view
    inst = toy_instance()
    v = public_view(inst, "I1")
    pl = A2Planner(v, np.random.default_rng(0), np.random.default_rng(1))
    out = pl.pd.request(0, 0)
    col = int(out.cols[0])
    l, j, k, s, iota, L = pl.column(col)
    assert s == 0 and L >= 2
    pl.refuse(col, 0, "precheck")
    pl.slot(_demand_obs_zero(inst, s + L - 1))
    assert col in pl.refused
    pl.slot(_demand_obs_zero(inst, s + L))
    assert col not in pl.refused


def _demand_obs_zero(inst, t):
    from types import SimpleNamespace
    return SimpleNamespace(t=t, demand=np.zeros((inst.n, inst.grid.phi)))


def test_release_at_window_end():
    """§6.6: A2 releases the lease of a column opened at t0 at max(s + L_k, ceil((t0 Δs + P_k) / Δs)) with
    s = floor(t0 / L_k) L_k; under billing 'commit_tau' (P = tau) the window's end binds for some lease."""
    from fixtures import toy_config
    from sublet.algos.common import pd_window_slots
    from sublet.engine import EngineConfig
    from sublet.instance import build_instance, public_view
    inst = build_instance(toy_config({"billing": "commit_tau", "lenders.0.R": [], "lenders.1.R": []}))
    v = public_view(inst, "I1")
    slow = inst.grid.slow_min
    res = simulate(inst, A2(rbar=1), LenderModel(), EngineConfig(check_invariants=True), policy_seed=0)
    assert res.invariant_failures == []
    n_window = 0
    released = [L for L in res.leases if L.end_cause == "release"]
    assert released
    for L in released:
        Lk = pd_window_slots(v, L.contract, None)
        s = (L.start_slot // Lk) * Lk
        billed = -(-(L.start_slot * slow + v.contracts[L.contract].prepaid_min) // slow)
        assert L.end_min == max(s + Lk, billed) * slow, (L, s, Lk, billed)
        n_window += s + Lk > billed
    assert n_window > 0
