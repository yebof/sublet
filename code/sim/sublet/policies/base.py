"""Policy base class (design/sim_spec.md §3.6, §5.2).

A policy sees the PublicView at `reset` and a SlowObs at every slow slot; it returns actions
(Buy, Release, Load, Unload, Drain, SetAdmission) that the engine applies at the slot's start
minute in list order. If `wants_fast` is True after `reset`, the engine also calls `on_fast`
after the routing of every fast slot; it may return only Drain and SetAdmission, effective from
the next fast slot.

MS2 additions (design/sim_spec_ms2.md §2.3, C6): the class attribute PARAMS (parameter name ->
default; empty for a policy without parameters), `params()` (the resolved parameters) and
`report()` (the policy's internal accounting, which the engine stores in
RunResult.metrics['policy'] after the last slot).
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from ..types import Action, FastObs, PublicView, SlowObs


class Policy:
    name: str = "policy"
    wants_fast: bool = False    # read by the engine after reset(), so reset() may set it
    PARAMS: dict = {}           # parameter name -> default (MS2 policies; the driver checks keys against it)

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        """Start of a run: keep the public view and the policy's random generator."""
        self.view: Optional[PublicView] = view
        self.rng = rng

    def act(self, obs: SlowObs) -> list[Action]:
        raise NotImplementedError

    def on_fast(self, obs: FastObs) -> list[Action]:
        return []

    def params(self) -> dict:
        """The resolved parameters of the policy (default: none)."""
        return {}

    def report(self) -> dict:
        """The policy's internal accounting at the end of a run (default: nothing)."""
        return {}
