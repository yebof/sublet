"""Closed-form adversary families for the C2 game (continuous time, no discretization of the
adversary).  They give a rigorous lower bound on the deterministic CR (Theorem 3 in the write-up):

  CR* >= min( CR_ins , LB_react ),   CR_ins = max(2 - alpha, ap/alpha)
  LB_react = inf_s max( F1(s), F2(s) )
  F1(s): no reclaim, demand ends just after the revocable purchase at s
  F2(s): reclaim right after the purchase: the window ends at R = E = s + D, D = max(H, tau),
         announced at max(s, E - H)+; value = min over the algorithm's reaction (cold / warm) of
         the worst demand end among {E+ , (E - lam)+ (only for warm), E + t after a cold reclaim}.
         For tau = 0 this is Theorem 3.  For tau > 0 it is a lower bound only in the model with one
         revocable lease per episode (a second lease bought before R can outlive R; see
         design/theory/audit_c2.md).
"""
import numpy as np
np.seterr(invalid='ignore', over='ignore')
from model import Params, opt_cost, INF


def cr_ins(P):
    if not P.allow_p:
        return INF
    return max(2 - P.alpha, P.ap / P.alpha) if P.alpha > 0 else INF


def F1(s, P):
    b, a = P.beta, P.alpha
    return (s + b) / np.minimum(s, b + a * s)


def F2_parts(s, P):
    """returns (cold, warm) values for threshold s (scalar)."""
    b, a, ap, mu, H, lam, tau = P.beta, P.alpha, P.ap, P.mu, P.H, P.lam, P.tau
    D = max(H, tau)
    E = s + D
    # OPT just after E with window end R = E (OPT's lease from 0 ends at max(E, tau) = E)
    oE = float(opt_cost(np.array([E + 1e-9]), E, P, None if tau == 0 else np.linspace(0, E, 201))[0])
    cold = (s + b + a * D + mu) / oE
    if P.allow_p:
        cold = max(cold, cold_tail(s, P))
    warm = INF
    if P.allow_p and H >= lam - 1e-12:
        y = E - lam
        oy = min(y, b + a * y) if y > 0 else 1e-12
        w1 = (s + b + a * (y - s) + b) / oy if (lam > 0 and y >= s - 1e-12) else 0.0   # commit wasted (x just after commit < E)
        w2 = (s + b + a * D + b) / oE
        warm = max(w1, w2)
    return cold, warm


_TT = np.concatenate([np.linspace(1e-6, 12, 1201), np.geomspace(12.5, 1e5, 60)])
_TH = np.concatenate([np.linspace(0, 12, 241), [np.inf]])


def cold_tail(s, P):
    """After a cold reclaim at E = s + D the algorithm is on fallback and buys protected at E + theta
    (theta >= 0 or never).  Value = min_theta max_t ratio at demand end E + t (t > 0)."""
    b, a, ap, mu, H, tau = P.beta, P.alpha, P.ap, P.mu, P.H, P.tau
    D = max(H, tau); E = s + D
    O = opt_cost(E + _TT, E, P, None if tau == 0 else np.linspace(0, E, 201))
    A0 = s + b + a * D + mu
    th = _TH[:, None]; t = _TT[None, :]
    tail = np.where(t <= th, t, th + b + ap * (t - th))
    tail = np.where(np.isinf(th), t, tail)
    # demand ending just after the purchase at theta: include t = theta+ explicitly
    w = ((A0 + tail) / O[None, :]).max(axis=1)
    Ot = opt_cost(E + _TH[:-1] + 1e-9, E, P, None if tau == 0 else np.linspace(0, E, 201))
    w[:-1] = np.maximum(w[:-1], (A0 + _TH[:-1] + b) / Ot)
    return float(w.min())


def lb_react(P, smax=8.0, n=321, nref=161, tail=True):
    """inf over the algorithm's first (no-notice) revocable purchase time s of max(F1, F2), on a grid.
    tail=True (default since the audit, design/theory/audit_c2.md) adds a geometric grid on
    (smax, 1e4] and the never-buy limit s = inf, whose ratio is 1/alpha (R = inf, x -> inf); the
    minimiser is beyond smax = 8 when mu is large (e.g. alpha = 0.5, mu = 10).  tail=False is the
    pre-audit window [1e-3, smax]."""
    f = lambda s: max(F1(s, P), min(F2_parts(s, P)))
    ss = np.linspace(1e-3, smax, n)
    if tail:
        ss = np.concatenate([ss, np.geomspace(smax * 1.05, 1e4, 80)])
    vals = np.array([f(s) for s in ss])
    i = int(np.argmin(vals))
    ss2 = np.linspace(ss[max(i - 1, 0)], ss[min(i + 1, len(ss) - 1)], nref)
    v2 = np.array([f(s) for s in ss2])
    j = int(np.argmin(v2))
    v, sarg = float(v2[j]), float(ss2[j])
    if tail and P.alpha > 0 and 1.0 / P.alpha < v:
        v, sarg = 1.0 / P.alpha, INF
    return v, sarg


def lb_total(P):
    l, s = lb_react(P)
    return min(cr_ins(P), l), l, s


if __name__ == '__main__':
    for kw in [dict(mu=1, H=0, alpha=0, allow_p=False), dict(mu=4, H=1, alpha=0, allow_p=False),
               dict(mu=4, lam=0.5, H=3, alpha=0.3, ap=0.6)]:
        P = Params(**kw)
        print(kw, lb_total(P))
