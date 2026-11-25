"""Trace-driven sanity check of the RRL primitive (single lender, LIFO layers, H = 0).

Borrower: overflow above own capacity C0 (= P75 of 15-min-smoothed tokens/min), split into K layers.
Lender: spare capacity s_t; borrower layer k is available while s_t >= k * v (LIFO: top layers reclaimed first).
Costs per layer, in units of one replica-minute of fallback (q = 1):
  fallback q=1/min when needed and not leased; lease alpha/min while held; setup B per lease start;
  reclaim while serving costs mu_A online and mu_O for the offline optimum.
Policies: NEVER, GREEDY (lease whenever needed and available), THRESH(s) (lease after the need has lasted s
minutes; s = B/(1-alpha) is the ski-rental break-even), KEEP(w) (THRESH plus keep the lease w minutes after
need ends). OPT: exact offline DP per layer.
"""
import json

import numpy as np

from common import OUT, save_json

rng = np.random.default_rng(1)


def layer_cost_online(need, avail, B, alpha, mu, s_thr, keep=0):
    cost, held, run, idle = 0.0, False, 0, 0
    for t in range(len(need)):
        if held and not avail[t]:                 # reclaimed
            if need[t]:
                cost += mu
            held = False
        run = run + 1 if need[t] else 0
        if not held and need[t] and avail[t] and run > s_thr:
            held, idle = True, 0
            cost += B
        if held:
            cost += alpha
            idle = 0 if need[t] else idle + 1
            if idle > keep:
                held = False
        elif need[t]:
            cost += 1.0
    return cost


def layer_cost_opt(need, avail, B, alpha, mu):
    """Exact offline optimum for one layer: 2-state DP (off / holding a lease)."""
    INF = 1e18
    off, on = 0.0, INF
    for t in range(len(need)):
        n = 1.0 if need[t] else 0.0
        if avail[t]:
            off, on = min(off, on) + n, min(on, off + B) + alpha
        else:  # lender reclaims: a held lease ends; pay mu if it was serving
            off, on = min(off, on + mu * n) + n, INF
    return min(off, on)


def run(borrower, lender_s, K=8, B=15, alpha=0.3, muA=15, muO=7.5, trials=6, smooth=15):
    # capacity follows demand smoothed over `smooth` minutes (queues absorb sub-minute bursts)
    d = np.convolve(np.asarray(borrower, float), np.ones(smooth) / smooth, mode="valid")
    C0 = np.percentile(d, 75)
    u = (np.percentile(d, 99.5) - C0) / K
    s = np.repeat(np.asarray(lender_s, float), 5)  # 5-min lender series -> 1-min
    v = np.percentile(s, 50) / K
    thr = B / (1 - alpha)
    pols = {"NEVER": None, "GREEDY": (0, 0), "THRESH": (thr, 0), "THRESH+KEEP": (thr, int(thr))}
    tot = {k: 0.0 for k in list(pols) + ["OPT"]}
    for _ in range(trials):
        off = rng.integers(0, len(s) - len(d)) if len(s) > len(d) else 0
        ss = s[off: off + len(d)] if len(s) > len(d) else np.resize(s, len(d))
        for k in range(1, K + 1):
            need = d - C0 >= k * u
            avail = ss >= k * v
            tot["NEVER"] += need.sum()
            for name, p in pols.items():
                if p is not None:
                    tot[name] += layer_cost_online(need, avail, B, alpha, muA, *p)
            tot["OPT"] += layer_cost_opt(need, avail, B, alpha, muO)
    return {k: v / tot["OPT"] for k, v in tot.items()} | {"savings_OPT_vs_NEVER": 1 - tot["OPT"] / tot["NEVER"]}


if __name__ == "__main__":
    import numpy as np
    bor = np.load(f"{OUT}/a3_minute_series.npz")
    lenders = {}
    for f in ("a1_slack_series.npz", "a2_slack_series.npz"):
        try:
            z = np.load(f"{OUT}/{f}")
            lenders.update({f[:2] + ":" + k: z[k] for k in z.files})
        except FileNotFoundError:
            pass
    # representative lenders: spot-gpu H800 and A100, and the three largest maas clusters
    pick = [k for k in lenders if k.startswith("a1:") and ("H800" in k or "A100" in k)]
    pick += [k for k in lenders if k.startswith("a2:")][:3]
    res = {}
    for bname in bor.files:
        d = bor[bname]
        if len(d) > 30 * 1440:  # cap long traces at 30 days to keep the DP fast
            d = d[: 30 * 1440]
        for lname in pick:
            for B, muA, muO in ((5, 5, 2.5), (15, 15, 7.5), (15, 30, 15), (60, 60, 30)):
                key = f"{bname}|{lname}|B={B},muA={muA},muO={muO}"
                res[key] = run(d, lenders[lname], B=B, muA=muA, muO=muO, trials=4)
                print(key, {k: round(v, 3) for k, v in res[key].items()})
    save_json("a7_policy_sim.json", res)
