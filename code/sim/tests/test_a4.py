"""Tests of marking under public information and policy A4 (sublet/algos/marking.py, a4.py;
design/sim_spec_ms2.md §8.1, §8.3; §17.2).

The marking site rule (MarkingSiteRule) is driven by hand-made observations on the synthetic three-site
instance of test_execution._three_sites (S0, S1 in region r0, S2 in r1), or through the engine with a
constant planner around an ExecutionLayer whose site rule is a MarkingSiteRule with its own generator;
the expected draws are replayed with a copy of that generator.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from fixtures import CONFIGS, load_json, toy_instance

from test_execution import _sites_of, _three_sites

from sublet.algos.a4 import A4
from sublet.algos.common import LeaseBook
from sublet.algos.execution import ExecutionLayer
from sublet.algos.handler import ReclaimHandler
from sublet.algos.marking import MarkState, MarkingSiteRule, harmonic
from sublet.engine import simulate
from sublet.instance import build_instance, public_view
from sublet.policies.base import Policy
from sublet.timing import latest_prewarm_slot, warm_fast
from sublet.types import Buy, LeaseView, LenderModel, Notice, Release, SlowObs

KEY = (0, 0, 0, 0)


def _obs(inst, t, *, leases=(), notices=(), D=None, site_announced=None):
    n, phi = inst.n, inst.grid.phi
    dem = np.ones((n, phi)) if D is None else np.repeat(np.asarray(D, dtype=float).reshape(n, 1), phi, axis=1)
    return SlowObs(t=t, minute=t * inst.grid.slow_min, demand=dem, leases={L.id: L for L in leases}, replicas={},
                   notices=list(notices), ended=[], results=[], site_announced=site_announced,
                   served_prev=np.zeros((inst.J, inst.m)), fallback_prev=np.zeros(n), cost_so_far=0.0)


def _layer(inst, info="I2", seed=0, **mk):
    """(view, book, layer, rule) with a MarkingSiteRule(mode 'marking' unless given) on `inst`."""
    v = public_view(inst, info)
    book = LeaseBook()
    mk.setdefault("mode", "marking")
    rule = MarkingSiteRule(v, np.random.default_rng(seed), **mk)
    layer = ExecutionLayer(v, book, x3=True, x2="reference", site_rule=rule,
                           handler=ReclaimHandler(v, reaction="cold"))
    return v, book, layer, rule


def _lv(lid, site, start=0, ann=None, death=None):
    return LeaseView(lid, site, 0, 1, start, 5 * start, 5 * start + 10, ann, death, ())


class _Draws:
    """Replays MarkingSiteRule._draw: sites[integers(len(sites))] on a copy of the rule's generator."""

    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)

    def __call__(self, sites):
        return int(sites[int(self.rng.integers(len(sites)))])


# ---------------------------------------------------------------- MarkState and groups
def test_mark_state_next_phase_ceil():
    """§8.1: the next phase starts at ceil((t1 Δs + H) / Δs): H = 7 min, Δs = 5, t1 = 1 gives slot 3 (floor
    would give 2); H = 10 gives 3 as well, H = 0 gives t1."""
    for H, want in ((7, 3), (10, 3), (0, 1), (11, 4)):
        st = MarkState(range(2), 1, H, 5)
        st.start(0)
        newly, unm = st.update(1, np.array([True, True]))
        assert newly == [0, 1] and unm == [] and not st.running and st.next_start == want, (H, st.next_start)
        assert st.phases == [[0, 1]]


def test_groups_and_rho_P():
    """§8.3 (M19, M20): slots of one LLM and contract with equal X3 pools share a mark group, slots with
    different pools get different groups; rho_P is the maximum over the pool of rho_ljk."""
    T = 24
    inst = _three_sites(([], [], []), [("r0", "strict", [1] * T), ("r1", "strict", [1] * T)])
    v, book, layer, rule = _layer(inst)
    for key in ((0, 0, 0, 0), (1, 0, 0, 0), (2, 0, 0, 0)):
        layer.open(key, t0=0, s=0, L=T)
    obs = _obs(inst, 0)
    book.begin(obs)
    layer.step(obs)
    s0, s1, s2 = (layer.slots[k] for k in ((0, 0, 0, 0), (1, 0, 0, 0), (2, 0, 0, 0)))
    assert s0.group == s1.group == (0, 0, (0, 1)) and s2.group == (0, 0, (2,))
    assert len(rule.groups) == 2 and rule.groups[s0.group].slots == [(0, 0, 0, 0), (1, 0, 0, 0)]
    # rho_P = max over the pool: L1's 'short' dearer than L0's
    t = toy_instance({"lenders.1.prices.short": 6.0})
    vt = public_view(t, "I2")
    mr = MarkingSiteRule(vt, np.random.default_rng(0))
    r0, r1 = mr.rho(0, 0, 0), mr.rho(0, 1, 0)
    assert r0 != r1
    mode, rho_P = mr._group_mode(0, 0, (0, 1))
    assert rho_P == max(r0, r1)
    assert mode == ("marking" if 2.0 * harmonic(2) + 1.0 < rho_P else "rr")


# ---------------------------------------------------------------- MK1
def test_mk1_fresh_lease_released_when_warm():
    """§8.3 MK1 (M17): at a phase start a slot with need[t0] and an alive lease draws a uniform site of P and
    buys a fresh lease there (also if the draw is its own site); the old lease is released at the first slow
    slot in which the new replica is warm (lambda' = 420 s bought at minute 15, Δf = 1: slot 5), not at t0;
    with rebuy_at_phase_start=False it keeps its lease and draws nothing; a slot without need draws nothing."""
    inst = _three_sites(([], [], []), [("r0", "strict", [1] * 24)], lam=420.0, fast=1)
    t_w = -(-warm_fast(15, 420_000, 1) // inst.grid.phi)
    assert t_w == 5
    for rebuy in (True, False):
        v, book, layer, rule = _layer(inst, seed=3, rebuy_at_phase_start=rebuy)
        layer.open(KEY, t0=0, s=0, L=24)
        sl = layer.slots[KEY]
        lv = _lv(7, 0)
        obs = _obs(inst, 3, leases=[lv])
        book.begin(obs)
        sl.lease, sl.lease_site = 7, 0
        g, new = rule._group(sl, obs, 3)
        assert new and g.state.sites == (0, 1)
        draw = _Draws(3)
        rule._phase_start(g, obs, 3)
        acts = book.assemble(obs, v)
        if rebuy:
            site = draw([0, 1])
            assert acts == [Buy(site, 0, 0, 1, tag="move")], acts
            assert sl.retiring == [(7, t_w)] and sl.ptr == site and rule.stats["mk1_moves"] == 1
        else:
            assert acts == [] and sl.retiring == [] and rule.stats["draws"] == 0
    # no need at t0: no draw
    v, book, layer, rule = _layer(inst, seed=3)
    layer.open(KEY, t0=0, s=0, L=2)
    sl = layer.slots[KEY]
    obs = _obs(inst, 3, leases=[_lv(7, 0)])
    book.begin(obs)
    sl.lease, sl.lease_site = 7, 0
    g, _ = rule._group(sl, obs, 3)
    rule._phase_start(g, obs, 3)
    assert rule.stats["draws"] == 0 and book.assemble(obs, v) == []


def test_mk1_keeps_planned_of_skipped_slots():
    """§8.3 MK1: a slot that draws nothing at a phase start (no need, a pending pre-warm or a pre-warmed next
    lease, or rebuy off) keeps its planned replacement site; a slot that draws gets a new one."""
    inst = _three_sites(([], [], []), [("r0", "strict", [1] * 24)])
    v, book, layer, rule = _layer(inst, seed=1, rebuy_at_phase_start=False)
    layer.open(KEY, t0=0, s=0, L=24)
    sl = layer.slots[KEY]
    obs = _obs(inst, 3, leases=[_lv(7, 0, ann=2, death=40)])
    book.begin(obs)
    sl.lease, sl.lease_site, sl.noticed = 7, 0, True
    g, _ = rule._group(sl, obs, 3)
    rule.planned[KEY] = 1
    rule._phase_start(g, obs, 3)                    # alive and rebuy off: skipped
    assert rule.planned == {KEY: 1} and rule.next_site(sl, obs, 3) == 1
    # a dead lease draws: the drawn site replaces the planned one
    v, book, layer, rule = _layer(inst, seed=1)
    layer.open(KEY, t0=0, s=0, L=24)
    sl = layer.slots[KEY]
    obs = _obs(inst, 3)
    book.begin(obs)
    sl.lease, sl.lease_site = 7, 0                  # held, absent from obs.leases: died at t
    g, _ = rule._group(sl, obs, 3)
    rule.planned[KEY] = 1
    draw = _Draws(1)
    rule._phase_start(g, obs, 3)
    site = draw([0, 1])
    assert rule.planned == {KEY: site} and sl.ptr == site and sl.ptr_moved


def test_mk1_drops_planned_of_skipped_slots_without_lease():
    """§8.3 MK1 (F11): a slot that holds no lease and draws nothing at a phase start (no need at t0) drops its
    planned site: it has no lease to replace, and the site was drawn in an earlier phase. Its next purchase in
    the new phase is placed by the rule for a re-buy in a running phase (its pointer if unmarked, else a uniform
    unmarked site), so it does not go to the old planned site S1 once S1 is marked in the new phase."""
    inst = _three_sites(([], [], []), [("r0", "strict", [1] * 24)])
    v, book, layer, rule = _layer(inst, seed=1)
    layer.open(KEY, t0=0, s=0, L=2)                 # need [0, 2) only
    sl = layer.slots[KEY]
    obs = _obs(inst, 3)
    book.begin(obs)
    g, _ = rule._group(sl, obs, 3)
    assert g.state.sites == (0, 1)
    sl.held_before, sl.last_end = True, "released"  # its lease was released by X2 in the last phase
    rule.planned[KEY] = 1                           # the replacement site drawn for that lease
    rule._phase_start(g, obs, 3)
    assert rule.planned == {} and rule.stats["draws"] == 0 and sl.ptr == 0
    assert book.assemble(obs, v) == []
    # S1 announced at slot 4 = p + tau: marked; the slot's pointer S0 is not, so MK2 does nothing
    o4 = _obs(inst, 4, site_announced=np.array([False, True, False]))
    book.begin(o4)
    layer.step(o4)
    assert g.state.mark == {0: None, 1: 4} and book.assemble(o4, v) == []
    # a new window at slot 5: the re-buy goes to the unmarked pointer S0
    o5 = _obs(inst, 5)
    book.begin(o5)
    layer.open(KEY, t0=5, s=5, L=2)
    layer.step(o5)
    assert book.assemble(o5, v) == [Buy(0, 0, 0, 1, tag="x1")]
    assert layer.report()["purchases"]["rebuy"] == 1 and rule.stats["draws"] == 0


# ---------------------------------------------------------------- MK2
def _mk2_setting(inst, *, move_at, announced, need=True, seed=0):
    v, book, layer, rule = _layer(inst, seed=seed, move_at=move_at)
    layer.open(KEY, t0=0, s=0, L=24 if need else 2)
    sl = layer.slots[KEY]
    lv = _lv(7, 0, ann=3 if announced else None, death=40 if announced else None)
    obs = _obs(inst, 3, leases=[lv], notices=[Notice(7, 3, 40)] if announced else [])
    book.begin(obs)
    sl.lease, sl.lease_site = 7, 0
    g, _ = rule._group(sl, obs, 0)
    g.state.start(0)
    return v, book, layer, rule, sl, g, obs


def test_mk2_hit_and_not_hit():
    """§8.3 MK2: when the slot's current site is marked at t and unmarked sites remain, the slot draws a uniform
    unmarked site. move_at='handler': hit (own lease announced at t): no purchase at t, the site goes to the
    handler (planned, next_site); not hit: a fresh lease at the drawn site at t, the old lease released when
    the new replica is warm. move_at='mark': a fresh lease at t and the old lease released at t in both cases.
    A slot that needs no coverage at t moves its pointer only (no fresh lease without need, as MK1)."""
    inst = _three_sites(([], [], []), [("r0", "strict", [1] * 24)], lam=420.0, fast=1)
    t_w = -(-warm_fast(15, 420_000, 1) // inst.grid.phi)
    for move_at in ("handler", "mark"):
        for announced in (True, False):
            v, book, layer, rule, sl, g, obs = _mk2_setting(inst, move_at=move_at, announced=announced)
            rule._mk2(g, obs, 3, {0}, [1])
            acts = book.assemble(obs, v)
            tag = (move_at, announced)
            if move_at == "handler" and announced:
                assert acts == [] and rule.planned == {KEY: 1} and sl.lease == 7, tag
                assert rule.stats["mk2_hits"] == 1 and rule.next_site(sl, obs, 3) == 1, tag
            elif move_at == "handler":
                assert acts == [Buy(1, 0, 0, 1, tag="move")] and sl.retiring == [(7, t_w)], (tag, acts)
            else:
                assert Buy(1, 0, 0, 1, tag="move") in acts and Release(7) in acts and sl.retiring == [], (tag, acts)
            assert rule.stats["draws"] == 1, tag
    for move_at in ("handler", "mark"):
        v, book, layer, rule, sl, g, obs = _mk2_setting(inst, move_at=move_at, announced=False, need=False)
        assert not sl.need[3]
        rule._mk2(g, obs, 3, {0}, [1])
        assert book.assemble(obs, v) == [] and sl.ptr == 1 and rule.planned == {KEY: 1}, move_at
        assert rule.stats["mk2_places"] == 1 and rule.stats["mk2_moves"] == 0


def test_death_outside_a_move():
    """§8.3: under marking, the replacement site at a notice or a death outside a phase move is the slot's
    current site if it is unmarked (no draw), else a uniform unmarked site, else the X3 next site (phase
    over); the drawn site is kept until the slot's next purchase."""
    inst = _three_sites(([], [], []), [("r0", "relaxed", [1] * 24)])
    v, book, layer, rule = _layer(inst, seed=2)
    layer.open(KEY, t0=0, s=0, L=24)
    sl = layer.slots[KEY]
    obs = _obs(inst, 3)
    book.begin(obs)
    g, _ = rule._group(sl, obs, 0)
    assert g.state.sites == (0, 1, 2)
    g.state.start(0)
    sl.lease, sl.lease_site = 7, 1
    assert rule.next_site(sl, obs, 3) == 1 and rule.stats["death_draws"] == 0      # current site unmarked
    rule.planned.clear()
    g.state.mark[1] = 2                                                             # current site marked
    draw = _Draws(2)
    site = rule.next_site(sl, obs, 3)
    assert site == draw([0, 2]) and rule.stats["death_draws"] == 1 and rule.planned == {KEY: site}
    assert rule.next_site(sl, obs, 4) == site                                       # kept until the next purchase
    rule.on_buy(sl, site, 4)
    assert rule.planned == {}
    for l in (0, 2):
        g.state.mark[l] = 2
    g.state.running = False                                                          # MK3: no unmarked site
    assert rule.next_site(sl, obs, 5) == rule.rr.next_site(sl, obs, 5)


def test_marking_on_i1_reads_no_i2_field():
    """M18 with require_I2=False: a MarkingSiteRule on an I1 view never reads obs.site_announced (nothing is
    marked under I1); under I2 it does."""
    inst = _three_sites(([], [], []), [("r0", "strict", [1] * 24)])
    for info in ("I1", "I2"):
        v, book, layer, rule = _layer(inst, info=info)
        layer.open(KEY, t0=0, s=0, L=24)
        obs = _obs(inst, 0)
        book.begin(obs)
        layer.step(obs)                                 # first purchase: group and phase 0
        assert rule.groups and next(iter(rule.groups.values())).state.running
        bare = SimpleNamespace(t=3)                     # no site_announced attribute
        if info == "I1":
            rule.on_slot(bare)
        else:
            try:
                rule.on_slot(bare)
                raised = False
            except AttributeError:
                raised = True
            assert raised


# ---------------------------------------------------------------- through the engine
class _MarkDriver(Policy):
    """A constant planner around an ExecutionLayer with a MarkingSiteRule(view, default_rng(seed), **mk) and
    a ReclaimHandler(view, reaction)."""
    name = "mark_driver"

    def __init__(self, opens, seed, reaction="cold", **mk):
        self.opens, self.seed, self.reaction, self.mk = opens, seed, reaction, mk

    def reset(self, view, rng):
        super().reset(view, rng)
        self.book = LeaseBook()
        self.rule = MarkingSiteRule(view, np.random.default_rng(self.seed), mode="marking", **self.mk)
        self.layer = ExecutionLayer(view, self.book, x3=True, x2="reference", site_rule=self.rule,
                                    handler=ReclaimHandler(view, reaction=self.reaction))

    def act(self, obs):
        self.layer.absorb(self.book.begin(obs))
        for key, s, L in self.opens.get(obs.t, ()):
            self.layer.open(key, t0=obs.t, s=s, L=L)
        self.layer.step(obs)
        return self.book.assemble(obs, self.view)

    def report(self):
        return self.layer.report()


def test_mk2_hit_prewarm_at_drawn_site():
    """§8.3 MK2 with move_at='handler' through the engine (I2, three feasible sites, H = 60 min, lambda' = 60 s,
    Δf = 1, forced pre-warm): phase 0 starts at the first purchase, which goes to the drawn site d0; d0 is
    announced at slot 10 (hit): the slot draws d1 among the unmarked sites and the handler pre-warms there at
    latest_prewarm_slot(10, 110) = 21; with move_at='mark' the slot buys at d1 at slot 10 and releases d0."""
    T = 40
    for seed in range(4):
        draw = _Draws(seed)
        d0 = draw([0, 1, 2])
        d1 = draw([l for l in (0, 1, 2) if l != d0])
        R = [[], [], []]
        R[d0] = [10]
        inst = _three_sites(tuple(R), [("r0", "relaxed", [1] * T)], H_min=60, lam=60.0, fast=1, T=T)
        assert latest_prewarm_slot(10, 110, 60_000, inst.grid) == 21
        pol = _MarkDriver({0: [(KEY, 0, T)]}, seed, reaction="prewarm_if_feasible", move_at="handler")
        res = simulate(inst, pol, LenderModel(information="I2"))
        assert res.invariant_failures == [], seed
        assert _sites_of(res) == [(d0, 0), (d1, 21)], (seed, d0, d1, _sites_of(res))
        tags = [L.tag for L in sorted(res.leases, key=lambda x: x.id)]
        assert tags == ["x1", "prewarm"]
        st = pol.rule.stats
        assert st["mk2_hits"] == 1 and st["phases"] == 1 and st["draws"] == 2, st
        pol2 = _MarkDriver({0: [(KEY, 0, T)]}, seed, reaction="prewarm_if_feasible", move_at="mark")
        res2 = simulate(inst, pol2, LenderModel(information="I2"))
        assert res2.invariant_failures == [], seed
        got = [(L.site, L.start_slot, L.end_min, L.end_cause) for L in sorted(res2.leases, key=lambda x: x.id)]
        assert got[0] == (d0, 0, 50, "release") and got[1][:2] == (d1, 10), (seed, got)


def test_mk3_wait_and_next_phase():
    """§8.3 MK3 through the engine (I2, pool {S0, S1}, tau 1 slot, H = 10 min, lambda = 0, Δf = Δs = 5,
    cold reaction): S0 is announced at 3 and S1 at 5, so the phase ends at t1 = 5 and the next phase starts
    at ceil((5 Δs + 10) / Δs) = 7; no purchase happens in slot 6 (the wait), and slot 7 buys at the site
    drawn at the phase start."""
    T = 12
    inst = _three_sites(([3], [5], []), [("r0", "strict", [1] * T)], H_min=10, T=T)
    for seed in range(4):
        draw = _Draws(seed)
        d0 = draw([0, 1])
        pol = _MarkDriver({0: [(KEY, 0, T)]}, seed, reaction="cold")
        res = simulate(inst, pol, LenderModel(information="I2"))
        assert res.invariant_failures == [], seed
        g = next(iter(pol.rule.groups.values()))
        assert [list(p) for p in g.state.phases] == [[0, 5], [7, None]], (seed, g.state.phases)
        starts = sorted(L.start_slot for L in res.leases)
        sites = _sites_of(res)
        if d0 == 0:
            # S0's lease announced at 3 (hit): planned S1, cold re-buy there at the death (slot 5)
            draw([1])
            assert sites[:2] == [(0, 0), (1, 5)], (seed, sites)
        else:
            assert sites[0] == (1, 0), (seed, sites)
        d2 = draw([0, 1])
        assert 6 not in starts and (d2, 7) in sites, (seed, d0, d2, sites)


def test_a4_marking_policy_smoke():
    """A4 with site_rule='marking' under I2 on ms2_multi_small (6 h) runs the marking path (group modes
    'marking', phases and draws); under I1 with require_I2 it runs as A3 ('off (I1)')."""
    cfg = load_json(CONFIGS / "ms2_multi_small.json")
    cfg["time"]["horizon_min"] = 360
    inst = build_instance(cfg)
    res = simulate(inst, A4(site_rule="marking"), LenderModel(information="I2"), policy_seed=0)
    assert res.invariant_failures == []
    mk = res.metrics["policy"]["marking"]
    n_mark = mk["group_modes"].get("marking", 0)
    assert mk["rule"] == "marking" and n_mark > 0 and mk["phases"] >= n_mark and mk["draws"] > 0, mk
    r1 = simulate(inst, A4(site_rule="marking"), LenderModel(information="I1"), policy_seed=0)
    assert r1.metrics["policy"]["marking"] == "off (I1)"
