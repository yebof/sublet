"""Policies on the T4/O1 family (design/sim_spec_ms2.md §7.6, §8.2; design check 3).

The family (code/theory_checks/c3/o1/fam.py, c3/check_c4_lower.py::cm_instance): m synthetic
sites, one always-active client, one LLM, one contract (tau, H), from_core instances.

RRRenew  RR-renew (O1-B): the execution layer of §7 driven by a constant planner, one logical
         slot (0, 0, 0, 0) needed in every slot; x1 on, x2 'reference' (it never releases), x3 =
         not stay, zeta = inf, no skip rule, a cold handler, site order 'index'. On the family the
         engine run equals fam.run_renew(F, om, rr_choose(m)) (or stay_choose).
Marking  O1-D's randomized marking under I2: a standalone policy with `marking.MarkState` and no
         execution layer, handler or site rule, so that the generator serves exactly
         fam.run_marking's draws: one integers(m) per phase start and one integers(len(unmarked))
         per move, in time order. With policy_rng = default_rng(1000 + s) the run's cost and
         purchases equal fam.run_marking(F, om, default_rng(1000 + s)).

Status: O1-B (PROVEN, any lender) and O1-D (PROVEN, oblivious lender, I2) on the family; the
equalities with fam are CONJECTURE until test_family.py passes.
"""
from __future__ import annotations

import numpy as np

from ..policies.base import Policy
from ..types import Buy, PublicView, SlowObs
from .common import LeaseBook, PolicyError, policy_streams, resolve_params, site_order
from .execution import ExecutionLayer
from .handler import ReclaimHandler
from .marking import MarkState


def _check_family(view: PublicView, who: str) -> None:
    """Domain of the family policies: one client, one LLM, one contract, synthetic sites only."""
    if len(view.client_llm) != 1 or len(view.llms) != 1 or len(view.contracts) != 1:
        raise PolicyError(f"{who}: needs one client, one LLM and one contract (the T4/O1 family); "
                          f"got {len(view.client_llm)} clients, {len(view.llms)} LLMs, "
                          f"{len(view.contracts)} contracts")
    if any(s.kind != "synthetic" for s in view.sites):
        raise PolicyError(f"{who}: needs synthetic sites only (from_core of the family)")
    if view.contracts[0].protected:
        raise PolicyError(f"{who}: the family contract must be revocable")
    if any(0 not in s.menu for s in view.sites):
        raise PolicyError(f"{who}: every site must offer the contract")


class RRRenew(Policy):
    """RR-renew on the T4/O1 family (§7.6): hold one lease while it lives (renewal), re-buy at the
    next site in index order at a revocation death (stay=True: at site 0 again)."""
    name = "rr_renew"
    PARAMS = {"stay": False, "site_order": "index"}

    def __init__(self, **kw):
        self._p, _ = resolve_params(self.PARAMS, kw, self.name)
        if not isinstance(self._p["stay"], (bool, np.bool_)):
            raise PolicyError(f"{self.name}: stay must be a bool, got {self._p['stay']!r}")

    def params(self) -> dict:
        return dict(self._p)

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        _check_family(view, self.name)
        streams = policy_streams(rng)
        perm = site_order(view, streams["order"], self._p["site_order"])
        self.book = LeaseBook()
        self.handler = ReclaimHandler(view, reaction="cold")
        self.layer = ExecutionLayer(view, self.book, x1=True, x2="reference", x3=not self._p["stay"],
                                    zeta=float("inf"), skip_rule=False, handler=self.handler,
                                    site_perm=perm, tag="rr")
        T = view.grid.T_slow
        self.layer.open((0, 0, 0, 0), t0=0, s=0, L=T)    # the constant planner: needed in every slot

    def act(self, obs: SlowObs) -> list:
        self.layer.absorb(self.book.begin(obs))
        self.layer.step(obs)
        return self.book.assemble(obs, self.view)

    def report(self) -> dict:
        ex = self.layer.report()
        return {"purchases": ex["purchases_total"], "rotations": ex["rotations"], "exec": ex,
                "book": dict(self.book.stats)}


class Marking(Policy):
    """O1-D's marking on the T4/O1 family under I2 (§8.2). At slot t:
    1. at the next phase start (slot 0 at first): release the current lease if alive, buy at
       site = main.integers(m) (a fresh lease also when the draw returns the current site, M17),
       start a phase at p = t;
    2. else, in a running phase with t >= p + tau: update the marks from obs.site_announced; if every
       site is marked the next phase starts at t + H / Δs (with H = 0 step 1 runs now); else, if the
       current site was newly marked: release the current lease if alive and buy at
       unmarked[main.integers(len(unmarked))] (ascending index order), at the mark slot."""
    name = "marking"
    PARAMS = {"move_at": "mark", "rebuy_at_phase_start": True}

    def __init__(self, **kw):
        self._p, _ = resolve_params(self.PARAMS, kw, self.name)
        if self._p["move_at"] != "mark":
            raise PolicyError(f"{self.name}: move_at must be 'mark' (the family policy moves at the "
                              f"mark slot), got {self._p['move_at']!r}")

    def params(self) -> dict:
        return dict(self._p)

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        _check_family(view, self.name)
        if view.information != "I2":
            raise PolicyError(f"{self.name}: needs public reclaim information (I2), got {view.information}")
        self.main = policy_streams(rng)["main"]          # = rng: draws in fam.run_marking's order
        c, g = view.contracts[0], view.grid
        self.m = len(view.sites)
        self.state = MarkState(range(self.m), c.tau_slots, c.H_min, g.slow_min)
        self.next_start = 0
        self.book = LeaseBook()
        self.cur = None            # current lease id (None until the purchase resolves)
        self.site = None           # site of the current lease
        self.lost = False          # the last purchase was refused
        self.staged = False
        self.n_buys = self.n_moves = self.n_repairs = self.n_refused = 0

    def _buy(self, site: int) -> None:
        self.site = int(site)
        self.cur = None
        self.book.buy(("mk", self.site), Buy(self.site, 0, 0, 1, tag="marking"))
        self.staged, self.lost = True, False
        self.n_buys += 1

    def _release_current(self, obs: SlowObs) -> None:
        if self.cur is not None and self.cur in obs.leases:
            self.book.release(self.cur)
        self.cur = None

    def _phase_start(self, obs: SlowObs, t: int) -> None:
        site = int(self.main.integers(self.m))
        alive = self.cur is not None and self.cur in obs.leases
        if not self._p["rebuy_at_phase_start"] and alive and site == self.site:
            pass                                        # M17 alternative: keep the current lease
        else:
            self._release_current(obs)
            self._buy(site)
        self.state.start(t)
        self.next_start = None

    def act(self, obs: SlowObs) -> list:
        t = obs.t
        self.staged = False
        for _key, r in self.book.begin(obs):
            if r.ok:
                self.cur = int(r.lease_id)
            else:                                       # refusal (stress variants): retried below
                self.cur, self.lost = None, True
                self.n_refused += 1
        if self.next_start is not None and t == self.next_start:
            self._phase_start(obs, t)
        elif self.state.running and t >= self.state.p + self.state.tau:
            newly, unmarked = self.state.update(t, obs.site_announced)
            if not self.state.running:
                self.next_start = self.state.next_start
                if self.next_start == t:                # H = 0: the next phase starts now
                    self._phase_start(obs, t)
            elif self.site in newly:
                self._release_current(obs)
                self._buy(unmarked[int(self.main.integers(len(unmarked)))])
                self.n_moves += 1
        if not self.staged and (self.lost or (self.cur is not None and self.cur not in obs.leases)):
            # outside O1-D's coverage argument (a refused purchase, a violation death): re-buy at the
            # same site, without a draw, so that the draw order is unchanged
            self._buy(self.site)
            self.n_repairs += 1
        return self.book.assemble(obs, self.view)

    def report(self) -> dict:
        return {"purchases": self.n_buys, "moves": self.n_moves, "repairs": self.n_repairs,
                "refused": self.n_refused,
                "phases": [list(p) for p in self.state.phases], "book": dict(self.book.stats)}


__all__ = ["RRRenew", "Marking"]
