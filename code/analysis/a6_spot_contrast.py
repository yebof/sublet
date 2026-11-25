"""Contrast: cloud spot preemption (no notice beyond ~30-120 s) from skypilot spot-traces (NSDI'24).

Preemption traces: 1 = instance held, 0 = not held. Holding period = run of 1s ending in a 1->0 drop.
Availability traces: 1 = capacity obtainable. Availability window = run of 1s.
"""
import glob
import json
import os

import numpy as np

from common import DATA, save_json, runs

res = {}
for kind in ("preemption", "availability"):
    hold = []
    per_file = {}
    for f in sorted(glob.glob(f"{DATA}/spot-traces/{kind}/1-node/*/*.json")):
        d = json.load(open(f))
        gap = d["metadata"]["gap_seconds"]
        x = np.array(d["data"]) > 0
        lens, _ = runs(x)
        mins = lens * gap / 60
        hold.extend(mins.tolist())
        per_file[os.path.relpath(f, f"{DATA}/spot-traces")] = {
            "events": int(len(lens)), "days": len(x) * gap / 86400,
            "median_min": float(np.median(mins)) if len(mins) else None}
    hold = np.array(hold)
    res[kind] = {"n_windows": int(len(hold)),
                 "window_min_quantiles_p10_25_50_75_90": np.percentile(hold, [10, 25, 50, 75, 90]).tolist() if len(hold) else None,
                 "per_file": per_file}
    print(kind, res[kind]["n_windows"], res[kind]["window_min_quantiles_p10_25_50_75_90"])
save_json("a6_spot_contrast.json", res)
