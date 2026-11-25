"""Shared helpers of the reproduction scripts R1-R8 (design/sim_spec_ms2.md §17.3); not a script.

Policies are built through the registry (`drivers.run.make_policy`), so that the scripts depend on
the policy ids and parameters of §4.2 only; engine runs use the public `simulate` with the lender
model and seeds of each reference; worker pools are capped at 4 processes (§18.3).
"""
from __future__ import annotations

import multiprocessing as mp
import os
from pathlib import Path
from typing import Callable, Iterable, Optional

import numpy as np

from ..engine import EngineConfig, simulate
from ..paths import SIM_OUT
from ..types import Instance, LenderModel


def checks_dir() -> Path:
    """Output folder of the reproduction scripts: code/sim/out/ms2_checks, or SUBLET_MS2_CHECKS_DIR if set
    (the folder that conftest.py's needs_ms2_checks reads)."""
    return Path(os.environ.get("SUBLET_MS2_CHECKS_DIR") or (SIM_OUT / "ms2_checks"))


def make(pid: str, params: Optional[dict], inst: Instance, inputs: Optional[dict] = None):
    """The policy of registry id `pid` with `params`, its driver inputs computed from `inst` unless given."""
    from ..drivers.run import make_policy
    return make_policy({"policy": {"id": pid, "params": dict(params or {})}}, inst, inputs=inputs)


def run(inst: Instance, pol, *, schedule: str = "trace", information: str = "I1",
        rng: Optional[np.random.Generator] = None, policy_seed: Optional[int] = None, lender_seed: int = 0,
        check: bool = True):
    """simulate(inst, pol) under LenderModel(schedule, information), the policy generator `rng`
    injected unchanged if given (reference draw orders, §4.3), else rng_streams(policy_seed).
    Raises AssertionError if the engine's invariant checks failed."""
    res = simulate(inst, pol, LenderModel(schedule=schedule, information=information),
                   EngineConfig(check_invariants=check), lender_seed=lender_seed,
                   policy_seed=policy_seed if rng is None else None, policy_rng=rng)
    assert not res.invariant_failures, res.invariant_failures[:5]
    return res


def lease_cost(res) -> float:
    """Lease cost of a run in the core's accounting: lease_prepaid + lease_rent + loading (§6.6)."""
    c = res.components
    return float(c["lease_prepaid"] + c["lease_rent"] + c["loading"])


def opened_map(pol) -> dict:
    """{reference key ('A', l, j, k, s) or with iota appended: opening slot} of a PD policy after its run
    (A2, A3; the shape of pd.round_pd(...)['opened']): its `opened_ref()` method if it has one, else
    report()['opened_map'] (runs with record=True)."""
    f = getattr(pol, "opened_ref", None)
    if callable(f):
        return {tuple(k): int(t) for k, t in f().items()}
    m = pol.report().get("opened_map")
    if m is None:
        raise KeyError(f"{type(pol).__name__} reports no opened map; run it with record=True")
    return {tuple(k): int(t) for k, t in m}


def get(rep: dict, *paths: str, default=KeyError):
    """The first of the dotted `paths` present in the nested report `rep`; KeyError naming all of them
    otherwise (or `default` if given)."""
    for p in paths:
        cur = rep
        ok = True
        for part in p.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok:
            return cur
    if default is KeyError:
        raise KeyError(f"none of {paths} in the report (keys {sorted(rep) if isinstance(rep, dict) else rep})")
    return default


def pool_map(fn: Callable, jobs: Iterable, workers: int = 4) -> list:
    """map(fn, jobs) in a pool of at most 4 processes (in this process for workers <= 1). The pool uses
    the 'spawn' start method, as the reference scripts do: a forked child of a process that has run
    HiGHS (scipy's milp or linprog) inherits HiGHS's thread pool without its threads and spins."""
    jobs = list(jobs)
    if workers <= 1 or len(jobs) <= 1:
        return [fn(j) for j in jobs]
    with mp.get_context("spawn").Pool(min(4, workers, len(jobs))) as p:
        return p.map(fn, jobs, chunksize=1)


def empty_omega(m: int) -> list:
    return [np.zeros(0, dtype=np.int64) for _ in range(m)]


__all__ = ["checks_dir", "make", "run", "lease_cost", "opened_map", "get", "pool_map", "empty_omega"]
