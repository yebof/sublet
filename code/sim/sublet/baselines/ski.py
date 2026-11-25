"""BL2, per-borrower ski rental (design/sim_spec_ms2.md §15.4; a7_policy_sim.py "THRESH" and
"THRESH+KEEP"; C2-T1).

Run per borrower through drivers/siloed.py (registry runner 'siloed') on an instance built with
borrowers.merge = false. Per client c, replica layers v = 1, 2, ...: layer v is active in slot t iff
D_c(t) > v - 1 (active_units(D, 1); with kappa_infinite only layer 1). Per layer: run_v = consecutive
active slots ending at t (not reset by a reclaim, as a7), idle_v = consecutive inactive slots.
- Buy: the layer holds no lease and run_v Δs > s0 (strict), with l the best usable site (§15.1) and
  s0 = 60 beta~_{j l k*} / (q_j - g_j a_{l k*}) at that site (C2's s0); one replica Buy(l, k*(l), j, 1).
- Release: idle_v Δs > w with w = 0 (keep "none") or w = s0 at the lease's site (keep "s0"), rule BR.
- Reclaim: the layer's lease ends at its death; a still active layer has run_v > s0 and re-buys in
  the slot where the death is observed. Notices are ignored.

MS7 option (design/ms7/plan.md X1, C53; design/ms7/feasibility/causal.md F2): demand_lag (0; slots, as BL1's, in
QUIET_KEYS so that params() and the records at the default stay those of MS2-MS6): D_c(t) is read from
Baseline.demand_of, so with L >= 1 the layers' run and idle counters advance on the demand of slot t - L as revealed
then (zeros for t < L); BL2-lag of experiments/e7c_tags.py takes L = 1. Every sub-run of the siloed runner gets it
through the run spec's parameters.

MS7 option (design/ms7/plan.md X4, C54; design/ms7/feasibility/baselines.md §2 item 1, §3 B2), default the behaviour
above and hidden from params() while it holds its default (QUIET_KEYS):
- contract_rule ('kstar'): 'c2' buys A9.3's base contract kbar(l, j) (common.c2_base_contracts_cached) at every site,
  and the usable sites, the site scores and C2's s0 = 60 beta~_{j l kbar} / (q_j - g_j a_{l kbar}) are those of kbar
  (SiteTable.use_contracts and s0_min; BL2-c2, the contract-only transplant of P3's notice-to-buy rule).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..instance import active_units
from ..types import PublicView, SlowObs
from .common import Baseline, c2_base_contracts_cached


@dataclass(eq=False)
class Layer:
    """One replica layer v of a client: its lease, site and the run and idle counters (slow slots)."""
    lease: Optional[int] = None
    site: Optional[int] = None
    run: int = 0
    idle: int = 0


class SkiRental(Baseline):
    """BL2 (online-I1): ski rental per replica layer of each client of one borrower."""
    name = "bl2_ski"
    PARAMS = {"keep": "none", "defer_release": True, "demand_lag": 0, "contract_rule": "kstar"}
    QUIET_KEYS = ("demand_lag", "contract_rule")   # MS7 C53, C54: the records at the defaults stay those of MS2-MS6

    def _validate(self) -> None:
        self._choice("keep", ("none", "s0"))

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        if self._params["contract_rule"] == "c2":
            self.sites.use_contracts(c2_base_contracts_cached(view))
        self.layers: list[list[Layer]] = [[] for _ in range(self.n)]
        self.kinf = bool(view.kappa_infinite)
        self.buy_slots: list[tuple[int, int, int, int]] = []     # (t, client, layer v, site)

    def _keep_min(self, j: int, l: int) -> float:
        return 0.0 if self._params["keep"] == "none" else self.sites.s0_min(j, l)

    def act(self, obs: SlowObs) -> list:
        t = obs.t
        for (c, v), r in self._begin(obs):
            if r.ok:
                L = self.layers[c][v]
                L.lease, L.site = int(r.lease_id), int(r.action.site)
        for layers in self.layers:
            for L in layers:
                if L.lease is not None and L.lease not in obs.leases:
                    self._gone(L.lease, obs)
                    L.lease = L.site = None
        d = np.asarray(self.demand_of(obs), dtype=np.float64)          # obs.demand at demand_lag 0 (C53)
        D = d.max(axis=1) if d.shape[1] else np.zeros(self.n)
        nact = active_units(D, 1)
        if self.kinf:
            nact = np.minimum(nact, 1)
        Ds = self.slow_min
        for c in range(self.n):
            while len(self.layers[c]) < nact[c]:
                self.layers[c].append(Layer())
            for v, L in enumerate(self.layers[c]):
                if v < nact[c]:
                    L.run, L.idle = L.run + 1, 0
                else:
                    L.run, L.idle = 0, L.idle + 1
        # releases: idle_v Δs > w (rule BR)
        for c in range(self.n):
            j = int(self.sites.cl_llm[c])
            for L in self.layers[c]:
                if L.lease is None:
                    continue
                if L.idle * Ds > self._keep_min(j, L.site):
                    if self._try_release(obs, obs.leases[L.lease]):
                        L.lease = L.site = None
                else:
                    self._not_deferred(L.lease)
        # purchases: run_v Δs > s0 at the best usable site
        for c in range(self.n):
            j = int(self.sites.cl_llm[c])
            for v, L in enumerate(self.layers[c]):
                if v >= nact[c] or L.lease is not None:
                    continue
                l = self.sites.best_site(c, obs, self.book, self.unavail)
                if l is None:
                    break
                if L.run * Ds > self.sites.s0_min(j, l):
                    self._buy((c, v), l, j, f"bl2:{c}:{v + 1}")
                    self.buy_slots.append((t, c, v + 1, l))
        return self.book.assemble(obs, self.view)

    def report(self) -> dict:
        out = super().report()
        if hasattr(self, "layers"):
            out["buy_slots"] = [list(x) for x in self.buy_slots]
            out["n_layers"] = [len(x) for x in self.layers]
        return out


__all__ = ["SkiRental", "Layer"]
