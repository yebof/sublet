"""Demand predictions and daily predicted plans (design/sim_spec_ms2.md §13.1-§13.2, M38, M39).

Predictions concern demand only (design §3.2.7). The driver computes them before the run and
hands them to A5 and A6 as constructor inputs (§4.2):
  - `previous_day`: the predicted demand of day d >= 1 is the realized demand of day d - 1; day 0
    has none (M38). The array is A6's input `pred_demand` and the demand that `plan_daily` plans.
  - `reference_noise`: the noise models of `check_c5_la.predicted` on an activity mask, for the
    reproduction tests ("reference-noise:<kind>:<par>").
  - `plan_daily`: the predicted columns (l, j, k, s) of the per-day plans of the predicted demand
    (P-hat), from the cohort MILP of `opt.milp.solve_eager` under the S36 gate, else from the LP over
    the day's aligned PD columns rounded with r-bar = 1 thresholds (M39), else none that day.
  - `plan_core`: the reference's P-hat, `core.opt_eager_cols(I, core.opt_eager(I))` (tests only).
Predicted columns are any-start columns covering [s, s + L_k) in the PD's window accounting
(§5.2); a column can occur several times, once per replica of a planned lease (§5.3, M58).
"""
from __future__ import annotations

import time
from typing import Optional

import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog

from .. import paths
from ..algos.common import column_cost, pd_window_slots, treated_as_protected, unit_costs
from ..instance import active_units, public_view, restrict_horizon, with_demand
from ..opt import milp as omilp
from ..types import Instance, Schedule

# check_c5_la.py lines 21-22 (NOISE): the nine reference predictions, each drawn with a fresh
# np.random.default_rng(12000 + seed) (check_c5_la.py:54, check_c5_la_nearest.py:23).
REFERENCE_NOISE = (("exact", 0), ("flip", 0.05), ("flip", 0.15), ("flip", 0.3), ("shift", 2), ("shift", 6),
                   ("complement", 0), ("empty", 0), ("flood", 0))
NOISE_KINDS = ("exact", "flip", "shift", "complement", "empty", "flood")
METHODS = ("auto", "milp", "lp_round")
GATE_MAX_VARS = 200_000                 # S36 gate (sim_spec.md §10): variables ...
GATE_MEM_MB = omilp.MEM_BUDGET_MB      # ... and estimated peak MB (2500)


class PredictedCols(list):
    """The predicted columns (l, j, k, s) of `plan_daily`, a plain list with the per-day record of
    the planner in `days` (method used, status, columns, sizes) and an optional label of its
    information class in `label` (set by the caller, e.g. 'previous-day', §13.1)."""

    def __init__(self, cols=(), days=None, label: Optional[str] = None):
        super().__init__(cols)
        self.days: list[dict] = list(days or [])
        self.label = label


# ---------------------------------------------------------------- predictors
def previous_day(demand: np.ndarray, day_fast: int) -> np.ndarray:
    """(n, T_fast) predicted demand: d-hat_c(f) = d_c(f - day_fast) for f >= day_fast and 0 on day 0,
    which has no prediction (M38); day_fast = 1440 / Δf fast slots per day."""
    d = np.asarray(demand, dtype=np.float64)
    if d.ndim != 2:
        raise ValueError(f"previous_day: demand must be (n, T_fast), got shape {d.shape}")
    day_fast = int(day_fast)
    if day_fast < 1:
        raise ValueError(f"previous_day: day_fast must be >= 1, got {day_fast}")
    out = np.zeros_like(d)
    if d.shape[1] > day_fast:
        out[:, day_fast:] = d[:, :-day_fast]
    return out


def reference_noise(active: np.ndarray, kind: str, par, rng: Optional[np.random.Generator]) -> np.ndarray:
    """`check_c5_la.predicted` (lines 27-41) on an activity mask (n, T): 'exact' returns the mask,
    'flip' flips each bit with probability par (one rng.random((n, T)) per call, the only draw),
    'shift' lags it by par slots (the first par slots inactive), 'complement' negates it, 'empty'
    is all False and 'flood' all True."""
    A = np.asarray(active, dtype=bool)
    if A.ndim != 2:
        raise ValueError(f"reference_noise: mask must be (n, T), got shape {A.shape}")
    if kind == "exact":
        return A.copy()
    if kind == "flip":
        if rng is None:
            raise ValueError("reference_noise: kind 'flip' needs a generator")
        return A ^ (rng.random(A.shape) < par)
    if kind == "shift":
        s = int(par)
        if s < 0:
            raise ValueError(f"reference_noise: shift must be >= 0, got {par}")
        if s == 0:
            return A.copy()
        out = np.zeros_like(A)
        if s < A.shape[1]:
            out[:, s:] = A[:, :-s]
        return out
    if kind == "complement":
        return ~A
    if kind == "empty":
        return np.zeros_like(A)
    if kind == "flood":
        return np.ones_like(A)
    raise ValueError(f"reference_noise: unknown kind {kind!r}; known {list(NOISE_KINDS)}")


def predicted_core(I, kind: str, par, rng: Optional[np.random.Generator]):
    """Copy of the core instance I (`I.subset()`) with the activity mask replaced by
    reference_noise(I.active, kind, par, rng), as `check_c5_la.predicted`."""
    Ip = I.subset()
    Ip.active = reference_noise(I.active, kind, par, rng)
    return Ip


def reference_predictions(I, seed: int) -> list[tuple[str, float, object]]:
    """The nine predicted core instances of check_c5_la.job for instance seed `seed`:
    [(kind, par, Ip)] in REFERENCE_NOISE order, each with a fresh default_rng(12000 + seed)."""
    return [(kind, par, predicted_core(I, kind, par, np.random.default_rng(12000 + seed)))
            for kind, par in REFERENCE_NOISE]


def plan_core(core_inst_pred) -> list[tuple[int, int, int, int]]:
    """The reference's predicted plan: core.opt_eager_cols(I_pred, core.opt_eager(I_pred)), the
    any-start columns (l, j, k, s) of an optimal integral OPT_eager solution (tests only)."""
    core = paths.import_ref("core")
    return [tuple(int(v) for v in F) for F in core.opt_eager_cols(core_inst_pred, core.opt_eager(core_inst_pred))]


# ---------------------------------------------------------------- daily plans
def _windows(view) -> np.ndarray:
    """(K,) PD windows L_k of §5.2 (protected window: M5's default)."""
    return np.array([pd_window_slots(view, k, None) for k in range(len(view.contracts))], dtype=np.int64)


def _plan_columns(plan, view_full, L: np.ndarray, o: int, T_day: int) -> list[tuple[int, int, int, int]]:
    """Predicted columns of a day plan (PlannedLease list, day-relative slots) shifted by o: one
    column (l, j, k, start + o) per replica of a revocable lease, and ceil((e - s) / L_k)
    consecutive columns s + o, s + o + L_k, ... per replica of a lease of a contract flagged by
    treated_as_protected, held over [s, e) with e its release slot or the day's end (§13.2)."""
    out = []
    for pl in plan:
        k = int(pl.contract)
        s = int(pl.start_slot)
        n = int(pl.n)
        if treated_as_protected(view_full, k):
            e = int(pl.release_slot) if pl.release_slot is not None else T_day
            e = min(max(e, s), T_day)
            Lk = int(L[k])
            starts = [s + i * Lk for i in range(-(-(e - s) // Lk))] if e > s else []
        else:
            starts = [s]
        for _ in range(n):
            for s0 in starts:
                out.append((int(pl.site), int(pl.llm), k, s0 + o))
    return out


def aligned_lp(day: Instance, *, max_vars: int = GATE_MAX_VARS, mem_budget_mb: float = GATE_MEM_MB,
               L: Optional[np.ndarray] = None) -> dict:
    """The LP of §13.2 (M39) over the day's aligned PD columns: min sum_F C_F x_F + sum delta_el z_el
    + sum q_e f_e s.t. sum_l z_el + f_e >= 1, z_el <= sum_{F covering (l, j_e, t_e)} x_F, all in
    [0, 1] (core.lp_aligned's program). Requests are the active units of the day's slot maxima;
    the identical units of one client and slot are one row with their count as weight (the same
    optimum). Columns as core.aligned_columns: (l, j) pairs with a finite-delta client of LLM j at l,
    offered contracts k, starts 0, L_k, 2 L_k, ... (day-relative), cost common.column_cost. Returns
    {'status', 'fun', 'x', 'cols', 'size'}; status 'over_gate' (no solve) if the variable count
    exceeds max_vars or the LP rule's estimate (130 + 5.4e-4 nnz MB) exceeds mem_budget_mb."""
    view = public_view(day, "I1")
    g = day.grid
    T, m, K = g.T_slow, day.m, day.K
    if L is None:
        L = _windows(view)
    q_req, d_req = unit_costs(view)
    D = day.clients.demand.reshape(day.n, T, g.phi).max(axis=2) if day.n else np.zeros((0, T))
    w = active_units(D, day.units_per_replica)
    cl_llm = np.asarray(day.clients.llm, dtype=np.int64)
    pairs = sorted({(l, int(cl_llm[c])) for c in range(day.n) for l in range(m) if np.isfinite(d_req[c, l])})
    cols, by_lj = [], {}
    for (l, j) in pairs:
        for k in range(K):
            if k not in view.sites[l].menu or not np.isfinite(view.price[l, k]):
                continue
            Lk = int(L[k])
            C = column_cost(view, l, j, k, Lk)
            for s in range(0, T, Lk):
                by_lj.setdefault((l, j), []).append((len(cols), s, min(s + Lk, T)))
                cols.append((l, j, k, s, C))
    el = [(c, t) for t in range(T) for c in range(day.n) if w[c, t] > 0]
    zidx = [(ei, l) for ei, (c, t) in enumerate(el) for l in range(m)
            if np.isfinite(d_req[c, l]) and (l, int(cl_llm[c])) in by_lj]
    nX, nZ, nE = len(cols), len(zidx), len(el)
    nV = nX + nZ + nE
    nnz = nZ + nE
    for (ei, l) in zidx:
        c, t = el[ei]
        nnz += 1 + sum(1 for (_, st, en) in by_lj[(l, int(cl_llm[c]))] if st <= t < en)
    size = {"n_vars": nV, "n_rows": nE + nZ, "nnz": nnz,
            "est_mb_lp": omilp.EST_LP_MB0 + omilp.EST_LP_MB_PER_NNZ * nnz}
    out = {"status": None, "fun": None, "x": None, "cols": cols, "size": size}
    if nV > max_vars or size["est_mb_lp"] > mem_budget_mb:
        out["status"] = "over_gate"
        return out
    if nE == 0:
        out.update(status="optimal", fun=0.0, x=np.zeros(nX))
        return out
    cost = np.zeros(nV)
    cost[:nX] = [col[4] for col in cols]
    for zi, (ei, l) in enumerate(zidx):
        c, t = el[ei]
        cost[nX + zi] = w[c, t] * d_req[c, l]
    for ei, (c, t) in enumerate(el):
        cost[nX + nZ + ei] = w[c, t] * q_req[c]
    rows, cix, vals = [], [], []
    z_of_e: dict[int, list[int]] = {}
    for zi, (ei, l) in enumerate(zidx):
        z_of_e.setdefault(ei, []).append(zi)
    r = 0
    for ei in range(nE):                          # coverage: -sum z - f <= -1
        for zi in z_of_e.get(ei, []):
            rows.append(r); cix.append(nX + zi); vals.append(-1.0)
        rows.append(r); cix.append(nX + nZ + ei); vals.append(-1.0)
        r += 1
    n_cov = r
    for zi, (ei, l) in enumerate(zidx):           # linking: z - sum x <= 0
        c, t = el[ei]
        rows.append(r); cix.append(nX + zi); vals.append(1.0)
        for (i, st, en) in by_lj[(l, int(cl_llm[c]))]:
            if st <= t < en:
                rows.append(r); cix.append(i); vals.append(-1.0)
        r += 1
    A = sp.csr_matrix((vals, (rows, cix)), shape=(r, nV))
    b = np.zeros(r)
    b[:n_cov] = -1.0
    res = linprog(cost, A_ub=A, b_ub=b, bounds=(0.0, 1.0), method="highs")
    if res.status != 0 or res.x is None:
        out["status"] = f"lp_status_{int(res.status)}"
        return out
    out.update(status="optimal", fun=float(res.fun), x=np.asarray(res.x[:nX], dtype=np.float64))
    return out


def plan_daily(inst: Instance, pred_demand: np.ndarray, *, day_slots: int, method: str = "auto",
               rng: Optional[np.random.Generator] = None) -> PredictedCols:
    """Predicted columns (l, j, k, s) of the day plans of the predicted demand (§13.2, M39).

    For each day d >= 1 (day 0 has no prediction, M38) the day instance is
    restrict_horizon(with_demand(inst, pred_demand), d * day_slots, day_slots) (the last day may be
    shorter). method 'milp', or 'auto' when opt.milp.estimate_size of OPT_eager is under the S36 gate
    (2e5 variables, 2500 MB): the plan of opt.milp.solve_eager on the slow grid (time limit and gap
    from the instance's 'bench' section), converted by `_plan_columns`. Otherwise ('lp_round'; 'auto'
    over the MILP gate; 'auto' when the MILP stops at a limit with an empty plan, i.e. HiGHS's trivial
    all-fallback incumbent) the LP of `aligned_lp`, if under the same gate, rounded with r-bar = 1:
    aligned column F is predicted iff x_F > 1 - U_F, one U_F = rng.random() per column in column
    order. A day over every gate gets no prediction; `days` of the result records each day."""
    if method not in METHODS:
        raise ValueError(f"plan_daily: unknown method {method!r}; known {list(METHODS)}")
    day_slots = int(day_slots)
    if day_slots < 1:
        raise ValueError(f"plan_daily: day_slots must be >= 1, got {day_slots}")
    g = inst.grid
    pred = np.asarray(pred_demand, dtype=np.float64)
    if pred.shape != (inst.n, g.T_fast):
        raise ValueError(f"plan_daily: pred_demand has shape {pred.shape}, expected {(inst.n, g.T_fast)}")
    view_full = public_view(inst, "I1")
    L = _windows(view_full)
    bench = inst.config.get("bench") or {}
    kw = {"time_limit_s": float(bench.get("time_limit_s", 300.0)),
          "mip_rel_gap": float(bench.get("mip_rel_gap", 1e-4))}
    out = PredictedCols()
    n_days = -(-g.T_slow // day_slots)
    if n_days <= 1:
        return out
    full = with_demand(inst, pred)
    for d in range(1, n_days):
        t0 = d * day_slots
        T_day = min(day_slots, g.T_slow - t0)
        rec = {"day": d, "t0": t0, "T": T_day}
        w0 = time.perf_counter()
        day = restrict_horizon(full, t0, T_day)
        cols: list = []
        use_milp = method == "milp"
        if method == "auto":
            est = omilp.estimate_size(day, Schedule.eager(day), grid="slow")
            rec["milp_size"] = {"n_vars": int(est["n_vars"]), "est_mb": float(est["est_mb"])}
            use_milp = est["n_vars"] <= GATE_MAX_VARS and est["est_mb"] <= GATE_MEM_MB
        use_lp = method == "lp_round" or not use_milp
        if use_milp:
            try:
                sr = omilp.solve_eager(day, grid="slow", max_vars=GATE_MAX_VARS, mem_budget_mb=GATE_MEM_MB, **kw)
            except omilp.SizeError as err:
                rec.update(method="milp", status="over_gate", note=str(err))
                sr = None
                use_lp = method == "auto"
            if sr is not None:
                rec.update(method="milp", status=int(sr.status), objective=sr.objective, gap=sr.gap)
                if sr.plan is not None:
                    cols = _plan_columns(sr.plan, view_full, L, t0, T_day)
                if method == "auto" and sr.status != 0 and not cols:
                    # stopped at a limit with an empty plan (HiGHS's trivial all-fallback incumbent):
                    # the LP substitute instead
                    rec["milp"] = {"status": int(sr.status), "status_msg": sr.status_msg,
                                   "objective": sr.objective, "dual_bound": sr.dual_bound, "gap": rec.pop("gap")}
                    use_lp = True
        if use_lp:
            lp = aligned_lp(day, L=L)
            rec.update(method="lp_round", status=lp["status"], lp_size=lp["size"], objective=lp["fun"])
            if lp["status"] == "optimal":
                if rng is None:
                    raise ValueError("plan_daily: the LP substitute needs a generator (rng) for its rounding")
                x = lp["x"]
                U = rng.random(len(lp["cols"]))
                cols = [(l, j, k, s + t0) for (l, j, k, s, _C), xv, uv in zip(lp["cols"], x, U) if xv > 1.0 - uv]
        rec["n_cols"] = len(cols)
        rec["wall_s"] = time.perf_counter() - w0
        out.extend(cols)
        out.days.append(rec)
    return out


__all__ = ["REFERENCE_NOISE", "NOISE_KINDS", "METHODS", "PredictedCols", "previous_day", "reference_noise",
           "predicted_core", "reference_predictions", "plan_core", "aligned_lp", "plan_daily"]
