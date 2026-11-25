"""X3 (finding F2): an inner policy that writes to its observation.

Audit of the full-model guard (design/theory/audit_guard.md); code/sim/audit/, run by run_all.sh, output
code/sim/out/audit_fm/x3_out.txt. Toy instance (gamma = 1, B0 = 2); the inner policy releases every held lease and
buys one protected lease per slot. Before the fix the guard read obs after the inner policy had it, so an inner that
set obs.cost_so_far = 0 was never aborted and ALG(T) exceeded even (1 + gamma) C_S(T) + B(T) (scratch output:
mutate=True, t_a=None, ALG(T) = 21.473). With the fix (the inner acts on a private copy, guard.inner_obs) every
writing variant runs exactly as the policy that does not write: the first two lines are the audit's, the further
ones write after choosing their actions to obs.leases (cleared), obs.replicas (cleared), obs.results (cleared),
obs.ended (cleared) and obs.demand (zeroed), and each line reports whether the run equals the non-writing run
(per-slot totals and the guard's a-hat) and whether ALG(T) <= gamma C_S(T) + B(T)."""
import sys

import numpy as np

import audit_env  # noqa: F401
from fixtures import toy_instance
from sublet.algos.guard import Guarded
from sublet.engine import simulate
from sublet.policies.base import Policy
from sublet.types import Buy, LenderModel, Release


class Mutator(Policy):
    name = "mutator"

    def __init__(self, mutate):
        self.mutate = mutate

    def act(self, obs):
        P = next(l for l, s in enumerate(self.view.sites) if s.kind == "protected")
        if self.mutate is True or self.mutate == "cost":
            obs.cost_so_far = 0.0
        acts = [Release(l) for l in obs.leases] + [Buy(P, sorted(self.view.sites[P].menu)[0], 0, 1)]
        if self.mutate in ("leases", "replicas", "results", "ended"):
            getattr(obs, self.mutate).clear()
        elif self.mutate == "demand":
            obs.demand[...] = 0.0
        return acts


def run(mutate):
    inst = toy_instance({})
    pol = Guarded(inner=Mutator(mutate), test="T0g", safe="fb", gamma=1.0, B0=2.0, kappa=None)
    res = simulate(inst, pol, LenderModel(), policy_seed=0)
    return res, res.metrics["policy"]


def main():
    ref, rref = run(False)
    viol = 0
    for mutate in (False, True, "leases", "replicas", "results", "ended", "demand"):
        res, rep = run(mutate)
        ALG = float(np.sum(res.per_slot["total"]))
        CS, B = rep["safe"]["C_S_curve"][-1], rep["safe"]["B_curve"][-1]
        same = bool(np.array_equal(res.per_slot["total"], ref.per_slot["total"])
                    and rep["guard"]["a_hat"] == rref["guard"]["a_hat"] and rep["t_a"] == rref["t_a"])
        ok = ALG <= CS + B + 1e-9 * max(1.0, ALG)
        viol += int(not ok or not same)
        label = mutate if isinstance(mutate, str) else f"mutate={mutate}"
        print(f"{label}: t_a={rep['t_a']} ALG(T)={ALG:.3f} gamma C_S(T)+B(T)={CS + B:.3f} "
              f"(1+gamma) C_S(T) + B(T) = {2 * CS + B:.3f}  same as the non-writing run: {same}  bound holds: {ok}")
    print(f"violations: {viol}")
    return viol


if __name__ == "__main__":
    if main():                                       # exit status 1 on a violation (run_all.sh counts it)
        print("x3: a writing variant differs from the non-writing run or breaks the bound", file=sys.stderr)
        sys.exit(1)
