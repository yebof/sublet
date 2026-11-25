"""E8q (X7): E8 v2's request-level replay with a FIFO queue and a waiting limit W (design/ms8/plan.md D1;
design/ms8/scout_x7_queue.md §2-§4). Exploratory: registered in design/ms8/registration.md before it runs (the gate
below), run once in a clean clone of the run commit and copied into code/sim/out/e8q/; nothing here is a
confirmation result.

Instance, tags and fluid runs: E8 v2 part (a)'s, unchanged (e8v2.py's module docstring; its builders are reused:
e8v2.build, e8v2.fluid_run, e8v2.overrides, e8v2.run_spec): configs/bench_e1.json with E1's menu, 1-min routing, one
week, one `series` borrower azure0 (azure2024_conv, week 0, own capacity at P75, market tightness 0.5), the tier t in
{S, M, L} as its LLM, smoothing window in {5, 15, 60} min, the trace lender (I1, 'sell', 'absorb'), mu / beta~ = 1,
alignments c in {1, 2, 3, 4} (config seed = lender seed = copier seed = c), policy seed 0. Tags (TAGS): Sublet (A8P
around A9 at 'lb'), A9, BL1-BO, BL5-cur; BL0a's zero placement gives the replayed all-fallback bill (BILL; own
capacity, then fallback, with the same queue).

Replay (sublet.replay.queue): one QCopier per cell feeds, in lockstep, one QueueReplay state per (tag, W) and one per
(BILL, W), W in WAITS = {0, 1, 2.5, 10} s (W* = 2.5 s, DistServe's chatbot TTFT SLO of the 66B LLM,
literature/papers/zhong2024distserve Table 1), so every state sees the same copies (E8 v2's copies: QCopier draws as
scale.Copier). At W = 0 a state is loop.replay, so its C_fluid and C_replay must equal E8 v2's stored pair (check Q-0
of e8q_analysis.py against out/e8v2/a/summary.json). Per state: the costs (C_replay = the fluid run's lease and
loading plus the replay's routing, fallback and stranding, e8.cost_error), E = (C_replay - C_fluid) / C_replay, the
counts (own, leased, immediate fallback, reneged, still queued at the end, stranded, queued, served after waiting),
the fallback split by the fluid demand of its fast slot (d(f) = 0 or > 0), the counters and TTFT histograms per window
class (queue.window_classes of the tag's fluid run: reclaim, load, overflow, base; the bill: overflow and base) and
conservation. Per tag also the fluid components, lease spend and headroom (queue.headroom).

Jobs (pool, ids by ms3_common.job_id; run_e8q.sh runs e8q:requests first, then the first cell job alone, timed, then
the rest):
  e8q:requests                   the request cache runs/requests/ (e8v2's: the Azure 2024 conversation week)
  e8q:cell:tier=T:win=W:c=C      the four fluid runs (E8-2, E8-3, classes, headroom), then one lockstep replay of the
                                 week with 4 x 4 + 4 states; record runs/cells/<job>.json (36 jobs)
Reduced job list (MS3_E8Q_REDUCED=1 together with MS3_E8V2_REDUCED=1, run_e8q.sh --reduced): E8 v2's reduced instance
(6 hours at market tightness 0.05), tiers S, M, L, windows 5 and 60, alignment 1; a smoke run, never a result (the
gate is recorded, not enforced).

Gate (design/ms8/plan.md D4): a full job refuses to start unless design/ms8/registration.md exists at HEAD with the
line 'e8q_analysis_sha256: <64 hex>', the sha256 of experiments/e8q_analysis.py on disk and at HEAD equals it, and
the working tree is clean (ms5b_common.dirty_paths: untracked files under code/sim/out/ do not count).

Outputs <root>/out/e8q/ (jobs/, logs/, runs/ (not versioned: requests/, cells/), manifest.json, summary.json,
hist.json, tables.md, run_e8q.log). summary.json: meta (grid, tags, waits, service models, the gate, sources), cells.
<tier>.<win>.<c>.<tag> {C_fluid, fluid, lease_usd, headroom, classes, e8_2_pass, e8_3_pass, status, guard, e8v2
(E8 v2's stored C_fluid and C_replay), by_W.<W> {C_replay, error, gap_usd, replay, counts, tokens,
fallback_by_demand, by_class, conservation_pass}} and cells.<tier>.<win>.<c>.BL0a (the bill), checks E8q-1 ... E8q-4.
hist.json (compact): the TTFT histograms pooled over windows and alignments, tiers.<tier>.<tag>.<W>.<class>.<kind>
(queue.sparse), the input of Q-2. The analysis (python -m sublet.experiments.e8q_analysis) runs after run_e8q.sh.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import copy
import gc
import hashlib
import re
import sys
import time
from pathlib import Path
from typing import Mapping, Optional

import numpy as np

from .. import paths
from . import e7
from . import e7h
from . import e8
from . import e8v2
from . import ms3_common as mc
from . import ms4_common as m4
from . import ms5b_common as m5
from . import s1v2 as sv
from .ms3_common import Job, job_id, num_key

EXP = "e8q"
SPEC = "design/ms8/plan.md D1; design/ms8/scout_x7_queue.md §2-§4 (X7)"
LABEL = "exploratory: E8 v2's replay with a queue, registered in design/ms8/registration.md, not a confirmation result"
TAGS = sv.TAGS4
BILL = "BL0a"
WAITS = (0.0, 1.0, 2.5, 10.0)
W_STAR = 2.5
MU = e8v2.MU
TIERS, WINDOWS, ALIGNMENTS = e8v2.TIERS, e8v2.WINDOWS, e8v2.ALIGNMENTS
REDUCED_ENV = "MS3_E8Q_REDUCED"
E8V2_SUMMARY = paths.SIM_OUT / "e8v2" / "a" / "summary.json"      # versioned (MS7, commit 44d1b4e4)
E8V2_SUMMARY_REL = "code/sim/out/e8v2/a/summary.json"
REL_TOL = 1e-9
# the registration (D4): design/ms8/registration.md records the analysis script's sha256 on this line
REGISTRATION = "design/ms8/registration.md"
ANALYSIS = Path(__file__).resolve().parent / "e8q_analysis.py"
ANALYSIS_REL = "code/sim/sublet/experiments/e8q_analysis.py"
REG_KEY = "e8q_analysis_sha256"
REG_SHA_RE = re.compile(r"^e8q_analysis_sha256:\s*([0-9a-f]{64})\s*$", re.MULTILINE)
GATE_KIND = "ms8_registration"
# provisional estimates of one full cell job (seconds, not a result): wall times of single full-scale cell jobs of
# this build, (S, 60, 1), (M, 15, 1) and (L, 5, 1), run two or three at a time under a host load of 13-26 on 12
# threads (peak RSS 562, 714 and 964 MB; scratch, not versioned); the timed first cell job of the run replaces them
EST_CELL_S = {"S": 1720.0, "M": 1150.0, "L": 620.0}
CHECK_IDS = ("E8q-1", "E8q-2", "E8q-3", "E8q-4")
CHECK_CLAIMS = {
    "E8q-1": "conservation in every replay state (every copy served once by own capacity, a leased replica or "
             "fallback, immediately, after reneging or at the end; per window class too; tokens to 1e-9 relative; "
             "the copier's counters)",
    "E8q-2": "fluid mode in every tag's run (E8-2: 1e-6 relative)",
    "E8q-3": "every fluid run: invariant_failures empty, gpu_only_lease_slots 0 (E8-3)",
    "E8q-4": "every Sublet run: certificate available and held in Theorem W's proven cases, the envelope holds, no "
             "projecting run aborts while S follows FB and T0g stays in bound form (Proposition P)"}


# ---------------------------------------------------------------- settings
def reduced() -> bool:
    return os.environ.get(REDUCED_ENV, "0") == "1"


def settings() -> dict:
    """E8 v2's grid (e8v2.settings); RuntimeError unless MS3_E8Q_REDUCED and MS3_E8V2_REDUCED agree, since the
    instance comes from e8v2's builders."""
    if reduced() != e8v2.reduced():
        raise RuntimeError(f"{REDUCED_ENV} and {e8v2.REDUCED_ENV} must agree (both 1 for a reduced run, run_e8q.sh "
                           f"--reduced sets both)")
    S = dict(e8v2.settings())
    S["waits"] = WAITS
    return S


def cell_id(tier: str, win: int, c: int) -> str:
    return job_id(EXP, "cell", tier=tier, win=int(win), c=int(c))


def requests_id() -> str:
    return job_id(EXP, "requests")


def cache_dir(out) -> Path:
    return Path(out) / "runs" / "requests"


def run_path(out, jid: str) -> Path:
    return Path(out) / "runs" / "cells" / mc.job_file_name(jid)


def wkey(w: float) -> str:
    return num_key(w)


def jobs() -> list:
    """e8q:requests, then the cell jobs (tiers S, M, L; windows from the largest; alignments): the first, the one
    with the most copies, is the one run_e8q.sh times alone."""
    S = settings()
    scale = S["horizon_min"] / e8.WEEK_MIN
    out = [Job(requests_id(), "pool", {"kind": "requests", "horizon_min": S["horizon_min"]}, est_s=e8.EST_REQUESTS_S)]
    for t in S["tiers"]:
        for w in sorted(S["windows"], reverse=True):
            for c in S["alignments"]:
                out.append(Job(cell_id(t, w, c), "pool",
                               {"kind": "cell", "tier": t, "win": int(w), "mu": MU, "c": int(c), "tags": list(TAGS),
                                "bill": BILL, "waits": list(WAITS)},
                               est_s=10.0 + scale * EST_CELL_S[t]))
    return out


# ---------------------------------------------------------------- the gate (D4)
_GATE: dict = {}


def analysis_sha256() -> Optional[str]:
    return m5._sha(ANALYSIS.read_bytes()) if ANALYSIS.is_file() else None


def registered_sha256(text: Optional[str]) -> Optional[str]:
    """The analysis script's sha256 that the registration records (its line 'e8q_analysis_sha256: <64 hex>');
    None without such a line."""
    if not text:
        return None
    m = REG_SHA_RE.search(text)
    return m.group(1) if m else None


def registration_record() -> dict:
    """The gate's facts (read-only git): HEAD, whether design/ms8/registration.md exists at HEAD, its sha256 and the
    analysis sha256 it records, the sha256 of e8q_analysis.py at HEAD and on disk, and the dirty paths."""
    reg = m5.file_at("HEAD", REGISTRATION)
    return {"head": m5.head_commit(), "registration": REGISTRATION, "registration_at_head": reg is not None,
            "registration_sha256": m5._sha(reg), "analysis": ANALYSIS_REL,
            "analysis_sha256_registered": registered_sha256(None if reg is None else reg.decode("utf-8", "replace")),
            "analysis_sha256_head": m5._sha(m5.file_at("HEAD", ANALYSIS_REL)),
            "analysis_sha256_disk": analysis_sha256(), "dirty_paths": m5.dirty_paths()}


def check_registration(rec: Optional[Mapping] = None) -> tuple[bool, str, dict]:
    """(ok, reason, record): a full run starts only if design/ms8/registration.md exists at HEAD, the working tree is
    clean and the sha256 of e8q_analysis.py, on disk and at HEAD, equals the registered one (D4)."""
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
        return False, "E8q does not start (design/ms8/plan.md D4): " + "; ".join(why), rec
    return True, "registration at HEAD, clean tree, analysis sha256 as registered", rec


def gate_state() -> dict:
    """The gate's record, taken once per process: {kind, ok, reason, enforced (full runs), registration}; never
    raises (summaries and manifests record it)."""
    key = reduced()
    if key not in _GATE:
        ok, why, rec = check_registration()
        g = {"kind": GATE_KIND, "ok": ok, "reason": why, "enforced": not key, "registration": rec}
        if key:
            g["note"] = "reduced run: the gate is recorded, not enforced"
        _GATE[key] = g
    return _GATE[key]


def gate() -> dict:
    """The gate of a job: enforced in full runs (RuntimeError when refused), recorded in reduced runs."""
    g = gate_state()
    if g["enforced"] and not g["ok"]:
        raise RuntimeError(g["reason"])
    return g


def check_start() -> int:
    """--check-start: the gate's line; 1 if a full run is refused."""
    try:
        g = gate()
    except RuntimeError as err:
        print(f"[{EXP}] REFUSED: {err}", file=sys.stderr)
        return 1
    print(f"[{EXP}] gate {'ok' if g['ok'] else 'REFUSED (not enforced)'}: {g['reason']}")
    return 0


def _meta(job_name: str) -> dict:
    return {"exp": EXP, "job": job_name, "spec": SPEC, "label": LABEL, "git_revision": mc.git_revision(),
            "versions": mc.versions(), "written": mc._now(), "reduced": reduced(), "gate": gate_state()}


# ---------------------------------------------------------------- jobs
def prefill_tok_per_s(svc) -> float:
    """a5's prefill_tok_per_s_per_replica of the service model's a5 tier (P_j of the TTFT model)."""
    from .. import calib
    return float(calib.A5["assumptions"]["prefill_tok_per_s_per_replica"][svc.a5_tier])


def run_requests(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """The request cache (e8v2.run_requests's steps with this driver's gate): the Azure 2024 conversation week, or its
    first horizon_min minutes, as the three .npy files and their record."""
    from ..replay import requests as rq
    from ..traces.borrowers import REQUEST_STREAMS
    g = gate()
    hz = int(job.params["horizon_min"])
    dur = None if hz >= e8.WEEK_MIN else 60.0 * hz
    t0 = time.perf_counter()
    arrs = rq.load_azure(dur, e8.SERIES)
    load_s = time.perf_counter() - t0
    pth = rq.cache_paths(cache_dir(out), e8.SERIES)
    t1 = time.perf_counter()
    for k in rq.CACHE_KEYS:
        rq.save_npy(arrs[k], outputs.partial(pth[k]))
    stats = rq.stream_stats(arrs["t_s"], arrs["inp"], arrs["out"])
    meta = {"stream": e8.SERIES, "window": {"t0_s": 0.0, "dur_s": dur}, **stats,
            "sha256": {k: rq.array_sha256(arrs[k]) for k in rq.CACHE_KEYS},
            "array_bytes": int(sum(v.nbytes for v in arrs.values())), "dtype": "float64",
            "files": {k: pth[k].name for k in rq.CACHE_KEYS},
            "source": rq.file_info(paths.DATA / REQUEST_STREAMS[e8.SERIES][1]),
            "load_s": load_s, "save_s": time.perf_counter() - t1, "reduced": reduced(),
            "git_revision": mc.git_revision(), "versions": mc.versions(), "job": job.id, "gate": g}
    outputs.dump(meta, pth["meta"])
    print(f"[e8q] {job.id}: {stats['rows']} requests in {load_s:.1f} s", flush=True)
    return {"runs": 0, "rows": stats["rows"], "load_s": load_s}


def _state_brief(r: Mapping) -> dict:
    """A replay state's result without its per-hour series (kept) and with its histograms (kept)."""
    return {k: r[k] for k in ("wait_s", "counts", "tokens", "costs", "fallback_by_demand", "by_class", "wait_hist",
                              "conservation", "per_hour", "timing", "hold_max_s", "ring_s", "own_slots")}


def run_cell(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One (tier, window, alignment): the instance once; per tag the fluid run, E8-3, E8-2's fluid mode, the window
    classes and headroom; then one lockstep replay of the horizon through every (tag, W) and (BILL, W) state; the
    record runs/cells/<job>.json."""
    from .. import replay as rp
    from ..replay import queue as rq
    p = job.params
    tier, win, mu, c = p["tier"], int(p["win"]), float(p["mu"]), int(p["c"])
    waits = tuple(float(w) for w in p["waits"])
    g = gate()
    t_job = time.perf_counter()
    inst, _, ecfg = e8v2.build(tier, win, mu, c)
    ih = mc.instance_hash(inst)
    svc = rp.service_model(inst)
    ms = rp.market_scale(inst, svc.n_seq)
    P = prefill_tok_per_s(svc)
    arrs, cmeta = rp.open_cache(cache_dir(out), e8.SERIES)
    n_sec = 60 * inst.grid.horizon_min
    e8._cache_check(cmeta, n_sec)
    idx = rp.StreamIndex.build(arrs["t_s"], n_sec)
    ring = rp.ring_size(svc.w_in * float(cmeta["max_inp"]) + float(cmeta["max_out"]), svc)
    refs, own = m4.references(inst), e7._own(inst)
    d = np.asarray(inst.clients.demand[0], dtype=np.float64)
    errors, fluid, plans = [], {}, {}
    for name in p["tags"]:
        def one(name=name):
            res, e, pol = e8v2.fluid_run(name, inst, ecfg, tier, win, mu, c, refs, own)
            chk3 = e8.e8_3(res)
            plan = rp.placement(res, inst)
            chk2 = rp.check_e8_2(res, inst, plan, svc)
            cls = rq.window_classes(res, inst)
            fl = e8._fluid_components(res.components)
            x = {"tag": name, "policy": pol, "seeds": dict(res.seeds), "fluid": fl,
                 "fluid_components": {k: float(v) for k, v in res.components.items()},
                 "lease_usd": fl["lease"] + fl["loading"], "headroom": rq.headroom(plan, d),
                 "classes": rq.class_counts(cls), "e8_2": chk2, "e8_3": chk3, "n_leases": len(res.leases),
                 "n_replicas": len(res.replicas), "n_announced": sum(1 for L in res.leases
                                                                       if L.announce_slot is not None),
                 "fluid_s": pol["fluid_s"], "entry": e8v2._entry_brief(e)}
            print(f"[e8q] {job.id} {name}: C_fluid {fl['total']:.2f}, E8-2 {chk2['pass']}, E8-3 {chk3['pass']}, "
                  f"classes {x['classes']}; fluid {pol['fluid_s']:.1f} s", flush=True)
            return x, plan, cls
        r = mc.try_run(errors, f"{name} {tier} w{win} c{c}", one)
        gc.collect()
        if r is not None:
            fluid[name], plans[name] = r[0], (r[1], r[2])
    states, keys = [], []
    for name in list(fluid):
        plan, cls = plans[name]
        for w in waits:
            states.append(rq.QueueReplay(plan, svc, ms.own_slots, ring, w, cls, d, P, n_sec))
            keys.append((name, w))
    zp = rq.zero_placement(next(iter(plans.values()))[0]) if plans else None
    if zp is None:                     # no tag ran: the bill alone, from the instance
        zp = rq.zero_placement(_placement_of_instance(inst))
    bcls = rq.demand_classes(d)
    for w in waits:
        states.append(rq.QueueReplay(zp, svc, ms.own_slots, ring, w, bcls, d, P, n_sec))
        keys.append((BILL, w))
    del plans
    gc.collect()
    t1 = time.perf_counter()
    copier = rq.QCopier(arrs["t_s"], arrs["inp"], arrs["out"], idx, ms.gamma, svc.w_in, seed=c)
    lock = rq.run_lockstep(copier, states, n_sec, P, progress_s=86400,
                           log=lambda m: print(f"[e8q] {job.id} {m}", flush=True))
    replay_s = time.perf_counter() - t1
    by_tag: dict = {}
    bl0a = float(refs["bl0a_usd"])
    for (name, w), st in zip(keys, states):
        rr = st.finish(lock["copier"])
        if name == BILL:
            fl = {k: 0.0 for k in e8.COMPONENTS}
            fl.update(fallback=bl0a, total=bl0a)
        else:
            fl = fluid[name]["fluid"]
        err = e8.cost_error(fl, rr["costs"])
        ent = by_tag.setdefault(name, fluid.get(name) or {"tag": BILL, "fluid": fl, "lease_usd": 0.0,
                                                            "classes": rq.class_counts(bcls),
                                                            "note": "BL0a's zero placement: no fluid run, C_fluid "
                                                                    "is the fluid BL0a (references.bl0a_usd)"})
        ent.setdefault("by_W", {})[wkey(w)] = {**err, "gap_usd": err["C_replay"] - err["C_fluid"],
                                              **_state_brief(rr)}
        print(f"[e8q] {job.id} {name} W {w:g}: C_replay {err['C_replay']:.2f}, E {err['error']}, fallback "
              f"{rr['counts']['fallback']} (reneged {rr['counts']['fallback_reneged']}), conservation "
              f"{rr['conservation']['pass']}", flush=True)
    del states
    rec = {"meta": _meta(job.id), "job": job.id, "kind": "cell", "tier": tier, "win": win, "mu": mu, "c": c,
           "policy_seed": e8.POLICY_SEED, "tags": list(p["tags"]), "bill": BILL, "waits": list(waits),
           "tag_table": sv.tag_table(p["tags"]), "config": e8.CONFIG, "overrides": e8v2.overrides(tier, win, mu),
           "instance_hash": ih, "horizon_min": inst.grid.horizon_min, "references": refs, "own_capacity_usd": own,
           "service": svc.record(), "scale": ms.record(), "prefill_tok_per_s": P,
           "demand": {"slots": int(len(d)), "positive_slots": int(np.sum(d > 0))},
           "runs": by_tag, "lockstep": {"copier": lock["copier"], "timing": lock["timing"], "replay_s": replay_s,
                                        "n_states": len(keys)},
           "cache": {k: cmeta.get(k) for k in ("rows", "window", "sha256")}, "errors": sv.errs(errors),
           "git_revision": mc.git_revision(), "wall_s": time.perf_counter() - t_job}
    outputs.dump(e7._jsonish(rec), run_path(out, job.id), compact=True)
    return {"runs": len(fluid), "errors": errors, "instance_hash": ih, "replay_s": replay_s,
            "E": {t: {k: x.get("error") for k, x in (by_tag.get(t) or {}).get("by_W", {}).items()}
                  for t in list(fluid) + [BILL]}}


def _placement_of_instance(inst):
    """A placement of the one-client instance without a run (the bill's, when no tag ran): W = 0."""
    from ..replay.loop import Placement
    j = int(inst.clients.llm[0])
    dd = np.asarray(inst.clients.delta_usd_per_h[0], dtype=np.float64)
    return Placement(W=np.zeros((inst.m, inst.grid.T_fast)), delta=np.where(np.isfinite(dd), dd, 0.0),
                     ok=np.zeros(inst.m, dtype=bool), q=float(inst.llms[j].q_usd_per_h),
                     mu_fb=float(inst.stranding.mu_fb_usd[j]), fast_min=int(inst.grid.fast_min),
                     site_ids=tuple(s.id for s in inst.sites))


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    fn = {"requests": run_requests, "cell": run_cell}[job.params["kind"]]
    return fn(job, outputs, out)


def manifest_extra(out) -> dict:
    from ..replay.requests import file_info
    from ..traces.borrowers import REQUEST_STREAMS
    out = Path(out)
    hashes = {}
    for j in jobs():
        if j.params["kind"] == "cell":
            f = mc.read_json(run_path(out, j.id))
            if isinstance(f, dict):
                hashes[j.id] = f.get("instance_hash")
    here = Path(__file__).resolve().parent
    files = [Path(__file__), ANALYSIS, here.parent / "replay" / "queue.py", here.parent / "replay" / "loop.py",
             here.parent / "replay" / "scale.py", Path(e8v2.__file__), Path(e8.__file__), Path(sv.__file__),
             E8V2_SUMMARY, paths.CONFIGS / e8.CONFIG, paths.ANALYSIS_OUT / "a12_minute_io.npz",
             paths.ANALYSIS_OUT / "a12_sim_inputs.json", paths.ANALYSIS_OUT / "a5_reclaim_cost_calibration.json"]
    return {"settings": {k: (list(v) if isinstance(v, tuple) else v) for k, v in settings().items()},
            "instance_hashes_from_outputs": hashes, "gate_record": registration_record(),
            "raw_azure": file_info(paths.DATA / REQUEST_STREAMS[e8.SERIES][1]),
            "sources_sha256": {sv._rel_repo(f): (hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None)
                               for f in files}}


# ---------------------------------------------------------------- summary
def _by_w_brief(x: Mapping) -> dict:
    """A state's row in the summary (no histograms, no per-hour series)."""
    bc = {k: {kk: vv for kk, vv in v.items() if kk != "hist"} for k, v in (x.get("by_class") or {}).items()}
    return {"C_fluid": x.get("C_fluid"), "C_replay": x.get("C_replay"), "error": x.get("error"),
            "gap_usd": x.get("gap_usd"), "replay": x.get("costs"), "counts": x.get("counts"), "tokens": x.get("tokens"),
            "fallback_by_demand": x.get("fallback_by_demand"), "by_class": bc,
            "conservation_pass": (x.get("conservation") or {}).get("pass"),
            "wall_s": (x.get("timing") or {}).get("wall_s")}


def _tag_cell(x: Mapping) -> dict:
    ent = x.get("entry") or {}
    out = {k: x.get(k) for k in ("C_fluid", "fluid", "lease_usd", "headroom", "classes", "n_leases", "n_announced",
                                 "fluid_s", "note")}
    out["C_fluid"] = (x.get("fluid") or {}).get("total")
    out["e8_2_pass"] = (x.get("e8_2") or {}).get("pass") if x.get("e8_2") is not None else None
    out["e8_3_pass"] = (x.get("e8_3") or {}).get("pass") if x.get("e8_3") is not None else None
    out["status"] = ent.get("status") if ent else ("ok" if x.get("tag") == BILL else None)
    gb = e7h.guard_brief(ent.get("a8")) if ent else None
    if gb is not None:
        out["guard"] = gb
    out["by_W"] = {w: _by_w_brief(y) for w, y in (x.get("by_W") or {}).items()}
    return {k: v for k, v in out.items() if v is not None or k in ("C_fluid", "status")}


def _e8v2_ref(s: Optional[Mapping], S: Mapping) -> tuple:
    """({tier: {win: {c: {tag: {C_fluid, C_replay}}}}} of E8 v2's summary on the same grid, or {}), same_scale."""
    g = ((s or {}).get("meta") or {}).get("grid") or {}
    same = s is not None and g.get("horizon_min") == S["horizon_min"] and \
        g.get("market_tightness") == S["market_tightness"]
    out: dict = {}
    if not same:
        return out, False
    for t, a in (s.get("cells") or {}).items():
        for w, b in a.items():
            for c, x in b.items():
                for tg in TAGS:
                    v = x.get(tg) or {}
                    out.setdefault(t, {}).setdefault(w, {}).setdefault(c, {})[tg] = {
                        "C_fluid": v.get("C_fluid"), "C_replay": v.get("C_replay")}
    return out, True


def summary(out) -> dict:
    from ..replay import queue as rq
    out = Path(out)
    S = settings()
    js = jobs()
    cjs = [j for j in js if j.params["kind"] == "cell"]
    files, ok, ignored, not_ok = sv.part_outputs(out, cjs, lambda j: run_path(out, j.id))
    e8s = mc.read_json(E8V2_SUMMARY)
    src = {"file": E8V2_SUMMARY_REL, "exists": E8V2_SUMMARY.is_file(),
           "sha256": hashlib.sha256(E8V2_SUMMARY.read_bytes()).hexdigest() if E8V2_SUMMARY.is_file() else None,
           "git_revision": ((e8s or {}).get("meta") or {}).get("git_revision")}
    ref, same_scale = _e8v2_ref(e8s, S)
    cells, missing, rows, hist = {}, [], [], {}
    for j in cjs:
        p = j.params
        f = files.get(j.id) or {}
        runs = f.get("runs") or {}
        for t in list(p["tags"]) + [BILL]:
            x = runs.get(t)
            cell = _tag_cell(x) if x is not None else None
            if cell is None or cell.get("status") != "ok" or set(cell.get("by_W") or {}) != {wkey(w) for w in WAITS}:
                missing.append({"job": j.id, "tag": t, "why": (cell or {}).get("status") or not_ok.get(j.id)
                                or "run missing"})
            if cell is not None and t != BILL:
                cell["e8v2"] = (((ref.get(p["tier"]) or {}).get(num_key(p["win"])) or {}).get(num_key(p["c"])) or
                                {}).get(t)
            tgt = cells.setdefault(p["tier"], {}).setdefault(num_key(p["win"]), {}).setdefault(num_key(p["c"]), {})
            tgt[t] = cell
            if x is None:
                continue
            if cell.get("guard"):
                rows.append({"job": j.id, "tag": t, "guard": cell["guard"]})
            for w, y in (x.get("by_W") or {}).items():
                for cn, z in (y.get("by_class") or {}).items():
                    for kn, sp in (z.get("hist") or {}).items():
                        h = hist.setdefault(p["tier"], {}).setdefault(t, {}).setdefault(w, {}).setdefault(cn, {})
                        h[kn] = h.get(kn, 0) + rq.dense(sp)
    hist_out = {t: {tg: {w: {cn: {kn: rq.sparse(np.asarray(h)) if not isinstance(h, int) else None
                                  for kn, h in b.items()} for cn, b in a.items()} for w, a in y.items()}
                    for tg, y in x.items()} for t, x in hist.items()}
    allx = [(jid, t, w, y) for jid, f in files.items() for t, x in (f.get("runs") or {}).items()
            for w, y in (x.get("by_W") or {}).items()]
    tagx = [(jid, t, x) for jid, f in files.items() for t, x in (f.get("runs") or {}).items() if t != BILL]
    f1 = [f"{j}:{t}:W{w}" for j, t, w, y in allx if not (y.get("conservation") or {}).get("pass")]
    f2 = [f"{j}:{t}" for j, t, x in tagx if not (x.get("e8_2") or {}).get("pass")]
    f3 = [f"{j}:{t}" for j, t, x in tagx if not (x.get("e8_3") or {}).get("pass")]
    miss = bool(not_ok) or bool(missing)
    checks = {"E8q-1": {"status": sv.status_of(bool(f1), len(allx), miss), "claim": CHECK_CLAIMS["E8q-1"],
                        "n": len(allx), "failures": f1[:50],
                        "max_tokens_rel_diff": max(((y.get("conservation") or {}).get("tokens_rel_diff") or 0.0
                                                    for _j, _t, _w, y in allx), default=None)},
              "E8q-2": {"status": sv.status_of(bool(f2), len(tagx), miss), "claim": CHECK_CLAIMS["E8q-2"],
                        "n": len(tagx), "failures": f2[:50]},
              "E8q-3": {"status": sv.status_of(bool(f3), len(tagx), miss), "claim": CHECK_CLAIMS["E8q-3"],
                        "n": len(tagx), "failures": f3[:50]},
              "E8q-4": {"claim": CHECK_CLAIMS["E8q-4"], **sv.guard_check(rows, miss)}}
    meta = {"exp": EXP, "spec": SPEC, "label": LABEL, "git_revision": mc.git_revision(), "versions": mc.versions(),
            "written": mc._now(), "reduced": bool(S["reduced"]), "gate": gate_state(),
            "grid": {"tiers": list(S["tiers"]), "windows": list(S["windows"]), "mu": MU,
                     "alignments": list(S["alignments"]), "policy_seed": e8.POLICY_SEED,
                     "horizon_min": S["horizon_min"], "market_tightness": S["market_tightness"],
                     "waits": list(WAITS), "w_star": W_STAR},
            "tags": sv.tag_table(TAGS), "bill": BILL, "classes": list(rq.CLASSES), "kinds": list(rq.KINDS),
            "hist": {"bin_s": rq.BIN_S, "n_bins": rq.N_BINS, "max_s": rq.HIST_MAX_S, "bin_eps": rq.BIN_EPS,
                     "pooled": "over windows and alignments, per tier"},
            "service": {f["tier"]: f.get("service") for f in files.values()},
            "prefill_tok_per_s": {f["tier"]: f.get("prefill_tok_per_s") for f in files.values()},
            "sources": {"e8v2": src}, "e8v2_same_scale": same_scale, "jobs": len(js), "jobs_ok": len(ok),
            "jobs_not_ok": not_ok, "ignored_outputs": ignored, "n_missing": len(missing)}
    if S["reduced"]:
        meta["reduced_note"] = (f"{REDUCED_ENV}=1: {S['horizon_min']} min at market tightness "
                                f"{S['market_tightness']}, a smoke run, never a result")
    s = {"meta": meta, "cells": cells, "missing": missing, "checks": {k: checks[k] for k in CHECK_IDS}}
    mc.dump_json(e7._jsonish(s), out / "summary.json")
    mc.dump_json({"meta": {k: meta[k] for k in ("exp", "git_revision", "reduced", "grid", "classes", "kinds",
                                                 "hist")}, "tiers": hist_out}, out / "hist.json", compact=True)
    mc.write_text(tables(s), out / "tables.md")
    return s


def tables(s: dict) -> str:
    m = s["meta"]
    L = [f"# E8q ({SPEC})", "", f"*{LABEL}*", ""]
    if m.get("reduced"):
        L += [f"Reduced run: {m.get('reduced_note')}", ""]
    rows = []
    for t, a in s["cells"].items():
        for w, b in a.items():
            for c, d in b.items():
                for tg, x in d.items():
                    for wk, y in ((x or {}).get("by_W") or {}).items():
                        rows.append([t, w, c, tg, wk, (x or {}).get("C_fluid"), y.get("C_replay"), y.get("error"),
                                     (y.get("counts") or {}).get("fallback_reneged")])
    L += ["## Cells (USD, overflow accounting; E = (C_replay - C_fluid) / C_replay)", "",
          mc.md_table(["tier", "window", "c", "tag", "W s", "C_fluid", "C_replay", "E", "reneged"], rows), ""]
    L += ["## Checks", "", mc.md_table(["check", "status"], [[k, v.get("status")] for k, v in s["checks"].items()]),
          ""]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check-start" in args:
        return check_start()
    if "--out" not in args and any(x in args for x in ("--job", "--summary", "--manifest")):
        args += ["--out", str(mc.ms3_root() / "out" / EXP)]
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=args, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
