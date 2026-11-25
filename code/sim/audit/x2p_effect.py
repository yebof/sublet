"""Does G over W^C (finding F5, audit_env.route_over_wc) differ from G over W^B? Prints the number of slots with a
lower G, over X2's cases of seed 0, block P (reference runs only).
Audit of the full-model guard (design/theory/audit_guard.md); code/sim/audit/, run by run_all.sh, output
code/sim/out/audit_fm/x2p_effect_out.txt."""
import numpy as np

import audit_env  # noqa: F401
from audit_env import TG
from x2_random_search import EXTRA, MODELS, Adv, rich
from sublet.algos.guard import Guarded
from sublet.engine import EngineConfig, simulate
from sublet.types import LenderModel
lower = tot = 0
gain = 0.0
for v in range(len(TG._RICH) + len(EXTRA)):
    for i, (mname, lm) in enumerate(MODELS.items()):
        seed = 1000 * (ord("P") - 64) + 5 * v + i
        inst = rich(seed, v, bool((v + i) % 2))
        Inner = Adv if i % 2 else TG._RandomInner
        onu = "refuse" if lm.get("on_unavailable") == "refuse" else None
        out = []
        for wc in (False, True):
            audit_env.route_over_wc(wc)
            res = simulate(inst, Guarded(inner=Inner(seed), test="T0g", safe="fb", on_unavailable=onu, B0=1e12,
                                         kappa=None), LenderModel(**lm), EngineConfig(auto_drain=bool(i % 2)),
                           policy_seed=0)
            out.append(np.asarray(res.metrics["policy"]["t0g"]["G"]))
        tot += len(out[0])
        lower += int(np.sum(out[1] < out[0] - 1e-12))
        gain += float(np.sum(out[0] - out[1]))
print(f"slots {tot}, slots with lower G under W^C {lower}, total G reduction {gain:.4f} USD")
