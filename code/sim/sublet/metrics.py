"""Run metrics, run files, ratios to benchmarks and aggregation (design/sim_spec.md §5.9).

`run_metrics` formats the sums that the engine accumulates online in RunResult.metrics, so it
needs no recorded routing. `write_run` writes one run as JSON. `ratio` relates an algorithm's
cost to a benchmark SolveResult; `aggregate` summarizes ratios over instances with a percentile
bootstrap interval of the median.
"""
from __future__ import annotations

import json
import math
import platform
import sys
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from .types import Instance, RunResult, SolveResult


def _share(num: float, den: float) -> Optional[float]:
    return float(num) / float(den) if den > 0 else None


def run_metrics(res: RunResult, inst: Instance) -> dict:
    """The metrics of §5.9 from the engine's online sums (shares are None when undefined)."""
    m = res.metrics
    days = float(m.get("horizon_days") or inst.grid.horizon_min / 1440.0)
    llm_ids = [L.id for L in inst.llms]
    dem = np.asarray(m["demand_load_min_by_llm"], dtype=float)
    fb = np.asarray(m["fallback_load_min_by_llm"], dtype=float)
    dem_r = np.asarray(m["demand_after_reclaims_load_min_by_llm"], dtype=float)
    fb_r = np.asarray(m["fallback_after_reclaims_load_min_by_llm"], dtype=float)
    checked = int(m.get("lender_slots_checked", 0))
    n_viol = int(m.get("violation_lender_slots", 0))
    n_att = int(m.get("violation_lender_slots_attributable", 0))
    return {
        "cost": dict(res.components),
        "fallback_share": _share(fb.sum(), dem.sum()),
        "fallback_share_by_llm": {j: _share(fb[i], dem[i]) for i, j in enumerate(llm_ids)},
        "stranded_load_fb": float(m["stranded_load_fb"]),
        "stranded_load_any": float(m["stranded_load_any"]),
        "stranding_events_per_day": m["stranding_events"] / days,
        "fallback_share_after_reclaims": _share(fb_r.sum(), dem_r.sum()),
        "fallback_share_after_reclaims_by_llm": {j: _share(fb_r[i], dem_r[i])
                                                 for i, j in enumerate(llm_ids)},
        "loads_per_day": m["loads"] / days,
        "replica_utilization": _share(m["served_load_min"], m["capacity_load_min"]),
        "gpu_hours_by_class": dict(m["gpu_hours_by_class"]),
        "gpu_only_lease_slots": int(m["gpu_only_lease_slots"]),
        # §6.5, S10: lender-slots with a deficit, and with a deficit the platform's leases cause
        # (zero for a policy that holds nothing); deficits summed in GPU-slots (one slow slot each)
        "buffer_violations": {"count": n_viol, "share": _share(n_viol, checked),
                              "deficit_gpu_slots": float(m.get("violation_deficit_gpu_slots", 0.0))},
        "buffer_violations_attributable": {
            "count": n_att, "share": _share(n_att, checked),
            "deficit_gpu_slots": float(m.get("violation_deficit_attributable_gpu_slots", 0.0))},
        "runtime": dict(res.runtime),
        # MS2 C6: the policy's report (RunResult.metrics['policy']), {} for MS1 policies
        "policy": m.get("policy", {}),
    }


def _jsonable(x):
    """Plain JSON values: arrays to lists, numpy scalars to Python, non-finite floats to strings."""
    if isinstance(x, dict):
        return {(k if isinstance(k, str) else str(k)): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        v = float(x)
        return v if math.isfinite(v) else ("inf" if v > 0 else "-inf" if v < 0 else "nan")
    return x


def _git_revision() -> Optional[str]:
    """HEAD commit of the repository, read from .git without running git. In a git worktree .git is a file
    'gitdir: <folder>'; that folder holds HEAD, and its file commondir names the folder of the shared refs."""
    from .paths import REPO
    git = REPO / ".git"
    try:
        common = git
        if git.is_file():
            line = git.read_text().strip()
            if not line.startswith("gitdir:"):
                return None
            git = Path(line.split(":", 1)[1].strip())
            if not git.is_absolute():
                git = REPO / git
            cd = git / "commondir"
            common = git / cd.read_text().strip() if cd.is_file() else git
        head = (git / "HEAD").read_text().strip()
        if not head.startswith("ref:"):
            return head
        ref = head.split(None, 1)[1]
        for base in (git, common):
            f = base / ref
            if f.is_file():
                return f.read_text().strip()
        packed = common / "packed-refs"
        if packed.is_file():
            for line in packed.read_text().splitlines():
                if line.endswith(" " + ref):
                    return line.split()[0]
    except OSError:
        pass
    return None


def _versions() -> dict:
    import scipy
    from . import __version__
    return {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
            "sublet": __version__}


def write_run(res: RunResult, inst: Instance, path, full: bool = False,
              extra_meta: Optional[dict] = None) -> None:
    """Write one run as JSON: meta, components, metrics, runtime, invariant_failures; with
    full=True also per_slot, leases, events and schedule (§5.9). `extra_meta` (MS2 C6: run-spec
    hash, policy id and parameters, seeds, information class) is added to meta."""
    from .config import config_hash
    meta = {"name": res.name, "policy": res.policy, "seed": res.seed,
            "config_hash": config_hash(inst.config), "git_revision": _git_revision(),
            "versions": _versions(), "argv": list(sys.argv)}
    if getattr(res, "seeds", None):
        meta["seeds"] = dict(res.seeds)
    if extra_meta:
        meta.update(extra_meta)
    out = {
        "meta": meta,
        "components": res.components,
        "metrics": run_metrics(res, inst),
        "runtime": res.runtime,
        "invariant_failures": res.invariant_failures,
    }
    if full:
        out["per_slot"] = res.per_slot
        out["leases"] = [vars(L) for L in res.leases]
        out["events"] = [[m, typ, payload] for m, typ, payload in res.events]
        out["schedule"] = {"mode": res.schedule.mode, "realized": res.schedule.realized,
                           "R": list(res.schedule.R)}
        out["violations"] = res.violations
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_jsonable(out), indent=1, allow_nan=False) + "\n")


def _ratio(a: float, b: Optional[float]) -> Optional[float]:
    if b is None or (isinstance(b, float) and math.isnan(b)):
        return None
    if b > 0:
        return float(a) / float(b)
    return 1.0 if a == 0 else math.inf


def ratio(alg_usd: float, bench: SolveResult) -> dict:
    """{'vs_objective': ALG / objective, 'vs_bound': ALG / dual bound, 'status', 'gap'}.
    vs_bound is an upper bound on the ratio to the optimum when the MILP stopped early, and the
    ratio to the LP bound for an LP. None where the benchmark has no value."""
    return {"vs_objective": _ratio(alg_usd, bench.objective),
            "vs_bound": _ratio(alg_usd, bench.dual_bound),
            "status": bench.status, "gap": bench.gap}


def aggregate(values: Sequence[float], seed: int = 0, B: int = 2000) -> dict:
    """{'n', 'median', 'p95', 'max', 'median_ci95': [lo, hi]}: the 95% percentile-bootstrap
    interval of the median from B resamples drawn with default_rng(seed)."""
    v = np.asarray(list(values), dtype=np.float64)
    n = len(v)
    if n == 0:
        return {"n": 0, "median": None, "p95": None, "max": None, "median_ci95": [None, None]}
    rng = np.random.default_rng(seed)
    meds = np.empty(B)
    rows = max(1, min(B, 4_000_000 // n))    # resample in chunks to bound memory
    for a in range(0, B, rows):
        b = min(B, a + rows)
        idx = rng.integers(0, n, size=(b - a, n))
        meds[a:b] = np.median(v[idx], axis=1)
    lo, hi = np.percentile(meds, [2.5, 97.5])
    return {"n": int(n), "median": float(np.median(v)), "p95": float(np.percentile(v, 95)),
            "max": float(v.max()), "median_ci95": [float(lo), float(hi)]}


__all__ = ["run_metrics", "write_run", "ratio", "aggregate"]
