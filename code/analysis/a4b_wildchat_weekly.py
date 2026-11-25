"""Regional hour-of-week demand profiles and region x tier request shares from WildChat-4.8M (MS0).

Design §5.3.3-5.3.4: the regional borrower (o, j) has demand d_oj(t) = Gamma * r_oj * p_o(hw(t)) * xi(t), where
  p_o(hw)  normalized hour-of-week profile of region o in UTC (mean 1 over the 168 hours of the week),
  r_oj     request share of region o and tier j (joint over the 5 regions and the mapped tiers, sums to 1).
hw = 24 * dayofweek + hour, Monday 00:00 UTC = 0 (pandas dayofweek convention, as in a4).

Base definitions follow a4_timezone_wildchat.py: one request = one conversation (row), placed at its
top-level `timestamp` (naive, read as UTC), rows with a null `country` dropped, and a profile is the count per
hour of the week summed over a window, divided by its mean over the 168 hours. The script reproduces a4's
stored 24-h profiles (per country, and per region rebuilt from a4's country profiles and counts) as a check.

Tier map (design Table 5.5; decision Q30 (b), 2026-10-16), applied to the model families of the dataset card:
gpt-3.5-turbo, gpt-4.1-mini, o1-mini -> M; gpt-4, gpt-4-turbo, gpt-4o, o1-preview -> L, except that gpt-4o-mini,
which the card counts in its gpt-4o family, goes to M like the other mini models (default map). The card's map
(gpt-4o-mini in L with its family) is the swept alternative ("card" map).

Diagnostics:
- counts per region and hour of the week (sparse cells), coverage gaps and an exposure-corrected profile;
- stability: correlation of the profiles of the two halves (split at the median request) of each window;
- whether the country label still separates regions: per month, the total-variation distance between each
  region's conversation-language mix and the pooled mix of the 5 regions;
- heavy users: share of a region's conversations from its 10 busiest hashed IPs and from its busiest 1%;
- variants: the whole trace or only the months before EARLY_END, counting conversations or user-hours
  (distinct hashed IPs per region and calendar hour, which caps each user at one per hour);
- a separable smoother for sparse cells: p(d, h) = (mean of day d) x (24-h profile at h);
- a profile built from assistant turns at their own timestamps, and a check that the naive timestamps are UTC
  (against the Unix-epoch `created` field of the assistant turns).

Borrower model (decision Q30 (a), (b), 2026-10-16): the default is the early window (before EARLY_END), with
p_o counted in user-hours and smoothed by the separable form, and r_oj counted in conversations of the same window
under the default tier map. Each named borrower model (`borrower_model.<name>`, BORROWER_MODELS) pairs p_o and r_oj
from one window under one tier map: "early" is the default; two sensitivity variants follow. "early_card_map"
changes one choice (the card's tier map); "full" changes the window, unit and profile together (the whole trace in
conversations, raw profile, as in a4). The
top-level p_o_hour_of_week_utc, r_oj and counts_region_tier_hour_of_week are those of the default, so a consumer
that reads the top level cannot combine a profile from one window with shares from another, or two tier maps.
"""
import glob
import json
import os
import re

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq

from common import DATA, OUT, save_json

REGIONS = {  # design §5.3.4
    "north_america": ["United States"],
    "europe": ["Russia", "Germany", "United Kingdom", "France"],
    "east_asia": ["China", "Japan", "Hong Kong", "South Korea"],
    "south_southeast_asia": ["India", "Vietnam"],
    "south_america": ["Brazil"],
}
COUNTRY_REGION = {c: o for o, cs in REGIONS.items() for c in cs}
REG = list(REGIONS)
TIER_CARD = {"gpt-3.5-turbo": "M", "gpt-4.1-mini": "M", "o1-mini": "M",  # card families, design Table 5.5
             "gpt-4": "L", "gpt-4-turbo": "L", "gpt-4o": "L", "o1-preview": "L"}
# default map (decision Q30 (b), 2026-10-16): model variants (version suffix removed) that leave their card family
TIER_OVERRIDE = {"gpt-4o-mini": "M"}
VERSION_SUFFIX = r"-\d{4}(-\d{2}-\d{2})?$|-\d{4}-preview$"
TIERS = ["M", "L"]
# family sizes stated on the dataset card (literature/sources/dataset-wildchat-4.8m.md)
CARD_FAMILY_COUNTS = {"gpt-4o": 1539780, "gpt-3.5-turbo": 688900, "gpt-4.1-mini": 634037, "gpt-4": 202915,
                      "o1-mini": 58529, "o1-preview": 53307, "gpt-4-turbo": 22392}
# Before EARLY_END every month has monthly mean TV >= 0.328 (label_check_language_tv_by_month); from 2024-10 on the
# series is unstable (0.06-0.50) after a 4x volume jump in 2024-10, so the country label does not reliably
# separate regions there (summary in label_check_summary).
EARLY_END = "2024-10-01"
# Named borrower models: each takes p_o and r_oj from one window under one tier map, so the borrower model never
# mixes windows or maps. "early" is the default (decision Q30 (a), (b), 2026-10-16): the whole-trace profile is
# unstable and the country label stops separating regions reliably from EARLY_END on (label_check_summary), and the
# separable smoother handles the sparse cells of the early window. The others are sensitivity variants that each
# change one choice of the default: "full" the window, unit and profile (whole trace in conversations, raw profile,
# as a4); "early_card_map" the tier map (gpt-4o-mini in L, the card's family map).
DEFAULT_WINDOW = "early"
BORROWER_MODELS = {
    "early": {"window": "early", "p_o_unit": "user_hours", "p_o_profile": "p_o_separable_utc",
              "r_oj_unit": "conversations", "tier_map": "default", "role": "default"},
    "full": {"window": "full", "p_o_unit": "conversations", "p_o_profile": "p_o_hour_of_week_utc",
             "r_oj_unit": "conversations", "tier_map": "default", "role": "sensitivity: whole trace in conversations, raw profile"},
    "early_card_map": {"window": "early", "p_o_unit": "user_hours", "p_o_profile": "p_o_separable_utc",
                       "r_oj_unit": "conversations", "tier_map": "card",
                       "role": "sensitivity: card tier map (gpt-4o-mini in L)"},
}
assert BORROWER_MODELS[DEFAULT_WINDOW]["window"] == DEFAULT_WINDOW
H = 168


def family(model):
    """Card model family of a versioned model string (prefix rules; checked against CARD_FAMILY_COUNTS)."""
    for p in ("gpt-4o", "gpt-4.1-mini", "gpt-4-turbo", "gpt-3.5-turbo", "o1-mini", "o1-preview"):
        if model.startswith(p):
            return p
    if model == "gpt-4" or model.startswith("gpt-4-"):
        return "gpt-4"
    return None


def hour_of_week(hour_idx):
    """hour_idx = whole hours since 1970-01-01 00:00 (a Thursday) -> 24 * dayofweek + hour, Monday 0."""
    return ((hour_idx // 24 + 3) % 7) * 24 + hour_idx % 24


def to_ts(hour_idx):
    return str(pd.Timestamp(int(hour_idx) * 3600, unit="s"))


def read():
    """One pass over the trace with column projection, one row group at a time.

    Returns aggregates only: conversations and turns by (country, model, calendar hour); for the 5 regions,
    one row per conversation with (region, hashed-IP hash, hour) as integers, languages by (region, month),
    assistant turns by (region, hour of week); and the UTC-check arrays.
    """
    files = sorted(glob.glob(f"{DATA}/wildchat-4.8m/train-*.parquet"))
    cols = ["timestamp", "country", "model", "turn", "language", "hashed_ip",
            "conversation.list.element.timestamp", "conversation.list.element.created"]
    ccode = {c: i for i, o in enumerate(REG) for c in REGIONS[o]}
    parts, users, langs, turn_parts, lag_s, last_eq = [], [], [], [], [], [0, 0]
    for f in files:
        pf = pq.ParquetFile(f)
        rows, urows, lrows, trows = [], [], [], []
        for g in range(pf.num_row_groups):
            t = pf.read_row_group(g, columns=cols)
            ts_us = t["timestamp"].to_numpy()
            ts = ts_us.astype("datetime64[s]").astype(np.int64)
            country = t["country"].to_numpy()
            rows.append(pd.DataFrame({"country": country, "model": t["model"].to_numpy(),
                                      "hour": ts // 3600, "turns": t["turn"].to_numpy()}))
            region = pd.Series(country).map(ccode).to_numpy(dtype=float)
            ok = ~np.isnan(region)
            rc = region[ok].astype(np.int8)
            urows.append(pd.DataFrame({"r": rc, "ip": pd.util.hash_array(t["hashed_ip"].to_numpy()[ok]),
                                       "hour": (ts[ok] // 3600).astype(np.int32)}))
            lrows.append(pd.DataFrame({"r": rc, "month": ts_us[ok].astype("datetime64[M]").astype(np.int32),
                                       "lang": t["language"].to_numpy()[ok]}))
            conv = t["conversation"].combine_chunks()
            flat = pc.list_flatten(conv)
            parent = pc.list_parent_indices(conv).to_numpy()
            el_ts = flat.field("timestamp")
            okt = el_ts.is_valid().to_numpy(zero_copy_only=False)
            el_s = el_ts.to_numpy(zero_copy_only=False)[okt].astype("datetime64[s]").astype(np.int64)
            par = parent[okt]
            keep = ok[par]
            trows.append(pd.DataFrame({"r": region[par][keep].astype(np.int8), "hw": hour_of_week(el_s[keep] // 3600)}))
            # UTC check: top-level timestamp vs the last assistant turn (its timestamp and its epoch `created`)
            last_ts = np.full(len(ts), -1, np.int64)
            np.maximum.at(last_ts, par, el_s)
            cr = flat.field("created")
            okc = cr.is_valid().to_numpy(zero_copy_only=False)
            last_cr = np.full(len(ts), -1, np.int64)
            np.maximum.at(last_cr, parent[okc], cr.to_numpy(zero_copy_only=False)[okc].astype(np.int64))
            has = last_cr >= 0
            lag_s.append(ts[has] - last_cr[has])
            last_eq[0] += int((last_ts[last_ts >= 0] == ts[last_ts >= 0]).sum())
            last_eq[1] += int((last_ts >= 0).sum())
        d = pd.concat(rows)
        d["country"] = d["country"].fillna("<null>")
        d["n"] = 1
        parts.append(d.groupby(["country", "model", "hour"], as_index=False)[["n", "turns"]].sum())
        users.append(pd.concat(urows))
        langs.append(pd.concat(lrows).groupby(["r", "month", "lang"]).size().rename("n").reset_index())
        turn_parts.append(pd.concat(trows).groupby(["r", "hw"]).size().rename("n").reset_index())
        print(os.path.basename(f), len(d))
    agg = pd.concat(parts).groupby(["country", "model", "hour"], as_index=False)[["n", "turns"]].sum()
    users = pd.concat(users, ignore_index=True)
    users["region"] = np.array(REG)[users.r.to_numpy()]
    langs = pd.concat(langs).groupby(["r", "month", "lang"], as_index=False).n.sum()
    turns_hw = pd.concat(turn_parts).groupby(["r", "hw"], as_index=False).n.sum()
    turns_hw["region"] = np.array(REG)[turns_hw.r.to_numpy()]
    return agg, users, langs, turns_hw, np.concatenate(lag_s), last_eq


def by_hw(df, key, keys, val="n"):
    """Matrix len(keys) x 168 of `val` summed by key and hour of week."""
    m = df.groupby([key, "hw"])[val].sum().unstack(fill_value=0).reindex(index=keys, columns=range(H), fill_value=0)
    return m.to_numpy(dtype=float)


def normalize_rows(M):
    return M / M.mean(axis=1, keepdims=True)


def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])


def fold(P):
    """Hour-of-week profiles (rows) -> 24-h profiles, the mean over the 7 days."""
    return P.reshape(len(P), 7, 24).mean(1)


def pooling(P, w):
    """Sum of regional peaks over the peak of the sum; equal mean load and weights w."""
    return {"equal_mean": float(P.max(1).sum() / P.sum(0).max()),
            "share_weighted": float((w * P.max(1)).sum() / (w[:, None] * P).sum(0).max())}


def variant(df, active, h0, window):
    """Profiles, counts and diagnostics of one variant; df has region, hour, hw, n (one window).

    active[k] says whether calendar hour h0 + k has any conversation in the whole trace (exposure).
    """
    R = by_hw(df, "region", REG)
    P = normalize_rows(R)
    h = df.sort_values("hour")
    cut = int(h.hour.to_numpy()[np.searchsorted(h.n.cumsum().to_numpy(), h.n.sum() / 2)])
    P1, P2 = (normalize_rows(by_hw(df[m], "region", REG)) for m in (df.hour < cut, df.hour >= cut))
    F, F1, F2 = fold(P), fold(P1), fold(P2)
    # separable smoother for sparse cells: day-of-week factor x 24-h profile (31 parameters instead of 168)
    S = (P.reshape(len(P), 7, 24).mean(2)[:, :, None] * F[:, None, :]).reshape(len(P), H)
    S1 = (P1.reshape(len(P), 7, 24).mean(2)[:, :, None] * F1[:, None, :]).reshape(len(P), H)
    S2 = (P2.reshape(len(P), 7, 24).mean(2)[:, :, None] * F2[:, None, :]).reshape(len(P), H)
    span = np.arange(window[0], window[1])
    expo = np.bincount(hour_of_week(span[active[span - h0]]), minlength=H)
    Pexp = normalize_rows(R / expo)
    stats = {}
    for i, o in enumerate(REG):
        n = R[i]
        stats[o] = {
            "total": int(n.sum()), "peak_hw": int(P[i].argmax()), "trough_hw": int(P[i].argmin()),
            "weekly_peak": float(P[i].max()), "weekly_trough": float(P[i].min()),
            "weekly_peak_to_trough": float(P[i].max() / P[i].min()),
            "peak_hour_utc_folded": int(F[i].argmax()), "daily_peak_to_trough_folded": float(F[i].max() / F[i].min()),
            "weekend_to_weekday_mean_utc": float(P[i, 120:].mean() / P[i, :120].mean()),
            "min_cell": int(n.min()), "median_cell": float(np.median(n)), "max_cell": int(n.max()),
            "cells_below_30": int((n < 30).sum()), "cells_below_100": int((n < 100).sum()),
            "cells_below_1000": int((n < 1000).sum()), "max_poisson_rel_se": float(1 / np.sqrt(max(n.min(), 1))),
            "split_half_corr_weekly": corr(P1[i], P2[i]), "split_half_corr_daily": corr(F1[i], F2[i]),
            "split_half_corr_separable": corr(S1[i], S2[i]), "separable_corr_with_weekly": corr(S[i], P[i]),
            "split_half_max_abs_diff_weekly": float(np.abs(P1[i] - P2[i]).max()),
            "exposure_corrected_max_rel_diff": float(np.abs(Pexp[i] / P[i] - 1).max()),
        }
    return R, P, {
        "window_utc": [to_ts(window[0]), to_ts(window[1])], "split_half_cut_utc": to_ts(cut),
        "p_o_hour_of_week_utc": {o: P[i].round(5).tolist() for i, o in enumerate(REG)},
        "p_o_daily_folded_utc": {o: F[i].round(5).tolist() for i, o in enumerate(REG)},
        "p_o_separable_utc": {o: S[i].round(5).tolist() for i, o in enumerate(REG)},
        "counts_hour_of_week": {o: R[i].astype(int).tolist() for i, o in enumerate(REG)},
        "exposure_hours_per_hw_min_max": [int(expo.min()), int(expo.max())],
        "region_stats": stats, "pooling_gain": pooling(P, R.sum(1) / R.sum()),
        "pooling_gain_separable": pooling(S, R.sum(1) / R.sum()),
    }


def shares(df, val="n", tier_col="tier"):
    m = df[df[tier_col].notna()].groupby(["region", tier_col])[val].sum().unstack(fill_value=0)
    m = m.reindex(index=REG, columns=TIERS, fill_value=0).astype(float)
    joint = m / m.to_numpy().sum()
    return {"r_oj": {o: {j: float(joint.loc[o, j]) for j in TIERS} for o in REG},
            "region_share": {o: float(joint.loc[o].sum()) for o in REG},
            "tier_share_within_region": {o: {j: float(m.loc[o, j] / m.loc[o].sum()) for j in TIERS} for o in REG},
            "tier_share_all_regions": {j: float(m[j].sum() / m.to_numpy().sum()) for j in TIERS},
            "counts": {o: {j: int(m.loc[o, j]) for j in TIERS} for o in REG}}


def heavy_users(u):
    out = {}
    for o, g in u.groupby("region"):
        per = g.groupby("ip").size().sort_values(ascending=False).to_numpy()
        k = max(1, len(per) // 100)
        out[o] = {"conversations": int(per.sum()), "distinct_ips": int(len(per)),
                  "share_top10_ips": float(per[:10].sum() / per.sum()), "share_top1pct_ips": float(per[:k].sum() / per.sum())}
    return out


def main():
    agg, users, langs, turns_hw, lag_s, last_eq = read()
    a4 = json.load(open(f"{OUT}/a4_timezone_wildchat.json"))
    agg["hw"] = hour_of_week(agg.hour.to_numpy())
    agg["family"] = agg.model.map(family)
    agg["variant"] = agg.model.map({m: re.sub(VERSION_SUFFIX, "", m) for m in agg.model.unique()})
    agg["tier_card"] = agg.family.map(TIER_CARD)
    agg["tier"] = agg.variant.map(TIER_OVERRIDE).fillna(agg.tier_card)  # default map
    agg["region"] = agg.country.map(COUNTRY_REGION)
    users["hw"] = hour_of_week(users.hour.to_numpy().astype(np.int64))
    early_end = int(np.datetime64(EARLY_END, "h").astype(np.int64))

    # ---- 1. reproduce a4: top-12 countries, their counts and 24-h profiles
    known = agg[agg.country != "<null>"]
    tot = known.groupby("country").n.sum().sort_values(ascending=False)
    top = tot.index[:12].tolist()
    C = normalize_rows(by_hw(known, "country", top))
    day_c = dict(zip(top, fold(C)))
    # a4's 12-country pooling gain (equal mean load), whole trace and the early window
    C_early = normalize_rows(by_hw(known[known.hour < early_end], "country", top))
    pool12 = {"full": pooling(C, np.ones(12))["equal_mean"], "early": pooling(C_early, np.ones(12))["equal_mean"],
              "a4_pooling_gain_all_top": a4["pooling_gain_all_top"]}
    a4_day = {c: np.array(v) for c, v in a4["daily_profile_utc"].items()}
    repro = {
        "countries_top_equal": top == a4["countries_top"],
        "requests_by_country_equal": {c: int(tot[c]) for c in top} == a4["requests_by_country"],
        "country_daily_max_abs_diff": float(max(np.abs(day_c[c] - a4_day[c]).max() for c in top)),
        "country_daily_max_abs_diff_rounded_3dp": float(max(np.abs(day_c[c].round(3) - a4_day[c]).max() for c in top)),
    }

    # ---- 2. coverage and gaps (all rows)
    allh = agg.groupby("hour").n.sum()
    h0, h1 = int(allh.index.min()), int(allh.index.max()) + 1
    active = np.zeros(h1 - h0, bool)
    active[allh.index.to_numpy() - h0] = True
    edges = np.diff(np.concatenate([[0], (~active).astype(np.int8), [0]]))
    gap_len = np.where(edges == -1)[0] - np.where(edges == 1)[0]

    # ---- 3. profile variants: window x unit
    reg = agg[agg.region.notna()]
    uh = users.drop_duplicates(["r", "ip", "hour"]).groupby(["region", "hour", "hw"], as_index=False).size()
    uh = uh.rename(columns={"size": "n"})
    windows = {"full": (h0, h1), "early": (h0, early_end)}
    variants, mats = {}, {}
    for wname, (a, b) in windows.items():
        for unit, df in (("conversations", reg), ("user_hours", uh)):
            sel = df[(df.hour >= a) & (df.hour < b)]
            R, P, v = variant(sel, active, h0, (a, b))
            variants[f"{wname}_{unit}"] = v
            mats[f"{wname}_{unit}"] = (R, P)
    R, P = mats["full_conversations"]

    # a4 stores sum_d g_c(d,h)/mean(g_c) / 7 with mean(g_c) = N_c/168, so a region's hour-of-day count is
    # sum_c day_c(h) * N_c / 24; compare its normalized form with p_o folded over the 7 days.
    rebuilt = normalize_rows(np.array([sum(a4_day[c] * a4["requests_by_country"][c] / 24 for c in REGIONS[o])
                                       for o in REG]))
    repro["region_daily_max_abs_diff_vs_a4_rebuilt"] = {o: float(np.abs(fold(P)[i] - rebuilt[i]).max())
                                                       for i, o in enumerate(REG)}
    hod = normalize_rows(reg.assign(hod=reg.hw % 24).groupby(["region", "hod"]).n.sum().unstack()
                         .reindex(REG).to_numpy(float))
    repro["region_fold_vs_hour_of_day_counts_max_abs_diff"] = float(np.abs(fold(P) - hod).max())

    # ---- 4. turn-level profile (assistant turns at their own timestamps, whole trace)
    PT = normalize_rows(by_hw(turns_hw, "region", REG))
    turn_check = {o: {"assistant_turns": int(turns_hw[turns_hw.region == o].n.sum()),
                      "turn_column_sum": int(reg[reg.region == o].turns.sum()),
                      "corr_with_conversation_profile": corr(P[i], PT[i]),
                      "max_abs_diff": float(np.abs(P[i] - PT[i]).max())} for i, o in enumerate(REG)}

    # ---- 5. does the country label still separate regions? language mix per month
    lm = langs.groupby(["month", "r", "lang"]).n.sum()
    label = {}
    for mo in sorted(langs.month.unique()):
        x = lm.loc[mo].unstack(fill_value=0)
        pooled = x.sum(axis=0) / x.to_numpy().sum()
        tv = {REG[r]: float(0.5 * np.abs(x.loc[r] / x.loc[r].sum() - pooled).sum()) for r in x.index}
        key = str(np.datetime64(int(mo), "M"))
        label[key] = {"conversations": int(x.to_numpy().sum()), "tv_to_pooled": tv,
                      "mean_tv": float(np.mean(list(tv.values())))}
    top_lang = {}
    for wname, m in (("early", langs.month < np.datetime64(EARLY_END, "M").astype(int)),
                     ("late", langs.month >= np.datetime64(EARLY_END, "M").astype(int))):
        s = langs[m].groupby(["r", "lang"]).n.sum()
        top_lang[wname] = {REG[r]: {k: float(v) for k, v in (s.loc[r] / s.loc[r].sum()).nlargest(4).items()}
                           for r in s.index.get_level_values(0).unique()}

    # ---- 6. tier maps and request shares r_oj (default map: column tier; card map: column tier_card)
    fam_counts = agg.groupby("family").n.sum()
    unmapped = agg[agg.tier.isna() | agg.tier_card.isna()].groupby("model").n.sum()
    reg = reg.assign(year=pd.to_datetime(reg.hour * 3600, unit="s").dt.year)
    share_out = {}
    for wname, (a, b) in windows.items():
        w = reg[(reg.hour >= a) & (reg.hour < b)]
        mc = w.groupby(["model", "region"]).n.sum().unstack(fill_value=0).reindex(columns=REG, fill_value=0)
        share_out[wname] = {
            "conversations": shares(w), "turn_weighted": shares(w, val="turns"),
            "card_tier_map": shares(w, tier_col="tier_card"),
            "model_counts_by_region": {m: {o: int(v) for o, v in row.items()} for m, row in mc.iterrows()},
        }
    by_year = {}
    for y, g in reg.groupby("year"):
        s, sc = shares(g), shares(g, tier_col="tier_card")
        by_year[str(y)] = {"conversations": int(g.n.sum()), "region_share": s["region_share"],
                           "tier_share_within_region": s["tier_share_within_region"],
                           "tier_share_within_region_card_tier_map": sc["tier_share_within_region"]}
    # region x tier x hour-of-week counts (conversations) of the default window under the default tier map
    a, b = windows[DEFAULT_WINDOW]
    rw = reg[(reg.hour >= a) & (reg.hour < b)]
    RT = {o: {j: rw[(rw.region == o) & (rw.tier == j)].groupby("hw").n.sum()
              .reindex(range(H), fill_value=0).astype(int).tolist() for j in TIERS} for o in REG}

    lag_q = np.percentile(lag_s, [0.1, 1, 50, 99, 99.9])
    # named borrower models: p_o and r_oj from the same window under one tier map, with their units
    borrower = {}
    for name, spec in BORROWER_MODELS.items():
        wname, pu, ru = spec["window"], spec["p_o_unit"], spec["r_oj_unit"]
        assert ru == "conversations"
        v = variants[f"{wname}_{pu}"]
        s = share_out[wname]["conversations" if spec["tier_map"] == "default" else "card_tier_map"]
        borrower[name] = {"role": spec["role"], "window": wname, "window_utc": v["window_utc"],
                          "p_o_unit": pu, "p_o_variant": f"{wname}_{pu}", "p_o_profile": spec["p_o_profile"],
                          "p_o": v[spec["p_o_profile"]],
                          "p_o_hour_of_week_utc_raw": v["p_o_hour_of_week_utc"],
                          "p_o_separable_utc": v["p_o_separable_utc"],
                          "r_oj_unit": ru, "tier_map": spec["tier_map"], "r_oj": s["r_oj"],
                          "region_share": s["region_share"], "tier_share_all_regions": s["tier_share_all_regions"],
                          "tier_share_within_region": s["tier_share_within_region"]}
    dflt = borrower[DEFAULT_WINDOW]
    # label check summary: monthly mean TV before and from EARLY_END, and the volume jump at EARLY_END
    em = str(np.datetime64(EARLY_END, "M"))
    before = {k: v for k, v in label.items() if k < em}
    after = {k: v for k, v in label.items() if k >= em}
    prev = max(before)
    label_summary = {
        "early_end": EARLY_END,
        "months_before": len(before), "min_mean_tv_before": min(v["mean_tv"] for v in before.values()),
        "months_from": len(after), "mean_tv_from_min_max": [min(v["mean_tv"] for v in after.values()),
                                                           max(v["mean_tv"] for v in after.values())],
        "argmax_month_from": max(after, key=lambda k: after[k]["mean_tv"]),
        "conversations_month_before_and_first_month": [before[prev]["conversations"], after[em]["conversations"]],
        "volume_jump": after[em]["conversations"] / before[prev]["conversations"],
        "reading": "every month before EARLY_END separates regions (mean TV to the pooled language mix at least "
                   "min_mean_tv_before); from EARLY_END on the monthly mean TV is unstable (mean_tv_from_min_max), "
                   "after the volume jump, so the country label does not reliably separate regions there"}
    save_json("a4b_wildchat_weekly.json", {
        "definitions": {
            "hw": "24*dayofweek + hour of the UTC timestamp, Monday 00:00 = 0",
            "profile": "count per hour of week summed over the window, divided by its mean over the 168 hours",
            "conversations": "one conversation (row) at its top-level timestamp (= its last assistant turn), as in a4",
            "user_hours": "distinct hashed IPs per region and calendar hour, summed by hour of week",
            "r_oj": "share of conversations of region o and tier j among all mapped conversations of the 5 regions",
            "p_o_separable_utc": "separable smoother: p(d, h) = (mean of day d) x (24-h profile at h), "
                                 "31 parameters instead of 168, for sparse hour-of-week cells",
            "windows": {"full": "whole trace", "early": f"before {EARLY_END} UTC"},
            "tier_maps": {"default": "card families, except gpt-4o-mini -> M like the other mini models",
                          "card": "card families, gpt-4o-mini in L with the gpt-4o family",
                          "rule": "default map: strip the version suffix from the model name; a variant in "
                                  "tier_map.variant_override takes that tier, every other model the tier of its card "
                                  "family in tier_map.family_map. Card map: the family map alone. gpt-4o-mini is "
                                  "never a family of its own, so the family map alone sends it to L"},
            "default": {"borrower_model": DEFAULT_WINDOW, "window": DEFAULT_WINDOW,
                        "p_o": dflt["p_o_variant"], "p_o_unit": dflt["p_o_unit"], "p_o_profile": dflt["p_o_profile"],
                        "r_oj_unit": dflt["r_oj_unit"], "tier_map": dflt["tier_map"],
                        "decided": "decision Q30 (a), (b), 2026-10-16 (design §7.7)",
                        "reason": "(a) the whole-trace profile is unstable (split-half correlation of the weekly "
                                  "profile in variants.full_conversations.region_stats) and the country label stops "
                                  "separating regions reliably from early_end on (label_check_summary); user-hours cap "
                                  "each hashed IP at one per hour against heavy users; the separable smoother handles "
                                  "the sparse cells of the early window; r_oj comes from the same window. (b) "
                                  "gpt-4o-mini goes to M like gpt-4.1-mini and o1-mini",
                        "note": "top-level p_o_hour_of_week_utc (= borrower_model.early.p_o), "
                                "counts_region_hour_of_week (the user-hour counts it is built from), r_oj and "
                                "counts_region_tier_hour_of_week (conversations) are those of this default; "
                                "borrower_model.<name> holds p_o and r_oj of each named model together. The top-level "
                                "p_o_hour_of_week_utc is the profile named by p_o_profile (the separable smoother), "
                                "not the raw hour-of-week profile, which is borrower_model.<name>."
                                "p_o_hour_of_week_utc_raw (= variants.<variant>.p_o_hour_of_week_utc). "
                                "rows_in_5_regions counts the whole trace; rows_in_5_regions_by_window gives each "
                                "window"},
            "sensitivity_variants": {n: {"borrower_model": n, "changes": BORROWER_MODELS[n]["role"]}
                                     for n in BORROWER_MODELS if n != DEFAULT_WINDOW},
            "regions": REGIONS, "region_order": REG, "tier_map": {"family_map": TIER_CARD, "variant_override": TIER_OVERRIDE},
            "tier_map_card": TIER_CARD,
        },
        "rows_total": int(agg.n.sum()), "rows_null_country": int(agg[agg.country == "<null>"].n.sum()),
        "rows_in_5_regions": int(R.sum()),
        "rows_in_5_regions_by_window": {wname: int(mats[f"{wname}_conversations"][0].sum()) for wname in windows},
        "p_o_hour_of_week_utc": dflt["p_o"],
        "p_o_unit": dflt["p_o_unit"],
        "p_o_profile": dflt["p_o_profile"],
        "counts_region_hour_of_week": variants[dflt["p_o_variant"]]["counts_hour_of_week"],
        "r_oj": dflt["r_oj"],
        "r_oj_unit": dflt["r_oj_unit"],
        "tier_map": dflt["tier_map"],
        "window": DEFAULT_WINDOW,
        "borrower_model": borrower,
        "variants": variants,
        "counts_region_tier_hour_of_week": RT,
        "shares": share_out,
        "shares_by_year": by_year,
        "tier_map_check": {
            "family_counts_all_rows": {k: int(v) for k, v in fam_counts.items()},
            "family_counts_equal_card": {k: int(v) for k, v in fam_counts.items()} == CARD_FAMILY_COUNTS,
            "unmapped_models": {k: int(v) for k, v in unmapped.items()},
            "gpt-4o-mini_all_rows": int(agg[agg.model.str.startswith("gpt-4o-mini")].n.sum()),
            "gpt-4o-mini_in_5_regions": int(reg[reg.variant == "gpt-4o-mini"].n.sum()),
            "gpt-4o-mini_in_5_regions_by_window": {wname: int(reg[(reg.variant == "gpt-4o-mini") & (reg.hour >= a)
                                                                  & (reg.hour < b)].n.sum())
                                                   for wname, (a, b) in windows.items()},
            "maps_differ_only_on_gpt-4o-mini": bool(set(reg[reg.tier != reg.tier_card].variant) == {"gpt-4o-mini"}),
        },
        "label_check_language_tv_by_month": label,
        "label_check_summary": label_summary,
        "top_languages": top_lang,
        "heavy_users": {"full": heavy_users(users),
                        "early": heavy_users(users[users.hour < early_end])},
        "pooling_gain_12_countries_equal_mean": pool12,
        "turn_profile_check": turn_check,
        "reproduce_a4": repro,
        "coverage": {
            "first_hour_utc": to_ts(h0), "last_hour_utc": to_ts(h1 - 1), "span_hours": int(len(active)),
            "hours_without_any_conversation": int((~active).sum()), "gaps_over_24h": int((gap_len > 24).sum()),
            "longest_gap_hours": int(gap_len.max()) if len(gap_len) else 0,
            "longest_gap_start_utc": to_ts(h0 + np.where(edges == 1)[0][gap_len.argmax()]) if len(gap_len) else None,
        },
        "utc_check": {
            "rows_with_created": int(len(lag_s)),
            "timestamp_minus_last_created_s_p0.1_1_50_99_99.9": [float(x) for x in lag_q],
            "share_abs_lag_le_120s": float((np.abs(lag_s) <= 120).mean()),
            "share_timestamp_equals_last_assistant_turn": last_eq[0] / last_eq[1],
        },
    })
    print("repro a4:", repro)
    for k, v in variants.items():
        print(k, v["pooling_gain"], "separable:", v["pooling_gain_separable"])
        for o, s in v["region_stats"].items():
            print(f"  {o:22s} n={s['total']:>8d} peak_hw={s['peak_hw']:>3d} p2t={s['weekly_peak_to_trough']:6.2f} "
                  f"min_cell={s['min_cell']:>5d} split_w={s['split_half_corr_weekly']:.3f} "
                  f"split_d={s['split_half_corr_daily']:.3f} split_sep={s['split_half_corr_separable']:.3f} "
                  f"sep_fit={s['separable_corr_with_weekly']:.3f}")
    for name, bm in borrower.items():
        print(f"borrower model {name} ({bm['role']}; p_o {bm['p_o_variant']} {bm['p_o_profile']}, r_oj "
              f"{bm['r_oj_unit']}, tier map {bm['tier_map']}): M share {bm['tier_share_all_regions']['M']:.4f}, "
              f"r_oj {bm['r_oj']}")
    print("label check:", {k: v for k, v in label_summary.items() if k != "reading"})
    print("pooling 12 countries:", pool12)


if __name__ == "__main__":
    main()
