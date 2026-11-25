"""sf_e6a: E6(a) for spot pools and lambda' = 0, with every cell as a table (design/sim_spec_ms3.md §8.7, §7.1;
plan §4, part S-F).

Heatmaps of cost(BL7) / cost(A1) over H and alpha_p / alpha as Fig. 7(c), at mu / beta~ = 1 (e6/a/heatmap.json
cells.<group>.<lam'>.1): (a) spot, lambda' = a5 (the measured load time; titled so); (b) MaaS, lambda' = 0; (c) spot,
lambda' = 0, with one shared log norm centered at 1 (PuOr) and one colorbar in a slim column right of (c) (as built
with an inset colorbar above (c)'s rows, it sat wedged between (c)'s title and its cells), so the rows fill the
axes; the black step line where the ratio crosses 1 and the "< 1" / "> 1" cues, as in Fig. 7(c) (extract
<panel>.contour, with its tolerance: a cell within 0.5% below 1 counts as 1); the boundary r*(H) computed with the
certified bound (e6/a/boundary.json rows.1.<lam'>.<group>.r_star; C2-T3, PROVEN for tau = 0) as a dotted line with a
white halo, its label on an opaque white box where it sits over missing cells. Spot cells are missing where fewer
than two pools have an A1 cell (M23), hatched; the step line skips their edges.

C62 (2026-11-24; the look of Fig. 7(c)): each heatmap framed on all four sides; the cues "< 1", "= 1" and "> 1"
each in the roomiest part of its region (region_cues); the boundary's halo HEAT_HALO_PT; H ticks thinned at half an em
of the 7-pt labels, 30 min before 60 min; SHARED_GUTTER_IN before (b) and (c); the notice H in math. The cells, the
extract's data and both tables are unchanged. C62 fix round: lambda' in the titles in math italic, as the caption sets
it (as built an upright Unicode glyph), each title on its letter's baseline as the PDF prints it (panel_titles); the
axes' tops sf_e2_mu_ep.title_drop_in below the letters' line (about 1.8 pt more), so that the descenders of "Spot,"
and "MaaS," end TITLE_CLEAR_PT above the top frame (they crossed it).

The script also writes e6a_cells.tex and e6a_cells.csv (C52) to figs.common.tables_dir() (SUBLET_FIGS_TABLES_DIR,
else SUBLET_FIGS_PDF_DIR when set, else paper/supplement/tables/): every cell of Fig. 7(c), of (a)-(c) and of the other
mu, with its value, 95% interval, n_pairs and share_insured (as built, a longtable in e6a_cells.tex; since C52 the data
file, with a summary table). The cells are in the extract (`table`), so --from-extract rewrites them.

C50 (design/ms6_spec.md §7.2, the D5 review, with §7.1 D4's script items): the table keeps the cells with a value and
its caption counts the others; each (group, lambda', mu) block is a longtable whose head repeats "Table <n>, continued"
and the block's label; the caption uses the paper's names (cells_tex).

C52 (design/ms7/plan.md D3 and §4, unit T1: the manuscript scan): the cell list, 21 pages of the supplement as a
longtable, becomes the supplementary data file e6a_cells.csv (cells_csv, beside e7v2_rc_runs.csv): one line per cell
with a value, with the columns of CELLS_COLUMNS. e6a_cells.tex is now a one-page summary of it (cells_tex): one row per
(group, lambda', mu) block with the number of cells with a value, how many lie above 1, at 1 (within the heatmaps'
tolerance fig7_e2_e6.CONTOUR_TOL below 1, as the step line counts them) and below, and the least and largest ratio;
its caption names the data file, defines its columns and counts the cells left out. Both are written from the
extract's `table` (unchanged), so --from-extract rewrites them.

Run from code/sim: python -m figs.supp.sf_e6a [--from-extract [JSON]].
"""
from __future__ import annotations

import csv
import io
import sys
from typing import Any, Mapping, Sequence

from figs import style
from figs.common import cli, need, num_items, tex_num, write_table
from figs.fig7_e2_e6 import (BOUND, CONTOUR_TOL, H_TICK_GAP_PT, H_TICK_PRIORITY_C, HEAT, HEAT_HALO_PT, LABELS,
                             MAIN_LABELS, SHARED_GUTTER_IN, STATUS, draw_heat_panel, heat_block, panel_titles,
                             right_colorbar_in)
from figs.inputs import Inputs
from figs.supp.sf_e2_mu_ep import raise_texts, title_drop_in        # C62 fix round

NAME = "sf_e6a"
# C52 (design/ms7/plan.md D3, T1): the summary table and the data file of every cell (rebuild.py reads TABLES)
TABLES = ("e6a_cells.tex", "e6a_cells.csv")                                                         # C52
TABLE, CELLS_CSV = TABLES                                                                           # C52
# C52: the data file's columns: lender group, protected load time ("measured" or "0"), mu / beta~, notice H (min),
# price ratio alpha_p / alpha, the cost of revocable-only leasing over ALG* (the cell's value), its 95% interval, the
# number of pairs (at mu / beta~ = 1, triples) and the share of them where ALG* insures
CELLS_COLUMNS = ("lender_group", "protected_load_time", "mu_over_beta_tilde", "notice_H_min",
                 "price_ratio_alpha_p_over_alpha", "revocable_only_over_alg_star", "ci95_lo", "ci95_hi", "n",
                 "share_insured")                                                                   # C52
CSV_GROUP = {"maas": "MaaS", "spot": "spot"}                                                        # C52
CSV_LAM = {"a5": "measured", "0": "0"}                                                              # C52
MU = 1                                                      # §8.7: the heatmaps at mu / beta~ = 1
PANELS = (("a", "spot", "a5"), ("b", "maas", "0"), ("c", "spot", "0"))
GROUP_NAME = {"maas": "MaaS", "spot": "Spot"}
# a5: the analysis step that measures it. C62 fix round: lambda' in math italic as the caption sets it (as built an
# upright Unicode "λ′"); the prime as \prime at full size beside the lambda, as LaTeX prints $\lambda'$ (mathtext
# sets $\lambda'$'s prime as a 5.6-pt superscript, a speck above the line at print size); panel_titles puts the
# mathtext titles on their letters' baseline as the PDF prints them
LAM_NAME = {"a5": r"$\lambda\prime$ = measured load time", "0": r"$\lambda\prime$ = 0"}
style.register_supplementary(NAME, "W2", 2.2)
CELL_FIELDS = ("value", "ci", "n_pairs", "share_insured")


def table_rows(heat: Mapping) -> list[dict]:
    """Every cell of heatmap.json: group, lam, mu, H_min, r, value, ci_lo, ci_hi, n_pairs, share_insured, note."""
    rows = []
    cells = need(heat, "cells", what=HEAT)
    for group in sorted(cells):
        if group.endswith("_note"):
            continue
        for lam in sorted(cells[group], key=lambda k: (k != "a5", k)):
            if lam.endswith("_note"):
                continue
            for mu, mk, by_h in num_items(cells[group][lam]):
                rs = sorted({x for _, _, c in num_items(by_h) if isinstance(c, Mapping) for x, _, _ in num_items(c)})
                for H, hk, c in num_items(by_h):
                    for r in rs:
                        cell = None
                        if isinstance(c, Mapping):
                            cell = {x: v for x, _, v in num_items(c)}.get(r)
                        ci = (cell or {}).get("ci95") or [None, None]
                        rows.append({"group": group, "lam": lam, "mu": mu, "H_min": H, "r": r,
                                     "value": (cell or {}).get("value"), "ci_lo": ci[0], "ci_hi": ci[1],
                                     "n_pairs": (cell or {}).get("n_pairs"),
                                     "share_insured": (cell or {}).get("share_insured"),
                                     "note": (None if (cell or {}).get("value") is not None else
                                              (cell or {}).get("note") or (cell or {}).get("value_note")
                                              or by_h.get(hk + "_note") or "missing")})
    return rows


def build(inp: Inputs) -> dict:
    heat, bnd = inp.json(HEAT), inp.json(BOUND)
    out = {}
    for p, group, lam in PANELS:
        hb = heat_block(heat, bnd, group, lam, MU)
        out[p] = {k: hb[k] for k in ("H_min", "x_edges", "y_edges", "rows", "values", "ci", "n_pairs",
                                     "share_insured", "vmin", "vmax", "notes", "boundary", "contour", "group", "lam",
                                     "mu")}
    vmax = max(out[p]["vmax"] for p, _, _ in PANELS)
    out["vmin"], out["vmax"] = 1.0 / vmax, vmax
    out["table"] = table_rows(heat)
    # C62: the notice H in math, as in Fig. 7 (MAIN_LABELS)
    out["labels"] = {**LABELS, "H": MAIN_LABELS["H"], "status": STATUS,
                     "titles": {p: f"{GROUP_NAME[g]}, {LAM_NAME[l]}" for p, g, l in PANELS},
                     "note": "mu/beta~ = 1; median over (lender, series, alignment) of the layer-summed cost ratio "
                             "(M29); boundary with the certified bound (M30); spot cells missing where fewer than "
                             "two pools have an A1 cell (M23)"}
    out["sources"] = list(inp.sources)
    return out


def draw(data: Mapping) -> Any:
    """C62 (the look of Fig. 7(c)): each heatmap framed on all four sides (frame; its cells of ratio 1, most of (a),
    are so pale that the panel's edges vanished without top and right spines); the cues "< 1", "= 1" and "> 1",
    each in the roomiest part of its region (region_cues; as built, sign_cues set "< 1" and "> 1" in the most extreme
    cells and the cells of ratio 1 had none); the boundary's halo HEAT_HALO_PT on each side of its line and label;
    the H ticks thinned at half an em of the 7-pt labels (H_TICK_GAP_PT), 30 min kept before 60 min as in Fig. 7(c)
    (H_TICK_PRIORITY_C: (b)'s step line turns on both sides of the 30-min column); the gutters before (b) and (c)
    SHARED_GUTTER_IN, so that their letters do not overhang the frame to their left. The colorbar of the shared norm
    stays in a slim column right of (c), as high as the rows."""
    lab = data["labels"]
    fig = style.new_figure(NAME)
    norm = style.ratio_norm(data["vmin"], data["vmax"])
    drop = title_drop_in()                         # C62 fix round: the titles' descenders clear of the top frame
    axes = style.panel_row(fig, (1, 1, 1), sharey=(False, True, True), top=style.MARGIN_TOP + drop,
                           left=(None, SHARED_GUTTER_IN, SHARED_GUTTER_IN),      # C62: room for the letters
                           right=style.MARGIN_RIGHT + right_colorbar_in(fig, norm, lab))
    for i, (ax, (p, _, _)) in enumerate(zip(axes, PANELS)):
        draw_heat_panel(ax, data[p], norm, lab, colorbar=(i == len(PANELS) - 1), ylabel=(i == 0), headroom=False,
                        cbar_at="right", cues="region", h_gap_pt=H_TICK_GAP_PT, h_priority=H_TICK_PRIORITY_C,
                        halo_pt=HEAT_HALO_PT, frame=True)
    letters, titles = panel_titles(axes, [lab["titles"][p] for p, _, _ in PANELS])
    raise_texts(letters + titles, drop)
    return fig


# ---------------------------------------------------------------------------------------------------------------
def _left_out(table: Sequence[Mapping]) -> str:
    """The caption's count of the cells without a value (C50): the spot cells that fewer than two pools have (M23;
    hatched in the figure) are named so; '' when every cell has a value."""
    gone = [r for r in table if r["value"] is None]                                          # C50
    spot = bool(gone) and all(r["group"] == "spot" and "fewer than two spot pools" in str(r.get("note") or "")
                              for r in gone)                                                 # C50
    why = r" (spot cells with data from fewer than two pools; hatched in Fig.~\ref{fig:s-sf_e6a})" if spot else ""
    return ((f" The {len(gone):,} cells without a value{why} are left out." if len(gone) != 1 else
             f" The one cell without a value{why} is left out.") if gone else "")             # C50


def _blocks(table: Sequence[Mapping]) -> list[tuple[tuple, list]]:
    """The cells with a value in blocks of one (group, lambda', mu), in the table's order."""
    blocks: list[tuple[tuple, list]] = []
    for row in table:
        if row["value"] is None:
            continue
        block = (row["group"], row["lam"], row["mu"])
        if not blocks or blocks[-1][0] != block:
            blocks.append((block, []))
        blocks[-1][1].append(row)
    return blocks


def block_counts(rows: Sequence[Mapping], tol: float = CONTOUR_TOL) -> dict:
    """C52: the summary of one block's cells with a value: their number, how many lie above 1, at 1 (from 1 - tol to
    1: the heatmaps' step line counts a cell within tol below 1 as 1, fig7_e2_e6.CONTOUR_TOL) and below 1 - tol, and
    the least and largest value."""
    v = [float(r["value"]) for r in rows]
    return {"n": len(v), "above": sum(x > 1.0 for x in v), "at": sum(1.0 - tol <= x <= 1.0 for x in v),
            "below": sum(x < 1.0 - tol for x in v), "min": min(v), "max": max(v)}


def cells_tex(table: Sequence[Mapping]) -> str:
    """C52 (design/ms7/plan.md D3, T1): the summary of the cells with a value, one row per (group, lambda', mu) block
    (block_counts), as a one-page longtable that names the data file CELLS_CSV (cells_csv; in \\textnormal, so that
    the caption's small capitals keep its lower case) and defines its columns.

    As built under C50, a longtable of every cell with a value in blocks with repeated heads (21 pages of the
    supplement); C50's caption rules hold: the cells without a value are left out and counted (_left_out), and the
    caption uses the paper's names (revocable-only leasing over ALG*, the share of pairs where ALG* insures)."""
    caption = (r"\caption{E6(a): the cells of the protection heatmaps per lender group, protected load time $\lambda'$ "
               r"and $\mu/\tilde\beta$. A cell holds the cost of revocable-only leasing over ALG$^\ast$: the median "
               r"over (lender, series) pairs, at $\mu/\tilde\beta=1$ over (lender, series, alignment) triples, of the "
               r"layer-summed cost ratio; above $1$, ALG$^\ast$'s insurance pays. Columns: the cells with a value, "
               r"those above $1$, at $1$ (down to " + f"{100 * CONTOUR_TOL:g}" + r"\% below $1$, as the step lines of "
               r"the heatmaps count them) and below $1$, and the range of the ratio. The supplementary data file "
               r"\textnormal{" + CELLS_CSV.replace("_", r"\_") + r"} lists every cell with a value: lender group, "
               r"$\lambda'$, "
               r"$\mu/\tilde\beta$, $H$ (min), $\alpha_p/\alpha$, the ratio, its 95\% bootstrap interval, the "
               r"number of pairs and the share of pairs where ALG$^\ast$ insures." + _left_out(table)
               + r"}\label{tab:e6a_cells}\\" "\n")                                                   # C52
    hdr = (r"Lenders & $\lambda'$ & $\mu/\tilde\beta$ & Cells & Above $1$ & At $1$ & Below $1$ & Range \\"
           "\n")                                                                                  # C52
    lam_tex = {"a5": "measured", "0": r"$0$"}
    lines = [r"\begin{longtable}{llrrrrrc}" "\n" + caption,
             r"\toprule" "\n" + hdr + r"\midrule" "\n" r"\endfirsthead" "\n",
             r"\multicolumn{8}{@{}l}{Table~\thetable, continued}\\[2pt]" "\n"
             r"\toprule" "\n" + hdr + r"\midrule" "\n" r"\endhead" "\n",
             r"\endlastfoot" "\n"]
    last = (None, None)
    for (group, lam, mu), rows in _blocks(table):
        c = block_counts(rows)
        g = GROUP_NAME.get(group, group) if group != last[0] else ""
        lm = lam_tex.get(lam, lam) if (group, lam) != last else ""
        if last[0] is not None and group != last[0]:
            lines.append(r"\addlinespace" "\n")
        last = (group, lam)
        lines.append(f"{g} & {lm} & {mu:g} & {c['n']} & {c['above']} & {c['at']} & {c['below']} & "
                     f"{tex_num(c['min'])}--{tex_num(c['max'])} \\\\\n")                       # C52
    lines.append(r"\bottomrule" "\n" r"\end{longtable}" "\n")
    return "".join(lines)


def _csv_num(v, fmt: str) -> str:
    return "" if v is None else format(float(v), fmt)


def cells_csv(table: Sequence[Mapping]) -> str:
    """C52 (design/ms7/plan.md D3, T1): the data file CELLS_CSV, one line per cell with a value in the table's order,
    the columns CELLS_COLUMNS: the ratio and its interval with 6 decimals, the share where ALG* insures with 6, H, the
    price ratio and mu as given (%g)."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CELLS_COLUMNS)
    for r in table:
        if r["value"] is None:
            continue
        w.writerow([CSV_GROUP.get(r["group"], r["group"]), CSV_LAM.get(r["lam"], r["lam"]), f"{r['mu']:g}",
                    f"{r['H_min']:g}", f"{r['r']:g}", _csv_num(r["value"], ".6f"), _csv_num(r["ci_lo"], ".6f"),
                    _csv_num(r["ci_hi"], ".6f"), "" if r["n_pairs"] is None else f"{int(r['n_pairs'])}",
                    _csv_num(r["share_insured"], ".6f")])
    return buf.getvalue()


def write_cells_table(data: Mapping, report: Mapping) -> None:
    """e6a_cells.tex and (C52) e6a_cells.csv in figs.common.tables_dir() (SUBLET_FIGS_TABLES_DIR, else
    SUBLET_FIGS_PDF_DIR, else paper/supplement/tables/)."""
    head = "% Written by code/sim/figs/supp/sf_e6a.py from code/sim/out/e6/a/heatmap.json; do not edit.\n"
    p = write_table(TABLE, head + cells_tex(data["table"]))
    q = write_table(CELLS_CSV, cells_csv(data["table"]))                                           # C52
    print(f"[{NAME}] wrote {p} and {q} ({sum(r['value'] is not None for r in data['table'])} of "
          f"{len(data['table'])} cells, those with a value)")                                         # C50; C52


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, after=write_cells_table, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
