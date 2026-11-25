"""The market scale of E8's replay (design/sim_spec_ms4.md §7.4).

The fluid demand of a series borrower is Gamma times the overflow of its smoothed weighted-token series above its own
capacity C0, in replica loads (instance._series_model, _overflow; design §5.3.3): d(f) = Gamma (x_sm - C0)^+ / kappa_j.
The replay serves the whole request stream at the same scale. market_scale recovers Gamma, C0 and the own capacity in
sequence slots, floor(n_seq Gamma C0 / kappa_j) (the builder's C0_loads x 128), from the built instance and checks that
Gamma times the builder's overflow reproduces the instance's demand.

Copier generates the copies one second at a time and never stores them: each request r yields floor(Gamma) copies
plus one with probability Gamma - floor(Gamma); copy 0 keeps (t_r, inp_r, out_r); every further copy arrives at
t_r + U(0, 1) s with the sizes of a request drawn uniformly from the same minute. The draws come from
np.random.default_rng(seed) (the alignment), per second in a fixed order: the extra copies (one uniform per request,
only if Gamma has a fractional part), the arrival offsets, then the drawn requests. A further copy that arrives in the
next second is carried to it; the copies of a second are returned in arrival order with their weighted sizes
l = w_in inp + out. At Gamma = 9.32 this is about 2.5e8 copies a week (§7.4).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .requests import StreamIndex


@dataclass(frozen=True)
class MarketScale:
    """Gamma and own capacity of a one-borrower series instance (market_scale)."""
    borrower: str
    series: str
    gamma: float
    C0_wtok_per_min: float        # own capacity of the smoothed series (its quantile), weighted tokens per minute
    C0_loads: float               # Gamma C0 / kappa_j (the builder's borrower_stats C0_loads)
    own_slots: int                # floor(n_seq C0_loads)
    kappa_wtok_per_min: float
    w_in: float
    n_seq: int
    smoothing_min: int
    demand_max_rel_diff: float    # max |Gamma y - demand| / max(demand) over the fast slots (check of the scale)

    def record(self) -> dict:
        return dict(self.__dict__)


def market_scale(inst, n_seq: int, tol: float = 1e-9) -> MarketScale:
    """The market scale of a series instance with one borrower and one client (E8's instance, §7.3): Gamma =
    C0_loads kappa_j / C0 with C0 recomputed by the builder's own step (instance._overflow on the borrower's weighted
    series with its smoothing lead-in) and C0_loads from borrower_stats; ValueError unless Gamma times the builder's
    overflow, averaged to fast slots, equals clients.demand to `tol` relative (of the demand's maximum)."""
    from .. import instance as I
    from ..traces import borrowers as tb
    b = inst.config.get("borrowers") or {}
    if b.get("model") != "series" or len(b.get("list") or []) != 1 or inst.n != 1:
        raise ValueError("market_scale: E8's replay needs a series instance with one borrower and one client")
    if b.get("normalize", "none") != "none":
        raise ValueError("market_scale: borrowers.normalize is not supported (the replay serves the raw stream)")
    x = b["list"][0]
    j = int(inst.clients.llm[0])
    llm = inst.llms[j]
    ser = tb.load_series(x["series"])
    w = tb.weighted(ser, llm.w_in)
    sm, T = int(b["smoothing_min"]), inst.grid.horizon_min
    i = np.arange(-(sm - 1), T, dtype=np.int64)
    start = (x["week_index"] or 0) * tb.MIN_PER_WEEK
    y, C0, _ = I._overflow(w[(start + i) % len(w)], b, llm.kappa_wtok_per_min)
    st = inst.borrower_stats[x["id"]]
    if not C0 > 0:
        raise ValueError(f"market_scale: own capacity C0 = {C0!r} is not positive")
    gam = float(st["C0_loads"]) * llm.kappa_wtok_per_min / C0
    d = I._fast_mean(gam * y, inst.grid.fast_min)
    dem = np.asarray(inst.clients.demand[0], dtype=np.float64)
    scale = max(float(dem.max()), 1e-300)
    diff = float(np.max(np.abs(d - dem))) / scale if len(d) == len(dem) else math.inf
    if not diff <= tol:
        raise ValueError(f"market_scale: Gamma {gam:.6g} times the builder's overflow differs from the instance's "
                         f"demand by {diff:.3g} (relative)")
    return MarketScale(borrower=x["id"], series=x["series"], gamma=gam, C0_wtok_per_min=float(C0),
                       C0_loads=float(st["C0_loads"]), own_slots=int(math.floor(n_seq * float(st["C0_loads"]) + 1e-9)),
                       kappa_wtok_per_min=float(llm.kappa_wtok_per_min), w_in=float(llm.w_in), n_seq=int(n_seq),
                       smoothing_min=sm, demand_max_rel_diff=diff)


@dataclass(eq=False)
class Copier:
    """The copies of a sorted request stream (t_s, inp, out; memory-mapped or in memory) at the scale `gamma`,
    generated per second (module docstring). Call second(s) for s = 0, 1, 2, ... in order; finish() at the end."""
    t_s: np.ndarray
    inp: np.ndarray
    out: np.ndarray
    index: StreamIndex
    gamma: float
    w_in: float
    seed: int
    n_requests: int = 0           # requests read
    n_generated: int = 0          # copies generated (sum of the copy counts)
    n_emitted: int = 0            # copies returned by second()
    tokens_emitted: float = 0.0   # their weighted tokens
    n_beyond: int = 0             # further copies of the last second that arrive after the end (finish)
    tokens_beyond: float = 0.0
    _next: int = 0
    _carry_a: np.ndarray = field(default_factory=lambda: np.zeros(0))
    _carry_l: np.ndarray = field(default_factory=lambda: np.zeros(0))

    def __post_init__(self):
        g = float(self.gamma)
        if not (math.isfinite(g) and g >= 0):
            raise ValueError(f"Copier: gamma must be finite and >= 0, got {self.gamma!r}")
        self.G = int(math.floor(g))
        self.frac = g - self.G
        self.rng = np.random.default_rng(int(self.seed))

    def second(self, s: int) -> np.ndarray:
        """The weighted sizes of the copies arriving in [s, s + 1), in arrival order (ties in generation order)."""
        if s != self._next:
            raise ValueError(f"Copier.second: seconds must be consecutive (expected {self._next}, got {s})")
        self._next = s + 1
        i0, i1 = int(self.index.sec[s]), int(self.index.sec[s + 1])
        n = i1 - i0
        parts_a, parts_l = [self._carry_a], [self._carry_l]
        self._carry_a = self._carry_l = np.zeros(0)
        if n:
            self.n_requests += n
            t = np.asarray(self.t_s[i0:i1], dtype=np.float64)
            lr = self.w_in * np.asarray(self.inp[i0:i1], dtype=np.float64) + np.asarray(self.out[i0:i1],
                                                                                         dtype=np.float64)
            if self.frac > 0:
                k = self.G + (self.rng.random(n) < self.frac)
            else:
                k = np.full(n, self.G, dtype=np.int64)
            self.n_generated += int(k.sum())
            if self.G >= 1:
                parts_a.append(t)
                parts_l.append(lr)
            else:
                m0 = k >= 1
                parts_a.append(t[m0])
                parts_l.append(lr[m0])
            kx = np.maximum(k - 1, 0)
            nx = int(kx.sum())
            if nx:
                ax = np.repeat(t, kx) + self.rng.random(nx)
                mi = s // 60
                lo, hi = int(self.index.mins[mi]), int(self.index.mins[mi + 1])
                jx = lo + np.minimum((self.rng.random(nx) * (hi - lo)).astype(np.int64), hi - lo - 1)
                lx = self.w_in * np.asarray(self.inp[jx], dtype=np.float64) + np.asarray(self.out[jx],
                                                                                          dtype=np.float64)
                late = ax >= s + 1
                if late.any():
                    self._carry_a, self._carry_l = ax[late], lx[late]
                    ax, lx = ax[~late], lx[~late]
                parts_a.append(ax)
                parts_l.append(lx)
        a = np.concatenate(parts_a)
        lw = np.concatenate(parts_l)
        if len(a) > 1:
            o = np.argsort(a, kind="stable")
            lw = lw[o]
        self.n_emitted += len(lw)
        self.tokens_emitted += float(lw.sum())
        return lw

    def finish(self) -> dict:
        """Count the carried copies that arrive after the last second read (outside the replayed window) and
        return the counters; n_generated = n_emitted + n_beyond."""
        self.n_beyond += len(self._carry_l)
        self.tokens_beyond += float(self._carry_l.sum())
        self._carry_a = self._carry_l = np.zeros(0)
        return {"gamma": float(self.gamma), "floor_gamma": self.G, "frac": self.frac, "seed": int(self.seed),
                "n_requests": self.n_requests, "n_generated": self.n_generated, "n_emitted": self.n_emitted,
                "tokens_emitted": self.tokens_emitted, "n_beyond": self.n_beyond, "tokens_beyond": self.tokens_beyond,
                "copies_balance": self.n_generated - self.n_emitted - self.n_beyond}


def mooncake_copies(trace, gamma: float, seed: int, t0_s: float = 0.0) -> dict:
    """The copies of a Mooncake trace at the scale `gamma` (§7.7): floor(gamma) copies of each request plus one with
    probability gamma - floor(gamma); copy 0 at t0_s + t_r, copy k >= 1 at t0_s + t_r + U(0, 1) s; every copy keeps
    its request's own sizes (Mooncake's sizes, so that ceil(input / 512) stays the block count) and its prefix blocks,
    copy k's blocks in its own namespace k, so that the replicated stream has the trace's global infinite-cache hit
    ratio (each namespace is the trace once). Draws from np.random.default_rng(seed): the extra copies (one uniform
    per request, only if gamma has a fractional part), then the offsets. Returns arrays sorted by arrival time:
    'a' (seconds), 'req' (request index), 'ns' (namespace), 'inp', 'out', with 'n_requests' and 'n_copies'."""
    g = float(gamma)
    G, frac = int(math.floor(g)), g - math.floor(g)
    rng = np.random.default_rng(int(seed))
    n = trace.n
    k = G + (rng.random(n) < frac) if frac > 0 else np.full(n, G, dtype=np.int64)
    req = np.repeat(np.arange(n, dtype=np.int64), k)
    ns = np.concatenate([np.arange(c, dtype=np.int64) for c in k]) if n else np.zeros(0, np.int64)
    a = float(t0_s) + trace.t_s[req]
    extra = ns >= 1
    a[extra] += rng.random(int(extra.sum()))
    o = np.argsort(a, kind="stable")
    return {"a": a[o], "req": req[o], "ns": ns[o], "inp": trace.inp[req[o]], "out": trace.out[req[o]],
            "n_requests": n, "n_copies": int(len(a)), "gamma": g, "seed": int(seed)}


__all__ = ["MarketScale", "market_scale", "Copier", "mooncake_copies"]
