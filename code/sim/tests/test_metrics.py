"""Tests of sublet/ledger.py totals and sublet/metrics.py (design/sim_spec.md §3.6, §5.6, §5.9; §9.2)."""
import numpy as np

from fixtures import recording_policy, toy_instance

from sublet.engine import simulate
from sublet.ledger import COMPONENTS, Ledger
from sublet.metrics import aggregate, ratio, run_metrics
from sublet.policies import AlwaysFallback, FixedPlan
from sublet.types import Buy, PlannedLease, SolveResult


def test_components_and_totals():
    assert COMPONENTS == ("lease_prepaid", "lease_rent", "loading", "routing", "fallback",
                          "stranding_kv", "stranding_fl", "stranding_fb", "stranding_pi")
    L = Ledger(3)
    adds = [("lease_prepaid", 0, 1.5), ("lease_rent", 1, 0.25), ("loading", 0, 0.1), ("routing", 2, 0.05),
            ("fallback", 1, 2.0), ("fallback", 1, 1.0), ("stranding_kv", 2, 0.3), ("stranding_fl", 1, 0.2),
            ("stranding_fb", 2, 0.4), ("stranding_pi", 0, 0.01)]
    for comp, t, usd in adds:
        L.add(comp, t, usd)
    ps = L.per_slot()
    assert set(COMPONENTS) <= set(ps)
    assert all(ps[k].shape == (3,) for k in COMPONENTS)
    assert np.allclose(ps["fallback"], [0.0, 3.0, 0.0], rtol=0, atol=1e-12)
    assert np.allclose(ps["lease_prepaid"], [1.5, 0.0, 0.0], rtol=0, atol=1e-12)
    tot = L.totals()
    want = {"lease_prepaid": 1.5, "lease_rent": 0.25, "loading": 0.1, "routing": 0.05, "fallback": 3.0,
            "stranding_kv": 0.3, "stranding_fl": 0.2, "stranding_fb": 0.4, "stranding_pi": 0.01}
    for k, v in want.items():
        assert abs(tot[k] - v) <= 1e-12, k
    assert abs(tot["lease"] - 1.75) <= 1e-12
    assert abs(tot["stranding"] - 0.91) <= 1e-12
    assert abs(tot["total"] - sum(want.values())) <= 1e-12
    # a run: components add up, and run_metrics reports the same cost
    inst = toy_instance()
    res = simulate(inst, FixedPlan([PlannedLease(0, 0, 0, 0), PlannedLease(1, 1, 0, 4, release_slot=12),
                                    PlannedLease(2, 2, 0, 10)]))
    c = res.components
    assert abs(sum(c[k] for k in COMPONENTS) - c["total"]) <= 1e-12 * max(1.0, c["total"])
    if "lease" in c:                                   # Ledger.totals() keys, if RunResult carries them
        assert abs(c["lease"] - c["lease_prepaid"] - c["lease_rent"]) <= 1e-12
    if "stranding" in c:
        assert abs(c["stranding"] - sum(c[k] for k in COMPONENTS if k.startswith("stranding"))) <= 1e-12
    for k in COMPONENTS:
        assert abs(res.per_slot[k].sum() - c[k]) <= 1e-12 * max(1.0, abs(c[k])), k
    m = run_metrics(res, inst)
    for k in COMPONENTS + ("total",):
        assert abs(m["cost"][k] - c[k]) <= 1e-12 * max(1.0, abs(c[k])), k


def test_fallback_share_hand():
    """AlwaysFallback: share 1. A short lease at L0 (lambda = 0) bought at slot 2 dies at minute 35, so it
    serves the demand of slots 2-6, 5 of the 16 demand slot-loads: share 11/16."""
    inst = toy_instance({"lenders.0.lam_s": 0.0})
    m = run_metrics(simulate(inst, AlwaysFallback()), inst)
    assert abs(m["fallback_share"] - 1.0) <= 1e-12
    res = simulate(inst, FixedPlan([PlannedLease(0, 0, 0, 2)]))
    (L,) = res.leases
    assert (L.start_min, L.end_min) == (10, 35)
    m = run_metrics(res, inst)
    assert abs(m["fallback_share"] - 11.0 / 16.0) <= 1e-12


def test_ratio_fields():
    sr = SolveResult(method="milp", benchmark="omega", grid="slow", status=1, status_msg="time limit",
                     objective=10.0, dual_bound=8.0, gap=0.2, plan=None, components={}, size={},
                     build_s=0.0, solve_s=0.0, peak_rss_mb=0.0)
    r = ratio(12.0, sr)
    assert set(r) == {"vs_objective", "vs_bound", "status", "gap"}
    assert abs(r["vs_objective"] - 1.2) <= 1e-12 and abs(r["vs_bound"] - 1.5) <= 1e-12
    assert r["status"] == 1 and r["gap"] == 0.2
    lp = SolveResult(method="lp", benchmark="omega", grid="slow", status=0, status_msg="", objective=4.0,
                     dual_bound=4.0, gap=0.0, plan=None, components={}, size={}, build_s=0.0, solve_s=0.0,
                     peak_rss_mb=0.0)
    r = ratio(5.0, lp)
    assert abs(r["vs_objective"] - 1.25) <= 1e-12 and abs(r["vs_bound"] - 1.25) <= 1e-12 and r["status"] == 0


def test_aggregate_deterministic():
    values = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0, 5.0, 3.5]
    a, b = aggregate(values, seed=0), aggregate(values, seed=0)
    assert set(a) == {"n", "median", "p95", "max", "median_ci95"}
    assert a == b
    assert a["n"] == 10
    assert abs(a["median"] - float(np.median(values))) <= 1e-12
    assert abs(a["p95"] - float(np.percentile(values, 95))) <= 1e-12
    assert a["max"] == 9.0
    lo, hi = a["median_ci95"]
    assert min(values) <= lo <= hi <= max(values)
    assert aggregate(values, seed=0, B=500) == aggregate(values, seed=0, B=500)


def test_aggregate_bootstrap_interval():
    """The 95% percentile-bootstrap interval of the median (§5.9: B = 2000, default_rng(seed)),
    recomputed from B resamples of default_rng(0) (1e-12)."""
    v = np.array([3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0, 5.0, 3.5])
    idx = np.random.default_rng(0).integers(0, len(v), size=(2000, len(v)))
    lo, hi = np.percentile(np.median(v[idx], axis=1), [2.5, 97.5])
    got = aggregate(v, seed=0)["median_ci95"]
    assert abs(got[0] - lo) <= 1e-12 and abs(got[1] - hi) <= 1e-12, (got, lo, hi)


def test_fallback_share_after_reclaims_window():
    """fallback_share_after_reclaims (§5.9): the window is the 60 minutes (12 fast slots of 5 min) from
    the reclaim-caused drop at fast slot 7 (short lease at L0 announced at slot 6, dying at minute 35).
    A protected lease bought at slot 19 (lambda 600 s) serves from fast slot 21, after the window, so
    the share is 1; overall, L0 serves slots 0-6 and P slots 21-23: 1 - (7 x 0.8 + 3 x 0.5) / (7 x 0.8 +
    17 x 0.5) (1e-12)."""
    inst = toy_instance({"borrowers.clients.0.demand.values": [0.8] * 7 + [0.5] * 17, "lenders.0.R": [6],
                         "lenders.0.lam_s": 0.0, "lenders.2.lam_s": 600.0}, sites=["L0", "P"])
    res = simulate(inst, recording_policy({0: [Buy(0, 0, 0)], 19: [Buy(1, 2, 0)]}))
    assert res.invariant_failures == []
    m = run_metrics(res, inst)
    assert abs(m["fallback_share_after_reclaims"] - 1.0) <= 1e-12
    want = 1.0 - (7 * 0.8 + 3 * 0.5) / (7 * 0.8 + 17 * 0.5)
    assert abs(m["fallback_share"] - want) <= 1e-12, (m["fallback_share"], want)
