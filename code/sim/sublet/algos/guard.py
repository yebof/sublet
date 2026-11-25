"""Policy A8: an inner policy under a worst-case guard (design/q44_practical_sublet.md §3.4, §3.10).

The guard runs an online inner policy E (A7, practical Sublet, by default; A3, A6, BL1 and BL5 are
allowed) unchanged and aborts, once and for good, to a safe expert S the first time an upper bound
a-hat(t) on the platform's real cost through slot t, plus a reserve R(t) for the cost of winding down
after an abort, exceeds gamma C_S(t) + B(t) (§3.4):

  Ratchet (pure logic, §3.4): the test value of slot t, known before the platform acts,
     (T0g, default) a-hat(t) = ALG(t-1) + p_E(t) + rent_E(t) + G(t) + S(t), with the reserve R(t) (T0gBound);
     (T0)           a-hat(t) = ALG(t-1) + p_E(t) + rent_E(t) + Q(t), R(t) = 0 (sound on the core only);
     (T1)           a-hat(t) = ALG(t-1) + p_E(t), R(t) = 0     (a purchase pre-check),
  and the guard executes E's actions iff a-hat(t) + R(t) <= gamma C_S(t) + B(t). ALG(t-1) = obs.cost_so_far,
  p_E(t) the engine price of E's purchases of the slot (prepaid billed term g a_lk P_k / 60 plus n_rep beta_jl
  loading per Buy; beta_jl per Load, and for a Load on a lease that the same list buys the largest beta_jl over
  the sites of the list's earlier Buys, audit F1), rent_E(t) = sum_L g_L a_L max{0, min((t+1) Δs, death_L) - max(t Δs,
  b_L)} / 60 over the leases held after E's actions (b_L the end minute of L's billed term, death_L its death
  minute once announced), and Q(t) the slot's exact all-fallback cost sum_c q_{j_c} sum_f d_c(f) Δf / 60 (it
  bounds the slot's routing and fallback, since routing uses only arcs with delta < q; it is the 'all-fallback
  service' of the note's replays (§3.11) and at most the formula sum_c q_{j_c} D_c(t) Δs / 60 of §3.10 with the
  slot maximum D_c(t); both equal q n(t) on core exports). T0g (§3.4, §3.10) keeps T0's purchase and rent
  terms and replaces Q(t) by G(t), the cost of a greedy cheapest-first routing of the slot's demand over the
  counted replicas of leases surely alive in each fast slot (inside the guaranteed window, protected, or
  announced with a death after the fast slot), fallback for the rest, plus S(t), a bound on the slot's
  stranding charges (§5.6 of sim_spec); it is sound (ALG(t) <= a-hat(t)) under the conditions and with the
  proof in T0gBound's docstring. T0 misses the stranding charges, so in the full model m(t) under T0 can be up
  to the slot's stranding; it is sound only on the core. Allowances: constant B0, online B_on(t) = sum_j
  min{F_j(t), C^min_j} (Lemma G5) and capped B(t) = min{B0, kappa B_on(t)} (default, kappa = 10); A8P
  (ProjectedGuarded, allowance 'lb') adds B(t) = min{W_k(t), LB'(t)} of online_lb.OnlineLB (Lemma G5'). m(t) =
  max{0, ALG(t) - a-hat(t)} is booked for every executed slot (0 under T0 on exact core exports, 0 under T0g
  under T0gBound's conditions C1-C3, up to the routing LP's round-off).
  SafeExpert (§3.10): S = T11_{gamma'}(FB, R) ('fb+pd', default), R alone ('pd') or FB alone ('fb').
  FB is all-fallback with the exact engine cost per slot; R is a2.A2Planner as specified (full menu,
  no contract rule, d = mK + 1, layering as built, r-bar = theory by default); the C3-T11 doubling
  combiner (a5.DoublingCombiner, gamma' = 1 + 1/sqrt 2) runs FB in its F slot. Before the abort R
  is a shadow: it buys nothing and receives no purchase result, so it is the eager, lender- and
  platform-independent R of §3.2. C_S is the combiner's accounted total (R's or FB's curve for
  'pd' and 'fb'); S's live set L_S(t) is the followed expert's live columns (none while it follows
  FB); P_S(t) its purchases at t; W_S(t) = sum of C_F over L_S(t) minus P_S(t).
  Guarded (§3.10, policy A8): mode E executes E's actions while a-hat(t) + R(t) <= gamma C_S(t) + B(t); at
  the first slot t_a where it fails, E's actions are discarded and the platform follows S as in Lemma G1(b):
  the inner's leases wind down by the rule `wind_down` (below); one Buy(l, k, j, 1) per column of L_S(t_a);
  from then on S's purchases (R's opened columns while S follows R, the combiner's copies at a switch to R),
  each released by A2's rule (first slot t >= max(s + L_k, ceil((t0 Δs + P_k) / Δs))); pre-check drops and
  engine refusals of S's purchases go to the planner as in A2 (§6.5), so C_S from t_a on is the curve of the
  trajectory executed. There is no return to mode E.

Wind-down of the inner's leases (design/q44_practical_sublet.md §8.11: close
the full-model gap by counting the wind-down cost of an abort in the test). Diagnosis of the 170 certificate
failures of the study (§8.9; sublet/experiments/q44_winddown.py reruns and decomposes them): with the rule
'keep' every failure had S following FB at and after t_a with no drop, refusal or switch, and its S-mode excess
is, by ledger component, the stranding of the load on the inner's leases when they die or are released (on
the study's instances only mu^fb > 0) plus their rent from the billed end to the first slot boundary at or
after it, minus their routing saving while they serve; there is no purchase or loading after t_a. Rules
(parameter wind_down):
  'keep' (the rule of the earlier build; wind_down 'auto' under T0 and T1): at t_a every held lease whose
     billed term has ended is released, the others keep serving and are released at the first slot at or
     after their billed end.
  'release': every held lease is released at t_a.
  'adaptive' (wind_down 'auto' under T0g, the default): at every slot u >= t_a at which inner leases H_u are
     still held, if T0gBound is in its bound form, S follows FB at u, buys nothing and holds no lease of its
     own, the guard evaluates the lists [Release(L) : L in H_u \\ K] for K1 (keep the leases of H_u without
     rent in slot u), K0 (keep none) and K2 (keep all) by beta(K) = G_K(u) + S_K(u) + rent_K(u) - Q(u) +
     R_K(u) (T0gBound.evaluate and slot_terms) and executes the least, K1, then K0, then K2 on a tie (WD_TIE);
     otherwise it releases H_u at once. The budget of slot u + 1 is R_{K*}(u). 'adaptive' keeps a lease
     where serving at delta_cl saves more than its rent and stranding bounds add; 'release' gives the same
     bound with the same reserve.
Reserve (T0g; T0gBound._reserve): R(t) = sum_c kappa'_{j_c} UB_c(f_l), kappa'_j = mu^kv_j + mu^fl_j [mu^fl_j >
0 and T_dr_j > 0] + mu^fb_j + pi_j W_f, with f_l the last fast slot of t and UB_c(f_l) T0gBound's upper bound
on client c's served load there for A_E(t) (W^hi, and the LB of the clients whose arcs lie within c's): the
stranding of the next slot's first fast slot if every replica were gone there. It is computed at slot t
before the platform acts, from the public view and the observations; R = 0 on core exports (mu = pi = 0).

Theorem W (the guard's bound in the full model; PROVEN for the engine as implemented, under T0gBound's
conditions C1-C3 and up to the tolerances below; the argument uses T0gBound's soundness proof, written in its
docstring). Both were audited in design/theory/audit_guard.md, section "Audit of the full-model guard" (findings
F1-F5; the auditor's scripts are code/sim/audit/, outputs code/sim/out/audit_fm/). The PROVEN labels of T0gBound
and of (a) and (b) hold without provisos since F1 (slot_terms prices a Load on a lease bought in the same list)
and F2 (the inner policy receives a private copy of its observation, inner_obs) are fixed; F5 (G over W^C) is a
possible refinement, not applied. Test T0g with wind_down 'adaptive' or 'release'; any lender of the engine (any
schedule, oblivious or adaptive; violations 'absorb' or 'reclaim'; on_unavailable 'sell', or 'refuse' with the
rule passed to A8 as drivers/run.py does); any inner policy that does not use on_fast (it may write to its
observation); any gamma > 0 and allowance; pathwise:
  (a) without an abort, ALG(T) <= gamma C_S(T) + B(T) - R(T-1) <= gamma C_S(T) + B(T);
  (b) with an abort at t_a after which S follows FB at every slot,
        ALG(T) <= C_S(T) + (gamma - 1) C_S(t_a - 1) + B(t_a - 1) - [R(t_a - 1) - Phi(t_a)],
      with the wind-down cost Phi(t_a) = sum_{u >= t_a} (ALG(u) - ALG(u-1) - Q(u)) <= R(t_a - 1): Theorem G2(b)'s
      bound with W_S(t_a) = 0 and m = 0.
  (c) CONJECTURE (per-run certificate, q44_study.certificate): if S follows R at some slot >= t_a, the
      bound of (b) with W_S(t_a) holds up to R's execution above its accounting (load times of the copies,
      layering, pre-check drops; §3.8 item 5 of the note), which nothing here bounds.
Proof. (1) E mode. A_E(t) is executed only if a-hat(t) + R(t) <= gamma C_S(t) + B(t), and then ALG(t) <=
a-hat(t) (T0gBound, C1-C3); so ALG(t) + R(t) <= gamma C_S(t) + B(t) at every executed slot, and (a) is the
case t = T - 1 (R >= 0). (2) FB slots. While S follows FB it buys nothing, and c_S(u) = Q(u): the combiner
adds FB's increment while following FB and at a switch to FB, whose state cost is 0. A slot whose platform
holds no replica has routing 0 and fallback Q(u); with replicas, routing + fallback <= Q(u), since routing
uses only arcs with delta < q. (3) Wind-down. Let Phi(u) = sum_{v >= u} (cost(v) - Q(v)) and Bud(u) the
budget of slot u: Bud(t_a) = R(t_a - 1) (0 for t_a = 0), Bud(u + 1) = R_{K*}(u) after an adaptive slot u with
K* not empty. Claim: Phi(u) <= Bud(u) at every slot u >= t_a of the wind-down. (i) A slot u at which no inner
lease is held, or all of H_u are released (K0, by either rule): S holds no replica, so from the first fast
slot f0 = u phi on every replica is gone (a lease that the lender ends at u Δs, an announced death at the slot
start or a violation victim under 'reclaim', is gone from f0 too); routing is 0, fallback Q(v), rent 0, and
stranding occurs only at f0 (at f > f0 there is no served load before): rule T11 gives m_c(f0) = sum_l (dh_c
z_cl(f0 - 1) - 0)^+ = dh_c zbar_c(f0 - 1) <= X_c(f0 - 1) and w_c(f0) <= the same, with the factors of mu^fl
and pi at most 1 and W_f for any lead time h >= 0. So Phi(u) <= sum_c kappa'_c X_c(f0 - 1) <= sum_c kappa'_c
UB_c(f0 - 1) = Bud(u), since UB_c(f0 - 1) >= X_c(f0 - 1) for the list executed at u - 1 (A_E(t_a - 1) at u =
t_a, the adaptive list K* after), by T0gBound's proof (c). (ii) An adaptive slot u with K* not empty: S buys
nothing, so the slot's cost is its rent, routing, fallback and stranding, at most rent_K*(u) + G_K*(u) +
S_K*(u) by slot_terms and T0gBound's proof (a)-(c) for the executed list (C1-C3 hold: no on_fast, no Buy, ends
only at slot starts), and Phi(u + 1) <= Bud(u + 1) = R_K*(u) by (i) or (ii) at u + 1, whose UB at the last
fast slot of u is the one R_K*(u) uses. So Phi(u) <= beta(K*) <= beta(K0) <= Bud(u) (the middle inequality
up to WD_TIE): K0's list leaves no replica, so G_K0 = Q(u), rent 0, R_K0 = 0, and S_K0(u) is the f0 term
sum_c [(mu^kv + mu^fl D) e_c + (mu^fb + pi W_f D) e_c] with e_c <= UB_c(f0 - 1) and LB = 0 (0 at later fast
slots), computed from the state from which the budget was computed. The induction is backward: with u* the
first wind-down slot of case (i), or T (Phi(T) = 0), (i) gives the claim at u*, and (ii) carries it from u + 1
to u for u = u* - 1, ..., t_a (only the chain of budgets runs forward). Case (i) includes a slot at which the
kept leases have all died at the slot start (an announcement with H = 0, a death at the boundary, a violation
victim). (4) ALG(T) = ALG(t_a - 1) + sum_{u >= t_a} Q(u) + Phi(t_a) <= [gamma C_S(t_a - 1) + B(t_a - 1) -
R(t_a - 1)] + [C_S(T) - C_S(t_a - 1)] + Phi(t_a), by (1) at t_a - 1 and (2); with (3), Phi(t_a) <= R(t_a -
1). []
Tolerances: (a) and (b) hold up to the routing LP's tolerance (the engine solves it with HiGHS and rescales its
round-off onto the rows), GUARD_TOL max(1, |gamma C_S(t) + B(t)|) per executed slot (Ratchet.step accepts a
test value above the right-hand side by that much), WD_TIE max(1, |Q(u)|) per adaptive wind-down slot (a
later candidate replaces an earlier one only if cheaper by more than that, so beta(K*) <= beta(K0) + WD_TIE
max(1, |Q(u)|)), the float differences between G_K0(u) and Q(u) (summation order) and between S_K0(u) and Bud(u)
(association: T0gBound.evaluate against T0gBound._reserve), and the rounding of the float sums in each comparison.
The bound needs the reserve only for the stranding of one fast slot: rent never accrues after t_a under
'release', and under 'adaptive' only where beta says that keeping pays. Keeping the inner's leases to their
billed end ('keep') would need a reserve for the stranding of every fast slot up to that end, with demand not
yet observed, and for their rent. The certificate holds on the study's failing cells rerun with the default
(q44_winddown.py; tests/test_guard.py::test_reserve_failing_cells).

Random streams: E and S each receive a deep copy of the policy generator at reset, so that E draws
exactly as it would alone and R exactly as A2 alone (§3.10).

Guarantees (§3.5, §3.6): on the ORML core (from_core exports, under a lender that sells and ends no lease inside
its guaranteed window [s, s + D_k)) and for every inner policy that buys with admission 1 and never drains (the
condition of T0gBound's 'On core exports'), Theorem G2 gives ALG(T) <= gamma C_S(T) + B(T) + m(T) without an
abort and ALG(T) <= C_S(T) + (gamma - 1) C_S(t_a - 1) + W_S(t_a) + B(t_a - 1) + m(t_a - 1) with one; with T0 or
T0g and B(t) <= kappa B_on(t), Corollary G3 gives a ratio to OPT_eager (R = 0 there, so T0g's test is C3 §9's, at
most T0's value). Both hold for A8 (PROVEN; audited in design/theory/audit_guard.md, 'Audit addendum (P6)') up to
WD_TIE sum_u max(1, Q(u)) over the adaptive wind-down slots u, a tolerance that G2 as stated does not carry: in
mode E A8 is C3 §9's guard, and its mode S (the wind-down above, then S's copies and purchases, each released by
A2's rule, which is t0 + D_k on core exports) meets G2(b)'s bound on the cost after t_a by C3 §9, "A8's mode S on
core exports". There an adaptive slot (S on FB with no lease of its own, T0g in bound form) costs at most
Q(u) + WD_TIE max(1, Q(u)), since beta(K0) = 0; at every other slot the inner leases are released ('release' at
t_a, 'adaptive' through K0) or kept to s + D_k ('keep'), as the guard's rule (3) does, and S's leases are those
of Lemma G1(b). Without the cap or under T1 only the additive envelope holds (Proposition G6). In the full model
Theorem W holds under T0g (cases (a) and (b)); case (c) and the tests T0 and T1 are measured by the per-run
certificate (§3.8 item 5, §3.10).

The guard reads only the PublicView, the observations and the driver inputs N_bound and on_unavailable. The
inner policy receives a private copy of each slow-slot observation (inner_obs; audit F2): the guard computes
every term of its test (SafeExpert.step, slot_terms, T0gBound, ALG(t-1) = obs.cost_so_far) from the engine's
observation, which the inner policy never holds, so writes of the inner policy to its observation cannot change
the test. The PublicView is protected already (frozen records, read-only arrays); the fast-slot observation is
passed through, since the guard does not read it. This module imports numpy, the standard library,
sublet.types, sublet.timing, sublet.policies.base and modules of sublet.algos and sublet.baselines (the inner
policies lazily, never the registry).
"""
from __future__ import annotations

import copy
import dataclasses
import math
from collections import Counter
from typing import Optional

import numpy as np

from ..baselines.common import k_star
from ..policies.base import Policy
from ..timing import warm_fast
from ..types import INF, ActionResult, Buy, Drain, FastObs, Load, PublicView, Release, SetAdmission, SlowObs, Unload
from .a2 import A2Planner
from .a5 import G2, DoublingCombiner
from .common import LeaseBook, PolicyError, lam_ms, policy_streams, resolve_params
from .online_lb import OnlineLB

INNER_IDS = ("A7", "A3", "A6", "BL1", "BL5")     # registry.A8_INNER_IDS (§6.1 item 5)
SAFE_MODES = ("fb+pd", "pd", "fb")
TESTS = ("T0", "T1", "T0g")
WIND_DOWNS = ("auto", "adaptive", "release", "keep")   # Guarded's rule for the inner's leases after an abort
SALE_RULES = (None, "sell", "refuse")                  # the lender's on_unavailable, as the driver passes it
GUARD_TOL = 1e-12          # a-hat(t) + R(t) > gamma C_S(t) + B(t) + GUARD_TOL max(1, |rhs|) aborts
WD_TIE = 1e-12             # adaptive wind-down: a later candidate must be cheaper by more than WD_TIE max(1, Q)
TAG_COPY = "a8:copy"       # a copy of S's live set (abort, or a switch of the combiner to R)
TAG_BUY = "a8:s"           # a purchase of S while it follows R


def _is_num(v) -> bool:
    return isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, (bool, np.bool_))


def _inner_class(inner: str):
    """The policy class of an inner id of A8, imported on first use."""
    if inner == "A7":
        from .a7 import PracticalSublet
        return PracticalSublet
    if inner == "A3":
        from .a3 import A3
        return A3
    if inner == "A6":
        from .a6 import A6
        return A6
    if inner == "BL1":
        from ..baselines.greedy import GreedyLease
        return GreedyLease
    if inner == "BL5":
        from ..baselines.retrorenting import RetroRentingStyle
        return RetroRentingStyle
    raise PolicyError(f"A8: inner must be one of {list(INNER_IDS)}, got {inner!r}")


# ---------------------------------------------------------------- prices and allowances (§3.4, §3.10)
def fallback_by_client(view: PublicView, demand: np.ndarray) -> np.ndarray:
    """(n,) exact all-fallback cost of one slow slot per client: q_{j_c} sum_f d_c(f) Δf / 60 over the
    fast slots of `demand` (n, phi), the engine's fallback charge with nothing served."""
    q = np.array([x.q_usd_per_h for x in view.llms], dtype=np.float64)
    d = np.asarray(demand, dtype=np.float64)
    cl = np.asarray(view.client_llm, dtype=np.int64)
    if d.size == 0:
        return np.zeros(len(cl))
    return q[cl] * d.sum(axis=1) * view.grid.fast_min / 60.0


def b0_auto(view: PublicView) -> float:
    """B0 = 'auto' (§3.10): sum over clients c of min over the sites l with a revocable contract
    (k*(l) of the baselines, §15.1) and delta_cl < INF of beta~_{j_c l k*(l)} + g_{j_c} a_{l k*(l)}
    P_{k*(l)} / 60, one fresh replica per client at its cheapest such site (0 for a client without one)."""
    ks = k_star(view)
    dl = np.asarray(view.client_delta_usd_per_h, dtype=np.float64)
    cl = np.asarray(view.client_llm, dtype=np.int64)
    tot = 0.0
    for c in range(len(cl)):
        j = int(cl[c])
        g = view.llms[j].g
        best = INF
        for l in range(len(view.sites)):
            k = int(ks[l])
            if k < 0 or not np.isfinite(dl[c, l]):
                continue
            v = float(view.beta_tilde_usd[j, l, k]) + g * float(view.price[l, k]) * view.contracts[k].prepaid_min / 60.0
            best = min(best, v)
        if np.isfinite(best):
            tot += best
    return float(tot)


def c_min(view: PublicView) -> np.ndarray:
    """(J,) C^min_j of B_on (§3.10): the engine's purchase charge of one replica of LLM j, beta_jl +
    g_j a_lk P_k / 60, minimized over the sites l that some client of j can use (delta finite and below
    q_j) and the contracts offered there, protected ones included; INF if no site is usable."""
    J = len(view.llms)
    q = np.array([x.q_usd_per_h for x in view.llms], dtype=np.float64)
    cl = np.asarray(view.client_llm, dtype=np.int64)
    dl = np.asarray(view.client_delta_usd_per_h, dtype=np.float64)
    with np.errstate(invalid="ignore"):
        arc = np.isfinite(dl) & (dl < q[cl][:, None])
    out = np.full(J, INF)
    for j in range(J):
        rows = arc[cl == j]
        if rows.size == 0:
            continue
        for l in np.flatnonzero(rows.any(axis=0)):
            l = int(l)
            for k in view.sites[l].menu:
                a = float(view.price[l, k])
                if not np.isfinite(a):
                    continue
                v = float(view.beta_usd[j, l]) + view.llms[j].g * a * view.contracts[k].prepaid_min / 60.0
                out[j] = min(out[j], v)
    return out


def buy_price(view: PublicView, b: Buy) -> float:
    """Engine charge of a Buy at its slot (§3.10): prepaid g n a_lk P_k / 60 plus n beta_jl loading."""
    n = int(b.n_replicas)
    gpus = view.llms[b.llm].g * n
    P = int(view.contracts[b.contract].prepaid_min)
    return gpus * float(view.price[b.site, b.contract]) * P / 60.0 + n * float(view.beta_usd[b.llm, b.site])


def slot_terms(view: PublicView, obs: SlowObs, actions) -> tuple[float, float]:
    """(p_E(t), rent_E(t)) of an action list at slot t = obs.t (§3.10): the engine price of its Buys
    and Loads, and the rent bound over slot t of the leases held after the actions (obs.leases minus
    the Released ones, plus the Buys), each over [max(t Δs, b_L), min((t+1) Δs, death_L)) at g_L a_L
    per hour, with b_L the end minute of the billed term and death_L the death minute once announced.

    A Load on a lease of obs.leases costs beta_jl at the lease's site. A Load on any other lease is priced at the
    largest beta_jl over the sites of the Buys that precede it in the list (audit F1, design/theory/audit_guard.md):
    the engine accepts such a Load only on a lease that an earlier Buy of the same list bought (obs.leases holds
    every lease alive at the slot's first fast slot, and the engine raises ActionError for a lease that does not
    exist yet or is not alive), for instance after an Unload of that Buy's replica, and charges beta_jl at its
    site. The price is exact when those sites have one beta_jl, in particular with one earlier Buy; the exact Buy
    could be told only by predicting the engine's lease ids and the lender's acceptance of every earlier Buy (not
    known under on_unavailable 'refuse'), which no inner policy of INNER_IDS needs, since none issues a Load. With
    no earlier Buy (the engine raises) the largest beta_jl over all sites. Refused Buys and Loads are priced too
    (an upper bound). The tests T0, T0g and T1 all take p_E(t) from here."""
    t = int(obs.t)
    slow = view.grid.slow_min
    t0m, t1m = t * slow, (t + 1) * slow
    released = {int(a.lease_id) for a in actions if isinstance(a, Release)}
    p = rent = 0.0
    buy_sites: list[int] = []                   # sites of the list's Buys so far
    for a in actions:
        if isinstance(a, Buy):
            p += buy_price(view, a)
            b = t0m + int(view.contracts[a.contract].prepaid_min)
            gpus = view.llms[a.llm].g * int(a.n_replicas)
            rent += gpus * float(view.price[a.site, a.contract]) * max(0, t1m - max(t0m, b)) / 60.0
            buy_sites.append(int(a.site))
        elif isinstance(a, Load):
            L = obs.leases.get(a.lease_id)
            if L is not None:
                p += float(view.beta_usd[a.llm, L.site])
            else:                               # a lease bought earlier in this list (audit F1)
                sites = buy_sites if buy_sites else range(len(view.sites))
                p += max(float(view.beta_usd[a.llm, l]) for l in sites)
    for lid, L in obs.leases.items():
        if int(lid) in released:
            continue
        hi = t1m if L.death_min is None else min(t1m, int(L.death_min))
        span = hi - max(t0m, int(L.prepaid_end_min))
        if span > 0:
            rent += L.gpus * float(view.price[L.site, L.contract]) * span / 60.0
    return float(p), float(rent)


# ---------------------------------------------------------------- T0g's service term (§3.4, §3.10)
class T0gBound:
    """Service term of test T0g in the full model (design/q44_practical_sublet.md §3.4, §3.10), computed at
    slot t from the observation and E's action list A_E(t), before the platform acts:

        service(t) = sum over the fast slots f of t of  G(f) Δf / 60 + S(f).

    Replicas. For every replica after A_E(t) (those of obs.replicas on leases not released and not unloaded
    at t, and the new ones of A_E(t)'s Buys and Loads, except the replica of a Load on a lease that a later
    Release of the list ends at the slot start) and every fast slot f of t: lo(f) <= its admitting
    capacity in the engine (§5.1 step 5(b)-(c) of sim_spec) <= hi(f). Both are its admission in force at f
    (ReplicaView.admission from t phi, then A_E(t)'s SetAdmission and Drain in list order and a pending drain
    from drain_min) if it is warm at f (warm_fast; rule T8 for a new replica) and its lease alive in f (rule
    T6 with the announced death minute; an unannounced lease is alive in every fast slot of t, condition C3),
    else 0. A new replica is counted (lo = hi) only if its Buy surely succeeds (condition C2), else lo = 0;
    when an action makes the admission unknown, lo = 0 and hi = 1. Per LLM j and site l: W^B_jl(f) = sum of
    lo(f) over the replicas on leases *surely alive in f* in C3 §9's sense (protected; or inside the
    guaranteed window, (f+1) Δf <= start + D_k with D_k = tau_k Δs + H_k; or announced with death minute >=
    (f+1) Δf), the leases bought at t included; W^C_jl(f) = sum of lo(f) over every replica; W^hi_jl(f) = sum
    of hi(f), whose support P_j(f) contains every site at which LLM j can admit load at f.

    G(f): per LLM, the greedy cheapest-first assignment of the clients' demand d_c(f) over the arcs with
    delta_cl < q_j (finite) and W^B_jl(f) > 0: arcs in increasing delta (ties by client, then site), each
    taking min{residual demand, residual capacity}; with kappa_infinite each client goes wholly to its
    cheapest such site. Cost (per hour) sum delta x + q_j (unserved demand). When the cheapest-site
    assignment fits the capacities the greedy is that assignment (computed directly). W^B is more conservative
    than C3 needs: under C3 G could route over W^C (audit F5, a possible refinement, not applied; it would
    change tests/test_guard.py::test_t0g_equals_core_t0g, which pins W^B to check_guard.py's core T0g).

    S(f) = sum_c [(mu_kv_j + mu_fl_j D_j(f)) e_c(f) + (mu_fb_j + pi_j W_f D_j(f)) (e_c(f) - LB_c(f))^+], j = j_c,
    the mu_fl term only where mu_fl_j > 0 and T_dr_j > 0, with
      dh_c(f) = min{d_c(f-1), d_c(f)} (d(-1) = 0; for the first fast slot of t, d(f-1) is the last fast slot of
        the previous slot's observation, and every quantity at f-1 comes from the previous slot's bound);
      e_c(f) = min{dh_c(f), UB_c(f-1)};
      UB_c(f-1) = min{d_c(f-1), sum over c's arcs l of W^hi_jl(f-1) - sum of LB_c'(f-1) over the other clients
        c' of j whose arcs to sites of P_j(f-1) all go to sites to which c has an arc} (with kappa_infinite:
        d_c(f-1) if c has an arc to a site of P_j(f-1), else 0);
      LB_c(f) = 0 if d_c(f) = 0; else d_c(f) if (i) kappa_infinite and c has an arc to a site with W^C_jl(f) >
        0, or (ii) W^C_j(f) = W^hi_j(f) (capacity known) and the cheapest-site assignment over the sites with
        W^C > 0 fits W^C; else (iii) min{d_c(f), (sum over c's arcs of W^C_jl(f) - demand at f of c's
        competitors)^+}, a competitor being another client c' of j with d_c'(f) > 0 and an arc to a site l
        of P_j(f) to which c has an arc with delta_{c'l} <= delta_{cl};
      D_j(f) = 1 iff some replica of j has hi(f-1) > lo(f) (for f = t phi: iff P_j(t phi - 1) is not empty).

    Conditions. (C1) the inner policy does not use on_fast (wants_fast False). (C2) every Buy counted is
    accepted. The engine refuses a Buy for capacity, replicated here as in sim_spec §6.4 (the GPUs held at
    the site after the Releases and the Buys accepted earlier in the list), or as 'unavailable' under
    on_unavailable = 'refuse' (t in R_l, sim_spec §6.4). The lender's option is not in the PublicView; it is
    the constructor's on_unavailable, which drivers/run.py passes from the run's lender model. Under 'refuse' the
    bound counts a Buy from slot 0 on only at a protected site (R_l is empty there in every mode) or, under I2,
    at a site not announced at t (site_announced is the realized R_l at t); every other Buy is uncertain and
    enters hi only (the cautious route). Under 'sell' every Buy that passes the capacity check is counted. With
    the option unknown (None, a direct construction) the bound presumes 'sell' until E's first 'unavailable'
    refusal and is cautious from then on; then C2 can fail at the slot of that first refusal, where ALG(t) >
    a-hat(t) is possible (tests/test_guard.py::test_t0g_refuse_first_refusal). (C3) inside slow slot t, after
    the observation, no lease of the platform ends except at its announced death minute or by the platform's
    own actions: the
    lender announces (death minute t Δs + H_k), and under violations = 'reclaim' ends leases, only at the
    start of a slow slot before the observation (sim_spec §5.1 steps 1-2, engine._slow_step). So an
    unannounced lease of obs.leases is alive in every fast slot of t, under every schedule and under
    violations 'absorb' and 'reclaim' alike.

    Soundness (PROVEN under C1-C3, up to the routing LP's tolerance; C2 holds under on_unavailable = 'sell', and
    under 'refuse' when the option is passed. Audited in design/theory/audit_guard.md, "Audit of the full-model
    guard"; the label holds without provisos since its finding F1, a Load on a lease bought in the same list, is
    priced in slot_terms, and F2, an inner policy that writes to its observation, is closed by inner_obs.)
    Let A_E(t) be executed; ALG(t) - ALG(t-1) is the slot's purchases and loading, rent, routing, fallback and
    stranding.
    (a) Purchases and loading are charged only for accepted Buys and Loads, at the prices that p_E(t) adds
        for every Buy and Load of A_E(t) (slot_terms); the rent is at most rent_E(t) (T0's terms). A Load on a
        lease outside obs.leases is accepted only on a lease that an earlier Buy of the list bought, so its
        charge beta_jl is at most the largest beta_jl over the sites of the earlier Buys, which slot_terms adds.
    (b) Routing + fallback of f is the engine's optimum of sum (delta - q) x + sum q d over x >= 0 with client
        rows <= d(f), site rows <= W(f) (the admitting capacity) and arcs with delta < q (§5.5; with
        kappa_infinite each client at its cheapest admitting site). Under C1-C3 every counted replica is warm,
        alive and admits at least lo(f) at f, so W^B(f) <= W^C(f) <= W(f) <= W^hi(f). The greedy assignment is
        feasible for the engine's problem, so G(f) Δf / 60 is at least the engine's routing + fallback of f.
    (c) Stranding of f (§5.6 of sim_spec). With X_c(f) = d_c(f) zbar_c(f) the load of c served at f:
        dh zbar_c(f-1) <= min{dh, X_c(f-1)} (if d(f) >= d(f-1) it is X_c(f-1) <= d(f-1) = dh, else d(f) X_c(f-1)
        / d(f-1)), so m_c(f) = sum_l (dh z_cl(f-1) - d z_cl(f))^+ <= dh zbar_c(f-1) <= e_c(f) once X_c(f-1) <=
        UB_c(f-1), and w_c(f) = (dh zbar_c(f-1) - X_c(f))^+ <= (e_c(f) - LB_c(f))^+ once X_c(f) >= LB_c(f). The
        factors of mu_fl and pi are at most 1 and W_f, and 0 when no replica of j loses capacity at f (h_j(f) =
        inf); a drop of a replica at f needs cap(f) < cap(f-1), impossible if hi(f-1) <= lo(f). Every optimal
        routing of a fast slot satisfies the bounds on X: an admitting site of c (W_l > 0) on which c could
        place one more unit is saturated whenever c is not fully served (that unit lowers the objective by
        q - delta > 0), and a client c' with x_{c'l} > 0 there has delta_{c'l} <= delta_{cl} (moving a unit at
        l from c' to c changes the objective by delta_{cl} - delta_{c'l} >= 0). Hence, if X_c(f) < d_c(f), the
        capacity of c's arcs is filled by c and its competitors: sum W^C <= sum W <= X_c(f) + their demand,
        which is (iii); (i) is the kappa_infinite rule; (ii) if the cheapest-site assignment fits, every unit
        of every client attains its least cost per unit, so an optimal solution must serve every client with
        an admitting arc fully. For UB: the capacity of c's arcs at f-1 also carries the load X_c'(f-1) >=
        LB_c'(f-1) of every client c' that has no admitting arc outside c's arcs. So the slot's stranding is at
        most sum_f S(f).
    Summing (a)-(c), ALG(t) <= a-hat(t). The engine solves the routing LP with HiGHS and rescales its
    round-off, so the inequality holds up to that tolerance.

    Online checks of C2 and C3 (at the next slot, from obs.results and obs.ended): a counted Buy refused as
    'unavailable' starts the cautious counting of C2 (`cautious_since`); a counted Buy or Load refused for
    another reason, or a counted lease that ended before the end of the last fast slot for which it was
    counted, switches T0g to its robust form for the rest of the run (`robust_since`):
        service(t) = Q(t) + sum_f sum_c dh_c(f) a_c [mu_kv_j + mu_fl_j + mu_fb_j + pi_j W_f],
    a_c = 1 iff c has an arc with delta < q, which needs none of C1-C3 (Q(t) bounds routing and fallback,
    m_c, w_c <= dh, and zbar_c = 0 without an arc; the purchase term is slot_terms', with a Load on a lease of
    the same list priced as in (a)). The robust form is also used at every slot if C1 fails, and at a slot whose
    action list names a lease or replica that obs does not contain (an object bought or loaded in the same list).
    A slot whose check fails at the next slot is booked in m(t).

    Reserve. With UB_c(f_l) the bound above for the slot's last fast slot f_l (W^hi at f_l, the LB at f_l of the
    clients whose arcs at sites of P_j(f_l) all lie within c's; with kappa_infinite d_c(f_l) if c has an arc to a
    site of P_j(f_l)), R(t) = sum_c kappa'_{j_c} UB_c(f_l), kappa'_j = mu^kv_j + mu^fl_j (where mu^fl_j > 0 and
    T_dr_j > 0) + mu^fb_j + pi_j W_f, bounds the stranding of the first fast slot of slot t + 1 for every list
    executed there that leaves no replica serving: its moved and lost loads are at most dh_c zbar_c(f_l) <=
    X_c(f_l) <= UB_c(f_l) (step (c)), whatever the lead time. In the robust form UB_c = d_c(f_l) a_c. The guard
    adds R(t) to its test (module docstring, Theorem W). evaluate() computes G, S and R for any list without
    changing the state, so that the guard can evaluate E's list (committed only if executed) and the candidate
    lists of its adaptive wind-down; service() is begin + evaluate + record + commit.

    On core exports (from_core): mu = pi = 0, so S = 0 and R = 0; kappa_infinite, lambda = 0, Δf = Δs. With admission 1
    (every inner policy of INNER_IDS buys with admission 1 and never drains) G(t) = sum over the requests e
    of t of min{q, min delta_{e l} over the counted leases of LLM j_e}: check_guard.py's core T0g (the held
    leases inside their prepaid window and the leases bought at t) plus the held leases past their window
    that are announced and alive through the slot, which C3 §9's minimal set leaves out. The two are equal
    whenever no such lease is held (always under the eager and the C3-T4 adaptive lenders, whose
    announcements come at s + tau, and without announcements), and T0g's a-hat is at most T0's at every
    slot (G(t) <= Q(t), S = 0)."""

    def __init__(self, view: PublicView, robust: bool = False, on_unavailable: Optional[str] = None):
        if on_unavailable not in SALE_RULES:
            raise PolicyError(f"T0gBound: on_unavailable must be one of {SALE_RULES}, got {on_unavailable!r}")
        g = view.grid
        self.Ds, self.Df, self.phi = int(g.slow_min), int(g.fast_min), int(g.phi)
        self.J, self.m = len(view.llms), len(view.sites)
        self.q = np.array([x.q_usd_per_h for x in view.llms], dtype=np.float64)
        self.g = np.array([x.g for x in view.llms], dtype=np.int64)
        self.cl = np.asarray(view.client_llm, dtype=np.int64)
        self.n = len(self.cl)
        dl = np.asarray(view.client_delta_usd_per_h, dtype=np.float64)
        with np.errstate(invalid="ignore"):
            self.ok = np.isfinite(dl) & (dl < self.q[self.cl][:, None]) if self.n else np.zeros((0, self.m), bool)
        self.delta = np.where(self.ok, dl, np.inf) if self.n else np.zeros((0, self.m))
        self.any_arc = self.ok.any(axis=1) if self.n else np.zeros(0, bool)
        self.kinf = bool(view.kappa_infinite)
        self.clients_of = [np.flatnonzero(self.cl == j) for j in range(self.J)]
        self.arcs = []                       # per LLM: [(client, site, delta)] in increasing (delta, client, site)
        for j in range(self.J):
            cs = self.clients_of[j]
            ci, si = np.nonzero(self.ok[cs])
            dv = self.delta[cs[ci], si]
            o = np.lexsort((si, ci, dv))
            self.arcs.append(list(zip(cs[ci[o]].tolist(), si[o].tolist(), dv[o].tolist())))
        # competitors: comp[j][c, c', l] iff c' != c, both have an arc to l and delta_{c'l} <= delta_{cl}
        self.comp = []
        for j in range(self.J):
            cs = self.clients_of[j]
            ok, dl_j = self.ok[cs], self.delta[cs]
            cp = ok[:, None, :] & ok[None, :, :] & (dl_j[None, :, :] <= dl_j[:, None, :])
            cp[np.arange(len(cs)), np.arange(len(cs)), :] = False
            self.comp.append(cp)
        st = view.stranding
        self.mu_kv = np.asarray(st.mu_kv_usd, dtype=np.float64)
        self.mu_fb = np.asarray(st.mu_fb_usd, dtype=np.float64)
        Tdr = np.array([x.T_dr_s for x in view.llms], dtype=np.float64)
        mu_fl = np.asarray(st.mu_fl_usd, dtype=np.float64)
        self.mu_fl = np.where((mu_fl > 0) & (Tdr > 0), mu_fl, 0.0)
        self.pi_W = np.asarray(st.pi_usd_per_min, dtype=np.float64) * float(st.W_f_min)
        self.has_strand = bool(np.any(self.mu_kv > 0) or np.any(self.mu_fl > 0) or np.any(self.mu_fb > 0)
                               or np.any(self.pi_W > 0))
        # kappa'_c of the reserve: the largest stranding charge per unit of client c's load that leaves its
        # replicas at once (factors 1 of mu_fl and W_f of pi, rule T11 at lead time h = 0)
        self.kap = (self.mu_kv + self.mu_fl + self.mu_fb + self.pi_W)[self.cl] if self.n else np.zeros(0)
        self.lam = lam_ms(view)
        self.Dk = [c.D_min(self.Ds) for c in view.contracts]          # None for protected contracts
        self.prot_site = [s.kind == "protected" for s in view.sites]
        self.cap_site = [float(s.capacity_gpus) for s in view.sites]
        self.I2 = view.information == "I2"
        self.robust_all = bool(robust)                                 # C1 fails: robust form at every slot
        self.robust_since: Optional[int] = None
        # C2: under on_unavailable 'refuse' every Buy that the lender could refuse is uncertain from slot 0;
        # with the sale rule unknown (None) the bound presumes 'sell' until E's first 'unavailable' refusal
        self.sales = on_unavailable
        self.cautious_since: Optional[int] = 0 if on_unavailable == "refuse" else None
        self.prev_d = np.zeros(self.n)
        self.prev_W = np.zeros((self.J, self.m))                      # W^hi of the previous slot's last fast slot
        self.prev_lb = np.zeros(self.n)                                # LB_c of that fast slot
        self.counted_until: dict[int, int] = {}                        # lease id -> minute counted alive through
        self.counted_acts: dict[int, object] = {}                      # action index -> counted Buy or Load
        self.events: list[dict] = []
        self.slots: list[int] = []
        self.G: list[float] = []
        self.S: list[float] = []
        self.Q: list[float] = []
        self.R: list[float] = []
        self.forms: list[str] = []
        self.uncertain: list[int] = []

    # -------------------------------------------------------- checks of C2 and C3 (previous slot)
    def _to_robust(self, t: int, why: str) -> None:
        if self.robust_since is None:
            self.robust_since = int(t)
            self.events.append({"t": int(t), "event": "robust", "why": why})

    def _check(self, obs: SlowObs) -> None:
        t = int(obs.t)
        for r in obs.results:
            a = self.counted_acts.get(r.index)
            if a is None or r.ok or r.action != a:
                continue
            if isinstance(a, Buy) and r.reason == "unavailable":
                if self.cautious_since is None:
                    self.cautious_since = t
                self.events.append({"t": t, "event": "unavailable", "index": int(r.index)})
            else:
                self._to_robust(t, f"counted {type(a).__name__} at index {r.index} refused ({r.reason})")
        if self.counted_until:
            ended = {int(lid): int(e) for lid, e, _c in obs.ended}
            for lid, until in self.counted_until.items():
                e = ended.get(lid)
                if e is not None and e < until:
                    self._to_robust(t, f"lease {lid} ended at minute {e}, counted alive until minute {until}")
        self.counted_until, self.counted_acts = {}, {}

    # -------------------------------------------------------- the replicas after A_E(t)
    def _replicas(self, obs: SlowObs, actions):
        """[(llm, site, lease id or None, inB, lo, hi)] with (phi,) arrays, the counted actions and the number
        of uncertain Buys; None if the list names a lease or replica that obs does not contain, or an action of
        another type."""
        t = int(obs.t)
        Ds, Df, phi = self.Ds, self.Df, self.phi
        f0, minute = t * phi, t * Ds
        fs = f0 + np.arange(phi)
        ends = (fs + 1) * Df                                     # end minute of each fast slot
        alive_l = set(obs.leases)
        rep_ok = {rid for rid, rv in obs.replicas.items() if rv.lease_id in obs.leases}
        held: dict[int, float] = {}
        used: dict[int, int] = {}
        for lid, L in obs.leases.items():
            held[L.site] = held.get(L.site, 0.0) + L.gpus
        for rid in rep_ok:
            rv = obs.replicas[rid]
            used[rv.lease_id] = used.get(rv.lease_id, 0) + int(self.g[rv.llm])
        pend: dict[int, list] = {}           # replica id -> A_E(t)'s entries (eff fast slot, index, value, is_drain)
        new = []                             # (llm, site, lease view or None, contract, n, admission, certain, index)
        counted: dict[int, object] = {}
        n_unc = 0
        for i, a in enumerate(actions):
            if isinstance(a, Release):
                lid = int(a.lease_id)
                if lid not in alive_l:
                    return None
                alive_l.discard(lid)
                L = obs.leases[lid]
                held[L.site] = held.get(L.site, 0.0) - L.gpus
                rep_ok -= {rid for rid in rep_ok if obs.replicas[rid].lease_id == lid}
                # a replica that an earlier Load of this list put on the lease dies with it (the engine ends the
                # lease at the slot start, sim_spec §5.1); it is neither counted nor checked
                for e in [e for e in new if e[2] is not None and int(e[2].id) == lid]:
                    counted.pop(e[7], None)
                new = [e for e in new if e[2] is None or int(e[2].id) != lid]
            elif isinstance(a, Buy):
                l, k, j, nr = int(a.site), int(a.contract), int(a.llm), int(a.n_replicas)
                gpus = float(self.g[j] * nr)
                if held.get(l, 0.0) + gpus > self.cap_site[l]:
                    continue                                     # refused for capacity (§6.4): nothing
                held[l] = held.get(l, 0.0) + gpus                # the lender sells (else every Buy at l is refused)
                ann = obs.site_announced
                sure = (self.cautious_since is None or self.prot_site[l]
                        or (self.I2 and ann is not None and not bool(ann[l])))
                new.append((j, l, None, k, nr, float(a.admission), sure, i))
                if sure:
                    counted[i] = a
                else:
                    n_unc += 1
            elif isinstance(a, Load):
                lid, j = int(a.lease_id), int(a.llm)
                if lid not in alive_l:
                    return None
                L = obs.leases[lid]
                if L.gpus - used.get(lid, 0) < int(self.g[j]):
                    continue                                     # refused (lease_gpus): nothing
                used[lid] = used.get(lid, 0) + int(self.g[j])
                new.append((j, L.site, L, L.contract, 1, 1.0, True, i))
                counted[i] = a
            elif isinstance(a, Unload):
                rid = int(a.replica_id)
                if rid not in rep_ok:
                    return None
                rep_ok.discard(rid)
                rv = obs.replicas[rid]
                used[rv.lease_id] = used.get(rv.lease_id, 0) - int(self.g[rv.llm])
            elif isinstance(a, SetAdmission):
                rid = int(a.replica_id)
                if rid not in rep_ok:
                    return None
                pend.setdefault(rid, []).append((f0, i, float(a.value), False))
            elif isinstance(a, Drain):
                rid = int(a.replica_id)
                if rid not in rep_ok:
                    return None
                eff = max(f0, -(-int(a.at_min) // Df))
                ent = [e for e in pend.get(rid, []) if not e[3]]
                ent.append((eff, i, 0.0, True))
                pend[rid] = ent
            else:
                return None
        reps = []

        def lease_masks(L, k, start):
            if L is not None and L.death_min is not None:
                alive = ends <= int(L.death_min)
                return alive, alive
            alive = np.ones(phi, dtype=bool)
            D = self.Dk[k]
            inB = alive if D is None else ends <= int(start) + int(D)
            return alive, inB

        for rid in sorted(rep_ok):
            rv = obs.replicas[rid]
            L = obs.leases[rv.lease_id]
            alive, inB = lease_masks(L, L.contract, L.start_min)
            warm = fs >= int(rv.warm_fast)
            ent = list(pend.get(rid, []))
            unknown = False
            if rv.drain_min is not None:
                eo = -(-int(rv.drain_min) // Df)
                if any(e[3] for e in ent):
                    unknown = eo == f0                           # A_E(t)'s Drain removes a drain the view reflects
                elif eo > f0:
                    ent.append((eo, -1, 0.0, True))
            ent.sort(key=lambda e: (e[0], e[1]))
            adm = np.full(phi, float(rv.admission))
            for e in ent:
                adm[fs >= e[0]] = e[2]
            on = warm & alive
            hi = np.where(on, 1.0 if unknown else adm, 0.0)
            lo = np.zeros(phi) if unknown else np.where(on, adm, 0.0)
            reps.append((int(rv.llm), int(L.site), int(L.id), inB, lo, hi))
        for (j, l, L, k, nr, a0, sure, _i) in new:
            alive, inB = lease_masks(L, k, minute if L is None else L.start_min)
            wf = warm_fast(minute, int(self.lam[j, l]), Df)
            on = (fs >= wf) & alive
            hi = np.where(on, a0, 0.0)
            lo = hi if sure else np.zeros(phi)
            for _ in range(nr):
                reps.append((j, l, None if L is None else int(L.id), inB, lo, hi))
        return reps, counted, n_unc

    # -------------------------------------------------------- per fast slot
    def _route(self, j: int, d: np.ndarray, W: np.ndarray) -> float:
        """Greedy routing + fallback cost (USD per hour) of LLM j's demand d (n,) over capacity W (m,)."""
        cs = self.clients_of[j]
        if len(cs) == 0:
            return 0.0
        dj = d[cs]
        if not np.any(dj > 0):
            return 0.0
        q = float(self.q[j])
        okW = self.ok[cs] & (W > 0)[None, :]
        dl = np.where(okW, self.delta[cs], np.inf)
        best = np.argmin(dl, axis=1)
        bd = dl[np.arange(len(cs)), best]
        has = np.isfinite(bd) & (dj > 0)
        direct = float(np.sum(bd[has] * dj[has])) + q * float(np.sum(dj[~has]))
        if self.kinf or not has.any():
            return direct
        load = np.zeros(self.m)
        np.add.at(load, best[has], dj[has])
        if np.all(load <= W):
            return direct
        rd = np.array(d, dtype=np.float64)
        rc = np.array(W, dtype=np.float64)
        cost = 0.0
        for c, l, dv in self.arcs[j]:
            r = rd[c]
            if r <= 0.0:
                continue
            cap = rc[l]
            if cap <= 0.0:
                continue
            x = r if r < cap else cap
            cost += dv * x
            rd[c] = r - x
            rc[l] = cap - x
        return cost + q * float(np.sum(np.maximum(rd[cs], 0.0)))

    def _served_lb(self, j: int, d: np.ndarray, Wc: np.ndarray, Whi: np.ndarray) -> np.ndarray:
        """(n_j,) lower bound LB_c(f) on the load of each client of LLM j that every optimal routing of the
        fast slot serves (class docstring): d_c with kappa_infinite and an arc to a site with W^C > 0; d_c
        if W^C = W^hi and the cheapest-site assignment fits; else min{d_c, (sum over c's arcs of W^C -
        demand of c's competitors)^+}, a competitor being another client with d > 0 and an arc to a site l of
        P to which c has an arc, with delta_{c'l} <= delta_{cl}; 0 for d_c = 0."""
        cs = self.clients_of[j]
        dj = d[cs]
        act = dj > 0
        if not act.any():
            return np.zeros(len(cs))
        dd = np.where(act, dj, 0.0)
        okc = self.ok[cs]
        adm = okc & (Wc > 0)[None, :]
        if self.kinf:
            return np.where(adm.any(axis=1), dd, 0.0)
        full = np.zeros(len(cs), dtype=bool)
        if np.array_equal(Wc, Whi):
            dl = np.where(adm, self.delta[cs], np.inf)
            best = np.argmin(dl, axis=1)
            has = np.isfinite(dl[np.arange(len(cs)), best]) & act
            load = np.zeros(self.m)
            np.add.at(load, best[has], dj[has])
            if np.all(load <= Wc):
                full = has
        comp = (self.comp[j] & (Whi > 0)[None, None, :]).any(axis=2)
        others = comp.astype(np.float64) @ dd
        capc = (okc * Wc[None, :]).sum(axis=1)
        lb = np.minimum(dd, np.maximum(capc - others, 0.0))
        return np.where(full, dd, lb)

    def _served_ub(self, j: int, dprev: np.ndarray, Wh_prev: np.ndarray, lb_prev: np.ndarray) -> np.ndarray:
        """(n_j,) upper bound UB_c(f-1) on each client's served load in the previous fast slot: d_c(f-1),
        capped by the sum of W^hi(f-1) over c's arcs minus LB_{c'}(f-1) of every other client c' whose arcs to
        sites of P(f-1) all go to sites to which c has an arc (that load lies on c's sites); with
        kappa_infinite, d_c(f-1) if c has an arc to a site of P(f-1), else 0."""
        cs = self.clients_of[j]
        okc = self.ok[cs]
        P = Wh_prev > 0
        if self.kinf:
            return np.where((okc & P[None, :]).any(axis=1), dprev[cs], 0.0)
        A = (okc & P[None, :]).astype(np.float64)
        outside = A @ (~okc).T.astype(np.float64)                # [c', c]: sites of c' in P outside c's arcs
        sub = (outside.T == 0)
        np.fill_diagonal(sub, False)
        cap = np.where(okc, Wh_prev[None, :], 0.0).sum(axis=1) - sub.astype(np.float64) @ lb_prev[cs]
        return np.minimum(dprev[cs], np.maximum(cap, 0.0))

    # -------------------------------------------------------- the slot
    @property
    def robust(self) -> bool:
        """Whether the bound is in its robust form (C1 fails, or a check of C2 or C3 failed)."""
        return self.robust_all or self.robust_since is not None

    def begin(self, obs: SlowObs) -> None:
        """The checks of C2 and C3 for the previous slot's committed list; once per slot, before evaluate."""
        self._check(obs)

    def _reserve(self, d_last: np.ndarray, W_last: np.ndarray, lb_last: np.ndarray) -> float:
        """R(t) = sum_c kappa'_c UB_c(f_l) for the last fast slot f_l of the slot: the stranding bound of the next
        slot's first fast slot if every replica were gone there (class docstring, 'Reserve')."""
        if not self.has_strand or not self.n:
            return 0.0
        tot = 0.0
        for j in range(self.J):
            cs = self.clients_of[j]
            if len(cs) == 0:
                continue
            ub = self._served_ub(j, d_last, W_last[j], lb_last)
            tot += float(np.sum(self.kap[cs] * ub))
        return tot

    def evaluate(self, obs: SlowObs, actions, Q: float) -> dict:
        """The bound of slot t for the action list `actions`, without changing the state: G(t), S(t), the reserve
        R(t), the form and the state that commit() stores (W^hi and LB of the last fast slot, its demand, and the
        counted leases and actions that the next slot's checks of C2 and C3 test). Q = Q(t)."""
        t = int(obs.t)
        phi, Df = self.phi, self.Df
        d = np.asarray(obs.demand, dtype=np.float64).reshape(self.n, phi)
        dprev = np.concatenate([self.prev_d[:, None], d[:, :-1]], axis=1) if phi else d
        dh = np.minimum(dprev, d)
        st = None if self.robust else self._replicas(obs, list(actions))
        until: dict[int, int] = {}
        counted: dict[int, object] = {}
        if st is None:
            coef = self.kap * self.any_arc
            S = float(np.sum(dh * coef[:, None])) if self.n else 0.0
            G = float(Q)
            form, n_unc = "robust", 0
            Wn, lbn = np.full((self.J, self.m), np.inf), np.zeros(self.n)          # unknown: UB = d(f-1)
        else:
            reps, counted, n_unc = st
            J, m = self.J, self.m
            Wb, Wc, Wh = np.zeros((phi, J, m)), np.zeros((phi, J, m)), np.zeros((phi, J, m))
            drop = np.zeros((phi, J), dtype=bool)
            drop[0] = (self.prev_W > 0).any(axis=1)
            for (j, l, lid, inB, lo, hi) in reps:
                Wb[:, j, l] += np.where(inB, lo, 0.0)
                Wc[:, j, l] += lo
                Wh[:, j, l] += hi
                if phi > 1:
                    drop[1:, j] |= hi[:-1] > lo[1:]
                if lid is not None and np.any(lo > 0):
                    i_last = int(np.flatnonzero(lo > 0)[-1])
                    until[lid] = max(until.get(lid, 0), (t * phi + i_last + 1) * Df)
            G = S = 0.0
            Wprev, lbprev = self.prev_W, self.prev_lb
            has_s = self.has_strand
            for i in range(phi):
                di = d[:, i]
                for j in range(J):
                    G += self._route(j, di, Wb[i, j]) * Df / 60.0
                if has_s:
                    lbi = np.zeros(self.n)
                    for j in range(J):
                        cs = self.clients_of[j]
                        if len(cs) == 0:
                            continue
                        lb = self._served_lb(j, di, Wc[i, j], Wh[i, j])
                        lbi[cs] = lb
                        e = np.minimum(dh[cs, i], self._served_ub(j, dprev[:, i], Wprev[j], lbprev))
                        if not np.any(e > 0):
                            continue
                        Dj = 1.0 if drop[i, j] else 0.0
                        S += float(np.sum((self.mu_kv[j] + self.mu_fl[j] * Dj) * e
                                          + (self.mu_fb[j] + self.pi_W[j] * Dj) * np.maximum(e - lb, 0.0)))
                    lbprev = lbi
                Wprev = Wh[i]
            Wn, lbn = Wprev.copy(), np.array(lbprev, dtype=np.float64)
            form = "bound"
        d_last = d[:, -1].copy() if phi else self.prev_d.copy()
        R = self._reserve(d_last, Wn, lbn)
        return {"t": t, "G": float(G), "S": float(S), "Q": float(Q), "reserve": float(R), "form": form,
                "n_unc": int(n_unc), "prev_W": Wn, "prev_lb": lbn, "prev_d": d_last, "until": until,
                "counted": counted}

    def record(self, ev: dict) -> None:
        """Log an evaluated slot (the guard's E-mode slots, the aborting slot included)."""
        self.slots.append(int(ev["t"]))
        self.G.append(float(ev["G"]))
        self.S.append(float(ev["S"]))
        self.Q.append(float(ev["Q"]))
        self.R.append(float(ev["reserve"]))
        self.forms.append(ev["form"])
        self.uncertain.append(int(ev["n_unc"]))

    def commit(self, ev: dict) -> None:
        """Store the state of the executed list's evaluation for the next slot."""
        self.prev_W, self.prev_lb, self.prev_d = ev["prev_W"], ev["prev_lb"], ev["prev_d"]
        self.counted_until, self.counted_acts = dict(ev["until"]), dict(ev["counted"])

    def service(self, obs: SlowObs, actions, Q: float) -> float:
        """service(t) = G(t) + S(t) of the slot (USD) for an executed list: begin, evaluate, record and commit;
        Q = Q(t), the slot's exact all-fallback cost. The reserve R(t) is self.R[-1]."""
        self.begin(obs)
        ev = self.evaluate(obs, actions, Q)
        self.record(ev)
        self.commit(ev)
        return ev["G"] + ev["S"]

    def report(self) -> dict:
        return {"slots": list(self.slots), "G": list(self.G), "S": list(self.S), "Q": list(self.Q),
                "reserve": list(self.R), "service": [g + s for g, s in zip(self.G, self.S)],
                "forms": dict(Counter(self.forms)),
                "robust_slots": [t for t, f in zip(self.slots, self.forms) if f == "robust"],
                "robust_all": self.robust_all, "robust_since": self.robust_since, "on_unavailable": self.sales,
                "cautious_since": self.cautious_since, "uncertain_buys": int(sum(self.uncertain)),
                "uncertain": list(self.uncertain),
                "events": list(self.events)}


# ---------------------------------------------------------------- the guard rule (§3.4)
class Ratchet:
    """The one-way guard rule of §3.4 as pure logic.

    step(t, a_hat, C_S, B, alg_prev, force, reserve) at slot t in mode E: books m(t - 1) = max{0, ALG(t - 1) -
    a-hat(t - 1)} from alg_prev = ALG(t - 1) if slot t - 1 was executed, and returns True (execute E's
    actions) iff a-hat(t) + R(t) <= gamma C_S(t) + B(t) (up to GUARD_TOL) and the abort is not forced;
    otherwise it records the abort at t_a = t and returns False. R(t) >= 0 is the wind-down reserve (T0g,
    T0gBound's 'Reserve'; 0 under T0 and T1); m(t) is booked against a-hat(t) alone, the bound on ALG(t).
    B(t) must be nondecreasing. `allowance(B_on)` gives the constant B0 (kappa None) or the capped min{B0,
    kappa B_on(t)}; `test_value` gives T0's, T0g's or T1's a-hat (T0 and T0g add the same terms; they differ
    in the service term the caller passes)."""

    def __init__(self, gamma: float = 1.0, test: str = "T0", B0: float = 0.0, kappa: Optional[float] = None,
                 tol: float = GUARD_TOL):
        if not _is_num(gamma) or not gamma > 0:
            raise PolicyError(f"Ratchet: gamma must be a number > 0, got {gamma!r}")
        if test not in TESTS:
            raise PolicyError(f"Ratchet: test must be one of {TESTS}, got {test!r}")
        if not _is_num(B0) or not B0 >= 0 or not math.isfinite(float(B0)):
            raise PolicyError(f"Ratchet: B0 must be a finite number >= 0, got {B0!r}")
        if kappa is not None and (not _is_num(kappa) or not kappa >= 0 or not math.isfinite(float(kappa))):
            raise PolicyError(f"Ratchet: kappa must be None or a finite number >= 0, got {kappa!r}")
        self.gamma, self.test, self.B0 = float(gamma), test, float(B0)
        self.kappa = None if kappa is None else float(kappa)
        self.tol = float(tol)
        self.t_a: Optional[int] = None
        self.forced = False
        self.slots: list[int] = []          # executed and aborting slots, in order
        self.a_hat: list[float] = []
        self.C_S: list[float] = []
        self.B: list[float] = []
        self.rhs: list[float] = []
        self.reserve: list[float] = []      # R(t) at the same slots
        self.m: dict[int, float] = {}       # executed slot -> m(t) (once ALG(t) is known)
        self._last = -1

    @property
    def aborted(self) -> bool:
        return self.t_a is not None

    def allowance(self, B_on: float) -> float:
        """B(t): B0 (kappa None) or min{B0, kappa B_on(t)}."""
        if self.kappa is None:
            return self.B0
        return min(self.B0, self.kappa * float(B_on))

    def test_value(self, alg_prev: float, purchases: float, rent: float = 0.0, service: float = 0.0) -> float:
        """a-hat(t): ALG(t-1) + p(t) + rent(t) + service(t) under T0 (service Q(t)) and T0g (service
        G(t) + S(t), T0gBound), ALG(t-1) + p(t) under T1."""
        if self.test in ("T0", "T0g"):
            return float(alg_prev) + float(purchases) + float(rent) + float(service)
        return float(alg_prev) + float(purchases)

    def observe(self, t: int, alg_prev: float) -> None:
        """ALG(t - 1) observed at slot t: books m(t - 1) if slot t - 1 was executed in mode E."""
        u = int(t) - 1
        if self.slots and self.slots[-1] == u and (self.t_a is None or u < self.t_a) and u not in self.m:
            self.m[u] = max(0.0, float(alg_prev) - self.a_hat[-1])

    def step(self, t: int, a_hat: float, C_S: float, B: float, alg_prev: Optional[float] = None,
             force: bool = False, reserve: float = 0.0) -> bool:
        if self.t_a is not None:
            raise PolicyError(f"Ratchet: slot {t} after the abort at {self.t_a} (no return to mode E)")
        t = int(t)
        if t <= self._last:
            raise PolicyError(f"Ratchet: slot {t} after slot {self._last}")
        if self.B and float(B) < self.B[-1] - self.tol * max(1.0, abs(self.B[-1])):
            raise PolicyError(f"Ratchet: the allowance decreased from {self.B[-1]!r} to {B!r} at slot {t}")
        if not _is_num(reserve) or not float(reserve) >= 0 or not math.isfinite(float(reserve)):
            raise PolicyError(f"Ratchet: the reserve must be a finite number >= 0, got {reserve!r} at slot {t}")
        if alg_prev is not None:
            self.observe(t, alg_prev)
        self._last = t
        rhs = self.gamma * float(C_S) + float(B)
        self.slots.append(t)
        self.a_hat.append(float(a_hat))
        self.C_S.append(float(C_S))
        self.B.append(float(B))
        self.rhs.append(rhs)
        self.reserve.append(float(reserve))
        ok = (not force) and float(a_hat) + float(reserve) <= rhs + self.tol * max(1.0, abs(rhs))
        if not ok:
            self.t_a, self.forced = t, bool(force)
        return ok

    def report(self) -> dict:
        ex = self.slots if self.t_a is None else self.slots[:-1]
        return {"test": self.test, "gamma": self.gamma, "B0": self.B0, "kappa": self.kappa, "t_a": self.t_a,
                "forced": self.forced, "slots": list(self.slots), "a_hat": list(self.a_hat),
                "C_S": list(self.C_S), "B": list(self.B), "rhs": list(self.rhs), "reserve": list(self.reserve),
                "a_hat_t_a": self.a_hat[-1] if self.t_a is not None else None,
                "m": [self.m.get(u) for u in ex]}


# ---------------------------------------------------------------- the safe expert (§3.10)
class SafeExpert:
    """S of §3.10 on a PublicView, one slot at a time.

    step(obs) at slot t: FB's increment (the slot's exact all-fallback cost, also per LLM for F_j(t)),
    R's requests of the slot (A2Planner.slot) and, for 'fb+pd', the combiner's step with FB in the F
    slot. After it: C_S (cumulative), followed ('FB' or 'R'), switched, live (L_S(t), column ids in
    opening order), purchases (P_S(t)), W_S (W_S(t)), B_on (B_on(t)). refuse(col, t, reason) passes
    a refused purchase to the planner (after the abort only; §6.5)."""

    def __init__(self, view: PublicView, rng: np.random.Generator, *, safe: str = "fb+pd", rbar="theory",
                 N_bound: Optional[int] = None, gamma_T11: float = G2):
        if safe not in SAFE_MODES:
            raise PolicyError(f"safe must be one of {SAFE_MODES}, got {safe!r}")
        self.view = view
        self.safe = safe
        self.T = int(view.grid.T_slow)
        self.J = len(view.llms)
        self.cl_llm = np.asarray(view.client_llm, dtype=np.int64)
        self.uses_R = safe in ("fb+pd", "pd")
        self.planner: Optional[A2Planner] = None
        if self.uses_R:
            st = policy_streams(rng)
            self.planner = A2Planner(view, st["main"], st["order"], rbar=rbar, N_bound=N_bound)
            self.Ccol = np.asarray(self.planner.prob.C, dtype=np.float64)
        self.comb = DoublingCombiner(gamma_T11, labels=("FB", "R")) if safe == "fb+pd" else None
        self.Cmin = c_min(view)
        self.F_j = np.zeros(self.J)                 # all-fallback cost of LLM j through the last slot
        self.curve_fb = np.zeros(self.T)
        self.curve_r = np.zeros(self.T)
        self.curve_s = np.zeros(self.T)             # increments c_S(t); C_S(t) = their prefix sum
        self.B_on_curve = np.zeros(self.T)
        self.W_curve = np.zeros(self.T)
        self.followed_list: list[str] = []
        self.switch_slots: list[int] = []
        self._live: dict[int, int] = {}             # R's opened column -> end of its window (opening order)
        self.C_S = 0.0
        self.C_FB = 0.0
        self.C_R = 0.0
        self.fb_inc = 0.0
        self.followed = "FB" if safe == "fb" else "R"
        self.switched = False
        self.live: list[int] = []
        self.purchases: list[int] = []
        self.W_S = 0.0
        self.B_on = 0.0
        self.t = -1

    # -------------------------------------------------------- columns
    def column(self, col: int) -> tuple[int, int, int, int, int, int]:
        """(l, j, k, s, iota, L_k) of one of R's columns."""
        return self.planner.column(col)

    def cost(self, cols) -> float:
        """sum of C_F (the PD's column cost, prob.C) over R's columns `cols`."""
        tot = 0.0
        for col in cols:
            l, j, k, s, iota, L = self.planner.column(col)
            tot += float(self.Ccol[l, j, k])
        return tot

    def r_live(self) -> list[int]:
        """R's opened columns whose window contains the current slot, in opening order (refused ones excluded)."""
        if not self.uses_R:
            return []
        op = self.planner.rounder.opened
        return [c for c in self._live if c in op]

    def refuse(self, col: int, t: int, reason: str = "") -> None:
        if self.planner is None:
            return
        self.planner.refuse(col, t, reason)
        self._live.pop(int(col), None)

    # -------------------------------------------------------- one slot
    def step(self, obs: SlowObs) -> None:
        t = int(obs.t)
        if t <= self.t:
            raise PolicyError(f"SafeExpert: slot {t} after slot {self.t}")
        self.t = t
        fb_c = fallback_by_client(self.view, obs.demand)
        inc_fb = float(fb_c.sum())
        if len(fb_c):
            np.add.at(self.F_j, self.cl_llm, fb_c)
        self.fb_inc = inc_fb
        opened: list[int] = []
        inc_r = 0.0
        if self.uses_R:
            pl = self.planner
            opened = list(pl.slot(obs))
            for col in opened:
                l, j, k, s, iota, L = pl.column(col)
                self._live[int(col)] = s + L
            for col in [c for c, e in self._live.items() if e <= t or c not in pl.rounder.opened]:
                del self._live[col]
            inc_r = float(pl.rounder.curve[t]) if t < len(pl.rounder.curve) else 0.0
        self.switched = False
        if self.safe == "fb":
            self.followed, inc_s, live, buys = "FB", inc_fb, [], []
        elif self.safe == "pd":
            self.followed, inc_s = "R", inc_r
            live = self.r_live()
            buys = [c for c in opened if c in self.planner.rounder.opened]
        else:
            comb = self.comb
            prev = comb.total
            live_r = self.r_live()
            opened_ok = [c for c in opened if c in self.planner.rounder.opened]

            def state_cost(w):
                return 0.0 if w == "F" else self.cost(live_r)

            def serv(w):
                return inc_fb if w == "F" else inc_r - self.cost(opened_ok)
            cur, sw = comb.step(inc_fb, inc_r, state_cost, serv)
            self.switched = bool(sw)
            if sw:
                self.switch_slots.append(t)
            inc_s = comb.total - prev
            if cur == "F":
                self.followed, live, buys = "FB", [], []
            else:
                self.followed, live = "R", live_r
                buys = list(live_r) if sw else opened_ok
        bset = set(buys)
        self.live, self.purchases = live, buys
        self.W_S = self.cost([c for c in live if c not in bset]) if live else 0.0
        self.C_FB += inc_fb
        self.C_R += inc_r
        self.C_S = (self.comb.total if self.comb is not None else self.C_S + inc_s)
        self.B_on = float(np.sum(np.minimum(self.F_j, self.Cmin)))
        if t < self.T:
            self.curve_fb[t], self.curve_r[t], self.curve_s[t] = inc_fb, inc_r, inc_s
            self.B_on_curve[t], self.W_curve[t] = self.B_on, self.W_S
        self.followed_list.append(self.followed)

    def followed_rle(self) -> list[list]:
        """S's followed expert per slot, run-length encoded: [[which, first slot, length], ...]."""
        out: list[list] = []
        for t, w in enumerate(self.followed_list):
            if out and out[-1][0] == w:
                out[-1][2] += 1
            else:
                out.append([w, t, 1])
        return out

    def report(self) -> dict:
        n = self.t + 1
        out = {"safe": self.safe, "C_S": float(self.C_S), "C_FB": float(self.C_FB), "C_R": float(self.C_R),
               "C_S_curve": np.cumsum(self.curve_s[:n]).tolist(), "curve_S": self.curve_s[:n].tolist(),
               "curve_FB": self.curve_fb[:n].tolist(), "curve_R": self.curve_r[:n].tolist(),
               "B_on": self.B_on_curve[:n].tolist(), "W_S": self.W_curve[:n].tolist(),
               "C_min": [None if not np.isfinite(x) else float(x) for x in self.Cmin],
               "followed": self.followed_rle(), "switch_slots": list(self.switch_slots)}
        if self.comb is not None:
            out.update(switches=int(self.comb.switches), gamma_T11=self.comb.gamma, labels=list(self.comb.labels))
        if self.planner is not None:
            pl, rd = self.planner, self.planner.rounder
            out["R"] = {"rbar": pl.rbar, "N_bound": pl.N_bound, "cost_pr": float(rd.cost_pr),
                        "cost_an": float(rd.cost_an), "opened": len(rd.opened), "refused": len(rd.refused),
                        "refused_by_reason": dict(pl.refused_reasons), "P": float(pl.pd.primal()),
                        "d": int(pl.pd.d)}
        return out


# ---------------------------------------------------------------- the inner policy's observation (audit F2)
_SHARED = (int, float, str, bytes, tuple, frozenset, type(None), np.generic)   # values that are not copied


def inner_obs(obs: SlowObs) -> SlowObs:
    """A private copy of a slow-slot observation for the inner policy (audit F2, design/theory/audit_guard.md): new
    dicts, lists and arrays with the same contents, sharing only immutable values (the frozen LeaseView, ReplicaView,
    Notice and ActionResult records, the tuples of obs.ended, numbers). The guard computes its test from the
    original, so an inner policy that writes to its observation (assigns a field such as obs.cost_so_far, adds or
    removes entries of obs.leases, obs.replicas, obs.results or obs.ended, writes into an array) cannot change the
    test, and it sees exactly the values it would see alone (the engine's arrays are writable copies too). A field
    of another type raises PolicyError, so that a new mutable field of SlowObs is not shared unnoticed; that the
    records are frozen dataclasses is pinned by tests/test_guard.py::test_audit_f2_inner_obs.

    Why a copy for the inner policy rather than a snapshot, before the inner policy acts, of the fields the guard
    reads: the guard reads t, cost_so_far, demand, leases, replicas, results, ended and site_announced, so the
    snapshot would copy the same containers; both are shallow, O(leases + replicas + results + n phi) per slot and
    negligible next to T0gBound.evaluate, and neither needs a deep copy, since the entries are immutable. The
    snapshot would in addition have to move SafeExpert.step and T0gBound.begin before the inner policy and be
    extended whenever the guard reads a further field, while the copy closes every path at one call site and leaves
    the order of the guard's steps (and so every run without writes, bit for bit) unchanged."""
    kw = {}
    for f in dataclasses.fields(obs):
        v = getattr(obs, f.name)
        if isinstance(v, np.ndarray):
            v = v.copy()
        elif isinstance(v, dict):
            v = dict(v)
        elif isinstance(v, list):
            v = list(v)
        elif not isinstance(v, _SHARED):
            raise PolicyError(f"inner_obs: field {f.name!r} of type {type(v).__name__} is neither copied nor immutable")
        kw[f.name] = v
    return type(obs)(**kw)


# ---------------------------------------------------------------- policy A8
class Guarded(Policy):
    """A8 (§3.10): the inner policy E under the guard of §3.4 with the safe expert S.

    Parameters: inner (an id of INNER_IDS, default 'A7'; a Policy instance is accepted for tests),
    inner_params (the inner's parameters and driver inputs), safe ('fb+pd', 'pd', 'fb'), S_rbar
    ('theory' or an integer >= 1), gamma (> 0, default 1), gamma_T11 (> 1, default 1 + 1/sqrt 2),
    test ('T0g', the default, with the wind-down reserve R(t) in the test; 'T0', sound on the core only;
    'T1'), wind_down ('auto', the default: 'adaptive' under T0g and 'keep' under T0 and T1; 'adaptive' needs
    T0g; 'release'; 'keep'; module docstring), reserve (default true: under T0g the reserve R(t) enters the test;
    false, with wind_down 'keep', reproduces the T0g of commit d2a538d, whose full-model bound fails; Theorem W
    needs true), B0 ('auto' or a number >= 0), kappa (default 10; None for the
    constant allowance B0) and the test-only abort_at (None, or the slot from which the guard aborts
    unconditionally). Driver inputs: N_bound (S_rbar = 'theory' with R in S) and on_unavailable (the lender's
    sale rule, 'sell' or 'refuse', which drivers/run.py passes from the run's lender model; T0gBound's C2:
    under 'refuse' every Buy the lender could refuse is uncertain from slot 0; None, the default of a direct
    construction, presumes 'sell' until E's first 'unavailable' refusal). In mode E the inner policy acts on a
    private copy of each slow-slot observation (inner_obs, audit F2)."""
    name = "A8"
    PARAMS = {"inner": "A7", "inner_params": {}, "safe": "fb+pd", "S_rbar": "theory", "gamma": 1.0,
              "gamma_T11": G2, "test": "T0g", "wind_down": "auto", "reserve": True, "B0": "auto", "kappa": 10.0,
              "abort_at": None}
    INPUTS = ("N_bound", "on_unavailable")

    def __init__(self, **kw):
        self._p, inp = resolve_params(self.PARAMS, kw, "A8", inputs=self.INPUTS)
        p = self._p
        if p["safe"] not in SAFE_MODES:
            raise PolicyError(f"A8: safe must be one of {list(SAFE_MODES)}, got {p['safe']!r}")
        r = p["S_rbar"]
        if r != "theory" and (isinstance(r, bool) or not isinstance(r, (int, np.integer)) or r < 1):
            raise PolicyError(f"A8: S_rbar must be an integer >= 1 or 'theory', got {r!r}")
        if not _is_num(p["gamma"]) or not p["gamma"] > 0:
            raise PolicyError(f"A8: gamma must be a number > 0, got {p['gamma']!r}")
        if not _is_num(p["gamma_T11"]) or not p["gamma_T11"] > 1:
            raise PolicyError(f"A8: gamma_T11 must be a number > 1, got {p['gamma_T11']!r}")
        if p["test"] not in TESTS:
            raise PolicyError(f"A8: test must be one of {list(TESTS)}, got {p['test']!r}")
        if p["wind_down"] not in WIND_DOWNS:
            raise PolicyError(f"A8: wind_down must be one of {list(WIND_DOWNS)}, got {p['wind_down']!r}")
        if p["wind_down"] == "adaptive" and p["test"] != "T0g":
            raise PolicyError("A8: wind_down 'adaptive' needs test 'T0g' (its bounds are T0gBound's)")
        if not isinstance(p["reserve"], (bool, np.bool_)):
            raise PolicyError(f"A8: reserve must be true or false, got {p['reserve']!r}")
        b0 = p["B0"]
        if b0 != "auto" and (not _is_num(b0) or not b0 >= 0 or not math.isfinite(float(b0))):
            raise PolicyError(f"A8: B0 must be 'auto' or a finite number >= 0, got {b0!r}")
        ka = p["kappa"]
        if ka is not None and (not _is_num(ka) or not ka >= 0 or not math.isfinite(float(ka))):
            raise PolicyError(f"A8: kappa must be None or a finite number >= 0, got {ka!r}")
        ab = p["abort_at"]
        if ab is not None and (isinstance(ab, bool) or not isinstance(ab, (int, np.integer)) or ab < 0):
            raise PolicyError(f"A8: abort_at must be None or an integer >= 0, got {ab!r}")
        ip = p["inner_params"]
        if ip is None:
            ip = {}
        if not isinstance(ip, dict):
            raise PolicyError(f"A8: inner_params must be an object, got {type(ip).__name__}")
        inner = p["inner"]
        if isinstance(inner, Policy):
            if ip:
                raise PolicyError("A8: inner_params must be empty when inner is a Policy instance")
            self.inner, self.inner_id = inner, getattr(inner, "name", type(inner).__name__)
        else:
            if inner not in INNER_IDS:
                raise PolicyError(f"A8: inner must be one of {list(INNER_IDS)}, got {inner!r}")
            self.inner, self.inner_id = _inner_class(inner)(**dict(ip)), inner
        self.N_bound = inp.get("N_bound")
        if p["safe"] != "fb" and r == "theory" and self.N_bound is None:
            raise PolicyError("A8: S_rbar='theory' needs the driver input N_bound (§6.3)")
        self.on_unavailable = inp.get("on_unavailable")
        if self.on_unavailable not in SALE_RULES:
            raise PolicyError(f"A8: on_unavailable must be one of {list(SALE_RULES)}, got {self.on_unavailable!r}")
        wd = p["wind_down"]
        self.wd = ("adaptive" if p["test"] == "T0g" else "keep") if wd == "auto" else wd

    def params(self) -> dict:
        out = {k: copy.deepcopy(v) for k, v in self._p.items() if k not in ("inner", "inner_params")}
        out["inner"] = self.inner_id
        pf = getattr(self.inner, "params", None)
        out["inner_params"] = pf() if callable(pf) else {}
        return out

    # -------------------------------------------------------- reset
    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        p = self._p
        rng_E, rng_S = copy.deepcopy(rng), copy.deepcopy(rng)
        self.inner.reset(view, rng_E)
        self.wants_fast = bool(getattr(self.inner, "wants_fast", False))
        self.sx = SafeExpert(view, rng_S, safe=p["safe"], rbar=p["S_rbar"],
                             N_bound=None if p["safe"] == "fb" else self.N_bound, gamma_T11=float(p["gamma_T11"]))
        B0 = b0_auto(view) if p["B0"] == "auto" else float(p["B0"])
        self.ratchet = Ratchet(float(p["gamma"]), p["test"], B0, p["kappa"])
        # T0g's service term and reserve (§3.4, §3.10); robust form at every slot for an inner that uses on_fast (C1)
        self.t0g = (T0gBound(view, robust=self.wants_fast, on_unavailable=self.on_unavailable)
                    if p["test"] == "T0g" else None)
        self.book = LeaseBook()
        self.slow = int(view.grid.slow_min)
        self.prepaid = [int(c.prepaid_min) for c in view.contracts]
        self.mode = "E"
        self.t_a: Optional[int] = None
        self.modes: list[str] = []
        self.alg_prev: list[float] = []          # ALG(t - 1) = obs.cost_so_far at slot t
        self.terms: list[list[float]] = []       # [p_E(t), rent_E(t), Q(t)] at the E-mode slots
        self._release_at: dict[int, list[int]] = {}
        self.at_abort: dict = {}
        self.budget = 0.0                        # R(t) of the last executed E-mode slot; in the wind-down, its budget
        self._inh: set[int] = set()              # E's leases held at t_a
        self._own: set[int] = set()              # S's own leases (bought after t_a)
        self._wd_live = True                     # T0gBound's state is the last slot's executed list
        self.wd_log: list[dict] = []
        self.exec = {"inherited": 0, "inherited_released_at_abort": 0, "inherited_released": 0, "copies": 0,
                     "buys": 0, "bought": 0, "released": 0, "precheck": 0, "refused": 0, "refused_by_reason": {}}

    # -------------------------------------------------------- act
    def act(self, obs: SlowObs) -> list:
        t = int(obs.t)
        self.alg_prev.append(float(obs.cost_so_far))
        if self.mode == "E":
            acts = list(self.inner.act(inner_obs(obs)))     # a private copy (audit F2): the test reads obs
            self.sx.step(obs)
            rt = self.ratchet
            B_t = rt.allowance(self.sx.B_on)
            pE, rent = slot_terms(self.view, obs, acts)
            Q = self.sx.fb_inc
            self.terms.append([pE, rent, Q])
            ev, R = None, 0.0
            if self.t0g is None:
                serv = Q
            else:
                self.t0g.begin(obs)
                ev = self.t0g.evaluate(obs, acts, Q)
                self.t0g.record(ev)
                serv, R = ev["G"] + ev["S"], (ev["reserve"] if self._p["reserve"] else 0.0)
            a_hat = rt.test_value(obs.cost_so_far, pE, rent, serv)
            ab = self._p["abort_at"]
            force = ab is not None and t >= int(ab)
            if rt.step(t, a_hat, self.sx.C_S, B_t, alg_prev=obs.cost_so_far, force=force, reserve=R):
                if ev is not None:
                    self.t0g.commit(ev)
                self.budget = float(R)
                self.modes.append("E")
                return acts
            return self._abort(obs)
        self.modes.append("S")
        return self._s_step(obs)

    def on_fast(self, obs: FastObs) -> list:
        if self.mode == "E" and self.wants_fast:
            return self.inner.on_fast(obs)
        return []

    # -------------------------------------------------------- mode S
    def _release_slot(self, col: int, t0: int) -> int:
        """A2's release slot (§6.6): max(s + L_k, t0 + ceil(P_k / Δs))."""
        l, j, k, s, iota, L = self.sx.column(col)
        return max(s + L, t0 + -(-self.prepaid[k] // self.slow))

    def _buy(self, col: int, t: int, kind: str) -> None:
        l, j, k, s, iota, L = self.sx.column(col)
        self.book.buy((kind, int(col), int(t)), Buy(l, k, j, 1, tag=TAG_COPY if kind == "copy" else TAG_BUY))
        self.exec["copies" if kind == "copy" else "buys"] += 1

    def _stage_purchases(self, t: int) -> None:
        sx = self.sx
        kind = "copy" if (sx.switched or t == self.t_a) else "buy"
        for col in (sx.live if t == self.t_a else sx.purchases):
            self._buy(col, t, kind)

    def _lease_rent(self, L, t: int) -> float:
        """The rent bound of slot t of one held lease (slot_terms): g a over [max(t Δs, b_L), min((t+1) Δs, d_L))."""
        t0m, t1m = t * self.slow, (t + 1) * self.slow
        hi = t1m if L.death_min is None else min(t1m, int(L.death_min))
        span = hi - max(t0m, int(L.prepaid_end_min))
        return L.gpus * float(self.view.price[L.site, L.contract]) * span / 60.0 if span > 0 else 0.0

    def _wind_down(self, obs: SlowObs, t: int, begun: bool):
        """The inner's leases still held at slot t >= t_a under wind_down 'release' or 'adaptive' (module docstring):
        stages their Releases and returns (candidate list, its evaluation, kept ids) for _commit_wind_down, or None.
        'release', and 'adaptive' wherever its conditions fail (T0gBound robust, S follows R, buys, or holds a lease
        of its own): every such lease is released now (K0). 'adaptive' otherwise: of K1 (keep the leases without
        rent in slot t), K0 (keep none) and K2 (keep all), the one with the least beta(K) = G + S + rent - Q(t) +
        R(t) of T0gBound's evaluation of its list, the earlier one on a tie (WD_TIE); beta(K0) <= the budget, the
        reserve of the previous slot (proof in the module docstring)."""
        H = [int(l) for l in sorted(obs.leases) if int(l) in self._inh]
        if not H:
            return None
        sx, tb = self.sx, self.t0g
        why = None
        if self.wd != "adaptive" or tb is None:
            why = "rule"
        elif not self._wd_live:
            why = "state"
        else:
            if not begun:
                tb.begin(obs)
            if tb.robust:
                why = "robust"
            elif sx.followed != "FB" or sx.purchases or (t == self.t_a and sx.live):
                why = "S follows R"
            elif any(int(l) in self._own for l in obs.leases):
                why = "own leases"
        if why is not None:
            for lid in H:
                self.book.release(lid)
            self.exec["inherited_released"] += len(H)
            if t == self.t_a:
                self.exec["inherited_released_at_abort"] += len(H)
            self._wd_live = False
            self.wd_log.append({"t": t, "held": len(H), "kept": 0, "choice": "K0", "why": why,
                                "budget": float(self.budget)})
            return None
        Q = float(sx.fb_inc)
        K1 = [l for l in H if self._lease_rent(obs.leases[l], t) <= 0.0]
        order = []                                        # in preference order for ties: K1, K0, K2
        if K1:
            order.append(("K1" if len(K1) < len(H) else "K2", K1))
        order.append(("K0", []))
        if len(K1) < len(H):
            order.append(("K2", H))
        cands = []
        for name, K in order:
            ks = set(K)
            lst = [Release(l) for l in H if l not in ks]
            ev = tb.evaluate(obs, lst, Q)
            rent = slot_terms(self.view, obs, lst)[1]
            beta = ev["G"] + ev["S"] + rent - Q + ev["reserve"]
            cands.append((name, K, lst, ev, rent, beta))
        tie = WD_TIE * max(1.0, abs(Q))
        best = cands[0]
        for c in cands[1:]:
            if c[5] < best[5] - tie:
                best = c
        name, K, lst, ev, rent, beta = best
        b0 = next(c[5] for c in cands if not c[1])
        for a in lst:
            self.book.release(a.lease_id)
        self.exec["inherited_released"] += len(lst)
        if t == self.t_a:
            self.exec["inherited_released_at_abort"] += len(lst)
        self.wd_log.append({"t": t, "held": len(H), "kept": len(K), "choice": name, "why": None,
                            "budget": float(self.budget), "beta": {c[0]: float(c[5]) for c in cands},
                            "beta_K0_le_budget": bool(b0 <= self.budget + GUARD_TOL * max(1.0, abs(self.budget),
                                                                                          abs(Q)))})
        return lst, ev, K

    def _commit_wind_down(self, obs: SlowObs, acts: list, pick) -> None:
        """After the slot's list is assembled: T0gBound's state for the next slot, and the next budget R(t)."""
        if pick is None:
            return
        lst, ev, K = pick
        if not K:
            self._wd_live = False
            self.budget = 0.0
            return
        if list(acts) != list(lst):                        # S stages nothing at an adaptive slot; recheck anyway
            ev = self.t0g.evaluate(obs, acts, float(self.sx.fb_inc))
            self.wd_log[-1]["relisted"] = True
        self.t0g.commit(ev)
        self.budget = float(ev["reserve"])
        self._wd_live = True

    def _abort(self, obs: SlowObs) -> list:
        """Slot t_a (§3.10): E's actions are discarded; the inner's leases wind down by the rule self.wd ('keep':
        held leases past their billed term are released, the others at the first slot at or after their billed
        end; 'release': all now; 'adaptive': _wind_down); one Buy per column of L_S(t_a)."""
        t = int(obs.t)
        self.mode, self.t_a = "S", t
        self.modes.append("S")
        sx = self.sx
        self.book.begin(obs)
        self._inh = {int(l) for l in obs.leases}
        self.exec["inherited"] += len(obs.leases)
        self.at_abort = {"t_a": t, "a_hat": self.ratchet.a_hat[-1], "rhs": self.ratchet.rhs[-1],
                         "reserve": self.ratchet.reserve[-1], "budget": float(self.budget), "wind_down": self.wd,
                         "C_S": float(sx.C_S), "B": self.ratchet.B[-1], "W_S": float(sx.W_S),
                         "followed": sx.followed, "switched": bool(sx.switched),
                         "live": len(sx.live), "purchases": len(sx.purchases),
                         "switches": int(sx.comb.switches) if sx.comb is not None else 0,
                         "forced": self.ratchet.forced}
        pick = None
        if self.wd == "keep":
            for lid, L in obs.leases.items():
                if int(L.prepaid_end_min) <= t * self.slow:
                    self.book.release(lid)
                    self.exec["inherited_released_at_abort"] += 1
                else:
                    self._release_at.setdefault(-(-int(L.prepaid_end_min) // self.slow), []).append(int(lid))
        else:
            pick = self._wind_down(obs, t, begun=self.t0g is not None)
        self._stage_purchases(t)
        acts = self.book.assemble(obs, self.view)
        self._commit_wind_down(obs, acts, pick)
        return acts

    def _s_step(self, obs: SlowObs) -> list:
        t = int(obs.t)
        sx = self.sx
        for key, r in self.book.begin(obs):
            kind, col, t0 = key
            if r.ok:
                self._release_at.setdefault(self._release_slot(col, t0), []).append(int(r.lease_id))
                self._own.add(int(r.lease_id))
                self.exec["bought"] += 1
            else:
                self.exec["precheck" if r.reason == "precheck" else "refused"] += 1
                rb = self.exec["refused_by_reason"]
                rb[r.reason] = rb.get(r.reason, 0) + 1
                sx.refuse(col, t, r.reason)
        sx.step(obs)
        for ts in sorted(x for x in self._release_at if x <= t):
            for lid in self._release_at.pop(ts):
                if lid in obs.leases:
                    self.book.release(lid)
                    self.exec["released"] += 1
        pick = None if self.wd == "keep" else self._wind_down(obs, t, begun=False)
        self._stage_purchases(t)
        acts = self.book.assemble(obs, self.view)
        self._commit_wind_down(obs, acts, pick)
        return acts

    # -------------------------------------------------------- report
    def mode_rle(self) -> list[list]:
        out: list[list] = []
        for t, w in enumerate(self.modes):
            if out and out[-1][0] == w:
                out[-1][2] += 1
            else:
                out.append([w, t, 1])
        return out

    def report(self) -> dict:
        sx = getattr(self, "sx", None)
        if sx is None:
            return {"inner_id": self.inner_id}
        rt = self.ratchet.report()
        safe = sx.report()
        safe["B_curve"] = [self.ratchet.allowance(b) for b in safe["B_on"]]       # B(t) at every slot
        if self.t_a is not None and sx.comb is not None:
            safe["switches_after_t_a"] = int(sx.comb.switches) - int(self.at_abort.get("switches", 0))
        else:
            safe["switches_after_t_a"] = 0
        ir = getattr(self.inner, "report", None)
        extra = {} if getattr(self, "t0g", None) is None else {"t0g": self.t0g.report()}
        return {**extra, "inner_id": self.inner_id, "t_a": self.t_a, "aborted": self.t_a is not None,
                "mode": self.mode_rle(), "guard": rt, "gamma": self.ratchet.gamma, "kappa": self.ratchet.kappa,
                "B0": self.ratchet.B0, "test": self.ratchet.test, "wind_down": self.wd,
                "reserve": bool(self._p["reserve"]),
                "on_unavailable": self.on_unavailable, "alg_prev": list(self.alg_prev),
                "terms": [list(x) for x in self.terms], "at_abort": dict(self.at_abort),
                "W_S_t_a": self.at_abort.get("W_S"), "a_hat_t_a": self.at_abort.get("a_hat"),
                "budget_t_a": self.at_abort.get("budget"), "wd": [dict(x) for x in self.wd_log],
                "safe": safe, "exec": copy.deepcopy(self.exec), "book": dict(self.book.stats),
                "inner": ir() if callable(ir) else {}}


__all__ = ["INNER_IDS", "SAFE_MODES", "TESTS", "WIND_DOWNS", "SALE_RULES", "GUARD_TOL", "WD_TIE", "fallback_by_client",
           "b0_auto", "c_min", "buy_price", "slot_terms", "T0gBound", "Ratchet", "SafeExpert", "inner_obs", "Guarded"]


# ---------------------------------------------------------------- policy A8P (design/sublet_v2.md §2.4)
PROJ_INNER_IDS = INNER_IDS + ("A9",)     # registry.A8P_INNER_IDS (design/sublet_v2.md §2.4, §8.1 C34, C36)
ALLOWANCES = ("alg1", "lb")              # A8P's allowance rules (ProjectedGuarded, parameter allowance)


class _LBRatchet(Ratchet):
    """The Ratchet of A8P's allowance 'lb': allowance(B_on) ignores B_on and returns the current slot's B(t) =
    min{W_k(t), LB'(t)} of the OnlineLB `source`, which ProjectedGuarded.act steps at its start; everything else,
    step's check that B never decreases included, is Ratchet's with kappa None."""

    def __init__(self, source: OnlineLB, gamma: float, test: str, B0: float):
        super().__init__(gamma, test, B0, None)
        self.source = source

    def allowance(self, B_on: float) -> float:
        return float(self.source.B)


class ProjectedGuarded(Guarded):
    """A8P (design/sublet_v2.md §2.4, §8.1 C36): A8 with projection, the revised Algorithm 1.

    Parameters: those of A8 (Guarded.PARAMS) with inner default 'A9' and the inner ids PROJ_INNER_IDS (INNER_IDS and
    A9; A8P builds the inner policy itself and passes the instance to Guarded.__init__, so that Guarded, INNER_IDS
    and registry.A8_INNER_IDS stay unchanged; a Policy instance is accepted for tests), and project (default true;
    true needs test 'T0g') and allowance ('alg1', the default, or 'lb'; below). With project false every slot is A8's
    (Guarded.act, Guarded.on_fast): A8P is A8 around the same inner policy, bit for bit, at the same allowance. A8P is
    a new id with its own PARAMS rather than a key of Guarded.PARAMS, which tests/test_guard.py::test_params pins
    (§8.1). Driver inputs as A8 (N_bound, on_unavailable).

    Allowance (parameter allowance; design/sublet_v2.md §2.5, §5 P2). 'alg1': Algorithm 1's B(t) =
    Ratchet.allowance(B_on(t)), that is B0 (kappa None) or min{B0, kappa B_on(t)} (Lemma G5); runs, reports and params()
    are exactly those before the option (tests/test_online_lb.py::test_alg1_bit_identical digests the full report).
    'lb': B(t) = min{W_k(t), LB'(t)} of online_lb.OnlineLB, the per-group online lower bound LB' of C3 §9's Lemma G5'
    with the pilot's U = W_k; Corollary G3' gives G3 with B <= LB' in place of B <= kappa B_on (kappa = 1; the constant
    of G3(b) becomes (1 + gamma) c(gamma') + 1, about 12.66 at gamma = 1); both are PROVEN (audited:
    design/theory/audit_guard.md, 'Audit addendum (P6)'; Corollary G3' on the core, and for A8P on core exports with the
    label of the Guarantees below; evidence in online_lb's module docstring). 'lb' needs kappa None (PolicyError
    otherwise), so that the per-run certificate's Corollary G3 line, which reads kappa (q44_study.certificate), is not
    applied to an allowance that kappa B_on does not bound; B0 is not used, and the report records B0 None (top level
    and guard.B0, so ms4_common.a8_record's B0_report_usd is None too) rather than a constant no slot used (_LBRatchet
    keeps the resolved B0, which nothing reads). The OnlineLB is built in reset from the view and stepped once per act
    call, at its start, in every mode (E and S, project true or false), from the engine's obs.demand, so B(t) is the
    slot's value wherever Guarded.act or the projected act asks for the allowance. It is served through the Ratchet: a
    private subclass (_LBRatchet) whose allowance(B_on) returns the slot's B(t), so that Ratchet.step's check that B
    never decreases stays in force. By Lemma G5'(a) B is nonnegative, nondecreasing and known at slot t before the
    platform acts (in float64 too, for nonnegative loading charges and fallback prices: online_lb's module docstring, C3
    §9's fact F7; Ratchet.step's check tolerates a decrease of up to GUARD_TOL max(1, |B|), so the float monotonicity
    that Proposition P(d) uses comes from OnlineLB itself), so Theorem W, which takes any such allowance, holds for it,
    and with 'lb' both guards of Remark R use this rule (tests/test_guard_projection.py::test_remark_r_identity compares
    A8P with A8P at project false, which is A8 at this allowance, around Proj(E)). The resolved parameters and the
    report keep 'allowance' only at 'lb', so that params() and the run records at Algorithm 1's allowance stay those of
    the pilot's A8P runs.

    Projection (project true, mode E, slot t):
    1. The inner policy acts on inner_obs(obs) (audit F2) whose results field is remapped after a projected slot t - 1:
       each executed action carries its index in the inner's own list A_E(t - 1), each action of A_E(t - 1) that the
       guard dropped appears as ActionResult(index, action, ok=False, lease_id=None, replica_ids=(), reason='guard'),
       and a Release that the guard added (K0) has no result; the lease it released appears in obs.ended with cause
       'release'. After a slot executed as A_E(t - 1) the inner receives the engine's results, as under A8.
    2. SafeExpert.step, B(t) = Ratchet.allowance(B_on), Q(t), then T0gBound.begin once.
    3. The candidates below, in this order, each evaluated with the stateless T0gBound.evaluate and slot_terms. A^-_E(t)
       is A_E(t) without its Buys and without every action that names a lease or replica that obs does not contain
       (an object of a Buy or Load of the same list):
         E   A_E(t);
         P1  if A_E(t) has n_b >= 2 Buys, for each n in the descending distinct values of {n_b - 1, floor(n_b / 2),
             floor(n_b / 4), 1} minus {0, n_b}: the first n Buys of A_E(t) and A^-_E(t), in A_E(t)'s order (an action
             on an object of a kept Buy is dropped too, a simplification);
         P0  if n_b >= 1 or A^-_E(t) differs from A_E(t): A^-_E(t);
         K0  a Release of every lease that obs holds, in lease-id order, and nothing else; it names only objects of
             obs, so its evaluation is in bound form unless T0g is in its robust form already.
       The first candidate with a-hat + R <= gamma C_S(t) + B(t) (Ratchet.step's test, up to GUARD_TOL) is executed and
       booked as A8 books an executed A_E(t): its [p_E(t), rent_E(t), Q(t)] in terms, Ratchet.step with its a-hat and
       R, T0gBound.record and commit of its evaluation, budget <- its R. A slot executed as A_E(t) is A8's slot bit for
       bit.
    4. If none passes, the guard records the failing step of A_E(t) (its terms and evaluation, Ratchet.step with its
       a-hat and R and force false, which fails on its own) and aborts exactly as A8 does (Guarded._abort: the
       wind-down, S thereafter). report()['guard']['forced'] and at_abort['forced'] therefore stay false; they are
       true only for the test-only abort_at, from which A8P aborts at once with A_E(t)'s forced step, as A8 does.
    The kept actions of a projected list keep their order in A_E(t). For an inner policy whose lists hold only Buys and
    Releases (A9, BL1 and BL5; the prototypes NBR and RCRb) the candidates are those of the prototype
    out/sublet_v2_dev/guard_allowance/projected.py, whose K0 (the inner's Releases plus a Release of every other held
    lease) is the same set of Releases.

    An inner policy that uses on_fast (condition C1 fails, so T0g is in its robust form at every slot; no inner id of
    PROJ_INNER_IDS does) receives the results of step 1 in the first fast slot of a projected slot, which on_fast
    recognizes by its non-empty results: after an empty executed list (P0 or K0 with no action) that fast slot has no
    results, nothing is remapped, and the inner receives step 1's results at the next slow slot. A8P passes on its fast
    actions only on the replicas that exist after the executed list: those of obs on leases that the list does not
    release and that it does not unload, and those that its accepted Buys, and its accepted Loads on leases it does not
    release, create. A fast action on any other replica (on a lease of a K0 Release, or an id the inner expects from a
    dropped Buy or Load) is dropped and counted (dropped_fast), since the engine would raise ActionError. After a slot
    executed as A_E(t) on_fast is A8's.

    Guarantees (design/sublet_v2.md §2.6; C3 §9, block 'The projected guard'). Remark R (PROVEN, audited in
    design/theory/audit_guard.md, 'Audit addendum (P6)', at Algorithm 1's allowance and at 'lb'; the bit-for-bit
    identity of the code is checked numerically, under the floating-point hypothesis (F) of C3 §9): for an inner policy
    E that is deterministic in its reset inputs and its calls, A8P around E is A8 around Proj(E), the policy of C3 §9's
    Definition R3, which holds E, its own SafeExpert (from an identical copy of S's generator), its own T0gBound and, at
    'lb', its own OnlineLB, computes B(t) and gamma C_S(t) + B(t) with Ratchet's float conversions, and proposes the
    first candidate of step 3 that passes, or A_E(t) when none passes or from abort_at on. At 'lb' A8 is
    ProjectedGuarded(project=False, allowance='lb', kappa=None), that is Guarded.act with the allowance served by
    _LBRatchet, since Guarded.PARAMS has no allowance. The two runs return equal lists at every slow and fast slot and
    abort at the same slot with the same failing step of A_E(t) (exact arithmetic; bit for bit under (F), checked
    numerically by tests/test_guard_projection.py::test_remark_r_identity, with test_remark_r_coverage on the paths that
    the audit found unobserved). Hence Theorem W(a)(b), PROVEN for A8, hold for A8P when E does not use on_fast (C1),
    with step (1) of its proof, ALG(t) + R(t) <= gamma C_S(t) + B(t) at every executed slot; they also follow directly
    from A8P's code, at either allowance and without (F) (C3 §9, Step 8: Lemma P.1 for the executed list, and the
    committed evaluation and budget of the list executed at u - 1). On core exports, under a lender that sells and ends
    no lease inside [s, s + D_k), G2 and G3(a)-(d) hold for A8P when E does not use on_fast and its lists hold only
    Releases and Buys of one replica with admission 1 (A9's do), since Proj(E)'s lists then do too and A8 around Proj(E)
    meets G2(b) after an abort by C3 §9, "A8's mode S on core exports" (PROVEN, audited, up to WD_TIE sum_u max(1, Q(u))
    over the adaptive wind-down slots, as for A8 in the module docstring's Guarantees); at 'lb' Corollary G3' gives G3
    with B <= LB' and the constant (1 + gamma) c(gamma') + 1. What is lost: G2(a) and G3(e) refer to Proj(E), and a run
    without an abort is E's alone iff no slot is projected; the price of the guard has no bound and is measured instead
    (H6).

    Proposition P (PROVEN, audited in the same section: (a)-(c), the Consequence and, under its three float hypotheses
    below, the code-level clause (d); proof in design/theory/c3_c4_c5_general.md §9; it uses neither Remark R nor
    Theorem W). Let A8P run on an instance with nonnegative stranding coefficients, loading charges and fallback prices
    (every instance of build_instance and from_core; instance.validate checks only shapes) with project true, test
    T0g, the reserve in the test, gamma >= 1, Algorithm 1's allowance or 'lb' (each nonnegative and nondecreasing in
    float64 too: C3 §9's fact F7; for 'lb' online_lb's module docstring), abort_at None and an inner policy whose lists
    consist of well-formed engine actions; let every slot before t be executed in mode E, T0gBound be in its bound form
    at t (robust_all false, robust_since None) and S follow FB at t. In exact arithmetic K0 has p = rent = R_K0 = 0,
    G_K0(t) = Q(t) and S_K0(t) <= R(t - 1) (both computed from the committed prev_d, prev_W and prev_lb), and with rhs =
    gamma C_S + B and tol = GUARD_TOL max(1, |rhs|),
        rhs(t) - a-hat_K0(t) - R_K0(t) = [rhs(t-1) - ALG(t-1) - R(t-1)] + [R(t-1) - S_K0(t)] + (gamma - 1) Q(t)
                                         + [B(t) - B(t-1)] + [Q(t) - G_K0(t)] >= -tol(t-1) - m(t-1),
    with tol(t-1) <= tol(t): if m(t - 1) = 0, K0 passes at t and A8P does not abort there. Lemma P.1 (PROVEN, audited in
    the same section): if on_unavailable equals the lender's (as drivers/run.py passes it) or the lender sells,
    T0gBound's soundness holds for whichever candidate A8P executes, so in exact arithmetic with the routing LP solved
    exactly m = 0 and a run in which S follows FB at every slot and T0g stays in bound form never aborts; in the code
    m(u) is at most the routing LP's tolerance, which reaches m through G and through S (the engine books stranding from
    the LP's served load), plus the rounding of ALG(u) and a-hat(u). Without that hypothesis C2 can fail with T0g still
    in bound form (tests/test_guard.py::test_t0g_refuse_first_refusal), and then K0 can fail by m(t - 1).
    Code-level clause (float64; Proposition P(d)). Under the same hypotheses, with C_S(t - 1) >= 0 in float64, no
    overflow and equal results of the two rounding reductions of T0gBound._served_ub at its calls at t - 1 and t, K0
    fails at t only if its excess X(t) = a-hat_K0(t) - lim(t) over the code's limit lim = rhs + GUARD_TOL max(1, |rhs|)
    satisfies 0 < X(t) <= m(t - 1) + (11 + 5k) u a-hat_K0(t), u = 2^-53, k = n + phi (J + 1) + 2 (clients, LLMs, fast
    slots per slow slot), with no use of the sale rule. The sources are G_K0 against Q, S_K0 against R(t - 1), the
    additions in C_S, a-hat and rhs, the comparison's rounding (a-hat + R and lim) and m(t - 1), which carries the
    rounding of ALG and a-hat and the routing LP's tolerance. An instrumented rerun of the run decides an abort at t_a
    under these hypotheses (C3 §9, 'Deciding an abort from one run', lists what it logs: the clause's terms at t_a - 1
    and t_a, slot t_a - 1's bookings by component and fast slot with the per-fast-slot G and S of its evaluation, and
    the engine's routing-LP calls in the fast slots of t_a - 1 and in the last fast slot of t_a - 2). It evaluates (R1)
    X(t_a) <= m(t_a - 1) + (11 + 5k) u a-hat_K0(t_a) and (R2) m(t_a - 1) <= q44_study.CERT_TOL max(1, ALG(t_a - 1))
    exactly. A booking of slot t_a - 1 is LP-explained if it is a routing, fallback or stranding booking of a fast slot
    f at which the engine solved a routing LP at f or at f - 1 (f - 1 may be the last fast slot of slot t_a - 2), and
    such a fast slot is an LP slot. x(f) is fast slot f's routing, fallback and stranding bookings minus G(f) + S(f),
    m_out = x0^+ + sum of x(f)^+ over the other fast slots (x0: the purchase, loading and rent bookings minus p + rent)
    and m_lp = sum of x(f)^+ over the LP slots; (T) says that the rerun's per-fast-slot G and S reproduce the
    evaluation's; theta = CERT_TOL max(1, ALG(t_a - 1)), theta_sep = 1e-12 max(1, ALG(t_a - 1)) (x9_prop_p.SEP). Five
    outcomes, decided in this order:
      refutation        of (d), if (R1) fails while C_S(t_a - 1) >= 0 in float64 and every logged value is finite;
                        of Lemma P.1, if (R2) fails under the sale-rule hypothesis, (T) holds and m_out > theta; both
                        can apply;
      undecided         no refutation, and (R1) fails, or (R2) fails under the sale-rule hypothesis without (T); a
                        logged value that is not finite also makes the abort undecided;
      C2 case           (R1) holds and (R2) fails without the sale-rule hypothesis (the C2 case of Lemma P.1's proof);
      routing-LP abort  (R1) holds, and either (R2) fails under the sale-rule hypothesis with (T) and m_out <= theta,
                        or (R2) holds, (T) holds and m_lp > theta_sep >= m_out;
      rounding abort    (R1) and (R2) hold and the condition of a routing-LP abort fails.
    tests/test_guard_projection.py checks K0's terms and the no-abort statement numerically on the full model, at
    Algorithm 1's allowances and at 'lb'; the K0 section of code/theory_checks/c3/check_guard.py (out/guard.txt) checks
    them on the core; code/sim/audit/x9_prop_p.py checks the clause and classifies its aborts with this rule, and
    x14_prop_p_lp_lb.py checks the rule on an emulated inexact routing LP and the float monotonicity of 'lb'.

    report() adds project; projection = {slots (projected slots), P1, P0, K0 (executed slots per candidate),
    dropped_buys and dropped_other (actions of A_E(t) dropped at projected slots: Buys, and actions of other types),
    guard_releases (K0's Releases of leases that A_E(t) does not release)}; candidates, the executed candidate per
    E-mode slot run-length encoded ([[name, first slot, length], ...]; 'E' at every executed slot with project false);
    dropped_fast (the four keys of Remark R(a); at 'alg1' the report is exactly that before the option). With 'lb' also
    allowance 'lb' and online_lb = {LB_T, Wk_T, B_T, n_groups} (OnlineLB.report at the last slot), B0 None (top level
    and guard.B0), and safe.B_curve is the OnlineLB's per-slot B(t) series (Guarded.report computes it from B_on, which
    holds only for 'alg1'). Otherwise A8P's report is A8's: for a run in which no slot before the abort (or no slot at
    all) is projected it equals A8's report of the same run, but for these keys. The information class is
    registry.info_class of A8 applied to A8P: online-I1 + a-priori N, with no BL0a (also with 'lb', whose W_k and LB'
    read only the view and the revealed demand)."""
    name = "A8P"
    PARAMS = {**Guarded.PARAMS, "inner": "A9", "project": True, "allowance": "alg1"}
    REFUSAL = "guard"                   # the reason of a dropped action in the inner's results (step 1)

    def __init__(self, **kw):
        p, _ = resolve_params(self.PARAMS, kw, "A8P", inputs=self.INPUTS)
        if not isinstance(p["project"], (bool, np.bool_)):
            raise PolicyError(f"A8P: project must be true or false, got {p['project']!r}")
        if p["project"] and p["test"] != "T0g":
            raise PolicyError("A8P: project true needs test 'T0g' (the candidates are evaluated with T0gBound)")
        if not isinstance(p["allowance"], str) or p["allowance"] not in ALLOWANCES:
            raise PolicyError(f"A8P: allowance must be one of {list(ALLOWANCES)}, got {p['allowance']!r}")
        if p["allowance"] == "lb" and p["kappa"] is not None:
            raise PolicyError("A8P: allowance 'lb' needs kappa None (B = min{W_k, LB'} is not capped by kappa B_on), "
                              f"got kappa {p['kappa']!r}")
        inner, ip = p["inner"], p["inner_params"]
        inner_id = None
        if not isinstance(inner, Policy):
            if inner not in PROJ_INNER_IDS:
                raise PolicyError(f"A8P: inner must be one of {list(PROJ_INNER_IDS)}, got {inner!r}")
            ip = {} if ip is None else ip
            if not isinstance(ip, dict):
                raise PolicyError(f"A8P: inner_params must be an object, got {type(ip).__name__}")
            inner_id = inner
            kw = {**kw, "inner": self._proj_inner_class(inner)(**dict(ip)), "inner_params": {}}
        super().__init__(**kw)
        if inner_id is not None:            # Guarded saw an instance: the record keeps the id and its parameters
            self.inner_id = inner_id
            self._p["inner"], self._p["inner_params"] = inner_id, copy.deepcopy(dict(ip))
        self.allowance_rule = p["allowance"]
        if self.allowance_rule == "alg1":   # params() and the records as before the option (class docstring)
            self._p.pop("allowance", None)

    @staticmethod
    def _proj_inner_class(inner: str):
        """The policy class of an inner id of A8P: A9 (sublet.algos.a9, imported on first use), else A8's."""
        if inner == "A9":
            from .a9 import NoticeCriticalRatio
            return NoticeCriticalRatio
        return _inner_class(inner)

    # -------------------------------------------------------- reset
    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        self._map: Optional[tuple] = None        # after a projected slot: (inner index per executed action, dropped)
        self._fast_ok: set[int] = set()          # replicas that exist after a projected list (on_fast)
        self._fast_rel: set[int] = set()         # the leases that list releases
        self.cands: list[str] = []               # the executed candidate per E-mode slot
        self.projection = {"slots": 0, "P1": 0, "P0": 0, "K0": 0, "dropped_buys": 0, "dropped_other": 0,
                           "guard_releases": 0}
        self.dropped_fast = 0
        self.olb: Optional[OnlineLB] = None      # allowance 'lb': B(t) = min{W_k(t), LB'(t)}, through _LBRatchet
        if self.allowance_rule == "lb":
            self.olb = OnlineLB(view)
            rt = self.ratchet
            self.ratchet = _LBRatchet(self.olb, rt.gamma, rt.test, rt.B0)

    # -------------------------------------------------------- candidates (step 3)
    def candidates(self, obs: SlowObs, acts: list) -> list:
        """The candidate lists of step 3 for A_E(t) = acts, in order: [(name, list, src)], src[i] the index in acts of
        list[i] (None for a Release that the guard adds)."""
        leases = {int(lid) for lid in obs.leases}
        reps = {int(rid) for rid, rv in obs.replicas.items() if int(rv.lease_id) in leases}

        def in_obs(a) -> bool:
            if isinstance(a, (Release, Load)):
                return int(a.lease_id) in leases
            if isinstance(a, (Unload, SetAdmission, Drain)):
                return int(a.replica_id) in reps
            return False
        buys = [i for i, a in enumerate(acts) if isinstance(a, Buy)]
        minus = [i for i, a in enumerate(acts) if not isinstance(a, Buy) and in_obs(a)]
        out = [("E", acts, list(range(len(acts))))]
        nb = len(buys)
        if nb >= 2:
            for n in sorted({nb - 1, nb // 2, nb // 4, 1} - {0, nb}, reverse=True):
                idx = sorted(buys[:n] + minus)
                out.append(("P1", [acts[i] for i in idx], idx))
        if nb >= 1 or len(minus) < len(acts):
            out.append(("P0", [acts[i] for i in minus], minus))
        own: dict[int, int] = {}                 # held lease -> index of the inner's first Release of it
        for i, a in enumerate(acts):
            if isinstance(a, Release) and int(a.lease_id) in leases:
                own.setdefault(int(a.lease_id), i)
        k0 = sorted(leases)
        out.append(("K0", [acts[own[lid]] if lid in own else Release(lid) for lid in k0], [own.get(lid) for lid in k0]))
        return out

    def _evaluate(self, obs: SlowObs, lst: list, Q: float) -> tuple:
        """(a-hat, R, p_E, rent_E, T0gBound evaluation) of an action list at slot t, as Guarded.act computes them."""
        pE, rent = slot_terms(self.view, obs, lst)
        ev = self.t0g.evaluate(obs, lst, Q)
        R = ev["reserve"] if self._p["reserve"] else 0.0
        return self.ratchet.test_value(obs.cost_so_far, pE, rent, ev["G"] + ev["S"]), R, pE, rent, ev

    def _inner_results(self, results) -> list:
        """The results of the last executed (projected) list in the inner's indices (step 1)."""
        src, dropped = self._map
        out = [ActionResult(src[r.index], r.action, r.ok, r.lease_id, r.replica_ids, r.reason)
               for r in results if 0 <= r.index < len(src) and src[r.index] is not None]
        out += [ActionResult(i, a, False, None, (), self.REFUSAL) for i, a in dropped]
        out.sort(key=lambda r: r.index)
        return out

    def _projected(self, obs: SlowObs, acts: list, name: str, lst: list, src: list) -> None:
        """Counts of a projected slot, and the state that step 1 and on_fast read."""
        pr = self.projection
        pr["slots"] += 1
        pr[name] += 1
        used = {i for i in src if i is not None}
        dropped = [(i, a) for i, a in enumerate(acts) if i not in used]
        nb = sum(1 for _i, a in dropped if isinstance(a, Buy))
        pr["dropped_buys"] += nb
        pr["dropped_other"] += len(dropped) - nb
        pr["guard_releases"] += sum(1 for i in src if i is None)
        self._map = (list(src), dropped)
        if self.wants_fast:
            rel = {int(a.lease_id) for a in lst if isinstance(a, Release)}
            unl = {int(a.replica_id) for a in lst if isinstance(a, Unload)}
            self._fast_rel = rel
            self._fast_ok = {int(rid) for rid, rv in obs.replicas.items()
                             if int(rv.lease_id) in obs.leases and int(rv.lease_id) not in rel and int(rid) not in unl}

    # -------------------------------------------------------- act
    def act(self, obs: SlowObs) -> list:
        if self.olb is not None:                             # allowance 'lb': B(t) of this slot, before any use
            self.olb.step(obs)
        if self.mode != "E" or not self._p["project"]:
            return super().act(obs)
        t = int(obs.t)
        self.alg_prev.append(float(obs.cost_so_far))
        io = inner_obs(obs)                                  # a private copy (audit F2): the test reads obs
        if self._map is not None:
            io.results = self._inner_results(obs.results)    # step 1
        acts = list(self.inner.act(io))
        sx, rt, tb = self.sx, self.ratchet, self.t0g
        sx.step(obs)                                         # step 2
        B_t = rt.allowance(sx.B_on)
        Q = sx.fb_inc
        tb.begin(obs)
        ab = self._p["abort_at"]
        force = ab is not None and t >= int(ab)
        rhs = rt.gamma * float(sx.C_S) + float(B_t)
        lim = rhs + rt.tol * max(1.0, abs(rhs))              # Ratchet.step's test
        pick, ev_E = None, None
        for name, lst, src in ([] if force else self.candidates(obs, acts)):     # step 3
            e = self._evaluate(obs, lst, Q)
            if name == "E":
                ev_E = e
            if e[0] + e[1] <= lim:
                pick = (name, lst, src, e)
                break
        self._map = None
        if pick is None:                                     # step 4: A_E(t)'s failing step, then A8's abort
            a_hat, R, pE, rent, ev = ev_E if ev_E is not None else self._evaluate(obs, acts, Q)
            self.terms.append([pE, rent, Q])
            tb.record(ev)
            if rt.step(t, a_hat, sx.C_S, B_t, alg_prev=obs.cost_so_far, force=force, reserve=R):
                raise PolicyError(f"A8P: slot {t}: A_E(t) failed the test and then passed it")
            return self._abort(obs)
        name, lst, src, (a_hat, R, pE, rent, ev) = pick
        self.terms.append([pE, rent, Q])
        tb.record(ev)
        if not rt.step(t, a_hat, sx.C_S, B_t, alg_prev=obs.cost_so_far, reserve=R):
            raise PolicyError(f"A8P: slot {t}: candidate {name} passed the test and then failed it")
        tb.commit(ev)
        self.budget = float(R)
        self.modes.append("E")
        self.cands.append(name)
        if name != "E":
            self._projected(obs, acts, name, lst, src)
        return lst

    def on_fast(self, obs: FastObs) -> list:
        if self._map is None:
            return super().on_fast(obs)
        if obs.results:                                      # the first fast slot of a projected slot
            for r in obs.results:
                if r.ok and (isinstance(r.action, Buy)
                             or (isinstance(r.action, Load) and int(r.lease_id) not in self._fast_rel)):
                    self._fast_ok.update(int(x) for x in r.replica_ids)
            obs = dataclasses.replace(obs, results=self._inner_results(obs.results))
        acts = list(self.inner.on_fast(obs) or [])
        keep = [a for a in acts if not isinstance(a, (Drain, SetAdmission)) or int(a.replica_id) in self._fast_ok]
        self.dropped_fast += len(acts) - len(keep)
        return keep

    # -------------------------------------------------------- report
    def report(self) -> dict:
        rep = super().report()
        if getattr(self, "sx", None) is None:
            return rep
        names = self.cands if self._p["project"] else ["E"] * self.modes.count("E")
        rle: list[list] = []
        for t, w in enumerate(names):
            if rle and rle[-1][0] == w:
                rle[-1][2] += 1
            else:
                rle.append([w, t, 1])
        rep.update(project=bool(self._p["project"]), projection=dict(self.projection), candidates=rle,
                   dropped_fast=int(self.dropped_fast))
        if self.olb is not None:                             # 'lb' only: at 'alg1' the report is that before the option
            rep["allowance"] = self.allowance_rule
            rep["B0"] = rep["guard"]["B0"] = None            # B0 is unused at 'lb' (class docstring)
            rep["safe"]["B_curve"] = list(self.olb.B_series)     # B(t) at every slot: the OnlineLB's, not from B_on
            rep["online_lb"] = self.olb.report()
        return rep


__all__ += ["PROJ_INNER_IDS", "ALLOWANCES", "ProjectedGuarded"]
