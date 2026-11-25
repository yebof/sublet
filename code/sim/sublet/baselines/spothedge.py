"""BL3, SpotHedge-style spread (design/sim_spec_ms2.md §15.5; mao2025skyserve: Alg. 1 p. 6,
over-provisioning pp. 7, 9, dynamic fallback p. 7).

One instance per pool (M55): the clients of one LLM j with the same set U of usable sites (§15.1)
form a pool; its zones Z are the lenders with a site in U (zone "group": the correlation groups).
State per pool: Z_A = Z, Z_P = {} at the start, the target N_Tar.
- Target: N_Can(t) = ceil(sum_{c in pool} dbar_c(t) - 1e-9) (1[sum dbar > 0] with kappa_infinite);
  N_Tar(0) = N_Can(0); afterwards N_Tar <- N_Can once N_Can has been above (resp. below) N_Tar in every
  slot of the last hysteresis_min (ceil(hysteresis_min / Δs) slots; ours). The pool runs
  N_Tar + N_Extra replicas (pp. 7, 9).
- Preemption of zone z: z moves from Z_A to Z_P; if then |Z_A| < 2, Z_A <- Z_A u Z_P, Z_P <- {}
  (Alg. 1, p. 6). Trigger (ours, M43): a notice on a pool lease in z (react_at "notice") or its death
  by reclaim or violation ("death"); under "notice" a violation death, which has no notice, also
  triggers it. A noticed lease no longer counts in S_p (it serves until its death).
- Return of a zone (ours): when a pool replica in z is first reported warm, z moves back to Z_A.
- S_p = the pool's alive, not preempted leases (one replica each). If S_p < N_Tar + N_Extra: launch
  one replica at a time in the cheapest zone of Z_A not used by the pool's current replicas (Alg. 1);
  all used: the cheapest zone of Z_A (ours); ties by fewer current pool replicas in the zone, then pi;
  inside the zone a uniformly random site of U that passes the pre-check (aux stream; ours); none:
  z is preempted and the launch tried again, at most |Z| attempts. A zone's cost is the minimum of
  sigma_cl over the pool's clients and its sites in U. If S_p > N_Tar + N_Extra: release the surplus,
  most expensive zone first, then the zone with most replicas, then latest start (rule BR).
- Dynamic fallback needs no action: the engine's fallback is always available and the engine's
  min-cost routing replaces SkyServe's load balancer.

MS7 option (design/ms7/plan.md X1, C53; design/ms7/feasibility/causal.md F2): demand_lag (0; slots, as BL1's, in
QUIET_KEYS so that params() and the records at the default stay those of MS2-MS6): dbar_c(t) of N_Can(t) is read from
Baseline.demand_of, so with L >= 1 the pools' targets follow the demand of slot t - L as revealed then (zeros for
t < L); the zone lists, notices and deaths are unchanged. BL3-0-lag of experiments/e7c_tags.py takes L = 1.

MS7 options (design/ms7/plan.md X4, C54; design/ms7/feasibility/baselines.md §1(b), §2 items 1 and 4, §3 B2 and B3),
defaults the behaviour above (MS2's BLD-14: N_Extra spares in every pool, also while N_Tar = 0) and hidden from
params() while they hold their defaults (QUIET_KEYS):
- contract_rule ('kstar'): 'c2' buys A9.3's base contract kbar(l, j) (common.c2_base_contracts_cached); the usable
  sites, hence the pools, and the zone costs are those of kbar (SiteTable.use_contracts before the pools are made;
  BL3-c2).
- extra_scope ('pool' | 'llm'): with 'llm' the N_Extra = n_extra spares belong to the LLM, as SkyServe's per-service
  N_Extra (mao2025skyserve, p. 7): they go one at a time to the LLM's eligible pools in decreasing N_Tar (ties by
  pool id), cyclically, so each LLM holds n_extra spares in all instead of n_extra per pool.
- extra_when_idle (True): False gives no spare to a pool while its N_Tar = 0 (with 'llm', such a pool is not
  eligible; an LLM whose pools are all idle holds none).
The pool's target is N_Tar plus its spares of the slot (_extras); every N_Tar is updated before the launches, which
run in pool order as before, so the defaults reproduce the runs above.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from ..algos.common import EPS_DEMAND, PolicyError
from ..types import PublicView, SlowObs
from .common import Baseline, c2_base_contracts_cached

EXTRA_SCOPES = ("pool", "llm")             # MS7 option extra_scope (C54)


@dataclass(eq=False)
class Pool:
    """One SpotHedge instance: the clients of one LLM with the same usable-site set U."""
    id: int
    llm: int
    clients: tuple[int, ...]
    sites: tuple[int, ...]                 # U in pi order
    zone_of: dict                          # site -> zone
    zones: tuple[str, ...]                 # Z, in order of their first site in pi
    zone_cost: dict                        # zone -> min sigma over the pool's clients and its sites in U
    Z_A: list = field(default_factory=list)
    Z_P: list = field(default_factory=list)
    N_tar: Optional[int] = None
    above: int = 0                         # consecutive slots with N_Can > N_Tar
    below: int = 0                         # consecutive slots with N_Can < N_Tar
    leases: dict = field(default_factory=dict)   # lease id -> {'zone', 'site', 'preempted', 'warm'}


class SpotHedgeStyle(Baseline):
    """BL3 (online-I1): SpotHedge's zone lists and over-provisioning per (LLM, usable-site set) pool."""
    name = "bl3_spothedge"
    PARAMS = {"n_extra": 2, "react_at": "notice", "zone": "lender", "hysteresis_min": 10, "defer_release": True,
              "demand_lag": 0, "contract_rule": "kstar", "extra_scope": "pool", "extra_when_idle": True}
    QUIET_KEYS = ("demand_lag", "contract_rule", "extra_scope", "extra_when_idle")   # MS7 C53, C54: records unchanged

    def _validate(self) -> None:
        p = self._params
        self._choice("react_at", ("notice", "death"))
        self._choice("zone", ("lender", "group"))
        self._choice("extra_scope", EXTRA_SCOPES)
        if not isinstance(p["extra_when_idle"], (bool, np.bool_)):
            raise PolicyError(f"SpotHedgeStyle: extra_when_idle must be true or false, got {p['extra_when_idle']!r}")
        for k in ("n_extra", "hysteresis_min"):
            v = p[k]
            if isinstance(v, bool) or not isinstance(v, (int, np.integer)) or v < 0:
                raise PolicyError(f"SpotHedgeStyle: {k} must be an integer >= 0, got {v!r}")

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        self.aux = self.streams["aux"]
        self.kinf = bool(view.kappa_infinite)
        self.h_slots = max(1, math.ceil(self._params["hysteresis_min"] / self.slow_min))
        if self._params["contract_rule"] == "c2":
            self.sites.use_contracts(c2_base_contracts_cached(view))
        self.pools = self._make_pools(view)
        self.pool_of_client = {c: p.id for p in self.pools for c in p.clients}
        self.pool_of_lease: dict[int, int] = {}
        self.events: list[list] = []        # [t, pool, kind, zone] for preempt, rebalance, return
        self._pools_of_llm: dict[int, list[Pool]] = {}
        for p in self.pools:
            self._pools_of_llm.setdefault(p.llm, []).append(p)
        self._extra_default = self._params["extra_scope"] == "pool" and bool(self._params["extra_when_idle"])
        self.spare_slots = 0                # sum over slots and pools of the spares in the target (MS7 options only)

    def _zone(self, view: PublicView, l: int) -> str:
        s = view.sites[l]
        return s.lender if self._params["zone"] == "lender" else s.group

    def _make_pools(self, view: PublicView) -> list[Pool]:
        st = self.sites
        groups: dict[tuple, list[int]] = {}
        for c in range(self.n):
            U = tuple(sorted(int(l) for l in np.flatnonzero(st.usable[c])))
            if U:
                groups.setdefault((int(st.cl_llm[c]), U), []).append(c)
        pools = []
        for (j, U), cl in groups.items():
            sites = tuple(sorted(U, key=lambda l: st.rank[l]))
            zone_of = {l: self._zone(view, l) for l in sites}
            zones = tuple(dict.fromkeys(zone_of[l] for l in sites))
            cost = {z: min(float(st.score[c, l]) for c in cl for l in sites if zone_of[l] == z) for z in zones}
            pools.append(Pool(len(pools), j, tuple(cl), sites, zone_of, zones, cost, Z_A=list(zones), Z_P=[]))
        return pools

    # -------------------------------------------------------- zone lists (Alg. 1)
    def _preempt(self, p: Pool, z: str, t: int) -> None:
        if z not in p.Z_A:
            return
        p.Z_A.remove(z)
        p.Z_P.append(z)
        self.events.append([t, p.id, "preempt", z])
        if len(p.Z_A) < 2:
            merged = set(p.Z_A) | set(p.Z_P)
            p.Z_A = [x for x in p.zones if x in merged]
            p.Z_P = []
            self.events.append([t, p.id, "rebalance", None])

    def _return(self, p: Pool, z: str, t: int) -> None:
        if z in p.Z_P:
            p.Z_P.remove(z)
            merged = set(p.Z_A) | {z}
            p.Z_A = [x for x in p.zones if x in merged]
            self.events.append([t, p.id, "return", z])

    # -------------------------------------------------------- one slot
    def act(self, obs: SlowObs) -> list:
        t = obs.t
        for pid, r in self._begin(obs):
            if r.ok:
                p = self.pools[pid]
                l = int(r.action.site)
                lid = int(r.lease_id)
                p.leases[lid] = {"zone": p.zone_of[l], "site": l, "preempted": False, "warm": False}
                self.pool_of_lease[lid] = pid
        noticed = {nt.lease_id for nt in obs.notices}
        for p in self.pools:
            # zone return: a pool replica first reported warm
            for lid, info in p.leases.items():
                if info["warm"] or info["preempted"] or lid not in obs.leases:
                    continue
                if any(obs.replicas[rid].state == "warm" for rid in obs.leases[lid].replicas if rid in obs.replicas):
                    info["warm"] = True
                    self._return(p, info["zone"], t)
            # notices: the lease stops counting; under react_at "notice" its zone is preempted
            if self._params["react_at"] == "notice":
                for lid in sorted(noticed & set(p.leases)):
                    info = p.leases[lid]
                    if not info["preempted"]:
                        info["preempted"] = True
                        self._preempt(p, info["zone"], t)
            # deaths (reclaim or violation: every lease end this policy did not release)
            for lid in [x for x in p.leases if x not in obs.leases]:
                info = p.leases.pop(lid)
                self.pool_of_lease.pop(lid, None)
                if self._gone(lid, obs) and not info["preempted"]:
                    self._preempt(p, info["zone"], t)
        # targets and launches or releases per pool
        d = np.asarray(self.demand_of(obs), dtype=np.float64)          # obs.demand at demand_lag 0 (C53)
        dbar = d.mean(axis=1) if d.shape[1] else np.zeros(self.n)
        for p in self.pools:
            tot = float(sum(dbar[c] for c in p.clients))
            n_can = int(tot > EPS_DEMAND) if self.kinf else max(0, math.ceil(tot - 1e-9))
            if p.N_tar is None:
                p.N_tar = n_can
            else:
                p.above = p.above + 1 if n_can > p.N_tar else 0
                p.below = p.below + 1 if n_can < p.N_tar else 0
                if p.above >= self.h_slots or p.below >= self.h_slots:
                    p.N_tar, p.above, p.below = n_can, 0, 0
        extra = self._extras()           # every N_Tar first (MS7 C54), then the launches or releases in pool order
        for p in self.pools:
            target = p.N_tar + extra[p.id]
            counted = [lid for lid, info in p.leases.items() if not info["preempted"]]
            S = len(counted)
            if S < target:
                self._launch(p, obs, target - S, counted)
            elif S > target:
                self._shrink(p, obs, S - target, counted)
            else:
                for lid in counted:
                    self._not_deferred(lid)
        return self.book.assemble(obs, self.view)

    def _extras(self) -> dict[int, int]:
        """N_Extra of each pool at this slot (pool id -> spares), from the pools' current N_Tar (module docstring,
        MS7 options): n_extra per pool at the defaults; with extra_when_idle false none for a pool with N_Tar = 0;
        with extra_scope 'llm' the LLM's n_extra spares one at a time to its eligible pools in (-N_Tar, pool id)
        order, cyclically."""
        n = int(self._params["n_extra"])
        if self._extra_default:
            return {p.id: n for p in self.pools}
        idle_ok = bool(self._params["extra_when_idle"])
        if self._params["extra_scope"] == "pool":
            out = {p.id: (n if (idle_ok or (p.N_tar or 0) > 0) else 0) for p in self.pools}
        else:
            out = {p.id: 0 for p in self.pools}
            for pools in self._pools_of_llm.values():
                elig = sorted((p for p in pools if idle_ok or (p.N_tar or 0) > 0),
                              key=lambda p: (-(p.N_tar or 0), p.id))
                for i in range(n if elig else 0):
                    out[elig[i % len(elig)].id] += 1
        self.spare_slots += sum(out.values())
        return out

    def _launch(self, p: Pool, obs: SlowObs, k: int, counted: list[int]) -> None:
        used = [p.leases[lid]["zone"] for lid in counted]
        st = self.sites
        zrank = {z: min(st.rank[l] for l in p.sites if p.zone_of[l] == z) for z in p.zones}
        gp = int(st.g[p.llm])
        for _ in range(k):
            placed = False
            for _attempt in range(len(p.zones)):
                if not p.Z_A:
                    break
                free = [z for z in p.Z_A if z not in used]
                cands = free or list(p.Z_A)
                z = min(cands, key=lambda x: (p.zone_cost[x], used.count(x), zrank[x]))
                ok = [l for l in p.sites if p.zone_of[l] == z and l not in self.unavail
                      and self.book.can_buy(obs, self.view, l, gp)]
                if ok:
                    l = ok[int(self.aux.integers(len(ok)))]
                    self._buy(p.id, l, p.llm, f"bl3:{p.id}")
                    used.append(z)
                    placed = True
                    break
                self._preempt(p, z, obs.t)
            if not placed:
                break

    def _shrink(self, p: Pool, obs: SlowObs, k: int, counted: list[int]) -> None:
        zcount = {z: 0 for z in p.zones}
        for lid in counted:
            zcount[p.leases[lid]["zone"]] += 1
        order = sorted(counted, key=lambda lid: (-p.zone_cost[p.leases[lid]["zone"]],
                                                  -zcount[p.leases[lid]["zone"]],
                                                  -obs.leases[lid].start_min, -lid))
        surplus = set(order[:k])
        for lid in order:
            if lid not in surplus:
                self._not_deferred(lid)
            elif self._try_release(obs, obs.leases[lid]):
                p.leases.pop(lid)
                self.pool_of_lease.pop(lid, None)

    def report(self) -> dict:
        out = super().report()
        out["pools"] = [{"id": p.id, "llm": p.llm, "clients": list(p.clients), "sites": list(p.sites),
                         "zones": list(p.zones), "Z_A": list(p.Z_A), "Z_P": list(p.Z_P), "N_tar": p.N_tar}
                        for p in getattr(self, "pools", [])]
        out["events"] = [list(e) for e in getattr(self, "events", [])]
        if hasattr(self, "pools") and not self._extra_default:        # MS7 options only: the records above unchanged
            out["extras"] = {"scope": self._params["extra_scope"], "when_idle": bool(self._params["extra_when_idle"]),
                             "spare_slots": int(self.spare_slots), "last": self._extras_last()}
        return out

    def _extras_last(self) -> dict:
        """The spares per pool at the pools' last N_Tar (report only; does not count toward spare_slots)."""
        keep = self.spare_slots
        out = {str(k): int(v) for k, v in self._extras().items()}
        self.spare_slots = keep
        return out


__all__ = ["SpotHedgeStyle", "Pool"]
