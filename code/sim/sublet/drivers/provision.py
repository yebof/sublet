"""BL0b and the own-capacity cost (design/sim_spec_ms2.md §15.2; M42).

BL0b (information class hindsight-reference) provisions own capacity at each borrower's peak at the
committed price, from Instance.borrower_stats (MS2 C4: per borrower {'llm', 'C0_loads',
'peak_loads'} in replica loads after the Gamma scaling):
  overflow accounting  sum_b g_{j_b} (peak_b - C0_b) a_commit T_h,
  total accounting     sum_b g_{j_b} peak_b a_commit T_h,
with T_h the horizon in hours and a_commit the cheapest protected price of the instance by default
(5.97 USD/GPU-h at the defaults, a11_calibration.json inputs.a_p). It is an analytic cost, not an
engine run (own GPUs, always warm: no loads, routing or stranding). own_capacity_usd(inst) =
sum_b g_{j_b} C0_b a_commit T_h is the constant that the total accounting of Q32 adds to every policy.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from ..types import Instance

ACCOUNTINGS = ("overflow", "total")


def committed_price(inst: Instance) -> float:
    """The cheapest price of an offered Contract.protected contract (USD per GPU-hour); without one,
    the config's prices.a_protected_usd_per_gpu_h. ValueError if neither exists."""
    best = np.inf
    for l, s in enumerate(inst.sites):
        for k in s.menu:
            if inst.contracts[k].protected and np.isfinite(inst.price[l, k]):
                best = min(best, float(inst.price[l, k]))
    if np.isfinite(best):
        return best
    p = (inst.config.get("prices") or {}).get("a_protected_usd_per_gpu_h")
    if p is None:
        raise ValueError("BL0b: the instance offers no protected contract and its config has no "
                         "prices.a_protected_usd_per_gpu_h; pass a_commit")
    return float(p)


def _setup(inst: Instance, a_commit: Optional[float]) -> tuple[float, float]:
    if not inst.borrower_stats:
        raise ValueError("BL0b: the instance has no borrower_stats (only the regional and series demand "
                         "models record own capacity and peaks)")
    a = committed_price(inst) if a_commit is None else float(a_commit)
    if not np.isfinite(a) or a < 0:
        raise ValueError(f"BL0b: a_commit must be finite and >= 0, got {a_commit!r}")
    return a, inst.grid.horizon_min / 60.0


def bl0b_usd(inst: Instance, *, a_commit: Optional[float] = None, accounting: str = "overflow") -> float:
    """BL0b's cost in USD: own capacity at every borrower's peak at a_commit over the horizon,
    counting only the part above C0 ('overflow') or all of it ('total')."""
    if accounting not in ACCOUNTINGS:
        raise ValueError(f"BL0b: accounting must be one of {list(ACCOUNTINGS)}, got {accounting!r}")
    a, T_h = _setup(inst, a_commit)
    tot = 0.0
    for st in inst.borrower_stats.values():
        g = inst.llms[int(st["llm"])].g
        loads = st["peak_loads"] - st["C0_loads"] if accounting == "overflow" else st["peak_loads"]
        tot += g * float(loads) * a * T_h
    return float(tot)


def own_capacity_usd(inst: Instance, *, a_commit: Optional[float] = None) -> float:
    """sum_b g_{j_b} C0_b a_commit T_h: the cost of the borrowers' own capacity C0 at a_commit."""
    a, T_h = _setup(inst, a_commit)
    return float(sum(inst.llms[int(st["llm"])].g * float(st["C0_loads"]) * a * T_h
                     for st in inst.borrower_stats.values()))


__all__ = ["ACCOUNTINGS", "committed_price", "bl0b_usd", "own_capacity_usd"]
