"""X4: Theorem W end to end with natural (unforced) aborts: A8 under T0g, reserve on, wind-down 'adaptive' or
'release', small constant allowances and gamma in {0.5, 1, 1.7}, safe 'fb' and the default 'fb+pd', around
random inner policies on rich instances. Checked from the ledger: (a) without an abort ALG(T) <= gamma C_S(T) + B(T)
- R(T-1); (b) with an abort and S following FB from t_a on, ALG(T) <= C_S(T) + (gamma - 1) C_S(t_a - 1) + B(t_a - 1)
- [R(t_a - 1) - Phi(t_a)] and Phi(t_a) <= R(t_a - 1). Runs in which S follows R at some slot >= t_a (case (c)) are
counted, and their excess over the bound of (b) with W_S(t_a) is recorded (not a violation of a proven claim).
Usage: x4_natural_aborts.py [n_seeds] (default 2).
Audit of the full-model guard (design/theory/audit_guard.md); code/sim/audit/, run by run_all.sh, output
code/sim/out/audit_fm/x4_out.txt."""
import sys
import time
from collections import Counter

import numpy as np

import audit_env  # noqa: F401
from audit_env import TG
from x2_random_search import MODELS, Adv, rich, EXTRA
from sublet.algos.guard import Guarded
from sublet.engine import EngineConfig, simulate
from sublet.types import LenderModel

TOL = 1e-9


def main():
    nseeds = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    st = Counter()
    worst = {"a": -np.inf, "b": -np.inf, "phi": -np.inf, "c": -np.inf}
    t0 = time.time()
    nvar = len(TG._RICH) + len(EXTRA)
    for s in range(nseeds):
        for v in range(nvar):
            for i, (mname, lm) in enumerate(MODELS.items()):
                kinf = bool((s + v + i) % 2)
                inst = rich(5000 + 31 * s + 7 * v + i, v, kinf)
                Q = TG._q_slot(inst)
                N = TG._N(inst)
                for gamma in (0.5, 1.0, 1.7):
                    for B0 in (0.0, 0.5, "auto"):
                        for safe in ("fb", "fb+pd"):
                            rule = ("adaptive", "release")[(s + v + i) % 2]
                            Inner = Adv if (s + i + v) % 2 else TG._RandomInner
                            onu = "refuse" if lm.get("on_unavailable") == "refuse" else None
                            pol = Guarded(inner=Inner(97 * s + v + 13 * i), test="T0g", safe=safe, gamma=gamma,
                                          B0=B0, kappa=None, wind_down=rule, on_unavailable=onu,
                                          N_bound=N if safe != "fb" else None)
                            res = simulate(inst, pol, LenderModel(**lm), EngineConfig(auto_drain=bool(s % 2)),
                                           policy_seed=s)
                            assert res.invariant_failures == [], res.invariant_failures[:2]
                            rep = res.metrics["policy"]
                            tot = np.asarray(res.per_slot["total"], dtype=float)
                            ALG = float(tot.sum())
                            scale = max(1.0, ALG)
                            CS = np.asarray(rep["safe"]["C_S_curve"], dtype=float)
                            Bc = np.asarray(rep["safe"]["B_curve"], dtype=float)
                            g = rep["guard"]
                            t_a = rep["t_a"]
                            st["runs"] += 1
                            if t_a is None:
                                T = len(CS)
                                bound = gamma * CS[-1] + Bc[-1] - g["reserve"][T - 1]
                                worst["a"] = max(worst["a"], (ALG - bound) / scale)
                                if ALG - bound > TOL * scale:
                                    print("VIOL (a)", mname, v, s, gamma, B0, safe, ALG, bound, flush=True)
                                    st["viol"] += 1
                                continue
                            st["aborts"] += 1
                            fol = rep["safe"]["followed"]
                            fb_after = all(w == "FB" for w, a, n in fol if a + n > t_a)
                            phi = np.cumsum((tot - Q)[::-1])[::-1][t_a]
                            R = g["reserve"][t_a - 1] if t_a > 0 else 0.0
                            CSp = CS[t_a - 1] if t_a > 0 else 0.0
                            Bp = Bc[t_a - 1] if t_a > 0 else 0.0
                            bound = CS[-1] + (gamma - 1) * CSp + Bp
                            if fb_after:
                                st["proven"] += 1
                                worst["b"] = max(worst["b"], (ALG - bound) / scale)
                                worst["phi"] = max(worst["phi"], (phi - R) / scale)
                                if ALG - bound > TOL * scale or phi - R > TOL * scale:
                                    print("VIOL (b)", mname, v, s, gamma, B0, safe, t_a, ALG, bound, phi, R,
                                          flush=True)
                                    st["viol"] += 1
                                st["held"] += int(rep["exec"]["inherited"] > 0)
                            else:
                                st["case_c"] += 1
                                worst["c"] = max(worst["c"], (ALG - bound - rep["W_S_t_a"]) / scale)
    print(f"{dict(st)} worst (rel): {worst}  {time.time() - t0:.0f} s", flush=True)
    # case (c) is CONJECTURE and only recorded; (a), (b) and Phi(t_a) <= R(t_a - 1) are the proven claims
    return int(st["viol"] > 0 or max(worst["a"], worst["b"], worst["phi"]) > TOL)


if __name__ == "__main__":
    if main():                                       # exit status 1 on a violation (run_all.sh counts it)
        print("x4: Theorem W(a) or (b) violated beyond the tolerance", file=sys.stderr)
        sys.exit(1)
