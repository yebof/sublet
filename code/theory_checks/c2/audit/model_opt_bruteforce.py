"""Audit (C2, model/solver lens): independent offline OPT for the C2 model by exhaustive schedule
enumeration on a time grid, compared with model.opt_cost (the OPT used by det_game, families,
alg_check).

Schedules enumerated (OPT knows x and R; decisions on the grid; costs as in c2_single_site.md Sec. 1):
  fallback; fallback then protected at u; revocable bought at u < min(R, x) ending at E = max(R, u+tau),
  then (if x > E) cold (mu, fallback, optional protected at v >= E), pre-warm committed at d >= u
  (takeover d+lam; if the takeover is after E: mu plus fallback until takeover), or a voluntary move
  to fallback at m in (u, E) (mu) followed by fallback/protected.  A pre-warm can also be committed
  while the lease is still running and x <= E.
  TWO_LEASES (tau > 0 only): additionally a second revocable lease, committed at d2 in [u, R) as a
  warm switch from the first (takeover w2 = d2 + lam <= E1, rent from takeover, as for the
  protected switch in the code), ending at E2 = max(R, d2 + tau), followed by cold or pre-warm
  into protected.  The document's model text does not forbid this; model.opt_cost and det_game
  allow one revocable lease per episode.

Parts:
  (1) 400 random instances: model.opt_cost vs brute force (one revocable lease).
  (2) Corner where the warm switch is infeasible for OPT (R < lam): the pre-audit model.opt_cost
      omitted 'cold reclaim, then protected' (reproduced here as opt_prefix).  This option beats
      every other option only if lam > R > (beta + mu)/(ap - alpha) >= s0, i.e. never under
      condition (C) (lam <= s0).  model.opt_cost now includes it (column opt_cost).
  (3) tau > 0: OPT with a second revocable lease vs one lease (relative reduction of OPT).
Output: audit/out/model_opt_bruteforce.txt"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from model import Params, opt_cost, INF


def tail_after(E, x, P, ts):
    """cheapest continuation for demand still on at E with no warm replacement (cold): mu + ..."""
    b, ap, mu = P.beta, P.ap, P.mu
    best = mu + (x - E)
    if P.allow_p:
        vs = ts[(ts >= E - 1e-12) & (ts < x - 1e-12)]
        if len(vs):
            best = min(best, mu + float(np.min((vs - E) + b + ap * (x - vs))))
    return best


def opt_bf(x, R, P, dt, two_leases=False):
    b, a, ap, mu, lam, tau = P.beta, P.alpha, P.ap, P.mu, P.lam, P.tau
    ts = np.round(np.arange(0.0, x, dt), 10)
    ts = ts[ts < x - 1e-12]
    best = x
    if P.allow_p and len(ts):
        best = min(best, float(np.min(ts + b + ap * (x - ts))))
    if not np.isinf(R) and R <= 0:
        return best
    for u in ts:
        if not (u < R - 1e-12):
            continue
        E = INF if np.isinf(R) else max(R, u + tau)
        if x <= E:
            best = min(best, u + b + a * (x - u))
            continue
        base = u + b + a * (E - u)
        best = min(best, base + tail_after(E, x, P, ts))
        if P.allow_p:
            ds = ts[ts >= u - 1e-12]
            for d in ds:                                      # pre-warm into protected
                w = d + lam
                if w <= E + 1e-12:
                    best = min(best, u + b + a * (w - u) + b + ap * (x - max(w, 0)) if w < x else u + b + a * (x - u) + b)
                else:
                    best = min(best, base + b + mu + (min(w, x) - E) + ap * max(x - w, 0.0))
        for m in ts[(ts > u + 1e-12) & (ts < E - 1e-12)]:     # voluntary move to fallback at m
            best = min(best, u + b + a * (m - u) + tail_after(m, x, P, ts))
        if two_leases and tau > 0:
            for d2 in ts[(ts >= u - 1e-12) & (ts < R - 1e-12)]:
                w2 = d2 + lam
                if w2 > E + 1e-12 or w2 >= x:
                    continue
                E2 = max(R, d2 + tau)
                c0 = u + b + a * (w2 - u) + b                  # first lease to takeover, second load
                if x <= E2:
                    best = min(best, c0 + a * (x - w2))
                    continue
                c1 = c0 + a * (E2 - w2)
                best = min(best, c1 + tail_after(E2, x, P, ts))
                if P.allow_p and E2 - lam >= d2 - 1e-12:
                    best = min(best, c1 + b + ap * (x - E2))
    return best


def main():
    out = []
    log = lambda s: (print(s, flush=True), out.append(s))
    dt = 0.05
    G = np.round(np.arange(0, 40, dt), 10)
    # ---------------- (1) random instances, one revocable lease ----------------
    rng = np.random.default_rng(3)
    mism = []; mism_C = 0; n = 0
    for k in range(400):
        al = float(rng.choice([0.0, 0.2, 0.3, 0.5])); ap = float(rng.uniform(al + 0.05, 1.0))
        mu = float(rng.choice([0.25, 0.5, 1.0, 2.0, 4.0])); lam = float(rng.choice([0.0, 0.5, 1.0, 1.5, 3.0]))
        tau = float(rng.choice([0.0, 0.0, 0.5, 1.0])); allow = bool(rng.random() < 0.85)
        R = float(np.round(rng.uniform(0, 4) / dt) * dt) if rng.random() < 0.9 else INF
        x = float(np.round(rng.uniform(0.05, 6) / dt) * dt)
        P = Params(mu=mu, alpha=al, ap=ap, lam=lam, tau=tau, allow_p=allow)
        om = float(opt_cost(np.array([x]), R, P, G)[0])
        ob = opt_bf(x, R, P, dt)
        n += 1
        if abs(om - ob) > 1e-9:
            s0 = 1.0 / (1 - al)
            inC = (tau == 0 and lam <= s0 + 1e-12)
            mism_C += inC
            mism.append((om - ob, dict(alpha=al, ap=round(ap, 3), mu=mu, lam=lam, tau=tau, allow_p=allow, R=R, x=x, s0=round(s0, 3), inC=inC), om, ob))
    log(f"(1) model.opt_cost vs brute force (one revocable lease), dt={dt}: {n} instances, mismatches {len(mism)} "
        f"(of which with tau=0 and lam<=s0: {mism_C})")
    for d, kw, om, ob in sorted(mism, key=lambda t: -abs(t[0]))[:12]:
        log(f"   opt_cost-bf={d:+.4f} opt_cost={om:.4f} bf={ob:.4f} {kw}  lam>R? {kw['lam'] > kw['R']}")
    # ---------------- (2) corner: lam > R ----------------
    log("(2) R < lam (OPT cannot pre-warm): 'cold then protected' vs the options in model.opt_cost")
    def opt_prefix(x, R, P):
        """pre-audit model.opt_cost for tau = 0 (no 'cold, then protected' option)"""
        b, a, ap, mu, lam = P.beta, P.alpha, P.ap, P.mu, P.lam
        tail = mu + (x - R)
        if P.allow_p and R - lam >= -1e-12:
            tail = min(tail, b + ap * (x - R))
        return min(x, b + ap * x if P.allow_p else np.inf, b + a * min(x, R) + (tail if x > R else 0.0))
    for kw in [dict(alpha=0.0, ap=0.6, mu=0.25, lam=3.0, R=2.5, x=10.0),
               dict(alpha=0.3, ap=0.9, mu=0.1, lam=1.4, R=1.35, x=8.0),
               dict(alpha=0.5, ap=0.95, mu=0.05, lam=2.0, R=1.9, x=8.0)]:
        P = Params(mu=kw['mu'], alpha=kw['alpha'], ap=kw['ap'], lam=kw['lam'])
        om = float(opt_cost(np.array([kw['x']]), kw['R'], P)[0]); ob = opt_bf(kw['x'], kw['R'], P, dt)
        s0 = 1 / (1 - kw['alpha']); thr = (1 + kw['mu']) / (kw['ap'] - kw['alpha'])
        op = opt_prefix(kw['x'], kw['R'], P)
        log(f"   {kw}: opt_prefix={op:.4f} opt_cost={om:.4f} bf={ob:.4f} prefix-bf={op-ob:+.4f} opt_cost-bf={om-ob:+.4f}; s0={s0:.3f}, (beta+mu)/(ap-alpha)={thr:.3f}, "
            f"condition (C) lam<=s0: {kw['lam'] <= s0}")
    # ---------------- (3) tau > 0: second revocable lease ----------------
    log("(3) tau>0: OPT with a second revocable lease (warm switch) vs one lease; brute force, dt=0.05")
    worst = (0, None)
    cnt = 0; nred = 0
    per_tau = {}
    for al, ap in [(0.0, 0.5), (0.3, 0.8), (0.3, 0.6), (0.5, 0.8)]:
        for mu in [0.5, 2.0, 4.0]:
            for lam in [0.0, 0.5]:
                for tau in [0.5, 1.0, 2.0]:
                    P = Params(mu=mu, alpha=al, ap=ap, lam=lam, tau=tau)
                    for R in [1.0, 2.0, 3.0]:
                        for x in [R + 0.25, R + 0.5, R + 1.0, R + 2.0]:
                            o1 = opt_bf(x, R, P, dt); o2 = opt_bf(x, R, P, dt, two_leases=True)
                            cnt += 1; nred += (o2 < o1 - 1e-9)
                            r = 1 - o2 / o1
                            pt = per_tau.setdefault(tau, [0, 0, 0.0, None])
                            pt[0] += 1; pt[1] += (o2 < o1 - 1e-9)
                            if r > pt[2]:
                                pt[2] = r; pt[3] = dict(alpha=al, ap=ap, mu=mu, lam=lam, R=R, x=x, one=round(float(o1), 4), two=round(float(o2), 4))
                            if r > worst[0]:
                                worst = (r, dict(alpha=al, ap=ap, mu=mu, lam=lam, tau=tau, R=R, x=x, one=round(float(o1), 4), two=round(float(o2), 4)))
    log(f"   {cnt} (params, R, x) points with x > R; OPT strictly lower with two leases at {nred}; "
        f"largest relative reduction {worst[0]:.3%} at {worst[1]}")
    for tau, (c, nr, r, kw) in sorted(per_tau.items()):
        log(f"   tau={tau}: {nr}/{c} points lower; largest reduction {r:.2%} at {kw}")
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'model_opt_bruteforce.txt'), 'w').write('\n'.join(out) + '\n')


if __name__ == '__main__':
    main()
