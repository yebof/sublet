"""Audit (C2, proof correctness): algebraic checks of Theorem 4 / Corollary 5 / Corollary 6
of design/theory/c2_single_site.md on random parameters.  Independent re-implementation of
the H* formula of Section 6 (not imported from alg_check.py / hstar.py).
Output: audit/out/formula_check.txt"""
import os
import numpy as np

def big(num, den):
    if den == 0:
        return np.inf if num > 0 else -np.inf
    return num / den

def Hmap(R, s0, Rw):
    return R - s0 if R <= Rw + 1e-12 else R

def thm4(al, ap, mu, lam, b=1.0):
    c = 2 - al; s0 = b / (1 - al); kap = c * ap - al
    Rw = c * b / (1 - al) ** 2
    Rc = max(s0 + mu / (2 * (1 - al)), big(mu - 2 * (1 - al) * b, al * (1 - al)), (mu + al * b) / kap)
    Rh = max(s0 + b / (2 * (1 - al)), (1 + al) * b / kap)
    if lam > 0:
        Rh = max(Rh, lam + big((1 + al) * b, al * (1 - al)))
    Hc = Hmap(Rc, s0, Rw); Hh = max(lam, Hmap(Rh, s0, Rw))
    return min(Hc, Hh), Hc, Hh, Rc, Rh, Rw, s0, kap

def condC(al, ap, lam, b=1.0):
    return (0 <= al <= 0.5) and ((2 - al) * ap >= 1) and (ap > al * (2 - al)) and (ap <= 1) and (lam <= b / (1 - al))

rng = np.random.default_rng(2026)
lines = []
bad = {k: 0 for k in ['C5.1', 'C5.2', 'C5.3', 'warm_only_if_mu_gt_beta', 'proviso_auto', 'C6_alpha0',
                      'warm_kappa_never_binds', 'Rwarm_lam_gt_Rwait']}
cnt = {k: 0 for k in bad}
for _ in range(200000):
    al = rng.choice([0.0, rng.uniform(0, 0.5), 0.5])
    lo = max(1 / (2 - al), al * (2 - al)) + 1e-9
    ap = rng.uniform(lo, 1.0) if rng.random() < 0.7 else lo + rng.uniform(0, 1e-3)
    mu = rng.choice([rng.uniform(0, 1), rng.uniform(1, 2), rng.uniform(0, 8)])
    lam = rng.choice([0.0, rng.uniform(0, 1 / (1 - al))])
    if not condC(al, ap, lam):
        continue
    Hs, Hc, Hh, Rc, Rh, Rw, s0, kap = thm4(al, ap, mu, lam)
    target = mu / (2 * (1 - al))
    if mu <= 1:
        cnt['C5.1'] += 1
        if abs(Hs - target) > 1e-9: bad['C5.1'] += 1
    if lam == 0:
        cnt['C5.2'] += 1
        if abs(Hs - min(mu, 1) / (2 * (1 - al))) > 1e-9: bad['C5.2'] += 1
    if lam > 0 and mu <= 2:
        prov = (mu + al) / kap <= s0 + target + 1e-12
        if prov:
            cnt['C5.3'] += 1
            if abs(Hs - target) > 1e-9: bad['C5.3'] += 1
        if mu <= 2 * (1 - al):
            cnt['proviso_auto'] += 1
            if not prov: bad['proviso_auto'] += 1
    # proof claim: warm attains H* (strictly smaller) only if mu > beta
    cnt['warm_only_if_mu_gt_beta'] += 1
    if Hh < Hc and mu <= 1: bad['warm_only_if_mu_gt_beta'] += 1
    # Cor-5 proof claim: (1+a)b/kappa <= s0 + b/(2(1-a)) for a <= 1/2
    cnt['warm_kappa_never_binds'] += 1
    if (1 + al) / kap > s0 + 1 / (2 * (1 - al)) + 1e-12: bad['warm_kappa_never_binds'] += 1
    if lam > 0 and al > 0:
        cnt['Rwarm_lam_gt_Rwait'] += 1
        if not Rh > Rw: bad['Rwarm_lam_gt_Rwait'] += 1
for al, mu in [(0, m) for m in np.linspace(0, 6, 61)]:
    s0 = 1.0; Rw = 2.0
    h = Hmap(s0 + mu / 2, s0, Rw)
    want = mu / 2 if mu <= 2 else 1 + mu / 2
    cnt['C6_alpha0'] += 1
    if abs(h - want) > 1e-9: bad['C6_alpha0'] += 1
lines.append("claim: violations / instances checked")
for k in bad:
    lines.append(f"{k}: {bad[k]} / {cnt[k]}")
# where the proviso of C5.3 fails, report how far H* is above mu/(2(1-alpha))
lines.append("C5.3 proviso failures (lam>0, mu<=2beta): examples of H* vs mu/(2(1-a))")
ex = 0
for al in [0.2, 1/3, 0.4, 0.5]:
    ap = max(1 / (2 - al), al * (2 - al)) + 1e-6
    for mu in [1.5, 1.8, 2.0]:
        Hs, Hc, Hh, Rc, Rh, Rw, s0, kap = thm4(al, ap, mu, 0.5)
        lines.append(f"alpha={al:.3f} ap={ap:.4f} kappa={kap:.4f} mu={mu}: H*={Hs:.4f} mu/(2(1-a))={mu/(2*(1-al)):.4f} R_cold={Rc:.4f} R_wait={Rw:.4f}")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'formula_check.txt'), 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
