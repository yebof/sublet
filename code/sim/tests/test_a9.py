"""Tests of policy A9, notice-aware critical-ratio renting (sublet/algos/a9.py; design/sublet_v2.md §2.2, §2.3,
§8.3 test_a9.py), and of contracts.c2_contract_table (§8.1, C37).

Instances are variants of configs/toy.json (hand-made slots fed through a small hand engine, _Hand, which turns
the policy's Buys into leases with fresh ids and its Releases into ends), configs/ms2_multi_small.json (engine
runs on layer sites with a random site order) and from_core exports of the T4/O1 family at the (m, rho, tau, H,
T) of the development folder's fresh families (code/sim/out/sublet_v2_dev/theory/fam_identity.py; development
cells, never the instances of the pilot's step P3 or of the confirmation). Oracles: the rules of §2.2 written
out by hand, contracts.p1_mask and p3_mask, c2rule.c2_units and insure_up_front, timing.latest_prewarm_slot and
family.RRRenew. The policy class is built directly (its registry id is added by another unit of the build).
"""
from __future__ import annotations

import dataclasses
import json

import numpy as np
import pytest

import fam

from fixtures import CONFIGS, site_index, toy_config, toy_instance

from sublet.algos import a9, c2rule
from sublet.algos.a9 import NoticeCriticalRatio
from sublet.algos.common import EPS_DEMAND, PolicyError, treated_as_protected
from sublet.algos.contracts import c2_contract_table, p1_mask, p3_mask
from sublet.algos.family import RRRenew
from sublet.baselines.greedy import GreedyLease
from sublet.engine import EngineConfig, simulate
from sublet.instance import build_instance, from_core, public_view
from sublet.timing import latest_prewarm_slot
from sublet.types import ActionResult, Buy, LeaseView, LenderModel, Notice, Release, SlowObs

TOL = 1e-12
DEV_FAMILIES = ((3, 3.0, 1, 1, 40), (3, 6.0, 3, 2, 60), (5, 3.0, 3, 2, 60), (5, 6.0, 1, 1, 40), (7, 10.0, 1, 2, 48))
FAM_MODES = {"F-ad": ("adaptive", {}, (0,)), "F-eg": ("eager", {}, (0,)), "F-ss": ("safe_site", {}, (0, 1, 2)),
             "F-iid": ("iid_step", {"p": 0.5}, (0, 1, 2))}


# ---------------------------------------------------------------- helpers
def _pol(view, **kw) -> NoticeCriticalRatio:
    p = NoticeCriticalRatio(**kw)
    p.reset(view, np.random.default_rng(0))
    return p


def _dem(inst, d) -> np.ndarray:
    """(n, phi) demand: per client a number (all fast slots) or a list of phi values."""
    n, phi = inst.n, inst.grid.phi
    out = np.zeros((n, phi))
    for c, v in enumerate(d):
        out[c] = np.broadcast_to(np.asarray(v, dtype=float), (phi,))
    return out


def _obs(inst, t, d, leases=(), notices=(), ended=(), results=()) -> SlowObs:
    return SlowObs(t=t, minute=t * inst.grid.slow_min, demand=_dem(inst, d), leases={L.id: L for L in leases},
                   replicas={}, notices=list(notices), ended=list(ended), results=list(results), site_announced=None,
                   served_prev=np.zeros((inst.J, inst.m)), fallback_prev=np.zeros(inst.n), cost_so_far=0.0)


class _Hand:
    """Feeds hand-made slots to a policy: a Buy becomes a lease (ids from 100, start at the slot, prepaid term
    `prepaid` minutes or the contract's), a Release ends its lease at the slot ('release', reported next slot);
    `step` can announce leases (notices) and end leases at the slot's start (kills with a cause)."""

    def __init__(self, inst, pol, prepaid=None, info="I1"):
        self.inst, self.pol, self.prepaid = inst, pol, prepaid
        self.view = public_view(inst, info)
        pol.reset(self.view, np.random.default_rng(0))
        self.leases: dict[int, LeaseView] = {}
        self.results: list = []
        self.ended: list = []
        self.next_id = 100
        self.buys: list = []        # (t, lease id, Buy)

    def step(self, t, d, notices=(), kill=()):
        slow = self.inst.grid.slow_min
        ended, self.ended = list(self.ended), []
        for lid, cause in kill:
            self.leases.pop(lid)
            ended.append((lid, t * slow, cause))
        nts = []
        for lid, death in notices:
            self.leases[lid] = dataclasses.replace(self.leases[lid], announce_slot=t, death_min=int(death))
            nts.append(Notice(lid, t, int(death)))
        acts = self.pol.act(_obs(self.inst, t, d, self.leases.values(), nts, ended, self.results))
        self.results = []
        for a in acts:
            if isinstance(a, Release):
                self.leases.pop(a.lease_id)
                self.ended.append((a.lease_id, t * slow, "release"))
        for i, a in enumerate(acts):
            if isinstance(a, Buy):
                lid = self.next_id
                self.next_id += 1
                P = self.inst.contracts[a.contract].prepaid_min if self.prepaid is None else self.prepaid
                g = self.inst.llms[a.llm].g
                self.leases[lid] = LeaseView(lid, a.site, a.contract, g, t, t * slow, t * slow + P, None, None, ())
                self.results.append(ActionResult(i, a, True, lid, (), ""))
                self.buys.append((t, lid, a))
        return acts


def _menu_instance(contracts, prices, *, lam=300.0, a_prot=None, with_prot=True, fast_min=5, horizon_min=120):
    """toy.json with site L0 offering `contracts` [(id, tau_min, H_min)] at `prices` (L1 removed), the protected
    site P (contract 'prot') unless with_prot is False."""
    cfg = toy_config(sites=["L0", "P"] if with_prot else ["L0"])
    cfg["time"].update({"fast_slot_min": int(fast_min), "horizon_min": int(horizon_min)})
    cfg["borrowers"]["clients"][0]["demand"]["values"] = [0.0] * (int(horizon_min) // int(fast_min))
    cfg["contracts"] = [{"id": i, "tau_min": t, "H_min": h} for i, t, h in contracts] + \
                       ([{"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": 5}] if with_prot else [])
    cfg["lenders"][0].update({"menu": [i for i, _, _ in contracts], "lam_s": float(lam),
                              "prices": {i: float(prices[i]) for i, _, _ in contracts}})
    if a_prot is not None:
        cfg["prices"]["a_protected_usd_per_gpu_h"] = float(a_prot)
    inst = build_instance(cfg)
    return inst, public_view(inst, "I1")


def _kid(inst, cid) -> int:
    return [c.id for c in inst.contracts].index(cid)


def _lease_rows(res) -> list:
    return [dataclasses.asdict(L) for L in res.leases]


def _same_ledger(a, b, what) -> None:
    assert set(a.per_slot) == set(b.per_slot), what
    for k in a.per_slot:
        assert np.array_equal(a.per_slot[k], b.per_slot[k]), (what, k)
    assert a.components == b.components, what
    assert _lease_rows(a) == _lease_rows(b), what


def _ms(horizon_min=720):
    cfg = json.loads((CONFIGS / "ms2_multi_small.json").read_text())
    cfg["time"]["horizon_min"] = int(horizon_min)
    return build_instance(cfg)


# ---------------------------------------------------------------- parameters
def test_params_and_validation():
    """§2.2 'Flags': PARAMS = GreedyLease's plus A9's keys with the defaults of A9; wrong values raise PolicyError;
    A9 never asks for fast slots."""
    P = NoticeCriticalRatio.PARAMS
    assert {k: P[k] for k in GreedyLease.PARAMS if k not in NoticeCriticalRatio.OWN_PARAMS} == \
        {k: v for k, v in GreedyLease.PARAMS.items() if k not in NoticeCriticalRatio.OWN_PARAMS}
    assert NoticeCriticalRatio.OWN_PARAMS == {"demand_lag": 0, "target": "ratio", "release": "ski",
                                              "contract_rule": "c2", "commit": True, "mbb": True, "site_rule": "ski",
                                              "insure": True, "theta": "be", "tie": "lru"}
    assert NoticeCriticalRatio().params() == P
    for bad in ({"target": "max"}, {"release": "later"}, {"contract_rule": "p3"}, {"site_rule": "lru"},
                {"theta": "x"}, {"tie": "pi"}, {"commit": 1}, {"mbb": "yes"}, {"insure": None}, {"demand_lag": 2},
                {"demand_lag": True}, {"demand_stat": "median"}, {"unknown": 1}):
        with pytest.raises(PolicyError):
            NoticeCriticalRatio(**bad)
    inst = toy_instance()
    p = _pol(public_view(inst, "I1"))
    assert p.wants_fast is False


# ---------------------------------------------------------------- A9.1
def test_theta_and_target_hand():
    """A9.1: theta_c = g a_{l_c kbar} / (q - delta_{c l_c}) at the usable site of least sigma ('be'), RCRb's
    (g a + delta) / q with theta 'cr'; N_c counts the layers whose mean utilization reaches theta (ceiling with
    tolerance 1e-9, EPS_DEMAND), and with kappa_infinite N_c = [mean demand >= theta]; target 'ceil' is BL1's."""
    inst = toy_instance({"time.fast_slot_min": 1, "borrowers.clients.0.demand.values": [0.0] * 120})
    l0, l1 = site_index(inst, "L0"), site_index(inst, "L1")
    inst.clients.delta_usd_per_h[0, [l0, l1]] = 0.5
    view = public_view(inst, "I1")
    q, a = view.llms[0].q_usd_per_h, float(view.price[l0, _kid(inst, "short")])
    be, cr = _pol(view), _pol(view, theta="cr")
    assert be.l_c[0] == l0 and be.kb[l0, 0] == _kid(inst, "short")
    assert abs(be.theta[0] - a / (q - 0.5)) <= TOL and abs(cr.theta[0] - (a + 0.5) / q) <= TOL
    th = be.theta[0]
    assert a / (q - 0.5) < 0.45 < (a + 0.5) / q
    cases = [([1.5, 1.5, 0.2, 0.2, 0.2], 1),            # x1 = 0.52, x2 = 0.2
             ([2.0] * 5, 2), ([0.0] * 5, 0), ([EPS_DEMAND] * 5, 0),
             ([1.0, 1.0, 1.0, 1.0, 1.0 + 5e-10], 1),     # ceil(max - 1e-9) = 1: no second layer
             ([0.45] * 5, 1), ([th - 1e-13] * 5, 1), ([th - 1e-11] * 5, 0)]
    for d, want in cases:
        assert list(be.base_target(_dem(inst, [d]))) == [want], d
    assert list(cr.base_target(_dem(inst, [[0.45] * 5]))) == [0]
    ceil = _pol(view, target="ceil")
    assert list(ceil.base_target(_dem(inst, [[1.5, 1.5, 0.2, 0.2, 0.2]]))) == [2]
    # kappa_infinite: one replica serves all; the slot's mean demand against theta
    inst.kappa_infinite = True
    kv = public_view(inst, "I1")
    k = _pol(kv)
    for d, want in (([1.5, 1.5, 0.2, 0.2, 0.2], 1), ([0.3] * 5, 0), ([0.0] * 5, 0), ([0.45] * 5, 1)):
        assert list(k.base_target(_dem(inst, [d]))) == [want], d
    assert list(_pol(kv, target="ceil").base_target(_dem(inst, [[0.3] * 5]))) == [1]


def test_demand_lag():
    """demand_lag 1 (P5's boundary run): the target of slot t is computed on slot t - 1's demand (zeros at t = 0)."""
    inst = toy_instance({"lenders.0.R": [], "lenders.1.R": []})
    h = _Hand(inst, NoticeCriticalRatio(demand_lag=1), prepaid=0)
    assert not [a for a in h.step(0, [1.0]) if isinstance(a, Buy)]
    assert len([a for a in h.step(1, [0.0]) if isinstance(a, Buy)]) == 1
    acts = h.step(2, [0.0])
    assert not [a for a in acts if isinstance(a, Buy)]
    h0 = _Hand(inst, NoticeCriticalRatio(), prepaid=0)
    assert len([a for a in h0.step(0, [1.0]) if isinstance(a, Buy)]) == 1


# ---------------------------------------------------------------- A9.2
def test_release_accumulator_and_resets():
    """A9.2: a surplus layer is kept while its accumulated waste (theta - x_k)^+ (q - delta) Δs/60 stays below
    kappa'_j clip(d(f*) - (k - 1), 0, 1), f* the last fast slot of the previous slot; the first failing layer is
    released, accumulators are cleared when the layer is released or when h_c <= N_c; release 'now' is BL1's."""
    inst = toy_instance({"time.fast_slot_min": 1, "borrowers.clients.0.demand.values": [0.0] * 120,
                         "lenders.0.R": [], "lenders.1.R": [], "lenders.0.capacity_gpus": 8})
    view = public_view(inst, "I1")
    st = view.stranding
    kap = float(st.mu_kv_usd[0] + st.mu_fl_usd[0] + st.mu_fb_usd[0] + st.pi_usd_per_min[0] * st.W_f_min)
    pol = NoticeCriticalRatio()
    h = _Hand(inst, pol, prepaid=0)
    assert abs(pol.kap[0] - kap) <= TOL and kap > 0
    th, rate, Ds = float(pol.theta[0]), float(pol.waste_rate[0]), 5 / 60
    low = [1.0, 1.0, 1.0, 1.0, 1.9]                     # x2 = 0.18 < theta, last fast slot 1.9
    x2 = 0.9 / 5
    assert x2 < th
    assert len([a for a in h.step(0, [2.0]) if isinstance(a, Buy)]) == 2
    # oracle of the scan for layer 2
    w, f_last, t, released = 0.0, 2.0, 1, None
    while released is None:
        acts = h.step(t, [low])
        w_new = w + max(0.0, th - x2) * rate * Ds
        keep = w_new < kap * min(1.0, max(0.0, f_last - 1))
        rel = [a for a in acts if isinstance(a, Release)]
        if keep:
            assert not rel and abs(pol.acc[0][2] - w_new) <= 1e-12, (t, pol.acc[0], w_new)
            w = w_new
        else:
            assert len(rel) == 1 and 2 not in pol.acc[0], t
            released = t
        f_last, t = 1.9, t + 1
        assert t < 40
    assert released >= 3                                 # the layer was held for at least two slots
    assert len(h.leases) == 1
    # reset when the demand returns: h <= N clears the accumulators; a new surplus starts again from 0
    h2 = _Hand(inst, NoticeCriticalRatio(), prepaid=0)
    h2.step(0, [2.0])
    h2.step(1, [low])
    assert h2.pol.acc[0].get(2, 0.0) > 0
    h2.step(2, [2.0])
    assert h2.pol.acc[0] == {}
    h2.step(3, [low])
    assert abs(h2.pol.acc[0][2] - max(0.0, th - x2) * rate * Ds) <= 1e-12
    # release 'now': the surplus goes at once
    h3 = _Hand(inst, NoticeCriticalRatio(release="now"), prepaid=0)
    h3.step(0, [2.0])
    assert len([a for a in h3.step(1, [low]) if isinstance(a, Release)]) == 1
    # the explicit-h form of target: h = 2 against N = 1 keeps layer 2 while the waste is below the charge
    p4 = _pol(view)
    p4.d_prev = _dem(inst, [[2.0] * 5])
    assert list(p4.target(_obs(inst, 1, [low]), h=[2])) == [2] and list(p4.target(_obs(inst, 1, [low]), h=[1])) == [1]


# ---------------------------------------------------------------- A9.3
def test_c2_contract_table():
    """C37: c2_contract_table's Rev, P3 and kbar against p1_mask and p3_mask, the billed terms, k_p, the usable sites
    and l0/l_p by hand, the insurance flags against c2rule.insure_up_front(c2rule.c2_units(...)); without insure no
    test runs; a9.contract_table caches the table read-only per instance."""
    contracts = [("h0", 5, 0), ("h15", 5, 15), ("t60", 60, 5), ("dear", 5, 15), ("z", 120, 0)]
    prices = {"h0": 2.85, "h15": 2.85, "t60": 2.80, "dear": 3.2, "z": 6.5}
    for a_prot in (None, 4.0):
        inst, view = _menu_instance(contracts, prices, a_prot=a_prot)
        l0, lp = site_index(inst, "L0"), site_index(inst, "P")
        tab = c2_contract_table(view, insure=True)
        P1 = p1_mask(view)
        flag = np.array([treated_as_protected(view, k) for k in range(inst.K)])
        assert flag[_kid(inst, "z")] and flag[_kid(inst, "prot")] and not flag[_kid(inst, "h0")]
        assert np.array_equal(tab["rev"], P1 & ~flag[None, :])
        assert not tab["rev"][l0, _kid(inst, "dear")]                       # dominated by h15 (P1)
        assert np.array_equal(tab["p3"], p3_mask(view, P1) & tab["rev"][:, None, :])
        assert {inst.contracts[k].id for k in np.flatnonzero(tab["p3"][l0, 0])} == {"h15", "t60"}
        assert tab["kbar"][l0, 0] == _kid(inst, "t60") and tab["kbar"][lp, 0] == -1
        for k, c in enumerate(inst.contracts):
            want = c.prepaid_min if flag[k] else max(c.prepaid_min, c.D_min(5))
            assert tab["b_min"][k] == want, c.id
        assert tab["kp"][l0] == _kid(inst, "z") and tab["kp"][lp] == _kid(inst, "prot")
        g, q = view.llms[0].g, view.llms[0].q_usd_per_h
        assert abs(tab["sigma"][0, l0] - g * 2.80) <= TOL and np.isinf(tab["sigma"][0, lp])
        assert tab["usable"][0].tolist() == [True, False] and tab["l0"][0] == l0
        sp = {l: g * float(view.price[l, tab["kp"][l]]) for l in (l0, lp)}
        assert all(v < q for v in sp.values()) and np.isfinite(tab["sigma_p"][0]).all()
        want_lp = min(sp, key=lambda l: (sp[l], l))
        assert tab["lp"][0] == want_lp == lp
        a, ap = 2.80 / q, float(view.price[lp, _kid(inst, "prot")]) / q
        assert (ap <= a * (2 - a)) == (a_prot is not None)        # 4.0: decided without lb_react; 5.97: with it
        u = c2rule.c2_units(view, 0, l0, int(tab["kbar"][l0, 0]), l_prot=want_lp, k_prot=int(tab["kp"][want_lp]),
                            rep_site=l0)
        assert bool(tab["insured"][0]) == bool(c2rule.insure_up_front(u, "lb_react"))
        assert tab["c2"][0]["insure"] == bool(tab["insured"][0]) and abs(tab["c2"][0]["alpha"] - u.alpha) <= TOL
        off = c2_contract_table(view, insure=False)
        assert not off["insured"].any() and off["c2"] == [None]
        for key in ("kbar", "b_min", "rev", "p3", "kp", "sigma", "usable", "l0", "sigma_p", "lp"):
            assert np.array_equal(off[key], tab[key]), key
        calls, hits = a9.TABLE_STATS["calls"], a9.TABLE_STATS["hits"]
        c1 = a9.contract_table(view, insure=True)
        c2 = a9.contract_table(view, insure=True)
        assert c1 is c2 and a9.TABLE_STATS["calls"] == calls + 2 and a9.TABLE_STATS["hits"] >= hits + 1
        assert not c1["kbar"].flags.writeable and np.array_equal(c1["kbar"], tab["kbar"])
    # cheap protection (alpha_p <= alpha (2 - alpha)): insured, and an insured client buys only k_p at its flagged
    # sites, with theta at (l_p, k_p)
    inst = toy_instance({"prices.a_protected_usd_per_gpu_h": 4.0, "lenders.0.R": [], "lenders.1.R": []})
    lp = site_index(inst, "P")
    res = simulate(inst, NoticeCriticalRatio(), LenderModel(), EngineConfig(check_invariants=True), policy_seed=0)
    assert not res.invariant_failures and res.leases
    assert {(L.site, inst.contracts[L.contract].id) for L in res.leases} == {(lp, "prot")}
    rep = res.metrics["policy"]["a9"]
    assert rep["insured"] == 1 and rep["insured_flags"] == [True] and rep["site_c"] == [lp]
    assert abs(rep["theta"][0] - 4.0 / inst.llms[0].q_usd_per_h) <= TOL
    off = simulate(inst, NoticeCriticalRatio(insure=False), LenderModel(), EngineConfig(check_invariants=True),
                   policy_seed=0)
    assert lp not in {L.site for L in off.leases} and off.metrics["policy"]["a9"]["insured"] == 0


def test_commitment_rule():
    """A9.3's commitment rule: a layer of age A may use k' in Rev(l) only if b_k' - min b <= Δs max(1, A); it buys
    argmin (a, b, k) over the allowed contracts in P3, else argmin (-H, a, k); with commit false A9 buys kbar."""
    contracts = [("h0", 5, 0), ("h15", 5, 15), ("t60", 60, 5)]
    prices = {"h0": 2.85, "h15": 2.85, "t60": 2.80}
    inst, view = _menu_instance(contracts, prices)
    l0 = site_index(inst, "L0")
    h0, h15, t60 = (_kid(inst, x) for x in ("h0", "h15", "t60"))
    pol = _pol(view)
    b = pol.b_min
    assert (b[h0], b[h15], b[t60]) == (5.0, 20.0, 65.0)
    assert pol.kb[l0, 0] == t60 and not pol.p3[l0, 0, h0] and pol.p3[l0, 0, h15]
    for A in (0, 1, 2, 3, 11, 12):
        want = [k for k in (h0, h15, t60) if b[k] - 5.0 <= 5 * max(1, A)]
        assert pol.commit_allowed(l0, A) == want, A
    assert pol.commit_contract(l0, 0, 1) == (h0, False)          # only h0 allowed, not in P3: longest notice
    assert pol.commit_contract(l0, 0, 3) == (h15, True)
    assert pol.commit_contract(l0, 0, 11) == (h15, True)          # 65 - 5 = 60 > 55
    assert pol.commit_contract(l0, 0, 12) == (t60, True)          # cheapest allowed P3 contract
    # through act: the layer's age at each purchase (a death at slot 3 leaves a layer of age 4)
    h = _Hand(inst, NoticeCriticalRatio(), prepaid=0)
    h.step(0, [1.0])
    for t in (1, 2):
        h.step(t, [1.0])
    lid = h.buys[0][1]
    h.step(3, [1.0], kill=[(lid, "reclaim")])
    assert [a.contract for _, _, a in h.buys] == [h0, h15]
    st = h.pol.report()["a9"]
    assert st["commit_fallbacks"] == 2 and st["commit_no_p3"] == 1
    assert st["contracts"] == {"h0": 1, "h15": 1}
    hn = _Hand(inst, NoticeCriticalRatio(commit=False), prepaid=0)
    hn.step(0, [1.0])
    assert [a.contract for _, _, a in hn.buys] == [t60]
    hk = _Hand(inst, NoticeCriticalRatio(contract_rule="kstar"), prepaid=0)
    hk.step(0, [1.0])
    assert [a.contract for _, _, a in hk.buys] == [int(hk.pol.sites.kstar[l0])]


# ---------------------------------------------------------------- A9.4
def test_mbb_timing():
    """A9.4: a noticed lease counts until u_L = latest_prewarm_slot(r, E, lam^max_c) (the largest load time over the
    usable sites, flagged ones included), then the deficit buys its replacement at u_L while the noticed lease is
    neither counted nor released; u_L = r when no pre-warm slot exists; with mbb false the replacement waits for
    the death; before u_L a noticed lease can be released as surplus."""
    inst = toy_instance({"time.fast_slot_min": 1, "borrowers.clients.0.demand.values": [0.0] * 120,
                         "contracts.0.H_min": 30, "lenders.0.R": [], "lenders.1.R": []})
    view = public_view(inst, "I1")
    pol = _pol(view)
    lam = np.round(1000 * np.asarray(view.lam_s)).astype(int)
    assert pol.lam_c[0] == lam[0].max() == 600000                  # the protected site's 600 s
    r = 2
    for mbb in (True, False):
        h = _Hand(inst, NoticeCriticalRatio(mbb=mbb, commit=False), prepaid=0)
        h.step(0, [1.0])
        h.step(1, [1.0])
        (_, lid, b0), = h.buys
        assert inst.contracts[b0.contract].id == "short"
        E = r * 5 + 30
        u = latest_prewarm_slot(r, E, 600000, view.grid)
        assert u is not None and r < u < E // 5
        for t in range(r, E // 5):
            acts = h.step(t, [1.0], notices=[(lid, E)] if t == r else ())
            buys = [a for a in acts if isinstance(a, Buy)]
            assert not [a for a in acts if isinstance(a, Release)], t
            assert len(buys) == (1 if (mbb and t == u) else 0), (mbb, t, buys)
            if mbb:
                assert h.pol.u[lid] == u
                assert (lid in h.pol._counted[0]) == (t < u), t
        acts = h.step(E // 5, [1.0], kill=[(lid, "reclaim")])
        assert len([a for a in acts if isinstance(a, Buy)]) == (0 if mbb else 1), mbb
    # no pre-warm slot (H = 0 at a 1-slot guarantee: E = 5 r): u_L = r
    inst0 = toy_instance({"time.fast_slot_min": 1, "borrowers.clients.0.demand.values": [0.0] * 120,
                          "contracts.0.H_min": 0, "lenders.0.R": [], "lenders.1.R": []})
    h = _Hand(inst0, NoticeCriticalRatio(commit=False), prepaid=0)
    h.step(0, [1.0])
    lid = h.buys[0][1]
    assert latest_prewarm_slot(1, 5, 600000, h.view.grid) is None
    acts = h.step(1, [1.0], notices=[(lid, 5)])
    assert h.pol.u[lid] == 1 and len([a for a in acts if isinstance(a, Buy)]) == 1
    # before u_L the noticed lease is released as surplus (release 'now', demand 0)
    h = _Hand(inst, NoticeCriticalRatio(release="now", commit=False), prepaid=0)
    h.step(0, [1.0])
    lid = h.buys[0][1]
    h.step(1, [1.0], notices=[(lid, 35)])
    acts = h.step(2, [0.0])
    assert [a for a in acts if isinstance(a, Release)] == [Release(lid)]


# ---------------------------------------------------------------- A9.5
def test_marking_expiry_and_phase_end():
    """A9.5: an own notice, or a 'reclaim'/'violation' end without an earlier notice, marks its site (excess 0,
    budget max_j ell, last hit); purchases go to the least key sigma + (beta~ + [marked] ell) / T; a mark expires
    once the counted leases at dearer sites have paid its budget in excess score; when every usable site is
    marked the marks are cleared (a phase end); equal keys go to the least recently hit site."""
    inst = toy_instance({"lenders.1.prices.short": 5.0, "lenders.1.prices.long": 5.2, "lenders.0.R": [],
                         "lenders.1.R": []})
    l0, l1 = site_index(inst, "L0"), site_index(inst, "L1")
    h = _Hand(inst, NoticeCriticalRatio(commit=False, mbb=False), prepaid=0)
    pol = h.pol
    bt = np.asarray(h.view.beta_tilde_usd)
    k = _kid(inst, "short")
    assert pol.kb[l0, 0] == pol.kb[l1, 0] == k
    ell0 = bt[0, l0, k]                                     # 60 H = 300 s is not below lambda = 300 s
    assert abs(pol.ell[l0, 0] - ell0) <= TOL and abs(pol.site_budget[l0] - ell0) <= TOL
    T = 10 / 60
    key = lambda l, marked: pol.sigma[0, l] + (bt[0, l, k] + (pol.ell[l, 0] if marked else 0.0)) / T
    assert pol.site_key(0, l0) == (key(l0, False), -1, l0)
    h.step(0, [1.0])
    assert h.buys[-1][2].site == l0
    lid = h.buys[-1][1]
    h.step(1, [1.0], notices=[(lid, 10)])
    assert pol.marked[l0] and pol.excess[l0] == 0.0 and pol.last_hit[l0] == 1 and pol.stats["marks"] == 1
    assert key(l1, False) < key(l0, True)
    acts = h.step(2, [1.0], kill=[(lid, "reclaim")])                # noticed earlier: no second mark
    assert pol.stats["marks"] == 1
    assert [a.site for a in acts if isinstance(a, Buy)] == [l1]
    # expiry: the lease at L1 pays (sigma_L1 - sigma_L0) Δs/60 per slot toward L0's budget
    inc = (pol.sigma[0, l1] - pol.sigma[0, l0]) * 5 / 60
    t, exc = 3, 0.0
    while pol.marked[l0]:
        h.step(t, [1.0])
        exc += inc
        if exc < pol.site_budget[l0]:
            assert pol.marked[l0] and abs(pol.excess[l0] - exc) <= 1e-12, t
        else:
            assert not pol.marked[l0] and pol.stats["mark_expiries"] == 1, t
        t += 1
        assert t < 30
    # a 'violation' end without notice marks; a 'release' end does not
    lid1 = h.buys[-1][1]
    h.step(t, [1.0], kill=[(lid1, "violation")])
    assert pol.marked[l1] and pol.last_hit[l1] == t and pol.stats["marks"] == 2
    assert h.buys[-1][2].site == l0
    lid2 = h.buys[-1][1]
    h.step(t + 1, [0.0])                    # kept: the waste of one slot is below the charge of the load at f*
    assert lid2 in h.leases
    h.step(t + 2, [0.0])                    # f* = 0: nothing left to strand, released
    assert lid2 not in h.leases
    acts = h.step(t + 3, [1.0])             # its end 'release' is reported now and marks nothing
    assert pol.stats["marks"] == 2 and [a.site for a in acts if isinstance(a, Buy)] == [l0]
    # phase end: both usable sites marked, the next purchase clears them and buys at the least key
    lid3 = h.buys[-1][1]
    h.step(t + 4, [1.0], notices=[(lid3, (t + 5) * 5)])
    assert pol.marked[l0] and pol.marked[l1] and pol.stats["marks"] == 3
    acts = h.step(t + 5, [1.0], kill=[(lid3, "reclaim")])
    assert pol.stats["phase_ends"] == 1 and [a.site for a in acts if isinstance(a, Buy)] == [l0]
    assert not pol.marked[l1] and not pol.marked[l0] and pol.stats["marks"] == 3


def test_guard_release_is_not_a_death():
    """§2.4 step 1: a lease that a guard around A9 released (A8P's K0 or a projected list) appears in obs.ended with
    cause 'release' although A9 did not release it; A9 neither marks its site nor counts it as a death, and reports
    it as guard_released. A 'reclaim' end without notice is a death and marks its site."""
    inst = toy_instance({"lenders.1.prices.short": 5.0, "lenders.1.prices.long": 5.2, "lenders.0.R": [],
                         "lenders.1.R": []})
    h = _Hand(inst, NoticeCriticalRatio(commit=False, mbb=False), prepaid=0)
    pol = h.pol
    h.step(0, [1.0])
    lid = h.buys[-1][1]
    h.step(1, [1.0], kill=[(lid, "release")])
    assert pol.counts["deaths"] == 0 and pol.stats["guard_released"] == 1 and pol.stats["marks"] == 0
    assert not pol.marked.any() and lid not in pol._released
    lid2 = h.buys[-1][1]
    assert lid2 != lid
    h.step(2, [1.0], kill=[(lid2, "reclaim")])
    assert pol.counts["deaths"] == 1 and pol.stats["guard_released"] == 1 and pol.stats["marks"] == 1
    assert pol.report()["a9"]["guard_released"] == 1


def test_lru_tie_and_static_rules():
    """A9.5's tie: on sites with equal prices, load times and contracts the keys tie and the least recently hit
    site wins (never hit first, then the site id), not the site index; site_rule 'static' is BL1's (sigma, pi)
    order with no marking; 'noticed' avoids the sites of own leases under notice."""
    inst = toy_instance({"lenders.1.prices.short": 2.85, "lenders.1.prices.long": 3.0, "lenders.0.R": [],
                         "lenders.1.R": []})
    l0, l1 = site_index(inst, "L0"), site_index(inst, "L1")
    h = _Hand(inst, NoticeCriticalRatio(commit=False, mbb=False), prepaid=0)
    pol = h.pol
    assert pol.site_key(0, l0)[0] == pol.site_key(0, l1)[0]
    h.step(0, [1.0])
    assert h.buys[-1][2].site == l0                         # never hit: the lower id
    a = h.buys[-1][1]
    h.step(1, [1.0], kill=[(a, "reclaim")])                  # L0 hit at 1
    assert h.buys[-1][2].site == l1
    b = h.buys[-1][1]
    h.step(2, [1.0], kill=[(b, "reclaim")])                  # L1 hit at 2; phase end; L0 least recently hit
    assert pol.stats["phase_ends"] == 1 and h.buys[-1][2].site == l0
    c = h.buys[-1][1]
    h.step(3, [1.0], kill=[(c, "reclaim")])                  # L0 hit at 3: L1 unmarked
    assert h.buys[-1][2].site == l1
    d = h.buys[-1][1]
    h.step(4, [1.0], kill=[(d, "reclaim")])                  # both marked: phase end, L0 (3) before L1 (4)
    assert h.buys[-1][2].site == l0 and pol.stats["phase_ends"] == 2
    # equal keys and no mark: the least recently hit site wins although its id is higher; tie 'rank' uses the
    # public layer rank (0 on synthetic sites), then pi (the index here)
    for tie, want in (("lru", l1), ("rank", l0)):
        hh = _Hand(inst, NoticeCriticalRatio(commit=False, tie=tie), prepaid=0)
        hh.pol.last_hit[[l0, l1]] = [5, 3]
        hh.step(0, [1.0])
        assert hh.buys[-1][2].site == want, tie
    # 'static': BL1's order (sigma, pi), no marks; 'noticed': the noticed site is avoided
    for rule in ("static", "noticed"):
        hs = _Hand(inst, NoticeCriticalRatio(site_rule=rule, commit=False), prepaid=0)
        assert hs.pol.order_static[0] == hs.pol.sites.order[0]
        hs.step(0, [1.0])
        first = hs.buys[-1][1]
        hs.step(1, [2.0], notices=[(first, 30)])
        assert hs.pol.stats["marks"] == 0
        assert hs.buys[-1][2].site == (l1 if rule == "noticed" else hs.pol.sites.order[0][0]), rule


# ---------------------------------------------------------------- the T4/O1 family
@pytest.mark.parametrize("fam_params", DEV_FAMILIES)
def test_equals_rr_renew_on_family(fam_params):
    """§2.2 A9.5 / §8.3: on from_core exports of the T4/O1 family at the development folder's fresh (m, rho, tau,
    H, T), A9 equals family.RRRenew in total cost, purchase count and purchase sites, under the adaptive, eager,
    safe-site and iid_step (p = 0.5) lenders (lender seeds 0-2 for the oblivious random ones)."""
    m, rho, tau, H, T = fam_params
    I = fam.Fam(m, rho, tau, H, T).core_instance()
    rotated = 0
    for md, (sched, par, seeds) in FAM_MODES.items():
        for ls in seeds:
            runs = {}
            for name, mk in (("RR", RRRenew), ("A9", NoticeCriticalRatio)):
                inst, _ = from_core(I, [np.zeros(0, dtype=np.int64)] * m)
                res = simulate(inst, mk(), LenderModel(schedule=sched, information="I1", params=dict(par)),
                               EngineConfig(check_invariants=True), lender_seed=ls, policy_seed=0)
                assert not res.invariant_failures, (name, md, ls)
                runs[name] = (res.components["total"], len(res.leases), [L.site for L in res.leases])
            assert runs["A9"] == runs["RR"], (fam_params, md, ls, runs)
            rotated += len(set(runs["A9"][2])) == m
    assert rotated >= 1, fam_params                 # a run that visits every site (a full RR-renew cycle)


# ---------------------------------------------------------------- engine runs on layer sites
def test_defaults_seed_independence_and_plan_class():
    """§8.3: A9 with every flag at its default equals A9 built with no parameters; its ledger is identical under
    policy seeds 0 and 1 although the site order pi differs (no rule reads pi or the policy's streams at the
    defaults); the run is in plan class P1 (single-replica Buys at admission 1 and Releases only) with no
    invariant failure; report() carries A9's counters."""
    inst = _ms()
    cfg = EngineConfig(check_invariants=True)
    runs, pis = {}, {}
    for tag, kw, seed in (("noparam", {}, 0), ("defaults", dict(NoticeCriticalRatio.PARAMS), 0), ("seed1", {}, 1)):
        pol = NoticeCriticalRatio(**kw)
        acts = []
        o_act = pol.act

        def act(obs, o_act=o_act, acts=acts):
            out = o_act(obs)
            acts.extend(out)
            return out

        pol.act = act
        res = simulate(inst, pol, LenderModel(schedule="trace"), cfg, lender_seed=0, policy_seed=seed)
        assert not res.invariant_failures, (tag, res.invariant_failures[:3])
        assert {type(a).__name__ for a in acts} <= {"Buy", "Release"} and any(isinstance(a, Buy) for a in acts)
        assert all(a.n_replicas == 1 and a.admission == 1.0 for a in acts if isinstance(a, Buy))
        runs[tag], pis[tag] = res, pol.pi.tolist()
    assert any(s.kind == "layer" for s in inst.sites) and pis["noparam"] != pis["seed1"]
    _same_ledger(runs["noparam"], runs["defaults"], "defaults")
    _same_ledger(runs["noparam"], runs["seed1"], "policy seed")
    rep = runs["noparam"].metrics["policy"]
    assert rep["params"] == NoticeCriticalRatio.PARAMS
    for key in ("marks", "phase_ends", "mark_expiries", "notices", "commit_fallbacks", "commit_no_p3",
                "guard_released", "contracts", "insured", "insured_flags"):
        assert key in rep["a9"], key
    assert sum(rep["a9"]["contracts"].values()) == rep["counts"]["buys"] >= len(runs["noparam"].leases) > 0
    json.dumps(rep, allow_nan=False)
