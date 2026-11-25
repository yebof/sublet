"""Time-zone offset between regional providers, from WildChat-4.8M conversation timestamps (UTC) by country.

Questions: are regional demand curves anti-correlated? How much peak capacity would pooling across regions save?
Pooling gain = sum of regional peaks / peak of the summed demand (hourly, average weekday profile).
"""
import glob

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from common import DATA, save_json

files = sorted(glob.glob(f"{DATA}/wildchat-4.8m/train-*.parquet"))
parts = []
for f in files:
    t = pq.read_table(f, columns=["timestamp", "country"]).to_pandas()
    t = t[t.country.notna()]
    t["h"] = t.timestamp.dt.floor("h")
    parts.append(t.groupby(["country", "h"]).size().rename("n").reset_index())
df = pd.concat(parts).groupby(["country", "h"]).n.sum().reset_index()
tot = df.groupby("country").n.sum().sort_values(ascending=False)
top = tot.index[:12].tolist()
print(tot.head(15))

# average hour-of-week profile (UTC) per country, normalised to mean 1
df["how"] = df.h.dt.dayofweek * 24 + df.h.dt.hour
df["week"] = df.h.dt.isocalendar().week.astype(int) + 100 * df.h.dt.year
prof = {}
for c in top:
    g = df[df.country == c].groupby("how").n.sum().reindex(range(168), fill_value=0).values.astype(float)
    prof[c] = g / g.mean()

M = np.vstack([prof[c] for c in top])
corr = np.corrcoef(M)
day = {c: prof[c].reshape(7, 24).mean(0) for c in top}
peak_hour_utc = {c: int(np.argmax(day[c])) for c in top}
p2t = {c: float(day[c].max() / max(day[c].min(), 1e-9)) for c in top}

# pooling gain for pairs and for all, each region scaled to equal mean load
pair_gain = {}
for i, a in enumerate(top):
    for b in top[i + 1:]:
        s = prof[a] + prof[b]
        pair_gain[f"{a}|{b}"] = float((prof[a].max() + prof[b].max()) / s.max())
all_gain = float(sum(prof[c].max() for c in top) / M.sum(0).max())
best = sorted(pair_gain.items(), key=lambda kv: -kv[1])[:10]

save_json("a4_timezone_wildchat.json", {
    "countries_top": top, "requests_by_country": {c: int(tot[c]) for c in top},
    "peak_hour_utc": peak_hour_utc, "daily_peak_to_trough": p2t,
    "hour_of_week_corr": {"countries": top, "corr": corr.round(3).tolist()},
    "pooling_gain_all_top": all_gain, "pooling_gain_best_pairs": best,
    "daily_profile_utc": {c: day[c].round(3).tolist() for c in top},
})
