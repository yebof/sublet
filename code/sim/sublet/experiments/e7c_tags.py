"""The tags of E7c, the causal-demand rerun of MS7 (design/ms7/plan.md X1, C53; design/ms7/feasibility/causal.md,
RECOMMENDED DESIGN item 1). Kept apart from ms5b_common.TAGS, which the frozen confirmation pins; a name that is not
an E7c tag resolves through ms5b_common (the gate part's revealed-slot tags of §3, design/sublet_v2.md).

Every lag tag acts at slot t on the demand of slot t - 1 as revealed then (zeros at t = 0): exactly causal at slot
granularity, with no lookahead (the revealed-slot rule of the supplement's "Order within a slow slot" gives the main
runs up to Δs - Δf of lookahead). The tags and their revealed-slot counterparts (REVEALED_OF, main's tags):

  Sublet-lag     A8P, sublet_lag (ms5b_common): Sublet with inner A9 at demand_lag 1. The guard's test (T0g's G(t),
                 the safe expert's Q(t), the allowance LB'(t)) reads the realized slot, as Theorem W's soundness needs;
                 in every run without a projected slot and without an abort the executed trajectory is A9-lag's
                 (e7c_analysis.py reports the identity r0(Sublet-lag) = r0(A9-lag) on those runs)
  A9-lag         A9 {demand_lag 1} (ms5b_common)
  BL1-lag        BL1 {demand_lag 1} (ms5b_common)
  BL1-BO-lag     BL1 {backoff_cap 288, demand_lag 1}
  BL2-lag        BL2 {demand_lag 1} (ski.py's MS7 option, siloed runner)
  BL3-0-lag      BL3 {n_extra 0, demand_lag 1} (spothedge.py's MS7 option)
  BL4-lag        BL4 {demand 'previous0'} (cocar.py: zeros in the first window; every other window plans on the
                 previous window's realized slot means, already causal)
  BL5-tau60-lag  BL5 {tau_min 60}: BL5-tau60 in BL5's lagged build (use_current_slot false: the rule at slot t reads
                 slots up to t - 1)
  BL5N-lag       BL5 {contract_rule 'c2', mbb true}: BL5N in BL5's lagged build
  BL1N-lag       A9 {target 'ceil', release 'now', demand_lag 1}
  BL1-GP-lag     A8P, bl1_gp_lag: BL1-GP with inner BL1 at demand_lag 1; labeled "inner lagged; the guard reads the
                 realized slot" (it projects at thousands of slots on revealed demand, so it is not a causal policy;
                 the label favors the baseline)

The RetroRenting-style rows need no lag tag: BL5's default build is the lagged one, so main's BL5 runs are lagged BL5
and lagged BL5-cur (LAGGED_FROM_MAIN). Lagged sets: H1_LAGGED (H1's set of design/sublet_v2.md §6 in lagged form)
and NOTICE_LAGGED (H2b's notice-aware set in lagged form), each {revealed tag: lagged tag}.

Status: the lag options are design rules; A9's rules stay HEURISTIC and no competitive ratio is claimed for A9 on the
full model; Sublet-lag's guarantee is the guard's (Theorem W(a)(b) for A8P through Remark R, PROVEN, audited), with
the test on the realized slot.
"""
from __future__ import annotations

import copy
from typing import Iterable

from . import ms5b_common as m5
from .ms5b_common import Tag

LAG = 1                                            # slots (Δs = 5 min)


def _bl1_gp_lag(inst) -> dict:
    """BL1-GP-lag: BL1-GP's parameters (ms5b_common._bl1_gp: Sublet's guard at P2's allowance around BL1) with the
    inner BL1 at demand_lag 1."""
    return {**m5.sublet_v2_params(inst), "inner": "BL1", "inner_params": {"demand_lag": LAG}}


PARAM_RULES = {"sublet_lag": m5.PARAM_RULES["sublet_lag"], "bl1_gp_lag": _bl1_gp_lag}
PARAM_RULE_TEXT = {"sublet_lag": m5.PARAM_RULE_TEXT["sublet_lag"],
                   "bl1_gp_lag": "ms5b_common.sublet_v2_params(inst) with inner 'BL1' and inner_params "
                                 "{'demand_lag': 1}"}

# the tags of ms5b_common.TAGS that E7c repeats, as the same objects (part gate reproduces part second's runs of them)
SHARED = ("Sublet-lag", "A9-lag", "BL1-lag")
TAGS = {**{n: m5.TAGS[n] for n in SHARED}, **{t[0]: Tag(*t[1:]) for t in (
    ("BL1-BO-lag", "BL1", {"backoff_cap": 288, "demand_lag": LAG}, "lag", False, "BL1-BO on slot t - 1's demand"),
    ("BL2-lag", "BL2", {"demand_lag": LAG}, "lag", False, "BL2 on slot t - 1's demand (siloed runner)"),
    ("BL3-0-lag", "BL3", {"n_extra": 0, "demand_lag": LAG}, "lag", False, "BL3-0 on slot t - 1's demand"),
    ("BL4-lag", "BL4", {"demand": "previous0"}, "lag", False,
     "BL4 without the first window's lookahead (every window on the previous window's slot means)"),
    ("BL5-tau60-lag", "BL5", {"tau_min": 60}, "lag", False, "BL5-tau60 in BL5's lagged build"),
    ("BL5N-lag", "BL5", {"contract_rule": "c2", "mbb": True}, "lag", False, "BL5N in BL5's lagged build"),
    ("BL1N-lag", "A9", {"target": "ceil", "release": "now", "demand_lag": LAG}, "lag", True,
     "BL1N on slot t - 1's demand"),
    ("BL1-GP-lag", "A8P", "bl1_gp_lag", "lag", False, "inner lagged; the guard reads the realized slot"),
)}}
LAG_TAGS = tuple(TAGS)                             # the 11 tags of part lag, in this order
REVEALED_OF = {"Sublet-lag": "Sublet", "A9-lag": "A9", "BL1-lag": "BL1", "BL1-BO-lag": "BL1-BO", "BL2-lag": "BL2",
               "BL3-0-lag": "BL3-0", "BL4-lag": "BL4", "BL5-tau60-lag": "BL5-tau60", "BL5N-lag": "BL5N",
               "BL1N-lag": "BL1N", "BL1-GP-lag": "BL1-GP"}
# main's runs that are lagged already: {lagged row: (main's tag)}; the revealed counterpart of lagged BL5 is BL5-cur
LAGGED_FROM_MAIN = {"BL5": "BL5"}
REVEALED_OF_MAIN = {"BL5": "BL5-cur"}
H1_LAGGED = {"BL1": "BL1-lag", "BL1-BO": "BL1-BO-lag", "BL2": "BL2-lag", "BL3-0": "BL3-0-lag", "BL4": "BL4-lag",
             "BL5": "BL5", "BL5-cur": "BL5"}
NOTICE_LAGGED = {"BL5-tau60": "BL5-tau60-lag", "BL1-GP": "BL1-GP-lag", "BL1N": "BL1N-lag", "BL5N": "BL5N-lag"}
GUARD_REALIZED = ("Sublet-lag", "BL1-GP-lag")      # lagged inner, the guard's test on the realized slot


def tag(name: str) -> Tag:
    """An E7c tag, else ms5b_common.tag(name) (KeyError if neither knows it)."""
    return TAGS[name] if name in TAGS else m5.tag(name)


def tag_params(name: str, inst=None) -> dict:
    """The resolved parameters of a tag on the run's own instance (the PARAM_RULES tags need it)."""
    if name not in TAGS:
        return m5.tag_params(name, inst)
    t = TAGS[name]
    if isinstance(t.params, str):
        if inst is None:
            raise ValueError(f"tag {name}: its parameters ({PARAM_RULE_TEXT[t.params]}) need the instance")
        return copy.deepcopy(PARAM_RULES[t.params](inst))
    return copy.deepcopy(dict(t.params))


def tag_params_text(name: str):
    if name not in TAGS:
        return m5.tag_params_text(name)
    t = TAGS[name]
    return PARAM_RULE_TEXT[t.params] if isinstance(t.params, str) else copy.deepcopy(dict(t.params))


def is_guarded(name: str) -> bool:
    return tag(name).id in m5.GUARDED_IDS


def tag_table(names: Iterable[str]) -> dict:
    """{tag: {policy_id, params (or their rule), kind, a9_family, role, information}} (ms5b_common.tag_table's shape),
    with 'revealed' (the revealed-slot counterpart in main) and 'guard_reads_realized_slot' for the lag tags."""
    out = {}
    for n in names:
        if n not in TAGS:
            out.update(m5.tag_table([n]))
            continue
        t = TAGS[n]
        out[n] = {"policy_id": t.id, "params": tag_params_text(n), "kind": t.kind, "a9_family": t.a9_family,
                  "role": t.role, "information": t.information, "revealed": REVEALED_OF[n],
                  "guard_reads_realized_slot": n in GUARD_REALIZED}
    return out


__all__ = ["LAG", "TAGS", "LAG_TAGS", "SHARED", "REVEALED_OF", "LAGGED_FROM_MAIN", "REVEALED_OF_MAIN", "H1_LAGGED",
           "NOTICE_LAGGED", "GUARD_REALIZED", "PARAM_RULES", "PARAM_RULE_TEXT", "tag", "tag_params",
           "tag_params_text", "is_guarded", "tag_table"]
