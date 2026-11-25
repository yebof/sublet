"""Policy A4: A3 with marking under public reclaim information (design/sim_spec_ms2.md §8.3).

A4 is A3 whose execution layer uses `marking.MarkingSiteRule`: logical slots of one LLM and
contract with equal X3 pools share a mark state (M19); the site rule of M20 chooses marking
(MK1-MK3) or RR-renew (X3) per group. Without I2 and with `require_I2` (default) A4 runs as A3
and reports marking 'off (I1)' (M18); footprint-approximated I2 is not built. Marking draws come
from the policy's `marking` stream (§2.3).

Status: the family policy `family.Marking` is O1-D's algorithm (PROVEN, oblivious lender, I2); A4
runs marking per logical slot of the PD, which opens more than one column per window on the
family, so O1-D does not cover it; A4 is a heuristic (design Table 3.4).
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from ..types import PublicView
from .a3 import A3
from .common import PolicyError
from .execution import SiteRule
from .marking import MarkingSiteRule

M_PARAMS = {"site_rule": "auto", "move_at": "handler", "rebuy_at_phase_start": True, "require_I2": True}


class A4(A3):
    """A3 with the marking site rule of §8.3 under I2 (online-I2)."""
    name = "A4"
    PARAMS = {**A3.PARAMS, **M_PARAMS}
    TAG = "a4"

    def __init__(self, **kw):
        super().__init__(**kw)
        p = self._params
        if p["site_rule"] not in ("auto", "rr", "marking"):
            raise PolicyError(f"A4: site_rule must be 'auto', 'rr' or 'marking', got {p['site_rule']!r}")
        if p["move_at"] not in ("handler", "mark"):
            raise PolicyError(f"A4: move_at must be 'handler' or 'mark', got {p['move_at']!r}")
        for b in ("rebuy_at_phase_start", "require_I2"):
            if not isinstance(p[b], (bool, np.bool_)):
                raise PolicyError(f"A4: {b} must be a bool, got {p[b]!r}")

    def _site_rule(self, view: PublicView, streams: dict) -> Optional[SiteRule]:
        p = self._params
        if view.information != "I2" and p["require_I2"]:
            self.marking = "off (I1)"
            return None
        self.marking = "on"
        return MarkingSiteRule(view, streams["marking"], mode=p["site_rule"], move_at=p["move_at"],
                               rebuy_at_phase_start=p["rebuy_at_phase_start"],
                               protected_window=p["protected_window"])

    def report(self) -> dict:
        out = super().report()
        out["marking"] = self.marking if self.marking != "on" else out["exec"]["site_rule"]
        return out


__all__ = ["A4"]
