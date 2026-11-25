"""Reclaim handler (design/sim_spec_ms2.md §10; design §3.4).

At a notice (r, E) on an own lease L at site l, contract k, LLM j, `ReclaimHandler.decide` chooses
between a pre-warm of the replacement, bought at the latest slow slot t_c at which it is warm in the
first fast slot in which L is dead (timing.latest_prewarm_slot), and a cold replacement after the
death (the execution layer's purchase, §7.2 step 4). The reaction is test (b) by default: the
C2-SW formula at the run's calibration (c2rule.c2_thresholds, M32), with the cheapest reachable
protected contract as the switch-cost convention; or a fixed reaction; or test (a) with a predicted
share p_hat of the stranded clients' active units (M33). At t_c the execution layer calls `confirm`,
which re-checks the decision with the observations of t_c. Step 1 (drain) is off by default (M31);
steps 2 and 3 need no action in the fluid engine (the residual load is used by test (a) only); step
5 (release) is none, since the lease dies at E.

Status: PROVEN only for one site under (C')/(C) with switch cost beta (C2-L2(ii), C2-T4, C2-Cor5);
at the default switch cost the reaction is CONJECTURE (Q11, Q17); multi-site use, test (a) and a
revocable replacement elsewhere are heuristics (design Table 3.4).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Literal, Optional, Sequence

import numpy as np

from ..instance import active_units
from ..timing import latest_prewarm_slot
from ..types import Drain, LeaseView, Notice, PublicView, SlowObs
from . import c2rule
from .common import EPS_DEMAND, PolicyError, attributed_load, lam_ms, slot_max_demand

REACTIONS = ("c2sw", "cold", "prewarm_if_feasible", "test_a")
EPS_LOAD = 1e-9          # residual load d_res must exceed this for test (a) to pre-warm


@dataclass(frozen=True)
class Decision:
    """Reaction to one notice: 'prewarm' (Buy at t_commit at `site` with `contract`) or 'cold'."""
    kind: Literal["cold", "prewarm"]
    t_commit: Optional[int]        # slow slot of the pre-warm Buy
    site: int; contract: int
    reason: str                    # 'infeasible', 'alpha>=1', 'no-protected', 'c2sw-cold', 'c2sw-warm',
                                   # 'forced', 'cold', 'test-a', 'test-a-cold', 'dead', 'beta~=0'
    clients: tuple[int, ...] = ()  # the stranded clients at the notice (§7.3), checked at t_commit


class PredictedShare:
    """p_hat(clients, slot) of test (a) (§10 step 4, M33) from a predicted demand pred_demand
    (n, T_fast): with n^_c the active units of the predicted slot maximum of `slot` and n_c the
    client's active units at the slot of the last observation, p_hat = sum_c min(n^_c, n_c) /
    sum_c n_c over the clients (0 if the denominator is 0, and n^_c = 0 for a slot outside the
    horizon). The handler calls `observe(obs)` before each evaluation, so that n_c is the count of
    the slot at which it decides (the notice slot) or confirms (t_c)."""

    def __init__(self, view: PublicView, pred_demand: np.ndarray):
        g = view.grid
        D = np.asarray(pred_demand, dtype=np.float64)
        n = len(view.client_llm)
        if D.shape != (n, g.T_fast):
            raise PolicyError(f"PredictedShare: pred_demand has shape {D.shape}, expected {(n, g.T_fast)}")
        self.u = int(view.units_per_replica)
        self.T = int(g.T_slow)
        self.Dmax = D.reshape(n, g.T_slow, g.phi).max(axis=2)       # (n, T_slow) predicted slot maxima
        self.n_now = np.zeros(n, dtype=np.int64)

    def observe(self, obs: SlowObs) -> None:
        self.n_now = active_units(slot_max_demand(obs), self.u)

    def __call__(self, clients: Sequence[int], slot: int) -> float:
        cl = np.asarray(list(clients), dtype=np.int64)
        if cl.size == 0:
            return 0.0
        den = float(self.n_now[cl].sum())
        if den <= 0:
            return 0.0
        if 0 <= int(slot) < self.T:
            n_hat = active_units(self.Dmax[cl, int(slot)], self.u)
        else:
            n_hat = np.zeros(cl.size, dtype=np.int64)
        return float(np.minimum(n_hat, self.n_now[cl]).sum()) / den


class ReclaimHandler:
    """Design §3.4 for one announced lease (§10). reaction: 'c2sw' (test (b), default), 'cold',
    'prewarm_if_feasible', 'test_a' (needs p_hat); switch: 'c2sw' or 'beta' (the switch cost of the
    C2-SW reaction, §9.2); drain: step 1 (off, M31)."""

    def __init__(self, view: PublicView, *, reaction: str = "c2sw", switch: str = "c2sw", drain: bool = False,
                 p_hat: Optional[Callable[[Sequence[int], int], float]] = None):
        if reaction not in REACTIONS:
            raise PolicyError(f"ReclaimHandler: reaction must be one of {REACTIONS}, got {reaction!r}")
        if switch not in c2rule.SWITCHES:
            raise PolicyError(f"ReclaimHandler: switch must be one of {c2rule.SWITCHES}, got {switch!r}")
        if not isinstance(drain, (bool, np.bool_)):
            raise PolicyError(f"ReclaimHandler: drain must be a bool, got {drain!r}")
        if reaction == "test_a" and p_hat is None:
            raise PolicyError("ReclaimHandler: reaction 'test_a' needs p_hat (from the driver input pred_demand)")
        self.view = view
        self.reaction, self.switch, self.drain, self.p_hat = reaction, switch, bool(drain), p_hat
        self._lam_ms = lam_ms(view)
        self._delta = np.asarray(view.client_delta_usd_per_h, dtype=np.float64)
        self._cl_llm = np.asarray(view.client_llm, dtype=np.int64)
        self._meta: dict[Decision, tuple[int, int]] = {}    # pre-warm decision -> (E, j), for confirm
        self.stats = {"decisions": {}, "prewarm": 0, "cold": 0, "confirmed": 0, "cancelled": 0, "drains": 0}

    # -------------------------------------------------------- helpers
    def stranded(self, obs: SlowObs, j: int, l: int) -> tuple[int, ...]:
        """S (§7.3, §10): clients of LLM j with delta_cl < inf and D_c(t) > EPS_DEMAND; if none, all
        clients of j with delta_cl < inf."""
        reach = [int(c) for c in np.flatnonzero(self._cl_llm == j) if np.isfinite(self._delta[c, l])]
        D = slot_max_demand(obs)
        on = [c for c in reach if D[c] > EPS_DEMAND]
        return tuple(on if on else reach)

    def _deadline(self, notice: Notice, j: int) -> int:
        """E, or with drain the drain start max(r Δs, E - ceil(T_dr_j / 60)) (step 1)."""
        E = int(notice.death_min)
        if not self.drain:
            return E
        return max(int(notice.r_slot) * self.view.grid.slow_min,
                   E - math.ceil(float(self.view.llms[j].T_dr_s) / 60.0))

    def residual(self, obs: SlowObs, lease: Optional[LeaseView], j: int, clients: Sequence[int]) -> float:
        """d_res = max(0, carried - spare) of step 3: carried = attributed_load of the announced lease;
        spare = sum over own warm admitting replicas of j at other sites, on unannounced leases, with
        delta_cl'' < q_j for some stranded client, of their admission minus their attributed load."""
        if lease is None or lease.id not in obs.leases:
            return 0.0
        carried = attributed_load(obs, self.view, lease)
        q = float(self.view.llms[j].q_usd_per_h)
        den: dict[int, float] = {}
        cand = []
        for rv in obs.replicas.values():
            L = obs.leases.get(rv.lease_id)
            if rv.state != "warm" or L is None or rv.llm != j:
                continue
            den[L.site] = den.get(L.site, 0.0) + float(rv.admission)
            if (L.site != lease.site and L.announce_slot is None and rv.admission > 0
                    and any(self._delta[c, L.site] < q for c in clients)):
                cand.append((L.site, float(rv.admission)))
        spare = 0.0
        for l2, adm in cand:
            d = den.get(l2, 0.0)
            att = float(obs.served_prev[j, l2]) * adm / d if d > 0 else 0.0
            spare += max(0.0, adm - att)
        return max(0.0, carried - spare)

    def _test_a(self, obs: SlowObs, lease: Optional[LeaseView], j: int, clients: Sequence[int], E: int,
                rep_site: int, rep_contract: int) -> bool:
        """Test (a) in engine units (§10 step 4, M33): pre-warm iff d_res > 1e-9 and
        p [(mu_fb + pi (W_f - H_k)^+) d_res + q_j (lam'/3600) d_res] > (1 - p) [beta_jl' + g a_l'k' P_k' / 60]."""
        if lease is None or lease.id not in obs.leases:
            return False
        v = self.view
        d_res = self.residual(obs, lease, j, clients)
        if not d_res > EPS_LOAD:
            return False
        obs_hook = getattr(self.p_hat, "observe", None)
        if obs_hook is not None:
            obs_hook(obs)
        p = float(self.p_hat(tuple(clients), int(E) // v.grid.slow_min))
        st = v.stranding
        Hk = int(v.contracts[lease.contract].H_min)
        mu = float(st.mu_fb_usd[j]) + float(st.pi_usd_per_min[j]) * max(float(st.W_f_min) - Hk, 0.0)
        q = float(v.llms[j].q_usd_per_h)
        lam = float(v.lam_s[j, rep_site])
        gain = p * (mu * d_res + q * (lam / 3600.0) * d_res)
        waste = (1.0 - p) * (float(v.beta_usd[j, rep_site]) + v.llms[j].g * float(v.price[rep_site, rep_contract])
                             * int(v.contracts[rep_contract].prepaid_min) / 60.0)
        return gain > waste

    def _record(self, d: Decision) -> Decision:
        s = self.stats
        s["decisions"][d.reason] = s["decisions"].get(d.reason, 0) + 1
        s[d.kind] += 1
        return d

    # -------------------------------------------------------- interface
    def decide(self, obs: SlowObs, notice: Notice, lease: Optional[LeaseView], j: int,
               rep_site: int, rep_contract: int) -> Decision:
        """Reaction to `notice` on `lease` (LLM j) with the replacement (rep_site, rep_contract) of the
        caller's site rule (X3 or MK2). A lease absent from obs.leases (trap T1: H_k < Δf) is dead:
        cold with reason 'dead'."""
        v = self.view
        if lease is None or lease.id not in obs.leases:
            return self._record(Decision("cold", None, int(rep_site), int(rep_contract), "dead", ()))
        l, k = int(lease.site), int(lease.contract)
        S = self.stranded(obs, j, l)
        E = int(notice.death_min)
        t_c = latest_prewarm_slot(int(notice.r_slot), self._deadline(notice, j), int(self._lam_ms[j, rep_site]),
                                  v.grid)

        def out(kind: str, reason: str) -> Decision:
            d = Decision(kind, t_c if kind == "prewarm" else None, int(rep_site), int(rep_contract), reason, S)
            if kind == "prewarm":
                self._meta[d] = (E, int(j))
            return self._record(d)

        if t_c is None:
            return out("cold", "infeasible")
        if self.reaction == "cold":
            return out("cold", "cold")
        if self.reaction == "prewarm_if_feasible":
            return out("prewarm", "forced")
        if self.reaction == "test_a":
            ok = self._test_a(obs, lease, j, S, E, int(rep_site), int(rep_contract))
            return out("prewarm", "test-a") if ok else out("cold", "test-a-cold")
        # test (b): the C2-SW reaction at the run's calibration (M32)
        if c2rule.alpha_of(v, j, l, k) >= 1:
            return out("cold", "alpha>=1")
        if not float(v.beta_tilde_usd[j, l, k]) > 0:
            return out("cold", "beta~=0")         # C2 units undefined; a free load makes cold and pre-warm alike
        prot = c2rule.cheapest_protected(v, j, S)
        if prot is None:
            return out("cold", "no-protected")
        units = c2rule.c2_units(v, j, l, k, l_prot=prot[0], k_prot=prot[1], rep_site=int(rep_site),
                                switch=self.switch)
        th = c2rule.c2_thresholds(units.alpha, units.ap, units.mu, units.lam, 1.0,
                                  None if self.switch == "beta" else units.bw)
        return out("prewarm", "c2sw-warm") if th.react == "warm" else out("cold", "c2sw-cold")

    def confirm(self, obs: SlowObs, d: Decision, lease: Optional[LeaseView]) -> bool:
        """At t_commit: for test (b) and the fixed reactions, some client of d.clients has demand on
        (D_c > EPS_DEMAND); for test (a), the test re-evaluated with the observations of t_commit."""
        if d.kind != "prewarm":
            return False
        if self.reaction == "test_a":
            meta = self._meta.get(d)
            if meta is None or lease is None:
                ok = False
            else:
                E = lease.death_min if lease.death_min is not None else meta[0]
                ok = self._test_a(obs, lease, meta[1], d.clients, int(E), d.site, d.contract)
        else:
            D = slot_max_demand(obs)
            ok = any(D[c] > EPS_DEMAND for c in d.clients)
        self.stats["confirmed" if ok else "cancelled"] += 1
        return bool(ok)

    def drain_actions(self, obs: SlowObs, notice: Notice) -> list[Drain]:
        """Step 1 with drain=True: Drain(rid, max(r Δs, E - ceil(T_dr_j / 60))) for each replica of the
        announced lease in obs.replicas, only if the lease is in obs.leases (trap T1); else []."""
        if not self.drain:
            return []
        L = obs.leases.get(notice.lease_id)
        if L is None:
            return []
        start = int(notice.r_slot) * self.view.grid.slow_min
        out = []
        for rid in L.replicas:
            rv = obs.replicas.get(rid)
            if rv is None:
                continue
            out.append(Drain(int(rid), max(start, int(notice.death_min)
                                           - math.ceil(float(self.view.llms[rv.llm].T_dr_s) / 60.0))))
        self.stats["drains"] += len(out)
        return out

    def report(self) -> dict:
        """Decisions by reason, pre-warm and cold counts, confirmations and cancellations at t_c."""
        s = self.stats
        return {"reaction": self.reaction, "switch": self.switch, "drain": self.drain,
                "decisions": dict(s["decisions"]), "prewarm": s["prewarm"], "cold": s["cold"],
                "confirmed": s["confirmed"], "cancelled": s["cancelled"], "drains": s["drains"]}


__all__ = ["Decision", "ReclaimHandler", "PredictedShare", "REACTIONS"]
