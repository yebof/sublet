"""R1: regenerate c3/out/c3_upper.txt and .json with the vectorized PD and the inline rounding
(design/sim_spec_ms2.md §17.3, R1; check 2e of §1.3 for rounding seeds 0-39).

For the 60 instances of `check_c3_upper.make` (families rand, slo, setcover, spiky, big; seeds
0-11) the script runs `VecPD(problem_from_core(I))` in core mode (requests by slot, then core
client, §5.1) for the fractional values P, sum Y, the dual-feasibility ratio, d and the cap hits,
and, per rounding seed s = 0..39, a fresh VecPD with an inline `Rounder(pd, default_rng(s), rbar)`
for rbar = ceil(2 ln N), N = max(n T, 3), and rbar = 1 (the reference's `round_pd(pd,
default_rng(s), r)`): ALG_an and ALG_pr are the means of the analysed and practical costs at the
theory rbar, ALG_r1 the mean practical cost at rbar = 1. The values that come from the reference
MILP and LPs (LP_trunc, LP_aligned, OPT_eager, OPT_lb, rho, mip_status, lp_valid, align2,
bound_frac, bound_int) are copied from c3_upper.json; the ratios use the denominators of
check_c3_upper.py (lines 72-84, 99-109). Writes code/sim/out/ms2_checks/c3_upper_repro.json,
c3_upper_repro.txt (the reference's format strings) and pd_raises.json (raise histogram and maximum
per family, M54; informative).

Run from code/sim under the 3 GB cap (run_ms2_checks.sh):
  python -m sublet.experiments.repro_c3_upper [--out DIR] [--workers 4] [--seeds 40] [--quick]
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from ..paths import C3, import_ref
from .repro_common import checks_dir, pool_map

OUT = checks_dir()
REF_JSON = C3 / "out" / "c3_upper.json"
FAMILIES = ("rand", "slo", "setcover", "spiky", "big")
COPIED = ("LP_trunc", "LP_aligned", "OPT_eager", "OPT_lb", "rho", "mip_status", "lp_valid", "align2",
          "bound_frac", "bound_int")


def core_requests(I):
    """Requests of the core order (core.Instance.elements(), §5.1): slots ascending, then clients."""
    for t in range(I.T):
        for c in range(I.n):
            if I.active[c, t]:
                yield c, t


def run_core(I, rng=None, rbar=None, **pd_kw):
    """VecPD(problem_from_core(I), **pd_kw) on the core requests, with an inline Rounder(pd, rng, rbar)
    after each request if rng is given. Returns (pd, rounder or None, raises per request)."""
    from ..algos.pd_core import VecPD, problem_from_core
    from ..algos.rounding import Rounder
    pd = VecPD(problem_from_core(I), **pd_kw)
    rd = Rounder(pd, rng, rbar) if rng is not None else None
    raises = []
    for c, t in core_requests(I):
        out = pd.request(c, t)
        raises.append(int(out.raises))
        if rd is not None:
            rd.process(out, (c, 1))
    return pd, rd, raises


def cap_hits(pd, raises) -> int:
    """Requests that hit the raise cap (VecPD.stats['cap_hits'] if kept, else raises above max_raises)."""
    st = getattr(pd, "stats", None) or {}
    if "cap_hits" in st:
        return int(st["cap_hits"])
    return int(sum(r > pd.max_raises for r in raises))


def job(args) -> dict:
    fam, seed, seeds, ref = args
    from ..algos.rounding import rbar_theory
    chk = import_ref("check_c3_upper")
    t0 = time.perf_counter()
    I = chk.make(fam, seed)
    pd, _, raises = run_core(I)
    P, dual, d = pd.primal(), pd.dual, int(getattr(pd, "d", pd.prob.d))
    r = rbar_theory(max(I.n * I.T, 3))
    an, pr, h1 = [], [], []
    for s in range(seeds):
        _, rd, _ = run_core(I, np.random.default_rng(s), r)
        an.append(rd.cost_an)
        pr.append(rd.cost_pr)
        _, rd1, _ = run_core(I, np.random.default_rng(s), 1)
        h1.append(rd1.cost_pr)
    an, pr, h1 = float(np.mean(an)), float(np.mean(pr)), float(np.mean(h1))
    OPT, OPTlb = ref["OPT_eager"], ref["OPT_lb"]
    rec = dict(fam=fam, seed=seed, m=I.m, K=I.K, J=I.J, n_el=len(I.elements()), d=d, r=r, P=P, dual=dual,
               dualfeas=pd.dual_feasibility(), iter_hits=cap_hits(pd, raises),
               P_over_LPal=P / ref["LP_aligned"], P_over_2dual=P / (2 * dual), ALG_an=an, ALG_pr=pr, ALG_r1=h1,
               chk_an_vs_rP=an / (r * P + OPT), ratio_an=an / OPTlb, ratio_pr=pr / OPTlb, ratio_r1=h1 / OPTlb)
    rec.update({k: ref[k] for k in COPIED})
    hist: dict[int, int] = {}
    for x in raises:
        hist[x] = hist.get(x, 0) + 1
    rec["_raises"] = hist
    rec["_seconds"] = time.perf_counter() - t0
    return rec


def text(recs: list[dict]) -> str:
    """c3_upper.txt with check_c3_upper.py's format strings (lines 95-109)."""
    lines = []
    hdr = ('fam       #  P/LPal(max) bound  dualfeas(max) P/2Y(max) LPt<=OPT LPal<=2LPt '
           'an/(rP+OPT)(max) ALGan/OPT(mean,max) bound_int  ALGpr/OPT(mean)  r=1/OPT(mean,max)')
    lines.append(hdr)
    for f in FAMILIES:
        R = [x for x in recs if x['fam'] == f]
        if not R:
            continue
        g = lambda k: np.array([x[k] for x in R])
        lines.append(f"{f:9s} {len(R):2d}  {g('P_over_LPal').max():.3f}     {g('bound_frac').max():.2f}   "
                     f"{g('dualfeas').max():.3f}         {g('P_over_2dual').max():.3f}     "
                     f"{all(g('lp_valid'))}     {all(g('align2'))}       {g('chk_an_vs_rP').max():.3f}"
                     f"            {g('ratio_an').mean():.2f},{g('ratio_an').max():.2f}        "
                     f"{g('bound_int').max():.1f}     {g('ratio_pr').mean():.2f}            "
                     f"{g('ratio_r1').mean():.2f},{g('ratio_r1').max():.2f}")
        lines.append(f"          frac P/OPT_eager mean {np.mean(g('P')/g('OPT_lb')):.3f} max {np.max(g('P')/g('OPT_lb')):.3f}; "
                     f"LPal/LPt max {np.max(g('LP_aligned')/g('LP_trunc')):.3f}; OPT/LPt max {np.max(g('OPT_eager')/g('LP_trunc')):.3f}; "
                     f"rho range [{g('rho').min():.2f},{g('rho').max():.2f}]; mip_status {set(g('mip_status'))}; iter_hits {g('iter_hits').sum()}")
    return '\n'.join(lines)


def raises_summary(recs: list[dict]) -> dict:
    """pd_raises.json: per family the histogram of raises per request, its mean and maximum (M54)."""
    out = {}
    for f in FAMILIES:
        hist: dict[int, int] = {}
        for x in recs:
            if x["fam"] == f:
                for k, v in x["_raises"].items():
                    hist[int(k)] = hist.get(int(k), 0) + v
        if not hist:
            continue
        n = sum(hist.values())
        out[f] = {"requests": n, "raises_hist": {str(k): hist[k] for k in sorted(hist)},
                  "raises_mean": sum(k * v for k, v in hist.items()) / n, "raises_max": max(hist),
                  "cap_hits": sum(x["iter_hits"] for x in recs if x["fam"] == f)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT, help="output folder (default code/sim/out/ms2_checks or SUBLET_MS2_CHECKS_DIR)")
    ap.add_argument("--workers", type=int, default=4, help="worker processes (at most 4)")
    ap.add_argument("--seeds", type=int, default=40, help="rounding seeds per instance (reference: 40)")
    ap.add_argument("--quick", action="store_true", help="seed 0 of each family only (a smoke check)")
    a = ap.parse_args(argv)
    ref = {(x["fam"], x["seed"]): x for x in json.loads(REF_JSON.read_text())}
    jobs = [(f, s, a.seeds, ref[(f, s)]) for f in FAMILIES for s in range(12) if not a.quick or s == 0]
    t0 = time.perf_counter()
    recs = pool_map(job, jobs, a.workers)
    a.out.mkdir(parents=True, exist_ok=True)
    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in recs]
    (a.out / "c3_upper_repro.json").write_text(json.dumps(clean, indent=1) + "\n")
    (a.out / "c3_upper_repro.txt").write_text(text(recs) + "\n")
    meta = {"script": "code/sim/sublet/experiments/repro_c3_upper.py",
            "spec": "design/sim_spec_ms2.md §17.3 R1 and M54 (informative)",
            "families": "check_c3_upper.make(fam, seed), seeds 0-11" + (" (quick: seed 0)" if a.quick else ""),
            "rounding_seeds": a.seeds, "seconds": time.perf_counter() - t0}
    (a.out / "pd_raises.json").write_text(json.dumps({"meta": meta, "families": raises_summary(recs)}, indent=1) + "\n")
    print(text(recs), flush=True)
    print(f"[repro_c3_upper] {len(recs)} instances in {time.perf_counter() - t0:.1f} s; wrote {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
