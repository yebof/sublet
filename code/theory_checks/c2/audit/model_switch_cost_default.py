"""C2 with a cheaper pre-warm switch (C2-SW) at the default calibration: exact notice threshold H*_mu
(design/Sublet_design.md, Q17 and Q25; Table 3.8).

Prices are read from code/analysis/out/a5b_exposure_thresholds.json (field `inputs`): alpha = a0/q_GPU = 2.85/7.15,
alpha_p = 5.97/7.15, phi = 1.  C2 units: q = 1, beta = beta~ = 1.  With beta_jl = 0 the core loading cost is
beta~ = lambda (alpha + phi), so lambda = 1/(alpha + phi) = 0.715 beta~ (a5b's lambda_C2), and a pre-warm into
protected capacity that pays protected rent during the load costs bw = alpha_p/(alpha + phi) = 0.597 beta~
(a5b field `prewarm_switch_cost_over_beta_tilde`).  With one-off fees f = beta_jl > 0 the same model gives
lambda < 0.715 and bw = f + lambda alpha_p = 1 - lambda (1 + alpha - alpha_p); those "consistent" pairs are
added for lambda = 0.25 and 0.5 (the two load times of the alpha = 1/3 runs in model_switch_cost.txt quoted in
the design document).  Fresh loads (protected from fallback, revocable) still cost beta in this model.

Solver: model_switch_cost.solve_det_bw (det_game.solve_det with full_plans=False and switch cost bw for the
algorithm's and OPT's switches; planned pre-notice upgrades belong to the insurance class, whose ratio is at
least alpha_p/alpha = 2.09 > 2 - alpha).  dt = 0.05.  alpha is not 1/3, so s0 = beta/(1-alpha) is not on the grid
for beta = 1; the game is scale-invariant (q = 1, every other quantity is a time or a cost), so it is solved with
beta_s = 1.65 (1 - alpha) = 0.992, which puts s0 = 1.65 on the grid, and every result is divided by beta_s.  The
default-calibration rows (lambda = 0.715, bw in {1, 0.597}) are repeated with beta_s = 1.70 (1 - alpha) (s0 = 1.70 on the
grid), which shifts the grid relative to the threshold; the intersection of the two brackets is reported.

Threshold: H*_exact = first H on the 0.05 grid (in beta_s units) with exact CR <= 2 - alpha + 1e-4.  CR is
non-increasing in H, so the script first evaluates the grid point g at or above the C2-SW substitution formula
and g - 0.05; if CR(g) passes and CR(g - 0.05) fails, H*_exact = g (what a full bisection returns); otherwise it
bisects the H grid [0, 8] (in beta_s units).  "agree" means H*_exact = g, i.e. the formula lies in
(H*_exact - 0.05, H*_exact] in beta_s units.  bw = 1 is Theorem 4 (C2-T4) and checks the solver at these prices.

Formula: C2-T4 with bw substituted in OPT's pre-warm branch L3 and in the warm terms (c2_single_site.md section 6,
"Switch cost"; identical to a5b_exposure_thresholds.c2_hstar and recheck_c2.thm4).
The default-calibration block prints the brackets of H*_mu / lambda to 3 decimals; the block "exact_full_precision"
after it repeats them with every digit (Python repr), so that code/analysis/a11_calibration.py can check
lo < formula <= hi at full precision instead of at the 3-decimal print resolution.
Output: audit/out/model_switch_cost_default.txt (about 10 min on 4 cores)."""
import os, sys, json, math
os.environ['OMP_NUM_THREADS'] = '1'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import numpy as np
from multiprocessing import Pool
from model import Params
import det_game
from model_switch_cost import solve_det_bw

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
A5B = json.load(open(os.path.join(ROOT, 'code', 'analysis', 'out', 'a5b_exposure_thresholds.json')))
AL, AP, PHI = A5B['inputs']['alpha'], A5B['inputs']['alpha_p'], A5B['inputs']['phi']
BW_DEF = A5B['prewarm_switch_cost_over_beta_tilde']        # alpha_p / (alpha + phi) = 0.597
LAM_DEF = 1 / (AL + PHI)                                    # lambda / beta~ with beta_jl = 0
F_BETA = A5B['H_star_beta_over_lambda_plus_tau']            # H*_beta = F_BETA lambda - tau
TAU_S = A5B['inputs']['tau_s']
DT = 0.05
BS = 1.65 * (1 - AL)                                        # beta_s: s0 = 1.65 on the grid
BS2 = 1.70 * (1 - AL)                                       # second grid offset: s0 = 1.70 on the grid
C = 2 - AL
TOL = 1e-4
HMAX = 8.0


def c2sw(mu, lam, bw, a=AL, ap=AP, b=1.0):
    """C2-T4 threshold with switch cost bw (bw = b: Theorem 4; bw < b: C2-SW substitution, CONJECTURE)."""
    s0, chi, rw = b / (1 - a), (2 - a) * ap - a, (2 - a) * b / (1 - a) ** 2
    div = lambda x, y: x / y if y != 0 else (math.inf if x > 0 else -math.inf)
    h = lambda r: r - s0 if r <= rw + 1e-12 else r
    rc = max(s0 + mu / (2 * (1 - a)), div(mu + a * b - (2 - a) * bw, a * (1 - a)), (mu + a * b) / chi)
    rh = max(s0 + bw / (2 * (1 - a)), (a * b + bw) / chi, lam + div(a * b + bw, a * (1 - a)) if lam > 0 else -math.inf)
    hc, hh = h(rc), max(lam, h(rh))
    react, r = ('cold', rc) if hc <= hh else ('pre-warm', rh)
    return dict(H=min(hc, hh), Hc=hc, Hh=hh, react=react, regime='sit-out' if r <= rw + 1e-12 else 'known window')


def cr(mu, lam, bw, H, bs=BS):
    """exact CR at notice H (beta_s units); inputs mu, lam, bw in beta~ units"""
    P = Params(H=H, alpha=AL, ap=AP, mu=mu * bs, lam=lam * bs, beta=bs)
    Rmax = H + 6.0
    return solve_det_bw(P, bw * bs, dt=DT, T=Rmax + 7.0, Rmax=Rmax)


def job(args):
    mu, lam, bw, label, bs = args
    f = c2sw(mu, lam, bw)
    g = round(math.ceil(f['H'] * bs / DT - 1e-9) * DT, 10)
    Hs = np.round(np.arange(0, HMAX + 1e-9, DT), 10)
    memo = {}

    def val(H):
        H = round(float(H), 10)
        if H not in memo:
            memo[H] = cr(mu, lam, bw, H, bs)
        return memo[H]['CR']
    ok = lambda H: val(H) <= C + TOL
    if g <= HMAX and ok(g) and (g == 0 or not ok(round(g - DT, 10))):
        hx = g
    else:
        lo, hi = 0, len(Hs) - 1
        if not ok(Hs[hi]):
            hx = math.inf
        elif ok(Hs[0]):
            hx = 0.0
        else:
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if ok(Hs[mid]):
                    hi = mid
                else:
                    lo = mid
            hx = float(Hs[hi])
    below = memo.get(round(hx - DT, 10), {}).get('CR', float('nan')) if np.isfinite(hx) else float('nan')
    at = memo.get(round(hx, 10), {}).get('CR', float('nan')) if np.isfinite(hx) else float('nan')
    plan = memo.get(round(hx, 10), {}).get('plan') if np.isfinite(hx) else None
    return dict(mu=mu, lam=lam, bw=bw, label=label, bs=bs, f=f, g=g, hx=hx, below=below, at=at, plan=plan, nsolve=len(memo))


def jobs():
    J = []
    for mu in [0.2, 0.5, 1.0, 2.0]:                      # default calibration (beta_jl = 0): lambda = 1/(alpha+phi)
        for bw, lab in [(1.0, 'switch beta~ (Thm 4)'), (0.8, ''), (0.6, ''), (BW_DEF, 'default switch'), (0.2, '')]:
            J.append((mu, LAM_DEF, bw, lab, BS))
    for lam in [0.25, 0.5]:                               # the two load times of the alpha = 1/3 runs
        for mu in [0.5, 1.0, 2.0]:
            for bw in [1.0, 0.8, 0.6, 0.2]:
                J.append((mu, lam, bw, 'switch beta~ (Thm 4)' if bw == 1.0 else '', BS))
            J.append((mu, lam, 1 - lam * (1 + AL - AP), 'consistent with fees', BS))
    for mu in [0.2, 0.5, 1.0, 2.0]:                      # second grid offset, default calibration
        for bw, lab in [(1.0, 'switch beta~ (Thm 4), s0 = 1.70 grid'), (BW_DEF, 'default switch, s0 = 1.70 grid')]:
            J.append((mu, LAM_DEF, bw, lab, BS2))
    return J


if __name__ == '__main__':
    lines = []
    log = lambda s='': (print(s, flush=True), lines.append(s))
    log(f"C2-SW at the default calibration (a5b_exposure_thresholds.json): alpha={AL:.6f} alpha_p={AP:.6f} phi={PHI}; "
        f"2-alpha={C:.6f}; s0={1 / (1 - AL):.4f} beta~; R_wait={(2 - AL) / (1 - AL) ** 2:.4f} beta~; "
        f"chi={(2 - AL) * AP - AL:.4f}")
    log(f"units: beta~ = 1 (q = 1); default lambda = 1/(alpha+phi) = {LAM_DEF:.4f}; default switch bw = alpha_p/(alpha+phi) = {BW_DEF:.4f}; "
        f"solver scale beta_s = {BS:.6f} (s0 = 1.65 on the dt = {DT} grid); grid step in beta~ = {DT / BS:.4f}")
    # sanity 1: formula reproduces a5b (switch beta~ and C2-SW at bw = 0.597, lambda = lambda_C2)
    for key, bw in (('switch_beta_tilde', 1.0), ('switch_full_model_C2SW_conjecture', BW_DEF)):
        d = max(abs(c2sw(float(m), LAM_DEF, bw)['H'] / LAM_DEF - v['H_over_lambda'])
                for m, v in A5B['H_star_mu_over_lambda'][key].items())
        log(f"sanity: formula vs a5b `H_star_mu_over_lambda.{key}` (mu/beta~ in 0.2/0.5/1/2): max |diff| = {d:.1e} (in lambda)")
    # sanity 2: solve_det_bw with bw = beta reproduces det_game.solve_det at these prices
    for mu, H in [(2.0, 1.0), (1.0, 0.5)]:
        P = Params(H=H, alpha=AL, ap=AP, mu=mu * BS, lam=LAM_DEF * BS, beta=BS)
        r0 = det_game.solve_det(P, dt=DT, T=H + 13.0, Rmax=H + 6.0, full_plans=False)['CR']
        r1 = solve_det_bw(P, BS, dt=DT, T=H + 13.0, Rmax=H + 6.0)['CR']
        log(f"sanity: bw=beta, mu={mu} beta~, lambda={LAM_DEF:.4f} beta~, H={H} beta_s: det_game {r0:.6f} variant {r1:.6f} diff {r1 - r0:+.1e}")
    log()
    log("Columns: mu, lambda, bw in beta~ | formula H*/beta~, H*/lambda, reaction, regime | exact: H* bracket (H*_exact - grid, H*_exact] "
        "in beta~ and in lambda | agree = H*_exact is the grid point at or above the formula | exact CR one grid step below and at H*_exact | plan at H*_exact")
    with Pool(4) as p:
        res = list(p.imap(job, jobs()))
    nagree = 0
    for r in res:
        f, hx = r['f'], r['hx']
        agree = np.isfinite(hx) and abs(hx - r['g']) < 1e-9
        nagree += agree
        lo, hi = (hx - DT) / r['bs'], hx / r['bs']
        log(f"mu={r['mu']:.2f} lam={r['lam']:.4f} bw={r['bw']:.4f} {('[' + r['label'] + ']') if r['label'] else ''}| "
            f"formula {f['H']:.4f} = {f['H'] / r['lam']:.3f} lam, {f['react']}, {f['regime']} | "
            f"exact ({lo:.4f}, {hi:.4f}] = ({lo / r['lam']:.3f}, {hi / r['lam']:.3f}] lam | {'agree' if agree else 'DIFFER'} | "
            f"CR {r['below']:.5f} / {r['at']:.5f} (2-a {C:.5f}) | {r['plan']} | solves {r['nsolve']}")
    log()
    log(f"summary: {nagree} of {len(res)} exact thresholds equal the C2-SW formula rounded up to the grid "
        f"(bw = 1: Theorem 4; bw < 1: substitution formula)")
    # default calibration: H*_mu / lambda for Table 3.8 and the order against H*_beta = F_BETA lambda - tau
    log()
    log(f"default calibration (lambda = {LAM_DEF:.4f} beta~): H*_mu/lambda, formula [exact bracket, intersection of the s0 = 1.65 and 1.70 grids]; "
        f"H*_beta = {F_BETA:.4f} lambda - tau (tau = {TAU_S:.0f} s); H*_mu < H*_beta iff lambda > tau/({F_BETA:.4f} - H*_mu/lambda)")
    fullp = []
    for bw, key in ((1.0, 'switch_beta_tilde'), (BW_DEF, 'switch_full_model_C2SW_conjecture')):
        for r in res:
            if abs(r['lam'] - LAM_DEF) > 1e-12 or abs(r['bw'] - bw) > 1e-12 or r['bs'] != BS:
                continue
            c = r['f']['H'] / LAM_DEF
            rr = [q for q in res if q['mu'] == r['mu'] and abs(q['lam'] - LAM_DEF) < 1e-12 and abs(q['bw'] - bw) < 1e-12]
            lo = max((q['hx'] - DT) / q['bs'] / LAM_DEF for q in rr)
            hi = min(q['hx'] / q['bs'] / LAM_DEF for q in rr)
            a5b = A5B['H_star_mu_over_lambda'][key][str(r['mu'])]['H_over_lambda'] if str(r['mu']) in A5B['H_star_mu_over_lambda'][key] else float('nan')
            cross = f"lambda > {TAU_S / (F_BETA - c):.1f} s" if c < F_BETA else "never (H*_mu > H*_beta for every lambda)"
            crossx = (f"[{TAU_S / (F_BETA - lo):.1f}, {TAU_S / (F_BETA - hi):.1f}] s" if hi < F_BETA else
                      ("never" if lo >= F_BETA else "bracket straddles 3.51"))
            log(f"bw={bw:.3f} mu={r['mu']:.1f}: formula {c:.3f} lam (a5b {a5b:.3f}) exact ({lo:.3f}, {hi:.3f}] lam; "
                f"H*_mu < H*_beta: {cross} (exact bracket {crossx})")
            fullp.append((bw, r['mu'], c, lo, hi))
    log()
    log("exact_full_precision: the brackets above with every digit (H*_mu/lambda; formula, then (lo, hi]); read by "
        "code/analysis/a11_calibration.py, check 3")
    for bw, mu, c, lo, hi in fullp:
        log(f"full bw={bw!r} mu={mu!r}: formula {c!r} exact ({lo!r}, {hi!r}]")
    # one-off fees beta_jl > 0: lambda < 1/(alpha+phi), bw = fees + lambda alpha_p; order against H*_beta = beta~/(g a) - tau
    log()
    log(f"with one-off fees f = 1 - lambda (alpha + phi) (bw = f + lambda alpha_p): H*_beta = beta~/(g a) - tau = {1 / AL:.4f} beta~ - tau "
        f"(beta~ read as beta~/q, a time); H*_mu < H*_beta iff beta~/q > tau/(1/alpha - H*_mu/beta~), never if H*_mu >= beta~/alpha")
    for r in res:
        if r['bs'] != BS or r['label'] not in ('consistent with fees', 'default switch'):
            continue
        h = r['f']['H']
        lo, hi = (r['hx'] - DT) / BS, r['hx'] / BS
        cmp = f"beta~/q > {TAU_S / (1 / AL - h):.1f} s" if h < 1 / AL else "never"
        log(f"lam={r['lam']:.4f} beta~ (f = {1 - r['lam'] * (AL + PHI):.3f} beta~) bw={r['bw']:.4f} mu={r['mu']:.1f}: H*_mu = {h:.3f} beta~ "
            f"(exact ({lo:.3f}, {hi:.3f}]), {r['f']['react']}, {r['f']['regime']}; H*_mu < H*_beta iff {cmp}")
    out =os.path.join(HERE, 'out', 'model_switch_cost_default.txt')
    open(out, 'w').write('\n'.join(lines) + '\n')
