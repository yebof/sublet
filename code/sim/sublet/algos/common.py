"""Shared policy helpers (design/sim_spec_ms2.md §2.3, §3.2).

Random streams and the site order pi, per-unit and per-column costs of the PD's accounting,
the protected-contract test of M47, and `LeaseBook`, the per-slot staging of a policy's actions
with the pending-buy bookkeeping, liveness filtering and the capacity pre-check of §2.3.
Policies see only the PublicView and the observations; this module imports only numpy, the
standard library and sublet.types.
"""
from __future__ import annotations

import copy
from typing import Optional, Sequence

import numpy as np

from ..types import INF, ActionResult, Buy, Drain, LeaseView, PublicView, Release, SetAdmission, SlowObs

EPS_DEMAND = 1e-12      # demand of a client is "on" iff > EPS_DEMAND


class PolicyError(ValueError):
    """A policy parameter outside its domain, or an instance outside the policy's domain (raised in
    the constructor or in reset)."""


def resolve_params(defaults: dict, kw: dict, who: str = "policy",
                   inputs: Sequence[str] = ()) -> tuple[dict, dict]:
    """Split constructor keywords into (parameters, driver inputs): parameters are `defaults` (a
    class's PARAMS, deep-copied) updated by the given keys, driver inputs the given keys named in
    `inputs` (e.g. 'N_bound', §4.2). Any other key raises PolicyError."""
    unknown = sorted(set(kw) - set(defaults) - set(inputs))
    if unknown:
        raise PolicyError(f"{who}: unknown parameter(s) {unknown}; allowed {sorted(defaults)}"
                          + (f", driver inputs {sorted(inputs)}" if inputs else ""))
    params = copy.deepcopy(dict(defaults))
    params.update({k: v for k, v in kw.items() if k in defaults})
    return params, {k: v for k, v in kw.items() if k in inputs and k not in defaults}


# ---------------------------------------------------------------- random streams and site order
def policy_streams(rng: np.random.Generator) -> dict[str, np.random.Generator]:
    """{'main': rng, 'order': c0, 'marking': c1, 'aux': c2} with (c0, c1, c2) = rng.spawn(3) (§2.3).
    `main` is the generator itself (PD thresholds, the family marking policy); spawning does not
    consume its draws."""
    c0, c1, c2 = rng.spawn(3)
    return {"main": rng, "order": c0, "marking": c1, "aux": c2}


def site_order(view: PublicView, rng_order: Optional[np.random.Generator], mode: str = "auto") -> np.ndarray:
    """Permutation pi of the site indices (§2.3, M7): identity for mode 'index',
    rng_order.permutation(m) for 'random'; 'auto' is 'random' if some site has kind 'layer', else
    'index' (so the identity on from_core instances)."""
    m = len(view.sites)
    if mode == "auto":
        mode = "random" if any(s.kind == "layer" for s in view.sites) else "index"
    if mode == "index":
        return np.arange(m, dtype=np.int64)
    if mode == "random":
        if rng_order is None:
            raise PolicyError("site_order: mode 'random' needs the 'order' stream")
        return np.asarray(rng_order.permutation(m), dtype=np.int64)
    raise PolicyError(f"site_order: unknown mode {mode!r} (auto, index, random)")


# ---------------------------------------------------------------- demand and costs
def slot_max_demand(obs: SlowObs) -> np.ndarray:
    """(n,) D_c(t): maximum of the demand over the fast slots of slot t (revealed at its start)."""
    d = np.asarray(obs.demand, dtype=np.float64)
    if d.size == 0:
        return np.zeros(d.shape[0], dtype=np.float64)
    return d.max(axis=1)


def unit_costs(view: PublicView) -> tuple[np.ndarray, np.ndarray]:
    """(q_req (n,), delta_req (n, m)) per unit-slot: q_{j_c} Δs / (60 u) and δ_cl Δs / (60 u), INF
    kept, with to_core's operation order (so the values equal its q and delta)."""
    slow, u = view.grid.slow_min, view.units_per_replica
    q = np.array([L.q_usd_per_h for L in view.llms], dtype=np.float64)
    q_req = q[np.asarray(view.client_llm, dtype=np.int64)] * slow / (60 * u)
    delta_req = np.asarray(view.client_delta_usd_per_h, dtype=np.float64) * slow / (60 * u)
    return q_req, delta_req


def treated_as_protected(view: PublicView, k: int) -> bool:
    """Contract k is protected or never announced within the horizon (tau_slots >= T_slow), M47."""
    c = view.contracts[k]
    return c.protected or c.tau_slots >= view.grid.T_slow


def pd_window_slots(view: PublicView, k: int, protected_window: Optional[int]) -> int:
    """PD window L_k in slow slots (§5.2): tau_k + H_k // Δs (rule T12) for a contract with
    tau_slots set, also when tau_k >= T_s; for a Contract.protected one `protected_window` if given,
    else the largest rule-T12 window over the contracts with tau_slots set, at least 1 (M5)."""
    c = view.contracts[k]
    slow = view.grid.slow_min
    if c.tau_slots is not None:
        return int(c.tau_slots) + int(c.H_min) // slow
    if protected_window is not None:
        if isinstance(protected_window, bool) or not isinstance(protected_window, (int, np.integer)) \
                or protected_window < 1:
            raise PolicyError(f"protected_window must be an integer >= 1, got {protected_window!r}")
        return int(protected_window)
    Ls = [int(x.tau_slots) + int(x.H_min) // slow for x in view.contracts if x.tau_slots is not None]
    return max([1] + Ls)


def column_cost(view: PublicView, l: int, j: int, k: int, L_slots: int) -> float:
    """C_F = beta_tilde_usd[j, l, k] + g_j price[l, k] max(P_k, L_slots Δs) / 60 (M4), with P_k the
    contract's prepaid_min: the billed term plus rent for the rest of the window. INF if (l, k) is
    not offered."""
    a = float(view.price[l, k])
    if not np.isfinite(a):
        return INF
    P = int(view.contracts[k].prepaid_min)
    g = view.llms[j].g
    return float(view.beta_tilde_usd[j, l, k]) + g * a * max(P, int(L_slots) * view.grid.slow_min) / 60.0


def lam_ms(view: PublicView) -> np.ndarray:
    """(J, m) int64 load times in milliseconds, np.round(1000 * lam_s) as Instance.lam_ms (rule T8)."""
    return np.round(1000.0 * np.asarray(view.lam_s, dtype=np.float64)).astype(np.int64)


# ---------------------------------------------------------------- attributed load
_ATTR_CACHE: list = [None, None]    # [obs, {(j, l): sum of admissions of own warm replicas}]


def _admission_sums(obs: SlowObs) -> dict:
    if _ATTR_CACHE[0] is obs:
        return _ATTR_CACHE[1]
    den: dict = {}
    for rv in obs.replicas.values():
        L = obs.leases.get(rv.lease_id)
        if rv.state != "warm" or L is None:
            continue
        key = (rv.llm, L.site)
        den[key] = den.get(key, 0.0) + float(rv.admission)
    _ATTR_CACHE[0], _ATTR_CACHE[1] = obs, den
    return den


def attributed_load(obs: SlowObs, view: PublicView, lease: Optional[LeaseView]) -> float:
    """Load attributed to `lease` over slot t-1: served_prev[j, l] x (admissions of the lease's warm
    replicas of j) / (admissions of all own warm replicas of j at l), summed over the LLMs of the
    lease's replicas; 0 where the denominator is 0, and 0 for a lease that is None or absent from
    obs.leases (dead). Admissions are the values in force at slot t (ReplicaView)."""
    if lease is None or lease.id not in obs.leases:
        return 0.0
    den = _admission_sums(obs)
    num: dict = {}
    for rid in lease.replicas:
        rv = obs.replicas.get(rid)
        if rv is None or rv.state != "warm":
            continue
        num[rv.llm] = num.get(rv.llm, 0.0) + float(rv.admission)
    out = 0.0
    for j, a in num.items():
        d = den.get((j, lease.site), 0.0)
        if d > 0:
            out += float(obs.served_prev[j, lease.site]) * a / d
    return out


def attributed_loads(obs: SlowObs, view: PublicView) -> dict[int, float]:
    """attributed_load for every lease in obs.leases, by lease id."""
    return {lid: attributed_load(obs, view, L) for lid, L in obs.leases.items()}


# ---------------------------------------------------------------- lease book
class LeaseBook:
    """Pending-buy bookkeeping, staging and liveness of one policy (§2.3), the pattern of FixedPlan
    and RenewReplay (MS1 §5.8).

    Per slow slot: `begin(obs)` first; components stage actions with `release`, `other` and `buy`
    (a Buy under a key of the caller's choice); `act` returns `assemble(obs, view)`. `assemble` puts
    the Releases first, then the Drains and SetAdmissions, then the Buys in staging order, drops a
    Buy that fails the capacity pre-check (the engine's check, which sees the Releases first and the
    Buys kept before it) and remembers (final index, key) of every kept Buy; the next `begin` maps
    them to their results. Releases of leases absent from obs.leases (dead, trap T1) and Drains and
    SetAdmissions of replicas absent from obs.replicas or on a lease released in the same slot are
    dropped, since the engine would raise ActionError; `stats` counts them."""

    def __init__(self) -> None:
        self._release: list[int] = []
        self._other: list = []
        self._buys: list[tuple[object, Buy]] = []
        self._pending: list[tuple[int, object, Buy]] = []     # (final index, key, Buy) of the last assemble
        self._dropped: list[tuple[object, Buy]] = []          # Buys the last assemble's pre-check dropped
        self._causes: dict[int, str] = {}
        self.stats = {"buys": 0, "precheck": 0, "dead_release": 0, "dead_other": 0}

    # -------------------------------------------------------- per slot
    def begin(self, obs: SlowObs) -> list[tuple[object, ActionResult]]:
        """Map the last slot's kept Buys to their results in obs.results: (key, result) for each, in
        final-index order, then (key, refused result) for each Buy that assemble dropped, in
        staging order (ActionResult with index -1, ok False, reason 'precheck'). Records the end
        causes of obs.ended and clears the staging lists."""
        out: list[tuple[object, ActionResult]] = []
        if self._pending:
            by_index = {r.index: r for r in obs.results}
            for i, key, b in self._pending:
                r = by_index.get(i)
                if r is None:
                    continue
                if r.action != b:
                    raise PolicyError(f"LeaseBook: result {i} is {r.action!r}, staged {b!r}; act must "
                                      "return the list of assemble() unchanged")
                out.append((key, r))
        for key, b in self._dropped:
            out.append((key, ActionResult(-1, b, False, None, (), "precheck")))
        for lid, _end, cause in obs.ended:
            self._causes[int(lid)] = cause
        self._pending, self._dropped = [], []
        self._release, self._other, self._buys = [], [], []
        return out

    def buy(self, key: object, b: Buy) -> None:
        """Stage the Buy `b` under `key` (its result comes back from the next begin under that key)."""
        if not isinstance(b, Buy):
            raise PolicyError(f"LeaseBook.buy: expected a Buy, got {b!r}")
        self._buys.append((key, b))

    def release(self, lease_id: int) -> None:
        """Stage Release(lease_id); a lease staged twice in one slot is released once."""
        lid = int(lease_id)
        if lid not in self._release:
            self._release.append(lid)

    def other(self, action) -> None:
        """Stage a Drain or a SetAdmission."""
        if not isinstance(action, (Drain, SetAdmission)):
            raise PolicyError(f"LeaseBook.other: expected a Drain or SetAdmission, got {action!r}")
        self._other.append(action)

    # -------------------------------------------------------- pre-check
    def _held(self, obs: SlowObs, view: PublicView) -> tuple[dict[int, float], set[int]]:
        """GPUs of the own leases alive at the slot start per site, minus the staged Releases (the
        engine processes them first), and the set of released lease ids."""
        released = {lid for lid in self._release if lid in obs.leases}
        held: dict[int, float] = {}
        for lid, L in obs.leases.items():
            if lid not in released:
                held[L.site] = held.get(L.site, 0.0) + L.gpus
        return held, released

    @staticmethod
    def _fits(view: PublicView, held: dict, b: Buy) -> tuple[bool, int, float]:
        """(fits, site, GPUs) of Buy b against the held GPUs; a Buy with an invalid site or LLM index
        passes, so that the engine raises its ActionError."""
        J, m = len(view.llms), len(view.sites)
        ok_idx = all(isinstance(v, (int, np.integer)) and not isinstance(v, bool) for v in (b.site, b.llm))
        if not ok_idx or not (0 <= b.site < m and 0 <= b.llm < J):
            return True, -1, 0.0
        n = b.n_replicas if isinstance(b.n_replicas, (int, np.integer)) else 0
        gpus = float(view.llms[b.llm].g * n)
        return held.get(int(b.site), 0.0) + gpus <= view.sites[b.site].capacity_gpus, int(b.site), gpus

    def can_buy(self, obs: SlowObs, view: PublicView, site: int, gpus: int) -> bool:
        """Whether a Buy of `gpus` GPUs at `site` staged now would pass the pre-check of assemble,
        given the Releases and Buys staged so far."""
        held, _ = self._held(obs, view)
        for _key, b in self._buys:
            ok, l, g = self._fits(view, held, b)
            if ok and l >= 0:
                held[l] = held.get(l, 0.0) + g
        return held.get(int(site), 0.0) + float(gpus) <= view.sites[int(site)].capacity_gpus

    def assemble(self, obs: SlowObs, view: PublicView) -> list:
        """The slot's action list: Releases, then Drains and SetAdmissions, then the Buys in staging
        order that pass the capacity pre-check of §2.3."""
        held, released = self._held(obs, view)
        actions: list = []
        for lid in self._release:
            if lid in obs.leases:
                actions.append(Release(lid))
            else:
                self.stats["dead_release"] += 1
        for a in self._other:
            rv = obs.replicas.get(a.replica_id)
            if rv is None or rv.lease_id in released or rv.lease_id not in obs.leases:
                self.stats["dead_other"] += 1
                continue
            actions.append(a)
        self._pending, self._dropped = [], []
        for key, b in self._buys:
            ok, l, g = self._fits(view, held, b)
            if not ok:
                self._dropped.append((key, b))
                self.stats["precheck"] += 1
                continue
            if l >= 0:
                held[l] = held.get(l, 0.0) + g
            self._pending.append((len(actions), key, b))
            actions.append(b)
            self.stats["buys"] += 1
        return actions

    def cause(self, lease_id: int) -> Optional[str]:
        """End cause of a lease once obs.ended has reported it ('reclaim', 'release', 'violation',
        'horizon'), else None."""
        return self._causes.get(int(lease_id))


__all__ = ["EPS_DEMAND", "PolicyError", "resolve_params", "policy_streams", "site_order", "slot_max_demand",
           "unit_costs", "treated_as_protected", "pd_window_slots", "column_cost", "lam_ms",
           "attributed_load", "attributed_loads", "LeaseBook"]
