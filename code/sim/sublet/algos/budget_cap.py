"""Policy CAP: a naive spend cap around an inner policy (design/ms8/plan.md D2; design/ms8/scout_x6_budget_cap.md
§1). A labeled baseline for X6, not a policy with a guarantee: it is the rule a practitioner would write first, and it
exists to show which terms of Algorithm 1's test (guard.py, A8 and A8P) make a spend cap sound.

At every slow slot t the inner policy E acts on a private copy of the observation (guard.inner_obs, audit F2), and the
cap decides whether to pass E's list A_E(t) on. With FB(t) = sum_{u <= t} Q(u) the all-fallback cost through slot t
(Q(u) = guard.fallback_by_client(view, obs.demand).sum(), the engine's fallback charge with nothing served) and the
allowance X(t), the cap binds at t iff
  count 'paid'   ALG(t - 1) > FB(t - 1) + X(t)                                  (the cost so far only)
  count 'slot'   ALG(t - 1) + p_E(t) + rent_E(t) > FB(t - 1) + Q(t) + X(t)       (also the slot's purchases and rent)
with ALG(t - 1) = obs.cost_so_far and (p_E(t), rent_E(t)) = guard.slot_terms(view, obs, A_E(t)), the engine price of the
list's purchases and the rent bound of slot t of the leases held after it. Allowances (parameter X):
  'lb'          X(t) = B(t) = min{W_k(t), LB'(t)} of online_lb.OnlineLB, Sublet's allowance (Theorem 11's B), the same
                series as Sublet's on the same instance, since it depends only on the view and the revealed demand;
  a number      X(t) = X, a constant in USD (>= 0, finite);
  'rel:<eps>'   X(t) = eps FB(t - 1) (eps >= 0, finite).
When the cap binds (parameter on_bind):
  'stop'   the slot's Buys are dropped, with every action that names a lease or replica that obs does not hold (an
           object of a dropped Buy); the other actions (Releases on held leases) are executed, and the test is made
           again at every later slot (the cap resumes once the cost so far falls back under the line);
  'latch'  every held lease is released once (Release in lease-id order) and from then on the cap returns no action
           but a Release of any lease still held (none, since a Release always succeeds); the inner is not called again.
After a slot with dropped actions the inner receives the engine's results in its own indices, a dropped action as
ActionResult(index, action, ok=False, lease_id=None, replica_ids=(), reason='cap'), as ProjectedGuarded._inner_results
remaps them (guard.py, step 1 of the projection). With X = 1e18 (or any X the run never reaches) the cap never binds and
the run is the inner's alone, bit for bit (tests/test_budget_cap.py).

What the cap leaves out, against Algorithm 1's test a-hat(t) + R(t) <= gamma C_S(t) + B(t) with a-hat(t) = ALG(t - 1) +
p_E(t) + rent_E(t) + G(t) + S(t) (design/theory/naive_caps.md, the four parts of the naive-cap result, PROVEN by
example and checked by code/theory_checks/c3/ms8/check_naive_cap.py): 'paid' misses p_E(t), so one slot's purchases
pass unpriced (excess n - X on Proposition G6(i)'s I_n); 'stop' has no K0 ('paid' also misses rent_E(t)), so leases
that the inner holds past their billed term keep renting (excess linear in T); every cap misses S(t) and the reserve
R(t), so the stranding of the served load when service ends is not priced (excess n mu^fb); and every cap misses the
service term G(t): 'slot' prices the slot's purchases and rent against FB(t - 1) + Q(t) + X(t) but prices the slot's
service at 0, so a purchase that serves no client and costs up to Q(t) + X(t) passes while the slot still falls back
(excess n q - X). So 'slot' is not stricter than 'paid', and it is not A8's test T0, which prices the service at its
upper bound Q(t) (binding iff ALG(t - 1) + p_E(t) + rent_E(t) > FB(t - 1) + X(t)).

Parameters: inner (an id of CAP_INNER_IDS, default 'A9', or a Policy instance for tests, with empty inner_params),
inner_params (the inner's parameters), X ('lb', the default, a number, or 'rel:<eps>'), count ('paid', the default, or
'slot'), on_bind ('stop', the default, or 'latch'). The inner must not use on_fast (wants_fast false after reset;
PolicyError otherwise): the cap passes no fast action. It receives a deep copy of the policy generator at reset, so it
draws exactly as it would alone. Information class: the inner's (online-I1 for A9, BL1 and BL5); OnlineLB reads only
the view and the revealed demand.

report(): {'cap': {X, count, on_bind, bind_slots, first_bind, dropped_buys, dropped_other, latch_t, latch_releases,
FB_T, X_T, B_T, paid_excess_max (max over slots of ALG(t - 1) - FB(t - 1) - X(t)), FB_series (FB(t) through slot t),
X_series (X(t)), B_series (B(t))}, 'online_lb': OnlineLB.report(), 'inner': the inner's report}. The OnlineLB is
stepped at every slot whatever X, so B(t) is reported for every cap.

This module imports numpy, the standard library, sublet.types, sublet.policies.base and modules of sublet.algos and
sublet.baselines (the inner policies lazily, never the registry); guard.py and online_lb.py are used unchanged.
"""
from __future__ import annotations

import copy
import math
from typing import Optional

import numpy as np

from ..policies.base import Policy
from ..types import ActionResult, Buy, Drain, FastObs, Load, PublicView, Release, SetAdmission, SlowObs, Unload
from .common import PolicyError, resolve_params
from .guard import fallback_by_client, inner_obs, slot_terms
from .online_lb import OnlineLB

CAP_INNER_IDS = ("A9", "BL1", "BL5")      # registry.CAP_INNER_IDS (design/ms8/plan.md D2)
COUNTS = ("paid", "slot")
ON_BIND = ("stop", "latch")
REFUSAL = "cap"                            # the reason of a dropped action in the inner's results


def _cap_inner_class(inner: str):
    """The policy class of an inner id of CAP, imported on first use."""
    if inner == "A9":
        from .a9 import NoticeCriticalRatio
        return NoticeCriticalRatio
    if inner == "BL1":
        from ..baselines.greedy import GreedyLease
        return GreedyLease
    if inner == "BL5":
        from ..baselines.retrorenting import RetroRentingStyle
        return RetroRentingStyle
    raise PolicyError(f"CAP: inner must be one of {list(CAP_INNER_IDS)}, got {inner!r}")


def _is_num(v) -> bool:
    return isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, (bool, np.bool_))


def parse_X(X) -> tuple[str, float]:
    """(kind, value) of an allowance: ('lb', 0.0), ('const', X) or ('rel', eps); PolicyError for anything else."""
    if isinstance(X, str):
        if X == "lb":
            return "lb", 0.0
        if X.startswith("rel:"):
            try:
                eps = float(X[4:])
            except ValueError:
                eps = float("nan")
            if math.isfinite(eps) and eps >= 0.0:
                return "rel", eps
        raise PolicyError(f"CAP: X must be 'lb', a number >= 0 or 'rel:<eps>' with eps >= 0, got {X!r}")
    if _is_num(X) and math.isfinite(float(X)) and float(X) >= 0.0:
        return "const", float(X)
    raise PolicyError(f"CAP: X must be 'lb', a finite number >= 0 or 'rel:<eps>', got {X!r}")


class BudgetCapped(Policy):
    """CAP (design/ms8/plan.md D2): the inner policy under the naive spend cap of the module docstring."""
    name = "CAP"
    PARAMS = {"inner": "A9", "inner_params": {}, "X": "lb", "count": "paid", "on_bind": "stop"}

    def __init__(self, **kw):
        self._p, _ = resolve_params(self.PARAMS, kw, "CAP")
        p = self._p
        self.X_kind, self.X_val = parse_X(p["X"])
        if p["count"] not in COUNTS:
            raise PolicyError(f"CAP: count must be one of {list(COUNTS)}, got {p['count']!r}")
        if p["on_bind"] not in ON_BIND:
            raise PolicyError(f"CAP: on_bind must be one of {list(ON_BIND)}, got {p['on_bind']!r}")
        ip = {} if p["inner_params"] is None else p["inner_params"]
        if not isinstance(ip, dict):
            raise PolicyError(f"CAP: inner_params must be an object, got {type(ip).__name__}")
        inner = p["inner"]
        if isinstance(inner, Policy):
            if ip:
                raise PolicyError("CAP: inner_params must be empty when inner is a Policy instance")
            self.inner, self.inner_id = inner, getattr(inner, "name", type(inner).__name__)
        else:
            if inner not in CAP_INNER_IDS:
                raise PolicyError(f"CAP: inner must be one of {list(CAP_INNER_IDS)}, got {inner!r}")
            self.inner, self.inner_id = _cap_inner_class(inner)(**dict(ip)), inner
        self._ip = copy.deepcopy(dict(ip))

    def params(self) -> dict:
        out = {k: copy.deepcopy(v) for k, v in self._p.items() if k not in ("inner", "inner_params")}
        out["inner"] = self.inner_id
        pf = getattr(self.inner, "params", None)
        out["inner_params"] = pf() if callable(pf) else {}
        return out

    # -------------------------------------------------------- reset
    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        self.inner.reset(view, copy.deepcopy(rng))
        if bool(getattr(self.inner, "wants_fast", False)):
            raise PolicyError(f"CAP: the inner policy {self.inner_id!r} uses on_fast; the cap passes no fast action")
        self.wants_fast = False
        self.olb = OnlineLB(view)
        self.fb = 0.0                              # FB(t - 1) at the start of act(t), FB(t) after it
        self.latched = False
        self._map: Optional[tuple] = None          # after a slot with dropped actions: (inner index per kept, dropped)
        self.fb_series: list[float] = []
        self.X_series: list[float] = []
        self.stats = {"bind_slots": 0, "first_bind": None, "dropped_buys": 0, "dropped_other": 0, "latch_t": None,
                      "latch_releases": 0, "after_latch_releases": 0, "paid_excess_max": None}

    def allowance(self, fb_prev: float) -> float:
        """X(t) at the current slot (after OnlineLB.step of the slot)."""
        if self.X_kind == "lb":
            return float(self.olb.B)
        if self.X_kind == "rel":
            return self.X_val * float(fb_prev)
        return self.X_val

    def _inner_results(self, results) -> list:
        """The engine's results of the last executed (filtered) list in the inner's indices (ProjectedGuarded's rule)."""
        src, dropped = self._map
        out = [ActionResult(src[r.index], r.action, r.ok, r.lease_id, r.replica_ids, r.reason)
               for r in results if 0 <= r.index < len(src) and src[r.index] is not None]
        out += [ActionResult(i, a, False, None, (), REFUSAL) for i, a in dropped]
        out.sort(key=lambda r: r.index)
        return out

    @staticmethod
    def _in_obs(obs: SlowObs, a) -> bool:
        """Whether a non-Buy action names only objects that obs holds (ProjectedGuarded.candidates' A^-)."""
        if isinstance(a, Buy):
            return False
        leases = {int(lid) for lid in obs.leases}
        if isinstance(a, (Release, Load)):
            return int(a.lease_id) in leases
        if isinstance(a, (Unload, SetAdmission, Drain)):
            reps = {int(rid) for rid, rv in obs.replicas.items() if int(rv.lease_id) in leases}
            return int(a.replica_id) in reps
        return False

    # -------------------------------------------------------- act
    def act(self, obs: SlowObs) -> list:
        t = int(obs.t)
        self.olb.step(obs)                         # B(t) of this slot (reported for every X)
        Q = float(fallback_by_client(self.view, obs.demand).sum())
        fb_prev = self.fb
        X = self.allowance(fb_prev)
        alg_prev = float(obs.cost_so_far)
        ex = alg_prev - fb_prev - X
        pm = self.stats["paid_excess_max"]
        self.stats["paid_excess_max"] = ex if pm is None else max(pm, ex)
        self.fb = fb_prev + Q
        self.fb_series.append(self.fb)
        self.X_series.append(X)
        if self.latched:
            rel = [Release(int(lid)) for lid in sorted(obs.leases)]
            self.stats["after_latch_releases"] += len(rel)
            return rel
        io = inner_obs(obs)                        # a private copy (audit F2): the test reads obs
        if self._map is not None:
            io.results = self._inner_results(obs.results)
            self._map = None
        acts = list(self.inner.act(io))
        lhs, rhs = alg_prev, fb_prev + X
        if self._p["count"] == "slot":
            pE, rent = slot_terms(self.view, obs, acts)
            lhs += pE + rent
            rhs += Q
        if not lhs > rhs:
            return acts
        st = self.stats
        st["bind_slots"] += 1
        if st["first_bind"] is None:
            st["first_bind"] = t
        if self._p["on_bind"] == "latch":
            self.latched = True
            st["latch_t"] = t
            rel = [Release(int(lid)) for lid in sorted(obs.leases)]
            st["latch_releases"] = len(rel)
            return rel
        keep = [i for i, a in enumerate(acts) if self._in_obs(obs, a)]
        if len(keep) == len(acts):
            return acts
        used = set(keep)
        dropped = [(i, a) for i, a in enumerate(acts) if i not in used]
        nb = sum(1 for _i, a in dropped if isinstance(a, Buy))
        st["dropped_buys"] += nb
        st["dropped_other"] += len(dropped) - nb
        self._map = (list(keep), dropped)
        return [acts[i] for i in keep]

    def on_fast(self, obs: FastObs) -> list:
        return []

    # -------------------------------------------------------- report
    def report(self) -> dict:
        if getattr(self, "olb", None) is None:
            return {}
        X_rule = self._p["X"] if not _is_num(self._p["X"]) else float(self._p["X"])
        cap = {"X": X_rule, "count": self._p["count"], "on_bind": self._p["on_bind"], **copy.deepcopy(self.stats),
               "FB_T": self.fb_series[-1] if self.fb_series else 0.0,
               "X_T": self.X_series[-1] if self.X_series else None,
               "B_T": float(self.olb.B), "FB_series": list(self.fb_series), "X_series": list(self.X_series),
               "B_series": list(self.olb.B_series)}
        rf = getattr(self.inner, "report", None)
        return {"cap": cap, "online_lb": self.olb.report(), "inner": (rf() or {}) if callable(rf) else {}}


__all__ = ["CAP_INNER_IDS", "COUNTS", "ON_BIND", "REFUSAL", "parse_X", "BudgetCapped"]
