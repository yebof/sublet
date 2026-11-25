"""Audit (C2, proof correctness): independent checks of Lemma 1(b) and of the sufficiency half of
Theorem 4 / Corollary 6 of design/theory/c2_single_site.md.  Does not import model.py, det_game.py,
alg_check.py or families.py.  tau = 0 throughout.

Part 1 (Lemma 1b).  Brute-force OPT(x, R): grid search over OPT schedules (protected at u; revocable
at u then pre-warm commit at any d, or cold reclaim then fresh protected at any w, or a voluntary move
to fallback at w < R then protected at w').  Compared with the four-branch formula
min{x, b+aR+mu+(x-R), 2b+aR+ap(x-R) [R>=lam], b+ap x}.
Part 2 (sufficiency).  ALG* coded from the text of Section 6.  For each window end R the cost of ALG*
and OPT are piecewise linear in x, so sup_x ratio is attained at a breakpoint (value or right
limit) or x -> inf; all breakpoints are enumerated (incl. crossings of OPT branches).  R runs over a
fine grid plus all critical points (s0, s0+H, R_cold, R_warm, R_wait, lam, each +-1e-9).
Cases: boundary points of condition (C) (alpha in {0, 1/2}, ap at its lower limit, lam = s0, mu at
the switch values beta, 2(1-a)beta, 2beta, ...), random (C) points, and the RRL variant (no protected
option) for alpha up to 0.9 (Corollary 6 claims every alpha in [0,1)).
Output: audit/out/alg_star_exact.txt"""
import os, sys
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'alg_star_exact.txt')
lines = []
def log(s):
    print(s, flush=True); lines.append(s)

# ---------------------------------------------------------------- formulas of Section 6
def big(num, den):
    if den == 0:
        return np.inf if num > 0 else -np.inf
    return num / den

def thresholds(a, ap, mu, lam, b=1.0, rrl=False):
    c = 2 - a; s0 = b / (1 - a); Rw = c * b / (1 - a) ** 2
    Hm = lambda R: R - s0 if R <= Rw + 1e-12 else R
    if rrl:
        Rc = s0 + mu / (2 * (1 - a))
        return dict(s0=s0, Rw=Rw, Rc=Rc, Rh=np.inf, Hc=Hm(Rc), Hh=np.inf, Hs=Hm(Rc), rho='cold', Rrho=Rc)
    kap = c * ap - a
    Rc = max(s0 + mu / (2 * (1 - a)), big(mu - 2 * (1 - a) * b, a * (1 - a)), (mu + a * b) / kap)
    Rh = max(s0 + b / (2 * (1 - a)), (1 + a) * b / kap)
    if lam > 0:
        Rh = max(Rh, lam + big((1 + a) * b, a * (1 - a)))
    Hc = Hm(Rc); Hh = max(lam, Hm(Rh))
    rho = 'cold' if Hc <= Hh else 'warm'
    return dict(s0=s0, Rw=Rw, Rc=Rc, Rh=Rh, Hc=Hc, Hh=Hh, Hs=min(Hc, Hh), rho=rho, Rrho=Rc if rho == 'cold' else Rh)

# ---------------------------------------------------------------- OPT
def opt_branches(R, P):
    """OPT for x > R as list of (A, B): cost A + B x; all are actual OPT runs."""
    b, a, ap, mu, lam = P['b'], P['a'], P['ap'], P['mu'], P['lam']
    br = [(0.0, 1.0), (b + a * R + mu - R, 1.0)]
    if not P['rrl']:
        br.append((b + a * R + mu + b - ap * R, ap))          # cold, fresh protected at R
        br.append((b, ap))                                     # protected from 0
        if R >= lam:
            br.append((2 * b + a * R - ap * R, ap))           # pre-warm at R - lam
        else:
            # late pre-warm (commit at 0, handover lam > R): stranded at R, fallback to lam
            br.append((b + a * R + b + mu + (lam - R) - ap * lam, ap))
    return br

def opt_exact(x, R, P):
    x = np.asarray(x, float)
    b, a, ap = P['b'], P['a'], P['ap']
    low = np.minimum(x, b + a * x)
    if not P['rrl']:
        low = np.minimum(low, b + ap * x)
    if np.isinf(R):
        return low
    hi = np.full_like(x, np.inf)
    for A, B in opt_branches(R, P):
        hi = np.minimum(hi, A + B * x)
    return np.where(x <= R, low, hi)

def opt_bruteforce(x, R, P, n=41):
    """grid search over OPT schedules (tau=0); returns min cost (upper bound on true OPT, tight up to grid)."""
    b, a, ap, mu, lam = P['b'], P['a'], P['ap'], P['mu'], P['lam']
    best = x
    us = np.linspace(0, x, n)
    if not P['rrl']:
        best = min(best, np.min(us + b + ap * (x - us)))
    for u in np.linspace(0, min(x, R), n)[:-1]:
        if x <= R:
            best = min(best, u + b + a * (x - u)); continue
        # cold at R, then fallback until w >= R, protected from w (or never)
        ws = np.linspace(R, x, n)
        base = u + b + a * (R - u) + mu
        best = min(best, base + (x - R))
        if not P['rrl']:
            best = min(best, np.min(base + (ws - R) + b + ap * (x - ws)))
            # pre-warm commit at d in [u, R): handover h = d + lam
            for d in np.unique(np.concatenate([np.linspace(u, R, n)[:-1], [R - lam] if R - lam >= u else []])):
                h = d + lam
                if h <= R:
                    best = min(best, u + b + a * (h - u) + b + ap * (x - h)) if h < x else min(best, u + b + a * (x - u) + (b if d < x else 0))
                else:   # stranded at R, fallback until h
                    cst = u + b + a * (R - u) + b + mu + (min(h, x) - R) + ap * max(0.0, x - h)
                    best = min(best, cst)
        # voluntary move to fallback at w < R (pays mu), then protected at w' >= w or never
        for w in np.linspace(u, R, 21)[1:-1]:
            base2 = u + b + a * (w - u) + mu
            best = min(best, base2 + (x - w))
            if not P['rrl']:
                w2 = np.linspace(w, x, 41)
                best = min(best, np.min(base2 + (w2 - w) + b + ap * (x - w2)))
    return best

def lemma1_formula(x, R, P):
    b, a, ap, mu, lam = P['b'], P['a'], P['ap'], P['mu'], P['lam']
    v = [x, b + a * R + mu + (x - R)]
    if not P['rrl']:
        v.append(b + ap * x)
        if R >= lam:
            v.append(2 * b + a * R + ap * (x - R))
    return min(v)

# ---------------------------------------------------------------- ALG* of Section 6
def alg_star(x, R, H, P, th):
    b, a, ap, mu, lam = P['b'], P['a'], P['ap'], P['mu'], P['lam']
    s = th['s0']
    x = np.asarray(x, float)
    plan = np.where(x <= s, x, s + b + a * (x - s))
    if np.isinf(R):
        return plan, 'inf'
    aN = R - H
    if aN >= s or R >= th['Rrho']:
        if aN >= s and R < th['Rrho'] - 1e-9:
            raise RuntimeError(f'notice after s0 with R < R_rho: R={R} H={H}')
        if th['rho'] == 'cold':
            return np.where(x <= R, plan, s + b + a * (R - s) + mu + (x - R)), 'hold-cold'
        d = R - lam
        assert d >= aN - 1e-9 and d >= s - 1e-9, 'warm commit infeasible'
        cc = np.where((x > d) & (x <= R), plan + b, plan)
        return np.where(x <= R, cc, s + b + a * (R - s) + b + ap * (x - R)), 'hold-warm'
    v = max(R, s)
    if P['rrl']:
        return x.copy(), 'wait'
    return np.where(x <= v, x, v + b + ap * (x - v)), 'wait'

def worst_at_R(R, H, P, th):
    b, a, ap, lam = P['b'], P['a'], P['ap'], P['lam']
    s = th['s0']
    bps = [s, R - lam, R, max(R, s), 1e9]
    if not np.isinf(R):
        br = opt_branches(R, P)
        for i in range(len(br)):
            for j in range(i + 1, len(br)):
                (A1, B1), (A2, B2) = br[i], br[j]
                if B1 != B2:
                    xc = (A2 - A1) / (B1 - B2)
                    if xc > R:
                        bps.append(xc)
    bps = np.array([p for p in bps if p > 0 and np.isfinite(p)])
    eps = 1e-9 * np.maximum(1.0, bps)
    xs = np.concatenate([bps, bps + eps, bps - eps])
    xs = xs[xs > 0]
    A, kind = alg_star(xs, R, H, P, th)
    O = opt_exact(xs, R, P)
    r = A / O
    assert np.all(np.isfinite(r)), (R, H)
    i = int(np.argmax(r))
    return r[i], xs[i], kind

def worst_ratio(P, H, th, dR=0.01, Rspan=12.0):
    s = th['s0']
    crit = [s, s + H, th['Rc'], th['Rh'], th['Rw'], P['lam'], H, th['Rrho'], th['Rrho'] - P['lam']]
    crit = [r for r in crit if np.isfinite(r)]
    Rs = list(np.arange(H, H + Rspan, dR)) + [r + e for r in crit for e in (-1e-9, 0.0, 1e-9)]
    Rs = [r for r in Rs if r >= H] + [np.inf]
    w, arg = 0.0, None
    for R in Rs:
        r, xw, kind = worst_at_R(R, H, P, th)
        if r > w:
            w, arg = r, (R, xw, kind)
    return w, arg

# ---------------------------------------------------------------- runs
if __name__ == '__main__':
    rng = np.random.default_rng(7)
    log('Part 1: Lemma 1(b) vs brute-force OPT (tau=0).  violation = formula - brute (must be <= ~0);')
    log('        gap = brute - formula (should be ~0 when R >= lam, i.e. Lemma 1(b) is exact there).')
    viol, gap_ok, gap_short, n = -np.inf, -np.inf, -np.inf, 0
    for k in range(400):
        a = rng.choice([0.0, rng.uniform(0, 0.9)])
        ap = rng.uniform(a + 0.01, 1.0)
        P = dict(b=1.0, a=a, ap=ap, mu=rng.uniform(0, 5), lam=rng.choice([0.0, rng.uniform(0, 3)]), rrl=bool(rng.random() < 0.2))
        R = rng.uniform(0.05, 6); x = R + rng.choice([rng.uniform(1e-3, 0.2), rng.uniform(0, 8)])
        bf = opt_bruteforce(x, R, P)
        f = lemma1_formula(x, R, P)
        ex = float(opt_exact(np.array([x]), R, P)[0])
        viol = max(viol, f - bf)
        if R >= P['lam']:
            gap_ok = max(gap_ok, bf - f)
        else:
            gap_short = max(gap_short, bf - f)
        assert abs(ex - bf) < 2e-2 * max(1, bf), (P, R, x, ex, bf)
        n += 1
    log(f'  {n} random (params, R, x): max violation {viol:+.2e}; max gap (R>=lam) {gap_ok:+.2e}; max gap (R<lam) {gap_short:+.2e}')
    log('  opt_exact (endpoint enumeration used in Part 2) agrees with brute force within the brute-force grid on all instances.')

    log('')
    log('Part 2: ALG* (Section 6) worst ratio minus (2 - alpha), exact in x, R on grid dR=0.01 + critical points.')
    cases = []
    # boundary / switching points of (C)
    for a in [0.0, 0.25, 1/3, 0.5]:
        aplo = max(1 / (2 - a), a * (2 - a)) + 1e-6
        s0 = 1 / (1 - a)
        for ap in [aplo, 0.8 if aplo < 0.8 else 0.95, 1.0]:
            for mu in sorted(set([0.0, 0.3, 1.0, 2 * (1 - a), 1.5, 2.0, 2.0 / (1 - a), 3.0, 4.0])):
                for lam in [0.0, 0.5, s0]:
                    cases.append(dict(b=1.0, a=a, ap=ap, mu=mu, lam=lam, rrl=False))
    for _ in range(60):
        a = rng.uniform(0, 0.5); lo = max(1 / (2 - a), a * (2 - a))
        cases.append(dict(b=1.0, a=a, ap=rng.uniform(lo + 1e-6, 1.0), mu=rng.uniform(0, 6),
                          lam=rng.choice([0.0, rng.uniform(0, 1 / (1 - a))]), rrl=False))
    for a in [0.0, 1/3, 0.5, 0.6, 0.75, 0.9]:
        for mu in [0.0, 0.5, 1.0, 2.0, 2.0 / (1 - a), 3.0, 6.0]:
            cases.append(dict(b=1.0, a=a, ap=1.0, mu=mu, lam=0.0, rrl=True))
    worst_excess = {'menu': -np.inf, 'rrl': -np.inf}
    nrun = {'menu': 0, 'rrl': 0}
    for P in cases:
        th = thresholds(P['a'], P['ap'], P['mu'], P['lam'], rrl=P['rrl'])
        if not np.isfinite(th['Hs']):
            log(f"  H*=inf  {P}  (skipped: no finite notice)")
            continue
        for H in [th['Hs'], th['Hs'] + 0.37]:
            w, arg = worst_ratio(P, H, th)
            ex = w - (2 - P['a'])
            key = 'rrl' if P['rrl'] else 'menu'
            nrun[key] += 1
            worst_excess[key] = max(worst_excess[key], ex)
            if ex > 1e-7:
                log(f"  VIOLATION {P} H={H:.4f} worst={w:.6f} excess={ex:+.3e} at {arg} th={th}")
    log(f"  menu cases: {nrun['menu']} runs, max excess {worst_excess['menu']:+.3e}")
    log(f"  RRL cases (Cor. 6, alpha up to 0.9): {nrun['rrl']} runs, max excess {worst_excess['rrl']:+.3e}")
    log('')
    log('Part 3: ALG* just below H* (H = H* - 0.05) must fail (sanity: the algorithm needs the threshold).')
    fails = 0; tot = 0
    for P in cases[::7]:
        th = thresholds(P['a'], P['ap'], P['mu'], P['lam'], rrl=P['rrl'])
        if not np.isfinite(th['Hs']) or th['Hs'] < 0.06:
            continue
        H = th['Hs'] - 0.05
        try:
            w, arg = worst_ratio(P, H, th)
        except (RuntimeError, AssertionError):
            fails += 1; tot += 1; continue
        tot += 1
        if w - (2 - P['a']) > 1e-7:
            fails += 1
    log(f'  {fails}/{tot} cases: ALG* exceeds 2-alpha (or is ill-defined) at H = H* - 0.05')
    open(OUT, 'w').write('\n'.join(lines) + '\n')
