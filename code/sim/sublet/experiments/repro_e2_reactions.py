"""E2 cells: kind, C2-SW reaction, H*_mu, status and A1's insurance decision per lender, contract and
mu / beta~ (design/sim_spec_ms2.md §9.4, §17.3, M48; informative, no reference value).

Every E2 lender (a11_calibration.json `inputs.maas_lenders` and `inputs.spot_L7_lenders`) and every
contract of its `ir_prices_by_lender` entry with a p99 IR multiplier (a contract without one has
b >= 1 and is not offered, P4) is mapped into C2 units by the formulas of §9.2 at the LLM tier and
load scenario of configs/ms2_single_site.json (one revocable site, one protected site, both load
scenarios explicit so that the replacement's load time lambda' equals lambda): the lease price
a_k = a0 * multiplier; beta~_k = beta_jl + lambda/3600 (g a_k + phi g q_GPU); alpha_k = g a_k / q_j;
alpha_p = g a_p / q_j; mu = (nu beta~_ref + pi (W_f - H_k)^+) / beta~_k with beta~_ref the
instance's stranding reference (beta~ at a0) and nu = mu / beta~_ref in {0.2, 0.5, 1, 2} (S1, S2);
lambda_C2 = (lambda'/3600) q_j / beta~_k; bw = (beta_{j,l_p} + g a_p lambda'/3600) / beta~_k;
H = (H_k / 60) q_j / beta~_k. For each cell and nu it records alpha_k, the kind (alpha >= 1:
outside A1's domain, M59; alpha_p <= alpha_k (2 - alpha_k): (C') fails and the first clause of
§9.3 insures at every H; else (C') may hold), the C2-SW reaction and H*_mu (c2_thresholds with bw),
the status (hstar_status), the first-clause flag and insure_up_front(units, 'lb_react') at the
contract's H (one cached families.lb_react call per row outside the first clause and the
alpha >= 1 cells). Writes code/sim/out/ms2_checks/e2_reactions.json; the cell lists of E2 and M48
are taken from it.

Run from code/sim under the 3 GB cap (run_ms2_checks.sh; needs the a12 outputs for the instance):
  python -m sublet.experiments.repro_e2_reactions [--out DIR] [--workers 4] [--tau-slot-only] [--quick]
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

import numpy as np

from ..paths import ANALYSIS_OUT, CONFIGS
from .repro_common import checks_dir, pool_map

OUT = checks_dir()
CONFIG = CONFIGS / "ms2_single_site.json"
NUS = (0.2, 0.5, 1.0, 2.0)


def setting(config=CONFIG) -> dict:
    """LLM, sites, prices, load times and stranding of the single-site instance (§9.2's engine sources)."""
    from ..instance import build_instance
    inst = build_instance(config)
    assert inst.J == 1, "ms2_single_site.json must serve one LLM"
    lr = [l for l, s in enumerate(inst.sites) if s.kind != "protected"]
    lp = [l for l, s in enumerate(inst.sites) if s.kind == "protected"]
    assert len(lr) == 1 and len(lp) == 1, [s.id for s in inst.sites]
    lr, lp = lr[0], lp[0]
    kp = min((k for k in inst.sites[lp].menu if np.isfinite(inst.price[lp, k])), key=lambda k: inst.price[lp, k])
    L = inst.llms[0]
    st = inst.stranding
    a0, qg, phi, g = inst.a0_usd_per_gpu_h, inst.q_gpu_usd_per_h, inst.phi_load, L.g
    lam = float(inst.lam_s[0, lr])
    bt_ref = float(inst.beta_usd[0, lr]) + lam / 3600.0 * (g * a0 + phi * g * qg)
    mu_ratio = (inst.config.get("stranding") or {}).get("mu_over_beta_tilde")
    if mu_ratio:
        assert abs(st.mu_fb_usd[0] / mu_ratio - bt_ref) <= 1e-9 * max(1.0, bt_ref), (st.mu_fb_usd[0], mu_ratio, bt_ref)
    return {"config": str(config),
            "llm": L.id, "tier": L.tier, "g": g, "q_usd_per_h": float(L.q_usd_per_h), "q_gpu": qg, "a0": a0,
            "phi": phi, "site_rev": inst.sites[lr].id, "site_prot": inst.sites[lp].id,
            "load_scenario_rev": inst.load_scenario[lr], "load_scenario_prot": inst.load_scenario[lp],
            "lam_s": lam, "lam_rep_s": float(inst.lam_s[0, lp]), "beta_jl": float(inst.beta_usd[0, lr]),
            "beta_j_prot": float(inst.beta_usd[0, lp]), "a_p": float(inst.price[lp, kp]),
            "beta_tilde_ref_usd": bt_ref, "pi_usd_per_min": float(st.pi_usd_per_min[0]), "W_f_min": float(st.W_f_min)}


def cells(tau_slot_only: bool = False) -> tuple[list, list]:
    """(offered cells, not offered cells) of E2: (lender, group, contract, H_min, tau class, multiplier)."""
    a11 = json.loads((ANALYSIS_OUT / "a11_calibration.json").read_text())
    inp, ir, con = a11["inputs"], a11["ir_prices_by_lender"], a11["contracts"]
    out, off = [], []
    for grp, names in (("maas", inp["maas_lenders"]), ("spot_L7", inp["spot_L7_lenders"])):
        for n in names:
            for k, v in ir[n]["contracts"].items():
                tau_cls = "1 slot" if con[k]["tau_min"] == con[k]["slot_min"] else f"{con[k]['tau_min']} min"
                if tau_slot_only and tau_cls != "1 slot":
                    continue
                m = v["ir_multiplier"]["p99"]
                cell = dict(lender=n, group=grp, contract=k, H_min=int(con[k]["H_min"]), tau=tau_cls, multiplier=m)
                (off if m is None else out).append(cell)
    return out, off


def row(args) -> dict:
    cell, nu, S, alpha_def, alpha_p_def, phi_def = args
    from ..algos.c2rule import C2Units, c2_thresholds, cr_react_lb, hstar_status, insure_up_front
    g, q, qg, phi = S["g"], S["q_usd_per_h"], S["q_gpu"], S["phi"]
    a_k = S["a0"] * cell["multiplier"]
    lam, lam_rep = S["lam_s"], S["lam_rep_s"]
    bt = S["beta_jl"] + lam / 3600.0 * (g * a_k + phi * g * qg)
    alpha = g * a_k / q
    ap = g * S["a_p"] / q
    Hk = cell["H_min"]
    mu_usd = nu * S["beta_tilde_ref_usd"] + S["pi_usd_per_min"] * max(S["W_f_min"] - Hk, 0.0)
    out = dict(cell, mu_over_beta_tilde_ref=nu, a_usd_per_gpu_h=a_k, alpha_k=alpha, alpha_p=ap, beta_tilde_usd=bt,
               lam_prime_s=lam_rep)
    if alpha >= 1:
        out.update(kind="alpha>=1", reaction=None, H_star_mu_s=None, H_star_over_lambda=None, regime=None,
                   status=hstar_status(alpha, ap, mu_usd / bt, (lam_rep / 3600.0) * q / bt, "c2sw", False),
                   first_clause=None, insure_up_front=None, LB_react=None)
        return out
    u = C2Units(alpha=alpha, ap=ap, mu=mu_usd / bt, lam=(lam_rep / 3600.0) * q / bt,
                bw=(S["beta_j_prot"] + g * S["a_p"] * lam_rep / 3600.0) / bt, H=(Hk / 60.0) * q / bt,
                beta_tilde_usd=bt, time_unit_h=bt / q)
    th = c2_thresholds(u.alpha, u.ap, u.mu, u.lam, 1.0, u.bw)
    first = bool(ap <= alpha * (2 - alpha))
    at_default = (abs(alpha - alpha_def) <= 1e-9 and abs(u.lam - 1 / (alpha_def + phi_def)) <= 1e-9
                  and abs(u.bw - alpha_p_def / (alpha_def + phi_def)) <= 1e-9)
    t0 = time.perf_counter()
    ins = insure_up_front(u, "lb_react")
    lb = None if first else cr_react_lb(u)
    out.update(kind="first-clause" if first else "Cprime", units=dataclasses.asdict(u),
               reaction={"cold": "cold", "warm": "pre-warm"}[th.react], H_star_mu_s=th.Hstar * u.time_unit_h * 3600.0,
               H_star_over_lambda=th.Hstar / u.lam if u.lam > 0 else None, regime=th.regime,
               status=hstar_status(u.alpha, u.ap, u.mu, u.lam, "c2sw", at_default), first_clause=first,
               insure_up_front=bool(ins), LB_react=lb, CR_ins=max(2 - alpha, ap / alpha) if alpha > 0 else None,
               H_C2=u.H, seconds=time.perf_counter() - t0)
    return out


def summary(rows: list) -> dict:
    s = {"rows": len(rows), "by_kind": {}, "pre_warm_rows": {}, "insuring_rows_second_clause": []}
    for r in rows:
        s["by_kind"][r["kind"]] = s["by_kind"].get(r["kind"], 0) + 1
        if r["reaction"] == "pre-warm":
            key = f"{r['kind']} mu={r['mu_over_beta_tilde_ref']}"
            s["pre_warm_rows"][key] = s["pre_warm_rows"].get(key, 0) + 1
        if r["kind"] == "Cprime" and r["insure_up_front"]:
            s["insuring_rows_second_clause"].append([r["lender"], r["contract"], r["mu_over_beta_tilde_ref"]])
    return s


def main(argv=None) -> int:
    ap_ = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap_.add_argument("--out", type=Path, default=OUT, help="output folder (default code/sim/out/ms2_checks or SUBLET_MS2_CHECKS_DIR)")
    ap_.add_argument("--workers", type=int, default=4, help="worker processes (at most 4)")
    ap_.add_argument("--config", type=Path, default=CONFIG, help="single-site instance config")
    ap_.add_argument("--tau-slot-only", action="store_true", help="only contracts with tau = 1 slot")
    ap_.add_argument("--quick", action="store_true", help="the first 6 cells only (a smoke check)")
    a = ap_.parse_args(argv)
    a11 = json.loads((ANALYSIS_OUT / "a11_calibration.json").read_text())
    alpha_def, alpha_p_def, phi_def = (a11["inputs"][k] for k in ("alpha", "alpha_p", "phi"))
    S = setting(a.config)
    offered, not_offered = cells(a.tau_slot_only)
    if a.quick:
        offered = offered[:6]
    t0 = time.perf_counter()
    jobs = [(c, nu, S, alpha_def, alpha_p_def, phi_def) for c in offered for nu in NUS]
    rows = pool_map(row, jobs, a.workers)
    out = {"meta": {"script": "code/sim/sublet/experiments/repro_e2_reactions.py",
                    "spec": "design/sim_spec_ms2.md §9.4, §17.3, M48 (informative)",
                    "source": "code/analysis/out/a11_calibration.json ir_prices_by_lender (p99), inputs",
                    "setting": S, "mu_over_beta_tilde_ref": list(NUS), "tau_slot_only": bool(a.tau_slot_only),
                    "quick": bool(a.quick), "n_cells": len(offered), "not_offered": not_offered,
                    "seconds": time.perf_counter() - t0},
           "summary": summary(rows), "rows": rows}
    a.out.mkdir(parents=True, exist_ok=True)
    path = a.out / "e2_reactions.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["summary"], indent=1)[:4000], flush=True)
    print(f"[repro_e2_reactions] {len(rows)} rows ({len(offered)} cells x {len(NUS)} mu); wrote {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
