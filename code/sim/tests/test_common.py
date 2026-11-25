"""Tests of sublet/algos/common.py (design/sim_spec_ms2.md §2.3, §3.2; §17.2)."""
import numpy as np
import pytest

from fixtures import CONFIGS, core_case, toy_config, toy_instance

from sublet.algos import common as cm
from sublet.algos.common import LeaseBook, PolicyError
from sublet.engine import simulate
from sublet.instance import build_instance, from_core, public_view, to_core, units
from sublet.policies.base import Policy
from sublet.types import Buy, LeaseView, Release, ReplicaView, Schedule, SetAdmission, SlowObs


def test_spawn_keeps_main_stream():
    """§2.3: policy_streams(rng) returns rng itself as 'main' and rng.spawn(3) as order, marking, aux;
    default_rng(s).random(5) equals the draws of 'main' after the spawn."""
    for s in (0, 1, 7, 1000, 12345):
        want = np.random.default_rng(s).random(5)
        rng = np.random.default_rng(s)
        st = cm.policy_streams(rng)
        assert set(st) == {"main", "order", "marking", "aux"} and st["main"] is rng
        assert np.array_equal(rng.random(5), want)
        kids = np.random.default_rng(s).spawn(3)
        for name, kid in zip(("order", "marking", "aux"), kids):
            assert np.array_equal(st[name].random(4), kid.random(4)), name
        draws = [st[k].random(3) for k in ("order", "marking", "aux")]
        assert not np.array_equal(draws[0], draws[1]) and not np.array_equal(draws[1], draws[2])


def test_site_order():
    """§2.3 (M7): site_order is the identity on from_core instances ('auto' -> 'index'), the seeded
    permutation rng_order.permutation(m) when layer sites exist, and the identity with mode 'index'."""
    inst, _ = from_core(*core_case(3, 0.2))
    v = public_view(inst, "I1")
    assert np.array_equal(cm.site_order(v, np.random.default_rng(1)), np.arange(inst.m))
    assert np.array_equal(cm.site_order(v, np.random.default_rng(1), "random"),
                          np.random.default_rng(1).permutation(inst.m))
    ml = build_instance(CONFIGS / "ms2_multi_small.json")
    vl = public_view(ml, "I1")
    assert any(s.kind == "layer" for s in vl.sites)
    for seed in (0, 3, 9):
        p = cm.site_order(vl, np.random.default_rng(seed))
        assert p.dtype == np.int64 and np.array_equal(p, np.random.default_rng(seed).permutation(ml.m))
        assert sorted(p.tolist()) == list(range(ml.m))
        assert np.array_equal(cm.site_order(vl, np.random.default_rng(seed), "index"), np.arange(ml.m))
    perms = {tuple(cm.site_order(vl, np.random.default_rng(s)).tolist()) for s in range(6)}
    assert len(perms) > 1
    with pytest.raises(PolicyError):
        cm.site_order(vl, np.random.default_rng(0), "cheapest")


def test_unit_and_column_costs():
    """toy (u = 4, λ > 0): unit_costs equal to_core's q and delta per unit; column_cost by hand for
    s5_tau5_H2 (L = 1 slot, P = 7 min) and for the protected window of §5.2 (the largest rule-T12 window,
    4 slots here, or `protected_window`); a contract with tau_slots >= T_s keeps rule T12 (from_core's
    (T, 0) gets L = T) and is treated as protected (M47)."""
    inst = toy_instance()
    assert inst.units_per_replica == 4 and np.all(inst.lam_s > 0)
    v = public_view(inst, "I1")
    sched = Schedule("trace", tuple(np.zeros(0, np.int64) for _ in inst.sites))
    ex = to_core(inst, sched, not_offered="big_m")
    q_req, d_req = cm.unit_costs(v)
    ut = units(inst)
    assert q_req.shape == (inst.n,) and d_req.shape == (inst.n, inst.m)
    assert np.all(np.abs(q_req[ut.client] - ex.core.q) <= 1e-12 * ex.core.q)
    assert np.array_equal(np.isinf(d_req[ut.client]), np.isinf(ex.core.delta))
    fin = np.isfinite(ex.core.delta)
    assert np.all(np.abs(d_req[ut.client][fin] - ex.core.delta[fin]) <= 1e-12)
    assert np.isclose(q_req[0], 7.15 * 5 / (60 * 4), rtol=1e-12)
    assert np.array_equal(cm.lam_ms(v), inst.lam_ms())

    i2 = build_instance(toy_config({"contracts.0.H_min": 2}))
    v2 = public_view(i2, "I1")
    c0 = v2.contracts[0]
    assert (c0.tau_slots, c0.H_min, c0.prepaid_min) == (1, 2, 7)
    L0 = cm.pd_window_slots(v2, 0, None)
    assert L0 == 1
    bt = 0.0 + 300.0 / 3600 * (1 * 2.85 + 1.0 * 1 * 7.15)          # beta~ at L0 (λ = 300 s, a = 2.85)
    assert abs(v2.beta_tilde_usd[0, 0, 0] - bt) <= 1e-12
    assert abs(cm.column_cost(v2, 0, 0, 0, L0) - (bt + 1 * 2.85 * 7 / 60.0)) <= 1e-12
    assert abs(cm.column_cost(v2, 0, 0, 0, 3) - (bt + 1 * 2.85 * 15 / 60.0)) <= 1e-12   # window past the term
    assert cm.pd_window_slots(v2, 1, None) == 2 + 10 // 5
    kp = 2
    assert v2.contracts[kp].protected and cm.treated_as_protected(v2, kp)
    assert not cm.treated_as_protected(v2, 0) and not cm.treated_as_protected(v2, 1)
    Lp = cm.pd_window_slots(v2, kp, None)
    assert Lp == 4
    btp = 600.0 / 3600 * (5.97 + 7.15)
    assert abs(cm.column_cost(v2, 2, 0, kp, Lp) - (btp + 5.97 * max(5, 4 * 5) / 60.0)) <= 1e-12
    assert cm.pd_window_slots(v2, kp, 7) == 7
    assert abs(cm.column_cost(v2, 2, 0, kp, 7) - (btp + 5.97 * 35 / 60.0)) <= 1e-12
    assert cm.column_cost(v2, 0, 0, kp, 4) == float("inf")          # not offered at L0
    for bad in (0, -1, 1.5, True):
        with pytest.raises(PolicyError):
            cm.pd_window_slots(v2, kp, bad)
    # from_core: the core's (T, 0) contract has tau_slots = T: rule T12 gives L = T, M47 flags it
    import check_c4_lower
    I = check_c4_lower.single(48, [(1, 1), (48, 0)], 6.0, [1.0, 1.3])
    fi, _ = from_core(I, [np.zeros(0, np.int64)])
    vf = public_view(fi, "I1")
    assert cm.pd_window_slots(vf, 0, None) == 2 and cm.pd_window_slots(vf, 1, None) == 48
    assert cm.treated_as_protected(vf, 1) and not cm.treated_as_protected(vf, 0)
    assert abs(cm.column_cost(vf, 0, 0, 1, 48) - I.C(0, 0, 1)) <= 1e-12 * I.C(0, 0, 1)
    assert abs(cm.column_cost(vf, 0, 0, 0, 2) - I.C(0, 0, 0)) <= 1e-12 * I.C(0, 0, 0)


class _BookDriver(Policy):
    """Drives a LeaseBook from a script {t: callable(book, obs, view, log)} and logs begin's pairs."""
    name = "book_driver"

    def __init__(self, script):
        self.script = script

    def reset(self, view, rng):
        super().reset(view, rng)
        self.book = LeaseBook()
        self.log: dict = {"begin": {}, "acts": {}, "can": {}, "cause": {}, "ids": {}}

    def act(self, obs):
        self.log["begin"][obs.t] = self.book.begin(obs)
        for key, r in self.log["begin"][obs.t]:
            if r.ok:
                self.log["ids"][key] = (r.lease_id, r.replica_ids)
        f = self.script.get(obs.t)
        if f is not None:
            f(self.book, obs, self.view, self.log)
        acts = self.book.assemble(obs, self.view)
        self.log["acts"][obs.t] = list(acts)
        return acts


def test_leasebook():
    """§2.3, §3.2: assemble orders Releases, then Drains and SetAdmissions, then Buys in staging order; the
    next begin maps the kept Buys to their results by final index; a Release staged after two Buys at the
    same site frees capacity for them (the engine sees the Releases first, MS1 test_refuse_and_capacity);
    a Buy that fails the pre-check is dropped and comes back from begin as refused with reason 'precheck';
    can_buy answers the pre-check for the actions staged so far; cause() reports end causes."""
    inst = toy_instance()               # L0 and L1: 4 GPUs each, P unlimited; g = 1

    def t0(book, obs, view, log):
        book.buy("a", Buy(0, 0, 0, 3, tag="a"))
        book.buy("b", Buy(0, 0, 0, 2, tag="b"))          # 3 + 2 > 4: dropped
        book.buy("p", Buy(2, 2, 0, 1, tag="p"))

    def t1(book, obs, view, log):
        la = log["ids"]["a"][0]
        log["can"][1] = [book.can_buy(obs, view, 0, 1), book.can_buy(obs, view, 0, 2)]
        book.buy("c", Buy(0, 1, 0, 2, tag="c"))          # 3 + 2 > 4: fits only because a is released
        log["can"][1].append(book.can_buy(obs, view, 0, 1))
        book.buy("d", Buy(0, 0, 0, 2, tag="d"))          # likewise; with a released 2 + 2 = 4
        book.release(la)                                 # staged after the two Buys
        log["can"][1].append(book.can_buy(obs, view, 0, 1))

    def t2(book, obs, view, log):
        rid_c = log["ids"]["c"][1][0]
        ld = log["ids"]["d"][0]
        book.buy("e", Buy(1, 0, 0, 1, tag="e"))
        book.other(SetAdmission(rid_c, 0.5))
        book.release(ld)
        book.release(ld)
        book.release(10 ** 6)                            # not an own alive lease: dropped
        book.buy("f", Buy(1, 0, 0, 4, tag="f"))          # 1 + 4 > 4: dropped
        book.buy("g", Buy(1, 0, 0, 3, tag="g"))          # 1 + 3 = 4 fits after the drop of f

    pol = _BookDriver({0: t0, 1: t1, 2: t2})
    res = simulate(inst, pol)
    assert res.invariant_failures == []
    log = pol.log
    A = log["acts"]
    assert [a.tag for a in A[0]] == ["a", "p"]
    b1 = log["begin"][1]
    assert [k for k, _ in b1] == ["a", "p", "b"]
    (ka, ra), (kp, rp), (kb, rb) = b1
    assert ra.ok and ra.index == 0 and ra.action == A[0][0] and rp.ok and rp.index == 1
    assert (rb.ok, rb.reason, rb.index, rb.lease_id, rb.action.tag) == (False, "precheck", -1, None, "b")
    assert log["can"][1] == [True, False, True, False]
    la = log["ids"]["a"][0]
    assert isinstance(A[1][0], Release) and A[1][0].lease_id == la
    assert [a.tag for a in A[1][1:]] == ["c", "d"]
    b2 = log["begin"][2]
    assert [k for k, _ in b2] == ["c", "d"] and all(r.ok for _, r in b2)
    assert [r.index for _, r in b2] == [1, 2]
    ld = log["ids"]["d"][0]
    rid_c = log["ids"]["c"][1][0]
    assert A[2][0] == Release(ld) and A[2][1] == SetAdmission(rid_c, 0.5)
    assert [type(a).__name__ for a in A[2]] == ["Release", "SetAdmission", "Buy", "Buy"]
    assert [a.tag for a in A[2][2:]] == ["e", "g"]
    b3 = log["begin"][3]
    assert [k for k, _ in b3] == ["e", "g", "f"]
    assert [r.index for _, r in b3] == [2, 3, -1] and [r.ok for _, r in b3] == [True, True, False]
    assert b3[2][1].reason == "precheck"
    assert all(len(log["begin"][t]) == 0 for t in range(4, inst.grid.T_slow))
    assert pol.book.cause(la) == "release" and pol.book.cause(ld) == "release"
    assert pol.book.cause(log["ids"]["c"][0]) == "reclaim"      # 'long' at L0: announced at 6, dead at minute 40
    assert pol.book.cause(log["ids"]["p"][0]) is None            # alive until the horizon end: never reported
    assert pol.book.cause(10 ** 6) is None
    assert sum(res.metrics["refused"].values()) == 0             # the engine refused nothing
    _attributed_load_hand()


def _attributed_load_hand():
    """§3.2 attributed_load by hand: served_prev[j, l] x (admissions of the lease's warm replicas) /
    (admissions of all own warm replicas of j at l); 0 for a loading replica, a dead lease or None."""
    inst = toy_instance()
    v = public_view(inst, "I1")
    lv = {0: LeaseView(0, 0, 0, 1, 0, 0, 7, None, None, (0,)),
          1: LeaseView(1, 0, 0, 1, 0, 0, 7, None, None, (1,)),
          2: LeaseView(2, 0, 0, 1, 1, 5, 12, None, None, (2,)),
          3: LeaseView(3, 1, 0, 1, 0, 0, 7, None, None, (3,))}
    rv = {0: ReplicaView(0, 0, 0, "warm", 0, 1, 1.0, None), 1: ReplicaView(1, 1, 0, "warm", 0, 1, 0.5, None),
          2: ReplicaView(2, 2, 0, "loading", 5, 3, 1.0, None), 3: ReplicaView(3, 3, 0, "warm", 0, 1, 0.0, None)}
    served = np.zeros((1, inst.m))
    served[0, 0], served[0, 1] = 0.9, 0.4
    obs = SlowObs(1, 5, np.zeros((1, 1)), lv, rv, [], [], [], None, served, np.zeros(1), 0.0)
    assert abs(cm.attributed_load(obs, v, lv[0]) - 0.6) <= 1e-15
    assert abs(cm.attributed_load(obs, v, lv[1]) - 0.3) <= 1e-15
    assert cm.attributed_load(obs, v, lv[2]) == 0.0
    assert cm.attributed_load(obs, v, lv[3]) == 0.0          # admission sum 0 at site 1
    assert cm.attributed_load(obs, v, None) == 0.0
    dead = LeaseView(9, 0, 0, 1, 0, 0, 7, None, None, (0,))
    assert cm.attributed_load(obs, v, dead) == 0.0
    al = cm.attributed_loads(obs, v)
    assert set(al) == {0, 1, 2, 3} and abs(al[0] - 0.6) <= 1e-15


def test_leasebook_drops_actions_on_released_lease():
    """§3.2: LeaseBook.assemble drops a Drain or SetAdmission of a replica whose lease is released in the same
    slot (the engine would raise ActionError) and counts it in stats['dead_other']; on another lease it is kept."""
    from sublet.types import Drain
    inst = toy_instance()
    v = public_view(inst, "I1")
    leases = [LeaseView(1, 0, 0, 1, 0, 0, 5, None, None, (10,)), LeaseView(2, 1, 0, 1, 0, 0, 5, None, None, (20,))]
    reps = [ReplicaView(10, 1, 0, "warm", 0, 1, 1.0, None), ReplicaView(20, 2, 0, "warm", 0, 1, 1.0, None)]
    obs = SlowObs(t=3, minute=15, demand=np.ones((inst.n, inst.grid.phi)), leases={L.id: L for L in leases},
                  replicas={r.id: r for r in reps}, notices=[], ended=[], results=[], site_announced=None,
                  served_prev=np.zeros((inst.J, inst.m)), fallback_prev=np.zeros(inst.n), cost_so_far=0.0)
    book = LeaseBook()
    book.begin(obs)
    book.release(1)
    book.other(SetAdmission(10, 0.5))
    book.other(Drain(10, 20))
    book.other(SetAdmission(20, 0.5))
    assert book.assemble(obs, v) == [Release(1), SetAdmission(20, 0.5)]
    assert book.stats["dead_other"] == 2
