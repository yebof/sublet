"""R2-R5: regenerate c3/out/c4_lower.txt (a)-(d) and c4_lower.json (design/sim_spec_ms2.md §17.3;
checks 3i-3k of §1.3).

(a) R2, cat-and-mouse: `check_c4_lower.cm_instance(m, rho)` (m in {2, 3, 4, 6}, rho in {2, 4, 8, 16})
    through the engine under the `adaptive` lender: RR_RENEW with stay=True ('stay') and RR_RENEW
    ('round-robin'), and A3 in reference mode (x3=False, x2='reference', reaction='cold') with
    rbar = 1 and the theory rbar, policy generators default_rng(s), s = 0..3; each cost over
    fam.opt_dp(Fam(m, rho, 2, 1, 48), realized R). A3's cost is the engine lease cost plus
    pd.service_cost_given_open of its opened map (the reference's real_cost_renew + service).
(b) R3: check_c4_lower.single(48, [(1,1),(48,0)], beta, [1.0, 1.3]), beta in {2, 6, 14, 30}, schedule
    `eager`: BL7 (inner A2, rbar = 1) engine total / core.opt_eager(I) ('revonly/OPT', per policy
    seed 0..9); A2 (rbar = 1, default_rng(s), s = 0..9): mean cost_pr / OPT and P / OPT. The random
    line offline: solve_eager on from_core of the contract subsets [0, 1] and [0] over the full menu.
(c) R4: single(48, [(2, H)], 20.0, [1.0]), H in {0, 1, 2, 4, 8}, `eager`: BL6 (inner A2, rbar = 1,
    policy seeds 0..3) engine total / core.opt_eager. The random line offline: solve_eager of the
    transform H' = 0, a' = a D / tau over solve_eager of the instance.
(d) R5: the instances of part_d_constructed (b in {1, 2, 4, 8, 16}): run_siloed(A2, rbar = 1) total /
    shared core.opt_eager, and the shared A2 / OPT (= 1). The random lines offline: sum of per-owner
    solve_eager over the shared solve_eager.
(e) is copied from c4_lower.json (MS1 checks the parking-permit DP).

The offline MILPs run at mip_rel_gap 1e-9 (the reference ran at HiGHS's default 1e-4; §17.2
test_c4_lower_random_offline); their status and gap are recorded. Writes
code/sim/out/ms2_checks/c4_lower_repro.json and c4_lower_repro.txt (the reference's format strings).

Run from code/sim under the 3 GB cap (run_ms2_checks.sh):
  python -m sublet.experiments.repro_c4_lower [--out DIR] [--workers 4] [--parts abcd] [--quick]
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import copy
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

from ..paths import C3, import_ref
from .repro_common import checks_dir, empty_omega, lease_cost, make, opened_map, pool_map, run

OUT = checks_dir()
REF_JSON = C3 / "out" / "c4_lower.json"
MILP_KW = dict(mip_rel_gap=1e-9, time_limit_s=600.0)
A3_REF = {"x3": False, "x2": "reference", "reaction": "cold", "record": True}


def _from_core(I, omega=None):
    from ..instance import from_core
    return from_core(I, empty_omega(I.m) if omega is None else omega)


def _n_bound(I) -> int:
    return max(I.n * I.T, 3)


# ---------------------------------------------------------------- (a) cat-and-mouse
def part_a_row(args) -> dict:
    m, rho = args
    c4 = import_ref("check_c4_lower")
    fam = import_ref("fam")
    pd = import_ref("pd")
    I = c4.cm_instance(m, rho)
    T, L, tau = I.T, int(I.L[0]), int(I.tau[0])
    beta, a = float(I.beta[0, 0]), float(I.a[0, 0])
    nA = math.ceil(T / L)
    LB_T = (nA * beta + a * T) / ((nA / m + 1) * beta + a * (T + L))
    asym = rho * m / (m + rho - 1)
    F = fam.Fam(m, rho, tau, int(I.H[0]), T)
    inst, _ = _from_core(I)
    res = dict(m=m, rho=rho, LB_T=LB_T, asym=asym)
    for name, params in (("stay", {"stay": True}), ("rr", {})):
        r = run(inst, make("RR_RENEW", params, inst), schedule="adaptive")
        opt = fam.opt_dp(F, [np.asarray(x, dtype=np.int64) for x in r.schedule.R])[0]
        res[name] = r.components["total"] / opt
        res[name + "_purchases"] = len(r.leases)
    for tag, rbar in (("pd_r1", 1), ("pd_rth", "theory")):
        ratios, R_ok = [], True
        for s in range(4):
            pol = make("A3", dict(A3_REF, rbar=rbar), inst, inputs={"N_bound": _n_bound(I)} if rbar == "theory" else None)
            r = run(inst, pol, schedule="adaptive", rng=np.random.default_rng(s))
            om = [np.asarray(x, dtype=np.int64) for x in r.schedule.R]
            opened = opened_map(pol)
            serv = float(pd.service_cost_given_open(I, opened).sum())
            ratios.append((lease_cost(r) + serv) / fam.opt_dp(F, om)[0])
            _, om_ref = pd.real_cost_renew(I, opened, None, adversary=True)
            R_ok &= all(np.array_equal(np.asarray(x), np.asarray(y)) for x, y in zip(om, om_ref))
        res[tag] = float(np.mean(ratios))
        res[tag + "_min"] = float(np.min(ratios))
        res[tag + "_per_seed"] = ratios
        res[tag + "_R_equals_real_cost_renew"] = bool(R_ok)
    return res


# ---------------------------------------------------------------- (b) revocable-only
def part_b_row(beta) -> dict:
    c4 = import_ref("check_c4_lower")
    core = import_ref("core")
    T = 48
    I = c4.single(T, [(1, 1), (T, 0)], beta, [1.0, 1.3])
    full = core.opt_eager(I)["fun"]
    rho1 = 1 + beta / 2.0
    inst, _ = _from_core(I)
    revonly = []
    for s in range(10):
        pol = make("BL7", {"inner": "A2", "inner_params": {"rbar": 1}}, inst)
        revonly.append(run(inst, pol, schedule="eager", rng=np.random.default_rng(s)).components["total"] / full)
    pr, P = [], None
    for s in range(10):
        pol = make("A2", {"rbar": 1}, inst)
        run(inst, pol, schedule="eager", rng=np.random.default_rng(s))
        rep = pol.report()
        pr.append(rep["cost_pr"])
        P = rep["P"]
    return dict(beta=beta, rho1=rho1, ratio=float(np.mean(revonly)), ratio_per_seed=revonly,
                formula_asym=1.0 * rho1 / 1.3, formula_T=(T / 2) * (beta + 2) / (beta + 1.3 * T),
                pd_r1_ratio=float(np.mean(pr)) / full, frac_ratio=P / full, OPT_eager=full)


def _eager(I) -> dict:
    from ..opt.milp import solve_eager
    inst, _ = _from_core(I)
    r = solve_eager(inst, **MILP_KW)
    return {"objective": r.objective, "status": r.status, "gap": r.gap}


def b_random(seed) -> dict:
    core = import_ref("core")
    I = core.random_instance(np.random.default_rng(9000 + seed), T=36, m=4, J=2, n=8)
    full, rev, spot = _eager(I), _eager(I.subset(contracts=[0, 1])), _eager(I.subset(contracts=[0]))
    return dict(seed=seed, rev_over_full=rev["objective"] / full["objective"],
                spot_over_full=spot["objective"] / full["objective"], milp=dict(full=full, rev=rev, spot=spot))


# ---------------------------------------------------------------- (c) notice-oblivious
def part_c_row(H) -> dict:
    c4 = import_ref("check_c4_lower")
    core = import_ref("core")
    I = c4.single(48, [(2, H)], 20.0, [1.0])
    opt = core.opt_eager(I)["fun"]
    inst, _ = _from_core(I)
    ratios = []
    for s in range(4):
        pol = make("BL6", {"inner": "A2", "inner_params": {"rbar": 1}}, inst)
        ratios.append(run(inst, pol, schedule="eager", rng=np.random.default_rng(s)).components["total"] / opt)
    return dict(H=H, tau=2, ratio=float(np.mean(ratios)), ratio_per_seed=ratios, L_over_tau=(2 + H) / 2, OPT_eager=opt)


def notice_oblivious_transform(I):
    """The class value of C3-P6 as an eager instance: every contract (tau, H) becomes (tau, 0) with price
    a D / tau, so that a column of window tau costs beta + g a D (check_c4_lower.notice_oblivious_opt)."""
    J = copy.deepcopy(I)
    tau, H = np.asarray(I.tau), np.asarray(I.H)
    J.a = np.asarray(I.a, dtype=float) * ((tau + H) / tau)[None, :]
    J.H = np.zeros_like(H)
    return J


def c_random(seed) -> dict:
    core = import_ref("core")
    I = core.random_instance(np.random.default_rng(9100 + seed), T=36, m=4, J=2, n=8,
                             contracts=[(1, 2, 1.0), (4, 4, 1.25), (12, 6, 1.6)])
    full, no = _eager(I), _eager(notice_oblivious_transform(I))
    return dict(seed=seed, ratio=no["objective"] / full["objective"], milp=dict(full=full, notice_oblivious=no))


# ---------------------------------------------------------------- (d) siloed planning
def part_d_row(b) -> dict:
    from ..drivers.siloed import run_siloed
    from ..engine import EngineConfig
    from ..types import LenderModel
    core = import_ref("core")
    T = 24
    I = core.Instance(T=T, tau=np.array([T]), H=np.array([0]), a=np.array([[1.0]]), beta=np.array([[10.0]]),
                      g=np.array([1]), q=1e3, cl_llm=np.zeros(b, dtype=int), delta=np.zeros((b, 1)),
                      active=np.ones((b, T), dtype=bool), owner=np.arange(b))
    shared = core.opt_eager(I)["fun"]
    inst, _ = _from_core(I)
    d = run_siloed(inst, lambda sub: make("A2", {"rbar": 1}, sub), LenderModel(schedule="eager"),
                   EngineConfig(), lender_seed=0, policy_seed=0)
    assert not d["invariant_failures"], d["invariant_failures"][:5]
    sh = run(inst, make("A2", {"rbar": 1}, inst), schedule="eager", policy_seed=0)
    return dict(b=b, ratio=d["components"]["total"] / shared, shared_ratio=sh.components["total"] / shared,
                OPT_eager=shared, n_borrowers=len(d["borrowers"]))


def d_random(args) -> dict:
    seed, b = args
    core = import_ref("core")
    I = core.random_instance(np.random.default_rng(9200 + seed), T=36, m=4, J=1, n=16, n_borrowers=b)
    shared = _eager(I)
    silo, parts = 0.0, []
    for o in range(b):
        cl = np.nonzero(I.owner == o)[0]
        if len(cl):
            r = _eager(I.subset(clients=cl))
            silo += r["objective"]
            parts.append(r)
    return dict(seed=seed, b=b, ratio=silo / shared["objective"], milp=dict(shared=shared, owners=parts))


# ---------------------------------------------------------------- text
def text(A, B, Br, C, Cr, D, Dr, E) -> str:
    """c4_lower.txt with check_c4_lower.py's format strings (lines 187-212)."""
    L = ['(a) cat-and-mouse (adaptive per-site lender), T=48, tau=2, H=1, a=1',
         '  m  rho   LB_T   rho*m/(m+rho-1)   stay   round-robin   PD(r=1) mean/min   PD(r=th) mean/min   all>=LB_T']
    for r in A:
        ok = min(r['stay'], r['rr'], r['pd_r1_min'], r['pd_rth_min']) >= r['LB_T'] - 1e-9
        L.append(f"  {r['m']}  {r['rho']:4.0f}  {r['LB_T']:.3f}   {r['asym']:.3f}           {r['stay']:.3f}  "
                 f"{r['rr']:.3f}         {r['pd_r1']:.3f}/{r['pd_r1_min']:.3f}      {r['pd_rth']:.3f}/{r['pd_rth_min']:.3f}       {ok}")
    L.append('(b) revocable-only vs full menu, announce every slot; revocable (1,1,a=1), protected (48,0,a=1.3)')
    L.append('  beta  rho1  revonly/OPT  finite-T formula  a1*rho1/a2  PD(r=1)/OPT  frac/OPT')
    for r in B:
        L.append(f"  {r['beta']:4.0f}  {r['rho1']:4.1f}  {r['ratio']:.3f}        {r['formula_T']:.3f}            "
                 f"{r['formula_asym']:.3f}       {r['pd_r1_ratio']:.3f}        {r['frac_ratio']:.3f}")
    if Br:
        rv = np.array([x['rev_over_full'] for x in Br]); sv = np.array([x['spot_over_full'] for x in Br])
        L.append(f"  random (T=36,m=4,J=2): without long contract OPT ratio mean {rv.mean():.3f} max {rv.max():.3f}; "
                 f"spot-only mean {sv.mean():.3f} max {sv.max():.3f}")
    L.append('(c) notice-oblivious (uses lease only for tau) vs OPT_eager; single site, tau=2, beta=20, a=1, T=48')
    for r in C:
        L.append(f"  H={r['H']}  ratio {r['ratio']:.3f}  L/tau {r['L_over_tau']:.2f}")
    if Cr:
        cr = np.array([x['ratio'] for x in Cr])
        L.append(f"  random (contracts (1,2),(4,4),(12,6)): mean {cr.mean():.3f} max {cr.max():.3f}")
    L.append('(d) siloed per-borrower OPT / shared OPT')
    L.append('  constructed: ' + ', '.join(f"b={r['b']}: {r['ratio']:.3f}" for r in D))
    for b in [2, 4, 8]:
        v = np.array([x['ratio'] for x in Dr if x['b'] == b])
        if len(v):
            L.append(f"  random n=16 clients, b={b} borrowers: mean {v.mean():.3f} min {v.min():.3f} max {v.max():.3f}")
    if E:
        err = max(abs(r['milp'] - r['dp']) for r in E)
        L.append(f"(e) parking-permit embedding: max |OPT_eager(MILP) - PP DP| over 20 instances = {err:.2e}")
    return '\n'.join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT, help="output folder (default code/sim/out/ms2_checks or SUBLET_MS2_CHECKS_DIR)")
    ap.add_argument("--workers", type=int, default=4, help="worker processes (at most 4)")
    ap.add_argument("--parts", default="abcd", help="parts to run (subset of 'abcd'; default all)")
    ap.add_argument("--no-random", action="store_true", help="skip the offline random lines (MILPs)")
    ap.add_argument("--quick", action="store_true", help="one row per part, no random lines (a smoke check)")
    a = ap.parse_args(argv)
    ref = json.loads(REF_JSON.read_text())
    t0 = time.perf_counter()
    rnd = not (a.no_random or a.quick)
    A = pool_map(part_a_row, [(m, rho) for m in [2, 3, 4, 6] for rho in [2, 4, 8, 16]][: 1 if a.quick else None],
                 a.workers) if "a" in a.parts else []
    B = pool_map(part_b_row, [2, 6, 14, 30][: 1 if a.quick else None], a.workers) if "b" in a.parts else []
    Br = pool_map(b_random, range(10), a.workers) if ("b" in a.parts and rnd) else []
    C = pool_map(part_c_row, [0, 1, 2, 4, 8][: 2 if a.quick else None], a.workers) if "c" in a.parts else []
    Cr = pool_map(c_random, range(10), a.workers) if ("c" in a.parts and rnd) else []
    D = pool_map(part_d_row, [1, 2, 4, 8, 16][: 2 if a.quick else None], a.workers) if "d" in a.parts else []
    Dr = pool_map(d_random, [(s, b) for b in [2, 4, 8] for s in range(6)], a.workers) if ("d" in a.parts and rnd) else []
    E = ref["e"]
    out = dict(a=A, b=B, b_random=Br, c=C, c_random=Cr, d=D, d_random=Dr, e=E,
               meta={"script": "code/sim/sublet/experiments/repro_c4_lower.py",
                     "spec": "design/sim_spec_ms2.md §17.3 R2-R5; checks 3i-3k",
                     "parts": a.parts, "random_lines": rnd, "quick": bool(a.quick), "milp": MILP_KW,
                     "e": "copied from code/theory_checks/c3/out/c4_lower.json",
                     "seconds": time.perf_counter() - t0})
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "c4_lower_repro.json").write_text(json.dumps(out, indent=1) + "\n")
    txt = text(A, B, Br, C, Cr, D, Dr, E)
    (a.out / "c4_lower_repro.txt").write_text(txt + "\n")
    print(txt, flush=True)
    print(f"[repro_c4_lower] done in {time.perf_counter() - t0:.1f} s; wrote {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
