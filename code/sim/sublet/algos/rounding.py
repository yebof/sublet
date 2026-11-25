"""Threshold rounding of the ORML-PD and capacity layering (design/sim_spec_ms2.md §6.1-§6.5).

Rounder: lazy thresholds theta_F = 1 - U^(1/r-bar), one uniform U per column drawn at the first
request whose candidate list contains it, in candidate order (M8); per request (right after its PD
step) the threshold openings, the analysed rule (reported) and the practical rule with its fix-up
purchase (executed), as `pd.round_pd` (C3-T2). Refused purchases leave the opened set (§6.5).
Practical Sublet's knobs (design/q44_practical_sublet.md §2.1, §6.1), off by default: S
(`suppress_covered`: the practical threshold openings of a covered request are skipped, while the
analysed threshold flags and cost_an stay those of the unmodified rule) and the renewal mark of R
(`mark_open`).

Layering: the replica index iota of §6.4 (a replica carries u units of 1/u load), deterministic
hosting of units per (l, j, k); inactive (one index) when kappa_infinite.

This module imports only numpy, the standard library and sublet.algos.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

from .common import PolicyError
from .pd_core import RequestOut, VecPD


def rbar_theory(N_bound: int) -> int:
    """C3-T2's rounding count r-bar = ceil(2 ln max(N_bound, 3))."""
    if isinstance(N_bound, bool) or not isinstance(N_bound, (int, np.integer)) or N_bound < 1:
        raise PolicyError(f"N_bound must be an integer >= 1, got {N_bound!r}")
    return int(math.ceil(2 * math.log(max(int(N_bound), 3))))


# ---------------------------------------------------------------- layering (§6.4)
class Layering:
    """Hosted sets host[l, j, k][iota] of units (c, v); a unit is hosted at most once.

    iota(unit, l, j, k): the index whose host set contains the unit, else the smallest index with
    fewer than u units (a new index if all are full). assign(unit, key): the unit leaves its host set
    and, for a column key (l, j, k, s, iota), joins host[l, j, k][iota]; None (fallback) only removes
    it. end_slot(active): units not active in the slot leave their host sets. Inactive: every iota is
    0 and nothing is kept. `shape` = (m, J, K) (optional, an addition to §3.4) keeps the smallest
    free index per (l, j, k) in an array for `iota_vec`."""

    def __init__(self, u: int, active: bool, shape: Optional[tuple[int, int, int]] = None):
        if isinstance(u, bool) or not isinstance(u, (int, np.integer)) or u < 1:
            raise PolicyError(f"Layering: u must be an integer >= 1, got {u!r}")
        self.u = int(u)
        self.active = bool(active)
        self._host: dict[tuple[int, int, int], list[set]] = {}
        self._where: dict[tuple, tuple[tuple[int, int, int], int]] = {}
        self._free: dict[tuple[int, int, int], int] = {}      # only keys with free index > 0
        self._free_arr = np.zeros(shape, dtype=np.int64) if (shape is not None and self.active) else None
        self.max_iota = 0

    def _set_free(self, key: tuple[int, int, int]) -> None:
        hs = self._host.get(key, [])
        fr = next((i for i, h in enumerate(hs) if len(h) < self.u), len(hs))
        if fr:
            self._free[key] = fr
        else:
            self._free.pop(key, None)
        if self._free_arr is not None:
            self._free_arr[key] = fr

    def iota(self, unit: tuple[int, int], l: int, j: int, k: int) -> int:
        if not self.active:
            return 0
        key = (int(l), int(j), int(k))
        w = self._where.get(unit)
        if w is not None and w[0] == key:
            return w[1]
        return self._free.get(key, 0)

    def iota_vec(self, unit: tuple[int, int], j: int, ls: np.ndarray, ks: np.ndarray) -> np.ndarray:
        """iota(unit, l, j, k) for every candidate pair (ls[i], ks[i]) of LLM j (needs `shape`)."""
        if not self.active:
            return np.zeros(len(ls), dtype=np.int64)
        if self._free_arr is None:
            return np.fromiter((self.iota(unit, int(l), j, int(k)) for l, k in zip(ls, ks)), np.int64, len(ls))
        out = self._free_arr[ls, int(j), ks] if self._free else np.zeros(len(ls), dtype=np.int64)
        w = self._where.get(unit)
        if w is not None and w[0][1] == int(j):
            (l, _j, k), io = w
            hit = np.nonzero((ls == l) & (ks == k))[0]
            if len(hit):
                out = out.copy()
                out[hit] = io
        return out

    def _remove(self, unit) -> None:
        w = self._where.pop(unit, None)
        if w is None:
            return
        key, io = w
        self._host[key][io].discard(unit)
        self._set_free(key)

    def assign(self, unit: tuple[int, int], col_key: Optional[tuple]) -> None:
        if not self.active:
            return
        self._remove(unit)
        if col_key is None or isinstance(col_key[0], str):
            return                                    # fallback (or a predicted column: not hosted)
        l, j, k, _s, io = (int(v) for v in col_key[:5])
        key = (l, j, k)
        hs = self._host.setdefault(key, [])
        while len(hs) <= io:
            hs.append(set())
        hs[io].add(unit)
        self._where[unit] = (key, io)
        self.max_iota = max(self.max_iota, io)
        self._set_free(key)

    def end_slot(self, active_units: set) -> None:
        if not self.active:
            return
        for unit in [u for u in self._where if u not in active_units]:
            self._remove(unit)

    def hosted(self) -> int:
        """Number of hosted units."""
        return len(self._where)


# ---------------------------------------------------------------- rounder (§6.1-§6.3, §6.5)
class Rounder:
    """Threshold rounding fed request by request by a VecPD (pd.round_pd's rules, §6.2).

    process(out, unit) returns the column ids opened at out.t by this request: threshold openings in
    candidate order, then the practical fix-up. The request's practical assignment (column key, or
    None for fallback) is left in `last_assignment`. Accounting: cost_an (analysed rule),
    cost_pr and curve (practical rule: purchases and service per slot), n_fix_an, opened
    (id -> opening slot, refused columns removed), refused (id -> (opening slot, refusal slot)).

    Knob S (`suppress_covered`, default False; design/q44_practical_sublet.md §2.1 step 3): if some
    candidate of a request crosses its threshold while the request already has an opened candidate F
    with delta_F < q, no candidate of the request is opened by its threshold. The analysed rule keeps
    its own threshold flags (`_thr`) and cost_an, charged at every first crossing as without the
    knob; the practical threshold openings use separate flags (`_thr_pr`), and a suppressed
    candidate is not flagged there, so a later uncovered request can still open it. Counter
    n_suppressed (suppressed threshold crossings). `mark_open` (knob R): a column realized by a
    renewed live lease enters the opened set with no cost and no threshold flag; counter n_renewed."""

    def __init__(self, pd: VecPD, rng: np.random.Generator, rbar: int):
        if isinstance(rbar, bool) or not isinstance(rbar, (int, np.integer)) or rbar < 1:
            raise PolicyError(f"Rounder: rbar must be an integer >= 1, got {rbar!r}")
        self.pd = pd
        self.rng = rng
        self.rbar = int(rbar)
        cap = len(pd.x)
        self._theta = np.full(cap, np.nan)
        self._thr = np.zeros(cap, dtype=bool)        # threshold-opened (analysed rule; also practical without S)
        self._thr_pr = np.zeros(cap, dtype=bool)     # practical threshold openings under knob S
        self._open = np.zeros(cap, dtype=bool)       # opened (practical rule), refused removed
        self.opened: dict[int, int] = {}
        self.refused: dict[int, tuple[int, int]] = {}
        self.cost_an = 0.0
        self.cost_pr = 0.0
        self.curve = np.zeros(pd.T)
        self.n_fix_an = 0
        self.n_draws = 0
        self.n_fixups = 0
        self.last_assignment: Optional[tuple] = None
        self.last_col: Optional[int] = None
        self.suppress_covered = False                # knob S (practical Sublet), off by default
        self.n_suppressed = 0
        self.n_renewed = 0

    def _ensure(self, n: int) -> None:
        cap = len(self._theta)
        if n <= cap:
            return
        new = max(n, 2 * cap)
        th = np.full(new, np.nan)
        th[:cap] = self._theta
        self._theta = th
        for name in ("_thr", "_thr_pr", "_open"):
            a = getattr(self, name)
            b = np.zeros(new, dtype=bool)
            b[:cap] = a
            setattr(self, name, b)

    def theta(self, col: int) -> Optional[float]:
        """Threshold of a column, None if not drawn yet."""
        col = int(col)
        if col >= len(self._theta) or np.isnan(self._theta[col]):
            return None
        return float(self._theta[col])

    def _open_col(self, col: int, t: int) -> None:
        self._open[col] = True
        self.opened[col] = t

    def process(self, out: RequestOut, unit=None) -> list[int]:
        self._ensure(self.pd.n_ids)
        ids, t = out.cols, int(out.t)
        x, y, f, dl, C, q = out.x, out.y, float(out.f), out.delta, out.C, float(out.q)
        th = self._theta[ids]
        new = np.isnan(th)
        if new.any():
            inv = 1.0 / self.rbar
            for i in np.nonzero(new)[0]:
                v = 1.0 - self.rng.random() ** inv
                self._theta[ids[i]] = v
                th[i] = v
            self.n_draws += int(new.sum())
        opened_now: list[int] = []
        # 1. threshold openings, in candidate order
        hits = np.nonzero(~self._thr[ids] & (x > th))[0]
        if not self.suppress_covered:
            for i in hits:
                col = int(ids[i])
                self._thr[col] = True
                cst = float(C[i])
                self.cost_an += cst
                if not self._open[col]:
                    self._open_col(col, t)
                    self.cost_pr += cst
                    self.curve[t] += cst
                    opened_now.append(col)
        else:
            # knob S: the analysed flags and cost_an exactly as above; practical openings on their own flags
            for i in hits:
                self._thr[int(ids[i])] = True
                self.cost_an += float(C[i])
            hp = np.nonzero(~self._thr_pr[ids] & (x > th))[0]
            if len(hp):
                if bool((self._open[ids] & (dl < q)).any()):
                    self.n_suppressed += len(hp)
                else:
                    for i in hp:
                        col = int(ids[i])
                        self._thr_pr[col] = True
                        if not self._open[col]:
                            cst = float(C[i])
                            self._open_col(col, t)
                            self.cost_pr += cst
                            self.curve[t] += cst
                            opened_now.append(col)
        # 2. analysed rule (reported, not executed)
        if f >= 0.5:
            self.cost_an += q
        else:
            usable = np.minimum(x, y) > th
            if usable.any():
                self.cost_an += float(dl[usable].min())
            else:
                self.n_fix_an += 1
                self.cost_an += min(q, float((C + dl).min())) if len(ids) else q
        # 3. practical rule (executed): the first candidate with the smallest cost below q
        self.last_assignment, self.last_col = None, None
        if len(ids):
            op = self._open[ids]
            cc = np.where(op, dl, C + dl)
            i = int(np.argmin(cc))
            if cc[i] < q:
                col = int(ids[i])
                self.last_col = col
                self.last_assignment = self.pd.col_key(col)
                if not op[i]:
                    self._open_col(col, t)
                    cst = float(C[i])
                    self.cost_pr += cst
                    self.curve[t] += cst
                    best = float(cc[i]) - cst
                    self.cost_pr += best
                    self.curve[t] += best
                    opened_now.append(col)
                    self.n_fixups += 1
                else:
                    self.cost_pr += float(cc[i])
                    self.curve[t] += float(cc[i])
                return opened_now
        self.cost_pr += q
        self.curve[t] += q
        return opened_now

    def mark_open(self, col: int, t: int) -> bool:
        """Knob R (design/q44_practical_sublet.md §2.1 step 2): a live lease that is renewed realizes
        column `col` at slot t. The column enters the opened set at no cost: nothing is added to
        cost_pr, cost_an or the curve, and no threshold flag is set. Returns False (and changes
        nothing) if the column is already open."""
        col = int(col)
        self._ensure(col + 1)
        if self._open[col]:
            return False
        self._open_col(col, int(t))
        self.n_renewed += 1
        return True

    def refuse(self, col: int, t: int) -> None:
        """A refused purchase (§6.5): the column leaves the opened set (the practical rule no longer
        routes through it); its C_F stays in cost_pr (M11)."""
        col = int(col)
        self._ensure(col + 1)
        t0 = self.opened.pop(col, None)
        self._open[col] = False
        self.refused[col] = (t0 if t0 is not None else -1, int(t))

    def is_open(self, col: int) -> bool:
        col = int(col)
        return col < len(self._open) and bool(self._open[col])

    def opened_ref(self) -> dict:
        """{ref_key: opening slot} of the opened columns (the shape of round_pd(...)['opened'])."""
        return {self.pd.ref_key(c): t for c, t in self.opened.items()}

    def report(self) -> dict:
        return {"rbar": self.rbar, "cost_pr": self.cost_pr, "cost_an": self.cost_an, "n_fix_an": self.n_fix_an,
                "curve": self.curve.tolist(), "opened": len(self.opened), "refused": len(self.refused),
                "fixups": self.n_fixups, "draws": self.n_draws}


__all__ = ["rbar_theory", "Layering", "Rounder"]
