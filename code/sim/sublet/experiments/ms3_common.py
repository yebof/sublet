"""Shared MS3 driver layer (design/sim_spec_ms3.md §2.4-§2.6, §0 items 2-3; open choices M3, M4, M13, M43-M45).

Job ids, the command line of every MS3 driver, job records with resume, the slot count of the host-wide slot
semaphore (ms3_lib.sh), the MILP wall-clock limit, Q39's lower-bound rule with the brackets of a ratio of two
benchmarks, aggregation and the output conventions.

An MS3 driver sublet/experiments/<exp>.py defines its jobs (a list of `Job`), a function that runs one job and
a summary, and calls `main(...)`, which gives it the command line of §2.4:

  python -m sublet.experiments.<exp> --list                  '<pool|alone|milp> <job id>' per line
  python -m sublet.experiments.<exp> --job ID [--out DIR]    run one job; record out/<exp>/jobs/<id>.json
  python -m sublet.experiments.<exp> --summary [--out DIR]   the summary from the job outputs (record
                                                             jobs/<exp>__summary.json; never skipped)
  python -m sublet.experiments.<exp> --estimate [--workers N]  the jobs with estimated times; runs nothing
  python -m sublet.experiments.<exp> --manifest [--out DIR]  manifest.json (§2.6; record jobs/<exp>__manifest.json;
                                                             never skipped)

Its run script run_<exp>.sh sources ms3_lib.sh (the slot semaphore and the launcher), which uses this module's
own command line:

  python -m sublet.experiments.ms3_common --max-workers [--root DIR]     N: min(MS3_WORKERS, MS3_HOST_SLOTS), or 0 while
                                                                         <root>/out/e11/summary.json is missing
  python -m sublet.experiments.ms3_common --record-failure ID --out DIR --exit-code RC [--elapsed S]
                                          [--peak-kb KB] [--limit S] [--slots NAMES]
  python -m sublet.experiments.ms3_common --job-file ID                  the record's file name

and, once after E11's copy and before the first MS3 run script (§3.2 step 1), check E11-0 (§3.3):

  python -m sublet.experiments.ms3_common --check-e11 CLONE_E11 [--root DIR] [--report FILE]
      compares <root>/out/e11 with CLONE_E11 (the clone's code/sim/out/e11/), writes <root>/out/ms3_e11_0.json
      (or FILE) and exits 1 if the check fails, 2 if it cannot run (a folder missing)

and, once per experiment after its run script has finished in the clean clone of the MS3 runs and its out/<exp>/
has been copied into this repository (§1.2, "Where the runs run"), the copy check:

  python -m sublet.experiments.ms3_common --check-copy EXP CLONE [--root DIR] [--report FILE]
      compares <root>/out/<exp> (for e6 the folder out/e6 with its parts a and b) with CLONE/code/sim/out/<exp>
      (CLONE the clone's repository root, the folder with .git), writes <root>/out/ms3_copy_<exp>.json (or FILE)
      and exits 1 if the check fails, 2 if it cannot run (a folder missing, no commit in CLONE/.git)

Job records (§2.4, §0 item 2). `status` is one of
  running     the job started and has not finished (or was killed before it could say so);
  ok          the job function returned; errors of single runs are listed under `errors` (the job goes on
              after an error of one run, as q44_study.run_cells);
  error       the job function raised (recorded by the job itself);
  failed      the process exited nonzero, or zero without an 'ok' record, and no rule below applies;
  oom_at_3G   killed by the 3G cap (exit 137 of a job without `timeout`, or of a MILP job before LIMIT + 60 s);
              never retried at a larger cap;
  wall_limit  a MILP job stopped by the hard wall-clock limit (exit 124, or exit 137 at LIMIT + 60 s or later).
With MS3_RESUME=1 (M43) a job whose record says 'ok' is skipped. A job writes its outputs to <path>.partial
files (JobOutputs) that are renamed when the job function returns, so a killed job leaves no half-written
output.

Environment: MS3_WORKERS (default 4, at most 4), MS3_RESUME, MS3_MILP_LIMIT (HiGHS's time_limit_s, default 300;
ms3_lib.sh exports the value its `timeout` uses), MS3_SLOTS (the lock files a job holds, set by ms3_lib.sh),
MS3_ROOT (tests only: a folder with the layout of code/sim/out under <root>/out instead of this repository's
code/sim).

Importing this module loads only the standard library and sublet.paths; numpy, the drivers and q44_study are
imported inside the functions that need them, so the semaphore's polls (--max-workers) start fast.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import os
import re
import resource
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from .. import paths

# ---------------------------------------------------------------- constants (§0 items 2-3, §2.4, §2.5, M3, M44)
MAX_SLOTS = 4                  # MS3 jobs on the host at once (processes of an all-slot job counted)
HOST_SLOTS_MAX = 6             # MS7 C57: MS3_HOST_SLOTS raises the host's slots up to its 6 physical cores
MILP_SLOTS = 2                 # of which MILP jobs
MILP_LIMIT_S = 300             # M3: HiGHS's own time_limit_s
WALL_GRACE_S = 60              # the script's `timeout` fires at LIMIT + 60 s (SIGTERM) ...
KILL_AFTER_S = 30              # ... and sends SIGKILL 30 s later (timeout -k 30)
EXACT_GAP = 1e-4               # a MILP with gap <= 1e-4 counts as exact (§2.5)
JOB_KINDS = ("pool", "alone", "milp")
STATUSES = ("running", "ok", "error", "failed", "oom_at_3G", "wall_limit")
E11_SUMMARY = Path("out") / "e11" / "summary.json"      # relative to the root (this repository's code/sim)
SLOTS_DIR = Path("out") / ".ms3_slots"
PARTIAL = ".partial"
_ID_SEP = re.compile(r"[:=\s]")


# ---------------------------------------------------------------- roots, workers, limits
def ms3_root(root=None) -> Path:
    """The folder whose out/ holds the MS3 outputs, the slot lock files and E11's copy: `root`, else MS3_ROOT
    (tests only), else this repository's code/sim (never E11's clone, §3.2)."""
    r = root if root is not None else (os.environ.get("MS3_ROOT") or paths.SIM)
    return Path(r).resolve()


def slots_dir(root=None) -> Path:
    return ms3_root(root) / SLOTS_DIR


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {v!r}") from None


def host_slots() -> int:
    """The slots of the host-wide semaphore: MS3_HOST_SLOTS (MS7 addition C57, design/ms7/registration.md §5), an
    integer in 1..HOST_SLOTS_MAX, default MAX_SLOTS = 4 (§2.4, M44). ms3_lib.sh reads the same variable. It sets
    only how many jobs run at once; every job and run file is the same whatever its value."""
    v = _env_int("MS3_HOST_SLOTS", MAX_SLOTS)
    if not 1 <= v <= HOST_SLOTS_MAX:
        raise ValueError(f"MS3_HOST_SLOTS must be in 1..{HOST_SLOTS_MAX}, got {v}")
    return v


def max_workers(root=None) -> int:
    """N of the slot semaphore (§2.4, M44): min(MS3_WORKERS, host_slots()) (default host_slots(), which is 4 unless
    MS3_HOST_SLOTS is set; at least 0) if <root>/out/e11/summary.json exists, else 0 (no MS3 job runs before E11
    has been copied, §3.2)."""
    if not (ms3_root(root) / E11_SUMMARY).is_file():
        return 0
    n = host_slots()
    return max(0, min(_env_int("MS3_WORKERS", n), n))


def milp_limit_s() -> int:
    """HiGHS's time_limit_s for every MS3 MILP (M3): MS3_MILP_LIMIT, default 300 s; ms3_lib.sh runs the job
    under `timeout --foreground -k 30 (LIMIT + 60)` with the same value."""
    v = _env_int("MS3_MILP_LIMIT", MILP_LIMIT_S)
    if v < 1:
        raise ValueError(f"MS3_MILP_LIMIT must be a positive number of seconds, got {v}")
    return v


def wall_timeout_s(limit_s: Optional[float] = None) -> float:
    """The duration of the script's `timeout` for a MILP job: LIMIT + 60 s (§2.5)."""
    return float(milp_limit_s() if limit_s is None else limit_s) + WALL_GRACE_S


# ---------------------------------------------------------------- job ids (§2.4)
def num_key(x, strict: bool = True) -> str:
    """A number as a key in job ids and JSON paths: format(float(x), "g") ("1.5", "16", "1", "0.2"). With
    strict=True a value that the key does not give back exactly (e.g. 1/3, 1234567) raises ValueError, so that
    two grid values never share a key."""
    if isinstance(x, bool):
        raise TypeError(f"num_key: a bool is not a number key ({x!r})")
    v = float(x)
    if not math.isfinite(v):
        raise ValueError(f"num_key: non-finite value {x!r}")
    s = format(v, "g")
    if strict and float(s) != v:
        raise ValueError(f"num_key: {x!r} is not given back by its key {s!r}; round it first or pass strict=False")
    return s


def _id_part(v) -> str:
    s = num_key(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)
    if not s or _ID_SEP.search(s):
        raise ValueError(f"job id part {s!r} is empty or contains ':', '=' or white space")
    return s


def job_id(exp: str, part: str, **kv) -> str:
    """'<exp>:<part>:<key>=<value>:...' in the order given; numbers as num_key (§2.4), e.g.
    job_id("e1", "cell", sched="adaptive", rho=4, mu=1, c=2) == "e1:cell:sched=adaptive:rho=4:mu=1:c=2"."""
    out = [_id_part(exp), _id_part(part)]
    for k, v in kv.items():
        out.append(f"{_id_part(k)}={_id_part(v)}")
    return ":".join(out)


def parse_job_id(jid: str) -> tuple[str, str, dict]:
    """(exp, part, {key: value string}) of a job id written by job_id."""
    parts = jid.split(":")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(f"not an MS3 job id: {jid!r}")
    kv = {}
    for p in parts[2:]:
        k, sep, v = p.partition("=")
        if not sep or not k or k in kv:
            raise ValueError(f"not an MS3 job id: {jid!r} (part {p!r})")
        kv[k] = v
    return parts[0], parts[1], kv


def job_file_name(jid: str) -> str:
    """The record's file name: q44_study.job_file_name (runs of characters other than letters, digits, '_', '.'
    and '-' become '__'), mirrored by ms3_lib.sh's ms3_job_name."""
    from .q44_study import job_file_name as f
    return f(jid)


@dataclass(frozen=True)
class Job:
    """One MS3 job: id, kind ('pool', 'alone': runs with every slot, 'milp': under the hard wall-clock limit and
    one of the two MILP slots), parameters (for the manifest and the driver) and the estimated wall time in
    seconds (constants of §11.1; None if unknown)."""
    id: str
    kind: str = "pool"
    params: Mapping[str, Any] = field(default_factory=dict)
    est_s: Optional[float] = None

    def __post_init__(self):
        if self.kind not in JOB_KINDS:
            raise ValueError(f"job {self.id!r}: kind must be one of {JOB_KINDS}, got {self.kind!r}")
        parse_job_id(self.id)


def check_jobs(jobs: Sequence[Job]) -> None:
    """Raise ValueError on duplicate job ids or two ids that share a record file."""
    from collections import Counter
    dup = sorted(i for i, c in Counter(j.id for j in jobs).items() if c > 1)
    if dup:
        raise ValueError(f"duplicate job ids: {dup[:5]}")
    names = {}
    for j in jobs:
        n = job_file_name(j.id)
        if n in names:
            raise ValueError(f"jobs {names[n]!r} and {j.id!r} share the record file {n}")
        names[n] = j.id


# ---------------------------------------------------------------- JSON output conventions (§2.6)
def _json_key(k, where: str) -> str:
    """A dict key as a JSON key: a string as it is, a number (int, float or numpy number; not a bool) as num_key
    (§2.4: format(float(x), "g"), so a grid value 16.0 is the key "16" of the JSON paths the figure scripts read);
    any other key type raises TypeError."""
    if isinstance(k, str):
        return k
    if not isinstance(k, bool) and type(k).__module__ == "numpy" and hasattr(k, "item"):
        k = k.item()                   # numpy scalar to a Python number (np.bool_ to bool, rejected below)
    if isinstance(k, (int, float)) and not isinstance(k, bool):
        try:
            return num_key(k)
        except ValueError as err:
            raise ValueError(f"key {k!r} at {where}: {err}") from None
    raise TypeError(f"key {k!r} of type {type(k).__name__} at {where}: JSON keys are strings or numbers (§2.4)")


def jsonable(x, where: str = "$"):
    """Plain JSON values (numpy arrays and scalars to lists and Python numbers, tuples to lists, Paths to
    strings; dict keys by _json_key: numbers as num_key, e.g. {16.0: x} -> {"16": x}; two keys that give the
    same string raise ValueError). A non-finite float raises ValueError: §2.6 writes a missing value as null
    with a '*_note' key (see `put`), never as NaN or a string."""
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            s = _json_key(k, where)
            if s in out:
                raise ValueError(f"keys at {where}: two keys give the JSON key {s!r} (the second is {k!r})")
            out[s] = jsonable(v, f"{where}.{s}")
        return out
    if isinstance(x, (list, tuple)):
        return [jsonable(v, f"{where}[{i}]") for i, v in enumerate(x)]
    if isinstance(x, Path):
        return str(x)
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return x
    if isinstance(x, int):
        return int(x)
    if isinstance(x, float):
        if not math.isfinite(x):
            raise ValueError(f"non-finite value {x!r} at {where}: write null with a '*_note' key (§2.6)")
        return float(x)
    tname = type(x).__module__
    if tname == "numpy":
        import numpy as np
        if isinstance(x, np.ndarray):
            return jsonable(x.tolist(), where)
        if isinstance(x, np.bool_):
            return bool(x)
        if isinstance(x, np.integer):
            return int(x)
        if isinstance(x, np.floating):
            return jsonable(float(x), where)
    if hasattr(x, "tolist"):
        return jsonable(x.tolist(), where)
    raise TypeError(f"not JSON-serializable at {where}: {type(x).__name__}")


def put(d: dict, key: str, value, note: Optional[str] = None) -> dict:
    """d[key] = value; a None or non-finite value is written as null with d[key + '_note'] = note (§2.6)."""
    missing = value is None or (isinstance(value, float) and not math.isfinite(value))
    if missing:
        d[key] = None
        d[f"{key}_note"] = note or ("not finite" if value is not None else "missing")
    else:
        d[key] = value
    return d


def _json_text(obj, compact: bool) -> str:
    js = jsonable(obj)
    if compact:
        return json.dumps(js, separators=(",", ":"), allow_nan=False) + "\n"
    return json.dumps(js, indent=1, allow_nan=False) + "\n"


def partial_path(path) -> Path:
    p = Path(path)
    return p.with_name(p.name + PARTIAL)


def dump_json(obj, path, compact: bool = False) -> Path:
    """Write obj as JSON (allow_nan=False) to <path>.partial and rename it to <path>."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = partial_path(p)
    tmp.write_text(_json_text(obj, compact))
    os.replace(tmp, p)
    return p


def write_text(text: str, path) -> Path:
    """Write text to <path>.partial and rename it to <path>."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = partial_path(p)
    tmp.write_text(text)
    os.replace(tmp, p)
    return p


def read_json(path) -> Optional[dict]:
    p = Path(path)
    try:
        return json.loads(p.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def stale_partials(root) -> list[Path]:
    """The *.partial files under `root` (left by killed jobs; a rerun overwrites them)."""
    r = Path(root)
    return sorted(r.rglob(f"*{PARTIAL}")) if r.is_dir() else []


class JobOutputs:
    """The outputs of one job (§2.4): each is written to <path>.partial and `commit()` renames them all to their
    final names when the job function has returned, so that a killed or failed job leaves no half-written
    output. `partial(path)` registers a path and returns the partial file to write (for writers such as
    metrics.write_run); `dump` and `write_text` write JSON or text there."""

    def __init__(self):
        self._final: list[Path] = []

    def partial(self, path) -> Path:
        p = Path(path).resolve()
        if p in self._final:
            raise ValueError(f"output {p} registered twice")
        p.parent.mkdir(parents=True, exist_ok=True)
        self._final.append(p)
        return partial_path(p)

    def dump(self, obj, path, compact: bool = False) -> Path:
        tmp = self.partial(path)
        tmp.write_text(_json_text(obj, compact))
        return tmp

    def write_text(self, text: str, path) -> Path:
        tmp = self.partial(path)
        tmp.write_text(text)
        return tmp

    @property
    def paths(self) -> list[Path]:
        return list(self._final)

    def commit(self) -> list[Path]:
        missing = [str(partial_path(p)) for p in self._final if not partial_path(p).is_file()]
        if missing:
            raise FileNotFoundError(f"registered outputs never written: {missing[:5]}")
        for p in self._final:
            os.replace(partial_path(p), p)
        return list(self._final)

    def discard(self) -> None:
        for p in self._final:
            q = partial_path(p)
            if q.is_file():
                q.unlink()


def md_table(header: Sequence[str], rows: Iterable[Sequence], digits: int = 4) -> str:
    """A markdown table (tables.md); floats to `digits` significant digits, None as '–'."""
    def cell(v):
        if v is None:
            return "–"
        if isinstance(v, float):
            return f"{v:.{digits}g}"
        return str(v).replace("|", "\\|")
    lines = ["| " + " | ".join(map(str, header)) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- provenance (reused from metrics / q44_study)
def git_revision() -> Optional[str]:
    from ..metrics import _git_revision
    try:
        return _git_revision()
    except Exception:          # informative only
        return None


def versions() -> dict:
    from ..metrics import _versions
    return _versions()


def instance_hash(inst) -> str:
    """q44_study.instance_hash (every Instance field except name, config, seed and notes), for manifests."""
    from .q44_study import instance_hash as h
    return h(inst)


def schedule_hash(sched) -> str:
    from .q44_study import schedule_hash as h
    return h(sched)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _peak_rss_kb() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


# ---------------------------------------------------------------- job records and resume (§2.4)
def out_dir(exp: str, out=None) -> Path:
    """An experiment's output folder: `out` (made absolute against the working directory, as
    q44_study.out_root does), else <root>/out/<exp>."""
    if out is not None:
        return Path(out).resolve()
    return ms3_root() / "out" / exp


def record_path(out, jid: str) -> Path:
    return Path(out) / "jobs" / job_file_name(jid)


def read_record(out, jid: str) -> Optional[dict]:
    return read_json(record_path(out, jid))


def resume_enabled() -> bool:
    return os.environ.get("MS3_RESUME", "0") == "1"


def is_done(out, jid: str) -> bool:
    """True iff MS3_RESUME=1 and the job's record says 'ok' (M43)."""
    if not resume_enabled():
        return False
    rec = read_record(out, jid)
    return bool(rec) and rec.get("status") == "ok"


def slots_from_env() -> list[str]:
    s = os.environ.get("MS3_SLOTS", "")
    return [x for x in s.split(",") if x]


def try_run(errors: list, tag: str, fn: Callable, *args, **kw):
    """fn(*args, **kw); an exception is appended to `errors` as {'tag', 'error', 'traceback'} and None is
    returned, so that the job goes on with its next run (§2.4)."""
    try:
        return fn(*args, **kw)
    except Exception as err:
        errors.append({"tag": tag, "error": f"{type(err).__name__}: {err}", "traceback": traceback.format_exc()})
        print(f"[ms3] {tag}: {type(err).__name__}: {err}", flush=True)
        return None


def run_job(exp: str, job: Job, fn: Callable[[JobOutputs], Optional[dict]], out=None, *,
            resume: Optional[bool] = None) -> dict:
    """Run one job and write its record out/<exp>/jobs/<id>.json (§2.4): a 'running' record first, then the final
    one with status 'ok' (fn returned; its outputs committed) or 'error' (fn raised; its partial outputs
    discarded), wall time, peak RSS (ru_maxrss), git revision, versions, the number of runs, the errors of
    single runs (without tracebacks, which go to the job's log), the slots held (MS3_SLOTS), the MILP limit for a
    'milp' job, and the other keys fn returned (under 'result'; keep them small, the record is versioned).
    fn(outputs) returns {'runs': n, 'errors': [...], ...} or None. With MS3_RESUME=1 (or
    resume=True) a job whose record says 'ok' is not run again and its record is returned with 'skipped'."""
    out = out_dir(exp, out)
    jp = record_path(out, job.id)
    if (resume_enabled() if resume is None else resume):
        old = read_json(jp)
        if old and old.get("status") == "ok":
            print(f"[{exp}] {job.id}: ok before, skipped (MS3_RESUME=1)", flush=True)
            return {**old, "skipped": True}
    rec = {"job": job.id, "exp": exp, "kind": job.kind, "params": dict(job.params), "status": "running",
           "started": _now(), "pid": os.getpid(), "argv": list(sys.argv), "slots": slots_from_env(),
           "milp_limit_s": milp_limit_s() if job.kind == "milp" else None,
           "git_revision": git_revision(), "versions": versions()}
    dump_json(rec, jp)
    outputs = JobOutputs()
    t0 = time.perf_counter()
    try:
        r = dict(fn(outputs) or {})
        errors = [{k: v for k, v in dict(e).items() if k != "traceback"} for e in r.pop("errors", []) or []]
        runs = int(r.pop("runs", 0))
        committed = outputs.commit()
        rec.update(status="ok", runs=runs, errors=errors, n_errors=len(errors),
                   outputs=[_rel(p, out) for p in committed], result=r)
    except Exception as err:
        outputs.discard()
        rec.update(status="error", error=f"{type(err).__name__}: {err}", traceback=traceback.format_exc())
        print(traceback.format_exc(), flush=True)
    rec.update(wall_s=time.perf_counter() - t0, peak_rss_kb=_peak_rss_kb(), peak_rss_mb=_peak_rss_kb() / 1024.0,
               finished=_now())
    try:
        dump_json(rec, jp)
    except (TypeError, ValueError) as err:     # fn returned something that is not JSON: keep the record valid
        bad = rec.pop("result", None)
        rec.update(status="error", error=f"job result is not valid JSON ({err})", result_repr=repr(bad)[:2000])
        dump_json(rec, jp)
    return rec


def _rel(p: Path, base: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(Path(base).resolve()))
    except ValueError:
        return str(p)


def classify_exit(rc: int, elapsed_s: Optional[float] = None, limit_s: Optional[float] = None,
                  prior_status: Optional[str] = None) -> tuple[Optional[str], str]:
    """(status, rule) of a finished job process (§0 item 2). `limit_s` is LIMIT for a job run under
    `timeout --foreground -k 30 (LIMIT + 60)` (a MILP job) and None otherwise; `elapsed_s` is /usr/bin/time's elapsed
    time; `prior_status` the status in the job's own record. Status None: nothing to record (exit 0 with an 'ok'
    record)."""
    if rc == 0:
        if prior_status == "ok":
            return None, "exit 0 with an 'ok' record"
        return "failed", f"exit 0 without an 'ok' record (record status {prior_status!r})"
    if limit_s is not None:
        bound = float(limit_s) + WALL_GRACE_S
        if rc == 124:
            return "wall_limit", f"exit 124: timeout's SIGTERM at LIMIT + {WALL_GRACE_S} = {bound:g} s"
        if rc == 137:
            if elapsed_s is None:
                return "oom_at_3G", ("exit 137 of a job under timeout, elapsed time unknown: counted as the 3G "
                                     "cap's kill")
            if float(elapsed_s) >= bound:
                return "wall_limit", (f"exit 137 at elapsed {float(elapsed_s):g} s >= LIMIT + {WALL_GRACE_S} = "
                                      f"{bound:g} s: timeout's SIGKILL {KILL_AFTER_S} s after its SIGTERM")
            return "oom_at_3G", (f"exit 137 at elapsed {float(elapsed_s):g} s < LIMIT + {WALL_GRACE_S} = {bound:g} s: "
                                 "the 3G cap's OOM kill")
    elif rc == 137:
        return "oom_at_3G", "exit 137 of a job without timeout: the 3G cap's OOM kill"
    if prior_status == "error":
        return "error", f"exit {rc}; the job recorded an error"
    return "failed", f"exit {rc}"


def record_failure(out, jid: str, rc: int, *, elapsed_s: Optional[float] = None, peak_kb: Optional[float] = None,
                   limit_s: Optional[float] = None, slots: Optional[Sequence[str]] = None) -> Optional[dict]:
    """Classify a finished job process by classify_exit and update its record (written by ms3_lib.sh's `launch`
    when the job exits nonzero or leaves no 'ok' record): status, exit code, elapsed time, peak RSS (KB, from
    /usr/bin/time), the rule applied and the slots held. Returns the record (None if nothing changed)."""
    jp = record_path(out, jid)
    old = read_json(jp) or {"job": jid}
    status, rule = classify_exit(int(rc), elapsed_s, limit_s, old.get("status"))
    if status is None:
        return None
    upd = {"status": status, "exit_code": int(rc), "elapsed_s": None if elapsed_s is None else float(elapsed_s),
           "peak_rss_kb_time": None if peak_kb is None else float(peak_kb), "rule": rule,
           "timeout_limit_s": None if limit_s is None else float(limit_s), "recorded": _now()}
    if old.get("status") not in (None, "running", status):
        upd["status_before"] = old.get("status")
    if slots is not None:
        upd["slots"] = list(slots)
    old.update(upd)
    dump_json(old, jp)
    return old


def read_records(out) -> dict:
    """{job id: record} of every jobs/*.json under `out`."""
    d = Path(out) / "jobs"
    recs = {}
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        r = read_json(p)
        recs[(r or {}).get("job", p.stem)] = r if r is not None else {"status": "unreadable", "file": p.name}
    return recs


# ---------------------------------------------------------------- estimates (§11.1 constants come from the drivers)
def _list_wall(durations: Sequence[float], lanes: int) -> float:
    """Wall time of list scheduling in list order on `lanes` workers."""
    if not durations:
        return 0.0
    free = [0.0] * max(1, int(lanes))
    for d in durations:
        heapq.heappush(free, heapq.heappop(free) + float(d))
    return max(free)


def estimate(jobs: Sequence[Job], workers: int = MAX_SLOTS) -> dict:
    """The jobs with their estimated times and the totals: single-worker time (sum) and the wall time of a run
    script alone on the host with `workers` slots: pool jobs by list scheduling on min(workers, 4) slots, then
    the 'alone' jobs one after another, then the MILP jobs on min(workers, 2) slots. Jobs without an estimate
    are counted under 'unknown'."""
    w = max(1, min(int(workers), MAX_SLOTS))
    known = [j for j in jobs if j.est_s is not None]
    by = {k: [float(j.est_s) for j in known if j.kind == k] for k in JOB_KINDS}
    pool, milp = _list_wall(by["pool"], w), _list_wall(by["milp"], min(w, MILP_SLOTS))
    alone = sum(by["alone"])
    return {"jobs": [{"id": j.id, "kind": j.kind, "est_s": j.est_s} for j in jobs], "workers": w,
            "n_jobs": len(jobs), "n_unknown": len(jobs) - len(known),
            "single_worker_s": sum(float(j.est_s) for j in known), "pool_wall_s": pool, "alone_s": alone,
            "milp_wall_s": milp, "wall_s": pool + alone + milp}


# ---------------------------------------------------------------- manifest (§2.6)
def manifest(exp: str, out, jobs: Sequence[Job], *, script=None, instance_hashes: Optional[Mapping] = None,
             extra: Optional[Mapping] = None) -> dict:
    """manifest.json: meta (experiment, script and its sha256, git revision, versions, time), the job list with
    ids, kinds, parameters, estimates and the status found under jobs/, the instance hashes
    (q44_study.instance_hash, given by the driver) and `extra`."""
    out = Path(out)
    recs = read_records(out)
    meta = {"exp": exp, "git_revision": git_revision(), "versions": versions(), "written": _now()}
    if script is not None:
        sp = Path(script)
        meta.update(script=_rel(sp, paths.REPO), script_sha256=hashlib.sha256(sp.read_bytes()).hexdigest())
    rows = []
    for j in jobs:
        r = recs.get(j.id) or {}
        rows.append({"id": j.id, "kind": j.kind, "params": dict(j.params), "est_s": j.est_s,
                     "status": r.get("status"), "wall_s": r.get("wall_s"), "peak_rss_mb": r.get("peak_rss_mb"),
                     "runs": r.get("runs")})
    m = {"meta": meta, "jobs": rows, "instance_hashes": dict(instance_hashes or {})}
    m.update(dict(extra or {}))
    dump_json(m, out / "manifest.json")
    return m


# ---------------------------------------------------------------- check E11-0 (§2.4, §3.2 step 1, §3.3)
E11_REVISION = "29919ea0a0cb0be883ceb60b86c1f1ddd1dcfa3c"     # E11's frozen commit 29919ea (§3.1)
E11_COPY = Path("out") / "e11"                                # relative to the root
E11_0_RECORD = Path("out") / "ms3_e11_0.json"                 # versioned; the claims report's E11-0 row reads it
E11_0_LIST_MAX = 200                                          # paths listed per finding (the counts are complete)
E11_DONE_LINE = "[run_q44_study] done"


def _tree(top: Path) -> dict:
    """{relative POSIX path: path} of every file under `top`; symbolic links are listed, never followed."""
    top = Path(top)
    files, stack = {}, [top]
    while stack:
        with os.scandir(stack.pop()) as it:
            for e in it:
                p = Path(e.path)
                if e.is_dir(follow_symlinks=False):
                    stack.append(p)
                else:
                    files[p.relative_to(top).as_posix()] = p
    return files


def _digest(p: Path) -> str:
    if p.is_symlink():
        return "symlink:" + os.readlink(p)
    with open(p, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def _recorded_revisions(d) -> set:
    """The git revisions a run file records: meta.git_revision (run files) and the top-level git_revision (the
    per-job cell files cell_*.json), and the git_revision of the first record inside a retry wrapper (retry/<name>.json:
    the keys job, moved, rule and first_record, written when ms3_lib.sh's rerun-once rule moves a failed job's record;
    MS7 addition C60). A value that is not a string (a list, a number) is kept as its JSON text in angle brackets,
    which never equals a commit, so it counts as another revision."""
    if not isinstance(d, dict):
        return set()
    meta = d.get("meta")
    vals = [meta.get("git_revision")] if isinstance(meta, dict) else []
    vals.append(d.get("git_revision"))
    first = d.get("first_record")
    if isinstance(first, dict):
        vals.append(first.get("git_revision"))
    return {v if isinstance(v, str) else f"<{json.dumps(v)[:60]}>" for v in vals if v is not None}


def _head(paths_: Sequence[str]) -> list:
    return list(paths_[:E11_0_LIST_MAX])


def _compare_trees(copy: Path, clone: Path) -> dict:
    """The file trees of `copy` and `clone` (_tree) with the paths found in one only and the common paths whose
    sha256 (or symbolic-link target) differ, each list sorted, and the digest of every file of the copy
    ('digest_copy', {path: _digest}), each file hashed once."""
    a, b = _tree(copy), _tree(clone)
    common = sorted(set(a) & set(b))
    da = {p: _digest(a[p]) for p in sorted(a)}
    return {"copy": a, "clone": b, "only_copy": sorted(set(a) - set(b)), "only_clone": sorted(set(b) - set(a)),
            "common": common, "mismatch": [p for p in common if da[p] != _digest(b[p])], "digest_copy": da}


def _tree_digest(digests: Mapping[str, str]) -> str:
    """sha256 over the lines '<path>\\t<digest>' of a tree's files in path order (tree_digest)."""
    h = hashlib.sha256()
    for p in sorted(digests):
        h.update(f"{p}\t{digests[p]}\n".encode())
    return h.hexdigest()


def _unversioned(exp: str, rel: str) -> bool:
    """Whether a path of an MS3 copy (relative to out/<exp>/) lies in a folder that .gitignore leaves out (M45): the
    per-run data runs/ of the experiment, or of each part of e6 (COPY_PARTS)."""
    sub = rel.split("/", 1)[1] if exp in COPY_PARTS and "/" in rel else rel
    return sub.startswith("runs/")


def tree_digest(top, exp: Optional[str] = None) -> str:
    """The digest of the file tree under `top` that the copy check records as tree_sha256: sha256 over the sorted
    (relative path, sha256 or symbolic-link target) pairs of its files, so a later change of any file, or a file
    added or removed, changes it. With `exp`, only the versioned files count (not those under runs/, _unversioned):
    the record's tree_sha256_versioned, which a checkout without the run files can recompute."""
    files = _tree(Path(top)).items()
    return _tree_digest({p: _digest(f) for p, f in files if exp is None or not _unversioned(exp, p)})


def _last_line(log: Path) -> Optional[str]:
    """The last non-empty line of a run log, None if the log is missing or empty."""
    if not log.is_file():
        return None
    last = [ln for ln in log.read_text(errors="replace").splitlines() if ln.strip()]
    return last[-1] if last else None


def check_e11(clone, root=None, record=None) -> dict:
    """Check E11-0 (§3.3) of this repository's copy <root>/out/e11 against E11's clone `clone` (the clone's
    code/sim/out/e11/): the file lists and the sha256 of every file are equal; manifest.json meta.git_revision is
    E11_REVISION; every run file runs/**/*.json is valid JSON, and every one that records a git revision
    (meta.git_revision, or the top-level git_revision of cell_*.json) records E11_REVISION, while those that
    record none are BL2's siloed sums *_sum.json (counted; the sha256 comparison covers them). Writes the record
    (`record`, default <root>/out/ms3_e11_0.json; 'pass', the paths, the counts, the checking code's git revision
    and the time) and returns it. A missing folder, or a clone that is the copy itself, raises (no record)."""
    r = ms3_root(root)
    copy = r / E11_COPY
    clone = Path(clone).resolve()
    for what, d in (("the clone's folder", clone), ("this repository's copy", copy)):
        if not d.is_dir():
            raise FileNotFoundError(f"check_e11: {what} {d} is not a folder")
    if clone.samefile(copy):
        raise ValueError(f"check_e11: the clone's folder {clone} is the copy itself")
    t = _compare_trees(copy, clone)
    a, b, only_copy, only_clone = t["copy"], t["clone"], t["only_copy"], t["only_clone"]
    common, mismatch = t["common"], t["mismatch"]
    man = read_json(copy / "manifest.json")
    man_meta = man.get("meta") if isinstance(man, dict) else None
    man_rev = man_meta.get("git_revision") if isinstance(man_meta, dict) else None
    n_runs, differs, unreadable, none_sum, none_other = 0, [], [], [], []
    found: dict = {}
    for rel in sorted(a):
        if not (rel.startswith("runs/") and rel.endswith(".json")):
            continue
        n_runs += 1
        try:
            d = json.loads(a[rel].read_bytes())
        except (OSError, ValueError):
            unreadable.append(rel)
            continue
        revs = _recorded_revisions(d)
        for v in revs:
            found[str(v)] = found.get(str(v), 0) + 1
        if not revs:
            (none_sum if rel.endswith("_sum.json") else none_other).append(rel)
        elif revs != {E11_REVISION}:
            differs.append(rel)
    last = _last_line(copy / "run_q44_study.log")
    checks = {"same_file_list": not only_copy and not only_clone and bool(a),
              "same_sha256": not mismatch,
              "manifest_revision": man_rev == E11_REVISION,
              "run_revisions": not differs,
              "runs_readable": not unreadable,
              "runs_without_revision_are_sums": not none_other}
    res = {"check": "E11-0", "pass": all(checks.values()), "checks": checks,
           "copy": str(copy), "clone": str(clone), "expected_git_revision": E11_REVISION,
           "n_files_copy": len(a), "n_files_clone": len(b), "n_files_compared": len(common),
           "n_only_in_copy": len(only_copy), "only_in_copy": _head(only_copy),
           "n_only_in_clone": len(only_clone), "only_in_clone": _head(only_clone),
           "n_sha256_mismatch": len(mismatch), "sha256_mismatch": _head(mismatch),
           "manifest_git_revision": man_rev,
           "n_run_files": n_runs, "run_revisions_found": dict(sorted(found.items())),
           "n_run_revision_differs": len(differs), "run_revision_differs": _head(differs),
           "n_runs_no_revision": len(none_sum) + len(none_other), "n_runs_no_revision_sum": len(none_sum),
           "n_runs_no_revision_other": len(none_other), "runs_no_revision_other": _head(none_other),
           "n_runs_unreadable": len(unreadable), "runs_unreadable": _head(unreadable),
           "e11_log_done": last is not None and last.startswith(E11_DONE_LINE),
           "lists_truncated_at": E11_0_LIST_MAX,
           "checked_by": {"module": "sublet.experiments.ms3_common", "git_revision": git_revision()},
           "time": _now()}
    dump_json(res, Path(record) if record is not None else r / E11_0_RECORD)
    return res


# ---------------------------------------------------------------- the copy check of an MS3 experiment (§1.2)
COPY_PARTS = {"e6": ("a", "b"),       # experiments whose folder has parts, each with its own run log, jobs/, manifest
              "e7": ("main", "stress", "gap", "allow"),       # MS4 addition C20 (design/sim_spec_ms4.md §2.3)
              "s1": ("sweep", "q28"),                         # MS5 addition C30 (design/sim_spec_ms5.md §2.3)
              "e7c": ("gate", "lag"),                         # MS7 addition C53 (design/ms7/plan.md X1)
              "e7r": ("tune", "confirm", "eval"),             # MS7 addition C54 (design/ms7/plan.md X4, X5; e7r.py)
              "e7o": ("fwd", "rev"),                          # MS7 addition C55 (design/ms7/plan.md §3 X2)
              "s1v2": ("sweep", "w0"),                        # MS7 addition C56 (design/ms7/plan.md X3): S1 v2
              "e8v2": ("a",),                                 # C56: E8 v2 part (a); a part (b) would add its folder
              "e7b": ("week", "sens")}                        # MS8 addition (design/ms8/plan.md D2, X6): budget caps
COPY_RECORD = "ms3_copy_{exp}.json"   # <root>/out/ms3_copy_<exp>.json (versioned; the claims report lists it)
_EXP_NAME = re.compile(r"[a-z][a-z0-9_]*")
_SHA1 = re.compile(r"[0-9a-f]{40}")


def _git_dir(repo: Path) -> Path:
    """The git folder of a repository root: <repo>/.git, or the folder a .git file names ('gitdir: <dir>', a
    worktree or a submodule)."""
    g = repo / ".git"
    if g.is_file():
        text = g.read_text(errors="replace").strip()
        if not text.startswith("gitdir:"):
            raise ValueError(f"{g} is neither a folder nor a 'gitdir:' file")
        d = Path(text.split(":", 1)[1].strip())
        return (d if d.is_absolute() else repo / d).resolve()
    if not g.is_dir():
        raise FileNotFoundError(f"{repo} has no .git")
    return g


def clone_commit(clone) -> str:
    """The commit checked out in the clone `clone` (its repository root), read from its .git without running git:
    HEAD holds the hash (a detached HEAD, as in the clean clone of the MS3 runs), or 'ref: <ref>', which is followed
    to the loose ref file or to packed-refs (in the git folder, then in the folder its commondir file names).
    ValueError if no 40-hex hash is found."""
    g = _git_dir(Path(clone))
    head = (g / "HEAD").read_text(errors="replace").strip()
    if _SHA1.fullmatch(head):
        return head
    if not head.startswith("ref:"):
        raise ValueError(f"{g / 'HEAD'}: neither a commit hash nor a ref ({head[:60]!r})")
    ref = head.split(":", 1)[1].strip()
    dirs = [g]
    cd = g / "commondir"
    if cd.is_file():
        c = Path(cd.read_text(errors="replace").strip())
        dirs.append((c if c.is_absolute() else g / c).resolve())
    for d in dirs:
        loose = d / ref
        if loose.is_file():
            h = loose.read_text(errors="replace").strip()
            if _SHA1.fullmatch(h):
                return h
        packed = d / "packed-refs"
        if packed.is_file():
            for ln in packed.read_text(errors="replace").splitlines():
                parts = ln.split()
                if len(parts) == 2 and parts[1] == ref and _SHA1.fullmatch(parts[0]):
                    return parts[0]
    raise ValueError(f"{g}: the ref {ref!r} of HEAD resolves to no commit")


def _copy_kind(rel: str, part: str) -> str:
    """The kind of a file for the counts of the copy check: its first folder under the experiment's (part) folder,
    or its name for a file at the top ('runs', 'jobs', 'lb', 'summary.json'), with the part as a prefix ('a/runs')."""
    sub = rel[len(part) + 1:] if part else rel
    k = sub.split("/", 1)[0]
    return f"{part}/{k}" if part else k


# JSON files that the drivers at the clone's commit write without a git revision (their job record carries it): E2's
# joint MILP files and their pre-MILP records (e2.run_joint) and its E2-5 MILP files (e2.run_ep_milp)
# MS4 addition C20: E4's repro/ files, written by the MS2 script repro_c5_la that job e4:repro reruns (its meta records
# no git revision; the job record does)
COPY_NO_REVISION = {"e2": ("runs/joint/", "runs/ep_milp/"), "e4": ("repro/",)}


def _load_json_file(p: Path) -> tuple[Any, bool]:
    """(parsed JSON, True), or (None, False) for a file that cannot be read or is not valid UTF-8 JSON."""
    try:
        return json.loads(p.read_bytes()), True
    except (OSError, ValueError, RecursionError):
        return None, False


def _no_revision_allowed(exp: str, sub: str, d: Any) -> bool:
    """Whether a JSON file of the copy may record no git revision (check_copy, revisions_recorded): a job record
    written by --record-failure for a job that never wrote one (jobs/<name>.json with no git_revision key and the
    rule applied), its retry wrapper (retry/<name>.json whose first_record is such a record; MS7 addition C60), or a
    file under COPY_NO_REVISION[exp]; `sub` is the path below the part's folder."""
    if re.fullmatch(r"jobs/[^/]+\.json", sub) and isinstance(d, dict) and "git_revision" not in d and "rule" in d:
        return True
    if re.fullmatch(r"retry/[^/]+\.json", sub) and isinstance(d, dict) and isinstance(d.get("first_record"), dict):
        first = d["first_record"]
        if "git_revision" not in first and "rule" in first:
            return True
    return any(sub.startswith(pre) for pre in COPY_NO_REVISION.get(exp, ()))


def check_copy(exp: str, clone, root=None, record=None) -> dict:
    """The copy check of an MS3 experiment (§1.2, "Where the runs run"; the check E11-0 does for E11, §3.3): this
    repository's copy <root>/out/<exp>/ (root as ms3_root(); for e6 the folder out/e6 with its parts a and b)
    against the clone's CLONE/code/sim/out/<exp>/, `clone` being the clone's repository root (the folder with .git).
    It passes iff
      same_file_list, same_sha256  the file lists (runs/ included) and the sha256 of every file are equal;
      no_symlinks                  neither folder holds a symbolic link (a link is compared by its target text only);
      json_readable                every *.json file of the copy is valid JSON (UTF-8);
      revisions                    every JSON file that records a git revision (meta.git_revision, the top-level
                                   git_revision of job records and cell files, or a retry wrapper's first record's,
                                   C60) records the clone's commit
                                   (clone_commit); the files that record none are counted by kind (_copy_kind);
      revisions_recorded           every JSON file records a revision, except a job record written by
                                   --record-failure for a job that never wrote one (no git_revision key, with its
                                   'rule'), its retry wrapper (C60) and the files under COPY_NO_REVISION[exp] (a
                                   null revision is none);
      manifest_revision            the manifest.json of every part records the clone's commit;
      summary_ok                   every part has a summary.json that parses to an object, and its job records
                                   '<exp>:summary' and '<exp>:manifest' have status 'ok';
      no_running_records           no job record jobs/*.json is still 'running' (the records are counted by
                                   status, STATUSES; a status outside them, or an unreadable record, fails
                                   record_statuses_known);
      run_log_done                 every part's run log run_<exp>.log ends with ms3_lib.sh's ms3_finish line
                                   '[run_<exp>] done <time>'.
    Writes the record (`record`, default <root>/out/ms3_copy_<exp>.json: 'pass', the checks, the paths, the counts,
    tree_sha256 (tree_digest of the copy), tree_sha256_versioned (the same over the versioned files, without runs/),
    the checking code's git revision and the time) and returns it. A bad
    experiment name, a missing folder, a clone whose folder is the copy itself, or a clone without a readable commit
    raises (no record)."""
    if not _EXP_NAME.fullmatch(str(exp)):
        raise ValueError(f"check_copy: {exp!r} is not an experiment name")
    if exp == "e11":
        raise ValueError("check_copy: E11 has its own check (--check-e11, §3.2 step 1)")
    r = ms3_root(root)
    copy = r / "out" / exp
    clone_repo = Path(clone).resolve()
    clone_out = clone_repo / "code" / "sim" / "out" / exp
    for what, d in (("the clone's folder", clone_out), ("this repository's copy", copy)):
        if not d.is_dir():
            raise FileNotFoundError(f"check_copy: {what} {d} is not a folder")
    if clone_out.samefile(copy):
        raise ValueError(f"check_copy: the clone's folder {clone_out} is the copy itself")
    commit = clone_commit(clone_repo)
    parts = COPY_PARTS.get(exp, ("",))
    t = _compare_trees(copy, clone_out)
    a = t["copy"]
    links = sorted({f"copy:{p}" for p, f in a.items() if f.is_symlink()}
                   | {f"clone:{p}" for p, f in t["clone"].items() if f.is_symlink()})
    n_json, differs, unreadable, unexpected = 0, [], [], []
    found: dict = {}
    none_by_kind: dict = {}
    small: dict = {}                     # the parsed job records, manifests and summaries, by path
    for rel in sorted(a):
        if not rel.endswith(".json"):
            continue
        n_json += 1
        part = next((p for p in parts if p and rel.startswith(p + "/")), "")
        sub = rel[len(part) + 1:] if part else rel
        d, ok = _load_json_file(a[rel])
        if not ok:
            unreadable.append(rel)
            continue
        if sub in ("manifest.json", "summary.json") or re.fullmatch(r"jobs/[^/]+\.json", sub):
            small[rel] = d
        revs = _recorded_revisions(d)
        for v in revs:
            found[v] = found.get(v, 0) + 1
        if not revs:
            k = _copy_kind(rel, part)
            none_by_kind[k] = none_by_kind.get(k, 0) + 1
            if not _no_revision_allowed(exp, sub, d):
                unexpected.append(rel)
        elif revs != {commit}:
            differs.append(rel)
    manifests, by_part, running, unknown, logs, summaries = {}, {}, [], [], {}, {}
    for part in parts:
        pre = f"{part}/" if part else ""
        top = copy / part if part else copy
        key = part or exp
        man = small.get(f"{pre}manifest.json")
        meta = man.get("meta") if isinstance(man, dict) else None
        rev = meta.get("git_revision") if isinstance(meta, dict) else None
        manifests[key] = rev if rev is None or isinstance(rev, str) else f"<{json.dumps(rev)[:60]}>"
        counts: dict = {}
        by_job: dict = {}
        for rel in sorted(p for p in a if p.startswith(pre) and re.fullmatch(r"jobs/[^/]+\.json", p[len(pre):])):
            rec = small.get(rel)
            st = rec.get("status") if isinstance(rec, dict) else "unreadable"
            st = st if isinstance(st, str) or st is None else f"<{json.dumps(st)[:40]}>"
            counts[str(st)] = counts.get(str(st), 0) + 1
            if isinstance(rec, dict) and isinstance(rec.get("job"), str):
                by_job[rec["job"]] = st
            if st == "running":
                running.append(rel)
            elif st not in STATUSES:
                unknown.append(rel)
        by_part[key] = dict(sorted(counts.items()))
        s_rel = f"{pre}summary.json"
        s_rec, m_rec = by_job.get(job_id(exp, "summary")), by_job.get(job_id(exp, "manifest"))
        summaries[key] = {"file": s_rel, "exists": s_rel in a, "object": isinstance(small.get(s_rel), dict),
                          "summary_record": s_rec, "manifest_record": m_rec}
        summaries[key]["ok"] = summaries[key]["object"] and s_rec == "ok" and m_rec == "ok"
        log = top / f"run_{exp}.log"
        last = _last_line(log)
        logs[key] = {"file": log.relative_to(copy).as_posix(), "exists": log.is_file(), "last_line": last,
                     "done": last is not None and last.startswith(f"[run_{exp}] done ")}
    total: dict = {}
    for counts in by_part.values():
        for st, n in counts.items():
            total[st] = total.get(st, 0) + n
    checks = {"same_file_list": not t["only_copy"] and not t["only_clone"] and bool(a),
              "same_sha256": not t["mismatch"],
              "no_symlinks": not links,
              "json_readable": not unreadable,
              "revisions": not differs,
              "revisions_recorded": not unexpected,
              "manifest_revision": all(v == commit for v in manifests.values()),
              "summary_ok": all(x["ok"] for x in summaries.values()),
              "no_running_records": not running,
              "record_statuses_known": not unknown,
              "run_log_done": all(x["done"] for x in logs.values())}
    res = {"check": "copy", "exp": exp, "pass": all(checks.values()), "checks": checks,
           "copy": str(copy), "clone": str(clone_repo), "clone_out": str(clone_out), "clone_commit": commit,
           "parts": [p for p in parts if p], "tree_sha256": _tree_digest(t["digest_copy"]),
           "tree_sha256_versioned": _tree_digest({p: d for p, d in t["digest_copy"].items()
                                                  if not _unversioned(exp, p)}),
           "n_files_copy": len(a), "n_files_clone": len(t["clone"]), "n_files_compared": len(t["common"]),
           "n_only_in_copy": len(t["only_copy"]), "only_in_copy": _head(t["only_copy"]),
           "n_only_in_clone": len(t["only_clone"]), "only_in_clone": _head(t["only_clone"]),
           "n_sha256_mismatch": len(t["mismatch"]), "sha256_mismatch": _head(t["mismatch"]),
           "n_symlinks": len(links), "symlinks": _head(links),
           "n_partial": sum(1 for p in a if p.endswith(PARTIAL)),
           "n_json": n_json, "revisions_found": dict(sorted(found.items())),
           "n_revision_differs": len(differs), "revision_differs": _head(differs),
           "n_no_revision": sum(none_by_kind.values()), "no_revision_by_kind": dict(sorted(none_by_kind.items())),
           "n_no_revision_unexpected": len(unexpected), "no_revision_unexpected": _head(unexpected),
           "no_revision_allowed_under": list(COPY_NO_REVISION.get(exp, ())),
           "n_json_unreadable": len(unreadable), "json_unreadable": _head(unreadable),
           "manifest_git_revision": manifests, "summaries": summaries,
           "records_by_status": dict(sorted(total.items())), "records_by_part": by_part,
           "n_running": len(running), "running_records": _head(running),
           "n_unknown_status": len(unknown), "unknown_status_records": _head(unknown),
           "run_logs": logs,
           "lists_truncated_at": E11_0_LIST_MAX,
           "checked_by": {"module": "sublet.experiments.ms3_common", "git_revision": git_revision()},
           "time": _now()}
    dump_json(res, Path(record) if record is not None else r / "out" / COPY_RECORD.format(exp=exp))
    return res


# ---------------------------------------------------------------- Q39's lower bound and the brackets (§2.5, M4)
def _field(x, name):
    if x is None:
        return None
    if isinstance(x, Mapping):
        return x.get(name)
    return getattr(x, name, None)


def _finite(v) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _status(x):
    """Numeric solver status (0 optimal, 1 limit reached, 2 infeasible, 3 unbounded, 4 other), a job status for
    a killed MILP job ('wall_limit', 'oom_at_3G', ...), or None (not run)."""
    if x is None:
        return None
    s = _field(x, "status")
    if isinstance(s, bool):
        return None
    if isinstance(s, (int, float)) and _finite(s) is not None:
        return int(s)
    return s


def bench_values(lp=None, milp=None) -> dict:
    """The benchmark values of one (σ, ω) or eager instance from its LP and MILP (SolveResult, a dict with the
    same fields read from a benchmark record, a killed job's record {'status': 'wall_limit' | 'oom_at_3G', ...},
    or None): LB = max(LP optimum, MILP dual bound) over the values that are valid lower bounds (an LP with
    status 0; a dual bound of a MILP with status 0 or 1), its source ('lp' or 'milp_dual'), the incumbent (a MILP
    with status 0 or 1), the gap, exact = gap <= 1e-4, the two statuses and the grid."""
    lp_status, milp_status = _status(lp), _status(milp)
    lp_val = _finite(_field(lp, "objective")) if lp_status == 0 else None
    solved = milp_status in (0, 1)
    dual = _finite(_field(milp, "dual_bound")) if solved else None
    inc = _finite(_field(milp, "objective")) if solved else None
    gap = _finite(_field(milp, "gap")) if solved else None
    grids = {g for g in (_field(lp, "grid"), _field(milp, "grid")) if g is not None}
    if len(grids) > 1:
        raise ValueError(f"LP and MILP on different grids {sorted(grids)}: not one benchmark")
    out = {"LP": lp_val, "dual_bound": dual, "incumbent": inc, "gap": gap,
           "exact": bool(gap is not None and inc is not None and gap <= EXACT_GAP),
           "lp_status": lp_status, "milp_status": milp_status, "grid": next(iter(grids), None)}
    cands = [(v, src) for v, src in ((lp_val, "lp"), (dual, "milp_dual")) if v is not None]
    if cands:
        v, src = max(cands, key=lambda t: (t[0], t[1] == "lp"))     # a tie counts as the LP's
        out.update(LB=v, LB_source=src)
    else:
        out.update(LB=None, LB_source=None,
                   LB_note=f"no valid lower bound (LP status {lp_status!r}, MILP status {milp_status!r})")
    return out


def _div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b <= 0:
        return None
    return float(a) / float(b)


def lb_record(alg_usd: float, lp=None, milp=None, *, inst=None, model=None, reason: Optional[str] = None) -> dict:
    """Q39's lower-bound record of one run (§2.5): {'LB': max(LP, dual bound), 'LB_source': 'lp'|'milp_dual',
    'ratio_LB': ALG/LB, 'ratio_inc': ALG/incumbent or null, 'gap', 'exact', 'milp_status', 'lp_status'} plus
    'ALG', 'LP', 'dual_bound', 'incumbent' and 'grid'. A MILP killed at the hard wall-clock limit (a record with
    status 'wall_limit') or by the cap leaves the LP as LB. ratio_LB bounds ALG/OPT(σ, ω) from above only for a
    run on the benchmark's grid with buffer violations absorbed: with `inst` and `model` given, the reason of
    drivers.run.ratio_validity(grid, inst, model) (or `reason` if given) sets ratio_LB and ratio_inc to null
    with 'ratio_note'. If neither record names its grid, the violations rule still applies (ratio_validity on
    grid 'fast', which its grid rule never rejects) and, when it passes, the ratios are null with the note
    'benchmark grid unknown: ratio validity not checked'."""
    alg = _finite(alg_usd)
    if alg is None:
        raise ValueError(f"lb_record: ALG must be a finite number, got {alg_usd!r}")
    b = bench_values(lp, milp)
    why = reason
    if why is None and inst is not None and model is not None:
        from ..drivers.run import ratio_validity
        if b["grid"] is not None:
            why = ratio_validity(b["grid"], inst, model)
        else:
            why = ratio_validity("fast", inst, model) or "benchmark grid unknown: ratio validity not checked"
    rec = {"ALG": alg, **b}
    if why is not None:
        rec.update(ratio_LB=None, ratio_inc=None, ratio_note=why)
        return rec
    rec["ratio_LB"] = _div(alg, b["LB"])
    if rec["ratio_LB"] is None:
        rec["ratio_LB_note"] = b.get("LB_note") or f"LB = {b['LB']!r} is not positive"
    rec["ratio_inc"] = _div(alg, b["incumbent"])
    if rec["ratio_inc"] is None:
        rec["ratio_inc_note"] = f"no incumbent (MILP status {b['milp_status']!r})"
    return rec


def bracket(eager: Mapping, omega: Mapping) -> dict:
    """M4: the ratio OPT_eager / OPT(σ, ω) of two benchmarks, each given by bench_values or lb_record:
    point = incumbent_e / incumbent_ω, lo = LB_e / incumbent_ω, hi = incumbent_e / LB_ω; the true ratio lies in
    [lo, hi] (OPT_e >= LB_e, OPT_ω <= incumbent_ω, and the reverse); exact iff both gaps are at most 1e-4."""
    ie, iw, le, lw = eager.get("incumbent"), omega.get("incumbent"), eager.get("LB"), omega.get("LB")
    out = {"point": _div(ie, iw), "lo": _div(le, iw), "hi": _div(ie, lw),
           "exact": bool(eager.get("exact") and omega.get("exact")),
           "gap_eager": eager.get("gap"), "gap_omega": omega.get("gap")}
    for k, (a, b) in (("point", (ie, iw)), ("lo", (le, iw)), ("hi", (ie, lw))):
        if out[k] is None:
            out[f"{k}_note"] = f"missing or non-positive value ({a!r} / {b!r})"
    if out["lo"] is not None and out["hi"] is not None and out["lo"] > out["hi"] * (1 + 1e-9):
        raise ValueError(f"bracket: lo {out['lo']} > hi {out['hi']}: the bounds contradict each other")
    return out


# ---------------------------------------------------------------- aggregation (§2.5, M13)
def median_summary(values, seed: int = 0, B: int = 2000) -> dict:
    """metrics.aggregate: median, P95, maximum and the 95% percentile bootstrap of the median."""
    from ..metrics import aggregate
    return aggregate(values, seed=seed, B=B)


def ratio_of_means(alg, opt, B: int = 2000, seed: int = 0) -> dict:
    """E[ALG] / E[OPT] over paired runs (M13: the form of Yao's principle and of C3-T4') with the 95% percentile
    bootstrap interval that resamples runs (one index set per resample for both arrays, B resamples drawn with
    default_rng(seed)). Returns {'n', 'mean_alg', 'mean_opt', 'ratio', 'ci95': [lo, hi], 'B', 'seed'}."""
    import numpy as np
    a = np.asarray(list(alg), dtype=np.float64)
    o = np.asarray(list(opt), dtype=np.float64)
    if a.shape != o.shape or a.ndim != 1:
        raise ValueError(f"ratio_of_means: alg and opt must be paired 1-d sequences, got {a.shape} and {o.shape}")
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(o))):
        raise ValueError("ratio_of_means: non-finite costs")
    n = int(len(a))
    res = {"n": n, "mean_alg": None, "mean_opt": None, "ratio": None, "ci95": [None, None], "B": int(B),
           "seed": int(seed)}
    if n == 0:
        res["ratio_note"] = "no runs"
        return res
    res.update(mean_alg=float(a.mean()), mean_opt=float(o.mean()))
    if o.sum() <= 0:
        res["ratio_note"] = "E[OPT] is not positive"
        return res
    res["ratio"] = float(a.sum() / o.sum())
    rng = np.random.default_rng(seed)
    ratios = np.empty(B)
    rows = max(1, min(B, 4_000_000 // n))    # resample in chunks, as metrics.aggregate
    for s in range(0, B, rows):
        e = min(B, s + rows)
        idx = rng.integers(0, n, size=(e - s, n))
        den = o[idx].sum(axis=1)
        num = a[idx].sum(axis=1)
        ratios[s:e] = np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)
    ok = ratios[np.isfinite(ratios)]
    if len(ok) < B:
        res["ci95_note"] = f"{B - len(ok)} of {B} resamples with E[OPT] = 0 left out"
    if len(ok):
        lo, hi = np.percentile(ok, [2.5, 97.5])
        res["ci95"] = [float(lo), float(hi)]
    return res


# ---------------------------------------------------------------- driver command line (§2.4)
def main(exp: str, *, jobs: Callable[[], Sequence[Job]], run: Callable[[Job, JobOutputs, Path], Optional[dict]],
         summary: Optional[Callable[[Path], Optional[dict]]] = None, script=None,
         manifest_extra: Optional[Callable[[Path], Mapping]] = None, argv=None, description: Optional[str] = None
         ) -> int:
    """The command line of an MS3 driver (module docstring): `jobs()` lists the jobs in run order, `run(job,
    outputs, out)` runs one (returns {'runs', 'errors', ...}; outputs through `outputs`), `summary(out)` builds
    summary.json and tables.md from the job outputs. Exit code 0 iff the job, the summary or the manifest has
    status 'ok' (the last two have the records '<exp>:summary' and '<exp>:manifest', which no job may use)."""
    ap = argparse.ArgumentParser(prog=f"python -m sublet.experiments.{exp}", description=description,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true", help="the jobs, '<pool|alone|milp> <job id>' per line")
    g.add_argument("--job", metavar="ID", help="run one job")
    g.add_argument("--summary", action="store_true", help="build the summary from the job outputs")
    g.add_argument("--estimate", action="store_true", help="the jobs with estimated times; runs nothing")
    g.add_argument("--manifest", action="store_true", help="write manifest.json")
    ap.add_argument("--out", type=Path, default=None, help=f"output folder (default <root>/out/{exp})")
    ap.add_argument("--workers", type=int, default=MAX_SLOTS, help="slots assumed by --estimate (at most 4)")
    a = ap.parse_args(argv)
    js = list(jobs())
    check_jobs(js)
    reserved = {job_id(exp, "summary"), job_id(exp, "manifest")} & {j.id for j in js}
    if reserved:
        raise ValueError(f"job ids {sorted(reserved)} are the records of --summary and --manifest")
    if a.list:
        for j in js:
            print(f"{j.kind} {j.id}")
        return 0
    if a.estimate:
        e = estimate(js, a.workers)
        for j in e["jobs"]:
            est = "?" if j["est_s"] is None else f"{j['est_s']:.0f}"
            print(f"{j['kind']:5s} {j['id']}  est {est} s")
        print(f"[estimate] {e['n_jobs']} jobs ({e['n_unknown']} without an estimate); single worker "
              f"{e['single_worker_s'] / 3600:.2f} h; with {e['workers']} slot(s): pool {e['pool_wall_s'] / 3600:.2f} h"
              f" + alone {e['alone_s'] / 3600:.2f} h + MILP {e['milp_wall_s'] / 3600:.2f} h = "
              f"{e['wall_s'] / 3600:.2f} h of wall time")
        return 0
    out = out_dir(exp, a.out)
    if a.manifest:
        mj = Job(job_id(exp, "manifest"), "pool")

        def _manifest(outputs):
            # manifest_extra may build every instance of the experiment (their hashes, §2.6), so ms3_lib.sh runs
            # this in a 3G scope holding one slot, and the record keeps its wall time and peak RSS
            manifest(exp, out, js, script=script, extra=manifest_extra(out) if manifest_extra else None)
            return {"runs": 0}
        rec = run_job(exp, mj, _manifest, out, resume=False)
    elif a.summary:
        if summary is None:
            print(f"[{exp}] no summary defined", file=sys.stderr)
            return 2
        sj = Job(job_id(exp, "summary"), "pool")

        def _summary(outputs):
            summary(out)            # writes summary.json and tables.md itself; nothing of it goes into the record
            return {"runs": 0}
        rec = run_job(exp, sj, _summary, out, resume=False)
    else:
        by_id = {j.id: j for j in js}
        if a.job not in by_id:
            print(f"[{exp}] no job {a.job!r} (see --list)", file=sys.stderr)
            return 2
        job = by_id[a.job]
        rec = run_job(exp, job, lambda outputs: run(job, outputs, out), out)
    print(f"[{exp}] {rec['job']}: {rec['status']}"
          + ("" if rec.get("skipped") else f" in {rec.get('wall_s', 0.0):.1f} s, peak RSS "
                                          f"{rec.get('peak_rss_mb', 0.0):.0f} MB"), flush=True)
    return 0 if rec["status"] == "ok" else 1


def _cli(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.ms3_common",
                                 description="Helpers of ms3_lib.sh (design/sim_spec_ms3.md §2.4).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--max-workers", action="store_true", help="print N of the slot semaphore")
    g.add_argument("--record-failure", metavar="ID", help="classify a finished job process and update its record")
    g.add_argument("--job-file", metavar="ID", help="print the record's file name of a job id")
    g.add_argument("--check-e11", metavar="CLONE_E11", type=Path, default=None,
                   help="check E11-0: compare <root>/out/e11 with the clone's code/sim/out/e11/, write "
                        "<root>/out/ms3_e11_0.json; exit 1 if the check fails")
    g.add_argument("--check-copy", nargs=2, metavar=("EXP", "CLONE"), default=None,
                   help="the copy check of §1.2: compare <root>/out/<EXP> with CLONE/code/sim/out/<EXP> (CLONE the "
                        "clone's repository root), write <root>/out/ms3_copy_<EXP>.json; exit 1 if the check fails")
    ap.add_argument("--root", default=None, help="folder whose out/ holds e11/ and the experiments' copies (default "
                                                 "MS3_ROOT or this repository's code/sim)")
    ap.add_argument("--report", type=Path, default=None,
                    help="where --check-e11 or --check-copy writes its record (default <root>/out/ms3_e11_0.json, "
                         "<root>/out/ms3_copy_<EXP>.json)")
    ap.add_argument("--out", type=Path, default=None, help="the experiment's output folder (--record-failure)")
    ap.add_argument("--exit-code", type=int, default=1)
    ap.add_argument("--elapsed", type=float, default=None, help="elapsed seconds (/usr/bin/time %%e)")
    ap.add_argument("--peak-kb", type=float, default=None, help="peak RSS in KB (/usr/bin/time %%M)")
    ap.add_argument("--limit", type=float, default=None, help="LIMIT of a job run under timeout (MILP jobs)")
    ap.add_argument("--slots", default=None, help="comma-separated lock files the job held")
    a = ap.parse_args(argv)
    if a.max_workers:
        print(max_workers(a.root))
        return 0
    if a.job_file:
        print(job_file_name(a.job_file))
        return 0
    if a.check_e11 is not None:
        try:
            res = check_e11(a.check_e11, a.root, a.report)
        except (OSError, ValueError) as err:
            print(f"[ms3] check E11-0 not run: {err}", file=sys.stderr)
            return 2
        failed = [k for k, v in res["checks"].items() if not v]
        print(f"[ms3] check E11-0 {'pass' if res['pass'] else 'FAIL'}: {res['n_files_copy']} files in the copy, "
              f"{res['n_files_clone']} in the clone, {res['n_sha256_mismatch']} sha256 mismatches, manifest "
              f"{res['manifest_git_revision']}, {res['n_run_files']} run files ({res['n_run_revision_differs']} "
              f"with another revision, {res['n_runs_no_revision_sum']} BL2 sums without one)"
              + (f"; failed: {', '.join(failed)}" if failed else ""), flush=True)
        return 0 if res["pass"] else 1
    if a.check_copy is not None:
        exp, clone = a.check_copy
        try:
            res = check_copy(exp, clone, a.root, a.report)
        except (OSError, ValueError) as err:
            print(f"[ms3] copy check not run: {err}", file=sys.stderr)
            return 2
        failed = [k for k, v in res["checks"].items() if not v]
        st = ", ".join(f"{k} {v}" for k, v in res["records_by_status"].items()) or "none"
        print(f"[ms3] copy check {exp} {'pass' if res['pass'] else 'FAIL'}: {res['n_files_copy']} files in the copy, "
              f"{res['n_files_clone']} in the clone, {res['n_sha256_mismatch']} sha256 mismatches, clone commit "
              f"{res['clone_commit']}, {res['n_json']} JSON files ({res['n_revision_differs']} with another "
              f"revision, {res['n_no_revision']} without one), job records: {st}, run log done "
              f"{all(x['done'] for x in res['run_logs'].values())}"
              + (f"; failed: {', '.join(failed)}" if failed else ""), flush=True)
        return 0 if res["pass"] else 1
    if a.out is None:
        ap.error("--record-failure needs --out")
    slots = [s for s in (a.slots or "").split(",") if s] if a.slots is not None else None
    rec = record_failure(a.out, a.record_failure, a.exit_code, elapsed_s=a.elapsed, peak_kb=a.peak_kb,
                         limit_s=a.limit, slots=slots)
    if rec is not None:
        print(f"[ms3] {a.record_failure}: {rec['status']} ({rec['rule']})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
