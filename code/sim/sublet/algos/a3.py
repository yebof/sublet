"""Policy A3: ORML-PD with rounding, executed through the execution layer (design/sim_spec_ms2.md §7.5).

At slow slot t: steps 1-4 of A2 (a2.A2Planner: refusals, the slot's requests through the PD,
rounding, capacity layering), with every column opened at t passed to
`layer.open((l, j, k, iota), t0=t, s=s, L=L_k)` instead of being bought; then `layer.step(obs)`
(X1 renewal, X2 release, X3 rotation, X4 through the reclaim handler); `act` returns
`book.assemble(obs, view)`.

A purchase of a logical slot at its own site l0 that is refused (pre-check drop or engine refusal,
reported at t + 1) refuses the PD column of the window that covers its purchase slot (§6.5), if
that column is still open; the refused column leaves the opened set, so its window leaves the
slot's coverage (layer.drop_window, M11: no retry). A refused purchase elsewhere (a rotated site)
refuses no column, and the slot retries at its next needed slot (§7.2 step 7).

Reference mode (tests, E1's comparison with c3_benchmark.txt): x3=False, x2='reference',
reaction='cold'. On from_core instances this is RenewReplay of the same opened map
(pd.real_cost_renew's semantics). Status: real cost <= 2 x accounted cost VERIFIED NUMERICALLY on
c3/out/c3_benchmark.txt (c) for this mode only; with X2's timer or X3 there is no check (heuristic).
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from ..policies.base import Policy
from ..types import PublicView, SlowObs
from .a2 import A2, A2Planner, check_params
from .common import LeaseBook, PolicyError, policy_streams, resolve_params
from .execution import ExecutionLayer, SiteRule
from .handler import REACTIONS, ReclaimHandler

X_PARAMS = {"x1": True, "x2": "reference", "x3": True, "zeta": 2.0, "skip_rule": True,
            "reaction": "c2sw", "switch": "c2sw"}


def check_x_params(p: dict, who: str) -> None:
    """Values of the execution-layer parameters (§4.2); PolicyError otherwise."""
    for b in ("x1", "x3", "skip_rule"):
        if not isinstance(p[b], (bool, np.bool_)):
            raise PolicyError(f"{who}: {b} must be a bool, got {p[b]!r}")
    if p["x2"] not in ("reference", "timer"):
        raise PolicyError(f"{who}: x2 must be 'reference' or 'timer', got {p['x2']!r}")
    z = p["zeta"]
    if isinstance(z, bool) or not isinstance(z, (int, float, np.integer, np.floating)) or not float(z) >= 1.0:
        raise PolicyError(f"{who}: zeta must be a number >= 1, got {z!r}")
    if p["reaction"] not in REACTIONS or p["reaction"] == "test_a":
        raise PolicyError(f"{who}: reaction must be one of {[r for r in REACTIONS if r != 'test_a']}, "
                          f"got {p['reaction']!r} (test (a) needs predictions: A6)")
    if p["switch"] not in ("c2sw", "beta"):
        raise PolicyError(f"{who}: switch must be 'c2sw' or 'beta', got {p['switch']!r}")


class A3(Policy):
    """A2's planner executed by the execution layer (§7.5). Driver input: N_bound (rbar='theory')."""
    name = "A3"
    PARAMS = {**A2.PARAMS, **X_PARAMS}
    INPUTS = ("N_bound",)
    TAG = "a3"

    def __init__(self, **kw):
        self._params, inputs = resolve_params(self.PARAMS, kw, self.name, inputs=self.INPUTS)
        check_params(self._params, self.name)
        check_x_params(self._params, self.name)
        if self._params["rbar"] == "theory" and inputs.get("N_bound") is None:
            raise PolicyError(f"{self.name}: rbar='theory' needs the driver input N_bound (§6.3)")
        self.N_bound = inputs.get("N_bound")

    def params(self) -> dict:
        return dict(self._params)

    # -------------------------------------------------------- construction
    def _site_rule(self, view: PublicView, streams: dict) -> Optional[SiteRule]:
        """The layer's site rule: None = X3's RRSiteRule (A4 overrides)."""
        return None

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        p = self._params
        streams = policy_streams(rng)
        self.planner = A2Planner(view, streams["main"], streams["order"], rbar=p["rbar"], N_bound=self.N_bound,
                                 d_mode=p["d_mode"], protected_window=p["protected_window"],
                                 site_order_mode=p["site_order"], root=p["root"], max_raises=p["max_raises"],
                                 layering=p["layering"], record=p["record"], view_transform=p["view_transform"])
        self.book = LeaseBook()
        self.handler = ReclaimHandler(view, reaction=p["reaction"], switch=p["switch"])
        self.layer = ExecutionLayer(view, self.book, x1=p["x1"], x2=p["x2"], x3=p["x3"], zeta=float(p["zeta"]),
                                    skip_rule=p["skip_rule"], site_rule=self._site_rule(view, streams),
                                    handler=self.handler, site_perm=self.planner.site_perm,
                                    protected_window=p["protected_window"], tag=self.TAG)
        self.window_col: dict[tuple, int] = {}      # (slot key, window start s) -> column id
        self.n_col_refused = 0
        self.last_cost_seen = 0.0

    # -------------------------------------------------------- one slot
    def act(self, obs: SlowObs) -> list:
        t = int(obs.t)
        pl = self.planner
        # 1. results of the last slot's purchases; refusals before this slot's requests (§6.5)
        for skey, site, t_buy, kind, reason in self.layer.absorb(self.book.begin(obs)):
            if kind != "lease" or site != skey[0]:
                continue
            L = self.layer.slots[skey].L
            s = (t_buy // L) * L
            col = self.window_col.get((skey, s))
            if col is not None and pl.rounder.is_open(col):
                pl.refuse(col, t, reason)
                self.n_col_refused += 1
                self.layer.drop_window(skey, s, t)
        # 2-4. requests, rounding, layering; the opened columns go to the layer
        for col in pl.slot(obs):
            l, j, k, s, iota, L = pl.column(col)
            key = (l, j, k, iota)
            self.layer.open(key, t0=t, s=s, L=L)
            self.window_col[(key, s)] = col
        # X1-X4
        self.layer.step(obs)
        self.last_cost_seen = float(obs.cost_so_far)
        return self.book.assemble(obs, self.view)

    def opened_ref(self) -> dict:
        """{ref_key: opening slot} of the opened columns (round_pd(...)['opened'] on core instances)."""
        return self.planner.rounder.opened_ref()

    def report(self) -> dict:
        out = self.planner.report()
        ex = self.layer.report()
        ex["columns_refused"] = self.n_col_refused
        ex["accounted_cost_pr"] = out["cost_pr"]
        ex["engine_cost_seen"] = self.last_cost_seen     # cost_so_far at the last slot's start
        out["exec"] = ex
        out["handler"] = self.handler.report()
        out["book"] = dict(self.book.stats)
        return out


__all__ = ["A3", "X_PARAMS", "check_x_params"]
