"""Policy A2: ORML-PD with threshold rounding, executed without renewal (design/sim_spec_ms2.md §6.6, §6.7).

A2Planner holds steps 1-4 of §6.7 (refusals, the requests of the slot through the vectorized PD,
rounding and capacity layering) and is shared with the policies that execute its columns otherwise
(A3 passes them to the execution layer, §7.5). A2 buys each opened column F = (l, j, k, s, iota),
opened at t0, as Buy(l, k, j, 1, tag='a2') at t0 and releases the lease at the first slot
t >= max(s + L_k, ceil((t0 Δs + P_k) / Δs)) if it is still alive (the window's end or the billed
term's end, whichever is later).

Guarantees: on the ORML core (C3-T2, PROVEN, oblivious demand, any lender) with r-bar = ceil(2 ln N);
in the full model (layering, lambda > 0 folded into beta~, refusals, billing-aware C_F) a heuristic.

Practical Sublet's knobs (design/q44_practical_sublet.md §2, §6.1) enter through the planner's `px`
(default None: the specified algorithm, unchanged): K `kstar_only` (candidate mask), S
`suppress_covered` (rounder), O `layer_order` (replica index by request order), and R / F
(`renew_live`, `renew_profit`), which `live_renewals` applies for policies with an execution layer
(A6, A7). The A2 and A3 policies take no `px`.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from ..baselines.common import k_star
from ..instance import active_units
from ..policies.base import Policy
from ..types import Buy, PublicView, SlowObs
from .common import (LeaseBook, PolicyError, attributed_load, pd_window_slots, policy_streams, resolve_params,
                     site_order, slot_max_demand, treated_as_protected)
from .pd_core import D_MODES, ROOTS, RequestOrder, VecPD, problem_from_view
from .rounding import Layering, Rounder, rbar_theory

VIEW_TRANSFORMS = (None, "notice_oblivious", "revocable_only")
SITE_ORDERS = ("auto", "index", "random")
# practical Sublet's adopted knobs (design/q44_practical_sublet.md §2.2), all off by default
PX_KEYS = ("kstar_only", "suppress_covered", "layer_order", "renew_live", "renew_profit")
RENEW_LOAD = 1e-9       # knob R: a lease renews only if its attributed load over slot t-1 exceeds this


def resolve_px(px, who: str = "px") -> dict:
    """The knob settings {key: bool} of PX_KEYS for a `px` parameter: None gives every knob off; a dict
    sets the keys it names (bools), the others off. PolicyError for an unknown key or a non-bool value."""
    if px is None:
        return {k: False for k in PX_KEYS}
    if not isinstance(px, dict):
        raise PolicyError(f"{who}: px must be None or an object of {list(PX_KEYS)}, got {px!r}")
    bad = sorted(set(px) - set(PX_KEYS))
    if bad:
        raise PolicyError(f"{who}: px has unknown key(s) {bad}; allowed {list(PX_KEYS)}")
    for k, v in px.items():
        if not isinstance(v, (bool, np.bool_)):
            raise PolicyError(f"{who}: px.{k} must be a bool, got {v!r}")
    return {k: bool(px.get(k, False)) for k in PX_KEYS}


def _is_int(v, lo: int) -> bool:
    return isinstance(v, (int, np.integer)) and not isinstance(v, bool) and v >= lo


def check_params(p: dict, who: str) -> None:
    """Values of the planner parameters of A2 (§4.2); PolicyError otherwise."""
    if not (p["rbar"] == "theory" or _is_int(p["rbar"], 1)):
        raise PolicyError(f"{who}: rbar must be 1 (or an integer >= 1) or 'theory', got {p['rbar']!r}")
    if p["d_mode"] not in D_MODES:
        raise PolicyError(f"{who}: d_mode must be one of {D_MODES}, got {p['d_mode']!r}")
    if p["root"] not in ROOTS:
        raise PolicyError(f"{who}: root must be one of {ROOTS}, got {p['root']!r}")
    if not _is_int(p["max_raises"], 1):
        raise PolicyError(f"{who}: max_raises must be an integer >= 1, got {p['max_raises']!r}")
    if p["site_order"] not in SITE_ORDERS:
        raise PolicyError(f"{who}: site_order must be one of {SITE_ORDERS}, got {p['site_order']!r}")
    if p["protected_window"] is not None and not _is_int(p["protected_window"], 1):
        raise PolicyError(f"{who}: protected_window must be None or an integer >= 1, got {p['protected_window']!r}")
    for b in ("layering", "record"):
        if not isinstance(p[b], (bool, np.bool_)):
            raise PolicyError(f"{who}: {b} must be a bool, got {p[b]!r}")
    if p["view_transform"] not in VIEW_TRANSFORMS:
        raise PolicyError(f"{who}: view_transform must be one of {VIEW_TRANSFORMS}, got {p['view_transform']!r}")


class A2Planner:
    """Steps 1-4 of A2 (§6.7) on a PublicView: the PD problem with the view transform, the PD, the
    rounder and the layering; `slot(obs)` returns the columns opened at obs.t in opening order.

    view_transform 'notice_oblivious' (BL6): every contract with tau_slots set gets the window
    L_k = tau_k, with C_F = beta~ + g a max(P_k, tau_k Δs) / 60 (the real billed term); a
    Contract.protected one keeps the window of §5.2. 'revocable_only' (BL7): the contracts that
    common.treated_as_protected flags leave the candidate mask. `cand_mask` (m, J, K) further
    restricts the candidates (contract rules of A6).

    px (design/q44_practical_sublet.md §2.1, §2.2; resolve_px; None = every knob off, the code path
    of the specified planner):
    - kstar_only (K): at every site l, the contracts that treated_as_protected does not flag leave the
      mask except k*(l), the baselines' contract (baselines.common.k_star: cheapest per GPU-hour, then
      the shortest billed term, the longest notice, the lowest index); applied on top of cand_mask.
      Flagged contracts are left to the view transform: with 'revocable_only' (practical Sublet) the
      candidate set at l is {k*(l)}, or empty if l offers no unflagged contract (§2.1, "At reset").
    - suppress_covered (S): Rounder.suppress_covered.
    - layer_order (O): when capacity layering is active, the replica index of a request at (l, k) is
      floor(n / u) by request order (pd_core.RequestOrder); iota = 0 on kappa_infinite instances.
    - renew_live (R) and renew_profit (F): read by `live_renewals` (the policy applies them)."""

    def __init__(self, view: PublicView, rng_main: np.random.Generator, rng_order: Optional[np.random.Generator],
                 *, rbar=1, N_bound=None, d_mode="mK+1", protected_window=None, site_order_mode="auto",
                 root="newton", max_raises=2000, layering=True, record=False, view_transform=None,
                 cand_mask=None, px=None):
        if view_transform not in VIEW_TRANSFORMS:
            raise PolicyError(f"view_transform must be one of {VIEW_TRANSFORMS}, got {view_transform!r}")
        if site_order_mode not in SITE_ORDERS:
            raise PolicyError(f"site_order must be one of {SITE_ORDERS}, got {site_order_mode!r}")
        self.view = view
        m, J, K = len(view.sites), len(view.llms), len(view.contracts)
        if rbar == "theory":
            if N_bound is None:
                raise PolicyError("rbar='theory' needs the driver input N_bound (§6.3)")
            self.rbar = rbar_theory(N_bound)
        elif isinstance(rbar, (int, np.integer)) and not isinstance(rbar, bool) and rbar >= 1:
            self.rbar = int(rbar)
        else:
            raise PolicyError(f"rbar must be 1 (or an integer >= 1) or 'theory', got {rbar!r}")
        self.N_bound = None if N_bound is None else int(N_bound)
        self.site_perm = site_order(view, rng_order, site_order_mode)
        mask = np.ones((m, J, K), dtype=bool) if cand_mask is None else np.array(cand_mask, dtype=bool)
        if mask.shape != (m, J, K):
            raise PolicyError(f"cand_mask must have shape {(m, J, K)}, got {mask.shape}")
        windows = None
        self.px_given = px is not None
        self.px = resolve_px(px, "A2Planner")
        if view_transform == "revocable_only":
            for k in range(K):
                if treated_as_protected(view, k):
                    mask[:, :, k] = False
        elif view_transform == "notice_oblivious":
            windows = [int(c.tau_slots) if c.tau_slots is not None else pd_window_slots(view, k, protected_window)
                       for k, c in enumerate(view.contracts)]
        self.kstar = None
        if self.px["kstar_only"]:
            self.kstar = k_star(view)
            unflagged = [k for k in range(K) if not treated_as_protected(view, k)]
            for l in range(m):
                for k in unflagged:
                    if k != int(self.kstar[l]):
                        mask[l, :, k] = False
        self.view_transform = view_transform
        self.prob = problem_from_view(view, protected_window=protected_window, cand_mask=mask, d_mode=d_mode,
                                      site_perm=self.site_perm, windows=windows)
        self.pd = VecPD(self.prob, root=root, max_raises=max_raises, record=record)
        self.rounder = Rounder(self.pd, rng_main, self.rbar)
        self.rounder.suppress_covered = self.px["suppress_covered"]
        self.u = int(view.units_per_replica)
        self.layering = Layering(self.u, bool(layering) and not view.kappa_infinite, shape=(m, J, K))
        self.order = RequestOrder(self.u, (m, J, K)) if self.px["layer_order"] else None
        self.cl_llm = np.asarray(view.client_llm, dtype=np.int64)
        self.refused: dict[int, int] = {}            # refused column id -> end of its window (slot)
        self.refused_reasons: dict[str, int] = {}
        self.n_units_max = 0
        self.n_renew_refused_F = 0                   # knob F: renewals refused because load < rent

    # -------------------------------------------------------- columns
    def column(self, col: int) -> tuple[int, int, int, int, int, int]:
        """(l, j, k, s, iota, L_k) of an opened column; its window is [s, s + L_k)."""
        l, j, k, s, iota, _copy, _p = self.pd.info(col)
        return l, j, k, s, iota, int(self.pd.L[k])

    def refuse(self, col: int, t: int, reason: str = "") -> None:
        """§6.5: the column leaves the candidate lists until its window ends and the opened set."""
        l, j, k, s, iota, L = self.column(col)
        self.refused[int(col)] = s + L
        self.rounder.refuse(col, t)
        self.refused_reasons[reason] = self.refused_reasons.get(reason, 0) + 1

    # -------------------------------------------------------- one slot
    def slot(self, obs: SlowObs) -> list[int]:
        """Steps 2-4 of §6.7: the active units of slot t (client ascending, unit v ascending) through
        the PD and the rounder, the layering; returns the columns opened at t in opening order."""
        t = int(obs.t)
        if self.refused:
            for col in [c for c, e in self.refused.items() if e <= t]:
                del self.refused[col]
        D = slot_max_demand(obs)
        n_units = active_units(D, self.u)
        lay = self.layering
        opened: list[int] = []
        active: set = set()
        excluded = self.refused if self.refused else None
        order = self.order if (self.order is not None and lay.active) else None     # knob O
        if order is not None:
            order.start_slot()
        for c in np.nonzero(n_units)[0]:
            c = int(c)
            ls, ks = self.pd.cand_pairs(c)
            j = int(self.cl_llm[c])
            for v in range(1, int(n_units[c]) + 1):
                unit = (c, v)
                if order is not None:
                    it = order.iota(j, ls, ks)
                else:
                    it = lay.iota_vec(unit, j, ls, ks) if lay.active else None
                out = self.pd.request(c, t, iota=it, excluded=excluded)
                opened += self.rounder.process(out, unit)
                if lay.active:
                    lay.assign(unit, self.rounder.last_assignment)
                    active.add(unit)
        lay.end_slot(active)
        self.n_units_max = max(self.n_units_max, int(n_units.sum()))
        return opened

    def report(self) -> dict:
        pd, r = self.pd, self.rounder
        out = {"P": pd.primal(), "dual": pd.dual, "dual_feasibility": pd.dual_feasibility(), "d": pd.d,
               "rbar": self.rbar, "N_bound": self.N_bound, "cost_pr": r.cost_pr, "cost_an": r.cost_an,
               "n_fix_an": r.n_fix_an, "curve": r.curve.tolist(), "opened": len(r.opened),
               "fixups": r.n_fixups, "refused": len(r.refused), "refused_by_reason": dict(self.refused_reasons),
               "view_transform": self.view_transform, "windows": [int(x) for x in pd.L],
               "layering": {"active": self.layering.active, "max_iota": self.layering.max_iota},
               "units_per_slot_max": self.n_units_max, "pd": pd.stats_summary()}
        if pd.record:
            out["opened_map"] = [[list(pd.ref_key(c)), int(t0)] for c, t0 in r.opened.items()]
        return out

    def px_report(self) -> Optional[dict]:
        """The knob block of a report (None if the planner was built with px=None): the settings, the
        suppressed threshold crossings (S), the renewals (R) and the renewals refused by F, and k*(l)
        per site (K)."""
        if not self.px_given:
            return None
        r = self.rounder
        return {"knobs": dict(self.px), "suppressed": int(r.n_suppressed), "renewed": int(r.n_renewed),
                "renew_refused_F": int(self.n_renew_refused_F),
                "kstar": None if self.kstar is None else [int(k) for k in self.kstar]}


def live_renewals(planner: A2Planner, layer, obs: SlowObs, view: PublicView) -> list[int]:
    """Knob R with F (design/q44_practical_sublet.md §2.1 step 2), before the slot's requests. For each
    logical slot sigma = (l0, j, k, iota) of `layer` in key order: renew if its lease L is in
    obs.leases, at sigma's own site l0 (not a rotated replacement), unannounced (announce_slot None
    and sigma not noticed), sigma's coverage has run out (need[t] false), the attributed load of L over
    slot t-1 (common.attributed_load, replica loads) exceeds RENEW_LOAD and, with renew_profit (F),
    att q_j >= g_j a, the lease's rent per hour (a = price of L's site and contract; the contract is
    sigma's k unless a pre-warm bought another). A renewal marks the PD column (l0, j, k,
    floor(t / L_k) L_k, iota) opened at t at no cost (Rounder.mark_open). Returns the marked column
    ids in key order; the policy opens their windows in the layer (layer.open), so X1 keeps the lease
    to the window's end. A column that is already open is not returned."""
    t = int(obs.t)
    out: list[int] = []
    profit = planner.px["renew_profit"]
    for sl in layer.slots.values():
        if sl.lease is None or sl.lease not in obs.leases or sl.noticed or sl.need[t]:
            continue
        lv = obs.leases[sl.lease]
        l0, j, k, iota = sl.key
        if lv.site != l0 or lv.announce_slot is not None:
            continue
        att = attributed_load(obs, view, lv)
        if att <= RENEW_LOAD:
            continue
        rent = float(view.llms[j].g) * float(view.price[lv.site, lv.contract])      # USD per hour
        if profit and att * float(view.llms[j].q_usd_per_h) < rent:
            planner.n_renew_refused_F += 1
            continue
        col = planner.pd.col_id(l0, j, k, t, iota)
        if planner.rounder.mark_open(col, t):
            out.append(col)
    return out


class A2(Policy):
    """Policy A2 (§6.7): the planner's columns bought at their opening slot and released at
    max(s + L_k, end of the billed term) (§6.6). Driver input: N_bound (for rbar='theory')."""
    name = "A2"
    PARAMS = {"rbar": 1, "d_mode": "mK+1", "protected_window": None, "site_order": "auto", "root": "newton",
              "max_raises": 2000, "layering": True, "record": False, "view_transform": None}
    INPUTS = ("N_bound",)

    def __init__(self, **kw):
        self._params, inputs = resolve_params(self.PARAMS, kw, "A2", inputs=self.INPUTS)
        check_params(self._params, "A2")
        if self._params["rbar"] == "theory" and inputs.get("N_bound") is None:
            raise PolicyError("A2: rbar='theory' needs the driver input N_bound (§6.3)")
        self.N_bound = inputs.get("N_bound")

    def params(self) -> dict:
        return dict(self._params)

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        p = self._params
        streams = policy_streams(rng)
        self.planner = A2Planner(view, streams["main"], streams["order"], rbar=p["rbar"], N_bound=self.N_bound,
                                 d_mode=p["d_mode"], protected_window=p["protected_window"],
                                 site_order_mode=p["site_order"], root=p["root"], max_raises=p["max_raises"],
                                 layering=p["layering"], record=p["record"], view_transform=p["view_transform"])
        self.book = LeaseBook()
        self.slow = int(view.grid.slow_min)
        self.prepaid = [int(c.prepaid_min) for c in view.contracts]
        self.release_at: dict[int, list[int]] = {}
        self.lease_col: dict[int, int] = {}          # lease id -> column id
        self.n_bought = 0
        self.n_released = 0
        self.n_refused = 0

    def _release_slot(self, col: int, t0: int) -> int:
        l, j, k, s, iota, L = self.planner.column(col)
        return max(s + L, t0 + -(-self.prepaid[k] // self.slow))

    def act(self, obs: SlowObs) -> list:
        t = int(obs.t)
        pl = self.planner
        # 1. results of the last slot's purchases; refusals before this slot's requests (§6.5)
        for col, res in self.book.begin(obs):
            if res.ok:
                self.lease_col[res.lease_id] = col
                self.release_at.setdefault(self._release_slot(col, t - 1), []).append(res.lease_id)
                self.n_bought += 1
            else:
                pl.refuse(col, t, res.reason)
                self.n_refused += 1
        # 2-4. requests, rounding, layering
        opened = pl.slot(obs)
        # 5. releases due at t (§6.6), then the purchases of the columns opened at t
        for lid in self.release_at.pop(t, ()):
            if lid in obs.leases:
                self.book.release(lid)
                self.n_released += 1
        for col in opened:
            l, j, k, s, iota, L = pl.column(col)
            self.book.buy(col, Buy(l, k, j, 1, tag="a2"))
        return self.book.assemble(obs, self.view)

    def opened_ref(self) -> dict:
        """{ref_key: opening slot} of the opened columns (round_pd(...)['opened'] on core instances)."""
        return self.planner.rounder.opened_ref()

    def report(self) -> dict:
        out = self.planner.report()
        out["leases"] = {"bought": self.n_bought, "released": self.n_released, "refused": self.n_refused}
        out["book"] = dict(self.book.stats)
        return out


__all__ = ["A2Planner", "A2", "VIEW_TRANSFORMS", "PX_KEYS", "RENEW_LOAD", "check_params", "live_renewals",
           "resolve_px"]
