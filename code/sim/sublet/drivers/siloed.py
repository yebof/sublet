"""Siloed planning: one engine run per borrower on its own sub-instance (design/sim_spec_ms2.md §15.9).

The clients are partitioned by their first borrower id; borrower b's sub-instance is
`restrict_clients(inst, clients_b)`, and its policy is built from the sub-instance by
`policy_factory`, so that driver inputs (N, predictions) come from the borrower's own clients.
The siloed cost is the sum of the per-borrower runs (check_c4_lower.part_d's definition). The
sub-runs share no site capacity, and buffer violations and an adaptive lender see one borrower's
leases at a time (M24).
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from ..engine import EngineConfig, simulate
from ..instance import restrict_clients
from ..policies.base import Policy
from ..types import Instance, LenderModel


def borrower_partition(inst: Instance) -> list[tuple[str, list[int]]]:
    """(first borrower id, client indices) per borrower, in order of the borrower's first client."""
    groups: dict[str, list[int]] = {}
    for c, bor in enumerate(inst.clients.borrowers):
        groups.setdefault(bor[0] if bor else "", []).append(c)
    return list(groups.items())


def run_siloed(inst: Instance, policy_factory: Callable[[Instance], Policy],
               model: LenderModel = LenderModel(), cfg: EngineConfig = EngineConfig(), *,
               seed: Optional[int] = None, lender_seed: Optional[int] = None,
               policy_seed: Optional[int] = None) -> dict:
    """Run `policy_factory(sub)` on each borrower's sub-instance with the same seeds and return
    {'components': summed components, 'per_slot': summed per-slot components, 'borrowers': ids,
     'clients': client indices per borrower, 'results': RunResult per borrower, 'instances':
     sub-instance per borrower, 'invariant_failures': the sub-runs' failures prefixed by the
     borrower, 'seeds': RunResult.seeds of the sub-runs (identical)}."""
    parts = borrower_partition(inst)
    comp: dict[str, float] = {}
    per_slot: dict[str, np.ndarray] = {}
    results, subs, fails = [], [], []
    for b, idx in parts:
        sub = restrict_clients(inst, idx)
        res = simulate(sub, policy_factory(sub), model, cfg, seed=seed, lender_seed=lender_seed,
                       policy_seed=policy_seed)
        for k, v in res.components.items():
            comp[k] = comp.get(k, 0.0) + float(v)
        for k, v in res.per_slot.items():
            per_slot[k] = per_slot[k] + v if k in per_slot else np.array(v, dtype=np.float64)
        fails += [f"borrower {b}: {f}" for f in res.invariant_failures]
        results.append(res)
        subs.append(sub)
    return {"components": comp, "per_slot": per_slot, "borrowers": [b for b, _ in parts],
            "clients": [list(idx) for _, idx in parts], "results": results, "instances": subs,
            "invariant_failures": fails, "seeds": dict(results[0].seeds) if results else {}}


__all__ = ["borrower_partition", "run_siloed"]
