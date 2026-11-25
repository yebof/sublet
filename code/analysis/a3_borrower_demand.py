"""Borrower-side demand: diurnal shape, burstiness and overflow episodes.

An overflow episode is a maximal run where demand exceeds own capacity C0 (set at a demand percentile).
Its length is the 'demand end time' x in the RRL primitive: how long a lease would be useful.
Sources: Azure LLM 2024 (1 week, code/conv), BurstGPT v2.0 (121 days), Azure LLM 2023 (1 hour) when present.
"""
import glob
import os

import numpy as np
import pandas as pd

from common import DATA, OUT, save_json, runs, diurnal_profile

SLOT_S = 60


def overflow_stats(x, slot_min):
    out = {}
    for p in (50, 75, 90, 95):
        C0 = np.percentile(x, p)
        lens, cens = runs(x > C0)
        L = lens * slot_min
        if len(L) == 0:
            continue
        # gaps between episodes (how long the lease would sit idle if kept)
        gaps, _ = runs(x <= C0)
        out[f"C0_at_P{p}"] = {
            "episodes_per_day": float(len(L) / (len(x) * slot_min / 1440)),
            "episode_min_quantiles_p10_25_50_75_90": [float(v) for v in np.percentile(L, [10, 25, 50, 75, 90])],
            "share_overflow_time_in_episodes_ge_min": {
                str(t): float(L[L >= t].sum() / L.sum()) for t in (15, 30, 60, 180)},
            "gap_min_quantiles_p10_50_90": [float(v) for v in np.percentile(gaps * slot_min, [10, 50, 90])] if len(gaps) else None,
            "peak_over_C0": float(x.max() / C0),
        }
    return out


def series_stats(name, ts_sec, tokens, slot_s=SLOT_S):
    t0 = ts_sec.min()
    idx = ((ts_sec - t0) // slot_s).astype(np.int64)
    n = int(idx.max()) + 1
    req = np.bincount(idx, minlength=n).astype(float)
    tok = np.bincount(idx, weights=tokens, minlength=n)
    spd = int(86400 // slot_s)
    r = {"name": name, "days": n * slot_s / 86400, "requests": int(len(ts_sec)),
         "tokens_per_min_mean": float(tok.mean() * 60 / slot_s),
         "peak_to_mean_1min": float(tok.max() / tok.mean()),
         "p99_to_mean_1min": float(np.percentile(tok, 99) / tok.mean())}
    if n >= 2 * spd:
        b = 900 // slot_s  # diurnal shape on 15-min totals; 1-min bins are dominated by noise
        q = tok[: n // b * b].reshape(-1, b).sum(1)
        r["diurnal_tokens_15min"] = diurnal_profile(q, 96)
    # 15-min smoothed series is what capacity decisions see (replicas take minutes to start)
    k = max(1, 900 // slot_s)
    sm = np.convolve(tok, np.ones(k) / k, mode="valid")
    r["peak_to_mean_15min"] = float(sm.max() / sm.mean())
    r["overflow_15min_smoothed"] = overflow_stats(sm, slot_s / 60)
    hourly = tok[: n // 60 * 60].reshape(-1, 60).sum(1) if slot_s == 60 else None
    minute_series[name] = tok if slot_s == 60 else None
    return r, hourly


result = {}
hourly_curves = {}
minute_series = {}

for kind in ("code", "conv"):
    f = f"{DATA}/azure-llm-2024/AzureLLMInferenceTrace_{kind}_1week.csv"
    if os.path.exists(f + ".done"):
        # Memory (run_all.sh runs a3 in a 3 GB scope): parse the CSV in chunks and keep only the parsed timestamps
        # and the token columns; same values as parsing the whole column at once
        ts, ctx, gen = [], [], []
        for c in pd.read_csv(f, usecols=["TIMESTAMP", "ContextTokens", "GeneratedTokens"], chunksize=2_000_000):
            ts.append(pd.to_datetime(c.TIMESTAMP, format="mixed"))
            ctx.append(c.ContextTokens)
            gen.append(c.GeneratedTokens)
            del c
        df = pd.DataFrame({"ContextTokens": pd.concat(ctx, ignore_index=True),
                           "GeneratedTokens": pd.concat(gen, ignore_index=True)})
        ts = pd.concat(ts, ignore_index=True)
        del ctx, gen
        ts = (ts - ts.min()).dt.total_seconds()  # resolution-agnostic (pandas 3 defaults to us)
        r, h = series_stats(f"azure2024_{kind}", ts.values, (df.ContextTokens + df.GeneratedTokens).values)
        r["output_tokens_quantiles_p50_90_99"] = [float(v) for v in np.percentile(df.GeneratedTokens, [50, 90, 99])]
        r["input_tokens_quantiles_p50_90_99"] = [float(v) for v in np.percentile(df.ContextTokens, [50, 90, 99])]
        result[f"azure2024_{kind}"] = r
        hourly_curves[f"azure2024_{kind}"] = h.tolist()
        print(kind, r["days"], r["peak_to_mean_15min"])

parts = sorted(glob.glob(f"{DATA}/burstgpt/BurstGPT_[0-9].csv"))
parts = [p for p in parts if os.path.exists(p + ".done")]
for p in parts:
    df = pd.read_csv(p)
    df = df[df["Response tokens"] > 0]
    name = "burstgpt_" + os.path.basename(p).split("_")[1].split(".")[0]
    r, h = series_stats(name, df.Timestamp.values.astype(float), df["Total tokens"].values.astype(float))
    # weekly pattern: daily totals
    days = (df.Timestamp // 86400).astype(int)
    daily = np.bincount(days, weights=df["Total tokens"])
    r["daily_total_cv"] = float(daily.std() / daily.mean())
    wk = daily[: len(daily) // 7 * 7].reshape(-1, 7).mean(0)
    r["weekly_profile_peak_to_trough"] = float(wk.max() / wk.min())
    for model, g in df.groupby("Model"):
        r.setdefault("requests_by_model", {})[model] = int(len(g))
    result[name] = r
    hourly_curves[name] = h.tolist()
    print(name, r["days"], r.get("diurnal_tokens_15min"))

save_json("a3_borrower_demand.json", result)
save_json("a3_hourly_curves.json", hourly_curves)
np.savez_compressed(os.path.join(OUT, "a3_minute_series.npz"), **{k: v for k, v in minute_series.items() if v is not None})
