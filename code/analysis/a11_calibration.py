"""MS0 calibration tables: load time, core loading cost, stranding cost, revocation exposure, notice thresholds and
individually rational (IR) contract prices per LLM tier, load-time scenario and contract of the default menu
(design/Sublet_design.md §1.5.3, §1.6, §3.6, §5.3.5, Table 3.8; open decisions Q24, Q25, Q29, Q30).

No raw trace is read. Inputs:
  catalog     MaaS entries of a10_maas_catalog.json (`proposed_catalog.entries`): default S, M, L (instance-hour
              medians: params_b over all online instances of the tier, g = gpu_count over fused instances, i.e. GPUs
              per replica weighted by replica time; L with 8-bit weights, because 16-bit weights do not fit on
              8 x 80 GB) and the sensitivity entries M_g_gpu_hours (g = 2, GPU-hour weighting), L_16bit (g = 16,
              memory-derived) and L_g4 (235B on 4 GPUs); the a5 Llama-3 tiers (a5_reclaim_cost_calibration.json
              `assumptions`) as the sensitivity catalog (Q30). GPUs are priced as H100-80GB, so every entry must
              satisfy w <= 0.9 x 80 GB x g (a5's usable HBM; asserted).
  load time   lambda = w / bw + t_init (design §1.5.3) in eight scenarios whose bw and t_init come from verified
              literature summaries or from a5's assumptions (SCENARIOS below; each has its source string).
  prices      a0 = 2.85, q_GPU = 7.15, protected 5.97 USD/GPU-h (a5b constants;
              literature/sources/gpu-rental-prices-h100-2026-10.md); IR price a_lk = a0 / (1 - b_l(D)) (design §1.5.2),
              with b_l(D) the P99 notice buffer of lender l over window D: a9_notice_buffer.buffer_curve on the a1/a2
              slack series, the running maximum over all 5-min windows up to D (the function the MS1 simulator,
              not yet written, is to use; design §5.2.2). Sample size: the MaaS series cover one week, so for
              D >= 120 min the P99 of many clusters rests on a single drop episode (a9b); `ir_summary` counts them
              per contract.
  model       beta_jl = 0, phi = 1, q_j = g q_GPU (fallback on hyperscaler GPUs of equal throughput, design §1.5.4).
  C2 status   code/theory_checks/c2/audit/out/model_switch_cost_default.txt (exact-game brackets at the default prices)
              and switch_cost_crossover.txt (breakpoints of the C2-SW formula), outputs of model_switch_cost_default.py
              and switch_cost_crossover.py, which read a5b's JSON (analysis/run_all.sh runs them between a5b and a11).
Outputs (out/a11_calibration.json): `load_time_s` per catalog, tier and scenario; `contracts` with the windows, the IR
summary and, per price reference (a0, MaaS median and max, spot L7 median), the price, alpha_k, f_beta, the C2
conditions, H*_mu / lambda with status, the largest load with rho <= 2 and the crossover load of H*_mu and H*_beta;
`ir_prices_by_lender`; `rows` (every tier x scenario x default-slot contract at the MaaS-median price);
`table_3_8_by_tier`; `condition_C_at_IR_prices` (window from which alpha_k > 1/2 per lender); `checks`.
Definitions (design §1.5.3, §1.6), with alpha_k = a / q_GPU and f = 1 + phi / alpha_k:
  beta~   = beta_jl + lambda (g a + phi g q_GPU)         [USD per load]
  mu      = (mu/beta~) beta~, mu/beta~ in {0.2, 0.5, 1, 2}  [USD per move of a fully loaded replica]
  rho     = 1 + beta~ / (g a D_pd) = 1 + f lambda / D_pd
  H*_beta = beta~ / (g a) - tau = f lambda - tau
  H*_mu   = (H*_mu / lambda) lambda from a5b's c2_hstar at alpha_k: the simple form mu/(2(q_j - g a)) where its conditions
            hold, the C2-SW formula otherwise; each value carries a status label (PROVEN / VERIFIED NUMERICALLY /
            CONJECTURE) in `contracts.<k>.price_refs.<ref>.H_star_mu_over_lambda`.
Contract windows: the platform's window D_pd counts sub-slot notices as 0 at the 5-min slow-loop slot (design §1.5.1):
D_pd = tau + slot * floor(H / slot); at the 1-min slot of the sensitivity run D_pd = tau + H. The lender's buffer
window D_lender follows a9's convention (a window of h slots spans slot levels t..t+h): 5 * floor(D / 5) when leases
start on 5-min slot boundaries (default slot) and 5 * ceil(D / 5) when they start on 1-min boundaries.

Checks (`checks`): (1) the a0 rows against a5b_exposure_thresholds.json, split into values a11 recomputes itself
(rho, H*_beta, max load, lambda) and values that come from the same a5b function on both sides (H*_mu, its
coefficients and crossovers: plumbing only); (1b) every H*_mu / lambda value against an independent implementation
of the C2-T4 / C2-SW formulas (design/theory/c2_single_site.md §6 and "Switch cost"); (2) the buffers equal
a9b_notice_buffer_24h.json at its grid windows; (3) the a0 H*_mu values lie in the exact-game brackets of
c2/audit/out/model_switch_cost_default.txt, whose header prices must equal a5b's (asserted): lo < H*_mu <= hi at full
precision, with the bracket ends read from the file's full-precision block (`exact_full_precision`); a value is
labeled VERIFIED only if every bracket check passes and the file reports agreement at all of its points; (4) the simple form equals the formula wherever its conditions hold;
(5) the scenario rates reproduce their literature anchors; (6) the prices of c2/out/por_default.json (Table PoR at the
default prices, cited next to these tables in the design) equal a5b's (asserted). The C2 audit files are inputs: after
a price change run a5b, then c2/audit model_switch_cost_default.py and switch_cost_crossover.py, then this script
(run_all.sh), and rerun c2/por_default.py (about 20 min; c2/audit/run_all.sh runs it), which run_all.sh does not.
"""
import json
import math
import os
import re

import numpy as np

from a5b_exposure_thresholds import (A0, ALPHA, ALPHA_P, A_P, MU_RATIOS, NOTICES, PHI, Q_GPU, SLOW_SLOT, TAU,
                                     c2_hstar, hstar_mu_coefs, load_points)
from a9_notice_buffer import SLOT_MIN, buffer_curve, drops, lenders, tail_episodes
from common import HERE, OUT, save_json

PRICE_GPU_GB = 80   # GPUs priced as H100-80GB
HBM_USABLE = 0.9    # a5_reclaim_cost_calibration.py: kv_cap = 0.9 x replica HBM - weights

BETA_JL = 0.0  # one-off load charges (design Table 3.6, Table 5.6 default)
H_MENU_MIN = (0, 1, 2, 5, 10, 15, 30, 60, 120, 240)  # design Table 3.7 contract menu
SLOTS_MIN = (5, 1)  # default slow-loop slot, 1-min sensitivity run (design §1.5.1)
TAU_1H_MIN = 60
DEFAULT_SWITCH = "switch_full_model_C2SW_conjecture"
ROW_REF = "maas_p99_median"  # default price reference of the rows
QS = ("p99", "p99.9")  # default buffer quantile and the sweep value (design Table 5.6)
MAAS = lambda n: n.startswith("a2:")
SPOT_L7 = ("a1:A100-SXM4-80GB", "a1:H800", "a1:A800-SXM4-80GB", "a1:GPU-series-2")  # design L7, as in a9b
C2_AUDIT = os.path.join(HERE, "..", "theory_checks", "c2", "audit", "out")
GBIT = 0.125  # GB/s per Gb/s

FS = "fu2024serverlessllm"
SCENARIOS = {
    # bw in GB/s; per_gpu: each of the g GPUs of a replica receives its 1/g shard over its own link
    "warm_peer_rdma": {
        "bw_GBps": 100 * GBIT, "per_gpu": True, "t_init_s": 0.5, "label": "LITERATURE (rate, t_init); ASSUMPTION (per-GPU shards)",
        "source": "zhang2025blitzscale p. 276 (summary.md): compute fabrics of 100-400 Gbps RDMA (low end used) and "
                  "'typical compute network setups (e.g., 200 Gbps per-GPU)', so each GPU loads its shard over its "
                  "own link; t_init = CUDA context about 500 ms (zhang2025blitzscale §A.1, p. 293)",
        "anchors": "Mistral-24B to 6 prefill instances in 1.2 s (zhang2025blitzscale Fig. 21, p. 287); Llama-13B to 8 "
                   "nodes in < 1 s (yu2025lambdascale p. 2)"},
    "ssd_optimized": {
        "bw_GBps": 130 / 10.3, "per_gpu": False, "t_init_s": 0.0, "label": "LITERATURE (rate); load only",
        "source": f"{FS}: LLaMA-2-70B (130 GB, p. 137) loads in 10.3 s from RAID0 NVMe (12 GB/s) with the ServerlessLLM "
                  "loader (Fig. 6a, p. 144); checkpoint loading latency only, no engine start (§7.2, p. 144); scaled "
                  "linearly in weight size (OPT-2.7B to OPT-66B: 0.5-10.0 s, Fig. 6a)",
        "anchor": {"w_GB": 130, "lambda_s": 10.3}},
    "ssd_stock_safetensors": {
        "bw_GBps": 130 / 48.0, "per_gpu": False, "t_init_s": 0.0, "label": "LITERATURE (rate); load only",
        "source": f"{FS}: LLaMA-2-70B (130 GB, p. 137) with Safetensors from local SSD: 48.0 s (Fig. 6a, p. 144)",
        "anchor": {"w_GB": 130, "lambda_s": 48.0}},
    "ssd_stock_pytorch": {
        "bw_GBps": 130 / 84.0, "per_gpu": False, "t_init_s": 0.0, "label": "LITERATURE (rate); load only",
        "source": f"{FS}: LLaMA-2-70B (130 GB, p. 137) with PyTorch from local NVMe: 84 s (p. 137; Fig. 6a, p. 144)",
        "anchor": {"w_GB": 130, "lambda_s": 84.0}},
    "a5_10GBps": {
        "bw_GBps": 10.0, "per_gpu": False, "t_init_s": 60.0, "label": "ASSUMPTION (a5 model); default pair with a5_2GBps (Q24)",
        "source": "a5_reclaim_cost_calibration.json assumptions.weight_load_gbps_GBps (10, local NVMe cache) and "
                  "assumptions.engine_init_s (60)"},
    "a5_2GBps": {
        "bw_GBps": 2.0, "per_gpu": False, "t_init_s": 60.0, "label": "ASSUMPTION (a5 model); default pair with a5_10GBps (Q24)",
        "source": "a5_reclaim_cost_calibration.json assumptions.weight_load_gbps_GBps (2, remote object store) and "
                  "assumptions.engine_init_s (60)"},
    "cold_wan_10gbps": {
        "bw_GBps": 10 * GBIT, "per_gpu": False, "t_init_s": 0.0, "label": "LITERATURE (link rate); lower bound at line rate",
        "source": f"10 Gbps cluster network of {FS} (Fig. 10a, p. 146), where stock Ray Serve needed 213 s to start "
                  "OPT-30B (p. 147); line rate, no engine start, so a lower bound"},
    "cold_wan_1gbps": {
        "bw_GBps": 1 * GBIT, "per_gpu": False, "t_init_s": 0.0, "label": "LITERATURE (link rate); lower bound at line rate",
        "source": "yu2025lambdascale p. 3: Llama-70B (140 GB) from a remote registry over 1 Gbps takes > 18 min; "
                  f"{FS} p. 148: KServe downloads OPT-6.7B over 1 Gbps in 114 s (first token 128 s); line rate, no "
                  "engine start, so a lower bound",
        "anchor": {"w_GB": 140, "lambda_s_lower_bound": 18 * 60.0}},
}
SOURCES = {
    "a0, q_GPU, a_p": "literature/sources/gpu-rental-prices-h100-2026-10.md (Silicon Data H100 index 2026-10-14: neo-cloud "
                      "2.85, hyperscaler 7.15 USD/GPU-h; AWS Capacity Blocks p5 5.97 USD/GPU-h); constants A0, Q_GPU, A_P "
                      "of a5b_exposure_thresholds.py",
    "phi": "ASSUMPTION 1 (design Table 3.6; a5b PHI)",
    "beta_jl": "ASSUMPTION 0 (design Table 3.6, Table 5.6)",
    "q_j": "q_j = g q_GPU: fallback on hyperscaler GPUs of equal throughput (design §1.5.4, §5.3.5)",
    "mu_over_beta_tilde": "ASSUMPTION, swept {0.2, 0.5, 1, 2} (design §1.5.5, Table 5.6, Q23; a5b MU_RATIOS)",
    "contract menu": "ASSUMPTION: H in {0, 1, 2, 5, 10, 15, 30, 60, 120, 240} min, tau in {1 slot, 1 h}, plus one "
                     "protected contract (design Table 3.7; Q29); slot 5 min by default, 1 min in the sensitivity run "
                     "(design §1.5.1)",
    "buffers": "a9_notice_buffer.buffer_curve on out/a1_slack_series.npz and out/a2_slack_series.npz (MEASURED; MaaS "
               "slack derived from allocation), quantile P99 (P99.9 as the sweep value), b_l(D) = running maximum of "
               "the raw quantile over all 5-min windows up to D (a9b `b_envelope_5min`; a9b `b_envelope` is the "
               "envelope over its 9-point grid only). Sample size: the MaaS series cover one week (2016 slots), so for "
               "D >= 120 min the P99 of many clusters is set by a single drop episode and lies just below the largest "
               "drop in the sample: at D = 60, 120, 240 and 480 min the P99 of {ep60}, {ep120}, {ep240} and {ep480} "
               "of the 20 clusters rests on a single drop episode, and the median ratio of P99 to the largest drop is "
               "{r120:.3f} at 120 min and {r240:.3f} at 240 min (a9b summary.maas_20_clusters.windows.<D>); per "
               "contract see contracts.<k>.ir_summary.maas_p99_tail_episodes",
    "IR price": "a_lk = a0 / (1 - b_l(D_lender)), offered only if b < 1 (design §1.5.2, §5.3.5)",
    "H*_mu": "a5b_exposure_thresholds.c2_hstar (C2-T4 formula; C2-SW substitution for a switch cheaper than beta~), "
             "status from c2/audit/out/model_switch_cost_default.txt and c2/audit/out/switch_cost_crossover.txt",
    "catalog": "a10_maas_catalog.json proposed_catalog.entries.<entry>.{params_b, g, precision, w_GB} (params_b and g "
               "MEASURED on the trace's GPU mix, instance-hour-weighted medians, params_b over all online instances of "
               "the tier and g over fused instances; their use on H100-80GB GPUs is an ASSUMPTION; precision ASSUMED: "
               "16-bit where the weights fit in 0.9 x 80 GB x g, 8-bit otherwise) and proposed_catalog.tiers.<S|M|L> "
               "for the shares",
    "a5 catalog": "a5_reclaim_cost_calibration.json assumptions.weights_gb and assumptions.replica_hbm_GB / 80 GB per H100",
    "fit": "every catalog entry has w_GB <= 0.9 x 80 GB x g (H100-80GB price unit; a5's usable HBM share), asserted",
}
STATUS = {
    "PROVEN-Cor5": "PROVEN (C2-Cor5, simple form) with switch cost beta~, for tau = 0; beta~ is not the switch cost of "
                   "the full model (design §1.7.1 item 13)",
    "PROVEN-T4": "PROVEN (C2-T4 under (C')) with switch cost beta~, for tau = 0; beta~ is not the switch cost of the full "
                 "model (design §1.7.1 item 13)",
    "VERIFIED": "VERIFIED NUMERICALLY: the exact game at the default prices (alpha = 0.3986) agrees with the formula "
                "(c2/audit/out/model_switch_cost_default.txt, bracket in `exact_bracket_over_lambda`); formula "
                "CONJECTURE, no proof (Q17); tau = 0",
    "CONJECTURE": "CONJECTURE: C2-SW formula at this alpha_k; the exact game ran only at alpha = 0.3986; tau = 0",
    "NA-Cprime": "not applicable: (C') fails, so up-front insurance attains 2 - alpha at every H (design §1.7.1 item 8)",
    "+C-fails": "suffix: (C) fails (alpha_k > 1/2), so no closed form of C2-Cor5 is proven even with switch cost beta~",
}
FIELD_SOURCES = {
    "lambda_s": "load_time_s.<catalog>.<tier>.<scenario>: w / (bw * (g if per-GPU shards else 1)) + t_init (design §1.5.3)",
    "a (price)": "contracts.<k>.price_refs.<ref>.a_usd_per_gpu_h: a0 times the IR multiplier of the price reference",
    "beta_tilde_usd": "beta_jl + lambda (g a + phi g q_GPU), lambda in hours (design §1.5.3)",
    "mu_usd": "(mu/beta~) beta~ for mu/beta~ in {0.2, 0.5, 1, 2}",
    "rho": "1 + beta~ / (g a D_pd) = 1 + f lambda / D_pd (design §1.6); 1 for the protected contract",
    "rho_le_2": "rho <= 2, i.e. H in the platform's window accounting >= H*_beta (design §1.6)",
    "H_star_beta_s": "beta~ / (g a) - tau = f lambda - tau (design §1.6); null for the protected contract",
    "H_star_mu_s": "contracts.<k>.price_refs.<ref>.H_star_mu_over_lambda.by_switch.<default switch>.<mu>.value times "
                   "lambda; null where C2 does not apply; status codes in H_star_mu_status_legend",
}


def lam_s(w_gb, g, sc):
    s = SCENARIOS[sc]
    return w_gb / (s["bw_GBps"] * (g if s["per_gpu"] else 1)) + s["t_init_s"]


def menu():
    """Contracts of the default menu (both slot lengths) plus the protected contract."""
    out = {}
    for slot in SLOTS_MIN:
        for tau in (slot, TAU_1H_MIN):
            for H in H_MENU_MIN:
                D = tau + H
                cls = ("GFS-like" if tau == TAU_1H_MIN and H == 0 else
                       "spot-like" if tau == slot and H <= 2 else
                       "AEP-82-like" if tau == slot and H >= 60 else "general")
                out[f"s{slot}_tau{tau}_H{H}"] = {
                    "slot_min": slot, "tau_min": tau, "tau": "1 slot" if tau == slot else "1 h", "H_min": H,
                    "class": cls, "D_exact_min": D, "D_pd_min": tau + slot * (H // slot),
                    "D_lender_min": SLOT_MIN * (D // SLOT_MIN if slot == SLOT_MIN else math.ceil(D / SLOT_MIN))}
    out["protected"] = {"class": "protected", "note": "never reclaimed (tau >= T); price a_p, no IR premium"}
    return out


def buffers(Dmax):
    """b_l(D) for every lender and every 5-min window up to Dmax, raw and as a running-maximum envelope (a9)."""
    grid = list(range(SLOT_MIN, Dmax + 1, SLOT_MIN))
    return grid, {name: dict(buffer_curve(s, Dmax), series=s) for name, s in lenders()}


def p99_episodes(bl, D):
    """Tail episodes behind lender bl's P99 envelope at window D, counted at the window D* <= D attaining it."""
    Ds = bl["argmax"][D]["p99"]
    d = drops(bl["series"], Ds)
    n_win, n_ep = tail_episodes(d, np.percentile(d, 99), Ds // SLOT_MIN)
    return {"envelope_window_min": Ds, "n_tail_windows": n_win, "n_tail_episodes": n_ep,
            "p99_over_max_drop": float(np.percentile(d, 99) / d.max()) if d.max() > 0 else None}


def hstar_independent(a, ap, mu, lam, bw, b=1.0):
    """H* of C2 in beta~ units, written from design/theory/c2_single_site.md §6 (Theorem 4) and its "Switch cost"
    paragraph (C2-SW: bw substituted in OPT's pre-warm branch L3 and in the warm terms), independently of a5b."""
    kappa = (2 - a) * ap - a
    s0 = b / (1 - a)
    r_wait = (2 - a) * b / (1 - a) ** 2

    def ratio(x, y):  # x/0 = +inf for x > 0, -inf for x <= 0
        return x / y if y != 0 else (math.inf if x > 0 else -math.inf)

    def H(r):
        return r - s0 if r <= r_wait else r

    r_cold = max(s0 + mu / (2 * (1 - a)), ratio(mu + a * b - (2 - a) * bw, a * (1 - a)), (mu + a * b) / kappa)
    warm = [s0 + bw / (2 * (1 - a)), (a * b + bw) / kappa]
    if lam > 0:
        warm.append(lam + ratio(a * b + bw, a * (1 - a)))
    return min(H(r_cold), max(lam, H(max(warm))))


def ir_mult(b):
    return float(1.0 / (1.0 - b)) if b < 1 else None


def parse_exact_brackets():
    """Exact-game brackets of H*_mu / lambda at the default prices (model_switch_cost_default.txt).

    The file is an output of the C2 audit, computed from a5b's prices; its header prices must equal a5b's."""
    path = os.path.join(C2_AUDIT, "model_switch_cost_default.txt")
    txt = open(path).read()
    hdr = re.search(r"alpha=([\d.]+) alpha_p=([\d.]+) phi=([\d.]+)", txt)
    assert hdr, "no price header in model_switch_cost_default.txt"
    al, ap, ph = map(float, hdr.groups())
    assert abs(al - ALPHA) < 5e-7 and abs(ap - ALPHA_P) < 5e-7 and ph == PHI, (
        f"stale C2 audit output: alpha={al}, alpha_p={ap}, phi={ph} vs a5b {ALPHA}, {ALPHA_P}, {PHI}; rerun "
        "c2/audit/model_switch_cost_default.py and switch_cost_crossover.py after a5b")
    pat = re.compile(r"^bw=([\d.]+) mu=([\d.]+): formula ([\d.]+) lam \(a5b ([\d.]+)\) exact \(([\d.]+), ([\d.]+)\] lam",
                     re.M)
    out = {}
    for bw, mu, f, _, lo, hi in pat.findall(txt):
        sw = "switch_beta_tilde" if abs(float(bw) - 1) < 1e-9 else DEFAULT_SWITCH
        out[(sw, str(float(mu)))] = {"formula_over_lambda_3dp": float(f), "exact_bracket_over_lambda": [float(lo), float(hi)]}
    m = re.search(r"summary: (\d+) of (\d+) exact thresholds equal", txt)
    assert m and m.group(1) == m.group(2) and len(out) == 8, "unexpected model_switch_cost_default.txt"
    num = r"([0-9.eE+-]+)"
    full = re.findall(rf"^full bw={num} mu={num}: formula {num} exact \({num}, {num}\]$", txt, re.M)
    assert len(full) == 8, ("no exact_full_precision block in model_switch_cost_default.txt; rerun "
                            "c2/audit/model_switch_cost_default.py")
    for bw, mu, f, lo, hi in full:
        sw = "switch_beta_tilde" if abs(float(bw) - 1) < 1e-9 else DEFAULT_SWITCH
        out[(sw, str(float(mu)))]["exact_full_precision"] = {"formula_over_lambda": float(f),
                                                             "bracket_over_lambda": [float(lo), float(hi)]}
    return out, f"{int(m.group(1))} of {int(m.group(2))} points"


def parse_crossover():
    """Breakpoints of the C2-SW formula at the default calibration (switch_cost_crossover.txt, first block)."""
    txt = open(os.path.join(C2_AUDIT, "switch_cost_crossover.txt")).read()
    hdr = re.search(r"alpha=([\d.]+) alpha_p=([\d.]+)", txt)
    assert hdr and abs(float(hdr.group(1)) - ALPHA) < 5e-7 and abs(float(hdr.group(2)) - ALPHA_P) < 5e-7, \
        "stale switch_cost_crossover.txt (prices differ from a5b)"
    head = f"lambda={1 / (ALPHA + PHI):.4f} bw={ALPHA_P / (ALPHA + PHI):.4f} (default calibration)"
    assert head in txt, f"stale switch_cost_crossover.txt: no block '{head}'"
    block = txt.split(head, 1)[1].split("\n\n", 1)[0]
    two_bw = float(re.search(r"2 bw = ([\d.]+)", block).group(1))
    marks = re.findall(r"mu >= ([\d.]+): (simple form|above simple form), (cold|pre-warm), (sit-out|known window)", block)
    return {"source": "c2/audit/out/switch_cost_crossover.txt (formula, CONJECTURE)",
            "simple_form_holds_for_mu_over_beta_tilde_le": two_bw,
            "breakpoints": [{"mu_over_beta_tilde_from": float(a), "form": b, "reaction": c, "regime": d} for a, b, c, d in marks]}


def c_conditions(a):
    cp = {"alpha<1": a < 1, "(2-a)ap>=1": (2 - a) * ALPHA_P >= 1, "ap>a(2-a)": ALPHA_P > a * (2 - a)}
    return {"C_prime": all(cp.values()), "C_prime_parts": cp, "C": all(cp.values()) and a <= 0.5}


def hstar_mu_entries(a, is_default_price, exact, violations):
    """H*_mu / lambda per switch convention and mu/beta~ at lease price ratio a, with form and status labels."""
    cond = c_conditions(a)
    if a >= 1:
        return cond, None
    coefs = hstar_mu_coefs(alpha=a)  # a5b
    bw_def = ALPHA_P / (a + PHI)
    chi, s0 = (2 - a) * ALPHA_P - a, 1 / (1 - a)
    out = {}
    for sw, c in coefs.items():
        bw = 1.0 if sw == "switch_beta_tilde" else bw_def
        out[sw] = {}
        for m, v in c.items():
            mu = float(m)
            simple = mu * (a + PHI) / (2 * (1 - a))  # mu / (2 (1 - a)) in C2 units, over lambda = 1 / (a + phi)
            if sw == "switch_beta_tilde":
                proviso = (mu + a) / chi <= s0 + mu / (2 * (1 - a))
                simple_cond = cond["C"] and (mu <= 1 or (mu <= 2 and proviso))
            else:
                simple_cond = cond["C"] and mu <= 2 * bw
            e = {"value": v["H_over_lambda"], "reaction": v["reaction"], "regime": v["regime"].split(" (")[0],
                 "form": "simple" if simple_cond else ("C2-T4 formula" if sw == "switch_beta_tilde" else "C2-SW formula")}
            if simple_cond and abs(e["value"] - simple) > 1e-9 * simple:
                violations.append((a, sw, m, e["value"], simple))
            if not cond["C_prime"]:
                e["value"], e["status"] = None, "NA-Cprime"
            elif sw == "switch_beta_tilde":
                e["status"] = "PROVEN-Cor5" if simple_cond else "PROVEN-T4"
            elif is_default_price and (sw, m) in exact:
                e["status"] = "VERIFIED"
                e["exact_bracket_over_lambda"] = exact[(sw, m)]["exact_bracket_over_lambda"]
            else:
                e["status"] = "CONJECTURE"
            if cond["C_prime"] and not cond["C"]:
                e["status"] += " +C-fails"
            out[sw][m] = e
    return cond, {"prewarm_switch_over_beta_tilde": bw_def, "by_switch": out}


def price_refs(k, c, buf, maas, spot):
    """Price references of contract k: a0, MaaS median and max, spot L7 median (P99 envelope)."""
    if k == "protected":
        return {"protected": {"multiplier": None, "a_usd_per_gpu_h": A_P, "source": SOURCES["a0, q_GPU, a_p"]}}
    D = c["D_lender_min"]
    mm = [ir_mult(buf[n]["env"][D]["p99"]) for n in maas]
    sp = [ir_mult(buf[n]["env"][D]["p99"]) for n in spot]
    med = lambda xs: (lambda v: None if not np.isfinite(v) else float(v))(np.median([np.inf if x is None else x for x in xs]))
    refs = {"a0": {"multiplier": 1.0, "source": "base price a0, no IR premium (a5b default; upper bound on rho)"},
            "maas_p99_median": {"multiplier": med(mm), "n_offering": sum(x is not None for x in mm), "n_lenders": len(mm),
                                "source": f"median over the {len(mm)} MaaS clusters of 1/(1 - b_envelope_p99(D_lender))"},
            "maas_p99_max": {"multiplier": None if None in mm else max(mm), "argmax": maas[int(np.argmax(mm))] if None not in mm else None,
                             "source": "largest MaaS cluster multiplier (P99 envelope)"},
            "spot_L7_p99_median": {"multiplier": med(sp), "n_offering": sum(x is not None for x in sp), "n_lenders": len(sp),
                                   "source": "median over the 4 L7 spot pools, a pool that cannot offer counts as infinite"}}
    for r in refs.values():
        r["a_usd_per_gpu_h"] = None if r["multiplier"] is None else A0 * r["multiplier"]
    return refs


def calib_row(lam, g, c, ref):
    """lambda, beta~, mu, rho, H*_beta, H*_mu of one (tier, scenario, contract, price) cell."""
    a = ref["a_usd_per_gpu_h"]
    if a is None:
        return {"offered": False}
    bt = BETA_JL + lam / 3600 * (g * a + PHI * g * Q_GPU)
    row = {"beta_tilde_usd": bt, "mu_usd": {str(m): m * bt for m in MU_RATIOS}}
    if "D_pd_min" not in c:  # protected: never reclaimed
        row.update({"rho": 1.0, "rho_le_2": True, "H_star_beta_s": None, "H_star_mu_s": None})
        return row
    assert BETA_JL == 0  # rho and H*_beta below use f lambda = beta~ / (g a)
    f, tau_s, slot_s = ref["f_beta"], 60.0 * c["tau_min"], 60.0 * c["slot_min"]
    D = tau_s + slot_s * ((60.0 * c["H_min"]) // slot_s)
    rho = 1 + f * lam / D
    hm = ref.get("H_star_mu_over_lambda")
    row.update({"rho": rho, "rho_le_2": rho <= 2, "H_star_beta_s": f * lam - tau_s,
                "H_star_mu_s": None if hm is None else
                {m: (None if e["value"] is None else e["value"] * lam) for m, e in hm["by_switch"][DEFAULT_SWITCH].items()}})
    return row


def main():
    a10 = json.load(open(f"{OUT}/a10_maas_catalog.json"))["proposed_catalog"]
    a5 = json.load(open(f"{OUT}/a5_reclaim_cost_calibration.json"))
    a9b = json.load(open(f"{OUT}/a9b_notice_buffer_24h.json"))
    a5b = json.load(open(f"{OUT}/a5b_exposure_thresholds.json"))
    ep = a9b["summary"]["maas_20_clusters"]["windows"]
    SOURCES["buffers"] = SOURCES["buffers"].format(
        **{f"ep{D}": ep[str(D)]["p99_tail_episodes"]["n_lenders_with_one_episode"] for D in (60, 120, 240, 480)},
        r120=ep["120"]["median_p99_over_max_drop"], r240=ep["240"]["median_p99_over_max_drop"])

    # exact-game brackets at the default prices (C2 audit output, header prices asserted equal to a5b's); a value is
    # labeled VERIFIED only if every a0 formula value lies in its bracket (check 3): lo < H*_mu/lambda <= hi at full
    # precision, with a relative tolerance of 1e-9 at the upper end for floating-point rounding where the formula
    # falls exactly on a grid point (mu = 2, switch beta~: H*_mu = s0, which the solver puts on its grid)
    exact_all, exact_n = parse_exact_brackets()
    coef0 = hstar_mu_coefs(alpha=A0 / Q_GPU)
    br = []
    for (sw, m), v in exact_all.items():
        f = coef0[sw][m]["H_over_lambda"]
        lo, hi = v["exact_full_precision"]["bracket_over_lambda"]
        br.append({"switch": sw, "mu_over_beta_tilde": m, "formula": f, "bracket": [lo, hi],
                   "bracket_3dp": v["exact_bracket_over_lambda"],
                   "audit_formula": v["exact_full_precision"]["formula_over_lambda"],
                   "inside_full_precision": lo < f <= hi * (1 + 1e-9)})
    brackets_ok = all(x["inside_full_precision"] for x in br)
    exact = exact_all if brackets_ok else {}

    # catalogs; GPUs are priced as H100-80GB, so every entry must fit on its g GPUs with KV room
    pc, t = a10["entries"], a10["tiers"]
    entries = a10["default_entries"] + a10["sensitivity_entries"]
    usable = all(pc[k]["params_b"] and pc[k]["g"] >= 1 and pc[k]["w_GB"] for k in entries)
    cat = {"maas_a10": {k: {"params_b": pc[k]["params_b"], "g": int(pc[k]["g"]), "w_GB": pc[k]["w_GB"],
                            "precision": pc[k]["precision"], "tier": k[0],
                            "role": "default" if k in a10["default_entries"] else "sensitivity",
                            "share_allocated_gpu_hours": t[k[0]]["share_allocated_gpu_hours"],
                            "share_instance_hours": t[k[0]]["share_instance_hours"], "moe_share": t[k[0]]["moe_share"],
                            "source": f"a10_maas_catalog.json proposed_catalog.entries.{k} ({pc[k]['basis']}; params_b "
                                      f"and g MEASURED, precision ASSUMED)"} for k in entries}}
    A = a5["assumptions"]
    cat["a5_llama3"] = {k: {"g": int(A["replica_hbm_GB"][k] / 80), "w_GB": A["weights_gb"][k], "precision": "16-bit",
                            "source": f"a5_reclaim_cost_calibration.json assumptions.weights_gb.{k}, replica_hbm_GB.{k} / 80"}
                        for k in A["weights_gb"]}
    fit = {}
    for cn, cv in cat.items():
        for tn, tv in cv.items():
            room = HBM_USABLE * PRICE_GPU_GB * tv["g"] - tv["w_GB"]
            assert room >= 0, f"{cn}:{tn}: {tv['w_GB']} GB of weights do not fit on {tv['g']} x {PRICE_GPU_GB} GB"
            fit[f"{cn}:{tn}"] = {"w_GB": tv["w_GB"], "g": tv["g"], "kv_room_GB": room}
    lam = {cn: {tn: {sc: lam_s(tv["w_GB"], tv["g"], sc) for sc in SCENARIOS} for tn, tv in cv.items()}
           for cn, cv in cat.items()}

    # contracts, buffers, IR prices
    K = menu()
    Dmax = max(c["D_lender_min"] for c in K.values() if "D_lender_min" in c)
    grid, buf = buffers(Dmax)
    names = list(buf)
    maas = [n for n in names if MAAS(n)]
    spot = [n for n in names if n in SPOT_L7]
    ir_table = {n: {"group": "maas" if MAAS(n) else ("spot_L7" if n in SPOT_L7 else "spot_other"),
                    "contracts": {k: {"b_envelope_5min": {q: buf[n]["env"][c["D_lender_min"]][q] for q in QS},
                                      "ir_multiplier": {q: ir_mult(buf[n]["env"][c["D_lender_min"]][q]) for q in QS}}
                                  for k, c in K.items() if k != "protected"}} for n in names}
    sf_bad = []  # simple form != formula although its conditions hold (check 4)
    for k, c in K.items():
        refs = price_refs(k, c, buf, maas, spot)
        for rn, r in refs.items():
            a = r["a_usd_per_gpu_h"]
            if a is None or k == "protected":
                continue
            al = a / Q_GPU
            r["alpha_k"], r["f_beta"] = al, 1 + PHI / al
            cond, hm = hstar_mu_entries(al, rn == "a0", exact, sf_bad)
            r["conditions"], r["H_star_mu_over_lambda"] = cond, hm
            D_s = 60.0 * c["tau_min"] + 60.0 * c["slot_min"] * ((60.0 * c["H_min"]) // (60.0 * c["slot_min"]))
            r["max_lambda_s_with_rho_le_2"] = D_s / r["f_beta"]
            if hm is not None:
                r["lambda_s_above_which_H_star_mu_lt_H_star_beta"] = {
                    m: (None if e["value"] is None else (60.0 * c["tau_min"] / (r["f_beta"] - e["value"])
                                                         if e["value"] < r["f_beta"] else None))
                    for m, e in hm["by_switch"][DEFAULT_SWITCH].items()}
        c["price_refs"] = refs
        if k != "protected":
            D = c["D_lender_min"]
            c["ir_summary"] = {}
            for q in QS:
                mm = [ir_mult(buf[n]["env"][D][q]) for n in maas]
                ok = [x for x in mm if x is not None]
                c["ir_summary"][f"maas_{q}"] = {"n_offering": len(ok), "median": float(np.median(ok)) if ok else None,
                                                "min": min(ok) if ok else None, "max": max(ok) if ok else None}
                c["ir_summary"][f"spot_L7_{q}"] = {n: ir_mult(buf[n]["env"][D][q]) for n in spot}
            eps = {n: p99_episodes(buf[n], D) for n in maas}
            pos = [e for e in eps.values() if e["n_tail_episodes"] is not None]
            amax = refs["maas_p99_max"].get("argmax")
            c["ir_summary"]["maas_p99_tail_episodes"] = {
                "note": "one-week MaaS series: a P99 with one tail episode is set by a single drop event, the "
                        "largest in the sample, not by a 1% tail",
                "n_lenders_with_one_episode": sum(e["n_tail_episodes"] == 1 for e in pos),
                "n_lenders_with_positive_p99": len(pos),
                "median_p99_over_max_drop": float(np.median([e["p99_over_max_drop"] for e in pos])) if pos else None,
                "maas_p99_max_lender": {"lender": amax, **(eps[amax] if amax else {})}}
            for n in maas:
                ir_table[n]["contracts"][k]["p99_tail_episodes"] = eps[n]

    # rows: catalog -> tier -> scenario -> contract, at the default price reference and the default 5-min slot
    # (other price references and the 1-min slot: contracts.<k>.price_refs coefficients times lambda)
    row_k = [k for k, c in K.items() if c.get("slot_min", SLOTS_MIN[0]) == SLOTS_MIN[0]]
    rows = {cn: {tn: {sc: {"lambda_s": lam[cn][tn][sc], "g": tv["g"],
                           "by_contract": {k: calib_row(lam[cn][tn][sc], tv["g"], K[k],
                                                        K[k]["price_refs"]["protected" if k == "protected" else ROW_REF])
                                           for k in row_k}}
                      for sc in SCENARIOS} for tn, tv in cv.items()} for cn, cv in cat.items()}

    # Table 3.8 per tier (default price reference, default 5-min slot, tau = 1 slot unless stated)
    t38 = {}
    for cn, cv in cat.items():
        t38[cn] = {}
        for tn in cv:
            t38[cn][tn] = {}
            for sc in SCENARIOS:
                R = rows[cn][tn][sc]["by_contract"]
                okH = [H for H in H_MENU_MIN if R[f"s5_tau5_H{H}"].get("rho_le_2")]
                t38[cn][tn][sc] = {
                    "lambda_s": lam[cn][tn][sc], "H_star_beta_s": R["s5_tau5_H0"]["H_star_beta_s"],
                    "rho": {f"H={H}min": R[f"s5_tau5_H{H}"]["rho"] for H in (2, 60, 240)},
                    "rho_tau1h_H0": R["s5_tau60_H0"]["rho"],
                    "min_menu_H_min_with_rho_le_2_tau_1slot": min(okH) if okH else None,
                    "H_star_mu_s": R["s5_tau5_H0"]["H_star_mu_s"]}

    # (C) at the IR prices: alpha_k = a0 / (1 - b(D)) / q_GPU > 1/2 iff b(D) > 1 - 2 a0 / q_GPU; b is
    # non-decreasing in D, so (C) fails for every window at or above the first failing one (5-min grid, D_lender)
    b_c = 1 - 2 * A0 / Q_GPU
    first_fail = {n: next((D for D in grid if buf[n]["env"][D]["p99"] > b_c), None) for n in maas + spot}
    # the MaaS median price is a0 times the median IR multiplier (price_refs), so test that multiplier, not the
    # median buffer (1/(1-b) is convex, so the two medians differ when the 10th and 11th clusters differ)
    med_mult = lambda D: np.median([np.inf if x is None else x for x in (ir_mult(buf[n]["env"][D]["p99"]) for n in maas)])
    med_fail = next((D for D in grid if A0 * med_mult(D) / Q_GPU > 0.5), None)
    worst = min((D, n) for n, D in first_fail.items() if D is not None and n in maas) if any(
        first_fail[n] for n in maas) else (None, None)
    cond_c = {"definition": "smallest lender window D_lender (5-min grid) at which the IR price a0 / (1 - b_p99(D)) "
                            "gives alpha_k > 1/2, i.e. (C) fails; b is the 5-min envelope, so (C) fails for every "
                            "longer window as well",
              "b_threshold": b_c, "by_lender": first_fail,
              "maas_p99_median_price": med_fail,
              "maas_p99_median_price_note": "first window at which a0 x median IR multiplier / q_GPU > 1/2 (the "
                                            "multiplier of price_refs.maas_p99_median); null: none up to the "
                                            "longest menu window",
              "maas_p99_max_price": {"D_lender_min": worst[0], "lender": worst[1],
                                     "p99_tail_episodes_there": p99_episodes(buf[worst[1]], worst[0]) if worst[1] else None},
              "menu_contracts_failing_at_maas_p99_max": sorted(
                  k for k, c in K.items() if k != "protected"
                  and c["price_refs"]["maas_p99_max"].get("conditions", {}).get("C") is False),
              "menu_contracts_failing_at_maas_p99_median": sorted(
                  k for k, c in K.items() if k != "protected"
                  and c["price_refs"]["maas_p99_median"].get("conditions", {}).get("C") is False)}

    # ---------- checks ----------
    # (1) a5b: the a0 price reference against a5b's rows, coefficients and limits. "independent": a11 recomputes the
    # value itself (rho, H*_beta, max load, lambda); "plumbing": both sides come from a5b's c2_hstar (H*_mu values,
    # H*_mu / lambda coefficients, crossover loads), so equality only shows that a11 passes them through unchanged.
    a0_of = lambda k: K[k]["price_refs"]["a0"]
    mism, n_cmp = [], {"independent": 0, "plumbing": 0}
    distinct = {"independent": set(), "plumbing": set()}

    def cmp(kind, key, x, y, *info):
        n_cmp[kind] += 1
        distinct[kind].add((key, y))
        if x != y:
            mism.append((kind, key, *info, x, y))

    hk = {"spot_like_2min": 2, "aep82_min_1h": 60, "h_4h": 240}
    for (name, l), r5 in zip(load_points(), a5b["rows"]):
        for nk, H in hk.items():
            for slot, got_rho, ref_hb in ((1, r5["rho"][nk], r5["H_star_beta_s"]),
                                          (5, r5["slot_5min"]["rho"][nk], r5["slot_5min"]["H_star_beta_s"])):
                k = f"s{slot}_tau{slot}_H{H}"
                mine = calib_row(l, 1, K[k], a0_of(k))
                cmp("independent", ("rho", name, k), mine["rho"], got_rho)
                cmp("independent", ("H_star_beta_s", name, slot), mine["H_star_beta_s"], ref_hb)
                for m, v in r5["H_star_mu_s"][DEFAULT_SWITCH].items():
                    cmp("plumbing", ("H_star_mu_s", name, DEFAULT_SWITCH, m), mine["H_star_mu_s"][m], v, k)
                hb = a0_of(k)["H_star_mu_over_lambda"]["by_switch"]["switch_beta_tilde"]
                for m, v in r5["H_star_mu_s"]["switch_beta_tilde"].items():
                    cmp("plumbing", ("H_star_mu_s", name, "switch_beta_tilde", m), hb[m]["value"] * l, v, k)
    for nk, H in hk.items():
        for slot, key in ((1, "max_load_s_with_rho_le_2"), (5, "max_load_s_with_rho_le_2_slot_5min")):
            cmp("independent", (key, nk), a0_of(f"s{slot}_tau{slot}_H{H}")["max_lambda_s_with_rho_le_2"], a5b[key][nk])
    for sw in ("switch_beta_tilde", DEFAULT_SWITCH):
        for m, v in a5b["H_star_mu_over_lambda"][sw].items():
            cmp("plumbing", ("H_star_mu_over_lambda", sw, m),
                a0_of("s1_tau1_H0")["H_star_mu_over_lambda"]["by_switch"][sw][m]["value"], v["H_over_lambda"])
    for m, v in a5b["lambda_s_above_which_H_star_mu_lt_H_star_beta"][DEFAULT_SWITCH].items():
        cmp("plumbing", ("crossover", m), a0_of("s1_tau1_H0")["lambda_s_above_which_H_star_mu_lt_H_star_beta"][m], v)
    cmp("independent", ("lambda", "llama3-8b@10"), lam["a5_llama3"]["llama3-8b"]["a5_10GBps"], a5b["rows"][2]["lambda_s"])
    cmp("independent", ("lambda", "llama3.1-405b@2"), lam["a5_llama3"]["llama3.1-405b"]["a5_2GBps"],
        a5b["rows"][4]["lambda_s"])
    assert a0_of("s1_tau1_H0")["f_beta"] == a5b["H_star_beta_over_lambda_plus_tau"]
    chk_a5b = {"n_independent_comparisons": n_cmp["independent"],
               "n_independent_distinct_values": len(distinct["independent"]),
               "n_plumbing_comparisons": n_cmp["plumbing"], "n_plumbing_distinct_values": len(distinct["plumbing"]),
               "n_mismatch": len(mism), "mismatches": [str(x) for x in mism[:20]],
               "what": "independent: rho and H*_beta at tau = 1 slot (1 and 5 min) for H = 2, 60, 240 min, max load "
                       "with rho <= 2, and the a5 tier load times (8B at 10 GB/s, 405B at 2 GB/s), recomputed by "
                       "a11; plumbing: H*_mu for both switch conventions, the H*_mu/lambda coefficients and the "
                       "crossover loads, which a11 takes from a5b's c2_hstar (check 1b tests them independently); at "
                       "price a0 for a5b's six load times"}

    # (1b) every H*_mu / lambda value (all contracts, price references and switch conventions) against an independent
    # implementation of the C2 formulas; H*_mu / lambda = H*(beta~ units) (alpha_k + phi) at lambda = 1/(alpha_k + phi)
    n_ind, worst_rel, bad_ind = 0, 0.0, []
    for k, c in K.items():
        for rn, r in c["price_refs"].items():
            hm = r.get("H_star_mu_over_lambda")
            if not hm:
                continue
            al = r["alpha_k"]
            for sw, ent in hm["by_switch"].items():
                bw = 1.0 if sw == "switch_beta_tilde" else ALPHA_P / (al + PHI)
                for m, e in ent.items():
                    mine = c2_hstar(al, ALPHA_P, float(m), 1 / (al + PHI), bw=bw)["H_over_lambda"]
                    ind = hstar_independent(al, ALPHA_P, float(m), 1 / (al + PHI), bw) * (al + PHI)
                    n_ind += 1
                    rel = abs(mine - ind) / abs(ind)
                    worst_rel = max(worst_rel, rel)
                    if rel > 1e-12 or (e["value"] is not None and e["value"] != mine):
                        bad_ind.append((k, rn, sw, m, mine, ind, e["value"]))
    chk_ind = {"n_values": n_ind, "max_rel_diff": worst_rel, "n_bad": len(bad_ind), "bad": [str(x) for x in bad_ind[:10]],
               "what": "H*_mu / lambda of every contract, price reference, switch convention and mu/beta~ "
                       "(a5b.c2_hstar, stored values) against hstar_independent (design/theory/c2_single_site.md §6 "
                       "and 'Switch cost'); stored values set to null where (C') fails are compared before nulling"}

    # (2) a9b: raw buffers equal a9b's b at its grid windows; the envelope equals a9b's b_envelope_5min there, and
    # where it exceeds a9b's grid envelope b_envelope, b dips between grid points
    n_eq, n_b, n_env_eq, env_diff = 0, 0, 0, []
    for n in names:
        for D in (x for x in map(int, a9b["meta"]["windows_min"]) if x <= Dmax):
            w = a9b["lenders"][n]["windows"][str(D)]
            for q in QS:
                n_b += 1
                n_eq += buf[n]["raw"][D][q] == w["b"][q]
                n_env_eq += buf[n]["env"][D][q] == w["b_envelope_5min"][q]
                if buf[n]["env"][D][q] != w["b_envelope"][q]:
                    env_diff.append({"lender": n, "D_min": D, "q": q, "fine_grid": buf[n]["env"][D][q],
                                     "a9b_grid": w["b_envelope"][q]})
    nonmono = sorted({f"{n}:{q}" for n in names for q in QS
                      if any(buf[n]["raw"][D][q] < buf[n]["env"][D][q] for D in grid)})
    chk_a9b = {"n_values_compared": n_b, "n_exactly_equal": n_eq, "n_envelope_equal_b_envelope_5min": n_env_eq,
               "envelope_differs_from_a9b_grid_envelope": env_diff,
               "lenders_with_b_non_monotone_on_5min_grid": nonmono}

    # (3) exact-game brackets at a0: computed before the contracts (br, brackets_ok)
    # (6) Table PoR at the default prices (c2/por_default.py, not run by run_all.sh) must use a5b's prices
    pj = json.load(open(os.path.join(HERE, "..", "theory_checks", "c2", "out", "por_default.json")))["inputs"]
    assert abs(pj["alpha"] - ALPHA) < 5e-7 and abs(pj["alpha_p"] - ALPHA_P) < 5e-7 and pj["phi"] == PHI, (
        f"stale c2/out/por_default.json: alpha={pj['alpha']}, alpha_p={pj['alpha_p']} vs a5b {ALPHA}, {ALPHA_P}; rerun "
        "code/theory_checks/c2/por_default.py")
    chk_por = {"source": "code/theory_checks/c2/out/por_default.json (inputs)", "alpha": pj["alpha"],
               "alpha_p": pj["alpha_p"], "phi": pj["phi"], "equal_to_a5b": True}
    # (5) scenario anchors
    anchors = {}
    for sc, s in SCENARIOS.items():
        if "anchor" in s:
            a = s["anchor"]
            v = lam_s(a["w_GB"], 1, sc)
            anchors[sc] = {"w_GB": a["w_GB"], "lambda_s": v,
                           "reproduces": abs(v - a["lambda_s"]) < 1e-9 if "lambda_s" in a else v >= a["lambda_s_lower_bound"]}
    for k8, bw in (("llama3-8b", "10"), ("llama3-70b", "2"), ("llama3.1-405b", "2"), ("llama3-70b", "10")):
        v = lam["a5_llama3"][k8][f"a5_{bw}GBps"]
        anchors[f"a5_{bw}GBps:{k8}"] = {"lambda_s": v, "a5_setup_s": a5["calibration"][k8]["setup_s_by_load_GBps"][bw],
                                        "reproduces": v == a5["calibration"][k8]["setup_s_by_load_GBps"][bw]}

    checks = {"catalog_usable": usable, "catalog_fits_g_x_80GB": fit, "a5b_reproduction": chk_a5b,
              "H_star_mu_independent_implementation": chk_ind, "a9b_buffers": chk_a9b,
              "exact_game_brackets_at_a0": {"source": f"c2/audit/out/model_switch_cost_default.txt ({exact_n}); "
                                                      "header prices equal a5b's (asserted); brackets from its "
                                                      "exact_full_precision block, lo < formula <= hi (1 + 1e-9)",
                                            "rows": br, "all_inside": brackets_ok,
                                            "VERIFIED_labels_granted": brackets_ok},
              "simple_form_equals_formula_where_conditions_hold": {"n_violations": len(sf_bad), "violations": sf_bad[:10]},
              "por_default_prices": chk_por,
              "scenario_anchors": anchors}

    res = {
        "meta": {"description": __doc__.split("\n\n")[0], "catalog_used": "maas_a10" if usable else "a5_llama3",
                 "catalog_note": "MaaS entries (a10 proposed_catalog) are the default catalog (Q30): S, M, L with g = "
                                 "the instance-hour-weighted fused gpu_count (GPUs per replica by replica time) and L "
                                 "with 8-bit weights (16-bit weights do not fit on 8 x 80 GB); M_g_gpu_hours (g = 2), "
                                 "L_16bit (g = 16) and L_g4 (235B, g = 4) are sensitivity entries; the a5 Llama-3 tiers "
                                 "are the sensitivity catalog. g is measured on the trace's GPU mix, mostly GPUs "
                                 "larger than 80 GB; pricing it as H100-80GB is an assumption. Every entry fits on "
                                 "g x 80 GB (checks.catalog_fits_g_x_80GB)",
                 "buffer_sample_size_caveat": "MaaS buffers come from one week of slack; for D >= 120 min the P99 of "
                                              "many clusters is set by a single drop episode (sources.buffers gives the "
                                              "counts and the median ratio of P99 to the largest drop), so the MaaS IR "
                                              "prices of long windows (and the (C) threshold of the worst cluster) "
                                              "rest on one drop event (contracts.<k>.ir_summary.maas_p99_tail_episodes)",
                 "default_scenarios": ["a5_10GBps", "a5_2GBps"], "default_price_ref": "maas_p99_median",
                 "default_switch": DEFAULT_SWITCH, "default_slot_min": 5,
                 "rows_note": f"rows are at price reference {ROW_REF} and the default 5-min slot; for the other "
                              "price references and the 1-min slot use contracts.<k>.price_refs.<ref> (f_beta, "
                              "H_star_mu_over_lambda, max_lambda_s_with_rho_le_2, a_usd_per_gpu_h) with load_time_s",
                 "scope_note": "H*_mu values come from C2, proven or checked only for tau = 0; every menu contract has "
                               "tau >= 1 slot, so they are an approximation (design §1.5.1, Q12). Windows above 300 min "
                               "(AEP-82-like notices of hours) are not in the menu and not priced here (a9b covers up "
                               "to 24 h on its grid)."},
        "sources": SOURCES, "field_sources": FIELD_SOURCES, "H_star_mu_status_legend": STATUS,
        "inputs": {"a0": A0, "q_GPU": Q_GPU, "a_p": A_P, "alpha": ALPHA, "alpha_p": ALPHA_P, "phi": PHI,
                   "beta_jl": BETA_JL, "mu_over_beta_tilde": MU_RATIOS, "H_menu_min": list(H_MENU_MIN),
                   "slots_min": list(SLOTS_MIN), "buffer_quantiles": list(QS), "lender_grid_min": [grid[0], grid[-1]],
                   "maas_lenders": maas, "spot_L7_lenders": spot},
        "catalog": cat,
        "scenarios": SCENARIOS,
        "load_time_s": lam,
        "default_prices_switch_cost_breakpoints": parse_crossover(),
        "condition_C_at_IR_prices": cond_c,
        "contracts": K,
        "ir_prices_by_lender": ir_table,
        "rows": rows,
        "table_3_8_by_tier": {"definition": "price maas_p99_median, 5-min slot, tau = 1 slot (5 min); rho at "
                                            "H = 2/60/240 min, and at tau = 1 h, H = 0; H*_mu with the default switch",
                              "values": t38},
        "checks": checks,
    }
    save_json("a11_calibration.json", res)

    # console summary
    print(f"catalog {res['meta']['catalog_used']}; a5b reproduction: {n_cmp['independent']} independent + "
          f"{n_cmp['plumbing']} plumbing comparisons, {len(mism)} mismatches; independent H*_mu: {n_ind} values, max "
          f"rel diff {worst_rel:.1e}; a9b buffers {n_eq}/{n_b} equal, envelope = b_envelope_5min {n_env_eq}/{n_b}; "
          f"grid-envelope diffs {len(env_diff)}; exact brackets all inside: {brackets_ok}; simple-form violations "
          f"{len(sf_bad)}")
    print(f"(C) fails at the maas_p99_max price ({cond_c['maas_p99_max_price']['lender']}) from D_lender = "
          f"{cond_c['maas_p99_max_price']['D_lender_min']} min; at the MaaS median "
          f"from {cond_c['maas_p99_median_price']}; contracts failing at maas_p99_max: "
          f"{cond_c['menu_contracts_failing_at_maas_p99_max']}")
    for k in ("s5_tau5_H2", "s5_tau5_H60", "s5_tau5_H240", "s5_tau60_H0", "s5_tau60_H240"):
        r = K[k]["price_refs"]
        e = K[k]["ir_summary"]["maas_p99_tail_episodes"]
        print(f"{k:15s} D_lender={K[k]['D_lender_min']:4d}  maas median x{r['maas_p99_median']['multiplier']:.4f} "
              f"max x{r['maas_p99_max']['multiplier']:.4f} ({r['maas_p99_max']['argmax']}, "
              f"{e['maas_p99_max_lender']['n_tail_episodes']} episode(s))  one-episode P99s "
              f"{e['n_lenders_with_one_episode']}/{e['n_lenders_with_positive_p99']}  spot L7 median "
              f"{r['spot_L7_p99_median']['multiplier']}  ({r['spot_L7_p99_median']['n_offering']}/4 offer)")
    for cn in t38:
        for tn, d in t38[cn].items():
            print(f"{cn}:{tn}")
            for sc, v in d.items():
                print(f"   {sc:22s} lam={v['lambda_s']:8.1f} s  H*_b={v['H_star_beta_s'] / 60:8.2f} min  rho(2/60/240)=" +
                      "/".join(f"{x:.2f}" for x in v["rho"].values()) + f"  minH(rho<=2)={v['min_menu_H_min_with_rho_le_2_tau_1slot']}"
                      "  H*_mu(0.2/1/2)=" + "/".join(f"{v['H_star_mu_s'][m] / 60:.2f}" for m in ("0.2", "1.0", "2.0")) + " min")


if __name__ == "__main__":
    main()
