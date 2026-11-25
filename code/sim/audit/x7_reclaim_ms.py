"""X7: X2's checks (m = 0 at executed slots, Phi <= budget in the wind-down) under trace lenders with buffer
violations 'reclaim' and with 'correlated' shocks, on ms2_multi_small (seed 3 and 4, 2-h horizon), around the
random and edge-pattern inners (every action type), forced aborts at every slot, wind-down 'adaptive' and 'release'.
Audit of the full-model guard (design/theory/audit_guard.md); code/sim/audit/, run by run_all.sh, output
code/sim/out/audit_fm/x7_out.txt."""
import sys
import time
from collections import Counter

import numpy as np

import audit_env  # noqa: F401
from audit_env import TG
from x2_random_search import TOL, Adv, run_case

MODELS = {"reclaim": {"schedule": "trace", "violations": "reclaim"},
          "reclaimI2": {"schedule": "trace", "violations": "reclaim", "information": "I2"},
          "corr": {"schedule": "correlated", "params": {"p_sh": 1.0, "groups": "all"}},
          "refuse_reclaim": {"schedule": "trace", "on_unavailable": "refuse", "violations": "reclaim"}}

st = Counter()
t0 = time.time()
wm = wp = -np.inf
for seed in (3, 4):
    inst = TG._ms(seed, 120)
    for k, (mname, lm) in enumerate(MODELS.items()):
        for j, Inner in enumerate((TG._RandomInner, Adv)):
            rule = ("adaptive", "release")[(k + j) % 2]
            m, p = run_case(inst, lm, lambda: Inner(100 * seed + 10 * k + j), rule, ("ms", seed, mname, Inner.name,
                                                                                       rule), bool(j), st)
            wm, wp = max(wm, m), max(wp, p)
            st["cases"] += 1
print(f"{dict(st)} max m/scale={wm:.3e} max (Phi - budget)/scale={wp:.3e} {time.time() - t0:.0f} s", flush=True)
if st["viol"] > 0 or wm > TOL or wp > TOL:            # exit status 1 on a violation (run_all.sh counts it)
    print("x7: m(t) or Phi - budget above the tolerance", file=sys.stderr)
    sys.exit(1)
