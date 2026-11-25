"""Q44 study: practical Sublet under a worst-case guard (design/q44_practical_sublet.md §5).

One cell-mode per process. A block file (sublet/experiments/q44_blocks/<block>.json) names the
instances (config, overrides, config seeds, tuning cells), the grid, the lender modes, the policy tags,
the seeds and the lower bounds; the tags and modes are defined in POLICIES and MODES below (§5.3, §5.4).

  python -m sublet.experiments.q44_study --list [BLOCK ...]       jobs, one per line: '<pool|alone> <job id>'
  python -m sublet.experiments.q44_study --job JOB [--out DIR]    run one job (a cell-mode, a family
                                                                 instance-mode, or a lower-bound job)
  python -m sublet.experiments.q44_study --record-failure JOB --exit-code RC
                                                                 a job killed by the cap (exit 137) or failed
  python -m sublet.experiments.q44_study --manifest [BLOCK ...]   manifest.json (block files, versions, jobs)
  python -m sublet.experiments.q44_study --describe [BLOCK ...]   cell-modes, runs and jobs per block
  python -m sublet.experiments.q44_study --estimate [BLOCK ...] [--workers 1|2]
                                                                 the jobs with estimated wall times and
                                                                 the totals (EST_RUN_S; nothing is run)

Job ids: '<block>:<instance>:c<c>:<mode>' (the runs of one cell-mode), the same with ':lb' (the lower
bound of an oblivious schedule), and '<block>:<family instance>:<mode>' (a family instance-mode of F1-F3).
Tier 1 is Q0 (the checks V1) and Q1-Q6; Tier 2 blocks (T2_*) run only when named (run_q44_study.sh).

Outputs (§5.5) under code/sim/out/q44_study/, or SUBLET_Q44_DIR (or --out):
  runs/<block>/<instance>/<grid>/<mode>/<tag>_c<c>_l<l>_p<p>.json  one per run, written by
      drivers/run.py (git revision, run-spec hash, parameters, seeds) and rewritten compactly with a
      'q44' object: block, cell, tuning flag, grid, mode, overrides, lender model, grouped components,
      realized intensity (announcements per site-day, lease lives), leases and re-buys, the ledger's
      plan class P1 flag, instance and schedule hashes, wall time, and for A8 the certificate of §3.10.
      BL2 (runner 'siloed') writes drivers/run.py's per-borrower files and <tag>_c<c>_l<l>_p<p>_sum.json,
      which carries the 'q44' object. Family runs (from_core instances, no config file) are written with
      metrics.write_run and the same meta.
  runs/.../cell_c<c>.json         per cell-mode: instance hash, schedule hash (BL0a's realized sets),
                                  BL0a's total, per-tag status and wall time, peak RSS.
  lb/<block>/<instance>/<mode>/lb_c<c>_l<l>.json   the LB of a schedule that does not depend on the run
                                  (LP of the cohort MILP on BL0a's realized schedule, merged relaxation
                                  under L-eg; BL8's MILP in block T2_bl8; core.opt_eager on F3; fam.opt_dp
                                  on F2), and per run <tag>_c<c>_l<l>_p<p>.json under L-ad and on F1 (§5.5).
  jobs/<job>.json                 status, wall time, peak RSS, runs and errors of each job.
The summary (D1-D6, checks V1-V7, tables, figures) is q44_summary.py.

Rules (§5.4, §3.10): every engine run has check_invariants on (V7); lender seeds equal config seeds
('config'); policy seeds 0-2 on the trace-driven instances; families as in §5.2. Grid '1min' is the
instances' 1-min routing grid (every cost comparison); 'slow' overrides time.fast_slot_min = 5 (the LP's
grid; ratios to the LB only there, with violations absorbed). The B0 of tag PS-G-3B0 is three times
guard.b0_auto of the public view (§3.10). An error of one policy is recorded and the job goes on.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import copy
import dataclasses
import hashlib
import json
import math
import re
import resource
import sys
import time
import traceback
from collections import Counter
from pathlib import Path
from typing import Optional

import numpy as np

from ..paths import SIM_OUT, import_ref

OUT = SIM_OUT / "q44_study"
BLOCKS_DIR = Path(__file__).resolve().parent / "q44_blocks"
TIER1 = ("Q0", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6")
NOTE = "design/q44_practical_sublet.md"
CERT_TOL = 1e-9                       # relative tolerance of the certificate checks (§3.10, V6)

# ---------------------------------------------------------------- catalogs (§5.3, §5.4)
GRIDS = {"1min": {}, "slow": {"time.fast_slot_min": 5}, "core": None}

# lender modes of the trace-driven instances (§5.3). oblivious: the realized schedule does not depend on
# the run (one LB per schedule); stress: counted in W0 (§5.5); lb: whether an LB is meaningful
MODES = {
    "L-tr": {"lender_model": {"schedule": "trace", "params": {}}, "oblivious": True, "stress": False, "lb": True},
    "L-eg": {"lender_model": {"schedule": "eager", "params": {}}, "oblivious": True, "stress": True, "lb": True,
             "merged": True},
    "L-ss": {"lender_model": {"schedule": "safe_site", "params": {"D_slots": 12, "k": 2}}, "oblivious": True,
             "stress": True, "lb": True},
    "L-iid-0.0124": {"lender_model": {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.0124}},
                     "oblivious": True, "stress": False, "lb": True},
    "L-iid-0.05": {"lender_model": {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.05}},
                   "oblivious": True, "stress": True, "lb": True},
    "L-iid-0.2": {"lender_model": {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.2}},
                  "oblivious": True, "stress": True, "lb": True},
    "L-co": {"lender_model": {"schedule": "correlated", "params": {"p_sh": 1.0, "groups": "all"}},
             "oblivious": True, "stress": True, "lb": True},
    "L-vr": {"lender_model": {"schedule": "trace", "params": {}, "violations": "reclaim"}, "oblivious": False,
             "stress": False, "lb": False},
    "L-rf": {"lender_model": {"schedule": "trace", "params": {}, "on_unavailable": "refuse"}, "oblivious": True,
             "stress": False, "lb": True, "refuse": True},
    "L-ad": {"lender_model": {"schedule": "adaptive", "params": {}}, "oblivious": False, "stress": False,
             "lb": True},
}
# lender modes of the families (§5.2): lender seeds 'paired' (lender seed = policy seed) or fixed at 0
FAMILY_MODES = {
    "F-ad": {"schedule": "adaptive", "params": {}, "lender_seeds": "fixed", "oblivious": False},
    "F-ss": {"schedule": "safe_site", "params": {}, "lender_seeds": "paired", "oblivious": True},
    "F-iid": {"schedule": "iid_step", "params": {"p": 0.5}, "lender_seeds": "paired", "oblivious": True},
    "F-eg": {"schedule": "eager", "params": {}, "lender_seeds": "fixed", "oblivious": True},
}

SQRT2 = math.sqrt(2.0)
# policy tags (§5.4): registry id, parameters, information model (default I1)
POLICIES = {
    "BL0a": {"id": "BL0a", "params": {}},
    "BL1": {"id": "BL1", "params": {}},
    "BL2": {"id": "BL2", "params": {}},
    "BL5": {"id": "BL5", "params": {}},
    "A6": {"id": "A6", "params": {}},
    "A2": {"id": "A2", "params": {}},
    "A2-th": {"id": "A2", "params": {"rbar": "theory"}},
    "A3": {"id": "A3", "params": {}},
    "RR_RENEW": {"id": "RR_RENEW", "params": {}},
    "MARKING": {"id": "MARKING", "params": {}, "information": "I2"},
    "PS": {"id": "A7", "params": {}},
    "PS-G": {"id": "A8", "params": {}},
    "PS-G1": {"id": "A8", "params": {"S_rbar": 1}},
    "PS-GR": {"id": "A8", "params": {"safe": "pd"}},
    "BL1-G": {"id": "A8", "params": {"inner": "BL1"}},
    "BL5-G": {"id": "A8", "params": {"inner": "BL5"}},
    # Tier 2 (§5.5, §7.3)
    "PS-GN": {"id": "A8", "params": {"test": "T1", "kappa": None}},
    "PS-G-g1.1": {"id": "A8", "params": {"gamma": 1.1}},
    "PS-G-g1.25": {"id": "A8", "params": {"gamma": 1.25}},
    "PS-G-k5": {"id": "A8", "params": {"kappa": 5.0}},
    "PS-G-k30": {"id": "A8", "params": {"kappa": 30.0}},
    "PS-G-3B0": {"id": "A8", "params": {"B0": "3x_auto"}},
    # Tier 2, block T2_t0g: test T0g (§3.4, §3.10) for the A8 rows of Q1, Q2 and Q6, paired in q44_summary with
    # the Tier 1 rows of the same cells, modes and seeds (T0G_PAIRS). Historical: run at commit d2a538d, when T0 was
    # A8's default and T0g had no wind-down reserve; since T0g became the default (decision of 2026-10-17) these
    # tags have the default parameters
    "PS-G-T0g": {"id": "A8", "params": {"test": "T0g"}},
    "BL1-G-T0g": {"id": "A8", "params": {"inner": "BL1", "test": "T0g"}},
    "BL5-G-T0g": {"id": "A8", "params": {"inner": "BL5", "test": "T0g"}},
    # the former default test T0 (sound on the core only), with its wind-down rule 'keep' (wind_down 'auto'), as the
    # T0 partners of the default tags for runs made after T0g became the default (T0_PARTNERS)
    "PS-G-T0": {"id": "A8", "params": {"test": "T0"}},
    "BL1-G-T0": {"id": "A8", "params": {"inner": "BL1", "test": "T0"}},
    "BL5-G-T0": {"id": "A8", "params": {"inner": "BL5", "test": "T0"}},
}
# T0g tag of block T2_t0g -> its T0 partner of Q1, Q2 and Q6 as run at commit d2a538d (same parameters except the test)
T0G_PAIRS = {"PS-G-T0g": "PS-G", "BL1-G-T0g": "BL1-G", "BL5-G-T0g": "BL5-G"}
# default A8 tag -> its T0 variant; q44_summary.t0g_pairs pairs runs by base tag (BASE_TAGS) and the test that the
# run's certificate records, so both the historical pairs and these are found
T0_PARTNERS = {"PS-G": "PS-G-T0", "BL1-G": "BL1-G-T0", "BL5-G": "BL5-G-T0"}
BASE_TAGS = {**{t: t for t in T0_PARTNERS}, **dict(T0G_PAIRS), **{b: a for a, b in T0_PARTNERS.items()}}
# A8's defaults as the note fixes them for PS-G (§5.4), since the decision of 2026-10-17 (test T0g with the
# wind-down reserve, reserve true, wind_down 'auto' = 'adaptive'; Theorem W needs reserve true); the summary compares
# the resolved parameters
GUARD_DEFAULTS = {"inner": "A7", "safe": "fb+pd", "S_rbar": "theory", "gamma": 1.0, "gamma_T11": 1.0 + 1.0 / SQRT2,
                  "test": "T0g", "wind_down": "auto", "reserve": True, "B0": "auto", "kappa": 10.0}
# the defaults of the Tier 1 runs and of T2_t0g's partners (commits 9cf16de to d2a538d: test T0, no wind_down)
GUARD_DEFAULTS_T0 = {"inner": "A7", "safe": "fb+pd", "S_rbar": "theory", "gamma": 1.0, "gamma_T11": 1.0 + 1.0 / SQRT2,
                     "test": "T0", "B0": "auto", "kappa": 10.0}
LB_KINDS = (None, "per_schedule", "per_run", "milp", "exact")
BLOCK_KEYS = ("block", "tier", "description", "grid", "lb", "policies", "policy_seeds", "modes", "instances",
              "families", "milp", "ref_block", "lb_only", "note")
INSTANCE_KEYS = ("id", "family", "config", "overrides", "config_seeds", "tuning_seeds", "extra_policies",
                 "exclude_policies", "modes", "policies", "ref_block", "note")   # ref_block: overrides the block's
FAMILY_KEYS = ("id", "kind", "m", "rho", "tau", "H", "T", "beta", "modes", "policy_seeds", "exclude_policies",
               "note")


# ---------------------------------------------------------------- small helpers
def out_root(out=None) -> Path:
    """The study's output folder: `out`, else SUBLET_Q44_DIR, else code/sim/out/q44_study. A relative path is
    made absolute against the working directory here, because drivers.run resolves a relative `out_dir`
    against the repository root, which would split one job's files across two folders."""
    if out is not None:
        return Path(out).resolve()
    return Path(os.environ.get("SUBLET_Q44_DIR") or OUT).resolve()


def blocks_dir(d=None) -> Path:
    return Path(d) if d is not None else Path(os.environ.get("SUBLET_Q44_BLOCKS") or BLOCKS_DIR)


def _peak_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def _git_revision():
    from ..metrics import _git_revision as g
    try:
        return g()
    except Exception:          # informative only
        return None


def _versions() -> dict:
    from ..metrics import _versions as v
    return v()


def _jsonable(x):
    from ..metrics import _jsonable as j
    return j(x)


def _dump(obj, path: Path, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(_jsonable(obj), separators=(",", ":"), allow_nan=False) if compact else \
        json.dumps(_jsonable(obj), indent=1, allow_nan=False)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(txt + "\n")
    tmp.replace(path)


def job_file_name(job_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.\-]+", "__", job_id) + ".json"


def _fam_instance_id(fam: dict, **v) -> str:
    if fam["kind"] == "c3p5":
        return f"{fam['id']}_b{v['beta']:g}_T{v['T']}"
    return f"{fam['id']}_m{v['m']}_r{v['rho']:g}"


# ---------------------------------------------------------------- blocks and jobs
def load_block(name, bdir=None) -> dict:
    """A block (§5.5, Run matrix) by name (a file <name>.json in the blocks folder) or path, validated."""
    p = Path(name)
    if not p.suffix:
        p = blocks_dir(bdir) / f"{name}.json"
    try:
        b = json.loads(p.read_text())
    except FileNotFoundError:
        raise SystemExit(f"q44_study: block file {p} not found") from None
    bad = [k for k in b if k not in BLOCK_KEYS]
    if bad:
        raise ValueError(f"block {p.name}: unknown key(s) {bad}; allowed {list(BLOCK_KEYS)}")
    if b.get("grid") not in GRIDS:
        raise ValueError(f"block {p.name}: grid must be one of {list(GRIDS)}, got {b.get('grid')!r}")
    if b.get("lb") not in LB_KINDS:
        raise ValueError(f"block {p.name}: lb must be one of {list(LB_KINDS)}, got {b.get('lb')!r}")
    tags = list(b.get("policies") or [])
    for inst in b.get("instances") or []:
        bad = [k for k in inst if k not in INSTANCE_KEYS]
        if bad:
            raise ValueError(f"block {p.name}, instance {inst.get('id')}: unknown key(s) {bad}")
        tags += list(inst.get("extra_policies") or []) + list(inst.get("policies") or [])
        for md in inst.get("modes") or []:
            if md not in MODES:
                raise ValueError(f"block {p.name}: unknown mode {md!r}")
    for fam in b.get("families") or []:
        bad = [k for k in fam if k not in FAMILY_KEYS]
        if bad:
            raise ValueError(f"block {p.name}, family {fam.get('id')}: unknown key(s) {bad}")
        for md in fam.get("modes") or []:
            if md not in FAMILY_MODES:
                raise ValueError(f"block {p.name}: unknown family mode {md!r}")
    for md in b.get("modes") or []:
        if md not in MODES:
            raise ValueError(f"block {p.name}: unknown mode {md!r}")
    unknown = sorted({t for t in tags if t not in POLICIES})
    if unknown:
        raise ValueError(f"block {p.name}: unknown policy tag(s) {unknown}; known {list(POLICIES)}")
    b["_path"] = str(p)
    b["_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    return b


def instance_policies(block: dict, inst: dict) -> list[str]:
    """The tags run on one instance of a block: the instance's own list or the block's, plus its extra
    tags, minus its exclusions, with BL0a first (the cell record needs BL0a's run)."""
    tags = list(inst.get("policies") or block.get("policies") or [])
    tags += [t for t in inst.get("extra_policies") or [] if t not in tags]
    tags = [t for t in tags if t not in set(inst.get("exclude_policies") or [])]
    if not block.get("lb_only"):
        tags = ["BL0a"] + [t for t in tags if t != "BL0a"]
    return tags


def instance_modes(block: dict, inst: dict) -> list[str]:
    return list(inst.get("modes") or block.get("modes") or [])


def list_jobs(block: dict) -> list[dict]:
    """The jobs of a block in run order: per instance, config seed and mode one 'cells' job (all tags,
    all policy seeds), then one 'lb' job per oblivious cell-mode when the block asks for per-schedule
    LBs or BL8's MILP; per family instance and mode one 'family' job. LP and MILP jobs, and cell-mode
    jobs with per-run LPs, are marked alone (run with no other job, §5.5)."""
    out = []
    name = block["block"]
    lb = block.get("lb")
    for inst in block.get("instances") or []:
        for c in inst["config_seeds"]:
            for md in instance_modes(block, inst):
                base = {"block": name, "instance": inst["id"], "c": int(c), "mode": md}
                if not block.get("lb_only"):
                    out.append({**base, "id": f"{name}:{inst['id']}:c{c}:{md}", "kind": "cells",
                                "alone": lb == "per_run" and md == "L-ad"})
                if lb in ("per_schedule", "milp") and MODES[md]["lb"] and MODES[md]["oblivious"]:
                    out.append({**base, "id": f"{name}:{inst['id']}:c{c}:{md}:lb", "kind": "lb", "alone": True})
    for fam in block.get("families") or []:
        for v in family_instances(fam):
            fid = _fam_instance_id(fam, **v)
            for md in fam["modes"]:
                out.append({"block": name, "instance": fid, "mode": md, "family": fam["id"], "values": v,
                            "id": f"{name}:{fid}:{md}", "kind": "family", "alone": False})
    return out


def family_instances(fam: dict) -> list[dict]:
    if fam["kind"] == "c3p5":
        return [{"beta": float(b), "T": int(T)} for T in fam["T"] for b in fam["beta"]]
    return [{"m": int(m), "rho": float(r)} for m in fam["m"] for r in fam["rho"]]


def find_job(job_id: str, bdir=None) -> tuple[dict, dict]:
    block = load_block(job_id.split(":", 1)[0], bdir)
    for j in list_jobs(block):
        if j["id"] == job_id:
            return block, j
    raise SystemExit(f"q44_study: no job {job_id!r} in block {block['block']}")


# ---------------------------------------------------------------- hashes and per-run metrics
_HASH_SKIP = {"name", "config", "seed", "notes"}


def _hash_update(h, x) -> None:
    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        h.update(type(x).__name__.encode())
        for f in dataclasses.fields(x):
            if f.name in _HASH_SKIP:
                continue
            h.update(f.name.encode())
            _hash_update(h, getattr(x, f.name))
    elif isinstance(x, np.ndarray):
        h.update(f"nd{x.dtype}{x.shape}".encode())
        h.update(np.ascontiguousarray(x).tobytes())
    elif isinstance(x, dict):
        h.update(b"{")
        for k in sorted(x, key=str):
            h.update(str(k).encode())
            _hash_update(h, x[k])
        h.update(b"}")
    elif isinstance(x, (list, tuple)):
        h.update(b"[")
        for v in x:
            _hash_update(h, v)
        h.update(b"]")
    else:
        h.update(repr(x).encode())


def instance_hash(inst) -> str:
    """sha256 of the built instance (every field except name, config, seed and the builder notes), so
    that two config seeds that build the same instance hash equal (§5.2, duplicate cells)."""
    h = hashlib.sha256()
    _hash_update(h, inst)
    return h.hexdigest()


def schedule_hash(sched) -> str:
    """sha256 of a realized schedule's announcement sets."""
    h = hashlib.sha256()
    _hash_update(h, [np.asarray(r, dtype=np.int64) for r in sched.R])
    return h.hexdigest()


def intensity(res, inst) -> dict:
    """Realized intensity (§5.5): announcements per revocable site and day of the realized schedule,
    and the leases' lives."""
    rev = [i for i, s in enumerate(inst.sites) if s.kind != "protected"]
    days = inst.grid.horizon_min / 1440.0
    ann = int(sum(len(res.schedule.R[i]) for i in rev))
    lives = [L.end_min - L.start_min for L in res.leases]
    rec = [L.end_min - L.start_min for L in res.leases if L.end_cause == "reclaim"]
    return {"announcements": ann, "revocable_sites": len(rev),
            "announcements_per_site_day": ann / (len(rev) * days) if rev and days > 0 else None,
            "mean_lease_life_min": float(np.mean(lives)) if lives else None,
            "median_lease_life_min": float(np.median(lives)) if lives else None,
            "mean_reclaimed_lease_life_min": float(np.mean(rec)) if rec else None}


def lease_stats(res, inst) -> dict:
    """Leases by end cause and re-buys: a lease bought within one slow slot after the death of a lease of
    the same LLM by reclaim or violation (§5.5)."""
    llm_of: dict = {}
    for r in res.replicas:
        llm_of.setdefault(r.lease_id, r.llm)
    deaths = [(L.end_min, llm_of.get(L.id)) for L in res.leases if L.end_cause in ("reclaim", "violation")]
    slow = inst.grid.slow_min
    rebuys = 0
    for L in res.leases:
        j = llm_of.get(L.id)
        if any(d <= L.start_min <= d + slow and jj == j for d, jj in deaths):
            rebuys += 1
    return {"leases": len(res.leases), "by_end_cause": dict(Counter(L.end_cause for L in res.leases)),
            "rebuys": rebuys, "replicas": len(res.replicas)}


def plan_class_p1(res, inst) -> bool:
    """Plan class P1 from the ledger (design §5.2.4): every lease carries at most one replica, of g_j GPUs
    of its LLM, and no lease slot is GPU-only. A run outside P1 can cost less than the P1 benchmark
    (§5.5, V4)."""
    reps = Counter(r.lease_id for r in res.replicas)
    llm_of = {r.lease_id: r.llm for r in res.replicas}
    if any(v > 1 for v in reps.values()):
        return False
    for L in res.leases:
        j = llm_of.get(L.id)
        if j is not None and L.gpus != inst.llms[j].g:
            return False
    return int(res.metrics.get("gpu_only_lease_slots", 0)) == 0


def grouped(components: dict) -> dict:
    """Components of §5.5: lease, loading, routing, fallback, stranding, total."""
    c = components
    return {"lease": float(c.get("lease_prepaid", 0.0) + c.get("lease_rent", 0.0)),
            "loading": float(c.get("loading", 0.0)), "routing": float(c.get("routing", 0.0)),
            "fallback": float(c.get("fallback", 0.0)),
            "stranding": float(sum(v for k, v in c.items() if k.startswith("stranding_"))),
            "total": float(c.get("total", 0.0))}


def fallback_per_slot(inst) -> np.ndarray:
    """(T_slow,) Q(t): the slot's exact all-fallback cost sum_c q_{j_c} sum_f d_c(f) Δf / 60 (§3.10)."""
    g = inst.grid
    q = np.array([L.q_usd_per_h for L in inst.llms], dtype=np.float64)[np.asarray(inst.clients.llm, dtype=np.int64)]
    d = np.asarray(inst.clients.demand, dtype=np.float64)
    f = (q[:, None] * d).sum(axis=0) * g.fast_min / 60.0 if d.size else np.zeros(g.T_fast)
    return f[: g.T_slow * g.phi].reshape(g.T_slow, g.phi).sum(axis=1)


def rent_bound_per_slot(res, inst) -> np.ndarray:
    """(T_slow,) the T0 rent term recomputed from the lease records: over the leases held after the slot's
    actions (bought at or before t, not ended by t Δs), g a max{0, min((t+1) Δs, death) - max(t Δs, b_L)} / 60
    with b_L the end of the billed term and the death minute once the lease is announced (§3.10)."""
    g = inst.grid
    Ds, T = g.slow_min, g.T_slow
    out = np.zeros(T)
    for L in res.leases:
        rate = float(inst.price[L.site, L.contract]) * L.gpus / 60.0
        for t in range(int(L.start_slot), T):
            t0m, t1m = t * Ds, (t + 1) * Ds
            if L.end_min <= t0m:
                break
            hi = t1m
            if L.announce_slot is not None and L.announce_slot <= t and L.death_min is not None:
                hi = min(hi, int(L.death_min))
            span = hi - max(t0m, int(L.prepaid_end_min))
            if span > 0:
                out[t] += rate * span
    return out


def b0_auto_of(inst, information: str = "I1") -> float:
    """guard.b0_auto of the instance's public view: one fresh k* replica per client (§3.10)."""
    from ..algos.guard import b0_auto
    from ..instance import public_view
    return float(b0_auto(public_view(inst, information)))


# ---------------------------------------------------------------- the certificate (§3.10)
def _rget(rep: dict, *paths, default=None):
    for p in paths:
        cur = rep
        ok = True
        for part in p.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur is not None:
            return cur
    return default


def certificate(res, inst, rep: dict, core_exact: bool) -> dict:
    """The per-run certificate of an A8 run (§3.10) from the ledger and A8's report.

    ALG(t) is the ledger's cumulative cost; C_S(t), B(t) (E-mode slots; B(T) from safe.B_curve), a-hat(t),
    t_a and W_S(t_a) come from the report; m(t) = max{0, ALG(t) - a-hat(t)} is recomputed from the ledger at every executed slot.
    Checks: the core bound ALG(T) <= C_S(T) + (gamma - 1) C_S(t_a - 1) + W_S(t_a) + B(t_a - 1) + m(t_a - 1)
    (gamma C_S(T) + B(T) + m(T) without an abort, Theorem G2 (a)); the E-mode check ALG(t) <= gamma C_S(t) +
    B(t) + m(t) at every executed slot; the S-mode excess [ALG(T) - ALG(t_a - 1)] - [W_S(t_a) + C_S(T) -
    C_S(t_a - 1)]; under T0 m(t) <= the slot's stranding charges (= 0 on exact core exports); under T1
    m(t) <= the slot's lease_rent + routing + fallback + stranding; under T0g (sound, guard.T0gBound)
    m(t) = 0, in the full model as well. T0g runs whose report records the wind-down reserve R(t) (guard.reserve;
    runs after the decision of 2026-10-17; guard.py, Theorem W) also get: ALG(t) + R(t) <= gamma C_S(t) +
    B(t) + m(t) at every executed slot (e_mode_reserve_ok), the budget R(t_a - 1), the wind-down cost (= the S-mode
    excess) and wind_down_ok = (wind-down cost <= budget), and proven_case (no abort, or S follows FB at every slot
    from t_a on under wind_down 'adaptive' or 'release': the case Theorem W proves); 'held' then also requires
    e_mode_reserve_ok and, in the proven case, wind_down_ok. T0g runs without it (block T2_t0g at commit d2a538d)
    keep the earlier checks. On exact core exports (core_exact)
    also a-hat(t) recomputed from the ledger and the lease records (purchases charged at t, the T0 rent
    term and Q(t)), with m recomputed from it (V6), Corollary G3's bound for T0 with a capped allowance,
    and B_on(T) for Lemma G5 (compared with the exact OPT by the family job); under T0g the recomputed T0
    value bounds the reported a-hat(t) at every executed slot (T0g <= T0 on core exports), m = 0 and
    Corollary G3 apply. 'held' = core bound and E-mode check (plus, on exact core exports, the S-mode excess,
    the recomputed checks and m = 0 under T0 and T0g; in the full model under T0g, m = 0)."""
    ps = res.per_slot
    tot = np.asarray(ps["total"], dtype=np.float64)
    alg = np.cumsum(tot)
    T = len(alg)
    gd = rep.get("guard") or {}
    test = _rget(rep, "test", "guard.test")
    gamma = float(_rget(rep, "gamma", "guard.gamma", default=float("nan")))
    kappa = _rget(rep, "kappa", "guard.kappa")
    ta = _rget(rep, "t_a", "guard.t_a")
    C_S = np.asarray(_rget(rep, "safe.C_S_curve", "C_S_curve", default=[]), dtype=np.float64)
    slots = list(gd.get("slots") or [])
    missing = [k for k, v in (("test", test), ("C_S_curve", C_S.size or None), ("guard.slots", slots or None),
                              ("guard.a_hat", gd.get("a_hat")), ("guard.B", gd.get("B"))) if v is None]
    if missing or len(C_S) < T:
        return {"available": False, "missing": missing or [f"C_S_curve has {len(C_S)} of {T} slots"], "held": None}
    B = np.full(T, np.nan)
    ah = np.full(T, np.nan)
    for s, b, a in zip(slots, gd["B"], gd["a_hat"]):
        if 0 <= int(s) < T:
            B[int(s)], ah[int(s)] = float(b), float(a)
    ta = None if ta is None else int(ta)
    executed = [int(s) for s in slots if ta is None or int(s) < ta]
    m = np.zeros(T)
    for t in executed:
        m[t] = max(0.0, alg[t] - ah[t])

    def at(a, t):
        return 0.0 if t < 0 else float(a[t])

    scale = max(1.0, float(abs(alg[-1])), float(np.nanmax(np.abs(C_S))) if C_S.size else 1.0)
    tol = CERT_TOL * scale
    e_ex = [alg[t] - (gamma * C_S[t] + B[t] + m[t]) for t in executed]
    e_max = float(max(e_ex)) if e_ex else None
    W = _rget(rep, "W_S_t_a", "at_abort.W_S")
    if ta is None:
        rhs = gamma * C_S[T - 1] + B[T - 1] + m[T - 1]
        s_ex = None
    else:
        W = float(W) if W is not None else float("nan")
        rhs = C_S[T - 1] + (gamma - 1.0) * at(C_S, ta - 1) + W + at(B, ta - 1) + at(m, ta - 1)
        s_ex = float((alg[T - 1] - at(alg, ta - 1)) - (W + C_S[T - 1] - at(C_S, ta - 1)))
    core_ok = bool(alg[T - 1] <= rhs + tol)
    e_ok = bool(e_max is None or e_max <= tol)
    # B(T): the report's allowance at every slot (safe.B_curve; guard.B covers only the slots through t_a)
    B_curve = _rget(rep, "safe.B_curve")
    if B_curve is not None and len(B_curve) >= T:
        B_T = float(B_curve[T - 1])
    else:
        B_T = None if not np.isfinite(B[T - 1]) else float(B[T - 1])
    strand = sum(np.asarray(ps[k], dtype=np.float64) for k in ps if str(k).startswith("stranding_"))
    running = sum(np.asarray(ps[k], dtype=np.float64) for k in ("lease_rent", "routing", "fallback")) + strand
    m_ex = [t for t in executed if np.isfinite(ah[t])]
    if test == "T0":
        m_over = max((m[t] - strand[t] for t in m_ex), default=0.0)
    elif test == "T0g":
        m_over = max((m[t] for t in m_ex), default=0.0)             # sound: m = 0 (T0gBound)
    else:
        m_over = max((m[t] - running[t] for t in m_ex), default=0.0)
    out = {"available": True, "test": test, "gamma": gamma, "kappa": kappa, "t_a": ta, "aborted": ta is not None,
           "ALG_T": float(alg[-1]), "C_S_T": float(C_S[T - 1]), "B_T": B_T,
           "W_S_t_a": W if ta is not None else None, "core_bound_rhs": float(rhs), "core_bound_ok": core_ok,
           "core_bound_slack": float(rhs - alg[T - 1]), "e_mode_max_excess": e_max, "e_mode_ok": e_ok,
           "s_mode_excess": s_ex, "m_max": float(max((m[t] for t in executed), default=0.0)),
           "m_over_allowed_max": float(m_over), "m_ok": bool(m_over <= tol),
           "executed_slots": len(executed), "tol": tol,
           "drops_after_t_a": _rget(rep, "exec.precheck"), "refusals_after_t_a": _rget(rep, "exec.refused"),
           "switches_after_t_a": _rget(rep, "safe.switches_after_t_a"),
           "followed": _rget(rep, "safe.followed"), "mode": _rget(rep, "mode")}
    B_on = _rget(rep, "safe.B_on")
    if B_on:
        out["B_on_T"] = float(B_on[-1])
    held = core_ok and e_ok
    # T0g with the wind-down reserve (runs after the decision of 2026-10-17; guard.py module docstring, Theorem W):
    # the test is a-hat(t) + R(t) <= gamma C_S(t) + B(t), so ALG(t) + R(t) <= gamma C_S(t) + B(t) + m(t) at every
    # executed slot, and when S follows FB at every slot from t_a on under wind_down 'adaptive' or 'release' the
    # wind-down cost (the S-mode excess) is at most the budget R(t_a - 1), which gives the core bound with m = 0
    Rl = gd.get("reserve")
    reserve = test == "T0g" and Rl is not None and bool(rep.get("reserve", True))
    out["reserve"] = bool(reserve)
    if reserve:
        Rv = np.full(T, np.nan)
        for s, rv in zip(slots, Rl):
            if 0 <= int(s) < T:
                Rv[int(s)] = float(rv)
        er = [alg[t] + Rv[t] - (gamma * C_S[t] + B[t] + m[t]) for t in executed]
        er_max = float(max(er)) if er else None
        fol = _rget(rep, "safe.followed") or []
        fb_after = ta is None or all(w == "FB" for w, t0, n in fol if int(t0) + int(n) > ta)
        wd = _rget(rep, "wind_down")
        budget = None if ta is None else at(Rv, ta - 1)
        proven = ta is None or (fb_after and wd in ("adaptive", "release"))
        wd_ok = ta is None or (s_ex is not None and s_ex <= budget + tol)
        out.update(reserve_max=float(np.nanmax(Rv)) if np.any(np.isfinite(Rv)) else 0.0,
                   e_mode_reserve_max_excess=er_max, e_mode_reserve_ok=bool(er_max is None or er_max <= tol),
                   wind_down=wd, budget_t_a=budget, wind_down_cost=s_ex, wind_down_ok=bool(wd_ok),
                   fb_after_t_a=bool(fb_after), proven_case=bool(proven))
        held = held and out["e_mode_reserve_ok"] and (wd_ok or not proven)
    if core_exact and test == "T0g":
        buy = np.asarray(ps["lease_prepaid"], dtype=np.float64) + np.asarray(ps["loading"], dtype=np.float64)
        Q = fallback_per_slot(inst)
        rb = rent_bound_per_slot(res, inst)
        ah_t0 = {t: at(alg, t - 1) + buy[t] + rb[t] + Q[t] for t in executed}
        out["recomputed"] = {"a_hat_minus_T0_rec_max": float(max((ah[t] - ah_t0[t] for t in executed), default=0.0)),
                             "e_mode_max_excess": e_max}
        rec_ok = out["recomputed"]["a_hat_minus_T0_rec_max"] <= tol
        m_zero = out["m_max"] <= tol
        s_ok = s_ex is None or s_ex <= tol
        out.update(recomputed_ok=bool(rec_ok), m_zero_ok=bool(m_zero), s_mode_ok=bool(s_ok))
        if kappa is not None and B_on:
            g3 = (1.0 + gamma) * C_S[T - 1] + float(kappa) * float(B_on[-1])
            out["cor_G3_rhs"], out["cor_G3_ok"] = float(g3), bool(alg[-1] <= g3 + tol)
        held = held and rec_ok and m_zero and s_ok and out.get("cor_G3_ok", True)
    elif core_exact:
        buy = np.asarray(ps["lease_prepaid"], dtype=np.float64) + np.asarray(ps["loading"], dtype=np.float64)
        Q = fallback_per_slot(inst)
        rb = rent_bound_per_slot(res, inst)
        ah_rec = np.full(T, np.nan)
        for t in executed:
            ah_rec[t] = at(alg, t - 1) + buy[t] + ((rb[t] + Q[t]) if test == "T0" else 0.0)
        m_rec = np.zeros(T)
        for t in executed:
            m_rec[t] = max(0.0, alg[t] - ah_rec[t])
        e_rec = [alg[t] - (gamma * C_S[t] + B[t] + m_rec[t]) for t in executed]
        out["recomputed"] = {
            "a_hat_rec_minus_report_max": float(max((ah_rec[t] - ah[t] for t in executed), default=0.0)),
            "a_hat_rec_minus_report_min": float(min((ah_rec[t] - ah[t] for t in executed), default=0.0)),
            "m_rec_max": float(max((m_rec[t] for t in executed), default=0.0)),
            "e_mode_max_excess": float(max(e_rec)) if e_rec else None}
        rec_ok = (not e_rec or max(e_rec) <= tol) and (test != "T0" or out["recomputed"]["m_rec_max"] <= tol)
        m_zero = test != "T0" or out["m_max"] <= tol
        s_ok = s_ex is None or s_ex <= tol
        out.update(recomputed_ok=bool(rec_ok), m_zero_ok=bool(m_zero), s_mode_ok=bool(s_ok))
        if test == "T0" and kappa is not None and B_on:
            g3 = (1.0 + gamma) * C_S[T - 1] + float(kappa) * float(B_on[-1])
            out["cor_G3_rhs"], out["cor_G3_ok"] = float(g3), bool(alg[-1] <= g3 + tol)
        held = held and rec_ok and m_zero and s_ok and out.get("cor_G3_ok", True)
    elif test == "T0g":
        out["m_zero_ok"] = out["m_ok"]
        held = held and out["m_ok"]
    else:
        out["m_le_stranding_ok" if test == "T0" else "m_le_running_ok"] = out["m_ok"]
    out["held"] = bool(held)
    out["ALG_per_slot"] = [float(x) for x in alg]
    return out


# ---------------------------------------------------------------- run specs
def _instance_src(inst: dict):
    return copy.deepcopy(inst["config"])


def run_spec(block: dict, inst: dict, tag: str, mode: str, c: int, policy_seeds, params=None) -> dict:
    """The run spec of one tag on one cell-mode (§4.1 of sim_spec_ms2): name = tag, the instance's config
    and overrides plus the grid's, the mode's lender model (the tag's information model on top), the
    engine's invariant checks on, lender seeds = config seeds."""
    pol = POLICIES[tag]
    lm = copy.deepcopy(MODES[mode]["lender_model"])
    if pol.get("information"):
        lm["information"] = pol["information"]
    ov = {**copy.deepcopy(inst.get("overrides") or {}), **(GRIDS[block["grid"]] or {})}
    return {"schema_version": 1, "name": tag, "instance": _instance_src(inst), "overrides": ov,
            "lender_model": lm, "engine": {"check_invariants": True},
            "policy": {"id": pol["id"], "params": copy.deepcopy(pol["params"] if params is None else params)},
            "seeds": {"config": [int(c)], "lender": "config", "policy": [int(p) for p in policy_seeds]},
            "bench": None, "out": f"code/sim/out/q44_study/runs/{block['block']}/{inst['id']}"}


def run_dir(out: Path, block: str, instance: str, grid: str, mode: str) -> Path:
    return out / "runs" / block / instance / grid / mode


def lb_dir(out: Path, block: str, instance: str, mode: str) -> Path:
    return out / "lb" / block / instance / mode


def _resolve_params(tag: str, inst_obj, information: str) -> dict:
    """The tag's parameters with PS-G-3B0's B0 = 3 b0_auto(view) resolved on the built instance."""
    p = copy.deepcopy(POLICIES[tag]["params"])
    if p.get("B0") == "3x_auto":
        p["B0"] = 3.0 * b0_auto_of(inst_obj, information)
    return p


def _q44_common(block: dict, inst: dict, mode: str, c: int, grid: str) -> dict:
    tuning = int(c) in set(int(x) for x in inst.get("tuning_seeds") or [])
    return {"block": block["block"], "tier": block.get("tier"), "instance": inst["id"],
            "family": inst.get("family", inst["id"]), "cell": int(c), "tuning": tuning, "grid": grid,
            "mode": mode, "mode_def": MODES[mode], "overrides": inst.get("overrides") or {},
            "grid_overrides": GRIDS[grid] or {}, "config": inst["config"] if isinstance(inst["config"], str) else "inline"}


def _post_run(path: Path, res, inst_obj, q44: dict, core_exact: bool, wall_s: Optional[float] = None) -> dict:
    """Add the 'q44' object to a run file written by drivers/run.py (or metrics.write_run) and rewrite it
    compactly; returns the q44 object."""
    js = json.loads(path.read_text())
    rep = res.metrics.get("policy") or {}
    q = dict(q44)
    q.update(seeds=dict(res.seeds), components=grouped(res.components), intensity=intensity(res, inst_obj),
             leases=lease_stats(res, inst_obj), plan_class_p1=plan_class_p1(res, inst_obj),
             schedule_hash=schedule_hash(res.schedule), engine_wall_s=res.runtime.get("wall_s"),
             wall_s=wall_s, invariant_failures=len(res.invariant_failures),
             gpu_only_lease_slots=int(res.metrics.get("gpu_only_lease_slots", 0)),
             fallback_share=js.get("metrics", {}).get("fallback_share"),
             replica_utilization=js.get("metrics", {}).get("replica_utilization"),
             stranding_events_per_day=js.get("metrics", {}).get("stranding_events_per_day"),
             buffer_violations_attributable=js.get("metrics", {}).get("buffer_violations_attributable"))
    if isinstance(rep.get("px"), dict):
        q["px"] = rep["px"]
    if q.get("policy_id") == "A8":
        q["certificate"] = certificate(res, inst_obj, rep, core_exact)
        inner = rep.get("inner") or {}
        if isinstance(inner.get("px"), dict):
            q["px"] = inner["px"]
    js["q44"] = q
    _dump(js, path, compact=True)
    return q


# ---------------------------------------------------------------- jobs: cell-modes of trace-driven instances
def _build(block: dict, inst: dict, mode: str, c: int):
    from ..drivers import run as drun
    spec = drun.load_run_spec(run_spec(block, inst, "BL0a", mode, c, [0]))
    return drun.build(spec, c)


def run_cells(block: dict, job: dict, out: Path) -> dict:
    """One cell-mode: every tag of the instance at the block's policy seeds through drivers/run.py::run,
    then the q44 object of each run file and the cell record."""
    from ..algos import registry
    from ..drivers import run as drun
    inst = next(i for i in block["instances"] if i["id"] == job["instance"])
    c, mode, grid = job["c"], job["mode"], block["grid"]
    seeds = block.get("policy_seeds", [0, 1, 2])
    d = run_dir(out, block["block"], inst["id"], grid, mode)
    d.mkdir(parents=True, exist_ok=True)
    inst_obj, model, _ = _build(block, inst, mode, c)
    rec = {"job": job["id"], "instance_hash": instance_hash(inst_obj), "schedule_hash": None, "BL0a_total": None,
           "policies": {}, "git_revision": _git_revision(), "versions": _versions(),
           "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "lb_per_run": block.get("lb") == "per_run"}
    errors, n_runs = [], 0
    for tag in instance_policies(block, inst):
        pid = POLICIES[tag]["id"]
        info = POLICIES[tag].get("information", "I1")
        t0 = time.perf_counter()
        try:
            params = _resolve_params(tag, inst_obj, info)
            spec = run_spec(block, inst, tag, mode, c, seeds, params)
            results = drun.run(spec, out_dir=d)
        except Exception as err:          # recorded; the job goes on with the next tag
            tb = traceback.format_exc()
            print(f"[q44_study] {job['id']} {tag}: {type(err).__name__}: {err}", flush=True)
            errors.append({"tag": tag, "error": f"{type(err).__name__}: {err}", "traceback": tb})
            rec["policies"][tag] = {"status": "error", "error": f"{type(err).__name__}: {err}",
                                    "wall_s": time.perf_counter() - t0}
            _dump({"job": job["id"], "tag": tag, "error": f"{type(err).__name__}: {err}", "traceback": tb},
                  d / f"{tag}_c{c}_error.json")
            continue
        wall = time.perf_counter() - t0
        runner = registry.entry(pid).runner
        totals = []
        for r in results:
            q44 = {**_q44_common(block, inst, mode, c, grid), "tag": tag, "policy_id": pid,
                   "params": POLICIES[tag]["params"], "resolved_tag_params": params,
                   "instance_hash": rec["instance_hash"]}
            if runner == "siloed":
                sd = r["seeds"]
                path = d / f"{tag}_c{c}_l{sd['lender']}_p{sd['policy']}_sum.json"
                js = json.loads(path.read_text())
                sub = r["results"]
                q44.update(seeds=dict(sd), components=grouped(r["components"]),
                           intensity=intensity(sub[0], r["instances"][0]) if sub else None,
                           leases={"leases": sum(len(x.leases) for x in sub)},
                           plan_class_p1=all(plan_class_p1(x, s) for x, s in zip(sub, r["instances"])),
                           schedule_hash=schedule_hash(sub[0].schedule) if sub else None,
                           engine_wall_s=sum(x.runtime.get("wall_s") or 0.0 for x in sub), wall_s=wall / len(results),
                           invariant_failures=len(r["invariant_failures"]),
                           gpu_only_lease_slots=sum(int(x.metrics.get("gpu_only_lease_slots", 0)) for x in sub))
                js["q44"] = q44
                _dump(js, path, compact=True)
                totals.append(float(r["components"]["total"]))
            else:
                path = d / f"{tag}_c{c}_l{r.seeds['lender']}_p{r.seeds['policy']}.json"
                q = _post_run(path, r, inst_obj, q44, core_exact=False, wall_s=wall / len(results))
                totals.append(float(r.components["total"]))
                if tag == "BL0a" and rec["schedule_hash"] is None:
                    rec["schedule_hash"] = q["schedule_hash"]
                    rec["BL0a_total"] = float(r.components["total"])
                if block.get("lb") == "per_run" and MODES[mode]["lb"]:
                    _lb_for_run(block, inst, mode, c, r, inst_obj, model, out, tag)
            n_runs += 1
        rec["policies"][tag] = {"status": "ok", "runs": len(results), "wall_s": wall, "totals": totals}
        print(f"[q44_study] {job['id']} {tag}: {len(results)} runs in {wall:.1f} s, mean total "
              f"{np.mean(totals):.2f}", flush=True)
    rec.update(finished=time.strftime("%Y-%m-%dT%H:%M:%S"), peak_rss_mb=_peak_rss_mb(), errors=len(errors))
    _dump(rec, d / f"cell_c{c}.json")
    return {"runs": n_runs, "errors": errors}


# ---------------------------------------------------------------- lower bounds
def _lb_record(sr, inst_obj, model, extra: dict) -> dict:
    from ..drivers import run as drun
    why = drun.ratio_validity(sr.grid, inst_obj, model)
    val = sr.objective if sr.method != "milp" else (sr.dual_bound if sr.dual_bound is not None else None)
    return {**extra, "method": sr.method, "benchmark": sr.benchmark, "grid": sr.grid, "status": sr.status,
            "status_msg": sr.status_msg, "objective": sr.objective, "dual_bound": sr.dual_bound, "gap": sr.gap,
            "lb": val, "valid_for_runs": why is None, "validity_note": why, "size": sr.size,
            "build_s": sr.build_s, "solve_s": sr.solve_s, "peak_rss_mb": _peak_rss_mb(),
            "git_revision": _git_revision()}


def _solve_lb(block: dict, mode: str, res, inst_obj, model):
    from ..drivers.bench import bench_for
    refuse = model.on_unavailable == "refuse"
    if block.get("lb") == "milp":
        mk = dict(block.get("milp") or {})
        return bench_for(res, inst_obj, "omega", grid="slow", time_limit_s=float(mk.get("time_limit_s", 300.0)),
                         mip_rel_gap=float(mk.get("mip_rel_gap", 1e-4)), allow_large=True, refuse_unavailable=refuse,
                         return_plan=False)
    return bench_for(res, inst_obj, "lp", grid="slow", merged=bool(MODES[mode].get("merged")), allow_large=True,
                     refuse_unavailable=refuse, return_plan=False, time_limit_s=3600.0)


def run_lb(block: dict, job: dict, out: Path) -> dict:
    """The LB of one oblivious cell-mode: BL0a's run gives the realized schedule (the same for every run of
    the cell-mode with on_unavailable 'sell' or 'refuse' and violations absorbed), then the LP (merged under
    L-eg) or BL8's MILP on the slow grid (§5.4, §5.5)."""
    from ..engine import simulate
    from ..policies import AlwaysFallback
    inst = next(i for i in block["instances"] if i["id"] == job["instance"])
    c, mode = job["c"], job["mode"]
    inst_obj, model, ecfg = _build(block, inst, mode, c)
    res = simulate(inst_obj, AlwaysFallback(), model, ecfg, lender_seed=c, policy_seed=0)
    t0 = time.perf_counter()
    sr = _solve_lb(block, mode, res, inst_obj, model)
    extra = {"job": job["id"], "block": block["block"], "instance": inst["id"], "family": inst.get("family"),
             "cell": int(c), "lender_seed": int(res.seeds["lender"]), "mode": mode, "run_grid": block["grid"],
             "kind": "milp" if block.get("lb") == "milp" else "lp", "merged": bool(MODES[mode].get("merged")),
             "instance_hash": instance_hash(inst_obj), "schedule_hash": schedule_hash(res.schedule),
             "wall_s": time.perf_counter() - t0}
    d = lb_dir(out, block["block"], inst["id"], mode)
    _dump(_lb_record(sr, inst_obj, model, extra), d / f"lb_c{c}_l{res.seeds['lender']}.json")
    print(f"[q44_study] {job['id']}: {extra['kind']} {sr.status_msg} objective {sr.objective} in "
          f"{extra['wall_s']:.1f} s", flush=True)
    return {"runs": 0, "errors": []}


def _lb_for_run(block, inst, mode, c, res, inst_obj, model, out, tag) -> None:
    """Per-run LB under L-ad (§5.5): the LP on the run's own realized schedule."""
    t0 = time.perf_counter()
    sr = _solve_lb(block, mode, res, inst_obj, model)
    extra = {"block": block["block"], "instance": inst["id"], "family": inst.get("family"), "cell": int(c),
             "lender_seed": int(res.seeds["lender"]), "policy_seed": res.seeds.get("policy"), "tag": tag,
             "mode": mode, "run_grid": block["grid"], "kind": "lp", "merged": False, "per_run": True,
             "schedule_hash": schedule_hash(res.schedule), "wall_s": time.perf_counter() - t0}
    p = lb_dir(out, block["block"], inst["id"], mode) / \
        f"{tag}_c{c}_l{res.seeds['lender']}_p{res.seeds['policy']}.json"
    _dump(_lb_record(sr, inst_obj, model, extra), p)


# ---------------------------------------------------------------- jobs: families F1-F3 (§5.2)
def family_core(fam: dict, v: dict):
    """(core instance, fam.Fam or None, instance description) of one family instance: F1/F2 the T4/O1
    family Fam(m, rho, tau, H, T).core_instance() (F1 is check_c4_lower.cm_instance's cat-and-mouse
    instance); F3 check_c4_lower.single(T, [(1, 1), (T, 0)], beta, [1.0, 1.3]) (C3-P5, part (b))."""
    if fam["kind"] == "c3p5":
        c4 = import_ref("check_c4_lower")
        T, beta = int(v["T"]), float(v["beta"])
        return c4.single(T, [(1, 1), (T, 0)], beta, [1.0, 1.3]), None, \
            f"check_c4_lower.single({T}, [(1, 1), ({T}, 0)], {beta:g}, [1.0, 1.3])"
    fm = import_ref("fam")
    F = fm.Fam(int(v["m"]), float(v["rho"]), int(fam["tau"]), int(fam["H"]), int(fam["T"]))
    return F.core_instance(), F, f"fam.Fam({v['m']}, {v['rho']:g}, {fam['tau']}, {fam['H']}, {fam['T']}).core_instance()"


def _family_lb(fam: dict, F, I, res, inst_obj) -> tuple[float, dict]:
    if fam["kind"] == "c3p5":
        core = import_ref("core")
        r = core.opt_eager(I)
        return float(r["fun"]), {"method": "core.opt_eager", "status": r.get("status") if isinstance(r, dict) else None}
    from ..drivers.bench import bench_for
    sr = bench_for(res, inst_obj, "fam", fam=F)
    return float(sr.objective), {"method": "fam.opt_dp", "status": sr.status, "status_msg": sr.status_msg,
                                 "size": sr.size}


def run_family(block: dict, job: dict, out: Path) -> dict:
    """One family instance-mode: every tag (minus the family's exclusions) at the family's runs (§5.2):
    'paired' modes run lender seed s with policy seed s, 'fixed' modes lender seed 0 with policy seeds
    0-9. Run files by metrics.write_run with drivers/run.py's meta; LBs exact (fam.opt_dp per schedule,
    per run under the adaptive lender of F1; core.opt_eager on F3); the certificate on every A8 run (V6)."""
    from ..algos import registry
    from ..drivers import run as drun
    from ..engine import EngineConfig, simulate
    from ..instance import from_core
    from ..metrics import write_run
    from ..types import LenderModel
    fam = next(f for f in block["families"] if f["id"] == job["family"])
    v, mode = job["values"], job["mode"]
    fmode = FAMILY_MODES[mode]
    I, F, desc = family_core(fam, v)
    seeds = list(fam.get("policy_seeds") or block.get("policy_seeds") or range(10))
    pairs = [(s, s) if fmode["lender_seeds"] == "paired" else (0, s) for s in seeds]
    d = run_dir(out, block["block"], job["instance"], "core", mode)
    ld = lb_dir(out, block["block"], job["instance"], mode)
    d.mkdir(parents=True, exist_ok=True)
    tags = [t for t in (block.get("policies") or []) if t not in set(fam.get("exclude_policies") or [])]
    inst0, _ = from_core(I, [np.zeros(0, dtype=np.int64)] * int(I.a.shape[0]))
    ih = instance_hash(inst0)
    lbs: dict = {}
    errors, n_runs = [], 0
    rec = {"job": job["id"], "instance": job["instance"], "core_instance": desc, "values": v,
           "instance_hash": ih, "policies": {}, "git_revision": _git_revision(), "versions": _versions(),
           "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    for tag in tags:
        pid = POLICIES[tag]["id"]
        info = POLICIES[tag].get("information", "I1")
        model = LenderModel(schedule=fmode["schedule"], information=info, params=dict(fmode["params"]))
        t0 = time.perf_counter()
        totals = []
        try:
            for (l, p) in pairs:
                inst, _ = from_core(I, [np.zeros(0, dtype=np.int64)] * int(I.a.shape[0]))
                params = copy.deepcopy(POLICIES[tag]["params"])
                vals, imeta = drun.driver_inputs(pid, params, inst)
                pol = drun.make_policy({"policy": {"id": pid, "params": params}}, inst, inputs=vals)
                r0 = time.perf_counter()
                res = simulate(inst, pol, model, EngineConfig(check_invariants=True), lender_seed=l, policy_seed=p)
                wall = time.perf_counter() - r0
                rp = {**params, **(pol.params() or {})}
                extra = {"run_spec_hash": None, "run_spec_name": tag, "policy_id": pid, "params": rp,
                         "seeds": res.seeds, "info_class": registry.info_class(pid, rp, info), "runner": "simulate",
                         "driver_inputs": imeta, "instance": desc,
                         "lender_model": {"schedule": fmode["schedule"], "information": info,
                                          "params": fmode["params"]}}
                path = d / f"{tag}_c{inst.seed}_l{l}_p{p}.json"
                write_run(res, inst, path, extra_meta=extra)
                # the exact LB: per run on F1 (adaptive), per schedule otherwise
                if fmode["oblivious"]:
                    key = ("sched", l)
                    if key not in lbs:
                        val, meta = _family_lb(fam, F, I, res, inst)
                        lbs[key] = val
                        _dump({"job": job["id"], "instance": job["instance"], "mode": mode, "cell": inst.seed,
                               "lender_seed": l, "lb": val, "exact": True, "run_grid": "core",
                               "schedule_hash": schedule_hash(res.schedule), **meta,
                               "git_revision": _git_revision()}, ld / f"lb_c{inst.seed}_l{l}.json")
                    opt = lbs[key]
                else:
                    opt, meta = _family_lb(fam, F, I, res, inst)
                    _dump({"job": job["id"], "instance": job["instance"], "mode": mode, "cell": inst.seed,
                           "lender_seed": l, "policy_seed": p, "tag": tag, "lb": opt, "exact": True, "per_run": True,
                           "run_grid": "core", "schedule_hash": schedule_hash(res.schedule), **meta,
                           "git_revision": _git_revision()}, ld / f"{tag}_c{inst.seed}_l{l}_p{p}.json")
                q44 = {"block": block["block"], "tier": block.get("tier"), "instance": job["instance"],
                       "family": fam["id"], "values": v, "cell": int(inst.seed), "tuning": False, "grid": "core",
                       "mode": mode, "mode_def": fmode, "tag": tag, "policy_id": pid,
                       "params": POLICIES[tag]["params"], "instance_hash": ih, "opt": opt,
                       "ratio_opt": float(res.components["total"]) / opt if opt > 0 else None,
                       "rho": None if F is None else float(F.rho), "m": None if F is None else int(F.m),
                       "rho1": (1.0 + float(v["beta"]) / 2.0) if fam["kind"] == "c3p5" else None}
                q = _post_run(path, res, inst, q44, core_exact=True, wall_s=wall)
                if pid == "A8" and q.get("certificate", {}).get("available") and "B_on_T" in q["certificate"]:
                    cert = q["certificate"]
                    cert["lemma_G5_ok"] = bool(cert["B_on_T"] <= opt * (1 + CERT_TOL) + CERT_TOL)
                    cert["held"] = bool(cert["held"] and cert["lemma_G5_ok"])
                    js = json.loads(path.read_text())
                    js["q44"]["certificate"] = cert
                    _dump(js, path, compact=True)
                totals.append(float(res.components["total"]))
                n_runs += 1
        except Exception as err:          # recorded; the job goes on with the next tag
            tb = traceback.format_exc()
            print(f"[q44_study] {job['id']} {tag}: {type(err).__name__}: {err}", flush=True)
            errors.append({"tag": tag, "error": f"{type(err).__name__}: {err}", "traceback": tb})
            _dump({"job": job["id"], "tag": tag, "error": f"{type(err).__name__}: {err}", "traceback": tb},
                  d / f"{tag}_error.json")
            rec["policies"][tag] = {"status": "error", "error": f"{type(err).__name__}: {err}",
                                    "runs": len(totals), "wall_s": time.perf_counter() - t0}
            continue
        rec["policies"][tag] = {"status": "ok", "runs": len(totals), "wall_s": time.perf_counter() - t0,
                                "totals": totals}
    rec.update(finished=time.strftime("%Y-%m-%dT%H:%M:%S"), peak_rss_mb=_peak_rss_mb(), errors=len(errors))
    _dump(rec, d / "cell_family.json")
    print(f"[q44_study] {job['id']}: {n_runs} runs, {len(errors)} errors", flush=True)
    return {"runs": n_runs, "errors": errors}


# ---------------------------------------------------------------- job records and manifest
def run_job(job_id: str, out: Path, bdir=None) -> dict:
    block, job = find_job(job_id, bdir)
    t0 = time.perf_counter()
    rec = {"job": job_id, "kind": job["kind"], "alone": job["alone"], "status": "running",
           "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "block_sha256": block["_sha256"]}
    jp = out / "jobs" / job_file_name(job_id)
    _dump(rec, jp)
    try:
        fn = {"cells": run_cells, "lb": run_lb, "family": run_family}[job["kind"]]
        r = fn(block, job, out)
        rec.update(status="ok" if not r["errors"] else "ok_with_errors", runs=r["runs"],
                   errors=[{k: e[k] for k in ("tag", "error")} for e in r["errors"]])
    except Exception as err:
        rec.update(status="error", error=f"{type(err).__name__}: {err}", traceback=traceback.format_exc())
        print(traceback.format_exc(), flush=True)
    rec.update(wall_s=time.perf_counter() - t0, peak_rss_mb=_peak_rss_mb(),
               finished=time.strftime("%Y-%m-%dT%H:%M:%S"))
    _dump(rec, jp)
    return rec


def record_failure(job_id: str, rc: int, out: Path) -> None:
    """A job killed by the cap (exit 137, 'oom_at_3G', not retried at a larger cap) or that failed."""
    jp = out / "jobs" / job_file_name(job_id)
    old = json.loads(jp.read_text()) if jp.is_file() else {"job": job_id}
    if old.get("status") in ("ok", "ok_with_errors"):
        return
    old.update(status="oom_at_3G" if rc == 137 else f"failed (exit code {rc})", exit_code=rc,
               recorded=time.strftime("%Y-%m-%dT%H:%M:%S"))
    _dump(old, jp)


def manifest(blocks: list[str], out: Path, bdir=None) -> dict:
    """manifest.json: block files (path, sha256, tier, job counts), the catalogs, versions, git revision,
    and the status of every job found under jobs/."""
    bl = []
    for name in blocks:
        b = load_block(name, bdir)
        js = list_jobs(b)
        bl.append({"block": b["block"], "tier": b.get("tier"), "file": b["_path"], "sha256": b["_sha256"],
                   "jobs": len(js), "alone": sum(1 for j in js if j["alone"]), "description": b.get("description")})
    jobs = {}
    for p in sorted((out / "jobs").glob("*.json")) if (out / "jobs").is_dir() else []:
        try:
            j = json.loads(p.read_text())
            jobs[j.get("job", p.stem)] = {k: j.get(k) for k in ("status", "wall_s", "peak_rss_mb", "runs")}
        except (OSError, json.JSONDecodeError):
            jobs[p.stem] = {"status": "unreadable"}
    src = Path(__file__)
    m = {"meta": {"script": "code/sim/sublet/experiments/q44_study.py", "note": NOTE,
                  "script_sha256": hashlib.sha256(src.read_bytes()).hexdigest(), "git_revision": _git_revision(),
                  "versions": _versions(), "written": time.strftime("%Y-%m-%dT%H:%M:%S")},
         "blocks": bl, "modes": MODES, "family_modes": FAMILY_MODES, "policies": POLICIES,
         "guard_defaults": GUARD_DEFAULTS, "grids": GRIDS, "jobs": jobs}
    _dump(m, out / "manifest.json")
    return m


def describe(blocks: list[str], bdir=None) -> list[dict]:
    rows = []
    for name in blocks:
        b = load_block(name, bdir)
        js = list_jobs(b)
        cm = [j for j in js if j["kind"] in ("cells", "family")]
        n_runs = 0
        for j in cm:
            if j["kind"] == "cells":
                inst = next(i for i in b["instances"] if i["id"] == j["instance"])
                n_runs += len(instance_policies(b, inst)) * len(b.get("policy_seeds", [0, 1, 2]))
            else:
                fam = next(f for f in b["families"] if f["id"] == j["family"])
                tags = [t for t in b["policies"] if t not in set(fam.get("exclude_policies") or [])]
                n_runs += len(tags) * len(fam.get("policy_seeds") or b.get("policy_seeds") or range(10))
        rows.append({"block": b["block"], "tier": b.get("tier"), "cell_modes": len(cm), "runs": n_runs,
                     "lb_jobs": sum(1 for j in js if j["kind"] == "lb"), "alone": sum(1 for j in js if j["alone"])})
    return rows


# ---------------------------------------------------------------- wall-time estimate (run_q44_study.sh --dry-run)
# Seconds per run by instance family, grid and tag class, the largest per-run wall time (instance build, engine
# run, run file) over the cell records of the single timed jobs of the MS3 build (2026-10-17, one job per 3G
# scope, one worker): Q1:I1:c3:L-tr, Q1:I1:c4:L-ss, Q1:I2:c2:L-eg, Q1:I2:c3:L-iid-0.2, Q1:I4:c1:L-tr,
# Q1:I4:c2:L-co, Q2:I3:c1:L-eg, Q2:I3:c2:L-tr, Q5:I1:c4:L-eg (slow grid) and Q6:F2_m16_r64:F-ss (families).
# Unmeasured combinations borrow a measured row: I2 and I4 on the slow grid use I1's slow row, I3 on the slow
# grid its 1-min rows, PS-GR on I4 I2's value, and I5 (bench_e7r, Tier 2) I3's rows times 175/45 (sites).
# Tag classes: 'pd' = A6, A2, A2-th, A3, PS; 'guard' = every A8 tag except PS-GR and the T0g tags; 'gr' = PS-GR;
# 't0g' = the T0g tags of block T2_t0g (T0G_PAIRS): the larger of 'guard' and the largest per-run wall time over the
# cell records of the timed T2_t0g jobs (2026-10-17, one job per 3G scope, one worker): T2_t0g:I1:c3:L-eg 2.16 s,
# T2_t0g:I2:c2:L-eg 1.17, T2_t0g:I4:c2:L-co 0.97, T2_t0g:I3:c1:L-eg 8.33, T2_t0g:I3:c2:L-tr 5.34 (I1's slow row
# unmeasured: 'guard'); on F1-F3 0.11 s per run (T2_t0g:F2_m16_r64:F-ss, T2_t0g:F3_b30_T192:F-eg), within 'core'
# plus the job overhead.
EST_RUN_S = {
    ("I1", "1min"): {"BL0a": 0.23, "BL1": 0.37, "BL2": 0.94, "BL5": 0.58, "pd": 1.33, "guard": 1.88, "gr": 1.93,
                     "t0g": 2.16},
    ("I2", "1min"): {"BL0a": 0.24, "BL1": 0.44, "BL2": 0.85, "BL5": 0.37, "pd": 1.20, "guard": 1.86, "gr": 1.83,
                     "t0g": 1.86},
    ("I4", "1min"): {"BL0a": 0.24, "BL1": 0.35, "BL2": 0.82, "BL5": 0.30, "pd": 0.80, "guard": 0.91, "gr": 1.83,
                     "t0g": 0.97},
    ("I3", "1min", "L-eg"): {"BL0a": 0.44, "BL1": 1.71, "BL2": 3.42, "BL5": 0.94, "pd": 8.50, "guard": 8.67,
                             "gr": 8.67, "t0g": 8.67},
    ("I3", "1min"): {"BL0a": 0.44, "BL1": 1.31, "BL2": 3.29, "BL5": 0.91, "pd": 4.29, "guard": 4.27, "gr": 4.29,
                     "t0g": 5.34},
    ("I1", "slow"): {"BL0a": 0.06, "BL1": 0.12, "BL2": 0.28, "BL5": 0.09, "pd": 0.66, "guard": 0.63, "gr": 1.17,
                     "t0g": 0.63},
    "core": 0.10,                 # every tag on F1-F3 (measured 0.02-0.08 s per run on the largest F2 instance)
}
EST_JOB_OVERHEAD_S = 3.0          # process start and imports per job
# LB jobs (seconds, process included): the LP of a small 1-day instance (bench_e1's 1-day slow-grid LP takes
# 1.52 s, code/sim/out/mem_bench/e1_lp_1d_slow.json, plus BL0a's run); I3: Q5:I3:c2:L-eg:lb took 51.0 s
# (merged relaxation), and bench_e7s's 1-day slow-grid LP 28.0 s (code/sim/out/mem_bench/e7s_lp_1d_slow.json);
# BL8's MILP: its time limit plus 20 s.
EST_LP_S = {"small": 10.0, ("I3", "L-eg"): 55.0, "I3": 35.0}


def _tag_class(tag: str) -> str:
    """The estimate's class of a tag: the baselines by name; A8 under T0 ('guard'), under T0g ('t0g', the default
    since 2026-10-17), PS-GR ('gr', safe = 'pd'); every other tag 'pd'."""
    pid = POLICIES[tag]["id"]
    if tag in ("BL0a", "BL1", "BL2", "BL5"):
        return tag
    if pid != "A8":
        return "pd"
    if tag == "PS-GR":
        return "gr"
    return "t0g" if POLICIES[tag]["params"].get("test", GUARD_DEFAULTS["test"]) == "T0g" else "guard"


def _run_s(family: str, grid: str, mode: str, tag: str) -> float:
    if grid == "core":
        return float(EST_RUN_S["core"])
    scale = 1.0
    fam = family
    if fam == "I5":
        fam, scale = "I3", 175.0 / 45.0
    if fam == "I3":
        row = EST_RUN_S[("I3", "1min", "L-eg")] if mode in ("L-eg", "L-ad") else EST_RUN_S[("I3", "1min")]
    elif grid == "slow":
        row = EST_RUN_S[("I1", "slow")]
    else:
        row = EST_RUN_S.get((fam, "1min"), EST_RUN_S[("I2", "1min")])
    return scale * float(row[_tag_class(tag)])


def _lp_s(family: str, mode: str) -> float:
    if family in ("I3", "I5"):
        v = EST_LP_S[("I3", "L-eg")] if mode in ("L-eg", "L-ad") else EST_LP_S["I3"]
        return v * (175.0 / 45.0 if family == "I5" else 1.0)
    return EST_LP_S["small"]


def estimate_job_s(block: dict, job: dict) -> float:
    """Estimated wall time of one job (seconds) from EST_RUN_S, EST_LP_S and EST_JOB_OVERHEAD_S."""
    if job["kind"] == "family":
        fam = next(f for f in block["families"] if f["id"] == job["family"])
        tags = [t for t in (block.get("policies") or []) if t not in set(fam.get("exclude_policies") or [])]
        n = len(fam.get("policy_seeds") or block.get("policy_seeds") or range(10))
        return EST_JOB_OVERHEAD_S + len(tags) * n * float(EST_RUN_S["core"])
    inst = next(i for i in block["instances"] if i["id"] == job["instance"])
    family = inst.get("family", inst["id"])
    if job["kind"] == "lb":
        if block.get("lb") == "milp":
            return float((block.get("milp") or {}).get("time_limit_s", 300.0)) + 20.0
        return _lp_s(family, job["mode"])
    seeds = block.get("policy_seeds", [0, 1, 2])
    tot = EST_JOB_OVERHEAD_S
    for tag in instance_policies(block, inst):
        tot += len(seeds) * _run_s(family, block["grid"], job["mode"], tag)
        if block.get("lb") == "per_run" and MODES[job["mode"]]["lb"]:
            tot += len(seeds) * _lp_s(family, job["mode"])
    return tot


def estimate(blocks: list[str], workers: int = 2, bdir=None) -> dict:
    """The jobs of `blocks` in run order with their estimated wall times, per-block sums, the single-worker
    total and the wall time of run_q44_study.sh with `workers` workers (the pool jobs by list scheduling in
    list order, as the runner starts them, then the 'alone' jobs one at a time)."""
    jobs, per_block = [], []
    for name in blocks:
        b = load_block(name, bdir)
        js = [(j, estimate_job_s(b, j)) for j in list_jobs(b)]
        jobs += js
        per_block.append({"block": b["block"], "tier": b.get("tier"), "jobs": len(js),
                          "alone": sum(1 for j, _ in js if j["alone"]), "single_worker_s": sum(s for _, s in js)})
    free = [0.0] * max(1, int(workers))
    for j, s in jobs:
        if not j["alone"]:
            i = int(np.argmin(free))
            free[i] += s
    pool_wall = max(free)
    alone = sum(s for j, s in jobs if j["alone"])
    return {"jobs": [{"id": j["id"], "kind": j["kind"], "alone": j["alone"], "est_s": s} for j, s in jobs],
            "blocks": per_block, "single_worker_s": sum(s for _, s in jobs), "workers": int(workers),
            "pool_wall_s": pool_wall, "alone_s": alone, "wall_s": pool_wall + alone}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", nargs="*", metavar="BLOCK")
    g.add_argument("--job")
    g.add_argument("--record-failure", metavar="JOB")
    g.add_argument("--manifest", nargs="*", metavar="BLOCK")
    g.add_argument("--describe", nargs="*", metavar="BLOCK")
    g.add_argument("--estimate", nargs="*", metavar="BLOCK",
                   help="list the jobs with their estimated wall times and the totals (no job is run)")
    ap.add_argument("--workers", type=int, default=2, help="workers assumed by --estimate (default 2)")
    ap.add_argument("--exit-code", type=int, default=1)
    ap.add_argument("--out", type=Path, default=None, help="output folder (default SUBLET_Q44_DIR or "
                                                           "code/sim/out/q44_study)")
    ap.add_argument("--blocks", type=Path, default=None, help="folder of the block files (default "
                                                              "sublet/experiments/q44_blocks or SUBLET_Q44_BLOCKS)")
    a = ap.parse_args(argv)
    out = out_root(a.out)
    if a.list is not None:
        for name in (a.list or TIER1):
            for j in list_jobs(load_block(name, a.blocks)):
                print(("alone " if j["alone"] else "pool ") + j["id"])
    elif a.job:
        rec = run_job(a.job, out, a.blocks)
        print(f"[q44_study] {a.job}: {rec['status']} in {rec['wall_s']:.1f} s, peak RSS {rec['peak_rss_mb']:.0f} MB",
              flush=True)
        return 0 if rec["status"] in ("ok", "ok_with_errors") else 1
    elif a.record_failure:
        record_failure(a.record_failure, a.exit_code, out)
    elif a.manifest is not None:
        manifest(a.manifest or list(TIER1), out, a.blocks)
    elif a.estimate is not None:
        e = estimate(a.estimate or list(TIER1), workers=max(1, min(2, a.workers)), bdir=a.blocks)
        for j in e["jobs"]:
            print(f"{'alone' if j['alone'] else 'pool '} {j['id']}  est {j['est_s']:.0f} s")
        for b in e["blocks"]:
            print(f"[estimate] block {b['block']}: {b['jobs']} jobs ({b['alone']} alone), single worker "
                  f"{b['single_worker_s'] / 60:.1f} min")
        print(f"[estimate] {len(e['jobs'])} processes; single worker {e['single_worker_s'] / 3600:.2f} h; with "
              f"{e['workers']} worker(s): pool {e['pool_wall_s'] / 3600:.2f} h + alone {e['alone_s'] / 60:.1f} min = "
              f"{e['wall_s'] / 3600:.2f} h of wall time")
    else:
        for r in describe(a.describe or list(TIER1), a.blocks):
            print(json.dumps(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
