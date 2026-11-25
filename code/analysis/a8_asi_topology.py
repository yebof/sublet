"""Alibaba ASI GPU v2026 (OSDI'26): reclaim-correlation domains and first-party job lifetimes.

server_hourly: GPUs per access switch (ASW / rack domain) -> size of a correlated-reclaim group.
job_execution_summary: execution-span lengths by priority and job type (how long first-party work holds GPUs).
"""
import glob

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from common import DATA, save_json

D = f"{DATA}/alibaba-gpu-v2026/data"
res = {}
srv_files = sorted(glob.glob(f"{D}/asi_opensource_server_hourly/day=*/hour=12/*.parquet"))
if srv_files:
    days = sorted({f.split("day=")[1].split("/")[0] for f in srv_files}, key=int)
    pick = [f for f in srv_files if f.split("day=")[1].split("/")[0] in (days[0], days[len(days) // 2], days[-1])]
    snap = {}
    for f in pick:
        t = pq.read_table(f).to_pandas()
        day = f.split("day=")[1].split("/")[0]
        per_asw = t.dropna(subset=["asw_id"]).groupby("asw_id").gpu_count.sum()
        per_cl = t.groupby("cluster_id").gpu_count.sum()
        snap[day] = {"servers": int(len(t)), "gpus": float(t.gpu_count.sum()),
                     "asw_id_coverage": float(t.asw_id.notna().mean()),
                     "gpus_per_asw_p10_50_90_max": np.percentile(per_asw, [10, 50, 90, 100]).tolist() if len(per_asw) else None,
                     "asw_count": int(per_asw.size), "clusters": int(per_cl.size),
                     "gpu_spec_share": (t.groupby("gpu_spec_public").gpu_count.sum() / t.gpu_count.sum()).round(3).to_dict()}
    res["server_inventory_snapshots"] = snap

jf = sorted(glob.glob(f"{D}/asi_opensource_job_execution_summary/*.parquet"))
if jf:
    # Memory (run_all.sh runs a8 in a 3 GB scope): the 40.5M-row table is read one row group at a time, rows with
    # gpu_request > 0 and both keys present are kept, and per (priority_class, job_type_public) only the durations
    # and GPU-hours are collected, in row order. Groups are then processed in sorted key order, as a pandas groupby
    # over the whole table does, so the results are unchanged.
    pa.set_cpu_count(2)
    pa.set_io_thread_count(2)
    pf = pq.ParquetFile(jf[0])
    dur, gh = {}, {}
    for i in range(pf.num_row_groups):
        t = pf.read_row_group(i, columns=["priority_class", "job_type_public", "gpu_request", "duration_hours"])
        t = t.filter(pc.and_(pc.greater(t["gpu_request"], 0),
                             pc.and_(pc.is_valid(t["priority_class"]), pc.is_valid(t["job_type_public"]))))
        if not t.num_rows:
            continue
        d = t.to_pandas()
        del t
        for key, g in d.groupby(["priority_class", "job_type_public"], sort=False):
            dur.setdefault(key, []).append(g.duration_hours.to_numpy())
            gh.setdefault(key, []).append((g.gpu_request * g.duration_hours).to_numpy())
        del d
    out = {}
    for p, jt in sorted(dur):
        x = np.concatenate(dur[(p, jt)])
        if len(x) < 200:
            continue
        w = pd.Series(np.concatenate(gh[(p, jt)]))
        out[f"{p}|{jt}"] = {"n": int(len(x)), "gpu_hours": float(w.sum()),
                            "duration_h_p10_50_90": np.percentile(x, [10, 50, 90]).tolist()}
    res["execution_spans"] = out
save_json("a8_asi_topology.json", res)
print({k: (v if k != "execution_spans" else len(v)) for k, v in res.items()})
