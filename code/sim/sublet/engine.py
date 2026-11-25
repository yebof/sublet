"""Simulation engine (design/sim_spec.md §3.6, §5).

The engine keeps lease and replica state on two time scales, calls the lender and the policy,
routes demand in every fast slot and books every cost in the ledger (rules T1-T11 of §3.1).
For each slow slot t (§5.1): (1) the lender's announcements, (2) buffer violations, (3) the
policy's observation, (4) the policy's actions at minute t * slow_min, (5) the fast slots of t
(deaths, warm-up, admitting capacity, routing, ledger, optional `on_fast`, online invariants and
metric sums). After the last slot the leases still alive end at the horizon.

The engine has no reclaim handler of its own (§5.4): a notice sets the death minute, and the
lease and its replicas die then. Stranding is booked from the routing (§5.6).

MS2 additions (design/sim_spec_ms2.md §2.4): separate lender and policy seeds and an injected
policy generator in `simulate` (C5, RunResult.seeds); the policy's report in
RunResult.metrics['policy'] (C6); the wall time of `act` per slow slot and the maximum number of
alive leases in RunResult.runtime (C7); warm-up through timing.warm_fast (C8).

MS5 addition (design/sim_spec_ms5.md §2.3, C27): RunResult.runtime gains, after the MS1 and MS2 keys, reset_s (the
wall time of policy.reset, which policy_s keeps counting), the sum, maximum and count of the slow steps
(slow_step_s_sum, slow_step_s_max, n_slow_steps) and of the fast steps (fast_step_s_sum, fast_step_s_max,
n_fast_steps), check_s (the per-slot invariant checks inside the fast steps) and finish_s (from the end of the last
slot to the reading of wall_s), so that the two step sums, reset_s and finish_s add up to at most wall_s. No other key,
value or order changes; the runtime dict is in no hash.
"""
from __future__ import annotations

import bisect
import math
import resource
import time
from dataclasses import dataclass, fields
from typing import Optional

import numpy as np
from scipy.optimize import linprog

from .ledger import Ledger, check_invariants
from .timing import warm_fast
from .types import (ActionResult, Buy, Drain, FastObs, Instance, LeaseRecord, LeaseView,
                    LenderModel, Load, Notice, Release, ReplicaRecord, ReplicaView, RunResult,
                    SetAdmission, SlowObs, Unload)


class ActionError(ValueError):
    """A malformed policy action (a policy bug, §5.2)."""


@dataclass(frozen=True)
class EngineConfig:
    auto_drain: bool = False        # drain every replica of an announced lease at max(r, death - T_dr) (§5.4)
    record_routing: bool = False    # keep per-fast-slot routing arrays (float64) in RunResult.routing
    check_invariants: bool = True
    tol: float = 1e-9


def engine_config(cfg: dict) -> EngineConfig:
    """EngineConfig from a resolved config (its 'engine' section; config.ENGINE_FIELDS)."""
    sec = cfg.get("engine", {}) if "engine" in cfg or "schema_version" in cfg else cfg
    sec = dict(sec or {})
    allowed = {f.name for f in fields(EngineConfig)}
    extra = sorted(set(sec) - allowed)
    if extra:
        from .config import ConfigError
        raise ConfigError(f"unknown engine fields {extra}; allowed {sorted(allowed)}")
    return EngineConfig(**sec)


# ---------------------------------------------------------------- internal state
class _Lease:
    __slots__ = ("id", "site", "contract", "gpus", "start_slot", "start_min", "prepaid_end_min",
                 "announce_slot", "death_min", "release_min", "end_min", "cut_cause",
                 "cut_issue_min", "prepaid_usd", "rent_usd", "tag", "reps", "rent_from_fast",
                 "rent_per_fast", "H_min", "dead_fast")

    def cause(self, horizon_min: int) -> str:
        """End cause once the end minute is reached: the cut (release or violation) if any,
        otherwise 'reclaim' if the death minute lies within the horizon, else 'horizon'."""
        if self.cut_cause is not None:
            return self.cut_cause
        if self.death_min is not None and self.death_min <= horizon_min:
            return "reclaim"
        return "horizon"


class _Replica:
    __slots__ = ("id", "lease", "llm", "g", "load_start_min", "warm_fast", "end_fast", "beta_usd",
                 "adm", "cap", "pending", "drain_min", "unload_issue_min", "change_issue_min",
                 "warm_seen")


# A pending admission change of a replica is a tuple (effective fast slot, sequence number,
# value, issue minute, is_drain); changes apply in this order, so a later-issued change wins
# within a fast slot.


def _p(values: list[float], q: float) -> Optional[float]:
    return float(np.percentile(values, q)) if values else None


class Engine:
    """One run of a policy against a lender on an instance (§5)."""

    def __init__(self, inst: Instance, lender, policy, cfg: EngineConfig = EngineConfig(),
                 rng: Optional[np.random.Generator] = None):
        self.inst, self.lender, self.policy, self.cfg = inst, lender, policy, cfg
        model = getattr(lender, "model", None)
        if not isinstance(model, LenderModel):
            raise TypeError("the lender must expose its LenderModel as `lender.model`")
        self.model = model
        if rng is None:
            from .config import rng_streams
            rng = rng_streams(inst.seed)["policy"]
        self.rng = rng
        self._ran = False

        g = inst.grid
        self.Ds, self.Df, self.phi = g.slow_min, g.fast_min, g.phi
        self.T_s, self.T_f, self.T_min = g.T_slow, g.T_fast, g.horizon_min
        self.J, self.m, self.n = inst.J, inst.m, inst.n
        self.g = np.array([L.g for L in inst.llms], dtype=np.int64)
        self.q = np.array([L.q_usd_per_h for L in inst.llms], dtype=np.float64)
        self.Tdr = np.array([L.T_dr_s for L in inst.llms], dtype=np.float64)
        cl = inst.clients
        self.c_llm = np.asarray(cl.llm, dtype=np.int64)
        self.delta = np.asarray(cl.delta_usd_per_h, dtype=np.float64)
        self.demand = np.asarray(cl.demand, dtype=np.float64)
        if self.demand.shape != (self.n, self.T_f):
            raise ValueError(f"demand shape {self.demand.shape}, expected {(self.n, self.T_f)}")
        # arcs that routing may use: finite delta below the LLM's fallback cost (§5.5)
        self.arc_ok = np.isfinite(self.delta) & (self.delta < self.q[self.c_llm][:, None])
        # the online INV3 tests the arcs against the instance data, not against arc_ok
        D = np.array(cl.delta_usd_per_h, dtype=np.float64)
        q_c = np.array([inst.llms[int(j)].q_usd_per_h for j in cl.llm], dtype=np.float64)
        self.arc_forbidden = ~np.isfinite(D) | (D >= q_c[:, None])
        self.delta0 = np.where(np.isfinite(self.delta), self.delta, 0.0)
        self.clients_of = [np.flatnonzero(self.c_llm == j) for j in range(self.J)]
        self.onehot = np.zeros((self.J, self.n))
        self.onehot[self.c_llm, np.arange(self.n)] = 1.0
        self.price = np.asarray(inst.price, dtype=np.float64)
        self.lam_ms = inst.lam_ms()
        self.beta = np.asarray(inst.beta_usd, dtype=np.float64)
        st = inst.stranding
        self.mu_kv = np.asarray(st.mu_kv_usd, dtype=np.float64)
        self.mu_fl = np.asarray(st.mu_fl_usd, dtype=np.float64)
        self.mu_fb = np.asarray(st.mu_fb_usd, dtype=np.float64)
        self.pi = np.asarray(st.pi_usd_per_min, dtype=np.float64)
        self.W_f = float(st.W_f_min)
        self.menus = [set(int(k) for k in s.menu) for s in inst.sites]
        self.site_lender = [s.lender for s in inst.sites]

    # ------------------------------------------------------------ helpers
    def _alive(self, L: _Lease, f: int) -> bool:
        """Rule T6: alive in fast slot f iff start <= f*Df and (f+1)*Df <= end minute."""
        return L.start_min <= f * self.Df and (f + 1) * self.Df <= L.end_min

    def _exists(self, r: _Replica, f: int) -> bool:
        return r.end_fast is None and self._alive(r.lease, f)

    def _lease_view(self, L: _Lease, f: int) -> LeaseView:
        return LeaseView(L.id, L.site, L.contract, L.gpus, L.start_slot, L.start_min,
                         L.prepaid_end_min, L.announce_slot, L.death_min,
                         tuple(r.id for r in L.reps if self._exists(r, f)))

    def _replica_view(self, r: _Replica, f: int) -> ReplicaView:
        if not self._exists(r, f):
            state = "dead"
        else:
            state = "warm" if f >= r.warm_fast else "loading"
        # admission in force from fast slot f (§10 S33): the pending changes with effective slot
        # <= f, applied in their order (effective slot, then issue sequence), as _fast_step will
        adm = r.adm
        for p in r.pending:
            if p[0] > f:
                break
            adm = p[2]
        return ReplicaView(r.id, r.lease.id, r.llm, state, r.load_start_min, r.warm_fast,
                           float(adm), r.drain_min)

    def _event(self, minute: int, typ: str, **payload) -> None:
        self.events.append((int(minute), typ, payload))

    def _fail(self, msg: str) -> None:
        if self.cfg.check_invariants:
            self.failures.append(msg)

    @staticmethod
    def _index(v, n: int, what: str) -> int:
        if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) or not 0 <= v < n:
            raise ActionError(f"invalid {what} index {v!r} (0..{n - 1})")
        return int(v)

    @staticmethod
    def _unit(v, what: str) -> float:
        if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)):
            raise ActionError(f"{what} must be a number in [0, 1], got {v!r}")
        v = float(v)
        if not 0.0 <= v <= 1.0:
            raise ActionError(f"{what} must lie in [0, 1], got {v}")
        return v

    # ------------------------------------------------------------ run
    def run(self) -> RunResult:
        if self._ran:
            raise RuntimeError("Engine.run() may be called only once")
        self._ran = True
        wall0 = time.perf_counter()
        inst, cfg = self.inst, self.cfg
        self.ledger = Ledger(self.T_s)
        self.leases: list[_Lease] = []
        self.replicas: list[_Replica] = []
        self.active: list[_Lease] = []          # leases not yet found dead in the fast loop
        self.reps_active: list[_Replica] = []   # replicas that existed in the previous fast slot
        self.unreported: list[_Lease] = []
        self.events: list[tuple[int, str, dict]] = []
        self.violations: list[dict] = []
        self.failures: list[str] = []
        self.seq = 0
        self.last_results: list[ActionResult] = []
        self.site_ann_log = {} if self.model.information == "I2" else None
        self.x_prev = np.zeros((self.n, self.m))
        self.W_prev = np.zeros((self.J, self.m))
        self.served_prev_fast = np.zeros((self.J, self.m))
        self.served_prev_slot = np.zeros((self.J, self.m))
        self.fallback_prev_slot = np.zeros(self.n)
        self.reclaim_until = np.zeros(self.J, dtype=np.int64)   # fast slot until which a reclaim window runs
        self.ms = dict(
            demand_load_min_by_llm=np.zeros(self.J), fallback_load_min_by_llm=np.zeros(self.J),
            served_load_min=0.0, capacity_load_min=0.0,
            stranded_load_fb=0.0, stranded_load_any=0.0,
            capacity_drops=0, capacity_drops_reclaim=0, stranding_events=0,
            attributed_load_at_drops=0.0,
            demand_after_reclaims_load_min_by_llm=np.zeros(self.J),
            fallback_after_reclaims_load_min_by_llm=np.zeros(self.J),
            loads=0, gpu_only_lease_slots=0, violation_lender_slots=0,
            violation_lender_slots_attributable=0, violation_deficit_gpu_slots=0.0,
            violation_deficit_attributable_gpu_slots=0.0,
            refused={"capacity": 0, "unavailable": 0})
        self.rt = dict(slow=[], fast=[], routing_s=0.0, routing_lp_calls=0, policy_s=0.0, act=[],
                       n_alive_max=0, reset_s=0.0, check_s=0.0, slots_end=None)
        if cfg.record_routing:
            self.rec_x: dict[tuple[int, int], np.ndarray] = {}
            self.rec_b = np.zeros((self.n, self.T_f))
            self.rec_W = np.zeros((self.J, self.m, self.T_f))

        from .instance import public_view
        view = public_view(inst, self.model.information)
        t0 = time.perf_counter()
        self.policy.reset(view, self.rng)
        dt = time.perf_counter() - t0
        self.rt["reset_s"] = dt                 # C27: the setup apart, also counted in policy_s
        self.rt["policy_s"] += dt
        self.wants_fast = bool(getattr(self.policy, "wants_fast", False))

        for t in range(self.T_s):
            self._slow_step(t)
        self.rt["slots_end"] = time.perf_counter()    # C27: finish_s runs from here to the reading of wall_s
        res = self._finish(wall0)
        return res

    # ------------------------------------------------------------ slow slot
    def _slow_step(self, t: int) -> None:
        ts = time.perf_counter()
        Ds, minute, f0 = self.Ds, t * self.Ds, t * self.phi
        inst = self.inst

        # 1. lender: announcements of slot t (rule T9 step 1)
        alive = [L for L in self.active if self._alive(L, f0)]
        alive_ids = {L.id for L in alive}
        site_ann, notices = self.lender.begin_slot(t, [self._lease_view(L, f0) for L in alive])
        delivered: list[Notice] = []
        for nt in notices:
            lid = nt.lease_id
            L = self.leases[lid] if isinstance(lid, (int, np.integer)) and 0 <= lid < len(self.leases) else None
            c = inst.contracts[L.contract] if L is not None else None
            if L is None or lid not in alive_ids:
                self._fail(f"INV7 slot {t}: notice for lease {lid}, which is not alive at the slot start")
                continue
            if L.announce_slot is not None or c.protected:
                self._fail(f"INV7 slot {t}: second notice or notice of a protected lease {lid}")
                continue
            if L.start_slot + c.tau_slots > t:
                self._fail(f"INV7 slot {t}: lease {lid} announced before s + tau")
                continue
            death = t * Ds + c.H_min
            if nt.r_slot != t or nt.death_min != death:
                self._fail(f"INV7 slot {t}: notice ({nt.r_slot}, {nt.death_min}) for lease {lid}, "
                           f"expected ({t}, {death})")
            L.announce_slot, L.death_min = t, death
            L.end_min = min(L.end_min, death)
            delivered.append(Notice(lid, t, death))
            self._event(minute, "announce", lease=lid, r=t, death_min=death)
            if self.cfg.auto_drain:
                for r in L.reps:
                    if self._exists(r, f0):
                        at = max(minute, death - math.ceil(self.Tdr[r.llm] / 60.0))
                        self._drain(r, at, minute, f0)
        site_ann = np.asarray(site_ann, dtype=bool).copy()
        if site_ann.shape != (self.m,):
            raise ValueError(f"lender.begin_slot returned site_announced of shape {site_ann.shape}")
        obs_site = None
        if self.site_ann_log is not None:
            self.site_ann_log[t] = site_ann
            obs_site = site_ann.copy()

        # 2. buffer violations (schedules 'trace' and 'correlated', §6.5)
        if self.model.schedule in ("trace", "correlated"):
            held: dict[str, int] = {lt.lender: 0 for lt in inst.lenders}
            for s in inst.sites:
                held.setdefault(s.lender, 0)
            for L in self.active:
                if self._alive(L, f0):
                    held[self.site_lender[L.site]] += L.gpus
            viols = self.lender.violations(t, held)
            self.ms["violation_lender_slots"] += len({v["lender"] for v in viols})
            # the part a policy causes (§6.5, S10): the deficit minus the one with no platform lease
            self.ms["violation_lender_slots_attributable"] += len(
                {v["lender"] for v in viols if v.get("deficit_attributable", v["deficit"]) > 0})
            for v in viols:
                entry = dict(v)
                att = float(v.get("deficit_attributable", v["deficit"]))
                self.ms["violation_deficit_gpu_slots"] += float(v["deficit"])
                self.ms["violation_deficit_attributable_gpu_slots"] += att
                self._event(minute, "violation", lender=v["lender"], required=v["required"],
                            slack=v["slack"], deficit=v["deficit"], owed=v.get("owed"),
                            deficit_attributable=att)
                if self.model.violations == "reclaim":
                    cur = [self._lease_view(L, f0) for L in self.active if self._alive(L, f0)]
                    victims = [int(x) for x in self.lender.violation_victims(t, cur, v)]
                    for lid in victims:
                        L = self.leases[lid]
                        if not self._alive(L, f0):
                            raise ValueError(f"violation victim {lid} is not alive at slot {t}")
                        L.cut_cause, L.cut_issue_min, L.end_min = "violation", minute, minute
                        self._event(minute, "death", lease=lid, cause="violation")
                    entry["victims"] = victims
                self.violations.append(entry)

        # 3. observation
        leases_obs = {}
        reps_obs = {}
        for L in self.active:
            if self._alive(L, f0):
                leases_obs[L.id] = self._lease_view(L, f0)
                for r in L.reps:
                    if self._exists(r, f0):
                        reps_obs[r.id] = self._replica_view(r, f0)
        ended = []
        keep = []
        for L in self.unreported:
            if L.end_min <= minute:
                ended.append((L.id, int(L.end_min), L.cause(self.T_min)))
            else:
                keep.append(L)
        self.unreported = keep
        obs = SlowObs(t=t, minute=minute, demand=self.demand[:, f0:f0 + self.phi].copy(),
                      leases=leases_obs, replicas=reps_obs, notices=delivered, ended=ended,
                      results=list(self.last_results), site_announced=obs_site,
                      served_prev=self.served_prev_slot.copy(),
                      fallback_prev=self.fallback_prev_slot.copy(),
                      cost_so_far=float(self.ledger.running_total))

        # 4. act
        tp = time.perf_counter()
        actions = self.policy.act(obs)
        dt = time.perf_counter() - tp
        self.rt["policy_s"] += dt
        self.rt["act"].append(dt)
        results = self._apply(t, actions, None)
        self.last_results = results
        n_alive, gpu_only = 0, False
        for L in self.active:
            if self._alive(L, f0):
                n_alive += 1
                if not gpu_only and not any(self._exists(r, f0) for r in L.reps):
                    gpu_only = True
        if gpu_only:
            self.ms["gpu_only_lease_slots"] += 1
        self.rt["n_alive_max"] = max(self.rt["n_alive_max"], n_alive)
        self.rt["slow"].append(time.perf_counter() - ts)

        # 5. fast slots
        self.slot_served = np.zeros((self.J, self.m))
        self.slot_fallback = np.zeros(self.n)
        for f in range(f0, f0 + self.phi):
            self._fast_step(t, f, results if f == f0 else [])
        self.served_prev_slot = self.slot_served / self.phi
        self.fallback_prev_slot = self.slot_fallback / self.phi

    # ------------------------------------------------------------ actions
    def _apply(self, t: int, actions, f: Optional[int]) -> list[ActionResult]:
        """Apply a list of actions in order: at slow slot t (f None) or from on_fast at fast slot f."""
        if actions is None:
            return []
        if not isinstance(actions, (list, tuple)):
            raise ActionError(f"actions must be a list, got {type(actions).__name__}")
        out = []
        for i, a in enumerate(actions):
            if f is not None and not isinstance(a, (Drain, SetAdmission)):
                raise ActionError(f"on_fast may return only Drain and SetAdmission, got {a!r}")
            if isinstance(a, Buy):
                out.append(self._buy(t, i, a))
            elif isinstance(a, Release):
                out.append(self._release(t, i, a))
            elif isinstance(a, Load):
                out.append(self._load(t, i, a))
            elif isinstance(a, Unload):
                out.append(self._unload(t, i, a))
            elif isinstance(a, Drain):
                out.append(self._drain_action(t, i, a, f))
            elif isinstance(a, SetAdmission):
                out.append(self._set_admission(t, i, a, f))
            else:
                raise ActionError(f"unknown action {a!r}")
        return out

    def _get_lease(self, lid, f: int) -> _Lease:
        if isinstance(lid, (bool, np.bool_)) or not isinstance(lid, (int, np.integer)) \
                or not 0 <= lid < len(self.leases):
            raise ActionError(f"unknown lease {lid!r}")
        L = self.leases[int(lid)]
        if not self._alive(L, f):
            raise ActionError(f"lease {lid} is not alive")
        return L

    def _get_replica(self, rid, f: int) -> _Replica:
        if isinstance(rid, (bool, np.bool_)) or not isinstance(rid, (int, np.integer)) \
                or not 0 <= rid < len(self.replicas):
            raise ActionError(f"unknown replica {rid!r}")
        r = self.replicas[int(rid)]
        if not self._exists(r, f):
            raise ActionError(f"replica {rid} does not exist (unloaded or its lease ended)")
        return r

    def _new_replica(self, L: _Lease, j: int, t: int, admission: float) -> _Replica:
        m0 = t * self.Ds
        r = _Replica()
        r.id, r.lease, r.llm, r.g = len(self.replicas), L, j, int(self.g[j])
        r.load_start_min = m0
        r.warm_fast = warm_fast(m0, int(self.lam_ms[j, L.site]), self.Df)     # rule T8
        r.end_fast = None
        r.beta_usd = float(self.beta[j, L.site])
        r.adm, r.cap = float(admission), 0.0
        r.pending, r.drain_min = [], None
        r.unload_issue_min, r.change_issue_min, r.warm_seen = None, m0, False
        self.replicas.append(r)
        self.reps_active.append(r)
        L.reps.append(r)
        self.ledger.add("loading", t, r.beta_usd)
        self.ms["loads"] += 1
        self._event(m0, "load", replica=r.id, lease=L.id, llm=j)
        return r

    def _buy(self, t: int, i: int, a: Buy) -> ActionResult:
        inst = self.inst
        site = self._index(a.site, self.m, "site")
        k = self._index(a.contract, inst.K, "contract")
        j = self._index(a.llm, self.J, "LLM")
        if k not in self.menus[site]:
            raise ActionError(f"contract {k} is not on the menu of site {site}")
        nrep = a.n_replicas
        if isinstance(nrep, (bool, np.bool_)) or not isinstance(nrep, (int, np.integer)) or nrep < 1:
            raise ActionError(f"n_replicas must be an integer >= 1, got {nrep!r}")
        nrep = int(nrep)
        adm = self._unit(a.admission, "admission")
        f0, minute = t * self.phi, t * self.Ds
        gpus = nrep * int(self.g[j])
        held = sum(L.gpus for L in self.active if L.site == site and self._alive(L, f0))
        ok, reason = self.lender.purchase_ok(t, site, gpus, held)
        if not ok:
            self.ms["refused"][reason] = self.ms["refused"].get(reason, 0) + 1
            self._event(minute, "refuse", lease=None, site=site, contract=k, gpus=gpus, llm=j,
                        n=nrep, reason=reason)
            return ActionResult(i, a, False, None, (), reason)
        c = inst.contracts[k]
        price = float(self.price[site, k])
        L = _Lease()
        L.id, L.site, L.contract, L.gpus = len(self.leases), site, k, gpus
        L.start_slot, L.start_min = t, minute
        L.prepaid_end_min = minute + c.prepaid_min
        L.announce_slot = L.death_min = L.release_min = None
        L.end_min = self.T_min
        L.cut_cause = L.cut_issue_min = None
        L.prepaid_usd = gpus * price * c.prepaid_min / 60.0
        L.rent_usd = 0.0
        L.tag = str(a.tag)
        L.reps = []
        L.rent_from_fast = max(f0, -(-(minute + c.prepaid_min) // self.Df))   # rule T7
        L.rent_per_fast = gpus * price * self.Df / 60.0
        L.H_min = 0 if c.protected else int(c.H_min)
        L.dead_fast = None
        self.leases.append(L)
        self.active.append(L)
        self.unreported.append(L)
        self.ledger.add("lease_prepaid", t, L.prepaid_usd)
        self._event(minute, "buy", lease=L.id, site=site, contract=k, gpus=gpus, llm=j, n=nrep,
                    reason="")
        reps = tuple(self._new_replica(L, j, t, adm).id for _ in range(nrep))
        return ActionResult(i, a, True, L.id, reps, "")

    def _release(self, t: int, i: int, a: Release) -> ActionResult:
        f0, minute = t * self.phi, t * self.Ds
        L = self._get_lease(a.lease_id, f0)
        L.release_min = minute
        L.end_min = minute
        L.cut_cause, L.cut_issue_min = "release", minute
        self._event(minute, "release", lease=L.id)
        return ActionResult(i, a, True, L.id, (), "")

    def _load(self, t: int, i: int, a: Load) -> ActionResult:
        f0 = t * self.phi
        L = self._get_lease(a.lease_id, f0)
        j = self._index(a.llm, self.J, "LLM")
        used = sum(r.g for r in L.reps if self._exists(r, f0))
        if L.gpus - used < self.g[j]:
            return ActionResult(i, a, False, L.id, (), "lease_gpus")
        r = self._new_replica(L, j, t, 1.0)
        return ActionResult(i, a, True, L.id, (r.id,), "")

    def _unload(self, t: int, i: int, a: Unload) -> ActionResult:
        f0, minute = t * self.phi, t * self.Ds
        r = self._get_replica(a.replica_id, f0)
        r.end_fast = f0
        r.unload_issue_min = minute
        self._event(minute, "unload", replica=r.id)
        return ActionResult(i, a, True, r.lease.id, (r.id,), "")

    def _now(self, t: int, f: Optional[int]) -> tuple[int, int, int]:
        """(current fast slot for validity, first fast slot of effect, issue minute)."""
        if f is None:
            return t * self.phi, t * self.phi, t * self.Ds
        return f, f + 1, (f + 1) * self.Df

    def _push(self, r: _Replica, eff: int, value: float, issue_min: int, is_drain: bool) -> None:
        self.seq += 1
        bisect.insort(r.pending, (eff, self.seq, value, issue_min, is_drain))

    def _drain(self, r: _Replica, at_min: int, issue_min: int, eff_min_fast: int) -> int:
        """Schedule a drain (admission 0 from the first fast slot starting at or after at_min,
        not before eff_min_fast); replaces a pending drain of the replica."""
        eff = max(eff_min_fast, -(-int(at_min) // self.Df))
        r.pending = [p for p in r.pending if not p[4]]
        self._push(r, eff, 0.0, issue_min, True)
        r.drain_min = int(at_min)
        self._event(issue_min, "drain", replica=r.id, at_min=int(at_min))
        return eff

    def _drain_action(self, t: int, i: int, a: Drain, f: Optional[int]) -> ActionResult:
        cur, eff, issue = self._now(t, f)
        r = self._get_replica(a.replica_id, cur)
        at = a.at_min
        if isinstance(at, (bool, np.bool_)) or not isinstance(at, (int, np.integer)):
            raise ActionError(f"Drain.at_min must be an integer minute, got {at!r}")
        if at < cur * self.Df:
            raise ActionError(f"Drain.at_min {at} lies before the current minute {cur * self.Df}")
        self._drain(r, int(at), issue, eff)
        return ActionResult(i, a, True, r.lease.id, (r.id,), "")

    def _set_admission(self, t: int, i: int, a: SetAdmission, f: Optional[int]) -> ActionResult:
        cur, eff, issue = self._now(t, f)
        r = self._get_replica(a.replica_id, cur)
        v = self._unit(a.value, "SetAdmission.value")
        self._push(r, eff, v, issue, False)
        self._event(issue, "admission", replica=r.id, value=v, fast=eff)
        return ActionResult(i, a, True, r.lease.id, (r.id,), "")

    # ------------------------------------------------------------ routing (§5.5)
    def _route(self, f: int, W: np.ndarray) -> np.ndarray:
        """Served load x (n, m) of fast slot f given the admitting capacity W (J, m)."""
        x = np.zeros((self.n, self.m))
        d = self.demand[:, f]
        kinf = self.inst.kappa_infinite
        for j in range(self.J):
            cl = self.clients_of[j]
            cl = cl[d[cl] > 0]
            if len(cl) == 0:
                continue
            sites = np.flatnonzero(W[j] > 0)
            if len(sites) == 0:
                continue
            ok = self.arc_ok[np.ix_(cl, sites)]
            if not ok.any():
                continue
            dl = np.where(ok, self.delta[np.ix_(cl, sites)], np.inf)
            best = np.argmin(dl, axis=1)                     # lowest site index on ties
            has = ok[np.arange(len(cl)), best]
            if kinf:
                x[cl[has], sites[best[has]]] = d[cl[has]]
                continue
            load = np.zeros(len(sites))
            np.add.at(load, best[has], d[cl[has]])
            cap = W[j, sites]
            if np.all(load <= cap):
                x[cl[has], sites[best[has]]] = d[cl[has]]
                continue
            if len(cl) == 1:
                rem = d[cl[0]]
                for si in np.argsort(dl[0], kind="stable"):
                    if not ok[0, si] or rem <= 0:
                        break
                    v = min(rem, cap[si])
                    x[cl[0], sites[si]] = v
                    rem -= v
                continue
            if len(sites) == 1:
                rem = cap[0]
                for ci in np.argsort(dl[:, 0], kind="stable"):
                    if not ok[ci, 0] or rem <= 0:
                        break
                    v = min(rem, d[cl[ci]])
                    x[cl[ci], sites[0]] = v
                    rem -= v
                continue
            x[np.ix_(cl, sites)] = self._route_lp(d[cl], cap, dl, ok, self.q[j])
        return x

    def _route_lp(self, d: np.ndarray, cap: np.ndarray, dl: np.ndarray, ok: np.ndarray,
                  q: float) -> np.ndarray:
        """Transportation LP min sum (delta - q) x, rows: clients <= d, sites <= cap."""
        nc, ns = ok.shape
        ci, si = np.nonzero(ok)
        nv = len(ci)
        A = np.zeros((nc + ns, nv))
        A[ci, np.arange(nv)] = 1.0
        A[nc + si, np.arange(nv)] = 1.0
        b = np.concatenate([d, cap])
        t0 = time.perf_counter()
        res = linprog(dl[ci, si] - q, A_ub=A, b_ub=b, bounds=(0, None), method="highs")
        self.rt["routing_lp_calls"] += 1
        self.rt["lp_s"] = self.rt.get("lp_s", 0.0) + time.perf_counter() - t0
        if res.status != 0:
            raise RuntimeError(f"routing LP failed: {res.message}")
        out = np.zeros((nc, ns))
        out[ci, si] = np.maximum(res.x, 0.0)
        # remove solver round-off so that client and site rows hold exactly
        s = out.sum(axis=1)
        over = s > d
        out[over] *= (d[over] / s[over])[:, None]
        s = out.sum(axis=0)
        over = s > cap
        out[:, over] *= cap[over] / s[over]
        return out

    # ------------------------------------------------------------ fast slot
    def _fast_step(self, t: int, f: int, results: list[ActionResult]) -> None:
        tf = time.perf_counter()
        Df = self.Df
        fmin = f * Df

        # (a) leases with end minute < (f+1)*Df are dead from f on; their replicas die
        still = []
        for L in self.active:
            if L.end_min < (f + 1) * Df:
                L.dead_fast = f
                for r in L.reps:
                    if r.end_fast is None:
                        r.end_fast = f
                if L.cut_cause is None:
                    self._event(L.end_min, "death", lease=L.id, cause=L.cause(self.T_min))
            else:
                still.append(L)
        self.active = still

        # (b) warm-up and admission changes, (c) admitting capacity
        W = np.zeros((self.J, self.m))
        drops = []
        keep = []
        for r in self.reps_active:
            prev = r.cap
            dead = r.end_fast is not None and r.end_fast <= f
            cap = 0.0
            applied = None
            if not dead:
                while r.pending and r.pending[0][0] <= f:
                    _, _, val, issue, _ = r.pending.pop(0)
                    r.adm = val
                    applied = issue
                if applied is not None:
                    r.change_issue_min = applied
                if f >= r.warm_fast:
                    if not r.warm_seen:
                        r.warm_seen = True
                        self._event(fmin, "warm", replica=r.id, fast=f)
                    cap = r.adm
            if cap < prev:
                drops.append((r, prev, dead))
            r.cap = cap
            if cap > 0:
                W[r.llm, r.lease.site] += cap
            if not dead:
                keep.append(r)
        self.reps_active = keep

        # (d) routing
        t0 = time.perf_counter()
        x = self._route(f, W)
        self.rt["routing_s"] += time.perf_counter() - t0
        d = self.demand[:, f]
        X = x.sum(axis=1)
        b = np.maximum(d - X, 0.0)
        served = self.onehot @ x                              # (J, m)

        # lead times h_j(f) of the capacity drops (§5.6) and drop metrics (§5.9)
        h = np.full(self.J, np.inf)
        for r, prev, dead in drops:
            L = r.lease
            announced = L.announce_slot is not None and L.announce_slot <= t
            if dead and r.unload_issue_min is not None:
                kind, issue = "action", r.unload_issue_min
            elif dead:
                if L.cut_cause is None:
                    kind, issue = "reclaim", None
                elif L.cut_cause == "violation":
                    kind, issue = "violation", None
                else:
                    kind, issue = "action", L.cut_issue_min
            else:
                kind, issue = "action", r.change_issue_min
            if kind == "reclaim":
                lead = float(L.H_min)
            elif kind == "violation":
                lead = 0.0
            else:
                lead = float(L.H_min) if announced else float(fmin - issue)
            h[r.llm] = min(h[r.llm], lead)
            reclaim_caused = kind in ("reclaim", "violation") or announced
            Wp = self.W_prev[r.llm, L.site]
            att = self.served_prev_fast[r.llm, L.site] * prev / Wp if Wp > 0 else 0.0
            self.ms["capacity_drops"] += 1
            self.ms["attributed_load_at_drops"] += att
            if att > self.cfg.tol:
                self.ms["stranding_events"] += 1
            if reclaim_caused:
                self.ms["capacity_drops_reclaim"] += 1
                self.reclaim_until[r.llm] = max(self.reclaim_until[r.llm],
                                                f + -(-60 // Df))

        # (e) ledger
        led = self.ledger
        led.add("routing", t, float(np.sum(self.delta0 * x)) * Df / 60.0)
        led.add("fallback", t, float(np.sum(self.q[self.c_llm] * b)) * Df / 60.0)
        rent = 0.0
        for L in self.active:
            if f >= L.rent_from_fast:
                L.rent_usd += L.rent_per_fast
                rent += L.rent_per_fast
        led.add("lease_rent", t, rent)
        d_prev = self.demand[:, f - 1] if f > 0 else np.zeros(self.n)
        dhat = np.minimum(d_prev, d)
        ratio = np.divide(dhat, d_prev, out=np.zeros(self.n), where=d_prev > 0)
        mv = np.maximum(ratio[:, None] * self.x_prev - x, 0.0).sum(axis=1)
        wv = np.maximum(ratio * self.x_prev.sum(axis=1) - X, 0.0)
        hc = h[self.c_llm]
        jc = self.c_llm
        Tdr = self.Tdr[jc]
        fl_on = (self.mu_fl[jc] > 0) & (Tdr > 0)
        fl_fac = np.zeros(self.n)
        if fl_on.any():
            fl_fac[fl_on] = np.maximum(0.0, 1.0 - 60.0 * hc[fl_on] / Tdr[fl_on])
        pi_fac = np.maximum(self.W_f - hc, 0.0)
        s_kv = float(np.sum(self.mu_kv[jc] * mv))
        s_fl = float(np.sum(self.mu_fl[jc] * fl_fac * mv))
        s_fb = float(np.sum(self.mu_fb[jc] * wv))
        s_pi = float(np.sum(self.pi[jc] * pi_fac * wv))
        led.add("stranding_kv", t, s_kv)
        led.add("stranding_fl", t, s_fl)
        led.add("stranding_fb", t, s_fb)
        led.add("stranding_pi", t, s_pi)

        # (f) fast callback: Drain / SetAdmission, effective from f + 1
        if self.wants_fast:
            fo = FastObs(f=f, served=served.copy(), capacity=W.copy(), fallback=b.copy(),
                         results=list(results))
            tp = time.perf_counter()
            acts = self.policy.on_fast(fo)
            self.rt["policy_s"] += time.perf_counter() - tp
            self._apply(t, acts, f)

        # (g) online invariants INV2, INV3, INV8 and metric sums
        if self.cfg.check_invariants:
            tc = time.perf_counter()
            self._check_fast(t, f, x, b, W, d, d_prev, h, (s_kv, s_fl, s_fb, s_pi))
            self.rt["check_s"] += time.perf_counter() - tc
        ms = self.ms
        dem_j = self.onehot @ d
        fb_j = self.onehot @ b
        ms["demand_load_min_by_llm"] += dem_j * Df
        ms["fallback_load_min_by_llm"] += fb_j * Df
        win = f < self.reclaim_until
        ms["demand_after_reclaims_load_min_by_llm"] += np.where(win, dem_j, 0.0) * Df
        ms["fallback_after_reclaims_load_min_by_llm"] += np.where(win, fb_j, 0.0) * Df
        adm = W > 0
        ms["served_load_min"] += float(served[adm].sum()) * Df
        ms["capacity_load_min"] += float(W[adm].sum()) * Df
        ms["stranded_load_fb"] += float(wv.sum())
        ms["stranded_load_any"] += float(mv.sum())
        if self.cfg.record_routing:
            for c, l in zip(*np.nonzero(x)):
                key = (int(c), int(l))
                arr = self.rec_x.get(key)
                if arr is None:
                    arr = self.rec_x[key] = np.zeros(self.T_f)
                arr[f] = x[c, l]
            self.rec_b[:, f] = b
            self.rec_W[:, :, f] = W
        self.slot_served += served
        self.slot_fallback += b
        self.x_prev, self.W_prev, self.served_prev_fast = x, W, served
        self.rt["fast"].append(time.perf_counter() - tf)

    def _check_fast(self, t, f, x, b, W, d, d_prev, h, booked) -> None:
        """Online INV2, INV3 and INV8 for fast slot f."""
        tol = self.cfg.tol
        X = x.sum(axis=1)
        bad = np.abs(X + b - d) > tol * np.maximum(1.0, d)
        if bad.any() or (x < -tol).any() or (b < -tol).any():
            c = int(np.flatnonzero(bad)[0]) if bad.any() else -1
            self.failures.append(f"INV2 fast slot {f}: conservation or sign violated (client {c})")
        Wc = W[self.c_llm]                                   # (n, m)
        bad = (x > tol) & (self.arc_forbidden | (Wc <= 0.0))
        if bad.any():
            c, l = map(int, np.argwhere(bad)[0])
            self.failures.append(f"INV3 fast slot {f}: load {x[c, l]!r} of client {c} at site {l} "
                                 "on a forbidden arc or without admitting capacity")
        if not self.inst.kappa_infinite:
            over = (self.onehot @ x) > W + tol
            if over.any():
                j, l = map(int, np.argwhere(over)[0])
                self.failures.append(f"INV3 fast slot {f}: LLM {j} site {l} served above capacity")
        # INV8: stranding recomputed in the z form of §5.6, client by client
        exp = np.zeros(4)
        for c in range(self.n):
            j = int(self.c_llm[c])
            dc, dp = d[c], d_prev[c]
            dh = min(dp, dc)
            zp = self.x_prev[c] / dp if dp > 0 else np.zeros(self.m)
            zn = x[c] / dc if dc > 0 else np.zeros(self.m)
            m_c = float(np.maximum(dh * zp - dc * zn, 0.0).sum())
            w_c = max(dh * float(zp.sum()) - dc * float(zn.sum()), 0.0)
            hj = h[j]
            fl = 0.0
            if self.mu_fl[j] > 0 and self.Tdr[j] > 0 and math.isfinite(hj):
                fl = max(0.0, 1.0 - 60.0 * hj / self.Tdr[j])
            pi = max(self.W_f - hj, 0.0) if math.isfinite(hj) else 0.0
            exp += (self.mu_kv[j] * m_c, self.mu_fl[j] * fl * m_c, self.mu_fb[j] * w_c,
                    self.pi[j] * pi * w_c)
        for name, e, v in zip(("stranding_kv", "stranding_fl", "stranding_fb", "stranding_pi"),
                              exp, booked):
            if abs(e - v) > tol * max(1.0, abs(e)):
                self.failures.append(f"INV8 fast slot {f}: {name} booked {v!r}, recomputed {e!r}")

    # ------------------------------------------------------------ end of run
    def _finish(self, wall0: float) -> RunResult:
        inst, cfg = self.inst, self.cfg
        for L in self.active:
            L.dead_fast = self.T_f
            for r in L.reps:
                if r.end_fast is None:
                    r.end_fast = self.T_f
            if L.cut_cause is None:
                self._event(L.end_min, "death", lease=L.id, cause=L.cause(self.T_min))
        self.active = []
        for r in self.replicas:
            if r.end_fast is None:
                r.end_fast = self.T_f
        leases = [LeaseRecord(L.id, L.site, L.contract, L.gpus, L.start_slot, L.start_min,
                              L.prepaid_end_min, L.announce_slot, L.death_min, L.release_min,
                              int(L.end_min), L.cause(self.T_min), float(L.prepaid_usd),
                              float(L.rent_usd), L.tag) for L in self.leases]
        replicas = [ReplicaRecord(r.id, r.lease.id, r.llm, r.load_start_min, int(r.warm_fast),
                                  int(r.end_fast), r.beta_usd) for r in self.replicas]
        schedule = self.lender.realized()

        # INV7 under I2: the delivered bits equal the realized membership
        if self.site_ann_log is not None and cfg.check_invariants:
            mask = np.zeros((self.m, self.T_s), dtype=bool)
            for l, R in enumerate(schedule.R):
                R = np.asarray(R, dtype=np.int64)
                mask[l, R[(R >= 0) & (R < self.T_s)]] = True
            for t, bits in self.site_ann_log.items():
                if not np.array_equal(bits, mask[:, t]):
                    self.failures.append(f"INV7 slot {t}: site_announced differs from the realized R")

        # metric sums (§5.9); GPU-hours from the alive fast slots of each lease (rule T6)
        ms = self.ms
        gh: dict[str, float] = {}
        for L in leases:
            n_alive = max(0, L.end_min // self.Df - L.start_min // self.Df)
            k = inst.contracts[L.contract].klass
            gh[k] = gh.get(k, 0.0) + L.gpus * n_alive * self.Df / 60.0
        checked = 0
        if self.model.schedule in ("trace", "correlated"):
            site_lenders = {s.lender for s in inst.sites}
            checked = sum(1 for lt in inst.lenders
                          if lt.S is not None and (lt.site_index or lt.lender in site_lenders))
        metrics = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in ms.items()}
        metrics["refused"] = dict(ms["refused"])
        metrics.update(gpu_hours_by_class=gh, lender_slots_checked=checked * self.T_s,
                       horizon_days=self.T_min / 1440.0, n_leases=len(leases),
                       n_replicas=len(replicas))
        # C6: the policy's own accounting after the last slot
        report = getattr(self.policy, "report", None)
        metrics["policy"] = report() if callable(report) else {}

        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        act, slow, fast = self.rt["act"], self.rt["slow"], self.rt["fast"]
        t_wall = time.perf_counter()
        end = self.rt["slots_end"]
        runtime = dict(wall_s=t_wall - wall0,
                       slow_step_s_p50=_p(self.rt["slow"], 50), slow_step_s_p99=_p(self.rt["slow"], 99),
                       fast_step_s_p50=_p(self.rt["fast"], 50), fast_step_s_p99=_p(self.rt["fast"], 99),
                       routing_s=self.rt["routing_s"], routing_lp_s=self.rt.get("lp_s", 0.0),
                       routing_lp_calls=self.rt["routing_lp_calls"], policy_s=self.rt["policy_s"],
                       peak_rss_mb=rss_kb / 1024.0,
                       # C7: wall time of act alone per slow slot, and the most leases alive in a slot
                       policy_act_s_mean=float(np.mean(act)) if act else None,
                       policy_act_s_p50=_p(act, 50), policy_act_s_p99=_p(act, 99),
                       policy_act_s_max=float(max(act)) if act else None,
                       n_alive_leases_max=int(self.rt["n_alive_max"]),
                       # C27 (MS5): the setup, the loops' sums, maxima and counts, the online checks, the finish
                       reset_s=float(self.rt["reset_s"]),
                       slow_step_s_sum=math.fsum(slow), slow_step_s_max=float(max(slow)) if slow else None,
                       n_slow_steps=len(slow),
                       fast_step_s_sum=math.fsum(fast), fast_step_s_max=float(max(fast)) if fast else None,
                       n_fast_steps=len(fast),
                       check_s=float(self.rt["check_s"]),
                       finish_s=t_wall - end if end is not None else None)
        routing = None
        if cfg.record_routing:
            routing = {"x": self.rec_x, "b": self.rec_b, "W": self.rec_W}
        events = sorted(self.events, key=lambda e: e[0])          # stable: same-minute order kept
        res = RunResult(name=inst.name, policy=getattr(self.policy, "name", type(self.policy).__name__),
                        seed=int(inst.seed), components=self.ledger.totals(),
                        per_slot=self.ledger.per_slot(), leases=leases, replicas=replicas,
                        events=events, schedule=schedule, violations=self.violations,
                        routing=routing, metrics=metrics, runtime=runtime,
                        invariant_failures=list(self.failures))
        if cfg.check_invariants:
            res.invariant_failures += check_invariants(res, inst, cfg.tol)
        return res


def simulate(inst: Instance, policy, model: LenderModel = LenderModel(),
             cfg: EngineConfig = EngineConfig(), seed: Optional[int] = None, *,
             lender_seed: Optional[int] = None, policy_seed: Optional[int] = None,
             policy_rng: Optional[np.random.Generator] = None) -> RunResult:
    """Run `policy` on `inst` against a fresh Lender(inst, model, rng_streams(ls)['lender']) with
    ls = lender_seed if given, else seed. The policy gets `policy_rng` unchanged if given (tests
    that reproduce a reference draw order), else rng_streams(policy_seed)['policy'] if given, else
    rng_streams(seed)['policy'] (MS1). seed None = inst.seed. RunResult.seeds = {'config': inst.seed,
    'lender': ls, 'policy': the policy seed, or 'injected' for policy_rng} (C5)."""
    from .config import rng_streams
    from .lender import Lender
    seed = inst.seed if seed is None else int(seed)
    ls = seed if lender_seed is None else int(lender_seed)
    streams = rng_streams(ls)
    lender = Lender(inst, model, streams["lender"])
    if policy_rng is not None:
        prng, ps = policy_rng, "injected"
    else:
        ps = seed if policy_seed is None else int(policy_seed)
        prng = (streams if ps == ls else rng_streams(ps))["policy"]
    res = Engine(inst, lender, policy, cfg, prng).run()
    res.seed = seed
    res.seeds = {"config": int(inst.seed), "lender": ls, "policy": ps}
    return res


__all__ = ["ActionError", "Engine", "EngineConfig", "engine_config", "simulate"]
