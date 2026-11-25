"""How much revocation the a7 policy simulation exercises, per lender layer.

a7 cuts each lender's slack series s_t into K = 8 LIFO layers of width v = P50(s)/K; layer k is available
while s_t >= k * v. This script reports, for the five lenders a7 uses, the share of 5-minute slots in which
each layer is unavailable and the number of reclaims (available -> unavailable transitions) per day, over
the full slack series. Inputs: out/a1_slack_series.npz, out/a2_slack_series.npz (no raw data needed).
"""
import numpy as np

from common import OUT, save_json

K = 8
SLOTS_PER_DAY = 1440 // 5

lenders = {}
for f in ("a1_slack_series.npz", "a2_slack_series.npz"):
    z = np.load(f"{OUT}/{f}")
    lenders.update({f[:2] + ":" + k: z[k].astype(float) for k in z.files})
# same selection as a7_policy_sim.py
pick = [k for k in lenders if k.startswith("a1:") and ("H800" in k or "A100" in k)]
pick += [k for k in lenders if k.startswith("a2:")][:3]

res = {}
for name in pick:
    s = lenders[name]
    v = np.percentile(s, 50) / K
    days = len(s) / SLOTS_PER_DAY
    layers = {}
    for k in range(1, K + 1):
        avail = s >= k * v
        reclaims = int(np.sum(avail[:-1] & ~avail[1:]))
        layers[str(k)] = {"unavailable_share": float(1 - avail.mean()), "reclaims_per_day": reclaims / days}
    res[name] = {"days": days, "min_over_median": float(s.min() / np.median(s)),
                 "layers_never_unavailable": [k for k in range(1, K + 1) if layers[str(k)]["unavailable_share"] == 0],
                 "layers": layers}
    print(name, f"days={days:.1f} min/median={res[name]['min_over_median']:.3f}",
          "never unavailable:", res[name]["layers_never_unavailable"],
          "top layer unavailable share=%.3f reclaims/day=%.2f" % (layers[str(K)]["unavailable_share"],
                                                                   layers[str(K)]["reclaims_per_day"]))
save_json("a7b_layer_exposure.json", res)
