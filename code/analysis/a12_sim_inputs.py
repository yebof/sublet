"""Simulator inputs that no other analysis output provides (design/sim_spec.md §3.9; design §5.2).

1. Input and output tokens and requests per minute (out/a12_minute_io.npz, float64 arrays
   `<name>__in`, `<name>__out`, `<name>__req`): Azure LLM 2024 code and conversation (ContextTokens,
   GeneratedTokens; minute 0 = minute of the first request) and BurstGPT 1-3 (Request tokens, Response
   tokens; rows with Response tokens > 0; minute 0 = first timestamp), with the minute index of
   a3_borrower_demand.py, plus the BurstGPT splits `burstgpt_<i>__<ChatGPT|GPT-4>__<conv|api>` by
   `Model` and `Log Type` ('Conversation log' -> conv, 'API log' -> api) on the minute index of the
   unsplit series. The simulator weights demand as output tokens plus w_in times input tokens
   (design §5.3.1), while a3_minute_series.npz holds only the unweighted total.
2. out/a12_sim_inputs.json: `series` (minutes, start time, totals), `checks.reproduce_a3` (per a3 series
   the largest absolute difference between in + out and a3_minute_series.npz, required 0; per BurstGPT
   part whether Total tokens equals Request + Response tokens on every row), `maas_clusters` (MaaS `site_id` of the 20 clusters
   behind a2_slack_series.npz), `corr_groups_dS` (an alternative correlation grouping, below) and `spot_pools`
   (keys of a1_slack_series.npz).

MaaS sites. The npz keys c00..c19 of a2_slack_series.npz follow the cluster keys of a2_lender_maas.json
(a2 writes both in its ranking order). The instance_daily table gives the site_id of every instance.
Fifteen of the 20 clusters have one site_id; five (c00, c01, c06, c13, c16) have instances at several
sites, some of which also host other clusters. sim_spec §3.9 asserts one site_id per cluster, which the
data contradict, so each entry records all its sites with their GPU-hours, and a cluster that spans
several sites is placed at the site that holds the largest share of its mean slack over the lender week
(days 140-146, the week of a2's slack series; sim_spec §10 S34): the lender lends the slack C - a_on,
which need not sit at the site with the most online load.
Per site, slack_s(t) = C_s - a_on,s(t) with C_s = max_t a_all,s(t) (a2's rule applied to the cluster's
instances at that site, each located by the instance_daily rows of its own cluster); the site sums of
a_on and a_all reproduce a2_slack_series.npz exactly (checked). Each entry gives `site_shares` (share of the mean slack per site, 0 for a site without
instances in the week), `site_share` (of the chosen site) and `n_site_ids`; `checks.maas_site_id` lists
the clusters where the rule chose. `corr_groups_dS` records an alternative correlation grouping: the
connected components of the graph on the 20 clusters with an edge where the correlation of 5-min slack
changes over the week exceeds 0.2. The simulator's correlation groups stay "clusters with the same
site_id" (an ASSUMPTION of sim_spec); the alternative is recorded only.

Raw traces are read in chunks (CSV) or one row group at a time (parquet) to fit a 6 GB cap
(run_all.sh). The npz is written with fixed zip timestamps, so a rerun gives identical bytes.
"""
import glob
import itertools
import json
import os
import zipfile

os.environ.setdefault("OMP_NUM_THREADS", "1")   # sim_spec §2.3, before numpy is imported

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from common import DATA, OUT, save_json  # noqa: E402

pa.set_cpu_count(2)
pa.set_io_thread_count(2)

SLOT_S = 60
MAAS_WEEK = (140, 146)   # days of a2_lender_maas.py's lender week
AZURE = {k: f"{DATA}/azure-llm-2024/AzureLLMInferenceTrace_{k}_1week.csv" for k in ("code", "conv")}
BURST = {i: f"{DATA}/burstgpt/BurstGPT_{i}.csv" for i in (1, 2, 3)}
BURST_MODELS = {"ChatGPT": "ChatGPT", "GPT-4": "GPT-4"}
BURST_LOGS = {"Conversation log": "conv", "API log": "api"}
MAAS_DAILY = f"{DATA}/alibaba-maas-v2026/data/instance_daily"
MAAS_5MIN = f"{DATA}/alibaba-maas-v2026/data/instance_week_5min"
CORR_DS_THRESHOLD = 0.2   # edge rule of corr_groups_dS (sim_spec §10 S34)


def save_npz(path, arrays):
    """np.savez_compressed with fixed member timestamps (byte-identical reruns); loads with np.load."""
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for key, val in arrays.items():
            zi = zipfile.ZipInfo(key + ".npy", date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with zf.open(zi, "w", force_zip64=True) as f:
                np.lib.format.write_array(f, np.ascontiguousarray(val), allow_pickle=False)
    os.replace(tmp, path)
    print("wrote", path)


def _codes(col, labels):
    """Index of each value in the keys of `labels` (-1 for any other value)."""
    v = col.to_numpy(object)
    out = np.full(len(v), -1, dtype=np.int8)
    for i, lab in enumerate(labels):
        out[v == lab] = i
    return out


def minute_sums(idx, n, w=None):
    return np.bincount(idx, weights=w, minlength=n).astype(np.float64)


def azure(kind):
    """Minute series of one Azure 2024 trace, minute index exactly as in a3."""
    f = AZURE[kind]
    assert os.path.exists(f + ".done"), f"{f} is incomplete"
    ts, ctx, gen = [], [], []
    for c in pd.read_csv(f, usecols=["TIMESTAMP", "ContextTokens", "GeneratedTokens"], chunksize=2_000_000):
        ts.append(pd.to_datetime(c.TIMESTAMP, format="mixed"))
        ctx.append(c.ContextTokens.to_numpy(np.int64))
        gen.append(c.GeneratedTokens.to_numpy(np.int64))
        del c
    ts = pd.concat(ts, ignore_index=True)
    ctx, gen = np.concatenate(ctx), np.concatenate(gen)
    t0 = ts.min()
    sorted_raw = bool(ts.is_monotonic_increasing)
    sec = (ts - t0).dt.total_seconds().to_numpy()   # a3: resolution-agnostic seconds from the first request
    del ts
    idx = (sec // SLOT_S).astype(np.int64)
    n = int(idx.max()) + 1
    out = {"in": minute_sums(idx, n, ctx), "out": minute_sums(idx, n, gen), "req": minute_sums(idx, n)}
    meta = {"n_minutes": n, "start_utc": t0.isoformat(), "rows": int(len(idx)),
            "raw_time_order_non_decreasing": sorted_raw}
    return out, meta


def burstgpt(i):
    """Minute series of one BurstGPT part (rows with Response tokens > 0, as in a3) and its four splits."""
    f = BURST[i]
    assert os.path.exists(f + ".done"), f"{f} is incomplete"
    cols = ["Timestamp", "Model", "Request tokens", "Response tokens", "Total tokens", "Log Type"]
    ts, rq, rs, mo, lg = [], [], [], [], []
    rows = rows_pos = bad_all = bad_pos = 0
    for c in pd.read_csv(f, usecols=cols, chunksize=1_000_000):
        tot_ok = c["Total tokens"].to_numpy() == c["Request tokens"].to_numpy() + c["Response tokens"].to_numpy()
        pos = c["Response tokens"].to_numpy() > 0
        rows += len(c); rows_pos += int(pos.sum())
        bad_all += int((~tot_ok).sum()); bad_pos += int((~tot_ok & pos).sum())
        c = c[pos]
        ts.append(c.Timestamp.to_numpy().astype(float))
        rq.append(c["Request tokens"].to_numpy(np.int64)); rs.append(c["Response tokens"].to_numpy(np.int64))
        mo.append(_codes(c.Model, BURST_MODELS)); lg.append(_codes(c["Log Type"], BURST_LOGS))
        del c
    ts, rq, rs = np.concatenate(ts), np.concatenate(rq), np.concatenate(rs)
    mo, lg = np.concatenate(mo), np.concatenate(lg)
    t0 = ts.min()
    idx = ((ts - t0) // SLOT_S).astype(np.int64)   # a3 series_stats
    n = int(idx.max()) + 1
    series = {f"burstgpt_{i}": {"in": minute_sums(idx, n, rq), "out": minute_sums(idx, n, rs),
                                "req": minute_sums(idx, n)}}
    covered = np.zeros(len(idx), dtype=bool)
    split_rows = {}
    for m_code, m_name in enumerate(BURST_MODELS.values()):
        for l_code, l_name in enumerate(BURST_LOGS.values()):
            sel = (mo == m_code) & (lg == l_code)
            covered |= sel
            name = f"burstgpt_{i}__{m_name}__{l_name}"
            split_rows[name] = int(sel.sum())
            series[name] = {"in": minute_sums(idx[sel], n, rq[sel]), "out": minute_sums(idx[sel], n, rs[sel]),
                            "req": minute_sums(idx[sel], n)}
    assert covered.all(), f"BurstGPT_{i}: {int((~covered).sum())} rows outside the Model x Log Type splits"
    meta = {"n_minutes": n, "start_utc": "relative", "rows_file": rows, "rows_response_gt_0": rows_pos,
            "raw_time_order_non_decreasing": bool(np.all(np.diff(ts) >= 0)), "split_rows": split_rows}
    check = {"rows": rows, "rows_total_ne_request_plus_response": bad_all,
             "rows_response_gt_0_total_ne_request_plus_response": bad_pos,
             "total_equals_request_plus_response_every_row": bad_all == 0,
             "total_equals_request_plus_response_rows_used": bad_pos == 0}
    return series, meta, check


def maas_site_slack(cids):
    """Mean slack per site of the MaaS clusters `cids` over the lender week (sim_spec §10 S34).

    Every instance of a cluster takes its site_id and workload from that cluster's instance_daily rows of
    days 140-146 (an instance listed at several sites takes the first site_id in sort order; the rows of
    other clusters are not used, since a few instance ids appear under several clusters). Per (cluster,
    site), a_on,s(t) and a_all,s(t) are the 5-min GPU allocations of instance_week_5min (NaN gpu_count as
    0, as in a2's sums), C_s = max_t a_all,s(t) and slack_s(t) = C_s - a_on,s(t). Returns {cluster_id:
    {site_id: mean slack_s}} and the largest |max(max_t a_all(t) - a_on(t), 0) - a2 slack| over the
    clusters, with a_all and a_on summed over the sites (0 iff the split covers a2's series exactly).
    Raises if some allocation of a cluster has no daily row of that cluster (site unknown)."""
    vs = pa.array(cids)
    pairs = []
    for f in sorted(glob.glob(f"{MAAS_DAILY}/*.parquet")):
        pf = pq.ParquetFile(f)
        for g in range(pf.num_row_groups):
            t = pf.read_row_group(g, columns=["day", "instance_id", "cluster_id", "site_id", "workload"])
            t = t.filter(pc.and_(pc.and_(pc.greater_equal(t["day"], MAAS_WEEK[0]),
                                         pc.less_equal(t["day"], MAAS_WEEK[1])),
                                 pc.is_in(t["cluster_id"], value_set=vs)))
            if t.num_rows:
                cols = ["instance_id", "cluster_id", "site_id", "workload"]
                pairs.append(t.select(cols).group_by(cols).aggregate([]))
    M = pa.concat_tables(pairs).group_by(["instance_id", "cluster_id", "site_id", "workload"]).aggregate([])
    M = M.to_pandas()
    del pairs
    site_names = sorted(set(M.site_id)) + ["unknown"]
    unknown = len(site_names) - 1
    scode = {x: i for i, x in enumerate(site_names)}
    maps = []   # per cluster: instance index, site code and workload class (0 online, 1 other); last = unknown
    for cid in cids:
        Mc = M[M.cluster_id == cid].sort_values(["instance_id", "site_id"]).drop_duplicates("instance_id")
        maps.append((pd.Index(Mc.instance_id.to_numpy()),
                     np.array([scode[x] for x in Mc.site_id] + [unknown], dtype=np.int64),
                     np.array([0 if x == "online" else 1 for x in Mc.workload] + [1], dtype=np.int64)))
    del M
    files = sorted(glob.glob(f"{MAAS_5MIN}/*.parquet"))
    tmin, tmax = [], []
    for f in files:   # a2's t0 is the minimum time over all rows: read it from the parquet statistics
        md = pq.ParquetFile(f).metadata
        ci = md.schema.names.index("time_s")
        for g in range(md.num_row_groups):
            st = md.row_group(g).column(ci).statistics
            tmin.append(st.min)
            tmax.append(st.max)
    t0 = min(tmin)
    T = (max(tmax) - t0) // 300 + 1
    acc = np.zeros((len(cids), len(site_names), T, 2))   # GPUs per (cluster, site, slot, online / other)
    for f in files:
        pf = pq.ParquetFile(f)
        for g in range(pf.num_row_groups):
            t = pf.read_row_group(g, columns=["instance_id", "time_s", "cluster_id", "gpu_count"])
            cc = pc.fill_null(pc.index_in(t["cluster_id"], value_set=vs), -1).to_numpy()
            keep = cc >= 0
            if not keep.any():
                continue
            t = t.filter(pa.array(keep))
            cc = cc[keep]
            iid = np.asarray(t["instance_id"].to_pylist(), dtype=object)
            sl = (t["time_s"].to_numpy() - t0) // 300
            gc = np.nan_to_num(t["gpu_count"].to_numpy(zero_copy_only=False).astype(float))
            del t
            for ci in np.unique(cc):
                sel = cc == ci
                idx, sc, wc = maps[ci]
                ix = idx.get_indexer(iid[sel])
                np.add.at(acc, (ci, sc[ix], sl[sel], wc[ix]), gc[sel])
    assert acc[:, unknown].sum() == 0, "some MaaS allocation has no instance_daily row of its cluster"
    key_of = {cid: f"c{i:02d}" for i, cid in enumerate(maas_cluster_ids())}
    with np.load(f"{OUT}/a2_slack_series.npz") as z:
        a2s = {k: z[k].astype(float) for k in z.files}
    out, rep = {}, 0.0
    for ci, cid in enumerate(cids):
        X = acc[ci]
        a_on = X[:, :, 0].sum(axis=0)
        rep = max(rep, float(np.max(np.abs(np.maximum(X.sum(axis=(0, 2)).max() - a_on, 0) - a2s[key_of[cid]]))))
        out[cid] = {sid: float((X[si].sum(axis=1).max() - X[si, :, 0]).mean())
                    for si, sid in enumerate(site_names) if X[si].sum() > 0}
    return out, rep


def maas_cluster_ids():
    """Cluster ids behind a2_slack_series.npz keys c00..c19 (a2's ranking order)."""
    a2 = json.load(open(f"{OUT}/a2_lender_maas.json"))
    cl = [k for k in a2 if k != "workload_rows" and not k.startswith("_")]
    with np.load(f"{OUT}/a2_slack_series.npz") as z:
        keys = list(z.files)
    assert keys == [f"c{i:02d}" for i in range(len(cl))] and len(cl) == 20, (keys, len(cl))
    return cl


def maas_clusters():
    """MaaS site of each of the 20 clusters behind a2_slack_series.npz (GPU-hours per site from instance_daily;
    a cluster at several sites goes to the site with the largest share of its mean slack, sim_spec §10 S34)."""
    cl = maas_cluster_ids()
    vs = pa.array(cl)
    parts = []
    for f in sorted(glob.glob(f"{MAAS_DAILY}/*.parquet")):
        pf = pq.ParquetFile(f)
        for g in range(pf.num_row_groups):
            t = pf.read_row_group(g, columns=["day", "cluster_id", "site_id", "workload", "gpu_hours"])
            t = t.filter(pc.is_in(t["cluster_id"], value_set=vs))
            if t.num_rows:
                wk = pc.and_(pc.greater_equal(t["day"], MAAS_WEEK[0]), pc.less_equal(t["day"], MAAS_WEEK[1]))
                t = t.append_column("week", wk).append_column("online", pc.equal(t["workload"], "online"))
                parts.append(t.group_by(["cluster_id", "site_id", "week", "online"]).aggregate([("gpu_hours", "sum")]))
    A = pa.concat_tables(parts).to_pandas()
    assert A.site_id.notna().all()
    A = A.groupby(["cluster_id", "site_id", "week", "online"]).gpu_hours_sum.sum().reset_index()
    site_lists = {}
    for cid in cl:
        s = A[A.cluster_id == cid]
        sites = []
        for sid in sorted(s.site_id.unique()):
            r = s[s.site_id == sid]
            gh = r.gpu_hours_sum.to_numpy()
            wk, on = r.week.to_numpy(bool), r.online.to_numpy(bool)
            sites.append({"site_id": sid,
                          "online_gpu_hours_week": float(gh[wk & on].sum()), "gpu_hours_week": float(gh[wk].sum()),
                          "online_gpu_hours_all": float(gh[on].sum()), "gpu_hours_all": float(gh.sum())})
        sites.sort(key=lambda x: (-x["online_gpu_hours_week"], -x["gpu_hours_all"], x["site_id"]))
        site_lists[cid] = sites
    multi = [cid for cid in cl if len(site_lists[cid]) > 1]
    slack_by_site, rep = maas_site_slack(multi)
    assert rep == 0, f"the per-site slack split does not reproduce a2_slack_series.npz (max abs diff {rep})"
    out, chosen = [], []
    for i, cid in enumerate(cl):
        sites = site_lists[cid]
        if len(sites) == 1:
            shares = {sites[0]["site_id"]: 1.0}
        else:
            ms = slack_by_site[cid]
            assert set(ms) <= {x["site_id"] for x in sites}, (cid, sorted(ms))   # own-cluster rows only
            tot = sum(ms.values())
            assert tot > 0, cid
            shares = {x["site_id"]: ms.get(x["site_id"], 0.0) / tot for x in sites}
        best = max(sites, key=lambda x: (shares[x["site_id"]], -sites.index(x)))   # ties: the order of `sites`
        tot_on = sum(x["online_gpu_hours_week"] for x in sites)
        e = {"npz_key": f"c{i:02d}", "cluster_id": cid, "site_id": best["site_id"], "n_site_ids": len(sites),
             "site_shares": shares, "site_share": shares[best["site_id"]],
             "site_share_online_gpu_hours_week": best["online_gpu_hours_week"] / tot_on if tot_on > 0 else None,
             "sites": sites}
        if len(sites) > 1:
            chosen.append(e["npz_key"])
        out.append(e)
    check = {"n_clusters": len(out), "n_with_one_site_id": sum(e["n_site_ids"] == 1 for e in out),
             "clusters_with_several_site_ids": chosen,
             "rule": "site_id = the cluster's only site_id; a cluster with several site_ids goes to the site with "
                     "the largest share of its mean slack over days "
                     f"{MAAS_WEEK[0]}-{MAAS_WEEK[1]} (per site C_s - a_on,s(t), C_s = max_t a_all,s(t), from "
                     "instance_week_5min with each instance's site_id in the instance_daily rows of its cluster; "
                     "sim_spec §10 S34); the site sums reproduce a2_slack_series.npz exactly (asserted). "
                     "site_shares holds every share. "
                     "sim_spec §3.9 asserts one site_id per cluster, which holds only for n_with_one_site_id "
                     "clusters"}
    return out, check


def corr_groups_dS(threshold=CORR_DS_THRESHOLD):
    """Alternative correlation grouping of the 20 MaaS clusters (recorded only, sim_spec §10 S34): connected
    components of the graph with an edge where corr(dS_a, dS_b) > threshold, dS the 5-min changes of the
    a2 slack series (the lender week)."""
    with np.load(f"{OUT}/a2_slack_series.npz") as z:
        keys = list(z.files)
        dS = {k: np.diff(z[k].astype(float)) for k in keys}
    parent = {k: k for k in keys}

    def root(k):
        while parent[k] != k:
            k = parent[k]
        return k

    edges = []
    for a, b in itertools.combinations(keys, 2):
        with np.errstate(invalid="ignore", divide="ignore"):
            c = float(np.corrcoef(dS[a], dS[b])[0, 1])   # NaN for a constant series: no edge
        if c > threshold:
            edges.append({"a": a, "b": b, "corr": c})
            ra, rb = root(a), root(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    comp = {}
    for k in keys:
        comp.setdefault(root(k), []).append(k)
    groups = sorted((sorted(v) for v in comp.values()), key=lambda v: v[0])
    return {"threshold": threshold,
            "rule": "connected components of the graph on the 20 clusters (npz keys) with an edge where the "
                    "Pearson correlation of the 5-min changes of a2_slack_series.npz exceeds the threshold; "
                    "an alternative to the site_id grouping, recorded only (the simulator groups clusters by "
                    "site_id, sim_spec §10 S34)",
            "groups": groups, "edges": sorted(edges, key=lambda e: -e["corr"])}


def main():
    arrays, meta, checks_b = {}, {}, {}
    for kind in ("code", "conv"):
        s, m = azure(kind)
        name = f"azure2024_{kind}"
        meta[name] = m
        for k in ("in", "out", "req"):
            arrays[f"{name}__{k}"] = s[k]
        print(name, m["n_minutes"], "minutes", m["rows"], "requests")
    for i in BURST:
        ser, m, chk = burstgpt(i)
        checks_b[f"burstgpt_{i}"] = chk
        for name, s in ser.items():
            meta[name] = m if name == f"burstgpt_{i}" else {"n_minutes": m["n_minutes"], "start_utc": "relative",
                                                              "rows": m["split_rows"][name], "split_of": f"burstgpt_{i}"}
            for k in ("in", "out", "req"):
                arrays[f"{name}__{k}"] = s[k]
        print(f"burstgpt_{i}", m["n_minutes"], "minutes", m["rows_response_gt_0"], "requests")
    for name, m in meta.items():
        m["totals"] = {"in_tokens": int(arrays[f"{name}__in"].sum()), "out_tokens": int(arrays[f"{name}__out"].sum()),
                       "requests": int(arrays[f"{name}__req"].sum())}

    # reproduce_a3: per a3 series the largest |in + out - a3| (required 0), and per BurstGPT part whether
    # Total tokens equals Request + Response tokens on every row of the file (sim_spec §3.9)
    rep = {}
    with np.load(f"{OUT}/a3_minute_series.npz") as z:
        for k in z.files:
            a3 = z[k]
            io = arrays[f"{k}__in"] + arrays[f"{k}__out"]
            assert len(io) == len(a3), f"{k}: {len(io)} minutes, a3 has {len(a3)}"
            rep[k] = {"max_abs_diff": float(np.max(np.abs(io - a3)))}
    rep["burstgpt_total_equals_request_plus_response"] = {
        k: v["total_equals_request_plus_response_every_row"] for k, v in checks_b.items()}
    split_sum = {}
    for i in BURST:
        base = f"burstgpt_{i}"
        split_sum[base] = {k: float(np.max(np.abs(sum(arrays[f"{base}__{m}__{l}__{k}"] for m in BURST_MODELS.values()
                                                        for l in BURST_LOGS.values()) - arrays[f"{base}__{k}"])))
                           for k in ("in", "out", "req")}

    clusters, chk_site = maas_clusters()
    corr_groups = corr_groups_dS()
    with np.load(f"{OUT}/a1_slack_series.npz") as z:
        spot = list(z.files)

    res = {"meta": {"description": __doc__.split("\n\n")[0], "minute_s": SLOT_S,
                    "npz": "a12_minute_io.npz: float64 <name>__in, <name>__out, <name>__req per minute",
                    "maas_week_days": list(MAAS_WEEK)},
           "series": meta,
           "checks": {"reproduce_a3": rep, "burstgpt_total_tokens": checks_b,
                      "burstgpt_splits_sum_to_unsplit_max_abs_diff": split_sum, "maas_site_id": chk_site},
           "maas_clusters": clusters,
           "corr_groups_dS": corr_groups,
           "spot_pools": spot}
    save_npz(f"{OUT}/a12_minute_io.npz", arrays)
    save_json("a12_sim_inputs.json", res)
    a3_keys = [k for k in rep if k != "burstgpt_total_equals_request_plus_response"]
    for k in a3_keys:
        print(f"reproduce_a3 {k}: max abs diff {rep[k]['max_abs_diff']}")
    print("BurstGPT Total tokens = Request + Response on every row:", rep["burstgpt_total_equals_request_plus_response"])
    print("site_id: one per cluster for", chk_site["n_with_one_site_id"], "of", chk_site["n_clusters"],
          "clusters; rule applied to", chk_site["clusters_with_several_site_ids"])
    for e in clusters:
        if e["n_site_ids"] > 1:
            print(f"  {e['npz_key']}: site {e['site_id']} holds {e['site_share']:.4f} of the mean slack")
    print(f"corr_groups_dS (corr > {corr_groups['threshold']}):", [g for g in corr_groups["groups"] if len(g) > 1],
          "and", sum(len(g) == 1 for g in corr_groups["groups"]), "singletons")
    assert all(rep[k]["max_abs_diff"] == 0 for k in a3_keys), "a12 does not reproduce a3_minute_series.npz"
    assert all(v == 0 for d in split_sum.values() for v in d.values()), "BurstGPT splits do not sum to the series"


if __name__ == "__main__":
    main()
