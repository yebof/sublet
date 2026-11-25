"""sf_oos: the out-of-sample folds, the trace lenders calibrated on one window of the MaaS trace week and evaluated on
the other, with the tables oos_margins.tex, oos_rules.tex, oos_policies.tex, oos_sources.tex and the data file
oos_runs.csv (design/ms7/registration.md §2-§3, X2; design/ms7/w_spec.md §4, unit W-G4; design/ms7/plan.md X2;
change C58).

Question: does Sublet's ordering hold when the lenders are calibrated out of sample? Every number is read from the
registered analysis code/sim/out/e7o/analysis.json (sublet/experiments/e7o_analysis.py, its sha256 in
design/ms7/registration.md): per fold (fwd, rev), arm (oos: the MaaS lenders calibrated on the fold's other days of
the trace week and the spot lenders on the first weeks of their series, e7o.SPOT_CALIB; is: the in-sample twin on the
same cells, demand and Gamma, every lender calibrated on its whole series, the evaluated window included; the
captions say so, arms_text, as the review of W-G4 A corrected), tag and cell, r0 under the eight lenders, W0, RC, the
lender-source counts, OOS minus IS, Sublet minus the cheapest primary baseline, the confirmation's rules applied to
the cells, the instances and the bridge to the confirmation. The analysis's per-cell comparisons are recomputed from
its per-cell r0 (StyleError: a stale input), and folds of full runs must hold the design's 16 cells and 15 tags
(check_design; review of W-G4 A). The statistics are descriptive (registration §3; design/ms7/plan.md D4):
sign counts, medians, min and max over the cells; no p-value. Margins are printed in the confirmation's convention
(the cheapest primary baseline minus Sublet, positive when Sublet costs less; the analysis's sublet_vs_h1 holds
Sublet minus the cheapest, its sign reversed here; a missing run is a loss).

Figure (W2 x 2.5 in; block A of style.SUPP_POLICIES_MS7). Legend row, keying every panel: the two folds (filled
diamond: forward; open circle: reverse), with the MaaS days each calibrates on and is evaluated on
(sublet.experiments.e7o.FOLDS; C62: the evaluated days added).
(a) Per cell, two sub-panels on one cell axis, the out-of-sample arm: "Cost margin", the least L-tr r0 over the
    primary baselines minus Sublet's; "W0 margin", the same on W0 (the largest r0 over the five stress lenders); each
    fold a series. A cell with a negative or missing margin of a sub-panel's series is shaded in that sub-panel.
(b) Per policy of the figure's set (Sublet, critical-ratio renting and the seven primary baselines; one row each, its
    registry label on the y axis; a grey line between Sublet and critical-ratio renting and the primary baselines,
    C62), out of sample minus in sample of the L-tr r0 per cell: the median over the cells (marker) and the min-max
    (bar), per fold; the grey line at 0 marks no change, named above the axes.
(c) The same for W0, sharing (b)'s rows.

Tables (after hook, figs.common.write_table; from the extract's `tables`, so --from-extract rewrites them; each with
its scope; one-column longtables):
  oos_margins.tex   per lender (the eight and W0), fold and arm: the margin of Sublet over the cheapest primary
                    baseline per cell, its wins, ties, losses and missing cells, median, min and max
  oos_rules.tex     the confirmation's rules (the trace cost under L-tr and L-vr, W0 against the primary baselines,
                    W0 against the notice-aware set) per fold and arm, as the analysis applies them to the cells, with
                    their thresholds (read from the analysis)
  oos_policies.tex  per fold and tag (all fifteen), the out-of-sample r0 under L-tr and L-vr, W0 and RC under L-tr
                    (median, [min, max] over the cells), and out of sample minus in sample of r0 under L-tr and L-vr
                    and of W0 with its sign counts (cells below, at and above 0); a dagger marks a median over fewer
                    cells (a missing run; ms7_a_lib.fewer_mark); the other lenders' r0 per tag and cell, and the
                    in-sample values, are in oos_runs.csv
  oos_sources.tex   per tag and lender source (MaaS, spot), fold, arm and lender (L-tr, L-vr), the sums over the cells
                    of the buffer-violation slots, those with a positive attributable deficit, the reclaims and the
                    violation cuts of the run's leases
  oos_runs.csv      one line per fold, arm, tag and cell: r0 under each lender, W0 and its lender, r0 minus the
                    confirmation's at the cell's config seed (the bridge), the source counts under L-tr and L-vr and
                    the instance (BL0a, supply per source, Gamma, the lenders' median b); the extract keeps its lines
                    and sha256
labels.caption is a caption draft (no design names; every count read from the inputs).

RUN_INPUTS is the run output of X2; figs/rebuild.py keeps the entry pending until it is copied in. A missing input
stops the script with exit code 2 and the file named; data from a reduced run is never written into
paper/supplement/ or code/sim/out/figs/ (ms7_a_lib.guard_reduced). Run from code/sim:
python -m figs.supp.sf_oos [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

from figs import style
from figs.common import MissingKey, need, write_table
from figs.inputs import Inputs
from figs.supp import ms5b_e7_lib as L
from figs.supp import ms7_a_lib as A
from sublet.experiments import e7o

NAME = "sf_oos"
KEYS = style.SUPP_POLICIES_MS7[NAME]
E7O = "code/sim/out/e7o/analysis.json"
RUN_INPUTS = (E7O,)                   # the MS7 run output this figure needs (figs/rebuild.py)
INPUTS = (E7O,)
TABLES = ("oos_margins.tex", "oos_rules.tex", "oos_policies.tex", "oos_sources.tex", "oos_runs.csv")
RUNS_CSV = TABLES[-1]
SEED = 0
FOLDS = ("fwd", "rev")
ARMS = ("oos", "is")
W0 = "W0"
SUBLET = "Sublet"
TRACE, VR, HON = "L-tr", "L-vr", "L-hon"
SOURCE_MODES = (TRACE, VR)
SOURCES = ("maas", "spot")
SOURCE_FIELDS = ("violation_slots", "violation_slots_attributable", "reclaims", "violation_cuts")
FOLD_LABEL = {"fwd": "Forward fold", "rev": "Reverse fold"}
FOLD_SHORT = {"fwd": "Forward", "rev": "Reverse"}
ARM_LABEL = dict(style.ENV_LABELS["calibration"])          # oos: "Out of sample", is: "In sample"
SOURCE_LABEL = {"maas": "MaaS", "spot": "Spot"}
SERIES = {"fwd_r0": "c", "rev_r0": "d", "fwd_W0": "c", "rev_W0": "d", "fwd": "c", "rev": "d"}
AXES_RATIOS = (1.55, 1.0, 1.0)        # (a), (b), (c): shares of the width left after the reserves
LABELS = {"a_x": "Cell", "a_y": {"cost": "Cost margin", "w0": "$W_0$ margin"},
          "b_x": "Δ trace cost (out − in sample)", "c_x": "Δ$W_0$ (out − in sample)", "zero": "No change"}
NAME_IN = 1.3                         # the tables' name column (in)
NAME_FIT_IN = 1.1                     # name_cells splits a label wider than this (its estimate drops math glyphs)
style.register_supplementary(NAME, "W2", 2.5)


def key_of(tag: str) -> str:
    try:
        return L.KEY_OF_TAG[tag]
    except KeyError:
        raise style.StyleError(f"{NAME}: no registry key for tag {tag!r}") from None


def label_of(tag: str) -> str:
    return style.POLICIES[key_of(tag)].label


def days(fold: str) -> dict:
    f = e7o.FOLDS[fold]
    return {"calib": f["calib_days"].replace("-", "–"), "eval": f["eval_days"].replace("-", "–")}


def spot_window() -> dict:
    """The spot lenders' windows, the same in both folds (sublet.experiments.e7o: SPOT_CALIB, SPOT_BLOCK_SLOTS): the
    out-of-sample arm calibrates them on the first weeks of their series and every cell evaluates them on one block of
    this many hours after those weeks (review of W-G4 A: the captions named only the MaaS days)."""
    lo, hi = e7o.SPOT_CALIB
    w = e7o.SLACK_SLOTS_PER_WEEK
    if lo % w or hi % w:
        raise style.StyleError(f"e7o.SPOT_CALIB {e7o.SPOT_CALIB} is not a whole number of weeks")
    return {"calib_weeks": f"{lo // w + 1}–{hi // w}", "block_h": round(e7o.SPOT_BLOCK_SLOTS * 7 * 24 / w)}


def arms_text(d: Mapping, tex: bool) -> str:
    """The folds and arms in words, one sentence (captions; review of W-G4 A): which window each kind of trace lender
    is calibrated and evaluated on, and the in-sample twin, which calibrates every lender on its whole series
    (e7o.ARMS: 'is' has no calib_slots), the evaluated window included, on the same cell and demand. `tex`: '--' for
    the en dash."""
    dy, sp = d["labels"]["days"], d["labels"]["spot"]

    def r(s: str) -> str:
        return s.replace("–", "--") if tex else s
    return (f"Forward fold: the MaaS lenders calibrated on days {r(dy['fwd']['calib'])} of the trace week and "
            f"evaluated on days {r(dy['fwd']['eval'])}; reverse fold: calibrated on days {r(dy['rev']['calib'])} and "
            f"evaluated on days {r(dy['rev']['eval'])}; in both folds, the spot lenders calibrated on weeks "
            f"{r(sp['calib_weeks'])} of their series and evaluated on a {sp['block_h']}-h block after them; in sample: "
            f"the same cell and demand, with every lender calibrated on its whole series, the evaluated window "
            f"included.")


# ---------------------------------------------------------------------------------------------------------------
# inputs and checks
def _cell_val(pc: Mapping, arm: str, tag: str, cell: str, key: str):
    x = ((pc.get(arm) or {}).get(tag) or {}).get(cell) or {}
    v = x.get(W0) if key == W0 else (x.get("r0") or {}).get(key)
    return None if v is None else float(v)


def folds_of(an: Mapping) -> dict:
    found = list(need(an, "folds_found", what=E7O))
    missing = [f for f in FOLDS if f not in found]
    if missing:
        raise MissingKey(f"{E7O}: no fold {missing} (folds found {found})")
    return {f: an["folds"][f] for f in FOLDS}


def tag_order(an: Mapping, x: Mapping) -> tuple[list[str], list[int]]:
    """The tables' rows: Sublet and the other policies outside both sets (critical-ratio renting, critical-ratio
    planning, ...), the notice-aware set, the primary baselines; with the indices where a group starts."""
    tags = list(x["tags"])
    h1 = list(need(an, "h1_set", what=E7O))
    notice = list(need(x, "criteria", "oos", "H2b", "set", what=E7O))
    rest = [t for t in tags if t not in h1 and t not in notice]
    rows = rest + [t for t in notice if t in tags] + [t for t in h1 if t in tags]
    if sorted(rows) != sorted(tags) or rows[0] != SUBLET:
        raise style.StyleError(f"{E7O}: tags {tags} do not hold Sublet first")
    for t in rows:
        key_of(t)
    return rows, [len(rest), len(rest) + len([t for t in notice if t in tags])]


def check(an: Mapping, folds: Mapping) -> None:
    """The analysis's per-cell comparisons against its per-cell r0 (StyleError: a stale input): Sublet minus the
    cheapest primary baseline and OOS minus IS, every arm, tag, lender, W0 and cell, exactly; the figure's tags are in
    every fold."""
    h1 = list(an["h1_set"])
    bad = []
    fig_tags = [L.TAG_OF_KEY[k] for k in KEYS]
    for f, x in folds.items():
        pc, cells = x["per_cell"], [str(c) for c in x["cells"]]
        lack = [t for t in fig_tags if t not in x["tags"]]
        if lack:
            raise style.StyleError(f"{E7O}: fold {f} lacks the figure's tags {lack}")
        keys = list(an["modes"]) + [W0]
        for arm in ARMS:
            for k in keys:
                for c in cells:
                    sv = _cell_val(pc, arm, SUBLET, c, k)
                    hv = [_cell_val(pc, arm, h, c, k) for h in h1]
                    want = None if sv is None or any(v is None for v in hv) else sv - min(hv)
                    got = (((x.get("sublet_vs_h1") or {}).get(arm) or {}).get(k) or {}).get(c, {}).get("d")
                    if not (want is None and got is None) and (want is None or got is None or want != float(got)):
                        bad.append(f"{f} {arm} {k} cell {c}: Sublet minus the cheapest")
        for t in x["tags"]:
            for k in keys:
                for c in cells:
                    a, b = _cell_val(pc, "oos", t, c, k), _cell_val(pc, "is", t, c, k)
                    want = None if a is None or b is None else a - b
                    got = x["oos_minus_is"][t][k][c]
                    if not (want is None and got is None) and (want is None or got is None or want != float(got)):
                        bad.append(f"{f} {t} {k} cell {c}: OOS minus IS")
    if bad:
        raise style.StyleError(f"{NAME}: {E7O} is not consistent with its per-cell r0 (stale input): {bad[:6]}")


def check_design(folds: Mapping) -> None:
    """Folds of full runs must hold the design's cells and tags (sublet.experiments.e7o: cells 0..N_CELLS-1, the 15
    tags of TAGS; review of W-G4 A): StyleError otherwise, so that a partial analysis is not printed as the result.
    Reduced folds pass (their figures never reach the versioned folders)."""
    bad = []
    for f, x in folds.items():
        if (x.get("meta") or {}).get("reduced"):
            continue
        if [int(c) for c in x["cells"]] != list(range(e7o.N_CELLS)):
            bad.append(f"fold {f}: cells {x['cells']}")
        if sorted(x["tags"]) != sorted(e7o.TAGS):
            bad.append(f"fold {f}: tags {x['tags']}")
    if bad:
        raise style.StyleError(f"{NAME}: {E7O} is not the full design of sublet/experiments/e7o.py ({'; '.join(bad)})")


# ---------------------------------------------------------------------------------------------------------------
# the figure's data
def _margin(x: Mapping, arm: str, k: str, c: str):
    d = (((x.get("sublet_vs_h1") or {}).get(arm) or {}).get(k) or {}).get(c, {}).get("d")
    return None if d is None else -float(d)


def panel_a(folds: Mapping) -> dict:
    cells = sorted({int(c) for x in folds.values() for c in x["cells"]})
    a: dict[str, Any] = {"x": cells, "cells": [str(c) for c in cells],
                         "subpanels": [["cost", ["fwd_r0", "rev_r0"]], ["w0", ["fwd_W0", "rev_W0"]]]}
    for f, x in folds.items():
        a[f"{f}_r0"] = [_margin(x, "oos", TRACE, str(c)) for c in cells]
        a[f"{f}_W0"] = [_margin(x, "oos", W0, str(c)) for c in cells]
    a["shaded"] = {name: A.flagged_columns(a["x"], a, keys) for name, keys in a["subpanels"]}
    a["missing"] = {k: [str(c) for c, v in zip(cells, a[k]) if v is None] for _, ks in a["subpanels"] for k in ks}
    return a


def _stat(d: Mapping | None) -> dict:
    d = d or {}
    return {k: d.get(k) for k in ("n", "n_missing", "median", "min", "max", "n_neg", "n_zero", "n_pos") if k in d}


def panel_rows(folds: Mapping, k: str) -> list[dict]:
    out = []
    for key in KEYS:
        t = L.TAG_OF_KEY[key]
        out.append({"key": key, "tag": t, **{f: _stat(x["oos_minus_is_summary"][t][k]) for f, x in folds.items()}})
    return out


# ---------------------------------------------------------------------------------------------------------------
# tables
def margins_table(an: Mapping, folds: Mapping) -> dict:
    keys = list(an["modes"]) + [W0]
    cols = []
    for f, x in folds.items():
        cells = [str(c) for c in x["cells"]]
        for arm in ARMS:
            by = {}
            for k in keys:
                ms = [_margin(x, arm, k, c) for c in cells]
                s = A.signs(ms)
                by[k] = {"wins": s["n_pos"], "ties": s["n_zero"], "losses": s["n_neg"], "lost": s["n_missing"],
                         "median": s["median"], "min": s["min"], "max": s["max"], "n_cells": len(cells),
                         "cells": dict(zip(cells, ms))}
            cols.append({"fold": f, "arm": arm, "by": by})
    return {"lenders": keys, "columns": cols, "set": list(an["h1_set"]),
            "scope": {"tags": [SUBLET] + list(an["h1_set"]), "modes": list(an["modes"]), "folds": list(folds),
                      "arms": list(ARMS), "cells": sorted({str(c) for x in folds.values() for c in x["cells"]},
                                                          key=int)}}


def rules_table(folds: Mapping) -> dict:
    cols = []
    thresholds = None
    for f, x in folds.items():
        for arm in ARMS:
            cr = x["criteria"][arm]
            thresholds = thresholds or cr["thresholds"]
            if cr["thresholds"] != thresholds:
                raise style.StyleError(f"{E7O}: the rules' thresholds differ between folds or arms")
            h1 = {m: {k: cr["H1"][m].get(k) for k in ("n_cells", "wins", "n_loss_cells", "median_margin", "min_margin",
                                                       "max_margin", "holds")} for m in cr["H1"]}
            h2 = {k: cr["H2"].get(k) for k in ("n_cells", "cells_below_1", "cells_below_set", "median_W0", "min_W0",
                                               "max_W0", "holds")}
            h2b = {"n_cells": cr["H2b"]["n_cells"], "cells_below_set": cr["H2b"]["cells_below_set"],
                   "per_tag": [[t, cr["H2b"]["cells_below_per_tag"][t]] for t in cr["H2b"]["set"]],
                   "holds": cr["H2b"]["holds"]}
            cols.append({"fold": f, "arm": arm, "cost": h1, "worst": h2, "notice": h2b, "note": cr.get("note")})
    any_x = next(iter(folds.values()))
    return {"thresholds": thresholds, "cost_modes": list(any_x["criteria"]["oos"]["H1"]),
            "set": list(any_x["criteria"]["oos"]["H2"]["set"]),
            "notice_set": list(any_x["criteria"]["oos"]["H2b"]["set"]),
            "columns": cols, "scope": {"tags": [SUBLET] + list(any_x["criteria"]["oos"]["H2"]["set"])
                                       + list(any_x["criteria"]["oos"]["H2b"]["set"]),
                                       "modes": list(any_x["criteria"]["oos"]["H1"]), "folds": list(folds),
                                       "arms": list(ARMS)}}


POLICY_COLS = (("r0", "oos", TRACE), ("r0", "oos", VR), ("r0", "oos", W0), ("rc", "oos", TRACE), ("d", None, TRACE),
               ("d", None, VR), ("d", None, W0))


def policies_table(folds: Mapping, rows: Sequence[str], seps: Sequence[int], modes: Sequence[str]) -> dict:
    blocks = []
    for f, x in folds.items():
        out = []
        for t in rows:
            cells = []
            for kind, arm, k in POLICY_COLS:
                if kind == "r0":
                    cells.append(_stat(x["stats"][arm][t][k]))
                elif kind == "rc":
                    cells.append(_stat(x["stats_rc"][arm][t][k]))
                else:
                    cells.append(_stat(x["oos_minus_is_summary"][t][k]))
            out.append({"tag": t, "key": key_of(t), "label": label_of(t), "cells": cells})
        blocks.append({"fold": f, "n_cells": len(x["cells"]), "rows": out})
    return {"columns": [list(c) for c in POLICY_COLS], "blocks": blocks, "separators": list(seps),
            "scope": {"tags": list(rows), "modes": [TRACE, VR, HON], "folds": list(folds), "arms": list(ARMS),
                      "W0_modes": [m for m in modes if m not in (TRACE, VR, HON)]}}


def sources_table(folds: Mapping, rows: Sequence[str], seps: Sequence[int]) -> dict:
    out = []
    for t in rows:
        r = {"tag": t, "key": key_of(t), "label": label_of(t), "cells": {}}
        for f, x in folds.items():
            for arm in ARMS:
                for m in SOURCE_MODES:
                    st = x["sources_total"][arm][t][m]
                    r["cells"][f"{f}|{arm}|{m}"] = {"n_cells_missing": st["n_cells_missing"],
                                                    **{s: [st[s][fld] for fld in SOURCE_FIELDS] for s in SOURCES}}
        out.append(r)
    return {"rows": out, "groups": [[f, arm, m] for f in folds for arm in ARMS for m in SOURCE_MODES],
            "separators": list(seps), "fields": list(SOURCE_FIELDS),
            "scope": {"tags": list(rows), "modes": list(SOURCE_MODES), "folds": list(folds), "arms": list(ARMS)}}


def runs_columns(modes: Sequence[str]) -> list[str]:
    return (["fold", "arm", "policy", "tag", "cell", "policy_seed"] + [f"r0_{m}" for m in modes] + ["W0", "W0_lender"]
            + [f"r0_minus_confirmation_{m}" for m in modes]
            + [f"{m}_{s}_{fld}" for m in SOURCE_MODES for s in SOURCES for fld in SOURCE_FIELDS]
            + ["bl0a_usd", "supply_maas_gpus", "supply_spot_gpus", "supply_protected_gpus", "gamma", "c0_from",
               "b_median_maas", "b_median_spot", "n_lenders_maas", "n_lenders_spot", "n_instance_hashes"])


def runs_entry(an: Mapping, folds: Mapping, rows: Sequence[str]) -> dict:
    modes = list(an["modes"])
    out = []
    for f, x in folds.items():
        for arm in ARMS:
            for t in rows:
                for c in [str(c) for c in x["cells"]]:
                    e = x["per_cell"][arm][t][c]
                    br = x["bridge"][arm][t]
                    src = e.get("sources") or {}
                    ins = (x.get("instances") or {}).get(arm, {}).get(c) or {}
                    sup, bm, nl = ins.get("supply_gpus") or {}, ins.get("b_median") or {}, ins.get("n_lenders") or {}
                    out.append([f, arm, L.plain_label(label_of(t)), t, c, SEED]
                               + [A.csv_num(e["r0"].get(m)) for m in modes] + [A.csv_num(e.get(W0)),
                                                                               e.get("W0_mode") or ""]
                               + [A.csv_num(br[m].get(c)) for m in modes]
                               + [("" if (src.get(m) or {}).get(s, {}).get(fld) is None else
                                   int(src[m][s][fld])) for m in SOURCE_MODES for s in SOURCES for fld in SOURCE_FIELDS]
                               + [A.csv_num(ins.get("bl0a_usd"), ".2f"), A.csv_num(sup.get("maas"), ".1f"),
                                  A.csv_num(sup.get("spot"), ".1f"), A.csv_num(sup.get("protected"), ".1f"),
                                  A.csv_num(ins.get("gamma"), ".6g"), ins.get("C0_from") or "",
                                  A.csv_num(bm.get("maas")), A.csv_num(bm.get("spot")),
                                  "" if nl.get("maas") is None else int(nl["maas"]),
                                  "" if nl.get("spot") is None else int(nl["spot"]),
                                  "" if ins.get("n_instance_hashes") is None else int(ins["n_instance_hashes"])])
    cells = sorted({str(c) for x in folds.values() for c in x["cells"]}, key=int)
    return A.csv_entry(RUNS_CSV, runs_columns(modes), out, {"tags": list(rows), "modes": modes, "folds": list(folds),
                                                            "arms": list(ARMS), "cells": cells, "seeds": [SEED]})


# ---------------------------------------------------------------------------------------------------------------
def caption_values(d: Mapping) -> dict:
    """The numbers of the caption draft, each read from the inputs (labels.caption_values; the integrator's \\val
    entries): the cells, the cells in which Sublet's out-of-sample cost and W0 are below every primary baseline per
    fold, the folds' windows (days of the trace week), the spot lenders' calibration weeks and evaluation block (hours)
    and the cells with a missing run."""
    a = d["a"]
    return {"n_cells": len(a["cells"]),
            **{f"wins_{k}_{f}": sum(1 for v in a[f"{f}_{m}"] if v is not None and v > 0)
               for f in FOLDS for k, m in (("cost", "r0"), ("w0", "W0"))},
            "days": d["labels"]["days"], "spot": d["labels"]["spot"],
            "missing_cells": sorted({c for v in a["missing"].values() for c in v}, key=int)}


def caption(d: Mapping, v: Mapping) -> str:
    """The caption draft: no design names; every count from caption_values."""
    n, miss = v["n_cells"], v["missing_cells"]
    lost = (f" A run is missing in cell{'s' if len(miss) > 1 else ''} {', '.join(miss)}: a loss for Sublet."
            if miss else "")
    return (f"Lenders calibrated out of sample on {n} cell{'s' if n != 1 else ''} per fold (policy seed 0). "
            f"{arms_text(d, tex=False)} (a) Per cell, out of sample, the least primary baseline minus Sublet on the "
            f"trace cost and on W0 (positive: Sublet costs less; shaded: a negative or missing margin); Sublet's cost "
            f"is below every primary baseline in {v['wins_cost_fwd']} (forward) and {v['wins_cost_rev']} (reverse) "
            f"of {n} cells. (b) Trace cost and (c) W0 of Sublet, critical-ratio renting and each primary baseline, "
            f"out of sample minus in sample: median over the cells (marker) and min-max (bar); grey: no change.{lost}")


def build(inp: Inputs) -> dict:
    an = A.read_json(inp, E7O, RUN_INPUTS, NAME)
    folds = folds_of(an)
    check(an, folds)
    check_design(folds)
    x0 = folds[FOLDS[0]]
    rows, seps = tag_order(an, x0)
    for f, x in folds.items():
        if tag_order(an, x)[0] != rows:
            raise style.StyleError(f"{E7O}: fold {f}'s tags differ from fold {FOLDS[0]}'s")
    tables = {"oos_margins": margins_table(an, folds), "oos_rules": rules_table(folds),
              "oos_policies": policies_table(folds, rows, seps, an["modes"]),
              "oos_sources": sources_table(folds, rows, seps),
              "oos_runs": runs_entry(an, folds, rows)}
    metas = {f: x.get("meta") or {} for f, x in folds.items()}
    reduced = {f: bool(m.get("reduced")) for f, m in metas.items()}
    dy = {f: days(f) for f in FOLDS}
    legend = [[SERIES[f], f"{FOLD_LABEL[f]}: calibrated on days {dy[f]['calib']}, evaluated on days "
                          f"{dy[f]['eval']}", True] for f in FOLDS]
    data = {"keys": list(KEYS), "rows": list(KEYS), "tags": rows, "fig_tags": [L.TAG_OF_KEY[k] for k in KEYS],
            "a": panel_a(folds), "b": panel_rows(folds, TRACE), "c": panel_rows(folds, W0), "series": dict(SERIES),
            "legend": legend, "labels": {**LABELS, "days": dy, "spot": spot_window(), "folds": dict(FOLD_LABEL),
                                         "arms": ARM_LABEL},
            "tables": tables,
            "meta": {"git_revision": {"analysis": an.get("git_revision"),
                                      **{f: m.get("git_revision") for f, m in metas.items()}},
                     "reduced": any(reduced.values()), "reduced_by_fold": reduced, "folds": list(FOLDS),
                     "modes": list(an["modes"]), "inputs": an.get("inputs")}}
    data["labels"]["caption_values"] = caption_values(data)
    data["labels"]["caption"] = caption(data, data["labels"]["caption_values"])
    data["meta"]["sources"] = list(inp.sources)
    return data


# ---------------------------------------------------------------------------------------------------------------
def separators(data: Mapping) -> list[int]:
    """The row before which a grey line goes: the first primary baseline (after Sublet and critical-ratio renting)."""
    h1 = set(data["tables"]["oos_margins"]["set"])
    return [i for i, r in enumerate(data["b"]) if r["tag"] in h1][:1]


def draw(data: Mapping) -> Any:
    fig = style.new_figure(NAME)
    lab = data["labels"]
    names = [style.POLICIES[k].label for k in data["rows"]]
    room = A.key_room_in([])                 # the room of "No change" (a key's text) above (b)'s axes
    ax_a, ax_b, ax_c = style.panel_row(fig, AXES_RATIOS, top=style.MARGIN_TOP + style.LEGEND_ROW + room,
                                       sharey=[False, False, True],
                                       left=[A.margins_reserve(fig, data["a"]), A.names_reserve(fig, names),
                                             style.LEFT_SHARED])
    leg = style.legend_row(fig, [], extra=A.handles([tuple(e) for e in data["legend"]]))
    subs = A.split_rows(fig, ax_a, 2)
    A.draw_margins(subs, data["a"], data["series"], lab["a_y"], lab["a_x"])
    seps = separators(data)
    for ax, rows, xl, nm in ((ax_b, data["b"], lab["b_x"], names), (ax_c, data["c"], lab["c_x"], None)):
        ax.set_xlim(*A.row_limits(rows, FOLDS, 0.0))
        A.draw_rows(ax, rows, FOLDS, data["series"], ref=0.0, xlabel=xl, names=nm, separators=seps)
    A.align_xlabels([subs[-1], ax_b, ax_c])
    letters = style.panel_letters([subs[0], ax_b, ax_c])
    A.letter_keys(fig, letters, {}, room)    # the letters back to their height above axes placed without the room
    A.line_label(ax_b, 0.0, lab["zero"], letters[1], avoid=list(letters) + list(leg.get_texts()))
    fig._sublet_panels = {"a": subs, "b": ax_b, "c": ax_c}
    return fig


# ---------------------------------------------------------------------------------------------------------------
# LaTeX
def _cells_text(d: Mapping) -> str:
    cs = d["a"]["cells"]
    many = len(cs) != 1
    return f"{len(cs)} cell{'s' if many else ''} (cell{'s' if many else ''} " + L.week_span(cs) + "; policy seed 0)"


def _span_head(groups: Sequence[str], width: int, first: int) -> str:
    """A head line of spanning group names, `width` columns each after `first` columns, with their rules."""
    cells = [""] * first + [r"\multicolumn{" + f"{width}" + r"}{c}{" + g + "}" for g in groups]
    rules = "".join(r"\cmidrule(lr){" + f"{first + 1 + i * width}-{first + (i + 1) * width}" + "}"
                    for i in range(len(groups)))
    return " & ".join(cells) + r" \\" + "\n" + rules


def _count(s: Mapping) -> str:
    return f"{s['wins']}/{s['ties']}/{s['losses']}/{s['lost']}"


def margins_tex(t: Mapping, d: Mapping) -> str:
    cols = t["columns"]
    body = []
    for k in t["lenders"]:
        row = ["$W_0$" if k == W0 else k]
        for c in cols:
            s = c["by"][k]
            row += [_count(s), A.num(s["median"]), A.num(s["min"]), A.num(s["max"])]
        body.append(row)
    groups = [f"{FOLD_SHORT[c['fold']]}, {ARM_LABEL[c['arm']].lower()}" for c in cols]
    cap = (r"The margin of Sublet over the primary baselines in the out-of-sample folds, per cell: the least $r_0$ "
           r"over the primary baselines minus Sublet's (positive: Sublet costs less), under each lender and on $W_0$ "
           r"(the largest $r_0$ over the five stress lenders), per fold and arm over " + _cells_text(d) + r": the "
           r"cells with a positive, zero and negative margin and those with a missing run, a loss (W/T/L/M), and the "
           r"median, minimum and maximum over the cells with a margin. The primary baselines: "
           + L.join_labels([label_of(x) for x in t["set"]]) + ". " + arms_text(d, tex=True))
    return A.longtable("@{}l" + "rrrr" * len(cols) + "@{}", cap, "tab:s-oos-margins",
                       ["Lender"] + ["W/T/L/M", "Med.", "Min", "Max"] * len(cols), body,
                       head_top=_span_head(groups, 4, 1), rules=[len(body) - 1], tabcolsep="2.0pt")


def _holds(h) -> str:
    return "not evaluated" if h is None else ("met" if h else "not met")


def _num3(v) -> str:
    return A.num(v, ".3f")


def rules_tex(t: Mapping, d: Mapping) -> str:
    th = t["thresholds"]
    n = th["n_cells"]
    cols = t["columns"]
    notice = [label_of(x) for x in t["notice_set"]]
    rules = []
    for m in t["cost_modes"]:
        rules.append((r"Cost under " + m + r": Sublet below every primary baseline in at least " + f"{th['H1_wins']}"
                      + r" of " + f"{n}" + r" cells, median margin at least " + f"{th['H1_median_margin']:g}",
                      lambda c, m=m: _cost_cell(c["cost"][m])))
    rules.append((r"$W_0$: below 1 and below every primary baseline in all " + f"{n}" + r" cells, median at most "
                  + f"{th['H2_median_W0']:g}", lambda c: _worst_cell(c["worst"])))
    rules.append((r"$W_0$ below each of " + L.join_labels([L.tex(x) for x in notice]) + r" in all " + f"{n}"
                  + r" cells (per-policy counts in this order)", lambda c: _notice_cell(c["notice"])))
    body = [[L.rag(text)] + [L.rag(fn(c)) for c in cols] for text, fn in rules]
    groups = [f"{FOLD_SHORT[c['fold']]}, {ARM_LABEL[c['arm']].lower()}" for c in cols]
    cap = (r"The confirmation's registered rules for the trace cost and the worst case, applied descriptively to the "
           r"out-of-sample folds over " + _cells_text(d) + r" with the confirmation's thresholds; a rule is evaluated "
           r"only on " + f"{n}" + r" cells. The margin is the least primary baseline minus Sublet, and a missing run "
           r"is a loss.")
    return A.longtable("@{}p{1.55in}" + "p{1.22in}" * len(cols) + "@{}", cap, "tab:s-oos-rules",
                       ["Rule"] + groups, body, rules=list(range(1, len(body))), tabcolsep="3.0pt")


def _cost_cell(h: Mapping) -> str:
    return (f"won {h['wins']} of {h['n_cells']}" + (f", {h['n_loss_cells']} lost to a missing run"
                                                    if h["n_loss_cells"] else "")
            + f"; median {_num3(h['median_margin'])} [{_num3(h['min_margin'])}, {_num3(h['max_margin'])}]; "
            + _holds(h["holds"]))


def _worst_cell(h: Mapping) -> str:
    return (f"below 1 in {h['cells_below_1']}, below the set in {h['cells_below_set']} of {h['n_cells']}; median "
            f"{_num3(h['median_W0'])} [{_num3(h['min_W0'])}, {_num3(h['max_W0'])}]; " + _holds(h["holds"]))


def _notice_cell(h: Mapping) -> str:
    return (f"below all in {h['cells_below_set']} of {h['n_cells']} ({', '.join(str(n) for _, n in h['per_tag'])}); "
            + _holds(h["holds"]))


POLICY_HEAD = ("$r_0$, L-tr", "$r_0$, L-vr", "$W_0$", "RC, L-tr", r"$\Delta r_0$, L-tr", r"$\Delta r_0$, L-vr",
               r"$\Delta W_0$")
POLICY_FMT = (".3f",) * 7


def _policy_lines(r: Mapping, cols: Sequence) -> list[list[str]]:
    top, low = [], []
    for (kind, _, _), s, fmt in zip(cols, r["cells"], POLICY_FMT):
        med = A.num(s.get("median"), fmt) + A.fewer_mark(s)      # review of W-G4 A: a statistic over fewer cells
        if kind == "d" and s.get("n"):
            med += f" ({s['n_neg']}/{s['n_zero']}/{s['n_pos']})"
        top.append(med)
        low.append(A.interval(s.get("min"), s.get("max"), fmt))
    nm = L.name_cells(L.tex(r["label"]), 2, NAME_FIT_IN)
    return [[nm[0]] + top, [nm[1]] + low]


def policies_tex(t: Mapping, d: Mapping) -> str:
    body, rules, together = [], [], []
    ncol = 1 + len(t["columns"])
    for b in t["blocks"]:
        dy = d["labels"]["days"][b["fold"]]
        head = len(body)
        rules.append(head)
        body.append([r"\multicolumn{" + f"{ncol}" + r"}{@{}l}{\emph{" + FOLD_LABEL[b["fold"]] + r": MaaS lenders "
                     r"calibrated on days " + dy["calib"].replace("–", "--") + r", evaluated on days "
                     + dy["eval"].replace("–", "--") + r"}}"])
        for i, r in enumerate(b["rows"]):
            if i in t["separators"] and i:
                rules.append(len(body))
            together.append([head if i == 0 else len(body), len(body) + 1])     # the fold's head with its first row
            body += _policy_lines(r, t["columns"])
    fewer = any(A.fewer_mark(s) for b in t["blocks"] for r in b["rows"] for s in r["cells"])
    cap = (r"Every policy in the out-of-sample folds, over " + _cells_text(d) + r": out of sample, $r_0$ under the "
           r"trace lender L-tr and under L-vr (buffer violations as reclaims without notice), $W_0$ (the largest "
           r"$r_0$ over the five stress lenders) and RC $=r_0(\mbox{L-tr})-r_0(\mbox{L-hon})$; then out of sample "
           r"minus in sample ($\Delta$) of $r_0$ under L-tr and L-vr and of $W_0$, with the cells below, at and above "
           r"zero in parentheses. First line: the median over the cells; second line: the minimum and maximum."
           + (r" $^\dagger$: over fewer cells (a missing run)." if fewer else "")
           + r" Every value per cell and lender is in the data file " + L.tex(RUNS_CSV) + ". "
           + arms_text(d, tex=True))
    return A.longtable("@{}p{" + f"{NAME_IN}in" + "}" + "r" * len(t["columns"]) + "@{}", cap, "tab:s-oos-policies",
                       ["Policy", *POLICY_HEAD], body, rules=rules, together=together, tabcolsep="2.2pt")


def _src(c: Mapping, s: str) -> str:
    v = "/".join(str(x) for x in c[s])
    return v + (r"$^\dagger$" if c["n_cells_missing"] else "")


def sources_tex(t: Mapping, d: Mapping) -> str:
    body, rules, together = [], [], []
    for i, r in enumerate(t["rows"]):
        if i in t["separators"] and i:
            rules.append(len(body))
        together.append([len(body), len(body) + len(SOURCES) - 1])
        nm = L.name_cells(L.tex(r["label"]), len(SOURCES), NAME_FIT_IN)
        for j, s in enumerate(SOURCES):
            body.append([nm[j], SOURCE_LABEL[s]] + [_src(r["cells"]["|".join(g)], s) for g in t["groups"]])
    pairs = [f"{FOLD_SHORT[f]}, {ARM_LABEL[arm].lower()}" for f, arm, m in t["groups"][::len(SOURCE_MODES)]]
    dag = any(c["n_cells_missing"] for r in t["rows"] for c in r["cells"].values())
    cap = (r"The lender-source counts of every policy in the out-of-sample folds, summed over " + _cells_text(d)
           + r": the slots with a buffer violation of the run's leases, those with a positive attributable deficit, "
           r"the reclaims and the violation cuts (v/a/r/c), per lender source, fold, arm and lender (L-tr; L-vr, which "
           r"cuts leases on a buffer violation)."
           + (r" $^\dagger$: a sum over fewer cells (a missing run)." if dag else ""))
    return A.longtable("@{}p{" + f"{NAME_IN}in" + "}l" + "r" * len(t["groups"]) + "@{}", cap, "tab:s-oos-sources",
                       ["Policy", "Source"] + [m for _, _, m in t["groups"]], body,
                       head_top=_span_head(pairs, len(SOURCE_MODES), 2), rules=rules, together=together,
                       tabcolsep="2.0pt")


def write_tables(data: Mapping, report: Mapping) -> None:
    """The four tables and the data file from the extract's `tables` (figs.common.write_table; the data file's
    sha256 checked against the extract's)."""
    t = data["tables"]
    head = L.table_head
    paths = [write_table(TABLES[0], head(NAME, [E7O]) + margins_tex(t["oos_margins"], data)),
             write_table(TABLES[1], head(NAME, [E7O]) + rules_tex(t["oos_rules"], data)),
             write_table(TABLES[2], head(NAME, [E7O]) + policies_tex(t["oos_policies"], data)),
             write_table(TABLES[3], head(NAME, [E7O]) + sources_tex(t["oos_sources"], data)),
             write_table(RUNS_CSV, A.csv_from_entry(t["oos_runs"]))]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    return A.main(NAME, build, draw, argv, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
