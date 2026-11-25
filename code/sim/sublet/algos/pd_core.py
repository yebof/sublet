"""ORML-PD on arrays: PD problems, the vectorized fractional step and the psi-PD (design/sim_spec_ms2.md §5).

The fractional primal-dual of C3-T1 (design §3.2.2) on the truncated-column covering LP with aligned
windows, rewritten on arrays and extended to the full model's costs. Requests are processed one at
a time in a fixed order (§5.1), since requests of one slot share columns; vectorization is over the
candidates of one request. Written from the specification alone: it does not import the reference
`code/theory_checks/c3/pd.py`, against which it is checked (§2.2, §5.7).

Columns. An aligned column (l, j, k, s) with replica index iota covers [s, s + L_k), s a multiple of
L_k. Columns with iota = 0 live in a dense block with id base[k] + (l J + j) nW[k] + w, nW[k] =
ceil(T / L_k), w = s / L_k; columns with iota >= 1 (capacity layering, §6.4) and predicted columns
(psi-PD, §5.8) get ids after the block. `ref_key` maps an id to the reference key ('A', l, j, k, s)
or ('P', l, j, k, s), with iota or the copy index appended when positive (§5.3).

Raise loop (§5.4). With x the live column masses of the request's candidates, y its connection
variables (1 where delta = 0) and f its fallback variable: while sum min(x, y) + f < 1 - 1e-10,
every candidate raises x_F if x_F <= y_eF (else y_eF), together with f; the raised values v follow
v(Y) = (v_0 + b_v) exp(Y / c_v) - b_v with the common dual increase Y set so that they sum to 1
(root of §5.5) and b_v = 1/d (psi-PD: §5.8).

Practical Sublet (design/q44_practical_sublet.md §2, §6.1): `VecPD.col_id` gives the column of a
type and slot (renewal, knob R) and `RequestOrder` the replica index by request order (knob O);
neither changes the PD's update rule.

This module imports only numpy, scipy, the standard library and sublet.algos.common.
"""
from __future__ import annotations

import math
import time
from array import array
from dataclasses import dataclass
from typing import Callable, Optional, Sequence, Union

import numpy as np
from scipy.optimize import brentq

from .common import PolicyError, column_cost, pd_window_slots, unit_costs

INF = float("inf")
W_TOL = 1e-10            # termination: sum min(x, y) + f >= 1 - W_TOL
EXP_CAP = 700.0          # exponent cap of the update and of h
NEWTON_MAX_IT = 60       # Newton iterations before the brentq fallback (§5.5)

D_MODES = ("mK+1", "max_cand+1")
ROOTS = ("newton", "brentq")
D_PRED = ("from_plan", "mK+2")


# ---------------------------------------------------------------- problem
@dataclass(eq=False)
class PDProblem:
    """Arrays of one PD problem (§5.2). C is INF where (l, k) is not a candidate of LLM j."""
    T: int; m: int; K: int; J: int
    L: np.ndarray           # (K,) int64 window in slots
    C: np.ndarray           # (m, J, K) column cost; INF where (l, k) is not a candidate
    g: np.ndarray           # (J,) GPUs per replica (reporting only)
    q_req: np.ndarray       # (n,) fallback cost per request of client n (a core client or an instance client)
    delta_req: np.ndarray   # (n, m) routing cost per request; INF = SLO-infeasible
    cl_llm: np.ndarray      # (n,)
    d: int                  # row sparsity used in the additive term 1/d
    site_perm: np.ndarray   # (m,) candidate site order (identity for the reference)

    @property
    def n(self) -> int:
        return len(self.cl_llm)


def _check_problem(p: PDProblem) -> None:
    """Assertions at construction (§5.2): every finite C_F > 0 and every q_req > 0."""
    fin = np.isfinite(p.C)
    if np.any(p.C[fin] <= 0):
        raise PolicyError("PD problem: a candidate column has cost C_F <= 0")
    if np.any(~(np.asarray(p.q_req) > 0)):
        raise PolicyError("PD problem: a fallback cost per request q_req is not positive")
    if np.any(np.asarray(p.L) < 1):
        raise PolicyError("PD problem: a window L_k < 1 slot")
    if sorted(np.asarray(p.site_perm).tolist()) != list(range(p.m)):
        raise PolicyError("PD problem: site_perm is not a permutation of the sites")


def problem_from_core(I) -> PDProblem:
    """Core mode (tests only): arrays of a core.Instance with the reference's costs, bitwise
    (C[l, j, k] = beta[j, l] + g[j] * a[l, k] * L[k], the operation order of core.Instance.C),
    q_req[:] = q, delta_req = delta, d = m K + 1, site_perm = identity."""
    tau, H = np.asarray(I.tau), np.asarray(I.H)
    L = (tau + H).astype(int).astype(np.int64)
    a = np.asarray(I.a)
    beta = np.asarray(I.beta)
    g = np.asarray(I.g)
    m, K = a.shape
    J = len(g)
    C = beta.T[:, :, None] + g[None, :, None] * a[:, None, :] * L[None, None, :]
    n = len(I.cl_llm)
    p = PDProblem(T=int(I.T), m=int(m), K=int(K), J=int(J), L=L, C=np.asarray(C, dtype=np.float64),
                  g=g.astype(np.int64), q_req=np.full(n, float(I.q)),
                  delta_req=np.asarray(I.delta, dtype=np.float64).copy(),
                  cl_llm=np.asarray(I.cl_llm, dtype=np.int64).copy(), d=int(m * K + 1),
                  site_perm=np.arange(m, dtype=np.int64))
    _check_problem(p)
    return p


def problem_from_view(view, *, protected_window=None, cand_mask=None, d_mode: str = "mK+1",
                      site_perm=None, windows: Optional[Sequence[int]] = None) -> PDProblem:
    """Engine mode (§5.2): the PD problem of a PublicView, one client per instance client.

    Windows L_k = tau_k + H_k // Δs (rule T12) for every contract with tau_slots set; a
    Contract.protected one gets `protected_window` or the largest rule-T12 window (M5). `windows`
    (an addition to §3.3, used by A2's view transform 'notice_oblivious') replaces these windows.
    (l, k) is a candidate of LLM j iff k is in the site's menu, the price is finite and
    cand_mask[l, j, k] holds (None: all true); its cost is common.column_cost at its window (M4).
    q_req and delta_req are per unit-slot (common.unit_costs). d = m K + 1 ('mK+1') or
    1 + the largest number of candidate pairs of one client ('max_cand+1', M3). site_perm: the
    site order pi (default identity)."""
    if d_mode not in D_MODES:
        raise PolicyError(f"d_mode must be one of {D_MODES}, got {d_mode!r}")
    g_ = view.grid
    T, m, K, J = int(g_.T_slow), len(view.sites), len(view.contracts), len(view.llms)
    if windows is None:
        L = np.array([pd_window_slots(view, k, protected_window) for k in range(K)], dtype=np.int64)
    else:
        L = np.asarray(windows, dtype=np.int64).copy()
        if L.shape != (K,):
            raise PolicyError(f"windows must have one entry per contract ({K}), got {L.shape}")
    if cand_mask is not None:
        cand_mask = np.asarray(cand_mask, dtype=bool)
        if cand_mask.shape != (m, J, K):
            raise PolicyError(f"cand_mask must have shape {(m, J, K)}, got {cand_mask.shape}")
    C = np.full((m, J, K), INF)
    for l, site in enumerate(view.sites):
        for k in site.menu:
            if not np.isfinite(view.price[l, k]):
                continue
            for j in range(J):
                if cand_mask is None or cand_mask[l, j, k]:
                    C[l, j, k] = column_cost(view, l, j, k, int(L[k]))
    q_req, delta_req = unit_costs(view)
    cl_llm = np.asarray(view.client_llm, dtype=np.int64).copy()
    if site_perm is None:
        site_perm = np.arange(m, dtype=np.int64)
    site_perm = np.asarray(site_perm, dtype=np.int64).copy()
    if d_mode == "mK+1":
        d = m * K + 1
    else:
        fin_c = np.isfinite(C)                        # (m, J, K)
        best = 0
        for c in range(len(cl_llm)):
            ok_l = np.isfinite(delta_req[c])
            best = max(best, int(fin_c[ok_l, cl_llm[c], :].sum()))
        d = 1 + best
    p = PDProblem(T=T, m=m, K=K, J=J, L=L, C=C, g=np.array([x.g for x in view.llms], dtype=np.int64),
                  q_req=np.asarray(q_req, dtype=np.float64), delta_req=np.asarray(delta_req, dtype=np.float64),
                  cl_llm=cl_llm, d=int(d), site_perm=site_perm)
    _check_problem(p)
    return p


# ---------------------------------------------------------------- root search (§5.5)
def _h_plain(vals: np.ndarray, bs: np.ndarray, cs: np.ndarray, Y: float) -> float:
    return float(np.sum((vals + bs) * np.exp(np.minimum(Y / cs, EXP_CAP)) - bs) - 1.0)


def root_brentq(vals: np.ndarray, bs: np.ndarray, cs: np.ndarray) -> float:
    """root='brentq': the reference routine (bracket from min(cs) 1e-3, doubling; brentq with
    xtol 1e-14, rtol 1e-12, maxiter 500) on h(Y) = sum((v + b) exp(min(Y / c, 700)) - b) - 1."""
    lo, hi = 0.0, float(np.min(cs)) * 1e-3
    while _h_plain(vals, bs, cs, hi) < 0:
        lo, hi = hi, hi * 2.0
    return brentq(lambda Y: _h_plain(vals, bs, cs, Y), lo, hi, xtol=1e-14, rtol=1e-12, maxiter=500)


def root_newton(vals: np.ndarray, bs: np.ndarray, cs: np.ndarray) -> float:
    """root='newton' (default): the Y > 0 with sum_v (v_0 + b_v) exp(Y / c_v) - sum b_v = 1.

    With a_v = v_0 + b_v and r_0 = 1 - sum v_0 > 0, h(Y) = sum a_v expm1(Y / c_v) - r_0 (the same
    function as §5.5's, in a form without cancellation), convex and increasing on [0, inf), h(0) < 0.
    Upper bracket Y_hi = min_v c_v ln((1 + b_v) / (v_0 + b_v)) (the minimizing variable alone
    reaches 1, so h(Y_hi) >= 0); Newton steps from Y_hi decrease monotonically to the root and stop
    when h(Y) <= 0 or the step is at most 1e-15 Y; after 60 iterations, or at a non-positive
    iterate, brentq(h, 0, Y_hi, xtol=1e-14, rtol=1e-12, maxiter=500). Every v_0 < 1 and c_v > 0
    (callers ensure it), and Y <= Y_hi keeps every exponent below ln(1 + 1/b) < 700."""
    a = vals + bs
    r0 = 1.0 - float(vals.sum())
    Y = float(np.min(cs * np.log1p((1.0 - vals) / a)))
    ac = a / cs

    def h(y: float) -> float:
        return float(np.dot(a, np.expm1(np.minimum(y / cs, EXP_CAP)))) - r0

    Y_hi = Y
    for _ in range(NEWTON_MAX_IT):
        z = np.minimum(Y / cs, EXP_CAP)
        em = np.expm1(z)
        hv = float(np.dot(a, em)) - r0
        if hv <= 0.0:
            return Y
        step = hv / float(np.dot(ac, em + 1.0))
        Yn = Y - step
        if not Yn > 0.0:
            break
        if step <= 1e-15 * Y:
            return Yn
        Y = Yn
    if h(Y_hi) <= 0.0:
        return Y_hi
    return brentq(h, 0.0, Y_hi, xtol=1e-14, rtol=1e-12, maxiter=500)


# ---------------------------------------------------------------- PD
@dataclass(eq=False)
class RequestOut:
    """Outcome of one request: its candidates (ids in candidate order) and their values after it."""
    t: int; c: int
    cols: np.ndarray        # (n_cand,) column ids in candidate order
    x: np.ndarray           # x of the candidates after the request
    y: np.ndarray; f: float
    delta: np.ndarray; C: np.ndarray; q: float
    raises: int


class _ClientCands:
    """Aligned candidate pairs of one client in candidate order (§5.3)."""
    __slots__ = ("j", "ls", "ks", "C", "dl", "off", "L", "rank")

    def __init__(self, j, ls, ks, C, dl, off, L, rank):
        self.j, self.ls, self.ks, self.C, self.dl, self.off, self.L, self.rank = j, ls, ks, C, dl, off, L, rank


IotaArg = Union[None, Callable[[int, int], int], np.ndarray, Sequence[int]]


class VecPD:
    """Vectorized ORML-PD (C3-T1) and the psi-interpolated PD (C3-T9), §5.

    `request(c, t)` processes one request of client c at slot t (callers keep the order of §5.1).
    psi < 1 with a non-empty `pred_cols` (any-start columns (l, j, k, s)) gives the psi-PD of §5.8:
    with `nearest_pred` one predicted column per request (the nearest by (delta, list index)), else
    every predicted column of the request's LLM covering t at a feasible site; d grows by
    min(p_max, 1), respectively p_max (`d_pred='from_plan'`, the reference), or by 1
    (`d_pred='mK+2'`, the bound of C3-T9 with the nearest column, for predictions whose p_max is not
    known in advance; an addition to §3.3). psi = 1 or no predicted columns: the plain PD."""

    def __init__(self, prob: PDProblem, *, psi: float = 1.0, pred_cols=None, nearest_pred: bool = True,
                 root: str = "newton", max_raises: int = 2000, record: bool = False,
                 d_pred: str = "from_plan"):
        if root not in ROOTS:
            raise PolicyError(f"root must be one of {ROOTS}, got {root!r}")
        if d_pred not in D_PRED:
            raise PolicyError(f"d_pred must be one of {D_PRED}, got {d_pred!r}")
        if isinstance(max_raises, bool) or not isinstance(max_raises, (int, np.integer)) or max_raises < 1:
            raise PolicyError(f"max_raises must be an integer >= 1, got {max_raises!r}")
        psi = float(psi)
        if not 0.0 < psi <= 1.0:
            raise PolicyError(f"psi must be in (0, 1], got {psi!r}")
        self.prob = prob
        self.psi = psi
        self.nearest_pred = bool(nearest_pred)
        self.root = root
        self._root = root_newton if root == "newton" else root_brentq
        self.max_raises = int(max_raises)
        self.record = bool(record)
        T, m, J, K = prob.T, prob.m, prob.J, prob.K
        self.T, self.m, self.J, self.K = T, m, J, K
        self.L = np.asarray(prob.L, dtype=np.int64)
        self.nW = -(-T // self.L)
        sizes = m * J * self.nW
        self.base = np.concatenate([[0], np.cumsum(sizes)[:-1]]).astype(np.int64)
        self.n_dense = int(sizes.sum())
        self.n_ids = self.n_dense
        cap = self.n_dense + 64
        self.x = np.zeros(cap)
        self.xload = np.zeros(cap)
        self.Ccol = np.zeros(cap)                  # 0 for non-candidate dense entries (x stays 0 there)
        Cfin = np.where(np.isfinite(prob.C), prob.C, 0.0)
        for k in range(K):
            blk = np.repeat(Cfin[:, :, k].reshape(m * J), int(self.nW[k]))
            self.Ccol[self.base[k]:self.base[k] + sizes[k]] = blk
        self._ext_key: list[tuple] = []            # keys of ids >= n_dense, in id order
        self._ext_id: dict[tuple, int] = {}
        self._ext_info: list[tuple] = []           # (l, j, k, s, iota, copy, is_pred) of ids >= n_dense
        rank = np.empty(m, dtype=np.int64)
        rank[np.asarray(prob.site_perm, dtype=np.int64)] = np.arange(m)
        self.rank = rank
        self._cands = [self._client_cands(c) for c in range(prob.n)]
        # predictions (§5.8)
        self.pred_mode = bool(psi < 1.0 and pred_cols is not None and len(pred_cols) > 0)
        self.pmax = 0
        self._pred: dict[int, dict] = {}
        if self.pred_mode:
            self._setup_pred(pred_cols)
            add = (min(self.pmax, 1) if self.nearest_pred else self.pmax) if d_pred == "from_plan" else 1
            self.d = int(prob.d) + int(add)
        else:
            self.d = int(prob.d)
        self.d_pred = d_pred
        self.psi_eff = psi if self.pred_mode else 1.0
        # b_v = 1/d (plain); psi-PD: psi/d + (1 - psi) 1[v in P_e] / |P_e|, where |P_e| = 1 always
        self._b_plain = 1.0 / self.d
        self._b_low = self.psi / self.d
        self._b_high = self.psi / self.d + (1.0 - self.psi)
        self.dual = 0.0
        self.serv = 0.0
        self.dualfeas_yf = 0.0
        self.records: list = []
        self._st = {"requests": 0, "raises_hist": {}, "max_raises": 0, "cap_hits": 0, "max_V": 0,
                    "cands_min": None, "cands_sum": 0, "cands_max": 0, "requests_per_slot_max": 0}
        self._slot, self._slot_n = None, 0
        self._times = array("d")

    # -------------------------------------------------------- columns
    def _client_cands(self, c: int) -> _ClientCands:
        """Candidate pairs (l, k) of client c: sites in site_perm order with finite delta, contracts
        in index order with finite C (§5.2)."""
        p = self.prob
        j = int(p.cl_llm[c])
        ls, ks = [], []
        for l in np.asarray(p.site_perm, dtype=np.int64):
            l = int(l)
            if not np.isfinite(p.delta_req[c, l]):
                continue
            for k in range(self.K):
                if np.isfinite(p.C[l, j, k]):
                    ls.append(l)
                    ks.append(k)
        ls = np.array(ls, dtype=np.int64)
        ks = np.array(ks, dtype=np.int64)
        C = np.asarray(p.C[ls, j, ks], dtype=np.float64) if len(ls) else np.zeros(0)
        dl = np.asarray(p.delta_req[c, ls], dtype=np.float64) if len(ls) else np.zeros(0)
        off = (self.base[ks] + (ls * self.J + j) * self.nW[ks]) if len(ls) else np.zeros(0, np.int64)
        Lk = self.L[ks] if len(ls) else np.zeros(0, np.int64)
        return _ClientCands(j, ls, ks, C, dl, off.astype(np.int64), Lk.astype(np.int64), self.rank[ls])

    def cand_pairs(self, c: int) -> tuple[np.ndarray, np.ndarray]:
        """(ls, ks) of client c's aligned candidate pairs in candidate order (the order of an iota array)."""
        cc = self._cands[c]
        return cc.ls, cc.ks

    def _grow(self, need: int) -> None:
        cap = len(self.x)
        if need <= cap:
            return
        new = max(need, 2 * cap)
        for name in ("x", "xload", "Ccol"):
            a = getattr(self, name)
            b = np.zeros(new)
            b[:cap] = a
            setattr(self, name, b)

    def _new_ext(self, key: tuple, info: tuple, cost: float) -> int:
        i = self.n_ids
        self._grow(i + 1)
        self.Ccol[i] = cost
        self.n_ids += 1
        self._ext_key.append(key)
        self._ext_id[key] = i
        self._ext_info.append(info)
        return i

    def _layer_id(self, l: int, j: int, k: int, s: int, iota: int) -> int:
        key = ("A", l, j, k, s, iota)
        i = self._ext_id.get(key)
        if i is None:
            i = self._new_ext(key, (l, j, k, s, iota, 0, False), float(self.prob.C[l, j, k]))
        return i

    def _decode(self, col: int) -> tuple[int, int, int, int]:
        k = int(np.searchsorted(self.base, col, side="right") - 1)
        lj, w = divmod(int(col - self.base[k]), int(self.nW[k]))
        l, j = divmod(lj, self.J)
        return l, j, k, w * int(self.L[k])

    def info(self, col: int) -> tuple[int, int, int, int, int, int, bool]:
        """(l, j, k, s, iota, copy, is_pred) of a column id; its window is [s, s + L[k])."""
        col = int(col)
        if col < self.n_dense:
            l, j, k, s = self._decode(col)
            return l, j, k, s, 0, 0, False
        return self._ext_info[col - self.n_dense]

    def ref_key(self, col: int) -> tuple:
        """('A', l, j, k, s) or ('P', l, j, k, s); iota > 0 appends iota, a copy index i > 0 appends i."""
        col = int(col)
        if col < self.n_dense:
            return ("A",) + self._decode(col)
        return self._ext_key[col - self.n_dense]

    def col_key(self, col: int) -> tuple:
        """Column key of a practical assignment: (l, j, k, s, iota) for an aligned column; the
        reference key ('P', ...) for a predicted one."""
        l, j, k, s, iota, _copy, is_pred = self.info(col)
        return self.ref_key(col) if is_pred else (l, j, k, s, iota)

    def col_id(self, l: int, j: int, k: int, t: int, iota: int = 0) -> int:
        """Id of the aligned column of type (l, j, k) with replica index iota whose window contains
        slot t (s = floor(t / L_k) L_k); a layered column (iota >= 1) is created if it does not exist
        yet. Used by practical Sublet's renewal (knob R, design/q44_practical_sublet.md §2.1 step 2).
        PolicyError if (l, k) is not a candidate of LLM j or t lies outside [0, T)."""
        l, j, k, t, iota = int(l), int(j), int(k), int(t), int(iota)
        if not 0 <= t < self.T:
            raise PolicyError(f"col_id: slot {t} outside [0, {self.T})")
        if not (0 <= l < self.m and 0 <= j < self.J and 0 <= k < self.K) or not np.isfinite(self.prob.C[l, j, k]):
            raise PolicyError(f"col_id: (l, j, k) = {(l, j, k)} is not a candidate column type")
        if iota < 0:
            raise PolicyError(f"col_id: iota must be >= 0, got {iota}")
        Lk = int(self.L[k])
        if iota == 0:
            return int(self.base[k] + (l * self.J + j) * self.nW[k] + t // Lk)
        return self._layer_id(l, j, k, (t // Lk) * Lk, iota)

    # -------------------------------------------------------- predictions
    def _setup_pred(self, pred_cols) -> None:
        """Predicted columns: one variable per entry (copy index i for the i-th occurrence, M58),
        kept if (l, k) is a candidate of LLM j (finite C); grouped per LLM for the candidate search."""
        p = self.prob
        seen: dict[tuple, int] = {}
        per_j: dict[int, list] = {}
        diff = np.zeros((self.J, self.T + 1), dtype=np.int64)
        for idx, F in enumerate(pred_cols):
            l, j, k, s = (int(v) for v in F)
            if not (0 <= l < self.m and 0 <= j < self.J and 0 <= k < self.K):
                raise PolicyError(f"predicted column {F} has an invalid (site, LLM, contract)")
            base = (l, j, k, s)
            i = seen.get(base, 0)
            seen[base] = i + 1
            if not np.isfinite(p.C[l, j, k]):
                continue
            key = ("P", l, j, k, s) if i == 0 else ("P", l, j, k, s, i)
            col = self._new_ext(key, (l, j, k, s, 0, i, True), float(p.C[l, j, k]))
            e = s + int(self.L[k])
            per_j.setdefault(j, []).append((idx, l, k, s, e, col))
            lo, hi = max(s, 0), min(e, self.T)
            if lo < hi:
                diff[j, lo] += 1
                diff[j, hi] -= 1
        self.pmax = int(np.cumsum(diff, axis=1).max()) if self.T > 0 else 0
        for j, rows in per_j.items():
            a = np.array(rows, dtype=np.int64).reshape(-1, 6)
            self._pred[j] = {"idx": a[:, 0], "l": a[:, 1], "k": a[:, 2], "s": a[:, 3], "e": a[:, 4],
                             "col": a[:, 5], "rank": self.rank[a[:, 1]]}

    def _with_pred(self, c: int, t: int, ids, C, dl, rank, excl):
        """Candidate arrays with the request's predicted columns merged in (§5.8); returns
        (ids, C, dl, pe) with pe the position of F_p (first predicted candidate with the smallest
        delta) or -1."""
        cc = self._cands[c]
        P = self._pred.get(cc.j)
        if P is None:
            return ids, C, dl, -1
        dlc = self.prob.delta_req[c]
        pdl = dlc[P["l"]]
        mask = (P["s"] <= t) & (t < P["e"]) & np.isfinite(pdl)
        if excl is not None and mask.any():
            mask &= ~np.isin(P["col"], excl)
        if not mask.any():
            return ids, C, dl, -1
        pcol, pidx, prk, pd_ = P["col"][mask], P["idx"][mask], P["rank"][mask], pdl[mask]
        pC = self.Ccol[pcol]
        if self.nearest_pred:
            i = int(np.lexsort((pidx, pd_))[0])
            ids2 = np.append(ids, pcol[i])
            return ids2, np.append(C, pC[i]), np.append(dl, pd_[i]), len(ids)
        n0 = len(ids)
        prim = np.concatenate([2 * rank, 2 * prk + 1])
        sec = np.concatenate([np.arange(n0, dtype=np.int64), pidx])
        order = np.lexsort((sec, prim))
        ids2 = np.concatenate([ids, pcol])[order]
        C2 = np.concatenate([C, pC])[order]
        dl2 = np.concatenate([dl, pd_])[order]
        is_p = (order >= n0)
        pos = np.nonzero(is_p)[0]
        pe = int(pos[np.argmin(dl2[pos])])
        return ids2, C2, dl2, pe

    # -------------------------------------------------------- one request
    def _iota(self, iota: IotaArg, cc: _ClientCands) -> Optional[np.ndarray]:
        if iota is None:
            return None
        if callable(iota):
            return np.fromiter((iota(int(l), int(k)) for l, k in zip(cc.ls, cc.ks)), np.int64, len(cc.ls))
        a = np.asarray(iota, dtype=np.int64)
        if a.shape != cc.ls.shape:
            raise PolicyError(f"iota array has shape {a.shape}, the client has {len(cc.ls)} candidate pairs")
        return a

    def request(self, c: int, t: int, *, iota: IotaArg = None, excluded=None) -> RequestOut:
        """One request of client c at slot t (§5.4). iota: None (all iota = 0), a callable (l, k) -> iota
        for this request's unit (§6.4), or an int array aligned with cand_pairs(c); excluded: a
        collection of refused column ids, dropped from the candidates (§6.5)."""
        t_start = time.perf_counter()
        c, t = int(c), int(t)
        if not 0 <= t < self.T:
            raise PolicyError(f"request at slot {t} outside [0, {self.T})")
        cc = self._cands[c]
        ids = cc.off + t // cc.L
        io = self._iota(iota, cc)
        if io is not None:
            nz = np.nonzero(io)[0]
            if len(nz):
                ids = ids.copy()
                for i in nz:
                    l, k = int(cc.ls[i]), int(cc.ks[i])
                    Lk = int(self.L[k])
                    ids[i] = self._layer_id(l, cc.j, k, (t // Lk) * Lk, int(io[i]))
        C, dl, rank = cc.C, cc.dl, cc.rank
        excl = None
        if excluded is not None and len(excluded) > 0:
            excl = np.fromiter((int(v) for v in excluded), np.int64)
            keep = ~np.isin(ids, excl)
            if not keep.all():
                ids, C, dl, rank = ids[keep], C[keep], dl[keep], rank[keep]
        pe = -1
        if self.pred_mode:
            ids, C, dl, pe = self._with_pred(c, t, ids, C, dl, rank, excl)
            if pe < 0 or not dl[pe] < self.prob.q_req[c]:
                pe = len(ids)                     # P_hat = {f}
        q = float(self.prob.q_req[c])
        out = self._raise_loop(c, t, ids, C, dl, q, pe)
        self._stat(t, len(ids), out.raises, time.perf_counter() - t_start)
        return out

    def _raise_loop(self, c: int, t: int, ids, C, dl, q: float, pe: int) -> RequestOut:
        n = len(ids)
        x = self.x[ids].copy()
        y = (dl == 0).astype(float)
        f = 0.0
        xl = np.zeros(n)
        yl = np.zeros(n)
        fl = 0.0
        raises = 0
        cs = np.empty(n + 1)
        cs[n] = q
        if self.pred_mode:
            bs = np.full(n + 1, self._b_low)
            bs[pe] = self._b_high
        else:
            bs = np.full(n + 1, self._b_plain)
        vals = np.empty(n + 1)
        while True:
            w = float(np.minimum(x, y).sum()) + f
            if w >= 1.0 - W_TOL:
                break
            if raises >= self.max_raises:
                self._st["cap_hits"] += 1
                break
            raises += 1
            A = x <= y
            vals[:n] = np.where(A, x, y)
            vals[n] = f
            cs[:n] = np.where(A, C, dl)
            Y = float(self._root(vals, bs, cs))
            nv = (vals + bs) * np.exp(np.minimum(Y / cs, EXP_CAP)) - bs
            x = np.where(A, nv[:n], x)
            y = np.where(A, y, nv[:n])
            f = float(nv[n])
            xl[A] += Y
            yl[~A] += Y
            fl += Y
            self.dual += Y
        self.x[ids] = x
        if raises:
            self.xload[ids] += xl
        self.serv += float(np.dot(dl, y)) + q * f
        lg = math.log(1 + self.d / self.psi_eff)
        if raises:
            pos = (dl > 0) & (yl > 0)
            if pos.any():
                self.dualfeas_yf = max(self.dualfeas_yf, float(np.max(yl[pos] / (dl[pos] * lg))))
            if fl > 0:
                self.dualfeas_yf = max(self.dualfeas_yf, fl / (q * lg))
        if self.record:
            self.records.append((c, t, [self.ref_key(i) for i in ids], x.copy(), y.copy(), f, dl.copy()))
        return RequestOut(t=t, c=c, cols=ids, x=x, y=y, f=f, delta=dl, C=C, q=q, raises=raises)

    def _stat(self, t: int, n_cand: int, raises: int, dt: float) -> None:
        s = self._st
        s["requests"] += 1
        h = s["raises_hist"]
        h[raises] = h.get(raises, 0) + 1
        s["max_raises"] = max(s["max_raises"], raises)
        s["max_V"] = max(s["max_V"], n_cand + 1)
        s["cands_min"] = n_cand if s["cands_min"] is None else min(s["cands_min"], n_cand)
        s["cands_sum"] += n_cand
        s["cands_max"] = max(s["cands_max"], n_cand)
        if t != self._slot:
            self._slot, self._slot_n = t, 0
        self._slot_n += 1
        s["requests_per_slot_max"] = max(s["requests_per_slot_max"], self._slot_n)
        self._times.append(dt)

    # -------------------------------------------------------- results
    def primal(self) -> float:
        """sum_F C_F x_F + service cost so far."""
        n = self.n_ids
        return float(np.dot(self.Ccol[:n], self.x[:n])) + self.serv

    def dual_feasibility(self) -> float:
        """max over variables with positive load of load / (cost ln(1 + d / psi_eff)) (C3-T1: <= 1)."""
        n = self.n_ids
        lg = math.log(1 + self.d / self.psi_eff)
        xl, Cc = self.xload[:n], self.Ccol[:n]
        pos = (xl > 0) & (Cc > 0)
        wx = float(np.max(xl[pos] / (Cc[pos] * lg))) if pos.any() else 0.0
        return max(self.dualfeas_yf, wx)

    def final_x(self) -> dict:
        """{ref_key: x} over the columns with x > 0."""
        n = self.n_ids
        return {self.ref_key(i): float(self.x[i]) for i in np.nonzero(self.x[:n])[0]}

    @property
    def cap_hits(self) -> int:
        return int(self._st["cap_hits"])

    @property
    def stats(self) -> dict:
        """The diagnostics of §5.6 (stats_summary())."""
        return self.stats_summary()

    def stats_summary(self) -> dict:
        """§5.6: requests, raises histogram and maximum, cap hits, maximum |V|, candidates per request,
        requests per slot (maximum), wall time per request (mean, P50, P99, maximum, seconds)."""
        s = self._st
        nreq = s["requests"]
        tm = np.frombuffer(self._times, dtype=np.float64) if len(self._times) else np.zeros(0)
        out = {"requests": nreq, "raises_hist": {int(k): int(v) for k, v in sorted(s["raises_hist"].items())},
               "raises_max": s["max_raises"], "raises_mean": (sum(k * v for k, v in s["raises_hist"].items()) / nreq
                                                              if nreq else None),
               "cap_hits": s["cap_hits"], "max_V": s["max_V"],
               "cands_min": s["cands_min"], "cands_mean": s["cands_sum"] / nreq if nreq else None,
               "cands_max": s["cands_max"], "requests_per_slot_max": s["requests_per_slot_max"],
               "n_columns": int(self.n_ids), "n_ext_columns": int(self.n_ids - self.n_dense), "d": self.d,
               "time_s_mean": float(tm.mean()) if len(tm) else None,
               "time_s_p50": float(np.percentile(tm, 50)) if len(tm) else None,
               "time_s_p99": float(np.percentile(tm, 99)) if len(tm) else None,
               "time_s_max": float(tm.max()) if len(tm) else None}
        return out


class RequestOrder:
    """Replica index by request order (knob O, design/q44_practical_sublet.md §2.1 step 3): within one
    slow slot, a request of LLM j gets iota = floor(n / u) at its candidate pair (l, k), where n is the
    number of earlier requests of the slot, of the same LLM, that listed (l, k). So each column of a
    slot receives at most u requests (PDC-3, sim_spec_ms2 §21.3); the index depends only on the
    slot's request order, not on the rounding. `start_slot()` resets the counts; `iota(j, ls, ks)`
    returns the indices of one request (aligned with its candidate pairs, which are distinct) and
    counts the request. Callers apply it only when capacity layering is active (iota = 0 on
    kappa_infinite instances)."""

    def __init__(self, u: int, shape: tuple[int, int, int]):
        if isinstance(u, bool) or not isinstance(u, (int, np.integer)) or u < 1:
            raise PolicyError(f"RequestOrder: u must be an integer >= 1, got {u!r}")
        self.u = int(u)
        self._n = np.zeros(shape, dtype=np.int64)
        self._dirty = False

    def start_slot(self) -> None:
        if self._dirty:
            self._n[...] = 0
            self._dirty = False

    def iota(self, j: int, ls: np.ndarray, ks: np.ndarray) -> np.ndarray:
        if len(ls) == 0:
            return np.zeros(0, dtype=np.int64)
        j = int(j)
        n = self._n[ls, j, ks]
        self._n[ls, j, ks] = n + 1
        self._dirty = True
        return n // self.u


def ref_key(pd: VecPD, col: int) -> tuple:
    """('A', l, j, k, s) or ('P', l, j, k, s); iota > 0 appends iota; a predicted copy index i > 0
    appends i (§5.3)."""
    return pd.ref_key(col)


__all__ = ["PDProblem", "problem_from_core", "problem_from_view", "VecPD", "RequestOut", "RequestOrder",
           "ref_key", "root_newton", "root_brentq"]
