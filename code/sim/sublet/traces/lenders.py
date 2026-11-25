"""Lender slack series and correlation groups (design/sim_spec.md §3.4.2; design §5.2.2, §5.3.4).

Slack is the lender's first-party slack S_l(t) in GPUs per 5-min slot: `a1_slack_series.npz`
(six spot GPU pools, 177 days, 50,993 slots; key 'a1:<pool>') and `a2_slack_series.npz`
(20 MaaS clusters, one week, 2,016 slots; key 'a2:c00'..'a2:c19'). The MaaS `site_id`
groups come from `a12_sim_inputs.json` (`maas_clusters`).
"""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np

from ..paths import ANALYSIS_OUT

SPOT_L7 = ("a1:A100-SXM4-80GB", "a1:A800-SXM4-80GB", "a1:GPU-series-2", "a1:H800")
_FILES = {"a1": "a1_slack_series.npz", "a2": "a2_slack_series.npz"}


@lru_cache(maxsize=2)
def _npz(prefix: str) -> dict[str, np.ndarray]:
    with np.load(ANALYSIS_OUT / _FILES[prefix]) as z:
        return {k: z[k].astype(np.float64) for k in z.files}


@lru_cache(maxsize=1)
def _a12() -> dict:
    p = ANALYSIS_OUT / "a12_sim_inputs.json"
    if not p.is_file():
        raise FileNotFoundError(f"{p} is missing; run code/analysis/a12_sim_inputs.py (6G cap)")
    with open(p) as f:
        return json.load(f)


def lender_names(group: str = "all24") -> list[str]:
    """Trace lender keys of a group: 'maas20' (a2:c00..a2:c19), 'spot_L7' (the four L7 pools),
    'all24' (maas20 + spot_L7), 'spot_all' (the six a1 pools in file order)."""
    maas = [f"a2:{k}" for k in _npz("a2")]
    spot = [f"a1:{k}" for k in _npz("a1")]
    if group == "maas20":
        return maas
    if group == "spot_L7":
        return list(SPOT_L7)
    if group == "all24":
        return maas + list(SPOT_L7)
    if group == "spot_all":
        return spot
    raise KeyError(f"unknown lender group {group!r}; known: maas20, spot_L7, all24, spot_all")


def all_names() -> list[str]:
    """Every trace lender key (20 MaaS clusters and 6 spot pools)."""
    return lender_names("maas20") + lender_names("spot_all")


def slack(name: str) -> np.ndarray:
    """5-min slack series of a trace lender in GPUs (float64, a copy)."""
    prefix, _, key = name.partition(":")
    if prefix not in _FILES or key not in _npz(prefix):
        raise KeyError(f"unknown slack series {name!r}")
    return _npz(prefix)[key].copy()


def lender_kind(name: str) -> str:
    """'maas' for a2:* keys, 'spot' for a1:* keys."""
    if name.startswith("a2:"):
        return "maas"
    if name.startswith("a1:"):
        return "spot"
    raise KeyError(f"{name!r} is not a trace lender key")


def group_of(name: str) -> str:
    """Correlation group of one trace lender: 'site:<site_id>' for a MaaS cluster (a12), the
    pool's own key for a spot pool. Reads a12 only for MaaS keys."""
    if lender_kind(name) == "spot":
        return name
    key = name.partition(":")[2]
    for c in _a12()["maas_clusters"]:
        if c["npz_key"] == key:
            return f"site:{c['site_id']}"
    raise KeyError(f"MaaS cluster {name!r} not in a12_sim_inputs.json maas_clusters")


def groups(kind: str = "site_id") -> dict[str, str]:
    """Lender key -> correlation group for every trace lender.
    'site_id': MaaS clusters by site_id ('site:<site_id>'), each spot pool its own group;
    'none': every lender its own group; 'all': one group 'all'."""
    names = all_names()
    if kind == "site_id":
        return {n: group_of(n) for n in names}
    if kind == "none":
        return {n: n for n in names}
    if kind == "all":
        return {n: "all" for n in names}
    raise KeyError(f"unknown group kind {kind!r}; known: site_id, none, all")
