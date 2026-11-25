"""Six-month view of lender first-party load: Alibaba maas instance_daily (days 0-181).

Per cluster: daily online / offline GPU-hours. Reports day-to-day variability, weekly pattern and
day-ahead predictability (how far ahead a lender could commit spare capacity in a contract).
"""
import glob

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from common import DATA, save_json

files = sorted(glob.glob(f"{DATA}/alibaba-maas-v2026/data/instance_daily/*.parquet"))
parts = []
for f in files:
    t = pq.read_table(f, columns=["day", "cluster_id", "workload", "gpu_hours"]).to_pandas()
    parts.append(t.groupby(["cluster_id", "day", "workload"]).gpu_hours.sum().reset_index())
df = pd.concat(parts).groupby(["cluster_id", "day", "workload"]).gpu_hours.sum().unstack("workload", fill_value=0)
df = df.reset_index()
print(df.head())

tot_by_wl = df.drop(columns=["cluster_id", "day"]).sum()
res = {"gpu_hours_share_by_workload": (tot_by_wl / tot_by_wl.sum()).to_dict(), "clusters": {}}
big = df.groupby("cluster_id").sum(numeric_only=True).drop(columns="day").sum(1).sort_values(ascending=False).index[:20]
mape_n, mape_w, cv = [], [], []
for c in big:
    g = df[df.cluster_id == c].set_index("day").reindex(range(182)).fillna(0)
    on = g.get("online", pd.Series(0, index=g.index)).values.astype(float)
    if on.mean() <= 0:
        continue
    x = on[14:]  # skip warm-up
    naive = np.abs(x[1:] - x[:-1]) / np.maximum(x[1:], 1e-9)
    weekly = np.abs(x[7:] - x[:-7]) / np.maximum(x[7:], 1e-9)
    dow = np.array([x[i::7].mean() for i in range(7)])
    r = {"online_daily_cv": float(x.std() / x.mean()),
         "day_ahead_naive_mape": float(np.median(naive)), "week_ahead_seasonal_mape": float(np.median(weekly)),
         "weekly_profile_peak_to_trough": float(dow.max() / max(dow.min(), 1e-9)),
         "trend_last30_over_first30": float(x[-30:].mean() / max(x[:30].mean(), 1e-9)),
         "offline_share": float(g.get("offline", pd.Series(0, index=g.index)).sum() / max(g.sum(numeric_only=True).sum(), 1e-9))}
    res["clusters"][str(c)] = r
    mape_n.append(r["day_ahead_naive_mape"]); mape_w.append(r["week_ahead_seasonal_mape"]); cv.append(r["online_daily_cv"])
res["summary"] = {"median_day_ahead_naive_mape": float(np.median(mape_n)),
                  "median_week_ahead_mape": float(np.median(mape_w)), "median_online_daily_cv": float(np.median(cv)),
                  "median_trend_ratio": float(np.median([v["trend_last30_over_first30"] for v in res["clusters"].values()]))}
print(res["summary"], res["gpu_hours_share_by_workload"])
save_json("a2b_lender_maas_daily.json", res)
