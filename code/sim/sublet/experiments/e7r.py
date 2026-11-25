"""E7r: baselines and stress regimes of MS7 (design/ms7/plan.md X4, X5, D6; change C54; design/ms7/feasibility/
baselines.md §2, §3 B7). Tags, modes, W0+, the grid and the gate are in ms7_baselines.py; e7h.py, ms5b_common.TAGS and
ms5b_analysis.py are untouched (this driver reuses e7h.one_run, e7h.collect and e7h's run-file layout).

Parts (E7R_PART; one part per run of run_e7r.sh, in this order), outputs in <root>/out/e7r/<part>/ (jobs/, logs/, runs/
(not versioned), retry/, manifest.json, summary.json, tables.md, run_e7r.log):
  tune     development weeks 113-116 (TUNE_WEEKS) x the six main modes (L-tr and the five stress modes of W0), policy
           seed 0: every configuration of the grids of ms7_baselines (tags '<family>-g<NN>'; families BL1, BL2, BL3,
           BL4, BL5, MPC; g00 the family's as-built setting); then run_e7r.sh runs e7r_select.py on tune's summary,
           which applies the pre-stated rules T and W and writes tune/selection.json (its sha256 is registered, D6)
  confirm  weeks 121-124 (CONFIRM_WEEKS) x the six main modes: per family its as-built setting (the MS5b tag of
           FAMILY_DEFAULT, or MPC) and its T and W settings ('<family>-T', '<family>-W'; W equal to T runs once, as T,
           with the alias recorded), read from tune/selection.json
  eval     the confirmation's weeks 301-316 (EVAL_WEEKS), policy seed 0: the transplants and spares tags of
           EVAL_FIXED and the tuned settings under EVAL_MODES (the confirmation's seven modes and the six NEW_MODES),
           MPC-oracle (a lookahead reference for the trace cost) under L-tr and L-hon (REFERENCE_MODES), and the
           confirmation's tags of EXISTING_EVAL_TAGS (Sublet, A9, the H1 and H2b sets, CR, A9-kstar) under
           EXISTING_MODES: NEW_MODES (their seven modes are out/sublet_v2/main's) and L-tr once more, which must
           reproduce main's runs bit for bit (e7r_analysis's identity check, so that runs of the two commits are
           combined only when the frozen behaviour is unchanged); then run_e7r.sh runs e7r_analysis.py
           (out/e7r/analysis.json and analysis.md)
A week job runs one tag on one week under every mode of its cell in one process (the instance built once; L-pk on its
own instance, ms7_baselines.peak_aligned_instance, L-b999 is not used), as e7h's week jobs; its run file is
runs/<job file>.json with e7h's entries (ms5b_common.week_entry: mode, r0, the guard's facts, A9's counts). Job ids:
'e7r:<part>:k=week:tag=<tag>:c=<week>'.

The gate (D6; ms7_baselines.check_registration): a part refuses to start unless design/ms7/registration.md exists at
HEAD, the tree is clean and e7r_select.py and e7r_analysis.py have the registered sha256; confirm and eval also need
tune/selection.json of a run of the same kind (reduced or not), and of a full run also that e7r_select.py with the
registered sha256 wrote it from a tune summary of this HEAD (selection_check). Reduced runs (MS7_E7R_REDUCED=1,
run_e7r.sh --reduced) record the gate without enforcing it and use the development cell bench_e7f 101 with a 2-hour
horizon only, never a seed of the tune, confirm or eval weeks (part eval runs the confirmation's tags there under every
mode, since main has no runs of that cell); their summaries carry meta.reduced, never a result.

Command line (ms3_common.main), run from code/sim:
  python -m sublet.experiments.e7r --list | --job ID | --summary | --estimate | --manifest  [--out DIR]
  python -m sublet.experiments.e7r --check-start          the gate of the part(s) of E7R_PART; exit 1 if refused
  python -m sublet.experiments.e7r --retry-list --out DIR  the missing-run rule's rerun (as e7h's)

Status: the tags are baselines and stress regimes; no ratio is claimed (ms7_baselines). The runs are exploratory (after
the MS5b freeze) and pre-specified (D6).
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

from .. import paths
from . import e7
from . import e7h
from . import ms3_common as mc
from . import ms4_common as m4
from . import ms5b_common as m5
from . import ms7_baselines as m7
from .ms3_common import Job, job_id, num_key

EXP = m7.EXP
SPEC = m7.SPEC
PARTS = ("tune", "confirm", "eval")
REDUCED_ENV = "MS7_E7R_REDUCED"
REDUCED_HORIZON_MIN = 120
SELECTION = "selection.json"


# ---------------------------------------------------------------- settings, parts, folders
def design() -> dict:
    red = os.environ.get(REDUCED_ENV, "0") == "1"
    return {"reduced": red, "horizon_min": REDUCED_HORIZON_MIN if red else m7.WEEK_MIN}


def parts() -> list:
    v = os.environ.get("E7R_PART", "")
    ps = [p for p in v.replace(",", " ").split() if p]
    bad = [p for p in ps if p not in PARTS]
    if bad:
        raise ValueError(f"E7R_PART must name parts of {list(PARTS)}, got {v!r}")
    return ps or list(PARTS)


def part_dir(part: str, root=None) -> Path:
    """<root>/out/e7r/<part> (root as ms3_common.ms3_root)."""
    return mc.ms3_root(root) / "out" / EXP / part


def selection_path(root=None) -> Path:
    return part_dir("tune", root) / SELECTION


def load_selection(root=None) -> Optional[dict]:
    """tune/selection.json (e7r_select.py), or None while it is missing."""
    p = selection_path(root)
    return mc.read_json(p) if p.is_file() else None


def selection_check(sel: dict, rec: Optional[dict] = None) -> tuple[bool, str]:
    """(ok, reason) for the selection of a full run (D6): e7r_select.py's sha256 that selection.json records equals
    the one design/ms7/registration.md records, and the tune summary it read was written at this HEAD (its meta's
    summary_git_revision; HEAD from ms7_baselines.registration_record, or `rec`)."""
    rec = rec if rec is not None else m7.registration_record()
    meta = sel.get("meta") or {}
    want = ((rec.get("files") or {}).get("e7r_select.py") or {}).get("recorded")
    why = []
    if want is None or meta.get("script_sha256") != want:
        why.append(f"selection.json was written by e7r_select.py {str(meta.get('script_sha256'))[:12]}, the "
                   f"registration records {str(want)[:12]}")
    if rec.get("head") is None or meta.get("summary_git_revision") != rec.get("head"):
        why.append(f"selection.json comes from a tune summary of {str(meta.get('summary_git_revision'))[:12]}, HEAD is "
                   f"{str(rec.get('head'))[:12]}")
    return (not why), ("; ".join(why) if why else "selection of the registered script on a tune summary of HEAD")


def need_selection(root=None) -> dict:
    """The selection the parts confirm and eval read; RuntimeError while it is missing, of the other run kind or, in
    a full run, not passing selection_check."""
    s = load_selection(root)
    if s is None:
        raise RuntimeError(f"{selection_path(root)} is missing: run part tune and e7r_select.py first")
    red = bool((s.get("meta") or {}).get("reduced"))
    if red != design()["reduced"]:
        raise RuntimeError(f"{selection_path(root)} is from a {'reduced' if red else 'full'} run, this run is "
                           f"{'reduced' if design()['reduced'] else 'full'}")
    if not red:
        ok, why = selection_check(s, _gate_record())
        if not ok:
            raise RuntimeError(f"{selection_path(root)}: {why}")
    return s


def run_path(out, jid: str) -> Path:
    return e7h.run_path(out, jid)


# ---------------------------------------------------------------- job lists
def _est(name: str, t: m7.Tag, n_runs: int, hz: int) -> float:
    return m7.EST_JOB_S + (m7.EST_TABLE_S if m7.a9_family(name, t) else 0.0) + \
        n_runs * m7.est_run_s(t) * hz / m7.WEEK_MIN


def _week_jobs(part: str, names, weeks, modes, hz: int, selection=None) -> list:
    out = []
    for c in weeks:
        for name in names:
            t = m7.tag(name, selection)
            params = None if isinstance(t.params, str) else dict(t.params)
            out.append(Job(job_id(EXP, part, k="week", tag=name, c=int(c)), "pool",
                           {"part": part, "kind": "week", "tag": name, "policy_id": t.id, "params": params,
                            "family": t.family, "c": int(c), "modes": list(modes), "policy_seeds": [0],
                            "horizon_min": int(hz)}, _est(name, t, len(modes), hz)))
    return out


def tuned_names(selection: dict, family: str) -> list:
    """The tuned tags of a family that run: '<family>-T' and '<family>-W' unless the selection aliases W to T."""
    al = selection.get("aliases") or {}
    return [n for n in (f"{family}-T", f"{family}-W") if n in (selection.get("tuned") or {}) and n not in al]


def jobs(ps=None, selection=None) -> list:
    """The jobs of the parts `ps` (default: E7R_PART) in run order (module docstring); confirm and eval read
    tune/selection.json (or `selection`)."""
    ps = parts() if ps is None else list(ps)
    d = design()
    red, hz = d["reduced"], d["horizon_min"]
    out: list = []
    for part in ps:
        if part == "tune":
            weeks = (m7.REDUCED_WEEK,) if red else m7.TUNE_WEEKS
            names = [n for fam in m7.FAMILIES for n in m7.grid(fam)]
            out += _week_jobs(part, names, weeks, m7.TUNE_MODES, hz)
            continue
        sel = selection if selection is not None else need_selection()
        if part == "confirm":
            weeks = (m7.REDUCED_WEEK,) if red else m7.CONFIRM_WEEKS
            names = []
            for fam in m7.FAMILIES:
                names += [m7.FAMILY_DEFAULT[fam]] + tuned_names(sel, fam)
            out += _week_jobs(part, names, weeks, m7.TUNE_MODES, hz, sel)
        elif part == "eval":
            weeks = (m7.REDUCED_WEEK,) if red else m7.EVAL_WEEKS
            names = list(m7.EVAL_FIXED) + [n for fam in m7.FAMILIES for n in tuned_names(sel, fam)]
            out += _week_jobs(part, names, weeks, m7.EVAL_MODES, hz, sel)
            out += _week_jobs(part, m7.EVAL_REFERENCE, weeks, m7.REFERENCE_MODES, hz, sel)
            # the confirmation's tags under the new modes and L-tr (their seven modes are main's; L-tr checks that this
            # commit reproduces main's runs); a reduced run's week has no main runs, so there they run under every mode
            out += _week_jobs(part, m7.EXISTING_EVAL_TAGS, weeks, m7.EVAL_MODES if red else m7.EXISTING_MODES, hz,
                              sel)
    return out


# ---------------------------------------------------------------- the gate (D6)
_GATE: dict = {}


def _gate_record() -> dict:
    """ms7_baselines.registration_record, read once per process (also by selection_check)."""
    if "rec" not in _GATE:
        _GATE["rec"] = m7.registration_record()
    return _GATE["rec"]


def gate(part: str) -> dict:
    """The gate of a part, checked once per process (ms7_baselines.check_registration; recorded and not enforced in
    reduced runs). Raises RuntimeError when refused."""
    if "g" not in _GATE:
        ok, why, rec = m7.check_registration(_gate_record())
        red = design()["reduced"]
        _GATE["g"] = {"kind": "registration", "ok": ok, "reason": why, "enforced": not red, "registration": rec}
        if red:
            _GATE["g"]["note"] = "reduced run on a development cell: the gate is recorded, not enforced"
    g = _GATE["g"]
    if g["enforced"] and not g["ok"]:
        raise RuntimeError(g["reason"])
    return g


def _selection_ref(part: str) -> Optional[dict]:
    if part == "tune":
        return None
    p = selection_path()
    return {"path": str(p.relative_to(mc.ms3_root())) if p.is_file() else str(p),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None}


def _meta_run(job: Job) -> dict:
    part = job.params["part"]
    return {"exp": EXP, "job": job.id, "part": part, "spec": SPEC, "git_revision": mc.git_revision(),
            "versions": mc.versions(), "written": mc._now(), "reduced": design()["reduced"], "gate": gate(part),
            "selection": _selection_ref(part)}


# ---------------------------------------------------------------- jobs: week runs
def run_week(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One week job: tag p['tag'] on week c under each mode of p['modes'] (e7h.one_run per run), the instance built
    once per instance key (L-pk: peak_aligned_instance of the base instance)."""
    from ..drivers import run as drun
    from ..lender import resolve_params
    p = job.params
    name, c, hz, seeds = p["tag"], int(p["c"]), int(p["horizon_min"]), [int(s) for s in p["policy_seeds"]]
    pid = p["policy_id"]
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
                                 seeds=seeds, name="e7r_build")
            inst, _, ecfg = drun.build(spec0, c)
            pk = None
        if not ecfg.check_invariants:
            raise RuntimeError("E7r runs need check_invariants=True")
        insts[key] = {"inst": inst, "ecfg": ecfg, "refs": m4.references(inst), "own": e7._own(inst),
                      "hash": mc.instance_hash(inst), "sizes": e7.instance_sizes(inst), "peak_aligned": pk}
        return insts[key]
    errors, rows, models, params_rec = [], [], {}, {}
    for mode in p["modes"]:
        key = m7.instance_key(mode)
        b = build(key)
        inst, ecfg, refs, own = b["inst"], b["ecfg"], b["refs"], b["own"]
        params = dict(p["params"]) if p["params"] is not None else m5.tag_params(name, inst)
        params_rec[key] = params
        spec = m7.week_spec(pid, params, mode=mode, c=c, horizon_min=hz, seeds=seeds, name=f"e7r_{p['part']}_{name}")
        model = drun._lender_model(spec, inst)
        models[mode] = {**e7._lender_dict(model), "resolved": resolve_params(inst, model)}
        for ps in seeds:
            e = mc.try_run(errors, f"{name} {mode} p{ps}", e7h.one_run, spec, name, inst, model, ecfg, refs, own, c,
                           ps, mode)
            if e is not None:
                rows.append(e)
                print(f"[e7r] {p['part']} c{c} {name} {mode} p{ps}: ALG {e['ALG']:.4f} USD, r0 {e.get('r0')}, "
                      f"status {e.get('status')}, {e.get('wall_s', 0.0):.1f} s", flush=True)
    rec = {"meta": meta, "part": p["part"], "kind": "week", "tag": name, "tags": {name: _job_tag(p)},
           "params": params_rec, "c": c, "modes": list(p["modes"]), "policy_seeds": seeds, "horizon_min": hz,
           "instances": {k: {"instance_hash": v["hash"], "sizes": v["sizes"], "references": v["refs"],
                             "own_capacity_usd": v["own"], "peak_aligned": v["peak_aligned"]}
                         for k, v in insts.items()},
           "lender_models": models, "wall_s": time.perf_counter() - t0, "runs": rows, "errors": e7h._errs(errors)}
    outputs.dump(e7._jsonish(rec), run_path(out, job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": (insts.get("base") or {}).get("hash"),
            "r0": [[r["mode"], r["policy_seed"], r.get("r0")] for r in rows]}


def _job_tag(p: dict) -> dict:
    """A job's tag record (policy id, parameters or the MS5b rule, family)."""
    name = p["tag"]
    par = p["params"] if p["params"] is not None else m5.tag_params_text(name)
    return {"policy_id": p["policy_id"], "params": par, "family": p["family"]}


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    gate(job.params["part"])
    if job.params["kind"] != "week":
        raise ValueError(f"e7r: unknown job kind {job.params['kind']!r}")
    return run_week(job, outputs, out)


# ---------------------------------------------------------------- summaries
def _meta(part: str, js: list, col: dict, selection: Optional[dict]) -> dict:
    d = design()
    names = sorted({j.params["tag"] for j in js})
    tags = {}
    for j in js:
        tags.setdefault(j.params["tag"], _job_tag(j.params))
    for n in names:
        t = m7.tag(n, selection)
        tags[n].update(kind=t.kind, role=t.role, information=t.information)
    ok, why, rec = m7.check_registration()
    m = {"exp": EXP, "part": part, "spec": SPEC, "git_revision": mc.git_revision(), "versions": mc.versions(),
         "written": mc._now(), "reduced": d["reduced"], "design": d, "tags": tags,
         "weeks": sorted({int(j.params["c"]) for j in js}), "modes": sorted({m for j in js for m in j.params["modes"]}),
         "w0_modes": list(m7.W0_MODES), "w0plus_modes": list(m7.W0PLUS_MODES),
         "adaptive_equivalence": m7.ADAPTIVE_EQUIV, "adaptive_note": m7.ADAPTIVE_NOTE, "mode_notes": m7.MODE_NOTES,
         "jobs": len(js), "jobs_ok": len(col["files"]), "jobs_not_ok": col["not_ok"], "ignored_outputs": col["ignored"],
         "n_runs": len(col["rows"]), "n_missing": len(col["missing"]),
         "registration_gate": {"ok": ok, "reason": why, "record": rec}, "selection": _selection_ref(part)}
    if selection is not None:
        m["aliases"] = dict(selection.get("aliases") or {})
    if part == "tune":
        m["families"] = {fam: {"configs": list(m7.grid(fam)), "default": m7.FAMILY_DEFAULT[fam]}
                         for fam in m7.FAMILIES}
    if d["reduced"]:
        m["reduced_note"] = f"reduced job list ({REDUCED_ENV}=1): development cell only; not a result"
    return m


def w0plus_table(table: dict, cells, tags, seed: int = 0) -> dict:
    """{tag: {cell: W0+ or null}} over the tags with a run of every mode of W0PLUS_MODES (ms7_baselines.w0plus_of)."""
    out = {}
    for t in tags:
        by_m = table.get(t) or {}
        if not all(m in by_m for m in m7.W0PLUS_MODES):
            continue
        for cell in cells:
            w, _m, _miss = m7.w0plus_of({m: e7h._val(table, t, m, cell, seed) for m in m7.W0PLUS_MODES})
            out.setdefault(t, {})[cell] = w
    return out


def summary_part(part: str, out_p: Path) -> dict:
    out_p = Path(out_p)
    sel = None if part == "tune" else need_selection()
    js = jobs([part], sel)
    col = e7h.collect(out_p, js)
    s = {"meta": _meta(part, js, col, sel), "runs": col["rows"], "table": col["table"], "missing": col["missing"],
         "guarded": col["guarded"], "guard_summary": e7h.guard_summary(col["guarded"])}
    cells = sorted({num_key(j.params["c"]) for j in js}, key=float)
    tags = sorted(col["table"])
    s["W0"] = {t: v for t, v in e7h.w0_table(col["table"], cells, tags).items()
               if all(m in (col["table"].get(t) or {}) for m in m7.W0_MODES)}
    if part == "eval":
        s["W0plus"] = w0plus_table(col["table"], cells, tags)
    s["RC"] = m5.rc_rows([{**r, "config_seed": r["c"], "policy_seed": r["seed"]} for r in col["rows"]])
    mc.dump_json(e7._jsonish(s), out_p / "summary.json")
    mc.write_text(tables(s), out_p / "tables.md")
    return s


def tables(s: dict) -> str:
    """tables.md: the median over the part's weeks of r0 per tag and mode, W0 (and W0+), and the missing runs."""
    m = s["meta"]
    lines = [f"# E7r part {m['part']} ({SPEC})", ""]
    if m.get("reduced"):
        lines += [f"Reduced run: {m.get('reduced_note')}", ""]
    modes = [x for x in m7.EVAL_MODES if x in m["modes"]]
    rows = []
    for t in sorted(s["table"]):
        by_m = s["table"][t]
        med = []
        for md in modes:
            v = [x.get("0") for x in (by_m.get(md) or {}).values()]
            med.append(e7h._median(v) if md in by_m else None)
        w0 = e7h._median(list((s.get("W0") or {}).get(t, {}).values()))
        w0p = e7h._median(list((s.get("W0plus") or {}).get(t, {}).values()))
        rows.append([t, m["tags"].get(t, {}).get("family")] + med + [w0, w0p])
    lines += ["## Median over the weeks of r0 (cost over BL0a), W0 and W0+", "",
              mc.md_table(["tag", "family"] + modes + ["W0", "W0+"], rows), ""]
    lines += ["## Missing runs", "", mc.md_table(["job", "tag", "mode", "cell", "seed", "why"],
                                                 [[x["job"], x["tag"], x["mode"], x["cell"], x["seed"], x["why"]]
                                                  for x in s["missing"]]), ""]
    return "\n".join(lines) + "\n"


def summary(out) -> dict:
    """The summary of the part whose folder `out` is (its name), else of the one part of E7R_PART."""
    out = Path(out)
    part = out.name if out.name in PARTS else None
    if part is None:
        ps = parts()
        if len(ps) != 1:
            raise ValueError(f"--summary needs one part (E7R_PART) or a part's folder, got {out}")
        part = ps[0]
    return summary_part(part, out)


def _part_of(out) -> Optional[str]:
    out = Path(out)
    if out.name in PARTS:
        return out.name
    ps = parts()
    return ps[0] if len(ps) == 1 else None


SOURCES = ("experiments/e7r.py", "experiments/ms7_baselines.py", "experiments/e7r_select.py",
           "experiments/e7r_analysis.py", "experiments/e7h.py", "experiments/ms5b_common.py", "baselines/mpc.py",
           "baselines/spothedge.py", "baselines/cocar.py", "baselines/ski.py", "baselines/common.py",
           "baselines/greedy.py", "baselines/retrorenting.py", "algos/a9p.py", "algos/a9.py", "algos/guard.py",
           "algos/online_lb.py", "algos/registry.py", "lender.py", "config.py", "drivers/run.py")


def manifest_extra(out) -> dict:
    """The job grid's design, the instance hashes the run files record, the sha256 of the sources of C54 and of the
    selection, and the gate."""
    out = Path(out)
    part = _part_of(out)
    js = jobs([part]) if part is not None else []
    hashes = {}
    for j in js:
        f = mc.read_json(run_path(out, j.id))
        if isinstance(f, dict) and isinstance(f.get("instances"), dict):
            hashes[j.id] = {k: v.get("instance_hash") for k, v in f["instances"].items() if isinstance(v, dict)}
    pkg = Path(__file__).resolve().parents[1]
    return {"part": part, "design": design(), "instance_hashes_from_outputs": hashes,
            "sources_sha256": {f"code/sim/sublet/{f}": (hashlib.sha256((pkg / f).read_bytes()).hexdigest()
                                                       if (pkg / f).is_file() else None) for f in SOURCES},
            "selection": None if part is None else _selection_ref(part),
            "gate": dict(zip(("ok", "reason", "record"), m7.check_registration()))}


# ---------------------------------------------------------------- the missing-run rule's rerun (as e7h's)
def retry_list(out) -> list:
    """The pool jobs of the part to run once more: a record not 'ok', or 'ok' with a run that raised or failed an
    invariant; each one's record moves to retry/ and its output to runs/retry/ first, once per job (e7h.retry_list's
    rule). Returns '<kind> <id>' lines."""
    out = Path(out)
    part = _part_of(out)
    js = [j for j in jobs([part]) if j.kind == "pool"]
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
        mc.dump_json({"job": j.id, "first_record": rec, "moved": mc._now(), "rule": "e7h.retry_list's rule (C54)"},
                     old)
        if mc.record_path(out, j.id).is_file():
            mc.record_path(out, j.id).unlink()
        if path.is_file():
            keep = out / "runs" / "retry" / name
            keep.parent.mkdir(parents=True, exist_ok=True)
            path.rename(keep)
        lines.append(f"{j.kind} {j.id}")
    return lines


# ---------------------------------------------------------------- command line
def check_start(part: str) -> tuple[bool, str]:
    """(ok, line) of --check-start: the gate, and for confirm and eval the selection of the same run kind."""
    try:
        g = gate(part)
    except RuntimeError as err:
        return False, f"REFUSED: {err}"
    if part != "tune":
        try:
            need_selection()
        except RuntimeError as err:
            return False, f"REFUSED: {err}"
    return True, f"gate {'ok' if g['ok'] else 'REFUSED (not enforced)'}: {g['reason']}"


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check-start" in args:
        rc = 0
        for part in parts():
            ok, line = check_start(part)
            print(f"[e7r] {part}: {line}", file=sys.stdout if ok else sys.stderr)
            rc = rc if ok else 1
        return rc
    if "--retry-list" in args:
        ap = argparse.ArgumentParser(prog="python -m sublet.experiments.e7r --retry-list")
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
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=args, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
