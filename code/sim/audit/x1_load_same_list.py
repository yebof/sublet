"""X1 (finding F1): a Load on a lease that the same list buys (Buy, Unload of its replica, Load on the new lease).

Audit of the full-model guard (design/theory/audit_guard.md); code/sim/audit/, run by run_all.sh, output
code/sim/out/audit_fm/x1_out.txt. Toy instance with beta = 0 and 0.4 at every site; the inner policy is idle until
slot T-1 and then issues [Buy(P, prot, 0, 1), Unload(0), Load(0, 0)]. The engine accepts the Load (the Unload frees
the GPUs) and charges beta_jl. Before the fix, slot_terms skipped it, so ALG(T-1) exceeded a-hat(T-1) by beta, and
with B0 set to make slot T-1's test an equality Theorem W(a) failed by beta (scratch output: m(T-1) = 0.4,
violation 0.4). With the fix m(T-1) = 0 and no violation, for every beta."""
import sys

import numpy as np

import audit_env  # noqa: F401
from fixtures import toy_instance
from sublet.algos.guard import Guarded
from sublet.engine import simulate
from sublet.policies.base import Policy
from sublet.types import Buy, LenderModel, Load, Unload


class Late(Policy):
    name = "late"

    def __init__(self, t_act):
        self.t_act = t_act

    def act(self, obs):
        if int(obs.t) != self.t_act:
            return []
        P = next(l for l, s in enumerate(self.view.sites) if s.kind == "protected")
        k = sorted(self.view.sites[P].menu)[0]
        # no earlier purchase: the new lease gets id 0 and its replica id 0
        return [Buy(P, k, 0, 1), Unload(0), Load(0, 0)]


def run(inst, B0, gamma=1.0):
    T = inst.grid.T_slow
    pol = Guarded(inner=Late(T - 1), test="T0g", safe="fb", gamma=gamma, B0=B0, kappa=None)
    res = simulate(inst, pol, LenderModel(), policy_seed=0)
    return res, res.metrics["policy"]


def main():
    viol = 0
    for beta in (0.0, 0.4):
        inst = toy_instance({})
        inst.beta_usd = np.full_like(np.asarray(inst.beta_usd, dtype=float), beta)
        T = inst.grid.T_slow
        res, rep = run(inst, 1e12)
        assert rep["t_a"] is None and res.invariant_failures == []
        alg = np.cumsum(res.per_slot["total"])
        g = rep["guard"]
        ah, R, CS = g["a_hat"][T - 1], g["reserve"][T - 1], g["C_S"][T - 1]
        m = alg[T - 1] - ah
        print(f"beta={beta}: ALG(T)={alg[-1]:.6f} a_hat(T-1)={ah:.6f} m(T-1)={m:.6f} "
              f"loading booked at T-1={res.per_slot['loading'][T-1]:.4f} form={rep['t0g']['forms']} "
              f"robust_slots={rep['t0g']['robust_slots']}")
        B0 = ah + R - CS
        res2, rep2 = run(inst, B0)
        alg2 = float(np.sum(res2.per_slot["total"]))
        g2 = rep2["guard"]
        bound = g2["C_S"][T - 1] + B0 - g2["reserve"][T - 1]
        print(f"   B0={B0:.6f}: aborted={rep2['aborted']}  ALG(T)={alg2:.6f}  "
              f"gamma C_S(T)+B(T)-R(T-1)={bound:.6f}  violation={alg2 - bound:.6f}")
        viol += int(m > 1e-9 * max(1.0, alg[-1]) or alg2 - bound > 1e-9 * max(1.0, alg2))
    print(f"violations: {viol}")
    return viol


if __name__ == "__main__":
    if main():                                       # exit status 1 on a violation (run_all.sh counts it)
        print("x1: violation of F1's fix or of Theorem W(a)", file=sys.stderr)
        sys.exit(1)
