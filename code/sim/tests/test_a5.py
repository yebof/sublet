"""Tests of policy A5 and the prediction driver (design/sim_spec_ms2.md §13, §17.2 test_a5.py).

A5 runs through the engine on from_core of the c5 instances (`fixtures.c5_case`, the instances and
the nine predictions of check_c5_la.py with P-hat = drivers.predict.plan_core) with execute='none'
(accounting only) and the policy generator default_rng(s) of the reference rounding; its report
gives the FP and R curves (`curve_FP`, `curve_R`), the combiner's `total` and `switches`, and R's
opened map (`opened_ref()`). The reference is pd.follow_prediction, pd.round_pd and pd.combine.
"""
from __future__ import annotations

import math
from collections import Counter

import numpy as np

import core
import pd as ref_pd

from fixtures import toy_config

from sublet.drivers import predict
from sublet.drivers.run import make_policy
from sublet.engine import EngineConfig, simulate
from sublet.experiments.repro_common import get, opened_map
from sublet.instance import build_instance, from_core, public_view, restrict_horizon, to_core, with_demand
from sublet.opt.milp import solve_eager
from sublet.policies.trivial import FixedPlan
from sublet.types import LenderModel, Schedule

G2 = 1 + 1 / math.sqrt(2)


def _a5(inst, P, *, gamma=G2, rbar=1, N=None, s=0):
    pol = make_policy({"policy": {"id": "A5", "params": {"gamma": gamma, "R_rbar": rbar, "execute": "none"}}}, inst,
                      inputs={"pred_cols": list(P), **({"N_bound": N} if rbar == "theory" else {})})
    res = simulate(inst, pol, LenderModel(schedule="trace"), EngineConfig(), policy_rng=np.random.default_rng(s))
    assert not res.invariant_failures, res.invariant_failures[:3]
    return pol, pol.report()


def _close(a, b, tol):
    return abs(a - b) <= tol * max(1.0, abs(b))


# ---------------------------------------------------------------- FP and the combiner
def test_follow_prediction_curve():
    """§13.3: A5's curve_FP equals pd.follow_prediction(I, P) on c5_case seeds 0-9, all nine predictions (1e-12)."""
    from fixtures import c5_case
    n = 0
    for seed in range(10):
        I, preds = c5_case(seed)
        inst, _ = from_core(I, [np.zeros(0, dtype=np.int64)] * I.m)
        for p in preds:
            _, rep = _a5(inst, p.P)
            want = ref_pd.follow_prediction(I, list(p.P))
            got = np.asarray(get(rep, "curve_FP"), dtype=float)
            assert got.shape == want.shape
            assert np.all(np.abs(got - want) <= 1e-12 * np.maximum(1.0, np.abs(want))), (seed, p.kind, p.par)
            assert _close(float(get(rep, "C_FP")), float(want.sum()), 1e-12)
            n += 1
    assert n == 90


def test_combiner_equals_reference():
    """§13.4: on c5_case seeds 0-1, the nine predictions, R seeds 0-7, rbar in {1, theory} and gamma in
    {2, 1 + 1/sqrt 2}: A5's opened map and R curve equal round_pd's (keys and slots exact, curve 1e-9),
    and its total and switches equal pd.combine(I, P, fp, opened, curve, gamma) (1e-9; exact)."""
    from fixtures import c5_case
    for seed in (0, 1):
        I, preds = c5_case(seed)
        inst, _ = from_core(I, [np.zeros(0, dtype=np.int64)] * I.m)
        N = max(I.n * I.T, 3)
        frac = ref_pd.FracPD(I).run()
        for p in preds:
            P = list(p.P)
            fp = ref_pd.follow_prediction(I, P)
            for rbar, r_ref in ((1, 1), ("theory", None)):
                for s in range(8):
                    x = ref_pd.round_pd(frac, np.random.default_rng(s), r=r_ref)
                    for gamma in (2.0, G2):
                        pol, rep = _a5(inst, P, gamma=gamma, rbar=rbar, N=N, s=s)
                        where = (seed, p.kind, p.par, rbar, s, gamma)
                        om = opened_map(pol)
                        assert om == {tuple(k): int(t) for k, t in x["opened"].items()}, where
                        cr = np.asarray(get(rep, "curve_R"), dtype=float)
                        assert np.all(np.abs(cr - x["curve"]) <= 1e-9 * np.maximum(1.0, np.abs(x["curve"]))), where
                        tot, sw = ref_pd.combine(I, P, fp, x["opened"], x["curve"], gamma=gamma)
                        assert _close(float(get(rep, "total")), tot, 1e-9), (where, get(rep, "total"), tot)
                        assert int(get(rep, "switches")) == sw, where


# ---------------------------------------------------------------- the prediction driver
def test_previous_day():
    """§13.2 (M38): day 0 has no prediction; day d >= 1 predicts the realized demand of day d - 1."""
    rng = np.random.default_rng(3)
    day_fast = 12
    d = rng.uniform(0, 2, size=(3, 3 * day_fast + 5))
    out = predict.previous_day(d, day_fast)
    assert out.shape == d.shape
    assert not out[:, :day_fast].any()
    assert np.array_equal(out[:, day_fast:], d[:, :-day_fast])


def _two_day_toy():
    """A 2-day toy on 60-min slots: revocable ('h1': tau 1 h, H 1 h; 'h2': tau 2 h, H 2 h) at L0 and L1
    with slow loads (1800 s), protected at 3.5 USD/GPU-h (load 600 s); demand of day 0 with one long
    run and short bursts, day 1 its copy shifted by one slot."""
    cfg = toy_config()
    cfg["name"] = "two_day_toy"
    cfg["time"] = {"slow_slot_min": 60, "fast_slot_min": 60, "horizon_min": 2880, "start_minute_of_week": 0}
    cfg["prices"]["a_protected_usd_per_gpu_h"] = 3.5
    cfg["contracts"] = [{"id": "h1", "tau_min": 60, "H_min": 60}, {"id": "h2", "tau_min": 120, "H_min": 120},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": 60}]
    for L in cfg["lenders"][:2]:
        L.update({"menu": ["h1", "h2"], "prices": {"h1": 2.85, "h2": 3.0}, "lam_s": 1800.0, "capacity_gpus": 8})
    cfg["lenders"][2]["lam_s"] = 600.0
    day0 = [0, 0] + [1.0] * 14 + [0, 0, 0, 1.0, 0, 1.0, 1.0, 0]
    day1 = [0] + day0[:-1]
    cfg["borrowers"]["clients"][0]["demand"]["values"] = [float(v) for v in day0 + day1]
    cfg["bench"] = {"grid": "slow", "time_limit_s": 120, "mip_rel_gap": 1e-9}
    return build_instance(cfg)


def test_plan_daily_milp():
    """§13.2 with method 'milp' on a 2-day toy with its protected site: the predicted columns of day 1 come
    from solve_eager's plan of the day instance (previous-day demand): one column (l, j, k, start + o)
    per replica of each revocable lease, ceil((e - s) / L_k) consecutive columns covering [s, e) per
    replica of each protected lease; FixedPlan of the day's plan replayed under 'eager' on the day
    instance costs solve_eager's objective (1e-6)."""
    inst = _two_day_toy()
    g = inst.grid
    day_slots = 1440 // g.slow_min
    pred = predict.previous_day(inst.clients.demand, 1440 // g.fast_min)
    cols = predict.plan_daily(inst, pred, day_slots=day_slots, method="milp")
    day = restrict_horizon(with_demand(inst, pred), day_slots, day_slots)
    bench = inst.config["bench"]
    sr = solve_eager(day, grid="slow", time_limit_s=bench["time_limit_s"], mip_rel_gap=bench["mip_rel_gap"])
    assert sr.status == 0 and sr.plan is not None
    view = public_view(inst, "I1")
    from sublet.algos.common import pd_window_slots, treated_as_protected
    want = []
    n_prot = n_rev = 0
    for pl in sr.plan:
        k = int(pl.contract)
        if treated_as_protected(view, k):
            n_prot += 1
            e = pl.release_slot if pl.release_slot is not None else day_slots
            Lk = pd_window_slots(view, k, None)
            starts = [pl.start_slot + i * Lk for i in range(-(-(e - pl.start_slot) // Lk))]
            assert starts[0] == pl.start_slot and starts[-1] + Lk >= e      # the columns cover [s, e)
        else:
            n_rev += 1
            starts = [pl.start_slot]
        want += [(pl.site, pl.llm, k, s + day_slots) for s in starts for _ in range(pl.n)]
    assert n_prot > 0 and n_rev > 0, (n_prot, n_rev, sr.plan)
    assert Counter(tuple(int(v) for v in c) for c in cols) == Counter(want)
    res = simulate(day, FixedPlan(sr.plan), LenderModel(schedule="eager"), EngineConfig())
    assert not res.invariant_failures
    assert abs(res.components["total"] - sr.objective) <= 1e-6 * max(1.0, abs(sr.objective))


def test_lp_round():
    """§13.2 (M39): the aligned-column LP of a day equals core.lp_aligned on a to_core-exact export (1e-6),
    and plan_daily with 'lp_round' predicts the aligned columns with x_F > 1 - U_F, one U_F per column
    from the driver's generator in column order."""
    I = core.random_instance(np.random.default_rng(41), T=24, m=3, J=2, n=6)
    inst, sched = from_core(I, [np.zeros(0, dtype=np.int64)] * I.m)
    ex = to_core(inst, Schedule.eager(inst))
    assert ex.exact, ex.notes
    lp = predict.aligned_lp(inst)
    want = core.lp_aligned(ex.core)["fun"]
    assert lp["status"] == "optimal" and abs(lp["fun"] - want) <= 1e-6 * max(1.0, abs(want)), (lp["fun"], want)
    # plan_daily on a two-'day' version (day_slots = 12): day 1's LP rounded with the driver's generator
    pred = inst.clients.demand.copy()
    cols = predict.plan_daily(inst, pred, day_slots=12, method="lp_round", rng=np.random.default_rng(5))
    day = restrict_horizon(with_demand(inst, pred), 12, 12)
    lp1 = predict.aligned_lp(day)
    U = np.random.default_rng(5).random(len(lp1["cols"]))
    exp = [(l, j, k, s + 12) for (l, j, k, s, _C), xv, uv in zip(lp1["cols"], lp1["x"], U) if xv > 1.0 - uv]
    assert [tuple(int(v) for v in c) for c in cols] == exp


# ---------------------------------------------------------------- FP service, replay execution, day 0
def test_fp_service_capped_at_q():
    """§13.3: FP serves a request at min{q, min delta} over the covering predicted columns: a covering column
    with delta > q does not win (cost q); without a covering column the request costs q."""
    from sublet.algos.a5 import FollowPrediction
    fp = FollowPrediction([(0, 0, 0, 0)], [2], lambda l, j, k: 1.0, 2, 1, 1)
    assert fp.slot(0, [(0, 1.0, np.array([2.0]), 1)]) == 1.0 + 1.0          # purchase C = 1 plus q = 1
    assert fp.slot(1, [(0, 1.0, np.array([0.25]), 2)]) == 0.5               # delta 0.25 < q, two requests
    fp2 = FollowPrediction([(0, 0, 0, 1)], [1], lambda l, j, k: 1.0, 3, 1, 1)
    assert fp2.slot(0, [(0, 1.0, np.array([0.25]), 1)]) == 1.0              # not covered yet: q


def _replay_runs(n_preds=None):
    from fixtures import c5_case
    for seed in (0, 1):
        I, preds = c5_case(seed)
        inst, _ = from_core(I, [np.zeros(0, dtype=np.int64)] * I.m)
        for p in (preds if n_preds is None else preds[:n_preds]):
            P = [tuple(int(v) for v in F) for F in p.P]
            pol = make_policy({"policy": {"id": "A5", "params": {"execute": "replay"}}}, inst, inputs={"pred_cols": P})
            res = simulate(inst, pol, LenderModel(schedule="trace"), EngineConfig(), policy_rng=np.random.default_rng(0))
            assert not res.invariant_failures, (seed, p.kind)
            yield seed, p, I, inst, P, res, res.metrics["policy"]


def test_replay_release_slot():
    """§13.5 (execute 'replay'): every released R lease (tag 'a5:r') ends at A2's release slot
    max(s + L_k, ceil((t0 Δs + P_k) / Δs)) with s = floor(t0 / L_k) L_k (§6.6); some lease is opened inside its
    window (t0 > s)."""
    from sublet.algos.common import pd_window_slots
    n_mid = n_rel = 0
    for seed, p, I, inst, P, res, rep in _replay_runs(3):
        v = public_view(inst, "I1")
        slow = inst.grid.slow_min
        for L in res.leases:
            if L.tag != "a5:r" or L.end_cause != "release":
                continue
            Lk = pd_window_slots(v, L.contract, None)
            s = (L.start_slot // Lk) * Lk
            want = max(s + Lk, -(-(L.start_slot * slow + v.contracts[L.contract].prepaid_min) // slow))
            assert L.end_min == want * slow, (seed, p.kind, L, want)
            n_mid += L.start_slot > s
            n_rel += 1
    assert n_rel > 0 and n_mid > 0


def test_replay_switch_buys_live_columns():
    """§13.4, §13.5: at a switch the combiner buys all live columns of the algorithm it switches to (FP: the
    predicted columns with s <= t < s + L_k; R: the opened columns with t0 <= t < s + L_k); some switch has
    live columns that were not bought at t."""
    n_switch = n_diff = 0
    for seed, p, I, inst, P, res, rep in _replay_runs():
        L = I.L
        opened = [(tuple(kk), int(t0)) for kk, t0 in rep["opened"]]
        for which, t, _n in rep["followed"][1:]:
            if which == "F":
                want = sum(1 for (l, j, k, s) in P if s <= t < s + L[k])
                at_t = sum(1 for (l, j, k, s) in P if s == t)
                got = sum(1 for x in res.leases if x.tag == "a5:fp" and x.start_slot == t)
            else:
                want = sum(1 for kk, t0 in opened if t0 <= t < kk[4] + L[kk[3]])
                at_t = sum(1 for kk, t0 in opened if t0 == t)
                got = sum(1 for x in res.leases if x.tag == "a5:r" and x.start_slot == t)
            assert got == want, (seed, p.kind, which, t, got, want)
            n_switch += 1
            n_diff += want != at_t
    assert n_switch > 0 and n_diff > 0


def test_day0_follows_lower_curve():
    """§13.2 with §13.4 (M38): with previous-day predictions, day 0 has no predicted column, so FP's day-0 curve
    is the all-fallback cost (the sum of q_req over the slot's requests); the combiner starts with FP iff
    curve_FP[0] <= curve_R[0] and otherwise follows the doubling rule; it does not force R on day 0."""
    from sublet.algos.common import unit_costs
    from sublet.instance import active_units
    inst = _two_day_toy()
    g = inst.grid
    day = 1440 // g.slow_min
    pred = predict.previous_day(inst.clients.demand, 1440 // g.fast_min)
    cols = predict.plan_daily(inst, pred, day_slots=day, method="milp")
    assert cols and min(int(F[3]) for F in cols) >= day
    pol = make_policy({"policy": {"id": "A5", "params": {"execute": "none"}}}, inst, inputs={"pred_cols": list(cols)})
    res = simulate(inst, pol, LenderModel(schedule="trace"), EngineConfig(), policy_rng=np.random.default_rng(0))
    assert not res.invariant_failures
    rep = pol.report()
    fp = np.asarray(rep["curve_FP"], dtype=float)
    cr = np.asarray(rep["curve_R"], dtype=float)
    v = public_view(inst, "I1")
    q_req, _ = unit_costs(v)
    D = inst.clients.demand.reshape(inst.n, g.T_slow, g.phi).max(axis=2)
    for t in range(day):
        n = active_units(D[:, t], v.units_per_replica)
        assert abs(fp[t] - float(np.dot(n, q_req))) <= 1e-12 * max(1.0, fp[t]), t
    first = rep["followed"][0]
    assert first[0] == ("F" if fp[0] <= cr[0] else "R") and first[1] == 0
    # the followed sequence is the doubling rule's on these curves
    cur, CF, CR, seq = None, 0.0, 0.0, []
    for a, b in zip(fp, cr):
        CF_t, CR_t = CF + a, CR + b
        if cur is None:
            cur = "F" if CF_t <= CR_t else "R"
        prev, inc, Cy = (CF, a, CR_t) if cur == "F" else (CR, b, CF_t)
        if prev + inc > G2 * Cy + 1e-12:
            cur = "R" if cur == "F" else "F"
        CF, CR = CF_t, CR_t
        seq.append(cur)
    got = [w for w, t0, n in rep["followed"] for _ in range(n)]
    assert got == seq
