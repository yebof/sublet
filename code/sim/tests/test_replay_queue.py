"""Tests of the request-level replay with a queue sublet/replay/queue.py (X7; design/ms8/plan.md D1,
design/ms8/scout_x7_queue.md §2 tests 1-6).

Quick (no raw data):
- QCopier's sizes equal scale.Copier's bit for bit (fractional, integer and sub-unit Gamma), with arrival times in
  order inside their second and input sizes that give back the weighted sizes;
- at W = 0 QueueReplay equals loop.replay exactly (costs, counts, tokens, stranding) on random placements with
  capacity drops, a site without an arc and a delta tie, and on the all-fallback (zero) placement;
- a pure-Python per-copy FIFO with reneging gives the same counts, tokens, costs, waits and renege counts on small
  streams for W in {1, 2.5, 10};
- conservation: own + leased + immediate fallback + reneged + queued at the end = every copy, per class too, tokens to
  1e-9;
- the TTFT histograms on a hand example (served, served after waiting, reneged, end of horizon), sparse/dense;
- window classes on a toy run (reclaim from the notice to death plus the load time, load, overflow, base; priority);
- the lockstep runner feeds several states the same copies.
- review probes: a per-copy reference with per-class bookkeeping (own and leased split, the three TTFT histograms per
  class, fallback by demand) for W in {0, 1, 2.5, 10}; hold_max_s equal to loop.replay's with a long fallback copy;
  the load window ends with a replica that dies before it is warm.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest

from sublet import replay as rp
from sublet.replay import queue as rq
from sublet.replay.loop import Placement, ServiceModel
from sublet.replay.loop import token_costs as loop_token_costs


def _stream(n_seconds: int, rate: float, seed: int):
    rng = np.random.default_rng(seed)
    n = rng.poisson(rate * n_seconds)
    t = np.sort(rng.random(n) * n_seconds)
    inp = rng.integers(1, 3000, n).astype(np.float64)
    out = rng.integers(1, 400, n).astype(np.float64)
    return t, inp, out


def _svc(tpot=0.035, n_seq=128, w_in=0.3) -> ServiceModel:
    return ServiceModel(tier="M", a5_tier="test", n_seq=n_seq, tpot_s=tpot, w_in=w_in,
                        kappa_wtok_per_min=60.0 * n_seq / tpot)


def _plan(seed: int, T: int = 10) -> Placement:
    rng = np.random.default_rng(10 + seed)
    W = rng.integers(0, 4, size=(4, T)).astype(np.float64) / 8.0
    return Placement(W=W, delta=np.array([0.5, 0.1, 0.0, 0.1]), ok=np.array([True, True, False, True]), q=7.15,
                     mu_fb=0.2, fast_min=1, site_ids=("a", "b", "c", "d"))


def _run_q(t, inp, out, plan, svc, own, n_sec, W, gamma=2.3, seed=4, P=12000.0, classes=None):
    idx = rp.StreamIndex.build(t, n_sec)
    ring = rp.ring_size(float((svc.w_in * inp + out).max()), svc)
    T = plan.T_fast
    cls = np.full(T, rq.BASE, np.int8) if classes is None else classes
    st = rq.QueueReplay(plan, svc, own, ring, W, cls, np.ones(T), P, n_sec)
    cp = rq.QCopier(t, inp, out, idx, gamma, svc.w_in, seed=seed)
    for s in range(n_sec):
        st.step(s, *cp.second3(s))
    return st.finish(cp.finish())


# ---------------------------------------------------------------- 1. QCopier
@pytest.mark.parametrize("gamma", [2.6, 3.0, 0.7])
def test_qcopier_equals_copier_bit_for_bit(gamma):
    t, inp, out = _stream(180, 4.0, 1)
    idx = rp.StreamIndex.build(t, 180)
    a = rp.Copier(t, inp, out, idx, gamma, 0.3, seed=5)
    b = rq.QCopier(t, inp, out, idx, gamma, 0.3, seed=5)
    for s in range(180):
        la = a.second(s)
        ar, lb, ib = b.second3(s)
        assert la.dtype == lb.dtype and np.array_equal(la, lb)           # bit for bit, same order
        assert len(ar) == len(lb) == len(ib)
        assert np.all((ar >= s) & (ar < s + 1)) and np.all(np.diff(ar) >= 0)
        np.testing.assert_array_equal(0.3 * ib + (lb - 0.3 * ib), lb)
        assert np.all(np.isin(ib, inp))
    sa, sb = a.finish(), b.finish()
    assert sa == sb
    c = rq.QCopier(t, inp, out, idx, gamma, 0.3, seed=5)
    d = rp.Copier(t, inp, out, idx, gamma, 0.3, seed=5)
    assert all(np.array_equal(c.second(s), d.second(s)) for s in range(180))
    with pytest.raises(ValueError):
        c.second3(3)


def test_qcopier_input_sizes_match_weighted_sizes():
    """The input size returned with each copy is the one its weighted size was built from."""
    t, inp, out = _stream(120, 3.0, 2)
    idx = rp.StreamIndex.build(t, 120)
    b = rq.QCopier(t, inp, out, idx, 2.5, 0.25, seed=1)
    pairs = set(zip((0.25 * inp + out).tolist(), inp.tolist()))
    for s in range(120):
        _, lw, ip = b.second3(s)
        assert all((l, i) in pairs for l, i in zip(lw.tolist(), ip.tolist()))


# ---------------------------------------------------------------- 2. W = 0 is loop.replay
@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_w0_equals_loop_replay_exactly(seed):
    n_sec = 600
    t, inp, out = _stream(n_sec, 1.5, seed)
    idx = rp.StreamIndex.build(t, n_sec)
    plan = _plan(seed)
    svc = _svc(tpot=0.02, n_seq=16, w_in=0.3)
    ring = rp.ring_size(float((0.3 * inp + out).max()), svc)
    ref = rp.replay(rp.Copier(t, inp, out, idx, 2.3, 0.3, seed=4), plan, svc, 12, n_sec, ring)
    got = _run_q(t, inp, out, plan, svc, 12, n_sec, 0.0)
    assert got["costs"] == ref["costs"]                                  # exact, not approximate
    for k in ("copies", "own", "leased", "leased_by_site", "fallback", "stranded", "strand_events",
              "in_flight_at_end"):
        assert got["counts"][k] == ref["counts"][k], k
    for k in ("stream", "own", "leased", "leased_by_site", "fallback", "stranded_remainder"):
        assert got["tokens"][k] == ref["tokens"][k], k
    assert got["counts"]["fallback_reneged"] == got["counts"]["fallback_end"] == got["counts"]["queued"] == 0
    assert ref["counts"]["stranded"] > 0 and ref["counts"]["fallback"] > 0
    assert got["per_hour"] == ref["per_hour"]
    assert got["hold_max_s"] == ref["hold_max_s"]                     # over every arrival, fallback copies too
    assert got["conservation"]["pass"]
    # the all-fallback bill: own capacity, then fallback
    zp = rq.zero_placement(plan)
    ref0 = rp.replay(rp.Copier(t, inp, out, idx, 2.3, 0.3, seed=4), zp, svc, 12, n_sec, ring)
    got0 = _run_q(t, inp, out, zp, svc, 12, n_sec, 0.0)
    assert got0["costs"] == ref0["costs"] and got0["costs"]["routing"] == 0.0 and got0["counts"]["leased"] == 0
    assert got0["hold_max_s"] == ref0["hold_max_s"]


# ---------------------------------------------------------------- 3. per-copy FIFO with reneging
def ref_queue(per_second, plan: Placement, svc: ServiceModel, own_slots: int, n_seconds: int, W: float, P: float):
    """Per-copy reference: one FIFO queue, reneging of copies that arrived before s - W, the queue's head served
    first, then the arrivals (own capacity, then the sites in delta order); stranding of the latest placed copies."""
    order = list(plan.order)
    dsec = 60 * plan.fast_min
    own, fl = [], {l: [] for l in order}
    routed = {l: 0.0 for l in order}
    n_site = {l: 0 for l in order}
    acc = dict(own_tok=0.0, fbi=0.0, fbr=0.0, fbe=0.0, rem=0.0, n_own=0, n_fbi=0, n_fbr=0, n_fbe=0, n_str=0,
               n_queued=0)
    waits, ttft_served = [], []
    queue, seq, caps = [], 0, {}
    for s in range(n_seconds):
        own = [c for c in own if c > s]
        for l in order:
            fl[l] = [x for x in fl[l] if x[1] > s]
        if s % dsec == 0:
            f = s // dsec
            for l in order:
                cap = int(math.floor(svc.n_seq * plan.W[l, f] + 1e-9))
                while len(fl[l]) > cap:
                    x = max(fl[l], key=lambda y: y[0])
                    fl[l].remove(x)
                    r = x[2] * (x[1] - s) / x[3]
                    acc["rem"] += r
                    routed[l] -= r
                    acc["n_str"] += 1
            caps = {l: int(math.floor(svc.n_seq * plan.W[l, f] + 1e-9)) for l in order}
        while queue and queue[0][0] < s - W:
            a, size, ip = queue.pop(0)
            acc["fbr"] += size
            acc["n_fbr"] += 1
        cand = [(c, True) for c in queue] + [(c, False) for c in per_second[s]]
        newq = []
        for (a, size, ip), fromq in cand:
            h = max(1, int(round(size * svc.tpot_s)))
            placed = False
            if len(own) < own_slots:
                own.append(s + h)
                acc["own_tok"] += size
                acc["n_own"] += 1
                placed = True
            else:
                for l in order:
                    if len(fl[l]) < caps[l]:
                        seq += 1
                        fl[l].append((seq, s + h, size, h))
                        routed[l] += size
                        n_site[l] += 1
                        placed = True
                        break
            if placed:
                w = (s - a) if fromq else 0.0
                if fromq:
                    waits.append(w)
                ttft_served.append(w + ip / P)
            elif fromq or W > 0:
                newq.append((a, size, ip))
                if not fromq:
                    acc["n_queued"] += 1
            else:
                acc["fbi"] += size
                acc["n_fbi"] += 1
        queue = newq
    for a, size, ip in queue:
        acc["fbe"] += size
        acc["n_fbe"] += 1
    return {"routed": routed, "n_site": n_site, "waits": waits, "ttft_served": ttft_served, **acc}


@pytest.mark.parametrize("seed,W", [(0, 1.0), (1, 2.5), (2, 10.0), (3, 2.5)])
def test_queue_against_per_copy_reference(seed, W):
    n_sec = 400
    t, inp, out = _stream(n_sec, 1.6, seed)
    idx = rp.StreamIndex.build(t, n_sec)
    plan = _plan(seed, T=7)
    svc = _svc(tpot=0.02, n_seq=16, w_in=0.3)
    P = 12000.0
    cp = rq.QCopier(t, inp, out, idx, 2.3, 0.3, seed=4)
    per = [list(zip(*[x.tolist() for x in cp.second3(s)])) for s in range(n_sec)]
    ref = ref_queue(per, plan, svc, 10, n_sec, W, P)
    got = _run_q(t, inp, out, plan, svc, 10, n_sec, W, P=P)
    c, tk = got["counts"], got["tokens"]
    assert c["own"] == ref["n_own"] and c["stranded"] == ref["n_str"]
    assert c["fallback_immediate"] == 0 and ref["n_fbi"] == 0
    assert c["fallback_reneged"] == ref["n_fbr"] and c["fallback_end"] == ref["n_fbe"]
    assert c["queued"] == ref["n_queued"] and c["served_after_wait"] == len(ref["waits"])
    assert c["leased_by_site"] == {plan.site_ids[l]: ref["n_site"][l] for l in plan.order}
    assert c["fallback_reneged"] > 0 and c["served_after_wait"] > 0 and c["stranded"] > 0
    assert tk["fallback_reneged"] == pytest.approx(ref["fbr"], rel=1e-12)
    assert tk["stranded_remainder"] == pytest.approx(ref["rem"], rel=1e-9)
    for l in plan.order:
        assert tk["leased_by_site"][plan.site_ids[l]] == pytest.approx(ref["routed"][l], rel=1e-9, abs=1e-6)
    wsum = sum(x["wait_sum_s"] for x in got["by_class"].values())
    assert wsum == pytest.approx(sum(ref["waits"]), rel=1e-9)
    assert max(ref["waits"]) <= W + 1e-12
    h = rq.dense(got["by_class"]["base"]["hist"]["served"])
    np.testing.assert_array_equal(h, np.bincount(rq.bins(np.asarray(ref["ttft_served"])), minlength=rq.N_BINS))
    assert got["conservation"]["pass"]


# ---------------------------------------------------------------- 4. conservation
def test_conservation_and_classes():
    n_sec = 360
    t, inp, out = _stream(n_sec, 2.0, 7)
    plan = _plan(7, T=6)
    svc = _svc(tpot=0.02, n_seq=16, w_in=0.3)
    cls = np.array([rq.RECLAIM, rq.LOAD, rq.OVERFLOW, rq.BASE, rq.OVERFLOW, rq.RECLAIM], np.int8)
    for W in (0.0, 1.0, 2.5, 10.0):
        g = _run_q(t, inp, out, plan, svc, 8, n_sec, W, classes=cls)
        c, tk, cons = g["counts"], g["tokens"], g["conservation"]
        assert c["own"] + c["leased"] + c["fallback_immediate"] + c["fallback_reneged"] + c["fallback_end"] == \
            c["copies"]
        assert cons["pass"] and cons["counts_exact"] and cons["classes_exact"] and cons["copier_match"]
        assert abs(tk["own"] + tk["leased"] + tk["fallback"] + tk["stranded_remainder"] - tk["stream"]) <= \
            1e-9 * tk["stream"]
        assert sum(x["copies"] for x in g["by_class"].values()) == c["copies"]
        assert sum(x["stranded"] for x in g["by_class"].values()) == c["stranded"]
        fbd = g["fallback_by_demand"]
        assert fbd["zero"]["usd"] + fbd["positive"]["usd"] == pytest.approx(g["costs"]["fallback"], rel=1e-12)
        for x in g["by_class"].values():
            n_h = sum(int(np.sum(rq.dense(h))) for h in x["hist"].values())
            assert n_h == x["copies"]                                    # every copy in exactly one histogram
        if W == 0:
            assert c["queued"] == 0
        else:
            assert c["fallback_immediate"] == 0 and c["queued"] >= c["served_after_wait"]


# ---------------------------------------------------------------- 5. TTFT on hand examples
class ArrCopier:
    """Copies given per second as (arrival, weighted size, input tokens), with QCopier's counters."""

    def __init__(self, per: dict):
        self.per, self.n_emitted, self.tokens_emitted = per, 0, 0.0

    def second3(self, s):
        rows = self.per.get(s, [])
        a = np.array([r[0] for r in rows], dtype=np.float64)
        lw = np.array([r[1] for r in rows], dtype=np.float64)
        ip = np.array([r[2] for r in rows], dtype=np.float64)
        self.n_emitted += len(lw)
        self.tokens_emitted += float(lw.sum())
        return a, lw, ip

    def finish(self):
        return {"n_emitted": self.n_emitted, "tokens_emitted": self.tokens_emitted, "copies_balance": 0}


def _hand(W, per, n_sec=8):
    svc = _svc(tpot=1.0, n_seq=1, w_in=0.5)
    plan = Placement(W=np.zeros((1, 1)), delta=np.array([0.0]), ok=np.array([False]), q=2.0, mu_fb=0.5, fast_min=1,
                     site_ids=("s0",))
    st = rq.QueueReplay(plan, svc, 1, 20, W, np.array([rq.OVERFLOW], np.int8), np.ones(1), 1000.0, n_sec)
    rq.run_lockstep(ArrCopier(per), [st], n_sec, 1000.0)
    return st.finish()


def test_ttft_hand_examples():
    """One own slot (TPOT 1 s, n_seq 1), P = 1000 tokens/s. Second 0: A (0.25 s, size 3, inp 125) is served at once,
    TTFT 0.125 s, and holds the slot until second 3; B (0.5 s, size 1, inp 250) waits. With W = 2.5 B is served at
    second 3 after 2.5 s, TTFT 2.75 s; C (3.25 s, inp 125) then waits until second 4, TTFT 0.875 s. With W = 2 B
    reneges at second 3 (fallback after waiting, prefill 0.25 s) and C is served at once. At W = 0 B goes to fallback
    at once. With W = 10 and a horizon of 2 s B is still queued at the end."""
    per = {0: [(0.25, 3.0, 125.0), (0.5, 1.0, 250.0)], 3: [(3.25, 1.0, 125.0)]}
    g = _hand(2.5, per)
    sv = rq.dense(g["by_class"]["overflow"]["hist"]["served"])
    assert sv[12] == 1 and sv[275] == 1 and sv[87] == 1 and sv.sum() == 3
    assert g["counts"]["served_after_wait"] == 2 and g["counts"]["fallback"] == 0 and g["counts"]["queue_max"] == 1
    assert g["by_class"]["overflow"]["wait_sum_s"] == pytest.approx(2.5 + 0.75)
    wh = rq.dense(g["wait_hist"])
    assert wh[250] == 1 and wh[75] == 1
    g = _hand(2.0, per)
    sv = rq.dense(g["by_class"]["overflow"]["hist"]["served"])
    fw = rq.dense(g["by_class"]["overflow"]["hist"]["fallback_waited"])
    assert sv[12] == 2 and sv.sum() == 2 and fw[25] == 1 and fw.sum() == 1
    assert g["counts"]["fallback_reneged"] == 1 and g["tokens"]["fallback_reneged"] == 1.0
    assert g["costs"]["fallback"] == pytest.approx(2.0 * 1.0 / (60 * 60.0), rel=1e-12)
    g = _hand(0.0, per)
    fi = rq.dense(g["by_class"]["overflow"]["hist"]["fallback"])
    assert fi[25] == 1 and fi.sum() == 1 and g["counts"]["fallback_immediate"] == 1
    g = _hand(10.0, per, n_sec=2)
    assert g["counts"]["fallback_end"] == 1 and g["counts"]["fallback_reneged"] == 0
    assert rq.dense(g["by_class"]["overflow"]["hist"]["fallback_waited"])[25] == 1


def test_sparse_dense_and_bins():
    h = np.zeros(rq.N_BINS, np.int64)
    h[[3, 7, 2000]] = [1, 2, 5]
    sp = rq.sparse(h)
    assert sp["lo"] == 3 and len(sp["counts"]) == 1998 and np.array_equal(rq.dense(sp), h)
    assert rq.sparse(np.zeros(5, np.int64)) is None and rq.dense(None).sum() == 0
    np.testing.assert_array_equal(rq.bins(np.array([0.0, 0.0099, 0.01, 0.5, 19.99, 20.0, 1e6])),
                                  [0, 0, 1, 50, 1999, 2000, 2000])


# ---------------------------------------------------------------- 6. window classes
def test_window_classes_on_a_toy_run():
    """Fast slots of 1 min, slow slots of 5 min, 30 fast slots. Demand positive in 2-24. A replica on lease 7 loads
    from minute 3 to warm at 6; lease 7 gets a notice in slow slot 3 (minute 15) and dies at minute 18, with a load
    time of 120 s at its site, so reclaim covers 15-19. A lease without a replica of the LLM (lease 9) and an
    unannounced lease do not count."""
    T = 30
    d = np.zeros(T)
    d[2:25] = 1.0
    inst = SimpleNamespace(grid=SimpleNamespace(fast_min=1, slow_min=5, T_fast=T),
                           clients=SimpleNamespace(demand=[d]), lam_s=np.array([[60.0, 120.0]]))
    reps = [SimpleNamespace(id=1, lease_id=7, llm=0, load_start_min=3, warm_fast=6, end_fast=18),
            SimpleNamespace(id=2, lease_id=8, llm=0, load_start_min=25, warm_fast=27, end_fast=30),
            SimpleNamespace(id=3, lease_id=9, llm=1, load_start_min=0, warm_fast=1, end_fast=30)]
    leases = [SimpleNamespace(id=7, site=1, announce_slot=3, death_min=18),
              SimpleNamespace(id=8, site=0, announce_slot=None, death_min=None),
              SimpleNamespace(id=9, site=0, announce_slot=1, death_min=8)]
    res = SimpleNamespace(replicas=reps, leases=leases)
    cls = rq.window_classes(res, inst)
    want = np.full(T, rq.BASE)
    want[2:25] = rq.OVERFLOW
    want[3:6] = rq.LOAD
    want[25:27] = rq.LOAD
    want[15:20] = rq.RECLAIM
    np.testing.assert_array_equal(cls, want)
    assert rq.class_counts(cls) == {"reclaim": 5, "load": 5, "overflow": 15, "base": 5}
    np.testing.assert_array_equal(rq.demand_classes(d), np.where(d > 0, rq.OVERFLOW, rq.BASE))
    plan = Placement(W=np.vstack([np.full(T, 0.5), np.full(T, 0.7)]), delta=np.array([0.1, 0.2]),
                     ok=np.array([True, False]), q=1.0, mu_fb=0.1, fast_min=1, site_ids=("x", "y"))
    hr = rq.headroom(plan, d)
    assert hr["share_all"] == pytest.approx(7 / 30) and hr["share_overflow"] == 0.0


def test_window_classes_on_an_engine_run():
    """A toy engine run (A6, two regions, 1-min fast slots): the classes are defined for every fast slot, the load
    windows cover each replica's load and overflow holds exactly where the demand is positive outside reclaim and
    load windows."""
    from sublet.drivers import run as drun
    from sublet.engine import simulate
    ov = {"regions.list": ["r0", "r1"], "regions.adjacency": [["r0", "r1"]], "lenders.0.region": "r1",
          "borrowers.clients.0.slo_class": "relaxed", "time.fast_slot_min": 1,
          "borrowers.clients.0.demand": {"kind": "onoff", "on_mean_min": 20, "off_mean_min": 10, "level": 2.5,
                                         "seed": 3}}
    spec = drun.load_run_spec({"schema_version": 1, "name": "t", "instance": "toy.json", "overrides": ov,
                               "engine": {"record_routing": True, "check_invariants": True},
                               "policy": {"id": "A6", "params": {}}})
    inst, model, ecfg = drun.build(spec, 7)
    res = simulate(inst, drun.make_policy(spec, inst), model, ecfg)
    cls = rq.window_classes(res, inst)
    d = np.asarray(inst.clients.demand[0])
    assert cls.shape == (inst.grid.T_fast,) and set(np.unique(cls)) <= {0, 1, 2, 3}
    for r in res.replicas:
        f0, f1 = r.load_start_min // inst.grid.fast_min, min(r.warm_fast, inst.grid.T_fast)
        assert np.all(np.isin(cls[f0:f1], (rq.RECLAIM, rq.LOAD)))
    other = (cls != rq.RECLAIM) & (cls != rq.LOAD)
    assert np.array_equal(cls[other] == rq.OVERFLOW, d[other] > 0)
    assert np.any(cls == rq.LOAD)


# ---------------------------------------------------------------- 7. lockstep
def test_lockstep_feeds_every_state_the_same_copies():
    n_sec = 240
    t, inp, out = _stream(n_sec, 2.0, 9)
    idx = rp.StreamIndex.build(t, n_sec)
    plan = _plan(9, T=4)
    svc = _svc(tpot=0.02, n_seq=16, w_in=0.3)
    ring = rp.ring_size(float((0.3 * inp + out).max()), svc)
    cls = np.full(4, rq.BASE, np.int8)
    sts = [rq.QueueReplay(p, svc, 10, ring, W, cls, np.ones(4), 12000.0, n_sec)
           for p in (plan, rq.zero_placement(plan)) for W in (0.0, 2.5)]
    r = rq.run_lockstep(rq.QCopier(t, inp, out, idx, 2.3, 0.3, seed=4), sts, n_sec, 12000.0)
    res = [s.finish(r["copier"]) for s in sts]
    assert len({x["counts"]["copies"] for x in res}) == 1 and all(x["conservation"]["pass"] for x in res)
    single = _run_q(t, inp, out, plan, svc, 10, n_sec, 2.5)
    assert single["costs"] == res[1]["costs"] and single["counts"] == res[1]["counts"]
    with pytest.raises(ValueError):
        rq.QueueReplay(plan, svc, 10, ring, -1.0, cls, np.ones(4), 1.0, n_sec)


# ---------------------------------------------------------------- review probes (X7 review, copied in by the fix)
# An independent per-copy reference with per-class bookkeeping: random classes per fast slot, demand with zero slots,
# arrivals exactly on whole seconds; every per-class counter (own and leased split included), the three TTFT
# histograms per class, the fallback by demand, the costs and the stranding.


def _stream_int(n_seconds, rate, seed):
    rng = np.random.default_rng(seed)
    n = rng.poisson(rate * n_seconds)
    t = np.sort(rng.random(n) * n_seconds)
    # include arrivals exactly on integer seconds
    k = max(1, n // 20)
    t[:k] = np.floor(t[:k])
    t = np.sort(t)
    inp = rng.integers(1, 3000, n).astype(np.float64)
    out = rng.integers(1, 400, n).astype(np.float64)
    return t, inp, out


def _svc16(tpot=0.02, n_seq=16, w_in=0.3):
    return ServiceModel(tier="M", a5_tier="t", n_seq=n_seq, tpot_s=tpot, w_in=w_in,
                        kappa_wtok_per_min=60.0 * n_seq / tpot)


def ref_classes(per, plan, svc, own_slots, n_sec, W, P, cls, dem):
    order = list(plan.order)
    dsec = 60 * plan.fast_min
    T = plan.T_fast
    own = []
    sites = {l: [] for l in order}
    caps = {l: 0 for l in order}
    routed = {l: 0.0 for l in order}
    n_site = {l: 0 for l in order}
    C = len(rq.CLASSES)
    z = lambda: [0] * C   # noqa
    zf = lambda: [0.0] * C   # noqa
    B = dict(arr=z(), own=z(), leased=z(), fbi=z(), fbr=z(), fbe=z(), queued=z(), waited=z(), strand=z(),
             t_arr=zf(), t_fbi=zf(), t_fbr=zf(), t_fbe=zf(), t_rem=zf(), wsum=zf())
    H = {(c, k): [] for c in range(C) for k in range(3)}
    fb_f = np.zeros(T)
    queue = []
    seq = 0
    own_tok = rem_tok = 0.0
    n_str = 0
    f = 0
    for s in range(n_sec):
        own = [x for x in own if x > s]
        for l in order:
            sites[l] = [x for x in sites[l] if x["comp"] > s]
        if s % dsec == 0:
            f = s // dsec
            for l in order:
                caps[l] = int(math.floor(svc.n_seq * plan.W[l, f] + 1e-9))
                while len(sites[l]) > caps[l]:
                    x = max(sites[l], key=lambda y: y["seq"])
                    sites[l].remove(x)
                    r = x["size"] * (x["comp"] - s) / x["h"]
                    rem_tok += r
                    routed[l] -= r
                    n_str += 1
                    B["strand"][cls[f]] += 1
                    B["t_rem"][cls[f]] += r
                    fb_f[f] += r
        c_now = int(cls[f])
        arrivals = [dict(a=a, size=lw, inp=ip, c=c_now) for a, lw, ip in per[s]]
        for x in arrivals:
            B["arr"][x["c"]] += 1
            B["t_arr"][x["c"]] += x["size"]
        while queue and queue[0]["a"] < s - W:
            x = queue.pop(0)
            B["fbr"][x["c"]] += 1
            B["t_fbr"][x["c"]] += x["size"]
            fb_f[f] += x["size"]
            H[(x["c"], 2)].append(x["inp"] / P)
        newq = []
        for x, fromq in [(y, True) for y in queue] + [(y, False) for y in arrivals]:
            h = max(1, int(np.rint(x["size"] * svc.tpot_s)))
            where = None
            if len(own) < own_slots:
                own.append(s + h)
                own_tok += x["size"]
                where = "own"
            else:
                for l in order:
                    if len(sites[l]) < caps[l]:
                        seq += 1
                        sites[l].append(dict(seq=seq, comp=s + h, size=x["size"], h=h))
                        routed[l] += x["size"]
                        n_site[l] += 1
                        where = "leased"
                        break
            if where is not None:
                B[where][x["c"]] += 1
                w = (s - x["a"]) if fromq else 0.0
                if fromq:
                    B["waited"][x["c"]] += 1
                    B["wsum"][x["c"]] += w
                H[(x["c"], 0)].append(w + x["inp"] / P)
            elif fromq:
                newq.append(x)
            elif W > 0:
                newq.append(x)
                B["queued"][x["c"]] += 1
            else:
                B["fbi"][x["c"]] += 1
                B["t_fbi"][x["c"]] += x["size"]
                fb_f[f] += x["size"]
                H[(x["c"], 1)].append(x["inp"] / P)
        queue = newq
    for x in queue:
        B["fbe"][x["c"]] += 1
        B["t_fbe"][x["c"]] += x["size"]
        fb_f[f] += x["size"]
        H[(x["c"], 2)].append(x["inp"] / P)
    rt = np.zeros(plan.m)
    for l in order:
        rt[l] = routed[l]
    fb_tok = sum(B["t_fbi"]) + sum(B["t_fbr"]) + sum(B["t_fbe"])
    costs = loop_token_costs(rt, fb_tok + rem_tok, n_str, plan, svc)
    pos = np.asarray(dem) > 0
    return dict(B=B, H=H, costs=costs, fb_f=fb_f, fbz=float(fb_f[~pos].sum()), fbp=float(fb_f[pos].sum()),
                n_site=n_site, n_str=n_str)


@pytest.mark.parametrize("seed,W,gamma", [(0, 1.0, 2.3), (1, 2.5, 3.0), (2, 10.0, 2.3), (3, 0.0, 2.3),
                                          (4, 2.5, 0.7), (5, 1.0, 4.4)])
def test_per_class_against_independent_reference(seed, W, gamma):
    n_sec, T = 540, 9
    t, inp, out = _stream_int(n_sec, 1.8, seed)
    rng = np.random.default_rng(100 + seed)
    Wp = rng.integers(0, 5, size=(3, T)).astype(np.float64) / 8.0
    plan = Placement(W=Wp, delta=np.array([0.3, 0.1, 0.3]), ok=np.array([True, True, True]), q=7.15, mu_fb=0.2,
                     fast_min=1, site_ids=("a", "b", "c"))
    svc = _svc16()
    P = 12000.0
    cls = rng.integers(0, 4, size=T).astype(np.int8)
    dem = np.where(rng.random(T) < 0.5, 0.0, 1.0)
    idx = rp.StreamIndex.build(t, n_sec)
    ring = rp.ring_size(float((0.3 * inp + out).max()), svc)
    cp = rq.QCopier(t, inp, out, idx, gamma, 0.3, seed=4)
    per = [list(zip(*[x.tolist() for x in cp.second3(s)])) for s in range(n_sec)]
    R = ref_classes(per, plan, svc, 9, n_sec, W, P, cls, dem)
    st = rq.QueueReplay(plan, svc, 9, ring, W, cls, dem, P, n_sec)
    cp2 = rq.QCopier(t, inp, out, idx, gamma, 0.3, seed=4)
    rq.run_lockstep(cp2, [st], n_sec, P)
    g = st.finish()
    B = R["B"]
    for i, cn in enumerate(rq.CLASSES):
        x = g["by_class"][cn]
        assert x["copies"] == B["arr"][i]
        assert x["own"] == B["own"][i], (cn, x["own"], B["own"][i])
        assert x["leased"] == B["leased"][i], cn
        assert x["fallback_immediate"] == B["fbi"][i]
        assert x["fallback_reneged"] == B["fbr"][i]
        assert x["fallback_end"] == B["fbe"][i]
        assert x["queued"] == B["queued"][i]
        assert x["served_after_wait"] == B["waited"][i]
        assert x["stranded"] == B["strand"][i]
        assert x["wait_sum_s"] == pytest.approx(B["wsum"][i], rel=1e-9, abs=1e-9)
        assert x["tokens_stranded_remainder"] == pytest.approx(B["t_rem"][i], rel=1e-9, abs=1e-9)
        for k, kn in enumerate(rq.KINDS):
            want = np.bincount(rq.bins(np.asarray(R["H"][(i, k)], dtype=float)), minlength=rq.N_BINS) \
                if R["H"][(i, k)] else np.zeros(rq.N_BINS, np.int64)
            np.testing.assert_array_equal(rq.dense(x["hist"][kn]), want, err_msg=f"{cn} {kn}")
    for k in ("routing", "fallback", "stranding"):
        assert g["costs"][k] == pytest.approx(R["costs"][k], rel=1e-9, abs=1e-12)
    assert g["fallback_by_demand"]["zero"]["tokens"] == pytest.approx(R["fbz"], rel=1e-9, abs=1e-9)
    assert g["fallback_by_demand"]["positive"]["tokens"] == pytest.approx(R["fbp"], rel=1e-9, abs=1e-9)
    assert g["counts"]["stranded"] == R["n_str"]
    assert g["conservation"]["pass"]


def test_hold_max_equals_loop_with_a_long_fallback_copy():
    """hold_max_s counts every arrival of a second, fallback copies included, as loop.replay (review finding 3)."""
    n_sec = 120
    t, inp, out = _stream_int(n_sec, 3.0, 11)
    out[-1] = 5000.0
    idx = rp.StreamIndex.build(t, n_sec)
    plan = Placement(W=np.zeros((1, 2)), delta=np.array([0.0]), ok=np.array([True]), q=2.0, mu_fb=0.5,
                     fast_min=1, site_ids=("s0",))
    svc = _svc16()
    ring = rp.ring_size(float((0.3 * inp + out).max()), svc)
    ref_ = rp.replay(rp.Copier(t, inp, out, idx, 2.0, 0.3, seed=1), plan, svc, 0, n_sec, ring)
    st = rq.QueueReplay(plan, svc, 0, ring, 0.0, np.full(2, rq.BASE, np.int8), np.ones(2), 1.0, n_sec)
    rq.run_lockstep(rq.QCopier(t, inp, out, idx, 2.0, 0.3, seed=1), [st], n_sec, 1.0)
    g = st.finish()
    assert g["costs"] == ref_["costs"]
    assert g["hold_max_s"] == ref_["hold_max_s"] > 1


def test_load_window_ends_with_a_replica_that_dies_before_warm():
    """A replica that ends (end_fast 4) before it is warm (warm_fast 12): the load window is slots 2-3 only
    (review finding 2)."""
    T = 20
    d = np.zeros(T)
    inst = SimpleNamespace(grid=SimpleNamespace(fast_min=1, slow_min=5, T_fast=T),
                           clients=SimpleNamespace(demand=[d]), lam_s=np.array([[60.0]]))
    reps = [SimpleNamespace(id=1, lease_id=7, llm=0, load_start_min=2, warm_fast=12, end_fast=4)]
    res = SimpleNamespace(replicas=reps, leases=[SimpleNamespace(id=7, site=0, announce_slot=None, death_min=None)])
    cls = rq.window_classes(res, inst)
    np.testing.assert_array_equal(np.flatnonzero(cls == rq.LOAD), [2, 3])
