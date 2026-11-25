"""Naive spend caps (design/theory/naive_caps.md; design/ms8/plan.md D2, X6): the four instances of the naive-cap
result, each in exact arithmetic on the core model of c3/core.py (Fractions) and through the simulator's engine with the
policy CAP (code/sim/sublet/algos/budget_cap.py) and Algorithm 1 (A8 at T0g, A8P at the allowance 'lb').

  (a) I_n (Proposition G6(i)'s core instance, c3/core.py): one site, one LLM, one contract tau = H = 1 (L = 2),
      g = a = beta = 1 (C = 3), q = 2, n clients with delta = 0 active at slot 1 only, T = 2; the inner policy E_n buys
      n leases at slot 0. Stated: FB(T) = 2n, OPT_eager = 3; the 'paid' cap (stop and latch) pays ALG = 3n, so its
      excess over FB + X is n - X; the 'slot' cap pays 2n (it drops the purchases once 3n > X); A8 (T0g) and A8P
      ('lb') pay 2n.
  (b) J_T (core, from_core with no announcement): one site, one LLM, one contract tau = 1, H = 0 (L = 1), g = a = 1,
      beta = 0 (C = 1), q = 2, one client active at slot 0 only, horizon T; the inner buys one lease at slot 0 and never
      releases it, the lender never ends it. Stated: FB(T) = 2; under 'stop' the cap pays ALG = T with either count,
      so its excess T - 2 - X grows linearly in T; under 'latch' it pays X + 3 ('paid', integer X, T > X + 3) and X + 2
      ('slot', T > X + 2); A8P at the constant allowance X pays floor(X) + 2 (K0 releases the lease once its rent
      would cross the line); A8P at 'lb' pays 3 = FB(T) + B(T), with B(T) = min{W_k, LB'} = 1 (one billed term of
      one replica): it keeps the lease while ALG(t - 1) + rent <= FB + B and its K0 releases it at slot 3.
  (c) K_n (core export with a stranding charge mu^fb = mu > 0 per replica load moved to fallback, rule T11): one site,
      one LLM, one contract tau = 1, H = 0 (L = 1), g = 1, a = n q, beta = 0 (C = n q, the fallback cost that the lease
      saves in its slot), q = 1, n clients with delta = 0 active at every slot of T = 3, kappa infinite (one replica
      serves every client); the inner buys one lease at slot 0, the eager lender ends it at slot 1 (tau = 1, H = 0).
      Stated: FB(T) = 3 n q; every cap variant ('paid' or 'slot', 'stop' or 'latch') pays ALG = FB(T) + n mu, so its
      excess over FB + X is n mu - X; A8P ('lb') stays at or below FB(T) + B(T) (Theorem W).
  (d) U_n (core, no stranding): two sites, one LLM, one contract tau = 1, H = 0 (L = 1), g = 1, beta = 0, a = 1 at
      site 0 and a = n q at site 1 (C = n q = Q(0) there), q = 1, n clients active at slot 0 with delta = 0 to site 0
      and delta = inf to site 1 (site 1 serves nobody), T = 1; the inner buys one lease at site 1 at slot 0. Stated:
      FB(T) = n q, OPT_eager = 1; no cap binds ('slot': n q <= FB(-1) + Q(0) + X, the slot's service priced at 0), so
      every cap pays ALG = 2 n q and its excess over FB + X is n q - X.
In every part A8P at the cap's own constant allowance (B0 = X, kappa None, safe expert all-fallback) stays at or below
FB(T) + X (Theorem W(a)(b)): with the same allowance, Algorithm 1 keeps the line that each cap crosses. Its exact values
(design/theory/naive_caps.md, the closing sentence of Proposition N) are checked too: on I_n 2n if X < 3, 3n if 3n <= X
and 3 otherwise; floor(X) + 2 on J_T (also at X = 1.5); on K_n FB(T) + n mu if n mu <= X and FB(T) otherwise; on U_n
2 n q if n q <= X and n q otherwise.
Exits 1 if a stated value fails (exact for the core values; engine values within 1e-9 relative). Writes
out/check_naive_cap.json and prints the table (out/check_naive_cap.txt when run through run_all.sh, or by hand:
  python check_naive_cap.py > out/check_naive_cap.txt).
"""
from __future__ import annotations

import dataclasses
import json
import math
import os
import sys
from fractions import Fraction as Fr
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
C3 = HERE.parent
REPO = C3.parents[2]
SIM = REPO / "code" / "sim"
for d in (str(C3), str(SIM)):
    if d not in sys.path:
        sys.path.insert(0, d)

import core                                                         # noqa: E402  (c3/core.py)

from sublet.algos.budget_cap import BudgetCapped                   # noqa: E402
from sublet.algos.guard import Guarded, ProjectedGuarded           # noqa: E402
from sublet.engine import simulate                                 # noqa: E402
from sublet.instance import from_core                              # noqa: E402
from sublet.policies.base import Policy                            # noqa: E402
from sublet.types import Buy, LenderModel                          # noqa: E402

REL = 1e-9
FAIL: list = []
ROWS: list = []
CAPS = (("paid", "stop"), ("paid", "latch"), ("slot", "stop"), ("slot", "latch"))


def check(name: str, got, want, exact: bool = False, le: bool = False) -> None:
    """Record one stated value: equal (exactly, or within REL relative), or at most `want` with le."""
    g, w = (Fr(got), Fr(want)) if exact else (float(got), float(want))
    if le:
        ok = g <= w if exact else g <= w + REL * max(1.0, abs(w))
    else:
        ok = g == w if exact else abs(g - w) <= REL * max(1.0, abs(w))
    ROWS.append({"check": name, "got": float(got), "want": float(want), "relation": "<=" if le else "=",
                 "exact": exact, "ok": bool(ok)})
    if not ok:
        FAIL.append(name)


class Script(Policy):
    """An inner policy that plays a fixed list of actions per slot (and nothing else); wants_fast false."""
    name = "script"

    def __init__(self, plan: dict):
        self.plan = {int(k): list(v) for k, v in plan.items()}

    def reset(self, view, rng):
        super().reset(view, rng)

    def act(self, obs):
        return list(self.plan.get(int(obs.t), []))


def engine(inst, pol, schedule: str = "trace") -> tuple[float, dict]:
    res = simulate(inst, pol, LenderModel(schedule=schedule), policy_rng=np.random.default_rng(0))
    if res.invariant_failures:
        raise RuntimeError(f"invariant failures: {res.invariant_failures[:3]}")
    return float(res.components["total"]), res.metrics.get("policy") or {}


def b_of(rep: dict) -> float:
    """B(T) of a CAP, A8 or A8P report."""
    if "online_lb" in rep:
        return float(rep["online_lb"]["B_T"])
    return float((rep.get("safe") or {}).get("B_curve", [0.0])[-1])


def a8p_const(inner_plan: dict, X: float) -> ProjectedGuarded:
    """Algorithm 1 (A8P) at the cap's own constant allowance: B(t) = B0 = X (allowance 'alg1', kappa None), the safe
    expert all-fallback, so Theorem W(a)(b) gives ALG(T) <= FB(T) + X."""
    return ProjectedGuarded(inner=Script(inner_plan), allowance="alg1", B0=float(X), kappa=None, safe="fb")


# ---------------------------------------------------------------- core arithmetic of a cap (exact, c3/core.py)
def core_cap(I, plan: dict, X: Fr, count: str, on_bind: str, death=None, site: int = 0, serves: bool = True) -> Fr:
    """ALG(T) of a cap around the scripted inner `plan` ({t: number of leases of (l, j, k) = (site, 0, 0) bought at t})
    on the core instance I, in Fractions: a lease bought at s costs C = beta + g a L at s (prepaid L slots), then rents
    g a per slot until released or dead (`death(s)` the slot from which it is gone, None: never), and, if `serves`,
    serves every client of the slot (delta = 0; one lease serves all, kappa infinite), otherwise none (delta = inf); a
    slot without a live serving lease pays q per active client. No stranding (the core). The cap: 'paid' binds iff
    ALG(t-1) > FB(t-1) + X; 'slot' iff ALG(t-1) + p(t) + rent(t) > FB(t-1) + Q(t) + X; 'stop' drops the slot's
    purchases, 'latch' releases every lease and stops."""
    C, r = Fr(I.C(site, 0, 0)), Fr(I.rent(site, 0, 0))
    L = int(I.L[0])
    q = Fr(I.q)
    live: list = []                                  # start slots of the held leases
    alg = fb = Fr(0)
    latched = False
    for t in range(I.T):
        Q = q * int(I.active[:, t].sum())
        live = [s for s in live if death is None or death(s) is None or t < death(s)]
        buys = 0 if latched else int(plan.get(t, 0))
        p = C * buys
        rent = r * sum(1 for s in live if t >= s + L)
        lhs, rhs = alg, fb + X
        if count == "slot":
            lhs, rhs = lhs + p + rent, rhs + Q
        if not latched and lhs > rhs:
            if on_bind == "latch":
                latched, live, buys = True, [], 0
            else:
                buys = 0
        live += [t] * buys
        cost = C * buys + r * sum(1 for s in live if t >= s + L)
        cost += Fr(0) if (live and serves) else Q
        alg += cost
        fb += Q
    return alg


# ---------------------------------------------------------------- (a) I_n
def opt_value(r) -> float:
    """The objective of core.opt_eager's return value (a number, a tuple or a dict)."""
    if isinstance(r, dict):
        return float(r["fun"])
    if isinstance(r, (tuple, list)):
        return float(r[0])
    return float(r)


def want_a(n: int, X: float, count: str, on_bind: str) -> int:
    """ALG of a cap on I_n by hand (design/theory/naive_caps.md, part (a)): 'paid' buys the n leases at slot 0 (0 > X
    fails); 'stop' then pays 3n; 'latch' binds at slot 1 iff 3n > X and then releases the leases, so slot 1 falls back
    (3n + 2n). 'slot' binds at slot 0 iff 3n > X (p(0) = 3n, Q(0) = 0) and then buys nothing (2n); otherwise it buys,
    and at slot 1 (lhs 3n, rhs 2n + X) 'latch' releases iff n > X (5n), 'stop' has nothing to drop (3n)."""
    if count == "paid":
        return 5 * n if (on_bind == "latch" and 3 * n > X) else 3 * n
    if 3 * n > X:
        return 2 * n
    return 5 * n if (on_bind == "latch" and n > X) else 3 * n


def part_a() -> dict:
    out = {}
    for n in (4, 64, 1024):
        I = core.Instance(T=2, tau=np.array([1]), H=np.array([1]), a=np.array([[1.0]]), beta=np.array([[1.0]]),
                          g=np.array([1]), q=2.0, cl_llm=np.zeros(n, dtype=int), delta=np.zeros((n, 1)),
                          active=np.array([[False, True]] * n))
        fb = 2 * n
        check(f"a n={n} C", I.C(0, 0, 0), 3, exact=True)
        if n <= 64:
            check(f"a n={n} OPT_eager", opt_value(core.opt_eager(I)), 3)
        inst, _ = from_core(I, [np.zeros(0, np.int64)])
        row = {"n": n, "FB": fb}
        for X in (0, 3, 30):
            for count, ob in CAPS:
                want = want_a(n, X, count, ob)
                got_core = core_cap(I, {0: n}, Fr(X), count, ob)
                check(f"a n={n} X={X} {count}/{ob} core", got_core, want, exact=True)
                alg, rep = engine(inst, BudgetCapped(inner=Script({0: [Buy(0, 0, 0, 1)] * n}), X=float(X),
                                                     count=count, on_bind=ob), "eager")
                check(f"a n={n} X={X} {count}/{ob} engine", alg, want)
                row[f"X={X} {count}/{ob}"] = alg
            check(f"a n={n} X={X} paid/stop excess n - X", want_a(n, X, "paid", "stop") - fb - X, n - X, exact=True)
            alg, _ = engine(inst, a8p_const({0: [Buy(0, 0, 0, 1)] * n}, X), "eager")
            check(f"a n={n} X={X} A8P B0=X <= FB + X", alg, fb + X, le=True)
            check(f"a n={n} X={X} A8P B0=X", alg, 2 * n if X < 3 else (3 * n if 3 * n <= X else 3))
            row[f"X={X} A8P B0=X"] = alg
        for name, pol in (("A8 T0g", Guarded(inner=Script({0: [Buy(0, 0, 0, 1)] * n}), safe="fb", test="T0g",
                                             B0="auto", kappa=10.0)),
                          ("A8P lb", ProjectedGuarded(inner=Script({0: [Buy(0, 0, 0, 1)] * n}), allowance="lb",
                                                      kappa=None, safe="fb"))):
            alg, rep = engine(inst, pol, "eager")
            check(f"a n={n} {name}", alg, 2 * n)
            check(f"a n={n} {name} <= FB + B", alg, fb + b_of(rep), le=True)
            row[name] = alg
        out[str(n)] = row
    return out


# ---------------------------------------------------------------- (b) J_T
def part_b() -> dict:
    out = {}
    for T in (5, 50, 500):
        act = np.zeros((1, T), dtype=bool)
        act[0, 0] = True
        I = core.Instance(T=T, tau=np.array([1]), H=np.array([0]), a=np.array([[1.0]]), beta=np.array([[0.0]]),
                          g=np.array([1]), q=2.0, cl_llm=np.zeros(1, dtype=int), delta=np.zeros((1, 1)), active=act)
        inst, _ = from_core(I, [np.zeros(0, np.int64)])
        row = {"T": T, "FB": 2}
        for X in (0, 1, 2):
            for count, ob in CAPS:
                if ob == "stop":
                    want = T
                else:
                    want = min(T, X + 3) if count == "paid" else min(T, X + 2)
                got_core = core_cap(I, {0: 1}, Fr(X), count, ob)
                check(f"b T={T} X={X} {count}/{ob} core", got_core, want, exact=True)
                alg, _ = engine(inst, BudgetCapped(inner=Script({0: [Buy(0, 0, 0, 1)]}), X=float(X), count=count,
                                                   on_bind=ob))
                check(f"b T={T} X={X} {count}/{ob} engine", alg, want)
                row[f"X={X} {count}/{ob}"] = alg
            check(f"b T={T} X={X} stop excess T - 2 - X", T - 2 - X, T - 2 - X, exact=True)
            alg, _ = engine(inst, a8p_const({0: [Buy(0, 0, 0, 1)]}, X))
            check(f"b T={T} X={X} A8P B0=X = floor(X) + 2", alg, math.floor(X) + 2)
            check(f"b T={T} X={X} A8P B0=X <= FB + X", alg, 2 + X, le=True)
            row[f"X={X} A8P B0=X"] = alg
        alg, _ = engine(inst, a8p_const({0: [Buy(0, 0, 0, 1)]}, 1.5))
        check(f"b T={T} X=1.5 A8P B0=X = floor(X) + 2", alg, 3)
        check(f"b T={T} X=1.5 A8P B0=X <= FB + X", alg, 2 + 1.5, le=True)
        row["X=1.5 A8P B0=X"] = alg
        alg, rep = engine(inst, ProjectedGuarded(inner=Script({0: [Buy(0, 0, 0, 1)]}), allowance="lb", kappa=None,
                                                 safe="fb"))
        check(f"b T={T} A8P lb B(T)", b_of(rep), 1)
        check(f"b T={T} A8P lb", alg, 3)
        check(f"b T={T} A8P lb <= FB + B", alg, 2 + b_of(rep), le=True)
        row["A8P lb"] = alg
        out[str(T)] = row
    return out


# ---------------------------------------------------------------- (c) K_n
def part_c() -> dict:
    out = {}
    q, mu = 1.0, 0.5
    for n in (4, 64, 1024):
        I = core.Instance(T=3, tau=np.array([1]), H=np.array([0]), a=np.array([[n * q]]), beta=np.array([[0.0]]),
                          g=np.array([1]), q=q, cl_llm=np.zeros(n, dtype=int), delta=np.zeros((n, 1)),
                          active=np.ones((n, 3), dtype=bool))
        inst, _ = from_core(I, [np.zeros(0, np.int64)])
        st = inst.stranding
        inst.stranding = dataclasses.replace(st, mu_fb_usd=np.full_like(np.asarray(st.mu_fb_usd, dtype=float), mu))
        fb = 3 * n * q
        # the core value without stranding: the lease saves exactly its cost in slot 0, then all fallback
        check(f"c n={n} core cost without stranding", core_cap(I, {0: 1}, Fr(0), "paid", "stop", death=lambda s: s + 1),
              Fr(3 * n) * Fr(q), exact=True)
        row = {"n": n, "FB": fb, "mu": mu}
        for X in (0.0, 5.0, 50.0):
            for count, ob in CAPS:
                alg, rep = engine(inst, BudgetCapped(inner=Script({0: [Buy(0, 0, 0, 1)]}), X=X, count=count,
                                                     on_bind=ob), "eager")
                check(f"c n={n} X={X:g} {count}/{ob} engine", alg, fb + n * mu)
                row[f"X={X:g} {count}/{ob}"] = alg
                row[f"X={X:g} {count}/{ob} excess"] = alg - fb - X
            alg, _ = engine(inst, a8p_const({0: [Buy(0, 0, 0, 1)]}, X), "eager")
            check(f"c n={n} X={X:g} A8P B0=X <= FB + X", alg, fb + X, le=True)
            check(f"c n={n} X={X:g} A8P B0=X", alg, fb + n * mu if n * mu <= X else fb)
            row[f"X={X:g} A8P B0=X"] = alg
        alg, rep = engine(inst, ProjectedGuarded(inner=Script({0: [Buy(0, 0, 0, 1)]}), allowance="lb", kappa=None,
                                                 safe="fb"), "eager")
        check(f"c n={n} A8P lb <= FB + B", alg, fb + b_of(rep), le=True)
        row["A8P lb"], row["A8P B_T"] = alg, b_of(rep)
        out[str(n)] = row
    return out


# ---------------------------------------------------------------- (d) U_n
def part_d() -> dict:
    out = {}
    q = 1.0
    for n in (4, 64, 1024):
        I = core.Instance(T=1, tau=np.array([1]), H=np.array([0]), a=np.array([[1.0], [n * q]]),
                          beta=np.array([[0.0, 0.0]]), g=np.array([1]), q=q, cl_llm=np.zeros(n, dtype=int),
                          delta=np.column_stack([np.zeros(n), np.full(n, np.inf)]),
                          active=np.ones((n, 1), dtype=bool))
        fb = n * q
        check(f"d n={n} C site 1 = Q(0)", I.C(1, 0, 0), Fr(n) * Fr(q), exact=True)
        if n <= 64:
            check(f"d n={n} OPT_eager", opt_value(core.opt_eager(I)), 1)
        inst, _ = from_core(I, [np.zeros(0, np.int64)] * 2)
        plan = {0: [Buy(1, 0, 0, 1)]}
        row = {"n": n, "FB": fb}
        for X in (0.0, 5.0, 50.0):
            for count, ob in CAPS:
                got_core = core_cap(I, {0: 1}, Fr(X), count, ob, site=1, serves=False)
                check(f"d n={n} X={X:g} {count}/{ob} core", got_core, Fr(2 * n) * Fr(q), exact=True)
                alg, rep = engine(inst, BudgetCapped(inner=Script(plan), X=X, count=count, on_bind=ob))
                check(f"d n={n} X={X:g} {count}/{ob} engine", alg, 2 * fb)
                check(f"d n={n} X={X:g} {count}/{ob} no bind", (rep.get("cap") or {}).get("bind_slots"), 0)
                row[f"X={X:g} {count}/{ob}"] = alg
                row[f"X={X:g} {count}/{ob} excess"] = alg - fb - X
            alg, _ = engine(inst, a8p_const(plan, X))
            check(f"d n={n} X={X:g} A8P B0=X <= FB + X", alg, fb + X, le=True)
            check(f"d n={n} X={X:g} A8P B0=X", alg, 2 * fb if fb <= X else fb)
            row[f"X={X:g} A8P B0=X"] = alg
        alg, rep = engine(inst, ProjectedGuarded(inner=Script(plan), allowance="lb", kappa=None, safe="fb"))
        check(f"d n={n} A8P lb <= FB + B", alg, fb + b_of(rep), le=True)
        row["A8P lb"], row["A8P B_T"] = alg, b_of(rep)
        out[str(n)] = row
    return out


def main() -> int:
    res = {"a": part_a(), "b": part_b(), "c": part_c(), "d": part_d()}
    w = max(len(r["check"]) for r in ROWS)
    for r in ROWS:
        print(f"{r['check']:<{w}}  {r['relation']} {r['want']:>14.6f}  got {r['got']:>14.6f}  "
              f"{'ok' if r['ok'] else 'FAIL'}")
    print(f"[check_naive_cap] {len(ROWS)} checks, {len(FAIL)} violations")
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "check_naive_cap.json").write_text(json.dumps({"checks": ROWS, "violations": FAIL, "values": res},
                                                         indent=1) + "\n")
    return 1 if FAIL else 0


if __name__ == "__main__":
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    sys.exit(main())
