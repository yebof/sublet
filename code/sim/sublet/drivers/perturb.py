"""E4's predictions: perturbations of the previous-day prediction and the full-model q-eta (design/sim_spec_ms4.md
§6.4, §6.8; open choices M11, M12; deliverable D34, unit U23).

The base predictor is drivers.predict.previous_day: d-hat_c(f) = d_c(f - 1440 / Δf), none on day 0 (MS2 spec M38).
`prediction(demand, key, ...)` applies one perturbation per day d >= 1 to that prediction w-hat_d of each client, on
the fast slots f of the day (Δf = 5 min in E4); PREDICTIONS lists E4's 13 predictions by their id key (§6.4):

  key        kind          parameter       definition on day d
  prev       previous_day  -               w-hat_d (the unperturbed prediction: phase 0)
  phase<s>   phase         s min           w-hat_d(f - s / Δf) for f >= s / Δf; the first s / Δf slots of the day are 0
                                           (no wrap); s in {15, 30, 60, 120}
  amp<a>     amplitude     a               a w-hat_d; a in {0.5, 0.75, 1.25, 1.5}
  del_p90    burst_delete  P90             min{w-hat_d, P90(w-hat_d)}, the client's P90 over the day's fast slots
  inj3x30    burst_inject  3 x 30 min, P99 max{w-hat_d, P99(w-hat_d)} on 3 windows of 30 min, else w-hat_d; the window
                                           starts are rng.integers(0, F - w + 1, size=3) with rng =
                                           np.random.default_rng((c, d)) (alignment c, day d: the same for every
                                           policy and seed; F fast slots of the day, w of the window; windows may
                                           overlap; a day shorter than a window is one window)
  empty      empty         -               0
  exact      exact         -               w_d, the realized day (the oracle: the point eta = 0)
Day 0 has no prediction under every key (zero), as under the base predictor. Percentiles are numpy's (linear
interpolation) over one client's fast slots of the day. The burst parameters are build defaults (M11; design §5.5 E4
names the kinds only). `none` (NONE_KEY) is the key of A6 without predictions, which has no predicted demand.

Information classes (MS2 spec §13.1, §6.4): the unperturbed prediction keeps 'previous-day'; a perturbed one is
labeled 'perturbation:<kind>:<par>' ('perturbation:empty' without a parameter) and the oracle 'exact': evaluation
devices derived from the realized demand (design §5.4), recorded with the run (LABELS, label()).

q-eta (M12, §6.8): the full-model analogue of C3-L10's q eta = q |sigma triangle sigma-hat| on day d,
  q eta_d = sum_c sum_{t in d} (q_{j_c} / u) (Δs / 60) |k_c(t) - k-hat_c(t)|,
with k_c(t) and k-hat_c(t) the active units of client c in slow slot t for the slot maxima of the realized and of the
predicted demand (instance.active_units), q_{j_c} in USD per replica-load-hour and u the units per replica: the
weighted |sigma triangle sigma-hat|, since active units are nested prefixes (the core form is
experiments/repro_c5_la.py's (I.active ^ Ip.active).sum()). eta_q(inst, demand, pred, day) gives it.
"""
from __future__ import annotations

import hashlib
from typing import Optional

import numpy as np

from ..instance import active_units
from .predict import previous_day

KINDS = ("previous_day", "phase", "amplitude", "burst_delete", "burst_inject", "empty", "exact")
PHASES_MIN = (15, 30, 60, 120)
AMPLITUDES = (0.5, 0.75, 1.25, 1.5)
DELETE_Q = 90                       # burst_delete: the day's P90
INJECT = (3, 30, 99)                # burst_inject: 3 windows of 30 min raised to the day's P99
NONE_KEY = "none"                   # A6 without predictions (no predicted demand)
# the 13 predictions of E4 in the order of §6.4: id key -> (kind, parameter)
PREDICTIONS: dict[str, tuple[str, object]] = {
    "prev": ("previous_day", None),
    **{f"phase{s}": ("phase", s) for s in PHASES_MIN},
    **{f"amp{a:g}": ("amplitude", a) for a in AMPLITUDES},
    "del_p90": ("burst_delete", DELETE_Q),
    "inj3x30": ("burst_inject", INJECT),
    "empty": ("empty", None),
    "exact": ("exact", None),
}


def spec(key: str) -> tuple[str, object]:
    """(kind, parameter) of a prediction key of PREDICTIONS; ValueError for any other key."""
    if key not in PREDICTIONS:
        raise ValueError(f"unknown prediction key {key!r}; known {list(PREDICTIONS)}")
    return PREDICTIONS[key]


def label(key: str) -> str:
    """The information-class label of a prediction key (§6.4): 'previous-day', 'perturbation:<kind>:<par>'
    ('perturbation:phase:15', 'perturbation:amplitude:0.5', 'perturbation:burst_delete:P90',
    'perturbation:burst_inject:3x30min-P99', 'perturbation:empty'), 'exact', or 'none' for NONE_KEY."""
    if key == NONE_KEY:
        return NONE_KEY
    kind, par = spec(key)
    if kind == "previous_day":
        return "previous-day"
    if kind == "exact":
        return "exact"
    if kind == "empty":
        return "perturbation:empty"
    if kind == "phase":
        return f"perturbation:phase:{int(par)}"
    if kind == "amplitude":
        return f"perturbation:amplitude:{float(par):g}"
    if kind == "burst_delete":
        return f"perturbation:burst_delete:P{int(par)}"
    n, minutes, q = par
    return f"perturbation:burst_inject:{int(n)}x{int(minutes)}min-P{int(q)}"


LABELS: dict[str, str] = {**{k: label(k) for k in PREDICTIONS}, NONE_KEY: NONE_KEY}


def inject_starts(c: int, d: int, n_fast: int, n_bursts: int, width: int) -> np.ndarray:
    """The window starts of burst_inject on day d at alignment c: rng.integers(0, n_fast - width + 1, size=n_bursts)
    with rng = np.random.default_rng((c, d)) (0 only if the day is not longer than a window)."""
    rng = np.random.default_rng((int(c), int(d)))
    return rng.integers(0, max(0, int(n_fast) - int(width)) + 1, size=int(n_bursts)).astype(np.int64)


def perturb_day(w: np.ndarray, kind: str, par=None, *, fast_min: int, realized: Optional[np.ndarray] = None,
                c: Optional[int] = None, d: Optional[int] = None) -> np.ndarray:
    """One day of a prediction (n, F): the perturbation `kind` with parameter `par` of the day's previous-day
    prediction `w` (module docstring); `realized` is the realized day (kind 'exact'), (c, d) the alignment and the
    day (kind 'burst_inject'), fast_min the fast slot in minutes (Δf)."""
    w = np.asarray(w, dtype=np.float64)
    if w.ndim != 2:
        raise ValueError(f"perturb_day: the day's prediction must be (n, F), got shape {w.shape}")
    F = w.shape[1]
    if kind == "previous_day":
        return w.copy()
    if kind == "empty":
        return np.zeros_like(w)
    if kind == "exact":
        if realized is None:
            raise ValueError("perturb_day: kind 'exact' needs the realized day")
        r = np.asarray(realized, dtype=np.float64)
        if r.shape != w.shape:
            raise ValueError(f"perturb_day: realized day {r.shape} != prediction {w.shape}")
        return r.copy()
    if kind == "amplitude":
        a = float(par)
        if not np.isfinite(a) or a < 0:
            raise ValueError(f"perturb_day: amplitude must be a finite number >= 0, got {par!r}")
        return a * w
    if kind == "phase":
        s = int(par)
        if s < 0 or s % int(fast_min):
            raise ValueError(f"perturb_day: phase {par!r} min is not a non-negative multiple of Δf = {fast_min} min")
        k = s // int(fast_min)
        out = np.zeros_like(w)
        if k < F:
            out[:, k:] = w[:, :F - k]
        return out
    if F == 0:
        return w.copy()
    if kind == "burst_delete":
        p = np.percentile(w, float(par), axis=1, keepdims=True)
        return np.minimum(w, p)
    if kind == "burst_inject":
        n_b, minutes, q = par
        if int(minutes) % int(fast_min):
            raise ValueError(f"perturb_day: a burst of {minutes} min is not a multiple of Δf = {fast_min} min")
        if c is None or d is None:
            raise ValueError("perturb_day: kind 'burst_inject' needs the alignment c and the day d")
        width = int(minutes) // int(fast_min)
        p = np.percentile(w, float(q), axis=1, keepdims=True)
        out = w.copy()
        for s0 in inject_starts(c, d, F, n_b, width):
            out[:, s0:s0 + width] = np.maximum(out[:, s0:s0 + width], p)
        return out
    raise ValueError(f"perturb_day: unknown kind {kind!r}; known {list(KINDS)}")


def prediction(demand: np.ndarray, key: str, *, day_fast: int, fast_min: int, c: int) -> np.ndarray:
    """(n, T_fast) predicted demand of prediction `key` (PREDICTIONS) for the realized demand `demand` (n, T_fast):
    previous_day(demand, day_fast), then perturb_day on every day d >= 1 (the last day may be shorter); day 0 has no
    prediction (zero). day_fast = fast slots per day (1440 / Δf on the week), fast_min = Δf, c the alignment (the
    draws of burst_inject)."""
    kind, par = spec(key)
    d = np.asarray(demand, dtype=np.float64)
    day_fast = int(day_fast)
    base = previous_day(d, day_fast)
    out = np.zeros_like(base)
    T = d.shape[1]
    for day in range(1, -(-T // day_fast)):
        a, b = day * day_fast, min(T, (day + 1) * day_fast)
        out[:, a:b] = perturb_day(base[:, a:b], kind, par, fast_min=fast_min, realized=d[:, a:b], c=c, d=day)
    return out


def pred_sha256(pred: np.ndarray) -> str:
    """sha256 of a predicted demand (float64 bytes, C order), as instance.with_demand records a demand."""
    return hashlib.sha256(np.ascontiguousarray(np.asarray(pred, dtype=np.float64)).tobytes()).hexdigest()


def _active(inst, demand: np.ndarray, t0: int, t1: int) -> np.ndarray:
    g = inst.grid
    d = np.asarray(demand, dtype=np.float64)
    if d.shape != (inst.n, g.T_fast):
        raise ValueError(f"eta_q: demand has shape {d.shape}, expected {(inst.n, g.T_fast)}")
    D = d.reshape(inst.n, g.T_slow, g.phi).max(axis=2)[:, t0:t1] if inst.n else np.zeros((0, t1 - t0))
    return active_units(D, inst.units_per_replica)


def eta_q(inst, demand: np.ndarray, pred: np.ndarray, day: int, day_slots: Optional[int] = None) -> float:
    """q eta_d of §6.8 (M12) in USD: sum over clients c and slow slots t of day `day` (slots [day ds, (day + 1) ds),
    ds = day_slots, default 1440 / Δs; the last day may be shorter) of (q_{j_c} / u) (Δs / 60) |k_c(t) - k-hat_c(t)|,
    with k and k-hat the active units (instance.active_units) of the slot maxima of `demand` and `pred` (both
    (n, T_fast)). ValueError for a day outside the horizon."""
    g = inst.grid
    ds = int(day_slots) if day_slots is not None else 1440 // g.slow_min
    t0 = int(day) * ds
    if ds < 1 or int(day) < 0 or t0 >= g.T_slow:
        raise ValueError(f"eta_q: day {day} of {ds} slow slots is outside the horizon of {g.T_slow} slots")
    t1 = min(g.T_slow, t0 + ds)
    k, kh = _active(inst, demand, t0, t1), _active(inst, pred, t0, t1)
    q = np.array([inst.llms[int(j)].q_usd_per_h for j in np.asarray(inst.clients.llm, dtype=np.int64)],
                 dtype=np.float64)
    w = q / inst.units_per_replica * g.slow_min / 60.0
    return float((w[:, None] * np.abs(k - kh)).sum())


def eta_q_days(inst, demand: np.ndarray, pred: np.ndarray, day_slots: Optional[int] = None) -> list[float]:
    """eta_q of every day of the horizon, day 0 first."""
    g = inst.grid
    ds = int(day_slots) if day_slots is not None else 1440 // g.slow_min
    return [eta_q(inst, demand, pred, d, ds) for d in range(-(-g.T_slow // ds))]


__all__ = ["KINDS", "PHASES_MIN", "AMPLITUDES", "DELETE_Q", "INJECT", "NONE_KEY", "PREDICTIONS", "LABELS", "label",
           "spec", "inject_starts", "perturb_day", "prediction", "pred_sha256", "eta_q", "eta_q_days"]
