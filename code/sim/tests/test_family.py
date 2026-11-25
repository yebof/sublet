"""Tests of the T4/O1 family policies RR-renew and marking (sublet/algos/family.py, marking.py;
design/sim_spec_ms2.md §7.6, §8.1, §8.2; exit checks 3g, 3h; R2 of §17.3; §17.2)."""
import json
import math

import numpy as np
import pytest

import fam
import o1_ub

from fixtures import CM_ROWS, CONFIGS, O1_JOBS, O1_T, cm_case, o1_case

from sublet.algos.family import Marking, RRRenew
from sublet.algos.marking import MarkState
from sublet.engine import simulate
from sublet.instance import from_core
from sublet.types import LenderModel

TC = CONFIGS.parents[1] / "theory_checks" / "c3"
O1_JSON = TC / "o1" / "out" / "o1_ub.json"
TOL = 1e-9


def _close(a, b, tol=TOL) -> bool:
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def _o1_rows():
    rows = json.loads(O1_JSON.read_text())
    assert len(rows) == 648
    return rows


def _o1_cases():
    """(row, F, schedule name, omega) for the 648 rows of o1_ub.json, in its order."""
    rows = _o1_rows()
    i = 0
    for job in O1_JOBS:
        F, sch = o1_case(*job)
        for name, om in sch:
            row = rows[i]
            i += 1
            assert (row["m"], row["rho"], row["tau"], row["H"], row["T"], row["sched"]) == job[:4] + (O1_T, name)
            yield row, F, name, om
    assert i == len(rows)


def _empty(m):
    return [np.zeros(0, np.int64) for _ in range(m)]


def test_rr_renew_o1_ub():
    """Check 3g: RRRenew on from_core(F.core_instance(), omega) for the 648 o1_case runs: total / fam.opt_dp
    equals rr, the number of purchases equals NA, and rr_ok recomputed (rr <= min(rho (1 + D/T), 2m + aD/OPT)
    + 1e-9, NA <= m (X + 1), NA <= ceil(T / D)) equals the JSON's; for the 72 adaptiveRR rows the same under
    LenderModel(schedule='adaptive') on from_core(F.core_instance(), [empty] * m), whose realized R equals
    o1_ub.adaptive_rr(F) on [0, 96)."""
    n_adapt = 0
    for row, F, name, om in _o1_cases():
        m = F.m
        tag = (row["m"], row["rho"], row["tau"], row["H"], name)
        if name == "adaptiveRR":
            inst, _ = from_core(F.core_instance(), _empty(m))
            res = simulate(inst, RRRenew(), LenderModel(schedule="adaptive"))
            R = [np.asarray(r, dtype=np.int64) for r in res.schedule.R]
            want = [np.asarray(r, dtype=np.int64) for r in o1_ub.adaptive_rr(F)]
            assert all(np.array_equal(a, b[b < O1_T]) for a, b in zip(R, want)), tag
            assert all(np.array_equal(a, b) for a, b in zip(R, om)), tag
            n_adapt += 1
        else:
            inst, sched = from_core(F.core_instance(), om)
            res = simulate(inst, RRRenew(), LenderModel())
            R = om
        assert res.invariant_failures == [], tag
        opt, X = fam.opt_dp(F, R)
        assert _close(opt, row["opt"]) and X == row["X"], tag
        tot = res.components["total"]
        rr = tot / opt
        NA = len(res.leases)
        assert _close(rr, row["rr"]), (tag, rr, row["rr"])
        assert NA == row["NA"] == res.metrics["policy"]["purchases"], (tag, NA, row["NA"])
        bound = min(F.rho * (1 + F.D / F.T), 2 * m + F.a * F.D / opt)
        ok = bool(rr <= bound + 1e-9 and NA <= m * (X + 1) and NA <= math.ceil(F.T / F.D))
        assert ok == row["rr_ok"], tag
    assert n_adapt == 72


def test_stay_rr_c4_lower_a():
    """R2: RRRenew(stay=True) and RRRenew() on cm_case(m, rho) under the adaptive lender reproduce c4_lower.json
    a[*].stay and a[*].rr; the denominator is fam.opt_dp(Fam(m, rho, 2, 1, 48), R) on the realized R."""
    rows = json.loads((TC / "out" / "c4_lower.json").read_text())["a"]
    assert [(r["m"], r["rho"]) for r in rows] == list(CM_ROWS)
    for row in rows:
        m, rho = row["m"], row["rho"]
        F = fam.Fam(m, rho, 2, 1, 48)
        inst, _ = from_core(cm_case(m, rho), _empty(m))
        for key, stay in (("stay", True), ("rr", False)):
            res = simulate(inst, RRRenew(stay=stay), LenderModel(schedule="adaptive"))
            assert res.invariant_failures == [], (m, rho, key)
            R = [np.asarray(r, dtype=np.int64) for r in res.schedule.R]
            ratio = res.components["total"] / fam.opt_dp(F, R)[0]
            assert _close(ratio, row[key]), (m, rho, key, ratio, row[key])
            if stay:
                assert {L.site for L in res.leases} == {0}
            else:
                assert [L.site for L in sorted(res.leases, key=lambda x: x.id)] == \
                       [i % m for i in range(len(res.leases))]


def _marking_cases():
    for row, F, name, om in _o1_cases():
        if name != "adaptiveRR":
            assert "mark" in row
            yield row, F, name, om


@pytest.mark.slow
def test_marking_per_seed():
    """Check 3h: Marking under I2 with policy_rng = default_rng(seed), seeds 1000-1002, on the 576 marking rows
    of o1_ub.json: total cost and number of purchases equal fam.run_marking(F, om, default_rng(seed)) (all 400
    seeds per row: reproduction R8)."""
    n = 0
    for row, F, name, om in _marking_cases():
        inst, _ = from_core(F.core_instance(), om)
        for seed in (1000, 1001, 1002):
            res = simulate(inst, Marking(), LenderModel(information="I2"), policy_rng=np.random.default_rng(seed))
            tag = (row["m"], row["rho"], row["tau"], row["H"], name, seed)
            assert res.invariant_failures == [], tag
            cost, na = fam.run_marking(F, om, np.random.default_rng(seed))
            assert _close(res.components["total"], cost), (tag, res.components["total"], cost)
            assert len(res.leases) == na, (tag, len(res.leases), na)
        n += 1
    assert n == 576


def test_mark_state_phases():
    """§8.1: MarkState driven slot by slot by the announcement mask (start at slot 0; update at every slot of a
    running phase; a new phase at next_start, also in the slot where the last phase ended when H = 0) gives
    the phases of fam.marking_phases on all 576 marking schedules; MarkState.run_phases agrees."""
    n = 0
    for row, F, name, om in _marking_cases():
        A = np.zeros((F.m, F.T), dtype=bool)
        for l, r in enumerate(om):
            A[l, np.asarray(r, dtype=np.int64)] = True
        st = MarkState(range(F.m), F.tau, 60 * F.H, 60)        # from_core: H_min = 60 H, slot of 60 min
        st.start(0)
        for t in range(F.T):
            if not st.running and st.next_start == t:
                st.start(t)
            elif st.running:
                newly, unmarked = st.update(t, A[:, t])
                assert set(newly) | set(unmarked) <= set(range(F.m))
                if not st.running and st.next_start == t:
                    st.start(t)
        got = [(p, t1) for p, t1 in st.phases]
        want = [(int(p), None if pe is None else int(pe)) for p, pe in fam.marking_phases(F, om)]
        assert got == want, (row["m"], row["rho"], row["tau"], row["H"], name, got, want)
        assert MarkState.run_phases(A, F.tau, 60 * F.H, 60) == want
        n += 1
    assert n == 576
