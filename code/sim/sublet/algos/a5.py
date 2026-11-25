"""Policy A5: predictions with the doubling combiner (design/sim_spec_ms2.md §13; design §3.2.7).

A5 runs the plain PD with rounding (R, §5-§6 at r-bar `R_rbar`), simulates follow-the-prediction
(FP) under eager accounting and follows one of the two with the doubling combiner of C3-T11
(`pd.combine`, gamma = 1 + 1/sqrt 2 by default, M40); it also runs psi-PDs (C3-T9) on the same
requests for reporting.

  FP (§13.3, `pd.follow_prediction`): curve_FP[t] = sum of C_F over the predicted columns with
     s = t, plus, per request e of slot t, min{q_e, min delta_el} over the predicted columns
     (l, j_e, k, s) with s <= t < s + L_k.
  R: curve_R[t] = the practical rule's cost at t (`Rounder.curve`, purchases and service).
  Combiner (§13.4): follow FP at t = 0 iff curve_FP[0] <= curve_R[0]; with X followed and Y the
     other, switch to Y at t iff C_X(t) > gamma C_Y(t) + 1e-12, then pay Y's live columns fresh
     (state_cost) plus Y's service at t; else pay X's increment. `total` is the accounted (eager)
     cost of C3-T11 (PROVEN, eager accounting): total <= (gamma + gamma^2/(gamma - 1))
     min{C_FP(T), C_R(T)} pathwise, 3 + 2 sqrt 2 at the default gamma.
  Execution (§13.5): execute='replay' buys each purchase of the combiner (X's purchases at t, or
     all of Y's live columns at a switch) as one single-replica lease at t and releases it by A2's
     rule (§6.6: first slot t >= max(s + L_k, ceil((t0 Δs + P_k) / Δs))); leases of the abandoned
     algorithm keep serving until then and the accounting ignores them. execute='none' buys
     nothing.

`DoublingCombiner` takes only the two experts' increments and, at a switch, a state-cost and a
service callback, so it combines any two eager experts (Proposition G4 of
design/q44_practical_sublet.md); the guard's safe expert (guard.SafeExpert, policy A8) runs it with
all-fallback FB in the F slot and R in the R slot, with report labels ('FB', 'R').
`FollowPrediction` and `DoublingCombiner` are incremental (one slot at a time, as a policy needs
them); `follow_prediction_curve` and `combine` apply them to a core instance and reproduce
`pd.follow_prediction` and `pd.combine` (tests and reproductions, §17.3 R7). The psi-PDs are
fractional only: no rounding keeps their consistency (O2, open).
"""
from __future__ import annotations

import math
from typing import Callable, Optional, Sequence

import numpy as np

from ..instance import active_units
from ..policies.base import Policy
from ..types import INF, Buy, PublicView, SlowObs
from .a2 import A2Planner
from .common import LeaseBook, PolicyError, column_cost, policy_streams, resolve_params, slot_max_demand
from .pd_core import VecPD

G2 = 1.0 + 1.0 / math.sqrt(2.0)        # gamma of design §3.2.7 (bound 3 + 2 sqrt 2)
SWITCH_TOL = 1e-12                     # pd.combine's slack in C_X(t) > gamma C_Y(t) + 1e-12


def p_max(pred_cols: Sequence[tuple], L: Sequence[int], T: int, J: int) -> int:
    """Largest number of predicted columns of one LLM covering one slot t in [0, T) (`FracPD`'s
    pmax, which sets d = mK + 1 + pmax, or + min(pmax, 1) with the nearest column, §5.8)."""
    if not pred_cols:
        return 0
    cnt = np.zeros((J, T + 1), dtype=np.int64)
    for (l, j, k, s) in pred_cols:
        a, b = max(int(s), 0), min(int(s) + int(L[k]), T)
        if a < b:
            cnt[j, a] += 1
            cnt[j, b] -= 1
    return int(np.cumsum(cnt[:, :T], axis=1).max(initial=0))


# ---------------------------------------------------------------- FP and the combiner
class FollowPrediction:
    """FP's accounted cost over predicted columns (l, j, k, s) (§13.3), slot by slot in increasing
    order. `cost(l, j, k)` is the column cost C_F, `L` the PD windows (K,), T the horizon in slots,
    J and m the numbers of LLMs and sites."""

    def __init__(self, pred_cols: Sequence[tuple], L: Sequence[int], cost: Callable[[int, int, int], float],
                 T: int, J: int, m: int):
        self.cols = [tuple(int(v) for v in F) for F in pred_cols]
        self.L = np.asarray(L, dtype=np.int64)
        self.T, self.J, self.m = int(T), int(J), int(m)
        self.C = [float(cost(l, j, k)) for (l, j, k, s) in self.cols]
        self.end = [s + int(self.L[k]) for (l, j, k, s) in self.cols]
        self.starts: dict[int, list[int]] = {}      # purchases: s -> indices (0 <= s < T)
        self._add: dict[int, list[int]] = {}        # coverage [max(s, 0), s + L_k) per column
        self._rem: dict[int, list[int]] = {}
        for i, (l, j, k, s) in enumerate(self.cols):
            if 0 <= s < self.T:
                self.starts.setdefault(s, []).append(i)
            a, b = max(s, 0), self.end[i]
            if a < b:
                self._add.setdefault(a, []).append(i)
                self._rem.setdefault(b, []).append(i)
        self.cover = np.zeros((self.J, self.m), dtype=np.int64)   # predicted columns of (j, l) covering t
        self.t = -1
        self.curve = np.zeros(self.T)

    def advance(self, t: int) -> None:
        """Move the coverage counts to slot t (slots strictly increasing)."""
        if t <= self.t:
            raise ValueError(f"FollowPrediction: slot {t} after slot {self.t}")
        for u in range(self.t + 1, t + 1):
            for i in self._rem.get(u, ()):
                self.cover[self.cols[i][1], self.cols[i][0]] -= 1
            for i in self._add.get(u, ()):
                self.cover[self.cols[i][1], self.cols[i][0]] += 1
        self.t = t

    def purchases(self, t: int) -> list[int]:
        """Indices of the predicted columns bought at t (s = t), in list order."""
        return list(self.starts.get(t, ())) if 0 <= t < self.T else []

    def live(self, t: int) -> list[int]:
        """Indices of the predicted columns with s <= t < s + L_k, in list order."""
        return [i for i, F in enumerate(self.cols) if F[3] <= t < self.end[i]]

    def buys(self, t: int) -> float:
        return sum(self.C[i] for i, F in enumerate(self.cols) if F[3] == t)

    def state_cost(self, t: int) -> float:
        """sum of C_F over the predicted columns live at t (pd.combine's state_cost('F', t))."""
        return sum(self.C[i] for i, F in enumerate(self.cols) if F[3] <= t < self.end[i])

    def best(self, j: int, q: float, delta_row: np.ndarray) -> float:
        """min{q, min delta_l over the sites l with a predicted column of LLM j covering t}."""
        cov = self.cover[j] > 0
        if not cov.any():
            return float(q)
        d = float(np.min(np.where(cov, delta_row, INF)))
        return d if d < q else float(q)

    def slot(self, t: int, requests) -> float:
        """curve_FP[t]: the purchases at t, then the service of `requests`, an iterable of
        (j, q, delta_row, count) in request order (count identical requests of one client)."""
        self.advance(t)
        v = 0.0
        for i in self.purchases(t):
            v += self.C[i]
        for (j, q, drow, cnt) in requests:
            if cnt <= 0:
                continue
            b = self.best(j, q, drow)
            v += b if cnt == 1 else cnt * b
        if 0 <= t < self.T:
            self.curve[t] = v
        return v


class DoublingCombiner:
    """The doubling combiner of C3-T11 (`pd.combine`), one slot at a time (§13.4).

    The rule is expert-agnostic: it sees only the two experts' increments per slot and, at a switch,
    the new expert's state cost and service (callbacks). The internal codes of the two slots are 'F'
    and 'R'. In A5 the F slot holds FP and the R slot the rounded PD R; the guard's safe expert
    (guard.SafeExpert, design/q44_practical_sublet.md §3.10) holds all-fallback FB in the F slot and
    R in the R slot. By Proposition G4 of that note (PROVEN by the C3-T11 proof) the accounted total
    satisfies total <= (gamma + gamma^2/(gamma - 1)) min{C_X(t), C_Y(t)} at every t for any two eager
    experts X, Y, and the combination is itself eager (§3.2 there). `labels` names the experts of the
    F and R slots in reports (default ('FP', 'R'), A5's); `followed` and `followed_rle()` keep the
    codes 'F' and 'R', and `label(code)` and `followed_rle(labeled=True)` give the names."""

    def __init__(self, gamma: float = G2, labels: tuple[str, str] = ("FP", "R")):
        if not gamma > 1:
            raise PolicyError(f"combiner: gamma must be > 1, got {gamma!r}")
        if not isinstance(labels, (tuple, list)) or len(labels) != 2:
            raise PolicyError(f"combiner: labels must be a pair of names, got {labels!r}")
        self.gamma = float(gamma)
        self.labels = (str(labels[0]), str(labels[1]))
        self.cur: Optional[str] = None      # 'F' (FP, or FB in the guard's safe expert) or 'R'
        self.CF = 0.0                       # cumulative curves through the last slot
        self.CR = 0.0
        self.total = 0.0
        self.switches = 0
        self.followed: list[str] = []

    def step(self, inc_fp: float, inc_r: float, state_cost: Callable[[str], float],
             serv: Callable[[str], float]) -> tuple[str, bool]:
        """Slot t with curve_FP[t] = inc_fp and curve_R[t] = inc_r: returns (the algorithm whose
        purchases are made at t, whether it switched at t). At a switch the purchases are all of the
        new algorithm's live columns at t; state_cost and serv are evaluated only then."""
        CF_t = self.CF + inc_fp
        CR_t = self.CR + inc_r
        if self.cur is None:
            self.cur = "F" if CF_t <= CR_t else "R"
        if self.cur == "F":
            prev, inc, Cy = self.CF, inc_fp, CR_t
        else:
            prev, inc, Cy = self.CR, inc_r, CF_t
        switched = False
        if prev + inc > self.gamma * Cy + SWITCH_TOL:
            self.cur = "R" if self.cur == "F" else "F"
            self.switches += 1
            self.total += state_cost(self.cur) + serv(self.cur)
            switched = True
        else:
            self.total += inc
        self.CF, self.CR = CF_t, CR_t
        self.followed.append(self.cur)
        return self.cur, switched

    def label(self, code: str) -> str:
        """Report name of the expert in slot `code` ('F' or 'R')."""
        if code not in ("F", "R"):
            raise PolicyError(f"combiner: unknown slot code {code!r} ('F' or 'R')")
        return self.labels[0] if code == "F" else self.labels[1]

    def followed_rle(self, labeled: bool = False) -> list[list]:
        """Followed algorithm per slot, run-length encoded: [[which, first slot, length], ...], with the
        codes 'F' and 'R' (labeled=False, A5's report) or the names of `labels`."""
        out: list[list] = []
        for t, w in enumerate(self.followed):
            if labeled:
                w = self.label(w)
            if out and out[-1][0] == w:
                out[-1][2] += 1
            else:
                out.append([w, t, 1])
        return out


# ---------------------------------------------------------------- core-mode wrappers (tests)
def follow_prediction_curve(I, pred_cols: Sequence[tuple]) -> np.ndarray:
    """FP's cost curve on a core instance (`pd.follow_prediction(I, pred_cols)`): FollowPrediction
    with C = I.C and the requests of I.elements() in order."""
    fp = FollowPrediction(pred_cols, I.L, I.C, I.T, I.J, I.m)
    by_t: dict[int, list[int]] = {}
    for (c, t) in I.elements():
        by_t.setdefault(t, []).append(c)
    for t in range(I.T):
        fp.slot(t, ((int(I.cl_llm[c]), float(I.q), I.delta[c], 1) for c in by_t.get(t, ())))
    return fp.curve.copy()


def combine(I, pred_cols: Sequence[tuple], curve_fp, opened_R: dict, curve_R, gamma: float = 2.0) -> tuple[float, int]:
    """`pd.combine` through DoublingCombiner on a core instance: opened_R maps reference keys
    ('A', l, j, k, s, ...) to their opening slot (round_pd's 'opened'). Returns (total, switches)."""
    cols = [tuple(int(v) for v in F) for F in pred_cols]
    L = I.L
    comb = DoublingCombiner(gamma)
    items = list(opened_R.items())
    for t in range(I.T):
        def state_cost(w, t=t):
            if w == "F":
                return sum(I.C(l, j, k) for (l, j, k, s) in cols if s <= t < s + L[k])
            return sum(I.C(F[1], F[2], F[3]) for F, t0 in items if t0 <= t and F[4] + L[F[3]] > t)

        def serv(w, t=t):
            if w == "F":
                return curve_fp[t] - sum(I.C(l, j, k) for (l, j, k, s) in cols if s == t)
            return curve_R[t] - sum(I.C(F[1], F[2], F[3]) for F, t0 in items if t0 == t)
        comb.step(float(curve_fp[t]), float(curve_R[t]), state_cost, serv)
    return comb.total, comb.switches


# ---------------------------------------------------------------- policy A5
class A5(Policy):
    """A5 (§13): R (plain PD + rounding through a2.A2Planner), FP, the doubling combiner, and
    psi-PDs for reporting. Driver inputs: pred_cols (required) and N_bound (R_rbar='theory')."""
    name = "A5"
    PARAMS = {"gamma": G2, "R_rbar": 1, "psi_list": [], "nearest_pred": True, "d_pred": "from_plan",
              "execute": "replay"}
    INPUTS = ("pred_cols", "N_bound")

    def __init__(self, **kw):
        self._p, inp = resolve_params(self.PARAMS, kw, "A5", inputs=self.INPUTS)
        p = self._p
        g = p["gamma"]
        if isinstance(g, bool) or not isinstance(g, (int, float, np.floating)) or not g > 1:
            raise PolicyError(f"A5: gamma must be a number > 1, got {g!r}")
        r = p["R_rbar"]
        if r != "theory" and (isinstance(r, bool) or not isinstance(r, (int, np.integer)) or r < 1):
            raise PolicyError(f"A5: R_rbar must be an integer >= 1 or 'theory', got {r!r}")
        psis = p["psi_list"]
        if not isinstance(psis, (list, tuple)) or any(
                isinstance(x, bool) or not isinstance(x, (int, float, np.floating)) or not 0 < x <= 1 for x in psis):
            raise PolicyError(f"A5: psi_list must be a list of numbers in (0, 1], got {psis!r}")
        if p["d_pred"] not in ("from_plan", "mK+2"):
            raise PolicyError(f"A5: d_pred must be 'from_plan' or 'mK+2', got {p['d_pred']!r}")
        if not isinstance(p["nearest_pred"], (bool, np.bool_)):
            raise PolicyError(f"A5: nearest_pred must be a bool, got {p['nearest_pred']!r}")
        if p["execute"] not in ("replay", "none"):
            raise PolicyError(f"A5: execute must be 'replay' or 'none', got {p['execute']!r}")
        if inp.get("pred_cols") is None:
            raise PolicyError("A5 needs the driver input pred_cols (predicted columns, §13.1)")
        self.pred_cols = inp["pred_cols"]
        self.N_bound = inp.get("N_bound")
        if r == "theory" and self.N_bound is None:
            raise PolicyError("A5: R_rbar='theory' needs the driver input N_bound (§6.3)")

    def params(self) -> dict:
        return dict(self._p)

    # -------------------------------------------------------- reset
    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        p = self._p
        streams = policy_streams(rng)
        self.planner = A2Planner(view, streams["main"], streams["order"], rbar=p["R_rbar"], N_bound=self.N_bound)
        pl = self.planner
        self.pd, self.rounder, self.prob = pl.pd, pl.rounder, pl.prob
        self.rbar = pl.rbar
        self.T, self.u = int(view.grid.T_slow), int(view.units_per_replica)
        self.L = np.asarray(self.prob.L, dtype=np.int64)
        self.preds = [tuple(int(v) for v in F) for F in self.pred_cols]
        Cp = np.asarray(self.prob.C, dtype=np.float64)
        L = self.L

        def cost(l, j, k):
            c = float(Cp[l, j, k])
            return c if np.isfinite(c) else column_cost(view, l, j, k, int(L[k]))
        self.fp = FollowPrediction(self.preds, L, cost, self.T, len(view.llms), len(view.sites))
        self.comb = DoublingCombiner(float(p["gamma"]))
        self.cl_llm = np.asarray(self.prob.cl_llm, dtype=np.int64)
        self.q_req = np.asarray(self.prob.q_req, dtype=np.float64)
        self.delta_req = np.asarray(self.prob.delta_req, dtype=np.float64)
        self.psi_pds = [(float(psi), VecPD(self.prob, psi=float(psi), pred_cols=self.preds,
                                           nearest_pred=bool(p["nearest_pred"]), d_pred=p["d_pred"]))
                        for psi in p["psi_list"]]
        self.book = LeaseBook()
        self._release_at: dict[int, int] = {}     # lease id -> release slot (A2's rule, §6.6)
        self.exec = {"buys_fp": 0, "buys_r": 0, "releases": 0, "refused_fp": 0, "refused_r": 0}

    # -------------------------------------------------------- R's columns
    def _r_cols(self, t: int, which: str) -> list[int]:
        """R's opened columns (in opening order) that are live at t (t0 <= t < s + L_k, 'live') or
        opened at t ('buys')."""
        out = []
        for col, t0 in self.rounder.opened.items():
            if which == "buys":
                if t0 == t:
                    out.append(col)
            elif t0 <= t:
                l, j, k, s, iota, L = self.planner.column(col)
                if s + L > t:
                    out.append(col)
        return out

    def _r_cost(self, cols) -> float:
        C = self.prob.C
        tot = 0
        for col in cols:
            l, j, k, s, iota, L = self.planner.column(col)
            tot += float(C[l, j, k])
        return tot

    def _release_slot(self, t0: int, s: int, k: int) -> int:
        """A2's release slot (§6.6): max(s + L_k, ceil((t0 Δs + P_k) / Δs))."""
        slow = self.view.grid.slow_min
        P = int(self.view.contracts[k].prepaid_min)
        return max(s + int(self.L[k]), -(-(t0 * slow + P) // slow))

    def _buy(self, t: int, which: str, idx: int) -> None:
        if which == "R":
            l, j, k, s, iota, L = self.planner.column(idx)
        else:
            l, j, k, s = self.preds[idx]
        self.book.buy((which, idx, t, s, k), Buy(l, k, j, 1, tag="a5:fp" if which == "F" else "a5:r"))

    # -------------------------------------------------------- act
    def act(self, obs: SlowObs):
        t = int(obs.t)
        book = self.book
        for key, r in book.begin(obs):
            which, idx, t0, s, k = key
            if r.ok:
                self._release_at[int(r.lease_id)] = self._release_slot(t0, s, k)
                self.exec["buys_fp" if which == "F" else "buys_r"] += 1
            elif which == "R":
                self.exec["refused_r"] += 1
                self.planner.refuse(idx, t, r.reason)
            else:
                self.exec["refused_fp"] += 1
        # R: the plain PD and the rounding on the requests of slot t (§5.1, §6.7 steps 2-4)
        opened_t = self.planner.slot(obs)
        n = active_units(slot_max_demand(obs), self.u)
        reqs = []
        for c in np.nonzero(n)[0]:
            c = int(c)
            reqs.append((int(self.cl_llm[c]), float(self.q_req[c]), self.delta_req[c], int(n[c])))
            for _psi, vp in self.psi_pds:
                for _v in range(int(n[c])):
                    vp.request(c, t)
        inc_r = float(self.rounder.curve[t])
        inc_fp = self.fp.slot(t, reqs)

        def state_cost(w):
            return self.fp.state_cost(t) if w == "F" else self._r_cost(self._r_cols(t, "live"))

        def serv(w):
            return (inc_fp - self.fp.buys(t)) if w == "F" else (inc_r - self._r_cost(self._r_cols(t, "buys")))
        cur, switched = self.comb.step(inc_fp, inc_r, state_cost, serv)
        # execution (§13.5)
        if self._p["execute"] == "replay":
            if switched:
                buys = self.fp.live(t) if cur == "F" else self._r_cols(t, "live")
            else:
                buys = self.fp.purchases(t) if cur == "F" else opened_t
            for idx in buys:
                self._buy(t, cur, idx)
            for lid in [x for x, ts in self._release_at.items() if ts <= t]:
                if lid in obs.leases:
                    book.release(lid)
                    self.exec["releases"] += 1
                del self._release_at[lid]
        return book.assemble(obs, self.view)

    # -------------------------------------------------------- report
    def opened_ref(self) -> dict:
        """{ref_key: opening slot} of R's opened columns (round_pd(...)['opened'] on core instances)."""
        return self.rounder.opened_ref()

    def report(self) -> dict:
        pd, rd = self.pd, self.rounder
        return {"C_FP": self.comb.CF, "C_R": self.comb.CR, "total": self.comb.total,
                "switches": self.comb.switches, "gamma": self.comb.gamma, "followed": self.comb.followed_rle(),
                "P": float(pd.primal()), "dual": float(pd.dual), "dual_feasibility": float(pd.dual_feasibility()),
                "d": int(pd.d), "rbar": self.rbar, "N_bound": self.N_bound, "cost_pr": float(rd.cost_pr),
                "cost_an": float(rd.cost_an), "n_fix_an": int(rd.n_fix_an), "curve_R": rd.curve.tolist(),
                "curve_FP": self.fp.curve.tolist(),
                "opened": [[list(pd.ref_key(col)), int(t0)] for col, t0 in rd.opened.items()],
                "refused": len(rd.refused), "exec": dict(self.exec), "book": dict(self.book.stats),
                "pd": pd.stats_summary(),
                "psi": [{"psi": psi, "P": float(vp.primal()), "dual_feasibility": float(vp.dual_feasibility()),
                         "d": int(vp.d), "p_max": int(vp.pmax)} for psi, vp in self.psi_pds],
                "prediction": {"n_cols": len(self.preds), "p_max": p_max(self.preds, self.L, self.T, len(self.view.llms)),
                               "label": getattr(self.pred_cols, "label", None),
                               "days": list(getattr(self.pred_cols, "days", []) or [])}}


__all__ = ["G2", "SWITCH_TOL", "p_max", "FollowPrediction", "DoublingCombiner", "follow_prediction_curve",
           "combine", "A5"]
