"""Trivial policies (design/sim_spec.md §5.8).

AlwaysFallback  never acts: every demand-minute goes to fallback.
FixedPlan       replays an offline plan (list of PlannedLease from the DP or the MILP).
RenewReplay     replays a rounded plan of the reference primal-dual (code/theory_checks/c3/pd.py)
                with the renewal semantics of pd.real_cost_renew.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

import numpy as np

from ..types import (Action, Buy, FastObs, PlannedLease, PublicView, Release, SetAdmission,
                     SlowObs)
from .base import Policy


class AlwaysFallback(Policy):
    """Never acts. Cost = sum over clients and fast slots of q_j d_c(f) Δf / 60."""
    name = "always_fallback"

    def act(self, obs: SlowObs) -> list[Action]:
        return []


class FixedPlan(Policy):
    """Replays `plan` (§5.8): at slow slot t it releases the leases with release_slot == t, buys
    the entries with start_slot == t (one Buy of n replicas each) and switches admission at the
    boundaries of the admission_off intervals [a, b): SetAdmission(0) at a, SetAdmission(1) at b.
    A boundary at the first fast slot of a slow slot is set from act (at the purchase slot through
    Buy.admission); any other boundary from on_fast one fast slot earlier, so `wants_fast` is True
    iff some boundary is not at a slow-slot start. An interval end at which the lease no longer
    holds its replicas is skipped. A refused purchase is recorded in `refused` and skipped."""
    name = "fixed_plan"

    def __init__(self, plan: list[PlannedLease]):
        self.plan = list(plan)
        for i, p in enumerate(self.plan):
            if p.release_slot is not None and p.release_slot <= p.start_slot:
                raise ValueError(f"plan entry {i}: release_slot {p.release_slot} <= start_slot "
                                 f"{p.start_slot}")
            if p.n < 1:
                raise ValueError(f"plan entry {i}: n = {p.n} < 1")
            for a, b in p.admission_off:
                if not a < b:
                    raise ValueError(f"plan entry {i}: empty admission_off interval [{a}, {b})")

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        phi = view.grid.phi
        self.phi, self.fast_min = phi, view.grid.fast_min
        self.T_fast = view.grid.T_fast
        self.by_start = defaultdict(list)
        self.by_release = defaultdict(list)
        self.bounds = defaultdict(list)       # fast slot -> [(entry, admission value)]
        for i, p in enumerate(self.plan):
            self.by_start[p.start_slot].append(i)
            if p.release_slot is not None:
                self.by_release[p.release_slot].append(i)
            f_buy = p.start_slot * phi
            for a, b in p.admission_off:
                if a > f_buy:
                    self.bounds[a].append((i, 0.0))
                if b > f_buy:
                    self.bounds[b].append((i, 1.0))
        self.wants_fast = any(f % phi for f in self.bounds)
        self.lease_of: dict[int, int] = {}          # entry -> lease id
        self.replicas_of: dict[int, tuple[int, ...]] = {}
        self.death_of: dict[int, int] = {}          # entry -> death minute (from notices)
        self.gone: set[int] = set()                 # entries whose lease was released or ended
        self.refused: list[tuple[int, str]] = []    # (entry, reason)
        self.pending: list[tuple[int, int]] = []    # (action index, entry) of the last act's Buys

    def _absorb(self, results) -> None:
        """Map the results of the last act's Buy actions to plan entries."""
        if not self.pending or not results:
            return
        by_index = {r.index: r for r in results}
        for ai, i in self.pending:
            r = by_index.get(ai)
            if r is None:
                continue
            if r.ok:
                self.lease_of[i] = r.lease_id
                self.replicas_of[i] = tuple(r.replica_ids)
            else:
                self.refused.append((i, r.reason))
                self.gone.add(i)
        self.pending = []

    def _alive_at(self, i: int, f: int) -> bool:
        """Lease of entry i alive in fast slot f, as far as the policy knows (rule T6)."""
        if i not in self.lease_of or i in self.gone or f >= self.T_fast:
            return False
        death = self.death_of.get(i)
        return death is None or (f + 1) * self.fast_min <= death

    def act(self, obs: SlowObs) -> list[Action]:
        self._absorb(obs.results)
        t, f0 = obs.t, obs.t * self.phi
        entry_of = {lid: i for i, lid in self.lease_of.items()}
        for i, lid in self.lease_of.items():
            if lid not in obs.leases:
                self.gone.add(i)
            elif obs.leases[lid].death_min is not None:
                self.death_of[i] = obs.leases[lid].death_min
        for nt in obs.notices:
            if nt.lease_id in entry_of:
                self.death_of[entry_of[nt.lease_id]] = nt.death_min
        actions: list[Action] = []
        for i in self.by_release.get(t, ()):
            if i in self.lease_of and i not in self.gone:
                actions.append(Release(self.lease_of[i]))
                self.gone.add(i)
        for i in self.by_start.get(t, ()):
            p = self.plan[i]
            off = any(a <= f0 < b for a, b in p.admission_off)
            self.pending.append((len(actions), i))
            actions.append(Buy(p.site, p.contract, p.llm, p.n, tag=f"plan:{i}",
                               admission=0.0 if off else 1.0))
        for i, v in self.bounds.get(f0, ()):
            if self._alive_at(i, f0):
                for rid in self.replicas_of[i]:
                    if rid in obs.replicas:
                        actions.append(SetAdmission(rid, v))
        return actions

    def on_fast(self, obs: FastObs) -> list[Action]:
        self._absorb(obs.results)
        nxt = obs.f + 1
        if nxt % self.phi == 0:
            return []          # boundaries at slow-slot starts are set from act
        actions: list[Action] = []
        for i, v in self.bounds.get(nxt, ()):
            if self._alive_at(i, nxt):
                actions.extend(SetAdmission(rid, v) for rid in self.replicas_of[i])
        return actions


def _remap(m, i: int) -> int:
    if m is None:
        return int(i)
    return int(m[i])


class RenewReplay(Policy):
    """Replays a rounded PD plan exactly as pd.real_cost_renew executes it (§5.8).

    `opened` maps columns (tag, l, j, k, s) (tag 'A' or 'P') to their opening slot t0
    (round_pd(...)['opened']). For every key (l, j, k) the needed coverage is
    U = union of [t0, min(s + L_k, T)) with L_k = tau_k + floor(H_k / Δs) (rule T12; T_slow for a
    protected contract). At slot t, per key in order of first appearance: a lease absent from
    obs.leases is forgotten; if t is in U and no lease is held, Buy(l, k, j, 1); if t is not in U
    and the lease is past its window (t >= start + L_k), Release. A lease is kept while it is
    alive, also during its notice period.

    `slot_of` maps core indices to instance indices: a dict with optional keys 'site', 'llm' and
    'contract', each a sequence or dict indexed by the core index (missing key: identity; None:
    identity everywhere, as for from_core instances)."""
    name = "renew_replay"

    def __init__(self, opened: dict, slot_of: Optional[dict] = None):
        self.opened = dict(opened)
        self.slot_of = dict(slot_of) if slot_of else {}

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        g = view.grid
        T = g.T_slow
        ms, mj, mk = (self.slot_of.get(k) for k in ("site", "llm", "contract"))
        self.need: dict[tuple[int, int, int], np.ndarray] = {}
        self.L: dict[tuple[int, int, int], int] = {}
        for F, t0 in self.opened.items():
            _, l, j, k, s = F
            key = (_remap(ms, l), _remap(mj, j), _remap(mk, k))
            li, ji, ki = key
            if not (0 <= li < len(view.sites) and 0 <= ji < len(view.llms)
                    and 0 <= ki < len(view.contracts)):
                raise ValueError(f"column {F} maps to an invalid (site, LLM, contract) {key}")
            if ki not in view.sites[li].menu:
                raise ValueError(f"column {F}: contract {ki} is not offered at site {li}")
            c = view.contracts[ki]
            Lk = T if c.protected else c.tau_slots + c.H_min // g.slow_min
            U = self.need.get(key)
            if U is None:
                U = self.need[key] = np.zeros(T, dtype=bool)
                self.L[key] = Lk
            U[int(t0):min(int(s) + Lk, T)] = True
        self.held: dict[tuple[int, int, int], Optional[int]] = {key: None for key in self.need}
        self.start: dict[int, int] = {}
        self.pending: list[tuple[int, tuple[int, int, int], int]] = []
        self.refused: list[tuple[tuple[int, int, int], int, str]] = []

    def act(self, obs: SlowObs) -> list[Action]:
        t = obs.t
        if self.pending:
            by_index = {r.index: r for r in obs.results}
            for ai, key, t_buy in self.pending:
                r = by_index.get(ai)
                if r is not None and r.ok:
                    self.held[key] = r.lease_id
                    self.start[r.lease_id] = t_buy
                elif r is not None:
                    self.refused.append((key, t_buy, r.reason))
            self.pending = []
        actions: list[Action] = []
        for key, U in self.need.items():
            l, j, k = key
            lid = self.held[key]
            if lid is not None and lid not in obs.leases:
                lid = self.held[key] = None
            if U[t]:
                if lid is None:
                    self.pending.append((len(actions), key, t))
                    actions.append(Buy(l, k, j, 1, tag=f"renew:{l},{j},{k}"))
            elif lid is not None and t >= self.start[lid] + self.L[key]:
                actions.append(Release(lid))
                self.held[key] = None
        return actions
