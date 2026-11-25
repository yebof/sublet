"""Audit (C2, model/solver lens): sensitivity of the notice threshold H* to the cost convention for
the pre-warm switch revocable -> protected.

In c2_single_site.md (Sec. 1, items 4-5) every load costs the same beta, and for a fresh purchase from
fallback 'the load delay is folded into beta; demand stays on fallback while loading'.  A pre-warm
load does not leave demand on fallback (the revocable lease serves until the takeover, and the code
bills protected rent only from the takeover), so under the document's own folding convention
(beta = fees + lam, the fallback cost of the load delay at q = 1) a switch costs
beta_w = fees + (rent of the new lease during the load, if billed) = beta - lam + ap*lam or beta - lam,
i.e. beta_w lies in [beta - lam, beta - (1 - ap) lam]; with negligible fees beta_w / beta is in [0, ap].  This script copies
det_game.solve_det and model.opt_cost with ONE change: the commit of a switch r -> p (online
pre-warm, planned pre-notice upgrade, and OPT's pre-warm) costs bw instead of beta.  Fresh loads
(protected from fallback, revocable) still cost beta.  bw = beta reproduces det_game exactly.

For each (bw, lam) the exact threshold H*_exact = first H on the 0.05 grid with exact CR <= 2-a+1e-4
(dt = 0.05, alpha = 1/3 so that s0 = 1.5 lies on the grid; bisection, CR is non-increasing in H).
Corollary 5.3 / Section 9 claim H* = mu/(2(1-alpha)) = 1.5 for every lam > 0 (mu = 2 beta).
Run without arguments, then with --extra (appends the bw = ap block).
Output: audit/out/model_switch_cost.txt"""
import os, sys
os.environ['OMP_NUM_THREADS'] = '1'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from multiprocessing import Pool
from model import Params, make_grids, INF
import det_game
np.seterr(invalid="ignore", over="ignore")


def opt_cost_bw(x, R, P, bw, ugrid=None):
    x = np.asarray(x, dtype=float)
    b, a, ap, mu, lam, tau = P.beta, P.alpha, P.ap, P.mu, P.lam, P.tau
    c = x.copy()
    if P.allow_p:
        c = np.minimum(c, b + ap * x)
    if R <= 0:
        return c
    if np.isinf(R):
        return np.minimum(c, b + a * x)
    us = np.array([0.0]) if (tau == 0 or ugrid is None) else ugrid[ugrid < R]
    for u in us:
        E = max(R, u + tau)
        cov = np.minimum(x, E)
        base = u + b + a * (cov - u)
        tail = mu + (x - E)
        if P.allow_p:
            tail = np.minimum(tail, mu + b + ap * (x - E))        # cold, then fresh protected (always feasible)
            if E - lam >= u - 1e-12:
                tail = np.minimum(tail, bw + ap * (x - E))        # pre-warm switch
        cu = np.where(x > E, base + tail, base)
        cu = np.where(x > u, cu, np.inf)
        c = np.minimum(c, cu)
    return c


def solve_det_bw(P, bw, dt=0.1, T=10.0, Rmax=6.0, Ts=None):
    """det_game.solve_det with full_plans=False (no planned pre-notice upgrades) and switch cost bw."""
    G, X, RG = make_grids(P, dt, T, Rmax)
    Ts = Ts if Ts is not None else min(T / 2, Rmax - P.H - 1.0)
    b, al, ap, mu, H, lam, tau = P.beta, P.alpha, P.ap, P.mu, P.H, P.lam, P.tau
    S1 = G[G <= Ts + 1e-9]
    typ = [0] + ([1] * len(S1) if P.allow_p else []) + [2] * len(S1)
    s1 = [INF] + (list(S1) if P.allow_p else []) + list(S1)
    typ = np.array(typ); s1 = np.array(s1)
    npl = len(typ)
    sidx = np.searchsorted(S1, np.where(np.isfinite(s1), s1, 0) - 1e-9)
    X2 = X[None, :]; S = s1[:, None]; t = typ[:, None]
    cp = np.where(X2 <= S, X2, S + b + ap * (X2 - S))
    cr = np.where(X2 <= S, X2, S + b + al * (X2 - S))
    C = np.where(t == 0, X2, np.where(t == 1, cp, cr))
    W = (C / opt_cost_bw(X, INF, P, bw)[None, :]).max(axis=1)
    for R in RG:
        a = max(0.0, R - H)
        Xa = np.unique(np.concatenate([X[X > a + 1e-12], [a + 2e-7, R + 2e-7, R - lam + 2e-7]]))
        Xa = Xa[Xa > a + 1e-12]
        O = opt_cost_bw(Xa, R, P, bw, G)
        opts = [Xa[None, :]]
        if P.allow_p:
            U = G[G >= a - 1e-12][:, None]
            opts.append(np.where(Xa[None, :] <= U, Xa[None, :], U + b + ap * (Xa[None, :] - U)))
        VN = (np.vstack(opts) / O).max(axis=1).min()
        for u in G[(G >= a - 1e-12) & (G < R - 1e-12)]:
            E = max(R, u + tau)
            pre = np.where(Xa <= u, Xa, u + b + al * (np.minimum(Xa, E) - u))
            atE = u + b + al * (E - u)
            M = det_game._cold_tails(Xa, E, atE, mu, b, ap, G, P.allow_p)
            M = np.where(Xa[None, :] > E, M, pre[None, :])
            if P.allow_p and E - lam >= u - 1e-12:
                d = E - lam
                wv = np.where(Xa > E, atE + bw + ap * (Xa - E), np.where(Xa > d, pre + bw, pre))
                M = np.vstack([M, wv[None, :]])
            VN = min(VN, (M / O).max(axis=1).min())
        VR = np.full(len(S1), np.nan)
        for i, s in enumerate(S1):
            if s >= a - 1e-12:
                break
            E = max(R, s + tau)
            Cc = s + b + al * (a - s)
            pre = Cc + al * (np.minimum(Xa, E) - a)
            atE = Cc + al * (E - a)
            M = det_game._cold_tails(Xa, E, atE, mu, b, ap, G, P.allow_p)
            M = np.where(Xa[None, :] > E, M, pre[None, :])
            if P.allow_p and E - lam >= a - 1e-12:
                d = E - lam
                wv = np.where(Xa > E, atE + bw + ap * (Xa - E), np.where(Xa > d, pre + bw, pre))
                M = np.vstack([M, wv[None, :]])
            VR[i] = (M / O).max(axis=1).min()
        val = np.full(npl, VN)
        before = np.isfinite(s1) & (s1 < a - 1e-12)
        mp = before & (typ == 1)
        if mp.any():
            sp = s1[mp][:, None]
            val[mp] = ((sp + b + ap * (Xa[None, :] - sp)) / O).max(axis=1)
        mr = before & (typ == 2)
        val[mr] = VR[sidx[mr]]
        W = np.maximum(W, val)
    k = int(np.argmin(W))
    plan = ('none',) if typ[k] == 0 else (('p', float(s1[k])) if typ[k] == 1 else ('r', float(s1[k])))
    return dict(CR=float(W[k]), plan=plan)


def cr_at(args):
    kw, bw, H, dt = args
    P = Params(H=H, **kw)
    Rmax = H + 6.0
    return solve_det_bw(P, bw, dt=dt, T=Rmax + 7.0, Rmax=Rmax)


def hstar_exact(args):
    kw, bw, dt = args
    c = 2 - kw['alpha']
    Hs = np.round(np.arange(0, 8.0 + 1e-9, 0.05), 10)
    ok = lambda H: cr_at((kw, bw, H, dt))['CR'] <= c + 1e-4
    lo, hi = 0, len(Hs) - 1
    if not ok(Hs[hi]):
        return kw, bw, np.inf
    if ok(Hs[0]):
        return kw, bw, 0.0
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if ok(Hs[mid]):
            hi = mid
        else:
            lo = mid
    return kw, bw, float(Hs[hi])


def extra():
    """bw = ap: the switch cost when fees are negligible and the new lease is billed from the commit
    (fresh load beta = fees + lam (fallback during the load); switch = fees + ap*lam).  Appends to the output."""
    lines = ["extra: bw = ap = 0.8 (consistent switch cost with negligible fees), alpha=1/3, lam=0.5"]
    jobs = [(dict(alpha=1/3, ap=0.8, mu=mu, lam=0.5), 0.8, 0.05) for mu in [1.5, 1.6, 2.0]]
    with Pool(3) as p:
        for kw, bw, hs in p.imap(hstar_exact, jobs):
            lines.append(f"mu={kw['mu']} lam={kw['lam']} bw={bw}: H*_exact={hs:.2f}   mu/(2(1-alpha))={kw['mu'] / (2 * (1 - kw['alpha'])):.3f}")
            print(lines[-1], flush=True)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'model_switch_cost.txt'), 'a') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__' and '--extra' in sys.argv:
    extra()
elif __name__ == '__main__':
    lines = []
    log = lambda s: (print(s, flush=True), lines.append(s))
    # sanity: bw = beta reproduces det_game (full_plans=False)
    for kw, H in [(dict(alpha=1/3, ap=0.8, mu=2.0, lam=0.5), 1.0), (dict(alpha=0.3, ap=0.7, mu=2.0, lam=0.5), 0.25),
                  (dict(alpha=0.0, ap=0.5, mu=4.0, lam=0.5), 0.0)]:
        P = Params(H=H, **kw)
        r0 = det_game.solve_det(P, dt=0.05, T=13.0, Rmax=H + 6.0, full_plans=False)['CR']
        r1 = solve_det_bw(P, 1.0, dt=0.05, T=13.0, Rmax=H + 6.0)['CR']
        log(f"sanity bw=beta {kw} H={H}: det_game {r0:.5f}  variant {r1:.5f}  diff {r1 - r0:+.2e}")
    base = dict(alpha=1/3, ap=0.8, mu=2.0)
    jobs = [(dict(base, lam=lam), bw, 0.05) for bw in [1.0, 0.6, 0.2] for lam in [0.25, 0.5, 1.0]]
    jobs += [(dict(alpha=1/3, ap=0.8, mu=1.0, lam=lam), bw, 0.05) for bw in [1.0, 0.2] for lam in [0.25, 0.5]]
    log("exact threshold (dt=0.05, H grid 0.05), alpha=1/3, ap=0.8, beta=1; claim (Cor. 5.1/5.3, Sec. 9): H* = mu/(2(1-alpha)) for every lam > 0")
    with Pool(4) as p:
        for kw, bw, hs in p.imap(hstar_exact, jobs):
            log(f"mu={kw['mu']} lam={kw['lam']} bw={bw}: H*_exact={hs:.2f}   mu/(2(1-alpha))={kw['mu'] / (2 * (1 - kw['alpha'])):.3f}")
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'model_switch_cost.txt'), 'w').write('\n'.join(lines) + '\n')
