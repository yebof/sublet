"""Tests of policy A1, C2's single-site rule in the engine (design/sim_spec_ms2.md §9.2-§9.4, §17.2 test_a1.py).

Instances are `fixtures.onesite_c2` (one synthetic revocable site 'R' with an explicit announcement
set, one protected site 'P', one client, Δs = Δf, explicit load times). Expected purchase and
commit slots are computed from the PublicView with the formulas of §9.2 and §9.4 and with
`timing.latest_prewarm_slot`; the insurance tests count the calls of `c2rule.cr_react_lb` (the
LB_react of §9.3) by wrapping it.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from fixtures import A0, Q_GPU, explicit_client, ms2_checks_dir, onesite_c2, site_index, toy_config, toy_instance

from sublet.algos import c2rule
from sublet.algos.a1 import A1
from sublet.algos.c2rule import AlgStarRule, C2Units, c2_thresholds, c2_units, insure_up_front
from sublet.algos.common import PolicyError
from sublet.drivers.run import make_policy
from sublet.engine import EngineConfig, simulate
from sublet.instance import build_instance, public_view
from sublet.paths import import_c2
from sublet.timing import latest_prewarm_slot
from sublet.types import LenderModel

E2_H_MIN = (0, 1, 2, 5, 10, 15, 30, 60, 120, 240)      # E2's notice grid (design Table 5.6)


def _view(inst, information="I1"):
    return public_view(inst, information)


def _reset(pol, inst, information="I1"):
    pol.reset(_view(inst, information), np.random.default_rng(0))
    return pol


def _run(inst, pol, **kw):
    res = simulate(inst, pol, LenderModel(schedule="trace", information=kw.pop("information", "I1")),
                   EngineConfig(auto_drain=False, check_invariants=True), policy_seed=0)
    assert not res.invariant_failures, res.invariant_failures[:5]
    return res


def _sites(inst):
    return site_index(inst, "R"), site_index(inst, "P"), [c.id for c in inst.contracts]


def _n_s0(view, l, k, mode="ceil"):
    """n_s0 of §9.4 from the view: s0_min = 60 beta~ / (q_j - g_j a_lk), rounded up (or down) to slow slots."""
    j = 0
    bt = float(view.beta_tilde_usd[j, l, k])
    q, g = view.llms[j].q_usd_per_h, view.llms[j].g
    s0_min = 60.0 * bt / (q - g * float(view.price[l, k]))
    x = s0_min / view.grid.slow_min
    return (math.ceil(x) if mode == "ceil" else math.floor(x)), s0_min


def _buys(res, tag_prefix):
    return sorted(L.start_slot for L in res.leases if L.tag.startswith(tag_prefix))


# ---------------------------------------------------------------- domain
def test_domain_errors():
    """§9.4 domain: a multi-client instance, two revocable sites, two revocable contracts without
    contract_rev and a revocable contract with g_j a >= q_j (M59) raise PolicyError at reset; with
    contract_rev the two-contract case runs; BL7(A1) resets in RRL mode with rep_site = l_r (lambda of
    the revocable site, a number) and status 'RRL'."""
    d24 = [1.0] * 24
    cfg = toy_config(sites=["L0", "P"])
    cfg["borrowers"]["clients"] = [explicit_client(d24), explicit_client(d24, borrower="b1")]
    with pytest.raises(PolicyError):
        _reset(A1(), build_instance(cfg))
    with pytest.raises(PolicyError):                                   # toy: L0 and L1 are revocable
        _reset(A1(), toy_instance())
    demand = [1.0] * 12
    two = [("r1", 5, 5, A0), ("r2", 5, 60, A0)]
    inst, _ = onesite_c2(demand, rev_contracts=two)
    with pytest.raises(PolicyError):
        _reset(A1(), inst)
    pol = _reset(A1(contract_rev="r2", insure="never"), inst)
    assert pol.report()["sites"]["rev"][1] == [c.id for c in inst.contracts].index("r2")
    res = _run(inst, A1(contract_rev="r2", insure="never"))
    assert {inst.contracts[L.contract].id for L in res.leases if L.tag.startswith("a1")} <= {"r2", "prot"}
    inst_hi, _ = onesite_c2(demand, a_rev=Q_GPU + 0.35)                # g a = 7.5 >= q_j = 7.15
    with pytest.raises(PolicyError):
        _reset(A1(), inst_hi)
    # BL7(A1): RRL mode, the cold re-buy loads at l_r
    inst, _ = onesite_c2(demand, lam_rev=300.0, lam_prot=600.0)
    l_r, l_p, ids = _sites(inst)
    bl7 = make_policy({"policy": {"id": "BL7", "params": {"inner": "A1", "inner_params": {"insure": "never"}}}}, inst)
    _reset(bl7, inst)
    rep = bl7.report()
    inner = rep.get("inner", rep)
    assert inner["rrl"] is True and inner["status"] == "RRL", inner
    u = inner["units"]
    view = _view(inst)
    k_r = ids.index("rev")
    bt = float(view.beta_tilde_usd[0, l_r, k_r])
    lam_r = (float(view.lam_s[0, l_r]) / 3600.0) * view.llms[0].q_usd_per_h / bt
    assert u["ap"] is None and u["bw"] is None
    assert isinstance(u["lam"], float) and math.isfinite(u["lam"]) and abs(u["lam"] - lam_r) <= 1e-12 * lam_r
    assert inner["insured"] is False and inner["reaction"] == "cold"


# ---------------------------------------------------------------- purchase slot
@pytest.mark.parametrize("mode", ["ceil", "floor"])
def test_purchase_slot(mode):
    """§9.4 steps 4 and 7: the revocable purchase comes n_s0 slots after each episode start, n_s0 =
    ceil (or floor) of s0_min / Δs with s0_min = 60 beta~ / (q_j - g_j a) from the view (M28); the
    gaps between episodes outlast the billed term, so every episode starts without a lease."""
    on = [(1, 7), (12, 20), (25, 31)]                       # episodes [start, end) in slow slots
    T = 36
    demand = [0.0] * T
    for a, b in on:
        demand[a:b] = [1.0] * (b - a)
    inst, _ = onesite_c2(demand, lam_rev=300.0, lam_prot=300.0)
    l_r, l_p, ids = _sites(inst)
    view = _view(inst)
    n, s0_min = _n_s0(view, l_r, ids.index("rev"), mode)
    assert math.ceil(s0_min / 5) != math.floor(s0_min / 5), s0_min        # the two modes differ here
    assert all(b - a > n for a, b in on)
    res = _run(inst, A1(insure="never", s0_round=mode))
    assert _buys(res, "a1") == [a + n for a, _ in on]
    assert all(inst.contracts[L.contract].id == "rev" and L.site == l_r for L in res.leases)
    assert res.metrics["policy"]["n_s0"] == n


def test_units_default_calibration():
    """§9.2 at beta_jl = 0, phi = 1, price a0 and lambda' = lambda: lambda = 1/(alpha + phi) and
    bw = alpha_p / (alpha + phi) (1e-12); A1's reset maps the same units."""
    inst, _ = onesite_c2([1.0] * 12, a_rev=A0, a_prot=5.97, lam_rev=300.0, lam_prot=300.0)
    assert inst.phi_load == 1.0 and not inst.beta_usd.any()
    l_r, l_p, ids = _sites(inst)
    view = _view(inst)
    u = c2_units(view, 0, l_r, ids.index("rev"), l_prot=l_p, k_prot=ids.index("prot"), rep_site=l_p)
    al, ap = A0 / Q_GPU, 5.97 / Q_GPU
    assert abs(u.alpha - al) <= 1e-12 and abs(u.ap - ap) <= 1e-12
    assert abs(u.lam - 1 / (al + 1.0)) <= 1e-12 and abs(u.bw - ap / (al + 1.0)) <= 1e-12
    rep = _reset(A1(insure="never"), inst).report()
    for f in ("alpha", "ap", "lam", "bw", "mu", "H"):
        assert abs(rep["units"][f] - getattr(u, f)) <= 1e-12 * max(1.0, abs(getattr(u, f))), f


# ---------------------------------------------------------------- notices
def test_prewarm_and_cold_paths():
    """§9.4 steps 1, 5, 6 and §10: with a warm reaction the protected Buy comes at
    latest_prewarm_slot(r, E, lambda'_ms) iff demand is on there; a notice shorter than the
    replacement's load is cold, and the clock restarts at the death (M29), so the next revocable
    purchase comes n_s0 slots after the death slot."""
    T = 40
    r = 6
    # feasible pre-warm: H = 60 min, lambda' = 300 s; demand on throughout
    inst, _ = onesite_c2([1.0] * T, [r], H_min=60, lam_rev=300.0, lam_prot=300.0)
    l_r, l_p, ids = _sites(inst)
    view = _view(inst)
    n, _ = _n_s0(view, l_r, ids.index("rev"))
    assert r >= n + 1                                         # the lease is past its guaranteed period at r
    E = r * 5 + 60
    t_c = latest_prewarm_slot(r, E, int(round(1000 * view.lam_s[0, l_p])), view.grid)
    assert t_c is not None and r <= t_c < T
    res = _run(inst, A1(reaction="prewarm_if_feasible", insure="never"))
    assert _buys(res, "a1:prewarm") == [t_c]
    pre = [L for L in res.leases if L.tag.startswith("a1:prewarm")][0]
    assert pre.site == l_p and inst.contracts[pre.contract].id == "prot"
    # the same notice with demand off in slot t_c (on before and after): no pre-warm
    d = [1.0] * T
    d[t_c] = 0.0
    inst2, _ = onesite_c2(d, [r], H_min=60, lam_rev=300.0, lam_prot=300.0)
    res2 = _run(inst2, A1(reaction="prewarm_if_feasible", insure="never"))
    assert _buys(res2, "a1:prewarm") == []
    # infeasible: H = 10 min < lambda' = 900 s: cold; death at E = 5 r + 10, dead from slot r + 2
    inst3, _ = onesite_c2([1.0] * T, [r], H_min=10, lam_rev=300.0, lam_prot=900.0)
    l_r3, l_p3, ids3 = _sites(inst3)
    view3 = _view(inst3)
    n3, _ = _n_s0(view3, l_r3, ids3.index("rev"))
    assert latest_prewarm_slot(r, r * 5 + 10, int(round(1000 * view3.lam_s[0, l_p3])), view3.grid) is None
    res3 = _run(inst3, A1(reaction="prewarm_if_feasible", insure="never"))
    assert _buys(res3, "a1:prewarm") == []
    death_slot = -(-(r * 5 + 10) // 5)
    assert _buys(res3, "a1") == [n3, death_slot + n3]
    first = min(res3.leases, key=lambda L: L.start_slot)
    assert first.end_cause == "reclaim" and first.death_min == r * 5 + 10


# ---------------------------------------------------------------- insurance (C2-T2, §9.3)
def _units(alpha, ratio, H, mu=1.0, rrl=False):
    lam = 1 / (alpha + 1.0)
    ap = None if rrl else ratio * alpha
    return C2Units(alpha=alpha, ap=ap, mu=mu, lam=lam, bw=None if rrl else ap / (alpha + 1.0), H=H,
                   beta_tilde_usd=1.0, time_unit_h=300.0 * (alpha + 1.0) / 3600.0)


def _e2_H(alpha, lam_s=300.0):
    """E2's notices in C2 units: H = (H_min / 60) q_j / beta~ with beta~ = lam (g a + phi q_j) / 3600, phi = 1."""
    return [h * 60.0 / (lam_s * (alpha + 1.0)) for h in E2_H_MIN]


@pytest.fixture
def lb_calls(monkeypatch):
    calls = []
    orig = c2rule.cr_react_lb

    def counted(units):
        calls.append(units)
        return orig(units)
    monkeypatch.setattr(c2rule, "cr_react_lb", counted)
    return calls


def test_insurance_c2t2(lb_calls):
    """§9.3 at alpha = 0.4: alpha_p / alpha in {1.1, 1.25, 1.5} (alpha_p <= alpha (2 - alpha)) insure at every
    notice of E2's grid by the first clause, without an LB_react call; {2, 2.5} do not insure at H* and
    H* + 0.5 (four calls); without a protected contract (RRL) A1 never insures (no call)."""
    al = 0.4
    for ratio in (1.1, 1.25, 1.5):
        assert ratio * al <= al * (2 - al)
        for H in _e2_H(al):
            assert insure_up_front(_units(al, ratio, H), "lb_react") is True
    assert lb_calls == []
    for ratio in (2.0, 2.5):
        u0 = _units(al, ratio, 0.0)
        Hs = c2_thresholds(u0.alpha, u0.ap, u0.mu, u0.lam, 1.0, u0.bw).Hstar
        for H in (Hs, Hs + 0.5):
            assert insure_up_front(_units(al, ratio, H), "lb_react") is False, (ratio, H)
    assert len(lb_calls) == 4
    for H in _e2_H(al):
        assert insure_up_front(_units(al, None, H, rrl=True), "lb_react") is False
    assert len(lb_calls) == 4
    assert insure_up_front(_units(al, 2.0, 1.0), "always") is True
    assert insure_up_front(_units(al, 1.1, 1.0), "never") is False


@pytest.mark.slow
def test_insurance_grid(lb_calls, capsys):
    """§9.3: alpha_p / alpha in {2, 2.5} at every notice of E2's grid (one LB_react call each); no insurance
    at H >= H* (C2-T4: LB_react is within grid error of 2 - alpha there); the insuring notices are reported."""
    al = 0.4
    insuring = []
    for ratio in (2.0, 2.5):
        u0 = _units(al, ratio, 0.0)
        Hs = c2_thresholds(u0.alpha, u0.ap, u0.mu, u0.lam, 1.0, u0.bw).Hstar
        for h_min, H in zip(E2_H_MIN, _e2_H(al)):
            ins = insure_up_front(_units(al, ratio, H), "lb_react")
            if ins:
                insuring.append((ratio, h_min, round(H, 4)))
            if H >= Hs:
                assert ins is False, (ratio, h_min, H, Hs)
    assert len(lb_calls) == 2 * len(E2_H_MIN)
    with capsys.disabled():
        print(f"\n[test_insurance_grid] insuring notices (alpha_p/alpha, H_min, H in C2 units): {insuring}")


# ---------------------------------------------------------------- engine decisions vs ALG*
def test_engine_decisions_match_rule():
    """§9.4, §10 at Δs = Δf = 1 min with an explicit R: the engine run's revocable purchase minute, its
    reaction (cold: no protected purchase before the death; warm: a pre-warm) and the commit minute
    equal AlgStarRule's plan mapped to minutes (purchase at ceil(s0), commit at floor(R - lambda)). The
    episode is one translation of C2's: the cold case ends the demand at E + n_s0, before A1's restarted
    clock (M29) would buy a second lease. Engine total minus c2_plan_cost (USD) equals the translation
    terms (1e-9): s0 rounding (q - g a)(n - s0)/60, the fallback minutes of the load
    q (ceil(lam_r/60)/60 - lam_r/3600), minus the load-time rent g a lam_r/3600 that beta~ holds while C2
    charges alpha (x - s) from s, and for the pre-warm the commit rounding g a_p ((E - t_c)/60 - lam_p/3600).
    Both totals and the terms go to ms2_checks/a1_translation.json (informative)."""
    c2 = import_c2()
    from sublet.harness.c2_harness import c2_plan_cost
    out = []
    T, H = 200, 40
    for mu_ratio, react in ((1.0, "cold"), (2.0, "warm")):
        probe, _ = onesite_c2([1.0] * T, (), slot_min=1, rev_contracts=[("rev", 1, H, A0)], lam_rev=300.0,
                              lam_prot=300.0, mu_over_beta_tilde=mu_ratio)
        l_r, l_p, ids = _sites(probe)
        view = _view(probe)
        k_r, k_p = ids.index("rev"), ids.index("prot")
        u = c2_units(view, 0, l_r, k_r, l_prot=l_p, k_prot=k_p, rep_site=l_p)
        th = c2_thresholds(u.alpha, u.ap, u.mu, u.lam, 1.0, u.bw)
        assert th.react == react, (mu_ratio, th)
        s_min = u.to_min(th.s0)
        n = math.ceil(s_min - 1e-9)
        r = n + 30                                   # the notice comes after the purchase and its guaranteed period
        E = r + H
        x_end = E + n if react == "cold" else 150    # cold: the demand ends before the restarted clock's purchase
        demand = [1.0] * x_end + [0.0] * (T - x_end)
        inst, _ = onesite_c2(demand, [r], slot_min=1, rev_contracts=[("rev", 1, H, A0)], lam_rev=300.0,
                             lam_prot=300.0, mu_over_beta_tilde=mu_ratio)
        res = _run(inst, A1(insure="never"))
        to_c2 = 1.0 / (60.0 * u.time_unit_h)
        rule = AlgStarRule.from_thresholds(th, u.lam)
        plan = rule.plan(E * to_c2, u.H)
        rev = sorted((L for L in res.leases if L.tag == "a1"), key=lambda L: L.start_slot)
        assert len(rev) == 1 and rev[0].start_slot == n, ([L.start_slot for L in rev], n)
        pre = [L for L in res.leases if L.tag.startswith("a1:prewarm")]
        q, g = view.llms[0].q_usd_per_h, view.llms[0].g
        a_r, a_p = float(view.price[l_r, k_r]), float(view.price[l_p, k_p])
        lam_r, lam_p = float(view.lam_s[0, l_r]), float(view.lam_s[0, l_p])
        terms = {"s0_rounding": (q - g * a_r) * (n - s_min) / 60.0,
                 "load_fallback_rounding": q * (math.ceil(lam_r / 60.0) / 60.0 - lam_r / 3600.0),
                 "load_rent_in_beta_tilde": -g * a_r * lam_r / 3600.0}
        if plan[0] == "react-cold":
            assert react == "cold" and pre == [] and rev[0].death_min == E
        else:
            assert plan[0] == "react-warm" and react == "warm"
            d_min = u.to_min(plan[3])
            t_c = latest_prewarm_slot(r, E, int(round(1000 * view.lam_s[0, l_p])), inst.grid)
            assert [L.start_slot for L in pre] == [t_c] and t_c == math.floor(d_min + 1e-9), (pre, t_c, d_min)
            terms["commit_rounding"] = g * a_p * ((E - t_c) / 60.0 - lam_p / 3600.0)
        P = c2.model.Params(mu=u.mu, alpha=u.alpha, ap=u.ap, H=u.H, lam=u.lam)
        c2_cost = float(np.asarray(c2_plan_cost(plan, E * to_c2, np.array([x_end * to_c2]), P, bw=u.bw))[0])
        diff = res.components["total"] - c2_cost * u.beta_tilde_usd
        pred = sum(terms.values())
        assert abs(diff - pred) <= 1e-9 * max(1.0, abs(pred)), (react, diff, pred, terms)
        out.append({"mu_over_beta_tilde": mu_ratio, "reaction": react, "plan": [str(plan[0])] + [float(v) for v in plan[1:]],
                    "purchase_min": rev[0].start_slot, "s0_min": s_min, "notice_min": r, "death_min": E,
                    "commit_min": [L.start_slot for L in pre], "x_end_min": x_end,
                    "engine_total_usd": res.components["total"], "c2_plan_cost_usd": c2_cost * u.beta_tilde_usd,
                    "difference_usd": diff, "predicted_difference_usd": pred, "difference_terms_usd": terms,
                    "components": res.components, "units": {f: getattr(u, f) for f in ("alpha", "ap", "mu", "lam",
                                                                                         "bw", "H", "beta_tilde_usd",
                                                                                         "time_unit_h")}})
    path = ms2_checks_dir() / "a1_translation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"meta": {"test": "tests/test_a1.py::test_engine_decisions_match_rule",
                                         "spec": "design/sim_spec_ms2.md §17.2 (informative)",
                                         "setting": "onesite_c2, Δs = Δf = 1 min, tau = 1 min, H = 40 min, "
                                                    "lambda = lambda' = 300 s, price a0, insure 'never'; one "
                                                    "revocable purchase per run (cold: demand ends at E + n_s0)"},
                                "runs": out}, indent=1) + "\n")


# ---------------------------------------------------------------- further cases of §9.2-§9.4
def test_units_stranding():
    """§9.2 (S22): mu = (mu_fb + pi (W_f - H_k)^+) / beta~: with W_f < H_k the SLO term is 0 (mu_fb / beta~),
    with W_f > H_k it adds pi (W_f - H_k)."""
    inst, _ = onesite_c2([1.0] * 12, H_min=60)
    l_r, l_p, ids = _sites(inst)
    k_r, k_p = ids.index("rev"), ids.index("prot")
    from fixtures import with_stranding
    for W_f, want_usd in ((5.0, 1.0), (60.0, 1.0), (90.0, 1.0 + 0.1 * 30.0)):
        with_stranding(inst, mu_fb_usd=1.0, pi_usd_per_min=0.1, W_f_min=W_f)
        view = _view(inst)
        bt = float(view.beta_tilde_usd[0, l_r, k_r])
        u = c2_units(view, 0, l_r, k_r, l_prot=l_p, k_prot=k_p, rep_site=l_p)
        assert abs(u.mu - want_usd / bt) <= 1e-12 * (want_usd / bt), (W_f, u.mu, want_usd / bt)
    # mu_usd given: used as is
    u = c2_units(_view(inst), 0, l_r, k_r, l_prot=l_p, k_prot=k_p, rep_site=l_p, mu_usd=2.0)
    assert abs(u.mu - 2.0 / float(_view(inst).beta_tilde_usd[0, l_r, k_r])) <= 1e-12 * u.mu


def test_rep_site_is_protected_site():
    """§9.4 reset: A1 maps lambda and beta_w at rep_site = l_p (the protected replacement), not at l_r:
    lambda_r = 300 s, lambda_p = 600 s."""
    inst, _ = onesite_c2([1.0] * 12, lam_rev=300.0, lam_prot=600.0)
    l_r, l_p, ids = _sites(inst)
    view = _view(inst)
    want = c2_units(view, 0, l_r, ids.index("rev"), l_prot=l_p, k_prot=ids.index("prot"), rep_site=l_p)
    other = c2_units(view, 0, l_r, ids.index("rev"), l_prot=l_p, k_prot=ids.index("prot"), rep_site=l_r)
    assert want.lam != other.lam and want.bw != other.bw
    pol = _reset(A1(insure="never"), inst)
    assert pol.units.lam == want.lam and pol.units.bw == want.bw


def test_insured_path():
    """§9.4 step 7 (C2-T2's INS): an insured A1 buys the protected contract at l_p n_s0 slots into each
    episode, holds no revocable lease, never reacts (insure='always'; and by the first clause of §9.3 with
    alpha_p <= alpha (2 - alpha) under 'lb_react'); insure_up_front is False for alpha = 0."""
    on = [(1, 7), (12, 20), (25, 31)]
    T = 36
    demand = [0.0] * T
    for a, b in on:
        demand[a:b] = [1.0] * (b - a)
    for a_rev, insure in ((A0, "always"), (4.3, "lb_react")):
        inst, _ = onesite_c2(demand, [4, 15], a_rev=a_rev, a_prot=5.97)
        l_r, l_p, ids = _sites(inst)
        view = _view(inst)
        n, _ = _n_s0(view, l_r, ids.index("rev"))
        u = c2_units(view, 0, l_r, ids.index("rev"), l_prot=l_p, k_prot=ids.index("prot"), rep_site=l_p)
        if insure == "lb_react":
            assert u.ap <= u.alpha * (2 - u.alpha)
        res = _run(inst, A1(insure=insure))
        rep = res.metrics["policy"]
        assert rep["insured"] is True, insure
        tags = {L.tag for L in res.leases}
        assert tags == {"a1:insure"}, (insure, tags)
        assert all(L.site == l_p and inst.contracts[L.contract].id == "prot" for L in res.leases)
        assert _buys(res, "a1:insure") == [a + n for a, _ in on], (insure, _buys(res, "a1:insure"))
        assert rep["counts"]["notices"] == 0 and rep["counts"]["buy_rev"] == 0
    assert insure_up_front(C2Units(alpha=0.0, ap=0.5, mu=1.0, lam=0.5, bw=0.4, H=1.0, beta_tilde_usd=1.0,
                                   time_unit_h=1.0), "lb_react") is False


def test_release_rule():
    """§9.4 step 3 (M50): with release='after_prepaid' a revocable lease is kept through an off gap shorter
    than its billed term (no Release before prepaid_end_min) and serves the returning demand without a new
    purchase; it is released in the first off slot at or after prepaid_end_min (equality included). With
    'immediate' it is released in the first off slot and the returning demand starts a new episode."""
    slot = 1
    probe, _ = onesite_c2([1.0] * 10, slot_min=slot, rev_contracts=[("rev", 1, 60, A0)])
    l_r, l_p, ids = _sites(probe)
    n, _ = _n_s0(_view(probe), l_r, ids.index("rev"))
    T = n + 100
    d = [1.0] * (n + 5) + [0.0] * 10 + [1.0] * 15 + [0.0] * (T - n - 30)
    inst, _ = onesite_c2(d, slot_min=slot, rev_contracts=[("rev", 1, 60, A0)])
    res = _run(inst, A1(insure="never"))
    rev = [L for L in res.leases if L.tag == "a1"]
    assert len(rev) == 1 and rev[0].start_slot == n and rev[0].prepaid_end_min == n + 61, rev
    assert rev[0].end_cause == "release" and rev[0].end_min == n + 61
    res_i = _run(inst, A1(insure="never", release="immediate"))
    rev_i = sorted((L for L in res_i.leases if L.tag == "a1"), key=lambda L: L.start_slot)
    assert [(L.start_slot, L.end_min, L.end_cause) for L in rev_i] == [(n, n + 5, "release"),
                                                                       (n + 15 + n, n + 30, "release")], rev_i
    # equality: on for [0, n + 2), billed term 10 min (Δs = 5): released at (n + 2) Δs exactly
    probe5, _ = onesite_c2([1.0] * 30)
    n5, _ = _n_s0(_view(probe5), *_sites(probe5)[:1], [c.id for c in probe5.contracts].index("rev"))
    end = n5 + 2
    inst5, _ = onesite_c2([1.0] * end + [0.0] * (30 - end))
    res5 = _run(inst5, A1(insure="never"))
    r5 = [L for L in res5.leases if L.tag == "a1"]
    assert len(r5) == 1 and r5[0].start_slot == n5 and r5[0].prepaid_end_min == end * 5
    assert r5[0].end_cause == "release" and r5[0].end_min == end * 5


def test_early_death_commits_now():
    """§9.4 step 1 (an addition): when the revocable lease dies (violation) before the pending pre-warm's
    commit slot, the commit moves to the death slot, so the protected lease is bought at once (no restart of
    the clock, no wait until t_c)."""
    from sublet.types import ActionResult, Buy, LeaseView, Notice, SlowObs
    T = 40
    inst, _ = onesite_c2([1.0] * T, H_min=60, lam_rev=300.0, lam_prot=300.0)
    l_r, l_p, ids = _sites(inst)
    view = _view(inst)
    k_r, k_p = ids.index("rev"), ids.index("prot")
    pol = _reset(A1(reaction="prewarm_if_feasible", insure="never"), inst)
    n = pol.n_s0

    def obs(t, leases=(), notices=(), ended=(), results=()):
        return SlowObs(t=t, minute=5 * t, demand=np.ones((1, 1)), leases={L.id: L for L in leases}, replicas={},
                       notices=list(notices), ended=list(ended), results=list(results), site_announced=None,
                       served_prev=np.zeros((1, inst.m)), fallback_prev=np.zeros(1), cost_so_far=0.0)
    acts = []
    for t in range(n):
        acts = pol.act(obs(t))
        assert acts == [], (t, acts)
    acts = pol.act(obs(n))
    assert acts == [Buy(l_r, k_r, 0, 1, tag="a1")]
    lv = LeaseView(5, l_r, k_r, 1, n, 5 * n, 5 * n + 65, None, None, ())
    assert pol.act(obs(n + 1, [lv], results=[ActionResult(0, acts[0], True, 5, (), "")])) == []
    r = n + 3
    E = 5 * r + 60
    lv_a = LeaseView(5, l_r, k_r, 1, n, 5 * n, 5 * n + 65, r, E, ())
    assert pol.act(obs(n + 2, [lv])) == []
    assert pol.act(obs(r, [lv_a], notices=[Notice(5, r, E)])) == []
    t_c = latest_prewarm_slot(r, E, int(round(1000 * view.lam_s[0, l_p])), view.grid)
    assert pol.pending == t_c and t_c > r + 1
    acts = pol.act(obs(r + 1, [], ended=[(5, 5 * r + 3, "violation")]))
    assert acts == [Buy(l_p, k_p, 0, 1, tag="a1:prewarm")], acts
    assert pol.pending is None and pol.report()["counts"]["revocations"] == 1
    assert pol.report()["counts"]["restarts"] == 0


def _two_prot_instance(demand, a_p2):
    """onesite_c2 with a second protected site 'P2' (a copy of 'P') whose protected price is a_p2."""
    from fixtures import with_capacity
    from sublet.types import INF
    cfg = toy_config(sites=["L0", "P"])
    cfg["time"] = {"slow_slot_min": 5, "fast_slot_min": 5, "horizon_min": 5 * len(demand), "start_minute_of_week": 0}
    cfg["prices"] = {"a0_usd_per_gpu_h": A0, "q_gpu_usd_per_gpu_h": Q_GPU, "a_protected_usd_per_gpu_h": 5.97,
                     "revocable_price": "explicit"}
    cfg["contracts"] = [{"id": "rev", "tau_min": 5, "H_min": 5}, {"id": "prot", "tau_min": None, "H_min": 0,
                                                                  "prepaid_min": 5}]
    L0, P = cfg["lenders"]
    L0.update({"id": "R", "group": "gR", "menu": ["rev"], "prices": {"rev": A0}, "R": [], "lam_s": 300.0})
    P.update({"lam_s": 300.0, "menu": ["prot"]})
    P2 = dict(P)
    P2.update({"id": "P2", "group": "gp2"})
    cfg["lenders"].append(P2)
    cfg["borrowers"]["clients"] = [explicit_client([float(v) for v in demand])]
    inst = build_instance(cfg)
    with_capacity(inst, {site_index(inst, "R"): INF})
    price = np.array(inst.price, dtype=float, copy=True)
    price[site_index(inst, "P2"), [c.id for c in inst.contracts].index("prot")] = a_p2
    inst.price = price
    return inst


def test_site_prot_and_i2_wait():
    """§9.4: A1 uses the cheapest protected contract by default and the one at `site_prot` if given (here the
    dearer site P2); i2_wait=True under I2 holds back the revocable purchase while site_announced[l_r]
    (one slot later when l_r is announced at n_s0), the default buys at n_s0 (M22)."""
    inst = _two_prot_instance([1.0] * 20, a_p2=6.5)
    kp = [c.id for c in inst.contracts].index("prot")
    lp, lp2 = site_index(inst, "P"), site_index(inst, "P2")
    assert _reset(A1(insure="never"), inst).report()["sites"]["prot"] == [lp, kp]
    rep = _reset(A1(insure="never", site_prot="P2"), inst).report()
    assert rep["sites"]["prot"] == [lp2, kp] and abs(rep["units"]["ap"] - 6.5 / Q_GPU) <= 1e-12
    res = _run(inst, A1(insure="always", site_prot="P2"))
    assert {L.site for L in res.leases} == {lp2}
    probe, _ = onesite_c2([1.0] * 30)
    b = _reset(A1(insure="never"), probe).n_s0
    inst2, _ = onesite_c2([1.0] * 30, [b])
    res_w = _run(inst2, A1(insure="never", i2_wait=True), information="I2")
    assert min(L.start_slot for L in res_w.leases if L.tag == "a1") == b + 1
    res_0 = _run(inst2, A1(insure="never"), information="I2")
    assert min(L.start_slot for L in res_0.leases if L.tag == "a1") == b
    res_1 = _run(inst2, A1(insure="never", i2_wait=True), information="I1")      # no site_announced under I1
    assert min(L.start_slot for L in res_1.leases if L.tag == "a1") == b
