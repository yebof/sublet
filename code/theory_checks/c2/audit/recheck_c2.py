"""Re-check (C2 audit, design/theory/audit_c2.md) of the auditor findings that were labelled WRONG,
STATEMENT NEEDS CHANGE or FIXABLE GAP.  Written independently of the auditor scripts: every formula
below is re-implemented here from design/theory/c2_single_site.md (no import from ../ or from the
other audit scripts, except part J, which uses audit/necessity_lb.py).  Closed-form or interval arithmetic
only; runs in under a minute.

Parts
  A  OPT corner R < lam (model.opt_cost before the fix omitted 'cold reclaim, then protected'):
     closed-form example, and the condition lam > (beta+mu)/(ap-alpha) on every parameter set used
     in the write-up.
  B  tau > 0: a second revocable lease bought just before R (allowed by the model text) vs the
     one-lease OPT used by det_game / model.opt_cost.
  C  Theorem 3, F2 for tau > H: literal text instance (R = s + H) vs the instance families.py uses
     (R = E = s + tau, announced at E - H).
  D  Two-family closed form with m = mu when H >= lam > 0: not implied by F1/F2 (warm reaction).
  E  Section 9 design rule vs Theorem 4 at the low end of the stated price range; rigorous F1/F2
     interval bound on CR* at the rule's H.
  F  alpha <= 1/2 is not needed in Theorem 4 (random check of the two inequalities that might use it).
  G  Switch cost bw != beta: substitution formula (Theorem 4 with bw in OPT's pre-warm branch and in
     the warm terms) vs the exact thresholds in out/model_switch_cost.txt.
  H  Calibration numbers of a5 (code/analysis/out/a5_reclaim_cost_calibration.json) are arithmetic on
     the script's assumptions.
  I  P7: RRL closed form at alpha = 0, H = 0 is 1 + sqrt(1 + mu).
  J  Scan rows of kind A: the known-window family F3 (audit A's interval implementation) vs the exact game.
Output: audit/out/recheck_c2.txt"""
import os, json, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
lines = []


def log(t=''):
    print(t, flush=True); lines.append(t)


def big(n, d):
    if d == 0:
        return np.inf if n > 0 else -np.inf
    return n / d


def thm4(al, ap, mu, lam, b=1.0, bw=None):
    """Theorem 4 thresholds (bw = beta); with bw != beta the substitution formula of part G."""
    bw = b if bw is None else bw
    c = 2 - al; s0 = b / (1 - al); kap = c * ap - al; Rw = c * b / (1 - al) ** 2
    Rc = max(s0 + mu / (2 * (1 - al)), big(mu + al * b - c * bw, al * (1 - al)), (mu + al * b) / kap)
    Rh = max(s0 + bw / (2 * (1 - al)), (al * b + bw) / kap)
    if lam > 0:
        Rh = max(Rh, lam + big(al * b + bw, al * (1 - al)))
    Hm = lambda R: R - s0 if R <= Rw + 1e-12 else R
    Hc, Hh = Hm(Rc), max(lam, Hm(Rh))
    return dict(H=min(Hc, Hh), Hc=Hc, Hh=Hh, Rc=Rc, Rh=Rh, Rw=Rw, s0=s0, kap=kap)


def opt_E(E, P):
    """OPT(E^+, E) for tau = 0 (Lemma 1(b) branches; exact when E >= lam)."""
    b, al, ap, mu, lam = P['b'], P['a'], P['ap'], P['mu'], P['lam']
    O = np.minimum(E, b + al * E + mu)
    if P['p']:
        O = np.minimum(O, b + ap * E)
        O = np.where(E >= lam, np.minimum(O, 2 * b + al * E), O)
    return O


def lb_F1F2(P, H, S=100.0, ds=2e-4):
    """Rigorous lower bound on CR* (tau = 0) from F1 and F2 at demand ends s^+, E^+, (E-lam)^+ only:
    min(insure, never-buy, inf over first revocable purchase s of max(F1, F2)); interval arithmetic
    over s in [0, S] (all terms are monotone in s on each piece), plus F1(S) for s > S."""
    b, al, ap, mu, lam = P['b'], P['a'], P['ap'], P['mu'], P['lam']
    s = np.arange(0.0, S + ds / 2, ds); lo, hi = s[:-1], s[1:]
    F1 = (lo + b) / np.minimum(np.maximum(hi, 1e-300), b + al * hi)
    O = opt_E(hi + H, P)                                   # OPT(E^+, E) is non-decreasing in E
    F2 = (lo + b + al * H + mu) / O                        # cold, demand ends at E^+
    if P['p'] and H >= lam:
        w = (lo + 2 * b + al * H) / O                      # warm, demand ends at E^+
        if lam > 0:
            y = hi + H - lam
            w = np.maximum(w, (lo + 2 * b + al * (H - lam)) / np.minimum(np.maximum(y, 1e-300), b + al * y))
        F2 = np.minimum(F2, w)
    react = min(np.maximum(F1, F2).min(), (S + b) / (b + al * S) if S > b / (1 - al) else 0.0)
    ins = max(2 - al, ap / al) if (P['p'] and al > 0) else np.inf
    never = 1 / al if al > 0 else np.inf
    return min(ins, never, react)


# ------------------------------------------------------------------ A
log('A. OPT when R < lam: cold reclaim, then protected at R (tau = 0, beta = 1)')
al, ap, mu, lam, R, x = 0.0, 0.6, 0.25, 3.0, 2.5, 10.0
prefix = min(x, 1 + ap * x, 1 + al * R + mu + (x - R))
fixed = min(prefix, 1 + al * R + mu + 1 + ap * (x - R))
log(f'   alpha={al} ap={ap} mu={mu} lam={lam} R={R} x={x}: pre-fix OPT {prefix:.4f}, with cold-then-protected {fixed:.4f}')
log('   cold-then-protected beats protected-from-0 iff R > (beta+mu)/(ap-alpha); it needs R < lam (else pre-warm is cheaper).')
sets = {
    'scan': [(a_, p_, m_, l_) for a_ in (0, .2, .3, .5) for p_ in (.4, .5, .6, .8) for m_ in (.5, 1, 2, 4) for l_ in (0, .5, 1) if p_ > a_],
    'hstar table': [(a_, .8, m_, l_) for a_ in (1 / 3, .5) for m_ in (.5, 1, 1.5, 2, 3) for l_ in (0, .5, 1)],
    'Table PoR': [(.3, .7, m_, l_) for m_ in (.5, 1, 2) for l_ in (0, .5, 1)],
    'Table R': [(.3, p_, m_, l_) for p_ in (.4, .5, .7) for m_ in (.5, 1, 2) for l_ in (0, .5)],
    'P7': [(0, .5, m_, l_) for m_ in (.5, 1, 2, 4) for l_ in (0, .5, 1)],
    'P10': [(.2, .45, m_, .5) for m_ in (.5, 1)],
    't4_exact / model_hstar_fine': [(1 / 3, .6, 2, .5), (1 / 3, .6, 1.8, .5), (.5, .8, 2.2, .5), (1 / 3, .8, 2.4, .5),
                                    (1 / 3, .8, 1.5, 1.5), (0, .6, 1.6, .5), (0, .6, 2.6, 0), (.2, .56, 2, 1),
                                    (.2, 1 / 1.8, 2, .5), (.2, .6, 1.5, .5)],
}
for k, v in sets.items():
    marg = min((1 + m_) / (p_ - a_) - l_ for a_, p_, m_, l_ in v)
    log(f'   {k}: min over {len(v)} parameter sets of (beta+mu)/(ap-alpha) - lam = {marg:+.3f} (> 0: the corner never occurs)')

# ------------------------------------------------------------------ B
log('')
log("B. tau > 0: second revocable lease (beta = 1)")


def opt_one(x, R, al, ap, mu, lam, tau, du=1e-3):
    best = min(x, 1 + ap * x)
    for u in np.arange(0.0, min(R, x), du):
        E = max(R, u + tau)
        c = u + 1 + al * (min(x, E) - u)
        if x > E:
            t = min(mu + (x - E), mu + 1 + ap * (x - E))
            if E - lam >= u - 1e-12:
                t = min(t, 1 + ap * (x - E))
            c += t
        best = min(best, c)
    return best


for al, ap, mu, lam, tau, R, x in [(0.0, 0.8, 2.0, 0.5, 1.0, 3.0, 3.5), (0.0, 0.8, 2.0, 0.0, 1.0, 3.0, 3.9),
                                   (0.3, 0.8, 2.0, 0.0, 1.0, 3.0, 3.9), (0.3, 0.7, 2.0, 0.5, 1.0, 3.0, 3.5)]:
    one = opt_one(x, R, al, ap, mu, lam, tau)
    d2 = R - max(lam, 0.05)                 # second lease committed before R (switch, takeover d2 + lam <= R)
    w2, E2 = d2 + lam, d2 + tau
    assert d2 < R and w2 <= R and x <= E2
    two = 1 + al * w2 + 1 + al * (x - w2)    # lease 1 from 0 to the takeover, lease 2 from the takeover to x
    log(f'   alpha={al} ap={ap} mu={mu} lam={lam} tau={tau} R={R} x={x}: one-lease OPT {one:.4f}; two leases '
        f'(second committed at {d2:.2f}, ends {E2:.2f}) {two:.4f}; one-lease OPT is {100 * (one - two) / two:.1f}% higher')

# ------------------------------------------------------------------ C
log('')
log('C. F2 for tau > H (beta = 1): literal instance R = s + H vs the families.py instance R = E = s + tau')
for al, ap, mu, lam, tau, H, s in [(0.3, 0.7, 1.0, 0.0, 1.0, 0.0, 2.0), (0.0, 0.6, 2.0, 0.5, 1.0, 0.25, 1.0)]:
    E = s + max(H, tau)
    for x in (E + 0.25, E + 0.5):
        A = s + 1 + al * (E - s) + mu + (x - E)
        Ol, Oe = opt_one(x, s + H, al, ap, mu, lam, tau), opt_one(x, E, al, ap, mu, lam, tau)
        log(f'   alpha={al} ap={ap} mu={mu} lam={lam} tau={tau} H={H} s={s} x={x}: cold cost {A:.4f}; '
            f'OPT(R=s+H) {Ol:.4f} -> ratio {A / Ol:.4f}; OPT(R=E) {Oe:.4f} -> ratio {A / Oe:.4f}')

# ------------------------------------------------------------------ D
log('')
log('D. Two-family closed form with m = mu at H >= lam > 0 (beta = 1)')


def quad(al, H, m, b=1.0):
    A = 1 - al; B = H * (1 - al * al) - al * (b + m); C = b * (H * (1 - al) - b - m)
    s = (-B + np.sqrt(B * B - 4 * A * C)) / (2 * A)
    return max(2 - al, (s + b) / (b + al * s)), s


for al, ap, mu, lam, H in [(0.1, 1 / 1.9 + 0.01, 4.0, 0.1, 0.1), (0.3, 0.7, 2.0, 0.5, 0.5), (0.3, 0.7, 2.0, 0.5, 1.0)]:
    P = dict(b=1.0, a=al, ap=ap, mu=mu, lam=lam, p=True)
    s0 = 1 / (1 - al); E = s0 + H; y = E - lam
    O = float(opt_E(np.array([E]), P)[0])
    warm = max((s0 + 2 + al * (H - lam)) / min(y, 1 + al * y), (s0 + 2 + al * H) / O)
    qmu, smu = quad(al, H, mu); qmin, _ = quad(al, H, min(mu, 1.0))
    lb = lb_F1F2(dict(P), H)
    log(f'   alpha={al} ap={ap:.4f} mu={mu} lam={lam} H={H}: quad(m=mu)={qmu:.4f} (s*={smu:.3f}); '
        f'algorithm buying at s0={s0:.3f} and pre-warming: max(F1, F2_warm) = {max(2 - al, warm):.4f}; '
        f'quad(m=min(mu,beta))={qmin:.4f}; rigorous F1/F2 bound (interval) {lb:.4f}')
log('   (first row: an algorithm exists in the F1/F2 game with value below quad(m=mu), so m = mu is not implied;'
    ' quad(m=min(mu,beta)) <= rigorous bound in every row)')

# ------------------------------------------------------------------ E
log('')
log('E. Section 9 rule H = mu/(2(1-alpha)) (lam > 0, mu <= 2 beta) vs Theorem 4; rigorous F1/F2 bound on CR*(H)')
for al, ap, mu, lam in [(1 / 3, 0.6, 2.0, 0.5), (0.2, 1 / 1.8, 2.0, 0.5), (0.4, 0.65, 2.0, 0.5), (1 / 3, 0.8, 2.0, 0.5)]:
    t = thm4(al, ap, mu, lam); Hr = mu / (2 * (1 - al)); c = 2 - al
    prov = (mu + al) / t['kap'] <= t['s0'] + mu / (2 * (1 - al)) + 1e-12
    P = dict(b=1.0, a=al, ap=ap, mu=mu, lam=lam, p=True)
    vals = '; '.join(f'H={H:.4f}: LB-(2-a)={lb_F1F2(P, H) - c:+.5f}' for H in (Hr, (Hr + t['H']) / 2, t['H']))
    log(f'   alpha={al:.4f} ap={ap:.4f} mu={mu} lam={lam}: rule {Hr:.4f}, Theorem 4 H*={t["H"]:.4f}, '
        f'Cor 5.3 proviso holds: {prov}; {vals}')
log('   proviso at mu = 2 beta reads ap >= (2+a-a^2)/(2(2-a)):')
for al in (0.2, 0.3, 1 / 3, 0.4, 0.5):
    pv = (2 + al - al * al) / (2 * (2 - al)); fl = max(1 / (2 - al), al * (2 - al))
    t = thm4(al, pv, 2.0, 0.5); t2 = thm4(al, pv - 1e-3, 2.0, 0.5)
    log(f'     alpha={al:.4f}: proviso bound {pv:.4f}, (C) floor {fl:.4f}; H* at the bound {t["H"]:.4f} '
        f'(rule {1 / (1 - al):.4f}); H* at bound-0.001 {t2["H"]:.4f}')

# ------------------------------------------------------------------ F
log('')
log('F. Theorem 4 without alpha <= 1/2: random check of the two inequalities that could need it')
rng = np.random.default_rng(5)
n1 = n2 = bad1 = bad2 = 0
for _ in range(200000):
    al = rng.uniform(0, 0.97); lo = max(1 / (2 - al), al * (2 - al))
    if lo >= 1:
        continue
    ap = rng.uniform(lo, 1.0); s0 = 1 / (1 - al); lam = rng.uniform(0, s0) * (rng.random() < 0.7)
    mu = rng.uniform(0, 1.0)                                   # (i) mu <= beta: cold attains H*
    t = thm4(al, ap, mu, lam); n1 += 1
    bad1 += t['Hc'] > t['Hh'] + 1e-12
    mu = rng.uniform(0, 1 / (2 - al))                          # (ii) Case C: mu < beta/(2-a)
    t = thm4(al, ap, mu, lam); n2 += 1
    bound = ((1 - al) + (2 - al) * mu) / (1 - al) ** 2
    bad2 += (t['Hc'] <= t['Hh']) and (t['Rc'] < t['Rw']) and (t['Rc'] > bound + 1e-12)
log(f'   (i) mu <= beta  =>  H(R_cold) <= max(lam, H(R_warm)): violations {bad1} / {n1} (alpha up to 0.97)')
log(f'   (ii) mu < beta/(2-a), R_cold < R_wait  =>  R_cold <= ((1-a)beta + (2-a)mu)/(1-a)^2: violations {bad2} / {n2}')

# ------------------------------------------------------------------ G
log('')
log('G. Switch cost bw: substitution formula vs exact thresholds (out/model_switch_cost.txt; grid 0.05, alpha = 1/3, ap = 0.8)')
f = os.path.join(HERE, 'out', 'model_switch_cost.txt')
nok = ntot = 0
for ln in open(f):
    m = re.match(r'mu=([\d.]+) lam=([\d.]+) bw=([\d.]+): H\*_exact=([\d.]+)', ln.strip())
    if not m:
        continue
    mu, lam, bw, hx = map(float, m.groups())
    t = thm4(1 / 3, 0.8, mu, lam, bw=bw)
    hg = np.ceil(t['H'] / 0.05 - 1e-9) * 0.05
    ok = abs(hg - hx) < 1e-9; nok += ok; ntot += 1
    log(f'   mu={mu} lam={lam} bw={bw}: formula {t["H"]:.4f} (grid {hg:.2f}) exact {hx:.2f} {"ok" if ok else "MISMATCH"}')
log(f'   agree: {nok} / {ntot}')
al, ap, mu, lam, bw = 1 / 3, 0.8, 2.0, 0.25, 0.2
t = thm4(al, ap, mu, lam, bw=bw); c = 2 - al
bound = ((1 - al) + (2 - al) * bw) / (1 - al) ** 2      # wait branch vs L3 = beta + bw + alpha R needs R <= bound
R = 0.5 * (bound + t['Rh'])
log(f'   proof check, bw={bw}, lam={lam}: rho = warm, R_warm={t["Rh"]:.4f} <= R_wait={t["Rw"]:.4f}; ALG* wait branch needs '
    f'R <= {bound:.4f}; at R={R:.4f}, x=R^+: (R+beta)/(beta+bw+alpha R) = {(R + 1) / (1 + bw + al * R):.4f} > 2-alpha = {c:.4f} '
    f'(the substituted formula matches the exact game, but the ALG* of the Theorem 4 proof does not carry over)')

# ------------------------------------------------------------------ H
log('')
log('H. a5 calibration: startup = weights / load bandwidth + engine_init (assumed); drain = p99 remaining tokens x TPOT (assumed)')
d = json.load(open(os.path.join(ROOT, 'code', 'analysis', 'out', 'a5_reclaim_cost_calibration.json')))
A = d['assumptions']
for mdl, c in d['calibration'].items():
    st = {k: v for k, v in c['setup_s_by_load_GBps'].items()}
    re_st = {k: A['weights_gb'][mdl] / float(k) + A['engine_init_s'] for k in st}
    log(f'   {mdl}: startup {st} = recomputed {re_st}; drain p99 {c["T_dr_s (p99 drain)"]:.1f} s (TPOT {A["tpot_s"][mdl]} s); '
        f'mu_noNotice_over_Bsetup {c["mu_noNotice_over_Bsetup"]:.3f}')
log(f'   in-flight source: {d["inflight_source"]}; engine_init_s = {A["engine_init_s"]} (assumption)')

# ------------------------------------------------------------------ I
log('')
log('I. P7: RRL, alpha = 0, H = 0: 1 + sqrt(1 + mu) = ' + ', '.join(f'{1 + np.sqrt(1 + m):.4f} (mu={m})' for m in (0.5, 1, 2, 4)))

# ------------------------------------------------------------------ J
log('')
log('J. Scan rows of kind A (mu = 4 beta, long notice, tau = 0): does the known-window family F3 close the gap?')
log('   (uses audit/necessity_lb.lb_all, the interval F1/F2/F3 bound of audit A; exact values from out/scan_compare.csv)')
import sys, csv
sys.path.insert(0, HERE)
from necessity_lb import lb_all
rows = list(csv.DictReader(open(os.path.join(HERE, '..', 'out', 'scan_compare.csv'))))
for al, ap, mu, lam, H, rrl in [(0.0, 1.0, 4.0, 0.0, 2.0, True), (0.3, 1.0, 4.0, 0.0, 3.0, True),
                                (0.2, 0.8, 4.0, 0.5, 3.0, False), (0.2, 0.6, 4.0, 0.5, 3.0, False)]:
    ex = [float(r['CR']) for r in rows if float(r['alpha']) == al and float(r['mu']) == mu and float(r['H']) == H
          and float(r['tau']) == 0 and (r.get('allow_p', '') == 'False') == rrl and (rrl or (float(r['ap']) == ap and float(r['lam']) == lam))]
    P = dict(b=1.0, a=al, ap=ap, mu=mu, lam=lam, rrl=rrl)
    v12 = lb_F1F2(dict(b=1.0, a=al, ap=ap, mu=mu, lam=lam, p=not rrl), H)
    v123, info = lb_all(P, H)
    log(f'   alpha={al} ap={ap} mu={mu} lam={lam} H={H} RRL={rrl}: exact (dt=0.1) {ex[0]:.4f}; F1/F2 bound {v12:.4f}; '
        f'F1/F2/F3 bound {v123:.4f} (binding {info["binding"]})')

open(os.path.join(HERE, 'out', 'recheck_c2.txt'), 'w').write('\n'.join(lines) + '\n')
