"""The request-level replay of E8 (design/sim_spec_ms4.md §7.4-§7.6).

Service model (§7.5, ASSUMPTIONs): a replica serves at most n_seq = 128 concurrent sequences and decodes at its
tier's TPOT (15, 35, 60 ms for S, M, L: a5's concurrent_seqs_per_replica and tpot_s,
a5_reclaim_cost_calibration.json `assumptions`, the a5 tier of the same letter). A copy of weighted size
l = w_in inp + out holds one sequence slot for l TPOT seconds, so one slot processes 1 / TPOT weighted tokens per
second and a replica kappa_j / 60, with kappa_j = 60 n_seq / TPOT the fluid goodput (service_model checks this
against the instance's LLM). The loop runs in whole seconds: a copy that arrives in second s holds its slot during
the seconds s, ..., s + h - 1 with h = max(1, rint(l TPOT)) and frees it at the start of second s + h; its work
progresses linearly over the h seconds.

Placement (§7.4): the fluid run's RunResult.routing W (warm admitted capacity in replica loads per LLM, site and fast
slot), the client's routing costs delta (clients.delta_usd_per_h) and the engine's arcs (finite delta below q_j,
engine.py). At fast slot f the own capacity offers floor(n_seq Gamma C0 / kappa_j) sequence slots (scale.market_scale)
and site l floor(n_seq W_l(f)) slots.

`replay` is the per-second loop of the Azure week, vectorized within each second (numpy over the copies of the
second and over the sites; no Python loop per copy). Per second: (1) the completions of the second free their slots
(per-site completion counts in a ring of per-second buckets); (2) at a fast-slot boundary, the sites' slots are set
to those of the new fast slot, and where a site's slots drop below its in-flight count the excess copies are
stranded, latest arrivals first: their remaining work moves to fallback; (3) the copies of the second, in arrival order,
take a free own slot, else a free slot at the site of least delta (stable order, lowest site index on ties), else go
to fallback (a cumulative sum of the free slots over own capacity and the sites in delta order). The copies placed
on a site in one second are kept as one cohort (completion seconds, sizes, holds), so that stranding can pick the
latest arrivals and their remaining work.

`replay_replicas` is the replica-level loop of the Mooncake hour (§7.7), with or without prefix hits: the leased
replicas are the run's own (ReplicaPlan: replica records and drain events, checked against W), own capacity is cut
into replicas of n_seq slots, each replica keeps an infinite cache of the prefix blocks it has served (emptied when it
dies); with hits a copy's input counts only its blocks not in the cache of the replica it lands on, l = w_in
max(inp - 512 h, 0) + out, and within the cheapest class with a free slot (own capacity, then the sites in delta
order) the copy goes to the free replica with the longest cached prefix of its blocks (the leading run of its blocks
in the replica's cache; Mooncake's hash_ids are prefix-chained, so this is the number of its cached blocks), the
replica with the most free slots among those (lowest index on ties), and to the replica with the most free slots
(lowest index on ties) when no free replica of the class holds its first block. Every request of Mooncake's
conversation trace has the same first block, so a first-block rule would not separate the replicas. Without hits the
same loop runs with no cache. The cache state changes with every copy, so this loop is sequential per copy (about
1.2e4 requests times Gamma_mc copies in the hour).

Costs (§7.6), both in overflow accounting: routing sum delta_l l / (60 kappa_j) over the work done on leased
replicas, fallback q_j l / (60 kappa_j) over the copies sent to fallback plus the remaining work of stranded copies (a
replica-load-hour is 60 kappa_j weighted tokens), stranding mu_fb_j per stranded replica load (stranded copies /
n_seq), the engine's charge at the build default. Own capacity costs nothing in either model.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

import numpy as np

SLOT_EPS = 1e-9                   # floor(n_seq W + eps): W is a sum of admissions in [0, 1]
TOKEN_REL_TOL = 1e-9              # E8-1: tokens to 1e-9 relative


# ---------------------------------------------------------------- service model (§7.5)
@dataclass(frozen=True)
class ServiceModel:
    tier: str
    a5_tier: str
    n_seq: int                    # concurrent sequences per replica (a5 assumption)
    tpot_s: float                 # TPOT of the a5 tier (a5 assumption)
    w_in: float                   # weight of an input token (the instance's LLM, design Table 5.6)
    kappa_wtok_per_min: float     # 60 n_seq / TPOT, equal to the LLM's goodput

    @property
    def wtok_per_load_h(self) -> float:
        """Weighted tokens of one replica-load-hour, 60 kappa_j."""
        return 60.0 * self.kappa_wtok_per_min

    def hold_s(self, l: np.ndarray) -> np.ndarray:
        """Whole seconds a copy of weighted size l holds its slot: max(1, rint(l TPOT))."""
        h = np.rint(np.asarray(l, dtype=np.float64) * self.tpot_s)
        np.maximum(h, 1.0, out=h)
        return h.astype(np.int64)

    def record(self) -> dict:
        return dict(self.__dict__)


def service_model(inst, j: int = 0) -> ServiceModel:
    """The service model of LLM j of `inst` (§7.5): n_seq and TPOT from a5's assumptions (calib.A5) for the a5 tier of
    the LLM's tier letter, w_in the LLM's; ValueError unless 60 n_seq / TPOT equals the LLM's kappa (relative 1e-12),
    i.e. the replay's slots give the fluid model's goodput."""
    from .. import calib
    from ..traces.catalog import a5_tier_of
    llm = inst.llms[j]
    a5 = a5_tier_of(llm.tier)
    A = calib.A5["assumptions"]
    n_seq, tpot = int(A["concurrent_seqs_per_replica"]), float(A["tpot_s"][a5])
    kap = 60.0 * n_seq / tpot
    if abs(kap - llm.kappa_wtok_per_min) > 1e-12 * kap:
        raise ValueError(f"service_model: 60 x {n_seq} / {tpot} = {kap} differs from LLM {llm.id}'s kappa "
                         f"{llm.kappa_wtok_per_min} (kappa_mult != 1?)")
    return ServiceModel(tier=llm.tier, a5_tier=a5, n_seq=n_seq, tpot_s=tpot, w_in=float(llm.w_in),
                        kappa_wtok_per_min=float(llm.kappa_wtok_per_min))


# ---------------------------------------------------------------- placement (§7.4)
@dataclass(eq=False)
class Placement:
    """What the replay takes from a fluid run of a one-client instance: W (m, T_fast) admitted capacity of the
    client's LLM in replica loads, the client's delta (m,), the arcs ok (m,), q_j, mu_fb_j, the fast-slot length and
    the site ids."""
    W: np.ndarray
    delta: np.ndarray
    ok: np.ndarray
    q: float
    mu_fb: float
    fast_min: int
    site_ids: tuple

    @property
    def m(self) -> int:
        return int(len(self.delta))

    @property
    def T_fast(self) -> int:
        return int(self.W.shape[1])

    @property
    def order(self) -> np.ndarray:
        """The sites with an arc, by delta (stable: lowest site index on ties), as the engine's cheapest-first
        routing of one client (engine._route)."""
        idx = np.flatnonzero(self.ok)
        return idx[np.argsort(self.delta[idx], kind="stable")]

    def slots(self, n_seq: int) -> np.ndarray:
        """(len(order), T_fast) int64: floor(n_seq W) per site in `order` and fast slot."""
        return np.floor(n_seq * self.W[self.order] + SLOT_EPS).astype(np.int64)


def placement(res, inst) -> Placement:
    """The Placement of a fluid run with engine.record_routing true on a one-client instance (ValueError
    otherwise): W of the client's LLM, delta and the engine's arcs (finite delta below q_j)."""
    if res.routing is None:
        raise ValueError("placement: the run has no routing record (engine.record_routing false)")
    if inst.n != 1:
        raise ValueError(f"placement: the replay serves one client, the instance has {inst.n}")
    j = int(inst.clients.llm[0])
    q = float(inst.llms[j].q_usd_per_h)
    d = np.asarray(inst.clients.delta_usd_per_h[0], dtype=np.float64)
    ok = np.isfinite(d) & (d < q)
    return Placement(W=np.asarray(res.routing["W"][j], dtype=np.float64), delta=np.where(np.isfinite(d), d, 0.0),
                     ok=ok, q=q, mu_fb=float(inst.stranding.mu_fb_usd[j]), fast_min=int(inst.grid.fast_min),
                     site_ids=tuple(s.id for s in inst.sites))


def token_costs(routed_by_site: np.ndarray, fallback_tokens: float, n_stranded: float, plan: Placement,
                svc: ServiceModel) -> dict:
    """Routing, fallback and stranding in USD (§7.6): routed_by_site (m,) weighted tokens of work done on leased
    replicas per site, fallback_tokens the work sent to fallback (stranded remainders included), n_stranded the
    stranded copies (or stranded replica loads x n_seq)."""
    unit = svc.wtok_per_load_h
    r = float(np.dot(plan.delta, routed_by_site)) / unit
    fb = plan.q * float(fallback_tokens) / unit
    st = plan.mu_fb * float(n_stranded) / svc.n_seq
    return {"routing": r, "fallback": fb, "stranding": st, "total": r + fb + st}


# ---------------------------------------------------------------- the per-second loop of the Azure week
def ring_size(max_weighted_size: float, svc: ServiceModel) -> int:
    """Buckets of the completion ring: the longest hold of any copy plus 2."""
    return int(svc.hold_s(np.array([max_weighted_size]))[0]) + 2


def replay(copier, plan: Placement, svc: ServiceModel, own_slots: int, n_seconds: int, ring_s: int, *,
           progress_s: Optional[int] = None, log=None) -> dict:
    """The per-second loop (module docstring) over seconds [0, n_seconds) with the copies of `copier`
    (scale.Copier) through the placement `plan`; `ring_s` from ring_size of the stream's largest size. Returns
    counts, tokens, costs, the conservation check E8-1 (§7.9), per-hour series and timings."""
    t_wall = time.perf_counter()
    order = plan.order
    k = len(order)
    slots = plan.slots(svc.n_seq)
    dsec = 60 * plan.fast_min
    if n_seconds > plan.T_fast * dsec:
        raise ValueError(f"replay: {n_seconds} s exceed the run's {plan.T_fast} fast slots")
    R = int(ring_s)
    tpot = svc.tpot_s
    own_cap = int(own_slots)
    own_busy = 0
    own_done = np.zeros(R, np.int64)
    busy = np.zeros(k, np.int64)
    done = np.zeros((k, R), np.int64)
    cap = np.zeros(k, np.int64)
    cohorts = [deque() for _ in range(k)]
    tok_site = np.zeros(k)
    n_site = np.zeros(k, np.int64)
    acc = {"tok_own": 0.0, "tok_fb": 0.0, "tok_rem": 0.0, "n_own": 0, "n_fb": 0, "n_strand": 0, "strand_events": 0,
           "h_max": 0}
    n_f = -(-n_seconds // dsec)
    snap = np.zeros((n_f + 1, 4))          # cumulative fallback tokens, delta-weighted routed tokens, stranded, emitted
    dl = plan.delta[order]
    pos_cache = np.arange(4096, dtype=np.int64)

    def strand(i: int, e: int, S: int) -> None:
        taken, rem_sum = 0, 0.0
        for coh in reversed(cohorts[i]):
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
            raise RuntimeError(f"replay: site {int(order[i])} at second {S}: {taken} in-flight copies found for an "
                               f"excess of {e}")
        busy[i] -= taken
        tok_site[i] -= rem_sum
        acc["tok_rem"] += rem_sum
        acc["n_strand"] += taken
        acc["strand_events"] += 1

    t_gen = 0.0
    for s in range(n_seconds):
        r = s % R
        x = own_done[r]
        if x:
            own_busy -= int(x)
            own_done[r] = 0
        if k:
            col = done[:, r]
            if col.any():
                busy -= col
                done[:, r] = 0
        if s % dsec == 0:
            f = s // dsec
            snap[f] = (acc["tok_fb"] + acc["tok_rem"], float(np.dot(dl, tok_site)), acc["n_strand"],
                       copier.n_emitted)
            cap = slots[:, f]
            exc = busy - cap
            if k and exc.max() > 0:
                for i in np.flatnonzero(exc > 0):
                    strand(int(i), int(exc[i]), s)
            if f % 60 == 0:
                for dq in cohorts:
                    while dq and dq[0][0] < s - R:
                        dq.popleft()
                if progress_s and log and f and (f * dsec) % progress_s == 0:
                    log(f"[replay] second {s} of {n_seconds}: {copier.n_emitted} copies, "
                        f"{time.perf_counter() - t_wall:.1f} s")
        t0 = time.perf_counter()
        lw = copier.second(s)
        t_gen += time.perf_counter() - t0
        n = len(lw)
        if not n:
            continue
        h = np.rint(lw * tpot)
        np.maximum(h, 1.0, out=h)
        h = h.astype(np.int64)
        hm = int(h.max())
        if hm > acc["h_max"]:
            acc["h_max"] = hm
            if hm >= R - 1:
                raise RuntimeError(f"replay: a hold of {hm} s does not fit the ring of {R} buckets")
        comp = s + h
        k0 = min(n, own_cap - own_busy)
        if k0 > 0:
            own_busy += k0
            np.add.at(own_done, comp[:k0] % R, 1)
            acc["tok_own"] += float(lw[:k0].sum())
            acc["n_own"] += k0
        else:
            k0 = 0
        rest = n - k0
        if not rest:
            continue
        ns = 0
        if k:
            cum = np.cumsum(cap - busy)
            ns = min(rest, int(cum[-1]))
        if ns > 0:
            pos = pos_cache[:ns] if ns <= len(pos_cache) else np.arange(ns, dtype=np.int64)
            site = np.searchsorted(cum, pos, side="right")
            ls, cs, hs = lw[k0:k0 + ns], comp[k0:k0 + ns], h[k0:k0 + ns]
            cnt = np.bincount(site, minlength=k)
            busy += cnt
            n_site += cnt
            np.add.at(done, (site, cs % R), 1)
            tok_site += np.bincount(site, weights=ls, minlength=k)
            ends = np.cumsum(cnt)
            for i in np.flatnonzero(cnt):
                b1 = int(ends[i])
                b0 = b1 - int(cnt[i])
                cohorts[i].append((s, cs[b0:b1], ls[b0:b1], hs[b0:b1], np.ones(b1 - b0, dtype=bool)))
        nf = rest - ns
        if nf:
            acc["tok_fb"] += float(lw[k0 + ns:].sum())
            acc["n_fb"] += nf
    snap[n_f] = (acc["tok_fb"] + acc["tok_rem"], float(np.dot(dl, tok_site)), acc["n_strand"], copier.n_emitted)
    cstat = copier.finish()
    routed = np.zeros(plan.m)
    routed[order] = tok_site
    by_site = np.zeros(plan.m, np.int64)
    by_site[order] = n_site
    costs = token_costs(routed, acc["tok_fb"] + acc["tok_rem"], acc["n_strand"], plan, svc)
    n_leased = int(n_site.sum())
    stream = cstat["tokens_emitted"]
    served = acc["tok_own"] + float(tok_site.sum())
    fb = acc["tok_fb"] + acc["tok_rem"]
    tok_diff = abs(served + fb - stream)
    counts_ok = (acc["n_own"] + n_leased + acc["n_fb"] == cstat["n_emitted"]) and cstat["copies_balance"] == 0
    tok_ok = tok_diff <= TOKEN_REL_TOL * max(1.0, stream)
    in_flight = int(busy.sum())
    cons = {"pass": bool(counts_ok and tok_ok), "counts_exact": bool(counts_ok), "tokens_ok": bool(tok_ok),
            "copies": cstat["n_emitted"], "own": acc["n_own"], "leased": n_leased, "fallback": acc["n_fb"],
            "stranded": acc["n_strand"], "generated": cstat["n_generated"], "beyond_window": cstat["n_beyond"],
            "tokens_stream": stream, "tokens_served": served, "tokens_fallback": fb,
            "tokens_rel_diff": tok_diff / max(1.0, stream), "tol": TOKEN_REL_TOL}
    hours = _per_hour(snap, dsec, plan, svc)
    return {"n_seconds": int(n_seconds), "ring_s": R, "hold_max_s": acc["h_max"], "own_slots": own_cap,
            "site_order": [plan.site_ids[i] for i in order],
            "counts": {"copies": cstat["n_emitted"], "own": acc["n_own"], "leased": n_leased,
                       "leased_by_site": {plan.site_ids[i]: int(by_site[i]) for i in order},
                       "fallback": acc["n_fb"], "stranded": acc["n_strand"], "strand_events": acc["strand_events"],
                       "in_flight_at_end": in_flight + own_busy},
            "tokens": {"stream": stream, "own": acc["tok_own"], "leased": float(tok_site.sum()),
                       "leased_by_site": {plan.site_ids[i]: float(routed[i]) for i in order},
                       "fallback": acc["tok_fb"], "stranded_remainder": acc["tok_rem"]},
            "costs": costs, "conservation": cons, "copier": cstat, "per_hour": hours,
            "timing": {"wall_s": time.perf_counter() - t_wall, "generate_s": t_gen}}


def _per_hour(snap: np.ndarray, dsec: int, plan: Placement, svc: ServiceModel) -> dict:
    """Per-hour replay routing, fallback and stranding in USD from the cumulative snapshots at the fast-slot
    boundaries (a stranding is booked in the hour of its fast-slot boundary)."""
    per_h = max(1, 3600 // dsec)
    idx = np.arange(0, len(snap) - 1, per_h)
    idx = np.append(idx, len(snap) - 1)
    d = np.diff(snap[idx], axis=0)
    unit = svc.wtok_per_load_h
    return {"fallback_usd": (plan.q * d[:, 0] / unit).tolist(), "routing_usd": (d[:, 1] / unit).tolist(),
            "stranding_usd": (plan.mu_fb * d[:, 2] / svc.n_seq).tolist(), "copies": d[:, 3].astype(np.int64).tolist()}


# ---------------------------------------------------------------- replicas of a run (the Mooncake hour)
@dataclass(eq=False)
class ReplicaPlan:
    """The leased replicas of one LLM in a fluid run: ids, site, first warm fast slot, first fast slot without the
    replica (T_fast if it lives to the horizon) and first fast slot with admission 0 after a drain (T_fast if none
    applies). Admitted at f iff warm <= f < min(end, drain)."""
    ids: np.ndarray
    site: np.ndarray
    warm: np.ndarray
    end: np.ndarray
    drain: np.ndarray
    T_fast: int

    def admitted(self, f: int) -> np.ndarray:
        return (self.warm <= f) & (f < np.minimum(self.end, self.drain))

    def alive(self, f: int) -> np.ndarray:
        """Warm and not yet gone (its cache exists)."""
        return (self.warm <= f) & (f < self.end)


def replica_plan(res, inst, j: int = 0) -> ReplicaPlan:
    """ReplicaPlan of LLM j from RunResult.replicas, leases and events: admission 1 from warm-up (every purchase and
    load of the policies used here starts at admission 1; ValueError on a SetAdmission event, which the plan does not
    model) until the effective fast slot of the first drain that is not replaced by a later one (engine._drain: a
    drain issued at minute i takes effect at max(i / fast_min, ceil(at / fast_min)) and replaces a pending drain).
    ValueError unless the admitted replicas reproduce RunResult.routing W of every site and fast slot exactly."""
    Df, T_f = int(inst.grid.fast_min), int(inst.grid.T_fast)
    site_of = {L.id: L.site for L in res.leases}
    drains: dict = {}
    for minute, typ, p in res.events:
        if typ == "drain":
            drains.setdefault(int(p["replica"]), []).append((int(minute), int(p["at_min"])))
        elif typ == "admission":
            raise ValueError("replica_plan: SetAdmission events are not modelled (A6 issues none)")
    rows = []
    for r in res.replicas:
        if int(r.llm) != j:
            continue
        applied, pending = None, None
        for issue, at in drains.get(int(r.id), []):
            fi = issue // Df
            if pending is not None and pending < fi:
                applied = pending
                break
            pending = max(fi, -(-at // Df))
        if applied is None:
            applied = pending
        end = T_f if r.end_fast is None else int(r.end_fast)
        rows.append((int(r.id), int(site_of[r.lease_id]), int(r.warm_fast), end,
                     T_f if applied is None else int(applied)))
    a = np.array(rows, dtype=np.int64).reshape(-1, 5)
    rp = ReplicaPlan(a[:, 0], a[:, 1], a[:, 2], a[:, 3], a[:, 4], T_f)
    if res.routing is not None:
        W = np.asarray(res.routing["W"][j], dtype=np.float64)
        f = np.arange(T_f)
        adm = (rp.warm[:, None] <= f) & (f < np.minimum(rp.end, rp.drain)[:, None])
        rec = np.zeros_like(W)
        np.add.at(rec, rp.site, adm.astype(np.float64))
        diff = float(np.max(np.abs(rec - W))) if W.size else 0.0
        if diff > 1e-9:
            raise ValueError(f"replica_plan: the replicas' admissions differ from RunResult.routing W by {diff}")
    return rp


def replay_replicas(cp: dict, trace, plan: Placement, rplan: ReplicaPlan, svc: ServiceModel, own_slots: int,
                    S0: int, S1: int, ring_s: int, prefix: bool) -> dict:
    """The replica-level loop of the Mooncake hour (module docstring) over seconds [S0, S1) with the copies `cp` of
    scale.mooncake_copies (arrival times absolute, in seconds of the run) and the trace's hash_ids; prefix True:
    with prefix hits. The replicas are own capacity's (n_seq slots each, the last the remainder) and the run's leased
    replicas at sites with an arc that are warm at some fast slot of [S0, S1). The caches are a bit matrix over
    (namespace, block) x replica, so a cache costs one bit per block and replica. Copies arriving outside [S0, S1)
    are left out (counted). Returns counts, tokens, costs, conservation (E8-1), the hit statistics and timings."""
    from .requests import BLOCK_TOKENS
    t_wall = time.perf_counter()
    n_seq, tpot, w_in = svc.n_seq, svc.tpot_s, svc.w_in
    dsec = 60 * plan.fast_min
    R = int(ring_s)
    f0, f1 = S0 // dsec, -(-S1 // dsec)
    n_own_rep = -(-int(own_slots) // n_seq) if own_slots > 0 else 0
    own_sl = [n_seq] * n_own_rep
    if n_own_rep and own_slots % n_seq:
        own_sl[-1] = int(own_slots) % n_seq
    rank = {int(l): i + 1 for i, l in enumerate(plan.order)}
    warm_in = (rplan.warm < f1) & (rplan.end > f0) & (rplan.warm < rplan.end)
    lr = np.flatnonzero(np.array([int(l) in rank for l in rplan.site], dtype=bool) & warm_in)
    n_rep = n_own_rep + len(lr)
    cls = np.array([0] * n_own_rep + [rank[int(rplan.site[i])] for i in lr], dtype=np.int64)
    site_of = np.array([-1] * n_own_rep + [int(rplan.site[i]) for i in lr], dtype=np.int64)
    classes = [np.flatnonzero(cls == c) for c in range(len(plan.order) + 1)]
    slots = np.zeros(n_rep, np.int64)
    slots[:n_own_rep] = own_sl
    busy = np.zeros(n_rep, np.int64)
    ring = np.zeros((n_rep, R), np.int64)
    inflight = [deque() for _ in range(n_rep)]
    a, req, nsp, inp, out = cp["a"], cp["req"], cp["ns"], cp["inp"], cp["out"]
    # prefix caches: dense block indices per request; bits[ns * U + u, r // 8] bit r % 8 = replica r holds the block
    if prefix:
        flat = np.array([b for h in trace.hash_ids for b in h], dtype=np.int64)
        uniq, inv = np.unique(flat, return_inverse=True)
        U = int(len(uniq))
        ends = np.cumsum([len(h) for h in trace.hash_ids])
        bidx = np.split(inv.astype(np.int64), ends[:-1]) if len(ends) else []
        n_ns = int(nsp.max()) + 1 if len(nsp) else 1
        bits = np.zeros((n_ns * max(U, 1), max(1, -(-n_rep // 8))), dtype=np.uint8)
    alive_prev = np.zeros(len(lr), dtype=bool)
    routed = np.zeros(plan.m)
    acc = {"tok_own": 0.0, "tok_fb": 0.0, "tok_rem": 0.0, "n_own": 0, "n_leased": 0, "n_fb": 0, "n_strand": 0,
           "blocks": 0, "hits": 0, "inp_saved": 0.0, "tok_saved": 0.0, "deaths": 0, "tok_stream": 0.0}
    lo = int(np.searchsorted(a, S0, side="left"))
    hi = int(np.searchsorted(a, S1, side="left"))
    sec_idx = np.searchsorted(a[lo:hi], np.arange(S0, S1 + 1, dtype=np.float64), side="left") + lo

    def strand(r: int, e: int, S: int) -> None:
        taken = 0
        for item in reversed(inflight[r]):
            if not item[3] or item[0] <= S:
                continue
            comp, lw, h = item[0], item[1], item[2]
            rem = lw * (comp - S) / h
            acc["tok_rem"] += rem
            if site_of[r] >= 0:
                routed[site_of[r]] -= rem
            ring[r, comp % R] -= 1
            item[3] = False
            taken += 1
            if taken == e:
                break
        if taken != e:
            raise RuntimeError(f"replay_replicas: replica {r} at second {S}: {taken} in flight for an excess of {e}")
        busy[r] -= taken
        acc["n_strand"] += taken

    for s in range(S0, S1):
        col = ring[:, s % R]
        if col.any():
            busy -= col
            ring[:, s % R] = 0
        if s % dsec == 0 or s == S0:
            f = s // dsec
            if len(lr):
                adm = rplan.admitted(f)[lr]
                alive = rplan.alive(f)[lr]
                slots[n_own_rep:] = np.where(adm, n_seq, 0)
                for i in np.flatnonzero(alive_prev & ~alive):
                    rr = n_own_rep + int(i)
                    if prefix:
                        bits[:, rr >> 3] &= np.uint8(0xFF ^ (1 << (rr & 7)))
                    acc["deaths"] += 1
                alive_prev = alive
            exc = busy - slots
            for r in np.flatnonzero(exc > 0):
                strand(int(r), int(exc[r]), s)
            for dq in inflight:
                while dq and dq[0][0] <= s:
                    dq.popleft()
        free = slots - busy
        for c in range(int(sec_idx[s - S0]), int(sec_idx[s - S0 + 1])):
            keys = nsp[c] * U + bidx[req[c]] if prefix else None
            r = -1
            for cl in classes:
                if not len(cl):
                    continue
                fr = free[cl]
                if fr.max() <= 0:
                    continue
                if prefix and len(keys):
                    # cached prefix length per replica of the class: the leading run of the copy's blocks it holds
                    held = np.unpackbits(bits[keys], axis=1, count=n_rep, bitorder="little")[:, cl].astype(bool)
                    plen = np.where(fr > 0, np.logical_and.accumulate(held, axis=0).sum(axis=0), -1)
                    best = int(plen.max())
                    if best > 0:
                        r = int(cl[int(np.argmax(np.where(plen == best, fr, -1)))])
                        break
                r = int(cl[int(np.argmax(fr))])
                break
            x_in, x_out = float(inp[c]), float(out[c])
            l_full = w_in * x_in + x_out
            acc["tok_stream"] += l_full
            if r < 0:
                acc["tok_fb"] += l_full
                acc["n_fb"] += 1
                continue
            lw = l_full
            if prefix and len(keys):
                byte, bit = r >> 3, np.uint8(1 << (r & 7))
                colb = bits[keys, byte]
                hits = int(np.count_nonzero(colb & bit))
                bits[keys, byte] = colb | bit
                acc["blocks"] += len(keys)
                acc["hits"] += hits
                saved = min(x_in, float(BLOCK_TOKENS * hits))
                acc["inp_saved"] += saved
                lw = w_in * (x_in - saved) + x_out
                acc["tok_saved"] += l_full - lw
            h = max(1, int(round(lw * tpot)))
            if h >= R - 1:
                raise RuntimeError(f"replay_replicas: a hold of {h} s does not fit the ring of {R} buckets")
            comp = s + h
            ring[r, comp % R] += 1
            busy[r] += 1
            free[r] -= 1
            inflight[r].append([comp, lw, h, True])
            if r < n_own_rep:
                acc["tok_own"] += lw
                acc["n_own"] += 1
            else:
                routed[site_of[r]] += lw
                acc["n_leased"] += 1
    costs = token_costs(routed, acc["tok_fb"] + acc["tok_rem"], acc["n_strand"], plan, svc)
    n_cp = int(hi - lo)
    served = acc["tok_own"] + float(routed.sum())
    fb = acc["tok_fb"] + acc["tok_rem"]
    tok_diff = abs(served + fb + acc["tok_saved"] - acc["tok_stream"])
    counts_ok = acc["n_own"] + acc["n_leased"] + acc["n_fb"] == n_cp
    tok_ok = tok_diff <= TOKEN_REL_TOL * max(1.0, acc["tok_stream"])
    cons = {"pass": bool(counts_ok and tok_ok), "counts_exact": bool(counts_ok), "tokens_ok": bool(tok_ok),
            "copies": n_cp, "own": acc["n_own"], "leased": acc["n_leased"], "fallback": acc["n_fb"],
            "stranded": acc["n_strand"], "before_window": lo, "beyond_window": int(len(a) - hi),
            "tokens_stream": acc["tok_stream"], "tokens_served": served, "tokens_fallback": fb,
            "tokens_saved_by_hits": acc["tok_saved"], "tokens_rel_diff": tok_diff / max(1.0, acc["tok_stream"]),
            "tol": TOKEN_REL_TOL}
    return {"prefix": bool(prefix), "seconds": [int(S0), int(S1)], "ring_s": R, "own_replicas": n_own_rep,
            "own_slots": int(own_slots), "leased_replicas": int(len(lr)),
            "counts": {"copies": n_cp, "own": acc["n_own"], "leased": acc["n_leased"], "fallback": acc["n_fb"],
                       "stranded": acc["n_strand"], "replica_deaths": acc["deaths"]},
            "tokens": {"stream": acc["tok_stream"], "own": acc["tok_own"], "leased": float(routed.sum()),
                       "fallback": acc["tok_fb"], "stranded_remainder": acc["tok_rem"],
                       "saved_by_hits": acc["tok_saved"], "input_tokens_saved_by_hits": acc["inp_saved"]},
            "hits": {"blocks_on_replicas": acc["blocks"], "block_hits": acc["hits"],
                     "hit_ratio": acc["hits"] / acc["blocks"] if acc["blocks"] else None},
            "costs": costs, "conservation": cons, "timing": {"wall_s": time.perf_counter() - t_wall}}


__all__ = ["ServiceModel", "service_model", "Placement", "placement", "token_costs", "ring_size", "replay",
           "ReplicaPlan", "replica_plan", "replay_replicas", "TOKEN_REL_TOL"]
