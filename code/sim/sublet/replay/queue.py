"""The request-level replay with a queue (X7, design/ms8/plan.md D1; design/ms8/scout_x7_queue.md §2).

E8's per-second loop (loop.replay) sends a copy that finds no free sequence slot straight to fallback. Here such a copy
waits in one FIFO queue for at most W seconds; W = 0 is loop.replay itself (QueueReplay at W = 0 gives its routing,
fallback and stranding exactly). loop.py, scale.py and the package's __init__.py are unchanged, so E8 and E8 v2 stay
reproducible; this module is imported as sublet.replay.queue.

  QCopier       scale.Copier that also returns the arrival times and input sizes of the copies of a second, with the
                same draws in the same order (second() returns Copier.second's sizes bit for bit)
  QueueReplay   one replay state (a placement and a waiting limit W), stepped one second at a time, so that one copy
                generator feeds every state of a cell in lockstep (run_lockstep)
  window_classes  the class of every fast slot of a fluid run (reclaim, load, overflow, base)
  the TTFT model and its histograms (below)

The loop of QueueReplay per second s, in this order:
  1. the completions of the second free their slots (own capacity and every site; loop.replay's ring of buckets);
  2. at a fast-slot boundary the sites' slots become those of the new fast slot, and where a site's slots drop below
     its in-flight count the latest placed copies are stranded, their remaining work to fallback (loop.replay);
  3. reneging: the queued copies that arrived before s - W leave the queue for fallback at their full size;
  4. the free slots go first to the head of the queue, then to the copies arriving in [s, s + 1) in arrival order,
     each taking a free own slot, else a free slot at the site of least delta (stable order), as in loop.replay;
  5. the arrivals that find no slot join the end of the queue (at W = 0 they go to fallback, as in loop.replay).
The queue is ordered by arrival (a second's arrivals all come after every earlier second's), so FIFO, reneging from
the head and loop.replay's "latest placed first" stranding agree. A copy waits in whole seconds: one queued in second
s can start at s + 1 at the earliest. Waiting costs nothing up to W. A stranded copy is not queued again (its
remainder goes to fallback, as in E8, so the costs stay comparable). Copies still queued after the last second go to
fallback ('end').

TTFT model (D1; a5's assumptions): a copy served on own capacity or a leased replica has TTFT = wait + inp / P_j, wait
= s - a for a copy served from the queue in second s (0 for a copy served in its arrival second), P_j a5's
prefill_tok_per_s_per_replica of the tier (40k, 12k, 4k tokens/s for S, M, L; consistent with w_in = n_seq / (TPOT
P_j)). A fallback copy has TTFT = D_fb + inp / P_j, plus W if it waited (reneged, or still queued at the end). The
histograms (10 ms bins, the last bin collects every value from HIST_MAX_S on) are kept per window class of the copy's
arrival fast slot and per kind: 'served' holds wait + inp / P_j, 'fallback' and 'fallback_waited' hold inp / P_j only,
so that any D_fb (and the W of the waited copies) is applied afterwards by shifting them (e8q_analysis.py).
Interrupted (stranded) copies are counted, with their remaining work, by the class of the fast slot of the stranding.

Window classes (one per fast slot, the first that applies): 'reclaim' from the notice of a lease that carries a
replica of the client's LLM (its slow slot's first minute) to the lease's death plus the load time of the LLM at the
lease's site (inst.lam_s); 'load' while a replica of the LLM is loading (from its load_start minute to its first warm
fast slot, or to its end_fast if it ends before it is warm); 'overflow' where the fluid demand d(f) is positive; 'base' otherwise. demand_classes gives the last two
only (the all-fallback bill, which has no leases).
"""
from __future__ import annotations

import math
import time
from collections import deque
from typing import Optional, Sequence

import numpy as np

from .loop import TOKEN_REL_TOL, Placement, ServiceModel, _per_hour, token_costs
from .scale import Copier

CLASSES = ("reclaim", "load", "overflow", "base")
RECLAIM, LOAD, OVERFLOW, BASE = range(4)
KINDS = ("served", "fallback", "fallback_waited")
SERVED, FALLBACK, FALLBACK_WAITED = range(3)
BIN_S = 0.01                       # 10 ms bins
BIN_EPS = 1e-6                     # of a bin (10 ns): v / BIN_S is rounded up by this before the floor
HIST_MAX_S = 20.0                  # the last bin collects every value >= 20 s (max TTFT here: W 10 + inp / P_j <= 2 s)
N_BINS = int(round(HIST_MAX_S / BIN_S)) + 1
_FLUSH = 1 << 18                   # histogram indices buffered (per state) before one bincount


# ---------------------------------------------------------------- the copy generator with arrival times
class QCopier(Copier):
    """scale.Copier whose second3(s) returns (arrival times, weighted sizes, input tokens) of the copies arriving in
    [s, s + 1), in arrival order. The draws are Copier.second's, in the same order, so the sizes are Copier's bit for
    bit; second(s) returns them alone. Call either for s = 0, 1, 2, ... in order."""

    def __post_init__(self):
        super().__post_init__()
        self._carry_i = np.zeros(0)

    def second3(self, s: int):
        if s != self._next:
            raise ValueError(f"QCopier.second3: seconds must be consecutive (expected {self._next}, got {s})")
        self._next = s + 1
        i0, i1 = int(self.index.sec[s]), int(self.index.sec[s + 1])
        n = i1 - i0
        pa, pl, pi = [self._carry_a], [self._carry_l], [self._carry_i]
        self._carry_a = self._carry_l = self._carry_i = np.zeros(0)
        if n:
            self.n_requests += n
            t = np.asarray(self.t_s[i0:i1], dtype=np.float64)
            ip = np.asarray(self.inp[i0:i1], dtype=np.float64)
            lr = self.w_in * ip + np.asarray(self.out[i0:i1], dtype=np.float64)
            if self.frac > 0:
                k = self.G + (self.rng.random(n) < self.frac)
            else:
                k = np.full(n, self.G, dtype=np.int64)
            self.n_generated += int(k.sum())
            if self.G >= 1:
                pa.append(t)
                pl.append(lr)
                pi.append(ip)
            else:
                m0 = k >= 1
                pa.append(t[m0])
                pl.append(lr[m0])
                pi.append(ip[m0])
            kx = np.maximum(k - 1, 0)
            nx = int(kx.sum())
            if nx:
                ax = np.repeat(t, kx) + self.rng.random(nx)
                mi = s // 60
                lo, hi = int(self.index.mins[mi]), int(self.index.mins[mi + 1])
                jx = lo + np.minimum((self.rng.random(nx) * (hi - lo)).astype(np.int64), hi - lo - 1)
                ix = np.asarray(self.inp[jx], dtype=np.float64)
                lx = self.w_in * ix + np.asarray(self.out[jx], dtype=np.float64)
                late = ax >= s + 1
                if late.any():
                    self._carry_a, self._carry_l, self._carry_i = ax[late], lx[late], ix[late]
                    ax, lx, ix = ax[~late], lx[~late], ix[~late]
                pa.append(ax)
                pl.append(lx)
                pi.append(ix)
        a = np.concatenate(pa)
        lw = np.concatenate(pl)
        ip = np.concatenate(pi)
        if len(a) > 1:
            o = np.argsort(a, kind="stable")
            a, lw, ip = a[o], lw[o], ip[o]
        self.n_emitted += len(lw)
        self.tokens_emitted += float(lw.sum())
        return a, lw, ip

    def second(self, s: int) -> np.ndarray:
        return self.second3(s)[1]

    def finish(self) -> dict:
        self._carry_i = np.zeros(0)
        return super().finish()


# ---------------------------------------------------------------- window classes
def demand_classes(d: np.ndarray) -> np.ndarray:
    """(T_fast,) int8: OVERFLOW where d(f) > 0, else BASE."""
    d = np.asarray(d, dtype=np.float64)
    return np.where(d > 0, OVERFLOW, BASE).astype(np.int8)


def window_classes(res, inst, j: int = 0) -> np.ndarray:
    """(T_fast,) int8 class of every fast slot of a fluid run of the one-client instance `inst` (module docstring):
    RECLAIM, LOAD, OVERFLOW or BASE, the first that applies."""
    g = inst.grid
    Df, T_f = int(g.fast_min), int(g.T_fast)
    cls = demand_classes(np.asarray(inst.clients.demand[0], dtype=np.float64))
    if len(cls) != T_f:
        raise ValueError(f"window_classes: demand of {len(cls)} fast slots, the grid has {T_f}")
    reps = [r for r in res.replicas if int(r.llm) == j]
    load = np.zeros(T_f, dtype=bool)
    for r in reps:
        f0 = int(r.load_start_min) // Df
        f1 = min(int(r.warm_fast), int(r.end_fast), T_f)
        if f1 > f0:
            load[max(f0, 0):f1] = True
    by_lease = {}
    for r in reps:
        by_lease.setdefault(int(r.lease_id), []).append(r)
    lam = np.asarray(inst.lam_s, dtype=np.float64)
    rec = np.zeros(T_f, dtype=bool)
    for L in res.leases:
        if L.announce_slot is None or L.death_min is None or int(L.id) not in by_lease:
            continue
        notice_min = int(L.announce_slot) * int(g.slow_min)
        end_min = float(L.death_min) + float(lam[j, int(L.site)]) / 60.0
        f0 = notice_min // Df
        f1 = min(int(math.ceil(end_min / Df)), T_f)
        if f1 > f0:
            rec[max(f0, 0):f1] = True
    cls[load] = LOAD
    cls[rec] = RECLAIM
    return cls


def class_counts(cls: np.ndarray) -> dict:
    c = np.bincount(np.asarray(cls, dtype=np.int64), minlength=len(CLASSES))
    return {name: int(c[i]) for i, name in enumerate(CLASSES)}


def headroom(plan: Placement, d: np.ndarray) -> dict:
    """The share of fast slots in which the run's warm admitted capacity at the sites with an arc, sum_l W_l(f),
    exceeds the fluid demand d(f) (all slots, and the slots with d(f) > 0), with the mean of the excess in replica
    loads."""
    d = np.asarray(d, dtype=np.float64)
    W = plan.W[plan.order].sum(axis=0) if len(plan.order) else np.zeros_like(d)
    pos = d > 0
    return {"share_all": float(np.mean(W > d)) if len(d) else None,
            "share_overflow": float(np.mean(W[pos] > d[pos])) if pos.any() else None,
            "mean_excess_loads": float(np.mean(np.maximum(W - d, 0.0))) if len(d) else None,
            "mean_capacity_loads": float(np.mean(W)) if len(d) else None}


def zero_placement(plan: Placement) -> Placement:
    """The placement of the all-fallback bill (BL0a: no lease): `plan`'s costs with W = 0 and no arc."""
    return Placement(W=np.zeros_like(plan.W), delta=plan.delta.copy(), ok=np.zeros_like(plan.ok), q=plan.q,
                     mu_fb=plan.mu_fb, fast_min=plan.fast_min, site_ids=plan.site_ids)


# ---------------------------------------------------------------- histograms
def bins(v: np.ndarray) -> np.ndarray:
    """10 ms bin indices of non-negative values (bin b holds [b BIN_S, (b + 1) BIN_S), up to BIN_EPS of a bin for the
    round-off of v / BIN_S, so that 19.99 s is bin 1999; the last bin every value from HIST_MAX_S on)."""
    return np.minimum((np.asarray(v, dtype=np.float64) / BIN_S + BIN_EPS).astype(np.int64), N_BINS - 1)


def sparse(h: np.ndarray) -> Optional[dict]:
    """A histogram as {'lo': first non-zero bin, 'counts': the counts from lo to the last non-zero bin}; None if
    empty."""
    nz = np.flatnonzero(h)
    if not len(nz):
        return None
    lo, hi = int(nz[0]), int(nz[-1]) + 1
    return {"lo": lo, "counts": [int(x) for x in h[lo:hi]]}


def dense(sp: Optional[dict], n: int = N_BINS) -> np.ndarray:
    """The inverse of sparse (length n)."""
    h = np.zeros(n, dtype=np.int64)
    if sp:
        c = np.asarray(sp["counts"], dtype=np.int64)
        h[sp["lo"]:sp["lo"] + len(c)] = c
    return h


# ---------------------------------------------------------------- the replay state
class QueueReplay:
    """One replay state: the placement `plan`, own capacity `own_slots`, the waiting limit `wait_s` (W), the fast
    slots' window classes `classes` and fluid demand `demand` (T_fast,), the prefill throughput `prefill_tok_per_s`
    (P_j) and the horizon `n_seconds`. step(s, a, lw, inp) for s = 0, 1, ... with the copies of QCopier.second3(s);
    finish() at the end (module docstring)."""

    def __init__(self, plan: Placement, svc: ServiceModel, own_slots: int, ring_s: int, wait_s: float,
                 classes: np.ndarray, demand: np.ndarray, prefill_tok_per_s: float, n_seconds: int):
        if not (wait_s >= 0 and math.isfinite(wait_s)):
            raise ValueError(f"QueueReplay: the waiting limit must be finite and >= 0, got {wait_s!r}")
        self.t_wall = time.perf_counter()
        self.plan, self.svc, self.wmax = plan, svc, float(wait_s)
        self.order = order = plan.order
        self.k = k = len(order)
        self.slots = plan.slots(svc.n_seq)
        self.dsec = 60 * plan.fast_min
        if n_seconds > plan.T_fast * self.dsec:
            raise ValueError(f"QueueReplay: {n_seconds} s exceed the run's {plan.T_fast} fast slots")
        self.n_seconds = int(n_seconds)
        self.cls = np.asarray(classes, dtype=np.int64)
        self.dem = np.asarray(demand, dtype=np.float64)
        if self.cls.shape != (plan.T_fast,) or self.dem.shape != (plan.T_fast,):
            raise ValueError("QueueReplay: classes and demand need one value per fast slot")
        self.P = float(prefill_tok_per_s)
        self.R = R = int(ring_s)
        self.tpot = svc.tpot_s
        self.own_cap, self.own_busy = int(own_slots), 0
        self.own_done = np.zeros(R, np.int64)
        self.busy = np.zeros(k, np.int64)
        self.done = np.zeros((k, R), np.int64)
        self.cap = np.zeros(k, np.int64)
        self.cohorts = [deque() for _ in range(k)]
        self.tok_site = np.zeros(k)
        self.n_site = np.zeros(k, np.int64)
        self.dl = plan.delta[order]
        self.q = deque()                         # chunks [a, lw, x, class]: one second's arrivals that found no slot
        self.qlen = 0
        self.qmax = 0
        z = lambda dt=np.int64: np.zeros(len(CLASSES), dt)       # noqa: E731
        self.c_arr, self.c_own, self.c_leased, self.c_fbi, self.c_fbr, self.c_fbe = z(), z(), z(), z(), z(), z()
        self.c_queued, self.c_waited, self.c_strand = z(), z(), z()
        self.t_arr, self.t_fbi, self.t_fbr, self.t_fbe, self.t_rem = z(float), z(float), z(float), z(float), z(float)
        self.c_wait_sum = z(float)
        self.acc = {"tok_own": 0.0, "tok_fbi": 0.0, "tok_fbr": 0.0, "tok_fbe": 0.0, "tok_rem": 0.0, "n_own": 0,
                    "n_fbi": 0, "n_fbr": 0, "n_fbe": 0, "n_strand": 0, "strand_events": 0, "h_max": 0, "n_in": 0,
                    "tok_in": 0.0}
        self.fb_tok_f = np.zeros(plan.T_fast)    # fallback tokens (immediate, reneged, end, remainders) by event slot
        self.fb_n_f = np.zeros(plan.T_fast, np.int64)
        self.hist = np.zeros(len(CLASSES) * len(KINDS) * N_BINS, np.int64)
        self.whist = np.zeros(N_BINS, np.int64)  # waits of the copies served after waiting (all classes)
        self._buf, self._nbuf = [], 0
        self.n_f = -(-self.n_seconds // self.dsec)
        self.snap = np.zeros((self.n_f + 1, 4))
        self._next = 0
        self._f = -1
        self._c = BASE
        self._pos = np.arange(4096, dtype=np.int64)
        self._qcls = []                          # (class, count) of the queue's copies placed in the current second

    # -------------------------------------------------- helpers
    def _off(self, c: int, kind: int) -> int:
        return (int(c) * len(KINDS) + kind) * N_BINS

    def _add(self, idx: np.ndarray) -> None:
        if len(idx):
            self._buf.append(idx)
            self._nbuf += len(idx)
            if self._nbuf >= _FLUSH:
                self._flush()

    def _flush(self) -> None:
        if self._buf:
            self.hist += np.bincount(np.concatenate(self._buf), minlength=len(self.hist))
            self._buf, self._nbuf = [], 0

    def _fb_waited(self, cl, cx, c, f, end: bool) -> None:
        n, tok = len(cl), float(cl.sum())
        if end:
            self.acc["tok_fbe"] += tok
            self.acc["n_fbe"] += n
            self.c_fbe[c] += n
            self.t_fbe[c] += tok
        else:
            self.acc["tok_fbr"] += tok
            self.acc["n_fbr"] += n
            self.c_fbr[c] += n
            self.t_fbr[c] += tok
        self.fb_tok_f[f] += tok
        self.fb_n_f[f] += n
        self._add(self._off(c, FALLBACK_WAITED) + bins(cx))

    def _strand(self, i: int, e: int, S: int, f: int) -> None:
        taken, rem_sum = 0, 0.0
        R, done = self.R, self.done
        for coh in reversed(self.cohorts[i]):
            _, cs, ls, hs, alive = coh
            live = np.flatnonzero(alive & (cs > S))
            if not len(live):
                continue
            take = live[::-1][:e - taken]
            rem = ls[take] * ((cs[take] - S) / hs[take])
            rem_sum += float(rem.sum())
            np.subtract.at(done[i], cs[take] % R, 1)
            alive[take] = False
            taken += len(take)
            if taken == e:
                break
        if taken != e:
            raise RuntimeError(f"QueueReplay: site {int(self.order[i])} at second {S}: {taken} in-flight copies "
                               f"found for an excess of {e}")
        self.busy[i] -= taken
        self.tok_site[i] -= rem_sum
        self.acc["tok_rem"] += rem_sum
        self.acc["n_strand"] += taken
        self.acc["strand_events"] += 1
        c = int(self.cls[f])
        self.c_strand[c] += taken
        self.t_rem[c] += rem_sum
        self.fb_tok_f[f] += rem_sum

    # -------------------------------------------------- one second
    def step(self, s: int, a: np.ndarray, lw: np.ndarray, inp: np.ndarray, x: Optional[np.ndarray] = None,
             xb: Optional[np.ndarray] = None) -> None:
        """Second s with the copies (a, lw, inp) arriving in [s, s + 1) in arrival order; x = inp / P_j and xb =
        bins(x) may be passed when several states share them."""
        if s != self._next:
            raise ValueError(f"QueueReplay.step: seconds must be consecutive (expected {self._next}, got {s})")
        if s >= self.n_seconds:
            raise ValueError(f"QueueReplay.step: second {s} is past the horizon of {self.n_seconds} s")
        self._next = s + 1
        acc = self.acc
        R = self.R
        r = s % R
        xo = self.own_done[r]
        if xo:
            self.own_busy -= int(xo)
            self.own_done[r] = 0
        k = self.k
        if k:
            col = self.done[:, r]
            if col.any():
                self.busy -= col
                self.done[:, r] = 0
        f = s // self.dsec
        if s % self.dsec == 0:
            self._f = f
            self._c = int(self.cls[f])
            self.snap[f] = (acc["tok_fbi"] + acc["tok_fbr"] + acc["tok_fbe"] + acc["tok_rem"],
                            float(np.dot(self.dl, self.tok_site)), acc["n_strand"], acc["n_in"])
            self.cap = self.slots[:, f]
            if k:
                exc = self.busy - self.cap
                if exc.max() > 0:
                    for i in np.flatnonzero(exc > 0):
                        self._strand(int(i), int(exc[i]), s, f)
            # every fast slot (loop.replay: every 60th): a cohort placed before s - R has completed (holds < R - 1),
            # so dropping it changes nothing; it bounds the memory of many states in lockstep
            for dq in self.cohorts:
                while dq and dq[0][0] < s - R:
                    dq.popleft()
        elif self._f != f:
            raise RuntimeError("QueueReplay.step: a fast slot started without its boundary second")
        c = self._c
        n = len(lw)
        if n:
            if x is None:
                x = np.asarray(inp, dtype=np.float64) / self.P
            if xb is None:
                xb = bins(x)
            tok = float(lw.sum())
            acc["n_in"] += n
            acc["tok_in"] += tok
            # the longest hold of the second's arrivals, placed or not, as loop.replay's hold_max_s and ring guard
            # (rint and the product are monotone, so this is max(rint(lw * tpot)) bit for bit)
            hm = max(1, int(np.rint(float(lw.max()) * self.tpot)))
            if hm > acc["h_max"]:
                acc["h_max"] = hm
                if hm >= R - 1:
                    raise RuntimeError(f"QueueReplay: a hold of {hm} s does not fit the ring of {R} buckets")
            self.c_arr[c] += n
            self.t_arr[c] += tok
        # 3. reneging: queued copies that arrived before s - W
        if self.qlen:
            cut = s - self.wmax
            q = self.q
            while q:
                ca, cl, cx, cc = q[0]
                j = int(np.searchsorted(ca, cut, side="left"))
                if j == 0:
                    break
                self._fb_waited(cl[:j], cx[:j], cc, f, end=False)
                self.qlen -= j
                if j == len(ca):
                    q.popleft()
                else:
                    q[0] = [ca[j:], cl[j:], cx[j:], cc]
                    break
        if not n and not self.qlen:
            return
        # 4. free slots: the queue's head first, then the arrivals
        own_free = self.own_cap - self.own_busy
        if k:
            cum = np.cumsum(self.cap - self.busy)
            F = own_free + int(cum[-1])
        else:
            cum = None
            F = own_free
        nq = min(F, self.qlen)
        pieces_l = []
        if nq:
            got = 0
            q = self.q
            while got < nq:
                ca, cl, cx, cc = q[0]
                m = min(len(ca), nq - got)
                w = s - ca[:m]
                self.c_waited[cc] += m
                self.c_wait_sum[cc] += float(w.sum())
                self._add(self._off(cc, SERVED) + bins(w + cx[:m]))
                self.whist += np.bincount(bins(w), minlength=N_BINS)
                self._qcls.append((cc, m))
                pieces_l.append(cl[:m])
                got += m
                if m == len(ca):
                    q.popleft()
                else:
                    q[0] = [ca[m:], cl[m:], cx[m:], cc]
            self.qlen -= nq
        na = min(F - nq, n)
        if na:
            self._add(self._off(c, SERVED) + xb[:na])
        if nq:
            take_l = np.concatenate(pieces_l + [lw[:na]]) if na else np.concatenate(pieces_l)
        else:
            take_l = lw[:na]
        nt = len(take_l)
        if nt:
            h = np.rint(take_l * self.tpot)
            np.maximum(h, 1.0, out=h)
            h = h.astype(np.int64)
            comp = s + h
            k0 = min(nt, own_free)
            if k0 > 0:
                self.own_busy += k0
                np.add.at(self.own_done, comp[:k0] % R, 1)
                acc["tok_own"] += float(take_l[:k0].sum())
                acc["n_own"] += k0
            else:
                k0 = 0
            ns = nt - k0
            if ns > 0:
                pos = self._pos[:ns] if ns <= len(self._pos) else np.arange(ns, dtype=np.int64)
                site = np.searchsorted(cum, pos, side="right")
                ls, cs, hs = take_l[k0:], comp[k0:], h[k0:]
                cnt = np.bincount(site, minlength=k)
                self.busy += cnt
                self.n_site += cnt
                np.add.at(self.done, (site, cs % R), 1)
                self.tok_site += np.bincount(site, weights=ls, minlength=k)
                ends = np.cumsum(cnt)
                for i in np.flatnonzero(cnt):
                    b1 = int(ends[i])
                    b0 = b1 - int(cnt[i])
                    # copies, not views: a view would keep the second's whole arrays alive in every state
                    self.cohorts[i].append((s, cs[b0:b1].copy(), ls[b0:b1].copy(), hs[b0:b1].copy(),
                                            np.ones(b1 - b0, dtype=bool)))
            # own and leased counts by class: the queue's copies (in order) first, then the arrivals
            self._split_served(k0, nq, na, c)
        # 5. arrivals without a slot
        rest = n - na
        if rest:
            if self.wmax > 0:
                self.q.append([a[na:], lw[na:], x[na:], c])
                self.qlen += rest
                self.c_queued[c] += rest
                if self.qlen > self.qmax:
                    self.qmax = self.qlen
            else:
                rl = lw[na:]
                tk = float(rl.sum())
                acc["tok_fbi"] += tk
                acc["n_fbi"] += rest
                self.c_fbi[c] += rest
                self.t_fbi[c] += tk
                self.fb_tok_f[f] += tk
                self.fb_n_f[f] += rest
                self._add(self._off(c, FALLBACK) + xb[na:])

    def _split_served(self, k0: int, nq: int, na: int, c: int) -> None:
        """Book the copies placed this second as own (the first k0 in placement order) or leased, by class: the queue's
        copies (classes in self._qcls) come first, then the na arrivals of class c."""
        seq = self._qcls + ([(c, na)] if na else [])
        self._qcls = []
        left = k0
        for cc, m in seq:
            o = min(m, left)
            left -= o
            self.c_own[cc] += o
            self.c_leased[cc] += m - o

    # -------------------------------------------------- the end
    def finish(self, copier_stats: Optional[dict] = None) -> dict:
        """Copies still queued go to fallback ('end'); costs (loop.token_costs), counts, tokens, conservation (every
        copy served once, tokens to 1e-9 relative; with copier_stats also against the copier's counters), the
        fallback by fluid demand (event slot with d(f) = 0 or > 0), the per-class counters and histograms, the
        per-hour series and the queue's statistics."""
        f_end = max(0, min(self._f, self.plan.T_fast - 1))
        while self.q:
            ca, cl, cx, cc = self.q.popleft()
            self._fb_waited(cl, cx, cc, f_end, end=True)
        self.qlen = 0
        self._flush()
        acc = self.acc
        plan, svc = self.plan, self.svc
        order = self.order
        self.snap[self.n_f] = (acc["tok_fbi"] + acc["tok_fbr"] + acc["tok_fbe"] + acc["tok_rem"],
                               float(np.dot(self.dl, self.tok_site)), acc["n_strand"], acc["n_in"])
        routed = np.zeros(plan.m)
        routed[order] = self.tok_site
        by_site = np.zeros(plan.m, np.int64)
        by_site[order] = self.n_site
        fb_tok = acc["tok_fbi"] + acc["tok_fbr"] + acc["tok_fbe"]
        costs = token_costs(routed, fb_tok + acc["tok_rem"], acc["n_strand"], plan, svc)
        n_leased = int(self.n_site.sum())
        n_fb = acc["n_fbi"] + acc["n_fbr"] + acc["n_fbe"]
        served = acc["tok_own"] + float(self.tok_site.sum())
        stream = acc["tok_in"]
        tok_diff = abs(served + fb_tok + acc["tok_rem"] - stream)
        counts_ok = acc["n_own"] + n_leased + n_fb == acc["n_in"]
        cls_ok = bool(np.array_equal(self.c_own + self.c_leased + self.c_fbi + self.c_fbr + self.c_fbe, self.c_arr))
        cop_ok = True
        if copier_stats is not None:
            cop_ok = (copier_stats["n_emitted"] == acc["n_in"] and copier_stats.get("copies_balance", 0) == 0
                      and abs(copier_stats["tokens_emitted"] - stream) <= TOKEN_REL_TOL * max(1.0, stream))
        tok_ok = tok_diff <= TOKEN_REL_TOL * max(1.0, stream)
        unit = svc.wtok_per_load_h
        pos = self.dem > 0
        fbz, fbp = float(self.fb_tok_f[~pos].sum()), float(self.fb_tok_f[pos].sum())
        cons = {"pass": bool(counts_ok and tok_ok and cls_ok and cop_ok), "counts_exact": bool(counts_ok),
                "classes_exact": cls_ok, "copier_match": bool(cop_ok), "tokens_ok": bool(tok_ok),
                "copies": acc["n_in"], "own": acc["n_own"], "leased": n_leased, "fallback_immediate": acc["n_fbi"],
                "fallback_reneged": acc["n_fbr"], "fallback_end": acc["n_fbe"], "stranded": acc["n_strand"],
                "tokens_stream": stream, "tokens_served": served, "tokens_fallback": fb_tok + acc["tok_rem"],
                "tokens_rel_diff": tok_diff / max(1.0, stream), "tol": TOKEN_REL_TOL}
        H = self.hist.reshape(len(CLASSES), len(KINDS), N_BINS)
        by_class = {}
        for i, name in enumerate(CLASSES):
            by_class[name] = {
                "slots": int(np.sum(self.cls == i)), "copies": int(self.c_arr[i]), "tokens": float(self.t_arr[i]),
                "own": int(self.c_own[i]), "leased": int(self.c_leased[i]),
                "fallback_immediate": int(self.c_fbi[i]), "fallback_reneged": int(self.c_fbr[i]),
                "fallback_end": int(self.c_fbe[i]), "tokens_fallback_immediate": float(self.t_fbi[i]),
                "tokens_fallback_reneged": float(self.t_fbr[i]), "tokens_fallback_end": float(self.t_fbe[i]),
                "queued": int(self.c_queued[i]), "served_after_wait": int(self.c_waited[i]),
                "wait_sum_s": float(self.c_wait_sum[i]), "stranded": int(self.c_strand[i]),
                "tokens_stranded_remainder": float(self.t_rem[i]),
                "hist": {kn: sparse(H[i, kk]) for kk, kn in enumerate(KINDS)}}
        in_flight = int(self.busy.sum()) + self.own_busy
        return {"wait_s": self.wmax, "n_seconds": self.n_seconds, "ring_s": self.R, "hold_max_s": acc["h_max"],
                "own_slots": self.own_cap, "prefill_tok_per_s": self.P,
                "site_order": [plan.site_ids[i] for i in order],
                "counts": {"copies": acc["n_in"], "own": acc["n_own"], "leased": n_leased,
                           "leased_by_site": {plan.site_ids[i]: int(by_site[i]) for i in order},
                           "fallback": n_fb, "fallback_immediate": acc["n_fbi"], "fallback_reneged": acc["n_fbr"],
                           "fallback_end": acc["n_fbe"], "stranded": acc["n_strand"],
                           "strand_events": acc["strand_events"], "queued": int(self.c_queued.sum()),
                           "served_after_wait": int(self.c_waited.sum()), "queue_max": int(self.qmax),
                           "in_flight_at_end": in_flight},
                "tokens": {"stream": stream, "own": acc["tok_own"], "leased": float(self.tok_site.sum()),
                           "leased_by_site": {plan.site_ids[i]: float(routed[i]) for i in order},
                           "fallback": fb_tok, "fallback_immediate": acc["tok_fbi"], "fallback_reneged": acc["tok_fbr"],
                           "fallback_end": acc["tok_fbe"], "stranded_remainder": acc["tok_rem"]},
                "costs": costs,
                "fallback_by_demand": {
                    "zero": {"tokens": fbz, "usd": plan.q * fbz / unit, "copies": int(self.fb_n_f[~pos].sum()),
                             "slots": int((~pos).sum())},
                    "positive": {"tokens": fbp, "usd": plan.q * fbp / unit, "copies": int(self.fb_n_f[pos].sum()),
                                 "slots": int(pos.sum())}},
                "by_class": by_class, "wait_hist": sparse(self.whist), "conservation": cons,
                "per_hour": _per_hour(self.snap, self.dsec, plan, svc),
                "timing": {"wall_s": time.perf_counter() - self.t_wall}}


def run_lockstep(copier: QCopier, states: Sequence[QueueReplay], n_seconds: int, prefill_tok_per_s: float, *,
                 progress_s: Optional[int] = None, log=None) -> dict:
    """Seconds [0, n_seconds) of `copier` through every state (one generator, the same copies for all); returns the
    copier's counters and the timings (generation, the states' steps)."""
    t0 = time.perf_counter()
    t_gen = 0.0
    P = float(prefill_tok_per_s)
    for st in states:
        if st.P != P:
            raise ValueError("run_lockstep: the states have another prefill throughput")
    for s in range(n_seconds):
        tg = time.perf_counter()
        a, lw, inp = copier.second3(s)
        x = inp / P
        xb = bins(x)
        t_gen += time.perf_counter() - tg
        for st in states:
            st.step(s, a, lw, inp, x, xb)
        if progress_s and log and s and s % progress_s == 0:
            log(f"[lockstep] second {s} of {n_seconds}: {copier.n_emitted} copies, "
                f"{time.perf_counter() - t0:.1f} s")
    cstat = copier.finish()
    return {"copier": cstat, "timing": {"wall_s": time.perf_counter() - t0, "generate_s": t_gen}}


__all__ = ["CLASSES", "KINDS", "BIN_S", "BIN_EPS", "HIST_MAX_S", "N_BINS", "QCopier", "QueueReplay", "window_classes",
           "demand_classes", "class_counts", "headroom", "zero_placement", "bins", "sparse", "dense", "run_lockstep"]
