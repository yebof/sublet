"""Cost ledger and record-based invariants (design/sim_spec.md §5.6, §5.7).

The engine books every cost with `Ledger.add(component, t_slow, usd)`. The ledger keeps one
(T_slow,) array per component and, separately, the running total of all bookings, so that
INV4 (components add up to the total) compares two independent sums.

`check_invariants(res, inst)` checks after a run the invariants that need only the records:
INV1 (reclaim rule), INV4 (components and total), INV5 (billing), INV6 (site capacity), and,
when the run recorded its routing (EngineConfig.record_routing), INV2 (conservation), INV3
(capacity and feasibility) and the `stranding_kv` and `stranding_fb` parts of INV8. The engine
checks INV2, INV3, INV7 and INV8 online.
"""
from __future__ import annotations

import math

import numpy as np

from . import reclaim
from .types import Instance, RunResult

COMPONENTS = ("lease_prepaid", "lease_rent", "loading", "routing", "fallback",
              "stranding_kv", "stranding_fl", "stranding_fb", "stranding_pi")
GROUPS = {"lease": ("lease_prepaid", "lease_rent"),
          "stranding": ("stranding_kv", "stranding_fl", "stranding_fb", "stranding_pi")}


class Ledger:
    """Per-slow-slot cost bookings in USD."""

    def __init__(self, T_slow: int):
        self.T_slow = int(T_slow)
        self._c = {c: np.zeros(self.T_slow) for c in COMPONENTS}
        self._total = np.zeros(self.T_slow)   # accumulated independently of the components
        self.running_total = 0.0

    def add(self, component: str, t_slow: int, usd: float) -> None:
        arr = self._c.get(component)
        if arr is None:
            raise KeyError(f"unknown ledger component {component!r}")
        if not 0 <= t_slow < self.T_slow:
            raise IndexError(f"slow slot {t_slow} outside [0, {self.T_slow})")
        usd = float(usd)
        if not math.isfinite(usd):
            raise ValueError(f"non-finite amount {usd} for {component} at slot {t_slow}")
        arr[t_slow] += usd
        self._total[t_slow] += usd
        self.running_total += usd

    def per_slot(self) -> dict[str, np.ndarray]:
        """Component -> (T_slow,) USD, plus the groups 'lease' and 'stranding' and 'total'."""
        out = {c: a.copy() for c, a in self._c.items()}
        for g, parts in GROUPS.items():
            out[g] = np.sum([out[p] for p in parts], axis=0)
        out["total"] = self._total.copy()
        return out

    def totals(self) -> dict[str, float]:
        """COMPONENTS + 'lease', 'stranding', 'total' summed over the run."""
        return {k: float(v.sum()) for k, v in self.per_slot().items()}


# ---------------------------------------------------------------- invariants
def _rel_ok(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(b))


def _first_dead_fast(start_min: int, end_min: int, fast_min: int) -> int:
    """First fast slot in which a lease is no longer alive (rule T6); the start fast slot if the
    lease is never alive."""
    return max(start_min // fast_min, end_min // fast_min)


def _inv1(res: RunResult, inst: Instance) -> list[str]:
    """Reclaim rule (T5): announcements at the first slot of R_l at or after s + tau, deaths at
    r * slow_min + H, lifetimes of reclaimed leases at least D_k, consistent end causes."""
    out = []
    g = inst.grid
    R = [np.asarray(x, dtype=np.int64) for x in res.schedule.R]
    for L in res.leases:
        c = inst.contracts[L.contract]
        tag = f"INV1 lease {L.id}"
        cut_slot = None
        if L.end_cause in ("release", "violation"):
            cut_slot = L.end_min // g.slow_min
        if c.protected:
            if L.announce_slot is not None or L.death_min is not None:
                out.append(f"{tag}: protected lease was announced")
            if L.end_cause == "reclaim":
                out.append(f"{tag}: protected lease has cause 'reclaim'")
        else:
            r_exp = reclaim.first_announcement(R[L.site], L.start_slot, c.tau_slots)
            if r_exp is not None and (r_exp >= g.T_slow or (cut_slot is not None and r_exp > cut_slot)):
                r_exp = None    # the lease was no longer held at the start of slot r_exp
            if L.announce_slot != r_exp:
                out.append(f"{tag}: announce_slot {L.announce_slot}, expected {r_exp} "
                           f"(start {L.start_slot}, tau {c.tau_slots})")
            if L.announce_slot is not None:
                exp_death = L.announce_slot * g.slow_min + c.H_min
                if L.death_min != exp_death:
                    out.append(f"{tag}: death_min {L.death_min}, expected {exp_death}")
            elif L.death_min is not None:
                out.append(f"{tag}: death_min without an announcement")
        if L.end_cause == "reclaim":
            r = L.announce_slot
            if r is None or L.death_min is None:
                out.append(f"{tag}: cause 'reclaim' without announcement")
            else:
                Rl = R[L.site]
                if r < L.start_slot + (c.tau_slots or 0):
                    out.append(f"{tag}: announced at {r} before s + tau")
                if not np.any(Rl == r):
                    out.append(f"{tag}: announce slot {r} not in the realized R")
                lo = L.start_slot + (c.tau_slots or 0)
                if np.any((Rl >= lo) & (Rl < r)):
                    out.append(f"{tag}: an element of R lies in [s + tau, r)")
                if L.end_min != L.death_min:
                    out.append(f"{tag}: end_min {L.end_min} != death_min {L.death_min}")
                D = c.D_min(g.slow_min)
                if D is not None and L.end_min - L.start_min < D:
                    out.append(f"{tag}: lived {L.end_min - L.start_min} min < D_k = {D}")
        elif L.end_cause == "release":
            if L.release_min is None or L.end_min != L.release_min:
                out.append(f"{tag}: cause 'release' but release_min {L.release_min}, "
                           f"end_min {L.end_min}")
        elif L.end_cause == "horizon":
            if L.end_min != g.horizon_min:
                out.append(f"{tag}: cause 'horizon' but end_min {L.end_min}")
        elif L.end_cause != "violation":
            out.append(f"{tag}: unknown end cause {L.end_cause!r}")
        if L.end_cause != "release" and L.release_min is not None:
            out.append(f"{tag}: release_min set with cause {L.end_cause!r}")
        if L.start_min != L.start_slot * g.slow_min:
            out.append(f"{tag}: start_min {L.start_min} != start_slot * slow_min")
        bound = min(x for x in (L.death_min, L.release_min, g.horizon_min) if x is not None)
        if L.end_cause != "violation" and L.end_min != bound:
            out.append(f"{tag}: end_min {L.end_min} != min(death, release, horizon) = {bound}")
        if L.end_min > bound:
            out.append(f"{tag}: end_min {L.end_min} after min(death, release, horizon)")
    return out


def _inv4(res: RunResult, tol: float) -> list[str]:
    out = []
    ps = res.per_slot
    tot = ps["total"]
    comp_sum = np.sum([ps[c] for c in COMPONENTS], axis=0)
    scale = max(1.0, abs(float(res.components.get("total", 0.0))))
    bad = np.flatnonzero(np.abs(comp_sum - tot) > tol * scale)
    if len(bad):
        t = int(bad[0])
        out.append(f"INV4: components {comp_sum[t]!r} != total {tot[t]!r} in slot {t} "
                   f"({len(bad)} slots)")
    for c in COMPONENTS + ("lease", "stranding", "total"):
        if not _rel_ok(float(ps[c].sum()), float(res.components[c]), tol):
            out.append(f"INV4: components[{c!r}] = {res.components[c]!r} != per-slot sum "
                       f"{float(ps[c].sum())!r}")
    total = sum(float(res.components[c]) for c in COMPONENTS)
    if abs(total - float(res.components["total"])) > tol * scale:
        out.append(f"INV4: sum of components {total!r} != total {res.components['total']!r}")
    return out


def _inv5(res: RunResult, inst: Instance, tol: float) -> list[str]:
    """Billing (rule T7) recomputed from the lease records."""
    out = []
    g = inst.grid
    Df = g.fast_min
    expect = 0.0
    for L in res.leases:
        c = inst.contracts[L.contract]
        a = float(inst.price[L.site, L.contract])
        pre = L.gpus * a * c.prepaid_min / 60.0
        f_start = L.start_min // Df
        f_end = _first_dead_fast(L.start_min, L.end_min, Df)
        f_rent = max(f_start, -(-(L.start_min + c.prepaid_min) // Df))
        n_rent = max(0, f_end - f_rent)
        rent = L.gpus * a * Df / 60.0 * n_rent
        expect += pre + rent
        if not _rel_ok(L.prepaid_usd, pre, tol):
            out.append(f"INV5 lease {L.id}: prepaid_usd {L.prepaid_usd!r}, expected {pre!r}")
        if not _rel_ok(L.rent_usd, rent, tol):
            out.append(f"INV5 lease {L.id}: rent_usd {L.rent_usd!r}, expected {rent!r} "
                       f"({n_rent} rent-bearing fast slots)")
        if L.prepaid_end_min != L.start_min + c.prepaid_min:
            out.append(f"INV5 lease {L.id}: prepaid_end_min {L.prepaid_end_min} != start + P_k")
    booked = float(res.components["lease_prepaid"] + res.components["lease_rent"])
    if not _rel_ok(booked, expect, tol):
        out.append(f"INV5: lease_prepaid + lease_rent = {booked!r}, recomputed {expect!r}")
    return out


def _inv6(res: RunResult, inst: Instance) -> list[str]:
    """GPUs of the leases alive in the first fast slot of every slow slot within site capacity."""
    out = []
    g = inst.grid
    held = np.zeros((inst.m, g.T_slow), dtype=np.int64)
    for L in res.leases:
        # alive in fast slot t*phi: start_min <= t*slow_min and t*slow_min + fast_min <= end_min
        t_hi = min(g.T_slow, (L.end_min - g.fast_min) // g.slow_min + 1)
        if t_hi > L.start_slot:
            held[L.site, L.start_slot:t_hi] += L.gpus
    for l, s in enumerate(inst.sites):
        if math.isfinite(s.capacity_gpus):
            bad = np.flatnonzero(held[l] > s.capacity_gpus)
            if len(bad):
                t = int(bad[0])
                out.append(f"INV6 site {l}: {int(held[l, t])} GPUs held at slot {t} > capacity "
                           f"{s.capacity_gpus} ({len(bad)} slots)")
    return out


def _client_routing(res: RunResult, inst: Instance) -> list[dict[int, np.ndarray]]:
    """Per client: site -> (T_fast,) served load, from the sparse routing record."""
    per = [dict() for _ in range(inst.n)]
    for (c, l), arr in res.routing["x"].items():
        per[int(c)][int(l)] = np.asarray(arr, dtype=np.float64)
    return per


def _inv2_inv3_inv8(res: RunResult, inst: Instance, tol: float) -> list[str]:
    """Post-hoc INV2, INV3 and INV8 (kv, fb) from the routing record, one client at a time."""
    out = []
    g = inst.grid
    T_f, phi = g.T_fast, g.phi
    d_all = np.asarray(inst.clients.demand, dtype=np.float64)
    b_all = np.asarray(res.routing["b"], dtype=np.float64)
    W = np.asarray(res.routing["W"], dtype=np.float64)              # (J, m, T_f)
    llm = np.asarray(inst.clients.llm, dtype=np.int64)
    q = np.array([L.q_usd_per_h for L in inst.llms], dtype=np.float64)
    delta = np.asarray(inst.clients.delta_usd_per_h, dtype=np.float64)
    st = inst.stranding
    mu_kv = np.asarray(st.mu_kv_usd, dtype=np.float64)
    mu_fb = np.asarray(st.mu_fb_usd, dtype=np.float64)
    served = np.zeros_like(W)                                       # (J, m, T_f)
    kv = np.zeros(T_f)
    fb = np.zeros(T_f)
    n_bad2 = n_bad3 = 0
    first2 = first3 = None
    for c, arcs in enumerate(_client_routing(res, inst)):
        j = int(llm[c])
        d, b = d_all[c], b_all[c]
        X = np.zeros(T_f)
        for l, x in arcs.items():
            X += x
            served[j, l] += x
            forbidden = (not math.isfinite(delta[c, l])) or delta[c, l] >= q[j]
            bad = (x > tol) & (forbidden | (W[j, l] <= 0.0))
            if bad.any():
                n_bad3 += 1
                if first3 is None:
                    f = int(np.flatnonzero(bad)[0])
                    first3 = (f"INV3 (post hoc): load {x[f]!r} on a forbidden arc or a site without "
                              f"admitting capacity: client {c}, site {l}, fast slot {f}")
            if (x < -tol).any():
                n_bad2 += 1
                first2 = first2 or f"INV2 (post hoc): negative served load, client {c}, site {l}"
        err = np.abs(X + b - d) > tol * np.maximum(1.0, d)
        if err.any() or (b < -tol).any():
            n_bad2 += 1
            if first2 is None:
                f = int(np.flatnonzero(err | (b < -tol))[0])
                first2 = (f"INV2 (post hoc): client {c} fast slot {f}: served {X[f]!r} + fallback "
                          f"{b[f]!r} != demand {d[f]!r}")
        # moved load (§5.6) in the z form: z = x / d, persisting load min(d(f-1), d(f))
        d_prev = np.concatenate([[0.0], d[:-1]])
        dhat = np.minimum(d_prev, d)
        pos = d > 0
        zbar = np.zeros(T_f)
        m_c = np.zeros(T_f)
        for l, x in arcs.items():
            z = np.zeros(T_f)
            z[pos] = x[pos] / d[pos]
            zbar += z
            z_prev = np.concatenate([[0.0], z[:-1]])
            m_c += np.maximum(dhat * z_prev - d * z, 0.0)
        zbar_prev = np.concatenate([[0.0], zbar[:-1]])
        w_c = np.maximum(dhat * zbar_prev - d * zbar, 0.0)
        kv += mu_kv[j] * m_c
        fb += mu_fb[j] * w_c
    if first2:
        out.append(first2 + (f" ({n_bad2} clients or arcs)" if n_bad2 > 1 else ""))
    if first3:
        out.append(first3 + (f" ({n_bad3} arcs)" if n_bad3 > 1 else ""))
    if not inst.kappa_infinite:
        over = served > W + tol
        if over.any():
            j, l, f = map(int, np.argwhere(over)[0])
            out.append(f"INV3 (post hoc): LLM {j} site {l} fast slot {f}: served "
                       f"{served[j, l, f]!r} > capacity {W[j, l, f]!r}")
    for name, val in (("stranding_kv", kv), ("stranding_fb", fb)):
        val = val.reshape(g.T_slow, phi).sum(axis=1)
        led = res.per_slot[name]
        bad = np.flatnonzero(np.abs(val - led) > tol * np.maximum(1.0, np.abs(led)))
        if len(bad):
            t = int(bad[0])
            out.append(f"INV8 (post hoc): {name} slot {t}: ledger {led[t]!r}, recomputed "
                       f"{val[t]!r} ({len(bad)} slots)")
    return out


def check_invariants(res: RunResult, inst: Instance, tol: float = 1e-9) -> list[str]:
    """The record-based invariants of §5.7 (INV1, INV4-INV6; with a routing record also INV2,
    INV3 and the stranding_kv / stranding_fb parts of INV8). Returns [] if all hold."""
    out = []
    out += _inv1(res, inst)
    out += _inv4(res, tol)
    out += _inv5(res, inst, tol)
    out += _inv6(res, inst)
    if res.routing is not None:
        out += _inv2_inv3_inv8(res, inst, tol)
    return out


__all__ = ["COMPONENTS", "GROUPS", "Ledger", "check_invariants"]
