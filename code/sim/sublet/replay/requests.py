"""Request streams of E8's replay (design/sim_spec_ms4.md §7.2, §7.4).

The Azure 2024 conversation week comes from traces.borrowers.load_requests (unchanged), read once by job
e8:requests and cached as three uncompressed .npy files, <stream>_t_s.npy, <stream>_inp.npy and <stream>_out.npy
(float64, written with np.save), which the replay jobs open with np.load(path, mmap_mode="r"): numpy does not
memory-map the members of an .npz archive (np.load with mmap_mode returns them as in-memory arrays). The cache's
record <stream>.json holds the window, the row count, the token totals, the largest sizes and the sha256 of each
array. t_s is in seconds from the stream start, the first row of the file, which is also minute 0 of the a12 minute
series that the fluid instance is built from (code/analysis/a12_sim_inputs.py: minute = floor of the seconds from
the first request), so second s of the replay lies in minute s // 60 of the fluid run.

load_requests drops Mooncake's hash_ids (traces/borrowers.py), so load_mooncake reads the Mooncake trace itself and
keeps them: per request the ids of its 512-token prefix blocks (BLOCK_TOKENS; ceil(input_length / 512) of them).

StreamIndex holds the offsets of the requests of each second and each minute (np.searchsorted on the sorted t_s),
which the copy generator of scale.py uses to read one second at a time from the memory-mapped arrays.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

AZURE_STREAM = "azure2024_conv"
MOONCAKE_STREAM = "mooncake_conversation"
CACHE_KEYS = ("t_s", "inp", "out")
BLOCK_TOKENS = 512                 # Mooncake hash_ids are 512-token prefix blocks (a5_reclaim_cost_calibration.py)
_CHUNK = 1 << 20                   # elements per chunk of the chunked passes over the cache


# ---------------------------------------------------------------- the Azure cache (job e8:requests)
def cache_paths(folder, stream: str = AZURE_STREAM) -> dict:
    """{'t_s', 'inp', 'out': <folder>/<stream>_<key>.npy, 'meta': <folder>/<stream>.json}."""
    f = Path(folder)
    out = {k: f / f"{stream}_{k}.npy" for k in CACHE_KEYS}
    out["meta"] = f / f"{stream}.json"
    return out


def save_npy(arr: np.ndarray, path) -> Path:
    """np.save of a float64 array to exactly `path` (an open file, so no '.npy' is appended to a '.partial' name)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as fh:
        np.save(fh, np.ascontiguousarray(arr, dtype=np.float64), allow_pickle=False)
    return p


def array_sha256(arr: np.ndarray) -> str:
    """sha256 of the array's bytes (C order), in chunks."""
    h = hashlib.sha256()
    a = np.asarray(arr)
    for i in range(0, len(a), _CHUNK):
        h.update(np.ascontiguousarray(a[i:i + _CHUNK]).tobytes())
    return h.hexdigest()


def stream_stats(t_s: np.ndarray, inp: np.ndarray, out: np.ndarray) -> dict:
    """Rows, time range, order, token totals and the largest input and output sizes of a stream (chunked passes)."""
    n = int(len(t_s))
    st = {"rows": n, "t_first_s": float(t_s[0]) if n else None, "t_last_s": float(t_s[-1]) if n else None,
          "input_tokens": 0.0, "output_tokens": 0.0, "max_inp": 0.0, "max_out": 0.0, "time_order_non_decreasing": True}
    last = -math.inf
    for i in range(0, n, _CHUNK):
        t = np.asarray(t_s[i:i + _CHUNK])
        if len(t) and (t[0] < last or np.any(np.diff(t) < 0)):
            st["time_order_non_decreasing"] = False
        if len(t):
            last = float(t[-1])
        a, b = np.asarray(inp[i:i + _CHUNK]), np.asarray(out[i:i + _CHUNK])
        st["input_tokens"] += float(a.sum())
        st["output_tokens"] += float(b.sum())
        st["max_inp"] = max(st["max_inp"], float(a.max()) if len(a) else 0.0)
        st["max_out"] = max(st["max_out"], float(b.max()) if len(b) else 0.0)
    return st


def load_azure(dur_s: Optional[float] = None, stream: str = AZURE_STREAM) -> dict:
    """The request stream from traces.borrowers.load_requests(stream, 0, dur_s) (dur_s None: the whole file)."""
    from ..traces.borrowers import load_requests
    return load_requests(stream, 0.0, None if dur_s is None else float(dur_s))


def open_cache(folder, stream: str = AZURE_STREAM, mmap: bool = True) -> tuple[dict, dict]:
    """(arrays {'t_s', 'inp', 'out'}, meta) of a cache written by job e8:requests: each array np.load(path,
    mmap_mode='r') (mmap False: in memory), checked against the record (rows, dtype float64, one length).
    FileNotFoundError if a file or the record is missing (run job e8:requests first)."""
    p = cache_paths(folder, stream)
    missing = [str(v) for v in p.values() if not v.is_file()]
    if missing:
        raise FileNotFoundError(f"request cache incomplete, missing {missing} (run job e8:requests first)")
    meta = json.loads(p["meta"].read_text())
    arrs = {k: np.load(p[k], mmap_mode="r" if mmap else None, allow_pickle=False) for k in CACHE_KEYS}
    n = {k: len(v) for k, v in arrs.items()}
    if len(set(n.values())) != 1 or n["t_s"] != meta.get("rows"):
        raise ValueError(f"request cache {p['meta']}: lengths {n} differ from the record's rows {meta.get('rows')}")
    bad = [k for k, v in arrs.items() if v.dtype != np.float64]
    if bad:
        raise ValueError(f"request cache: arrays {bad} are not float64")
    return arrs, meta


# ---------------------------------------------------------------- Mooncake (hash_ids kept)
@dataclass(eq=False)
class MooncakeTrace:
    """A Mooncake trace with its prefix blocks: t_s (seconds from the first row), inp, out (float64) and hash_ids
    (per request a list of block ids, in prefix order)."""
    name: str
    path: str
    t_s: np.ndarray
    inp: np.ndarray
    out: np.ndarray
    hash_ids: list

    @property
    def n(self) -> int:
        return int(len(self.t_s))

    def stats(self) -> dict:
        """Requests, duration, token totals, blocks (total and distinct), the share of blocks seen earlier in time
        order (an infinite global cache's hit ratio; a5's 0.366 for the conversation trace), the requests whose
        block count differs from ceil(input / 512), the distinct first blocks and the block ids that follow more
        than one predecessor (0: the ids are prefix-chained, so a cache that holds a block holds its whole prefix and
        a copy's cached blocks are the leading run of its blocks, loop.replay_replicas)."""
        seen, hits, total, mism = set(), 0, 0, 0
        parent, multi = {}, set()
        for i, h in enumerate(self.hash_ids):
            if len(h) != -(-int(self.inp[i]) // BLOCK_TOKENS):
                mism += 1
            for k, b in enumerate(h):
                total += 1
                if b in seen:
                    hits += 1
                else:
                    seen.add(b)
                pre = h[k - 1] if k else None
                if parent.setdefault(b, pre) != pre:
                    multi.add(b)
        return {"requests": self.n, "duration_s": float(self.t_s[-1] - self.t_s[0]) if self.n else 0.0,
                "input_tokens": float(self.inp.sum()), "output_tokens": float(self.out.sum()),
                "blocks_total": int(total), "blocks_unique": int(len(seen)),
                "block_hit_ratio_infinite_cache": hits / total if total else None,
                "requests_with_blocks_ne_ceil_input_over_512": int(mism),
                "first_blocks_distinct": len({h[0] for h in self.hash_ids if len(h)}),
                "blocks_with_more_than_one_predecessor": len(multi)}


def load_mooncake(name: str = MOONCAKE_STREAM, path=None) -> MooncakeTrace:
    """A Mooncake trace with hash_ids (load_requests drops them): the raw file of traces.borrowers.REQUEST_STREAMS
    [name] (or `path`), one JSON object per line with timestamp (ms), input_length, output_length and hash_ids;
    t_s is in seconds from the first row (the files are in time order, as load_requests assumes)."""
    from ..paths import DATA
    from ..traces.borrowers import REQUEST_STREAMS
    if path is None:
        kind, rel = REQUEST_STREAMS[name]
        if kind != "mooncake":
            raise ValueError(f"{name!r} is not a Mooncake stream")
        path = DATA / rel
    ts, inp, out, hs = [], [], [], []
    t0 = None
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if t0 is None:
                t0 = r["timestamp"]
            ts.append((r["timestamp"] - t0) / 1000.0)
            inp.append(r["input_length"])
            out.append(r["output_length"])
            hs.append([int(b) for b in (r.get("hash_ids") or [])])
    return MooncakeTrace(name, str(path), np.asarray(ts, np.float64), np.asarray(inp, np.float64),
                         np.asarray(out, np.float64), hs)


# ---------------------------------------------------------------- per-second offsets
@dataclass(eq=False)
class StreamIndex:
    """Offsets into a sorted stream: the requests of second s are rows sec[s]:sec[s + 1], those of minute m rows
    mins[m]:mins[m + 1] (s in [0, n_seconds), m in [0, ceil(n_seconds / 60)))."""
    n_seconds: int
    sec: np.ndarray
    mins: np.ndarray

    @staticmethod
    def build(t_s: np.ndarray, n_seconds: int) -> "StreamIndex":
        n = int(n_seconds)
        sec = np.searchsorted(t_s, np.arange(n + 1, dtype=np.float64), side="left").astype(np.int64)
        n_min = -(-n // 60)
        mins = np.searchsorted(t_s, 60.0 * np.arange(n_min + 1, dtype=np.float64), side="left").astype(np.int64)
        return StreamIndex(n, sec, mins)

    def requests_in(self, s0: int, s1: int) -> int:
        return int(self.sec[s1] - self.sec[s0])


def max_weighted(inp: np.ndarray, out: np.ndarray, w_in: float) -> float:
    """The largest weighted size w_in inp + out over a stream (chunked)."""
    m = 0.0
    for i in range(0, len(inp), _CHUNK):
        a = w_in * np.asarray(inp[i:i + _CHUNK]) + np.asarray(out[i:i + _CHUNK])
        if len(a):
            m = max(m, float(a.max()))
    return m


def file_info(path) -> dict:
    """Size and modification time of a raw file (provenance of the cache)."""
    p = Path(path)
    st = os.stat(p)
    return {"file": str(p), "file_bytes": int(st.st_size), "mtime": int(st.st_mtime)}


__all__ = ["AZURE_STREAM", "MOONCAKE_STREAM", "CACHE_KEYS", "BLOCK_TOKENS", "cache_paths", "save_npy",
           "array_sha256", "stream_stats", "load_azure", "open_cache", "MooncakeTrace", "load_mooncake",
           "StreamIndex", "max_weighted", "file_info"]
