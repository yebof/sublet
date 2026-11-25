"""C2 Table PoR at the default prices, and whether up-front insurance binds there (design/Sublet_design.md, Q25).

Table PoR of design/theory/c2_single_site.md section 7 was computed at alpha = 0.3, alpha_p = 0.7 (tables.py por ->
out/table_por.txt).  This script recomputes it at the default prices of the design, read from
code/analysis/out/a5b_exposure_thresholds.json (field `inputs`): alpha = 2.85/7.15 = 0.3986, alpha_p = 5.97/7.15 = 0.8350.
C2-T2: insuring up front has ratio CR_ins = max(2 - alpha, alpha_p/alpha) = 2.0947, and CR* = min(CR_ins, CR_react).
Insurance binds where CR_react(H) > CR_ins.

Units: q = 1, beta~ = 1 (C2's beta).  The default load time is lambda = 1/(alpha + phi) = 0.715 beta~ (no one-off fees),
and the default pre-warm switch cost is bw = alpha_p/(alpha + phi) = 0.597 beta~; with one-off fees the consistent pairs
are (lambda, bw) = (0.5, 0.718) and (0.25, 0.859) (audit/model_switch_cost_default.py, whose constants and C2-SW formula
c2sw are imported here).  mu/beta~ in {0.2, 0.5, 1, 2} (a5b `inputs.mu_over_beta_tilde`).

Parts (tau = 0 throughout):
  A  Table PoR in C2's stated model (a switch costs beta~), mu x lambda in {0, 0.25, 0.5, 0.715} x H.  Per cell:
     exact deterministic game (det_game.solve_det, dt = 0.05, full_plans=False; planned pre-notice upgrades belong to
     the insurance class) with the best reactive and the best insuring plan separately; family bound
     min(CR_ins, LB_react) of families.lb_total (C2-T3, grid over the algorithm only); rigorous interval bound on
     CR_react from audit/necessity_lb.lb_all (F1, F2, F3; include_insure=False); the two-family closed form of C2 section 5.
  B  Same table under the default switch cost (C2-SW model: OPT's and the algorithm's pre-warm switch costs bw, fresh
     loads beta~), solver audit/model_switch_cost.solve_det_bw (dt = 0.05), for (lambda, bw) = (0.715, 0.597),
     (0.5, 0.718), (0.25, 0.859).  The solver returns only CR* and the optimal plan; a cell's insurance flag is the
     plan type.  Lower bound on CR_react: lb_react_interval below (F1 and F2 at the demand ends E^+ and (E-lambda)^+,
     interval arithmetic over the algorithm's purchase time s, OPT replaced by actual OPT runs of the bw model; it is
     audit/lb_rigorous.lb with the switch cost bw in OPT's pre-warm branch and in the warm reaction, and with bw = beta~
     it reproduces necessity_lb.lb_all without F3).
  C  Crossover in mu: the smallest mu at which insurance binds, per H.  Rigorous side: bisection on mu of the reactive
     lower bound against CR_ins (lb_all for switch beta~, lb_react_interval for bw); mu at or above it => insurance is
     optimal (certified).  Exact side: bisection on mu in [0, 4] of "the exact game's optimal plan insures"
     (resolution 0.01 beta~), lambda = 0.715, both switch costs.
  D  Notice below which insurance binds at mu = 2 beta~ under the default switch (lambda = 0.715, bw = 0.597): exact game
     scanned upward on the H grid (0.05 beta_s) until the optimal plan stops insuring (CR is non-increasing in H);
     rigorous side: bisection on H in [0, lambda) of lb_react_interval >= CR_ins.
The closed form is reported twice: with the m of the proven two-family bound (m = mu if H < lambda, min(mu, beta)
otherwise) and with the convention of make_doc_tables.py for the alpha = 0.3 table (m = mu if lambda > 0, min(mu, beta)
if lambda = 0).

Grid: the game is scale-invariant (q = 1; every other quantity is a time or a cost), so it is solved with
beta_s = 1.65 (1 - alpha) = 0.9923, which puts s0 = beta/(1-alpha) on the dt = 0.05 grid (as in
audit/model_switch_cost_default.py).  H is on the grid in beta_s units, {0, .25, .5, .75, 1, 1.5, 2, 3} (plus 4, 4.5, ...
for rows whose threshold exceeds 3), and is reported in beta~ (H/beta_s) and in lambda.  T = H + 13, Rmax = H + 6.
Output: out/por_default.txt (raw rows, markdown tables, answer), out/por_default.json.  About 20 min on 4 cores.
Run: python por_default.py  (from anywhere)."""
import os, sys, json, math, time
os.environ['OMP_NUM_THREADS'] = '1'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'audit'))
import numpy as np
from multiprocessing import Pool
from model import Params
from det_game import solve_det
from families import lb_total
from necessity_lb import lb_all
from model_switch_cost import solve_det_bw
from model_switch_cost_default import c2sw, AL, AP, PHI, BW_DEF, LAM_DEF, A5B

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
A5B_PATH = 'code/analysis/out/a5b_exposure_thresholds.json'
DT = 0.05
BS = 1.65 * (1 - AL)                      # beta_s: s0 = 1.65 on the grid
C = 2 - AL
CR_INS = max(C, AP / AL)
S0 = 1 / (1 - AL)
MUS = [float(m) for m in A5B['inputs']['mu_over_beta_tilde']]
LAMS = [0.0, 0.25, 0.5, LAM_DEF]
BW_ROWS = [(LAM_DEF, BW_DEF, 'default (no fees)')] + [(l, 1 - l * (1 + AL - AP), 'consistent with fees') for l in (0.5, 0.25)]
H_BASE = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]   # beta_s units, on the grid
TOL = 1e-9


def dn(x, d):
    """x rounded down to d decimals (outward for a lower end or a certified upper bound such as H <= H_c)."""
    return f"{math.floor(x * 10 ** d + 1e-9) / 10 ** d:.{d}f}"


def up(x, d):
    """x rounded up to d decimals (outward for an upper end or a certified lower bound such as mu >= mu_c)."""
    return f"{math.ceil(x * 10 ** d - 1e-9) / 10 ** d:.{d}f}"


def h_grid(hstar):
    """base grid, extended in steps of 0.5 (beta_s units) past the threshold when it exceeds 3"""
    g = list(H_BASE)
    top = hstar * BS
    if top > 3.0:
        h = 4.0
        while h <= math.ceil(top / 0.5) * 0.5 + 1e-9:
            g.append(h); h += 0.5
    return g


def params(mu, lam, Hs):
    return Params(H=Hs, alpha=AL, ap=AP, mu=mu * BS, lam=lam * BS, beta=BS)


def quad(H, m, a=AL, b=1.0):
    """two-family closed form of C2 section 5 (C2-T3): max(2 - a, (s* + b)/(b + a s*))"""
    A = 1 - a; B = H * (1 - a * a) - a * (b + m); Cq = b * (H * (1 - a) - b - m)
    s = (-B + math.sqrt(B * B - 4 * A * Cq)) / (2 * A)
    return max(2 - a, (s + b) / (b + a * s))


def lb_react_interval(mu, lam, H, bw, a=AL, ap=AP, b=1.0, S=60.0, n=600001):
    """Rigorous lower bound on CR_react (algorithms that do not insure before a notice), tau = 0, switch cost bw.
    F1: R = inf, x = s^+.  F2: notice at s^+, R = E = s + H; cold reaction at x = E^+ (pays mu), pre-warm (needs H >= lam;
    commit at E - lam costs bw) at x = (E - lam)^+ and E^+.  OPT(E^+, E) <= min(E, b + aE + mu, b + ap E, b + bw + aE [E >= lam]),
    all actual OPT runs of the bw model; OPT(y^+) = min(y, b + a y) for y < E.  Interval method of audit/lb_rigorous.py:
    on [s_i, s_i+1] each numerator and each OPT branch is nondecreasing in s, so ratio >= num(s_i)/den(s_i+1).
    s >= S: F1 is nondecreasing beyond s0; s = inf (never buy): 1/a."""
    s = np.linspace(1e-6, S, n)
    lo, hi = s[:-1], s[1:]
    F1 = (lo + b) / np.minimum(hi, b + a * hi)
    Elo, Ehi = lo + H, hi + H
    O = np.minimum(np.minimum(Ehi, b + a * Ehi + mu), b + ap * Ehi)
    O = np.where(Elo >= lam, np.minimum(O, b + bw + a * Ehi), O)
    F2 = (lo + b + a * H + mu) / O
    if H >= lam:
        w = (lo + b + bw + a * H) / O
        if lam > 0:
            yhi = hi + H - lam
            w = np.maximum(w, (lo + b + bw + a * (H - lam)) / np.minimum(yhi, b + a * yhi))
        F2 = np.minimum(F2, w)
    v = float(np.maximum(F1, F2).min())
    return min(v, (S + b) / (b + a * S), 1 / a)


def lb_rig(mu, lam, H, bw):
    """reactive lower bound: lb_all (F1, F2, F3) for bw = beta~, lb_react_interval otherwise"""
    if bw is None:
        return float(lb_all(dict(b=1.0, a=AL, ap=AP, mu=mu, lam=lam, rrl=False), H, include_insure=False)[0])
    return lb_react_interval(mu, lam, H, bw)


def exact(mu, lam, Hs, bw):
    P = params(mu, lam, Hs)
    if bw is None:
        r = solve_det(P, dt=DT, T=Hs + 13.0, Rmax=Hs + 6.0, full_plans=False, return_detail=True)
        return dict(CR=r['CR'], plan=r['plan'], CR_react=r['CR_react_class'], CR_ins=r['CR_ins_class'])
    r = solve_det_bw(P, bw * BS, dt=DT, T=Hs + 13.0, Rmax=Hs + 6.0)
    return dict(CR=r['CR'], plan=r['plan'], CR_react=None, CR_ins=None)


def job(j):
    t0 = time.time()
    kind = j[0]
    if kind == 'cell':
        _, mu, lam, bw, Hs = j
        H = Hs / BS
        e = exact(mu, lam, Hs, bw)
        out = dict(kind=kind, mu=mu, lam=lam, bw=bw, Hs=Hs, H=H, **e)
        out['plan_type'] = e['plan'][0]
        out['plan_s'] = (e['plan'][1] / BS) if len(e['plan']) > 1 else None
        out['LB_react_rig'] = lb_rig(mu, lam, H, bw)
        if bw is None:
            lb, lr, _ = lb_total(Params(H=H, alpha=AL, ap=AP, mu=mu, lam=lam, beta=1.0))
            out['LB_family'], out['LB_react_family'] = float(lb), float(lr)
            m = mu if H < lam else min(mu, 1.0)
            out['closed_form'] = quad(H, m)
            out['closed_form_doc'] = quad(H, mu if lam > 0 else min(mu, 1.0))
            out['LB_react_interval_bw1'] = lb_react_interval(mu, lam, H, 1.0)
        out['sec'] = time.time() - t0
        return out
    if kind == 'bis_rig':
        _, lam, bw, Hs = j
        H = Hs / BS
        f = lambda mu: lb_rig(mu, lam, H, bw) >= CR_INS
        grid = [0.25 * k for k in range(1, 41)]                     # monotonicity check on mu in (0, 10]
        flags = [f(m) for m in grid]
        mono = all(not (flags[i] and not flags[i + 1]) for i in range(len(flags) - 1))
        hi = 20.0
        if not f(hi):
            return dict(kind=kind, lam=lam, bw=bw, Hs=Hs, H=H, mu_c=None, mono=mono, sec=time.time() - t0)
        lo = 0.0
        while hi - lo > 1e-3:
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if f(mid) else (mid, hi)
        return dict(kind=kind, lam=lam, bw=bw, Hs=Hs, H=H, mu_c=hi, mono=mono, sec=time.time() - t0)
    if kind == 'bis_exact':
        _, lam, bw, Hs = j
        memo = {}

        def ins(mu):
            mu = round(mu, 6)
            if mu not in memo:
                memo[mu] = exact(mu, lam, Hs, bw)
            return memo[mu]['plan'][0] == 'p'
        lo, hi = 0.0, 4.0
        if not ins(hi):
            return dict(kind=kind, lam=lam, bw=bw, Hs=Hs, H=Hs / BS, mu_lo=hi, mu_hi=None, CR_lo=memo[round(hi, 6)]['CR'],
                        CR_hi=None, nsolve=len(memo), sec=time.time() - t0)
        while hi - lo > 0.01 + 1e-9:
            mid = round((lo + hi) / 2, 6)
            lo, hi = (lo, mid) if ins(mid) else (mid, hi)
        return dict(kind=kind, lam=lam, bw=bw, Hs=Hs, H=Hs / BS, mu_lo=lo, mu_hi=hi,
                    CR_lo=memo[round(lo, 6)]['CR'] if round(lo, 6) in memo else None, CR_hi=memo[round(hi, 6)]['CR'],
                    nsolve=len(memo), sec=time.time() - t0)
    if kind == 'hscan_exact':
        _, mu, lam, bw = j
        rows = []
        Hs = 0.0
        while Hs <= 2.0 + 1e-9:
            e = exact(mu, lam, Hs, bw)
            rows.append(dict(Hs=Hs, H=Hs / BS, CR=e['CR'], plan_type=e['plan'][0]))
            if e['plan'][0] != 'p':
                break
            Hs = round(Hs + DT, 10)
        return dict(kind=kind, mu=mu, lam=lam, bw=bw, rows=rows, sec=time.time() - t0)
    if kind == 'hbis_rig':
        _, mu, lam, bw = j
        f = lambda H: lb_react_interval(mu, lam, H, bw) >= CR_INS
        grid = [0.01 * k for k in range(int(lam / 0.01) + 1)]
        flags = [f(h) for h in grid]
        mono = all(not (not flags[i] and flags[i + 1]) for i in range(len(flags) - 1))
        if not f(0.0):
            return dict(kind=kind, mu=mu, lam=lam, bw=bw, H_c=None, mono=mono, sec=time.time() - t0)
        lo, hi = 0.0, lam
        while hi - lo > 1e-4:
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return dict(kind=kind, mu=mu, lam=lam, bw=bw, H_c=lo, mono=mono, sec=time.time() - t0)
    raise ValueError(kind)


def jobs():
    J = []
    for lam, bw, _ in BW_ROWS:
        for mu in MUS:
            for Hs in h_grid(c2sw(mu, lam, bw)['H']):
                J.append(('cell', mu, lam, bw, Hs))
    for mu in MUS:
        for lam in LAMS:
            for Hs in H_BASE:
                J.append(('cell', mu, lam, None, Hs))
    for bw in (None, BW_DEF):
        for Hs in [0.0, 0.25, 0.5, 0.75, 1.0, 1.5]:
            J.append(('bis_exact', LAM_DEF, bw, Hs))
    for lam in LAMS:
        for Hs in H_BASE:
            J.append(('bis_rig', lam, None, Hs))
    for lam, bw, _ in BW_ROWS:
        for Hs in H_BASE:
            J.append(('bis_rig', lam, bw, Hs))
    J += [('hscan_exact', 2.0, LAM_DEF, BW_DEF), ('hbis_rig', 2.0, LAM_DEF, BW_DEF)]
    cost = lambda j: 1 if j[0] in ('hscan_exact', 'hbis_rig') else (2 if j[0] == 'bis_exact' else 1) * (j[-1] + 4)   # longest first
    return sorted(J, key=cost, reverse=True)


def fmt_plan(r):
    return f"{r['plan_type']}@{r['plan_s']:.3f}" if r['plan_s'] is not None else r['plan_type']


if __name__ == '__main__':
    t0 = time.time()
    with Pool(4) as p:
        res = list(p.imap_unordered(job, jobs()))
    cells_b = sorted([r for r in res if r['kind'] == 'cell' and r['bw'] is None], key=lambda r: (r['mu'], r['lam'], r['Hs']))
    cells_w = sorted([r for r in res if r['kind'] == 'cell' and r['bw'] is not None], key=lambda r: (-r['lam'], r['mu'], r['Hs']))
    bis_e = sorted([r for r in res if r['kind'] == 'bis_exact'], key=lambda r: (r['bw'] is not None, r['Hs']))
    bis_r = sorted([r for r in res if r['kind'] == 'bis_rig'], key=lambda r: (r['bw'] is not None, -(r['bw'] or 0), r['lam'], r['Hs']))
    hscan = next(r for r in res if r['kind'] == 'hscan_exact')
    hbis = next(r for r in res if r['kind'] == 'hbis_rig')

    L = []
    log = lambda s='': (print(s, flush=True), L.append(s))
    log(f"C2 Table PoR at the default prices ({A5B_PATH}, field `inputs`): alpha={AL:.6f} alpha_p={AP:.6f} phi={PHI}")
    log(f"2-alpha={C:.6f}; CR_ins = max(2-alpha, alpha_p/alpha) = {CR_INS:.6f}; s0={S0:.4f} beta~; tau=0; units q=1, beta~=1; "
        f"default lambda={LAM_DEF:.4f} beta~, default switch bw={BW_DEF:.4f} beta~")
    log(f"exact game: dt={DT} in beta_s = {BS:.6f} beta~ (s0 = 1.65 on the grid; grid step {DT / BS:.4f} beta~); H on the grid in beta_s, "
        f"reported in beta~ (= H_s/beta_s) and in lambda (lambda = {LAM_DEF:.4f})")
    # sanity checks
    d1 = max(abs(r['LB_react_interval_bw1'] - r['LB_react_rig']) for r in cells_b)
    d1F3 = max(r['LB_react_rig'] - r['LB_react_interval_bw1'] for r in cells_b)
    log(f"sanity: lb_react_interval with bw = beta~ vs necessity_lb.lb_all (F1-F3) over the {len(cells_b)} part-A cells: "
        f"max |diff| = {d1:.1e}, max(lb_all - interval) = {d1F3:+.1e} (lb_all also has the known-window family F3; it raises no cell)")
    gins = max(abs(r['CR_ins'] - CR_INS) for r in cells_b)
    log(f"sanity: exact best insuring plan vs CR_ins over part A: max |diff| = {gins:.1e} (the sup is at x -> inf; the grid stops at x = 1e5)")
    viol = min(r['CR_react'] - r['LB_react_rig'] for r in cells_b)
    violw = min(r['CR'] - min(CR_INS, r['LB_react_rig']) for r in cells_w)
    log(f"sanity: exact CR_react - rigorous LB_react >= {viol:+.5f} (part A); exact CR* - min(CR_ins, LB_react) >= {violw:+.5f} (part B)")
    log()

    # ---- Part A raw
    log("PART A. switch cost beta~ (C2's stated model). Columns: mu lam H_s | H/beta~ | exact CR*, best reactive, best insuring, plan "
        "(type@s in beta~) | family bound min(CR_ins, LB_react), LB_react (families.lb_total) | rigorous LB_react (lb_all) | "
        "closed form (proven m), closed form (m of the alpha = 0.3 table) | PoR exact, PoR bound | insurance optimal")
    for r in cells_b:
        log(f"{r['mu']:g} {r['lam']:.4f} {r['Hs']:g} | {r['H']:.4f} | {r['CR']:.4f} {r['CR_react']:.4f} {r['CR_ins']:.4f} {fmt_plan(r)} | "
            f"{r['LB_family']:.4f} {r['LB_react_family']:.4f} | {r['LB_react_rig']:.4f} | {r['closed_form']:.4f} {r['closed_form_doc']:.4f} | "
            f"{r['CR'] / C:.4f} {r['LB_family'] / C:.4f} | {r['plan_type'] == 'p'}")
    log()
    # ---- Part A markdown (rows with identical cells across lambda merged)
    Hb = sorted({r['Hs'] for r in cells_b})
    log(f"Markdown, part A. Each cell: family bound min(CR_ins, LB_react) / exact game (dt = 0.05) / PoR = bound/(2-alpha). "
        f"CR_ins = {CR_INS:.4f}.")
    log("| $\\mu/\\tilde\\beta$, $\\lambda/\\tilde\\beta$ | $H^\\star_\\mu$ | " + " | ".join(f"$H={h / BS:.3f}$" for h in Hb) + " |")
    log("|---|---|" + "---|" * len(Hb))
    md_rows_b = []
    for mu in MUS:
        groups = []
        for lam in LAMS:
            rr = [next(r for r in cells_b if r['mu'] == mu and r['lam'] == lam and r['Hs'] == h) for h in Hb]
            key = tuple((round(r['LB_family'], 4), round(r['CR'], 4)) for r in rr)
            for g in groups:
                if g['key'] == key and abs(c2sw(mu, g['lams'][0], 1.0)['H'] - c2sw(mu, lam, 1.0)['H']) < 1e-9:
                    g['lams'].append(lam); break
            else:
                groups.append(dict(key=key, lams=[lam], rr=rr))
        for g in groups:
            hs = c2sw(mu, g['lams'][0], 1.0)['H']
            lab = f"{mu:g}, " + ("{" + ", ".join(f"{l:g}" for l in g['lams']) + "}" if len(g['lams']) > 1 else f"{g['lams'][0]:g}")
            log(f"| {lab} | {hs:.3f} | " + " | ".join(f"{r['LB_family']:.4f} / {r['CR']:.4f} / {r['LB_family'] / C:.3f}" for r in g['rr']) + " |")
            md_rows_b.append(dict(mu=mu, lams=g['lams'], Hstar=hs))
    log()

    # ---- Part B raw + markdown
    log(f"PART B. default switch cost (C2-SW model; solve_det_bw). Columns: mu lam bw H_s | H/beta~ H/lambda | exact CR*, plan | "
        f"rigorous LB_react (lb_react_interval, bw) | PoR exact | insurance optimal")
    for r in cells_w:
        log(f"{r['mu']:g} {r['lam']:.4f} {r['bw']:.4f} {r['Hs']:g} | {r['H']:.4f} {r['H'] / r['lam']:.3f} | {r['CR']:.4f} {fmt_plan(r)} | "
            f"{r['LB_react_rig']:.4f} | {r['CR'] / C:.4f} | {r['plan_type'] == 'p'}")
    log()
    log("Markdown, part B. Each cell: exact game CR* (dt = 0.05) / PoR = CR*/(2-alpha); a cell marked (ins) is one where the optimal "
        "plan insures up front (CR* = CR_ins); H*_mu by the C2-SW formula (CONJECTURE; exact brackets in audit/out/model_switch_cost_default.txt).")
    for lam, bw, lab in BW_ROWS:
        rows = [r for r in cells_w if r['lam'] == lam]
        Hw = sorted({r['Hs'] for r in rows})
        log(f"lambda = {lam:.4f} beta~, bw = {bw:.4f} beta~ ({lab})")
        log("| $\\mu/\\tilde\\beta$ | $H^\\star_\\mu$ | " + " | ".join(f"$H={h / BS:.3f}$" for h in Hw) + " |")
        log("|---|---|" + "---|" * len(Hw))
        for mu in MUS:
            cs = []
            for h in Hw:
                r = next((r for r in rows if r['mu'] == mu and r['Hs'] == h), None)
                cs.append('' if r is None else f"{r['CR']:.4f} / {r['CR'] / C:.3f}" + (' (ins)' if r['plan_type'] == 'p' else ''))
            log(f"| {mu:g} | {c2sw(mu, lam, bw)['H']:.3f} | " + " | ".join(cs) + " |")
        log()

    # ---- Part C
    log(f"PART C. crossover in mu: smallest mu at which up-front insurance binds (CR_react >= CR_ins = {CR_INS:.4f}).")
    log("Rigorous (reactive lower bound >= CR_ins, bisection on mu in [0, 20] to 1e-3; mono = the bound's insurance flag is monotone in mu "
        "on mu = 0.25..10): for every mu >= mu_c insurance is optimal.")
    for r in bis_r:
        sw = 'beta~ (lb_all)' if r['bw'] is None else f"{r['bw']:.4f} (lb_react_interval)"
        mc = up(r['mu_c'], 3) if r['mu_c'] is not None else 'none up to 20'
        log(f"switch {sw} lam={r['lam']:.4f} H_s={r['Hs']:g} H={r['H']:.4f} beta~: mu_c = {mc} | mono={r['mono']}")
    log()
    log("Exact game (optimal plan insures; bisection on mu in [0, 4], resolution 0.01): insurance optimal for mu >= mu_hi, "
        "reactive at mu_lo; lam = default. Printed values are rounded outward: certified mu_c up, H_c down, bracket "
        "ends (mu_lo, mu_hi] down and up; the JSON has the unrounded values")
    for r in bis_e:
        sw = 'beta~' if r['bw'] is None else f"{r['bw']:.4f}"
        if r['mu_hi'] is None:
            log(f"switch {sw} H_s={r['Hs']:g} H={r['H']:.4f} beta~ = {r['H'] / LAM_DEF:.3f} lam: no insurance up to mu = 4 "
                f"(CR* at mu=4: {r['CR_lo']:.4f}) | solves {r['nsolve']}")
        else:
            log(f"switch {sw} H_s={r['Hs']:g} H={r['H']:.4f} beta~ = {r['H'] / LAM_DEF:.3f} lam: mu_c in ({dn(r['mu_lo'], 3)}, {up(r['mu_hi'], 3)}] "
                f"(CR* {r['CR_lo'] if r['CR_lo'] is not None else float('nan'):.4f} / {r['CR_hi']:.4f}) | solves {r['nsolve']}")
    log()

    # ---- Part D
    log(f"PART D. mu = 2 beta~, lambda = {LAM_DEF:.4f}, default switch bw = {BW_DEF:.4f}: notice below which insurance binds.")
    for r in hscan['rows']:
        log(f"exact: H_s={r['Hs']:g} H={r['H']:.4f} beta~ = {r['H'] / LAM_DEF:.3f} lam: CR* {r['CR']:.4f}, plan {r['plan_type']}")
    hins = [r for r in hscan['rows'] if r['plan_type'] == 'p']
    H_ins_exact = (hins[-1]['H'] if hins else None, hscan['rows'][-1]['H'])
    log(f"exact: optimal plan insures at H <= {H_ins_exact[0]:.4f} beta~ on the grid, reactive from H = {H_ins_exact[1]:.4f} beta~")
    log(f"rigorous: lb_react_interval >= CR_ins for every H <= H_c = {dn(hbis['H_c'], 4)} beta~ = {dn(hbis['H_c'] / LAM_DEF, 3)} lam "
        f"(bisection to 1e-4; flag monotone in H on a 0.01 grid: {hbis['mono']})")
    log()
    # closed-form tightness
    gaps = [(r['LB_family'] - r['closed_form_doc'], r) for r in cells_b]
    gmax, gr = max(gaps, key=lambda t: t[0])
    gapsp = [(r['LB_family'] - r['closed_form'], r) for r in cells_b]
    gpmax, gpr = max(gapsp, key=lambda t: t[0])
    ngap = sum(1 for g, _ in gaps if g > 2e-4)
    exmax = max(r['CR'] - r['LB_family'] for r in cells_b)
    log(f"closed form vs family bound (part A): with the m of the alpha = 0.3 table, family bound - closed form > 2e-4 in {ngap} of "
        f"{len(cells_b)} cells, max {gmax:+.4f} at mu={gr['mu']:g}, lam={gr['lam']:.3f}, H={gr['H']:.3f}; with the proven m, max "
        f"{gpmax:+.4f} at mu={gpr['mu']:g}, lam={gpr['lam']:.3f}, H={gpr['H']:.3f}. Exact game - family bound <= {exmax:.4f} in every cell.")
    log()
    # ---- answer
    inrange_b = [r for r in cells_b if r['mu'] <= max(MUS)]
    ins_b = [r for r in inrange_b if r['plan_type'] == 'p']
    mx = max(inrange_b, key=lambda r: r['CR_react'])
    ins_w = [r for r in cells_w if r['plan_type'] == 'p']
    log("ANSWER (Q25).")
    log(f"switch beta~: insurance optimal in {len(ins_b)} of {len(inrange_b)} cells (mu/beta~ in {MUS}); max exact CR_react = "
        f"{mx['CR_react']:.4f} at mu={mx['mu']:g}, lam={mx['lam']:.3f}, H={mx['H']:.3f} (CR_ins - max = {CR_INS - mx['CR_react']:+.4f})")
    for lam, bw, lab in BW_ROWS:
        rows = [r for r in ins_w if r['lam'] == lam]
        log(f"switch {bw:.4f} (lam {lam:.4f}, {lab}): insurance optimal in {len(rows)} of {len([r for r in cells_w if r['lam'] == lam])} cells: "
            + (', '.join(f"mu={r['mu']:g} H={r['H']:.3f}" for r in rows) if rows else 'none'))
    for bw, lab in ((None, 'beta~'), (BW_DEF, f"{BW_DEF:.4f}")):
        r0 = next(r for r in bis_e if r['bw'] == bw and r['Hs'] == 0)
        q0 = next(r for r in bis_r if r['bw'] == bw and abs(r['lam'] - LAM_DEF) < 1e-12 and r['Hs'] == 0)
        log(f"switch {lab}, lam {LAM_DEF:.4f}, H = 0: insurance binds for mu > mu_c, exact mu_c in ({dn(r0['mu_lo'], 3)}, {up(r0['mu_hi'], 3)}], "
            f"certified for mu >= {up(q0['mu_c'], 3)}")
    log(f"switch {BW_DEF:.4f}, lam {LAM_DEF:.4f}, mu = 2: insurance binds for H <= {H_ins_exact[0]:.4f} beta~ (exact grid; reactive from "
        f"{H_ins_exact[1]:.4f}), certified for H <= {dn(hbis['H_c'], 4)} beta~ = {dn(hbis['H_c'] / LAM_DEF, 3)} lam")
    log(f"total time {time.time() - t0:.0f} s")
    open(os.path.join(HERE, 'out', 'por_default.txt'), 'w').write('\n'.join(L) + '\n')

    # ---- JSON
    def clean(r, keys):
        return {k: (None if (isinstance(r.get(k), float) and not math.isfinite(r[k])) else r.get(k)) for k in keys}
    kb = ['mu', 'lam', 'Hs', 'H', 'CR', 'CR_react', 'CR_ins', 'plan_type', 'plan_s', 'LB_family', 'LB_react_family', 'LB_react_rig', 'closed_form']
    kw = ['mu', 'lam', 'bw', 'Hs', 'H', 'CR', 'plan_type', 'plan_s', 'LB_react_rig']
    J = dict(
        script='code/theory_checks/c2/por_default.py', source=A5B_PATH,
        inputs=dict(alpha=AL, alpha_p=AP, phi=PHI, lambda_default=LAM_DEF, bw_default=BW_DEF, mu_over_beta_tilde=MUS,
                    bw_rows=[dict(lam=l, bw=b, label=s) for l, b, s in BW_ROWS], tau=0.0),
        derived=dict(two_minus_alpha=C, CR_ins=CR_INS, alpha_p_over_alpha=AP / AL, s0=S0, beta_s=BS, dt=DT,
                     grid_step_beta_tilde=DT / BS),
        units='q = 1, beta~ = 1; H, lam, mu, bw, plan_s in beta~; Hs = H in solver units beta_s; PoR = CR/(2-alpha)',
        table_por_switch_beta=[dict(clean(r, kb), PoR_exact=r['CR'] / C, PoR_bound=r['LB_family'] / C,
                                    insurance_optimal=r['plan_type'] == 'p', Hstar_formula=c2sw(r['mu'], r['lam'], 1.0)['H'])
                               for r in cells_b],
        table_por_switch_bw=[dict(clean(r, kw), PoR_exact=r['CR'] / C, insurance_optimal=r['plan_type'] == 'p',
                                  Hstar_formula_C2SW=c2sw(r['mu'], r['lam'], r['bw'])['H']) for r in cells_w],
        crossover_mu_rigorous=[dict(switch='beta' if r['bw'] is None else r['bw'], lam=r['lam'], Hs=r['Hs'], H=r['H'],
                                    mu_c_certified=r['mu_c'], monotone_on_grid=r['mono']) for r in bis_r],
        crossover_mu_exact=[dict(switch='beta' if r['bw'] is None else r['bw'], lam=r['lam'], Hs=r['Hs'], H=r['H'],
                                 H_over_lambda=r['H'] / r['lam'], mu_reactive=r['mu_lo'], mu_insure=r['mu_hi'],
                                 CR_at_mu_reactive=r['CR_lo'], CR_at_mu_insure=r['CR_hi']) for r in bis_e],
        answer=dict(
            switch_beta=dict(n_cells=len(inrange_b), n_insurance_optimal=len(ins_b), max_CR_react_exact=mx['CR_react'],
                             argmax=dict(mu=mx['mu'], lam=mx['lam'], H=mx['H']), CR_ins_minus_max_CR_react=CR_INS - mx['CR_react'],
                             PoR_H0_bound={f"mu={r['mu']:g},lam={r['lam']:.3f}": r['LB_family'] / C for r in cells_b if r['Hs'] == 0},
                             closed_form_gap=dict(n_cells_gt_2e4=ngap, max_family_minus_closed_doc_m=gmax,
                                                  at=dict(mu=gr['mu'], lam=gr['lam'], H=gr['H']),
                                                  max_family_minus_closed_proven_m=gpmax,
                                                  at_proven=dict(mu=gpr['mu'], lam=gpr['lam'], H=gpr['H']),
                                                  max_exact_minus_family=exmax)),
            mu2_default_switch_H_threshold=dict(H_max_insure_exact_grid=H_ins_exact[0], H_first_reactive_exact_grid=H_ins_exact[1],
                                                H_c_rigorous=hbis['H_c'], H_c_rigorous_over_lambda=hbis['H_c'] / LAM_DEF,
                                                monotone_on_grid=hbis['mono'], scan=hscan['rows']),
            switch_bw={f"{bw:.4f}": dict(lam=lam, label=lab, n_cells=len([r for r in cells_w if r['lam'] == lam]),
                                         insurance_optimal_cells=[dict(mu=r['mu'], H=r['H'], Hs=r['Hs']) for r in ins_w if r['lam'] == lam])
                       for lam, bw, lab in BW_ROWS}),
        sanity=dict(lb_interval_bw1_vs_lb_all_max_abs=d1, exact_ins_vs_CR_ins_max_abs=gins,
                    min_exact_react_minus_rig_LB=viol, min_exact_minus_bound_bw=violw),
        seconds=time.time() - t0)
    json.dump(J, open(os.path.join(HERE, 'out', 'por_default.json'), 'w'), indent=1)
