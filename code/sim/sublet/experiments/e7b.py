"""E7b: budget caps (design/ms8/plan.md D2, X6, D4; design/ms8/scout_x6_budget_cap.md §1-§3). The naive spend caps of
algos/budget_cap.py (registry id CAP; tags in e7b_tags.py) against Sublet, which is Algorithm 1 as the sound version of
a spend cap, on the confirmation's weeks and at five sensitivity points. Exploratory runs registered in
design/ms8/registration.md before they run; the MS5b confirmation, E7r and S1 v2 and their frozen analyses are
untouched (e7h.py, e7r.py, s1v2.py, ms5b_common, ms7_baselines and their analysis scripts are imported, never changed).

Parts (E7B_PART; one part per run of run_e7b.sh; ms3_common.COPY_PARTS['e7b']), outputs in <root>/out/e7b/<part>/
(jobs/, logs/, runs/ (not versioned), retry/, manifest.json, summary.json, tables.md, run_e7b.log):
  week  weeks 301-316 x the 13 lender modes of E7r's part eval (ms7_baselines.EVAL_MODES: the confirmation's seven and
        NEW_MODES), the seven cap tags (e7b_tags.CAP_TAGS), policy seed 0; one job runs one tag on one week under every
        mode in one process (the instance built once, L-pk on its own instance, as e7r.run_week; A9's contract table
        once per job). Plus Sublet and A9 under L-tr on the 16 weeks, which must reproduce the confirmation's part main
        bit for bit (the identity check of e7b_analysis.py: runs of two commits are combined only if the frozen
        behaviour is unchanged). The other modes of Sublet, A9, BL1 and BL1-GP are read from the frozen summaries
        (out/sublet_v2/main: the seven modes; out/e7r/eval: NEW_MODES). 112 + 32 = 144 jobs, 1,488 runs.
  sens  the S1 v2 points SENS_POINTS (fee4, fee8, fee16: rho = 4, 8, 16; slow1: a 1-minute slow slot;
        scen_cold_wan_1gbps: cold WAN loads at 1 Gb/s), each built exactly as S1 v2 builds it (s1v2._build_job,
        s1v2.point_spec): L-tr on weeks 301-304 and the five stress modes of W0 on weeks 301-302, policy seed 0; one job
        runs one tag at one point and week under that week's modes. Tags: the seven caps, and BL1 and BL1-GP (no run of
        either exists at these points, and the comparisons of the GR caps need them) at every cell; Sublet and A9 where
        S1 v2 has no run (slow1 under the stress modes on weeks 301-302) and, as an identity check against S1 v2's
        frozen runs and for Sublet's per-slot excess series, at fee16 under L-tr on week 301 and under L-eg on weeks
        301-302 (SENS_SUBLET_CELLS). The other runs of Sublet and A9 are read from out/s1v2/sweep and out/s1v2/w0.
        5 x 4 x 9 = 180 jobs of caps and references (630 runs) plus 2 x 2 x 2 = 8 jobs of Sublet and A9 (26 runs).
Every run entry is ms5b_common.week_entry's (e7h.one_run's steps) plus
  bound  the excess over Theorem 11's bound FB(t) + B(t), with FB(t) the all-fallback cost through slot t and B(t)
         Sublet's allowance min{W_k(t), LB'(t)} (online_lb.series on the run's public view and the instance's demand;
         policy-independent, the same series for every tag on the instance): ALG_T, FB_T (= BL0a: fb_equal_bl0a, the
         check |FB_T - BL0a| <= 1e-9 max(1, BL0a) against the cell's BL0a reference run), B_T, final excess
         ALG(T) - FB(T) - B(T) (USD and over FB(T)), whether the run lands above the bound (final excess > BOUND_TOL:
         GUARD_TOL max(1, |FB_T + B_T|) + CERT_TOL max(1, ALG_T), the guard's envelope tolerance), the run-time excess
         max_t ALG(t) - FB(t) - B(t) with its slot and the slots above the tolerance, and the per-slot series;
  cap    for a cap tag, its report (algos/budget_cap.py: bind slots, first bind, dropped Buys, latch slot, FB_T, X_T,
         B_T) and its excess over its own line FB(t) + X(t) (final and run-time), with the check that its FB(T) equals
         the bound's and, at X = 'lb', its X(T) equals B(T).

The gate (D4). A full run refuses to start unless design/ms8/registration.md exists at HEAD, the working tree is clean
(ms5b_common.dirty_paths: untracked outputs under code/sim/out/ do not count) and the sha256 of e7b_analysis.py, on disk
and at HEAD, equals the one its line 'e7b_analysis_sha256: <64 hex>' records. Every run file and summary records the
gate (kind 'ms8_registration'), never the confirmation's. Reduced runs (MS8_E7B_REDUCED=1, run_e7b.sh --reduced) record
it without enforcing it and use the development cell bench_e7f 101 with a 2-hour horizon only (part sens: the same
week at each point, with L-tr and the five stress modes), never a confirmation week; their summaries carry meta.reduced,
never a result.

Command line (ms3_common.main), run from code/sim:
  python -m sublet.experiments.e7b --list | --job ID | --summary | --estimate | --manifest  [--out DIR]
  python -m sublet.experiments.e7b --check-start          the gate of the part(s) of E7B_PART; exit 1 if refused
  python -m sublet.experiments.e7b --retry-list --out DIR  the missing-run rule's rerun (as e7h's)
Without --out the part's folder is the default (one part in E7B_PART).

Status: the caps are labeled baselines (no ratio claimed); Sublet's guarantee is Theorem W(a)(b) for A8P through
Remark R (PROVEN, audited), with Theorem 11's bound ALG(T) <= FB(T) + B(T) when the safe expert follows all-fallback.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import hashlib
import re
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

from .. import paths
from . import e7
from . import e7b_tags as bt
from . import e7h
from . import ms3_common as mc
from . import ms4_common as m4
from . import ms5b_common as m5
from . import ms7_baselines as m7
from . import s1v2
from .ms3_common import Job, job_id, num_key

EXP = "e7b"
SPEC = "design/ms8/plan.md D2 (X6); design/ms8/scout_x6_budget_cap.md"
LABEL = "exploratory: post-freeze runs registered in design/ms8/registration.md (D4), not a confirmation result"
PARTS = ("week", "sens")
REDUCED_ENV = "MS8_E7B_REDUCED"
REDUCED_HORIZON_MIN = 120
REDUCED_WEEK = 101
WEEKS = m5.CONF_WEEKS                                          # 301-316
WEEK_MODES = m7.EVAL_MODES                                     # the 13 modes of E7r's part eval
IDENTITY_MODES = (m5.TRACE_MODE,)
SENS_POINTS = ("fee4", "fee8", "fee16", "slow1", "scen_cold_wan_1gbps")
SENS_WEEKS = (301, 302, 303, 304)
SENS_STRESS_WEEKS = (301, 302)
SENS_REF_TAGS = ("BL1", "BL1-GP")
STRESS = m5.stress_modes()
# Sublet and A9 in part sens: {point: {week: modes}} (module docstring)
SENS_SUBLET_CELLS = {"slow1": {301: STRESS, 302: STRESS},
                     "fee16": {301: (m5.TRACE_MODE, "L-eg"), 302: ("L-eg",)}}
SENS_SUBLET_TAGS = bt.IDENTITY_TAGS
POLICY_SEEDS = (0,)
# the registration (D4): design/ms8/registration.md records the analysis script's sha256 on this line
REGISTRATION = "design/ms8/registration.md"
ANALYSIS = Path(__file__).resolve().parent / "e7b_analysis.py"
ANALYSIS_REL = "code/sim/sublet/experiments/e7b_analysis.py"
REG_KEY = "e7b_analysis_sha256"
REG_SHA_RE = re.compile(r"^e7b_analysis_sha256:\s*([0-9a-f]{64})\s*$", re.MULTILINE)
GATE_KIND = "ms8_registration"
SOURCES = ("sublet/experiments/e7b.py", "sublet/experiments/e7b_tags.py", "sublet/experiments/e7b_analysis.py",
           "sublet/experiments/e7h.py", "sublet/experiments/e7r.py", "sublet/experiments/s1v2.py",
           "sublet/experiments/s1.py", "sublet/experiments/ms5b_common.py", "sublet/experiments/ms7_baselines.py",
           "sublet/algos/budget_cap.py", "sublet/algos/registry.py", "sublet/algos/a9.py", "sublet/algos/guard.py",
           "sublet/algos/online_lb.py", "sublet/baselines/greedy.py", "sublet/baselines/common.py", "sublet/lender.py",
           "sublet/engine.py", "sublet/drivers/run.py", "sublet/experiments/ms3_common.py",
           "sublet/experiments/q44_study.py")
# estimates (seconds per full-week run): A9 and BL1 from the confirmation's job medians (ms7_baselines.EST_RUN_S), the
# caps from the prototype (4-49 s per run, design/ms8/scout_x6_budget_cap.md §2); part sens scales S1 v2's
# Sublet time at the point (s1v2.est_run_s) by the tag's ratio
EST_RUN_S = {"CAP-A9": 32.0, "CAP-BL1": 35.0, "A8P": 222.0, "A9": 28.0, "BL1": 33.0}
EST_SENS_RATIO = {"CAP-A9": 0.15, "CAP-BL1": 0.10, "A8P": 1.10, "A9": 0.30, "BL1": 0.12}
EST_TABLE_S = 44.0                                             # A9's contract table, once per job of the A9 family
EST_JOB_S = 10.0
EST_BUILD_S = 30.0                                             # a sens job builds the week's default and the point


# ---------------------------------------------------------------- settings, parts, folders
def reduced() -> bool:
    return os.environ.get(REDUCED_ENV, "0") == "1"


def design() -> dict:
    red = reduced()
    return {"reduced": red, "horizon_min": REDUCED_HORIZON_MIN if red else m5.WEEK_MIN,
            "weeks": [REDUCED_WEEK] if red else list(WEEKS), "week_modes": list(WEEK_MODES),
            "sens_points": list(SENS_POINTS), "sens_weeks": [REDUCED_WEEK] if red else list(SENS_WEEKS),
            "sens_stress_weeks": [REDUCED_WEEK] if red else list(SENS_STRESS_WEEKS), "policy_seeds": list(POLICY_SEEDS)}


def parts() -> list:
    v = os.environ.get("E7B_PART", "")
    ps = [p for p in v.replace(",", " ").split() if p]
    bad = [p for p in ps if p not in PARTS]
    if bad:
        raise ValueError(f"E7B_PART must name parts of {list(PARTS)}, got {v!r}")
    return ps or list(PARTS)


def part_dir(part: str, root=None) -> Path:
    """<root>/out/e7b/<part> (root as ms3_common.ms3_root)."""
    return mc.ms3_root(root) / "out" / EXP / part


def run_path(out, jid: str) -> Path:
    return Path(out) / "runs" / mc.job_file_name(jid)


def sens_modes(c: int) -> list:
    """The modes of a part-sens cell at week c: L-tr, and the five stress modes on weeks 301-302 (every reduced cell)."""
    if reduced() or int(c) in SENS_STRESS_WEEKS:
        return [m5.TRACE_MODE] + list(STRESS)
    return [m5.TRACE_MODE]


def sens_sublet_modes(point: str, c: int) -> list:
    """The modes of Sublet's and A9's part-sens runs at a point and week (SENS_SUBLET_CELLS; in a reduced run the union
    of the point's full cells at the development week)."""
    cells = SENS_SUBLET_CELLS.get(point) or {}
    if reduced():
        ms = {m for v in cells.values() for m in v}
        return [m for m in [m5.TRACE_MODE] + list(STRESS) if m in ms]
    return list(cells.get(int(c), ()))


# ---------------------------------------------------------------- job lists
def _est_key(name: str) -> str:
    t = bt.tag(name)
    if t.id == "CAP":
        return "CAP-" + t.params["inner"]
    return t.id


def _est_week(name: str, n_runs: int, hz: int) -> float:
    return EST_JOB_S + (EST_TABLE_S if bt.tag(name).a9_family else 0.0) + \
        n_runs * EST_RUN_S.get(_est_key(name), 30.0) * hz / m5.WEEK_MIN


def _est_sens(point: str, name: str, n_runs: int, hz: int) -> float:
    base = s1v2.est_run_s(point, "Sublet") / s1v2.EST_RATIO["Sublet"]
    return EST_JOB_S + EST_BUILD_S + (EST_TABLE_S if bt.tag(name).a9_family else 0.0) + \
        n_runs * base * EST_SENS_RATIO.get(_est_key(name), 0.3) * hz / m5.WEEK_MIN


def week_id(name: str, c: int) -> str:
    return job_id(EXP, "week", k="week", tag=name, c=int(c))


def sens_id(point: str, name: str, c: int) -> str:
    return job_id(EXP, "sens", k="sens", pt=point, tag=name, c=int(c))


def jobs(ps=None) -> list:
    """The jobs of the parts `ps` (default: E7B_PART) in run order (module docstring); per part the longest first."""
    ps = parts() if ps is None else list(ps)
    d = design()
    hz = d["horizon_min"]
    out: list = []
    for part in ps:
        js = []
        if part == "week":
            for c in d["weeks"]:
                for name in bt.CAP_TAGS + bt.IDENTITY_TAGS:
                    modes = list(WEEK_MODES) if bt.is_cap(name) else list(IDENTITY_MODES)
                    js.append(Job(week_id(name, c), "pool",
                                  {"part": part, "kind": "week", "tag": name, "policy_id": bt.tag(name).id,
                                   "c": int(c), "modes": modes, "policy_seeds": list(POLICY_SEEDS), "horizon_min": hz},
                                  _est_week(name, len(modes), hz)))
        elif part == "sens":
            for point in SENS_POINTS:
                for c in d["sens_weeks"]:
                    for name in bt.CAP_TAGS + SENS_REF_TAGS + SENS_SUBLET_TAGS:
                        modes = sens_sublet_modes(point, c) if name in SENS_SUBLET_TAGS else sens_modes(c)
                        if not modes:
                            continue
                        js.append(Job(sens_id(point, name, c), "pool",
                                      {"part": part, "kind": "sens", "point": point, "tag": name,
                                       "policy_id": bt.tag(name).id, "c": int(c), "modes": modes,
                                       "policy_seeds": list(POLICY_SEEDS), "horizon_min": hz},
                                      _est_sens(point, name, len(modes), hz)))
        else:
            raise ValueError(f"unknown E7b part {part!r}")
        out += [j for _i, j in sorted(enumerate(js), key=lambda x: (-(x[1].est_s or 0.0), x[0]))]
    return out


def jobs_all() -> list:
    return jobs(list(PARTS))


# ---------------------------------------------------------------- the gate (D4)
_GATE: dict = {}


def analysis_sha256() -> Optional[str]:
    return m5._sha(ANALYSIS.read_bytes()) if ANALYSIS.is_file() else None


def registered_sha256(text: Optional[str]) -> Optional[str]:
    """The analysis script's sha256 that the registration records (its line 'e7b_analysis_sha256: <64 hex>')."""
    if not text:
        return None
    m = REG_SHA_RE.search(text)
    return m.group(1) if m else None


def registration_record() -> dict:
    """The gate's facts: HEAD, whether design/ms8/registration.md exists at HEAD and the analysis sha256 it records,
    the sha256 of e7b_analysis.py at HEAD and on disk, and the dirty paths (ms5b_common's read-only git helpers)."""
    reg = m5.file_at("HEAD", REGISTRATION)
    return {"head": m5.head_commit(), "registration": REGISTRATION, "registration_at_head": reg is not None,
            "registration_sha256": m5._sha(reg), "analysis": ANALYSIS_REL,
            "analysis_sha256_registered": registered_sha256(None if reg is None else reg.decode("utf-8", "replace")),
            "analysis_sha256_head": m5._sha(m5.file_at("HEAD", ANALYSIS_REL)),
            "analysis_sha256_disk": analysis_sha256(), "dirty_paths": m5.dirty_paths()}


def check_registration(rec: Optional[dict] = None) -> tuple[bool, str, dict]:
    """(ok, reason, record): an E7b part runs only if design/ms8/registration.md exists at HEAD, the working tree is
    clean and the sha256 of e7b_analysis.py (on disk and at HEAD) equals the registered one (D4)."""
    rec = dict(rec if rec is not None else registration_record())
    why = []
    if not rec.get("registration_at_head"):
        why.append(f"{REGISTRATION} does not exist at HEAD")
    if rec.get("dirty_paths") is None:
        why.append("git cannot tell whether the working tree is clean")
    elif rec["dirty_paths"]:
        why.append(f"the working tree is dirty ({len(rec['dirty_paths'])} paths, e.g. {rec['dirty_paths'][:3]})")
    want = rec.get("analysis_sha256_registered")
    if rec.get("registration_at_head") and want is None:
        why.append(f"{REGISTRATION} records no line '{REG_KEY}: <64 hex>'")
    for k in ("analysis_sha256_disk", "analysis_sha256_head"):
        if want is not None and rec.get(k) != want:
            why.append(f"{k} {str(rec.get(k))[:12]} differs from the registration's {want[:12]}")
    if why:
        return False, "E7b does not start (design/ms8/plan.md D4): " + "; ".join(why), rec
    return True, "registration at HEAD, clean tree, analysis sha256 as registered", rec


def gate_state() -> dict:
    """The gate's record, taken once per process: {kind, ok, reason, enforced (full runs), registration}; never
    raises (summaries and manifests record it)."""
    if "g" not in _GATE:
        red = reduced()
        ok, why, rec = check_registration()
        g = {"kind": GATE_KIND, "ok": ok, "reason": why, "enforced": not red, "registration": rec}
        if red:
            g["note"] = "reduced run on a development cell: the gate is recorded, not enforced"
        _GATE["g"] = g
    return _GATE["g"]


def gate() -> dict:
    """The gate of a job: enforced in full runs (RuntimeError when refused), recorded in reduced runs."""
    g = gate_state()
    if g["enforced"] and not g["ok"]:
        raise RuntimeError(g["reason"])
    return g


def _meta_run(job: Job) -> dict:
    return {"exp": EXP, "job": job.id, "part": job.params["part"], "spec": SPEC, "label": LABEL,
            "git_revision": mc.git_revision(), "versions": mc.versions(), "written": mc._now(), "reduced": reduced(),
            "gate": gate()}


# ---------------------------------------------------------------- the bound and the cap's fields
BOUND_NOTE = ("excess over Theorem 11's bound FB(t) + B(t): FB the all-fallback cost through slot t, B(t) = min{W_k(t), "
              "LB'(t)} (online_lb.series on the run's public view); ALG(t) the ledger's cumulative cost")


def bound_series(inst, information: str = "I1") -> dict:
    """{'FB', 'B', 'Q'}: (T_slow,) float arrays of the policy-independent bound of an instance: Q(t) the slot's
    all-fallback cost (guard.fallback_by_client on the instance's demand, summed over the clients), FB(t) their running
    sum in slot order (the cap's own accumulation), B(t) online_lb.series' B on public_view(inst, information)."""
    from ..algos.guard import fallback_by_client
    from ..algos.online_lb import series
    from ..instance import public_view
    view = public_view(inst, information)
    d = np.asarray(inst.clients.demand, dtype=np.float64)
    phi, T = int(inst.grid.phi), int(inst.grid.T_slow)
    Q = np.array([float(fallback_by_client(view, d[:, t * phi:(t + 1) * phi]).sum()) for t in range(T)])
    fb, acc = np.empty(T), 0.0
    for t in range(T):
        acc += float(Q[t])
        fb[t] = acc
    return {"FB": fb, "B": np.asarray(series(view, d)["B"], dtype=np.float64), "Q": Q}


def bound_tol(fb_T: float, b_T: float, alg_T: float) -> float:
    """BOUND_TOL of a run (module docstring): the guard's envelope tolerance at the final slot."""
    from ..algos.guard import GUARD_TOL
    from .q44_study import CERT_TOL
    return GUARD_TOL * max(1.0, abs(fb_T + b_T)) + CERT_TOL * max(1.0, abs(alg_T))


def bound_fields(res, ser: dict) -> dict:
    """The entry's 'bound' block (module docstring) from the run's per-slot costs and the instance's bound series."""
    from ..algos.guard import GUARD_TOL
    from .q44_study import CERT_TOL
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=np.float64))
    fb, B = ser["FB"], ser["B"]
    if len(alg) != len(fb):
        raise ValueError(f"bound_fields: {len(alg)} slots of costs, {len(fb)} of the bound")
    ex = alg - fb - B
    alg_T = float(res.components["total"])
    fb_T, b_T = float(fb[-1]), float(B[-1])
    fin = alg_T - fb_T - b_T
    tol = bound_tol(fb_T, b_T, alg_T)
    tol_t = GUARD_TOL * np.maximum(1.0, np.abs(fb + B)) + CERT_TOL * np.maximum(1.0, np.abs(alg))
    i = int(np.argmax(ex))
    return {"note": BOUND_NOTE, "ALG_T": alg_T, "FB_T": fb_T, "B_T": b_T, "final_excess_usd": fin,
            "final_excess_rel": fin / fb_T if fb_T > 0 else None, "tol_usd": tol, "above": bool(fin > tol),
            "runtime_max_excess_usd": float(ex[i]), "runtime_max_slot": i,
            "runtime_max_excess_rel": float(ex[i]) / fb_T if fb_T > 0 else None,
            "n_slots_above": int(np.sum(ex > tol_t)), "n_slots": int(len(ex)), "series": [float(x) for x in ex]}


def cap_fields(res, bound: dict) -> Optional[dict]:
    """The entry's 'cap' block of a CAP run: its report without the series, its excess over its own line FB(t) + X(t)
    (final and run-time) and the checks FB_T = the bound's FB_T (relative 1e-12) and, at X = 'lb', X_T = B_T."""
    rep = (res.metrics.get("policy") or {}).get("cap")
    if not isinstance(rep, dict):
        return None
    out = {k: v for k, v in rep.items() if not k.endswith("_series")}
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=np.float64))
    fb = np.asarray(rep["FB_series"], dtype=np.float64)
    X = np.asarray(rep["X_series"], dtype=np.float64)
    own = alg - fb - X
    alg_T = float(res.components["total"])
    out["final_excess_over_X_usd"] = alg_T - float(fb[-1]) - float(X[-1])
    i = int(np.argmax(own))
    out["runtime_max_excess_over_X_usd"], out["runtime_max_over_X_slot"] = float(own[i]), i
    out["fb_equal_bound"] = abs(float(fb[-1]) - bound["FB_T"]) <= 1e-12 * max(1.0, abs(bound["FB_T"]))
    if rep.get("X") == "lb":
        out["X_equal_B"] = float(X[-1]) == float(bound["B_T"])
    out["B_series_equal_bound"] = None
    return out


# ---------------------------------------------------------------- one run
def one_run(spec: dict, name: str, inst, model, ecfg, refs: dict, own, c: int, ps: int, mode: str,
            ser: dict) -> dict:
    """One run of tag `name` on `inst` under `model`: e7h.one_run's steps (ms5b_common.week_entry), plus the bound and,
    for a cap, the cap's fields (module docstring)."""
    from ..drivers.run import driver_inputs, make_policy
    from ..engine import simulate
    pid, params = spec["policy"]["id"], dict(spec["policy"]["params"] or {})
    t0 = time.perf_counter()
    _, imeta = driver_inputs(pid, params, inst)
    pol = make_policy(spec, inst)
    res = simulate(inst, pol, model, ecfg, lender_seed=int(c), policy_seed=int(ps))
    e = m5.week_entry(res, inst, model, refs, own, tag_name=name, spec=spec, pol=pol, ps=ps, c=c, mode=mode,
                      wall_s=time.perf_counter() - t0, imeta=imeta)
    e["bound"] = bound_fields(res, ser)
    bl0a = float(refs["bl0a_usd"])
    e["bound"]["fb_equal_bl0a"] = bool(abs(e["bound"]["FB_T"] - bl0a) <= 1e-9 * max(1.0, abs(bl0a)))
    cap = cap_fields(res, e["bound"])
    if cap is not None:
        rep = res.metrics["policy"]["cap"]
        cap["B_series_equal_bound"] = bool(np.array_equal(np.asarray(rep["B_series"], dtype=np.float64), ser["B"]))
        e["cap"] = cap
    return e


def _print(e: dict, where: str) -> None:
    b, cp, a8 = e.get("bound") or {}, e.get("cap") or {}, e.get("a8") or {}
    print(f"[e7b] {where} {e['tag']} {e['mode']} p{e['policy_seed']}: r0 {e.get('r0')}, status {e.get('status')}, "
          f"excess final {b.get('final_excess_usd', float('nan')):.3f} run-time "
          f"{b.get('runtime_max_excess_usd', float('nan')):.3f} USD, binds {cp.get('bind_slots')}, latch "
          f"{cp.get('latch_t')}, projected {a8.get('projected_slots')}, {e.get('wall_s', 0.0):.1f} s", flush=True)


# ---------------------------------------------------------------- jobs: week and sens
def _tag_record(name: str) -> dict:
    return bt.tag_table([name])


def run_week(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One week job: tag p['tag'] on week c under each mode of p['modes'], the instance built once per instance key
    (L-pk: ms7_baselines.peak_aligned_instance of the base instance), as e7r.run_week."""
    from ..drivers import run as drun
    from ..lender import resolve_params
    p = job.params
    name, c, hz, seeds = p["tag"], int(p["c"]), int(p["horizon_min"]), [int(s) for s in p["policy_seeds"]]
    meta = _meta_run(job)
    t0 = time.perf_counter()
    insts: dict = {}

    def build(key):
        if key in insts:
            return insts[key]
        if key == "pk":
            base = build("base")
            inst, pk = m7.peak_aligned_instance(base["inst"])
            ecfg = base["ecfg"]
        else:
            spec0 = m7.week_spec("BL0a", {}, mode=m5.B999_MODE if key == "b999" else "L-tr", c=c, horizon_min=hz,
                                 seeds=seeds, name="e7b_build")
            inst, _, ecfg = drun.build(spec0, c)
            pk = None
        if not ecfg.check_invariants:
            raise RuntimeError("E7b runs need check_invariants=True")
        insts[key] = {"inst": inst, "ecfg": ecfg, "refs": m4.references(inst), "own": e7._own(inst),
                      "hash": mc.instance_hash(inst), "sizes": e7.instance_sizes(inst), "peak_aligned": pk, "ser": {}}
        return insts[key]
    errors, rows, models, params_rec = [], [], {}, {}
    for mode in p["modes"]:
        key = m7.instance_key(mode)
        b = build(key)
        inst, ecfg, refs, own = b["inst"], b["ecfg"], b["refs"], b["own"]
        params = bt.tag_params(name, inst)
        params_rec[key] = params
        spec = m7.week_spec(bt.tag(name).id, params, mode=mode, c=c, horizon_min=hz, seeds=seeds,
                            name=f"e7b_week_{name}")
        model = drun._lender_model(spec, inst)
        models[mode] = {**e7._lender_dict(model), "resolved": resolve_params(inst, model)}
        if model.information not in b["ser"]:
            b["ser"][model.information] = bound_series(inst, model.information)
        for ps in seeds:
            e = mc.try_run(errors, f"{name} {mode} p{ps}", one_run, spec, name, inst, model, ecfg, refs, own, c, ps,
                           mode, b["ser"][model.information])
            if e is not None:
                rows.append(e)
                _print(e, f"week c{c}")
    rec = {"meta": meta, "part": p["part"], "kind": "week", "tag": name, "tags": _tag_record(name),
           "params": params_rec, "c": c, "modes": list(p["modes"]), "policy_seeds": seeds, "horizon_min": hz,
           "instances": {k: {"instance_hash": v["hash"], "sizes": v["sizes"], "references": v["refs"],
                             "own_capacity_usd": v["own"], "peak_aligned": v["peak_aligned"]}
                         for k, v in insts.items()},
           "lender_models": models, "wall_s": time.perf_counter() - t0, "runs": rows, "errors": e7h._errs(errors)}
    outputs.dump(e7._jsonish(rec), run_path(out, job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": (insts.get("base") or {}).get("hash"),
            "r0": [[r["mode"], r["policy_seed"], r.get("r0")] for r in rows]}


def run_sens(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One sens job: tag p['tag'] at point p['point'] and week c under each mode of p['modes'], the point built as S1
    v2 builds it (s1v2._build_job, s1v2.point_spec)."""
    from ..drivers import run as drun
    from ..lender import resolve_params
    from . import s1
    p = job.params
    name, point, c, hz = p["tag"], p["point"], int(p["c"]), int(p["horizon_min"])
    seeds = [int(s) for s in p["policy_seeds"]]
    meta = _meta_run(job)
    t0 = time.perf_counter()
    b = s1v2._build_job({"point": point, "c": c, "horizon_min": hz})
    inst, ecfg, refs, own = b["inst"], b["ecfg"], b["refs"], b["own"]
    pt = s1v2.POINTS[point]
    params = bt.tag_params(name, inst)
    errors, rows, models, sers = [], [], {}, {}
    for mode in p["modes"]:
        spec = s1v2.point_spec(bt.tag(name).id, params, b["overrides"], mu=pt.mu, mode=mode, horizon_min=hz, c=c,
                               seeds=seeds, name=f"e7b_sens_{point}_{name}")
        model = drun._lender_model(spec, inst)
        models[mode] = {**e7._lender_dict(model), "resolved": resolve_params(inst, model)}
        if model.information not in sers:
            sers[model.information] = bound_series(inst, model.information)
        for ps in seeds:
            e = mc.try_run(errors, f"{name} {mode} p{ps}", one_run, spec, name, inst, model, ecfg, refs, own, c, ps,
                           mode, sers[model.information])
            if e is not None:
                e["point"] = point
                rows.append(e)
                _print(e, f"sens {point} c{c}")
    rec = {"meta": meta, "part": p["part"], "kind": "sens", "point": point, "row": pt.row or None, "value": pt.value,
           "label": pt.label, "mu": pt.mu, "tag": name, "tags": _tag_record(name), "params": params, "c": c,
           "modes": list(p["modes"]), "policy_seeds": seeds, "horizon_min": hz, "overrides": b["overrides"],
           "instance_hash": b["instance_hash"], "instance": s1.instance_record(inst), "references": refs,
           "own_capacity_usd": own, "vs_default": b["facts"], "lender_models": models, "build_s": b["build_s"],
           "wall_s": time.perf_counter() - t0, "runs": rows, "errors": e7h._errs(errors)}
    outputs.dump(e7._jsonish(rec), run_path(out, job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": b["instance_hash"], "bl0a_usd": refs["bl0a_usd"],
            "r0": [[r["mode"], r["policy_seed"], r.get("r0")] for r in rows]}


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    gate()
    k = job.params["kind"]
    if k == "week":
        return run_week(job, outputs, out)
    if k == "sens":
        return run_sens(job, outputs, out)
    raise ValueError(f"e7b: unknown job kind {k!r}")


# ---------------------------------------------------------------- summaries
def cell_key(job: Job) -> str:
    """The cell of a job's runs in a summary's tables: the week ('301'), or '<point>:<week>' in part sens."""
    p = job.params
    return num_key(p["c"]) if p["kind"] == "week" else f"{p['point']}:{num_key(p['c'])}"


def expected_runs(job: Job) -> list:
    """(tag, mode, cell, seed) of every run a job owes."""
    p = job.params
    return [(p["tag"], m, cell_key(job), int(s)) for m in p["modes"] for s in p["policy_seeds"]]


def brief(e: dict, job: Job) -> dict:
    """One run's summary row: the cell, tag, mode and seed, the missing-run rule's status, r0, ALG, BL0a, the fallback
    and stranding totals, the leases, the guard facts (e7h.guard_brief), A9's counts, the bound without its series and
    the cap's fields."""
    p = job.params
    row = {"job": job.id, "kind": p["kind"], "cell": cell_key(job), "c": int(p["c"]), "point": p.get("point"),
           "tag": e["tag"], "mode": e.get("mode"), "seed": int(e.get("policy_seed", 0)),
           "status": e.get("status") or m5.run_status(e), "r0": e.get("r0"), "ALG": e.get("ALG"),
           "bl0a_usd": e.get("bl0a_usd"), "fallback_usd": e.get("fallback_usd"), "stranding_usd": e.get("stranding_usd"),
           "fallback_share": e.get("fallback_share"), "n_leases": e.get("n_leases"),
           "n_invariant_failures": e.get("n_invariant_failures"), "wall_s": e.get("wall_s")}
    g = e7h.guard_brief(e.get("a8"))
    if g is not None:
        row["guard"] = g
    a9 = e7h._a9_brief(e.get("a9"))
    if a9 is not None:
        row["a9"] = a9
    if e.get("bound"):
        row["bound"] = {k: v for k, v in e["bound"].items() if k not in ("series", "note")}
    if e.get("cap"):
        row["cap"] = dict(e["cap"])
    return row


def collect(out_p: Path, js: list) -> dict:
    """The rows of a part (e7h.collect's rule with this driver's rows): every run of the 'ok' jobs, the missing runs
    of the expected grid with their reason, the table {tag: {mode: {cell: {seed: r0}}}} (null for a run missing or
    not ok) and the guarded runs."""
    files, not_ok, ignored = e7h.part_outputs(out_p, js)
    by_id = {j.id: j for j in js}
    rows, guarded, have = [], [], {}
    for jid, f in files.items():
        j = by_id[jid]
        for e in f.get("runs") or []:
            r = brief(e, j)
            rows.append(r)
            have[(r["tag"], r["mode"], r["cell"], r["seed"])] = r
            if r.get("guard"):
                guarded.append({k: r[k] for k in ("job", "cell", "tag", "mode", "seed")} | r["guard"])
    missing, table = [], {}
    for j in js:
        errs = {e.get("tag"): e.get("error") for e in (files.get(j.id) or {}).get("errors") or []}
        for key in expected_runs(j):
            t, m, cell, s = key
            r = have.get(key)
            ok = r is not None and r["status"] == "ok"
            table.setdefault(t, {}).setdefault(m, {}).setdefault(cell, {})[num_key(s)] = r["r0"] if ok else None
            if not ok:
                why = r["status"] if r is not None else (not_ok.get(j.id) or next(iter(errs.values()), None)
                                                         or "run missing")
                missing.append({"job": j.id, "tag": t, "mode": m, "cell": cell, "seed": s, "why": why})
    return {"files": files, "not_ok": not_ok, "ignored": ignored, "rows": rows, "table": table, "missing": missing,
            "guarded": guarded}


def _meta(part: str, js: list, col: dict) -> dict:
    d = design()
    tags = sorted({j.params["tag"] for j in js})
    ok, why, rec = check_registration()
    m = {"exp": EXP, "part": part, "spec": SPEC, "label": LABEL, "git_revision": mc.git_revision(),
         "versions": mc.versions(), "written": mc._now(), "reduced": d["reduced"], "design": d,
         "tags": bt.tag_table(tags), "cells": sorted({cell_key(j) for j in js}),
         "modes": sorted({m for j in js for m in j.params["modes"]}), "w0_modes": list(m7.W0_MODES),
         "w0plus_modes": list(m7.W0PLUS_MODES), "bound_note": BOUND_NOTE, "jobs": len(js),
         "jobs_ok": len(col["files"]), "jobs_not_ok": col["not_ok"], "ignored_outputs": col["ignored"],
         "n_runs": len(col["rows"]), "n_missing": len(col["missing"]),
         "gate": {"kind": GATE_KIND, "ok": ok, "reason": why, "record": rec}}
    if part == "sens":
        m["points"] = {pt: {"row": s1v2.POINTS[pt].row, "value": s1v2.POINTS[pt].value,
                            "label": s1v2.POINTS[pt].label, "mu": s1v2.POINTS[pt].mu} for pt in SENS_POINTS}
        m["sublet_cells"] = {pt: {num_key(c): list(v) for c, v in cells.items()}
                             for pt, cells in SENS_SUBLET_CELLS.items()}
    if d["reduced"]:
        m["reduced_note"] = f"reduced job list ({REDUCED_ENV}=1): development cell {REDUCED_WEEK} only; not a result"
    return m


def w0_tables(table: dict, cells, tags) -> dict:
    """{'W0': {tag: {cell: W0}}, 'W0plus': {tag: {cell: W0+}}} over the tags with a run of every mode of the metric."""
    out = {"W0": {}, "W0plus": {}}
    for t in tags:
        by_m = table.get(t) or {}
        for key, modes, fn in (("W0", m7.W0_MODES, m5.w0_of), ("W0plus", m7.W0PLUS_MODES, m7.w0plus_of)):
            if not all(md in by_m for md in modes):
                continue
            for cell in cells:
                if not all(cell in (by_m.get(md) or {}) for md in modes):
                    continue
                w, _m, _miss = fn({md: e7h._val(table, t, md, cell, 0) for md in modes})
                out[key].setdefault(t, {})[cell] = w
    return out


def summary_part(part: str, out_p: Path) -> dict:
    out_p = Path(out_p)
    js = [j for j in jobs_all() if j.params["part"] == part]
    col = collect(out_p, js)
    cells = sorted({cell_key(j) for j in js})
    s = {"meta": _meta(part, js, col), "runs": col["rows"], "table": col["table"], "missing": col["missing"],
         "guarded": col["guarded"], "guard_summary": e7h.guard_summary(col["guarded"]),
         **w0_tables(col["table"], cells, sorted(col["table"]))}
    mc.dump_json(e7._jsonish(s), out_p / "summary.json")
    mc.write_text(tables(s), out_p / "tables.md")
    return s


def tables(s: dict) -> str:
    """tables.md: per tag and mode the median r0 over the part's cells, the runs above the bound, the largest final
    and run-time excess, and the missing runs."""
    m = s["meta"]
    lines = [f"# E7b part {m['part']} ({SPEC})", "", LABEL, ""]
    if m.get("reduced"):
        lines += [f"Reduced run: {m.get('reduced_note')}", ""]
    by: dict = {}
    for r in s["runs"]:
        by.setdefault((r["tag"], r["mode"]), []).append(r)
    rows = []
    for (t, md), rs in sorted(by.items()):
        b = [x.get("bound") or {} for x in rs]
        fin = [x.get("final_excess_rel") for x in b if x.get("final_excess_rel") is not None]
        rt = [x.get("runtime_max_excess_rel") for x in b if x.get("runtime_max_excess_rel") is not None]
        rows.append([t, md, len(rs), e7h._median([x.get("r0") for x in rs]), sum(1 for x in b if x.get("above")),
                     max(fin) if fin else None, max(rt) if rt else None,
                     sum(int((x.get("cap") or {}).get("bind_slots") or 0) for x in rs)])
    lines += ["## Per tag and mode (r0 = cost over BL0a; excess over FB(T) + B(T) relative to FB(T))", "",
              mc.md_table(["tag", "mode", "runs", "median r0", "above bound", "max final excess",
                           "max run-time excess", "bind slots"], rows), ""]
    g = s["guard_summary"]
    lines += ["## Guarded runs", "", mc.md_table(["runs", "held", "envelope violations", "aborts", "projected slots"],
                                                 [[g["n_runs"], g["held"], g["n_envelope_violations"], g["aborts"],
                                                   g["projected_slots"]]]), ""]
    lines += ["## Missing runs", "", mc.md_table(["job", "tag", "mode", "cell", "seed", "why"],
                                                 [[x["job"], x["tag"], x["mode"], x["cell"], x["seed"], x["why"]]
                                                  for x in s["missing"]]), ""]
    return "\n".join(lines) + "\n"


def _part_of(out) -> Optional[str]:
    out = Path(out)
    if out.name in PARTS:
        return out.name
    ps = parts()
    return ps[0] if len(ps) == 1 else None


def summary(out) -> dict:
    """The summary of the part whose folder `out` is (its name), else of the one part of E7B_PART."""
    part = _part_of(out)
    if part is None:
        raise ValueError(f"--summary needs one part (E7B_PART) or a part's folder, got {out}")
    return summary_part(part, Path(out))


def manifest_extra(out) -> dict:
    """The job grid's design, the instance hashes the run files record (no instance is rebuilt), the sha256 of the
    sources and the gate as the manifest's process sees it (recorded, not enforced)."""
    out = Path(out)
    part = _part_of(out)
    js = [j for j in jobs_all() if part is None or j.params["part"] == part]
    hashes = {}
    for j in js:
        f = mc.read_json(run_path(out, j.id))
        if not isinstance(f, dict):
            continue
        if isinstance(f.get("instances"), dict):
            hashes[j.id] = {k: v.get("instance_hash") for k, v in f["instances"].items() if isinstance(v, dict)}
        elif f.get("instance_hash") is not None:
            hashes[j.id] = {"point": f.get("instance_hash")}
    src = {}
    for rel in SOURCES:
        f = paths.SIM / rel
        src[str(f.relative_to(paths.REPO))] = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
    ok, why, rec = check_registration()
    return {"part": part, "design": design(), "instance_hashes_from_outputs": hashes, "sources_sha256": src,
            "gate": {"kind": GATE_KIND, "ok": ok, "reason": why, "record": rec}}


# ---------------------------------------------------------------- the missing-run rule's rerun (as e7h's)
def retry_list(out) -> list:
    """The pool jobs of the part to run once more: a record not 'ok', or 'ok' with a run that raised or failed an
    invariant; each one's record moves to retry/ and its output to runs/retry/ first, once per job (e7h.retry_list's
    rule). Returns '<kind> <id>' lines."""
    out = Path(out)
    part = _part_of(out)
    js = [j for j in jobs_all() if j.params["part"] == part and j.kind == "pool"]
    lines = []
    for j in js:
        name = mc.job_file_name(j.id)
        old = out / "retry" / name
        if old.is_file():
            continue
        rec = mc.read_record(out, j.id)
        if rec is None:
            continue
        path = run_path(out, j.id)
        bad = rec.get("status") != "ok" or int(rec.get("n_errors") or 0) > 0
        if not bad:
            f = mc.read_json(path) or {}
            bad = any(m5.run_status(e) == "invariant_failure" for e in f.get("runs") or [])
        if not bad:
            continue
        old.parent.mkdir(parents=True, exist_ok=True)
        mc.dump_json({"job": j.id, "first_record": rec, "moved": mc._now(), "rule": "e7h.retry_list's rule"}, old)
        if mc.record_path(out, j.id).is_file():
            mc.record_path(out, j.id).unlink()
        if path.is_file():
            keep = out / "runs" / "retry" / name
            keep.parent.mkdir(parents=True, exist_ok=True)
            path.rename(keep)
        lines.append(f"{j.kind} {j.id}")
    return lines


# ---------------------------------------------------------------- command line
def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check-start" in args:
        try:
            g = gate()
        except RuntimeError as err:
            print(f"[e7b] {' '.join(parts())}: REFUSED: {err}", file=sys.stderr)
            return 1
        print(f"[e7b] {' '.join(parts())}: gate {g['kind']} {'ok' if g['ok'] else 'REFUSED (not enforced)'}: "
              f"{g['reason']}")
        return 0
    if "--retry-list" in args:
        ap = argparse.ArgumentParser(prog="python -m sublet.experiments.e7b --retry-list")
        ap.add_argument("--retry-list", action="store_true", required=True)
        ap.add_argument("--out", type=Path, required=True)
        a = ap.parse_args(args)
        for ln in retry_list(a.out):
            print(ln)
        return 0
    if "--out" not in args and any(x in args for x in ("--job", "--summary", "--manifest")):
        ps = parts()
        if len(ps) == 1:
            args += ["--out", str(part_dir(ps[0]))]
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra, argv=args,
                   description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
