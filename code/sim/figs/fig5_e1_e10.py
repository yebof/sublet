"""Fig. 5: the revocation loss (E1(b); E10(a) under the adaptive lender); design/sim_spec_ms3.md §8.4, plan §1.

(a) OPT_eager / OPT(sigma, omega) against rho: C3-L1(c)'s single-site family at T = 60 (c3_benchmark.json a) and
    at the largest T of e1/tight_family.json (T = 3000, M9), the rho < 2 instance at the largest D of
    a1_lemma2_tight_small_rho.txt (D = 25), the random core instances (c3_benchmark.json b, grey) and the E1(b) trace
    brackets (e1/summary.json brackets.trace, M4, M5); grey dashed max(2, rho) (C3-L2, PROVEN). Each of the five
    marker kinds has a direct label on the free space next to its markers (common.place_label; labels.a_direct).
(b) ALG / LB against rho on E1(b)'s instances under the adaptive lender (e1/summary.json
    ratios.adaptive.<rho>.1.<tag>): medians of ratio_LB with median_ci95 bars, a black tick at the median of
    ratio_inc where it differs from the median by more than 1% (common.inc_ticks); A2 fractional from A2-r1's P/LB;
    the guarded series (E1's tag Sublet) is the one-way guard around the lagged BL5 at Algorithm 1's defaults, drawn
    as bl5_g1, "Lagged RetroRenting + one-way guard" (MS6 C46: design/ms6_spec.md M2, M4); grey dashed max(2, rho)
    (C3-Cor3's factor; its label hangs below the line's end, and the rho tick at 2, its kink, is labeled first where
    1.5 and 2 do not both fit; at 7 pt both are labeled), grey solid rho m / (m + rho - 1) at m = 8 (C3-T4's limit on
    its own family, a reference here).
(c) E[ALG] / E[OPT] against m on the T4 family at rho = 16 under the adaptive lender (e10/summary.json
    a.adaptive.16.<m>.<tag>, bounds.16.<m>): LB_T (C3-T4, dotted), its T -> infinity limit (solid), O1-B at
    RR-renew's run (dashed), labeled so that no label is level with another line's end, theory or data
    (right_theory_lines(..., clear_ends=True)). Where RR-renew's ratio equals the limit at every m (limit_is_rr),
    the limit's line lies under RR-renew's and its label says so (LIMIT_IS_RR; labels.c_limit).
The drawn labels name no design or experiment ID (MS6 C46: design/ms6_spec.md M6, M17): "max(2, ρ)" in (a) and (b),
"trace instances" in (a) (M6's label; "trace" from C46 to C62, since at 9 pt "trace instances" fit nowhere on (a)'s
free space), "LB_T (adaptive)" and "RR-renew bound" (O1-B) in (c); the caption (LaTeX, in the manuscript) gives the
paper's result numbers. The status labels of the extract keep the design names (data).
C47 (print check of the gate): (c)'s "RR-renew bound" is set on one line, level with its dashed line's end and with
no leader (on two lines, stacked above the other labels, its leader ended on A3's last marker and read as A3's), and
(c) is a little wider (PANEL_RATIOS), so that the label column keeps every m tick; the limit's T is set in math
($T\\to\\infty$, as Fig. 6). C47 (print check of the gate, U46): every drawn symbol is set in math, italic as on the
axes ($T=3000$, $\\rho<2$, $\\max(2,\\rho)$, $\\rho m/(m+\\rho-1)$, $m=8$), and the limit's arrow is \\longrightarrow,
STIX's full-height arrow (Liberation Sans' U+2192, which \\to sets, prints at about 40% of the cap height), as in
Figs. 3 and 6.
MS7 C62 (the type scale of style.py: text at 7 pt, axis labels and letters at the caption size): the axes widths are
0.95 : 1.1 : 0.95 (PANEL_RATIOS), since (c)'s label column and m ticks need less width at 7 pt, so that (b) labels
rho = 1.5 beside 2; "random core" is set on two lines, which fit directly above its grey dots, and the trace squares
carry M6's "trace instances"; the label columns of (b) and (c) are stacked on the labels' own heights
(right_theory_lines(..., measured=True): a mathtext line is taller than the 1.2 em that common.LINE_STEP_PT
allows); the legend's two mathtext labels (A2's r-bar) sit on the row's plain baseline as printed
(common.align_baselines; 0.9 pt high before); (b)'s log y axis has no minor ticks between its labeled 1, 2, 5, 10,
20 (as Fig. 7). No plotted number changes.
C62 fix round (the supplement's critic): a direct label of (a) starts at least SPINE_CLEAR_PT (4 pt) right of the y
spine (off_spine; free_spot keeps 1.5 pt from the axes edges, and "rho < 2" started 2.5 pt from the spine, reading as
touching it); sf_e1_sched's keys follow the same rule.

Run from code/sim: python -m figs.fig5_e1_e10 [--from-extract [JSON]]. --from-extract redraws the figure from its
extract alone (default: code/sim/out/figs/fig5.json under the input root of figs.inputs, i.e. the repository or
SUBLET_FIGS_IN_ROOT).
"""
from __future__ import annotations

import math
import re
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.ticker import NullLocator

from figs import style
from figs.common import (E1, E10, INC_TICK_RULE, KEY_PAD_PT, MissingKey, RHO_MAIN, agreement, align_baselines, cli,
                         data_range, draw_e1_ratio_panel, draw_e10_series, e1_series, e10_bound, e10_series, finite,
                         free_spot, m_axis, max2rho, need, num_items, place_label, points_pt, ratio_log2_axis,
                         ratio_log10_axis, rho_star_axis, rho_star_range, right_theory_lines)
from figs.inputs import Inputs

NAME = "fig5"

C3B = "code/theory_checks/c3/out/c3_benchmark.json"
C3B_TXT = "code/theory_checks/c3/out/c3_benchmark.txt"          # the T of part (a), in its header line
SMALL_RHO = "code/theory_checks/c3/audit/out/a1_lemma2_tight_small_rho.txt"
TIGHT = "code/sim/out/e1/tight_family.json"

FIG5_B_KEYS = ("bl5_g1", "a2_frac", "a2_r1", "a2_theory", "a3")     # C46 (M2, M4): E1's tag Sublet is bl5_g1
FIG5_C_KEYS = ("rr_renew", "a2_theory", "a3")

RHO_XLIM = (1.0, 20.0)          # panels (a), (b): rho from 1 to 20 (§8.4)
LIMIT_M = 8                     # (b): the reference rho m / (m + rho - 1) at m = 8 (§8.4)
RHO_C = RHO_MAIN                # (c): rho of the T4 family in the main text (§5.2)
PANEL_RATIOS = (0.95, 1.1, 0.95)   # axes widths of (a), (b), (c) (not in §8.4, which has (1, 1, 1)). C62: at 7 pt (c)'s
#                                    label column and m ticks need less width, which goes to (b), so that its data area
#                                    labels rho = 1.5 beside 2, and to (a)'s direct labels ((0.85, 1.0, 1.15) since
#                                    C47, which widened (c) for its one-line "RR-renew bound" at 9 pt)
KINK = 2.0                      # (b): the kink of max(2, rho), the rho tick labeled first
A_ORDER = ("small_rho", "tight_T3000", "tight_T60", "trace_brackets", "random_core")     # (a): labeling order
A_BOUND_DX_PT = -6.0             # (a): the max(2, rho) label ends this far left of its line's end (clear of "(b)")
SPINE_CLEAR_PT = 4.0            # C62 fix round: a placed label or key starts at least this far right of the y spine
TEXT_GAP_PT = 7.0               # C62 fix round: and, where asked, keeps 1 em (7 pt) beside a text level with it
# (c): the limit's label where RR-renew equals it at every m, and where not (C47: T in math, as Fig. 6; U46: the
# full-height arrow \longrightarrow, as Figs. 3 and 6)
LIMIT_IS_RR = "$T\\longrightarrow\\infty$ limit\n= RR-renew"
LIMIT_LABEL = "$T\\longrightarrow\\infty$ limit"

STATUS = {"C3-L2": "PROVEN", "C3-Cor3": "PROVEN", "C3-T4": "PROVEN", "C3-T4'": "PROVEN", "O1-B": "PROVEN",
          "C-O1a": "VERIFIED NUMERICALLY / CONJECTURE", "G3(b)": "PROVEN"}


# ---------------------------------------------------------------------------------------------------------------
# Fig. 5
_SMALL_RE = re.compile(r"rho=([0-9.]+)\s+D=(\d+):\s+OPT_eager=([0-9.]+)\s+OPT\(no reclaim\)=([0-9.]+)\s+"
                       r"ratio=([0-9.]+)")


def small_rho_rows(text: str) -> list[dict]:
    rows = [dict(rho=float(m[0]), D=int(m[1]), OPT_eager=float(m[2]), OPT_none=float(m[3]), ratio=float(m[4]))
            for m in _SMALL_RE.findall(text)]
    if not rows:
        raise MissingKey(f"{SMALL_RHO}: no 'rho=... D=...: ... ratio=...' line")
    return rows


def part_a_horizon(text: str) -> float:
    """T of c3_benchmark's part (a), from its header line '(a) single site, ..., T=60, no reclaims'."""
    m = re.search(r"^\(a\)[^\n]*\bT=(\d+)", text, re.M)
    if m is None:
        raise MissingKey(f"{C3B_TXT}: no '(a) ... T=<n>' header line")
    return float(m.group(1))


def tight_rows(tf: Any) -> list[dict]:
    rows = tf.get("rows") if isinstance(tf, Mapping) else None          # e1.py: {meta, rows, ...} (§4.4)
    if not isinstance(rows, list) or not rows:
        raise MissingKey(f"{TIGHT}: no 'rows' list")
    return rows


def build(inp: Inputs) -> dict:
    c3 = inp.json(C3B)
    t_ref = part_a_horizon(inp.text(C3B_TXT))
    tf = tight_rows(inp.json(TIGHT))
    small = small_rho_rows(inp.text(SMALL_RHO))
    e1 = inp.json(E1)
    e10 = inp.json(E10)

    # (a)
    a60 = sorted(need(c3, "a", what=C3B), key=lambda r: r["rho"])
    t_big = max(float(r["T"]) for r in tf)
    big = sorted((r for r in tf if float(r["T"]) == t_big), key=lambda r: float(r["rho"]))
    d_big = max(r["D"] for r in small)
    sm = [r for r in small if r["D"] == d_big]
    if not sm or any(r["rho"] >= 2.0 for r in sm):     # (a) labels these points "ρ < 2"
        raise MissingKey(f"{SMALL_RHO}: the rows at D = {d_big} are not all at rho < 2")
    rand = [(b["rho"], pr["rate"], pr["eager_over_omega"]) for b in need(c3, "b", what=C3B) for pr in b["per_rate"]]
    br = {"rho_star": [], "c": [], "rho_instance": [], "point": [], "lo": [], "hi": [], "exact": []}
    for rho, _, by_c in num_items(need(e1, "brackets", "trace", what=E1)):
        for c, _, rec in num_items(by_c):
            vals = (rho, int(c), rec.get("rho_instance"), rec.get("point"), rec.get("lo"), rec.get("hi"),
                    bool(rec.get("exact")))
            for f, v in zip(br, vals):
                br[f].append(v)
    a = {"tight_T60": {"rho": [r["rho"] for r in a60], "ratio": [r["OPTeager_over_OPTnone"] for r in a60],
                       "T": t_ref},
         "tight_T3000": {"rho": [float(r["rho"]) for r in big], "ratio": [float(r["ratio"]) for r in big],
                         "T": t_big},
         "small_rho": {"rho": [r["rho"] for r in sm], "ratio": [r["ratio"] for r in sm], "D": d_big},
         "random_core": {"rho": [t[0] for t in rand], "rate": [t[1] for t in rand],
                         "eager_over_omega": [t[2] for t in rand]},
         "trace_brackets": br,
         "bound": max2rho(RHO_XLIM)}

    # (b)
    b = e1_series(e1, "adaptive", 1, FIG5_B_KEYS)
    b = {k: {"rho_star": v.pop("x"), **v} for k, v in b.items()}
    b["x_range"] = rho_star_range(b[FIG5_B_KEYS[0]]["rho_star"], len(FIG5_B_KEYS))
    b["bound"] = max2rho(b["x_range"])
    grid = list(np.geomspace(*b["x_range"], 41))
    b["limit_m8"] = {"rho": grid, "value": [r * LIMIT_M / (LIMIT_M + r - 1) for r in grid], "m": LIMIT_M}

    # (c)
    c = build_e10_adaptive(e10, RHO_C)
    c_limit = LIMIT_IS_RR if limit_is_rr([c]) else LIMIT_LABEL
    labels = {
        "a_x": r"$\rho$", "a_y": r"OPT$_{\mathrm{eager}}$ / OPT($\sigma, \omega$)",
        "a_series": {"tight_T60": f"single-site family (C3-L1(c)), T = {t_ref:g}, open circles",
                     "tight_T3000": f"same family, T = {t_big:g}, filled circles",
                     "small_rho": f"rho < 2 instance, D = {d_big}, open diamonds",
                     "random_core": "random core instances (c3_benchmark b), grey dots",
                     "trace_brackets": "E1(b) trace instances (trace schedule), squares with brackets "
                                       "[LB_e/inc_w, inc_e/LB_w] (M4, M5)"},
        # C47 (print check of the gate, U46): the symbols of the drawn labels in math, italic as on the axes and in (c)
        "a_direct": {"tight_T60": f"$T={t_ref:g}$", "tight_T3000": f"$T={t_big:g}$", "small_rho": r"$\rho<2$",
                  # C62: "random core" on two lines, which fit directly above the grey dots (on one line it fit only
                  # beside the circles at rho = 2, far from the dots); "trace instances", M6's label, fits at 7 pt
                  # (as built "trace": at 9 pt it fit nowhere)
                  "trace_brackets": "trace instances", "random_core": "random\ncore"},   # C46 (M6): no ID
        "a_bound": r"$\max(2,\rho)$",                                                      # C47 (U46): math
        "b_x": r"$\rho$", "b_y": "ALG / LB", "b_bound": r"$\max(2,\rho)$",                # C46 (M6): no ID
        "b_limit": f"$\\rho m/(m+\\rho-1)$,\n$m={LIMIT_M}$, limit",                         # C47 (U46): math
        "b_tick": f"black tick: median of ALG / MILP incumbent, {INC_TICK_RULE}",
        "b_note": "trace instances leave the ORML core: ratios are diagnostics, not bound checks (E1-8)",
        "c_x": "Sites m", "c_y": "E[ALG] / E[OPT]", "c_LB_T": "LB$_T$\n(adaptive)", "c_limit": c_limit,
        "c_O1B": "RR-renew bound", "c_T": "T = 16 m D (M10)", "c_rho": f"rho = {RHO_C}",      # C46 (M6): no ID
        "status": STATUS,
    }
    return {"a": a, "b": b, "c": c, "labels": labels, "sources": list(inp.sources)}


def a_marks() -> dict:
    """Line2D keywords of (a)'s five marker kinds, black (grey for the random core instances), no line."""
    black = dict(linestyle="none", markeredgewidth=style.MARKER_EDGE_PT, markeredgecolor="black",
                 markersize=style.MARKER_PT, zorder=style.Z_DATA)
    return {"tight_T60": dict(black, marker="o", markerfacecolor="white"),
            "tight_T3000": dict(black, marker="o", markerfacecolor="black"),
            "small_rho": dict(black, marker="D", markerfacecolor="white", markersize=style.MARKER_PT - 0.6),
            "trace_brackets": dict(black, marker="s", markerfacecolor="black"),
            "random_core": dict(linestyle="none", marker="o", markersize=2.0, markeredgewidth=0,
                                color=style.THEORY_GREY, zorder=style.Z_DATA - 0.1)}


def draw_a(ax, a: Mapping, labels: Mapping) -> None:
    mk = a_marks()
    rc = a["random_core"]
    ax.plot(rc["rho"], rc["eager_over_omega"], label="_nolegend_", **mk["random_core"])
    tb = a["trace_brackets"]
    x, y, lo, hi = (finite(tb[f]) for f in ("rho_instance", "point", "lo", "hi"))
    ok = np.isfinite(lo) & np.isfinite(hi) & np.isfinite(y)
    ax.errorbar(x[ok], y[ok], yerr=np.vstack([y[ok] - lo[ok], hi[ok] - y[ok]]), fmt="none", ecolor="black",
                elinewidth=style.UNCERTAINTY_PT, capsize=0, zorder=style.Z_DATA, label="_nolegend_")
    ax.plot(x, y, label="_nolegend_", **mk["trace_brackets"])
    for k in ("tight_T60", "tight_T3000", "small_rho"):
        ax.plot(a[k]["rho"], a[k]["ratio"], label="_nolegend_", **mk[k])
    style.theory_line(ax, a["bound"]["rho"], a["bound"]["max2rho"], "upper", labels["a_bound"], dx=A_BOUND_DX_PT)


def a_direct_labels(ax, a: Mapping, labels: Mapping) -> None:
    """Direct labels of (a)'s five marker kinds (labels.a_direct), after the axes limits are final: each on the free
    space nearest to its own markers and nearer to them than to any other kind's (common.place_label), placed in
    A_ORDER, each an obstacle for the next; a kind with no finite point gets no label; StyleError if one fits
    nowhere."""
    pts = {"tight_T60": (a["tight_T60"]["rho"], a["tight_T60"]["ratio"]),
           "tight_T3000": (a["tight_T3000"]["rho"], a["tight_T3000"]["ratio"]),
           "small_rho": (a["small_rho"]["rho"], a["small_rho"]["ratio"]),
           "trace_brackets": (a["trace_brackets"]["rho_instance"], a["trace_brackets"]["point"]),
           "random_core": (a["random_core"]["rho"], a["random_core"]["eager_over_omega"])}
    pts = {k: points_pt(ax, *v) for k, v in pts.items()}
    for k in A_ORDER:
        if not len(pts[k]):                             # a kind with no finite point has no markers to label
            continue
        others = np.concatenate([p for j, p in pts.items() if j != k])
        t = place_label(ax, labels["a_direct"][k], pts[k], others=others)
        if t is None:
            raise style.StyleError(f"{NAME} (a): the label {labels['a_direct'][k]!r} fits nowhere on the free space")
        off_spine(ax, t, pts[k], others=others)         # C62 fix round: clear of the y spine


def spine_gap_pt(ax, artist) -> float:
    """C62 fix round: how far (pt) `artist` (a text or a key) starts right of the y spine of `ax` (its left edge)."""
    r = ax.figure.canvas.get_renderer()
    return (artist.get_window_extent(r).x0 - ax.get_window_extent(r).x0) * 72.0 / ax.figure.dpi


def move_to(ax, artist, x_pt: float, y_pt: float) -> None:
    """C62 fix round: put the lower left corner of a key or label placed by common.place_key or place_label at
    (x_pt, y_pt), display pt, as those functions put it."""
    xy = tuple(ax.transAxes.inverted().transform((x_pt * ax.figure.dpi / 72.0, y_pt * ax.figure.dpi / 72.0)))
    if hasattr(artist, "set_bbox_to_anchor"):
        artist.set_bbox_to_anchor(xy, ax.transAxes)
    else:
        artist.set_position(xy)


def text_gap_pt(ax, artist) -> float:
    """C62 fix round: the least horizontal gap (pt) between `artist` and another text of `ax` that overlaps it in
    height (a theory label beside a key reads as the key's next word); infinity where none does."""
    r = ax.figure.canvas.get_renderer()
    bb = artist.get_window_extent(r)
    gaps = [max(t.x0 - bb.x1, bb.x0 - t.x1) for t in (o.get_window_extent(r) for o in ax.texts
                                                       if o is not artist and o.get_visible() and o.get_text().strip())
            if t.y0 < bb.y1 and bb.y0 < t.y1]
    return min(gaps, default=math.inf) * 72.0 / ax.figure.dpi


def off_spine(ax, artist, near, *, others=None, min_pt: float = SPINE_CLEAR_PT, text_pt: float = 0.0) -> bool:
    """C62 fix round (the supplement's critic): re-place a key or label of common.place_key or place_label that starts
    less than `min_pt` right of the y spine (free_spot keeps only KEY_PAD_PT, 1.5 pt, from the axes edges, so such a
    label reads as touching the axis), or, with `text_pt`, that comes closer than text_pt beside a text level with it
    (text_gap_pt), on the free space nearest to `near` and nearer to them than to `others` as free_spot places it, in
    a box widened leftward by max(min_pt, text_pt) - KEY_PAD_PT and rightward by text_pt - KEY_PAD_PT, so that the
    label starts min_pt right of the spine at least and keeps text_pt from the texts beside it. Returns False, the
    label left where it was, where no such box fits."""
    if spine_gap_pt(ax, artist) >= min_pt and (text_pt <= 0.0 or text_gap_pt(ax, artist) >= text_pt):
        return True
    r = ax.figure.canvas.get_renderer()
    to_pt = 72.0 / ax.figure.dpi
    bb = artist.get_window_extent(r)
    left = max(min_pt, text_pt) - KEY_PAD_PT
    right = max(text_pt - KEY_PAD_PT, 0.0)
    spot = free_spot(ax, bb.width * to_pt + left + right, bb.height * to_pt, near, others=others, skip=(artist,))
    if spot is None:
        return False
    move_to(ax, artist, spot[0] + left, spot[1])
    return True


def rho_axis(ax) -> None:
    style.log2_axis(ax, "x", ticks=[1, 2, 4, 8, 16])
    ax.set_xlim(*RHO_XLIM)


def build_e10_adaptive(e10: Mapping, rho) -> dict:
    """Fig. 5(c)'s series and theory lines at `rho` (also sf_e10_rho (a), (b))."""
    c = e10_series(e10, "adaptive", rho, FIG5_C_KEYS)
    c["LB_T"] = e10_bound(e10, rho, "LB_T")
    c["limit"] = e10_bound(e10, rho, "limit")
    c["O1B"] = e10_bound(e10, rho, "O1B_adaptive")
    c["rho"] = rho
    return c


def limit_is_rr(blocks: Sequence[Mapping]) -> bool:
    """Whether RR-renew's ratio equals the T -> infinity limit (to 1e-12, common.agreement) at every m of either, both
    given at the same m, in every block of build_e10_adaptive (Fig. 5(c); sf_e10_rho (a), (b)): the limit's line
    then lies under RR-renew's, and its label says so."""
    for c in blocks:
        lim = dict(zip(c["limit"]["m"], c["limit"]["value"]))
        rr = dict(zip(c["rr_renew"]["m"], c["rr_renew"]["ratio"]))
        ms = sorted(set(lim) | set(rr))
        ag = agreement([rr.get(m) for m in ms], [lim.get(m) for m in ms])
        if ag is None or ag["within_pct"] != 0:
            return False
    return True


def draw_e10_adaptive_panel(ax, c: Mapping, lab: Mapping, *, env: tuple[str, str] | None = None,
                            ylabel: bool = True, label_top_pad_pt: float = 0.0) -> None:
    """RR-renew, A2 (theory r-bar) and A3 against m with LB_T (dotted), its limit (solid) and O1-B (dashed),
    labeled in a column right of the largest m so that no label is level with another line's end, theory or data
    (right_theory_lines(..., clear_ends=True); where RR-renew equals the limit, the limit's end is RR-renew's last
    point, and lab["c_limit"] says so, limit_is_rr). O1-B's leader, where it has one, ends on its flat part clear of
    the data (its last point lies under the markers)."""
    draw_e10_series(ax, c, FIG5_C_KEYS, env=env)
    specs = [dict(x=c["O1B"]["m"], y=c["O1B"]["value"], kind="upper", label=lab["c_O1B"], leader_end="flat"),
             dict(x=c["limit"]["m"], y=c["limit"]["value"], kind="limit", label=lab["c_limit"]),
             dict(x=c["LB_T"]["m"], y=c["LB_T"]["value"], kind="lower", label=lab["c_LB_T"])]
    m_axis(ax, c["LB_T"]["m"] or c["rr_renew"]["m"], [sp["label"] for sp in specs])
    lo, hi = data_range(*(c[k][f] for k in FIG5_C_KEYS for f in ("ci_lo", "ci_hi", "ratio")), c["LB_T"]["value"],
                        c["O1B"]["value"])
    ratio_log2_axis(ax, min(lo, 1.0), hi)
    # C62: the labels' own heights; `label_top_pad_pt` keeps them that far below the axes top (sf_e10_rho: its titles)
    right_theory_lines(ax, specs, clear_ends=True, measured=True, top_pad_pt=label_top_pad_pt)
    style.ygrid(ax)
    if ylabel:
        ax.set_ylabel(lab["c_y"])


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    # (b) and (c) carry a label column right of the data, (a) its one label inside: (a) gives them some width
    ax_a, ax_b, ax_c = style.panel_row(fig, PANEL_RATIOS, legend=True)

    draw_a(ax_a, data["a"], lab)
    rho_axis(ax_a)
    lo, hi = data_range(data["a"]["bound"]["max2rho"], data["a"]["random_core"]["eager_over_omega"],
                        data["a"]["trace_brackets"]["lo"], data["a"]["trace_brackets"]["hi"])
    ratio_log2_axis(ax_a, min(lo, 1.0), hi, margin_oct=0.55)
    ax_a.set_xlabel(lab["a_x"])
    ax_a.set_ylabel(lab["a_y"])
    a_direct_labels(ax_a, data["a"], lab)

    b = data["b"]
    ser = {k: {"x": b[k]["rho_star"], **{f: b[k][f] for f in ("median", "ci_lo", "ci_hi", "inc_median")}}
           for k in FIG5_B_KEYS}
    draw_e1_ratio_panel(ax_b, ser, FIG5_B_KEYS)
    # the label of max(2, rho) hangs below the line's end (first line level with it): centered there, its first line
    # would be level with A2 (theory r-bar)'s last marker above
    b_specs = [dict(x=b["bound"]["rho"], y=b["bound"]["max2rho"], kind="upper", label=lab["b_bound"],
                    first_line=True),
               dict(x=b["limit_m8"]["rho"], y=b["limit_m8"]["value"], kind="limit", label=lab["b_limit"])]
    ax_b.set_xlabel(lab["b_x"])                    # before the label column, which centers it under the data
    rho_star_axis(ax_b, b[FIG5_B_KEYS[0]]["rho_star"], b["x_range"], [sp["label"] for sp in b_specs],
                  prefer=[KINK])
    ratio_log10_axis(ax_b, *data_range(*(ser[k][f] for k in FIG5_B_KEYS for f in ("ci_lo", "ci_hi", "median")),
                                       b["bound"]["max2rho"]))
    ax_b.yaxis.set_minor_locator(NullLocator())     # C62: no comb of minor ticks between 1, 2, 5, 10, 20 (as Fig. 7)
    right_theory_lines(ax_b, b_specs, measured=True)                     # C62: the labels' own heights
    ax_b.set_ylabel(lab["b_y"])

    draw_e10_adaptive_panel(ax_c, data["c"], lab)

    for ax in (ax_a, ax_b, ax_c):
        style.ygrid(ax)
    style.panel_letters([ax_a, ax_b, ax_c])
    leg = style.legend_row(fig, list(FIG5_B_KEYS) + ["rr_renew"])
    align_baselines(leg.get_texts())        # C62: the r-bar labels (mathtext) on their plain neighbors' baseline
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
