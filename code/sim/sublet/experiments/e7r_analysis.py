"""E7r's analysis: per-week and median r0, W0, W0+ and RC, Sublet's margin over each baseline as built and as c2, the
tuned settings and their confirmation (design/ms7/plan.md X4, X5, D4, D6; change C54;
design/ms7/feasibility/baselines.md §2).
Its sha256 is recorded in design/ms7/registration.md before the runs and every e7r part refuses to start unless the
file still has it (ms7_baselines.check_registration); so every rule below is fixed and deterministic, and the file
depends only on the summaries it reads and ms3_common's file helpers. No p-value is computed (D4: the weeks are
rotations of one series); the margins are reported with sign counts and min-max, in the confirmation's convention
(ms5b_common.paired_margins, design/sublet_v2.md §4.5: the baseline minus Sublet, positive when Sublet costs less, a
missing run a loss for Sublet), as experiments/e7c_analysis.py reports X1's.

Inputs (<root> as ms3_common.ms3_root): <root>/out/e7r/eval/summary.json and confirm/summary.json (e7r), tune/
selection.json (e7r_select.py), and the confirmation's frozen <frozen>/main/summary.json and second/summary.json
(default <frozen> = <root>/out/sublet_v2; read only). Output: <root>/out/e7r/analysis.json and analysis.md.

Rules (policy seed 0; r0 is a run's overflow cost over BL0a; a missing or failed run is null in the tables):
  table     per tag, mode and week: eval's r0; for a tag of the confirmation's main part (the tags e7r runs under the
            new modes and L-tr) its seven modes come from main's table, which takes precedence over eval's in every
            (mode, week) cell main has (eval's L-tr runs of these tags serve check (i) only; a cell main lacks, as the
            development week of a reduced run, is eval's); an alias of selection.json (W equal to T) reads its
            target's runs. A tag's sources are recorded.
  metrics   per week: r0(M) per mode M; r0_tr = r0 under L-tr; W0 = the largest r0 over STRESS_MODES (the
            registered W0's five modes); W0+ = the largest over W0PLUS_MODES (STRESS_MODES and NEW_MODES; L-ad is in
            it through its identity with L-eg, ADAPTIVE_EQUIV, checked below on the confirmation's runs); RC(M) =
            r0(M) - r0(L-hon) per mode M; a metric is null while one of its runs is; per tag the median, min and max
            over the weeks with a value, with the count of weeks without one.
  margins   for every tag b other than Sublet and each metric (r0_tr, W0, W0+, and r0(M) for every mode M both
            tags have): Delta_w = metric(b, w) - metric(Sublet, w) per week (positive: Sublet costs less); n, the
            weeks with Delta_w > 0 (wins), = 0 (ties) and < 0 (losses), the weeks without a value (missing; by
            §4.5's missing-run rule a loss for Sublet, so losses_with_missing = losses + missing), and the median, min
            and max of Delta_w over the weeks with a value.
  as built and c2  the pairs AS_BUILT_C2 (each baseline as built and with A9.3's kbar contracts): both margins.
  best of a set  per week and metric the least value over the tags of a comparison set (BASELINE_SETS: the
            confirmation's H1 and H2b sets, the c2 transplants, SpotHedge with spares, the tuned T and the tuned W
            settings (aliases read as their targets), and every online baseline together); null while a member that
            was run has no value that week (a missing run could be the least); members that were not run are listed
            and left out. Sublet's margin over the best of each set: the margins above (ms5b_common.paired_margins'
            min over the set, as H1's).
  tuned     per family the selection's T and W settings: the margin over T on r0_tr (H1-type), over W on W0 and on
            W0+ (H2-type), with their dev-week medians from selection.json.
  intensity per tag, the i.i.d. stress-intensity curve of design/sublet_v2.md §4.5 at the points of the evaluation's
            16 weeks, p in INTENSITY (0 = L-hon, the three low rates of X5, 0.05 and 0.2): per week the points (p, r0)
            in p order and the first p at which r0 > 1 (null if none; a flag when a point before it has no value), and
            per p the median, min and max over the weeks (the margin over a tag at each p is in its margins by mode).
  confirm   weeks 121-124: per family the median over the weeks of r0_tr and of W0 for the as-built setting, T and W;
            T holds iff median r0_tr(T) <= median r0_tr(as built); W holds iff median W0(W) <= median W0(as built).
  checks    (i) identity: every eval tag whose registry id and parameters (a dict, or the text of an MS5b rule) equal
            those of a tag of main has the same r0 in every shared (mode, week) (max |difference| reported; all
            identical iff every pair with shared cells is), and each tag whose rows combine main's runs with eval's
            records reproduces_main (its pair with main's tag of the same name identical; null without a shared
            cell), the condition for reporting its W0+ and new-mode margins as one policy's; (ii) A9-P's lender
            invariance: per week the spread of its r0 over the modes; (iii) the adaptive lender: max |r0(L-ad) -
            r0(L-eg)| over the paired runs of second (L-ad) and main (L-eg); (iv) provenance: the sha256 of the
            selection.json read here equals the one that eval's and confirm's summaries record, and the git revisions
            of eval, confirm and the selection's tune summary are one commit.
"""
from __future__ import annotations

import argparse
import hashlib
import statistics
import sys
from pathlib import Path
from typing import Optional

from . import ms3_common as mc

SUBLET = "Sublet"
TRACE_MODE = "L-tr"
HON_MODE = "L-hon"
STRESS_MODES = ("L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co")
NEW_MODES = ("L-iid-0.0005", "L-iid-0.002", "L-iid-0.0124", "L-co-reg-0.5", "L-co-reg-1", "L-pk")
CONF_MODES = (TRACE_MODE,) + STRESS_MODES + (HON_MODE,)
W0PLUS_MODES = STRESS_MODES + NEW_MODES
ADAPTIVE_EQUIV = {"L-ad": "L-eg"}
AS_BUILT_C2 = (("BL1", "BL1-c2"), ("BL2", "BL2-c2"), ("BL3-0", "BL3-0-c2"), ("BL4", "BL4-c2"),
               ("BL5-cur", "BL5-cur-c2"))
FAMILIES = ("BL1", "BL2", "BL3", "BL4", "BL5", "MPC")
FAMILY_DEFAULT = {"BL1": "BL1", "BL2": "BL2", "BL3": "BL3-0", "BL4": "BL4", "BL5": "BL5-cur", "MPC": "MPC"}
PROTECTED_ONLY = "A9-P"
METRICS = ("r0_tr", "W0", "W0plus")
H1_SET = ("BL1", "BL1-BO", "BL2", "BL3-0", "BL4", "BL5", "BL5-cur")      # ms5b_common.H1_SET (as built)
H2B_SET = ("BL5-tau60", "BL1-GP", "BL1N", "BL5N")                      # ms5b_common.H2B_SET (notice-aware)
C2_SET = tuple(c for _a, c in AS_BUILT_C2)
SPARES_SET = ("BL3-1", "BL3-2", "BL3-1-llm", "BL3-2-llm")
TUNED_T = tuple(f"{f}-T" for f in FAMILIES)
TUNED_W = tuple(f"{f}-W" for f in FAMILIES)
BASELINE_SETS = {"as_built": H1_SET, "notice_aware": H2B_SET, "c2": C2_SET, "spares": SPARES_SET, "tuned_T": TUNED_T,
                 "tuned_W": TUNED_W,
                 "all_online": tuple(dict.fromkeys(H1_SET + H2B_SET + C2_SET + SPARES_SET + TUNED_T + TUNED_W
                                                   + (PROTECTED_ONLY,)))}
SEED = "0"
IDENTITY_TOL = 1e-12
INTENSITY = ((0.0, HON_MODE), (0.0005, "L-iid-0.0005"), (0.002, "L-iid-0.002"), (0.0124, "L-iid-0.0124"),
             (0.05, "L-iid-0.05"), (0.2, "L-iid-0.2"))         # (p, mode) of the i.i.d. points on the 16 weeks


# ---------------------------------------------------------------- inputs
def load(root: Path, frozen: Optional[Path] = None) -> dict:
    e = root / "out" / "e7r"
    fz = Path(frozen) if frozen is not None else root / "out" / "sublet_v2"
    files = {"eval": e / "eval" / "summary.json", "confirm": e / "confirm" / "summary.json",
             "selection": e / "tune" / "selection.json", "main": fz / "main" / "summary.json",
             "second": fz / "second" / "summary.json"}
    out = {k: mc.read_json(p) for k, p in files.items()}
    out["sha256"] = {k: (hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None) for k, p in files.items()}
    out["paths"] = {k: str(p) for k, p in files.items()}
    return out


def _cells(s: Optional[dict], tag: str, mode: str) -> dict:
    return (((s or {}).get("table") or {}).get(tag) or {}).get(mode) or {}


def _r0(s: Optional[dict], tag: str, mode: str, week: str) -> Optional[float]:
    v = _cells(s, tag, mode).get(week, {}).get(SEED)
    return None if v is None else float(v)


def merged_table(ev: dict, main: Optional[dict], aliases: dict) -> tuple[dict, dict]:
    """({tag: {mode: {week: r0 or None}}}, {tag: sources}) over eval's weeks (module docstring, 'table')."""
    weeks = [mc.num_key(w) for w in (ev.get("meta") or {}).get("weeks") or []]
    tags = sorted(set((ev.get("table") or {})) | set(aliases))
    tab, src = {}, {}
    for t in tags:
        base = aliases.get(t, t)
        rows = {}
        for m in (ev.get("table") or {}).get(base) or {}:
            rows[m] = {w: _r0(ev, base, m, w) for w in weeks}
        sources = ["eval" if base == t else f"eval (alias of {base})"]
        if main is not None and base in (main.get("table") or {}):
            n = 0
            for m in CONF_MODES:
                cells = _cells(main, base, m)
                for w in weeks:
                    if w in cells:                     # main's cell (its run, or its failed run's null) first
                        rows.setdefault(m, {w2: None for w2 in weeks})[w] = _r0(main, base, m, w)
                        n += 1
            if n:
                sources.append("confirmation main (seven modes, before eval's)")
        tab[t], src[t] = rows, sources
    return tab, src


# ---------------------------------------------------------------- metrics and margins
def _max_or_none(vals) -> Optional[float]:
    vals = list(vals)
    return None if not vals or any(v is None for v in vals) else max(vals)


def week_metrics(rows: dict, week: str) -> dict:
    """r0_tr, W0, W0+ and RC per mode of one tag and week (null while a run is missing or a mode was not run)."""
    def r(m):
        return (rows.get(m) or {}).get(week) if m in rows else None
    out = {"r0": {m: r(m) for m in rows}, "r0_tr": r(TRACE_MODE),
           "W0": _max_or_none(r(m) for m in STRESS_MODES) if all(m in rows for m in STRESS_MODES) else None,
           "W0plus": _max_or_none(r(m) for m in W0PLUS_MODES) if all(m in rows for m in W0PLUS_MODES) else None}
    h = r(HON_MODE)
    out["RC"] = {m: (None if r(m) is None or h is None else r(m) - h) for m in rows if m != HON_MODE}
    return out


def _stats(vals: list) -> dict:
    v = [x for x in vals if x is not None]
    return {"n": len(v), "n_missing": len(vals) - len(v), "median": statistics.median(v) if v else None,
            "min": min(v) if v else None, "max": max(v) if v else None}


def tag_metrics(rows: dict, weeks: list) -> dict:
    per = {w: week_metrics(rows, w) for w in weeks}
    rc_modes = sorted({m for x in per.values() for m in x["RC"]})
    return {"per_week": per, **{k: _stats([per[w][k] for w in weeks]) for k in METRICS},
            "r0": {m: _stats([per[w]["r0"].get(m) for w in weeks]) for m in sorted(rows)},
            "RC": {m: _stats([per[w]["RC"].get(m) for w in weeks]) for m in rc_modes}}


def _metric(per_w: dict, metric: str) -> Optional[float]:
    """One week's metric: 'r0_tr', 'W0' or 'W0plus', or 'r0:<mode>' for r0 under a mode."""
    if metric.startswith("r0:"):
        return (per_w.get("r0") or {}).get(metric[3:])
    return per_w.get(metric)


def margin(per_s: dict, per_b: dict, metric: str, weeks: list) -> dict:
    """Delta_w = metric(b, w) - metric(Sublet, w), per_s Sublet's weeks and per_b the baseline's (module docstring,
    'margins'; positive when Sublet costs less); metric as _metric reads it."""
    d = {}
    for w in weeks:
        a, b = _metric(per_s[w], metric), _metric(per_b[w], metric)
        d[w] = None if a is None or b is None else b - a
    v = [x for x in d.values() if x is not None]
    losses, miss = sum(1 for x in v if x < 0), len(d) - len(v)
    return {"per_week": d, "n": len(v), "wins": sum(1 for x in v if x > 0), "ties": sum(1 for x in v if x == 0),
            "losses": losses, "missing": miss, "losses_with_missing": losses + miss,
            "median": statistics.median(v) if v else None, "min": min(v) if v else None,
            "max": max(v) if v else None}


def intensity(rows: dict, weeks: list) -> Optional[dict]:
    """The i.i.d. stress-intensity curve of one tag (module docstring, 'intensity'); None without any of its modes."""
    pts = [(p, m) for p, m in INTENSITY if m in rows]
    if not pts:
        return None
    per = {}
    for w in weeks:
        vals = [(p, (rows.get(m) or {}).get(w)) for p, m in pts]
        first, gap = None, False
        for p, v in vals:
            if v is None:
                gap = True
                continue
            if v > 1.0:
                first = p
                break
        per[w] = {"points": [[p, v] for p, v in vals], "first_p_above_1": first, "missing_before_first": gap}
    return {"points": [[p, m] for p, m in pts], "per_week": per,
            "by_p": {m: _stats([(rows.get(m) or {}).get(w) for w in weeks]) for _p, m in pts}}


def best_of(met: dict, members, weeks: list, aliases: dict) -> dict:
    """The best of a comparison set per week (module docstring, 'best of a set'): {'members', 'absent', 'per_week':
    {week: {metric: least value or None, metric + '_tag': its tag}}}; aliases (W equal to T) read as their targets,
    once."""
    names = list(dict.fromkeys(aliases.get(t, t) for t in members))
    have = [t for t in names if t in met]
    per = {}
    for w in weeks:
        row = {}
        for k in METRICS:
            vals = [(met[t]["per_week"][w][k], t) for t in have]
            ok = bool(vals) and all(v is not None for v, _t in vals)
            best = min(vals, key=lambda x: (x[0], have.index(x[1]))) if ok else (None, None)
            row[k], row[k + "_tag"] = best
        per[w] = row
    return {"members": have, "absent": [t for t in names if t not in met], "per_week": per}


# ---------------------------------------------------------------- confirm and checks
def confirm_check(conf: Optional[dict], sel: Optional[dict]) -> Optional[dict]:
    if conf is None or sel is None:
        return None
    weeks = [mc.num_key(w) for w in (conf.get("meta") or {}).get("weeks") or []]
    aliases = sel.get("aliases") or {}

    def med(tag, kind):
        t = aliases.get(tag, tag)
        vals = []
        for w in weeks:
            if kind == "r0_tr":
                vals.append(_r0(conf, t, TRACE_MODE, w))
            else:
                st = [_r0(conf, t, m, w) for m in STRESS_MODES]
                vals.append(None if any(v is None for v in st) else max(st))
        return None if not vals or any(v is None for v in vals) else statistics.median(vals)
    out = {}
    for fam in FAMILIES:
        d, T, W = FAMILY_DEFAULT[fam], f"{fam}-T", f"{fam}-W"
        row = {"as_built": d, "median_r0_tr": {}, "median_W0": {}}
        for name in (d, T, W):
            row["median_r0_tr"][name], row["median_W0"][name] = med(name, "r0_tr"), med(name, "W0")
        a, b = row["median_r0_tr"][T], row["median_r0_tr"][d]
        row["T_holds"] = None if a is None or b is None else a <= b
        a, b = row["median_W0"][W], row["median_W0"][d]
        row["W_holds"] = None if a is None or b is None else a <= b
        out[fam] = row
    return {"weeks": weeks, "families": out}


def identity_check(ev: dict, main: Optional[dict]) -> list:
    """(i): eval tags with the registry id and parameters (a dict, or an MS5b rule's text) of a main tag, their max
    |r0 difference| on shared cells."""
    if main is None:
        return []
    et, mt = (ev.get("meta") or {}).get("tags") or {}, (main.get("meta") or {}).get("tags") or {}
    out = []
    for t, x in sorted(et.items()):
        if not isinstance(x.get("params"), (dict, str)):
            continue
        for u, y in sorted(mt.items()):
            if y.get("policy_id") != x.get("policy_id") or y.get("params") != x.get("params"):
                continue
            diffs = []
            for m in set((ev.get("table") or {}).get(t, {})) & set((main.get("table") or {}).get(u, {})):
                for w in set(_cells(ev, t, m)) & set(_cells(main, u, m)):
                    a, b = _r0(ev, t, m, w), _r0(main, u, m, w)
                    if a is not None and b is not None:
                        diffs.append(abs(a - b))
            out.append({"eval_tag": t, "main_tag": u, "n_cells": len(diffs),
                        "max_abs_diff": max(diffs) if diffs else None,
                        "identical": bool(diffs) and max(diffs) <= IDENTITY_TOL})
    return out


def identity_summary(pairs: list) -> dict:
    """(i) over the pairs with shared cells: their number, how many are identical, the cells and the largest
    |difference|; all_identical is null without a shared cell."""
    sh = [x for x in pairs if x["n_cells"]]
    return {"pairs_with_cells": len(sh), "identical": sum(1 for x in sh if x["identical"]),
            "cells": sum(x["n_cells"] for x in sh),
            "max_abs_diff": max((x["max_abs_diff"] for x in sh), default=None),
            "all_identical": all(x["identical"] for x in sh) if sh else None,
            "not_identical": [[x["eval_tag"], x["main_tag"]] for x in sh if not x["identical"]]}


def provenance_check(inp: dict) -> dict:
    """(iv): the selection read here against the sha256 that eval's and confirm's summaries record (meta.selection),
    and the git revisions of eval, confirm and the selection's tune summary."""
    sel_sha = (inp.get("sha256") or {}).get("selection")
    out = {"selection_sha256": sel_sha}
    for k in ("eval", "confirm"):
        meta = (inp.get(k) or {}).get("meta") or {}
        rec = (meta.get("selection") or {}).get("sha256")
        out[f"{k}_selection_sha256"] = rec
        out[f"{k}_selection_equal"] = None if inp.get(k) is None else (sel_sha is not None and rec == sel_sha)
        out[f"{k}_git_revision"] = meta.get("git_revision")
    out["tune_git_revision"] = ((inp.get("selection") or {}).get("meta") or {}).get("summary_git_revision")
    revs = [out[k] for k in ("eval_git_revision", "confirm_git_revision", "tune_git_revision")]
    out["one_commit"] = None if any(r is None for r in revs) else len(set(revs)) == 1
    return out


def invariance_check(tab: dict, tag: str, weeks: list) -> Optional[dict]:
    """(ii): per week max - min of the tag's r0 over its modes."""
    rows = tab.get(tag)
    if not rows:
        return None
    spread = {}
    for w in weeks:
        v = [rows[m].get(w) for m in rows]
        spread[w] = None if any(x is None for x in v) else max(v) - min(v)
    v = [x for x in spread.values() if x is not None]
    return {"per_week": spread, "max_spread": max(v) if v else None, "modes": sorted(rows)}


def adaptive_check(main: Optional[dict], second: Optional[dict]) -> Optional[dict]:
    """(iii): max |r0(L-ad) - r0(L-eg)| over the (tag, week) cells with both runs (L-ad from second, L-eg from main or
    second)."""
    if second is None:
        return None
    diffs = []
    for t, by_m in sorted((second.get("table") or {}).items()):
        for w, s in (by_m.get("L-ad") or {}).items():
            a = s.get(SEED)
            b = _r0(second, t, "L-eg", w)
            if b is None:
                b = _r0(main, t, "L-eg", w)
            if a is not None and b is not None:
                diffs.append(abs(float(a) - b))
    return {"n_pairs": len(diffs), "max_abs_diff": max(diffs) if diffs else None, "equivalence": ADAPTIVE_EQUIV}


# ---------------------------------------------------------------- the analysis
def analysis(inp: dict) -> dict:
    ev, main, sel = inp.get("eval"), inp.get("main"), inp.get("selection")
    if ev is None:
        raise FileNotFoundError(f"{inp['paths']['eval']} is missing: run part eval first")
    aliases = dict((sel or {}).get("aliases") or {})
    weeks = [mc.num_key(w) for w in (ev.get("meta") or {}).get("weeks") or []]
    tab, src = merged_table(ev, main, aliases)
    met = {t: tag_metrics(rows, weeks) for t, rows in tab.items()}
    tags_meta = (ev.get("meta") or {}).get("tags") or {}
    out = {"weeks": weeks, "tags": {}, "margins": {}, "as_built_vs_c2": [], "tuned": {}, "best_of": {}}
    for t in sorted(tab):
        m = met[t]
        out["tags"][t] = {"sources": src[t], **{k: v for k, v in tags_meta.get(aliases.get(t, t), {}).items()
                                               if k in ("policy_id", "params", "family", "kind", "role")},
                          "modes": sorted(tab[t]), **{k: m[k] for k in METRICS}, "r0": m["r0"], "RC": m["RC"],
                          "intensity": intensity(tab[t], weeks), "per_week": m["per_week"]}
    if SUBLET in met:
        sp = met[SUBLET]["per_week"]
        for t in sorted(met):
            if t != SUBLET:
                out["margins"][t] = {k: margin(sp, met[t]["per_week"], k, weeks) for k in METRICS}
                out["margins"][t]["r0_by_mode"] = {m: margin(sp, met[t]["per_week"], f"r0:{m}", weeks)
                                                   for m in sorted(set(tab[SUBLET]) & set(tab[t]))}
        out["best_of"] = {}
        for name, members in BASELINE_SETS.items():
            b = best_of(met, members, weeks, aliases)
            out["best_of"][name] = {**b, "margins": {k: margin(sp, b["per_week"], k, weeks) for k in METRICS}}
        for a, c in AS_BUILT_C2:
            out["as_built_vs_c2"].append({"as_built": a, "c2": c,
                                          "margins_as_built": out["margins"].get(a),
                                          "margins_c2": out["margins"].get(c)})
        for fam in FAMILIES:
            T, W = f"{fam}-T", f"{fam}-W"
            tuned = (sel or {}).get("tuned") or {}
            out["tuned"][fam] = {
                "T": {**(tuned.get(T) or {}), "margin_r0_tr": (out["margins"].get(T) or {}).get("r0_tr")},
                "W": {**(tuned.get(W) or {}), "alias_of": aliases.get(W),
                      "margin_W0": (out["margins"].get(W) or {}).get("W0"),
                      "margin_W0plus": (out["margins"].get(W) or {}).get("W0plus")}}
    out["confirm"] = confirm_check(inp.get("confirm"), sel)
    ident = identity_check(ev, main)
    same = {x["eval_tag"]: x for x in ident if x["eval_tag"] == x["main_tag"]}
    for t, x in out["tags"].items():
        if any(s.startswith("confirmation main") for s in x["sources"]):
            # whether this commit reproduces the main runs the tag's rows combine with (check (i); null: no shared cell)
            p = same.get(aliases.get(t, t))
            x["reproduces_main"] = None if p is None or not p["n_cells"] else bool(p["identical"])
    out["checks"] = {"identity_with_confirmation": ident, "identity_summary": identity_summary(ident),
                     "a9p_invariance": invariance_check(tab, PROTECTED_ONLY, weeks),
                     "adaptive_equivalence": adaptive_check(main, inp.get("second")),
                     "provenance": provenance_check(inp)}
    me = Path(__file__).resolve()
    out["meta"] = {"script": "code/sim/sublet/experiments/e7r_analysis.py",
                   "script_sha256": hashlib.sha256(me.read_bytes()).hexdigest(), "inputs_sha256": inp["sha256"],
                   "inputs": inp["paths"], "git_revision": mc.git_revision(), "written": mc._now(),
                   "reduced": bool((ev.get("meta") or {}).get("reduced")),
                   "eval_git_revision": (ev.get("meta") or {}).get("git_revision"),
                   "stress_modes": list(STRESS_MODES), "new_modes": list(NEW_MODES),
                   "w0plus_modes": list(W0PLUS_MODES), "adaptive_equivalence": ADAPTIVE_EQUIV,
                   "intensity_points": [[p, m] for p, m in INTENSITY],
                   "baseline_sets": {k: list(v) for k, v in BASELINE_SETS.items()},
                   "note": "margins are the baseline minus Sublet (positive: Sublet costs less; a missing run is a "
                           "loss for Sublet, design/sublet_v2.md §4.5); no p-values (D4)"}
    return out


def _f(x) -> str:
    return "-" if x is None else f"{x:.4f}"


def to_md(a: dict) -> str:
    lines = ["# E7r analysis (design/ms7/plan.md X4, X5; C54)", ""]
    if a["meta"].get("reduced"):
        lines += ["Reduced run (development cell only): not a result.", ""]
    lines += [f"Weeks: {', '.join(a['weeks'])}. Margins are the baseline minus Sublet (the confirmation's Delta); "
              "positive means Sublet costs less; a missing run is a loss for Sublet. No p-values.", ""]
    rows = [[t, x.get("family"), _f(x["r0_tr"]["median"]), _f(x["W0"]["median"]), _f(x["W0plus"]["median"]),
             x["r0_tr"]["n_missing"], x.get("reproduces_main", "-")] for t, x in sorted(a["tags"].items())]
    lines += ["## Medians over the weeks", "",
              mc.md_table(["tag", "family", "r0 L-tr", "W0", "W0+", "weeks missing", "reproduces main"], rows), ""]
    rows = []
    for t, x in sorted(a["margins"].items()):
        for k in METRICS:
            mm = x[k]
            rows.append([t, k, mm["n"], mm["wins"], mm["ties"], mm["losses"], mm["missing"], _f(mm["median"]),
                         _f(mm["min"]), _f(mm["max"])])
    lines += ["## Sublet's margin over each baseline (baseline minus Sublet)", "",
              mc.md_table(["baseline", "metric", "weeks", "wins", "ties", "losses", "missing", "median", "min",
                           "max"], rows), ""]
    rows = []
    for name, x in (a.get("best_of") or {}).items():
        for k in METRICS:
            mm = x["margins"][k]
            rows.append([name, k, len(x["members"]), mm["n"], mm["wins"], mm["ties"], mm["losses"], mm["missing"],
                         _f(mm["median"]), _f(mm["min"]), _f(mm["max"])])
    lines += ["## Sublet's margin over the best of each comparison set (per week)", "",
              mc.md_table(["set", "metric", "members run", "weeks", "wins", "ties", "losses", "missing", "median",
                           "min", "max"], rows), ""]
    modes = sorted({m for x in a["tags"].values() for m in x.get("r0") or {}})
    rows = [[t] + [_f(((x.get("r0") or {}).get(m) or {}).get("median")) for m in modes]
            for t, x in sorted(a["tags"].items())]
    lines += ["## Median r0 per mode", "", mc.md_table(["tag"] + modes, rows), ""]
    rows = []
    for fam, x in a["tuned"].items():
        rows.append([fam, x["T"].get("config"), _f((x["T"].get("margin_r0_tr") or {}).get("median")),
                     x["W"].get("config"), _f((x["W"].get("margin_W0") or {}).get("median")),
                     _f((x["W"].get("margin_W0plus") or {}).get("median"))])
    lines += ["## Tuned settings (median margins, baseline minus Sublet)", "",
              mc.md_table(["family", "T", "T - Sublet (r0 L-tr)", "W", "W - Sublet (W0)", "W - Sublet (W0+)"], rows),
              ""]
    if a.get("confirm"):
        rows = [[fam, x["as_built"], x["T_holds"], x["W_holds"]] for fam, x in a["confirm"]["families"].items()]
        lines += ["## Confirmation of the tuned settings (weeks " + ", ".join(a["confirm"]["weeks"]) + ")", "",
                  mc.md_table(["family", "as built", "T holds", "W holds"], rows), ""]
    pmodes = [m for _p, m in INTENSITY]
    rows = []
    for t, x in sorted(a["tags"].items()):
        it = x.get("intensity")
        if not it:
            continue
        firsts = [v["first_p_above_1"] for v in it["per_week"].values()]
        rows.append([t] + [_f((it["by_p"].get(m) or {}).get("median")) for m in pmodes]
                    + [sum(1 for v in firsts if v is not None)])
    lines += ["## I.i.d. stress intensity (median r0 over the weeks; p = 0 is L-hon)", "",
              mc.md_table(["tag"] + [f"p {p:g}" for p, _m in INTENSITY] + ["weeks with r0 > 1 at some p"], rows), ""]
    c = a["checks"]
    ids, pv = c["identity_summary"], c["provenance"]
    lines += ["## Checks", "",
              f"- identity with the confirmation: {ids['identical']} of {ids['pairs_with_cells']} tag pairs with the "
              f"same registry id and parameters identical on their {ids['cells']} shared cells (max |diff| "
              f"{_f(ids['max_abs_diff'])}; not identical: {ids['not_identical'] or 'none'})",
              f"- A9-P max spread over modes: {_f((c['a9p_invariance'] or {}).get('max_spread'))}",
              f"- L-ad vs L-eg: {(c['adaptive_equivalence'] or {}).get('n_pairs')} pairs, max |diff| "
              f"{_f((c['adaptive_equivalence'] or {}).get('max_abs_diff'))}",
              f"- provenance: selection as eval records {pv['eval_selection_equal']}, as confirm records "
              f"{pv['confirm_selection_equal']}; eval, confirm and tune at one commit {pv['one_commit']}", ""]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.e7r_analysis", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="folder whose out/e7r/ holds the parts (default MS3_ROOT or this "
                                                 "repository's code/sim)")
    ap.add_argument("--frozen", type=Path, default=None,
                    help="the confirmation's folder (default <root>/out/sublet_v2)")
    a = ap.parse_args(argv)
    root = mc.ms3_root(a.root)
    try:
        res = analysis(load(root, a.frozen))
    except FileNotFoundError as err:
        print(f"[e7r_analysis] {err}", file=sys.stderr)
        return 2
    out = root / "out" / "e7r"
    mc.dump_json(res, out / "analysis.json")
    mc.write_text(to_md(res), out / "analysis.md")
    print(f"[e7r_analysis] {len(res['tags'])} tags over {len(res['weeks'])} weeks; wrote {out / 'analysis.json'}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
