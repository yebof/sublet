"""Empirical LLM catalog of a production MaaS fleet: Alibaba cluster-trace-v2026-maas, instance_daily (ATC'26).

Design §5.3.1 (milestone MS0): replace the assumed S/M/L tiers of Table 5.4 (8B/1 GPU, 70B/8, 405B/16) with
tiers measured on the lender trace. Over online instances:
  - distributions of params_b (total parameters, B) and gpu_count (allocated GPU equivalents per instance);
  - tier boundaries in params_b, g_j per tier, each tier's share;
  - served variants per base_id (how many variants share base weights) and GPU-hour concentration;
  - GPU types (anonymized) with the GPU memory per GPU equivalent implied by gpu_mem_alloc / gpu_count.

Two weightings. Allocated GPU-hours (gpu_hours) weight an instance by gpu_count x time, so they are size-biased
for per-replica quantities. Instance-hours (gpu_hours / gpu_count = samples x 20 s, replica time) weight every
instance by its time alone. Both catalog medians are instance-hour weighted, over two populations. g_j is GPUs per
replica (design §1.5.3), so it is the median gpu_count of fused (PD-collocated) online instances, the only instances
that are whole replicas. The representative params_b is the median over all online instances of the tier, fused,
prefill and decode alike, since each instance holds the full weights. The fused-only params_b median and the
PD-disaggregated share of the median's mass point are reported next to it (tiers.<window>.<tier>), because for L
the two populations differ: L's all-instance median runs almost only PD-disaggregated. The GPU-hour versions are
reported too. Tier shares are given in both units; neither is a request or token share. tier_catalog_by_28day_block
gives the same medians per 28-day block, to show how stable they are over the six months.

Price unit. The calibration prices GPUs as H100-80GB (a5b, a11), so a catalog entry is feasible only if its
weights fit on g x 80 GB with room for KV cache. The rule is a5's: usable HBM = 0.9 x replica HBM
(a5_reclaim_cost_calibration.py, kv_cap). The proposed catalog uses 16-bit weights where they fit and 8-bit
weights otherwise, and lists the memory-derived g for 16-bit weights.

Field semantics follow the trace's docs/schema.md (literature/sources/dataset-alibaba-maas-v2026-schema.md); the
script checks the ones it relies on (section "checks" of the output). Variants per base use the trace authors'
rule from their reproduction SQL (scripts/sql/table2.sql, scripts/plot_fig12.py: base_id IS NOT NULL, so the
'-' placeholder base is kept): 1 if a base-only (b_) or both (x_) model_id is present, plus the number of
distinct s_/x_ model_ids. Distributions over bases exclude the '-' placeholder and say so.

One pass over the 61 shards with column projection and row-group iteration (4 worker processes). The raw rows
never leave a worker; only grouped GPU-hour sums do. Shards are merged in file order, so reruns are
byte-identical. Output: out/a10_maas_catalog.json and out/a10.log. Development option: A10_AGG_CACHE=<path> stores
the aggregation pass in a pickle and reuses it on the next run; the pickle carries a key (input files with sizes and
mtimes, columns, windows, and the source of the aggregation functions), and a cache whose key differs is refused.
"""
import glob
import hashlib
import inspect
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from common import DATA, OUT, save_json

FILES = sorted(glob.glob(f"{DATA}/alibaba-maas-v2026/data/instance_daily/*.parquet"))
COLS = ["day", "instance_id", "app_id", "model_id", "base_id", "cluster_id", "site_id", "gpu_type", "workload",
        "model_arch", "params_b", "pd_role", "gpu_count", "gpu_hours", "samples", "gpu_mem_alloc"]
WEEK = (140, 146)      # the week of instance_week_5min, used by a2 for lender slack
LAST28 = (154, 181)    # last four weeks of the daily table (day 172 is missing in the trace)
NPROC = 4
LOG = os.path.join(OUT, "a10.log")
# Table 5.4 defaults (a5 assumptions): params_b per tier; weights and replica memory are read from a5's JSON
DEFAULT_TIERS = {"S": ("llama3-8b", 8), "M": ("llama3-70b", 70), "L": ("llama3.1-405b", 405)}
TIER_EDGES = (10.0, 100.0)   # params_b: S < 10 <= M < 100 <= L (rounded weighted natural breaks, output "natural_breaks")
TIERS = ("S", "M", "L")
WINDOWS = {"all": (0, 181), "week": WEEK, "last28": LAST28}
PERIODS = {"all": ("o", "w", "l"), "week": ("w",), "last28": ("l",)}
# GPU memory classes by GiB per GPU equivalent (modal gpu_mem_alloc / gpu_count of each gpu_type)
MEM_CLASSES = ((0, 50, "<=48GiB"), (50, 88, "~80GiB"), (88, 120, "~96GiB"), (120, 170, "~141GiB"),
               (170, 1e9, ">=179GiB"))
GIB_GB = 2 ** 30 / 1e9  # gpu_mem_alloc is in GiB; weights are counted in GB (1e9 bytes)
PRICE_GPU_GB = 80       # price unit: H100-80GB (a5b, a11; literature/sources/gpu-rental-prices-h100-2026-10.md)
HBM_USABLE = 0.9        # a5_reclaim_cost_calibration.py: kv_cap = 0.9 x replica HBM - weights
README = {"rows": 145083117, "clusters": 56, "gpu_types": 30, "apps": 300000, "variants": 70000}  # trace README


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOG, "a") as f:
        f.write(s + "\n")


# ----------------------------------------------------------------------------------------------- aggregation pass
def period(day):
    p = np.full(len(day), "o", dtype=object)
    p[(day >= WEEK[0]) & (day <= WEEK[1])] = "w"
    p[(day >= LAST28[0]) & (day <= LAST28[1])] = "l"
    return p


def gsum(df, keys, val="gpu_hours"):
    return df.groupby(keys, dropna=False, observed=True)[val].sum().reset_index()


def agg_file(path):
    pa.set_cpu_count(2)
    pa.set_io_thread_count(2)
    f = pq.ParquetFile(path)
    out = {k: [] for k in ("day_wl", "online", "online_mem", "mem_per_gpu", "variants", "week_rows")}
    chk = {"rows": 0, "gh_formula_bad_rows": 0, "gh_formula_bad_gh": 0.0, "gh_per_gpu_gt24_rows": 0,
           "gpu_count_le0_rows": 0, "gpu_hours_total": 0.0}
    sets = {k: set() for k in ("gpu_type", "cluster_id", "site_id", "app_id", "day", "workload")}
    for i in range(f.num_row_groups):
        d = f.read_row_group(i, columns=COLS).to_pandas()
        n = len(d)
        chk["rows"] += n
        chk["gpu_hours_total"] += float(d.gpu_hours.sum())
        # gpu_hours = gpu_count x samples x 20 s (schema: GPU-hours of the segment; 20-s source observations)
        pred = d.gpu_count * d.samples * 20.0 / 3600.0
        bad = (pred - d.gpu_hours).abs() > 1e-4 * np.maximum(d.gpu_hours.abs(), 1e-3)
        chk["gh_formula_bad_rows"] += int(bad.sum())
        chk["gh_formula_bad_gh"] += float(d.gpu_hours[bad].sum())
        chk["gh_per_gpu_gt24_rows"] += int((d.gpu_hours > 24.0 * d.gpu_count + 1e-6).sum())
        chk["gpu_count_le0_rows"] += int((d.gpu_count <= 0).sum())
        for k in sets:
            sets[k].update(d[k].dropna().unique().tolist())
        d["period"] = period(d.day.values)
        d["mpg"] = (d.gpu_mem_alloc / d.gpu_count.where(d.gpu_count > 0)).round(1)
        out["day_wl"].append(gsum(d, ["day", "workload"]))
        out["mem_per_gpu"].append(gsum(d, ["workload", "gpu_type", "mpg"]))
        out["variants"].append(
            d.groupby(["workload", "base_id", "model_id", "params_b", "period"], dropna=False)
             .agg(gpu_hours=("gpu_hours", "sum"), rows=("gpu_hours", "size")).reset_index())
        o = d[d.workload == "online"]
        out["online"].append(gsum(o, ["day", "params_b", "gpu_count", "gpu_type", "pd_role", "model_arch"]))
        o = o.assign(mem=o.gpu_mem_alloc.round(0))
        out["online_mem"].append(gsum(o, ["period", "params_b", "gpu_count", "mem", "pd_role"]))
        w = o[(o.day >= WEEK[0]) & (o.day <= WEEK[1])]
        out["week_rows"].append(w[["instance_id", "day", "model_id", "base_id", "params_b", "gpu_count", "gpu_type",
                                   "pd_role", "cluster_id", "gpu_hours"]].copy())
        del d, o, w
    return path, combine(out), chk, {k: list(v) for k, v in sets.items()}


SUM_KEYS = {"day_wl": ["day", "workload"], "online": ["day", "params_b", "gpu_count", "gpu_type", "pd_role",
                                                      "model_arch"],
            "online_mem": ["period", "params_b", "gpu_count", "mem", "pd_role"],
            "mem_per_gpu": ["workload", "gpu_type", "mpg"]}


def combine(parts):
    res = {}
    for k, v in parts.items():
        if not v:
            continue
        df = pd.concat(v, ignore_index=True)
        if k in SUM_KEYS:
            df = gsum(df, SUM_KEYS[k])
        elif k == "variants":
            df = (df.groupby(["workload", "base_id", "model_id", "params_b", "period"], dropna=False)
                    .agg(gpu_hours=("gpu_hours", "sum"), rows=("rows", "sum")).reset_index())
        res[k] = df
    return res


def aggregate():
    t0 = time.time()
    parts = {k: [] for k in ("day_wl", "online", "online_mem", "mem_per_gpu", "variants", "week_rows")}
    chk, sets = {}, {}
    with Pool(NPROC) as pool:   # imap keeps file order, so the float sums do not depend on worker timing
        for j, (path, agg, c, s) in enumerate(pool.imap(agg_file, FILES)):
            for k, v in agg.items():
                parts[k].append(v)
            for k, v in c.items():
                chk[k] = chk.get(k, 0) + v
            for k, v in s.items():
                sets.setdefault(k, set()).update(v)
            if (j + 1) % 8 == 0:   # keep the merged tables small
                parts = {k: [v] for k, v in combine(parts).items()}
            print(f"  {j + 1}/{len(FILES)} {os.path.basename(path)} {time.time() - t0:.0f}s", flush=True)
    agg = combine(parts)
    return agg, chk, sets


# ------------------------------------------------------------------------------------------------------ analysis
def wquant(x, w, qs):
    """Weighted quantiles: smallest x whose cumulative weight share reaches q."""
    x, w = np.asarray(x, float), np.asarray(w, float)
    o = np.argsort(x)
    x, w = x[o], w[o]
    c = np.cumsum(w) / w.sum()
    return [float(x[min(np.searchsorted(c, q - 1e-12), len(x) - 1)]) for q in qs]


QS = (0.1, 0.25, 0.5, 0.75, 0.9, 0.99)


def wsummary(s):
    """s: Series value -> GPU-hours."""
    s = s[s > 0]
    q = wquant(s.index.values, s.values, QS)
    return {"weighted_quantiles_p10_25_50_75_90_99": q, "weighted_mean": float((s.index * s).sum() / s.sum())}


def share_table(s, top=None, min_share=0.0):
    s = s[s > 0].sort_values(ascending=False)
    sh = s / s.sum()
    sh = sh[sh >= min_share]
    if top:
        sh = sh.head(top)
    return {str(k): round(float(v), 5) for k, v in sh.items()}


def jenks_weighted(x, w, k):
    """Exact weighted 1-D k-means (natural breaks) over sorted distinct values x with weights w.

    Minimizes the total within-class weighted sum of squares; returns the class index of each value."""
    n = len(x)
    cw, cwx, cwx2 = (np.concatenate([[0.0], np.cumsum(a)]) for a in (w, w * x, w * x * x))

    def cost(i, j):  # values i..j-1
        W = cw[j] - cw[i]
        S = cwx[j] - cwx[i]
        return (cwx2[j] - cwx2[i]) - S * S / W if W > 0 else 0.0

    D = np.full((k + 1, n + 1), np.inf)
    B = np.zeros((k + 1, n + 1), dtype=int)
    D[0, 0] = 0.0
    for c in range(1, k + 1):
        for j in range(c, n + 1):
            best, arg = np.inf, c - 1
            for i in range(c - 1, j):
                v = D[c - 1, i] + cost(i, j)
                if v < best:
                    best, arg = v, i
            D[c, j], B[c, j] = best, arg
    cls, j = np.zeros(n, dtype=int), n
    for c in range(k, 0, -1):
        i = B[c, j]
        cls[i:j] = c - 1
        j = i
    return cls, float(D[k, n])


def cache_key():
    """Key of the aggregation pass: input files (size, mtime), columns, windows and the aggregation code."""
    h = hashlib.sha256()
    for f in FILES:
        st = os.stat(f)
        h.update(f"{f}|{st.st_size}|{st.st_mtime_ns}\n".encode())
    h.update(json.dumps([COLS, WEEK, LAST28, sorted(SUM_KEYS.items())]).encode())
    for fn in (period, gsum, agg_file, combine, aggregate):
        h.update(inspect.getsource(fn).encode())
    return h.hexdigest()


def main():
    if os.path.exists(LOG):
        os.remove(LOG)
    cache = os.environ.get("A10_AGG_CACHE")  # development only: reuse the aggregation pass
    key = cache_key()
    if cache and os.path.exists(cache):
        with open(cache, "rb") as fh:
            obj = pickle.load(fh)
        if not (isinstance(obj, dict) and obj.get("key") == key):
            sys.exit(f"A10_AGG_CACHE {cache} was written by other inputs or other aggregation code; delete it")
        agg, chk, sets = obj["agg"], obj["chk"], obj["sets"]
        log("loaded aggregation cache", cache)
    else:
        agg, chk, sets = aggregate()
        if cache:
            with open(cache, "wb") as fh:
                pickle.dump({"key": key, "agg": agg, "chk": chk, "sets": sets}, fh)
    analyse(agg, chk, sets)


def tier_of(p):
    p = np.asarray(p, float)
    return np.select([p < TIER_EDGES[0], p < TIER_EDGES[1], p >= TIER_EDGES[1]], TIERS, default="unknown")


def fmt(x):
    return f"{float(x):g}"


def mem_class(gib):
    for lo, hi, name in MEM_CLASSES:
        if lo <= gib < hi:
            return name
    return "unknown"


def model_key(model_id, base_id):
    """Trace authors' pooling: base-only (b_) and both (x_) model_ids are pooled by base_id."""
    pooled = model_id.str[:2].isin(["b_", "x_"])
    return np.where(pooled, "base:" + base_id.fillna("NULL"), "model:" + model_id.fillna("NULL"))


def n_variants(v):
    """Variants per base (trace authors' rule): [b_ or x_ present] + #distinct s_/x_ model_ids."""
    v = v[v.base_id.notna() & v.model_id.notna()]
    cls = v.model_id.str[:2]
    has_base = v.assign(b=cls.isin(["b_", "x_"])).groupby("base_id").b.any().astype(int)
    sft = v[cls.isin(["s_", "x_"])].groupby("base_id").model_id.nunique()
    return has_base.add(sft, fill_value=0).astype(int)


def n_for_share(s, shares=(0.5, 0.8, 0.9)):
    s = s[s > 0].sort_values(ascending=False)
    c = s.cumsum() / s.sum()
    return {fmt(q): int(np.searchsorted(c.values, q - 1e-12) + 1) for q in shares}


def wmed(s):
    """Weighted median of a Series value -> weight."""
    return wquant(s.index.values, s.values, (0.5,))[0]


def tier_stats(o, om, vo, type_mem):
    """o: online rows (params_b, gpu_count, gpu_type, pd_role, model_arch, gpu_hours, ih) of one window.

    ih = instance-hours (gpu_hours / gpu_count): replica-time weights. GPU-hour weights are size-biased for
    per-replica quantities (an instance counts gpu_count times)."""
    known = o[o.params_b.notna() & (o.params_b > 0)]
    tot_known, tot = known.gpu_hours.sum(), o.gpu_hours.sum()
    ih_known = known.ih.sum()
    res = {}
    for t in TIERS:
        ot = known[known.tier == t]
        gh, ih = ot.gpu_hours.sum(), ot.ih.sum()
        ps = ot.groupby("params_b").gpu_hours.sum()
        q = wquant(ps.index.values, ps.values, (0.1, 0.5, 0.9))
        psi = ot.groupby("params_b").ih.sum()
        qi = wquant(psi.index.values, psi.values, (0.1, 0.5, 0.9))
        psf = ot[ot.pd_role == "fused"].groupby("params_b").ih.sum()
        qf = wquant(psf.index.values, psf.values, (0.1, 0.5, 0.9))
        mp = ot[ot.params_b == qi[1]]       # the all-instance median's mass point
        mp_fused = mp[mp.pd_role == "fused"]
        median_point = {"params_b": qi[1],
                        "share_of_tier_instance_hours": round(float(mp.ih.sum() / ih), 4),
                        "pd_disaggregated_share_of_its_instance_hours": round(float(
                            mp[mp.pd_role.isin(["prefill", "decode"])].ih.sum() / mp.ih.sum()), 4),
                        "share_of_fused_tier_instance_hours": round(float(mp_fused.ih.sum() / psf.sum()), 4),
                        "params_b_instance_hour_cdf_below_and_at": [
                            round(float(psi[psi.index < qi[1]].sum() / psi.sum()), 4),
                            round(float(psi[psi.index <= qi[1]].sum() / psi.sum()), 4)]}
        gc = ot.groupby("gpu_count").gpu_hours.sum()
        fu = ot[ot.pd_role == "fused"].groupby("gpu_count").gpu_hours.sum()
        g_med = wmed(gc)
        g_med_fused = wmed(fu)
        gci = ot.groupby("gpu_count").ih.sum()
        fui = ot[ot.pd_role == "fused"].groupby("gpu_count").ih.sum()
        ot = ot.assign(mc=ot.gpu_type.map(type_mem).map(mem_class))
        by_mc = {}
        for mc, g in ot.groupby("mc"):
            s = g.groupby("gpu_count").gpu_hours.sum()
            si = g.groupby("gpu_count").ih.sum()
            pi = g.groupby("params_b").ih.sum()
            by_mc[mc] = {"share_of_tier_gh": round(float(g.gpu_hours.sum() / gh), 4),
                         "share_of_tier_instance_hours": round(float(g.ih.sum() / ih), 4),
                         "g_weighted_median": wmed(s),
                         "g_instance_hour_weighted_median": wmed(si),
                         "params_b_instance_hour_weighted_p10_p50_p90": wquant(pi.index.values, pi.values,
                                                                               (0.1, 0.5, 0.9)),
                         "gpu_count_share": {fmt(k): round(float(v / s.sum()), 4) for k, v in s.items() if v > 0}}
        # largest params_b mass points (instance-hours) with the gpu_count mix of their fused instances
        top_p = {}
        for p, x in psi.sort_values(ascending=False).head(4).items():
            f = ot[(ot.params_b == p) & (ot.pd_role == "fused")].groupby("gpu_count").ih.sum()
            top_p[fmt(p)] = {"share_of_tier_instance_hours": round(float(x / ih), 4),
                             "fused_g_instance_hour_weighted_median": wmed(f) if f.sum() > 0 else None,
                             "fused_gpu_count_share_instance_hours": {fmt(k): round(float(v / f.sum()), 4)
                                                                      for k, v in f.items() if v > 0}}
        omt = om[om.tier == t]
        ms = omt.groupby("mem").gpu_hours.sum()
        mq = wquant(ms.index.values, ms.values, (0.1, 0.5, 0.9))
        mf = omt[omt.params_b > 0].assign(gb=lambda x: x["mem"] * GIB_GB)   # allocated GPU memory in GB
        rq = wquant((mf.gb / (2.0 * mf.params_b)).values, mf.gpu_hours.values, (0.1, 0.5, 0.9))
        fit16 = float(mf.gpu_hours[2.0 * mf.params_b > mf.gb].sum() / mf.gpu_hours.sum())
        fit8 = float(mf.gpu_hours[mf.params_b > mf.gb].sum() / mf.gpu_hours.sum())
        vt = vo[vo.tier == t]
        keys = vt.groupby("key").gpu_hours.sum()
        res[t] = {
            "params_b_range": [float(ps.index.min()), float(ps.index.max())],
            "gpu_hours": float(gh),
            "instance_hours": float(ih),
            "share_of_online_gh_with_params": round(float(gh / tot_known), 4),
            "share_of_online_gh": round(float(gh / tot), 4),
            "share_of_online_instance_hours_with_params": round(float(ih / ih_known), 4),
            "params_b_weighted_p10_p50_p90": q,
            "params_b_instance_hour_weighted_p10_p50_p90": qi,
            "params_b_instance_hour_weighted_p10_p50_p90_fused_instances": qf,
            "params_b_instance_hour_median_mass_point": median_point,
            "params_b_top_mass_points_share_of_tier": {fmt(k): round(float(v / gh), 4)
                                                       for k, v in ps.sort_values(ascending=False).head(6).items()},
            "params_b_top_mass_points_instance_hours": top_p,
            "weights_GB_16bit_at_p50": 2.0 * q[1],
            "gpu_count_share": {fmt(k): round(float(v / gh), 4) for k, v in gc.items() if v > 0},
            "gpu_count_share_instance_hours": {fmt(k): round(float(v / ih), 4) for k, v in gci.items() if v > 0},
            "fused_gpu_count_share_instance_hours": {fmt(k): round(float(v / fui.sum()), 4)
                                                     for k, v in fui.items() if v > 0},
            "g_weighted_median_all_instances": g_med,
            "g_weighted_median_fused_instances": g_med_fused,
            "g_instance_hour_weighted_median_all_instances": wmed(gci),
            "g_instance_hour_weighted_median_fused_instances": wmed(fui),
            "g_weighted_mean_all_instances": float((gc.index * gc).sum() / gc.sum()),
            "g_by_gpu_memory_class": by_mc,
            "instance_gpu_mem_alloc_GiB_weighted_p10_p50_p90": mq,
            "instance_mem_GB_over_16bit_weights_weighted_p10_p50_p90": rq,
            "gh_share_16bit_weights_exceed_instance_mem": round(fit16, 4),
            "gh_share_8bit_weights_exceed_instance_mem": round(fit8, 4),
            "moe_share": round(float(ot[ot.model_arch == "moe"].gpu_hours.sum() / gh), 4),
            "pd_disaggregated_share": round(float(ot[ot.pd_role.isin(["prefill", "decode"])].gpu_hours.sum() / gh), 4),
            "n_model_ids": int(vt.model_id.nunique()),
            "n_base_ids_excluding_dash_placeholder": int(vt.loc[vt.base_id != "-", "base_id"].nunique()),
            "n_model_keys": int(len(keys)),
            "n_model_keys_for_gh_share": n_for_share(keys),
        }
    return res


def analyse(agg, chk, sets):
    res = {"source": {"trace": "Alibaba cluster-trace-v2026-maas, instance_daily (zheng2026model)",
                      "files": len(FILES), "windows_days": {k: list(v) for k, v in WINDOWS.items()},
                      "weights": "allocated GPU-hours (gpu_hours) of online instance segments, and instance-hours "
                                 "(gpu_hours / gpu_count, replica time) where a field name says instance_hour(s)",
                      "tier_rule": f"S: params_b < {fmt(TIER_EDGES[0])}; M: {fmt(TIER_EDGES[0])} <= params_b < "
                                   f"{fmt(TIER_EDGES[1])}; L: params_b >= {fmt(TIER_EDGES[1])} (total parameters, B)"}}
    on, om, v, w = agg["online"].copy(), agg["online_mem"].copy(), agg["variants"].copy(), agg["week_rows"].copy()
    on["tier"] = tier_of(on.params_b)
    assert chk["gpu_count_le0_rows"] == 0 and (on.gpu_count > 0).all()
    on["ih"] = on.gpu_hours / on.gpu_count   # instance-hours (replica time); gpu_count > 0 on every row
    om["tier"] = tier_of(om.params_b)
    v["tier"] = tier_of(v.params_b)
    v["key"] = model_key(v.model_id, v.base_id)

    # ---------------------------------------------------------------- checks of the field semantics we rely on
    days = sorted(int(d) for d in sets["day"])
    mp = agg["mem_per_gpu"]
    mpo = mp[mp.mpg.notna()]
    modal = mpo.sort_values("gpu_hours").groupby("gpu_type").mpg.last()          # GiB per GPU, modal by GPU-hours
    near = mpo.assign(m=mpo.gpu_type.map(modal)).pipe(lambda x: (x.mpg - x.m).abs() <= 0.5)
    wk = w.groupby("instance_id").agg(**{c: (c, "nunique") for c in ("model_id", "params_b", "gpu_count",
                                                                     "gpu_type", "pd_role", "cluster_id")},
                                      gh=("gpu_hours", "sum"))
    idd = w.groupby(["instance_id", "day"]).agg(gh=("gpu_hours", "sum"), gc=("gpu_count", "max"))
    hrs = idd.gh / idd.gc
    va = v.groupby(["base_id", "model_id"], dropna=False).gpu_hours.sum().reset_index()
    nv_all = n_variants(va)
    vo_all = v[v.workload == "online"]
    pm = vo_all[vo_all.params_b.notna()].groupby("model_id").agg(n=("params_b", "nunique"),
                                                                  nb=("base_id", "nunique"), gh=("gpu_hours", "sum"))
    nl = vo_all[vo_all.params_b.isna()]
    nul_cls = nl.gpu_hours.groupby(nl.model_id.fillna("NULL").str[:2].replace({"": "empty"})).sum()
    pb = vo_all[vo_all.params_b.notna() & (vo_all.base_id != "-")].groupby("base_id").agg(
        n=("params_b", "nunique"), gh=("gpu_hours", "sum"))
    a2b = json.load(open(os.path.join(OUT, "a2b_lender_maas_daily.json")))["gpu_hours_share_by_workload"]
    dw = agg["day_wl"].groupby("workload").gpu_hours.sum()
    res["checks"] = {
        "rows": {"value": chk["rows"], "readme": README["rows"]},
        "days": {"n": len(days), "min": days[0], "max": days[-1],
                 "missing": sorted(set(range(days[0], days[-1] + 1)) - set(days))},
        "clusters": {"value": len(sets["cluster_id"]), "readme": README["clusters"]},
        "sites": len(sets["site_id"]),
        "gpu_type_values": {"all": len(sets["gpu_type"]),
                            "named_gpu_": sum(1 for x in sets["gpu_type"] if x.startswith("gpu_")),
                            "unknown_": sum(1 for x in sets["gpu_type"] if x.startswith("unknown_")),
                            "empty": sum(1 for x in sets["gpu_type"] if x == ""), "readme": README["gpu_types"]},
        "apps": {"value": len(sets["app_id"]), "readme_approx": README["apps"]},
        "variants_all_workloads_authors_rule": {"value": int(nv_all.sum()), "bases": int(len(nv_all)),
                                                "readme_approx": README["variants"]},
        "workload_values": sorted(sets["workload"]),
        "workload_gh_share": {k: float(x / dw.sum()) for k, x in dw.items()},
        "workload_gh_share_a2b": a2b,
        "gpu_hours_eq_gpu_count_x_samples_x_20s": {
            "rows_violating_rel_1e-4": chk["gh_formula_bad_rows"], "rows": chk["rows"]},
        "rows_with_gpu_hours_over_24h_per_gpu": chk["gh_per_gpu_gt24_rows"],
        "rows_with_gpu_count_le_0": chk["gpu_count_le0_rows"],
        "gh_share_mem_per_gpu_within_0.5GiB_of_type_mode": float(mpo.gpu_hours[near].sum() / mpo.gpu_hours.sum()),
        "week_online_instances": {
            "n": int(len(wk)),
            **{f"gh_share_instances_with_gt1_{c}": round(float(wk.gh[wk[c] > 1].sum() / wk.gh.sum()), 5)
               for c in ("model_id", "params_b", "gpu_count", "gpu_type", "pd_role", "cluster_id")},
            "instance_days": int(len(idd)),
            "instance_days_over_24h_per_gpu": int((hrs > 24 + 1e-6).sum()),
            "gh_share_instance_days_ge_23.9h": round(float(idd.gh[hrs >= 23.9].sum() / idd.gh.sum()), 4)},
        "online_params_b_varies_within_model_id_gh_share": round(float(pm.gh[pm.n > 1].sum() / pm.gh.sum()), 4),
        "online_model_id_under_gt1_base_id_gh_share": round(float(pm.gh[pm.nb > 1].sum() / pm.gh.sum()), 4),
        "online_params_b_null_gh_share_by_model_id_class": {
            k: round(float(x), 4) for k, x in (nul_cls / nul_cls.sum()).items()},
        "online_params_b_varies_within_base_id": {
            "share_of_bases": round(float((pb.n > 1).mean()), 4),
            "gh_share": round(float(pb.gh[pb.n > 1].sum() / pb.gh.sum()), 4)},
    }
    res["gpu_types"] = {}
    type_gh = on.groupby("gpu_type").gpu_hours.sum().sort_values(ascending=False)
    for k, x in type_gh.items():
        if x > 0:
            res["gpu_types"][k[:20] if k else "(empty)"] = {
                "share_online_gh": round(float(x / type_gh.sum()), 5),
                "GiB_per_gpu_modal": float(modal.get(k, np.nan)),
                "memory_class": mem_class(modal.get(k, np.nan))}
    mc = on.assign(mc=on.gpu_type.map(modal).map(mem_class)).groupby("mc").gpu_hours.sum()
    res["gpu_memory_class_share_online_gh"] = {k: round(float(x / mc.sum()), 4) for k, x in mc.items()}

    # ---------------------------------------------------------------------------- distributions and tiers
    res["online"], res["tiers"], res["natural_breaks"] = {}, {}, {}
    for wn, (a, b) in WINDOWS.items():
        o = on[(on.day >= a) & (on.day <= b)]
        tot = o.gpu_hours.sum()
        kn = o[o.params_b.notna() & (o.params_b > 0)]
        ps = kn.groupby("params_b").gpu_hours.sum()
        gc = o.groupby("gpu_count").gpu_hours.sum()
        nul = o[o.params_b.isna() | (o.params_b <= 0)]
        ng = nul.groupby("gpu_count").gpu_hours.sum()
        cdf = ps.sort_index().cumsum() / ps.sum()
        res["online"][wn] = {
            "gpu_hours": float(tot),
            "params_b_null_share": round(float(nul.gpu_hours.sum() / tot), 4),
            "params_b_null_gpu_count_share": {fmt(k): round(float(x / ng.sum()), 4) for k, x in ng.items() if x > 0},
            "params_b": wsummary(ps),
            "params_b_mass_points_ge_1pct": share_table(ps, min_share=0.01),
            "params_b_share_le": {fmt(x): round(float(cdf[cdf.index <= x].iloc[-1]), 4)
                                  for x in (3, 8, 10, 14, 32, 70, 100, 235, 405, 706)},
            "gpu_count": {**wsummary(gc), "share": {fmt(k): round(float(x / gc.sum()), 5)
                                                    for k, x in gc.sort_index().items() if x > 0}},
            "gpu_count_share_by_params_bin": {},
            "pd_role_share": share_table(o.groupby("pd_role").gpu_hours.sum()),
            "model_arch_share": share_table(o.groupby("model_arch").gpu_hours.sum()),
        }
        bins = [0, 2, 5, 10, 20, 40, 100, 200, 400, 800, 1100]
        kb = kn.assign(bin=pd.cut(kn.params_b, bins))
        for bi, g in kb.groupby("bin", observed=True):
            s = g.groupby("gpu_count").gpu_hours.sum()
            res["online"][wn]["gpu_count_share_by_params_bin"][str(bi)] = {
                "share_of_known": round(float(s.sum() / ps.sum()), 4),
                "gpu_count_share": {fmt(k): round(float(x / s.sum()), 4) for k, x in s.items() if x > 0}}
        x, wt = np.log10(ps.index.values), ps.values
        nb = {}
        for k in (2, 3, 4):
            cls, sse = jenks_weighted(x, wt, k)
            sst = float((wt * (x - (wt * x).sum() / wt.sum()) ** 2).sum())
            nb[str(k)] = {"classes_params_b_min_max_share": [
                [float(ps.index[cls == c].min()), float(ps.index[cls == c].max()),
                 round(float(wt[cls == c].sum() / wt.sum()), 4)] for c in range(k)],
                "within_over_total_ss": round(sse / sst, 4)}
        res["natural_breaks"][wn] = nb
        per = PERIODS[wn]
        vo = v[(v.workload == "online") & v.period.isin(per)]
        res["tiers"][wn] = tier_stats(o, om[om.period.isin(per)], vo, modal)

    # tier shares over the six months, 28-day blocks
    blocks = {}
    kn = on[on.params_b.notna() & (on.params_b > 0)]
    for s0 in range(0, 182, 28):
        g = kn[(kn.day >= s0) & (kn.day < s0 + 28)].groupby("tier").gpu_hours.sum()
        blocks[f"{s0}-{min(s0 + 27, 181)}"] = {t: round(float(g.get(t, 0) / g.sum()), 4) for t in TIERS}
    res["tier_share_by_28day_block"] = blocks
    # catalog medians per 28-day block (instance-hour weights): fused g, params_b over all instances of the tier and
    # over fused instances only (stability of the proposed catalog over the six months)
    cblocks = {}
    for s0 in range(0, 182, 28):
        b = kn[(kn.day >= s0) & (kn.day < s0 + 28)]
        cb = {}
        for t in TIERS:
            bt = b[b.tier == t]
            fu = bt[bt.pd_role == "fused"]
            cb[t] = {"g_fused": wmed(fu.groupby("gpu_count").ih.sum()),
                     "params_b": wmed(bt.groupby("params_b").ih.sum()),
                     "params_b_fused_instances": wmed(fu.groupby("params_b").ih.sum()),
                     "pd_disaggregated_share_instance_hours": round(float(
                         bt[bt.pd_role.isin(["prefill", "decode"])].ih.sum() / bt.ih.sum()), 4)}
        cblocks[f"{s0}-{min(s0 + 27, 181)}"] = cb
    res["tier_catalog_by_28day_block"] = cblocks
    # NULL params_b (mostly 1-GPU instances): tier shares of all online GPU-hours (and instance-hours) if they all
    # counted as S
    res["tier_share_null_params_as_S"] = {}
    res["tier_share_null_params_as_S_instance_hours"] = {}
    for wn, (a, b) in WINDOWS.items():
        o = on[(on.day >= a) & (on.day <= b)]
        for key, col in (("tier_share_null_params_as_S", "gpu_hours"), ("tier_share_null_params_as_S_instance_hours", "ih")):
            g = o.groupby("tier")[col].sum()
            res[key][wn] = {
                "S": round(float((g.get("S", 0) + g.get("unknown", 0)) / g.sum()), 4),
                "M": round(float(g.get("M", 0) / g.sum()), 4), "L": round(float(g.get("L", 0) / g.sum()), 4)}
    res["tier_share_units"] = (
        "share_of_online_gh_with_params: share of allocated online GPU-hours (gpu_count x time, idle allocation "
        "included); share_of_online_instance_hours_with_params: share of instance-hours (replica time; a "
        "PD-disaggregated replica counts its prefill and decode instances). Neither is a request or token share: "
        "converting to one needs the replica capacity kappa_j (design §5.3.1), an ASSUMPTION")

    # ---------------------------------------------------------------------------- variants and sharing
    res["variants"] = {}
    for wn, per in PERIODS.items():
        vo = v[(v.workload == "online") & v.period.isin(per)]
        tot = vo.gpu_hours.sum()
        cls = vo.model_id.fillna("NULL").str[:2].replace({"": "empty"})
        # authors' rule: base_id IS NOT NULL, so the '-' placeholder base counts as one base
        nva = n_variants(vo[vo.base_id.notna()].groupby(["base_id", "model_id"]).gpu_hours.sum().reset_index())
        # distributions over bases: without the '-' placeholder, which pools unrelated models
        real = vo[vo.base_id.notna() & (vo.base_id != "-")]
        nvb = n_variants(real.groupby(["base_id", "model_id"]).gpu_hours.sum().reset_index())
        bgh = real.groupby("base_id").gpu_hours.sum().reindex(nvb.index)
        # variants that share the base and the parameter count
        real_p = real[real.params_b.notna()]
        bp = real_p.assign(bp=real_p.base_id + "|" + real_p.params_b.map(fmt))
        nvp = n_variants(bp.drop(columns="base_id").rename(columns={"bp": "base_id"}))
        bpgh = bp.groupby("bp").gpu_hours.sum().reindex(nvp.index)
        keys = vo.groupby("key").gpu_hours.sum()
        ks = keys.sort_values(ascending=False)
        res["variants"][wn] = {
            "gh_share_by_model_id_class": {k: round(float(x / tot), 4)
                                           for k, x in vo.gpu_hours.groupby(cls).sum().items()},
            "gh_share_base_id_placeholder_dash": round(float(vo.gpu_hours[vo.base_id == "-"].sum() / tot), 4),
            "n_model_ids": int(vo.model_id.nunique()),
            "n_bases_authors_rule": int(len(nva)),
            "n_variants_authors_rule": int(nva.sum()),
            "n_variants_of_dash_placeholder": int(nva.get("-", 0)),
            "n_bases_excluding_dash_placeholder": int(len(nvb)),
            "n_variants_excluding_dash_placeholder": int(nvb.sum()),
            "distributions_below_exclude_dash_placeholder": True,
            "variants_per_base": {
                "share_of_bases_with_1": round(float((nvb == 1).mean()), 4),
                "unweighted_p50_p90_max": [float(np.percentile(nvb, 50)), float(np.percentile(nvb, 90)),
                                           int(nvb.max())],
                "gh_weighted_p10_p25_p50_p75_p90": wquant(nvb.values, bgh.values, (0.1, 0.25, 0.5, 0.75, 0.9)),
                "gh_share_of_bases_with_ge_10_variants": round(float(bgh[nvb >= 10].sum() / bgh.sum()), 4)},
            "variants_per_base_and_params_b": {
                "n_groups": int(len(nvp)),
                "gh_weighted_p10_p25_p50_p75_p90": wquant(nvp.values, bpgh.values, (0.1, 0.25, 0.5, 0.75, 0.9)),
                "gh_share_of_groups_with_ge_10_variants": round(float(bpgh[nvp >= 10].sum() / bpgh.sum()), 4)},
            "base_concentration": {"top10_share": round(float(bgh.sort_values(ascending=False).head(10).sum()
                                                              / bgh.sum()), 4),
                                   "n_bases_for_gh_share": n_for_share(bgh)},
            "model_key_concentration": {
                "n_model_keys": int(len(keys)),
                "top10pct_keys_share": round(float(ks.head(max(1, len(ks) // 10)).sum() / ks.sum()), 4),
                "n_model_keys_for_gh_share": n_for_share(keys)},
        }
    # instances per LLM in the lender week, per model_key and day: distinct instance_ids seen during the day (an
    # instance that ran part of the day counts as 1; PD prefill and decode instances count separately) and the
    # mean number of concurrent instances, sum of instance-hours / 24 (all instances; fused only = replicas)
    w["key"] = model_key(w.model_id, w.base_id)
    w["ih"] = w.gpu_hours / w.gpu_count

    def per_key(x):
        k = x.groupby(["key", "day"]).agg(n=("instance_id", "nunique"), ih=("ih", "sum"), gh=("gpu_hours", "sum"))
        k["conc"] = k.ih / 24.0
        return k.groupby("key").agg(n=("n", "mean"), conc=("conc", "mean"), gh=("gh", "sum"))

    kk, kf = per_key(w), per_key(w[w.pd_role == "fused"])
    qs5 = (0.1, 0.25, 0.5, 0.75, 0.9)
    res["variants"]["week"]["instances_per_model_key_per_day"] = {
        "definition": "per model_key, mean over its days in the week of (a) distinct instance_ids per day (an "
                      "instance that ran part of the day counts as one; PD prefill and decode instances count "
                      "separately) and (b) mean concurrent instances = instance-hours / 24; quantiles over keys "
                      "weighted by GPU-hours. *_fused: the same over fused (PD-collocated) instances only, keys "
                      "weighted by their fused GPU-hours; a fused instance is one warm replica",
        "distinct_instances_unweighted_p50_p90": [float(kk.n.median()), float(kk.n.quantile(0.9))],
        "distinct_instances_gh_weighted_p10_p25_p50_p75_p90": wquant(kk.n.values, kk.gh.values, qs5),
        "concurrent_instances_gh_weighted_p10_p25_p50_p75_p90": wquant(kk.conc.values, kk.gh.values, qs5),
        "distinct_fused_instances_gh_weighted_p10_p25_p50_p75_p90": wquant(kf.n.values, kf.gh.values, qs5),
        "concurrent_fused_instances_gh_weighted_p10_p25_p50_p75_p90": wquant(kf.conc.values, kf.gh.values, qs5),
        "share_of_instance_days_under_23.9_instance_hours": round(float(
            (w.groupby(["instance_id", "day"]).ih.sum() < 23.9).mean()), 4)}

    # ---------------------------------------------------------------------------- comparison with Table 5.4
    a5 = json.load(open(os.path.join(OUT, "a5_reclaim_cost_calibration.json")))["assumptions"]
    cmp = {}
    for t in TIERS:
        m, (name, size) = res["tiers"]["all"][t], DEFAULT_TIERS[t]
        cmp[t] = {"table_5_4": {"llm": name, "params_b": size, "weights_GB": a5["weights_gb"][name],
                                "replica_hbm_GB": a5["replica_hbm_GB"][name],
                                "g_80GB": a5["replica_hbm_GB"][name] // 80},
                  "maas": {"params_b_p50": m["params_b_weighted_p10_p50_p90"][1],
                           "params_b_p50_instance_hours": m["params_b_instance_hour_weighted_p10_p50_p90"][1],
                           "weights_GB_16bit_at_p50": m["weights_GB_16bit_at_p50"],
                           "g_weighted_median_fused": m["g_weighted_median_fused_instances"],
                           "g_instance_hour_weighted_median_fused": m["g_instance_hour_weighted_median_fused_instances"],
                           "g_on_80GiB_class": m["g_by_gpu_memory_class"].get("~80GiB", {}).get("g_weighted_median"),
                           "share_of_tier_gh_on_80GiB_class": m["g_by_gpu_memory_class"].get("~80GiB", {}).get(
                               "share_of_tier_gh"),
                           "instance_mem_GiB_p50": m["instance_gpu_mem_alloc_GiB_weighted_p10_p50_p90"][1],
                           "gh_share_16bit_weights_exceed_instance_mem": m["gh_share_16bit_weights_exceed_instance_mem"],
                           "share_of_online_gh_with_params": m["share_of_online_gh_with_params"],
                           "moe_share": m["moe_share"]},
                  "maas_gh_share_params_b_le_table_5_4_size": res["online"]["all"]["params_b_share_le"][fmt(size)]}
    res["comparison_with_table_5_4"] = cmp

    # ---------------------------------------------------------------------------- proposed catalog (MS0, Q30)
    def fits(w_gb, g):
        return w_gb <= HBM_USABLE * PRICE_GPU_GB * g

    def g_mem(w_gb):
        """Smallest power-of-two GPU count whose usable HBM (0.9 x 80 GB each) holds the weights."""
        g = 1
        while not fits(w_gb, g):
            g *= 2
        return g

    def entry(params_b, g, basis, precision=None):
        w16, w8 = 2.0 * params_b, 1.0 * params_b
        prec = precision or ("16-bit" if fits(w16, g) else "8-bit")
        w = w16 if prec == "16-bit" else w8
        assert fits(w, g), (params_b, g, prec)
        return {"params_b": params_b, "g": g, "precision": prec, "w_GB": w,
                "usable_HBM_GB": HBM_USABLE * PRICE_GPU_GB * g, "kv_room_GB": HBM_USABLE * PRICE_GPU_GB * g - w,
                "basis": basis}

    prop = {}
    for t in TIERS:
        m, wkt, l28 = res["tiers"]["all"][t], res["tiers"]["week"][t], res["tiers"]["last28"][t]
        p50 = m["params_b_instance_hour_weighted_p10_p50_p90"][1]
        g = m["g_instance_hour_weighted_median_fused_instances"]
        prop[t] = {"params_b_range": {"S": [0, TIER_EDGES[0]], "M": list(TIER_EDGES),
                                      "L": [TIER_EDGES[1], None]}[t],
                   "params_b": p50, "g": g,
                   "params_b_fused_instances": m["params_b_instance_hour_weighted_p10_p50_p90_fused_instances"][1],
                   "params_b_median_mass_point": m["params_b_instance_hour_median_mass_point"],
                   "params_b_gpu_hour_weighted": m["params_b_weighted_p10_p50_p90"][1],
                   "g_gpu_hour_weighted": m["g_weighted_median_fused_instances"],
                   "share_allocated_gpu_hours": m["share_of_online_gh_with_params"],
                   "share_instance_hours": m["share_of_online_instance_hours_with_params"],
                   "weights_GB_16bit": 2.0 * p50, "weights_GB_8bit": p50,
                   "fits_on_g_x_80GB": {"16-bit": fits(2.0 * p50, g), "8-bit": fits(p50, g)},
                   "g_80GB_memory_derived_16bit": g_mem(2.0 * p50),
                   "moe_share": m["moe_share"], "pd_disaggregated_share": m["pd_disaggregated_share"],
                   "week_check": {"params_b": wkt["params_b_instance_hour_weighted_p10_p50_p90"][1],
                                  "g_fused": wkt["g_instance_hour_weighted_median_fused_instances"],
                                  "params_b_fused_instances":
                                      wkt["params_b_instance_hour_weighted_p10_p50_p90_fused_instances"][1],
                                  "params_b_gpu_hour_weighted": wkt["params_b_weighted_p10_p50_p90"][1],
                                  "g_fused_gpu_hour_weighted": wkt["g_weighted_median_fused_instances"],
                                  "share_allocated_gpu_hours": wkt["share_of_online_gh_with_params"],
                                  "share_instance_hours": wkt["share_of_online_instance_hours_with_params"]},
                   "last28_check": {"params_b": l28["params_b_instance_hour_weighted_p10_p50_p90"][1],
                                    "g_fused": l28["g_instance_hour_weighted_median_fused_instances"],
                                    "params_b_fused_instances":
                                        l28["params_b_instance_hour_weighted_p10_p50_p90_fused_instances"][1]}}
    S, M, L = (prop[t] for t in TIERS)
    # L at 8 GPUs: the 16-bit weights do not fit on 8 x 80 GB, so the default L uses 8-bit weights; the 16-bit L
    # needs the memory-derived g. The 235B mass point runs mostly on 4 GPUs (fused, instance-hours) and is the
    # instance-hour median of L in the lender week, so g = 4 is a sensitivity entry.
    l4 = res["tiers"]["all"]["L"]["params_b_top_mass_points_instance_hours"]
    p4 = max(l4, key=lambda p: l4[p]["share_of_tier_instance_hours"])
    entries = {
        "S": entry(S["params_b"], int(S["g"]), "instance-hour medians (params_b, fused g), window all"),
        "M": entry(M["params_b"], int(M["g"]), "instance-hour medians (params_b, fused g), window all"),
        "L": entry(L["params_b"], int(L["g"]), "instance-hour medians (params_b, fused g), window all; 16-bit "
                                               "weights do not fit on g x 80 GB"),
        "M_g_gpu_hours": entry(M["params_b"], int(M["g_gpu_hour_weighted"]),
                               "M with the GPU-hour-weighted fused g (size-biased); sensitivity"),
        "L_16bit": entry(L["params_b"], L["g_80GB_memory_derived_16bit"], "L with 16-bit weights and the "
                         "memory-derived g on 80 GB GPUs (as a5 does for 405B); sensitivity", precision="16-bit"),
        "L_g4": entry(float(p4), int(l4[p4]["fused_g_instance_hour_weighted_median"]),
                      f"largest L mass point ({p4}B, {l4[p4]['share_of_tier_instance_hours']} of L instance-hours) "
                      "with its fused g; L median in the lender week; sensitivity"),
    }
    res["proposed_catalog"] = {
        "definition": "window all (days 0-181); params_b = instance-hour-weighted median over all online instances "
                      "of the tier (fused, prefill and decode; each holds the full weights); g = instance-hour-weighted "
                      "median gpu_count of fused (PD-collocated) online instances (GPUs per replica, weighted by "
                      "replica time). The two medians come from different populations: params_b_fused_instances is "
                      "the params_b median over fused instances only, and params_b_median_mass_point gives the "
                      "PD-disaggregated share of the median's mass point. The GPU-hour-weighted versions are "
                      "size-biased and given as *_gpu_hour_weighted; shares in allocated GPU-hours and in "
                      "instance-hours (tier_share_units); weights at 2 and 1 bytes per parameter (precision is not in "
                      "the trace); per-block medians in tier_catalog_by_28day_block",
        "price_unit_note": f"GPUs are priced as H100-80GB, so an entry is feasible only if its weights fit in "
                           f"{HBM_USABLE} x {PRICE_GPU_GB} GB x g (a5's usable HBM). On 8 x 80 GB GPUs this holds "
                           f"for 16-bit weights up to {HBM_USABLE * PRICE_GPU_GB * 8 / 2:g}B parameters and for "
                           f"8-bit weights up to {HBM_USABLE * PRICE_GPU_GB * 8:g}B. The trace's L instances run "
                           f"mostly on larger GPUs (g_by_gpu_memory_class), so g = 8 for L is consistent with 80 GB "
                           f"GPUs only with 8-bit weights or smaller L LLMs",
        "tiers": prop,
        "entries": entries,
        "default_entries": ["S", "M", "L"],
        "sensitivity_entries": ["M_g_gpu_hours", "L_16bit", "L_g4"]}

    res["field_semantics"] = {
        "workload": "online or offline (schema); only online instances enter the catalog",
        "params_b": "total parameters in B, not active MoE parameters; NULL if unavailable (schema). Used per row: "
                    "it varies within model_id and base_id (checks), so tiers are assigned per instance segment",
        "gpu_count": "allocated GPU equivalents per instance, fractional allowed (schema). Constant per instance in "
                     "the lender week (checks), so it is the replica footprint of a fused instance; a "
                     "PD-disaggregated replica spans a prefill and a decode instance",
        "gpu_hours": "allocated GPU-hours of the segment (schema); equals gpu_count x samples x 20 s on every row "
                     "(checks), i.e. allocation time, not busy time",
        "gpu_type": "anonymized GPU type; unknown_ = unknown source label (schema). GiB per GPU equivalent = "
                    "gpu_mem_alloc / gpu_count is constant within a type (checks), so it identifies a memory class",
        "gpu_mem_alloc": "total allocated GPU memory of the instance segment, GiB (schema)",
        "model_id": "anonymized source name with class prefix b_ base-only, s_ SFT-only, x_ both, o_ other (schema). "
                    "Not a unique checkpoint: some model_ids appear under several base_ids and with several "
                    "params_b values (checks)",
        "base_id": "base-model identifier; '-' is a placeholder (schema). Variants per base follow the trace "
                   "authors' rule (module docstring), which reproduces the README's ~70,000 variants (checks)",
        "pd_role": "prefill, decode or fused (PD-collocated) (schema)",
    }
    save_json("a10_maas_catalog.json", res)
    report(res)


def report(r):
    c = r["checks"]
    log("== a10 MaaS catalog")
    log("rows", c["rows"], "days", c["days"], "clusters", c["clusters"], "gpu_type values", c["gpu_type_values"])
    log("apps", c["apps"], "variants (authors' rule, all workloads)", c["variants_all_workloads_authors_rule"])
    log("workload GH share", c["workload_gh_share"], "a2b", c["workload_gh_share_a2b"])
    log("gpu_hours == gpu_count*samples*20s:", c["gpu_hours_eq_gpu_count_x_samples_x_20s"],
        "| rows >24h/GPU:", c["rows_with_gpu_hours_over_24h_per_gpu"])
    log("mem/GPU within 0.5 GiB of type mode (GH share):", round(c["gh_share_mem_per_gpu_within_0.5GiB_of_type_mode"], 4))
    log("week instances:", c["week_online_instances"])
    log("params_b varies within model_id (GH share):", c["online_params_b_varies_within_model_id_gh_share"],
        "within base_id:", c["online_params_b_varies_within_base_id"],
        "| model_id under >1 base_id (GH share):", c["online_model_id_under_gt1_base_id_gh_share"],
        "| NULL params_b by model_id class:", c["online_params_b_null_gh_share_by_model_id_class"])
    log("GPU memory classes (online GH):", r["gpu_memory_class_share_online_gh"])
    for wn in WINDOWS:
        o = r["online"][wn]
        log(f"-- window {wn}: online GH {o['gpu_hours']:.4g}, params_b null {o['params_b_null_share']}")
        log("   params_b", o["params_b"], "share<=", o["params_b_share_le"])
        log("   gpu_count", o["gpu_count"])
        log("   pd_role", o["pd_role_share"], "arch", o["model_arch_share"])
        log("   natural breaks k=3", r["natural_breaks"][wn]["3"])
        for t in TIERS:
            x = r["tiers"][wn][t]
            log(f"   tier {t}: share {x['share_of_online_gh_with_params']} params p10/50/90 "
                f"{x['params_b_weighted_p10_p50_p90']} g med (all/fused) {x['g_weighted_median_all_instances']}/"
                f"{x['g_weighted_median_fused_instances']} g share {x['gpu_count_share']} mem p50 "
                f"{x['instance_gpu_mem_alloc_GiB_weighted_p10_p50_p90'][1]} GiB moe {x['moe_share']} "
                f"disagg {x['pd_disaggregated_share']} keys {x['n_model_keys']}")
            log(f"      instance-hours: share {x['share_of_online_instance_hours_with_params']} params p10/50/90 "
                f"{x['params_b_instance_hour_weighted_p10_p50_p90']} g med (all/fused) "
                f"{x['g_instance_hour_weighted_median_all_instances']}/"
                f"{x['g_instance_hour_weighted_median_fused_instances']} fused g share "
                f"{x['fused_gpu_count_share_instance_hours']}")
    log("tier share by 28-day block", r["tier_share_by_28day_block"])
    log("catalog medians by 28-day block", json.dumps(r["tier_catalog_by_28day_block"]))
    log("tier share with NULL params counted as S (GPU-hours)", r["tier_share_null_params_as_S"])
    log("tier share with NULL params counted as S (instance-hours)", r["tier_share_null_params_as_S_instance_hours"])
    for t in TIERS:
        x = r["tiers"]["all"][t]
        log(f"   tier {t} (all): 16-bit weights exceed instance memory {x['gh_share_16bit_weights_exceed_instance_mem']}, "
            f"8-bit {x['gh_share_8bit_weights_exceed_instance_mem']}; g by memory class "
            + str({k: (v["share_of_tier_gh"], v["g_weighted_median"]) for k, v in x["g_by_gpu_memory_class"].items()}))
    for wn in PERIODS:
        log(f"variants {wn}:", json.dumps(r["variants"][wn]))
    log("comparison with Table 5.4:", json.dumps(r["comparison_with_table_5_4"]))
    log("proposed catalog:", json.dumps(r["proposed_catalog"]["tiers"]))
    log("catalog entries:", json.dumps(r["proposed_catalog"]["entries"]))


if __name__ == "__main__":
    sys.exit(main())
