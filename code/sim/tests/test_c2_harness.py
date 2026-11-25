"""Tests of the C2 harness and of A1's C2 rule (design/sim_spec_ms2.md §16, §17.2 test_c2_harness.py).

Checks 3e and 3f of §1.3. A1's decision logic (`sublet.algos.c2rule`: thresholds, branch, reaction),
priced in C2's game by `sublet.harness.c2_harness` against `c2/model.py::opt_cost`, regenerates
`c2/out/alg_check.txt`, `alg_check_general.txt` and `alg_check_targeted.txt` line by line (§16.4
item 1); its thresholds equal `alg_check.thresholds` on every parameter draw, the closed-form column
of `c2/out/hstar.txt`, the H*_mu values of `a5b_exposure_thresholds.json` and `a11_calibration.json`,
the formula column of `c2/audit/out/model_switch_cost_default.txt` and the breakpoints of
`c2/audit/out/switch_cost_crossover.txt` (items 2-6). Items 7, 10 and 11: the known failure of the
C2-SW rule, the exact-in-x check of `c2/audit/alg_star_exact.py` through adapters, and C2-T2's INS
and the RRL rule in C2's game.

The loops of `alg_check.py` (lines 66-95 and 151-173) and `alg_check_targeted.py` (lines 7-26) are
transcribed here with their generators, call order and format strings, the plan coming from the
harness instead of `alg_cost`/`alg_star_cost`. `alg_check_targeted.py`, `switch_cost_crossover.py`
and `recheck_c2.py` write their output files on import and are never imported (§0 rule 5);
`alg_check` is imported only as the oracle of item 2 and for the diagnostics of item 1.
"""
from __future__ import annotations

import importlib
import itertools
import json
import math
import sys

import numpy as np
import pytest

from sublet.paths import ANALYSIS_OUT, C2, import_c2

C2REF = import_c2()                       # puts c2 and c2/audit on sys.path, without bytecode
Params, opt_cost, INF = C2REF.model.Params, C2REF.model.opt_cost, C2REF.model.INF
OUT = C2 / "out"
AUDIT_OUT = C2 / "audit" / "out"
A5B = json.loads((ANALYSIS_OUT / "a5b_exposure_thresholds.json").read_text())
A11 = json.loads((ANALYSIS_OUT / "a11_calibration.json").read_text())
REACT_LABEL = {"cold": "cold", "warm": "pre-warm"}     # C2Thresholds.react -> the references' label (§16.4 item 4)
SWITCH_KEY = {"switch_beta_tilde": "beta", "switch_full_model_C2SW_conjecture": "c2sw"}
FIELDS = ("s0", "Rw", "Rc", "Rh", "Hc", "Hh", "Hstar")


def _harness():
    from sublet.harness import c2_harness
    return c2_harness


def _rule():
    from sublet.algos import c2rule
    return c2rule


def _ref_module(name: str):
    """A reference module of c2 or c2/audit that is safe to import (alg_check, alg_star_exact), without bytecode."""
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        return importlib.import_module(name)
    finally:
        sys.dont_write_bytecode = old


def _rel_ok(a, b, tol):
    if math.isinf(a) or math.isinf(b):
        return a == b
    return abs(a - b) <= tol * max(1.0, abs(b))


def _ref_lines(path) -> list[str]:
    return path.read_text().splitlines()


# ---------------------------------------------------------------- the three loops (§16.3)
def _hc_worst(P, react):
    """H_c of alg_check.worst's default (line 46): min(mu, beta) for 'warm', mu for 'cold', over 2(1 - alpha)."""
    m = min(P.mu, P.beta) if react == "warm" else P.mu
    return m / (2 * (1 - P.alpha))


def alg_check_draws():
    """The 60 parameter draws of alg_check.py's first main block (default_rng(1), lines 67-81):
    (alpha, alpha_p, mu, react, lam, Hc)."""
    rng = np.random.default_rng(1)
    out = []
    for k in range(60):
        al = rng.uniform(0, 0.5)
        ap = rng.uniform(max(1 / (2 - al), al + 0.01), 1.0)
        mu = rng.uniform(0.05, 1.0) if k % 2 == 0 else rng.uniform(1.0, 5.0)
        react = "cold" if mu <= 1 else "warm"
        lam = rng.uniform(0, 3) if react == "cold" else 0.0
        m = min(mu, 1.0)
        Hc = m / (2 * (1 - al))
        out.append((al, ap, mu, react, lam, Hc))
    return out


NECESSITY = [(dict(mu=1.0, alpha=0.3, ap=0.45), "cold"), (dict(mu=1.0, alpha=0.6, ap=0.9), "cold"),
             (dict(mu=3.0, alpha=0.3, ap=0.7, lam=0.5), "warm"), (dict(mu=3.0, alpha=0.3, ap=0.7, lam=0.0), "cold")]


def alg_check_lines(n_draws: int = 60):
    """(line, context) pairs of alg_check.txt (alg_check.py lines 71-95) with the plan of
    AlgStarRule(s0, s0 + Hc, react, lam) priced by the harness (harness.worst). n_draws < 60 gives
    only the instance lines of the first n_draws draws."""
    h = _harness()
    lines = [("Theorem 5 check: worst ratio of ALG_c at H = Hc and H = Hc + 0.5 (target 2 - alpha)", None),
             ("conditions: tau=0, alpha<=1/2, (2-alpha)*ap>=1; cold if mu<=beta, warm with lam=0 if mu>beta", None)]
    cnt, maxexcess = 0, -1
    for al, ap, mu, react, lam, Hc in alg_check_draws()[:n_draws]:
        for H in [Hc, Hc + 0.5]:
            P = Params(mu=mu, alpha=al, ap=ap, H=H, lam=lam)
            res = h.worst(P, react, Hc=_hc_worst(P, react), Rmax=10.0, dR=0.02)
            w, arg = res[0], res[1]
            maxexcess = max(maxexcess, w - (2 - al))
            cnt += 1
            lines.append((f"alpha={al:.3f} ap={ap:.3f} mu={mu:.3f} lam={lam:.2f} H={H:.3f} react={react}: "
                          f"worst={w:.5f} 2-alpha={2-al:.5f} excess={w-(2-al):+.2e} at {arg}",
                          ("worst", P, react, w)))
    if n_draws < 60:
        return lines
    lines.append((f"SUMMARY: {cnt} instances, max excess over 2-alpha = {maxexcess:+.3e}", None))
    lines.append(("Necessity of the side conditions (expected excess > 0):", None))
    for kw, react in NECESSITY:
        al = kw["alpha"]
        m = min(kw["mu"], 1.0) if react == "warm" else kw["mu"]
        Hc = m / (2 * (1 - al))
        P = Params(H=Hc, **kw)
        res = h.worst(P, react, Hc=_hc_worst(P, react), Rmax=10.0, dR=0.02)
        w, arg = res[0], res[1]
        lines.append((f"{kw} react={react} H=Hc={Hc:.3f}: worst={w:.4f} 2-alpha={2-al:.4f} at {arg}",
                      ("worst", P, react, w)))
    return lines


def general_draws(thresholds):
    """Every draw of alg_check.main_general's rejection loop (default_rng(7), lines 152-166):
    (alpha, alpha_p, mu, lam, accepted), accepted by `thresholds` (a function of (al, ap, mu, lam)
    returning (Hstar, ...)); the loop stops after 60 accepted draws (120 instances)."""
    rng = np.random.default_rng(7)
    out, cnt = [], 0
    while cnt < 120:
        al = rng.uniform(0.05, 0.5)
        ap = rng.uniform(max(1 / (2 - al), al * (2 - al)) + 1e-3, 1.0)
        mu = rng.choice([rng.uniform(0.05, 1.0), rng.uniform(1.0, 6.0)])
        lam = rng.choice([0.0, rng.uniform(0, 1 / (1 - al))])
        Hs = thresholds(al, ap, mu, lam)
        ok = bool(np.isfinite(Hs) and Hs <= 9)
        out.append((al, ap, mu, lam, ok))
        if ok:
            cnt += 2
    return out


def targeted_draws(kind_of):
    """Every draw of alg_check_targeted.py's loop (default_rng(11), lines 7-20): (alpha, alpha_p, mu,
    lam, kind, accepted); kind_of(al, ap, mu, lam) returns (kind, Hstar) with the filter of lines
    17-20 (no tolerance). The loop stops after 30 accepted draws (60 runs)."""
    rng = np.random.default_rng(11)
    out, cnt = [], 0
    while cnt < 60:
        al = rng.uniform(0.25, 0.5)
        ap = rng.uniform(max(1 / (2 - al), al * (2 - al)) + 1e-3, 1.0)
        mu = rng.uniform(2.0, 8.0)
        lam = rng.uniform(0.01, 1 / (1 - al))
        kind, Hs = kind_of(al, ap, mu, lam)
        ok = not (Hs > 12 or kind == ("cold", "Rx<=Rwait"))
        out.append((al, ap, mu, lam, kind, ok))
        if ok:
            cnt += 2
    return out


def _kind_rule(al, ap, mu, lam):
    th = _rule().c2_thresholds(al, ap, mu, lam)
    warm = th.Hh < th.Hc
    Rx = th.Rh if warm else th.Rc
    return ("warm" if warm else "cold", "Rx>Rwait" if Rx > th.Rw else "Rx<=Rwait"), th.Hstar


def general_lines():
    """(line, context) pairs of alg_check_general.txt (alg_check.py lines 153-171) through the harness."""
    h, r = _harness(), _rule()
    lines = [("Theorem 6 check: ALG* at H = H* and H* + 0.3 (target 2 - alpha); random parameters with", None),
             ("tau=0, 0<alpha<=1/2, (2-alpha)ap>=1, ap>alpha(2-alpha), lam<=s0, H*<=9", None)]
    cnt, mx = 0, -1
    for al, ap, mu, lam, ok in general_draws(lambda *p: r.c2_thresholds(*p).Hstar):
        if not ok:
            continue
        th = r.c2_thresholds(al, ap, mu, lam)
        P0 = Params(mu=mu, alpha=al, ap=ap, lam=lam)
        for H in [th.Hstar, th.Hstar + 0.3]:
            P = P0.with_(H=H)
            res = h.worst_star(P, Rmax=14.0, dR=0.02)
            w, arg = res[0], res[1]
            mx = max(mx, w - (2 - al))
            cnt += 1
            lines.append((f"alpha={al:.3f} ap={ap:.3f} mu={mu:.3f} lam={lam:.3f} H*={th.Hstar:.3f} "
                          f"(Hc={th.Hc:.3f}, Hw={th.Hh:.3f}) H={H:.3f}: worst={w:.5f} excess={w-(2-al):+.2e} at R={arg}",
                          ("worst_star", P, 14.0, 0.02, w)))
    lines.append((f"SUMMARY: {cnt} instances, max excess over 2-alpha = {mx:+.3e}", None))
    return lines


def targeted_lines():
    """(line, context) pairs of alg_check_targeted.txt (alg_check_targeted.py lines 8-25) through the harness."""
    h, r = _harness(), _rule()
    lines = [("ALG* at H = H* and H* + 0.3; instances where warm (lam>0) or R_rho > R_wait", None)]
    cnt, mx, kinds = 0, -1, {}
    for al, ap, mu, lam, kind, ok in targeted_draws(_kind_rule):
        if not ok:
            continue
        th = r.c2_thresholds(al, ap, mu, lam)
        P0 = Params(mu=mu, alpha=al, ap=ap, lam=lam)
        kinds[kind] = kinds.get(kind, 0) + 1
        for H in [th.Hstar, th.Hstar + 0.3]:
            P = P0.with_(H=H)
            res = h.worst_star(P, Rmax=H + 8, dR=0.02)
            w, arg = res[0], res[1]
            mx = max(mx, w - (2 - al))
            cnt += 1
            lines.append((f"{kind} alpha={al:.3f} ap={ap:.3f} mu={mu:.3f} lam={lam:.3f} H*={th.Hstar:.3f} "
                          f"H={H:.3f}: worst={w:.5f} excess={w-(2-al):+.2e} at R={arg}",
                          ("worst_star", P, H + 8, 0.02, w)))
    lines.append((f"branch counts (instances): {kinds}", None))
    lines.append((f"SUMMARY: {cnt} runs, max excess over 2-alpha = {mx:+.3e}", None))
    return lines


def _diagnose(ctx) -> str:
    """The harness's worst ratio next to alg_check.worst / worst_star run in-process (§16.4 item 1)."""
    if ctx is None:
        return ""
    ac = _ref_module("alg_check")
    if ctx[0] == "worst":
        _, P, react, w = ctx
        ref = ac.worst(P, react, Rmax=10.0, dR=0.02)
    else:
        _, P, Rmax, dR, w = ctx
        ref = ac.worst_star(P, Rmax=Rmax, dR=dR)
    return f" [harness worst {w!r}, alg_check {ref[0]!r} at {ref[1]!r}]"


def _assert_text_equal(got, ref_path):
    ref = _ref_lines(ref_path)
    assert len(got) == len(ref), f"{ref_path.name}: {len(got)} lines, reference {len(ref)}"
    bad = [(i, line, ctx, ref[i]) for i, (line, ctx) in enumerate(got) if i < len(ref) and line != ref[i]]
    msg = "\n".join(f"line {i + 1}:\n  got {line!r}\n  ref {r!r}{_diagnose(ctx)}" for i, line, ctx, r in bad[:10])
    assert not bad, f"{ref_path.name}: {len(bad)} line(s) differ\n{msg}"


# ---------------------------------------------------------------- item 1: text equality (check 3e)
@pytest.mark.slow
def test_alg_check_txt():
    got = alg_check_lines()
    assert len(got) == 128
    _assert_text_equal(got, OUT / "alg_check.txt")


@pytest.mark.slow
def test_alg_check_general_txt():
    got = general_lines()
    assert len(got) == 123
    _assert_text_equal(got, OUT / "alg_check_general.txt")


@pytest.mark.slow
def test_alg_check_targeted_txt():
    got = targeted_lines()
    assert len(got) == 63
    _assert_text_equal(got, OUT / "alg_check_targeted.txt")


def test_alg_check_head():
    """The first 10 instance lines of alg_check.txt (the first five draws, both notices)."""
    got = alg_check_lines(n_draws=5)
    assert len(got) == 12
    ref = _ref_lines(OUT / "alg_check.txt")
    for i, (line, ctx) in enumerate(got):
        assert line == ref[i], f"line {i + 1}:\n  got {line!r}\n  ref {ref[i]!r}{_diagnose(ctx)}"


# ---------------------------------------------------------------- items 2-6: thresholds (check 3f)
def _compare_thresholds(al, ap, mu, lam, ac, where):
    r = _rule()
    ref = ac.thresholds(Params(mu=mu, alpha=al, ap=ap, lam=lam))
    th = r.c2_thresholds(al, ap, mu, lam)
    for f in FIELDS:
        assert _rel_ok(getattr(th, f), ref[f], 1e-12), (where, f, getattr(th, f), ref[f])
    react = "cold" if ref["Hc"] <= ref["Hh"] else "warm"           # alg_check.alg_star_cost, line 119
    Rx = ref["Rc"] if react == "cold" else ref["Rh"]
    assert th.react == react, (where, th.react, react)
    assert _rel_ok(th.Rrho, Rx, 1e-12), (where, th.Rrho, Rx)
    assert th.regime == ("sit-out" if Rx <= ref["Rw"] + 1e-12 else "known window"), (where, th.regime)
    assert th.rrl is False
    # branch of alg_check_targeted.py (lines 17-19), no tolerance
    warm = ref["Hh"] < ref["Hc"]
    rx = ref["Rh"] if warm else ref["Rc"]
    kind_ref = ("warm" if warm else "cold", "Rx>Rwait" if rx > ref["Rw"] else "Rx<=Rwait")
    kind_got = ("warm" if th.Hh < th.Hc else "cold",
                "Rx>Rwait" if (th.Rh if th.Hh < th.Hc else th.Rc) > th.Rw else "Rx<=Rwait")
    assert kind_got == kind_ref, (where, kind_got, kind_ref)


def test_thresholds_match_reference():
    """§16.4 item 2: c2_thresholds equals alg_check.thresholds on every parameter draw of the three loops
    (all fields to 1e-12 relative; reaction, R_rho, regime and the targeted branch equal)."""
    ac = _ref_module("alg_check")
    n = 0
    for al, ap, mu, react, lam, Hc in alg_check_draws():
        _compare_thresholds(al, ap, mu, lam, ac, ("alg_check", n))
        n += 1
    for kw, react in NECESSITY:
        _compare_thresholds(kw["alpha"], kw["ap"], kw["mu"], kw.get("lam", 0.0), ac, ("necessity", kw))
        n += 1
    ref_hs = lambda al, ap, mu, lam: ac.thresholds(Params(mu=mu, alpha=al, ap=ap, lam=lam))["Hstar"]
    gen = general_draws(ref_hs)
    assert sum(ok for *_, ok in gen) == 60
    for al, ap, mu, lam, ok in gen:
        _compare_thresholds(al, ap, mu, lam, ac, ("general", n))
        n += 1

    def kind_ref(al, ap, mu, lam):
        th = ac.thresholds(Params(mu=mu, alpha=al, ap=ap, lam=lam))
        warm = th["Hh"] < th["Hc"]
        Rx = th["Rh"] if warm else th["Rc"]
        return ("warm" if warm else "cold", "Rx>Rwait" if Rx > th["Rw"] else "Rx<=Rwait"), th["Hstar"]
    tgt = targeted_draws(kind_ref)
    assert sum(ok for *_, ok in tgt) == 30
    for al, ap, mu, lam, kind, ok in tgt:
        _compare_thresholds(al, ap, mu, lam, ac, ("targeted", n))
        n += 1
    # the rule's own rejection loops accept the same draws
    assert [d[:4] for d in general_draws(lambda *p: _rule().c2_thresholds(*p).Hstar)] == [d[:4] for d in gen]
    assert [d[:5] for d in targeted_draws(_kind_rule)] == [d[:5] for d in tgt]
    assert n == 60 + 4 + len(gen) + len(tgt)


def test_hstar_txt():
    """§16.4 item 3: the closed-form column 'Theorem 4: H* (H(R_cold), max(lam, H(R_warm)))' of the 30
    cases of c2/out/hstar.txt (hstar.py lines 73-84), at 3 decimals."""
    r = _rule()
    ref = _ref_lines(OUT / "hstar.txt")
    assert ref[0].startswith("alpha ap mu lam |") and len(ref) == 31
    cases = list(itertools.product([1 / 3, 0.5], [0.8], [0.5, 1.0, 1.5, 2.0, 3.0], [0.0, 0.5, 1.0]))
    for (al, ap, mu, lam), line in zip(cases, ref[1:]):
        head, _, closed = (p.strip() for p in line.split("|"))
        assert head == f"{al:.3f} {ap} {mu} {lam}", (head, al, ap, mu, lam)
        th = r.c2_thresholds(al, ap, mu, lam)
        assert closed == f"{th.Hstar:.3f} ({th.Hc:.3f}, {th.Hh:.3f})", (line, th)


def test_hstar_mu_a5b_a11():
    """§16.4 item 4: H*_mu / lambda of a5b (both switch conventions, mu/beta~ in {0.2, 0.5, 1, 2}) and of
    a11 per contract and price reference (value to 1e-9 relative, reaction, regime, status), via
    c2_thresholds at alpha_k with lambda = 1/(alpha_k + phi) and bw = alpha_p/(alpha_k + phi); plus
    one PublicView contract mapped through c2_units at beta_jl = 0 and price a0."""
    r = _rule()
    al, ap, phi = A5B["inputs"]["alpha"], A5B["inputs"]["alpha_p"], A5B["inputs"]["phi"]
    lam = 1 / (al + phi)
    n = 0
    for key, sw in SWITCH_KEY.items():
        for mu_s, v in A5B["H_star_mu_over_lambda"][key].items():
            mu = float(mu_s)
            th = r.c2_thresholds(al, ap, mu, lam, 1.0, None if sw == "beta" else ap / (al + phi))
            assert _rel_ok(th.Hstar / lam, v["H_over_lambda"], 1e-9), (key, mu_s, th.Hstar / lam, v)
            assert REACT_LABEL[th.react] == v["reaction"], (key, mu_s, th.react, v)
            assert th.regime == v["regime"].split(" (")[0], (key, mu_s, th.regime, v)
            n += 1
    assert n == 8

    AL11, AP11, PHI11 = A11["inputs"]["alpha"], A11["inputs"]["alpha_p"], A11["inputs"]["phi"]
    counts = {"compared": 0, "values": 0, "alpha>=1": 0, "not offered": 0}
    for kname, c in A11["contracts"].items():
        if kname == "protected":
            continue
        for ref_name, pref in c["price_refs"].items():
            if pref.get("multiplier") is None:
                assert "alpha_k" not in pref and "H_star_mu_over_lambda" not in pref, (kname, ref_name)
                counts["not offered"] += 1
                continue
            a_k = pref["alpha_k"]
            hs = pref["H_star_mu_over_lambda"]
            lam_k = 1 / (a_k + PHI11)
            at_default = abs(a_k - AL11) <= 1e-9
            if hs is None:
                assert a_k >= 1, (kname, ref_name, a_k)
                for sw in ("beta", "c2sw"):
                    assert r.hstar_status(a_k, AP11, 1.0, lam_k, sw, at_default) == "NA-alpha>=1"
                counts["alpha>=1"] += 1
                continue
            bw_k = AP11 / (a_k + PHI11)
            for key, by_mu in hs["by_switch"].items():
                sw = SWITCH_KEY[key]
                for mu_s, e in by_mu.items():
                    mu = float(mu_s)
                    th = r.c2_thresholds(a_k, AP11, mu, lam_k, 1.0, None if sw == "beta" else bw_k)
                    where = (kname, ref_name, key, mu_s)
                    if e["value"] is not None:
                        assert _rel_ok(th.Hstar / lam_k, e["value"], 1e-9), (where, th.Hstar / lam_k, e["value"])
                        counts["values"] += 1
                    else:
                        assert e["status"] == "NA-Cprime", (where, e)
                    assert REACT_LABEL[th.react] == e["reaction"], (where, th.react, e)
                    assert th.regime == e["regime"], (where, th.regime, e)
                    assert r.hstar_status(a_k, AP11, mu, lam_k, sw, at_default) == e["status"], (where, e)
                    counts["compared"] += 1
    assert counts["compared"] > 0 and counts["values"] > 0 and counts["alpha>=1"] > 0, counts

    # one PublicView contract through c2_units: the toy's L0 'short' at a0 = 2.85, beta_jl = 0, phi = 1, with
    # the protected site's load time set to L0's, so that lambda' = lambda
    from fixtures import site_index, toy_instance
    from sublet.instance import public_view
    inst = toy_instance({"lenders.2.lam_s": 300.0})
    view = public_view(inst, "I1")
    l, lp = site_index(inst, "L0"), site_index(inst, "P")
    k = [c.id for c in inst.contracts].index("short")
    kp = [c.id for c in inst.contracts].index("prot")
    assert view.price[l, k] == inst.a0_usd_per_gpu_h and inst.phi_load == 1.0 and not view.beta_usd.any()
    u = r.c2_units(view, 0, l, k, l_prot=lp, k_prot=kp, rep_site=lp)
    a0, aq = inst.a0_usd_per_gpu_h / inst.q_gpu_usd_per_h, float(view.price[lp, kp]) / inst.q_gpu_usd_per_h
    assert abs(u.alpha - a0) <= 1e-12 and abs(u.ap - aq) <= 1e-12
    assert abs(u.lam - 1 / (a0 + 1.0)) <= 1e-12, u
    assert abs(u.bw - aq / (a0 + 1.0)) <= 1e-12, u
    assert abs(u.lam - 0.715) <= 5e-4 and abs(u.bw - 0.597) <= 5e-4, u


def _default_jobs():
    """model_switch_cost_default.jobs() (lines 113-126): (mu, lam, bw, label)."""
    AL, AP, PHI = A5B["inputs"]["alpha"], A5B["inputs"]["alpha_p"], A5B["inputs"]["phi"]
    BW_DEF, LAM_DEF = A5B["prewarm_switch_cost_over_beta_tilde"], 1 / (AL + PHI)
    J = []
    for mu in [0.2, 0.5, 1.0, 2.0]:
        for bw, lab in [(1.0, "switch beta~ (Thm 4)"), (0.8, ""), (0.6, ""), (BW_DEF, "default switch"), (0.2, "")]:
            J.append((mu, LAM_DEF, bw, lab))
    for lam in [0.25, 0.5]:
        for mu in [0.5, 1.0, 2.0]:
            for bw in [1.0, 0.8, 0.6, 0.2]:
                J.append((mu, lam, bw, "switch beta~ (Thm 4)" if bw == 1.0 else ""))
            J.append((mu, lam, 1 - lam * (1 + AL - AP), "consistent with fees"))
    for mu in [0.2, 0.5, 1.0, 2.0]:
        for bw, lab in [(1.0, "switch beta~ (Thm 4), s0 = 1.70 grid"), (BW_DEF, "default switch, s0 = 1.70 grid")]:
            J.append((mu, LAM_DEF, bw, lab))
    return J, AL, AP


def test_switch_cost_default_formula():
    """§16.4 item 5: the formula column 'mu=.. lam=.. bw=..| formula H = h lam, reaction, regime' of the 58
    rows of c2/audit/out/model_switch_cost_default.txt (4 and 3 decimals), with the C2-SW thresholds."""
    r = _rule()
    jobs, AL, AP = _default_jobs()
    assert len(jobs) == 58
    rows = [x for x in _ref_lines(AUDIT_OUT / "model_switch_cost_default.txt")
            if x.startswith("mu=") and "| formula " in x]
    assert len(rows) == 58
    for (mu, lam, bw, lab), line in zip(jobs, rows):
        th = r.c2_thresholds(AL, AP, mu, lam, 1.0, bw)
        want = (f"mu={mu:.2f} lam={lam:.4f} bw={bw:.4f} {('[' + lab + ']') if lab else ''}| "
                f"formula {th.Hstar:.4f} = {th.Hstar / lam:.3f} lam, {REACT_LABEL[th.react]}, {th.regime}")
        assert line.split(" | exact")[0] == want, (line, want)


def _breakpoints(lam, bw, a, ap, step=0.001, mu_max=4.0):
    """switch_cost_crossover.breakpoints (lines 24-35) on top of c2_thresholds."""
    r = _rule()
    out, prev = [], None
    for i in range(1, int(round(mu_max / step)) + 1):
        mu = i * step
        th = r.c2_thresholds(a, ap, mu, lam, 1.0, bw)
        simple = abs(th.Hstar - mu / (2 * (1 - a))) < 1e-9
        key = ("simple form" if simple else "above simple form", REACT_LABEL[th.react], th.regime)
        if key != prev:
            out.append((mu, key, th.Hstar))
            prev = key
    return out


def test_crossover_breakpoints():
    """§16.4 item 6: every block of c2/audit/out/switch_cost_crossover.txt (the six (lambda, bw) cases at
    the default alpha, alpha_p), printed with the module's format strings (its lines 49-58)."""
    AL, AP, PHI = A5B["inputs"]["alpha"], A5B["inputs"]["alpha_p"], A5B["inputs"]["phi"]
    BW_DEF, LAM_DEF = A5B["prewarm_switch_cost_over_beta_tilde"], 1 / (AL + PHI)
    cases = [(LAM_DEF, BW_DEF, "default calibration"), (0.5, BW_DEF, "default switch, lambda = 0.5"),
             (0.25, BW_DEF, "default switch, lambda = 0.25"), (1e-9, BW_DEF, "default switch, lambda -> 0"),
             (0.5, 0.7182, "fee-consistent pair"), (0.25, 0.8591, "fee-consistent pair")]
    want = []
    for lam, bw, lab in cases:
        want += ["", f"lambda={lam:.4f} bw={bw:.4f} ({lab}); 2 bw = {2 * bw:.4f}"]
        want += [f"  mu >= {mu:.3f}: {key[0]}, {key[1]}, {key[2]} (H* = {H:.4f})"
                 for mu, key, H in _breakpoints(lam, bw, AL, AP)]
    ref = _ref_lines(AUDIT_OUT / "switch_cost_crossover.txt")
    assert f"alpha={AL:.6f} alpha_p={AP:.6f}" in ref[0], ref[0]
    i0 = ref.index(want[1]) - 1
    assert ref[i0:i0 + len(want)] == want
    assert ref[i0 + len(want)] == "" and ref[i0 + len(want) + 1].startswith("lambda dependence")
    # the breakpoints quoted in §16.4 item 6 for the default calibration
    bp = [round(mu, 3) for mu, _, _ in _breakpoints(LAM_DEF, BW_DEF, AL, AP)]
    assert bp == [0.001, 1.195, 1.619, 1.725], bp


# ---------------------------------------------------------------- item 7: the known failure of the C2-SW rule
def test_c2sw_known_failure():
    """§16.4 item 7: at alpha = 1/3, alpha_p = 0.8, mu = 2, lambda = 0.25, bw = 0.2 and H = H*_SW = 1.15 the
    C2-SW thresholds react warm with R_warm = 2.65 < R_wait = 3.75; for the window ending at R = 2.45 the
    notice comes at 1.30 < s0 = 1.5, ALG* waits, and at x = R+ its ratio against opt_cost_bw is
    1.7107 > 2 - alpha (recheck_c2.txt line 64). The worst ratio on worst_star's grid, with ALG* paying
    bw for its pre-warm, exceeds 2 - alpha."""
    from sublet.experiments.repro_c2sw_scan import grid_worst
    r, h = _rule(), _harness()
    al, ap, mu, lam, bw = 1 / 3, 0.8, 2.0, 0.25, 0.2
    th = r.c2_thresholds(al, ap, mu, lam, 1.0, bw)
    assert th.react == "warm" and f"{th.Rh:.4f}" == "2.6500" and f"{th.Rw:.4f}" == "3.7500", th
    assert f"{th.Hstar:.2f}" == "1.15" and f"{th.s0:.4f}" == "1.5000", th
    H = th.Hstar
    P = Params(mu=mu, alpha=al, ap=ap, H=H, lam=lam)
    rule = r.AlgStarRule.from_thresholds(th, lam)
    R = 2.45
    plan = rule.plan(R, H)
    assert plan[0] == "wait-insure" and R - H < th.s0 and R < th.Rrho, plan
    x = np.array([R + 1e-7])
    ratio = float(np.asarray(h.c2_plan_cost(plan, R, x, P, bw=bw))[0]
                  / C2REF.model_switch_cost.opt_cost_bw(x, R, P, bw)[0])
    assert f"{ratio:.4f}" == "1.7107", ratio
    assert ratio > 2 - al
    w, arg = grid_worst(P, lambda RR: rule.plan(RR, H),
                        lambda xs, RR: C2REF.model_switch_cost.opt_cost_bw(xs, RR, P, bw), th.s0, bw=bw)
    assert w > 2 - al, (w, arg)


# ---------------------------------------------------------------- item 10: exact in x (optional, slow)
@pytest.mark.slow
def test_alg_star_exact_menu(monkeypatch):
    """§16.4 item 10: the menu and RRL runs of c2/audit/alg_star_exact.py (Part 2) with A1's rule through
    adapters for the module's `thresholds` and `alg_star`: 654 menu runs and 84 RRL runs
    (alg_star_exact.txt lines 19-20), each with max excess <= 1e-7."""
    ase = _ref_module("alg_star_exact")
    h = _harness()
    # the harness's own adapters (c2_harness.exact_thresholds and exact_alg_star), the code of §16.4 item 10
    monkeypatch.setattr(ase, "thresholds", h.exact_thresholds)
    monkeypatch.setattr(ase, "alg_star", lambda x, R, H, P, th: h.exact_alg_star(np.asarray(x, float), R, H, P, th))
    rng = np.random.default_rng(7)
    for k in range(400):                         # Part 1's draws (lines 182-186), to reach the generator state
        a = rng.choice([0.0, rng.uniform(0, 0.9)])
        ap = rng.uniform(a + 0.01, 1.0)
        _P = dict(b=1.0, a=a, ap=ap, mu=rng.uniform(0, 5), lam=rng.choice([0.0, rng.uniform(0, 3)]),
                  rrl=bool(rng.random() < 0.2))
        R = rng.uniform(0.05, 6)
        _x = R + rng.choice([rng.uniform(1e-3, 0.2), rng.uniform(0, 8)])
    cases = []
    for a in [0.0, 0.25, 1 / 3, 0.5]:            # lines 202-217
        aplo = max(1 / (2 - a), a * (2 - a)) + 1e-6
        s0 = 1 / (1 - a)
        for ap in [aplo, 0.8 if aplo < 0.8 else 0.95, 1.0]:
            for mu in sorted(set([0.0, 0.3, 1.0, 2 * (1 - a), 1.5, 2.0, 2.0 / (1 - a), 3.0, 4.0])):
                for lam in [0.0, 0.5, s0]:
                    cases.append(dict(b=1.0, a=a, ap=ap, mu=mu, lam=lam, rrl=False))
    for _ in range(60):
        a = rng.uniform(0, 0.5)
        lo = max(1 / (2 - a), a * (2 - a))
        cases.append(dict(b=1.0, a=a, ap=rng.uniform(lo + 1e-6, 1.0), mu=rng.uniform(0, 6),
                          lam=rng.choice([0.0, rng.uniform(0, 1 / (1 - a))]), rrl=False))
    for a in [0.0, 1 / 3, 0.5, 0.6, 0.75, 0.9]:
        for mu in [0.0, 0.5, 1.0, 2.0, 2.0 / (1 - a), 3.0, 6.0]:
            cases.append(dict(b=1.0, a=a, ap=1.0, mu=mu, lam=0.0, rrl=True))
    worst = {"menu": -np.inf, "rrl": -np.inf}
    nrun = {"menu": 0, "rrl": 0}
    bad = []
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        for P in cases:
            th = ase.thresholds(P["a"], P["ap"], P["mu"], P["lam"], rrl=P["rrl"])
            if not np.isfinite(th["Hs"]):
                continue
            for H in [th["Hs"], th["Hs"] + 0.37]:
                w, arg = ase.worst_ratio(P, H, th)
                ex = w - (2 - P["a"])
                key = "rrl" if P["rrl"] else "menu"
                nrun[key] += 1
                worst[key] = max(worst[key], ex)
                if ex > 1e-7:
                    bad.append((P, H, w, arg))
    assert nrun == {"menu": 654, "rrl": 84}, nrun
    assert not bad and worst["menu"] <= 1e-7 and worst["rrl"] <= 1e-7, (worst, bad[:5])


# ---------------------------------------------------------------- item 11: INS and RRL in C2's game
def _ins_and_rrl(al, ap, mu, lam, H_ins):
    """(INS's worst ratio, CR_ins, [RRL rule's worst ratio at H*_RRL and H*_RRL + 0.5])."""
    from sublet.experiments.repro_c2sw_scan import grid_worst
    r = _rule()
    th = r.c2_thresholds(al, ap, mu, lam)
    plan = r.ins_plan(th)
    assert plan == ("wait-insure", th.s0)
    P = Params(mu=mu, alpha=al, ap=ap, H=H_ins, lam=lam)
    w_ins, _ = grid_worst(P, lambda R: plan, lambda xs, R: opt_cost(xs, R, P), th.s0)
    cr_ins = max(2 - al, ap / al)
    th_r = r.c2_thresholds(al, None, mu, lam)
    assert th_r.rrl and th_r.react == "cold" and math.isinf(th_r.Rh)
    w_rrl = []
    for H in (th_r.Hstar, th_r.Hstar + 0.5):
        Pr = Params(mu=mu, alpha=al, ap=ap, H=H, lam=lam, allow_p=False)
        rule = r.AlgStarRule.from_thresholds(th_r, lam)
        w, _ = grid_worst(Pr, lambda R, H=H, rule=rule: rule.plan(R, H), lambda xs, R, Pr=Pr: opt_cost(xs, R, Pr),
                          th_r.s0)
        w_rrl.append(w)
    return w_ins, cr_ins, w_rrl


@pytest.mark.parametrize("n_draws", [pytest.param(10, id="quick"),
                                     pytest.param(60, id="all", marks=pytest.mark.slow)])
def test_ins_and_rrl(n_draws):
    """§16.4 item 11: INS (ins_plan) against model.opt_cost has worst ratio CR_ins = max(2 - alpha,
    alpha_p/alpha) on worst_star's grid (within [CR_ins (1 - 1e-3), CR_ins + 1e-9]), on the draws of
    alg_check.py's first block with alpha >= 0.01 and at the default prices of a11 `inputs`
    (CR_ins = alpha_p/alpha = 2.0947); the RRL rule against opt_cost with allow_p = False has worst
    ratio at most 2 - alpha + 1e-7 at H >= H*_RRL on the same draws."""
    draws = [d for d in alg_check_draws() if d[0] >= 0.01][:n_draws]
    assert len(draws) == n_draws
    cases = [(al, ap, mu, lam, Hc, f"draw {i}") for i, (al, ap, mu, react, lam, Hc) in enumerate(draws)]
    al0, ap0, phi = A11["inputs"]["alpha"], A11["inputs"]["alpha_p"], A11["inputs"]["phi"]
    lam0 = 1 / (al0 + phi)
    H0 = _rule().c2_thresholds(al0, ap0, 1.0, lam0).Hstar
    cases.append((al0, ap0, 1.0, lam0, H0, "default prices"))
    for al, ap, mu, lam, H_ins, where in cases:
        w_ins, cr_ins, w_rrl = _ins_and_rrl(al, ap, mu, lam, H_ins)
        assert cr_ins * (1 - 1e-3) <= w_ins <= cr_ins + 1e-9, (where, w_ins, cr_ins)
        for w in w_rrl:
            assert w <= 2 - al + 1e-7, (where, w, 2 - al)
    assert f"{max(2 - al0, ap0 / al0):.4f}" == "2.0947"


# ---------------------------------------------------------------- the harness's own loops and closed forms
def test_harness_head_lines():
    """§16: c2_harness.alg_check_lines (the harness's own transcription of alg_check.py) gives the first 10
    instance lines of alg_check.txt, and compare_lines finds no difference on them."""
    h = _harness()
    got = h.alg_check_lines(n_runs=10)
    ref = h.reference_lines("alg_check.txt")
    assert len(got) == 12 and got == ref[:12]
    assert got == [line for line, _ in alg_check_lines(n_draws=5)]


@pytest.mark.slow
def test_harness_regenerate():
    """§16 (check 3e) through the harness itself: c2_harness.regenerate gives alg_check.txt (128 lines),
    alg_check_general.txt (123) and alg_check_targeted.txt (63) with no differing line (compare_lines)."""
    h = _harness()
    for name, n in (("alg_check.txt", 128), ("alg_check_general.txt", 123), ("alg_check_targeted.txt", 63)):
        lines = h.regenerate(name, workers=1)
        assert len(lines) == n and h.compare_lines(name, lines) == [], (name, h.compare_lines(name, lines)[:3])


def test_harness_closed_forms():
    """§16.4 items 2-7 and 11 through the harness's own helpers: threshold_draws holds every draw of the three
    loops (the tests' transcriptions with the reference's thresholds); hstar_closed_rows, the formula lines of
    model_switch_cost_default.txt and the crossover blocks equal the stored files; default_hstar_entry gives
    a5b's H*_mu / lambda (1e-9), reaction and regime; c2sw_failure_point gives the ratio 1.7107 of recheck_c2.txt
    line 64; worst_ins attains CR_ins and worst_rrl stays within 2 - alpha at H*_RRL."""
    h, r = _harness(), _rule()
    ac = _ref_module("alg_check")
    ref_hs = lambda al, ap, mu, lam: ac.thresholds(Params(mu=mu, alpha=al, ap=ap, lam=lam))["Hstar"]

    def kind_ref(al, ap, mu, lam):
        th = ac.thresholds(Params(mu=mu, alpha=al, ap=ap, lam=lam))
        warm = th["Hh"] < th["Hc"]
        Rx = th["Rh"] if warm else th["Rc"]
        return ("warm" if warm else "cold", "Rx>Rwait" if Rx > th["Rw"] else "Rx<=Rwait"), th["Hstar"]
    td = h.threshold_draws()
    key = lambda d: (d["alpha"], d["ap"], d["mu"], d["lam"])
    first = [(al, ap, mu, lam) for al, ap, mu, react, lam, Hc in alg_check_draws()] + \
            [(kw["alpha"], kw["ap"], kw["mu"], kw.get("lam", 0.0)) for kw, _ in NECESSITY]
    assert [key(d) for d in td if d["source"] == "alg_check"] == first
    assert [key(d) for d in td if d["source"] == "general"] == [d[:4] for d in general_draws(ref_hs)]
    assert [key(d) for d in td if d["source"] == "targeted"] == [d[:4] for d in targeted_draws(kind_ref)]
    # closed forms against the stored files
    ref = _ref_lines(OUT / "hstar.txt")[1:]
    rows = h.hstar_closed_rows()
    assert len(rows) == len(ref) == 30
    for (head, closed), line in zip(rows, ref):
        parts = [x.strip() for x in line.split("|")]
        assert (parts[0], parts[2]) == (head, closed), (line, head, closed)
    assert h.switch_cost_default_formula_lines() == h.stored_switch_cost_default_formula()
    assert len(h.stored_switch_cost_default_formula()) == 58
    assert h.crossover_lines() == h.stored_crossover_lines() and len(h.crossover_lines()) == 28
    for key_sw, sw in SWITCH_KEY.items():
        for mu_s, v in A5B["H_star_mu_over_lambda"][key_sw].items():
            e = h.default_hstar_entry(A5B["inputs"]["alpha"], float(mu_s), sw)
            assert _rel_ok(e["value"], v["H_over_lambda"], 1e-9) and e["reaction"] == v["reaction"], (key_sw, mu_s, e)
            assert e["regime"] == v["regime"].split(" (")[0], (key_sw, mu_s, e)
    f = h.c2sw_failure_point()
    assert f["plan"][0] == "wait-insure" and f"{f['ratio']:.4f}" == "1.7107" and f["ratio"] > f["two_minus_alpha"]
    # INS and RRL on worst_star's grid
    al, ap, phi = A11["inputs"]["alpha"], A11["inputs"]["alpha_p"], A11["inputs"]["phi"]
    lam = 1 / (al + phi)
    P = Params(mu=1.0, alpha=al, ap=ap, lam=lam, H=r.c2_thresholds(al, ap, 1.0, lam).Hstar)
    cr = max(2 - al, ap / al)
    w_ins = float(h.worst_ins(P)[0])
    assert cr * (1 - 1e-3) <= w_ins <= cr + 1e-9, (w_ins, cr)
    H_rrl = r.c2_thresholds(al, None, 1.0, lam).Hstar
    w_rrl = float(h.worst_rrl(P.with_(H=H_rrl))[0])
    assert w_rrl <= 2 - al + 1e-7, (w_rrl, 2 - al)


def test_h_star_mu_view_a11():
    """§9.2 through a PublicView: for every a11 contract and price reference, h_star_mu on onesite_c2 at price
    alpha_k q (beta_jl = 0, phi = 1, lambda' = lambda = 300 s; the protected contract at alpha_p q) gives a11's
    H*_mu / lambda as over_lambda (1e-9) and value_s = over_lambda x 300 s, and a11's reaction, regime and
    status, so that the a0 references reach 'VERIFIED' through at_default_calibration; alpha_k >= 1 gives no
    value and status 'NA-alpha>=1'."""
    from fixtures import Q_GPU, onesite_c2, site_index
    from sublet.instance import public_view
    r = _rule()
    AP11 = A11["inputs"]["alpha_p"]
    views = {}

    def view_for(a_k):
        if a_k not in views:
            inst, _ = onesite_c2([1.0] * 4, a_rev=a_k * Q_GPU, a_prot=AP11 * Q_GPU, lam_rev=300.0, lam_prot=300.0)
            assert inst.phi_load == 1.0 and not inst.beta_usd.any()
            v = public_view(inst, "I1")
            ids = [c.id for c in inst.contracts]
            views[a_k] = (v, site_index(inst, "R"), site_index(inst, "P"), ids.index("rev"), ids.index("prot"))
        return views[a_k]
    counts = {"values": 0, "verified": 0, "na": 0, "alpha>=1": 0}
    for kname, c in A11["contracts"].items():
        if kname == "protected":
            continue
        for ref_name, pref in c["price_refs"].items():
            if pref.get("multiplier") is None:
                continue
            a_k = float(pref["alpha_k"])
            v, l, lp, k, kp = view_for(a_k)
            bt = float(v.beta_tilde_usd[0, l, k])
            hs = pref["H_star_mu_over_lambda"]
            if hs is None:
                for sw in ("beta", "c2sw"):
                    hm = r.h_star_mu(v, 0, l, k, l_prot=lp, k_prot=kp, rep_site=lp, mu_usd=bt, switch=sw)
                    assert hm["status"] == "NA-alpha>=1" and hm["value_s"] is None, (kname, ref_name, hm)
                counts["alpha>=1"] += 1
                continue
            for key_sw, by_mu in hs["by_switch"].items():
                sw = SWITCH_KEY[key_sw]
                for mu_s, e in by_mu.items():
                    hm = r.h_star_mu(v, 0, l, k, l_prot=lp, k_prot=kp, rep_site=lp, mu_usd=float(mu_s) * bt, switch=sw)
                    where = (kname, ref_name, key_sw, mu_s)
                    assert REACT_LABEL[hm["reaction"]] == e["reaction"] and hm["regime"] == e["regime"], (where, hm, e)
                    assert hm["status"] == e["status"], (where, hm["status"], e["status"])
                    assert _rel_ok(hm["value_s"], hm["over_lambda"] * 300.0, 1e-12), (where, hm)
                    if e["value"] is not None:
                        assert _rel_ok(hm["over_lambda"], e["value"], 1e-9), (where, hm["over_lambda"], e["value"])
                        counts["values"] += 1
                    else:
                        assert e["status"] == "NA-Cprime", (where, e)
                        counts["na"] += 1
                    counts["verified"] += hm["status"] == "VERIFIED"
    assert counts["values"] > 0 and counts["verified"] > 0 and counts["alpha>=1"] > 0, counts


def test_hstar_status_order():
    """§9.2: hstar_status tests in this order: NA-alpha>=1 (alpha >= 1); RRL (no protected contract), before
    any test on lambda; NA-Cprime when (C') fails, including lambda <= s0 = 1/(1 - alpha) (tolerance 1e-12);
    then PROVEN-Cor5 / PROVEN-T4 (switch 'beta') or VERIFIED / CONJECTURE ('c2sw'). Through a PublicView: a
    protected load time of 3000 s makes A1's lambda exceed s0, so its status is NA-Cprime."""
    from fixtures import onesite_c2
    from sublet.algos.a1 import A1
    from sublet.instance import public_view
    r = _rule()
    st = r.hstar_status
    assert st(1.0, None, 1.0, 9.0, "c2sw", False) == "NA-alpha>=1"
    assert st(1.2, 0.8, 1.0, 0.1, "beta", True) == "NA-alpha>=1"
    assert st(0.4, None, 1.0, 99.0, "beta", False) == "RRL"
    s0 = 1 / 0.6
    assert st(0.4, 0.84, 1.0, s0 + 2e-12, "beta", False) == "NA-Cprime"
    assert st(0.4, 0.84, 1.0, s0, "beta", False) == "PROVEN-Cor5"
    assert st(0.4, 0.84, 1.0, s0 + 0.5e-12, "c2sw", False) == "CONJECTURE"
    assert st(0.4, 0.8, 1.0, 2.0, "c2sw", False) == "NA-Cprime"            # (2 - a) ap >= 1, but lam > s0
    assert st(0.4, 0.8, 1.0, 1.0, "c2sw", False) == "CONJECTURE"
    assert st(0.4, 0.5, 1.0, 1.0, "c2sw", False) == "NA-Cprime"            # (2 - a) ap < 1
    inst, _ = onesite_c2([1.0] * 12, lam_rev=300.0, lam_prot=3000.0)
    pol = A1(insure="never")
    pol.reset(public_view(inst, "I1"), np.random.default_rng(0))
    u = pol.units
    assert u.lam > 1 / (1 - u.alpha) and (2 - u.alpha) * u.ap >= 1 and u.ap > u.alpha * (2 - u.alpha)
    assert pol.report()["status"] == "NA-Cprime"


def test_alg_star_announcement_at_s():
    """§9.1: ALG*'s plan reacts when the announcement a = R - H comes at or after the purchase s (a >= s,
    equality included) or R >= R_thr; else wait-insure at max(R, s) (fallback in RRL mode); R = inf: none."""
    rule = _rule().AlgStarRule(1.0, 5.0, "cold", 0.5)
    assert rule.plan(2.0, 1.0) == ("react-cold", 1.0, 2.0)                  # a = 1 = s
    assert rule.plan(1.9, 1.0) == ("wait-insure", 1.9)                       # a = 0.9 < s, R < R_thr
    assert rule.plan(5.0, 4.5) == ("react-cold", 1.0, 5.0)                  # R >= R_thr
    warm = _rule().AlgStarRule(1.0, 5.0, "warm", 0.5)
    assert warm.plan(2.0, 1.0) == ("react-warm", 1.0, 2.0, 1.5)
    assert _rule().AlgStarRule(1.0, 5.0, "cold", 0.5, True).plan(1.9, 1.0) == ("fallback",)
    assert rule.plan(math.inf, 1.0) == ("none", 1.0)


def test_cheapest_protected_order():
    """§9.2, M32: cheapest_protected returns the flagged contract with the smallest (price, site, contract
    index) at a site reachable by some client: a second protected contract on P at a higher price, and a
    second protected site at a lower price, change the choice accordingly; `sites` restricts the search."""
    from fixtures import site_index, toy_config
    from sublet.instance import build_instance, public_view
    cfg = toy_config()
    cfg["contracts"].append({"id": "prot2", "tau_min": None, "H_min": 0, "prepaid_min": 10})
    cfg["lenders"][2]["menu"] = ["prot", "prot2"]
    P2 = dict(cfg["lenders"][2])
    P2.update({"id": "P2", "group": "gp2"})
    cfg["lenders"].append(P2)
    inst = build_instance(cfg)
    ids = [c.id for c in inst.contracts]
    lp, lp2 = site_index(inst, "P"), site_index(inst, "P2")
    kp, kp2 = ids.index("prot"), ids.index("prot2")
    price = np.array(inst.price, dtype=float, copy=True)
    price[lp, kp2] = 6.5                    # prot2 dearer than prot on P
    price[lp2, kp] = 6.0
    price[lp2, kp2] = 5.5                   # the cheapest flagged contract: prot2 on P2
    inst.price = price
    v = public_view(inst, "I1")
    cp = _rule().cheapest_protected
    assert cp(v, 0, [0]) == (lp2, kp2)
    assert cp(v, 0, [0], sites=[lp]) == (lp, kp)
    price[lp2, kp2] = 5.97                  # tie with (P, prot) at 5.97: the lower site index wins
    inst.price = price
    v = public_view(inst, "I1")
    assert cp(v, 0, [0]) == (min(lp, lp2), kp if min(lp, lp2) == lp else kp2)
    assert cp(v, 0, []) is None
