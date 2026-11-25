"""Exact (up to discretization) deterministic minimax for the C2 single-site game.

A deterministic online algorithm is a pre-notice plan plus, for every possible notice
(i.e. every window end R), a post-notice plan.  Before the notice the algorithm only learns
whether demand is still on, so a pre-notice plan is one of
   none            : stay on fallback until notice
   ('p', s1)       : buy protected at s1
   ('r', s1, d2)   : buy revocable at s1, commit a planned switch to protected at d2 >= s1
                     (handover at d2 + lam), d2 = inf means no planned switch.
After the notice (time a = max(0, R - H), R known) the remaining information is only the
demand end, so the post-notice plan is again a fixed schedule; it is chosen optimally for each R
(the game separates over R).  Post-notice plans (state at time a):
   state N (nothing held):  fallback forever | protected at u >= a |
                            revocable at u in [a, R), then warm switch (commit at E-lam) or
                            cold reclaim (pay mu) followed by protected at v >= E or never
   state Rv (revocable held, no committed switch): warm switch (commit at E-lam, needs E-lam >= a)
                            or cold reclaim then protected at v >= E or never
   committed / protected states: no decision left.
Dominance facts used to restrict the post-notice plans (proved in the write-up, Lemma 1):
latest commit E-lam is optimal for a warm switch; voluntary release never helps; after a cold
reclaim only 'protected at v' matters.

Usage: python det_game.py  (runs the self-test against the RRL formulas)
"""
import numpy as np
from model import Params, opt_cost, make_grids, INF
np.seterr(invalid="ignore", over="ignore")


def _minmax(cost, O):
    """cost: (n_opt, nx), O: (nx,) -> (value, argmin)"""
    w = (cost / O).max(axis=1)
    i = int(np.argmin(w))
    return w[i], i


def _cold_tails(Xa, E, atE, mu, b, ap, G, allow_p):
    """matrix of costs for x > E after a cold reclaim at E, one row per v in {inf} U {G >= E}"""
    vs = np.array([INF] + (list(G[G >= E - 1e-12]) if allow_p else []))
    X2 = Xa[None, :]
    V = vs[:, None]
    tail = np.where(X2 <= V, X2 - E, V - E + b + ap * (X2 - V))
    tail[0] = Xa - E
    return atE + mu + tail


def solve_det(P, dt=0.1, T=10.0, Rmax=6.0, Ts=None, full_plans=True, return_detail=False):
    G, X, RG = make_grids(P, dt, T, Rmax)
    Ts = Ts if Ts is not None else min(T / 2, Rmax - P.H - 1.0)   # adversary must be able to reclaim after any purchase
    b, al, ap, mu, H, lam, tau = P.beta, P.alpha, P.ap, P.mu, P.H, P.lam, P.tau
    S1 = G[G <= Ts + 1e-9]
    # ---- plan arrays: typ 0 none, 1 protected at s1, 2 revocable at s1 with planned commit d2 ----
    typ = [0]; s1 = [INF]; d2 = [INF]
    if P.allow_p:
        typ += [1] * len(S1); s1 += list(S1); d2 += [INF] * len(S1)
    for s in S1:
        typ.append(2); s1.append(s); d2.append(INF)
        if P.allow_p and full_plans:
            ds = G[G >= s - 1e-12]
            typ += [2] * len(ds); s1 += [s] * len(ds); d2 += list(ds)
    typ = np.array(typ); s1 = np.array(s1); d2 = np.array(d2)
    npl = len(typ)
    sidx = np.searchsorted(S1, np.where(np.isfinite(s1), s1, 0) - 1e-9)

    def plan_cost(sel, x):
        """pre-notice-plan cost (no reclaim before x) for plans sel, x: (nx,) -> (nsel, nx)"""
        t = typ[sel][:, None]; s = s1[sel][:, None]; d = d2[sel][:, None]; X2 = x[None, :]
        w = d + lam
        cp = np.where(X2 <= s, X2, s + b + ap * (X2 - s))
        cr = np.where(X2 <= s, X2, s + b + al * (X2 - s))
        cr = np.where(X2 > d, cr + b, cr)
        cr = np.where(X2 > w, s + b + al * (w - s) + b + ap * (X2 - w), cr)
        c = np.where(t == 1, cp, cr)
        return np.where(t == 0, X2, c)

    Oinf = opt_cost(X, INF, P)
    W = np.empty(npl)
    for ch in np.array_split(np.arange(npl), max(1, npl // 2000)):
        W[ch] = (plan_cost(ch, X) / Oinf).max(axis=1)

    for R in RG:
        a = max(0.0, R - H)
        Xa = np.unique(np.concatenate([X[X > a + 1e-12], [a + 2e-7, R + 2e-7, R - lam + 2e-7]]))
        Xa = Xa[Xa > a + 1e-12]
        O = opt_cost(Xa, R, P, G)
        # ---- state N (nothing held at notice) ----
        opts = [Xa[None, :]]
        if P.allow_p:
            U = G[G >= a - 1e-12][:, None]
            opts.append(np.where(Xa[None, :] <= U, Xa[None, :], U + b + ap * (Xa[None, :] - U)))
        VN = (np.vstack(opts) / O).max(axis=1).min()
        for u in G[(G >= a - 1e-12) & (G < R - 1e-12)]:
            E = max(R, u + tau)
            pre = np.where(Xa <= u, Xa, u + b + al * (np.minimum(Xa, E) - u))
            atE = u + b + al * (E - u)
            M = _cold_tails(Xa, E, atE, mu, b, ap, G, P.allow_p)
            M = np.where(Xa[None, :] > E, M, pre[None, :])
            if P.allow_p and E - lam >= u - 1e-12:
                d = E - lam
                wv = np.where(Xa > E, atE + b + ap * (Xa - E), np.where(Xa > d, pre + b, pre))
                M = np.vstack([M, wv[None, :]])
            VN = min(VN, (M / O).max(axis=1).min())
        # ---- state Rv (revocable held, no committed switch) ----
        VR = np.full(len(S1), np.nan)
        for i, s in enumerate(S1):
            if s >= a - 1e-12:
                break
            E = max(R, s + tau)
            C = s + b + al * (a - s)
            pre = C + al * (np.minimum(Xa, E) - a)
            atE = C + al * (E - a)
            M = _cold_tails(Xa, E, atE, mu, b, ap, G, P.allow_p)
            M = np.where(Xa[None, :] > E, M, pre[None, :])
            if P.allow_p and E - lam >= a - 1e-12:
                d = E - lam
                wv = np.where(Xa > E, atE + b + ap * (Xa - E), np.where(Xa > d, pre + b, pre))
                M = np.vstack([M, wv[None, :]])
            VR[i] = (M / O).max(axis=1).min()
        # ---- assemble ----
        val = np.full(npl, VN)
        before = np.isfinite(s1) & (s1 < a - 1e-12)
        mp = before & (typ == 1)
        if mp.any():
            sp = s1[mp][:, None]
            val[mp] = ((sp + b + ap * (Xa[None, :] - sp)) / O).max(axis=1)
        mr = before & (typ == 2) & (d2 >= a - 1e-12)
        val[mr] = VR[sidx[mr]]
        mc = np.where(before & (typ == 2) & (d2 < a - 1e-12))[0]
        for ch in np.array_split(mc, max(1, len(mc) // 2000)) if len(mc) else []:
            s = s1[ch][:, None]; d = d2[ch][:, None]; X2 = Xa[None, :]
            E = np.maximum(R, s + tau); w = d + lam
            c_ok = np.where(X2 <= w, s + b + al * (X2 - s) + b, s + b + al * (w - s) + b + ap * (X2 - w))
            c_late = np.where(X2 <= E, s + b + al * (X2 - s) + b,
                              np.where(X2 <= w, s + b + al * (E - s) + b + mu + (X2 - E),
                                       s + b + al * (E - s) + b + mu + (w - E) + ap * (X2 - w)))
            c = np.where(w <= E + 1e-12, c_ok, c_late)
            val[ch] = (c / O).max(axis=1)
        W = np.maximum(W, val)
    k = int(np.argmin(W))
    plan = ('none',) if typ[k] == 0 else (('p', float(s1[k])) if typ[k] == 1 else ('r', float(s1[k]), float(d2[k])))
    out = dict(CR=float(W[k]), plan=plan)
    if return_detail:
        out['W'] = W; out['typ'] = typ; out['s1'] = s1; out['d2'] = d2
        # best value among plans that commit to protected before any notice
        ins = (typ == 1) | ((typ == 2) & np.isfinite(d2))
        out['CR_ins_class'] = float(W[ins].min()) if ins.any() else INF
        out['CR_react_class'] = float(W[~ins].min())
    return out


def rrl_closed(mu, H, alpha=0.0):
    """Report section 5A/5B formulas (B = 1, mu_A = mu_O = mu)."""
    if alpha == 0:
        if H == 0:
            return 1 + np.sqrt(1 + mu)
        s = (-H + np.sqrt((2 - H) ** 2 + 4 * mu)) / 2
        return 1 + max(1.0, s)          # valid for mu <= 2
    # H = 0, alpha > 0: positive root of (1-a)s^2 - a(1+mu)s - (1+mu) = 0
    A, Bq, Cq = 1 - alpha, -alpha * (1 + mu), -(1 + mu)
    s = (-Bq + np.sqrt(Bq ** 2 - 4 * A * Cq)) / (2 * A)
    return 1 + (1 + mu) / s


if __name__ == '__main__':
    import time
    t0 = time.time()
    print("RRL special case (allow_p=False), dt=0.05")
    for mu, H, al in [(1, 0, 0), (2, 0, 0), (0.5, 0, 0), (1, 0, 0.3), (1, 0.25, 0), (1, 0.5, 0), (2, 0.5, 0)]:
        P = Params(mu=mu, H=H, alpha=al, allow_p=False)
        r = solve_det(P, dt=0.05, T=8, Rmax=5)
        print(f"mu={mu} H={H} alpha={al}: brute={r['CR']:.4f} plan={r['plan']} closed={rrl_closed(mu,H,al):.4f}", flush=True)
    print(f"time {time.time()-t0:.1f}s")
