"""Tests of sublet/calib.py against code/analysis/out (design/sim_spec.md §3.4.3; §9.2)."""
import math

from fixtures import load_json

from sublet import calib
from sublet.paths import ANALYSIS_OUT
from sublet.traces import catalog, lenders

A11 = load_json(ANALYSIS_OUT / "a11_calibration.json")
A5 = load_json(ANALYSIS_OUT / "a5_reclaim_cost_calibration.json")
A9B = load_json(ANALYSIS_OUT / "a9b_notice_buffer_24h.json")
A5_TIER = {"S": "llama3-8b", "M": "llama3-70b", "L": "llama3.1-405b"}
ALL26 = lenders.lender_names("spot_all") + lenders.lender_names("maas20")


def _rel(a, b, tol):
    return abs(a - b) <= tol * max(1.0, abs(b))


def test_load_time_matches_a11():
    """load_time_s for every catalog entry and scenario equals a11 load_time_s (1e-9 abs)."""
    n = 0
    for cn, entries in A11["load_time_s"].items():
        for name, by_sc in entries.items():
            e = catalog.entry(cn, name)
            assert e["g"] == A11["catalog"][cn][name]["g"] and e["w_GB"] == A11["catalog"][cn][name]["w_GB"]
            for sc, lam in by_sc.items():
                got = calib.load_time_s(e["w_GB"], e["g"], sc)
                assert abs(got - lam) <= 1e-9, (cn, name, sc, got, lam)
                n += 1
    assert n == sum(len(v2) for v in A11["load_time_s"].values() for v2 in v.values()) and n >= 64


def test_kappa_w_in_T_dr():
    """kappa, w_in and T_dr from the a5 assumptions (1e-12), and the rounded values of §3.4.3."""
    A = A5["assumptions"]
    for tier, a5t in A5_TIER.items():
        assert catalog.a5_tier_of(tier) == a5t
        c, tp, pf = A["concurrent_seqs_per_replica"], A["tpot_s"][a5t], A["prefill_tok_per_s_per_replica"][a5t]
        assert _rel(calib.kappa_wtok_per_min(tier), 60.0 * c / tp, 1e-12)
        assert _rel(calib.w_in(tier), (c / tp) / pf, 1e-12)
        assert _rel(calib.T_dr_s(tier), A5["calibration"][a5t]["T_dr_s (p99 drain)"], 1e-12)
    assert [round(calib.kappa_wtok_per_min(t)) for t in "SML"] == [512000, 219429, 128000]
    assert [round(calib.w_in(t), 4) for t in "SML"] == [0.2133, 0.3048, 0.5333]
    assert calib.prices() == {"a0": A11["inputs"]["a0"], "q_gpu": A11["inputs"]["q_GPU"], "a_p": A11["inputs"]["a_p"]}


def test_D_lender_matches_a11():
    n = 0
    for k, c in A11["contracts"].items():
        if "D_exact_min" not in c:
            continue
        assert calib.D_lender_min(c["D_exact_min"], c["slot_min"]) == c["D_lender_min"], k
        n += 1
    assert n == 40


def test_ir_multiplier_matches_a11():
    """ir_multiplier of every lender (26) and contract (40) at p99 and p99.9 (None <-> None; 1e-12)."""
    tab = A11["ir_prices_by_lender"]
    assert set(tab) == set(ALL26)
    contracts = {k: c for k, c in A11["contracts"].items() if "D_lender_min" in c}
    assert len(contracts) == 40
    n = 0
    for name in ALL26:
        s = lenders.slack(name)
        memo = {}
        for k, c in contracts.items():
            for q in ("p99", "p99.9"):
                key = (c["D_lender_min"], q)
                if key not in memo:
                    memo[key] = calib.ir_multiplier(s, c["D_lender_min"], q)
                got, want = memo[key], tab[name]["contracts"][k]["ir_multiplier"][q]
                assert (got is None) == (want is None), (name, k, q, got, want)
                if want is not None:
                    assert _rel(got, want, 1e-12), (name, k, q, got, want)
                n += 1
    assert n == 26 * 40 * 2


def test_rho_Hstar_matches_a11_rows():
    """rows.maas_a10.<tier>.<scenario>.by_contract (5-min slot): rho, H*_beta and beta~ at the
    maas_p99_median price; protected: beta~ at a_p, rho = 1, H*_beta None (1e-9)."""
    P = calib.prices()
    phi = A11["inputs"]["phi"]
    beta_jl = A11["inputs"]["beta_jl"]
    n = 0
    for tier, by_sc in A11["rows"]["maas_a10"].items():
        e = catalog.entry("maas_a10", tier)
        for sc, row in by_sc.items():
            lam = calib.load_time_s(e["w_GB"], e["g"], sc)
            assert abs(lam - row["lambda_s"]) <= 1e-9 and e["g"] == row["g"]
            for k, r in row["by_contract"].items():
                c = A11["contracts"][k]
                if k == "protected":
                    bt = calib.beta_tilde_usd(beta_jl, lam, e["g"], P["a_p"], P["q_gpu"], phi)
                    assert _rel(bt, r["beta_tilde_usd"], 1e-9) and r["rho"] == 1.0 and r["H_star_beta_s"] is None
                    assert calib.contract_klass(None, 0, 5) == "protected"
                    n += 1
                    continue
                assert c["slot_min"] == 5
                a = c["price_refs"]["maas_p99_median"]["a_usd_per_gpu_h"]
                if a is None:
                    assert r == {"offered": False}, (tier, sc, k)
                    continue
                bt = calib.beta_tilde_usd(beta_jl, lam, e["g"], a, P["q_gpu"], phi)
                assert _rel(bt, r["beta_tilde_usd"], 1e-9), (tier, sc, k)
                assert _rel(calib.rho(bt, e["g"], a, c["D_pd_min"]), r["rho"], 1e-9), (tier, sc, k)
                assert _rel(calib.H_star_beta_s(bt, e["g"], a, 60.0 * c["tau_min"]), r["H_star_beta_s"], 1e-9)
                assert calib.contract_klass(c["tau_min"], c["H_min"], 5) == c["class"], k
                n += 1
    assert n > 0


def test_buffer_env_running_max():
    """buffer_env is non-decreasing in D and equals a9b b_envelope_5min at its grid windows (exact)."""
    windows = A9B["meta"]["windows_min"]
    quantiles = A9B["meta"]["quantiles"]
    assert set(A9B["lenders"]) == set(ALL26)
    for name in ALL26:
        s = lenders.slack(name)
        prev = {q: -math.inf for q in quantiles}
        for D in windows:
            ref = A9B["lenders"][name]["windows"][str(D)]["b_envelope_5min"]
            for q in quantiles:
                b = calib.buffer_env(s, D, q)
                assert b == ref[q], (name, D, q, b, ref[q])
                assert b >= prev[q]
                prev[q] = b
    # every 5-min window up to 300 min on a spot pool and a MaaS cluster
    for name in ("a1:H800", "a2:c05"):
        s = lenders.slack(name)
        for q in ("p99", "p99.9"):
            vals = [calib.buffer_env(s, D, q) for D in range(5, 305, 5)]
            assert all(x <= y for x, y in zip(vals, vals[1:])), (name, q)
    assert calib.buffer_env(lenders.slack("a2:c05"), 60) == calib.buffer_env(lenders.slack("a2:c05"), 60, "p99")
