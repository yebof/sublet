"""E5 v2: redundancy under correlated reclaims for Sublet itself, A9, the two strongest baselines and SpotHedge with
and without spares (design/ms7/plan.md X3, D6; design/ms7/feasibility/sens.md §2 B, §3 item 2; change C56).
Exploratory, after the MS5b freeze; s1v2's registration gate applies (s1v2.gate).

Instance (§2 B; MS4's E5, design/sim_spec_ms4.md §5.2): e5.e5_instance(menu, mu, c) on configs/bench_e7r.json, one
week of 1-min routing, the menu's contracts (short: the spot-like s5_tau5_H0, H1, H2; long: the AEP-82-like
s5_tau5_H60, H120, H240; both with the config's protected contract), the long menu with the short menu's demand,
engine.check_invariants true; config seed = lender seed = E5 config seed c in 301-304 (the confirmation's E5 seeds,
part second), policy seed 0. The correlation levels are e5.LEVELS (trace, sh0.25, sh0.5, sh1, all1) through
e5.e5_spec's lender model; the level does not change the instance, so one job covers every level of its cell.

Policies (TAGS): Sublet (A8P around A9 at 'lb'), A9, BL1-BO, BL5-cur, BL3-0 (SpotHedge-style, notice-reactive, no
spare) and BL3-2 (BL3 at its default n_extra 2, E5's SpotHedge with spares, s1v2.LOCAL_TAGS); parameters on each
run's own instance (ms5b_common.tag_params). The A6 modes are dropped: they bought no spare (out/e5/summary.json
checks.E5-6), and A9 insures no client on the E5 cells (out/sublet_v2_pilot/p4/summary.json decision.e5_d9).

Grid. At mu / beta~ = 1: 5 levels x 2 menus x 6 tags x 4 seeds; at the default point (trace, short) also mu in
{0.2, 0.5, 2} for Sublet, A9, BL1-BO and BL5-cur. Reused, not rerun (REUSED): part second's E5 runs at the levels
trace and all1 for Sublet, A9, BL3-0 and BL5-cur (e7h's SECOND_E5_TAGS), read from out/sublet_v2/second/
summary.json; each reused tag's job at (short, first seed) reruns the trace level once as an identity run (check
E5v2-0 against second's r0 and its manifest's instance hash), which the tables do not count.

Jobs (pool, ids by ms3_common.job_id):
  e5v2:cell:menu=<menu>:tag=<tag>:c=<c>   the levels the cell owes (all five; for a reused tag sh0.25, sh0.5 and sh1,
                                          with trace as the identity run at the short menu and the first seed)
  e5v2:mu:mu=<mu>:tag=<tag>:c=<c>         the default point (trace, short) at mu
48 cell jobs (176 new runs at mu 1 and 4 identity runs) and 48 mu jobs (48 runs); with second's 64 reused runs the
tables hold 288 runs. Estimates from part second's E5 job walls (EST_RUN_S per run, scaled by the horizon) plus A9's
contract table once per A9-family job.

Command line (ms3_common.main), run from code/sim:
  python -m sublet.experiments.e5v2 --list | --job ID | --summary | --estimate | --manifest | --check-start [--out DIR]
Reduced runs (MS3_E5V2_REDUCED=1, run_e5v2.sh --reduced): development E5 config seed 101 (never a confirmation
seed), a 2-hour horizon, the same job shapes; the gate is recorded, not enforced; never a result.

Outputs <root>/out/e5v2/ (jobs/, logs/, runs/ (not versioned), manifest.json, summary.json, tables.md, run_e5v2.log).
summary.json: meta (grid, tags, menus, levels, the gate, the sources' sha256), runs (rows with level, menu, mu, week,
tag, r0, fallback share after reclaims, guard and A9 facts; identity runs flagged), cells.<level>.<menu>.<mu>.<tag>
{by_c {c: r0}, source 'e5v2' or 'second', n_runs, n_runs_expected} (null for a run missing or failed), missing,
checks E5v2-0 ... E5v2-3. The quantities of the study (per level and menu: each tag's saving, Delta against the H1
pair and against every baseline, the weeks of the ordering) are computed by ms7_sens_analysis.py.

Status labels: as s1v2 (no theory claim; Theorem W, Remark R, Lemma G5', Proposition P as recorded there).
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import hashlib
import sys
import time
from pathlib import Path
from typing import Mapping, Optional

from .. import paths
from . import e5
from . import e7
from . import e7h
from . import ms3_common as mc
from . import ms4_common as m4
from . import ms5b_common as m5
from . import s1v2 as sv
from .ms3_common import Job, job_id, num_key, put

EXP = "e5v2"
SPEC = "design/ms7/feasibility/sens.md §2 B, §3 item 2 (C56)"
TAGS = sv.TAGS4 + ("BL3-0", "BL3-2")
MU_TAGS = sv.TAGS4
LEVELS = tuple(e5.LEVELS)
MENUS = tuple(e5.MENUS)
MU = 1.0
MUS = (0.2, 0.5, 2.0)
DEFAULT_POINT = tuple(e5.DEFAULT_POINT)              # (trace, short)
WEEKS = sv.WEEKS                                     # E5 config seeds 301-304 (e7h.E5_CONF)
REUSED_LEVELS = tuple(e7h.E5_LEVELS)                 # trace, all1: part second's E5 levels
REUSED_TAGS = tuple(t for t in e7h.SECOND_E5_TAGS if t in TAGS)    # Sublet, A9, BL3-0, BL5-cur
IDENTITY = ("short", "trace")                        # the identity run of a reused tag at its first seed
REDUCED_ENV = "MS3_E5V2_REDUCED"
# seconds per E5 week run (part second's e5 jobs, feasibility §4: Sublet 116-152 s, A9 49-65 s, BL5-cur about 20 s;
# BL1 and BL3 as e7h.EST_WEEK_S), A9's table once per A9-family job
EST_RUN_S = {"A8P": 152.0, "A9": 65.0, "BL1": 15.0, "BL5": 20.0, "BL3": 28.6}
EST_TABLE_S = e7h.EST_TABLE_S
EST_JOB_S = 5.0
CHECK_IDS = ("E5v2-0", "E5v2-1", "E5v2-2", "E5v2-3")
CHECK_CLAIMS = {
    "E5v2-0": "every reused tag's identity run (trace level, short menu, first seed) equals part second's run (r0 "
              "within 1e-9 relative) on the instance of second's manifest (equal instance hash), so second's trace "
              "and all1 runs stand for this driver's",
    "E5v2-1": "every run finishes with status ok (no invariant failure), no run raised, every run of the grid exists",
    "E5v2-2": "every Sublet run: certificate available and held in Theorem W's proven cases, the envelope holds, no "
              "projecting run aborts while S follows FB and T0g stays in bound form (Proposition P)",
    "E5v2-3": "per (level, menu) at mu 1 and per mu at the default point, each tag's median r0 and fallback share "
              "after reclaims over the weeks (informative)"}


def reduced() -> bool:
    return os.environ.get(REDUCED_ENV, "0") == "1"


def design() -> dict:
    red = reduced()
    return {"reduced": red, "weeks": (sv.REDUCED_WEEK,) if red else WEEKS, "policy_seeds": sv.POLICY_SEEDS,
            "horizon_min": sv.REDUCED_HORIZON_MIN if red else e5.WEEK_MIN}


def cell_id(menu: str, tag: str, c: int) -> str:
    return job_id(EXP, "cell", menu=menu, tag=tag, c=int(c))


def mu_id(mu: float, tag: str, c: int) -> str:
    return job_id(EXP, "mu", mu=float(mu), tag=tag, c=int(c))


def run_path(out, jid: str) -> Path:
    return Path(out) / "runs" / mc.job_file_name(jid)


def cell_levels(tag: str, menu: str, c: int, first_c: int) -> tuple[list, list]:
    """(the levels a cell job runs, the identity levels among them): every level, or, for a reused tag, those not in
    REUSED_LEVELS plus the identity run at (short, the first seed)."""
    if tag not in REUSED_TAGS:
        return list(LEVELS), []
    lv = [x for x in LEVELS if x not in REUSED_LEVELS]
    ident = [IDENTITY[1]] if (menu, int(c)) == (IDENTITY[0], int(first_c)) else []
    return ident + lv, ident


def est_run_s(name: str) -> float:
    return EST_RUN_S.get(sv.tag_id(name), 20.0)


def jobs() -> list:
    """The cell jobs (menus, tags, seeds), then the mu jobs (mu, tags, seeds)."""
    d = design()
    hz, seeds = d["horizon_min"], list(d["policy_seeds"])
    scale = hz / float(e5.WEEK_MIN)
    first = d["weeks"][0]
    out = []
    for menu in MENUS:
        for t in TAGS:
            for c in d["weeks"]:
                lv, ident = cell_levels(t, menu, c, first)
                est = EST_JOB_S + (EST_TABLE_S if sv.a9_family(t) else 0.0) + len(lv) * scale * est_run_s(t)
                out.append(Job(cell_id(menu, t, c), "pool",
                               {"kind": "cell", "menu": menu, "mu": MU, "tag": t, "c": int(c), "levels": lv,
                                "identity_levels": ident, "policy_seeds": seeds, "horizon_min": hz}, est))
    for mu in MUS:
        for t in MU_TAGS:
            for c in d["weeks"]:
                est = EST_JOB_S + (EST_TABLE_S if sv.a9_family(t) else 0.0) + scale * est_run_s(t)
                out.append(Job(mu_id(mu, t, c), "pool",
                               {"kind": "mu", "menu": DEFAULT_POINT[1], "mu": float(mu), "tag": t, "c": int(c),
                                "levels": [DEFAULT_POINT[0]], "identity_levels": [], "policy_seeds": seeds,
                                "horizon_min": hz}, est))
    return out


def expected_runs(job: Job) -> list:
    """(tag, level, menu, mu key, c, seed, identity) of every run a job owes."""
    p = job.params
    return [(p["tag"], lv, p["menu"], num_key(p["mu"]), int(p["c"]), int(s), lv in p["identity_levels"])
            for lv in p["levels"] for s in p["policy_seeds"]]


def run_cell(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One cell or mu job: e5.e5_instance of (menu, mu, c) built once, then the tag at each level of p['levels'] and
    each policy seed (e7h.one_run through s1v2.run_tag; an identity run is flagged)."""
    p = job.params
    name, menu, mu, c, hz = p["tag"], p["menu"], float(p["mu"]), int(p["c"]), int(p["horizon_min"])
    g = sv.gate(reduced())
    t0 = time.perf_counter()
    inst, _, ecfg, info = e5.e5_instance(menu, mu, c, "trace", horizon_min=hz)
    build_s = time.perf_counter() - t0
    if not ecfg.check_invariants:
        raise RuntimeError("E5 v2 runs need check_invariants=True")
    refs, own = m4.references(inst), e7._own(inst)
    params = sv.tag_params(name, inst)
    errors, rows, models = [], [], {}
    for lv in p["levels"]:
        spec = e5.e5_spec(menu, mu, c, lv, sv.tag_id(name), params, horizon_min=hz)
        for ps in p["policy_seeds"]:
            e, model = sv.run_tag(errors, spec, name, inst, ecfg, refs, own, c, ps, lv)
            models.setdefault(lv, e7._lender_dict(model))
            if e is None:
                continue
            e["identity"] = lv in p["identity_levels"]
            rows.append(e)
            print(f"[e5v2] {job.id} {lv} p{ps}: r0 {e.get('r0')}, status {e.get('status')}, {e['wall_s']:.1f} s"
                  + (" (identity run)" if e["identity"] else ""), flush=True)
    rec = {"meta": {"exp": EXP, "job": job.id, "spec": SPEC, "change": sv.CHANGE, "label": sv.LABEL,
                    "git_revision": mc.git_revision(), "versions": mc.versions(), "written": mc._now(),
                    "reduced": reduced(), "gate": g},
           "kind": p["kind"], "tag": name, "tags": sv.tag_table([name]), "menu": menu, "mu": mu, "c": c,
           "levels": list(p["levels"]), "identity_levels": list(p["identity_levels"]), "horizon_min": hz,
           "params": params, "instance_hash": mc.instance_hash(inst), "instance": e5.instance_info(inst),
           "instance_info": info, "references": refs, "own_capacity_usd": own, "lender_models": models,
           "build_s": build_s, "runs": rows, "errors": sv.errs(errors)}
    outputs.dump(e7._jsonish(rec), run_path(out, job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": rec["instance_hash"],
            "r0": [[r["mode"], r.get("r0")] for r in rows]}


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    if job.params["kind"] in ("cell", "mu"):
        return run_cell(job, outputs, out)
    raise ValueError(f"unknown E5 v2 job {job.id!r}")


def manifest_extra(out) -> dict:
    out = Path(out)
    hashes = {}
    for j in jobs():
        f = mc.read_json(run_path(out, j.id))
        if isinstance(f, dict):
            hashes[j.id] = f.get("instance_hash")
    files = [Path(__file__), Path(e5.__file__), Path(sv.__file__), Path(m5.__file__), sv.ANALYSIS_FILE,
             sv.conf_file("second"), sv.conf_file("second", "manifest.json")] + [Path(f) for f in e5.INPUT_FILES]
    return {"design": {k: (list(v) if isinstance(v, tuple) else v) for k, v in design().items()},
            "instance_hashes_from_outputs": hashes, "gate_record": sv.registration_record(),
            "sources_sha256": {sv._rel_repo(f): (hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None)
                               for f in files}}


# ---------------------------------------------------------------- summary
def second_cell(menu: str, c: int) -> str:
    """The cell key of part second's E5 runs (e7h.cell_key: '<menu>:c<c>')."""
    return f"{menu}:c{int(c)}"


def check_identity(rows: list, files: Mapping, second: Optional[Mapping], second_m: Optional[Mapping],
                   d: Mapping, missing: bool = False) -> dict:
    """E5v2-0: every identity run against part second's r0 (REL_TOL relative) and the job's instance hash against
    second's manifest (instance_hashes_from_outputs of e7h:second:k=e5:menu=<menu>:tag=<tag>:c=<c>)."""
    ih = (second_m or {}).get("instance_hashes_from_outputs") or {}
    cells, bad, miss = {}, [], []
    for r in rows:
        if not r.get("identity"):
            continue
        f = files[r["job"]]
        ref = sv.conf_r0((second or {}).get("table"), r["tag"], r["mode"], second_cell(r["menu"], r["c"]),
                         r["seed"])
        hr = ih.get(f"e7h:second:k=e5:menu={r['menu']}:tag={r['tag']}:c={r['c']}")
        dd = sv.rel_diff(r.get("r0"), ref)
        key = f"{r['tag']}:{r['menu']}:{r['mode']}:c{r['c']}"
        cells[key] = {"r0": r.get("r0"), "r0_second": ref, "rel_diff": dd, "instance_hash": f.get("instance_hash"),
                      "instance_hash_second": hr, "hash_equal": hr is not None and hr == f.get("instance_hash")}
        if ref is None or hr is None:
            miss.append(key)
        elif dd is None or dd > sv.REL_TOL or not cells[key]["hash_equal"]:
            bad.append(key)
    want = {f"{t}:{IDENTITY[0]}:{IDENTITY[1]}:c{d['weeks'][0]}" for t in REUSED_TAGS}
    absent = sorted(want - set(cells))
    st = "fail" if bad else ("missing" if (miss or absent or missing) else "pass")
    out = {"status": st, "claim": CHECK_CLAIMS["E5v2-0"], "tolerance": sv.REL_TOL, "cells": cells, "failures": bad,
           "references_missing": miss, "runs_absent": absent}
    if second is None:
        out["note"] = "part second's summary is missing (or this is a reduced run on a development seed)"
    return out


def summary(out) -> dict:
    out = Path(out)
    d = design()
    js = jobs()
    files, ok, ignored, not_ok = sv.part_outputs(out, js, lambda j: run_path(out, j.id))
    second, second_src = sv.conf_source("second")
    second_m, second_m_src = sv.conf_source("second", "manifest.json")
    rows, have = [], {}
    for jid, f in files.items():
        for e in f.get("runs") or []:
            r = sv.brief(e, job=jid, menu=f["menu"], mu=float(f["mu"]), c=int(f["c"]))
            r.update(level=e.get("mode"), identity=bool(e.get("identity")))
            rows.append(r)
            have[(r["tag"], r["level"], r["menu"], num_key(r["mu"]), r["c"], r["seed"], r["identity"])] = r
    cells: dict = {}
    missing = []

    def put_cell(lv, menu, mk, t, c, v, source):
        x = cells.setdefault(lv, {}).setdefault(menu, {}).setdefault(mk, {}).setdefault(
            t, {"source": source, "by_c": {}})
        x["by_c"][num_key(c)] = v
    for j in js:
        for key in expected_runs(j):
            t, lv, menu, mk, c, s, ident = key
            r = have.get(key)
            good = r is not None and r["status"] == "ok"
            if not good:
                missing.append({"job": j.id, "tag": t, "level": lv, "menu": menu, "mu": mk, "c": c, "seed": s,
                                "identity": ident, "why": r["status"] if r is not None
                                else not_ok.get(j.id, "run missing")})
            if not ident:
                put_cell(lv, menu, mk, t, c, r["r0"] if good else None, EXP)
    for t in REUSED_TAGS:                           # part second's trace and all1 runs (REUSED)
        for lv in REUSED_LEVELS:
            for menu in MENUS:
                for c in d["weeks"]:
                    put_cell(lv, menu, num_key(MU), t, c,
                             sv.conf_r0((second or {}).get("table"), t, lv, second_cell(menu, c)), "second")
    order = {"lv": list(LEVELS), "menu": list(MENUS), "mu": [num_key(MU)] + [num_key(m) for m in MUS], "t": list(TAGS)}
    cells = {lv: {menu: {mk: {t: cells[lv][menu][mk][t] for t in order["t"] if t in cells[lv][menu][mk]}
                         for mk in order["mu"] if mk in cells[lv][menu]}
                  for menu in order["menu"] if menu in cells[lv]}
             for lv in order["lv"] if lv in cells}                 # in the order of LEVELS, MENUS, mu, TAGS
    for lv, a in cells.items():
        for menu, b in a.items():
            for mk, x in b.items():
                for t, e in x.items():
                    vals = [v for v in e["by_c"].values() if v is not None]
                    e.update(n_runs=len(vals), n_runs_expected=len(d["weeks"]))
    fsh = {}
    for r in rows:
        if r["status"] == "ok" and not r["identity"]:
            fsh.setdefault((r["level"], r["menu"], num_key(r["mu"]), r["tag"]), []).append(
                r.get("fallback_share_after_reclaims"))
    info = {}
    for (lv, menu, mk, t), v in sorted(fsh.items()):
        info.setdefault(lv, {}).setdefault(menu, {}).setdefault(mk, {})[t] = {
            "median_r0": e7h._median((cells.get(lv, {}).get(menu, {}).get(mk, {}).get(t) or {}).get("by_c", {})
                                     .values()),
            "median_fallback_share_after_reclaims": e7h._median(v)}
    miss_ok = bool(not_ok)
    sub = [r for r in rows if r.get("guard")]
    checks = {"E5v2-0": check_identity(rows, files, second, second_m, d, miss_ok),
              "E5v2-1": {"claim": CHECK_CLAIMS["E5v2-1"],
                         **sv.clean_check(rows, sv.run_errors_of(files), missing, not_ok, miss_ok)},
              "E5v2-2": {"claim": CHECK_CLAIMS["E5v2-2"], **sv.guard_check(sub, miss_ok)},
              "E5v2-3": {"status": "informative", "claim": CHECK_CLAIMS["E5v2-3"], "by_level_menu_mu": info}}
    meta = sv.meta_common(EXP, None, SPEC, d["reduced"],
                          grid={"levels": list(LEVELS), "menus": list(MENUS), "mu": MU, "mus": list(MUS),
                                "default_point": list(DEFAULT_POINT), "weeks": list(d["weeks"]),
                                "weeks_design": list(WEEKS), "policy_seeds": list(d["policy_seeds"]),
                                "horizon_min": d["horizon_min"]},
                          tags=sv.tag_table(TAGS), mu_tags=list(MU_TAGS), h1_pair=list(sv.H1_PAIR),
                          reused={"tags": list(REUSED_TAGS), "levels": list(REUSED_LEVELS), "part": "second",
                                  "identity": list(IDENTITY)},
                          levels={lv: e5.level_lender_model(lv) for lv in LEVELS},
                          menus={mn: {"contracts": e5.menu_contracts(mn), "class": e5.MENU_CLASS[mn]}
                                 for mn in MENUS},
                          sources={"second": second_src, "second_manifest": second_m_src},
                          jobs=len(js), jobs_ok=len(ok), jobs_not_ok=not_ok, ignored_outputs=ignored,
                          n_runs=len(rows), n_missing=len(missing))
    if d["reduced"]:
        meta["reduced_note"] = (f"reduced job list ({REDUCED_ENV}=1): E5 config seed {sv.REDUCED_WEEK}, a "
                                f"{sv.REDUCED_HORIZON_MIN}-min horizon; not a result")
    s = {"meta": meta, "runs": rows, "cells": cells, "missing": missing, "checks": {k: checks[k] for k in CHECK_IDS}}
    mc.dump_json(e7._jsonish(s), out / "summary.json")
    mc.write_text(tables(s), out / "tables.md")
    return s


def tables(s: dict) -> str:
    m = s["meta"]
    L = [f"# E5 v2 ({SPEC})", "", f"*{sv.LABEL}*", ""]
    if m.get("reduced"):
        L += [f"Reduced run: {m.get('reduced_note')}", ""]
    rows = []
    for lv, a in s["cells"].items():
        for menu, b in a.items():
            for mk, x in b.items():
                for t, e in x.items():
                    rows.append([lv, menu, mk, t, e["source"], e["n_runs"], e7h._median(e["by_c"].values())])
    L += ["## Cells (median r0 over the weeks; source e5v2 or second)", "",
          mc.md_table(["level", "menu", "mu", "tag", "source", "runs", "median r0"], rows), ""]
    L += ["## Checks", "", mc.md_table(["check", "status"], [[k, v.get("status")] for k, v in s["checks"].items()]),
          ""]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check-start" in args:
        return sv.check_start(EXP, reduced())
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=args, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
