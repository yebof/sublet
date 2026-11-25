"""Lender-side slack in a production LLM-inference fleet: Alibaba cluster-trace-v2026-maas (ATC'26).

Per cluster, 5-minute series over one week (days 140-146):
  alloc_online_t  GPUs allocated to online instances (first-party demand the lender must protect)
  alloc_all_t     online + offline (offline batch is deferrable, so it does not block lending)
  used_online_t   alloc x SM utilisation (how much of the allocation does work)
Lendable slack s_t = C - alloc_online_t, with C = weekly max of alloc_all_t (capacity proxy; the trace does
not publish per-cluster capacity). Reported: diurnal shape, idle windows, residual-to-reclaim, predictability,
and cross-cluster correlation of slack changes.
"""
import glob

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from common import DATA, OUT, save_json, window_stats, residual_to_reclaim, reclaim_predictability, diurnal_profile

D = f"{DATA}/alibaba-maas-v2026/data"
week = sorted(glob.glob(f"{D}/instance_week_5min/*.parquet"))
daily = sorted(glob.glob(f"{D}/instance_daily/*.parquet"))

# Memory (run_all.sh runs a2 in a 6 GB scope): the workload of each instance in days 140-146 is read one row group
# at a time and kept as an Arrow table of distinct (instance_id, workload) pairs (one workload per instance in this
# week: 4,681,106 pairs and as many instances), and the 5-min rows are labeled with an Arrow lookup instead of a
# pandas map, after which instance_id is dropped. Arrow's thread pools are capped. Results are unchanged.
pa.set_cpu_count(2)
pa.set_io_thread_count(2)
meta = None
if daily:
    pairs = []
    for f in daily:
        pf = pq.ParquetFile(f)
        for i in range(pf.num_row_groups):
            t = pf.read_row_group(i, columns=["day", "instance_id", "workload"])
            t = t.filter(pc.and_(pc.greater_equal(t["day"], 140), pc.less_equal(t["day"], 146)))
            if t.num_rows:
                pairs.append(t.select(["instance_id", "workload"]).group_by(["instance_id", "workload"]).aggregate([]))
    meta = pa.concat_tables(pairs).group_by(["instance_id", "workload"]).aggregate([])
    del pairs
    assert len(pc.unique(meta["instance_id"])) == meta.num_rows   # one workload per instance

parts = []
for f in week:
    t = pq.read_table(f, columns=["instance_id", "time_s", "cluster_id", "gpu_count", "sm_util"])
    if meta is not None:
        wl = pc.take(meta["workload"], pc.index_in(t["instance_id"], value_set=meta["instance_id"]))
        t = t.append_column("workload", pc.fill_null(wl, "unknown"))
    w = t.drop_columns(["instance_id"]).to_pandas()   # instance_id is needed only for the lookup
    del t
    if meta is None:
        w["workload"] = "unknown"
    w["used"] = w.gpu_count * w.sm_util.fillna(0) / 100.0
    parts.append(w.groupby(["cluster_id", "time_s", "workload"])[["gpu_count", "used"]].sum().reset_index())
df = pd.concat(parts).groupby(["cluster_id", "time_s", "workload"])[["gpu_count", "used"]].sum().reset_index()
df = df.rename(columns={"gpu_count": "alloc"})
print(df.workload.value_counts())

t0 = df.time_s.min()
df["slot"] = ((df.time_s - t0) // 300).astype(int)
T = df.slot.max() + 1
res, slack = {"workload_rows": df.workload.value_counts().to_dict()}, {}
# rank clusters by online (first-party, latency-critical) allocation: clusters with no online
# instances have no reclaim driver and would give a constant slack series
key = df[df.workload == "online"] if (df.workload == "online").any() else df
sizes = key.groupby("cluster_id").alloc.mean().sort_values(ascending=False)
for cid in sizes.index[:20]:
    g = df[df.cluster_id == cid]
    a_all = np.zeros(T); a_on = np.zeros(T); u_on = np.zeros(T)
    s_all = g.groupby("slot").alloc.sum()
    a_all[s_all.index] = s_all.values
    on = g[g.workload == "online"] if daily else g
    s_on = on.groupby("slot")[["alloc", "used"]].sum()
    a_on[s_on.index] = s_on.alloc.values
    u_on[s_on.index] = s_on.used.values
    C = a_all.max()
    s = np.maximum(C - a_on, 0)
    slack[cid] = s
    r = {"C_proxy_gpus": float(C), "online_alloc_mean_frac": float(a_on.mean() / C),
         "online_sm_util_of_alloc": float(u_on.sum() / max(a_on.sum(), 1e-9)),
         "online_alloc_diurnal": diurnal_profile(a_on, 288),
         "online_used_diurnal": diurnal_profile(u_on, 288),
         "slack_cv": float(s.std() / max(s.mean(), 1e-9)), "leases": {}}
    for qn, q in (("p10", 10), ("p25", 25), ("p50", 50)):
        L = np.percentile(s, q)
        if L > 0:
            r["leases"][qn] = {"window": window_stats(s, L, 5), "residual": residual_to_reclaim(s, L, 5),
                               "predictability": reclaim_predictability(s, L, 5, 288)}
    res[str(cid)] = r
    print(cid, round(C), round(r["online_alloc_mean_frac"], 2), r["online_alloc_diurnal"]["peak_to_trough"])

ids = list(slack)
M = np.vstack([slack[c] for c in ids])
cc = np.corrcoef(np.diff(M, axis=1))
res["_cross_cluster_slack_change_corr"] = {
    "median_offdiag": float(np.median(cc[~np.eye(len(ids), dtype=bool)])),
    "p90_offdiag": float(np.percentile(cc[~np.eye(len(ids), dtype=bool)], 90))}
lv = np.corrcoef(M)
res["_cross_cluster_slack_level_corr_median"] = float(np.median(lv[~np.eye(len(ids), dtype=bool)]))
save_json("a2_lender_maas.json", res)
np.savez_compressed(f"{OUT}/a2_slack_series.npz", **{f"c{i:02d}": slack[c] for i, c in enumerate(ids)})
