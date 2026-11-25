"""Lender-side slack from Alibaba spot-gpu v2026 (ASPLOS'26 GFS): lendable = capacity - HP occupancy.

HP jobs are the lender's first-party demand; Spot jobs are the in-house analogue of a borrower.
Outputs per GPU model: diurnal shape, idle-window lengths, residual time to reclaim, reclaim predictability.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import DATA, FIG, OUT, save_json, occupancy, window_stats, residual_to_reclaim, \
    reclaim_predictability, diurnal_profile

SLOT = 300  # seconds
D = f"{DATA}/alibaba-spot-gpu-v2026"
jobs = pd.read_csv(f"{D}/job_info_df.csv")
nodes = pd.read_csv(f"{D}/node_info_df.csv")
jobs["g"] = jobs.gpu_request * jobs.worker_num
T = int((jobs.submit_time.max()) // SLOT) + 1
WARMUP = 7 * 288  # drop first week: jobs running before t=0 are missing (left-censored)

cap = nodes.groupby("gpu_model").gpu_capacity_num.sum()
result, series = {}, {}
for model, C in cap.items():
    hp = jobs[(jobs.gpu_model == model) & (jobs.job_type == "HP")]
    sp = jobs[(jobs.gpu_model == model) & (jobs.job_type == "Spot")]
    occ_hp = occupancy(hp.submit_time.values, hp.duration.values, hp.g.values, SLOT, T)[WARMUP:]
    occ_sp = occupancy(sp.submit_time.values, sp.duration.values, sp.g.values, SLOT, T)[WARMUP:]
    s = np.maximum(C - occ_hp, 0)
    series[model] = s
    r = {"capacity_gpus": int(C), "hp_util_mean": float(occ_hp.mean() / C),
         "hp_over_capacity_frac": float((occ_hp > C).mean()),
         "spot_gpus_mean": float(occ_sp.mean()), "slack_mean_gpus": float(s.mean()),
         "slack_cv": float(s.std() / max(s.mean(), 1e-9)),
         "hp_diurnal": diurnal_profile(occ_hp, 288), "leases": {}}
    for qname, q in (("p10", 10), ("p25", 25), ("p50", 50)):
        L = np.percentile(s, q)
        if L <= 0:
            continue
        r["leases"][qname] = {"window": window_stats(s, L, 5),
                              "residual": residual_to_reclaim(s, L, 5),
                              "predictability": reclaim_predictability(s, L, 5, 288)}
    result[model] = r
    print(model, {k: r[k] for k in ("capacity_gpus", "hp_util_mean", "slack_mean_gpus", "hp_over_capacity_frac")})

# correlation of slack across GPU pools (proxy for correlated reclaim across a lender's machines)
names = list(series)
M = np.vstack([series[n] for n in names])
corr = np.corrcoef(np.diff(M, axis=1))
result["_slack_change_corr_across_models"] = {"models": names, "corr": corr.round(3).tolist()}
save_json("a1_lender_spotgpu.json", result)
np.savez_compressed(f"{OUT}/a1_slack_series.npz", **series)

fig, axes = plt.subplots(len(names), 1, figsize=(10, 2 * len(names)), sharex=True)
for ax, n in zip(axes, names):
    x = np.arange(len(series[n])) * 5 / 1440
    ax.plot(x, series[n], lw=0.4)
    ax.set_ylabel(n, fontsize=7)
axes[-1].set_xlabel("day")
fig.suptitle("Lendable slack = capacity - HP occupancy (Alibaba spot-gpu v2026)")
fig.tight_layout()
fig.savefig(f"{FIG}/a1_slack_timeseries.png", dpi=130)
