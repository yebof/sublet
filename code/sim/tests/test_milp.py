"""Tests of sublet/opt/milp.py (design/sim_spec.md §3.8, §8; §9.2)."""
import numpy as np
import pytest

import check_c3_benchmark
import core
import fam

from fixtures import (CONFIGS, _build_single, c3b_case, c4l_b, c4l_d, c4l_e, core_case, explicit_client,
                      explicit_llm, fam_case, full_variant, load_json, random_toy_config, single_site_config,
                      toy_config, toy_instance, trace_schedule, with_capacity, with_stranding)

from sublet import reclaim
from sublet.engine import simulate
from sublet.instance import build_instance, from_core
from sublet.opt import milp as milp_mod
from sublet.opt.milp import SizeError, estimate_size, solve_core, solve_eager, solve_lp, solve_opt
from sublet.paths import C3
from sublet.policies import FixedPlan
from sublet.types import INF, Schedule

C3B = load_json(C3 / "out" / "c3_benchmark.json")
C4 = load_json(C3 / "out" / "c4_lower.json")
SIZE_KEYS = ("n_vars", "n_int", "n_rows", "nnz")


def _close(a, b, tol):
    return abs(a - b) <= tol * max(1.0, abs(b))


def _ok(r):
    assert r.status == 0 and r.objective is not None, (r.method, r.status, r.status_msg)
    return r.objective


def _core(I, om, integral=True):
    return _ok(solve_core(I, om, integral=integral, mip_rel_gap=1e-9))


def _opt(inst, sched, **kw):
    return _ok(solve_opt(inst, sched, mip_rel_gap=1e-9, **kw))


def _all(I):
    return [np.arange(I.T)] * I.m


def _none(I):
    return [np.zeros(0, dtype=np.int64)] * I.m


def _accepted(ref):
    """§9.1 acceptance rule for a reference core.opt_omega / opt_eager value."""
    return ref["status"] == 0 and ref["fun"] - ref["lb"] <= 1e-9 * max(1.0, abs(ref["fun"]))


def _in_bracket(x, ref, tol):
    lo, hi = ref["lb"], ref["fun"]
    return lo - tol * max(1.0, abs(lo)) <= x <= hi + tol * max(1.0, abs(hi))


# ---------------------------------------------------------------- case generators
CORE_RATES = (0.0, 0.05, 0.2, 1.0)


def core_cases():
    for seed in range(20):
        for rate in CORE_RATES:
            yield seed, rate, core_case(seed, rate)


def family_cases():
    for m in (2, 3, 5):
        for rho in (2, 8):
            for (tau, H) in ((1, 0), (2, 1)):
                for sched in ("bern0.02", "bern0.2", "safe", "iid0.5"):
                    for seed in range(3):
                        yield (m, rho, tau, H, sched, seed), fam_case(m, rho, tau, H, 48, sched, seed)


def _capacitated_two_llm(seed):
    """One site of 1 GPU, two LLMs (g = 1), contract tau = 1 slot, H = 2 min (D = 7 min), random R."""
    rng = np.random.default_rng([seed, 41])
    cfg = toy_config(sites=["L0"])
    cfg["contracts"] = [{"id": "c", "tau_min": 5, "H_min": 2}]
    cfg["lenders"][0].update({"menu": ["c"], "prices": {"c": 3.0}, "capacity_gpus": 1,
                              "R": [int(x) for x in np.flatnonzero(rng.random(24) < 0.3)],
                              "lam_s": float(rng.choice([0.0, 300.0]))})
    cfg["llms"] = [explicit_llm("j1", 1), explicit_llm("j2", 1)]
    d1 = (rng.random(24) < 0.6).astype(float)
    d2 = np.where(d1 > 0, 0.0, (rng.random(24) < 0.8).astype(float))
    cfg["borrowers"]["clients"] = [explicit_client(d1, "j1"), explicit_client(d2, "j2", borrower="b1")]
    inst = build_instance(cfg)
    return inst, trace_schedule(inst)


def toy_slow_variants():
    """Toy variants whose deaths under omega_all fall on decision slots (slow grid, or fast grid with
    every H a multiple of Delta_s), with the grid to solve on."""
    toy = toy_instance()
    out = [(toy, trace_schedule(toy), "slow")]
    for seed in range(4):
        rng = np.random.default_rng([seed, 17])
        inst = build_instance(random_toy_config(rng, fast_min=5))
        with_stranding(inst, mu_fb_usd=float(rng.uniform(0, 1)), mu_kv_usd=float(rng.uniform(0, 0.3)))
        out.append((inst, trace_schedule(inst), "slow"))
    for seed in range(2):
        rng = np.random.default_rng([seed, 18])
        inst = build_instance(random_toy_config(rng, fast_min=1, n_clients=1))
        out.append((inst, trace_schedule(inst), "fast"))
    for seed in range(4):
        inst, sched = _capacitated_two_llm(seed)
        out.append((inst, sched, "slow"))
    return out


def _fast_example(billing, demand, T_s=2):
    """§8.4 / §9.2: Delta_s = 5, Delta_f = 1, one site of unlimited capacity, contract tau = 1 slot,
    H = 2 min, 6 USD/GPU-h, q = 60 USD per replica-load-hour, lambda = 0, delta = 0, R empty."""
    cfg = toy_config(sites=["L0"])
    cfg["time"] = {"slow_slot_min": 5, "fast_slot_min": 1, "horizon_min": 5 * T_s, "start_minute_of_week": 0}
    cfg["billing"] = billing
    cfg["prices"]["q_gpu_usd_per_gpu_h"] = 60.0
    cfg["contracts"] = [{"id": "c", "tau_min": 5, "H_min": 2}]
    cfg["lenders"][0].update({"menu": ["c"], "prices": {"c": 6.0}, "R": [], "lam_s": 0.0})
    cfg["borrowers"]["clients"] = [explicit_client(demand)]
    cfg["stranding"]["mu_over_beta_tilde"] = 0.0
    inst = with_capacity(build_instance(cfg), {0: INF})
    return inst, trace_schedule(inst)


def _slowlb_fixed():
    """§8.6: T_s = 4, one site with R = {1} and refuse_unavailable, tau = 2 slots, H = 0, per_slot,
    2.85 USD/GPU-h, lambda = 420 s, demand 0 in minutes 0-6 and 1 in minutes 7-19: fine optimum 0.95."""
    cfg = toy_config(sites=["L0"])
    cfg["time"] = {"slow_slot_min": 5, "fast_slot_min": 1, "horizon_min": 20, "start_minute_of_week": 0}
    cfg["billing"] = "per_slot"
    cfg["contracts"] = [{"id": "c", "tau_min": 10, "H_min": 0}]
    cfg["lenders"][0].update({"menu": ["c"], "prices": {"c": 2.85}, "R": [1], "lam_s": 420.0})
    cfg["borrowers"]["clients"] = [explicit_client([0] * 7 + [1] * 13)]
    cfg["stranding"]["mu_over_beta_tilde"] = 0.0
    inst = with_capacity(build_instance(cfg), {0: INF})
    return inst, trace_schedule(inst)


def slowlb_variants():
    """(inst, sched, refuse_unavailable): 10 toy variants with Delta_s = 5, Delta_f = 1, and 6 more
    whose contracts have H in {2, 7, 12} min (fine deaths and, under prepaid_D, billed terms not a
    multiple of the slow slot, so that the partial-slot rules of §8.6 apply)."""
    out = []
    for i in range(10):
        rng = np.random.default_rng([i, 23])
        lam = 420.0 if i < 4 else None
        billing = "per_slot" if i % 2 == 0 else None
        inst = build_instance(random_toy_config(rng, fast_min=1, lam=lam, billing=billing))
        if i % 3 == 0:
            with_stranding(inst, mu_fb_usd=0.5)
        out.append((inst, trace_schedule(inst), i % 2 == 1))
    for i in range(6):
        rng = np.random.default_rng([i, 24])
        cfg = random_toy_config(rng, fast_min=1, billing=("prepaid_D", "per_slot", "commit_tau")[i % 3],
                                lam=float(rng.choice([0.0, 120.0, 300.0, 420.0])))
        cfg["contracts"][0]["H_min"] = int(rng.choice([2, 7]))
        cfg["contracts"][1]["H_min"] = int(rng.choice([2, 7, 12]))
        inst = build_instance(cfg)
        out.append((inst, trace_schedule(inst), i % 2 == 1))
    return out


def _one_site_fast(T_s, R, demand, billing="prepaid_D", H=2, tau_min=5, price=6.0, lam=0.0):
    """Delta_s = 5, Delta_f = 1, one site of unlimited capacity, g = 1, q = 60 USD per
    replica-load-hour, delta = beta = 0, no stranding (the setting of the §8.4 example)."""
    cfg = toy_config(sites=["L0"])
    cfg["time"] = {"slow_slot_min": 5, "fast_slot_min": 1, "horizon_min": 5 * T_s, "start_minute_of_week": 0}
    cfg["billing"] = billing
    cfg["prices"]["q_gpu_usd_per_gpu_h"] = 60.0
    cfg["contracts"] = [{"id": "c", "tau_min": tau_min, "H_min": H}]
    cfg["lenders"][0].update({"menu": ["c"], "prices": {"c": price}, "R": list(R), "lam_s": lam})
    cfg["borrowers"]["clients"] = [explicit_client(demand)]
    cfg["stranding"]["mu_over_beta_tilde"] = 0.0
    inst = with_capacity(build_instance(cfg), {0: INF})
    return inst, trace_schedule(inst)


def _capacitated_h2_toy():
    inst = toy_instance({"contracts.0.H_min": 2})
    return inst, trace_schedule(inst)


# ---------------------------------------------------------------- tests
def test_core_mode_equals_opt_omega():
    """Proposition M1: solve_core = core.opt_omega (1e-6), with the acceptance rule of §9.1."""
    n = skipped = 0
    for seed, rate, (I, om) in core_cases():
        n += 1
        ref = core.opt_omega(I, om)
        if not _accepted(ref):
            skipped += 1
            continue
        got = _core(I, om)
        assert _in_bracket(got, ref, 1e-6), (seed, rate, got, ref)
    assert n == 80 and skipped <= 0.1 * n, (skipped, n)


def test_core_eager_equals_opt_eager():
    """Corollary M2: solve_core(I, omega_all) = core.opt_eager (1e-6)."""
    n = skipped = 0
    for seed in range(20):
        I, _ = core_case(seed, 1.0)
        n += 1
        ref = core.opt_eager(I)
        if not _accepted(ref):
            skipped += 1
            continue
        assert _in_bracket(_core(I, _all(I)), ref, 1e-6), seed
    assert skipped <= 0.1 * n


@pytest.mark.parametrize("part", ["a", pytest.param("b", marks=pytest.mark.slow)])
def test_c3_benchmark_values(part):
    """(a) check_c3_benchmark.single_site: OPT_eager and OPT_none of c3_benchmark.json 'a';
    (b) OPT_omega of 'b[*].per_rate[*]' on the c3b_case instances (1e-6)."""
    if part == "a":
        assert len(C3B["a"]) == 5
        for row in C3B["a"]:
            beta = (row["rho"] - 1) * 3
            I = check_c3_benchmark.single_site(beta)
            assert _close(_core(I, _all(I)), row["OPT_eager"], 1e-6), row
            assert _close(_core(I, _none(I)), row["OPT_none"], 1e-6), row
            inst, _ = from_core(I, _none(I))
            assert _close(_ok(solve_eager(inst, mip_rel_gap=1e-9)), row["OPT_eager"], 1e-6), row
            assert _close(_opt(inst, Schedule("trace", tuple(_none(I)))), row["OPT_none"], 1e-6), row
    else:
        assert len(C3B["b"]) == 10
        for b in C3B["b"]:
            for pr in b["per_rate"]:
                I, om = c3b_case(b["seed"], pr["rate"])
                assert _close(_core(I, om), pr["OPT_omega"], 1e-6), (b["seed"], pr["rate"])


def test_c4_lower_offline():
    """c4_lower.json (b) revocable-only / full-menu OPT, (d) siloed / shared OPT, (e) eager MILP (1e-6)."""
    assert [r["beta"] for r in C4["b"]] == [2, 6, 14, 30]
    for row in C4["b"]:
        full, rev = c4l_b(row["beta"])
        assert _close(_core(rev, _all(rev)) / _core(full, _all(full)), row["ratio"], 1e-6), row
    assert [r["b"] for r in C4["d"]] == [1, 2, 4, 8, 16]
    for row in C4["d"]:
        I = c4l_d(row["b"])
        shared = _core(I, _all(I))
        silo = sum(_core(I.subset(clients=[c]), _all(I)) for c in range(row["b"]))
        assert _close(silo / shared, row["ratio"], 1e-6), row
    for seed in range(20):
        I = c4l_e(seed)
        assert C4["e"][seed]["seed"] == seed
        want = C4["e"][seed]["milp"]
        assert _close(_core(I, _all(I)), want, 1e-6), seed
        inst, _ = from_core(I, _all(I))
        assert _close(_ok(solve_eager(inst, mip_rel_gap=1e-9)), want, 1e-6), seed


def test_family_equals_fam_opt_dp():
    """T4/O1 family (m in {2, 3, 5}): solve_core and solve_opt(from_core(...)) equal fam.opt_dp (1e-6)."""
    n = 0
    for key, (F, om) in family_cases():
        want = fam.opt_dp(F, om)[0]
        I = F.core_instance()
        assert _close(_core(I, om), want, 1e-6), (key, "core")
        inst, sched = from_core(I, om)
        assert _close(_opt(inst, sched), want, 1e-6), (key, "full")
        n += 1
    assert n == 144


def test_full_mode_reduces_to_core():
    """Claim M3: on from_core instances solve_opt equals solve_core (1e-6)."""
    for seed in range(10):
        for rate in (0.0, 0.2, 1.0):
            I, om = core_case(seed, rate)
            inst, sched = from_core(I, om)
            assert _close(_opt(inst, sched), _core(I, om), 1e-6), (seed, rate)


def test_eager_ge_omega():
    """solve_eager >= solve_opt where every death under omega_all falls on a decision slot (-1e-6);
    the fast-grid example of §8.4: solve_eager 0.7 USD, solve_opt with omega empty 1.0 USD (1e-9)."""
    for inst, sched, grid in toy_slow_variants():
        e = _ok(solve_eager(inst, grid=grid, mip_rel_gap=1e-9))
        o = _opt(inst, sched, grid=grid)
        assert e >= o - 1e-6 * max(1.0, abs(o)), (inst.name, grid, e, o)
    for billing in ("prepaid_D", "per_slot"):
        inst, sched = _fast_example(billing, [1] * 7 + [0] * 3)
        assert len(sched.R[0]) == 0
        e = _ok(solve_eager(inst, grid="fast", mip_rel_gap=1e-9))
        o = _opt(inst, sched, grid="fast")
        assert abs(e - 0.7) <= 1e-9 and abs(o - 1.0) <= 1e-9, (billing, e, o)


def _all_milp_cases():
    """Every MILP test instance of this file, as (label, solve function of integral)."""
    cases = []
    for seed, rate, (I, om) in core_cases():
        cases.append((f"core {seed} {rate}", lambda integral, I=I, om=om:
                      solve_core(I, om, integral=integral, mip_rel_gap=1e-9)))
        if seed < 10 and rate in (0.0, 0.2, 1.0):
            inst, sched = from_core(I, om)
            cases.append((f"full {seed} {rate}", lambda integral, i=inst, s=sched:
                          solve_opt(i, s, integral=integral, mip_rel_gap=1e-9)))
    for seed in range(20):
        I = c4l_e(seed)
        cases.append((f"c4e {seed}", lambda integral, I=I: solve_core(I, _all(I), integral=integral)))
    for key, (F, om) in family_cases():
        I = F.core_instance()
        cases.append((f"fam {key}", lambda integral, I=I, om=om: solve_core(I, om, integral=integral)))
        inst, sched = from_core(I, om)
        cases.append((f"fam full {key}", lambda integral, i=inst, s=sched: solve_opt(i, s, integral=integral)))
    for row in C3B["a"]:
        I = check_c3_benchmark.single_site((row["rho"] - 1) * 3)
        cases.append((f"c3a {row['rho']}", lambda integral, I=I: solve_core(I, _none(I), integral=integral)))
    for n, (inst, sched, grid) in enumerate(toy_slow_variants()):
        cases.append((f"toy {n}", lambda integral, i=inst, s=sched, g=grid:
                      solve_opt(i, s, grid=g, integral=integral, mip_rel_gap=1e-9)))
        cases.append((f"toy eager {n}", lambda integral, i=inst, g=grid:
                      solve_eager(i, grid=g, integral=integral, mip_rel_gap=1e-9)))
    for n, (inst, sched, refuse) in enumerate(slowlb_variants()):
        for grid in ("fast", "slow_lb"):
            cases.append((f"slowlb {n} {grid}", lambda integral, i=inst, s=sched, g=grid, r=refuse:
                          solve_opt(i, s, grid=g, refuse_unavailable=r, integral=integral, mip_rel_gap=1e-9)))
    for i in range(10):
        inst, sched = full_variant(i)
        cases.append((f"fullvar {i}", lambda integral, i_=inst, s=sched:
                      solve_opt(i_, s, integral=integral, mip_rel_gap=1e-9)))
    inst, sched = _capacitated_h2_toy()
    cases.append(("toy H=2", lambda integral, i=inst, s=sched: solve_opt(i, s, integral=integral, mip_rel_gap=1e-9)))
    return cases


@pytest.mark.slow
def test_lp_le_milp():
    """LP <= MILP (+1e-9) on the MILP test instances of this file."""
    for label, solve in _all_milp_cases():
        m = _ok(solve(True))
        lp = _ok(solve(False))
        assert lp <= m + 1e-9 * max(1.0, abs(m)), (label, lp, m)


def test_slow_lb_le_fast():
    """Claim M5: MILP and LP on 'slow_lb' are at most those on 'fast' (+1e-9); the fixed case of §8.6."""
    for n, (inst, sched, refuse) in enumerate(slowlb_variants()):
        kw = dict(refuse_unavailable=refuse, mip_rel_gap=1e-9)
        for integral in (True, False):
            fast = _ok(solve_opt(inst, sched, grid="fast", integral=integral, **kw))
            lb = _ok(solve_opt(inst, sched, grid="slow_lb", integral=integral, **kw))
            assert lb <= fast + 1e-9 * max(1.0, abs(fast)), (n, integral, lb, fast)
    inst, sched = _slowlb_fixed()
    kw = dict(refuse_unavailable=True, mip_rel_gap=1e-9)
    fine = _ok(solve_opt(inst, sched, grid="fast", **kw))
    assert abs(fine - 0.95) <= 1e-9, fine
    # slow_lb by hand: Lambda-bar = floor(7/5) = 1 = A-bar (P = 0), the lease from slot 0 is charged
    # r_f * |{f in [0, 7): f < 5}| = 5 * 2.85/60 and pool slots 1-3 at 5 r_f each: 0.95, serving slots 2-3
    assert abs(_ok(solve_opt(inst, sched, grid="slow_lb", **kw)) - 0.95) <= 1e-9
    lp_fast = _ok(solve_lp(inst, sched, grid="fast", **kw))
    assert _ok(solve_lp(inst, sched, grid="slow_lb", **kw)) <= lp_fast + 1e-9


def test_slow_lb_hand():
    """slow_lb hand values (§8.6) on one site of unlimited capacity (Delta_s = 5, Delta_f = 1, tau 1 slot,
    H = 2 min, prepaid_D so P = 7 min, 6 USD/GPU-h, q = 60, lambda = 0), T_s = 3 (1e-9):
    (h1) R = {2}, demand 1 in every minute: fine optimum 1.7 (lease A from 0 dies at minute 12, B bought at
    slot 2 is never announced; A released at slot 2 pays rent in minutes 7-9: 0.7 + 0.3 + 0.7); slow_lb 0.7
    (A covers slots 0-1 in its hold region, A-bar = ceil(7/5) = 2, and slot 2 as a pool slot of rent
    coefficient 0, since A's fine death 12 is not a multiple of 5);
    (h3) R empty, demand 1 only in minutes 12-14: the slot-2 minimum is 0, so slow_lb = 0; fine 0.7."""
    kw = dict(mip_rel_gap=1e-9)
    inst, sched = _one_site_fast(3, [2], [1.0] * 15)
    assert abs(_ok(solve_opt(inst, sched, grid="fast", **kw)) - 1.7) <= 1e-9
    assert abs(_ok(solve_opt(inst, sched, grid="slow_lb", **kw)) - 0.7) <= 1e-9
    assert _ok(solve_lp(inst, sched, grid="slow_lb")) <= 0.7 + 1e-9
    # the same with a site of 1 GPU (hold pools): A is released at slot 2 when B is bought there
    with_capacity(inst, {0: 1})
    r = solve_opt(inst, sched, grid="slow_lb", **kw)
    assert r.size["parts"]["N_hp"] > 0 and abs(_ok(r) - 0.7) <= 1e-9
    assert abs(_ok(solve_opt(inst, sched, grid="fast", **kw)) - 1.7) <= 1e-9
    inst, sched = _one_site_fast(3, [], [0.0] * 12 + [1.0] * 3)
    assert abs(_ok(solve_opt(inst, sched, grid="fast", **kw)) - 0.7) <= 1e-9
    assert abs(_ok(solve_opt(inst, sched, grid="slow_lb", **kw))) <= 1e-9


def _mukv_case(demand, mu_kv, mu_fb):
    """The example of §7.1 (item 4): revocable site (3.0 USD/GPU-h, tau 1 slot, H 5 min, prepaid_D,
    lambda 600 s, R = {4, ..., 9}) and protected site (6.0, prepaid 5 min, lambda 0), Delta_s = Delta_f
    = 5, T_s = 10, g = 1, q = 7.15, delta = beta = 0, unlimited capacity, the given mu_kv and mu_fb."""
    cfg = single_site_config(10, 5, [("r1", 5, 5)], {"r1": 3.0}, 6.0, [4, 5, 6, 7, 8, 9], 600.0, 0.0, demand,
                             "prepaid_D")
    inst, sched = _build_single(cfg, unlimited=True)
    with_stranding(inst, mu_kv_usd=mu_kv, mu_fb_usd=mu_fb)
    return inst, sched


def test_stranding_hand():
    """(C5)-(C6) by hand (1e-9). The revocable lease from slot 0 is warm in slots 2-4 and dies at minute
    25: prepaid 0.5 + rent 3 x 0.25; the protected lease costs 0.5 per slot; fallback 7.15 d / 12 per slot.
    (a) §7.1 with mu_kv = 2: moving the load to P at slot 5 costs 2, so P from slot 2: 4.0;
    (b) mu_kv = 0.1, mu_fb = 0.5: revocable from 0, P from 5 (warm at once), y = 1 at slot 5, w = 0:
        1.25 + 2.5 + 0.1 = 3.85;
    (c) mu_kv = 0.1, mu_fb = 0, demand 0.6 from slot 5: fallback (0.3575 per slot) beats P (0.5), the move
        at slot 5 has d_hat = min(1, 0.6) = 0.6: 1.25 + 5 x 0.3575 + 0.1 x 0.6 = 3.0975."""
    demand = [0, 0] + [1] * 8
    assert abs(_opt(*_mukv_case(demand, 2.0, 0.0)) - 4.0) <= 1e-9
    r = solve_opt(*_mukv_case(demand, 0.1, 0.5), mip_rel_gap=1e-9)
    assert abs(_ok(r) - 3.85) <= 1e-9
    assert abs(r.components["stranding_kv"] - 0.1) <= 1e-9 and abs(r.components["stranding_fb"]) <= 1e-9
    r = solve_opt(*_mukv_case([0, 0, 1, 1, 1] + [0.6] * 5, 0.1, 0.0), mip_rel_gap=1e-9)
    assert abs(_ok(r) - 3.0975) <= 1e-9
    assert abs(r.components["stranding_kv"] - 0.06) <= 1e-9


def test_eager_refuse_sched_hand():
    """solve_eager with the refusal sets of a 'refuse' run (§8.4), by hand (1e-9): revocable site
    (tau 1 slot, H 5 min, prepaid_D so D = 10 min, 3.0 USD/GPU-h: 0.5 per lease) and protected site
    (6.0, prepaid 5 min: 0.5 per slot), lambda 0, demand 1 in T_s = 4 slots, fallback 0.596 per slot.
    Under omega_all every revocable lease lives exactly 2 slots: leases at 0 and 2 give 1.0. With
    the trace schedule R = {1, 2} as refusal sets the revocable starts are 0 and 3: the lease at 0 and
    P over slots 2-3 (or P at 2 and a lease at 3) give 1.5."""
    cfg = single_site_config(4, 5, [("r1", 5, 5)], {"r1": 3.0}, 6.0, [1, 2], 0.0, 0.0, [1, 1, 1, 1], "prepaid_D")
    inst, sched = _build_single(cfg, unlimited=True, mu_fb=0.0)
    assert abs(_ok(solve_eager(inst, mip_rel_gap=1e-9)) - 1.0) <= 1e-9
    assert abs(_ok(solve_eager(inst, refuse_sched=sched, mip_rel_gap=1e-9)) - 1.5) <= 1e-9
    assert abs(_ok(solve_eager(inst, refuse_sched=sched, integral=False)) - 1.5) <= 1e-9


def test_hold_pool_fifo_hand():
    """Hold pools (module docstring of opt/milp.py) by hand: one site of 2 GPUs, contract tau 1 slot,
    H 10 min, prepaid_D (P = 15 min = 3 slots: 1.5 USD per lease at 6 USD/GPU-h, then 0.5 per slot),
    lambda 0, R empty, q = 60 (5 USD per slot of load 1), demand (1, 1, 2, 1, 1, 0). Lease a from 0 and
    lease b from 2 share one cohort; at slot 3 a becomes rent-bearing while b is still in its billed
    term, so the optimum releases a at slot 3 (the earliest start, FIFO) and b at slot 5, where its
    rent would start: 3.0 (releasing b at slot 3 instead would cost 4.0). The plan replays at its
    objective (1e-9)."""
    cfg = toy_config(sites=["L0"])
    cfg["time"] = {"slow_slot_min": 5, "fast_slot_min": 5, "horizon_min": 30, "start_minute_of_week": 0}
    cfg["prices"]["q_gpu_usd_per_gpu_h"] = 60.0
    cfg["contracts"] = [{"id": "c", "tau_min": 5, "H_min": 10}]
    cfg["lenders"][0].update({"menu": ["c"], "prices": {"c": 6.0}, "R": [], "lam_s": 0.0, "capacity_gpus": 2})
    cfg["borrowers"]["clients"] = [explicit_client([1, 1, 2, 1, 1, 0])]
    cfg["stranding"]["mu_over_beta_tilde"] = 0.0
    inst = build_instance(cfg)
    sched = trace_schedule(inst)
    r = solve_opt(inst, sched, mip_rel_gap=1e-9)
    assert abs(_ok(r) - 3.0) <= 1e-9, r.components
    assert r.size["parts"]["N_hp"] > 0 and r.size["parts"]["N_rho"] > 0
    assert sorted((pl.start_slot, pl.release_slot) for pl in r.plan) == [(0, 3), (2, 5)]
    assert abs(_ok(solve_lp(inst, sched)) - 3.0) <= 1e-9
    res = simulate(inst, FixedPlan(r.plan))
    assert res.invariant_failures == [] and abs(res.components["total"] - 3.0) <= 1e-9


def test_size_estimate_exact():
    """estimate_size counts equal the built model's counts (exact)."""
    fast_toy = build_instance(random_toy_config(np.random.default_rng(2), fast_min=1))
    cases = [(*_capacitated_h2_toy(), "slow"), (fast_toy, trace_schedule(fast_toy), "fast")]
    toy = toy_instance()
    cases.insert(0, (toy, trace_schedule(toy), "slow"))
    fc, fs = from_core(*core_case(0, 0.2))
    cases.append((fc, fs, "slow"))
    for inst, sched, grid in cases:
        est = estimate_size(inst, sched, grid=grid)
        assert {"n_vars", "n_int", "n_rows", "nnz", "est_mb", "parts"} <= set(est)
        r = solve_opt(inst, sched, grid=grid, mip_rel_gap=1e-9)
        assert r.status == 0
        for k in SIZE_KEYS:
            assert est[k] == r.size[k], (inst.name, grid, k, est[k], r.size[k])


def test_size_error():
    """§8.9: SizeError iff n_vars > max_vars (the boundary max_vars = n_vars solves), unless allow_large."""
    toy = toy_instance()
    sched = trace_schedule(toy)
    with pytest.raises(SizeError):
        solve_opt(toy, sched, max_vars=10)
    assert solve_opt(toy, sched, max_vars=10, allow_large=True).status == 0
    n = estimate_size(toy, sched)["n_vars"]
    n_eager = estimate_size(toy, Schedule.eager(toy))["n_vars"]
    for f, nv in ((lambda **kw: solve_opt(toy, sched, **kw), n), (lambda **kw: solve_lp(toy, sched, **kw), n),
                  (lambda **kw: solve_eager(toy, **kw), n_eager)):
        assert f(max_vars=nv).status == 0
        with pytest.raises(SizeError, match="max_vars"):
            f(max_vars=nv - 1)


def test_memory_gate():
    """§8.9, §10 S36: est_mb = 400 + 2.7e-3 nnz (MILP and OPT_eager), parts['est_mb_lp'] = 130 + 5.4e-4 nnz
    (LP). solve_opt and solve_eager raise SizeError when est_mb > mem_budget_mb, solve_lp when est_mb_lp >
    mem_budget_mb, unless allow_large; the n_vars gate holds for all three. On the toy est_mb_lp < 200 <
    400 <= est_mb, so a budget of 200 MB stops the MILP and OPT_eager but not the LP."""
    toy = toy_instance()
    sched = trace_schedule(toy)
    est = estimate_size(toy, sched)
    nnz = est["nnz"]
    assert est["est_mb"] == 400.0 + 2.7e-3 * nnz and est["parts"]["est_mb_milp"] == est["est_mb"]
    assert est["parts"]["est_mb_lp"] == 130.0 + 5.4e-4 * nnz
    assert est["parts"]["est_mb_lp"] < 200.0 < 400.0 <= est["est_mb"]
    eager_est = estimate_size(toy, Schedule.eager(toy))
    assert eager_est["est_mb"] > 200.0
    with pytest.raises(SizeError, match="mem_budget_mb"):
        solve_opt(toy, sched, mem_budget_mb=200.0)
    with pytest.raises(SizeError, match="mem_budget_mb"):
        solve_eager(toy, mem_budget_mb=200.0)
    assert solve_lp(toy, sched, mem_budget_mb=200.0).status == 0
    with pytest.raises(SizeError, match=r"\(LP rule"):
        solve_lp(toy, sched, mem_budget_mb=100.0)
    for f in (lambda **kw: solve_opt(toy, sched, **kw), lambda **kw: solve_eager(toy, **kw),
              lambda **kw: solve_lp(toy, sched, **kw)):
        assert f(mem_budget_mb=100.0, allow_large=True).status == 0
        with pytest.raises(SizeError, match="max_vars"):
            f(max_vars=10)
    assert solve_opt(toy, sched).status == 0          # default budget 2500 MB
    # boundaries: a budget equal to the estimate solves, one 1e-6 MB below raises (MILP, OPT_eager, LP)
    for f, mb in ((lambda **kw: solve_opt(toy, sched, **kw), est["est_mb"]),
                  (lambda **kw: solve_eager(toy, **kw), eager_est["est_mb"]),
                  (lambda **kw: solve_lp(toy, sched, **kw), est["parts"]["est_mb_lp"])):
        assert f(mem_budget_mb=mb).status == 0
        with pytest.raises(SizeError, match="mem_budget_mb"):
            f(mem_budget_mb=mb - 1e-6)


def test_memory_rule_covers_benchmark():
    """§10 S36: the estimate rules lie at or above every measured case of code/sim/out/mem_bench (status
    ok): LP cases against 130 + 5.4e-4 nnz, MILP and OPT_eager cases against 400 + 2.7e-3 nnz."""
    import glob
    import json
    from sublet.paths import SIM_OUT
    files = sorted(glob.glob(str(SIM_OUT / "mem_bench" / "*_*_*d_*.json")))
    cases = [json.load(open(f)) for f in files]
    cases = [c for c in cases if c.get("status") == "ok" and c.get("method") in ("lp", "milp", "eager")]
    if not cases:
        pytest.skip("no measured LP or MILP case in code/sim/out/mem_bench")
    for c in cases:
        nnz, peak = c["built"]["nnz"], c["peak_rss_mb"]
        if c["method"] == "lp":
            rule = milp_mod.EST_LP_MB0 + milp_mod.EST_LP_MB_PER_NNZ * nnz
        else:
            rule = milp_mod.EST_MILP_MB0 + milp_mod.EST_MILP_MB_PER_NNZ * nnz
        assert peak <= rule, (c["id"], peak, rule)


@pytest.mark.needs_a12
def test_time_limit_status():
    """example_1day with time_limit_s = 0.5: status 1 with a reported gap; the incumbent (the
    all-fallback plan if HiGHS has none) is no better than the bound, and the substitutes are noted."""
    inst = build_instance(CONFIGS / "example_1day.json")
    sched = trace_schedule(inst)
    r = solve_opt(inst, sched, time_limit_s=0.5)
    assert r.status == 1, (r.status, r.status_msg)
    assert r.gap is not None and r.objective is not None and r.dual_bound is not None
    assert 0.0 <= r.dual_bound <= r.objective and r.gap > 0, (r.objective, r.dual_bound, r.gap)
    assert abs(r.gap - (r.objective - r.dual_bound) / max(1.0, r.objective)) <= 1e-12
    if "no incumbent" in r.status_msg:
        q = np.array([inst.llms[j].q_usd_per_h for j in inst.clients.llm])
        allfb = float((q[:, None] * inst.clients.demand).sum() * inst.grid.fast_min / 60.0)
        assert abs(r.objective - allfb) <= 1e-9 * allfb and r.plan == []


class _FakeRes:
    def __init__(self, status, x, fun, bound):
        self.status, self.x, self.fun, self.mip_dual_bound = status, x, fun, bound
        self.message = f"stub status {status}"


def test_limit_branches(monkeypatch):
    """The four branches of a MILP stopped at a limit (§8.8), with HiGHS replaced by a stub on the toy:
    an incumbent with a bound, an incumbent with a negative bound (reported as 0, since every cost is
    non-negative), no incumbent with a bound, and no incumbent without a bound (the all-fallback plan,
    7.15 * 16 * 5 / 60 USD, with bound 0)."""
    inst = toy_instance()
    sched = trace_schedule(inst)
    opt = solve_opt(inst, sched, mip_rel_gap=1e-9)
    assert opt.status == 0
    allfb = 7.15 * 16 * 5 / 60
    real = milp_mod.milp
    captured = {}

    def run(status, use_x, bound_total):
        def fake(c, **kw):
            res = real(c, **kw)
            captured["const"] = opt.objective - float(res.fun)
            x = res.x if use_x else None
            b = None if bound_total is None else bound_total - captured["const"]
            return _FakeRes(status, x, None if x is None else float(res.fun), b)
        monkeypatch.setattr(milp_mod, "milp", fake)
        try:
            return solve_opt(inst, sched, mip_rel_gap=1e-9)
        finally:
            monkeypatch.setattr(milp_mod, "milp", real)

    r = run(1, True, 0.5 * opt.objective)
    assert abs(captured["const"] - allfb) <= 1e-9
    assert r.status == 1 and abs(r.objective - opt.objective) <= 1e-9
    assert abs(r.dual_bound - 0.5 * opt.objective) <= 1e-9 and abs(r.gap - 0.5 * opt.objective / opt.objective) <= 1e-9
    assert len(r.plan) == len(opt.plan)
    r = run(1, True, -1.0)
    assert r.dual_bound == 0.0 and "below 0" in r.status_msg and abs(r.gap - 1.0) <= 1e-12
    r = run(1, False, 0.25)
    assert abs(r.objective - allfb) <= 1e-9 and abs(r.dual_bound - 0.25) <= 1e-9 and r.plan == []
    assert "no incumbent" in r.status_msg
    assert r.components["fallback"] == pytest.approx(allfb, rel=1e-12) and r.components["lease_prepaid"] == 0.0
    r = run(1, False, None)
    assert abs(r.objective - allfb) <= 1e-9 and r.dual_bound == 0.0 and abs(r.gap - 1.0) <= 1e-12
    assert "no dual bound" in r.status_msg


def _alive_gpus(inst, sched, plan, t):
    """GPUs per site of the plan's leases alive in the first fast slot of slow slot t (rule T6)."""
    g = inst.grid
    out = np.zeros(inst.m)
    for pl in plan:
        if pl.start_slot > t or (pl.release_slot is not None and pl.release_slot <= t):
            continue
        c = inst.contracts[pl.contract]
        dm = reclaim.death_min(sched.R[pl.site], pl.start_slot, c, g.slow_min)
        if dm is not None and dm < t * g.slow_min + g.fast_min:
            continue
        out[pl.site] += pl.n * inst.llms[pl.llm].g
    return out


def test_plan_extraction_valid():
    """MILP plans: releases only at decision slots after the purchase slot, capacity respected,
    replay feasible (no refused purchase)."""
    cases = [full_variant(i) for i in range(10)] + [_capacitated_h2_toy()]
    for inst, sched in cases:
        r = solve_opt(inst, sched, mip_rel_gap=1e-9)
        assert r.status == 0 and r.plan is not None
        T_s = inst.grid.T_slow
        for pl in r.plan:
            assert pl.n == 1 and 0 <= pl.start_slot < T_s
            assert pl.release_slot is None or (isinstance(pl.release_slot, (int, np.integer))
                                               and pl.start_slot < pl.release_slot < T_s), pl
            assert pl.contract in inst.sites[pl.site].menu
        cap = np.array([s.capacity_gpus for s in inst.sites], dtype=float)
        for t in range(T_s):
            assert np.all(_alive_gpus(inst, sched, r.plan, t) <= cap), t
        res = simulate(inst, FixedPlan(r.plan))
        assert res.invariant_failures == []
        assert not any(e[1] == "refuse" for e in res.events)
        assert len(res.leases) == len(r.plan)
