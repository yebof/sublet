"""Tests of sublet/algos/pd_core.py: the vectorized ORML-PD against code/theory_checks/c3/pd.py
(design/sim_spec_ms2.md §5; exit checks 2a-2d of §1.3; §17.2)."""
import json
import math
import re

import numpy as np
import pytest
from scipy.optimize import brentq

import check_c5_la
import pd as ref_pd

from fixtures import (AUDIT_TAGS, CONFIGS, UPPER_FAMS, UPPER_SEEDS, audit_case, c5_case, ms2_checks_dir,
                      toy_config, upper_case)

from sublet.algos import pd_core
from sublet.algos.common import column_cost, pd_window_slots, unit_costs
from sublet.algos.pd_core import VecPD, problem_from_core, problem_from_view, ref_key
from sublet.instance import active_units, build_instance, from_core, public_view

TC = CONFIGS.parents[1] / "theory_checks" / "c3"
TOL = 1e-9                  # M1: per-request and final values, relative to max(1, |ref|)
PSI = check_c5_la.LAMS      # 0.1, 0.3, 0.5, 0.8, 1.0


def _close(a, b, tol=TOL) -> bool:
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


# ---------------------------------------------------------------- reference runs
def _count_solves(monkeypatch):
    """Wrap pd._solve_Y to count its calls (the raises of a request, as the audit script counts them)."""
    calls = [0]
    orig = ref_pd._solve_Y

    def wrapped(*a, **k):
        calls[0] += 1
        return orig(*a, **k)
    monkeypatch.setattr(ref_pd, "_solve_Y", wrapped)
    return calls


def _ref_run(I, calls, requests=None, **kw):
    """pd.FracPD(I, **kw) over `requests` (default I.elements()); returns (pd, raises per request)."""
    pdr = ref_pd.FracPD(I, **kw)
    raises = []
    for c, t in (I.elements() if requests is None else requests):
        calls[0] = 0
        pdr.process(c, t)
        raises.append(calls[0])
    return pdr, raises


def _vec_run(prob, requests, **kw):
    vpd = VecPD(prob, record=True, **kw)
    return vpd, [vpd.request(c, t) for c, t in requests]


def _assert_same_run(I, vpd, outs, pdr, raises, tag, bitwise_costs=True):
    """Check 2a (M1): same requests and candidate keys, equal raise counts, per-request x, y, f within
    1e-9 max(1, |ref|); final x per column, primal, dual sum, dual-feasibility ratio, d; no cap hit."""
    assert len(outs) == len(pdr.records) == len(raises), tag
    for i, (out, rec, nr) in enumerate(zip(outs, pdr.records, raises)):
        c, t, cand, xs, ys, f, dl = rec
        where = f"{tag} request {i} ({c}, {t})"
        assert (out.c, out.t) == (c, t), where
        keys = [ref_key(vpd, col) for col in out.cols]
        assert keys == list(cand), (where, keys, cand)
        assert out.raises == nr, (where, out.raises, nr)
        for p, F in enumerate(cand):
            assert _close(out.x[p], xs[F]), (where, F, out.x[p], xs[F])
            assert _close(out.y[p], ys[F]), (where, F, out.y[p], ys[F])
            if bitwise_costs:          # core mode: the reference's arrays, bitwise
                assert out.delta[p] == dl[F] and out.C[p] == I.C(F[1], F[2], F[3]), (where, F)
            else:                      # engine mode: the view's arrays, 1e-12 (other operation order)
                assert (out.delta[p] == 0) == (dl[F] == 0) and _close(out.delta[p], dl[F], 1e-12), (where, F)
                assert _close(out.C[p], I.C(F[1], F[2], F[3]), 1e-12), (where, F)
        assert _close(out.f, f), (where, out.f, f)
    fx = vpd.final_x()
    assert set(fx) <= set(pdr.x), tag
    for F, v in pdr.x.items():
        assert _close(fx.get(F, 0.0), v), (tag, F, fx.get(F, 0.0), v)
    assert _close(vpd.primal(), pdr.primal()), (tag, vpd.primal(), pdr.primal())
    assert _close(vpd.dual, pdr.dual), (tag, vpd.dual, pdr.dual)
    assert _close(vpd.dual_feasibility(), pdr.check_dual_feasible()), tag
    assert vpd.d == pdr.d, (tag, vpd.d, pdr.d)
    assert vpd.stats["cap_hits"] == pdr.max_iter_hit == 0, tag


# ---------------------------------------------------------------- check 2a
@pytest.mark.parametrize("fam_name", UPPER_FAMS)
def test_equals_reference(fam_name, monkeypatch):
    """Check 2a: VecPD(problem_from_core(I)) equals pd.FracPD(I).run() on the 12 check_c3_upper instances
    of the family (core mode, costs bitwise equal)."""
    calls = _count_solves(monkeypatch)
    for seed in UPPER_SEEDS:
        I = upper_case(fam_name, seed)
        pdr, raises = _ref_run(I, calls)
        prob = problem_from_core(I)
        assert prob.d == I.m * I.K + 1 and np.array_equal(prob.site_perm, np.arange(I.m))
        vpd, outs = _vec_run(prob, I.elements())
        _assert_same_run(I, vpd, outs, pdr, raises, f"{fam_name}/{seed}")


# ---------------------------------------------------------------- check 2b
def _engine_requests(inst):
    """Requests of the engine mode (§5.1): per slow slot, D = slot maxima, n_c = active_units(D, u);
    clients ascending, units v ascending; on from_core instances one unit per active client."""
    g = inst.grid
    D = inst.clients.demand.reshape(inst.n, g.T_slow, g.phi).max(axis=2)
    out = []
    for t in range(g.T_slow):
        n = active_units(D[:, t], inst.units_per_replica)
        for c in range(inst.n):
            out += [(c, t)] * int(n[c])
    return out


@pytest.mark.parametrize("fam_name", UPPER_FAMS)
def test_equals_reference_via_view(fam_name, monkeypatch):
    """Check 2b: from_core(I, omega) -> PublicView -> problem_from_view arrays equal problem_from_core(I)
    to 1e-12 (not bitwise: other operation order), the engine-mode request order is I.elements(), and the
    PD run on the view's problem equals the reference as in 2a; seeds 0-3."""
    calls = _count_solves(monkeypatch)
    for seed in range(4):
        I = upper_case(fam_name, seed)
        inst, _ = from_core(I, [np.zeros(0, np.int64)] * I.m)
        pv = problem_from_view(public_view(inst, "I1"))
        pc = problem_from_core(I)
        tag = f"{fam_name}/{seed}"
        assert (pv.T, pv.m, pv.K, pv.J, pv.d) == (pc.T, pc.m, pc.K, pc.J, pc.d), tag
        for name in ("L", "g", "cl_llm", "site_perm"):
            assert np.array_equal(getattr(pv, name), getattr(pc, name)), (tag, name)
        for name in ("C", "q_req", "delta_req"):
            a, b = getattr(pv, name), getattr(pc, name)
            assert a.shape == b.shape and np.array_equal(np.isinf(a), np.isinf(b)), (tag, name)
            fin = np.isfinite(b)
            assert np.all(np.abs(a[fin] - b[fin]) <= 1e-12 * np.maximum(1.0, np.abs(b[fin]))), (tag, name)
        req = _engine_requests(inst)
        assert req == I.elements(), tag
        pdr, raises = _ref_run(I, calls)
        vpd, outs = _vec_run(pv, req)
        _assert_same_run(I, vpd, outs, pdr, raises, tag + " (view)", bitwise_costs=False)


# ---------------------------------------------------------------- check 2c
def test_c3_upper_stored():
    """Check 2c: P, dual, dualfeas, d and iter_hits of c3/out/c3_upper.json for all 60 entries (1e-9)."""
    recs = json.loads((TC / "out" / "c3_upper.json").read_text())
    assert len(recs) == 60
    for rec in recs:
        I = upper_case(rec["fam"], rec["seed"])
        vpd, _ = _vec_run(problem_from_core(I), I.elements())
        tag = f"{rec['fam']}/{rec['seed']}"
        assert _close(vpd.primal(), rec["P"]), (tag, vpd.primal(), rec["P"])
        assert _close(vpd.dual, rec["dual"]), tag
        assert _close(vpd.dual_feasibility(), rec["dualfeas"]), tag
        assert vpd.d == rec["d"] and vpd.stats["cap_hits"] == rec["iter_hits"], tag


# ---------------------------------------------------------------- check 2d
def _audit_counts() -> dict:
    """Part (2) of c3/audit/out/a2_P_equiv_and_termination.txt: tag -> (requests, mean, max, cap hits)."""
    txt = (TC / "audit" / "out" / "a2_P_equiv_and_termination.txt").read_text()
    pat = re.compile(r"^\s*(\w+): requests (\d+), mean iters ([\d.]+), max iters (\d+), cap\(2000\) hits (\d+)",
                     re.M)
    out = {m.group(1): (int(m.group(2)), m.group(3), int(m.group(4)), int(m.group(5))) for m in pat.finditer(txt)}
    assert set(out) == set(AUDIT_TAGS), out
    return out


def test_ties_family(monkeypatch):
    """Check 2d: per-request equality as 2a on the audit families (rand, slo, ties; seeds 0-5; core mode);
    requests, mean and maximum raises and cap hits equal part (2) of
    c3/audit/out/a2_P_equiv_and_termination.txt (563, 4.48, 8, 0; 563, 3.18, 7, 0; 510, 2.69, 4, 0)."""
    want = _audit_counts()
    calls = _count_solves(monkeypatch)
    for tag in AUDIT_TAGS:
        nreq = tot = mx = hits = 0
        for seed in range(6):
            I = audit_case(tag, seed)
            pdr, raises = _ref_run(I, calls)
            vpd, outs = _vec_run(problem_from_core(I), I.elements())
            _assert_same_run(I, vpd, outs, pdr, raises, f"{tag}/{seed}")
            r = [o.raises for o in outs]
            nreq += len(r)
            tot += sum(r)
            mx = max([mx] + r)
            hits += vpd.stats["cap_hits"]
        assert (nreq, f"{tot / nreq:.2f}", mx, hits) == want[tag], (tag, nreq, tot / nreq, mx, hits)


def _psi_pd(nearest: bool, monkeypatch):
    calls = _count_solves(monkeypatch)
    for seed in range(2):
        I, preds = c5_case(seed)
        prob = problem_from_core(I)
        for pr in preds:
            P = [tuple(col) for col in pr.P]
            for psi in PSI:
                tag = f"seed {seed} {pr.kind}{pr.par} psi {psi} nearest {nearest}"
                pdr, raises = _ref_run(I, calls, lam=psi, pred_cols=P, nearest_pred=nearest)
                vpd, outs = _vec_run(prob, I.elements(), psi=psi, pred_cols=P, nearest_pred=nearest)
                _assert_same_run(I, vpd, outs, pdr, raises, tag)


def test_psi_pd_nearest(monkeypatch):
    """Check 2d: the psi-PD with the nearest predicted column equals FracPD(I, lam=psi, pred_cols=P,
    nearest_pred=True) per request on c5_case seeds 0-1, all nine predictions, psi in {0.1, 0.3, 0.5,
    0.8, 1.0}; d equal (d = mK + 1 + min(p_max, 1))."""
    _psi_pd(True, monkeypatch)


def test_psi_pd_all_pred(monkeypatch):
    """Check 2d: the psi-PD with every predicted column equals FracPD(I, lam=psi, pred_cols=P,
    nearest_pred=False) (check_c5_la.py part (a)) on c5_case seeds 0-1, all nine predictions and psi."""
    _psi_pd(False, monkeypatch)


# ---------------------------------------------------------------- root search (§5.5)
def _h(vals, bs, cs, Y):
    """h(Y) = sum (v0 + b) exp(min(Y / c, 700)) - sum b - 1 (§5.5), evaluated in extended precision
    (np.longdouble), so that the oracle's root is not limited by cancellation in h."""
    v, b, c = (np.asarray(a, dtype=np.longdouble) for a in (vals, bs, cs))
    Yl = np.longdouble(Y)
    return float(np.sum((v + b) * np.exp(np.minimum(Yl / c, np.longdouble(700.0)))) - np.sum(b) - 1)


def test_root_accuracy():
    """§5.5: the Newton root equals the oracle brentq(h, 0, Y_hi, xtol=1e-300, rtol=4 eps, maxiter=1000) to
    1e-12 relative on 10,000 random vectors of length 2-500: v0 ~ U(0, 1) per variable, rescaled so that
    sum v0 <= 1 - 1e-3, b = 1/d with d uniform in {2, ..., 500}, c = 10^U(-3, 2). The reference routine
    (root='brentq') is checked on the same vectors at its own tolerance."""
    rng = np.random.default_rng(55)
    eps = np.finfo(float).eps
    worst = worst_b = 0.0
    for it in range(10_000):
        n = int(rng.integers(2, 501))
        v0 = rng.random(n)
        s = float(v0.sum())
        if s > 1 - 1e-3:
            v0 *= (1 - 1e-3) * float(rng.random()) / s
        d = int(rng.integers(2, 501))
        bs = np.full(n, 1.0 / d)
        cs = 10.0 ** rng.uniform(-3.0, 2.0, n)
        Y_hi = float(np.min(cs * np.log((1.0 + bs) / (v0 + bs))))
        assert _h(v0, bs, cs, Y_hi) >= 0 and _h(v0, bs, cs, 0.0) < 0
        oracle = brentq(lambda Y: _h(v0, bs, cs, Y), 0.0, Y_hi, xtol=1e-300, rtol=4 * eps, maxiter=1000)
        y = pd_core.root_newton(v0, bs, cs)
        rel = abs(y - oracle) / oracle
        worst = max(worst, rel)
        assert rel <= 1e-12, (it, n, d, y, oracle, rel)
        if it % 20 == 0:
            yb = pd_core.root_brentq(v0, bs, cs)
            worst_b = max(worst_b, abs(yb - oracle) / oracle)
    assert worst_b <= 1e-10, worst_b


# ---------------------------------------------------------------- order dependence (§5.1)
def test_order_dependence():
    """§5.1 (M2): the check_c3_upper families with the clients of each slot processed in reverse order;
    the change of P is written to ms2_checks/pd_order.json (informative: nothing is asserted about it)."""
    rows = []
    for fam_name in UPPER_FAMS:
        for seed in UPPER_SEEDS:
            I = upper_case(fam_name, seed)
            fwd = I.elements()
            rev = [(c, t) for t in range(I.T) for c in reversed(range(I.n)) if I.active[c, t]]
            assert sorted(fwd) == sorted(rev)
            Pf = _vec_run(problem_from_core(I), fwd)[0].primal()
            Pr = _vec_run(problem_from_core(I), rev)[0].primal()
            assert math.isfinite(Pf) and math.isfinite(Pr) and Pf > 0 and Pr > 0
            rows.append({"fam": fam_name, "seed": seed, "P": Pf, "P_reverse": Pr, "rel_change": (Pr - Pf) / Pf})
    summary = {f: {"max_abs_rel_change": max(abs(r["rel_change"]) for r in rows if r["fam"] == f),
                   "mean_rel_change": float(np.mean([r["rel_change"] for r in rows if r["fam"] == f]))}
               for f in UPPER_FAMS}
    out = ms2_checks_dir() / "pd_order.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"description": "P of VecPD with the clients of each slot in reverse order versus "
                                              "the core order (client ascending), check_c3_upper families",
                               "summary": summary, "rows": rows}, indent=1) + "\n")
    assert json.loads(out.read_text())["rows"] == rows


# ---------------------------------------------------------------- full model (§5.2)
def test_full_model_problem():
    """§5.2 in engine mode: candidate lists are the offered pairs (l, k) with finite delta, sites in pi order
    and contracts in index order; C_F = beta~ + g a max(P_k, L_k Δs) / 60 (M4) by hand on the toy (u = 4,
    λ > 0); q_req and delta_req per unit-slot; d for both d_modes; the windows of §5.2 (a contract with
    tau_slots >= T_s keeps rule T12, a Contract.protected one gets M5's window or protected_window); a
    refused (excluded) column is absent from its window's requests, and the next window's column of the
    same type is a candidate; cand_mask removes candidates."""
    # toy: one region, menus {short, long} at L0 and L1, {prot} at P; u = 4, λ = 300 s / 600 s
    inst = build_instance(toy_config({"contracts.0.H_min": 2}))
    v = public_view(inst, "I1")
    assert inst.units_per_replica == 4 and v.contracts[0].prepaid_min == 7
    perm = np.array([2, 0, 1])
    prob = problem_from_view(v, site_perm=perm)
    assert list(prob.L) == [1, 4, 4]                     # short: 1 + 2 // 5; long: 2 + 10 // 5; prot: M5 = 4
    assert prob.d == 3 * 3 + 1
    assert problem_from_view(v, d_mode="max_cand+1").d == 1 + 5
    bt = lambda lam, a: lam / 3600 * (1 * a + 1.0 * 1 * 7.15)        # beta_jl = 0, g = 1, phi = 1
    hand = {(0, 0): bt(300, 2.85) + 2.85 * 7 / 60, (0, 1): bt(300, 3.0) + 3.0 * 20 / 60,
            (1, 0): bt(300, 2.9) + 2.9 * 7 / 60, (1, 1): bt(300, 3.1) + 3.1 * 20 / 60,
            (2, 2): bt(600, 5.97) + 5.97 * 20 / 60}
    for l in range(3):
        for k in range(3):
            if (l, k) in hand:
                assert abs(prob.C[l, 0, k] - hand[(l, k)]) <= 1e-12 * hand[(l, k)], (l, k)
                assert prob.C[l, 0, k] == column_cost(v, l, 0, k, int(prob.L[k]))
            else:
                assert prob.C[l, 0, k] == np.inf
    q_req, d_req = unit_costs(v)
    assert np.array_equal(prob.q_req, q_req) and np.array_equal(prob.delta_req, d_req)
    assert abs(prob.q_req[0] - 7.15 * 5 / 240) <= 1e-15
    vpd = VecPD(prob)
    out = vpd.request(0, 3)
    keys = [ref_key(vpd, c) for c in out.cols]
    assert keys == [("A", 2, 0, 2, 0), ("A", 0, 0, 0, 3), ("A", 0, 0, 1, 0), ("A", 1, 0, 0, 3), ("A", 1, 0, 1, 0)]
    # a refused column: absent in its window [0, 4), its next window's column a candidate again
    col = int(out.cols[2])                                # ('A', 0, 0, 1, 0): window [0, 4)
    for t in (2, 3):
        ks = [ref_key(vpd, c) for c in vpd.request(0, t, excluded={col}).cols]
        assert ("A", 0, 0, 1, 0) not in ks and len(ks) == 4, ks
    ks = [ref_key(vpd, c) for c in vpd.request(0, 4, excluded={col}).cols]
    assert ("A", 0, 0, 1, 4) in ks and len(ks) == 5
    # cand_mask: drop (L1, long)
    mask = np.ones((3, 1, 3), dtype=bool)
    mask[1, 0, 1] = False
    pm = problem_from_view(v, site_perm=perm, cand_mask=mask)
    ks = [ref_key(vp, c) for vp in [VecPD(pm)] for c in vp.request(0, 0).cols]
    assert ks == [("A", 2, 0, 2, 0), ("A", 0, 0, 0, 0), ("A", 0, 0, 1, 0), ("A", 1, 0, 0, 0)]
    # windows: a contract with tau >= T_s keeps rule T12; protected: M5 (largest T12 window) or the parameter
    cfg = toy_config({"contracts.0.H_min": 2})
    cfg["contracts"].insert(2, {"id": "whole", "tau_min": 120, "H_min": 10})
    cfg["lenders"][1]["menu"] = ["short", "long", "whole"]
    cfg["lenders"][1]["prices"]["whole"] = 3.2
    i2 = build_instance(cfg)
    v2 = public_view(i2, "I1")
    assert v2.contracts[2].tau_slots == 24 and v2.contracts[3].protected
    p2 = problem_from_view(v2)
    assert list(p2.L) == [1, 4, 26, 26]
    assert [pd_window_slots(v2, k, None) for k in range(4)] == [1, 4, 26, 26]
    assert list(problem_from_view(v2, protected_window=6).L) == [1, 4, 26, 6]
    # multi-site config: SLO-infeasible sites leave the candidate list; pi from the 'order' stream
    ml = build_instance(CONFIGS / "ms2_multi_small.json")
    vm = public_view(ml, "I1")
    pi = np.random.default_rng(4).permutation(ml.m)
    pmm = problem_from_view(vm, site_perm=pi)
    vp = VecPD(pmm)
    for c in range(ml.n):
        j = int(ml.clients.llm[c])
        want = [(int(l), k) for l in pi if np.isfinite(ml.clients.delta_usd_per_h[c, l])
                for k in sorted(ml.sites[l].menu) if np.isfinite(ml.price[l, k])]
        got = [(F[1], F[3]) for F in (ref_key(vp, x) for x in vp.request(c, 5).cols)]
        assert got == want, (c, got, want)
        assert all(F[2] == j for F in (ref_key(vp, x) for x in vp.request(c, 6).cols))


# ---------------------------------------------------------------- raise cap, layered keys, assertions, scale
def test_raise_cap():
    """§5.4, §5.6: max_raises caps the raises of one request; a capped request performs exactly max_raises
    raises (the reference's count: pd.FracPD stops when its counter passes 2000) and counts as a cap hit,
    and RequestOut.raises reports the raises performed."""
    I = audit_case("rand", 0)
    full = VecPD(problem_from_core(I))
    most = max(full.request(c, t).raises for c, t in I.elements())
    assert most > 2 and full.stats_summary()["cap_hits"] == 0
    vpd = VecPD(problem_from_core(I), max_raises=2)
    outs = [vpd.request(c, t) for c, t in I.elements()]
    assert max(o.raises for o in outs) == 2
    capped = sum(1 for o in outs if o.raises == 2 and o.f + float(np.minimum(o.x, o.y).sum()) < 1.0 - 1e-10)
    assert vpd.stats_summary()["cap_hits"] == capped > 0


def test_layered_column_key():
    """§5.3, §6.4: a column with replica index iota >= 1 is the aligned window's column (l, j, k, floor(t/L) L,
    iota), with ref_key ('A', l, j, k, s, iota), shared by the requests of every slot of its window, and a new
    column in the next window."""
    inst = build_instance(toy_config({"contracts.0.H_min": 2}))
    v = public_view(inst, "I1")
    vpd = VecPD(problem_from_view(v))
    ls, ks = vpd.cand_pairs(0)
    io = np.ones(len(ls), dtype=np.int64)
    klong = [c.id for c in inst.contracts].index("long")
    L = int(vpd.L[klong])
    assert L == 4
    i = list(ks).index(klong)
    o0 = vpd.request(0, 0, iota=io)
    o1 = vpd.request(0, 1, iota=io)
    assert ref_key(vpd, o0.cols[i]) == ("A", int(ls[i]), 0, klong, 0, 1)
    assert o1.cols[i] == o0.cols[i]
    o4 = vpd.request(0, L, iota=io)
    assert ref_key(vpd, o4.cols[i]) == ("A", int(ls[i]), 0, klong, L, 1) and o4.cols[i] != o0.cols[i]
    o2 = vpd.request(0, 2, iota=2 * io)
    assert ref_key(vpd, o2.cols[i]) == ("A", int(ls[i]), 0, klong, 0, 2)
    assert ref_key(vpd, vpd.request(0, 2).cols[i]) == ("A", int(ls[i]), 0, klong, 0)    # iota 0: dense block


def test_construction_assertions():
    """§5.2: every finite C_F > 0 and every q_req > 0, PolicyError otherwise."""
    from sublet.algos.common import PolicyError
    import core

    def inst(a, beta, q):
        return core.Instance(T=2, tau=np.array([2]), H=np.array([0]), a=np.full((1, 1), a),
                             beta=np.full((1, 1), beta), g=np.array([1]), q=q, cl_llm=np.array([0]),
                             delta=np.array([[0.0]]), active=np.array([[True, False]]))
    problem_from_core(inst(0.1, 0.0, 1.0))                     # C_F = 0.2 > 0: accepted
    with pytest.raises(PolicyError):
        problem_from_core(inst(0.0, 0.0, 1.0))                 # C_F = 0
    with pytest.raises(PolicyError):
        problem_from_core(inst(0.1, 0.0, 0.0))                 # q_req = 0
    with pytest.raises(PolicyError):
        problem_from_core(inst(0.1, 0.0, -1.0))


def test_scale_invariance():
    """§5.5, §5.7: VecPD (root 'newton') is scale-invariant: multiplying a, beta, q and delta of a core
    instance by s in {1e-8, 1e5} leaves the candidate lists and raise counts identical and x, y, f within
    1e-12, scales the primal and the dual by s (1e-12 relative) and keeps the dual-feasibility ratio
    (1e-12 relative). The reference's root has an absolute xtol of 1e-14, so the reference itself is
    accurate only above a cost scale (§5.7); VecPD stays correct below it."""
    import copy
    for fam_name, seed in (("rand", 0), ("slo", 1), ("setcover", 2), ("spiky", 3)):
        I = upper_case(fam_name, seed)
        base = VecPD(problem_from_core(I))
        ob = [base.request(c, t) for c, t in I.elements()]
        for s in (1e-8, 1e5):
            J = copy.deepcopy(I)
            J.a, J.beta, J.q, J.delta = J.a * s, J.beta * s, J.q * s, J.delta * s
            v = VecPD(problem_from_core(J))
            os_ = [v.request(c, t) for c, t in J.elements()]
            tag = f"{fam_name}/{seed} s={s}"
            for i, (a, b) in enumerate(zip(ob, os_)):
                assert a.raises == b.raises and np.array_equal(a.cols, b.cols), (tag, i)
                assert np.max(np.abs(a.x - b.x), initial=0.0) <= 1e-12, (tag, i)
                assert np.max(np.abs(a.y - b.y), initial=0.0) <= 1e-12 and abs(a.f - b.f) <= 1e-12, (tag, i)
            for got, want in ((v.primal(), base.primal() * s), (v.dual, base.dual * s),
                              (v.dual_feasibility(), base.dual_feasibility())):
                assert abs(got - want) <= 1e-12 * abs(want), (tag, got, want)
