"""Tests of practical Sublet's knobs (design/q44_practical_sublet.md §2, §6.1 item 1, §6.3 test_q44_knobs.py).

The knobs are parameters of A2Planner (`px`: K kstar_only, S suppress_covered, O layer_order; R renew_live and
F renew_profit through a2.live_renewals) and of A6 (`px`, passed to the planner and the execution layer),
every one off by default. A2 and A3 take no `px` (§6.1 lists the knobs for a2.py's planner and a6.py only);
A3's knobs-off identity is checked with its planner built with every key False.
Oracles: the build's runs and code/sim/out/ms2_checks/pd_cost_diag.json (V1 of §5.5: A6 787.10, A3 736.12,
A2 747.96 USD on ms2_multi_small, config seed 3, policy seed 0), the knob-off runs, and hand computations.
"""
from __future__ import annotations

import numpy as np
import pytest

from fixtures import (c4l_b, core_case, load_json, onesite_c2, policy_actions_recorder, toy_config, toy_instance,
                      with_capacity)

from sublet.algos.a2 import PX_KEYS, A2Planner, resolve_px
from sublet.algos.a6 import A6
from sublet.algos.a7 import PracticalSublet
from sublet.algos.common import PolicyError, column_cost, policy_streams
from sublet.algos.pd_core import RequestOrder
from sublet.drivers.run import make_policy
from sublet.engine import EngineConfig, simulate
from sublet.instance import build_instance, from_core, public_view
from sublet.paths import CONFIGS
from sublet.types import INF, Buy, LenderModel, SlowObs

MULTI = CONFIGS / "ms2_multi_small.json"
ALL_OFF = {k: False for k in PX_KEYS}
# V1 (design/q44_practical_sublet.md §5.5): code/sim/out/ms2_checks/pd_cost_diag.json, rows A6, A3, A2 ({})
V1_TOTALS = {"A6": 787.1016852130742, "A3": 736.1157987175352, "A2": 747.9566683495417}


def _ms_s3():
    cfg = load_json(MULTI)
    cfg["seed"] = 3
    return build_instance(cfg)


def _sim(inst, pol, model=None, seed=0):
    res = simulate(inst, pol, model or LenderModel(schedule="trace"),
                   EngineConfig(auto_drain=False, check_invariants=True), policy_seed=seed)
    assert not res.invariant_failures, res.invariant_failures[:5]
    return res


def _same_ledger(a, b) -> bool:
    return (a.components == b.components and all(np.array_equal(a.per_slot[k], b.per_slot[k]) for k in a.per_slot)
            and [vars(x) for x in a.leases] == [vars(x) for x in b.leases]
            and [vars(x) for x in a.replicas] == [vars(x) for x in b.replicas]
            and all(np.array_equal(x, y) for x, y in zip(a.schedule.R, b.schedule.R)))


def _strip(rep):
    """A report without the knob block 'px' and the wall-time statistics (time_s_*)."""
    if isinstance(rep, dict):
        return {k: _strip(v) for k, v in rep.items() if k != "px" and not str(k).startswith("time_s")}
    if isinstance(rep, (list, tuple)):
        return [_strip(v) for v in rep]
    return rep


def _a3_with_planner_px(px):
    """A3 whose planner is built with `px` (A3 itself takes no px): a3.A2Planner replaced for one construction."""
    import sublet.algos.a3 as a3mod
    from sublet.algos.a3 import A3

    class A3px(A3):
        def reset(self, view, rng):
            orig = a3mod.A2Planner
            a3mod.A2Planner = lambda *a, **kw: orig(*a, **kw, px=px)
            try:
                super().reset(view, rng)
            finally:
                a3mod.A2Planner = orig
    return A3px()


# ---------------------------------------------------------------- knobs off
def test_resolve_px():
    """px=None and every key False resolve to every knob off; a partial object leaves the other keys off;
    unknown keys and non-bool values raise PolicyError (A2Planner and A6)."""
    assert resolve_px(None) == ALL_OFF == resolve_px({})
    assert resolve_px({"suppress_covered": True}) == {**ALL_OFF, "suppress_covered": True}
    for bad in ({"x2_surplus": True}, {"renew_live": 1}, ["renew_live"]):
        with pytest.raises(PolicyError):
            resolve_px(bad)
        with pytest.raises(PolicyError):
            A6(px=bad)
    with pytest.raises(PolicyError):
        A6(px={"renew_live": True}, predictions=True, pred_cols=[], pred_demand=[])
    assert A6().params()["px"] is None


@pytest.mark.parametrize("which", ["ms s3", "toy"])
def test_knobs_off_identity(which):
    """§6.3 'Knobs off': A3 and A6 with px=None and with every key False give identical ledgers and reports
    (except the px block and wall times), on ms2_multi_small (config seed 3, policy seed 0) and toy.json;
    on ms s3 A6, A3 and A2 reproduce V1's totals of pd_cost_diag.json (787.10, 736.12, 747.96 USD)."""
    inst = _ms_s3() if which == "ms s3" else toy_instance()
    runs = {}
    for name, mk in (("A6 none", lambda: A6()), ("A6 off", lambda: A6(px=dict(ALL_OFF))),
                     ("A3 none", lambda: make_policy({"policy": {"id": "A3", "params": {}}}, inst)),
                     ("A3 off", lambda: _a3_with_planner_px(dict(ALL_OFF)))):
        pol = mk()
        runs[name] = (pol, _sim(inst, pol))
    for a, b in (("A6 none", "A6 off"), ("A3 none", "A3 off")):
        (pa, ra), (pb, rb) = runs[a], runs[b]
        assert _same_ledger(ra, rb), (which, a, b)
        assert _strip(ra.metrics["policy"]) == _strip(rb.metrics["policy"]), (which, a, b)
        assert pa.planner.px == pb.planner.px == ALL_OFF
    assert runs["A6 none"][1].metrics["policy"]["px"] is None
    assert runs["A6 off"][1].metrics["policy"]["px"]["knobs"] == ALL_OFF
    if which == "ms s3":
        a2 = _sim(inst, make_policy({"policy": {"id": "A2", "params": {}}}, inst))
        tot = {"A6": runs["A6 none"][1].components["total"], "A3": runs["A3 none"][1].components["total"],
               "A2": a2.components["total"]}
        for pid, v in V1_TOTALS.items():
            assert abs(tot[pid] - v) <= 1e-9 * v, (pid, tot[pid], v)


# ---------------------------------------------------------------- S: the analysed shadow
def _shadow(pol):
    r = pol.planner.rounder
    n = pol.planner.pd.n_ids
    rep = pol.report()
    return {"P": rep["P"], "dual": rep["dual"], "cost_an": rep["cost_an"], "n_fix_an": rep["n_fix_an"],
            "thr": r._thr[:n].copy(), "theta": np.nan_to_num(r._theta[:n], nan=-1.0), "n_ids": n,
            "refused": rep["refused"], "cost_pr": rep["cost_pr"], "suppressed": r.n_suppressed}


def _assert_shadow_equal(a, b, tag):
    assert a["n_ids"] == b["n_ids"], tag
    for key in ("P", "dual", "cost_an"):
        assert abs(a[key] - b[key]) <= 1e-9 * max(1.0, abs(b[key])), (tag, key, a[key], b[key])
    assert a["n_fix_an"] == b["n_fix_an"], tag
    assert np.array_equal(a["thr"], b["thr"]), tag
    assert np.array_equal(a["theta"], b["theta"]), tag


def test_suppress_keeps_analysed_shadow():
    """§6.3 'Analysed shadow' (§2.2 note on S): with suppress_covered on, P, the dual, cost_an, n_fix_an, the
    thresholds and the analysed threshold flags equal those of the knob-off run, (a) on kappa_infinite
    from_core exports (core_case seeds 0-5, announcement rate 0.1) and (b) on ms2_multi_small (layering active,
    u = 4) with layer_order on in both runs (iota then does not depend on the rounding) and unlimited site
    capacities; runs without refusals (a refusal removes a column from the PD's candidates, §6.5), so the PD's
    input is the same. The knob acts: some request is suppressed and the practical accounting differs."""
    n_sup = 0
    differ = 0
    for seed in range(6):
        I, om = core_case(seed, 0.1)
        inst, _ = from_core(I, om)
        assert public_view(inst, "I1").kappa_infinite
        runs = []
        for px in (None, {"suppress_covered": True}):
            pol = A6(px=px, redundancy="off")
            _sim(inst, pol, LenderModel())
            runs.append(_shadow(pol))
        assert runs[0]["refused"] == runs[1]["refused"] == 0
        _assert_shadow_equal(runs[1], runs[0], ("core", seed))
        n_sup += runs[1]["suppressed"]
        differ += runs[1]["cost_pr"] != runs[0]["cost_pr"]
    assert n_sup > 0 and differ > 0, (n_sup, differ)
    inst = _ms_s3()
    with_capacity(inst, {i: INF for i in range(inst.m)})
    runs = []
    for px in ({"layer_order": True}, {"layer_order": True, "suppress_covered": True}):
        pol = A6(px=px)
        _sim(inst, pol)
        runs.append(_shadow(pol))
    assert runs[0]["refused"] == runs[1]["refused"] == 0
    _assert_shadow_equal(runs[1], runs[0], "ms s3 layer_order")
    assert runs[1]["suppressed"] > 0 and runs[0]["suppressed"] == 0 and runs[1]["cost_pr"] != runs[0]["cost_pr"]


# ---------------------------------------------------------------- R with F: renewal
A_REV, Q_HI = 2.85, 100.0


def _renew_case(d: float, T: int = 6):
    """One client of the toy LLM (g = 1, q = 100 USD/h, u = 4) at one revocable site with contract
    tau = 5 min, H = 5 min (window L = 2 slots, billed term 10 min, price 2.85), no announcement, load time
    0 (beta~ = 0), demand d replica loads in every slot (one unit for d <= 1/4); the protected site is
    invisible under 'revocable_only'."""
    inst, _ = onesite_c2([d] * T, a_rev=A_REV, q_gpu=Q_HI, lam_rev=0.0, lam_prot=0.0)
    return inst


def _renew_policy(renew: bool):
    return A6(x2="reference", contract_rules=[], view_transform="revocable_only", redundancy="off",
              px={"renew_live": renew, "renew_profit": True})


def test_renewal_hand():
    """§6.3 'Renewal' on a one-client, one-site hand instance (_renew_case, T = 6 slots, windows [0,2), [2,4),
    [4,6)). The first window's column opens at slot 0 at cost C = g a max(P, L Δs) / 60 = 2.85 x 10 / 60 =
    0.475 (q_req = 100 x 5 / 240 = 2.083 > C, so the practical rule opens it if the threshold does not). At
    slots 2 and 4 the coverage has run out and the lease is alive, unannounced and at its own site, with
    attributed load att = d over the previous slot. Renewal iff att q_j >= g_j a, i.e. 100 d >= 2.85:
    - d = 0.04 (4.0 >= 2.85): two renewals, no F refusal; cost_pr = C and the curve is C at slot 0 and 0 after
      (a renewal adds nothing; delta = 0); one lease across the three windows;
    - d = 0.02 (2.0 < 2.85): no renewal, two F refusals; the practical rule reopens each window at C, so
      cost_pr = 3 C; X1 keeps the lease, so again one lease.
    With renew_live off, d = 0.04 gives the d = 0.02 accounting (3 C) and the same single lease."""
    C = A_REV * 10 / 60
    out = {}
    for d, renew in ((0.04, True), (0.02, True), (0.04, False)):
        inst = _renew_case(d)
        view = public_view(inst, "I1")
        assert float(view.beta_tilde_usd[0, 0, 0]) == 0.0
        assert abs(column_cost(view, 0, 0, 0, 2) - C) <= 1e-12
        pol = _renew_policy(renew)
        res = _sim(inst, pol, LenderModel())
        rep = res.metrics["policy"]
        assert pol.planner.prob.L[0] == 2 and np.isfinite(pol.planner.prob.C[0, 0, 0])
        assert not np.isfinite(pol.planner.prob.C[1, 0, :]).any()       # the protected site is no candidate
        assert len(res.leases) == 1, (d, renew, [vars(L) for L in res.leases])
        L = res.leases[0]
        assert L.site == 0 and L.start_slot == 0 and L.release_min is None, vars(L)
        out[(d, renew)] = (rep, np.asarray(rep["curve"]))
    rep, curve = out[(0.04, True)]
    assert rep["px"]["renewed"] == 2 and rep["px"]["renew_refused_F"] == 0 and rep["realized"]["renewed"] == 2
    assert abs(rep["cost_pr"] - C) <= 1e-12 and abs(curve[0] - C) <= 1e-12 and np.all(curve[1:] == 0.0), curve
    assert rep["exec"]["renewals"] == 2
    for key in ((0.02, True), (0.04, False)):
        rep, curve = out[key]
        assert rep["px"]["renewed"] == 0
        assert rep["px"]["renew_refused_F"] == (2 if key[1] else 0)
        assert abs(rep["cost_pr"] - 3 * C) <= 1e-12, (key, rep["cost_pr"])
        assert np.allclose(curve, [C, 0, C, 0, C, 0], rtol=0, atol=1e-12), (key, curve)


def test_mark_open_hand():
    """Rounder.mark_open (§6.1 item 1): the column enters the opened set at the given slot with no change of
    cost_pr, cost_an, the curve or the threshold flags; a second mark is refused (already open);
    VecPD.col_id returns the dense id of iota 0 and creates a layered column for iota >= 1."""
    inst = toy_instance()
    view = public_view(inst, "I1")
    rng = np.random.default_rng(0)
    pl = A2Planner(view, rng, policy_streams(np.random.default_rng(1))["order"], px={"renew_live": True})
    r, pd = pl.rounder, pl.pd
    col = pd.col_id(0, 0, 0, 5, 0)
    l, j, k, s, iota, Lk = pl.column(col)
    assert (l, j, k, iota) == (0, 0, 0, 0) and s == (5 // Lk) * Lk
    n0 = pd.n_ids
    col1 = pd.col_id(0, 0, 0, 5, 1)
    assert col1 >= pd.n_dense and pd.n_ids == n0 + 1 and pd.col_id(0, 0, 0, 5, 1) == col1
    assert pl.column(col1)[4] == 1
    before = (r.cost_pr, r.cost_an, r.curve.copy())
    assert r.mark_open(col, 5) and not r.mark_open(col, 6)
    assert r.is_open(col) and r.opened[col] == 5 and r.n_renewed == 1
    assert (r.cost_pr, r.cost_an) == before[:2] and np.array_equal(r.curve, before[2])
    assert not r._thr.any() and not r._thr_pr.any()
    with pytest.raises(PolicyError):
        pd.col_id(0, 0, 0, view.grid.T_slow, 0)


# ---------------------------------------------------------------- O: layer order
def test_request_order_hand():
    """RequestOrder (knob O): 2u + 1 requests at one candidate get iota 0 (u times), 1 (u times), 2; counts are
    per (l, j, k) and per slot. Oracle: hand."""
    u = 4
    ro = RequestOrder(u, (2, 1, 2))
    ls, ks = np.array([0, 1]), np.array([0, 1])
    got = [ro.iota(0, ls[:1], ks[:1])[0] for _ in range(2 * u + 1)]
    assert got == [0] * u + [1] * u + [2]
    assert list(ro.iota(0, ls, ks)) == [2, 0]          # (0, 0) has 9 earlier requests, (1, 1) none
    ro.start_slot()
    assert list(ro.iota(0, ls, ks)) == [0, 0]


def _obs(view, t: int, D) -> SlowObs:
    n, J, m = len(view.client_llm), len(view.llms), len(view.sites)
    phi = view.grid.phi
    return SlowObs(t=t, minute=t * view.grid.slow_min, demand=np.repeat(np.asarray(D, float)[:, None], phi, axis=1),
                   leases={}, replicas={}, notices=[], ended=[], results=[], site_announced=None,
                   served_prev=np.zeros((J, m)), fallback_prev=np.zeros(n), cost_so_far=0.0)


def test_layer_order_through_planner():
    """§6.3 'Layer order' in A2Planner.slot: on the toy with sites L0 and P (u = 4, layering active), with
    'revocable_only' and kstar_only (one candidate pair, L0 with 'short', per request), two clients of LLM M
    with 9 = 2u + 1 and 3 active units: the PD requests carry iota 0 (4 times), 1 (4 times), 2, then 2, 2, 2
    (the count runs over the requests of the slot that listed the pair, across clients of the same LLM); the
    next slot starts again at 0. Oracle: hand."""
    cfg = toy_config(sites=["L0", "P"])
    cfg["borrowers"]["clients"].append(dict(cfg["borrowers"]["clients"][0], borrowers=["b1"]))
    inst = build_instance(cfg)
    view = public_view(inst, "I1")
    assert not view.kappa_infinite and view.units_per_replica == 4
    pl = A2Planner(view, np.random.default_rng(0), None, site_order_mode="index", view_transform="revocable_only",
                   px={"layer_order": True, "kstar_only": True})
    for c in range(2):
        ls, ks = pl.pd.cand_pairs(c)
        assert list(zip(ls.tolist(), ks.tolist())) == [(0, 0)], (c, ls, ks)
    seen = []
    orig = pl.pd.request

    def request(c, t, *, iota=None, excluded=None):
        seen.append((t, c, [int(v) for v in np.asarray(iota)]))
        return orig(c, t, iota=iota, excluded=excluded)
    pl.pd.request = request
    pl.slot(_obs(view, 0, [2.25, 0.75]))
    pl.slot(_obs(view, 1, [0.5, 0.0]))
    assert [x[2][0] for x in seen if x[0] == 0] == [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2]
    assert [x[1] for x in seen if x[0] == 0] == [0] * 9 + [1] * 3
    assert [x[2][0] for x in seen if x[0] == 1] == [0, 0]


def test_layer_order_off_without_layering():
    """§6.3 'Layer order off without layering': on kappa_infinite multi-client from_core exports (layering off,
    u = 1) P, the opened set and the ledger are identical with layer_order on and off (iota = 0 throughout)."""
    for seed in (1, 6, 9):
        I, om = core_case(seed, 0.1)
        assert len(I.cl_llm) > 1
        inst, _ = from_core(I, om)
        out = []
        for px in (None, {"layer_order": True}):
            pol = A6(px=px)
            res = _sim(inst, pol, LenderModel())
            assert not pol.planner.layering.active
            out.append((res, pol.report()["P"], pol.opened_ref()))
        assert out[0][1] == out[1][1] and out[0][2] == out[1][2], seed
        assert _same_ledger(out[0][0], out[1][0]), seed


# ---------------------------------------------------------------- K: the k* mask
def _kstar_config():
    """A hand menu (billing commit_tau, so the billed term is tau): site L0 offers k0 (tau 10, H 5), k1 (5, 2),
    k2 (5, 5), k3 (5, 5) at 2.0 and k5 (tau = horizon, treated as protected) at 1.0; L1 offers k0 at 1.9,
    k1, k3 at 2.0 and k4 (5, 5) at 2.1; L2 offers k1, k3 at 2.0; P offers the protected 'prot'."""
    cfg = toy_config()
    cfg["billing"] = "commit_tau"
    cfg["contracts"] = [{"id": "k0", "tau_min": 10, "H_min": 5}, {"id": "k1", "tau_min": 5, "H_min": 2},
                        {"id": "k2", "tau_min": 5, "H_min": 5}, {"id": "k3", "tau_min": 5, "H_min": 5},
                        {"id": "k4", "tau_min": 5, "H_min": 5}, {"id": "k5", "tau_min": 120, "H_min": 0},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": 5}]
    L0, L1, P = cfg["lenders"]
    L0.update(menu=["k0", "k1", "k2", "k3", "k5"], prices={"k0": 2.0, "k1": 2.0, "k2": 2.0, "k3": 2.0, "k5": 1.0})
    L1.update(menu=["k0", "k1", "k3", "k4"], prices={"k0": 1.9, "k1": 2.0, "k3": 2.0, "k4": 2.1})
    L2 = dict(L1, id="L2", group="g2", menu=["k1", "k3"], prices={"k1": 2.0, "k3": 2.0})
    cfg["lenders"] = [L0, L1, L2, P]
    return cfg


def test_kstar_mask_hand():
    """§6.3 'k* mask' on a hand menu with ties in price per GPU-hour, billed term and notice. By the rule of §2.1
    (cheapest per GPU-hour, then shortest billed term, then longest notice, then lowest index), chosen by hand:
    L0 -> k2 (k5 is cheaper but treated as protected; k1, k2, k3 tie on price and billed term 5 min, k2 and k3
    on notice 5 min, k2 has the lower index), L1 -> k0 (cheapest), L2 -> k3 (longer notice than k1), P -> none.
    With 'revocable_only' (practical Sublet) the PD candidates per site are exactly these; with no view
    transform the flagged contracts (k5 at L0, 'prot' at P) stay candidates (the K knob restricts the unflagged
    contracts only; §2.1's 'no protected contract' comes from RO)."""
    inst = build_instance(_kstar_config())
    view = public_view(inst, "I1")
    ids = [c.id for c in view.contracts]
    K = {name: ids.index(name) for name in ids}
    want = {0: {K["k2"]}, 1: {K["k0"]}, 2: {K["k3"]}, 3: set()}
    flagged = {0: {K["k5"]}, 1: set(), 2: set(), 3: {K["prot"]}}
    for vt in ("revocable_only", None):
        pl = A2Planner(view, np.random.default_rng(0), None, site_order_mode="index", view_transform=vt,
                       px={"kstar_only": True})
        for l in range(len(view.sites)):
            got = {int(k) for k in np.flatnonzero(np.isfinite(pl.prob.C[l, 0, :]))}
            exp = want[l] if vt == "revocable_only" else want[l] | flagged[l]
            assert got == exp, (vt, view.sites[l].id, got, exp)
        assert [int(k) for k in pl.kstar] == [K["k2"], K["k0"], K["k3"], -1]
    base = A2Planner(view, np.random.default_rng(0), None, site_order_mode="index")
    assert np.isfinite(base.prob.C[0, 0, K["k1"]]) and np.isfinite(base.prob.C[1, 0, K["k4"]])


# ---------------------------------------------------------------- RO: revocable only
def test_revocable_only_core_c3p5():
    """§6.3 'Revocable only': A7 (practical Sublet, view_transform 'revocable_only') on from_core exports of the
    C3-P5 instance (check_c4_lower.single(48, [(1, 1), (48, 0)], beta, [1.0, 1.3]), beta in {2, 14}) under the
    eager lender buys no lease of the protected contract (tau = T, treated as protected), and every handler
    decision has reason 'no-protected'."""
    for beta in (2, 14):
        I, _ = c4l_b(beta)
        inst, _ = from_core(I, [np.zeros(0, np.int64)] * I.m)
        rec = policy_actions_recorder(PracticalSublet())
        res = _sim(inst, rec, LenderModel(schedule="eager"))
        buys = [a for _, a in rec.actions if isinstance(a, Buy)]
        assert buys and all(b.contract == 0 for b in buys), beta
        assert all(L.contract == 0 for L in res.leases)
        dec = res.metrics["policy"]["exec"]["decisions"]
        assert set(dec) == {"no-protected"} and dec["no-protected"] > 0, dec
