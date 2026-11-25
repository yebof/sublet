"""Reproductions R1-R8 against their reference files (design/sim_spec_ms2.md §17.2 test_ms2_checks.py, §17.3).

Every test reads the output of a reproduction script that `sublet/experiments/run_ms2_checks.sh`
wrote to code/sim/out/ms2_checks/ (or SUBLET_MS2_CHECKS_DIR, conftest.py) and is skipped while that
file is missing (marker `needs_ms2_checks`). Per-run values must match the reference JSON to 1e-9 relative (deterministic
given the draws), text files line by line at print precision. The offline random lines of R3-R5
come from MILPs that the reference ran at HiGHS's default mip_rel_gap of 1e-4 and the build at
1e-9, so their ratios are compared at 2e-4 relative and their printed lines number by number
within that tolerance plus the print rounding (§17.2 test_c4_lower_random_offline). The two
`_written` tests check that the informative outputs hold one row per scanned point, respectively
per E2 cell and mu / beta~.
"""
from __future__ import annotations

import json
import math
import re

import pytest

from fixtures import ms2_checks_dir

from sublet.paths import ANALYSIS_OUT, C3, O1

TOL = 1e-9
TOL_MILP = 2e-4


def _path(name):
    p = ms2_checks_dir() / name
    if not p.is_file():
        pytest.skip(f"{p} is missing; run code/sim/sublet/experiments/run_ms2_checks.sh")
    return p


def _json(name):
    return json.loads(_path(name).read_text())


def _lines(path) -> list[str]:
    return path.read_text().splitlines()


def _close(a, b, tol=TOL) -> bool:
    if a is None or b is None:
        return a is None and b is None
    a, b = float(a), float(b)
    if math.isinf(a) or math.isinf(b):
        return a == b
    return abs(a - b) <= tol * max(1.0, abs(b))


def _check(got: dict, ref: dict, keys, tol=TOL, where=""):
    for k in keys:
        assert k in got, f"{where}: key {k!r} missing in the reproduction"
        assert _close(got[k], ref[k], tol), f"{where} {k}: {got[k]!r} != reference {ref[k]!r} (tol {tol})"


def _same(got: dict, ref: dict, keys, where=""):
    for k in keys:
        assert got[k] == ref[k], f"{where} {k}: {got[k]!r} != reference {ref[k]!r}"


_NUM = re.compile(r"[-+]?\d+\.\d+(?:e[-+]?\d+)?")


def _numbers_close(line: str, ref: str, rel: float, abs_tol: float) -> bool:
    """Same text apart from the decimal numbers, which agree within rel relative plus abs_tol."""
    if _NUM.sub("#", line) != _NUM.sub("#", ref):
        return False
    a, b = [float(x) for x in _NUM.findall(line)], [float(x) for x in _NUM.findall(ref)]
    return len(a) == len(b) and all(abs(x - y) <= rel * abs(y) + abs_tol for x, y in zip(a, b))


def _not_quick(meta: dict, name: str):
    assert not meta.get("quick"), f"{name} was written by a quick (smoke) run; rerun run_ms2_checks.sh"


# ---------------------------------------------------------------- R1
@pytest.mark.needs_ms2_checks("c3_upper_repro.json", "c3_upper_repro.txt")
def test_c3_upper():
    """R1: per (fam, seed) P, dual, dualfeas, ALG_an, ALG_pr, ALG_r1 of c3_upper.json (1e-9; d, r,
    iter_hits exact) and c3_upper.txt line by line."""
    got = {(x["fam"], x["seed"]): x for x in _json("c3_upper_repro.json")}
    ref = json.loads((C3 / "out" / "c3_upper.json").read_text())
    assert len(got) == len(ref) == 60
    for r in ref:
        g = got[(r["fam"], r["seed"])]
        w = f"{r['fam']} seed {r['seed']}"
        _check(g, r, ("P", "dual", "dualfeas", "ALG_an", "ALG_pr", "ALG_r1", "P_over_LPal", "P_over_2dual",
                      "chk_an_vs_rP", "ratio_an", "ratio_pr", "ratio_r1"), where=w)
        _same(g, r, ("d", "r", "iter_hits", "n_el", "m", "K", "J"), where=w)
    assert _lines(_path("c3_upper_repro.txt")) == _lines(C3 / "out" / "c3_upper.txt")


# ---------------------------------------------------------------- R2-R5
@pytest.mark.needs_ms2_checks("c4_lower_repro.json", "c4_lower_repro.txt")
def test_c4_lower():
    """R2-R5: c4_lower.json (a) stay, round-robin, PD(r=1), PD(r=th) mean/min; (b) revonly/OPT (BL7, every
    policy seed), PD(r=1)/OPT, frac/OPT; (c) BL6's ratio (every policy seed); (d) siloed A2 and shared
    A2 / OPT = 1, all to 1e-9; the random lines at 2e-4; c4_lower.txt line by line (the random lines
    number by number within 2e-4 plus the print rounding)."""
    got = _json("c4_lower_repro.json")
    ref = json.loads((C3 / "out" / "c4_lower.json").read_text())
    _not_quick(got["meta"], "c4_lower_repro.json")
    assert got["meta"]["random_lines"] and got["meta"]["parts"] == "abcd"
    assert len(got["a"]) == len(ref["a"]) == 16
    for g, r in zip(got["a"], ref["a"]):
        w = f"(a) m={r['m']} rho={r['rho']}"
        _same(g, r, ("m", "rho"), w)
        _check(g, r, ("LB_T", "asym", "stay", "rr", "pd_r1", "pd_r1_min", "pd_rth", "pd_rth_min"), where=w)
        assert g["pd_r1_R_equals_real_cost_renew"] and g["pd_rth_R_equals_real_cost_renew"], w
    assert len(got["b"]) == len(ref["b"]) == 4
    for g, r in zip(got["b"], ref["b"]):
        w = f"(b) beta={r['beta']}"
        _check(g, r, ("beta", "rho1", "ratio", "formula_T", "formula_asym", "pd_r1_ratio", "frac_ratio"), where=w)
        for v in g["ratio_per_seed"]:
            assert _close(v, r["ratio"]), (w, g["ratio_per_seed"], r["ratio"])
    assert len(got["c"]) == len(ref["c"]) == 5
    for g, r in zip(got["c"], ref["c"]):
        w = f"(c) H={r['H']}"
        _check(g, r, ("H", "tau", "ratio", "L_over_tau"), where=w)
        for v in g["ratio_per_seed"]:
            assert _close(v, r["ratio"]), (w, g["ratio_per_seed"], r["ratio"])
    assert len(got["d"]) == len(ref["d"]) == 5
    for g, r in zip(got["d"], ref["d"]):
        _check(g, r, ("b", "ratio"), where=f"(d) b={r['b']}")
        assert _close(g["shared_ratio"], 1.0), g
    for part, keys in (("b_random", ("rev_over_full", "spot_over_full")), ("c_random", ("ratio",)),
                       ("d_random", ("ratio",))):
        assert len(got[part]) == len(ref[part]), part
        for g, r in zip(got[part], ref[part]):
            assert g["seed"] == r["seed"] and g.get("b") == r.get("b"), (part, g, r)
            _check(g, r, keys, tol=TOL_MILP, where=f"{part} seed {r['seed']}")
    mine, refl = _lines(_path("c4_lower_repro.txt")), _lines(C3 / "out" / "c4_lower.txt")
    assert len(mine) == len(refl)
    for a, b in zip(mine, refl):
        if "random" in b:
            assert _numbers_close(a, b, TOL_MILP, 5e-4), (a, b)
        else:
            assert a == b, (a, b)


# ---------------------------------------------------------------- R6
@pytest.mark.needs_ms2_checks("c3_benchmark_repro.json", "c3_benchmark_repro.txt")
def test_c3_benchmark():
    """R6: c3_benchmark.json b[*].per_rate[*] ALG_renew, ALG_acc, ALG_renew_r1, ALG_acc_r1 (1e-9) and
    renew_le_2acc; c3_benchmark.txt (b, c) line by line."""
    got = _json("c3_benchmark_repro.json")
    ref = json.loads((C3 / "out" / "c3_benchmark.json").read_text())
    _not_quick(got["meta"], "c3_benchmark_repro.json")
    assert len(got["b"]) == len(ref["b"]) == 10
    for g, r in zip(got["b"], ref["b"]):
        assert g["seed"] == r["seed"] and len(g["per_rate"]) == len(r["per_rate"]) == 5
        for gp, rp in zip(g["per_rate"], r["per_rate"]):
            w = f"seed {r['seed']} rate {rp['rate']}"
            _check(gp, rp, ("rate", "ALG_renew", "ALG_acc", "ALG_renew_r1", "ALG_acc_r1"), where=w)
            _same(gp, rp, ("renew_le_2acc",), w)
    mine, refl = _lines(_path("c3_benchmark_repro.txt")), _lines(C3 / "out" / "c3_benchmark.txt")
    i, j = mine.index(next(x for x in mine if x.startswith("(b,c)"))), refl.index(next(x for x in refl if x.startswith("(b,c)")))
    assert mine[i:] == refl[j:]


# ---------------------------------------------------------------- R7
@pytest.mark.needs_ms2_checks("c5_la_repro.json", "c5_la_repro.txt")
def test_c5_la():
    """R7 (a, b): c5_la.json per instance and prediction: cPhat first (the predicted plan), then the psi-PD
    rows (P/OPT, cons_chk, dualfeas, rob_chk) and the integral rows of both rbar (FP, R, comb2, combg,
    chk2, chkg, switches), all to 1e-9; c5_la.txt line by line."""
    got = _json("c5_la_repro.json")
    ref = json.loads((C3 / "out" / "c5_la.json").read_text())
    _not_quick(got["meta"], "c5_la_repro.json")
    runs = got["runs"]
    assert len(runs) == len(ref) == 10
    for g, r in zip(runs, ref):
        assert g["seed"] == r["seed"] and len(g["rows"]) == len(r["rows"]) == 9
        for gr, rr in zip(g["rows"], r["rows"]):
            w = f"seed {r['seed']} {rr['kind']} {rr['par']}"
            _same(gr, rr, ("kind", "par"), w)
            _check(gr, rr, ("cPhat",), where=w)
            _check(gr, rr, ("cPhat_over_OPT",), where=w)
            _same(gr, rr, ("eta", "eta_chk"), w)
            for gl, rl in zip(gr["lam"], rr["lam"]):
                _check(gl, rl, ("lam", "P_over_OPT", "cons_chk", "dualfeas", "rob_chk"), where=f"{w} lam {rl['lam']}")
            for tag in ("r1", "rth"):
                _check(gr[tag], rr[tag], ("FP", "R", "comb2", "combg", "chk2", "chkg", "switches"), where=f"{w} {tag}")
    assert _lines(_path("c5_la_repro.txt")) == _lines(C3 / "out" / "c5_la.txt")


@pytest.mark.needs_ms2_checks("c5_la_nearest_repro.json", "c5_la_nearest_repro.txt")
def test_c5_la_nearest():
    """R7 (nearest): c5_la_nearest.json per row d (exact), P/OPT, cons_chk, dualfeas, rob_chk (1e-9) and
    c5_la_nearest.txt line by line."""
    got = _json("c5_la_nearest_repro.json")
    ref = json.loads((C3 / "out" / "c5_la_nearest.json").read_text())
    _not_quick(got["meta"], "c5_la_nearest_repro.json")
    runs = got["runs"]
    assert len(runs) == len(ref) == 10
    for g, r in zip(runs, ref):
        assert g["seed"] == r["seed"] and len(g["rows"]) == len(r["rows"]) == 45
        for gr, rr in zip(g["rows"], r["rows"]):
            w = f"seed {r['seed']} {rr['kind']} {rr['par']} lam {rr['lam']}"
            _same(gr, rr, ("kind", "par", "lam", "d"), w)
            _check(gr, rr, ("P_over_OPT", "cons_chk", "dualfeas", "rob_chk"), where=w)
    assert _lines(_path("c5_la_nearest_repro.txt")) == _lines(C3 / "out" / "c5_la_nearest.txt")


# ---------------------------------------------------------------- R8
@pytest.mark.needs_ms2_checks("o1_ub_repro.json", "o1_ub_repro.txt")
def test_o1_ub():
    """R8: the 648 rows of o1_ub.json (rr, NA, rr_bound, rr_ok; the 72 adaptiveRR rows also under the
    adaptive lender) and the marking fields of the 576 others (mark, mark_N, mark_se, Phi, mark_ok,
    opt_phase_ok), to 1e-9 (counts exact); both tables of o1_ub.txt line by line."""
    got = _json("o1_ub_repro.json")
    ref = json.loads((O1 / "out" / "o1_ub.json").read_text())
    _not_quick(got["meta"], "o1_ub_repro.json")
    assert got["meta"]["marking_seeds"] == 400
    rows = got["rows"]
    assert len(rows) == len(ref) == 648
    n_mark = n_ad = 0
    for i, (g, r) in enumerate(zip(rows, ref)):
        w = f"row {i} m={r['m']} rho={r['rho']} tau={r['tau']} H={r['H']} {r['sched']}"
        _same(g, r, ("m", "rho", "tau", "H", "T", "sched", "X", "NA", "rr_ok"), w)
        _check(g, r, ("opt", "rr", "rr_bound"), where=w)
        if r["sched"] == "adaptiveRR":
            assert "mark" not in g and _close(g["rr_adaptive_lender"], r["rr"]), w
            assert g["NA_adaptive_lender"] == r["NA"] and g["adaptive_R_equals_adaptive_rr"], w
            n_ad += 1
        else:
            _check(g, r, ("mark", "mark_N", "mark_se", "mark_N_exact", "mark_N_bound"), where=w)
            _same(g, r, ("Phi", "mark_ok", "opt_phase_ok"), w)
            n_mark += 1
    assert (n_mark, n_ad) == (576, 72)
    assert _lines(_path("o1_ub_repro.txt")) == _lines(O1 / "out" / "o1_ub.txt")


# ---------------------------------------------------------------- informative outputs
@pytest.mark.needs_ms2_checks("c2sw_rule_scan.json")
def test_c2sw_scan_written():
    """§16.4 item 8: c2sw_rule_scan.json holds one row per mu / beta~ = 1.10, 1.11, ..., 2.00."""
    d = _json("c2sw_rule_scan.json")
    _not_quick(d["meta"], "c2sw_rule_scan.json")
    mus = [r["mu_over_beta_tilde"] for r in d["rows"]]
    assert mus == [round(i * 0.01, 2) for i in range(110, 201)]
    for r in d["rows"]:
        assert {"H_star_SW", "reaction", "regime", "worst_ratio", "excess_over_2_minus_alpha"} <= set(r), r
        assert math.isfinite(r["worst_ratio"]) and r["worst_ratio"] >= 1.0, r


@pytest.mark.needs_ms2_checks("e2_reactions.json")
def test_e2_reactions_written():
    """§17.3: e2_reactions.json holds one row per E2 cell (E2 lender and contract with a p99 IR price in
    a11_calibration.json) and mu / beta~ in {0.2, 0.5, 1, 2}, with the fields of §9.4."""
    d = _json("e2_reactions.json")
    _not_quick(d["meta"], "e2_reactions.json")
    a11 = json.loads((ANALYSIS_OUT / "a11_calibration.json").read_text())
    inp, ir, con = a11["inputs"], a11["ir_prices_by_lender"], a11["contracts"]
    want = set()
    for n in inp["maas_lenders"] + inp["spot_L7_lenders"]:
        for k, v in ir[n]["contracts"].items():
            if d["meta"].get("tau_slot_only") and con[k]["tau_min"] != con[k]["slot_min"]:
                continue
            if v["ir_multiplier"]["p99"] is not None:
                for mu in (0.2, 0.5, 1.0, 2.0):
                    want.add((n, k, mu))
    got = [(r["lender"], r["contract"], r["mu_over_beta_tilde_ref"]) for r in d["rows"]]
    assert len(got) == len(set(got)) and set(got) == want, (len(got), len(want))
    fields = {"alpha_k", "kind", "reaction", "H_star_mu_s", "status", "first_clause", "insure_up_front",
              "lam_prime_s"}
    for r in d["rows"]:
        assert fields <= set(r), (sorted(fields - set(r)), r["lender"], r["contract"])
        if r["alpha_k"] >= 1:
            assert r["kind"] == "alpha>=1" and r["status"] == "NA-alpha>=1" and r["insure_up_front"] is None, r
        else:
            assert r["first_clause"] == (r["alpha_p"] <= r["alpha_k"] * (2 - r["alpha_k"])), r
            if r["first_clause"]:
                assert r["insure_up_front"] is True, r
