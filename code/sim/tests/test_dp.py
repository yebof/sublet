"""Tests of sublet/opt/dp.py (design/sim_spec.md §3.7, §7; §9.2)."""
import copy
import math

import numpy as np
import pytest

import check_c4_lower
import fam

from fixtures import (_build_single, c4l_e, explicit_client, fam_case, fixed_76_case, load_json,
                      single_site_case, single_site_config, toy_config, toy_instance, trace_schedule,
                      with_capacity, with_stranding)

from sublet import reclaim
from sublet.instance import build_instance, from_core
from sublet.ledger import COMPONENTS
from sublet.opt.dp import DomainError, dp_domain, solve_dp
from sublet.opt.milp import solve_opt
from sublet.paths import C3
from sublet.types import Schedule

C4 = load_json(C3 / "out" / "c4_lower.json")


def _milp(inst, sched, grid="slow"):
    r = solve_opt(inst, sched, grid=grid, mip_rel_gap=1e-9)
    assert r.status == 0, r.status_msg
    return r.objective


def _dp(inst, sched, grid="slow", **kw):
    r = solve_dp(inst, sched, grid=grid, **kw)
    assert r.status == 0 and r.objective is not None, r.status_msg
    return r


def _close(a, b, tol):
    return abs(a - b) <= tol * max(1.0, abs(b))


def test_dp_family_equals_fam_opt_dp():
    """m = 1 family instances: the DP equals fam.opt_dp (1e-9 abs)."""
    n = 0
    for rho in (2, 8, 32):
        for (tau, H) in ((1, 0), (2, 1), (1, 3)):
            for sched_name in ("bern0.02", "bern0.2", "iid0.5"):
                for seed in range(3):
                    F, om = fam_case(1, rho, tau, H, 96, sched_name, seed)
                    inst, sched = from_core(F.core_instance(), om)
                    got = _dp(inst, sched).objective
                    want = fam.opt_dp(F, om)[0]
                    assert abs(got - want) <= 1e-9, (rho, tau, H, sched_name, seed, got, want)
                    n += 1
    assert n == 81


def test_dp_eager_equals_pp_dp():
    """check_c4_lower part (e) instances: the DP under 'eager' equals pp_dp and c4_lower.json e[*].dp."""
    for seed in range(20):
        I = c4l_e(seed)
        inst, _ = from_core(I, [np.arange(I.T)])
        got = _dp(inst, Schedule.eager(inst)).objective
        pp = check_c4_lower.pp_dp(I.T, I.active[0], list(I.L), [I.C(0, 0, k) for k in range(I.K)], I.q)
        assert C4["e"][seed]["seed"] == seed
        assert abs(got - pp) <= 1e-9 and abs(got - C4["e"][seed]["dp"]) <= 1e-9, (seed, got, pp)


def test_dp_equals_milp_single_site(record_property):
    """Claim D2: DP = MILP (1e-6) on 40 'bern' and 20 'runs' cases, the fixed case of §7.6 (where capacity
    2 g_j at the revocable site must cost strictly more) and 20 cases near it."""
    for kind, n in (("bern", 40), ("runs", 20)):
        for seed in range(n):
            inst, sched = single_site_case(seed, "slow", kind)
            assert dp_domain(inst, sched) == []
            d, m = _dp(inst, sched).objective, _milp(inst, sched)
            assert _close(d, m, 1e-6), (kind, seed, d, m)
    inst, sched = fixed_76_case()
    d, m = _dp(inst, sched).objective, _milp(inst, sched)
    assert _close(d, m, 1e-6), (d, m)
    capped = with_capacity(copy.deepcopy(inst), {0: 2 * inst.llms[0].g})
    m2 = _milp(capped, sched)
    assert m2 > m + 1e-6 * max(1.0, m), (m, m2)
    need_more = 0
    for seed in range(20):
        inst, sched = single_site_case(seed, "slow", "near")
        d, m = _dp(inst, sched).objective, _milp(inst, sched)
        assert _close(d, m, 1e-6), ("near", seed, d, m)
        rev = [i for i, s in enumerate(inst.sites) if s.kind != "protected"]
        m2 = _milp(with_capacity(copy.deepcopy(inst), {i: 2 * inst.llms[0].g for i in rev}), sched)
        need_more += m2 > m + 1e-6 * max(1.0, m)
    record_property("near_cases_needing_capacity_above_2g", need_more)
    print(f"near cases needing capacity above 2 g_j: {need_more} of 20")


def test_dp_refuse_equals_milp():
    """refuse_unavailable (§7.4 step 3, §8.1): DP = MILP (1e-6) with the starts in R refused, on 10 'bern'
    and 5 'fast' single_site_case instances; on at least one the refusal changes the optimum."""
    changed = 0
    for grid, seeds in (("slow", range(10)), ("fast", range(5))):
        for seed in seeds:
            inst, sched = single_site_case(seed, grid)
            d = _dp(inst, sched, grid=grid, refuse_unavailable=True).objective
            m = _ok_opt(solve_opt(inst, sched, grid=grid, refuse_unavailable=True, mip_rel_gap=1e-9))
            assert _close(d, m, 1e-6), (grid, seed, d, m)
            changed += not _close(m, _milp(inst, sched, grid=grid), 1e-9)
    assert changed > 0


def _ok_opt(r):
    assert r.status == 0, r.status_msg
    return r.objective


# single_site_case(seed, 'fast') seeds in which the rent of a retiring serving lease up to the next
# decision slot t+ changes the optimum (found by scanning seeds 0-299 with that rent removed)
RETIRE_RENT_SEEDS = (128, 161, 176, 205, 221)


def test_dp_fast_grid():
    """40 cases with Delta_s = 5, Delta_f = 1 (H in {2, 7} min among them) and the 5 cases of
    RETIRE_RENT_SEEDS: DP = MILP on grid 'fast'."""
    Hs = set()
    for seed in list(range(40)) + list(RETIRE_RENT_SEEDS):
        inst, sched = single_site_case(seed, "fast")
        Hs |= {c.H_min for c in inst.contracts if not c.protected}
        assert dp_domain(inst, sched, grid="fast") == []
        d, m = _dp(inst, sched, grid="fast").objective, _milp(inst, sched, grid="fast")
        assert _close(d, m, 1e-6), (seed, d, m)
    assert {2, 7} <= Hs


def plan_cost(inst, sched, plan, grid):
    """Ledger of a single-client DP plan on its bench grid, recomputed from rules T5-T8 (§5.6, §7.4):
    every admitting warm lease serves the whole demand (one replica load at most, equal routing costs)."""
    g = inst.grid
    Db = g.bench_min(grid)
    Tb = g.T_bench(grid)
    phib = g.slow_min // Db
    per_b = Db // g.fast_min
    assert per_b == 1, "the evaluator needs Delta_b = Delta_f"
    d = inst.clients.demand[0]
    j = int(inst.clients.llm[0])
    q = inst.llms[j].q_usd_per_h
    gj = inst.llms[j].g
    lam_ms = inst.lam_ms()
    comp = dict.fromkeys(COMPONENTS, 0.0)
    serving = np.zeros(Tb, dtype=bool)
    delta = None
    for pl in plan:
        c = inst.contracts[pl.contract]
        a = inst.price[pl.site, pl.contract]
        G = pl.n * gj
        sb = pl.start_slot * phib
        E = reclaim.death_bench(sched.R[pl.site], pl.start_slot, c, g, grid)
        end = min(E, pl.release_slot * phib if pl.release_slot is not None else Tb)
        Pb = math.ceil(c.prepaid_min / Db)
        Lam = math.ceil(int(lam_ms[pl.llm, pl.site]) / (60000 * Db))
        comp["lease_prepaid"] += G * a * c.prepaid_min / 60.0
        comp["loading"] += pl.n * inst.beta_usd[pl.llm, pl.site]
        off = np.zeros(Tb, dtype=bool)
        for (lo, hi) in pl.admission_off:
            off[lo:hi] = True
        for t in range(sb, end):
            if t >= sb + Pb:
                comp["lease_rent"] += G * a * Db / 60.0
            if t >= sb + Lam and not off[t] and pl.llm == j:
                serving[t] = True
                delta = inst.clients.delta_usd_per_h[0, pl.site]
    mu = inst.stranding.mu_fb_usd[j]
    prev_d, prev_s = 0.0, False
    for t in range(Tb):
        s = bool(serving[t] and d[t] > 0)
        if d[t] > 0:
            if s:
                comp["routing"] += delta * d[t] * Db / 60.0
            else:
                comp["fallback"] += q * d[t] * Db / 60.0
        comp["stranding_fb"] += mu * max(0.0, min(prev_d, d[t]) * prev_s - d[t] * s)
        prev_d, prev_s = d[t], s
    return comp


def _adm_case():
    """The hand case of test_engine.py::test_fixedplan_replays_dp: a DP plan with an admission_off
    interval (refuse_unavailable; value 0.25 + 4 x 7.15 / 12)."""
    cfg = single_site_config(6, 5, [("r1", 15, 0)], {"r1": 1.0}, 50.0, [2, 3, 4, 5], 0.0, 0.0,
                             [1, 0, 1, 1, 1, 1], "prepaid_D")
    return _build_single(cfg, unlimited=True, mu_fb=3.0)


def test_dp_plan_consistent():
    """The plan's recomputed ledger equals the DP's components and objective (1e-9); one of the plans
    has an admission_off interval."""
    cases = [(single_site_case(s, "slow"), "slow", False) for s in range(10)]
    cases += [(single_site_case(s, "slow", "runs"), "slow", False) for s in range(5)]
    cases += [(single_site_case(s, "fast"), "fast", False) for s in range(5)]
    cases += [(fixed_76_case(), "slow", False), (_adm_case(), "slow", True)]
    n_adm = 0
    for (inst, sched), grid, refuse in cases:
        sol = _dp(inst, sched, grid=grid, refuse_unavailable=refuse)
        n_adm += sum(len(pl.admission_off) for pl in sol.plan)
        if refuse:
            assert abs(sol.objective - (0.25 + 4 * 7.15 / 12)) <= 1e-9, sol.objective
        comp = plan_cost(inst, sched, sol.plan, grid)
        total = sum(comp.values())
        assert _close(total, sol.objective, 1e-9), (total, sol.objective)
        for k in COMPONENTS:
            assert abs(comp[k] - sol.components.get(k, 0.0)) <= 1e-9 * max(1.0, abs(comp[k])), (k, comp, sol.components)
        for pl in sol.plan:
            assert pl.release_slot is None or pl.release_slot > pl.start_slot
            assert pl.n == 1 and pl.llm == 0
    assert n_adm > 0


def _mukv_example():
    """The example of §7.1 for item 4 (mu_kv = 2 USD): Delta_s = Delta_f = 5, T_s = 10."""
    cfg = single_site_config(10, 5, [("r1", 5, 5)], {"r1": 3.0}, 6.0, [4, 5, 6, 7, 8, 9], 600.0, 0.0,
                             [0, 0] + [1] * 8, "prepaid_D")
    inst, sched = _build_single(cfg, unlimited=True)
    with_stranding(inst, mu_kv_usd=2.0, mu_fb_usd=0.0)
    return inst, sched


def test_dp_domain_errors():
    toy_lp = toy_instance(sites=["L0", "P"])
    assert dp_domain(toy_lp, trace_schedule(toy_lp)) == []
    _dp(toy_lp, trace_schedule(toy_lp))

    two_clients = toy_config(sites=["L0", "P"])
    two_clients["borrowers"]["clients"].append(explicit_client([1] * 24, borrower="b1"))
    two_clients = build_instance(two_clients)
    two_sites = toy_instance()                                          # L0 and L1 both revocable
    not_onoff = toy_instance({"borrowers.clients.0.demand.values": [0, 0.5, 1, 1, 0.5, 1] * 4}, sites=["L0", "P"])
    small_cap = toy_instance({"lenders.0.capacity_gpus": 3}, sites=["L0", "P"])
    mukv = toy_instance({"stranding.kv_share": 0.5}, sites=["L0", "P"])
    assert mukv.stranding.mu_kv_usd[0] > 0
    ex = _mukv_example()
    cases = {"two_clients": (two_clients, None), "small_capacity": (small_cap, None), "mu_kv": (mukv, None),
             "mu_kv_example": ex, "two_revocable_sites": (two_sites, None), "not_onoff": (not_onoff, None)}
    solvable = ("two_revocable_sites", "not_onoff")
    for name, (inst, sched) in cases.items():
        sched = sched if sched is not None else trace_schedule(inst)
        assert dp_domain(inst, sched) != [], name
        with pytest.raises(DomainError):
            solve_dp(inst, sched)
        if name not in solvable:
            with pytest.raises(DomainError):
                solve_dp(inst, sched, strict=False)
        else:
            r = solve_dp(inst, sched, strict=False)
            assert r.status == 0 and r.status_msg != "", name
            assert r.objective >= _milp(inst, sched) - 1e-6, name
