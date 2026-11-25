"""Policy A7, practical Sublet (design/q44_practical_sublet.md §2; registry id A7, "practical Sublet").

PS is A6 (design/sim_spec_ms2.md §14) with these settings as its defaults (§2.1):
- r-bar = 1 (variant 'practical'), predictions off, X2 'reference' (no idle timer n_idle), the view
  transform 'revocable_only' (BL7's, sim_spec_ms2 §15.8): no contract that
  common.treated_as_protected flags is a PD candidate, in X3's pool or in the handler's search, so
  the handler reacts cold ('no-protected');
- contract rule P1 only, with the candidate mask {k*(l)} per site on top (knob K; P3 off): k*(l) is
  the baselines' contract (sim_spec_ms2 §15.1), and a site without an unflagged contract has no
  candidate;
- the slot-loop knobs R (renew a live own lease at its own site that served load in t-1), F (only if
  that load at fallback price pays the lease's rent), S (no threshold opening for a covered request)
  and O (replica index by request order), as implemented in a2.A2Planner, a2.live_renewals and
  rounding.Rounder (§2.1 steps 2 and 3).
Every other A6 parameter keeps its build default (zeta = 2 and the skip rule for X3, redundancy
'rule', reaction and switch 'c2sw', drain off, marking 'auto', site order 'auto', d = mK + 1, the
instance's u). All A6 parameters can be overridden; a `px` object given to A7 is merged onto PS's
knobs (each key it names replaces PS's setting; px=None turns every knob off), so that the
leave-one-out rows of §2.2 are A7 with one key set to False.

Information class online-I1: the public view, the slot's revealed demand, own leases, notices and
served load; no hindsight statistic, no a-priori N (no driver input at the defaults); no knob reads
site_announced.
Under I2 A6's marking rule would switch on (marking 'auto'); PS was not studied there.

Status: a labeled heuristic with no proven ratio (§2.3). Its fractional PD is C3-T1's ORML-PD on the
menu restricted to {k*(l)}, mapped to the core by capacity layering (a heuristic, Q18); being
revocable-only, PS has no ratio against the full menu's OPT_eager independent of a_1 rho_1 / a_2
(C3-P5). The renewal makes cost_pr omit the renewal rent, so cost_pr is no cost bound for PS.
"""
from __future__ import annotations

import copy

from .a6 import A6

PS_PX = {"kstar_only": True, "renew_live": True, "renew_profit": True, "suppress_covered": True,
         "layer_order": True}
PS_SETTINGS = {"variant": "practical", "predictions": False, "x2": "reference",
               "view_transform": "revocable_only", "contract_rules": ["P1"], "px": dict(PS_PX)}


class PracticalSublet(A6):
    """Practical Sublet (A7): A6 with the PS settings of design/q44_practical_sublet.md §2.1 as its
    defaults. At the defaults it takes no driver input; the inputs of A6 stay accepted for overridden
    parameters (N_bound for variant 'theory'; pred_cols and pred_demand for predictions, which need
    px.renew_live off)."""
    name = "A7"
    PARAMS = {**A6.PARAMS, **copy.deepcopy(PS_SETTINGS)}
    INPUTS = A6.INPUTS

    def __init__(self, **kw):
        if isinstance(kw.get("px"), dict):
            kw = {**kw, "px": {**PS_PX, **kw["px"]}}
        super().__init__(**kw)

    def report(self) -> dict:
        out = super().report()
        out["policy"] = "A7"
        return out


__all__ = ["PracticalSublet", "PS_PX", "PS_SETTINGS"]
