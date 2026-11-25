"""X13: Theorem G2 for A8 (Guarded) and A8P (ProjectedGuarded) on core exports, with S following R after the abort.

Claim and source. design/theory/c3_c4_c5_general.md §9, Theorem G2 and the paragraph "A8's mode S on core exports":
on a from_core export, under a lender that sells and ends no lease inside its window, A8's mode S costs at every
slot u >= t_a at most c_S(u) (plus W_S at a copy slot), and at an adaptive wind-down slot at most Q(u) + WD_TIE
max(1, Q(u)); hence G2(b) holds for A8, and through Remark R(e) for A8P, up to WD_TIE sum_u max(1, Q(u)) over the
adaptive slots. The audit addendum of step P6 (design/sublet_v2.md §5) in design/theory/audit_guard.md: finding
REMARK_R-F1 (the mode-S step of G2(b) was not proved for A8's wind-down) and the row 'G2 on core exports with S
following R after the abort' of its 'Adversarial attempts'. The auditors' scratch scripts behind that row are moved
here (open item 1 of the addendum).

Checked from the ledger (ALG(t), the cumulative per-slot total) and the guard's report (C_S(t), B(t), gamma C_S(t) +
B(t), a-hat(t), W_S(t_a), FB's increments Q(u), the wind-down records), per run:
  G2(a) without an abort: ALG(T) <= gamma C_S(T) + B(T), up to GUARD_TOL max(1, |gamma C_S(T) + B(T)|) + FLT;
  G2(b) with an abort at t_a: ALG(T) <= C_S(T) + (gamma - 1) C_S(t_a - 1) + W_S(t_a) + B(t_a - 1), up to GUARD_TOL
        max(1, |gamma C_S(t_a - 1) + B(t_a - 1)|) (none at t_a = 0) + TIE + FLT;
  mode S: the S-mode excess X = [ALG(T) - ALG(t_a - 1)] - [W_S(t_a) + C_S(T) - C_S(t_a - 1)] <= TIE + FLT (the step of
        G2(b)'s proof that the paragraph supplies);
  soundness: m(u) = max{0, ALG(u) - a-hat(u)} <= CERT_TOL max(1, ALG(u)) at every slot executed in mode E (T0g's test
        is sound on core exports, so G2's m is 0);
with TIE = WD_TIE sum over the adaptive wind-down slots u (records with a choice among K1, K0, K2) of max(1, |Q(u)|),
FLT = 1e-12 max(1, ALG(T)) and CERT_TOL = 1e-9 (q44_study). Every lender sells (on_unavailable 'sell') and absorbs
violations (the LenderModel defaults), as the paragraph requires. Every run's engine invariants must be empty. The
output counts the runs with an abort (forced by abort_at or natural), with S following R at some slot >= t_a, with
inherited leases at t_a, with both, and with adaptive slots that keep leases (K1 or K2), and gives the worst relative
excesses (excess / max(1, ALG(T))).

(a) The inner policy Renter (one lease per active client at a random usable site and contract unless its LLM is held
    at a usable site; each lease released at a random slot 0-3 slots after its window, so leases past their window
    are held at t_a) on the core instances of check_c3_upper (families rand, slo, spiky, setcover, seeds 0-2),
    c3p5_case(6) and cm_case(2, 4); lenders: oblivious (core.random_omega, rate 0.15), eager and adaptive; safe 'pd'
    and 'fb+pd'; wind-down 'auto' (adaptive), 'release' and 'keep'; A8 and A8P (project true); gamma 1, B0 'auto',
    kappa 10, on_unavailable 'sell'; each configuration without abort_at and with abort_at at each of the slots 1,
    1 + d, 1 + 2d, ... < T, d = max(3, T // 6).
(b) The inner policies _CoreRandom (tests' _RandomInner restricted to Buys of one replica and Releases), _Greedy (one
    lease per active client at a random usable site every slot, Releases at random), BL5 and A9 on the core
    instances rand, slo, spiky, setcover (seeds 0-1), c3p5_case(6), c3p5_case(30) and cm_case(2, 4); lenders as
    tests/test_guard.py::_core_inst builds them (oblivious, rate 0.1; eager; adaptive); the three wind-downs; A8P
    and A8 on the same configuration; over the configurations k, gamma cycles over 0.5, 1 and G2, safe over 'fb+pd'
    and 'pd', the allowance over B0 0, B0 'auto' with kappa 10 and B0 'auto' uncapped, and abort_at is 1 + (k mod 7)
    when floor(k / 2) is odd (so with either safe mode). (The scratch script behind the addendum's row advanced its
    index once per run, so the index was even at every configuration: it ran safe 'fb+pd' only and no forced abort.)
(c) A8P at the allowance 'lb' (B = min{W_k, LB'}, kappa None) on the instances and lenders of (b), around _CoreRandom,
    _Greedy and A9, the three wind-downs; over the configurations k, gamma alternates between 1 and G2 and safe
    between 'fb+pd' and 'pd' every second configuration; each configuration without and with abort_at 2.

Usage: x13_core_mode_s.py [--reduced]   (default about 5 min on one worker; --reduced: part (a) on two cases, parts
(b) and (c) on two cases). Audit addendum of step P6; code/sim/audit/, run by run_all.sh (step x13), output
code/sim/out/audit_fm/x13_out.txt. Exit status 1 on a violation of G2(a), G2(b), the mode-S step or soundness, on
an engine invariant failure, or on a run that raises."""
import sys
import time
import traceback
from collections import Counter

import numpy as np

import audit_env  # noqa: F401
from audit_env import TG
import core  # noqa: E402  (code/theory_checks/c3, on sys.path through audit_env)
from fixtures import c3p5_case, cm_case, upper_case
from sublet.algos.a5 import G2
from sublet.algos.a9 import NoticeCriticalRatio
from sublet.algos.guard import GUARD_TOL, WD_TIE, Guarded, ProjectedGuarded
from sublet.engine import EngineConfig, simulate
from sublet.experiments.q44_study import CERT_TOL
from sublet.instance import from_core
from sublet.policies.base import Policy
from sublet.types import Buy, LenderModel, Release

FLT = 1e-12            # float tolerance, times max(1, ALG(T))


# ================================================================ inner policies
class Renter(Policy):
    """Part (a): buys one lease per active client (random usable site, random contract) unless a lease of its LLM is
    held at a usable site; releases each lease at a random slot >= its window end + extra (extra in 0..3), so that
    leases past their window are held (rent) and may be announced."""
    name = "renter"

    def __init__(self, seed, p_buy=0.8):
        self.seed, self.p_buy = int(seed), float(p_buy)

    def reset(self, view, rng):
        super().reset(view, rng)
        self.r = np.random.default_rng(self.seed)
        self.rel_at = {}

    def act(self, obs):
        v, r, t = self.view, self.r, int(obs.t)
        out = []
        held = {}
        for lid, L in sorted(obs.leases.items()):
            if lid not in self.rel_at:
                end = -(-int(L.prepaid_end_min) // int(v.grid.slow_min))
                self.rel_at[lid] = end + int(r.integers(0, 4))
            if t >= self.rel_at[lid]:
                out.append(Release(lid))
            else:
                for rid in L.replicas:
                    held.setdefault(int(obs.replicas[rid].llm) if rid in obs.replicas else -1, set()).add(int(L.site))
        d = np.asarray(obs.demand).sum(axis=1)
        dl = np.asarray(v.client_delta_usd_per_h)
        q = np.array([float(v.llms[int(j)].q_usd_per_h) for j in v.client_llm])
        for c in np.flatnonzero(d > 0):
            j = int(v.client_llm[c])
            ok = np.flatnonzero(np.isfinite(dl[c]) & (dl[c] < q[c]))
            if not len(ok) or held.get(j, set()) & set(int(x) for x in ok):
                continue
            if r.random() < self.p_buy:
                l = int(r.choice(ok))
                out.append(Buy(l, int(r.choice(sorted(v.sites[l].menu))), j, 1))
                held.setdefault(j, set()).add(l)
        return out


class _CoreRandom(TG._RandomInner):
    """Parts (b), (c): tests' _RandomInner with every Buy of one replica and only Buys and Releases kept."""
    name = "core_random"

    def act(self, obs):
        out = []
        for a in super().act(obs):
            if isinstance(a, Buy):
                out.append(Buy(a.site, a.contract, a.llm, 1))
            elif isinstance(a, Release):
                out.append(a)
        return out


class _Greedy(TG._RandomInner):
    """Parts (b), (c): buys one lease per active client at a random usable site every slot, releases at random."""
    name = "core_greedy"

    def act(self, obs):
        v, r = self.view, self.r
        out = [Release(l) for l in sorted(obs.leases) if r.random() < 0.2]
        d = np.asarray(obs.demand).sum(axis=1)
        dl = np.asarray(v.client_delta_usd_per_h)
        for c in np.flatnonzero(d > 0):
            ok = np.flatnonzero(np.isfinite(dl[c]))
            if len(ok) and r.random() < 0.7:
                l = int(r.choice(ok))
                out.append(Buy(l, int(r.choice(sorted(v.sites[l].menu))), int(v.client_llm[c]), 1))
        return out


# ================================================================ the check
def check_run(part, inst, model, pol, gamma, tag, st, worst, bad):
    """One run: G2(a) or G2(b), the mode-S step and soundness from the ledger and the report (module docstring)."""
    res = simulate(inst, pol, model, EngineConfig(), policy_seed=0)
    if res.invariant_failures:
        bad.append((f"{part}: engine invariant", tag, res.invariant_failures[:3]))
    rep = res.metrics["policy"]
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
    C = np.asarray(rep["safe"]["C_S_curve"], dtype=float)
    Q = np.asarray(rep["safe"]["curve_FB"], dtype=float)
    g = rep["guard"]
    B, rhs, a_hat, slots = (np.asarray(g[k], dtype=float) for k in ("B", "rhs", "a_hat", "slots"))
    ta = rep["t_a"]
    flt = FLT * max(1.0, alg[-1])
    st[f"{part}: runs"] += 1
    st[f"{part}: runs {type(pol).__name__}"] += 1
    st[f"{part}: projected slots"] += rep.get("projection", {}).get("slots", 0)
    ex = slots if ta is None else slots[:-1]       # slots executed in mode E (slots are 0, 1, ... in order)
    for i, u in enumerate(ex.astype(int)):
        m = max(0.0, alg[u] - a_hat[i])
        worst[f"{part}: m"] = max(worst[f"{part}: m"], m / max(1.0, alg[u]))
        if m > CERT_TOL * max(1.0, alg[u]):
            bad.append((f"{part}: soundness (m > CERT_TOL)", tag, (int(u), m)))
    if ta is None:
        e = alg[-1] - (gamma * C[-1] + B[-1])
        worst[f"{part}: G2(a)"] = max(worst[f"{part}: G2(a)"], e / max(1.0, alg[-1]))
        if e > GUARD_TOL * max(1.0, abs(rhs[-1])) + flt:
            bad.append((f"{part}: G2(a)", tag, e))
        st[f"{part}: runs without an abort"] += 1
        return
    adaptive = [int(w["t"]) for w in rep["wd"] if w.get("why") is None]
    tie = WD_TIE * sum(max(1.0, abs(Q[u])) for u in adaptive)
    W = float(rep["at_abort"]["W_S"])
    st[f"{part}: W_S(t_a) of at_abort differs from the W_S curve"] += int(W != rep["safe"]["W_S"][ta])
    Cp, Bp, ap = (C[ta - 1], B[ta - 1], alg[ta - 1]) if ta >= 1 else (0.0, 0.0, 0.0)
    gt = GUARD_TOL * max(1.0, abs(rhs[ta - 1])) if ta >= 1 else 0.0
    eb = alg[-1] - (C[-1] + (gamma - 1.0) * Cp + W + Bp)
    X = (alg[-1] - ap) - (W + C[-1] - Cp)
    worst[f"{part}: G2(b)"] = max(worst[f"{part}: G2(b)"], eb / max(1.0, alg[-1]))
    worst[f"{part}: mode S"] = max(worst[f"{part}: mode S"], X / max(1.0, alg[-1]))
    if eb > gt + tie + flt:
        bad.append((f"{part}: G2(b)", tag, eb))
    if X > tie + flt:
        bad.append((f"{part}: mode S", tag, X))
    after_R = any(w == "R" and (f0 + n - 1) >= ta for w, f0, n in rep["safe"]["followed"])
    inh = rep["exec"]["inherited"] > 0
    st[f"{part}: aborts"] += 1
    st[f"{part}: aborts forced"] += int(bool(g["forced"]))
    st[f"{part}: aborts with S following R at a slot >= t_a"] += int(after_R)
    st[f"{part}: aborts with inherited leases"] += int(inh)
    st[f"{part}: aborts with both"] += int(after_R and inh)
    st[f"{part}: adaptive slots"] += len(adaptive)
    kept = [w for w in rep["wd"] if w.get("kept", 0) > 0]
    st[f"{part}: aborts with an adaptive slot keeping leases"] += int(bool(kept))
    st[f"{part}: aborts with an adaptive slot choosing K2"] += int(any(w.get("choice") == "K2" for w in kept))
    worst[f"{part}: TIE"] = max(worst[f"{part}: TIE"], tie / max(1.0, alg[-1]))


def guarded(part, fn, tag, errors):
    try:
        fn()
    except Exception as e:  # a run that cannot be checked is a failure of the audit
        errors.append((f"{part}: {tag}", f"{type(e).__name__}: {e}", traceback.format_exc(limit=3)))


# ================================================================ parts
def part_a(reduced, st, worst, bad, errors):
    cases = [(f"{fam}{s}", upper_case(fam, s), s) for fam in ("rand", "slo", "spiky", "setcover") for s in (0, 1, 2)]
    cases += [("c3p5_6", c3p5_case(6.0), 0), ("cm", cm_case(2, 4.0), 0)]
    if reduced:
        cases = cases[:1] + cases[-1:]
    for name, I, s in cases:
        T = int(I.T)
        om = core.random_omega(np.random.default_rng(9100 + s), I, 0.15)
        inst0, _ = from_core(I, [np.zeros(0, np.int64)] * I.m)
        lenders = [("oblivious", from_core(I, om)[0], LenderModel()),
                   ("eager", inst0, LenderModel(schedule="eager")),
                   ("adaptive", inst0, LenderModel(schedule="adaptive"))]
        for lname, inst, model in lenders:
            for safe in ("pd", "fb+pd"):
                for wd in ("auto", "release", "keep"):
                    for cls in (Guarded, ProjectedGuarded):
                        for ab in [None] + list(range(1, T, max(3, T // 6))):
                            kw = {"safe": safe, "S_rbar": "theory", "N_bound": TG._N(inst), "wind_down": wd,
                                  "gamma": 1.0, "B0": "auto", "kappa": 10.0, "on_unavailable": "sell"}
                            if ab is not None:
                                kw["abort_at"] = ab
                            tag = f"{name} {lname} safe={safe} wd={wd} {cls.__name__} abort_at={ab}"
                            guarded("a", lambda: check_run("a", inst, model, cls(inner=Renter(31 * s + len(name)),
                                                                                  **kw), 1.0, tag, st, worst, bad),
                                    tag, errors)


def core_cases_b(reduced):
    cases = [(f"{f}{s}", upper_case(f, s)) for f in ("rand", "slo", "spiky", "setcover") for s in (0, 1)]
    cases += [("c3p5_6", c3p5_case(6)), ("c3p5_30", c3p5_case(30)), ("cm24", cm_case(2, 4))]
    return cases[:1] + cases[-1:] if reduced else cases


def part_b(reduced, st, worst, bad, errors):
    k = 0                  # configuration index: A8P and A8 run the same configuration
    for name, I in core_cases_b(reduced):
        for sched in ("oblivious", "eager", "adaptive"):
            inst, model = TG._core_inst(I, sched, 3)
            for iname, mk in (("core_random", lambda s: _CoreRandom(s)), ("core_greedy", lambda s: _Greedy(s)),
                              ("BL5", lambda s: TG._inner("BL5")), ("A9", lambda s: NoticeCriticalRatio())):
                for wd in ("auto", "release", "keep"):
                    gamma = (0.5, 1.0, G2)[k % 3]
                    safe = ("fb+pd", "pd")[k % 2]
                    allow = ({"B0": 0.0, "kappa": None}, {"B0": "auto", "kappa": 10.0},
                             {"B0": "auto", "kappa": None})[(k // 3) % 3]
                    kw = {"safe": safe, "S_rbar": "theory", "N_bound": TG._N(inst), "gamma": gamma, "wind_down": wd,
                          **allow}
                    if (k // 2) % 2 == 1:
                        kw["abort_at"] = 1 + (k % 7)
                    for cls in (ProjectedGuarded, Guarded):
                        tag = (f"{name} {sched} {iname} wd={wd} {cls.__name__} gamma={gamma:.4g} safe={safe} "
                               f"B0={allow['B0']} kappa={allow['kappa']} abort_at={kw.get('abort_at')}")
                        guarded("b", lambda: check_run("b", inst, model, cls(inner=mk(50 + k), **kw), gamma, tag, st,
                                                       worst, bad), tag, errors)
                    k += 1


def part_c(reduced, st, worst, bad, errors):
    k = 0
    for name, I in core_cases_b(reduced):
        for sched in ("oblivious", "eager", "adaptive"):
            inst, model = TG._core_inst(I, sched, 3)
            for iname, mk in (("core_random", lambda s: _CoreRandom(s)), ("core_greedy", lambda s: _Greedy(s)),
                              ("A9", lambda s: NoticeCriticalRatio())):
                for wd in ("auto", "release", "keep"):
                    gamma = (1.0, G2)[k % 2]
                    safe = ("fb+pd", "pd")[(k // 2) % 2]
                    for ab in (None, 2):
                        kw = {"safe": safe, "S_rbar": "theory", "N_bound": TG._N(inst), "gamma": gamma,
                              "wind_down": wd, "allowance": "lb", "kappa": None}
                        if ab is not None:
                            kw["abort_at"] = ab
                        tag = f"{name} {sched} {iname} wd={wd} gamma={gamma:.4g} safe={safe} lb abort_at={ab}"
                        guarded("c", lambda: check_run("c", inst, model, ProjectedGuarded(inner=mk(70 + k), **kw),
                                                       gamma, tag, st, worst, bad), tag, errors)
                    k += 1


def main():
    reduced = "--reduced" in sys.argv
    t0 = time.time()
    st, worst, bad, errors = Counter(), Counter(), [], []
    for p in ("a", "b", "c"):
        for key in ("G2(a)", "G2(b)", "mode S", "m", "TIE"):
            worst[f"{p}: {key}"] = -np.inf
    part_a(reduced, st, worst, bad, errors)
    part_b(reduced, st, worst, bad, errors)
    part_c(reduced, st, worst, bad, errors)
    wall = time.time() - t0
    L = ["X13: Theorem G2 for A8 and A8P on core exports, with S following R after the abort "
         "(design/theory/c3_c4_c5_general.md §9, Theorem G2 and \"A8's mode S on core exports\"; audit addendum of "
         "step P6 in design/theory/audit_guard.md, finding REMARK_R-F1)",
         "checked from the ledger and the guard's report: G2(a), G2(b), the mode-S step and soundness; script "
         "code/sim/audit/x13_core_mode_s.py",
         f"runs: (a) {st['a: runs']}, (b) {st['b: runs']}, (c) {st['c: runs']} "
         f"({'reduced' if reduced else 'default'}); run errors: {len(errors)}; wall time {wall:.0f} s on one worker",
         f"tolerances: GUARD_TOL {GUARD_TOL:g} max(1, |rhs|) at the last executed slot; TIE = WD_TIE {WD_TIE:g} sum "
         f"over the adaptive slots of max(1, |Q(u)|); FLT {FLT:g} max(1, ALG(T)); soundness CERT_TOL {CERT_TOL:g} "
         "max(1, ALG(u))", ""]
    titles = {"a": "(a) Renter, A8 and A8P, gamma 1, B0 'auto', kappa 10:",
              "b": "(b) _CoreRandom, _Greedy, BL5 and A9, A8P and A8, gamma, safe, allowance and abort_at cycling:",
              "c": "(c) A8P at the allowance 'lb' around _CoreRandom, _Greedy and A9:"}
    for p in ("a", "b", "c"):
        L.append(titles[p])
        for key in ("runs", "runs Guarded", "runs ProjectedGuarded", "runs without an abort", "aborts",
                    "aborts forced", "aborts with S following R at a slot >= t_a", "aborts with inherited leases",
                    "aborts with both", "aborts with an adaptive slot keeping leases",
                    "aborts with an adaptive slot choosing K2", "adaptive slots", "projected slots",
                    "W_S(t_a) of at_abort differs from the W_S curve"):
            L.append(f"  {key}: {st[f'{p}: {key}']}")
        L.append("  worst relative excesses (excess / max(1, ALG(T))): "
                 + ", ".join(f"{key} {worst[f'{p}: {key}']:.6e}" for key in ("G2(a)", "G2(b)", "mode S")))
        L.append(f"  largest TIE / max(1, ALG(T)): {worst[f'{p}: TIE']:.6e}; largest m(u) / max(1, ALG(u)): "
                 f"{worst[f'{p}: m']:.6e}")
    kinds = Counter(b[0] for b in bad)
    L.append("failures by kind: " + (", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) or "none"))
    for kind, tag, detail in bad[:20]:
        L.append(f"  FAIL {kind}: {tag}: {detail}")
    for tag, msg, tb in errors[:10]:
        L.append(f"  ERROR {tag}: {msg}")
        L.append("    " + tb.strip().replace("\n", "\n    "))
    L.append(f"violations: {len(bad)}, errors: {len(errors)}")
    print("\n".join(L), flush=True)
    return int(len(bad) > 0 or len(errors) > 0)


if __name__ == "__main__":
    if main():   # exit status 1 on a violation, an engine invariant failure or a run error (run_all.sh counts it)
        print("x13: a violation of G2, of the mode-S step or of soundness, or a run error", file=sys.stderr)
        sys.exit(1)
