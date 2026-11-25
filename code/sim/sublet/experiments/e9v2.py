"""E9 v2: scalability of Sublet itself, with the guard's per-slot overhead over A9 (design/ms7/plan.md X3, D6;
design/ms7/feasibility/sens.md §2 D, §3 item 4; change C56). Exploratory, after the MS5b freeze; s1v2's registration
gate applies (s1v2.gate). Run it last and alone on the host, after S1 v2 (as run_e9.sh after run_s1.sh).

Instances: MS5's E9 points unchanged (e9.RUN_POINTS: e7f SML at V in {1, 2, 4, 8, 16, 32, 64}, e7f S and ML at V 8,
e7r SML at the seven V; e9.point_spec, e9.build_point: one simulated day of 1-min routing on 5-min slow slots, the
trace lender, engine.check_invariants true), alignments c in {1, 2, 3, 4} (config seed = lender seed), policy seed 0.
The one-day merged LP bounds do not depend on the policy and are reused: the summary copies out/e9/summary.json's
'lp' block with its sha256, and check E9v2-4 compares every run's instance hash with E9's at the same point and
alignment, so that E9's LPs bound these instances.

Policies (TAGS): Sublet (A8P around A9 at 'lb', ms5b_common.sublet_v2_params) and A9 (its inner policy alone), on each
point's own instance. The guard's per-slot overhead (the T0g test, LB', the safe expert and the projection) is Sublet's
time minus A9's in the engine's RunResult.runtime (C27's keys and policy_act_s_*: the act time per slow slot), computed
by ms7_sens_analysis.py; Sublet's runs make different decisions from A9's only at projected slots, so the difference of
the act times per slot is the guard's own work plus the inner policy's work on a different state there.

The exact split (optional, §2 D). TimedProjectedGuarded, defined here and not in algos/guard.py, is ProjectedGuarded
with timers around act, the inner policy's act (and on_fast), the OnlineLB's step, the safe expert's step, T0gBound's
begin, the candidate lists and every evaluation (_evaluate: the first of a slot is the test of A_E(t), the later ones
the projection's); it adds no state that the policy reads and returns every result unchanged. A split job runs Sublet
with it at one alignment per point; its run must equal the uninstrumented run job of the same point and alignment bit
for bit (check E9v2-5: ALG, the components, the per-slot cost series, the policy report and the schedule hash, by their
sha256), else its split is not used.

Jobs (every job 'alone', holding every slot, ids by ms3_common.job_id):
  e9v2:run:pt=<point>:pol=<tag>:c=<c>   one simulated day (16 points x 2 tags x 4 alignments = 128); the first in the
                                        list is FIRST_JOB (e7f_V64_SML, Sublet, c 1), which run_e9v2.sh runs alone and
                                        first, under FIRST_LIMIT_S, to set the other limits
  e9v2:split:pt=<point>:c=<c>           Sublet with TimedProjectedGuarded at the first alignment (16)
Limits (`--limits --out DIR`: '<limit s> <job id>' per job): FIRST_LIMIT_S for the first job; for the others the
largest of LIMIT_FLOOR_S (E9's limits doubled at its large points), three times the job's estimate, and, once the
first job has an 'ok' record, three times the estimate scaled by the first job's wall time over its estimate.
Estimates (est_run_s, labeled estimates, not results): Sublet's day 2.0 x E9's measured Sublet-MS4 day at the point
(e9_day_s; the feasibility smoke at V 32), 3.8 x at V 64 (this build's 2-hour smoke at e7f_V64_SML under a host load
of 8, an extrapolation of the first two hours), A9's 0.35 x Sublet's, each plus A9's contract table (about 500 s at
V 64); about 31 h of single-worker time, 24 h of it at V 64, 4.7 h of it in the 16 split jobs (which run last);
likely high.

Command line (ms3_common.main), run from code/sim:
  python -m sublet.experiments.e9v2 --list | --job ID | --summary | --estimate | --manifest | --check-start [--out DIR]
  python -m sublet.experiments.e9v2 --limits [--out DIR]
Reduced runs (MS3_E9V2_REDUCED=1, run_e9v2.sh --reduced): every point and kind at alignment 1 with a 2-hour horizon;
the gate is recorded, not enforced; never a result.

Outputs <root>/out/e9v2/ (jobs/, logs/, runs/ (not versioned), manifest.json, summary.json, tables.md, run_e9v2.log).
summary.json: meta (grid, tags, limits, the gate, sources), points.<point> {sizes, policies.<tag> (e9.policy_entry:
by_alignment with e9's RUN_METRICS and the act times, median, min, max), split {the timed parts per slot, identity}},
lp (E9's, copied), checks E9v2-1 ... E9v2-6.

Status labels: as s1v2 (E9 v2 is a system measurement with no claim).
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path
from typing import Mapping, Optional

import numpy as np

from .. import paths
from ..algos.guard import ProjectedGuarded
from . import e7
from . import e7h
from . import e9
from . import ms3_common as mc
from . import ms4_common as m4
from . import ms5b_common as m5
from . import s1v2 as sv
from .ms3_common import Job, job_id, num_key, put

EXP = "e9v2"
SPEC = "design/ms7/feasibility/sens.md §2 D, §3 item 4 (C56)"
TAGS = ("Sublet", "A9")
RUN_POINTS = e9.RUN_POINTS
ALIGNMENTS = e9.ALIGNMENTS
POLICY_SEED = e9.POLICY_SEED
FIRST = ("e7f_V64_SML", "Sublet", 1)               # timed alone first (§2 D)
FIRST_LIMIT_S = 28800                              # 8 h; its estimate is about 2.8 h (est_run_s)
LIMIT_MIN_S = e9.RUN_LIMIT_DEFAULT_S               # 900 s
LIMIT_FACTOR = 3.0
LIMIT_FLOOR_S = {"e7f_V16_SML": {"Sublet": 3600, "A9": 1800}, "e7f_V32_SML": {"Sublet": 14400, "A9": 3600},
                 "e7f_V64_SML": {"Sublet": 28800, "A9": 14400}, "e7r_V64_SML": {"Sublet": 14400, "A9": 3600}}
# Sublet v2's day over E9's measured Sublet-MS4 day at the point (e9_day_s: out/e9/summary.json points.<p>.policies.
# Sublet.median.job_s; e9.est_run_s where the summary has none) (estimates, not results): 2.0 by the feasibility smoke
# at e7f_V32 (56 s/h against E9's measured 27.4 s/h), 3.8 at V 64 by this build's reduced smoke (e7f_V64_SML, the first
# 2 hours, host load 8: 400 s/h against E9's measured 105.6 s/h; slow steps P50 2.0 s, max 247 s). The first hours
# hold the largest steps, so the day's estimate is high; run_e9v2.sh rescales the limits by the first job's wall time.
SUBLET_OVER_MS4 = {64: 3.8}
A9_OVER_SUBLET = 0.35
# A9's contract table (A9.3), built in reset by A9 and by Sublet's inner A9 (scratch timings of this build at e7f, 2
# hours: V 16 26 s, V 32 100 s; V 64 492 s of reset in the smoke run; the first call in a process about 45 s)
A9_TABLE_S = {32: 100.0, 64: 500.0}
EST_TABLE_S = 45.0
REDUCED_ENV = "MS3_E9V2_REDUCED"
E9_SUMMARY = paths.SIM_OUT / "e9" / "summary.json"          # versioned (MS5, commit 622cf450)
E9_SUMMARY_REL = "code/sim/out/e9/summary.json"
ACT_KEYS = ("policy_act_s_mean", "policy_act_s_p50", "policy_act_s_p99", "policy_act_s_max")
SPLIT_KEYS = ("act", "inner_act", "fast", "inner_fast", "lb", "safe", "test_begin", "test_eval", "proj_candidates",
              "proj_eval")
RUN_METRICS = e9.RUN_METRICS + ACT_KEYS + ("policy_act_s_sum",)
CHECK_IDS = ("E9v2-1", "E9v2-2", "E9v2-3", "E9v2-4", "E9v2-5", "E9v2-6")
CHECK_CLAIMS = {
    "E9v2-1": "every run job finished with status ok inside the 3 GB cap, with no invariant failure (e9's E9-1)",
    "E9v2-2": "per run, C27's counts equal the grid and the step sums with reset_s and finish_s do not exceed wall_s "
              "by more than 1e-6 s (e9's E9-2)",
    "E9v2-3": "every Sublet run: certificate available and held in Theorem W's proven cases, the envelope holds, no "
              "projecting run aborts while S follows FB and T0g stays in bound form (Proposition P)",
    "E9v2-4": "every run's instance equals E9's at the same point and alignment (instance hash), so E9's one-day LP "
              "bounds (copied) bound these instances",
    "E9v2-5": "every split run equals the uninstrumented Sublet run of its point and alignment bit for bit (ALG, the "
              "components, the per-slot cost series, the policy report, the schedule hash)",
    "E9v2-6": "per point: the loops per simulated hour of Sublet and A9 against real time and the act time per slow "
              "slot (informative)"}


def reduced() -> bool:
    return os.environ.get(REDUCED_ENV, "0") == "1"


def design() -> dict:
    red = reduced()
    return {"reduced": red, "alignments": (1,) if red else ALIGNMENTS, "policy_seed": POLICY_SEED,
            "horizon_min": sv.REDUCED_HORIZON_MIN if red else e9.DAY_MIN}


def run_id(point: str, tag: str, c: int) -> str:
    return job_id(EXP, "run", pt=point, pol=tag, c=int(c))


def split_id(point: str, c: int) -> str:
    return job_id(EXP, "split", pt=point, c=int(c))


FIRST_JOB = run_id(*FIRST)


def run_path(out, jid: str) -> Path:
    return Path(out) / "runs" / mc.job_file_name(jid)


_E9_DAY: dict = {}


def e9_day_s(point: str) -> float:
    """E9's measured Sublet-MS4 day at the point (the median job_s over its alignments in out/e9/summary.json, read
    once), else e9.est_run_s's estimate (no summary, or no value there)."""
    if "points" not in _E9_DAY:
        _E9_DAY["points"] = ((mc.read_json(E9_SUMMARY) or {}).get("points") or {}) if E9_SUMMARY.is_file() else {}
    v = ((((_E9_DAY["points"].get(point) or {}).get("policies") or {}).get("Sublet") or {}).get("median") or {}) \
        .get("job_s")
    return float(v) if v is not None and float(v) > 0 else float(e9.est_run_s(point, "Sublet"))


def est_run_s(point: str, tag: str) -> float:
    """A one-day run's seconds (estimate): the loops at SUBLET_OVER_MS4[V] (default 2.0) x E9's Sublet-MS4 day
    (e9_day_s) for Sublet and A9_OVER_SUBLET x that for A9, each plus A9's contract table (A9_TABLE_S[V], default
    EST_TABLE_S), which both build in their reset."""
    V = e9.parse_point(point)[1]
    s = SUBLET_OVER_MS4.get(V, 2.0) * e9_day_s(point)
    table = A9_TABLE_S.get(V, EST_TABLE_S)
    return (s if tag == "Sublet" else A9_OVER_SUBLET * s) + table


def static_limit_s(point: str, tag: str, est_s: float) -> int:
    return int(max(LIMIT_FLOOR_S.get(point, {}).get(tag, LIMIT_MIN_S), math.ceil(LIMIT_FACTOR * float(est_s))))


def jobs() -> list:
    """FIRST_JOB, the other runs in the order of the points (per point Sublet, then A9, over the alignments), then
    the split jobs; every job 'alone'."""
    d = design()
    hz, scale = d["horizon_min"], d["horizon_min"] / float(e9.DAY_MIN)
    runs = []
    for point in RUN_POINTS:
        base, V, llms = e9.parse_point(point)
        for t in TAGS:
            for c in d["alignments"]:
                est = e9.EST_JOB_S + scale * est_run_s(point, t)
                runs.append(Job(run_id(point, t, c), "alone",
                                {"kind": "run", "point": point, "base": base, "V": V, "llm_set": llms, "tag": t,
                                 "c": int(c), "policy_seed": POLICY_SEED, "horizon_min": hz,
                                 "limit_s": FIRST_LIMIT_S if run_id(point, t, c) == FIRST_JOB
                                 else static_limit_s(point, t, est)}, est))
    first = [j for j in runs if j.id == FIRST_JOB]
    out = first + [j for j in runs if j.id != FIRST_JOB]
    c0 = int(d["alignments"][0])
    for point in RUN_POINTS:
        base, V, llms = e9.parse_point(point)
        est = e9.EST_JOB_S + scale * est_run_s(point, "Sublet")
        out.append(Job(split_id(point, c0), "alone",
                       {"kind": "split", "point": point, "base": base, "V": V, "llm_set": llms, "tag": "Sublet",
                        "c": c0, "policy_seed": POLICY_SEED, "horizon_min": hz,
                        "limit_s": static_limit_s(point, "Sublet", est)}, est))
    return out


def limits(out=None) -> list:
    """[(limit_s, job id)]: FIRST_LIMIT_S for FIRST_JOB; for the others the static limit, or, once FIRST_JOB has an
    'ok' record under `out`, the larger of it and LIMIT_FACTOR x the estimate x (the first job's wall time over its
    estimate)."""
    js = jobs()
    first = next((j for j in js if j.id == FIRST_JOB), None)
    r = None
    if out is not None and first is not None:
        rec = mc.read_record(out, FIRST_JOB) or {}
        if rec.get("status") == "ok" and rec.get("wall_s") and first.est_s:
            r = float(rec["wall_s"]) / float(first.est_s)
    lines = []
    for j in js:
        lim = int(j.params["limit_s"])
        if j.id != FIRST_JOB and r is not None:
            lim = max(lim, int(math.ceil(LIMIT_FACTOR * float(j.est_s) * r)))
        lines.append((lim, j.id))
    return lines


# ---------------------------------------------------------------- the timed guard (exact split, §2 D)
class TimedProjectedGuarded(ProjectedGuarded):
    """A8P (ProjectedGuarded) with timers (perf_counter) around act, its parts and on_fast: split {key: seconds} over
    the run (SPLIT_KEYS) and split_slots, per slow slot [t, act, inner_act, lb, safe, test, projection] (test: T0g's
    begin and the slot's first evaluation; projection: the candidate lists and the later evaluations). The parts are
    timed by wrapping the bound methods of the objects reset() built (the inner policy, the OnlineLB, the safe expert,
    T0gBound) and by overriding act, candidates, _evaluate and on_fast, each returning its result unchanged; nothing
    the policy reads changes, so the run is A8P's (check E9v2-5)."""

    def reset(self, view, rng) -> None:
        super().reset(view, rng)
        self.split = {k: 0.0 for k in SPLIT_KEYS}
        self.split_n = {"slots": 0, "evaluations": 0, "projection_evaluations": 0, "fast_calls": 0}
        self.split_slots: list = []
        self._cur: Optional[dict] = None
        self._wrap(self.inner, "act", "inner_act")
        if getattr(self.inner, "wants_fast", False):
            self._wrap(self.inner, "on_fast", "inner_fast")
        if self.olb is not None:
            self._wrap(self.olb, "step", "lb")
        self._wrap(self.sx, "step", "safe")
        if self.t0g is not None:
            self._wrap(self.t0g, "begin", "test_begin")

    def _add(self, key: str, dt: float) -> None:
        self.split[key] += dt
        if self._cur is not None:
            self._cur[key] = self._cur.get(key, 0.0) + dt

    def _wrap(self, obj, name: str, key: str) -> None:
        f = getattr(obj, name)
        add = self._add

        def timed(*a, **kw):
            t0 = time.perf_counter()
            try:
                return f(*a, **kw)
            finally:
                add(key, time.perf_counter() - t0)
        setattr(obj, name, timed)

    def act(self, obs):
        self._cur = {"n_eval": 0}
        t0 = time.perf_counter()
        try:
            return super().act(obs)
        finally:
            dt = time.perf_counter() - t0
            c, self._cur = self._cur, None
            self.split["act"] += dt
            self.split_n["slots"] += 1
            g = c.get
            self.split_slots.append([int(obs.t), dt, g("inner_act", 0.0), g("lb", 0.0), g("safe", 0.0),
                                     g("test_begin", 0.0) + g("test_eval", 0.0),
                                     g("proj_candidates", 0.0) + g("proj_eval", 0.0)])

    def candidates(self, obs, acts):
        t0 = time.perf_counter()
        try:
            return super().candidates(obs, acts)
        finally:
            self._add("proj_candidates", time.perf_counter() - t0)

    def _evaluate(self, obs, lst, Q):
        first = self._cur is None or self._cur.get("n_eval", 0) == 0
        t0 = time.perf_counter()
        try:
            return super()._evaluate(obs, lst, Q)
        finally:
            self._add("test_eval" if first else "proj_eval", time.perf_counter() - t0)
            self.split_n["evaluations"] += 1
            self.split_n["projection_evaluations"] += 0 if first else 1
            if self._cur is not None:
                self._cur["n_eval"] = self._cur.get("n_eval", 0) + 1

    def on_fast(self, obs):
        t0 = time.perf_counter()
        try:
            return super().on_fast(obs)
        finally:
            self.split["fast"] += time.perf_counter() - t0
            self.split_n["fast_calls"] += 1


def timed(pol):
    """The A8P object built by make_policy, its class set to TimedProjectedGuarded (no constructor state added;
    fig1_illustrative.logged's rule)."""
    if type(pol) is not ProjectedGuarded:
        raise TypeError(f"expected A8P (ProjectedGuarded), got {type(pol).__name__}")
    pol.__class__ = TimedProjectedGuarded
    return pol


def split_record(pol, n_slow: int) -> dict:
    """The split of a timed run: the totals, per slow slot the means of act, the inner policy, the guard (act minus
    the inner's act) and its parts (lb, safe, test, projection, other), and the slots' P50, P99 and maxima."""
    s = dict(pol.split)
    arr = np.asarray(pol.split_slots, dtype=np.float64).reshape(-1, 7)
    n = max(1, int(n_slow))
    guard = arr[:, 1] - arr[:, 2]
    other = guard - arr[:, 3:7].sum(axis=1)
    per = {"act": arr[:, 1], "inner_act": arr[:, 2], "guard": guard, "lb": arr[:, 3], "safe": arr[:, 4],
           "test": arr[:, 5], "projection": arr[:, 6], "other": other}
    out = {"totals_s": s, "counts": dict(pol.split_n), "n_slow_steps": int(n_slow),
           "per_slot_mean_s": {k: float(v.sum()) / n for k, v in per.items()},
           "per_slot_p50_s": {k: float(np.percentile(v, 50)) if v.size else None for k, v in per.items()},
           "per_slot_p99_s": {k: float(np.percentile(v, 99)) if v.size else None for k, v in per.items()},
           "per_slot_max_s": {k: float(v.max()) if v.size else None for k, v in per.items()},
           "fast_per_slot_mean_s": s["fast"] / n,
           "parts": {"guard": "act - inner_act", "test": "T0gBound.begin + the slot's first _evaluate",
                     "projection": "candidates + the slot's later _evaluate calls", "lb": "OnlineLB.step",
                     "safe": "SafeExpert.step", "other": "guard - (lb + safe + test + projection)"}}
    return out


def digests(res) -> dict:
    """sha256 of the run's identity facts (E9v2-5): the per-slot cost series, the components, the policy report (JSON,
    sorted keys) and the schedule hash, with ALG."""
    from ..metrics import _jsonable
    ps = np.asarray(res.per_slot["total"], dtype=np.float64)
    comp = json.dumps({k: float(v) for k, v in sorted(res.components.items())}, sort_keys=True)
    rep = json.dumps(_jsonable(res.metrics.get("policy") or {}), sort_keys=True)
    return {"ALG": float(res.components["total"]), "per_slot_total_sha256": hashlib.sha256(ps.tobytes()).hexdigest(),
            "components_sha256": hashlib.sha256(comp.encode()).hexdigest(),
            "report_sha256": hashlib.sha256(rep.encode()).hexdigest(), "schedule_hash": mc.schedule_hash(res.schedule),
            "n_leases": len(res.leases)}


# ---------------------------------------------------------------- jobs
def run_point(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One run or split job alone on the host: the build, the driver inputs, the policy (timed with
    TimedProjectedGuarded in a split job) and engine.simulate, each timed; ms5b_common.week_entry's entry, E9's timing
    (e9.timing_fields, e9.step_check) with the act times per slow slot, the digests and, for a split, its record."""
    from ..algos import registry
    from ..drivers.run import driver_inputs, make_policy
    from ..engine import simulate
    from ..lender import resolve_params
    p = job.params
    point, t, c, hz, kind = p["point"], p["tag"], int(p["c"]), int(p["horizon_min"]), p["kind"]
    g = sv.gate(reduced())
    load, cg0 = e9._loadavg(), e9.cgroup_memory()
    t_job = time.perf_counter()
    inst, model, ecfg, build_s = e9.build_point(point, c, hz)
    if not ecfg.check_invariants:
        raise RuntimeError("E9 v2 runs need check_invariants=True")
    refs, ih = m4.references(inst), mc.instance_hash(inst)
    sizes = e9.instance_sizes(inst)
    pid, params = sv.tag_id(t), sv.tag_params(t, inst)
    spec = e9.point_spec(point, pid, params, c=c, horizon_min=hz, name=f"e9v2_{t}_{point}")
    t0 = time.perf_counter()
    inputs, imeta = driver_inputs(pid, params, inst)
    driver_inputs_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    pol = make_policy(spec, inst, inputs=inputs)
    if kind == "split":
        timed(pol)
    make_policy_s = time.perf_counter() - t0
    print(f"[e9v2] {job.id}: {inst.m} sites x {inst.J} LLMs, {sizes['n_units']} units, T_slow {inst.grid.T_slow}; "
          f"running {pid}{' (timed)' if kind == 'split' else ''}", flush=True)
    t0 = time.perf_counter()
    res = simulate(inst, pol, model, ecfg, lender_seed=c, policy_seed=POLICY_SEED)
    sim_s = time.perf_counter() - t0
    peak, cg1 = e9._rss_mb(), e9.cgroup_memory()
    hours = inst.grid.horizon_min / 60.0
    rt = dict(res.runtime)
    timing = e9.timing_fields(rt, hours, {"build_s": build_s, "driver_inputs_s": driver_inputs_s,
                                          "make_policy_s": make_policy_s})
    for k in ACT_KEYS:
        timing[k] = e9._num(rt.get(k))
    na = e9._num(rt.get("n_slow_steps"))
    timing["policy_act_s_sum"] = None if timing["policy_act_s_mean"] is None or na is None else \
        timing["policy_act_s_mean"] * na
    job_s = build_s + driver_inputs_s + make_policy_s + sim_s
    timing.update(simulate_s=sim_s, job_s=job_s, job_s_per_h=job_s / hours, hours=hours)
    steps = e9.step_check(rt, inst.grid.T_slow, inst.grid.T_fast)
    entry = m5.week_entry(res, inst, model, refs, refs.get("own_capacity_usd"), tag_name=t, spec=spec, pol=pol,
                          ps=POLICY_SEED, c=c, mode="L-tr", wall_s=driver_inputs_s + make_policy_s + sim_s,
                          imeta=imeta)
    entry["runtime"] = rt
    memory = {"peak_rss_mb": peak, "scope_start": cg0, "scope_after_run": cg1, "scope_capped": e9._capped(cg1),
              "cap_mb": e9.CAP_MB, "fits_cap": e9._fits_cap(peak, cg1)}
    put(memory, "scope_memory_peak_mb", cg1.get("memory_peak_mb") if e9._capped(cg1) else None, e9.SCOPE_NOTE)
    rec = {"meta": {"exp": EXP, "job": job.id, "spec": SPEC, "change": sv.CHANGE, "label": sv.LABEL,
                    "git_revision": mc.git_revision(), "versions": mc.versions(), "written": mc._now(),
                    "reduced": reduced(), "host": platform.node(),
                    "omp_num_threads": os.environ.get("OMP_NUM_THREADS"), "loadavg_start": load, "gate": g},
           "kind": kind, "point": point, "base": p["base"], "config": e9.BASES[p["base"]], "V": int(p["V"]),
           "llm_set": p["llm_set"], "tag": t, "policy_id": pid, "params": params, "c": c, "policy_seed": POLICY_SEED,
           "horizon_min": hz, "limit_s": p.get("limit_s"), "overrides": spec["overrides"], "instance_hash": ih,
           "instance": sizes, "references": refs, "lender_model": e9._lender_dict(inst, model),
           "lender_params_resolved": resolve_params(inst, model),
           "info_class": registry.info_class(pid, params, model.information), "timing": timing, "steps_check": steps,
           "memory": memory, "digests": digests(res), "job_wall_s": time.perf_counter() - t_job, "runs": [entry],
           "errors": []}
    if kind == "split":
        rec["split"] = split_record(pol, inst.grid.T_slow)
    outputs.dump(e7._jsonish(rec), run_path(out, job.id), compact=True)
    print(f"[e9v2] {job.id}: r0 {entry.get('r0')}; slow loop {timing['slow_loop_s_per_h']} s/h, act per slot "
          f"{timing['policy_act_s_mean']} s, job {job_s:.1f} s, ru_maxrss {peak:.0f} MB", flush=True)
    return {"runs": 1, "errors": [], "point": point, "tag": t, "c": c, "instance_hash": ih,
            "slow_loop_s_per_h": timing["slow_loop_s_per_h"], "policy_act_s_mean": timing["policy_act_s_mean"],
            "r0": entry.get("r0"), "steps_ok": steps["ok"]}


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    if job.params["kind"] in ("run", "split"):
        return run_point(job, outputs, out)
    raise ValueError(f"unknown E9 v2 job {job.id!r}")


def manifest_extra(out) -> dict:
    out = Path(out)
    hashes = {}
    for j in jobs():
        f = mc.read_json(run_path(out, j.id))
        if isinstance(f, dict):
            hashes[j.id] = f.get("instance_hash")
    files = [Path(__file__), Path(e9.__file__), Path(sv.__file__), sv.ANALYSIS_FILE, E9_SUMMARY]
    files += [paths.CONFIGS / f for f in e9.BASES.values()]
    return {"design": {k: (list(v) if isinstance(v, tuple) else v) for k, v in design().items()},
            "first_job": FIRST_JOB, "limits": [[a, b] for a, b in limits(out)],
            "instance_hashes_from_outputs": hashes, "gate_record": sv.registration_record(),
            "sources_sha256": {sv._rel_repo(f): (hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None)
                               for f in files}}


# ---------------------------------------------------------------- summary
def run_fields(f: Mapping) -> dict:
    """e9.run_fields of a run file plus the act times per slow slot and the guard facts of a Sublet run."""
    x = e9.run_fields(f)
    tm = f.get("timing") or {}
    for k in ACT_KEYS + ("policy_act_s_sum", "hours"):
        put(x, k, tm.get(k), f"no {k} in the run file")
    e = (f.get("runs") or [{}])[0]
    x["r0"] = e.get("r0")
    a8 = e.get("a8") or {}
    if a8:
        x.update(t_a=a8.get("t_a"), aborted=bool(a8.get("aborted")), certificate_case=a8.get("certificate_case"),
                 certificate_held=(a8.get("certificate") or {}).get("held"), projected_slots=a8.get("projected_slots"))
    return x


def policy_entry(files: list, t: str) -> dict:
    by = {num_key(int(f["c"])): run_fields(f) for f in sorted(files, key=lambda f: int(f["c"]))}
    e = {"n_runs": len(by), "alignments": sorted(int(c) for c in by), "by_alignment": by}
    if not by:
        e["note"] = "no run of this point and policy in the outputs"
    a = e9.agg_alignments(by, RUN_METRICS)
    e.update(median=a["median"], min=a["min"], max=a["max"])
    return e


def summary(out) -> dict:
    out = Path(out)
    d = design()
    js = jobs()
    data, recs, ignored, no_file = e9._outputs(out, js)
    runs = [f for f in data.values() if f.get("kind") == "run"]
    splits = [f for f in data.values() if f.get("kind") == "split"]
    e9s = mc.read_json(E9_SUMMARY)
    e9_src = {"file": E9_SUMMARY_REL, "exists": E9_SUMMARY.is_file(),
              "sha256": hashlib.sha256(E9_SUMMARY.read_bytes()).hexdigest() if E9_SUMMARY.is_file() else None,
              "git_revision": ((e9s or {}).get("meta") or {}).get("git_revision")}
    # E9's instances (and LPs) are this part's only at E9's horizon (a reduced run has none to compare)
    same_scale = ((e9s or {}).get("meta") or {}).get("horizon_min") == d["horizon_min"]
    e9p = ((e9s or {}).get("points") or {}) if same_scale else {}
    by_run = {(f["point"], f["tag"], int(f["c"])): f for f in runs}
    points, ident, inst_eq = {}, [], []
    for point in RUN_POINTS:
        fs = [f for f in runs if f["point"] == point]
        first = min(fs, key=lambda f: int(f["c"]), default=None)
        ins = (first or {}).get("instance") or {}
        e = {k: ins.get(k) for k in ("n_sites", "n_llms", "n_contracts", "sites_x_llms", "n_units")}
        e["policies"] = {t: policy_entry([f for f in fs if f["tag"] == t], t) for t in TAGS}
        sp = next((f for f in splits if f["point"] == point), None)
        if sp is not None:
            ref = by_run.get((point, "Sublet", int(sp["c"])))
            dg, dr = sp.get("digests") or {}, (ref or {}).get("digests")
            same = dr is not None and dg == dr
            ident.append({"point": point, "c": sp["c"], "equal": same if dr is not None else None,
                          "differs": None if dr is None else sorted(k for k in dg if dg.get(k) != dr.get(k))})
            e["split"] = {"c": sp["c"], "identical": same if dr is not None else None,
                          **({"split": sp.get("split")} if same else
                             {"split_not_used": "the split run does not equal the uninstrumented run" if dr is not None
                              else "no uninstrumented run of this point and alignment"})}
        for f in fs:
            ref_h = (((e9p.get(point) or {}).get("by_alignment") or {}).get(num_key(int(f["c"]))) or {}) \
                .get("instance_hash")
            inst_eq.append({"job": f["meta"]["job"], "instance_hash": f.get("instance_hash"), "e9": ref_h,
                            "equal": None if ref_h is None else ref_h == f.get("instance_hash")})
        points[point] = e
    gs = [{"job": f["meta"]["job"], "tag": f["tag"], "mode": "L-tr", "seed": POLICY_SEED,
           "guard": e7h.guard_brief((f.get("runs") or [{}])[0].get("a8"))} for f in runs + splits
          if f.get("tag") == "Sublet"]
    gs = [x for x in gs if x["guard"]]
    c1 = e9.check_e9_1(js, recs, data, no_file)
    c1["claim"] = CHECK_CLAIMS["E9v2-1"]
    c2 = e9.check_e9_2(runs + splits)
    c2["claim"] = CHECK_CLAIMS["E9v2-2"]
    miss = bool(c1.get("n_missing"))
    bad4 = [x for x in inst_eq if x["equal"] is False]
    unk4 = [x for x in inst_eq if x["equal"] is None]
    bad5 = [x for x in ident if x["equal"] is False]
    unk5 = [x for x in ident if x["equal"] is None]
    n_split_jobs = sum(1 for j in js if j.params["kind"] == "split")
    per = {p: {t: {k: e["policies"][t]["median"].get(k) for k in ("loops_s_per_h", "slow_loop_s_per_h",
                                                                   "policy_act_s_mean", "job_s_per_h", "peak_rss_mb")}
               for t in TAGS} for p, e in points.items()}
    checks = {"E9v2-1": c1, "E9v2-2": c2, "E9v2-3": {"claim": CHECK_CLAIMS["E9v2-3"], **sv.guard_check(gs, miss)},
              "E9v2-4": {"status": "fail" if bad4 else ("missing" if (unk4 or not inst_eq) else "pass"),
                         "claim": CHECK_CLAIMS["E9v2-4"], "n": len(inst_eq), "differ": bad4[:50],
                         "without_reference": unk4[:50], "same_scale": same_scale},
              "E9v2-5": {"status": "fail" if bad5 else
                         ("missing" if (unk5 or len(ident) < n_split_jobs) else "pass"),
                         "claim": CHECK_CLAIMS["E9v2-5"], "n": len(ident), "splits": ident},
              "E9v2-6": {"status": "informative", "claim": CHECK_CLAIMS["E9v2-6"], "per_point": per,
                         "real_time_s_per_h": e9.REAL_TIME_S_PER_H, "slow_slot_s": e9.SLOW_SLOT_S}}
    meta = sv.meta_common(EXP, None, SPEC, d["reduced"],
                          grid={"run_points": list(RUN_POINTS), "alignments": list(d["alignments"]),
                                "alignments_design": list(ALIGNMENTS), "policy_seed": POLICY_SEED,
                                "horizon_min": d["horizon_min"]}, tags=sv.tag_table(TAGS),
                          first_job=FIRST_JOB, limits={"first_s": FIRST_LIMIT_S, "floor_s": LIMIT_FLOOR_S,
                                                       "factor": LIMIT_FACTOR, "min_s": LIMIT_MIN_S},
                          sources={"e9": e9_src}, jobs=len(js), jobs_ok=len(data), ignored_outputs=ignored,
                          loadavg_start={jid: (f.get("meta") or {}).get("loadavg_start") for jid, f in data.items()})
    if d["reduced"]:
        meta["reduced_note"] = (f"reduced job list ({REDUCED_ENV}=1): alignment 1, a {sv.REDUCED_HORIZON_MIN}-min "
                                "horizon; not a result")
    s = {"meta": meta, "points": points, "lp": (e9s or {}).get("lp") if same_scale else None,
         "checks": {k: checks[k] for k in CHECK_IDS}}
    mc.dump_json(e7._jsonish(s), out / "summary.json")
    mc.write_text(tables(s), out / "tables.md")
    return s


def tables(s: dict) -> str:
    m = s["meta"]
    L = [f"# E9 v2 ({SPEC})", "", f"*{sv.LABEL}*", ""]
    if m.get("reduced"):
        L += [f"Reduced run: {m.get('reduced_note')}", ""]
    rows = []
    for p, e in s["points"].items():
        for t, pe in e["policies"].items():
            md = pe["median"]
            rows.append([p, t, e.get("sites_x_llms"), pe["n_runs"], md.get("slow_loop_s_per_h"),
                         md.get("fast_loop_s_per_h"), md.get("policy_act_s_mean"), md.get("peak_rss_mb")])
    L += ["## Runs (medians over the alignments)", "",
          mc.md_table(["point", "tag", "sites x LLMs", "runs", "slow loop s/h", "fast loop s/h", "act s/slot",
                       "peak MB"], rows), ""]
    rows = [[p, (e.get("split") or {}).get("identical"),
             ((e.get("split") or {}).get("split") or {}).get("per_slot_mean_s", {}).get("guard")]
            for p, e in s["points"].items()]
    L += ["## Split runs (guard s per slow slot, if identical)", "", mc.md_table(["point", "identical", "guard s"],
                                                                                 rows), ""]
    L += ["## Checks", "", mc.md_table(["check", "status"], [[k, v.get("status")] for k, v in s["checks"].items()]),
          ""]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check-start" in args:
        return sv.check_start(EXP, reduced())
    if "--limits" in args:
        ap = argparse.ArgumentParser(prog=f"python -m sublet.experiments.{EXP} --limits")
        ap.add_argument("--limits", action="store_true", required=True)
        ap.add_argument("--out", type=Path, default=None)
        a = ap.parse_args(args)
        out = mc.out_dir(EXP, a.out)
        sys.stdout.write("".join(f"{lim} {jid}\n" for lim, jid in limits(out)))
        return 0
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=args, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
