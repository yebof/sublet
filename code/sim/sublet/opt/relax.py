"""Merged relaxation of an instance for lower bounds on large models (design/sim_spec.md §6.2, §10 S32).

With `merge_identical_layers` off (the default), every offered layer is its own site, so that the
site structure depends neither on the horizon nor on the offset and the public view reveals nothing
about announcement sets. `merged_relaxation(inst, sched)` merges, for one realized schedule omega,
each maximal run of consecutive layer sites of one lender whose announcement sets in `sched` are
identical and whose other attributes are identical (lender, kind, menu and prices, load times and
loading charges, load scenario, region, group, routing costs); the merged site has the summed
capacity, ids and layer fields as the merged sites of §6.2. Protected and synthetic sites are kept.

Claim (PROVEN, §10 S32). Every P1 plan on (inst, sched) maps to a plan on (inst_m, sched_m) of no
larger cost: each lease moves to the merged site that contains its layer, where announcements fall at
the same slots (identical sets, per-site rule T5), the capacity is the sum, and prices, load times and
routing costs are equal. The lease, loading, routing, fallback and stranding_fb terms are therefore
equal, while stranding_kv can only fall, since m_c (§5.6, MILP (C5)) counts persisting load that
leaves a site and a move between two layers of one merged run is no move on inst_m. The mapped plan
costs the same when mu_kv = 0 (the default kv_share 0). Hence OPT(inst_m) <= OPT(inst), likewise
OPT_eager, the LP and slow_lb; equality of the optima is not claimed. A result against a merged bound
must be labeled as such.

inst_m is meant for bounds. The engine runs it under the schedules that do not read the trace sets
('eager', 'adaptive', 'safe_site', 'iid_step'); under 'trace' or 'correlated' only when sched was the
trace schedule, since the lender recomputes the trace set of a merged site from S_lend and rejects a
merged site whose layers have different trace sets (lender._base_R).
"""
from __future__ import annotations

import dataclasses

import numpy as np

from ..instance import validate
from ..types import Instance, Schedule


def _same(inst: Instance, sched: Schedule, a: int, b: int) -> bool:
    """Sites a and b = a + 1 may be merged: consecutive layers of one lender with identical sets and
    identical attributes."""
    sa, sb = inst.sites[a], inst.sites[b]
    if sa.kind != "layer" or sb.kind != "layer" or sa.lender != sb.lender:
        return False
    if sa.layer_hi is None or sb.layer_lo is None or sb.layer_lo != sa.layer_hi + 1:
        return False
    if (sa.menu, sa.region, sa.group) != (sb.menu, sb.region, sb.group):
        return False
    if inst.load_scenario[a] != inst.load_scenario[b]:
        return False
    if not np.array_equal(np.asarray(sched.R[a]), np.asarray(sched.R[b])):
        return False
    return (np.array_equal(inst.price[a], inst.price[b]) and np.array_equal(inst.lam_s[:, a], inst.lam_s[:, b])
            and np.array_equal(inst.beta_usd[:, a], inst.beta_usd[:, b])
            and np.array_equal(inst.clients.delta_usd_per_h[:, a], inst.clients.delta_usd_per_h[:, b]))


def merged_relaxation(inst: Instance, sched: Schedule) -> tuple[Instance, Schedule, np.ndarray]:
    """(inst_m, sched_m, site_map): the merged relaxation of (inst, sched) and the map old site
    index -> new site index ((m,) int64, non-decreasing). sched is the realized schedule omega of any
    mode; sched_m has the common set of each merged run and keeps sched's mode and `realized` flag.
    Every field of inst other than the site arrays and the lenders' site_index is unchanged."""
    if len(sched.R) != inst.m:
        raise ValueError(f"schedule has {len(sched.R)} sites, instance {inst.m}")
    runs: list[list[int]] = []
    for l in range(inst.m):
        if runs and _same(inst, sched, runs[-1][-1], l):
            runs[-1].append(l)
        else:
            runs.append([l])
    site_map = np.empty(inst.m, dtype=np.int64)
    sites, first = [], []
    for i, run in enumerate(runs):
        site_map[run] = i
        s0, s1 = inst.sites[run[0]], inst.sites[run[-1]]
        first.append(run[0])
        if len(run) == 1:
            sites.append(s0)
            continue
        sites.append(dataclasses.replace(
            s0, id=f"{s0.lender}/L{s0.layer_lo}-{s1.layer_hi}",
            capacity_gpus=float(sum(inst.sites[l].capacity_gpus for l in run)),
            layer_lo=s0.layer_lo, layer_hi=s1.layer_hi, local_layer_lo=s0.local_layer_lo))
    first = np.asarray(first, dtype=np.int64)
    lenders = tuple(dataclasses.replace(lt, site_index=tuple(sorted({int(site_map[l]) for l in lt.site_index})))
                    for lt in inst.lenders)
    clients = dataclasses.replace(inst.clients,
                                  delta_usd_per_h=np.array(inst.clients.delta_usd_per_h[:, first], copy=True))
    inst_m = dataclasses.replace(
        inst, sites=tuple(sites), price=np.array(inst.price[first], copy=True),
        lam_s=np.array(inst.lam_s[:, first], copy=True), beta_usd=np.array(inst.beta_usd[:, first], copy=True),
        load_scenario=tuple(inst.load_scenario[l] for l in first), clients=clients, lenders=lenders,
        notes=list(inst.notes))
    sched_m = Schedule(sched.mode, tuple(np.asarray(sched.R[l], dtype=np.int64).copy() for l in first),
                       sched.realized)
    validate(inst_m)
    return inst_m, sched_m, site_map


__all__ = ["merged_relaxation"]
