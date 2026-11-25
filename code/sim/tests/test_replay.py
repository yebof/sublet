"""Tests of E8's request-level replay sublet/replay/ (design/sim_spec_ms4.md §7.4-§7.9, §10 row test_replay.py).

Quick: the copy generator against a per-request reference; the per-second loop against a per-copy reference on a
synthetic stream with capacity drops (conservation, own capacity first, least-delta site, fallback, stranding latest
arrivals first) and on a hand example; check E8-2's oracle, the fluid mode against the engine on toy instances with
capacity drops (one with routing costs); the request cache round trip; the replica plan against W on an engine run
with replaced and applied drains, and its failure on a wrong reconstruction; the replica-level loop with and without
prefix hits (hits, the longest cached prefix among free replicas, a partial last block, caches emptied at a replica's
death, equality with the site-level loop without hits, also under a drain and a death that strand copies).
needs_raw: the Mooncake reader keeps hash_ids, the Azure cache of the first hour. needs_a12: E8's instance per tier,
reduced and at full scale (service model, market scale), and E8-2 on a reduced and a full-scale week run.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest

from sublet import replay as rp
from sublet.replay.loop import Placement, ReplicaPlan, ServiceModel


# ---------------------------------------------------------------- helpers
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


class ListCopier:
    """A copy stream given per second (sizes in arrival order), with Copier's counters."""

    def __init__(self, sizes: dict):
        self.sizes, self.n_emitted, self.tokens_emitted = sizes, 0, 0.0

    def second(self, s):
        x = np.asarray(self.sizes.get(s, []), dtype=np.float64)
        self.n_emitted += len(x)
        self.tokens_emitted += float(x.sum())
        return x

    def finish(self):
        return {"n_emitted": self.n_emitted, "tokens_emitted": self.tokens_emitted, "n_generated": self.n_emitted,
                "n_beyond": 0, "tokens_beyond": 0.0, "copies_balance": 0}


def ref_copies(t, inp, out, gamma, w_in, seed, n_seconds):
    """Per-request reference of scale.Copier: the same draws in the same order, one request at a time."""
    rng = np.random.default_rng(seed)
    G, frac = int(math.floor(gamma)), gamma - math.floor(gamma)
    carry, res = [], []
    for s in range(n_seconds):
        idx = [i for i in range(len(t)) if s <= t[i] < s + 1]
        mi = [i for i in range(len(t)) if 60 * (s // 60) <= t[i] < 60 * (s // 60 + 1)]
        lo, hi = (mi[0], mi[-1] + 1) if mi else (0, 0)
        u = rng.random(len(idx)) if (frac > 0 and idx) else None
        k = [G + (1 if (u is not None and u[q] < frac) else 0) for q in range(len(idx))]
        batch, nxt = list(carry), []
        for q, i in enumerate(idx):
            if k[q] >= 1:
                batch.append((t[i], w_in * inp[i] + out[i]))
        nx = sum(max(x - 1, 0) for x in k)
        if nx:
            off, pick = rng.random(nx), rng.random(nx)
            p = 0
            for q, i in enumerate(idx):
                for _ in range(max(k[q] - 1, 0)):
                    a = t[i] + off[p]
                    j = lo + min(int(pick[p] * (hi - lo)), hi - lo - 1)
                    (batch if a < s + 1 else nxt).append((a, w_in * inp[j] + out[j]))
                    p += 1
        carry = nxt
        batch.sort(key=lambda x: x[0])
        res.append([x[1] for x in batch])
    return res, len(carry)


def ref_replay(per_second, plan: Placement, svc: ServiceModel, own_slots: int, n_seconds: int) -> dict:
    """Per-copy reference of loop.replay: lists of in-flight copies, a capacity drop strands the latest arrivals."""
    order = list(plan.order)
    dsec = 60 * plan.fast_min
    own, fl = [], {l: [] for l in order}
    routed = {l: 0.0 for l in order}
    n_site = {l: 0 for l in order}
    acc = dict(own_tok=0.0, fb=0.0, rem=0.0, n_own=0, n_fb=0, n_str=0)
    seq = 0
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
        for size in per_second[s]:
            h = max(1, int(round(size * svc.tpot_s)))
            seq += 1
            if len(own) < own_slots:
                own.append(s + h)
                acc["own_tok"] += size
                acc["n_own"] += 1
                continue
            for l in order:
                if len(fl[l]) < caps[l]:
                    fl[l].append((seq, s + h, size, h))
                    routed[l] += size
                    n_site[l] += 1
                    break
            else:
                acc["fb"] += size
                acc["n_fb"] += 1
    return {"routed": routed, "n_site": n_site, **acc}


def _toy_spec(pid: str, params=None):
    from sublet.drivers import run as drun
    ov = {"regions.list": ["r0", "r1"], "regions.adjacency": [["r0", "r1"]], "lenders.0.region": "r1",
          "borrowers.clients.0.slo_class": "relaxed", "time.fast_slot_min": 1,
          "borrowers.clients.0.demand": {"kind": "onoff", "on_mean_min": 20, "off_mean_min": 10, "level": 2.5,
                                         "seed": 3}}
    return drun.load_run_spec({"schema_version": 1, "name": "t", "instance": "toy.json", "overrides": ov,
                               "engine": {"record_routing": True, "check_invariants": True},
                               "policy": {"id": pid, "params": params or {}}})


# ---------------------------------------------------------------- the copy generator (scale.py)
@pytest.mark.parametrize("gamma", [2.6, 3.0, 0.7])
def test_copier_matches_per_request_reference(gamma):
    t, inp, out = _stream(180, 4.0, 1)
    idx = rp.StreamIndex.build(t, 180)
    cp = rp.Copier(t, inp, out, idx, gamma, 0.3, seed=5)
    got = [cp.second(s) for s in range(180)]
    st = cp.finish()
    ref, beyond = ref_copies(t, inp, out, gamma, 0.3, 5, 180)
    for s in range(180):
        np.testing.assert_allclose(got[s], ref[s], rtol=0, atol=0)
    assert st["n_beyond"] == beyond and st["copies_balance"] == 0
    assert st["n_emitted"] == sum(len(x) for x in ref) and st["n_requests"] == len(t)
    if gamma == 3.0:
        assert st["n_generated"] == 3 * len(t)            # an integer Gamma draws no extra copy
    if gamma < 1:
        assert st["n_generated"] < len(t)                 # floor 0: copy 0 alone, with probability Gamma


def test_copier_copy0_keeps_request_and_further_copies_from_the_minute():
    t, inp, out = _stream(120, 3.0, 2)
    idx = rp.StreamIndex.build(t, 120)
    l_req = 0.3 * inp + out
    cp = rp.Copier(t, inp, out, idx, 2.0, 0.3, seed=1)
    every = [cp.second(s) for s in range(120)]
    for s in range(120):
        own = l_req[idx.sec[s]:idx.sec[s + 1]]
        minute = set(l_req[idx.mins[s // 60]:idx.mins[s // 60 + 1]])
        if s % 60 == 0 and s:                             # copies carried from the last second of the minute before
            minute |= set(l_req[idx.mins[s // 60 - 1]:idx.mins[s // 60]])
        got = list(every[s])
        for x in own:                                     # copy 0 of each request of the second is there
            got.remove(x)
        assert set(got) <= minute                         # the further copies have sizes of the same minute
    a = rp.Copier(t, inp, out, idx, 2.5, 0.3, seed=1)
    b = rp.Copier(t, inp, out, idx, 2.5, 0.3, seed=1)
    c = rp.Copier(t, inp, out, idx, 2.5, 0.3, seed=2)
    xa, xb, xc = ([g.second(s) for s in range(120)] for g in (a, b, c))
    assert all(np.array_equal(p, q) for p, q in zip(xa, xb))
    assert any(len(p) != len(q) or not np.array_equal(p, q) for p, q in zip(xa, xc))
    with pytest.raises(ValueError):
        a.second(5)                                       # seconds are consecutive


def test_mooncake_copies_namespaces():
    tr = SimpleNamespace(n=3, t_s=np.array([0.0, 2.5, 7.0]), inp=np.array([600.0, 100.0, 1100.0]),
                         out=np.array([5.0, 6.0, 7.0]), hash_ids=[[1, 2], [3], [1, 2, 4]])
    cp = rp.mooncake_copies(tr, 2.0, seed=0, t0_s=100.0)
    assert cp["n_copies"] == 6 and sorted(cp["ns"].tolist()) == [0, 0, 0, 1, 1, 1]
    assert np.all(np.diff(cp["a"]) >= 0)
    for r in range(3):
        a = cp["a"][cp["req"] == r]
        ns = cp["ns"][cp["req"] == r]
        assert a[ns == 0][0] == 100.0 + tr.t_s[r] and 0 <= a[ns == 1][0] - (100.0 + tr.t_s[r]) < 1
    np.testing.assert_array_equal(cp["inp"], tr.inp[cp["req"]])


def test_mooncake_trace_stats_on_hand_traces():
    from sublet.replay.requests import MooncakeTrace
    mk = lambda hs, inp: MooncakeTrace("t", "-", np.arange(len(hs), dtype=float), np.asarray(inp, float),
                                       np.ones(len(hs)), hs)
    st = mk([[1, 2, 3], [1, 2, 9], [1, 4]], [1536, 1100, 600]).stats()
    assert st["blocks_total"] == 8 and st["blocks_unique"] == 5 and st["block_hit_ratio_infinite_cache"] == 3 / 8
    assert st["first_blocks_distinct"] == 1 and st["blocks_with_more_than_one_predecessor"] == 0
    assert st["requests_with_blocks_ne_ceil_input_over_512"] == 0
    st = mk([[1, 2], [3, 2]], [1024, 1024]).stats()                  # block 2 after 1 and after 3: not chained
    assert st["first_blocks_distinct"] == 2 and st["blocks_with_more_than_one_predecessor"] == 1


# ---------------------------------------------------------------- the per-second loop (loop.py)
def test_replay_hand_example():
    """Own capacity 1 slot, one site with 2 slots in minute 0 and 1 in minute 1 (TPOT 1 s, n_seq 2): at second 0
    copies of 10, 100, 80, 5 take own, site, site, fallback; at second 60 the latest arrival on the site (80) is
    stranded with (80 - 60) / 80 of its work left; at second 61 a copy of 7 takes the freed own slot."""
    svc = _svc(tpot=1.0, n_seq=2, w_in=0.5)
    plan = Placement(W=np.array([[1.0, 0.5]]), delta=np.array([0.3]), ok=np.array([True]), q=2.0, mu_fb=0.5,
                     fast_min=1, site_ids=("s0",))
    out = rp.replay(ListCopier({0: [10, 100, 80, 5], 61: [7]}), plan, svc, 1, 120, 120)
    c, tk = out["counts"], out["tokens"]
    assert (c["own"], c["leased"], c["fallback"], c["stranded"]) == (2, 2, 1, 1)
    assert tk["own"] == 17 and tk["leased"] == 160 and tk["fallback"] == 5 and tk["stranded_remainder"] == 20
    unit = 60 * 120.0
    assert out["costs"]["routing"] == pytest.approx(0.3 * 160 / unit, rel=1e-12)
    assert out["costs"]["fallback"] == pytest.approx(2.0 * 25 / unit, rel=1e-12)
    assert out["costs"]["stranding"] == pytest.approx(0.5 * 1 / 2, rel=1e-12)
    assert out["conservation"]["pass"] and out["conservation"]["tokens_stream"] == 202
    assert out["hold_max_s"] == 100


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_replay_against_per_copy_reference(seed):
    """Synthetic stream (Gamma 2.3) through four sites (one without an arc, a delta tie) whose capacity changes and
    drops every minute: counts, tokens and costs equal the per-copy reference; conservation (E8-1) holds."""
    n_sec = 600
    t, inp, out = _stream(n_sec, 1.5, seed)
    idx = rp.StreamIndex.build(t, n_sec)
    rng = np.random.default_rng(10 + seed)
    W = rng.integers(0, 4, size=(4, 10)).astype(np.float64) / 8.0
    plan = Placement(W=W, delta=np.array([0.5, 0.1, 0.0, 0.1]), ok=np.array([True, True, False, True]), q=7.15,
                     mu_fb=0.2, fast_min=1, site_ids=("a", "b", "c", "d"))
    svc = _svc(tpot=0.02, n_seq=16, w_in=0.3)
    ring = rp.ring_size(float((0.3 * inp + out).max()), svc)
    got = rp.replay(rp.Copier(t, inp, out, idx, 2.3, 0.3, seed=4), plan, svc, 12, n_sec, ring)
    ref_cp = rp.Copier(t, inp, out, idx, 2.3, 0.3, seed=4)
    ref = ref_replay([ref_cp.second(s) for s in range(n_sec)], plan, svc, 12, n_sec)
    c, tk = got["counts"], got["tokens"]
    assert c["own"] == ref["n_own"] and c["fallback"] == ref["n_fb"] and c["stranded"] == ref["n_str"]
    assert c["stranded"] > 0 and c["fallback"] > 0 and c["leased"] > 0
    assert c["leased_by_site"] == {plan.site_ids[l]: ref["n_site"][l] for l in plan.order}
    assert "c" not in c["leased_by_site"]                 # no arc, no copy
    for l in plan.order:
        assert tk["leased_by_site"][plan.site_ids[l]] == pytest.approx(ref["routed"][l], rel=1e-9, abs=1e-6)
    assert tk["fallback"] == pytest.approx(ref["fb"], rel=1e-12)
    assert tk["stranded_remainder"] == pytest.approx(ref["rem"], rel=1e-9)
    assert got["conservation"]["pass"] and got["conservation"]["counts_exact"]
    assert got["conservation"]["tokens_rel_diff"] <= 1e-9
    assert list(plan.order) == [1, 3, 0]                  # least delta first, the tie in site order


# ---------------------------------------------------------------- E8-2's oracle (fluid.py)
@pytest.mark.parametrize("pid", ["A6", "BL1", "BL4"])
def test_fluid_mode_reproduces_engine_on_toy(pid):
    """The fluid mode of a toy run with record_routing (two regions, a relaxed client, so delta > 0 at the remote
    site; 1-min fast slots, on/off demand) reproduces the engine's routing and fallback to 1e-6, and here also its
    stranding_fb, with x and b equal to RunResult.routing. Every run's capacity W drops at some fast slot; A6's run
    routes to the remote site (routing cost > 0)."""
    from sublet.drivers import run as drun
    from sublet.engine import simulate
    spec = _toy_spec(pid)
    inst, model, ecfg = drun.build(spec, 7)
    res = simulate(inst, drun.make_policy(spec, inst), model, ecfg)
    plan = rp.placement(res, inst)
    svc = _svc(w_in=inst.llms[0].w_in, tpot=60 * 128 / inst.llms[0].kappa_wtok_per_min)
    chk = rp.check_e8_2(res, inst, plan, svc)
    assert chk["pass"]
    assert chk["routing"]["rel_diff"] <= 1e-6 and chk["fallback"]["rel_diff"] <= 1e-6
    assert chk["stranding"]["rel_diff"] <= 1e-9 and chk["stranding"]["reported"]
    assert chk["max_abs_diff_x"] <= 1e-12 and chk["max_abs_diff_b"] <= 1e-12
    assert np.any(np.diff(plan.W, axis=1) < 0)                 # a capacity drop
    if pid == "A6":
        assert res.components["routing"] > 0 and res.components["fallback"] > 0


def test_fluid_mode_detects_a_wrong_placement():
    """E8-2 fails when the placement's capacity is not the run's (W halved)."""
    from sublet.drivers import run as drun
    from sublet.engine import simulate
    spec = _toy_spec("A6")
    inst, model, ecfg = drun.build(spec, 7)
    res = simulate(inst, drun.make_policy(spec, inst), model, ecfg)
    plan = rp.placement(res, inst)
    plan.W = plan.W * 0.5
    svc = _svc(w_in=inst.llms[0].w_in, tpot=60 * 128 / inst.llms[0].kappa_wtok_per_min)
    assert not rp.check_e8_2(res, inst, plan, svc)["pass"]


# ---------------------------------------------------------------- the request cache (requests.py)
def test_cache_roundtrip_memory_mapped(tmp_path):
    import json
    from sublet.replay import requests as rq
    t, inp, out = _stream(100, 2.0, 3)
    p = rq.cache_paths(tmp_path, "s")
    for k, a in zip(rq.CACHE_KEYS, (t, inp, out)):
        rq.save_npy(a, p[k].with_name(p[k].name + ".partial"))
        p[k].with_name(p[k].name + ".partial").rename(p[k])
    st = rq.stream_stats(t, inp, out)
    p["meta"].write_text(json.dumps({"rows": st["rows"], "window": {"dur_s": 100.0}}))
    arrs, meta = rq.open_cache(tmp_path, "s")
    assert all(isinstance(arrs[k], np.memmap) for k in rq.CACHE_KEYS)
    np.testing.assert_array_equal(arrs["t_s"], t)
    np.testing.assert_array_equal(arrs["out"], out)
    assert st["time_order_non_decreasing"] and st["max_inp"] == inp.max()
    assert rq.array_sha256(arrs["inp"]) == rq.array_sha256(inp)
    idx = rq.StreamIndex.build(arrs["t_s"], 100)
    np.testing.assert_array_equal(np.diff(idx.sec), np.bincount(np.floor(t).astype(int), minlength=100)[:100])
    p["meta"].write_text(json.dumps({"rows": st["rows"] + 1}))
    with pytest.raises(ValueError):
        rq.open_cache(tmp_path, "s")
    p["inp"].unlink()
    with pytest.raises(FileNotFoundError):
        rq.open_cache(tmp_path, "s")


# ---------------------------------------------------------------- replicas and the Mooncake loop
class DrainScript:
    """A scripted policy on the toy's protected site: two replicas bought at slot 0; replica A drained at minute
    30 (issued at slot 2), then the pending drain replaced by one at minute 50 (slot 4); replica B drained at minute
    60 (slot 8), applied, and drained again at minute 80 (slot 14), which changes nothing."""
    wants_fast = False
    name = "drain_script"

    def reset(self, view, rng):
        self.rep = []

    def act(self, obs):
        from sublet.types import Buy, Drain
        for r in obs.results:
            if r.ok and isinstance(r.action, Buy):
                self.rep = list(r.replica_ids)
        t = obs.t
        if t == 0:
            return [Buy(site=2, contract=2, llm=0, n_replicas=2)]
        plan = {2: (0, 30), 4: (0, 50), 8: (1, 60), 14: (1, 80)}
        if t in plan and self.rep:
            i, at = plan[t]
            return [Drain(self.rep[i], at)]
        return []

    def on_fast(self, obs):
        return []

    def params(self):
        return {}

    def report(self):
        return {}


def test_replica_plan_reproduces_W_with_replaced_drains():
    from sublet.drivers import run as drun
    from sublet.engine import simulate
    spec = _toy_spec("BL0a")
    inst, model, ecfg = drun.build(spec, 7)
    res = simulate(inst, DrainScript(), model, ecfg)
    rpl = rp.replica_plan(res, inst)                  # raises if the admissions do not reproduce W
    assert len(rpl.ids) == 2
    assert list(rpl.drain) == [50, 60]                # the replaced drain takes effect at 50, B's first at 60
    W = res.routing["W"][0, 2]
    assert W[49] == 2 and W[50] == 1 and W[59] == 1 and W[60] == 0
    events = list(res.events)
    # a wrong reconstruction is detected: without the replacing drain, A's drain at minute 30 would apply
    res.events = [e for e in events if not (e[1] == "drain" and int(e[2]["at_min"]) == 50)]
    assert len(res.events) == len(events) - 1
    with pytest.raises(ValueError, match="differ from RunResult.routing W"):
        rp.replica_plan(res, inst)
    res.events = events + [(20, "admission", {"replica": 0})]  # SetAdmission is not modelled
    with pytest.raises(ValueError, match="SetAdmission"):
        rp.replica_plan(res, inst)
    res.events = events
    rp.replica_plan(res, inst)


def _mc_trace():
    return SimpleNamespace(n=3, t_s=np.array([0.2, 5.0, 70.0]), inp=np.array([1536.0, 1536.0, 1536.0]),
                           out=np.array([10.0, 10.0, 10.0]), hash_ids=[[1, 2, 3], [1, 2, 9], [1, 2, 3]])


def test_replay_replicas_prefix_hits_and_conservation():
    """One own replica: the second request finds blocks 1 and 2 cached (input 1536 - 1024 counted); without hits
    every input counts; the tokens balance with the input saved by hits."""
    tr = _mc_trace()
    svc = _svc(tpot=0.001, n_seq=4, w_in=0.25)
    plan = Placement(W=np.zeros((1, 3)), delta=np.zeros(1), ok=np.array([True]), q=7.0, mu_fb=0.1, fast_min=1,
                     site_ids=("s0",))
    empty = ReplicaPlan(*(np.zeros(0, np.int64) for _ in range(5)), T_fast=3)
    cp = rp.mooncake_copies(tr, 1.0, seed=0)
    on = rp.replay_replicas(cp, tr, plan, empty, svc, 4, 0, 180, 50, True)
    off = rp.replay_replicas(cp, tr, plan, empty, svc, 4, 0, 180, 50, False)
    assert on["hits"]["block_hits"] == 2 + 3 and on["hits"]["blocks_on_replicas"] == 9
    assert on["tokens"]["input_tokens_saved_by_hits"] == 512 * 5
    assert off["tokens"]["own"] == pytest.approx(3 * (0.25 * 1536 + 10))
    assert on["tokens"]["own"] == pytest.approx(3 * (0.25 * 1536 + 10) - 0.25 * 512 * 5)
    assert on["conservation"]["pass"] and off["conservation"]["pass"] and off["hits"]["hit_ratio"] is None


def test_replay_replicas_longest_cached_prefix_and_partial_block():
    """Two own replicas of one slot (holds of 1 s). Second 0: request 0 (blocks 1, 2, 3) takes replica 0 (most free
    slots, lowest index), request 1 (1, 7, 8) the free replica 1. Second 5: request 2 (1, 7, 8, 9) finds both free and
    both holding its first block; it goes to replica 1, whose cached prefix (1, 7, 8) is longer, with 3 hits (a
    first-block rule would take replica 0, 1 hit). Second 10: request 3 (1, 2, 3) with input 1100, a partial last
    block, goes to replica 0 with 3 hits that save its whole input (min(1100, 3 x 512))."""
    tr = SimpleNamespace(n=4, t_s=np.array([0.1, 0.2, 5.0, 10.0]), inp=np.array([1536.0, 1536.0, 2048.0, 1100.0]),
                         out=np.full(4, 10.0), hash_ids=[[1, 2, 3], [1, 7, 8], [1, 7, 8, 9], [1, 2, 3]])
    svc = _svc(tpot=0.001, n_seq=1, w_in=0.25)
    plan = Placement(W=np.zeros((1, 1)), delta=np.zeros(1), ok=np.array([True]), q=7.0, mu_fb=0.1, fast_min=1,
                     site_ids=("s0",))
    empty = ReplicaPlan(*(np.zeros(0, np.int64) for _ in range(5)), T_fast=1)
    cp = rp.mooncake_copies(tr, 1.0, seed=0)
    on = rp.replay_replicas(cp, tr, plan, empty, svc, 2, 0, 60, 50, True)
    assert on["own_replicas"] == 2 and on["counts"]["own"] == 4 and on["counts"]["fallback"] == 0
    assert on["hits"]["blocks_on_replicas"] == 13 and on["hits"]["block_hits"] == 3 + 3
    assert on["tokens"]["input_tokens_saved_by_hits"] == 3 * 512 + 1100
    assert on["tokens"]["own"] == pytest.approx(0.25 * (1536 + 1536 + 512) + 4 * 10)
    assert on["conservation"]["pass"]


def test_replay_replicas_strands_like_the_site_level_loop():
    """One replica per site, no hits: site a's replica is drained at fast slot 4, site b's replica is warm from slot
    2 and dies at slot 7, with holds of up to 2 minutes, so copies are in flight at both drops. The replica-level loop
    strands what the site-level loop strands (latest arrivals first), with equal counts, remainders and costs."""
    rng = np.random.default_rng(7)
    n, T = 3000, 10
    tr = SimpleNamespace(n=n, t_s=np.sort(rng.random(n) * 60 * T), inp=rng.integers(200, 4000, n).astype(float),
                         out=rng.integers(50, 600, n).astype(float),
                         hash_ids=[[int(x)] for x in rng.integers(0, 50, n)])
    svc = _svc(tpot=0.03, n_seq=8, w_in=0.3)
    W = np.zeros((2, T))
    W[0, :4] = 1.0
    W[1, 2:7] = 1.0
    plan = Placement(W=W, delta=np.array([0.1, 0.2]), ok=np.array([True, True]), q=7.0, mu_fb=0.3, fast_min=1,
                     site_ids=("a", "b"))
    rpl = ReplicaPlan(ids=np.array([0, 1]), site=np.array([0, 1]), warm=np.array([0, 2]), end=np.array([T, 7]),
                      drain=np.array([4, T]), T_fast=T)
    cp = rp.mooncake_copies(tr, 3.3, seed=2)
    ring = rp.ring_size(float((0.3 * tr.inp + tr.out).max()), svc)
    rr = rp.replay_replicas(cp, tr, plan, rpl, svc, 5, 0, 60 * T, ring, False)
    per = {}
    for a, i in zip(cp["a"], cp["req"]):
        per.setdefault(int(a), []).append(0.3 * tr.inp[i] + tr.out[i])
    sl = rp.replay(ListCopier(per), plan, svc, 5, 60 * T, ring)
    assert rr["counts"]["stranded"] > 0 and rr["counts"]["replica_deaths"] == 1
    for k in ("own", "leased", "fallback", "stranded"):
        assert rr["counts"][k] == sl["counts"][k]
    assert rr["tokens"]["stranded_remainder"] == pytest.approx(sl["tokens"]["stranded_remainder"], rel=1e-12)
    for k in ("routing", "fallback", "stranding"):
        assert rr["costs"][k] == pytest.approx(sl["costs"][k], rel=1e-12, abs=1e-15)
    assert rr["conservation"]["pass"] and sl["conservation"]["pass"]


def test_replay_replicas_cache_emptied_at_death():
    """Replica A (site 0) dies at fast slot 1, replica B is warm from fast slot 1: the request at 70 s lands on B,
    whose cache is empty, so it has no hit, although A had served the same blocks."""
    tr = _mc_trace()
    svc = _svc(tpot=0.001, n_seq=4, w_in=0.25)
    plan = Placement(W=np.array([[1.0, 1.0, 1.0]]), delta=np.array([0.1]), ok=np.array([True]), q=7.0, mu_fb=0.1,
                     fast_min=1, site_ids=("s0",))
    rpl = ReplicaPlan(ids=np.array([0, 1]), site=np.array([0, 0]), warm=np.array([0, 1]), end=np.array([1, 3]),
                      drain=np.array([3, 3]), T_fast=3)
    cp = rp.mooncake_copies(tr, 1.0, seed=0)
    on = rp.replay_replicas(cp, tr, plan, rpl, svc, 0, 0, 180, 50, True)
    assert on["counts"]["replica_deaths"] == 1 and on["counts"]["leased"] == 3
    assert on["hits"]["block_hits"] == 2                  # request 1 on A; request 2 on the fresh B: none
    assert on["conservation"]["pass"]


def test_replay_replicas_without_hits_equals_site_level_loop():
    """Without hits and without capacity drops, the replica-level loop gives the site-level loop's counts and
    costs on the same copies."""
    rng = np.random.default_rng(3)
    n = 400
    tr = SimpleNamespace(n=n, t_s=np.sort(rng.random(n) * 300), inp=rng.integers(1, 2000, n).astype(float),
                         out=rng.integers(1, 300, n).astype(float), hash_ids=[[int(x)] for x in rng.integers(0, 50, n)])
    svc = _svc(tpot=0.02, n_seq=4, w_in=0.3)
    W = np.ones((2, 5))
    plan = Placement(W=W, delta=np.array([0.2, 0.1]), ok=np.array([True, True]), q=7.0, mu_fb=0.1, fast_min=1,
                     site_ids=("a", "b"))
    rpl = ReplicaPlan(ids=np.array([0, 1]), site=np.array([0, 1]), warm=np.zeros(2, np.int64),
                      end=np.full(2, 5), drain=np.full(2, 5), T_fast=5)
    cp = rp.mooncake_copies(tr, 2.4, seed=1)
    ring = rp.ring_size(float((0.3 * tr.inp + tr.out).max()), svc)
    rr = rp.replay_replicas(cp, tr, plan, rpl, svc, 6, 0, 300, ring, False)
    per = {}
    for a, i in zip(cp["a"], cp["req"]):
        per.setdefault(int(a), []).append(0.3 * tr.inp[i] + tr.out[i])
    sl = rp.replay(ListCopier(per), plan, svc, 6, 300, ring)
    assert rr["counts"]["own"] == sl["counts"]["own"] and rr["counts"]["fallback"] == sl["counts"]["fallback"]
    assert rr["counts"]["leased"] == sl["counts"]["leased"] and sl["counts"]["stranded"] == 0
    for k in ("routing", "fallback", "stranding"):
        assert rr["costs"][k] == pytest.approx(sl["costs"][k], rel=1e-12, abs=1e-15)


# ---------------------------------------------------------------- raw traces (needs_raw)
@pytest.mark.needs_raw
def test_mooncake_loader_keeps_hash_ids():
    import json
    from sublet.paths import ANALYSIS_OUT
    from sublet.traces.borrowers import load_requests
    tr = rp.load_mooncake()
    st = tr.stats()
    a5 = json.loads((ANALYSIS_OUT / "a5_reclaim_cost_calibration.json").read_text())["mooncake"]["conversation"]
    assert tr.n == 12031 == a5["n"] and len(tr.hash_ids) == tr.n
    assert st["requests_with_blocks_ne_ceil_input_over_512"] == 0 and st["blocks_total"] == 288500
    # one first block shared by every request, and prefix-chained ids: the routing rule of replay_replicas
    assert st["first_blocks_distinct"] == 1 and st["blocks_with_more_than_one_predecessor"] == 0
    assert st["block_hit_ratio_infinite_cache"] == pytest.approx(a5["prefix_block_hit_ratio_infinite_cache"],
                                                                rel=1e-12)
    lr = load_requests("mooncake_conversation")
    assert set(lr) == {"t_s", "inp", "out"}                # load_requests drops hash_ids, unchanged
    for k in ("t_s", "inp", "out"):
        np.testing.assert_array_equal(lr[k], getattr(tr, k))


@pytest.mark.needs_raw
def test_azure_first_hour_cache(tmp_path):
    from sublet.replay import requests as rq
    a = rq.load_azure(3600.0)
    assert len(a["t_s"]) > 0 and a["t_s"][0] == 0.0 and a["t_s"][-1] < 3600
    p = rq.cache_paths(tmp_path)
    for k in rq.CACHE_KEYS:
        rq.save_npy(a[k], p[k])
    import json
    p["meta"].write_text(json.dumps({"rows": len(a["t_s"])}))
    arrs, _ = rq.open_cache(tmp_path)
    np.testing.assert_array_equal(arrs["inp"], a["inp"])
    idx = rq.StreamIndex.build(arrs["t_s"], 3600)
    assert idx.sec[-1] == len(a["t_s"]) and idx.mins[-1] == len(a["t_s"])


# ---------------------------------------------------------------- E8's instance (needs_a12)
@pytest.mark.needs_a12
@pytest.mark.parametrize("reduced", [True, False], ids=["reduced", "week"])
@pytest.mark.parametrize("tier,tpot,w_in", [("S", 0.015, 0.2133), ("M", 0.035, 0.3048), ("L", 0.06, 0.5333)])
def test_e8_instance_service_model_and_scale(monkeypatch, tier, tpot, w_in, reduced):
    """E8's instance of the reduced list and of the grid (the week at market tightness 0.5): the service model, and
    Gamma times the builder's overflow reproduces the demand (market_scale raises otherwise); Gamma grows with the
    smoothing window, so the job order of e8.jobs puts the window with the most copies first."""
    if reduced:
        monkeypatch.setenv("MS3_E8_REDUCED", "1")
    else:
        monkeypatch.delenv("MS3_E8_REDUCED", raising=False)
    from sublet.experiments import e8
    S = e8.settings()
    gam = {}
    for w in S["windows"]:
        inst, model, ecfg, spec = e8.build(tier, w, 1.0, 1)
        assert inst.grid.fast_min == 1 and inst.n == 1 and inst.llms[0].tier == tier and inst.llms[0].id == tier
        assert inst.grid.horizon_min == S["horizon_min"]
        assert inst.config["borrowers"]["list"][0]["tier"] == tier and inst.config["borrowers"]["smoothing_min"] == w
        assert inst.config["borrowers"]["market_tightness"] == S["market_tightness"]
        assert ecfg.record_routing and ecfg.check_invariants
        svc = rp.service_model(inst)
        assert svc.n_seq == 128 and svc.tpot_s == tpot and round(svc.w_in, 4) == w_in
        ms = rp.market_scale(inst, svc.n_seq)
        assert ms.own_slots == math.floor(128 * inst.borrower_stats["azure0"]["C0_loads"] + 1e-9)
        assert ms.demand_max_rel_diff <= 1e-12 and ms.gamma > 0
        gam[w] = ms.gamma
    if not reduced:
        assert gam[5] < gam[15] < gam[60]
        first = next(j for j in e8.jobs() if j.params["kind"] == "pair" and j.params["tier"] == tier)
        assert first.params["win"] == 60


@pytest.mark.needs_a12
@pytest.mark.parametrize("reduced,tier,win", [(True, "M", 5), (False, "L", 60)], ids=["reduced-M5", "week-L60"])
def test_e8_2_on_e8_instance(monkeypatch, reduced, tier, win):
    """E8-2 and E8-3 on E8's reduced instance (tier M) and on a week of the grid (tier L, the shortest fluid run):
    the fluid mode reproduces the engine; the replicas reproduce W; the policy record is the resolved A6."""
    if reduced:
        monkeypatch.setenv("MS3_E8_REDUCED", "1")
    else:
        monkeypatch.delenv("MS3_E8_REDUCED", raising=False)
    from sublet.experiments import e8
    inst, model, ecfg, spec = e8.build(tier, win, 1.0, 1)
    res, _, pol = e8.fluid_run(inst, model, ecfg, spec, 1)
    svc = rp.service_model(inst)
    chk = rp.check_e8_2(res, inst, rp.placement(res, inst), svc)
    assert chk["pass"] and e8.e8_3(res)["pass"]
    assert chk["max_abs_diff_x"] <= 1e-9 and chk["max_abs_diff_b"] <= 1e-9
    rp.replica_plan(res, inst)
    assert pol["id"] == "A6" and pol["params"] and pol["info_class"] == "online-I1"
