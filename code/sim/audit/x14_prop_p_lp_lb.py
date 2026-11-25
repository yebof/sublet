"""X14: the abort classification of Proposition P on an emulated inexact routing LP, and the float monotonicity of
A8P's allowance 'lb'.

Claims and sources. design/theory/c3_c4_c5_general.md §9, "Deciding an abort from one run" (a procedure, no label)
and Proposition P (d) with its fact F7, as corrected after the audit addendum of step P6 (design/sublet_v2.md §5):
  PROP_P-F1 (wrong as written): the pre-P6 rule declares an abort a refutation of Lemma P.1 when (R2) fails under the
    sale-rule hypothesis and the excess m(t_a-1) does not lie in the routing and fallback bookings of fast slots with
    a routing-LP call. An inexact routing LP also produces stranding excess (T0gBound's LB_c and UB_c rest on routing
    optimality), at the LP's own fast slot and at the next one, which may lie in the next slow slot. The corrected
    rule (x9_prop_p.clause) takes x(f), the routing, fallback and stranding bookings of fast slot f minus G(f) + S(f),
    calls a fast slot f of slot t_a-1 an LP slot if the engine solved a routing LP at f or at f-1, and refutes Lemma
    P.1 only if m_out = x0^+ + sum of x(f)^+ over the other fast slots (x0: the purchase, loading and rent bookings
    minus p + rent) exceeds CERT_TOL max(1, ALG(t_a-1)); an abort with (R1), (R2) and (T) is a routing-LP abort when
    the excess at LP slots exceeds SEP max(1, ALG(t_a-1)) and m_out does not, else a rounding abort.
  PROP_P-F2 (gap, closed by an argument): at 'lb', B(t) = min{W_k(t), LB'(t)} of algos/online_lb.OnlineLB is
    nonnegative and nondecreasing in float64 when beta, beta-tilde and the fallback prices q_j are >= 0 (every addend
    is nonnegative, float addition and the minima are monotone, new 'cap' entries copy S[M] and fl(nu beta-hat) is
    nondecreasing in nu, W_k = p ceil(peak - 1e-9) with p >= 0 and a running peak); with beta < 0 the property fails
    (PROP_P-F4: the instance class matters).

(a) Inexact routing LP, emulated by wrapping Engine._route_lp (the engine's code is not changed): 'scale' multiplies
    the LP's solution by 1 - eps at odd fast slots (feasible, slightly short of optimal; the P6 auditor's
    p6audit/prop_p/lp_classify.py and the second reader's p6audit/prop_p_verify/f1_lp.py); 'shift' moves eps of client
    1's load at L0 to client 0 at fast slot 1, the last fast slot of slot 0 (feasible; client 1 falls below LB_1 and
    client 0 rises above UB_0, so the excess appears at fast slot 2, the first fast slot of slot 1, which solves no
    LP). Instances: the toy with slow slots of 10 min, fast slots of 5 min, two clients of one LLM, client 0 with arcs
    to L0 and P, client 1 (its competitor at L0) with an arc to L0 only, mu_fb in {1, 20} and every other stranding
    coefficient 0, load times 0, loading charges 0 except at L1: 'scale' on the routing costs of lp_classify.py (0.3 q,
    0.1 q; demand 0.8, 0.6) and of f1_lp.py (0.4 q, 0.2 q); 'shift' on (0.4 q, 0.2 q) with demand 1.5 and 0.9 (0 from
    fast slot 2 on), and a Buy at L1 (no arcs) with a loading charge of 30 USD at slot 1, so that slot 1's list can be
    put at its limit while slot 0 passes. The scripted inner policy buys at L0 and P at slot 0 and releases its
    leases at slot 1 (adding the Buy at L1 under 'shift'); A8P with safe 'fb', gamma 1, the option 'sell', a lender
    that sells; B0 in 61 ulp steps (offsets -20 to 40, as in f1_lp.py) around the value that puts the list of slot 0
    ('scale') or slot 1 ('shift') at its limit; eps in {0, 1e-6, 1e-8, 1e-9, 1e-10, 1e-12}. Every abort of the scan is
    classified by x9's corrected clause after an instrumented rerun (with the emulation), and by the pre-P6 rule
    (old_rule, re-implemented in exact arithmetic; it differs from the float original only by rounding, far below
    RND).
    Checks: the unemulated instances (eps = 0) do not abort in the scanned range; every emulated abort is reproduced
    bit for bit, meets P's hypotheses and the sale-rule hypothesis, and is classified 'routing-LP abort' (or 'rounding
    abort' when m(t_a-1) <= CERT_TOL max(1, ALG(t_a-1)) and the excess cannot be separated), never 'refutation' or
    'undecided'; the pre-P6 rule labels at least one of them a refutation (the probe has power), and the 'shift'
    emulation produces at least one abort that only the f-1 clause explains.
(b) OnlineLB's LB', W_k and B series (online_lb.series, the slot-by-slot stepping that A8P uses) are >= 0 and
    nondecreasing exactly in float64 on the instance class: the 480 instances of the second reader's
    p6audit/prop_p_verify/f2_lb.py (tests/test_guard.py::_rich_instance, seeds 0-59 x 8 variants, kappa_infinite
    alternating, demand over 1e-15..1e5 with zeros and growing bursts) and the 200 instances of the auditor's
    p6audit/prop_p/cs_sign.py (x9's big_instance, 2-24 clients, 1-3 LLMs, 100 slow slots, demand over 1e-15..1e5 with
    zeros). Negative controls, on every instance of both sets: beta = -|beta| - 50 (LB' must go negative or decrease,
    as f2_lb.py found) and beta-tilde = -|beta-tilde| - 50 in the view (W_k must go negative or decrease).

Usage: x14_prop_p_lp_lb.py. Audit of the full-model guard; code/sim/audit/, output code/sim/out/audit_fm/x14_out.txt.
Deterministic (fixed seeds, no policy randomness). Exit status 1 if the corrected clause outputs 'refutation' or
'undecided' on an LP-caused abort, if an unemulated instance aborts, if a power check fails, if monotonicity fails on
the instance class, or if a negative control does not fail."""
import dataclasses
import math
import sys
import time
from collections import Counter
from fractions import Fraction as F

import numpy as np

import audit_env  # noqa: F401
import x9_prop_p as X9
from audit_env import TG
from fixtures import CONFIGS, load_json
from sublet import engine as _eng
from sublet.algos import online_lb
from sublet.algos.guard import GUARD_TOL
from sublet.experiments.q44_study import CERT_TOL
from sublet.instance import build_instance, public_view
from sublet.policies.base import Policy
from sublet.types import Buy, Release, Stranding

EPS = (0.0, 1e-6, 1e-8, 1e-9, 1e-10, 1e-12)
MU_FB = (1.0, 20.0)
LM = {"schedule": "trace", "information": "I1", "on_unavailable": "sell"}
RND = X9.RND
STRAND = X9.STRAND


# ------------------------------------------------------------------------------------------ (a) the emulation
class Emulation:
    """Wraps Engine._fast_step (to know the fast slot) and Engine._route_lp: 'scale' returns the LP's solution times
    1 - eps at odd fast slots; 'shift' moves eps of client 1's load at the first site (L0) to client 0 at fast slot 1
    (rows = the LLM's clients with demand, columns = its admitting sites, in index order). Restored on exit."""

    def __init__(self, mode, eps):
        self.mode, self.eps = mode, float(eps)

    def __enter__(self):
        E = _eng.Engine
        self.o_fast, self.o_lp = E._fast_step, E._route_lp
        cur = {"f": None}
        o_fast, o_lp, mode, eps = self.o_fast, self.o_lp, self.mode, self.eps

        def fast(eng, t, f, results):
            cur["f"] = int(f)
            return o_fast(eng, t, f, results)

        def route_lp(eng, *a, **k):
            x = o_lp(eng, *a, **k)
            f = cur["f"]
            if mode == "scale" and f % 2 == 1:
                return x * (1.0 - eps)
            if mode == "shift" and f == 1 and x.shape[0] == 2 and x[1, 0] >= eps:
                x = x.copy()
                x[0, 0] += eps
                x[1, 0] -= eps
            return x
        E._fast_step, E._route_lp = fast, route_lp
        return self

    def __exit__(self, *exc):
        _eng.Engine._fast_step, _eng.Engine._route_lp = self.o_fast, self.o_lp
        return False


def instance(mu_fb, deltas, demand, shift):
    """The two-client toy instance of (a) (module docstring)."""
    cfg = load_json(CONFIGS / "toy.json")
    cfg["time"].update(slow_slot_min=10, fast_slot_min=5, horizon_min=60)
    cfg["contracts"] = [{"id": "short", "tau_min": 10, "H_min": 5}, {"id": "long", "tau_min": 20, "H_min": 10},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": 10}]
    for L in cfg["lenders"][:2]:
        L["R"] = []
    base = cfg["borrowers"]["clients"][0]
    cfg["borrowers"]["clients"] = [{**base, "borrowers": [f"b{c}"], "demand": {"kind": "array", "values": [1.0] * 12}}
                                   for c in range(2)]
    inst = build_instance(cfg)
    q = inst.llms[0].q_usd_per_h
    inst.clients.delta_usd_per_h = np.array([[deltas[0] * q, np.inf, deltas[0] * q], [deltas[1] * q, np.inf, np.inf]])
    d1 = [demand[1]] * 2 + [0.0] * 10 if shift else [demand[1]] * 12
    inst.clients.demand = np.array([[demand[0]] * 12, d1])
    inst.stranding = Stranding(mu_kv_usd=np.zeros(1), mu_fl_usd=np.zeros(1), mu_fb_usd=np.full(1, float(mu_fb)),
                               pi_usd_per_min=np.zeros(1), W_f_min=0.0)
    inst.lam_s = np.zeros((1, 3))
    beta = np.zeros((1, 3))
    if shift:
        beta[0, 1] = 30.0                    # the Buy at L1 of slot 1 (no client has an arc to L1)
    inst.beta_usd = beta
    inst.kappa_infinite = False
    return inst


class Script(Policy):
    """Buys one replica at L0 (contract 'long') and one at P (contract 'prot') at slot 0 and releases every held lease
    at slot 1; with shift, also buys one replica at L1 (contract 'long') at slot 1."""
    name = "script"
    shift = False

    def act(self, obs):
        if obs.t == 0:
            return [Buy(0, 1, 0, 1), Buy(2, 2, 0, 1)]
        if obs.t == 1:
            return [Release(int(lid)) for lid in sorted(obs.leases)] + ([Buy(1, 1, 0, 1)] if self.shift else [])
        return []


class ScriptShift(Script):
    shift = True


def old_rule(cl):
    """The pre-P6 classification (x9_prop_p.py at HEAD 8d369e51, clause() and placed), re-implemented in exact
    arithmetic for the comparison (the original sums routing + fallback and G(f) in float; the difference is rounding,
    far below RND): the excess counts as placed if the routing and fallback bookings of slot t_a-1's fast slots with a
    routing-LP call exceed that slot's G(f) by at least m(t_a-1) - RND max(1, ALG(t_a-1))."""
    tr = cl["trace"]
    t1, phi = tr["t1"], tr["phi"]
    ex = F(0)
    lp1 = [f for f in range(t1 * phi, (t1 + 1) * phi) if tr["lp"].get(f, 0) > 0]
    for f in lp1:
        i = f - t1 * phi
        rf = F(tr["bk"].get(("routing", f), 0.0)) + F(tr["bk"].get(("fallback", f), 0.0))
        ex += max(F(0), rf - (tr["Gf"][i] if i < len(tr["Gf"]) else F(0)))
    placed = bool(lp1) and ex >= cl["m"] - F(RND) * max(F(1), F(tr["alg1"]))
    if not cl["R1"]:
        return "R1 fails (refutes P(d))"
    if cl["R2"]:
        return "rounding abort"
    if cl["sale"]:
        return "routing-LP abort" if placed else "unexplained (refutes Lemma P.1)"
    return "C2 case"


def without_f1(cl):
    """True iff the corrected rule without the f-1 clause (an LP slot needs a routing-LP call at f itself) would refute
    Lemma P.1 here: x0^+ plus the positive parts of x(f) over the fast slots of t_a-1 with no routing-LP call at f
    exceeds CERT_TOL max(1, ALG(t_a-1))."""
    if not (cl["hyp"] and cl["finite"] and not cl["R2"] and cl["sale"] and cl["trace_ok"]):
        return False
    tr = cl["trace"]
    t1, phi = tr["t1"], tr["phi"]
    out = max(F(0), sum((F(v) for (c, _f), v in tr["bk"].items() if c in X9.SLOW_COMPS), F(0)) - F(tr["p"])
              - F(tr["rent"]))
    for i in range(phi):
        f = t1 * phi + i
        if tr["lp"].get(f, 0) == 0:
            xf = sum((F(tr["bk"].get((c, f), 0.0)) for c in X9.FAST_COMPS), F(0)) - tr["Gf"][i] - tr["Sf"][i]
            out += max(F(0), xf)
    return out > F(CERT_TOL) * max(F(1), F(tr["alg1"]))


def part_a(st, out):
    t0 = time.time()
    cases = []
    for mu in MU_FB:
        for name, dl, dem in (("scale/lp_classify", (0.3, 0.1), (0.8, 0.6)), ("scale/f1_lp", (0.4, 0.2), (0.8, 0.6))):
            cases += [(name, "scale", mu, dl, dem, False, Script, 0, e) for e in EPS]
        cases += [("shift", "shift", mu, (0.4, 0.2), (1.5, 0.9), True, ScriptShift, 1, e) for e in EPS]
    rows = []
    for name, mode, mu, dl, dem, shift, Inner, edge, eps in cases:
        inst = instance(mu, dl, dem, shift)
        tag = f"{name} mu_fb={mu:g} eps={eps:g}"
        with Emulation(mode, eps):
            ref, _p, _b, _l = X9.run_a8p(inst, LM, Inner(), dict(gamma=1.0, B0=1e3, kappa=None, on_unavailable="sell"))
            g = ref.metrics["policy"]["guard"]
            i = g["slots"].index(edge)
            tgt, CSe = g["a_hat"][i] + g["reserve"][i], g["C_S"][i]
            Bs = (tgt - GUARD_TOL - CSe) if tgt < 1.0 else (tgt / (1.0 + GUARD_TOL) - CSe)
            found, runs = [], 0
            for kk in range(-20, 41):
                B0 = Bs + kk * math.ulp(Bs)
                if B0 < 0:
                    continue
                kw = dict(gamma=1.0, B0=float(B0), kappa=None, on_unavailable="sell")
                res, _p, _b, _l = X9.run_a8p(inst, LM, Inner(), kw)
                runs += 1
                if res.metrics["policy"]["t_a"] is not None:
                    cl, same = X9.classify_abort(inst, LM, Inner, kw, False, res)
                    found.append((kk, cl, same))
        rows.append((tag, eps, runs, found))
    by_new, by_old, f1_needed, n_ab = Counter(), Counter(), 0, 0
    out.append("(a) emulated inexact routing LP: case | runs in the B0 scan, aborts | corrected outcomes | pre-P6 rule "
               "| aborts that only the f-1 clause explains; then the first abort: B0 offset (ulp), t_a, (R1), (R2), "
               "m(t_a-1), m_lp, m_out, reproduced, and the numbers that decided its outcome")
    for tag, eps, runs, found in rows:
        if eps == 0.0:
            out.append(f"  {tag} | {runs} runs, {len(found)} aborts")
            st.add("(a) the unemulated instance (eps = 0) does not abort in the scanned B0 range (0/1)", 0.0, tag,
                   ok=not found)
            continue
        if not found:
            out.append(f"  {tag} | {runs} runs, no abort")
            continue
        new = Counter(X9.outcome(cl) for _kk, cl, _s in found)
        old = Counter(old_rule(cl) for _kk, cl, _s in found)
        nf1 = sum(1 for _kk, cl, _s in found if without_f1(cl) and cl["cls"] == "routing-LP abort")
        by_new.update(new)
        by_old.update(old)
        f1_needed += nf1
        n_ab += len(found)
        out.append(f"  {tag} | {runs} runs, {len(found)} aborts | {dict(new)} | {dict(old)} | {nf1}")
        kk, cl, same = found[0]
        out.append(f"      first abort: B0 {kk:+d} ulp, t_a {cl['log']['t_a']}, (R1) {cl['R1']}, (R2) {cl['R2']}, m "
                   f"{float(cl['m']):.3e}, m_lp {float(cl['m_lp']):.3e}, m_out {float(cl['m_out']):.3e}, "
                   f"reproduced {same}; {cl['why']}")
        out.append(f"      its R2 trace: {cl['log']['R2 trace']}")
        for kk, cl, same in found:
            w = f"{tag} B0 {kk:+d} ulp"
            st.add("(a) LP-caused abort: reproduced bit for bit, P's hypotheses and the sale-rule hypothesis (0/1)",
                   0.0, w, ok=(same and cl["hyp"] and cl["sale"] and not cl["forced"] and cl["sum_ok"]))
            ok = cl["cls"] == "routing-LP abort" or (cl["cls"] == "rounding abort" and cl["R2"])
            st.add("(a) LP-caused abort: corrected clause gives 'routing-LP abort' (or 'rounding abort' with (R2)), "
                   "never 'refutation' or 'undecided' (0/1)", 0.0, w, ok=ok)
    st.add("(a) power: the pre-P6 rule labels at least one LP-caused abort a refutation (count)",
           by_old["unexplained (refutes Lemma P.1)"] - 1, "all cases", ok=by_old["unexplained (refutes Lemma P.1)"] > 0)
    st.add("(a) power: the 'shift' emulation produces an abort that only the f-1 clause explains (count)",
           f1_needed - 1, "shift", ok=f1_needed > 0)
    n_cases = sum(1 for r in rows if r[1] > 0)
    out.append(f"(a) {n_cases} emulated cases, {sum(1 for r in rows if r[1] > 0 and r[3])} with an abort, {n_ab} "
               f"aborts; corrected outcomes {dict(by_new)}; pre-P6 rule {dict(by_old)}; aborts that only the f-1 "
               f"clause explains: {f1_needed}; {time.time() - t0:.0f} s")


# ------------------------------------------------------------------------------------------ (b) OnlineLB
def bad(x):
    """True iff the float series x has a negative value or a decrease."""
    x = np.asarray(x, dtype=np.float64)
    return bool(np.any(x < 0) or np.any(np.diff(x) < 0))


def scan(insts):
    """(values checked, series failing on the class, LB' failing with beta < 0, W_k failing with beta-tilde < 0, n)."""
    vals = fails = neg_b = neg_bt = n = 0
    for inst, dem in insts:
        n += 1
        view = public_view(inst, "I1")
        s = online_lb.series(view, dem)
        for key in ("LB", "Wk", "B"):
            vals += len(s[key])
            fails += int(bad(s[key]))
        b0 = inst.beta_usd
        inst.beta_usd = -np.abs(np.asarray(b0, dtype=np.float64)) - 50.0
        neg_b += int(bad(online_lb.series(public_view(inst, "I1"), dem)["LB"]))
        inst.beta_usd = b0
        bt = -np.abs(np.nan_to_num(np.asarray(view.beta_tilde_usd, dtype=np.float64), posinf=0.0)) - 50.0
        neg_bt += int(bad(online_lb.series(dataclasses.replace(view, beta_tilde_usd=bt), dem)["Wk"]))
    return vals, fails, neg_b, neg_bt, n


def set_rich():
    """The 480 instances of f2_lb.py with its adversarial demand."""
    for seed in range(60):
        for v in range(8):
            inst = TG._rich_instance(seed, v, bool((seed + v) % 2))
            rng = np.random.default_rng(seed * 100 + v)
            n, Tf = inst.clients.demand.shape
            scales = 10.0 ** rng.integers(-15, 6, size=(n, Tf))
            dem = np.where(rng.random((n, Tf)) < 0.6, rng.random((n, Tf)) * scales, 0.0)
            for k in range(0, Tf, max(1, Tf // 5)):          # growing bursts: the running peak grows, S is extended
                dem[:, k] += rng.random(n) * (k + 1) * 3.0
            yield inst, dem


def set_big():
    """The 200 instances of cs_sign.py (x9's big_instance) with demand over 1e-15..1e5 and zeros."""
    rng = np.random.default_rng(11)
    for s in range(200):
        inst = X9.big_instance(5000 + s, int(rng.integers(2, 25)), int(rng.integers(1, 4)), 20,
                               int(rng.choice([1, 4, 5, 10])), 2000, kinf=bool(s % 2))
        n, Tf = inst.n, inst.grid.T_fast
        dem = np.where(rng.random((n, Tf)) < 0.5, rng.uniform(0, 1, (n, Tf)) * 10.0 ** rng.integers(-15, 5, (n, Tf)),
                       0.0)
        yield inst, dem


def part_b(st, out):
    t0 = time.time()
    for name, gen in (("f2_lb (_rich_instance)", set_rich), ("cs_sign (big_instance)", set_big)):
        vals, fails, neg_b, neg_bt, n = scan(gen())
        out.append(f"(b) {name}: {n} instances, {vals} values of LB', W_k and B: {fails} series with a negative value "
                   f"or a decrease; controls: beta < 0 makes LB' negative or decreasing on {neg_b} of {n}, beta-tilde "
                   f"< 0 makes W_k negative or decreasing on {neg_bt} of {n}")
        st.add("(b) OnlineLB's LB', W_k and B >= 0 and nondecreasing in float64 on the instance class (series failing)",
               -fails, name, ok=(fails == 0))
        st.add("(b) negative control beta < 0: LB' goes negative or decreases on every instance (0/1)", 0.0, name,
               ok=(neg_b == n))
        st.add("(b) negative control beta-tilde < 0: W_k goes negative or decreases on every instance (0/1)", 0.0,
               name, ok=(neg_bt == n))
    out.append(f"(b) {time.time() - t0:.0f} s")


def main():
    t0 = time.time()
    st = X9.Checks()
    out = ["X14: the abort classification of Proposition P on an emulated inexact routing LP (P6 audit, PROP_P-F1) "
           "and the float monotonicity of A8P's allowance 'lb' (PROP_P-F2); script code/sim/audit/x14_prop_p_lp_lb.py",
           f"Corrected clause: x9_prop_p.clause (CERT_TOL = {CERT_TOL:g}, SEP = {X9.SEP:g}); pre-P6 rule: old_rule "
           "here."]
    part_a(st, out)
    part_b(st, out)
    out.append("")
    out.append("Checks (violation: a 0/1 check that fails, or a negative slack):")
    out += st.lines()
    nv = st.nviol()
    out.append(f"runtime {time.time() - t0:.0f} s")
    out.append(f"violations: {nv}")
    print("\n".join(out), flush=True)
    return nv


if __name__ == "__main__":
    if main():
        print("x14: a violation (a refutation or undecided outcome on an LP-caused abort, an abort without emulation, "
              "a failed power check, a monotonicity failure, or a negative control that does not fail)",
              file=sys.stderr)
        sys.exit(1)
