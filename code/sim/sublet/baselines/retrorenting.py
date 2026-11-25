"""BL5, RetroRenting-style rent (design/sim_spec_ms2.md §15.7; narayana2020retrorenting: Alg. 1 p. 4,
Remark 3 p. 4).

One stack per pool = client c (M45): instances i = 1, 2, ..., created as dbar_c grows (up to
ceil(max_{l <= t} dbar_c(l)) + 1; one instance with kappa_infinite, which sees dbar_c itself).
Instance i sees the residual x_l = min(max(dbar_c(l) - (i - 1), 0), 1) per slow slot and holds at most
one lease. With its site l (the bound site while hosting, else the client's best usable site, §15.1)
and k*(l): gain g_l = x_l (1 - delta_cl / q_j) - c with rent c = g_j a_{l k*} / q_j, fetch cost
M = 60 beta~_{j l k*} / (q_j Δs) (in slot-loads of fallback), prefix sums P(t) = sum_{l <= t} g_l.
- Fetch iff not hosting and P(t-1) - min_{t_evict < tau <= t-1} P(tau-1) >= M; then Buy at the best
  usable site that passes the pre-check, t_fetch = t - 1. Evict iff hosting and
  P(t-1) - max_{t_fetch < tau <= t-1} P(tau-1) < -M; then t_evict = t - 1 and release (rule BR; a fetch
  decision before the deferred release keeps the lease without a new fetch cost). With
  use_current_slot = False (default; our timing) the rule at slot t uses the slots up to t - 1 and
  acts at t; True uses slot t too. The eviction look-back starts at the last fetch (ours).
- A death (cause reclaim or violation) is a forced eviction: hosting off, t_evict = t, so a re-fetch
  needs fresh evidence ("rule"); "immediate" re-fetches at once. A fetch whose Buy is dropped or refused
  leaves the instance not hosting with t_evict unchanged. Notices are ignored. lookback = u slots
  limits the look-back (RR_u, Remark 3). RR's Theorem 1 (p. 4) holds in RR's model only; no ratio is
  claimed here.

MS5b options (design/sublet_v2.md §3, §8.1; C38), defaults the behaviour above:
- tau_min (None): k* over the contracts with tau_k Δs >= tau_min (baselines/common.py; BL5-tau60: 60 with
  use_current_slot).
- contract_rule ('kstar'): 'c2' buys A9.3's base contract kbar(l, j) at every site, and the usable sites, the
  site scores, the rent c and the fetch cost M are those of kbar (common.c2_base_contracts; no commitment rule
  and no insurance, since the stacks have no layer age). Not combined with tau_min.
- mbb (False): A9.4's make-before-break adapted to the stacks (the prototype of BL5N, design/sublet_v2.md §3).
  A hosting instance whose lease L has an own notice (r, E) detaches L at u_L =
  timing.latest_prewarm_slot(r, E, lam_c, grid) (at once if that is None), with lam_c the largest load time of
  the LLM over c's usable sites, and keeps its rule state (no new fetch cost): it buys a replacement at its
  cheapest usable site with no own lease under notice (any usable site if each has one), while L serves until
  its death and is never released. A replacement that cannot be bought, is refused or is dropped by the
  pre-check is a forced eviction at that slot. As in the prototype the detach test reads the instances before
  the slot's results, and the replacement is staged after the slot's other Buys.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from ..algos.common import PolicyError, lam_ms
from ..timing import latest_prewarm_slot
from ..types import PublicView, SlowObs
from .common import Baseline, c2_base_contracts


class RRRule:
    """RetroRenting's fetch and evict tests on prefix sums of per-slot gains (Alg. 1, p. 4), with an
    optional look-back of u slots (RR_u, Remark 3). Slots are processed in order by `step`; the
    candidates P(tau - 1) for tau in (mark, idx] sit in a monotone deque (minima while not hosting,
    maxima while hosting), so each step is O(1) amortized. `mark` is t_evict while not hosting and
    t_fetch while hosting; P(start) = 0."""

    def __init__(self, start: int = -1, lookback: Optional[int] = None):
        self.u = lookback
        self.idx = int(start)          # last processed slot
        self.P = 0.0                   # P(idx)
        self.hosting = False
        self.mark = int(start)
        self.dq: deque = deque()

    def step(self, idx: int, gain: float, M: float) -> bool:
        """Process slot idx (= self.idx + 1) with gain g_idx; True iff the rule fires: fetch while not
        hosting (P(idx) - min P(tau - 1) >= M), evict while hosting (P(idx) - max P(tau - 1) < -M), over
        tau in (mark, idx], within the look-back."""
        if idx != self.idx + 1:
            raise ValueError(f"RRRule.step: slot {idx} after {self.idx}")
        prev = idx - 1
        if prev >= self.mark:
            if self.hosting:
                while self.dq and self.dq[-1][1] <= self.P:
                    self.dq.pop()
            else:
                while self.dq and self.dq[-1][1] >= self.P:
                    self.dq.pop()
            self.dq.append((prev, self.P))
        self.P += float(gain)
        self.idx = idx
        if self.u is not None:
            while self.dq and self.dq[0][0] < idx - self.u:
                self.dq.popleft()
        if not self.dq:
            return False
        if self.hosting:
            return self.P - self.dq[0][1] < -M
        return self.P - self.dq[0][1] >= M

    def fetch(self, at: int) -> None:
        self.hosting, self.mark = True, int(at)
        self.dq.clear()

    def evict(self, at: int) -> None:
        self.hosting, self.mark = False, int(at)
        self.dq.clear()


@dataclass(eq=False)
class RRInstance:
    """Instance i of client c's stack: its rule, lease and site, and its pending fetch."""
    c: int
    i: int
    rule: RRRule
    lease: Optional[int] = None
    site: Optional[int] = None
    deferred: bool = False             # evicted, lease kept until its billed term ends (rule BR)
    pending: Optional[int] = None      # t_fetch of a fetch whose Buy awaits its result
    forced_at: Optional[int] = None    # slot of the last forced eviction
    events: list = field(default_factory=list)   # [t, kind] with kind fetch, evict, forced, keep, refused,
    #                                              and with mbb: detach, mbb (replacement staged)


class RetroRentingStyle(Baseline):
    """BL5 (online-I1): RetroRenting's retrospective rent rule per replica layer of each client."""
    name = "bl5_retrorenting"
    PARAMS = {"use_current_slot": False, "refetch_after_reclaim": "rule", "lookback": None, "defer_release": True,
              "tau_min": None, "contract_rule": "kstar", "mbb": False}
    QUIET_KEYS = ("tau_min", "contract_rule", "mbb")

    def _validate(self) -> None:
        p = self._params
        if not isinstance(p["use_current_slot"], bool):
            raise PolicyError("RetroRentingStyle: use_current_slot must be true or false")
        self._choice("refetch_after_reclaim", ("rule", "immediate"))
        u = p["lookback"]
        if u is not None and (isinstance(u, bool) or not isinstance(u, (int, np.integer)) or u < 1):
            raise PolicyError(f"RetroRentingStyle: lookback must be None or an integer >= 1, got {u!r}")
        if p["contract_rule"] == "c2" and p["tau_min"] is not None:
            raise PolicyError("RetroRentingStyle: tau_min applies to contract_rule 'kstar' only")

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        self.kinf = bool(view.kappa_infinite)
        self.stacks: list[list[RRInstance]] = [[] for _ in range(self.n)]
        self.maxd = np.zeros(self.n)
        self.prev_dbar = np.zeros(self.n)
        st = self.sites
        if self._params["contract_rule"] == "c2":
            st.use_contracts(c2_base_contracts(view))
        self.home = [st.best_static(c) for c in range(self.n)]       # site of the gains while not hosting
        self.mbb = bool(self._params["mbb"])
        if self.mbb:
            L = lam_ms(view)
            self.lam_c = np.array([int(max((L[int(st.cl_llm[c]), l] for l in st.order[c]), default=0))
                                   for c in range(self.n)], dtype=np.int64)
            self.noticed: dict[int, tuple[int, int]] = {}            # own noticed lease alive -> (r_slot, death_min)
            self.detached: set[int] = set()                          # noticed leases no instance holds any more
            self.mbb_pending: set[tuple[int, int]] = set()           # (c, i) whose replacement awaits its result
            self.mbb_counts = {"detached": 0, "buys": 0, "ok": 0, "failed": 0, "no_site": 0,
                               "noticed_site_used": 0}

    # -------------------------------------------------------- per-slot quantities
    def _c_M(self, c: int, l: int) -> tuple[float, float, float]:
        """(rent c, fetch cost M, delta_cl / q_j) at site l with its contract (k*(l), or kbar(l, j) with
        contract_rule 'c2'), normalized by q_j."""
        st = self.sites
        j = int(st.cl_llm[c])
        k = st.contract(l, j)
        q = st.q[j]
        rent = st.g[j] * st.price_of(l, j) / q
        M = 60.0 * float(self.view.beta_tilde_usd[j, l, k]) / (q * self.slow_min)
        return rent, M, st.delta[c, l] / q

    def _residual(self, d: float, i: int) -> float:
        return d if self.kinf else min(max(d - (i - 1), 0.0), 1.0)

    def _grow(self, c: int, idx: int) -> None:
        """Create the instances up to ceil(max dbar_c) + 1 (one with kappa_infinite); a new instance
        starts at P(idx - 1) = 0 with t_evict = idx - 1, which is the same as having existed with zero
        residual (gains -c only)."""
        want = 1 if self.kinf else math.ceil(self.maxd[c]) + 1
        while len(self.stacks[c]) < want:
            i = len(self.stacks[c]) + 1
            self.stacks[c].append(RRInstance(c, i, RRRule(idx - 1, self._params["lookback"])))

    def _release(self, obs: SlowObs, inst: RRInstance) -> None:
        self.book.release(inst.lease)
        self._released.add(inst.lease)
        self.counts["releases"] += 1
        inst.lease = inst.site = None
        inst.deferred = False

    # -------------------------------------------------------- make-before-break (mbb)
    def _mbb_detach(self, obs: SlowObs) -> list[RRInstance]:
        """Record the slot's own notices and detach the lease of every hosting instance whose notice reached
        its pre-warm slot u_L (or has none); returns those instances. Sets the sites of own leases under
        notice (self._mbb_excl). Runs before the slot's results are read (the prototype's order)."""
        for nt in obs.notices:
            self.noticed[int(nt.lease_id)] = (int(nt.r_slot), int(nt.death_min))
        self._mbb_excl = {int(obs.leases[lid].site) for lid in self.noticed if lid in obs.leases}
        todo = []
        for stack in self.stacks:
            for inst in stack:
                lid = inst.lease
                if lid is None or lid not in self.noticed or lid not in obs.leases or not inst.rule.hosting:
                    continue
                r, death = self.noticed[lid]
                u = latest_prewarm_slot(r, death, int(self.lam_c[inst.c]), self.view.grid)
                if u is None or obs.t >= u:
                    self.detached.add(lid)
                    inst.lease = inst.site = None
                    inst.deferred = False
                    inst.events.append([obs.t, "detach"])
                    self.mbb_counts["detached"] += 1
                    todo.append(inst)
        return todo

    def _mbb_result(self, obs: SlowObs, key: tuple, r) -> None:
        """Result of a replacement Buy: the instance holds the new lease and keeps its rule state; a refused or
        dropped replacement is a forced eviction at this slot."""
        _, c, i = key
        inst = self.stacks[c][i - 1]
        self.mbb_pending.discard((c, i))
        if r.ok:
            inst.lease, inst.site = int(r.lease_id), int(r.action.site)
            self.mbb_counts["ok"] += 1
            return
        inst.lease = inst.site = None
        inst.events.append([obs.t, "refused"])
        self.mbb_counts["failed"] += 1
        if inst.rule.hosting:
            inst.rule.evict(obs.t)
            inst.events.append([obs.t, "forced"])

    def _mbb_buy(self, obs: SlowObs, todo: list[RRInstance]) -> None:
        """Stage the replacements of the detached instances that still host: the cheapest usable site with no
        own lease under notice, else any usable site; none is a forced eviction at this slot."""
        t = obs.t
        for inst in todo:
            if inst.lease is not None or not inst.rule.hosting or (inst.c, inst.i) in self.mbb_pending:
                continue
            l = self.sites.best_site(inst.c, obs, self.book, self.unavail | self._mbb_excl)
            if l is None:
                l = self.sites.best_site(inst.c, obs, self.book, self.unavail)
                if l is not None:
                    self.mbb_counts["noticed_site_used"] += 1
            if l is None:
                inst.rule.evict(t)
                inst.events.append([t, "forced"])
                self.mbb_counts["no_site"] += 1
                continue
            self.mbb_pending.add((inst.c, inst.i))
            self._buy(("mbb", inst.c, inst.i), l, int(self.sites.cl_llm[inst.c]), f"bl5:{inst.c}:{inst.i}:mbb")
            inst.events.append([t, "mbb"])
            self.mbb_counts["buys"] += 1

    # -------------------------------------------------------- one slot
    def act(self, obs: SlowObs) -> list:
        t = obs.t
        todo = self._mbb_detach(obs) if self.mbb else []
        res = self._begin(obs)
        if self.mbb:
            for key, r in res:
                if key[0] == "mbb":
                    self._mbb_result(obs, key, r)
            res = [(key, r) for key, r in res if key[0] != "mbb"]
        for (c, i), r in res:
            inst = self.stacks[c][i - 1]
            if r.ok:
                inst.lease, inst.site, inst.deferred = int(r.lease_id), int(r.action.site), False
                inst.rule.fetch(inst.pending)
            else:
                inst.events.append([t, "refused"])
                if inst.rule.hosting:              # an "immediate" re-fetch failed: the forced eviction stands
                    inst.rule.evict(inst.forced_at)
            inst.pending = None
        # deaths: forced evictions
        immediate = []
        for stack in self.stacks:
            for inst in stack:
                if inst.lease is not None and inst.lease not in obs.leases:
                    died = self._gone(inst.lease, obs)
                    was_hosting = inst.rule.hosting
                    inst.lease = inst.site = None
                    inst.deferred = False
                    if died and was_hosting:
                        inst.events.append([t, "forced"])
                        inst.forced_at = t
                        if self._params["refetch_after_reclaim"] == "immediate":
                            immediate.append(inst)
                        else:
                            inst.rule.evict(t)
        d = np.asarray(obs.demand, dtype=np.float64)
        dbar = d.mean(axis=1) if d.shape[1] else np.zeros(self.n)
        use_cur = self._params["use_current_slot"]
        idx = t if use_cur else t - 1
        if idx >= 0:
            dsl = dbar if use_cur else self.prev_dbar
            for c in range(self.n):
                if self.home[c] is None:
                    continue
                self.maxd[c] = max(self.maxd[c], float(dsl[c]))
                self._grow(c, idx)
                for inst in self.stacks[c]:
                    self._step(obs, inst, idx, float(dsl[c]), decide=inst not in immediate)
        for inst in immediate:                     # refetch_after_reclaim "immediate": re-fetch at once
            l = self.sites.best_site(inst.c, obs, self.book, self.unavail)
            if l is not None:
                inst.pending = idx
                self._buy((inst.c, inst.i), l, int(self.sites.cl_llm[inst.c]), f"bl5:{inst.c}:{inst.i}")
                inst.events.append([t, "fetch"])
            else:
                inst.rule.evict(t)
        self.prev_dbar = dbar
        if self.mbb:
            self._mbb_buy(obs, todo)
            for lid in [lid for lid in self.noticed if lid not in obs.leases]:
                del self.noticed[lid]
                if lid in self.detached:               # never released by BL5: it died (counted as by _gone)
                    self.detached.discard(lid)
                    self._gone(lid, obs)
        return self.book.assemble(obs, self.view)

    def _step(self, obs: SlowObs, inst: RRInstance, idx: int, dval: float, decide: bool = True) -> None:
        """Process slot idx for one instance (its gain at the bound site while hosting, else at the
        client's home site) and act on the rule's verdict unless `decide` is False."""
        c = inst.c
        l = inst.site if inst.rule.hosting and inst.site is not None else self.home[c]
        rent, M, dq = self._c_M(c, l)
        gain = self._residual(dval, inst.i) * (1.0 - dq) - rent
        fire = inst.rule.step(idx, gain, M)
        if not decide:
            return
        t = obs.t
        if inst.rule.hosting:
            if fire:
                inst.rule.evict(idx)
                inst.events.append([t, "evict"])
                L = obs.leases.get(inst.lease) if inst.lease is not None else None
                if L is not None:
                    if self._release_due(obs, L):
                        self._release(obs, inst)
                    else:
                        inst.deferred = True
                        self.counts["deferred_leases"] += 1
            return
        # not hosting
        if inst.deferred and inst.lease is not None:
            L = obs.leases[inst.lease]
            if fire:
                inst.rule.fetch(idx)               # keep the lease, no new fetch cost
                inst.deferred = False
                inst.events.append([t, "keep"])
                return
            if self._release_due(obs, L):
                self._release(obs, inst)
            return
        if fire and inst.pending is None and inst.lease is None:
            l = self.sites.best_site(c, obs, self.book, self.unavail)
            if l is not None:
                inst.pending = idx
                self._buy((c, inst.i), l, int(self.sites.cl_llm[c]), f"bl5:{c}:{inst.i}")
                inst.events.append([t, "fetch"])

    def report(self) -> dict:
        out = super().report()
        if hasattr(self, "stacks"):
            out["instances"] = [{"client": inst.c, "i": inst.i, "events": [list(e) for e in inst.events]}
                                for stack in self.stacks for inst in stack]
            if self.mbb:
                out["mbb"] = {**self.mbb_counts, "lam_c_ms": [int(x) for x in self.lam_c]}
        return out


__all__ = ["RetroRentingStyle", "RRRule", "RRInstance"]
