"""Memory and time benchmark of the single-site DP and of the LP and MILP (design/sim_spec.md §9.3).

  mem_bench.py --list                     case ids, one per line, in run order
  mem_bench.py --case <id>                run one case in this process; writes out/mem_bench/<id>.json
  mem_bench.py --record-failure <id> --exit-code <rc>
                                          record a case that left no output file as "oom_at_3G"
  mem_bench.py --list-families            the LP/MILP families, one per line
  mem_bench.py --estimate <family> --days <d>
                                          estimate_size of the family's LP/MILP models at d days
                                          (counts only); writes out/mem_bench/est_<family>_<d>d.json
  mem_bench.py --summary                  fit peak memory to model size; writes out/mem_bench/summary.json

A case id is <family>_<method>_<days>d_<grid> (method lp, milp, eager or dp). One solve per process,
so that ru_maxrss belongs to that solve; run_mem_bench.sh runs each case in its own 3G scope, one at a
time. The configs build one site per layer (merge_identical_layers off, the default of §10 S32); the
E7 families (e7r, e7f, e7s) solve their LP on merged_relaxation(inst, sched), the lower bound that E7
runs at merge off (§10 S37), and record merged: true with the site counts and estimate_size of both
models; e1 and the DP families solve the unmerged instance. Before a case runs, its peak is predicted;
a case predicted above 2560 MB (MiB, as CAP_MB = 3072 for the 3G cap) is recorded as
"skipped_predicted_over_cap" instead (a MILP family always runs its 1-day case). Predictions: an LP
uses estimate_size(...)['parts']['est_mb_lp'] and a MILP estimate_size(...)['est_mb'] (the two rules
of §8.7) until the same family, method and grid has a measured shorter case, whose peak is then
scaled by the ratio of nonzeros; the DP uses n_states * T_b * 4 bytes
of choices plus the overhead measured on the family's 1-day case (before that, the state bound of
§7.5 plus 150 MB).
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import copy
import json
import math
import platform
import re
import resource
import socket
import subprocess
import sys
import time
import traceback
from pathlib import Path

SIM = Path(__file__).resolve().parents[1]
REPO = SIM.parents[1]
if str(SIM) not in sys.path:
    sys.path.insert(0, str(SIM))
OUT = SIM / "out" / "mem_bench"
CONFIGS = SIM / "configs"

CAP_MB = 3072.0              # MemoryMax=3G of run_mem_bench.sh (MiB)
SKIP_ABOVE_MB = 2560.0       # §9.3, §10 S37: do not run a case predicted above 2.5 GiB (MiB, as CAP_MB)
DP_BASE_MB = 150.0           # DP overhead before the family's 1-day case has run
METHODS = ("lp", "milp", "eager", "dp")

# family -> (config, [(method, days, grid), ...]) in run order (1-day cases first)
FAMILIES = {
    "dp_maas": ("bench_dp_maas.json", [("dp", 1, "fast"), ("dp", 2, "fast"), ("dp", 7, "fast")]),
    "dp_spot": ("bench_dp_spot.json", [("dp", 1, "fast"), ("dp", 2, "fast"), ("dp", 7, "fast")]),
    "e1": ("bench_e1.json", [("lp", 1, "slow"), ("milp", 1, "slow"), ("eager", 1, "slow"),
                             ("lp", 2, "slow"), ("milp", 2, "slow"), ("eager", 2, "slow"),
                             ("lp", 1, "fast"), ("milp", 1, "fast"), ("eager", 1, "fast")]),
    "e7r": ("bench_e7r.json", [("lp", 1, "slow"), ("lp", 2, "slow")]),
    "e7f": ("bench_e7f.json", [("lp", 1, "slow")]),
    "e7s": ("bench_e7s.json", [("lp", 1, "slow"), ("lp", 2, "slow")]),
}
# §10 S37: families whose LP is solved on merged_relaxation(inst, sched), as E7 runs at merge off
MERGED_FAMILIES = ("e7r", "e7f", "e7s")
CASE_RE = re.compile(r"^(?P<family>.+)_(?P<method>lp|milp|eager|dp)_(?P<days>\d+)d_(?P<grid>slow|fast|slow_lb)$")


# ---------------------------------------------------------------- cases
def case_id(family: str, method: str, days: int, grid: str) -> str:
    return f"{family}_{method}_{days}d_{grid}"


def all_cases() -> list[str]:
    return [case_id(f, m, d, g) for f, (_, cases) in FAMILIES.items() for (m, d, g) in cases]


def parse_case(cid: str) -> tuple[str, str, int, str]:
    mt = CASE_RE.match(cid)
    if mt is None or mt["family"] not in FAMILIES or cid not in all_cases():
        raise SystemExit(f"unknown case {cid!r}; see --list")
    return mt["family"], mt["method"], int(mt["days"]), mt["grid"]


def case_config(family: str, days: int) -> dict:
    """The family's config with the horizon set to `days` days."""
    with open(CONFIGS / FAMILIES[family][0]) as f:
        cfg = json.load(f)
    cfg = copy.deepcopy(cfg)
    cfg["time"]["horizon_min"] = int(days) * 1440
    return cfg


def out_path(cid: str) -> Path:
    return OUT / f"{cid}.json"


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=_json_default)
        f.write("\n")
    os.replace(tmp, path)


def _json_default(x):
    try:
        import numpy as np
        if isinstance(x, np.integer):
            return int(x)
        if isinstance(x, np.floating):
            return float(x)
        if isinstance(x, np.ndarray):
            return x.tolist()
    except ImportError:
        pass
    return str(x)


def read_json(path: Path):
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------- environment
def rss_peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def cgroup_info() -> dict:
    """cgroup v2 path of this process and its memory.max (Table 5.10's logs lack the cap)."""
    out = {"path": None, "memory_max": None, "memory_peak": None}
    try:
        with open("/proc/self/cgroup") as f:
            for line in f:
                parts = line.strip().split(":", 2)
                if len(parts) == 3 and parts[0] == "0":
                    out["path"] = parts[2]
        if out["path"] is not None:
            base = Path("/sys/fs/cgroup") / out["path"].lstrip("/")
            for key, fn in (("memory_max", "memory.max"), ("memory_peak", "memory.peak")):
                p = base / fn
                if p.exists():
                    out[key] = p.read_text().strip()
    except OSError as e:
        out["error"] = str(e)
    return out


def git_revision() -> dict:
    def run(*args):
        try:
            r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, timeout=30)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None
    status = run("status", "--porcelain", "--untracked-files=no")
    return {"head": run("rev-parse", "HEAD"), "dirty": None if status is None else bool(status)}


def environment() -> dict:
    import numpy
    import scipy
    return {"python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__,
            "host": socket.gethostname(), "platform": platform.platform(),
            "cpu_affinity": sorted(os.sched_getaffinity(0)), "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
            "cgroup": cgroup_info(), "git": git_revision()}


# ---------------------------------------------------------------- instance counts
def usable_triples(inst) -> list[tuple[int, int, int]]:
    """U of §8.2: (l, j, k) with k offered at l and a client of LLM j with delta < q_j at l."""
    import numpy as np
    out = []
    cl = inst.clients
    for l, s in enumerate(inst.sites):
        for j in range(inst.J):
            q = inst.llms[j].q_usd_per_h
            if not np.any((cl.llm == j) & (cl.delta_usd_per_h[:, l] < q)):
                continue
            out.extend((l, j, k) for k in s.menu)
    return out


def instance_counts(inst, sched, grid: str) -> dict:
    """Sites, clients, usable triples, starts and cohorts (§8.2; cohorts by the fine death for slow_lb)."""
    import numpy as np
    from sublet import reclaim
    g = inst.grid
    bench = "fast" if grid in ("fast", "slow_lb") else "slow"
    Db = g.bench_min(bench)
    phib = g.slow_min // Db
    lam_ms = inst.lam_ms()
    U = usable_triples(inst)
    n_starts = n_cohorts = 0
    starts = np.arange(g.T_slow, dtype=np.int64)
    for (l, j, k) in U:
        c = inst.contracts[k]
        Lam = math.ceil(int(lam_ms[j, l]) / (60000 * Db))
        for E, part in reclaim.cohorts(sched.R[l], starts, c, g, bench):
            keep = part[part * phib + Lam < E]
            if len(keep):
                n_starts += len(keep)
                n_cohorts += 1
    return {"n_sites": inst.m, "n_sites_by_kind": {kd: sum(s.kind == kd for s in inst.sites)
                                                    for kd in ("layer", "protected", "synthetic")},
            "n_clients": inst.n, "n_llms": inst.J, "n_contracts": inst.K, "n_usable_triples": len(U),
            "n_starts": n_starts, "n_cohorts": n_cohorts, "T_slow": g.T_slow, "T_bench": g.T_bench(grid)}


def dp_states(inst, grid: str) -> dict:
    """State count S = 2 (1 + Y) prod_l (1 + |O_l|)^N_Q of §7.5, from the instance (no solve). It is an
    upper bound: the DP stores only the loading sets that can occur (SolveResult.size['n_states'])."""
    g = inst.grid
    Db = g.bench_min(grid)
    phib = g.slow_min // Db
    j = int(inst.clients.llm[0])
    q = inst.llms[j].q_usd_per_h
    lam_ms = inst.lam_ms()
    usable = [l for l in range(inst.m) if inst.clients.delta_usd_per_h[0, l] < q]
    Y, lam_max, per_site = 0, 0, {}
    for l in usable:
        Lam = math.ceil(int(lam_ms[j, l]) / (60000 * Db))
        lam_max = max(lam_max, Lam)
        per_site[l] = len(inst.sites[l].menu)
        for k in inst.sites[l].menu:
            c = inst.contracts[k]
            A = max(math.ceil(c.prepaid_min / Db), Lam)
            Yo = A if c.protected else max(A, math.ceil(c.D_min(g.slow_min) / Db))
            Y += Yo - Lam + 1
    NQ = math.ceil(lam_max / phib)
    prod = 1
    for n in per_site.values():
        prod *= (1 + n) ** NQ
    S = 2 * (1 + Y) * prod
    return {"n_states_formula": S, "N_Q": NQ, "Y": Y, "T_bench": g.T_bench(grid),
            "choices_mb": S * g.T_bench(grid) * 4 / 2 ** 20}


# ---------------------------------------------------------------- predictions
def _measured(family, method, grid, days_below):
    """The longest measured ('ok') case of the same family, method and grid with fewer days."""
    best = None
    for (m, d, gr) in FAMILIES[family][1]:
        if m != method or gr != grid or d >= days_below:
            continue
        p = out_path(case_id(family, m, d, gr))
        if p.exists():
            r = read_json(p)
            if r.get("status") == "ok" and (best is None or r["days"] > best["days"]):
                best = r
    return best


def predict_lp(family, method, days, grid, est) -> tuple[float, str]:
    prev = _measured(family, method, grid, days)
    if prev is not None and prev.get("built", {}).get("nnz"):
        pred = prev["peak_rss_mb"] * est["nnz"] / prev["built"]["nnz"]
        return pred, f"scaled from {prev['id']} by nnz ratio"
    if method == "lp":
        # estimate_size's 'est_mb' is the MILP rule; the LP rule of §8.7 is in parts['est_mb_lp']
        return float(est["parts"]["est_mb_lp"]), "estimate_size parts.est_mb_lp (§8.7, LP rule)"
    return float(est["est_mb"]), "estimate_size est_mb (§8.7, MILP rule)"


def _dp_n_states(rec) -> int:
    """Measured state count of a DP case (the formula's bound if the solve did not report it)."""
    return int(rec.get("built", {}).get("n_states") or rec["dp_states"]["n_states_formula"])


def predict_dp(family, days, grid, st) -> tuple[float, str]:
    """Choices of n_states * T_b int32 codes plus an overhead. The state count does not depend on the
    horizon, so the family's measured shorter case gives both the count and the overhead."""
    prev = _measured(family, "dp", grid, days)
    if prev is not None and "dp_states" in prev:
        n = _dp_n_states(prev)
        prev_choices = n * prev["dp_states"]["T_bench"] * 4 / 2 ** 20
        over = max(0.0, prev["peak_rss_mb"] - prev_choices)
        return n * st["T_bench"] * 4 / 2 ** 20 + over, f"measured n_states and overhead of {prev['id']}"
    return st["choices_mb"] + DP_BASE_MB, f"formula choices + {DP_BASE_MB:.0f} MB"


def merged_model(inst, sched):
    """(inst_m, sched_m) of merged_relaxation (§10 S32): the lower-bound model of the E7 families."""
    from sublet.opt.relax import merged_relaxation
    inst_m, sched_m, _ = merged_relaxation(inst, sched)
    return inst_m, sched_m


# ---------------------------------------------------------------- one case
def run_case(cid: str) -> dict:
    family, method, days, grid = parse_case(cid)
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
    t_start = time.time()
    rec = {"id": cid, "family": family, "method": method, "days": days, "grid": grid,
           "config_file": FAMILIES[family][0], "started_unix": t_start, "env": environment()}
    try:
        from sublet import config as C
        from sublet.instance import build_instance
        from sublet.lender import Lender
        from sublet.opt import dp as DP
        from sublet.opt import milp as MILP
        from sublet.types import Schedule
        cfg = case_config(family, days)
        t0 = time.time()
        inst = build_instance(cfg)
        sched = Lender(inst, C.lender_model(inst.config), C.rng_streams(inst.seed)["lender"]).static_schedule()
        if sched is None:
            raise ValueError("the benchmark needs a static schedule")
        rec.update(config=inst.config.get("name"), config_hash=C.config_hash(inst.config),
                   horizon_min=inst.grid.horizon_min, instance_build_s=time.time() - t0,
                   rss_after_instance_mb=rss_peak_mb(), notes=list(inst.notes))
        bench = inst.config.get("bench", {})
        kw = dict(grid=grid, time_limit_s=float(bench.get("time_limit_s", 300.0)),
                  mip_rel_gap=float(bench.get("mip_rel_gap", 1e-4)), max_vars=int(bench.get("max_vars", 200_000)),
                  allow_large=True, return_plan=False)
        rec["merged"] = family in MERGED_FAMILIES
        if rec["merged"] and method != "dp":
            inst_u, sched_u = inst, sched
            inst, sched = merged_model(inst_u, sched_u)
            rec["n_sites_unmerged"], rec["n_sites_merged"] = inst_u.m, inst.m
            rec["estimate_unmerged"] = MILP.estimate_size(
                inst_u, Schedule.eager(inst_u) if method == "eager" else sched_u, grid=grid)
            del inst_u, sched_u
        bench_sched = Schedule.eager(inst) if method == "eager" else sched
        try:
            rec["instance"] = instance_counts(inst, bench_sched, grid)
        except Exception as e:                       # counts are diagnostics only
            rec["instance"] = {"error": repr(e)}
        if method == "dp":
            st = dp_states(inst, grid)
            rec["dp_states"] = st
            pred, basis = predict_dp(family, days, grid, st)
            always = False
        else:
            est = MILP.estimate_size(inst, bench_sched, grid=grid)
            rec["estimate"] = est
            pred, basis = predict_lp(family, method, days, grid, est)
            always = method in ("milp", "eager") and days == 1
        rec.update(predicted_peak_mb=pred, prediction_basis=basis)
        if pred > SKIP_ABOVE_MB and not always:
            rec["status"] = "skipped_predicted_over_cap"
            print(f"[mem_bench] {cid}: skipped, predicted {pred:.0f} MB ({basis})", flush=True)
        else:
            print(f"[mem_bench] {cid}: predicted {pred:.0f} MB ({basis}); solving", flush=True)
            if method == "dp":
                r = DP.solve_dp(inst, sched, grid=grid, return_plan=True)
            elif method == "lp":
                r = MILP.solve_lp(inst, sched, **kw)
            elif method == "milp":
                r = MILP.solve_opt(inst, sched, **kw)
            else:
                r = MILP.solve_eager(inst, **kw)
            rec.update(status="ok", built=dict(r.size), build_s=r.build_s, solve_s=r.solve_s,
                       rss_after_build_mb=r.size.get("rss_after_build_mb"), solve_status=r.status,
                       status_msg=r.status_msg, objective=r.objective, dual_bound=r.dual_bound, gap=r.gap,
                       solver_peak_rss_mb=r.peak_rss_mb)
    except Exception:
        rec["status"] = "error"
        rec["traceback"] = traceback.format_exc()
        print(rec["traceback"], file=sys.stderr, flush=True)
    rec["peak_rss_mb"] = rss_peak_mb()
    rec["wall_s"] = time.time() - t_start
    rec["env"]["cgroup_end"] = cgroup_info()
    write_json(out_path(cid), rec)
    print(f"[mem_bench] {cid}: {rec['status']}, peak RSS {rec['peak_rss_mb']:.0f} MB, "
          f"wall {rec['wall_s']:.1f} s", flush=True)
    return rec


def record_failure(cid: str, rc: int) -> None:
    """A case that was killed (exit 137) or left no output file is recorded as 'oom_at_3G' (not retried)."""
    family, method, days, grid = parse_case(cid)
    p = out_path(cid)
    if p.exists() and rc not in (137, -9):
        print(f"[mem_bench] {cid}: output exists (exit {rc}); nothing recorded", flush=True)
        return
    write_json(p, {"id": cid, "family": family, "method": method, "days": days, "grid": grid,
                   "status": "oom_at_3G", "exit_code": rc, "cap_mb": CAP_MB, "recorded_unix": time.time()})
    print(f"[mem_bench] {cid}: recorded oom_at_3G (exit {rc})", flush=True)


# ---------------------------------------------------------------- 7-day size estimates
def lp_families() -> list[str]:
    return [f for f, (_, cases) in FAMILIES.items() if any(m != "dp" for m, _, _ in cases)]


def estimate_family(family: str, days: int) -> dict:
    """estimate_size of every (method, grid) of the family's LP/MILP cases at `days` days (no solve)."""
    from sublet import config as C
    from sublet.instance import build_instance
    from sublet.lender import Lender
    from sublet.opt import milp as MILP
    from sublet.types import Schedule
    rec = {"family": family, "days": days, "env": environment(), "estimates": {},
           "merged": family in MERGED_FAMILIES}
    try:
        inst = build_instance(case_config(family, days))
        sched = Lender(inst, C.lender_model(inst.config), C.rng_streams(inst.seed)["lender"]).static_schedule()
        rec["config_hash"] = C.config_hash(inst.config)
        models = [("estimates", inst, sched)]
        if rec["merged"]:
            # 'estimates': the merged model that the E7 cases solve; 'estimates_unmerged': the unmerged one
            inst_m, sched_m = merged_model(inst, sched)
            rec["n_sites_unmerged"], rec["n_sites_merged"] = inst.m, inst_m.m
            rec["estimates_unmerged"] = {}
            models = [("estimates", inst_m, sched_m), ("estimates_unmerged", inst, sched)]
        for name, ins, sch in models:
            for (m, d, g) in FAMILIES[family][1]:
                key = f"{m}/{g}"
                if m == "dp" or key in rec[name]:
                    continue
                s = Schedule.eager(ins) if m == "eager" else sch
                rec[name][key] = MILP.estimate_size(ins, s, grid=g)
        rec["status"] = "ok"
    except Exception:
        rec["status"] = "error"
        rec["traceback"] = traceback.format_exc()
    rec["peak_rss_mb"] = rss_peak_mb()
    write_json(OUT / f"est_{family}_{days}d.json", rec)
    print(f"[mem_bench] estimate {family} {days}d: {rec['status']}, peak RSS {rec['peak_rss_mb']:.0f} MB", flush=True)
    return rec


# ---------------------------------------------------------------- summary
def _fit(xs, ys) -> dict:
    """Least squares peak = a + b x; with one point, b = y / x through the origin (a = 0)."""
    import numpy as np
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    if len(xs) == 0:
        return {"n_points": 0}
    if len(xs) == 1 or np.ptp(xs) == 0:
        return {"n_points": int(len(xs)), "a": 0.0, "b": float(ys.mean() / xs.mean()) if xs.mean() > 0 else None,
                "rule": "proportional (one size)"}
    A = np.vstack([np.ones_like(xs), xs]).T
    (a, b), *_ = np.linalg.lstsq(A, ys, rcond=None)
    return {"n_points": int(len(xs)), "a": float(a), "b": float(b), "rule": "least squares"}


def summary() -> dict:
    cases = []
    for cid in all_cases():
        p = out_path(cid)
        cases.append(read_json(p) if p.exists() else {"id": cid, "status": "not_run"})
    fits, week = {}, {}
    for family in lp_families():
        est7 = OUT / f"est_{family}_7d.json"
        e7 = read_json(est7) if est7.exists() else None
        for key in sorted({f"{m}/{g}" for (m, d, g) in FAMILIES[family][1] if m != "dp"}):
            m, g = key.split("/")
            pts = [c for c in cases if c.get("family") == family and c.get("method") == m
                   and c.get("grid") == g and c.get("status") == "ok"]
            fit = _fit([c["built"]["nnz"] for c in pts], [c["peak_rss_mb"] for c in pts])
            fit.update(x="nnz", cases=[c["id"] for c in pts])
            fits[f"{family}/{key}"] = fit
            w = {"estimate_7d": None, "predicted_peak_mb_7d": None}
            if e7 is not None and e7.get("status") == "ok" and key in e7["estimates"]:
                est = e7["estimates"][key]
                w["estimate_7d"] = {k: est.get(k) for k in ("n_vars", "n_int", "n_rows", "nnz", "est_mb")}
                if fit.get("b") is not None:
                    w["predicted_peak_mb_7d"] = fit["a"] + fit["b"] * est["nnz"]
                    w["fits_3GB"] = bool(w["predicted_peak_mb_7d"] < CAP_MB)
            week[f"{family}/{key}"] = w
    dp = {}
    for family in [f for f in FAMILIES if f not in lp_families()]:
        pts = [c for c in cases if c.get("family") == family and c.get("status") == "ok"]
        xs = [_dp_n_states(c) * c["dp_states"]["T_bench"] for c in pts]
        fit = _fit(xs, [c["peak_rss_mb"] for c in pts])
        fit.update(x="n_states * T_b", cases=[c["id"] for c in pts])
        seven = [c for c in cases if c.get("family") == family and c.get("days") == 7]
        pred7 = None
        if seven and "dp_states" in seven[0] and fit.get("b") is not None and pts:
            n = _dp_n_states(min(pts, key=lambda c: c["days"]))
            pred7 = fit["a"] + fit["b"] * n * seven[0]["dp_states"]["T_bench"]
        dp[family] = {"fit": fit, "measured_7d": seven[0].get("peak_rss_mb") if seven and
                      seven[0].get("status") == "ok" else None, "status_7d": seven[0].get("status") if seven else None,
                      "predicted_peak_mb_7d": pred7}
    # per family and grid: a family with LPs on two grids (e1: slow and fast) gets one flag per grid
    week_lp = {}
    for family in lp_families():
        vals = {k.rsplit("/", 1)[1]: v.get("fits_3GB") for k, v in week.items() if k.startswith(f"{family}/lp/")}
        week_lp[family] = vals or None
    out = {"spec": "design/sim_spec.md §9.3", "generated_unix": time.time(), "cap_mb": CAP_MB,
           "skip_above_mb": SKIP_ABOVE_MB, "cases": cases, "lp_milp_fits": fits, "week_predictions": week,
           "dp": dp, "week_scale_lp_fits_3GB": week_lp}
    write_json(OUT / "summary.json", out)
    print(json.dumps({"week_scale_lp_fits_3GB": week_lp,
                      "statuses": {c["id"]: c.get("status") for c in cases}}, indent=1), flush=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--list-families", action="store_true")
    g.add_argument("--case")
    g.add_argument("--record-failure", metavar="CASE")
    g.add_argument("--estimate", metavar="FAMILY")
    g.add_argument("--summary", action="store_true")
    ap.add_argument("--exit-code", type=int, default=-1)
    ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args(argv)
    if a.list:
        print("\n".join(all_cases()))
    elif a.list_families:
        print("\n".join(lp_families()))
    elif a.case:
        rec = run_case(a.case)
        return 0 if rec["status"] in ("ok", "skipped_predicted_over_cap") else 1
    elif a.record_failure:
        record_failure(a.record_failure, a.exit_code)
    elif a.estimate:
        if a.estimate not in FAMILIES:
            raise SystemExit(f"unknown family {a.estimate!r}")
        return 0 if estimate_family(a.estimate, a.days)["status"] == "ok" else 1
    else:
        summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
