"""Tests of sublet/algos/rounding.py: threshold rounding and capacity layering against
code/theory_checks/c3/pd.py::round_pd (design/sim_spec_ms2.md §6.1-§6.4; exit check 2e; §17.2)."""
import json
import math

import numpy as np

import core
import pd as ref_pd

from fixtures import CONFIGS, UPPER_FAMS, UPPER_SEEDS, upper_case

from sublet.algos.pd_core import VecPD, problem_from_core
from sublet.algos.rounding import Layering, Rounder, rbar_theory

TC = CONFIGS.parents[1] / "theory_checks" / "c3"
TOL = 1e-9


def _close(a, b, tol=TOL) -> bool:
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def _pd_outs(I):
    vpd = VecPD(problem_from_core(I))
    return vpd, [vpd.request(c, t) for c, t in I.elements()]


def _round(vpd, outs, rng, rbar):
    """A Rounder fed request by request (the PD's outputs do not depend on the rounding)."""
    r = Rounder(vpd, rng, rbar)
    for out in outs:
        r.process(out, (out.c, 1))
    return r


def _assert_same_rounding(r, x, tag):
    assert r.opened_ref() == x["opened"], (tag, r.opened_ref(), x["opened"])
    assert _close(r.cost_an, x["cost_an"]), (tag, r.cost_an, x["cost_an"])
    assert _close(r.cost_pr, x["cost_pr"]), (tag, r.cost_pr, x["cost_pr"])
    assert r.n_fix_an == x["n_fix_an"], tag
    assert r.curve.shape == x["curve"].shape
    assert np.all(np.abs(r.curve - x["curve"]) <= TOL * np.maximum(1.0, np.abs(x["curve"]))), tag


def test_round_equals_reference():
    """Check 2e: on the 60 check_c3_upper instances, rounding seeds 0-3 and r-bar in {theory, 1}, a Rounder
    fed by VecPD with default_rng(s) gives round_pd(FracPD(I).run(), default_rng(s), r)'s opened map
    (keys and slots), cost_an, cost_pr, curve and n_fix_an (seeds 0-39: reproduction R1)."""
    for fam_name in UPPER_FAMS:
        for seed in UPPER_SEEDS:
            I = upper_case(fam_name, seed)
            pdr = ref_pd.FracPD(I).run()
            vpd, outs = _pd_outs(I)
            r_th = rbar_theory(max(I.n * I.T, 3))
            for s in range(4):
                for rbar in (r_th, 1):
                    x = ref_pd.round_pd(pdr, np.random.default_rng(s), r=None if rbar == r_th else 1)
                    assert x["r"] == rbar
                    r = _round(vpd, outs, np.random.default_rng(s), rbar)
                    _assert_same_rounding(r, x, f"{fam_name}/{seed} s={s} r={rbar}")


def test_rbar_theory():
    """§6.3: rbar_theory(max(n T, 3)) equals r of c3/out/c3_upper.json for all 60 entries."""
    recs = json.loads((TC / "out" / "c3_upper.json").read_text())
    assert len(recs) == 60
    for rec in recs:
        I = upper_case(rec["fam"], rec["seed"])
        assert rbar_theory(max(I.n * I.T, 3)) == rec["r"], rec["fam"]
    assert rbar_theory(1) == rbar_theory(3) == math.ceil(2 * math.log(3)) == 3
    assert rbar_theory(288 * 15) == math.ceil(2 * math.log(4320))


class _Scripted:
    """A generator stand-in whose random() returns scripted uniforms and counts the calls."""

    def __init__(self, values):
        self.values = list(values)
        self.calls = 0

    def random(self):
        v = self.values[self.calls]
        self.calls += 1
        return v


def _hand_instance():
    """T = 2, one contract (2, 0), three sites with beta 1, 2, 3 and a = 0.1, q = 1e12; client 0 is feasible
    at sites 0 and 1, client 1 at sites 0, 1 and 2 (delta 0); both active at slot 0. Request (0, 0) raises
    x_0 + x_1 (+ f ~ 1e-13) to 1 in one raise; request (1, 0) then has w = x_0 + x_1 >= 1 - 1e-10 and does
    not raise, so the column of site 2 enters a candidate list with x = 0."""
    inf = np.inf
    return core.Instance(T=2, tau=np.array([2]), H=np.array([0]), a=np.full((3, 1), 0.1),
                         beta=np.array([[1.0, 2.0, 3.0]]), g=np.array([1]), q=1e12,
                         cl_llm=np.array([0, 0]), delta=np.array([[0.0, 0.0, inf], [0.0, 0.0, 0.0]]),
                         active=np.array([[True, False], [True, False]]))


def test_draw_order_hand():
    """§6.1 (M8): one uniform per column, drawn at the first request whose candidate list contains it, in
    candidate order, also when x_F is still 0; theta = 1 - U^(1/r). By hand: U = (0.9, 0.2, 0.95) gives
    theta = (0.1, 0.8, 0.05); x after request 1 is about (0.72, 0.28, 0): column 0 opens by its threshold,
    column 2 (x = 0) does not; the practical rule assigns both requests to column 0, cost_pr = C_0 = 1.2;
    the reference round_pd with the same uniforms gives the same; with r = 2 theta = 1 - sqrt(U)."""
    I = _hand_instance()
    vpd, outs = _pd_outs(I)
    assert [o.raises for o in outs] == [1, 0]
    x0, x1 = outs[0].x
    assert outs[1].x[2] == 0.0 and abs(x0 + x1 - 1.0) <= 1e-9 and x0 > 0.7 and 0.27 < x1 < 0.3
    for rbar in (1, 2):
        U = [0.9, 0.2, 0.95]
        rng = _Scripted(U)
        r = Rounder(vpd, rng, rbar)
        seen = []
        opened = []
        for out in outs:
            opened.append([vpd.ref_key(c) for c in r.process(out, (out.c, 1))])
            seen.append(rng.calls)
        assert seen == [2, 3], seen                                  # 2 new columns, then 1 (x = 0)
        for col, u in zip(outs[1].cols, U):
            assert abs(r.theta(col) - (1.0 - u ** (1.0 / rbar))) <= 1e-15
        assert opened == [[("A", 0, 0, 0, 0)], []]
        assert r.opened_ref() == {("A", 0, 0, 0, 0): 0}
        assert abs(r.cost_pr - I.C(0, 0, 0)) <= 1e-12 and abs(I.C(0, 0, 0) - 1.2) <= 1e-12
        assert abs(r.cost_an - 1.2) <= 1e-12 and r.n_fix_an == 0
        assert r.last_assignment == (0, 0, 0, 0, 0)
        x = ref_pd.round_pd(ref_pd.FracPD(I).run(), _Scripted(U), r=rbar)
        _assert_same_rounding(r, x, f"hand r={rbar}")
    # thresholds that open nothing: the practical rule's fix-up buys the cheapest closed column (C + delta < q)
    rng = _Scripted([0.0, 0.0, 0.0])
    r = Rounder(vpd, rng, 1)
    ops = [[vpd.ref_key(c) for c in r.process(out, (out.c, 1))] for out in outs]
    assert ops == [[("A", 0, 0, 0, 0)], []] and r.n_fixups == 1
    x = ref_pd.round_pd(ref_pd.FracPD(I).run(), _Scripted([0.0, 0.0, 0.0]), r=1)
    _assert_same_rounding(r, x, "hand fix-up")


def test_layering_hand():
    """§6.4: layering with u = 2 and units a, b, c (and d) by hand: the index of a unit's host set, else the
    smallest index with fewer than u units (a new one if all are full); assign moves a unit (None: to
    fallback); end_slot drops the units that were not active; keys (l, j, k) are independent; inactive
    layering gives index 0 and keeps nothing."""
    a, b, c, d = (0, 1), (0, 2), (1, 1), (1, 2)
    L = Layering(2, True)
    assert L.iota(a, 0, 0, 0) == 0
    L.assign(a, (0, 0, 0, 0, 0))
    assert L.iota(b, 0, 0, 0) == 0
    L.assign(b, (0, 0, 0, 0, 0))
    assert L.iota(c, 0, 0, 0) == 1                     # host[0] = {a, b} is full
    L.assign(c, (0, 0, 0, 0, 1))
    assert L.iota(a, 0, 0, 0) == 0 and L.iota(c, 0, 0, 0) == 1 and L.iota(d, 0, 0, 0) == 1
    assert L.iota(a, 1, 0, 0) == 0 and L.iota(c, 0, 0, 1) == 0     # other (l, j, k): independent
    L.assign(a, None)                                  # a goes to fallback: host[0] = {b}
    assert L.iota(a, 0, 0, 0) == 0 and L.iota(d, 0, 0, 0) == 0 and L.hosted() == 2
    L.assign(d, (0, 0, 0, 4, 0))                       # another window of the same type: host[0] = {b, d}
    assert L.iota(a, 0, 0, 0) == 1                     # host[0] full, host[1] = {c} has room
    L.end_slot({b, c})                                 # d was not active: host[0] = {b}
    assert L.hosted() == 2 and L.iota(a, 0, 0, 0) == 0
    L.assign(c, (0, 0, 0, 0, 0))                       # c moves to host[0] = {b, c}; host[1] empty
    assert L.iota(a, 0, 0, 0) == 1 and L.iota(c, 0, 0, 0) == 0
    L.assign(a, (1, 0, 0, 0, 0))                       # hosting at another site
    assert L.iota(a, 1, 0, 0) == 0 and L.iota(a, 0, 0, 0) == 1 and L.hosted() == 3
    L.end_slot(set())
    assert L.hosted() == 0 and L.iota(c, 0, 0, 0) == 0
    off = Layering(2, False)
    off.assign(a, (0, 0, 0, 0, 0))
    off.assign(b, (0, 0, 0, 0, 0))
    assert off.iota(c, 0, 0, 0) == 0 and off.hosted() == 0


def test_practical_tie_with_q_is_fallback():
    """§6.2 step 3: the practical rule opens a closed column only if C_F + delta < q (strict): with
    C_F + delta == q exactly (0.5 + 0.5 = 1.0 in binary) and no threshold opening (theta = 1), the request
    goes to fallback: no purchase, no fix-up, cost_pr = q."""
    I = core.Instance(T=1, tau=np.array([1]), H=np.array([0]), a=np.array([[0.5]]), beta=np.array([[0.0]]),
                      g=np.array([1]), q=1.0, cl_llm=np.array([0]), delta=np.array([[0.5]]),
                      active=np.array([[True]]))
    vpd = VecPD(problem_from_core(I))
    out = vpd.request(0, 0)
    assert float(out.C[0]) + float(out.delta[0]) == 1.0 == out.q
    r = Rounder(vpd, _Scripted([0.0]), 1)                    # theta = 1 - 0 = 1: no threshold opening
    assert r.process(out, (0, 1)) == []
    assert r.last_assignment is None and r.opened == {} and r.n_fixups == 0
    assert r.cost_pr == 1.0
    # a hair cheaper column is bought by the fix-up
    I2 = core.Instance(T=1, tau=np.array([1]), H=np.array([0]), a=np.array([[0.25]]), beta=np.array([[0.0]]),
                       g=np.array([1]), q=1.0, cl_llm=np.array([0]), delta=np.array([[0.5]]),
                       active=np.array([[True]]))
    v2 = VecPD(problem_from_core(I2))
    o2 = v2.request(0, 0)
    r2 = Rounder(v2, _Scripted([0.0]), 1)
    assert [v2.ref_key(c) for c in r2.process(o2, (0, 1))] == [("A", 0, 0, 0, 0)] and r2.n_fixups == 1
    assert r2.cost_pr == 0.75


def test_refuse_leaves_opened_set():
    """§6.5 (M11): Rounder.refuse removes a column from the opened set (is_open False, absent from opened and
    opened_ref), records (opening slot, refusal slot) and leaves cost_pr unchanged; the practical rule then
    no longer routes through it (its C_F counts again for the next request)."""
    I = _hand_instance()
    vpd, outs = _pd_outs(I)
    r = Rounder(vpd, _Scripted([0.9, 0.2, 0.95]), 1)
    opened = r.process(outs[0], (0, 1))
    col = opened[0]
    assert r.is_open(col) and vpd.ref_key(col) == ("A", 0, 0, 0, 0)
    cost = r.cost_pr
    r.refuse(col, 1)
    assert not r.is_open(col) and col not in r.opened and r.opened_ref() == {}
    assert r.refused[col] == (0, 1) and r.cost_pr == cost
    r.process(outs[1], (1, 1))
    # request (1, 0): column 0 is closed again, so the practical rule pays C_0 + 0 = 1.2 < q (a fix-up)
    assert r.n_fixups == 1 and r.is_open(col) and abs(r.cost_pr - (cost + 1.2)) <= 1e-12


def test_iota_vec_equals_iota():
    """§6.4: the array path Layering.iota_vec (used by A2Planner, with `shape`) equals the scalar
    Layering.iota for every candidate pair, after each step of random assign / end_slot sequences
    (u in {2, 4}; a unit's own host set, else the smallest index with fewer than u units)."""
    rng = np.random.default_rng(31)
    for u in (2, 4):
        m, J, K = 3, 2, 2
        lay = Layering(u, True, shape=(m, J, K))
        ref = Layering(u, True)
        units = [(c, v) for c in range(4) for v in range(1, 6)]
        ls = np.array([l for l in range(m) for _ in range(K)], dtype=np.int64)
        ks = np.array([k for _ in range(m) for k in range(K)], dtype=np.int64)
        checked = 0
        for step in range(600):
            unit = units[int(rng.integers(len(units)))]
            j = unit[0] % J
            for uu in (unit, units[int(rng.integers(len(units)))]):
                jj = uu[0] % J
                want = [lay.iota(uu, int(l), jj, int(k)) for l, k in zip(ls, ks)]
                assert lay.iota_vec(uu, jj, ls, ks).tolist() == want, (u, step, uu)
                assert want == [ref.iota(uu, int(l), jj, int(k)) for l, k in zip(ls, ks)]
                checked += 1
            if rng.random() < 0.08:
                keep = {x for x in units if rng.random() < 0.6}
                lay.end_slot(keep)
                ref.end_slot(keep)
                continue
            if rng.random() < 0.2:
                key = None
            else:
                i = int(rng.integers(len(ls)))
                l, k = int(ls[i]), int(ks[i])
                key = (l, j, k, 0, lay.iota(unit, l, j, k))
            lay.assign(unit, key)
            ref.assign(unit, key)
        assert checked == 1200 and lay.max_iota >= 1
