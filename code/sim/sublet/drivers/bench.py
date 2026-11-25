"""BL8: the offline benchmark of a finished run (design/sim_spec_ms2.md §15.10; design Table 5.3).

`bench_for(res, inst, kind, ...)` solves the benchmark on the run's realized schedule res.schedule:
  'omega' -> opt.milp.solve_opt(inst, res.schedule), with the run's refusal sets when the run used
             on_unavailable = 'refuse' (refuse_unavailable=True);
  'eager' -> opt.milp.solve_eager(inst) (refuse_sched = res.schedule for a 'refuse' run);
  'lp'    -> opt.milp.solve_lp(inst, res.schedule), on opt.relax.merged_relaxation(inst, res.schedule)
             when merged=True (a bound on the merged instance, labeled as such in status_msg);
  'dp'    -> opt.dp.solve_dp(inst, res.schedule) (single-site instances);
  'fam'   -> fam.opt_dp on a family instance (code/theory_checks/c3/o1/fam.py through paths.import_ref):
             the Fam passed as `fam`, else rebuilt from a from_core instance of Fam.core_instance().
It returns the SolveResult (status and gap included); metrics.ratio gives the ratio. Ratios are
meaningful only for runs on the benchmark's grid with violations absorbed (design §5.2.4): a run
with violations = 'reclaim' has no valid omega.
"""
from __future__ import annotations

import resource
import time
from typing import Optional

import numpy as np

from ..opt.dp import solve_dp
from ..opt.milp import solve_eager, solve_lp, solve_opt
from ..opt.relax import merged_relaxation
from ..paths import import_ref
from ..types import Instance, RunResult, SolveResult

KINDS = ("omega", "eager", "lp", "dp", "fam")


def _peak_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def fam_of(inst: Instance):
    """The fam.Fam of a from_core instance built from Fam(m, rho, tau, H, T, a).core_instance():
    m sites with one contract (tau, H), one LLM with g = 1, one always-active client with delta = 0,
    equal rent a and loading cost beta at every site; rho = 1 + beta / (a D). ValueError otherwise."""
    fam = import_ref("fam")
    slot = inst.grid.slow_min
    if "from_core" not in (inst.config or {}) or inst.K != 1 or inst.J != 1 or inst.n != 1:
        raise ValueError("fam bench: needs a from_core instance with one contract, one LLM and one client")
    c = inst.contracts[0]
    if c.tau_slots is None or c.H_min % slot:
        raise ValueError("fam bench: the contract must be revocable with H a multiple of the slot")
    tau, H, T, m = int(c.tau_slots), c.H_min // slot, inst.grid.T_slow, inst.m
    a_all = inst.price[:, 0] * slot / 60.0
    beta_all = inst.beta_usd[0, :]
    if np.ptp(a_all) > 1e-12 * max(1.0, abs(a_all[0])) or np.ptp(beta_all) > 1e-12 * max(1.0, abs(beta_all[0])):
        raise ValueError("fam bench: rent and loading cost must be equal at every site")
    if inst.llms[0].g != 1 or not np.all(inst.clients.demand > 0) or np.any(inst.clients.delta_usd_per_h != 0):
        raise ValueError("fam bench: needs g = 1, an always-active client and delta = 0")
    a, beta = float(a_all[0]), float(beta_all[0])
    F = fam.Fam(m, 1.0 + beta / (a * (tau + H)), tau, H, T, a)
    q = inst.llms[0].q_usd_per_h * slot / 60.0
    if abs(F.q - q) > 1e-9 * max(1.0, abs(q)) or abs(F.beta - beta) > 1e-9 * max(1.0, abs(beta)):
        raise ValueError(f"fam bench: the instance is not a Fam (q {q} vs {F.q}, beta {beta} vs {F.beta})")
    return F


def bench_for(res: RunResult, inst: Instance, kind: str, *, grid: str = "slow", time_limit_s: float = 300.0,
              mip_rel_gap: float = 1e-4, max_vars: int = 200_000, merged: bool = False,
              refuse_unavailable: bool = False, fam=None, allow_large: bool = False,
              mem_budget_mb: Optional[float] = None, return_plan: bool = True) -> SolveResult:
    """The BL8 benchmark `kind` (one of KINDS) for the finished run `res` on `inst` (§15.10).
    refuse_unavailable: the run used on_unavailable = 'refuse' (its schedule's sets are refusal sets,
    MS1 §8.1). merged: 'lp' on the merged relaxation. fam: the Fam of kind 'fam' (default: rebuilt
    from inst). The MILP options go to opt.milp (MS1 bench fields)."""
    if kind not in KINDS:
        raise ValueError(f"bench kind must be one of {list(KINDS)}, got {kind!r}")
    sched = res.schedule
    if not sched.realized:
        raise ValueError("bench: the run's schedule is not realized")
    kw = dict(grid=grid, time_limit_s=float(time_limit_s), mip_rel_gap=float(mip_rel_gap), max_vars=int(max_vars),
              allow_large=bool(allow_large), return_plan=bool(return_plan))
    if mem_budget_mb is not None:
        kw["mem_budget_mb"] = float(mem_budget_mb)
    rs = sched if refuse_unavailable else None
    if kind == "omega":
        return solve_opt(inst, sched, refuse_unavailable=bool(refuse_unavailable), refuse_sched=rs, **kw)
    if kind == "eager":
        return solve_eager(inst, refuse_sched=rs, **kw)
    if kind == "lp":
        if merged:
            inst_m, sched_m, site_map = merged_relaxation(inst, sched)
            out = solve_lp(inst_m, sched_m, refuse_unavailable=bool(refuse_unavailable),
                           refuse_sched=sched_m if refuse_unavailable else None, **kw)
            out.status_msg = (f"merged relaxation ({inst.m} -> {inst_m.m} sites; LP bound on the merged "
                              f"instance): {out.status_msg}")
            out.size = dict(out.size, merged_sites=int(inst_m.m), sites=int(inst.m))
            return out
        return solve_lp(inst, sched, refuse_unavailable=bool(refuse_unavailable), refuse_sched=rs, **kw)
    if kind == "dp":
        return solve_dp(inst, sched, grid=grid, refuse_unavailable=bool(refuse_unavailable),
                        return_plan=bool(return_plan))
    # 'fam': exact OPT(sigma, omega) of the T4/O1 family by fam.opt_dp
    fam_mod = import_ref("fam")
    t0 = time.perf_counter()
    F = fam if fam is not None else fam_of(inst)
    t1 = time.perf_counter()
    omega = [np.asarray(R, dtype=int) for R in sched.R]
    if len(omega) != F.m:
        raise ValueError(f"fam bench: schedule has {len(omega)} sites, the family {F.m}")
    cost, cnt = fam_mod.opt_dp(F, omega)
    t2 = time.perf_counter()
    return SolveResult(method="dp", benchmark="omega", grid="slow", status=0, status_msg="optimal (fam.opt_dp)",
                       objective=float(cost), dual_bound=float(cost), gap=0.0, plan=None,
                       components={"total": float(cost)},
                       size={"m": int(F.m), "T": int(F.T), "n_purchases_plus_fallback": int(cnt)},
                       build_s=t1 - t0, solve_s=t2 - t1, peak_rss_mb=_peak_rss_mb())


__all__ = ["KINDS", "bench_for", "fam_of"]
