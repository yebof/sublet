"""Per-calendar-week WildChat profiles for the out-of-sample folds (MS7, design/ms7/plan.md §3 X2;
design/ms7/feasibility/oos.md §3 and §4 item 4; change C55).

The borrower model of a4b (decision Q30 (a), (b), 2026-10-16) averages the user-hour profile over the whole early
window (before a4b.EARLY_END) and counts r_oj over the same window. The held-out evaluation of MS7 needs instead
  (1) one profile per calendar week, so that every evaluated week has its own demand shape (the simulator's borrowers
      key p_o_week, traces.borrowers.wildchat_week), and
  (2) p_o and r_oj fitted on the earlier weeks only (borrower model 'a4c_fit'), so that the platform's own capacity
      C0 and Gamma are fitted without the evaluated weeks (borrowers.demand_fit).
Definitions follow a4b exactly: a user-hour is a distinct (region, hashed IP, calendar hour) of a4b.read(); hw =
24 * dayofweek + hour of the UTC hour, Monday 00:00 = 0 (a4b.hour_of_week); the separable smoother p(d, h) = (mean of
day d) x (24-h profile at h) of the normalized counts (a4b.variant), mean 1 over the 168 hours; r_oj are a4b.shares
of the conversations under the default tier map.

Calendar weeks start on Monday 00:00 UTC: with h the hours since 1970-01-01 00:00 (a Thursday), week (h + 72) // 168
(a4b.hour_of_week(h) is 0 exactly at its first hour). A week is full when it lies inside the early window and at
least MIN_ACTIVE_HOURS of its 168 hours have a user-hour in one of the five regions (the feasibility study's rule:
73 full weeks, 2023-04-10 to 2024-09-23). The first N_FIT full weeks are 'fit', the rest 'held_out' (36 weeks);
the fit part of the early window is [start of the early window, start of the first held-out week), and every
partial week before that boundary counts in the fit model, as a4b counts every hour of its window.

Per week and region: the user-hour counts by hw and the week's profile p_o_week, a4b's separable smoother of the
week's counts, level normalized to mean 1 (a week's volume does not enter; the weekly volume factor, total over the
mean weekly total, is reported apart). For the two sparse regions of POOL_REGIONS (south_southeast_asia, median 288
user-hours per week, and south_america, 128; oos.md §1.7 and risk 6) the smoother is applied to the counts summed over
POOL_WEEKS consecutive full weeks of the same split that end at the week (shifted forward at the start of the split,
so always POOL_WEEKS weeks and never a week of the other split; the window is recorded): on a single week it leaves up
to 84 of south_america's 168 hours at zero, on four weeks at most 14 (the single-week profile of every region is
separable() of the stored counts, a sensitivity). Per week and region also its correlation with a4b's averaged profile
and its peak over mean. Check: a4b's early-window p_o and r_oj recomputed by this script's code path (a4b.variant and
a4b.shares on the same rows) equal the stored a4b values; the script exits nonzero otherwise.

The fit model's r_oj differs from a4b's early r_oj (the L tier's share rose in 2024): the simulator's evaluated demand
takes r_oj from the borrower model it names, so under 'a4c_fit' the held-out weeks keep the fit part's region x tier
mix (level normalization: a held-out week contributes its shape, not its volume or mix).

Output: out/a4c_wildchat_weeks.json (numeric lists on one line each, about 0.7 MB). Reads the WildChat raw trace through
a4b.read() (6 GB cap in run_all.sh; measured on 2026-11-07: 0.73 GB peak RSS, 27-65 s).
"""
import json
import os
import re

import numpy as np

import a4b_wildchat_weekly as a4b
from common import OUT

MIN_ACTIVE_HOURS = 150       # a full week: at least this many of its 168 hours with a user-hour (oos.md §1.3)
N_FIT = 37                   # the first 37 of the 73 full weeks are the fit weeks (oos.md §3)
H = a4b.H
WEEK_SHIFT_H = 72            # (h + 72) // 168 changes at Monday 00:00 UTC (epoch hour 0 is Thursday 00:00)
ROUND = 6
POOL_REGIONS = ("south_southeast_asia", "south_america")     # sparse regions: pooled profiles (oos.md risk 6)
POOL_WEEKS = 4


def week_of(hour):
    return (np.asarray(hour, dtype=np.int64) + WEEK_SHIFT_H) // H


def week_start_hour(w):
    return int(w) * H - WEEK_SHIFT_H


def separable(counts):
    """a4b's separable smoother of one (or several) rows of hour-of-week counts: P = counts / mean, then
    (mean of day d of P) x (mean over the 7 days of P at hour h); mean 1 over the 168 hours."""
    R = np.atleast_2d(np.asarray(counts, dtype=float))
    P = a4b.normalize_rows(R)
    F = a4b.fold(P)
    return (P.reshape(len(P), 7, 24).mean(2)[:, :, None] * F[:, None, :]).reshape(len(P), H)


def pool_window(k: int, n_weeks: int, n_fit: int = N_FIT, n: int = POOL_WEEKS) -> tuple:
    """[start, end) of the n full weeks of week k's split that end at k, shifted forward at the split's start (fit
    weeks [0, n_fit), held-out weeks [n_fit, n_weeks))."""
    lo, hi = (0, n_fit) if k < n_fit else (n_fit, n_weeks)
    s = min(max(lo, k - n + 1), hi - n)
    return s, s + n


def _corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])


def _compact(obj) -> str:
    """JSON with indent 1 whose innermost numeric lists stay on one line (the file holds 73 x 5 x 168 x 2 numbers)."""
    text = json.dumps(obj, indent=1, default=float)
    return re.sub(r"\[\s*((?:-?[0-9.eE+-]+,\s*)*-?[0-9.eE+-]+)\s*\]",
                  lambda m: "[" + ",".join(x.strip() for x in m.group(1).split(",")) + "]", text)


def main():
    agg, users, langs, turns_hw, lag_s, last_eq = a4b.read()
    a4b_json = json.load(open(f"{OUT}/a4b_wildchat_weekly.json"))
    early_end = int(np.datetime64(a4b.EARLY_END, "h").astype(np.int64))
    # a4b.main's frames: the tier maps, the region and hour-of-week columns, coverage and the user-hours
    agg["hw"] = a4b.hour_of_week(agg.hour.to_numpy())
    agg["family"] = agg.model.map(a4b.family)
    agg["variant"] = agg.model.map({m: re.sub(a4b.VERSION_SUFFIX, "", m) for m in agg.model.unique()})
    agg["tier_card"] = agg.family.map(a4b.TIER_CARD)
    agg["tier"] = agg.variant.map(a4b.TIER_OVERRIDE).fillna(agg.tier_card)
    agg["region"] = agg.country.map(a4b.COUNTRY_REGION)
    users["hw"] = a4b.hour_of_week(users.hour.to_numpy().astype(np.int64))
    allh = agg.groupby("hour").n.sum()
    h0, h1 = int(allh.index.min()), int(allh.index.max()) + 1
    active = np.zeros(h1 - h0, bool)
    active[allh.index.to_numpy() - h0] = True
    reg = agg[agg.region.notna()]
    uh = users.drop_duplicates(["r", "ip", "hour"]).groupby(["region", "hour", "hw"], as_index=False).size()
    uh = uh.rename(columns={"size": "n"})

    # reproduction of a4b's early borrower model by this code path
    sel = uh[(uh.hour >= h0) & (uh.hour < early_end)]
    _, _, v_early = a4b.variant(sel, active, h0, (h0, early_end))
    s_early = a4b.shares(reg[(reg.hour >= h0) & (reg.hour < early_end)])
    bm = a4b_json["borrower_model"]["early"]
    repro = {"p_o_max_abs_diff": float(max(np.abs(np.array(v_early["p_o_separable_utc"][o])
                                                  - np.array(bm["p_o"][o])).max() for o in a4b.REG)),
             "r_oj_max_abs_diff": float(max(abs(s_early["r_oj"][o][j] - bm["r_oj"][o][j])
                                            for o in a4b.REG for j in a4b.TIERS))}
    repro["ok"] = repro["p_o_max_abs_diff"] == 0.0 and repro["r_oj_max_abs_diff"] <= 1e-12

    # calendar weeks of the early window
    sel = sel.assign(week=week_of(sel.hour.to_numpy()))
    hours_per_week = sel.groupby("week").hour.nunique()
    full = [int(w) for w in sorted(hours_per_week.index)
            if week_start_hour(w) >= h0 and week_start_hour(w) + H <= early_end
            and int(hours_per_week[w]) >= MIN_ACTIVE_HOURS]
    if len(full) <= N_FIT:
        raise SystemExit(f"only {len(full)} full weeks, not more than N_FIT = {N_FIT}")
    split_h = week_start_hour(full[N_FIT])
    counts = {o: [] for o in a4b.REG}
    for w in full:
        sw = sel[sel.week == w]
        for i, o in enumerate(a4b.REG):
            s = sw[sw.region == o].groupby("hw").n.sum()
            row = np.zeros(H, dtype=np.int64)
            row[s.index.to_numpy()] = s.to_numpy()
            counts[o].append(row)
    prof, single, stats = {}, {}, {}
    p_avg = {o: np.asarray(bm["p_o"][o], dtype=float) for o in a4b.REG}
    windows = [list(pool_window(k, len(full))) for k in range(len(full))]
    for o in a4b.REG:
        C = np.vstack(counts[o])
        if np.any(C.sum(1) == 0):
            raise SystemExit(f"{o}: a full week without a user-hour")
        single[o] = np.round(separable(C), ROUND)
        S = np.vstack([separable(C[a:b].sum(0)) for a, b in windows]) if o in POOL_REGIONS else separable(C)
        prof[o] = np.round(S, ROUND)
        tot = C.sum(1)
        level = tot / tot.mean()
        cors = np.array([_corr(S[k], p_avg[o]) for k in range(len(full))])
        held = slice(N_FIT, None)
        stats[o] = {"user_hours_per_week_median": float(np.median(tot)),
                    "user_hours_per_week_median_fit": float(np.median(tot[:N_FIT])),
                    "user_hours_per_week_median_held_out": float(np.median(tot[held])),
                    "user_hours_per_week_min": int(tot.min()),
                    "corr_with_a4b_p_o_median": float(np.median(cors)),
                    "corr_with_a4b_p_o_p10": float(np.percentile(cors, 10)),
                    "peak_over_mean_week_median": float(np.median(S.max(1))),
                    "peak_over_mean_a4b_p_o": float(p_avg[o].max()),
                    "pooled": o in POOL_REGIONS,
                    "weeks_with_zero_hours": int((prof[o] == 0).any(1).sum()),
                    "zero_hours_max": int((prof[o] == 0).sum(1).max()),
                    "weeks_with_zero_hours_single": int((single[o] == 0).any(1).sum()),
                    "zero_hours_max_single": int((single[o] == 0).sum(1).max()),
                    "level_p10_p90": [float(np.percentile(level, 10)), float(np.percentile(level, 90))],
                    "level_per_week": np.round(level, ROUND).tolist()}

    # the fit model: p_o (user-hours) and r_oj (conversations) of [h0, split_h)
    sel_fit = uh[(uh.hour >= h0) & (uh.hour < split_h)]
    _, _, v_fit = a4b.variant(sel_fit, active, h0, (h0, split_h))
    s_fit = a4b.shares(reg[(reg.hour >= h0) & (reg.hour < split_h)])
    fit_model = {"role": "MS7 out-of-sample folds (C55): the early borrower model fitted before the first held-out "
                         "week", "window": "fit", "window_utc": v_fit["window_utc"], "p_o_unit": "user_hours",
                 "p_o_profile": "p_o_separable_utc", "p_o": v_fit["p_o_separable_utc"],
                 "p_o_hour_of_week_utc_raw": v_fit["p_o_hour_of_week_utc"], "r_oj_unit": "conversations",
                 "tier_map": "default", "r_oj": s_fit["r_oj"], "region_share": s_fit["region_share"],
                 "tier_share_all_regions": s_fit["tier_share_all_regions"],
                 "tier_share_within_region": s_fit["tier_share_within_region"], "counts": s_fit["counts"],
                 "corr_with_a4b_p_o": {o: _corr(np.array(v_fit["p_o_separable_utc"][o]), p_avg[o]) for o in a4b.REG},
                 "r_oj_max_abs_diff_vs_a4b": float(max(abs(s_fit["r_oj"][o][j] - bm["r_oj"][o][j])
                                                       for o in a4b.REG for j in a4b.TIERS))}
    weeks = [{"index": k, "start_utc": a4b.to_ts(week_start_hour(w)), "calendar_week": int(w),
              "active_hours": int(hours_per_week[w]), "split": "fit" if k < N_FIT else "held_out"}
             for k, w in enumerate(full)]
    out = {
        "definitions": {
            "spec": "design/ms7/plan.md §3 X2; design/ms7/feasibility/oos.md §3, §4 item 4; change C55",
            "week": "calendar week from Monday 00:00 UTC: (hours since 1970-01-01 + 72) // 168",
            "full_week": f"inside the early window (before {a4b.EARLY_END}) with at least {MIN_ACTIVE_HOURS} of its "
                         "168 hours holding a user-hour of the five regions",
            "split": f"the first {N_FIT} full weeks are 'fit', the others 'held_out'; the fit window is [start of the "
                     "early window, start of the first held-out week)",
            "user_hours": "a4b: distinct hashed IPs per region and calendar hour",
            "p_o_week": "per region and full week: the week's user-hour counts by hw, smoothed by a4b's separable "
                        f"form, mean 1 over the 168 hours (level normalized), rounded to {ROUND} decimals; for "
                        f"{list(POOL_REGIONS)} the counts summed over the {POOL_WEEKS} full weeks of pool_window",
            "single_week": "the *_single statistics: p_o_week on the week's own counts for every region "
                           "(separable(counts[region][week]), not stored)",
            "pool_window": f"[start, end) of the {POOL_WEEKS} consecutive full weeks of the week's split that end at "
                           "the week, shifted forward at the split's start",
            "borrower_model": "a4c_fit: a4b's early model (p_o user-hours, separable; r_oj conversations, default "
                              "tier map) on the fit window only",
            "level": "a week's user-hour total over the mean weekly total of the full weeks (not used by p_o_week)",
            "regions": a4b.REG, "hw": "24*dayofweek + hour of the UTC timestamp, Monday 00:00 = 0"},
        "n_weeks": len(full), "n_fit": N_FIT, "n_held_out": len(full) - N_FIT,
        "early_window_utc": [a4b.to_ts(h0), a4b.to_ts(early_end)], "split_utc": a4b.to_ts(split_h),
        "weeks": weeks,
        "counts": {o: [r.tolist() for r in counts[o]] for o in a4b.REG},
        "pool_regions": list(POOL_REGIONS), "pool_weeks": POOL_WEEKS, "pool_window": windows,
        "p_o_week": {o: prof[o].tolist() for o in a4b.REG},
        "region_stats": stats,
        "borrower_model": {"a4c_fit": fit_model},
        "reproduce_a4b_early": repro,
    }
    path = os.path.join(OUT, "a4c_wildchat_weeks.json")
    with open(path, "w") as f:
        f.write(_compact(out) + "\n")
    print("wrote", path)
    print(f"{len(full)} full weeks ({N_FIT} fit, {len(full) - N_FIT} held out), split {a4b.to_ts(split_h)}; "
          f"reproduction of a4b early: {repro}")
    for o, s in stats.items():
        print(f"  {o:22s} user-hours/week median {s['user_hours_per_week_median']:.0f}, corr with a4b p_o median "
              f"{s['corr_with_a4b_p_o_median']:.3f}, peak/mean median {s['peak_over_mean_week_median']:.2f}, "
              f"pooled {s['pooled']}, weeks with zero hours {s['weeks_with_zero_hours']} (single week: "
              f"{s['weeks_with_zero_hours_single']}, at most {s['zero_hours_max_single']} hours)")
    if not repro["ok"]:
        raise SystemExit(f"a4b's early model is not reproduced: {repro}")


if __name__ == "__main__":
    main()
