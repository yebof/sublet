"""E8 v2 part (a): the request-level replay of the fluid model for Sublet itself, A9 and the two strongest baselines
(design/ms7/plan.md X3, D6, D9; design/ms7/feasibility/sens.md §2 C(a), §3 item 3; change C56). Exploratory, after
the MS5b freeze; s1v2's registration gate applies (s1v2.gate). Part (b), the multi-client replay on the confirmation
instance, is not built (plan D9); COPY_PARTS['e8v2'] = ('a',) leaves room for it.

Instance: MS4's E8 instance unchanged (design/sim_spec_ms4.md §7.3; e8.py's module docstring): configs/bench_e1.json
with E1's menu, 1-min routing, one week, one `series` borrower azure0 (azure2024_conv, week 0, north_america, own
capacity at P75, market tightness 0.5), the tier t in {S, M, L} as its LLM, smoothing window in {5, 15, 60} min,
engine.check_invariants and record_routing true, the trace lender (I1, 'sell', 'absorb'); here at mu / beta~ = 1
only, alignments c in {1, 2, 3, 4} (config seed = lender seed = c), policy seed 0. overrides() builds e8.overrides's
dict from this module's settings (E8's at full scale; tests check the equality).

Policies (TAGS): Sublet (A8P around A9 at 'lb'), A9, BL1-BO, BL5-cur, parameters on the run's own instance
(ms5b_common.tag_params). A6's runs are kept: the analysis reads them from out/e8/summary.json (components.<tier>.
<win>.1.by_c, mooncake.<win>.<prefix>); the pair job of (M, 15, c 1) reruns A6 once as an identity run (check
E8v2-0: C_fluid and C_replay equal E8's within 1e-9 relative).

Replay (sublet.replay, unchanged; e8.py's §7.4-§7.7). Each pair job builds the instance once and, for every tag, runs
the fluid week with the routing recorded (e7h.one_run's steps: drivers.run.make_policy, engine.simulate), checks E8-2
(fluid mode) and E8-3, then replays the Azure 2024 conversation requests (the request cache of this part's
e8v2:requests job) through the run's placements with the copier's seed c, so every tag sees the same copies; C_replay
and E = (C_replay - C_fluid) / C_replay as e8.cost_error. A Mooncake job (tier M, mu 1, alignment 1, window w) runs the
fluid week of every tag, takes the hour of the largest fluid overflow (it depends on the demand only), and replays the
Mooncake conversation hour through the run's replicas with ('on') or without ('off') prefix hits. The fluid run files
of metrics.write_run(full=True) that E8 wrote are not written; each tag's run entry (ms5b_common.week_entry: ALG, both
accountings, the guard's record for Sublet) is in the job's record instead.

Jobs (pool, ids by ms3_common.job_id; run_e8v2.sh runs e8v2:requests first, then the first pair job alone, timed,
then the rest, as run_e8.sh):
  e8v2:requests                       the request cache runs/requests/
  e8v2:pair:tier=T:win=W:c=C          4 tags (A6 too at the identity cell): fluid run, E8-2, E8-3, replay, E; record
                                      runs/pairs/<job>.json (36 jobs)
  e8v2:mooncake:win=W:prefix=P        4 tags: the fluid run, the hour, the replica-level replay (6 jobs)
Reduced job list (MS3_E8V2_REDUCED=1, run_e8v2.sh --reduced): E8's reduced instance (6 hours at market tightness 0.05),
tiers S, M, L, windows 5 and 60, alignment 1, the Mooncake jobs at windows 5 and 60; the identity run at (M, 60, 1)
without a reference; never a result.

Outputs <root>/out/e8v2/a/ (jobs/, logs/, runs/ (not versioned: requests/, pairs/, mooncake/), manifest.json,
summary.json, tables.md, run_e8v2.log). summary.json: meta (grid, tags, service models, the gate, sources),
cells.<tier>.<win>.<c>.<tag> {C_fluid, C_replay, error, fluid, replay, r0_fluid, r0_replay (over the fluid BL0a),
e8_1, e8_2, e8_3, guard}, reused_a6.<tier>.<win>.<c> (E8's A6 at mu 1), mooncake.<win>.<prefix>.<tag>,
reused_a6_mooncake, checks E8v2-0 ... E8v2-5. The rankings (fluid against replayed, per policy) are computed by
ms7_sens_analysis.py.

Status labels: as s1v2 (no claim: model validity; design Table 5.9).
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import copy
import gc
import hashlib
import sys
import time
from pathlib import Path
from typing import Mapping, Optional

import numpy as np

from .. import paths
from . import e7
from . import e7h
from . import e8
from . import ms3_common as mc
from . import ms4_common as m4
from . import ms5b_common as m5
from . import s1v2 as sv
from .ms3_common import Job, job_id, num_key, put

EXP = "e8v2"
PART = "a"
SPEC = "design/ms7/feasibility/sens.md §2 C(a), §3 item 3 (C56)"
TAGS = sv.TAGS4
IDENTITY_TAG = "A6"                           # E8's policy (e8.POLICY), rerun once against E8's stored run
MU = 1.0
TIERS, WINDOWS, ALIGNMENTS = e8.TIERS, e8.WINDOWS, e8.ALIGNMENTS
PREFIX = e8.PREFIX
MOONCAKE = {"tier": "M", "mu": MU, "c": 1}
REDUCED_ENV = "MS3_E8V2_REDUCED"
E8_SUMMARY = paths.SIM_OUT / "e8" / "summary.json"          # versioned (MS4, commit 939847ca)
E8_SUMMARY_REL = "code/sim/out/e8/summary.json"
REL_TOL = sv.REL_TOL
# seconds per fluid run (feasibility §1.3 smoke at (M, 15)) and per replay (E8's pair jobs, e8.EST_PAIR_S)
EST_FLUID_S = {"Sublet": 10.3, "A9": 4.4, "BL1-BO": 1.7, "BL5-cur": 1.9, "A6": 7.8}
EST_TABLE_S = 45.0
CHECK_IDS = ("E8v2-0", "E8v2-1", "E8v2-2", "E8v2-3", "E8v2-4", "E8v2-5")
CHECK_CLAIMS = {
    "E8v2-0": "A6's identity run at (M, 15, c 1) reproduces E8's stored pair (C_fluid and C_replay within 1e-9 "
              "relative, out/e8/summary.json components.M.15.1.by_c.1), so E8's A6 runs stand beside this part's",
    "E8v2-1": "conservation in every replay (e8's E8-1: every copy served once, tokens to 1e-9 relative)",
    "E8v2-2": "fluid mode in every pair (e8's E8-2: the replay's accounting fed the demand rates reproduces the "
              "engine's routing and fallback, 1e-6 relative)",
    "E8v2-3": "every fluid run: invariant_failures empty, gpu_only_lease_slots 0 (e8's E8-3)",
    "E8v2-4": "every Sublet run: certificate available and held in Theorem W's proven cases, the envelope holds, no "
              "projecting run aborts while S follows FB and T0g stays in bound form (Proposition P)",
    "E8v2-5": "E = (C_replay - C_fluid) / C_replay per (tier, window, tag), median over the alignments with its range, "
              "and the Mooncake hour's E per tag with and without prefix hits (informative)"}


def reduced() -> bool:
    return os.environ.get(REDUCED_ENV, "0") == "1"


def settings() -> dict:
    """E8's grid at mu 1 (e8.settings's values), or its reduced one with MS3_E8V2_REDUCED=1."""
    if reduced():
        r = e8.REDUCED
        return {"reduced": True, "horizon_min": r["horizon_min"], "market_tightness": r["market_tightness"],
                "tiers": tuple(r["tiers"]), "windows": tuple(r["windows"]), "alignments": tuple(r["alignments"])}
    return {"reduced": False, "horizon_min": e8.WEEK_MIN, "market_tightness": e8.TIGHTNESS, "tiers": TIERS,
            "windows": WINDOWS, "alignments": ALIGNMENTS}


def identity_cell(S: Optional[Mapping] = None) -> tuple:
    """(tier, window, c) of A6's identity run: (M, 15, 1), or (M, the largest window, 1) in a grid without 15."""
    S = S or settings()
    return ("M", 15 if 15 in S["windows"] else max(S["windows"]), int(S["alignments"][0]))


def pair_id(tier: str, win: int, c: int) -> str:
    return job_id(EXP, "pair", tier=tier, win=int(win), c=int(c))


def mooncake_id(win: int, prefix: str) -> str:
    return job_id(EXP, "mooncake", win=int(win), prefix=prefix)


def requests_id() -> str:
    return job_id(EXP, "requests")


def part_dir(out) -> Path:
    o = Path(out)
    return o if o.name == PART else o / PART


def cache_dir(out) -> Path:
    return Path(out) / "runs" / "requests"


def run_path(out, sub: str, jid: str) -> Path:
    return Path(out) / "runs" / sub / mc.job_file_name(jid)


def _est(tags, tier: str, win: int, scale: float, replays: bool = True) -> float:
    rep = e8.EST_PAIR_S[(tier, int(win))] if replays else 0.0
    fam = any(sv.a9_family(t) for t in tags if t != IDENTITY_TAG)
    return 5.0 + (EST_TABLE_S if fam else 0.0) + scale * sum(EST_FLUID_S.get(t, 10.0) + rep for t in tags)


def jobs() -> list:
    """e8v2:requests, the pair jobs (tiers S, M, L; windows from the largest; alignments: the first job, the one
    with the most copies, is the one run_e8v2.sh times alone), then the Mooncake jobs."""
    S = settings()
    scale = S["horizon_min"] / e8.WEEK_MIN
    ident = identity_cell(S)
    out = [Job(requests_id(), "pool", {"kind": "requests", "horizon_min": S["horizon_min"]}, est_s=e8.EST_REQUESTS_S)]
    for t in S["tiers"]:
        for w in sorted(S["windows"], reverse=True):
            for c in S["alignments"]:
                ids = [IDENTITY_TAG] if (t, int(w), int(c)) == ident else []
                tags = list(TAGS) + ids
                out.append(Job(pair_id(t, w, c), "pool",
                               {"kind": "pair", "tier": t, "win": int(w), "mu": MU, "c": int(c), "tags": tags,
                                "identity_tags": ids}, est_s=_est(tags, t, w, scale)))
    for w in S["windows"]:
        for p in PREFIX:
            out.append(Job(mooncake_id(w, p), "pool",
                           {"kind": "mooncake", "win": int(w), "prefix": p, **MOONCAKE, "tags": list(TAGS),
                            "identity_tags": []},
                           est_s=_est(TAGS, "M", w, scale, replays=False)
                           + len(TAGS) * e8.EST_MOONCAKE_S[p] * (0.3 if S["reduced"] else 1.0)))
    return out


# ---------------------------------------------------------------- instances and runs
def overrides(tier: str, win: int, mu: float = MU) -> dict:
    """e8.overrides's dict with this module's horizon and market tightness (equal to E8's at full scale)."""
    from .e1 import MENU
    if tier not in TIERS:
        raise ValueError(f"E8 v2 tier must be one of {TIERS}, got {tier!r}")
    S = settings()
    ov = copy.deepcopy(MENU)
    ov.update({"time.fast_slot_min": e8.FAST_MIN, "time.horizon_min": int(S["horizon_min"]),
               "llms": [e8.llm_entry(tier)],
               "borrowers": {"model": "series",
                             "list": [{"id": e8.BORROWER, "series": e8.SERIES, "week_index": 0, "tier": tier,
                                       "region": e8.REGION}],
                             "own_capacity_quantile": e8.OWN_QUANTILE, "smoothing_min": int(win),
                             "market_tightness": float(S["market_tightness"])},
               "stranding.mu_over_beta_tilde": float(mu)})
    return ov


def policy_of(name: str, inst) -> tuple:
    """(registry id, parameters) of a tag on the instance (A6: e8.POLICY)."""
    if name == IDENTITY_TAG:
        return e8.POLICY[0], copy.deepcopy(dict(e8.POLICY[1]))
    return sv.tag_id(name), sv.tag_params(name, inst)


def run_spec(policy_id: str, params, tier: str, win: int, mu: float, c: int) -> dict:
    """e8.run_spec's spec with the policy given (E8's spec when it is e8.POLICY)."""
    from ..drivers.run import load_run_spec
    return load_run_spec({"schema_version": 1, "name": f"e8v2_{tier}_w{int(win)}_mu{num_key(mu)}_c{int(c)}",
                          "instance": e8.CONFIG, "overrides": overrides(tier, win, mu),
                          "lender_model": dict(e8.LENDER_MODEL), "engine": dict(e8.ENGINE),
                          "policy": {"id": policy_id, "params": copy.deepcopy(dict(params or {}))},
                          "seeds": {"config": [int(c)], "lender": "config", "policy": [e8.POLICY_SEED]},
                          "bench": None, "out": "code/sim/out/e8v2/a/runs"})


def build(tier: str, win: int, mu: float, c: int) -> tuple:
    """(inst, model, ecfg) of one (tier, window, mu, alignment) (the instance does not depend on the policy)."""
    from ..drivers import run as drun
    inst, model, ecfg = drun.build(run_spec("BL0a", {}, tier, win, mu, c), int(c))
    if not (ecfg.check_invariants and ecfg.record_routing):
        raise RuntimeError("E8 v2's fluid runs need engine.check_invariants and engine.record_routing true")
    return inst, model, ecfg


def fluid_run(name: str, inst, ecfg, tier: str, win: int, mu: float, c: int, refs: dict, own) -> tuple:
    """(res, entry, policy record) of one tag's fluid run: the policy from its spec (drivers.run.make_policy), the
    engine run (lender seed c, policy seed 0), its ms5b_common.week_entry and e8.fluid_run's policy record."""
    from ..algos import registry
    from ..drivers import run as drun
    from ..engine import simulate
    pid, params = policy_of(name, inst)
    spec = run_spec(pid, params, tier, win, mu, c)
    model = drun._lender_model(spec, inst)
    t0 = time.perf_counter()
    _, imeta = drun.driver_inputs(pid, params, inst)
    pol = drun.make_policy(spec, inst)
    res = simulate(inst, pol, model, ecfg, lender_seed=int(c), policy_seed=e8.POLICY_SEED)
    wall = time.perf_counter() - t0
    e = m5.week_entry(res, inst, model, refs, own, tag_name=name, spec=spec, pol=pol, ps=e8.POLICY_SEED, c=c,
                      mode="L-tr", wall_s=wall, imeta=imeta)
    rp_ = {**params, **(pol.params() or {})}
    return res, e, {"id": pid, "params": rp_, "info_class": registry.info_class(pid, rp_, model.information),
                    "driver_inputs": imeta, "fluid_s": wall}


def _entry_brief(e: Mapping) -> dict:
    """The run entry's fields kept in a replay record (the guard's and A9's facts; no per-slot lists)."""
    keep = ("tag", "policy_id", "params", "resolved_params", "info_class", "info_class_reported", "ALG",
            "accountings", "components", "fallback_share", "fallback_share_after_reclaims", "n_leases",
            "n_invariant_failures", "invariant_failures_first", "gpu_only_lease_slots", "plan_class_p1", "status",
            "r0", "fallback_usd", "stranding_usd", "a9", "schedule_hash", "wall_s", "engine_wall_s", "mode")
    out = {k: copy.deepcopy(e.get(k)) for k in keep}
    a8 = e.get("a8")
    if a8:
        out["a8"] = {k: v for k, v in a8.items() if k not in ("safe_followed",)}
    return out


# ---------------------------------------------------------------- jobs
def run_requests(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """The request cache (e8.run_requests's steps): the Azure 2024 conversation week, or its first horizon_min
    minutes, as the three .npy files and their record."""
    from ..paths import DATA
    from ..replay import requests as rq
    from ..traces.borrowers import REQUEST_STREAMS
    g = sv.gate(reduced())
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
            "source": rq.file_info(DATA / REQUEST_STREAMS[e8.SERIES][1]),
            "load_s": load_s, "save_s": time.perf_counter() - t1, "reduced": reduced(),
            "git_revision": mc.git_revision(), "versions": mc.versions(), "job": job.id, "gate": g}
    outputs.dump(meta, pth["meta"])
    print(f"[e8v2] {job.id}: {stats['rows']} requests in {load_s:.1f} s", flush=True)
    return {"runs": 0, "rows": stats["rows"], "load_s": load_s}


def run_pair(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One (tier, window, alignment) at mu 1: the instance once, then per tag the fluid run, E8-3, E8-2's fluid mode,
    the replay of the horizon (E8-1) and E; the record runs/pairs/<job>.json."""
    from .. import replay as rp
    p = job.params
    tier, win, mu, c = p["tier"], int(p["win"]), float(p["mu"]), int(p["c"])
    g = sv.gate(reduced())
    t_job = time.perf_counter()
    inst, _, ecfg = build(tier, win, mu, c)
    ih = mc.instance_hash(inst)
    svc = rp.service_model(inst)
    ms = rp.market_scale(inst, svc.n_seq)
    arrs, cmeta = rp.open_cache(cache_dir(out), e8.SERIES)
    n_sec = 60 * inst.grid.horizon_min
    e8._cache_check(cmeta, n_sec)
    idx = rp.StreamIndex.build(arrs["t_s"], n_sec)
    ring = rp.ring_size(svc.w_in * float(cmeta["max_inp"]) + float(cmeta["max_out"]), svc)
    refs, own = m4.references(inst), e7._own(inst)
    n_h = inst.grid.horizon_min // 60
    errors, by_tag = [], {}
    for name in p["tags"]:
        def one(name=name):
            res, e, pol = fluid_run(name, inst, ecfg, tier, win, mu, c, refs, own)
            chk3 = e8.e8_3(res)
            plan = rp.placement(res, inst)
            chk2 = rp.check_e8_2(res, inst, plan, svc)
            t1 = time.perf_counter()
            copier = rp.Copier(arrs["t_s"], arrs["inp"], arrs["out"], idx, ms.gamma, svc.w_in, seed=c)
            rep = rp.replay(copier, plan, svc, ms.own_slots, n_sec, ring, progress_s=86400,
                            log=lambda m: print(f"[e8v2] {job.id} {name} {m}", flush=True))
            replay_s = time.perf_counter() - t1
            fl = e8._fluid_components(res.components)
            err = e8.cost_error(fl, rep["costs"])
            bl0a = float(refs["bl0a_usd"])
            x = {"tag": name, "identity": name in p["identity_tags"], "policy": pol, "seeds": dict(res.seeds),
                 "fluid": fl, "fluid_components": {k: float(v) for k, v in res.components.items()},
                 "replay": {k: rep[k] for k in ("n_seconds", "ring_s", "hold_max_s", "own_slots", "site_order",
                                                "counts", "tokens", "costs", "copier", "timing")},
                 **err, "r0_fluid": err["C_fluid"] / bl0a if bl0a > 0 else None,
                 "r0_replay": err["C_replay"] / bl0a if bl0a > 0 else None,
                 "e8_1": rep["conservation"], "e8_2": chk2, "e8_3": chk3,
                 "per_hour": {"fluid": e8._hourly(res.per_slot, inst.grid.slow_min, n_h), "replay": rep["per_hour"]},
                 "n_leases": len(res.leases), "n_replicas": len(res.replicas), "fluid_s": pol["fluid_s"],
                 "replay_s": replay_s, "entry": _entry_brief(e)}
            print(f"[e8v2] {job.id} {name}: C_fluid {err['C_fluid']:.2f}, C_replay {err['C_replay']:.2f}, E "
                  f"{err['error']}, E8-1 {rep['conservation']['pass']}, E8-2 {chk2['pass']}, E8-3 {chk3['pass']}; "
                  f"fluid {pol['fluid_s']:.1f} s, replay {replay_s:.1f} s", flush=True)
            del res, plan, rep, copier
            return x
        x = mc.try_run(errors, f"{name} {tier} w{win} c{c}", one)
        gc.collect()
        if x is not None:
            by_tag[name] = x
    rec = {"meta": {"exp": EXP, "part": PART, "job": job.id, "spec": SPEC, "change": sv.CHANGE, "label": sv.LABEL,
                    "git_revision": mc.git_revision(), "versions": mc.versions(), "written": mc._now(),
                    "reduced": reduced(), "gate": g},
           "job": job.id, "kind": "pair", "tier": tier, "win": win, "mu": mu, "c": c, "policy_seed": e8.POLICY_SEED,
           "tags": list(p["tags"]), "identity_tags": list(p["identity_tags"]), "tag_table": _tag_table(p["tags"]),
           "config": e8.CONFIG, "overrides": overrides(tier, win, mu), "instance_hash": ih,
           "horizon_min": inst.grid.horizon_min, "references": refs, "own_capacity_usd": own,
           "service": svc.record(), "scale": ms.record(), "runs": by_tag,
           "cache": {k: cmeta.get(k) for k in ("rows", "window", "sha256")}, "errors": sv.errs(errors),
           "git_revision": mc.git_revision(), "wall_s": time.perf_counter() - t_job}
    outputs.dump(e7._jsonish(rec), run_path(out, "pairs", job.id))
    return {"runs": len(by_tag), "errors": errors, "instance_hash": ih,
            "E": {t: x.get("error") for t, x in by_tag.items()}}


def run_mooncake(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One (window, prefix) of the Mooncake hour (e8.run_mooncake's steps) for every tag: its fluid run (tier M, mu
    1, alignment 1), the hour of the largest fluid overflow, Gamma_mc, the replica-level replay with or without prefix
    hits and the hour's E."""
    from .. import replay as rp
    p = job.params
    win, prefix, tier, mu, c = int(p["win"]), p["prefix"], p["tier"], float(p["mu"]), int(p["c"])
    if prefix not in PREFIX:
        raise ValueError(f"prefix must be one of {PREFIX}, got {prefix!r}")
    g = sv.gate(reduced())
    t_job = time.perf_counter()
    inst, _, ecfg = build(tier, win, mu, c)
    ih = mc.instance_hash(inst)
    svc = rp.service_model(inst)
    ms = rp.market_scale(inst, svc.n_seq)
    arrs, cmeta = rp.open_cache(cache_dir(out), e8.SERIES)
    e8._cache_check(cmeta, 60 * inst.grid.horizon_min)
    h, over = e8.peak_hour(np.asarray(inst.clients.demand[0]), inst.grid.fast_min)
    S0, S1 = h * e8.HOUR_S, (h + 1) * e8.HOUR_S
    i0, i1 = np.searchsorted(arrs["t_s"], [float(S0), float(S1)], side="left")
    az_tok = ms.gamma * float((svc.w_in * np.asarray(arrs["inp"][i0:i1]) + np.asarray(arrs["out"][i0:i1])).sum())
    trace = rp.load_mooncake()
    tstat = trace.stats()
    mc_tok = float((svc.w_in * trace.inp + trace.out).sum())
    gamma_mc = az_tok / mc_tok
    ring = rp.ring_size(float((svc.w_in * trace.inp + trace.out).max()), svc)
    refs, own = m4.references(inst), e7._own(inst)
    sl = slice(S0 // (60 * inst.grid.slow_min), S1 // (60 * inst.grid.slow_min))
    errors, by_tag = [], {}
    for name in p["tags"]:
        def one(name=name):
            res, e, pol = fluid_run(name, inst, ecfg, tier, win, mu, c, refs, own)
            chk3 = e8.e8_3(res)
            plan = rp.placement(res, inst)
            rplan = rp.replica_plan(res, inst)
            cp = rp.mooncake_copies(trace, gamma_mc, seed=c, t0_s=float(S0))
            t1 = time.perf_counter()
            rep = rp.replay_replicas(cp, trace, plan, rplan, svc, ms.own_slots, S0, S1, ring, prefix == "on")
            replay_s = time.perf_counter() - t1
            fl_h = {k: float(np.asarray(res.per_slot[k][sl]).sum()) for k in e8.COMPONENTS}
            err = e8.cost_error(fl_h, rep["costs"])
            x = {"tag": name, "policy": pol, "seeds": dict(res.seeds),
                 "fluid_week": e8._fluid_components(res.components), "copies": cp["n_copies"], "fluid": fl_h,
                 "replay": {k: rep[k] for k in ("seconds", "ring_s", "own_replicas", "own_slots", "leased_replicas",
                                                "counts", "tokens", "hits", "costs", "timing")},
                 **err, "e8_1": rep["conservation"], "e8_3": chk3, "fluid_s": pol["fluid_s"], "replay_s": replay_s,
                 "entry": _entry_brief(e)}
            print(f"[e8v2] {job.id} {name}: hour {h}, {cp['n_copies']} copies, E {err['error']}, hit ratio "
                  f"{rep['hits']['hit_ratio']}, E8-1 {rep['conservation']['pass']}; replay {replay_s:.1f} s",
                  flush=True)
            del res, plan, rplan, rep, cp
            return x
        x = mc.try_run(errors, f"{name} mooncake w{win} {prefix}", one)
        gc.collect()
        if x is not None:
            by_tag[name] = x
    rec = {"meta": {"exp": EXP, "part": PART, "job": job.id, "spec": SPEC, "change": sv.CHANGE, "label": sv.LABEL,
                    "git_revision": mc.git_revision(), "versions": mc.versions(), "written": mc._now(),
                    "reduced": reduced(), "gate": g},
           "job": job.id, "kind": "mooncake", "tier": tier, "win": win, "mu": mu, "c": c, "prefix": prefix,
           "policy_seed": e8.POLICY_SEED, "tags": list(p["tags"]), "tag_table": _tag_table(p["tags"]),
           "config": e8.CONFIG, "overrides": overrides(tier, win, mu), "instance_hash": ih, "references": refs,
           "service": svc.record(), "scale": ms.record(),
           "hour": {"index": h, "start_s": S0, "end_s": S1, "fluid_overflow_load_min": over * inst.grid.fast_min,
                    "azure_requests": int(i1 - i0), "azure_weighted_tokens_scaled": az_tok},
           "mooncake_trace": {"path": trace.path, **tstat, "weighted_tokens": mc_tok}, "gamma_mc": gamma_mc,
           "runs": by_tag, "errors": sv.errs(errors), "git_revision": mc.git_revision(),
           "wall_s": time.perf_counter() - t_job}
    outputs.dump(e7._jsonish(rec), run_path(out, "mooncake", job.id))
    return {"runs": len(by_tag), "errors": errors, "instance_hash": ih, "hour": h, "gamma_mc": gamma_mc,
            "E": {t: x.get("error") for t, x in by_tag.items()}}


def _tag_table(names) -> dict:
    out = sv.tag_table([n for n in names if n != IDENTITY_TAG])
    if IDENTITY_TAG in names:
        out[IDENTITY_TAG] = {"policy_id": e8.POLICY[0], "params": dict(e8.POLICY[1]), "kind": "identity",
                             "a9_family": False, "role": "E8's policy, rerun once against E8's stored pair",
                             "information": "I1"}
    return out


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    fn = {"requests": run_requests, "pair": run_pair, "mooncake": run_mooncake}[job.params["kind"]]
    return fn(job, outputs, out)


def manifest_extra(out) -> dict:
    from ..replay.requests import file_info
    from ..traces.borrowers import REQUEST_STREAMS
    out = Path(out)
    hashes = {}
    for j in jobs():
        k = j.params["kind"]
        if k in ("pair", "mooncake"):
            f = mc.read_json(run_path(out, "pairs" if k == "pair" else "mooncake", j.id))
            if isinstance(f, dict):
                hashes[j.id] = f.get("instance_hash")
    files = [Path(__file__), Path(e8.__file__), Path(sv.__file__), sv.ANALYSIS_FILE, E8_SUMMARY,
             paths.CONFIGS / e8.CONFIG, paths.ANALYSIS_OUT / "a12_minute_io.npz",
             paths.ANALYSIS_OUT / "a12_sim_inputs.json", paths.ANALYSIS_OUT / "a5_reclaim_cost_calibration.json"]
    return {"settings": {k: (list(v) if isinstance(v, tuple) else v) for k, v in settings().items()},
            "instance_hashes_from_outputs": hashes, "gate_record": sv.registration_record(),
            "raw_azure": file_info(paths.DATA / REQUEST_STREAMS[e8.SERIES][1]),
            "raw_mooncake": file_info(paths.DATA / REQUEST_STREAMS["mooncake_conversation"][1]),
            "sources_sha256": {sv._rel_repo(f): (hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None)
                               for f in files}}


# ---------------------------------------------------------------- summary
def _cell(x: Mapping) -> dict:
    """A tag's row of a pair or Mooncake record in the summary."""
    ent = x.get("entry") or {}
    out = {k: x.get(k) for k in ("C_fluid", "C_replay", "error", "r0_fluid", "r0_replay", "fluid", "fluid_s",
                                 "replay_s", "n_leases", "copies")}
    out["replay"] = {k: (x.get("replay") or {}).get("costs", {}).get(k) for k in ("routing", "fallback", "stranding",
                                                                                 "total")}
    out["e8_1_pass"] = (x.get("e8_1") or {}).get("pass")
    out["e8_2_pass"] = (x.get("e8_2") or {}).get("pass") if x.get("e8_2") is not None else None
    out["e8_3_pass"] = (x.get("e8_3") or {}).get("pass")
    out["status"] = ent.get("status")
    out["hit_ratio"] = ((x.get("replay") or {}).get("hits") or {}).get("hit_ratio")
    g = e7h.guard_brief(ent.get("a8"))
    if g is not None:
        out["guard"] = g
    return out


def _e8_reused(e8s: Optional[Mapping], S: Mapping) -> tuple:
    """(E8's A6 pairs at mu 1 {tier: {win: {c: {C_fluid, C_replay, error}}}}, its Mooncake hours {win: {prefix: {E,
    C_fluid, C_replay}}})."""
    comps = (e8s or {}).get("components") or {}
    errs = (e8s or {}).get("error") or {}
    pairs = {}
    for t in S["tiers"]:
        for w in S["windows"]:
            byc = ((comps.get(t) or {}).get(num_key(w)) or {}).get(num_key(MU), {}).get("by_c") or {}
            ebc = ((errs.get(t) or {}).get(num_key(w)) or {}).get(num_key(MU), {}).get("by_c") or {}
            for c in S["alignments"]:
                v = byc.get(num_key(c)) or {}
                pairs.setdefault(t, {}).setdefault(num_key(w), {})[num_key(c)] = {
                    "C_fluid": v.get("C_fluid"), "C_replay": v.get("C_replay"), "error": ebc.get(num_key(c))}
    moon = {}
    for w in S["windows"]:
        for pf in PREFIX:
            v = (((e8s or {}).get("mooncake") or {}).get(num_key(w)) or {}).get(pf) or {}
            moon.setdefault(num_key(w), {})[pf] = {"error": v.get("error"), "C_fluid": v.get("C_fluid"),
                                                    "C_replay": v.get("C_replay")}
    return pairs, moon


def summary(out) -> dict:
    out = Path(out)
    S = settings()
    js = jobs()
    rjs = [j for j in js if j.params["kind"] != "requests"]
    files, ok, ignored, not_ok = sv.part_outputs(
        out, rjs, lambda j: run_path(out, "pairs" if j.params["kind"] == "pair" else "mooncake", j.id))
    e8s = mc.read_json(E8_SUMMARY)
    e8_src = {"file": E8_SUMMARY_REL, "exists": E8_SUMMARY.is_file(),
              "sha256": hashlib.sha256(E8_SUMMARY.read_bytes()).hexdigest() if E8_SUMMARY.is_file() else None,
              "git_revision": ((e8s or {}).get("meta") or {}).get("git_revision")}
    cells, moon, missing, rows = {}, {}, [], []
    for j in rjs:
        p = j.params
        f = files.get(j.id) or {}
        runs = f.get("runs") or {}
        for t in p["tags"]:
            x = runs.get(t)
            cell = _cell(x) if x is not None else None
            if cell is None or cell.get("status") != "ok":
                missing.append({"job": j.id, "tag": t, "why": (cell or {}).get("status") or not_ok.get(j.id)
                                or "run missing"})
            if p["kind"] == "pair":
                tgt = cells.setdefault(p["tier"], {}).setdefault(num_key(p["win"]), {}).setdefault(num_key(p["c"]), {})
                tgt["A6_identity" if t == IDENTITY_TAG else t] = cell
            else:
                moon.setdefault(num_key(p["win"]), {}).setdefault(p["prefix"], {})[t] = cell
            if x is not None:
                rows.append({"job": j.id, "kind": p["kind"], "tag": t, **({"guard": cell["guard"]}
                                                                       if cell.get("guard") else {})})
    g8 = ((e8s or {}).get("meta") or {}).get("grid") or {}
    same_scale = e8s is not None and g8.get("horizon_min") == S["horizon_min"] \
        and g8.get("market_tightness") == S["market_tightness"]
    # E8's stored runs stand beside this part's only on the same instances (a reduced run has none to compare)
    reused, reused_moon = _e8_reused(e8s if same_scale else None, S)
    ident = identity_cell(S)
    ic = ((cells.get(ident[0]) or {}).get(num_key(ident[1])) or {}).get(num_key(ident[2])) or {}
    a6 = ic.get("A6_identity") or {}
    ref = ((reused.get(ident[0]) or {}).get(num_key(ident[1])) or {}).get(num_key(ident[2])) or {}
    dd = {k: sv.rel_diff(a6.get(k), ref.get(k)) for k in ("C_fluid", "C_replay")}
    if not a6:
        st0 = "missing"
    elif ref.get("C_fluid") is None or ref.get("C_replay") is None:
        st0 = "missing"
    else:
        st0 = "pass" if all(v is not None and v <= REL_TOL for v in dd.values()) else "fail"
    checks = {"E8v2-0": {"status": st0, "claim": CHECK_CLAIMS["E8v2-0"], "cell": list(ident), "run": a6 or None,
                         "reference": ref, "rel_diff": dd, "tolerance": REL_TOL, "same_scale": same_scale}}
    if not same_scale:
        checks["E8v2-0"]["note"] = ("E8's summary is missing or its grid (horizon, market tightness) is not this "
                                    "run's: no reference, and E8's A6 runs are not reused")
    allx = [(jid, t, x) for jid, f in files.items() for t, x in (f.get("runs") or {}).items()]
    f1 = [f"{j}:{t}" for j, t, x in allx if not (x.get("e8_1") or {}).get("pass")]
    f2 = [f"{j}:{t}" for j, t, x in allx if x.get("e8_2") is not None and not x["e8_2"].get("pass")]
    f3 = [f"{j}:{t}" for j, t, x in allx if not (x.get("e8_3") or {}).get("pass")]
    miss = bool(not_ok) or bool(missing)
    checks["E8v2-1"] = {"status": sv.status_of(bool(f1), len(allx), miss), "claim": CHECK_CLAIMS["E8v2-1"],
                        "n": len(allx), "failures": f1[:50],
                        "max_tokens_rel_diff": max((x["e8_1"].get("tokens_rel_diff") or 0.0 for _j, _t, x in allx
                                                    if x.get("e8_1")), default=None)}
    n2 = sum(1 for _j, _t, x in allx if x.get("e8_2") is not None)
    checks["E8v2-2"] = {"status": sv.status_of(bool(f2), n2, miss), "claim": CHECK_CLAIMS["E8v2-2"], "n": n2,
                        "failures": f2[:50]}
    checks["E8v2-3"] = {"status": sv.status_of(bool(f3), len(allx), miss), "claim": CHECK_CLAIMS["E8v2-3"],
                        "n": len(allx), "failures": f3[:50]}
    checks["E8v2-4"] = {"claim": CHECK_CLAIMS["E8v2-4"], **sv.guard_check(rows, miss)}
    errt = {}
    for t, a in cells.items():
        for w, b in a.items():
            for tg in TAGS:
                vals = [x[tg]["error"] for x in b.values() if (x.get(tg) or {}).get("error") is not None]
                errt.setdefault(t, {}).setdefault(w, {})[tg] = e8._agg(vals) if vals else {"n": 0}
    checks["E8v2-5"] = {"status": "informative", "claim": CHECK_CLAIMS["E8v2-5"], "error_by_tier_window_tag": errt,
                        "mooncake_error": {w: {pf: {t: (x or {}).get("error") for t, x in d.items()}
                                               for pf, d in a.items()} for w, a in moon.items()}}
    meta = sv.meta_common(EXP, PART, SPEC, S["reduced"],
                          grid={"tiers": list(S["tiers"]), "windows": list(S["windows"]), "mu": MU,
                                "alignments": list(S["alignments"]), "policy_seed": e8.POLICY_SEED,
                                "horizon_min": S["horizon_min"], "market_tightness": S["market_tightness"],
                                "mooncake_point": dict(MOONCAKE), "identity_cell": list(ident)},
                          tags=_tag_table(list(TAGS) + [IDENTITY_TAG]), h1_pair=list(sv.H1_PAIR),
                          service={f["tier"]: f.get("service") for f in files.values() if f.get("kind") == "pair"},
                          sources={"e8": e8_src}, jobs=len(js), jobs_ok=len(ok), jobs_not_ok=not_ok,
                          ignored_outputs=ignored, n_missing=len(missing))
    if S["reduced"]:
        meta["reduced_note"] = (f"{REDUCED_ENV}=1: {S['horizon_min']} min at market tightness "
                                f"{S['market_tightness']}, a smoke run, never a result")
    s = {"meta": meta, "cells": cells, "reused_a6": reused, "mooncake": moon, "reused_a6_mooncake": reused_moon,
         "missing": missing, "checks": {k: checks[k] for k in CHECK_IDS}}
    mc.dump_json(e7._jsonish(s), out / "summary.json")
    mc.write_text(tables(s), out / "tables.md")
    return s


def tables(s: dict) -> str:
    m = s["meta"]
    L = [f"# E8 v2 part (a) ({SPEC})", "", f"*{sv.LABEL}*", ""]
    if m.get("reduced"):
        L += [f"Reduced run: {m.get('reduced_note')}", ""]
    rows = [[t, w, c, tg, (x or {}).get("C_fluid"), (x or {}).get("C_replay"), (x or {}).get("error")]
            for t, a in s["cells"].items() for w, b in a.items() for c, d in b.items() for tg, x in d.items()]
    L += ["## Pairs (USD, overflow accounting; E = (C_replay - C_fluid) / C_replay)", "",
          mc.md_table(["tier", "window", "c", "tag", "C_fluid", "C_replay", "E"], rows), ""]
    rows = [[w, pf, tg, (x or {}).get("error"), (x or {}).get("hit_ratio")] for w, a in s["mooncake"].items()
            for pf, d in a.items() for tg, x in d.items()]
    L += ["## Mooncake hour (tier M, mu 1, alignment 1)", "",
          mc.md_table(["window", "prefix", "tag", "E", "hit ratio"], rows), ""]
    L += ["## Checks", "", mc.md_table(["check", "status"], [[k, v.get("status")] for k, v in s["checks"].items()]),
          ""]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check-start" in args:
        return sv.check_start(EXP, reduced())
    if "--out" not in args and any(x in args for x in ("--job", "--summary", "--manifest")):
        args += ["--out", str(mc.ms3_root() / "out" / EXP / PART)]
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=args, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
