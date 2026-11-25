"""Policy A6, Sublet as specified (design/sim_spec_ms2.md §14; design Table 5.7, §3).

A6 composes the components of A2-A5 and the heuristics of design §3.2-§3.4. At slow slot t:
  1. book.begin(obs); the execution layer absorbs its purchase results; a refused purchase at the
     column's own site goes to the rounder (§6.5); the redundancy rule takes its results.
  2. Under I2 with marking != 'off' the mark states are updated from obs.site_announced (§8.3;
     done by the layer's site rule at the start of its step).
  3. The requests of slot t (§5.1) through the PD with the candidate mask of P1 and P3 (§11), the
     protected window of §5.2, d = mK + 1, the site order pi and capacity layering (§6.4); rounding
     with r-bar = 1 (variant 'practical', the Q26 headline) or ceil(2 ln N) ('theory').
  4. With predictions: FP and the doubling combiner (§13.4, gamma = 1 + 1/sqrt 2) choose the
     columns to realize at t (the followed algorithm's purchases, or the other's live columns at a
     switch); without: the PD's opened columns.
  5. layer.open for each of them; layer.step (X1 renewal; X2 with the idle timer; X3 round robin,
     or marking under I2 with the site rule of §8.3; X4 through the reclaim handler with the C2-SW
     reaction 'c2sw', or test (a) 'test_a' with predictions).
  6. The redundancy rule (§12).
  7. book.assemble: releases, drains (drain=True), purchases in staging order (pre-warm commits,
     logical-slot purchases, spares), after the capacity pre-check.

view_transform (BL6, BL7, §15.8): 'notice_oblivious' gives PD windows tau_k (A2Planner), P1 with
every H_k read as 0 and P3 off; 'revocable_only' drops every contract flagged by
common.treated_as_protected from the candidate mask (A2Planner), X3's pool (which never holds a
flagged contract) and the handler's protected-contract search (the handler sees a view without
them), so the handler reacts cold ('no-protected', the RRL case).

px (default None: every knob off, the code path of A6 as specified): practical Sublet's knobs
(design/q44_practical_sublet.md §2.1, §2.2; keys a2.PX_KEYS, each a bool, absent keys off). K, S and O
act in the planner (A2Planner); R with F is the renewal step after step 1: a2.live_renewals marks the
PD column of each renewable live lease opened at t at no cost and its window goes to the layer, so X1
keeps the lease; F is also passed to the layer as `profit_idle` (it acts there only under X2's
timer). report()['px'] is the planner's knob block (None for px=None). renew_live with predictions is
refused (R's practical curve would omit the renewal rent, §2.3).

Guarantees: the slow loop's as in A2-A5 in their cores; the handler, redundancy, capacity layering,
contract rules and the composition are heuristics (design Table 5.7, Table 3.4); the knobs are
labeled heuristics with no ratio of their own (§2.3).
"""
from __future__ import annotations

import dataclasses
from typing import Optional

import numpy as np

from ..instance import active_units
from ..policies.base import Policy
from ..types import INF, PublicView, SlowObs
from .a2 import A2Planner, SITE_ORDERS, VIEW_TRANSFORMS, live_renewals, resolve_px
from .a5 import G2, DoublingCombiner, FollowPrediction
from .common import (LeaseBook, PolicyError, column_cost, policy_streams, resolve_params, slot_max_demand,
                     treated_as_protected)
from .contracts import p1_mask, p3_mask
from .execution import ExecutionLayer
from .handler import REACTIONS, PredictedShare, ReclaimHandler
from .marking import MarkingSiteRule
from .redundancy import MODES as REDUNDANCY_MODES, RedundancyRule

VARIANTS = ("practical", "theory")
CONTRACT_RULES = ("P1", "P2", "P3", "P4")      # P1 and P3 restrict the candidate mask; P2, P4 do not (§11)
LAYER_TAG = "a6"


def _ro(a: np.ndarray) -> np.ndarray:
    a = np.array(a, copy=True)
    a.setflags(write=False)
    return a


def view_without_protected(view: PublicView) -> PublicView:
    """Copy of the view without the contracts that treated_as_protected flags (menus, price INF,
    beta~ INF): the handler's view under 'revocable_only', whose protected search then finds none."""
    flagged = [k for k in range(len(view.contracts)) if treated_as_protected(view, k)]
    if not flagged:
        return view
    sites = tuple(dataclasses.replace(s, menu=tuple(k for k in s.menu if k not in flagged)) for s in view.sites)
    price = np.array(view.price, dtype=np.float64, copy=True)
    bt = np.array(view.beta_tilde_usd, dtype=np.float64, copy=True)
    price[:, flagged] = INF
    bt[:, :, flagged] = INF
    return dataclasses.replace(view, sites=sites, price=_ro(price), beta_tilde_usd=_ro(bt))


def contract_mask(view: PublicView, rules, view_transform: Optional[str] = None,
                  switch: str = "c2sw") -> tuple[np.ndarray, dict]:
    """(m, J, K) candidate mask of A6's contract rules (§11, §14) and a summary: P1 (p1_mask, with
    every H_k read as 0 under 'notice_oblivious'), then P3 (p3_mask on P1's mask; off under
    'notice_oblivious'). Without rules the mask is every offered (l, k) for every LLM.
    ('revocable_only' is applied by A2Planner on top of this mask.)"""
    m, J, K = len(view.sites), len(view.llms), len(view.contracts)
    offered = np.zeros((m, K), dtype=bool)
    for l, s in enumerate(view.sites):
        for k in s.menu:
            if np.isfinite(view.price[l, k]):
                offered[l, k] = True
    rules = list(rules)
    m1 = p1_mask(view, ignore_notice=(view_transform == "notice_oblivious")) if "P1" in rules else offered
    p3 = "P3" in rules and view_transform != "notice_oblivious"
    M = p3_mask(view, m1, switch=switch) if p3 else np.repeat(m1[:, None, :], J, axis=1)
    M = np.asarray(M, dtype=bool) & offered[:, None, :]
    info = {"rules": rules, "P1": "P1" in rules, "P3": p3, "offered_pairs": int(offered.sum()),
            "after_P1_pairs": int(m1.sum()), "candidates": int(M.sum()), "offered_candidates": int(offered.sum()) * J,
            "removed_P1": [[int(l), int(k)] for l, k in zip(*np.nonzero(offered & ~m1))],
            "removed_P3": [[int(l), int(j), int(k)] for l, j, k in zip(*np.nonzero(np.repeat(m1[:, None, :], J, axis=1)
                                                                                   & ~M))]}
    return M, info


def _is_num(v) -> bool:
    return isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool)


class A6(Policy):
    """Sublet (§14). Driver inputs: N_bound (variant 'theory'); pred_cols and pred_demand
    (predictions=True; pred_demand also for reaction 'test_a')."""
    name = "A6"
    PARAMS = {"variant": "practical", "x2": "timer", "zeta": 2.0, "skip_rule": True, "contract_rules": ["P1", "P3"],
              "redundancy": "rule", "reaction": "c2sw", "switch": "c2sw", "drain": False, "marking": "auto",
              "predictions": False, "nu_per_day": None, "site_order": "auto", "view_transform": None,
              "px": None}
    INPUTS = ("N_bound", "pred_cols", "pred_demand")

    def __init__(self, **kw):
        self._p, inp = resolve_params(self.PARAMS, kw, self.name, inputs=self.INPUTS)
        p = self._p
        if p["variant"] not in VARIANTS:
            raise PolicyError(f"{self.name}: variant must be one of {VARIANTS}, got {p['variant']!r}")
        if p["x2"] not in ("timer", "reference"):
            raise PolicyError(f"{self.name}: x2 must be 'timer' or 'reference', got {p['x2']!r}")
        if not _is_num(p["zeta"]) or not p["zeta"] >= 1:
            raise PolicyError(f"{self.name}: zeta must be a number >= 1, got {p['zeta']!r}")
        for b in ("skip_rule", "drain", "predictions"):
            if not isinstance(p[b], (bool, np.bool_)):
                raise PolicyError(f"{self.name}: {b} must be a bool, got {p[b]!r}")
        cr = p["contract_rules"]
        if not isinstance(cr, (list, tuple)) or any(r not in CONTRACT_RULES for r in cr):
            raise PolicyError(f"{self.name}: contract_rules must be a list of {list(CONTRACT_RULES)}, got {cr!r}")
        if p["redundancy"] not in REDUNDANCY_MODES:
            raise PolicyError(f"{self.name}: redundancy must be one of {REDUNDANCY_MODES}, got {p['redundancy']!r}")
        if p["reaction"] not in REACTIONS:
            raise PolicyError(f"{self.name}: reaction must be one of {REACTIONS}, got {p['reaction']!r}")
        if p["switch"] not in ("c2sw", "beta"):
            raise PolicyError(f"{self.name}: switch must be 'c2sw' or 'beta', got {p['switch']!r}")
        if p["marking"] not in ("auto", "off"):
            raise PolicyError(f"{self.name}: marking must be 'auto' or 'off', got {p['marking']!r}")
        if p["nu_per_day"] is not None and (not _is_num(p["nu_per_day"]) or not p["nu_per_day"] >= 0):
            raise PolicyError(f"{self.name}: nu_per_day must be None or a number >= 0, got {p['nu_per_day']!r}")
        if p["site_order"] not in SITE_ORDERS:
            raise PolicyError(f"{self.name}: site_order must be one of {SITE_ORDERS}, got {p['site_order']!r}")
        if p["view_transform"] not in VIEW_TRANSFORMS:
            raise PolicyError(f"{self.name}: view_transform must be one of {VIEW_TRANSFORMS}, "
                              f"got {p['view_transform']!r}")
        px = resolve_px(p["px"], self.name)
        if px["renew_live"] and p["predictions"]:
            raise PolicyError(f"{self.name}: px.renew_live with predictions=True is not supported (the R curve of "
                              "the combiner would omit the renewal rent)")
        self.N_bound = inp.get("N_bound")
        self.pred_cols = inp.get("pred_cols")
        self.pred_demand = inp.get("pred_demand")
        if p["variant"] == "theory" and self.N_bound is None:
            raise PolicyError(f"{self.name}: variant 'theory' needs the driver input N_bound (§6.3)")
        if p["predictions"] and (self.pred_cols is None or self.pred_demand is None):
            raise PolicyError(f"{self.name}: predictions=True needs the driver inputs pred_cols and pred_demand (§4.2)")
        if p["reaction"] == "test_a" and self.pred_demand is None:
            raise PolicyError(f"{self.name}: reaction 'test_a' needs the driver input pred_demand (§10)")

    def params(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in self._p.items()}

    # -------------------------------------------------------- reset
    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        p = self._p
        vt = p["view_transform"]
        streams = policy_streams(rng)
        self.cand_mask, self.mask_info = contract_mask(view, p["contract_rules"], vt, p["switch"])
        self.planner = A2Planner(view, streams["main"], streams["order"],
                                 rbar=1 if p["variant"] == "practical" else "theory", N_bound=self.N_bound,
                                 d_mode="mK+1", protected_window=None, site_order_mode=p["site_order"],
                                 layering=True, view_transform=vt, cand_mask=self.cand_mask, px=p["px"])
        pl = self.planner
        self.pi = pl.site_perm
        self.book = LeaseBook()
        # X4: the reclaim handler
        self.predictions = bool(p["predictions"])
        reaction = "test_a" if (self.predictions and p["reaction"] == "c2sw") else p["reaction"]
        p_hat = PredictedShare(view, self.pred_demand) if reaction == "test_a" else None
        hview = view_without_protected(view) if vt == "revocable_only" else view
        self.handler = ReclaimHandler(hview, reaction=reaction, switch=p["switch"], drain=bool(p["drain"]),
                                      p_hat=p_hat)
        # X3: round robin, or marking under I2 (§8.3)
        self.marking_on = view.information == "I2" and p["marking"] != "off"
        site_rule = MarkingSiteRule(view, streams["marking"], mode="auto", move_at="handler",
                                    rebuy_at_phase_start=True) if self.marking_on else None
        self.layer = ExecutionLayer(view, self.book, x1=True, x2=p["x2"], x3=True, zeta=float(p["zeta"]),
                                    skip_rule=bool(p["skip_rule"]), site_rule=site_rule, handler=self.handler,
                                    site_perm=self.pi, protected_window=None, tag=LAYER_TAG,
                                    profit_idle=pl.px["renew_profit"])
        self.L = np.asarray(pl.prob.L, dtype=np.int64)
        self.redundancy = RedundancyRule(view, mode=p["redundancy"], nu_per_day=p["nu_per_day"],
                                         zeta=float(p["zeta"]), site_perm=self.pi, L=self.L, C=pl.prob.C)
        # predictions: FP and the combiner (§13.3, §13.4)
        self.fp = self.comb = None
        if self.predictions:
            Cp = np.asarray(pl.prob.C, dtype=np.float64)
            L = self.L

            def cost(l, j, k):
                c = float(Cp[l, j, k])
                return c if np.isfinite(c) else column_cost(view, l, j, k, int(L[k]))
            self.preds = [tuple(int(v) for v in F) for F in self.pred_cols]
            seen: dict[tuple, int] = {}
            self.pred_copy = []                    # copy index of each predicted column (M58)
            for F in self.preds:
                self.pred_copy.append(seen.get(F, 0))
                seen[F] = seen.get(F, 0) + 1
            self.fp = FollowPrediction(self.preds, L, cost, view.grid.T_slow, len(view.llms), len(view.sites))
            self.comb = DoublingCombiner(G2)
        self.cl_llm = np.asarray(pl.prob.cl_llm, dtype=np.int64)
        self.q_req = np.asarray(pl.prob.q_req, dtype=np.float64)
        self.delta_req = np.asarray(pl.prob.delta_req, dtype=np.float64)
        self.u = int(view.units_per_replica)
        self._r_open: dict[tuple, list[tuple[int, int, int]]] = {}    # slot key -> [(col, s, L)] realized
        self.stats = {"realized_R": 0, "realized_FP": 0, "refused_to_rounder": 0, "refused_rotated": 0,
                      "refused_unmatched": 0, "renewed": 0}

    # -------------------------------------------------------- helpers
    def _refusal(self, skey: tuple, site: int, t_buy: int, reason: str, t: int) -> None:
        """A refused layer purchase at the column's own site l0 refuses the realized PD column of type
        skey whose window covers the purchase slot (§6.5) and drops that window from the slot's
        coverage (layer.drop_window); one elsewhere (a rotated site) does not."""
        if int(site) != int(skey[0]):
            self.stats["refused_rotated"] += 1
            return
        for col, s, L in reversed(self._r_open.get(tuple(skey), ())):
            if s <= t_buy < s + L and self.planner.rounder.is_open(col):
                self.planner.refuse(col, t, reason)
                self.stats["refused_to_rounder"] += 1
                self.layer.drop_window(skey, s, t)      # M11: the refused window is not retried
                return
        self.stats["refused_unmatched"] += 1        # e.g. a slot that realizes a predicted column

    def _open_r(self, col: int, t: int) -> None:
        l, j, k, s, iota, L = self.planner.column(col)
        key = (l, j, k, iota)
        self.layer.open(key, t0=t, s=s, L=L)
        lst = self._r_open.setdefault(key, [])
        lst.append((int(col), int(s), int(L)))
        if len(lst) > 8:
            del lst[0]
        self.stats["realized_R"] += 1

    def _open_fp(self, i: int, t: int) -> None:
        l, j, k, s = self.preds[i]
        self.layer.open((l, j, k, self.pred_copy[i]), t0=t, s=s, L=int(self.L[k]))
        self.stats["realized_FP"] += 1

    def _r_cols(self, t: int, which: str) -> list[int]:
        out = []
        for col, t0 in self.planner.rounder.opened.items():
            if which == "buys":
                if t0 == t:
                    out.append(col)
            elif t0 <= t:
                l, j, k, s, iota, L = self.planner.column(col)
                if s + L > t:
                    out.append(col)
        return out

    def _r_cost(self, cols) -> float:
        C = self.planner.prob.C
        tot = 0
        for col in cols:
            l, j, k, s, iota, L = self.planner.column(col)
            tot += float(C[l, j, k])
        return tot

    # -------------------------------------------------------- act
    def act(self, obs: SlowObs):
        t = int(obs.t)
        pairs = self.book.begin(obs)
        # 1. results: layer, refusals to the rounder, spares
        for skey, site, t_buy, kind, reason in self.layer.absorb(pairs):
            self._refusal(skey, site, t_buy, reason, t)
        self.redundancy.on_results(pairs)
        # knob R (with F): renewals of live leases before the PD (design/q44_practical_sublet.md §2.1 step 2)
        if self.planner.px["renew_live"]:
            for col in live_renewals(self.planner, self.layer, obs, self.view):
                self._open_r(col, t)
                self.stats["renewed"] += 1
        # 3. the PD and the rounding on the requests of slot t
        opened_t = self.planner.slot(obs)
        D = slot_max_demand(obs)
        # 4.-5. the columns to realize, then the execution layer
        if self.predictions:
            n = active_units(D, self.u)
            reqs = [(int(self.cl_llm[c]), float(self.q_req[c]), self.delta_req[c], int(n[c]))
                    for c in np.nonzero(n)[0]]
            inc_r = float(self.planner.rounder.curve[t])
            inc_fp = self.fp.slot(t, reqs)

            def state_cost(w):
                return self.fp.state_cost(t) if w == "F" else self._r_cost(self._r_cols(t, "live"))

            def serv(w):
                return (inc_fp - self.fp.buys(t)) if w == "F" else (inc_r - self._r_cost(self._r_cols(t, "buys")))
            cur, switched = self.comb.step(inc_fp, inc_r, state_cost, serv)
            if cur == "F":
                for i in (self.fp.live(t) if switched else self.fp.purchases(t)):
                    self._open_fp(i, t)
            else:
                for col in (self._r_cols(t, "live") if switched else opened_t):
                    self._open_r(col, t)
        else:
            for col in opened_t:
                self._open_r(col, t)
        self.layer.step(obs)
        # 6. redundancy
        self.redundancy.step(obs, self.book, self.layer.slots.values(), D)
        # 7. the slot's actions after the pre-check
        return self.book.assemble(obs, self.view)

    # -------------------------------------------------------- report
    def opened_ref(self) -> dict:
        """{ref_key: opening slot} of the PD's opened columns (the shape of round_pd(...)['opened'])."""
        return self.planner.rounder.opened_ref()

    def report(self) -> dict:
        out = {"variant": self._p["variant"], "view_transform": self._p["view_transform"],
               "information": self.view.information,
               "marking": "on (I2)" if self.marking_on else ("off (I1)" if self.view.information != "I2" else "off"),
               **self.planner.report(), "contract_rules": self.mask_info, "exec": self.layer.report(),
               "handler": self.handler.report(), "redundancy": self.redundancy.report(),
               "realized": dict(self.stats), "book": dict(self.book.stats), "combiner": None,
               "px": self.planner.px_report()}
        if self.predictions:
            c = self.comb
            out["combiner"] = {"C_FP": c.CF, "C_R": c.CR, "total": c.total, "switches": c.switches,
                               "gamma": c.gamma, "followed": c.followed_rle(), "curve_FP": self.fp.curve.tolist(),
                               "n_pred_cols": len(self.preds), "label": getattr(self.pred_cols, "label", None),
                               "days": list(getattr(self.pred_cols, "days", []) or [])}
        return out


__all__ = ["A6", "VARIANTS", "CONTRACT_RULES", "contract_mask", "view_without_protected"]
