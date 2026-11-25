"""Time rules T6 and T8 as functions, and the latest pre-warm slot (design/sim_spec_ms2.md §3.1, C8).

One implementation of the rules for the engine (warm-up of a replica) and for the reclaim
handler (pre-warm commit slot, design §3.4 step 4). Integer minutes from horizon minute 0;
load times in integer milliseconds (rule T8: lam_ms = round(1000 * lam_s)).
This module imports only the standard library and sublet.types.
"""
from __future__ import annotations

from typing import Optional

from .types import TimeGrid


def warm_fast(load_start_min: int, lam_ms: int, fast_min: int) -> int:
    """Rule T8: first fast slot in which a replica whose load starts at minute `load_start_min` is
    warm, ceil((60000 * load_start_min + lam_ms) / (60000 * fast_min)) in integer arithmetic."""
    return -(-(60000 * int(load_start_min) + int(lam_ms)) // (60000 * int(fast_min)))


def first_dead_fast(end_min: int, fast_min: int) -> int:
    """Rule T6: the first fast slot in which a lease with end minute `end_min` is dead
    (alive in f iff (f + 1) * fast_min <= end_min): end_min // fast_min."""
    return int(end_min) // int(fast_min)


def latest_prewarm_slot(r_slot: int, E_min: int, lam_ms: int, grid: TimeGrid) -> Optional[int]:
    """Latest slow slot t with r_slot <= t <= E_min // slow_min and
    warm_fast(t * slow_min, lam_ms, fast_min) <= first_dead_fast(E_min, fast_min): a replacement
    bought at t is warm in the first fast slot in which the announced lease (death minute E_min) is
    dead. None if no such t. The slot is not capped at the horizon: for E_min past the horizon end
    it can be >= grid.T_slow, and a caller that commits at that slot never reaches it."""
    slow, fast = int(grid.slow_min), int(grid.fast_min)
    dead = first_dead_fast(E_min, fast)
    for t in range(int(E_min) // slow, int(r_slot) - 1, -1):
        if warm_fast(t * slow, lam_ms, fast) <= dead:
            return t
    return None


__all__ = ["warm_fast", "first_dead_fast", "latest_prewarm_slot"]
