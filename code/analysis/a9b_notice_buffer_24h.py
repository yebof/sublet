"""Notice buffer for contract windows up to 24 h (MS0; design §5.2.2).

For lender l with first-party slack S_l(t) (a1/a2 slack series, 5-min slots) and contract window D = tau + H:
    B_l(D) = quantile_{1-eps}[ S_l(t) - min_{t <= t' <= t+D} S_l(t') ],   b_l(D) = B_l(D) / mean(S_l),
computed with a9's functions (eps = 0.01 by default; P90 and P99.9 as well). A contract of window D is
individually rational for the lender at price a0 / (1 - b_l(D)) and can be offered only if b_l(D) < 1.

Sample size. Only windows that lie inside the series are used, so a window of D minutes has n - D/5 start
slots. The MaaS series cover one week (2016 slots): a 24 h window has 1728 overlapping start slots, which
span 6 days, and 6 disjoint 24 h windows fit in the week. Per lender and window we report n_windows
(overlapping start slots), n_disjoint (disjoint windows that fit), and, per quantile, n_tail_windows (windows
whose drop is at least the quantile) and n_tail_episodes (groups of tail windows that overlap, so distinct
drop events behind the quantile).

Envelopes. b_envelope is the running maximum of b over this script's 9-point grid only. The pricing buffer of a
contract (a11; the MS1 simulator, not yet written, is to use the same function; design §5.2.2, §5.3.5) is
a9_notice_buffer.buffer_curve's running maximum over every 5-min window up to D, reported here as b_envelope_5min
at the grid windows; it can exceed b_envelope where b dips between grid points.

Longest offerable window. D_max_offerable_min is the largest window of the 9-point grid that a lender can offer
(every grid window up to it has b < 1); the true limit lies between it and the next grid window.
D_max_offerable_5min_min is the largest window on the 5-min grid up to 1440 min whose 5-min envelope is below 1
(1440 means at least 24 h).

Checks: (1) for D <= 240 min the values equal a9_notice_buffer.json; (2) the window minimum is recomputed
with an independent implementation (pandas rolling minimum on the reversed series); (3) buffer_curve's raw values
equal b at the grid windows.
"""
import json

import numpy as np
import pandas as pd

from a9_notice_buffer import QUANTILES, SLOT_MIN, buffer_curve, buffer_fracs, drops, lenders, tail_episodes
from common import OUT, save_json

WINDOWS_MIN = (5, 15, 30, 60, 120, 240, 480, 720, 1440)
DEFAULT_Q = "p99"  # eps = 0.01
QK = [f"p{q}" for q in QUANTILES]
# Groups for summaries. L7 of the design uses the four spot pools below; A10 is excluded there because its
# high-priority requests exceed its GPU count (GPU sharing), and GPU-series-1 shares machines with A10.
GROUPS = {
    "maas_20_clusters": lambda n: n.startswith("a2:"),
    "spot_4_pools_L7": lambda n: n in ("a1:A100-SXM4-80GB", "a1:H800", "a1:A800-SXM4-80GB", "a1:GPU-series-2"),
    "spot_all_6_pools": lambda n: n.startswith("a1:"),
}
SOURCE = {"a1": "Alibaba spot GPU v2026 (a1_slack_series.npz)",
          "a2": "Alibaba MaaS v2026, one week (a2_slack_series.npz)"}


def drops_independent(s, H):
    """Same as a9's drops(), via a rolling minimum on the reversed series."""
    h = H // SLOT_MIN
    fwd_min = pd.Series(s[::-1]).rolling(h + 1).min().to_numpy()[::-1]
    n = len(s) - h
    return s[:n] - fwd_min[:n]


def ir_multiplier(b):
    return float(1.0 / (1.0 - b)) if b < 1 else None


assert all(D % SLOT_MIN == 0 for D in WINDOWS_MIN)
res_l, max_impl_diff, monotone_violations, curve_mismatch, env_above_grid = {}, 0.0, [], 0, []
for name, s in lenders():
    n, mean = len(s), float(s.mean())
    curve = buffer_curve(s, max(WINDOWS_MIN))
    r = {"source": SOURCE[name[:2]], "n_slots": n, "horizon_days": n * SLOT_MIN / 1440,
         "mean_slack_gpus": mean, "windows": {}}
    for D in WINDOWS_MIN:
        h = D // SLOT_MIN
        d = drops(s, D)
        max_impl_diff = max(max_impl_diff, float(np.max(np.abs(d - drops_independent(s, D)))))
        b = buffer_fracs(s, D)
        curve_mismatch += sum(curve["raw"][D][q] != b[q] for q in b)
        w = {"n_windows": int(len(d)), "start_span_days": len(d) * SLOT_MIN / 1440,
             "n_disjoint": int(n // (h + 1)), "b": b, "max_drop_frac": float(d.max() / mean),
             "offerable": {q: bool(b[q] < 1) for q in QK},
             "ir_multiplier": {q: ir_multiplier(b[q]) for q in QK},
             "n_tail_windows": {}, "n_tail_episodes": {}}
        for q, qv in zip(QK, QUANTILES):
            w["n_tail_windows"][q], w["n_tail_episodes"][q] = tail_episodes(d, np.percentile(d, qv), h)
        r["windows"][str(D)] = w
    # largest window D in the grid such that every grid window up to D is offerable
    r["D_max_offerable_min"] = {}
    for q in QK:
        ok = [D for D in WINDOWS_MIN if r["windows"][str(D)]["b"][q] < 1]
        dmax = None
        for D in WINDOWS_MIN:
            if D not in ok:
                break
            dmax = D
        r["D_max_offerable_min"][q] = dmax
        # same on the 5-min grid: the envelope is non-decreasing, so the offerable windows form a prefix
        ok5 = [D for D in sorted(curve["env"]) if curve["env"][D][q] < 1]
        r.setdefault("D_max_offerable_5min_min", {})[q] = ok5[-1] if ok5 else None
        bs = [r["windows"][str(D)]["b"][q] for D in WINDOWS_MIN]
        if any(y < x for x, y in zip(bs, bs[1:])):
            monotone_violations.append(f"{name}:{q}")
        # non-decreasing envelope over the grid: a lender that honors window D also honors every shorter one,
        # and the shrinking set of start slots can make the raw quantile dip at long D
        for D, e in zip(WINDOWS_MIN, np.maximum.accumulate(bs)):
            w = r["windows"][str(D)]
            w.setdefault("b_envelope", {})[q] = float(e)
            w.setdefault("ir_multiplier_envelope", {})[q] = ir_multiplier(e)
            e5 = curve["env"][D][q]
            w.setdefault("b_envelope_5min", {})[q] = e5
            w.setdefault("b_envelope_5min_argmax_D_min", {})[q] = curve["argmax"][D][q]
            w.setdefault("ir_multiplier_envelope_5min", {})[q] = ir_multiplier(e5)
            if e5 > e:
                env_above_grid.append(f"{name}:{q}:{D}")
    res_l[name] = r

summary = {}
for g, pick in GROUPS.items():
    names = [k for k in res_l if pick(k)]
    sg = {"lenders": names, "windows": {}}
    for D in map(str, WINDOWS_MIN):
        sw = {}
        for q in QK:
            b = np.array([res_l[k]["windows"][D]["b"][q] for k in names])
            m = np.median(np.where(b < 1, 1.0 / np.maximum(1.0 - b, 1e-300), np.inf))
            sw[q] = {"median_b": float(np.median(b)), "min_b": float(b.min()), "max_b": float(b.max()),
                     "argmax": names[int(b.argmax())], "n_offerable": int((b < 1).sum()),
                     "median_ir_multiplier": float(m) if np.isfinite(m) else None}
        ep = [res_l[k]["windows"][D]["n_tail_episodes"]["p99"] for k in names]
        ep = [e for e in ep if e is not None]
        sw["p99_tail_episodes"] = {"min": min(ep, default=None), "median": float(np.median(ep)) if ep else None,
                                   "n_lenders_with_one_episode": sum(e == 1 for e in ep),
                                   "n_lenders_with_positive_p99": len(ep)}
        ratio = [res_l[k]["windows"][D]["b"]["p99"] / res_l[k]["windows"][D]["max_drop_frac"] for k in names
                 if res_l[k]["windows"][D]["max_drop_frac"] > 0]
        sw["median_p99_over_max_drop"] = float(np.median(ratio)) if ratio else None
        sg["windows"][D] = sw
    summary[g] = sg

# check against a9 for D <= 240 min
with open(f"{OUT}/a9_notice_buffer.json") as f:
    a9 = json.load(f)
diffs, n_cmp, n_exact = [], 0, 0
for name, r in res_l.items():
    for D in WINDOWS_MIN:
        if D > 240:
            continue
        for q in QK:
            x, y = r["windows"][str(D)]["b"][q], a9[name][str(D)][q]
            diffs.append(abs(x - y)); n_cmp += 1; n_exact += x == y
check = {"a9_lenders_match": sorted(res_l) == sorted(k for k in a9 if not k.startswith("_")),
         "n_values_compared": n_cmp, "n_exactly_equal": int(n_exact), "max_abs_diff": float(max(diffs)),
         "independent_window_min_max_abs_diff_gpus": max_impl_diff,
         "b_non_monotone_in_D": monotone_violations,
         "buffer_curve_raw_vs_b_mismatches": curve_mismatch,
         "b_envelope_5min_above_grid_envelope": env_above_grid}

meta = {"definition": "b_l(D) = quantile_q[S(t) - min_{t<=t'<=t+D} S(t')] / mean S, over start slots t whose "
                      "window lies inside the series; window D = tau + H of the contract",
        "slot_min": SLOT_MIN, "windows_min": list(WINDOWS_MIN), "quantiles": QK,
        "default_quantile": DEFAULT_Q, "eps_default": 0.01,
        "ir_multiplier": "1 / (1 - b); null when b >= 1 (contract not offerable from this lender)",
        "n_disjoint": "floor(n_slots / (D/5 + 1)): disjoint windows that fit in the series",
        "n_tail_episodes": "groups of mutually overlapping windows with drop >= the quantile; null if the "
                           "quantile is 0",
        "D_max_offerable_min": "largest grid window D such that b(D') < 1 for every grid D' <= D; null if none. "
                               "The true limit lies between it and the next grid window",
        "D_max_offerable_5min_min": "largest window D on the 5-min grid up to 1440 min with b_envelope_5min(D) < 1; "
                                    "1440 means at least 24 h; null if none",
        "b_envelope": "max of b(D') over the grid windows D' <= D only (non-decreasing in D); "
                      "ir_multiplier_envelope uses it",
        "b_envelope_5min": "max of b(D') over every 5-min window D' <= D (a9_notice_buffer.buffer_curve); the "
                           "pricing buffer b_l(D_k) of a11 (the MS1 simulator is to use the same function); "
                           "_argmax_D_min is the window attaining it",
        "max_drop_frac": "largest drop over all windows, as a fraction of mean slack",
        "median_p99_over_max_drop": "median over the group of b_p99 / max_drop_frac; near 1 means the P99 is "
                                    "in effect the largest drop observed"}
save_json("a9b_notice_buffer_24h.json",
          {"meta": meta, "check_vs_a9": check, "summary": summary, "lenders": res_l})

print("check:", {k: v for k, v in check.items()})
for g, sg in summary.items():
    print(f"== {g} (P99): D -> median b [min, max] (n offerable / n)  P99 tail episodes")
    for D, sw in sg["windows"].items():
        v = sw["p99"]
        e = sw["p99_tail_episodes"]
        print(f"  D={D:>4}  {v['median_b']:.4f} [{v['min_b']:.4f}, {v['max_b']:.4f} {v['argmax']}]  "
              f"{v['n_offerable']}/{len(sg['lenders'])}  episodes min {e['min']} median {e['median']} "
              f"one-episode {e['n_lenders_with_one_episode']}/{e['n_lenders_with_positive_p99']}  "
              f"p99/max {sw['median_p99_over_max_drop']:.3f}")
