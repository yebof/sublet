"""sf_e7_mix: E7's contract mix, and the three supplementary E7 tables (design/sim_spec_ms4.md §8.2, §9; M2, M24,
M25; plan §4, part S-F).

(a) Per policy (rows in Table III's order, table3.json `order`, as Fig. 4(a) and table3_intervals.tex; named on the y
    ticks), the GPU-hour share per contract class of the leases it held: GPU-hours summed over the main-grid runs at mu
    / beta~ = 1 (the alignments x policy seeds of meta.grids) and normalized (e7/main/summary.json
    runs.1.<tag>.gpu_hour_share, §3.10), as a horizontal stacked bar in a grey ramp (contract classes, non-policy
    categories; plan §5) outlined in the policy's color (BL4's yellow in its black edge color); a class that no bar
    holds has no segment and is left out of the key.
(b) The same in the stress block under the i.i.d. lender at p = 0.2 (e7/stress/summary.json
    modes.L-iid-0.2.<tag>.gpu_hour_share; the stress block's alignment and policy seeds); its title sets p in
    italic, as the stress table's MODE_TEX.
The panel titles sit on the baseline of their bold letters (common.panel_title). A title with a $...$ part (labels
.titles, the caption source's TeX) is drawn as separate texts on that baseline (title_on_baseline): the letters of the
math part in italic (the face mathtext sets them in), the rest upright, each text at the pen advance of the ones before
it as the PDF backend sets them. As built, the title was one mathtext text, which the PDF backend sets about 0.5 pt
above the baseline (mathtext's vector output rounds the box height up to a whole point), so that (b)'s title sat
above its letter and above (a)'s title.
A segment narrower than SMALL_PT is printed as text with its share in percent inside the bar (sf_e6b.small_shares),
and is edged in its own color, not in the white SEG_EDGE_PT edge of the other segments, so that it prints in its class
color (as built, the white edges and the bar's outline covered A6's 0.23% protected in (b), 0.4 pt wide, and it
printed as a white stripe). The bars are BAR_H = 0.75 of the row pitch (sf_e6b.BAR_H, 0.62, as built), and the in-bar
text is centered on the row by its capitals and digits (va "center_baseline"; "center" centers the line box, which
includes the descender, and set the glyphs 1 pt high): 1.2-1.4 pt of fill above and below the 9-pt text (as built,
0.5 pt above; about 2.7 pt around the 7-pt text since C62). Below the last row the y range runs (1 - BAR_H) / 2 row
pitch further than half a row (rows_ylim), so that the last bar is as far from the x spine as the bars are from each
other (as built, 1.0 pt against 2.6 pt: it seemed to sit on the axis). (b) reserves PANEL_GAP_IN left of its axes,
wider than style.LEFT_SHARED (0.14 in at 9 pt, 0.11 in since C62), so that (a)'s end label "1" and (b)'s first label
"0" (12.6 pt apart at 9 pt, 13.2 pt at 7 pt; 7.6 pt as built) do not read as "1 0".
C62 (2026-11-24): the panel titles at the caption size (title_on_baseline), and the row names with mathtext on
the rows' pitch as printed (common.align_baselines; the PDF set them up to 1 pt off it).
A policy without leased GPU-hours (gpu_hour_share null) has an empty row with its note.

The after hook writes three tables through figs.common.write_table (SUBLET_FIGS_TABLES_DIR, else SUBLET_FIGS_PDF_DIR
when set, else paper/supplement/tables/), from the extract's `tables`, so --from-extract rewrites them; every count,
scope and slot length in their captions is read from the inputs into `tables` (never typed), and the rows follow
Table III's order:
  table3_intervals.tex     every Table III cell with its 95% percentile-bootstrap interval and n (e7/table3.json,
                           M25; W0's interval is the range of r0 over the attaining mode's seeds)
  e7_total_accounting.tex  per policy the week USD and the saving over BL0a in total accounting (own capacity
                           included), medians with 95% intervals (e7/main/summary.json runs.1.<tag>.total_usd,
                           saving_pct_total; BL0a and BL0b analytic, meta.bl0a_total_usd, bl0b_total_usd), with the
                           own-capacity USD per alignment (meta.own_capacity_usd; M2)
  e7_stress_aborts.tex     per A8 row (Sublet, A7 + guard) and stress mode: the share of runs with an abort, the
                           median abort slot and the runs and held certificates per case of Theorem W
                           (e7/stress/summary.json modes.<mode>.<tag>; M24), named by its paper label
                           (Theorem~\\ref{thm:fullmodel}, design/ms6_spec.md §5; the supplement resolves the main
                           text's labels) with the case heads (a), (b), (c)

MS6 C47 (design/ms6_spec.md M2, M3, M4; §2 U43b): the summaries' recorded keys are drawn as the configuration keys
(ms4_lib.DRAWN_KEY: Sublet as sublet_ms4, BL5 as bl5_lag, A7 + guard as a7_ms4, the guard around A7 at MS4's
allowance, C46), and every row label, of the bars and
of the three tables, is the registry label of the key drawn for its recorded style key (Table III's included:
table3_rows, not e7/table3.json's recorded "Sublet", which the rows keep as `recorded_label`; e7/table3.json and
figs/table3_e7.py are unchanged). The top row's label, sublet_ms4's 3.1 in at 9 pt (as built; with C59's label in
words 3.08 in at C62's 7 pt), is split before its parenthesis, its stem set one line above the row (row_names), so that
the bars keep their width; a7_ms4's label (2.6 in as built; 2.68 in at 7 pt) stays on one line and sets the rows'
reserve. The contract classes' key then sits over (b), so that the stem
stands alone on its line (print check of the gate: over (a) the stem read as the key's first entry). The tables split
the long labels before their parenthesis (table3_intervals.tex and e7_stress_aborts.tex, whose blocks are ruled
apart, also before " + "), the parts after the first on the rows below, indented.
The note and the captions state the guards' allowance from the summary's B0_rule (guards_text). The captions name
MS4's E7 table as the main-week table, not as "Table III", which is the paper's Table III v2 (figs/table3_v2.py).

Run from code/sim: python -m figs.supp.sf_e7_mix [--from-extract [JSON]].

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): table3_intervals.tex's head on its later pages
opens with "Table <n>, continued".
"""
from __future__ import annotations

import re
import statistics
import sys
from typing import Any, Mapping, Sequence

import matplotlib as mpl
from matplotlib import font_manager
from matplotlib.transforms import offset_copy
from matplotlib._text_helpers import layout
from matplotlib.ft2font import Kerning, LoadFlags
from matplotlib.patches import Patch

from figs import style
from figs.common import (LINE_STEP_PT, align_baselines, cli, legend_rows, maybe, need, panel_title, text_width_in,
                         write_table)
from figs.fig7_e2_e6 import text_on
from figs.inputs import Inputs
from figs.supp.ms4_lib import DRAWN_KEY, agg_point, b0_share_text, grid_counts, label_lines, runs_text, tag_of
from figs.table3_e7 import HORIZON_WORDS
from figs.supp.sf_e6b import (BAR_EDGE_PT, CLASS_LABEL, CLASS_ORDER, SMALL_GAP_PT, SMALL_PT, _ordered, percent,
                              small_shares)

NAME = "sf_e7_mix"
MAIN = "code/sim/out/e7/main/summary.json"
STRESS = "code/sim/out/e7/stress/summary.json"
TABLE3 = "code/sim/out/e7/table3.json"
KEYS = style.SUPP_POLICIES_MS4[NAME]          # sublet_ms4, a7_ms4, a7, a6, bl5_lag, bl1, bl2, bl4
MU = 1
STRESS_MODE = "L-iid-0.2"
A8_KEYS = ("sublet_ms4", "a7_ms4")            # C47: the A8 rows of the stress table, as the registry keys drawn
CASES = ("W(a)", "W(b)", "W(c)", "unavailable")
# Table III columns of table3_intervals.tex: (table3.json key, label in LaTeX)
T3_COLUMNS = (("usd.overflow", "USD per week, overflow accounting"), ("usd.total", "USD per week, total accounting"),
              ("saving_pct", r"Saving over all-fallback (\%), overflow accounting"),
              ("gap", "Cost / merged LP bound (slow grid, reduced menu)"),     # C47: no experiment ID (U46)
              ("fallback_share_after_reclaims", "Fallback share after reclaims"),
              ("W0", r"$W_0$ (worst cost / all-fallback, stress modes)"),
              ("abort_share", "Share of runs with an abort"))
TITLE_GAP_PT = 3.0             # a panel title this far right of its letter (as common.panel_title)
KEY_TOP_PT = 3.0               # the class key this far below the axes top, clear of the panel titles (not in §8.2)
BAR_H = 0.75                   # bar height over the row pitch (sf_e6b.BAR_H is 0.62; not in §8.2)
SEG_EDGE_PT = 0.4              # the white edge between a bar's segments (not in §8.2)
PANEL_GAP_IN = 0.21            # (b)'s reserve left of its axes (style.LEFT_SHARED is 0.14 in; not in §8.2)
KEY_TIGHT = (0.8, 0.4, 0.5)    # C47: the class key over (b): swatch length, swatch-text gap, column gap (em)
TABLES = ("table3_intervals.tex", "e7_total_accounting.tex", "e7_stress_aborts.tex")
style.register_supplementary(NAME, "W2", 2.2)
LABELS = {"a_x": "GPU-hour share", "b_x": "GPU-hour share", "classes": CLASS_LABEL, "small": "{} {}%",
          "small_summary": "{} classes {}%",
          "no_data": "no leases", "titles": {"a": "Trace lender (main grid)",
                                             "b": r"i.i.d. lender, $p = 0.2$"},
          "note": "GPU-hours per contract class summed over the runs and normalized: (a) the main grid at mu/beta~ = "
                  "1 ({main_runs}), (b) the stress block under the i.i.d. lender at p = {stress_p} (alignment "
                  "{stress_alignment}, {stress_seeds}){guards}",
          # C47 (design/ms6_spec.md M2, M3, M4): the allowance of the one-way guards, from the summary's B0_rule (E7
          # ran A8 around A7, drawn as a7_ms4, at the allowance of sublet_ms4; both labels give it as a share of BL0a)
          "guards": "; {names} run at B0 = {pct} of each run's all-fallback cost"}    # C47: no milestone name (U46)


def guards_text(keys: Sequence[str], rule: Any, *, tex: bool = False) -> str:
    """The sentence (tex: for a table caption) or clause (labels.note) on the one-way guards among `keys` (A8_KEYS)
    and their allowance from the summary's meta.B0_rule (ms4_lib.b0_share_text); '' where none is drawn or the rule is
    not a share of BL0a. C47: E7's two A8 policies ran at MS4's allowance, which their labels give as "B0 = 10%
    BL0a" and this sentence in words."""
    guards = [k for k in A8_KEYS if k in keys]
    pct = b0_share_text(rule, tex=tex)
    if not guards or pct is None:
        return ""
    names = [_tex_label(style.POLICIES[k].label) if tex else style.POLICIES[k].label for k in guards]
    if tex:
        who = "Both one-way guards run" if len(guards) == 2 else f"{names[0]} runs"
        return f" {who} at $B_0$ = {pct} of each run's all-fallback cost."
    return LABELS["guards"].format(names=" and ".join(names), pct=pct)


def shares_of(ent: Any) -> tuple[dict, str | None]:
    sh = ent.get("gpu_hour_share") if isinstance(ent, Mapping) else None
    if not isinstance(sh, Mapping):
        return {}, (ent.get("gpu_hour_share_note") if isinstance(ent, Mapping) else None) or "missing"
    return {k: float(v) for k, v in sh.items() if not k.endswith("_note") and v is not None}, None


# ---------------------------------------------------------------------------------------------------------------
# tables
def t3_cell(row: Mapping, col: str) -> dict:
    c = row
    for part in col.split("."):
        c = c.get(part) if isinstance(c, Mapping) else None
    c = c if isinstance(c, Mapping) else {}
    lo, hi = (c.get("interval") or [None, None])[:2]
    return {"median": c.get("median"), "lo": lo, "hi": hi, "n": c.get("n"), "note": c.get("note")}


def drawn_key(style_key: str | None) -> str | None:
    """The registry key drawn for a recorded style key (C47: ms4_lib.DRAWN_KEY; the others are their own)."""
    return DRAWN_KEY.get(style_key, style_key)


def table3_rows(t3: Mapping) -> dict:
    """Table III's rows with their cells; C47 (design/ms6_spec.md U43b): each row's label is the registry label of
    the key drawn for its recorded style key (drawn_key; e.g. Sublet-MS4 as sublet_ms4's), not the label that
    e7/table3.json recorded at MS4 ("Sublet"), which `recorded_label` keeps."""
    order = list(need(t3, "order", what=TABLE3))
    rows = []
    for tag in order:
        row = need(t3, "rows", tag, what=TABLE3)
        key = drawn_key(need(row, "style_key", what=f"{TABLE3} rows.{tag}"))
        rows.append({"tag": tag, "key": key, "label": style.policy(key).label,
                     "recorded_label": row.get("label") or t3["labels"][tag], "style_key": row.get("style_key"),
                     "cells": {col: t3_cell(row, col) for col, _ in T3_COLUMNS}})
    scope = need(t3, "caption", "scope", what=TABLE3)
    return {"order": order, "columns": [{"key": k, "label": lab} for k, lab in T3_COLUMNS], "rows": rows,
            "scope": {k: need(scope, k, what=f"{TABLE3} caption.scope") for k in (
                "horizon_min", "menu", "lender", "mu_over_beta_tilde")},
            "reduced": bool((t3.get("meta") or {}).get("reduced")), "git_revision": (t3.get("meta") or {}).get(
                "git_revision")}


def total_accounting(main: Mapping, tags: Mapping, keys: Sequence[str]) -> dict:
    meta = need(main, "meta", what=MAIN)
    own = {k: float(v) for k, v in need(meta, "own_capacity_usd", what=MAIN).items() if not k.endswith("_note")}
    bl0a = {k: float(v) for k, v in need(meta, "bl0a_total_usd", what=MAIN).items() if not k.endswith("_note")}
    bl0b = {k: float(v) for k, v in need(meta, "bl0b_total_usd", what=MAIN).items() if not k.endswith("_note")}
    rows = []
    for key in keys:
        ent, note = maybe(main, "runs", MU, tags[key])
        usd = agg_point(ent, "total_usd") if note is None else {"median": None, "ci_lo": None, "ci_hi": None,
                                                                "n": 0, "note": note}
        sav = agg_point(ent, "saving_pct_total") if note is None else dict(usd)
        rows.append({"key": key, "label": style.POLICIES[key].label, "usd": usd, "saving_pct": sav})
    cs = sorted(set(bl0a) & set(bl0b), key=float)
    for key, vals in (("bl0b", bl0b), ("bl0a", bl0a)):
        usd = statistics.median(vals[c] for c in cs) if cs else None
        sav = statistics.median(100.0 * (1.0 - vals[c] / bl0a[c]) for c in cs) if cs else None
        rows.append({"key": key, "label": style.POLICIES[key].label,
                     "usd": {"median": usd, "ci_lo": None, "ci_hi": None, "n": len(cs),
                             "note": "analytic, median over the alignments"},
                     "saving_pct": {"median": sav, "ci_lo": None, "ci_hi": None, "n": len(cs),
                                    "note": "analytic, median over the alignments"}})
    n_al, n_se = grid_counts(need(meta, "grids", what=MAIN), f"{MAIN} meta.grids")
    return {"rows": rows, "own_capacity_usd": {c: own[c] for c in sorted(own, key=float)},
            "own_capacity_median": statistics.median(own.values()) if own else None,
            "grid": {"n_alignments": n_al, "n_policy_seeds": n_se}}


def stress_aborts(stress: Mapping, main: Mapping, tags: Mapping) -> dict:
    modes = [m for m in need(stress, "modes", what=STRESS) if not m.endswith("_note")]
    rows = []
    for key in A8_KEYS:
        for mode in modes:
            ent, note = maybe(stress, "modes", mode, tags[key])
            ent = ent if isinstance(ent, Mapping) else {}
            cert = ent.get("certificates") if isinstance(ent.get("certificates"), Mapping) else {}
            by_case = cert.get("by_case") or {}
            rows.append({"key": key, "label": style.POLICIES[key].label, "mode": mode, "n_runs": ent.get("n_runs"),
                         "abort_share": ent.get("abort_share"), "t_a_median": ent.get("t_a_median"),
                         "cases": {c: {"runs": (by_case.get(c) or {}).get("runs"),
                                       "held": (by_case.get(c) or {}).get("held")} for c in CASES},
                         "failures": cert.get("failures"),
                         "note": note or ent.get("abort_share_note") or ent.get("t_a_median_note")})
    smeta = need(stress, "meta", what=STRESS)
    al = need(smeta, "alignment", what=f"{STRESS} meta")
    mu = float(smeta.get("mu", MU))
    inst = need(main, "meta", "instances", f"mu={mu:g}:c={al}", what=MAIN)        # the stress block's instance
    _, n_se = grid_counts({"alignments": [al], **need(smeta, "grids", what=f"{STRESS} meta")}, f"{STRESS} meta.grids")
    return {"modes": modes, "rows": rows, "grid": {"alignment": al, "n_policy_seeds": n_se,
                                                   "slow_min": need(inst, "slow_min", what=f"{MAIN} meta.instances")}}


# ---------------------------------------------------------------------------------------------------------------
def build(inp: Inputs) -> dict:
    main, stress, t3 = inp.json(MAIN), inp.json(STRESS), inp.json(TABLE3)
    tags = tag_of(need(main, "meta", "tags", what=MAIN), KEYS, MAIN, drawn=DRAWN_KEY)       # C47: recorded keys
    a, b, notes = {}, {}, {}
    for key in KEYS:
        a[key], na = shares_of(maybe(main, "runs", MU, tags[key])[0])
        b[key], nb = shares_of(maybe(stress, "modes", STRESS_MODE, tags[key])[0])
        notes[key] = {"a": na, "b": nb}
    # Table III's order (as Fig. 4(a) and table3_intervals.tex), the keys without a Table III row after them
    t3_keys = [drawn_key(need(t3, "rows", tag, "style_key", what=TABLE3)) for tag in need(t3, "order", what=TABLE3)]
    keys = [k for k in t3_keys if k in KEYS] + [k for k in KEYS if k not in t3_keys]
    tables = {"table3_intervals": table3_rows(t3),
              "total_accounting": total_accounting(main, tags, keys),          # then BL0b, BL0a, as Table III
              "stress_aborts": stress_aborts(stress, main, tags)}
    sg = tables["stress_aborts"]["grid"]
    ta = tables["total_accounting"]["grid"]
    ns = sg["n_policy_seeds"]
    rule = main["meta"].get("B0_rule")
    for t in tables.values():
        t["b0_rule"] = rule                          # C47: the guards' allowance, for the captions (guards_text)
    note = LABELS["note"].format(main_runs=runs_text(ta["n_alignments"], ta["n_policy_seeds"]),
                                 stress_alignment=sg["alignment"], stress_p=STRESS_MODE.rsplit("-", 1)[1],
                                 stress_seeds=f"{ns} policy seed{'s' if ns != 1 else ''}",
                                 guards=guards_text(keys, rule))
    return {"keys": keys, "tags": tags, "a": a, "b": b, "notes": notes, "stress_mode": STRESS_MODE,
            "tables": tables, "labels": {**LABELS, "note": note},
            "meta": {"git_revision": {"main": need(main, "meta", "git_revision", what=MAIN),
                                      "stress": need(stress, "meta", "git_revision", what=STRESS),
                                      "table3": (t3.get("meta") or {}).get("git_revision")},
                     "reduced": bool(main["meta"].get("reduced") or stress["meta"].get("reduced")),
                     "B0_rule": rule},
            "sources": list(inp.sources)}


def draw_bars(ax, keys: Sequence[str], shares: Mapping, classes: Sequence[str], colors: Mapping, lab: Mapping) -> dict:
    """Row i's stacked bar of `keys[i]`, segments in the class colors with a white SEG_EDGE_PT edge, except those
    narrower than SMALL_PT, edged in their own color (the white edges and the outline would cover their fill), and
    the policy's outline; returns {row: [(class label, left, width, color)]} for small_text. Call after the axes are
    placed (the widths in points)."""
    segs = {}
    pt = style.axes_rect_in(ax)[2] * style.BP_PER_IN / (ax.get_xlim()[1] - ax.get_xlim()[0])     # points per unit
    for i, key in enumerate(keys):
        sh = shares.get(key) or {}
        tot = sum(sh.get(k, 0.0) for k in classes)
        if tot <= 0:
            ax.text(0.01, i, lab.get("no_data", "no leases"), transform=ax.get_yaxis_transform(), ha="left",
                    va="center", fontsize=style.TICK_PT, color=style.THEORY_LABEL_GREY)
            continue
        x0, segs[i] = 0.0, []
        for k in classes:
            v = float(sh.get(k, 0.0)) / tot
            if v <= 0:
                continue
            edge = colors[k] if v * pt < SMALL_PT else "white"
            ax.barh(i, v, left=x0, height=BAR_H, color=colors[k], linewidth=SEG_EDGE_PT, edgecolor=edge, zorder=1.5)
            segs[i].append((lab["classes"].get(k, k), x0, v, colors[k]))
            x0 += v
        p = style.policy(key)
        ax.barh(i, 1.0, height=BAR_H, fill=False, edgecolor=p.text_color, linewidth=BAR_EDGE_PT, zorder=1.6)
    return segs


def rows_ylim(axes, n_rows: int, h_key: float) -> None:
    """One categorical y range for both panels (as sf_e6b.rows_below): the rows, an empty band of h_key inches above
    them for the key, and below the last row (1 - BAR_H) / 2 row pitch more than half a row, so that the last bar
    is as far from the x spine as the bars are from each other."""
    h_ax = style.axes_rect_in(axes[0])[3]
    pad = (1.0 - BAR_H) / 2.0
    extra = (n_rows + pad) * h_key / (h_ax - h_key)        # the key's band of h_key inches above row -0.5
    for ax in axes:
        ax.set_ylim(n_rows - 0.5 + pad, -0.5 - extra)


def title_runs(text: str) -> list[tuple[str, str]] | None:
    """(text, font style) runs of a title: outside $...$ upright; inside, letters italic (as mathtext sets a
    variable), everything else upright, spaces kept; adjacent runs of one style merged. None where a math part holds
    more than letters, digits, spaces and plain operators (a command, script or group: mathtext draws it)."""
    runs: list[tuple[str, str]] = []
    for j, part in enumerate(text.split("$")):
        math = j % 2 == 1
        if math and re.search(r"[\\^_{}]", part):
            return None
        for run in (re.findall(r"[A-Za-z]+|[^A-Za-z]+", part) if math else [part]):
            sty = "italic" if math and run[0].isalpha() else "normal"
            if runs and runs[-1][1] == sty:
                runs[-1] = (runs[-1][0] + run, sty)
            elif run:
                runs.append((run, sty))
    return runs


def advance_pt(text: str, prop) -> float:
    """The pen advance (points) of `text` in the font of `prop` as the PDF backend sets it (glyph advances and
    kerning, matplotlib._text_helpers.layout)."""
    font = font_manager.get_font(font_manager.fontManager._find_fonts_by_props(prop))
    font.clear()
    font.set_size(prop.get_size_in_points(), 72)
    last = None
    for last in layout(text, font, kern_mode=Kerning.UNFITTED):
        pass
    if last is None:
        return 0.0
    return last.x + last.ft_object.load_glyph(last.glyph_idx, flags=LoadFlags.NO_HINTING).linearHoriAdvance / 65536


def title_on_baseline(ax, letter, text: str, *, fontsize: float = style.LABEL_PT) -> None:
    """common.panel_title, except that a title with a $...$ part is set as separate texts on the letter's baseline
    (title_runs; each at the pen advance of the ones before it): one mathtext text sits up to 1 pt above the
    baseline in the PDF (the vector output rounds the box height up to a whole point). C62: at the caption size
    (style.LABEL_PT, 7.97 bp), as C62 sets panel titles (as built at TICK_PT, the 9-pt scale's single size)."""
    runs = title_runs(text) if "$" in text else None
    if runs is None:
        panel_title(ax, letter, text, fontsize=fontsize)
        return
    fig = ax.figure
    bb = letter.get_window_extent(fig.canvas.get_renderer())
    w_in = fig.get_size_inches()[0]
    x_in = bb.x1 / fig.dpi + TITLE_GAP_PT / 72.0
    for run, sty in runs:
        t = fig.text(x_in / w_in, letter.get_position()[1], run, ha="left", va="baseline", fontsize=fontsize,
                     fontstyle=sty)
        x_in += advance_pt(run, t.get_fontproperties()) / 72.0


def class_key(ax, pairs) -> float:
    """The contract classes' key from the top left of `ax` ((a), or (b) where the top row's stem takes (a)'s band;
    C47) (figure legends anchored at `ax`, common.legend_rows, drawn above both axes; as built, an axes legend of five
    classes was cut by (b)'s background); returns its height in inches with a 0.03-in gap, the band that rows_ylim
    leaves above the bars. Over (b) it is set tighter (KEY_TIGHT: shorter swatches and gaps), so that the three classes
    of E7's data fit (b)'s width in one row; more classes than fit there go on further rows (key_rows)."""
    tight = ax is not ax.figure.axes[0]
    hl, pad, cs = KEY_TIGHT if tight else (1.2, mpl.rcParams["legend.handletextpad"], 0.9)
    with mpl.rc_context({"legend.handlelength": hl, "legend.handleheight": 0.8, "legend.handletextpad": pad}):
        rows = key_rows(ax, list(pairs), cs) if tight else [list(pairs)]
        legs = legend_rows(ax, rows, columnspacing=cs, top_pt=KEY_TOP_PT)
    r = ax.figure.canvas.get_renderer()
    return (legs[0].get_window_extent(r).y1 - legs[-1].get_window_extent(r).y0) / ax.figure.dpi + 0.03


def key_rows(ax, pairs: list, columnspacing: float) -> list:
    """`pairs` split into consecutive rows, each as long as fits between the left edge of `ax` and the figure's right
    margin (measured as one frameless legend row in the current rc settings); one entry per row at least."""
    from matplotlib.legend import Legend
    fig = ax.figure
    r = fig.canvas.get_renderer()
    room = (fig.get_size_inches()[0] - style.MARGIN_RIGHT) - style.axes_rect_in(ax)[0]

    def width(group) -> float:
        h, t = zip(*group)
        leg = Legend(fig, list(h), list(t), ncol=len(group), frameon=False, borderpad=0.0,
                     columnspacing=columnspacing)
        return leg.get_window_extent(r).width / fig.dpi

    rows: list = []
    for p in pairs:
        if rows and width(rows[-1] + [p]) <= room + 1e-6:
            rows[-1].append(p)
        else:
            rows.append([p])
    return rows


def small_text(ax, i: int, segs: Sequence[tuple], label: str, summary: str) -> None:
    """Row i's segments narrower than SMALL_PT as text with their share in percent (sf_e6b.small_shares: left of the
    first of them, inside the bar); where that leaves no room (the slivers at the bar's left end), right-aligned
    SMALL_GAP_PT inside the right end of the widest segment, in black or white for contrast (text_on), the list or,
    where it is too long, `summary` (their count and summed share; the names are in the extract's shares); StyleError
    where neither fits. The text is centered on the row by its capitals and digits (va "center_baseline")."""
    n0 = len(ax.texts)
    try:
        small_shares(ax, i, segs, label)
        for t in ax.texts[n0:]:
            t.set_verticalalignment("center_baseline")
        return
    except style.StyleError:
        pass
    to_pt = 72.0 / ax.figure.dpi
    pt = (ax.transData.transform((1.0, i))[0] - ax.transData.transform((0.0, i))[0]) * to_pt
    small = [(n, w) for n, _, w, _ in segs if 0 < w * pt < SMALL_PT]
    total = sum(w for _, _, w, _ in segs)
    name, x0, w, c = max(segs, key=lambda sg: sg[2])
    for text in (", ".join(label.format(n, percent(v / total)) for n, v in small),
                 summary.format(len(small), percent(sum(v for _, v in small) / total))):
        if text_width_in(ax.figure, text) * 72.0 + 2 * SMALL_GAP_PT <= w * pt:
            ax.text(x0 + w - SMALL_GAP_PT / pt, i, text, ha="right", va="center_baseline", fontsize=style.TICK_PT,
                    color=text_on([c]), zorder=1.8)
            return
    raise style.StyleError(f"{NAME}: no room in row {i} for the shares of {[n for n, _ in small]}")


def row_names(fig, names: Sequence[str]) -> tuple[list[str], str | None]:
    """(the y tick labels, the stem drawn one line above the top row, or None): the top row's label is split
    (label_lines) where it is the widest and its two lines are narrower, its stem then set above the row in the band
    of the class key, which no other row label reaches (C47: sublet_ms4's label in one line, 3.1 in at 9 pt, took
    the bars' width); every other label stays in one line."""
    names = list(names)
    if not names:
        return names, None
    lines = label_lines(names[0])
    widths = [text_width_in(fig, n) for n in names]
    if len(lines) == 2 and widths[0] == max(widths) and max(text_width_in(fig, t) for t in lines) < widths[0]:
        return [lines[1]] + names[1:], lines[0]
    return names, None


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    keys = list(data["keys"])
    fig = style.new_figure(NAME)
    names, stem = row_names(fig, [style.POLICIES[k].label for k in keys])
    left = style.ytick_reserve(fig, names + ([stem] if stem else []))
    ax_a, ax_b = style.panel_row(fig, (1, 1), left=(left, PANEL_GAP_IN))
    classes = _ordered({c for p in ("a", "b") for k in keys for c, v in (data[p].get(k) or {}).items() if v > 0},
                       CLASS_ORDER)
    colors = dict(zip(classes, style.ramp(len(classes), "greys")[::-1])) if classes else {}
    for ax in (ax_a, ax_b):
        ax.set_xlim(0.0, 1.0)
    segs = {p: draw_bars(ax, keys, data[p], classes, colors, lab) for ax, p in ((ax_a, "a"), (ax_b, "b"))}
    for ax, p in ((ax_a, "a"), (ax_b, "b")):
        ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
        ax.xaxis.set_major_formatter(style.PLAIN)
        ax.set_xlabel(lab[f"{p}_x"])
        style.end_label_inside(ax)
    ax_a.set_yticks(range(len(keys)), names)
    ax_b.set_yticks(range(len(keys)), [""] * len(keys))
    pairs = [(Patch(facecolor=colors[c], edgecolor="none"), lab["classes"].get(c, c)) for c in classes]
    # C47: with a stem over (a)'s top row the key goes over (b), so that the stem stands alone on its line
    h_key = class_key(ax_b if stem else ax_a, pairs) if pairs else 0.0
    rows_ylim((ax_a, ax_b), len(keys), h_key)
    small = lab.get("small", "{} {}%")
    for ax, p in ((ax_a, "a"), (ax_b, "b")):
        for i, sg in segs[p].items():
            small_text(ax, i, sg, small, lab.get("small_summary", "{} classes {}%"))
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
    if stem:                       # C47: the top row's stem one line above its tick label, right-aligned with it
        tl = ax_a.get_yticklabels()[0]
        t = ax_a.text(0.0, 0.0, stem, transform=offset_copy(tl.get_transform(), fig=fig, y=LINE_STEP_PT,
                                                            units="points"),
                      ha="right", va=tl.get_verticalalignment(), fontsize=style.TICK_PT)
        t._sublet_role = "row_label:stem"
    # C62: the row names with mathtext ("($B_0=10\%$ ...)") on the rows' pitch as printed (common.align_baselines: the
    # PDF backend set them up to 1 pt off it, and the top row's second line 0.5 pt nearer its stem); after the stem,
    # which keeps its line above the unshifted anchor
    align_baselines([tk.label1 for tk in ax_a.yaxis.get_major_ticks()])
    letters = style.panel_letters([ax_a, ax_b])
    for ax, letter, p in zip((ax_a, ax_b), letters, ("a", "b")):
        title_on_baseline(ax, letter, lab["titles"][p])
    return fig


# ---------------------------------------------------------------------------------------------------------------
def _num(v, fmt: str) -> str:
    if v is None:
        return "--"
    s = format(float(v), fmt)
    return s.replace("-", "$-$") if s.startswith("-") else s


FMT = {"usd.overflow": ",.0f", "usd.total": ",.0f", "saving_pct": ".1f", "gap": ".3f",
       "fallback_share_after_reclaims": ".3f", "W0": ".3f", "abort_share": ".2f"}


def _interval(lo, hi, fmt: str) -> str:
    return "--" if lo is None or hi is None else f"[{_num(lo, fmt)}, {_num(hi, fmt)}]"


def _tex_text(s: str) -> str:
    return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def _tex_label(s: str) -> str:
    """A registry label in LaTeX (C47): its $...$ parts kept as math (mathtext and LaTeX share them, as sublet_ms4's
    "$B_0=10\\%$"), the text between them escaped (_tex_text, which the MS5b scripts import unchanged)."""
    parts = re.split(r"(?<!\\)\$", str(s))
    if len(parts) % 2 == 0:
        raise style.StyleError(f"unbalanced $ in the label {s!r}")
    return "".join(f"${p}$" if i % 2 else _tex_text(p) for i, p in enumerate(parts))


def _tex_lines(label: str, *, plus: bool = False) -> list[str]:
    """A table row label's lines in LaTeX (C47): split before its parenthesis and, with `plus`, also before " + "
    (ms4_lib.label_lines; table3_intervals.tex, whose 10-pt longtable fills the text width: "Lagged RetroRenting +
    one-way guard" in one line made it 44 pt too wide), each line _tex_label'd; a table puts the lines after the
    first on the rows below (the next column rows, modes, or rows of their own)."""
    lines = [_tex_label(t) for t in label_lines(label, plus=plus)]
    return lines[:1] + [TEX_INDENT + t for t in lines[1:]]


TEX_INDENT = r"\quad "                         # C47: a label's continuation lines are indented (not a new policy)


def scope_text(scope: Mapping) -> str:
    """'one week, full menu, trace lender, $\\mu/\\tilde\\beta=1$' from table3.json caption.scope (as figs.table3_e7
    writes Table III's caption)."""
    h = float(scope["horizon_min"])
    horizon = HORIZON_WORDS.get(int(h), f"{h:g} min") if h.is_integer() else f"{h:g} min"
    menu = str(scope["menu"]).split(" (")[0]
    return (f"{horizon}, {_tex_text(menu)} menu, {_tex_text(scope['lender'])} lender, "
            f"$\\mu/\\tilde\\beta={float(scope['mu_over_beta_tilde']):g}$")


DEFINED = re.compile(r"(\S+) by definition")     # C47: a cell's note "<value> by definition" (BL0a's W0, n = 0)


def defined_text(c: Mapping) -> str | None:
    """C47 (print check of the gate): the Median entry of a cell whose value holds by definition and has no values
    (n = 0, its note "<value> by definition": BL0a's W0) as "<value> (by definition)", its interval then a dash and
    its n 0, as every cell without values (as relabeled, "1.000 [1.000, 1.000]" with n = 0); None for every other
    cell."""
    m = DEFINED.fullmatch(str(c.get("note") or ""))
    return f"{m.group(1)} (by definition)" if m and c.get("n") == 0 and c.get("median") is not None else None


def table3_intervals_tex(t: Mapping) -> str:
    """table3_intervals.tex: a longtable at footnotesize (C47, print check of the gate: as the other supplementary
    tables; as built at 10 pt), one block of rows per policy, its name on the block's first rows; every row of a
    block but its last ends in \\\\*, so that a page breaks only between blocks (C47: as relabeled, a name split over
    three rows could break across a page, and a block could continue on the next page without its name). C50
    (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): the head on the later pages opens with "Table
    <n>, continued"."""
    # C59 (RC18(4)): over n = 4 values (the alignments of the analytic rows and of all-fallback's ALG/LB) the
    # percentile-bootstrap interval is the range of the values, and the caption says so
    four = any((c or {}).get("n") == 4 for r in t["rows"] for c in r["cells"].values())
    head = (r"{\footnotesize" "\n" r"\begin{longtable}{llrrr}" "\n"
            r"\caption{E7 on its main week (" + scope_text(t["scope"]) + r"): each policy's value in each column "
            r"with its 95\% percentile-bootstrap interval of the median"
            + (r" (over $n=4$ values, the alignments, the range of the values)" if four else "")
            + r" and the number of values $n$; the interval "
            r"of $W_0$ is the range of $r_0$ over the seeds of its attaining stress mode. A dash marks a cell without "
            r"a value." + guards_text([r["key"] for r in t["rows"]], t.get("b0_rule"), tex=True)
            + r"}\label{tab:table3-intervals}\\" "\n"
            r"\toprule" "\n" r"Policy & Column & Median & Interval & $n$ \\" "\n" r"\midrule\endfirsthead" "\n"
            r"\multicolumn{5}{@{}l}{Table~\thetable, continued}\\[2pt]" "\n"                          # C50
            r"\toprule" "\n" r"Policy & Column & Median & Interval & $n$ \\" "\n" r"\midrule\endhead" "\n"
            r"\bottomrule\endlastfoot" "\n")
    lines = [head]
    cols = [(c["key"], c["label"]) for c in t["columns"]]
    for j, row in enumerate(t["rows"]):
        if j:
            lines.append(r"\midrule" "\n")
        name = _tex_lines(row["label"], plus=True)   # C47: a long label on the block's first rows
        for i, (col, clab) in enumerate(cols):
            c = row["cells"][col]
            fmt = FMT.get(col, ".3f")
            n = "--" if c["n"] is None else str(int(c["n"]))
            med, iv = _num(c["median"], fmt), _interval(c["lo"], c["hi"], fmt)
            if defined_text(c) is not None:                  # C47: a value by definition, without values
                med, iv = defined_text(c), "--"
            end = r"\\*" if i < len(cols) - 1 else r"\\"      # C47: no page break inside a policy's block
            lines.append(f"{name[i] if i < len(name) else ''} & {clab} & {med} & {iv} & {n} {end}\n")
    lines.append(r"\end{longtable}}" "\n")
    return "".join(lines)


def own_text(own: Mapping, median) -> str:
    """The own capacity's sentence: one alignment's USD, or the median with each alignment's USD after it."""
    if len(own) == 1:
        (c, v), = own.items()
        return f"Own capacity costs {_num(v, ',.0f')} USD per week (alignment {c})"
    by = "; ".join(f"{c}: {_num(v, ',.0f')}" for c, v in own.items())
    return (f"Own capacity costs {_num(median, ',.0f')} USD per week, the median over the alignments (by alignment: "
            f"{by})")


def total_accounting_tex(t: Mapping) -> str:
    g = t["grid"]
    runs = runs_text(g["n_alignments"], g["n_policy_seeds"], times=r"$\times$")
    lines = [r"\begin{table}[t]",
             r"\caption{E7 in total accounting: the week cost including the borrowers' own capacity and the saving "
             r"over all-fallback in the same accounting (medians over " + runs + r" with 95\% bootstrap intervals; "
             r"all-fallback and provision for peak analytic, medians over the alignments). "
             + own_text(t["own_capacity_usd"], t["own_capacity_median"]) + r"; it is the same for every policy."
             + guards_text([r["key"] for r in t["rows"]], t.get("b0_rule"), tex=True) + "}",
             r"\label{tab:e7-total-accounting}", r"\centering\footnotesize", r"\setlength{\tabcolsep}{3.4pt}",
             r"\begin{tabular}{@{}lrrrr@{}}", r"\toprule",
             r"Policy & USD per week & 95\% interval & Saving (\%) & 95\% interval \\", r"\midrule"]
    for r in t["rows"]:
        # C47: a long label's parenthesis on a row of its own below (not split before " + ": "PD heuristic" alone
        # would read as A7's row, the one above it)
        name = _tex_lines(r["label"])
        lines.append(f"{name[0]} & {_num(r['usd']['median'], ',.0f')} & "
                     f"{_interval(r['usd']['ci_lo'], r['usd']['ci_hi'], ',.0f')} & "
                     f"{_num(r['saving_pct']['median'], '.1f')} & "
                     f"{_interval(r['saving_pct']['ci_lo'], r['saving_pct']['ci_hi'], '.1f')} \\\\")
        lines += [f"{more} & & & & \\\\" for more in name[1:]]
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


MODE_TEX = {"L-eg": "eager", "L-ss": "safe-site", "L-iid-0.05": r"i.i.d.\ $p=0.05$", "L-iid-0.2": r"i.i.d.\ $p=0.2$",
            "L-co": "correlated"}


def stress_aborts_tex(t: Mapping) -> str:
    # C47 (U46, second review): Theorem \ref{thm:fullmodel} has the parts (a) and (b); the column (c) counts the runs
    # of its conjectured extension (S following PD after an abort), which the paper states after the theorem
    g = t["grid"]
    n = g["n_policy_seeds"]
    lines = [r"\begin{table}[t]",
             r"\caption{Aborts of the guarded policies in E7's stress block (alignment " + f"{g['alignment']}, {n} "
             r"policy seed" + ("s" if n != 1 else "") + r" per mode): the share of runs with an abort, the median "
             r"abort slot $t_a$ (" + f"{float(g['slow_min']):g}" + r"-min slots) and, per case, (a) and (b) of "
             r"Theorem~\ref{thm:fullmodel} and (c) its conjectured extension to $S$ following PD after an abort, "
             r"the runs and the runs whose certificate held." + guards_text([r["key"] for r in t["rows"]],
                                                                             t.get("b0_rule"), tex=True) + "}",
             r"\label{tab:e7-stress-aborts}", r"\centering\footnotesize", r"\setlength{\tabcolsep}{3.4pt}",
             r"\begin{tabular}{@{}llrrrrr@{}}", r"\toprule",
             r"Policy & Lender & Abort share & Median $t_a$ & (a) & (b) & (c) \\", r"\midrule"]
    prev, more = None, []
    for r in t["rows"]:
        if prev is not None and r["key"] != prev:
            lines += [f"{m} & & & & & & \\\\" for m in more]       # C47: a parenthesis its modes did not take
            lines.append(r"\midrule")
            more = []
        if r["key"] != prev:
            name, *more = _tex_lines(r["label"], plus=True)   # C47: a long label's parts on the policy's next rows
        else:
            name = more.pop(0) if more else ""
        prev = r["key"]
        cases = " & ".join("--" if r["cases"][c]["runs"] is None else f"{r['cases'][c]['held']}/{r['cases'][c]['runs']}"
                           for c in ("W(a)", "W(b)", "W(c)"))
        lines.append(f"{name} & {MODE_TEX.get(r['mode'], _tex_text(r['mode']))} & {_num(r['abort_share'], '.2f')} & "
                     f"{_num(r['t_a_median'], '.0f')} & {cases} \\\\")
    lines += [f"{m} & & & & & & \\\\" for m in more]
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def write_tables(data: Mapping, report: Mapping) -> None:
    """The three supplementary E7 tables from the extract's `tables` (figs.common.write_table)."""
    t = data["tables"]
    head = "% Written by code/sim/figs/supp/sf_e7_mix.py from {}; do not edit.\n"
    paths = [write_table(TABLES[0], head.format(TABLE3) + table3_intervals_tex(t["table3_intervals"])),
             write_table(TABLES[1], head.format(MAIN) + total_accounting_tex(t["total_accounting"])),
             write_table(TABLES[2], head.format(STRESS) + stress_aborts_tex(t["stress_aborts"]))]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
