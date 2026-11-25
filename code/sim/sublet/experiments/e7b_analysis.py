"""E7b's analysis: budget caps against Sublet (design/ms8/plan.md D2, X6, D4; design/ms8/scout_x6_budget_cap.md §3).
Its sha256 is recorded in design/ms8/registration.md before the runs, and every e7b part refuses to start unless the
file still has it (e7b.check_registration); so every rule below is fixed and deterministic, and the file depends only on
the summaries it reads and ms3_common's file helpers. Descriptive only: no p-value is computed (D4; the weeks are
rotations of one series). Every reading below is reported whatever its sign.

Inputs (<root> as ms3_common.ms3_root; <frozen> default <root>/out, read only, each file's sha256 recorded):
  week   <root>/out/e7b/week/summary.json      the seven caps on weeks 301-316 x 13 modes; Sublet and A9 under L-tr
  sens   <root>/out/e7b/sens/summary.json      the caps, BL1 and BL1-GP at the five points; Sublet and A9 at cells
                                               S1 v2 lacks (slow1 under stress) and at fee16's identity cells
  main   <frozen>/sublet_v2/main/summary.json  Sublet, A9, BL1, BL1-GP: the confirmation's seven modes, weeks 301-316
  eval   <frozen>/e7r/eval/summary.json        the same tags under E7r's NEW_MODES (and L-tr, not used: main's first)
  sweep  <frozen>/s1v2/sweep/summary.json      Sublet and A9 at the points under L-tr, weeks 301-304
  w0     <frozen>/s1v2/w0/summary.json         Sublet and A9 at the W0 points under the five stress modes, 301-302
A missing input makes the command exit 2. Output: <root>/out/e7b/analysis.json and analysis.md.

Rules (policy seed 0; r0 the overflow cost over BL0a; FB(T) = BL0a, the all-fallback cost):
  runs     one record per (part, point, mode, week, tag): part 'week' (point 'default') or 'sens'. Sources, in order of
           precedence for r0, ALG and BL0a: the frozen summaries (main before eval; sweep and w0 for the sens points),
           then E7b's own runs; an E7b rerun of a frozen cell (Sublet and A9 under L-tr, part sens' fee16 cells) adds its
           per-slot fields and is compared with the frozen run (identity). B(T), Sublet's allowance min{W_k, LB'} at the
           horizon, depends only on the instance: an E7b run's bound.B_T, else the B_T of a guarded frozen run of the
           same cell.
  excess   final excess ALG(T) - FB(T) - B(T), in USD and over FB(T); 'above' iff it exceeds the run's tolerance
           (E7b's bound.tol_usd; for a frozen run GUARD_TOL max(1, |FB + B|) + CERT_TOL max(1, ALG), the same rule);
           run-time excess max_t ALG(t) - FB(t) - B(t) from E7b's per-slot series (bound), 'runtime_above' iff some slot
           exceeds the tolerance there; for a frozen guarded run (Sublet, BL1-GP) the envelope max_t ALG(t) + R(t) -
           (C_S(t) + B(t)), an upper bound on the run-time excess when the safe expert followed all-fallback (s_fb_all),
           labeled 'envelope'; none for a frozen unguarded run.
  W0, W0+  per (part, point, week, tag): W0 = the largest r0 over the five stress modes (L-eg, L-ss, L-iid-0.05,
           L-iid-0.2, L-co), W0+ = the largest over those and NEW_MODES (part week); null while a run is missing.
  per tag  per part (and point) and mode: runs, median, min and max r0, runs above the bound, the largest final and
           run-time excess over FB(T), and for the caps the binds and the latch slots.
  margins  delta = metric(tag) - metric(reference) per week (positive: the reference costs less; a missing run is a
           loss for the reference, counted in 'missing', so losses_with_missing = losses + missing), with n, wins
           (delta > 0), ties (= 0), losses (< 0), missing, losses_with_missing, median, min and max over the weeks with
           a value; metrics r0 per mode, r0_tr (L-tr), W0 and W0+ (part week);
           references: Sublet for every cap, BL1-GP also for the GR caps; part sens per point.
  inner    per cap and cell: r0(cap) - r0(inner) (A9 or BL1) and the share of the inner's saving the cap keeps,
           (1 - r0(cap)) / (1 - r0(inner)) where 1 - r0(inner) > 0; median, min and max, per part and mode class.
  Sublet   its certificate rows: per part, runs, certificates held, envelope violations, runs above the bound, the
           largest final excess and envelope.
  identity E7b's reruns against the frozen runs: r0 equal as floats, per cell; holds iff every rerun has a frozen
           counterpart and equals it.
  checks   over E7b's own runs, per part: the runs whose FB(T) equals the cell's BL0a (bound.fb_equal_bl0a), and over
           its cap runs the cap's FB(T) equal to the bound's (cap.fb_equal_bound), X(T) = B(T) at X = B(t)
           (cap.X_equal_B) and the cap's B series equal to the bound's (cap.B_series_equal_bound); each as counts of
           true, false and missing, and 'holds' iff none is false or missing.
Readings (pre-stated, design/ms8/scout_x6_budget_cap.md §3; each reported whatever its sign):
  R1 (soundness matters): holds iff some run of a cap at X = B(t) (B_CAPS) under a stress mode (W0+'s eleven) in part
     week, or at point fee16 in part sens, lands above the bound with a positive run-time excess, while no Sublet run
     lands above the bound or violates its envelope. Reported: the runs, per tag the count and the largest excesses.
  R2 (an allowance-free cap gives up savings): holds iff the median r0 of CR-cap-0 over part week's runs under the
     five stress modes is at least 0.95 while Sublet's median over the same cells is at most 0.79.
  R3 (price of soundness): every cell where a cap's r0 is below Sublet's, with the margin, and counts per tag.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import statistics
import sys
from pathlib import Path
from typing import Optional

from . import ms3_common as mc

EXP = "e7b"
SUBLET = "Sublet"
TRACE_MODE = "L-tr"
STRESS_MODES = ("L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co")
NEW_MODES = ("L-iid-0.0005", "L-iid-0.002", "L-iid-0.0124", "L-co-reg-0.5", "L-co-reg-1", "L-pk")
CONF_MODES = (TRACE_MODE,) + STRESS_MODES + ("L-hon",)
W0PLUS_MODES = STRESS_MODES + NEW_MODES
CAP_TAGS = ("CR-cap-B", "CR-cap-0", "CR-cap-5", "CR-cap-B-latch", "CR-cap-B-slot", "GR-cap-B", "GR-cap-0")
B_CAPS = ("CR-cap-B", "CR-cap-B-latch", "CR-cap-B-slot", "GR-cap-B")
INNER = {t: ("BL1" if t.startswith("GR-") else "A9") for t in CAP_TAGS}
REFERENCES = {t: ((SUBLET, "BL1-GP") if t.startswith("GR-") else (SUBLET,)) for t in CAP_TAGS}
FROZEN_TAGS = (SUBLET, "A9", "BL1", "BL1-GP")
SENS_POINTS = ("fee4", "fee8", "fee16", "slow1", "scen_cold_wan_1gbps")
R1_POINTS = ("fee16",)
R2_CAP, R2_CAP_MIN, R2_SUBLET_MAX = "CR-cap-0", 0.95, 0.79
DEFAULT = "default"
SEED = "0"
GUARD_TOL = 1e-12                  # guard.GUARD_TOL (the envelope's tolerance, with CERT_TOL)
CERT_TOL = 1e-9                    # q44_study.CERT_TOL
REGISTRATION = "design/ms8/registration.md"
REG_SHA_RE = re.compile(r"^e7b_analysis_sha256:\s*([0-9a-f]{64})\s*$", re.MULTILINE)
SCRIPT = "code/sim/sublet/experiments/e7b_analysis.py"


# ---------------------------------------------------------------- inputs
def files(root: Path, frozen: Optional[Path] = None) -> dict:
    fz = Path(frozen) if frozen is not None else root / "out"
    e = root / "out" / EXP
    return {"week": e / "week" / "summary.json", "sens": e / "sens" / "summary.json",
            "main": fz / "sublet_v2" / "main" / "summary.json", "eval": fz / "e7r" / "eval" / "summary.json",
            "sweep": fz / "s1v2" / "sweep" / "summary.json", "w0": fz / "s1v2" / "w0" / "summary.json"}


def load(root: Path, frozen: Optional[Path] = None) -> dict:
    """The six summaries, their paths and sha256; FileNotFoundError naming every missing file."""
    fs = files(root, frozen)
    miss = [str(p) for p in fs.values() if not p.is_file()]
    if miss:
        raise FileNotFoundError(f"missing input(s): {miss}")
    out = {k: mc.read_json(p) for k, p in fs.items()}
    bad = [str(fs[k]) for k, v in out.items() if not isinstance(v, dict)]
    if bad:
        raise FileNotFoundError(f"unreadable input(s): {bad}")
    out["sha256"] = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in fs.items()}
    out["paths"] = {k: str(p) for k, p in fs.items()}
    return out


def registration(sha: str, repo: Optional[Path] = None) -> dict:
    """This file's sha256 against the line 'e7b_analysis_sha256: <64 hex>' of design/ms8/registration.md in the
    working tree of `repo` (default: the repository that holds this file)."""
    base = Path(repo) if repo is not None else Path(__file__).resolve().parents[4]
    f = base / REGISTRATION
    m = REG_SHA_RE.search(f.read_text(encoding="utf-8", errors="replace")) if f.is_file() else None
    want = m.group(1) if m else None
    return {"path": REGISTRATION, "exists": f.is_file(), "registered_sha256": want,
            "matches": want is not None and want == sha}


# ---------------------------------------------------------------- statistics
def _num(x) -> Optional[float]:
    return None if x is None else float(x)


def stats(xs) -> dict:
    v = [float(x) for x in xs if x is not None]
    if not v:
        return {"n": 0, "median": None, "min": None, "max": None}
    return {"n": len(v), "median": statistics.median(v), "min": min(v), "max": max(v)}


def margin_stats(deltas: dict) -> dict:
    """{week: delta or None} -> n, wins, ties, losses, missing, median, min, max (module docstring)."""
    v = [d for d in deltas.values() if d is not None]
    s = stats(v)
    return {"n": len(v), "wins": sum(1 for d in v if d > 0), "ties": sum(1 for d in v if d == 0),
            "losses": sum(1 for d in v if d < 0), "missing": sum(1 for d in deltas.values() if d is None),
            "losses_with_missing": sum(1 for d in v if d < 0) + sum(1 for d in deltas.values() if d is None),
            "median": s["median"], "min": s["min"], "max": s["max"], "deltas": dict(deltas)}


def tol_of(fb: float, b: float, alg: float) -> float:
    return GUARD_TOL * max(1.0, abs(fb + b)) + CERT_TOL * max(1.0, abs(alg))


# ---------------------------------------------------------------- run records
def _rows(s: Optional[dict]) -> list:
    return [r for r in (s or {}).get("runs") or [] if str(r.get("seed", 0)) == SEED and r.get("status") == "ok"]


def _week(r: dict) -> str:
    c = r.get("c")
    if c is None:
        c = str(r.get("cell", "")).split(":")[-1]
    return mc.num_key(int(c))


def collect_runs(inp: dict) -> tuple[dict, list]:
    """({(part, point, mode, week, tag): record}, identity rows) by the module docstring's rule 'runs'."""
    recs: dict = {}
    frozen = []                                          # (key, row, source) in precedence order
    for src in ("main", "eval"):
        for r in _rows(inp.get(src)):
            if r.get("tag") in FROZEN_TAGS and (src == "main" or r.get("mode") in NEW_MODES):
                frozen.append((("week", DEFAULT, r["mode"], _week(r), r["tag"]), r, src))
    for src in ("sweep", "w0"):
        for r in _rows(inp.get(src)):
            if r.get("tag") in FROZEN_TAGS and r.get("point") in SENS_POINTS:
                frozen.append((("sens", r["point"], r["mode"], _week(r), r["tag"]), r, src))
    for key, r, src in frozen:
        if key in recs:
            continue
        g = r.get("guard") or {}
        recs[key] = {"source": src, "r0": _num(r.get("r0")), "ALG": _num(r.get("ALG")), "FB": _num(r.get("bl0a_usd")),
                     "B": _num(g.get("B_T")), "guarded": bool(g), "held": g.get("held"), "env_ok": g.get("env_ok"),
                     "envelope_usd": _num(g.get("env_max_excess_usd")), "s_fb_all": g.get("s_fb_all"),
                     "rerun": None}
    ident = []
    for part in ("week", "sens"):
        for r in _rows(inp.get(part)):
            point = r.get("point") or DEFAULT
            key = (part, point, r["mode"], _week(r), r["tag"])
            b, cap, g = r.get("bound") or {}, r.get("cap") or {}, r.get("guard") or {}
            own = {"r0": _num(r.get("r0")), "ALG": _num(r.get("ALG")), "FB": _num(r.get("bl0a_usd")),
                   "B": _num(b.get("B_T")), "tol_usd": _num(b.get("tol_usd")),
                   "runtime_usd": _num(b.get("runtime_max_excess_usd")), "runtime_slot": b.get("runtime_max_slot"),
                   "n_slots_above": b.get("n_slots_above"), "guarded": bool(g), "held": g.get("held"),
                   "env_ok": g.get("env_ok"), "envelope_usd": _num(g.get("env_max_excess_usd")),
                   "s_fb_all": g.get("s_fb_all"), "cap": cap or None}
            if key in recs:
                f = recs[key]
                ident.append({"part": part, "point": point, "mode": r["mode"], "week": key[3], "tag": r["tag"],
                              "frozen_source": f["source"], "r0": own["r0"], "r0_frozen": f["r0"],
                              "equal": own["r0"] is not None and own["r0"] == f["r0"],
                              "diff": None if own["r0"] is None or f["r0"] is None else own["r0"] - f["r0"]})
                f["rerun"] = own
                for k in ("tol_usd", "runtime_usd", "runtime_slot", "n_slots_above"):
                    f[k] = own[k]
                if f.get("B") is None:
                    f["B"] = own["B"]
                continue
            recs[key] = {"source": EXP, **own, "rerun": None}
    # B(T) of the cell for the records without one (frozen unguarded runs)
    cellB: dict = {}
    for (part, point, mode, week, _t), x in recs.items():
        if x.get("B") is not None:
            cellB.setdefault((part, point, mode, week), x["B"])
    for (part, point, mode, week, _t), x in recs.items():
        if x.get("B") is None:
            x["B"] = cellB.get((part, point, mode, week))
            x["B_from_cell"] = x["B"] is not None
    for x in recs.values():
        excess(x)
    return recs, ident


def excess(x: dict) -> None:
    """The record's final excess, 'above', and run-time excess with its label (module docstring, 'excess')."""
    alg, fb, b = x.get("ALG"), x.get("FB"), x.get("B")
    if alg is None or fb is None or b is None:
        x.update(final_usd=None, final_rel=None, above=None)
    else:
        fin = alg - fb - b
        tol = x.get("tol_usd") if x.get("tol_usd") is not None else tol_of(fb, b, alg)
        x.update(final_usd=fin, final_rel=fin / fb if fb > 0 else None, above=bool(fin > tol), tol_used=tol)
    if x.get("runtime_usd") is not None:
        x["runtime_label"] = "series"
        x["runtime_rel"] = x["runtime_usd"] / fb if fb else None
        x["runtime_above"] = bool((x.get("n_slots_above") or 0) > 0)
    elif x.get("envelope_usd") is not None:
        x["runtime_label"] = "envelope"
        x["runtime_usd"] = x["envelope_usd"]
        x["runtime_rel"] = x["envelope_usd"] / fb if fb else None
        x["runtime_above"] = x.get("env_ok") is False
    else:
        x.update(runtime_label=None, runtime_rel=None, runtime_above=None)


# ---------------------------------------------------------------- tables
def cells_of(recs: dict, part: str) -> dict:
    """{point: sorted weeks} of a part."""
    out: dict = {}
    for (p, point, _m, week, _t) in recs:
        if p == part:
            out.setdefault(point, set()).add(week)
    return {k: sorted(v, key=int) for k, v in sorted(out.items())}


def r0(recs: dict, part: str, point: str, mode: str, week: str, tag: str) -> Optional[float]:
    x = recs.get((part, point, mode, week, tag))
    return None if x is None else x.get("r0")


def w_metric(recs: dict, part: str, point: str, week: str, tag: str, modes) -> Optional[float]:
    v = [r0(recs, part, point, m, week, tag) for m in modes]
    return None if any(x is None for x in v) else max(v)


def metric(recs: dict, part: str, point: str, week: str, tag: str, name: str) -> Optional[float]:
    if name == "r0_tr":
        return r0(recs, part, point, TRACE_MODE, week, tag)
    if name == "W0":
        return w_metric(recs, part, point, week, tag, STRESS_MODES)
    if name == "W0plus":
        return w_metric(recs, part, point, week, tag, W0PLUS_MODES)
    if name.startswith("r0:"):
        return r0(recs, part, point, name[3:], week, tag)
    raise ValueError(name)


def modes_of(recs: dict, part: str, point: str, tag: str) -> list:
    ms = {m for (p, pt, m, _w, t) in recs if p == part and pt == point and t == tag}
    order = CONF_MODES + NEW_MODES
    return [m for m in order if m in ms] + sorted(ms - set(order))


def per_tag(recs: dict) -> dict:
    """{part: {point: {tag: {mode: row}}}} (module docstring, 'per tag')."""
    out: dict = {}
    for (part, point, mode, week, tag), x in recs.items():
        out.setdefault(part, {}).setdefault(point, {}).setdefault(tag, {}).setdefault(mode, []).append(x)
    res: dict = {}
    for part, by_pt in out.items():
        for point, by_t in by_pt.items():
            for tag, by_m in by_t.items():
                for mode, xs in by_m.items():
                    caps = [x.get("cap") or (x.get("rerun") or {}).get("cap") or {} for x in xs]
                    row = {"runs": len(xs), "r0": stats(x.get("r0") for x in xs),
                           "above": sum(1 for x in xs if x.get("above")),
                           "final_rel_max": stats(x.get("final_rel") for x in xs)["max"],
                           "runtime_rel_max": stats(x.get("runtime_rel") for x in xs)["max"],
                           "runtime_labels": sorted({str(x.get("runtime_label")) for x in xs})}
                    if any(caps):
                        row["bind_slots"] = stats(c.get("bind_slots") for c in caps)
                        row["latched_runs"] = sum(1 for c in caps if c.get("latch_t") is not None)
                    res.setdefault(part, {}).setdefault(point, {}).setdefault(tag, {})[mode] = row
    return res


def w_tables(recs: dict) -> dict:
    """{part: {point: {tag: {'W0': {week: v}, 'W0plus': ...}}}}."""
    out: dict = {}
    for part in ("week", "sens"):
        for point, weeks in cells_of(recs, part).items():
            tags = sorted({t for (p, pt, _m, _w, t) in recs if p == part and pt == point})
            for t in tags:
                row = {"W0": {w: metric(recs, part, point, w, t, "W0") for w in weeks}}
                if part == "week":
                    row["W0plus"] = {w: metric(recs, part, point, w, t, "W0plus") for w in weeks}
                row["W0_stats"] = stats(row["W0"].values())
                if "W0plus" in row:
                    row["W0plus_stats"] = stats(row["W0plus"].values())
                out.setdefault(part, {}).setdefault(point, {})[t] = row
    return out


def margins(recs: dict) -> dict:
    """{part: {point: {cap: {reference: {metric: margin_stats}}}}} (module docstring, 'margins')."""
    out: dict = {}
    for part in ("week", "sens"):
        for point, weeks in cells_of(recs, part).items():
            for cap in CAP_TAGS:
                if not any((part, point, m, w, cap) in recs for m in CONF_MODES + NEW_MODES for w in weeks):
                    continue
                ms = modes_of(recs, part, point, cap)
                names = ["r0_tr", "W0"] + (["W0plus"] if part == "week" else []) + [f"r0:{m}" for m in ms]
                for ref in REFERENCES[cap]:
                    res = {}
                    for name in names:
                        # a mode's weeks are those the cap ran there (part sens: the stress modes on 301-302 only)
                        mw = [w for w in weeks if any((part, point, m, w, cap) in recs for m in
                                                      ((name[3:],) if name.startswith("r0:") else
                                                       ((TRACE_MODE,) if name == "r0_tr" else STRESS_MODES)))]
                        d = {}
                        for w in mw:
                            a, b = metric(recs, part, point, w, cap, name), metric(recs, part, point, w, ref, name)
                            d[w] = None if a is None or b is None else a - b
                        res[name] = margin_stats(d)
                    out.setdefault(part, {}).setdefault(point, {}).setdefault(cap, {})[ref] = res
    return out


def inner_kept(recs: dict) -> dict:
    """{part: {point: {cap: {'all' | 'stress' | 'trace': {delta_r0, kept_share}}}}} (module docstring, 'inner')."""
    out: dict = {}
    for (part, point, mode, week, tag), x in recs.items():
        if tag not in CAP_TAGS:
            continue
        y = recs.get((part, point, mode, week, INNER[tag]))
        if y is None or x.get("r0") is None or y.get("r0") is None:
            continue
        cls = "trace" if mode == TRACE_MODE else ("stress" if mode in STRESS_MODES else "other")
        d = x["r0"] - y["r0"]
        sh = (1.0 - x["r0"]) / (1.0 - y["r0"]) if 1.0 - y["r0"] > 0 else None
        for c in ("all", cls):
            o = out.setdefault(part, {}).setdefault(point, {}).setdefault(tag, {}).setdefault(c, {"d": [], "s": []})
            o["d"].append(d)
            o["s"].append(sh)
    res: dict = {}
    for part, a in out.items():
        for point, b in a.items():
            for tag, c in b.items():
                for cls, v in c.items():
                    res.setdefault(part, {}).setdefault(point, {}).setdefault(tag, {})[cls] = {
                        "inner": INNER[tag], "r0_minus_inner": stats(v["d"]), "kept_share": stats(v["s"]),
                        "n_inner_saving_nonpositive": sum(1 for s in v["s"] if s is None)}
    return res


def sublet_rows(recs: dict) -> dict:
    """Sublet's certificate rows per part (module docstring, 'Sublet')."""
    out = {}
    for part in ("week", "sens"):
        xs = [(k, x) for k, x in recs.items() if k[0] == part and k[4] == SUBLET]
        out[part] = {"runs": len(xs), "held": sum(1 for _k, x in xs if x.get("held") is True),
                     "envelope_violations": sum(1 for _k, x in xs if x.get("env_ok") is False),
                     "above": sum(1 for _k, x in xs if x.get("above")),
                     "runtime_above": sum(1 for _k, x in xs if x.get("runtime_above")),
                     "final_rel_max": stats(x.get("final_rel") for _k, x in xs)["max"],
                     "final_usd_max": stats(x.get("final_usd") for _k, x in xs)["max"],
                     "envelope_usd_max": stats(x.get("envelope_usd") for _k, x in xs)["max"],
                     "s_fb_all": sum(1 for _k, x in xs if x.get("s_fb_all") is True)}
    return out


def identity(ident: list, recs: dict) -> dict:
    """E7b's reruns of frozen cells (module docstring, 'identity'): every Sublet and A9 rerun has a frozen counterpart
    and equals it."""
    reruns = [k for k, x in recs.items() if x.get("source") == EXP and k[4] in (SUBLET, "A9")
              and not (k[0] == "sens" and k[1] == "slow1" and k[2] in STRESS_MODES)]
    n_eq = sum(1 for r in ident if r["equal"])
    diffs = [abs(r["diff"]) for r in ident if r["diff"] is not None]
    return {"holds": bool(ident) and n_eq == len(ident) and not reruns, "n_pairs": len(ident), "n_equal": n_eq,
            "max_abs_diff": max(diffs) if diffs else None,
            "reruns_without_frozen": [list(k) for k in reruns],
            "rule": "r0 of each E7b rerun equal as a float to the frozen run of the same cell", "rows": ident}


def _count(vals: list) -> dict:
    return {"true": sum(1 for v in vals if v is True), "false": sum(1 for v in vals if v is False),
            "missing": sum(1 for v in vals if v is None)}


def run_checks(inp: dict) -> dict:
    """The per-run checks of E7b's own runs (module docstring, 'checks')."""
    out = {}
    for part in ("week", "sens"):
        rows = _rows(inp.get(part))
        caps = [(r["tag"], r.get("cap") or {}) for r in rows if r.get("tag") in CAP_TAGS]
        res = {"runs": len(rows), "cap_runs": len(caps),
               "fb_equal_bl0a": _count([(r.get("bound") or {}).get("fb_equal_bl0a") for r in rows]),
               "cap_fb_equal_bound": _count([c.get("fb_equal_bound") for _t, c in caps]),
               "cap_X_equal_B": _count([c.get("X_equal_B") for t, c in caps if t in B_CAPS]),
               "cap_B_series_equal_bound": _count([c.get("B_series_equal_bound") for _t, c in caps])}
        res["holds"] = all(v["false"] == 0 and v["missing"] == 0 for k, v in res.items() if isinstance(v, dict))
        out[part] = res
    return out


def _is_r1_cell(part: str, point: str, mode: str) -> bool:
    return (part == "week" and mode in W0PLUS_MODES) or (part == "sens" and point in R1_POINTS)


def readings(recs: dict) -> dict:
    r1_runs = []
    for (part, point, mode, week, tag), x in sorted(recs.items()):
        if tag in B_CAPS and _is_r1_cell(part, point, mode) and x.get("above") and x.get("runtime_above"):
            r1_runs.append({"part": part, "point": point, "mode": mode, "week": week, "tag": tag, "r0": x["r0"],
                            "final_rel": x.get("final_rel"), "final_usd": x.get("final_usd"),
                            "runtime_rel": x.get("runtime_rel"), "runtime_usd": x.get("runtime_usd")})
    sub = [x for k, x in recs.items() if k[4] == SUBLET]
    sub_bad = [list(k) for k, x in recs.items() if k[4] == SUBLET and (x.get("above") or x.get("env_ok") is False
                                                                      or x.get("runtime_above"))]
    by_tag = {}
    for t in B_CAPS:
        xs = [x for x in r1_runs if x["tag"] == t]
        allx = [x for k, x in recs.items() if k[4] == t and _is_r1_cell(k[0], k[1], k[2])]
        by_tag[t] = {"runs_in_scope": len(allx), "above_with_runtime": len(xs),
                     "final_rel_max": stats(x.get("final_rel") for x in allx)["max"],
                     "runtime_rel_max": stats(x.get("runtime_rel") for x in allx)["max"]}
    R1 = {"claim": "some X = B(t) cap lands above the bound with a positive run-time excess in a stress or rho = 16 run, "
                   "while no Sublet run does", "holds": bool(r1_runs) and not sub_bad and bool(sub),
          "n_runs": len(r1_runs), "runs": r1_runs, "by_tag": by_tag, "sublet_runs": len(sub),
          "sublet_violations": sub_bad}
    cells = [k for k in recs if k[0] == "week" and k[2] in STRESS_MODES and k[4] == R2_CAP]
    cap_v = [recs[k]["r0"] for k in cells]
    sub_v = [r0(recs, k[0], k[1], k[2], k[3], SUBLET) for k in cells]
    mc_, ms_ = stats(cap_v)["median"], stats(sub_v)["median"]
    R2 = {"claim": f"median r0 of {R2_CAP} under the stress modes >= {R2_CAP_MIN} while Sublet's <= {R2_SUBLET_MAX}",
          "cap_median": mc_, "sublet_median": ms_, "n_cells": len(cells),
          "n_sublet_missing": sum(1 for v in sub_v if v is None),
          "holds": None if mc_ is None or ms_ is None else bool(mc_ >= R2_CAP_MIN and ms_ <= R2_SUBLET_MAX),
          "per_mode": {m: {"cap": stats(recs[k]["r0"] for k in cells if k[2] == m)["median"],
                           "sublet": stats(r0(recs, *k[:4], SUBLET) for k in cells if k[2] == m)["median"]}
                       for m in STRESS_MODES}}
    beats = []
    for (part, point, mode, week, tag), x in sorted(recs.items()):
        if tag not in CAP_TAGS:
            continue
        s = r0(recs, part, point, mode, week, SUBLET)
        if x.get("r0") is not None and s is not None and x["r0"] < s:
            beats.append({"part": part, "point": point, "mode": mode, "week": week, "tag": tag, "r0": x["r0"],
                          "sublet_r0": s, "margin": s - x["r0"]})
    counts: dict = {}
    for b in beats:
        c = counts.setdefault(b["tag"], {"cells": 0, "margin_max": None})
        c["cells"] += 1
        c["margin_max"] = b["margin"] if c["margin_max"] is None else max(c["margin_max"], b["margin"])
    R3 = {"claim": "every cell where a cap's r0 is below Sublet's", "n_cells": len(beats), "by_tag": counts,
          "cells": beats}
    return {"R1": R1, "R2": R2, "R3": R3}


def analysis(inp: dict, repo: Optional[Path] = None) -> dict:
    recs, ident = collect_runs(inp)
    sha = hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()
    red = {k: bool(((inp.get(k) or {}).get("meta") or {}).get("reduced")) for k in ("week", "sens")}
    runs = [{"part": k[0], "point": k[1], "mode": k[2], "week": k[3], "tag": k[4],
             **{f: x.get(f) for f in ("source", "r0", "ALG", "FB", "B", "B_from_cell", "final_usd", "final_rel",
                                      "above", "runtime_label", "runtime_usd", "runtime_rel", "runtime_above",
                                      "held", "env_ok")},
             "cap": x.get("cap") or (x.get("rerun") or {}).get("cap")} for k, x in sorted(recs.items())]
    return {"meta": {"exp": EXP, "spec": "design/ms8/plan.md D2, D4 (X6)", "script": SCRIPT, "analysis_sha256": sha,
                     "registration": registration(sha, repo), "inputs": inp["paths"], "inputs_sha256": inp["sha256"],
                     "git_revision": mc.git_revision(), "written": mc._now(), "reduced": red,
                     "git_revisions": {k: ((inp.get(k) or {}).get("meta") or {}).get("git_revision")
                                       for k in ("week", "sens", "main", "eval", "sweep", "w0")},
                     "cap_tags": list(CAP_TAGS), "b_caps": list(B_CAPS), "inner": INNER,
                     "references": {k: list(v) for k, v in REFERENCES.items()}, "stress_modes": list(STRESS_MODES),
                     "w0plus_modes": list(W0PLUS_MODES), "sens_points": list(SENS_POINTS),
                     "cells": {p: cells_of(recs, p) for p in ("week", "sens")},
                     "note": "descriptive: margins are the tag minus the reference (positive: the reference costs "
                             "less; a missing run is a loss for the reference); no p-values (D4)"},
            "runs": runs, "per_tag": per_tag(recs), "W": w_tables(recs), "margins": margins(recs),
            "inner": inner_kept(recs), "sublet": sublet_rows(recs), "identity": identity(ident, recs),
            "checks": run_checks(inp), "readings": readings(recs)}


# ---------------------------------------------------------------- report
def _f(x, d: int = 4) -> str:
    return "-" if x is None else f"{x:.{d}f}"


def to_md(a: dict) -> str:
    m = a["meta"]
    lines = ["# E7b analysis: budget caps (design/ms8/plan.md D2, X6)", ""]
    if any(m["reduced"].values()):
        lines += ["Reduced run (development cell only): not a result.", ""]
    lines += [f"Registration: {m['registration']['path']} records {str(m['registration']['registered_sha256'])[:12]}, "
              f"this file {m['analysis_sha256'][:12]} (matches {m['registration']['matches']}). Margins are the tag "
              "minus the reference; positive means the reference costs less. No p-values.", ""]
    rd = a["readings"]
    lines += ["## Readings", "",
              f"- R1 ({rd['R1']['claim']}): holds {rd['R1']['holds']}; {rd['R1']['n_runs']} runs; Sublet violations "
              f"{len(rd['R1']['sublet_violations'])} of {rd['R1']['sublet_runs']} runs.",
              f"- R2 ({rd['R2']['claim']}): holds {rd['R2']['holds']}; median r0 {R2_CAP} {_f(rd['R2']['cap_median'])}, "
              f"Sublet {_f(rd['R2']['sublet_median'])} over {rd['R2']['n_cells']} cells.",
              f"- R3 ({rd['R3']['claim']}): {rd['R3']['n_cells']} cells; " +
              ", ".join(f"{t} {c['cells']} (max margin {_f(c['margin_max'])})" for t, c in rd['R3']['by_tag'].items()),
              ""]
    rows = [[t, x["runs_in_scope"], x["above_with_runtime"], _f(x["final_rel_max"], 5), _f(x["runtime_rel_max"], 5)]
            for t, x in rd["R1"]["by_tag"].items()]
    lines += ["### R1 by tag (scope: part week under the 11 stress modes of W0+, part sens at fee16)", "",
              mc.md_table(["tag", "runs", "above with run-time excess", "max final excess / FB",
                           "max run-time excess / FB"], rows), ""]
    for part, by_pt in a["per_tag"].items():
        for point, by_t in by_pt.items():
            rows = []
            for t, by_m in sorted(by_t.items()):
                for md, x in by_m.items():
                    rows.append([t, md, x["runs"], _f(x["r0"]["median"]), x["above"], _f(x["final_rel_max"], 5),
                                 _f(x["runtime_rel_max"], 5)])
            lines += [f"## Part {part}, point {point}: per tag and mode", "",
                      mc.md_table(["tag", "mode", "runs", "median r0", "above", "max final excess / FB",
                                   "max run-time excess / FB"], rows), ""]
    rows = []
    for part, by_pt in a["margins"].items():
        for point, by_c in by_pt.items():
            for cap, by_r in by_c.items():
                for ref, by_k in by_r.items():
                    for k in ("r0_tr", "W0", "W0plus"):
                        if k in by_k:
                            x = by_k[k]
                            rows.append([part, point, cap, ref, k, x["n"], x["wins"], x["ties"], x["losses"],
                                         x["missing"], x["losses_with_missing"], _f(x["median"]), _f(x["min"]),
                                         _f(x["max"])])
    lines += ["## Margins (tag minus reference, per week)", "",
              mc.md_table(["part", "point", "cap", "reference", "metric", "weeks", "wins", "ties", "losses", "missing",
                           "losses with missing", "median", "min", "max"], rows), ""]
    rows = []
    for part, by_pt in a["inner"].items():
        for point, by_c in by_pt.items():
            for cap, by_cls in by_c.items():
                for cls, x in by_cls.items():
                    rows.append([part, point, cap, cls, x["inner"], _f(x["r0_minus_inner"]["median"]),
                                 _f(x["kept_share"]["median"]), x["n_inner_saving_nonpositive"]])
    lines += ["## Against the inner policy alone", "",
              mc.md_table(["part", "point", "cap", "modes", "inner", "median r0 - inner", "median kept share",
                           "cells without inner saving"], rows), ""]
    rows = [[p, x["runs"], x["held"], x["envelope_violations"], x["above"], _f(x["final_usd_max"], 3),
             _f(x["envelope_usd_max"], 3)] for p, x in a["sublet"].items()]
    lines += ["## Sublet's certificate rows", "",
              mc.md_table(["part", "runs", "held", "envelope violations", "above bound", "max final excess (USD)",
                           "max envelope (USD)"], rows), ""]
    i = a["identity"]
    lines += ["## Identity with the frozen runs", "",
              f"- {i['n_equal']} of {i['n_pairs']} reruns equal (max |diff| {_f(i['max_abs_diff'], 12)}); reruns "
              f"without a frozen run {len(i['reruns_without_frozen'])}; holds {i['holds']}", ""]
    rows = []
    for part, x in a["checks"].items():
        for k in ("fb_equal_bl0a", "cap_fb_equal_bound", "cap_X_equal_B", "cap_B_series_equal_bound"):
            rows.append([part, k, x[k]["true"], x[k]["false"], x[k]["missing"], x["holds"]])
    lines += ["## Per-run checks of E7b's runs", "",
              mc.md_table(["part", "check", "true", "false", "missing", "part holds"], rows), ""]
    rows = [[c["part"], c["point"], c["mode"], c["week"], c["tag"], _f(c["r0"]), _f(c["sublet_r0"]), _f(c["margin"])]
            for c in rd["R3"]["cells"]]
    lines += ["## R3: every cell where a cap costs less than Sublet", "",
              mc.md_table(["part", "point", "mode", "week", "tag", "r0", "Sublet r0", "Sublet - cap"], rows), ""]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.e7b_analysis", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="folder whose out/e7b/ holds the parts (default MS3_ROOT or this "
                                                 "repository's code/sim)")
    ap.add_argument("--frozen", type=Path, default=None,
                    help="the folder holding sublet_v2/, e7r/ and s1v2/ (default <root>/out)")
    a = ap.parse_args(argv)
    root = mc.ms3_root(a.root)
    try:
        res = analysis(load(root, a.frozen))
    except FileNotFoundError as err:
        print(f"[e7b_analysis] {err}", file=sys.stderr)
        return 2
    rg = res["meta"]["registration"]
    if not rg["matches"]:
        print(f"[e7b_analysis] WARNING: this file's sha256 {res['meta']['analysis_sha256'][:12]} is not the one "
              f"{rg['path']} records ({str(rg['registered_sha256'])[:12]}); the output says so (meta.registration)",
              file=sys.stderr)
    out = root / "out" / EXP
    mc.dump_json(res, out / "analysis.json")
    mc.write_text(to_md(res), out / "analysis.md")
    r = res["readings"]
    print(f"[e7b_analysis] {len(res['runs'])} runs; R1 {r['R1']['holds']}, R2 {r['R2']['holds']}, R3 "
          f"{r['R3']['n_cells']} cells; identity {res['identity']['holds']}; wrote {out / 'analysis.json'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
