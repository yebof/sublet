"""X8: the reserve is attained. Toy instance (phi = 1), one client with constant demand 0.8, every stranding
coefficient positive; the inner buys one protected replica at slot 0 and keeps it. Forced abort at slot 6 under
'release' (and 'adaptive'): the release at t_a has lead time 0, so the stranding of t_a's first fast slot is
kappa' d = R(t_a - 1) exactly, and Phi(t_a) = R(t_a - 1).
Audit of the full-model guard (design/theory/audit_guard.md); code/sim/audit/, run by run_all.sh, output
code/sim/out/audit_fm/x8_out.txt."""
import sys

import numpy as np

import audit_env  # noqa: F401
from fixtures import toy_instance
from sublet.algos.guard import Guarded
from sublet.engine import simulate
from sublet.policies.base import Policy
from sublet.types import Buy, LenderModel, Stranding

TOL = 1e-9


class Hold(Policy):
    name = "hold"

    def act(self, obs):
        if int(obs.t) != 0:
            return []
        P = next(l for l, s in enumerate(self.view.sites) if s.kind == "protected")
        return [Buy(P, sorted(self.view.sites[P].menu)[0], 0, 1)]


def main():
    inst = toy_instance({})
    inst.clients.demand = np.full_like(np.asarray(inst.clients.demand, dtype=float), 0.8)
    inst.stranding = Stranding(mu_kv_usd=np.array([0.3]), mu_fl_usd=np.array([0.2]), mu_fb_usd=np.array([0.5]),
                               pi_usd_per_min=np.array([0.05]), W_f_min=4.0)
    q = inst.llms[0].q_usd_per_h
    Q = np.full(inst.grid.T_slow, q * 0.8 * inst.grid.fast_min / 60.0)
    bad = []
    for rule in ("release", "adaptive"):
        res = simulate(inst, Guarded(inner=Hold(), test="T0g", safe="fb", wind_down=rule, B0=1e12, kappa=None,
                                     abort_at=6), LenderModel(), policy_seed=0)
        rep = res.metrics["policy"]
        tot = np.asarray(res.per_slot["total"], dtype=float)
        phi = float(np.sum(tot[6:] - Q[6:]))
        R = rep["budget_t_a"]
        wd = [(e["choice"], round(e.get("beta", {}).get("K0", 0), 6)) for e in rep["wd"]]
        print(f"{rule}: t_a={rep['t_a']} R(t_a-1)={R:.6f} Phi(t_a)={phi:.6f} "
              f"stranding(t_a)={res.per_slot['stranding'][6]:.6f} "
              f"kappa' d = {(0.3 + 0.2 + 0.5 + 0.05 * 4.0) * 0.8:.6f} wd={wd}")
        tol = TOL * max(1.0, abs(R))
        if phi > R + tol:                                # the reserve bound Phi(t_a) <= R(t_a - 1) fails
            bad.append(f"{rule}: Phi(t_a) = {phi!r} > R(t_a - 1) = {R!r}")
        elif phi < R - tol:                              # sound, but X8's claim (the reserve is attained) fails
            bad.append(f"{rule}: Phi(t_a) = {phi!r} < R(t_a - 1) = {R!r}, the reserve is not attained")
    return bad


if __name__ == "__main__":
    bad = main()
    if bad:                                          # exit status 1 (run_all.sh counts it)
        print("x8: " + "; ".join(bad), file=sys.stderr)
        sys.exit(1)
