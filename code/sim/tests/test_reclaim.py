"""Tests of sublet/reclaim.py (design/sim_spec.md §3.3, rules T5 and T10; §9.2)."""
import numpy as np
import pytest

import core
import fam

from sublet import reclaim
from sublet.types import Contract, TimeGrid

INF_FAM = fam.INF          # fam's "never" (10**9)
INF_CORE = 10 ** 9         # core.effective_end's "never"


def _contract(tau, H, slow_min=1, klass="general"):
    return Contract("k", tau, H, tau * slow_min + H, klass)


def test_first_announcement_matches_core():
    """1,000 random (R, s, tau, H): death slot equals core.effective_end and fam.Fam.death."""
    rng = np.random.default_rng(20261016)
    for case in range(1000):
        T = int(rng.integers(5, 60))
        R = np.sort(np.flatnonzero(rng.random(T) < rng.uniform(0.0, 0.6))).astype(np.int64)
        s = int(rng.integers(0, T))
        tau = int(rng.integers(1, 6))
        H = int(rng.integers(0, 6))
        I = core.Instance(T=T, tau=np.array([tau]), H=np.array([H]), a=np.ones((1, 1)), beta=np.zeros((1, 1)),
                          g=np.array([1]), q=1.0, cl_llm=np.array([0]), delta=np.zeros((1, 1)),
                          active=np.ones((1, T), dtype=bool))
        ref = core.effective_end(I, [R], 0, 0, s)
        F = fam.Fam(1, 2.0, tau, H, T)
        ref_fam = F.death([R], 0, s)
        ref_ann = F.ann([R], 0, s)
        assert ref == ref_fam
        r = reclaim.first_announcement(R, s, tau)
        assert (r is None) == (ref_ann == INF_FAM), case
        if r is not None:
            assert r == ref_ann
        # slot units (slow_min = 1, H in slots = minutes)
        d1 = reclaim.death_min(R, s, _contract(tau, H, 1), 1)
        assert (d1 is None) == (ref == INF_CORE), case
        if d1 is not None:
            assert d1 == ref
        # 5-min slots with H a multiple of the slot: death minute = 5 * core death slot
        d5 = reclaim.death_min(R, s, _contract(tau, 5 * H, 5), 5)
        assert (d5 is None) == (ref == INF_CORE)
        if d5 is not None:
            assert d5 == 5 * ref
        # vectorized form, -1 for never
        starts = np.arange(T, dtype=np.int64)
        dv = reclaim.death_mins(R, starts, _contract(tau, H, 1), 1)
        refv = np.array([core.effective_end(I, [R], 0, 0, int(x)) for x in starts])
        assert np.array_equal(dv, np.where(refv == INF_CORE, -1, refv))
    # protected contracts are never announced
    prot = Contract("p", None, 0, 5, "protected")
    assert reclaim.death_min(np.arange(10, dtype=np.int64), 0, prot, 5) is None


def test_death_bench_rounding():
    """Hand cases of rule T10 with H not a multiple of the slow slot (the example of §3.1)."""
    def triple(R, s, tau_slots, H_min, slow_min, fast_min, T_slow):
        c = Contract("k", tau_slots, H_min, tau_slots * slow_min + H_min, "general")
        g = TimeGrid(slow_min, fast_min, T_slow)
        return tuple(reclaim.death_bench(np.asarray(R, dtype=np.int64), s, c, g, b)
                     for b in ("slow", "fast", "slow_lb"))

    # §3.1: spot-like lease (tau = 1 slot, H = 2 min) bought at slot 10, first announcement >= 11 is
    # slot 13: death at minute 67 -> slow floor(67/5) = 13, fast 67, slow_lb ceil(67/5) = 14
    assert reclaim.death_min(np.array([3, 13, 15]), 10, Contract("k", 1, 2, 7, "spot-like"), 5) == 67
    assert triple([3, 13, 15], 10, 1, 2, 5, 1, 20) == (13, 67, 14)
    # an announcement in the purchase slot or before s + tau does not count
    assert triple([10, 13], 10, 1, 2, 5, 1, 20) == (13, 67, 14)
    # never announced: T_b on every grid
    assert triple([1, 2], 10, 1, 2, 5, 1, 20) == (20, 100, 20)
    # §8.4: T_s = 2, eager R = {0, 1}, tau = 1 slot, H = 2 min: death at minute 7
    assert triple([0, 1], 0, 1, 2, 5, 1, 2) == (1, 7, 2)
    # §8.6: T_s = 4, R = {1}, tau = 2 slots, H = 0: never announced
    assert triple([1], 0, 2, 0, 5, 1, 4) == (4, 20, 4)
    # H = 7 min: death at 5 * 4 + 7 = 27 -> (5, 27, 6); H = 3 min on 1-min fast slots
    assert triple([4], 2, 1, 7, 5, 1, 10) == (5, 27, 6)
    assert triple([4], 2, 1, 3, 5, 1, 10) == (4, 23, 5)
    # death on a slow boundary (H a multiple of the slot): all grids agree
    assert triple([2], 0, 1, 5, 5, 1, 10) == (3, 15, 3)
    # death past the horizon is capped at T_b
    assert triple([9], 0, 1, 60, 5, 1, 10) == (10, 50, 10)
    # fast slot = slow slot: the three grids coincide
    assert triple([13], 10, 1, 2, 5, 5, 20) == (13, 13, 13)
    # 15-min slow slots, 5-min fast slots: death at 15 * 3 + 20 = 65 -> (4, 13, 5)
    assert triple([3], 0, 1, 20, 15, 5, 10) == (4, 13, 5)
    # protected contracts: never announced
    g = TimeGrid(5, 1, 20)
    prot = Contract("p", None, 0, 5, "protected")
    assert [reclaim.death_bench(np.arange(20), 3, prot, g, b) for b in ("slow", "fast", "slow_lb")] == [20, 100, 20]


@pytest.mark.parametrize("bench", ["slow", "fast", "slow_lb"])
def test_cohorts_partition(bench):
    """cohorts() partitions the starts by E_b, sorted by E_b, with E_b non-decreasing in the start."""
    rng = np.random.default_rng(7 + ["slow", "fast", "slow_lb"].index(bench))
    for case in range(300):
        slow_min = int(rng.choice([1, 5, 15]))
        fast_min = int(rng.choice([d for d in (1, 5, 15) if slow_min % d == 0]))
        T_s = int(rng.integers(1, 40))
        g = TimeGrid(slow_min, fast_min, T_s)
        if rng.random() < 0.15:
            c = Contract("p", None, 0, slow_min, "protected")
        else:
            tau = int(rng.integers(1, 4))
            H = int(rng.integers(0, 3 * slow_min + 1))
            c = Contract("k", tau, H, tau * slow_min + H, "general")
        R = np.flatnonzero(rng.random(T_s) < rng.uniform(0, 0.7)).astype(np.int64)
        starts = np.flatnonzero(rng.random(T_s) < 0.6).astype(np.int64)
        coh = reclaim.cohorts(R, starts, c, g, bench)
        E_all = np.array([reclaim.death_bench(R, int(s), c, g, bench) for s in starts], dtype=np.int64)
        assert np.all(np.diff(E_all) >= 0), "E_b not non-decreasing in the start"
        keys = [E for E, _ in coh]
        assert keys == sorted(set(keys)), "cohorts not sorted by E_b or keys repeated"
        got = np.concatenate([p for _, p in coh]) if coh else np.zeros(0, dtype=np.int64)
        assert np.array_equal(np.sort(got), np.sort(starts)), "not a partition of the starts"
        for E, part in coh:
            assert len(part) > 0
            for s in part:
                assert reclaim.death_bench(R, int(s), c, g, bench) == E
        if len(starts) == 0:
            assert coh == []
