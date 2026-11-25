"""Tests of the reclaim handler (design/sim_spec_ms2.md §10, §3.5; §17.2 test_handler.py).

The handler is driven with hand-made observations (SlowObs, LeaseView, ReplicaView, Notice) on
variants of configs/toy.json (u = 4, Δs = Δf = 5 min): an announced lease at L0, a second own lease
at L1, the protected site P. Expected decisions are computed from the view with the formulas of §10
and `timing.latest_prewarm_slot`; test (a) uses a hand-made predicted demand and its own p_hat.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from fixtures import site_index, toy_instance, with_stranding

from sublet.algos import c2rule
from sublet.algos.handler import ReclaimHandler
from sublet.instance import active_units, public_view
from sublet.timing import latest_prewarm_slot
from sublet.types import Drain, LeaseView, Notice, ReplicaView, SlowObs

SLOW = 5


def _inst(H_short=60, price_short=2.85, lam=(300.0, 300.0, 300.0), billing="prepaid_D", mu_fb=1.0):
    """toy.json with contract 'short' = (tau 5 min, H_short), L0's 'short' at price_short, load times
    lam = (L0, L1, P) in seconds, mu_fb in USD and no other stranding term."""
    inst = toy_instance({"contracts.0.H_min": H_short, "lenders.0.prices.short": price_short,
                         "lenders.0.lam_s": lam[0], "lenders.1.lam_s": lam[1], "lenders.2.lam_s": lam[2],
                         "billing": billing})
    with_stranding(inst, mu_fb_usd=mu_fb, mu_kv_usd=0.0, mu_fl_usd=0.0, pi_usd_per_min=0.0, W_f_min=0.0)
    return inst


def _ids(inst):
    return (site_index(inst, "L0"), site_index(inst, "L1"), site_index(inst, "P"),
            [c.id for c in inst.contracts].index("short"))


def _lease(lid, site, k, t_start, *, announce=None, death=None, replicas=(), gpus=1, prepaid_end=None):
    return LeaseView(id=lid, site=site, contract=k, gpus=gpus, start_slot=t_start, start_min=t_start * SLOW,
                     prepaid_end_min=t_start * SLOW + 10 if prepaid_end is None else prepaid_end,
                     announce_slot=announce, death_min=death, replicas=tuple(replicas))


def _rep(rid, lid, admission=1.0, state="warm"):
    return ReplicaView(id=rid, lease_id=lid, llm=0, state=state, load_start_min=0, warm_fast=0,
                       admission=admission, drain_min=None)


def _obs(inst, t, D, leases=(), replicas=(), served=None):
    """SlowObs at slot t with every fast slot of the client at demand D."""
    m = inst.m
    return SlowObs(t=t, minute=t * SLOW, demand=np.full((inst.n, inst.grid.phi), float(D)),
                   leases={L.id: L for L in leases}, replicas={r.id: r for r in replicas}, notices=[], ended=[],
                   results=[], site_announced=None,
                   served_prev=np.zeros((inst.J, m)) if served is None else np.asarray(served, dtype=float),
                   fallback_prev=np.zeros(inst.n), cost_so_far=0.0)


def _setting(inst, r=4, H=60, D=1.0, served=None):
    """An announced lease 1 at L0 (contract 'short', notice at r, death at r Δs + H) with replica 11, and an
    unannounced lease 2 at L1 with replica 12."""
    l0, l1, lp, k = _ids(inst)
    E = r * SLOW + H
    L = _lease(1, l0, k, 0, announce=r, death=E, replicas=(11,))
    L2 = _lease(2, l1, k, 0, replicas=(12,))
    obs = _obs(inst, r, D, [L, L2], [_rep(11, 1), _rep(12, 2)], served)
    return obs, Notice(lease_id=1, r_slot=r, death_min=E), L, (l0, l1, lp, k)


def _t_c(view, r, E, site):
    return latest_prewarm_slot(r, E, int(round(1000.0 * float(view.lam_s[0, site]))), view.grid)


# ---------------------------------------------------------------- step 4: infeasible and alpha >= 1
@pytest.mark.parametrize("reaction", ["c2sw", "cold", "prewarm_if_feasible", "test_a"])
def test_infeasible_cold(reaction):
    """§10 step 4: H = 5 min < lambda' = 600 s at the replacement site: no slow slot makes the replacement
    warm before the death, so every reaction is cold with reason 'infeasible'."""
    inst = _inst(H_short=5, lam=(300.0, 600.0, 600.0))
    view = public_view(inst, "I1")
    obs, notice, L, (l0, l1, lp, k) = _setting(inst, r=4, H=5)
    assert _t_c(view, 4, notice.death_min, l1) is None
    h = ReclaimHandler(view, reaction=reaction, p_hat=(lambda S, t: 1.0) if reaction == "test_a" else None)
    d = h.decide(obs, notice, L, 0, l1, k)
    assert d.kind == "cold" and d.reason == "infeasible" and d.t_commit is None, d


def test_alpha_ge1_cold(monkeypatch):
    """§10 step 4 (b), M59: a lease with g_j a >= q_j (price 7.5 > q = 7.15) reacts cold with reason
    'alpha>=1', without calling c2_units or c2_thresholds."""
    calls = []
    for name in ("c2_thresholds", "c2_units"):
        orig = getattr(c2rule, name)
        monkeypatch.setattr(c2rule, name, lambda *a, _o=orig, _n=name, **kw: (calls.append(_n), _o(*a, **kw))[1])
    inst = _inst(price_short=7.5)
    view = public_view(inst, "I1")
    obs, notice, L, (l0, l1, lp, k) = _setting(inst)
    assert _t_c(view, 4, notice.death_min, l1) is not None
    d = ReclaimHandler(view).decide(obs, notice, L, 0, l1, k)
    assert d.kind == "cold" and d.reason == "alpha>=1", d
    assert calls == []


@pytest.mark.parametrize("nu, kind", [(1.0, "cold"), (2.0, "prewarm")])
def test_c2sw_reaction(nu, kind):
    """§10 step 4 (b) at a default-like calibration (lease at a0 = 2.85, protected 5.97, lambda = lambda' =
    300 s, beta_jl = 0, phi = 1, so lambda = 0.715 and bw = 0.597 in C2 units): mu / beta~ = 1 is cold and
    2 is a pre-warm at latest_prewarm_slot (crossover 1.725, switch_cost_crossover.txt)."""
    inst = _inst()
    view = public_view(inst, "I1")
    l0, l1, lp, k = _ids(inst)
    bt = float(view.beta_tilde_usd[0, l0, k])
    with_stranding(inst, mu_fb_usd=nu * bt)
    view = public_view(inst, "I1")
    obs, notice, L, _ = _setting(inst)
    u = c2rule.c2_units(view, 0, l0, k, l_prot=lp, k_prot=[c.id for c in inst.contracts].index("prot"), rep_site=l1)
    assert abs(u.lam - 0.715) < 5e-4 and abs(u.bw - 0.597) < 5e-4 and abs(u.mu - nu) < 1e-12, u
    d = ReclaimHandler(view).decide(obs, notice, L, 0, l1, k)
    assert d.kind == kind, d
    assert d.reason == ("c2sw-warm" if kind == "prewarm" else "c2sw-cold"), d
    assert (d.site, d.contract) == (l1, k)
    assert d.clients == (0,)
    assert d.t_commit == (_t_c(view, 4, notice.death_min, l1) if kind == "prewarm" else None)


# ---------------------------------------------------------------- test (a)
def _p_hat_from(view, pred_demand, D_now, calls):
    """p_hat of §10 step 4 (a) by hand: n^_c = active units of the predicted slot maximum, n_c those of the
    notice slot; p_hat = sum min(n^_c, n_c) / sum n_c."""
    g = view.grid
    Dmax = np.asarray(pred_demand, dtype=float).reshape(len(view.client_llm), g.T_slow, g.phi).max(axis=2)
    n_now = active_units(np.array([D_now]), view.units_per_replica)

    def p_hat(S, slot):
        calls.append((tuple(S), int(slot)))
        S = list(S)
        n_hat = active_units(Dmax[S, slot], view.units_per_replica)
        den = n_now[S].sum()
        return float(np.minimum(n_hat, n_now[S]).sum() / den) if den > 0 else 0.0
    return p_hat


def test_test_a_hand():
    """§10 step 4 (a) by hand (M33): carried = 0.8 (served_prev at L0, one warm replica), spare = 1 - 0.5 at
    L1, d_res = 0.3; commit_tau billing, so a wasted pre-warm costs g a P / 60 with P = tau = 5 min; the predicted
    share p_hat in {0, 0.25, 0.5, 0.75, 1} (u = 4) comes from a hand-made pred_demand at the death slot.
    Pre-warm iff p [(mu_fb + pi (W_f - H)^+) d_res + q lambda'/3600 d_res] > (1 - p) [beta + g a P / 60]."""
    inst = _inst(billing="commit_tau", mu_fb=1.0)
    view = public_view(inst, "I1")
    l0, l1, lp, k = _ids(inst)
    served = np.zeros((1, inst.m))
    served[0, l0], served[0, l1] = 0.8, 0.5
    r, H = 4, 60
    obs, notice, L, _ = _setting(inst, r=r, H=H, D=1.0, served=served)
    E = notice.death_min
    d_res = 0.8 - (1.0 - 0.5)
    q, g = view.llms[0].q_usd_per_h, view.llms[0].g
    lam_p = float(view.lam_s[0, l1])
    gain_per_p = 1.0 * d_res + q * (lam_p / 3600.0) * d_res
    waste = float(view.beta_usd[0, l1]) + g * float(view.price[l1, k]) * int(view.contracts[k].prepaid_min) / 60.0
    assert int(view.contracts[k].prepaid_min) == SLOW
    seen = set()
    for D_hat in (0.0, 0.25, 0.5, 0.75, 1.0):
        pred = np.zeros((inst.n, inst.grid.T_fast))
        pred[:, (E // SLOW) * inst.grid.phi:(E // SLOW + 1) * inst.grid.phi] = D_hat
        calls = []
        h = ReclaimHandler(view, reaction="test_a", p_hat=_p_hat_from(view, pred, 1.0, calls))
        d = h.decide(obs, notice, L, 0, l1, k)
        p = D_hat                                   # u = 4 and D_now = 1: p_hat = n^ / 4 = D_hat
        want = "prewarm" if p * gain_per_p > (1 - p) * waste else "cold"
        assert d.kind == want, (D_hat, d, p * gain_per_p, (1 - p) * waste)
        assert calls and calls[0] == ((0,), E // SLOW), calls
        if want == "prewarm":
            assert d.t_commit == _t_c(view, r, E, l1)
        seen.add(want)
    assert seen == {"cold", "prewarm"}
    # no residual load (the other lease absorbs all of it): cold whatever p_hat
    served2 = served.copy()
    served2[0, l1] = 0.0
    obs2, _, _, _ = _setting(inst, r=r, H=H, D=1.0, served=served2)
    obs2.served_prev[0, l0] = 0.8 * 0.5
    h = ReclaimHandler(view, reaction="test_a", p_hat=lambda S, t: 1.0)
    assert h.decide(obs2, notice, L, 0, l1, k).kind == "cold"


# ---------------------------------------------------------------- confirm at t_c
def test_confirm():
    """§10, §3.5: at t_c test (b) cancels when the stranded clients' demand is off and holds when it is on;
    test (a) cancels when d_res has dropped to 0 (no load on the announced lease in slot t_c - 1)."""
    inst = _inst()
    view = public_view(inst, "I1")
    l0, l1, lp, k = _ids(inst)
    with_stranding(inst, mu_fb_usd=2.0 * float(view.beta_tilde_usd[0, l0, k]))
    view = public_view(inst, "I1")
    obs, notice, L, _ = _setting(inst)
    h = ReclaimHandler(view)
    d = h.decide(obs, notice, L, 0, l1, k)
    assert d.kind == "prewarm" and d.clients == (0,)
    t_c = d.t_commit
    on, _, _, _ = _setting(inst, r=t_c, D=1.0)
    off, _, _, _ = _setting(inst, r=t_c, D=0.0)
    assert h.confirm(on, d, L) is True
    assert h.confirm(off, d, L) is False
    # test (a)
    served = np.zeros((1, inst.m))
    served[0, l0], served[0, l1] = 0.8, 0.5
    obs_a, _, _, _ = _setting(inst, D=1.0, served=served)
    ha = ReclaimHandler(view, reaction="test_a", p_hat=lambda S, t: 1.0)
    da = ha.decide(obs_a, notice, L, 0, l1, k)
    assert da.kind == "prewarm"
    keep, _, _, _ = _setting(inst, r=da.t_commit, D=1.0, served=served)
    gone_served = served.copy()
    gone_served[0, l0] = 0.0
    gone, _, _, _ = _setting(inst, r=da.t_commit, D=1.0, served=gone_served)
    assert ha.confirm(keep, da, L) is True
    assert ha.confirm(gone, da, L) is False


# ---------------------------------------------------------------- drain (step 1)
def test_drain_option():
    """§10 step 1 (M31): no drains by default; with drain=True one Drain(rid, max(r Δs, E - ceil(T_dr / 60)))
    per replica of the announced lease in obs.replicas, only if the lease is in obs.leases; the pre-warm
    deadline is then the drain start."""
    inst = _inst()
    view = public_view(inst, "I1")
    l0, l1, lp, k = _ids(inst)
    r, H = 4, 60
    E = r * SLOW + H
    L = _lease(1, l0, k, 0, announce=r, death=E, replicas=(11, 13))
    obs = _obs(inst, r, 1.0, [L], [_rep(11, 1), _rep(13, 1, admission=0.5)])
    notice = Notice(lease_id=1, r_slot=r, death_min=E)
    assert ReclaimHandler(view).drain_actions(obs, notice) == []
    h = ReclaimHandler(view, drain=True, reaction="prewarm_if_feasible")
    at = max(r * SLOW, E - math.ceil(float(view.llms[0].T_dr_s) / 60.0))
    assert sorted(h.drain_actions(obs, notice), key=lambda a: a.replica_id) == [Drain(11, at), Drain(13, at)]
    d = h.decide(obs, notice, L, 0, l1, k)
    assert d.kind == "prewarm" and d.t_commit == _t_c(view, r, at, l1)
    absent = _obs(inst, r, 1.0, [], [])
    assert h.drain_actions(absent, notice) == []


# ---------------------------------------------------------------- trap T1
def test_trap_t1():
    """§2.3 (M51), trap T1: with H_k < Δf the notified lease is dead in its whole notice slot and absent
    from obs.leases; the handler treats it as dead: no drain, a cold decision, no exception."""
    inst = _inst(H_short=2)
    view = public_view(inst, "I1")
    l0, l1, lp, k = _ids(inst)
    r = 6
    E = r * SLOW + 2
    L = _lease(1, l0, k, 0, announce=r, death=E, replicas=(11,))
    obs = _obs(inst, r, 1.0, [], [])                 # the lease is absent at its notice slot
    notice = Notice(lease_id=1, r_slot=r, death_min=E)
    for reaction in ("c2sw", "prewarm_if_feasible"):
        h = ReclaimHandler(view, reaction=reaction, drain=True)
        assert h.drain_actions(obs, notice) == []
        for lease in (L, None):
            d = h.decide(obs, notice, lease, 0, l1, k)
            assert d.kind == "cold" and d.t_commit is None and d.reason == "dead", d
    # lambda' = 0: a pre-warm would be feasible (t_c = r), so only the 'dead' guard (M51) keeps it cold
    inst0 = _inst(H_short=2, lam=(0.0, 0.0, 0.0))
    view0 = public_view(inst0, "I1")
    assert _t_c(view0, r, E, l1) == r
    for reaction in ("c2sw", "prewarm_if_feasible"):
        d = ReclaimHandler(view0, reaction=reaction).decide(obs, notice, L, 0, l1, k)
        assert d.kind == "cold" and d.reason == "dead" and d.t_commit is None, (reaction, d)


# ---------------------------------------------------------------- further cases of §10
def test_beta_tilde_zero_is_cold():
    """§10 step 4 (b): a lease whose beta~ is 0 (beta_jl = 0 and lambda = 0 at its site) has no C2 units
    (c2_units would raise): the c2sw reaction is cold with reason 'beta~=0', also when a pre-warm is
    feasible."""
    inst = _inst(lam=(0.0, 0.0, 0.0))
    view = public_view(inst, "I1")
    l0, l1, lp, k = _ids(inst)
    assert float(view.beta_tilde_usd[0, l0, k]) == 0.0
    obs, notice, L, _ = _setting(inst)
    assert _t_c(view, 4, notice.death_min, l1) is not None
    d = ReclaimHandler(view).decide(obs, notice, L, 0, l1, k)
    assert d.kind == "cold" and d.reason == "beta~=0" and d.t_commit is None, d
    with pytest.raises(Exception):
        c2rule.c2_units(view, 0, l0, k, l_prot=lp, k_prot=[c.id for c in inst.contracts].index("prot"),
                        rep_site=l1)


def _two_client_inst():
    from fixtures import explicit_client, toy_config
    from sublet.instance import build_instance
    cfg = toy_config()
    d = [1.0] * 24
    cfg["borrowers"]["clients"] = [explicit_client(d), explicit_client(d, borrower="b1")]
    return build_instance(cfg)


def test_stranded_and_confirm_two_clients():
    """§7.3, §10: S = the clients of LLM j with finite delta at the lease's site and demand on, all of them if
    none is on; confirm (test (b) and fixed reactions) holds if SOME client of d.clients has demand on."""
    from sublet.algos.handler import Decision
    inst = _two_client_inst()
    view = public_view(inst, "I1")
    h = ReclaimHandler(view)

    def obs(D):
        return SlowObs(t=3, minute=15, demand=np.repeat(np.asarray(D, dtype=float)[:, None], inst.grid.phi, axis=1),
                       leases={}, replicas={}, notices=[], ended=[], results=[], site_announced=None,
                       served_prev=np.zeros((inst.J, inst.m)), fallback_prev=np.zeros(inst.n), cost_so_far=0.0)
    assert h.stranded(obs([1.0, 0.0]), 0, 0) == (0,)
    assert h.stranded(obs([0.0, 1.0]), 0, 0) == (1,)
    assert h.stranded(obs([0.0, 0.0]), 0, 0) == (0, 1)
    d = Decision("prewarm", 3, 1, 0, "forced", (0, 1))
    assert h.confirm(obs([0.0, 1.0]), d, None) is True
    assert h.confirm(obs([1.0, 0.0]), d, None) is True
    assert h.confirm(obs([0.0, 0.0]), d, None) is False


def test_residual_spare_excludes_announced():
    """§10 step 3: test (a)'s spare capacity counts only own warm replicas at other sites on unannounced leases:
    with the L1 lease announced, d_res = carried = 0.8; unannounced, d_res = 0.8 - (1 - 0.5) = 0.3."""
    inst = _inst()
    view = public_view(inst, "I1")
    l0, l1, lp, k = _ids(inst)
    served = np.zeros((1, inst.m))
    served[0, l0], served[0, l1] = 0.8, 0.5
    L = _lease(1, l0, k, 0, announce=4, death=80, replicas=(11,))
    h = ReclaimHandler(view)
    for ann, want in ((4, 0.8), (None, 0.3)):
        L2 = _lease(2, l1, k, 0, announce=ann, death=80 if ann is not None else None, replicas=(12,))
        obs = _obs(inst, 4, 1.0, [L, L2], [_rep(11, 1), _rep(12, 2)], served)
        assert abs(h.residual(obs, L, 0, (0,)) - want) <= 1e-12, (ann, h.residual(obs, L, 0, (0,)))


def test_test_a_waste_at_replacement():
    """§10 step 4 (a): a wasted pre-warm costs beta_jl' + g a_l'k' P_k' / 60 at the replacement (l', k'), not at
    the announced lease's site: with L1's 'short' at 6.0 (commit_tau, P = 5 min), d_res = 0.3 and p_hat = 0.4
    the test is cold at L1, while the same test with the waste priced at L0's 2.85 would pre-warm."""
    inst = toy_instance({"contracts.0.H_min": 60, "lenders.0.prices.short": 2.85, "lenders.1.prices.short": 6.0,
                         "lenders.0.lam_s": 300.0, "lenders.1.lam_s": 300.0, "lenders.2.lam_s": 300.0,
                         "billing": "commit_tau"})
    with_stranding(inst, mu_fb_usd=1.0, mu_kv_usd=0.0, mu_fl_usd=0.0, pi_usd_per_min=0.0, W_f_min=0.0)
    view = public_view(inst, "I1")
    l0, l1, lp, k = _ids(inst)
    served = np.zeros((1, inst.m))
    served[0, l0], served[0, l1] = 0.8, 0.5
    obs, notice, L, _ = _setting(inst, served=served)
    p, d_res = 0.4, 0.3
    q, g = view.llms[0].q_usd_per_h, view.llms[0].g
    gain = p * (1.0 * d_res + q * (300.0 / 3600.0) * d_res)
    P = int(view.contracts[k].prepaid_min)
    assert P == SLOW
    waste_rep = (1 - p) * (float(view.beta_usd[0, l1]) + g * 6.0 * P / 60.0)
    waste_own = (1 - p) * (float(view.beta_usd[0, l0]) + g * 2.85 * P / 60.0)
    assert waste_own < gain < waste_rep
    d = ReclaimHandler(view, reaction="test_a", p_hat=lambda S, t: p).decide(obs, notice, L, 0, l1, k)
    assert d.kind == "cold" and d.reason == "test-a-cold", d
    d0 = ReclaimHandler(view, reaction="test_a", p_hat=lambda S, t: p).decide(obs, notice, L, 0, l0, k)
    assert d0.kind == "prewarm", d0


def test_c2sw_uses_replacement_load():
    """§9.2, §10 step 4 (b): the C2-SW reaction maps lambda' at decide()'s replacement site: lambda' = 3000 s at
    L1 gives the reaction of c2_units(rep_site=L1), which differs from the one at L0 (300 s) with
    mu = 2 beta~."""
    inst = _inst(lam=(300.0, 3000.0, 300.0))
    view = public_view(inst, "I1")
    l0, l1, lp, k = _ids(inst)
    bt = float(view.beta_tilde_usd[0, l0, k])
    with_stranding(inst, mu_fb_usd=2.0 * bt)
    view = public_view(inst, "I1")
    obs, notice, L, _ = _setting(inst)
    kp = [c.id for c in inst.contracts].index("prot")
    r = {}
    for site in (l0, l1):
        u = c2rule.c2_units(view, 0, l0, k, l_prot=lp, k_prot=kp, rep_site=site)
        r[site] = c2rule.c2_thresholds(u.alpha, u.ap, u.mu, u.lam, 1.0, u.bw).react
    assert r[l0] != r[l1], r
    for site in (l0, l1):
        d = ReclaimHandler(view).decide(obs, notice, L, 0, site, k)
        if _t_c(view, 4, notice.death_min, site) is None:
            assert d.reason == "infeasible", (site, d)
        else:
            assert d.reason == f"c2sw-{r[site]}", (site, d, r)
