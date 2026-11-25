"""The tags of E7b, MS8's budget-cap runs (design/ms8/plan.md D2, X6; design/ms8/scout_x6_budget_cap.md §1, §2). Kept
apart from ms5b_common.TAGS, which the frozen confirmation pins, and from e7c_tags and ms7_baselines; a name that is not
an E7b tag resolves through ms5b_common (Sublet, A9, BL1 and BL1-GP, the references of the comparisons).

The cap tags (registry id CAP, algos/budget_cap.py; a naive spend cap, a labeled baseline with no guarantee):

  tag             inner  X          count  on_bind   role
  CR-cap-B        A9     'lb'       paid   stop      critical-ratio renting under a cap at Sublet's allowance B(t)
  CR-cap-0        A9     0          paid   stop      the same cap with no allowance
  CR-cap-5        A9     'rel:0.05' paid   stop      the same cap with 5% of the fallback so far
  CR-cap-B-latch  A9     'lb'       paid   latch     the cap that releases everything once, at its first bind
  CR-cap-B-slot   A9     'lb'       slot   stop      the cap that also prices the slot's purchases and rent
  GR-cap-B        BL1    'lb'       paid   stop      greedy renting under a cap at Sublet's allowance
  GR-cap-0        BL1    0          paid   stop      greedy renting under a cap with no allowance

The inner policies run at their defaults (A9 and BL1 as in the confirmation). The comparisons (e7b_analysis.py): every
cap against Sublet (A8P around A9 at the allowance 'lb'), the GR caps also against BL1-GP (the same guard around BL1),
and each cap against its inner policy alone (A9 or BL1).

Status: the caps are baselines; no ratio is claimed for any of them. The naive-cap result (design/theory/naive_caps.md,
PROVEN by example; code/theory_checks/c3/ms8/check_naive_cap.py) shows that each rule leaves out a term of Algorithm 1's
test and has an unbounded excess over FB + X on some instance.
"""
from __future__ import annotations

import copy
from typing import Iterable

from . import ms5b_common as m5
from .ms5b_common import Tag


def _cap(inner: str, X, count: str = "paid", on_bind: str = "stop") -> dict:
    return {"inner": inner, "X": X, "count": count, "on_bind": on_bind}


TAGS = {t[0]: Tag(*t[1:]) for t in (
    ("CR-cap-B", "CAP", _cap("A9", "lb"), "cap", True, "A9 under a naive cap at Sublet's allowance B(t), cost so far"),
    ("CR-cap-0", "CAP", _cap("A9", 0.0), "cap", True, "A9 under a naive cap with no allowance"),
    ("CR-cap-5", "CAP", _cap("A9", "rel:0.05"), "cap", True, "A9 under a naive cap at 5% of the fallback so far"),
    ("CR-cap-B-latch", "CAP", _cap("A9", "lb", on_bind="latch"), "cap", True,
     "A9 under the cap at B(t) that releases every lease once at its first bind and stops"),
    ("CR-cap-B-slot", "CAP", _cap("A9", "lb", count="slot"), "cap", True,
     "A9 under the cap at B(t) that also prices the slot's purchases and rent"),
    ("GR-cap-B", "CAP", _cap("BL1", "lb"), "cap", False, "BL1 under a naive cap at Sublet's allowance B(t)"),
    ("GR-cap-0", "CAP", _cap("BL1", 0.0), "cap", False, "BL1 under a naive cap with no allowance"),
)}
CAP_TAGS = tuple(TAGS)                                     # the seven cap tags, in this order
B_CAPS = ("CR-cap-B", "CR-cap-B-latch", "CR-cap-B-slot", "GR-cap-B")     # X = B(t): reading R1
INNER_TAG = {n: ("A9" if t.params["inner"] == "A9" else "BL1") for n, t in TAGS.items()}
GUARD_TAG = {n: ("Sublet" if t.params["inner"] == "A9" else "BL1-GP") for n, t in TAGS.items()}
REFERENCE_TAGS = ("Sublet", "A9", "BL1", "BL1-GP")         # MS5b tags the analysis compares with
IDENTITY_TAGS = ("Sublet", "A9")                           # rerun under L-tr against the confirmation's part main


def tag(name: str) -> Tag:
    """An E7b tag, else ms5b_common.tag(name) (KeyError if neither knows it)."""
    return TAGS[name] if name in TAGS else m5.tag(name)


def tag_params(name: str, inst=None) -> dict:
    """The resolved parameters of a tag on the run's own instance (Sublet's and BL1-GP's rules need it)."""
    if name in TAGS:
        return copy.deepcopy(dict(TAGS[name].params))
    return m5.tag_params(name, inst)


def tag_params_text(name: str):
    return copy.deepcopy(dict(TAGS[name].params)) if name in TAGS else m5.tag_params_text(name)


def is_cap(name: str) -> bool:
    return name in TAGS


def tag_table(names: Iterable[str]) -> dict:
    """{tag: {policy_id, params (or their rule), kind, a9_family, role, information}} (ms5b_common.tag_table's shape),
    with inner, inner_tag and guard_tag for the cap tags."""
    out = {}
    for n in names:
        if n not in TAGS:
            out.update(m5.tag_table([n]))
            continue
        t = TAGS[n]
        out[n] = {"policy_id": t.id, "params": tag_params_text(n), "kind": t.kind, "a9_family": t.a9_family,
                  "role": t.role, "information": t.information, "inner_tag": INNER_TAG[n], "guard_tag": GUARD_TAG[n],
                  "label": "naive spend cap (baseline, no guarantee)"}
    return out


__all__ = ["TAGS", "CAP_TAGS", "B_CAPS", "INNER_TAG", "GUARD_TAG", "REFERENCE_TAGS", "IDENTITY_TAGS", "tag",
           "tag_params", "tag_params_text", "is_cap", "tag_table"]
