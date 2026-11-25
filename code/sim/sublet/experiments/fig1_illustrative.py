"""Fig. 1 v2's illustrative run: one run of Sublet with per-slot logging (design/ms6_spec.md §1.1 M1, §2 U44;
design/ms6/inventory_w8_gate.md §4).

  python -m sublet.experiments.fig1_illustrative [--out DIR] [--reduced]

run from code/sim under a memory cap, e.g. ``systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env
OMP_NUM_THREADS=1 ~/venv/bin/python -m sublet.experiments.fig1_illustrative``. Default DIR is code/sim/out/fig1v2/,
which is written by a run in a clean clone of the commit that holds this driver and then copied in (the MS3-MS5b
precedent of every frozen experiment); a development run goes to another folder.

The run (M1). Sublet is the MS5b tag 'Sublet' (ms5b_common.tag_params: A8P around A9 at the allowance
B(t) = min{W_k(t), LB'(t)}, kappa None; the other parameters A8's defaults), on the pilot cell Q44 I2 c1 (block Q1,
instance I2, the one-day instance example_1day on the 5-min slow grid, config seed 1; a development cell of
design/sublet_v2.md §4.1, never a confirmation cell) under the eager stress lender L-eg, policy seed 0, lender seed
the config seed. The instance and the run spec are built as e7h's part p4 builds that cell (e7h._q44_build,
e7h._q44_spec), and the run is that of e7h.one_run: drivers/run.make_policy, then engine.simulate. The instance's
inputs are versioned (code/analysis/out/a12_*, the Q44 block files); no raw trace is read. The chosen cell is a
stress case, not a typical one (design/ms6/inventory_w8_gate.md §4.2 sets it against the confirmation's runs).

Logging. LoggedProjectedGuarded, defined here and not in algos/guard.py, is ProjectedGuarded with two overrides:
reset starts the list eval_log, and _evaluate, the stateless evaluation of a candidate list (T0gBound.evaluate and
slot_terms), appends (t, n, a-hat, R) of every list it evaluates to eval_log (t the slow slot, n the list's length)
and returns the evaluation unchanged. make_policy builds A8P from the run spec with its driver inputs; since the
subclass adds no constructor state, the built object's class is set to the subclass. ProjectedGuarded.act evaluates the
candidates of a slot in the order E, P1..., P0, K0 and executes the first that passes, so at every slot executed in
mode E the first logged evaluation is the inner list A_E(t) and the last the executed list; a slot whose only
evaluation is A_E(t) is executed as A_E(t).

run.json (deterministic: no time, host or revision; mc.dump_json, compact):
  cell, mode, policy_seed, lender_seed, tag, tag_params (ms5b_common.tag_params), policy {id, params (the policy's
  resolved params())}, instance_hash, grid {T_slow, slow_min, fast_min}, window, gamma, guard_tol (guard.GUARD_TOL,
  the relative tolerance of the guard's test)
  series     per slow slot t = 0..T-1: t, t_h (t x slow_min / 60, the slot's start in hours since the start of the
             run), test_value (a-hat(t) + R(t) of the executed list: the guard's record), a_hat, reserve, threshold
             (gamma C_S(t) + B(t), the guard's rhs), C_S (the safe expert's accounted cost), B (the allowance B(t),
             the OnlineLB's), candidate (the executed candidate: E, P1, P0 or K0), projected (candidate is not E),
             n_inner (the length of A_E(t)), inner_test_value (a-hat_E(t) + R_E(t) of A_E(t) at a projected slot,
             null at a slot executed as A_E(t), where it is test_value), ALG (the ledger's cost of the slot,
             per_slot['total']) and ALG_cum (its cumulative sum)
  evaluations  fields [t, n, a_hat, R] and rows, every logged evaluation in order
  summary    ALG_T (the ledger total, as e7.run_entry's ALG), n_slots, aborted, t_a, projected_slots, projection,
             candidates (run-length encoded, the report's), B_T, online_lb, s_fb_all, t0g_bound_all, envelope
             (ms5b_common.guard_extras: the pilot record's fields), min_margin_usd (least threshold - test_value),
             inner_excess_usd {min, max} (inner_test_value - threshold over the projected slots) and projected_runs
             ([first, last] slot of each run of consecutive projected slots)
manifest.json: what, spec, command, git_revision, tracked_files_dirty (read-only git: tracked changes only, as
figs/rebuild.py), cell, mode, policy_seed, lender_seed, tag, tag_params, policy, window, reduced, started, wall_s,
peak_rss_mb, versions, run_file and run_sha256 (sha256 of run.json's bytes), and checks:
  identical  the logged run's policy report (JSON with sorted keys), its per-slot costs and its components equal those
             of an unlogged run of the same spec (bit for bit)
  log        at every slot the guard executed, the first evaluation has n = len(A_E(t)), the last one's a-hat and R
             equal the guard's record bit for bit, a slot with one evaluation is executed as E and one with more is
             projected; at every projected slot A_E(t)'s test value exceeds the guard's limit rhs + GUARD_TOL max(1,
             |rhs|), and at every slot the executed one does not; the guard's C_S and B equal the safe expert's
             C_S_curve and B_curve
  pilot      (full run only) ALG(T) equals the pilot's record (code/sim/out/sublet_v2_pilot/p4/summary.json, the run
             with tag Sublet, cell I2:c1, mode L-eg, seed 0) within PILOT_TOL = 1e-9 USD, and so do B_T and the
             envelope's max_excess_usd; projected_slots, projection and aborted are equal
  pass       all of them; the driver exits 1 otherwise (the files are written for diagnosis).
--reduced runs the same cell on the slow slots WINDOW_REDUCED, the day's first 3 h (instance.restrict_horizon, as e7h's
reduced runs restrict theirs), for the figure's test fixture (tests/fixtures_figs_ms6/; not a result): no pilot check.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import hashlib
import json
import resource
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

from .. import paths
from ..algos.guard import GUARD_TOL, ProjectedGuarded

NAME = "fig1v2"
SPEC = "design/ms6_spec.md §1.1 M1, §2 U44"
OUT = paths.SIM_OUT / "fig1v2"
RUN_FILE, MANIFEST_FILE = "run.json", "manifest.json"
BLOCK, INST, C = "Q1", "I2", 1                 # the pilot cell Q44 I2 c1 (design/sublet_v2.md §4.1)
MODE = "L-eg"                                  # the eager stress lender
POLICY_SEED = 0
TAG = "Sublet"
WINDOW_REDUCED = (0, 36)                       # --reduced: slow slots [0, 36), the day's first 3 h
PILOT = "code/sim/out/sublet_v2_pilot/p4/summary.json"
PILOT_KEY = {"kind": "q44", "cell": f"{INST}:c{C}", "tag": TAG, "mode": MODE, "seed": POLICY_SEED}
PILOT_TOL = 1e-9                               # USD


class LoggedProjectedGuarded(ProjectedGuarded):
    """A8P (ProjectedGuarded) with a log of every candidate list it evaluates: (t, n, a-hat, R), t the slow slot and n
    the list's length. _evaluate is stateless, and the override returns its result unchanged, so the run is A8P's
    (check 'identical' of the module docstring)."""

    def reset(self, view, rng) -> None:
        super().reset(view, rng)
        self.eval_log: list = []

    def _evaluate(self, obs, lst: list, Q: float) -> tuple:
        e = super()._evaluate(obs, lst, Q)
        self.eval_log.append([int(obs.t), len(lst), float(e[0]), float(e[1])])
        return e


def logged(pol):
    """The A8P object built by make_policy, its class set to LoggedProjectedGuarded (which adds no constructor
    state)."""
    if type(pol) is not ProjectedGuarded:
        raise TypeError(f"expected A8P (ProjectedGuarded), got {type(pol).__name__}")
    pol.__class__ = LoggedProjectedGuarded
    return pol


# ---------------------------------------------------------------- the cell and the run
def build(window: Optional[tuple] = None) -> dict:
    """The cell's instance, engine config, run spec and lender model, as e7h's part p4 builds them."""
    from ..drivers import run as drun
    from . import e7h
    from . import ms5b_common as m5
    win = None if window is None else [int(window[0]), int(window[1])]
    block, idef, inst, ecfg = e7h._q44_build(BLOCK, INST, C, win)
    params = m5.tag_params(TAG, inst)
    spec = e7h._q44_spec(block, idef, TAG, MODE, C, [POLICY_SEED], params)
    model = drun._lender_model(spec, inst)
    return {"inst": inst, "ecfg": ecfg, "spec": spec, "model": model, "tag_params": params, "window": win,
            "config": idef.get("config")}


def simulate(cell: dict, *, log: bool):
    """One run of the cell: (result, policy)."""
    from ..drivers import run as drun
    from ..engine import simulate as sim
    pol = drun.make_policy(cell["spec"], cell["inst"])
    if log:
        pol = logged(pol)
    res = sim(cell["inst"], pol, cell["model"], cell["ecfg"], lender_seed=C, policy_seed=POLICY_SEED)
    return res, pol


def _rle_expand(rle: list) -> list:
    out: list = []
    for name, first, n in rle:
        if first != len(out):
            raise ValueError(f"candidates: run {name} starts at {first}, expected {len(out)}")
        out += [name] * int(n)
    return out


def _runs(mask) -> list:
    """[first, last] of each run of consecutive true entries."""
    out: list = []
    for t, v in enumerate(mask):
        if v and out and out[-1][1] == t - 1:
            out[-1][1] = t
        elif v:
            out.append([t, t])
    return out


def record(res, pol, cell: dict) -> tuple[dict, dict]:
    """(run.json's content, the 'log' check) of the logged run."""
    from . import ms3_common as mc
    from . import ms5b_common as m5
    inst = cell["inst"]
    rep = res.metrics["policy"]
    g, safe = rep["guard"], rep["safe"]
    T, slow_min = int(inst.grid.T_slow), float(inst.grid.slow_min)
    gamma = float(rep["gamma"])
    alg = np.asarray(res.per_slot["total"], dtype=np.float64)
    if len(alg) != T:
        raise ValueError(f"per_slot['total'] has {len(alg)} slots, the grid {T}")
    slots = [int(s) for s in g["slots"]]
    t_a = rep.get("t_a")
    executed = slots[:-1] if t_a is not None else slots          # the abort slot is recorded, not executed
    cands = _rle_expand(rep.get("candidates") or [])
    if len(cands) != len(executed) or executed != list(range(len(executed))):
        raise ValueError(f"{len(cands)} executed candidates for the executed slots {executed[:3]}...")
    by_t: dict = {}
    for row in pol.eval_log:
        by_t.setdefault(row[0], []).append(row)
    bad: list = []
    C_S_curve, B_curve = safe["C_S_curve"], safe["B_curve"]
    n_inner, inner = [None] * T, [None] * T
    for i, t in enumerate(executed):
        ev = by_t.get(t) or []
        rhs = float(g["rhs"][i])
        lim = rhs + GUARD_TOL * max(1.0, abs(rhs))
        if not ev:
            bad.append(f"slot {t}: no evaluation logged")
            continue
        n_inner[t] = int(ev[0][1])
        last = ev[-1]
        if last[2] != float(g["a_hat"][i]) or last[3] != float(g["reserve"][i]):
            bad.append(f"slot {t}: the executed evaluation differs from the guard's record")
        if (len(ev) == 1) != (cands[i] == "E"):
            bad.append(f"slot {t}: {len(ev)} evaluations, candidate {cands[i]}")
        if g["a_hat"][i] + g["reserve"][i] > lim:
            bad.append(f"slot {t}: the executed test value exceeds the limit")
        if cands[i] != "E":
            inner[t] = ev[0][2] + ev[0][3]
            if not inner[t] > lim:
                bad.append(f"slot {t}: projected, but A_E(t)'s test value does not exceed the limit")
        if float(g["C_S"][i]) != float(C_S_curve[t]) or float(g["B"][i]) != float(B_curve[t]):
            bad.append(f"slot {t}: the guard's C_S or B differs from the safe expert's curves")
    extra = sorted(set(by_t) - set(executed))
    if extra:
        bad.append(f"evaluations logged at slots {extra[:5]} that the guard did not execute")
    test = [float(a) + float(r) for a, r in zip(g["a_hat"][:len(executed)], g["reserve"][:len(executed)])]
    thr = [float(v) for v in g["rhs"][:len(executed)]]
    proj = [c != "E" for c in cands]
    ex = [inner[t] - thr[t] for t in executed if proj[t]]
    gx = m5.guard_extras(res, rep)
    ne = len(executed)
    run = {
        "what": "Fig. 1 v2's illustrative run of Sublet (A8P around A9), per-slot logging",
        "spec": SPEC,
        "cell": {"block": BLOCK, "inst": INST, "c": C, "cell": f"{INST}:c{C}", "config": cell["config"],
                 "development_cell": True},
        "window": cell["window"], "mode": MODE, "policy_seed": POLICY_SEED, "lender_seed": C, "tag": TAG,
        "tag_params": cell["tag_params"],
        "policy": {"id": cell["spec"]["policy"]["id"], "params": pol.params()},
        "instance_hash": mc.instance_hash(inst),
        "grid": {"T_slow": T, "slow_min": slow_min, "fast_min": float(inst.grid.fast_min)},
        "gamma": gamma, "guard_tol": GUARD_TOL,
        "series": {
            "t": list(range(T)), "t_h": [t * slow_min / 60.0 for t in range(T)],
            "test_value": test + [None] * (T - ne),
            "a_hat": [float(v) for v in g["a_hat"][:ne]] + [None] * (T - ne),
            "reserve": [float(v) for v in g["reserve"][:ne]] + [None] * (T - ne),
            "threshold": thr + [None] * (T - ne),
            "C_S": [float(v) for v in C_S_curve], "B": [float(v) for v in B_curve],
            "candidate": cands + [None] * (T - ne), "projected": proj + [None] * (T - ne),
            "n_inner": n_inner, "inner_test_value": inner,
            "ALG": alg.tolist(), "ALG_cum": np.cumsum(alg).tolist(),
        },
        "evaluations": {"fields": ["t", "n", "a_hat", "R"], "rows": [list(r) for r in pol.eval_log]},
        "summary": {
            "ALG_T": float(res.components["total"]), "n_slots": T, "aborted": bool(rep.get("aborted")),
            "t_a": t_a, "projected_slots": gx["projected_slots"], "projection": gx["projection"],
            "candidates": rep.get("candidates"), "B_T": gx["B_T"], "online_lb": gx.get("online_lb"),
            "s_fb_all": gx["s_fb_all"], "t0g_bound_all": gx["t0g_bound_all"], "envelope": gx["envelope"],
            "min_margin_usd": min(h - v for h, v in zip(thr, test)) if ne else None,
            "inner_excess_usd": {"min": min(ex), "max": max(ex)} if ex else None,
            "projected_runs": _runs(proj),
        },
    }
    return run, {"ok": not bad, "n_evaluations": len(pol.eval_log), "problems": bad[:20]}


def identical(res_a, res_b) -> dict:
    """Whether two runs have the same policy report, per-slot costs and components (bit for bit)."""
    rep = [json.dumps(r.metrics.get("policy"), sort_keys=True, default=str) for r in (res_a, res_b)]
    keys = sorted(res_a.per_slot)
    slots = keys == sorted(res_b.per_slot) and all(
        np.array_equal(np.asarray(res_a.per_slot[k]), np.asarray(res_b.per_slot[k])) for k in keys)
    comps = json.dumps(res_a.components, sort_keys=True, default=str) == \
        json.dumps(res_b.components, sort_keys=True, default=str)
    out = {"report": rep[0] == rep[1], "per_slot": bool(slots), "components": comps}
    out["ok"] = all(out.values())
    return out


def pilot_check(run: dict) -> dict:
    """The run against the pilot's record of the same cell, mode, tag and seed (PILOT, PILOT_KEY)."""
    p = paths.REPO / PILOT
    try:
        rows = [r for r in json.loads(p.read_text())["runs"] if all(r.get(k) == v for k, v in PILOT_KEY.items())]
    except (OSError, ValueError, KeyError) as e:
        return {"ok": False, "file": PILOT, "note": f"cannot read the pilot's record: {e}"}
    if len(rows) != 1:
        return {"ok": False, "file": PILOT, "note": f"{len(rows)} records match {PILOT_KEY}"}
    r, s = rows[0], run["summary"]
    g = r.get("guard") or {}
    diffs = {"ALG": abs(s["ALG_T"] - float(r["ALG"])), "B_T": abs(s["B_T"] - float(g["B_T"])),
             "env_max_excess_usd": abs(s["envelope"]["max_excess_usd"] - float(g["env_max_excess_usd"]))}
    same = {"projected_slots": s["projected_slots"] == g.get("projected_slots"),
            "projection": s["projection"] == g.get("projection"), "aborted": s["aborted"] == g.get("aborted")}
    return {"ok": all(v <= PILOT_TOL for v in diffs.values()) and all(same.values()), "file": PILOT,
            "key": dict(PILOT_KEY), "tol_usd": PILOT_TOL, "pilot": {"ALG": r["ALG"], "B_T": g.get("B_T"),
            "env_max_excess_usd": g.get("env_max_excess_usd"), "projected_slots": g.get("projected_slots"),
            "projection": g.get("projection"), "aborted": g.get("aborted")}, "abs_diff": diffs, "equal": same}


def _git_dirty() -> Optional[bool]:
    from . import ms5b_common as m5
    s = m5.git("status", "--porcelain", "--untracked-files=no")
    return None if s is None else bool(s.strip())


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.fig1_illustrative",
                                 description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(OUT), help=f"output folder (default {OUT})")
    ap.add_argument("--reduced", action="store_true",
                    help=f"the slow slots [{WINDOW_REDUCED[0]}, {sum(WINDOW_REDUCED)}) only (test fixtures)")
    args = ap.parse_args(argv)
    from . import ms3_common as mc
    out = Path(args.out)
    started, t0 = mc._now(), time.perf_counter()
    cell = build(WINDOW_REDUCED if args.reduced else None)
    res, pol = simulate(cell, log=True)
    run, log_check = record(res, pol, cell)
    res_u, _ = simulate(cell, log=False)
    checks = {"identical": identical(res, res_u), "log": log_check,
              "pilot": None if args.reduced else pilot_check(run)}
    if args.reduced:
        checks["pilot_note"] = "reduced run (a window of the cell): no pilot record"
    checks["pass"] = bool(checks["identical"]["ok"] and log_check["ok"] and (args.reduced or checks["pilot"]["ok"]))
    run_path = mc.dump_json(run, out / RUN_FILE, compact=True)
    man = {"what": run["what"], "spec": SPEC, "command": "python -m sublet.experiments.fig1_illustrative" +
           (" --reduced" if args.reduced else ""), "git_revision": mc.git_revision(),
           "tracked_files_dirty": _git_dirty(), "cell": run["cell"], "mode": MODE, "policy_seed": POLICY_SEED,
           "lender_seed": C, "tag": TAG, "tag_params": run["tag_params"], "policy": run["policy"],
           "window": cell["window"], "reduced": bool(args.reduced), "started": started,
           "wall_s": time.perf_counter() - t0,
           "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, "versions": mc.versions(),
           "run_file": RUN_FILE, "run_sha256": hashlib.sha256(run_path.read_bytes()).hexdigest(), "checks": checks}
    mc.dump_json(man, out / MANIFEST_FILE)
    s = run["summary"]
    print(f"[{NAME}] {run['cell']['cell']} {MODE} p{POLICY_SEED}{' (reduced)' if args.reduced else ''}: ALG "
          f"{s['ALG_T']!r} USD, projected {s['projected_slots']}, aborted {s['aborted']}, min margin "
          f"{s['min_margin_usd']}; identical {checks['identical']['ok']}, log {log_check['ok']}, pilot "
          f"{None if checks['pilot'] is None else checks['pilot']['ok']}; {man['wall_s']:.1f} s, "
          f"{man['peak_rss_mb']:.0f} MB; wrote {out / RUN_FILE}, {out / MANIFEST_FILE}", flush=True)
    return 0 if checks["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
