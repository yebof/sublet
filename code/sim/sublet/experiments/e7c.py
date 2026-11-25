"""E7c: the causal-demand rerun of MS7 (design/ms7/plan.md X1, D6; change C53; design/ms7/feasibility/causal.md,
RECOMMENDED DESIGN items 1-4). Every main policy acts on the demand of slot t - 1 (e7c_tags: the 11 lag tags; the
lagged RetroRenting-style rows are main's BL5 runs), on the 16 confirmation weeks under the seven modes of
design/sublet_v2.md §4.4(a).

Parts (E7C_PART; one part per run of run_e7c.sh; gate before lag, both in the clean clone of the registration commit,
D6), outputs in <root>/out/e7c/<part>/ (jobs/, logs/, runs/ (not versioned), retry/, manifest.json, summary.json,
tables.md, run_e7c.log; ms3_common.COPY_PARTS['e7c']):
  gate  (a) the classes C53 changes, at their defaults, against the confirmation's part main bit for bit: BL1, BL2,
        BL3-0, BL4, BL5 and A9 on weeks 301-302 x the seven modes (BL5 added to the study's list: C53 changes
        Baseline, whose lagged BL5 rows the analysis reuses from main); (b) Sublet-lag, A9-lag and BL1-lag on weeks
        301-304 under L-tr against part second's runs. Every r0 must equal the reference's exactly (the versioned
        summaries code/sim/out/sublet_v2/{main,second}/summary.json of this repository, their sha256 recorded):
        24 jobs, 96 runs
  lag   the 11 lag tags x weeks 301-316 x the seven modes, policy seed 0: 176 jobs, 1,232 runs

Jobs are e7h's week jobs (one tag on one week, every mode in one process, so that A9's contract table is built once per
job), ids 'e7c:<part>:k=week:tag=<tag>:c=<c>', run by e7h.run_week with the tag module e7c_tags and this driver's meta
(the hooks of C53; e7h's own runs are unchanged); the summary is e7h.collect's rows and table with e7h's W0 table and
ms5b_common's RC (e7h.conf_tables), e7h.guard_summary overall and per tag, and for part gate the identity checks.

Gate (D6): a run refuses to start unless design/ms7/registration.md exists at HEAD, the working tree is clean
(ms5b_common.dirty_paths: untracked files under code/sim/out/ do not count) and the sha256 of e7c_analysis.py, on disk
and at HEAD, equals the one the registration records on its line 'e7c_analysis_sha256: <64 hex>'; part lag also
needs <root>/out/e7c/gate/summary.json of a full run at the same commit with every identity check passed. Every run
file and summary records this gate (kind 'ms7_registration'), never the confirmation's (ms5b_common.check_confirmation,
which e7h's confirmation parts carry). Reduced runs record it and do not enforce it.

Reduced runs (MS3_E7C_REDUCED=1, run_e7c.sh --reduced): week 101 (a development seed of bench_e7f, never a week of
§4.4) with a 2-hour horizon, the same tags and modes; part gate has no reference there, so its checks report 'no
reference' and do not pass. For smoke runs under a scratch MS3_ROOT; never a result.

Command line (ms3_common.main), run from code/sim:
  python -m sublet.experiments.e7c --list | --job ID | --summary | --estimate | --manifest  [--out DIR]
  python -m sublet.experiments.e7c --check-start          the gate of the part(s) of E7C_PART; exit 1 if refused
  python -m sublet.experiments.e7c --retry-list --out DIR  the missing-run rule's rerun (design/sublet_v2.md §4.5, as
                                                           e7h's): '<kind> <id>' of every pool job to run once more
Without --out the part's folder is the default (one part in E7C_PART).

Status labels: A9's rules HEURISTIC, no competitive ratio claimed for A9 on the full model; Sublet-lag's guarantee is
the guard's (Theorem W(a)(b) for A8P through Remark R, PROVEN, audited), its test on the realized slot.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Optional

from .. import paths
from . import e7
from . import e7c_tags as ct
from . import e7h
from . import ms3_common as mc
from . import ms5b_common as m5
from .ms3_common import Job, job_id

EXP = "e7c"
SPEC = "design/ms7/plan.md X1 (C53); design/ms7/feasibility/causal.md"
PARTS = ("gate", "lag")
REDUCED_ENV = "MS3_E7C_REDUCED"
REDUCED_HORIZON_MIN = 120
REDUCED_WEEK = 101
CONF_WEEKS = m5.CONF_WEEKS                                     # 301-316
GATE_DEFAULT_TAGS = ("BL1", "BL2", "BL3-0", "BL4", "BL5", "A9")
GATE_DEFAULT_WEEKS = (301, 302)
GATE_LAG_TAGS = ct.SHARED                                      # Sublet-lag, A9-lag, BL1-lag
GATE_LAG_WEEKS = (301, 302, 303, 304)
GATE_LAG_MODES = (m5.TRACE_MODE,)
GATE_REF = {"a": "main", "b": "second"}                        # out/sublet_v2/<part>/summary.json
# the registration (D6): design/ms7/registration.md records the analysis script's sha256 on this line
REGISTRATION = "design/ms7/registration.md"
ANALYSIS = Path(__file__).resolve().parent / "e7c_analysis.py"
ANALYSIS_REL = "code/sim/sublet/experiments/e7c_analysis.py"
REG_SHA_RE = re.compile(r"^e7c_analysis_sha256:\s*([0-9a-f]{64})\s*$", re.MULTILINE)
SOURCES = ("sublet/experiments/e7c.py", "sublet/experiments/e7c_tags.py", "sublet/experiments/e7c_analysis.py",
           "sublet/experiments/e7h.py", "sublet/experiments/ms5b_common.py", "sublet/baselines/common.py",
           "sublet/baselines/greedy.py", "sublet/baselines/ski.py", "sublet/baselines/spothedge.py",
           "sublet/baselines/cocar.py", "sublet/baselines/retrorenting.py", "sublet/algos/a9.py",
           "sublet/algos/guard.py", "sublet/algos/online_lb.py")


# ---------------------------------------------------------------- settings and parts
def design() -> dict:
    red = os.environ.get(REDUCED_ENV, "0") == "1"
    return {"reduced": red, "horizon_min": REDUCED_HORIZON_MIN if red else m5.WEEK_MIN}


def parts() -> list:
    v = os.environ.get("E7C_PART", "")
    ps = [p for p in v.replace(",", " ").split() if p]
    bad = [p for p in ps if p not in PARTS]
    if bad:
        raise ValueError(f"E7C_PART must name parts of {list(PARTS)}, got {v!r}")
    return ps or list(PARTS)


def part_dir(part: str, root=None) -> Path:
    """<root>/out/e7c/<part> (root as ms3_common.ms3_root)."""
    return mc.ms3_root(root) / "out" / EXP / part


# ---------------------------------------------------------------- job lists
def _est_week(t: str, n_runs: int, hz: int) -> float:
    """e7h's estimate of a week job (seconds): job overhead, A9's contract table for an A9-family tag, and the runs at
    e7h.EST_WEEK_S of the registry id, scaled to the horizon."""
    tg = ct.tag(t)
    return e7h.EST_JOB_S + (e7h.EST_TABLE_S if tg.a9_family else 0.0) + \
        n_runs * e7h.EST_WEEK_S.get(tg.id, 20.0) * hz / m5.WEEK_MIN


def _weeks(part: str, tags, weeks, modes, seeds, hz: int) -> list:
    out = []
    for c in weeks:
        for t in tags:
            ct.tag(t)
            out.append(Job(job_id(EXP, part, k="week", tag=t, c=int(c)), "pool",
                           {"part": part, "kind": "week", "tag": t, "c": int(c), "modes": list(modes),
                            "policy_seeds": [int(s) for s in seeds], "horizon_min": int(hz)},
                           _est_week(t, len(modes) * len(seeds), hz)))
    return out


def jobs(ps=None) -> list:
    """The jobs of the parts `ps` (default: E7C_PART) in run order (module docstring)."""
    ps = parts() if ps is None else list(ps)
    d = design()
    red, hz = d["reduced"], d["horizon_min"]
    out: list = []
    for part in ps:
        if part == "gate":
            out += _weeks(part, GATE_DEFAULT_TAGS, (REDUCED_WEEK,) if red else GATE_DEFAULT_WEEKS, m5.conf_modes(),
                          (0,), hz)
            out += _weeks(part, GATE_LAG_TAGS, (REDUCED_WEEK,) if red else GATE_LAG_WEEKS, GATE_LAG_MODES, (0,), hz)
        elif part == "lag":
            out += _weeks(part, ct.LAG_TAGS, (REDUCED_WEEK,) if red else CONF_WEEKS, m5.conf_modes(), (0,), hz)
        else:
            raise ValueError(f"unknown E7c part {part!r}")
    return out


def jobs_all() -> list:
    return jobs(list(PARTS))


# ---------------------------------------------------------------- the gate (D6)
_GATE: dict = {}


def analysis_sha256() -> Optional[str]:
    return m5._sha(ANALYSIS.read_bytes()) if ANALYSIS.is_file() else None


def registered_sha256(text: Optional[str]) -> Optional[str]:
    """The analysis script's sha256 that the registration records (its line 'e7c_analysis_sha256: <64 hex>')."""
    if not text:
        return None
    m = REG_SHA_RE.search(text)
    return m.group(1) if m else None


def registration_record() -> dict:
    """The gate's facts: HEAD, whether design/ms7/registration.md exists at HEAD and the analysis sha256 it records,
    the sha256 of e7c_analysis.py at HEAD and on disk, and the dirty paths (ms5b_common's read-only git helpers)."""
    reg = m5.file_at("HEAD", REGISTRATION)
    return {"head": m5.head_commit(), "registration": REGISTRATION, "registration_at_head": reg is not None,
            "registration_sha256": m5._sha(reg),
            "analysis_sha256_registered": registered_sha256(None if reg is None else reg.decode("utf-8", "replace")),
            "analysis_sha256_head": m5._sha(m5.file_at("HEAD", ANALYSIS_REL)),
            "analysis_sha256_disk": analysis_sha256(), "dirty_paths": m5.dirty_paths()}


def check_registration(rec: Optional[dict] = None) -> tuple[bool, str, dict]:
    """(ok, reason, record): an E7c part runs only if design/ms7/registration.md exists at HEAD, the working tree is
    clean and the sha256 of e7c_analysis.py (on disk and at HEAD) equals the registered one (D6)."""
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
        why.append(f"{REGISTRATION} records no line 'e7c_analysis_sha256: <64 hex>'")
    for k in ("analysis_sha256_disk", "analysis_sha256_head"):
        if want is not None and rec.get(k) != want:
            why.append(f"{k} {str(rec.get(k))[:12]} differs from the registration's {want[:12]}")
    if why:
        return False, "E7c does not start (D6): " + "; ".join(why), rec
    return True, "registration at HEAD, clean tree, analysis sha256 as registered", rec


def gate_part_record(root=None) -> dict:
    """Part gate's outcome as part lag's gate reads it: <root>/out/e7c/gate/summary.json's reduced flag, git revision
    and decision (pass, counts)."""
    f = part_dir("gate", root) / "summary.json"
    s = mc.read_json(f)
    if not isinstance(s, dict):
        return {"summary": str(f), "exists": False}
    d, meta = s.get("decision") or {}, s.get("meta") or {}
    return {"summary": str(f), "exists": True, "reduced": meta.get("reduced"), "git_revision": meta.get("git_revision"),
            "pass": d.get("pass"), "n_checks": d.get("n_checks"), "n_equal": d.get("n_equal")}


def check_gate_part(rec: dict, head: Optional[str]) -> tuple[bool, str]:
    """(ok, reason): part lag starts only after a full run of part gate at commit `head` passed every check."""
    if not rec.get("exists"):
        return False, f"part gate has no summary ({rec.get('summary')})"
    why = []
    if rec.get("reduced") is not False:
        why.append("part gate's summary is a reduced run")
    if head is None or rec.get("git_revision") != head:
        why.append(f"part gate ran at {str(rec.get('git_revision'))[:12]}, not at HEAD {str(head)[:12]}")
    if rec.get("pass") is not True:
        why.append(f"part gate's identity checks did not pass ({rec.get('n_equal')} of {rec.get('n_checks')} equal)")
    return (False, "; ".join(why)) if why else (True, "part gate passed at HEAD")


def gate(part: str) -> dict:
    """The gate of a part, checked once per process (module docstring); raises RuntimeError when refused in a full
    run. Reduced runs record it without enforcing it."""
    if part not in _GATE:
        red = design()["reduced"]
        ok, why, rec = check_registration()
        g = {"kind": "ms7_registration", "ok": ok, "reason": why, "enforced": not red, "registration": rec}
        if part == "lag":
            gp = gate_part_record()
            ok2, why2 = check_gate_part(gp, rec.get("head"))
            g["gate_part"] = {**gp, "ok": ok2, "reason": why2}
            if not ok2:
                g["ok"] = False
                g["reason"] = (why + "; " if not ok else "E7c does not start (D6): ") + why2
        if red:
            g["note"] = "reduced run on a development week: the gate is recorded, not enforced"
        _GATE[part] = g
    g = _GATE[part]
    if g["enforced"] and not g["ok"]:
        raise RuntimeError(g["reason"])
    return g


def _meta_run(job: Job) -> dict:
    part = job.params["part"]
    return {"exp": EXP, "job": job.id, "part": part, "spec": SPEC, "git_revision": mc.git_revision(),
            "versions": mc.versions(), "written": mc._now(), "reduced": design()["reduced"], "gate": gate(part)}


# ---------------------------------------------------------------- jobs
def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One week job through e7h.run_week with the E7c tags and this driver's meta (C53)."""
    gate(job.params["part"])
    if job.params["kind"] != "week":
        raise ValueError(f"E7c has week jobs only, not {job.params['kind']!r}")
    return e7h.run_week(job, outputs, out, tags=ct, meta_of=_meta_run)


# ---------------------------------------------------------------- part gate: the identity checks
def reference_tables() -> dict:
    """{'a': main's table, 'b': second's table} from this repository's versioned confirmation summaries, with their
    paths and sha256 (None where a file is missing)."""
    out = {}
    for k, part in GATE_REF.items():
        f = paths.SIM_OUT / m5.CONF_DIR / part / "summary.json"
        s = mc.read_json(f) if f.is_file() else None
        out[k] = {"part": part, "path": str(f.relative_to(paths.REPO)) if f.is_absolute() else str(f),
                  "sha256": m5._sha(f.read_bytes()) if f.is_file() else None,
                  "table": (s or {}).get("table") if isinstance(s, dict) else None}
    return out


def identity_checks(table: dict, refs: dict, reduced: Optional[bool] = None) -> dict:
    """Part gate's checks (module docstring): per (check, tag, mode, week) the r0 of this part against the reference
    part's, equal iff both exist and are the same float; pass iff every check has a reference and every r0 equals it.
    `refs` as reference_tables() returns it; `reduced` (default: design()) selects the cells."""
    d = design() if reduced is None else {"reduced": reduced}
    wa = (REDUCED_WEEK,) if d["reduced"] else GATE_DEFAULT_WEEKS
    wb = (REDUCED_WEEK,) if d["reduced"] else GATE_LAG_WEEKS
    rows = []
    for chk, tags, weeks, modes in (("a", GATE_DEFAULT_TAGS, wa, m5.conf_modes()), ("b", GATE_LAG_TAGS, wb,
                                                                                 GATE_LAG_MODES)):
        ref = (refs.get(chk) or {}).get("table")
        for t in tags:
            for w in weeks:
                for m in modes:
                    got = e7h._val(table, t, m, mc.num_key(w))
                    want = None if ref is None else e7h._val(ref, t, m, mc.num_key(w))
                    rows.append({"check": chk, "ref_part": GATE_REF[chk], "tag": t, "mode": m, "cell": mc.num_key(w),
                                 "r0": got, "reference": want,
                                 "equal": got is not None and want is not None and got == want,
                                 "diff": None if got is None or want is None else float(got) - float(want)})
    n = len(rows)
    no_ref = sum(1 for r in rows if r["reference"] is None)
    missing = sum(1 for r in rows if r["r0"] is None)
    equal = sum(1 for r in rows if r["equal"])
    diffs = [abs(r["diff"]) for r in rows if r["diff"] is not None]
    out = {"pass": bool(n) and equal == n, "n_checks": n, "n_equal": equal,
           "n_differ": sum(1 for r in rows if r["diff"] is not None and not r["equal"]), "n_missing_run": missing,
           "n_no_reference": no_ref, "max_abs_diff": max(diffs) if diffs else None,
           "references": {k: {kk: v.get(kk) for kk in ("part", "path", "sha256")} for k, v in refs.items()},
           "rule": "every r0 equal to the reference's exactly (a: main at the defaults; b: second's lagged runs)",
           "rows": rows}
    if d["reduced"]:
        out["note"] = "reduced run on a development week: the confirmation has no reference there"
    return out


# ---------------------------------------------------------------- summaries
def _meta(part: str, js: list, col: dict) -> dict:
    d = design()
    tags = sorted({t for j in js for t, *_ in e7h.expected_runs(j)})
    ok, why, rec = check_registration()
    m = {"exp": EXP, "part": part, "spec": SPEC, "git_revision": mc.git_revision(), "versions": mc.versions(),
         "written": mc._now(), "reduced": d["reduced"], "design": d, "tags": ct.tag_table(tags), "jobs": len(js),
         "jobs_ok": len(col["files"]), "jobs_not_ok": col["not_ok"], "ignored_outputs": col["ignored"],
         "n_runs": len(col["rows"]), "n_missing": len(col["missing"]),
         "gate": {"kind": "ms7_registration", "ok": ok, "reason": why, "record": rec}}
    if d["reduced"]:
        m["reduced_note"] = f"reduced job list ({REDUCED_ENV}=1): development week {REDUCED_WEEK} only; not a result"
    return m


def summary_part(part: str, out_p: Path) -> dict:
    out_p = Path(out_p)
    js = [j for j in jobs_all() if j.params["part"] == part]
    col = e7h.collect(out_p, js)
    by_tag = sorted({g["tag"] for g in col["guarded"]})
    s = {"meta": _meta(part, js, col), "runs": col["rows"], "table": col["table"], "missing": col["missing"],
         "guarded": col["guarded"], "guard_summary": e7h.guard_summary(col["guarded"]),
         "guard_by_tag": {t: e7h.guard_summary([g for g in col["guarded"] if g["tag"] == t]) for t in by_tag}}
    s.update(e7h.conf_tables(col, part))
    if part == "gate":
        s["decision"] = identity_checks(col["table"], reference_tables(), design()["reduced"])
    mc.dump_json(e7._jsonish(s), out_p / "summary.json")
    mc.write_text(tables(s), out_p / "tables.md")
    return s


def tables(s: dict) -> str:
    """tables.md: the r0 of every run, the missing runs, the guarded runs and, for part gate, the identity checks."""
    m = s["meta"]
    lines = [f"# E7c part {m['part']} ({SPEC})", ""]
    if m.get("reduced"):
        lines += [f"Reduced run: {m.get('reduced_note')}", ""]
    rows = [[r["tag"], r["mode"], r["cell"], r["seed"], r.get("r0"), r["status"],
             (r.get("guard") or {}).get("projected_slots"), (r.get("guard") or {}).get("aborted")] for r in s["runs"]]
    lines += ["## Runs (r0 = cost over BL0a)", "",
              mc.md_table(["tag", "mode", "cell", "seed", "r0", "status", "projected", "aborted"], rows), ""]
    lines += ["## Missing runs", "", mc.md_table(["job", "tag", "mode", "cell", "seed", "why"],
                                                 [[x["job"], x["tag"], x["mode"], x["cell"], x["seed"], x["why"]]
                                                  for x in s["missing"]]), ""]
    g = s["guard_summary"]
    lines += ["## Guarded runs", "", mc.md_table(["runs", "held", "envelope violations", "aborts", "projected slots",
                                                  "runs projected", "K0"],
                                                 [[g["n_runs"], g["held"], g["n_envelope_violations"], g["aborts"],
                                                   g["projected_slots"], g["runs_projected"], g["K0"]]]), ""]
    d = s.get("decision")
    if d:
        lines += [f"## Identity checks (pass {d['pass']}: {d['n_equal']} of {d['n_checks']} equal, "
                  f"{d['n_no_reference']} without a reference, {d['n_missing_run']} runs missing)", "",
                  mc.md_table(["check", "ref", "tag", "mode", "cell", "r0", "reference", "equal"],
                              [[r["check"], r["ref_part"], r["tag"], r["mode"], r["cell"], r["r0"], r["reference"],
                                r["equal"]] for r in d["rows"]]), ""]
    return "\n".join(lines) + "\n"


def summary(out) -> dict:
    """The summary of the part whose folder `out` is (its name), else of the one part of E7C_PART."""
    out = Path(out)
    part = out.name if out.name in PARTS else None
    if part is None:
        ps = parts()
        if len(ps) != 1:
            raise ValueError(f"--summary needs one part (E7C_PART) or a part's folder, got {out}")
        part = ps[0]
    return summary_part(part, out)


def manifest_extra(out) -> dict:
    """The job grid's design, the instance hashes the run files record (no instance is rebuilt), the sha256 of the
    sources C53 runs on and the gate as the manifest's process sees it (recorded, not enforced)."""
    out = Path(out)
    part = out.name if out.name in PARTS else (parts()[0] if len(parts()) == 1 else None)
    js = [j for j in jobs_all() if part is None or j.params["part"] == part]
    hashes = {}
    for j in js:
        f = mc.read_json(e7h.run_path(out, j.id))
        if isinstance(f, dict) and isinstance(f.get("instances"), dict):
            hashes[j.id] = {k: v.get("instance_hash") for k, v in f["instances"].items() if isinstance(v, dict)}
    src = {}
    for rel in SOURCES:
        f = paths.SIM / rel
        src[str(f.relative_to(paths.REPO))] = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
    ok, why, rec = check_registration()
    return {"part": part, "design": design(), "instance_hashes_from_outputs": hashes, "sources_sha256": src,
            "gate": {"kind": "ms7_registration", "ok": ok, "reason": why, "record": rec}}


# ---------------------------------------------------------------- the missing-run rule's rerun
def retry_list(out) -> list:
    """e7h.retry_list's rule for E7c's pool jobs of the part whose folder `out` is: a record not 'ok', or 'ok' with a
    run that raised or failed an invariant, is moved to retry/ (its output to runs/retry/) and the job listed once;
    a job with a record in retry/ is not listed again, a job without a record is left to the next run."""
    out = Path(out)
    part = out.name if out.name in PARTS else parts()[0]
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
        path = e7h.run_path(out, j.id)
        bad = rec.get("status") != "ok" or int(rec.get("n_errors") or 0) > 0
        if not bad:
            f = mc.read_json(path) or {}
            bad = any(m5.run_status(e) == "invariant_failure" or e.get("status") == "invariant_failure"
                      for e in f.get("runs") or [])
        if not bad:
            continue
        old.parent.mkdir(parents=True, exist_ok=True)
        mc.dump_json({"job": j.id, "first_record": rec, "moved": mc._now(), "rule": "design/sublet_v2.md §4.5"}, old)
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
        rc = 0
        for part in parts():
            try:
                g = gate(part)
                print(f"[e7c] {part}: gate {g['kind']} {'ok' if g['ok'] else 'REFUSED (not enforced)'}: {g['reason']}")
            except RuntimeError as err:
                print(f"[e7c] {part}: REFUSED: {err}", file=sys.stderr)
                rc = 1
        return rc
    if "--retry-list" in args:
        ap = argparse.ArgumentParser(prog="python -m sublet.experiments.e7c --retry-list")
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
