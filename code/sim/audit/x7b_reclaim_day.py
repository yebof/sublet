"""X7b: X2's checks under violations 'reclaim' on whole days of ms2_multi_small (seeds 3, 4) and q44_spot_1day
(seed 1), with an inner that fills every revocable site to capacity and keeps its leases ('hog', so that buffer
violations hit the platform) and the edge-pattern inner; forced aborts at every 6th slot (offset by the case).
Audit of the full-model guard (design/theory/audit_guard.md); code/sim/audit/, run by run_all.sh, output
code/sim/out/audit_fm/x7b_out.txt."""
import sys
import time
from collections import Counter

import numpy as np

import audit_env  # noqa: F401
from audit_env import TG
from x2_random_search import Adv, check, NO_ABORT, TOL
from sublet.algos.guard import Guarded
from sublet.engine import EngineConfig, simulate
from sublet.types import Buy, LenderModel


class Hog(TG._RandomInner):
    """Buys, at every slot, one replica of a random LLM at every revocable site with room, cheapest contract first;
    never releases; plus _RandomInner's actions at a third of the slots."""
    name = "hog"

    def act(self, obs):
        view = self.view
        acts = list(super().act(obs)) if self.r.random() < 0.33 else []
        held = {}
        for L in obs.leases.values():
            held[L.site] = held.get(L.site, 0) + L.gpus
        rel = {int(a.lease_id) for a in acts if hasattr(a, "lease_id") and type(a).__name__ == "Release"}
        for lid in rel:
            L = obs.leases[lid]
            held[L.site] -= L.gpus
        for a in acts:
            if isinstance(a, Buy):
                held[a.site] = held.get(a.site, 0) + view.llms[a.llm].g * a.n_replicas
        for l, s in enumerate(view.sites):
            if s.kind == "protected":
                continue
            j = int(self.r.integers(0, len(view.llms)))
            if held.get(l, 0) + view.llms[j].g <= s.capacity_gpus:
                k = min(s.menu, key=lambda k: float(view.price[l, k]))
                acts.append(Buy(l, int(k), j, 1))
                held[l] = held.get(l, 0) + view.llms[j].g
        return acts


st = Counter()
t0 = time.time()
wm = wp = -np.inf
cases = [("ms2_multi_small", 3), ("ms2_multi_small", 4), ("q44_spot_1day", 1)]
for ci, (name, seed) in enumerate(cases):
    inst = TG._full(name, seed)
    T = inst.grid.T_slow
    for k, lm in enumerate(({"schedule": "trace", "violations": "reclaim"},
                            {"schedule": "trace", "violations": "reclaim", "on_unavailable": "refuse"})):
        for j, Inner in enumerate((Hog, Adv)):
            rule = ("adaptive", "release")[(k + j) % 2]
            cautious = lm.get("on_unavailable") == "refuse"
            kw = dict(test="T0g", safe="fb", wind_down=rule, on_unavailable="refuse" if cautious else None, **NO_ABORT)
            model = LenderModel(**lm)
            mk = lambda: Inner(1000 * ci + 10 * k + j)
            ref = simulate(inst, Guarded(inner=mk(), **kw), model, EngineConfig(), policy_seed=0)
            m0, _, _ = check(inst, ref, (name, seed, k, j, "ref"))
            rr = ref.metrics["policy"]
            st["victims"] += sum(len(v.get("victims", [])) for v in ref.violations)
            st["uncertain"] += int(sum(rr["t0g"]["uncertain"]))
            wm = max(wm, m0)
            for t_a in range(3 * ci + 2 * k + j, T, 6):
                res = simulate(inst, Guarded(inner=mk(), abort_at=t_a, **kw), model, EngineConfig(), policy_seed=0)
                R = rr["guard"]["reserve"][t_a - 1] if t_a > 0 else 0.0
                m, p, info = check(inst, res, (name, seed, t_a), budget_ref=R)
                st["victims_abort_runs"] += sum(len(v.get("victims", [])) for v in res.violations)
                wm, wp = max(wm, m), max(wp, p)
                st["aborts"] += 1
                st["kept"] += sum(1 for c in info["choices"] if c != "K0")
                if m > TOL or p > TOL:
                    st["viol"] += 1
                    print("VIOLATION", name, seed, k, j, t_a, m, p, info, flush=True)
            st["cases"] += 1
            print(name, seed, k, Inner.name, dict(st), f"{time.time() - t0:.0f} s", flush=True)
print(f"{dict(st)} max m/scale={wm:.3e} max (Phi - budget)/scale={wp:.3e} {time.time() - t0:.0f} s", flush=True)
if st["viol"] > 0 or wm > TOL or wp > TOL:            # exit status 1 on a violation (run_all.sh counts it)
    print("x7b: m(t) or Phi - budget above the tolerance", file=sys.stderr)
    sys.exit(1)
