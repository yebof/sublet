"""E8: fluid-model fidelity (design/sim_spec_ms4.md §7; deliverable D35, unit U24; open choices M29, M31).

The engine is fluid (design §3.3): it routes demand rates over warm replica capacity and keeps no request state. E8
replays the Azure 2024 conversation requests through the placements of fluid runs at request level, with in-flight
state (package sublet.replay), and reports the relative cost error of the fluid model, E = (C_replay - C_fluid) /
C_replay in overflow accounting, against the smoothing window (5, 15, 60 min), one line per tier. Claims: none (model
validity; design Table 5.9). Prefix hits enter only through a one-hour Mooncake sensitivity (§7.7).

Fluid runs (§7.3, M31). E4's Azure panel (§6.3) without the slow-grid override: configs/bench_e1.json with E1's menu
(e1.MENU: s5_tau5_H60, s5_tau60_H0, protected) and time.fast_slot_min 1, so the engine routes every minute; one week
(time.horizon_min 10080); one `series` borrower azure0 = azure2024_conv, week 0, region north_america, own capacity
at P75, market tightness 0.5; the borrower's tier and `llms` [t] (catalog maas_a10, entry t, kappa_mult 1) for t in
{S, M, L} by Table 5.5's swept relabeling (all -> S; both Azure services -> M, the default; conversation -> L);
borrowers.smoothing_min in {5, 15, 60} (design Table 5.6); stranding.mu_over_beta_tilde in {1, 0.2, 0.5, 2};
lender model trace, I1, 'sell', 'absorb'; engine.check_invariants and engine.record_routing true. Policy A6 {}
(practical), policy seed 0, alignments c in {1, 2, 3, 4} (config seed = lender seed = c; one policy seed per
alignment, M29). 3 tiers x 3 windows x 4 mu x 4 alignments = 144 fluid runs, each replayed in its own job right
after the run, which reads RunResult.routing (W, b, x) in memory, so no job reads another job's run files.

Replay (§7.4-§7.6; sublet.replay). The week's requests are cached once by e8:requests as uncompressed .npy files and
memory-mapped by every replay job. Each request yields floor(Gamma) copies plus one with probability Gamma -
floor(Gamma) (Gamma the instance's market scale; scale.market_scale checks it against the demand), generated per
second with np.random.default_rng(c) and never stored. Service model: 128 sequences per replica, TPOT 15 / 35 / 60 ms
for S / M / L (a5 assumptions), w_in the LLM's (0.2133 / 0.3048 / 0.5333); a copy holds a slot for rint(l TPOT) s.
Own capacity floor(128 Gamma C0 / kappa_j) slots, site l floor(128 W_l(f)) slots at fast slot f; a copy takes a free
own slot, else a free slot at the site of least delta, else fallback; at a capacity drop the in-flight copies above
a site's slots are stranded, latest arrivals first, and their remaining work moves to fallback. C_replay = the fluid
run's lease and loading (common to both) + the replay's routing, fallback and stranding (mu_fb per stranded replica
load, stranded copies / 128); C_fluid = the fluid run's ledger total.

Mooncake (§7.7). For tier M, mu / beta~ = 1, alignment 1 and each window: the fluid run again, then the Mooncake
conversation trace (12,031 requests over 3,537 s, hash_ids kept) replayed through the placements of the clock hour of
the week with the largest fluid overflow (sum of d(f) over its minutes), replicated by Gamma_mc = (that hour's
Gamma-scaled Azure weighted tokens) / (Mooncake's weighted tokens), each copy with its request's own sizes and blocks
(copy k's blocks in its own namespace, so the replicated stream keeps Mooncake's global hit ratio, 0.366), through the
replica-level loop (loop.replay_replicas: the run's replicas, reconstructed from its records and drain events and
checked against W; own capacity cut into replicas of 128 slots; with prefix hits an infinite cache per replica,
emptied when it dies, and a copy goes to the free replica of the cheapest class with the longest cached prefix of its
blocks), with ('on') and without ('off') hits. The hour's E uses the fluid run's per-slot costs of the
hour and the replay's routing, fallback and stranding of the copies arriving in the hour; the replay starts the hour
with no copy in flight.

Jobs (§7.8; ids by ms3_common.job_id, numbers as num_key):
  pool  e8:requests                              the request cache runs/requests/ (load 52.5 s, 1,439-MB peak)
  pool  e8:pair:tier=T:win=W:mu=U:c=C            fluid run, its run file, E8-2's fluid mode, E8-3, the replay
                                                 (E8-1) and E; record runs/pairs/<job>.json, run file runs/fluid/
  pool  e8:mooncake:win=W:prefix=P               P in {off, on}: the fluid run (rerun in the job), the hour, the
                                                 replica-level replay; record runs/mooncake/<job>.json
The e8:pair jobs are listed by tier S, M, L, window 60, 15, 5, mu / beta~ 1, 0.2, 0.5, 2 and alignment: Gamma, and
with it the number of copies, grows with the smoothing window at every tier (and does not depend on mu or the
alignment), so the first, e8:pair:tier=S:win=60:mu=1:c=1, is the job with the most copies. run_e8.sh runs
e8:requests first (a filtered pass, §2.4; rerun when the request cache's files are missing, as under MS3_RESUME=1 in
a tree without runs/), then the first e8:pair job alone, which is timed, then the remaining e8:pair and e8:mooncake
jobs; the replay passes do not run without an ok e8:requests and its cache files.

Reduced job list (smoke runs and tests): MS3_E8_REDUCED=1 (run_e8.sh --reduced sets it) builds every instance on the
first 6 hours (time.horizon_min 360) at market tightness 0.05 (a tenth of the default, so Gamma and the leased
capacity are small), caches only those 6 hours of requests, and keeps tiers S, M, L, windows 5 and 60, mu 1 and 2,
alignment 1 and the Mooncake jobs at windows 5 and 60; its summary has meta.reduced true and is never a result.

Outputs (code/sim/out/e8/): runs/ (not versioned: requests/ the cache, fluid/ the fluid run files of
metrics.write_run(full=True), pairs/ and mooncake/ the job records of the replays), jobs/, logs/, manifest.json,
run_e8.log, summary.json, tables.md. The fluid run files and the replay records hold the policy as resolved
(policy.params() over the spec's parameters), its information class (registry.info_class) and the driver inputs.

summary.json (<tier> in {S, M, L}, <win> in {5, 15, 60}, <mu> in {1, 0.2, 0.5, 2}, <c> in {1, 2, 3, 4}, <prefix> in
{off, on}; every key of the grid is present, a value without an 'ok' job output is null with its '*_note'; a job
whose record is 'ok' but whose run file is missing or unreadable counts as missing):
  meta                             exp, spec, git_revision, written, reduced (and reduced_note), grid (tiers,
                                   windows, mus, alignments, policy seed, horizon_min, market_tightness), config,
                                   overrides of the reference point, lender_model, engine, policy (as specified),
                                   policy_resolved (resolved parameters, info_class and driver inputs of the first
                                   ok record, null before), tier_map (Table 5.5), service model per tier (n_seq,
                                   tpot_s, w_in, kappa), scale.<tier>.<win> (gamma_by_c, own_slots_by_c,
                                   C0_loads_by_c), requests (the cache record), mooncake_trace (the trace's
                                   statistics), timings (pair job, fluid run and replay wall times: median, max; the
                                   first pair job's), jobs_ok (ok records with a usable output), jobs_missing,
                                   ignored_outputs, outputs_missing (ok records whose run file is missing or
                                   unreadable; also in jobs_missing)
  error.<tier>.<win>.<mu>          median, min, max, n of E over the alignments, by_c {<c>: E}, alignments
  components.<tier>.<win>.<mu>     fluid {lease, loading, routing, fallback, stranding, total} and replay {routing,
                                   fallback, stranding, total} (medians over the alignments, USD), by_c {<c>: {fluid,
                                   replay, C_fluid, C_replay}}, alignments, n
  mooncake.<win>.<prefix>          error (E of the hour), C_fluid, C_replay, fluid {routing, fallback, stranding,
                                   lease, loading, total} of the hour, replay {routing, fallback, stranding, total},
                                   hour (index, start second), gamma_mc, copies, hit_ratio (blocks hit / blocks of
                                   the copies on replicas, null without hits), global_hit_ratio (Mooncake's
                                   infinite-cache ratio), n (1)
  checks.E8-1 ... E8-5             status ('pass', 'fail', 'missing' or 'informative'), claim, inputs (§7.9)

Run from code/sim under the 3 GB cap through run_e8.sh (ms3_lib.sh). --estimate uses provisional job times (EST_*:
full-scale timing jobs of this build under load, not versioned, and values derived from them); §11.1 sets the budget
from the first e8:pair job of the run.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import copy
import hashlib
import sys
import time
from pathlib import Path

import numpy as np

from . import ms3_common as mc
from .ms3_common import Job, job_id, num_key, put

EXP = "e8"
SPEC = "design/sim_spec_ms4.md §7"
CONFIG = "bench_e1.json"
SERIES = "azure2024_conv"
BORROWER = "azure0"
REGION = "north_america"
TIERS = ("S", "M", "L")
WINDOWS = (5, 15, 60)
MUS = (1.0, 0.2, 0.5, 2.0)                # the headline first
ALIGNMENTS = (1, 2, 3, 4)
POLICY_SEED = 0                           # M29: one policy seed per alignment
POLICY = ("A6", {})                       # M31
FAST_MIN = 1                              # 1-min routing, the fluid model that E8 tests
WEEK_MIN = 10080
OWN_QUANTILE = 75
TIGHTNESS = 0.5
LENDER_MODEL = {"schedule": "trace", "information": "I1", "on_unavailable": "sell", "violations": "absorb"}
ENGINE = {"check_invariants": True, "record_routing": True}
MOONCAKE = {"tier": "M", "mu": 1.0, "c": 1}
PREFIX = ("off", "on")
HOUR_S = 3600
TIER_MAP = {"S": "all -> S (Table 5.5, swept)", "M": "both Azure services -> M (Table 5.5, default)",
            "L": "conversation -> L (Table 5.5, swept)"}
REDUCED_ENV = "MS3_E8_REDUCED"
REDUCED = {"horizon_min": 360, "market_tightness": 0.05, "tiers": TIERS, "windows": (5, 60), "mus": (1.0, 2.0),
           "alignments": (1,)}
# provisional time constants of --estimate (seconds), not a result: wall times of single full-scale timing jobs of
# this build under a host load of about 3 (not versioned; e8:requests, e8:pair at mu 1, c 1 for (S, 60), (S, 5),
# (M, 15) and (L, 60), e8:mooncake at window 15, 'on' with the longest-cached-prefix rule of loop.replay_replicas);
# the other (tier, window) points are the measured job of the tier
# shifted by 0.12 s per million copies (the slope between the (L, 60) and (S, 60) jobs; Gamma does not depend on mu
# or the alignment). §11.1 replaces them with the timed first e8:pair job of the run.
EST_REQUESTS_S = 54.0
EST_PAIR_S = {("S", 60): 143.3, ("S", 15): 127.4, ("S", 5): 121.7, ("M", 60): 81.8, ("M", 15): 76.8, ("M", 5): 73.4,
              ("L", 60): 31.6, ("L", 15): 31.4, ("L", 5): 31.2}
EST_MOONCAKE_S = {"off": 11.4, "on": 25.1}
CHECK_CLAIMS = {
    "E8-1": "conservation in every replay: every copy is served by own capacity, a leased replica or fallback exactly "
            "once (a stranded copy is served by its leased replica and its remaining work by fallback), and the "
            "served and fallback weighted tokens sum to the stream's total (counts exact, tokens to 1e-9 relative; "
            "the Mooncake hour's tokens with the input saved by prefix hits)",
    "E8-2": "fluid mode: the replay's accounting fed the instance's per-fast-slot demand as rates, with capacity "
            "kappa_j W(f) and cheapest-first routing (the min-cost routing of the one client), reproduces the "
            "engine's routing and fallback components (1e-6 relative, over max(|engine|, 1e-9 USD)); stranding "
            "compared and reported",
    "E8-3": "every fluid run: invariant_failures empty, gpu_only_lease_slots 0",
    "E8-4": "the relative cost error E = (C_replay - C_fluid) / C_replay per (tier, window, mu), median over the "
            "alignments with its range (informative; no claim: model validity)",
    "E8-5": "the Mooncake hour's E with and without prefix hits (informative; the 0.366 infinite-cache ratio bounds "
            "any replica-level hit ratio from above)"}


# ---------------------------------------------------------------- settings and grid
def reduced() -> bool:
    return os.environ.get(REDUCED_ENV, "0") == "1"


def settings() -> dict:
    """The grid of §7.3, or the reduced one with MS3_E8_REDUCED=1 (module docstring)."""
    if reduced():
        return {"reduced": True, "horizon_min": REDUCED["horizon_min"], "market_tightness": REDUCED["market_tightness"],
                "tiers": REDUCED["tiers"], "windows": REDUCED["windows"], "mus": REDUCED["mus"],
                "alignments": REDUCED["alignments"]}
    return {"reduced": False, "horizon_min": WEEK_MIN, "market_tightness": TIGHTNESS, "tiers": TIERS,
            "windows": WINDOWS, "mus": MUS, "alignments": ALIGNMENTS}


def pair_id(tier: str, win: int, mu: float, c: int) -> str:
    return job_id(EXP, "pair", tier=tier, win=int(win), mu=float(mu), c=int(c))


def mooncake_id(win: int, prefix: str) -> str:
    return job_id(EXP, "mooncake", win=int(win), prefix=prefix)


def requests_id() -> str:
    return job_id(EXP, "requests")


def jobs() -> list:
    """The jobs in run order (§7.8): e8:requests, the e8:pair jobs (tiers S, M, L, windows from the largest, mu,
    alignments; the first, the job with the most copies, is the one run_e8.sh times alone), the e8:mooncake jobs."""
    S = settings()
    out = [Job(requests_id(), "pool", {"kind": "requests", "horizon_min": S["horizon_min"]}, est_s=EST_REQUESTS_S)]
    scale = S["horizon_min"] / WEEK_MIN
    for t in S["tiers"]:
        for w in sorted(S["windows"], reverse=True):          # Gamma grows with the window: the most copies first
            for mu in S["mus"]:
                for c in S["alignments"]:
                    out.append(Job(pair_id(t, w, mu, c), "pool",
                                   {"kind": "pair", "tier": t, "win": int(w), "mu": float(mu), "c": int(c)},
                                   est_s=EST_PAIR_S[(t, int(w))] * scale + 5.0))
    for w in S["windows"]:
        for p in PREFIX:
            out.append(Job(mooncake_id(w, p), "pool", {"kind": "mooncake", "win": int(w), "prefix": p, **MOONCAKE},
                           est_s=EST_MOONCAKE_S[p] * (0.3 if S["reduced"] else 1.0)))
    return out


# ---------------------------------------------------------------- instances (§7.3)
def llm_entry(tier: str) -> dict:
    return {"id": tier, "catalog": "maas_a10", "entry": tier, "kappa_mult": 1.0}


def overrides(tier: str, win: int, mu: float) -> dict:
    """The overrides of one fluid run on configs/bench_e1.json (module docstring): e1.MENU with time.fast_slot_min 1,
    the horizon, llms [tier], the series borrower azure0 at the tier, smoothing window `win` and mu / beta~ = mu."""
    from .e1 import MENU
    if tier not in TIERS:
        raise ValueError(f"E8 tier must be one of {TIERS}, got {tier!r}")
    S = settings()
    ov = copy.deepcopy(MENU)
    ov.update({"time.fast_slot_min": FAST_MIN, "time.horizon_min": int(S["horizon_min"]), "llms": [llm_entry(tier)],
               "borrowers": {"model": "series",
                             "list": [{"id": BORROWER, "series": SERIES, "week_index": 0, "tier": tier,
                                       "region": REGION}],
                             "own_capacity_quantile": OWN_QUANTILE, "smoothing_min": int(win),
                             "market_tightness": float(S["market_tightness"])},
               "stranding.mu_over_beta_tilde": float(mu)})
    return ov


def run_spec(tier: str, win: int, mu: float, c: int) -> dict:
    from ..drivers.run import load_run_spec
    pid, params = POLICY
    return load_run_spec({"schema_version": 1, "name": f"e8_{tier}_w{int(win)}_mu{num_key(mu)}_c{int(c)}",
                          "instance": CONFIG, "overrides": overrides(tier, win, mu),
                          "lender_model": dict(LENDER_MODEL), "engine": dict(ENGINE),
                          "policy": {"id": pid, "params": copy.deepcopy(params)},
                          "seeds": {"config": [int(c)], "lender": "config", "policy": [POLICY_SEED]}, "bench": None,
                          "out": "code/sim/out/e8/runs"})


def build(tier: str, win: int, mu: float, c: int) -> tuple:
    """(inst, model, ecfg, spec) of one fluid run; RuntimeError unless invariants and routing are recorded."""
    from ..drivers import run as drun
    spec = run_spec(tier, win, mu, c)
    inst, model, ecfg = drun.build(spec, int(c))
    if not (ecfg.check_invariants and ecfg.record_routing):
        raise RuntimeError("E8's fluid runs need engine.check_invariants and engine.record_routing true (§7.3)")
    return inst, model, ecfg, spec


def fluid_run(inst, model, ecfg, spec, c: int):
    """(res, wall_s, policy): the fluid run of A6 {} (lender seed c, policy seed 0), its wall time and the policy
    as run: id, the parameters as resolved (policy.params() over the spec's), the information class
    (registry.info_class) and the driver inputs' record (drivers.run.driver_inputs), as the MS3 drivers record them."""
    from ..algos import registry
    from ..drivers import run as drun
    from ..engine import simulate
    pid, params = POLICY
    t0 = time.perf_counter()
    pol = drun.make_policy(spec, inst)
    _, imeta = drun.driver_inputs(pid, params, inst)
    res = simulate(inst, pol, model, ecfg, lender_seed=int(c), policy_seed=POLICY_SEED)
    wall = time.perf_counter() - t0
    rp_ = {**params, **(pol.params() or {})}
    return res, wall, {"id": pid, "params": rp_, "info_class": registry.info_class(pid, rp_, model.information),
                       "driver_inputs": imeta}


# ---------------------------------------------------------------- paths
def cache_dir(out) -> Path:
    return Path(out) / "runs" / "requests"


def run_path(out, sub: str, jid: str) -> Path:
    return Path(out) / "runs" / sub / mc.job_file_name(jid)


# ---------------------------------------------------------------- small helpers
COMPONENTS = ("lease", "loading", "routing", "fallback", "stranding", "total")


def _fluid_components(comp: dict) -> dict:
    return {k: float(comp[k]) for k in COMPONENTS}


def cost_error(fluid: dict, replay_costs: dict) -> dict:
    """C_fluid (the fluid ledger's total), C_replay (lease and loading of the fluid run + the replay's routing,
    fallback and stranding) and E = (C_replay - C_fluid) / C_replay (§7.6), null with a note if C_replay <= 0."""
    cf = float(fluid["total"])
    cr = cf - float(fluid["routing"]) - float(fluid["fallback"]) - float(fluid["stranding"]) \
        + float(replay_costs["routing"]) + float(replay_costs["fallback"]) + float(replay_costs["stranding"])
    out = {"C_fluid": cf, "C_replay": cr}
    put(out, "error", (cr - cf) / cr if cr > 0 else None, "C_replay is not positive")
    return out


def _cache_check(meta: dict, n_seconds: int) -> None:
    """The cache covers [0, n_seconds) of the stream (the record's window and last time)."""
    dur = meta.get("window", {}).get("dur_s")
    if dur is not None and float(dur) < n_seconds:
        raise ValueError(f"the request cache holds {dur} s, the replay needs {n_seconds} s (rerun e8:requests)")


def _hourly(per_slot: dict, slow_min: int, n_hours: int) -> dict:
    per_h = 60 // slow_min
    return {k: np.asarray(per_slot[k][: n_hours * per_h]).reshape(n_hours, per_h).sum(axis=1).tolist()
            for k in ("routing", "fallback", "stranding", "lease", "loading", "total")}


def e8_3(res) -> dict:
    inv = list(res.invariant_failures)
    gpu = int(res.metrics.get("gpu_only_lease_slots", 0))
    return {"pass": not inv and gpu == 0, "n_invariant_failures": len(inv), "invariant_first": inv[:3],
            "gpu_only_lease_slots": gpu}


# ---------------------------------------------------------------- job: the request cache
def run_requests(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """Load the Azure 2024 conversation week (reduced: the first horizon_min minutes) through load_requests and write
    the three .npy files and their record (§7.4)."""
    from ..paths import DATA
    from ..replay import requests as rq
    from ..traces.borrowers import REQUEST_STREAMS
    hz = int(job.params["horizon_min"])
    dur = None if hz >= WEEK_MIN else 60.0 * hz
    t0 = time.perf_counter()
    arrs = rq.load_azure(dur, SERIES)
    load_s = time.perf_counter() - t0
    paths = rq.cache_paths(cache_dir(out), SERIES)
    t1 = time.perf_counter()
    for k in rq.CACHE_KEYS:
        rq.save_npy(arrs[k], outputs.partial(paths[k]))
    stats = rq.stream_stats(arrs["t_s"], arrs["inp"], arrs["out"])
    sha = {k: rq.array_sha256(arrs[k]) for k in rq.CACHE_KEYS}
    meta = {"stream": SERIES, "window": {"t0_s": 0.0, "dur_s": dur}, **stats, "sha256": sha,
            "array_bytes": int(sum(v.nbytes for v in arrs.values())), "dtype": "float64",
            "files": {k: paths[k].name for k in rq.CACHE_KEYS},
            "source": rq.file_info(DATA / REQUEST_STREAMS[SERIES][1]), "load_s": load_s,
            "save_s": time.perf_counter() - t1, "reduced": reduced(), "git_revision": mc.git_revision(),
            "versions": mc.versions(), "job": job.id}
    outputs.dump(meta, paths["meta"])
    print(f"[e8] {job.id}: {stats['rows']} requests in {load_s:.1f} s, saved in {meta['save_s']:.1f} s", flush=True)
    return {"runs": 0, "rows": stats["rows"], "load_s": load_s, "save_s": meta["save_s"]}


# ---------------------------------------------------------------- job: one fluid run and its replay
def run_pair(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One (tier, window, mu, alignment) of §7.3: the fluid run (its run file), E8-3, E8-2's fluid mode, the replay of
    the week (E8-1) and E (§7.6); the record runs/pairs/<job>.json."""
    from .. import replay as rp
    from ..metrics import write_run
    p = job.params
    tier, win, mu, c = p["tier"], int(p["win"]), float(p["mu"]), int(p["c"])
    t_job = time.perf_counter()
    inst, model, ecfg, spec = build(tier, win, mu, c)
    ih = mc.instance_hash(inst)
    svc = rp.service_model(inst)
    ms = rp.market_scale(inst, svc.n_seq)
    arrs, cmeta = rp.open_cache(cache_dir(out), SERIES)
    n_sec = 60 * inst.grid.horizon_min
    _cache_check(cmeta, n_sec)
    res, fluid_s, pol = fluid_run(inst, model, ecfg, spec, c)
    write_run(res, inst, outputs.partial(run_path(out, "fluid", job.id)), full=True,
              extra_meta={"exp": EXP, "job": job.id, "policy_id": pol["id"], "params": pol["params"],
                          "info_class": pol["info_class"], "driver_inputs": pol["driver_inputs"], "tier": tier,
                          "win": win, "mu": mu, "c": c, "instance_hash": ih})
    chk3 = e8_3(res)
    plan = rp.placement(res, inst)
    chk2 = rp.check_e8_2(res, inst, plan, svc)
    t1 = time.perf_counter()
    idx = rp.StreamIndex.build(arrs["t_s"], n_sec)
    ring = rp.ring_size(svc.w_in * float(cmeta["max_inp"]) + float(cmeta["max_out"]), svc)
    copier = rp.Copier(arrs["t_s"], arrs["inp"], arrs["out"], idx, ms.gamma, svc.w_in, seed=c)
    rep = rp.replay(copier, plan, svc, ms.own_slots, n_sec, ring, progress_s=86400,
                    log=lambda m: print(f"[e8] {job.id} {m}", flush=True))
    replay_s = time.perf_counter() - t1
    fl = _fluid_components(res.components)
    err = cost_error(fl, rep["costs"])
    n_h = inst.grid.horizon_min // 60
    rec = {"job": job.id, "exp": EXP, "tier": tier, "win": win, "mu": mu, "c": c, "policy_seed": POLICY_SEED,
           "policy": pol, "seeds": dict(res.seeds), "config": CONFIG, "overrides": spec["overrides"],
           "instance_hash": ih, "horizon_min": inst.grid.horizon_min, "reduced": reduced(),
           "service": svc.record(), "scale": ms.record(), "fluid": fl,
           "fluid_components": {k: float(v) for k, v in res.components.items()},
           "replay": {k: rep[k] for k in ("n_seconds", "ring_s", "hold_max_s", "own_slots", "site_order", "counts",
                                          "tokens", "costs", "copier", "timing")},
           **err, "e8_1": rep["conservation"], "e8_2": chk2, "e8_3": chk3,
           "per_hour": {"fluid": _hourly(res.per_slot, inst.grid.slow_min, n_h), "replay": rep["per_hour"]},
           "n_leases": len(res.leases), "n_replicas": len(res.replicas), "fluid_s": fluid_s, "replay_s": replay_s,
           "engine_wall_s": res.runtime.get("wall_s"), "cache": {k: cmeta.get(k) for k in ("rows", "window", "sha256")},
           "git_revision": mc.git_revision(), "versions": mc.versions(), "wall_s": time.perf_counter() - t_job}
    outputs.dump(rec, run_path(out, "pairs", job.id))
    print(f"[e8] {job.id}: C_fluid {err['C_fluid']:.2f}, C_replay {err['C_replay']:.2f}, E {err['error']}, "
          f"E8-1 {rep['conservation']['pass']}, E8-2 {chk2['pass']}, E8-3 {chk3['pass']}; fluid {fluid_s:.1f} s, "
          f"replay {replay_s:.1f} s ({rep['counts']['copies']} copies)", flush=True)
    return {"runs": 1, "error": err["error"], "C_fluid": err["C_fluid"], "C_replay": err["C_replay"],
            "e8_1": rep["conservation"]["pass"], "e8_2": chk2["pass"], "e8_3": chk3["pass"], "fluid_s": fluid_s,
            "replay_s": replay_s, "copies": rep["counts"]["copies"], "instance_hash": ih}


# ---------------------------------------------------------------- job: the Mooncake hour (§7.7)
def peak_hour(demand: np.ndarray, fast_min: int) -> tuple[int, float]:
    """(hour index, overflow) of the clock hour of the horizon with the largest fluid overflow, the sum of d(f) over
    its fast slots (the first such hour on ties)."""
    per = 60 // fast_min
    n = len(demand) // per
    if n == 0:
        raise ValueError("peak_hour: the horizon is shorter than one hour")
    hours = np.asarray(demand[: n * per], dtype=np.float64).reshape(n, per).sum(axis=1)
    h = int(np.argmax(hours))
    return h, float(hours[h])


def run_mooncake(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One (window, prefix) of §7.7: the fluid run of tier M, mu 1, alignment 1, its peak hour, Gamma_mc, the
    replica-level replay of the Mooncake hour with or without prefix hits and the hour's E."""
    from .. import replay as rp
    p = job.params
    win, prefix, tier, mu, c = int(p["win"]), p["prefix"], p["tier"], float(p["mu"]), int(p["c"])
    if prefix not in PREFIX:
        raise ValueError(f"prefix must be one of {PREFIX}, got {prefix!r}")
    t_job = time.perf_counter()
    inst, model, ecfg, spec = build(tier, win, mu, c)
    ih = mc.instance_hash(inst)
    svc = rp.service_model(inst)
    ms = rp.market_scale(inst, svc.n_seq)
    arrs, cmeta = rp.open_cache(cache_dir(out), SERIES)
    _cache_check(cmeta, 60 * inst.grid.horizon_min)
    res, fluid_s, pol = fluid_run(inst, model, ecfg, spec, c)
    chk3 = e8_3(res)
    plan = rp.placement(res, inst)
    rplan = rp.replica_plan(res, inst)
    h, over = peak_hour(np.asarray(inst.clients.demand[0]), inst.grid.fast_min)
    S0, S1 = h * HOUR_S, (h + 1) * HOUR_S
    i0, i1 = np.searchsorted(arrs["t_s"], [float(S0), float(S1)], side="left")
    az_tok = ms.gamma * float((svc.w_in * np.asarray(arrs["inp"][i0:i1]) + np.asarray(arrs["out"][i0:i1])).sum())
    trace = rp.load_mooncake()
    tstat = trace.stats()
    mc_tok = float((svc.w_in * trace.inp + trace.out).sum())
    gamma_mc = az_tok / mc_tok
    cp = rp.mooncake_copies(trace, gamma_mc, seed=c, t0_s=float(S0))
    ring = rp.ring_size(float((svc.w_in * trace.inp + trace.out).max()), svc)
    t1 = time.perf_counter()
    rep = rp.replay_replicas(cp, trace, plan, rplan, svc, ms.own_slots, S0, S1, ring, prefix == "on")
    replay_s = time.perf_counter() - t1
    sl = slice(S0 // (60 * inst.grid.slow_min), S1 // (60 * inst.grid.slow_min))
    fl_h = {k: float(np.asarray(res.per_slot[k][sl]).sum()) for k in COMPONENTS}
    err = cost_error(fl_h, rep["costs"])
    rec = {"job": job.id, "exp": EXP, "tier": tier, "win": win, "mu": mu, "c": c, "prefix": prefix,
           "policy_seed": POLICY_SEED, "policy": pol, "seeds": dict(res.seeds), "config": CONFIG,
           "overrides": spec["overrides"], "instance_hash": ih, "reduced": reduced(), "service": svc.record(),
           "scale": ms.record(), "fluid_week": _fluid_components(res.components),
           "hour": {"index": h, "start_s": S0, "end_s": S1, "fluid_overflow_load_min": over * inst.grid.fast_min,
                    "azure_requests": int(i1 - i0), "azure_weighted_tokens_scaled": az_tok},
           "mooncake_trace": {"path": trace.path, **tstat, "weighted_tokens": mc_tok}, "gamma_mc": gamma_mc,
           "copies": cp["n_copies"], "fluid": fl_h,
           "replay": {k: rep[k] for k in ("seconds", "ring_s", "own_replicas", "own_slots", "leased_replicas",
                                          "counts", "tokens", "hits", "costs", "timing")},
           **err, "e8_1": rep["conservation"], "e8_3": chk3, "fluid_s": fluid_s, "replay_s": replay_s,
           "git_revision": mc.git_revision(), "versions": mc.versions(), "wall_s": time.perf_counter() - t_job}
    outputs.dump(rec, run_path(out, "mooncake", job.id))
    print(f"[e8] {job.id}: hour {h}, Gamma_mc {gamma_mc:.3f}, {cp['n_copies']} copies, E {err['error']}, hit ratio "
          f"{rep['hits']['hit_ratio']}, E8-1 {rep['conservation']['pass']}; replay {replay_s:.1f} s", flush=True)
    return {"runs": 1, "error": err["error"], "gamma_mc": gamma_mc, "hour": h, "e8_1": rep["conservation"]["pass"],
            "e8_3": chk3["pass"], "replay_s": replay_s, "instance_hash": ih}


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    fn = {"requests": run_requests, "pair": run_pair, "mooncake": run_mooncake}[job.params["kind"]]
    return fn(job, outputs, out)


# ---------------------------------------------------------------- manifest
def _sha256_file(path) -> str:
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def manifest_extra(out) -> dict:
    """Instance hashes of every fluid run (pair and Mooncake jobs) and the sha256 of the inputs (the config, the a12
    files the borrower series come from, a5's calibration, the Mooncake trace) with the raw Azure file's size."""
    from .. import paths
    from ..replay.requests import file_info
    from ..traces.borrowers import REQUEST_STREAMS
    hashes = {}
    for j in jobs():
        p = j.params
        if p["kind"] == "pair":
            hashes[j.id] = mc.instance_hash(build(p["tier"], p["win"], p["mu"], p["c"])[0])
        elif p["kind"] == "mooncake":
            hashes[j.id] = mc.instance_hash(build(p["tier"], p["win"], p["mu"], p["c"])[0])
    files = (paths.CONFIGS / CONFIG, paths.ANALYSIS_OUT / "a12_minute_io.npz",
             paths.ANALYSIS_OUT / "a12_sim_inputs.json", paths.ANALYSIS_OUT / "a5_reclaim_cost_calibration.json",
             paths.DATA / REQUEST_STREAMS["mooncake_conversation"][1])
    return {"instance_hashes": hashes,
            "inputs_sha256": {str(f.relative_to(paths.REPO) if paths.REPO in f.parents else f): _sha256_file(f)
                              for f in files},
            "raw_azure": file_info(paths.DATA / REQUEST_STREAMS[SERIES][1]), "reduced": reduced(),
            "settings": {k: (list(v) if isinstance(v, tuple) else v) for k, v in settings().items()}}


# ---------------------------------------------------------------- summary
def _agg(vals: list) -> dict:
    v = [float(x) for x in vals]
    return {"median": float(np.median(v)), "min": float(min(v)), "max": float(max(v)), "n": len(v)}


def _agg_null(note: str) -> dict:
    return {"median": None, "median_note": note, "min": None, "min_note": note, "max": None, "max_note": note, "n": 0,
            "by_c": {}, "alignments": [], "note": note}


def _comp_null(note: str) -> dict:
    return {"fluid": {k: None for k in COMPONENTS}, "fluid_note": note,
            "replay": {k: None for k in ("routing", "fallback", "stranding", "total")}, "replay_note": note,
            "by_c": {}, "alignments": [], "n": 0, "note": note}


def _moon_null(note: str) -> dict:
    d = {"n": 0, "note": note}
    for k in ("error", "C_fluid", "C_replay", "gamma_mc", "copies", "hit_ratio", "global_hit_ratio"):
        put(d, k, None, note)
    d.update(fluid={k: None for k in COMPONENTS}, replay={k: None for k in ("routing", "fallback", "stranding",
                                                                             "total")},
             hour={"index": None, "start_s": None}, e8_1_pass=None, e8_3_pass=None)
    return d


def summary(out) -> dict:
    """summary.json and tables.md from the 'ok' job outputs (module docstring); a listed job without an 'ok' record
    leaves its keys null with notes and is listed in meta.jobs_missing; an output present with another record is
    listed in meta.ignored_outputs and not used; an 'ok' record whose run file is missing or unreadable is listed in
    meta.outputs_missing and meta.jobs_missing."""
    out = Path(out)
    S = settings()
    js = jobs()
    recs = mc.read_records(out)
    ok = {j.id for j in js if (recs.get(j.id) or {}).get("status") == "ok"}
    ignored, unread = [], []
    pairs, moons = {}, {}
    for j in js:
        k = j.params["kind"]
        if k == "requests":
            continue
        path = run_path(out, "pairs" if k == "pair" else "mooncake", j.id)
        if j.id not in ok:
            if path.is_file():
                ignored.append({"job": j.id, "status": (recs.get(j.id) or {}).get("status"), "file": str(path.name)})
            continue
        d = mc.read_json(path)
        if d is None:
            unread.append({"job": j.id, "status": "ok", "file": str(path.relative_to(out)),
                           "note": "the record is ok but its run file is missing or unreadable (not used)"})
            continue
        if k == "pair":
            pairs[(d["tier"], int(d["win"]), num_key(d["mu"]), int(d["c"]))] = d
        else:
            moons[(int(d["win"]), d["prefix"])] = d
    error, comps, scale = {}, {}, {}
    for t in S["tiers"]:
        for w in S["windows"]:
            gam = {num_key(c): d["scale"]["gamma"] for (tt, ww, _, c), d in sorted(pairs.items())
                   if tt == t and ww == w}
            own = {num_key(c): d["scale"]["own_slots"] for (tt, ww, _, c), d in sorted(pairs.items())
                   if tt == t and ww == w}
            c0 = {num_key(c): d["scale"]["C0_loads"] for (tt, ww, _, c), d in sorted(pairs.items())
                  if tt == t and ww == w}
            scale.setdefault(t, {})[num_key(w)] = {"gamma_by_c": gam, "own_slots_by_c": own, "C0_loads_by_c": c0}
            for mu in S["mus"]:
                rows = {c: pairs.get((t, int(w), num_key(mu), c)) for c in S["alignments"]}
                have = {c: d for c, d in rows.items() if d is not None}
                ek = error.setdefault(t, {}).setdefault(num_key(w), {})
                ck = comps.setdefault(t, {}).setdefault(num_key(w), {})
                es = {c: d["error"] for c, d in have.items() if d.get("error") is not None}
                if es:
                    e = _agg(list(es.values()))
                    e.update(by_c={num_key(c): v for c, v in sorted(es.items())}, alignments=sorted(es))
                    ek[num_key(mu)] = e
                else:
                    ek[num_key(mu)] = _agg_null("no usable e8:pair output with an error value (no ok record, or "
                                                "its run file is missing)")
                if have:
                    fl = {k: float(np.median([d["fluid"][k] for d in have.values()])) for k in COMPONENTS}
                    rp_ = {k: float(np.median([d["replay"]["costs"][k] for d in have.values()]))
                           for k in ("routing", "fallback", "stranding", "total")}
                    ck[num_key(mu)] = {"fluid": fl, "replay": rp_, "n": len(have), "alignments": sorted(have),
                                       "by_c": {num_key(c): {"fluid": d["fluid"],
                                                             "replay": {k: d["replay"]["costs"][k]
                                                                        for k in ("routing", "fallback", "stranding",
                                                                                  "total")},
                                                             "C_fluid": d["C_fluid"], "C_replay": d["C_replay"]}
                                                for c, d in sorted(have.items())}}
                else:
                    ck[num_key(mu)] = _comp_null("no usable e8:pair output (no ok record, or its run file is "
                                                 "missing)")
    mooncake = {}
    for w in S["windows"]:
        for pf in PREFIX:
            d = moons.get((int(w), pf))
            tgt = mooncake.setdefault(num_key(w), {})
            if d is None:
                tgt[pf] = _moon_null("no usable e8:mooncake output (no ok record, or its run file is missing)")
                continue
            e = {"n": 1, "C_fluid": d["C_fluid"], "C_replay": d["C_replay"], "gamma_mc": d["gamma_mc"],
                 "copies": d["copies"], "global_hit_ratio": d["mooncake_trace"]["block_hit_ratio_infinite_cache"],
                 "fluid": d["fluid"], "replay": {k: d["replay"]["costs"][k] for k in ("routing", "fallback",
                                                                                      "stranding", "total")},
                 "hour": {"index": d["hour"]["index"], "start_s": d["hour"]["start_s"]},
                 "e8_1_pass": d["e8_1"]["pass"], "e8_3_pass": d["e8_3"]["pass"]}
            put(e, "error", d.get("error"), d.get("error_note"))
            put(e, "hit_ratio", d["replay"]["hits"]["hit_ratio"], "no prefix hits in this mode" if pf == "off"
                else "no block on a replica")
            tgt[pf] = e
    checks = _checks(S, pairs, moons, error, mooncake)
    meta = _meta(S, out, js, ok, ignored, unread, pairs, moons, recs, scale)
    summ = {"meta": meta, "error": error, "components": comps, "mooncake": mooncake, "checks": checks}
    mc.dump_json(summ, out / "summary.json")
    mc.write_text(tables(summ), out / "tables.md")
    return summ


def _status(n: int, n_fail: int) -> str:
    return "missing" if n == 0 else ("fail" if n_fail else "pass")


def _checks(S: dict, pairs: dict, moons: dict, error: dict, mooncake: dict) -> dict:
    from ..replay.fluid import E8_2_FLOOR_USD, E8_2_TOL
    n_pairs_exp = len(S["tiers"]) * len(S["windows"]) * len(S["mus"]) * len(S["alignments"])
    n_moon_exp = len(S["windows"]) * len(PREFIX)
    f1 = [d["job"] for d in list(pairs.values()) + list(moons.values()) if not d["e8_1"]["pass"]]
    rel = [d["e8_1"]["tokens_rel_diff"] for d in list(pairs.values()) + list(moons.values())]
    n1 = len(pairs) + len(moons)
    c1 = {"status": _status(n1, len(f1)), "claim": CHECK_CLAIMS["E8-1"], "n": n1,
          "n_expected": n_pairs_exp + n_moon_exp, "n_fail": len(f1), "failures": f1[:20],
          "max_tokens_rel_diff": max(rel) if rel else None, "pass": bool(n1 and not f1)}
    f2 = [d["job"] for d in pairs.values() if not d["e8_2"]["pass"]]
    rr = [d["e8_2"]["routing"]["rel_diff"] for d in pairs.values() if d["e8_2"]["routing"]["rel_diff"] is not None]
    rf = [d["e8_2"]["fallback"]["rel_diff"] for d in pairs.values() if d["e8_2"]["fallback"]["rel_diff"] is not None]
    rs = [d["e8_2"]["stranding"]["rel_diff"] for d in pairs.values() if d["e8_2"]["stranding"]["rel_diff"] is not None]
    c2 = {"status": _status(len(pairs), len(f2)), "claim": CHECK_CLAIMS["E8-2"], "n": len(pairs),
          "n_expected": n_pairs_exp, "n_fail": len(f2), "failures": f2[:20], "tol": E8_2_TOL,
          "floor_usd": E8_2_FLOOR_USD,
          "max_rel_diff_routing": max(rr) if rr else None, "max_rel_diff_fallback": max(rf) if rf else None,
          "stranding_max_rel_diff": max(rs) if rs else None,
          "stranding_note": "the fluid mode books the engine's stranding_fb charge on its own routing; reported, "
                            "not a pass criterion", "pass": bool(pairs and not f2)}
    f3 = [d["job"] for d in list(pairs.values()) + list(moons.values()) if not d["e8_3"]["pass"]]
    inv = sum(d["e8_3"]["n_invariant_failures"] for d in list(pairs.values()) + list(moons.values()))
    gpu = sum(d["e8_3"]["gpu_only_lease_slots"] for d in list(pairs.values()) + list(moons.values()))
    c3 = {"status": _status(n1, len(f3)), "claim": CHECK_CLAIMS["E8-3"], "n_runs": n1,
          "n_expected": n_pairs_exp + n_moon_exp, "n_fail": len(f3), "failures": f3[:20],
          "n_invariant_failures": inv, "n_gpu_only_lease_slots": gpu, "pass": bool(n1 and not f3)}
    cells = [(t, w, u, e) for t, v in error.items() for w, x in v.items() for u, e in x.items()]
    vals = [e["median"] for *_, e in cells if e["median"] is not None]
    c4 = {"status": "informative" if vals else "missing", "claim": CHECK_CLAIMS["E8-4"], "n_cells": len(cells),
          "n_cells_with_value": len(vals), "median_range": [min(vals), max(vals)] if vals else [None, None],
          "at_mu_1": {t: {w: x.get("1", {}).get("median") for w, x in v.items()} for t, v in error.items()}}
    mv = {w: {p: e["error"] for p, e in x.items()} for w, x in mooncake.items()}
    have = [e for x in mv.values() for e in x.values() if e is not None]
    c5 = {"status": "informative" if have else "missing", "claim": CHECK_CLAIMS["E8-5"], "error": mv,
          "hit_ratio": {w: x["on"]["hit_ratio"] for w, x in mooncake.items()},
          "global_hit_ratio": next((x["on"]["global_hit_ratio"] for x in mooncake.values()
                                    if x["on"]["global_hit_ratio"] is not None), None),
          "n": len(have)}
    if c4["median_range"] == [None, None]:
        c4["median_range_note"] = "no error value"
    return {"E8-1": c1, "E8-2": c2, "E8-3": c3, "E8-4": c4, "E8-5": c5}


def _meta(S: dict, out: Path, js: list, ok: set, ignored: list, unread: list, pairs: dict, moons: dict, recs: dict,
          scale: dict) -> dict:
    from ..replay.requests import cache_paths
    svc = {}
    for d in pairs.values():
        svc.setdefault(d["tier"], d["service"])
    walls = [r.get("wall_s") for j, r in recs.items() if j.startswith(f"{EXP}:pair:") and r.get("status") == "ok"]
    fl = [d["fluid_s"] for d in pairs.values()]
    rpl = [d["replay_s"] for d in pairs.values()]
    first = next((j.id for j in js if j.params["kind"] == "pair"), None)
    fr = recs.get(first) or {}

    def _t(v):
        v = [float(x) for x in v if x is not None]
        return {"median": float(np.median(v)), "max": float(max(v)), "n": len(v)} if v else \
            {"median": None, "median_note": "no ok job", "max": None, "max_note": "no ok job", "n": 0}
    cm = mc.read_json(cache_paths(cache_dir(out), SERIES)["meta"])
    unread_ids = {u["job"] for u in unread}
    t0, w0, m0, c0 = MOONCAKE["tier"], S["windows"][0], MOONCAKE["mu"], MOONCAKE["c"]
    meta = {"exp": EXP, "spec": SPEC, "git_revision": mc.git_revision(), "written": mc._now(), "reduced": S["reduced"],
            "grid": {"tiers": list(S["tiers"]), "windows": list(S["windows"]), "mus": list(S["mus"]),
                     "alignments": list(S["alignments"]), "alignments_design": list(ALIGNMENTS),
                     "policy_seed": POLICY_SEED, "horizon_min": S["horizon_min"],
                     "market_tightness": S["market_tightness"], "fast_min": FAST_MIN},
            "config": f"configs/{CONFIG}", "overrides_reference": overrides(t0, 15 if 15 in S["windows"] else w0, m0),
            "lender_model": dict(LENDER_MODEL), "engine": dict(ENGINE),
            "policy": {"id": POLICY[0], "params": dict(POLICY[1])},
            "policy_resolved": next((d.get("policy") for d in list(pairs.values()) + list(moons.values())), None),
            "tier_map": dict(TIER_MAP),
            "mooncake_point": dict(MOONCAKE), "service": svc, "scale": scale,
            "requests": None if cm is None else {k: cm.get(k) for k in ("stream", "window", "rows", "input_tokens",
                                                                       "output_tokens", "sha256", "source")},
            "mooncake_trace": next((d["mooncake_trace"] for d in moons.values()), None),
            "timings": {"pair_job_wall_s": _t(walls), "fluid_run_s": _t(fl), "replay_s": _t(rpl),
                        "first_pair_job": {"job": first, "status": fr.get("status"), "wall_s": fr.get("wall_s"),
                                           "peak_rss_mb": fr.get("peak_rss_mb")}},
            "jobs_ok": len(ok - unread_ids), "jobs_missing": [j.id for j in js if j.id not in ok or j.id in unread_ids],
            "ignored_outputs": ignored, "outputs_missing": unread}
    if S["reduced"]:
        meta["reduced_note"] = (f"{REDUCED_ENV}=1: {S['horizon_min']} min at market tightness "
                                f"{S['market_tightness']}, a smoke run, never a result")
    if cm is None:
        meta["requests_note"] = "no request cache record (e8:requests has not run)"
    if meta["policy_resolved"] is None:
        meta["policy_resolved_note"] = "no usable e8:pair or e8:mooncake output"
    if meta["mooncake_trace"] is None:
        meta["mooncake_trace_note"] = "no ok e8:mooncake output"
    return meta


def tables(summ: dict) -> str:
    meta = summ["meta"]
    head = (f"# E8: fluid-model fidelity ({SPEC})\n\n" + ("**Reduced run (smoke test), not a result.**\n\n"
                                                           if meta["reduced"] else ""))
    rows = []
    for t, v in summ["error"].items():
        for w, x in v.items():
            for u, e in x.items():
                rows.append([t, w, u, e.get("median"), e.get("min"), e.get("max"), e.get("n")])
    crow = []
    for t, v in summ["components"].items():
        for w, x in v.items():
            for u, e in x.items():
                f, r = e.get("fluid") or {}, e.get("replay") or {}
                crow.append([t, w, u, f.get("routing"), r.get("routing"), f.get("fallback"), r.get("fallback"),
                             f.get("stranding"), r.get("stranding"), f.get("total"), e.get("n")])
    mrow = [[w, p, e.get("error"), e.get("C_fluid"), e.get("C_replay"), e.get("gamma_mc"), e.get("hit_ratio"),
             (e.get("hour") or {}).get("index")] for w, x in summ["mooncake"].items() for p, e in x.items()]
    chk = [[k, v["status"]] for k, v in summ["checks"].items()]
    return (head + "## Relative cost error E = (C_replay - C_fluid) / C_replay (overflow accounting)\n\n"
            + mc.md_table(["tier", "window (min)", "mu / beta~", "median", "min", "max", "n"], rows)
            + "\n## Components (USD, medians over the alignments)\n\n"
            + mc.md_table(["tier", "window", "mu", "routing fluid", "routing replay", "fallback fluid",
                           "fallback replay", "stranding fluid", "stranding replay", "C_fluid", "n"], crow)
            + "\n## Mooncake hour (tier M, mu / beta~ = 1, alignment 1)\n\n"
            + mc.md_table(["window", "prefix", "E", "C_fluid (hour)", "C_replay (hour)", "Gamma_mc", "hit ratio",
                           "hour"], mrow)
            + "\n## Checks\n\n" + mc.md_table(["check", "status"], chk))


def main(argv=None) -> int:
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=argv, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
