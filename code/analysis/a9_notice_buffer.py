"""Price of notice from the lender's side.

Reclaims are hard to forecast (a1/a2), so a lender can only promise H minutes of notice by holding back a buffer:
lend s_t - b and keep b in reserve, so a drop of first-party slack within H minutes is absorbed by the buffer
while the borrower is notified. Buffer needed for H-minute notice with probability 1-eps:
    b_H = quantile_{1-eps} of  D_H(t) = s_t - min_{t <= u <= t+H} s_u.
Reported as a fraction of mean lendable slack, i.e. the share of lendable capacity sacrificed to offer notice H.
The functions are reused by a9b (windows up to 24 h) and a11 (IR prices). buffer_curve() gives the pricing buffer
b_l(D) of a contract with window D: the running maximum of the raw quantile over all 5-min windows up to D
(design §5.2.2, §5.3.5); the MS1 simulator (code/sim/, not yet written) is to use the same function.
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from common import OUT, save_json

SLOT_MIN = 5  # resolution of the a1/a2 slack series
SERIES_FILES = ("a1_slack_series.npz", "a2_slack_series.npz")
WINDOWS_MIN = (5, 15, 30, 60, 120, 240)
QUANTILES = (90, 99, 99.9)


def drops(s, H, slot_min=SLOT_MIN):
    """D_H(t) = s_t - min_{t <= u <= t+H} s_u for every t whose window lies inside the series."""
    h = H // slot_min
    w = sliding_window_view(s, h + 1)
    return s[: len(w)] - w.min(axis=1)


def buffer_fracs(s, H, quantiles=QUANTILES):
    """Quantiles of D_H(t) as fractions of mean slack, keyed 'p90', 'p99', 'p99.9'."""
    d = drops(s, H)
    return {f"p{q}": float(np.percentile(d, q) / s.mean()) for q in quantiles}


def buffer_curve(s, Dmax, quantiles=QUANTILES, slot_min=SLOT_MIN):
    """Raw buffer b(D) and its non-decreasing envelope on every slot-multiple window D = slot_min, ..., Dmax.

    Returns {"raw": {D: {q: b}}, "env": {D: {q: b}}, "argmax": {D: {q: D'}}}, q in 'p90', 'p99', 'p99.9'.
    env[D] = max over D' <= D of raw[D'] (argmax: the first D' attaining it). A lender that honors window D also
    honors every shorter window, while the raw quantile can dip as D grows (fewer start slots remain), so the
    pricing buffer b_l(D_k) of a contract is env at D_k. The window minimum is extended one slot at a time, so
    raw[D] equals buffer_fracs(s, D) exactly."""
    n, mean = len(s), s.mean()
    keys = [f"p{q}" for q in quantiles]
    wmin, raw, env, arg = s.copy(), {}, {}, {}
    best = {k: (-np.inf, None) for k in keys}
    for h in range(1, Dmax // slot_min + 1):
        wmin = np.minimum(wmin[: n - h], s[h:])   # min of s[t..t+h] for t < n - h
        D = h * slot_min
        d = s[: n - h] - wmin
        raw[D] = {k: float(np.percentile(d, q) / mean) for k, q in zip(keys, quantiles)}
        best = {k: (raw[D][k], D) if raw[D][k] > best[k][0] else best[k] for k in keys}
        env[D] = {k: best[k][0] for k in keys}
        arg[D] = {k: best[k][1] for k in keys}
    return {"raw": raw, "env": env, "argmax": arg}


def tail_episodes(d, v, h):
    """Windows with drop >= v (v > 0) and the number of groups of mutually overlapping tail windows.

    d: drops(s, D) with h = D / slot_min. Windows [t, t+h] and [t', t'+h] overlap iff |t' - t| <= h, so one
    episode is one drop event; a quantile with a single episode rests on the largest drop in the sample."""
    if v <= 0:
        return None, None
    idx = np.flatnonzero(d >= v)
    return int(len(idx)), int(1 + np.count_nonzero(np.diff(idx) > h))


def lenders():
    """(name, slack series) for every lender with a non-constant, positive slack series, in file order."""
    out = []
    for f in SERIES_FILES:
        z = np.load(f"{OUT}/{f}")
        for k in z.files:
            s = z[k].astype(float)
            if s.mean() <= 0 or s.std() == 0:
                continue
            out.append((f"{f[:2]}:{k}", s))
    return out


def main():
    res = {name: {str(H): buffer_fracs(s, H) for H in WINDOWS_MIN} for name, s in lenders()}
    summary = {}
    for H in map(str, WINDOWS_MIN):
        summary[H] = {q: float(np.median([v[H][q] for v in res.values()])) for q in ("p90", "p99", "p99.9")}
    res["_median_over_lenders"] = summary
    save_json("a9_notice_buffer.json", res)
    for H, v in summary.items():
        print(f"H={H:>3} min  buffer/mean slack  p90={v['p90']:.3f}  p99={v['p99']:.3f}  p99.9={v['p99.9']:.3f}")


if __name__ == "__main__":
    main()
