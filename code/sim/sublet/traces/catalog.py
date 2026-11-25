"""LLM catalog entries (design/sim_spec.md §3.4.2; design Table 5.4).

Entries come from `a11_calibration.json` `catalog`, which carries the MaaS entries of
`a10_maas_catalog.json` (`maas_a10`: S, M, L and the sensitivity entries) and the a5 Llama-3
tiers (`a5_llama3`). No raw trace is read.
"""
from __future__ import annotations

import json
from functools import lru_cache

from ..paths import ANALYSIS_OUT

A5_TIER = {"S": "llama3-8b", "M": "llama3-70b", "L": "llama3.1-405b"}
CATALOGS = ("maas_a10", "a5_llama3")
_KEYS = ("g", "w_GB", "precision", "tier")


@lru_cache(maxsize=1)
def _catalog() -> dict:
    with open(ANALYSIS_OUT / "a11_calibration.json") as f:
        return json.load(f)["catalog"]


def names(catalog: str) -> list[str]:
    """Entry names of one catalog, in file order."""
    if catalog not in CATALOGS:
        raise KeyError(f"unknown catalog {catalog!r}; known: {CATALOGS}")
    return list(_catalog()[catalog])


def entry(catalog: str, name: str) -> dict:
    """Catalog entry `name` of `catalog` from a11_calibration.json catalog.<catalog>.<name>:
    keys g (int), w_GB, precision, and tier (maas_a10 only)."""
    if catalog not in CATALOGS:
        raise KeyError(f"unknown catalog {catalog!r}; known: {CATALOGS}")
    cat = _catalog()[catalog]
    if name not in cat:
        raise KeyError(f"no entry {name!r} in catalog {catalog!r}; known: {list(cat)}")
    e = cat[name]
    out = {k: e[k] for k in _KEYS if k in e}
    out["g"] = int(out["g"])
    out["w_GB"] = float(out["w_GB"])
    return out


def a5_tier_of(tier: str) -> str:
    """The a5 Llama-3 tier of the same letter: 'S'->'llama3-8b', 'M'->'llama3-70b', 'L'->'llama3.1-405b'."""
    if tier not in A5_TIER:
        raise KeyError(f"tier {tier!r} has no a5 counterpart; known: {list(A5_TIER)}")
    return A5_TIER[tier]


def tier_of_a5(name: str) -> str:
    """Inverse of a5_tier_of: the tier letter of an a5 entry name."""
    for t, n in A5_TIER.items():
        if n == name:
            return t
    raise KeyError(f"{name!r} is not an a5 tier; known: {list(A5_TIER.values())}")
