"""X9: audit of Lemma P.1 and Proposition P (the projected guard A8P, class ProjectedGuarded of sublet/algos/guard.py;
design/theory/c3_c4_c5_general.md §9, written 2026-11-02, with its float64 code-level clause), the full-model part of
the audit addendum of step P6 (design/sublet_v2.md §5 and its §8.1 row for check_guard.py), with the P6 audit's
corrections: the abort classification of PROP_P-F1 and F3, the allowance 'lb' (PROP_P-F2), the labels and the richer
edge scan of PROP_P-F5.

(a) Proposition P(a)-(c) and Lemma P.1 on A8P runs: project true, test T0g with the reserve in the test, safe 'fb',
    gamma in {1, 1+1/sqrt2}, abort_at None, the lender's sale rule passed as on_unavailable (as drivers/run.py passes
    it), around the random inner policies of tests/test_guard.py (_RandomInner: every slow-slot action type;
    _OwnListInner: also actions on objects of its own list, evaluated in T0g's robust form at their slot) on the eight
    variants of _rich_instance (every stranding coefficient positive; kappa_infinite alternating), the nine lender
    models of x2_random_search.py (eager, trace, iid_step, adaptive, safe_site, correlated, trace under I2, 'refuse'
    under I1 and I2), five allowances (constant B0 0.3 and 3.0, capped 'auto' with kappa 10, capped 5.0 with kappa 1,
    and 'lb', B = min{W_k, LB'} of algos/online_lb.py) and auto_drain alternating. At every E-mode slot t at which T0g
    is in its bound form after begin (robust_all false, robust_since None) and S follows FB, the script recomputes,
    independently of T0gBound and in fractions.Fraction on the float inputs: Q(t) and G_K0(t) from the instance's
    demand; K0 (a Release of every lease of obs) and its purchase and rent terms from obs; S_K0(t) and R(t-1) from
    T0gBound's committed state (prev_d, prev_W, prev_lb), with UB_c by the class docstring's definition written here
    (served_ub); B(t) from the instance (B_on and C^min recomputed; B0 'auto' read from the guard; at 'lb' the OnlineLB
    replayed offline on the instance's demand, a check of its wiring and non-anticipation, the independent LB' oracle
    being X11); C_S(t) as the exact sum of Q. It checks (a): p = rent = R_K0 = 0 and K0 releases exactly obs's leases,
    G_K0 = Q and S_K0 <= R(t-1) exactly; the code's values (slot_terms and T0gBound.evaluate on K0, the guard's Q, C_S,
    B and recorded R(t-1)) agree with the recomputation to 1e-12 relative; identity (b) holds exactly (its five brackets
    from the recomputation, the guard's float B and ALG(t-1) = obs.cost_so_far), with the second, third and fourth
    brackets >= 0 and the fifth = 0 exactly and the first >= -tol(t-1) - m(t-1) (m(t-1) = max{0, ALG(t-1) - a-hat(t-1)}
    with the guard's a-hat) up to 1e-12 max(1,|rhs|) of rounding; the exact K0 margin rhs(t) + tol(t) - a-hat_K0(t) -
    R_K0(t) >= -m(t-1) up to the same rounding; and K0 passes the code's own float64 comparison. Lines labelled 'impl.'
    hold by construction of this script's exact formulas (the identity, G_K0 == Q, S_K0 <= R(t-1), brackets 2 and 5);
    they check the implementation, not the claim. Per run, the guard's float B(t) is >= 0 and nondecreasing exactly (F7
    at Algorithm 1's allowances, PROP_P-F2's argument at 'lb', where the OnlineLB's LB', W_k and B series are checked
    the same way); the instance class (stranding coefficients, W_f, loading charges beta and beta-tilde and fallback
    prices q_j >= 0, finite nonnegative demand; PROP_P-F4) enters P's hypotheses. Lemma P.1 (with the sale-rule
    hypothesis, which these runs meet): ALG(t) <= a-hat(t) at every executed slot, whichever candidate is executed, up
    to CERT_TOL = 1e-9 max(1, ALG(t)) (ALG from the ledger). Every abort is classified by the clause of (b) after an
    instrumented rerun; a 'refutation' or 'undecided' counts as a violation, and in a run in which S follows FB and T0g
    stays in its bound form every abort under P's hypotheses must be a rounding or routing-LP abort.
(b) The clause "Deciding an abort from one run", corrected (P6 audit, PROP_P-F1, F3): an instrumented rerun (ClauseProbe
    under trace_engine: the ledger's bookings by component and fast slot, the engine's routing-LP calls per fast slot,
    every candidate's a-hat + R, and the executed candidate's G and S per fast slot, recomputed with T0gBound's own
    helpers in evaluate's order and required to reproduce evaluate's G and S, bit for bit in the bound form and to REL
    in the per-list robust form) must reproduce the abort bit for bit (t_a and the guard's float records); it logs the
    clause's float64 values in hexadecimal, computes X(t_a), m(t_a-1) and the terms of the clause's identity in
    Fraction, checks that the terms add up to X(t_a) exactly, and evaluates (R1) X(t_a) <= m(t_a-1) + (11+5k) u
    a-hat_K0(t_a), k = n + phi(J+1) + 2, u = 2^-53, and (R2) m(t_a-1) <= CERT_TOL max(1, ALG(t_a-1)). Where the excess
    lies: x0 = slot t_a-1's purchase, loading and rent bookings minus the executed candidate's p + rent; x(f) = the
    routing, fallback and stranding bookings of fast slot f minus G(f) + S(f); an LP slot is a fast slot f of slot t_a-1
    at which the engine solved a routing LP at f or at f-1 (f-1 may be the last fast slot of slot t_a-2); m_out = x0^+ +
    sum of x(f)^+ over the other fast slots, m_lp = sum of x(f)^+ over the LP slots; (T): the per-fast-slot terms
    reproduce evaluate's G and S; (V): C_S(t_a-1) >= 0 in float and every logged value finite. Under P's hypotheses
    (with the instance class) the outcome is decided in this order: 'refutation' of (d) if (R1) fails under (V), of
    Lemma P.1 if (R2) fails under the sale-rule hypothesis and (T) with m_out > CERT_TOL max(1, ALG(t_a-1)) (both can
    apply); else 'undecided' if (R1) fails, or (R2) fails under the sale-rule hypothesis without (T) (a logged value
    that is not finite makes it 'undecided'); else the 'C2 case' if (R2) fails without the sale-rule hypothesis; else
    'routing-LP abort' if (R2) fails, or if (R2) holds, (T) holds and m_lp > SEP max(1, ALG(t_a-1)) >= m_out (SEP =
    1e-12); else 'rounding abort'. Outside P's hypotheses an abort is not classified. Each classified abort is printed
    with the numbers that decided it. Exercised on three float edge scans: the scenario of C3 §9
    (tests/fixtures.toy_instance, n = J = phi = 1, L0's load time 0 and demand scaled by s, lender trace/I1/'sell', the
    option 'sell', safe 'fb', gamma 1, a scripted inner that buys at L0 at slot 2 and releases its leases at slot 3, a
    constant B0 in 81 steps of one ulp around the value that puts slot 2's executed list at its limit), and two scans on
    n = 16 clients of J = 2 LLMs (the P6 auditor's B2: phi = 10, mu_kv = mu_fl = 0 so that slot 0's bound is tight; B3:
    phi = 1, every stranding coefficient positive; a scripted inner that buys one protected replica per LLM at slot 0
    and releases its leases at slot 1, B0 in 81 ulp steps around slot 0's limit), where G_K0 - Q is nonzero at aborts:
    every abort must be a rounding abort, and the scans report the aborts with G_K0 - Q != 0 and the least (R1) slack as
    a share of (11+5k) u a-hat_K0(t_a).
(c) The C2 negative control: the setup of tests/test_guard.py::test_t0g_refuse_first_refusal (toy with L0's load
    time 0 and announcement slots 2 and 3, lender trace with on_unavailable 'refuse', I1 and I2, a Buy at L0 at slot
    2) under A8P with safe 'fb', gamma 1 and B0 = a-hat(2) + R(2) - C_S(2) of the run with B0 = 1e3 (slot 2's purchase
    at its limit), with the option not passed (None) or wrong ('sell'): each run must show an unforced abort with S on
    FB and T0g in its bound form (cautious), explained by m(t_a-1) > 0, with (R1) holding and (R2) failing (the C2
    case); the same runs with the option passed ('refuse') must not abort. A control that fails to show this is a
    violation.

Usage: x9_prop_p.py [n_seeds] (default 24; part (a) runs seeds 0..n_seeds-1, 144 runs per seed). Audit of the
full-model guard; code/sim/audit/, run by run_all.sh (step x9), output code/sim/out/audit_fm/x9_out.txt; x14 uses its
clause on an emulated inexact routing LP. Exit status 1 on a violation of a checked claim, when the C2 control fails
to produce its abort, or when an abort is classified 'refutation' or 'undecided'."""
import contextlib
import dataclasses
import math
import sys
import time
from collections import Counter
from fractions import Fraction as F

import numpy as np

import audit_env  # noqa: F401
from audit_env import TG
from fixtures import CONFIGS, load_json, toy_instance
from sublet import engine as _eng
from sublet import ledger as _led
from sublet.algos import online_lb
from sublet.algos.a5 import G2
from sublet.algos.guard import GUARD_TOL, ProjectedGuarded, slot_terms
from sublet.engine import EngineConfig, simulate
from sublet.experiments.q44_study import CERT_TOL
from sublet.instance import build_instance, with_demand
from sublet.policies.base import Policy
from sublet.types import Buy, LenderModel, Release, Stranding

U = F(1, 2 ** 53)
MX = {}                # largest values seen (informational)
REL = 1e-12            # agreement of the code's floats with the exact recomputation (rounding is ~1e-15 here)
RND = 1e-12            # rounding allowance of the margin checks, times max(1, |rhs|)
SEP = 1e-12            # rounding allowance of the separation of an LP-caused excess, times max(1, ALG(t_a-1))
STRAND = ("stranding_kv", "stranding_fl", "stranding_fb", "stranding_pi")
FAST_COMPS = ("routing", "fallback") + STRAND
SLOW_COMPS = ("lease_prepaid", "lease_rent", "loading")
MODELS = {
    "eager": {"schedule": "eager"},
    "trace": {"schedule": "trace"},
    "iid": {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.3}},
    "adaptive": {"schedule": "adaptive"},
    "safe": {"schedule": "safe_site", "params": {"D_slots": 2, "k": 2, "Phi": None}},
    "corr": {"schedule": "correlated", "params": {"p_sh": 1.0, "groups": "all"}},
    "traceI2": {"schedule": "trace", "information": "I2"},
    "refuse": {"schedule": "trace", "on_unavailable": "refuse"},
    "refuseI2": {"schedule": "trace", "on_unavailable": "refuse", "information": "I2"},
}
ALLOWS = ({"B0": 0.3, "kappa": None}, {"B0": 3.0, "kappa": None}, {"B0": "auto", "kappa": 10.0},
          {"B0": 5.0, "kappa": 1.0}, {"allowance": "lb", "kappa": None})
OUTCOMES = ("rounding abort", "routing-LP abort", "refutation", "undecided")


def alabel(allow):
    """Short label of an allowance of ALLOWS."""
    if allow.get("allowance") == "lb":
        return "allowance=lb"
    return f"B0={allow['B0']} kappa={allow['kappa']}"


# ------------------------------------------------------------------------------------------ bookkeeping
class Checks:
    """name -> [evals, violations, min slack, where of min, first violations (<= 4)]. slack >= 0 is fine."""

    def __init__(self):
        self.d = {}

    def add(self, name, slack, where, ok=None):
        e = self.d.setdefault(name, [0, 0, math.inf, None, []])
        e[0] += 1
        slack = float(slack)
        if slack < e[2]:
            e[2], e[3] = slack, where
        bad = (slack < 0) if ok is None else (not ok)
        if bad:
            e[1] += 1
            if len(e[4]) < 4:
                e[4].append((where, slack))

    def lines(self):
        w = max(len(k) for k in self.d)
        out = [f"  {'check'.ljust(w)}  {'evals':>7} {'viol':>5} {'min slack':>11}  at min"]
        for k in sorted(self.d):
            e = self.d[k]
            out.append(f"  {k.ljust(w)}  {e[0]:7d} {e[1]:5d} {e[2]:11.3e}  {e[3]}")
            for wh, s in e[4]:
                out.append(f"      VIOLATION at {wh}: slack {s:.6e}")
        return out

    def nviol(self):
        return sum(e[1] for e in self.d.values())


# ------------------------------------------------------------------------------------------ probes and tracing
class EdgeScript(Policy):
    """The float edge scenario's inner policy: a Buy of one replica at site 0 (L0), contract 0, LLM 0 at slot 2, and a
    Release of every held lease at slot 3."""
    name = "edge"

    def act(self, obs):
        if obs.t == 2:
            return [Buy(0, 0, 0, 1)]
        if obs.t == 3:
            return [Release(int(lid)) for lid in sorted(obs.leases)]
        return []


class EdgeBuy0(Policy):
    """The inner policy of the n = 16 edge scans: one protected replica per LLM (site 2 'P', contract 2) bought at slot
    0, and a Release of every held lease at slot 1."""
    name = "edgebuy0"

    def act(self, obs):
        if obs.t == 0:
            return [Buy(2, 2, j, 1) for j in range(len(self.view.llms))]
        if obs.t == 1:
            return [Release(int(lid)) for lid in sorted(obs.leases)]
        return []


class BuyAt2(Policy):
    """The C2 control's inner policy (test_t0g_refuse_first_refusal): a Buy at L0 at slot 2 and nothing else."""
    name = "buy2"

    def act(self, obs):
        return [Buy(0, 0, 0, 1)] if obs.t == 2 else []


class KProbe(ProjectedGuarded):
    """A8P that records at every E-mode slot, after T0gBound.begin and before any evaluation is committed: the guard's
    float64 values of the slot (ALG(t-1), Q, C_S, B, y, rhs, tau, lim, the followed expert, T0g's form), K0's code
    evaluation (slot_terms and T0gBound.evaluate, both stateless), the committed state (prev_d, prev_W, prev_lb) and
    the budget R(t-1); after the slot, the executed (or failing) step's a-hat, R, sigma = fl(a-hat + R), terms and
    candidate. Nothing it records changes the run."""

    def reset(self, view, rng):
        super().reset(view, rng)
        self.log = {}

    def candidates(self, obs, acts):
        c = super().candidates(obs, acts)
        t = int(obs.t)
        sx, rt, tb = self.sx, self.ratchet, self.t0g
        k0 = c[-1][1]
        Q = float(sx.fb_inc)
        pE, rent = slot_terms(self.view, obs, k0)
        ev = tb.evaluate(obs, k0, Q)
        B = float(rt.allowance(sx.B_on))
        y = rt.gamma * float(sx.C_S)
        rhs = y + B
        tau = rt.tol * max(1.0, abs(rhs))
        e = dict(t=t, alg1=float(obs.cost_so_far), Q=Q, CS=float(sx.C_S), B=B, y=y, rhs=rhs, tau=tau, lim=rhs + tau,
                 followed=sx.followed, robust_all=bool(tb.robust_all), robust_since=tb.robust_since,
                 cautious_since=tb.cautious_since, k0=list(k0), k0_p=pE, k0_rent=rent, k0_G=float(ev["G"]),
                 k0_S=float(ev["S"]), k0_R=float(ev["reserve"]), k0_form=ev["form"],
                 k0_ahat=rt.test_value(obs.cost_so_far, pE, rent, ev["G"] + ev["S"]), budget=float(self.budget),
                 prev_d=tb.prev_d.copy(), prev_W=tb.prev_W.copy(), prev_lb=tb.prev_lb.copy(),
                 obs_leases=sorted(int(x) for x in obs.leases), demand=np.array(obs.demand, dtype=np.float64))
        self.log[t] = e
        self._hook(obs, c, e)
        return c

    def _hook(self, obs, c, e):
        pass

    def act(self, obs):
        t = int(obs.t)
        out = super().act(obs)
        e = self.log.get(t)
        if e is not None and "mode" not in e:
            rt = self.ratchet
            e["mode"] = "abort" if rt.t_a == t else "E"
            e["ahat"], e["R"] = float(rt.a_hat[-1]), float(rt.reserve[-1])
            e["sigma"] = e["ahat"] + e["R"]
            e["p"], e["rent"] = float(self.terms[-1][0]), float(self.terms[-1][1])
            if e["mode"] == "E":
                e["name"] = self.cands[-1]
                e["G"], e["S"] = float(self.t0g.G[-1]), float(self.t0g.S[-1])
        return out


def fast_terms(tb, obs, lst, ev):
    """Per-fast-slot terms of T0gBound.evaluate for the list lst at slot obs.t (ev its evaluation), computed with
    T0gBound's own helpers (_replicas, _route, _served_lb, _served_ub) in evaluate's order: ([G(f) Δf/60], [S(f)]) as
    Fractions of the float terms that evaluate adds, and whether they reproduce ev (bound form: the float accumulations
    equal ev's G and S bit for bit; robust form, G(f) = Q(f) and S(f) = sum_c dh_c(f) kappa'_c a_c: to REL)."""
    phi, Df, n, J, m = tb.phi, tb.Df, tb.n, tb.J, tb.m
    d = np.asarray(obs.demand, dtype=np.float64).reshape(n, phi)
    dprev = np.concatenate([tb.prev_d[:, None], d[:, :-1]], axis=1)
    dh = np.minimum(dprev, d)
    if ev["form"] != "bound":
        coef = tb.kap * tb.any_arc
        Gf = [sum((F(float(tb.q[tb.cl[c]])) * F(float(d[c, i])) for c in range(n)), F(0)) * F(Df) / 60
              for i in range(phi)]
        Sf = [sum((F(float(dh[c, i] * coef[c])) for c in range(n)), F(0)) for i in range(phi)]
        ok = rel(sum(Gf, F(0)), ev["G"]) <= REL and rel(sum(Sf, F(0)), ev["S"]) <= REL
        return Gf, Sf, ok
    reps, _cnt, _nunc = tb._replicas(obs, list(lst))
    Wb, Wc, Wh = np.zeros((phi, J, m)), np.zeros((phi, J, m)), np.zeros((phi, J, m))
    drop = np.zeros((phi, J), dtype=bool)
    drop[0] = (tb.prev_W > 0).any(axis=1)
    for (j, l, _lid, inB, lo, hi) in reps:
        Wb[:, j, l] += np.where(inB, lo, 0.0)
        Wc[:, j, l] += lo
        Wh[:, j, l] += hi
        if phi > 1:
            drop[1:, j] |= hi[:-1] > lo[1:]
    G = S = 0.0
    Gf, Sf = [], []
    Wprev, lbprev = tb.prev_W, tb.prev_lb
    for i in range(phi):
        di = d[:, i]
        gi = si = F(0)
        for j in range(J):
            v = tb._route(j, di, Wb[i, j]) * Df / 60.0
            G += v
            gi += F(v)
        if tb.has_strand:
            lbi = np.zeros(n)
            for j in range(J):
                cs = tb.clients_of[j]
                if len(cs) == 0:
                    continue
                lb = tb._served_lb(j, di, Wc[i, j], Wh[i, j])
                lbi[cs] = lb
                e = np.minimum(dh[cs, i], tb._served_ub(j, dprev[:, i], Wprev[j], lbprev))
                if not np.any(e > 0):
                    continue
                Dj = 1.0 if drop[i, j] else 0.0
                v = float(np.sum((tb.mu_kv[j] + tb.mu_fl[j] * Dj) * e
                                 + (tb.mu_fb[j] + tb.pi_W[j] * Dj) * np.maximum(e - lb, 0.0)))
                S += v
                si += F(v)
            lbprev = lbi
        Wprev = Wh[i]
        Gf.append(gi)
        Sf.append(si)
    return Gf, Sf, (G == ev["G"] and S == ev["S"])


class ClauseProbe(KProbe):
    """KProbe that also evaluates every candidate of the slot (a-hat + R) and, for the candidate that the slot's test
    executes, G and S per fast slot (fast_terms), for the clause's log; evaluate is stateless, so the run is
    unchanged."""

    def _hook(self, obs, c, e):
        sx, rt, tb = self.sx, self.ratchet, self.t0g
        Q = float(sx.fb_inc)
        rows, evs = [], []
        for name, lst, _src in c:
            pE, rent = slot_terms(self.view, obs, lst)
            ev = tb.evaluate(obs, lst, Q)
            ah = rt.test_value(obs.cost_so_far, pE, rent, ev["G"] + ev["S"])
            rows.append(dict(name=name, sigma=ah + float(ev["reserve"]), ahat=ah, R=float(ev["reserve"]),
                             p=pE, rent=rent, G=float(ev["G"]), S=float(ev["S"]), form=ev["form"]))
            evs.append((lst, ev))
        e["cands"] = rows
        e["pick"] = next((i for i, r in enumerate(rows) if r["sigma"] <= e["lim"]), None)
        if e["pick"] is not None:
            lst, ev = evs[e["pick"]]
            e["Gf"], e["Sf"], e["fast_ok"] = fast_terms(tb, obs, lst, ev)


@contextlib.contextmanager
def trace_engine():
    """Records the ledger's bookings (component, slow slot, fast slot or None for the slow step, USD) and the engine's
    routing-LP calls per fast slot, by wrapping Engine._slow_step, Engine._fast_step, Engine._route_lp and Ledger.add
    (each wrapper calls the original with the same arguments); restored on exit."""
    E, L = _eng.Engine, _led.Ledger
    o_slow, o_fast, o_lp, o_add = E._slow_step, E._fast_step, E._route_lp, L.add
    book, lp, cur = [], Counter(), {"f": None}

    def slow(self, t):
        cur["f"] = None
        return o_slow(self, t)

    def fast(self, t, f, results):
        cur["f"] = int(f)
        try:
            return o_fast(self, t, f, results)
        finally:
            cur["f"] = None

    def route_lp(self, *a, **k):
        lp[cur["f"]] += 1
        return o_lp(self, *a, **k)

    def add(self, component, t_slow, usd):
        book.append((component, int(t_slow), cur["f"], float(usd)))
        return o_add(self, component, t_slow, usd)
    E._slow_step, E._fast_step, E._route_lp, L.add = slow, fast, route_lp, add
    try:
        yield book, lp
    finally:
        E._slow_step, E._fast_step, E._route_lp, L.add = o_slow, o_fast, o_lp, o_add


def run_a8p(inst, lm, inner, kw, ad=False, probe=KProbe, trace=False):
    pol = probe(inner=inner, project=True, test="T0g", safe="fb", **kw)
    cfg = EngineConfig(auto_drain=ad)
    if trace:
        with trace_engine() as (book, lp):
            res = simulate(inst, pol, LenderModel(**lm), cfg, policy_seed=0)
        return res, pol, book, lp
    return simulate(inst, pol, LenderModel(**lm), cfg, policy_seed=0), pol, None, None


def guard_records(res):
    g = res.metrics["policy"]["guard"]
    return (res.metrics["policy"]["t_a"], tuple(float(x).hex() for k in ("a_hat", "rhs", "reserve", "C_S", "B")
                                                for x in g[k]))


def instance_class_ok(view, demand=None):
    """PROP_P-F4 and C3 §9's instance class of Proposition P: stranding coefficients, W_f, the loading charges beta and
    beta-tilde and the fallback prices q_j are >= 0 (NaN and inf allowed: unavailable entries); with demand (the
    instance's, (n, T_fast)), also finite and >= 0."""
    st = view.stranding
    arrs = (st.mu_kv_usd, st.mu_fl_usd, st.mu_fb_usd, st.pi_usd_per_min, [st.W_f_min], view.beta_usd,
            view.beta_tilde_usd, [x.q_usd_per_h for x in view.llms])
    ok = all(not np.any(np.asarray(a, dtype=np.float64) < 0) for a in arrs)
    if demand is not None:
        d = np.asarray(demand, dtype=np.float64)
        ok = ok and bool(np.all(np.isfinite(d))) and not np.any(d < 0)
    return ok


# ------------------------------------------------------------------------------------------ the clause
def clause(pol, inst, lender_onu, book, lp):
    """'Deciding an abort from one run' (C3 §9, as corrected by the P6 audit, PROP_P-F1 and F3) for the abort of an
    instrumented run (ClauseProbe, trace_engine). Returns the outcome (cls), the numbers that decided it (why) and the
    clause's log; 'trace' holds slot t_a-1's bookings, per-fast-slot terms and routing-LP calls (x14 applies the
    pre-P6 rule to them)."""
    ta = pol.ratchet.t_a
    e = pol.log[ta]
    p1 = pol.log.get(ta - 1) if ta >= 1 else None
    g = F(pol.ratchet.gamma)
    gr = inst.grid
    phi = gr.phi
    z = 0.0
    if p1 is not None:
        A2, ah1, R1v, sig1 = p1["alg1"], p1["ahat"], p1["R"], p1["sigma"]
        CS1, B1, y1, rhs1, tau1, lim1 = (p1[k] for k in ("CS", "B", "y", "rhs", "tau", "lim"))
    else:
        A2 = ah1 = R1v = sig1 = CS1 = B1 = y1 = rhs1 = tau1 = lim1 = z
    ALG1, Q = e["alg1"], e["Q"]
    CS, B, y, rhs, tau, lim = (e[k] for k in ("CS", "B", "y", "rhs", "tau", "lim"))
    ak, G, S, RK = e["k0_ahat"], e["k0_G"], e["k0_S"], e["k0_R"]
    hyp = (e["followed"] == "FB" and not e["robust_all"] and e["robust_since"] is None
           and pol._p["abort_at"] is None and pol.ratchet.gamma >= 1.0 and pol._p["project"]
           and pol._p["test"] == "T0g" and pol._p["reserve"] and RK == 0.0
           and instance_class_ok(pol.view, inst.clients.demand))
    sale = pol.on_unavailable == lender_onu or lender_onu == "sell"
    k = inst.n + phi * (inst.J + 1) + 2
    # slot t_a-1: bookings by component and fast slot, the executed candidate's G and S per fast slot, LP calls
    t1 = ta - 1
    bk = {}
    for comp, ts, f, usd in book:
        if ts == t1:
            bk[(comp, f)] = bk.get((comp, f), 0.0) + usd
    f_lo = t1 * phi
    lpw = {f: lp.get(f, 0) for f in range(max(0, f_lo - 1), f_lo + phi)} if p1 is not None else {}
    Gf = p1.get("Gf", []) if p1 is not None else []
    Sf = p1.get("Sf", []) if p1 is not None else []
    trace_ok = p1 is None or (p1.get("pick") is not None and p1["cands"][p1["pick"]]["name"] == p1.get("name")
                              and bool(p1.get("fast_ok")) and len(Gf) == phi and len(Sf) == phi)
    vals = [A2, ah1, R1v, sig1, CS1, B1, y1, rhs1, tau1, lim1, ALG1, Q, CS, B, y, rhs, tau, lim, ak, G, S, RK,
            e["k0_p"], e["k0_rent"]] + [r["sigma"] for r in e.get("cands", [])]
    if p1 is not None:
        vals += [p1["p"], p1["rent"], p1.get("G", 0.0), p1.get("S", 0.0)]
    finite = all(math.isfinite(float(v)) for v in vals) and all(math.isfinite(v) for v in bk.values())
    h = (lambda v: float(v).hex())
    log = {"t_a": ta,
           "t_a-1": None if p1 is None else {
               "ALG(t_a-2)": h(A2), "executed": p1.get("name"),
               "p,rent,G,S,R": [h(p1[x]) for x in ("p", "rent", "G", "S", "R")], "ahat": h(ah1), "sigma": h(sig1),
               "C_S,B,y,rhs,tau,lim": [h(v) for v in (CS1, B1, y1, rhs1, tau1, lim1)]},
           "slot t_a": {"ALG(t_a-1)": h(ALG1), "Q": h(Q),
                        "C_S,B,y,rhs,tau,lim": [h(v) for v in (CS, B, y, rhs, tau, lim)],
                        "candidates ahat+R": [(r["name"], h(r["sigma"])) for r in e.get("cands", [])],
                        "K0 p,rent,G,S,R,ahat": [h(v) for v in (e["k0_p"], e["k0_rent"], G, S, RK, ak)],
                        "followed": e["followed"], "robust_all": e["robust_all"], "robust_since": e["robust_since"],
                        "cautious_since": e["cautious_since"], "abort_at": pol._p["abort_at"],
                        "on_unavailable guard, lender": [pol.on_unavailable, lender_onu]},
           "n,J,phi": [inst.n, inst.J, phi],
           "R2 trace": {"bookings(t_a-1) by component, fast slot": {f"{c}@{f}": h(v) for (c, f), v in sorted(
               bk.items(), key=lambda x: (str(x[0][1]), x[0][0]))},
               "G per fast slot": [h(v) for v in Gf], "S per fast slot": [h(v) for v in Sf],
               "routing-LP calls per fast slot (t_a-1, and the last fast slot of t_a-2)":
                   {str(f): nc for f, nc in sorted(lpw.items()) if nc}}}
    trace = dict(t1=t1, phi=phi, bk=bk, Gf=list(Gf), Sf=list(Sf), lp=dict(lpw), alg1=ALG1,
                 p=z if p1 is None else p1["p"], rent=z if p1 is None else p1["rent"])
    base = dict(hyp=bool(hyp), sale=bool(sale), forced=bool(pol.ratchet.forced), log=log, k=k, trace=trace,
                finite=bool(finite), cs_ok=bool(CS1 >= 0.0), trace_ok=bool(trace_ok))
    if not finite:                       # Fraction cannot take inf or NaN: nothing below can be evaluated
        cls = "undecided" if hyp else "outside P's hypotheses"
        return dict(base, X=None, m=None, sum_ok=False, R1=False, R2=False, cls=cls, refutes=None, terms={},
                    m_lp=None, m_out=None, share=None, why="a logged value is not finite (overflow or NaN)")
    X = F(ak) - F(lim)
    m1 = max(F(0), F(ALG1) - F(ah1))
    terms = dict(
        alg_minus_ahat=F(ALG1) - F(ah1), sigma_minus_lim=F(sig1) - F(lim1), tau_diff=F(tau1) - F(tau),
        gamma_m1_Q=-(g - 1) * F(Q), dB=-(F(B) - F(B1)), S_minus_R=F(S) - F(R1v), G_minus_Q=F(G) - F(Q),
        eps_a=F(ak) - F(ALG1) - F(G) - F(S), eps_sigma=F(ah1) + F(R1v) - F(sig1), eps_lim1=F(lim1) - F(rhs1) - F(tau1),
        eps_lim=-(F(lim) - F(rhs) - F(tau)), gamma_eps_C=-g * (F(CS) - F(CS1) - F(Q)), eps_rhs=-(F(rhs) - F(y) - F(B)),
        eps_rhs1=F(rhs1) - F(y1) - F(B1), eps_y=-(F(y) - g * F(CS)), eps_y1=F(y1) - g * F(CS1))
    tot = sum(terms.values(), F(0))
    bnd = (11 + 5 * k) * U * F(ak)
    r1 = X <= m1 + bnd
    scale = max(F(1), F(ALG1))
    thr = F(CERT_TOL) * scale
    r2 = m1 <= thr
    # where the excess of slot t_a-1 lies: x0 = its purchase, loading and rent bookings minus p + rent; x(f) = the
    # routing, fallback and stranding bookings of fast slot f minus G(f) + S(f); an LP slot is a fast slot f of t_a-1
    # with a routing-LP call at f or at f-1; m_out = x0^+ + sum of x(f)^+ over the other fast slots (the excess outside
    # the LP-explained bookings), m_lp = sum of x(f)^+ over the LP slots
    m_out = m_lp = F(0) if p1 is None else None    # at t_a = 0 every term of slot t_a-1 is 0
    lpf = []
    if p1 is not None and trace_ok:
        x0 = sum((F(v) for (c, _f), v in bk.items() if c in SLOW_COMPS), F(0)) - F(p1["p"]) - F(p1["rent"])
        m_out, m_lp = max(F(0), x0), F(0)
        for i in range(phi):
            f = f_lo + i
            xf = sum((F(bk.get((c, f), 0.0)) for c in FAST_COMPS), F(0)) - Gf[i] - Sf[i]
            if lpw.get(f, 0) > 0 or lpw.get(f - 1, 0) > 0:
                lpf.append(f)
                m_lp += max(F(0), xf)
            else:
                m_out += max(F(0), xf)
    sep = F(SEP) * scale
    # C3 §9, "Deciding an abort from one run": refutations first (both can apply), then undecided, the C2 case,
    # routing-LP and rounding aborts
    refutes = []
    if hyp and not r1 and CS1 >= 0.0:
        refutes.append("(d) via (R1)")
    if hyp and not r2 and sale and trace_ok and m_out > thr:
        refutes.append("Lemma P.1 via (R2)")
    if not hyp:
        cls = "outside P's hypotheses"
    elif refutes:
        cls = "refutation"
    elif not r1:
        cls = "undecided"
    elif not r2:
        cls = "C2 case" if not sale else ("undecided" if not trace_ok else "routing-LP abort")
    else:
        cls = "routing-LP abort" if (trace_ok and m_lp > sep and m_out <= sep) else "rounding abort"
    refutes = " and ".join(refutes) or None
    share = (m1 + bnd - X) / bnd if bnd > 0 else None
    fl = (lambda v: "n/a" if v is None else f"{float(v):.3e}")
    why = (f"X {float(X):.3e} vs (R1) bound m + (11+5k) u a-hat_K0 = {float(m1 + bnd):.3e} (k {k}; slack share "
           f"{float(share) if share is not None else float('nan'):.4f}); m(t_a-1) {float(m1):.3e} vs CERT_TOL "
           f"max(1,ALG(t_a-1)) = {float(thr):.3e}; m_lp {fl(m_lp)} at LP slots {lpf}, m_out "
           f"{fl(m_out)} (SEP max(1,ALG) = {float(sep):.3e}); C_S(t_a-1) {CS1:.6g}; per-fast-slot terms "
           f"reproduce evaluate {trace_ok}; sale-rule hypothesis {sale}")
    return dict(base, X=X, m=m1, sum_ok=(tot == X), R1=bool(r1), R2=bool(r2), cls=cls, refutes=refutes, terms=terms,
                m_lp=m_lp, m_out=m_out, share=share, why=why)


def classify_abort(inst, lm, make_inner, kw, ad, res_plain):
    """Instrumented rerun of an aborting run; returns (clause dict, reproduced bit for bit)."""
    res, pol, book, lp = run_a8p(inst, lm, make_inner(), kw, ad, ClauseProbe, trace=True)
    same = guard_records(res) == guard_records(res_plain)
    return clause(pol, inst, lm.get("on_unavailable", "sell"), book, lp), same


def outcome(cl):
    """The printed outcome of a classified abort."""
    return cl["cls"] + (f" of {cl['refutes']}" if cl["refutes"] else "")


# ------------------------------------------------------------------------------------------ exact recomputation
class Exact:
    """Per instance: the exact Q(t) and G_K0(t) (Fraction) from the instance's demand, arcs, clients per LLM, the
    stranding coefficients of S_K0 and of the reserve (the float inputs, combined exactly), C^min_j."""

    def __init__(self, inst):
        g = inst.grid
        self.phi, self.Df, self.T = g.phi, g.fast_min, g.T_slow
        self.n, self.J, self.m = inst.n, inst.J, inst.m
        self.q = [float(x.q_usd_per_h) for x in inst.llms]
        self.cl = [int(x) for x in np.asarray(inst.clients.llm)]
        self.d = np.asarray(inst.clients.demand, dtype=np.float64)
        dl = np.asarray(inst.clients.delta_usd_per_h, dtype=np.float64)
        self.ok = [[bool(np.isfinite(dl[c, l]) and dl[c, l] < self.q[self.cl[c]]) for l in range(self.m)]
                   for c in range(self.n)]
        self.clients_of = [[c for c in range(self.n) if self.cl[c] == j] for j in range(self.J)]
        self.kinf = bool(inst.kappa_infinite)
        st = inst.stranding
        Tdr = [float(x.T_dr_s) for x in inst.llms]
        mu_fl = [float(v) if (float(v) > 0 and Tdr[j] > 0) else 0.0 for j, v in enumerate(np.asarray(st.mu_fl_usd))]
        piW = [float(p) * float(st.W_f_min) for p in np.asarray(st.pi_usd_per_min)]   # the float product, as the code
        self.mkv = [F(float(v)) for v in np.asarray(st.mu_kv_usd)]
        self.mfl = [F(v) for v in mu_fl]
        self.mfb = [F(float(v)) for v in np.asarray(st.mu_fb_usd)]
        self.piW = [F(v) for v in piW]
        self.kap = [self.mkv[j] + self.mfl[j] + self.mfb[j] + self.piW[j] for j in range(self.J)]
        Dfr = F(self.Df) / 60
        self.Q, self.G, self.Fj = [], [], []
        Fcum = [F(0)] * self.J
        for t in range(self.T):
            fs = range(t * self.phi, (t + 1) * self.phi)
            Qt = sum((F(self.q[self.cl[c]]) * sum((F(float(self.d[c, f])) for f in fs), F(0)) * Dfr
                      for c in range(self.n)), F(0))
            Gt = F(0)
            for f in fs:
                for j in range(self.J):
                    Gt += F(self.q[j]) * sum((F(float(self.d[c, f])) for c in self.clients_of[j]), F(0)) * Dfr
            for j in range(self.J):
                Fcum[j] += sum((F(self.q[j]) * sum((F(float(self.d[c, f])) for f in fs), F(0)) * Dfr
                                for c in self.clients_of[j]), F(0))
            self.Q.append(Qt)
            self.G.append(Gt)
            self.Fj.append(list(Fcum))
        self.CS = []
        acc = F(0)
        for Qt in self.Q:
            acc += Qt
            self.CS.append(acc)
        price = np.asarray(inst.price, dtype=np.float64)
        beta = np.asarray(inst.beta_usd, dtype=np.float64)
        self.Cmin = []
        for j in range(self.J):
            best = None
            for l in range(self.m):
                if not any(self.ok[c][l] for c in self.clients_of[j]):
                    continue
                for kk in inst.sites[l].menu:
                    a = float(price[l, kk])
                    if not math.isfinite(a):
                        continue
                    v = F(float(beta[j, l])) + inst.llms[j].g * F(a) * int(inst.contracts[kk].prepaid_min) / 60
                    best = v if best is None or v < best else best
            self.Cmin.append(best)
        self._lb = {}

    def B(self, t, allow, B0_used, view):
        """B(t) from the instance: B0, min{B0, kappa B_on(t)}, or at 'lb' the OnlineLB series replayed offline on the
        instance's demand with the run's view (algos/online_lb.series)."""
        if allow.get("allowance") == "lb":
            key = view.information
            if key not in self._lb:
                self._lb[key] = online_lb.series(view, self.d)["B"]
            return F(float(self._lb[key][t]))
        if allow["kappa"] is None:
            return F(float(B0_used))
        Bon = sum((Fj if Cm is None else min(Fj, Cm) for Fj, Cm in zip(self.Fj[t], self.Cmin)), F(0))
        return min(F(float(B0_used)), F(float(allow["kappa"])) * Bon)

    def served_ub(self, j, dprev, Wrow, lbprev):
        """UB_c(f-1) of T0gBound's class docstring for the clients of LLM j (Fraction; +inf capacity allowed)."""
        cs = self.clients_of[j]
        P = [l for l in range(self.m) if Wrow[l] > 0]
        out = {}
        for c in cs:
            if self.kinf:
                out[c] = F(float(dprev[c])) if any(self.ok[c][l] for l in P) else F(0)
                continue
            if any(self.ok[c][l] and math.isinf(Wrow[l]) for l in range(self.m)):
                out[c] = F(float(dprev[c]))
                continue
            cap = sum((F(float(Wrow[l])) for l in range(self.m) if self.ok[c][l]), F(0))
            for c2 in cs:
                if c2 != c and all(self.ok[c][l] for l in P if self.ok[c2][l]):
                    cap -= F(float(lbprev[c2]))
            out[c] = min(F(float(dprev[c])), max(cap, F(0)))
        return out

    def k0_strand(self, t, e):
        """(S_K0(t), R(t-1)) from the committed state: S_K0 = sum_c [mu_kv + mu_fl D_j + mu_fb + pi W_f D_j] e_c at the
        first fast slot (LB = 0 with no replica; later fast slots add nothing), e_c = min{dh_c, UB_c}, dh_c =
        min{prev_d_c, d_c(t phi)}, D_j = [prev W^hi_j > 0 somewhere]; R(t-1) = sum_c kappa'_c UB_c."""
        S = R = F(0)
        f0 = t * self.phi
        for j in range(self.J):
            if not self.clients_of[j]:
                continue
            ub = self.served_ub(j, e["prev_d"], e["prev_W"][j], e["prev_lb"])
            Dj = 1 if any(w > 0 for w in e["prev_W"][j]) else 0
            coef = self.mkv[j] + self.mfl[j] * Dj + self.mfb[j] + self.piW[j] * Dj
            for c, u in ub.items():
                dh = min(F(float(e["prev_d"][c])), F(float(self.d[c, f0])))
                S += coef * min(dh, u)
                R += self.kap[j] * u
        return S, R


def rel(a, b):
    return abs(float(a) - float(b)) / max(1.0, abs(float(b)))


def monotone(x):
    """True iff the float series x is >= 0 and nondecreasing, exactly."""
    x = np.asarray(x, dtype=np.float64)
    return bool(np.all(x >= 0) and np.all(np.diff(x) >= 0))


# ------------------------------------------------------------------------------------------ part (a)
def check_run(inst, X, res, pol, gamma, allow, st, cov, tag):
    rep = res.metrics["policy"]
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=np.float64))
    g = F(gamma)
    st.add("F7/F2: the guard's B(t) is >= 0 and nondecreasing in float64 over the run (exactly; 0/1)", 0.0, tag,
           ok=monotone(rep["guard"]["B"]))
    st.add("P's instance class: stranding coefficients, W_f, beta, beta-tilde, q_j >= 0, demand finite and >= 0 (0/1)",
           0.0, tag,
           ok=instance_class_ok(pol.view, inst.clients.demand))
    if pol.olb is not None:
        cov["OnlineLB values checked at lb"] += 3 * len(pol.olb.B_series)
        st.add("F2 at 'lb': OnlineLB's LB', W_k and B series >= 0 and nondecreasing in float64 (exactly; 0/1)", 0.0,
               tag, ok=all(monotone(s) for s in (pol.olb.LB_series, pol.olb.Wk_series, pol.olb.B_series)))
    for t, e in sorted(pol.log.items()):
        where = f"{tag} t={t}"
        if e.get("mode") == "E":
            st.add("Lemma P.1: ALG(t) <= a-hat(t) + CERT_TOL max(1,ALG(t)) at executed slots, any candidate",
                   (e["ahat"] - alg[t]) / max(1.0, abs(alg[t])) + CERT_TOL, f"{where} cand={e['name']}")
            mr = (alg[t] - e["ahat"]) / max(1.0, abs(alg[t]))
            if mr > MX.get("m", (-math.inf, None))[0]:
                MX["m"] = (mr, f"{where} cand={e['name']}")
            cov["executed:" + e["name"]] += 1
        st.add("consistency: obs.cost_so_far == ledger's ALG(t-1) (rel)", REL - (rel(e["alg1"], alg[t - 1]) if t else
                                                                           abs(e["alg1"])), where)
        if e["followed"] != "FB" or e["robust_all"] or e["robust_since"] is not None:
            cov["slots outside the hypotheses"] += 1
            continue
        cov["slots checked"] += 1
        cov["slots checked at lb"] += int(allow.get("allowance") == "lb")
        cov["slots with cautious counting"] += int(e["cautious_since"] is not None)
        f0 = t * X.phi
        st.add("consistency: obs.demand == the instance's demand (0/1)", 0.0, where,
               ok=bool(np.array_equal(e["demand"], X.d[:, f0:f0 + X.phi])))
        dprev_inst = X.d[:, f0 - 1] if t > 0 else np.zeros(X.n)
        st.add("consistency: committed prev_d == the instance's demand at fast slot t phi - 1 (0/1)", 0.0, where,
               ok=bool(np.array_equal(e["prev_d"], dprev_inst)))
        # (a) K0's terms
        rel_ok = all(isinstance(a, Release) for a in e["k0"]) and sorted(int(a.lease_id) for a in e["k0"]) == \
            e["obs_leases"]
        st.add("(a) K0 is a Release of every lease of obs and nothing else (0/1)", 0.0, where, ok=rel_ok)
        st.add("(a) p_K0 = rent_K0 = R_K0 = 0 and K0's evaluation in bound form (code values, exactly; 0/1)", 0.0,
               where, ok=(e["k0_p"] == 0.0 and e["k0_rent"] == 0.0 and e["k0_R"] == 0.0 and e["k0_form"] == "bound"))
        Qx, Gx = X.Q[t], X.G[t]
        st.add("impl. (a) G_K0(t) == Q(t), exact recomputation (0/1)", 0.0, where, ok=(Gx == Qx))
        st.add("(a) code G_K0(t) vs exact Q(t) (REL - rel diff)", REL - rel(e["k0_G"], Qx), where)
        st.add("consistency: code Q(t) (SafeExpert.fb_inc) vs exact Q(t) (REL - rel diff)", REL - rel(e["Q"], Qx),
               where)
        st.add("consistency: code C_S(t) vs exact sum of Q (REL - rel diff)", REL - rel(e["CS"], X.CS[t]), where)
        Bx = X.B(t, allow, pol.ratchet.B0, pol.view)
        st.add("consistency: code B(t) vs B(t) from the instance (REL - rel diff)", REL - rel(e["B"], Bx), where)
        Sx, Rx = X.k0_strand(t, e)
        st.add("impl. (a) S_K0(t) <= R(t-1), exact recomputation from the committed state", float(Rx - Sx), where,
               ok=(Sx <= Rx))
        st.add("(a) code S_K0(t) vs exact recomputation (REL - rel diff)", REL - rel(e["k0_S"], Sx), where)
        st.add("consistency: recorded R(t-1) vs exact recomputation from the committed state (REL - rel diff)",
               REL - rel(e["budget"], Rx), where)
        cov["slots with R(t-1) > 0 and S_K0(t) > 0"] += int(Rx > 0 and Sx > 0)
        cov["slots after a robust-form list (committed W = inf)"] += int(bool(np.isinf(e["prev_W"]).any()))
        # (b) identity and brackets
        p1 = pol.log.get(t - 1)
        Bt = F(e["B"])
        B1 = F(p1["B"]) if p1 is not None else F(0)
        CS1 = X.CS[t - 1] if t > 0 else F(0)
        rhs_t = g * X.CS[t] + Bt
        rhs_1 = g * CS1 + B1
        A1 = F(e["alg1"])
        ak = A1 + 0 + 0 + Gx + Sx
        lhs = rhs_t - ak - 0
        b1, b2, b3, b4, b5 = rhs_1 - A1 - Rx, Rx - Sx, (g - 1) * Qx, Bt - B1, Qx - Gx
        st.add("impl. (b) identity: rhs(t) - a-hat_K0(t) - R_K0(t) == sum of the five brackets (exact; 0/1)", 0.0,
               where, ok=(lhs == b1 + b2 + b3 + b4 + b5))
        st.add("impl. (b) bracket 2 >= 0 and bracket 5 == 0 (exact; bracket 2)", float(b2), where,
               ok=(b2 >= 0 and b5 == 0))
        st.add("(b) brackets 3 and 4 >= 0 (exact, bracket 4 from the guard's float B; min of the two)",
               float(min(b3, b4)), where, ok=(b3 >= 0 and b4 >= 0))
        m1 = max(F(0), A1 - F(p1["ahat"])) if p1 is not None else F(0)
        tol1 = F(p1["tau"]) if p1 is not None else F(0)
        sc = max(1.0, abs(float(rhs_t)))
        st.add("(b) bracket 1 + tol(t-1) + m(t-1) >= -RND max(1,|rhs|) (relative)", float(b1 + tol1 + m1) / sc + RND,
               where)
        cov["slots with m(t-1) > 0"] += int(m1 > 0)
        tolt = F(GUARD_TOL) * max(F(1), abs(rhs_t))
        st.add("(b)/(c) exact K0 margin rhs(t) + tol(t) - a-hat_K0(t) - R_K0(t) + m(t-1) >= -RND max(1,|rhs|) (rel.)",
               float(rhs_t + tolt - ak + m1) / sc + RND, where)
        st.add("(c) K0 passes the code's float64 test: fl(a-hat_K0 + R_K0) <= lim(t) (relative slack)",
               (e["lim"] - (e["k0_ahat"] + e["k0_R"])) / sc, where)
    return rep


def part_a(nseeds, st, cov, out):
    Xc = {}
    aborts = []
    t0 = time.time()
    nvar = 8
    for s in range(nseeds):
        for v in range(nvar):
            for i, (mname, lm) in enumerate(MODELS.items()):
                for k, Inner in enumerate((TG._RandomInner, TG._OwnListInner)):
                    kinf = bool((s + v + i) % 2)
                    ad = bool((s + i + k) % 2)
                    allow = ALLOWS[(s + v + i + k) % len(ALLOWS)]
                    gamma = (1.0, G2)[(s + v + i + k) % 2]
                    seed = 9000 + 101 * s + 13 * v + i
                    try:
                        inst = TG._rich_instance(seed, v, kinf)
                    except Exception:
                        cov["skip:" + mname] += 1
                        continue
                    onu = lm.get("on_unavailable", "sell")
                    kw = dict(gamma=gamma, on_unavailable=onu, **allow)
                    make = (lambda S=seed, I=Inner: I(S))
                    tag = f"s={s} v={v} {mname} {Inner.name} kinf={int(kinf)} ad={int(ad)} {alabel(allow)} " \
                          f"gamma={gamma:.4f}"
                    try:
                        res, pol, _b, _l = run_a8p(inst, lm, make(), kw, ad)
                    except Exception as ex:
                        if "ConfigError" in type(ex).__name__ or "safe_site" in str(ex):
                            cov["skip:" + mname] += 1
                            continue
                        raise
                    assert res.invariant_failures == [], (tag, res.invariant_failures[:2])
                    key = (seed, v, kinf)
                    if key not in Xc:
                        Xc = {key: Exact(inst)}             # instances are not reused across cases
                    rep = check_run(inst, Xc[key], res, pol, gamma, allow, st, cov, tag)
                    cov["runs"] += 1
                    cov["runs " + mname] += 1
                    cov["runs " + alabel(allow)] += 1
                    pr = rep["projection"]
                    for kk in ("slots", "P1", "P0", "K0", "guard_releases"):
                        cov["projection:" + kk] += pr[kk]
                    bound_run = (rep["t0g"]["robust_since"] is None and not rep["t0g"]["robust_all"])
                    cov["runs in which T0g stays in bound form"] += int(bound_run)
                    if rep["t_a"] is not None:
                        cl, same = classify_abort(inst, lm, make, kw, ad, res)
                        aborts.append((tag, rep["t_a"], bound_run, cl, same))
    out.append(f"(a) runs: {cov['runs']} (seeds 0-{nseeds - 1} x 8 variants x {len(MODELS)} lender models x 2 inner "
               f"policies; skipped: {sum(v for k, v in cov.items() if k.startswith('skip:'))}); "
               f"{time.time() - t0:.0f} s")
    return aborts


# ------------------------------------------------------------------------------------------ part (b)
def big_instance(seed, n, J, slow, fast, hor, kinf=False, const_demand=False, lam0=False, caps=(60, 60)):
    """A full-model instance with many clients per LLM (the P6 auditor's builder, p6audit/prop_p/pp_audit.py): the
    toy's sites with capacities caps, J LLMs (1 and 2 GPUs per replica alternating), n clients with random routing
    costs (10% infinite, 5% at or above q), constant or random demand over several magnitudes, every stranding
    coefficient positive, random load times (0 with lam0) and loading charges."""
    rng = np.random.default_rng(seed)
    cfg = load_json(CONFIGS / "toy.json")
    cfg["time"].update(slow_slot_min=slow, fast_slot_min=fast, horizon_min=hor)
    cfg["contracts"] = [{"id": "short", "tau_min": slow, "H_min": 3},
                        {"id": "long", "tau_min": 2 * slow, "H_min": 13},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": slow}]
    base_llm = cfg["llms"][0]
    cfg["llms"] = [{**base_llm, "id": f"M{j}", "g": 1 + (j % 2)} for j in range(J)]
    T = hor // slow
    cfg["lenders"][0].update(capacity_gpus=caps[0], R=[x for x in (3, 4, 9, 14) if x < T])
    cfg["lenders"][1].update(capacity_gpus=caps[1], R=[x for x in (2, 6, 7, 12) if x < T])
    base = cfg["borrowers"]["clients"][0]
    cfg["borrowers"]["clients"] = [{**base, "llm": f"M{c % J}", "borrowers": [f"b{c}"],
                                    "demand": {"kind": "array", "values": [1.0] * (hor // fast)}} for c in range(n)]
    inst = build_instance(cfg)
    m = inst.m
    q = np.array([x.q_usd_per_h for x in inst.llms])
    cl = np.asarray(inst.clients.llm)
    dl = np.empty((n, m))
    for c in range(n):
        for l in range(m):
            u = rng.random()
            dl[c, l] = (np.inf if u < 0.1 else q[cl[c]] * (1.0 + rng.random()) if u < 0.15
                        else q[cl[c]] * rng.random() * 0.9)
    inst.clients.delta_usd_per_h = dl
    Tf = inst.grid.T_fast
    if const_demand:
        lev = rng.uniform(0.1, 3.0, n)
        dem = np.repeat(lev[:, None], Tf, axis=1)
    else:
        dem = np.where(rng.random((n, Tf)) < 0.8,
                       rng.uniform(0.01, 3.0, (n, Tf)) * 10.0 ** rng.integers(-3, 2, (n, Tf)), 0.0)
    inst.clients.demand = dem
    inst.stranding = Stranding(mu_kv_usd=rng.uniform(0.05, 1.0, J), mu_fl_usd=rng.uniform(0.05, 1.0, J),
                               mu_fb_usd=rng.uniform(0.05, 1.0, J), pi_usd_per_min=rng.uniform(0.01, 0.2, J),
                               W_f_min=float(rng.choice([1.0, 3.0, 7.0])))
    inst.lam_s = (np.zeros((J, m)) if lam0 else
                  rng.choice([0.0, 30.0, 90.0, 250.0, 700.0], size=(J, m)).astype(float))
    inst.beta_usd = rng.uniform(0.0, 0.3, (J, m))
    inst.llms = tuple(dataclasses.replace(x, T_dr_s=float(rng.choice([10.0, 28.49, 200.0]))) for x in inst.llms)
    inst.kappa_infinite = bool(kinf)
    return inst


def edge16(seed, phi1):
    """The n = 16 edge instance of the P6 auditor's scans B2 (phi = 10, mu_kv = mu_fl = 0 so that slot 0's bound is
    tight) and B3 (phi = 1, every stranding coefficient positive): two LLMs, constant demand scaled down, the protected
    site's contract 2 priced in {0.3, 0.6, 0.9, 1.2}, beta = 0 there, load times 0, capacities 200."""
    inst = big_instance(1900 + seed, 16, 2, 20, 20 if phi1 else 2, 200, kinf=bool(seed % 2), const_demand=True,
                        lam0=True, caps=(200, 200))
    inst.clients.demand = inst.clients.demand * (0.0005, 0.001, 0.002)[seed % 3]
    pr = np.array(inst.price, dtype=float)
    pr[2, 2] = (0.3, 0.6, 0.9, 1.2)[seed % 4]
    inst.price = pr
    bt = np.array(inst.beta_usd, dtype=float)
    bt[:, 2] = 0.0
    inst.beta_usd = bt
    if not phi1:
        stv = inst.stranding
        inst.stranding = Stranding(mu_kv_usd=np.zeros(2), mu_fl_usd=np.zeros(2), mu_fb_usd=np.asarray(stv.mu_fb_usd),
                                   pi_usd_per_min=np.asarray(stv.pi_usd_per_min), W_f_min=stv.W_f_min)
    return inst


def edge_b0(g, slot):
    """The constant B0 that puts the executed list of `slot` at its limit in the reference run's guard record g, and
    rhs(slot+1) of that run (None if absent)."""
    i = g["slots"].index(slot)
    tgt, CSs = g["a_hat"][i] + g["reserve"][i], g["C_S"][i]
    nxt = tgt + g["C_S"][i + 1] - CSs if len(g["C_S"]) > i + 1 else None
    return ((tgt - GUARD_TOL - CSs) if tgt < 1.0 else (tgt / (1.0 + GUARD_TOL) - CSs)), nxt


def edge_scan(name, cases, slot, Inner, st, out):
    """B0 in 81 ulp steps around the value that puts `slot`'s executed list at its limit, for every (label, inst) of
    cases (None skips a case); every abort is classified by the clause. Returns the classified aborts."""
    t0 = time.time()
    lm = {"schedule": "trace", "information": "I1", "on_unavailable": "sell"}
    res_cls, runs, skipped = [], 0, 0
    for label, inst in cases:
        if inst is None:
            skipped += 1
            continue
        ref, _p, _b, _l = run_a8p(inst, lm, Inner(), dict(gamma=1.0, B0=1e3, kappa=None, on_unavailable="sell"))
        Bs, nxt = edge_b0(ref.metrics["policy"]["guard"], slot)
        if Bs < 0 or (slot == 0 and (nxt is None or nxt >= 1.0)):
            skipped += 1
            continue
        for kk in range(-40, 41):
            B0 = Bs + kk * math.ulp(Bs)
            if B0 < 0:
                continue
            kw = dict(gamma=1.0, B0=float(B0), kappa=None, on_unavailable="sell")
            res, _p, _b, _l = run_a8p(inst, lm, Inner(), kw)
            runs += 1
            if res.metrics["policy"]["t_a"] is not None:
                cl, same = classify_abort(inst, lm, Inner, kw, False, res)
                res_cls.append((f"{name} {label} B0={float(B0).hex()}", cl, same))
    nab = len(res_cls)
    by = Counter(outcome(c) for _w, c, _s in res_cls)
    n_hyp = sum(1 for _w, c, _s in res_cls if c["hyp"] and c["sale"])
    n_r1 = sum(1 for _w, c, _s in res_cls if c["R1"])
    n_r2 = sum(1 for _w, c, _s in res_cls if c["R2"])
    n_gq = sum(1 for _w, c, _s in res_cls if c["terms"].get("G_minus_Q", 0) != 0)
    shares = [float(c["share"]) for _w, c, _s in res_cls if c["share"] is not None]
    out.append(f"(b) {name}: {runs} runs ({skipped} cases skipped), {nab} aborts (at slots "
               f"{dict(Counter(c['log']['t_a'] for _w, c, _s in res_cls))}); outcomes {dict(by)}; reproduced bit for "
               f"bit by the instrumented rerun {sum(1 for _w, _c, s in res_cls if s)} of {nab}; identity terms add up "
               f"exactly {sum(1 for _w, c, _s in res_cls if c['sum_ok'])} of {nab}; P's hypotheses and the sale-rule "
               f"hypothesis at t_a {n_hyp} of {nab}; (R1) {n_r1}, (R2) {n_r2}; aborts with G_K0 - Q != 0: {n_gq}; "
               f"least (R1) slack as a share of (11+5k) u a-hat_K0: "
               f"{min(shares) if shares else float('nan'):.4f}; {time.time() - t0:.0f} s")
    for w, c, same in res_cls:
        st.add("(b) edge scans: every abort is a rounding abort ((R1) and (R2)) with P's hypotheses (0/1)", 0.0, w,
               ok=(c["cls"] == "rounding abort" and c["hyp"] and c["sale"] and not c["forced"]))
        st.add("(b) clause: identity terms add up to X(t_a) exactly (0/1)", 0.0, w, ok=c["sum_ok"])
        st.add("(b) instrumented rerun reproduces the abort bit for bit (0/1)", 0.0, w, ok=same)
        st.add("(b) clause: the executed candidate's per-fast-slot G and S at t_a-1 reproduce evaluate (0/1)", 0.0, w,
               ok=c["trace_ok"])
    st.add(f"(b) the edge scan {name} produces at least one float64 abort, so the clause is exercised (count)",
           nab - 1, name, ok=nab > 0)
    return res_cls


def part_b(st, out):
    t0 = time.time()
    base = toy_instance({"lenders.0.lam_s": 0.0})
    scales = [round(0.05 + 0.006 * i, 6) for i in range(40)]
    toy = edge_scan("toy (n=J=phi=1)", ((f"s={s}", with_demand(base, base.clients.demand * s)) for s in scales), 2,
                    EdgeScript, st, out)
    b2 = edge_scan("B2 (n=16, J=2, phi=10)", ((f"seed={s}", edge16(s, False)) for s in range(40)), 0, EdgeBuy0, st,
                   out)
    b3 = edge_scan("B3 (n=16, J=2, phi=1)", ((f"seed={s}", edge16(s, True)) for s in range(40)), 0, EdgeBuy0, st, out)
    rich = b2 + b3
    n_gq = sum(1 for _w, c, _s in rich if c["terms"].get("G_minus_Q", 0) != 0)
    st.add("(b) the n = 16 scans produce an abort with G_K0 - Q != 0, so (R1)'s k-dependent part is exercised (count)",
           n_gq - 1, "B2, B3", ok=n_gq > 0)
    res_cls = toy + rich
    shares = [float(c["share"]) for _w, c, _s in res_cls if c["share"] is not None]
    by = Counter(outcome(c) for _w, c, _s in res_cls)
    out.append(f"(b) all edge scans: {len(res_cls)} aborts, outcomes {dict(by)}; aborts with G_K0 - Q != 0: "
               f"{sum(1 for _w, c, _s in res_cls if c['terms'].get('G_minus_Q', 0) != 0)}"
               f"; least (R1) slack as a share of the bound {min(shares) if shares else float('nan'):.4f}; "
               f"{time.time() - t0:.0f} s")
    if res_cls:
        mx = max((r for r in res_cls if r[1]["X"] is not None), key=lambda r: r[1]["X"])
        c = mx[1]
        ak = F(float.fromhex(c["log"]["slot t_a"]["K0 p,rent,G,S,R,ahat"][5]))
        out.append(f"    max X(t_a) {float(c['X']):.3e} (m(t_a-1) {float(c['m']):.3e}, bound of (R1) "
                   f"{float(c['m'] + (11 + 5 * c['k']) * U * ak):.3e}) at {mx[0]}; "
                   f"max m(t_a-1) {max(float(c['m']) for _w, c, _s in res_cls if c['m'] is not None):.3e}")
        for w, c, _s in (toy[:1] + b2[:1]):
            nz = ", ".join(f"{k}: {float(v):.3e}" for k, v in c["terms"].items() if v)
            out.append(f"    first abort {w}: X(t_a) {float(c['X']):.6e}, m(t_a-1) {float(c['m']):.6e}, outcome "
                       f"{outcome(c)}; terms {{{nz}}} (others 0)")
            out.append(f"    logged float64 values (hex): {c['log']}")
    out.append("    every abort (scan, case, B0, t_a, (R1), (R2), outcome, reproduced; the numbers that decided it):")
    for w, c, same in res_cls:
        out.append(f"      {w} t_a={c['log']['t_a']} R1={c['R1']} R2={c['R2']} {outcome(c)} reproduced={same}; "
                   f"{c['why']}")
    return res_cls


# ------------------------------------------------------------------------------------------ part (c)
def part_c(st, out):
    t0 = time.time()
    ok_all = True
    res_cls = []
    for info in ("I1", "I2"):
        lm = {"schedule": "trace", "information": info, "on_unavailable": "refuse"}
        inst = toy_instance({"lenders.0.lam_s": 0.0, "lenders.0.R": [2, 3]})
        for told in (None, "sell"):
            ref, _p, _b, _l = run_a8p(inst, lm, BuyAt2(), dict(gamma=1.0, B0=1e3, kappa=None, on_unavailable=told))
            g = ref.metrics["policy"]["guard"]
            i2 = g["slots"].index(2)
            B0 = g["a_hat"][i2] + g["reserve"][i2] - g["C_S"][i2]
            kw = dict(gamma=1.0, B0=float(B0), kappa=None, on_unavailable=told)
            res, _p, _b, _l = run_a8p(inst, lm, BuyAt2(), kw)
            rep = res.metrics["policy"]
            tag = f"C2 control {info} option={told} B0={float(B0).hex()}"
            if rep["t_a"] is None:
                out.append(f"(c) {tag}: NO ABORT (the control fails)")
                st.add("(c) C2 control: unforced abort, S on FB, T0g bound form (cautious), m(t_a-1) > 0, (R1) holds, "
                       "(R2) fails (0/1)", 0.0, tag, ok=False)
                ok_all = False
                continue
            cl, same = classify_abort(inst, lm, BuyAt2, kw, False, res)
            res_cls.append((tag, cl, same))
            e = cl["log"]["slot t_a"]
            good = (not cl["forced"] and cl["hyp"] and e["cautious_since"] is not None and cl["m"] > 0 and cl["R1"]
                    and not cl["R2"] and not cl["sale"] and cl["sum_ok"] and same
                    and cl["cls"] == "C2 case" and res.metrics["refused"]["unavailable"] >= 1)
            ok_all &= good
            out.append(f"(c) {tag}: abort at t_a = {cl['log']['t_a']} (forced {cl['forced']}); S follows "
                       f"{e['followed']}, robust_all {e['robust_all']}, robust_since {e['robust_since']}, "
                       f"cautious_since {e['cautious_since']}; refused {dict(res.metrics['refused'])}; "
                       f"m(t_a-1) = {float(cl['m']):.6g}, X(t_a) = {float(cl['X']):.6g}, "
                       f"X - m(t_a-1) = {float(cl['X'] - cl['m']):.3e}; (R1) {cl['R1']}, "
                       f"(R2) {cl['R2']}; sale-rule hypothesis {cl['sale']}; outcome: {outcome(cl)}; terms add up "
                       f"{cl['sum_ok']}; reproduced bit for bit {same}; {cl['why']}")
            out.append(f"    logged float64 values (hex): {cl['log']}")
            st.add("(c) C2 control: unforced abort, S on FB, T0g bound form (cautious), m(t_a-1) > 0, (R1) holds, "
                   "(R2) fails (0/1)", 0.0, tag, ok=good)
            kw2 = dict(kw, on_unavailable="refuse")
            res2, _p, _b, _l = run_a8p(inst, lm, BuyAt2(), kw2)
            r2 = res2.metrics["policy"]
            m2 = [x for x in r2["guard"]["m"] if x is not None]
            out.append(f"    the same run with the option passed ('refuse'): t_a {r2['t_a']}, max m {max(m2):.3g}, "
                       f"cautious_since {r2['t0g']['cautious_since']}")
            st.add("(c) contrast: with the option passed the C2 control's run does not abort and m == 0 (0/1)", 0.0,
                   tag, ok=(r2["t_a"] is None and max(m2) == 0.0))
    out.append(f"(c) {time.time() - t0:.0f} s")
    return ok_all, res_cls


def main():
    nseeds = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    t0 = time.time()
    st, cov = Checks(), Counter()
    out = ["X9: audit of Lemma P.1 and Proposition P (projected guard A8P, ProjectedGuarded; design/theory/"
           "c3_c4_c5_general.md §9 with its code-level clause; design/sublet_v2.md §5 P6, §8.1; with the P6 audit's "
           "corrections PROP_P-F1, F2, F3, F5); script code/sim/audit/x9_prop_p.py",
           "Oracles: K0's terms, identity (b) and its brackets recomputed in fractions.Fraction from the instance, the "
           "observation, the ledger's running total and T0gBound's committed state (not from T0gBound's own "
           "computation); the ledger for Lemma P.1; the clause's identity, (R1), (R2) and the LP-explained excess in "
           "Fraction from an instrumented rerun. Lines labelled 'impl.' hold by construction of the script's exact "
           "formulas (implementation checks, not evidence).",
           f"Abort outcomes under P's hypotheses: {', '.join(OUTCOMES)} (the C2 case without the sale-rule "
           f"hypothesis); CERT_TOL = {CERT_TOL:g}, SEP = {SEP:g}."]
    aborts = part_a(nseeds, st, cov, out)
    nb = sum(1 for a in aborts if a[2])
    out.append("    slots checked under P's hypotheses (S on FB, T0g in bound form after begin): "
               f"{cov['slots checked']} "
               f"(at 'lb': {cov['slots checked at lb']}; with cautious counting: "
               f"{cov['slots with cautious counting']}); outside: "
               f"{cov['slots outside the hypotheses']}; slots with R(t-1) > 0 and S_K0(t) > 0: "
               f"{cov['slots with R(t-1) > 0 and S_K0(t) > 0']}; slots after a robust-form list (committed W = inf): "
               f"{cov['slots after a robust-form list (committed W = inf)']}; slots with m(t-1) > 0: "
               f"{cov['slots with m(t-1) > 0']}")
    out.append("    executed candidates (slots): "
               + ", ".join(f"{k} {cov['executed:' + k]}" for k in ("E", "P1", "P0", "K0"))
               + "; projection totals: " + ", ".join(f"{k} {cov['projection:' + k]}" for k in
                                                       ("slots", "P1", "P0", "K0", "guard_releases"))
               + "; runs per lender model: " + ", ".join(f"{m} {cov['runs ' + m]}" for m in MODELS)
               + "; runs per allowance: " + ", ".join(f"{alabel(a)} {cov['runs ' + alabel(a)]}" for a in ALLOWS)
               + f"; OnlineLB values checked at 'lb': {cov['OnlineLB values checked at lb']}")
    mm = MX.get("m", (float("nan"), None))
    out.append(f"    Lemma P.1: max (ALG(t) - a-hat(t)) / max(1, ALG(t)) over executed slots {mm[0]:.3e} (at {mm[1]})")
    out.append(f"    runs in which T0g stays in bound form: {cov['runs in which T0g stays in bound form']}; aborts: "
               f"{len(aborts)} (in such runs: {nb}); outcomes {dict(Counter(outcome(a[3]) for a in aborts))}")
    for tag, ta, bound_run, cl, same in aborts:
        out.append(f"    abort {tag} t_a={ta} bound-form run {bound_run}: outcome {outcome(cl)}, (R1) {cl['R1']}, "
                   f"(R2) {cl['R2']}, reproduced {same}; {cl['why']}")
        if bound_run and cl["hyp"]:
            st.add("(a) no abort in a run where S follows FB and T0g stays in bound form, unless a rounding or "
                   "routing-LP abort (0/1)", 0.0, tag, ok=cl["cls"] in ("rounding abort", "routing-LP abort"))
    b_cls = part_b(st, out)
    c_ok, c_cls = part_c(st, out)
    every = [(a[0], a[3]) for a in aborts] + [(w, c) for w, c, _s in b_cls] + [(w, c) for w, c, _s in c_cls]
    for w, c in every:
        st.add("no classified abort is a 'refutation' or 'undecided' (0/1)", 0.0, w,
               ok=c["cls"] not in ("refutation", "undecided"))
    out.append(f"classified aborts in (a)-(c): {len(every)}, outcomes {dict(Counter(outcome(c) for _w, c in every))}")
    out.append("")
    out.append("Checks (violation: a 0/1 check that fails, or a negative slack):")
    out += st.lines()
    nv = st.nviol()
    assert c_ok == (st.d["(c) C2 control: unforced abort, S on FB, T0g bound form (cautious), m(t_a-1) > 0, (R1) "
                         "holds, (R2) fails (0/1)"][1] == 0)
    out.append(f"runtime {time.time() - t0:.0f} s")
    out.append(f"violations: {nv}")
    print("\n".join(out), flush=True)
    return nv


if __name__ == "__main__":
    if main():
        print("x9: a violation of a checked claim, the C2 control failed, or an abort is a refutation or undecided",
              file=sys.stderr)
        sys.exit(1)
