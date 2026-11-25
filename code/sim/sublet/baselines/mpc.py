"""MPC, a forecast-based receding-horizon LP baseline (design/ms7/plan.md X4, C54; design/ms7/feasibility/baselines.md
§1(d-i), §2 item 5, §3 B4; registry id MPC in registry.MS7: online-I1, or lookahead-<W>min with the oracle forecast).

A subclass of BL4 (cocar.CoCaRStyle): its contract sets K_l (K_lj with contract_rule 'c2'), arcs and n_new triples
(CoCaRStyle._setup_arcs), its omega_share, rounding and repair helpers and its lease bookkeeping. Where BL4 plans once
per window and is blind inside it, MPC solves a multi-stage LP over the next W = window_min minutes every replan_slots
slow slots (aligned at horizon minute 0) and executes the plan's first replan_slots stages until the next solve.

LP at a solve slot t0 (S = min(W / Δs, T_slow - t0) stages, stage i the slot t0 + i; W_S = S Δs minutes), on BL4's
triples v = (j, l, k). Held = MPC's alive leases without a notice; pre_v(i) = the held leases of v still inside their
billed term at stage i ((t0 + i) Δs < prepaid_end_min). omega_jl(d) = cocar.omega_share(lambda_jl, d, Δs) is the warm
share of stage s + d of a replica bought at stage s. N_jl(i) counts the noticed own leases of (j, l), each with the
share of stage i before its death: noticed leases count as capacity until their death, are never released by MPC and
keep their GPUs out of the capacity rows, as BL4's announced leases. The constant terms of the objective are left out.
- Routing ('region', default): x_{c,R,i} >= 0 per client c, site region R into which c has a BL4 arc, and stage i,
  with cost (delta_cR - q_j) Δs / 60, served at the sites of R that have a triple of (j, l). The engine routes demand to
  any warm replica, and on the E7 instances delta_cl depends on the site only through its region (checked at reset),
  so this is BL4's routing aggregated per region, relaxed to every such site of R; it keeps the LP small, the per-site
  detail being in the triples' variables. 'arc', and the fallback with kappa_infinite or when delta_cl differs inside
  a region: x_{a,i} per BL4 arc a = (c, l), cost (delta_cl - q_j) Δs / 60. Demand rows: per client and stage, the sum
  of its routes <= dhat_c(i). The serving rows below are per route key K, (j, R) or (j, l), with the capacity terms
  and the N_jl of the key's sites summed: sum_{routes of K} x_i <= cap_K(i) + N_K(i).
- holding 'stage' (default): every stage has its own counts, so a replica can be bought at any stage and released once
  its billed term P_k is over. Variables b_{i,v} >= 0 bought at stage i, n_{i,v} >= 0 the window's purchases active at
  stage i, z_{i,v} in [pre_v(i), held_v] the held leases kept at stage i. Cost: b (beta_jl + g_j a_lk max(0, P_k - (S
  - i) Δs) / 60: the load and the part of the billed term past the window, a commitment), n and z g_j a_lk Δs / 60 per
  stage. Rows: n_{i,v} - n_{i-1,v} - b_{i,v} <= 0 (n_{-1} = 0: a released replica is not active again);
  sum_{s = i - m_v + 1}^{i} b_{s,v} - n_{i,v} <= 0 with m_v = ceil(P_k / Δs) (a purchase is active through its billed
  term); z_{i,v} - z_{i-1,v} <= 0 (held leases are only released); the capacity of (j, l) at stage i is sum_k (n_{i,v}
  + z_{i,v} - sum_{s <= i} (1 - omega_jl(i - s)) b_{s,v}) (the cold share of the purchases is subtracted, so the bound
  stays valid whatever is released); per site with finite capacity and stage i, sum_v g_j (n_{i,v} + z_{i,v}) <=
  capacity_gpus minus the GPUs of the noticed leases there.
- holding 'window' (BL4's cost model): new_{s,v} >= 0 bought at stage s and held to the window's end, keep_v in
  [pre_v(0), held_v] for the whole window. Cost: new (beta_jl + g_j a_lk max(W_S - s Δs, P_k) / 60), keep g_j a_lk W_S
  / 60. The capacity of (j, l) at stage i is sum_k (sum_{s <= i} omega_jl(i - s) new_{s,v} + keep_v); per site sum_v
  g_j (sum_s new_{s,v} + keep_v) <= capacity_gpus minus the noticed leases' GPUs (the last stage binds). With a flat
  forecast it plans like BL4; with a varying one (the oracle) it cannot plan a release inside the window and so buys
  less for short peaks than a flat forecast does, which is why 'stage' is the default.
With kappa_infinite the serving bound is per arc and scaled by the client's demand, x_{a,i} <= dhat_c(i) (cap_(j,l)(i)
+ N_jl(i)), as BL4's. The rows, columns and coefficients are built once per S (the matrix depends on dhat only through
the kappa_infinite rows); each solve sets the right-hand sides and the bounds of z (keep).
- Forecast dhat_c(i), from the slot means dbar_c (revealed at each slot's start, MS1 spec S14): 'persistence' dbar_c(t0)
  for every i (online-I1); 'ewma' e_c(t0) for every i, e_c(t) = alpha dbar_c(t) + (1 - alpha) e_c(t - 1), e_c(0) =
  dbar_c(0), updated every slot (online-I1); 'previous_day' dbar_c(t0 + i - D) with D the slots of a day, and dbar_c(t0)
  while t0 + i < D (online-I1); 'oracle' the realized slot means of the window (driver input future_demand; information
  class lookahead-<W>min, a reference only, never an online baseline).
- Rounding ('nearest', deterministic, the default; or 'random', BL4's floor + Bernoulli on the aux stream) of the
  stages s < replan_slots, in the lexicographic order of the triples (for 'random': stage 0's purchases, its kept
  counts, then stage 1's purchases and kept counts, ...). Kept counts stay in [pre_v(s), the kept count of stage s - 1]
  ('stage'; held_v at s = 0) or [pre_v(0), held_v] ('window', one kept count). BL4's repair against the site capacities
  on stage 0's purchases and kept counts (benefit per replica: the LP's value served on the route key over its replicas
  there, their mean over the stages with 'stage' and the window's total with 'window', minus the replica's cost); a
  later stage's purchases meet LeaseBook's pre-check when they are staged.
- Execution: at t0 BL4's releases (keep the pre leases and the oldest others up to stage 0's kept count, release the
  rest, which are past their billed term) and stage 0's purchases; at t0 + s, 0 < s < replan_slots, stage s's purchases
  of the last plan, each its own lease Buy(l, k, j, 1), and with 'stage' its kept counts of the leases held at t0 (the
  same rule). Purchases of the window itself are released only by a later solve. A solve whose LP fails keeps every
  held lease and buys nothing.

Status: a baseline (no ratio is claimed). Policy isolation (design/sim_spec_ms2.md §2.2): numpy, scipy, the standard
library and the baselines' modules; no file is read.
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
from .cocar import CoCaRStyle, omega_share, repair_counts, round_counts
from .common import Baseline, DemandHistory

FORECASTS = ("persistence", "ewma", "previous_day", "oracle")
ROUNDINGS = ("nearest", "random")
HOLDINGS = ("stage", "window")
ROUTINGS = ("region", "arc")
DAY_MIN = 1440


def nearest_counts(values, lo, hi) -> np.ndarray:
    """floor(v + 1/2) per entry, v clipped to the integer bounds [lo, hi] and snapped to an integer within 1e-9 first
    (the deterministic rounding of MPC; ties round up)."""
    out = np.zeros(len(values), dtype=np.int64)
    for i, (v, a, b) in enumerate(zip(values, lo, hi)):
        v = min(max(float(v), float(a)), float(b))
        r = round(v)
        if abs(v - r) <= 1e-9:
            v = float(r)
        out[i] = int(math.floor(v + 0.5))          # in [a, b]: the bounds are integers (or b infinite)
    return out


class RecedingLP(CoCaRStyle):
    """MPC (online-I1 with the online forecasts; lookahead-<W>min with 'oracle'): a multi-stage LP over the next window
    solved every replan_slots slots (module docstring)."""
    name = "mpc_receding_lp"
    PARAMS = {"window_min": 60, "replan_slots": 1, "forecast": "persistence", "ewma_alpha": 0.5,
              "contract_rule": "kstar", "rounding": "nearest", "holding": "stage", "routing": "region"}
    INPUTS = ("future_demand",)

    def _validate(self) -> None:
        p = self._params
        self._choice("forecast", FORECASTS)
        self._choice("rounding", ROUNDINGS)
        self._choice("holding", HOLDINGS)
        self._choice("routing", ROUTINGS)
        for k in ("window_min", "replan_slots"):
            v = p[k]
            if isinstance(v, bool) or not isinstance(v, (int, np.integer)) or v < 1:
                raise PolicyError(f"RecedingLP: {k} must be an integer >= 1, got {v!r}")
        a = p["ewma_alpha"]
        if isinstance(a, bool) or not isinstance(a, (int, float, np.floating, np.integer)) or not 0.0 < float(a) <= 1.0:
            raise PolicyError(f"RecedingLP: ewma_alpha must be a number in (0, 1], got {a!r}")
        if p["forecast"] == "previous_day" and p["window_min"] >= DAY_MIN:
            raise PolicyError("RecedingLP: forecast 'previous_day' needs window_min < 1440")
        if p["forecast"] == "oracle" and self._inputs.get("future_demand") is None:
            raise PolicyError("RecedingLP: forecast 'oracle' needs the driver input future_demand (n, T_slow)")

    # -------------------------------------------------------- reset
    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        Baseline.reset(self, view, rng)
        p = self._params
        W = int(p["window_min"])
        if W % self.slow_min:
            raise PolicyError(f"RecedingLP: window_min {W} is not a multiple of the slow slot {self.slow_min}")
        self.nW = W // self.slow_min
        self.R = int(p["replan_slots"])
        if self.R > self.nW:
            raise PolicyError(f"RecedingLP: replan_slots {self.R} exceeds the window's {self.nW} slots")
        self.stage = p["holding"] == "stage"
        self.aux = self.streams["aux"]
        self.kinf = bool(view.kappa_infinite)
        self.day = DAY_MIN // self.slow_min
        self.hist = DemandHistory(self.n, self.day + 1 if p["forecast"] == "previous_day" else 1)
        self.ewma: Optional[np.ndarray] = None
        if p["forecast"] == "oracle":
            fd = np.asarray(self._inputs["future_demand"], dtype=np.float64)
            if fd.shape != (self.n, self.T_slow):
                raise PolicyError(f"RecedingLP: future_demand has shape {fd.shape}, expected {(self.n, self.T_slow)}")
            self.future = fd
        self._setup_arcs(view)
        self.tidx = {tr: i for i, tr in enumerate(self.triples_new)}
        self.routes, self.routing = self._routes(view)
        # billed term P_k (minutes, BL4's) and m_v = ceil(P_k / Δs) stages per triple
        self.P = np.array([float(view.contracts[k].prepaid_min) for _j, _l, k in self.triples_new])
        self.m_P = np.array([max(1, math.ceil(P / self.slow_min - 1e-9)) for P in self.P], dtype=np.int64)
        self.lease_triple: dict[int, tuple[int, int, int]] = {}
        self.pending: dict[int, tuple] = {}          # slot -> (purchases, kept counts or None) of a later stage
        self._lp: dict[int, dict] = {}               # S -> the LP's structure
        self.last_plan: Optional[dict] = None
        self.lp_seconds = 0.0                        # wall time of the LPs (kept out of report(): it is deterministic)
        self.rep = {"solves": 0, "lp_status": {}, "lp_n_vars_max": 0, "lp_n_rows_max": 0, "lp_nnz_max": 0,
                    "new": 0, "new_later": 0, "kept": 0, "released": 0, "released_later": 0, "repair_removals": 0,
                    "noticed_counted": 0, "precheck_dropped": 0}

    # -------------------------------------------------------- forecasts
    def _observe_demand(self, obs: SlowObs) -> np.ndarray:
        """Push slot obs.t into the history and update the EWMA; returns dbar(t)."""
        _, mean = self.hist.push(obs)
        a = float(self._params["ewma_alpha"])
        self.ewma = mean.copy() if self.ewma is None else a * mean + (1.0 - a) * self.ewma
        return mean

    def forecast(self, t0: int, S: int, mean: np.ndarray) -> np.ndarray:
        """(n, S) dhat of the window starting at t0 (module docstring); `mean` is dbar(t0)."""
        f = self._params["forecast"]
        if f == "oracle":
            return self.future[:, t0:t0 + S].copy()
        if f == "ewma":
            return np.repeat(self.ewma[:, None], S, axis=1)
        if f == "previous_day":
            cols = [self.hist.mean_at(t0 + i - self.day) if t0 + i - self.day >= 0 else mean for i in range(S)]
            return np.stack(cols, axis=1)
        return np.repeat(mean[:, None], S, axis=1)

    # -------------------------------------------------------- the LP's structure (per S)
    def _structure(self, S: int) -> dict:
        """Rows, columns, coefficients, costs and row blocks of the LP with S stages (module docstring), cached."""
        if S not in self._lp:
            self._lp[S] = self._structure_stage(S) if self.stage else self._structure_window(S)
        return self._lp[S]

    def _routes(self, view: PublicView) -> tuple[list, str]:
        """The LP's routing variables (module docstring, 'Routing'): [(c, key, sites)], per arc (c, l) with key (j, l)
        and sites (l,) ('arc'), or per client c and site region R with key (j, R) and the sites of R that have a triple
        of (j, l) ('region'). 'region' needs a finite kappa and delta_cl equal over those sites for every client with an
        arc into R; otherwise the routing is 'arc'. Returns (routes, the routing used)."""
        st = self.sites
        arc_routes = [(c, (int(st.cl_llm[c]), l), (l,)) for c, l in self.arcs]
        if self._params["routing"] == "arc" or self.kinf:
            return arc_routes, "arc"
        reg = [s.region for s in view.sites]
        sites_of: dict[tuple, set] = {}
        for j, l, _k in self.triples_new:
            sites_of.setdefault((j, reg[l]), set()).add(l)
        out, seen = [], set()
        for c, l in self.arcs:
            j, R = int(st.cl_llm[c]), reg[l]
            if (c, R) in seen:
                continue
            seen.add((c, R))
            sites = tuple(sorted(sites_of[(j, R)]))
            d = {float(st.delta[c, x]) for x in sites}
            if len(d) != 1 or not np.isfinite(next(iter(d))):
                return arc_routes, "arc"
            out.append((c, (j, R), sites))
        return out, "region"

    def _demand_rows(self, S: int, oX: int, rows: list, cols: list, vals: list, dix: list) -> tuple[int, list]:
        """The demand rows (rows 0, 1, ...): per client and stage, sum of its routes <= dhat_c(i); returns (next row,
        demand rows (row, c, i))."""
        r = 0
        of_c: dict[int, list[int]] = {}
        for x, (c, _key, _sites) in enumerate(self.routes):
            of_c.setdefault(c, []).append(x)
        dem = []
        for c, xs in sorted(of_c.items()):
            for i in range(S):
                for x in xs:
                    rows.append(r); cols.append(oX + x * S + i); vals.append(1.0); dix.append(-1)
                dem.append((r, c, i))
                r += 1
        return r, dem

    def _serving_rows(self, S: int, oX: int, r: int, cap_terms, rows: list, cols: list, vals: list,
                      dix: list) -> tuple[int, list]:
        """The serving rows from row r: per route key ((j, l) or (j, R)) and stage i, or per arc and stage with
        kappa_infinite (the capacity terms then scaled by the client's dhat through dix); cap_terms(jl, i) lists the
        (column, coefficient) pairs of the capacity of (j, l) at stage i, summed over the key's sites. Returns (next
        row, serving rows (row, the key's (j, l) pairs, i, c or -1))."""
        srv = []
        if self.kinf:
            for x, (c, jl, _sites) in enumerate(self.routes):
                for i in range(S):
                    rows.append(r); cols.append(oX + x * S + i); vals.append(1.0); dix.append(-1)
                    for col, w in cap_terms(jl, i):
                        rows.append(r); cols.append(col); vals.append(-w); dix.append(c * S + i)
                    srv.append((r, (jl,), i, c))
                    r += 1
            return r, srv
        of_key: dict[tuple, list[int]] = {}
        sites_of: dict[tuple, tuple] = {}
        for x, (_c, key, sites) in enumerate(self.routes):
            of_key.setdefault(key, []).append(x)
            sites_of[key] = sites
        for key, xs in sorted(of_key.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
            jls = tuple((key[0], l) for l in sites_of[key])
            for i in range(S):
                for x in xs:
                    rows.append(r); cols.append(oX + x * S + i); vals.append(1.0); dix.append(-1)
                for jl in jls:
                    for col, w in cap_terms(jl, i):
                        rows.append(r); cols.append(col); vals.append(-w); dix.append(-1)
                srv.append((r, jls, i, -1))
                r += 1
        return r, srv

    def _route_costs(self, cost: np.ndarray, S: int, oX: int) -> None:
        st, Ds = self.sites, self.slow_min
        for x, (c, key, sites) in enumerate(self.routes):
            cost[oX + x * S: oX + (x + 1) * S] = (st.delta[c, sites[0]] - st.q[key[0]]) * Ds / 60.0

    def _omega_trips(self, S: int) -> tuple[dict, dict]:
        """({(j, l): [omega_jl(d), d < S]}, {(j, l): its triple indices})."""
        lam = np.asarray(self.view.lam_s, dtype=np.float64)
        trips: dict[tuple, list[int]] = {}
        for v, (j, l, k) in enumerate(self.triples_new):
            trips.setdefault((j, l), []).append(v)
        om = {jl: [omega_share(lam[jl[0], jl[1]], d, self.slow_min) for d in range(S)] for jl in trips}
        return om, trips

    def _pack(self, kind: str, S: int, nv: int, r: int, cost, rows, cols, vals, dix, dem, srv, cap, **offsets) -> dict:
        return {"kind": kind, "S": S, "W": S * self.slow_min, "nv": nv, "n_rows": r, "Nn": len(self.triples_new),
                "Na": len(self.routes), "cost": cost, "rows": np.asarray(rows, dtype=np.int64),
                "cols": np.asarray(cols, dtype=np.int64), "vals": np.asarray(vals, dtype=np.float64),
                "dix": np.asarray(dix, dtype=np.int64), "dem": np.asarray(dem, dtype=np.int64).reshape(-1, 3),
                "srv": srv, "cap": cap, **offsets}

    def _structure_stage(self, S: int) -> dict:
        view, st, Ds = self.view, self.sites, self.slow_min
        price = np.asarray(view.price, dtype=np.float64)
        beta = np.asarray(view.beta_usd, dtype=np.float64)
        tn = self.triples_new
        Nn = len(tn)
        oB, oN, oZ, oX = 0, S * Nn, 2 * S * Nn, 3 * S * Nn
        nv = oX + len(self.routes) * S
        cost = np.zeros(nv)
        for v, (j, l, k) in enumerate(tn):
            rate = st.g[j] * price[l, k] / 60.0
            for i in range(S):
                cost[oB + i * Nn + v] = beta[j, l] + rate * max(0.0, self.P[v] - (S - i) * Ds)
                cost[oN + i * Nn + v] = rate * Ds
                cost[oZ + i * Nn + v] = rate * Ds
        self._route_costs(cost, S, oX)
        rows, cols, vals, dix = [], [], [], []
        r, dem = self._demand_rows(S, oX, rows, cols, vals, dix)
        om, trips = self._omega_trips(S)

        def cap_terms(jl, i):
            out = []
            for v in trips.get(jl, ()):
                out += [(oN + i * Nn + v, 1.0), (oZ + i * Nn + v, 1.0)]
                out += [(oB + s * Nn + v, -(1.0 - om[jl][i - s])) for s in range(i + 1) if om[jl][i - s] < 1.0]
            return out
        r, srv = self._serving_rows(S, oX, r, cap_terms, rows, cols, vals, dix)
        for v in range(Nn):
            m = int(self.m_P[v])
            for i in range(S):
                # activity: n_i - n_{i-1} - b_i <= 0
                rows += [r, r]; cols += [oN + i * Nn + v, oB + i * Nn + v]; vals += [1.0, -1.0]; dix += [-1, -1]
                if i:
                    rows.append(r); cols.append(oN + (i - 1) * Nn + v); vals.append(-1.0); dix.append(-1)
                r += 1
                # billed term: the purchases of the last m_v stages are active, sum b - n_i <= 0
                rows.append(r); cols.append(oN + i * Nn + v); vals.append(-1.0); dix.append(-1)
                for s in range(max(0, i - m + 1), i + 1):
                    rows.append(r); cols.append(oB + s * Nn + v); vals.append(1.0); dix.append(-1)
                r += 1
                # held leases are only released: z_i - z_{i-1} <= 0
                if i:
                    rows += [r, r]; cols += [oZ + i * Nn + v, oZ + (i - 1) * Nn + v]; vals += [1.0, -1.0]
                    dix += [-1, -1]
                    r += 1
        cap = []                                      # (row, site, stage)
        for l in sorted({l for _, l, _ in tn}):
            if not np.isfinite(float(view.sites[l].capacity_gpus)):
                continue
            at = [(v, float(st.g[j])) for v, (j, ll, k) in enumerate(tn) if ll == l]
            for i in range(S):
                for v, g in at:
                    rows += [r, r]; cols += [oN + i * Nn + v, oZ + i * Nn + v]; vals += [g, g]; dix += [-1, -1]
                cap.append((r, l, i))
                r += 1
        return self._pack("stage", S, nv, r, cost, rows, cols, vals, dix, dem, srv, cap, oB=oB, oN=oN, oZ=oZ, oX=oX)

    def _structure_window(self, S: int) -> dict:
        view, st, Ds = self.view, self.sites, self.slow_min
        price = np.asarray(view.price, dtype=np.float64)
        beta = np.asarray(view.beta_usd, dtype=np.float64)
        tn = self.triples_new
        Nn = len(tn)
        oK, oX = S * Nn, (S + 1) * Nn                 # offsets of keep and x
        nv = oX + len(self.routes) * S
        W = S * Ds
        cost = np.zeros(nv)
        for v, (j, l, k) in enumerate(tn):
            for s in range(S):
                cost[s * Nn + v] = beta[j, l] + st.g[j] * price[l, k] * max(W - s * Ds, self.P[v]) / 60.0
            cost[oK + v] = st.g[j] * price[l, k] * W / 60.0
        self._route_costs(cost, S, oX)
        rows, cols, vals, dix = [], [], [], []
        r, dem = self._demand_rows(S, oX, rows, cols, vals, dix)
        om, trips = self._omega_trips(S)

        def cap_terms(jl, i):
            out = []
            for v in trips.get(jl, ()):
                out += [(s * Nn + v, om[jl][i - s]) for s in range(i + 1) if om[jl][i - s] > 0.0]
                out.append((oK + v, 1.0))
            return out
        r, srv = self._serving_rows(S, oX, r, cap_terms, rows, cols, vals, dix)
        cap = []                                      # (row, site, -1: every stage)
        for l in sorted({l for _, l, _ in tn}):
            if not np.isfinite(float(view.sites[l].capacity_gpus)):
                continue
            for v, (j, ll, k) in enumerate(tn):
                if ll != l:
                    continue
                for s in range(S):
                    rows.append(r); cols.append(s * Nn + v); vals.append(float(st.g[j])); dix.append(-1)
                rows.append(r); cols.append(oK + v); vals.append(float(st.g[j])); dix.append(-1)
            cap.append((r, l, -1))
            r += 1
        return self._pack("window", S, nv, r, cost, rows, cols, vals, dix, dem, srv, cap, oK=oK, oX=oX)

    # -------------------------------------------------------- one solve
    def _held(self, obs: SlowObs, S: int) -> tuple:
        """(held {triple index: lease ids}, pre (S, Nn): held leases inside their billed term per stage, noticed
        {(j, l): (S,) shares before death}, GPUs of the noticed leases per site) at the solve slot."""
        Ds, Nn = self.slow_min, len(self.triples_new)
        held: dict[int, list[int]] = {}
        pre = np.zeros((S, Nn), dtype=np.int64)
        noticed: dict[tuple, np.ndarray] = {}
        ann_gpus: dict[int, float] = {}
        starts = (obs.t + np.arange(S)) * Ds
        for lid, tr in self.lease_triple.items():
            Lv = obs.leases.get(lid)
            if Lv is None or tr not in self.tidx:
                continue
            v = self.tidx[tr]
            if Lv.announce_slot is not None:
                ann_gpus[Lv.site] = ann_gpus.get(Lv.site, 0.0) + Lv.gpus
                if Lv.death_min is not None:
                    alive = np.clip((float(Lv.death_min) - starts) / Ds, 0.0, 1.0)
                    noticed[tr[:2]] = noticed.get(tr[:2], np.zeros(S)) + alive
                    self.rep["noticed_counted"] += 1          # (solve, noticed lease) pairs
                continue
            held.setdefault(v, []).append(lid)
            pre[:, v] += (starts < Lv.prepaid_end_min).astype(np.int64)
        return held, pre, noticed, ann_gpus

    def plan(self, obs: SlowObs, mean: np.ndarray) -> dict:
        """Solve the LP at t0 = obs.t, round the stages s < replan_slots (purchases and kept counts) and repair stage
        0; returns the plan (also kept in last_plan)."""
        view, st, Ds = self.view, self.sites, self.slow_min
        t0 = obs.t
        S = min(self.nW, self.T_slow - t0)
        L = self._structure(S)
        Nn = L["Nn"]
        tn = self.triples_new
        dhat = self.forecast(t0, S, mean)
        price = np.asarray(view.price, dtype=np.float64)
        held, pre, noticed, ann_gpus = self._held(obs, S)
        held_n = np.array([len(held.get(v, ())) for v in range(Nn)], dtype=np.int64)
        lo = np.zeros(L["nv"])
        hi = np.full(L["nv"], np.inf)
        if self.stage:
            for i in range(S):
                a = L["oZ"] + i * Nn
                lo[a:a + Nn], hi[a:a + Nn] = pre[i], held_n
        else:
            lo[L["oK"]:L["oK"] + Nn], hi[L["oK"]:L["oK"] + Nn] = pre[0], held_n
        rhs = np.zeros(L["n_rows"])
        dem = L["dem"]
        if len(dem):
            rhs[dem[:, 0]] = dhat[dem[:, 1], dem[:, 2]]
        for r, jls, i, c in L["srv"]:
            nt = sum(float(noticed[jl][i]) for jl in jls if jl in noticed)
            if nt:
                rhs[r] = nt * (float(dhat[c, i]) if c >= 0 else 1.0)
        for r, l, _i in L["cap"]:
            rhs[r] = float(view.sites[l].capacity_gpus) - ann_gpus.get(l, 0.0)
        vals = L["vals"]
        if self.kinf:
            vals = vals.copy()
            m = L["dix"] >= 0
            vals[m] = vals[m] * dhat.reshape(-1)[L["dix"][m]]
        ts = time.perf_counter()
        if L["nv"] == 0:
            status, xv, obj = 0, np.zeros(0), 0.0
        else:
            A = sp.csr_matrix((vals, (L["rows"], L["cols"])), shape=(L["n_rows"], L["nv"])) if L["n_rows"] else None
            res = linprog(L["cost"], A_ub=A, b_ub=rhs if L["n_rows"] else None, bounds=np.column_stack([lo, hi]),
                          method="highs")
            status, xv = int(res.status), res.x
            obj = float(res.fun) if status == 0 else None
        self.lp_seconds += time.perf_counter() - ts
        self.rep["solves"] += 1
        self.rep["lp_status"][str(status)] = self.rep["lp_status"].get(str(status), 0) + 1
        self.rep["lp_n_vars_max"] = max(self.rep["lp_n_vars_max"], int(L["nv"]))
        self.rep["lp_n_rows_max"] = max(self.rep["lp_n_rows_max"], int(L["n_rows"]))
        self.rep["lp_nnz_max"] = max(self.rep["lp_nnz_max"], int(len(vals)))
        if status != 0 or xv is None:
            plan = {"t0": t0, "S": S, "lp_status": status, "new": {}, "keep": {0: held_n.copy()}, "pre": pre,
                    "held": held, "ok": False}
            self.last_plan = plan
            return plan
        n_exec = min(self.R, S)
        inf, zero = np.full(Nn, np.inf), np.zeros(Nn)
        rnd = self._params["rounding"] == "random"

        def rounded(values, a, b):
            return round_counts(values, a, b, self.aux) if rnd else nearest_counts(values, a, b)
        if self.stage:
            buys = xv[L["oB"]:L["oN"]].reshape(S, Nn)
            keeps = xv[L["oZ"]:L["oX"]].reshape(S, Nn)
            active = xv[L["oN"]:L["oZ"]].reshape(S, Nn) + keeps
        else:
            buys = xv[:L["oK"]].reshape(S, Nn)
            keeps = np.repeat(xv[L["oK"]:L["oX"]][None, :], S, axis=0)
            active = np.cumsum(buys, axis=0) + keeps
        xd = xv[L["oX"]:]
        new_r: dict[int, np.ndarray] = {}
        keep_r: dict[int, np.ndarray] = {}
        for s in range(n_exec):
            new_r[s] = rounded(buys[s], zero, inf)
            if s == 0:
                keep_r[0] = rounded(keeps[0], pre[0], held_n)
            elif self.stage:
                keep_r[s] = rounded(keeps[s], np.minimum(pre[s], keep_r[s - 1]), keep_r[s - 1])
        # repair of stage 0 against the site capacities (BL4's benefit with the LP's mean replicas of (j, l))
        V: dict[tuple, float] = {}                    # value served per route key
        for x, (c, key, sites) in enumerate(self.routes):
            served = float(np.sum(xd[x * S:(x + 1) * S]))
            V[key] = V.get(key, 0.0) + served * (st.q[key[0]] - st.delta[c, sites[0]]) * Ds / 60.0
        key_of = {(j, l): ((j, view.sites[l].region) if self.routing == "region" else (j, l)) for j, l, _k in tn}
        Nd: dict[tuple, float] = {}                   # replicas per key: mean over the stages ('window': the last)
        for v, (j, l, k) in enumerate(tn):
            key = key_of[(j, l)]
            Nd[key] = Nd.get(key, 0.0) + float(active[:, v].mean() if self.stage else active[-1, v])
        share = {jl: (V.get(key, 0.0) / Nd[key] if Nd.get(key, 0.0) > 1e-12 else 0.0) for jl, key in key_of.items()}
        cap = {l: float(view.sites[l].capacity_gpus) - ann_gpus.get(l, 0.0) for _r, l, _i in L["cap"]}
        beta = np.asarray(view.beta_usd, dtype=np.float64)
        span = Ds if self.stage else L["W"]           # the minutes a kept replica is charged for in the LP
        rate = [st.g[tr[0]] * price[tr[1], tr[2]] / 60.0 for tr in tn]
        bn = [share.get(tr[:2], 0.0) - beta[tr[0], tr[1]] - rate[v] * max(span, self.P[v]) for v, tr in enumerate(tn)]
        bk = [share.get(tr[:2], 0.0) - rate[v] * span for v, tr in enumerate(tn)]
        new0, keep0, removed = repair_counts([tr[1] for tr in tn], [float(st.g[tr[0]]) for tr in tn], new_r[0],
                                             keep_r[0], pre[0], bn, bk, cap)
        new_r[0] = new0
        keep_r = {s: (keep0 if s == 0 else np.minimum(k, keep0)) for s, k in keep_r.items()}
        self.rep["repair_removals"] += removed
        plan = {"t0": t0, "S": S, "lp_status": status, "lp_objective": obj, "new": new_r, "keep": keep_r,
                "pre": pre, "held": held, "ok": True, "dhat_sum": float(dhat.sum()),
                "lp_active": [float(x) for x in active.sum(axis=1)]}
        self.last_plan = plan
        return plan

    # -------------------------------------------------------- one slot
    def _stage_buys(self, counts: np.ndarray, later: bool) -> None:
        for i, n in enumerate(counts):
            j, l, k = self.triples_new[i]
            for _ in range(int(n)):
                self.book.buy(("new", j, l, k), Buy(l, k, j, 1, tag="mpc"))
                self.counts["buys"] += 1
                self.rep["new_later" if later else "new"] += 1

    def _release_to(self, obs: SlowObs, held: dict, keep: np.ndarray, later: bool) -> None:
        """Per triple, keep the leases of `held` inside their billed term and the oldest others up to the kept count
        keep[v], and release the rest (BL4's execution rule); leases that ended, were released or got a notice since
        the solve are skipped."""
        for v, lids in sorted(held.items()):
            alive = [lid for lid in lids if lid in obs.leases and lid not in self._released
                     and obs.leases[lid].announce_slot is None]
            pre_ids = [lid for lid in alive if obs.minute < obs.leases[lid].prepaid_end_min]
            rest = sorted(lid for lid in alive if lid not in pre_ids)
            n_keep_rest = int(keep[v]) - len(pre_ids)
            if not later:
                self.rep["kept"] += len(pre_ids) + max(0, min(n_keep_rest, len(rest)))
            for lid in rest[max(0, n_keep_rest):]:
                self.book.release(lid)
                self._released.add(lid)
                self.counts["releases"] += 1
                self.rep["released_later" if later else "released"] += 1

    def act(self, obs: SlowObs) -> list:
        for _key, r in self._begin(obs):
            if r.ok:
                b = r.action
                self.lease_triple[int(r.lease_id)] = (int(b.llm), int(b.site), int(b.contract))
            elif r.reason == "precheck":
                self.rep["precheck_dropped"] += 1
        for lid in [x for x in self.lease_triple if x not in obs.leases]:
            self.lease_triple.pop(lid)
            self._gone(lid, obs)
        mean = self._observe_demand(obs)
        t = obs.t
        if t % self.R:
            buys, keep = self.pending.pop(t, (np.zeros(0, dtype=np.int64), None))
            if keep is not None and self.last_plan is not None:
                self._release_to(obs, self.last_plan["held"], keep, later=True)
            self._stage_buys(buys, later=True)
            return self.book.assemble(obs, self.view)
        self.pending = {}
        plan = self.plan(obs, mean)
        if not plan["ok"]:
            return self.book.assemble(obs, self.view)
        self._release_to(obs, plan["held"], plan["keep"][0], later=False)
        self._stage_buys(plan["new"][0], later=False)
        for s in range(1, min(self.R, plan["S"])):
            self.pending[t + s] = (plan["new"][s], plan["keep"].get(s) if self.stage else None)
        return self.book.assemble(obs, self.view)

    def report(self) -> dict:
        out = Baseline.report(self)
        p = self._params
        out["forecast"] = p["forecast"]
        out["holding"] = p["holding"]
        out["routing"] = getattr(self, "routing", p["routing"])
        out["info_class"] = (f"lookahead-{int(p['window_min'])}min" if p["forecast"] == "oracle" else "online-I1")
        if hasattr(self, "rep"):
            out.update(self.rep)
            out["n_arcs"] = len(self.arcs)
            out["n_routes"] = len(self.routes)
            out["n_triples_new"] = len(self.triples_new)
        return out


__all__ = ["RecedingLP", "FORECASTS", "ROUNDINGS", "HOLDINGS", "ROUTINGS", "nearest_counts"]
