"""Tests of policy A6, Sublet (design/sim_spec_ms2.md §14; §17.2 test_a6.py).

A6 runs through the registry (drivers.run.make_policy) on configs/ms2_multi_small.json (one day, three
inline trace lenders with two layer sites each, two LLMs, two regions, protected per region) and on
from_core instances of the T4/O1 family (`fixtures.o1_case`). The report fields checked are those
§14 lists (PD, rounder, execution layer, handler, combiner, redundancy); the names of the handler's
and the combiner's parts ('handler', 'combiner') and of the site-rule report under 'exec' are those
of the build, since §14 does not name them.
"""
from __future__ import annotations

import numpy as np
import pytest

from fixtures import policy_actions_recorder

from sublet import calib
from sublet.algos.contracts import p1_mask, p3_mask
from sublet.algos.rounding import rbar_theory
from sublet.drivers.run import make_policy
from sublet.engine import EngineConfig, simulate
from sublet.instance import build_instance, from_core, public_view, units
from sublet.paths import CONFIGS
from sublet.types import Buy, LenderModel

CFG = CONFIGS / "ms2_multi_small.json"


def _a6(inst, params=None, inputs=None):
    return make_policy({"policy": {"id": "A6", "params": dict(params or {})}}, inst, inputs=inputs)


def _run(inst, pol, information="I1", seed=0):
    res = simulate(inst, pol, LenderModel(schedule="trace", information=information),
                   EngineConfig(auto_drain=False, check_invariants=True), lender_seed=seed, policy_seed=seed)
    assert not res.invariant_failures, res.invariant_failures[:5]
    return res


@pytest.fixture(scope="module")
def multi():
    return build_instance(CFG)


# ---------------------------------------------------------------- smoke
@pytest.mark.parametrize("information", ["I1", "I2"])
def test_smoke(multi, information):
    """§14 on ms2_multi_small.json, one day: the run completes with empty invariant_failures, only P1
    actions, and the report merges the PD (P, dual, d, 'pd' statistics), the rounder (rbar, cost_pr,
    cost_an), the execution layer ('exec'), the handler, the combiner and the redundancy rule; marking
    is on under I2 only."""
    assert multi.grid.horizon_min == 1440
    pol = policy_actions_recorder(_a6(multi))
    res = _run(multi, pol, information)
    rep = res.metrics["policy"]
    kinds = {type(a).__name__ for _, a in pol.actions}
    assert "Buy" in kinds and kinds <= {"Buy", "Release", "Drain", "SetAdmission"}, kinds
    assert all(a.n_replicas == 1 for _, a in pol.actions if isinstance(a, Buy))
    for key in ("P", "dual", "dual_feasibility", "d", "rbar", "cost_pr", "cost_an", "pd", "exec", "handler",
                "combiner", "redundancy"):
        assert key in rep, key
    assert rep["rbar"] == 1 and rep["d"] == multi.m * multi.K + 1
    assert rep["pd"]["requests"] > 0 and rep["exec"]["purchases_total"] >= 0
    assert rep["marking"] == ("on (I2)" if information == "I2" else "off (I1)")
    assert res.metrics["gpu_only_lease_slots"] == 0
    assert len(res.leases) > 0
    for L in res.leases:
        assert L.gpus in {x.g for x in multi.llms}


# ---------------------------------------------------------------- component toggles
def _offered(view):
    m, K = np.asarray(view.price).shape
    off = np.zeros((m, K), dtype=bool)
    for l, s in enumerate(view.sites):
        for k in s.menu:
            off[l, k] = np.isfinite(view.price[l, k])
    return off


def test_components_toggle(multi):
    """§14: redundancy 'off' / 'rule' / 'always2', contract rules [] / [P1, P3] and variant practical /
    theory change exactly the parts they should: the candidate mask follows the contract rules only
    (P3 of P1's mask, or every offered pair), r-bar follows the variant only (1, or ceil(2 ln N) with the
    driver's N), spares follow the redundancy mode only (none with 'off'; with 'always2' one whenever a
    group has an exposed replica); runs without refusals have the same fractional P whatever the
    redundancy mode and the variant (the PD's input is the active units, M10)."""
    view = public_view(multi, "I1")
    off = _offered(view)
    J = multi.J
    m13 = p3_mask(view, p1_mask(view)) & off[:, None, :]
    N = max(len(units(multi).client) * multi.grid.T_slow, 3)
    runs = {}
    for name, params in (("base", {}), ("red_off", {"redundancy": "off"}), ("red_always2", {"redundancy": "always2"}),
                         ("rules_off", {"contract_rules": []}), ("theory", {"variant": "theory"})):
        pol = _a6(multi, params)
        res = _run(multi, pol)
        runs[name] = (pol, res, res.metrics["policy"])
    for name, (pol, res, rep) in runs.items():
        mask = np.asarray(pol.cand_mask, dtype=bool)
        want = np.repeat(off[:, None, :], J, axis=1) if name == "rules_off" else m13
        assert np.array_equal(mask, want), name
        assert rep["rbar"] == (rbar_theory(N) if name == "theory" else 1), name
        spares = [L for L in res.leases if L.tag == "spare"]
        red = rep["redundancy"]
        assert red["mode"] == {"red_off": "off", "red_always2": "always2"}.get(name, "rule"), name
        assert len(spares) <= red["buys"]
        if name == "red_off":
            assert spares == [] and red["buys"] == 0
        if name == "red_always2" and red["n_exp_total"] > 0:
            assert red["buys"] > 0
    assert not np.array_equal(m13, np.repeat(off[:, None, :], J, axis=1)), "the rules remove nothing here"
    base_rep = runs["base"][2]
    for name in ("red_off", "red_always2", "theory"):
        rep = runs[name][2]
        if base_rep["refused"] == 0 and rep["refused"] == 0:
            assert abs(rep["P"] - base_rep["P"]) <= 1e-9 * max(1.0, abs(base_rep["P"])), name


# ---------------------------------------------------------------- marking under I2
def test_marking_under_i2():
    """§8.3 in A6 on from_core of the o1_case instances with (m, rho, tau, H) = (8, 32, 2, 1) under I2:
    calib.rho on the window L_k = tau + H equals the family's rho = 32, 2 h_8 + 1 = 6.436 < 32
    (c3/o1/out/o1_ub.txt (b), rows '8 32'), so the default marking='auto' selects marking for every mark
    group; with marking='off' A6 rotates by X3's round robin, and the two runs place their leases
    differently on some schedule. Under I1 marking is off."""
    from fixtures import o1_case
    H8 = sum(1.0 / i for i in range(1, 9))
    assert f"{2 * H8 + 1:.3f}" == "6.436"
    differ = 0
    n = 0
    for seed in (0, 1):
        F, sch = o1_case(8, 32, 2, 1, seed)
        for name, om in sch:
            if name == "adaptiveRR":
                continue
            inst, _ = from_core(F.core_instance(), om)
            view = public_view(inst, "I2")
            rho = calib.rho(float(view.beta_tilde_usd[0, 0, 0]), 1, float(view.price[0, 0]),
                            (F.tau + F.H) * inst.grid.slow_min)
            assert abs(rho - 32.0) <= 1e-9
            res_on = _run(inst, _a6(inst), "I2")
            rep = res_on.metrics["policy"]
            assert rep["marking"] == "on (I2)"
            sr = rep["exec"]["site_rule"]
            assert sr["rule"] == "marking"
            assert sr["groups_detail"], (seed, name)
            for g in sr["groups_detail"]:
                assert g["mode"] == "marking" and abs(g["rho_P"] - 32.0) <= 1e-9, g
            res_off = _run(inst, _a6(inst, {"marking": "off"}), "I2")
            rep_off = res_off.metrics["policy"]
            assert rep_off["marking"] == "off" and rep_off["exec"]["site_rule"]["rule"] == "rr"
            sites_on = [(L.start_slot, L.site) for L in sorted(res_on.leases, key=lambda L: (L.start_slot, L.id))]
            sites_off = [(L.start_slot, L.site) for L in sorted(res_off.leases, key=lambda L: (L.start_slot, L.id))]
            differ += sites_on != sites_off
            n += 1
    assert n == 16 and differ > 0
    F, sch = o1_case(8, 32, 2, 1, 0)
    inst, _ = from_core(F.core_instance(), sch[3][1])
    rep_i1 = _run(inst, _a6(inst), "I1").metrics["policy"]
    assert rep_i1["marking"] == "off (I1)" and rep_i1["exec"]["site_rule"]["rule"] == "rr"


# ---------------------------------------------------------------- refusals
def test_refused_window_not_retried():
    """§14 step 1 with §6.5 and §7.2 step 7 (M11), as test_execution::test_a3_refused_window_not_retried for
    A6: a refused layer purchase at its column's own site refuses the realized PD column, and its window leaves
    the slot's coverage, so the slot stages no purchase in that window later (unless another opened window of
    the slot covers the slot). Seeds 0-2 on two settings:
    - the toy with 1-GPU sites (pre-check drops): no lender announces, so every refusal is a slot's lease
      purchase at its own site and drops a window (exec 'windows_dropped' = realized 'refused_to_rounder' =
      the planner's refusals > 0, none rotated or unmatched);
    - ms2_multi_small, 12 h, on_unavailable='refuse' (engine refusals, rotated sites): at most one window
      dropped per column refused, and some window is dropped."""
    from fixtures import capped_toy_instance, load_json, purchases_in_refused_windows, refusal_recorder
    cfg = load_json(CFG)
    cfg["time"]["horizon_min"] = 720
    cases = (("toy capped", capped_toy_instance(), LenderModel()),
             ("ms2 refuse 12h", build_instance(cfg), LenderModel(on_unavailable="refuse")))
    ecfg = EngineConfig(auto_drain=False, check_invariants=True)
    for name, inst, model in cases:
        n_drop = 0
        for s in range(3):
            pol = _a6(inst)
            rec = refusal_recorder(pol)
            res = simulate(inst, pol, model, ecfg, policy_seed=s)
            tag = (name, s)
            assert res.invariant_failures == [], tag
            rep = res.metrics["policy"]
            ex, re_ = rep["exec"], rep["realized"]
            assert re_["refused_to_rounder"] == len(rec["refused"]), (tag, re_)
            assert ex["windows_dropped"] <= re_["refused_to_rounder"], (tag, ex["windows_dropped"], re_)
            if name == "toy capped":
                assert ex["windows_dropped"] == re_["refused_to_rounder"] > 0, (tag, ex["windows_dropped"], re_)
                assert re_["refused_rotated"] == re_["refused_unmatched"] == 0, (tag, re_)
            n_drop += ex["windows_dropped"]
            bad = purchases_in_refused_windows(rec)
            assert bad == [], (tag, bad[:5])
        assert n_drop > 0, name


# ---------------------------------------------------------------- informative: the PD policies' cost
def test_pd_cost_diag():
    """Informative (nothing asserted about the values): A2 (r-bar 1 and theory), A3 and A6 on
    ms2_multi_small (config seed 3, policy seed 0) next to BL0a and BL1. Per PD policy it writes to
    ms2_checks/pd_cost_diag.json the engine components, the totals over BL0a's and BL1's, the PD's accounting
    (P, dual, cost_pr, cost_an, fix-ups, the all-fallback accounting sum q_req over the requests), the minimum
    over requests of min over the closed candidates of (C_F + delta) / q_req (the practical fix-up fires only
    below 1, §6.2), the fallback share and the replica utilization (metrics.run_metrics)."""
    import json
    from fixtures import ms2_checks_dir
    from sublet.metrics import run_metrics
    cfg = dict(__import__("fixtures").load_json(CFG))
    cfg["seed"] = 3
    inst = build_instance(cfg)
    model, ecfg = LenderModel(schedule="trace"), EngineConfig(auto_drain=False, check_invariants=True)
    base = {}
    for pid in ("BL0a", "BL1"):
        r = simulate(inst, make_policy({"policy": {"id": pid, "params": {}}}, inst), model, ecfg, policy_seed=0)
        assert not r.invariant_failures
        base[pid] = r.components["total"]
    rows = []
    for pid, params in (("A2", {}), ("A2", {"rbar": "theory"}), ("A3", {}), ("A6", {})):
        pol = make_policy({"policy": {"id": pid, "params": params}}, inst)
        acc = {"n": 0, "q_sum": 0.0, "min_ratio": float("inf"), "n_below_1": 0}
        o_reset = pol.reset

        def reset(view, rng, pol=pol, acc=acc, o_reset=o_reset):
            o_reset(view, rng)
            rd = pol.planner.rounder
            o_proc = rd.process

            def process(out, unit=None):
                rd._ensure(rd.pd.n_ids)
                closed = ~rd._open[out.cols]
                acc["n"] += 1
                acc["q_sum"] += float(out.q)
                if closed.any():
                    v = float(np.min((out.C + out.delta)[closed]) / out.q)
                    acc["min_ratio"] = min(acc["min_ratio"], v)
                    acc["n_below_1"] += v < 1.0
                return o_proc(out, unit)
            rd.process = process
        pol.reset = reset
        res = simulate(inst, pol, model, ecfg, policy_seed=0)
        assert not res.invariant_failures, pid
        rep = res.metrics["policy"]
        assert acc["n"] == rep["pd"]["requests"]
        rm = run_metrics(res, inst)
        rows.append({"policy": pid, "params": params, "components": res.components,
                     "total_over_BL0a": res.components["total"] / base["BL0a"],
                     "total_over_BL1": res.components["total"] / base["BL1"],
                     "P": rep["P"], "dual": rep["dual"], "cost_pr": rep["cost_pr"], "cost_an": rep["cost_an"],
                     "fixups": rep["fixups"], "n_fix_an": rep["n_fix_an"], "requests": acc["n"],
                     "all_fallback_accounted": acc["q_sum"], "min_closed_CFdelta_over_q": acc["min_ratio"],
                     "requests_with_closed_ratio_below_1": acc["n_below_1"], "opened": rep["opened"],
                     "fallback_share": rm["fallback_share"], "replica_utilization": rm["replica_utilization"],
                     "leases": len(res.leases)})
    out = ms2_checks_dir() / "pd_cost_diag.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"description": "PD policies' engine cost against BL0a and BL1 and the PD's own "
                                              "accounting on ms2_multi_small (config seed 3, policy seed 0); "
                                              "informative (tests/test_a6.py::test_pd_cost_diag)",
                               "baselines": base, "rows": rows}, indent=1, default=float) + "\n")
    assert len(json.loads(out.read_text())["rows"]) == 4
