"""Audit (C2, proof correctness): rigorous lower bound on the deterministic CR*(H) (tau = 0) from the
three adversary families of the necessity proof of Theorem 4 / Corollary 6, evaluated with interval
bounds so that the infimum over ALL algorithms is covered (no grid over the algorithm's choices is
trusted; every ratio is bounded below on each interval).  Does not use Lemma 2: every post-notice
action is bounded at the demand ends used below (a commit at d <= R - lam is no better at x = d^+ than
at d = R - lam, because that ratio falls in d; commits after R - lam, voluntary moves and fresh
protection before R all cost >= the cold reaction at x = R^+).

Algorithm classes (deterministic):
  insure before any notice                  -> ratio >= max(2-a, ap/a)          (Thm 2.1, R = inf)
  never buy before a notice                 -> ratio >= 1/a                     (R = inf, x -> inf)
  first pre-notice purchase revocable at s  -> ratio >= max(F1(s), F2(s), sup_R V3(R) over R in [H, s+H))
     F1: R = inf, x = s^+.
     F2: notice at s^+, R = s + H; reaction cold (x = R^+) or warm (x = (R-lam)^+ and R^+, only if H >= lam).
     F3 (V3(R)): notice at R - H < s, so the algorithm holds nothing and knows R; its first purchase
         after the notice (time u in [R-H, R)) is protected or revocable, or it buys nothing before R;
         demand ends at u^+, R^-, (R-lam)^+ or R^+.
  OPT values used are actual OPT runs (upper bounds on OPT), so every ratio is a valid lower bound.
Output: audit/out/necessity_lb.txt"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alg_star_exact import thresholds

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'necessity_lb.txt')


def optR_upper(Rlo, Rhi, P):
    """upper bound on OPT(R^+, R) for R in [Rlo, Rhi] (vectorized)."""
    b, a, ap, mu, lam = P['b'], P['a'], P['ap'], P['mu'], P['lam']
    O = np.minimum(Rhi, b + a * Rhi + mu)
    if not P['rrl']:
        O = np.minimum(O, b + ap * Rhi)
        O = np.where(Rlo >= lam, np.minimum(O, 2 * b + a * Rhi), O)
    return O


def V3(R, H, P, du=1e-3):
    """lower bound on the best ratio of an algorithm that learns R at R - H holding nothing."""
    b, a, ap, mu, lam = P['b'], P['a'], P['ap'], P['mu'], P['lam']
    if R <= 1e-12:
        return 0.0, 'empty window (no constraint used)'
    ORm = min(R, b + a * R)                      # OPT(R^-, R)
    never = R / ORm
    aN = R - H
    if R - aN <= 0:
        return never, 'never'
    m = max(2, int(np.ceil((R - aN) / du)))
    u = np.linspace(aN, R, m + 1)
    ulo, uhi = u[:-1], u[1:]
    F1u = (ulo + b) / np.minimum(np.maximum(uhi, 1e-300), b + a * uhi)
    O3 = float(optR_upper(np.array([R]), np.array([R]), P)[0])
    cold = (b + a * R + mu + (1 - a) * ulo) / O3
    best = cold
    if (not P['rrl']) and H >= lam:
        avail = (R - lam) >= ulo
        w2 = (2 * b + a * R + (1 - a) * ulo) / O3
        if lam > 0:
            y = R - lam
            w1 = (2 * b + a * y + (1 - a) * ulo) / min(y, b + a * y) if y > 0 else np.full_like(ulo, np.inf)
            w = np.maximum(w1, w2)
        else:
            w = w2
        best = np.where(avail, np.minimum(cold, w), cold)
    rev = np.maximum(F1u, best)
    opts = [rev.min()]
    if not P['rrl']:
        prot = np.maximum(F1u, (b + ap * R + (1 - ap) * ulo) / ORm)
        opts.append(prot.min())
    v = min(never, *opts)
    return v, 'never' if v == never else 'buy'


def lb_all(P, H, ds=2e-4, dR=0.01, du=1e-3, extra=10.0, include_insure=True):
    b, a, ap, mu, lam = P['b'], P['a'], P['ap'], P['mu'], P['lam']
    c = 2 - a
    s0 = b / (1 - a)
    CRins = np.inf if (P['rrl'] or a == 0 or not include_insure) else max(c, ap / a)
    never = 1 / a if a > 0 else np.inf
    S = s0 + max(H, 1.0) + extra
    # ---- F3 table: V3 on an R grid, cumulative max
    Rg = np.arange(H, S + H + dR, dR)
    v3 = np.array([V3(R, H, P, du)[0] for R in Rg])
    cm = np.maximum.accumulate(v3)
    # ---- s intervals
    s = np.arange(0.0, S + ds / 2, ds)
    slo, shi = s[:-1], s[1:]
    F1 = (slo + b) / np.minimum(np.maximum(shi, 1e-300), b + a * shi)
    Rlo, Rhi = slo + H, shi + H
    O = optR_upper(Rlo, Rhi, P)
    cold = (slo + b + a * H + mu) / O
    F2 = cold
    if (not P['rrl']) and H >= lam:
        w2 = (slo + 2 * b + a * H) / O
        if lam > 0:
            yhi = shi + H - lam
            w1 = (slo + 2 * b + a * (H - lam)) / np.minimum(np.maximum(yhi, 1e-300), b + a * yhi)
            w = np.maximum(w1, w2)
        else:
            w = w2
        F2 = np.minimum(cold, w)
    # F3 usable for the whole interval: R < slo + H  (strict)
    idx = np.searchsorted(Rg, slo + H, side='left') - 1          # last R_k < slo + H
    F3 = np.where(idx >= 0, cm[np.clip(idx, 0, None)], 0.0)
    LBs = np.maximum(F1, np.maximum(F2, F3))
    i = int(np.argmin(LBs))
    # s >= S: F1 nondecreasing beyond s0, F3 sup nondecreasing in s
    jS = np.searchsorted(Rg, S + H, side='left') - 1
    tail = max((S + b) / (b + a * S), cm[jS] if jS >= 0 else 0.0)
    cands = {'insure': CRins, 'never': never, 'react': LBs[i], 'tail': tail}
    k = min(cands, key=cands.get)
    which = 'F1' if LBs[i] == F1[i] else ('F2' if LBs[i] == F2[i] else 'F3')
    return cands[k], dict(cls=k, s=slo[i], binding=which, F1=F1[i], F2=F2[i], F3=F3[i])


if __name__ == '__main__':
    lines = []
    def log(t):
        print(t, flush=True); lines.append(t)
    log('Rigorous family lower bound LB(H) on CR*(H) (all deterministic algorithms, tau = 0).')
    log('Columns: case | H* (Thm 4 / Cor 6 formula) | H | LB(H) - (2-a) | binding family, algorithm s at the inf')
    log('Expectation: LB - (2-a) > 0 for every H < H*; ~0 (<= grid error 1e-3) for H >= H*.')
    cases = []
    for a in [1/3, 0.5]:
        for mu in [0.5, 1, 1.5, 2, 3]:
            for lam in [0.0, 0.5, 1.0]:
                cases.append(('hstar-table', dict(b=1.0, a=a, ap=0.8, mu=mu, lam=lam, rrl=False)))
    cases += [('kappa-binding', dict(b=1.0, a=1/3, ap=0.6, mu=2.0, lam=0.5, rrl=False)),
              ('L3-binding regime1', dict(b=1.0, a=0.5, ap=0.8, mu=2.2, lam=0.5, rrl=False)),
              ('L3-binding known window', dict(b=1.0, a=1/3, ap=0.8, mu=2.4, lam=0.5, rrl=False)),
              ('lam = s0', dict(b=1.0, a=1/3, ap=0.8, mu=1.5, lam=1.5, rrl=False)),
              ('alpha=0 menu lam>0', dict(b=1.0, a=0.0, ap=0.6, mu=1.6, lam=0.5, rrl=False)),
              ('alpha=0 menu lam=0 mu>2b', dict(b=1.0, a=0.0, ap=0.6, mu=2.6, lam=0.0, rrl=False)),
              ('alpha=0 lam>0 mu>2b (H*=inf claimed)', dict(b=1.0, a=0.0, ap=0.8, mu=3.0, lam=0.5, rrl=False)),
              ('ap at (C) lower limit', dict(b=1.0, a=0.4, ap=0.64 + 1e-6, mu=2.0, lam=0.5, rrl=False)),
              ('ap at (C) lower limit', dict(b=1.0, a=0.2, ap=1 / 1.8 + 1e-6, mu=1.8, lam=0.5, rrl=False))]
    for a in [0.0, 1/3, 0.5, 0.6, 0.75]:
        for mu in [0.5, 2.0, 2.0 / (1 - a) + 0.5, 6.0]:
            cases.append(('RRL', dict(b=1.0, a=a, ap=1.0, mu=mu, lam=0.0, rrl=True)))
    rng = np.random.default_rng(11)
    for _ in range(16):
        a = rng.uniform(0, 0.5); lo = max(1 / (2 - a), a * (2 - a))
        cases.append(('random (C)', dict(b=1.0, a=a, ap=rng.uniform(lo + 1e-6, 1.0), mu=rng.uniform(0, 4),
                                         lam=rng.choice([0.0, rng.uniform(0, 1 / (1 - a))]), rrl=False)))
    worst_below, worst_above = np.inf, -np.inf
    for name, P in cases:
        th = thresholds(P['a'], P['ap'], P['mu'], P['lam'], rrl=P['rrl'])
        Hs = th['Hs']
        c = 2 - P['a']
        Hlist = [Hs - 0.1, Hs - 0.01, Hs, Hs + 0.05] if np.isfinite(Hs) else [5.0, 20.0]
        for H in Hlist:
            if H < 0:
                continue
            v, info = lb_all(P, H)
            d = v - c
            tag = ''
            if np.isfinite(Hs) and H < Hs - 1e-12:
                worst_below = min(worst_below, d)
                if d <= 1e-9:
                    tag = '   <-- NO GAP below H*'
            elif np.isfinite(Hs):
                worst_above = max(worst_above, d)
                if d > 2e-3:
                    tag = '   <-- LB above 2-a at H >= H*: contradiction with sufficiency'
            else:
                if d <= 1e-9:
                    tag = '   <-- H*=inf claimed but LB = 2-a'
            pr = {k: (round(v_, 4) if isinstance(v_, float) else v_) for k, v_ in P.items()}
            log(f"{name} | {pr} | H*={Hs:.4f} ({th['rho']}) | H={H:.4f} | {d:+.5f} | {info['cls']}/{info['binding']} s={info['s']:.3f}{tag}")
    log(f'SUMMARY: min over H < H* of LB-(2-a) = {worst_below:+.5f};  max over H >= H* of LB-(2-a) = {worst_above:+.5f}')
    # ---- Section 9 design rule: H* = mu/(2(q-a)) for lam > 0 "in the calibrated range" (proviso of Cor 5.3 dropped)
    log('')
    log('Section 9 design rule check (calibrated range: mu <= 2beta, a <= 1/2, ap >= 1/(2-a), ap > a(2-a), lam > 0):')
    for P in [dict(b=1.0, a=1/3, ap=0.6, mu=2.0, lam=0.5, rrl=False), dict(b=1.0, a=0.4, ap=0.65, mu=2.0, lam=0.5, rrl=False),
              dict(b=1.0, a=0.3, ap=0.6, mu=2.0, lam=0.5, rrl=False), dict(b=1.0, a=0.3, ap=0.6, mu=1.8, lam=1.0, rrl=False)]:
        a = P['a']; Hrule = P['mu'] / (2 * (1 - a))
        th = thresholds(a, P['ap'], P['mu'], P['lam'])
        for H in [Hrule, (Hrule + th['Hs']) / 2]:
            v, info = lb_all(P, H)
            log(f"  {P}: rule H={Hrule:.4f}, Thm-4 H*={th['Hs']:.4f}; at H={H:.4f}: rigorous LB={v:.5f} vs 2-a={2-a:.5f} "
                f"(excess {v-(2-a):+.5f}, {info['binding']})")
    open(OUT, 'w').write('\n'.join(lines) + '\n')
