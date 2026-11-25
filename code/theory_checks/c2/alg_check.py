"""Independent check of the explicit algorithm ALG_c used in the proof of Theorem 5 (phase
transition).  Direct cost simulation on a fine (R, x) grid; does not use det_game.py.

ALG_c(s0 = beta/(1-alpha), Hc, react):
  no notice yet           : buy revocable at s0
  notice while holding r  : react at R: 'cold' (pay mu, stay on fallback forever) or
                            'warm' (commit protected at R - lam, handover at R)
  notice before purchase  : if R >= s0 + Hc: same as above (buy r at s0, react at R)
                            else: stay on fallback, buy protected at max(R, s0)
Output: out/alg_check.txt
"""
import itertools
import numpy as np
from model import Params, opt_cost, INF
np.seterr(invalid='ignore', over='ignore')


def alg_cost(R, x, P, s, Hc, react):
    b, al, ap, mu, H, lam = P.beta, P.alpha, P.ap, P.mu, P.H, P.lam
    a = R - H
    x = np.asarray(x, float)
    plan = np.where(x <= s, x, s + b + al * (x - s))          # cost while no reclaim hits
    if a >= s or R >= s0_plus(s, Hc):
        # holds r from s (or will), window ends at R
        if R <= s:      # cannot happen when R >= s + Hc
            raise ValueError
        if react == 'cold':
            after = s + b + al * (R - s) + mu + (x - R)
            return np.where(x <= R, plan, after)
        d = R - lam
        c = np.where((x > d) & (x <= R), plan + b, plan)
        after = s + b + al * (R - s) + b + ap * (x - R)
        return np.where(x <= R, c, after)
    v = max(R, s)
    return np.where(x <= v, x, v + b + ap * (x - v))


def s0_plus(s, Hc):
    return s + Hc


def worst(P, react, Hc=None, Rmax=12.0, dR=0.01):
    b, al = P.beta, P.alpha
    s = b / (1 - al)
    m = min(P.mu, b) if react == 'warm' else P.mu
    Hc = m / (2 * (1 - al)) if Hc is None else Hc
    xs_base = np.concatenate([np.linspace(1e-4, 30, 6001), np.geomspace(31, 1e6, 80)])
    w = 0.0; arg = None
    Rs = np.arange(P.H, Rmax + 1e-9, dR)
    for R in Rs:
        xs = np.unique(np.concatenate([xs_base, [R - P.lam + 1e-7, R + 1e-7, R - 1e-7, s + 1e-7, R + s, R + 2 * s]]))
        xs = xs[xs > 0]
        A = alg_cost(R, xs, P, s, Hc, react)
        O = opt_cost(xs, R, P)
        r = (A / O).max()
        if r > w:
            w, arg = r, (round(R, 3), float(xs[np.argmax(A / O)]))
    # R = inf
    A = np.where(xs_base <= s, xs_base, s + b + al * (xs_base - s))
    r = (A / opt_cost(xs_base, INF, P)).max()
    if r > w:
        w, arg = r, ('inf', None)
    return w, arg


if __name__ == '__main__':
    rng = np.random.default_rng(1)
    lines = []
    def log(t):
        print(t, flush=True); lines.append(t)
    log("Theorem 5 check: worst ratio of ALG_c at H = Hc and H = Hc + 0.5 (target 2 - alpha)")
    log("conditions: tau=0, alpha<=1/2, (2-alpha)*ap>=1; cold if mu<=beta, warm with lam=0 if mu>beta")
    cnt = 0; maxexcess = -1
    for k in range(60):
        al = rng.uniform(0, 0.5)
        ap = rng.uniform(max(1 / (2 - al), al + 0.01), 1.0)
        mu = rng.uniform(0.05, 1.0) if k % 2 == 0 else rng.uniform(1.0, 5.0)
        react = 'cold' if mu <= 1 else 'warm'
        lam = rng.uniform(0, 3) if react == 'cold' else 0.0
        m = min(mu, 1.0)
        Hc = m / (2 * (1 - al))
        for H in [Hc, Hc + 0.5]:
            P = Params(mu=mu, alpha=al, ap=ap, H=H, lam=lam)
            w, arg = worst(P, react, Rmax=10.0, dR=0.02)
            maxexcess = max(maxexcess, w - (2 - al)); cnt += 1
            log(f"alpha={al:.3f} ap={ap:.3f} mu={mu:.3f} lam={lam:.2f} H={H:.3f} react={react}: worst={w:.5f} 2-alpha={2-al:.5f} excess={w-(2-al):+.2e} at {arg}")
    log(f"SUMMARY: {cnt} instances, max excess over 2-alpha = {maxexcess:+.3e}")
    log("Necessity of the side conditions (expected excess > 0):")
    for kw, react in [(dict(mu=1.0, alpha=0.3, ap=0.45), 'cold'), (dict(mu=1.0, alpha=0.6, ap=0.9), 'cold'),
                      (dict(mu=3.0, alpha=0.3, ap=0.7, lam=0.5), 'warm'), (dict(mu=3.0, alpha=0.3, ap=0.7, lam=0.0), 'cold')]:
        al = kw['alpha']; m = min(kw['mu'], 1.0) if react == 'warm' else kw['mu']
        Hc = m / (2 * (1 - al))
        P = Params(H=Hc, **kw)
        w, arg = worst(P, react, Rmax=10.0, dR=0.02)
        log(f"{kw} react={react} H=Hc={Hc:.3f}: worst={w:.4f} 2-alpha={2-al:.4f} at {arg}")
    open('out/alg_check.txt', 'w').write('\n'.join(lines) + '\n')


# ---------------------------------------------------------------------------------------------
# General algorithm ALG* of Theorem 6 (cold or warm reaction, wait-and-insure for short known windows)
def thresholds(P):
    a, b, mu, lam, ap = P.alpha, P.beta, P.mu, P.lam, P.ap
    s0 = b / (1 - a); c = 2 - a
    kap = c * ap - a
    big = lambda num, den: (np.inf if num > 0 else -np.inf) if den == 0 else num / den
    Rw = c * b / (1 - a) ** 2
    Rc = max(s0 + mu / (2 * (1 - a)), big(mu - 2 * (1 - a) * b, a * (1 - a)), (mu + a * b) / kap)
    Rh = max(s0 + b / (2 * (1 - a)), (1 + a) * b / kap)
    if lam > 0:
        Rh = max(Rh, lam + big((1 + a) * b, a * (1 - a)))
    Hc = Rc - s0 if Rc <= Rw + 1e-12 else Rc
    Hh = max(lam, Rh - s0 if Rh <= Rw + 1e-12 else Rh)
    return dict(s0=s0, Rw=Rw, Rc=Rc, Rh=Rh, Hc=Hc, Hh=Hh, Hstar=min(Hc, Hh))


def alg_star_cost(R, x, P, th):
    b, al, ap, mu, H, lam = P.beta, P.alpha, P.ap, P.mu, P.H, P.lam
    s = th['s0']
    react = 'cold' if th['Hc'] <= th['Hh'] else 'warm'
    Rx = th['Rc'] if react == 'cold' else th['Rh']
    a = R - H
    x = np.asarray(x, float)
    plan = np.where(x <= s, x, s + b + al * (x - s))
    if a >= s or R >= Rx:
        if react == 'cold':
            return np.where(x <= R, plan, s + b + al * (R - s) + mu + (x - R))
        d = R - lam
        cc = np.where((x > d) & (x <= R), plan + b, plan)
        return np.where(x <= R, cc, s + b + al * (R - s) + b + ap * (x - R))
    v = max(R, s)
    return np.where(x <= v, x, v + b + ap * (x - v))


def worst_star(P, Rmax=14.0, dR=0.02):
    th = thresholds(P)
    s = th['s0']; b, al = P.beta, P.alpha
    xs_base = np.concatenate([np.linspace(1e-4, 30, 6001), np.geomspace(31, 1e6, 80)])
    w = 0.0; arg = None
    for R in np.arange(P.H, max(Rmax, P.H + 6), dR):
        xs = np.unique(np.concatenate([xs_base, [R - P.lam + 1e-7, R + 1e-7, R - 1e-7, s + 1e-7]]))
        xs = xs[xs > 0]
        A = alg_star_cost(R, xs, P, th)
        r = (A / opt_cost(xs, R, P)).max()
        if r > w:
            w, arg = r, round(R, 3)
    A = np.where(xs_base <= s, xs_base, s + b + al * (xs_base - s))
    w = max(w, (A / opt_cost(xs_base, INF, P)).max())
    return w, arg, th


def main_general():
    rng = np.random.default_rng(7)
    lines = ["Theorem 6 check: ALG* at H = H* and H* + 0.3 (target 2 - alpha); random parameters with",
             "tau=0, 0<alpha<=1/2, (2-alpha)ap>=1, ap>alpha(2-alpha), lam<=s0, H*<=9"]
    cnt = 0; mx = -1
    while cnt < 120:
        al = rng.uniform(0.05, 0.5)
        ap = rng.uniform(max(1 / (2 - al), al * (2 - al)) + 1e-3, 1.0)
        mu = rng.choice([rng.uniform(0.05, 1.0), rng.uniform(1.0, 6.0)])
        lam = rng.choice([0.0, rng.uniform(0, 1 / (1 - al))])
        P0 = Params(mu=mu, alpha=al, ap=ap, lam=lam)
        th = thresholds(P0)
        if not np.isfinite(th['Hstar']) or th['Hstar'] > 9:
            continue
        for H in [th['Hstar'], th['Hstar'] + 0.3]:
            P = P0.with_(H=H)
            w, arg, _ = worst_star(P)
            mx = max(mx, w - (2 - al)); cnt += 1
            lines.append(f"alpha={al:.3f} ap={ap:.3f} mu={mu:.3f} lam={lam:.3f} H*={th['Hstar']:.3f} "
                         f"(Hc={th['Hc']:.3f}, Hw={th['Hh']:.3f}) H={H:.3f}: worst={w:.5f} excess={w-(2-al):+.2e} at R={arg}")
    lines.append(f"SUMMARY: {cnt} instances, max excess over 2-alpha = {mx:+.3e}")
    print('\n'.join(lines[-5:]))
    open('out/alg_check_general.txt', 'w').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main_general()
