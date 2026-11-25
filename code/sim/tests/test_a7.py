"""Tests of policy A7, practical Sublet (sublet/algos/a7.py; design/q44_practical_sublet.md §2, §6.3 test_a7.py).

A7 is A6 with the PS settings of §2.1 as its defaults. Oracles: A6 run with those parameters (identical
ledgers), and on the C3-P5 insurance family the revocable-only ratios of code/theory_checks/c3/out/c4_lower.txt
(b) (C3-P5, PROVEN) and the finite-T formula of check_c4_lower.part_b.
"""
from __future__ import annotations

import numpy as np
import pytest

import check_c4_lower
import core
import fam

from fixtures import SIM, c4l_b, load_json, toy_instance

from sublet.algos.a6 import A6
from sublet.algos.a7 import PS_PX, PS_SETTINGS, PracticalSublet
from sublet.algos.common import PolicyError
from sublet.engine import EngineConfig, simulate
from sublet.instance import build_instance, from_core
from sublet.paths import CONFIGS
from sublet.types import LenderModel

C4_LOWER = SIM.parent / "theory_checks" / "c3" / "out" / "c4_lower.txt"


def _sim(inst, pol, model=None, seed=0):
    res = simulate(inst, pol, model or LenderModel(schedule="trace"),
                   EngineConfig(auto_drain=False, check_invariants=True), policy_seed=seed)
    assert not res.invariant_failures, res.invariant_failures[:5]
    return res


def _same_ledger(a, b) -> bool:
    return (a.components == b.components and all(np.array_equal(a.per_slot[k], b.per_slot[k]) for k in a.per_slot)
            and [vars(x) for x in a.leases] == [vars(x) for x in b.leases]
            and [vars(x) for x in a.replicas] == [vars(x) for x in b.replicas])


def _empty(m: int) -> list:
    return [np.zeros(0, dtype=np.int64) for _ in range(m)]


def test_defaults_and_px_merge():
    """§2.1: A7's defaults are A6's with variant 'practical', predictions off, X2 'reference', view transform
    'revocable_only', contract rule P1 only and the five knobs K, R, F, S, O on; every other parameter keeps
    A6's default. A px object is merged onto PS's knobs (leave-one-out rows); px=None turns them off; no
    driver input is needed at the defaults."""
    p = PracticalSublet().params()
    a6 = A6().params()
    assert p["px"] == PS_PX and all(PS_PX.values()) and len(PS_PX) == 5
    for k, v in PS_SETTINGS.items():
        assert p[k] == v, k
    for k in set(a6) - set(PS_SETTINGS):
        assert p[k] == a6[k], k
    assert PracticalSublet(px={"renew_live": False}).params()["px"] == {**PS_PX, "renew_live": False}
    assert PracticalSublet(px=None).params()["px"] is None
    with pytest.raises(PolicyError):
        PracticalSublet(variant="theory")              # needs N_bound
    with pytest.raises(PolicyError):
        PracticalSublet(px={"x2_surplus": True})       # not an adopted knob (§2.3)


@pytest.mark.parametrize("which", ["ms s3", "toy", "core"])
def test_a7_equals_a6_with_ps_parameters(which):
    """§6.3: A7 equals A6 run with the PS parameters (identical ledgers and reports), on ms2_multi_small (config
    seed 3, policy seeds 0 and 1), the toy and a from_core export of the C3-P5 instance (beta = 14, eager)."""
    if which == "ms s3":
        cfg = load_json(CONFIGS / "ms2_multi_small.json")
        cfg["seed"] = 3
        inst, model, seeds = build_instance(cfg), LenderModel(schedule="trace"), (0, 1)
    elif which == "toy":
        inst, model, seeds = toy_instance(), LenderModel(schedule="trace"), (0,)
    else:
        I, _ = c4l_b(14)
        inst, model, seeds = from_core(I, _empty(I.m))[0], LenderModel(schedule="eager"), (0,)
    for s in seeds:
        a = _sim(inst, PracticalSublet(), model, s)
        b = _sim(inst, A6(**PS_SETTINGS), model, s)
        assert _same_ledger(a, b), (which, s)
        ra, rb = a.metrics["policy"], b.metrics["policy"]
        assert ra["policy"] == "A7" and ra["px"]["knobs"] == rb["px"]["knobs"] == PS_PX
        for key in ("cost_pr", "cost_an", "P", "opened", "realized", "exec", "px"):
            assert ra[key] == rb[key], (which, s, key)


def _c4_lower_b() -> dict:
    """{beta: 'revonly/OPT' string} of c4_lower.txt part (b)."""
    rows, on = {}, False
    for line in C4_LOWER.read_text().splitlines():
        if line.startswith("(b)"):
            on = True
            continue
        if on and line.startswith("("):
            break
        parts = line.split()
        if on and parts and parts[0].isdigit():
            rows[int(parts[0])] = parts[2]
    return rows


def test_c3p5_family_revocable_only_ratios():
    """§6.3 (§2.4, core families): on the C3-P5 insurance family (check_c4_lower.single(T, [(1, 1), (T, 0)], beta,
    [1.0, 1.3]), eager lender, from_core export, policy seed 0) A7's engine cost over core.opt_eager of the full
    menu reproduces the revocable-only ratios 1.491, 2.807, 5.026, 8.312 of c4_lower.txt (b) for beta = 2, 6,
    14, 30 at T = 48; its cost equals OPT_eager of the revocable-only instance (to 1e-9), with no protected
    lease; at T = 192, beta = 14, 30 the ratio equals the finite-T formula (T / 2) (beta + 2) / (beta + 1.3 T)
    of check_c4_lower.part_b (5.827, 10.987; the limit a_1 rho_1 / a_2 is 6.154 and 12.308)."""
    ref = _c4_lower_b()
    assert sorted(ref) == [2, 6, 14, 30]
    assert [ref[b] for b in (2, 6, 14, 30)] == ["1.491", "2.807", "5.026", "8.312"]
    for T, betas in ((48, (2, 6, 14, 30)), (192, (14, 30))):
        for beta in betas:
            I = check_c4_lower.single(T, [(1, 1), (T, 0)], beta, [1.0, 1.3])
            full = core.opt_eager(I)["fun"]
            rev = core.opt_eager(I.subset(contracts=[0]))["fun"]
            inst, _ = from_core(I, _empty(I.m))
            res = _sim(inst, PracticalSublet(), LenderModel(schedule="eager"))
            tot = res.components["total"]
            assert all(L.contract == 0 for L in res.leases), (T, beta)
            assert abs(tot - rev) <= 1e-9 * max(1.0, rev), (T, beta, tot, rev)
            if T == 48:
                assert f"{tot / full:.3f}" == ref[beta], (beta, tot / full, ref[beta])
            else:
                f_T = (T / 2) * (beta + 2) / (beta + 1.3 * T)
                assert abs(tot / full - f_T) <= 1e-9 * f_T, (T, beta, tot / full, f_T)


def test_cat_and_mouse_above_lower_bound():
    """Bound check (no fixed values): on the cat-and-mouse family (check_c4_lower.cm_instance(4, rho),
    rho = 4, 8, 16, C3-T4's adaptive lender, from_core export) A7's engine cost over fam.opt_dp on the run's
    realized schedule is at least LB_T of c4_lower.txt (a) (2.000, 2.462, 2.783), as for every online policy."""
    lb = {}
    on = False
    for line in C4_LOWER.read_text().splitlines():
        if line.startswith("(a)"):
            on = True
            continue
        if on and line.startswith("("):
            break
        parts = line.split()
        if on and parts and parts[0].isdigit() and int(parts[0]) == 4:
            lb[int(parts[1])] = float(parts[2])
    assert lb[4] == 2.0 and lb[8] == 2.462 and lb[16] == 2.783
    for rho in (4, 8, 16):
        I = check_c4_lower.cm_instance(4, rho)
        F = fam.Fam(4, rho, int(I.tau[0]), int(I.H[0]), I.T)
        inst, _ = from_core(I, _empty(I.m))
        res = _sim(inst, PracticalSublet(), LenderModel(schedule="adaptive"))
        opt = fam.opt_dp(F, [np.asarray(x, dtype=np.int64) for x in res.schedule.R])[0]
        assert res.components["total"] / opt >= lb[rho] - 5e-4, (rho, res.components["total"] / opt, lb[rho])
