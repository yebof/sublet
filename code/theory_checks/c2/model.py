"""C2 single-site rent / buy / insure game: model primitives.

Normalization: fallback price q = 1 per unit time of demand.
Parameters (all in units where q = 1; beta is usually normalized to 1):
  beta   load cost of any new replica (lease purchase or switch), paid at commitment
  alpha  revocable lease price per unit time (alpha = a/q), 0 <= alpha < 1
  ap     protected lease price per unit time (ap = a_p/q), alpha < ap
  mu     stranded cost: paid when the replica serving live demand is reclaimed
         and no replacement replica is warm at the reclaim time
  H      notice: the end R of the revocable supply window is revealed at max(0, R - H)
  lam    load time of a replacement replica (handover r -> p completes lam after commit)
  tau    guaranteed period: a revocable lease bought at s ends at E = max(R, s + tau)
  allow_p  False removes the protected option for everyone (recovers RRL)

Environment (oblivious adversary): R in [0, inf] (end of revocable supply window),
x in (0, inf) (end of demand; demand = 1 on [0, x), not announced).
"""
import numpy as np
from dataclasses import dataclass, replace

INF = np.inf


@dataclass(frozen=True)
class Params:
    mu: float = 1.0
    alpha: float = 0.0
    ap: float = 0.5
    H: float = 0.0
    lam: float = 0.0
    tau: float = 0.0
    beta: float = 1.0
    allow_p: bool = True
    short_windows: bool = False   # False: R >= H (report.md convention); True: windows shorter than H announced at t=0

    def with_(self, **kw):
        return replace(self, **kw)


def opt_cost(x, R, P, ugrid=None):
    """Offline optimum for demand end(s) x (array) and window end R (scalar, may be inf).
    Options: fallback; protected from 0; revocable bought at u < min(R, x), held to
    E_u = max(R, u + tau), then (if x > E_u) cold reclaim (mu + fallback), cold reclaim followed
    by protected at E_u (mu + beta + ap per unit time), or warm switch to protected (beta + ap per
    unit time; needs E_u - lam >= u).  At most one revocable lease per episode (for tau = 0 a
    second one is useless; for tau > 0 this is a restriction of the model, see c2_single_site.md).
    The 'cold, then protected' option was added after the audit (design/theory/audit_c2.md); it
    matters only when the warm switch is infeasible (E_u - lam < u) and E_u > (beta+mu)/(ap-alpha),
    which never happens under condition (C) nor at any parameter point used in the write-up."""
    x = np.asarray(x, dtype=float)
    b, a, ap, mu, lam, tau = P.beta, P.alpha, P.ap, P.mu, P.lam, P.tau
    c = x.copy()
    if P.allow_p:
        c = np.minimum(c, b + ap * x)
    if R <= 0:
        return c
    if np.isinf(R):
        return np.minimum(c, b + a * x)
    if tau == 0 or ugrid is None:
        us = np.array([0.0])
    else:
        us = ugrid[ugrid < R]
    for u in us:
        E = max(R, u + tau)
        cov = np.minimum(x, E)
        base = u + b + a * (cov - u)
        tail = mu + (x - E)
        if P.allow_p:
            tail = np.minimum(tail, mu + b + ap * (x - E))      # cold reclaim, then protected at E
            if E - lam >= u - 1e-12:
                tail = np.minimum(tail, b + ap * (x - E))       # warm switch (pre-warm)
        cu = np.where(x > E, base + tail, base)
        cu = np.where(x > u, cu, np.inf)
        c = np.minimum(c, cu)
    return c


def make_grids(P, dt, T, Rmax):
    G = np.round(np.arange(0.0, T + dt / 2, dt), 10)
    eps = 1e-7
    X = np.concatenate([G[1:] - eps, G + eps, [T + 1, 2 * T, 4 * T, 10 * T, 1e3, 1e5]])
    X = np.unique(X[X > 0])
    RG0 = G[G <= Rmax + 1e-9]
    if not P.short_windows:
        RG0 = RG0[RG0 >= P.H - 1e-12]
    RG = np.unique(np.concatenate([RG0, RG0 + eps]))   # reclaim just after a decision point
    return G, X, RG
