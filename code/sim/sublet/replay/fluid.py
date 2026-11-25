"""The fluid mode of E8's replay, check E8-2 (design/sim_spec_ms4.md §7.4, §7.9).

The replay's accounting fed the instance's per-fast-slot demand d(f) as rates (no requests): d(f) kappa_j Delta_f
weighted tokens per fast slot, capacity kappa_j W_l(f) Delta_f at each site with an arc, cheapest-first routing over
the sites in delta order (loop.Placement.order, the order of the request-level loop), which for the one client of
E8's instance is the engine's min-cost routing (engine._route: all to the cheapest site if it fits, else
cheapest-first). Costs go through loop.token_costs, the request-level replay's cost function, so that E8-2 tests the
replay's placement input (W, delta, arcs) and its units against the engine's ledger: the routing and fallback
components must agree to 1e-6 relative. Stranding has no request state here; the fluid mode books the engine's
charge mu_fb_j max(r X(f - 1) - X(f), 0) per fast slot, r = min(d(f - 1), d(f)) / d(f - 1) (engine.py, ledger step),
and it is compared and reported. Relative differences are taken over max(|engine|, 1e-9 USD).
"""
from __future__ import annotations

import numpy as np

from .loop import Placement, ServiceModel, token_costs

E8_2_TOL = 1e-6
E8_2_FLOOR_USD = 1e-9          # floor of the denominator: a component below a nano-dollar is round-off, not a cost


def fluid_mode(d: np.ndarray, plan: Placement, svc: ServiceModel) -> dict:
    """The fluid mode on demand d (T_fast,) in replica loads: x (m, T_fast) routed load in replica loads, b (T_fast,)
    fallback load, the tokens and the costs (loop.token_costs), with the engine's stranding_fb of this routing."""
    d = np.asarray(d, dtype=np.float64)
    T = plan.T_fast
    if d.shape != (T,):
        raise ValueError(f"fluid_mode: demand of shape {d.shape}, the placement has {T} fast slots")
    order = plan.order
    per = svc.kappa_wtok_per_min * plan.fast_min            # weighted tokens of one replica load over one fast slot
    cap = plan.W[order] * per                                # (k, T)
    dem = d * per
    x_tok = np.zeros((plan.m, T))
    if len(order):
        before = np.cumsum(cap, axis=0) - cap
        x_tok[order] = np.clip(dem[None, :] - before, 0.0, cap)
    fb_tok = np.maximum(dem - x_tok.sum(axis=0), 0.0)
    x = x_tok / per
    X = x.sum(axis=0)
    d_prev = np.concatenate(([0.0], d[:-1]))
    X_prev = np.concatenate(([0.0], X[:-1]))
    ratio = np.divide(np.minimum(d_prev, d), d_prev, out=np.zeros(T), where=d_prev > 0)
    wv = np.maximum(ratio * X_prev - X, 0.0)
    costs = token_costs(x_tok.sum(axis=1), float(fb_tok.sum()), float(wv.sum()) * svc.n_seq, plan, svc)
    return {"x": x, "b": fb_tok / per, "tokens": {"demand": float(dem.sum()), "routed": float(x_tok.sum()),
                                                  "fallback": float(fb_tok.sum())},
            "stranded_loads": float(wv.sum()), "costs": costs}


def _rel(a: float, b: float) -> float:
    """|a - b| / max(|b|, E8_2_FLOOR_USD)."""
    return abs(a - b) / max(abs(b), E8_2_FLOOR_USD)


def check_e8_2(res, inst, plan: Placement, svc: ServiceModel, tol: float = E8_2_TOL) -> dict:
    """E8-2 on one fluid run: the fluid mode of the instance's demand against the engine's components. pass iff
    routing and fallback agree to `tol` relative (|fluid mode - engine| / max(|engine|, 1e-9 USD), so that two
    components that are 0 up to round-off agree); stranding (the engine's stranding_fb) is compared and reported, with
    the largest per-slot differences of x and b against RunResult.routing."""
    fm = fluid_mode(np.asarray(inst.clients.demand[0], dtype=np.float64), plan, svc)
    eng = res.components
    c = fm["costs"]
    rr, rf = _rel(c["routing"], float(eng["routing"])), _rel(c["fallback"], float(eng["fallback"]))
    rs = _rel(c["stranding"], float(eng["stranding_fb"]))
    out = {"pass": bool(rr <= tol and rf <= tol), "tol": tol, "floor_usd": E8_2_FLOOR_USD,
           "routing": {"fluid_mode": c["routing"], "engine": float(eng["routing"]), "rel_diff": _finite(rr),
                       "abs_diff": abs(c["routing"] - float(eng["routing"]))},
           "fallback": {"fluid_mode": c["fallback"], "engine": float(eng["fallback"]), "rel_diff": _finite(rf),
                        "abs_diff": abs(c["fallback"] - float(eng["fallback"]))},
           "stranding": {"fluid_mode": c["stranding"], "engine_fb": float(eng["stranding_fb"]),
                         "engine_total": float(eng["stranding"]), "rel_diff": _finite(rs),
                         "abs_diff": abs(c["stranding"] - float(eng["stranding_fb"])), "reported": True},
           "stranding_other_components": {k: float(eng[k]) for k in ("stranding_kv", "stranding_fl", "stranding_pi")}}
    if res.routing is not None:
        j = int(inst.clients.llm[0])
        xr = np.zeros((plan.m, plan.T_fast))
        for (cl, l), arr in res.routing["x"].items():
            if cl == 0:
                xr[l] = arr
        out["max_abs_diff_x"] = float(np.max(np.abs(xr - fm["x"]))) if xr.size else 0.0
        out["max_abs_diff_b"] = float(np.max(np.abs(np.asarray(res.routing["b"][0]) - fm["b"])))
        out["llm"] = j
    return out


def _finite(v: float):
    return None if not np.isfinite(v) else float(v)


__all__ = ["E8_2_TOL", "E8_2_FLOOR_USD", "fluid_mode", "check_e8_2"]
