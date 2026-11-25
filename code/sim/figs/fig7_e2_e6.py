"""Fig. 7: one site, the value of notice, its price and when protection pays (E2, E6(a)); design/sim_spec_ms3.md §8.6.

(a) Per-episode ALG / OPT against the notice H (min, symlog) at mu / beta~ = 1 under `trace` (e2/summary.json
    episodes.<group>.<H>.1.<rule>): median line per rule and lender group (MaaS solid, spot dashed) and A1's band
    from the median to the P95 (MaaS filled, spot as a dashed outline, so that their overlap does not read as a
    third band); the pre-warm rule only at the H where the coincidence table says it differs from A1 (Q42 (a)),
    drawn as a larger open ring behind ALG*, and BL6 as a smaller X with a dark edge on top of ALG*, so that all
    three are seen where their medians coincide (a.overlap); spot points null where fewer than two pools have an A1
    cell (M23). Grey solid: the exact CR*(H) of C2's game (e2/game.json, switch beta~, mu = 1, lambda =
    por_default.json inputs.lambda_default), continued from its last grid point at 2 - alpha (por_default.json
    derived.two_minus_alpha) where that point is at or above C2-T4's H*_mu (game.json meta.hstar). Reference
    verticals at H*_mu and H*_beta for tier M (a11_calibration.json, M25).
(b) Total cost over BL0a against H: A1's MaaS and spot medians of the (lender, series, alignment) totals
    (totals.<group>.<H>.1.trace.a1.cost_over_bl0a) with their bootstrap intervals, a marker at each minimizing H
    (best_H.<group>.1.trace.a1), and the level 1 (all-fallback) as a reference line.
(c) Heatmap of cost(BL7) / cost(A1) over H and alpha_p / alpha (e6/a/heatmap.json cells.maas.a5.1), PuOr on a
    log norm centered at 1, with a thin black step line along the cell edges where the ratio crosses 1 (cells
    below 1 - CONTOUR_TOL on one side, the others on the other: a cell within 0.5% below 1 counts as 1; extract
    c.contour with its tol, label "contour"), since PuOr prints both signs as mid grey in greyscale (2026-10-22),
    a 7-pt "< 1" and "> 1" in the two regions (and "= 1" in the third, region_cues, C62), and the
    boundary r*(H) computed with the certified bound (e6/a/boundary.json rows.1.a5.maas; C2-T3, PROVEN for tau = 0)
    as a dotted line with a white halo (HEAT_HALO_PT on each side in Fig. 7), under the step line.

C62 (2026-11-24: no text above the caption's 7.97 pt; high-end, informative, readable), Fig. 7's drawing only
(draw(); the shared builders and drawers keep their defaults for sf_e2_* and sf_e6a, every number drawn comes from the
extract as before, and the extract is unchanged): one header row, the legend centered over (a) and (b), whose series
it keys, and the colorbar of (c) over (c) on the legend's center line (draw_heat_panel(..., cbar_at="header")), so
that (c)'s cells take the axes' full height (the inset colorbar took 0.30 in of it); (a) the MaaS band's top edge
labeled "P95" at its right end (band_top_label); (b) the light y grid of (a) and the lender lines labeled directly
(lender_labels); (c) the cues "< 1", "= 1" and "> 1" each in the roomiest part of its region in its strongest colors
(region_cues: "= 1" marks the cells where revocable-only leasing equals ALG*, which then does not insure), and the H
ticks thinned at half an em of the 7-pt labels (H_TICK_GAP_PT), which keeps 30 min in (a) and (b) and 5 min in (c).
After the review of C62's redesign: (c) framed on all four sides (frame=True: its cells of ratio 1, over a third of
the panel, are so pale that without top and right spines the panel's edges vanished on paper); the boundary's halo
thinned to HEAT_HALO_PT on each side, line and label (style.HALO_PT made the line read as a white solid line with grey
dots and left white rims around its label on the pale cells); (c) labels 30 min and leaves 60 min a minor tick
(H_TICK_PRIORITY_C: the step line turns between the 30 and 60 columns); the legend's dashed Spot sample centered on
its dash pattern (centered_dashes: three whole dashes, no sliver of a fourth at its right end).

The drawn labels name no design ID (MS6 C46: design/ms6_spec.md M6, M11): the boundary is "LB_react" (C2-T3) and the
exact curve "exact CR*(H)" (of C2's core game) on two lines (as built at 9 pt, "single-site core" on a second line,
or the name on one line, ran over the dashed edge of the spot band left of 6 min, which cr_label_end does not avoid
and the label's halo does not cover), MAIN_LABELS; the caption (LaTeX, in the
manuscript) gives the paper's result numbers and names the single-site core, and the status labels of the extract
keep the design names (data). LABELS keeps the labels
with the design names, which the supplementary sf_e2_mu_ep, sf_e2_mu_cost and sf_e6a take (the supplement keeps the
design names, M9).

Run from code/sim: python -m figs.fig7_e2_e6 [--from-extract [JSON]].

The panel builders and drawers are shared with sf_e2_mu_ep, sf_e2_mu_cost, sf_e2_pool, sf_e2_por and sf_e6a.
"""
from __future__ import annotations

import math
import sys
from typing import Any, Mapping, Sequence

import matplotlib as mpl
import numpy as np
from matplotlib import patheffects
from matplotlib.colors import to_rgb
from matplotlib.font_manager import FontProperties
from matplotlib.legend_handler import HandlerBase
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.textpath import TextPath
from matplotlib.ticker import FixedLocator, NullFormatter, NullLocator

from figs import style
from figs.common import (MissingKey, align_baselines, cli, finite, maybe, need, num_items, place_label, points_pt,
                         text_width_in)
from figs.inputs import Inputs

NAME = "fig7"
E2 = "code/sim/out/e2/summary.json"
GAME = "code/sim/out/e2/game.json"
POR = "code/theory_checks/c2/out/por_default.json"
A11 = "code/analysis/out/a11_calibration.json"
HEAT = "code/sim/out/e6/a/heatmap.json"
BOUND = "code/sim/out/e6/a/boundary.json"

GROUPS = ("maas", "spot")
LENDER = {"maas": ("lender", "maas"), "spot": ("lender", "spot")}
FIXED_RULE_TABLE = {"prewarm": "coincide", "cold": "cold_equals_a1"}    # e2/summary.json, §6.7
RAN_RULES = ("bl6",)            # drawn only where they ran (e2/summary.json episodes...<rule>.ran; §6.4, §8.7)
A11_TIER = ("table_3_8_by_tier", "values", "maas_a10", "M", "a5_2GBps")             # M25
RATIO_TICKS = (0.5, 0.67, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0)                       # colorbar candidates
STATUS = {"C2-T4": "PROVEN under (C'), tau = 0, switch cost beta, site-window semantics",
          "C2-Cor5": "PROVEN under (C) with the proviso of C2-Cor5(3)",
          "threshold form at the default switch cost, mu = 1": "VERIFIED NUMERICALLY",
          "C2-T2": "PROVEN for insurance held to the end of the demand", "C2-T3": "PROVEN for tau = 0"}
CONTOUR_LEVEL = 1.0             # (c): the black step line between cells with ratio < 1 - tol and the others
CONTOUR_TOL = 0.005             # a cell within 0.5% below 1 counts as 1 (sf_e6a: medians of 0.9987-0.99997)
LABELS = {"H": "Notice H (min)", "a_y": "Per-episode ALG / OPT", "b_y": "Total cost / all-fallback",
          "c_y": r"Price ratio $\alpha_p/\alpha$", "cr": "exact CR*(H), C2 core",
          "H_star_mu": r"$H^\star_\mu$", "H_star_beta": r"$H^\star_\beta$",
          "boundary": r"LB$_{\mathrm{react}}$, C2-T3", "colorbar": "Revocable-only / ALG*",
          "contour": f"ratio = 1 (cells within {CONTOUR_TOL:.1%} below 1 count as 1)",
          "below": "< 1", "above": "> 1"}      # with the design names: the supplementary panels' (sf_e2_*, sf_e6a)
# C46 (design/ms6_spec.md M6, M11): Fig. 7's drawn labels, without design IDs; C47 (print check of the gate, U46): the
# notice H in math, italic as in $H^\star_\mu$ and $H^\star_\beta$ of the same figure (LABELS, which the frozen
# supplementary panels sf_e2_* and sf_e6a draw, keep their upright H)
MAIN_LABELS = {**LABELS, "H": "Notice $H$ (min)", "cr": "exact\nCR*($H$)", "boundary": r"LB$_{\mathrm{react}}$"}
CONTOUR_PT = 0.6
# above the cells (0.8), the hatch (0.7) and the boundary line with its halo (Z_THEORY), so that the halo hides no
# part of it where the two run close (as built at 9 pt: H = 2-30 min and the step near 1.4 min in Fig. 7(c)); below
# the theory label (Z_THEORY_LABEL)
Z_CONTOUR = style.Z_THEORY + 0.05


# ---------------------------------------------------------------------------------------------------------------
# (a) per-episode ratios
def h_values(block: Mapping) -> list[float]:
    return [x for x, _, _ in num_items(block)]


def coincides(e2: Mapping, rule: str, group: str, hk: str, mu) -> tuple[Any, str | None]:
    """Whether a fixed rule equals A1 at (group, H, mu) (Q42 (a)), as e2.py writes it: the pre-warm rule from
    coincide.<group>.<H>.<mu>, "always cold" from cold_equals_a1.<group>.<H>.<mu> (booleans; null with a note where
    nothing is compared)."""
    v, note = maybe(e2, FIXED_RULE_TABLE[rule], group, hk, mu)
    if v is not None and not isinstance(v, bool):
        raise MissingKey(f"{E2}: {FIXED_RULE_TABLE[rule]}.{group}.{hk}.{format(float(mu), 'g')} is "
                         f"{type(v).__name__}, not a boolean (§6.7)")
    return v, note


def episode_block(e2: Mapping, mu, rules: Sequence[str], groups: Sequence[str] = GROUPS,
                  ran_rules: Sequence[str] = RAN_RULES) -> dict:
    """{rule: {group: {H_min, median, p95, n, note}}} from episodes.<group>.<H>.<mu>.<rule>; a fixed rule (pre-warm,
    always cold) only where coincide.<group>.<H>.<mu> says it differs from A1; a rule of `ran_rules` (BL6) only
    where it ran (`ran` not false: BL6 is not run at H = 0, where it equals A1, and takes A1's values there, §6.4);
    `shown_at` lists the H of the fixed rules."""
    eps = need(e2, "episodes", what=E2)
    out: dict = {r: {} for r in rules}
    shown: dict = {}
    for g in groups:
        hs = num_items(need(eps, g, what=f"{E2} episodes"))
        for rule in rules:
            s = {"H_min": [], "median": [], "p95": [], "n": [], "note": []}
            for H, hk, _ in hs:
                ent, note = maybe(eps, g, hk, mu, rule)
                if ent is not None and ent.get("median") is None:          # every field null with `note` (M23)
                    ent, note = None, ent.get("note") or ent.get("median_note") or "null"
                if ent is not None and rule in ran_rules and ent.get("ran") is False:
                    ent, note = None, ent.get("ran_note") or "not run here (takes A1's values, §6.4)"
                if ent is not None and rule in FIXED_RULE_TABLE:
                    same, cnote = coincides(e2, rule, g, hk, mu)
                    if same is None:
                        ent, note = None, f"coincidence unknown ({cnote})"
                    elif same:
                        ent, note = None, "equals A1 (Q42 (a))"
                    else:
                        shown.setdefault(rule, {}).setdefault(g, []).append(H)
                s["H_min"].append(H)
                s["median"].append(None if ent is None else ent.get("median"))
                s["p95"].append(None if ent is None else ent.get("p95"))
                s["n"].append(None if ent is None else ent.get("n"))
                s["note"].append(note)
            out[rule][g] = s
    out["shown_at"] = shown
    return out


def cr_curve(game: Mapping, por: Mapping, mu, *, h_end: float, switch: str = "beta", lam=None) -> dict:
    """The exact CR*(H) rows of game.json (switch, mu, lambda = inputs.lambda_default unless given) by H_min, and its
    continuation at 2 - alpha from the last grid point to h_end where that point lies at or above C2-T4's H*_mu
    (game.json meta.hstar.<mu>.<lambda>, switch beta)."""
    lam = need(por, "inputs", "lambda_default", what=POR) if lam is None else lam
    rows = sorted((r for r in need(game, "rows", what=GAME) if r["switch"] == switch
                   and abs(float(r["mu"]) - float(mu)) < 1e-12 and abs(float(r["lam"]) - float(lam)) < 1e-12),
                  key=lambda r: float(r["H_min"]))
    if not rows:
        raise MissingKey(f"{GAME}: no rows with switch {switch!r}, mu {mu}, lam {lam}")
    hstar = need(game, "meta", "hstar", mu, format(float(lam), "g"), what=GAME)
    last = float(rows[-1]["H_min"])
    ext = None
    if last >= float(need(hstar, "H_min", what=f"{GAME} meta.hstar")):
        ext = {"from_H_min": last, "to_H_min": float(h_end),
               "value": need(por, "derived", "two_minus_alpha", what=POR)}
    return {"H_min": [float(r["H_min"]) for r in rows], "CR": [float(r["CR"]) for r in rows], "extension": ext,
            "hstar_H_min": float(hstar["H_min"]), "mu": float(mu), "lam": float(lam)}


def verticals(a11: Mapping, mu) -> dict:
    v = need(a11, *A11_TIER, what=A11)
    return {"H_star_mu_min": float(need(v, "H_star_mu_s", str(float(mu)), what=A11)) / 60.0,
            "H_star_beta_min": float(need(v, "H_star_beta_s", what=A11)) / 60.0}


H_TICK_PRIORITY = (1.0, 10.0, 60.0, 2.0, 5.0, 30.0, 15.0, 120.0)   # after the first and last tick (minutes)


def thin_x_ticks(ax, ticks: Sequence[float], *, gap_pt: float = 5.0,
                 priority: Sequence[float] = H_TICK_PRIORITY) -> list[float]:
    """Major x ticks whose labels stay at least gap_pt apart (measured; so that neighbors such as "5" and "10" do not
    read as one group; 5 pt by default, about half an em of the 9-pt labels before C62, kept for sf_e2_por and
    sf_e2_pool; Fig. 7 passes H_TICK_GAP_PT, half an em of its 7-pt labels), chosen in the order: the last and the
    first tick, then `priority` (H_TICK_PRIORITY by default: 1 min, 10 min, 1 h, ...; Fig. 7(c) passes
    H_TICK_PRIORITY_C), then the rest from the right, each kept if its label clears the labels kept so far (a label
    at the right end of the axis is right-aligned, end_label_inside; the others are centered); the others become
    unlabeled minor ticks."""
    to_pt = 72.0 / ax.figure.dpi
    ticks = sorted(float(t) for t in ticks)
    right = ax.get_xlim()[1]
    rank = {float(t): i for i, t in enumerate(priority)}
    order = ticks[-1:] + ticks[:1] + sorted(ticks[1:-1], key=lambda t: (rank.get(t, len(rank)), -t))
    kept, boxes = [], []
    for t in order:
        if t in kept:
            continue
        x = ax.transData.transform((t, 1.0))[0] * to_pt
        w = text_width_in(ax.figure, style.PLAIN(t)) * 72.0
        at_end = abs(t - right) <= 1e-9 * max(abs(right), 1.0)
        lo, hi = (x - w, x) if at_end else (x - w / 2, x + w / 2)
        if all(hi + gap_pt <= b_lo or b_hi + gap_pt <= lo for b_lo, b_hi in boxes):
            kept.append(t)
            boxes.append((lo, hi))
    kept = sorted(kept)
    ax.xaxis.set_major_locator(FixedLocator(kept))
    ax.xaxis.set_minor_locator(FixedLocator([t for t in ticks if t not in kept]))
    ax.xaxis.set_minor_formatter(NullFormatter())
    style.end_label_inside(ax)
    return kept


Z_LABEL_UNDER_BAND = style.Z_THEORY + 0.1      # the CR* label: above its curve, below bands (Z_DATA - 0.02), medians
H_PAD_LIN = 0.08                # x margin left of H = 0 (linear part of the symlog axis), in minutes
H_PAD_LOG = 1.2                 # x margin right of the largest H, as a factor


def h_axis(ax, h_values_: Sequence[float], *, gap_pt: float = 5.0) -> None:
    """Symlog notice axis (min) over the H grid with a small margin at both ends, so that markers at the first and
    last H (0 and 240 min) are not cut by the axes edge; tick labels thinned to fit (thin_x_ticks, gap_pt)."""
    lo, hi = min(h_values_), max(h_values_)
    ticks = [t for t in style.H_TICKS_MIN if lo <= t <= hi]
    style.symlog_minutes(ax, "x", ticks=ticks)
    ax.set_xlim(lo - H_PAD_LIN if lo < 1.0 else lo / H_PAD_LOG, hi * H_PAD_LOG if hi > 1.0 else hi + H_PAD_LIN)
    thin_x_ticks(ax, ticks, gap_pt=gap_pt)


TICK_LADDERS = ((1.0, 2.0, 5.0, 10.0, 20.0, 50.0), (1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0),
                (1.0, 1.1, 1.2, 1.5, 2.0, 3.0, 5.0, 10.0), (1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 2.0, 2.5, 3.0))


def nice_log_ticks(lo: float, hi: float) -> list[float]:
    """Ticks of a log ratio axis on [lo, hi]: the coarsest ladder that gives at least three ticks, the highest in
    the top half of the range (in log)."""
    top = lo * (hi / lo) ** 0.5
    for ladder in TICK_LADDERS:
        ticks = [c for c in ladder if lo <= c <= hi]
        if len(ticks) >= 3 and ticks[-1] >= top:
            return ticks
    return ticks


def draw_vertical_labels(ax, vert: Mapping, labels: Mapping) -> None:
    """Reference verticals at H*_beta and H*_mu (thresholds, not bounds), labeled at the top inside the axes, each
    right of its line, or left of it where the next vertical to the right would run through the label (as built at
    9 pt: in sf_e2_mu_ep (a) H*_mu's line ran through the H of H*_beta's label) and the label fits there inside the
    axes, clear of the previous line and label; where it does not fit there, it stays right of its line and the
    crossing line ends 1 pt below it. The right label goes just below the left one (by the left label's measured
    height, which the star and the subscript make taller than a text line) where the two would still touch."""
    items = sorted(((vert[k], labels[lk]) for k, lk in (("H_star_beta_min", "H_star_beta"),
                                                          ("H_star_mu_min", "H_star_mu"))), key=lambda t: t[0])
    to_pt = 72.0 / ax.figure.dpi
    renderer = ax.figure.canvas.get_renderer()
    bb_ax = ax.get_window_extent(renderer)
    xs_pt = [ax.transData.transform((x, 1.0))[0] * to_pt for x, _ in items]
    prev, dy, prev_h, ymax = None, -1.5, 0.0, 1.0       # prev: (left, right) of the previous label, points
    for k, ((x, lab), x_pt) in enumerate(zip(items, xs_pt)):
        style.reference_line(ax, x=x, ymax=ymax)
        w = text_width_in(ax.figure, lab) * 72.0
        crossed = k + 1 < len(items) and xs_pt[k + 1] <= x_pt + 1.5 + w + 1.0
        lo = x_pt - 1.5 - w
        left = crossed and lo >= bb_ax.x0 * to_pt + 1.0 and all(not (lo - 1.0 <= v <= x_pt) for v in xs_pt[:k]) \
            and (prev is None or prev[1] + 1.0 <= lo)
        span = (lo, x_pt - 1.5) if left else (x_pt + 1.5, x_pt + 1.5 + w)
        if prev is not None and span[0] < prev[1] + 1.0:
            dy -= prev_h + 1.0
        t = ax.annotate(lab, xy=(x, 1.0), xycoords=("data", "axes fraction"), xytext=(-1.5 if left else 1.5, dy),
                        textcoords="offset points", ha="right" if left else "left", va="top",
                        fontsize=style.TICK_PT, color=style.THEORY_LABEL_GREY)
        t._sublet_role = "reference_label"
        bb = t.get_window_extent(renderer)
        ymax = (bb.y0 - bb_ax.y0 - 1.0 / to_pt) / bb_ax.height if crossed and not left else 1.0
        prev_h = bb.height * to_pt
        prev = span


def median_overlap(block: Mapping, rules: Sequence[str], ref: str = "a1") -> dict:
    """{rule: {group: {n, max_rel_gap, at_H_min}}}: the largest |median / ref median - 1| over the H where both rules
    have a median, per lender group (the caption names the series that the panel draws on top of each other)."""
    out: dict = {}
    for rule in rules:
        if rule == ref:
            continue
        for g in GROUPS:
            r, s = block[ref].get(g), block[rule].get(g)
            if not r or not s:
                continue
            pairs = [(h, v / u - 1.0) for h, u, v in zip(r["H_min"], r["median"], s["median"])
                     if u is not None and v is not None and u > 0]
            i = max(range(len(pairs)), key=lambda j: abs(pairs[j][1])) if pairs else None
            out.setdefault(rule, {})[g] = {"n": len(pairs),
                                           "max_rel_gap": None if i is None else abs(pairs[i][1]),
                                           "at_H_min": None if i is None else pairs[i][0]}
    return out


def cr_label_end(ax, block: Mapping, rules: Sequence[str], hx: Sequence[float], hy: Sequence[float],
                 label: str, *, avoid_x: Sequence[float] = (),
                 avoid_lines: Sequence[tuple] = ()) -> tuple[float, float, str, str]:
    """Where the exact CR* curve's label goes (as built: at the curve's last point the label covered the steep MaaS
    segments from 120 to 240 min): (x, y, side, text), the label right-aligned at the curve's point (x, y), above it
    (theory_line's "inside") or, with side "below", under it. The point is the rightmost one of the curve, sampled
    every half point (pt) from its last point leftwards, where the label's box stays inside the axes and covers no
    median line or marker of the panel and no part of the curve itself; tried above the curve, then below it, with
    the label on one line, then on two (broken after its comma), then with its first line broken again at its
    first space (three lines for a label with a comma; as built at 9 pt, sf_e2_mu_ep (c) with H*_mu at the core
    game's threshold: the two-line label did not fit between H*_mu's line and the medians rising from 120 to 240 min,
    and H*_mu's line ran into it)); all of that first clear of the reference verticals at `avoid_x` (H*_beta,
    H*_mu: the label's halo would cut them), then across them; the last point, above, one line, if no position is free. Needs the final x and y scales.
    `avoid_lines` (C62, supplementary panels; empty by default, as Fig. 7 draws): further polylines (x, y) in data
    coordinates that the label's box covers no part of, as the medians (the edges of the P95 bands)."""
    to_pt = 72.0 / ax.figure.dpi
    pad = 2.5

    def dense(P):                         # a polyline in points, sampled about every 0.5 pt
        out = [P[:1]]
        for p0, p1 in zip(P[:-1], P[1:]):
            n = max(2, int(np.hypot(*(p1 - p0)) / 0.5) + 1)
            out.append(p0 + np.linspace(0.0, 1.0, n)[1:, None] * (p1 - p0))
        return np.vstack(out)

    def polyline(x, y):
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        ok = np.isfinite(x) & np.isfinite(y)
        return dense(ax.transData.transform(np.column_stack([x[ok], y[ok]])) * to_pt) if ok.any() else None

    data = [polyline(finite(s["H_min"]), finite(s["median"]))
            for rule in rules for g in GROUPS if (s := block[rule].get(g))]
    data += [polyline(finite(x), finite(y)) for x, y in avoid_lines]
    data = np.vstack([d for d in data if d is not None] or [np.empty((0, 2))])
    curve = polyline(hx, hy)
    left = ax.transAxes.transform((0.0, 0.0))[0] * to_pt
    bottom = ax.transAxes.transform((0.0, 0.0))[1] * to_pt
    vx = [ax.transData.transform((v, 1.0))[0] * to_pt for v in avoid_x]

    def hits(P, xr, lo, hi, xpad):
        return ((P[:, 0] >= xr - w - xpad) & (P[:, 0] <= xr + xpad) & (P[:, 1] >= lo) & (P[:, 1] <= hi)).any()

    texts = [label] + ([label.replace(", ", ",\n", 1)] if ", " in label else [])
    if " " in texts[-1].split("\n", 1)[0]:
        texts.append(texts[-1].replace(" ", "\n", 1))
    for verts, text, side in ((vs, tx, sd) for vs in (vx, []) for tx in texts for sd in ("above", "below")):
        w = text_width_in(ax.figure, text) * 72.0
        h = style.TICK_PT * 1.25 * (text.count("\n") + 1)
        for xr, y0 in curve[np.argsort(-curve[:, 0])]:
            if xr - w < left + 1.0:
                break
            if any(xr - w - pad <= v <= xr + pad for v in verts):
                continue
            if side == "above":           # the box from 1.5 pt above the curve; the curve may run under it
                lo, hi = y0 + 1.5, y0 + 1.5 + h
                clear = not hits(data, xr, lo - pad, hi + pad, pad) and not hits(curve, xr, lo - 0.5, hi + pad, 0.0)
            else:                         # the box down from 1.5 pt below the curve; the curve may run above it
                lo, hi = y0 - 1.5 - h, y0 - 1.5
                clear = (lo - pad >= bottom and not hits(data, xr, lo - pad, hi + pad, pad)
                         and not hits(curve, xr, lo - pad, hi + 0.5, 0.0))
            if clear:
                x, y = ax.transData.inverted().transform((xr / to_pt, y0 / to_pt))
                return float(x), float(y), side, text
    return float(hx[-1]), float(hy[-1]), "above", label


# (a): A1's medians and those of the fixed rule and of BL6 can lie within a marker of each other (a.overlap); as
# built at 9 pt the pre-warm hexagon was hidden under A1's and BL6's X showed only as specks. The fixed rule (pre-warm
# or always cold) is drawn with a larger marker (about 6 pt; the pre-warm rule's is an open ring) behind ALG*, BL6's
# markers smaller with a dark edge on top of ALG* (its line stays under A1's), so that each of the three is seen
# where they coincide, in color and in greyscale; the legend glyphs are drawn the same way (episode_handles).
RING_PT = 6.0
EPISODE_MARKS = {"prewarm": {"markersize": RING_PT}, "cold": {"markersize": RING_PT},
                 "bl6": {"markersize": 2.8, "markeredgecolor": "#000000", "markeredgewidth": 0.5}}
MARKS_ON_TOP = ("bl6",)
Z_A1 = style.Z_DATA + 0.2
BAND_FILLED = ("maas",)          # A1's P95 band: MaaS filled, the other groups as an outline in their line style
Y_CLEAR_PT = 1.5                 # (a): least gap between the lowest marker and the bottom spine


def episode_handles(keys: Sequence[str]) -> list[tuple[Line2D, str]]:
    """Legend entries of the rules of panel (a) as drawn there (EPISODE_MARKS), in the order of §5."""
    out = []
    for k in style.legend_order(keys):
        kw = style.policy_kwargs(k)
        kw.update(EPISODE_MARKS.get(k, {}))
        out.append((Line2D([], [], **kw), kw["label"]))
    return out


def episode_range(block: Mapping, cr: Mapping, rules: Sequence[str], band_rules: Sequence[str] = ("a1",)):
    """(lo, hi) of the plotted per-episode values: medians, the P95 of the banded rules, the exact CR* line."""
    hy = list(cr["CR"]) + ([cr["extension"]["value"]] if cr.get("extension") else [])
    vals = [v for rule in rules for g in GROUPS if block[rule].get(g)
            for f in (("median", "p95") if rule in band_rules else ("median",))
            for v in block[rule][g][f] if v is not None] + hy
    return min(vals + [1.0]), max(vals)


def draw_episode_panel(ax, block: Mapping, cr: Mapping, vert: Mapping | None, labels: Mapping,
                       rules: Sequence[str], *, band_rules: Sequence[str] = ("a1",),
                       yrange: tuple[float, float] | None = None, h_gap_pt: float = 5.0,
                       cr_clear_bands: bool = False) -> None:
    """Medians (lines with markers) per rule and lender group, the median-to-P95 band of the rules in band_rules
    (A1: six overlapping bands at alpha 0.18 do not read; every P95 is in the extract; MaaS filled, the spot band
    as a dashed outline), the exact CR* line. ALG* is drawn above the other rules' lines and the fixed rule's ring,
    BL6's markers above ALG* (EPISODE_MARKS). `h_gap_pt`: the least gap between H tick labels (h_axis).
    `cr_clear_bands` (C62, sf_e2_mu_ep; off as Fig. 7 draws): the exact CR* label also clears the dashed outline of
    each unfilled band (cr_label_end's avoid_lines; as built at 7 pt, the one-line label ran across the spot band's
    outline in sf_e2_mu_ep (a) and (b)); the filled band's edge does not count, since the label lies under the band
    (Z_LABEL_UNDER_BAND) and no place below its P95 edge holds the label where the edge is low (5-10 min)."""
    xs_all = []
    for rule in rules:
        for g in GROUPS:
            s = block[rule].get(g)
            if not s:
                continue
            x, y, p = finite(s["H_min"]), finite(s["median"]), finite(s["p95"])
            xs_all += list(x)
            if not np.isfinite(y).any():
                continue
            ok = np.isfinite(y) & np.isfinite(p)
            if ok.any() and rule in band_rules:
                xb, lo_b, hi_b = (np.where(ok, v, np.nan) for v in (x, y, p))
                if g in BAND_FILLED:
                    style.band(ax, rule, xb, lo_b, hi_b)
                else:           # the same color and alpha twice read as a third band where they overlap
                    pol = style.policy(rule)
                    ax.fill_between(xb, lo_b, hi_b, facecolor="none", edgecolor=pol.color, alpha=0.6,
                                    linewidth=style.UNCERTAINTY_PT, linestyle=style.env_linestyle(*LENDER[g]),
                                    zorder=pol.zorder - 0.02, label="_nolegend_")
            marks = EPISODE_MARKS.get(rule, {})
            if rule in MARKS_ON_TOP:
                style.plot_policy(ax, rule, x, y, env=LENDER[g], markers=False)
                style.plot_policy(ax, rule, x, y, env=LENDER[g], lines=False, zorder=Z_A1 + 0.1,
                                  label="_nolegend_", **marks)
            else:
                style.plot_policy(ax, rule, x, y, env=LENDER[g], **marks,
                                  **({"zorder": Z_A1} if rule == "a1" else {}))
    h_axis(ax, [v for v in xs_all if np.isfinite(v)], gap_pt=h_gap_pt)
    lo, hi = yrange or episode_range(block, cr, rules, band_rules)
    style.log_axis(ax, "y", ticks=nice_log_ticks(lo, hi * 1.05))
    ax.yaxis.set_minor_locator(NullLocator())
    # the bottom below lo (1 or the lowest value) by the largest marker's radius and Y_CLEAR_PT, solved for the log
    # scale of the final limits (x = r D / (h - r), D the log span above lo, h the axes height; as built, lo / 1.03
    # left the spot series 1.5 pt above the spine); the radius is that of the largest marker any of `rules` uses,
    # drawn or not, so that the panels of one y range keep one scale
    mark_pt = [EPISODE_MARKS.get(q, {}).get("markersize", style.policy(q).markersize) for q in rules]
    r = max(mark_pt, default=style.MARKER_PT) / 2.0 + style.MARKER_EDGE_PT / 2.0 + Y_CLEAR_PT
    h = style.axes_rect_in(ax)[3] * 72.0
    ax.set_ylim(min(lo / 1.03, lo * math.exp(-r * math.log(hi * 1.10 / lo) / (h - r))), hi * 1.10)
    hx = cr["H_min"] + ([cr["extension"]["to_H_min"]] if cr.get("extension") else [])
    hy = cr["CR"] + ([cr["extension"]["value"]] if cr.get("extension") else [])
    # labeled above the continued curve where its box covers no median (cr_label_end), or just right of the last
    # grid point where the curve is not continued (its last point lies below H*_mu), so that the label stays inside
    # the axes; the labels are placed after the final scales, which their tests read. The A1 band fills the panel
    # from the medians to the P95 at every H, so the label cannot avoid it: it is drawn above the curve, the
    # reference lines and the grid but below the bands (Z_LABEL_UNDER_BAND), so that its white halo hides no part
    # of a band (as built at 9 pt, 2026-10-22: above the bands the halo cut a hole into A1's band and its P95 edge)
    edges = []
    if cr_clear_bands:                    # each outline band's whole outline: medians, P95 and the two ends
        for rule in band_rules:
            for g in GROUPS:
                s = block[rule].get(g) if rule in rules and g not in BAND_FILLED else None
                if not s:
                    continue
                x, y, p = finite(s["H_min"]), finite(s["median"]), finite(s["p95"])
                ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(p)
                if ok.any():
                    edges.append((np.r_[x[ok], x[ok][::-1], x[ok][:1]], np.r_[y[ok], p[ok][::-1], y[ok][:1]]))
    if cr.get("extension"):
        x, y, side, text = cr_label_end(ax, block, rules, hx, hy, labels["cr"],
                                        avoid_x=[] if vert is None else [vert["H_star_beta_min"],
                                                                         vert["H_star_mu_min"]],
                                        avoid_lines=edges)
        _, txt = style.theory_line(ax, hx, hy, "exact", text, where="inside", label_xy=(x, y))
        if side == "below":
            txt.set_verticalalignment("top")
            txt.xyann = (0.0, -1.5)
    else:
        _, txt = style.theory_line(ax, hx, hy, "exact", labels["cr"], where="right")
    txt.set_zorder(Z_LABEL_UNDER_BAND)
    if vert is not None:
        draw_vertical_labels(ax, vert, labels)
    style.ygrid(ax)
    ax.set_xlabel(labels["H"])
    ax.set_ylabel(labels["a_y"])


# ---------------------------------------------------------------------------------------------------------------
# (b) total cost over BL0a
def totals_block(e2: Mapping, mu, *, rule: str = "a1", sched: str = "trace", field: str = "cost_over_bl0a",
                 groups: Sequence[str] = GROUPS, alignment=None, minimizer: bool = True) -> dict:
    """{group: {H_min, median, ci_lo, ci_hi}} from totals.<group>.<H>.<mu>.<sched>.<rule>.<field> (or its
    by_alignment.<c> value), and the minimizers best_H.<group>.<mu>.<sched>.<rule>."""
    tot = need(e2, "totals", what=E2)
    out = {}
    for g in groups:
        s = {"H_min": [], "median": [], "ci_lo": [], "ci_hi": [], "note": []}
        for H, hk, _ in num_items(need(tot, g, what=f"{E2} totals")):
            path = (g, hk, mu, sched, rule) + (("by_alignment", alignment) if alignment is not None else ()) + (field,)
            ent, note = maybe(tot, *path)
            if isinstance(ent, Mapping) and ent.get("median") is None:      # null fields with a note (M23)
                note = ent.get("note") or ent.get("median_note") or "null"
            lo, hi = (ent.get("median_ci95") or [None, None]) if ent else (None, None)
            for f, v in zip(s, (H, ent.get("median") if ent else None, lo, hi, note)):
                s[f].append(v)
        out[g] = s
    if minimizer:
        out["minimizer"] = {}
        for g in groups:
            bh, note = maybe(e2, "best_H", g, mu, sched, rule)
            bh = bh if isinstance(bh, Mapping) else {}
            h, val = bh.get("H"), bh.get("cost_over_bl0a")          # minutes and the median (numbers, e2.py)
            if h is None or val is None:          # no H with a value: null with the summary's note (§2.6)
                out["minimizer"][g] = {"H_min": None, "value": None, "note": bh.get("note") or note or "null"}
            else:
                out["minimizer"][g] = {"H_min": float(h), "value": float(val)}
    return out


def draw_totals_panel(ax, block: Mapping, labels: Mapping, *, key: str = "a1", h_gap_pt: float = 5.0) -> None:
    """Medians per lender group (line style) with their bootstrap bars, a marker at each group's minimizing H, and the
    level 1 (all-fallback) as a reference line; `h_gap_pt`: the least gap between H tick labels (h_axis)."""
    xs, vals = [], [1.0]
    for g in GROUPS:
        s = block[g]
        x, y, lo, hi = finite(s["H_min"]), finite(s["median"]), finite(s["ci_lo"]), finite(s["ci_hi"])
        style.plot_policy(ax, key, x, y, env=LENDER[g], markers=False)
        ok = np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi)
        if ok.any():
            style.errorbars(ax, key, x[ok], y[ok], lo[ok], hi[ok])
        xs += list(x)
        vals += [v for v in np.concatenate([y, lo, hi]) if np.isfinite(v)]
    for g in GROUPS:
        mn = block.get("minimizer", {}).get(g)
        if mn and mn.get("H_min") is not None and mn.get("value") is not None:
            style.scatter_policy(ax, key, [mn["H_min"]], [mn["value"]], label="_nolegend_")
    style.reference_line(ax, y=1.0)
    h_axis(ax, xs, gap_pt=h_gap_pt)
    lo, hi = min(vals), max(vals)
    pad = 0.06 * (hi - lo)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlabel(labels["H"])
    ax.set_ylabel(labels["b_y"])


# ---------------------------------------------------------------------------------------------------------------
# (c) the protection heatmap
def h_edges(hs: Sequence[float], linthresh: float = 1.0) -> list[float]:
    """Cell edges on the symlog H axis: midpoints in the linear part (H <= linthresh), geometric means above it,
    outer edges mirrored (§8.6: -0.5, 0.5, sqrt 2, sqrt 10, ..., 240 sqrt 2)."""
    hs = [float(h) for h in hs]
    inner = [0.5 * (a + b) if a < linthresh else math.sqrt(a * b) for a, b in zip(hs, hs[1:])]
    first = hs[0] - (inner[0] - hs[0])
    last = hs[-1] * hs[-1] / inner[-1] if hs[-2] >= linthresh else hs[-1] + (hs[-1] - inner[-1])
    return [first] + inner + [last]


def r_edges(rs: Sequence[float]) -> list[float]:
    """Geometric means of neighboring rows, outer edges by the same ratio (§8.6)."""
    rs = [float(r) for r in rs]
    inner = [math.sqrt(a * b) for a, b in zip(rs, rs[1:])]
    return [rs[0] * rs[0] / inner[0]] + inner + [rs[-1] * rs[-1] / inner[-1]]


def ratio_contour(values: Sequence[Sequence], x_edges: Sequence[float], y_edges: Sequence[float],
                  level: float = CONTOUR_LEVEL, tol: float = CONTOUR_TOL) -> dict:
    """The step line at `level` of a heatmap (rows by r, columns by H; None where a cell is missing): the cell edges
    that separate a cell with value below level x (1 - tol) from a neighbor that is not, edges to a missing cell
    skipped, chained into polylines that break at a crossing of four edges, with the corners of straight runs
    dropped. Returns {level, tol, lines: [{H_min, r}]} in data coordinates (the cell edges), for the extract. In
    greyscale PuOr prints both signs of a ratio as mid grey; the line shows where the ratio crosses 1.
    A value within the relative `tol` below the level counts as the level (2026-10-22:
    as built with a tolerance of 1e-9, the line outlined cells of 0.9987-0.99997 in sf_e6a, which are
    1 within rounding, as heavily as the real boundary)."""
    nr, nc = len(values), len(values[0]) if values else 0
    cut = level * (1.0 - tol)
    below = [[None if values[i][j] is None else float(values[i][j]) < cut for j in range(nc)] for i in range(nr)]
    segs = []                                       # nodes are (column edge, row edge) indices
    for i in range(nr):
        for j in range(nc):
            if below[i][j] is None:
                continue
            if j + 1 < nc and below[i][j + 1] is not None and below[i][j + 1] != below[i][j]:
                segs.append(((j + 1, i), (j + 1, i + 1)))
            if i + 1 < nr and below[i + 1][j] is not None and below[i + 1][j] != below[i][j]:
                segs.append(((j, i + 1), (j + 1, i + 1)))
    adj: dict = {}
    for k, (a, b) in enumerate(segs):
        adj.setdefault(a, []).append(k)
        adj.setdefault(b, []).append(k)
    used, chains = set(), []
    for start in sorted(adj, key=lambda n: (len(adj[n]) == 2, n)):   # line ends and crossings first, then loops
        for k in adj[start]:
            if k in used:
                continue
            path, node = [start], start
            while k is not None:
                used.add(k)
                a, b = segs[k]
                node = b if a == node else a
                path.append(node)
                if len(adj[node]) != 2:
                    break
                k = next((q for q in adj[node] if q not in used), None)
            chains.append([p for n, p in enumerate(path) if n in (0, len(path) - 1)
                           or (path[n - 1][0] == p[0]) != (p[0] == path[n + 1][0])])   # keep the corners only
    return {"level": float(level), "tol": float(tol),
            "lines": [{"H_min": [float(x_edges[c]) for c, _ in ch], "r": [float(y_edges[r]) for _, r in ch]}
                      for ch in chains]}


def heat_block(heat: Mapping, bnd: Mapping, group: str, lamp: str, mu) -> dict:
    """Cell values, intervals and counts of heatmap.json cells.<group>.<lam'>.<mu>.<H>.<r> (rows by r, null where a
    cell is missing) and the boundary rows.<mu>.<lam'>.<group> (H_min, r_star, r_star_grid)."""
    block = need(heat, "cells", group, lamp, mu, what=HEAT)
    hs = num_items(block)
    rows = sorted({x for _, _, cells in hs if isinstance(cells, Mapping) for x, _, _ in num_items(cells)})
    vals = [[None] * len(hs) for _ in rows]
    ci = [[None] * len(hs) for _ in rows]
    n_pairs = [[None] * len(hs) for _ in rows]
    share = [[None] * len(hs) for _ in rows]
    notes = {}
    for j, (H, hk, cells) in enumerate(hs):
        if not isinstance(cells, Mapping):
            notes[hk] = block.get(hk + "_note") or "null"
            continue
        by_r = {x: v for x, _, v in num_items(cells)}
        for i, r in enumerate(rows):
            c = by_r.get(r)
            if isinstance(c, Mapping):
                vals[i][j], ci[i][j] = c.get("value"), c.get("ci95")
                n_pairs[i][j], share[i][j] = c.get("n_pairs"), c.get("share_insured")
                if c.get("value") is None and (c.get("note") or c.get("value_note")):
                    notes.setdefault(hk, c.get("note") or c.get("value_note"))
    # a group whose boundary job has no 'ok' output is null with a note (e6.py); the panel then has no line
    b_rows, b_note = maybe(bnd, "rows", mu, lamp, group)
    brows = boundary_records(b_rows) if b_rows is not None else []
    boundary = {"H_min": [float(r["H_min"]) for r in brows], "r_star": [r.get("r_star") for r in brows],
                "r_star_grid": [r.get("r_star_grid") for r in brows]}
    if b_rows is None:
        boundary["note"] = f"{BOUND} rows.{format(float(mu), 'g')}.{lamp}.{group}: {b_note}"
    present = [v for row in vals for v in row if v is not None]
    vmax = max([max(v, 1.0 / v) for v in present if v > 0] + [1.0 + 1e-6])
    xe, ye = h_edges([h for h, _, _ in hs]), r_edges(rows)
    return {"H_min": [h for h, _, _ in hs], "rows": rows, "x_edges": xe, "y_edges": ye, "values": vals, "ci": ci,
            "n_pairs": n_pairs, "share_insured": share, "vmin": 1.0 / vmax, "vmax": vmax, "notes": notes,
            "boundary": boundary, "contour": ratio_contour(vals, xe, ye), "group": group, "lam": lamp,
            "mu": float(mu)}


def boundary_records(rows: Any) -> list[dict]:
    """boundary.json rows.<mu>.<lam'>.<group> as records sorted by H_min; e6.py writes parallel column lists over
    the H with a value (H, H_min, r_star, r_star_grid, ...) beside H_skipped (§7.1)."""
    if not (isinstance(rows, Mapping) and isinstance(rows.get("H_min"), list)):
        raise MissingKey(f"{BOUND}: a boundary entry is {type(rows).__name__} without an H_min column (§7.1)")
    cols = {k: v for k, v in rows.items() if isinstance(v, list) and len(v) == len(rows["H_min"])}
    recs = [{k: cols[k][i] for k in cols} for i in range(len(rows["H_min"]))]
    recs = [r for r in recs if r.get("H_min") is not None]
    return sorted(recs, key=lambda r: float(r["H_min"]))


def colorbar_ticks(vmin: float, vmax: float) -> list[float]:
    pairs = [(a, b) for a, b in zip(RATIO_TICKS, RATIO_TICKS[::-1]) if a < 1.0]
    for a, b in pairs:
        if vmin <= a * 1.0001 and b <= vmax * 1.0001:
            return [a, 1.0, b]
    return [1.0]


def row_ticks(ax, rows: Sequence[float], min_sep_pt: float = style.TICK_PT) -> list[float]:
    """Row values as y ticks whose labels are at least min_sep_pt apart (one font size, style.TICK_PT: digits with a
    cap height of about 0.72 em keep a gap of about 0.28 em, 2.0 pt at 7 pt; 9.0 at 9 pt, 2026-10-22 to C62), chosen
    in the order: the bottom and top rows, then the rows with the fewest decimals (2, 3, then 1.5, 2.5, then 1.25,
    ...), each from the bottom, kept if it clears the rows kept so far; the others become minor ticks."""
    to_pt = 72.0 / ax.figure.dpi
    rows = sorted(float(r) for r in rows)

    def decimals(r: float) -> int:
        return len(f"{r:g}".partition(".")[2])

    order = rows[:1] + rows[-1:] + sorted(rows[1:-1], key=lambda r: (decimals(r), r))
    kept, ys = [], []
    for r in order:
        y = ax.transData.transform((0, r))[1] * to_pt
        if r not in kept and all(abs(y - v) >= min_sep_pt for v in ys):
            kept.append(r)
            ys.append(y)
    return sorted(kept)


def _dense(P: np.ndarray, step: float = 0.5) -> np.ndarray:
    """A polyline in points sampled about every `step` points."""
    out = [P[:1]]
    for p0, p1 in zip(P[:-1], P[1:]):
        n = max(2, int(np.hypot(*(p1 - p0)) / step) + 1)
        out.append(p0 + np.linspace(0.0, 1.0, n)[1:, None] * (p1 - p0))
    return np.vstack(out)


def _luminance(rgb) -> float:
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrasts(colors) -> tuple[float, float]:
    """The least contrast, (L1 + 0.05) / (L2 + 0.05) (WCAG), of black and of white text against the `colors`, each
    taken in color (its relative luminance) and as a greyscale print shows it (its luma 0.299 R + 0.587 G + 0.114 B
    as a grey)."""
    lums = []
    for c in colors:
        rgb = to_rgb(c)
        y = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        lums += [_luminance(rgb), _luminance((y, y, y))]
    return min((v + 0.05) / 0.05 for v in lums), min(1.05 / (v + 0.05) for v in lums)


def text_on(colors) -> str:
    """'black' or 'white', whichever has the larger least contrast against the `colors` (_contrasts: in color and as
    a greyscale print shows them)."""
    black, white = _contrasts(colors)
    return "black" if black >= white else "white"


SIGN_PAD_PT = 1.0               # least gap from a sign cue's ink to a cell of the other side (the step line)
SIGN_EDGE_PT = 2.5              # least gap from its ink to the outer cell edges, the spines (at 1 pt, "< 1" beside
#                                 the y axis read as a neighbor of the tick labels)
SIGN_LINE_PT = 4.5              # least gap from its ink to a line, half an em (at 2.5 pt, "< 1" before the boundary's
#                                 end in sf_e6a (b) read as a label of it)
SIGN_STEP_PT = 1.0              # grid of the positions tried


def sign_cues(ax, block: Mapping, cmap, norm, labels: Mapping, *, avoid: Sequence = ()) -> list:
    """A 7-pt (TICK_PT) "< 1" (labels "below") in the region of cells below the step line's cut (level x (1 - tol))
    and "> 1" ("above") in the region of cells above 1, each only where the data have such cells: in greyscale PuOr
    prints both ends as dark grey, so the step line alone does not tell which side is below 1 (2026-10-22;
    sf_e6a; Fig. 7 takes region_cues since C62). Each sits where its ink box, padded by
    SIGN_PAD_PT, covers only cells of its side, clears the lines in `avoid` (the boundary and its halo, their width
    included) by SIGN_LINE_PT and the layout boxes of the texts there (the boundary's label) by SIGN_PAD_PT: of the
    positions on a SIGN_STEP_PT grid with the ink at least SIGN_EDGE_PT inside the outer cell edges, the one whose
    least |log ratio| over the cells it covers is largest (its most extreme region that holds the text), then the
    nearest to the center of the most extreme cell it covers; in black or white, whichever contrasts more with the
    cells it covers, in color and in greyscale (text_on). Needs the final scales; returns the texts."""
    fig = ax.figure
    to_pt = 72.0 / fig.dpi
    rend = fig.canvas.get_renderer()
    vals = np.array([[np.nan if v is None else float(v) for v in row] for row in block["values"]], dtype=float)
    xs, ys = np.asarray(block["x_edges"], dtype=float), np.asarray(block["y_edges"], dtype=float)
    xe = ax.transData.transform(np.column_stack([xs, np.full(xs.size, ys[0])]))[:, 0] * to_pt
    ye = ax.transData.transform(np.column_stack([np.full(ys.size, xs[0]), ys]))[:, 1] * to_pt
    pts, clear, boxes = [np.empty((0, 2))], [np.empty(0)], []
    for a in avoid:
        if isinstance(a, Line2D):
            P = ax.transData.transform(np.column_stack([a.get_xdata(), a.get_ydata()]).astype(float)) * to_pt
            P = P[np.isfinite(P).all(axis=1)]
            if len(P):
                P = _dense(P)
                pts.append(P)
                clear.append(np.full(len(P), a.get_linewidth() / 2.0))
        else:
            bb = a.get_window_extent(rend)
            boxes.append((bb.x0 * to_pt, bb.y0 * to_pt, bb.x1 * to_pt, bb.y1 * to_pt))
    pts, clear = np.vstack(pts), np.concatenate(clear)
    level, tol = block["contour"]["level"], block["contour"].get("tol", 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        sides = (("below", vals < level * (1.0 - tol)), ("above", vals > level * (1.0 + 1e-9)))
        absl = np.abs(np.log(vals))
    out = []
    for key, side in sides:
        side = side & np.isfinite(vals)
        if not side.any():
            continue
        text = labels[key]
        ink = TextPath((0, 0), text, size=style.TICK_PT, prop=FontProperties(family=style.FONT_FAMILY)).get_extents()
        probe = ax.annotate(text, xy=(0.5, 0.5), xycoords="axes fraction", ha="left", va="baseline",
                            fontsize=style.TICK_PT)
        bb, (ax0, ay0) = probe.get_window_extent(rend), ax.transAxes.transform((0.5, 0.5))
        lay = ((bb.x0 - ax0) * to_pt, (bb.y0 - ay0) * to_pt, (bb.x1 - ax0) * to_pt, (bb.y1 - ay0) * to_pt)
        probe.remove()
        ic = ((ink.x0 + ink.x1) / 2.0, (ink.y0 + ink.y1) / 2.0)       # ink center from the baseline-left anchor
        hw, hh = ink.width / 2.0 + SIGN_PAD_PT, ink.height / 2.0 + SIGN_PAD_PT
        best = None                                                   # (score, -distance, cx, cy, cells)
        mx, my = hw + SIGN_EDGE_PT - SIGN_PAD_PT, hh + SIGN_EDGE_PT - SIGN_PAD_PT
        for cx in np.arange(xe[0] + mx, xe[-1] - mx + 1e-9, SIGN_STEP_PT):
            j0, j1 = np.searchsorted(xe, cx - hw, "right") - 1, np.searchsorted(xe, cx + hw, "left") - 1
            for cy in np.arange(ye[0] + my, ye[-1] - my + 1e-9, SIGN_STEP_PT):
                i0, i1 = np.searchsorted(ye, cy - hh, "right") - 1, np.searchsorted(ye, cy + hh, "left") - 1
                if not side[i0:i1 + 1, j0:j1 + 1].all():
                    continue
                sub = absl[i0:i1 + 1, j0:j1 + 1]
                score = round(float(sub.min()), 9)
                if best is not None and score < best[0]:
                    continue
                i, j = np.unravel_index(int(np.argmax(sub)), sub.shape)
                dist = math.hypot(cx - (xe[j0 + j] + xe[j0 + j + 1]) / 2.0, cy - (ye[i0 + i] + ye[i0 + i + 1]) / 2.0)
                if best is not None and (score, -dist) <= best[:2]:
                    continue
                near = clear + SIGN_LINE_PT
                if ((np.abs(pts[:, 0] - cx) <= hw - SIGN_PAD_PT + near)
                        & (np.abs(pts[:, 1] - cy) <= hh - SIGN_PAD_PT + near)).any():
                    continue
                lx, ly = cx - ic[0], cy - ic[1]                         # the text's anchor
                if any(lx + lay[0] < b[2] + SIGN_PAD_PT and b[0] - SIGN_PAD_PT < lx + lay[2]
                       and ly + lay[1] < b[3] + SIGN_PAD_PT and b[1] - SIGN_PAD_PT < ly + lay[3] for b in boxes):
                    continue
                best = (score, -dist, cx, cy, (i0, i1, j0, j1))
        if best is None:
            continue
        _, _, cx, cy, (i0, i1, j0, j1) = best
        colors = [cmap(norm(v)) for v in vals[i0:i1 + 1, j0:j1 + 1].ravel()]
        x, y = ax.transData.inverted().transform(((cx - ic[0]) / to_pt, (cy - ic[1]) / to_pt))
        t = ax.text(x, y, text, ha="left", va="baseline", fontsize=style.TICK_PT, color=text_on(colors),
                    zorder=Z_CONTOUR + 0.1)
        t._sublet_role = "sign_cue"
        out.append(t)
    return out


# C62, Fig. 7(c) (region_cues): each cue where its region has the most room. As built with sign_cues at 7 pt, "< 1"
# went to the most extreme cell, the top left one under the boundary's start, whose row is 7 pt high (1 pt from the
# step line above and below it), and "> 1" to the bottom right corner cell; the cells of ratio 1 (more than a third of
# the panel) had no cue. CUE_ROOM_PT was 6 pt until the boundary's halo was thinned to HEAT_HALO_PT; then "< 1" found
# 6 pt next to the boundary's start, in the top left corner between the y axis and the line, and moved there again
CUE_ROOM_PT = 8.0               # clearance (pt) beyond which more room does not count before the colors do
CUE_CONTRAST = 4.5              # least contrast of a cue with every cell it covers, in color and greyscale (WCAG AA)
CUE_STEP_PT = 0.5               # grid of the positions tried (pt)


def region_cues(ax, block: Mapping, cmap, norm, labels: Mapping, *, avoid: Sequence = ()) -> list:
    """Fig. 7(c) (C62): a 7-pt "< 1" (labels "below") in the region of cells below the step line's cut (level x
    (1 - tol)), "> 1" ("above") in the region of cells above the level and "= 1" (the level, style.PLAIN) in the
    region of the other cells, where revocable-only leasing and ALG* cost the same (ALG* does not insure there), each
    only where the data have such cells. Of the positions on a CUE_STEP_PT grid whose ink box clears the cells of the
    other regions by SIGN_PAD_PT, the outer cell edges by SIGN_EDGE_PT, the lines in `avoid` (their width included)
    by SIGN_LINE_PT and the layout boxes of the texts there by SIGN_PAD_PT, the cue takes: one where black or white
    text has a contrast of at least CUE_CONTRAST with every cell that the ink box, padded by SIGN_PAD_PT, covers, in
    color and in greyscale (_contrasts), if there is one; then the most room (the least of those three clearances,
    counted up to CUE_ROOM_PT in steps of 0.5 pt); then the strongest colors (the largest least |log ratio| over the
    cells it covers); then the most room. In black or white, whichever contrasts more. Needs the final scales;
    returns the texts."""
    fig = ax.figure
    to_pt = 72.0 / fig.dpi
    rend = fig.canvas.get_renderer()
    vals = np.array([[np.nan if v is None else float(v) for v in row] for row in block["values"]], dtype=float)
    xs, ys = np.asarray(block["x_edges"], dtype=float), np.asarray(block["y_edges"], dtype=float)
    xe = ax.transData.transform(np.column_stack([xs, np.full(xs.size, ys[0])]))[:, 0] * to_pt
    ye = ax.transData.transform(np.column_stack([np.full(ys.size, xs[0]), ys]))[:, 1] * to_pt
    pts, half, boxes = [np.empty((0, 2))], [np.empty(0)], []
    for a in avoid:
        if isinstance(a, Line2D):
            P = ax.transData.transform(np.column_stack([a.get_xdata(), a.get_ydata()]).astype(float)) * to_pt
            P = P[np.isfinite(P).all(axis=1)]
            if len(P):
                P = _dense(P)
                pts.append(P)
                half.append(np.full(len(P), a.get_linewidth() / 2.0))
        else:
            bb = a.get_window_extent(rend)
            boxes.append((bb.x0 * to_pt, bb.y0 * to_pt, bb.x1 * to_pt, bb.y1 * to_pt))
    pts, half = np.vstack(pts), np.concatenate(half)
    level, tol = block["contour"]["level"], block["contour"].get("tol", 0.0)
    ok_v = np.isfinite(vals)
    with np.errstate(invalid="ignore", divide="ignore"):
        below = ok_v & (vals < level * (1.0 - tol))
        above = ok_v & (vals > level * (1.0 + 1e-9))
        absl = np.abs(np.log(vals))
    equal = ok_v & ~below & ~above
    con = np.full(vals.shape + (2,), np.nan)                  # per cell: least contrast of black, of white text
    for i, j in zip(*np.nonzero(ok_v)):
        con[i, j] = _contrasts([cmap(norm(vals[i, j]))])
    out = []
    for text, side in ((labels["below"], below), (f"= {style.PLAIN(level)}", equal), (labels["above"], above)):
        if not side.any():
            continue
        ink = TextPath((0, 0), text, size=style.TICK_PT, prop=FontProperties(family=style.FONT_FAMILY)).get_extents()
        probe = ax.annotate(text, xy=(0.5, 0.5), xycoords="axes fraction", ha="left", va="baseline",
                            fontsize=style.TICK_PT)
        bb, (ax0, ay0) = probe.get_window_extent(rend), ax.transAxes.transform((0.5, 0.5))
        lay = ((bb.x0 - ax0) * to_pt, (bb.y0 - ay0) * to_pt, (bb.x1 - ax0) * to_pt, (bb.y1 - ay0) * to_pt)
        probe.remove()
        ic = ((ink.x0 + ink.x1) / 2.0, (ink.y0 + ink.y1) / 2.0)       # ink center from the baseline-left anchor
        hw, hh = ink.width / 2.0, ink.height / 2.0
        cx = np.arange(xe[0] + hw + SIGN_EDGE_PT, xe[-1] - hw - SIGN_EDGE_PT + 1e-9, CUE_STEP_PT)
        cy = np.arange(ye[0] + hh + SIGN_EDGE_PT, ye[-1] - hh - SIGN_EDGE_PT + 1e-9, CUE_STEP_PT)
        if not (cx.size and cy.size):
            continue
        CX, CY = (v.ravel() for v in np.meshgrid(cx, cy))
        x0, x1, y0, y1 = CX - hw, CX + hw, CY - hh, CY + hh
        d_edge = np.minimum.reduce([x0 - xe[0], xe[-1] - x1, y0 - ye[0], ye[-1] - y1])
        d_cell, ext = np.full(CX.size, np.inf), np.full(CX.size, np.inf)
        c_black, c_white = np.full(CX.size, np.inf), np.full(CX.size, np.inf)
        p = SIGN_PAD_PT
        for i, j in np.ndindex(side.shape):
            if side[i, j]:
                cov = (x0 - p < xe[j + 1]) & (x1 + p > xe[j]) & (y0 - p < ye[i + 1]) & (y1 + p > ye[i])
                ext[cov] = np.minimum(ext[cov], absl[i, j])
                c_black[cov] = np.minimum(c_black[cov], con[i, j, 0])
                c_white[cov] = np.minimum(c_white[cov], con[i, j, 1])
            else:
                dx = np.maximum(np.maximum(xe[j] - x1, x0 - xe[j + 1]), 0.0)
                dy = np.maximum(np.maximum(ye[i] - y1, y0 - ye[i + 1]), 0.0)
                d_cell = np.minimum(d_cell, np.hypot(dx, dy))
        d_line = np.full(CX.size, np.inf)
        for k0 in (range(0, CX.size, 2048) if len(pts) else ()):
            sl = slice(k0, k0 + 2048)
            dx = np.maximum(np.abs(pts[None, :, 0] - CX[sl, None]) - hw, 0.0)
            dy = np.maximum(np.abs(pts[None, :, 1] - CY[sl, None]) - hh, 0.0)
            d_line[sl] = (np.hypot(dx, dy) - half[None, :]).min(axis=1)
        d_text = np.full(CX.size, np.inf)
        lx, ly = CX - ic[0], CY - ic[1]                                 # the text's anchor
        for b in boxes:
            dx = np.maximum(np.maximum(b[0] - (lx + lay[2]), (lx + lay[0]) - b[2]), 0.0)
            dy = np.maximum(np.maximum(b[1] - (ly + lay[3]), (ly + lay[1]) - b[3]), 0.0)
            d_text = np.minimum(d_text, np.hypot(dx, dy))
        ok = (d_edge >= SIGN_EDGE_PT) & (d_cell >= SIGN_PAD_PT) & (d_line >= SIGN_LINE_PT) & (d_text >= SIGN_PAD_PT)
        if not ok.any():
            continue
        cand = np.flatnonzero(ok)
        room = np.minimum.reduce([d_edge, d_cell, d_line])[cand]
        contrast = np.maximum(c_black, c_white)[cand]
        k = cand[np.lexsort((room, np.round(ext[cand], 9), np.floor(np.minimum(room, CUE_ROOM_PT) / 0.5),
                             contrast >= CUE_CONTRAST))[-1]]
        x, y = ax.transData.inverted().transform((lx[k] / to_pt, ly[k] / to_pt))
        t = ax.text(x, y, text, ha="left", va="baseline", fontsize=style.TICK_PT,
                    color="black" if c_black[k] >= c_white[k] else "white", zorder=Z_CONTOUR + 0.1)
        t._sublet_role = "sign_cue"
        out.append(t)
    return out


# The inset colorbar above the rows (inches; cbar_at="top", which no figure uses since C62): 0.04 to the axes top, the
# bar, its ticks and 9-pt tick labels, whose layout boxes then ended 1.6 pt above the top row (measured in Fig. 7(c)
# before C62; at the earlier 0.27 in they reached 0.6 pt into it); CBAR_GAP: from the axes to a colorbar right of them
# (cbar_at="right", sf_e6a), whose bar is CBAR_H wide; a colorbar in the header row (cbar_at="header", Fig. 7(c)
# since C62, header_colorbar) is CBAR_H high
CBAR_TOP, CBAR_H, CBAR_HEAD, CBAR_GAP = 0.04, 0.069, 0.30, 0.06
CBAR_LABEL_GAP_PT = 3.0         # header: from the colorbar's label to its bar (as the inset colorbar's label)
CBAR_CLEAR_PT = 1.5             # header: least gap from the tick labels' layout boxes to the axes top (checked)
BOUNDARY_LABEL_DY = 3.5         # the boundary's label above its end (theory_line's 1.5 pt raised by 2 pt), so that its
#                                 halo clears the line's (as built at 9 pt the label's halo cut into the line's)


def right_colorbar_in(fig, norm, labels: Mapping) -> float:
    """Width (inches) of a colorbar column right of a heat panel (draw_heat_panel(..., cbar_at="right")), for the
    right margin of panel_row: CBAR_GAP, the bar, its ticks (2 pt) and pads (1.5 pt), the widest 7-pt tick label and
    the 7-pt label turned by 90 degrees, with 0.02 in to spare."""
    tick_w = max(text_width_in(fig, style.PLAIN(t)) for t in colorbar_ticks(norm.vmin, norm.vmax))
    _, h, _ = fig.canvas.get_renderer().get_text_width_height_descent(labels["colorbar"],
                                                                     FontProperties(size=style.TICK_PT), ismath=False)
    return CBAR_GAP + CBAR_H + (2.0 + 1.5 + 1.5) / 72.0 + tick_w + h / fig.dpi + 0.02


def header_colorbar(ax, mappable, ticks: Sequence[float], label: str, level: float):
    """Fig. 7(c) (C62): the colorbar of a heat panel in the figure's header row, above the panel: a horizontal bar
    CBAR_H high, centered on the legend row's center line (legend_row: the middle of the top LEGEND_ROW of the
    figure), from CBAR_LABEL_GAP_PT right of its label to the axes' right edge, the label (TICK_PT) left-aligned with
    the axes' left edge and centered on the bar, the ticks and tick labels under the bar, a black tick at `level`
    (the step line). Raises StyleError if the tick labels come closer than CBAR_CLEAR_PT to the axes top (a header
    row for the colorbar needs panel_row(..., legend=True))."""
    fig = ax.figure
    _, H = fig.get_size_inches()
    _, y0, w, h = style.axes_rect_in(ax)
    yc = H - 0.5 * style.LEGEND_ROW
    bx = (text_width_in(fig, label) + CBAR_LABEL_GAP_PT / 72.0) / w
    cb = style.inset_colorbar(ax, mappable, rect=(bx, (yc - 0.5 * CBAR_H - y0) / h, 1.0 - bx, CBAR_H / h),
                              ticks=ticks)
    cb.ax.axvline(level, color="black", linewidth=CONTOUR_PT, zorder=3.0)     # the step line
    t = ax.annotate(label, xy=(0.0, (yc - y0) / h), xycoords="axes fraction", ha="left", va="center",
                    fontsize=style.TICK_PT, annotation_clip=False)
    t._sublet_role = "colorbar_label"
    rend = fig.canvas.get_renderer()
    low = min(tl.get_window_extent(rend).y0 for tl in cb.ax.xaxis.get_ticklabels() if tl.get_text())
    gap = (low - ax.get_window_extent(rend).y1) * 72.0 / fig.dpi
    if gap < CBAR_CLEAR_PT:
        raise style.StyleError(f"header colorbar: its tick labels end {gap:.2f} pt above the axes, less than "
                               f"{CBAR_CLEAR_PT} pt (place the panels with panel_row(..., legend=True))")
    return cb


def draw_heat_panel(ax, block: Mapping, norm, labels: Mapping, *, colorbar: bool = True, ylabel: bool = True,
                    headroom: bool | None = None, cbar_at: str = "top", cues: str = "sign", h_gap_pt: float = 5.0,
                    h_priority: Sequence[float] | None = None, halo_pt: float | None = None, frame: bool = False):
    """pcolormesh of the cell values (PuOr, log norm centered at 1; cell edges stroked in the cell color, so that no
    seam shows between cells), the step line at ratio 1 along the cell edges (block["contour"], ratio_contour: thin
    solid black, above the cells and the boundary line with its halo, so that the sign of a cell reads in greyscale;
    marked on the colorbar at 1), the sign cues "< 1" and "> 1" (sign_cues), the boundary r*(H) as a dotted grey
    line with a white halo (its label on an opaque white box where it sits over missing, hatched cells). The
    colorbar: with cbar_at "top" inset above the rows, the y axis extended for it (§8.6, "inset_colorbar"), so that
    it covers no cell (`headroom` keeps that space in a panel without a colorbar); with "right" a slim column right
    of the axes, as high as the rows, whose width the caller leaves free (right_colorbar_in); with "header" above the
    axes in the figure's header row (header_colorbar; Fig. 7, C62). `cues`: "sign" (sign_cues) or "region"
    (region_cues; Fig. 7, C62). `h_gap_pt` and `h_priority`: the least gap between H tick labels and the order in
    which they are kept (thin_x_ticks; None: its default). Fig. 7 (C62) only: `halo_pt`, the white halo of the
    boundary's line on each side and of its label (style.HALO_PT and LABEL_HALO_PT if None), set before the cues are
    placed; `frame`, the top and right spines drawn as the left and bottom ones, so that the cell area has an edge
    on all four sides where its cells are pale."""
    if cbar_at not in ("top", "right", "header") or cues not in ("sign", "region"):
        raise style.StyleError(f"draw_heat_panel: cbar_at {cbar_at!r}, cues {cues!r}")
    vals = np.ma.masked_invalid(finite(np.array(block["values"], dtype=object).ravel()).reshape(
        len(block["rows"]), len(block["H_min"])))
    mesh = ax.pcolormesh(block["x_edges"], block["y_edges"], vals, cmap=style.RATIO_CMAP, norm=norm,
                         shading="flat", edgecolors="face", linewidth=0.3, zorder=0.8)
    for ln in block["contour"]["lines"]:
        (line,) = ax.plot(ln["H_min"], ln["r"], color="black", linewidth=CONTOUR_PT, linestyle="-",
                          solid_capstyle="projecting", solid_joinstyle="miter", zorder=Z_CONTOUR,
                          label="_nolegend_")
        line._sublet_role = "contour"
    if np.ma.getmaskarray(vals).any():     # missing cells (M23) hatched, so they do not read as the value 1
        xe0, ye0 = block["x_edges"], block["y_edges"]
        ax.add_patch(Rectangle((xe0[0], ye0[0]), xe0[-1] - xe0[0], ye0[-1] - ye0[0], facecolor="white",
                               edgecolor=style.REFERENCE_GREY, hatch="//////", linewidth=0, zorder=0.7))
    ax.set_xscale("symlog", linthresh=1.0, linscale=1.0)
    ax.set_yscale("log")
    xe, ye = block["x_edges"], block["y_edges"]
    ax.set_xlim(xe[0], xe[-1])
    # ticks only at cell centers (H values of the grid), so that no tick label sits inside another H's cell
    ticks = [t for t in style.H_TICKS_MIN if xe[0] <= t <= xe[-1] and any(abs(t - h) < 1e-9 for h in block["H_min"])]
    ax.xaxis.set_major_formatter(style.PLAIN)
    thin_x_ticks(ax, ticks, gap_pt=h_gap_pt, **({} if h_priority is None else {"priority": h_priority}))
    h_ax = style.axes_rect_in(ax)[3]
    if headroom is None:
        headroom = colorbar and cbar_at == "top"
    head = CBAR_HEAD if headroom else 0.0               # inches above the rows: colorbar
    span = math.log(ye[-1] / ye[0])
    ax.set_ylim(ye[0], ye[0] * math.exp(span / (1.0 - head / h_ax)))
    ax.spines["left"].set_bounds(ye[0], ye[-1])
    ax.yaxis.set_major_locator(FixedLocator(row_ticks(ax, block["rows"])))
    ax.yaxis.set_minor_locator(FixedLocator(block["rows"]))
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.yaxis.set_minor_formatter(NullFormatter())
    if frame:
        for side in ("top", "right"):
            ax.spines[side].set_visible(True)
            ax.spines[side].set_linewidth(ax.spines["left"].get_linewidth())
            ax.spines[side].set_edgecolor(ax.spines["left"].get_edgecolor())
    b = block["boundary"]
    last = max((h for h, r in zip(b["H_min"], b["r_star"]) if r is not None), default=None)
    ends_early = last is not None and last < max(block["H_min"])      # spot: the boundary stops before 240 min
    if ends_early:                        # right of its end only if the 7-pt label fits inside the axes there
        to_pt = 72.0 / ax.figure.dpi
        room = (ax.get_window_extent().x1 - ax.transData.transform((last, 1.0))[0]) * to_pt
        ends_early = room >= 3.0 + text_width_in(ax.figure, labels["boundary"]) * 72.0 + 1.0
    avoid = []
    if last is not None:                  # no line where boundary.json has no value (its note is in the extract)
        line, txt = style.theory_line(ax, b["H_min"], [np.nan if r is None else r for r in b["r_star"]], "lower",
                                      labels["boundary"], on_heatmap=True, where="right" if ends_early else "inside",
                                      **({"dx": 3.0} if ends_early else {"dy": BOUNDARY_LABEL_DY}))
        if halo_pt is not None:           # Fig. 7 (C62): a thinner halo than style.HALO_PT, line and label
            for h in ax.lines:
                if getattr(h, "_sublet_role", "") == "halo" and h.get_zorder() == line.get_zorder() - 0.001 \
                        and np.array_equal(h.get_xdata(), line.get_xdata()):
                    h.set_linewidth(line.get_linewidth() + 2.0 * halo_pt)
            txt.set_path_effects([patheffects.withStroke(linewidth=2.0 * halo_pt, foreground="white")])
        # right of an early end the label sits over the hatched missing cells, whose lines would run between its
        # letters (as built at 9 pt in sf_e6a (a), (c)): an opaque white box 1.35 pt around the text, between the
        # hatch (0.7) and the cells (0.8), so that it blanks the hatch and no cell
        if ends_early and np.ma.getmaskarray(vals)[:, np.asarray(block["H_min"], dtype=float) > last].any():
            bb = txt.get_window_extent(ax.figure.canvas.get_renderer()).padded(1.35 * ax.figure.dpi / 72.0)
            (x0, y0), (x1, y1) = ax.transData.inverted().transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor="white", edgecolor="none", linewidth=0,
                                   zorder=0.75))
        avoid = [ln for ln in ax.lines if ln is line or getattr(ln, "_sublet_role", "") == "halo"] + [txt]
    ax.set_xlabel(labels["H"])
    if ylabel:
        ax.set_ylabel(labels["c_y"])
    (region_cues if cues == "region" else sign_cues)(ax, block, mesh.get_cmap(), norm, labels, avoid=avoid)
    cb = None
    ticks = colorbar_ticks(norm.vmin, norm.vmax)
    if colorbar and cbar_at == "right":
        w_ax = style.axes_rect_in(ax)[2]
        top = ax.transAxes.inverted().transform(ax.transData.transform((xe[0], ye[-1])))[1]
        cb = style.inset_colorbar(ax, mesh, rect=(1.0 + CBAR_GAP / w_ax, 0.0, CBAR_H / w_ax, top),
                                  orientation="vertical", label=labels["colorbar"], ticks=ticks)
        cb.ax.axhline(block["contour"]["level"], color="black", linewidth=CONTOUR_PT, zorder=3.0)  # the step line
    elif colorbar and cbar_at == "header":
        cb = header_colorbar(ax, mesh, ticks, labels["colorbar"], block["contour"]["level"])
    elif colorbar:
        frac_h = CBAR_H / h_ax
        bar_y = 1.0 - (CBAR_TOP / h_ax) - frac_h
        lab_w = text_width_in(ax.figure, labels["colorbar"])
        w_ax = style.axes_rect_in(ax)[2]
        x0 = min(0.62, (lab_w + 0.10) / w_ax)
        cb = style.inset_colorbar(ax, mesh, rect=(x0, bar_y, 0.97 - x0, frac_h), ticks=ticks)
        cb.ax.axvline(block["contour"]["level"], color="black", linewidth=CONTOUR_PT, zorder=3.0)  # the step line
        ax.annotate(labels["colorbar"], xy=(x0, bar_y + frac_h / 2), xycoords="axes fraction", xytext=(-3, 0),
                    textcoords="offset points", ha="right", va="center", fontsize=style.TICK_PT)
    return mesh, cb


# ---------------------------------------------------------------------------------------------------------------
def build(inp: Inputs) -> dict:
    e2, game, por, a11 = inp.json(E2), inp.json(GAME), inp.json(POR), inp.json(A11)
    heat, bnd = inp.json(HEAT), inp.json(BOUND)
    rules = ("a1", "prewarm", "bl6")
    ep = episode_block(e2, 1, rules)
    h_end = max(max(h_values(need(e2, "episodes", g, what=E2))) for g in GROUPS)
    cr = cr_curve(game, por, 1, h_end=h_end)
    a = {**{r: ep[r] for r in rules}, "prewarm_shown_at": ep["shown_at"].get("prewarm", {}),
         "CR_exact": {"H_min": cr["H_min"], "CR": cr["CR"]}, "CR_extension": cr["extension"],
         "hstar_H_min": cr["hstar_H_min"], "verticals": verticals(a11, 1), "overlap": median_overlap(ep, rules)}
    b = totals_block(e2, 1)
    b = {"a1": {g: b[g] for g in GROUPS}, "minimizer": b["minimizer"]}
    hb = heat_block(heat, bnd, "maas", "a5", 1)
    c = {k: hb[k] for k in ("H_min", "x_edges", "y_edges", "rows", "values", "ci", "n_pairs", "share_insured",
                            "vmin", "vmax", "notes", "boundary", "contour")}
    labels = {**MAIN_LABELS, "status": STATUS,
              "a_note": "trace episodes leave C2's core: per-episode ratios are diagnostics; mu/beta~ = 1, tier M; "
                        "episodes of the four alignments pooled (M19)",
              "a_coincide": "A1 equals 'always cold' wherever it does not insure at mu <= 1 (Q42 (a)); the pre-warm "
                            "rule is drawn only where its per-episode ratios differ from A1's (its medians can still "
                            "equal A1's); A1 is drawn on top; a.overlap gives each rule's largest median gap to A1",
              "b_note": "level 1 = all-fallback (BL0a); medians over (lender, series, alignment) triples (M19)",
              "c_note": "MaaS lenders, lambda' from a5 at both sites, mu/beta~ = 1; median over (lender, series, "
                        "alignment) of the layer-summed cost ratio (M29); boundary with the certified bound (M30)"}
    return {"a": a, "b": b, "c": c, "labels": labels, "sources": list(inp.sources)}


# ---------------------------------------------------------------------------------------------------------------
# Fig. 7's own drawing (C62)
H_TICK_GAP_PT = 0.5 * style.TICK_PT     # half an em of the 7-pt H tick labels (thin_x_ticks' 5 pt was half of 9 pt)
# (c): 30 min before 1 h. The step line turns between the 30 and 60 columns (rows 1.25-1.5), and (a) and (b) label 30;
# "30" does not fit next to "60" in (c) (2.25 pt of the 3.5 pt gap free), so 60 becomes a minor tick there
H_TICK_PRIORITY_C = (1.0, 10.0, 30.0, 2.0, 5.0, 60.0, 15.0, 120.0)
# (c): the white halo of the boundary's dotted line on each side and of its label (pt). style.HALO_PT (0.8 pt per side)
# was wider than the 0.9-pt dots, so the line read as a white solid line with grey dots, and the label showed white
# rims on the pale cells of ratio 1; 0.35 pt still parts the dots from the orange cells
HEAT_HALO_PT = 0.35
P95_LABEL = "P95"               # (a): the top edge of ALG*'s MaaS band (the caption: "ALG*'s band to the P95")
BAND_LABEL_DX_PT = 2.0          # (a): from the label's right end to the band's last point
BAND_LABEL_CLEAR_PT = 1.0       # (a): least gap from the label's layout box to the band's top edge
LEGEND_CLEAR_IN = 0.10          # least gap from the legend row to the colorbar's label in the header row


def band_top_label(ax, block: Mapping, *, key: str = "a1", group: str = "maas", text: str = P95_LABEL):
    """Fig. 7(a) (C62): `text` at the right end of the filled band's top edge (block[key][group]: its P95 points),
    right-aligned at least BAND_LABEL_DX_PT left of the last point, where its layout box lies above the edge (the
    polyline through the P95 points) by BAND_LABEL_CLEAR_PT or more, outside the band, and inside the axes: at the
    height of the reference verticals' labels (top 1.5 pt under the axes top, draw_vertical_labels) if it fits
    there, so that the panel's top labels share one line, else at the offset nearest to that point (on a 0.5-pt
    grid); in the policy's label color with a white halo. Needs the final scales."""
    s = block[key][group]
    x, p = finite(s["H_min"]), finite(s["p95"])
    ok = np.isfinite(x) & np.isfinite(p)
    if not ok.any():
        return None
    fig = ax.figure
    to_pt = 72.0 / fig.dpi
    rend = fig.canvas.get_renderer()
    edge = _dense(ax.transData.transform(np.column_stack([x[ok], p[ok]])) * to_pt)
    abox = ax.get_window_extent(rend)
    t = ax.annotate(text, xy=(x[ok][-1], p[ok][-1]), xytext=(-BAND_LABEL_DX_PT, 0.0), textcoords="offset points",
                    ha="right", va="center", fontsize=style.TICK_PT, color=style.policy(key).label_color,
                    zorder=style.Z_THEORY_LABEL)
    bb = t.get_window_extent(rend)
    bx0, by0, bx1, by1 = bb.x0 * to_pt, bb.y0 * to_pt, bb.x1 * to_pt, bb.y1 * to_pt
    c, best, top = BAND_LABEL_CLEAR_PT, None, abox.y1 * to_pt
    dy_top = top - 1.5 - by1                            # the layout box's top 1.5 pt under the axes top
    for ddx in np.arange(0.0, 12.0 + 1e-9, 0.5):
        for dy in [dy_top] + list(np.arange(-12.0, 12.0 + 1e-9, 0.5)):
            x0, x1, y0, y1 = bx0 - ddx, bx1 - ddx, by0 + dy, by1 + dy
            under = edge[(edge[:, 0] >= x0 - c) & (edge[:, 0] <= x1 + c)]
            if (under[:, 1] > y0 - c).any() or y1 > top or x0 < abox.x0 * to_pt + c:
                continue
            rank = (dy != dy_top, math.hypot(ddx, dy))
            if best is None or rank < best[0]:
                best = (rank, (float(ddx), float(dy)))
    best = None if best is None else best[1]
    if best is None:
        t.remove()
        raise style.StyleError(f"{text!r} finds no place above the band's top edge")
    t.xyann = (-BAND_LABEL_DX_PT - best[0], best[1])
    t.set_path_effects([patheffects.withStroke(linewidth=style.LABEL_HALO_PT, foreground="white")])
    t._sublet_role = "direct_label"
    return t


def lender_labels(ax, block: Mapping, *, key: str = "a1") -> list:
    """Fig. 7(b) (C62): each lender group's line labeled with its name (style.ENV_LABELS['lender']) on the free space
    next to its line and nearer to it than to the other group's (common.place_label), in the policy's label color
    with a white halo; StyleError where a label fits nowhere."""
    lines = {}
    for g in GROUPS:
        P = points_pt(ax, block[g]["H_min"], block[g]["median"])
        lines[g] = _dense(P) if len(P) > 1 else P
    out = []
    for g in GROUPS:
        others = np.vstack([lines[o] for o in GROUPS if o != g])
        t = place_label(ax, style.ENV_LABELS["lender"][g], lines[g], others=others,
                        color=style.policy(key).label_color)
        if t is None:
            raise style.StyleError(f"the {g} line's label fits nowhere in the panel")
        out.append(t)
    return out


DASH_RC = {"--": "lines.dashed_pattern", ":": "lines.dotted_pattern"}


def centered_dashes(pairs: Sequence[tuple], *, fontsize: float = style.TICK_PT) -> list[tuple]:
    """Fig. 7 (C62): the dashed (or dotted) legend samples of `pairs` with their on-off pattern centered on the
    sample, a dash in the middle and the two ends alike, by a dash offset. Started at the sample's left end, the
    pattern (3.0 on, 1.6 off) left a 0.2-pt sliver of a fourth dash at the right end of the 14-pt Spot sample (two
    ems of the 7-pt legend); centered, the sample shows three whole dashes with 0.9 pt free at each end. The sample's
    length is legend.handlelength x `fontsize`, the patterns those of the rcParams (unscaled: lines.scale_dashes is
    off); other samples are returned unchanged."""
    if mpl.rcParams["lines.scale_dashes"]:
        raise style.StyleError("centered_dashes assumes unscaled dash patterns (lines.scale_dashes off)")
    length = float(mpl.rcParams["legend.handlelength"]) * fontsize
    out = []
    for h, lab in pairs:
        ls = h.get_linestyle() if isinstance(h, Line2D) else None
        pat = [float(v) for v in mpl.rcParams[DASH_RC[ls]]] if ls in DASH_RC else []
        if len(pat) == 2:
            on, period = pat[0], sum(pat)
            h.set_linestyle(((0.5 * on - 0.5 * length) % period, pat))
        out.append((h, lab))
    return out


def legend_over(leg, axes: Sequence, clear_of=None) -> None:
    """Fig. 7 (C62): the legend row (legend_row) centered over `axes`, the panels whose series it keys, instead of
    over every panel; StyleError if it ends less than LEGEND_CLEAR_IN left of the artist `clear_of` (the header
    colorbar's label) or leaves the page."""
    fig = leg.figure
    W, H = fig.get_size_inches()
    rects = [style.axes_rect_in(a) for a in axes]
    rend = fig.canvas.get_renderer()
    w = leg.get_window_extent(rend).width / fig.dpi
    xc = 0.5 * (min(r[0] for r in rects) + max(r[0] + r[2] for r in rects))
    xc = min(max(xc, 0.5 * w), W - style.MARGIN_RIGHT - 0.5 * w)
    leg.set_bbox_to_anchor((xc / W, 1.0 - 0.5 * style.LEGEND_ROW / H), transform=fig.transFigure)
    if clear_of is not None:
        end, start = leg.get_window_extent(rend).x1 / fig.dpi, clear_of.get_window_extent(rend).x0 / fig.dpi
        if end + LEGEND_CLEAR_IN > start:
            raise style.StyleError(f"the legend row ends at {end:.2f} in, within {LEGEND_CLEAR_IN} in of the header "
                                   f"colorbar's label at {start:.2f} in")


# ---------------------------------------------------------------------------------------------------------------
# C62, the supplementary panels (sf_e2_por, sf_e2_mu_ep, sf_e2_mu_cost, sf_e2_pool, sf_e6b): header keys and panel
# titles. Added for those scripts only; Fig. 7's drawing does not call them.
# the gutter before a panel that shares its left neighbor's y axis (panel_row's left; style.LEFT_SHARED is 0.11 in):
# the bold letter, 0.14 in wide, and its 2-pt gap to the spine fit in it, so that no letter overhangs its left
# neighbor's top right corner (at 0.11 in, "(b)" reached 0.08 in over (a))
SHARED_GUTTER_IN = 0.20
KEY_ROW_IN = 0.17               # pitch of the key rows of a header, row i centered (i + 0.5) KEY_ROW_IN below the top
KEY_GAP_IN = 0.02               # below a header's last key row, to the top margin (the letters' and titles' line)


def key_rows_in(n: int) -> float:
    """The top margin (inches) of panels under a header of n key rows (key_row): MARGIN_TOP, the rows and
    KEY_GAP_IN, so that the last row's ink ends about 5 pt above the panel letters (two rows: 0.48 in, against
    0.54 in for panel_row(legend=2))."""
    return style.MARGIN_TOP + n * KEY_ROW_IN + KEY_GAP_IN


def _math_baseline(texts: Sequence) -> None:
    """The mathtext texts of `texts` with va 'baseline' (one line each; the others are left as they are) moved so that
    their glyphs' baseline lies on their anchor as the PDF sets it, as a plain text's does (common.align_baselines:
    matplotlib rounds a mathtext line's height and depth up to whole pt in the PDF and its glyphs rise by up to
    1 pt)."""
    align_baselines([t for t in texts if t.get_verticalalignment() == "baseline"])


class KeyTitle:
    """A key row's title (key_row): an entry of the row without a sample (_KeyTitleHandler), so that the title is laid
    out with the labels, on their baseline in whichever backend draws the row."""


class _KeyTitleHandler(HandlerBase):
    def legend_artist(self, legend, orig_handle, fontsize, handlebox):
        handlebox.width = 0.0                       # no sample: the title's text starts the row
        a = Line2D([], [], linestyle="none", marker="None")
        handlebox.add_artist(a)
        return a


def key_row(fig, pairs: Sequence[tuple], *, x_center_in: float, y_center_in: float, title: str | None = None,
            **legend_kw):
    """C62 (supplementary panels): one frameless key row of `pairs` (handle, label), its entries side by side, centered
    at (x_center_in, y_center_in) inches on the page (kept on the page, MARGIN_RIGHT free at the right), led by
    `title` (an entry without a sample, KeyTitle, one column spacing before the first sample; a mathtext title or
    label moved onto the plain labels' baseline as the PDF prints it, _math_baseline: as built with legend_row,
    sf_e2_mu_cost's "Minimum over $H$" sat 1 pt above "ALG*"), so that a row of several mathtext labels
    ("mu/beta~ = 2", "mu/beta~ = 1", ...) is written once as "mu/beta~ =" and the values. Each row is its own legend,
    so that the rows of a header keep their own baselines (a two-row legend sets each column's rows from that
    column's tallest label: as built, sf_e2_por's second row sat 2.3 pt lower under its mathtext labels than in its
    third column). Returns the legend."""
    W, H = (float(v) for v in fig.get_size_inches())
    pairs = ([(KeyTitle(), title)] if title else []) + list(pairs)
    handles, labels = zip(*pairs)
    kw = dict(loc="center", ncol=len(handles), frameon=False, borderaxespad=0.0, borderpad=0.0,
              handler_map={**style.PAIR_HANDLER_MAP, KeyTitle: _KeyTitleHandler()})
    kw.update(legend_kw)
    leg = fig.legend(list(handles), list(labels), bbox_to_anchor=(x_center_in / W, y_center_in / H),
                     bbox_transform=fig.transFigure, **kw)
    leg._sublet_role = "key_row"
    w = leg.get_window_extent(fig.canvas.get_renderer()).width / fig.dpi
    if w > W - style.MARGIN_RIGHT:
        leg.remove()
        raise style.StyleError(f"key row {labels!r} is {w:.2f} in wide, wider than the page less its right margin")
    xc = min(max(x_center_in, 0.5 * w), W - style.MARGIN_RIGHT - 0.5 * w)
    leg.set_bbox_to_anchor((xc / W, y_center_in / H), transform=fig.transFigure)
    _math_baseline(leg.get_texts())
    return leg


def panel_titles(axes: Sequence, texts: Sequence[str]) -> tuple[list, list]:
    """C62 (supplementary panels): the bold panel letters (style.panel_letters) and beside each its title at the
    caption size that C62 gives panel titles (common.panel_title with style.LABEL_PT, as group g1's sf_e1_* and
    sf_e10_*; TICK_PT until C62), on the letter's baseline, a mathtext title moved onto it as the PDF prints it
    (_math_baseline; as built, "mu/beta~ = 0.2" sat up to 0.2 pt off its letter). Returns (letters, titles)."""
    from figs.common import panel_title
    letters = style.panel_letters(list(axes))
    titles = []
    for ax, letter, text in zip(axes, letters, texts):
        t = panel_title(ax, letter, text, fontsize=style.LABEL_PT)
        t._sublet_role = "panel_title"
        titles.append(t)
    _math_baseline(titles)
    return letters, titles


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    ax_a, ax_b, ax_c = style.panel_row(fig, (1, 1, 1), legend=True)
    a = data["a"]
    cr = {"H_min": a["CR_exact"]["H_min"], "CR": a["CR_exact"]["CR"], "extension": a["CR_extension"]}
    draw_episode_panel(ax_a, a, cr, a["verticals"], lab, ("a1", "prewarm", "bl6"), h_gap_pt=H_TICK_GAP_PT)
    band_top_label(ax_a, a)
    tot = {**data["b"]["a1"], "minimizer": data["b"]["minimizer"]}
    draw_totals_panel(ax_b, tot, lab, h_gap_pt=H_TICK_GAP_PT)
    style.ygrid(ax_b)
    lender_labels(ax_b, tot)
    c = data["c"]
    norm = style.ratio_norm(c["vmin"], c["vmax"])
    draw_heat_panel(ax_c, c, norm, lab, cbar_at="header", cues="region", h_gap_pt=H_TICK_GAP_PT,
                    h_priority=H_TICK_PRIORITY_C, halo_pt=HEAT_HALO_PT, frame=True)
    style.panel_letters([ax_a, ax_b, ax_c])
    leg = style.legend_row(fig, [], extra=episode_handles(["a1", "prewarm", "bl6"])
                           + centered_dashes(style.env_handles("lender")))
    legend_over(leg, [ax_a, ax_b], clear_of=next(t for t in ax_c.texts
                                                 if getattr(t, "_sublet_role", "") == "colorbar_label"))
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
