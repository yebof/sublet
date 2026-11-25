"""sf_e3_v2: E3 on the confirmation instances, reported as measured (design/sublet_v2.md §11, W3, W4, W9; §4.4(c),
§6 H5; plan §4, part S-F).

H5 failed on its first clause (analysis.json H5), so by its registered consequence the sharing claim leaves the main
text and E3 is reported as measured, here and in the table e3_v2.tex. The figure and the table claim nothing; the copy
bound (siloed OPT <= b x shared OPT, attained on C3-P7's instance) is PROVEN, elementary (labels.status).

Inputs (versioned): code/sim/out/sublet_v2/e3/summary.json (e3.<cell>.ratios.<tag>:<mode>, the run's cost over the
cell's shared lower bound, Q39's LB, which the siloed runs take too; e3.<cell>.bracket, siloed OPT / shared OPT with its
[lo, hi] and the `open` flag of a shared MILP without a result), its manifest.json (u and mu / beta~ of the e3cell
jobs) and code/sim/out/sublet_v2/analysis.json (H5's rows: the medians and the two clauses per b). No runs/ file is
read (W10: the extract's meta.runs_files is empty). The cells b<b>:c<c> give the b levels and the config seeds, never
typed (the reduced fixtures have other ones).

Layout (W2 x 2.2 in, C41), two panels against b on log2 axes (sf_e3_util.b_axis) sharing one log2 ratio axis
(sf_e3_util.ratio_axis, ticks 1, 1.5, 2, ...) so that shared and siloed read on one scale, with the level 1 as a
reference line:
(a) shared: Sublet, Lagged RetroRenting + one-way guard (Sublet-MS4, B0 = 10% BL0a), Critical-ratio renting (A9),
    RetroRenting-style (BL5-cur) and Greedy renting (BL1), solid lines;
(b) siloed: the same policies in the sharing line style (dashed; env ("sharing", "siloed")), Sublet as its registry
    key sublet_v2_siloed (open circles, C41), the others with their own markers; siloed OPT / shared OPT as black stars
    at their b (the median of the bracket points over the seeds, the bar from the smallest lo to the largest hi; an
    open star where a seed's bracket is open; C62: at b itself, not in a dodge slot of their own, since they lie below
    every policy's point at every b), labeled "Siloed / shared OPT" on the free space nearest to them
    (common.place_label; a bare "OPT" read against the axis's shared LB is ambiguous), and the grey dashed line b,
    the copy bound on siloed OPT, which leaves through the axis top, labeled on the free space nearest to it
    (fig4_e7_e3.place_theory_label).
Each point is the median over the config seeds with the registered week bootstrap's 95% interval
(ms5b_common.bootstrap_median_ci, seed 20261031, 10,000 resamples, imported read-only; W9: the statistic of §4.5,
here over the four seeds, which are instances, not weeks), dodged in x by sf_e3_util.DODGE_OCT_E3 (the same five slots
in both panels) and drawn in two passes (ms4_lib.draw_series_layered: lines, then bars and markers above every line).
With four seeds that interval is the range over the seeds in every cell of the confirmation; the extract's
bootstrap.ci_equals_range says whether it is in every cell, and the caption and the table then call it the range
(print check of 2026-11-03). The panel titles name the replica mode on the letters' baseline at the caption size
(ms5b_e7_lib.caption_title).
The key (C62): the six keys drawn, registry labels (sublet_ms4's on two lines, split before its parenthesis,
ms4_lib.wrap_wide), in two columns in the upper left of (a), which the shared ratio axis leaves empty above the shared
costs (a figure legend anchored at (a), `_sublet_role` "key"); the shared y axis reaches high enough that the key
clears every point and bar of (a) by KEY_CLEAR_PT (key_headroom). As built until C62, a legend in two rows above the
panels took 0.48 in of the 2.2-in height at 9 pt (one row needs 9 in); inside (a) it frees that height for the data.

Table e3_v2.tex (TABLES; written by the after hook from the extract's `tables`, so --from-extract rewrites it; it needs
booktabs and array, for its wrapped policy column): per policy and mode a row of medians over the seeds and a row of
their 95% intervals, per b (a label with a parenthesis, sublet_ms4's, is split before it: the name on the median row,
the parenthesis on the interval row below, so that no wrapped name pushes an interval row away from its medians);
the OPT brackets; and H5's two clauses per b from analysis.json (H5.b.<i>.le_MS4 and shared_below_siloed; the second
is tested at b >= 2 only and reads "--" at b = 1), labeled "reported as measured".
Its scope (tags, modes, b, seeds, the summary's cells b<b>:c<c>, u, mu) is in tables.e3_v2.scope; tex_label, tex_f,
tex_iv and verdict serve the other U39b scripts' tables too.

The caption draft (labels.caption) reads every count and level from the inputs. Run from code/sim:
python -m figs.supp.sf_e3_v2 [--from-extract [JSON]] (figs.common.cli).

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): the table's caption says "the main text claims
no measured sharing gain for any policy" for "no sharing claim enters the main text", which Section VII-C's
Proposition 5 paragraph contradicted.
"""
from __future__ import annotations

import math
import re
import sys
from typing import Any, Mapping, Sequence

import matplotlib as mpl
import numpy as np

from figs import style
from figs.common import MissingKey, cli, finite, need, place_label, points_pt, write_table
from figs.fig4_e7_e3 import place_theory_label
from figs.inputs import Inputs
from figs.supp.ms4_lib import centered_dash_pairs, draw_series_layered, drop_idle_halos, wrap_wide
from figs.supp.ms5b_e7_lib import caption_title
from figs.supp.sf_e3_util import DODGE_OCT_E3, b_axis, ratio_axis
from figs.supp.sf_e7_mix import _num, _tex_text
from sublet.experiments.ms5b_common import BOOT_B, BOOT_SEED, bootstrap_median_ci

NAME = "sf_e3_v2"
E3 = "code/sim/out/sublet_v2/e3/summary.json"
MANIFEST = "code/sim/out/sublet_v2/e3/manifest.json"
ANALYSIS = "code/sim/out/sublet_v2/analysis.json"
KEYS = style.SUPP_POLICIES_MS5B[NAME]          # sublet_v2, sublet_v2_siloed, sublet_ms4, a9, bl5_cur, bl1, opt
TAG_KEY = {"Sublet": "sublet_v2", "Sublet-MS4": "sublet_ms4", "A9": "a9", "BL5-cur": "bl5_cur", "BL1": "bl1"}
MODES = ("shared", "siloed")
SILOED_KEY = {"sublet_v2": "sublet_v2_siloed"}  # a registry key of its own (C41); the others: the sharing line style
# dodge slots, left to right, and the drawing order (Sublet last, above the others)
SLOTS = ("sublet_ms4", "bl5_cur", "sublet_v2", "a9", "bl1")
DRAW = ("bl1", "bl5_cur", "a9", "sublet_ms4", "sublet_v2")
TABLES = ("e3_v2.tex",)
NAME_COL = "4.7cm"                              # the table's policy column (needs the array package): holds the
#                                                 longest name stem, sublet_ms4's 128.5 pt, on one line (split_label)
LABEL_BREAK = " ("                              # a table label is split here (split_label)
CELL_RE = re.compile(r"^b(\d+):c(\d+)$")
style.register_supplementary(NAME, "W2", 2.2)
COPY_STATUS = "PROVEN, elementary"              # the copy bound's status label (W3), copied into the caption
KEY_NCOL = 2                                    # C62: the key's columns, in (a) (draw_key)
KEY_INSET_PT = (2.0, 0.5)                       # C62: the key's upper left corner this far right of (a)'s y spine
#                                                 and below its top (pt)
KEY_PAD_EM = 0.3                                # C62: the key's white box (no edge) reaches this far beyond its
#                                                 entries (em), so that the y grid line at the top tick stops at it
KEY_CLEAR_PT = 4.0                              # C62: the least gap between the key and a point or bar under it
# C62: the titles name the replica mode, the x label the paper's symbol; "b" in the line's label in italics as well
LABELS = {"x": "Borrowers per LLM, $b$", "y": "Cost / shared LB",
          "titles": {"shared": "Shared replicas", "siloed": "Siloed replicas"},
          "theory_forms": ["$b$, bound on\nsiloed OPT", "$b$, bound\non OPT"], "opt": "Siloed / shared OPT",
          "status": {"copy bound siloed OPT <= b x shared OPT, attained on C3-P7's instance": COPY_STATUS,
                     "H5": "failed (registered consequence: E3 reported as measured, no sharing claim in the main "
                           "text)"}}


# ---------------------------------------------------------------------------------------------------------------
# inputs
def cells_of(e3: Mapping) -> dict:
    """{cell: (b, config seed)} of the summary's e3 block (cells b<b>:c<c>)."""
    out = {}
    for cell in need(e3, "e3", what=E3):
        m = CELL_RE.match(cell)
        if m is None:
            raise MissingKey(f"{E3}: e3 cell {cell!r} is not of the form b<b>:c<c>")
        out[cell] = (int(m.group(1)), int(m.group(2)))
    if not out:
        raise MissingKey(f"{E3}: the e3 block has no cell")
    return out


def one_level(man: Mapping, field: str) -> float:
    """The single value of params.<field> over the manifest's e3cell jobs (u, mu)."""
    vals = {float(j["params"][field]) for j in need(man, "jobs", what=MANIFEST)
            if (j.get("params") or {}).get("kind") == "e3cell"}
    if len(vals) != 1:
        raise MissingKey(f"{MANIFEST}: the e3cell jobs have {sorted(vals)} as {field}, not one value")
    return vals.pop()


def boot(values: Sequence[float]) -> dict:
    """{median, ci_lo, ci_hi, n} by the registered bootstrap (ms5b_common.bootstrap_median_ci; W9)."""
    r = bootstrap_median_ci(values)
    lo, hi = r["ci"]
    return {"median": r["median"], "ci_lo": lo, "ci_hi": hi, "n": r["n"]}


def series(e3: Mapping, cells: Mapping, tag: str, mode: str, bs: Sequence[int], seeds: Sequence[int]) -> dict:
    """{b, median, ci_lo, ci_hi, n, values, note} of tag:mode against b; a b without values has null points."""
    s = {"b": [], "median": [], "ci_lo": [], "ci_hi": [], "n": [], "values": [], "note": []}
    for b in bs:
        vals = []
        for c in seeds:
            v = ((e3["e3"].get(f"b{b}:c{c}") or {}).get("ratios") or {}).get(f"{tag}:{mode}")
            if v is not None:
                vals.append(float(v))
        p = boot(vals) if vals else {"median": None, "ci_lo": None, "ci_hi": None, "n": 0}
        for f in ("median", "ci_lo", "ci_hi", "n"):
            s[f].append(p[f])
        s["b"].append(b)
        s["values"].append(vals)
        s["note"].append(None if vals else "no run")
    return s


def brackets(e3: Mapping, bs: Sequence[int], seeds: Sequence[int]) -> dict:
    """Siloed OPT / shared OPT per b: the median of the seeds' bracket points, the smallest lo and the largest hi, and
    whether a seed's bracket is open (a shared MILP without a result)."""
    o = {"b": [], "point": [], "lo": [], "hi": [], "open": [], "n": [], "per_seed": []}
    for b in bs:
        ents = [(c, (e3["e3"].get(f"b{b}:c{c}") or {}).get("bracket")) for c in seeds]
        ents = [(c, e) for c, e in ents if isinstance(e, Mapping) and e.get("point") is not None]
        o["b"].append(b)
        o["point"].append(float(np.median([e["point"] for _, e in ents])) if ents else None)
        los = [e["lo"] for _, e in ents if e.get("lo") is not None]
        his = [e["hi"] for _, e in ents if e.get("hi") is not None]
        o["lo"].append(min(los) if los else None)
        o["hi"].append(max(his) if his else None)
        o["open"].append(any(bool(e.get("open")) for _, e in ents))
        o["n"].append(len(ents))
        o["per_seed"].append({f"c{c}": {k: e.get(k) for k in ("point", "lo", "hi", "open", "exact")} for c, e in ents})
    return o


def h5_rows(an: Mapping, bs: Sequence[int]) -> dict:
    """H5's rows per b (analysis.json H5.b) with its kind and verdict; clause (ii) is tested at b >= 2 only."""
    h5 = need(an, "H5", what=ANALYSIS)
    by = {int(r["b"]): r for r in need(h5, "b", what=f"{ANALYSIS} H5")}
    rows = []
    for b in bs:
        r = by.get(b) or {}
        rows.append({"b": b, "le_MS4": r.get("le_MS4"),
                     "shared_below_siloed": r.get("shared_below_siloed") if b >= 2 else None,
                     "Sublet_shared": r.get("Sublet_shared"), "Sublet_MS4_shared": r.get("Sublet_MS4_shared"),
                     "Sublet_siloed": r.get("Sublet_siloed")})
    return {"kind": h5.get("kind"), "pass": h5.get("pass"), "seeds": h5.get("seeds"), "rows": rows,
            "failed_b": [r["b"] for r in rows if r["le_MS4"] is False or r["shared_below_siloed"] is False]}


def interval_text(d: Mapping) -> str:
    """What the second number of a point is: the range over the seeds where the registered bootstrap's 95% interval
    equals it in every cell (bootstrap.ci_equals_range), else that interval."""
    if d["bootstrap"].get("ci_equals_range"):
        return "the range over the seeds (the registered bootstrap's 95% interval, equal to the range in every cell)"
    return "the registered bootstrap's 95% interval"


def caption(d: Mapping) -> str:
    """The caption draft (W3, W4): scope, encoding and H5's outcome, every number read from the inputs."""
    g = d["grid"]
    fail = d["h5"]["failed_b"]
    fails = ("H5 failed at b = " + ", ".join(str(b) for b in fail)) if fail else "H5 held at every b"
    seeds = g["seeds"]
    ms4 = style.POLICIES["sublet_ms4"].label.split(LABEL_BREAK)[0]
    return (f"The sharing study on its confirmation instances, reported as measured ({fails}): cost over the "
            f"shared lower bound "
            f"against the borrowers per LLM b (u = {g['u']:g}, mu/beta~ = {g['mu']:g}, one day), (a) shared and (b) "
            f"siloed replicas (dashed). Each point is the median over {len(seeds)} config seed"
            f"{'s' if len(seeds) != 1 else ''} ({', '.join(str(c) for c in seeds)}) with {interval_text(d)}; "
            f"intervals narrower than a marker are hidden by it, and every one is in Table e3_v2. {ms4}: the lagged "
            f"RetroRenting-style rule in the one-way guard at B0 = 10% of all-fallback. Stars: siloed OPT / shared "
            f"OPT (the median of the seeds' bracket points, with the bracket ends over the seeds); grey: b, the copy "
            f"bound on siloed OPT (each borrower can copy the whole shared plan), attained on C3-P7's instance "
            f"({COPY_STATUS}).")


def build(inp: Inputs) -> dict:
    e3, man, an = inp.json(E3), inp.json(MANIFEST), inp.json(ANALYSIS)
    meta = need(e3, "meta", what=E3)
    tags = need(meta, "tags", what=E3)
    missing = [t for t in TAG_KEY if t not in tags]
    if missing:
        raise MissingKey(f"{E3}: meta.tags lacks {missing}")
    cells = cells_of(e3)
    bs = sorted({b for b, _ in cells.values()})
    seeds = sorted({c for _, c in cells.values()})
    grid = {"b": bs, "seeds": seeds, "u": one_level(man, "u"), "mu": one_level(man, "mu"), "cells": sorted(cells)}
    panels = {m: {TAG_KEY[t]: {"tag": t, **series(e3, cells, t, m, bs, seeds)} for t in TAG_KEY} for m in MODES}
    opt = brackets(e3, bs, seeds)
    h5 = h5_rows(an, bs)
    cells_iv = [(s["ci_lo"][i], s["ci_hi"][i], s["values"][i]) for p in panels.values() for s in p.values()
                for i in range(len(bs)) if s["values"][i]]
    d = {"grid": grid, "panels": panels, "opt": opt, "h5": h5, "tag_key": dict(TAG_KEY),
         "bootstrap": {"seed": BOOT_SEED, "B": BOOT_B, "rule": "ms5b_common.bootstrap_median_ci over the config seeds",
                       "ci_equals_range": bool(cells_iv) and all(lo == min(v) and hi == max(v)
                                                                 for lo, hi, v in cells_iv)},
         "labels": dict(LABELS),
         "meta": {"git_revision": {"e3": meta.get("git_revision"),
                                   "analysis": (an.get("meta") or {}).get("git_revision")},
                  "reduced": bool(meta.get("reduced")), "sources": list(inp.sources), "runs_files": []}}
    d["tables"] = {"e3_v2": {"file": TABLES[0], "scope": {"tags": list(TAG_KEY), "modes": list(MODES), "b": bs,
                                       "seeds": [f"c{c}" for c in seeds], "cells": sorted(cells),
                                       "u": grid["u"], "mu": grid["mu"]}}}
    d["labels"]["caption"] = caption(d)
    return d


# ---------------------------------------------------------------------------------------------------------------
# figure
def key_of(key: str, mode: str) -> tuple[str, tuple | None]:
    """The drawn registry key and line style of a policy's series in a mode."""
    if mode == "shared":
        return key, None
    return SILOED_KEY.get(key, key), ("sharing", "siloed")


def draw_panel(ax, block: Mapping, mode: str, n: int) -> list[float]:
    """The five policies of `block` dodged into SLOTS (n slots), drawn in DRAW's order in two passes
    (ms4_lib.draw_series_layered); returns the values drawn."""
    ser = []
    for key in DRAW:
        k, env = key_of(key, mode)
        ser.append((k, block[key], SLOTS.index(key), env))
    draw_series_layered(ax, ser, "b", n=n, oct_=DODGE_OCT_E3)
    return [v for key in DRAW for f in ("median", "ci_lo", "ci_hi") for v in block[key][f] if v is not None]


def opt_x(o: Mapping, n: int) -> np.ndarray:
    """The stars' x: b itself (C62; as built until then the last of n + 1 dodge slots, right of every policy's). The
    stars lie below every policy's point at every b, so they need no slot of their own; `n` is kept for the callers."""
    return finite(o["b"])


def draw_opt(ax, o: Mapping, n: int) -> list[float]:
    """Siloed OPT / shared OPT: black stars with their brackets in the last dodge slot; an open star where open."""
    x = opt_x(o, n)
    y, lo, hi = finite(o["point"]), finite(o["lo"]), finite(o["hi"])
    ok = np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi)
    z = style.Z_SUBLET + 0.12
    if ok.any():
        style.errorbars(ax, "opt", x[ok], y[ok], lo[ok], hi[ok], zorder=z)
    shut = np.isfinite(y) & ~np.asarray(o["open"], dtype=bool)
    if shut.any():
        style.scatter_policy(ax, "opt", x[shut], y[shut], zorder=z + 0.01)
    opened = np.isfinite(y) & np.asarray(o["open"], dtype=bool)
    if opened.any():
        style.scatter_policy(ax, "opt", x[opened], y[opened], markerfacecolor="white", label="_nolegend_",
                             zorder=z + 0.01)
    return [v for v in np.concatenate([y, lo, hi]) if np.isfinite(v)]


def draw_key(fig, ax):
    """C62: the key of the six keys drawn, in KEY_NCOL columns (registry labels in the legend order, read down the
    columns; sublet_ms4's on two lines, ms4_lib.wrap_wide; dashed samples centered on their handles,
    ms4_lib.centered_dash_pairs), a figure legend on a white box without an edge (KEY_PAD_EM; the y grid line at the
    top tick stops at it) with its upper left corner KEY_INSET_PT inside (a)'s upper left corner."""
    keys = ["sublet_v2", "sublet_v2_siloed"] + [k for k in KEYS if k not in ("sublet_v2", "sublet_v2_siloed", "opt")]
    pairs = centered_dash_pairs(wrap_wide(fig, style.policy_handles(keys)), mpl.rcParams["legend.handlelength"])
    h, t = zip(*pairs)
    x0, y0, w, hh = style.axes_rect_in(ax)
    W, H = (float(v) for v in fig.get_size_inches())
    dx, dy = (v / style.BP_PER_IN for v in KEY_INSET_PT)
    leg = fig.legend(list(h), list(t), loc="upper left", bbox_to_anchor=((x0 + dx) / W, (y0 + hh - dy) / H),
                     bbox_transform=fig.transFigure, ncol=KEY_NCOL, frameon=True, fancybox=False, shadow=False,
                     facecolor="white", edgecolor="none", framealpha=1.0, borderaxespad=0.0, borderpad=KEY_PAD_EM,
                     handler_map=dict(style.PAIR_HANDLER_MAP))
    leg.get_frame().set_linewidth(0.0)
    leg._sublet_role = "key"
    return leg


def key_headroom(ax, leg) -> None:
    """C62: raise the top of (a)'s log2 y axis (shared with (b)) so that the key's lower edge clears every marker, bar
    and line point of (a) under its width by KEY_CLEAR_PT (the key's depth below the axes top is fixed in inches, so
    its lower edge sits at a fixed share of the axes height: each point (log2 value v, its marker's radius rad in pixels)
    needs (v - lo) / (hi - lo) * H + rad + clear <= (1 - f) * H, H the axes height and f the key's depth over H);
    StyleError where the key does not fit the panel's width or height."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    bb, ab = leg.get_window_extent(r), ax.get_window_extent(r)
    if bb.x1 > ab.x1 + 0.5:
        raise style.StyleError(f"{NAME}: the key ({bb.width / fig.dpi:.2f} in) is wider than (a)")
    px = fig.dpi / 72.0
    x_right = ax.transData.inverted().transform((bb.x1, ab.y0))[0]
    pts = []                                         # (log2 value, radius in pixels) of every mark under the key
    for ln in ax.lines:
        if getattr(ln, "_sublet_role", "") not in ("markers", "") or not len(ln.get_xdata()):
            continue
        rad = 0.5 * (ln.get_markersize() + ln.get_markeredgewidth()) if ln.get_marker() not in ("None", None) else 0
        pts += [(math.log2(y), rad * px) for x, y in ln.get_xydata()
                if np.isfinite(x) and np.isfinite(y) and y > 0 and x <= x_right]
    for c in ax.collections:                         # the interval bars (errorbar's LineCollections)
        for seg in getattr(c, "get_segments", lambda: [])():
            pts += [(math.log2(y), 0.0) for x, y in seg if x <= x_right and y > 0]
    y0, y1 = ax.get_ylim()
    lo, hi = math.log2(y0), math.log2(y1)
    H = ab.height
    room = (bb.y0 - ab.y0) / H                       # the key's lower edge, as a share of the axes height
    span = hi - lo
    for v, rad in pts:
        free = room - (rad + KEY_CLEAR_PT * px) / H
        if free <= 0.0:
            raise style.StyleError(f"{NAME}: the key leaves no room for the data under it in (a)")
        span = max(span, (v - lo) / free)
    if span > hi - lo + 1e-12:
        ax.set_ylim(y0, 2.0 ** (lo + span))


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    ax_a, ax_b = style.panel_row(fig, (1, 1), sharey=(False, True))
    bs = [float(b) for b in data["grid"]["b"]]
    n = len(SLOTS)                                   # C62: the same five slots in both panels (opt_x)
    vals = draw_panel(ax_a, data["panels"]["shared"], "shared", n)
    vals += draw_panel(ax_b, data["panels"]["siloed"], "siloed", n)
    vals += draw_opt(ax_b, data["opt"], n)
    _, txt = style.theory_line(ax_b, bs, bs, "upper", lab["theory_forms"][0])
    for ax in (ax_a, ax_b):
        b_axis(ax, bs, n)
        ax.set_xlabel(lab["x"])
    vals = [v for v in vals if v > 0] or [1.0]
    ratio_axis(ax_a, min(min(vals), 1.0), max(max(vals), 1.0))
    ax_a.set_ylabel(lab["y"])
    for ax in (ax_a, ax_b):
        style.reference_line(ax, y=1.0)
        style.ygrid(ax)
    key_headroom(ax_a, draw_key(fig, ax_a))
    place_theory_label(ax_b, txt, bs, bs, lab["theory_forms"])
    label_opt(ax_b, data["opt"], n, lab["opt"])
    drop_idle_halos(ax_b, [txt])                     # C62: the line's label as text in the PDF where it masks nothing
    letters = style.panel_letters([ax_a, ax_b])
    for ax, letter, m in zip((ax_a, ax_b), letters, MODES):
        caption_title(ax, letter, lab["titles"][m])
    return fig


def label_opt(ax, o: Mapping, n: int, text: str):
    """The stars' label (black) on the free space nearest to them and nearer to them than to any policy's points
    (common.place_label); StyleError where it fits nowhere."""
    y = finite(o["point"])
    x = opt_x(o, n)
    ok = np.isfinite(x) & np.isfinite(y)
    near = points_pt(ax, x[ok], y[ok])
    others = [points_pt(ax, ln.get_xdata(), ln.get_ydata()) for ln in ax.lines
              if getattr(ln, "_sublet_policy", "opt") != "opt"]
    others = np.concatenate(others) if others else None
    t = place_label(ax, text, near, others=others, color="black")
    if t is None:
        raise style.StyleError(f"{NAME} (b): the stars' label {text!r} fits nowhere on the free space")
    drop_idle_halos(ax, [t])                       # text in the PDF where its halo would mask nothing
    return t


# ---------------------------------------------------------------------------------------------------------------
# table (tex_label, tex_f, tex_iv and verdict are shared with the other U39b scripts)
def split_label(label: str) -> tuple[str, str]:
    """(stem, rest) of a registry label split before its first parenthesis (LABEL_BREAK); rest '' where it has none."""
    stem, sep, rest = str(label).partition(LABEL_BREAK)
    return (stem, "(" + rest) if sep else (stem, "")


def tex_label(label: str) -> str:
    """A registry label in LaTeX: its $...$ parts kept as math (mathtext and LaTeX share them, C41), the text between
    them escaped (sf_e7_mix._tex_text)."""
    parts = re.split(r"(?<!\\)\$", str(label))
    if len(parts) % 2 == 0:
        raise style.StyleError(f"unbalanced $ in the label {label!r}")
    return "".join(f"${p}$" if i % 2 else _tex_text(p) for i, p in enumerate(parts))


def tex_f(v, fmt: str = ".3f") -> str:
    return _num(v, fmt)


def tex_iv(lo, hi, fmt: str = ".3f") -> str:
    return "--" if lo is None or hi is None else f"[{_num(lo, fmt)}, {_num(hi, fmt)}]"


def verdict(v) -> str:
    """'holds', 'fails', or '--' where the clause is not tested."""
    return "--" if v is None else ("holds" if v else "fails")


def _bs_text(bs: Sequence[int]) -> str:
    return ", ".join(str(b) for b in bs)


def e3_tex(d: Mapping) -> str:
    """e3_v2.tex: per policy and mode the medians over the seeds and their 95% intervals, per b; the OPT brackets;
    H5's two clauses per b (reported as measured)."""
    g, h5 = d["grid"], d["h5"]
    bs = g["b"]
    seeds = ", ".join(str(c) for c in g["seeds"])
    ns = len(g["seeds"])
    f1 = [r["b"] for r in h5["rows"] if r["le_MS4"] is False]
    f2 = [r["b"] for r in h5["rows"] if r["shared_below_siloed"] is False]
    outcome = "; ".join(t for t in ((f"clause (i) fails at $b={_bs_text(f1)}$" if f1 else ""),
                                    (f"clause (ii) fails at $b={_bs_text(f2)}$" if f2 else "")) if t)
    cols = r"@{}>{\raggedright\arraybackslash}p{" + NAME_COL + "}l" + "r" * len(bs) + "@{}"
    iv = interval_text(d).replace("95%", r"95\%")
    lines = [r"\begin{table*}[t]",
             # C59 (RC19(3)): the experiment by its name (as built "E3")
             r"\caption{The sharing study on its confirmation instances, reported as measured: cost over the shared "
             r"lower bound per "
             r"policy and replica mode against the borrowers per LLM $b$ ($u=" + f"{g['u']:g}" + r"$, "
             r"$\mu/\tilde\beta=" + f"{g['mu']:g}" + r"$, one day), medians over " + f"{ns} config seed"
             + ("s" if ns != 1 else "") + f" ({seeds})" + r" with, on the second line, " + iv + r"; siloed "
             r"OPT over shared OPT (the median of the brackets' points, from the smallest lower to the largest upper "
             r"end); and H5's two clauses as registered: (i) Sublet's shared median is at most that of the lagged "
             r"RetroRenting-style rule in the one-way guard at $B_0=10\%$ of all-fallback, (ii) Sublet's shared "
             r"median is below its siloed one (tested at $b\geq2$). "
             + (f"H5 failed ({outcome}); by its registered consequence the sharing study is reported as measured, "
                f"and the main text "
                r"claims no measured sharing gain for any policy.}" if outcome else r"H5 held.}"),   # C50 (D5 review)
             r"\label{tab:e3-v2}", r"\centering\footnotesize", r"\setlength{\tabcolsep}{3.4pt}",
             r"\begin{tabular}{" + cols + "}", r"\toprule",
             "Policy & Replicas & " + " & ".join(f"$b={b}$" for b in bs) + r" \\", r"\midrule"]
    first = True
    for key in TAG_KEY.values():
        stem, rest = split_label(style.POLICIES[key].label)
        for m in MODES:
            s = d["panels"][m][key]
            name, under = (tex_label(stem), tex_label(rest) if rest else "") if m == "shared" else ("", "")
            if not first and m == "shared":
                lines.append(r"\addlinespace[2pt]")
            first = False
            lines.append(f"{name} & {m} & " + " & ".join(tex_f(v) for v in s["median"]) + r" \\")
            lines.append(f"{under} &  & " + " & ".join(tex_iv(lo, hi) for lo, hi in zip(s["ci_lo"], s["ci_hi"]))
                         + r" \\")
    o = d["opt"]
    lines += [r"\midrule",
              r"Siloed OPT / shared OPT &  & " + " & ".join(tex_f(v) for v in o["point"]) + r" \\",
              r" &  & " + " & ".join(tex_iv(lo, hi) for lo, hi in zip(o["lo"], o["hi"])) + r" \\",
              r"\midrule",
              r"\multicolumn{2}{@{}l}{H5 (i), reported as measured} & "
              + " & ".join(verdict(r["le_MS4"]) for r in h5["rows"]) + r" \\",
              r"\multicolumn{2}{@{}l}{H5 (ii), reported as measured} & "
              + " & ".join(verdict(r["shared_below_siloed"]) for r in h5["rows"]) + r" \\",
              r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    return "\n".join(lines)


def write_tables(data: Mapping, report: Mapping) -> None:
    head = f"% Written by code/sim/figs/supp/{NAME}.py from {E3} and {ANALYSIS}; do not edit.\n"
    p = write_table(TABLES[0], head + e3_tex(data))
    print(f"[{NAME}] wrote {p}")


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
