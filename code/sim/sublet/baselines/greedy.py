"""BL1, greedy lease-when-idle (design/sim_spec_ms2.md §15.3; a7_policy_sim.py "GREEDY").

Per client c at slow slot t: target N_c(t) = ceil(D_c(t) - 1e-9) replicas (1[D_c(t) > 0] with
kappa_infinite), D_c(t) the slot maximum (demand_stat "max") or mean ("mean"); h_c = alive BL1 leases
bought for c (announced or not). If h_c < N_c: buy N_c - h_c single-replica leases, each
Buy(l, k*(l), j_c, 1, tag="bl1:c") at the best usable site (§15.1). If h_c > N_c: release h_c - N_c,
highest rent rate first, then latest start, with rule BR. No reaction to notices: after a death the
deficit appears and BL1 re-buys at the then-best site.

MS5b options (design/sublet_v2.md §3, §8.1; C38), defaults the behaviour above:
- backoff_cap (None): the generic site back-off of baselines/common.py; the purchases avoid backed-off sites
  (BL1-BO: backoff_cap 288).
- demand_lag (0): with L >= 1 the target of slot t is computed from the demand of slot t - L as revealed then
  (zeros for t < L), so BL1 acts on lagged demand (P5's boundary run). A subclass that reads obs.demand itself
  must read demand_of(obs) instead for the option to apply. MS7 (C53): demand_of is Baseline's (baselines/
  common.py), moved there unchanged so that BL2 and BL3 take the same option.
"""
from __future__ import annotations

import numpy as np

from ..algos.common import EPS_DEMAND
from ..types import PublicView, SlowObs
from .common import Baseline


class GreedyLease(Baseline):
    """BL1 (online-I1): lease whenever needed, release when not (rule BR)."""
    name = "bl1_greedy"
    PARAMS = {"defer_release": True, "demand_stat": "max", "site_order": "auto", "backoff_cap": None, "demand_lag": 0}
    QUIET_KEYS = ("backoff_cap", "demand_lag")

    def _validate(self) -> None:
        self._choice("demand_stat", ("max", "mean"))

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        self.held: list[list[int]] = [[] for _ in range(self.n)]    # lease ids per client, purchase order
        self.kinf = bool(view.kappa_infinite)

    def target(self, obs: SlowObs) -> np.ndarray:
        """(n,) N_c(t)."""
        d = np.asarray(self.demand_of(obs), dtype=np.float64)
        D = d.max(axis=1) if self._params["demand_stat"] == "max" else d.mean(axis=1)
        if self.kinf:
            return (D > EPS_DEMAND).astype(np.int64)
        return np.maximum(np.ceil(D - 1e-9), 0).astype(np.int64)

    def act(self, obs: SlowObs) -> list:
        for c, r in self._begin(obs):
            if r.ok:
                self.held[c].append(int(r.lease_id))
        for c in range(self.n):
            alive = []
            for lid in self.held[c]:
                if lid in obs.leases:
                    alive.append(lid)
                else:
                    self._gone(lid, obs)
            self.held[c] = alive
        N = self.target(obs)
        # releases: the surplus, highest rent rate first, then latest start (rule BR)
        for c in range(self.n):
            h = len(self.held[c])
            order = sorted(self.held[c], key=lambda lid: (-self.sites.rent_rate(obs.leases[lid]),
                                                           -obs.leases[lid].start_min, -lid))
            surplus = set(order[:max(0, h - int(N[c]))])
            for lid in order:
                if lid not in surplus:
                    self._not_deferred(lid)
                elif self._try_release(obs, obs.leases[lid]):
                    self.held[c].remove(lid)
        # purchases: the deficit, one lease per replica at the best usable site (not backed off, MS5b)
        exclude = self._excluded(obs.t)
        for c in range(self.n):
            j = int(self.sites.cl_llm[c])
            for _ in range(int(N[c]) - len(self.held[c])):
                l = self.sites.best_site(c, obs, self.book, exclude)
                if l is None:
                    break
                self._buy(c, l, j, f"bl1:{c}")
        return self.book.assemble(obs, self.view)


__all__ = ["GreedyLease"]
