"""Borrower inputs (design/sim_spec.md §3.4.2; design §5.3.1-§5.3.3).

- Minute series of input and output tokens and requests (`a12_minute_io.npz`, written by
  code/analysis/a12_sim_inputs.py): Azure 2024 code and conversation, BurstGPT 1-3 and the
  BurstGPT splits by Model and Log Type.
- WildChat hour-of-week profiles p_o and region-tier shares r_oj (`a4b_wildchat_weekly.json`).
- Request streams for replay, read from the raw traces in chunks (marker needs_raw).

MS7 addition (design/ms7/plan.md §3 X2, design/ms7/feasibility/oos.md §3 and §4 item 3; change C55): the WildChat
calendar weeks of `a4c_wildchat_weeks.json` (code/analysis/a4c_wildchat_weeks.py): `wildchat_weeks` (the table of the
73 full weeks of the early window, each 'fit' or 'held_out'), `wildchat_week(index)` (one week's own separable
profile per region, mean 1: the borrowers key p_o_week) and the borrower model 'a4c_fit' of `wildchat` (p_o and
r_oj counted before the first held-out week only). The file is read only when one of them is called, so every
config without them reads a4b alone, as before.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import numpy as np

from ..paths import ANALYSIS_OUT, DATA

MIN_PER_WEEK = 10080
_SUFFIXES = ("__in", "__out", "__req")


@dataclass(eq=False)
class BorrowerSeries:
    name: str                  # e.g. 'azure2024_conv', 'burstgpt_2__GPT-4__conv'
    inp: np.ndarray            # (N,) input tokens per minute
    out: np.ndarray            # (N,) output tokens per minute
    req: np.ndarray            # (N,) requests per minute
    start_utc: Optional[str]   # ISO time of minute 0 (Azure), None (BurstGPT: relative)


def _need(path):
    if not path.is_file():
        raise FileNotFoundError(f"{path} is missing; run code/analysis/a12_sim_inputs.py (6G cap)")
    return path


@lru_cache(maxsize=1)
def _a12_npz() -> dict[str, np.ndarray]:
    with np.load(_need(ANALYSIS_OUT / "a12_minute_io.npz")) as z:
        return {k: z[k] for k in z.files}


@lru_cache(maxsize=1)
def _a12_json() -> dict:
    with open(_need(ANALYSIS_OUT / "a12_sim_inputs.json")) as f:
        return json.load(f)


def series_names() -> list[str]:
    """Series names present in a12_minute_io.npz, in file order."""
    out = []
    for k in _a12_npz():
        for suf in _SUFFIXES:
            if k.endswith(suf):
                name = k[: -len(suf)]
                if name not in out:
                    out.append(name)
    return out


def series_length(name: str) -> int:
    """Number of minutes of a series (without loading a copy)."""
    if name not in series_names():
        raise KeyError(f"unknown borrower series {name!r}; known: {series_names()}")
    return len(_a12_npz()[name + "__out"])


def load_series(name: str) -> BorrowerSeries:
    """Input, output and request series of `name` from a12_minute_io.npz (float64 copies)."""
    if name not in series_names():
        raise KeyError(f"unknown borrower series {name!r}; known: {series_names()}")
    z = _a12_npz()
    st = _a12_json()["series"][name]["start_utc"]
    return BorrowerSeries(name, z[name + "__in"].astype(np.float64), z[name + "__out"].astype(np.float64),
                          z[name + "__req"].astype(np.float64), None if st == "relative" else st)


def weighted(series: BorrowerSeries, w_in: float) -> np.ndarray:
    """Weighted tokens per minute: output tokens + w_in * input tokens (design §5.3.1)."""
    return series.out + w_in * series.inp


def _how(n: int) -> np.ndarray:
    return (np.arange(n, dtype=np.int64) // 60) % 168


def hour_of_week_profile(x: np.ndarray) -> np.ndarray:
    """(168,) mean of x over the minutes i with (i // 60) % 168 == h (0 for an empty cell)."""
    x = np.asarray(x, dtype=np.float64)
    h = _how(len(x))
    s = np.bincount(h, weights=x, minlength=168)
    c = np.bincount(h, minlength=168)
    return np.divide(s, c, out=np.zeros(168), where=c > 0)


def xi(x: np.ndarray) -> np.ndarray:
    """Unit-mean fluctuation x / profile[(i // 60) % 168]; 1.0 where the profile is 0."""
    x = np.asarray(x, dtype=np.float64)
    p = hour_of_week_profile(x)[_how(len(x))]
    return np.divide(x, p, out=np.ones(len(x)), where=p > 0)


@lru_cache(maxsize=1)
def _a4b() -> dict:
    with open(ANALYSIS_OUT / "a4b_wildchat_weekly.json") as f:
        return json.load(f)["borrower_model"]


A4C_MODELS = ("a4c_fit",)          # borrower models of a4c_wildchat_weeks.json (C55)


@lru_cache(maxsize=1)
def _a4c() -> dict:
    p = ANALYSIS_OUT / "a4c_wildchat_weeks.json"
    if not p.is_file():
        raise FileNotFoundError(f"{p} is missing; run code/analysis/a4c_wildchat_weeks.py (6G cap)")
    with open(p) as f:
        return json.load(f)


def wildchat_weeks() -> list[dict]:
    """The full calendar weeks of a4c_wildchat_weeks.json (C55), in calendar order: {'index', 'start_utc' (Monday
    00:00 UTC), 'active_hours', 'split' ('fit' or 'held_out')}; index i is wildchat_week(i)."""
    return [dict(w) for w in _a4c()["weeks"]]


def wildchat_week(index: int) -> dict[str, np.ndarray]:
    """p_o of one calendar week (C55): {region: (168,) array}, a4c's 'p_o_week'[region][index]: the week's own
    user-hour counts smoothed by a4b's separable form and divided by their mean (mean 1, UTC, hw 0 = Monday 00:00);
    for a4c's pool_regions (south_southeast_asia, south_america) the counts of the pool_weeks (4) full weeks of the
    same split that end at the week (a4c's pool_window). KeyError for an index outside the table."""
    d = _a4c()
    n = len(d["weeks"])
    if isinstance(index, bool) or not isinstance(index, (int, np.integer)) or not 0 <= int(index) < n:
        raise KeyError(f"WildChat week {index!r} is not in a4c_wildchat_weeks.json (0..{n - 1})")
    return {o: np.asarray(v[int(index)], dtype=np.float64) for o, v in d["p_o_week"].items()}


def wildchat(model: str = "early") -> tuple[dict[str, np.ndarray], dict[str, dict[str, float]]]:
    """(p_o, r_oj) from a4b_wildchat_weekly.json borrower_model.<model>:
    p_o[region] = (168,) array 'p_o' (mean 1, UTC, hw 0 = Monday 00:00);
    r_oj[region][tier] = 'r_oj' (tiers 'M', 'L'; sums to 1 over regions and tiers).
    C55: a model of A4C_MODELS ('a4c_fit') is read from a4c_wildchat_weeks.json borrower_model.<model> instead, in
    the same form (p_o and r_oj of the fit part of the early window, before the first held-out week)."""
    bm = _a4c()["borrower_model"] if model in A4C_MODELS else _a4b()
    if model not in bm:
        raise KeyError(f"unknown WildChat borrower model {model!r}; known: {list(bm)}")
    e = bm[model]
    p_o = {o: np.asarray(v, dtype=np.float64) for o, v in e["p_o"].items()}
    r_oj = {o: {t: float(x) for t, x in v.items()} for o, v in e["r_oj"].items()}
    return p_o, r_oj


# ---------------------------------------------------------------- request streams (raw traces)
REQUEST_STREAMS = {
    "azure2024_conv": ("azure", "azure-llm-2024/AzureLLMInferenceTrace_conv_1week.csv"),
    "azure2023_code": ("azure", "azure-llm-2023/AzureLLMInferenceTrace_code.csv"),
    "azure2023_conv": ("azure", "azure-llm-2023/AzureLLMInferenceTrace_conv.csv"),
    "mooncake_conversation": ("mooncake", "mooncake/conversation_trace.jsonl"),
    "mooncake_toolagent": ("mooncake", "mooncake/toolagent_trace.jsonl"),
    "mooncake_synthetic": ("mooncake", "mooncake/synthetic_trace.jsonl"),
}
_CHUNK = 500_000


def load_requests(name: str, t0_s: float = 0.0, dur_s: Optional[float] = None,
                  n_max: Optional[int] = None) -> dict[str, np.ndarray]:
    """Request streams for replay (E8): keys 't_s' (seconds from the stream start), 'inp', 'out';
    at most n_max requests (the chunked reader stops after them).
    name in {'azure2024_conv', 'azure2023_code', 'azure2023_conv', 'mooncake_conversation',
    'mooncake_toolagent', 'mooncake_synthetic'}; reads raw files in chunks (6G cap; marker needs_raw).
    Azure: TIMESTAMP, ContextTokens, GeneratedTokens. Mooncake: timestamp (ms), input_length, output_length.

    The stream start is the first row of the file (the files are in time order). Requests with
    t0_s <= t_s < t0_s + dur_s are returned (dur_s None: to the end)."""
    if name not in REQUEST_STREAMS:
        raise KeyError(f"unknown request stream {name!r}; known: {list(REQUEST_STREAMS)}")
    kind, rel = REQUEST_STREAMS[name]
    path = DATA / rel
    t1_s = np.inf if dur_s is None else t0_s + dur_s
    parts: dict[str, list] = {"t_s": [], "inp": [], "out": []}
    n = 0

    def take(t, i, o) -> bool:
        """Append the requests of one chunk inside the window; True when the reader can stop."""
        nonlocal n
        keep = (t >= t0_s) & (t < t1_s)
        t, i, o = t[keep], i[keep], o[keep]
        if n_max is not None:
            t, i, o = t[: n_max - n], i[: n_max - n], o[: n_max - n]
        parts["t_s"].append(t); parts["inp"].append(i); parts["out"].append(o)
        n += len(t)
        return n_max is not None and n >= n_max

    if kind == "azure":
        import pandas as pd
        ts0 = None
        for c in pd.read_csv(path, usecols=["TIMESTAMP", "ContextTokens", "GeneratedTokens"], chunksize=_CHUNK):
            ts = pd.to_datetime(c.TIMESTAMP, format="mixed")
            if ts0 is None:
                ts0 = ts.iloc[0]
            t = (ts - ts0).dt.total_seconds().to_numpy(np.float64)
            stop = take(t, c.ContextTokens.to_numpy(np.float64), c.GeneratedTokens.to_numpy(np.float64))
            if stop or t[-1] >= t1_s:
                break
    else:
        ts0 = None
        buf = {"t": [], "i": [], "o": []}
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                if ts0 is None:
                    ts0 = r["timestamp"]
                buf["t"].append((r["timestamp"] - ts0) / 1000.0)
                buf["i"].append(r["input_length"]); buf["o"].append(r["output_length"])
                if len(buf["t"]) >= _CHUNK:
                    t = np.asarray(buf["t"], np.float64)
                    if take(t, np.asarray(buf["i"], np.float64), np.asarray(buf["o"], np.float64)) or t[-1] >= t1_s:
                        buf = None
                        break
                    buf = {"t": [], "i": [], "o": []}
        if buf is not None and buf["t"]:
            take(np.asarray(buf["t"], np.float64), np.asarray(buf["i"], np.float64), np.asarray(buf["o"], np.float64))
    return {k: (np.concatenate(v) if v else np.zeros(0)) for k, v in parts.items()}
