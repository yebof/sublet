"""Marking under public reclaim information (design/sim_spec_ms2.md §8; design §3.2.4).

`MarkState` is the phase and mark bookkeeping of O1-D's marking algorithm for one pool and one
contract (§8.1): in a phase that starts at p, site l is marked at its first announcement
r >= p + tau (I2: SlowObs.site_announced); when the last site is marked at t1 the next phase
starts at ceil((t1 Δs + H) / Δs). It is shared by the family policy `family.Marking` (§8.2) and
by `MarkingSiteRule`, the site rule of the execution layer under I2 (§8.3, used by A4 and A6):

- groups: logical slots of one LLM j and contract k whose X3 pools at their first purchase are
  equal share one mark state, key (j, k, P) (M19); each slot draws its own sites;
- site rule (M20): marking iff I2 holds and 2 h_|P| + 1 < rho_P = max_{l in P} rho_{ljk}
  (calib.rho on the PD window L_k), else RR-renew (X3); fixed per group, since P, rho and I2 are;
- MK1: at a phase start each slot of the group with need[t0] draws a uniform site of P and buys a
  fresh lease there; its old lease is released once the new replica is warm;
- MK2: when a slot's current site is marked at t and unmarked sites remain, it draws a uniform
  unmarked site; hit (own lease announced at t): the site goes to the reclaim handler as the
  replacement (move_at="handler"); not hit: buy there at t and release the old lease once the new
  replica is warm; move_at="mark": buy at t and release the old lease at t in both cases;
- MK3: when the last site is marked, slots keep their leases until the next phase start;
- a death outside a move: the slot's current site if unmarked, else a uniform unmarked site,
  else the X3 next site.
Draws come from the policy's `marking` stream (§2.3), groups in creation order, slots in key
order, sites in pi order.

Status: O1-D (PROVEN, oblivious lender, I2) covers `family.Marking` on the T4/O1 family; the
per-logical-slot rule of A4 and A6 is a heuristic (several replicas per pool, contracts, loads).
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from .. import calib
from ..types import PublicView, SlowObs
from .common import PolicyError, pd_window_slots, treated_as_protected
from .execution import LogicalSlot, SiteRule


def harmonic(n: int) -> float:
    """h_n = sum_{i=1}^n 1/i."""
    return sum(1.0 / i for i in range(1, int(n) + 1))


class MarkState:
    """Phases and marks of one pool P (sites in pi order) and one contract (tau, H) (§8.1)."""

    def __init__(self, sites: Sequence[int], tau_slots: int, H_min: int, slow_min: int):
        self.sites = tuple(int(l) for l in sites)
        if not self.sites:
            raise PolicyError("MarkState needs a non-empty pool")
        self.tau = int(tau_slots)
        if self.tau < 1:
            raise PolicyError(f"MarkState: tau must be >= 1 slot, got {tau_slots}")
        self.H_min, self.slow_min = int(H_min), int(slow_min)
        self.p: Optional[int] = None                 # start slot of the current or last phase
        self.mark: dict[int, Optional[int]] = {l: None for l in self.sites}
        self.running = False
        self.next_start: Optional[int] = None        # next phase start once the phase has ended
        self.phases: list[list] = []                 # [p, t1 or None] per phase started

    def start(self, t: int) -> None:
        """Start a phase at slot t: every site unmarked."""
        self.p, self.running, self.next_start = int(t), True, None
        self.mark = {l: None for l in self.sites}
        self.phases.append([int(t), None])

    def unmarked(self) -> list[int]:
        """The unmarked sites of P in pi order (all of them if no phase is running)."""
        return [l for l in self.sites if self.mark[l] is None]

    def update(self, t: int, announced) -> tuple[list[int], list[int]]:
        """Marks of slot t (announced: (m,) bool, t in R_l; None reads as no announcement). If the
        phase runs and t >= p + tau, the unmarked sites with announced[l] are marked at t (newly, in
        pi order); if then every site is marked, the phase ends at t1 = t and the next phase starts
        at ceil((t1 Δs + H) / Δs). Returns (newly, unmarked)."""
        if not self.running or t < self.p + self.tau or announced is None:
            return [], self.unmarked()
        newly = [l for l in self.sites if self.mark[l] is None and bool(announced[l])]
        for l in newly:
            self.mark[l] = int(t)
        unm = self.unmarked()
        if not unm:
            self.running = False
            self.phases[-1][1] = int(t)
            self.next_start = -(-(int(t) * self.slow_min + self.H_min) // self.slow_min)
        return newly, unm

    @classmethod
    def run_phases(cls, announced: np.ndarray, tau_slots: int, H_min: int, slow_min: int,
                   sites: Optional[Sequence[int]] = None) -> list[tuple[int, Optional[int]]]:
        """Phases (p, t1 or None) of the state machine driven by a full (m, T) announcement mask,
        phase 0 at slot 0: the sequence of fam.marking_phases (test_mark_state_phases)."""
        A = np.asarray(announced, dtype=bool)
        st = cls(range(A.shape[0]) if sites is None else sites, tau_slots, H_min, slow_min)
        st.start(0)
        for t in range(A.shape[1]):
            if not st.running and st.next_start == t:
                st.start(t)
            elif st.running:
                st.update(t, A[:, t])
                if not st.running and st.next_start == t:
                    st.start(t)
        return [(p, t1) for p, t1 in st.phases]


class _Group:
    """One mark group (j, k, P) of §8.3."""
    __slots__ = ("key", "mode", "state", "slots", "rho")

    def __init__(self, key, mode, state, rho):
        self.key, self.mode, self.state, self.rho = key, mode, state, rho
        self.slots: list[tuple] = []


class MarkingSiteRule(SiteRule):
    """Site rule of the execution layer under I2 (§8.3): marking per mark group, RR-renew (the
    layer's RRSiteRule) where the site rule of M20 selects it. `rng` is the policy's `marking`
    stream. mode: 'auto' (M20), 'rr' or 'marking' (forced); move_at: 'handler' or 'mark'."""

    def __init__(self, view: PublicView, rng: np.random.Generator, *, mode: str = "auto",
                 move_at: str = "handler", rebuy_at_phase_start: bool = True,
                 protected_window: Optional[int] = None):
        if mode not in ("auto", "rr", "marking"):
            raise PolicyError(f"site_rule must be 'auto', 'rr' or 'marking', got {mode!r}")
        if move_at not in ("handler", "mark"):
            raise PolicyError(f"move_at must be 'handler' or 'mark', got {move_at!r}")
        self.view, self.rng, self.mode = view, rng, mode
        self.move_at, self.rebuy = move_at, bool(rebuy_at_phase_start)
        self.protected_window = protected_window
        self.i2 = view.information == "I2"
        self.groups: dict[tuple, _Group] = {}
        self.planned: dict[tuple, int] = {}        # slot key -> replacement site drawn for it
        self.stats = {"phases": 0, "phases_done": 0, "mk1_moves": 0, "mk1_places": 0, "mk2_moves": 0,
                      "mk2_hits": 0, "mk2_places": 0, "joins_drawn": 0, "death_draws": 0, "draws": 0}

    def bind(self, layer) -> None:
        super().bind(layer)
        self.rr = layer.rr

    # ------------------------------------------------------------ groups
    def rho(self, j: int, l: int, k: int) -> float:
        """rho_{ljk} = calib.rho(beta~, g_j, a_lk, L_k Δs) on the PD window L_k (§8.3, P2)."""
        v = self.view
        L = pd_window_slots(v, k, self.protected_window)
        return float(calib.rho(float(v.beta_tilde_usd[j, l, k]), v.llms[j].g, float(v.price[l, k]),
                               L * v.grid.slow_min))

    def _group_mode(self, j: int, k: int, P: tuple) -> tuple[str, float]:
        rho_P = max(self.rho(j, l, k) for l in P)
        if treated_as_protected(self.view, k):
            return "rr", rho_P                 # never announced within the horizon: nothing to mark
        if self.mode != "auto":
            return self.mode, rho_P
        return ("marking" if self.i2 and 2.0 * harmonic(len(P)) + 1.0 < rho_P else "rr"), rho_P

    def _group(self, sl: LogicalSlot, obs: SlowObs, t: int) -> tuple[_Group, bool]:
        """The slot's group, created from its X3 pool at its first purchase (new: True)."""
        if sl.group is not None:
            return self.groups[sl.group], False
        P = tuple(self.rr.pool(sl, obs, t))
        if not P:
            P = (int(sl.ptr),)
        gk = (sl.j, sl.k, P)
        g = self.groups.get(gk)
        new = g is None
        if new:
            mode, rho_P = self._group_mode(sl.j, sl.k, P)
            c = self.view.contracts[sl.k]
            tau = c.tau_slots if c.tau_slots is not None else self.view.grid.T_slow
            g = self.groups[gk] = _Group(gk, mode, MarkState(P, tau, c.H_min, self.view.grid.slow_min), rho_P)
        g.slots.append(sl.key)
        sl.group = gk
        return g, new

    def _draw(self, sites: list[int]) -> int:
        self.stats["draws"] += 1
        return int(sites[int(self.rng.integers(len(sites)))])

    # ------------------------------------------------------------ per slot
    def on_slot(self, obs: SlowObs) -> None:
        """Phase starts (MK1), marks and moves (MK2), MK3 for every marking group. Without I2 (a
        forced 'marking' rule on an I1 view) nothing is marked, so no phase ends: the rule never
        reads obs.site_announced then."""
        if not self.i2:
            return
        t = obs.t
        for g in self.groups.values():
            if g.mode != "marking":
                continue
            st = g.state
            if not st.running:
                if st.next_start is not None and st.next_start == t:
                    self._phase_start(g, obs, t)
                continue
            newly, unm = st.update(t, obs.site_announced)
            if not st.running:
                self.stats["phases_done"] += 1
                if st.next_start == t:
                    self._phase_start(g, obs, t)
            elif newly:
                self._mk2(g, obs, t, set(newly), unm)

    def _alive(self, sl: LogicalSlot, obs: SlowObs) -> bool:
        return sl.holds() and sl.lease in obs.leases

    def _phase_start(self, g: _Group, obs: SlowObs, t: int) -> None:
        """MK1: each slot of the group with need[t] draws a uniform site of P; one with an alive lease
        buys a fresh lease there (rebuy_at_phase_start), one without moves its pointer there. Slots
        in a pre-warm handover (pending decision or pre-warmed next lease) keep it and draw nothing.
        A slot that draws nothing keeps its planned replacement site (MK2's or a death draw) while it
        holds a lease, so a cold-noticed lease is still replaced there; one without a lease drops it
        (nothing to replace, and the site was drawn in an earlier phase), so that its next purchase
        is placed by `place` in the new phase."""
        g.state.start(t)
        self.stats["phases"] += 1
        layer = self.layer
        for key in g.slots:
            sl = layer.slots[key]
            alive = self._alive(sl, obs)
            if (not sl.need[t] or sl.pending is not None or sl.next_lease is not None
                    or (alive and not self.rebuy)):
                if not sl.holds():
                    self.planned.pop(key, None)
                continue
            self.planned.pop(key, None)
            site = self._draw(list(g.state.sites))
            if alive:
                layer.move(sl, site, obs, t, "warm")
                self.stats["mk1_moves"] += 1
            else:
                sl.ptr = site
                if sl.holds():                # its lease died at t: the death re-buys at the drawn site
                    self.planned[key] = site
                    sl.ptr_moved = True
                self.stats["mk1_places"] += 1

    def _mk2(self, g: _Group, obs: SlowObs, t: int, newly: set, unmarked: list[int]) -> None:
        if not unmarked:
            return
        layer = self.layer
        noticed = {nt.lease_id for nt in obs.notices}
        for key in g.slots:
            sl = layer.slots[key]
            cur = sl.lease_site if sl.lease is not None and sl.lease_site is not None else sl.ptr
            if cur not in newly or sl.pending is not None or sl.next_lease is not None:
                continue
            site = self._draw(unmarked)
            alive = self._alive(sl, obs)
            lv = obs.leases.get(sl.lease) if alive else None
            hit = sl.holds() and (sl.lease in noticed or (lv is not None and lv.announce_slot == t))
            if not alive or not sl.need[t]:
                # dead at t, or alive but not needed at t (no fresh lease without need, as MK1): the
                # pointer moves; a held lease's notice or death uses the drawn site
                sl.ptr = site
                if sl.holds():
                    self.planned[key] = site
                    sl.ptr_moved = True
                self.stats["mk2_places"] += 1
            elif self.move_at == "mark":
                layer.move(sl, site, obs, t, "now")
                self.stats["mk2_moves"] += 1
            elif hit:
                self.planned[key] = site      # the handler's replacement site (pre-warm or cold)
                self.stats["mk2_hits"] += 1
            else:
                layer.move(sl, site, obs, t, "warm")
                self.stats["mk2_moves"] += 1

    # ------------------------------------------------------------ SiteRule hooks
    def next_site(self, sl: LogicalSlot, obs: SlowObs, t: int) -> int:
        """Replacement site at a notice or a revocation death: MK2's planned site; else the current
        site if unmarked, else a uniform unmarked site, else the X3 next site. A drawn site is kept
        until the slot's next purchase, so the notice and the death agree."""
        g = self.groups.get(sl.group) if sl.group is not None else None
        if g is None or g.mode != "marking":
            return self.rr.next_site(sl, obs, t)
        if sl.key in self.planned:
            return self.planned[sl.key]
        st = g.state
        unm = st.unmarked() if st.running else []
        cur = sl.lease_site if sl.lease_site is not None else sl.ptr
        if cur in unm:
            site = int(cur)
        elif unm:
            site = self._draw(unm)
            self.stats["death_draws"] += 1
        else:
            site = int(self.rr.next_site(sl, obs, t))
        self.planned[sl.key] = site
        return site

    def place(self, sl: LogicalSlot, obs: SlowObs, t: int, cause: str) -> int:
        """Site of a purchase without a planned replacement: a slot's first purchase assigns its
        group (a new marking group starts a phase at t, MK1); in a running phase a first purchase or
        a re-buy goes to the slot's pointer if it is unmarked, else to a uniform unmarked site."""
        g, new = self._group(sl, obs, t)
        if g.mode != "marking":
            return int(sl.ptr)
        if new:
            self._phase_start(g, obs, t)
            return int(sl.ptr)
        if cause == "cold" or sl.key in self.planned:
            return int(self.planned.get(sl.key, sl.ptr))
        st = g.state
        if not st.running:
            return int(sl.ptr)
        unm = st.unmarked()
        if sl.ptr in unm:
            return int(sl.ptr)
        self.stats["joins_drawn"] += 1
        return self._draw(unm)

    def on_buy(self, sl: LogicalSlot, site: int, t: int) -> None:
        self.planned.pop(sl.key, None)

    def report(self) -> dict:
        modes: dict[str, int] = {}
        for g in self.groups.values():
            modes[g.mode] = modes.get(g.mode, 0) + 1
        return {"rule": "marking", "mode": self.mode, "move_at": self.move_at, "I2": self.i2,
                "groups": len(self.groups), "group_modes": modes,
                "groups_detail": [{"llm": g.key[0], "contract": g.key[1], "pool": list(g.key[2]),
                                   "mode": g.mode, "rho_P": g.rho, "phases": len(g.state.phases)}
                                  for g in self.groups.values()],
                **self.stats, "rr": self.rr.report()}


__all__ = ["harmonic", "MarkState", "MarkingSiteRule"]
