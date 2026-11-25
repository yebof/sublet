"""Calibration functions (design/sim_spec.md §3.4.3).

Every formula follows `code/analysis/a11_calibration.py`, so that the values reproduce
`a11_calibration.json`; the a5 tier assumptions come from `a5_reclaim_cost_calibration.json`
(`assumptions`, ASSUMPTION in design Table 5.6). Buffers use `a9_notice_buffer.buffer_curve`,
imported through `sublet.paths` (§2.2). Units: minutes for windows, seconds for load and
drain times, USD per GPU-hour for prices, USD per load for loading costs.

MS3 addition (design/sim_spec_ms3.md §2.3, C12): `instance_rho` (rho of design §1.6 per LLM on a built
instance) and `beta_for_rho` (the transfer fee per LLM that sets each LLM's rho to a target; E1(b), M1).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

import numpy as np

from . import paths
from .traces.catalog import a5_tier_of

SLACK_SLOT_MIN = 5          # resolution of the a1/a2 slack series
TAU_1H_MIN = 60             # the 1-h guaranteed period of the a11 menu (a11 TAU_1H_MIN)


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


A11 = load_json(paths.ANALYSIS_OUT / "a11_calibration.json")
A5 = load_json(paths.ANALYSIS_OUT / "a5_reclaim_cost_calibration.json")


def prices() -> dict:
    """{'a0', 'q_gpu', 'a_p'} in USD per GPU-hour from a11 `inputs` (keys a0, q_GPU, a_p)."""
    i = A11["inputs"]
    return {"a0": float(i["a0"]), "q_gpu": float(i["q_GPU"]), "a_p": float(i["a_p"])}


def scenarios() -> list[str]:
    """Names of the a11 load-time scenarios, in file order."""
    return list(A11["scenarios"])


def load_time_s(w_GB: float, g: int, scenario: str) -> float:
    """Load time w / (bw * (g if per_gpu else 1)) + t_init (a11 lam_s; design §1.5.3)."""
    if scenario not in A11["scenarios"]:
        raise KeyError(f"unknown load scenario {scenario!r}; known: {scenarios()}")
    s = A11["scenarios"][scenario]
    return w_GB / (s["bw_GBps"] * (g if s["per_gpu"] else 1)) + s["t_init_s"]


def _a5(tier: str) -> str:
    return a5_tier_of(tier)


def kappa_wtok_per_min(tier: str) -> float:
    """Replica goodput in weighted tokens per minute: 60 * concurrent sequences / TPOT of the a5
    tier of the same letter (ASSUMPTION)."""
    A = A5["assumptions"]
    return 60.0 * A["concurrent_seqs_per_replica"] / A["tpot_s"][_a5(tier)]


def w_in(tier: str) -> float:
    """Weight of an input token: decode rate (concurrent / TPOT) over the prefill rate (a5)."""
    A = A5["assumptions"]
    k = _a5(tier)
    return (A["concurrent_seqs_per_replica"] / A["tpot_s"][k]) / A["prefill_tok_per_s_per_replica"][k]


def T_dr_s(tier: str) -> float:
    """P99 drain time in seconds of the a5 tier of the same letter."""
    return float(A5["calibration"][_a5(tier)]["T_dr_s (p99 drain)"])


def D_lender_min(D_exact_min: int, slow_min: int) -> int:
    """Lender's buffer window: 5 floor(D/5) at the 5-min slot, 5 ceil(D/5) otherwise (a11 menu())."""
    if slow_min == SLACK_SLOT_MIN:
        return SLACK_SLOT_MIN * (D_exact_min // SLACK_SLOT_MIN)
    return SLACK_SLOT_MIN * math.ceil(D_exact_min / SLACK_SLOT_MIN)


def _check_window(series: np.ndarray, D: int) -> None:
    if D < SLACK_SLOT_MIN or D % SLACK_SLOT_MIN:
        raise ValueError(f"buffer window {D} min is not a positive multiple of {SLACK_SLOT_MIN} min")
    if D // SLACK_SLOT_MIN >= len(series):
        raise ValueError(f"buffer window {D} min is not shorter than the series ({len(series)} slots)")


def buffer_curve(series: np.ndarray, Dmax: int) -> dict:
    """a9_notice_buffer.buffer_curve(series, Dmax): raw and running-maximum buffers (fractions of
    mean slack) for every 5-min window up to Dmax. env[D] does not depend on Dmax >= D."""
    s = np.asarray(series, dtype=np.float64)
    _check_window(s, Dmax)
    return paths.import_a9().buffer_curve(s, Dmax)


def buffer_env(series: np.ndarray, D_lender_min: int, q: str = "p99") -> float:
    """b_l(D): a9_notice_buffer.buffer_curve(series, D)['env'][D][q] (fraction of mean slack)."""
    return float(buffer_curve(series, D_lender_min)["env"][D_lender_min][q])


def ir_multiplier(series: np.ndarray, D_lender_min: int, q: str = "p99") -> Optional[float]:
    """IR price multiplier 1 / (1 - b) if b < 1, else None (the lender cannot offer the window)."""
    return _ir(buffer_env(series, D_lender_min, q))


def _ir(b: float) -> Optional[float]:
    return float(1.0 / (1.0 - b)) if b < 1 else None


def beta_tilde_usd(beta_jl: float, lam_s: float, g: int, a: float, q_gpu: float, phi: float) -> float:
    """Core loading cost beta_jl + lam_s / 3600 * (g a + phi g q_gpu) (design §1.5.3)."""
    return beta_jl + lam_s / 3600 * (g * a + phi * g * q_gpu)


def rho(beta_tilde: float, g: int, a: float, D_pd_min: float) -> float:
    """rho = 1 + beta_tilde / (g a D_pd / 60) (design §1.6)."""
    return 1 + beta_tilde / (g * a * D_pd_min / 60)


def H_star_beta_s(beta_tilde: float, g: int, a: float, tau_s: float) -> float:
    """H*_beta = 3600 beta_tilde / (g a) - tau in seconds (design §1.6)."""
    return 3600 * beta_tilde / (g * a) - tau_s


def contract_klass(tau_min: Optional[int], H_min: int, slow_min: int) -> str:
    """Contract class by the a11 menu() rule; 'protected' if tau_min is None."""
    if tau_min is None:
        return "protected"
    if tau_min == TAU_1H_MIN and H_min == 0:
        return "GFS-like"
    if tau_min == slow_min and H_min <= 2:
        return "spot-like"
    if tau_min == slow_min and H_min >= 60:
        return "AEP-82-like"
    return "general"


# ---------------------------------------------------------------- MS3 C12: rho of a built instance
def _rho_pairs(inst):
    """Usable revocable (site, contract) pairs of a built Instance in contract-major order, with the window
    D_k = max(L_k Δs, P_k) in minutes: L_k = tau_k + H_k // Δs slow slots (the slot-rounded PD window of rule
    T12, algos.common.pd_window_slots) and P_k the minimum billed term; usable = positive finite price (the
    loading cost is checked by the callers). Yields (l, k, a_lk, D_k)."""
    slow = inst.grid.slow_min
    for k, c in enumerate(inst.contracts):
        if c.protected:
            continue
        D = max((int(c.tau_slots) + int(c.H_min) // slow) * slow, int(c.prepaid_min))
        for l in range(inst.m):
            a = float(inst.price[l, k])
            if not math.isfinite(a) or a <= 0:
                continue
            yield l, k, a, float(D)


def _beta_tilde0(inst, j: int, l: int, a: float) -> float:
    """Loading cost without the transfer fee: lam_s / 3600 (g a + phi g q_GPU) (design §1.5.3)."""
    return beta_tilde_usd(0.0, float(inst.lam_s[j, l]), inst.llms[j].g, a, inst.q_gpu_usd_per_h, inst.phi_load)


def instance_rho(inst) -> dict:
    """{LLM id: (rho, site id, contract id)}: per LLM the maximum over the usable revocable (l, k) (finite
    price and loading cost) of rho = 1 + beta~_jlk / (g_j a_lk D_k / 60) (design §1.6), with beta~_jlk =
    beta_usd[j, l] + lam_s[j, l] / 3600 (g_j a_lk + phi g_j q_GPU) and D_k = max(L_k Δs, P_k) the slot-rounded
    window. Ties keep the first pair in contract-major, site-minor order; None for an LLM without a usable
    pair. `to_core(...)` uses beta~ at a0 and so gives other values."""
    out = {}
    pairs = list(_rho_pairs(inst))
    for j, x in enumerate(inst.llms):
        best = None
        for l, k, a, D in pairs:
            bt = float(inst.beta_usd[j, l]) + _beta_tilde0(inst, j, l, a)
            if not math.isfinite(bt):
                continue
            r = rho(bt, x.g, a, D)
            if best is None or r > best[0]:
                best = (float(r), inst.sites[l].id, inst.contracts[k].id)
        out[x.id] = best
    return out


def beta_for_rho(inst, target: float) -> dict:
    """{LLM id: USD}: the transfer fee beta_j per LLM (the same at every site) with which instance_rho of the
    instance rebuilt with costs.beta_jl_usd = this map equals `target` for every LLM: beta_j = min over the
    usable revocable (l, k) of (target - 1) g_j a_lk D_k / 60 - beta~0_jlk, beta~0 the loading cost without
    fee (the instance's own fee is ignored). Raises ConfigError if some beta_j < 0 (the calibrated rho already
    exceeds the target; tolerance 1e-12 relative) or an LLM has no usable pair."""
    from .config import ConfigError          # config imports calib
    target = float(target)
    if not math.isfinite(target):
        raise ConfigError(f"beta_for_rho: target rho must be finite, got {target!r}")
    out = {}
    pairs = list(_rho_pairs(inst))
    for j, x in enumerate(inst.llms):
        need = []
        for l, k, a, D in pairs:
            b0 = _beta_tilde0(inst, j, l, a)
            if not math.isfinite(b0):
                continue
            cap = (target - 1.0) * x.g * a * D / 60.0
            need.append((cap - b0, max(abs(cap), abs(b0), 1.0), inst.sites[l].id, inst.contracts[k].id))
        if not need:
            raise ConfigError(f"beta_for_rho: LLM {x.id!r} has no usable revocable (site, contract) pair")
        b, scale, site, cid = min(need, key=lambda t: t[0])
        if b < -1e-12 * scale:
            raise ConfigError(f"beta_for_rho: the calibrated rho of LLM {x.id!r} at ({site}, {cid}) already exceeds "
                              f"the target {target:g} (the fee would be {b:.6g} USD < 0)")
        out[x.id] = max(float(b), 0.0)
    return out

