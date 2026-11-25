"""Out-of-sample notice buffers of the trace lenders (MS7, design/ms7/plan.md §3 X2; design/ms7/feasibility/oos.md
§1.6, §3 and §4 item 5; change C55).

The simulator prices a revocable contract with lender window D by the lender's P99 notice buffer b_l(D) (a9's
buffer_curve: the running maximum over the windows up to D of the P99 drop D_D(t) = s_t - min_{t <= u <= t+D} s_u, as
a fraction of mean slack), holds back B = b x mean slack, sizes the lease block by the P25 of the lendable slack
(s - B)^+ and prunes the contracts with b >= 1 (code/sim/sublet/instance.py). In the confirmation every one of these
is fitted on the series the lender replays. The out-of-sample folds of the simulator (experiments/e7o.py, the lender
key calib_slots) fit them on a calibration window and evaluate on a held-out one; this script measures, outside the
simulator, how far the fitted values hold on the held-out windows:

  MaaS (20 clusters, one week of 2,016 slots)  fold fwd: fit slots [0, 1152) (days 1-4), evaluate [1152, 2016)
                                               (days 5-7, 72 h); fold rev: fit [864, 2016) (days 4-7), evaluate
                                               [0, 864) (days 1-3)
  spot (the four pools of all24, 50,993 slots) fit weeks 1-12 (slots [0, 24192)); evaluate every later full week and
                                               the 72-h blocks of the e7o cells (SPOT_BLOCK_STARTS)

Per lender, fold (or spot segment) and lender window D of the 5-min menu (a11's contracts with slot_min 5):
  b_fit, b_full, b_eval    the P99 buffer fitted on the calibration window, on the whole series (the in-sample
                           calibration of the confirmation) and on the evaluation window itself (its realized value)
  exceed_fit, exceed_full  the share of the evaluation window's drops D_D(t) (windows inside it) above B_fit = b_fit x
                           mean(fit window), and above B_full = b_full x mean(whole series): the P99 target is 1%
  ir_fit, ir_full          the IR multipliers 1 / (1 - b) (None for b >= 1: the contract is removed)
  v_top_fit, v_top_full    the lease size floor(P25((s - B)^+) / 8) on the calibration window and on the whole series
  announced_fit, _full     the share of the evaluation window's slots at which the top offered layer (v_top x 8 GPUs)
                           is announced, (s - B)^+ < v_top x 8 (the calibration makes it 25% on its own window)
and per fold and D the medians and maxima over the lenders and the number of lenders with exceed above 1%. The
prices are a0 x the IR multiplier (a0 of a11's inputs). Reads a1_slack_series.npz, a2_slack_series.npz and
a11_calibration.json (so it runs after a11 in run_all.sh); seconds, under 0.3 GB.

Output: out/a14_oos_buffers.json (numeric lists on one line each).
"""
import json
import math
import os
import re

import numpy as np

from a9_notice_buffer import buffer_curve, drops
from common import OUT

SLOT_MIN = 5
WEEK = 2016                                   # 5-min slots per week
FOLDS = {"fwd": {"fit": (0, 1152), "eval": (1152, 2016)},     # oos.md §3: days 1-4 | 5-7
         "rev": {"fit": (864, 2016), "eval": (0, 864)}}       # days 4-7 | 1-3
SPOT_FIT = (0, 12 * WEEK)                     # weeks 1-12
SPOT_BLOCK = 864                              # 72 h
SPOT_BLOCK_STRIDE = 1729                      # e7o.SPOT_BLOCK_STRIDE: 16 disjoint blocks spread over weeks 13-25
SPOT_BLOCK_STARTS = tuple(SPOT_FIT[1] + k * SPOT_BLOCK_STRIDE for k in range(16))
SPOT_L7 = ("A100-SXM4-80GB", "A800-SXM4-80GB", "GPU-series-2", "H800")     # traces/lenders.py SPOT_L7
Q = "p99"
LAYER_GPUS = 8
LEASE_Q = 25
EXCEED_TARGET = 0.01


def _ir(b):
    return None if b >= 1 else 1.0 / (1.0 - b)


def _v_top(s, B):
    return int(math.floor(np.percentile(np.maximum(s - B, 0.0), LEASE_Q) / LAYER_GPUS))


def evaluate(s_full, fit, ev, windows):
    """The fields of the module docstring for one lender, calibration window `fit` and evaluation window `ev` (slot
    ranges [lo, hi)), as lists over `windows` (minutes)."""
    s_fit, s_ev = s_full[fit[0]:fit[1]], s_full[ev[0]:ev[1]]
    Dmax = max(windows)
    cf, cu, ce = (buffer_curve(x, Dmax)["env"] for x in (s_fit, s_full, s_ev))
    out = {k: [] for k in ("b_fit", "b_full", "b_eval", "exceed_fit", "exceed_full", "ir_fit", "ir_full",
                           "v_top_fit", "v_top_full", "announced_fit", "announced_full")}
    for D in windows:
        b_fit, b_full, b_ev = cf[D][Q], cu[D][Q], ce[D][Q]
        B_fit, B_full = b_fit * s_fit.mean(), b_full * s_full.mean()
        d = drops(s_ev, D)
        v_fit, v_full = _v_top(s_fit, B_fit), _v_top(s_full, B_full)
        out["b_fit"].append(b_fit)
        out["b_full"].append(b_full)
        out["b_eval"].append(b_ev)
        out["exceed_fit"].append(float((d > B_fit + 1e-9).mean()))
        out["exceed_full"].append(float((d > B_full + 1e-9).mean()))
        out["ir_fit"].append(_ir(b_fit))
        out["ir_full"].append(_ir(b_full))
        out["v_top_fit"].append(v_fit)
        out["v_top_full"].append(v_full)
        out["announced_fit"].append(float((np.maximum(s_ev - B_fit, 0.0) < v_fit * LAYER_GPUS).mean()))
        out["announced_full"].append(float((np.maximum(s_ev - B_full, 0.0) < v_full * LAYER_GPUS).mean()))
    out["mean_slack_fit"], out["mean_slack_eval"], out["mean_slack_full"] = (float(s_fit.mean()), float(s_ev.mean()),
                                                                             float(s_full.mean()))
    return out


def summarize(rows: dict, windows) -> dict:
    """Per window: medians and maxima over the lenders (or segments) of `rows` {name: evaluate(...)}."""
    out = {"n": len(rows), "D_min": list(windows)}
    for k in ("exceed_fit", "exceed_full", "b_fit", "b_full", "b_eval", "announced_fit", "announced_full"):
        a = np.array([r[k] for r in rows.values()], dtype=float)
        out[f"{k}_median"] = np.median(a, axis=0).tolist()
        out[f"{k}_max"] = a.max(axis=0).tolist()
    for k in ("exceed_fit", "exceed_full"):
        a = np.array([r[k] for r in rows.values()], dtype=float)
        out[f"{k}_n_above_target"] = (a > EXCEED_TARGET).sum(axis=0).astype(int).tolist()
    ir = np.array([[np.nan if (f is None or u is None) else f / u for f, u in zip(r["ir_fit"], r["ir_full"])]
                   for r in rows.values()], dtype=float)
    out["ir_fit_over_full_median"] = [None if np.all(np.isnan(c)) else float(np.nanmedian(c)) for c in ir.T]
    vt = np.array([[f - u for f, u in zip(r["v_top_fit"], r["v_top_full"])] for r in rows.values()], dtype=float)
    out["v_top_fit_minus_full_median"] = np.median(vt, axis=0).tolist()
    out["removed_fit"] = [int(sum(r["ir_fit"][i] is None for r in rows.values())) for i in range(len(windows))]
    out["removed_full"] = [int(sum(r["ir_full"][i] is None for r in rows.values())) for i in range(len(windows))]
    return out


def _compact(obj) -> str:
    text = json.dumps(obj, indent=1, default=float)
    return re.sub(r"\[\s*((?:(?:-?[0-9.eE+-]+|null),\s*)*(?:-?[0-9.eE+-]+|null))\s*\]",
                  lambda m: "[" + ",".join(x.strip() for x in m.group(1).split(",")) + "]", text)


def main():
    a11 = json.load(open(f"{OUT}/a11_calibration.json"))
    windows = sorted({c["D_lender_min"] for c in a11["contracts"].values()
                      if c.get("slot_min") == SLOT_MIN and c.get("class") != "protected"})
    a0 = float(a11["inputs"]["a0"])
    with np.load(f"{OUT}/a2_slack_series.npz") as z:
        maas = {f"a2:{k}": z[k].astype(float) for k in z.files}
    with np.load(f"{OUT}/a1_slack_series.npz") as z:
        spot = {f"a1:{k}": z[k].astype(float) for k in SPOT_L7}
    out = {"definitions": {"spec": "design/ms7/plan.md §3 X2; design/ms7/feasibility/oos.md §1.6, §3, §4 item 5; "
                                   "change C55",
                           "fields": "module docstring of code/analysis/a14_oos_buffers.py", "quantile": Q,
                           "lease_size_quantile": LEASE_Q, "layer_gpus": LAYER_GPUS, "exceed_target": EXCEED_TARGET,
                           "maas_folds": {k: {"fit": list(v["fit"]), "eval": list(v["eval"])}
                                          for k, v in FOLDS.items()},
                           "spot_fit": list(SPOT_FIT), "spot_block_slots": SPOT_BLOCK,
                           "spot_block_starts": list(SPOT_BLOCK_STARTS), "slot_min": SLOT_MIN},
           "D_min": windows, "a0_usd_per_gpu_h": a0, "maas": {}, "spot": {}, "summary": {}}
    for fold, fr in FOLDS.items():
        rows = {n: evaluate(s, fr["fit"], fr["eval"], windows) for n, s in maas.items()}
        out["maas"][fold] = rows
        out["summary"][f"maas_{fold}"] = summarize(rows, windows)
    n_spot = min(len(s) for s in spot.values())
    weeks = [(w * WEEK, (w + 1) * WEEK) for w in range(SPOT_FIT[1] // WEEK, n_spot // WEEK)]
    blocks = [(a, a + SPOT_BLOCK) for a in SPOT_BLOCK_STARTS]
    if blocks[-1][1] > n_spot:
        raise SystemExit(f"the last e7o spot block ends at {blocks[-1][1]} > {n_spot} slots")
    for n, s in spot.items():
        out["spot"][n] = {"weeks": {f"w{a // WEEK + 1}": evaluate(s, SPOT_FIT, (a, b), windows) for a, b in weeks},
                          "blocks": {f"k{k}": evaluate(s, SPOT_FIT, blk, windows) for k, blk in enumerate(blocks)}}
        out["summary"][f"spot_{n}_weeks"] = summarize(out["spot"][n]["weeks"], windows)
        out["summary"][f"spot_{n}_blocks"] = summarize(out["spot"][n]["blocks"], windows)
    out["prices_usd_per_gpu_h"] = {
        "maas_fwd_fit_median": [None if v is None else a0 * v for v in
                                [None if all(r["ir_fit"][i] is None for r in out["maas"]["fwd"].values()) else
                                 float(np.median([r["ir_fit"][i] for r in out["maas"]["fwd"].values()
                                                  if r["ir_fit"][i] is not None])) for i in range(len(windows))]],
        "maas_full_median": [None if v is None else a0 * v for v in
                             [None if all(r["ir_full"][i] is None for r in out["maas"]["fwd"].values()) else
                              float(np.median([r["ir_full"][i] for r in out["maas"]["fwd"].values()
                                               if r["ir_full"][i] is not None])) for i in range(len(windows))]]}
    path = os.path.join(OUT, "a14_oos_buffers.json")
    with open(path, "w") as f:
        f.write(_compact(out) + "\n")
    print("wrote", path)
    i300 = windows.index(max(windows))
    for k, s in out["summary"].items():
        if k.startswith("maas") or k.endswith("_blocks"):
            print(f"{k:34s} D={windows[i300]}: exceed_fit median {s['exceed_fit_median'][i300]:.4f} max "
                  f"{s['exceed_fit_max'][i300]:.4f} n>1% {s['exceed_fit_n_above_target'][i300]}/{s['n']}; exceed_full "
                  f"median {s['exceed_full_median'][i300]:.4f}; b_fit {s['b_fit_median'][i300]:.4f} b_full "
                  f"{s['b_full_median'][i300]:.4f} b_eval {s['b_eval_median'][i300]:.4f}")


if __name__ == "__main__":
    main()
