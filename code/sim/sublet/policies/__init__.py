"""Policies of the Sublet simulator: the base class and the trivial policies of §5.8."""
from .base import Policy
from .trivial import AlwaysFallback, FixedPlan, RenewReplay

__all__ = ["Policy", "AlwaysFallback", "FixedPlan", "RenewReplay"]
