"""Audit (C2, model/solver lens): lease-end semantics and the guaranteed period tau.

(a) Family F2 as written in c2_single_site.md Sec. 5 ('notice at s+; the lease serves D = max(H,tau)')
    vs. as coded in families.F2_parts.  When tau > H the code evaluates OPT with window end R = s + D
    and allows the pre-warm only if H >= lam, i.e. it uses the adversary 'R = s + tau, announced at
    s + tau - H' (a valid and stronger adversary).  The literal text (R = s + H announced at s+) gives
    the algorithm D = tau of lead time, so a pre-warm is feasible when tau >= lam > H, and OPT's window
    is s + H.  We evaluate inf_s max(F1, F2) under both readings.
(b) Per-lease notice semantics.  C2 lets a lease bought after an announcement inherit the announced
    end R (site-window semantics); this creates family F3 and the 'known window' regime H* = R_rho.
    Under per-lease semantics (each lease lives >= H after its purchase, as in the system model's
    reclaim rule r >= s_L + tau_k, end r + H_k, and in Akash AEP-82), a tau = 0 contract is emulated
    exactly (single lease) by C2 with tau := H: E = max(R, s + H).  We compare exact CR (det_game,
    dt = 0.1) under both semantics at the C2 threshold and at the regime-1 value R_rho - s0.
    Caveat: with tau := H a lease bought just before R also extends to R + H for OPT.
(d) Regime-1 (calibrated range) thresholds under the per-lease emulation, dt = 0.05.
(c) Guaranteed period under notice-after-commitment (NAC) semantics (system model, C3: D = tau + H)
    vs C2's max semantics (D = max(H, tau)): NAC(tau, H) is emulated by C2 with tau' = tau + H.  P9
    compares C2(tau=1, H=0) with C2(tau=0, H=1); under NAC the second contract is C2(tau'=1, H=1).
Output: audit/out/model_tau_semantics.txt"""
import os, sys
os.environ['OMP_NUM_THREADS'] = '1'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from multiprocessing import Pool
from model import Params, opt_cost, INF
from families import F1, F2_parts, lb_react
from det_game import solve_det
from alg_check import thresholds
np.seterr(invalid='ignore', over='ignore')

_TT = np.concatenate([np.linspace(1e-6, 12, 1201), np.geomspace(12.5, 1e5, 60)])
_TH = np.concatenate([np.linspace(0, 12, 241), [np.inf]])


def F2_literal(s, P):
    """F2 exactly as written: notice at s+, window end R = s + H, lease ends at E = s + max(H, tau);
    pre-warm feasible iff E - lam >= s; OPT faces window end R = s + H (tau applies to OPT's lease too)."""
    b, a, ap, mu, H, lam, tau = P.beta, P.alpha, P.ap, P.mu, P.H, P.lam, P.tau
    D = max(H, tau); E = s + D; Rt = s + H
    ug = None if tau == 0 else np.linspace(0, Rt, 401)
    oE = float(opt_cost(np.array([E + 1e-9]), Rt, P, ug)[0])
    A0 = s + b + a * D + mu
    cold = A0 / oE
    if P.allow_p:
        O = opt_cost(E + _TT, Rt, P, ug)
        th = _TH[:, None]; t = _TT[None, :]
        tail = np.where(t <= th, t, th + b + ap * (t - th)); tail = np.where(np.isinf(th), t, tail)
        w = ((A0 + tail) / O[None, :]).max(axis=1)
        Ot = opt_cost(E + _TH[:-1] + 1e-9, Rt, P, ug)
        w[:-1] = np.maximum(w[:-1], (A0 + _TH[:-1] + b) / Ot)
        cold = max(cold, float(w.min()))
    warm = INF
    if P.allow_p and E - lam >= s - 1e-12:
        y = E - lam
        oy = float(opt_cost(np.array([y + 1e-9]), Rt, P, ug)[0]) if y > 0 else 1e-12
        w1 = (s + b + a * (y - s) + b) / oy if lam > 0 else 0.0
        w2 = (s + b + a * D + b) / oE
        warm = max(w1, w2)
    return cold, warm


def lb_generic(P, f2, smax=8.0, n=321, nref=161):
    f = lambda s: max(F1(s, P), min(f2(s, P)))
    ss = np.linspace(1e-3, smax, n)
    v = np.array([f(s) for s in ss]); i = int(np.argmin(v))
    ss2 = np.linspace(ss[max(i - 1, 0)], ss[min(i + 1, n - 1)], nref)
    v2 = np.array([f(s) for s in ss2]); j = int(np.argmin(v2))
    return float(v2[j]), float(ss2[j])


def part_a(kw):
    P = Params(**kw)
    lc, sc = lb_generic(P, F2_parts)
    ll, sl = lb_generic(P, F2_literal)
    return kw, lc, sc, ll, sl


def det(job):
    tag, kw, dt = job
    P = Params(**kw)
    Rmax = P.H + 6.0
    r = solve_det(P, dt=dt, T=Rmax + 7.0, Rmax=Rmax, full_plans=False)
    return tag, kw, r['CR'], r['plan']


if __name__ == '__main__':
    lines = []
    log = lambda s: (print(s, flush=True), lines.append(s))
    # (a)
    log("(a) LB_react = inf_s max(F1, F2): code reading (families.F2_parts) vs literal text reading; tau > H")
    A = []
    for (al, ap) in [(0.3, 0.8), (0.0, 0.5), (0.3, 0.6)]:
        for mu in [1.0, 2.0, 4.0]:
            for lam in [0.5, 1.0]:
                for H in [0.0, 0.5]:
                    if lam > H:
                        A.append(dict(alpha=al, ap=ap, mu=mu, lam=lam, H=H, tau=1.0))
    with Pool(4) as p:
        for kw, lc, sc, ll, sl in p.map(part_a, A):
            log(f"   {kw}: code {lc:.4f} (s={sc:.2f})  literal {ll:.4f} (s={sl:.2f})  diff {lc - ll:+.4f}")
    # (b) + (c)
    jobs = []
    for H in [2.0, 2.5, 3.0]:
        kw = dict(alpha=0.0, ap=1.0, mu=4.0, allow_p=False, H=H)
        jobs.append((f"(b) RRL a=0 mu=4: C2 H*=3.0 (Cor. 6), regime-1 value mu/2=2.0 | C2 semantics", dict(kw, tau=0.0), 0.1))
        jobs.append((f"(b) RRL a=0 mu=4: C2 H*=3.0 (Cor. 6), regime-1 value mu/2=2.0 | per-lease (tau:=H)", dict(kw, tau=H), 0.1))
    for H in [5.0, 6.0, 6.5]:
        kw = dict(alpha=1/3, ap=0.8, mu=3.0, lam=0.5, H=H)
        jobs.append((f"(b) menu a=1/3 ap=.8 mu=3 lam=.5: C2 H*=6.5 (Thm 4), regime-1 value 5.0 | C2 semantics", dict(kw, tau=0.0), 0.1))
        jobs.append((f"(b) menu a=1/3 ap=.8 mu=3 lam=.5: C2 H*=6.5 (Thm 4), regime-1 value 5.0 | per-lease (tau:=H)", dict(kw, tau=H), 0.1))
    for (al, ap, mu, lam) in [(0.3, 0.8, 4.0, 0.5), (0.0, 0.5, 4.0, 0.5), (0.3, 0.8, 1.0, 0.5), (0.2, 0.6, 2.0, 0.5)]:
        base = dict(alpha=al, ap=ap, mu=mu, lam=lam)
        jobs.append(("(c) P9 C2(tau=1,H=0) = NAC(tau=1,H=0)", dict(base, tau=1.0, H=0.0), 0.1))
        jobs.append(("(c) P9 C2(tau=0,H=1)", dict(base, tau=0.0, H=1.0), 0.1))
        jobs.append(("(c) P9 NAC(tau=0,H=1) = C2(tau'=1,H=1)", dict(base, tau=1.0, H=1.0), 0.1))
        jobs.append(("(c) NAC(tau=1,H=1) = C2(tau'=2,H=1)", dict(base, tau=2.0, H=1.0), 0.1))
        jobs.append(("(c) C2(tau=1,H=1)", dict(base, tau=1.0, H=1.0), 0.1))
    # (d) calibrated-range (regime 1) thresholds under per-lease semantics (tau := H), dt = 0.05
    for kw, H in [(dict(alpha=1/3, ap=0.8, mu=0.5, lam=0.0), 0.40), (dict(alpha=1/3, ap=0.8, mu=1.5, lam=0.5), 1.15),
                  (dict(alpha=1/3, ap=0.8, mu=2.0, lam=0.5), 1.50), (dict(alpha=0.5, ap=0.8, mu=1.0, lam=0.5), 1.00),
                  (dict(alpha=1/3, ap=1.0, mu=1.0, allow_p=False), 0.75), (dict(alpha=0.5, ap=1.0, mu=2.0, allow_p=False), 2.0)]:
        jobs.append(("(d) regime 1 at Thm-4/Cor-6 H* | C2 semantics", dict(kw, H=H, tau=0.0), 0.05))
        jobs.append(("(d) regime 1 at Thm-4/Cor-6 H* | per-lease (tau:=H)", dict(kw, H=H, tau=H), 0.05))
    with Pool(4) as p:
        res = p.map(det, jobs, chunksize=1)
    log("(b)/(c)/(d) exact deterministic CR (det_game, full_plans=False; dt=0.1 for (b),(c), 0.05 for (d))")
    for tag, kw, cr, plan in res:
        log(f"   {tag}: {kw} -> CR={cr:.4f} plan={plan}")
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'model_tau_semantics.txt'), 'w').write('\n'.join(lines) + '\n')
