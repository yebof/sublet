"""Revocation exposure rho and the notice thresholds H*_beta and H*_mu at the default calibration
(design/Sublet_design.md §3.6.6, Table 3.8; open decision Q25).

Inputs (no trace is read except a2 and a5 outputs):
  prices      Silicon Data H100 index 2026-10-14: lease a0 = 2.85, fallback q_GPU = 7.15 USD/GPU-h; protected
              (AWS Capacity Blocks p5) 5.97 USD/GPU-h (literature/sources/gpu-rental-prices-h100-2026-10.md)
  load times  1.2 s warm peer over RDMA (zhang2025blitzscale, Fig. 21, p. 287); 10.3 s LLaMA-2-70B from local
              SSD, optimized loader (fu2024serverlessllm, Fig. 6a, p. 144); a5 model 8B at 10 GB/s and 405B at
              2 GB/s (a5_reclaim_cost_calibration.json); 128 s OPT-6.7B over 1 Gbps (fu2024serverlessllm, p. 148);
              18 min Llama-70B over 1 Gbps, a lower bound (yu2025lambdascale, p. 3)
  model       beta_jl = 0, phi = 1, a_lk = a0; one replica's demand normalized to q_j; tau = 1 slot, reported for
              the 1-min slot of the sensitivity run (tau = 60 s, notices exact) and for the default 5-min slow-loop
              slot (tau = 300 s, notices rounded down to whole slots in the guaranteed window D)
Definitions (design §1.5.3, §1.6):
  beta~   = lambda q_j (alpha + phi)                    core loading cost
  rho(H)  = 1 + beta~ / (g a D), D = tau + H             = 1 + (1 + phi/alpha) lambda / D
  H*_beta = beta~ / (g a) - tau                          = (1 + phi/alpha) lambda - tau
  H*_mu   = C2-T4 threshold (c2_single_site.md §6) in C2 units q = 1, beta = beta~ = 1, lambda_C2 = 1/(alpha+phi);
            with a switch that costs beta~ (C2-T4, PROVEN under (C')) and with the switch cost of the full model,
            a pre-warm into protected capacity that pays protected rent during the load, alpha_p/(alpha+phi) beta~
            (C2-SW substitution, CONJECTURE: the exact game agrees at 58 points at the default prices,
            c2/audit/out/model_switch_cost_default.txt; earlier 16 points in c2/audit/out/model_switch_cost.txt).
H*_mu scales with lambda (all terms are proportional to beta~), so it is reported as a multiple of lambda.
The functions are reused by a11_calibration.py (per-tier, per-contract calibration tables).
"""
import json
import math

import numpy as np

from common import OUT, save_json

A0, Q_GPU, A_P = 2.85, 7.15, 5.97
ALPHA, ALPHA_P, PHI, TAU = A0 / Q_GPU, A_P / Q_GPU, 1.0, 60.0
SLOW_SLOT = 300.0
MU_RATIOS = [0.2, 0.5, 1.0, 2.0]
NOTICES = {"spot_like_2min": 120.0, "aep82_min_1h": 3600.0, "h_4h": 14400.0}


def c2_hstar(a, ap, mu, lam, b=1.0, bw=None):
    """C2-T4 threshold; bw = switch cost (bw = b is Theorem 4, bw < b the C2-SW substitution)."""
    bw = b if bw is None else bw
    s0, chi = b / (1 - a), (2 - a) * ap - a
    r_wait = (2 - a) * b / (1 - a) ** 2
    div = lambda x, y: x / y if y != 0 else (math.inf if x > 0 else -math.inf)
    h = lambda r: r - s0 if r <= r_wait else r
    r_cold = max(s0 + mu / (2 * (1 - a)), div(mu + a * b - (2 - a) * bw, a * (1 - a)), (mu + a * b) / chi)
    r_warm = max(s0 + bw / (2 * (1 - a)), (a * b + bw) / chi,
                 lam + (a * b + bw) / (a * (1 - a)) if lam > 0 else -math.inf)
    h_cold, h_warm = h(r_cold), max(lam, h(r_warm))
    react, r = ("cold", r_cold) if h_cold <= h_warm else ("pre-warm", r_warm)
    return {"H_over_lambda": min(h_cold, h_warm) / lam, "reaction": react,
            "regime": "sit-out (R <= R_wait)" if r <= r_wait else "known window (R > R_wait)"}


def load_points():
    """The six load times of Table 3.8 as (label, lambda in s); two of them come from a5's model."""
    a5 = json.load(open(f"{OUT}/a5_reclaim_cost_calibration.json"))["calibration"]
    return [("warm peer over RDMA, 1.2 s (zhang2025blitzscale Fig. 21)", 1.2),
            ("LLaMA-2-70B local SSD, optimized loader (fu2024serverlessllm Fig. 6a)", 10.3),
            ("a5 model, 8B at 10 GB/s", a5["llama3-8b"]["setup_s_by_load_GBps"]["10"]),
            ("OPT-6.7B over 1 Gbps, stock stack (fu2024serverlessllm p. 148)", 128.0),
            ("a5 model, 405B at 2 GB/s", a5["llama3.1-405b"]["setup_s_by_load_GBps"]["2"]),
            ("Llama-70B over 1 Gbps, lower bound (yu2025lambdascale p. 3)", 18 * 60.0)]


def hstar_mu_coefs(alpha=ALPHA, alpha_p=ALPHA_P, phi=PHI, mu_ratios=MU_RATIOS):
    """H*_mu / lambda per mu/beta~ (keys str(mu)) for the two switch-cost conventions at lease price ratio alpha
    (beta_jl = 0, so lambda = beta~ / (q (alpha + phi)) and a protected pre-warm costs alpha_p / (alpha + phi) beta~).
    Reused by a11_calibration.py for contract prices other than a0."""
    lam_c2 = 1 / (alpha + phi)
    bw_full = alpha_p / (alpha + phi)
    coef = {}
    for name, bw in (("switch_beta_tilde", None), ("switch_full_model_C2SW_conjecture", bw_full)):
        coef[name] = {str(m): c2_hstar(alpha, alpha_p, m, lam_c2, bw=bw) for m in mu_ratios}
    return coef


def exposure_row(name, lam, coef, f_beta):
    """rho, H*_beta and H*_mu of one load time at the default prices (Table 3.8 row)."""
    return {"load": name, "lambda_s": lam, "H_star_beta_s": f_beta * lam - TAU,
            "rho": {k: 1 + f_beta * lam / (TAU + h) for k, h in NOTICES.items()},
            "slot_5min": {"H_star_beta_s": f_beta * lam - SLOW_SLOT,
                          "rho": {k: 1 + f_beta * lam / (SLOW_SLOT + SLOW_SLOT * (h // SLOW_SLOT))
                                  for k, h in NOTICES.items()}},
            "H_star_mu_s": {sw: {m: v["H_over_lambda"] * lam for m, v in c.items()} for sw, c in coef.items()}}


def crossover(coef, f_beta, tau=TAU):
    """Load time above which H*_mu < H*_beta: c lam < f_beta lam - tau  <=>  lam > tau / (f_beta - c)."""
    return {sw: {m: (tau / (f_beta - v["H_over_lambda"]) if v["H_over_lambda"] < f_beta else None)
                 for m, v in c.items()} for sw, c in coef.items()}


def main():
    loads = load_points()
    f_beta = 1 + PHI / ALPHA
    lam_c2 = 1 / (ALPHA + PHI)
    bw_full = ALPHA_P / (ALPHA + PHI)
    coef = hstar_mu_coefs()
    rows = [exposure_row(name, lam, coef, f_beta) for name, lam in loads]
    cross = crossover(coef, f_beta)

    a2 = json.load(open(f"{OUT}/a2_lender_maas.json"))
    cl = [v for k, v in a2.items() if k.startswith("cluster_")]
    nu = {s: float(np.median([c["leases"][s]["window"]["reclaims_per_day"] for c in cl])) for s in ("p10", "p25", "p50")}
    nu_max = max(nu.values())
    lam_spare = 300.0

    res = {
        "inputs": {"alpha": ALPHA, "alpha_p": ALPHA_P, "phi": PHI, "tau_s": TAU, "slow_slot_s": SLOW_SLOT, "beta_jl": 0.0,
                   "notices_s": NOTICES, "mu_over_beta_tilde": MU_RATIOS},
        "conditions": {
            "C_prime": {"(2-a)ap>=1": (2 - ALPHA) * ALPHA_P >= 1, "ap>a(2-a)": ALPHA_P > ALPHA * (2 - ALPHA),
                        "lambda<=s0": lam_c2 <= 1 / (1 - ALPHA), "s0_over_lambda": (1 / (1 - ALPHA)) / lam_c2},
            "C_alpha<=0.5": ALPHA <= 0.5,
            "cor5_3_proviso_at_mu_2beta": {"needs_ap_ge": (2 + ALPHA - ALPHA ** 2) / (2 * (2 - ALPHA)),
                                           "holds": ALPHA_P >= (2 + ALPHA - ALPHA ** 2) / (2 * (2 - ALPHA))},
            "chi": (2 - ALPHA) * ALPHA_P - ALPHA},
        "H_star_beta_over_lambda_plus_tau": f_beta,
        "prewarm_switch_cost_over_beta_tilde": bw_full,
        "H_star_mu_over_lambda": coef,
        "rows": rows,
        "max_load_s_with_rho_le_2": {k: (TAU + h) / f_beta for k, h in NOTICES.items()},
        "max_load_s_with_rho_le_2_slot_5min": {k: (SLOW_SLOT + SLOW_SLOT * (h // SLOW_SLOT)) / f_beta
                                               for k, h in NOTICES.items()},
        "lambda_s_above_which_H_star_mu_lt_H_star_beta": cross,
        "spare_threshold": {"rule": "spare pays if n_exp > alpha / (nu lambda) (design §3.2.6)",
                            "nu_per_day_median_over_maas_clusters_by_lease_size": nu, "nu_per_day_used": nu_max,
                            "lambda_s": lam_spare, "nu_lambda": nu_max * lam_spare / 86400,
                            "n_exp_threshold": ALPHA / (nu_max * lam_spare / 86400)},
    }
    print(json.dumps({k: res[k] for k in ("H_star_mu_over_lambda", "max_load_s_with_rho_le_2",
                                          "lambda_s_above_which_H_star_mu_lt_H_star_beta", "spare_threshold")}, indent=1))
    for r in rows:
        print(f'{r["lambda_s"]:8.1f} s  H*_beta={r["H_star_beta_s"] / 60:7.2f} min  rho=' +
              " / ".join(f"{v:.2f}" for v in r["rho"].values()) + "  H*_mu(beta~)=" +
              " / ".join(f"{v / 60:.2f}" for v in r["H_star_mu_s"]["switch_beta_tilde"].values()) + " min" +
              f'  | 5-min slot: H*_beta={r["slot_5min"]["H_star_beta_s"] / 60:7.2f} min  rho=' +
              " / ".join(f"{v:.2f}" for v in r["slot_5min"]["rho"].values()))
    save_json("a5b_exposure_thresholds.json", res)


if __name__ == "__main__":
    main()
