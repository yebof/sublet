"""sf_e4: E4, the learning-augmented PDs on the trace ratio day against the prediction error (design/sim_spec_ms4.md
§8.2, §6.6-§6.10; plan §4, part S-F; the add-back size of plan §3.4).

(a) Azure, (b) BurstGPT (e4/summary.json ratio.<panel>.<pred>.<series>): each series against the optimum of its own
cost model (§8.2): the fractional psi-PDs (psi = 0.1, 0.3, 0.5,
A5's psi[i].P) and the plain fractional PD (psi = 1, A5's P, "A2 fractional") cost the uncapacitated covering program
of predict.aligned_lp, so for them x = q eta / LP_core and y = ALG / LP_core (`x_core`, `core_median`), LP_core the
LP optimum of that program on the ratio day; the combiner's run (A5, an engine total) has x = q eta / OPT_eager and
y = ALG / OPT_eager with Q39's LB (`x`, `median`); `cost_model` names each. Both axis labels say "OPT (own model)"
for these optima, which the note defines (print check: §8.2's x label "OPT of the series' cost model" beside the y
label "OPT (own model)", which §8.2 shortened, read as two different optima). Medians over 2 alignments x 3 policy
seeds, one point per prediction (previous day, its phase, amplitude and burst perturbations, empty, and the oracle at
eta = 0), drawn as markers only: the predictions are different kinds of error, so a line joining them in order of x
drew spikes that meant nothing (as built); a prediction without a ratio-day value is left out (`skipped` in the
extract, with its note); the 95% intervals are in the extract, not drawn (up to 13 points of five series in one
color). x on a symlog axis (linear below 1, so that the oracle's x = 0 is drawn; positions on it by matplotlib's own
transform, symlog_u), y on a log axis; the panels share y (`axes` in the extract), and the y label is centered on the
axes (C62: the legend stands above the panels and the y spines run to the axes' top; as built, the label was centered
on the y spine, which ended below the legend headroom, since centered on the axes it reached the legend band).
Where the three psi-PDs' points lie at one x and within common.AGREE_MAX_PCT percent in y (`coincide` in the
extract, recomputed from the drawn series in draw()), the note says so with their values; where they are the same
value (on the real data the empty prediction, in both panels), the markers lie on each other and only the last drawn
is seen, so the point is labeled with the prediction's name on the free space next to it (common.place_label, in the
PDs' label color; a leader only where it lies more than PRED_LEADER_MIN_PT from the point; print check: the hidden
psi = 0.1 point left the lowest psi-PD ratio at the largest x of (a) unexplained). The note also gives A2
fractional's ratio where it is the same at every prediction (`a2_constant`; psi = 1, A5's plain PD, does not use the
prediction) and the x range of the predictions other than the oracle (`x_spread`; in (b) the fractional series'
twelve lie within 0.08 decade, so that their markers merge), and says that 1 + x bends at x = 1 only because the
symlog axis turns logarithmic there.
Theory (grey dashed, upper bounds of the core): 1 + x (c(P-hat) <= OPT_eager + q eta, C3-L10, PROVEN), a bound on the
cost of following the prediction, not on a plotted ALG (labeled "c(P-hat)"; the ratios may lie above it), and 5.83 (1 +
x) (C3-T11 with C3-L10, PROVEN; the factor from meta.combiner_bound), the bound on A5's ALG / OPT_eager. Each is drawn
as a line where it lies inside the y range and labeled there if that part covers at least BOUND_MIN_SPAN of the x axis;
where it does not but its value at x = 0 lies inside the y range (`mark_at_zero`; 5.83 (1 + x) on the real data and the
fixture), its part inside the range is drawn as a dashed stub from x = 0 to where it leaves the y range (`stub_to`), in
the style of an upper bound, with a filled arrowhead (STUB_HEAD) at that end, since the bound goes on above the axes,
and labeled with the series it bounds: "$5.83\\,(1+x)$" (math, x italic as on the x axis and in the caption; C62 fix
round, as built "5.83 (1 + x)" in plain text) over "A5, C3-T11" where that sits
within LABEL_NEAR_PT of the stub in both panels, else "C3-T11 (A5)", "C3-T11" over "(A5)" or "C3-T11" (the first that
does; common_stub_forms, so that the panels name it alike; on the real data "C3-T11 (A5)": the two-line form with the
formula fits nowhere on the free space between (a)'s stub and 1 + x). A stub's label sits nearer to the stub than to the
data and the y spine (next to the spine it read as a tick label), not necessarily nearer than to 1 + x, since it names
its bound. §8.2 marks the value at x = 0 by a short grey tick instead; at the print check the solid tick with its leader
read as a legend sample or a constant level next to the label "C3-T11", in the style of an exact value rather than an
upper bound, and named neither A5 nor the rise, so that BurstGPT's psi = 0.1 points just below its level seemed to
nearly reach C3-T11. `bounds.lines` says which, with the interval. Each label sits on the free space nearest the drawn
part (common.free_spot over the whole segment or stub), and the figure fails (StyleError) where it fits nowhere; a label
set apart from its bound is joined to it by a thin grey leader. A drawn 5.83 (1 + x) is labeled "C3-T11 (A5)" (with
"with C3-L10", or on two lines, where that fits; "C3-T11" alone where nothing longer fits), so that it is not read as a
bound on the fractional series. The label of 1 + x sits on the free space nearest its line, in (a) left of it next to
the oracle's markers (at 9 pt the free space between the line and the x = 10 clusters was narrower than the label);
the note says what 1 + x bounds.
They bound the core; on these full-model trace instances the ratios are diagnostics (design §5.5 E4, reading). The
legend (marker samples) is two rows above the panels, the trust-psi PDs, then A2 fractional and A5 (C62:
ms4_lib.legend_rows_above, with the mathtext labels on their row's baseline as printed; as built two rows in the
panels' headroom, common.legend_rows and legend_headroom, which raised the y axes over the data, the row of (a) running
over (b)'s headroom); the minor x ticks are at 2 and 5 per decade (X_MINOR; as built 2-9, a comb). A6-pred's week
costs over A6 without predictions (A6-pred has no ratio-day run, §6.7) and A5's are in the extract (`week`), not drawn.

Run from code/sim: python -m figs.supp.sf_e4 [--from-extract [JSON]].
"""
from __future__ import annotations

import math
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib import patheffects
from matplotlib.patches import FancyArrowPatch
from matplotlib.ticker import FixedLocator, NullFormatter, NullLocator

from figs import style
from figs.common import (AGREE_MAX_PCT, LEADER_PT, TOP_TICK_GAP_PT, align_baselines, cli, finite, free_spot, maybe,
                         need, panel_title, place_label, points_pt)
from figs.inputs import Inputs
from figs.supp.ms4_lib import (agg_point, center_xlabel, finite_values, legend_reserve_top, legend_rows_above,
                               log_ticks, runs_text)

NAME = "sf_e4"
E4 = "code/sim/out/e4/summary.json"
KEYS = style.SUPP_POLICIES_MS4[NAME]          # psi_01, psi_03, psi_05, a2_frac, a5
PSI_KEYS = ("psi_01", "psi_03", "psi_05")     # the three psi-PDs, the same at the empty prediction
PANELS = (("a", "azure"), ("b", "burstgpt"))
FRACTIONAL_MODEL = "pd_covering"              # e4.py's cost_model of the four fractional series (§6.10)
PRED_TEXT = {"empty": "empty", "exact": "exact", "prev": "previous day"}   # a labeled prediction's name (not in §8.2)
SAME_REL = 1e-9                               # values this close (relative) are the same
LINTHRESH = 1.0                               # symlog x: linear below 1 (x = 0 is the oracle)
LINSCALE = 0.6                                # matplotlib's linscale: the linear part [0, 1] is
LINSCALE_ADJ = LINSCALE / (1.0 - 1.0 / 10.0)  # ... LINSCALE / (1 - 1/base) = 0.667 decade wide
#                                               (matplotlib's SymmetricalLogTransform, base 10)
X_PAD = 1.25                                  # the x axis reaches this factor beyond the largest x (not in §8.2)
X_LEFT = -0.12 * LINTHRESH                    # left of x = 0, so that the oracle's markers clear the y axis
Y_PAD_LO, Y_PAD_HI = 1.1, 1.15                # the y axis beyond the drawn values (factors; not in §8.2)
BOUND_MIN_SPAN = 0.12                         # a bound is drawn where it covers at least this share of the x axis
STUB_POINTS = 9                               # points of a bound's stub at x = 0 (not in §8.2)
STUB_HEAD = 5.0                               # mutation scale of the stub's arrowhead at its top end, pt (not in §8.2)
LEADER_MIN_PT = 4.0                           # a bound's label farther than this from it gets a leader (as Fig. 4(c))
PRED_LEADER_MIN_PT = 6.0                      # a prediction's label farther than this from its point gets a leader:
#                                               next to a marker it lies about 4 pt from the point's center, where a
#                                               leader was a 1-pt tick under the marker (not in §8.2)
LABEL_NEAR_PT = 10.0                          # a bound's label form is taken where it sits this close to its bound;
#                                               else the shorter form, else the nearest (not in §8.2)
# C62: the legend's two rows above the panels (ms4_lib.legend_rows_above), the trust-psi PDs in the first, A2 fractional
# (psi = 1) and A5 in the second; as built at 9 pt, rows of two and three in the panels' headroom, with the y axes
# raised over the data to hold them (common.legend_headroom), the row of (a) running on over (b)'s headroom
LEGEND_ROWS = (("psi_01", "psi_03", "psi_05"), ("a2_frac", "a5"))
LEGEND_RESERVE = 2                             # C62: the reserve of two legend rows above the panels
LEGEND_HANDLE = 1.0                            # C62: marker samples one em long (not in §8.2)
X_MINOR = (2.0, 5.0)                           # C62: minor x ticks at 2 and 5 per decade, unlabeled (as built 2-9,
#                                                a comb of eight ticks in each 0.5-in decade)
style.register_supplementary(NAME, "W1", 2.2)
LABELS = {"x": r"$q\eta$ / OPT (own model)", "y": "ALG / OPT (own model)",
          "panel": {"azure": "Azure", "burstgpt": "BurstGPT"},
          "bound_1x": "c($\\hat{P}$),\nC3-L10", "bound_t11": "C3-T11 (A5)\nwith C3-L10",
          "bound_1x_short": "c($\\hat{P}$), C3-L10", "bound_t11_short": "C3-T11 (A5)",
          "bound_t11_narrow": "C3-T11\n(A5)", "bound_t11_bare": "C3-T11",
          "bound_1x_stub": "$1+x$\nc($\\hat{P}$), C3-L10", "bound_t11_stub": "{line}\nA5, C3-T11",
          "bound_1x_stub_short": "C3-L10 (c($\\hat{P}$))", "bound_t11_stub_short": "C3-T11 (A5)",
          "bound_1x_stub_narrow": "C3-L10\n(c($\\hat{P}$))", "bound_t11_stub_narrow": "C3-T11\n(A5)",
          "bound_mark": "dashed stub from x = 0 with an arrowhead where it leaves the y range: the part of the bound "
                        "inside the y range, where it is too short to "
                        "carry its label; labeled with the series it bounds and its theorem, with its formula where "
                        "that fits next to the stub in both panels",
          "status": {"C3-L10": "PROVEN; numerically checked", "C3-T11": "PROVEN; numerically checked",
                     "C3-T9": "PROVEN; numerically checked", "O2": "CONJECTURE"},
          "note": "fractional psi-PDs and A2 fractional: x = q eta / LP_core, y = ALG / LP_core (LP_core: the LP "
                  "optimum of the uncapacitated covering program of predict.aligned_lp on the ratio day); A5 (the "
                  "combiner's run, engine total): x = q eta / OPT_eager, y = ALG / OPT_eager (Q39's LB); 'OPT (own "
                  "model)' on the axes is this optimum of each series' cost model; medians over {runs}; one marker "
                  "per prediction, not joined (the predictions are different kinds of error); x on a symlog axis, "
                  "linear on [0, {lin}] and logarithmic above, so that 1 + x bends at x = {lin}; dashed: 1 + x "
                  "bounds c(P-hat) / OPT_eager, the cost of following the prediction (C3-L10), not a plotted ALG; "
                  "{t11} bounds A5's ALG / OPT_eager (C3-T11 with C3-L10){stub}; the bounds are core bounds and the "
                  "trace ratios diagnostics{coincide}{a2}{spread}"}


def series_points(block: Mapping, preds: Sequence[str], key: str) -> dict:
    """One key's points {pred, x, y, model} in order of x; the predictions without a value in `skipped` with notes."""
    pts, skipped = [], {}
    for pred in preds:
        ent, note = maybe(block, pred, key)
        if note is not None or not isinstance(ent, Mapping):
            skipped[pred] = note or "missing"
            continue
        model = ent.get("cost_model")
        xf, yf = ("x_core", "core_median") if model == FRACTIONAL_MODEL else ("x", "median")
        x, y = ent.get(xf), ent.get(yf)
        if x is None or y is None:
            skipped[pred] = ent.get(f"{yf}_note") or ent.get(f"{xf}_note") or ent.get("median_note") or "null"
            continue
        lo, hi = (ent.get("core_median_ci95" if model == FRACTIONAL_MODEL else "median_ci95") or [None, None])[:2]
        pts.append((float(x), float(y), pred, model, lo, hi, ent.get("n_runs")))
    pts.sort(key=lambda p: (p[0], p[2]))
    return {"pred": [p[2] for p in pts], "x": [p[0] for p in pts], "y": [p[1] for p in pts],
            "ci_lo": [p[4] for p in pts], "ci_hi": [p[5] for p in pts], "n_runs": [p[6] for p in pts],
            "cost_model": sorted({p[3] for p in pts}), "x_field": "x_core" if pts and pts[0][3] == FRACTIONAL_MODEL
            else "x", "skipped": skipped}


def week_block(e4: Mapping) -> dict:
    """week.<panel>.<mu>.<pred>.<tag>: the median cost over A6 without predictions (E4-6), with its interval."""
    out = {}
    for panel, by_mu in need(e4, "week", what=E4).items():
        if panel.endswith("_note") or not isinstance(by_mu, Mapping):
            continue
        for mk, by_pred in by_mu.items():
            if mk.endswith("_note") or not isinstance(by_pred, Mapping):
                continue
            for pred, by_tag in by_pred.items():
                if pred in ("none",) or pred.endswith("_note") or not isinstance(by_tag, Mapping):
                    continue
                for tag in ("A5", "A6-pred"):
                    p = agg_point(by_tag.get(tag) or {}, "cost_over_a6")
                    out.setdefault(panel, {}).setdefault(mk, {}).setdefault(pred, {})[tag] = {
                        "median": p["median"], "ci_lo": p["ci_lo"], "ci_hi": p["ci_hi"], "n": p["n"],
                        "note": p["note"]}
    return out


def axis_ranges(out: Mapping) -> dict:
    """The y range of the shared log axis (the drawn values and 1, the bounds' value at x = 0) and the largest x."""
    keys = [k for k in KEYS if k in out["a"]]
    xs = finite_values(*(out[p][k]["x"] for p, _ in PANELS for k in keys))
    ys = finite_values(*(out[p][k]["y"] for p, _ in PANELS for k in keys))
    ys = ys[ys > 0]
    lo, hi = (float(min(ys.min(), 1.0)), float(max(ys.max(), 1.0))) if ys.size else (1.0, 2.0)
    return {"y_lim": [lo / Y_PAD_LO, hi * Y_PAD_HI], "x_max": float(xs.max()) if xs.size else 1.0}


def bounds_inside(factor: float, rng: Mapping) -> list[dict]:
    """1 + x and factor (1 + x), each with the x interval where it lies inside the y range (from x = 0 up to where it
    leaves through the top, or to the x axis's end), drawn as a labeled line only where that interval covers at least
    BOUND_MIN_SPAN of the x axis's width (on the symlog scale): a sliver at x = 0 cannot carry a label on the line.
    Where it does not but the bound's value at x = 0 lies inside the y range, `mark_at_zero`: its part from x = 0 to
    `stub_to` (where it leaves the y range) is drawn as a stub, labeled as draw_bound_lines says."""
    y0, y1 = rng["y_lim"]
    x_end = x_top(rng["x_max"])
    out = []
    for f, name in ((1.0, "1 + x"), (factor, f"{factor:g} (1 + x)")):
        x_from = max(0.0, y0 / f - 1.0)
        x_to = min(x_end, y1 / f - 1.0)
        span = (symlog_u(x_to) - symlog_u(x_from)) / (symlog_u(x_end) - symlog_u(X_LEFT)) if x_to > x_from else 0.0
        drawn = span >= BOUND_MIN_SPAN
        mark = not drawn and y0 <= f <= y1
        out.append({"line": name, "factor": f, "drawn": drawn, "mark_at_zero": mark,
                    "x_from": x_from if drawn else None, "x_to": x_to if drawn else None,
                    "stub_to": x_to if mark else None, "span": span,
                    "note": None if drawn else (f"inside the y range [{y0:.4g}, {y1:.4g}] only over {span:.1%} of the "
                                                f"x axis (a line labeled on it needs at least {BOUND_MIN_SPAN:.0%})"
                                                + (f": drawn as a stub from x = 0 (value {f:g}) to x = {x_to:.3g}, "
                                                   f"where it leaves the y range" if mark else ": not drawn"))})
    return out


def coincidences(out: Mapping) -> list[dict]:
    """The predictions at which the three psi-PDs' points of a panel lie at one x and within AGREE_MAX_PCT percent of
    each other in y: [{panel, pred, x, y_lo, y_hi, within_pct, label}], within_pct 0 where they are the same value
    (SAME_REL), so that the markers lie on each other and only the last drawn is seen; those get `label`, the
    prediction's name (PRED_TEXT), drawn next to the point."""
    res = []
    for p, _ in PANELS:
        if not all(k in out[p] for k in PSI_KEYS):
            continue
        pts = {k: dict(zip(out[p][k]["pred"], zip(out[p][k]["x"], out[p][k]["y"]))) for k in PSI_KEYS}
        for q in out[p][PSI_KEYS[0]]["pred"]:
            if not all(q in pts[k] for k in PSI_KEYS):
                continue
            xs = [float(pts[k][q][0]) for k in PSI_KEYS]
            ys = [float(pts[k][q][1]) for k in PSI_KEYS]
            lo, hi = min(ys), max(ys)
            if max(xs) - min(xs) > SAME_REL * max(1.0, abs(xs[0])) or not lo > 0:
                continue
            d = hi / lo - 1.0
            pct = 0 if d <= SAME_REL else int(math.ceil(100.0 * d - 1e-9))
            if pct <= AGREE_MAX_PCT:
                res.append({"panel": p, "pred": q, "x": xs[0], "y_lo": lo, "y_hi": hi, "within_pct": pct,
                            "label": PRED_TEXT.get(q, q) if pct == 0 else None})
    return res


def constant_values(out: Mapping, key: str) -> dict:
    """{panel letter: value} where every point of `key` in that panel has the same y (SAME_REL)."""
    res = {}
    for p, _ in PANELS:
        ys = finite(out[p][key]["y"]) if key in out[p] else np.array([])
        ys = ys[np.isfinite(ys)]
        if ys.size > 1 and ys.max() - ys.min() <= SAME_REL * abs(ys.max()):
            res[p] = float(ys[0])
    return res


def x_spread(out: Mapping) -> dict:
    """{panel letter: {fractional: [lo, hi], a5: [lo, hi], n}}: the x range of the predictions other than the oracle
    (x > 0) of the fractional series (they share x = q eta / LP_core) and of A5, with their count."""
    res = {}
    for p, _ in PANELS:
        ent = {}
        for name, key in (("fractional", PSI_KEYS[0]), ("a5", "a5")):
            if key not in out[p]:
                continue
            xs = finite(out[p][key]["x"])
            xs = xs[np.isfinite(xs) & (xs > 0)]
            if xs.size:
                ent[name] = [float(xs.min()), float(xs.max())]
                ent[f"n_{name}"] = int(xs.size)
        res[p] = ent
    return res


def fmt(v: float) -> str:
    """An x value in a note: 3 significant digits."""
    return f"{v:.3g}"


def fmt_y(v: float) -> str:
    """A ratio in a note: 2 decimals."""
    return f"{v:.2f}"


def note_text(out: Mapping, runs: str) -> str:
    """The caption material: LABELS["note"] with the counts, the bound and the coincidences read from the data."""
    t11 = out["bounds"]["lines"][1]
    stub = (f"; it leaves the y range at x = {fmt(t11['stub_to'])}, so only its stub from x = 0 is drawn, labeled "
            f"with A5 and C3-T11" if t11.get("mark_at_zero") else "")
    same = [c for c in out["coincide"] if c["within_pct"] == 0]
    near = [c for c in out["coincide"] if c["within_pct"] > 0]
    parts = []
    for pred in dict.fromkeys(c["pred"] for c in same):
        cs = [c for c in same if c["pred"] == pred]
        vals = ", ".join(f"{fmt_y(c['y_lo'])} in ({c['panel']})" for c in cs)
        parts.append(f"with the {pred} prediction the three psi-PDs coincide ({vals}; labeled '{cs[0]['label']}')")
    for c in near:
        parts.append(f"in ({c['panel']}) at the {c['pred']} prediction (x = {fmt(c['x'])}) they lie within "
                     f"{c['within_pct']}% ({fmt_y(c['y_lo'])}-{fmt_y(c['y_hi'])})")
    coincide = "; " + "; ".join(parts) if parts else ""
    a2 = out["a2_constant"]
    a2_txt = ("; A2 fractional (psi = 1, A5's plain PD) does not use the prediction: its ratio is the same at every x ("
              + ", ".join(f"{fmt_y(v)} in ({p})" for p, v in a2.items()) + ")") if a2 else ""
    sp = out["x_spread"]
    fr = [(p, e) for p, e in sp.items() if "fractional" in e]
    a5 = [(p, e) for p, e in sp.items() if "a5" in e]
    spread = ""
    if fr:
        spread = ("; the predictions other than the oracle lie at x = "
                  + " and ".join(f"{fmt(e['fractional'][0])}-{fmt(e['fractional'][1])} in ({p})" for p, e in fr)
                  + " for the fractional series"
                  + ("" if not a5 else " (" + " and ".join(f"{fmt(e['a5'][0])}-{fmt(e['a5'][1])} in ({p})"
                                                           for p, e in a5) + " for A5)"))
    return LABELS["note"].format(runs=runs, lin=f"{LINTHRESH:g}", t11=t11["line"], stub=stub, coincide=coincide,
                                 a2=a2_txt, spread=spread)


def build(inp: Inputs) -> dict:
    e4 = inp.json(E4)
    labels_pred = need(e4, "meta", "predictions", what=E4)
    preds = [q for q in labels_pred if q != "none"]
    factor = float(need(e4, "meta", "combiner_bound", what=E4))
    out = {}
    for p, panel in PANELS:
        block = need(e4, "ratio", panel, what=E4)
        out[p] = {"panel": panel, **{key: series_points(block, preds, key) for key in KEYS}}
    rng = axis_ranges(out)
    out["axes"] = rng
    out["bounds"] = {"factor_t11": factor, "lines": bounds_inside(factor, rng)}
    out["coincide"] = coincidences(out)
    out["a2_constant"] = constant_values(out, "a2_frac")
    out["x_spread"] = x_spread(out)
    out["week"] = week_block(e4)
    out["predictions"] = {k: labels_pred[k] for k in preds}
    runs = runs_text(len(need(e4, "meta", "alignments", what=E4)), len(need(e4, "meta", "policy_seeds", what=E4)))
    # C62 (fix round): the formula drawn in math, x italic as on the x axis and in the caption ($5.83(1+x)$); as built
    # the plain bounds.lines name "5.83 (1 + x)", which the note keeps
    t11_line = rf"${out['bounds']['lines'][1]['factor']:g}\,(1+x)$"
    out["labels"] = {**LABELS, "bound_t11_stub": LABELS["bound_t11_stub"].format(line=t11_line),
                     "note": note_text(out, runs)}
    out["meta"] = {"git_revision": need(e4, "meta", "git_revision", what=E4),
                   "reduced": bool(e4["meta"].get("reduced")), "ratio_day": e4["meta"].get("ratio_day")}
    out["sources"] = list(inp.sources)
    return out


def symlog_u(x: float) -> float:
    """Position of x on the symlog x axis (linear below LINTHRESH, log above), in the axis's own units: matplotlib's
    SymmetricalLogTransform with base 10, whose linear part [0, LINTHRESH] is LINSCALE_ADJ decade wide."""
    x = float(x)
    if abs(x) <= LINTHRESH:
        return LINSCALE_ADJ * x / LINTHRESH
    return math.copysign(LINTHRESH * (LINSCALE_ADJ + math.log10(abs(x) / LINTHRESH)), x)


def x_top(xmax: float) -> float:
    return max(xmax * X_PAD, 2.0 * LINTHRESH)


def x_axis(ax, xmax: float) -> None:
    """symlog x, linear below LINTHRESH: ticks 0, 1, 10, 100, ... up to the axis end, unlabeled minor ticks at X_MINOR
    (2 and 5) per decade (C62; as built 2-9)."""
    ax.set_xscale("symlog", linthresh=LINTHRESH, linscale=LINSCALE)
    top = x_top(xmax)
    dec = int(math.floor(math.log10(top)))
    major = [0.0] + [10.0 ** e for e in range(0, dec + 1)]
    minor = [m * 10.0 ** e for e in range(0, dec + 1) for m in X_MINOR if m * 10.0 ** e <= top]
    ax.xaxis.set_major_locator(FixedLocator(major))
    ax.xaxis.set_major_formatter(style.PLAIN)
    ax.xaxis.set_minor_locator(FixedLocator(minor))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlim(X_LEFT, top)
    style.end_label_inside(ax)


def clear_top_ticks(ax) -> list[float]:
    """C62: drop the major y ticks whose labels would reach within TOP_TICK_GAP_PT of the axes top, where the panel
    titles stand on the letters' baseline (the y limits stay the data's, `axes.y_lim`, from which bounds_inside reads
    where a bound leaves the range); as built, the legend's headroom kept the ticks far below the top. Returns the
    ticks kept."""
    y0, y1 = ax.get_ylim()
    r = ax.figure.canvas.get_renderer()
    to_pt = style.BP_PER_IN / ax.figure.dpi
    top_pt = ax.get_window_extent(r).y1 * to_pt
    keep = []
    for tk in ax.yaxis._update_ticks():
        t = tk.get_loc()
        if not y0 <= t <= y1:
            continue
        if tk.label1.get_window_extent(r).y1 * to_pt <= top_pt - TOP_TICK_GAP_PT:
            keep.append(t)
    ax.yaxis.set_major_locator(FixedLocator(keep))
    return keep


def bound_spot(ax, txt, near, text: str, others) -> tuple[float, tuple[float, float]] | None:
    """(distance to `near`, lower left corner) in pt of the free spot of the bound's label `txt` set to `text`
    (common.free_spot nearest to the points `near` and nearer to them than to `others`), or None where it fits
    nowhere."""
    to_pt = 72.0 / ax.figure.dpi
    txt.set_text(text)
    txt.xyann = (0.0, 0.0)
    bb = txt.get_window_extent(ax.figure.canvas.get_renderer())
    w, h = bb.width * to_pt, bb.height * to_pt
    spot = free_spot(ax, w, h, near, others=others if len(others) else None, skip=(txt,))
    if spot is None:
        return None
    dx = np.maximum(np.maximum(spot[0] - near[:, 0], 0.0), near[:, 0] - (spot[0] + w))
    dy = np.maximum(np.maximum(spot[1] - near[:, 1], 0.0), near[:, 1] - (spot[1] + h))
    return float(np.hypot(dx, dy).min()), spot


def place_bound_label(ax, txt, near, forms: Sequence[str], others_sets: Sequence) -> None:
    """Move a bound's label (an annotation) to the free space nearest to the points `near` (pt: the whole drawn segment,
    or the stub at x = 0; bound_spot) and nearer to them than to the points of `others_sets` (tried in order: for a
    line the other bound and the data, then the other bound alone, then none; for a stub the data, then none),
    left- and bottom-aligned there: the first text form whose spot lies within LABEL_NEAR_PT of the bound (the last
    form the shortest), else the form whose spot lies nearest; StyleError where none fits (as built, a fallback below
    the line's end put the label on the y label when the line left through the top next to the y axis, and without
    `others` the label of 1 + x sat next to the other bound)."""
    to_pt = 72.0 / ax.figure.dpi
    txt.set_annotation_clip(False)
    anchor = ax.transData.transform(txt.xy) * to_pt
    near = np.asarray(near, dtype=float).reshape(-1, 2)
    for others in others_sets:
        found = []                                     # (distance, form, spot)
        for text in forms:
            got = bound_spot(ax, txt, near, text, others)
            if got is None:
                continue
            found.append((got[0], text, got[1]))
            if found[-1][0] <= LABEL_NEAR_PT:            # the first form that sits next to its bound
                break
        if found:
            _, text, spot = next((f for f in found if f[0] <= LABEL_NEAR_PT), min(found, key=lambda f: f[0]))
            txt.set_text(text)
            txt.set_ha("left")
            txt.set_va("bottom")
            txt.xyann = (spot[0] - anchor[0], spot[1] - anchor[1])
            leader(ax, txt, near)
            return
    raise style.StyleError(f"{NAME}: the bound label fits nowhere on the free space ({list(forms)})")


def leader(ax, txt, near, role: str = "theory_leader", min_pt: float = LEADER_MIN_PT) -> None:
    """A thin grey leader from a placed label's box to the nearest of its points `near` (pt) where the label lies more
    than `min_pt` from them, as Fig. 4(c) and common.right_theory_lines join a moved label (IEEE: connect the label to
    its line)."""
    to_pt = 72.0 / ax.figure.dpi
    bb = txt.get_window_extent(ax.figure.canvas.get_renderer())
    x0, y0, x1, y1 = bb.x0 * to_pt, bb.y0 * to_pt, bb.x1 * to_pt, bb.y1 * to_pt
    near = np.asarray(near, dtype=float).reshape(-1, 2)
    q = np.column_stack([np.clip(near[:, 0], x0, x1), np.clip(near[:, 1], y0, y1)])
    d = np.hypot(*(near - q).T)
    k = int(np.argmin(d))
    if d[k] <= min_pt:
        return
    end = ax.transData.inverted().transform(near[k] / to_pt)
    start = ax.transData.inverted().transform(q[k] / to_pt)
    ld = ax.annotate("", xy=tuple(end), xytext=tuple(start), arrowprops=dict(
        arrowstyle="-", color=style.THEORY_GREY, linewidth=LEADER_PT, shrinkA=1.0, shrinkB=1.5),
        zorder=style.Z_THEORY, annotation_clip=False)
    ld._sublet_role = role


def draw_bound_lines(ax, lines: Sequence[Mapping], lab: Mapping) -> list[dict]:
    """The bounds drawn (bounds_inside) on a dense grid of their x interval, or as a dashed stub from x = 0 to where
    they leave the y range (`mark_at_zero`), each with its label (an annotation, placed by label_bounds) and its text
    forms, longest first: a line's name with the series it bounds (with "with C3-L10" where it fits), a stub's formula
    with the series it bounds and its theorem, else the theorem with the series (the stub cannot show the bound's
    shape); the theorem alone last, where nothing longer fits (as built). Returns [{txt, near (the drawn points in pt),
    forms, stub}]."""
    drawn = []
    for b, text, short, narrow, bare, stub, stub_short, stub_narrow in zip(
            lines, (lab["bound_1x"], lab["bound_t11"]), (lab.get("bound_1x_short"), lab.get("bound_t11_short")),
            (None, lab.get("bound_t11_narrow")), (None, lab.get("bound_t11_bare")),
            (lab["bound_1x_stub"], lab["bound_t11_stub"]), (lab["bound_1x_stub_short"], lab["bound_t11_stub_short"]),
            (lab["bound_1x_stub_narrow"], lab["bound_t11_stub_narrow"])):
        if b["drawn"]:
            lo, hi = b["x_from"], b["x_to"]
            grid = np.unique(np.concatenate([np.linspace(lo, min(hi, LINTHRESH), 41) if lo < LINTHRESH else [],
                                             np.geomspace(max(lo, LINTHRESH), hi, 160) if hi > LINTHRESH else [],
                                             [lo, hi]]))
            y = b["factor"] * (1.0 + grid)
            _, txt = style.theory_line(ax, grid, y, "upper", text, where="inside")
            forms = [f for f in (text, short, narrow, bare) if f]
            drawn.append({"txt": txt, "near": points_pt(ax, grid, y), "forms": forms, "stub": False})
        elif b.get("mark_at_zero"):
            grid = np.linspace(0.0, b["stub_to"], STUB_POINTS)
            y = b["factor"] * (1.0 + grid)
            (mk,) = ax.plot(grid, y, color=style.THEORY_GREY, zorder=style.Z_THEORY, label="_nolegend_",
                            **style.THEORY_STYLES["upper"])
            mk._sublet_role = "theory_mark:upper"
            # an arrowhead where the stub leaves the y range: the bound goes on above the axes (as built, the stub of
            # one 3-pt dash read as a speck between its label and 1 + x; print check of 2026-10-27)
            head = FancyArrowPatch((grid[-3], y[-3]), (grid[-1], y[-1]), arrowstyle="-|>", mutation_scale=STUB_HEAD,
                                   color=style.THEORY_GREY, linewidth=0.0, zorder=style.Z_THEORY, clip_on=False)
            ax.add_patch(head)
            head._sublet_role = "theory_mark_head:upper"
            # the label in theory_line's style (THEORY_LABEL_GREY, white halo), for the stub
            txt = ax.annotate(stub, xy=(0.0, b["factor"]), xytext=(0.0, 0.0), textcoords="offset points",
                              fontsize=style.TICK_PT, color=style.THEORY_LABEL_GREY, zorder=style.Z_THEORY_LABEL)
            txt.set_path_effects([patheffects.withStroke(linewidth=style.LABEL_HALO_PT, foreground="white")])
            txt._sublet_role = "theory_label:upper"
            forms = [f for f in (stub, stub_short, stub_narrow, bare) if f]
            drawn.append({"txt": txt, "near": points_pt(ax, grid, y), "forms": forms, "stub": True})
    return drawn


def data_points(ax) -> np.ndarray:
    """The policies' points of `ax` in pt (n x 2)."""
    pts = [points_pt(ax, ln.get_xdata(), ln.get_ydata()) for ln in ax.lines if hasattr(ln, "_sublet_policy")]
    return np.concatenate(pts) if pts else np.zeros((0, 2))


def spine_points(ax) -> np.ndarray:
    """Points (pt) every 2 pt along the drawn y spine of `ax` (its bounds)."""
    to_pt = 72.0 / ax.figure.dpi
    lo, hi = ax.spines["left"].get_bounds() or ax.get_ylim()
    x0 = ax.get_xlim()[0]
    a, b = (ax.transData.transform((x0, v)) * to_pt for v in (lo, hi))
    ys = np.linspace(a[1], b[1], max(int((b[1] - a[1]) / 2.0), 1) + 1)
    return np.column_stack([np.full_like(ys, a[0]), ys])


def stub_others(ax) -> np.ndarray:
    """What a stub's label must lie farther from than from its stub: the data and the y spine (on the stub's left, a
    label next to the spine read as a tick label, (b) as built)."""
    return np.concatenate([data_points(ax), spine_points(ax)])


def label_order(drawn: Sequence[Mapping]) -> list[int]:
    """The labels with the least room first: a stub, or the shorter segment (5.83 (1 + x) leaves through the top
    first)."""
    return sorted(range(len(drawn)), key=lambda k: np.ptp(drawn[k]["near"][:, 0]) if len(drawn[k]["near"]) else 0.0)


def common_stub_forms(axes, drawn_by_ax: Sequence[Sequence[dict]]) -> None:
    """Keep, for a stub labeled first in every panel, its forms from the first one whose spot lies within
    LABEL_NEAR_PT of the stub in every panel, so that the panels name the stub alike (on the real data the two-line
    form with the formula fits next to (b)'s stub only)."""
    firsts = [label_order(d)[0] if d else None for d in drawn_by_ax]
    if not drawn_by_ax or any(i is None or not d[i]["stub"] for i, d in zip(firsts, drawn_by_ax)):
        return
    entries = [d[i] for i, d in zip(firsts, drawn_by_ax)]
    forms = entries[0]["forms"]
    if any(e["forms"] != forms for e in entries):
        return
    for k, text in enumerate(forms):
        ok = True
        for ax, e in zip(axes, entries):
            got = bound_spot(ax, e["txt"], np.asarray(e["near"], dtype=float).reshape(-1, 2), text, stub_others(ax))
            ok = ok and got is not None and got[0] <= LABEL_NEAR_PT
        if ok:
            for e in entries:
                e["forms"] = forms[k:]
            return


def label_bounds(ax, drawn: Sequence[Mapping]) -> None:
    """Each bound labeled on the free space nearest the drawn part (place_bound_label), the label with the least room
    first (label_order): a line's label nearer to it than to the other bound and the data; a stub's label, which names
    its bound, nearer to the stub than to the data and the y spine (stub_others). A label placed counts as the other
    bound's for the next, so that the two do not read as one block."""
    data = data_points(ax)
    placed = []
    for i in label_order(drawn):
        e = drawn[i]
        other = [d["near"] for j, d in enumerate(drawn) if j != i] + placed
        other = np.concatenate(other) if other else np.zeros((0, 2))
        sets = ((stub_others(ax), data, np.zeros((0, 2))) if e["stub"] else
                (np.concatenate([other, data]), other, np.zeros((0, 2))))
        place_bound_label(ax, e["txt"], e["near"], e["forms"], sets)
        placed.append(np.concatenate([box_points(ax, e["txt"]), e["near"]]) if e["stub"] else box_points(ax, e["txt"]))


def label_coincidences(ax, p: str, coincide: Sequence[Mapping]) -> list:
    """Name the prediction at a point where the three psi-PDs are the same value (`coincide` entries with a label) on
    the free space next to it and nearer to it than to the other points (common.place_label; then without that
    condition), in the PDs' label color, joined by a leader where set apart; StyleError where it fits nowhere."""
    out = []
    pts = [ln for ln in ax.lines if getattr(ln, "_sublet_policy", None) in KEYS]
    for c in coincide:
        if c["panel"] != p or not c.get("label"):
            continue
        near = points_pt(ax, [c["x"]], [c["y_lo"]])
        data = np.concatenate([points_pt(ax, ln.get_xdata(), ln.get_ydata()) for ln in pts]) if pts else \
            np.zeros((0, 2))
        others = data[np.hypot(*(data - near[0]).T) > 0.5] if len(data) else data
        color = style.policy(PSI_KEYS[0]).label_color
        t = place_label(ax, c["label"], near, others=others if len(others) else None, color=color)
        if t is None:
            t = place_label(ax, c["label"], near, color=color)
        if t is None:
            raise style.StyleError(f"{NAME}: the label {c['label']!r} of ({p}) fits nowhere on the free space")
        t._sublet_role = "prediction_label"
        leader(ax, t, near, role="prediction_leader", min_pt=PRED_LEADER_MIN_PT)
        out.append(t)
    return out


def box_points(ax, txt) -> np.ndarray:
    """Points (pt) on the outline of a text's box, every 2 pt: the placed label as `others` of free_spot."""
    to_pt = 72.0 / ax.figure.dpi
    bb = txt.get_window_extent(ax.figure.canvas.get_renderer())
    x0, y0, x1, y1 = bb.x0 * to_pt, bb.y0 * to_pt, bb.x1 * to_pt, bb.y1 * to_pt
    xs = np.linspace(x0, x1, max(int((x1 - x0) / 2.0), 1) + 1)
    ys = np.linspace(y0, y1, max(int((y1 - y0) / 2.0), 1) + 1)
    return np.concatenate([np.column_stack([xs, np.full_like(xs, y0)]), np.column_stack([xs, np.full_like(xs, y1)]),
                           np.column_stack([np.full_like(ys, x0), ys]), np.column_stack([np.full_like(ys, x1), ys])])


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    axes = style.panel_row(fig, (1, 1), sharey=(False, True), top=legend_reserve_top(LEGEND_RESERVE))     # C62
    keys = [k for k in KEYS if k in data["a"]]
    rng = data["axes"]
    for ax, (p, panel) in zip(axes, PANELS):
        for key in keys:
            s = data[p][key]
            if s["x"]:
                style.scatter_policy(ax, key, finite(s["x"]), finite(s["y"]))
        x_axis(ax, rng["x_max"])
    y0, y1 = rng["y_lim"]
    style.log_axis(axes[0], "y", ticks=log_ticks(y0, y1))
    axes[0].yaxis.set_minor_locator(NullLocator())
    axes[0].set_ylim(y0, y1)
    clear_top_ticks(axes[0])               # C62: no tick label under the panel titles
    axes[0].set_ylabel(lab["y"])
    center_xlabel(axes, lab["x"])
    letters = style.panel_letters(axes)
    # C62 (fix round): the titles at the caption size (style.LABEL_PT; at TICK_PT as first restyled) on the letters'
    # baseline as printed
    align_baselines(letters + [panel_title(ax, letter, lab["panel"][panel], fontsize=style.LABEL_PT)
                                    for ax, letter, (p, panel) in zip(axes, letters, PANELS)])
    by_key = {k: style.policy_handles([k], lines=False)[0] for k in keys}
    rows = [r for r in ([by_key[k] for k in row if k in by_key] for row in LEGEND_ROWS) if r]
    for leg in legend_rows_above(fig, rows, n_rows=LEGEND_RESERVE, handlelength=LEGEND_HANDLE):     # C62
        align_baselines(leg.get_texts())
    # C62: the legend above the panels, so the y spines run to the axes' top (as built, legend_headroom ended them below
    # the legend, the shared panel's where (a)'s ended, and center_ylabel_on_spine centered the y label on that span)
    drawn = [draw_bound_lines(ax, data["bounds"]["lines"], lab) for ax in axes]
    coincide = coincidences(data)          # from the series drawn (the extract's `coincide` is their record)
    common_stub_forms(axes, drawn)
    for ax, d, (p, _) in zip(axes, drawn, PANELS):
        label_bounds(ax, d)
        label_coincidences(ax, p, coincide)
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
