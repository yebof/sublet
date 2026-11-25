"""sf_stress_ms7: the stress regimes of the MS7 baseline study (X5) on the confirmation weeks, with the tables
e7r_modes.tex and e7r_stress.tex (design/ms7/w_spec.md §4, unit W-G4 B; design/ms7/registration.md §2 and §3, X4 and
X5; design/ms7/plan.md X5; change C58).

Claims: none of its own. Every number is read from the registered analysis of the baseline study (e7r_analysis.py, its
sha256 in design/ms7/registration.md): medians and min-max over weeks, counts of weeks, no interval and no p-value
(design/ms7/plan.md D4; registration §3).

Figure (W2 x 2.5 in, C58 block B). One question: how does each policy's cost grow with the reclaim rate of the i.i.d.
lender, from the rates converted from SpotLake's interruption fractions to the stress rates of the confirmation? The
analysis's i.i.d. stress-intensity curve of each policy of the set (SUPP_POLICIES_MS7[NAME], fourteen keys: Sublet,
critical-ratio renting, protected-only critical-ratio renting, the seven primary baselines and the four notice-aware
policies; critical-ratio planning and the k* ablation are in the tables only) at its points p (the analysis's intensity
block, p = 0 being the honoring lender L-hon; {0, 0.0005, 0.002, 0.0124, 0.05, 0.2} in the runs, read from the data):
the median over the weeks of r0 at each p, with its min-max over the weeks as a bar. Three panels (GROUPS): (a) greedy
renting and its variants, (b) RetroRenting-style and its variants, (c) critical-ratio renting, protected-only renting
and the other primary baselines; Sublet is drawn in every panel. Every series is named at its curve's right end
(end_labels, C62: in place of each panel's legend, which took four or five rows over the data): its registry label
(split once at a space where wider than LABEL_WRAP_IN) in a label column right of the data, as near to the height of
its last median as a column of labels allows, with a thin leader where it sits off that height; the panels' data parts
share one width and one x scale, and each label column is as wide as its labels (layout).
The p axis is logarithmic with p = 0 drawn left of a break (ZERO_DECADES below the least positive p); the series of a
panel are offset horizontally (DODGE_PT) so that equal medians stay apart; the grey line marks all-fallback (cost 1);
a light y grid (style.ygrid) ends with the x spine, so that the label columns hold no line.
The regional and peak-aligned lenders, W0+ and every tag under every lender are in the tables (and in sf_bl_ms7's
figure and tables, which draw W0+ and the margins).

As built (choices that w_spec §4 leaves open):
* The y axis is shared and spans the data (C62: as built until C62 it reached high enough that no point or bar lay
  under a legend, as sf_e7_intensity.headroom).
* labels.caption is a caption draft with every count, week and grid point read from the inputs.
* The label column right of the largest p (final render, C58: Sublet's label alone; C62: every series' label): the x
  spine ends a pad right of the largest p, so the column reads as a label column, and the decades are ticked up to the
  largest p only. The panel titles are at the caption size (style.LABEL_PT, C62) on their letters' baseline
  (ms7_e7r_lib.title).

Tables (after hook, figs.common.write_table: SUBLET_FIGS_TABLES_DIR, else SUBLET_FIGS_PDF_DIR when set, else
paper/supplement/tables/), from the extract's `tables`, so --from-extract rewrites them; each entry carries a `scope`:
  e7r_modes.tex   every tag of the analysis under every lender mode it ran (the analysis's tags.<tag>.r0: the
                  confirmation's seven lenders and the six new ones, thirteen in the runs): the median over the weeks
                  of r0 and, on a second row, its min-max; a W setting equal to its T setting (an alias, one run) is
                  a row that says so; the per-run values are in sf_bl_ms7's data file baseline_study_runs.csv;
  e7r_stress.tex  every tag: for a tag run under every lender of the intensity grid (not the oracle forecast, run
                  under L-tr and L-hon only: '--'), the number of weeks whose first p with r0 > 1 is each p of the
                  grid, or that reach no p with r0 > 1 (a dagger on the policy where a point before the crossing has
                  no run), and
                  the lender at which W0+ is reached, with its number of weeks (per week the largest r0 over the
                  analysis's W0+ modes, ties to the first in that order, as ms7_baselines.w0plus_of); the caption has
                  the equivalence of the adaptive and the eager lender that puts the adaptive lender into W0+ (the
                  analysis's check (iii)).
Every table is a longtable (ms5b_e7_lib.longtable: one-column mode, "Table <n>, continued").

Inputs (RUN_INPUTS; figs.inputs, so SUBLET_FIGS_IN_ROOT redirects them): code/sim/out/e7r/analysis.json, an MS7 run
output copied in after the runs (figs/rebuild.py keeps the entry pending until then). A missing input stops the script
with exit code 2 and the file named; input from a reduced (smoke) run is never written into paper/ or
code/sim/out/figs/ (ms7_e7r_lib.guard_reduced). Run from code/sim: python -m figs.supp.sf_stress_ms7
[--from-extract [JSON]].
"""
from __future__ import annotations

import math
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.ticker import FixedFormatter, FixedLocator

from figs import style
from figs.common import (KEY_PAD_PT, LEADER_PT, LEVEL_PT, MissingKey, cli, need, stack_labels, text_width_in,
                         write_table)
from figs.inputs import Inputs
from figs.supp import ms5b_e7_lib as L
from figs.supp import ms7_e7r_lib as E
from figs.supp.ms4_lib import center_xlabel, line_casing

NAME = "sf_stress_ms7"
KEYS = style.SUPP_POLICIES_MS7[NAME]
TABLES = ("e7r_modes.tex", "e7r_stress.tex")
RUN_INPUTS = (E.ANALYSIS,)
INPUTS = RUN_INPUTS
style.register_supplementary(NAME, "W2", 2.5)
REF = "sublet_v2"
GROUPS = (("a", "Greedy variants", ("bl1", "bl1_bo", "bl1n", "bl1_gp")),
          ("b", "RetroRenting variants", ("bl5_cur", "bl5_lag", "bl5_tau60", "bl5n")),
          ("c", "Other policies", ("a9", "a9p", "bl2", "bl3_0", "bl4")))
if sorted({REF, *(k for _, _, ks in GROUPS for k in ks)}) != sorted(KEYS):
    raise style.StyleError(f"{NAME}: the panels' keys must be SUPP_POLICIES_MS7[{NAME!r}]")
ZERO_DECADES = 0.75             # p = 0 is drawn this many decades left of the least positive p
BREAK_DECADES = 0.32            # ... and the axis break between them this far right of it
X_PAD_DEC = 0.22                # the x axis beyond the outermost points (decades)
DODGE_PT = 1.4                  # x offset between neighboring series of a panel
Y_STEPS = (0.05, 0.1, 0.2, 0.25, 0.5, 1.0)
Y_MIN_TICKS, Y_MAX_TICKS = 3, 6
Y_PAD = 0.04
# C62: every series named at its curve's right end (end_labels), in place of the panels' legends, which took the top
# 0.75 in of each panel (four or five rows over the data) and left the curves 1.2 in of height
LABEL_WRAP_IN = 0.85            # an end label wider than this is split once at a space (end_name)
END_RUN_PT = 9.0                # the label column starts this far right of the end markers' reach (a leader's run)
END_MARK_GAP_PT = 2.0           # each label is its series' marker, then this gap, then its name (the series told
#                                 apart where two curves end at one height, and in greyscale)
END_EDGE_PT = KEY_PAD_PT + 1.0  # ... and ends this far left of the panel's right edge
LABEL_GAP_PT = 2.0              # between two end labels of a column
LEADER_GAP_PT = 1.0             # a leader ends this far left of its label
Z_BARS = style.Z_SUBLET + 0.05
Z_MARKS = style.Z_SUBLET + 0.1
Z_STEP = 0.1
LABELS = {"x": "i.i.d. lender: reclaim probability $p$ per site and slot (logarithmic; $p=0$ left of the break)",
          "y": "Cost / all-fallback",
          "caption": ("I.i.d.\\ stress-intensity curves on weeks {weeks} ({n_weeks} week{s}, policy seed 0): the cost "
                      "over all-fallback of {n_keys} policies, Sublet, critical-ratio renting, protected-only "
                      "renting, the primary baselines and the notice-aware policies, against the reclaim probability "
                      "$p$ of the i.i.d.\\ lender per site and slot, "
                      "$p\\in\\{{{grid}\\}}$; $p=0$ is the honoring lender L-hon, drawn left of the break, and "
                      "{spot} convert SpotLake's interruption fractions to a constant hazard per site-slot (a derived "
                      "conversion). Medians over the weeks, bars min--max. Sublet is drawn in every panel, and each "
                      "curve is named at its right end; the grey line marks all-fallback; the series of a panel are "
                      "offset horizontally by "
                      "{dodge}~pt. {flat}Every policy under every lender, critical-ratio planning, its ablation with the "
                      "$k^{{\\ast}}$ contract and the regional and peak-aligned lenders included: "
                      "Table~\\ref{{tab:e7r-modes}}; the first crossing of all-fallback and the lender of "
                      "$W_0^{{+}}$: Table~\\ref{{tab:e7r-stress}}."),
          "flat": "Protected-only renting holds no revocable lease, so its cost is the same at every $p$. "}
SPOT_P = (0.0005, 0.002)        # the rates converted from SpotLake (ms7_baselines.MODE_NOTES; Supplement S-E.8)


def _fmt_p(p) -> str:
    return format(float(p), "g")


# ---------------------------------------------------------------------------------------------------------------
# data
def build(inp: Inputs) -> dict:
    an = E.read(inp, E.ANALYSIS, NAME)
    weeks = E.check_weeks(an, E.ANALYSIS)
    tags = need(an, "tags", what=E.ANALYSIS)
    meta = an.get("meta") or {}
    pts = [(float(p), m) for p, m in need(meta, "intensity_points", what=E.ANALYSIS)]
    series = {}
    for key in KEYS:
        tag = E.TAG_OF_KEY[key]
        it = need(tags, tag, "intensity", what=E.ANALYSIS)
        by_p = need(it, "by_p", what=f"{E.ANALYSIS} tags.{tag}.intensity")
        s = {"tag": tag, "p": [], "median": [], "min": [], "max": [], "n": []}
        for p, m in pts:
            st = by_p.get(m)
            if st is None:
                raise MissingKey(f"{E.ANALYSIS}: tags.{tag}.intensity.by_p has no point {m!r}")
            s["p"].append(p)
            for f in ("median", "min", "max", "n"):
                s[f].append(st.get(f))
        series[key] = s
    out = {"keys": list(KEYS), "groups": [{"letter": g, "title": t, "keys": list(ks)} for g, t, ks in GROUPS],
           "grid": [p for p, _ in pts], "grid_modes": [m for _, m in pts], "weeks": weeks, "series": series,
           "flat": [k for k, s in series.items() if _flat(s)],
           "tables": {"e7r_modes": modes_table(an), "e7r_stress": stress_table(an, pts)},
           "labels": dict(LABELS),
           "meta": {**E.meta_of({"analysis": an}), "analysis_sha256": meta.get("script_sha256"),
                    "eval_git_revision": meta.get("eval_git_revision")}}
    out["labels"]["caption"] = caption(out)
    out["meta"]["sources"] = list(inp.sources)
    return out


def _flat(s: Mapping) -> bool:
    v = [x for x in s["median"] if x is not None]
    lo = [x for x in s["min"] if x is not None]
    hi = [x for x in s["max"] if x is not None]
    return bool(v) and max(v) == min(v) and max(lo) == min(lo) and max(hi) == min(hi)


def caption(d: Mapping) -> str:
    nw = len(d["weeks"])
    spot = [p for p in d["grid"] if p in SPOT_P]
    flat = LABELS["flat"] if "a9p" in d["flat"] else ""
    return LABELS["caption"].format(weeks=L.week_span(d["weeks"]), n_weeks=nw, s="s" if nw != 1 else "",
                                    n_keys=E.count(len(d["keys"])), grid=", ".join(_fmt_p(p) for p in d["grid"]),
                                    spot=("$p=" + "$ and $p=".join(_fmt_p(p) for p in spot) + "$") if spot
                                    else "no rates",
                                    dodge=format(DODGE_PT, "g"), flat=flat)


def mode_columns(modes) -> list[dict]:
    """The columns of e7r_modes in order: L-tr, L-hon, the other stress lenders of the confirmation that are not
    i.i.d., the i.i.d. lenders by p, the regional lenders by spreading probability, the peak-aligned lender, then any
    other mode; each with its group ('iid', 'regional' or None) and its head."""
    modes = set(modes)
    iid = sorted((m for m in modes if m.startswith("L-iid-")), key=lambda m: float(m[len("L-iid-"):]))
    reg = sorted((m for m in modes if m.startswith("L-co-reg-")), key=lambda m: float(m[len("L-co-reg-"):]))
    first = [m for m in (E.TRACE, E.HON, "L-eg", "L-ss", "L-co") if m in modes]
    last = [m for m in ("L-pk",) if m in modes]
    rest = sorted(modes - set(first) - set(iid) - set(reg) - set(last), key=E.mode_rank)
    out = [{"mode": m, "group": None, "head": E.mode_text(m)} for m in first]
    out += [{"mode": m, "group": "iid", "head": m[len("L-iid-"):]} for m in iid]
    out += [{"mode": m, "group": "regional", "head": m[len("L-co-reg-"):]} for m in reg]
    out += [{"mode": m, "group": None, "head": "peak"} for m in last]
    out += [{"mode": m, "group": None, "head": E.mode_text(m)} for m in rest]
    return out


def modes_table(an: Mapping) -> dict:
    tags = an["tags"]
    have = {m for x in tags.values() for m in (x.get("r0") or {})}
    cols = mode_columns(have)
    aliases = {}
    for t, x in tags.items():
        src = " ".join(x.get("sources") or [])
        if "alias of" in src:
            aliases[t] = src.split("alias of ", 1)[1].rstrip(")")
    rows = []
    for t in E.tag_order(tags):
        x = tags[t]
        rows.append({"tag": t, "label": E.label(t), "group": E.group_of(t, x), "alias_of": aliases.get(t),
                     "r0": {m: E.stats_of(st) for m, st in (x.get("r0") or {}).items()}})
    return {"rows": rows, "columns": cols,
            "scope": {"tags": [r["tag"] for r in rows], "modes": [c["mode"] for c in cols],
                      "weeks": [str(w) for w in an["weeks"]]}}


def stress_table(an: Mapping, pts: Sequence[tuple]) -> dict:
    tags = an["tags"]
    meta = an.get("meta") or {}
    w0p = list(meta.get("w0plus_modes") or [])
    weeks = [str(w) for w in an["weeks"]]
    rows = []
    for t in E.tag_order(tags):
        x = tags[t]
        it = x.get("intensity")
        cross = None
        # review of W-G4 B: a tag not run under every lender of the grid (the oracle forecast: L-hon only) has no curve;
        # its one point at p = 0 would otherwise count every week as 'not reached'
        if it and [m for _p, m in it.get("points") or []] == [m for _p, m in pts]:
            counts = {_fmt_p(p): 0 for p, _ in pts}
            counts["none"] = 0
            gaps = 0
            for w in weeks:
                c = (it.get("per_week") or {}).get(w) or {}
                f = c.get("first_p_above_1")
                counts["none" if f is None else _fmt_p(f)] += 1
                gaps += bool(c.get("missing_before_first"))
            cross = {"counts": counts, "weeks_with_gap": gaps}
        attained = {}
        for w in weeks:
            r = ((x.get("per_week") or {}).get(w) or {}).get("r0") or {}
            vals = [r.get(m) for m in w0p]
            if not w0p or any(v is None for v in vals):
                continue
            m = max(w0p, key=lambda k: (r[k], -w0p.index(k)))
            attained[m] = attained.get(m, 0) + 1
        rows.append({"tag": t, "label": E.label(t), "group": E.group_of(t, x), "crossings": cross,
                     "w0plus_lender": dict(sorted(attained.items(), key=lambda kv: (-kv[1], w0p.index(kv[0]))))})
    ad = (an.get("checks") or {}).get("adaptive_equivalence") or {}
    return {"rows": rows, "grid": [_fmt_p(p) for p, _ in pts], "w0plus_modes": w0p,
            "adaptive": {k: ad.get(k) for k in ("n_pairs", "max_abs_diff", "equivalence")},
            "scope": {"tags": [r["tag"] for r in rows], "weeks": weeks, "grid": [_fmt_p(p) for p, _ in pts]}}


# ---------------------------------------------------------------------------------------------------------------
# drawing
def x_of(p: float, grid: Sequence[float]) -> float:
    """The x position of a p: log10(p) for p > 0, p = 0 ZERO_DECADES left of the least positive p."""
    pos = [q for q in grid if q > 0]
    if p > 0:
        return math.log10(p)
    return math.log10(min(pos)) - ZERO_DECADES


def _outside_math(text: str, i: int) -> bool:
    return text[:i].count("$") % 2 == 0


def end_name(fig, label: str) -> str:
    """A registry label as an end label: one line where it is at most LABEL_WRAP_IN wide, else split once at the space
    (outside $...$) that gives the narrowest widest line (the words stay the registry label's)."""
    if text_width_in(fig, label) <= LABEL_WRAP_IN:
        return label
    best = None
    for i, c in enumerate(label):
        if c == " " and _outside_math(label, i):
            a, b = label[:i], label[i + 1:]
            w = max(text_width_in(fig, a), text_width_in(fig, b))
            if best is None or w < best[0]:
                best = (w, f"{a}\n{b}")
    return label if best is None else best[1]


def _rad_pt(keys: Sequence[str]) -> float:
    """The largest marker radius of `keys` (pt), its edge included."""
    return max(0.5 * (style.policy(k).markersize + style.MARKER_EDGE_PT) for k in keys)


def layout(fig, groups: Sequence[Mapping], grid: Sequence[float]) -> dict:
    """The panels' widths and x ranges (C62): each panel is the data part, the same width and scale in every panel,
    and on its right a label column as wide as its widest end label (end_name) after the end markers' reach and
    END_RUN_PT, with END_EDGE_PT to the panel's edge; the data part from the p = 0 point less a pad to the largest p,
    the x spine to the largest p plus a pad, each pad X_PAD_DEC or the dodge and the marker's reach with
    KEY_PAD_PT, whichever is larger."""
    keys = [[REF] + list(g["keys"]) for g in groups]
    names = [{k: end_name(fig, style.policy(k).label) for k in ks} for ks in keys]
    rad = _rad_pt([k for ks in keys for k in ks])
    dodge = [0.5 * (len(ks) - 1) * DODGE_PT for ks in keys]
    reach = max(dodge) + rad + KEY_PAD_PT            # the outermost series' marker edge beyond its p, with clearance
    right = [d + rad + END_RUN_PT + 2.0 * _rad_pt(ks) + END_MARK_GAP_PT
             + max(text_width_in(fig, n) for n in nm.values()) * style.BP_PER_IN + END_EDGE_PT
             for d, ks, nm in zip(dodge, keys, names)]
    avail = (style.W2 - style.LEFT_LABEL - style.LEFT_SHARED * (len(groups) - 1) - style.MARGIN_RIGHT) * style.BP_PER_IN
    left_pt = (avail - sum(right)) / len(groups)    # the data part of every panel, from xlo to the largest p
    if left_pt <= 0:
        raise style.StyleError(f"{NAME}: the end labels need {sum(right):.0f} pt, the row has {avail:.0f} pt")
    xs = [x_of(p, grid) for p in grid]
    x0, x1 = min(xs), max(xs)
    pad = X_PAD_DEC
    for _ in range(20):                              # the left pad in decades at the scale it sets
        ppd = left_pt / (x1 - x0 + pad)
        new = max(X_PAD_DEC, reach / ppd)
        if abs(new - pad) < 1e-9:
            break
        pad = new
    ppd = left_pt / (x1 - x0 + pad)
    return {"names": names, "widths_pt": [left_pt + r for r in right], "xlo": x0 - pad,
            "xhi": [x1 + r / ppd for r in right], "spine_hi": x1 + max(X_PAD_DEC, reach / ppd),
            "x_col": [x1 + (d + rad + END_RUN_PT) / ppd for d in dodge], "pt_per_decade": ppd}


def y_ticks(lo: float, hi: float) -> list[float]:
    for st in Y_STEPS:
        t = [round(k * st, 10) for k in range(math.ceil(lo / st - 1e-9), math.floor(hi / st + 1e-9) + 1)]
        if Y_MIN_TICKS <= len(t) <= Y_MAX_TICKS:
            return t
    return [round(lo, 3), round(hi, 3)]


def draw_panel(ax, keys: Sequence[str], series: Mapping, grid: Sequence[float]) -> list[tuple]:
    """The panel's series, layered (lines, bars, markers) and dodged; returns (x, y_top) of every point and bar end."""
    n = len(keys)
    w_pt = style.axes_rect_in(ax)[2] * style.BP_PER_IN
    x0, x1 = ax.get_xlim()
    per_pt = (x1 - x0) / w_pt
    drawn = []
    for i, k in enumerate(keys):
        s = series[k]
        x = np.array([x_of(p, grid) for p in s["p"]]) + (i - (n - 1) / 2.0) * DODGE_PT * per_pt
        y = np.array([np.nan if v is None else v for v in s["median"]], dtype=float)
        lo = np.array([np.nan if v is None else v for v in s["min"]], dtype=float)
        hi = np.array([np.nan if v is None else v for v in s["max"]], dtype=float)
        drawn.append((k, x, y, lo, hi))
        pos = np.array([p > 0 for p in s["p"]])
        if pos.any():                       # the line joins the positive p; p = 0 is joined across the break dotted
            line_casing(ax, k, x[pos], y[pos])
            ln = style.plot_policy(ax, k, x[pos], y[pos], markevery=[])
            ln._sublet_role = "line"        # review of W-G4 B: ref_label may set Sublet's label on its own line
        if (~pos).any() and pos.any():
            j0, j1 = int(np.flatnonzero(~pos)[0]), int(np.flatnonzero(pos)[0])
            kw = style.policy_kwargs(k, markers=False, label=False)
            kw.update(linestyle=":", linewidth=0.8 * kw["linewidth"])
            (ln,) = ax.plot([x[j0], x[j1]], [y[j0], y[j1]], **kw)
            ln._sublet_policy = k
            ln._sublet_role = "zero_link"
    for k, x, y, lo, hi in drawn:
        ok = np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi) & (hi > lo)
        if ok.any():
            style.errorbars(ax, k, x[ok], y[ok], lo[ok], hi[ok], zorder=Z_BARS)
    pts = []
    for k, x, y, lo, hi in drawn:
        kw = style.policy_kwargs(k, lines=False, label=False)
        kw["zorder"] = Z_MARKS + Z_STEP * (kw["zorder"] - style.Z_DATA)
        (mk,) = ax.plot(x, y, **kw)
        mk._sublet_role = "markers"
        mk._sublet_markers_of = k
        mk._sublet_policy = k
        pts += [(float(a), float(np.nanmax([b, c]))) for a, b, c in zip(x, y, hi) if np.isfinite(b)]
    return pts


def end_labels(ax, keys: Sequence[str], series: Mapping, grid: Sequence[float], names: Mapping[str, str],
               x_col: float, spine_hi: float) -> list:
    """Each series named at its curve's right end (C62, in place of the panel's legend): in the label column at x_col
    (data units) its marker (role 'end_marker') and END_MARK_GAP_PT after the markers' column its end label
    (names[key]; TICK_PT, the policy's label color, va 'center'), centered as near to the height of the series' last
    median as the labels stacked in one column with LABEL_GAP_PT between them allow (common.stack_labels, inside the
    axes by KEY_PAD_PT); a thin leader in the label's color from just right of the panel's last markers (spine_hi), at
    the height of the series' last median, to the label's marker, where the label sits more than common.LEVEL_PT off
    that height. Sublet's label has the role 'direct_label' (the tests' and review's name), the others 'end_label'.
    Returns the labels."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    to_pt = 72.0 / fig.dpi
    inv = ax.transData.inverted()
    col_pt = ax.transData.transform((x_col, 0.0))[0] * to_pt          # the column's left edge (pt)
    mark_w = 2.0 * _rad_pt(keys)                                      # the markers' column, as wide as the widest
    x_text = float(inv.transform(((col_pt + mark_w + END_MARK_GAP_PT) / to_pt, 0.0))[0])
    x_mark = float(inv.transform(((col_pt + 0.5 * mark_w) / to_pt, 0.0))[0])
    ends, texts = [], []
    for k in keys:
        s = series[k]
        idx = [j for j, v in enumerate(s["median"]) if v is not None]
        if not idx:
            continue
        y_end = float(s["median"][idx[-1]])
        p = style.policy(k)
        t = ax.text(x_text, y_end, names[k], fontsize=style.TICK_PT, ha="left", va="center", color=p.label_color,
                    zorder=style.Z_THEORY_LABEL, linespacing=1.1)
        t._sublet_role = "direct_label" if k == REF else "end_label"
        t._sublet_policy = k
        texts.append(t)
        ends.append(ax.transData.transform((x_col, y_end))[1] * to_pt)
    if not texts:
        return []
    heights = [max(t.get_window_extent(r).height * to_pt, mark_w) for t in texts]
    bb = ax.get_window_extent(r)
    pos = stack_labels(ends, heights, gap=LABEL_GAP_PT, bottom=bb.y0 * to_pt + KEY_PAD_PT + 0.5,
                       top=bb.y1 * to_pt - KEY_PAD_PT - 0.5)
    x_lead1 = float(inv.transform(((col_pt - LEADER_GAP_PT) / to_pt, 0.0))[0])
    for t, y_pt, e_pt in zip(texts, pos, ends):
        k = t._sublet_policy
        y = float(inv.transform((0.0, y_pt / to_pt))[1])
        t.set_position((x_text, y))
        kw = style.policy_kwargs(k, lines=False, label=False)        # the series' marker before its name
        kw["zorder"] = style.Z_THEORY_LABEL
        (m,) = ax.plot([x_mark], [y], **kw)
        m._sublet_role, m._sublet_marker_of = "end_marker", k
        if abs(y_pt - e_pt) > LEVEL_PT:
            ye = float(inv.transform((0.0, e_pt / to_pt))[1])
            (ln,) = ax.plot([spine_hi, x_lead1], [ye, y], color=t.get_color(), linewidth=LEADER_PT, linestyle="-",
                            marker="None", zorder=style.Z_THEORY_LABEL - 0.01, label="_nolegend_", clip_on=False)
            ln._sublet_role = "leader"
            ln._sublet_leader_of = k
    return texts


def x_ticks(grid: Sequence[float], lo: float, hi: float) -> tuple[list, list]:
    """(positions, labels): p = 0 at its place and the powers of ten inside the axis, up to the largest p (C58: the
    margin of Sublet's end label holds no tick)."""
    pos, lab = [x_of(0.0, grid)], ["0"]
    zero_break = x_of(0.0, grid) + BREAK_DECADES
    hi = min(hi, max(x_of(p, grid) for p in grid) + 0.15)
    for e in range(math.floor(lo), math.ceil(hi) + 1):
        if zero_break + 0.15 < e <= hi:
            pos.append(float(e))
            lab.append(f"$10^{{{e}}}$")
    return pos, lab


def break_marks(ax, x: float) -> None:
    """Two short slanted strokes on the x spine at x (the axis break between p = 0 and the positive p)."""
    tr = ax.get_xaxis_transform()
    w_pt = style.axes_rect_in(ax)[2] * style.BP_PER_IN
    x0, x1 = ax.get_xlim()
    dx = 1.6 * (x1 - x0) / w_pt
    h = 3.0 / (style.axes_rect_in(ax)[3] * style.BP_PER_IN)
    for off in (-dx, dx):
        (ln,) = ax.plot([x + off - dx, x + off + dx], [-h, h], transform=tr, color="black", linewidth=style.AXES_PT,
                        clip_on=False, zorder=5, label="_nolegend_")
        ln._sublet_role = "axis_break"


def draw(data: Mapping) -> Any:
    fig = style.new_figure(NAME)
    lab = data["labels"]
    groups = data["groups"]
    grid = data["grid"]
    lay = layout(fig, groups, grid)
    axes = style.panel_row(fig, lay["widths_pt"], sharey=[False] + [True] * (len(groups) - 1))
    series = data["series"]
    vals = [v for s in series.values() for f in ("median", "min", "max") for v in s[f] if v is not None]
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, 1e-6)
    y0, top = lo - Y_PAD * span, hi + Y_PAD * span
    axes[0].set_ylim(y0, top)
    ticks = y_ticks(y0, top)
    xs = [x_of(p, grid) for p in grid]
    xlo, spine_hi = lay["xlo"], lay["spine_hi"]
    for ax, g, xhi in zip(axes, groups, lay["xhi"]):
        ax.set_xlim(xlo, xhi)
        keys = style.legend_order([REF] + list(g["keys"]))
        draw_panel(ax, keys, series, grid)
        if y0 < 1.0 < top:                  # all-fallback, ending with the x spine (the label column holds none)
            style.reference_line(ax, y=1.0, xmax=(spine_hi - xlo) / (xhi - xlo))
        pos, labs = x_ticks(grid, xlo, spine_hi)
        ax.xaxis.set_major_locator(FixedLocator(pos))
        ax.xaxis.set_major_formatter(FixedFormatter(labs))
        ax.xaxis.set_minor_locator(FixedLocator([x for x, p in zip(xs, grid) if p > 0]))
        break_marks(ax, x_of(0.0, grid) + BREAK_DECADES)
        ax.yaxis.set_major_locator(FixedLocator(ticks))
        ax.yaxis.set_major_formatter(style.PLAIN)
        ax.spines["bottom"].set_bounds(xlo, spine_hi)       # the label column right of it holds the end labels
        style.ygrid(ax)                                     # C62: light y grid, ending with the x spine
    for ax, g, x_col, names in zip(axes, groups, lay["x_col"], lay["names"]):   # once the limits are final
        end_labels(ax, style.legend_order([REF] + list(g["keys"])), series, grid, names, x_col, spine_hi)
    axes[0].set_ylabel(lab["y"])
    center_xlabel(axes, lab["x"])
    letters = style.panel_letters(axes)
    for letter, g in zip(letters, groups):
        E.title(letter, g["title"])
    fig._sublet_axes = axes
    fig._sublet_layout = lay
    return fig


# ---------------------------------------------------------------------------------------------------------------
# LaTeX
NAME_IN = 1.05                  # the name column of e7r_modes (in; a long name on two lines)
RUNS_FILE = "baseline_study_runs.csv"   # sf_bl_ms7's data file of every run (named in the captions)
STRESS_NAME_IN = 1.75


def two_lines(st: Mapping | None) -> str:
    """A cell of e7r_modes: the median (three decimals) over its min--max (two decimals); '--' without a run."""
    if not st or st.get("median") is None:
        return "--"
    rng = "" if st.get("min") is None else f"{E.num(st['min'], 2)}--{E.num(st['max'], 2)}"
    return r"\begin{tabular}[t]{@{}c@{}}" + E.num(st["median"]) + r"\\" + rng + r"\end{tabular}"


def modes_tex(t: Mapping, d: Mapping) -> str:
    cols = t["columns"]
    n = len(cols)
    rows, groups, prev = [], [], None
    for r in t["rows"]:
        if r["group"] != prev:
            groups.append(len(rows))
            prev = r["group"]
        if r["alias_of"]:
            rows.append([L.rag(L.tex(r["label"])), r"\multicolumn{" + str(n) + r"}{l}{the runs of "
                         + L.tex(E.label(r["alias_of"])) + "}"])
            continue
        st = [r["r0"].get(c["mode"]) for c in cols]
        rows.append([L.rag(L.tex(r["label"]))] + [two_lines(x) for x in st])
    spans, i = [], 0
    while i < n:                                   # the spanning heads of the i.i.d. and regional columns
        g = cols[i]["group"]
        j = i
        while j + 1 < n and g is not None and cols[j + 1]["group"] == g:
            j += 1
        spans.append((i, j, g))
        i = j + 1
    head_top = " & " + " & ".join(
        ("" if g is None else r"\multicolumn{" + str(b - a + 1) + r"}{c}{" + {"iid": r"i.i.d., $p=$",
                                                                             "regional": "regional"}[g] + "}")
        for a, b, g in spans) + r" \\"
    rules = "".join(r"\cmidrule(lr){" + f"{a + 2}-{b + 2}" + "}" for a, b, g in spans if g is not None)
    if rules:
        head_top += "\n" + rules
    n_w = len(d["weeks"])
    cap = (r"Every policy of the baseline study under every lender on weeks " + L.week_span(d["weeks"]) + f" ({n_w} "
           + ("weeks" if n_w != 1 else "week") + r", policy seed 0): the median of $r_0$ over the weeks and, on the "
           r"line below, its min--max: the trace lender L-tr, the honoring lender L-hon, the stress lenders of the "
           r"confirmation, the i.i.d.\ lenders by their reclaim probability $p$ per site and slot (the new rates and "
           r"the confirmation's $0.05$ and $0.2$), the regional correlated lender by its spreading probability, and "
           r"the peak-aligned trace lender (peak). Rules separate " + groups_text(t["rows"]) + r". The "
           r"confirmation's policies take their runs under its seven lenders from the confirmation; MPC with the "
           r"oracle forecast, at MPC's as-built setting, ran under L-tr and L-hon only (--: not run). Every run is in "
           r"the data file "
           + L.tex(RUNS_FILE) + ".")
    return L.longtable("@{}p{" + f"{NAME_IN}in" + "}" + "c" * n + "@{}", cap, "tab:e7r-modes",
                       ["Policy"] + [c["head"] for c in cols], rows, groups=groups, size=r"\scriptsize",
                       tabcolsep="1.7pt", head_top=head_top, keep=0)


def groups_text(items: Sequence[Mapping]) -> str:
    """The groups of a table's rows in their order, for its caption (ms7_e7r_lib.GROUP_TEXT)."""
    return E.join(E.GROUP_TEXT[g] for g in dict.fromkeys(x["group"] for x in items))


def _lender_list(att: Mapping) -> str:
    return ", ".join(f"{E.mode_text(m)} ({n})" for m, n in att.items()) or "--"


def stress_tex(t: Mapping, d: Mapping) -> str:
    grid = t["grid"]
    rows, groups, prev, marked = [], [], None, False
    for r in t["rows"]:
        if r["group"] != prev:
            groups.append(len(rows))
            prev = r["group"]
        c = r["crossings"]
        mark = ""
        if c is None:
            cells = ["--"] * (len(grid) + 1)
        else:
            cells = [str(c["counts"][p]) if c["counts"][p] else "" for p in grid] + [str(c["counts"]["none"])]
            # review of W-G4 B: the mark goes on the policy, not on the 'not reached' count (a gap week may cross)
            mark = r"$^{\dagger}$" if c["weeks_with_gap"] else ""
            marked = marked or bool(mark)
        rows.append([L.rag(L.tex(r["label"]) + mark)] + cells + [L.rag(_lender_list(r["w0plus_lender"]))])
    ad = t.get("adaptive") or {}
    eq = ""
    if ad.get("n_pairs"):
        diff = ad.get("max_abs_diff")
        eq = (r" The adaptive lender L-ad of Theorem~\ref{thm:lower}(a) enters $W_0^{+}$ through its equivalence with "
              r"the eager lender L-eg: on the confirmation's " + f"{ad['n_pairs']}" + r" paired runs their $r_0$ "
              + ("are equal" if not diff else r"differ by at most " + L.bound_text(float(diff))) + ".")
    n_w = len(d["weeks"])
    # review of W-G4 B: the policies without a curve, read from the data (the oracle forecast in the runs)
    none = [r["label"] for r in t["rows"] if r["crossings"] is None]
    no_curve = ("" if not none else " " + E.join(L.tex(x) for x in none)
                + (" was" if len(none) == 1 else " were") + r" not run under the i.i.d.\ lenders (--).")
    cap = (r"The stress regimes per policy on weeks " + L.week_span(d["weeks"]) + f" ({n_w} week" + ("s" if n_w != 1
                                                                                                    else "")
           + r"): the number of weeks whose least reclaim probability $p$ of the i.i.d.\ lender with $r_0>1$ is each "
           r"$p$ of the grid ($p=0$: the honoring lender; blank: none), or that have $r_0\le1$ at every $p$ "
           r"(not reached"
           # integration review of X5: the dagger's note only where a row carries the dagger
           + (r"; $^{\dagger}$in a week of the policy a point before its crossing, or any point where it has none, "
              r"has no run" if marked else "") + r"), and the lenders "
           r"at which $W_0^{+}$, the largest $r_0$ over the " + E.count(len(t["w0plus_modes"]))
           + r" stress lenders, is reached, with their numbers of weeks (ties to the first of L-eg, L-ss, L-iid-0.05, "
           r"L-iid-0.2, L-co and the new lenders)." + no_curve + r" Rules separate " + groups_text(t["rows"]) + "."
           + eq)
    head_top = (r" & \multicolumn{" + str(len(grid) + 1) + r"}{c}{Weeks with first $r_0>1$ at $p=$} & \\" "\n"
                r"\cmidrule(lr){2-" + str(len(grid) + 2) + "}")
    return L.longtable("@{}p{" + f"{STRESS_NAME_IN}in" + "}" + "c" * (len(grid) + 1) + "p{2.75in}@{}", cap,
                       "tab:e7r-stress", ["Policy"] + grid + ["not reached", r"Lender of $W_0^{+}$ (weeks)"], rows,
                       groups=groups, tabcolsep="2.4pt", head_top=head_top, size=r"\scriptsize", keep=0)


def write_tables(data: Mapping, report: Mapping) -> None:
    E.guard_reduced(data, NAME)
    t = data["tables"]
    head = L.table_head
    paths = [write_table(TABLES[0], head(NAME, [E.ANALYSIS]) + modes_tex(t["e7r_modes"], data)),
             write_table(TABLES[1], head(NAME, [E.ANALYSIS]) + stress_tex(t["e7r_stress"], data))]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    def build_checked(inp: Inputs) -> dict:
        d = build(inp)
        E.guard_reduced(d, NAME)
        return d

    def draw_checked(d: Mapping) -> Any:
        E.guard_reduced(d, NAME)
        return draw(d)

    try:
        return cli(NAME, build_checked, draw_checked, argv, supplementary=True, after=write_tables, doc=__doc__)
    except E.MissingInput as err:
        print(err.code, file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main(sys.argv[1:])
