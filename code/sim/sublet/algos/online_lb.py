"""The per-group online lower bound LB'(t) of Lemma G5' and the pilot's allowance B(t) = min{W_k(t), LB'(t)}
(design/theory/c3_c4_c5_general.md §9, 'Per-group allowance', Lemma G5', Corollary G3', 'The pilot's instance of
U'; design/sublet_v2.md §2.5, §5 P2), computed online from the public view and SlowObs.demand.

Definition (C3 §9, full-model form). Groups: for an LLM j, (c, l) is a usable arc if j_c = j and delta_cl is finite
and < q_j (the arcs the engine may route over, engine.arc_ok); a group Gamma of j is a connected component, with at
least one site, of the bipartite graph on the clients of j and the sites whose edges are the usable arcs of j (a
client without a usable arc is in no group). Per group, with j = j_Gamma and Delta_f the fast slot in minutes:
  zeta_k   = P_k / (ceil(P_k / Delta_f) Delta_f) for P_k > 0, 1 for P_k = 0 (P_k the minimum billed term);
  r        = min over the group's sites l and the contracts k of l's menu of zeta_k g_j a_lk (USD per replica-hour);
  theta_jl = ceil(lam_ms_jl / (60000 Delta_f)), lam_ms the engine's integer milliseconds (rule T8,
             Instance.lam_ms, algos.common.lam_ms), and Lambda-bar_jl = min{lam_s_jl / 60, theta_jl Delta_f} minutes;
  hat-beta = min_l beta_jl + r min_l Lambda-bar_jl / 60 (the entry cost: loading charge and the rent of the loading
             fast slots that every warm replica paid);
  capacitated (kappa_infinite false): h_f(n) = n r + q_j (d_Gamma(f) - n)^+ with d_Gamma(f) the group's demand in
     replica loads, n_f its least minimizer (floor(d) + [q_j (d - floor(d)) > r] if r < q_j, 0 if r >= q_j), and
     LB'_Gamma(t) = min over nu >= 0 of nu hat-beta + (Delta_f / 60) sum_{f <= f_t} h_f(min{nu, n_f});
  uncapacitated (kappa_infinite true; no all-fallback shortcut for r >= q_j): LB'_Gamma(t) = min{(Delta_f / 60)
     sum_{f <= f_t} q_j d_Gamma(f), hat-beta + (Delta_f / 60) sum_{f <= f_t} min{r, q_j d_Gamma(f)}};
  LB'(t) = sum over groups of LB'_Gamma(t), with f_t the last fast slot of slow slot t.
W_k(t) = sum over the groups with a site where the baselines' k*(l) is defined (baselines.common.k_star) of p_Gamma
ceil(max_{f <= f_t} d_Gamma(f) - 1e-9), p_Gamma = min over those sites of beta~_{j l k*} + g_j a_{l k*} P_{k*} / 60
(PublicView.beta_tilde_usd): one billed term of a fresh fleet sized to each group's observed peak, as
run_proj.wk_series. B(t) = min{W_k(t), LB'(t)}: Lemma G5'(a) with U = W_k, kappa = 1.

Status. Lemma G5' (LB'(T) <= min{q |sigma|, OPT(sigma, omega)} on the core; ALG(t) >= LB'(t) on every engine run, hence
LB'(T) <= the full-model OPT(sigma, omega), which leaves out site capacities and refusals and so only lowers the
benchmark, and LB'(T) <= the fast-grid MILP) and Corollary G3' (G3 with B <= kappa LB' in place of B <= kappa B_on; for
B = min{U, LB'} the constant of G3(b) is (1 + gamma) c(gamma') + 1, about 12.66 at gamma = 1, gamma' = 1 + 1/sqrt 2)
are PROVEN (audited: design/theory/audit_guard.md, 'Audit addendum (P6)'; Corollary G3' on the core, and for A8P on
core exports with the label of Remark R(e)'s core-export bullet, which rests on C3 §9, "A8's mode S on core exports").
Numerical evidence: code/theory_checks/c3/check_g5p.py (LB' against MILP solves and exact optima, with the prototype's
groups and (r, K)), code/sim/audit/x10_g5p_pathwise.py (Lemma G5'(c) on fuzzed engine runs), x11_g5p_oracle.py (an
independent oracle against this module, x10's lb_prime and the prototype, with edge cases), x12_g5p_same_list.py (Lemma
G5'(c) with Load and Unload on objects created earlier in the same list) and tests/test_online_lb.py. LB' is not a
bound on the LP relaxation in the capacitated model (C3 §9, 'What does not hold', item 2). W_k is not a lower bound on
the optimum.

Online (Lemma G5'(a)). The groups, r, hat-beta and p_Gamma are functions of the PublicView (the clients' LLMs and
routing costs, q_j, g_j, menus, prices, contracts, load times, loading charges, kappa_infinite), fixed at construction;
step(obs) at slow slot t reads only obs.demand, the demand of the fast slots of slot t (rule T9: known at step (2) of
slot t, before the platform acts), and the state of the earlier slots. The minimum over nu: for nu >= M_t = max_{f <=
f_t} n_f, Xi_nu(t) = Xi_{M_t}(t) + (nu - M_t) hat-beta, so the minimum is attained in {0, ..., M_t}; step keeps the
running sums S[nu] for nu = 0, ..., M (M the running maximum of n_f) and, when an n_f of slot t exceeds M, extends S
with copies of S[M] before the slot's terms are added (every earlier n_f is <= M, so every S[nu] with nu > M had
received exactly S[M]'s terms), then adds the term of each fast slot of t to every S[nu]. For nonnegative loading
charges beta and beta~ and fallback prices q_j (every instance of build_instance and from_core) LB'(t), W_k(t) and B(t)
are nonnegative and nondecreasing: sums of nonnegative terms, running maxima, minima of such. This holds in floating
point too (C3 §9, fact F7): a sum of nonnegative terms never decreases; the new entries of S copy S[M] and fl(nu
hat-beta) is nondecreasing in nu, so the minimum over nu never decreases; the group sums run in a fixed order; and W_k
= p ceil(peak - WK_TOL) with p >= 0 and a running maximum peak. So B is an allowance as the guard needs it:
Ratchet.step rejects a decrease beyond GUARD_TOL max(1, |B|), and Proposition P(d) uses the exact float monotonicity.
With beta < 0 the series can decrease (code/sim/audit/x14_prop_p_lp_lb.py).

Relation to the prototype (C3 §9, 'Relation to the prototype'). The pilot's alternative allowance is the rule
'mix:0:1:1:Wk' (ms5b_common.RULE_ALT) of run_proj.allowance in the prototype copies
sublet/experiments/ms5b_proto/{lb.py, run_proj.py}, computed offline from the whole horizon's demand. On every instance
that meets (i) kappa_infinite false or no group with r >= q_j, (ii) Delta_f divides every offered P_k, (iii) no load
time in the half-millisecond corner (lam_ms a multiple of 60000 Delta_f with 1000 lam_s > lam_ms) and (iv) a horizon of
at least two fast slots or fewer than eight clients in every group (conditions(view)), OnlineLB's series equals the
prototype's bit for bit: the groups are in the prototype's order (by LLM, then by the least client of each component;
clients and sites ascending), d_Gamma(f) is the sequential sum of the group's client rows in client order (numpy's sum
over axis 0 of lb.py adds row by row whenever the horizon has at least two fast slots, and sums a single column
sequentially below eight rows), and every term is formed with the prototype's operations: n r + q (d - n)^+ with (c
Delta_f) / 60 per fast slot and sequential running sums (np.cumsum), nu hat-beta + S[nu] with hat-beta = b + (r
Lambda-bar) / 60, q d Delta_f / 60 for an all-fallback group, the sum over groups in group order from 0.0, and min{W_k,
LB'} for the prototype's min{0 F + 1 W_k, 1 LB'} (0 F + 1 W_k = W_k and 1 LB' = LB' exactly, since the cumulative
fallback F is finite and W_k >= +0.0). Under (ii) zeta_k = 1 and zeta_k g a = g a exactly; under (iii) Lambda-bar =
lam_s / 60 exactly (if lam_s / 60 <= theta Delta_f in the reals, its rounding is <= the integer theta Delta_f), and
min_l fl(lam_s / 60) = fl(min_l lam_s / 60) by the monotonicity of rounding, which is the prototype's min(lam) / 60.
Condition (iv) excludes the one case within (i)-(iii) where the two codes may differ: a horizon of a single fast slot
with at least eight clients in a group, where lb.py's sum over axis 0 is a reduction over one contiguous column, which
numpy sums pairwise from eight elements on (sequentially below eight): with n_Gamma the group's clients and u = 2^-53
the two values of d_Gamma then differ by at most 2 (n_Gamma - 1) u d_Gamma, and the series differ only through d_Gamma.
Outside (i)-(iii) the prototype differs (it puts a group with r >= q_j on all-fallback also under kappa_infinite, omits
zeta_k and uses lam_s / 60 in the corner), and all three differences can make its value exceed the optimum: the first
two by a factor (C3 §9, 'What does not hold', item 1; tests/test_online_lb.py checks both probes of check_g5p.py), the
third by at most r_Gamma / (7.2e6) USD per entry, in the corner only.
"""
from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Optional

import numpy as np

from ..baselines.common import k_star
from ..types import PublicView
from .common import PolicyError, lam_ms

WK_TOL = 1e-9          # W_k's ceiling: ceil(peak - WK_TOL) (run_proj.wk_series, b0_auto's unit per replica)


def zeta(view: PublicView) -> np.ndarray:
    """(K,) zeta_k = P_k / (ceil(P_k / Delta_f) Delta_f) for P_k > 0, 1.0 for P_k = 0 (C3 §9; exactly 1.0 iff
    Delta_f divides P_k)."""
    Df = int(view.grid.fast_min)
    out = np.ones(len(view.contracts))
    for k, c in enumerate(view.contracts):
        P = int(c.prepaid_min)
        if P > 0:
            out[k] = P / (-(-P // Df) * Df)
    return out


def usable_arcs(view: PublicView) -> np.ndarray:
    """(n, m) bool: delta_cl finite and < q_{j_c} (engine.arc_ok)."""
    q = np.array([x.q_usd_per_h for x in view.llms], dtype=np.float64)
    cl = np.asarray(view.client_llm, dtype=np.int64)
    dl = np.asarray(view.client_delta_usd_per_h, dtype=np.float64)
    with np.errstate(invalid="ignore"):
        return np.isfinite(dl) & (dl < q[cl][:, None])


def groups(view: PublicView) -> list[tuple[int, tuple[int, ...], tuple[int, ...]]]:
    """[(j, clients, sites)]: the groups of C3 §9 in the prototype's order (lb.groups): by LLM j, then by the least
    client of each connected component; clients and sites ascending; components without a site left out."""
    ok = usable_arcs(view)
    cl = np.asarray(view.client_llm, dtype=np.int64)
    out = []
    for j in range(len(view.llms)):
        cs = [int(c) for c in np.flatnonzero(cl == j)]
        seen: set[int] = set()
        for c0 in cs:
            if c0 in seen:
                continue
            seen.add(c0)
            comp_c, comp_s, todo = [c0], set(), [c0]
            while todo:
                c = todo.pop()
                for l in np.flatnonzero(ok[c]):
                    l = int(l)
                    if l in comp_s:
                        continue
                    comp_s.add(l)
                    for c2 in cs:
                        if c2 not in seen and ok[c2, l]:
                            seen.add(c2)
                            comp_c.append(c2)
                            todo.append(c2)
            if comp_s:
                out.append((j, tuple(sorted(comp_c)), tuple(sorted(comp_s))))
    return out


class _Group:
    """One group's parameters and running state (OnlineLB)."""

    def __init__(self, view: PublicView, j: int, clients: tuple, sites: tuple, z: np.ndarray, lms: np.ndarray,
                 ks: np.ndarray):
        Df = int(view.grid.fast_min)
        llm = view.llms[j]
        g = int(llm.g)
        self.j, self.clients, self.sites = int(j), tuple(clients), tuple(sites)
        self.q = float(llm.q_usd_per_h)
        r = math.inf
        for l in sites:
            for k in view.sites[l].menu:
                a = float(view.price[l, k])
                if np.isfinite(a):
                    r = min(r, g * a * float(z[k]))
        self.r = r
        b = min(float(view.beta_usd[j, l]) for l in sites)
        lbar = min(min(float(view.lam_s[j, l]) / 60.0, float(-(-int(lms[j, l]) // (60000 * Df)) * Df))
                   for l in sites)
        self.hb = b + r * lbar / 60.0
        self.kind = "unc" if view.kappa_infinite else ("fb" if not (np.isfinite(r) and r < self.q) else "cap")
        p = math.inf
        for l in sites:
            k = int(ks[l])
            if k < 0:
                continue
            p = min(p, float(view.beta_tilde_usd[j, l, k]) + g * float(view.price[l, k])
                    * view.contracts[k].prepaid_min / 60.0)
        self.p: Optional[float] = p if np.isfinite(p) else None
        self.S = np.zeros(1)            # 'cap': running sums S[nu], nu = 0..M
        self.M = 0
        self.nu = np.arange(1, dtype=np.int64)
        self.S0 = 0.0                   # 'fb' and 'unc': sum of q d Delta_f / 60
        self.S1 = 0.0                   # 'unc': sum of min{r, q d} Delta_f / 60
        self.peak = -math.inf           # running maximum of d_Gamma(f)
        self.lb = 0.0
        self.wk = 0.0

    def demand(self, d: np.ndarray) -> np.ndarray:
        """(phi,) d_Gamma(f) of one slot: the group's client rows of d (n, phi) added in client order."""
        cs = self.clients
        out = d[cs[0]].copy()
        for c in cs[1:]:
            out = out + d[c]
        return out

    def step(self, dg: np.ndarray, Df: int) -> None:
        """Adds the slot's fast slots dg (phi,) to the running sums; sets lb = LB'_Gamma(t) and wk = the group's term
        of W_k(t) (0.0 without a k* site)."""
        q, r = self.q, self.r
        if self.kind == "cap":
            fl = np.floor(dg)
            nf = (fl + ((dg - fl) * q > r)).astype(np.int64)
            M = int(nf.max())
            if M > self.M:                                  # every earlier n_f <= self.M (module docstring)
                self.S = np.concatenate([self.S, np.full(M - self.M, self.S[self.M])])
                self.M = M
                self.nu = np.arange(M + 1, dtype=np.int64)
            for i in range(len(dg)):
                n = np.minimum(nf[i], self.nu)
                c = n * r + q * np.maximum(dg[i] - n, 0.0)
                self.S = self.S + c * Df / 60.0
            self.lb = float((self.nu * self.hb + self.S).min())
        else:
            for i in range(len(dg)):
                qd = q * dg[i]
                self.S0 = self.S0 + qd * Df / 60.0
                if self.kind == "unc":
                    self.S1 = self.S1 + (r if qd > r else qd) * Df / 60.0
            self.lb = float(min(self.S0, self.hb + self.S1)) if self.kind == "unc" else float(self.S0)
        self.peak = max(self.peak, float(dg.max()))
        self.wk = 0.0 if self.p is None else float(self.p * np.ceil(self.peak - WK_TOL))


class OnlineLB:
    """LB'(t), W_k(t) and B(t) = min{W_k(t), LB'(t)} online, one slow slot at a time (module docstring).

    OnlineLB(view) fixes the groups and their parameters from the PublicView. step(obs) at slow slot t = obs.t (in
    order from 0) reads obs.demand (n, phi) and sets t, LB, Wk and B to the slot's values and appends them to
    LB_series, Wk_series and B_series; before the first step all are 0.0 (LB'(-1) = 0). report() gives
    {LB_T, Wk_T, B_T, n_groups} at the last stepped slot."""

    def __init__(self, view: PublicView):
        g = view.grid
        self.phi, self.Df, self.T = int(g.phi), int(g.fast_min), int(g.T_slow)
        self.n = len(view.client_llm)
        self.kappa_infinite = bool(view.kappa_infinite)
        z, lms, ks = zeta(view), lam_ms(view), k_star(view)
        self.groups = [_Group(view, j, cs, ss, z, lms, ks) for j, cs, ss in groups(view)]
        self.t = -1
        self.LB = self.Wk = self.B = 0.0
        self.LB_series: list[float] = []
        self.Wk_series: list[float] = []
        self.B_series: list[float] = []

    @property
    def n_groups(self) -> int:
        return len(self.groups)

    def step(self, obs) -> float:
        """B(t) at slot t = obs.t from obs.demand (a SlowObs, or anything with t and demand)."""
        return self.step_demand(int(obs.t), obs.demand)

    def step_demand(self, t: int, demand) -> float:
        """B(t) at slot t from the demand (n, phi) of its fast slots; t must follow the last stepped slot."""
        if int(t) != self.t + 1:
            raise PolicyError(f"OnlineLB: slot {t} after slot {self.t} (one step per slow slot, in order)")
        d = np.asarray(demand, dtype=np.float64)
        if d.shape != (self.n, self.phi):
            raise PolicyError(f"OnlineLB: demand of shape {d.shape}, expected {(self.n, self.phi)}")
        lb = wk = 0.0
        for gr in self.groups:
            gr.step(gr.demand(d), self.Df)
            lb += gr.lb
            if gr.p is not None:
                wk += gr.wk
        self.t = int(t)
        self.LB, self.Wk = float(lb), float(wk)
        self.B = float(min(self.Wk, self.LB))
        self.LB_series.append(self.LB)
        self.Wk_series.append(self.Wk)
        self.B_series.append(self.B)
        return self.B

    def report(self) -> dict:
        return {"LB_T": self.LB, "Wk_T": self.Wk, "B_T": self.B, "n_groups": self.n_groups}


def series(view: PublicView, demand) -> dict:
    """{'LB', 'Wk', 'B'}: (T_slow,) arrays of an OnlineLB stepped over a whole horizon's fast-slot demand (n,
    T_fast) (an instance's clients.demand), slot by slot as the engine reveals it."""
    olb = OnlineLB(view)
    d = np.asarray(demand, dtype=np.float64)
    phi = olb.phi
    for t in range(d.shape[1] // phi):
        olb.step(SimpleNamespace(t=t, demand=d[:, t * phi:(t + 1) * phi]))
    return {"LB": np.array(olb.LB_series), "Wk": np.array(olb.Wk_series), "B": np.array(olb.B_series)}


def conditions(view: PublicView) -> dict:
    """Conditions (i)-(iv) of C3 §9's 'Relation to the prototype' and the module docstring, under which OnlineLB's
    series equals run_proj.allowance('mix:0:1:1:Wk', ...)'s bit for bit: {'i': kappa_infinite false or no group with r
    >= q_j, 'ii': Delta_f divides every offered P_k, 'iii': no load time of a group's LLM at a group site in the
    half-millisecond corner, 'iv': the horizon has at least two fast slots (T_fast >= 2) or every group has fewer than
    eight clients, 'valid': all four}. Condition (iv) is numpy's, not C3 §9's: with T_fast = 1, lb.py's sum over axis 0
    of the group's (n_Gamma, 1) demand rows is a reduction over one contiguous column, which numpy sums pairwise once it
    has eight or more elements, while OnlineLB adds the rows in client order, so d_Gamma may differ in its last bits
    (numpy 2.4.4: no difference below eight rows, many at eight)."""
    Df = int(view.grid.fast_min)
    z, lms, ks = zeta(view), lam_ms(view), k_star(view)
    grs = [_Group(view, j, cs, ss, z, lms, ks) for j, cs, ss in groups(view)]
    c1 = (not view.kappa_infinite) or all(gr.r < gr.q for gr in grs)
    offered = {int(k) for l, s in enumerate(view.sites) for k in s.menu if np.isfinite(view.price[l, k])}
    c2 = all(int(view.contracts[k].prepaid_min) % Df == 0 for k in offered)
    c3 = not any(int(lms[gr.j, l]) % (60000 * Df) == 0 and 1000.0 * float(view.lam_s[gr.j, l]) > int(lms[gr.j, l])
                 for gr in grs for l in gr.sites)
    c4 = int(view.grid.T_fast) >= 2 or all(len(gr.clients) < 8 for gr in grs)
    return {"i": bool(c1), "ii": bool(c2), "iii": bool(c3), "iv": bool(c4), "valid": bool(c1 and c2 and c3 and c4)}


__all__ = ["WK_TOL", "zeta", "usable_arcs", "groups", "OnlineLB", "series", "conditions"]
