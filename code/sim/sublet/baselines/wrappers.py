"""BL6 notice-oblivious and BL7 revocable-only wrappers around A1, A2 and A6
(design/sim_spec_ms2.md §15.8; C3-P6, C3-P5; M46, M47).

BL6 = NoticeOblivious(inner): the inner algorithm plans as if H_k = 0. For A2 and A6 the wrapper sets
the inner's view_transform = "notice_oblivious" (PD windows tau_k with the real billed term; for A6
also P1 with every H_k read as 0 and P3 off). For A1 the wrapper passes the inner, in reset, a copy of
the view whose revocable contracts have H_min = 0 and their real prepaid_min. In mode "as_if_H0"
(default) a notice (r, E) on a lease in obs.leases makes the wrapper release the lease at r (not
deferred) and show the inner the slot as it would be with H = 0: the notice with death_min = r Δs,
the lease and its replicas absent from obs.leases and obs.replicas (dead in the whole slot, rule T6),
and its end (lease, r Δs, 'reclaim') in obs.ended (the engine's later report of the release is
dropped). Under `eager` every lease is announced at s + tau_k, so BL6 uses exactly [s, s + tau_k),
C3-P6's class. Mode "notice_blind" (a sensitivity, not C3-P6's class) keeps the H = 0 planning and
hides every notice (obs.notices empty, announce_slot and death_min of the leases None); the inner
reacts at the death.

BL7 = RevocableOnly(inner): the inner sees no contract that common.treated_as_protected flags
(protected, or tau_k >= T_s; M47). For A2 and A6 the wrapper sets view_transform = "revocable_only";
for A1 it passes a view without the flagged contracts on any menu (price INF), so A1 runs in its RRL
mode (cold only, no insurance, §9.4). The instance, and therefore BL8, keeps the full menu.

The inner's actions are returned unchanged after the wrapper's own Releases, which come first (the
engine processes Releases before the inner's Buys); results are mapped back to the inner's indices.
The wrappers import algos.a1, algos.a2 and algos.a6 directly (§2.2), lazily, never the registry.
"""
from __future__ import annotations

import copy
import dataclasses

import numpy as np

from ..algos.common import PolicyError, resolve_params, treated_as_protected
from ..policies.base import Policy
from ..types import INF, FastObs, Notice, PublicView, Release, SlowObs

INNER_IDS = ("A1", "A2", "A6")


def _inner_class(inner: str):
    """The policy class of an inner id, imported on first use."""
    if inner == "A1":
        from ..algos.a1 import A1
        return A1
    if inner == "A2":
        from ..algos.a2 import A2
        return A2
    if inner == "A6":
        from ..algos.a6 import A6
        return A6
    raise PolicyError(f"inner must be one of {list(INNER_IDS)}, got {inner!r}")


def _ro(a: np.ndarray) -> np.ndarray:
    a = np.array(a, copy=True)
    a.setflags(write=False)
    return a


def view_h0(view: PublicView) -> PublicView:
    """Copy of the view whose revocable contracts (not flagged by treated_as_protected) have H_min = 0
    and their real prepaid_min (BL6 with inner A1)."""
    cs = tuple(c if treated_as_protected(view, k) else dataclasses.replace(c, H_min=0)
               for k, c in enumerate(view.contracts))
    return dataclasses.replace(view, contracts=cs)


def view_revocable_only(view: PublicView) -> PublicView:
    """Copy of the view without the contracts that treated_as_protected flags: they leave every menu
    and their prices and beta~ become INF (BL7 with inner A1)."""
    flagged = [k for k in range(len(view.contracts)) if treated_as_protected(view, k)]
    if not flagged:
        return view
    sites = tuple(dataclasses.replace(s, menu=tuple(k for k in s.menu if k not in flagged)) for s in view.sites)
    price = np.array(view.price, dtype=np.float64, copy=True)
    bt = np.array(view.beta_tilde_usd, dtype=np.float64, copy=True)
    price[:, flagged] = INF
    bt[:, :, flagged] = INF
    return dataclasses.replace(view, sites=sites, price=_ro(price), beta_tilde_usd=_ro(bt))


class _Wrapper(Policy):
    """Common part of BL6 and BL7: builds the inner policy from `inner` and `inner_params` (which also
    carry the inner's driver inputs, drivers/run.py::make_policy), maps results back to the inner's
    action indices and forwards reset, act, on_fast, params and report."""
    PARAMS: dict = {}
    VIEW_TRANSFORM = ""
    WHO = ""

    def __init__(self, **kw):
        self._params, _ = resolve_params(self.PARAMS, kw, who=self.WHO)
        inner = self._params["inner"]
        if inner not in INNER_IDS:
            raise PolicyError(f"{self.WHO}: inner must be one of {list(INNER_IDS)}, got {inner!r}")
        ip = self._params["inner_params"]
        if ip is None:
            ip = {}
        if not isinstance(ip, dict):
            raise PolicyError(f"{self.WHO}: inner_params must be an object, got {type(ip).__name__}")
        kw_inner = dict(ip)
        if inner in ("A2", "A6"):
            vt = kw_inner.get("view_transform")
            if vt is not None and vt != self.VIEW_TRANSFORM:
                raise PolicyError(f"{self.WHO}: inner_params.view_transform {vt!r} conflicts with the wrapper's "
                                  f"{self.VIEW_TRANSFORM!r}")
            kw_inner["view_transform"] = self.VIEW_TRANSFORM
        self._check_inner(inner, kw_inner)
        self.inner_id = inner
        self.inner = _inner_class(inner)(**kw_inner)
        self._n_pre = 0

    def _check_inner(self, inner: str, kw_inner: dict) -> None:
        """Parameter checks of the subclass (PolicyError)."""

    def _inner_view(self, view: PublicView) -> PublicView:
        return view

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        self.slow_min = view.grid.slow_min
        self.inner_view = self._inner_view(view)
        self.inner.reset(self.inner_view, rng)
        self.wants_fast = bool(getattr(self.inner, "wants_fast", False))
        self._n_pre = 0

    def _results(self, results: list) -> list:
        """The results of the inner's actions with the inner's own indices (the wrapper's Releases,
        indices below n_pre, are dropped)."""
        k = self._n_pre
        if not k:
            return list(results)
        return [dataclasses.replace(r, index=r.index - k) for r in results if r.index >= k]

    def on_fast(self, obs: FastObs) -> list:
        if not self.wants_fast:
            return []
        if obs.results and self._n_pre:
            obs = dataclasses.replace(obs, results=self._results(obs.results))
        return self.inner.on_fast(obs)

    def params(self) -> dict:
        out = {k: copy.deepcopy(v) for k, v in self._params.items() if k != "inner_params"}
        p = getattr(self.inner, "params", None)
        out["inner_params"] = p() if callable(p) else {}
        return out

    def report(self) -> dict:
        r = getattr(self.inner, "report", None)
        return {"wrapper": self.WHO, "inner_id": self.inner_id, "inner": r() if callable(r) else {}}


class NoticeOblivious(_Wrapper):
    """BL6 (C3-P6 class, M46): the inner plans as if every notice were 0."""
    name = "notice_oblivious"
    WHO = "BL6"
    VIEW_TRANSFORM = "notice_oblivious"
    PARAMS = {"inner": "A1", "mode": "as_if_H0", "inner_params": {}}

    def _check_inner(self, inner: str, kw_inner: dict) -> None:
        if self._params["mode"] not in ("as_if_H0", "notice_blind"):
            raise PolicyError(f"BL6: mode must be 'as_if_H0' or 'notice_blind', got {self._params['mode']!r}")

    def _inner_view(self, view: PublicView) -> PublicView:
        return view_h0(view) if self.inner_id == "A1" else view

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        self._converted: set[int] = set()
        self.n_notices = 0
        self.n_released = 0

    def act(self, obs: SlowObs) -> list:
        results = self._results(obs.results)
        if self._params["mode"] == "notice_blind":
            leases = {lid: (dataclasses.replace(L, announce_slot=None, death_min=None)
                            if L.announce_slot is not None or L.death_min is not None else L)
                      for lid, L in obs.leases.items()}
            self.n_notices += len(obs.notices)
            obs_in = dataclasses.replace(obs, leases=leases, notices=[], results=results)
            self._n_pre = 0
            return list(self.inner.act(obs_in))
        # as_if_H0: release at the notice, show the inner the slot of an H = 0 notice
        ended_now = {e[0] for e in obs.ended}
        ended = [e for e in obs.ended if e[0] not in self._converted]
        notices, rel = [], []
        for nt in obs.notices:
            self.n_notices += 1
            E0 = nt.r_slot * self.slow_min
            notices.append(Notice(nt.lease_id, nt.r_slot, E0))
            if nt.lease_id in self._converted:
                continue
            self._converted.add(nt.lease_id)
            if nt.lease_id not in ended_now:
                ended.append((nt.lease_id, E0, "reclaim"))
            if nt.lease_id in obs.leases:
                rel.append(nt.lease_id)
        if rel:
            gone = set(rel)
            leases = {lid: L for lid, L in obs.leases.items() if lid not in gone}
            replicas = {rid: R for rid, R in obs.replicas.items() if R.lease_id not in gone}
        else:
            leases, replicas = obs.leases, obs.replicas
        obs_in = dataclasses.replace(obs, leases=leases, replicas=replicas, notices=notices, ended=ended,
                                     results=results)
        acts = list(self.inner.act(obs_in))
        inner_rel = {a.lease_id for a in acts if isinstance(a, Release)}
        own = [Release(lid) for lid in rel if lid not in inner_rel]
        self.n_released += len(own)
        self._n_pre = len(own)
        return own + acts

    def report(self) -> dict:
        out = super().report()
        out.update(mode=self._params["mode"], notices=getattr(self, "n_notices", 0),
                   released_at_notice=getattr(self, "n_released", 0))
        return out


class RevocableOnly(_Wrapper):
    """BL7 (C3-P5 class, M47): the inner sees only the contracts that treated_as_protected does not flag."""
    name = "revocable_only"
    WHO = "BL7"
    VIEW_TRANSFORM = "revocable_only"
    PARAMS = {"inner": "A1", "inner_params": {}}

    def _check_inner(self, inner: str, kw_inner: dict) -> None:
        if inner == "A1" and kw_inner.get("site_prot") is not None:
            raise PolicyError("BL7: inner A1 runs in RRL mode, so site_prot must be None")

    def _inner_view(self, view: PublicView) -> PublicView:
        return view_revocable_only(view) if self.inner_id == "A1" else view

    def act(self, obs: SlowObs) -> list:
        self._n_pre = 0
        return list(self.inner.act(obs))


__all__ = ["NoticeOblivious", "RevocableOnly", "view_h0", "view_revocable_only", "INNER_IDS"]
