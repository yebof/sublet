"""S1 v2: Sublet's own sensitivity across the register, with A9 and the two strongest baselines (design/ms7/plan.md
X3, D6, D9; design/ms7/feasibility/sens.md §2 A, §3 item 1; change C56). Exploratory: post-freeze runs on the
confirmation weeks, pre-specified by design/ms7/registration.md (the gate below); the MS5b confirmation and its frozen
analysis are untouched (e7h.py, ms5b_analysis.py and ms5b_common.TAGS are imported, never changed).

This module also holds unit B4's small shared layer (C56), which e5v2, e8v2 and e9v2 import: the weeks, the
registration gate, the tags (ms5b_common's, plus BL3-2), one run of a tag through e7h.one_run, the summary rows and
the checks shared by the four drivers.

Instance (§2 A). The E7 main week of the confirmation: configs/bench_e7f.json through ms4_common.e7_spec at mu / beta~
= 1 (one week of 1-min routing on 5-min slow slots, the full a11 menu, all 24 lenders, regional borrowers, I1, 'sell',
violations absorbed, engine.check_invariants true, unmerged layers), config seed = lender seed = week c in WEEKS
(301-304, the confirmation's weeks of part seeds and second), policy seed 0 (Sublet's r0 did not move with the policy
seed on these weeks, feasibility §1.2). A point adds its overrides to e7_spec's (point_spec); its overrides come from
s1.point_overrides' builders on the default build `ref` of the same week, so a point of S1 is built here exactly as S1
built it, on the confirmation's weeks. At the default point the spec is the confirmation's L-tr week spec
(ms5b_common.week_spec), so its runs must equal part main's (check S1v2-0).

Points (POINTS, 57 with the default): S1's 50 points but buf999, plus
  mu0.2, mu0.5, mu2      mu / beta~ in {0.2, 0.5, 2} through e7_spec's mu argument (overrides may not set mu); S1 read
                         this row from MS4's E7 summary, which ran the earlier configuration
  kappaM05, kappaM2      kappa of M alone x0.5 and x2 (s1._ov_kappa('M', ...)), the row kappa_M beside S1's kappa_L
                         (a uniform multiplier cancels through Gamma, s1.NOT_RUN)
  fee8, fee16            transfer fees with rho = 8 and 16 (s1._ov_fee; calib.beta_for_rho raises below the calibrated
                         rho, at most 3.80 for L on the E7 week, so S1's fee4 and these two are the points above it)
Read, not rerun (REUSED): buf999 is the confirmation's mode L-b999 (the same override, ms5b_common.B999_OVERRIDES), and
Q28's variants are its modes L-rf and L-vr, all three in part second on weeks 301-304 for every tag here; the
summary copies their r0 with the file's sha256.

Policies (TAGS, ms5b_common's tags, parameters on each run's own instance): Sublet (A8P around A9 at the allowance
'lb', ms5b_common.sublet_v2_params), A9 (critical-ratio renting alone), BL1-BO and BL5-cur (the per-week best of H1's
set in every confirmation week). Part w0 adds BL4 (the best baseline under W0 in every confirmation week).

Parts (S1V2_PART; COPY_PARTS['s1v2'], C56):
  sweep  s1v2:sweep:pt=<point>:c=<c>   57 points x 4 weeks = 228 jobs; one job runs the four tags at policy seed 0
                                       under L-tr in one process, so the build and A9's contract table are shared
  w0     s1v2:w0:pt=<point>:c=<c>      W0 (the five stress modes of ms5b_common.stress_modes) at the load-scenario and
                                       transfer-fee rows (8 + 3 points) on weeks 301-302 for the four tags and BL4: 22
                                       jobs of 25 runs; the default point's W0 is read from part main's W0 table
Job limits as S1's (three times the job's estimate, at least 1,800 s; `--limits` for run_s1v2.sh). Estimates: S1's
seconds per Sublet-MS4 week run at the point (s1.est_run_s) times the tag's ratio of the feasibility study's §4
(EST_RATIO: Sublet v2 1.10, A9 0.30, BL1-BO 0.072, BL5-cur 0.065, BL4 0.20) plus A9's contract table once per job.

The gate (D6). A full run refuses to start unless design/ms7/registration.md exists at HEAD, the working tree is clean
(ms5b_common.dirty_paths: untracked outputs under code/sim/out/ do not count) and the sha256 of
experiments/ms7_sens_analysis.py, on disk and at HEAD, equals the one the registration records on its line
'ms7_sens_analysis_sha256: <64 hex>'; reduced runs record the gate (kind 'ms7_registration') without enforcing it.
Every run file and summary records it. `--check-start` prints it and exits 1 when refused (the run scripts stop with
exit 2).

Command line (ms3_common.main), run from code/sim:
  python -m sublet.experiments.s1v2 --list | --job ID | --summary | --estimate | --manifest  [--out DIR]
  python -m sublet.experiments.s1v2 --limits | --check-start
Reduced runs (MS3_S1V2_REDUCED=1, run_s1v2.sh --reduced): development week 101 (never a confirmation week), policy
seed 0, a 2-hour horizon, every point and tag; part w0 at week 101 with its points; never a result.

Outputs <root>/out/s1v2/<part>/ (jobs/, logs/, runs/ (not versioned), manifest.json, summary.json, tables.md,
run_s1v2.log). sweep/summary.json: meta (grids, points, rows, tags, the gate, the sources' sha256), runs (one row per
run: point, week, tag, seed, r0, ALG, status, guard and A9 facts), table {tag: {point: {c: {seed: r0}}}} (null for a
run missing or failed), points.<point> {row, value, label, mu, by_tag.<tag> (e7.cost_entry)}, reused.<point> (the
second part's r0 by tag and week, with its source), missing, checks S1v2-0 ... S1v2-3. w0/summary.json: table {tag:
{mode: {point: {c: {seed: r0}}}}}, W0 {tag: {point: {c: W0}}}, reused_default_W0 (part main's W0 table at the default),
checks S1v2-W1, S1v2-W2. The quantities of the study (savings, Delta, the weeks of H1's ordering, W0 orderings) are
computed by ms7_sens_analysis.py from these summaries.

Status labels (copied from ms5b_common, never upgraded): Theorem W(a)(b), G2 and G3(b) PROVEN for A8; for A8P through
Remark R, PROVEN, audited; Lemma G5' and Corollary G3' PROVEN, audited; Proposition P PROVEN, audited; A9's rules
HEURISTIC; S1 v2 is a sensitivity study with no theory claim.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import copy
import gc
import hashlib
import math
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from .. import paths
from . import e3
from . import e7
from . import e7h
from . import ms3_common as mc
from . import ms4_common as m4
from . import ms5b_common as m5
from . import s1
from .ms3_common import Job, job_id, num_key, put

# ================================================================ the unit's shared layer (C56)
CHANGE = "C56"
PLAN = "design/ms7/plan.md X3, D6"
LABEL = "exploratory: post-freeze runs on the confirmation weeks (design/ms7/plan.md D6), not a confirmation result"
WEEKS = (301, 302, 303, 304)                       # the confirmation weeks of parts seeds and second (§2)
REDUCED_WEEK = 101                                 # development week of the reduced lists (e7h.REDUCED_WEEK)
REDUCED_HORIZON_MIN = 120
POLICY_SEEDS = (0,)                                # §2: policy seed 0 (Sublet's r0 is seed-free on these weeks)
H1_PAIR = ("BL1-BO", "BL5-cur")                    # the per-week best of H1's set in every confirmation week
TAGS4 = ("Sublet", "A9") + H1_PAIR
REL_TOL = 1e-9                                     # identity checks against the confirmation's records
# the confirmation's versioned outputs that the drivers read (tests point CONF_DIR elsewhere)
CONF_DIR = paths.SIM_OUT / m5.CONF_DIR
CONF_REL = "code/sim/out/" + m5.CONF_DIR
# the registration of the unit's analysis (D6): design/ms7/registration.md records the analysis script's sha256 on
# its line 'ms7_sens_analysis_sha256: <64 hex>' (the script's basename without .py, as unit B1's e7c_analysis)
REGISTRATION = "design/ms7/registration.md"
ANALYSIS_FILE = Path(__file__).resolve().parent / "ms7_sens_analysis.py"
ANALYSIS_REL = "code/sim/sublet/experiments/ms7_sens_analysis.py"
REG_KEY = "ms7_sens_analysis_sha256"
REG_SHA_RE = re.compile(r"^ms7_sens_analysis_sha256:\s*([0-9a-f]{64})\s*$", re.MULTILINE)
GATE_KIND = "ms7_registration"
# BL3-2 (E5's SpotHedge-style baseline with spares, BL3 at its default n_extra 2) is no tag of ms5b_common.TAGS
LOCAL_TAGS = {"BL3-2": m5.Tag("BL3", {}, "baseline", False,
                              "SpotHedge-style with spares: BL3 at its default n_extra 2 (E5's BL3-2; plan X3)")}


def conf_file(part: str, name: str = "summary.json") -> Path:
    """<CONF_DIR>/<part>/<name>: a versioned file of the MS5b confirmation (out/sublet_v2/)."""
    return Path(CONF_DIR) / part / name


def conf_source(part: str, name: str = "summary.json") -> tuple[Optional[dict], dict]:
    """(the confirmation's file or None, its source record: file, exists, sha256, git_revision)."""
    f = conf_file(part, name)
    d = mc.read_json(f)
    src = {"file": f"{CONF_REL}/{part}/{name}", "exists": f.is_file(),
           "sha256": hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None,
           "git_revision": ((d or {}).get("meta") or {}).get("git_revision")}
    if d is None:
        src["note"] = "missing or unreadable"
    return d, src


def conf_r0(table: Optional[Mapping], tag: str, mode: str, cell: str, seed: int = 0) -> Optional[float]:
    """r0 of a confirmation summary's table {tag: {mode: {cell: {seed: r0}}}} (None when absent or null)."""
    v = (((table or {}).get(tag) or {}).get(mode) or {}).get(cell, {}).get(num_key(seed))
    return None if v is None else float(v)


def rel_diff(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    return abs(float(a) - float(b)) / max(abs(float(b)), 1e-300)


# ---------------------------------------------------------------- the registration gate (D6)
def analysis_sha256() -> Optional[str]:
    return m5._sha(ANALYSIS_FILE.read_bytes()) if ANALYSIS_FILE.is_file() else None


def registered_sha256(text: Optional[str]) -> Optional[str]:
    """The analysis script's sha256 that the registration records (its line 'ms7_sens_analysis_sha256: <64 hex>');
    None without such a line."""
    if not text:
        return None
    m = REG_SHA_RE.search(text)
    return m.group(1) if m else None


def registration_record() -> dict:
    """The gate's facts (read-only git, ms5b_common's helpers): HEAD, whether design/ms7/registration.md exists at
    HEAD, its sha256 and the analysis sha256 it records, the sha256 of ms7_sens_analysis.py on disk and at HEAD, and
    the dirty paths (ms5b_common.dirty_paths: untracked files under code/sim/out/ do not count)."""
    reg = m5.file_at("HEAD", REGISTRATION)
    return {"head": m5.head_commit(), "registration": REGISTRATION, "registration_at_head": reg is not None,
            "registration_sha256": m5._sha(reg), "analysis": ANALYSIS_REL,
            "analysis_sha256_registered": registered_sha256(None if reg is None else reg.decode("utf-8", "replace")),
            "analysis_sha256_head": m5._sha(m5.file_at("HEAD", ANALYSIS_REL)),
            "analysis_sha256_disk": analysis_sha256(), "dirty_paths": m5.dirty_paths()}


def check_registration(rec: Optional[Mapping] = None) -> tuple[bool, str, dict]:
    """(ok, reason, record): a full run starts only if design/ms7/registration.md exists at HEAD, the working tree is
    clean and the sha256 of ms7_sens_analysis.py, on disk and at HEAD, equals the one its line
    'ms7_sens_analysis_sha256: <64 hex>' records (D6)."""
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
        return False, "the run does not start (design/ms7/plan.md D6): " + "; ".join(why), rec
    return True, "registration at HEAD, clean tree, analysis sha256 as registered", rec


_GATE: dict = {}


def gate_state(reduced: bool) -> dict:
    """The gate's record, taken once per process: {kind, ok, reason, enforced (full runs), registration}; never
    raises (summaries and manifests record it)."""
    key = bool(reduced)
    if key not in _GATE:
        ok, why, rec = check_registration()
        g = {"kind": GATE_KIND, "ok": ok, "reason": why, "enforced": not key, "registration": rec}
        if key:
            g["note"] = "reduced run on a development week: the gate is recorded, not enforced"
        _GATE[key] = g
    return _GATE[key]


def gate(reduced: bool) -> dict:
    """The gate of a job: enforced in full runs (RuntimeError when refused), recorded in reduced runs, which use the
    development week only."""
    g = gate_state(reduced)
    if g["enforced"] and not g["ok"]:
        raise RuntimeError(g["reason"])
    return g


def check_start(exp: str, reduced: bool) -> int:
    """--check-start: the gate's line; 1 if a full run is refused."""
    try:
        g = gate(reduced)
    except RuntimeError as err:
        print(f"[{exp}] REFUSED: {err}", file=sys.stderr)
        return 1
    print(f"[{exp}] gate {'ok' if g['ok'] else 'REFUSED (not enforced)'}: {g['reason']}")
    return 0


# ---------------------------------------------------------------- tags
def tag(name: str) -> m5.Tag:
    return LOCAL_TAGS[name] if name in LOCAL_TAGS else m5.tag(name)


def tag_id(name: str) -> str:
    return tag(name).id


def tag_params(name: str, inst=None) -> dict:
    """The resolved parameters of a tag on the run's own instance (ms5b_common.tag_params; BL3-2's {})."""
    if name in LOCAL_TAGS:
        return copy.deepcopy(dict(LOCAL_TAGS[name].params))
    return m5.tag_params(name, inst)


def tag_table(names: Iterable[str]) -> dict:
    """ms5b_common.tag_table with BL3-2, in the order of `names`."""
    names = list(names)
    base = m5.tag_table([n for n in names if n not in LOCAL_TAGS])
    out = {}
    for n in names:
        if n in LOCAL_TAGS:
            t = LOCAL_TAGS[n]
            out[n] = {"policy_id": t.id, "params": dict(t.params), "kind": t.kind, "a9_family": t.a9_family,
                      "role": t.role, "information": t.information}
        else:
            out[n] = base[n]
    return out


def a9_family(name: str) -> bool:
    return tag(name).a9_family


# ---------------------------------------------------------------- runs and rows
def run_tag(errors: list, spec: dict, name: str, inst, ecfg, refs: dict, own, c: int, ps: int, mode: str):
    """One run of tag `name` (the spec's policy) through e7h.one_run under the spec's lender model, as
    ms5b_common.week_entry's entry (None when it raised; the error goes to `errors`), with its lender model."""
    from ..drivers import run as drun
    model = drun._lender_model(spec, inst)
    e = mc.try_run(errors, f"{name} {mode} p{ps}", e7h.one_run, spec, name, inst, model, ecfg, refs, own, int(c),
                   int(ps), mode)
    return e, model


def errs(errors: list) -> list:
    return [{k: v for k, v in e.items() if k != "traceback"} for e in errors]


def brief(e: Mapping, **cell) -> dict:
    """One run's summary row: the cell fields, tag, mode, seed, the missing-run rule's status, r0, ALG, BL0a, the
    fallback and stranding totals and shares, the leases, the guard facts (e7h.guard_brief) and A9's counts."""
    row = {**cell, "tag": e["tag"], "mode": e.get("mode"), "seed": int(e.get("policy_seed", 0)),
           "status": e.get("status") or m5.run_status(e), "r0": e.get("r0"), "ALG": e.get("ALG"),
           "bl0a_usd": e.get("bl0a_usd"), "fallback_usd": e.get("fallback_usd"),
           "stranding_usd": e.get("stranding_usd"), "fallback_share": e.get("fallback_share"),
           "fallback_share_after_reclaims": e.get("fallback_share_after_reclaims"), "n_leases": e.get("n_leases"),
           "n_invariant_failures": e.get("n_invariant_failures"), "wall_s": e.get("wall_s")}
    g = e7h.guard_brief(e.get("a8"))
    if g is not None:
        row["guard"] = g
    a9 = e7h._a9_brief(e.get("a9"))
    if a9 is not None:
        row["a9"] = a9
    return row


def part_outputs(out_p: Path, js: Sequence[Job], path_of: Callable[[Job], Path]) -> tuple:
    """({job id: output} of the jobs whose record says 'ok', the ok ids, ignored outputs, {job id: status} of the
    others ('no record' without one)): an output present while its job's record is not 'ok' is listed and not used."""
    recs = mc.read_records(out_p)
    data, ok, ignored, not_ok = {}, set(), [], {}
    for j in js:
        rec = recs.get(j.id) or {}
        path = path_of(j)
        if rec.get("status") != "ok":
            not_ok[j.id] = rec.get("status") or "no record"
            if path.is_file():
                ignored.append({"job": j.id, "status": rec.get("status"), "output": e3._rel(path, out_p)})
            continue
        d = mc.read_json(path)
        if d is None:
            not_ok[j.id] = "ok record without a readable output"
            continue
        data[j.id] = d
        ok.add(j.id)
    return data, ok, ignored, not_ok


def status_of(fail: bool, n: int, missing: bool = False) -> str:
    """'fail' if a run fails the check, else 'missing' without runs or while a job lacks an 'ok' output, else 'pass'."""
    if fail:
        return "fail"
    return "missing" if (n == 0 or missing) else "pass"


def guard_check(rows: Sequence[Mapping], missing: bool = False) -> dict:
    """The guard facts of the guarded runs (H3's rule on these runs): the certificate is available and holds in
    Theorem W's proven cases (W(a), W(b)), the envelope ALG(t) + R(t) <= gamma C_S(t) + B(t) + tolerance holds at
    every executed slot, and no projecting A8P run aborts while S follows FB everywhere and T0g stays in bound form
    (Proposition P); with e7h.guard_summary's counts (aborts, projected slots, K0, dropped Buys)."""
    gs = [{**{k: r.get(k) for k in ("job", "tag", "mode", "seed")}, **r["guard"]} for r in rows if r.get("guard")]
    summ = e7h.guard_summary(gs)
    unav = [g for g in gs if g.get("case") in (None, "unavailable")]
    bad_cert = [g for g in gs if g.get("case") in m4.PROVEN_CASES and g.get("held") is not True]
    wc = [g for g in gs if g.get("case") == "W(c)"]
    fail = bool(unav or bad_cert or summ["n_envelope_violations"] or summ["n_aborts_s_fb_bound_form"])
    return {"status": status_of(fail, len(gs), missing), "n_runs": len(gs), "summary": summ,
            "unavailable": unav[:50], "n_unavailable": len(unav), "certificate_failures": bad_cert[:50],
            "n_certificate_failures": len(bad_cert), "n_w_c": len(wc), "w_c_runs": wc[:50]}


def clean_check(rows: Sequence[Mapping], run_errors: Sequence[Mapping], missing_runs: Sequence[Mapping],
                job_failures: Mapping, missing: bool = False) -> dict:
    """Every run finished with status 'ok' (no invariant failure; ms5b_common.run_status), no run raised, and no job
    ended in a failure status; the runs missing from the grid are listed."""
    bad = [{k: r.get(k) for k in ("job", "tag", "mode", "seed", "status")} for r in rows if r.get("status") != "ok"]
    jf = [{"job": j, "status": s} for j, s in sorted(job_failures.items())
          if s in ("error", "failed", "oom_at_3G", "wall_limit")]
    fail = bool(bad or run_errors or jf)
    return {"status": status_of(fail, len(rows), missing or bool(missing_runs)), "n_runs": len(rows),
            "not_ok": bad[:50], "n_not_ok": len(bad), "run_errors": list(run_errors)[:50],
            "n_run_errors": len(run_errors), "job_failures": jf[:50], "n_job_failures": len(jf),
            "missing_runs": list(missing_runs)[:100], "n_missing_runs": len(missing_runs)}


def run_errors_of(files: Mapping) -> list:
    return [{"job": jid, **x} for jid, f in files.items() for x in f.get("errors") or []]


def meta_common(exp: str, part: Optional[str], spec: str, reduced: bool, **extra) -> dict:
    m = {"exp": exp, "part": part, "spec": spec, "change": CHANGE, "label": LABEL,
         "git_revision": mc.git_revision(), "versions": mc.versions(), "written": mc._now(), "reduced": bool(reduced),
         "gate": gate_state(reduced)}
    m.update(extra)
    return m


def limits_main(exp: str, jobs_fn: Callable[[], Sequence[Job]], args: list) -> Optional[int]:
    """--limits: '<kind> <limit_s> <job id>' per job (the run scripts' jobs_limits.txt); None if not asked."""
    if "--limits" not in args:
        return None
    ap = argparse.ArgumentParser(prog=f"python -m sublet.experiments.{exp} --limits")
    ap.add_argument("--limits", action="store_true", required=True)
    ap.parse_args(args)
    js = list(jobs_fn())
    mc.check_jobs(js)
    for j in js:
        print(f"{j.kind} {int(j.params['limit_s'])} {j.id}")
    return 0


def job_limit_s(est_s: float, floor_s: int = s1.LIMIT_MIN_S, factor: float = s1.LIMIT_FACTOR) -> int:
    """Three times the job's estimate, at least 1,800 s (S1's rule, whole seconds)."""
    return int(max(floor_s, math.ceil(factor * float(est_s))))


# ================================================================ S1 v2
EXP = "s1v2"
SPEC = "design/ms7/feasibility/sens.md §2 A, §3 item 1 (C56)"
PARTS = mc.COPY_PARTS[EXP]                         # ("sweep", "w0"), C56
TAGS = TAGS4
W0_TAGS = TAGS4 + ("BL4",)
W0_WEEKS = (301, 302)
MU = 1.0
DEFAULT = s1.DEFAULT
REDUCED_ENV = "MS3_S1V2_REDUCED"
# seconds per week run relative to S1's Sublet-MS4 run at the point (feasibility §4) and A9's table once per job
EST_RATIO = {"Sublet": 1.10, "A9": 0.30, "BL1-BO": 0.072, "BL5-cur": 0.065, "BL4": 0.20}
EST_TABLE_S = e7h.EST_TABLE_S
EST_JOB_S = 5.0
# the feasibility study's estimate of the longest sweep job at the week (slow1: about 2,000 s, §4), above EST_RATIO's
EST_WEEK_JOB_S = {("sweep", "slow1"): 2000.0}


@dataclass(frozen=True)
class Point:
    """One S1 v2 point: S1's fields (row, value, label, the builder of its overrides from the default build of the
    same week) and its mu / beta~ (1 but at the mu row)."""
    name: str
    row: str
    value: object
    label: str
    build: Callable
    mu: float = 1.0


REUSED = {"buf999": {"row": "buffer_quantile", "value": 0.999, "label": "0.999", "part": "second",
                     "mode": m5.B999_MODE, "note": "prices.buffer_quantile 'p99.9' under L-tr (the override of S1's "
                                                    "buf999, ms5b_common.B999_OVERRIDES)"},
          "q28_rf": {"row": "q28_rf", "value": "L-rf", "label": "L-rf", "part": "second", "mode": "L-rf",
                     "note": "Q28's refusals: lender_model.on_unavailable 'refuse' on the trace schedule"},
          "q28_vr": {"row": "q28_vr", "value": "L-vr", "label": "L-vr", "part": "second", "mode": "L-vr",
                     "note": "Q28's violations as reclaims: lender_model.violations 'reclaim'"}}

_NEW = [Point("mu0.2", "mu", 0.2, "0.2", s1._static({}), 0.2), Point("mu0.5", "mu", 0.5, "0.5", s1._static({}), 0.5),
        Point("mu2", "mu", 2.0, "2", s1._static({}), 2.0),
        Point("kappaM05", "kappa_M", 0.5, "x0.5", s1._ov_kappa("M", 0.5)),
        Point("kappaM2", "kappa_M", 2.0, "x2", s1._ov_kappa("M", 2.0)),
        Point("fee8", "transfer_fee", 8.0, "rho = 8", s1._ov_fee(8.0)),
        Point("fee16", "transfer_fee", 16.0, "rho = 16", s1._ov_fee(16.0))]
POINTS = {p.name: Point(p.name, p.row, p.value, p.label, p.build) for p in s1._POINT_LIST if p.name not in REUSED}
POINTS.update({p.name: p for p in _NEW})
POINT_NAMES = tuple(POINTS)                        # the default first, S1's order, then the added points (57)
ROWS = {}
for _k, _r in s1.ROWS.items():
    ROWS[_k] = _r
    if _k == "kappa_L":
        ROWS["kappa_M"] = s1.Row("kappa_M", "kappa of M", "b", True, "x1", "llms.<M>.kappa_mult")
ROWS_ORDER = tuple(ROWS) + ("q28_rf", "q28_vr")
W0_ROWS = ("load_scenario", "transfer_fee")
W0_POINTS = tuple(n for n, p in POINTS.items() if p.row in W0_ROWS)      # 8 scenarios, fee4, fee8, fee16
NOT_RUN = tuple(dict(x) for x in s1.NOT_RUN) + tuple(
    {"row": k, "reason": f"read, not rerun: part {v['part']}'s mode {v['mode']} ({v['note']})",
     "sources": [f"{CONF_REL}/{v['part']}/summary.json"]} for k, v in REUSED.items())
CHECK_IDS_SWEEP = ("S1v2-0", "S1v2-1", "S1v2-2", "S1v2-3")
CHECK_IDS_W0 = ("S1v2-W1", "S1v2-W2")
CHECK_CLAIMS = {
    "S1v2-0": "at the default point every tag's L-tr run equals part main's (r0 within 1e-9 relative, the instance "
              "hash equal to main's manifest) on every week",
    "S1v2-1": "every point is built as S1 builds it (s1.vs_default's facts): its instance hash differs from the "
              "default's; on the rows without Gamma the demand and BL0a equal the default's; every LLM fits a layer "
              "site; every LLM but S at sS0 has clients",
    "S1v2-2": "every Sublet run: certificate available and held in Theorem W's proven cases, the envelope holds, no "
              "projecting run aborts while S follows FB and T0g stays in bound form (Proposition P)",
    "S1v2-3": "every run finishes with status ok (no invariant failure), no run raised, every run of the grid exists",
    "S1v2-W1": "every W0 run finishes with status ok, no run raised, every run of the grid exists",
    "S1v2-W2": "the guard facts of S1v2-2 on part w0's Sublet runs"}


def reduced() -> bool:
    return os.environ.get(REDUCED_ENV, "0") == "1"


def design() -> dict:
    red = reduced()
    return {"reduced": red, "weeks": (REDUCED_WEEK,) if red else WEEKS,
            "w0_weeks": (REDUCED_WEEK,) if red else W0_WEEKS, "policy_seeds": POLICY_SEEDS,
            "horizon_min": REDUCED_HORIZON_MIN if red else m4.WEEK_MIN}


def parts() -> list:
    v = os.environ.get("S1V2_PART", "")
    ps = [p for p in v.replace(",", " ").split() if p]
    bad = [p for p in ps if p not in PARTS]
    if bad:
        raise ValueError(f"S1V2_PART must name parts of {list(PARTS)}, got {v!r}")
    return ps or list(PARTS)


def part_dir(out, part: str) -> Path:
    o = Path(out)
    return o if o.name == part else o / part


def sweep_id(point: str, c: int) -> str:
    return job_id(EXP, "sweep", pt=point, c=int(c))


def w0_id(point: str, c: int) -> str:
    return job_id(EXP, "w0", pt=point, c=int(c))


def run_path(out, part: str, jid: str) -> Path:
    return part_dir(out, part) / "runs" / mc.job_file_name(jid)


def est_run_s(point: str, tag_name: str) -> float:
    """Seconds of one week run of `tag_name` at `point`: S1's Sublet-MS4 time there (s1.est_run_s; the default's at
    the added points but fee8 and fee16, which take fee4's) times EST_RATIO."""
    base = point if point in s1.POINTS else ("fee4" if point.startswith("fee") else DEFAULT)
    return s1.est_run_s(base) * EST_RATIO[tag_name]


def est_job_s(point: str, tags, n_modes: int, scale: float) -> float:
    fam = any(a9_family(t) for t in tags)
    return EST_JOB_S + (EST_TABLE_S if fam else 0.0) + n_modes * scale * sum(est_run_s(point, t) for t in tags)


def jobs(ps=None) -> list:
    """The jobs of the parts `ps` (default S1V2_PART), each part's jobs longest first (ties in POINTS order and by
    week)."""
    ps = parts() if ps is None else list(ps)
    d = design()
    hz, seeds = d["horizon_min"], list(d["policy_seeds"])
    scale = float(hz) / float(m4.WEEK_MIN)
    out = []
    if "sweep" in ps:
        js = []
        for i, name in enumerate(POINT_NAMES):
            pt = POINTS[name]
            for c in d["weeks"]:
                est = max(est_job_s(name, TAGS, 1, scale), EST_WEEK_JOB_S.get(("sweep", name), 0.0) * scale)
                js.append((-est, i, c, Job(sweep_id(name, c), "pool",
                                           {"part": "sweep", "kind": "sweep", "point": name, "row": pt.row or None,
                                            "mu": pt.mu, "c": int(c), "tags": list(TAGS), "modes": ["L-tr"],
                                            "policy_seeds": seeds, "horizon_min": hz, "limit_s": job_limit_s(est)},
                                           est)))
        out += [j for *_, j in sorted(js, key=lambda x: x[:3])]
    if "w0" in ps:
        js = []
        modes = list(m5.stress_modes())
        for i, name in enumerate(W0_POINTS):
            for c in d["w0_weeks"]:
                est = est_job_s(name, W0_TAGS, len(modes), scale)
                js.append((-est, i, c, Job(w0_id(name, c), "pool",
                                           {"part": "w0", "kind": "w0", "point": name, "row": POINTS[name].row,
                                            "mu": POINTS[name].mu, "c": int(c), "tags": list(W0_TAGS),
                                            "modes": modes, "policy_seeds": seeds, "horizon_min": hz,
                                            "limit_s": job_limit_s(est)}, est)))
        out += [j for *_, j in sorted(js, key=lambda x: x[:3])]
    return out


def jobs_all() -> list:
    return jobs(list(PARTS))


def expected_runs(job: Job) -> list:
    """(tag, mode, point, c, seed) of every run a job owes."""
    p = job.params
    return [(t, m, p["point"], int(p["c"]), int(s)) for t in p["tags"] for m in p["modes"] for s in p["policy_seeds"]]


# ---------------------------------------------------------------- specs and builds
def point_spec(policy_id: str, params=None, overrides=None, *, mu: float = MU, mode: str = "L-tr",
               horizon_min: int = m4.WEEK_MIN, c: int = 1, seeds=(0,), name: str = "s1v2") -> dict:
    """The validated run spec of one run: ms4_common.e7_spec at mu with the mode's lender model and overrides
    (ms5b_common.mode_lender_model, mode_overrides) and the point's overrides; config seed c, lender 'config', policy
    `seeds`. At the default point under L-tr this is ms5b_common.week_spec's spec."""
    ov = {**copy.deepcopy(dict(overrides or {})), **m5.mode_overrides(mode)}
    return m4.e7_spec(policy_id, params, mu=float(mu), horizon_min=int(horizon_min),
                      lender_model=m5.mode_lender_model(mode), overrides=ov, name=name,
                      seeds={"config": [int(c)], "lender": "config", "policy": [int(p) for p in seeds]})


def build_ref(c: int, horizon_min: int) -> tuple:
    """(inst, model, ecfg) of the default point at week c."""
    from ..drivers.run import build
    return build(point_spec("BL0a", {}, {}, horizon_min=horizon_min, c=c, name="s1v2_default"), int(c))


def build_point(name: str, ref, c: int, horizon_min: int) -> tuple:
    """(inst, model, ecfg, overrides) of the point `name` at week c, `ref` the default build of c (its own instance
    at the default)."""
    from ..drivers.run import build
    pt = POINTS[name]
    ov = pt.build(ref)
    if name == DEFAULT:
        return ref, None, None, ov
    inst, model, ecfg = build(point_spec("BL0a", {}, ov, mu=pt.mu, horizon_min=horizon_min, c=c,
                                         name=f"s1v2_{name}"), int(c))
    return inst, model, ecfg, ov


def _build_job(p: Mapping) -> dict:
    """The default build of the week and the point's instance with the facts of S1v2-1 (the default's build is
    dropped once the facts are taken)."""
    name, c, hz = p["point"], int(p["c"]), int(p["horizon_min"])
    t0 = time.perf_counter()
    ref, model, ecfg = build_ref(c, hz)
    ih_ref = mc.instance_hash(ref)
    inst, m2, e2, ov = build_point(name, ref, c, hz)
    if inst is not ref:
        model, ecfg = m2, e2
    if not ecfg.check_invariants:
        raise RuntimeError("S1 v2 runs need check_invariants=True")
    ih = ih_ref if inst is ref else mc.instance_hash(inst)
    facts = s1.vs_default(inst, ref, ih, ih_ref)
    if inst is not ref:
        del ref
        gc.collect()
    return {"inst": inst, "ecfg": ecfg, "overrides": ov, "instance_hash": ih, "facts": facts,
            "refs": m4.references(inst), "own": e7._own(inst), "build_s": time.perf_counter() - t0}


def run_cells(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One sweep or w0 job: the point's instance (built once), then every tag of p['tags'] under every mode of
    p['modes'] at each policy seed (one process, so A9's contract table is computed once)."""
    p = job.params
    part, name, c, hz, seeds = p["part"], p["point"], int(p["c"]), int(p["horizon_min"]), list(p["policy_seeds"])
    g = gate(reduced())
    b = _build_job(p)
    inst, ecfg, refs, own = b["inst"], b["ecfg"], b["refs"], b["own"]
    pt = POINTS[name]
    errors, rows, params_rec, models = [], [], {}, {}
    for t in p["tags"]:
        params = tag_params(t, inst)
        params_rec[t] = params
        for mode in p["modes"]:
            spec = point_spec(tag_id(t), params, b["overrides"], mu=pt.mu, mode=mode, horizon_min=hz, c=c,
                              seeds=seeds, name=f"s1v2_{part}_{name}_{t}")
            for ps in seeds:
                e, model = run_tag(errors, spec, t, inst, ecfg, refs, own, c, ps, mode)
                models.setdefault(mode, e7._lender_dict(model))
                if e is None:
                    continue
                rows.append(s1._savings(e))
                a8 = e.get("a8") or {}
                print(f"[s1v2] {part} {name} c{c} {t} {mode} p{ps}: r0 {e.get('r0')}, status {e.get('status')}, "
                      f"projected {a8.get('projected_slots')}, t_a {a8.get('t_a')}, {e['wall_s']:.1f} s", flush=True)
    rec = {"meta": {"exp": EXP, "job": job.id, "part": part, "spec": SPEC, "change": CHANGE, "label": LABEL,
                    "git_revision": mc.git_revision(), "versions": mc.versions(), "written": mc._now(),
                    "reduced": reduced(), "gate": g},
           "part": part, "kind": p["kind"], "point": name, "row": pt.row or None, "value": pt.value, "label": pt.label,
           "mu": pt.mu, "c": c, "horizon_min": hz, "policy_seeds": seeds, "tags": tag_table(p["tags"]),
           "params": params_rec, "modes": list(p["modes"]), "overrides": b["overrides"],
           "instance_hash": b["instance_hash"], "instance": s1.instance_record(inst), "references": refs,
           "own_capacity_usd": own, "prices": s1.prices(inst), "vs_default": b["facts"], "lender_models": models,
           "build_s": b["build_s"], "runs": rows, "errors": errs(errors)}
    outputs.dump(e7._jsonish(rec), run_path(out, part, job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": b["instance_hash"], "bl0a_usd": refs["bl0a_usd"],
            "r0": [[r["tag"], r["mode"], r.get("r0")] for r in rows]}


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    if job.params["kind"] in ("sweep", "w0"):
        return run_cells(job, outputs, out)
    raise ValueError(f"unknown S1 v2 job {job.id!r}")


def manifest_extra(out) -> dict:
    """The instance hashes the run files record (no instance is rebuilt), the design, the gate and the sha256 of the
    driver layer and of the confirmation files read."""
    out = Path(out)
    ps = parts()
    hashes = {}
    for j in jobs(ps):
        f = mc.read_json(run_path(out, j.params["part"], j.id))
        if isinstance(f, dict):
            hashes[j.id] = f.get("instance_hash")
    files = [Path(__file__), Path(s1.__file__), Path(m5.__file__), Path(e7h.__file__), ANALYSIS_FILE,
             conf_file("main"), conf_file("main", "manifest.json"), conf_file("second")]
    return {"parts": ps, "design": {k: (list(v) if isinstance(v, tuple) else v) for k, v in design().items()},
            "instance_hashes_from_outputs": hashes, "gate_record": registration_record(),
            "sources_sha256": {_rel_repo(f): (hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None)
                               for f in files}}


def _rel_repo(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(paths.REPO))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------- summaries
def collect(out_p: Path, part: str) -> dict:
    """The rows of a part: every run of the ok jobs (brief, with point and week), the table {tag: {mode: {point: {c:
    {seed: r0}}}}} of the expected grid (null for a run missing or not ok), the missing runs and the files."""
    js = [j for j in jobs_all() if j.params["part"] == part]
    files, ok, ignored, not_ok = part_outputs(out_p, js, lambda j: run_path(out_p, part, j.id))
    rows, have = [], {}
    for jid, f in files.items():
        for e in f.get("runs") or []:
            r = brief(e, job=jid, point=f["point"], c=int(f["c"]))
            r["saving_pct"] = e.get("saving_pct")
            rows.append(r)
            have[(r["tag"], r["mode"], r["point"], r["c"], r["seed"])] = r
    table, missing = {}, []
    for j in js:
        for key in expected_runs(j):
            t, m, pt, c, s = key
            r = have.get(key)
            good = r is not None and r["status"] == "ok"
            table.setdefault(t, {}).setdefault(m, {}).setdefault(pt, {}).setdefault(num_key(c), {})[num_key(s)] = \
                r["r0"] if good else None
            if not good:
                missing.append({"job": j.id, "tag": t, "mode": m, "point": pt, "c": c, "seed": s,
                                "why": r["status"] if r is not None else not_ok.get(j.id, "run missing")})
    return {"js": js, "files": files, "ok": ok, "ignored": ignored, "not_ok": not_ok, "rows": rows, "table": table,
            "missing": missing}


def check_identity(files: Mapping, weeks, main_s: Optional[Mapping], main_m: Optional[Mapping],
                   missing: bool = False) -> dict:
    """S1v2-0: the default point's L-tr runs against part main's table (r0 within REL_TOL relative) and the instance
    hash against main's manifest (instance_hashes_from_outputs of the job e7h:main:k=week:tag=<tag>:c=<c>)."""
    out = {"claim": CHECK_CLAIMS["S1v2-0"], "tolerance": REL_TOL, "reference": f"{CONF_REL}/main/summary.json, "
                                                                                f"manifest.json"}
    ih_main = (main_m or {}).get("instance_hashes_from_outputs") or {}
    cells, bad, miss = {}, [], []
    for jid, f in files.items():
        if f.get("point") != DEFAULT:
            continue
        c = int(f["c"])
        for e in f.get("runs") or []:
            t = e["tag"]
            ref = conf_r0((main_s or {}).get("table"), t, "L-tr", num_key(c), int(e.get("policy_seed", 0)))
            hr = (ih_main.get(f"e7h:main:k=week:tag={t}:c={c}") or {}).get("base")
            d = rel_diff(e.get("r0"), ref)
            x = {"r0": e.get("r0"), "r0_main": ref, "rel_diff": d, "instance_hash": f.get("instance_hash"),
                 "instance_hash_main": hr, "hash_equal": hr is not None and hr == f.get("instance_hash")}
            cells[f"{t}:c{c}"] = x
            if ref is None or hr is None:
                miss.append(f"{t}:c{c}")
            elif d is None or d > REL_TOL or not x["hash_equal"]:
                bad.append(f"{t}:c{c}")
    want = {f"{t}:c{int(c)}" for t in TAGS for c in weeks}
    absent = sorted(want - set(cells))
    st = "fail" if bad else ("missing" if (miss or absent or missing) else "pass")
    out.update(status=st, cells=cells, failures=bad, references_missing=miss, runs_absent=absent)
    if main_s is None:
        out["note"] = "part main's summary is missing (or this is a reduced run on a development week)"
    return out


def check_built(files: Mapping, missing: bool = False) -> dict:
    """S1v2-1 (S1-1's rule on S1 v2's points and rows)."""
    bad, n = [], 0
    for jid, f in sorted(files.items()):
        name = f.get("point")
        if name == DEFAULT or name not in POINTS:
            continue
        n += 1
        v, pt = f["vs_default"], POINTS[name]
        probs = []
        if v.get("instance_equal"):
            probs.append("the instance hash equals the default's")
        if not ROWS[pt.row].gamma:
            dm = v.get("demand_matched") or {}
            if not (dm.get("identical") is True and not dm.get("only_in_point") and not dm.get("only_in_default")):
                probs.append(f"the demand differs from the default's (max abs diff {dm.get('max_abs_diff')})")
            if not v.get("bl0a_equal"):
                probs.append(f"BL0a {v.get('bl0a_usd')!r} != the default's {v.get('default_bl0a_usd')!r}")
        if v.get("llms_fitting_no_layer_site"):
            probs.append(f"LLMs fitting no layer site: {v['llms_fitting_no_layer_site']}")
        want = ["S"] if name == "sS0" else []
        if list(v.get("llms_without_clients") or []) != want:
            probs.append(f"LLMs without clients {v.get('llms_without_clients')} != {want}")
        if probs:
            bad.append({"job": jid, "point": name, "c": f.get("c"), "problems": probs})
    return {"status": status_of(bool(bad), n, missing), "claim": CHECK_CLAIMS["S1v2-1"], "n_instances": n,
            "failures": bad[:100], "n_failures": len(bad),
            "rows_without_gamma": [k for k, r in ROWS.items() if not r.gamma]}


def reused_block(second: Optional[Mapping], weeks, tags) -> dict:
    """The points read from part second (REUSED): {point: {row, value, label, mode, source, by_tag: {tag: {c: r0}}}}."""
    out = {}
    for name, v in REUSED.items():
        by = {t: {num_key(c): conf_r0((second or {}).get("table"), t, v["mode"], num_key(c)) for c in weeks}
              for t in tags}
        out[name] = {**{k: v[k] for k in ("row", "value", "label", "mode", "note")}, "part": v["part"],
                     "by_tag": by}
    return out


def summary_sweep(out_s: Path) -> dict:
    out_s = Path(out_s)
    d = design()
    col = collect(out_s, "sweep")
    files = col["files"]
    main_s, main_src = conf_source("main")
    main_m, main_m_src = conf_source("main", "manifest.json")
    second, second_src = conf_source("second")
    pts = {}
    for name, pt in POINTS.items():
        # e7.cost_entry reads A8 fields only for E7's A8 tag 'Sublet' (A8P's record has them); another tag takes an
        # unguarded E7 tag, which selects only the null A8 fields (s1.q28_entry's rule)
        by_tag = {t: e7.cost_entry([dict(r, config_seed=f["c"]) for f in files.values() if f.get("point") == name
                                    for r in f["runs"] if r["tag"] == t], t if t in e7.TAGS else "BL5")
                  for t in TAGS}
        pts[name] = {"row": pt.row or None, "value": pt.value, "label": pt.label, "mu": pt.mu,
                     "gamma_row": bool(ROWS[pt.row].gamma) if pt.row else None,
                     "n_runs_expected": len(d["weeks"]) * len(d["policy_seeds"]),
                     "bl0a_usd": {num_key(f["c"]): f["references"]["bl0a_usd"] for f in files.values()
                                  if f.get("point") == name}, "by_tag": by_tag}
    instances = {}
    for f in files.values():
        instances.setdefault(f["point"], {})[num_key(f["c"])] = {
            "instance_hash": f["instance_hash"], "bl0a_usd": f["references"]["bl0a_usd"],
            "gamma": f["instance"].get("gamma"), "n_units": f["instance"].get("n_units"), "overrides": f["overrides"]}
    missing = bool(col["not_ok"])
    re_ = run_errors_of(files)
    sub = [r for r in col["rows"] if r.get("guard")]
    checks = {"S1v2-0": check_identity(files, d["weeks"], main_s, main_m,
                                       missing=any(sweep_id(DEFAULT, c) in col["not_ok"] for c in d["weeks"])),
              "S1v2-1": check_built(files, missing),
              "S1v2-2": {"claim": CHECK_CLAIMS["S1v2-2"], **guard_check(sub, missing)},
              "S1v2-3": {"claim": CHECK_CLAIMS["S1v2-3"],
                         **clean_check(col["rows"], re_, col["missing"], col["not_ok"], missing)}}
    meta = meta_common(EXP, "sweep", SPEC, d["reduced"],
                       grids={"weeks": list(d["weeks"]), "weeks_design": list(WEEKS),
                              "policy_seeds": list(d["policy_seeds"]), "horizon_min": d["horizon_min"],
                              "horizon_min_design": m4.WEEK_MIN, "mode": "L-tr"},
                       points={n: {"row": p.row or None, "value": p.value, "label": p.label, "mu": p.mu}
                               for n, p in POINTS.items()},
                       reused_points={k: dict(v) for k, v in REUSED.items()},
                       rows={k: {"label": r.label, "panel": r.panel, "gamma": r.gamma, "default_label": r.default_label}
                             for k, r in ROWS.items()}, rows_order=list(ROWS_ORDER), tags=tag_table(TAGS),
                       h1_pair=list(H1_PAIR), instances=instances,
                       sources={"main": main_src, "main_manifest": main_m_src, "second": second_src},
                       jobs=len(col["js"]), jobs_ok=len(col["ok"]), jobs_not_ok=col["not_ok"],
                       ignored_outputs=col["ignored"], n_runs=len(col["rows"]), n_missing=len(col["missing"]))
    if d["reduced"]:
        meta["reduced_note"] = (f"reduced job list ({REDUCED_ENV}=1): week {REDUCED_WEEK}, policy seed 0, a "
                                f"{REDUCED_HORIZON_MIN}-min horizon; not a result")
    s = {"meta": meta, "runs": col["rows"], "table": col["table"], "points": pts,
         "reused": reused_block(second, d["weeks"], W0_TAGS), "missing": col["missing"],
         "not_run": [dict(x) for x in NOT_RUN], "checks": {k: checks[k] for k in CHECK_IDS_SWEEP}}
    mc.dump_json(e7._jsonish(s), out_s / "summary.json")
    mc.write_text(tables(s), out_s / "tables.md")
    return s


def summary_w0(out_w: Path) -> dict:
    out_w = Path(out_w)
    d = design()
    col = collect(out_w, "w0")
    main_s, main_src = conf_source("main")
    w0: dict = {}
    for t in W0_TAGS:
        for name in W0_POINTS:
            for c in d["w0_weeks"]:
                v, mode, miss = m5.w0_of({m: ((col["table"].get(t) or {}).get(m) or {}).get(name, {})
                                          .get(num_key(c), {}).get("0") for m in m5.stress_modes()})
                w0.setdefault(t, {}).setdefault(name, {})[num_key(c)] = {"W0": v, "mode": mode, "missing": miss}
    dflt = {t: {num_key(c): (((main_s or {}).get("W0") or {}).get("0") or {}).get(t, {}).get(num_key(c))
                for c in d["w0_weeks"]} for t in W0_TAGS}
    missing = bool(col["not_ok"])
    sub = [r for r in col["rows"] if r.get("guard")]
    checks = {"S1v2-W1": {"claim": CHECK_CLAIMS["S1v2-W1"],
                          **clean_check(col["rows"], run_errors_of(col["files"]), col["missing"], col["not_ok"],
                                        missing)},
              "S1v2-W2": {"claim": CHECK_CLAIMS["S1v2-W2"], **guard_check(sub, missing)}}
    meta = meta_common(EXP, "w0", SPEC, d["reduced"],
                       grids={"weeks": list(d["w0_weeks"]), "weeks_design": list(W0_WEEKS),
                              "policy_seeds": list(d["policy_seeds"]), "horizon_min": d["horizon_min"],
                              "modes": list(m5.stress_modes()), "points": list(W0_POINTS), "rows": list(W0_ROWS)},
                       tags=tag_table(W0_TAGS), sources={"main": main_src}, jobs=len(col["js"]),
                       jobs_ok=len(col["ok"]), jobs_not_ok=col["not_ok"], ignored_outputs=col["ignored"],
                       n_runs=len(col["rows"]), n_missing=len(col["missing"]))
    if d["reduced"]:
        meta["reduced_note"] = f"reduced job list ({REDUCED_ENV}=1): week {REDUCED_WEEK}; not a result"
    s = {"meta": meta, "runs": col["rows"], "table": col["table"], "W0": w0, "reused_default_W0": dflt,
         "missing": col["missing"], "checks": {k: checks[k] for k in CHECK_IDS_W0}}
    mc.dump_json(e7._jsonish(s), out_w / "summary.json")
    mc.write_text(tables(s), out_w / "tables.md")
    return s


def tables(s: dict) -> str:
    m = s["meta"]
    lines = [f"# S1 v2 part {m['part']} ({SPEC})", "", f"*{LABEL}*", ""]
    if m.get("reduced"):
        lines += [f"Reduced run: {m.get('reduced_note')}", ""]
    rows = [[r.get("point"), r.get("c"), r["tag"], r["mode"], r.get("r0"), r["status"],
             (r.get("guard") or {}).get("projected_slots"), (r.get("guard") or {}).get("aborted")] for r in s["runs"]]
    lines += ["## Runs (r0 = overflow cost over BL0a)", "",
              mc.md_table(["point", "week", "tag", "mode", "r0", "status", "projected", "aborted"], rows), ""]
    lines += ["## Checks", "", mc.md_table(["check", "status"], [[k, v.get("status")] for k, v in s["checks"].items()]),
              ""]
    return "\n".join(lines) + "\n"


SUMMARIES = {"sweep": summary_sweep, "w0": summary_w0}


def summary(out) -> dict:
    """The summaries of the parts of S1V2_PART (each from its own folder)."""
    return {p: SUMMARIES[p](part_dir(out, p)) for p in PARTS if p in parts()}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check-start" in args:
        return check_start(EXP, reduced())
    rc = limits_main(EXP, jobs, args)
    if rc is not None:
        return rc
    if "--out" not in args and any(x in args for x in ("--job", "--summary", "--manifest")):
        ps = parts()
        if len(ps) == 1:
            args += ["--out", str(mc.ms3_root() / "out" / EXP / ps[0])]
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=args, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
