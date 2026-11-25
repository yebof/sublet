"""Audit (C2): rigorous (interval) evaluation of the Theorem 3 lower bound restricted to the
demand ends E^+ and (E-lam)^+ (no tail sup), tau = 0, for the cells of Table PoR (P8) and the
P7 table.  No grid over the adversary and no grid over OPT: OPT(E^+, E) is the exact minimum of
the four branches of Lemma 1(b) at t = 0 (all four are actual OPT runs when E >= lam; the
pre-warm branch is dropped when E < lam).
Interval method: on [s_i, s_{i+1}] every numerator and every OPT branch used below is
nondecreasing in s, so ratio(s) >= num(s_i) / den(s_{i+1}); the bound is the minimum over
intervals of max(F1_lo, min(cold_lo, warm_lo)), plus s >= S (F1 nondecreasing beyond s0) and
s = infinity (ratio >= 1/alpha).  Output: audit/out/lb_rigorous.txt"""
import numpy as np, os

def opt0(E, P, allow_warm):
    b, a, ap, mu = P['b'], P['a'], P['ap'], P['mu']
    c = np.minimum(E, b + a * E + mu)
    if P['allow_p']:
        c = np.minimum(c, b + ap * E)
        if allow_warm is not None:
            c = np.where(allow_warm, np.minimum(c, 2 * b + a * E), c)
    return c

def lb(P, S=60.0, n=600001):
    b, a, mu, H, lam = P['b'], P['a'], P['mu'], P['H'], P['lam']
    s = np.linspace(1e-6, S, n)
    lo, hi = s[:-1], s[1:]
    # F1 >= (lo + b) / min(hi, b + a hi)
    F1 = (lo + b) / np.minimum(hi, b + a * hi)
    # OPT(E^+,E) upper bound on the interval: evaluate at hi, keep the pre-warm branch only if E_lo >= lam
    Elo, Ehi = lo + H, hi + H
    O = opt0(Ehi, P, (Elo >= lam) if P['allow_p'] else None)
    cold = (lo + b + a * H + mu) / O
    warm = np.full_like(cold, np.inf)
    if P['allow_p'] and H >= lam:
        w2 = (lo + 2 * b + a * H) / O
        if lam > 0:
            ylo, yhi = lo + H - lam, hi + H - lam
            w1 = (lo + 2 * b + a * (H - lam)) / np.minimum(yhi, b + a * yhi)
            warm = np.maximum(w1, w2)
        else:
            warm = w2
    F = np.maximum(F1, np.minimum(cold, warm))
    v = F.min()
    tail = (S + b) / (b + a * S) if S > b / (1 - a) else 0   # F1 for s >= S
    v = min(v, max(tail, 0))  # s >= S: only F1 is used (conservative)
    if a > 0:
        v = min(v, 1 / a)
    return v

def quad(P, mA):
    b, a, H = P['b'], P['a'], P['H']
    A = 1 - a; B = H * (1 - a * a) - a * (b + mA); C = b * (H * (1 - a) - b - mA)
    s = (-B + np.sqrt(B * B - 4 * A * C)) / (2 * A)
    return max(2 - a, (s + b) / (b + a * s)), s

lines = []
lines.append("Table PoR cells (alpha=0.3, ap=0.7, beta=1): rigorous LB (interval, t=0 only) | quadratic (m_A) | doc family bound")
doc = {  # family bound column of the doc's Table PoR
 (0.5,'any'): [1.8241,1.7386,1.7000,1.7000,1.7000,1.7000,1.7000,1.7000],
 (1,'any'):   [1.9207,1.8479,1.7702,1.7000,1.7000,1.7000,1.7000,1.7000],
 (2,0):       [1.9207,1.8479,1.7702,1.7000,1.7000,1.7000,1.7000,1.7000],
 (2,'>0'):    [2.0674,2.0104,1.9501,1.8865,1.8198,1.7000,1.7000,1.7000]}
Hs = [0, 0.25, 0.5, 0.75, 1, 1.5, 2, 3]
for (mu, lamk), vals in doc.items():
    lams = [0.0, 0.5, 1.0] if lamk == 'any' else ([0.0] if lamk == 0 else [0.5, 1.0])
    for lam in lams:
        for H, dv in zip(Hs, vals):
            P = dict(b=1.0, a=0.3, ap=0.7, mu=mu, H=H, lam=lam, allow_p=True)
            v = min(lb(P), 0.7 / 0.3)
            mA = mu if (lam > 0 and H < lam) or mu <= 1 else (1.0 if lam == 0 else mu)
            q, s = quad(P, mA)
            flag = '' if v >= dv - 2e-4 else '   <-- doc value above rigorous t=0 bound'
            lines.append(f"mu={mu} lam={lam} H={H}: rigorous={v:.4f} quad(m_A={mA})={q:.4f} (s*={s:.3f}) doc={dv:.4f}{flag}")
lines.append("")
lines.append("P7 table (alpha=0, ap=0.5, H=0): rigorous LB vs doc formula")
for mu in [0.5, 1, 2, 4]:
    for lam, allow in [(0.5, True), (0.0, True), (0.5, False)]:
        P = dict(b=1.0, a=0.0, ap=0.5, mu=mu, H=0.0, lam=lam, allow_p=allow)
        v = lb(P)
        muA = mu if (lam > 0 or not allow) else min(mu, 1)
        muO = min(mu, 1) if allow else mu
        f = 1 + (1 + muA) / min(np.sqrt(1 + muA), 1 + muO)
        lines.append(f"mu={mu} lam={lam} allow_p={allow}: rigorous={v:.4f} formula={f:.4f}")
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'lb_rigorous.txt')
open(out, 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
