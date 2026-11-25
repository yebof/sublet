"""SM-utilisation coverage of the online allocation in the 20 MaaS clusters of a2.

a2 reports `online_sm_util_of_alloc` = sum(gpu_count x sm_util) / sum(gpu_count) with missing SM values set to 0,
so online GPU-slots without an SM record count as idle and the value is biased low. For the same 20 clusters and
the same online instances (workload "online" in instance_daily, days 140-146), this script reports
  sm_util_over_slots_with_data   SM utilisation over the online GPU-slots that have an SM value
  missing_share                  share of online GPU-slots (GPU-weighted) without an SM value
  sm_util_missing_as_idle        a2's definition, recomputed as a check against a2_lender_maas.json
Every instance has a single workload in days 140-146, so "online" here is the same label a2 uses.
Tables are streamed in pyarrow batches with the system allocator to stay under a 3 GB memory cap.
"""
import glob
import json

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from common import DATA, OUT, save_json

pa.set_memory_pool(pa.system_memory_pool())
D = f"{DATA}/alibaba-maas-v2026/data"
week = sorted(glob.glob(f"{D}/instance_week_5min/*.parquet"))
daily = sorted(glob.glob(f"{D}/instance_daily/*.parquet"))
a2 = json.load(open(f"{OUT}/a2_lender_maas.json"))
clusters = [k for k in a2 if k.startswith("cluster_")]
cl_arr = pa.array(clusters)

# online instances in days 140-146
chunks = []
for f in daily:
    for b in pq.ParquetFile(f).iter_batches(batch_size=250_000, columns=["instance_id", "workload", "day"]):
        d = b.column("day")
        m = pc.and_(pc.and_(pc.greater_equal(d, 140), pc.less_equal(d, 146)), pc.equal(b.column("workload"), "online"))
        ids = b.column("instance_id").filter(m)
        if len(ids):
            chunks.append(pc.unique(ids))
online = pc.unique(pa.chunked_array(chunks).combine_chunks())
del chunks
print("online instances", len(online))

acc = {c: np.zeros(3) for c in clusters}  # online GPU-slots, GPU-slots with an SM value, used GPU-slots
for f in week:
    for b in pq.ParquetFile(f).iter_batches(batch_size=1_000_000,
                                            columns=["instance_id", "cluster_id", "gpu_count", "sm_util"]):
        b = b.filter(pc.is_in(b.column("cluster_id"), value_set=cl_arr))
        if b.num_rows == 0:
            continue
        b = b.filter(pc.is_in(b.column("instance_id"), value_set=online))
        if b.num_rows == 0:
            continue
        g = pc.fill_null(b.column("gpu_count"), 0.0)
        sm = b.column("sm_util")
        has = pc.and_(pc.is_valid(sm), pc.invert(pc.is_nan(pc.fill_null(sm, 0.0))))
        t = pa.table({"c": b.column("cluster_id"), "g": g, "gs": pc.if_else(has, g, 0.0),
                      "u": pc.divide(pc.multiply(g, pc.if_else(has, sm, 0.0)), 100.0)})
        agg = t.group_by("c").aggregate([("g", "sum"), ("gs", "sum"), ("u", "sum")]).to_pydict()
        for c, x, y, z in zip(agg["c"], agg["g_sum"], agg["gs_sum"], agg["u_sum"]):
            acc[c] += (x, y, z)

res, diffs = {"clusters": {}}, []
for c in clusters:
    g, gs, u = acc[c]
    r = {"online_gpu_slots": float(g), "missing_share": float(1 - gs / g),
         "sm_util_over_slots_with_data": float(u / gs) if gs > 0 else None,
         "sm_util_missing_as_idle": float(u / g),
         "a2_online_sm_util_of_alloc": a2[c]["online_sm_util_of_alloc"]}
    diffs.append(abs(r["sm_util_missing_as_idle"] - r["a2_online_sm_util_of_alloc"]))
    res["clusters"][c] = r
cl = list(res["clusters"].values())
with_data = [r for r in cl if r["sm_util_over_slots_with_data"] is not None]
res["summary"] = {
    "n_clusters": len(cl), "n_clusters_with_sm_data": len(with_data),
    "median_sm_util_over_slots_with_data": float(np.median([r["sm_util_over_slots_with_data"] for r in with_data])),
    "median_sm_util_over_slots_with_data_excl_missing_ge_0.99": float(np.median(
        [r["sm_util_over_slots_with_data"] for r in with_data if r["missing_share"] < 0.99])),
    "median_sm_util_missing_as_idle_clusters_with_data": float(np.median(
        [r["sm_util_missing_as_idle"] for r in with_data])),
    "missing_share_sorted_desc": sorted((r["missing_share"] for r in cl), reverse=True),
    "max_abs_diff_missing_as_idle_vs_a2": float(max(diffs))}
print(json.dumps(res["summary"], indent=1))
save_json("a2c_sm_coverage.json", res)
