"""sf_s1_v2: Sublet's one-parameter sensitivity on the confirmation weeks, the tornado of sf_s1 drawn for Sublet with
the new rows, and the tables s1v2_points.tex, s1v2_w0.tex and s1v2_seeds.tex with the data file s1v2_runs.csv
(design/ms7/w_spec.md §4, unit W-G4, writer C; design/ms7/registration.md §2-§3, X3; change C58).

Question: how much does Sublet save under each one-at-a-time change of an assumption, and at which settings is it not
cheaper than both of its strongest baselines in every week?

Inputs (RUN_INPUTS, the MS7 run outputs; a missing one stops the build with exit code 2 and the file named; figs/
rebuild.py keeps the entry pending until they are copied in): the registered analysis code/sim/out/s1v2/analysis.json
(sublet/experiments/ms7_sens_analysis.py, frozen by its sha256: every saving, margin, week count, row span and the seed
spread is read from it, nothing recomputed) and the two summaries it read, code/sim/out/s1v2/sweep/summary.json (the
rows' panels, labels and default settings, the points' settings and the rows not run) and code/sim/out/s1v2/w0/
summary.json (the r0 of every stress lender behind each W0, for the data file), each checked against the sha256 that the
analysis recorded. A non-reduced analysis must be the registered one on full runs (ms7_x3_lib.check_registered). The
statistics are descriptive (medians and min-max over the weeks; the weeks are rotations of one series, design/ms7/
plan.md D4); no p-value.

Figure (W2 x HEIGHT_IN in). Three panels side by side, one group of register rows each as the driver assigns them
(sweep meta.rows.<row>.panel; the confirmation's stress variants L-rf and L-vr, rows q28_rf and q28_vr, in (c)): (a)
prices, costs and timing; (b) LLMs and demand; (c) lenders, contracts and stress. Per row a bar from the lowest to the
highest median saving of Sublet over the row's settings and the default (the analysis's rows.<row>.lo and .hi), in
Sublet's blue at alpha BAR_ALPHA, each setting a Sublet marker at its median saving (points.<pt>.by_tag.Sublet.
median_saving_pct), filled where Sublet's r0 is below both Greedy, back-off and RetroRenting-style in every week (the
analysis's vs_pair.weeks_hold = n_weeks: H1's ordering on the confirmation's per-week best pair), open where it is not
(a week with a missing run counts as not holding); the settings at the bar's ends as labels (TICK_PT) outside it
(sf_s1's short forms, setting_text), a row without a span "no change" ("no run" where no setting of the row has a
saving, every run missing); rows sorted by span within each panel, the largest at the top, ties in the register's
order; one row pitch in all panels; the default point's median saving as a grey line in each panel; x "Saving over
all-fallback (%)" centered under the panels.

C62 layout (layout(), stored in the extract, so a redraw is exact): the panels share one x scale (pt per percentage
point), so that bar lengths compare across panels, and each shows its own window of the axis, the range of its data and
end labels, with ticks of one step in all panels; each panel reserves its own widest row label, after an equal gutter
(GUTTER_IN) to its left neighbor's axes. The scale is the largest at which the three windows fit the figure's width
with every end label EDGE_CLEAR_PT inside its axes and every marker DATA_CLEAR_PT inside (a bisection; the labels of a
row without a span on the side of its panel that needs less width). As built (MS7, at 9 pt) the panels shared one x
range, sf_s1's rule, which spent most of (b)'s and (c)'s width on empty range and still left the end labels of three
long rows of (a) to the table and the caption. Only where the data would then keep less than DATA_MIN_SHARE of the
axes' width do rows give up their end labels (the costliest first) to the table, column Setting, and to the caption.
The row labels are texts on the baseline of their row's end labels (common.align_baselines: a mathtext label such as
$\\alpha_p$ otherwise sat up to 0.8 pt off its row in the PDF). The two marker states and the default's grey line are
keyed in a legend in the free rows at the bottom of the panel with the fewest rows where it fits there
(LEGEND_FREE_ROWS), else in a legend row above the panels. The panel titles at the caption size (LABEL_PT) on the
letters' baseline, a panel's window widened on both sides where its title would otherwise end beyond its axes' right
end (title_min_widths; binding on narrow data only, as the fixture's).

Tables (after hook, figs.common.write_table, from the extract's `tables`, so --from-extract rewrites them byte for byte;
longtables of ms5b_e7_lib, one-column mode):
  s1v2_points.tex  one line per setting, the default point first, then the rows in the figure's order: the assumption
                   with its default setting (and the bar end the default is at), the setting (and the bar end it is
                   at), Sublet's median saving and its min-max over the weeks, the median savings of critical-ratio
                   renting, Greedy, back-off and RetroRenting-style, the margin min(Greedy, back-off; RetroRenting-
                   style) - Sublet in r0 (percentage points of the all-fallback cost; positive when Sublet costs less)
                   with its median and min-max over the weeks without a missing run, the weeks in which it is positive
                   of the weeks, and the price of the guard, Sublet - critical-ratio renting in r0 (median, pp);
  s1v2_w0.tex      part w0: per load-scenario and fee setting and the default (the confirmation's runs) the median W0
                   (the largest r0 over the five stress lenders) of Sublet with its min-max over the weeks and of the
                   four other policies, and the weeks in which Sublet's W0 is below 1 and below that of Greedy,
                   back-off, RetroRenting-style and CoCaR-style (H2's ordering on these policies);
  s1v2_seeds.tex   the seed spread of the confirmation that justifies policy seed 0: per policy of its seed part the
                   largest |r0 at seed k - r0 at seed 0| with its lender, week and seed, the pairs counted and missing;
  s1v2_runs.csv    every per-run value behind the figure and the tables: per setting, policy and week the r0 under the
                   trace lender; per W0 setting, policy, stress lender and week the r0, and per setting, policy and week
                   the W0 (its source: this study's runs, or the confirmation's parts second and main for the reused
                   settings and the default's W0). The extract's tables.s1v2_runs holds its rows and sha256.
Every policy is named by its registry label; no tag, file or design name is printed.

labels.caption is a caption draft for the integrator (the supplement part s_f3.tex), labels.values the counts and
values it reads from the inputs (each a candidate \\val entry); headline is the analysis's headline block, unchanged.

Run from code/sim: python -m figs.supp.sf_s1_v2 [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

import math

from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator
from matplotlib.transforms import ScaledTranslation, blended_transform_factory

from figs import style
from figs.common import (MissingKey, align_baselines, letter_box, need, panel_title, text_width_in, thin_tick_labels,
                         write_table)
from figs.inputs import Inputs
from figs.supp import ms7_x3_lib as X
from figs.supp import sf_s1 as v1
from figs.supp.ms4_lib import center_xlabel

NAME = "sf_s1_v2"
ANALYSIS = "code/sim/out/s1v2/analysis.json"
SWEEP = "code/sim/out/s1v2/sweep/summary.json"
W0 = "code/sim/out/s1v2/w0/summary.json"
RUN_INPUTS = (ANALYSIS, SWEEP, W0)
INPUTS = RUN_INPUTS
KEYS = style.SUPP_POLICIES_MS7[NAME]
KEY = "sublet_v2"
TAGS4 = ("Sublet", "A9", "BL1-BO", "BL5-cur")          # ms7_sens_analysis.TAGS4
PAIR = ("BL1-BO", "BL5-cur")                           # ms7_sens_analysis.PAIR
W0_TAGS = TAGS4 + ("BL4",)                             # part w0's tags (W0_SET = PAIR + BL4)
TRACE = "L-tr"
PANELS = ("a", "b", "c")
Q28_ROWS = ("q28_rf", "q28_vr")                        # the confirmation's stress variants, panel (c) as in sf_s1
Q28_PANEL = "c"
DEFAULT = "default"
TABLES = ("s1v2_points.tex", "s1v2_w0.tex", "s1v2_seeds.tex", "s1v2_runs.csv")
RUNS_CSV = TABLES[-1]
HEIGHT_IN = 2.5
style.register_supplementary(NAME, "W2", HEIGHT_IN)
BAR_H, BAR_ALPHA, BAR_EDGE_PT = v1.BAR_H, v1.BAR_ALPHA, v1.BAR_EDGE_PT
END_GAP_PT, EDGE_CLEAR_PT, DATA_CLEAR_PT = v1.END_GAP_PT, v1.EDGE_CLEAR_PT, v1.DATA_CLEAR_PT
ZERO_SPAN = v1.ZERO_SPAN
TIE = 1e-9                         # a setting whose median is within this of a bar's end is at that end
LEGEND_FREE_ROWS = 2               # the legend goes into a panel with at least this many free rows at its bottom
LEGEND_PAD_PT = 2.0                # ... clear of its last row's bar by at least this
# C62 layout (layout())
GUTTER_IN = 0.14                   # a panel's widest row label this far right of its left neighbor's axes
OUTER_IN = 0.02                    # (a)'s widest row label this far right of the page's left edge
ROW_PAD_PT = style.TICK_PAD_PT     # a row label ends this far left of its panel's y spine
DATA_MIN_SHARE = 0.35              # the data spans keep at least this share of the axes' total width
SCALE_MAX_PP = 30.0                # where no panel has a span: the axes' total width shows this many points
SCALE_ITER = 60                    # bisection steps of the scale
TICK_STEPS = (5.0, 10.0, 20.0, 25.0, 50.0, 100.0)    # one step in every panel: the first at least TICK_MIN_PT long
TICK_MIN_PT = 24.0
TITLE_GAP_PT = 3.0                 # common.panel_title: a panel title starts this far right of its letter
TABCOLSEP = "2.0pt"
# C59 (RC18(1)): the default setting of a row as the tables print it where the driver's register (s1.ROWS) types it
# coarser than Section V and the supplement's register table: the price ratios alpha = a0 / q^GPU and alpha_p =
# a_p / q^GPU at three decimals, code/analysis/out/a11_calibration.json inputs.alpha (0.3986) and inputs.alpha_p
# (0.8350), the prices that the week instance's config reads (as built "0.40" and "0.83"; the test checks them against
# that file)
DEFAULT_TEXT = {"alpha": "0.399", "alpha_p": "0.835"}
# the figure's row labels: sf_s1's, with the new row of the replica goodput of tier M (C56)
ROW_LABELS = {**v1.ROW_LABELS, "kappa_M": r"$\kappa$ of M"}
LABELS = {
    "x": "Saving over all-fallback (%)",
    "titles": {"a": "Prices, costs, timing", "b": "LLMs and demand", "c": "Lenders, contracts, stress"},
    "holds": "Cheaper than both in every week",
    "fails": "Not in every week",
    "no_change": "no change", "no_run": "no run", "default_point": "Default point",
    "default_key": "Default point, {v:.1f}%",     # C62: the grey line keyed with its value
    "stress_default": "L-tr",      # the default lender of the stress rows (end text 'off')
    "caption": (
        "Sensitivity of {sublet} on {weeks}: its median saving over the all-fallback cost (overflow accounting, "
        "the trace lender) per assumption, one assumption at a time, each setting's saving over its own all-fallback "
        "cost. A bar runs from the lowest to the highest median over the row's settings (markers) and the default "
        "(grey line, {default:.1f}\\%), labeled with the settings at its ends; rows sorted by span; one $x$ scale in "
        "all panels. Filled: {sublet}'s "
        "cost is below that of both {bo} and {rr} in every week ({n_hold} of {n_points} settings); open: not in every "
        "week. {gamma}L-rf refuses purchases on unavailable layers and L-vr turns buffer violations into reclaims "
        "without notice (off: the trace lender; on: the variant); these two rows and the buffer quantile 0.999 reuse "
        "the confirmation's runs. {moved}Not run: {not_run}."),
    "moved": "Bar ends not labeled: {rows} (Table~\\ref{{tab:s-s1v2-points}}). ",
}


def row_label(row_id: str, meta_row: Mapping | None) -> str:
    return ROW_LABELS.get(row_id) or str((meta_row or {}).get("label") or row_id)


# ---------------------------------------------------------------------------------------------------------------
# data
def _sav(e: Mapping, tag: str):
    return ((e.get("by_tag") or {}).get(tag) or {}).get("median_saving_pct")


def bar_rows(ana: Mapping, sweep_meta: Mapping) -> list[dict]:
    """Every tornado row in the register's order (sweep meta.rows_order): id, panel, labels, gamma_row, lo, hi, span
    (the analysis's rows.<row>), the settings at each end (ties within TIE, the default included), the end texts, the
    points (name, the driver's label, the setting's short form, Sublet's median saving, whether the ordering holds in
    every week) and the default (its setting's short form and Sublet's median saving)."""
    pts = need(ana, "points", what=ANALYSIS)
    arows = need(ana, "rows", what=ANALYSIS)
    mrows = need(sweep_meta, "rows", what=f"{SWEEP} meta")
    dflt = need(pts, DEFAULT, what=f"{ANALYSIS} points")
    dsav = _sav(dflt, "Sublet")
    out = []
    for i, rid in enumerate(need(sweep_meta, "rows_order", what=f"{SWEEP} meta")):
        if rid not in arows:
            raise MissingKey(f"{ANALYSIS}: no rows.{rid} (a row of the sweep's rows_order)")
        r = arows[rid]
        mr = mrows.get(rid)
        if mr is None and rid not in Q28_ROWS:
            raise MissingKey(f"{SWEEP} meta.rows has no {rid!r}")
        panel = Q28_PANEL if rid in Q28_ROWS else need(mr, "panel", what=f"{SWEEP} meta.rows.{rid}")
        d_label = LABELS["stress_default"] if rid in Q28_ROWS else need(mr, "default_label", what=f"{SWEEP} rows.{rid}")
        points = []
        for n in need(r, "points", what=f"{ANALYSIS} rows.{rid}"):
            e = need(pts, n, what=f"{ANALYSIS} points")
            vp = e.get("vs_pair") or {}
            nw, wh = int(vp.get("n_weeks") or 0), int(vp.get("weeks_hold") or 0)
            points.append({"name": n, "label": e.get("label"), "end_text": v1.setting_text(rid, e.get("label")),
                           "median": _sav(e, "Sublet"), "weeks_hold": wh, "n_weeks": nw,
                           "holds": bool(nw > 0 and wh == nw), "source": e.get("source")})
        lo, hi, sp = r.get("lo"), r.get("hi"), r.get("span")
        cand = [(DEFAULT, dsav)] + [(p["name"], p["median"]) for p in points]
        ends = {"lo": [n for n, v in cand if v is not None and lo is not None and abs(v - lo) <= TIE],
                "hi": [n for n, v in cand if v is not None and hi is not None and abs(v - hi) <= TIE]}
        texts = {DEFAULT: v1.setting_text(rid, DEFAULT_TEXT.get(rid, d_label)),                         # C59
                 **{p["name"]: p["end_text"] for p in points}}
        zero = lo is not None and hi is not None and abs(hi - lo) <= ZERO_SPAN * (1.0 + abs(dsav or 0.0))
        # review: a row none of whose settings has a saving (every run missing) has no span either, but "no change"
        # would state a result; it reads "no run"
        no_run = bool(points) and all(p["median"] is None for p in points)
        out.append({"id": rid, "order": i, "panel": panel, "label": row_label(rid, mr),
                    "driver_label": (mr or {}).get("label") or rid, "gamma_row": bool((mr or {}).get("gamma")),
                    "lo": lo, "hi": hi, "span": sp, "zero_span": bool(zero), "lo_points": ends["lo"],
                    "hi_points": ends["hi"],
                    "lo_text": None if zero else (", ".join(_uniq(texts[n] for n in ends["lo"])) or None),
                    "hi_text": (LABELS["no_run" if no_run else "no_change"] if zero
                                else (", ".join(_uniq(texts[n] for n in ends["hi"])) or None)), "no_run": no_run,
                    "points": points, "default": {"label": texts[DEFAULT], "driver_label": d_label, "median": dsav},
                    "min_weeks_hold": r.get("min_weeks_hold"), "points_with_flips": list(r.get("points_with_flips")
                                                                                        or [])})
    return out


def _uniq(xs) -> list:
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out


def panel_order(rows: Sequence[Mapping]) -> dict[str, list[str]]:
    """Per panel the row ids sorted by span, the largest first, ties in the register's order (sf_s1, M6); a row
    without a span last."""
    return {p: [r["id"] for r in sorted((r for r in rows if r["panel"] == p),
                                        key=lambda r: (r["span"] is None, -(r["span"] or 0.0), r["order"]))]
            for p in PANELS}


def point_rows(ana: Mapping, rows: Mapping, panels: Mapping) -> list[dict]:
    """s1v2_points.tex's lines: the default point, then the settings of each row in the figure's order."""
    pts = ana["points"]

    def line(rid, rlabel, name, setting, ends, dsetting, dends):
        e = pts[name]
        sub = (e.get("by_tag") or {}).get("Sublet") or {}
        lo, hi = X.extent((sub.get("saving_pct") or {}).values())
        vp = e.get("vs_pair") or {}
        return {"row": rid, "row_label": rlabel, "point": name, "setting": setting, "ends": ends,
                "default_setting": dsetting, "default_ends": dends,
                "saving": {t: _sav(e, t) for t in TAGS4}, "sublet_lo": lo, "sublet_hi": hi,
                "delta_median": vp.get("delta_median"), "delta_min": vp.get("delta_min"),
                "delta_max": vp.get("delta_max"), "weeks_hold": vp.get("weeks_hold"), "n_weeks": vp.get("n_weeks"),
                "loss_weeks": list(vp.get("loss_weeks") or []),
                "guard_r0": (e.get("sublet_minus_a9_r0") or {}).get("median"), "source": e.get("source")}
    out = [line(DEFAULT, LABELS["default_point"], DEFAULT, None, [], None, [])]
    for p in PANELS:
        for rid in panels[p]:
            r = rows[rid]
            end_of = {n: [w for w, k in (("low", "lo_points"), ("high", "hi_points")) if n in r[k]]
                      for n in [DEFAULT] + [q["name"] for q in r["points"]]}
            for q in r["points"]:
                out.append(line(rid, r["label"], q["name"], q["end_text"], end_of[q["name"]], r["default"]["label"],
                                end_of[DEFAULT]))
    return out


def w0_rows(ana: Mapping, labels: Mapping[str, tuple[str, str]]) -> dict:
    """s1v2_w0.tex's lines from the analysis's w0 block: per point (the default first) each tag's median W0 over the
    weeks, Sublet's min-max, and the weeks in which the rule holds."""
    w = ana.get("w0")
    if not w:
        return {"rows": [], "weeks": [], "note": ana.get("w0_note") or "no w0 block"}
    names = [DEFAULT] + [n for n in need(w, "points", what=f"{ANALYSIS} w0") if n != DEFAULT]
    out = []
    for n in names:
        e = w["points"][n]
        lo, hi = X.extent(e["W0"]["Sublet"].values())
        row, setting = labels.get(n, ("", n))
        out.append({"point": n, "row_label": row, "setting": setting, "source": e.get("source"),
                    "median": {t: X.median(e["W0"].get(t, {}).values()) for t in W0_TAGS},
                    "sublet_lo": lo, "sublet_hi": hi, "weeks_hold": e.get("weeks_hold"), "n_weeks": e.get("n_weeks"),
                    "holds": dict(e.get("holds") or {})})
    return {"rows": out, "weeks": [str(x) for x in w.get("weeks") or []], "set": list(w.get("set") or []),
            "headline": w.get("headline"), "rule": w.get("rule")}


def seed_rows(ana: Mapping) -> dict:
    ss = ana.get("seed_spread") or {}
    rows = []
    for t, x in (ss.get("by_tag") or {}).items():
        mode, week, seed = (str(x.get("at") or "::").split(":") + ["", "", ""])[:3]
        rows.append({"tag": t, "key": X.key_of(t), "max_abs_diff": x.get("max_abs_diff"), "mode": mode or None,
                     "week": week or None, "seed": seed or None, "n_pairs": x.get("n_pairs"),
                     "n_missing": x.get("n_missing")})
    return {"rows": rows, "weeks": list(ss.get("weeks") or []), "seeds": list(ss.get("seeds") or []),
            "reference_seed": ss.get("reference_seed"), "note": ss.get("note")}


def runs_csv(ana: Mapping, w0s: Mapping, labels: Mapping[str, tuple[str, str]]) -> dict:
    """The data file: every r0 per setting, policy and week under the trace lender (sweep and reused settings), every
    r0 of part w0 per stress lender, and every W0 (the default's from the confirmation's part main)."""
    cols = ("part", "setting_id", "assumption", "setting", "policy", "tag", "lender", "week", "policy_seed",
            "metric", "value", "source")
    rows = []
    for n, e in ana["points"].items():
        row, setting = labels.get(n, ("", n))
        src = "confirmation, part second" if e.get("source") == "second" else "this study"
        for t in TAGS4:
            for wk, v in (((e.get("by_tag") or {}).get(t) or {}).get("r0") or {}).items():
                rows.append(("sweep", n, X.plain(row), X.plain(setting), X.plain(X.label_of(t)), t,
                             _lender_of(n, ana), wk, 0, "r0", v, src))
    table = w0s.get("table") or {}
    for t in W0_TAGS:
        for mode, by_p in (table.get(t) or {}).items():
            for n, by_w in by_p.items():
                row, setting = labels.get(n, ("", n))
                for wk, by_s in by_w.items():
                    for s, v in by_s.items():
                        rows.append(("w0", n, X.plain(row), X.plain(setting), X.plain(X.label_of(t)), t, mode, wk,
                                     int(s), "r0", v, "this study"))
    for n, e in ((ana.get("w0") or {}).get("points") or {}).items():
        row, setting = labels.get(n, ("", n))
        src = "confirmation, part main" if e.get("source") == "main" else "this study"
        for t in W0_TAGS:
            for wk, v in ((e.get("W0") or {}).get(t) or {}).items():
                rows.append(("w0", n, X.plain(row), X.plain(setting), X.plain(X.label_of(t)), t,
                             "max over the five stress lenders", wk, 0, "W0", v, src))
    return X.csv_entry(RUNS_CSV, cols, rows)


def _lender_of(name: str, ana: Mapping) -> str:
    """The lender of a sweep setting's runs: the trace lender, or the stress variant of a reused Q28 row."""
    return {"q28_rf": "L-rf", "q28_vr": "L-vr"}.get(name, TRACE)


def setting_labels(rows: Mapping, ana: Mapping) -> dict[str, tuple[str, str]]:
    """{point: (its row's label, its setting's short form)}; the default as the default point."""
    out = {DEFAULT: (LABELS["default_point"], "")}
    for r in rows.values():
        for p in r["points"]:
            out[p["name"]] = (r["label"], p["end_text"])
    for n, e in ana["points"].items():
        out.setdefault(n, (str(e.get("row") or ""), str(e.get("label") or n)))
    return out


def build(inp: Inputs) -> dict:
    ana = X.load(inp, ANALYSIS, script=NAME, run_inputs=RUN_INPUTS)
    sweep = X.load(inp, SWEEP, script=NAME, run_inputs=RUN_INPUTS)
    w0s = X.load(inp, W0, script=NAME, run_inputs=RUN_INPUTS)
    prov = X.provenance(ana, ANALYSIS)
    X.check_registered(prov, NAME)
    shas = X.check_input_shas(prov, inp, {"out/s1v2/sweep/summary.json": SWEEP, "out/s1v2/w0/summary.json": W0},
                              NAME)
    shas[ANALYSIS] = X.sha256_of(inp, ANALYSIS)
    smeta = need(sweep, "meta", what=SWEEP)
    weeks = [str(w) for w in need(ana, "weeks", what=ANALYSIS)]
    rows = bar_rows(ana, smeta)
    panels = panel_order(rows)
    by_id = {r["id"]: r for r in rows}
    labels = setting_labels(by_id, ana)
    dflt = ana["points"][DEFAULT]
    data = {"rows": by_id, "panels": panels, "default_saving_pct": _sav(dflt, "Sublet"),
            "default_holds": {"weeks_hold": (dflt.get("vs_pair") or {}).get("weeks_hold"),
                              "n_weeks": (dflt.get("vs_pair") or {}).get("n_weeks")},
            "weeks": weeks, "not_run": [{"row": n.get("row"), "reason": n.get("reason")}
                                        for n in (sweep.get("not_run") or [])
                                        if n.get("row") not in (smeta.get("reused_points") or {})],
            "tables": {"points": point_rows(ana, by_id, panels), "w0": w0_rows(ana, labels),
                       "seeds": seed_rows(ana), "s1v2_runs": runs_csv(ana, w0s, labels)},
            "headline": ana.get("headline"), "w0_headline": (ana.get("w0") or {}).get("headline"),
            "flips": ana.get("flips"),
            "meta": {"reduced": bool(prov["reduced"] or smeta.get("reduced") or (w0s.get("meta") or {}).get("reduced")),
                     "git_revision": {"analysis": prov["git_revision"], "sweep": smeta.get("git_revision"),
                                      "w0": (w0s.get("meta") or {}).get("git_revision")},
                     "analysis": prov, "inputs_sha256": shas,
                     "horizon_min": (smeta.get("grids") or {}).get("horizon_min")},
            "labels": {k: v for k, v in LABELS.items() if k not in ("caption", "moved")}}
    data["layout"] = layout(data)
    data["labels"]["values"] = values(data)
    data["labels"]["caption"] = caption(data)
    return data


def values(d: Mapping) -> dict:
    """The counts and values that the caption and the integrator's text read from the inputs (candidate \\val
    entries)."""
    pts = [p for r in d["rows"].values() for p in r["points"] if p["median"] is not None]
    w0 = d["tables"]["w0"]
    h, wh = d.get("headline") or {}, d.get("w0_headline") or {}
    return {"weeks": X.week_list(d["weeks"]), "n_weeks": len(d["weeks"]),
            "default_saving_pct": d["default_saving_pct"], "n_points": len(pts),
            "n_hold": sum(1 for p in pts if p["holds"]), "n_open": sum(1 for p in pts if not p["holds"]),
            "default_weeks_hold": d["default_holds"]["weeks_hold"], "default_n_weeks": d["default_holds"]["n_weeks"],
            "n_rows": len(d["rows"]), "w0_weeks": X.week_list(w0.get("weeks") or []),
            "w0_points": len(w0.get("rows") or []),
            # the analysis's headline, with the row names as the figure prints them
            "sublet_saving_lo": h.get("Sublet", {}).get("lo"), "sublet_saving_lo_point": h.get("Sublet", {}).get(
                "lo_point"), "sublet_saving_hi": h.get("Sublet", {}).get("hi"),
            "sublet_saving_hi_point": h.get("Sublet", {}).get("hi_point"), "max_span_pp": h.get("max_span"),
            "max_span_row": (d["rows"].get(h.get("max_span_row")) or {}).get("label"),
            "rows_span_above_threshold": [(d["rows"].get(r) or {}).get("label", r) for r in
                                          h.get("rows_span_above") or []],
            "span_threshold_pp": h.get("span_threshold_pp"), "points_all_weeks_hold": h.get("points_all_weeks_hold"),
            "point_weeks_hold": h.get("point_weeks_hold"), "point_weeks": h.get("point_weeks"),
            "guard_price_r0_median": h.get("sublet_minus_a9_r0_median"),
            "w0_points_all_weeks_hold": wh.get("points_all_weeks_hold"), "w0_point_weeks_hold": wh.get(
                "point_weeks_hold"), "w0_point_weeks": wh.get("point_weeks"), "sublet_W0_max": wh.get("sublet_W0_max"),
            "seed_spread_max": h.get("seed_spread_max")}


def caption(d: Mapping) -> str:
    v = d["labels"]["values"]
    rows = d["rows"]
    moved = [f"{rows[i]['label']}, {rows[i]['hi_text']}" if rows[i]["zero_span"] else
             f"{rows[i]['label']} from {rows[i]['lo_text'] or '--'} to {rows[i]['hi_text'] or '--'}"
             for i in d["layout"]["moved"]]
    return LABELS["caption"].format(
        sublet=style.POLICIES[KEY].label, bo=style.POLICIES["bl1_bo"].label, rr=style.POLICIES["bl5_cur"].label,
        weeks=X.weeks_text(d["weeks"]), default=d["default_saving_pct"] or 0.0, n_hold=v["n_hold"],
        n_points=v["n_points"], gamma=v1._gamma_text(d),
        moved=LABELS["moved"].format(rows="; ".join(moved)) if moved else "",
        not_run=X.tex(v1._not_run_text(d["not_run"])))


# ---------------------------------------------------------------------------------------------------------------
# layout and drawing
def _label_pt(fig, text: str) -> float:
    """The room an end label takes beyond its bar's end (pt): its width, END_GAP_PT and EDGE_CLEAR_PT."""
    return text_width_in(fig, text) * style.BP_PER_IN + END_GAP_PT + EDGE_CLEAR_PT


def reserves(fig, data: Mapping) -> list[float]:
    """Each panel's left reserve (in): its own widest row label (TICK_PT) and ROW_PAD_PT, after OUTER_IN for (a) and
    after GUTTER_IN, the gutter to the left neighbor's axes, for (b) and (c)."""
    out = []
    for i, p in enumerate(PANELS):
        w = max((text_width_in(fig, data["rows"][r]["label"]) for r in data["panels"][p]), default=0.0)
        out.append((OUTER_IN if i == 0 else GUTTER_IN) + w + ROW_PAD_PT / style.BP_PER_IN)
    return out


def constraints(fig, data: Mapping, labeled) -> dict:
    """Per panel what its window must hold at a scale s (pt per percentage point), as (value, pt) pairs: 'L' a left
    end at or below value * s - pt, 'R' a right end at or above value * s + pt; 'Z' the end labels of the labeled rows
    without a span (on one side, chosen per panel), and 'span' the data's span. Every marker, bar end and the default
    DATA_CLEAR_PT inside; the end labels of the rows in `labeled` outside their bars and EDGE_CLEAR_PT inside."""
    dflt = data["default_saving_pct"]
    out = {}
    for p in PANELS:
        L, R, Z = [], [], []
        vals = [] if dflt is None else [float(dflt)]
        for rid in data["panels"][p]:
            r = data["rows"][rid]
            vals += [float(v) for v in (r["lo"], r["hi"]) if v is not None]
            vals += [float(q["median"]) for q in r["points"] if q["median"] is not None]
            if rid not in labeled or r["lo"] is None or r["hi"] is None:
                continue
            if r["zero_span"]:
                if r["hi_text"]:
                    Z.append((float(r["hi"]), _label_pt(fig, r["hi_text"])))
                continue
            if r["lo_text"]:
                L.append((float(r["lo"]), _label_pt(fig, r["lo_text"])))
            if r["hi_text"]:
                R.append((float(r["hi"]), _label_pt(fig, r["hi_text"])))
        L += [(v, DATA_CLEAR_PT) for v in vals]
        R += [(v, DATA_CLEAR_PT) for v in vals]
        out[p] = {"L": L, "R": R, "Z": Z, "span": (max(vals) - min(vals)) if vals else 0.0,
                  "data": [min(vals), max(vals)] if vals else None}
    return out


def windows_pt(cons: Mapping, s: float, min_w: Mapping[str, float] | None = None) -> dict:
    """{panel: (left, right, side)} in pt at scale s: each panel's labels of rows without a span on the side that
    needs the narrower window (right on a tie); a window narrower than its panel's least width (min_w, pt; C62: the
    room of its title, title_min_widths) widened to it on both sides alike."""
    out = {}
    for p, c in cons.items():
        best = None
        for k, side in enumerate(("right", "left")):
            lo = [v * s - d for v, d in c["L"]] + ([v * s - d for v, d in c["Z"]] if side == "left" else [])
            hi = [v * s + d for v, d in c["R"]] + ([v * s + d for v, d in c["Z"]] if side == "right" else [])
            a, b = (min(lo), max(hi)) if lo and hi else (0.0, 2.0 * DATA_CLEAR_PT)
            if best is None or (b - a, k) < (best[1] - best[0], 0 if best[2] == "right" else 1):
                best = (a, b, side)
        a, b, side = best
        short = float((min_w or {}).get(p, 0.0)) - (b - a)
        if short > 0.0:
            a, b = a - 0.5 * short, b + 0.5 * short
        out[p] = (a, b, side)
    return out


def _total_pt(cons: Mapping, s: float, min_w: Mapping[str, float] | None = None) -> float:
    return sum(b - a for a, b, _ in windows_pt(cons, s, min_w).values())


def scale_of(cons: Mapping, avail_pt: float, min_w: Mapping[str, float] | None = None) -> float | None:
    """The largest scale s (pt per percentage point) at which the panels' windows (at least min_w wide) fit avail_pt
    together (their total width is convex and nondecreasing in s), at most avail_pt / SCALE_MAX_PP where no panel has
    a span; None where none fits."""
    cap = avail_pt / SCALE_MAX_PP if sum(c["span"] for c in cons.values()) <= 0.0 else math.inf
    hi = min(1.0, cap)
    while _total_pt(cons, hi, min_w) <= avail_pt and hi < cap:
        hi = min(2.0 * hi, cap)
    if _total_pt(cons, hi, min_w) <= avail_pt:
        return hi
    lo = hi
    while _total_pt(cons, lo, min_w) > avail_pt:
        lo *= 0.5
        if lo < 1e-6:
            return None
    for _ in range(SCALE_ITER):
        m = 0.5 * (lo + hi)
        if _total_pt(cons, m, min_w) <= avail_pt:
            lo = m
        else:
            hi = m
    return lo


def title_min_widths(fig, data: Mapping, res: Sequence[float]) -> dict[str, float]:
    """C62: per panel the least axes width (pt) at which its title, at the caption size (LABEL_PT) TITLE_GAP_PT right
    of its bold letter (common.panel_title) at the slot's left edge (geometry), ends at its axes' right end: so that
    (c)'s title stays on the page and (a)'s and (b)'s keep the gutter to the next letter, whatever the data's widths
    (as built at 7 pt, the fixture's narrow (c) put "Lenders, contracts, stress" past the page's right edge)."""
    out = {}
    for i, p in enumerate(PANELS):
        letter_in, _ = letter_box(fig, p)
        need_in = letter_in + TITLE_GAP_PT / style.BP_PER_IN + text_width_in(fig, data["labels"]["titles"][p],
                                                                               size=style.LABEL_PT)
        slot_in = res[i] - (OUTER_IN if i == 0 else GUTTER_IN)      # the slot's part left of the y spine
        out[p] = max(0.0, (need_in - slot_in) * style.BP_PER_IN)
    return out


def tick_step(s: float) -> float:
    """The x tick step of every panel: the first of TICK_STEPS that is at least TICK_MIN_PT long at scale s."""
    return next((t for t in TICK_STEPS if t * s >= TICK_MIN_PT), TICK_STEPS[-1])


def ticks_in(a: float, b: float, step: float, data: Sequence[float] | None) -> list[float]:
    """The multiples of `step` in the window [a, b], those more than a step beyond the panel's data left out (where
    only end labels are, (a)'s -40 left of "WAN 1 Gb/s")."""
    lo, hi = (a, b) if data is None else (max(a, data[0] - step), min(b, data[1] + step))
    return [float(k * step) for k in range(math.ceil(lo / step - 1e-9), math.floor(hi / step + 1e-9) + 1)]


def scale_layout(data: Mapping) -> dict:
    """The panels' widths and reserves, the common scale, each panel's window and ticks, and the rows whose end
    labels are drawn (all, unless the data would keep less than DATA_MIN_SHARE of the axes' total width: then the
    row whose labels cost the most scale gives them up, one at a time)."""
    fig = style.new_figure(NAME)
    res = reserves(fig, data)
    W = float(fig.get_size_inches()[0])
    avail = (W - style.MARGIN_RIGHT - sum(res)) * style.BP_PER_IN
    order = [i for p in PANELS for i in data["panels"][p]]
    labeled = [i for i in order if (data["rows"][i]["lo_text"] or data["rows"][i]["hi_text"])
               and data["rows"][i]["lo"] is not None and data["rows"][i]["hi"] is not None]
    cons = constraints(fig, data, set(labeled))
    min_w = title_min_widths(fig, data, res)
    total_span = sum(c["span"] for c in cons.values())
    s_min = DATA_MIN_SHARE * avail / total_span if total_span > 0 else 0.0
    s = scale_of(cons, avail, min_w)
    while (s is None or s < s_min) and labeled:
        best = None
        for i in labeled:                    # the row whose labels, left out, give the largest scale
            s2 = scale_of(constraints(fig, data, set(labeled) - {i}), avail, min_w)
            key = (s2 or 0.0, -float(data["rows"][i]["span"] or 0.0), order.index(i))
            if best is None or key > best[0]:
                best = (key, i)
        labeled.remove(best[1])
        cons = constraints(fig, data, set(labeled))
        s = scale_of(cons, avail, min_w)
    if s is None:
        raise style.StyleError(f"[{NAME}] the panels' data do not fit the figure's width at any scale")
    win = windows_pt(cons, s, min_w)
    total = sum(b - a for a, b, _ in win.values())
    widths, wins, sides, ticks, steps = [], {}, {}, {}, {}
    step = tick_step(s)
    for p in PANELS:
        a, b, side = win[p]
        extra = (avail - total) * (b - a) / total          # what the bisection leaves (below 1e-9 pt), shared out
        a, b = a - 0.5 * extra, b + 0.5 * extra
        widths.append(round(b - a, 6))
        wins[p] = [a / s, b / s]
        sides[p] = side
        # the common step; a panel where it gives fewer than two ticks near its data takes them over its whole window,
        # else the next smaller steps, until it has two
        for st in [step] + [t for t in reversed(TICK_STEPS) if t < step]:
            steps[p] = st
            ticks[p] = ticks_in(a / s, b / s, st, cons[p]["data"])
            if len(ticks[p]) < 2:
                ticks[p] = ticks_in(a / s, b / s, st, None)
            if len(ticks[p]) >= 2:
                break
    side = {}
    for p in PANELS:
        for i in data["panels"][p]:
            if i in labeled:
                side[i] = sides[p] if data["rows"][i]["zero_span"] else "both"
    moved = [i for i in order if i not in labeled and (data["rows"][i]["lo_text"] or data["rows"][i]["hi_text"])
             and data["rows"][i]["lo"] is not None]
    return {"reserves_in": [round(v, 6) for v in res], "title_min_pt": {p: round(v, 4) for p, v in min_w.items()},
            "widths_pt": widths, "scale_pt_per_pp": s,
            "windows": wins, "tick_step": steps, "ticks": ticks, "end_labels": {i: i in labeled for i in order},
            "side": side, "moved": moved, "all_fit": not moved,
            "data_share": round(s * total_span / avail, 4) if avail > 0 else None}


def geometry(fig, lay: Mapping, legend_row: bool) -> list:
    """The three panels at the layout's widths and reserves (a legend row above them where the legend goes there);
    each panel's slot starts at its row-label column (the panel letter and an in-panel legend align with it)."""
    axes = style.panel_row(fig, lay["widths_pt"], left=lay["reserves_in"], legend=bool(legend_row))
    for i, ax in enumerate(axes):
        ax._sublet_slot_left_in += OUTER_IN if i == 0 else GUTTER_IN
    return axes


def legend_pairs(lab: Mapping, default: float | None) -> list[tuple[Line2D, str]]:
    """The two marker states and, where there is a default, its grey line (a vertical rule, as drawn) with its value."""
    kw = style.policy_kwargs(KEY, lines=False, label=False)
    out = [(Line2D([], [], **kw), lab["holds"]), (Line2D([], [], **dict(kw, markerfacecolor="white")), lab["fails"])]
    if default is not None:
        rule = Line2D([], [], linestyle="None", marker="|", markersize=BAR_H * 12.0, markeredgewidth=style.REFERENCE_PT,
                      color=style.REFERENCE_GREY)
        out.append((rule, lab["default_key"].format(v=default)))
    return out


def _legend_size_in(fig, lab: Mapping, default: float | None) -> tuple[float, float]:
    """(width, height) in inches of the in-panel legend, drawn once on `fig`."""
    h, t = zip(*legend_pairs(lab, default))
    leg = fig.legend(list(h), list(t), loc="lower left", frameon=False, borderaxespad=0.0, borderpad=0.0)
    bb = leg.get_window_extent(fig.canvas.get_renderer())
    leg.remove()
    return bb.width / fig.dpi, bb.height / fig.dpi


def legend_place(data: Mapping, lay: Mapping) -> dict:
    """Where the legend goes: the panel with the most free rows (ties: the last), if it has at least LEGEND_FREE_ROWS
    of them and the legend fits its slot (row-label column and axes) and its free rows; else a legend row above the
    panels."""
    fig = style.new_figure(NAME)
    axes = geometry(fig, lay, False)
    n_max = max(len(data["panels"][p]) for p in PANELS)
    w_in, h_in = _legend_size_in(fig, data["labels"], data["default_saving_pct"])
    best = None
    for ax, p in zip(axes, PANELS):
        free = n_max - len(data["panels"][p])
        if best is None or free >= best[1]:
            best = (p, free, ax)
    p, free, ax = best
    x0, _, w, h = style.axes_rect_in(ax)
    slot = ax._sublet_slot_left_in
    pitch_in = h / n_max
    room_h = free * pitch_in - (0.5 * BAR_H * pitch_in) - 2.0 * LEGEND_PAD_PT / style.BP_PER_IN
    fits = free >= LEGEND_FREE_ROWS and w_in <= (x0 + w - slot) and h_in <= room_h
    return {"mode": "panel" if fits else "row", "panel": p if fits else None, "free_rows": int(free),
            "width_in": round(float(w_in), 4), "height_in": round(float(h_in), 4), "room_in": round(float(room_h), 4)}


def layout(data: Mapping) -> dict:
    """The C62 layout (module docstring): scale_layout's widths, scale, windows, ticks and end labels, and the
    legend's place."""
    if not any(r["lo"] is not None for r in data["rows"].values()) and data["default_saving_pct"] is None:
        raise MissingKey(f"{ANALYSIS}: no saving of Sublet at any setting")
    lay = scale_layout(data)
    lay["legend"] = legend_place(data, lay)
    lay["rule"] = (f"one x scale in all panels, each its own window; end labels {END_GAP_PT:g} pt outside their bars "
                   f"and at least {EDGE_CLEAR_PT:g} pt inside the axes, markers {DATA_CLEAR_PT:g} pt; the data keep "
                   f"at least {DATA_MIN_SHARE:g} of the axes' total width; gutter {GUTTER_IN:g} in; each panel's "
                   f"title within its axes' right end; the legend in a panel with at least {LEGEND_FREE_ROWS} free "
                   f"rows where it fits, else in a row above the panels")
    return lay



def draw_row(ax, y: float, r: Mapping, labels: bool, side: str = "both") -> list:
    p = style.policy(KEY)
    if r["lo"] is not None and r["hi"] is not None:
        bar = ax.barh(y, r["hi"] - r["lo"], left=r["lo"], height=BAR_H, color=to_rgba(p.color, BAR_ALPHA),
                      edgecolor=p.color, linewidth=BAR_EDGE_PT, zorder=style.Z_DATA)
        for pa in bar.patches:
            pa._sublet_row = r["id"]
    for state, face in ((True, None), (False, "white")):
        xs = [q["median"] for q in r["points"] if q["median"] is not None and q["holds"] is state]
        if xs:
            kw = {"markerfacecolor": face} if face else {}
            ln = style.scatter_policy(ax, KEY, xs, [y] * len(xs), **kw)
            ln._sublet_row = r["id"]
            ln._sublet_holds = state
    if not labels:
        return []
    ends = (("lo", r["lo_text"], "right", -1.0), ("hi", r["hi_text"], "left", 1.0))
    if side == "left":
        ends = (("lo", r["hi_text"], "right", -1.0),)
    out = []
    for end, text, ha, sign in ends:
        if text and r[end] is not None:
            # a text, not an annotation, so that align_baselines can move it (an annotation resets its transform)
            off = ScaledTranslation(sign * END_GAP_PT / style.BP_PER_IN, 0.0, ax.figure.dpi_scale_trans)
            t = ax.text(r[end], y, text, transform=ax.transData + off, ha=ha, va="center_baseline",
                        fontsize=style.TICK_PT, color="black", zorder=style.Z_THEORY_LABEL)
            t._sublet_role = f"end_label:{end}"
            t._sublet_row = r["id"]
            out.append(t)
    return out


def row_labels(ax, ids: Sequence[str], rows: Mapping) -> list:
    """The panel's row labels (TICK_PT) as texts ROW_PAD_PT left of its y spine, right-aligned, one per row."""
    tr = blended_transform_factory(ax.transAxes, ax.transData) + ScaledTranslation(
        -ROW_PAD_PT / style.BP_PER_IN, 0.0, ax.figure.dpi_scale_trans)
    out = []
    for i, rid in enumerate(ids):
        t = ax.text(0.0, float(i), rows[rid]["label"], transform=tr, ha="right", va="center_baseline",
                    fontsize=style.TICK_PT, color="black")
        t._sublet_role = "row_label"
        t._sublet_row = rid
        out.append(t)
    return out


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    lay = data["layout"]
    leg = lay["legend"]
    fig = style.new_figure(NAME)
    axes = geometry(fig, lay, leg["mode"] == "row")
    n_max = max(len(data["panels"][p]) for p in PANELS)
    texts = []
    for ax, p in zip(axes, PANELS):
        ids = data["panels"][p]
        if data["default_saving_pct"] is not None and ids:        # the default's line along the panel's rows only,
            ref = ax.vlines(data["default_saving_pct"], -0.5, len(ids) - 0.5, color=style.REFERENCE_GREY,
                            linewidth=style.REFERENCE_PT, zorder=style.Z_REFERENCE)    # as the y spine (the legend
            ref._sublet_role = "reference"                                           # may sit in the free rows)
        for i, rid in enumerate(ids):
            texts += draw_row(ax, float(i), data["rows"][rid], bool(lay["end_labels"].get(rid)),
                              (lay.get("side") or {}).get(rid, "both"))
        ax.set_ylim(n_max - 0.5, -0.5)
        ax.set_yticks([])
        texts += row_labels(ax, ids, data["rows"])
        if ids:
            ax.spines["left"].set_bounds(len(ids) - 0.5, -0.5)
        ax.set_xlim(*lay["windows"][p])
        ax.xaxis.set_major_locator(FixedLocator(lay["ticks"][p]))
        ax.xaxis.set_major_formatter(style.PLAIN)
        thin_tick_labels(ax)
    style.end_label_inside(axes[-1])
    center_xlabel(axes, lab["x"])
    letters = style.panel_letters(axes)
    for ax, letter, p in zip(axes, letters, PANELS):       # C62: titles at the caption size, on the letters' baseline
        panel_title(ax, letter, lab["titles"][p], fontsize=style.LABEL_PT)
    align_baselines(texts)                    # a row's mathtext labels on its plain labels' baseline (C62)
    h, t = zip(*legend_pairs(lab, data["default_saving_pct"]))
    if leg["mode"] == "panel":
        ax = axes[PANELS.index(leg["panel"])]
        x0, _, w, hh = style.axes_rect_in(ax)
        # C62: centered in the free rows, between the x axis and the panel's last bar (as built on the x axis)
        free = n_max - len(data["panels"][leg["panel"]])
        mid = 0.5 * (free + 0.5 - 0.5 * BAR_H) * hh / n_max
        lg = ax.legend(list(h), list(t), loc="center left", frameon=False, borderaxespad=0.0, borderpad=0.0,
                       bbox_to_anchor=((ax._sublet_slot_left_in - x0) / w, mid / hh))
        lg._sublet_role = "legend"
    else:
        style.legend_row(fig, [], extra=list(zip(h, t)), lines=False)
    fig._sublet_axes = dict(zip(PANELS, axes))
    return fig


# ---------------------------------------------------------------------------------------------------------------
# tables
def _ends_text(ends: Sequence[str]) -> str:
    return f" ({', '.join(ends)})" if ends else ""


def points_tex(t: Sequence[Mapping], d: Mapping) -> str:
    rows, groups, last = [], [], None
    for i, r in enumerate(t):
        first = r["row"] != last
        if first and i:
            groups.append(i)
        last = r["row"]
        name = X.tex(r["row_label"]) if first else ""
        dflt = (X.tex(r["default_setting"]) + _ends_text(r["default_ends"])) if first and r["default_setting"] else ""
        setting = "" if r["setting"] is None else X.tex(r["setting"]) + _ends_text(r["ends"])
        s = r["saving"]
        wk = "--" if r["n_weeks"] is None else X.count_text(r["weeks_hold"], r["n_weeks"])
        rows.append([name, dflt, setting, X.pct(s["Sublet"]), X.span(r["sublet_lo"], r["sublet_hi"]), X.pct(s["A9"]),
                     X.pct(s["BL1-BO"]), X.pct(s["BL5-cur"]), X.pp(r["delta_median"]),
                     X.span(r["delta_min"], r["delta_max"], scale=100.0), wk, X.pp(r["guard_r0"])])
    lab = {t_: X.tex(style.POLICIES[X.key_of(t_)].label) for t_ in TAGS4}
    bo, rr, cr = lab["BL1-BO"], lab["BL5-cur"], lab["A9"].lower()
    cap = " ".join((
        r"Sensitivity of Sublet per setting on " + X.weeks_text(d["weeks"]) + r" (the trace lender, policy seed 0):",
        r"the saving over each setting's all-fallback cost in overflow accounting, the median over the weeks and,",
        r"for Sublet, its range; the margin, " + bo + r" or " + rr + r", whichever costs less in the week, minus",
        r"Sublet in percentage points of the all-fallback cost (positive when Sublet costs less), its median and",
        r"range over the weeks without a missing run, and the weeks in which it is positive (a missing run counts as",
        r"not); and the price of the guard, Sublet minus " + cr + r" (median, percentage points). Default: the",
        r"assumption's default setting; low and high mark the settings at the ends of the row's bar in",
        r"Fig.~\ref{fig:s-sf_s1_v2}, the default point being part of every bar. Rows in the order of the figure's",
        r"panels, each sorted by span. The buffer quantile 0.999 and the rows L-rf and L-vr are the confirmation's",
        r"runs. Every per-week value is in the data file " + RUNS_CSV.replace("_", r"\_") + "."))
    head_top = (r" & & & \multicolumn{5}{c}{Saving (\%)} & \multicolumn{3}{c}{Margin (pp)} & \\" "\n"
                r"\cmidrule(lr){4-8}\cmidrule(lr){9-11}")
    header = ["Assumption", "Default", "Setting", r"\shortstack{Sublet\\median}", r"\shortstack{Sublet\\range}",
              r"\shortstack{Critical-\\ratio\\renting}", r"\shortstack{Greedy,\\back-off}",
              r"\shortstack{RetroRenting-\\style}", "Median", "Range", "Weeks", r"\shortstack{Guard\\(pp)}"]
    return X.longtable("@{}lllrrrrrrrrr@{}", cap, "tab:s-s1v2-points", header, rows, groups=groups,
                       tabcolsep=TABCOLSEP, head_top=head_top)


def w0_tex(t: Mapping, d: Mapping) -> str:
    rows = []
    for r in t["rows"]:
        m = r["median"]
        wk = "--" if r["n_weeks"] is None else X.count_text(r["weeks_hold"] or 0, r["n_weeks"])
        rows.append([X.tex(r["row_label"]), X.tex(r["setting"]), X.num(m["Sublet"]),
                     X.span(r["sublet_lo"], r["sublet_hi"], ".3f"), X.num(m["A9"]), X.num(m["BL1-BO"]),
                     X.num(m["BL5-cur"]), X.num(m["BL4"]), wk])
    lab = {t_: X.tex(style.POLICIES[X.key_of(t_)].label) for t_ in W0_TAGS}
    cap = " ".join((
        r"Worst case of the sensitivity settings on " + X.weeks_text(t.get("weeks") or []) + r": $W_0$, the largest",
        r"cost over the all-fallback cost under the five stress lenders (overflow accounting, policy seed 0), the",
        r"median over the weeks and, for Sublet, its range, at the load-scenario and transfer-fee settings and at the",
        r"default point (the confirmation's runs). Weeks: those in which Sublet's $W_0$ is below 1 and below that of",
        lab["BL1-BO"] + ", " + lab["BL5-cur"] + r" and " + lab["BL4"] + r" (a missing run counts as not). Every",
        r"stress lender's cost is in the data file " + RUNS_CSV.replace("_", r"\_") + "."))
    head_top = (r" & & \multicolumn{6}{c}{$W_0$} & \\" "\n" r"\cmidrule(lr){3-8}")
    header = ["Assumption", "Setting", r"\shortstack{Sublet\\median}", r"\shortstack{Sublet\\range}",
              r"\shortstack{Critical-\\ratio\\renting}", r"\shortstack{Greedy,\\back-off}",
              r"\shortstack{RetroRenting-\\style}", r"\shortstack{CoCaR-\\style}", "Weeks"]
    return X.longtable("@{}llrrrrrrr@{}", cap, "tab:s-s1v2-w0", header, rows, tabcolsep="3.0pt", head_top=head_top)


def seeds_tex(t: Mapping, d: Mapping) -> str:
    rows = []
    for r in t["rows"]:
        at = ("--" if r["mode"] is None else f"{X.tex(r['mode'])}, week {r['week']}, seed {r['seed']}")
        rows.append([X.tex(style.POLICIES[r["key"]].label), X.num(r["max_abs_diff"], ".4f"), at,
                     str(r["n_pairs"]), str(r["n_missing"])])
    cap = (r"Policy seeds of the confirmation on " + X.weeks_text(t.get("weeks") or []) + r" under every lender: "
           r"per policy of its seed part the largest difference of the cost over the all-fallback cost between "
           r"policy seed " + ", ".join(str(s) for s in t.get("seeds") or []) + r" and seed "
           + str(t.get("reference_seed")) + r", where it occurs, and the pairs compared and missing; the sensitivity "
           r"study runs policy seed 0.")
    return X.longtable("@{}lrlrr@{}", cap, "tab:s-s1v2-seeds", ["Policy", r"Largest $|\Delta r_0|$", "At", "Pairs",
                                                                 "Missing"], rows, tabcolsep="4.0pt")


def write_tables(data: Mapping, report: Mapping) -> None:
    t = data["tables"]
    src = [ANALYSIS, SWEEP, W0]
    paths = [write_table(TABLES[0], X.table_head(NAME, src[:2]) + points_tex(t["points"], data)),
             write_table(TABLES[1], X.table_head(NAME, [ANALYSIS]) + w0_tex(t["w0"], data)),
             write_table(TABLES[2], X.table_head(NAME, [ANALYSIS]) + seeds_tex(t["seeds"], data)),
             X.write_csv(t["s1v2_runs"], NAME)]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    return X.run(NAME, build, draw, argv, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
