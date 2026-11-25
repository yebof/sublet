"""A stand-in e7b analysis at the scale of the registered runs, for the layout tests of figs/supp/sf_cap.py
(design/ms8/plan.md D2, W). **Its numbers are made up from the reduced fixture tree by a seeded perturbation and exist
only in the tests: never results, never written into the repository.**

    standin_root(dst) -> dst          # writes dst/code/sim/out/e7b/analysis.json

The fixture tree (inputs/, development week 101) gives each tag's r0 per part, point and lender mode (the analysis's
runs; a cell it lacks takes the tag's r0 under the same lender in part week, else STANDIN_R0). The stand-in writes the
six summaries that e7b_analysis.py reads in the shape of the registered runs (part week: the seven caps under the
thirteen lenders on weeks 301-316, Sublet and A9 under L-tr; the confirmation's part main and E7r's part eval for
Sublet, A9, BL1 and BL1-GP; part sens: the caps, BL1 and BL1-GP at the five points under L-tr on weeks 301-304 and the
five stress lenders on 301-302, Sublet and A9 at slow1's stress cells and fee16's identity cells; S1 v2's sweep and w0
for Sublet and A9), each value times a seeded week factor and a seeded run factor, with the all-fallback bill and B(T)
one per cell. A seeded share of the runs of the caps at X = B(t) under a stress lender or at fee16 is set above the
bound (a positive run-time excess), so that the figure's panel (b) has runs on both sides of it; Sublet stays below its
bound. The summaries go through the frozen analysis (sublet.experiments.e7b_analysis.analysis), so the stand-in has the
real analysis's structure.

    standin_root(dst, frozen=<folder>)   # the same, with the four frozen summaries read from <folder>

With `frozen` (a folder holding sublet_v2/main/, e7r/eval/ and s1v2/sweep/, s1v2/w0/ summaries; the tests pass the
repository's code/sim/out/), the stand-in reads the real frozen summaries instead of making them up: their runs of
Sublet, A9, BL1 and BL1-GP enter the analysis unchanged, each cell's all-fallback bill and B(T) are those of the real
frozen Sublet run of that cell (made up where it has none), and the stand-in's reruns of Sublet and A9 take the frozen
r0 of their cell, so the identity holds. The caps' runs stay made up.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FIX = HERE / "inputs" / "code" / "sim" / "out" / "e7b" / "analysis.json"
WEEKS = tuple(range(301, 317))
SENS_WEEKS = (301, 302, 303, 304)
SENS_STRESS_WEEKS = (301, 302)
POINTS = ("fee4", "fee8", "fee16", "slow1", "scen_cold_wan_1gbps")
SEED = 20261124
STANDIN_R0 = 0.9
ABOVE_SHARE = 0.12


def _frozen_cells(fz: dict) -> tuple[dict, dict]:
    """From the real frozen summaries: {(part, point, mode, c): (FB, B)} of the guarded Sublet runs and
    {(part, point, mode, c, tag): r0} of every run of Sublet and A9."""
    cells, r0s = {}, {}
    for src, part in (("main", "week"), ("eval", "week"), ("sweep", "sens"), ("w0", "sens")):
        for r in (fz.get(src) or {}).get("runs") or []:
            if str(r.get("seed", 0)) != "0" or r.get("status") != "ok" or r.get("c") is None:
                continue
            point = r.get("point") if part == "sens" else None
            k = (part, point, r["mode"], int(r["c"]))
            g = r.get("guard") or {}
            if r.get("tag") == "Sublet" and g.get("B_T") is not None and r.get("bl0a_usd") is not None:
                cells.setdefault(k, (float(r["bl0a_usd"]), float(g["B_T"])))
            if r.get("tag") in ("Sublet", "A9") and r.get("r0") is not None:
                r0s.setdefault(k + (r["tag"],), float(r["r0"]))
    return cells, r0s


def standin_inputs(seed: int = SEED, frozen: Path | None = None) -> dict:
    from sublet.experiments import e7b_analysis as ea

    fz = {}
    if frozen is not None:
        fs = ea.files(Path(frozen).parent, Path(frozen))
        fz = {k: json.loads(fs[k].read_text()) for k in ("main", "eval", "sweep", "w0")}
    real_cell, real_r0 = _frozen_cells(fz)

    rng = np.random.default_rng(seed)
    a = json.loads(FIX.read_text())
    base = {}
    for r in a["runs"]:
        if r.get("r0") is not None:
            base[(r["part"], r["point"], r["mode"], r["tag"])] = float(r["r0"])
    fb0 = {}
    for r in a["runs"]:
        if r.get("FB") is not None and r.get("B") is not None:
            fb0.setdefault((r["part"], r["point"], r["mode"]), (float(r["FB"]), float(r["B"])))
    fb_any = next(iter(fb0.values()), (1000.0, 100.0))
    modes = ("L-tr",) + ea.STRESS_MODES + ("L-hon",) + ea.NEW_MODES
    wf = {w: 1.0 + 0.08 * float(rng.standard_normal()) for w in WEEKS}

    def r0_of(part, point, mode, tag):
        for k in ((part, point, mode, tag), ("week", "default", mode, tag), ("week", "default", "L-tr", tag)):
            if k in base:
                return base[k]
        return STANDIN_R0

    cell_cache: dict = {}

    def cell(part, point, mode, c):
        k = (part, point, mode, c)
        real = real_cell.get((part, point, mode, c))
        if k not in cell_cache and real is not None:
            cell_cache[k] = real
        if k not in cell_cache:
            fb, b = fb0.get((part, point, mode)) or fb0.get(("week", "default", mode)) or fb_any
            f = wf[c] * (1.0 + 0.03 * float(rng.standard_normal()))
            cell_cache[k] = (fb * f, b * f)
        return cell_cache[k]

    runs_cache: dict = {}

    def row(part, point, mode, c, tag, *, guard=False, bound=False, cap=None):
        fb, b = cell(part, point, mode, c)
        key = (part, point, mode, c, tag)
        if key not in runs_cache:
            r0 = r0_of(part, point, mode, tag) * wf[c] ** 0.3 * (1.0 + 0.04 * float(rng.standard_normal()))
            above = (cap is not None and tag in ea.B_CAPS and (mode in ea.W0PLUS_MODES or point == "fee16")
                     and rng.random() < ABOVE_SHARE)
            if above:
                r0 = max(r0, (fb + b) / fb * (1.0 + 0.2 * float(rng.random())))
            if tag == "Sublet":
                r0 = min(r0, (fb + b) / fb - 0.01)
            if (part, point, mode, c, tag) in real_r0:
                r0 = real_r0[(part, point, mode, c, tag)]          # a rerun of a real frozen cell: its r0
            rt = (r0 * fb - fb - b) * (0.5 + 0.5 * float(rng.random())) if above else -float(rng.uniform(0.1, 2.0))
            runs_cache[key] = (r0, rt)
        r0, rt = runs_cache[key]
        r = {"tag": tag, "mode": mode, "c": c, "cell": str(c) if point is None else f"{point}:{c}", "seed": 0,
             "status": "ok", "r0": r0, "ALG": r0 * fb, "bl0a_usd": fb}
        if point is not None:
            r["point"] = point
        if guard:
            r["guard"] = {"B_T": b, "held": True, "env_ok": True, "env_max_excess_usd": -float(rng.uniform(0.1, 2.0)),
                          "s_fb_all": True}
        if bound:
            r["bound"] = {"B_T": b, "tol_usd": 1e-6, "runtime_max_excess_usd": rt, "runtime_max_slot": 40,
                          "n_slots_above": 5 if rt > 0 else 0, "fb_equal_bl0a": True}
        if cap is not None:
            binds = int(rng.integers(0, 50))
            r["cap"] = {"X": cap["X"], "count": cap["count"], "on_bind": cap["on_bind"], "bind_slots": binds,
                        "first_bind": 30 if binds else None,
                        "latch_t": (30 if binds else None) if cap["on_bind"] == "latch" else None,
                        "X_T": b if cap["X"] == "lb" else 0.0, "B_T": b, "FB_T": fb, "fb_equal_bound": True,
                        "X_equal_B": True if cap["X"] == "lb" else None, "B_series_equal_bound": True}
        return r

    from sublet.experiments import e7b_tags as bt
    capp = {t: bt.TAGS[t].params for t in ea.CAP_TAGS}
    week = {"meta": {"reduced": False, "git_revision": "s" * 40}, "runs": [
        row("week", None, m, c, t, bound=True, cap=capp[t]) for t in ea.CAP_TAGS for m in modes for c in WEEKS]
        + [row("week", None, "L-tr", c, t, guard=t == "Sublet", bound=True) for t in ("Sublet", "A9") for c in WEEKS]}
    main = {"meta": {"git_revision": "m" * 40}, "runs": [
        row("week", None, m, c, t, guard=t in ("Sublet", "BL1-GP")) for t in ea.FROZEN_TAGS for m in ea.CONF_MODES
        for c in WEEKS]}
    ev = {"meta": {"git_revision": "e" * 40}, "runs": [
        row("week", None, m, c, t, guard=t in ("Sublet", "BL1-GP")) for t in ea.FROZEN_TAGS for m in ea.NEW_MODES
        for c in WEEKS]}
    sens_rows, sweep_rows, w0_rows = [], [], []
    for p in POINTS:
        for c in SENS_WEEKS:
            ms = ("L-tr",) + (ea.STRESS_MODES if c in SENS_STRESS_WEEKS else ())
            for m in ms:
                for t in ea.CAP_TAGS:
                    sens_rows.append(row("sens", p, m, c, t, bound=True, cap=capp[t]))
                for t in ("BL1", "BL1-GP"):
                    sens_rows.append(row("sens", p, m, c, t, guard=t == "BL1-GP", bound=True))
                for t in ("Sublet", "A9"):
                    own = (p == "slow1" and m in ea.STRESS_MODES) or (p == "fee16" and (m, c) in
                                                                       (("L-tr", 301), ("L-eg", 301), ("L-eg", 302)))
                    if own:
                        sens_rows.append(row("sens", p, m, c, t, guard=t == "Sublet", bound=True))
                    if not (p == "slow1" and m in ea.STRESS_MODES):
                        (sweep_rows if m == "L-tr" else w0_rows).append(row("sens", p, m, c, t, guard=t == "Sublet"))
    inp = {"week": week, "sens": {"meta": {"reduced": False}, "runs": sens_rows}, "main": main, "eval": ev,
           "sweep": {"meta": {}, "runs": sweep_rows}, "w0": {"meta": {}, "runs": w0_rows}}
    inp.update(fz)                                       # the real frozen summaries, when given
    inp["sha256"] = {k: "0" * 64 for k in inp}
    inp["paths"] = {k: f"standin/{k}" for k in inp if k != "sha256"}
    return inp


def standin_root(dst: Path, seed: int = SEED, frozen: Path | None = None) -> Path:
    from sublet.experiments import e7b_analysis as ea

    an = ea.analysis(standin_inputs(seed, frozen))
    an["meta"]["standin_note"] = "made-up stand-in at the registered scale (tests only), never a result"
    p = Path(dst) / "code" / "sim" / "out" / "e7b" / "analysis.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(an, indent=1, allow_nan=False) + "\n")
    return Path(dst)
