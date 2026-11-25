"""Shared helpers for trace analysis: lender idle windows, reclaim events, predictability."""
import json
import os

import numpy as np

DATA = "/mnt/data/datasets"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FIG = os.path.join(HERE, "fig")
os.makedirs(OUT, exist_ok=True)
os.makedirs(FIG, exist_ok=True)


def save_json(name, obj):
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=float)
    print("wrote", path)


def occupancy(starts, durations, weights, slot, n_slots):
    """Sum of `weights` active in each slot, intervals [start, start+duration) in seconds."""
    a = np.clip((starts // slot).astype(np.int64), 0, n_slots)
    b = np.clip(((starts + durations) // slot).astype(np.int64), 0, n_slots)
    diff = np.zeros(n_slots + 1)
    np.add.at(diff, a, weights)
    np.add.at(diff, b, -weights)
    return np.cumsum(diff)[:n_slots]


def runs(mask):
    """Lengths (in slots) of maximal True runs, excluding runs touching either boundary (censored)."""
    m = np.concatenate([[False], mask, [False]]).astype(np.int8)
    d = np.diff(m)
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    lens = en - st
    keep = (st > 0) & (en < len(mask))
    return lens[keep], lens[~keep]


def window_stats(s, L, slot_min, thresholds_min=(5, 15, 30, 60, 180, 360)):
    """Idle windows where spare capacity s_t >= L.

    Returns window-length quantiles and the share of lendable unit-time that lies in windows
    of at least x minutes (what a borrower with break-even lease length x could actually use).
    """
    lens, cens = runs(s >= L)
    allw = np.concatenate([lens, cens]) * slot_min
    res = {"L": float(L), "n_windows": int(len(lens)), "n_censored": int(len(cens)),
           "frac_time_available": float((s >= L).mean())}
    if len(lens):
        q = np.percentile(lens * slot_min, [10, 25, 50, 75, 90])
        res["window_min_quantiles_p10_25_50_75_90"] = [float(x) for x in q]
    tot = allw.sum()
    res["share_of_available_time_in_windows_ge"] = {
        str(x): float(allw[allw >= x].sum() / tot) if tot else 0.0 for x in thresholds_min}
    days = len(s) * slot_min / 1440
    res["reclaims_per_day"] = float(len(lens) / days) if days else 0.0
    return res


def residual_to_reclaim(s, L, slot_min, n_samples=20000, seed=0):
    """For leases of size L started at random slots with s_t>=L: time until s drops below L."""
    ok = s >= L
    idx = np.where(ok)[0]
    if len(idx) == 0:
        return {}
    # next index where not ok, for every position
    nxt = np.full(len(s) + 1, len(s))
    for i in range(len(s) - 1, -1, -1):
        nxt[i] = i if not ok[i] else nxt[i + 1]
    rng = np.random.default_rng(seed)
    pick = rng.choice(idx, size=min(n_samples, len(idx)), replace=False)
    res = (nxt[pick] - pick).astype(float)
    censored = nxt[pick] == len(s)
    r = res[~censored] * slot_min
    if len(r) == 0:
        return {"censored_frac": 1.0}
    return {"censored_frac": float(censored.mean()),
            "residual_min_quantiles_p10_25_50_75_90": [float(x) for x in np.percentile(r, [10, 25, 50, 75, 90])],
            "P_survive_ge": {str(x): float((r >= x).mean()) for x in (15, 30, 60, 180, 360)}}


def reclaim_predictability(s, L, slot_min, period_slots, leads_min=(5, 15, 30, 60, 120)):
    """Can a lender announce a reclaim H minutes ahead?

    A reclaim is a down-crossing of L. Forecast for t made at t-H: seasonal-naive (same time one period
    earlier) and seasonal with level correction s[t-P] + (s[t-H] - s[t-H-P]). A reclaim at r is 'announced'
    if the forecast made at r-H says s < L at r. Reports recall and precision of announcements.
    """
    ok = s >= L
    down = np.where(ok[:-1] & ~ok[1:])[0] + 1
    P = period_slots
    out = {}
    for H in leads_min:
        h = max(1, int(round(H / slot_min)))
        res = {}
        for name in ("seasonal", "seasonal_level"):
            fc = np.full(len(s), np.nan)
            if name == "seasonal":
                fc[P:] = s[:-P]
            else:
                fc[P + h:] = s[h:-P] + (s[P:-h] - s[:-P - h])
            pred_below = fc < L
            valid = ~np.isnan(fc)
            rec = down[valid[down]]
            recall = float(pred_below[rec].mean()) if len(rec) else float("nan")
            # precision: forecast-made announcements (forecast flips to below while currently ok) that come true
            ann = np.where(valid[h:] & pred_below[h:] & ok[:-h])[0] + h
            prec = float((~ok[ann]).mean()) if len(ann) else float("nan")
            res[name] = {"recall": recall, "precision": prec}
        out[str(H)] = res
    return out


def diurnal_profile(x, slots_per_day):
    n = len(x) // slots_per_day * slots_per_day
    m = x[:n].reshape(-1, slots_per_day)
    prof = m.mean(axis=0)
    return {"peak_to_trough": float(prof.max() / max(prof.min(), 1e-9)),
            "cv_daily_profile": float(prof.std() / max(prof.mean(), 1e-9)),
            "day_to_day_corr": float(np.nanmean([np.corrcoef(m[i], m[i + 1])[0, 1] for i in range(len(m) - 1)]))
            if len(m) > 1 else float("nan")}
