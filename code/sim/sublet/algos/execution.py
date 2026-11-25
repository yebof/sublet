"""Execution layer X1-X4 (design/sim_spec_ms2.md §3.5, §7; design §3.2.3).

The rounded PD decides which windows must be covered; the execution layer decides which live
lease realizes each window. Its unit is the logical slot sigma = (l0, j, k, iota) of a PD column
type (§7.1): the coverage `need` it must provide (the union of [t0, min(s + L_k, T)) over its
opened windows, as pd.real_cost_renew), the lease that realizes it now (possibly at another site
after rotations), and the pointer `ptr` to the site of its next purchase (initially l0).

Per slow slot the planner calls `open` for every column it opened, then `step(obs)` (§7.2):
notices go to the reclaim handler (X4), deaths of revoked leases rotate `ptr` (X3, `RRSiteRule`,
or marking's rule of §8.3), pre-warm purchases are committed, missing leases are bought, alive
leases are renewed (X1) and unneeded ones released (X2). Every action is staged in the policy's
`LeaseBook` (§2.3); the results of the layer's purchases come back through `absorb`.

Guarantees: on from_core instances with x3=False, x2="reference" and a cold handler the layer is
pd.real_cost_renew's execution (MS1 RenewReplay); real cost <= 2 x accounted cost is VERIFIED
NUMERICALLY there only (c3/out/c3_benchmark.txt (c)). RR-renew on the T4/O1 family is O1-B
(PROVEN). With X2's timer, X3 in general or the handler the layer is a heuristic.

Practical Sublet (design/q44_practical_sublet.md §6.1): `profit_idle` (default False) is knob F under
X2's timer (a lease whose attributed load at fallback price is worth less than its rent counts as
idle), used only by the ablation row "X2 timer in place of reference"; releases are counted by cause.
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

import numpy as np

from ..timing import warm_fast
from ..types import Buy, Notice, PublicView, SlowObs
from .common import (EPS_DEMAND, LeaseBook, PolicyError, attributed_load, column_cost, lam_ms,
                     pd_window_slots, slot_max_demand, treated_as_protected)

if TYPE_CHECKING:                       # handler.py (U9) is used through the object passed in
    from .handler import Decision, ReclaimHandler

PENDING = -1            # next_lease of a pre-warm staged in this slot, until its result arrives
IDLE_LOAD = 1e-9        # X2 timer: a lease with attributed load <= IDLE_LOAD hosted no load
BOOK_KEY = "x"          # first field of the layer's LeaseBook keys


@dataclass(eq=False)
class LogicalSlot:
    """A PD column type (l0, j, k, iota) and the lease that realizes it (§7.1).

    The fields up to `idle` are those of §3.5; the others are the layer's bookkeeping."""
    key: tuple                     # (l0, j, k, iota): the PD column type
    need: np.ndarray               # (T_slow,) bool
    ptr: int                       # site of the current or next lease
    lease: Optional[int] = None    # current lease id (None while a purchase is in flight: `buying`)
    lease_site: Optional[int] = None          # site of the current lease or of the purchase in flight
    start_slot: Optional[int] = None
    prepaid_end_min: Optional[int] = None
    next_lease: Optional[int] = None          # pre-warmed replacement while the old lease lives
                                              # (PENDING from its purchase until the result arrives)
    pending: Optional["Decision"] = None      # pre-warm scheduled at decision.t_commit
    idle: int = 0
    # bookkeeping
    buying: bool = False           # a purchase of the current lease is in flight (result at t + 1)
    L: int = 1                     # PD window L_k of the slot's contract, in slow slots
    noticed: bool = False          # the current lease has been announced
    ptr_moved: bool = False        # a decision set ptr for the current lease's replacement
    pending_for: Optional[int] = None     # lease id the pending decision was made for
    next_site: Optional[int] = None
    next_noticed: bool = False
    next_notice: Optional[Notice] = None      # notice on next_lease before it took over (handled then)
    held_before: bool = False      # a purchase of the slot has succeeded (else cause 'first')
    last_end: Optional[str] = None # how the last lease ended: 'revoked', 'released' or 'ended'
    buy_cause: str = "first"       # cause of the purchase in flight (retried after a refusal)
    opened: int = 0                # windows opened by the planner
    new_window: bool = False       # a window was opened at this slot (renewal count)
    retiring: list = field(default_factory=list)   # [(lease id, release slot)] after marking moves
    move_from: Optional[tuple] = None              # (lease id, site, noticed) of a retiring lease
    pool: Optional[tuple] = None   # X3 pool at the last purchase (sites in pi order; §12)
    windows: list = field(default_factory=list)    # [(t0, s, L)] of the opened windows (need's union)
    group: Optional[tuple] = None  # marking group key (j, k, P) (§8.3)

    @property
    def l0(self) -> int:
        return self.key[0]

    @property
    def j(self) -> int:
        return self.key[1]

    @property
    def k(self) -> int:
        return self.key[2]

    def holds(self) -> bool:
        """A current lease is set (it may have died in this slot)."""
        return self.lease is not None


# ---------------------------------------------------------------- site rules
class SiteRule:
    """Replacement-site rule of the execution layer: RRSiteRule (X3, §7.3) or
    marking.MarkingSiteRule (§8.3). `next_site` gives the replacement site at a notice or a
    revocation death; `on_slot` runs at the start of every step. The other hooks are additions
    used by marking: `place` (site of a first purchase or of a re-buy after a release), `on_buy`
    (a purchase for the slot was staged) and `report`."""
    layer: "ExecutionLayer"

    def bind(self, layer: "ExecutionLayer") -> None:
        self.layer = layer

    def next_site(self, slot: LogicalSlot, obs: SlowObs, t: int) -> int:
        raise NotImplementedError

    def on_slot(self, obs: SlowObs) -> None:
        return None

    def place(self, slot: LogicalSlot, obs: SlowObs, t: int, cause: str) -> int:
        return slot.ptr

    def on_buy(self, slot: LogicalSlot, site: int, t: int) -> None:
        return None

    def report(self) -> dict:
        return {}


class RRSiteRule(SiteRule):
    """X3 round robin (§7.3, M15). For sigma = (l0, j, k, iota):
    - stranded clients S: clients of LLM j with delta_{c l0} < inf and D_c(t) > EPS_DEMAND, else
      all clients of j with delta_{c l0} < inf;
    - feasible sites: k not treated as protected, k on the site's menu, delta_{cl} < inf for every
      c in S; pool: feasible sites with C_{ljk} <= zeta min C (column cost of §5.2, window L_k);
      empty pool: {sigma.ptr};
    - next site: the first pool site after sigma.ptr in the cyclic order of pi (ptr itself last);
      with the skip rule, sites where the platform holds another announced lease (any LLM) are
      skipped unless every pool site would be.
    The pool is recomputed at every call. On the T4/O1 family (pi the identity, equal costs) the
    next site is (ptr + 1) mod m, fam.rr_choose."""

    def __init__(self, view: PublicView, *, zeta: float = 2.0, skip_rule: bool = True,
                 site_perm: Optional[np.ndarray] = None, protected_window: Optional[int] = None):
        m = len(view.sites)
        self.view = view
        self.perm = np.arange(m, dtype=np.int64) if site_perm is None else np.asarray(site_perm, dtype=np.int64)
        if sorted(self.perm.tolist()) != list(range(m)):
            raise PolicyError(f"site_perm is not a permutation of the {m} sites")
        self.pos = np.empty(m, dtype=np.int64)
        self.pos[self.perm] = np.arange(m)
        zeta = float(zeta)
        if not zeta >= 1.0:
            raise PolicyError(f"zeta must be >= 1 (inf: every feasible site), got {zeta}")
        self.zeta = zeta
        self.skip_rule = bool(skip_rule)
        self.protected_window = protected_window
        self.cl_llm = np.asarray(view.client_llm, dtype=np.int64)
        self.delta_ok = np.isfinite(np.asarray(view.client_delta_usd_per_h, dtype=np.float64))
        self.offers = np.zeros((m, len(view.contracts)), dtype=bool)
        for l, s in enumerate(view.sites):
            self.offers[l, list(s.menu)] = True
        self._cost: dict[tuple[int, int], np.ndarray] = {}
        self._D: tuple = (None, None)          # (obs, D_c(t)) of the last observation seen
        self.stats = {"calls": 0, "pool_empty": 0, "skipped": 0, "skip_ignored": 0}

    def costs(self, j: int, k: int) -> np.ndarray:
        """(m,) column costs C_{ljk} on the PD window of contract k (INF where k is not offered)."""
        c = self._cost.get((j, k))
        if c is None:
            L = pd_window_slots(self.view, k, self.protected_window)
            c = np.array([column_cost(self.view, l, j, k, L) if self.offers[l, k] else np.inf
                          for l in range(len(self.view.sites))], dtype=np.float64)
            self._cost[(j, k)] = c
        return c

    def demand(self, obs: SlowObs) -> np.ndarray:
        """D_c(t) of the observation (slot_max_demand, cached per observation)."""
        if self._D[0] is not obs:
            self._D = (obs, slot_max_demand(obs))
        return self._D[1]

    def stranded(self, slot: LogicalSlot, D: np.ndarray) -> np.ndarray:
        """Indices of the stranded clients S of the slot (§7.3)."""
        mine = np.flatnonzero((self.cl_llm == slot.j) & self.delta_ok[:, slot.l0])
        on = mine[D[mine] > EPS_DEMAND]
        return on if on.size else mine

    def pool(self, slot: LogicalSlot, obs: SlowObs, t: int) -> list[int]:
        """The pool P of the slot at slot t, in pi order (may be empty)."""
        j, k = slot.j, slot.k
        if treated_as_protected(self.view, k):
            return []
        S = self.stranded(slot, self.demand(obs))
        ok = self.offers[:, k].copy()
        if S.size:
            ok &= self.delta_ok[S].all(axis=0)
        if not ok.any():
            return []
        C = self.costs(j, k)
        if math.isfinite(self.zeta):
            ok &= C <= self.zeta * float(C[ok].min())
        return [int(l) for l in self.perm if ok[l]]

    def next_site(self, slot: LogicalSlot, obs: SlowObs, t: int) -> int:
        self.stats["calls"] += 1
        P = set(self.pool(slot, obs, t))
        if not P:
            self.stats["pool_empty"] += 1
            return int(slot.ptr)
        m = len(self.perm)
        p0 = int(self.pos[slot.ptr])
        cand = [int(self.perm[(p0 + i) % m]) for i in range(1, m + 1)]
        cand = [l for l in cand if l in P]
        if self.skip_rule:
            own = {slot.lease, slot.next_lease}
            busy = {L.site for lid, L in obs.leases.items() if L.announce_slot is not None and lid not in own}
            keep = [l for l in cand if l not in busy]
            if keep:
                self.stats["skipped"] += len(cand) - len(keep)
                cand = keep
            else:
                self.stats["skip_ignored"] += 1
        return cand[0]

    def report(self) -> dict:
        return {"rule": "rr", **self.stats}


# ---------------------------------------------------------------- the layer
class ExecutionLayer:
    """Logical slots with X1 (renew), X2 (release: 'reference' or 'timer'), X3 (rotation through
    the site rule) and the handler hook X4 (§7.2). Purchases are staged in `book` under the key
    ('x', tag, slot key, 'lease' or 'next', slot); the policy passes the output of `book.begin`
    to `absorb` before the planner's `open` calls and `step`.

    profit_idle (knob F under X2's timer, default False): a lease with attributed load att > IDLE_LOAD
    also counts as idle in a slot when att q_j < g_j a (a = price of the lease's site and contract).
    stats['releases_by_cause'] counts the layer's releases: 'x2_reference', 'x2_timer', 'x1_off' (a
    fresh lease for a new window), 'move' (marking moves released at once) and 'retired' (marking
    moves released when the new replica is warm)."""

    def __init__(self, view: PublicView, book: LeaseBook, *, x1: bool = True, x2: str = "reference",
                 x3: bool = True, zeta: float = 2.0, skip_rule: bool = True,
                 site_rule: Optional[SiteRule] = None, handler: Optional["ReclaimHandler"] = None,
                 site_perm=None, protected_window: Optional[int] = None, tag: str = "x",
                 profit_idle: bool = False):
        if x2 not in ("reference", "timer"):
            raise PolicyError(f"x2 must be 'reference' or 'timer', got {x2!r}")
        self.view, self.book = view, book
        self.x1, self.x2, self.x3 = bool(x1), x2, bool(x3)
        self.tag = str(tag)
        self.profit_idle = bool(profit_idle)
        g = view.grid
        self.T, self.slow, self.fast, self.phi = g.T_slow, g.slow_min, g.fast_min, g.phi
        self.rr = RRSiteRule(view, zeta=zeta, skip_rule=skip_rule, site_perm=site_perm,
                             protected_window=protected_window)
        self.rr.bind(self)
        self.site_rule = site_rule if site_rule is not None else self.rr
        if site_rule is not None:
            site_rule.bind(self)
        self.handler = handler
        self.lam_ms = lam_ms(view)
        self.g = np.array([x.g for x in view.llms], dtype=np.int64)
        self.slots: dict[tuple, LogicalSlot] = {}      # creation order = the layer's key order
        self._n_idle: dict[tuple[int, int, int], float] = {}
        self.stats = {"windows": 0, "windows_dropped": 0, "renewals": 0, "purchases": {"first": 0, "cold": 0, "prewarm": 0,
                                                                  "rebuy": 0, "move": 0},
                      "rotations": 0, "releases": 0, "retired": 0, "refused": {}, "notices": 0,
                      "releases_by_cause": {"x2_reference": 0, "x2_timer": 0, "x1_off": 0, "move": 0, "retired": 0},
                      "revoked_deaths": 0, "other_deaths": 0, "decisions": {},
                      "prewarm": {"decided": 0, "committed": 0, "cancelled": 0, "dropped": 0,
                                  "next_lost": 0}}

    # ------------------------------------------------------------ planner side
    def open(self, key: tuple, t0: int, s: int, L: int) -> None:
        """Window [s, s + L) of type key = (l0, j, k, iota) opened at t0: need[t0 : min(s + L, T)]
        = True (pd.real_cost_renew's coverage); the slot is created at its first window."""
        key = tuple(int(x) for x in key)
        if len(key) != 4:
            raise PolicyError(f"logical slot key must be (l0, j, k, iota), got {key}")
        sl = self.slots.get(key)
        if sl is None:
            sl = LogicalSlot(key=key, need=np.zeros(self.T, dtype=bool), ptr=key[0], L=int(L))
            self.slots[key] = sl
        sl.need[int(t0):min(int(s) + int(L), self.T)] = True
        sl.windows.append((int(t0), int(s), int(L)))
        sl.opened += 1
        sl.new_window = True
        self.stats["windows"] += 1

    def drop_window(self, key: tuple, s: int, t: int) -> bool:
        """A refused PD column (§6.5) leaves the opened set, so its window [s, s + L) leaves the
        slot's coverage (M11: no retry of a refused column): from slot t on, need is the union of the
        slot's other opened windows. Only while the slot holds no lease (a refused purchase left the
        window unrealized). Returns whether a window was dropped."""
        sl = self.slots.get(tuple(int(x) for x in key))
        if sl is None or sl.holds() or sl.buying:
            return False
        i = next((i for i, w in enumerate(sl.windows) if w[1] == int(s)), None)
        if i is None:
            return False
        del sl.windows[i]
        t = int(t)
        keep = np.zeros(max(self.T - t, 0), dtype=bool)
        for t0, s2, L in sl.windows:
            a, b = max(t0, t), min(s2 + L, self.T)
            if b > a:
                keep[a - t:b - t] = True
        sl.need[t:] = keep
        self.stats["windows_dropped"] += 1
        return True

    def absorb(self, pairs) -> list[tuple]:
        """Take the results of the layer's purchases from `book.begin`'s (key, result) pairs (other
        keys are ignored). A refused purchase (engine refusal or pre-check drop) leaves the slot
        without that lease; it is retried at the next needed slot (§7.2 step 7). Returns the refused
        purchases as (slot key, site, slot of purchase, kind, reason)."""
        refused = []
        for key, r in pairs:
            if not (isinstance(key, tuple) and len(key) == 5 and key[0] == BOOK_KEY and key[1] == self.tag):
                continue
            _, _, skey, kind, t_buy = key
            sl = self.slots[skey]
            if r.ok:
                sl.held_before = True
                if kind == "lease":
                    sl.lease, sl.buying = int(r.lease_id), False
                    sl.move_from = None
                else:
                    sl.next_lease = int(r.lease_id)
                continue
            self.stats["refused"][r.reason] = self.stats["refused"].get(r.reason, 0) + 1
            refused.append((skey, int(r.action.site), int(t_buy), kind, r.reason))
            if kind == "lease":
                sl.lease = sl.lease_site = None
                sl.buying = False
                if sl.move_from is not None:            # a marking move failed: keep the old lease
                    lid, site, noticed = sl.move_from
                    sl.retiring = [x for x in sl.retiring if x[0] != lid]
                    sl.lease, sl.lease_site, sl.noticed = lid, site, noticed
                    sl.move_from = None
            else:
                sl.next_lease = sl.next_site = None
                sl.next_noticed = False
                sl.next_notice = None
        return refused

    # ------------------------------------------------------------ actions
    def _stage_buy(self, sl: LogicalSlot, site: int, contract: int, t: int, kind: str, tag: str,
                   obs: SlowObs) -> None:
        self.book.buy((BOOK_KEY, self.tag, sl.key, kind, t), Buy(int(site), int(contract), sl.j, 1, tag=tag))
        sl.pool = tuple(self.rr.pool(sl, obs, t))
        self.site_rule.on_buy(sl, site, t)

    def _release(self, sl: LogicalSlot, lid: int, cause: str) -> None:
        self.book.release(lid)
        self.stats["releases"] += 1
        self.stats["releases_by_cause"][cause] += 1
        sl.lease = sl.lease_site = None
        sl.last_end = "released"
        sl.noticed = sl.ptr_moved = False
        if sl.pending is not None:
            sl.pending = sl.pending_for = None
            self.stats["prewarm"]["dropped"] += 1
        sl.idle = 0

    def move(self, sl: LogicalSlot, site: int, obs: SlowObs, t: int, release: str = "warm") -> None:
        """Marking move (§8.3 MK1, MK2): buy a fresh lease at `site` now; the current lease is
        released at t ('now') or at the first slow slot in which the new replica is warm ('warm',
        timing.warm_fast), so that the replacement loads while the old lease still serves."""
        old, old_site = sl.lease, sl.lease_site
        if old is None or old not in obs.leases:
            raise PolicyError(f"move of slot {sl.key}: no alive lease")
        self._stage_buy(sl, site, sl.k, t, "lease", "move", obs)
        self.stats["purchases"]["move"] += 1
        f_w = warm_fast(t * self.slow, int(self.lam_ms[sl.j, site]), self.fast)
        t_w = -(-f_w // self.phi)
        if release == "now" or t_w <= t:
            self.book.release(old)
            self.stats["releases"] += 1
            self.stats["releases_by_cause"]["move"] += 1
            sl.move_from = None
            sl.last_end = "released"
        else:
            sl.retiring.append((old, t_w))
            sl.move_from = (old, old_site, sl.noticed)
        if sl.pending is not None:
            sl.pending = sl.pending_for = None
            self.stats["prewarm"]["dropped"] += 1
        sl.lease, sl.buying, sl.lease_site, sl.ptr = None, True, int(site), int(site)
        sl.noticed = sl.ptr_moved = False
        sl.buy_cause = "move"
        sl.idle = 0

    def _set_ptr(self, sl: LogicalSlot, site: int) -> None:
        if int(site) != sl.ptr:
            self.stats["rotations"] += 1
        sl.ptr = int(site)

    def _decide(self, sl: LogicalSlot, obs: SlowObs, t: int, nt: Notice) -> None:
        """Step 1's handler path for a notice on the slot's current lease: the replacement site from
        the site rule (x3) or ptr, the handler's decision; a pre-warm moves ptr to that site."""
        lv = obs.leases.get(sl.lease)
        l_rep = self.site_rule.next_site(sl, obs, t) if self.x3 else sl.ptr
        d = self.handler.decide(obs, nt, lv, sl.j, int(l_rep), sl.k)
        self.stats["decisions"][d.reason] = self.stats["decisions"].get(d.reason, 0) + 1
        if d.kind == "prewarm":
            sl.pending, sl.pending_for = d, sl.lease
            self._set_ptr(sl, l_rep)
            sl.ptr_moved = True
            self.stats["prewarm"]["decided"] += 1

    def n_idle(self, l: int, j: int, k: int) -> float:
        """X2 timer threshold ceil((beta~_{jlk} / (g_j a_{lk})) 60 / Δs) slots (inf if g a <= 0)."""
        key = (l, j, k)
        v = self._n_idle.get(key)
        if v is None:
            ga = float(self.g[j]) * float(self.view.price[l, k])
            bt = float(self.view.beta_tilde_usd[j, l, k])
            v = float(math.ceil(bt / ga * 60.0 / self.slow)) if ga > 0 else math.inf
            self._n_idle[key] = v
        return v

    # ------------------------------------------------------------ one slot
    def step(self, obs: SlowObs) -> None:
        """§7.2 for every logical slot in key order (creation order); stages actions in the book."""
        t = obs.t
        self.site_rule.on_slot(obs)
        notices = {nt.lease_id: nt for nt in obs.notices}
        for sl in self.slots.values():
            if (sl.lease is None and not sl.buying and sl.next_lease is None and sl.pending is None
                    and not sl.retiring and not sl.need[t]):
                sl.new_window = False
                continue
            self._step_slot(sl, obs, t, notices)

    def _step_slot(self, sl: LogicalSlot, obs: SlowObs, t: int, notices: dict) -> None:
        # retiring leases of marking moves: released at their slot, forgotten once dead
        if sl.retiring:
            keep = []
            for lid, t_w in sl.retiring:
                if lid not in obs.leases:
                    continue
                if t >= t_w:
                    self.book.release(lid)
                    self.stats["releases"] += 1
                    self.stats["retired"] += 1
                    self.stats["releases_by_cause"]["retired"] += 1
                else:
                    keep.append((lid, t_w))
            sl.retiring = keep
            if sl.move_from is not None and sl.move_from[0] not in {x[0] for x in keep}:
                sl.move_from = None

        # 1. notices (X4)
        if sl.holds() and sl.lease in notices:
            nt = notices[sl.lease]
            sl.noticed = True
            self.stats["notices"] += 1
            if self.handler is not None:
                if sl.lease in obs.leases:
                    for a in self.handler.drain_actions(obs, nt):
                        self.book.other(a)
                self._decide(sl, obs, t, nt)
        if sl.next_lease is not None and sl.next_lease >= 0 and sl.next_lease in notices:
            # the pre-warmed replacement is announced before it takes over: the notice is kept and
            # reaches the handler at the takeover (step 2), when the replacement is the slot's lease
            sl.next_noticed = True
            sl.next_notice = notices[sl.next_lease]
            self.stats["notices"] += 1
            if self.handler is not None and sl.next_lease in obs.leases:
                for a in self.handler.drain_actions(obs, sl.next_notice):
                    self.book.other(a)

        # 2. deaths
        if sl.next_lease is not None and sl.next_lease >= 0 and sl.next_lease not in obs.leases:
            sl.next_lease = sl.next_site = None     # the pre-warmed replacement died first
            sl.next_noticed = False
            sl.next_notice = None
            self.stats["prewarm"]["next_lost"] += 1
        if sl.holds() and sl.lease not in obs.leases:
            cause = self.book.cause(sl.lease)
            revoked = sl.noticed or cause in ("reclaim", "violation")
            if revoked:
                self.stats["revoked_deaths"] += 1
                if self.x3 and not sl.ptr_moved:
                    self._set_ptr(sl, self.site_rule.next_site(sl, obs, t))
            else:
                self.stats["other_deaths"] += 1
            if sl.pending is not None and sl.pending.t_commit > t:
                sl.pending = sl.pending_for = None      # died before the commit: step 4 buys now
                self.stats["prewarm"]["dropped"] += 1
            sl.lease = sl.lease_site = None
            sl.last_end = "revoked" if revoked else "ended"
            sl.noticed = sl.ptr_moved = False
            sl.idle = 0
        if sl.lease is None and not sl.buying and sl.next_lease is not None and sl.next_lease >= 0:
            sl.lease, sl.lease_site, sl.noticed = sl.next_lease, sl.next_site, sl.next_noticed
            nt = sl.next_notice
            sl.next_lease = sl.next_site = None
            sl.next_noticed = False
            sl.next_notice = None
            if nt is not None and self.handler is not None:
                # its notice came before or at the takeover: step 1's handler path now, as a notice
                # seen at t (the remaining notice period [t, E]; a commit slot before t is impossible)
                self._decide(sl, obs, t, dataclasses.replace(nt, r_slot=max(int(nt.r_slot), t)))

        alive = sl.holds() and sl.lease in obs.leases
        if sl.new_window:
            sl.new_window = False
            if alive and self.x1:
                self.stats["renewals"] += 1
            elif alive and obs.leases[sl.lease].start_slot < t:
                self._release(sl, sl.lease, "x1_off")     # x1 off: a fresh lease for the new window
                alive = False

        # 3. pre-warm commit
        if sl.pending is not None and sl.pending.t_commit == t:
            d = sl.pending
            lv = obs.leases.get(sl.pending_for) if sl.pending_for is not None else None
            sl.pending = sl.pending_for = None
            if sl.need[t] and sl.next_lease is None and self.handler.confirm(obs, d, lv):
                self._stage_buy(sl, sl.ptr, d.contract, t, "next", "prewarm", obs)
                sl.next_lease, sl.next_site = PENDING, sl.ptr
                self.stats["purchases"]["prewarm"] += 1
                self.stats["prewarm"]["committed"] += 1
            else:
                self.stats["prewarm"]["cancelled"] += 1

        # 4. purchases (first purchase, cold replacement, re-buy after a release)
        if sl.need[t] and sl.lease is None and not sl.buying and sl.next_lease is None and sl.pending is None:
            if not sl.held_before:
                cause = "first"
            elif sl.last_end == "revoked":
                cause = "cold"
            else:
                cause = "rebuy"
            site = int(self.site_rule.place(sl, obs, t, cause))
            sl.ptr = site
            self._stage_buy(sl, site, sl.k, t, "lease", "x1", obs)
            sl.buying, sl.lease_site, sl.buy_cause = True, site, cause
            self.stats["purchases"][cause] += 1
            return

        # 5. renewal (X1) and 6. release (X2)
        if not alive:
            sl.idle = 0
            return
        lv = obs.leases[sl.lease]
        sl.start_slot, sl.prepaid_end_min, sl.lease_site = lv.start_slot, lv.prepaid_end_min, lv.site
        if sl.need[t]:
            sl.idle = 0
            return
        past_term = t * self.slow >= lv.prepaid_end_min
        if self.x2 == "reference":
            if t >= lv.start_slot + sl.L and past_term:
                self._release(sl, lv.id, "x2_reference")
            return
        att = attributed_load(obs, self.view, lv)
        idle_now = att <= IDLE_LOAD
        if self.profit_idle and not idle_now:      # knob F under the timer
            idle_now = att * float(self.view.llms[sl.j].q_usd_per_h) < \
                float(self.g[sl.j]) * float(self.view.price[lv.site, lv.contract])
        if idle_now:
            sl.idle += 1
        else:
            sl.idle = 0
        if sl.idle >= self.n_idle(lv.site, sl.j, lv.contract) and past_term:
            self._release(sl, lv.id, "x2_timer")

    # ------------------------------------------------------------ report
    def report(self) -> dict:
        st = self.stats
        return {"tag": self.tag, "x1": self.x1, "x2": self.x2, "x3": self.x3, "slots": len(self.slots),
                "windows": st["windows"], "windows_dropped": st["windows_dropped"], "renewals": st["renewals"],
                "purchases": dict(st["purchases"]), "purchases_total": sum(st["purchases"].values()),
                "rotations": st["rotations"], "releases": st["releases"], "retired": st["retired"],
                "releases_by_cause": dict(st["releases_by_cause"]), "profit_idle": self.profit_idle,
                "refused": dict(st["refused"]), "notices": st["notices"],
                "revoked_deaths": st["revoked_deaths"], "other_deaths": st["other_deaths"],
                "decisions": dict(st["decisions"]), "prewarm": dict(st["prewarm"]),
                "site_rule": self.site_rule.report()}


__all__ = ["PENDING", "LogicalSlot", "SiteRule", "RRSiteRule", "ExecutionLayer"]
