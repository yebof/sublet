"""Audit (C2, model/solver lens): does the irreversibility of the protected lease matter?

c2_single_site.md Sec. 1 item 3: 'Insurance is irreversible within an episode'; Theorem 2.1 (any
algorithm that commits to protection before its first notice has ratio >= max(2-a, ap/a)) and
Theorem 2.3 (CR* = min(CR_ins, CR_react)) rely on it.  The system model lets the platform release
any lease, so a protected replica could be replaced by a revocable one later (a switch p -> r costs
a load beta and takes lam, like r -> p in the code; rent of the new lease from its takeover).

Extended class INS-REV (tau = 0), exact on the grid, restricted options (so its value is an UPPER
bound on the best ratio of insure-then-revoke algorithms):
  pre-notice plan (s1, s2): protected at s1; planned switch to revocable committed at s2 >= s1
  (takeover s2 + lam), s2 = inf allowed.
  notice before s2 (protected held): stay protected, or switch to revocable at u in [a, R - lam)
     (takeover u + lam < R), then at R: cold (mu, fallback, optional protected at v in [R, R+4])
     or pre-warm back to protected (commit R - lam >= u + lam).
  notice while the switch is loading: keep protected (beta sunk) or take over at s2 + lam < R and react at R.
  notice after the takeover: revocable held; cold or pre-warm as in det_game.
  nothing held at the notice: det_game's post-notice options (state N).
OPT is unchanged (protected-then-revocable is dominated for a clairvoyant OPT).
Reference: det_game.solve_det (dt = 0.1, full plans) = min(CR_ins class, CR_react class).
Output: audit/out/model_reversible_ins.txt"""
import os, sys
os.environ['OMP_NUM_THREADS'] = '1'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from multiprocessing import Pool
from model import Params, opt_cost, make_grids, INF
import det_game
np.seterr(invalid="ignore", over="ignore")


def tails(Xa, R, atR, mu, b, ap, G, lam, warm_ok):
    """cost rows for x > R after holding revocable to R with cost atR at R: cold(v=inf), cold+protected(v), warm."""
    vs = G[(G >= R - 1e-12) & (G <= R + 4 + 1e-9)]
    rows = [atR + mu + (Xa - R)]
    for v in vs:
        rows.append(atR + mu + np.where(Xa <= v, Xa - R, v - R + b + ap * (Xa - v)))
    if warm_ok:
        rows.append(atR + b + ap * (Xa - R))
    return rows


def solve_insrev(P, dt=0.1, T=14.0, Rmax=7.0, s2span=4.0):
    G, X, RG = make_grids(P, dt, T, Rmax)
    b, al, ap, mu, H, lam = P.beta, P.alpha, P.ap, P.mu, P.H, P.lam
    Ts = min(T / 2, Rmax - H - 1.0)
    S1 = G[G <= Ts + 1e-9]
    plans = []
    for s in S1:
        plans.append((s, INF))
        # cap: the adversary must be able to reclaim right after the takeover s2 + lam (cf. bug 3 of the write-up)
        for s2 in G[(G >= s - 1e-12) & (G <= s + s2span + 1e-9) & (G + lam <= Rmax - H - 1.0 + 1e-9)]:
            plans.append((s, s2))
    s1 = np.array([p[0] for p in plans]); s2 = np.array([p[1] for p in plans]); w2 = s2 + lam
    # pre-notice (no reclaim) ratios
    X2 = X[None, :]; S = s1[:, None]; S2 = s2[:, None]; W2 = w2[:, None]
    c = np.where(X2 <= S, X2, S + b + ap * (X2 - S))
    c = np.where(X2 > S2, c + b, c)
    c = np.where(X2 > W2, S + b + ap * (W2 - S) + b + al * (X2 - W2), c)
    W = (c / opt_cost(X, INF, P)[None, :]).max(axis=1)
    for R in RG:
        a = max(0.0, R - H)
        Xa = np.unique(np.concatenate([X[X > a + 1e-12], [a + 2e-7, R + 2e-7, R - lam + 2e-7]]))
        Xa = Xa[Xa > a + 1e-12]
        O = opt_cost(Xa, R, P, G)
        # state N value (copied logic of det_game, tau = 0)
        opts = [Xa[None, :]]
        U = G[G >= a - 1e-12][:, None]
        opts.append(np.where(Xa[None, :] <= U, Xa[None, :], U + b + ap * (Xa[None, :] - U)))
        VN = (np.vstack(opts) / O).max(axis=1).min()
        for u in G[(G >= a - 1e-12) & (G < R - 1e-12)]:
            pre = np.where(Xa <= u, Xa, u + b + al * (np.minimum(Xa, R) - u))
            atR = u + b + al * (R - u)
            M = np.vstack([np.where(Xa > R, r, pre) for r in tails(Xa, R, atR, mu, b, ap, G, lam, R - lam >= u - 1e-12)])
            if R - lam >= u - 1e-12:
                M[-1] = np.where(Xa > R, M[-1], np.where(Xa > R - lam, pre + b, pre))
            VN = min(VN, (M / O).max(axis=1).min())
        # state P options as functions g(x) with the sunk cost at a removed (cost = C + g)
        gP = [ap * (Xa - a)]
        for u in G[(G >= a - 1e-12) & (G + lam < R - 1e-12)]:
            w = u + lam
            pre = np.where(Xa <= u, ap * (Xa - a), np.where(Xa <= w, ap * (Xa - a) + b, ap * (w - a) + b + al * (np.minimum(Xa, R) - w)))
            atR = ap * (w - a) + b + al * (R - w)
            warm_ok = R - lam >= w - 1e-12
            rows = tails(Xa, R, atR, mu, b, ap, G, lam, warm_ok)
            for k, r in enumerate(rows):
                g = np.where(Xa > R, r, pre)
                if warm_ok and k == len(rows) - 1:
                    g = np.where(Xa > R, r, np.where(Xa > R - lam, pre + b, pre))
                gP.append(g)
        gP = np.vstack(gP)
        # revocable-held options (cost = C + g), C = sunk cost at a
        pre = al * (np.minimum(Xa, R) - a)
        atR = al * (R - a)
        warm_ok = R - lam >= a - 1e-12
        rows = tails(Xa, R, atR, mu, b, ap, G, lam, warm_ok)
        gR = []
        for k, r in enumerate(rows):
            g = np.where(Xa > R, r, pre)
            if warm_ok and k == len(rows) - 1:
                g = np.where(Xa > R, r, np.where(Xa > R - lam, pre + b, pre))
            gR.append(g)
        gR = np.vstack(gR)
        val = np.full(len(plans), VN)
        held = s1 < a - 1e-12
        # case 1: protected held, switch not yet committed
        m1 = held & (s2 >= a - 1e-12)
        if m1.any():
            Cs = s1[m1] + b + ap * (a - s1[m1])
            uC, inv = np.unique(np.round(Cs, 12), return_inverse=True)
            vals = np.array([((Cv + gP) / O).max(axis=1).min() for Cv in uC])
            val[m1] = vals[inv]
        # case 3: revocable held since takeover w2 <= a
        m3 = held & (w2 <= a + 1e-12)
        if m3.any():
            Cs = s1[m3] + b + ap * (w2[m3] - s1[m3]) + b + al * (a - w2[m3])
            val[m3] = np.array([((Cv + gR) / O).max(axis=1).min() for Cv in Cs])
        # case 2: switch committed, takeover pending at the notice
        m2 = np.where(held & (s2 < a - 1e-12) & (w2 > a + 1e-12))[0]
        for i in m2:
            C = s1[i] + b + ap * (a - s1[i]) + b
            keep = C + ap * (Xa - a)
            best = (keep / O).max()
            if w2[i] < R - 1e-12:
                wi = w2[i]
                pre = np.where(Xa <= wi, C + ap * (Xa - a), C + ap * (wi - a) + al * (np.minimum(Xa, R) - wi))
                atR = C + ap * (wi - a) + al * (R - wi)
                wok = R - lam >= a - 1e-12
                rows = tails(Xa, R, atR, mu, b, ap, G, lam, wok)
                for k, r in enumerate(rows):
                    g = np.where(Xa > R, r, pre)
                    if wok and k == len(rows) - 1:
                        g = np.where(Xa > R, r, np.where(Xa > R - lam, pre + b, pre))
                    best = min(best, (g / O).max())
            val[i] = best
        W = np.maximum(W, val)
    k = int(np.argmin(W))
    kinf = [i for i in range(len(plans)) if np.isinf(s2[i])]
    kfin = [i for i in range(len(plans)) if np.isfinite(s2[i])]
    jf = kfin[int(np.argmin(W[kfin]))]
    return dict(CR=float(W[k]), plan=(float(s1[k]), float(s2[k])), CR_s2inf=float(W[kinf].min()),
                CR_s2fin=float(W[jf]), plan_fin=(float(s1[jf]), float(s2[jf])))


def run(kw):
    P = Params(**kw)
    ref = det_game.solve_det(P, dt=0.1, T=14.0, Rmax=7.0, return_detail=True)
    r = solve_insrev(P, dt=0.1, T=14.0, Rmax=7.0)
    return kw, ref, r


if __name__ == '__main__':
    cases = [dict(alpha=0.3, ap=0.6, mu=2.0, lam=0.5, H=0.0), dict(alpha=0.3, ap=0.6, mu=1.0, lam=0.5, H=0.0),
             dict(alpha=0.3, ap=0.6, mu=2.0, lam=0.5, H=0.5), dict(alpha=0.2, ap=0.4, mu=1.0, lam=0.5, H=0.0),
             dict(alpha=0.5, ap=0.8, mu=4.0, lam=1.0, H=0.0), dict(alpha=0.3, ap=0.7, mu=4.0, lam=0.5, H=0.0),
             dict(alpha=0.2, ap=0.5, mu=4.0, lam=1.0, H=1.0)]
    lines = ["params | det_game: CR*, CR_ins class, CR_react class | INS-REV class (reversible insurance): CR, best plan (s1, s2), best with s2=inf (post-notice switch only), best with finite s2 (plan) | CR*_reversible = min(CR_react, INS-REV)"]
    with Pool(4) as p:
        for kw, ref, r in p.imap(run, cases):
            crr = min(ref['CR_react_class'], r['CR'])
            lines.append(f"{kw} | {ref['CR']:.4f}, {ref['CR_ins_class']:.4f}, {ref['CR_react_class']:.4f} | {r['CR']:.4f}, {r['plan']}, {r['CR_s2inf']:.4f}, {r['CR_s2fin']:.4f} {r['plan_fin']} | {crr:.4f} (change {crr - ref['CR']:+.4f})")
            print(lines[-1], flush=True)
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'model_reversible_ins.txt'), 'w').write('\n'.join(lines) + '\n')
