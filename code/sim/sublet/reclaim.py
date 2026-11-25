"""Pure functions of the reclaim rule (design/sim_spec.md §3.3, rules T5 and T10).

A lease of contract k bought at slow slot s on a site with announcement set R (sorted
unique int64 slow slots) is announced at the first r in R with r >= s + tau_k and dies at
minute r * slow_min + H_k (T5). A protected contract is never announced. On a bench grid
the death is converted to a bench index E_b (T10). No state; this module imports only
numpy and sublet.types.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .types import BenchGrid, Contract, TimeGrid

_NEVER = -1   # encodes "no death" in the vectorized functions


def _as_R(R) -> np.ndarray:
    return np.asarray(R, dtype=np.int64)


def first_announcement(R: np.ndarray, s: int, tau: int) -> Optional[int]:
    """First r in R with r >= s + tau (R sorted int64); None if none.
    Identical to core.effective_end's searchsorted(R, s + tau, 'left')."""
    R = _as_R(R)
    i = int(np.searchsorted(R, s + tau, side="left"))
    return None if i >= len(R) else int(R[i])


def death_min(R: np.ndarray, s: int, c: Contract, slow_min: int) -> Optional[int]:
    """r*slow_min + c.H_min for r = first_announcement(R, s, c.tau_slots); None if never
    (protected contract, or no announcement)."""
    if c.protected:
        return None
    r = first_announcement(R, s, c.tau_slots)
    return None if r is None else r * slow_min + c.H_min


def death_mins(R: np.ndarray, starts: np.ndarray, c: Contract, slow_min: int) -> np.ndarray:
    """Vectorized death_min for int64 start slots; -1 encodes None."""
    starts = np.asarray(starts, dtype=np.int64)
    out = np.full(starts.shape, _NEVER, dtype=np.int64)
    if c.protected:
        return out
    R = _as_R(R)
    i = np.searchsorted(R, starts + c.tau_slots, side="left")
    hit = i < len(R)
    out[hit] = R[i[hit]] * slow_min + c.H_min
    return out


def death_benches(R: np.ndarray, starts_slow: np.ndarray, c: Contract, grid: TimeGrid,
                  bench: BenchGrid) -> np.ndarray:
    """Vectorized death_bench: E_b of rule T10 for every SLOW start in `starts_slow`, as an
    int64 array of bench indices. (An addition to the §3.3 interface.)"""
    dm = death_mins(R, starts_slow, c, grid.slow_min)
    never = dm == _NEVER
    if bench == "slow":
        E = np.minimum(grid.T_slow, dm // grid.slow_min)
        E[never] = grid.T_slow
    elif bench == "fast":
        E = np.minimum(grid.T_fast, dm // grid.fast_min)
        E[never] = grid.T_fast
    elif bench == "slow_lb":
        E_fast = np.minimum(grid.T_fast, dm // grid.fast_min)
        E_fast[never] = grid.T_fast
        E = np.minimum(grid.T_slow, -(-E_fast // grid.phi))
    else:
        raise ValueError(f"unknown bench grid {bench!r}")
    return E.astype(np.int64)


def death_bench(R: np.ndarray, s_slow: int, c: Contract, grid: TimeGrid, bench: BenchGrid) -> int:
    """E_b of rule T10 for a lease bought at SLOW slot s_slow, as a bench index:
    'slow': min(T_s, floor(death_min / Δ_s)); 'fast': min(T_f, floor(death_min / Δ_f));
    'slow_lb': min(T_s, ceil(E_fast / φ_sf)) with E_fast the 'fast' value; T_b if never."""
    return int(death_benches(R, np.array([s_slow], dtype=np.int64), c, grid, bench)[0])


def cohorts(R: np.ndarray, starts_slow: np.ndarray, c: Contract, grid: TimeGrid,
            bench: BenchGrid) -> list[tuple[int, np.ndarray]]:
    """Partition of the SLOW-slot starts `starts_slow` by E_b (a bench index), as (E_b, starts_slow)
    sorted by E_b. Callers convert a slow start s to its bench index s * Δ_s // Δ_b themselves.

    The starts within a cohort are sorted ascending. Note that §8.6 builds the `slow_lb`
    cohorts with bench 'fast' (the fine death), not with bench 'slow_lb'."""
    starts = np.sort(np.asarray(starts_slow, dtype=np.int64))
    if len(starts) == 0:
        return []
    E = death_benches(R, starts, c, grid, bench)
    order = np.argsort(E, kind="stable")   # identity in practice: E_b is non-decreasing in s
    E, starts = E[order], starts[order]
    vals, first = np.unique(E, return_index=True)
    return [(int(v), part) for v, part in zip(vals, np.split(starts, first[1:]))]


def layer_R(S_lend_h: np.ndarray, threshold_gpus: float) -> np.ndarray:
    """Sorted int64 slow slots t with S_lend_h[t] < threshold_gpus: the announcement set of a layer
    whose top lendable level is threshold_gpus (§6.2). U1 calls it to merge layers and U2's build_R
    to build the 'trace' sets, so both use one implementation."""
    return np.flatnonzero(np.asarray(S_lend_h, dtype=np.float64) < threshold_gpus).astype(np.int64)
