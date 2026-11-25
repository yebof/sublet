"""The certificate failures of the Q44 study and the wind-down fix (design/q44_practical_sublet.md §8.9, §8.11;
sublet/algos/guard.py, module docstring and Theorem W).

  python -m sublet.experiments.q44_winddown [--runs DIR] [--out DIR] [--limit N]

Reads the run files of the study (default `<q44 out>/runs`, q44_study.out_root) and selects the guarded full-model
runs whose certificate did not hold. For each it rebuilds the run from the block files (instance, cell, mode, tag
and seeds of its q44 record) and reruns it twice through drivers/run.py's policy construction:
  - 'historical': the parameters the run had (the tag's, with the test its certificate records; test T0g with
    reserve false and wind_down 'keep', the T0g of commit d2a538d). The rerun must reproduce the recorded
    ALG(T) and core-bound slack. Its cost after the abort slot t_a is decomposed by ledger component against
    the safe expert's increments C_S(T) - C_S(t_a - 1) and W_S(t_a), and the inner's leases held at t_a are
    described from the lease records (end cause, minutes from t_a Δs to their billed end and to their end).
  - 'default': the tag's parameters without 'test', i.e. A8's default since the decision of 2026-10-17
    (test T0g with the reserve, wind_down 'auto' = 'adaptive'), with the certificate of q44_study.certificate.
Writes winddown.json (one record per run and the aggregates) and winddown.md into `--out` (default
`<q44 out>/winddown`). Cost components are in USD.

Scope in time: the 'correlated' lender (the study's mode L-co) draws its shocks per (source lender, onset, target
lender) since 2026-10-19 (design/sim_spec.md §6.6 and §10 S11), where the study's runs drew them per source site.
On code after that change the 'historical' reruns of L-co runs do not reproduce the recorded values; the recorded
winddown.json was written before the change.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Optional

import numpy as np

from . import q44_study as qs

COMPONENTS = ("lease_prepaid", "lease_rent", "loading", "routing", "fallback", "stranding_kv", "stranding_fl",
              "stranding_fb", "stranding_pi")
REPRO_TOL = 1e-9


def failing_runs(runs: Path) -> list[dict]:
    """The q44 records (with the file name) of the guarded full-model runs whose certificate did not hold."""
    out = []
    for p in sorted(runs.rglob("*.json")):
        if p.name.startswith("cell_") or p.name.endswith("_error.json") or "/core/" in p.as_posix():
            continue
        try:
            js = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        q = js.get("q44") or {}
        c = q.get("certificate")
        if q.get("policy_id") == "A8" and isinstance(c, dict) and c.get("available") and c.get("held") is False:
            out.append({**q, "file": str(p.relative_to(runs))})
    return out


def historical_params(q: dict) -> dict:
    """The parameters the run had: the tag's, with its certificate's test; T0g as at commit d2a538d."""
    p = dict(qs.POLICIES[q["tag"]]["params"])
    test = q["certificate"]["test"]
    p["test"] = test
    if test == "T0g":
        p.update(reserve=False, wind_down="keep")
    return p


def default_params(q: dict) -> dict:
    return {k: v for k, v in qs.POLICIES[q["tag"]]["params"].items() if k != "test"}


def _rerun(q: dict, params: dict):
    from ..drivers import run as drun
    from ..engine import simulate
    block = qs.load_block(q["block"])
    inst = next(i for i in block["instances"] if i["id"] == q["instance"])
    c, seeds = int(q["cell"]), q["seeds"]
    spec = drun.load_run_spec(qs.run_spec(block, inst, q["tag"], q["mode"], c, [int(seeds["policy"])], params))
    I, model, ecfg = drun.build(spec, c)
    pol, _ = drun._make_policy(spec, I)
    res = simulate(I, pol, model, ecfg, lender_seed=int(seeds["lender"]), policy_seed=int(seeds["policy"]))
    return I, res


def decompose(I, res, rep: dict) -> dict:
    """The cost after t_a by ledger component, against the safe expert's increments and W_S(t_a), and the inner's
    leases held at t_a (lease records)."""
    ps = res.per_slot
    ta = rep["t_a"]
    T = len(ps["total"])
    curve = np.asarray(rep["safe"]["curve_S"], dtype=float)
    W = float(rep.get("W_S_t_a") or 0.0)
    after = {k: float(np.sum(ps[k][ta:])) for k in COMPONENTS}
    tot_after = float(np.sum(ps["total"][ta:]))
    Q = qs.fallback_per_slot(I)
    strand = sum(np.asarray(ps[k], dtype=float) for k in COMPONENTS if k.startswith("stranding_"))
    Ds = I.grid.slow_min
    Df = I.grid.fast_min                # held at t_a: alive in its first fast slot (rule T6), or released there
    held = [L for L in res.leases if L.start_slot < ta and (L.end_min >= ta * Ds + Df or
                                                            (L.release_min is not None and L.release_min == ta * Ds))]
    fol = rep["safe"]["followed"]
    return {"t_a": int(ta), "excess": tot_after - (W + float(np.sum(curve[ta:]))), "W_S_t_a": W,
            "S_increments": float(np.sum(curve[ta:])), "Q_after": float(np.sum(Q[ta:])), "after": after,
            "routing_saving": float(np.sum(Q[ta:])) - after["routing"] - after["fallback"],
            "stranding_after": float(np.sum(strand[ta:])), "stranding_at_t_a": float(strand[ta]),
            "rent_after": after["lease_rent"], "purchases_after": after["lease_prepaid"] + after["loading"],
            "held_at_t_a": len(held), "end_causes": dict(Counter(L.end_cause for L in held)),
            "released_at_t_a": sum(1 for L in held if L.release_min == ta * Ds),
            "minutes_to_billed_end": sorted(int(L.prepaid_end_min - ta * Ds) for L in held),
            "minutes_to_end": sorted(int(L.end_min - ta * Ds) for L in held),
            "contracts": sorted({I.contracts[L.contract].id for L in held}),
            "fb_after_t_a": all(w == "FB" for w, t0, n in fol if t0 + n > ta),
            "drops_after_t_a": int(rep["exec"]["precheck"]), "refusals_after_t_a": int(rep["exec"]["refused"]),
            "switches_after_t_a": int(rep["safe"].get("switches_after_t_a") or 0), "T": T}


def one(q: dict) -> dict:
    rec = {"file": q["file"], "block": q["block"], "instance": q["instance"], "cell": q["cell"], "mode": q["mode"],
           "tag": q["tag"], "seeds": q["seeds"], "recorded": {k: q["certificate"].get(k) for k in (
               "test", "t_a", "ALG_T", "core_bound_slack", "core_bound_rhs", "s_mode_excess")}}
    t0 = time.perf_counter()
    I, res = _rerun(q, historical_params(q))
    rep = res.metrics["policy"]
    c = qs.certificate(res, I, rep, core_exact=False)
    rc = rec["recorded"]
    rec["historical"] = {"params": historical_params(q), "held": c["held"], "t_a": c["t_a"], "ALG_T": c["ALG_T"],
                         "core_bound_slack": c["core_bound_slack"], "s_mode_excess": c["s_mode_excess"],
                         "reproduced": bool(c["t_a"] == rc["t_a"] and abs(c["ALG_T"] - rc["ALG_T"]) <= REPRO_TOL *
                                            max(1.0, abs(rc["ALG_T"])) and abs(c["core_bound_slack"] -
                                                                              rc["core_bound_slack"]) <= 1e-9),
                         "decomposition": decompose(I, res, rep) if c["t_a"] is not None else None}
    I2, res2 = _rerun(q, default_params(q))
    rep2 = res2.metrics["policy"]
    c2 = qs.certificate(res2, I2, rep2, core_exact=False)
    rec["default"] = {k: c2.get(k) for k in (
        "test", "wind_down", "held", "t_a", "ALG_T", "core_bound_ok", "core_bound_slack", "core_bound_rhs",
        "e_mode_ok", "m_ok", "m_max", "e_mode_reserve_ok", "proven_case", "fb_after_t_a", "budget_t_a",
        "wind_down_cost", "wind_down_ok", "reserve_max")}
    wd = rep2.get("wd") or []
    rec["default"].update(wd_choices=[x.get("choice") for x in wd], wd_kept=[x.get("kept") for x in wd],
                          beta_K0_le_budget=all(x.get("beta_K0_le_budget", True) for x in wd),
                          on_unavailable=rep2.get("on_unavailable"),
                          invariant_failures=len(res.invariant_failures) + len(res2.invariant_failures))
    rec["wall_s"] = time.perf_counter() - t0
    return rec


def _stats(v) -> dict:
    v = [float(x) for x in v if x is not None]
    if not v:
        return {"n": 0}
    return {"n": len(v), "min": float(min(v)), "median": float(np.median(v)), "max": float(max(v)), "sum": float(sum(v))}


def aggregate(recs: list[dict]) -> dict:
    H = [r["historical"] for r in recs]
    D = [h["decomposition"] for h in H if h["decomposition"]]
    N = [r["default"] for r in recs]
    comp = {k: float(sum(d["after"][k] for d in D)) for k in COMPONENTS}
    shift = Counter((n["t_a"] - h["t_a"]) if (n["t_a"] is not None and h["t_a"] is not None) else None
                    for n, h in zip(N, H))
    choices = Counter(c for n in N for c in n["wd_choices"])
    return {"runs": len(recs), "by_tag": dict(Counter(r["tag"] for r in recs)),
            "by_block_instance": dict(Counter(f"{r['block']}/{r['instance']}" for r in recs)),
            "historical": {"reproduced": sum(h["reproduced"] for h in H), "held": sum(bool(h["held"]) for h in H),
                           "aborted": len(D), "fb_after_t_a": sum(d["fb_after_t_a"] for d in D),
                           "no_drop_refusal_switch": sum(d["drops_after_t_a"] == 0 and d["refusals_after_t_a"] == 0
                                                         and d["switches_after_t_a"] == 0 for d in D),
                           "W_S_t_a_zero": sum(d["W_S_t_a"] == 0.0 for d in D),
                           "components_after_t_a": comp, "excess": _stats(d["excess"] for d in D),
                           "stranding_after": _stats(d["stranding_after"] for d in D),
                           "stranding_at_t_a": _stats(d["stranding_at_t_a"] for d in D),
                           "rent_after": _stats(d["rent_after"] for d in D),
                           "routing_saving": _stats(d["routing_saving"] for d in D),
                           "purchases_after": _stats(d["purchases_after"] for d in D),
                           "excess_identity_max": float(max((abs(d["excess"] - (d["stranding_after"] + d["rent_after"]
                                                                                - d["routing_saving"] + d["purchases_after"]
                                                                                - d["W_S_t_a"])) for d in D),
                                                            default=0.0)),
                           "end_causes": dict(sum((Counter(d["end_causes"]) for d in D), Counter())),
                           "held_at_t_a": dict(Counter(d["held_at_t_a"] for d in D)),
                           "minutes_to_billed_end": dict(Counter(m for d in D for m in d["minutes_to_billed_end"])),
                           "contracts": dict(Counter(k for d in D for k in d["contracts"]))},
            "default": {"held": sum(bool(n["held"]) for n in N), "proven_case": sum(bool(n["proven_case"]) for n in N),
                        "aborted": sum(n["t_a"] is not None for n in N),
                        "wind_down_ok": sum(bool(n["wind_down_ok"]) for n in N),
                        "beta_K0_le_budget": sum(bool(n["beta_K0_le_budget"]) for n in N),
                        "m_max": float(max((n["m_max"] for n in N), default=0.0)),
                        "core_bound_slack": _stats(n["core_bound_slack"] for n in N),
                        "budget_t_a": _stats(n["budget_t_a"] for n in N),
                        "wind_down_cost": _stats(n["wind_down_cost"] for n in N),
                        "t_a_shift_vs_historical": {str(k): v for k, v in sorted(shift.items(), key=lambda x: (x[0] is None, x[0] or 0))},
                        "cost_ratio_default_over_historical": _stats(n["ALG_T"] / h["ALG_T"] for n, h in zip(N, H)),
                        "wind_down_choices": dict(choices),
                        "invariant_failures": sum(n["invariant_failures"] for n in N)}}


def write_md(recs: list[dict], agg: dict, path: Path) -> None:
    h, d = agg["historical"], agg["default"]
    L = ["# Q44 certificate failures and the wind-down fix (q44_winddown.py)", "",
         f"Runs: {agg['runs']} guarded full-model runs whose certificate failed; by tag {agg['by_tag']}.", "",
         "## Historical parameters (rerun)", "",
         f"- reproduced (t_a, ALG(T), core-bound slack): {h['reproduced']} of {agg['runs']}; held: {h['held']}",
         f"- S followed FB at and after t_a: {h['fb_after_t_a']} of {h['aborted']}; no drop, refusal or switch after "
         f"t_a: {h['no_drop_refusal_switch']}; W_S(t_a) = 0: {h['W_S_t_a_zero']}",
         "- cost after t_a by component (sum over runs, USD): " + ", ".join(
             f"{k} {v:.4f}" for k, v in h["components_after_t_a"].items()),
         f"- S-mode excess: {h['excess']}", f"- stranding after t_a: {h['stranding_after']}",
         f"- stranding in slot t_a: {h['stranding_at_t_a']}", f"- rent after t_a: {h['rent_after']}",
         f"- routing saving after t_a (Q - routing - fallback): {h['routing_saving']}",
         f"- purchases and loading after t_a: {h['purchases_after']}",
         f"- excess = stranding + rent - saving + purchases - W_S, largest deviation: {h['excess_identity_max']:.3g}",
         f"- inner leases held at t_a: {h['held_at_t_a']}; end causes {h['end_causes']}; minutes from t_a to their "
         f"billed end {h['minutes_to_billed_end']}; contracts {h['contracts']}", "",
         "## Default parameters (test T0g with the reserve, wind_down auto)", "",
         f"- certificate held: {d['held']} of {agg['runs']}; proven case (Theorem W): {d['proven_case']}; "
         f"wind-down cost <= budget: {d['wind_down_ok']}; beta(K0) <= budget at every adaptive slot: "
         f"{d['beta_K0_le_budget']}; max m: {d['m_max']:.3g}; invariant failures: {d['invariant_failures']}",
         f"- core-bound slack: {d['core_bound_slack']}", f"- budget R(t_a - 1): {d['budget_t_a']}",
         f"- wind-down cost: {d['wind_down_cost']}",
         f"- t_a(default) - t_a(historical): {d['t_a_shift_vs_historical']}",
         f"- ALG(T) default / historical: {d['cost_ratio_default_over_historical']}",
         f"- adaptive wind-down choices (per slot): {d['wind_down_choices']}", "",
         "## Runs", "", "| file | tag | test | t_a hist | slack hist | t_a default | held | slack | budget | "
         "wind-down cost |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in recs:
        hh, dd = r["historical"], r["default"]
        L.append(f"| {r['file']} | {r['tag']} | {r['recorded']['test']} | {hh['t_a']} | {hh['core_bound_slack']:.4f} | "
                 f"{dd['t_a']} | {dd['held']} | {dd['core_bound_slack']:.4f} | "
                 f"{(dd['budget_t_a'] if dd['budget_t_a'] is not None else float('nan')):.4f} | "
                 f"{(dd['wind_down_cost'] if dd['wind_down_cost'] is not None else float('nan')):.4f} |")
    path.write_text("\n".join(L) + "\n")


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", default=None, help="the study's runs folder (default <q44 out>/runs)")
    ap.add_argument("--out", default=None, help="output folder (default <q44 out>/winddown)")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args(argv)
    runs = Path(a.runs) if a.runs else qs.out_root() / "runs"
    out = Path(a.out) if a.out else qs.out_root() / "winddown"
    out.mkdir(parents=True, exist_ok=True)
    sel = failing_runs(runs)
    if a.limit is not None:
        sel = sel[: a.limit]
    t0 = time.perf_counter()
    recs = []
    for i, q in enumerate(sel):
        recs.append(one(q))
        r = recs[-1]
        print(f"[q44_winddown] {i + 1}/{len(sel)} {r['file']}: historical held {r['historical']['held']} "
              f"(reproduced {r['historical']['reproduced']}), default held {r['default']['held']}", flush=True)
    agg = aggregate(recs)
    meta = {"git_revision": qs._git_revision(), "versions": qs._versions(), "runs_dir": str(runs),
            "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "wall_s": time.perf_counter() - t0,
            "peak_rss_mb": qs._peak_rss_mb()}
    qs._dump({"meta": meta, "aggregate": agg, "runs": recs}, out / "winddown.json")
    write_md(recs, agg, out / "winddown.md")
    print(json.dumps(agg["default"], default=str)[:2000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
