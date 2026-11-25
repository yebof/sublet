"""C2 harness: A1's decision logic in C2's own game (design/sim_spec_ms2.md §16; design §5.2.7
check 3, C2 part).

A1's rule (`algos.c2rule`: thresholds, branch, reaction) produces plans (`AlgStarRule.plan`,
`ins_plan`); `c2_plan_cost` prices a plan in C2's game (c2_single_site.md §1 items 1-6, with the
arithmetic of alg_check.alg_cost so that printed values agree bit for bit) and OPT is
`c2/model.py::opt_cost` (`model_switch_cost.opt_cost_bw` with a switch cost bw), both imported through
`paths.import_c2`. `worst` and `worst_star` copy the grids of alg_check.py (lines 42-63 and
134-148); the three instance loops of alg_check.py (first main block and `main_general`) and
alg_check_targeted.py are regenerated with the same generators, call order and format strings
(`regenerate`). alg_check.py and alg_check_targeted.py are not imported: the second writes its output
file on import (§0 rule 5). Helpers for §16.4 items 2-11: the parameter draws of the three loops,
the closed-form column of c2/out/hstar.txt, the formula column of
c2/audit/out/model_switch_cost_default.txt, the breakpoints of switch_cost_crossover.txt (transcribed
from `breakpoints()`, lines 24-35, on top of c2_thresholds), the known failure of the C2-SW rule,
adapters for c2/audit/alg_star_exact.py, and INS and the RRL rule.

It does not check the engine translation (slot rounding, tau_k >= 1 slot, notice after commitment,
resale, prepaid billing) and cannot establish the default switch cost (C2-SW, CONJECTURE).
Nothing here writes into code/theory_checks/.
"""
from __future__ import annotations

import itertools
import json
from multiprocessing import get_context
from typing import Callable, Optional

import numpy as np

from .. import paths
from ..algos.c2rule import AlgStarRule, C2Thresholds, c2_thresholds, ins_plan

INF = np.inf
XS_BASE = np.concatenate([np.linspace(1e-4, 30, 6001), np.geomspace(31, 1e6, 80)])   # alg_check.py:47, 137
REF_FILES = {"alg_check.txt": paths.C2 / "out" / "alg_check.txt",
             "alg_check_general.txt": paths.C2 / "out" / "alg_check_general.txt",
             "alg_check_targeted.txt": paths.C2 / "out" / "alg_check_targeted.txt",
             "hstar.txt": paths.C2 / "out" / "hstar.txt",
             "model_switch_cost_default.txt": paths.C2 / "audit" / "out" / "model_switch_cost_default.txt",
             "switch_cost_crossover.txt": paths.C2 / "audit" / "out" / "switch_cost_crossover.txt",
             "alg_star_exact.txt": paths.C2 / "audit" / "out" / "alg_star_exact.txt"}
REACT_LABEL = {"cold": "cold", "warm": "pre-warm"}     # C2Thresholds.react -> label of the reference files

_C2 = None


def c2():
    """Namespace of the C2 reference modules (model, families, model_switch_cost), imported once."""
    global _C2
    if _C2 is None:
        _C2 = paths.import_c2()
    return _C2


def Params(**kw):
    """c2/model.py::Params."""
    return c2().model.Params(**kw)


# ---------------------------------------------------------------- plan cost and OPT
def c2_plan_cost(plan: tuple, R: float, x, P, bw: Optional[float] = None) -> np.ndarray:
    """Cost of an AlgStarRule plan in C2's game for demand ends x (array) and window end R (§16.2):
    base = fallback until the purchase s, beta at s, rent alpha afterwards; 'none': base;
    'react-cold': mu at R and fallback afterwards; 'react-warm': the switch at the commit d (beta, or
    bw for C2-SW) and protected rent ap after R; 'wait-insure': fallback until v, a fresh protected
    load beta at v, ap afterwards; 'fallback': x (RRL's wait branch)."""
    b, al, ap, mu = P.beta, P.alpha, P.ap, P.mu
    x = np.asarray(x, float)
    kind = plan[0]
    if kind == "fallback":
        return x.copy()
    if kind == "wait-insure":
        v = plan[1]
        return np.where(x <= v, x, v + b + ap * (x - v))
    s = plan[1]
    base = np.where(x <= s, x, s + b + al * (x - s))
    if kind == "none":
        return base
    if kind not in ("react-cold", "react-warm"):
        raise ValueError(f"c2_plan_cost: unknown plan {plan!r}")
    Rp = plan[2]
    if Rp != R:
        raise ValueError(f"c2_plan_cost: plan {plan!r} was made for R = {Rp}, not {R}")
    if kind == "react-cold":
        return np.where(x <= Rp, base, s + b + al * (Rp - s) + mu + (x - Rp))
    d = plan[3]
    sw = b if bw is None else bw
    c = np.where((x > d) & (x <= Rp), base + sw, base)
    return np.where(x <= Rp, c, s + b + al * (Rp - s) + sw + ap * (x - Rp))


def opt_cost(x, R, P, bw: Optional[float] = None) -> np.ndarray:
    """OPT: model.opt_cost (P.allow_p False gives RRL's OPT), or model_switch_cost.opt_cost_bw with
    switch cost bw."""
    m = c2()
    if bw is None:
        return m.model.opt_cost(x, R, P)
    return m.model_switch_cost.opt_cost_bw(x, R, P, bw)


# ---------------------------------------------------------------- worst ratios on the reference grids
def alg_c_rule(P, react: str, Hc: Optional[float] = None) -> tuple[AlgStarRule, float, float]:
    """ALG_c of alg_check.txt (alg_check.py:42-46): AlgStarRule(s0, s0 + Hc, react, lam) with
    s0 = beta/(1 - alpha) and Hc = min(mu, beta)/(2(1 - alpha)) (warm) or mu/(2(1 - alpha)) (cold)."""
    b, al = P.beta, P.alpha
    s = b / (1 - al)
    m = min(P.mu, b) if react == "warm" else P.mu
    Hc = m / (2 * (1 - al)) if Hc is None else Hc
    return AlgStarRule(s, s + Hc, react, P.lam), s, Hc


def worst(P, react: str, Hc: Optional[float] = None, Rmax: float = 12.0, dR: float = 0.01):
    """alg_check.worst (lines 42-63) with the plan of alg_c_rule: (worst ratio, arg) with
    arg = (round(R, 3), x at the maximum) or ('inf', None)."""
    rule, s, Hc = alg_c_rule(P, react, Hc)
    w = 0.0
    arg = None
    with np.errstate(invalid="ignore", over="ignore"):
        for R in np.arange(P.H, Rmax + 1e-9, dR):
            xs = np.unique(np.concatenate([XS_BASE, [R - P.lam + 1e-7, R + 1e-7, R - 1e-7, s + 1e-7, R + s, R + 2 * s]]))
            xs = xs[xs > 0]
            A = c2_plan_cost(rule.plan(R, P.H), R, xs, P)
            O = opt_cost(xs, R, P)
            r = (A / O).max()
            if r > w:
                w, arg = r, (round(R, 3), float(xs[np.argmax(A / O)]))
        A = c2_plan_cost(rule.plan(INF, P.H), INF, XS_BASE, P)
        r = (A / opt_cost(XS_BASE, INF, P)).max()
    if r > w:
        w, arg = r, ("inf", None)
    return w, arg


def worst_star(P, Rmax: float = 14.0, dR: float = 0.02, *, bw: Optional[float] = None,
               th: Optional[C2Thresholds] = None, plan: Optional[Callable[[float, float], tuple]] = None):
    """alg_check.worst_star (lines 134-148): (worst ratio, round(R, 3) at the maximum, thresholds).
    th defaults to c2_thresholds(alpha, ap (None if not P.allow_p: RRL), mu, lam, beta, bw), plan to
    AlgStarRule.from_thresholds(th, lam).plan; with bw, ALG*'s pre-warm pays bw and OPT is
    opt_cost_bw (§16.4 items 7, 8); plan=lambda R, H: ins_plan(th) evaluates INS (item 11)."""
    if th is None:
        th = c2_thresholds(P.alpha, P.ap if P.allow_p else None, P.mu, P.lam, P.beta, bw)
    if plan is None:
        plan = AlgStarRule.from_thresholds(th, P.lam).plan
    s = th.s0
    w = 0.0
    arg = None
    with np.errstate(invalid="ignore", over="ignore"):
        for R in np.arange(P.H, max(Rmax, P.H + 6), dR):
            xs = np.unique(np.concatenate([XS_BASE, [R - P.lam + 1e-7, R + 1e-7, R - 1e-7, s + 1e-7]]))
            xs = xs[xs > 0]
            A = c2_plan_cost(plan(R, P.H), R, xs, P, bw)
            r = (A / opt_cost(xs, R, P, bw)).max()
            if r > w:
                w, arg = r, round(R, 3)
        A = c2_plan_cost(plan(INF, P.H), INF, XS_BASE, P, bw)
        w = max(w, (A / opt_cost(XS_BASE, INF, P, bw)).max())
    return w, arg, th


def worst_ins(P, Rmax: float = 14.0, dR: float = 0.02):
    """C2-T2's INS ('wait-insure' at s0 for every R) against model.opt_cost on worst_star's grid."""
    th = c2_thresholds(P.alpha, P.ap, P.mu, P.lam, P.beta)
    return worst_star(P, Rmax, dR, th=th, plan=lambda R, H: ins_plan(th))


def worst_rrl(P, Rmax: float = 14.0, dR: float = 0.02):
    """The RRL rule (C2-Cor6 thresholds, cold, fallback while waiting) against model.opt_cost with
    allow_p False, on worst_star's grid."""
    return worst_star(P.with_(allow_p=False), Rmax, dR)


# ---------------------------------------------------------------- the three reference loops
NECESSITY = [(dict(mu=1.0, alpha=0.3, ap=0.45), "cold"), (dict(mu=1.0, alpha=0.6, ap=0.9), "cold"),
             (dict(mu=3.0, alpha=0.3, ap=0.7, lam=0.5), "warm"), (dict(mu=3.0, alpha=0.3, ap=0.7, lam=0.0), "cold")]


def alg_check_draws() -> list[dict]:
    """Runs of alg_check.py's first main block (lines 67-95): default_rng(1), 60 draws with
    H in {Hc, Hc + 0.5}, then the four necessity cases. Each run: {'kw' (Params keywords), 'react',
    'Hc', 'nec', 'kw_print' (necessity cases: the dict as printed)}."""
    rng = np.random.default_rng(1)
    runs = []
    for k in range(60):
        al = rng.uniform(0, 0.5)
        ap = rng.uniform(max(1 / (2 - al), al + 0.01), 1.0)
        mu = rng.uniform(0.05, 1.0) if k % 2 == 0 else rng.uniform(1.0, 5.0)
        react = "cold" if mu <= 1 else "warm"
        lam = rng.uniform(0, 3) if react == "cold" else 0.0
        m = min(mu, 1.0)
        Hc = m / (2 * (1 - al))
        for H in [Hc, Hc + 0.5]:
            runs.append({"kw": dict(mu=mu, alpha=al, ap=ap, H=H, lam=lam), "react": react, "Hc": Hc, "nec": False})
    for kw, react in NECESSITY:
        al = kw["alpha"]
        m = min(kw["mu"], 1.0) if react == "warm" else kw["mu"]
        Hc = m / (2 * (1 - al))
        runs.append({"kw": dict(H=Hc, **kw), "react": react, "Hc": Hc, "nec": True, "kw_print": kw})
    return runs


def general_draws() -> tuple[list[dict], list[dict]]:
    """main_general of alg_check.py (lines 151-170): default_rng(7) and its rejection loop. Returns
    (every draw {'alpha', 'ap', 'mu', 'lam', 'accepted'}, the runs {'kw', 'th'})."""
    rng = np.random.default_rng(7)
    draws, runs = [], []
    cnt = 0
    while cnt < 120:
        al = rng.uniform(0.05, 0.5)
        ap = rng.uniform(max(1 / (2 - al), al * (2 - al)) + 1e-3, 1.0)
        mu = rng.choice([rng.uniform(0.05, 1.0), rng.uniform(1.0, 6.0)])
        lam = rng.choice([0.0, rng.uniform(0, 1 / (1 - al))])
        th = c2_thresholds(al, ap, mu, lam, 1.0)
        ok = bool(np.isfinite(th.Hstar)) and not th.Hstar > 9
        draws.append({"alpha": al, "ap": ap, "mu": mu, "lam": lam, "accepted": ok})
        if not ok:
            continue
        for H in [th.Hstar, th.Hstar + 0.3]:
            runs.append({"kw": dict(mu=mu, alpha=al, ap=ap, lam=lam, H=H), "th": th})
            cnt += 1
    return draws, runs


def targeted_draws() -> tuple[list[dict], list[dict], dict]:
    """alg_check_targeted.py (lines 7-26): default_rng(11) and its filter, transcribed as written
    (warm = Hh < Hc, Rx > R_wait without tolerance). Returns (every draw, the runs {'kw', 'th',
    'kind'}, the branch counts)."""
    rng = np.random.default_rng(11)
    draws, runs, kinds = [], [], {}
    cnt = 0
    while cnt < 60:
        al = rng.uniform(0.25, 0.5)
        ap = rng.uniform(max(1 / (2 - al), al * (2 - al)) + 1e-3, 1.0)
        mu = rng.uniform(2.0, 8.0)
        lam = rng.uniform(0.01, 1 / (1 - al))
        th = c2_thresholds(al, ap, mu, lam, 1.0)
        warm = th.Hh < th.Hc
        Rx = th.Rh if warm else th.Rc
        kind = ("warm" if warm else "cold", "Rx>Rwait" if Rx > th.Rw else "Rx<=Rwait")
        ok = not (th.Hstar > 12 or kind == ("cold", "Rx<=Rwait"))
        draws.append({"alpha": al, "ap": ap, "mu": mu, "lam": lam, "accepted": ok})
        if not ok:
            continue
        kinds[kind] = kinds.get(kind, 0) + 1
        for H in [th.Hstar, th.Hstar + 0.3]:
            runs.append({"kw": dict(mu=mu, alpha=al, ap=ap, lam=lam, H=H), "th": th, "kind": kind})
            cnt += 1
    return draws, runs, kinds


def threshold_draws() -> list[dict]:
    """Every parameter draw of the three loops (§16.4 item 2), with its source: 'alg_check' (the 60
    draws and the 4 necessity cases), 'general' and 'targeted' (rejected draws included)."""
    out, seen = [], set()
    for r in alg_check_draws():
        kw = r["kw"]
        key = (kw["alpha"], kw["ap"], kw["mu"], kw.get("lam", 0.0))
        if key not in seen:
            seen.add(key)
            out.append({"source": "alg_check", "alpha": key[0], "ap": key[1], "mu": key[2], "lam": key[3]})
    out += [dict(source="general", **{k: d[k] for k in ("alpha", "ap", "mu", "lam")}) for d in general_draws()[0]]
    out += [dict(source="targeted", **{k: d[k] for k in ("alpha", "ap", "mu", "lam")}) for d in targeted_draws()[0]]
    return out


def _job_worst(run: dict):
    return worst(Params(**run["kw"]), run["react"], Rmax=10.0, dR=0.02)


def _job_star(args):
    kw, Rmax = args
    P = Params(**kw)
    if Rmax is None:
        return worst_star(P)[:2]
    return worst_star(P, Rmax=Rmax, dR=0.02)[:2]


def _map(fn, jobs: list, workers: int) -> list:
    if workers <= 1 or len(jobs) <= 1:
        return [fn(j) for j in jobs]
    with get_context("fork").Pool(int(workers)) as pool:
        return pool.map(fn, jobs, chunksize=1)


def alg_check_lines(workers: int = 1, n_runs: Optional[int] = None) -> list[str]:
    """The lines of c2/out/alg_check.txt (128 lines). n_runs limits the main block to its first runs
    and omits the summary and the necessity block (quick variant)."""
    runs = alg_check_draws()
    main = [r for r in runs if not r["nec"]]
    nec = [r for r in runs if r["nec"]]
    if n_runs is not None:
        main, nec = main[:n_runs], []
    res = _map(_job_worst, main + nec, workers)
    lines = ["Theorem 5 check: worst ratio of ALG_c at H = Hc and H = Hc + 0.5 (target 2 - alpha)",
             "conditions: tau=0, alpha<=1/2, (2-alpha)*ap>=1; cold if mu<=beta, warm with lam=0 if mu>beta"]
    cnt = 0
    maxexcess = -1
    for r, (w, arg) in zip(main, res):
        kw, react = r["kw"], r["react"]
        al, ap, mu, lam, H = kw["alpha"], kw["ap"], kw["mu"], kw["lam"], kw["H"]
        maxexcess = max(maxexcess, w - (2 - al))
        cnt += 1
        lines.append(f"alpha={al:.3f} ap={ap:.3f} mu={mu:.3f} lam={lam:.2f} H={H:.3f} react={react}: worst={w:.5f} "
                     f"2-alpha={2-al:.5f} excess={w-(2-al):+.2e} at {arg}")
    if n_runs is not None:
        return lines
    lines.append(f"SUMMARY: {cnt} instances, max excess over 2-alpha = {maxexcess:+.3e}")
    lines.append("Necessity of the side conditions (expected excess > 0):")
    for r, (w, arg) in zip(nec, res[len(main):]):
        kw, react, Hc = r["kw_print"], r["react"], r["Hc"]
        al = kw["alpha"]
        lines.append(f"{kw} react={react} H=Hc={Hc:.3f}: worst={w:.4f} 2-alpha={2-al:.4f} at {arg}")
    return lines


def alg_check_general_lines(workers: int = 1) -> list[str]:
    """The lines of c2/out/alg_check_general.txt (123 lines)."""
    _, runs = general_draws()
    res = _map(_job_star, [(r["kw"], None) for r in runs], workers)
    lines = ["Theorem 6 check: ALG* at H = H* and H* + 0.3 (target 2 - alpha); random parameters with",
             "tau=0, 0<alpha<=1/2, (2-alpha)ap>=1, ap>alpha(2-alpha), lam<=s0, H*<=9"]
    cnt = 0
    mx = -1
    for r, (w, arg) in zip(runs, res):
        kw, th = r["kw"], r["th"]
        al, ap, mu, lam, H = kw["alpha"], kw["ap"], kw["mu"], kw["lam"], kw["H"]
        mx = max(mx, w - (2 - al))
        cnt += 1
        lines.append(f"alpha={al:.3f} ap={ap:.3f} mu={mu:.3f} lam={lam:.3f} H*={th.Hstar:.3f} "
                     f"(Hc={th.Hc:.3f}, Hw={th.Hh:.3f}) H={H:.3f}: worst={w:.5f} excess={w-(2-al):+.2e} at R={arg}")
    lines.append(f"SUMMARY: {cnt} instances, max excess over 2-alpha = {mx:+.3e}")
    return lines


def alg_check_targeted_lines(workers: int = 1) -> list[str]:
    """The lines of c2/out/alg_check_targeted.txt (63 lines)."""
    _, runs, kinds = targeted_draws()
    res = _map(_job_star, [(r["kw"], r["kw"]["H"] + 8) for r in runs], workers)
    lines = ["ALG* at H = H* and H* + 0.3; instances where warm (lam>0) or R_rho > R_wait"]
    cnt = 0
    mx = -1
    for r, (w, arg) in zip(runs, res):
        kw, th, kind = r["kw"], r["th"], r["kind"]
        al, ap, mu, lam, H = kw["alpha"], kw["ap"], kw["mu"], kw["lam"], kw["H"]
        mx = max(mx, w - (2 - al))
        cnt += 1
        lines.append(f"{kind} alpha={al:.3f} ap={ap:.3f} mu={mu:.3f} lam={lam:.3f} H*={th.Hstar:.3f} H={H:.3f}: "
                     f"worst={w:.5f} excess={w-(2-al):+.2e} at R={arg}")
    lines.append(f"branch counts (instances): {kinds}")
    lines.append(f"SUMMARY: {cnt} runs, max excess over 2-alpha = {mx:+.3e}")
    return lines


GENERATORS = {"alg_check.txt": alg_check_lines, "alg_check_general.txt": alg_check_general_lines,
              "alg_check_targeted.txt": alg_check_targeted_lines}


def regenerate(name: str, workers: int = 1) -> list[str]:
    """The regenerated lines of one of the three reference files (keys of GENERATORS)."""
    return GENERATORS[name](workers=workers)


def reference_lines(name: str) -> list[str]:
    """The stored lines of a reference file (REF_FILES), without the final newline."""
    return REF_FILES[name].read_text().rstrip("\n").split("\n")


def compare_lines(name: str, lines: list[str]) -> list[tuple[int, str, str]]:
    """(line number, stored, regenerated) for every line that differs, including a length mismatch."""
    ref = reference_lines(name)
    out = [(i, a, b) for i, (a, b) in enumerate(zip(ref, lines)) if a != b]
    for i in range(min(len(ref), len(lines)), max(len(ref), len(lines))):
        out.append((i, ref[i] if i < len(ref) else "", lines[i] if i < len(lines) else ""))
    return out


# ---------------------------------------------------------------- items 3-6: closed forms
def hstar_closed_rows() -> list[tuple[str, str]]:
    """c2/out/hstar.txt (hstar.py:73-83): per case (al, ap, mu, lam) of the 30, the printed prefix
    'alpha ap mu lam' and the closed-form column 'H* (H(R_cold), max(lam, H(R_warm)))' from c2_thresholds."""
    out = []
    for al, ap, mu, lam in itertools.product([1 / 3, 0.5], [0.8], [0.5, 1.0, 1.5, 2.0, 3.0], [0.0, 0.5, 1.0]):
        th = c2_thresholds(al, ap, mu, lam, 1.0)
        out.append((f"{al:.3f} {ap} {mu} {lam}", f"{th.Hstar:.3f} ({th.Hc:.3f}, {th.Hh:.3f})"))
    return out


def a5b_inputs() -> dict:
    """alpha, alpha_p, phi and the default switch cost bw of a5b_exposure_thresholds.json, the inputs of
    model_switch_cost_default.py (lines 45-48) and switch_cost_crossover.py."""
    a5b = json.loads((paths.ANALYSIS_OUT / "a5b_exposure_thresholds.json").read_text())
    i = a5b["inputs"]
    al, phi = float(i["alpha"]), float(i["phi"])
    return {"alpha": al, "alpha_p": float(i["alpha_p"]), "phi": phi,
            "bw_default": float(a5b["prewarm_switch_cost_over_beta_tilde"]), "lam_default": 1 / (al + phi)}


def default_hstar_entry(alpha_k: float, mu: float, switch: str, alpha_p: Optional[float] = None,
                        phi: Optional[float] = None) -> dict:
    """H*_mu / lambda at price ratio alpha_k with the convention of a5b_exposure_thresholds.hstar_mu_coefs
    (beta_jl = 0): lam = 1/(alpha_k + phi), bw = alpha_p/(alpha_k + phi) for switch 'c2sw', the C2-T4
    form for 'beta'. {'value' (H*/lam), 'reaction' ('cold' or 'pre-warm'), 'regime', 'th'}."""
    d = a5b_inputs()
    ap = d["alpha_p"] if alpha_p is None else alpha_p
    ph = d["phi"] if phi is None else phi
    lam = 1 / (alpha_k + ph)
    th = c2_thresholds(alpha_k, ap, mu, lam, 1.0, None if switch == "beta" else ap / (alpha_k + ph))
    return {"value": th.Hstar / lam, "reaction": REACT_LABEL[th.react], "regime": th.regime, "th": th}


def switch_cost_default_jobs() -> list[tuple]:
    """model_switch_cost_default.jobs() (lines 113-126): (mu, lam, bw, label, grid label) of the 58 lines."""
    d = a5b_inputs()
    AL, AP, BW_DEF, LAM_DEF = d["alpha"], d["alpha_p"], d["bw_default"], d["lam_default"]
    J = []
    for mu in [0.2, 0.5, 1.0, 2.0]:
        for bw, lab in [(1.0, "switch beta~ (Thm 4)"), (0.8, ""), (0.6, ""), (BW_DEF, "default switch"), (0.2, "")]:
            J.append((mu, LAM_DEF, bw, lab))
    for lam in [0.25, 0.5]:
        for mu in [0.5, 1.0, 2.0]:
            for bw in [1.0, 0.8, 0.6, 0.2]:
                J.append((mu, lam, bw, "switch beta~ (Thm 4)" if bw == 1.0 else ""))
            J.append((mu, lam, 1 - lam * (1 + AL - AP), "consistent with fees"))
    for mu in [0.2, 0.5, 1.0, 2.0]:
        for bw, lab in [(1.0, "switch beta~ (Thm 4), s0 = 1.70 grid"), (BW_DEF, "default switch, s0 = 1.70 grid")]:
            J.append((mu, LAM_DEF, bw, lab))
    return J


def switch_cost_default_formula_lines() -> list[str]:
    """The formula part of the 58 lines of c2/audit/out/model_switch_cost_default.txt, i.e. each line
    up to ' | exact': 'mu=.. lam=.. bw=.. [label]| formula H = h lam, reaction, regime', from the
    C2-SW form of c2_thresholds (bw given, also bw = 1) at a5b's alpha and alpha_p."""
    d = a5b_inputs()
    out = []
    for mu, lam, bw, label in switch_cost_default_jobs():
        th = c2_thresholds(d["alpha"], d["alpha_p"], mu, lam, 1.0, bw)
        out.append(f"mu={mu:.2f} lam={lam:.4f} bw={bw:.4f} {('[' + label + ']') if label else ''}| "
                   f"formula {th.Hstar:.4f} = {th.Hstar / lam:.3f} lam, {REACT_LABEL[th.react]}, {th.regime}")
    return out


def stored_switch_cost_default_formula() -> list[str]:
    """The stored formula parts (lines starting with 'mu=' cut before ' | exact')."""
    return [ln.split(" | exact")[0] for ln in reference_lines("model_switch_cost_default.txt") if ln.startswith("mu=")]


CROSSOVER_STEP, CROSSOVER_MU_MAX = 0.001, 4.0


def breakpoints(lam: float, bw: float, a: Optional[float] = None, ap: Optional[float] = None) -> list[tuple]:
    """switch_cost_crossover.breakpoints (lines 24-35) on top of c2_thresholds: (mu, label, H*) at
    every mu = i * 0.001 (i = 1..4000) where the label (simple form or above it, reaction, regime)
    changes."""
    d = a5b_inputs()
    a = d["alpha"] if a is None else a
    ap = d["alpha_p"] if ap is None else ap
    out, prev = [], None
    for i in range(1, int(round(CROSSOVER_MU_MAX / CROSSOVER_STEP)) + 1):
        mu = i * CROSSOVER_STEP
        th = c2_thresholds(a, ap, mu, lam, 1.0, bw)
        simple = abs(th.Hstar - mu / (2 * (1 - a))) < 1e-9
        key = ("simple form" if simple else "above simple form", REACT_LABEL[th.react], th.regime)
        if key != prev:
            out.append((mu, key, th.Hstar))
            prev = key
    return out


def crossover_lines() -> list[str]:
    """The six breakpoint blocks of switch_cost_crossover.txt (lines 49-58 of the script), without the
    blank lines that separate them."""
    d = a5b_inputs()
    cases = [(d["lam_default"], d["bw_default"], "default calibration"),
             (0.5, d["bw_default"], "default switch, lambda = 0.5"),
             (0.25, d["bw_default"], "default switch, lambda = 0.25"),
             (1e-9, d["bw_default"], "default switch, lambda -> 0"),
             (0.5, 0.7182, "fee-consistent pair"),
             (0.25, 0.8591, "fee-consistent pair")]
    out = []
    for lam, bw, lab in cases:
        out.append(f"lambda={lam:.4f} bw={bw:.4f} ({lab}); 2 bw = {2 * bw:.4f}")
        for mu, key, H in breakpoints(lam, bw):
            out.append(f"  mu >= {mu:.3f}: {key[0]}, {key[1]}, {key[2]} (H* = {H:.4f})")
    return out


def stored_crossover_lines() -> list[str]:
    """The block headers and breakpoint rows of the six blocks of the stored switch_cost_crossover.txt."""
    out = []
    for ln in reference_lines("switch_cost_crossover.txt"):
        if ln.startswith("lambda dependence"):
            break
        if ln.startswith("lambda=") or ln.startswith("  mu >= "):
            out.append(ln)
    return out


# ---------------------------------------------------------------- item 7: known failure of C2-SW
def c2sw_failure_point(alpha: float = 1 / 3, ap: float = 0.8, mu: float = 2.0, lam: float = 0.25,
                       bw: float = 0.2, H: float = 1.15, R: float = 2.45) -> dict:
    """§16.4 item 7 (recheck_c2.py lines 226-229, recheck_c2.txt line 64): the C2-SW thresholds, the
    plan of ALG* for the window ending at R announced at R - H, and its ratio at x = R + 1e-7 against
    opt_cost_bw, ALG* paying bw for a pre-warm."""
    P = Params(mu=mu, alpha=alpha, ap=ap, H=H, lam=lam)
    th = c2_thresholds(alpha, ap, mu, lam, 1.0, bw)
    plan = AlgStarRule.from_thresholds(th, lam).plan(R, H)
    x = np.array([R + 1e-7])
    ratio = float(c2_plan_cost(plan, R, x, P, bw=bw)[0] / opt_cost(x, R, P, bw)[0])
    return {"th": th, "plan": plan, "ratio": ratio, "two_minus_alpha": 2 - alpha}


# ---------------------------------------------------------------- item 10: adapters for alg_star_exact.py
def exact_thresholds(a, ap, mu, lam, b=1.0, rrl=False) -> dict:
    """Adapter for c2/audit/alg_star_exact.py's global `thresholds`: the dict it uses (s0, Rw, Rc, Rh,
    Hc, Hh, Hs, rho, Rrho) from c2_thresholds (ap None in RRL mode)."""
    th = c2_thresholds(a, None if rrl else ap, mu, lam, b)
    return dict(s0=th.s0, Rw=th.Rw, Rc=th.Rc, Rh=th.Rh, Hc=th.Hc, Hh=th.Hh, Hs=th.Hstar, rho=th.react, Rrho=th.Rrho)


_EXACT_KIND = {"none": "inf", "react-cold": "hold-cold", "react-warm": "hold-warm", "wait-insure": "wait",
               "fallback": "wait"}


def exact_alg_star(x, R, H, P: dict, th: dict):
    """Adapter for alg_star_exact.py's global `alg_star(x, R, H, P, th)`: (cost of AlgStarRule's plan
    priced by c2_plan_cost, kind label), with P the module's dict (b, a, ap, mu, lam, rrl)."""
    rrl = bool(P["rrl"])
    rule = AlgStarRule(th["s0"], th["Rrho"], th["rho"], P["lam"], rrl)
    plan = rule.plan(R, H)
    PP = Params(beta=P["b"], alpha=P["a"], ap=P["ap"], mu=P["mu"], lam=P["lam"], H=H, allow_p=not rrl)
    return c2_plan_cost(plan, R, x, PP), _EXACT_KIND[plan[0]]


__all__ = ["c2_plan_cost", "opt_cost", "alg_c_rule", "worst", "worst_star", "worst_ins", "worst_rrl",
           "alg_check_draws", "general_draws", "targeted_draws", "threshold_draws", "alg_check_lines",
           "alg_check_general_lines", "alg_check_targeted_lines", "regenerate", "reference_lines", "compare_lines",
           "hstar_closed_rows", "a5b_inputs", "default_hstar_entry", "switch_cost_default_jobs",
           "switch_cost_default_formula_lines", "stored_switch_cost_default_formula", "breakpoints",
           "crossover_lines", "stored_crossover_lines", "c2sw_failure_point", "exact_thresholds", "exact_alg_star",
           "REF_FILES", "XS_BASE", "Params"]
