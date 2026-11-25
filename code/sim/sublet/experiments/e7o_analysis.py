"""E7o's analysis (MS7 X2; design/ms7/plan.md §3 X2 and D6; design/ms7/feasibility/oos.md §3; change C55).

Written and frozen before the runs (D6: its sha256 is recorded in design/ms7/registration.md, and e7o's gate refuses a
job of the full design unless the script on disk and at HEAD has that sha256); it reads only the part summaries and
the confirmation's main summary, draws nothing and prints no p-value (D4: the cells share one held-out lender block
per fold, so the per-cell values are reported with sign counts, medians and min-max).

Inputs: <root>/out/e7o/<part>/summary.json for the parts fwd and rev (e7o.summary_part; a part without a summary is
listed as missing) and, for the bridge, <root>/out/sublet_v2/main/summary.json (the confirmation's week runs).
Per fold (part), arm (oos, is), tag and cell (policy seed 0; the missing-run rule of design/sublet_v2.md §4.5: a run
that is missing or not ok gives None, and a comparison that needs it is None, counted apart):
  r0       r0 per mode (cost over BL0a; the cell's BL0a is the same in both arms, since the demand and Gamma are)
  W0       the largest r0 over the five stress modes (ms5b_common.w0_of)
  RC       r0(mode) - r0(L-hon) for L-tr, L-vr and the five stress modes
  sources  per lender source (maas, spot): buffer violation slots, those with a positive attributable deficit,
           reclaims and violation cuts of the run's leases (e7o.source_fields), under L-tr and L-vr
and the summaries over the cells:
  stats            per (arm, tag, mode) and for W0: n, median, min, max over the cells
  oos_minus_is     per tag, cell and mode (and W0): r0(oos) - r0(is); per (tag, mode): n_pos, n_neg, n_zero,
                   n_missing, median, min, max over the cells
  sublet_vs_h1     per arm, cell and mode (and W0): d = r0(Sublet) - min over ms5b_common.H1_SET of r0 (the cheapest
                   H1 baseline, its tag kept); per (arm, mode): n_sublet_cheaper (d < 0), n_equal, n_sublet_dearer
                   (d > 0), n_missing (a missing run of Sublet or of any H1 baseline: a loss for Sublet), median, min,
                   max of d
  stats_rc         per (arm, tag, mode of RC) n, median, min, max of RC over the cells
  sources_total    per (arm, tag, mode in L-tr, L-vr) the sums over the cells of the source counts
  criteria         per arm, the confirmation's rules H1, H2 and H2b (design/sublet_v2.md §6, as ms5b_analysis states
                   them, with its thresholds H1_WINS, H1_MARGIN and H2_MEDIAN) applied to the cells in place of the
                   weeks, descriptively: per cell the margins and W0 comparisons, the counts, the median and whether
                   every threshold is met ('holds'; None unless the fold has N_CRITERIA_CELLS = 16 cells); without
                   ms5b_analysis's sign test, bootstrap interval and Wilcoxon test (D4). H1: Delta = min over H1's
                   set of r0 - r0(Sublet) under L-tr (the confirmation's mode) and, reported alike, under L-vr (the
                   mode that charges buffer violations, oos.md risk 3); Sublet wins a cell when Delta > 0; holds when
                   it wins at least 12 of 16 cells and the median Delta (a missing run: LOSS_MARGIN, below every real
                   margin; a median that a loss decides is None) is at least 0.02 BL0a. H2: Sublet's W0 < 1 and below
                   the W0 of every policy of H1's set in 16 of 16 cells, and the median of Sublet's W0 <= 0.85. H2b:
                   Sublet's W0 below that of every policy of ms5b_common.H2B_SET in 16 of 16 cells (and per policy)
  instances        per arm and cell the supply by lender source, the pinned Gamma, BL0a, the number of instance hashes
                   (1 when every tag ran on the same instance) and per source the median of the lenders' b, from the
                   part summary's instance facts
  bridge           per (arm, tag, mode, cell) r0 - r0 of the confirmation's week run at the cell's config seed (the
                   in-sample twin differs from the confirmation in horizon, clock and demand construction, oos.md §3
                   and risk 5); None where the confirmation has no such run (reduced cells)
Outputs <out>/analysis.json and analysis.md (default <root>/out/e7o/); both are byte-identical for the same inputs at
the same commit (analysis.json records the git revision it ran at, so ms3_common.check_copy('e7o') finds the clone's
commit in it as in every other JSON file of out/e7o/).

  python -m sublet.experiments.e7o_analysis [--root DIR] [--out DIR]     (root: as ms3_common.ms3_root)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path
from typing import Optional

from . import ms3_common as mc
from . import ms5b_common as m5

EXP = "e7o"
FOLDS = ("fwd", "rev")                   # e7o.PARTS
ARMS = ("oos", "is")                     # e7o.ARMS
SUBLET = "Sublet"
H1 = tuple(m5.H1_SET)
TRACE, HON, VR = m5.TRACE_MODE, m5.HON_MODE, "L-vr"
STRESS = tuple(m5.stress_modes())
MODES = (TRACE, VR) + STRESS + (HON,)    # e7o.MODES
RC_MODES = (TRACE, VR) + STRESS
SOURCE_MODES = (TRACE, VR)
SOURCES = ("maas", "spot")
SOURCE_FIELDS = ("violation_slots", "violation_slots_attributable", "reclaims", "violation_cuts")
CONF_SUMMARY = ("sublet_v2", "main", "summary.json")
W0_KEY = "W0"
DIGITS = 4
H2B = tuple(m5.H2B_SET)
CRITERIA_MODES = (TRACE, VR)             # H1's modes
N_CRITERIA_CELLS = 16                    # the confirmation's 16 weeks: the rules are evaluated on 16 cells only
H1_WINS, H1_MARGIN, H2_MEDIAN = 12, 0.02, 0.85     # ms5b_analysis's (the confirmation's) thresholds
LOSS_MARGIN, LOSS_LIMIT = -1.0e9, 1.0e8            # ms5b_analysis's: a missing run's margin, and the bound of real ones


def _sha(p: Path) -> Optional[str]:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def _ok(r: dict) -> bool:
    return r.get("status") == "ok" and r.get("r0") is not None


def load(root=None) -> dict:
    """{'parts': {fold: summary or None}, 'conf': the confirmation's main summary or None, 'inputs': paths and
    sha256} under <root>/out (root as ms3_common.ms3_root)."""
    r = mc.ms3_root(root)
    parts, inputs = {}, {}
    for f in FOLDS:
        p = r / "out" / EXP / f / "summary.json"
        parts[f] = mc.read_json(p)
        inputs[f] = {"path": f"out/{EXP}/{f}/summary.json", "sha256": _sha(p)}
    cp = r / "out" / Path(*CONF_SUMMARY)
    inputs["confirmation_main"] = {"path": "out/" + "/".join(CONF_SUMMARY), "sha256": _sha(cp)}
    return {"parts": parts, "conf": mc.read_json(cp), "inputs": inputs}


def _stat(xs) -> dict:
    v = [float(x) for x in xs if x is not None]
    return {"n": len(v), "n_missing": sum(1 for x in xs if x is None),
            "median": float(statistics.median(v)) if v else None, "min": min(v) if v else None,
            "max": max(v) if v else None}


def _signs(xs) -> dict:
    v = [float(x) for x in xs if x is not None]
    return {**_stat(xs), "n_pos": sum(1 for x in v if x > 0), "n_neg": sum(1 for x in v if x < 0),
            "n_zero": sum(1 for x in v if x == 0)}


def runs_by_key(s: dict) -> dict:
    """{(arm, tag, mode, cell): row} of a part summary's runs at policy seed 0."""
    return {(r["arm"], r["tag"], r["mode"], int(r["cell"])): r for r in s.get("runs") or [] if int(r["seed"]) == 0}


def fold_tables(s: dict) -> dict:
    """The per-cell tables of one fold (module docstring): {arm: {tag: {cell: {'r0': {mode: r0}, 'W0', 'RC':
    {mode: RC}, 'sources': {mode: {source: {field: n}}}, 'status': {mode: status}}}}} and the cells and tags found."""
    by = runs_by_key(s)
    cells = sorted({k[3] for k in by} | {int(c["k"]) for c in (s.get("meta") or {}).get("cells") or []})
    tags = [t for t in ((s.get("meta") or {}).get("design") or {}).get("tags") or sorted({k[1] for k in by})]
    out = {}
    for arm in ARMS:
        for t in tags:
            for c in cells:
                rows = {m: by.get((arm, t, m, c)) for m in MODES}
                r0 = {m: (float(r["r0"]) if r is not None and _ok(r) else None) for m, r in rows.items()}
                w0, w0_mode, _ = m5.w0_of({m: r0[m] for m in STRESS})
                rc = {m: (None if r0[m] is None or r0[HON] is None else r0[m] - r0[HON]) for m in RC_MODES}
                src = {m: {k: {f: ((((rows[m] or {}).get("sources") or {}).get(k) or {}).get(f)
                                   if rows[m] is not None and _ok(rows[m]) else None) for f in SOURCE_FIELDS}
                           for k in SOURCES} for m in SOURCE_MODES}
                out.setdefault(arm, {}).setdefault(t, {})[str(c)] = {
                    "r0": r0, W0_KEY: w0, "W0_mode": w0_mode, "RC": rc, "sources": src,
                    "status": {m: (r or {}).get("status", "missing") for m, r in rows.items()}}
    return {"cells": cells, "tags": tags, "per_cell": out}


def _val(pc: dict, arm: str, t: str, c, key: str) -> Optional[float]:
    x = ((pc.get(arm) or {}).get(t) or {}).get(str(c)) or {}
    return x.get(W0_KEY) if key == W0_KEY else (x.get("r0") or {}).get(key)


def analyse_fold(s: dict, conf: Optional[dict]) -> dict:
    ft = fold_tables(s)
    pc, cells, tags = ft["per_cell"], ft["cells"], ft["tags"]
    keys = MODES + (W0_KEY,)
    stats = {arm: {t: {k: _stat([_val(pc, arm, t, c, k) for c in cells]) for k in keys} for t in tags} for arm in ARMS}
    stats_rc = {arm: {t: {m: _stat([(((pc.get(arm) or {}).get(t) or {}).get(str(c)) or {}).get("RC", {}).get(m)
                                    for c in cells]) for m in RC_MODES} for t in tags} for arm in ARMS}
    diff, diff_sum = {}, {}
    for t in tags:
        for k in keys:
            xs = []
            for c in cells:
                a, b = _val(pc, "oos", t, c, k), _val(pc, "is", t, c, k)
                d = None if a is None or b is None else a - b
                diff.setdefault(t, {}).setdefault(k, {})[str(c)] = d
                xs.append(d)
            diff_sum.setdefault(t, {})[k] = _signs(xs)
    svh, svh_sum = {}, {}
    if SUBLET in tags and all(h in tags for h in H1):
        for arm in ARMS:
            for k in keys:
                ds = []
                for c in cells:
                    sv = _val(pc, arm, SUBLET, c, k)
                    hv = {h: _val(pc, arm, h, c, k) for h in H1}
                    miss = ([] if sv is not None else [SUBLET]) + [h for h, v in hv.items() if v is None]
                    if miss:
                        svh.setdefault(arm, {}).setdefault(k, {})[str(c)] = {"d": None, "best": None,
                                                                           "missing": miss}
                        ds.append(None)
                        continue
                    best = min(hv, key=lambda h: (hv[h], H1.index(h)))
                    d = sv - hv[best]
                    svh.setdefault(arm, {}).setdefault(k, {})[str(c)] = {"d": d, "best": best, "best_r0": hv[best],
                                                                       "sublet_r0": sv, "missing": []}
                    ds.append(d)
                st = _stat(ds)
                v = [x for x in ds if x is not None]
                svh_sum.setdefault(arm, {})[k] = {**st, "n_sublet_cheaper": sum(1 for x in v if x < 0),
                                                  "n_equal": sum(1 for x in v if x == 0),
                                                  "n_sublet_dearer": sum(1 for x in v if x > 0)}
    src_tot = {}
    for arm in ARMS:
        for t in tags:
            for m in SOURCE_MODES:
                tot = {k: {f: 0 for f in SOURCE_FIELDS} for k in SOURCES}
                n_missing = 0
                for c in cells:
                    x = ((pc.get(arm) or {}).get(t) or {}).get(str(c)) or {}
                    blk = (x.get("sources") or {}).get(m) or {}
                    if any(blk.get(k, {}).get(f) is None for k in SOURCES for f in SOURCE_FIELDS):
                        n_missing += 1
                        continue
                    for k in SOURCES:
                        for f in SOURCE_FIELDS:
                            tot[k][f] += int(blk[k][f])
                src_tot.setdefault(arm, {}).setdefault(t, {})[m] = {**tot, "n_cells_missing": n_missing}
    bridge = {}
    ctab = (conf or {}).get("table") or {}
    c_of = {int(c["k"]): int(c["c"]) for c in (s.get("meta") or {}).get("cells") or []}
    for arm in ARMS:
        for t in tags:
            for m in MODES:
                for c in cells:
                    cv = (((ctab.get(t) or {}).get(m) or {}).get(mc.num_key(c_of.get(c, -1))) or {}).get("0")
                    v = _val(pc, arm, t, c, m)
                    bridge.setdefault(arm, {}).setdefault(t, {}).setdefault(m, {})[str(c)] = \
                        None if v is None or cv is None else v - float(cv)
    meta = s.get("meta") or {}
    return {"meta": {k: meta.get(k) for k in ("part", "git_revision", "reduced", "n_runs", "n_missing", "jobs",
                                              "jobs_ok")},
            "cells": cells, "tags": tags, "per_cell": pc, "stats": stats, "stats_rc": stats_rc, "oos_minus_is": diff,
            "oos_minus_is_summary": diff_sum, "sublet_vs_h1": svh, "sublet_vs_h1_summary": svh_sum,
            "sources_total": src_tot, "criteria": {arm: criteria(pc, cells, arm) for arm in ARMS},
            "instances": instances(s), "bridge": bridge}


def _median_margin(d: list) -> Optional[float]:
    """The median of the margins with LOSS_MARGIN for a missing one (ms5b_analysis._stat_block); None when a loss
    decides it or there is none."""
    if not d:
        return None
    m = float(statistics.median([LOSS_MARGIN if x is None else float(x) for x in d]))
    return None if abs(m) >= LOSS_LIMIT else m


def _evaluated(n: int) -> bool:
    return n == N_CRITERIA_CELLS


def criteria(pc: dict, cells: list, arm: str) -> dict:
    """The confirmation's H1, H2 and H2b rules on the cells of one arm (module docstring), descriptively."""
    n = len(cells)
    note = None if _evaluated(n) else f"not evaluated: {n} cell(s), the rules need {N_CRITERIA_CELLS}"
    h1 = {}
    for m in CRITERIA_MODES:
        mg = m5.paired_margins({c: _val(pc, arm, SUBLET, c, m) for c in cells},
                               {t: {c: _val(pc, arm, t, c, m) for c in cells} for t in H1}, cells)
        d = [mg[c]["delta"] for c in cells]
        wins = sum(1 for x in d if x is not None and x > 0)
        med = _median_margin(d)
        h1[m] = {"mode": m, "margins": {str(c): mg[c] for c in cells}, "n_cells": n, "wins": wins,
                 "n_loss_cells": sum(1 for x in d if x is None), "median_margin": med,
                 "min_margin": min((x for x in d if x is not None), default=None),
                 "max_margin": max((x for x in d if x is not None), default=None),
                 "holds": (wins >= H1_WINS and med is not None and med >= H1_MARGIN) if _evaluated(n) else None}
    w0s = {c: _val(pc, arm, SUBLET, c, W0_KEY) for c in cells}
    rows2, below1, below_all = {}, 0, 0
    for c in cells:
        a, o = w0s[c], {t: _val(pc, arm, t, c, W0_KEY) for t in H1}
        b1 = a is not None and a < 1.0
        ba = a is not None and all(v is not None and a < v for v in o.values())
        below1, below_all = below1 + b1, below_all + ba
        rows2[str(c)] = {"Sublet": a, "others": o, "below_1": b1, "below_all": ba}
    med2 = statistics.median([w0s[c] for c in cells]) if cells and all(w0s[c] is not None for c in cells) else None
    h2 = {"set": list(H1), "cells": rows2, "n_cells": n, "cells_below_1": below1, "cells_below_set": below_all,
          "median_W0": med2, "min_W0": min((v for v in w0s.values() if v is not None), default=None),
          "max_W0": max((v for v in w0s.values() if v is not None), default=None),
          "holds": (below1 == n and below_all == n and med2 is not None and med2 <= H2_MEDIAN) if _evaluated(n)
          else None}
    rows3, below_b, per = {}, 0, {t: 0 for t in H2B}
    for c in cells:
        a, o = w0s[c], {t: _val(pc, arm, t, c, W0_KEY) for t in H2B}
        bt = {t: a is not None and v is not None and a < v for t, v in o.items()}
        for t, x in bt.items():
            per[t] += x
        below_b += all(bt.values())
        rows3[str(c)] = {"Sublet": a, "others": o, "below": bt, "below_all": all(bt.values())}
    h2b = {"set": list(H2B), "cells": rows3, "n_cells": n, "cells_below_set": below_b, "cells_below_per_tag": per,
           "holds": (below_b == n) if _evaluated(n) else None}
    out = {"thresholds": {"H1_wins": H1_WINS, "H1_median_margin": H1_MARGIN, "H2_median_W0": H2_MEDIAN,
                          "n_cells": N_CRITERIA_CELLS},
           "H1": h1, "H2": h2, "H2b": h2b}
    if note:
        out["note"] = note
    return out


def instances(s: dict) -> dict:
    """{arm: {cell: supply by source, Gamma, BL0a, n_instance_hashes, median b per source}} from the part summary."""
    out = {}
    for arm, by_c in (s.get("instances") or {}).items():
        for ck, x in sorted(by_c.items(), key=lambda kv: int(str(kv[0]).lstrip("k"))):
            f = x.get("facts") or {}
            bs: dict = {}
            for e in (f.get("lenders") or {}).values():
                if e.get("b") is not None:
                    bs.setdefault(e.get("kind"), []).append(float(e["b"]))
            out.setdefault(arm, {})[str(int(str(ck).lstrip("k")))] = {
                "supply_gpus": f.get("supply_gpus"), "gamma": f.get("gamma"), "C0_from": f.get("C0_from"),
                "bl0a_usd": (x.get("references") or {}).get("bl0a_usd"),
                "n_instance_hashes": x.get("n_instance_hashes"), "b_median": {k: float(statistics.median(v)) for k, v in sorted(bs.items())},
                "n_lenders": {k: len(v) for k, v in sorted(bs.items())}}
    return out


def analyse(d: dict) -> dict:
    folds = {f: analyse_fold(s, d["conf"]) for f, s in d["parts"].items() if isinstance(s, dict)}
    return {"analysis": "e7o (design/ms7/plan.md §3 X2; design/ms7/feasibility/oos.md §3; C55)",
            "script": "code/sim/sublet/experiments/e7o_analysis.py", "git_revision": mc.git_revision(),
            "inputs": d["inputs"],
            "folds_found": sorted(folds), "folds_missing": [f for f in FOLDS if f not in folds],
            "h1_set": list(H1), "modes": list(MODES), "stress_modes": list(STRESS), "folds": folds}


def _f(x) -> str:
    return "-" if x is None else f"{x:.{DIGITS}f}"


def markdown(a: dict) -> str:
    """analysis.md: per fold the OOS minus IS summary, Sublet against the cheapest H1 baseline, the medians of r0 and
    W0 per arm, and the violations and reclaims per lender source."""
    L = ["# E7o analysis (design/ms7/plan.md §3 X2; no p-values)", "",
         f"Folds found: {', '.join(a['folds_found']) or 'none'}; missing: {', '.join(a['folds_missing']) or 'none'}.",
         ""]
    for f in a["folds_found"]:
        x = a["folds"][f]
        L += [f"## Fold {f} ({len(x['cells'])} cells; reduced {x['meta'].get('reduced')})", ""]
        rows = [[t, k, s["n"], s["n_neg"], s["n_zero"], s["n_pos"], s["n_missing"], _f(s["median"]), _f(s["min"]),
                 _f(s["max"])] for t in x["tags"] for k, s in x["oos_minus_is_summary"].get(t, {}).items()
                if k in (TRACE, VR, HON, W0_KEY)]
        L += ["### OOS minus IS (r0; W0)", "",
              mc.md_table(["tag", "mode", "n", "neg", "zero", "pos", "missing", "median", "min", "max"], rows), ""]
        rows = [[arm, k, s["n"], s["n_sublet_cheaper"], s["n_equal"], s["n_sublet_dearer"], s["n_missing"],
                 _f(s["median"]), _f(s["min"]), _f(s["max"])]
                for arm, by_k in x["sublet_vs_h1_summary"].items() for k, s in by_k.items()]
        L += ["### Sublet minus the cheapest H1 baseline per cell", "",
              mc.md_table(["arm", "mode", "n", "Sublet cheaper", "equal", "Sublet dearer", "missing", "median", "min",
                           "max"], rows), ""]
        rows = []
        for arm in ARMS:
            cr = x["criteria"][arm]
            for m, h in cr["H1"].items():
                rows.append([arm, f"H1 ({m})", f"{h['wins']} of {h['n_cells']} cells won, {h['n_loss_cells']} lost "
                             f"by a missing run", f"median margin {_f(h['median_margin'])} (min {_f(h['min_margin'])}, "
                             f"max {_f(h['max_margin'])})", h["holds"]])
            h = cr["H2"]
            rows.append([arm, "H2", f"{h['cells_below_1']} of {h['n_cells']} below 1, {h['cells_below_set']} below "
                         "the set", f"median W0 {_f(h['median_W0'])} (min {_f(h['min_W0'])}, max {_f(h['max_W0'])})",
                         h["holds"]])
            h = cr["H2b"]
            rows.append([arm, "H2b", f"{h['cells_below_set']} of {h['n_cells']} below the set",
                         ", ".join(f"{t} {v}" for t, v in h["cells_below_per_tag"].items()), h["holds"]])
        L += ["### The confirmation's rules on the cells (descriptive; thresholds of ms5b_analysis)", "",
              mc.md_table(["arm", "rule", "counts", "values", "holds"], rows), ""]
        rows = [[arm, t] + [_f(x["stats"][arm][t][k]["median"]) for k in (TRACE, VR, HON, W0_KEY)]
                for arm in ARMS for t in x["tags"]]
        L += ["### Median over the cells", "", mc.md_table(["arm", "tag", "r0 L-tr", "r0 L-vr", "r0 L-hon", "W0"],
                                                          rows), ""]
        rows = [[arm, t] + [_f(x["stats_rc"][arm][t][m]["median"]) for m in RC_MODES]
                for arm in ARMS for t in x["tags"]]
        L += ["### Median RC over the cells (r0 - r0 under L-hon)", "",
              mc.md_table(["arm", "tag"] + list(RC_MODES), rows), ""]
        rows = [[arm, t, m] + [x["sources_total"][arm][t][m][k][fld] for k in SOURCES for fld in SOURCE_FIELDS]
                + [x["sources_total"][arm][t][m]["n_cells_missing"]]
                for arm in ARMS for t in x["tags"] for m in SOURCE_MODES]
        L += ["### Violations and reclaims per lender source (sums over the cells)", "",
              mc.md_table(["arm", "tag", "mode"] + [f"{k} {fld}" for k in SOURCES for fld in SOURCE_FIELDS]
                          + ["cells missing"], rows), ""]
    return "\n".join(L) + "\n"


def write(a: dict, out: Path) -> tuple:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pj, pm = out / "analysis.json", out / "analysis.md"
    pj.write_text(json.dumps(mc.jsonable(a), indent=1, sort_keys=True) + "\n")
    pm.write_text(markdown(a))
    return pj, pm


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.e7o_analysis", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="folder whose out/ holds e7o/ (default MS3_ROOT or code/sim)")
    ap.add_argument("--out", type=Path, default=None, help="where analysis.json and analysis.md go "
                                                           "(default <root>/out/e7o)")
    a = ap.parse_args(argv)
    d = load(a.root)
    res = analyse(d)
    pj, pm = write(res, a.out if a.out is not None else mc.ms3_root(a.root) / "out" / EXP)
    print(f"[e7o_analysis] folds {res['folds_found']} (missing {res['folds_missing']}): wrote {pj} and {pm}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
