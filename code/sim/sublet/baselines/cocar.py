"""BL4, CoCaR-style window LP (design/sim_spec_ms2.md §15.6; qiu2026joint, the ToN extension of
qiu2025cocar: LP relaxation and randomized rounding, Sec. V pp. 6-9; Thm 1 p. 7).

Windows of W = window_min minutes aligned at horizon minute 0 (W / Δs slow slots; the last window
ends at the horizon). At a window start t0:
- Contracts and arcs: K_l holds k*(l) (§15.1) if l offers an unflagged contract and the cheapest
  contract that treated_as_protected flags if l offers one (one n_new variable per kind); arcs are the
  pairs (c, l) with delta_cl < INF and delta_cl + g_j a_lk < q_j for some k in K_l.
- Leases: single-replica leases (M56). Held = BL4's alive, unannounced leases at t0 (M44); pre = those
  inside their billed term (t0 Δs < prepaid_end_min).
- Variables: n_new_jlk >= 0, n_keep_jlk in [pre_jlk, held_jlk], routing x_clt >= 0 on the arcs.
- Objective (USD over the window): sum n_new (beta_jl + g_j a_lk max(W, P_k) / 60)
  + sum_{L in pre} g_j a_lk W^rent_L / 60 + sum (n_keep - pre) g_j a_lk W / 60
  + sum delta_cl x_clt Δs / 60 + sum q_jc (dhat_c(t) - sum_l x_clt) Δs / 60.
- Constraints: sum_l x_clt <= dhat_c(t); sum_{c: j_c = j} x_clt <= sum_k omega_jl(t) n_new_jlk
  + sum_k n_keep_jlk with omega_jl(t) = 1 - min(1, max(0, lambda_jl / 60 - (t - t0) Δs) / Δs) (ours: the
  share of slot t after a new replica is warm, fluid); per site sum_j g_j sum_k (n_new + n_keep) <=
  capacity_gpus minus the GPUs of BL4's announced leases there; with kappa_infinite the routing bound is
  x_clt <= dhat_c(t) (sum_k omega n_new + sum_k n_keep) per client.
- Rounding (ours): n = floor(n+) + Bernoulli(n+ - floor(n+)) per (j, l, k), new then kept, with the aux
  stream in lexicographic (j, l, k) order (one uniform per variable); kept counts stay in [pre, held].
- Repair (ours): while a site exceeds its capacity, remove the rounded replica with the smallest LP
  benefit (its share of the load the LP serves at (j, l) times (q_j - delta), minus its cost), new
  before kept, never a pre lease.
- Execution at t0: keep the pre leases and, among the other held leases of each (j, l, k), the oldest
  (lowest id) up to the kept count; release the rest (past their billed term); buy each new replica
  as its own lease Buy(l, k, j, 1). Inside the window BL4 does nothing.
- Demand dhat: "previous" (online) = the previous window's realized slot means shifted by W, and
  slot 0's revealed mean held constant in the first window; "oracle" = the realized slot means of the
  coming window (driver input future_demand, information class lookahead-<W>min).

MS7 choice of `demand` (design/ms7/plan.md X1, C53; design/ms7/feasibility/causal.md F2, risk 5): "previous0" is
"previous" with zeros as dhat in the first window instead of slot 0's revealed mean, so that no window reads the
slot it plans (the only lookahead of "previous" is that first window, 1 h of a week); every later window is
"previous"'s. Information class online-I1, no driver input; BL4-lag of experiments/e7c_tags.py. The default
"previous" is unchanged.

MS7 option (design/ms7/plan.md X4, C54; design/ms7/feasibility/baselines.md §2 item 1, §3 B2), default the behaviour
above and hidden from params() while it holds its default (QUIET_KEYS):
- contract_rule ('kstar'): with 'c2' the contract set of site l for LLM j is K_lj = {kbar(l, j), the cheapest flagged
  contract} (kbar of A9.3, common.c2_base_contracts_cached; -1 entries dropped) in place of K_l: the arcs, the n_new
  triples (j, l, k) and so the purchases use kbar (BL4-c2). mpc.py's receding-horizon LP reads the same sets.
"""
from __future__ import annotations

import math
import time
from typing import Optional

import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog

from ..algos.common import PolicyError
from ..types import Buy, PublicView, SlowObs
from .common import Baseline, DemandHistory, c2_base_contracts_cached, cheapest_flagged


def omega_share(lam_s: float, i: int, slow_min: int) -> float:
    """omega for slot t0 + i: the share of the slot after a replica bought at t0 with load time lam_s
    (seconds) is warm, 1 - min(1, max(0, lam_s / 60 - i Δs) / Δs) (fluid, no fast-slot rounding)."""
    return 1.0 - min(1.0, max(0.0, float(lam_s) / 60.0 - i * slow_min) / slow_min)


def round_counts(values, lo, hi, rng: np.random.Generator) -> np.ndarray:
    """floor(v) + Bernoulli(v - floor(v)) per entry, in order, one uniform of `rng` per entry; v is
    clipped to the integer bounds [lo, hi] and snapped to an integer within 1e-9 first, so the result
    stays in [lo, hi] and its expectation is v."""
    out = np.zeros(len(values), dtype=np.int64)
    for i, (v, a, b) in enumerate(zip(values, lo, hi)):
        v = min(max(float(v), float(a)), float(b))
        r = round(v)
        if abs(v - r) <= 1e-9:
            v = float(r)
        f = math.floor(v)
        u = rng.random()
        out[i] = f + (1 if u < v - f else 0)
    return out


def repair_counts(site_of: list, gpus: list, new: np.ndarray, keep: np.ndarray, pre: np.ndarray,
                  benefit_new: list, benefit_keep: list, cap: dict) -> tuple[np.ndarray, np.ndarray, int]:
    """Repair of §15.6 on rounded counts per triple: while a site's sum of gpus x (new + keep) exceeds
    cap[site], remove one new replica with the smallest benefit, else one kept replica above pre with
    the smallest benefit (ties by triple order). Returns (new, keep, removals)."""
    new, keep = new.copy(), keep.copy()
    removed = 0
    for l, c in cap.items():
        idx = [i for i, s in enumerate(site_of) if s == l]
        while sum(gpus[i] * (new[i] + keep[i]) for i in idx) > c + 1e-9:
            cand = [i for i in idx if new[i] > 0]
            if cand:
                i = min(cand, key=lambda i: (benefit_new[i], i))
                new[i] -= 1
            else:
                cand = [i for i in idx if keep[i] > pre[i]]
                if not cand:
                    break
                i = min(cand, key=lambda i: (benefit_keep[i], i))
                keep[i] -= 1
            removed += 1
    return new, keep, removed


class CoCaRStyle(Baseline):
    """BL4 (online-I1 with demand "previous" or "previous0"; lookahead-<W>min with "oracle")."""
    name = "bl4_cocar"
    PARAMS = {"window_min": 60, "demand": "previous", "contract_rule": "kstar"}
    QUIET_KEYS = ("contract_rule",)          # MS7 C54: the records at the defaults stay those of MS2-MS5b
    INPUTS = ("future_demand",)

    def _validate(self) -> None:
        self._choice("demand", ("previous", "previous0", "oracle"))
        w = self._params["window_min"]
        if isinstance(w, bool) or not isinstance(w, (int, np.integer)) or w < 1:
            raise PolicyError(f"CoCaRStyle: window_min must be an integer >= 1, got {w!r}")
        if self._params["demand"] == "oracle" and self._inputs.get("future_demand") is None:
            raise PolicyError("CoCaRStyle: demand 'oracle' needs the driver input future_demand (n, T_slow)")

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        W = int(self._params["window_min"])
        if W % self.slow_min:
            raise PolicyError(f"CoCaRStyle: window_min {W} is not a multiple of the slow slot {self.slow_min}")
        self.nW = W // self.slow_min
        self.aux = self.streams["aux"]
        self.kinf = bool(view.kappa_infinite)
        self.hist = DemandHistory(self.n, self.nW + 1)      # slots [t0 - W, t0] at a window start
        if self._params["demand"] == "oracle":
            fd = np.asarray(self._inputs["future_demand"], dtype=np.float64)
            if fd.shape != (self.n, self.T_slow):
                raise PolicyError(f"CoCaRStyle: future_demand has shape {fd.shape}, expected {(self.n, self.T_slow)}")
            self.future = fd
        self._setup_arcs(view)
        self.lease_triple: dict[int, tuple[int, int, int]] = {}
        self.last_plan: Optional[dict] = None
        self.lp_seconds = 0.0          # wall time of the window LPs (kept out of report(), which is deterministic)
        self.rep = {"windows": 0, "lp_status": {}, "lp_n_vars_max": 0, "lp_n_rows_max": 0,
                    "lp_nnz_max": 0, "lp_size_last": None, "new": 0, "kept": 0, "released": 0,
                    "repair_removals": 0, "announced_skipped": 0}

    def _setup_arcs(self, view: PublicView) -> None:
        """K_l (and K_lj with contract_rule 'c2'), BL4's arcs and the n_new triples (module docstring); shared with
        mpc.RecedingLP (MS7 C54)."""
        st = self.sites
        flag = cheapest_flagged(view)
        m = len(view.sites)
        self.K_l = [[int(k) for k in (st.kstar[l], flag[l]) if k >= 0] for l in range(m)]
        self.K_lj: Optional[list] = None              # MS7 contract_rule 'c2': K_lj[l][j] in place of K_l[l]
        if self._params.get("contract_rule", "kstar") == "c2":
            kb = c2_base_contracts_cached(view)
            st.use_contracts(kb)                      # for the record's 'contracts'; BL4 reads K_lj
            self.K_lj = [[[int(k) for k in (kb[l, j], flag[l]) if k >= 0] for j in range(len(view.llms))]
                         for l in range(m)]
        price = np.asarray(view.price, dtype=np.float64)
        self.arcs: list[tuple[int, int]] = []
        for c in range(self.n):
            j = int(st.cl_llm[c])
            for l in range(m):
                d = st.delta[c, l]
                if np.isfinite(d) and any(d + st.g[j] * price[l, k] < st.q[j] for k in self.contracts_of(l, j)):
                    self.arcs.append((c, l))
        jl = sorted({(int(st.cl_llm[c]), l) for c, l in self.arcs})
        self.triples_new = [(j, l, k) for j, l in jl for k in sorted(self.contracts_of(l, j))]

    def contracts_of(self, l: int, j: int) -> list:
        """The contracts of site l for LLM j: K_l[l] (k*(l) and the cheapest flagged contract), or with contract_rule
        'c2' K_lj[l][j] (kbar(l, j) and the cheapest flagged contract; MS7 C54)."""
        return self.K_l[l] if self.K_lj is None else self.K_lj[l][j]

    # -------------------------------------------------------- demand
    def _dhat(self, t0: int, nslots: int) -> np.ndarray:
        if self._params["demand"] == "oracle":
            return self.future[:, t0:t0 + nslots].copy()
        if t0 == 0:
            if self._params["demand"] == "previous0":      # C53: no lookahead in the first window
                return np.zeros((self.n, nslots))
            return np.repeat(self.hist.mean_at(0)[:, None], nslots, axis=1)
        return np.stack([self.hist.mean_at(t0 - self.nW + i) for i in range(nslots)], axis=1)

    # -------------------------------------------------------- the window LP
    def plan_window(self, obs: SlowObs) -> dict:
        """Solve, round and repair the window LP at window start obs.t; returns the plan (also kept
        in last_plan): triples, LP values, rounded counts, the held leases per triple and LP stats."""
        view, st = self.view, self.sites
        t0 = obs.t
        nsl = min(self.nW, self.T_slow - t0)
        W = nsl * self.slow_min
        Ds = self.slow_min
        dhat = self._dhat(t0, nsl)
        price = np.asarray(view.price, dtype=np.float64)
        lam = np.asarray(view.lam_s, dtype=np.float64)
        beta = np.asarray(view.beta_usd, dtype=np.float64)
        # held, pre and announced GPUs
        held: dict[tuple, list[int]] = {}
        pre: dict[tuple, int] = {}
        ann_gpus: dict[int, float] = {}
        rent_pre = 0.0
        for lid, tr in self.lease_triple.items():
            L = obs.leases.get(lid)
            if L is None:
                continue
            if L.announce_slot is not None:          # its death is known: not planned as owned (M44)
                ann_gpus[L.site] = ann_gpus.get(L.site, 0.0) + L.gpus
                self.rep["announced_skipped"] += 1
                continue
            held.setdefault(tr, []).append(lid)
            if obs.minute < L.prepaid_end_min:
                pre[tr] = pre.get(tr, 0) + 1
                j, l, k = tr
                rent_pre += st.g[j] * price[l, k] * max(0, obs.minute + W - L.prepaid_end_min) / 60.0
        tn = self.triples_new
        tk = sorted(held)
        Nn, Nk = len(tn), len(tk)
        arcs = self.arcs
        Na = len(arcs)
        Nx = Na * nsl
        nv = Nn + Nk + Nx
        cost = np.zeros(nv)
        for i, (j, l, k) in enumerate(tn):
            P = view.contracts[k].prepaid_min
            cost[i] = beta[j, l] + st.g[j] * price[l, k] * max(W, P) / 60.0
        for i, (j, l, k) in enumerate(tk):
            cost[Nn + i] = st.g[j] * price[l, k] * W / 60.0
        for a, (c, l) in enumerate(arcs):
            j = int(st.cl_llm[c])
            cost[Nn + Nk + a * nsl: Nn + Nk + (a + 1) * nsl] = (st.delta[c, l] - st.q[j]) * Ds / 60.0
        lo = np.zeros(nv)
        hi = np.full(nv, np.inf)
        for i, tr in enumerate(tk):
            lo[Nn + i], hi[Nn + i] = pre.get(tr, 0), len(held[tr])
        rows, cols, vals, rhs = [], [], [], []
        r = 0
        # demand rows: sum_l x_clt <= dhat_c(t)
        arcs_of_c: dict[int, list[int]] = {}
        for a, (c, l) in enumerate(arcs):
            arcs_of_c.setdefault(c, []).append(a)
        for c, al in arcs_of_c.items():
            for i in range(nsl):
                for a in al:
                    rows.append(r); cols.append(Nn + Nk + a * nsl + i); vals.append(1.0)
                rhs.append(float(dhat[c, i])); r += 1
        # serving rows
        new_of = {}
        for i, (j, l, k) in enumerate(tn):
            new_of.setdefault((j, l), []).append(i)
        keep_of = {}
        for i, (j, l, k) in enumerate(tk):
            keep_of.setdefault((j, l), []).append(i)
        om = {(j, l): [omega_share(lam[j, l], i, Ds) for i in range(nsl)] for (j, l) in new_of}
        if self.kinf:
            for a, (c, l) in enumerate(arcs):
                j = int(st.cl_llm[c])
                for i in range(nsl):
                    rows.append(r); cols.append(Nn + Nk + a * nsl + i); vals.append(1.0)
                    dh = float(dhat[c, i])
                    for v in new_of.get((j, l), ()):
                        rows.append(r); cols.append(v); vals.append(-dh * om[(j, l)][i])
                    for v in keep_of.get((j, l), ()):
                        rows.append(r); cols.append(Nn + v); vals.append(-dh)
                    rhs.append(0.0); r += 1
        else:
            arcs_of_jl: dict[tuple, list[int]] = {}
            for a, (c, l) in enumerate(arcs):
                arcs_of_jl.setdefault((int(st.cl_llm[c]), l), []).append(a)
            for (j, l), al in sorted(arcs_of_jl.items()):
                for i in range(nsl):
                    for a in al:
                        rows.append(r); cols.append(Nn + Nk + a * nsl + i); vals.append(1.0)
                    for v in new_of.get((j, l), ()):
                        rows.append(r); cols.append(v); vals.append(-om[(j, l)][i])
                    for v in keep_of.get((j, l), ()):
                        rows.append(r); cols.append(Nn + v); vals.append(-1.0)
                    rhs.append(0.0); r += 1
        # capacity rows
        cap: dict[int, float] = {}
        sites_used = sorted({l for _, l, _ in tn} | {l for _, l, _ in tk})
        for l in sites_used:
            capl = float(view.sites[l].capacity_gpus)
            if not np.isfinite(capl):
                continue
            cap[l] = capl - ann_gpus.get(l, 0.0)
            for i, (j, ll, k) in enumerate(tn):
                if ll == l:
                    rows.append(r); cols.append(i); vals.append(float(st.g[j]))
            for i, (j, ll, k) in enumerate(tk):
                if ll == l:
                    rows.append(r); cols.append(Nn + i); vals.append(float(st.g[j]))
            rhs.append(cap[l]); r += 1
        size = {"n_vars": nv, "n_rows": r, "nnz": len(vals), "t0": t0}
        ts = time.perf_counter()
        if nv == 0:
            status, xv, obj = 0, np.zeros(0), 0.0
        else:
            A = sp.csr_matrix((vals, (rows, cols)), shape=(r, nv)) if r else None
            res = linprog(cost, A_ub=A, b_ub=np.asarray(rhs) if r else None,
                          bounds=np.column_stack([lo, hi]), method="highs")
            status, xv, obj = int(res.status), res.x, (float(res.fun) if res.status == 0 else None)
        self.lp_seconds += time.perf_counter() - ts
        self.rep["lp_status"][str(status)] = self.rep["lp_status"].get(str(status), 0) + 1
        for key, k2 in (("n_vars", "lp_n_vars_max"), ("n_rows", "lp_n_rows_max"), ("nnz", "lp_nnz_max")):
            self.rep[k2] = max(self.rep[k2], size[key])
        self.rep["lp_size_last"] = size
        pre_v = np.array([pre.get(tr, 0) for tr in tk], dtype=np.int64)
        held_v = np.array([len(held[tr]) for tr in tk], dtype=np.int64)
        if status != 0 or xv is None:
            new_d, keep_d = np.zeros(Nn), held_v.astype(float)      # LP failed: keep all, buy nothing
            xd = np.zeros(Nx)
        else:
            new_d, keep_d, xd = xv[:Nn], xv[Nn:Nn + Nk], xv[Nn + Nk:]
        # rounding in lexicographic (j, l, k) order, new then kept
        allt = sorted(set(tn) | set(tk))
        ni = {tr: i for i, tr in enumerate(tn)}
        ki = {tr: i for i, tr in enumerate(tk)}
        new_r = np.zeros(Nn, dtype=np.int64)
        keep_r = held_v.copy()
        for tr in allt:
            if tr in ni:
                i = ni[tr]
                new_r[i] = round_counts([new_d[i]], [0], [np.inf], self.aux)[0]
            if tr in ki:
                i = ki[tr]
                keep_r[i] = round_counts([keep_d[i]], [pre_v[i]], [held_v[i]], self.aux)[0]
        # repair against the site capacities
        V: dict[tuple, float] = {}
        for a, (c, l) in enumerate(arcs):
            j = int(st.cl_llm[c])
            served = float(np.sum(xd[a * nsl:(a + 1) * nsl]))
            V[(j, l)] = V.get((j, l), 0.0) + served * (st.q[j] - st.delta[c, l]) * Ds / 60.0
        Nd: dict[tuple, float] = {}
        for i, (j, l, k) in enumerate(tn):
            Nd[(j, l)] = Nd.get((j, l), 0.0) + float(new_d[i])
        for i, (j, l, k) in enumerate(tk):
            Nd[(j, l)] = Nd.get((j, l), 0.0) + float(keep_d[i])
        share = {jl: (V.get(jl, 0.0) / Nd[jl] if Nd.get(jl, 0.0) > 1e-12 else 0.0) for jl in Nd}
        # one list over the union of triples, so that the repair sees new and kept replicas per site
        site_of = [tr[1] for tr in allt]
        gp = [float(st.g[tr[0]]) for tr in allt]
        nu = np.array([new_r[ni[tr]] if tr in ni else 0 for tr in allt], dtype=np.int64)
        ku = np.array([keep_r[ki[tr]] if tr in ki else 0 for tr in allt], dtype=np.int64)
        pu = np.array([pre_v[ki[tr]] if tr in ki else 0 for tr in allt], dtype=np.int64)
        bn = [share.get(tr[:2], 0.0) - (cost[ni[tr]] if tr in ni else 0.0) for tr in allt]
        bk = [share.get(tr[:2], 0.0) - st.g[tr[0]] * price[tr[1], tr[2]] * W / 60.0 for tr in allt]
        nu, ku, removed = repair_counts(site_of, gp, nu, ku, pu, bn, bk, cap)
        self.rep["repair_removals"] += removed
        # constant terms of the objective: all demand on fallback, the pre leases' rent in the window
        # minus the rent that the n_keep coefficients charge for them
        const = float(np.sum(st.q[st.cl_llm] * dhat.sum(axis=1)) * Ds / 60.0) + rent_pre
        const -= float(sum(pre_v[i] * cost[Nn + i] for i in range(Nk)))
        plan = {"t0": t0, "W_min": W, "triples": allt, "new": nu, "keep": ku, "pre": pu,
                "held": {tr: list(held.get(tr, [])) for tr in allt}, "lp_status": status, "lp_objective": obj,
                "lp_window_usd": (obj + const) if obj is not None else None,
                "n_new_lp": {tn[i]: float(new_d[i]) for i in range(Nn)},
                "n_keep_lp": {tk[i]: float(keep_d[i]) for i in range(Nk)},
                "size": size, "rent_pre_usd": rent_pre, "cap": cap}
        self.last_plan = plan
        return plan

    # -------------------------------------------------------- one slot
    def act(self, obs: SlowObs) -> list:
        for _key, r in self._begin(obs):
            if r.ok:
                b = r.action
                self.lease_triple[int(r.lease_id)] = (int(b.llm), int(b.site), int(b.contract))
        for lid in [x for x in self.lease_triple if x not in obs.leases]:
            self.lease_triple.pop(lid)
            self._gone(lid, obs)
        self.hist.push(obs)
        if obs.t % self.nW:
            return self.book.assemble(obs, self.view)
        plan = self.plan_window(obs)
        self.rep["windows"] += 1
        for i, tr in enumerate(plan["triples"]):
            lids = plan["held"][tr]
            pre_ids = [lid for lid in lids if obs.minute < obs.leases[lid].prepaid_end_min]
            rest = sorted(lid for lid in lids if lid not in pre_ids)
            n_keep_rest = int(plan["keep"][i]) - len(pre_ids)
            self.rep["kept"] += len(pre_ids) + max(0, n_keep_rest)
            for lid in rest[max(0, n_keep_rest):]:
                self.book.release(lid)
                self._released.add(lid)
                self.counts["releases"] += 1
                self.rep["released"] += 1
        for i, (j, l, k) in enumerate(plan["triples"]):
            for _ in range(int(plan["new"][i])):
                self.book.buy(("new", j, l, k), Buy(l, k, j, 1, tag="bl4"))
                self.counts["buys"] += 1
                self.rep["new"] += 1
        return self.book.assemble(obs, self.view)

    def report(self) -> dict:
        out = super().report()
        out["demand"] = self._params["demand"]
        out["info_class"] = ("online-I1" if self._params["demand"] in ("previous", "previous0")
                             else f"lookahead-{int(self._params['window_min'])}min")
        if hasattr(self, "rep"):
            out.update(self.rep)
            out["n_arcs"] = len(self.arcs)
            out["n_triples_new"] = len(self.triples_new)
        return out


__all__ = ["CoCaRStyle", "omega_share", "round_counts", "repair_counts"]
