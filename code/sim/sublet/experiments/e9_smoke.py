"""E9 smoke run of MS2: one case per process (design/sim_spec_ms2.md §18).

  python -m sublet.experiments.e9_smoke --list                       case ids, one per line, in run order
  python -m sublet.experiments.e9_smoke --case <id> [--out DIR]       run one case; writes <id>.json
  python -m sublet.experiments.e9_smoke --record-failure <id> --exit-code <rc>
                                                                    a case killed by the cap (exit 137) or
                                                                    without an output file: "oom_at_3G"
  python -m sublet.experiments.e9_smoke --summary                    summary.json: every case, the targets
                                                                    P1-P4 with measured values and pass
                                                                    flags, the MS2 pass flag, the git revision

Cases (§18.2):
  pd_bench        the instances of code/analysis/bench/pd_time.py (random_instance(default_rng(1), T, m, J=2,
                  n, K=3) for (T, m, n) in (48, 6, 12), (96, 12, 24), (96, 24, 24)) plus (96, 48, 24),
                  (96, 96, 24), (96, 160, 24): the reference pd.FracPD and VecPD on the same requests, timed
                  in this process (P1); it replaces code/analysis/bench/pd_time.log as the PD measurement.
  a2_ex1d         example_1day.json (needs a12), A2 with rbar = 1, 1-min routing, 1 day.
  a6_ex1d         example_1day.json, A6 practical, 1-min routing, 1 day.
  a6_e7r_1d_slow  bench_e7r.json, A6 practical, slow grid (fast slot = slow slot), 1 day.
  a6_e7r_7d       bench_e7r.json, horizon 10080 min, A6 practical, one seed, 1-min routing (P2, P3).
  fam_m8          from_core(Fam(8, 16, 2, 1, 96).core_instance()) under the safe_site lender: A2 (rbar = 1),
                  RR_RENEW and MARKING (I2).
  a1_single_7d    ms2_single_site.json, 7 days, A1 with contract_rev = 's5_tau5_H60', 1-min routing.
  bl_e7r_1d       bench_e7r.json, BL1, BL3, BL4 (demand 'previous') and BL5, slow grid, 1 day.
Every engine case sets engine.check_invariants = true in its run spec (bench_e7r.json and
bench_dp_maas.json switch the checks off; with them off an empty invariant_failures says nothing).
A case file holds metrics.write_run's output of each run plus wall time, wall time per simulated
hour, slow and fast step P50/P99, policy_act_s P50/P99/maximum, routing time, LP calls and time per
call, the PD statistics (§5.6), peak RSS, invariant_failures and gpu_only_lease_slots.
Run every case through run_e9_smoke.sh (each in its own 3 GB scope, one at a time).
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import json
import resource
import sys
import tempfile
import time
import traceback
from pathlib import Path

import numpy as np

from ..paths import SIM_OUT, import_ref

OUT = SIM_OUT / "e9_smoke"
CAP_MB = 3072.0
PD_CASES = [(48, 6, 12), (96, 12, 24), (96, 24, 24), (96, 48, 24), (96, 96, 24), (96, 160, 24)]
REF_PD_LOG = "code/analysis/bench/pd_time.log"
TARGETS = {"P1": "VecPD mean time per request <= pd.FracPD's on every pd_bench instance (same process)",
           "P2": "A6 on bench_e7r: policy_act_s_mean <= 0.1 s and policy_act_s_p99 <= 2 s",
           "P3": "A6 on bench_e7r, one week, 1-min routing: wall time <= 2 h on one core",
           "P4": "peak RSS <= 1.5 GB per policy run"}


def _spec(name, instance, policy, params=None, overrides=None, lender_model=None):
    return {"schema_version": 1, "name": name, "instance": instance, "overrides": dict(overrides or {}),
            "lender_model": dict(lender_model or {}), "engine": {"check_invariants": True},
            "policy": {"id": policy, "params": dict(params or {})}, "seeds": {}, "bench": None,
            "out": f"code/sim/out/e9_smoke/{name}"}


DAY = {"time.horizon_min": 1440}
SLOW_GRID = {"time.fast_slot_min": 5}
CASES = {
    "pd_bench": None,
    "a2_ex1d": [_spec("a2_ex1d", "example_1day.json", "A2", {"rbar": 1}, {**DAY, "time.fast_slot_min": 1})],
    "a6_ex1d": [_spec("a6_ex1d", "example_1day.json", "A6", {"variant": "practical"},
                      {**DAY, "time.fast_slot_min": 1})],
    "a6_e7r_1d_slow": [_spec("a6_e7r_1d_slow", "bench_e7r.json", "A6", {"variant": "practical"}, {**DAY, **SLOW_GRID})],
    "a6_e7r_7d": [_spec("a6_e7r_7d", "bench_e7r.json", "A6", {"variant": "practical"},
                        {"time.horizon_min": 10080, "time.fast_slot_min": 1})],
    "fam_m8": "fam",
    "a1_single_7d": [_spec("a1_single_7d", "ms2_single_site.json", "A1", {"contract_rev": "s5_tau5_H60"},
                           {"time.horizon_min": 10080, "time.fast_slot_min": 1})],
    "bl_e7r_1d": [_spec(f"bl_e7r_1d_{p}", "bench_e7r.json", p, params, {**DAY, **SLOW_GRID})
                  for p, params in (("BL1", {}), ("BL3", {}), ("BL4", {"demand": "previous"}), ("BL5", {}))],
}


def _peak_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def _git_revision():
    from ..metrics import _git_revision as g
    try:
        return g()
    except Exception:          # informative only
        return None


# ---------------------------------------------------------------- PD microbenchmark (P1)
def _requests(I):
    return [(c, t) for t in range(I.T) for c in range(I.n) if I.active[c, t]]


def pd_bench() -> dict:
    core = import_ref("core")
    pd = import_ref("pd")
    from ..algos.pd_core import VecPD, problem_from_core
    rows = []
    for (T, m, n) in PD_CASES:
        I = core.random_instance(np.random.default_rng(1), T=T, m=m, J=2, n=n, K=3)
        reqs = _requests(I)
        t0 = time.perf_counter()
        ref = pd.FracPD(I).run()
        t_ref = time.perf_counter() - t0
        t0 = time.perf_counter()
        vec = VecPD(problem_from_core(I))
        for c, t in reqs:
            vec.request(c, t)
        t_vec = time.perf_counter() - t0
        st = vec.stats_summary() if hasattr(vec, "stats_summary") else dict(vec.stats)
        P_ref, P_vec = ref.primal(), vec.primal()
        rows.append({"T": T, "m": m, "n": n, "K": 3, "requests": len(reqs), "candidates_per_request_max": m * 3,
                     "ref_time_s": t_ref, "ref_ms_per_request": 1e3 * t_ref / len(reqs),
                     "vec_time_s": t_vec, "vec_ms_per_request": 1e3 * t_vec / len(reqs),
                     "vec_stats": st, "P_ref": P_ref, "P_vec": P_vec,
                     "P_rel_diff": abs(P_vec - P_ref) / max(1.0, abs(P_ref)),
                     "P1_pass": bool(t_vec <= t_ref)})
        print(f"[pd_bench] T={T} m={m} n={n}: requests {len(reqs)}, ref {1e3 * t_ref / len(reqs):.3f} ms, "
              f"vec {1e3 * t_vec / len(reqs):.3f} ms per request", flush=True)
    return {"kind": "pd_bench", "replaces": REF_PD_LOG, "rows": rows,
            "P1_pass": all(r["P1_pass"] for r in rows)}


# ---------------------------------------------------------------- engine runs
def _run_record(res, inst, extra_meta: dict, wall_s: float, pol) -> dict:
    from ..metrics import write_run
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "run.json"
        write_run(res, inst, p, extra_meta=extra_meta)
        rec = json.loads(p.read_text())
    rt = res.runtime
    hours = inst.grid.horizon_min / 60.0
    rep = res.metrics.get("policy") or {}
    pd_stats = rep.get("pd")
    if pd_stats is None and isinstance(rep.get("inner"), dict):
        pd_stats = rep["inner"].get("pd")
    lp_calls = rt.get("routing_lp_calls") or 0
    rec["smoke"] = {"wall_s": wall_s, "wall_s_per_sim_hour": wall_s / hours if hours else None,
                    "engine_wall_s": rt.get("wall_s"),
                    "slow_step_s_p50": rt.get("slow_step_s_p50"), "slow_step_s_p99": rt.get("slow_step_s_p99"),
                    "fast_step_s_p50": rt.get("fast_step_s_p50"), "fast_step_s_p99": rt.get("fast_step_s_p99"),
                    "policy_act_s_mean": rt.get("policy_act_s_mean"), "policy_act_s_p50": rt.get("policy_act_s_p50"),
                    "policy_act_s_p99": rt.get("policy_act_s_p99"), "policy_act_s_max": rt.get("policy_act_s_max"),
                    "routing_s": rt.get("routing_s"), "routing_lp_calls": lp_calls,
                    "routing_lp_s_per_call": (rt.get("routing_lp_s", 0.0) / lp_calls) if lp_calls else None,
                    "n_alive_leases_max": rt.get("n_alive_leases_max"), "pd": pd_stats,
                    "peak_rss_mb": _peak_rss_mb(), "invariant_failures": list(res.invariant_failures),
                    "gpu_only_lease_slots": int(res.metrics.get("gpu_only_lease_slots", 0)),
                    "check_invariants": True, "horizon_min": inst.grid.horizon_min,
                    "fast_min": inst.grid.fast_min, "slow_min": inst.grid.slow_min, "sites": inst.m,
                    "clients": inst.n, "policy": type(pol).__name__}
    return rec


def run_spec_case(spec: dict) -> dict:
    from .. import config as C
    from ..algos import registry
    from ..drivers.run import build, driver_inputs, load_run_spec, make_policy
    from ..engine import simulate
    spec = load_run_spec(spec)
    c = spec["seeds"]["config"][0]
    pid, params = spec["policy"]["id"], spec["policy"]["params"]
    t0 = time.perf_counter()
    inst, model, ecfg = build(spec, c)
    assert ecfg.check_invariants
    inputs, imeta = driver_inputs(pid, params, inst)
    pol = make_policy(spec, inst, inputs=inputs)
    res = simulate(inst, pol, model, ecfg, lender_seed=c, policy_seed=c)
    wall = time.perf_counter() - t0
    extra = {"run_spec_hash": C.config_hash(spec), "run_spec_name": spec["name"], "policy_id": pid,
             "params": {**params, **(pol.params() or {})}, "seeds": res.seeds,
             "info_class": registry.info_class(pid, params, model.information), "driver_inputs": imeta,
             "e9_case": spec["name"]}
    return _run_record(res, inst, extra, wall, pol)


def fam_case() -> list[dict]:
    """fam_m8: A2 (rbar = 1), RR_RENEW and MARKING (I2) on from_core(Fam(8, 16, 2, 1, 96)) under safe_site."""
    from ..drivers.run import make_policy
    from ..engine import EngineConfig, simulate
    from ..instance import from_core
    from ..types import LenderModel
    fam = import_ref("fam")
    F = fam.Fam(8, 16, 2, 1, 96)
    out = []
    for pid, params, info in (("A2", {"rbar": 1}, "I1"), ("RR_RENEW", {}, "I1"), ("MARKING", {}, "I2")):
        t0 = time.perf_counter()
        inst, _ = from_core(F.core_instance(), [np.zeros(0, dtype=np.int64)] * F.m)
        pol = make_policy({"policy": {"id": pid, "params": params}}, inst)
        res = simulate(inst, pol, LenderModel(schedule="safe_site", information=info), EngineConfig(check_invariants=True),
                       lender_seed=0, policy_seed=0)
        wall = time.perf_counter() - t0
        out.append(_run_record(res, inst, {"policy_id": pid, "params": params, "seeds": res.seeds,
                                           "info_class": "online-" + info, "e9_case": f"fam_m8_{pid}",
                                           "instance": "from_core(Fam(8, 16, 2, 1, 96).core_instance())",
                                           "lender_model": {"schedule": "safe_site", "information": info}},
                               wall, pol))
    return out


def run_case(cid: str, out: Path) -> dict:
    if cid not in CASES:
        raise SystemExit(f"unknown case {cid!r}; known {list(CASES)}")
    t0 = time.perf_counter()
    rec = {"case": cid, "status": "ok", "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if cid == "pd_bench":
        rec.update(pd_bench())
    elif cid == "fam_m8":
        rec["runs"] = fam_case()
    else:
        rec["runs"] = [run_spec_case(s) for s in CASES[cid]]
    rec["wall_s"] = time.perf_counter() - t0
    rec["peak_rss_mb"] = _peak_rss_mb()
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{cid}.json").write_text(json.dumps(rec, indent=1, default=_json_default) + "\n")
    return rec


def _json_default(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    return str(x)


def record_failure(cid: str, rc: int, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{cid}.json"
    if p.is_file() and p.stat().st_size > 0:
        return
    status = "oom_at_3G" if rc == 137 else f"failed (exit code {rc})"
    p.write_text(json.dumps({"case": cid, "status": status, "exit_code": rc}, indent=1) + "\n")


# ---------------------------------------------------------------- summary
def _runs(rec: dict) -> list:
    return rec.get("runs") or []


def summary(out: Path) -> dict:
    recs = {}
    for cid in CASES:
        p = out / f"{cid}.json"
        recs[cid] = json.loads(p.read_text()) if p.is_file() else {"case": cid, "status": "missing"}
    cases = []
    for cid, r in recs.items():
        runs = _runs(r)
        fails = [f for x in runs for f in x.get("smoke", {}).get("invariant_failures", [])]
        gpu_only = sum(x.get("smoke", {}).get("gpu_only_lease_slots", 0) for x in runs)
        ok = r.get("status") == "ok" and not fails and gpu_only == 0
        cases.append({"case": cid, "status": r.get("status"), "wall_s": r.get("wall_s"),
                      "peak_rss_mb": r.get("peak_rss_mb"), "runs": len(runs), "invariant_failures": len(fails),
                      "gpu_only_lease_slots": gpu_only, "pass": bool(ok)})
    tg = {}
    pdb = recs.get("pd_bench", {})
    tg["P1"] = {"target": TARGETS["P1"], "pass": pdb.get("P1_pass") if pdb.get("status") == "ok" else None,
                "values": [{k: x[k] for k in ("T", "m", "n", "ref_ms_per_request", "vec_ms_per_request")}
                           for x in pdb.get("rows", [])]}
    e7 = [x["smoke"] for cid in ("a6_e7r_7d", "a6_e7r_1d_slow") for x in _runs(recs.get(cid, {}))]
    wk = [x["smoke"] for x in _runs(recs.get("a6_e7r_7d", {}))]
    tg["P2"] = {"target": TARGETS["P2"],
                "values": [{"policy_act_s_mean": s["policy_act_s_mean"], "policy_act_s_p99": s["policy_act_s_p99"],
                            "horizon_min": s["horizon_min"], "fast_min": s["fast_min"]} for s in e7],
                "pass": (all(s["policy_act_s_mean"] is not None and s["policy_act_s_mean"] <= 0.1
                             and s["policy_act_s_p99"] <= 2.0 for s in e7) if e7 else None)}
    tg["P3"] = {"target": TARGETS["P3"], "values": [s["wall_s"] for s in wk],
                "pass": (all(s["wall_s"] <= 7200.0 for s in wk) if wk else None)}
    rss = [r.get("peak_rss_mb") for r in recs.values() if r.get("status") == "ok" and r.get("case") != "pd_bench"]
    tg["P4"] = {"target": TARGETS["P4"], "values": {cid: recs[cid].get("peak_rss_mb") for cid in recs},
                "pass": (all(v <= 1536.0 for v in rss) if rss else None)}
    out_d = {"meta": {"script": "code/sim/sublet/experiments/e9_smoke.py", "spec": "design/sim_spec_ms2.md §18",
                      "git_revision": _git_revision(), "written": time.strftime("%Y-%m-%dT%H:%M:%S"),
                      "cap_mb": CAP_MB, "note": "targets P1-P4 do not block MS2 (§1.4, M53)"},
             "cases": cases, "targets": tg,
             "ms2_pass": all(c["pass"] for c in cases)}
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(out_d, indent=1, default=_json_default) + "\n")
    return out_d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--case")
    g.add_argument("--record-failure", metavar="CASE")
    g.add_argument("--summary", action="store_true")
    ap.add_argument("--exit-code", type=int, default=1)
    ap.add_argument("--out", type=Path, default=OUT, help="output folder (default code/sim/out/e9_smoke)")
    a = ap.parse_args(argv)
    if a.list:
        print("\n".join(CASES))
    elif a.case:
        try:
            rec = run_case(a.case, a.out)
        except Exception:
            traceback.print_exc()
            a.out.mkdir(parents=True, exist_ok=True)
            (a.out / f"{a.case}.json").write_text(json.dumps({"case": a.case, "status": "error",
                                                              "traceback": traceback.format_exc(),
                                                              "peak_rss_mb": _peak_rss_mb()}, indent=1) + "\n")
            return 1
        print(f"[e9_smoke] {a.case}: {rec['status']} in {rec['wall_s']:.1f} s, peak RSS {rec['peak_rss_mb']:.0f} MB",
              flush=True)
    elif a.record_failure:
        record_failure(a.record_failure, a.exit_code, a.out)
    else:
        s = summary(a.out)
        print(json.dumps({"cases": s["cases"], "ms2_pass": s["ms2_pass"]}, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
