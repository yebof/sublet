"""sf_e2_por: the exact price of revocation PoR(H) = CR*(H) / (2 - alpha) of C2's game at four mu
(design/sim_spec_ms3.md §8.7, §6.6; plan §4, part S-F).

From e2/game.json (the exact deterministic game of code/theory_checks/c2/det_game.py on E2's finer H grid, with
por_default.py's settings, mapped to minutes by H_min = (H_s / beta_s) lambda_s (alpha + phi) / 60):
(a) lambda = inputs.lambda_default of por_default.json: the rows with switch cost beta~ (`switch` beta), one exact
    line per mu / beta~ in {0.2, 0.5, 1, 2} in the shades of a grey ramp (darkest mu = 2), and the C2-SW rows
    (`switch` c2sw, mu in {1, 2}) in the same shades with open circles evenly spaced along the line (MARK_EVERY).
(b) lambda = 0: the switch-beta~ rows as in (a).
In a panel whose lines of one switch cost and several mu agree at every shared H within COINCIDE_TOL (extract
<panel>.coincide; at lambda = 0, mu = 1 and 2), a note above the top one of them names those mu, since only one
line shows.
Black '+': the values of por_default.json (table_por_switch_beta; in (a) also table_por_switch_bw at
inputs.bw_default) at their H_s. A curve ends at its last grid point. C2-T4 (PROVEN under (C'), tau = 0, switch
cost beta); the threshold form at the default switch cost is VERIFIED NUMERICALLY; the C2-SW formula is a
CONJECTURE (VERIFIED NUMERICALLY at 58 points).

C62 (2026-11-24: no text above the caption's 7.97 pt; the look of Fig. 7): the key above the panels in two
rows of their own (key_row), the first "mu/beta~ =" and the four shades with their values, the second the C2-SW
circles and the Table PoR crosses, each row on one baseline (as built, one two-row legend whose second row sat 2.3 pt
lower under its mathtext entries); the notice H in math; the light y grid across both panels; H ticks thinned at half
an em of the 7-pt labels; (b) SHARED_GUTTER_IN right of (a), so that its letter clears (a); the panel titles on their
letters' baseline (panel_titles). The data and their extract entries are unchanged. C62 fix round: the y label's alpha
in math italic, as elsewhere (as built an upright Unicode glyph). Its titles' descenders lie clear of the y spines'
tops (the beta of (a) left of (a)'s spine; 3.2 pt above it under "= 0.715"), so the axes keep their place
(sf_e2_mu_ep.title_drop_in is not applied: it would move the C2-SW circles, spaced along the lines in display units).

Run from code/sim: python -m figs.supp.sf_e2_por [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

from figs import style
from figs.common import MissingKey, cli, need
from figs.fig7_e2_e6 import (GAME, H_TICK_GAP_PT, KEY_ROW_IN, POR, SHARED_GUTTER_IN, key_row, key_rows_in,
                             panel_titles, thin_x_ticks)
from figs.inputs import Inputs

NAME = "sf_e2_por"
# 2.4 in (2.2 before the 9-pt text): the key above the panels takes two rows; C62: the rows KEY_ROW_IN (0.17 in)
# apart (key_rows_in) instead of two legend rows of 0.21 in, the 0.06 in freed going to the axes (1.54 in high)
style.register_supplementary(NAME, "W1", 2.4)
# open circles on the C2-SW rows (§8.7: at every fifth grid point), spaced by this fraction of the axes diagonal
# along the line (as built at every fifth grid point, the circles bunched where the grid is dense in display)
MARK_EVERY = 0.08
COINCIDE_TOL = 1e-6               # PoR: lines that agree at every shared H within this are named in a note
PLUS = dict(linestyle="none", marker="+", markersize=4.0, markeredgewidth=0.6, color="black", label="_nolegend_",
            zorder=style.Z_DATA)
STATUS = {"C2-T4": "PROVEN under (C'), tau = 0, switch cost beta",
          "threshold form at the default switch cost": "VERIFIED NUMERICALLY",
          "C2-SW formula": "CONJECTURE (VERIFIED NUMERICALLY at 58 points)"}


def _same(a, b) -> bool:
    return abs(float(a) - float(b)) < 1e-12


def min_per_beta(rows: Sequence[Mapping]) -> float:
    """Minutes per beta~ of game.json's mapping (H_min / H_beta, constant over the rows)."""
    f = [float(r["H_min"]) / float(r["H_beta"]) for r in rows if float(r["H_beta"]) > 0]
    if not f or max(f) - min(f) > 1e-9 * max(f):
        raise MissingKey(f"{GAME}: H_min / H_beta is not one constant ({min(f, default=None)}, {max(f, default=None)})")
    return float(np.mean(f))


def coincide(series: Sequence[Mapping], tol: float = COINCIDE_TOL) -> list[dict]:
    """Groups of the lines of one switch cost whose PoR agree within `tol` at every H they share (at least two):
    [{switch, mu: [...], max_gap, n_shared}] (a group of lines that pairwise agree, joined transitively)."""
    out = []
    for switch in dict.fromkeys(s["switch"] for s in series):
        ss = sorted((s for s in series if s["switch"] == switch), key=lambda s: s["mu"])
        parent = list(range(len(ss)))

        def root(i):
            while parent[i] != i:
                i = parent[i]
            return i

        gaps: dict = {}
        for i in range(len(ss)):
            for j in range(i + 1, len(ss)):
                b = {round(h, 9): v for h, v in zip(ss[j]["H_min"], ss[j]["PoR"])}
                d = [abs(v - b[round(h, 9)]) for h, v in zip(ss[i]["H_min"], ss[i]["PoR"]) if round(h, 9) in b]
                if len(d) >= 2 and max(d) <= tol:
                    parent[root(j)] = root(i)
                    gaps[(i, j)] = (max(d), len(d))
        for r in sorted({root(i) for i in range(len(ss))}):
            members = [i for i in range(len(ss)) if root(i) == r]
            if len(members) > 1:
                pairs = [g for (i, j), g in gaps.items() if i in members and j in members]
                out.append({"switch": switch, "mu": [ss[i]["mu"] for i in members],
                            "max_gap": max(g[0] for g in pairs), "n_shared": min(g[1] for g in pairs)})
    return out


def build(inp: Inputs) -> dict:
    game, por = inp.json(GAME), inp.json(POR)
    rows = need(game, "rows", what=GAME)
    two_alpha = float(need(por, "derived", "two_minus_alpha", what=POR))
    lam_def = float(need(por, "inputs", "lambda_default", what=POR))
    bw_def = float(need(por, "inputs", "bw_default", what=POR))
    mus = [float(m) for m in need(por, "inputs", "mu_over_beta_tilde", what=POR)]
    f = min_per_beta(rows)
    out = {}
    for panel, lam, switches in (("a", lam_def, ("beta", "c2sw")), ("b", 0.0, ("beta",))):
        series, points = [], []
        for switch in switches:
            for mu in mus:
                rs = sorted((r for r in rows if r["switch"] == switch and _same(r["mu"], mu) and _same(r["lam"], lam)),
                            key=lambda r: float(r["H_min"]))
                if not rs:
                    continue
                series.append({"mu": mu, "lam": lam, "switch": switch, "H_min": [float(r["H_min"]) for r in rs],
                               "PoR": [float(r["CR"]) / two_alpha for r in rs]})
                table = need(por, "table_por_switch_beta" if switch == "beta" else "table_por_switch_bw", what=POR)
                for r in table:
                    if _same(r["mu"], mu) and _same(r["lam"], lam) and (switch == "beta" or _same(r["bw"], bw_def)):
                        points.append({"mu": mu, "lam": lam, "switch": switch, "Hs": float(r["Hs"]),
                                       "H_min": float(r["H"]) * f, "PoR_exact": float(r["PoR_exact"])})
        out[panel] = {"series": series, "points": points, "lam": lam, "coincide": coincide(series)}
    out["mus"] = mus
    out["min_per_beta_tilde"] = f
    out["coincide_tol"] = COINCIDE_TOL
    # C62: the notice H in math, italic as in Fig. 7 and the caption; the key writes "mu/beta~ =" once (mu_title)
    # before the values ("mu"; as built "mu/beta~ = {:g}" in every entry); "C2-SW switch cost" without its ", (a)"
    # (the circles are drawn in (a) only); C62 fix round: alpha in math italic as elsewhere (as built an upright "α")
    out["labels"] = {"x": "Notice $H$ (min)", "y": r"PoR = CR* / (2 − $\alpha$)", "mu_title": r"$\mu/\tilde{\beta}$ =",
                     "mu": "{:g}", "lam": r"$\lambda/\tilde{{\beta}}$ = {:.3g}", "c2sw": "C2-SW switch cost",
                     "plus": "Table PoR, default prices", "coincide": r"$\mu/\tilde{{\beta}}$ = {} coincide",
                     "status": STATUS}
    out["sources"] = list(inp.sources)
    return out


def shades(mus: Sequence[float]) -> dict:
    """Grey ramp, darkest for the largest mu."""
    ramp = style.ramp(len(mus), "greys")                 # darkest first
    return {float(m): c for m, c in zip(sorted(mus, reverse=True), ramp)}


def draw_panel(ax, block: Mapping, colors: Mapping) -> None:
    """The lines and the Table PoR crosses of one panel (draw_coincide adds the note after the final scales)."""
    for s in block["series"]:
        c = colors[float(s["mu"])]
        kw = dict(color=c, label="_nolegend_", zorder=style.Z_THEORY, **style.THEORY_STYLES["exact"])
        if s["switch"] == "c2sw":
            kw.update(marker="o", markevery=MARK_EVERY, markersize=3.0, markerfacecolor="white",
                      markeredgecolor=c, markeredgewidth=style.MARKER_EDGE_PT)
        (line,) = ax.plot(s["H_min"], s["PoR"], **kw)
        line._sublet_role = "theory:exact"
    pts = block["points"]
    if pts:
        ax.plot([p["H_min"] for p in pts], [p["PoR_exact"] for p in pts], **PLUS)


def draw_coincide(ax, block: Mapping, colors: Mapping, labels: Mapping) -> list:
    """For each group of coinciding lines (block["coincide"]), the note labels["coincide"] with their mu, just above
    the group's line at its first point, left-aligned, in the darkest shade of the group (readable on white); after
    the final scales."""
    out = []
    for grp in block.get("coincide", []):
        mus = sorted(float(m) for m in grp["mu"])
        s = next(s for s in block["series"] if s["switch"] == grp["switch"] and float(s["mu"]) == mus[-1])
        t = ax.annotate(labels["coincide"].format(", ".join(f"{m:g}" for m in mus)), xy=(s["H_min"][0], s["PoR"][0]),
                        xytext=(2.0, 3.0), textcoords="offset points", ha="left", va="bottom",
                        fontsize=style.TICK_PT, color=style.readable_on_white(colors[mus[-1]]))
        t._sublet_role = "coincide_note"
        out.append(t)
    return out


KEY_ROWS = 2                       # the key's rows above the panels (key)


def key(fig, axes: Sequence, colors: Mapping, labels: Mapping) -> list:
    """The key above the panels, two rows centered over the axes (key_row; KEY_ROW_IN apart): the mu shades of both
    panels as "mu/beta~ =" and line samples with the values, darkest (mu = 2) first; then the C2-SW circles and the
    Table PoR crosses. A key of categories (plan §5: non-policy categories in grey ramps), not of policies; the
    lightest shade does not read as text, so the shades are not text colors. As built at 9 pt (2026-10-22): the key
    inside (b) was wider than the panel and ran over (a)'s curves; until C62 one two-row legend with "mu/beta~ = "
    in each of the four entries, its second row 2.3 pt lower under them than under the third column. Extracts of
    the 9-pt figure have no labels["mu_title"]; their "mu" entries are written in full, without a title."""
    W, H = fig.get_size_inches()
    x0 = style.axes_rect_in(axes[0])[0]
    r = style.axes_rect_in(axes[-1])
    xc = 0.5 * (x0 + r[0] + r[2])
    mus = sorted(colors, reverse=True)
    pairs = [(Line2D([], [], color=colors[mu], **style.THEORY_STYLES["exact"]), labels["mu"].format(mu))
             for mu in mus]
    marks = [(Line2D([], [], color="#4D4D4D", marker="o", markersize=3.0, markerfacecolor="white",
                     markeredgewidth=style.MARKER_EDGE_PT, **style.THEORY_STYLES["exact"]), labels["c2sw"]),
             (Line2D([], [], linestyle="none", **{k: v for k, v in PLUS.items() if k != "linestyle"}),
              labels["plus"])]
    return [key_row(fig, row, x_center_in=xc, y_center_in=H - (i + 0.5) * KEY_ROW_IN, title=title)
            for i, (row, title) in enumerate(((pairs, labels.get("mu_title")), (marks, None)))]


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    ax_a, ax_b = style.panel_row(fig, (1, 1), sharey=(False, True), top=key_rows_in(KEY_ROWS),
                                 left=(None, SHARED_GUTTER_IN))          # C62: room for (b)'s letter
    colors = shades(data["mus"])
    xmax = max(max(s["H_min"]) for p in "ab" for s in data[p]["series"])
    ymin = min(min(s["PoR"]) for p in "ab" for s in data[p]["series"])
    ymax = max(max(s["PoR"]) for p in "ab" for s in data[p]["series"])
    for ax, p in ((ax_a, "a"), (ax_b, "b")):
        draw_panel(ax, data[p], colors)
        ticks = [t for t in style.H_TICKS_MIN if t <= xmax]
        style.symlog_minutes(ax, "x", ticks=ticks, end_inside=False)
        ax.set_xlim(-0.08, xmax * 1.12)            # the markers at H = 0 and at the last H clear of the axes edges
        thin_x_ticks(ax, ticks, gap_pt=H_TICK_GAP_PT)      # C62: half an em of the 7-pt labels
        ax.set_xlabel(lab["x"])
    key(fig, (ax_a, ax_b), colors, lab)
    pad = 0.04 * (ymax - ymin)
    ax_a.set_ylim(ymin - pad, ymax + pad)
    ax_a.yaxis.set_major_locator(MaxNLocator(5, steps=[1, 2, 2.5, 5, 10]))
    ax_a.yaxis.set_major_formatter(style.PLAIN)
    ax_a.set_ylabel(lab["y"])
    for ax in (ax_a, ax_b):
        style.ygrid(ax)                            # C62: the light y grid of Fig. 7(a), (b), across both panels
    for ax, p in ((ax_a, "a"), (ax_b, "b")):
        draw_coincide(ax, data[p], colors, lab)
    panel_titles((ax_a, ax_b), [lab["lam"].format(data[p]["lam"]) for p in "ab"])   # each panel's lambda
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
