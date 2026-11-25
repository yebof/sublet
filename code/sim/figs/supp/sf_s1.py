"""sf_s1: S1's tornado, with Q28's stress variants, and the tables s1_points.tex and s1_q28.tex
(design/sim_spec_ms5.md §3, §4, §7.1; M2, M5-M7, M13, M25; plan §4, part S-F).

Sublet's median saving over all-fallback in overflow accounting (M2) per register row on the E7 main week, in three
panels side by side (style.panel_row(fig, (1, 1, 1), left=(r, r, r)), r the measured width of the row labels at
style.TICK_PT, style.ytick_reserve, less the unused length of the y tick), one group of rows each, as the driver
assigns them (s1/sweep/summary.json rows.<row>.panel, and s1/q28/summary.json rows.q28_rf, q28_vr for Q28's two
variants): (a)
prices, costs and timing; (b) LLMs and demand; (c) lenders, contracts and the stress lenders L-rf and L-vr. Each row is
a bar from `lo` to `hi` (the lowest and highest median saving over the row's points and the default point, as the
driver writes them; M5) in Sublet's color (#0072B2) at alpha BAR_ALPHA with a BAR_EDGE_PT edge, each of the row's
points a Sublet marker (style.scatter_policy) on the bar, and the settings at the two ends as labels (TICK_PT) just
outside the bar (the point labels of the summary in short forms, setting_text: a unit that the row label carries left
out, ROW_UNITS; row-specific words, ROW_WORDS; end_text; the points tied at an end listed together; a row whose points all
equal the default says "no change" right of its marker, or left of it where the right has no room, and the L-vr row
says "none" instead where Sublet's L-vr runs had no buffer violation, so that an unexercised variant does not read as
robustness); rows sorted by span within each panel, the largest at the top, ties in the register's order
(meta.rows_order; M6), on one row pitch in all panels (that of the panel with the most rows); the default point's
median saving (points.default.saving_pct) as a reference line in every panel; x "Saving over all-fallback (%)" over
one common range, centered under the row, so that bar lengths compare across panels; the y spine along each panel's
rows, between the row labels and the plot (without it a left end label read as part of its row label); panel titles on
the baseline of the letters; no legend. The row labels stay under about 70 pt (ROW_LABELS), since every panel reserves
the widest.

End labels (M25). build() lays the end labels out once (layout(), on the panel geometry of draw()): the common x range
is the data range (every bar end, marker and the default) with DATA_CLEAR_PT on each side, widened, while the data keep
at least FIT_MIN_SHARE of the axes width, just enough to hold every end label EDGE_CLEAR_PT inside the axes; where no
such range holds them all, the range that holds the most rows' labels is taken, ties broken toward the largest sum of
the labeled rows' spans (so the rows at the top keep theirs first; the narrowest of those), and the end labels of the
other rows move to s1_points.tex (its column "Bar end" marks the points at each bar's two ends) and to the caption,
which names those rows with their end settings. In panels of about 1.3 in, a long bar with long end labels (the load
scenarios) has no room for them on either side (at 9 pt as built; still at C62's 7 pt). The layout (x range, the rows
whose labels are drawn and their side) is stored in the extract, so a redraw is exact; C62 (2026-11-24) rebuilt the
extract from the summaries, so that the stored layout is measured at 7 pt, the end labels' size since C62 (the x range
narrowed from [-5.9, 67.8] to [-4.0, 62.5]; the same rows labeled).

The after hook writes two tables through figs.common.write_table, from the extract's `tables`:
  s1_points.tex  a longtable, the default point first, then one row per point in the figure's order (panels (a), (b),
                 (c), each by span; the mu row's points from E7's summary, code/sim/out/e7/main/summary.json
                 runs.<mu>.<tag>, named by rows.mu.source; Q28's two Sublet variants from s1/q28/summary.json
                 runs.<variant>.Sublet): its row's default setting and the bar end(s) the default is at (on the row's
                 first line), its value, BL0a at alignment 1, the median saving and its 95% bootstrap interval in
                 overflow and in total accounting, and the bar end(s) it is at;
  s1_q28.tex     one row per policy of part q28 (E7's eight and BL3): the median cost over BL0a in overflow accounting
                 under the default lender (the driver's reference: E7's runs.1.<tag>, part q28's own default jobs for
                 BL3), under L-rf and under L-vr, the median refusals per run under L-rf by reason (the reason "lack of
                 capacity" left out where no run had one), and the median violation victims per run under L-vr, with
                 one decimal; the caption notes the equal rows, L-vr's effect and where violations occurred.
 MS6 C47 (design/ms6_spec.md M2, M4): "Sublet" above is the summaries' tag of the one-way guard around the lagged BL5 at
MS4's allowance (recorded style key sublet), drawn as the registry key sublet_ms4: its sky blue at alpha BAR_ALPHA and
its filled left triangle at 3.5 pt; the caption and the tables name it by its registry label, never "Sublet" (the
paper's A8P around A9), and part q28's other recorded keys map by ms4_lib.DRAWN_KEY (bl5 -> bl5_lag, a7_guard -> a7_ms4,
the guard around A7 at the same allowance, C46). The setting markers have a dark edge (the key's color darkened to 4.5:1
against white, Policy.label_color; MARKER_EDGE_KEYED): sky-blue triangles on the light sky-blue bars otherwise printed
with little contrast, in greyscale above all (print check of the gate). In s1_q28.tex a label is split before " + " and
its parenthesis (ms4_lib.label_lines), the further lines indented on rows of their own, so that the table stays within
the 252-pt column, and the caption states the guards' allowance from the sweep's B0_rule. Print check of the gate
(U46): the settings named after the analysis step a5 are written in words (ROW_WORDS: "Llama" for "a5 tiers",
"10 and 2 GB/s" for "a5 pair"), and s1_points.tex's head says "All-fallback (USD)" (as built "BL0a (USD)").

Run from code/sim: python -m figs.supp.sf_s1 [--from-extract [JSON]].

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): s1_points.tex's head on its later pages opens
with "Table <n>, continued".
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

import matplotlib as mpl
from matplotlib.colors import to_rgba
from matplotlib.ticker import FixedLocator, MaxNLocator

from figs import style
from figs.common import (MissingKey, align_baselines, cli, maybe, need, panel_title, text_width_in, thin_tick_labels,
                         write_table)
from figs.inputs import Inputs
from figs.supp.ms4_lib import DRAWN_KEY, b0_share_text, center_xlabel, grid_counts, label_lines, runs_text, tag_of
from figs.table3_e7 import HORIZON_WORDS

NAME = "sf_s1"
SWEEP = "code/sim/out/s1/sweep/summary.json"
Q28 = "code/sim/out/s1/q28/summary.json"
E7 = "code/sim/out/e7/main/summary.json"          # the mu row's points (rows.mu.source.file), for s1_points.tex
KEYS = style.SUPP_POLICIES_MS5[NAME]              # sublet_ms4
# C47 (design/ms6_spec.md M2, M4): S1 ran the one-way guard around the lagged BL5 at MS4's allowance (the summaries'
# tag Sublet, recorded style key sublet), drawn as its configuration key sublet_ms4; part q28's other recorded keys
# map by ms4_lib.DRAWN_KEY too (bl5 -> bl5_lag, a7_guard -> a7_ms4)
KEY = "sublet_ms4"
MARKER_EDGE_KEYED = True        # C47: the setting markers edged in style.policy(KEY).label_color (print check)
PANELS = ("a", "b", "c")
Q28_ROWS = ("q28_rf", "q28_vr")
Q28_VARIANTS = {"q28_rf": "rf", "q28_vr": "vr"}
TABLES = ("s1_points.tex", "s1_q28.tex")
BAR_H = 0.6                     # bar height over the row pitch (not in §7.1)
BAR_ALPHA = 0.35                # §7.1
BAR_EDGE_PT = 0.6               # §7.1
END_GAP_PT = 4.5                # an end label this far outside its bar's end: 2.2 pt clear of the edge of the 4-pt end
#                                 marker (radius 2 pt and half its 0.6-pt edge; print check 2026-10-30)
EDGE_CLEAR_PT = 4.0             # ... and at least this far inside the axes' sides: clear of the y spine, beyond which
#                                 the row labels sit, and of the next panel's row labels (not in §7.1)
DATA_CLEAR_PT = 4.0             # every marker's center at least this far inside the axes' sides (a 4-pt marker's
#                                 radius and edge, 2.3 pt, and room before the next panel's row labels; not in §7.1)
FIT_MIN_SHARE = 0.70            # the data keep at least this share of the axes width when the range widens for labels
#                                 (0.75 until the print check of 2026-10-30, which left both ends of alpha unlabeled;
#                                 on the E7 week the labels drawn need 0.72)
FIT_STEPS = 40                  # widths tried from the data range with its clearance to FIT_MIN_SHARE
TABCOLSEP = "3.4pt"             # s1_points.tex at footnotesize, as the MS4 tables (not in §7.1)
Q28_TABCOLSEP = "3.0pt"         # s1_q28.tex: within the 252-pt column of the two-column IEEEtran supplement
ZERO_SPAN = 1e-9                # a row whose span is at most this (relative to 1 + |default|) has "no change"
style.register_supplementary(NAME, "W2", 2.5)

# the figure's row labels (mathtext; LaTeX in the tables and the caption), by the driver's row id; a row without one
# keeps the driver's label. Each is at most about 70 pt at 9 pt (55 pt at C62's 7 pt), since every panel reserves the
# widest of all three
# (§7.1): a unit goes into the row label rather than into both end labels (ROW_UNITS)
ROW_LABELS = {"alpha": r"$\alpha$", "alpha_p": r"$\alpha_p$", "mu": r"$\mu/\tilde{\beta}$",
              "mu_split": r"Split of $\mu$", "load_scenario": "Load scenario", "phi": r"$\varphi$",
              "kappa_L": r"$\kappa$ of L", "catalog": "LLM catalog", "precision": "Weight precision",
              "gpt4o_mini": "gpt-4o-mini tier",
              "s_S": r"$s_S$", "xi": r"Sources $\xi$", "wildchat": "WildChat window",
              "own_capacity": r"Own capacity $C^0$", "smoothing": "Smoothing (min)",
              "lease_quantile": "Lease quantile", "layer_width": "Layer GPUs",
              "n_layers": r"Offered layers $V_\ell$", "protected_term": "Protected term",
              "buffer_quantile": "Buffer quantile", "tightness": "Market tightness", "delta1": r"$\delta_1/q$",
              "slo_class": "SLO classes", "transfer_fee": "Transfer fee", "slow_slot": "Slow-loop slot",
              "q28_rf": "Refusals (L-rf)", "q28_vr": "Violations (L-vr)"}
# the unit that a row's label carries, left out of its settings ("5 min" at the bar's end reads "5")
ROW_UNITS = {"smoothing": "min", "layer_width": "GPUs"}
# row-specific short forms of the driver's setting labels: the transfer fee's default is no fee (its other end names
# the fee by its rho), not rho = 0; the strictest SLO class is the one where every client is strict; the sources xi
# are one series per region (regional) or one series for all regions at different offsets (shared)
ROW_WORDS = {"transfer_fee": {"0": "no fee"}, "slo_class": {"all strict": "strict"},
             "xi": {"per region": "regional", "one series": "shared"},
             # C47 (print check of the gate): the analysis step's name (a5) out of the drawn and printed settings: the
             # default load scenarios, half the lenders at 10 GB/s and half at 2 GB/s (config.DEFAULT_SCENARIOS), and
             # the Llama tiers (llama3-8b, llama3-70b, llama3.1-405b; traces.catalog.A5_TIER) as "Llama" ("Llama 3",
             # 2.2 pt wider than "a5 tiers", did not fit (b), and the layout then moved both of the row's end labels to
             # s1_points.tex)
             "load_scenario": {"a5 pair": "10 and 2 GB/s"}, "catalog": {"a5 tiers": "Llama"}}
# end-label forms of the driver's point labels (§7.1: short forms): the stress lenders as off (the default lender)
# and on; the multipliers and rho in math
END_WORDS = {"L-tr": "off", "L-rf": "on", "L-vr": "on"}
# rows that act through the protected contract alone: where Sublet leases no protected capacity at any of their
# settings they cannot change its saving, and the caption says why
PROTECTED_ROWS = ("alpha_p", "protected_term")
PROTECTED_CLASS = "protected"   # the contract class of the protected lease in gpu_hour_share (calib.contract_klass)
Q28_VR_ROW = "q28_vr"           # the row whose zero span says "none" (no violation) when Sublet's L-vr runs had none
LABELS = {"x": "Saving over all-fallback (%)", "titles": {"a": "Prices, costs, timing", "b": "LLMs and demand",
                                                           "c": "Lenders, contracts, stress"},
          "no_change": "no change", "no_violation": "none", "default_point": "Default point",
          # C47: the policy by its registry label ({name}); "Sublet" (MS4's name of the configuration) is the paper's
          # A8P around A9 since MS5b
          "caption": ("The saving over all-fallback of {name} in overflow accounting per assumption on E7's main week "
                      "({horizon}; medians over {runs}; each setting's saving over its own all-fallback cost). A bar "
                      "runs from the lowest to the highest median over the row's settings (markers) and the default "
                      "(grey line, {default:.1f}%), labeled with the settings at its ends; rows sorted by span. "
                      "{gamma}Its allowance $B_0$ is {b0} of each run's all-fallback cost. {protected}L-rf refuses "
                      "purchases on unavailable layers, L-vr turns buffer violations into reclaims without notice "
                      "(off: the default lender; on: the variant){vr}. The {mu} row reuses E7's runs. {moved}"
                      "Not run: {not_run}."),
          "gamma": ("$\\Gamma$ is re-solved to keep the market tightness at its default {tight} (in its own row, at "
                    "the row's values) {where}. "),
          "protected": "{rows} change{s} nothing: the policy leases no protected capacity at {these}. ",
          "vr": "; no buffer violation occurred in its L-vr runs, so they equal the default lender's",
          "moved": "Bar ends not labeled: {rows} (Table~\\ref{{tab:s1-points}}). "}
# the caption's names and reasons for the driver's rows not run (s1/sweep/summary.json not_run): short reasons by the
# start of the driver's reason, first match (a reason without a match keeps its text up to the first ':' or ';'), and
# paper names by the driver's row text (a row without one keeps the driver's text)
NOT_RUN_REASONS = (("no sweep in the register", "no sweep in the register"),
                   ("its sweep is its default", "its sweep is the default"),
                   ("no traced source", "no source"), ("not built: no source", "no source"),
                   ("not built", "not built"), ("not defined", "not defined"),
                   ("identical to the default", "identical to the default"),
                   ("the dense arrays", "beyond the evaluation's memory budget"))
NOT_RUN_ROWS = {"warm-peer and SSD load models": "the warm-peer and SSD load-rate scaling",
                "client unit 1/u": r"the client unit $1/u$", "pool width zeta": r"the pool width $\zeta$",
                "tier map": "the tier map",
                "per-tier tokens-per-conversation factor": "a per-tier tokens-per-conversation factor",
                "clock alignment at local midnight": "a clock alignment at local midnight",
                "non-causal smoothing window": "a non-causal smoothing window",
                "scenario assignment per region pair": "a load scenario per region pair",
                "offered layers V_l as the whole block below the lease-size quantile":
                    r"$V_\ell$ as the whole block below the lease quantile",
                "offered layers V_l as a share of the mean lendable capacity":
                    r"$V_\ell$ as a share of the mean lendable capacity",
                "a uniform kappa multiplier": r"a uniform $\kappa$ multiplier"}


def row_label(row_id: str, row: Mapping) -> str:
    return ROW_LABELS.get(row_id) or str(row.get("label") or row_id)


def end_text(label: Any) -> str:
    """The short form of a point label at a bar's end: END_WORDS, 'x0.5' as '×0.5', 'rho = 4' as 'ρ = 4' (mathtext,
    which LaTeX reads too); idempotent, so that a setting_text() stays as it is."""
    s = str(label)
    if s in END_WORDS:
        return END_WORDS[s]
    if s.startswith("x"):
        try:
            float(s[1:])
            return r"$\times$" + s[1:]
        except ValueError:
            pass
    if s.startswith("rho"):
        return r"$\rho$" + s[3:]
    return s


def setting_text(row_id: str, label: Any) -> str:
    """A setting of row `row_id` as the figure and the tables write it: the row's ROW_WORDS form, its number alone
    where the row label carries its unit (ROW_UNITS: '5 min' as '5'), then end_text()."""
    s = str(label)
    s = ROW_WORDS.get(row_id, {}).get(s, s)
    unit = ROW_UNITS.get(row_id)
    if unit and s.endswith(" " + unit):
        try:
            float(s[:-len(unit) - 1])
            s = s[:-len(unit) - 1]
        except ValueError:
            pass
    return end_text(s)


def _agg(ent: Any, field: str) -> dict:
    """{median, lo, hi, n} of a metrics.aggregate field of `ent` (None where missing)."""
    a = ent.get(field) if isinstance(ent, Mapping) else None
    a = a if isinstance(a, Mapping) else {}
    lo, hi = (a.get("median_ci95") or [None, None])[:2]
    return {"median": a.get("median"), "lo": lo, "hi": hi, "n": a.get("n")}


def _protected_share(ent: Any) -> float | None:
    """The protected contract's share of a sweep point's leased GPU-hours (0 where gpu_hour_share has no protected
    class; None where the point has no gpu_hour_share)."""
    g = ent.get("gpu_hour_share") if isinstance(ent, Mapping) else None
    return float(g.get(PROTECTED_CLASS) or 0.0) if isinstance(g, Mapping) else None


def bar_rows(sweep: Mapping, q28: Mapping) -> list[dict]:
    """Every tornado row in the register's order (meta.rows_order, then Q28's): id, panel, label, gamma_row, lo, hi,
    span, the end texts, the points (name, the driver's label, the figure's setting text, median, and for a sweep
    point the protected share of its GPU-hours) and the default (its setting text as `label`, the driver's as
    `driver_label`, median, protected share); the L-vr row also the largest number of violation events in Sublet's
    L-vr runs, and a zero-span L-vr row without any says "none" (LABELS["no_violation"]) in place of "no change"."""
    order = list(need(sweep, "meta", "rows_order", what=SWEEP)) + [r for r in Q28_ROWS]
    sweep_points = sweep.get("points") or {}
    dflt_share = _protected_share(sweep_points.get("default"))
    q28_tag = tag_of(need(q28, "meta", "tags", what=Q28), (KEY,), Q28, drawn=DRAWN_KEY)[KEY]
    out = []
    for i, rid in enumerate(order):
        src, what = (q28, Q28) if rid in Q28_ROWS else (sweep, SWEEP)
        r = need(src, "rows", rid, what=what)
        dflt = need(r, "default", what=f"{what} rows.{rid}")
        kind = (r.get("source") or {}).get("kind")
        pts = [{"name": n, "label": p.get("label"), "end_text": setting_text(rid, p.get("label")),
                "median": p.get("saving_pct_median"), "n_runs": p.get("n_runs"),
                "protected_share": _protected_share(sweep_points.get(n)) if src is sweep and kind == "s1" else None}
               for n, p in need(r, "points", what=f"{what} rows.{rid}").items() if not n.endswith("_note")]
        texts = {"default": setting_text(rid, dflt.get("label"))}
        texts.update({p["name"]: p["end_text"] for p in pts})
        lo, hi, span = r.get("lo"), r.get("hi"), r.get("span")
        zero = lo is not None and hi is not None and abs(hi - lo) <= ZERO_SPAN * (1.0 + abs(dflt.get(
            "saving_pct_median") or 0.0))
        ends = {"lo": [n for n in r.get("lo_points") or [] if n in texts],
                "hi": [n for n in r.get("hi_points") or [] if n in texts]}
        row = {"id": rid, "order": i, "panel": need(r, "panel", what=f"{what} rows.{rid}"),
               "label": row_label(rid, r), "driver_label": r.get("label"), "gamma_row": r.get("gamma_row"),
               "lo": lo, "hi": hi, "span": span, "zero_span": bool(zero),
               "lo_points": ends["lo"], "hi_points": ends["hi"],
               "lo_text": None if zero else ", ".join(texts[n] for n in ends["lo"]) or None,
               "hi_text": LABELS["no_change"] if zero else (", ".join(texts[n] for n in ends["hi"]) or None),
               "points": pts, "default": {"label": texts["default"], "driver_label": dflt.get("label"),
                                          "median": dflt.get("saving_pct_median"), "protected_share": dflt_share},
               "complete": r.get("complete"), "points_missing": list(r.get("points_missing") or []),
               "source": kind}
        if rid == Q28_VR_ROW:
            ev = maybe(q28, "runs", Q28_VARIANTS[rid], q28_tag, "violation_events", "max")[0]
            row["violation_events_max"] = ev
            row["no_violation"] = bool(zero and ev is not None and float(ev) == 0.0)
            if row["no_violation"]:
                row["hi_text"] = LABELS["no_violation"]
        out.append(row)
    return out


def panel_order(rows: Sequence[Mapping]) -> dict[str, list[str]]:
    """Per panel the row ids sorted by span, the largest first (the top), ties in the register's order (M6); a row
    without a span last."""
    out = {}
    for p in PANELS:
        rs = [r for r in rows if r["panel"] == p]
        out[p] = [r["id"] for r in sorted(rs, key=lambda r: (r["span"] is None, -(r["span"] or 0.0), r["order"]))]
    return out


# ---------------------------------------------------------------------------------------------------------------
# tables' data
def point_rows(sweep: Mapping, q28: Mapping, e7: Mapping | None, rows: Sequence[Mapping],
               panels: Mapping[str, Sequence[str]]) -> list[dict]:
    """s1_points.tex's rows: the default point, then each tornado row's points, the rows in the figure's order (panels
    (a), (b), (c), each by span as drawn); per point its value, BL0a at alignment 1 (or the lowest alignment run), the
    median saving with its 95% interval in both accountings and the bar ends it is at, and its row's default setting
    with the bar ends the default is at (the default point is part of every bar)."""
    out = []
    al = sorted(need(sweep, "meta", "grids", "alignments", what=SWEEP))
    c1 = str(al[0])

    def entry(rid, rlabel, name, value, ent, bl0a, src):
        return {"row": rid, "row_label": rlabel, "point": name, "value": value, "alignment": c1,
                "bl0a_usd": bl0a, "saving": _agg(ent, "saving_pct"), "saving_total": _agg(ent, "saving_pct_total"),
                "source": src}
    dflt = need(sweep, "points", "default", what=SWEEP)
    out.append({**entry("default", LABELS["default_point"], "default", None, dflt,
                        (dflt.get("bl0a_usd") or {}).get(c1), "s1_sweep"), "ends": [],
                "default_setting": None, "default_ends": []})
    e7_tag = None if e7 is None else tag_of(need(e7, "meta", "tags", what=E7), (KEY,), E7, drawn=DRAWN_KEY)[KEY]
    q28_tag = tag_of(need(q28, "meta", "tags", what=Q28), (KEY,), Q28, drawn=DRAWN_KEY)[KEY]
    by_id = {r["id"]: r for r in rows}
    for r in [by_id[i] for p in PANELS for i in panels[p]]:
        ends = {n: [e for e, k in (("low", "lo_points"), ("high", "hi_points")) if n in r[k]] for n in
                ["default"] + [p["name"] for p in r["points"]]}
        for p in r["points"]:
            if r["source"] == "e7":
                mu = p["name"][2:] if p["name"].startswith("mu") else None
                ent = maybe(e7, "runs", mu, e7_tag)[0] if (e7 is not None and mu is not None) else None
                bl0a = maybe(e7, "meta", "bl0a_usd", c1)[0] if e7 is not None else None
                src = "e7"
            elif r["id"] in Q28_ROWS:
                ent = maybe(q28, "runs", Q28_VARIANTS[r["id"]], q28_tag)[0]
                bl0a = (dflt.get("bl0a_usd") or {}).get(c1)
                src = "s1_q28"
            else:
                ent = maybe(sweep, "points", p["name"])[0]
                bl0a = ((ent or {}).get("bl0a_usd") or {}).get(c1)
                src = "s1_sweep"
            row = entry(r["id"], r["label"], p["name"], p["end_text"], ent, bl0a, src)
            if row["saving"]["median"] is None:
                row["saving"]["median"] = p["median"]          # the figure's value where the entry lacks it
            row["ends"] = ends[p["name"]]
            row["default_setting"] = r["default"]["label"]
            row["default_ends"] = ends["default"]
            out.append(row)
    return out


def q28_rows(q28: Mapping) -> dict:
    """s1_q28.tex's rows: one per policy of part q28 (runs.rf's order), with the reference and both variants."""
    tags = need(q28, "meta", "tags", what=Q28)
    out = []
    for tag in need(q28, "runs", "rf", what=Q28):
        if tag.endswith("_note"):
            continue
        rf, vr = maybe(q28, "runs", "rf", tag)[0] or {}, maybe(q28, "runs", "vr", tag)[0] or {}
        key = DRAWN_KEY.get((tags.get(tag) or {}).get("style_key"), (tags.get(tag) or {}).get("style_key"))   # C47
        ref = rf.get("reference") or {}
        refus = rf.get("refusals") or {}
        out.append({"tag": tag, "key": key, "label": style.POLICIES[key].label if key in style.POLICIES else tag,
                    "default": ref.get("overflow_over_bl0a_median"), "default_source": ref.get("source"),
                    "rf": _agg(rf, "overflow_over_bl0a")["median"], "vr": _agg(vr, "overflow_over_bl0a")["median"],
                    "refused_unavailable": _agg(refus, "unavailable")["median"],
                    "refused_capacity": _agg(refus, "capacity")["median"],
                    "refused_capacity_max": maybe(refus, "capacity", "max")[0],
                    "victims": _agg(vr, "violation_victims")["median"],
                    "violation_events_max": maybe(vr, "violation_events", "max")[0],
                    "guarded": bool((tags.get(tag) or {}).get("a8")),
                    "abort_share": {"rf": rf.get("abort_share"), "vr": vr.get("abort_share")},
                    "n_runs": {"rf": rf.get("n_runs"), "vr": vr.get("n_runs")}})
    return {"rows": out}


def horizon_text(minutes: float) -> str:
    m = float(minutes)
    return HORIZON_WORDS.get(int(m), f"{m:g} min") if m.is_integer() else f"{m:g} min"


def build(inp: Inputs) -> dict:
    sweep, q28 = inp.json(SWEEP), inp.json(Q28)
    meta = need(sweep, "meta", what=SWEEP)
    tag = need(meta, "tag", what=f"{SWEEP} meta")
    if DRAWN_KEY.get(tag.get("style_key"), tag.get("style_key")) != KEY:           # C47: the recorded key's
        raise MissingKey(f"{SWEEP} meta.tag.style_key is {tag.get('style_key')!r}, not one drawn as {KEY!r}")
    rows = bar_rows(sweep, q28)
    mu_src = next((r for r in rows if r["source"] == "e7"), None)
    e7 = None
    if mu_src is not None:
        src_file = (need(sweep, "rows", mu_src["id"], what=SWEEP).get("source") or {}).get("file")
        if src_file != E7:
            raise MissingKey(f"{SWEEP} rows.{mu_src['id']}.source.file is {src_file!r}, not {E7}")
        e7 = inp.json(E7)
    default = need(sweep, "points", "default", "saving_pct", "median", what=SWEEP)
    grids = need(meta, "grids", what=f"{SWEEP} meta")
    n_al, n_se = grid_counts(grids, f"{SWEEP} meta.grids")
    prices = (meta.get("default_prices") or {})
    panels = panel_order(rows)
    out = {"rows": {r["id"]: r for r in rows}, "panels": panels, "default_saving_pct": default,
           "not_run": [{"row": n.get("row"), "reason": n.get("reason")} for n in need(sweep, "not_run", what=SWEEP)],
           "tables": {"points": point_rows(sweep, q28, e7, rows, panels), "q28": q28_rows(q28)},
           "grid": {"n_alignments": n_al, "n_policy_seeds": n_se, "horizon_min": grids.get("horizon_min"),
                    "alignments": list(grids.get("alignments") or []),
                    "B0_rule": meta.get("B0_rule"), "default_prices": prices,
                    "q28_horizon_min": (need(q28, "meta", "grids", what=Q28) or {}).get("horizon_min")},
           "meta": {"git_revision": {"sweep": meta.get("git_revision"), "q28": need(q28, "meta", what=Q28).get(
               "git_revision"), "e7": None if e7 is None else e7["meta"].get("git_revision")},
               "reduced": bool(meta.get("reduced") or q28["meta"].get("reduced"))},
           "labels": dict(LABELS), "sources": list(inp.sources)}
    out["layout"] = layout(out)
    out["labels"]["caption"] = caption(out)
    return out


def caption(d: Mapping) -> str:
    """The caption draft of §7.1 from the extract: the base (each setting over its own all-fallback cost), the bars
    and the reference line, Gamma re-solved at the rows that change supply or the LLMs, the allowance, the protected
    rows that cannot act (PROTECTED_ROWS), the stress lenders and whether L-vr was exercised, the rows whose end
    labels moved (by their figure labels) and the rows not run (§3.5), with short reasons."""
    g = d["grid"]
    rows = d["rows"]
    moved = [f"{rows[i]['label']}, {rows[i]['hi_text']}" if rows[i]["zero_span"] else
             f"{rows[i]['label']} from {rows[i]['lo_text'] or '–'} to {rows[i]['hi_text'] or '–'}"
             for i in d["layout"]["moved"]]
    b0 = b0_share_text(g.get("B0_rule"), tex=True) or str(g.get("B0_rule") or "the MS4 rule")   # C47: "10\\%"
    vr = rows.get(Q28_VR_ROW) or {}
    return LABELS["caption"].format(
        horizon=horizon_text(g["horizon_min"]) if g.get("horizon_min") else "–",
        runs=runs_text(g["n_alignments"], g["n_policy_seeds"], times="×"), default=d["default_saving_pct"],
        gamma=_gamma_text(d), b0=b0, protected=_protected_text(d), vr=LABELS["vr"] if vr.get("no_violation") else "",
        mu=rows["mu"]["label"] if "mu" in rows else "mu", name=style.POLICIES[KEY].label,
        moved=LABELS["moved"].format(rows="; ".join(moved)) if moved else "", not_run=_not_run_text(d["not_run"]))


def _prose(label: str) -> str:
    """A row label in running text: the first letter in lower case, unless the label starts with math or lower case,
    or its first word is an acronym or a name with an inner capital (LLM catalog, SLO classes, WildChat window)."""
    first = label.split(" ")[0]
    if label.startswith("$") or not first[:1].isupper() or any(c.isupper() for c in first[1:]):
        return label
    return label[0].lower() + label[1:]


def _gamma_text(d: Mapping) -> str:
    """Where Gamma is re-solved: per panel 'in every row of (x)' or 'in the ... rows of (x)'; the tightness row's own
    target named where it is one of them."""
    rows, where = d["rows"], []
    for p in PANELS:
        ids = d["panels"][p]
        gam = [i for i in ids if rows[i]["gamma_row"]]
        if gam and len(gam) == len(ids):
            where.append(f"in every row of ({p})")
        elif gam:
            where.append(f"in the {_list([_prose(rows[i]['label']) for i in gam])} row{'s' if len(gam) > 1 else ''} "
                         f"of ({p})")
    if not where:
        return ""
    t = rows.get("tightness")
    text = LABELS["gamma"].format(tight=t["default"]["label"] if t else "–", where=_list(where))
    return text if t and t["gamma_row"] else text.replace(" (in its own row, at the row's values)", "")


def _protected_text(d: Mapping) -> str:
    """The rows of PROTECTED_ROWS without a span where Sublet leased no protected GPU-hour at any setting (the default
    included), with the reason; '' where there is none."""
    ids = []
    for i in PROTECTED_ROWS:
        r = d["rows"].get(i)
        if not r or not r["zero_span"]:
            continue
        shares = [r["default"].get("protected_share")] + [p.get("protected_share") for p in r["points"]]
        if all(s is not None and s == 0.0 for s in shares):
            ids.append(i)
    if not ids:
        return ""
    names = "the " + _list([_prose(d["rows"][i]["label"]) for i in ids]) + (" rows" if len(ids) > 1 else " row")
    return LABELS["protected"].format(rows=names[0].upper() + names[1:], s="" if len(ids) > 1 else "s",
                                      these="their settings" if len(ids) > 1 else "its settings")


def _not_run_text(not_run: Sequence[Mapping]) -> str:
    """The rows not run, grouped by their short reason (NOT_RUN_REASONS) in the order of first appearance."""
    groups: dict[str, list[str]] = {}
    for n in not_run:
        reason = str(n.get("reason") or "")
        short = next((s for start, s in NOT_RUN_REASONS if reason.startswith(start)), None)
        if short is None:
            short = reason.split(":")[0].split(";")[0].strip() or "no reason given"
        groups.setdefault(short, []).append(NOT_RUN_ROWS.get(str(n.get("row")), str(n.get("row"))))
    return "; ".join(f"{_list(rs)} ({s})" for s, rs in groups.items()) or "none"


def _list(xs: Sequence[str]) -> str:
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


# ---------------------------------------------------------------------------------------------------------------
# layout and drawing
def geometry(fig, data: Mapping) -> list:
    """The three panels at their places: left reserve r = the widest row label at TICK_PT (style.ytick_reserve), the
    same for each panel (§7.1), less the y tick's length, since the row labels have no tick (draw() sets its length
    to 0, and the labels then sit at the tick pad from the spine)."""
    r = (style.ytick_reserve(fig, [row["label"] for row in data["rows"].values()])
         - mpl.rcParams["ytick.major.size"] / style.BP_PER_IN)
    return style.panel_row(fig, (1, 1, 1), left=(r, r, r))


def data_extent(data: Mapping) -> tuple[float, float]:
    vals = [data["default_saving_pct"]]
    for r in data["rows"].values():
        vals += [v for v in (r["lo"], r["hi"]) if v is not None]
        vals += [p["median"] for p in r["points"] if p["median"] is not None]
    return min(vals), max(vals)


def layout(data: Mapping) -> dict:
    """The x range and the rows whose end labels are drawn (see the module docstring): the narrowest widening of the
    data range with DATA_CLEAR_PT on each side (FIT_STEPS widths up to the one where the data span FIT_MIN_SHARE of
    the axes) that holds every end label inside the axes,
    else the one that holds the most rows' labels, ties broken toward the largest sum of the labeled rows' spans, so
    that the rows at the top of the panels keep theirs first (the narrowest of those; the range then placed, among
    those that hold them, nearest to centering the data)."""
    fig = style.new_figure(NAME)
    ax = geometry(fig, data)[0]
    w_pt = style.axes_rect_in(ax)[2] * style.BP_PER_IN
    lo_d, hi_d = data_extent(data)
    span = max(hi_d - lo_d, 1e-9)
    c = DATA_CLEAR_PT
    R0 = span / (1.0 - 2.0 * c / w_pt)                 # the data with DATA_CLEAR_PT on each side
    R_max = max(R0, span / FIT_MIN_SHARE)              # the widest range: the data on FIT_MIN_SHARE of the width
    need_rows = []                                     # (row, lo, hi, [(left need, right need, side), ...])
    for r in data["rows"].values():
        if r["lo"] is None or r["hi"] is None:
            continue
        wl = text_width_in(fig, r["lo_text"]) * 72.0 + END_GAP_PT + EDGE_CLEAR_PT if r["lo_text"] else 0.0
        wr = text_width_in(fig, r["hi_text"]) * 72.0 + END_GAP_PT + EDGE_CLEAR_PT if r["hi_text"] else 0.0
        # a row without a span says "no change" right of its marker, or left of it where the right has no room
        opts = [(0.0, wr, "right"), (wr, 0.0, "left")] if r["zero_span"] else [(wl, wr, "both")]
        need_rows.append((r["id"], r["lo"], r["hi"], opts))
    spans = {r["id"]: float(r["span"] or 0.0) for r in data["rows"].values()}

    def score(fit):                                    # most rows labeled, then the largest spans labeled
        return len(fit), round(sum(spans[i] for i in fit), 9)
    best = None
    for k in range(FIT_STEPS + 1):
        R = R0 + k * (R_max - R0) / FIT_STEPS
        s = w_pt / R                                   # pt per percentage point
        # a row's option fits iff a lies in [hi + wr / s - R, lo - wl / s]; the data iff a lies in
        # [hi_d + c / s - R, lo_d - c / s]
        lo_a, hi_a = hi_d + c / s - R, lo_d - c / s
        ivs = [(rid, side, max(h + wr / s - R, lo_a), min(lo_r - wl / s, hi_a))
               for rid, lo_r, h, opts in need_rows for wl, wr, side in opts]
        cands = sorted({lo_a, hi_a, *[x for _, _, x0, x1 in ivs for x in (x0, x1) if lo_a <= x <= hi_a]})
        center = 0.5 * (lo_a + hi_a)

        def fits(a):
            out = {}
            for rid, side, x0, x1 in ivs:
                if rid not in out and x0 <= a + 1e-12 and a <= x1 + 1e-12:
                    out[rid] = side
            return out
        top = max(cands, key=lambda a: (*score(fits(a)), -abs(a - center)))
        fit = fits(top)
        if best is None or score(fit) > score(best[2]):
            best = (top, top + R, fit)
        if len(fit) == len(need_rows):
            break
    a, b, fit = best
    moved = [i for p in PANELS for i in data["panels"][p] if i not in fit and
             (data["rows"][i]["lo_text"] or data["rows"][i]["hi_text"])]
    return {"x_range": [float(a), float(b)], "end_labels": {i: i in fit for p in PANELS for i in data["panels"][p]},
            "side": {i: fit[i] for p in PANELS for i in data["panels"][p] if i in fit},
            "moved": moved, "all_fit": not moved,
            "rule": f"the data keep at least {FIT_MIN_SHARE:g} of the axes width; end labels {END_GAP_PT:g} pt "
                    f"outside their bars and at least {EDGE_CLEAR_PT:g} pt inside the axes"}


def x_ticks(a: float, b: float) -> list[float]:
    t = MaxNLocator(5, steps=[1, 2, 2.5, 5, 10]).tick_values(a, b)
    return [float(v) for v in t if a - 1e-9 <= v <= b + 1e-9]


def draw_row(ax, y: float, r: Mapping, labels: bool, side: str = "both") -> None:
    c = style.policy(KEY).color
    if r["lo"] is not None and r["hi"] is not None:
        bar = ax.barh(y, r["hi"] - r["lo"], left=r["lo"], height=BAR_H, color=to_rgba(c, BAR_ALPHA), edgecolor=c,
                      linewidth=BAR_EDGE_PT, zorder=style.Z_DATA)
        for pa in bar.patches:
            pa._sublet_row = r["id"]
    xs = [p["median"] for p in r["points"] if p["median"] is not None]
    if xs:
        edge = {"markeredgecolor": style.policy(KEY).label_color} if MARKER_EDGE_KEYED else {}
        ln = style.scatter_policy(ax, KEY, xs, [y] * len(xs), **edge)
        ln._sublet_row = r["id"]
    if not labels:
        return
    ends = (("lo", r["lo_text"], "right", -1.0), ("hi", r["hi_text"], "left", 1.0))
    if side == "left":                                 # a row without a span: "no change" left of its marker
        ends = (("lo", r["hi_text"], "right", -1.0),)
    for end, text, ha, sign in ends:
        if text and r[end] is not None:
            t = ax.annotate(text, xy=(r[end], y), xytext=(sign * END_GAP_PT, 0.0), textcoords="offset points", ha=ha,
                            va="center_baseline", fontsize=style.TICK_PT, color="black", zorder=style.Z_THEORY_LABEL)
            t._sublet_role = f"end_label:{end}"
            t._sublet_row = r["id"]


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    lay = data["layout"]
    fig = style.new_figure(NAME)
    axes = geometry(fig, data)
    a, b = lay["x_range"]
    n_max = max(len(data["panels"][p]) for p in PANELS)
    for ax, p in zip(axes, PANELS):
        ids = data["panels"][p]
        style.reference_line(ax, x=data["default_saving_pct"])
        for i, rid in enumerate(ids):
            draw_row(ax, float(i), data["rows"][rid], bool(lay["end_labels"].get(rid)),
                     (lay.get("side") or {}).get(rid, "both"))
        ax.set_ylim(n_max - 0.5, -0.5)
        ax.set_yticks(range(len(ids)), [data["rows"][rid]["label"] for rid in ids])
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_bounds(len(ids) - 0.5, -0.5)       # the y spine separates the row labels from the plot
        ax.set_xlim(a, b)
        ax.xaxis.set_major_locator(FixedLocator(x_ticks(a, b)))
        ax.xaxis.set_major_formatter(style.PLAIN)
        thin_tick_labels(ax)
    style.end_label_inside(axes[-1])
    center_xlabel(axes, lab["x"])
    letters = style.panel_letters(axes)
    for ax, letter, p in zip(axes, letters, PANELS):       # C62: titles at the caption size, on the letters' baseline
        panel_title(ax, letter, lab["titles"][p], fontsize=style.LABEL_PT)
    # C62: the mathtext row labels on their rows' baseline ($\mu/\tilde{\beta}$ printed 0.8 pt off its end labels)
    align_baselines([tk.label1 for ax in axes for tk in ax.yaxis.get_major_ticks()])
    return fig


# ---------------------------------------------------------------------------------------------------------------
# tables
def _tex(s: Any) -> str:
    """Text for LaTeX: & % _ # escaped outside $...$ (the row labels and end texts are mathtext, which LaTeX reads)."""
    parts = str(s).split("$")
    for i in range(0, len(parts), 2):
        parts[i] = parts[i].replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")
    return "$".join(parts)


def _num(v, d: int) -> str:
    if v is None:
        return "--"
    s = f"{float(v):,.{d}f}"
    return s.replace("-", "$-$") if s.startswith("-") else s


def _iv(lo, hi, d: int) -> str:
    return "--" if lo is None or hi is None else f"[{_num(lo, d)}, {_num(hi, d)}]"


def points_tex(rows: Sequence[Mapping], d: Mapping) -> str:
    g = d["grid"]
    runs = runs_text(g["n_alignments"], g["n_policy_seeds"], times=r"$\times$")
    al = rows[0]["alignment"] if rows else "1"
    # two header lines without \multicolumn: with it, longtable's caption row ran 108 pt beyond the text width
    # C47 (print check of the gate): "All-fallback" in the head (as built "BL0a", a design name)
    hdr = (r"Assumption & Default & Setting & All-fallback (USD) & Overflow & Overflow & Total & Total & Bar \\" "\n"
           r" & (bar end) & & alignment " + f"{al}" + r" & median (\%) & 95\% interval & median (\%) & 95\% interval "
           r"& end \\" "\n")
    head = (r"{\footnotesize\setlength{\tabcolsep}{" + TABCOLSEP + r"}" "\n"
            r"\begin{longtable}{@{}lllrrrrrl@{}}" "\n"
            r"\caption{S1 per setting: the saving over all-fallback of " + _tex(style.POLICIES[KEY].label)
            + r" on E7's main week ("
            + horizon_text(g["horizon_min"]) + r"), medians over " + runs + r" with 95\% bootstrap intervals of the "
            r"median, in overflow and in total accounting (total: own capacity included), each over the setting's "
            r"own all-fallback cost, given at alignment " + f"{al}" + r". Default: the assumption's default setting "
            r"(the default point) and the end of the row's bar it is at, if any; Bar end: the end of its row's bar a "
            r"setting is at. Rows in the order of the tornado's panels (a)--(c), each sorted by span. The "
            r"$\mu/\tilde{\beta}$ rows are E7's runs; the rows L-rf and L-vr are the same policy under the stress "
            r"lenders.}\label{tab:s1-points}\\" "\n"
            r"\toprule" "\n" + hdr + r"\midrule\endfirsthead" "\n"
            r"\multicolumn{9}{@{}l}{Table~\thetable, continued}\\[2pt]" "\n"   # C50 (D5 review; D4's script items)
            r"\toprule" "\n" + hdr + r"\midrule\endhead" "\n"
            r"\bottomrule\endlastfoot" "\n")
    lines, last = [head], None
    for i, r in enumerate(rows):
        # C47 (U46 re-review): \\* inside an assumption's block, so that a page breaks only between blocks
        brk = "\\\\" if i + 1 == len(rows) or rows[i + 1]["row"] != r["row"] else "\\\\*"
        if r["row"] != last and last is not None:
            lines.append(r"\addlinespace[2pt]" "\n")
        first = r["row"] != last
        name = _tex(r["row_label"]) if first else ""
        dflt = ""
        if first and r.get("default_setting") is not None:
            dends = r.get("default_ends") or []
            dflt = _tex(r["default_setting"]) + (f" ({', '.join(dends)})" if dends else "")
        last = r["row"]
        ends = ", ".join(r["ends"]) if r["ends"] else ""
        s, t = r["saving"], r["saving_total"]
        lines.append(f"{name} & {dflt} & {_tex(r['value']) if r['value'] is not None else ''} & "
                     f"{_num(r['bl0a_usd'], 0)} & {_num(s['median'], 2)} & {_iv(s['lo'], s['hi'], 2)} & "
                     f"{_num(t['median'], 2)} & {_iv(t['lo'], t['hi'], 2)} & {ends} {brk}\n")
    lines.append(r"\end{longtable}}" "\n")
    return "".join(lines)


def _q28_notes(rows: Sequence[Mapping]) -> str:
    """The caption's notes on s1_q28.tex, from its rows: the policies whose three costs, refusals and victims are all
    equal (with 'the guard never aborts' where each such pair's guarded policy aborted in no run), whether L-vr left
    every policy at its default and which policies had buffer violations, and the refusals for lack of capacity where
    there were none (their column is then left out)."""
    notes = []
    groups: dict[tuple, list[Mapping]] = {}
    for r in rows:
        groups.setdefault((r["default"], r["rf"], r["vr"], r["refused_unavailable"], r["victims"]), []).append(r)
    same = [g for g in groups.values() if len(g) > 1 and None not in (g[0]["default"], g[0]["rf"], g[0]["vr"])]
    if same:
        guarded = [r for g in same for r in g if r.get("guarded")]
        never = guarded and all((r.get("abort_share") or {}).get(v) == 0.0 for r in guarded for v in ("rf", "vr"))
        notes.append("Equal rows: " + "; ".join(" = ".join(_tex(r["label"]) for r in g) for g in same)
                     + (" (the guard never aborts)" if never else "") + ".")
    if rows and all(r["vr"] is not None and r["vr"] == r["default"] for r in rows):
        hit = [r for r in rows if (r.get("violation_events_max") or 0.0) > 0.0]
        if hit:
            most = max(float(r["violation_events_max"]) for r in hit)
            notes.append(r"Under L-vr every policy's median cost equals its default: buffer violations occurred only in "
                         + _list([_tex(r["label"]) + "'s" for r in hit]) + f" runs (at most {most:g} per run).")
        else:
            notes.append(r"Under L-vr every policy's median cost equals its default: no buffer violation occurred.")
    if _no_capacity_refusals(rows):
        notes.append("No purchase was refused for lack of capacity.")
    return (" " + " ".join(notes)) if notes else ""


def _guards_text(rows: Sequence[Mapping], g: Mapping) -> str:
    """The caption's sentence on the allowance of the one-way guards among the rows (C47: part q28 ran the guard
    around A7, drawn as a7_ms4, at the allowance of sublet_ms4; both labels give it as a share of BL0a), from the
    sweep's B0_rule; '' where no guarded row or no share rule."""
    pct = b0_share_text(g.get("B0_rule"), tex=True)
    n = sum(1 for r in rows if r.get("guarded"))
    if not n or pct is None:
        return ""
    who = "Both one-way guards run" if n == 2 else "The one-way guards run" if n > 2 else "The one-way guard runs"
    return f" {who} at $B_0$ = {pct} of each run's all-fallback cost."


def _no_capacity_refusals(rows: Sequence[Mapping]) -> bool:
    return bool(rows) and all(r.get("refused_capacity_max") is not None and float(r["refused_capacity_max"]) == 0.0
                              for r in rows)


def q28_tex(t: Mapping, d: Mapping) -> str:
    """s1_q28.tex: a `table` within the column of the two-column supplement; the refusals and victims are medians of
    the runs, with one decimal (a median of an even number of runs can end in .5); the column of refusals for lack of
    capacity is left out where every run of every policy had none (the caption says so)."""
    g = d["grid"]
    h = horizon_text(g.get("q28_horizon_min") or g["horizon_min"])
    runs = runs_text(g["n_alignments"], g["n_policy_seeds"], times=r"$\times$")
    rows = t["rows"]
    cap = not _no_capacity_refusals(rows)
    refused = (r"\multicolumn{2}{c}{Refused (L-rf)}" if cap else r"Refused")
    lines = [r"\begin{table}[t]",
             r"\caption{The stress lenders on E7's main week (" + h + r" per run, medians over " + runs + r"): "
             r"the cost over all-fallback in overflow accounting under the default lender, under L-rf (purchases on "
             r"unavailable layers refused) and under L-vr (buffer violations as reclaims without notice), the "
             r"purchases refused per run under L-rf (" + (r"on unavailable layers; for lack of capacity" if cap else
                                                          r"on unavailable layers") + r") and the leases "
             r"ended by a violation per run under L-vr." + _q28_notes(rows) + _guards_text(rows, g) + "}",
             r"\label{tab:s1-q28}", r"\centering\footnotesize", r"\setlength{\tabcolsep}{" + Q28_TABCOLSEP + "}",
             r"\begin{tabular}{@{}l" + "r" * (6 if cap else 5) + r"@{}}", r"\toprule",
             r" & \multicolumn{3}{c}{Cost / all-fallback} & " + refused + r" & Victims \\",
             r"\cmidrule(lr){2-4}" + (r"\cmidrule(lr){5-6}" if cap else ""),
             (r"Policy & Default & L-rf & L-vr & Unavail. & Capacity & (L-vr) \\" if cap else
              r"Policy & Default & L-rf & L-vr & (L-rf) & (L-vr) \\"), r"\midrule"]
    for r in rows:
        # C47: a label split into lines (ms4_lib.label_lines, before " + " and its parenthesis), the lines after the
        # first on rows of their own, so that the table stays within the 252-pt column
        name, *more = [_tex(t) for t in label_lines(r["label"], plus=True)]
        more = [r"\quad " + m for m in more]          # indented: the continuation of the policy's name
        lines.append(f"{name} & {_num(r['default'], 3)} & {_num(r['rf'], 3)} & {_num(r['vr'], 3)} & "
                     f"{_num(r['refused_unavailable'], 1)} & "
                     + (f"{_num(r['refused_capacity'], 1)} & " if cap else "")
                     + f"{_num(r['victims'], 1)} \\\\")
        lines += [m + " &" * (6 if cap else 5) + r" \\" for m in more]
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def write_tables(data: Mapping, report: Mapping) -> None:
    t = data["tables"]
    head = "% Written by code/sim/figs/supp/sf_s1.py from {}; do not edit.\n"
    paths = [write_table(TABLES[0], head.format(f"{SWEEP}, {Q28} and {E7}") + points_tex(t["points"], data)),
             write_table(TABLES[1], head.format(Q28) + q28_tex(t["q28"], data))]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)} ({len(t['points'])} settings, "
          f"{len(t['q28']['rows'])} policies)")


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
